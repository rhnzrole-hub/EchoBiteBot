import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from echobite.api import API, APIError


class APITests(unittest.TestCase):
    def test_json_request_and_error_redaction(self):
        api = API('123:secret')
        with patch('echobite.api.urlopen', return_value=io.BytesIO(b'{"ok":true,"result":[]}')) as request:
            self.assertEqual(api.call('getUpdates', {'timeout': 30}), [])
            self.assertEqual(json.loads(request.call_args.args[0].data), {'timeout': 30})
        with patch('echobite.api.urlopen', return_value=io.BytesIO(
                b'{"ok":false,"error_code":429,"parameters":{"retry_after":5}}')):
            with self.assertRaises(APIError) as ctx:
                api.call('sendMessage')
            self.assertEqual(ctx.exception.retry_after, 5)
            self.assertNotIn('secret', str(ctx.exception))

    def test_multipart_voice(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'test.ogg'
            path.write_bytes(b'example audio bytes')
            with patch('echobite.api.urlopen', return_value=io.BytesIO(
                    b'{"ok":true,"result":{"voice":{"file_id":"abc"}}}')) as request:
                result = API('123:secret').call('sendVoice', {'chat_id': 1, 'title': 'O‘zbek'}, voice=path)
                body = request.call_args.args[0].data
                self.assertIn(b'name="voice"; filename="voice.ogg"', body)
                self.assertIn('O‘zbek'.encode(), body)
                self.assertIn(b'example audio bytes', body)
                self.assertEqual(result['voice']['file_id'], 'abc')
