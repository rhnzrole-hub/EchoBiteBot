import logging
import queue
import secrets
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .api import APIError
from .media import MediaError, convert, interval, probe

log = logging.getLogger(__name__)
DENIED = "Bu buyruqni faqat admin ishlata oladi."


class Bot:
    def __init__(self, api, store, owner_id, data_dir, username='EchoBiteBot'):
        self.api, self.store, self.owner = api, store, owner_id
        self.username = username
        self.max_input_bytes = getattr(api, 'max_input_bytes', 20_000_000)
        self.limit_label = getattr(api, 'limit_label', '20 MB')
        self.temp = Path(data_dir) / 'tmp'
        self.temp.mkdir(parents=True, exist_ok=True)
        # Single-instance application: abandoned drafts are removed on restart.
        for item in self.temp.iterdir():
            if item.is_dir() and item.name.startswith('draft-'):
                shutil.rmtree(item)
        self.session = None

    def say(self, chat, text, **extra):
        return self.api.call('sendMessage', dict(chat_id=chat, text=text, **extra))

    def clear(self):
        if self.session:
            if 'dir' in self.session:
                shutil.rmtree(self.session['dir'], ignore_errors=True)
        self.session = None

    def expire(self):
        if self.session and time.monotonic() - self.session['updated'] > 1800:
            self.clear()

    def inline(self, q):
        raw_offset = q.get('offset', '')
        offset = int(raw_offset) if raw_offset.isascii() and raw_offset.isdigit() and len(raw_offset) <= 7 else 0
        rows = self.store.search(q.get('query', '')[:256], offset, voices_only=True)
        self.api.call('answerInlineQuery', {
            'inline_query_id': q['id'], 'cache_time': 0, 'is_personal': False,
            'results': [{'type': 'voice', 'id': row['job'], 'voice_file_id': row['file_id'], 'title': row['title']}
                        for row in rows[:20]],
            'next_offset': str(offset + 20) if len(rows) > 20 else '',
            'button': {'text': 'EchoBiteBot haqida', 'start_parameter': 'help'},
        })

    def handle(self, update):
        self.expire()
        if 'callback_query' in update:
            return self.callback(update['callback_query'])
        m = update.get('message')
        if not m:
            return
        chat = m['chat']['id']
        user = m.get('from', {}).get('id')
        text = m.get('text', '').strip()
        command = text.split()[0] if text.startswith('/') else ''
        if '@' in command and command.split('@', 1)[1].casefold() != self.username.casefold():
            return
        command = command.split('@')[0].casefold()
        if command in ('/start', '/help'):
            return self.say(chat, f"EchoBiteBot — mem audiolar kutubxonasi.\n\n"
                            f"Istalgan chatda @{self.username} va audio nomini yozing, natijani tanlang. "
                            "Bo'sh qidiruvda barcha audiolar chiqadi.\n\n"
                            "/add — audio qo'shish (faqat admin)\n/delete — audio o‘chirish (admin)\n/clear — barchasini o‘chirish (admin)\n/cancel — qo'shishni bekor qilish\n"
                            "/id — Telegram ID raqamingiz\n\nKanal/guruhda yuborish huquqingiz bo'lishi kerak.")
        if command == '/id':
            return self.say(chat, f"Telegram ID: {user}" if user else 'Foydalanuvchi aniqlanmadi.')
        if command in ('/add', '/cancel', '/delete', '/clear') and user != self.owner:
            return self.say(chat, DENIED)
        if user != self.owner:
            if m['chat']['type'] == 'private':
                self.say(chat, 'Audio qo‘shish faqat admin uchun. Foydalanish: /start')
            return
        if m['chat']['type'] != 'private':
            if command in ('/add', '/cancel', '/delete', '/clear'):
                self.say(chat, 'Bu buyruqni bot bilan shaxsiy chatda ishlating.')
            return
        if command == '/cancel':
            self.clear()
            return self.say(chat, 'Bekor qilindi. Yangi audio uchun /add.')
        if command == '/delete':
            self.clear()
            argument = text.partition(' ')[2].strip()
            if argument.isascii() and argument.isdigit():
                return self.confirm_delete(chat, int(argument))
            self.session = dict(state='delete', chat=chat, updated=time.monotonic())
            return self.list_delete(chat, argument)
        if command == '/clear':
            self.clear()
            count = self.store.count()
            if not count:
                return self.say(chat, 'Katalog bo‘sh.')
            return self.confirm_remove(chat, 'all', count=count)
        if command == '/add':
            self.clear()
            job = secrets.token_hex(8)
            folder = self.temp / ('draft-' + job)
            folder.mkdir()
            self.session = dict(job=job, dir=folder, state='file', chat=chat, updated=time.monotonic())
            return self.say(chat, f'Audio, voice yoki audio fayl yuboring ({self.limit_label} gacha). Bekor qilish: /cancel')
        if command:
            return self.say(chat, 'Buyruqlar: /start, /add, /delete, /clear, /cancel, /id')
        s = self.session
        if not s:
            return self.say(chat, 'Audio qo‘shish uchun /add yuboring.')
        s['updated'] = time.monotonic()
        if s['state'] == 'delete':
            if text.isascii() and text.isdigit():
                return self.confirm_delete(chat, int(text))
            return self.list_delete(chat, text)
        if s['state'] == 'confirm_remove':
            return self.say(chat, 'Tasdiqlash tugmasini bosing yoki /cancel yuboring.')
        try:
            if s['state'] == 'file':
                media = m.get('audio') or m.get('voice') or m.get('document')
                if not media:
                    return self.say(chat, 'Audio, voice yoki audio hujjat yuboring.')
                if media.get('file_size', 0) > self.max_input_bytes:
                    return self.say(chat, f'Fayl {self.limit_label} dan katta. Kichikroq audio yuboring.')
                source = s['dir'] / 'source'
                self.say(chat, 'Fayl yuklanmoqda va tekshirilmoqda. Katta fayl ko‘proq vaqt olishi mumkin…')
                source = self.api.download(media['file_id'], source) or source
                s['duration'] = probe(source)
                s['source'] = source
                s['state'] = 'choice'
                s['updated'] = time.monotonic()
                return self.ask_choice()
            if s['state'] == 'choice':
                return self.ask_choice()
            if s['state'] == 'range':
                bounds = interval(text, s['duration'])
                self.say(chat, 'Audio kesilmoqda…')
                convert(s['source'], s['dir'] / 'output.ogg', bounds)
                s['bounds'] = bounds
                s['state'] = 'title'
                s['updated'] = time.monotonic()
                return self.say(chat, 'Audio kesildi. Endi audio nomini kiriting (1–100 belgi).')
            if s['state'] == 'title':
                if not text or len(text) > 100 or any(ord(c) < 32 for c in text):
                    return self.say(chat, 'Audio nomi bir qatorda, 1–100 belgi bo‘lsin.')
                output = s['dir'] / 'output.ogg'
                if not output.exists():
                    self.say(chat, 'Audio tayyorlanmoqda…')
                    convert(s['source'], output)
                # Reuse a confirmed upload on a database retry. Title is frozen once uploaded.
                if 'uploaded' not in s:
                    sent = self.api.call('sendVoice', {
                        'chat_id': chat,
                        'caption': text,
                    }, voice=output)
                    s['uploaded'] = sent['voice']['file_id']
                    s['title'] = text
                length = s['bounds'][1] - s['bounds'][0] if 'bounds' in s else s['duration']
                self.store.add(s['job'], s['title'], s['uploaded'], length)
                self.clear()
                return self.say(chat, f'Saqlandi! Endi @{self.username} orqali qidirib yuborish mumkin.')
        except (MediaError, ValueError) as exc:
            # Failed encoding must not leave a partial OGG that could later be uploaded.
            (s['dir'] / 'output.ogg').unlink(missing_ok=True)
            s['updated'] = time.monotonic()
            return self.say(chat, str(exc))

    def ask_choice(self):
        s = self.session
        return self.say(s['chat'], f"Davomiyligi: {s['duration']:.3f} soniya.\nAudioni kesish kerakmi?",
                        reply_markup={'inline_keyboard': [[
                            {'text': 'Ha', 'callback_data': f"cut:{s['job']}:yes"},
                            {'text': "Yo'q", 'callback_data': f"cut:{s['job']}:no"}]]})

    def callback(self, q):
        m = q.get('message', {})
        s = self.session
        if q['from']['id'] != self.owner:
            return self.api.call('answerCallbackQuery', {'callback_query_id': q['id'], 'text': DENIED, 'show_alert': True})
        if q.get('data', '').startswith('remove:'):
            return self.remove_callback(q)
        parts = q.get('data', '').split(':')
        valid = (s and s['state'] == 'choice' and len(parts) == 3
                 and parts[:2] == ['cut', s['job']] and parts[2] in ('yes', 'no')
                 and m.get('chat', {}).get('id') == s['chat']
                 and m.get('chat', {}).get('type') == 'private')
        self.api.call('answerCallbackQuery', {'callback_query_id': q['id'],
                                             'text': '' if valid else 'Bu tugma eskirgan. /add orqali boshlang.'})
        if not valid:
            return
        s['updated'] = time.monotonic()
        s['state'] = 'range' if parts[2] == 'yes' else 'title'
        prompt = (f"Qaysi qism qolsin? Boshlanish - tugash vaqtini yuboring.\n"
                  f"Masalan: 00:05.250 - 00:12.800\nFaqat 10 yuborsangiz, dastlabki 10 soniya olinadi.\n"
                  f"Audio uzunligi: {s['duration']:.3f} soniya."
                  if parts[2] == 'yes' else 'Audio nomini kiriting (1–100 belgi).')
        try:
            self.api.call('editMessageReplyMarkup', {'chat_id': s['chat'], 'message_id': m['message_id'],
                                                    'reply_markup': {'inline_keyboard': []}})
        except APIError:
            pass  # State and nonce still prevent reuse of a stale keyboard.
        self.say(s['chat'], prompt)

    def safe_handle(self, update):
        try:
            self.handle(update)
        except Exception as exc:
            # Do not log exception contents: network URLs may contain credentials.
            log.error('Update failed: %s', type(exc).__name__)
            m = update.get('message') or update.get('callback_query', {}).get('message')
            if m:
                try:
                    self.say(m['chat']['id'], 'Amal bajarilmadi. Qayta urinib ko‘ring yoki /cancel va /add yuboring.')
                except Exception:
                    pass

    def serve(self):
        admin_queue = queue.Queue(maxsize=100)
        stop = threading.Event()

        def worker():
            while not stop.is_set():
                try:
                    update = admin_queue.get(timeout=1)
                except queue.Empty:
                    self.expire()
                    continue
                self.safe_handle(update)
                admin_queue.task_done()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        # Inline/public traffic never waits for FFmpeg or admin uploads.
        slots = threading.BoundedSemaphore(64)

        def public(update):
            try:
                if 'inline_query' in update:
                    self.inline(update['inline_query'])
                else:
                    self.safe_public(update)
            except Exception as exc:
                log.warning('Public request failed: %s', type(exc).__name__)
            finally:
                slots.release()

        offset = 0
        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                while True:
                    try:
                        updates = self.api.call('getUpdates', {'offset': offset, 'timeout': 30,
                            'allowed_updates': ['message', 'callback_query', 'inline_query']})
                    except APIError as exc:
                        if exc.code in (401, 409):
                            raise RuntimeError('Token xato yoki boshqa bot nusxasi/webhook ishlayapti.') from None
                        log.warning('Polling interrupted; retrying.')
                        time.sleep(min(max(exc.retry_after, 3), 60))
                        continue
                    for update in updates:
                        payload = update.get('message') or update.get('callback_query') or {}
                        if 'inline_query' not in update and payload.get('from', {}).get('id') == self.owner:
                            admin_queue.put(update)
                        else:
                            slots.acquire()
                            pool.submit(public, update)
                        offset = update['update_id'] + 1
        finally:
            stop.set()
            thread.join(timeout=180)
            if not thread.is_alive():
                self.clear()

    def safe_public(self, update):
        # Public requests must not read or mutate the owner's draft across threads.
        if 'callback_query' in update:
            q = update['callback_query']
            self.api.call('answerCallbackQuery', {'callback_query_id': q['id'], 'text': DENIED, 'show_alert': True})
            return
        # Use a draft-free facade; public user is never authorized as owner.
        facade = object.__new__(Bot)
        facade.__dict__ = dict(self.__dict__, session=None)
        facade.safe_handle(update)

    def list_delete(self, chat, query=''):
        rows = self.store.search(query, limit=21)
        if not rows:
            return self.say(chat, 'Audio topilmadi. Boshqa nom yuboring yoki /cancel.')
        lines = [f"{r['id']} — {r['title']}" for r in rows[:20]]
        self.say(chat, 'O‘chirish uchun ID raqamini yuboring yoki nom bo‘yicha qidiring:\n\n'
                 + '\n'.join(lines) + ('\n\nYana natijalar bor. Nomini aniqroq yozing.' if len(rows) > 20 else ''))

    def confirm_delete(self, chat, audio_id):
        row = self.store.get(audio_id)
        if not row:
            self.session = dict(state='delete', chat=chat, updated=time.monotonic())
            return self.say(chat, 'Bu ID topilmadi. Boshqa ID yoki audio nomini yuboring.')
        return self.confirm_remove(chat, 'one', row=row)

    def confirm_remove(self, chat, scope, row=None, count=0):
        nonce = secrets.token_hex(8)
        self.session = dict(state='confirm_remove', chat=chat, updated=time.monotonic(),
                            nonce=nonce, scope=scope, row=row)
        text = (f"“{row['title']}” (ID: {row['id']}) o‘chirilsinmi?" if scope == 'one'
                else f'Katalogdagi barcha {count} ta audio o‘chirilsinmi? Bu amalni qaytarib bo‘lmaydi.')
        self.say(chat, text, reply_markup={'inline_keyboard': [[
            {'text': 'Ha, o‘chirish', 'callback_data': f'remove:{nonce}:yes'},
            {'text': 'Bekor qilish', 'callback_data': f'remove:{nonce}:no'}]]})

    def remove_callback(self, q):
        s = self.session
        parts = q.get('data', '').split(':')
        chat = q.get('message', {}).get('chat', {})
        valid = (q['from']['id'] == self.owner and s and s['state'] == 'confirm_remove'
                 and len(parts) == 3 and parts[1] == s['nonce'] and parts[2] in ('yes', 'no')
                 and chat.get('type') == 'private' and chat.get('id') == s['chat'])
        self.api.call('answerCallbackQuery', {'callback_query_id': q['id'],
            'text': '' if valid else 'Bu tugma eskirgan yoki ruxsat yo‘q.'})
        if not valid:
            return
        if parts[2] == 'no':
            self.clear()
            result = 'Bekor qilindi.'
        else:
            count = (self.store.clear_all() if s['scope'] == 'all'
                     else self.store.delete(s['row']['id'], s['row']['job']))
            self.clear()
            result = f'{count} ta audio katalogdan o‘chirildi.'
        try:
            self.api.call('editMessageReplyMarkup', {'chat_id': chat['id'],
                'message_id': q['message']['message_id'], 'reply_markup': {'inline_keyboard': []}})
        except APIError:
            pass
        self.say(chat['id'], result)

    def migrate_legacy(self):
        """Only legacy entries are downloaded; successful migrations are resumable."""
        import tempfile
        failed = 0
        for row in self.store.legacy():
            try:
                with tempfile.TemporaryDirectory(dir=self.temp, prefix='draft-') as folder:
                    source, output = Path(folder) / 'source', Path(folder) / 'voice.ogg'
                    source = self.api.download(row['file_id'], source) or source
                    probe(source)
                    convert(source, output)
                    sent = self.api.call('sendVoice', {'chat_id': self.owner,
                        'caption': f"Voice formatiga o‘tkazildi: {row['title']}"}, voice=output)
                    self.store.set_voice(row['id'], sent['voice']['file_id'])
            except Exception as exc:
                failed += 1
                log.warning('Legacy migration failed for ID %s: %s', row['id'], type(exc).__name__)
        if failed:
            self.say(self.owner, f'{failed} ta eski audio voice formatiga o‘tmadi. Ular bazada saqlandi, '
                     'lekin inline’da ko‘rsatilmaydi. Botni qayta ishga tushirib urinishingiz yoki '
                     '/delete bilan o‘chirib, /add orqali asl faylni qayta qo‘shishingiz mumkin.')
