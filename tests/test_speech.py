"""Offline tests for the Meta transcription adapter; never call paid APIs."""
import io
import json
import shutil
import struct
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from agent_kit import client, speech

ROOT = Path(__file__).resolve().parent.parent
KEY = 'speech-secret-key-value'
SCRIPT = (ROOT / speech.DEMO_SCRIPT).read_text().strip()


def wav(rate=24000, channels=1, bits=16, seconds=1.0):
    data = b'\0\0' * int(rate * seconds) * channels
    fmt = struct.pack('<HHIIHH', 1, channels, rate, rate * channels * bits // 8, channels * bits // 8, bits)
    body = b'WAVE' + b'fmt ' + struct.pack('<I', 16) + fmt + b'data' + struct.pack('<I', len(data)) + data
    return b'RIFF' + struct.pack('<I', len(body)) + body


def reply(data):
    return io.BytesIO(json.dumps(data).encode())


class SpeechTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict('os.environ', {'MODEL_API_KEY': KEY}, clear=True); env.start(); self.addCleanup(env.stop)

    def test_demo_audio_matches_documented_format(self):
        info = speech.wav_info((ROOT / speech.DEMO_AUDIO).read_bytes())
        self.assertEqual(info['sample_rate'], 24000); self.assertTrue(5 < info['seconds'] < 30)

    def test_rejects_unsupported_audio_without_network(self):
        with patch('urllib.request.OpenerDirector.open') as opened:
            for bad in [b'not audio', b'RIFF', wav(rate=44100), wav(channels=2), wav(bits=8)]:
                with self.subTest(size=len(bad)), self.assertRaises(ValueError):
                    speech.transcribe(bad)
            opened.assert_not_called()

    def test_request_shape_and_metadata(self):
        answer = {'sessionId': 's1', 'transcript': SCRIPT, 'audioDurationMs': 13134, 'turns': []}
        with patch('urllib.request.OpenerDirector.open', return_value=reply(answer)) as opened:
            out = speech.transcribe(wav(seconds=2), keywords=['Demo Community Clinic'])
        req = opened.call_args.args[0]
        self.assertTrue(req.full_url.startswith('https://api.meta.ai/v1/asr/transcribe?sessionId=harvey-'))
        self.assertEqual(req.get_header('Authorization'), 'Bearer ' + KEY)
        self.assertIn('multipart/form-data; boundary=', req.get_header('Content-type'))
        self.assertIn(b'"model": "muse-voice-transcribe-1.0"', req.data); self.assertIn(b'"mode": "PUSH_TO_TALK"', req.data)
        self.assertIn(b'"keywords": ["Demo Community Clinic"]', req.data); self.assertIn(b'name="audio"', req.data)
        self.assertEqual((out['billed_seconds_estimate'], out['session_id']), (13, 's1'))
        self.assertAlmostEqual(out['cost_usd_estimate'], 13 * 0.18 / 3600, places=6)

    def test_errors_hide_remote_body_and_key(self):
        error = urllib.error.HTTPError('u', 400, 'bad', {}, io.BytesIO(b'remote secret body'))
        with patch('urllib.request.OpenerDirector.open', side_effect=error), self.assertRaises(client.ModelError) as caught:
            speech.transcribe(wav())
        self.assertNotIn('remote secret body', str(caught.exception)); self.assertNotIn(KEY, str(caught.exception))
        with patch('urllib.request.OpenerDirector.open', return_value=reply({'sessionId': 'x'})), self.assertRaises(client.ModelError):
            speech.transcribe(wav())

    def test_refuses_other_endpoints_and_missing_key(self):
        with patch.dict('os.environ', {'MODEL_API_BASE': 'https://evil.example/v1'}), patch('urllib.request.OpenerDirector.open') as opened, self.assertRaises(client.ModelError):
            speech.transcribe(wav())
        opened.assert_not_called()
        with patch.dict('os.environ', {'MODEL_API_KEY': ''}), self.assertRaises(client.ModelError):
            speech.transcribe(wav())

    def test_accuracy_scoring(self):
        self.assertEqual(speech.word_error_rate(SCRIPT, SCRIPT), 0.0)
        self.assertTrue(all(speech.key_fact_checks(SCRIPT).values()))
        numeric = 'I need a wheelchair accessible ride with my service dog to Demo Community Clinic on November 2nd, arrive by 9:45 a.m.'
        self.assertTrue(all(speech.key_fact_checks(numeric).values()))
        wrong = speech.key_fact_checks('I need a ride to Demo Community Clinic on November third at ten.')
        self.assertFalse(wrong['wheelchair']); self.assertFalse(wrong['date']); self.assertFalse(wrong['arrive by'])

    def test_probe_makes_one_call_and_saves_no_key(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); root = Path(tmp.name)
        shutil.copytree(ROOT / 'cases', root / 'cases')
        answer = {'sessionId': 's2', 'transcript': SCRIPT, 'audioDurationMs': 13134}
        with patch('urllib.request.OpenerDirector.open', return_value=reply(answer)) as opened:
            result = speech.speech_probe(root)
        self.assertEqual(opened.call_count, 1); self.assertEqual(result['status'], 'PASSED')
        self.assertEqual(result['word_error_rate'], 0.0)
        self.assertNotIn(KEY, (root / result['saved_to']).read_text())
        with patch('urllib.request.OpenerDirector.open', side_effect=urllib.error.HTTPError('u', 429, 'x', {}, io.BytesIO(b''))) as opened:
            failed = speech.speech_probe(root)
        self.assertEqual(opened.call_count, 1); self.assertEqual(failed['status'], 'REQUEST_REJECTED_OR_FAILED')


if __name__ == '__main__':
    unittest.main()
