import contextlib
import http.client
import io
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from ui.ui import ConsoleServer
ROOT=Path(__file__).resolve().parent.parent

class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);shutil.copytree(ROOT/'cases',self.root/'cases')
        self.server=ConsoleServer(('127.0.0.1',0),self.root)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join()
    def req(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        h={'Content-Type':'application/json','X-Console-Token':self.server.token}
        if headers:h.update(headers)
        conn.request(method,path,body=json.dumps(body) if body is not None else None,headers=h)
        result=conn.getresponse();data=result.read();status=result.status;conn.close()
        return status,data
    def test_config_has_no_key(self):
        code,data=self.req('GET','/api/config');body=json.loads(data)
        self.assertEqual(code,200);self.assertIn('healthcare-clinic-visit',body['cases']);self.assertNotIn('api_key',body)
    def test_no_arbitrary_file_serving(self):
        for path in ['/.env','/helper','/agent_kit/settings.py','/../.env','/workspace/runs/run_latest.json']:
            with self.subTest(path=path):self.assertEqual(self.req('GET',path)[0],404)
    def test_no_cross_origin_mutations(self):
        self.assertEqual(self.req('POST','/api/run',{}, {'Origin':'https://evil.example'})[0],403)
    def test_bad_host_blocked(self):self.assertEqual(self.req('GET','/api/config',headers={'Host':'evil.example'})[0],403)
    def test_missing_token_blocked(self):self.assertEqual(self.req('POST','/api/run',{}, {'X-Console-Token':''})[0],403)
    def test_stale_token_is_reported_as_expired_session(self):
        code,data=self.req('POST','/api/run',{'case':'healthcare-clinic-visit'},{'X-Console-Token':'token-from-an-earlier-process'})
        self.assertEqual((code,json.loads(data)['code']),(403,'session_expired'))
        self.assertEqual(list((self.root/'workspace').glob('runs/run_*.json')) if (self.root/'workspace').exists() else [],[])
        code,data=self.req('POST','/api/run',{}, {'Origin':'https://evil.example','X-Console-Token':'stale'})
        self.assertEqual(code,403);self.assertNotIn('code',json.loads(data))
    def test_fixed_token_is_used_when_supplied(self):
        server=ConsoleServer(('127.0.0.1',0),self.root,token='fixed-token-value');self.addCleanup(server.server_close)
        self.assertEqual(server.token,'fixed-token-value');self.assertNotEqual(self.server.token,'fixed-token-value')
    def test_invalid_type(self):self.assertEqual(self.req('POST','/api/run',{}, {'Content-Type':'text/plain'})[0],415)
    def test_invalid_body(self):self.assertEqual(self.req('POST','/api/run',[])[0],400)
    def test_run_step_and_approve(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code,data=self.req('POST','/api/run',{'mode':'simulation','case':'healthcare-clinic-visit'})
            rec=json.loads(data);self.assertEqual(code,200);self.assertEqual(rec['turn'],1);self.assertNotIn('messages',rec)
            for _ in range(15):
                if rec['status']!='paused':break
                code,data=self.req('POST','/api/continue',{'run_id':rec['run_id']});self.assertEqual(code,200);rec=json.loads(data)
            self.assertEqual(rec['status'],'awaiting_signoff')
            code,data=self.req('POST','/api/approve',{'run_id':rec['run_id'],'signature':'Demo Reviewer'})
            self.assertEqual(code,200);self.assertFalse(json.loads(data)['dispatch_enabled'])
    def test_concurrent_mutation_refused(self):
        self.server.mutation_lock.acquire()
        try:self.assertEqual(self.req('POST','/api/run',{})[0],409)
        finally:self.server.mutation_lock.release()
    def test_missing_run_returns_404(self):self.assertEqual(self.req('GET','/api/run?id=run_'+('f'*32))[0],404)
    def test_execution_modes_are_visible_radio_controls(self):
        from html.parser import HTMLParser
        class Inputs(HTMLParser):
            def __init__(self):
                super().__init__();self.values=[];self.defaults=[]
            def handle_starttag(self, tag, attrs):
                attrs=dict(attrs)
                if tag=='input' and attrs.get('name')=='execution-mode':
                    if attrs.get('type')!='radio':raise AssertionError('Mode must be a radio input')
                    self.values.append(attrs.get('value'))
                    if 'checked' in attrs:self.defaults.append(attrs.get('value'))
        parser=Inputs();parser.feed((ROOT/'index.html').read_text())
        self.assertEqual(parser.values,['simulation','live'])
        self.assertEqual(parser.defaults,['simulation'])
        self.assertIn('input[name="execution-mode"]:checked',(ROOT/'app.js').read_text())
        self.assertIn('github.io', (ROOT/'app.js').read_text())

    def test_ui_assets_match(self):
        self.assertEqual((ROOT/'index.html').read_bytes(),(ROOT/'ui/index.html').read_bytes())
        page=(ROOT/'docs/index.html').read_text()
        self.assertIn('This public page does not execute inference',page)
        self.assertIn('simulated curb evidence',page)
        self.assertNotIn('id="start"',page)

if __name__=='__main__':unittest.main()
