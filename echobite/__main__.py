import logging
import os
import shutil
from pathlib import Path
from .api import API, APIError
from .bot import Bot
from .store import Store


def load_env(path=Path('.env')):
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.partition('=')
            if sep:
                os.environ.setdefault(key.strip(), value.strip().strip('\"\''))


def main():
    load_env()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    token = os.environ.get('BOT_TOKEN', '')
    try:
        owner = int(os.environ.get('ADMIN_ID', '0'))
    except ValueError:
        owner = 0
    if ':' not in token or owner <= 0:
        raise SystemExit('.env ichida BOT_TOKEN va musbat raqamli ADMIN_ID ni kiriting.')
    for binary in ('ffmpeg', 'ffprobe'):
        if not shutil.which(binary):
            raise SystemExit(f'{binary} o‘rnatilmagan yoki PATH ichida yo‘q.')
    data = Path(os.environ.get('DATA_DIR', 'data'))
    api = API.from_env(token)
    try:
        me = api.call('getMe')
        hook = api.call('getWebhookInfo')
        if hook.get('url'):
            raise SystemExit('Webhook faol. Polling uchun avval webhookni o‘chiring; README ni o‘qing.')
        if not me.get('supports_inline_queries'):
            logging.warning('BotFather /setinline orqali inline rejimni yoqing.')
        api.call('setMyCommands', {'commands': [
            {'command': 'start', 'description': 'Bot haqida'},
            {'command': 'add', 'description': 'Audio qo‘shish (admin)'},
            {'command': 'delete', 'description': 'Audio o‘chirish (admin)'},
            {'command': 'clear', 'description': 'Barcha audioni o‘chirish (admin)'},
            {'command': 'cancel', 'description': 'Qo‘shishni bekor qilish'},
            {'command': 'id', 'description': 'Telegram ID raqamingiz'}]})
        logging.info('Bot started: @%s; input limit: %s', me['username'], api.limit_label)
        bot = Bot(api, Store(data / 'library.sqlite3'), owner, data, me['username'])
        bot.migrate_legacy()
        bot.serve()
    except KeyboardInterrupt:
        pass
    except (APIError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == '__main__':
    main()
