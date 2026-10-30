"""Optional hosted-adapter checks; no cloud calls or model requests."""
import importlib.util
import os
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

@unittest.skipUnless(importlib.util.find_spec('fastapi') and importlib.util.find_spec('httpx'), 'Optional hosted dependencies not installed')
class HostedConsoleTests(unittest.TestCase):
    def test_gate_and_loopback_proxy(self):
        from fastapi.testclient import TestClient
        from ui.modal_console import create_app
        commits=[]
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'HARVEY_DEMO_PASSWORD':'long-test-password-123'}):
            shutil.copytree(Path(__file__).resolve().parent.parent/'cases',Path(root)/'cases')
            with TestClient(create_app(root,lambda:commits.append(True))) as client:
                self.assertEqual(client.get('/').status_code,401)
                auth=('reviewer','long-test-password-123')
                self.assertEqual(client.get('/',auth=auth).status_code,200)
                self.assertEqual(client.get('/.env',auth=auth).status_code,404)
                self.assertEqual(client.post('/api/run',auth=auth,json={},headers={'Origin':'https://foreign.example'}).status_code,403)
                self.assertEqual(client.post('/api/run',auth=auth,json={}).status_code,403)
                self.assertEqual(client.post('/api/run',auth=auth,content='x'*128001).status_code,413)
                self.assertEqual(client.put('/',auth=auth).status_code,405)
                config=client.get('/api/config',auth=auth).json()
                self.assertNotIn('MODEL_API_KEY',str(config))
                response=client.post('/api/run',auth=auth,json={'case':'healthcare-clinic-visit','mode':'simulation'},headers={'X-Console-Token':config['token'],'Origin':'http://testserver'})
                self.assertEqual(response.status_code,200)
                self.assertFalse(response.json()['model_invoked_in_run'])
                self.assertEqual(response.json()['turn'],1)
                self.assertEqual(len(commits),2)
    def test_token_survives_restart_and_reveals_nothing(self):
        from fastapi.testclient import TestClient
        from ui.modal_console import create_app
        def token(password):
            with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'HARVEY_DEMO_PASSWORD': password}):
                shutil.copytree(Path(__file__).resolve().parent.parent/'cases',Path(root)/'cases')
                with TestClient(create_app(root)) as client:
                    self.assertEqual(client.get('/api/config').status_code,401)
                    return client.get('/api/config',auth=('reviewer',password)).json()['token']
        first,restarted,other=token('long-test-password-123'),token('long-test-password-123'),token('another-password-4567')
        self.assertEqual(first,restarted); self.assertNotEqual(first,other)
        self.assertNotIn('long-test-password-123',first); self.assertGreaterEqual(len(first),40)
    def test_idle_window_keeps_sessions_alive(self):
        source=(Path(__file__).resolve().parent.parent/'modal_console.py').read_text()
        self.assertIn('scaledown_window=900',source); self.assertIn('max_containers=1',source)
    def test_password_required(self):
        from ui.modal_console import create_app
        with patch.dict(os.environ,{'HARVEY_DEMO_PASSWORD':''}):
            with self.assertRaises(ValueError):create_app('.')
