import copy
import unittest
from pathlib import Path

from basketball_common import read_json
from scripts import release_gate

REPORTS = Path(__file__).resolve().parents[1] / 'analysis/experiments'


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.repair = read_json(REPORTS / '20261123_a1_vector_penalty_f4_200_v1_compare.json')

    def test_correctness_class_requires_compatibility_not_invented_accuracy_gain(self):
        result = release_gate.assess(self.repair, 'mechanics')
        self.assertEqual(result['core']['checks'], 44)
        self.assertEqual(result['core']['established'], 44)
        self.assertEqual(result['coverage']['unresolved'], 2)
        self.assertEqual(result['decision'], 'development_scores_compatible')
        self.assertIn('no automatic promotion', result['release_requirements'])

    def test_same_evidence_does_not_establish_a_learned_accuracy_improvement(self):
        result = release_gate.assess(self.repair, 'learned', 'players/all/pts/crps')
        self.assertEqual(result['decision'], 'primary_benefit_not_established')
        with self.assertRaisesRegex(ValueError, 'preregistered'):
            release_gate.assess(self.repair, 'learned')

    def test_independent_seed_null_requests_precision_instead_of_asserting_harm(self):
        noise = read_json(REPORTS / '20261122_a1_seed_noise.json')
        result = release_gate.assess(noise, 'mechanics')
        self.assertEqual(result['decision'], 'more_precision_or_coverage_needed')
        self.assertFalse(result['statistical_compatibility'])
        self.assertFalse(any(row['status'] == 'material_harm' for row in result['core']['details']))

    def test_calibration_harm_is_not_ignored_by_a_mechanical_classification(self):
        harmed = copy.deepcopy(self.repair)
        harmed['games']['q3_margin']['coverage'].update(change=.05, ci_95=[.04, .06])
        result = release_gate.assess(harmed, 'mechanics')
        self.assertEqual(result['decision'], 'material_harm')
        self.assertFalse(result['statistical_compatibility'])

    def test_player_score_harm_blocks_even_if_every_calibration_check_is_good(self):
        harmed = copy.deepcopy(self.repair)
        harmed['players']['star']['pts']['crps'].update(change=.2, ci_95=[.15, .25])
        result = release_gate.assess(harmed, 'mechanics')
        self.assertEqual(result['decision'], 'material_harm')
        self.assertFalse(result['statistical_compatibility'])


if __name__ == '__main__':
    unittest.main()
