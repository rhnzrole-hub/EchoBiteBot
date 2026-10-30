import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from echobite.bot import Bot, DENIED
from echobite.media import MediaError, interval, convert, probe
from echobite.store import Store


class FakeAPI:
    def __init__(self, fixture):
        self.fixture, self.calls = fixture, []

    def call(self, method, payload=None, voice=None):
        self.calls.append((method, payload, voice))
        if method == 'sendVoice':
            assert voice.exists()
            return {'voice': {'file_id': 'cached-voice'}}
        return {'message_id': len(self.calls)}

    def download(self, file_id, target):
        target.write_bytes(self.fixture.read_bytes())


class BotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.wav = self.root / 'test.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=3:sample_rate=48000', str(self.wav)], check=True)
        self.api = FakeAPI(self.wav)
        self.store = Store(self.root / 'db.sqlite3')
        self.bot = Bot(self.api, self.store, 123, self.root)

    def tearDown(self):
        self.temp.cleanup()

    def msg(self, text='', user=123, **extra):
        self.bot.handle({'message': {'from': {'id': user}, 'chat': {'id': user, 'type': 'private'},
                                     'text': text, **extra}})

    def choice(self, answer, user=123, job=None):
        job = job or self.bot.session['job']
        self.bot.handle({'callback_query': {'id': 'cb', 'from': {'id': user},
            'message': {'message_id': 7, 'chat': {'id': 123, 'type': 'private'}},
            'data': f'cut:{job}:{answer}'}})

    def upload(self, kind='audio'):
        self.msg('/add')
        self.msg(**{kind: {'file_id': 'original', 'file_size': self.wav.stat().st_size}})

    def test_denied_and_start(self):
        self.msg('/start', user=999)
        self.assertIn('@EchoBiteBot', self.api.calls[-1][1]['text'])
        self.msg('/add', user=999)
        self.assertEqual(self.api.calls[-1][1]['text'], DENIED)
        self.assertIsNone(self.bot.session)

    def test_uncut_workflow_and_search(self):
        self.upload('document')
        self.choice('no')
        self.msg('Oʻzbek MEM')
        self.assertIsNone(self.bot.session)
        self.assertEqual(len(self.store.search("o'zbek mem")), 1)
        self.bot.inline({'id': 'query', 'query': "o'zbek", 'offset': ''})
        response = self.api.calls[-1][1]
        self.assertEqual(response['results'][0]['voice_file_id'], 'cached-voice')
        self.assertEqual(response['results'][0]['type'], 'voice')
        self.assertEqual(len(Store(self.root / 'db.sqlite3').search('')), 1)

    def test_trim_workflow(self):
        self.upload('voice')
        self.choice('yes')
        self.msg('00:00.250 - 00:01.375')
        self.assertEqual(self.bot.session['state'], 'title')
        self.assertTrue((self.bot.session['dir'] / 'output.ogg').exists())
        self.msg('Kulgi')
        self.assertAlmostEqual(self.store.search('kulgi')[0]['duration'], 1.125)

    def test_bad_ranges_and_retry(self):
        self.upload()
        self.choice('yes')
        for value in ('3 - 1', '0 - 8', 'nan', '00:99 - 01:00', '0 - 0.001'):
            self.msg(value)
            self.assertEqual(self.bot.session['state'], 'range')
        self.msg('1.5')
        self.assertEqual(self.bot.session['state'], 'title')

    def test_unauthorized_stale_and_repeated_callbacks(self):
        self.upload()
        self.choice('yes', user=999)
        self.assertEqual(self.bot.session['state'], 'choice')
        self.choice('yes', job='old')
        self.assertEqual(self.bot.session['state'], 'choice')
        self.choice('no')
        self.choice('yes')
        self.assertEqual(self.bot.session['state'], 'title')

    def test_cancel_expiry_and_restart_cleanup(self):
        self.upload()
        folder = self.bot.session['dir']
        self.msg('/cancel')
        self.assertFalse(folder.exists())
        self.upload()
        self.bot.session['updated'] -= 1801
        self.bot.expire()
        self.assertIsNone(self.bot.session)
        abandoned = self.bot.temp / 'draft-abandoned'
        abandoned.mkdir()
        Bot(self.api, self.store, 123, self.root)
        self.assertFalse(abandoned.exists())

    def test_size_invalid_file_and_invalid_title(self):
        self.msg('/add')
        self.msg(audio={'file_id': 'x', 'file_size': 20_000_001})
        self.assertEqual(self.bot.session['state'], 'file')
        self.wav.write_bytes(b'not audio')
        self.msg(document={'file_id': 'x'})
        self.assertEqual(self.bot.session['state'], 'file')

    def test_pagination_and_literal_search(self):
        for i in range(43):
            self.store.add(str(i), f'Mem {i}', 'file' + str(i), 1)
        self.bot.inline({'id': 'q', 'query': '', 'offset': '20'})
        result = self.api.calls[-1][1]
        self.assertEqual(len(result['results']), 20)
        self.assertEqual(result['next_offset'], '40')
        self.bot.inline({'id': 'q', 'query': '', 'offset': '40'})
        self.assertEqual(len(self.api.calls[-1][1]['results']), 3)
        self.assertEqual(self.api.calls[-1][1]['next_offset'], '')
        self.assertEqual(self.store.search("%' OR 1=1 --"), [])

    def test_public_requests_preserve_draft(self):
        self.upload()
        session = self.bot.session
        self.bot.safe_public({'message': {'from': {'id': 999}, 'chat': {'id': 999, 'type': 'private'}, 'text': '/add'}})
        self.assertIs(self.bot.session, session)

    def test_failed_conversion_does_not_publish_partial_file(self):
        self.upload()
        self.choice('no')
        def fail(source, output, *args):
            output.write_bytes(b'partial')
            raise MediaError('failed')
        with patch('echobite.bot.convert', fail):
            self.msg('Broken')
        self.assertFalse((self.bot.session['dir'] / 'output.ogg').exists())
        self.assertEqual(self.store.search(''), [])
        self.msg('Fixed')
        self.assertEqual(len(self.store.search('fixed')), 1)

    def test_real_formats_and_sample_length(self):
        for ext, codec in [('mp3', 'libmp3lame'), ('m4a', 'aac'), ('ogg', 'libopus'), ('flac', 'flac')]:
            with self.subTest(format=ext):
                source = self.root / ('input.' + ext)
                subprocess.run(['ffmpeg', '-v', 'error', '-i', str(self.wav), '-c:a', codec, str(source)], check=True)
                self.assertGreater(probe(source), 2.9)
                output = self.root / 'cut.ogg'
                convert(source, output, (0.251, 1.376))
                pcm = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(output),
                    '-f', 's16le', '-ac', '1', '-ar', '48000', '-'])
                # Decoded MP3 honors gapless delay/padding metadata: 54,000 samples.
                self.assertLessEqual(abs(len(pcm) // 2 - 54000), 1)


if __name__ == '__main__':
    unittest.main()
