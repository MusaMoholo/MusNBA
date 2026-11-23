import copy
import tempfile
import unittest
from pathlib import Path

from basketball_common import write_json
from analysis import a1_mixed_availability_audit as audit


class MixedAvailabilityAuditTests(unittest.TestCase):
    def test_missing_injury_report_and_ambiguous_rosters_stay_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            for team in ('1', '2'):
                players = [{'id': 'shared', 'displayName': 'Shared'},
                           {'id': team, 'displayName': f'P{team}'}]
                write_json(run / 'roster' / f'{team}.json.gz',
                           {'team': {'id': team}, 'athletes': players})
            roster, _ = audit.origin_roster(run)
            self.assertNotIn('shared', roster)
            self.assertEqual((roster['1']['status'], roster['1']['status_source']),
                             ('Unknown', 'missing_report'))

    def test_each_game_uses_its_own_original_roster_and_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs, snapshot = root / 'runs', root / '2026-11-22'
            game_ids = ('a', 'b')
            model = {'id': 'engine'}
            events = [{'id': gid, 'date': '2026-11-22T18:00:00Z',
                       'competitions': [{'timeValid': True, 'status': {'type': {'name': 'STATUS_SCHEDULED'}},
                                         'competitors': [{'homeAway': 'home', 'team': {'id': '1'}},
                                                         {'homeAway': 'away', 'team': {'id': '2'}}]}]}
                      for gid in game_ids]
            games, sources = {}, {}
            for i, gid in enumerate(game_ids, start=15):
                run_id = f'20261122T{i}0000Z'
                run = runs / run_id
                write_json(run / 'report.json', {'run': run_id, 'slate_date': '2026-11-22',
                                                'started': run_id, 'finished': f'20261122T{i}1000Z'})
                write_json(run / 'schedule' / '1.json.gz', {'events': events})
                for team in ('1', '2'):
                    write_json(run / 'roster' / f'{team}.json.gz',
                               {'team': {'id': team}, 'athletes': [{'id': team, 'displayName': f'P{team}'}]})
                status = 'Out' if gid == 'a' else 'Questionable'
                injury = {'athlete': {'links': [{'href': 'https://example.invalid/id/1/'}]},
                          'status': status, 'shortComment': 'Report'}
                write_json(run / 'injuries.json.gz', {'injuries': [{'id': '1', 'injuries': [injury]},
                                                                    {'id': '2', 'injuries': []}]})
                detail = {'status': status, 'date': None, 'comment': 'Report',
                          'type': None, 'detail': None, 'return': None}
                games[gid] = {'game_id': gid, 'model': 'engine', 'sims': 2,
                              'home': {'team_id': '1'}, 'away': {'team_id': '2'},
                              'availability_report': {
                                  'home': [{'id': '1', 'name': 'P1', 'status': status, 'reported_status': status,
                                            'status_source': 'injury_report', 'injury': detail,
                                            'availability': 0.0 if status == 'Out' else .5}],
                                  'away': [{'id': '2', 'name': 'P2', 'status': 'Active', 'reported_status': None,
                                            'status_source': 'not_listed_assumption', 'injury': None, 'availability': 1.0}]}}
                sources[gid] = {'kind': 'prospective', 'slate_date': '2026-11-22', 'origin': '2026-11-22',
                                'cutoff': '2026-11-21',
                                'model': model, 'sims': 2, 'started_at': f'2026-11-22T{i}:20:00Z',
                                'generated': f'2026-11-22T{i}:30:00Z',
                                'completed_at': f'2026-11-22T{i}:30:00Z', 'pre_tip': {gid: True},
                                'inputs': {'registry_run': run_id}}
            meta = {'origin': '2026-11-22', 'model': model, 'games': list(game_ids),
                    'game_provenance_schema': 1, 'game_provenance': sources}
            write_json(snapshot / 'meta.json', meta)
            write_json(snapshot / 'games.json', games)
            result, _ = audit.audit(snapshot, runs)
            self.assertEqual((result['games'], result['report_entries'], result['pre_tip_games'],
                              result['origin_collections']), (2, 4, 2, 2))
            corrupt = copy.deepcopy(games)
            corrupt['a']['availability_report']['home'][0]['status'] = 'Questionable'
            write_json(snapshot / 'games.json', corrupt)
            with self.assertRaisesRegex(ValueError, 'status'):
                audit.audit(snapshot, runs)
            write_json(snapshot / 'games.json', games)
            uncertain = copy.deepcopy(events)
            uncertain[0]['competitions'][0]['status']['type']['name'] = 'STATUS_SUSPENDED'
            write_json(runs / '20261122T150000Z' / 'schedule' / '1.json.gz', {'events': uncertain})
            with self.assertRaisesRegex(ValueError, 'status cannot establish'):
                audit.audit(snapshot, runs)
            write_json(runs / '20261122T150000Z' / 'schedule' / '1.json.gz', {'events': events})
            sources['a']['started_at'] = '2026-11-22T15:05:00Z'
            write_json(snapshot / 'meta.json', meta)
            with self.assertRaisesRegex(ValueError, 'collection'):
                audit.audit(snapshot, runs)


if __name__ == '__main__':
    unittest.main()
