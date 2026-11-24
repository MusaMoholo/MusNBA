import gzip
import json
import tempfile
import unittest
import warnings
from pathlib import Path

from scripts import box_scores, projection


def save(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, 'wt', encoding='utf-8') as stream:
        json.dump(document, stream)


class RosterAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.run_path = Path(self.directory.name)
        save(self.run_path / 'roster/1.json.gz', {
            'team': {'id': '1'},
            'athletes': [
                {'id': '10', 'displayName': 'Unreported'},
                {'id': '11', 'displayName': 'Questionable', 'injuries': [{'status': 'Questionable'}]},
                {'id': '12', 'displayName': 'Unknown injury', 'injuries': [{}]},
            ],
        })

    def test_missing_report_does_not_make_unreported_players_active(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            players = box_scores.roster_registry(self.run_path)
        self.assertEqual(players['10']['status'], 'Unknown')
        self.assertIsNone(players['10']['reported_status'])
        self.assertEqual(players['10']['status_source'], 'missing_report')
        self.assertEqual(projection.availability(players['10']['status']), 0.5)
        self.assertEqual(players['11']['status'], 'Questionable')
        self.assertEqual(players['11']['reported_status'], 'Questionable')
        self.assertEqual(players['11']['status_source'], 'roster_injury')
        self.assertEqual(players['12']['status'], 'Unknown')
        self.assertTrue(any('injury report' in str(item.message).lower() for item in caught))

    def test_missing_and_wrong_team_report_status_stays_unknown(self):
        save(self.run_path / 'injuries.json.gz', {'injuries': [
            {'id': '1', 'injuries': [{'athlete': {'links': [{'href': '/id/10/'}]}, 'details': {}}]},
            {'id': '2', 'injuries': [{'athlete': {'links': [{'href': '/id/11/'}]}, 'status': 'Out'}]},
        ]})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            players = box_scores.roster_registry(self.run_path)
        self.assertEqual(players['10']['status'], 'Unknown')
        self.assertIsNone(players['10']['reported_status'])
        self.assertEqual(players['10']['status_source'], 'injury_report')
        self.assertEqual(players['11']['status'], 'Unknown')
        self.assertIsNone(players['11']['reported_status'])
        self.assertEqual(players['11']['status_source'], 'team_conflict')
        self.assertEqual(players['12']['status'], 'Unknown')
        self.assertTrue(any('team' in str(item.message).lower() for item in caught))

    def test_matching_report_and_no_injury_keep_existing_statuses(self):
        save(self.run_path / 'injuries.json.gz', {'injuries': [
            {'id': '1', 'injuries': [{'athlete': {'links': [{'href': '/id/11/'}]}, 'status': 'Out'}]},
            {'id': '2', 'injuries': [{'athlete': {'links': [{'href': '/id/11/'}]}, 'status': 'Questionable'}]},
        ]})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            players = box_scores.roster_registry(self.run_path)
        self.assertEqual(players['10']['status'], 'Active')
        self.assertIsNone(players['10']['reported_status'])
        self.assertEqual(players['10']['status_source'], 'not_listed_assumption')
        self.assertEqual(players['11']['status'], 'Out')
        self.assertEqual(players['11']['reported_status'], 'Out')
        self.assertEqual(players['11']['status_source'], 'injury_report')
        self.assertEqual(projection.availability(players['11']['status']), 0.0)
        self.assertTrue(any('team' in str(item.message).lower() for item in caught))

    def test_player_on_multiple_team_rosters_is_not_assigned_arbitrarily(self):
        save(self.run_path / 'roster/2.json.gz', {'team': {'id': '2'}, 'athletes': [{'id': '10'}]})
        save(self.run_path / 'injuries.json.gz', {'injuries': []})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            players = box_scores.roster_registry(self.run_path)
        self.assertNotIn('10', players)
        self.assertTrue(any('multiple' in str(item.message).lower() for item in caught))

    def test_unidentifiable_report_entry_is_not_treated_as_healthy(self):
        save(self.run_path / 'injuries.json.gz', {'injuries': [
            {'id': '1', 'injuries': [{'athlete': {}, 'status': 'Out'}]},
        ]})
        with self.assertRaisesRegex(ValueError, 'player ID'):
            box_scores.roster_registry(self.run_path)

    def test_malformed_injury_report_is_rejected(self):
        save(self.run_path / 'injuries.json.gz', {'message': 'unavailable'})
        with self.assertRaisesRegex(ValueError, 'team list'):
            box_scores.roster_registry(self.run_path)

    def test_numeric_identifiers_match_string_report_links(self):
        save(self.run_path / 'roster/1.json.gz', {'team': {'id': 1}, 'athletes': [{'id': 10}]})
        save(self.run_path / 'injuries.json.gz', {'injuries': [
            {'id': 1, 'injuries': [{'athlete': {'links': [{'href': '/id/10/'}]}, 'status': 'Out'}]},
        ]})
        players = box_scores.roster_registry(self.run_path)
        self.assertEqual(players['10']['team'], '1')
        self.assertEqual(players['10']['status'], 'Out')

    def test_missing_roster_identifier_is_rejected(self):
        save(self.run_path / 'roster/1.json.gz', {'team': {'id': '1'}, 'athletes': [{'id': None}]})
        save(self.run_path / 'injuries.json.gz', {'injuries': []})
        with self.assertRaisesRegex(ValueError, 'roster player ID'):
            box_scores.roster_registry(self.run_path)


if __name__ == '__main__':
    unittest.main()
