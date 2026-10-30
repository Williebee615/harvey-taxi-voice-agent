"""Console labels and remembered mode. The browser check answers every API request from local fixtures; no paid calls."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ConsoleLabelTests(unittest.TestCase):
    def test_label_wording_is_precise(self):
        page, script = (ROOT / 'index.html').read_text(), (ROOT / 'app.js').read_text()
        self.assertEqual(page, (ROOT / 'ui' / 'index.html').read_text())
        for text in ('LIVE META INFERENCE — ', 'RECORDED RESPONSE', 'not independently authenticated with Meta',
                     'OFFLINE SIMULATION — NO META API CALLS', 'SIMULATED CURB MEASUREMENTS — Demonstration data, not camera measurements',
                     'HUMAN ACKNOWLEDGMENT RECORDED — No vehicle dispatched', 'No payment authorized', 'paid API calls'):
            with self.subTest(text=text):
                self.assertIn(text, script)
        self.assertNotIn('VERIFIED API RESPONSES', script.upper())
        self.assertIn('No vehicle is dispatched and no payment is authorized', page)
        self.assertIn('id="paid-note"', page)

    def test_remembered_mode_never_starts_a_review(self):
        script = (ROOT / 'app.js').read_text()
        self.assertIn("localStorage.setItem(MODE_KEY", script)
        self.assertEqual(script.count("perform('/api/run'"), 1)
        self.assertIn("$('start').onclick=guarded(async()=>{automatic=false;", script)


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class ConsoleBrowserTests(unittest.TestCase):
    def test_mode_persistence_and_badges_in_a_browser(self):
        probe = subprocess.run(['node', '-e', "require('playwright')"], cwd=ROOT, capture_output=True)
        if probe.returncode:
            self.skipTest('playwright is not available to node')
        done = subprocess.run(['node', str(ROOT / 'tests' / 'console_browser.js'), str(ROOT)], capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        out = json.loads(done.stdout)
        self.assertFalse(out['initial']['live']); self.assertTrue(out['initial']['paidHidden'])
        self.assertIn('Start offline simulation (no API calls)', out['initial']['start'])
        self.assertTrue(out['afterReload']['live'], 'Live Meta should be remembered after a refresh')
        self.assertFalse(out['afterReload']['paidHidden']); self.assertIn('paid API calls', out['afterReload']['start'])
        self.assertIsNone(out['afterReload']['badge'], 'No inference label before a run exists')
        self.assertEqual(out['posts'], [], 'Loading or refreshing the console must not start a review')
        self.assertIn('LIVE META INFERENCE — 24 RECORDED RESPONSES', out['liveRun']['badge'])
        self.assertIn('not independently authenticated with Meta', out['liveRun']['badge'])
        self.assertIn('HUMAN ACKNOWLEDGMENT RECORDED — No vehicle dispatched', out['liveRun']['signoff'])
        self.assertIn('SIMULATED CURB MEASUREMENTS', out['liveRun']['checks'])
        self.assertIn('OFFLINE SIMULATION — NO META API CALLS', out['simRun']['badge'])
        self.assertIsNone(out['simRun']['signoff'])
        self.assertFalse(out['backToSimulation']['live'])
        expired = out['expired']
        self.assertIn('The review was not started; no Meta call was made', expired['notice'])
        self.assertEqual(expired['configRefetched'], 1, 'The page should fetch a fresh token once')
        self.assertEqual(expired['runPosts'], 1, 'The page must not retry a review on its own')
        self.assertTrue(expired['startEnabled'])
