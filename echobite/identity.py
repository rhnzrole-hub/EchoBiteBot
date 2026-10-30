"""Temporary setup-only mode: respond to /id; never accept audio."""
import os
from .__main__ import load_env
from .api import API, APIError


def main():
    load_env()
    token = os.environ.get('BOT_TOKEN', '')
    if ':' not in token:
        raise SystemExit('Avval .env ichiga BOT_TOKEN ni yozing.')
    api = API.from_env(token)
    try:
        me = api.call('getMe')
        if api.call('getWebhookInfo').get('url'):
            raise SystemExit('Webhook faol. README bo‘yicha avval uni o‘chiring.')
        print(f"@{me['username']} ga shaxsiy chatda /id yuboring. So‘ng Ctrl+C bosing.")
        offset = 0
        while True:
            for update in api.call('getUpdates', {'offset': offset, 'timeout': 30, 'allowed_updates': ['message']}):
                offset = update['update_id'] + 1
                m = update.get('message', {})
                if m.get('chat', {}).get('type') == 'private' and m.get('text', '').strip() == '/id':
                    api.call('sendMessage', {'chat_id': m['chat']['id'],
                        'text': f"Sizning Telegram ID: {m['from']['id']}\nShu raqamni .env dagi ADMIN_ID ga kiriting."})
    except KeyboardInterrupt:
        pass
    except APIError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == '__main__':
    main()
