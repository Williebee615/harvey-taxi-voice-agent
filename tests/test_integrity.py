"""Offline tests for final-state audit integrity and provenance labeling; never call paid APIs."""
import copy
from pathlib import Path
from agent_kit import client
from harvey_agent.loop import approve_run, run_agent, _simulation_calls
from test_agent import AgentFixture, FakeAPI
from verification import checks

ROOT = Path(__file__).resolve().parent.parent
RETURN = 'healthcare-missing-return-plan'
CLINIC = 'healthcare-clinic-visit'
CONFLICT = 'healthcare-card-contradiction'


class IntegrityTests(AgentFixture):
    def live(self, case, calls=None, **kw):
        spec = self.rec(); spec['case'] = case
        calls = calls if calls is not None else _simulation_calls(self.root, spec)
        return run_agent(self.root, turns=len(calls) or 1, case_name=case, mode='live', api=FakeAPI(calls), **kw)

    def test_correct_needs_input_stop_passes_integrity(self):
        """A live run that correctly asks for the missing return plan has a consistent audit record."""
        rec = self.live(RETURN)
        self.assertEqual(rec['status'], 'needs_input')
        integrity = rec['run_integrity']
        self.assertTrue(integrity['passed'], integrity['errors'])
        self.assertEqual(integrity['state'], 'needs_input')
        self.assertEqual(integrity['failed_checks'], ['healthcare_transport_check'])
        self.assertTrue(integrity['evidence_requested'])
        self.assertIn('not a booking approval', integrity['scope'])
        self.assertEqual((rec['inference_mode'], rec['telemetry_source']), ('LIVE_META_API', 'simulation_fixture'))

    def test_simulation_and_contradiction_stops_pass(self):
        self.assertTrue(self.simulate(RETURN)['run_integrity']['passed'])
        self.assertTrue(self.live(CONFLICT)['run_integrity']['passed'])

    def test_signoff_states_pass_and_approval_still_gated(self):
        rec = self.live(CLINIC)
        self.assertEqual(rec['status'], 'awaiting_signoff'); self.assertTrue(rec['run_integrity']['passed'])
        signed = approve_run(self.root, rec['run_id'], 'Demo Reviewer')
        self.assertTrue(signed['run_integrity']['passed']); self.assertEqual(signed['run_integrity']['state'], 'completed_after_human_signoff')
        other = self.live(CLINIC)
        from agent_kit import progress
        stored = progress.load_progress(self.root, other['run_id'])
        stored['run_integrity'] = {'passed': False, 'errors': ['tampered']}
        progress.save(self.root, stored)
        with self.assertRaises(ValueError):
            approve_run(self.root, other['run_id'], 'Demo Reviewer')

    def test_unfinished_runs_say_not_verified_yet(self):
        paused = self.live(CLINIC, calls=[client.ModelError('Meta HTTP 500; Provider error')])
        self.assertEqual(paused['status'], 'paused')
        self.assertFalse(paused['run_integrity']['passed'])
        self.assertIn('Not verified yet', paused['run_integrity']['errors'][0])
        self.assertIn('Not verified yet', self.simulate(CLINIC, turns=2)['run_integrity']['errors'][0])

    def test_evidence_request_before_any_check_is_consistent(self):
        items = [{'id': x, 'question': x} for x in ('a', 'b', 'c', 'd')]
        rec = self.live(CLINIC, calls=[('list_documents', {}), ('set_checklist', {'items': items}),
                                       ('request_evidence', {'missing': ['Coordinator phone number']})])
        self.assertEqual(rec['status'], 'needs_input'); self.assertTrue(rec['run_integrity']['passed'])
        self.assertEqual(rec['run_integrity']['failed_checks'], [])

    def test_tampered_records_fail_integrity(self):
        base = self.live(RETURN)
        cases = {
            'dispatch on': lambda r: r.update(dispatch_enabled=True),
            'receipt removed': lambda r: r['receipts'].pop(),
            'receipt id blank': lambda r: r['turns'][0]['receipt'].update(response_id=None),
            'memo on needs_input': lambda r: r.update(memo={'answer': 'x', 'findings': [], 'gaps': []}),
            'quote altered': lambda r: r['facts'][0].update(quote=r['facts'][0]['quote'] + ' (edited)') if r['facts'] else r['facts'].append({'id': 'F9', 'document': 'HANDBOOK.md', 'quote': 'invented quote text', 'source_digest': 'x'}),
            'signoff without approval': lambda r: r.update(human_signoff_token='Someone'),
            'nothing failed or requested': lambda r: (r['verification'].update({k: {**v, 'passed': True} for k, v in r['verification'].items()}), r.update(evidence_requests=[])),
            'live label without response': lambda r: r.update(model_invoked_in_run=False),
        }
        for name, change in cases.items():
            with self.subTest(name):
                record = copy.deepcopy(base); change(record)
                self.assertFalse(checks.audit_integrity(self.root, record)['passed'])
        sim = copy.deepcopy(self.simulate(RETURN)); sim['receipts'] = [{'response_id': 'resp_fake'}]
        self.assertFalse(checks.audit_integrity(self.root, sim)['passed'])

    def test_changed_evidence_after_the_run_fails_integrity(self):
        rec = self.live(RETURN)
        self.write('rider_intake.txt', (self.root / 'cases' / RETURN / 'inbox' / 'rider_intake.txt').read_text() + '\nLate edit', RETURN)
        self.assertFalse(checks.audit_integrity(self.root, rec)['passed'])


