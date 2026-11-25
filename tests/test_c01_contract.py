"""Independent tiny arithmetic/source fixtures; no NBA data or fitted models."""
from copy import deepcopy
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from analysis.c01_core import (
    ContractError, distribution, participation, probability_score, reference_crps,
    require_pre_tip, require_prior, score, validate_box, validate_events, validate_minutes,
)
from analysis.c01_workbench import create_json, digest, read_panel
from analysis import c01_workbench as workbench
from basketball_common import sha256_file


def accounting_fixture(periods=4, technical=0):
    """Hand construction: one two-point and one three-point basket per period.

    Five players play every second on each team, plus explicit DNP and unknown
    roster entries. A technical point is scored outside segment possession IDs.
    These intentionally tiny games are arithmetic cases, not simulated NBA truth.
    """
    fives = {"1": [str(i) for i in range(11, 16)], "2": [str(i) for i in range(21, 26)]}
    events = []
    for p in range(1, periods + 1):
        length = 720 if p <= 4 else 300
        for side, off in enumerate(("1", "2")):
            events.append({"game_id": "100", "event_index": len(events), "period": p,
                           "poss": len(events), "offense": off, "defense": "2" if off == "1" else "1",
                           "start_clock": length * (1 - side / 2), "action_clock": length * (1 - (side + 1) / 2),
                           "end_clock": length * (1 - (side + 1) / 2), "lineup_off": fives[off],
                           "lineup_def": fives["2" if off == "1" else "1"], "actor": fives[off][0],
                           "points": 2 if off == "1" else 3})
    players = []
    for team, ids in fives.items():
        for i, pid in enumerate(ids):
            shooter = i == 0
            three = team == "2"
            ft = technical if shooter and not three else 0
            players.append({"game_id": "100", "team": team, "player": pid, "dnp": False,
                            "minutes": 48 + 5 * (periods - 4), "pts": (3 if three else 2) * periods * shooter + ft,
                            "fgm": periods * shooter, "fga": periods * shooter,
                            "fg3m": periods * shooter * three, "fg3a": periods * shooter * three,
                            "ftm": ft, "fta": ft, "reb": 0, "oreb": 0, "dreb": 0})
    points = {"1": 2 * periods + technical, "2": 3 * periods}
    return players, events, points


