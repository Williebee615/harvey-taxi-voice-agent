"""Offline contract tests with a fake Responses transport; never call paid APIs."""
import contextlib
import copy
import io
import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from agent_kit import client, document_text, evidence, progress, settings, tools
from legal_agent.loop import run_agent, resume_run, approve_run, _simulation_calls
from verification import checks

ROOT = Path(__file__).resolve().parent.parent
SAFE = 'harvey-taxi-ada-doctor-visit'


class FakeAPI:
    def __init__(self, calls):
        self.calls = list(calls)
        self.inputs = []
        self.responses = SimpleNamespace(create=self.create)
    def create(self, **kwargs):
        self.inputs.append(copy.deepcopy(kwargs))
        if not self.calls:
            raise AssertionError('Unexpected extra model call')
        item = self.calls.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, dict):
            return item
        name, args = item
        n = len(self.inputs)
        return {'id': f'resp_{n}', 'model': 'muse-spark-1.3', 'status': 'completed',
                'output': [{'type': 'function_call', 'name': name, 'arguments': json.dumps(args), 'call_id': f'call_{n}'}],
                'usage': {'total_tokens': 30}}


class AgentFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / 'cases', self.root / 'cases')
        self.stdout = contextlib.redirect_stdout(io.StringIO())
        self.stdout.__enter__()
        self.addCleanup(self.stdout.__exit__, None, None, None)
    def simulate(self, case=SAFE, **kwargs):
        return run_agent(self.root, case_name=case, **kwargs)
    def write(self, doc, text, case=SAFE):
        (self.root/'cases'/case/'inbox'/doc).write_text(text)
    def call(self, rec, name, args):
        return tools.run(None, self.root, rec['run_id'], {'name':name,'arguments':json.dumps(args)}, record=rec)
    def rec(self):
        return progress.new_record(SAFE, 'Verify', 'live', settings.model())


