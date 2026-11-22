import unittest
from unittest.mock import patch

from scripts import nightly, views


class AvailabilityViewTests(unittest.TestCase):
    def setUp(self):
        self.game = {'game_id': 'g', 'home_id': '1', 'away_id': '2'}
        self.registry = {
            '10': {'team': '1', 'on_roster': True, 'name': 'Maybe', 'status': 'Questionable',
                   'reported_status': 'Questionable', 'status_source': 'injury_report',
                   'injury': {'comment': 'Original'}},
            '11': {'team': '1', 'on_roster': True, 'name': 'Out', 'status': 'Out', 'injury': None},
            '12': {'team': '2', 'on_roster': True, 'name': 'No report', 'status': None, 'injury': None},
            '13': {'team': '1', 'on_roster': False, 'name': 'Former', 'status': 'Out', 'injury': None},
            '14': {'team': '1', 'on_roster': True, 'name': 'Unlisted', 'status': 'Active',
                   'reported_status': None, 'status_source': 'not_listed_assumption', 'injury': None},
        }

    def test_forecast_report_is_immutable_against_later_roster_and_status_changes(self):
        report = nightly.forecast_availability_report(self.game, self.registry)
        self.registry['10']['injury']['comment'] = 'Later'
        self.registry['10']['reported_status'] = 'Out'
        saved = {entry['id']: entry for entry in report['home']}
        self.assertEqual(saved['10']['reported_status'], 'Questionable')
        self.assertEqual(saved['10']['status_source'], 'injury_report')
        self.assertIsNone(saved['14']['reported_status'])
        self.assertEqual(saved['14']['status_source'], 'not_listed_assumption')
        sim = {'availability_report': report,
               'home': {'players': [{'id': '10', 'name': 'Maybe', 'status': 'Questionable',
                                     'availability': 0.5, 'played': 0.4}]},
               'away': {'players': [{'id': '12', 'name': 'No report', 'status': 'Unknown',
                                     'availability': 0.6, 'played': 0.5}]}}
        result = views.availability(sim, lambda _: None)
        self.assertEqual(result['source'], 'snapshot')
        self.assertEqual({row['id']: row['status'] for row in result['home']},
                         {'10': 'Questionable', '11': 'Out'})
        self.assertEqual(next(row['comment'] for row in result['home'] if row['id'] == '10'), 'Original')
        self.assertEqual(result['away'][0]['status'], 'Unknown')
        self.assertNotIn('13', {row['id'] for row in result['home']})

    def test_old_snapshot_never_fills_report_gaps_from_a_later_registry(self):
        sim = {'home': {'players': [{'id': '10', 'name': 'Maybe', 'status': 'Unknown',
                                     'availability': 0.6, 'played': 0.4}]},
               'away': {'players': []}}
        result = views.availability(sim, lambda _: None)
        self.assertEqual(result['source'], 'partial-legacy')
        self.assertEqual([(row['id'], row['status']) for row in result['home']], [('10', 'Unknown')])

    def test_active_recent_inactivity_fallback_is_visible(self):
        report = {'home': [{'id': '10', 'name': 'Maybe', 'status': 'Active', 'injury': None}], 'away': []}
        sim = {'availability_report': report,
               'home': {'players': [{'id': '10', 'name': 'Maybe', 'status': 'Active',
                                     'availability': 0.5, 'availability_basis': 'recent_inactivity', 'played': 0.3}]},
               'away': {'players': []}}
        result = views.availability(sim, lambda _: None)
        self.assertEqual(result['home'][0]['basis'], 'recent_inactivity')
        self.assertEqual(result['home'][0]['assumed_availability'], 0.5)
        self.assertEqual(result['home'][0]['plays'], 0.3)

    def test_prospective_slate_attaches_its_report_to_the_saved_game(self):
        game = {**self.game, 'date_et': '2026-11-22', 'tip_utc': '2099-01-01T00:00:00Z'}
        result = {'home': {'players': []}, 'away': {'players': []}}
        with patch.object(nightly, 'team_table', return_value=({}, {'teams_gp': 20})), \
                patch.object(nightly, 'player_table', return_value={}), \
                patch.object(nightly, 'period_profiles', return_value=({}, {})), \
                patch.object(nightly.projection, 'simulate_game', return_value=result):
            part = nightly.project_slate('2026-11-22', {}, [game], [], [], self.registry, True, 100, period_rows=[])
        saved = {entry['id']: entry for entry in part['games']['g']['availability_report']['home']}
        self.assertEqual(saved['11']['status'], 'Out')


if __name__ == '__main__':
    unittest.main()
