import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from basketball_common import sha256_file, write_json
from scripts import a1_snapshot_availability_audit as audit


class SnapshotAvailabilityAuditTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            '1': {'name': 'Assumed', 'status': 'Active', 'reported_status': None,
                  'status_source': 'not_listed_assumption', 'injury': None},
            '2': {'name': 'Out', 'status': 'Out', 'reported_status': 'Out',
                  'status_source': 'injury_report', 'injury': {'comment': 'Original'}},
        }
        self.report = [
            {'id': '1', **self.registry['1'], 'availability': 1.0},
            {'id': '2', **copy.deepcopy(self.registry['2']), 'availability': 0.0},
        ]

    def test_report_matches_origin_and_keeps_ruled_out_players(self):
        self.assertEqual(audit.check_report('g', 'home', self.report, self.registry), 2)
        missing = self.report[:1]
        with self.assertRaisesRegex(ValueError, 'roster'):
            audit.check_report('g', 'home', missing, self.registry)

    def test_report_rejects_later_status_or_fabricated_health_provenance(self):
        for field, value in (('status', 'Questionable'), ('reported_status', 'Active'),
                             ('status_source', 'injury_report'), ('injury', {'comment': 'Later'})):
            report = copy.deepcopy(self.report)
            report[0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                audit.check_report('g', 'home', report, self.registry)

    def test_world_points_must_match_player_lines_per_side(self):
        periods = np.zeros((2, 2, 5), dtype=np.int16)
        periods[:, 0, 0] = [3, 5]
        periods[:, 1, 0] = [2, 4]
        lines = np.zeros((2, 2, 2), dtype=np.uint8)
        lines[:, 0, 1] = [3, 5]
        lines[:, 1, 1] = [2, 4]
        self.assertEqual(audit.check_worlds('g', periods, lines, np.array([0, 1])), 4)
        lines[1, 0, 1] = 4
        with self.assertRaisesRegex(ValueError, 'points'):
            audit.check_worlds('g', periods, lines, np.array([0, 1]))

    def test_single_registry_audit_refuses_mixed_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / '2026-11-22' / 'meta.json', {'game_provenance_schema': 1})
            with patch.object(audit, 'SNAPSHOTS', root), self.assertRaisesRegex(ValueError, 'per-game origin registries'):
                audit.audit_day('2026-11-22', {}, {}, 'engine', 2, '2026-11-22')

    def test_snapshot_audit_checks_view_and_season_against_saved_worlds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshots, views, master = root / 'snapshots', root / 'views', root / 'fixtures.csv'
            master.write_text('fixture')
            day, gid = '2026-11-22', 'g'
            snapshot = snapshots / day
            snapshot.mkdir(parents=True)
            registry = {'run': 'run1', 'players': {}}
            report, sim = {}, {}
            for team, name in ((1, 'home'), (2, 'away')):
                roster = [{'id': str(team * 10 + i), 'name': f'{name}{i}', 'status': 'Active',
                           'reported_status': None, 'status_source': 'not_listed_assumption',
                           'injury': None, 'availability': 1.0} for i in range(5)]
                report[name] = roster.copy()
                sim[name] = {'players': [{'id': row['id'], 'starter': True, 'availability': 1.0} for row in roster]}
                for row in roster:
                    registry['players'][row['id']] = {**row, 'team': str(team), 'on_roster': True}
            out = {'id': '99', 'name': 'Out', 'status': 'Out', 'reported_status': 'Out',
                   'status_source': 'injury_report', 'injury': None, 'availability': 0.0}
            report['home'].append(out)
            registry['players']['99'] = {**out, 'team': '1', 'on_roster': True}
            write_json(snapshot / 'games.json', {gid: {**sim, 'availability_report': report}})
            origin = '2026-11-21'
            meta = {'slate_date': day, 'origin': origin, 'cutoff': '2026-11-20',
                    'kind': 'prospective', 'model': {'id': 'engine'},
                    'started_at': '2026-11-21T22:00:00Z',
                    'generated': '2026-11-21T23:00:00Z', 'completed_at': '2026-11-21T23:00:00Z',
                    'pre_tip': {gid: True},
                    'sims': 2, 'season_sims': 2, 'games': [gid],
                    'inputs': {'registry_run': 'run1', 'master_sha256': sha256_file(master), 'completed_games_used': 1}}
            write_json(snapshot / 'meta.json', meta)
            season = {'sims': 2, 'as_of': origin, 'games': [
                {'game_id': gid, 'source': 'engine', 'p_home': 0.5, 'mu_home': 4.0, 'mu_away': 4.0},
            ]}
            write_json(snapshot / 'season.json', season)
            prior_game = {'game_id': 'past', 'date': '2026-11-20'}
            stats = {'league': {'games': 1}, 'teams': {'1': {'games': [prior_game]}, '2': {'games': [prior_game]}},
                     'players': {'10': {'log': [prior_game]}}}
            write_json(snapshot / 'stats.json', stats)
            periods = np.zeros((2, 2, 5), dtype=np.int16)
            periods[:, :, 0] = [[3, 5], [5, 3]]
            lines = np.zeros((2, 10, 2), dtype=np.uint8)
            lines[:, 0, 1], lines[:, 5, 1] = [3, 5], [5, 3]
            np.savez_compressed(snapshot / 'engine_worlds.npz', **{gid: periods})
            np.savez_compressed(snapshot / 'engine_players.npz', **{
                f'{gid}__ids': np.array([str(10 + i) for i in range(5)] + [str(20 + i) for i in range(5)]),
                f'{gid}__side': np.repeat([0, 1], 5), f'{gid}__lines': lines,
            })
            view_path = views / 'api/game' / f'{gid}.json'
            view = {'projection': {'snapshot': day, 'origin': origin, 'pre_tip': True,
                                   'completed_at': meta['completed_at'], 'model': {'id': 'engine'}},
                    'availability': {'source': 'snapshot', 'home': [out], 'away': []}}
            write_json(view_path, view)
            fixture = {gid: {'home_id': '1', 'away_id': '2', 'status': 'scheduled', 'date_et': day,
                             'tip_utc': '2026-11-22T02:00:00Z'},
                       'past': {'status': 'final', 'date_et': '2026-11-20'},
                       'origin-game': {'status': 'final', 'date_et': origin}}
            with patch.object(audit, 'SNAPSHOTS', snapshots), patch.object(audit, 'VIEWS', views), \
                    patch.object(audit, 'MASTER_CSV', master):
                result, _ = audit.audit_day(day, registry, fixture, 'engine', 2, origin)
                self.assertEqual((result['report_entries'], result['ruled_out_entries'],
                                  result['player_team_point_checks'], result['season_game_checks']), (11, 1, 4, 1))
                meta['cutoff'] = '2026-11-21'
                write_json(snapshot / 'meta.json', meta)
                with self.assertRaisesRegex(ValueError, 'origin'):
                    audit.audit_day(day, registry, fixture, 'engine', 2, origin)
                meta['cutoff'] = '2026-11-20'
                write_json(snapshot / 'meta.json', meta)
                meta['pre_tip'][gid] = False
                write_json(snapshot / 'meta.json', meta)
                with self.assertRaisesRegex(ValueError, 'pre-tip'):
                    audit.audit_day(day, registry, fixture, 'engine', 2, origin)
                meta['pre_tip'][gid] = True
                write_json(snapshot / 'meta.json', meta)
                stats['teams']['1']['games'].append({'game_id': 'origin-game', 'date': origin})
                write_json(snapshot / 'stats.json', stats)
                with self.assertRaisesRegex(ValueError, 'team inputs'):
                    audit.audit_day(day, registry, fixture, 'engine', 2, origin)
                stats['teams']['1']['games'].pop()
                stats['players']['10']['log'].append({'game_id': 'origin-game', 'date': origin})
                write_json(snapshot / 'stats.json', stats)
                with self.assertRaisesRegex(ValueError, 'player inputs'):
                    audit.audit_day(day, registry, fixture, 'engine', 2, origin)
                stats['players']['10']['log'].pop()
                write_json(snapshot / 'stats.json', stats)
                season['as_of'] = day
                write_json(snapshot / 'season.json', season)
                with self.assertRaisesRegex(ValueError, 'origin'):
                    audit.audit_day(day, registry, fixture, 'engine', 2, origin)
                season['as_of'] = origin
                write_json(snapshot / 'season.json', season)
                view['availability']['home'] = []
                write_json(view_path, view)
                with self.assertRaisesRegex(ValueError, 'visible report'):
                    audit.audit_day(day, registry, fixture, 'engine', 2, origin)


if __name__ == '__main__':
    unittest.main()
