"""The audit's safeguard demonstration stays true: offline, stand-in model, real checks."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'audit'))
import safeguards_demo  # noqa: E402


class SafeguardDemoTests(unittest.TestCase):
    def test_bad_inputs_are_blocked(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            safeguards_demo.main()
        text = out.getvalue()
        self.assertIn('fare_check: passed=False', text)
        self.assertIn('Accessibility surcharge must be $0.00', text)
        self.assertIn('Spoken request mentions service animal, but the rider intake does not record it', text)
        self.assertEqual(text.count('Quote must occur exactly in a source document read in this run'), 2)
        self.assertEqual(text.count('memo accepted: False'), 3)
        self.assertEqual(text.count('human sign-off: refused'), 3)
        self.assertNotIn('ACCEPTED', text)
