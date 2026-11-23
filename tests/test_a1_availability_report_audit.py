import tempfile
import unittest
from pathlib import Path

from scripts import a1_availability_report_audit as audit


class ReportCoverageTests(unittest.TestCase):
    def test_collection_must_finish_strictly_before_a_known_tip(self):
        event = {'date': '2026-11-20T01:00:00Z', 'competitions': [{'timeValid': True}]}
        before = audit.utc('20261120T005959Z')
        at_tip = audit.utc('20261120T010000Z')
        self.assertEqual(audit.game_origin(event, before), ('pre_tip', '2026-11-19'))
        self.assertEqual(audit.game_origin(event, at_tip), ('at_or_after_tip', '2026-11-19'))
        event['competitions'][0]['timeValid'] = False
        self.assertEqual(audit.game_origin(event, before), ('unknown_tip', None))
        del event['competitions'][0]['timeValid']
        self.assertEqual(audit.game_origin(event, before), ('unknown_tip', None))
        with self.assertRaisesRegex(ValueError, 'lacks a UTC offset'):
            audit.utc('2026-11-20T01:00:00')

    def test_injury_entries_count_unmatched_and_duplicate_ids_without_inventing_health(self):
        def entry(player, status):
            links = [] if player is None else [{'href': f'https://example.test/player/_/id/{player}/name'}]
            return {'status': status, 'athlete': {'links': links}}

        report = {'injuries': [{'id': '10', 'injuries': [entry('1', 'Out'), entry('1', 'Out'),
                                                          entry('2', 'Day-To-Day'), entry(None, None)]}]}
        roster = {'1': {'team': '10'}, '2': {'team': '20'}}
        result = audit.report_entries(report, roster)
        self.assertEqual(result['statuses'], {'Out': 2, 'Day-To-Day': 1, 'Unknown': 1})
        self.assertEqual(result['matching'], {'matched_roster_team': 2, 'different_roster_team': 1,
                                              'missing_player_id': 1})
        self.assertEqual(result['duplicate_player_ids'], 1)

    def test_final_box_presence_does_not_infer_play_or_dnp(self):
        summary = {'header': {'competitions': [{'id': '7', 'status': {'type': {'completed': True}}}]},
                   'boxscore': {'players': [{'team': {'id': '10'}, 'statistics': [{'athletes': [
                       {'athlete': {'id': '1'}, 'didNotPlay': True},
                       {'athlete': {'id': '2'}, 'stats': ['30']},
                   ]}]}]}}
        self.assertEqual(audit.box_player_keys(summary, '7'), {('10', '1'), ('10', '2')})
        self.assertEqual(audit.box_presence(None, '10', '1'), 'final_box_missing')
        self.assertEqual(audit.box_presence(set(), '10', '1'), 'unlisted_in_final_box')
        self.assertEqual(audit.box_presence({('10', '1')}, '10', '1'), 'listed_in_final_box')
        with self.assertRaisesRegex(ValueError, 'not the expected final'):
            audit.box_player_keys(summary, '8')
        summary['boxscore']['players'][0]['statistics'][0]['athletes'].append(
            {'athlete': {'id': '1'}})
        with self.assertRaisesRegex(ValueError, 'repeats'):
            audit.box_player_keys(summary, '7')

    def test_missing_collection_report_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            result, paths, snapshots = audit.inventory(Path(folder), Path(folder))
        self.assertEqual(result['status'], 'missing_report')
        self.assertEqual(paths, [])
        self.assertEqual(snapshots, [])


if __name__ == '__main__':
    unittest.main()
