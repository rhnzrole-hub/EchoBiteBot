import io
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from echobite.api import API
from echobite.media import probe, convert
import test_bot


class LargeFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cache = self.root / 'cache'
        self.cache.mkdir()
        self.api = API('123:secret', local=True, base_url='http://127.0.0.1:8081', local_files_dir=self.cache)

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_2gb_sparse_wav_no_copy_and_accurate_trim(self):
        source = self.cache / 'large.wav'
        size = 2_000_000_000
        # Valid, silent PCM WAV, sparse backing: logical size really is 2 GB.
        header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', size-8, b'WAVE', b'fmt ',
                             16, 1, 1, 48000, 96000, 2, 16, b'data', size-44)
        with source.open('wb') as f:
            f.write(header)
            f.truncate(size)
        target = self.root / 'must-not-copy'
        with patch.object(self.api, 'call', return_value={'file_path': str(source), 'file_size': size}), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('whole-file memory read')):
            actual = self.api.download('file', target)
        self.assertEqual(actual, source)
        self.assertFalse(target.exists())
        self.assertGreater(probe(source), 3600)
        output = self.root / 'voice.ogg'
        convert(source, output, (0.251, 1.376))
        self.assertAlmostEqual(probe(output), 1.125, delta=0.03)
        self.assertEqual(source.stat().st_size, size)

    def test_over_limit_checked_before_open(self):
        with patch.object(self.api, 'call', return_value={'file_size': 2_000_000_001}):
            with self.assertRaisesRegex(ValueError, '2 GB'):
                self.api.download('x', self.root / 'out')

    def test_real_size_checked_without_size_metadata(self):
        p = self.cache / 'too-large'
        with p.open('wb') as f:
            f.truncate(2_000_000_001)
        with patch.object(self.api, 'call', return_value={'file_path': str(p)}):
            with self.assertRaisesRegex(ValueError, '2 GB'):
                self.api.download('x', self.root / 'out')

    def test_local_path_boundary_and_mode(self):
        for path in (str(self.root / 'outside'), 'relative/path'):
            with patch.object(self.api, 'call', return_value={'file_path': path}):
                with self.assertRaises(ValueError):
                    self.api.download('x', self.root / 'out')
        with self.assertRaises(ValueError):
            API('x', local=True, local_files_dir=self.cache)
        with self.assertRaises(ValueError):
            API('x', local=True, base_url='http://127.0.0.1:8081')

    def test_cloud_stays_20mb(self):
        api = API('123:secret')
        with patch.object(api, 'call', return_value={'file_size': 20_000_001}):
            with self.assertRaisesRegex(ValueError, '20 MB'):
                api.download('x', self.root / 'out')

    def test_getfile_extended_timeout_only(self):
        with patch('echobite.api.urlopen', return_value=io.BytesIO(b'{"ok":true,"result":{}}')) as u:
            self.api.call('getFile')
            self.assertEqual(u.call_args.kwargs['timeout'], 3600)
        with patch('echobite.api.urlopen', return_value=io.BytesIO(b'{"ok":true,"result":{}}')) as u:
            self.api.call('getUpdates')
            self.assertEqual(u.call_args.kwargs['timeout'], 90)

    def test_local_env(self):
        with patch.dict(os.environ, {'BOT_API_MODE': 'local', 'LOCAL_FILES_DIR': str(self.cache)}, clear=True):
            api = API.from_env('x')
            self.assertEqual(api.max_input_bytes, 2_000_000_000)
            self.assertTrue(api.base.startswith('http://127.0.0.1:8081/'))


class LargeBotTests(unittest.TestCase):
    setUp = test_bot.BotTests.setUp
    tearDown = test_bot.BotTests.tearDown
    msg = test_bot.BotTests.msg

    def test_bot_accepts_2gb_metadata_and_rejects_larger(self):
        self.bot.max_input_bytes = 2_000_000_000
        self.bot.limit_label = '2 GB'
        self.msg('/add')
        self.assertIn('2 GB', self.api.calls[-1][1]['text'])
        self.msg(document={'file_id':'x', 'file_size':2_000_000_001})
        self.assertEqual(self.bot.session['state'], 'file')
        self.msg(document={'file_id':'x', 'file_size':2_000_000_000})
        self.assertEqual(self.bot.session['state'], 'choice')
