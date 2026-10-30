"""Offline tests for the console's Meta speech-to-text endpoint; never call paid APIs."""
import contextlib
import http.client
import io
import json
import shutil
import struct
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from agent_kit import client, speech
from ui.ui import ConsoleServer

ROOT = Path(__file__).resolve().parent.parent
KEY = 'console-secret-key-value'


def wav(seconds=2.0, rate=16000):
    data = b'\x01\x00' * int(rate * seconds)
    fmt = struct.pack('<HHIIHH', 1, 1, rate, rate * 2, 2, 16)
    body = b'WAVE' + b'fmt ' + struct.pack('<I', 16) + fmt + b'data' + struct.pack('<I', len(data)) + data
    return b'RIFF' + struct.pack('<I', len(body)) + body


def heard(audio, keywords=None, opener=None):
    speech.wav_info(audio)
    return {'transcript': 'I need a wheelchair accessible ride with my service dog.', 'session_id': 'sess-console', 'model': speech.MODEL,
            'audio_duration_ms': 2000, 'local_audio_seconds': 2.0, 'latency_ms': 900, 'billed_seconds_estimate': 2, 'cost_usd_estimate': 0.0001}


class ConsoleSpeechTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name); shutil.copytree(ROOT / 'cases', self.root / 'cases')
        env = patch.dict('os.environ', {'MODEL_API_KEY': KEY}, clear=True); env.start(); self.addCleanup(env.stop)
        self.server = ConsoleServer(('127.0.0.1', 0), self.root)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True); thread.start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close(), thread.join()))
        out = contextlib.redirect_stdout(io.StringIO()); out.__enter__(); self.addCleanup(out.__exit__, None, None, None)

    def post(self, path, body, content_type, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        h = {'Content-Type': content_type, 'X-Console-Token': self.server.token, **(headers or {})}
        conn.request('POST', path, body=body, headers=h)
        result = conn.getresponse(); data = result.read(); conn.close()
        return result.status, data

    def transcribe(self, audio=None, **kw):
        with patch.object(speech, 'transcribe', side_effect=heard) as called:
            code, data = self.post('/api/transcribe', audio if audio is not None else wav(), 'audio/wav', **kw)
        return code, json.loads(data), called

    def test_transcribe_returns_transcript_without_key(self):
        code, body, called = self.transcribe()
        self.assertEqual(code, 200); self.assertEqual(called.call_count, 1)
        self.assertTrue(body['transcription_id'].startswith('tx_')); self.assertEqual(body['model'], speech.MODEL)
        self.assertNotIn(KEY, json.dumps(body)); self.assertNotIn('api_key', json.dumps(body).lower())

    def test_transcribe_refuses_bad_requests_before_calling_meta(self):
        cases = [(wav(), 'application/json', None, 415), (wav(), 'audio/wav', {'X-Console-Token': ''}, 403),
                 (wav(), 'audio/wav', {'Origin': 'https://evil.example'}, 403), (b'not audio' * 10, 'audio/wav', None, 400),
                 (wav(seconds=61), 'audio/wav', None, 400), (wav(seconds=0.1), 'audio/wav', None, 400),
                 (b'R' * 2_200_000, 'audio/wav', None, 413)]
        for audio, kind, headers, expected in cases:
            with self.subTest(expected=expected, kind=kind), patch.object(speech, 'transcribe') as called:
                code, _ = self.post('/api/transcribe', audio, kind, headers)
                self.assertEqual(code, expected); called.assert_not_called()

    def test_meta_error_is_reported_without_details(self):
        with patch.object(speech, 'transcribe', side_effect=client.ModelError('Meta HTTP 429; Rate or stream limit reached; not billed.')):
            code, data = self.post('/api/transcribe', wav(), 'audio/wav')
        self.assertEqual(code, 502); self.assertIn('429', json.loads(data)['error'])

    def run_with(self, body):
        code, data = self.post('/api/run', json.dumps({'mode': 'simulation', 'case': 'healthcare-clinic-visit', **body}), 'application/json')
        return code, json.loads(data)

    def test_confirmed_meta_transcript_runs_with_meta_provenance(self):
        _, tx, _ = self.transcribe()
        code, rec = self.run_with({'transcription_id': tx['transcription_id'], 'transcript_confirmed': True})
        self.assertEqual(code, 200)
        self.assertEqual(rec['run_documents']['spoken_request.txt'], tx['transcript'])
        self.assertEqual(rec['speech_source']['session_id'], 'sess-console'); self.assertTrue(rec['speech_source']['confirmed_by_reviewer'])

    def test_transcript_must_be_confirmed_unaltered_and_used_once(self):
        _, tx, _ = self.transcribe()
        self.assertEqual(self.run_with({'transcription_id': tx['transcription_id']})[0], 400)
        self.assertEqual(self.run_with({'transcription_id': tx['transcription_id'], 'transcript_confirmed': True, 'spoken_request': 'altered text'})[0], 400)
        code, body = self.run_with({'transcription_id': 'tx_unknown', 'transcript_confirmed': True})
        self.assertEqual((code, body['code']), (410, 'transcript_expired'))
        _, tx2, _ = self.transcribe()
        self.assertEqual(self.run_with({'transcription_id': tx2['transcription_id'], 'transcript_confirmed': True})[0], 200)
        self.assertEqual(self.run_with({'transcription_id': tx2['transcription_id'], 'transcript_confirmed': True})[0], 410)

    def test_typed_text_is_labeled_not_meta(self):
        code, rec = self.run_with({'spoken_request': 'I need a wheelchair accessible ride.'})
        self.assertEqual(code, 200); self.assertIn('not Meta', rec['speech_source'])


if __name__ == '__main__':
    unittest.main()