class ProvenanceLabelTests(AgentFixture):
    def test_console_separates_live_reasoning_from_simulated_curb_data(self):
        page, script = (ROOT / 'index.html').read_text(), (ROOT / 'app.js').read_text()
        self.assertIn('Where each result came from', page); self.assertIn('id="provenance"', page)
        for text in ('Live Meta inference', 'Offline simulation: scripted tool choices, no model',
                     'Simulated fixture: not measured by a camera, SAM or any model',
                     'record check, not a booking approval', 'saved by an earlier version'):
            with self.subTest(text=text):
                self.assertIn(text, script)
        self.assertNotIn('curb: simulated fixture`', script)


class SignoffLabelTests(AgentFixture):
    def signed(self):
        rec = self.simulate(CLINIC)
        return approve_run(self.root, rec['run_id'], 'Demo Reviewer')

    def test_new_signoff_uses_no_dispatch_label(self):
        signed = self.signed()
        self.assertEqual(signed['authorization_mode'], 'DEMO_HUMAN_SIGNOFF_NO_DISPATCH')
        self.assertFalse(signed['dispatch_enabled']); self.assertTrue(signed['run_integrity']['passed'])

    def test_integrity_accepts_both_labels_only_after_signoff(self):
        signed = self.signed()
        for label, ok in (('SIMULATED_DISPATCHER_SIGNOFF', True), ('DEMO_HUMAN_SIGNOFF_NO_DISPATCH', True), ('DISPATCH_AUTHORIZED', False), ('NONE', False)):
            with self.subTest(label=label):
                self.assertEqual(checks.audit_integrity(self.root, {**signed, 'authorization_mode': label})['passed'], ok)
        waiting = self.simulate(CLINIC)
        self.assertFalse(checks.audit_integrity(self.root, {**waiting, 'authorization_mode': 'DEMO_HUMAN_SIGNOFF_NO_DISPATCH'})['passed'])

    def test_historical_records_are_unchanged_and_still_verify(self):
        """Published runs keep their original label and audit fingerprints."""
        import hashlib, json
        folder = ROOT / 'docs' / 'evidence' / 'hosted-console-2026-10-29'
        expected = {'run_b2023b2da615466fba74a611b17ec923': '3ef9b71dde864d5ad85997013318e1110b241763d412c2af992866d4a8ff5465',
                    'run_0e228025cdfe4b6397add01fc117c7eb': 'eac7cd674552a2a42d2413a6520d7ba67829219f896730777328746a65465576'}
        readme = (folder / 'README.md').read_text()
        for run_id, digest in expected.items():
            with self.subTest(run_id=run_id):
                record = json.loads((folder / f'{run_id}.json').read_text())
                compact = json.dumps(record, sort_keys=True).encode()  # the documented fingerprint recipe
                self.assertEqual(hashlib.sha256(compact).hexdigest(), digest); self.assertIn(digest, readme)
                self.assertEqual(record['authorization_mode'], 'SIMULATED_DISPATCHER_SIGNOFF')
                self.assertTrue(checks.audit_integrity(ROOT, record)['passed'])