class AgentTests(AgentFixture):
    def test_fares(self):
        for miles, expected in [(0,2.5),(6,11.5),(15,25),(1.23,4.35)]:
            with self.subTest(miles=miles): self.assertEqual(settings.calculate_verified_fare(miles)['total_fare'], expected)
    def test_nonfinite_negative_mileage(self):
        for v in [-1,float('nan'),float('inf'),True]:
            with self.subTest(value=v),self.assertRaises(ValueError):settings.calculate_verified_fare(v)
    def test_fare_and_surcharge(self):
        self.assertTrue(checks.verify_fare_invariant(6,11.5)['passed'])
        self.assertFalse(checks.verify_fare_invariant(6,26.5,15)['passed'])
        self.assertFalse(checks.verify_fare_invariant(6,float('nan'))['passed'])
    def test_nonfinite_curb(self):
        for x in [None,True,float('nan'),float('inf'),10**1000,6.1]:self.assertFalse(checks.verify_curb_safety(x)['passed'])
        self.assertTrue(checks.verify_curb_safety(9.4)['passed'])
    def test_exact_quote_only(self):
        quote='$2.50 base component plus $1.50 per verified mile.'
        self.assertTrue(document_text.verify_quote(self.root,'HANDBOOK.md',1,quote))
        self.assertFalse(document_text.verify_quote(self.root,'HANDBOOK.md',1,'This is fabricated and long enough'))
        self.assertFalse(document_text.verify_quote(self.root,'HANDBOOK.md',2,quote))
        self.assertFalse(document_text.verify_quote(self.root,'unknown',1,'anything'))
    def test_empty_quote_rejected(self):self.assertFalse(checks.verify_fact_quote('  ','  '))
    def test_unknown_case(self):
        with self.assertRaises(ValueError): self.simulate('does-not-exist')
    def test_case_traversal(self):
        for value in ['../cases', '/tmp', 'safe/../bad']:
            with self.assertRaises(ValueError):self.simulate(value)
    def test_symlink_case_blocked(self):
        (self.root/'cases'/'alias').symlink_to(self.root/'cases'/SAFE,target_is_directory=True)
        with self.assertRaises(ValueError):self.simulate('alias')
    def test_hidden_files_not_evidence(self):
        self.write('.env','SECRET=hidden');self.assertNotIn('.env',evidence.documents(self.root,SAFE))
    def test_safe_simulation(self):
        rec=self.simulate();self.assertEqual(rec['status'],'awaiting_signoff');self.assertFalse(rec['model_invoked_in_run']);self.assertEqual(rec['receipts'],[])
    def test_no_network_in_simulation(self):
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Network forbidden')):self.simulate()
    def test_all_negative_fixtures(self):
        for case in ['harvey-taxi-incomplete-intake','harvey-taxi-unsafe-curb-boarding','harvey-taxi-wrong-fare-drift','harvey-taxi-contradictory-evidence']:
            with self.subTest(case=case):self.assertEqual(self.simulate(case)['status'],'needs_input')
    def test_missing_distance_not_defaulted(self):
        self.write('rider_intake.txt','Rider: Changed rider\nPickup: Here\nDropoff: There\nPickup Time: Tomorrow\nQuoted Fare: $11.50')
        rec=self.simulate();self.assertEqual(rec['status'],'needs_input');self.assertFalse(rec['verification']['fare_check']['passed'])
    def test_missing_telemetry_not_defaulted(self):
        self.write('sam3_curb_telemetry.json','{}');self.assertEqual(self.simulate()['status'],'needs_input')
    def test_invalid_telemetry(self):
        for data in ['not json','[]','{"north_bay": {"clearance_ft": NaN}}','{"selected_bay":"north_bay","north_bay":null}']:
            self.write('sam3_curb_telemetry.json',data);self.assertEqual(self.simulate()['status'],'needs_input')
    def test_false_safety_flag_rejected(self):
        data=json.loads(evidence.documents(self.root,SAFE)['sam3_curb_telemetry.json']);data['north_bay']['safe_for_ramp']=False
        self.write('sam3_curb_telemetry.json',json.dumps(data));self.assertEqual(self.simulate()['status'],'needs_input')
    def test_missing_policy(self):
        self.write('HANDBOOK.md','Different policy');self.assertEqual(self.simulate()['status'],'needs_input')
    def test_actual_rider_used(self):
        text=evidence.documents(self.root,SAFE)['rider_intake.txt'].replace('Evelyn Carter','Taylor Morgan')
        self.write('rider_intake.txt',text);self.assertEqual(self.simulate()['booking']['rider'],'Taylor Morgan')
    def test_cli_help_has_no_run_side_effect(self):
        import subprocess
        output=subprocess.check_output([str(ROOT/'helper'),'--help'],text=True)
        self.assertIn('validate-models',output);self.assertNotIn('[turn',output)
    def test_invalid_turn_limits(self):
        for turns in [0,41,True]:
            with self.assertRaises(ValueError):self.simulate(turns=turns)
    def test_simulation_resume_same_run(self):
        rec=self.simulate(turns=1);self.assertEqual(rec['status'],'paused')
        nxt=resume_run(self.root,rec['run_id'],turns=20);self.assertEqual(nxt['run_id'],rec['run_id']);self.assertEqual(nxt['status'],'awaiting_signoff')
    def test_independent_runs_do_not_clobber(self):
        a=self.simulate();b=self.simulate('harvey-taxi-incomplete-intake')
        self.assertNotEqual(a['run_id'],b['run_id']);self.assertEqual(progress.load_progress(self.root,a['run_id'])['status'],'awaiting_signoff')
    def test_signoff_named_run(self):
        a=self.simulate();self.simulate('harvey-taxi-incomplete-intake')
        result=approve_run(self.root,a['run_id'],'Demo Reviewer');self.assertEqual(result['status'],'completed_after_human_signoff');self.assertFalse(result['dispatch_enabled'])
    def test_no_approval_for_needs_input(self):
        a=self.simulate('harvey-taxi-incomplete-intake')
        with self.assertRaises(ValueError):approve_run(self.root,a['run_id'],'Reviewer')
    def test_no_approval_without_reviewer(self):
        a=self.simulate()
        with self.assertRaises(ValueError):approve_run(self.root,a['run_id'],'')
    def test_changed_evidence_blocks_signoff(self):
        a=self.simulate();self.write('rider_intake.txt',evidence.documents(self.root,SAFE)['rider_intake.txt']+'\nChanged details')
        with self.assertRaises(ValueError):approve_run(self.root,a['run_id'],'Reviewer')
    def test_run_id_traversal(self):
        with self.assertRaises(ValueError):progress.load_progress(self.root,'../../.env')
    def test_schema_and_unknown_tool_rejected(self):
        for name,args in [('dispatch',{}),('set_checklist',{'items':['bad']}),('record_fact',{'quote':'bad'})]:
            self.assertIn('error',self.call(self.rec(),name,args))
    def test_fake_quote_tool_rejected(self):
        rec=self.rec();rec['checklist']=[{'id':'q','question':'Question'}];rec['read_documents']=['HANDBOOK.md']
        self.assertIn('error',self.call(rec,'record_fact',{'item':'q','document':'HANDBOOK.md','quote':'Fabrication long enough','claim':'Wrong'}));self.assertEqual(rec['facts'],[])
    def test_memo_without_citations_rejected(self):
        rec=self.rec();self.call(rec,'verify_booking',{});rec['checklist']=[{'id':'q','question':'Question'}]
        self.assertIn('error',self.call(rec,'submit_memo',{'answer':'Yes','findings':[{'item':'q','finding':'Fine','fact_ids':[]}],'gaps':[]}))
    def test_live_loop_selects_tools_and_replays(self):
        rec=self.rec();calls=_simulation_calls(self.root,rec);api=FakeAPI(calls)
        out=run_agent(self.root,case_name=SAFE,mode='live',api=api)
        self.assertEqual(out['status'],'awaiting_signoff');self.assertTrue(out['model_invoked_in_run']);self.assertEqual(out['inference_mode'],'LIVE_META_API')
        self.assertEqual(len(out['receipts']),len(calls));self.assertTrue(any(m.get('type')=='function_call_output' for m in api.inputs[1]['input']))
    def test_api_failure_pauses_without_fallback(self):
        api=FakeAPI([client.ModelError('Meta HTTP 401')]);rec=run_agent(self.root,mode='live',api=api)
        self.assertEqual(rec['status'],'paused');self.assertFalse(rec['model_invoked_in_run']);self.assertEqual(rec['inference_mode'],'NOT_INVOKED');self.assertEqual(rec['turns'][0]['tool'],'api_error')
    def test_no_calls_when_no_new_evidence(self):
        rec=self.simulate('harvey-taxi-incomplete-intake');api=FakeAPI([])
        self.assertEqual(resume_run(self.root,rec['run_id'],api=api)['status'],'needs_input');self.assertEqual(api.inputs,[])
    def test_no_calls_after_awaiting_signoff(self):
        rec=self.simulate();api=FakeAPI([]);resume_run(self.root,rec['run_id'],api=api);self.assertEqual(api.inputs,[])
    def test_multiple_tools_are_not_executed(self):
        response={'id':'r','model':'m','output':[{'type':'function_call','call_id':'a','name':'request_evidence','arguments':'{"missing":["x"]}'},{'type':'function_call','call_id':'b','name':'submit_memo','arguments':'{}'}]}
        rec=run_agent(self.root,mode='live',turns=1,api=FakeAPI([response]));self.assertEqual(rec['turns'][0]['tool'],'no_tool_executed');self.assertIsNone(rec['memo'])
    def test_no_plaintext_answer_as_completion(self):
        response={'id':'r','model':'m','output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':'Approved!'}]}]}
        rec=run_agent(self.root,mode='live',turns=1,api=FakeAPI([response]));self.assertEqual(rec['status'],'paused');self.assertIsNone(rec['memo'])
    def test_public_record_hides_replay(self):
        rec=self.rec();rec['messages'].append({'encrypted_content':'PRIVATE_REPLAY'});self.assertNotIn('messages',progress.public_record(rec))
    def test_meta_provider_never_uses_fireworks_key(self):
        with patch.dict('os.environ',{'MODEL_API_KEY':'meta-test','FIREWORKS_API_KEY':'fw-test'},clear=True):self.assertEqual(settings.api_key(),'meta-test');self.assertEqual(settings.base_url(),'https://api.meta.ai/v1')
    def test_env_aliases(self):
        with patch.dict('os.environ',{'META_MODEL':'muse-spark-1.3','META_BASE_URL':'https://api.meta.ai/v1'},clear=True):self.assertEqual(settings.model(),'muse-spark-1.3');self.assertEqual(settings.base_url(),'https://api.meta.ai/v1')
    def test_invalid_base_blocks_credentials(self):
        with patch.dict('os.environ',{'MODEL_API_KEY':'secret','MODEL_API_BASE':'https://evil.example'},clear=True),self.assertRaises(client.ModelError):client.Responses().create(model='m',instructions='',input=[],tools=[])
    def test_model_error_never_exposes_remote_body(self):
        import urllib.error
        error=urllib.error.HTTPError('url',401,'secret',{},io.BytesIO(b'SECRET'))
        with patch.dict('os.environ',{'MODEL_API_KEY':'secret'},clear=True),patch('urllib.request.OpenerDirector.open',side_effect=error):
            with self.assertRaisesRegex(client.ModelError,'HTTP 401') as captured:client.Responses().create(model='m',instructions='',input=[],tools=[])
        self.assertNotIn('SECRET',str(captured.exception))
    def test_client_payload_and_receipt(self):
        fake=io.BytesIO(json.dumps({'id':'resp','model':'muse-spark-1.3','status':'completed','output':[]}).encode())
        with patch.dict('os.environ',{'MODEL_API_KEY':'secret'},clear=True),patch('urllib.request.OpenerDirector.open',return_value=fake) as opened:
            out=client.Responses().create(model='muse-spark-1.3',instructions='instructions',input=[],tools=tools.definitions())
            payload=json.loads(opened.call_args.args[0].data);self.assertFalse(payload['store']);self.assertFalse(payload['parallel_tool_calls']);self.assertEqual(payload['tool_choice'],'auto');self.assertEqual(out['id'],'resp')
    def test_no_fake_web_evidence(self):
        from agent_kit.web_domains import inspect_domain
        with self.assertRaises(ValueError):inspect_domain('example.com')
    def test_healthcare_safe_case(self):self.assertEqual(self.simulate('healthcare-clinic-visit')['status'],'awaiting_signoff')
    def test_healthcare_missing_return_plan(self):self.assertEqual(self.simulate('healthcare-missing-return-plan')['status'],'needs_input')
    def test_healthcare_clinical_support_escalated(self):self.assertEqual(self.simulate('healthcare-clinical-support')['status'],'needs_input')