class IndependentAccountingTests(unittest.TestCase):
    def test_regulation_hand_totals_and_exact_minutes(self):
        players, events, points = accounting_fixture()
        self.assertEqual(points, {"1": 8, "2": 12})
        self.assertEqual(validate_box(players, points), points)
        self.assertEqual(validate_minutes(players, ["1", "2"], 4), {"1": 240, "2": 240})
        result = validate_events(events, ["1", "2"], 4, points, {"1": 0, "2": 0})
        self.assertEqual(result, {"points": points, "possessions": {"1": 4, "2": 4}, "team_minutes": 240})

    def test_overtime_is_300_seconds_and_adds_25_team_minutes(self):
        players, events, points = accounting_fixture(5)
        self.assertEqual(points, {"1": 10, "2": 15})
        self.assertEqual(validate_minutes(players, ["1", "2"], 5), {"1": 265, "2": 265})
        self.assertEqual(validate_events(events, ["1", "2"], 5, points, {"1": 0, "2": 0})["team_minutes"], 265)
        events[-1]["start_clock"] = 360
        with self.assertRaisesRegex(ContractError, "clock"):
            validate_events(events, ["1", "2"], 5, points, {"1": 0, "2": 0})

    def test_technical_ft_has_no_extra_possession_and_must_be_evidenced(self):
        players, events, points = accounting_fixture(technical=1)
        validate_box(players, points)
        self.assertEqual(validate_events(events, ["1", "2"], 4, points, {"1": 1, "2": 0})["possessions"], {"1": 4, "2": 4})
        with self.assertRaisesRegex(ContractError, "other points identity"):
            validate_events(events, ["1", "2"], 4, points, {"1": 0, "2": 0})

    def test_dnp_unknown_and_conflicts_stay_different(self):
        self.assertEqual(participation(True, 0, [0]), "dnp")
        self.assertEqual(participation(True, None, [None]), "dnp")
        self.assertEqual(participation(None, None, [0]), "unknown")
        self.assertEqual(participation(False, 0, [0]), "unknown")
        self.assertEqual(participation(False, 2, [1]), "played")
        for minute, counts in [(1, [0]), (None, [1]), (0, [1])]:
            with self.assertRaisesRegex(ContractError, "DNP contradicts"):
                participation(True, minute, counts)

    def test_explicit_dnp_blank_box_does_not_exclude_game_unknown_stays_missing(self):
        players, _, points = accounting_fixture()
        blank = {k: float("nan") for k in ("pts", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "reb", "oreb", "dreb")}
        dnp = {**blank, "game_id": "100", "team": "1", "player": "16", "minutes": None, "dnp": True}
        self.assertEqual(validate_box(players + [dnp], points), points)
        with self.assertRaisesRegex(ContractError, "box counts"):
            validate_box(players + [{**dnp, "dnp": None}], points)
        with self.assertRaisesRegex(ContractError, "DNP contradicts"):
            validate_box(players + [{**dnp, "pts": 1}], points)

    def test_scoring_and_rebound_corruption_fail_at_source_boundary(self):
        players, _, points = accounting_fixture()
        players[0]["pts"] += 1
        with self.assertRaisesRegex(ContractError, "scoring identity"):
            validate_box(players, points)
        players[0]["pts"] -= 1
        players[0]["reb"] = 1
        with self.assertRaisesRegex(ContractError, "rebound identity"):
            validate_box(players, points)

    def test_duplicate_foreign_player_and_event_ids_fail(self):
        players, events, points = accounting_fixture()
        with self.assertRaisesRegex(ContractError, "duplicate key"):
            validate_box(players + [deepcopy(players[0])], points)
        bad = deepcopy(players)
        bad[-1]["player"] = bad[0]["player"]
        with self.assertRaisesRegex(ContractError, "duplicate key"):
            validate_box(bad, points)
        for field, value in [("event_index", events[0]["event_index"]), ("defense", "2"), ("actor", "999")]:
            bad = deepcopy(events)
            bad[-1][field] = value
            with self.assertRaises(ContractError):
                validate_events(bad, ["1", "2"], 4, points, {"1": 0, "2": 0})

    def test_clock_gaps_period_gaps_and_duplicate_fives_fail(self):
        _, events, points = accounting_fixture()
        for field, value in [("start_clock", 719), ("end_clock", -1), ("action_clock", 800),
                             ("lineup_off", ["11"] * 5), ("period", 6), ("poss", 1)]:
            bad = deepcopy(events)
            bad[0][field] = value
            with self.assertRaises(ContractError):
                validate_events(bad, ["1", "2"], 4, points, {"1": 0, "2": 0})
        with self.assertRaisesRegex(ContractError, "incomplete"):
            validate_events(events[:-2], ["1", "2"], 4, points, {"1": 0, "2": 0})

    def test_minutes_corruption_and_unknown_do_not_get_rescaled(self):
        players, _, _ = accounting_fixture()
        players[0]["minutes"] -= 1
        with self.assertRaisesRegex(ContractError, "team minutes identity"):
            validate_minutes(players, ["1", "2"], 4)
        players[0]["minutes"] = None
        with self.assertRaisesRegex(ContractError, "unknown reconstructed"):
            validate_minutes(players, ["1", "2"], 4)


class IndependentScoringTests(unittest.TestCase):
    def test_hand_weighted_score_and_outside_support(self):
        # P(X=0)=1/4, P(X=2)=3/4: E|X-1|=1, E|X-X'|/2=3/8.
        self.assertEqual(score([0, 2], 1, [.25, .75])["crps"], .625)
        self.assertEqual(score([0, 2], 10, [.25, .75])["crps"], 8.125)
        self.assertEqual(score([0, 2], -10, [.25, .75])["crps"], 11.125)

    def test_perfect_known_bad_and_self_comparison(self):
        perfect, bad = score([5, 5], 5), score([15, 15], 5)
        self.assertEqual(perfect["crps"], 0)
        self.assertEqual(bad["crps"], 10)
        self.assertLess(perfect["crps"], bad["crps"])
        self.assertEqual(score([1, 2, 3], 2)["crps"] - score([1, 2, 3], 2)["crps"], 0)

    def test_independent_pairwise_reference_and_metamorphic_properties(self):
        rng = np.random.default_rng(14)
        for _ in range(100):
            values = rng.normal(size=9)
            weights = rng.dirichlet(np.ones(9))
            y = float(rng.normal())
            result = score(values, y, weights)["crps"]
            self.assertAlmostEqual(result, reference_crps(values, y, weights), places=12)
            self.assertAlmostEqual(result, score(values + 100, y + 100, weights)["crps"], places=12)
            self.assertAlmostEqual(result * 3, score(values * 3, y * 3, weights)["crps"], places=12)
            order = rng.permutation(9)
            self.assertAlmostEqual(result, score(values[order], y, weights[order])["crps"], places=12)

    def test_missing_is_unsupported_and_bad_distributions_raise(self):
        for y in (None, float("nan")):
            self.assertEqual(score([0, 1], y), {"supported": False, "reason": "missing truth"})
        for values, weights in [([], None), ([0, float("nan")], None), ([0, 1], [.2, .2]),
                                ([0, 1], [-1, 2]), ([0, 1], [1]), ([0, 1], [float("nan"), 1])]:
            with self.assertRaises(ContractError):
                distribution(values, weights)

    def test_discrete_rank_intervals_zero_weights_and_infinite_log_loss(self):
        r = score([1, 1, 2, 100], 1, [.25, .25, .5, 0])
        self.assertEqual(r["rank_bounds"], [0, .5])
        self.assertEqual(r["intervals"]["0.8"]["hi"], 2)
        self.assertTrue(math.isinf(probability_score([1, 0], 1)["log_loss"]))
        self.assertEqual(probability_score([0, 1], 1), {"log_loss": -0., "brier": 0.})
        self.assertEqual(probability_score([.25, .75], 1)["brier"], .125)
        with self.assertRaises(ContractError):
            probability_score([.5, .4], 1)


