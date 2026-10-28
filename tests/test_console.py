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
    def test_ui_assets_match(self):
        self.assertEqual((ROOT/'index.html').read_bytes(),(ROOT/'docs/index.html').read_bytes())
        self.assertEqual((ROOT/'app.js').read_bytes(),(ROOT/'docs/app.js').read_bytes())

if __name__=='__main__':unittest.main()
