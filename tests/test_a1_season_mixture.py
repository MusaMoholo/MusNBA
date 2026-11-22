import json
import unittest
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from scripts import a1_season_mixture, smoke


def games_from_scores(scores):
    out = np.zeros((len(scores), 2, 5), dtype=np.int64)
    out[:, 0, 0] = scores
    return out


class SeasonMixtureTests(unittest.TestCase):
    def test_smoke_selects_training_losses_not_other_research_arrays(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            loss = root / '20261120T120935Z_final_v1.3.npz'
            loss.touch()
            (root / '20261122_chunk_a_a1_d47_season_coupling.npz').touch()
            self.assertEqual(smoke.training_loss_runs(root), [loss])

    def test_exact_indivisible_marginals_for_multiple_games(self):
        games = {
            'a': [(games_from_scores([1] + [0] * 9999), Fraction(1, 2)),
                  (games_from_scores([0] * 10000), Fraction(1, 2))],
            'b': [(games_from_scores([0, 1, 2]), Fraction(1))],
        }
        result = a1_season_mixture.couple(games, 17)
        weights = result['numerators']
        denominator = result['denominator']
        self.assertEqual(int(weights.sum()), denominator)
        self.assertEqual(Fraction(int(weights[result['games']['a'][:, 0, 0] == 1].sum()), denominator),
                         Fraction(1, 20000))
        for score in range(3):
            mask = result['games']['b'][:, 0, 0] == score
            self.assertEqual(Fraction(int(weights[mask].sum()), denominator), Fraction(1, 3))

    def test_repeat_and_input_order_do_not_change_paths(self):
        a = [(games_from_scores([1, 2, 3]), Fraction(1))]
        b = [(games_from_scores([4, 5]), Fraction(3, 4)), (games_from_scores([6, 7]), Fraction(1, 4))]
        first = a1_season_mixture.couple({'a': a, 'b': b}, 42)
        second = a1_season_mixture.couple({'b': b, 'a': a}, 42)
        np.testing.assert_array_equal(first['numerators'], second['numerators'])
        for game in ('a', 'b'):
            np.testing.assert_array_equal(first['games'][game], second['games'][game])

    def test_rejects_nonunit_and_unrepresentable_weights(self):
        worlds = games_from_scores([0])
        for pieces in ([(worlds, Fraction(1, 2))], [(worlds, Fraction(0)), (worlds, Fraction(1))],
                       [(worlds, Fraction(1, 10**30)), (worlds, 1 - Fraction(1, 10**30))]):
            with self.subTest(pieces=pieces), self.assertRaises(ValueError):
                a1_season_mixture.couple({'a': pieces}, 0)

    def test_explicit_path_limit_fails_before_building_coupled_worlds(self):
        games = {'a': [(games_from_scores([1, 2, 3]), Fraction(1))]}
        with self.assertRaisesRegex(ValueError, 'exceeding limit'):
            a1_season_mixture.couple(games, 17, max_paths=2)
        with self.assertRaisesRegex(ValueError, 'positive integer'):
            a1_season_mixture.couple(games, 17, max_paths=0)
        self.assertEqual(len(a1_season_mixture.couple(games, 17, max_paths=3)['numerators']), 3)

    def test_branch_source_retains_availability_limitations(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            capture = root / 'scores.npz'
            np.savez(capture, team_points=games_from_scores([1, 2]))
            selected = [{'team_id': '1', 'player_id': '10', 'probability': 0.5,
                         'status': 'Unknown', 'status_source': None, 'role_basis': 'prior',
                         'missing': ['observed_role']}]
            report = {'game': 'g', 'origin': '2026-01-01', 'engine': 'test', 'selected': selected,
                      'availability_policy': 'quarter', 'weight_assumptions': 'uncalibrated independence',
                      'branches': [{'assignments': [['1', '10', plays]], 'capture': str(capture),
                                    'weight': {'numerator': '1', 'denominator': '2'}}
                                   for plays in (True, False)]}
            path = root / 'report.json'
            path.write_text(json.dumps(report))
            with patch.object(a1_season_mixture.a1_branch_persist_audit, 'audit'):
                _, provenance, _ = a1_season_mixture.from_reports([path])
                self.assertEqual(provenance[0]['selected_players'], selected)
                self.assertEqual(provenance[0]['weight_assumptions'], 'uncalibrated independence')
                del report['weight_assumptions']
                path.write_text(json.dumps(report))
                with self.assertRaisesRegex(ValueError, 'assumptions'):
                    a1_season_mixture.from_reports([path])

    def test_season_summaries_use_weights_not_path_counts(self):
        teams = {'1': {'conf': 'East'}, '2': {'conf': 'West'}}
        standings = {'1': {'w': 0}, '2': {'w': 0}}
        games = [{'game_id': 'g', 'home_id': '1', 'away_id': '2'}]
        played = {'home_win': np.array([[True], [False]]),
                  'points': np.array([[[1, 0]], [[0, 1]]])}
        out = a1_season_mixture.summarize_pathway(teams, standings, games, played, np.array([1, 3]), 4, 7)
        def F(value):
            return Fraction(int(value['numerator']), int(value['denominator']))
        self.assertEqual(F(out['games'][0]['home_win']), Fraction(1, 4))
        self.assertEqual(F(out['teams']['1']['mean_wins']), Fraction(1, 4))
        self.assertEqual(F(out['teams']['2']['mean_wins']), Fraction(3, 4))
        self.assertEqual([F(row) for row in out['teams']['1']['wins']], [Fraction(3, 4), Fraction(1, 4)])
        self.assertEqual(F(out['teams']['1']['seeds'][0]), 1)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            a1_season_mixture.summarize_pathway(teams, standings, games * 2, played, np.array([1, 3]), 4, 7)


if __name__ == '__main__':
    unittest.main()
