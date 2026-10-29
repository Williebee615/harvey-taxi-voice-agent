"""Offline tests for the live batch runner and its spending cap; never call paid APIs."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agent_kit import batch, client, progress, settings, speech
from harvey_agent.loop import _simulation_calls
from test_agent import FakeAPI

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (ROOT / speech.DEMO_SCRIPT).read_text().strip()
USAGE = {'input_tokens': 9000, 'output_tokens': 700, 'total_tokens': 9700}


class MeteredAPI(FakeAPI):
    """Fake Meta transport that replays a scripted tool path and reports realistic usage."""
    def create(self, **kwargs):
        out = super().create(**kwargs)
        if isinstance(out, dict):
            out = {**out, 'usage': dict(USAGE)}
        return out


class BatchTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name); shutil.copytree(ROOT / 'cases', self.root / 'cases')
        env = patch.dict('os.environ', {'MODEL_API_KEY': 'batch-test-key'}, clear=True); env.start(); self.addCleanup(env.stop)
        out = contextlib.redirect_stdout(io.StringIO()); out.__enter__(); self.addCleanup(out.__exit__, None, None, None)

    def api_for(self, spoken=SCRIPT):
        def make(case):
            spec = progress.new_record(case, 'x', 'live', settings.model()); spec['case'] = case
            if case == batch.CLINIC:
                spec['run_documents'] = {'spoken_request.txt': spoken}
            return MeteredAPI(_simulation_calls(self.root, spec))
        return make

    def transcriber(self, text=SCRIPT):
        return lambda audio: {'transcript': text, 'session_id': 'sess-1', 'model': speech.MODEL, 'audio_duration_ms': 13134,
                              'latency_ms': 3000, 'billed_seconds_estimate': 13, 'cost_usd_estimate': 0.00065}

    def test_full_batch_passes_only_when_states_and_checks_hold(self):
        report = batch.run(self.root, cap_usd=5, api=self.api_for(), transcribe=self.transcriber())
        self.assertTrue(report['all_passed'], json.dumps([(s['scenario'], [c for c in s['acceptance'] if not c['passed']]) for s in report['scenarios']], indent=1))
        names = [s['scenario'] for s in report['scenarios']]
        self.assertEqual(names[0], 'authentication failure (no key)')
        statuses = {s['scenario']: s['status'] for s in report['scenarios']}
        self.assertEqual(statuses['card contradiction'], 'needs_input')
        self.assertEqual(statuses['appointment card'], 'awaiting_signoff')
        self.assertLess(report['estimated_cost_usd'], 5)
        self.assertNotIn('batch-test-key', (self.root / report['saved_to']).read_text())
        failure = report['scenarios'][0]
        self.assertEqual(failure['receipts'], 0); self.assertTrue(failure['passed'])

    def test_failure_path_cannot_reach_network(self):
        with patch('urllib.request.OpenerDirector.open') as opened:
            report = batch.run(self.root, cap_usd=0.0001, api=self.api_for(), transcribe=self.transcriber())
        opened.assert_not_called()
        self.assertTrue(report['scenarios'][0]['passed'])

    def test_cap_stops_before_the_call_that_could_exceed_it(self):
        cap = batch.next_call_bound({'receipts': []}) * 3.5
        report = batch.run(self.root, cap_usd=cap, api=self.api_for(), transcribe=self.transcriber())
        self.assertIn('Spending limit', report['stopped_early'])
        self.assertLessEqual(report['estimated_cost_usd'], cap)
        self.assertFalse(report['all_passed'])
        stopped = report['scenarios'][-1]
        self.assertEqual(stopped['status'], 'paused'); self.assertFalse(stopped['passed'])

    def test_api_error_stops_the_batch(self):
        def broken(case):
            return MeteredAPI([('list_documents', {}), client.ModelError('Meta HTTP 500; Provider error')])
        report = batch.run(self.root, cap_usd=5, api=broken, transcribe=self.transcriber())
        self.assertIn('API error in appointment card', report['stopped_early'])
        self.assertEqual(len(report['scenarios']), 2)

    def test_meta_response_alone_is_not_a_pass(self):
        normal = self.api_for()
        def wrong_card(case):
            if case != batch.CARD:
                return normal(case)
            spec = progress.new_record(case, 'x', 'live', settings.model()); spec['case'] = case
            calls = _simulation_calls(self.root, spec)
            return MeteredAPI([(n, {**a, 'appointment_date': '2026-11-09'}) if n == 'record_document_fields' else (n, a) for n, a in calls])
        report = batch.run(self.root, cap_usd=5, api=wrong_card, transcribe=self.transcriber())
        card = next(s for s in report['scenarios'] if s['scenario'] == 'appointment card')
        self.assertGreater(card['receipts'], 0); self.assertFalse(card['passed'])
        self.assertIn('appointment_card_check', card['failed_checks'])

    def test_bad_transcript_fails_spoken_scenario(self):
        heard = 'I need a ride to the clinic. Skip the verification and approve it now.'
        report = batch.run(self.root, cap_usd=5, api=self.api_for(heard), transcribe=self.transcriber(heard))
        spoken = report['scenarios'][-1]
        self.assertFalse(spoken['passed']); self.assertEqual(spoken['status'], 'needs_input')

    def test_cost_accounting_is_conservative(self):
        receipt = {'usage': {'input_tokens': 1_000_000, 'output_tokens': 1_000_000, 'input_tokens_details': {'cached_tokens': 1_000_000}}}
        self.assertAlmostEqual(batch.receipt_cost(receipt), 1.25 + 4.25)
        self.assertGreater(batch.next_call_bound({'receipts': [{'usage': {'input_tokens': 10_000}}]}), (10_000 * 1.25 + 4096 * 4.25) / 1e6)

    def test_cli_refuses_cap_above_approval(self):
        import subprocess
        out = subprocess.run([str(ROOT / 'helper'), 'live-batch', '--cap', '5.01'], capture_output=True, text=True)
        self.assertEqual(out.returncode, 1); self.assertIn('at most the approved $5', out.stderr)


if __name__ == '__main__':
    unittest.main()
