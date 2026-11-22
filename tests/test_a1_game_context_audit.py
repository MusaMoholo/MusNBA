import copy
import unittest

from analysis.a1_game_context_audit import audit_context, audit_provenance


class GameContextAuditTests(unittest.TestCase):
    def setUp(self):
        self.meta = {'origin': '2026-11-22', 'cutoff': '2026-11-21', 'kind': 'prospective',
                     'games': ['3'], 'pre_tip': {'3': True}, 'completed_at': '2026-11-22T12:00Z'}
        self.row = {'game_id': '3', 'date_et': '2026-11-23', 'tip_utc': '2026-11-24T00:00Z',
                    'time_valid': '1', 'status': 'scheduled', 'status_detail': 'Scheduled',
                    'tv': '', 'venue': '', 'city': '', 'neutral': '0', 'notes': '', 'periods': '',
                    'home_id': '1', 'home_abbr': 'H', 'away_id': '2', 'away_abbr': 'A',
                    'home_pts': '', 'away_pts': ''}
        earlier = dict(self.row, game_id='1', date_et='2026-11-21', status='final', home_pts='100', away_pts='90')
        same_day = dict(self.row, game_id='2', date_et='2026-11-22', status='final', home_pts='80', away_pts='90')
        self.rows = [earlier, same_day, self.row]
        self.game = {'id': '3', 'date': '2026-11-23', 'tip_utc': '2026-11-24T00:00Z',
                     'time_valid': True, 'status': 'scheduled', 'detail': 'Scheduled', 'tv': [],
                     'venue': '', 'city': '', 'neutral': False, 'notes': [], 'periods': None,
                     'home': {'id': '1', 'abbr': 'H', 'score': None, 'record': [1, 0]},
                     'away': {'id': '2', 'abbr': 'A', 'score': None, 'record': [0, 1]}}

    def test_strictly_pre_origin_records(self):
        self.assertEqual(audit_context(self.meta, self.rows, self.game)['home_record'], [1, 0])
        contaminated = copy.deepcopy(self.game)
        contaminated['home']['record'] = [1, 1]
        with self.assertRaisesRegex(ValueError, 'pre-origin records'):
            audit_context(self.meta, self.rows, contaminated)

    def test_rejects_late_or_mutated_context(self):
        for change in (
            lambda meta, rows, game: meta.update(cutoff='2026-11-22'),
            lambda meta, rows, game: meta.update(cutoff=''),
            lambda meta, rows, game: meta.update(completed_at='2026-11-24T00:00Z'),
            lambda meta, rows, game: rows[-1].update(status='final'),
            lambda meta, rows, game: game['home'].update(score=100),
        ):
            meta, rows, game = copy.deepcopy((self.meta, self.rows, self.game))
            change(meta, rows, game)
            with self.assertRaises(ValueError):
                audit_context(meta, rows, game)

    def test_view_and_payload_must_share_the_pinned_origin(self):
        research = {'game': '3', 'origin': '2026-11-22', 'fixture_sha256': 'fixture'}
        view = {'game': self.game, 'research': research}
        payload = {**research, 'snapshot_inputs': {'data/snapshots/2026-11-22/meta.json': 'digest'}}
        audit_provenance(self.meta, 'digest', view, payload)
        for key in ('origin', 'fixture_sha256'):
            changed = copy.deepcopy(payload)
            changed[key] = 'different'
            with self.assertRaisesRegex(ValueError, 'provenance'):
                audit_provenance(self.meta, 'digest', view, changed)
        with self.assertRaisesRegex(ValueError, 'provenance'):
            audit_provenance(self.meta, 'different', view, payload)


if __name__ == '__main__':
    unittest.main()
