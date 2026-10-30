"""Decode, sample-accurate trim, and encode; never stream-copy."""
import json
import math
import os
import re
import subprocess
from pathlib import Path


class MediaError(ValueError):
    pass


def timestamp(value: str) -> float:
    if not re.fullmatch(r"\d+(?::\d{1,2}){0,2}(?:[.,]\d{1,6})?", value.strip()):
        raise MediaError("Vaqt formati noto'g'ri. Masalan: 5.250 yoki 00:05.250")
    parts = [float(x) for x in value.replace(',', '.').split(':')]
    if len(parts) > 1 and any(x >= 60 for x in parts[1:]):
        raise MediaError("Daqiqa/soniya maydoni 60 dan kichik bo'lishi kerak.")
    total = 0.0
    for part in parts:
        total = total * 60 + part
    if not math.isfinite(total):
        raise MediaError("Vaqt qiymati juda katta.")
    return total


def interval(value: str, duration: float) -> tuple[float, float]:
    parts = re.split(r"\s*[-–—]\s*", value.strip())
    if len(parts) == 1:
        start, end = 0.0, timestamp(parts[0])
    elif len(parts) == 2:
        start, end = map(timestamp, parts)
    else:
        raise MediaError("Masalan: 00:05.250 - 00:12.800")
    if not 0 <= start < end <= duration:
        raise MediaError(f"0 ≤ boshlanish < tugash ≤ {duration:.3f} soniya bo'lishi kerak.")
    if end - start < 0.1:
        raise MediaError("Parcha kamida 0.1 soniya bo'lsin.")
    return start, end


def run(args: list[str], timeout: int = 120) -> bytes:
    try:
        return subprocess.run(args, check=True, capture_output=True, timeout=timeout).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        raise MediaError("Audio o'qilmadi yoki qayta ishlash vaqti tugadi. Boshqa fayl yuboring.") from exc


def probe(path: Path) -> float:
    raw = run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe',
               '-select_streams', 'a:0', '-show_entries', 'stream=codec_type,duration:format=duration',
               '-of', 'json', str(path)], 120)
    try:
        info = json.loads(raw)
        streams = info['streams']
        if not streams:
            raise ValueError()
        duration = float(streams[0].get('duration') or info['format']['duration'])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError()
        return duration
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise MediaError("Audio topilmadi yoki davomiyligini aniqlab bo‘lmadi.") from exc


def convert(source: Path, output: Path, bounds=None) -> None:
    # Normalize timestamps before trimming; atrim operates on decoded samples.
    expected = bounds[1] - bounds[0] if bounds is not None else probe(source)
    timeout = int(os.environ.get('FFMPEG_TIMEOUT_SECONDS', '1800'))
    if timeout <= 0:
        raise MediaError('FFMPEG_TIMEOUT_SECONDS musbat bo‘lsin.')
    filters = 'asetpts=PTS-STARTPTS'
    if bounds is not None:
        start, end = bounds
        filters += f',atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
         '-protocol_whitelist', 'file,pipe', '-i', str(source), '-map', '0:a:0',
         '-vn', '-sn', '-dn', '-map_metadata', '-1', '-af', filters,
         '-ac', '1', '-ar', '48000', '-c:a', 'libopus', '-b:a', '64k',
         '-threads', '1', '-t', f'{expected:.6f}', '-fs', '49000000', str(output)], timeout)
    if not output.exists() or output.stat().st_size >= 49_000_000:
        raise MediaError("Natija juda katta. Qisqaroq parcha tanlang.")
    actual = probe(output)
    if actual < expected - 0.15:
        output.unlink(missing_ok=True)
        raise MediaError('Chiqish voice hajmi chegaraga yetdi yoki fayl to‘liq o‘qilmadi. '
                         'Qisqaroq parcha tanlash uchun /cancel va /add yuboring.')
