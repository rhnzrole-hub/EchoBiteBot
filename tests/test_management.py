import test_bot
import unittest
import sqlite3
from echobite.store import Store


class ManagementTests(unittest.TestCase):
    setUp = test_bot.BotTests.setUp
    tearDown = test_bot.BotTests.tearDown
    msg = test_bot.BotTests.msg
    def seed(self):
        self.store.add('a', 'Birinchi', 'voice-a', 2)
        self.store.add('b', 'Ikkinchi', 'voice-b', 3)

    def confirm(self, answer='yes', user=123, nonce=None, chat_type='private'):
        nonce = nonce or self.bot.session['nonce']
        self.bot.handle({'callback_query': {'id': 'r', 'from': {'id': user},
            'message': {'message_id': 55, 'chat': {'id': 123, 'type': chat_type}},
            'data': f'remove:{nonce}:{answer}'}})

    def test_delete_confirm_permissions_and_replay(self):
        self.seed()
        self.msg('/delete', user=999)
        self.assertEqual(self.store.count(), 2)
        self.msg('/delete')
        self.msg('Birinchi')
        self.assertIn('Birinchi', self.api.calls[-1][1]['text'])
        self.msg('1')
        nonce = self.bot.session['nonce']
        self.confirm(user=999)
        self.confirm(nonce='stale')
        self.confirm(chat_type='group')
        self.assertEqual(self.store.count(), 2)
        self.confirm()
        self.assertEqual(self.store.count(), 1)
        self.confirm(nonce=nonce)
        self.assertEqual(self.store.count(), 1)
        self.bot.inline({'id':'q', 'query':'Birinchi', 'offset':''})
        self.assertEqual(self.api.calls[-1][1]['results'], [])

    def test_clear_cancel_and_confirm(self):
        self.seed()
        self.msg('/clear', user=999)
        self.assertEqual(self.store.count(), 2)
        self.msg('/clear')
        self.assertEqual(self.store.count(), 2)
        self.confirm('no')
        self.assertEqual(self.store.count(), 2)
        self.msg('/clear')
        self.confirm()
        self.assertEqual(self.store.count(), 0)
        self.msg('/clear')
        self.assertIn('bo‘sh', self.api.calls[-1][1]['text'])

    def test_cancel_invalidates_destructive_button(self):
        self.seed()
        self.msg('/clear')
        nonce = self.bot.session['nonce']
        self.msg('/cancel')
        self.confirm(nonce=nonce)
        self.assertEqual(self.store.count(), 2)

    def test_legacy_conversion_and_resume(self):
        self.seed()
        with self.store.connect() as db:
            db.execute("UPDATE audios SET kind='audio'")
        self.bot.inline({'id':'q', 'query':'', 'offset':''})
        self.assertEqual(self.api.calls[-1][1]['results'], [])
        self.bot.migrate_legacy()
        self.assertEqual(self.store.legacy(), [])
        uploads = len([x for x in self.api.calls if x[0] == 'sendVoice'])
        self.bot.migrate_legacy()
        self.assertEqual(uploads, len([x for x in self.api.calls if x[0] == 'sendVoice']))
        self.bot.inline({'id':'q', 'query':'', 'offset':''})
        self.assertTrue(all(x['type'] == 'voice' for x in self.api.calls[-1][1]['results']))

    def test_v1_schema_migration(self):
        path = self.root / 'old.sqlite3'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE audios (id INTEGER PRIMARY KEY,job TEXT UNIQUE,title TEXT,search TEXT,file_id TEXT,duration REAL,created_at TEXT)')
            db.execute("INSERT INTO audios VALUES(7,'old','Old','old','mp3',1,NULL)")
        store = Store(path)
        self.assertEqual(store.legacy()[0]['id'], 7)
        self.assertEqual(store.search('', voices_only=True), [])
