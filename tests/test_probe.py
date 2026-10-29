"""Offline tests for the capability probe; never call paid APIs."""
import io
import json
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from agent_kit import client, probe

ROOT = Path(__file__).resolve().parent.parent
KEY = 'probe-secret-key-value'


def reply(data):
    return io.BytesIO(json.dumps(data).encode())


def http_error(code):
    return urllib.error.HTTPError('https://api.meta.ai/v1', code, 'error', {}, io.BytesIO(b'remote body'))


GOOD = {'appointment_date': '2026-11-02', 'appointment_time': '10:00', 'arrive_by': '09:45',
        'destination': 'Demo Community Clinic, Suite 200, Nashville, TN'}


def response(fields):
    return reply({'id': 'resp_probe', 'model': 'muse-spark-1.3', 'status': 'completed', 'usage': {'total_tokens': 9},
                  'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(fields)}]}]})


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / 'cases', self.root / 'cases')
        env = patch.dict('os.environ', {'MODEL_API_KEY': KEY}, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def probe(self, *replies, image=True):
        with patch('urllib.request.OpenerDirector.open', side_effect=list(replies)) as opened:
            result = probe.run(self.root, image=image)
        return result, opened

    def test_all_capabilities_recorded_without_key(self):
        models = reply({'data': [{'id': 'muse-spark-1.3'}, {'id': 'sam-3.1'}, {'id': 'muse-voice-transcribe'}]})
        result, opened = self.probe(models, response(GOOD))
        self.assertEqual(result['image_input']['status'], 'PASSED')
        self.assertEqual(result['image_input']['response_id'], 'resp_probe')
        self.assertEqual(result['sam_segmentation']['candidates'], ['sam-3.1'])
        self.assertEqual(result['speech']['candidates'], ['muse-voice-transcribe'])
        self.assertFalse(result['sam_segmentation']['request_sent'])
        self.assertEqual(opened.call_count, 2)
        saved = (self.root / result['saved_to']).read_text()
        self.assertNotIn(KEY, saved)
        sent = json.loads(opened.call_args_list[1].args[0].data)
        self.assertEqual(sent['input'][0]['content'][1]['type'], 'input_image')
        self.assertEqual(sent['tools'] if 'tools' in sent else [], [])

    def test_wrong_extraction_is_not_reported_as_passing(self):
        wrong = dict(GOOD, arrive_by='10:00')
        result, _ = self.probe(reply({'data': []}), response(wrong))
        self.assertEqual(result['image_input']['status'], 'MODEL_RESPONDED_FIELDS_MISMATCH')
        self.assertFalse(result['image_input']['field_checks']['arrive_by'])

    def test_rejected_image_request_is_recorded_not_raised(self):
        result, _ = self.probe(http_error(404), http_error(400))
        self.assertEqual(result['models']['status'], 'UNAVAILABLE')
        self.assertEqual(result['sam_segmentation']['status'], 'UNKNOWN_MODEL_LIST_UNAVAILABLE')
        self.assertEqual(result['image_input']['status'], 'REQUEST_REJECTED_OR_FAILED')
        self.assertFalse(result['image_input']['inference_succeeded'])
        self.assertNotIn('remote body', json.dumps(result))

    def test_no_image_makes_no_inference_call(self):
        result, opened = self.probe(reply({'data': [{'id': 'muse-spark-1.3'}]}), image=False)
        self.assertEqual(opened.call_count, 1)
        self.assertEqual(result['paid_inference_calls'], 0)
        self.assertEqual(result['speech']['status'], 'NOT_LISTED')

    def test_refuses_non_meta_endpoint_and_missing_key(self):
        with patch.dict('os.environ', {'MODEL_API_BASE': 'https://evil.example/v1'}), \
             patch('urllib.request.OpenerDirector.open') as opened, self.assertRaises(client.ModelError):
            probe.run(self.root)
        opened.assert_not_called()
        with patch.dict('os.environ', {'MODEL_API_KEY': ''}), self.assertRaises(client.ModelError):
            probe.run(self.root)


if __name__ == '__main__':
    unittest.main()
