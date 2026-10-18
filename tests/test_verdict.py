"""Regression tests for incomplete electrical evidence; no simulations are run."""
import unittest
from dataclasses import replace

from virtual_lab import datasets as D
from virtual_lab import tester as T


def complete_tiles():
    # Synthetic logic fixtures, never displayed as device measurements.
    return [T.Tile(key, label, unit, 1.0, "IN_LIMIT", "test fixture", "", "SIMULATED")
            for key, label, unit in T.SLIDE_TILES]


class VerdictRegression(unittest.TestCase):
    def test_missing_required_check_cannot_pass(self):
        tiles = [t for t in complete_tiles() if t.key != "vth"]
        result = T.verdict(tiles, "SLIDE")
        self.assertEqual(result["reason"], "NOT VERIFIED")
        self.assertIn("Turn-on threshold", result["unverified"])
        self.assertEqual(result["hardware_decision"], "INCONCLUSIVE")

    def test_excluded_check_is_reported_not_hidden(self):
        # Team decision 2026-10-18: DESAT turn-off is simulated but excluded from the verdict (model tail
        # limitation). It must stay out of the required set, keep its slide limit and still show its result.
        self.assertNotIn("protection", [k for k, _, _ in T.SLIDE_TILES])
        traction = [d for d in D.discover() if d.selectable and d.id == "traction_rl"]
        if not traction or D.latest_run("desat_test_*", traction[0].params.get("schema", "")) is None:
            self.skipTest("No traction DESAT run available")
        (tile,) = T.excluded_tiles_from_sim(traction[0])
        self.assertEqual(tile.key, "protection")
        self.assertIn("10 µs", tile.limit)
        self.assertEqual(tile.state, "IN_LIMIT" if tile.value <= 10 else "OUT_OF_LIMIT")
        self.assertIn("Excluded from verdict", tile.note)

    def test_pending_or_unbounded_check_cannot_pass(self):
        for state in ("NOT_TESTED", "NO_LIMIT", "UNRECOGNIZED"):
            with self.subTest(state=state):
                tiles = complete_tiles()
                tiles[0] = replace(tiles[0], state=state)
                self.assertEqual(T.verdict(tiles, "SLIDE")["reason"], "NOT VERIFIED")

    def test_nonfinite_or_missing_value_cannot_pass(self):
        for value in (None, float("nan"), float("inf")):
            with self.subTest(value=value):
                tiles = complete_tiles()
                tiles[0] = replace(tiles[0], value=value)
                self.assertEqual(T.verdict(tiles, "SLIDE")["reason"], "NOT VERIFIED")

    def test_empty_set_cannot_pass(self):
        self.assertEqual(T.verdict([], "SLIDE")["verdict"], "NO-PASS")

    def test_failed_check_remains_failed_even_with_pending_checks(self):
        tiles = complete_tiles()
        tiles[0] = replace(tiles[0], state="OUT_OF_LIMIT")
        tiles[-1] = replace(tiles[-1], state="NO_LIMIT")
        result = T.verdict(tiles, "SLIDE")
        self.assertEqual(result["reason"], "FAILED")
        self.assertEqual(result["verdict"], "NO-PASS")

    def test_complete_simulated_checks_do_not_certify_hardware(self):
        result = T.verdict(complete_tiles(), "SLIDE")
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["hardware_decision"], "INCONCLUSIVE")

    def test_demo_limits_remain_demo(self):
        result = T.verdict(complete_tiles(), "DEMO")
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["hardware_decision"], "INCONCLUSIVE")

    def test_saved_rl_records_with_missing_evidence_cannot_pass(self):
        datasets = [d for d in D.discover() if d.selectable and d.id in ("dynamic_rl", "traction_rl")]
        self.assertTrue(datasets, "No saved RL data available for regression")
        for ds in datasets:
            with self.subTest(dataset=ds.id):
                tiles = T.tiles_from_sim(ds)
                # Withhold threshold evidence explicitly so later static runs do
                # not change the regression's missing-evidence precondition.
                tiles = [replace(t, state="NOT_TESTED", value=None) if t.key == "vth" else t
                         for t in tiles]
                checked, pending = T.split_simulated(tiles)
                self.assertTrue(pending)
                self.assertEqual(T.verdict(tiles, "SLIDE")["verdict"], "NO-PASS")
                # Regression for the former app path: even a filtered subset must not pass.
                self.assertEqual(T.verdict(checked, "SLIDE")["verdict"], "NO-PASS")


if __name__ == "__main__":
    unittest.main()
