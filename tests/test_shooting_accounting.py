import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from basketball_common import write_json
from scripts import a1_snapshot_shooting_audit as audit, projection, smoke, views


class ShootingAccountingTests(unittest.TestCase):
    def test_snapshot_audit_checks_roster_and_period_accounting(self):
        worlds, gid = 4, '123'
        values = {'fgm': [1, 0, 1, 1], 'fga': [8, 0, 2, 1],
                  'fg3m': [0, 0, 0, 0], 'fg3a': [0, 0, 0, 0],
                  'ftm': [0, 1, 0, 2], 'fta': [0, 2, 1, 2]}
        stats = {key: projection.summary(np.array(series)) for key, series in values.items()}
        stats.update(projection.shooting_summaries(values))
        period = {'stats': stats, 'mean': {key: stats[key]['mean'] for key in values}}
        player = {'id': '1', 'periods': {key: copy.deepcopy(period) for key in projection.SLICES}}
        game = {'game_id': gid, 'model': 'engine-v1.3', 'sims': worlds, 'shooting_distribution_schema': 1,
                'home': {'players': [player]}, 'away': {'players': [{'id': '2'}]}}
        meta = {'slate_date': '2026-11-22', 'origin': '2026-11-22', 'model': {'id': 'engine-v1.3'},
                'cutoff': '2026-11-21', 'kind': 'prospective', 'sims': worlds, 'games': [gid]}
        lines = np.zeros((worlds, 2, len(views.WORLD_STATS)), dtype=np.uint8)
        for key, series in values.items():
            lines[:, 0, views.WORLD_STATS.index(key)] = series
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            day = root / '2026-11-22'
            day.mkdir()
            write_json(day / 'meta.json', meta)
            write_json(day / 'games.json', {gid: game})
            np.savez_compressed(day / 'engine_players.npz', **{
                f'{gid}__ids': np.array(['1', '2']), f'{gid}__side': np.array([0, 1]), f'{gid}__lines': lines})
            with patch.object(audit, 'SNAPSHOTS', root):
                result, _ = audit.audit_day('2026-11-22', '2026-11-22', 'engine-v1.3', worlds)
                self.assertEqual(result['period_triplets'], 21)
                self.assertEqual(result['partial_no_attempt_period_triplets'], 14)
                self.assertEqual(result['no_attempt_period_triplets'], 7)
                self.assertEqual(result['players_without_periods'], 1)
                game['away']['players'][0]['id'] = '1'
                write_json(day / 'games.json', {gid: game})
                with self.assertRaisesRegex(ValueError, 'player IDs or sides'):
                    audit.audit_day('2026-11-22', '2026-11-22', 'engine-v1.3', worlds)

    def test_independent_audit_matches_saved_worlds_and_mixed_no_attempts(self):
        lines = np.zeros((4, len(views.WORLD_STATS)), dtype=np.int16)
        values = {'fgm': [1, 0, 1, 1], 'fga': [8, 0, 2, 1],
                  'fg3m': [0, 0, 0, 0], 'fg3a': [0, 0, 0, 0],
                  'ftm': [0, 1, 0, 2], 'fta': [0, 2, 1, 2]}
        for key, series in values.items():
            lines[:, views.WORLD_STATS.index(key)] = series
        stats = {key: projection.summary(np.array(series)) for key, series in values.items()}
        stats.update(projection.shooting_summaries(values))
        self.assertEqual(audit.check_period(stats, 4, 'test'), {'fgpct': 3, 'fg3pct': 0, 'ftpct': 3})
        self.assertEqual(audit.check_full_game(stats, lines, 'test'), 8)
        self.assertEqual(stats['fgpct']['hist'][13], 1)  # 1/8 rounds up from 12.5%

        broken = copy.deepcopy(stats)
        broken['ftpct']['defined'] = 4
        with self.assertRaisesRegex(ValueError, 'conditional sample size'):
            audit.check_period(broken, 4, 'test')
        broken = copy.deepcopy(stats)
        broken['fgpct']['hist'][13] -= 1
        broken['fgpct']['hist'][12] += 1
        with self.assertRaisesRegex(ValueError, 'differs from retained player worlds'):
            audit.check_full_game(broken, lines, 'test')
        broken = copy.deepcopy(stats)
        broken['fga']['mean'] += 1
        with self.assertRaisesRegex(ValueError, 'summary does not match'):
            audit.check_period(broken, 4, 'test')

    def test_histograms_account_for_no_attempt_worlds(self):
        counts = {'min': 0, 'hist': [1, 0, 2]}
        percentage = {'min': 0, 'hist': [1, 0, 1], 'defined': 2, 'total': 3}
        zero = {'min': 0, 'hist': [3]}
        stats = {'fga': counts, 'fg3a': zero, 'fta': zero, 'fgpct': percentage}
        self.assertEqual(smoke.player_hist_problems(stats, 3, True), [])
        broken = copy.deepcopy(stats)
        broken['fgpct']['defined'] = 3
        self.assertIn('fgpct conditional histogram count', smoke.player_hist_problems(broken, 3, True))
        del broken['fgpct']
        self.assertIn('fgpct conditional histogram count', smoke.player_hist_problems(broken, 3, True))
        broken['fgpct'] = {'min': 101, 'hist': [2], 'defined': 2, 'total': 3}
        self.assertIn('fgpct conditional histogram count', smoke.player_hist_problems(broken, 3, True))

    def test_legacy_replay_ignores_only_new_fields(self):
        stats = {'pts': {'hist': [1], 'min': 0}, 'fga': {'hist': [1], 'min': 0},
                 'fgpct': {'hist': [1], 'min': 0, 'defined': 1, 'total': 1}}
        replay = {'shooting_distribution_schema': 1, 'home': {'players': [{'periods': {
            'fg': {'stats': copy.deepcopy(stats)}, 'q1': {'stats': copy.deepcopy(stats)}}}]}, 'away': {'players': []}}
        current = copy.deepcopy(replay)
        smoke.align_legacy_shooting_schema({'shooting_distribution_schema': 1}, current)
        self.assertEqual(current, replay)
        smoke.align_legacy_shooting_schema({}, replay)
        self.assertNotIn('shooting_distribution_schema', replay)
        self.assertEqual(set(replay['home']['players'][0]['periods']['fg']['stats']), {'pts', 'fga'})
        self.assertEqual(set(replay['home']['players'][0]['periods']['q1']['stats']), {'pts'})


if __name__ == '__main__':
    unittest.main()
