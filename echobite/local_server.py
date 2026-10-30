"""Launch a separately installed official Telegram Bot API binary, without Docker."""
import os
import shutil
import subprocess
from pathlib import Path
from .__main__ import load_env
from .api import API, APIError


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--logout-cloud', action='store_true',
                        help='Cloud sessiyasidan bir marta chiqish; mahalliy serverga o‘tish uchun.')
    args = parser.parse_args()
    load_env()
    if args.logout_cloud:
        token = os.environ.get('BOT_TOKEN', '')
        if ':' not in token:
            raise SystemExit('BOT_TOKEN ni kiriting.')
        try:
            API(token).call('logOut')
        except APIError as exc:
            raise SystemExit(str(exc)) from None
        print('Cloud sessiyasi yopildi. Local serverni va keyin botni ishga tushiring.')
        return
    api_id = os.environ.get('TELEGRAM_API_ID', '')
    api_hash = os.environ.get('TELEGRAM_API_HASH', '')
    if not api_id.isdigit() or int(api_id) <= 0 or not api_hash:
        raise SystemExit('TELEGRAM_API_ID va TELEGRAM_API_HASH ni .env ichiga kiriting.')
    binary = os.environ.get('TELEGRAM_BOT_API_EXE', 'telegram-bot-api')
    executable = shutil.which(binary)
    if not executable:
        raise SystemExit('telegram-bot-api topilmadi. LOCAL_API_WINDOWS.md ni o‘qing.')
    directory = os.environ.get('LOCAL_FILES_DIR', '')
    if not directory:
        raise SystemExit('LOCAL_FILES_DIR ni kiriting.')
    directory = Path(directory).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    print('Local Bot API: http://127.0.0.1:8081 — terminalni ochiq qoldiring.')
    try:
        result = subprocess.run([executable, '--local', '--http-ip-address=127.0.0.1',
            '--http-port=8081', f'--dir={directory}'], env=os.environ.copy())
        raise SystemExit(result.returncode)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