class CutoffAndEvidenceTests(unittest.TestCase):
    def test_each_auxiliary_rejects_same_day_future_and_missing_dates(self):
        provenance = dict.fromkeys(("fit", "features", "normalisation", "missing_prior", "residuals", "calibration"), "2025-12-31")
        self.assertTrue(require_prior("2026-01-01", provenance))
        for field in provenance:
            for bad in ("2026-01-01", "2026-01-02", None):
                p = {**provenance, field: bad}
                with self.assertRaisesRegex(ContractError, field):
                    require_prior("2026-01-01", p)
        with self.assertRaisesRegex(ContractError, "provenance fields"):
            require_prior("2026-01-01", {})

    def test_timestamp_proof_fails_closed_and_rejects_backwards_retrieval(self):
        times = {"captured": "2026-01-02T00:00:00Z", "model_fitted": "2025-12-31T00:00:00Z",
                 "input_as_of": "2026-01-01T18:00:00Z", "report_published": "2026-01-01T19:00:00Z",
                 "report_retrieved": "2026-01-01T20:00:00Z"}
        tip = "2026-01-02T01:00:00Z"
        self.assertTrue(require_pre_tip(tip, times))
        for field in times:
            for value in (None, tip, "2026-01-03T00:00:00Z", "2026-01-01T00:00:00"):
                with self.assertRaises(ContractError):
                    require_pre_tip(tip, {**times, field: value})
        with self.assertRaisesRegex(ContractError, "order"):
            require_pre_tip(tip, {**times, "report_retrieved": "2026-01-01T18:00:00Z"})

    def test_immutable_evidence_creation_and_order_sensitive_panel_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            create_json(path, {"value": 1})
            with self.assertRaises(FileExistsError):
                create_json(path, {"value": 2})
            self.assertEqual(path.read_text(), '{\n  "value": 1\n}\n')
        self.assertNotEqual(digest(["1", "2"]), digest(["2", "1"]))

    def test_parquet_reader_never_returns_out_of_panel_rows(self):
        import pandas as pd
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outcomes.parquet"
            pd.DataFrame({"game_id": [100, 101, 102], "points": [4, 5, 999]}).to_parquet(path)
            # The third row stands for an outcome that this run must never open.
            frame = read_panel(path, ["100", "101"], numeric=True)
            self.assertEqual(frame.game_id.tolist(), ["100", "101"])
            self.assertEqual(frame.points.tolist(), [4, 5])

    def test_capture_and_receipt_corruption_fail_at_hash_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture = root / "worlds.npz"
            np.savez(capture, game_id="100", player_ids=["11", "21"], side=[0, 1], final_period=np.full(1000, 4))
            receipt = root / "receipt.json"
            create_json(receipt, {"game": "100", "arm": "reference", "entry": {
                "capture": "worlds.npz", "sha256": sha256_file(capture), "result": {
                    "date_et": "2026-01-01", "home": "1", "away": "2", "real_home": 8, "real_away": 12, "real_ot": 0}}})
            descriptor = {"game": "100", "receipt": "receipt.json", "sha256": sha256_file(receipt)}
            with patch.object(workbench, "ROOT", root):
                self.assertEqual(workbench.checked_reference(descriptor)["worlds"], 1000)
                with self.assertRaisesRegex(ContractError, "receipt hash"):
                    workbench.checked_reference({**descriptor, "sha256": "wrong"})
                capture.write_bytes(b"deliberately corrupted world capture")
                with self.assertRaisesRegex(ContractError, "capture hash"):
                    workbench.checked_reference(descriptor)


if __name__ == "__main__":
    unittest.main()
