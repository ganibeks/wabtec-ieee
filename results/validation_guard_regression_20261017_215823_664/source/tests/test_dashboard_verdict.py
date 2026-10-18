"""Targeted Streamlit integration check using saved MATLAB data only."""
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from virtual_lab import datasets as D


class DashboardVerdictRegression(unittest.TestCase):
    def test_missing_evidence_is_visible_and_prevents_headline_pass(self):
        root = Path(__file__).resolve().parents[1]
        lookup = D.latest_run

        def without_desat(pattern, *args, **kwargs):
            # Exercise the missing-evidence UI even if new DESAT results exist.
            return None if pattern == "desat_test_*" else lookup(pattern, *args, **kwargs)

        with patch.object(D, "latest_run", side_effect=without_desat):
            app = AppTest.from_file(str(root / "app_virtual_lab.py"), default_timeout=60).run()
        self.assertEqual(len(app.exception), 0, str(app.exception))
        text = "\n".join(item.value for item in app.markdown)
        self.assertIn('<div class="vbig">NO-PASS</div>', text)
        self.assertIn("Hardware decision: <b>INCONCLUSIVE</b>", text)
        self.assertIn('<div class="tile NOT_TESTED"', text)
        self.assertIn("Desat turn-off", text)
        captions = "\n".join(item.value for item in app.caption)
        self.assertIn("These checks prevent an overall PASS.", captions)


if __name__ == "__main__":
    unittest.main()
