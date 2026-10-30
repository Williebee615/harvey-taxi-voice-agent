"""The post-deploy check script passes against a local copy of the hosted app and makes no Meta calls."""
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(all(importlib.util.find_spec(m) for m in ('fastapi', 'httpx', 'uvicorn')), 'Optional hosted dependencies not installed')
class HostedCheckTests(unittest.TestCase):
    def test_check_script_passes_offline_and_never_goes_live(self):
        import uvicorn
        from ui.modal_console import create_app
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'HARVEY_DEMO_PASSWORD': 'local-test-password-1234'}):
            shutil.copytree(ROOT / 'cases', Path(root) / 'cases')
            (Path(root) / 'workspace' / 'runs').mkdir(parents=True)
            for run in (ROOT / 'docs/evidence/hosted-console-2026-10-29').glob('run_*.json'):
                shutil.copy(run, Path(root) / 'workspace' / 'runs')
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(create_app(root), host='127.0.0.1', port=port, log_level='error'))
            thread = threading.Thread(target=server.run, daemon=True); thread.start()
            self.addCleanup(lambda: (setattr(server, 'should_exit', True), thread.join(5)))
            while not server.started:
                time.sleep(0.05)
            env = {**os.environ, 'CONSOLEPW': 'local-test-password-1234', 'NO_PROXY': '*', 'no_proxy': '*'}
            env.pop('MODEL_API_KEY', None)
            script = [sys.executable, str(ROOT / 'audit' / 'hosted_check.py'), f'http://127.0.0.1:{port}']
            done = subprocess.run(script, capture_output=True, text=True, timeout=120, env=env)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            result = json.loads(done.stdout)
            self.assertEqual((result['no_password'], result['wrong_password'], result['signed_in'], result['stale_token']), (401, 401, 200, 403))
            self.assertEqual((result['take1_appointment_card']['meta_calls'], result['take2_card_contradiction']['meta_calls']), (0, 0))
            self.assertEqual(set(result['earlier_runs'].values()), {'completed_after_human_signoff'})
            self.assertNotIn('local-test-password-1234', done.stdout + done.stderr)
            self.assertNotEqual(subprocess.run(script, capture_output=True, text=True, timeout=60, env={**env, 'CONSOLEPW': 'short'}).returncode, 0)
