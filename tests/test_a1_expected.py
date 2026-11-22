import json
import unittest
from fractions import Fraction
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from scripts import a1_expected


def fraction(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


class ExpectedMixtureTests(unittest.TestCase):
    def test_exact_indivisible_world_probability(self):
        values = [np.r_[1, np.zeros(9999, dtype=int)], np.zeros(10000, dtype=int)]
        result = a1_expected.weighted_distribution(values, [Fraction(1, 2), Fraction(1, 2)])
        self.assertEqual(result['worlds'], 20000)
        self.assertEqual(fraction(result['histogram'][1]), Fraction(1, 20000))
        self.assertEqual(result['quantiles'], [0, 0, 0, 0, 0])
        self.assertEqual(result['mean'], 1 / 20000)

    def test_undefined_ratios_are_conditioned_by_probability_mass(self):
        values = [np.array([np.nan, 50.0]), np.array([100.0, np.nan])]
        result = a1_expected.weighted_distribution(values, [Fraction(3, 4), Fraction(1, 4)])
        self.assertEqual(fraction(result['defined_mass']), Fraction(1, 2))
        self.assertEqual(fraction(result['undefined_mass']), Fraction(1, 2))
        self.assertEqual([fraction(item) for item in result['histogram']], [Fraction(3, 4), Fraction(1, 4)])
        self.assertEqual(result['mean'], 62.5)
        self.assertEqual(result['quantiles'], [50.0, 50.0, 50.0, 50.0, 100.0])
        empty = a1_expected.weighted_distribution([np.array([np.nan])], [Fraction(1)])
        self.assertEqual(empty['status'], 'undefined in every selected world')
        self.assertIsNone(empty['mean'])

    def test_invalid_or_nonunit_inputs_fail(self):
        for values, weights in (([np.array([np.inf])], [Fraction(1)]),
                                ([np.array([])], [Fraction(1)]),
                                ([np.array([1])], [Fraction(1, 2)]),
                                ([np.array([1])], [1.0])):
            with self.subTest(values=values, weights=weights), self.assertRaises(ValueError):
                a1_expected.weighted_distribution(values, weights)

    def test_given_and_joint_use_the_same_unequal_branch_masses(self):
        event = [np.array([True, False]), np.array([True, True])]
        condition = [np.array([True, True]), np.array([True, False])]
        result = a1_expected.weighted_joint(event, condition, [Fraction(1, 4), Fraction(3, 4)])
        self.assertEqual(fraction(result['event']), Fraction(7, 8))
        self.assertEqual(fraction(result['condition']), Fraction(5, 8))
        self.assertEqual(fraction(result['joint']), Fraction(1, 2))
        self.assertEqual(fraction(result['given']), Fraction(4, 5))
        empty = a1_expected.weighted_joint(event, [np.zeros(2, bool), np.zeros(2, bool)],
                                           [Fraction(1, 4), Fraction(3, 4)])
        self.assertIsNone(empty['given'])
        self.assertEqual(empty['status'], 'no matching condition worlds')
        with self.assertRaisesRegex(ValueError, 'boolean'):
            a1_expected.weighted_joint(event, [np.ones(2), np.ones(2)], [Fraction(1, 4), Fraction(3, 4)])

    def test_partial_condition_marginalises_other_player_exactly(self):
        selected = [{'team_id': '1', 'player_id': '10', 'probability': 0.75},
                    {'team_id': '2', 'player_id': '20', 'probability': 0.5}]
        records = []
        for first, second in product((True, False), repeat=2):
            weight = (Fraction(3, 4) if first else Fraction(1, 4)) * Fraction(1, 2)
            records.append({'assignments': [['1', '10', first], ['2', '20', second]],
                            'weight': a1_expected.fraction_json(weight)})
        report = {'selected': selected, 'branches': records}
        result = a1_expected.selected_branches(report, {'10': False})
        self.assertEqual([weight for _, weight in result], [Fraction(1, 2), Fraction(1, 2)])
        self.assertEqual([record['assignments'][1][2] for record, _ in result], [True, False])
        with self.assertRaisesRegex(ValueError, 'conditions'):
            a1_expected.selected_branches(report, {'99': True})
        report['branches'][0]['weight'] = a1_expected.fraction_json(Fraction(1, 4))
        with self.assertRaisesRegex(ValueError, 'weight'):
            a1_expected.selected_branches(report, {})

    def test_player_shooting_ratio_is_per_world_and_undefined_without_attempts(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'worlds.npz'
            made = np.array([[[1], [1]], [[0], [1]]])
            attempts = np.array([[[2], [1]], [[0], [4]]])
            np.savez(path, side=np.array([0, 0]), player_ids=np.array(['10', '11']),
                     box_fgm=made, box_fga=attempts)
            with np.load(path, allow_pickle=False) as data:
                np.testing.assert_equal(a1_expected.metric(data, 'home', '10', 'fgpct'), [50.0, np.nan])
                np.testing.assert_equal(a1_expected.metric(data, 'home', None, 'fgpct'), [200 / 3, 25.0])
                with self.assertRaisesRegex(ValueError, 'not uniquely present'):
                    a1_expected.metric(data, 'away', '10', 'fgpct')

    def test_report_exposes_missing_status_and_prior_role_assumptions(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            selected = [{'team_id': '1', 'player_id': '10', 'probability': 0.5,
                         'status': 'Unknown', 'status_source': None, 'role_basis': 'prior',
                         'missing': ['observed_role', 'usage']}]
            branches = []
            for plays in (True, False):
                capture = root / f'{plays}.npz'
                np.savez(capture, side=np.array([0]), player_ids=np.array(['10']),
                         box_pts=np.array([[[int(plays)]]]))
                branches.append({'branch_id': str(plays), 'assignments': [['1', '10', plays]],
                                 'weight': {'numerator': '1', 'denominator': '2'},
                                 'capture': str(capture), 'capture_sha256': 'test'})
            source = root / 'source.json'
            source.write_text(json.dumps({'selected': selected, 'branches': branches,
                                          'weight_assumptions': 'uncalibrated independence'}))
            output = root / 'result.json'
            argv = ['a1_expected.py', str(source), '--side', 'home', '--player', '10',
                    '--stat', 'pts', '--output', str(output)]
            with patch('sys.argv', argv), patch.object(a1_expected.a1_branch_persist_audit, 'audit'):
                a1_expected.main()
            result = json.loads(output.read_text())
            self.assertEqual(result['selected_players'], selected)
            self.assertEqual(result['weight_assumptions'], 'uncalibrated independence')
            self.assertTrue(any('independence' in line for line in result['limitations']))
            self.assertTrue(any('missing status' in line for line in result['limitations']))


if __name__ == '__main__':
    unittest.main()
