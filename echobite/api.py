"""Small Bot API client using only Python's standard library."""
import json
import os
from urllib.parse import urlsplit
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class APIError(RuntimeError):
    def __init__(self, code=0, retry_after=0):
        self.code, self.retry_after = code, retry_after
        super().__init__(f'Telegram API error {code}')  # Never expose token-bearing URLs.


class API:
    def __init__(self, token, *, local=False, base_url='https://api.telegram.org',
                 local_files_dir=None, download_timeout=3600):
        base_url = base_url.rstrip('/')
        parsed = urlsplit(base_url)
        if local:
            if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
                raise ValueError('Local API shu kompyuterda, localhost HTTP manzilida ishlashi kerak.')
            if not local_files_dir:
                raise ValueError('Local rejim uchun LOCAL_FILES_DIR kerak.')
        elif base_url != 'https://api.telegram.org':
            raise ValueError('Cloud rejim uchun rasmiy API manzilidan foydalaning.')
        if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError('BOT_API_URL faqat server manzili va portdan iborat bo‘lsin.')
        self.local = local
        self.max_input_bytes = 2_000_000_000 if local else 20_000_000
        self.limit_label = '2 GB' if local else '20 MB'
        self.local_files_dir = Path(local_files_dir).expanduser().resolve() if local_files_dir else None
        self.download_timeout = download_timeout
        self.base = f'{base_url}/bot{token}/'
        self.files = f'{base_url}/file/bot{token}/'

    @classmethod
    def from_env(cls, token):
        mode = os.environ.get('BOT_API_MODE', 'cloud').lower()
        if mode not in ('cloud', 'local'):
            raise ValueError('BOT_API_MODE cloud yoki local bo‘lsin.')
        local = mode == 'local'
        timeout = int(os.environ.get('DOWNLOAD_TIMEOUT_SECONDS', '3600'))
        if timeout <= 0:
            raise ValueError('DOWNLOAD_TIMEOUT_SECONDS musbat bo‘lsin.')
        return cls(token, local=local,
                   base_url=os.environ.get('BOT_API_URL') or ('http://127.0.0.1:8081' if local else 'https://api.telegram.org'),
                   local_files_dir=os.environ.get('LOCAL_FILES_DIR'), download_timeout=timeout)

    def call(self, method, payload=None, voice: Path | None = None):
        payload = payload or {}
        if voice is None:
            body = json.dumps(payload).encode()
            content_type = 'application/json'
        else:
            boundary = uuid.uuid4().hex
            chunks = []
            for key, value in payload.items():
                chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n').encode())
            chunks.extend([(f'--{boundary}\r\nContent-Disposition: form-data; name="voice"; filename="voice.ogg"\r\nContent-Type: audio/ogg\r\n\r\n').encode(),
                           voice.read_bytes(), f'\r\n--{boundary}--\r\n'.encode()])
            body = b''.join(chunks)
            content_type = f'multipart/form-data; boundary={boundary}'
        request = Request(self.base + method, data=body, headers={'Content-Type': content_type})
        try:
            with urlopen(request, timeout=self.download_timeout if method == 'getFile' else 90) as response:
                result = json.load(response)
        except HTTPError as exc:
            try:
                result = json.load(exc)
            except (ValueError, OSError):
                raise APIError(exc.code) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise APIError() from None
        if not result.get('ok'):
            raise APIError(result.get('error_code', 0), result.get('parameters', {}).get('retry_after', 0))
        return result['result']

    def download(self, file_id, target: Path, limit=None):
        limit = self.max_input_bytes if limit is None else min(limit, self.max_input_bytes)
        file = self.call('getFile', {'file_id': file_id})
        error = f'Fayl {self.limit_label} dan katta.'
        if file.get('file_size', 0) > limit:
            raise ValueError(error)
        if self.local:
            # Local API owns its cache. Read in place, never load/copy 2 GB into RAM.
            source = Path(file.get('file_path', '')).expanduser()
            if not source.is_absolute():
                raise ValueError('Local server --local bilan ishga tushirilmagan: mutlaq file_path kutilgan.')
            source = source.resolve()
            if not source.is_relative_to(self.local_files_dir):
                raise ValueError('Fayl LOCAL_FILES_DIR tashqarisida. Server va bot papkalarini moslang.')
            if not source.is_file():
                raise ValueError('Local API fayli ko‘rinmayapti. Server va bot bir tizimda ishlasin.')
            if source.stat().st_size > limit:
                raise ValueError(error)
            return source
        try:
            with urlopen(self.files + file['file_path'], timeout=90) as response, target.open('wb') as out:
                size = 0
                while chunk := response.read(64 * 1024):
                    size += len(chunk)
                    if size > limit:
                        raise ValueError(error)
                    out.write(chunk)
            return target
        except (URLError, TimeoutError, OSError):
            target.unlink(missing_ok=True)
            raise APIError() from None
        except ValueError:
            target.unlink(missing_ok=True)
            raise
