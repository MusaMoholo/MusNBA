import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis import a1_branch_persist_audit, a1_branch_roster_pressure
from basketball_common import sha256_file


class BranchAuditTests(unittest.TestCase):
    def test_roster_pressure_counts_and_rejects_illegal_worlds(self):
        sides = np.array([0] * 6 + [1] * 6)
        available = np.ones((2, 12), dtype=bool)
        available[1, 11] = False
        fouls = np.zeros((2, 12, 5))
        fouls[0, 0, 0] = 6
        result = a1_branch_roster_pressure.pressure(available, fouls, sides)
        self.assertEqual(result['sides'][0]['exactly_five_final_eligible'], 1)
        self.assertEqual(result['sides'][0]['any_six_foul_player'], 1)
        self.assertEqual(result['sides'][1]['exactly_five_initial'], 1)
        fouls[1, 11, 0] = 1
        with self.assertRaisesRegex(ValueError, 'availability or foul'):
            a1_branch_roster_pressure.pressure(available, fouls, sides)
        fouls[1, 11, 0] = 0
        fouls[1, 6, 0] = 6
        with self.assertRaisesRegex(ValueError, 'fewer than five'):
            a1_branch_roster_pressure.pressure(available, fouls, sides)

    def test_exact_weights_and_unavailable_player_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            selected = [{'team_id': '1', 'player_id': '100', 'probability': 0.3,
                         'impact_rank': 1, 'impact_proxy': 30.0}]
            report = {'selected': selected, 'engine': 'engine-v1.3', 'origin': '2026-01-01',
                      'slate_date': '2026-01-02', 'game': '123', 'worlds_per_branch': 2, 'branches': [],
                      'selection_policy': 'top3-offensive-proxy-one-per-team-v1',
                      'impact_ranking': [{'team_id': '1', 'player_id': '100', 'availability': 0.3, 'rank': 1,
                                          'impact_proxy': 30.0, 'healthy_role': 30.0, 'value': 1.0},
                                         {'team_id': '2', 'player_id': '200', 'availability': 1.0, 'rank': 1,
                                          'impact_proxy': 20.0, 'healthy_role': 20.0, 'value': 1.0}]}
            paths = []
            for plays, numerator in ((True, '3'), (False, '7')):
                branch_id = 'lineup-v1:1/100=' + ('plays' if plays else 'sits')
                seed = int.from_bytes(hashlib.sha256(
                    f"lineup-v1|engine-v1.3|2026-01-01|2026-01-02|123|{branch_id}".encode()).digest()[:8], 'little')
                path = Path(directory) / f'{plays}.npz'
                zeros = np.zeros((2, 2, 5), dtype=int)
                data = {'player_ids': np.array(['100', '200']), 'side': np.array([0, 1]),
                        'available': np.array([[plays, True], [plays, True]]),
                        'minutes': zeros.copy(), 'player_points': zeros.copy(), 'player_fouls': zeros.copy(),
                        'team_points': np.zeros((2, 2, 5), dtype=int), 'trace_world': np.array([0, 1]),
                        **{f'box_{name}': zeros.copy() for name in ('pts', 'pf', 'fgm', 'fga', 'fg3m',
                                                                     'fg3a', 'ftm', 'fta')}}
                np.savez_compressed(path, **data)
                paths.append((path, data))
                report['branches'].append({'branch_id': branch_id, 'assignments': [['1', '100', plays]],
                                           'seed': str(seed), 'worlds': 2, 'capture': str(path),
                                           'capture_sha256': sha256_file(path),
                                           'weight': {'numerator': numerator, 'denominator': '10'}})
            self.assertEqual(a1_branch_persist_audit.audit(report)['weight_total'], '1')
            report['availability_policy'] = 'D47-nearest-quarter-preserve-uncertain-v1'
            report['impact_ranking'][0]['original_availability'] = 0.3
            with self.assertRaisesRegex(ValueError, 'D47 scale'):
                a1_branch_persist_audit.audit(report)
            del report['availability_policy']
            report['impact_ranking'][0]['rank'] = 2
            with self.assertRaisesRegex(ValueError, 'rank'):
                a1_branch_persist_audit.audit(report)
            report['impact_ranking'][0]['rank'] = 1
            report['branches'][0]['weight']['numerator'] = '4'
            with self.assertRaisesRegex(ValueError, 'weight'):
                a1_branch_persist_audit.audit(report)
            report['branches'][0]['weight']['numerator'] = '3'
            path, data = paths[1]
            data['minutes'][0, 0, 0] = 1
            np.savez_compressed(path, **data)
            report['branches'][1]['capture_sha256'] = sha256_file(path)
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                a1_branch_persist_audit.audit(report)


if __name__ == '__main__':
    unittest.main()
