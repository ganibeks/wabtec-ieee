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

        def without_static(pattern, *args, **kwargs):
            # Exercise the missing-evidence UI even if new static-check results exist.
            return None if pattern == "static_checks_*" else lookup(pattern, *args, **kwargs)

        with patch.object(D, "latest_run", side_effect=without_static):
            app = AppTest.from_file(str(root / "app_virtual_lab.py"), default_timeout=60).run()
        self.assertEqual(len(app.exception), 0, str(app.exception))
        text = "\n".join(item.value for item in app.markdown)
        self.assertIn('<div class="vbig">NO-PASS</div>', text)
        self.assertIn("simulation only, not a hardware decision", text)
        self.assertIn('<div class="tile NO_LIMIT"', text)
        self.assertIn("Turn-on threshold", text)
        captions = "\n".join(item.value for item in app.caption)
        self.assertIn("These checks prevent an overall PASS.", captions)

    def test_marked_ui_clutter_is_removed(self):
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / "app_virtual_lab.py"), default_timeout=60).run()
        self.assertEqual(len(app.exception), 0, str(app.exception))
        text = "\n".join(item.value for item in app.markdown)
        for removed in ("Tester rule:", "DATA: SIMULATED (MATLAB/Simscape)", "STATIC CHECKS", "LIMITS: Wabtec brief"):
            self.assertNotIn(removed, text)
        self.assertIn("simulation only, not a hardware decision", text)
        self.assertNotIn("Excluded runs (never shown as valid)", [item.label for item in app.sidebar.expander])
        self.assertFalse(any("Desat current interruption" in item.value for item in app.warning))
        self.assertFalse(any("SIMULATED data from MATLAB/Simscape" in item.value for item in app.sidebar.caption))


if __name__ == "__main__":
    unittest.main()