class AdditionalContracts(AgentFixture):
    def test_followup_rechecks_updated_source(self):
        case='healthcare-missing-return-plan'
        api=FakeAPI([('request_evidence',{'missing':['Return Plan']})])
        rec=run_agent(self.root,case_name=case,mode='live',api=api)
        text=evidence.documents(self.root,case)['rider_intake.txt'].replace('MISSING_RETURN_PLAN','Coordinator will arrange pickup and a supervised waiting location')
        self.write('rider_intake.txt',text,case)
        spec=self.rec();spec['case']=case
        result=resume_run(self.root,rec['run_id'],message='Return plan updated in the source file.',api=FakeAPI(_simulation_calls(self.root,spec)))
        self.assertEqual(result['status'],'awaiting_signoff');self.assertEqual(result['run_id'],rec['run_id'])
    def test_stale_fact_citations_refused(self):
        rec=self.simulate();self.write('rider_intake.txt',evidence.documents(self.root,SAFE)['rider_intake.txt']+'\nExtra source text')
        result=self.call(rec,'submit_memo',{'answer':rec['memo']['answer'],'findings':rec['memo']['findings'],'gaps':[]})
        self.assertNotEqual(result['status'],'awaiting_signoff')
    def test_no_report_without_record(self):
        from agent_kit.pdf_export import generate_report
        with self.assertRaises(ValueError):generate_report(self.root)
    def test_incomplete_provider_response_not_executed(self):
        fake=io.BytesIO(json.dumps({'id':'resp','model':'m','status':'incomplete','output':[]}).encode())
        with patch.dict('os.environ',{'MODEL_API_KEY':'secret'},clear=True),patch('urllib.request.OpenerDirector.open',return_value=fake),self.assertRaises(client.ModelError):
            client.Responses().create(model='m',instructions='',input=[],tools=[])

if __name__=='__main__':
    unittest.main()
