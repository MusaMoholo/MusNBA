import unittest

import numpy as np

from scripts import a1_substitution_world_audit as audit


def fixture():
    side = np.array([0] * 6 + [1] * 5)
    original = np.array([[0, 1, 2, 3, 4], [6, 7, 8, 9, 10]])
    changed = np.array([[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])
    fives = np.stack([original] + [changed] * 5)
    minutes = np.zeros((1, 11, 5))
    minutes[0, original.reshape(-1), 0] += 5
    minutes[0, changed.reshape(-1), 0] += 7
    for q in range(1, 4):
        minutes[0, changed.reshape(-1), q] += 12
    minutes[0, changed.reshape(-1), 4] += 5
    points = np.zeros((1, 11, 5), dtype=int)
    points[0, 0, 0] = 2
    points[0, 6, 3] = 3
    team_points = np.zeros((1, 2, 5), dtype=int)
    team_points[0, 0, 0], team_points[0, 1, 3] = 2, 3
    player_fouls = np.zeros_like(points)
    player_fouls[0, 0, 0] = 6
    trace_fouls = np.zeros((6, 2, 5))
    trace_fouls[0, 0, 0] = 5
    return {
        'game_id': np.asarray('1'),
        'player_ids': np.array([str(i) for i in range(11)]),
        'side': side,
        'available': np.ones((1, 11), dtype=bool),
        'final_period': np.array([5]),
        'final_score': np.array([[2, 3]]),
        'minutes': minutes,
        'player_points': points,
        'player_fouls': player_fouls,
        'team_points': team_points,
        'trace_world': np.zeros(6, dtype=int),
        'trace_period': np.array([1, 1, 2, 3, 4, 5]),
        'trace_clock': np.array([720., 420., 720., 720., 720., 300.]),
        'trace_lineups': fives,
        'trace_fouls': trace_fouls,
        'trace_phase': np.array([0, 1, 0, 0, 0, 0]),
    }


def penalty_fixture():
    data = fixture()
    data['available'][0, 5] = False
    data['trace_lineups'][:] = data['trace_lineups'][0]
    data['minutes'][:] = 0
    on_court = data['trace_lineups'][0].reshape(-1)
    data['minutes'][0, on_court, :4] = 12
    data['minutes'][0, on_court, 4] = 5
    data['trace_fouls'][1:, 0, 0] = 6
    data['trace_all_fouls'] = np.zeros((6, 11))
    data['trace_all_fouls'][0, 0] = 5
    data['trace_all_fouls'][1:, 0] = 6
    data['player_ft_pct'] = np.zeros(11)
    data['player_ft_pct'][6] = 1
    data['player_fta'] = np.zeros_like(data['player_points'])
    data['player_ftm'] = np.zeros_like(data['player_points'])
    data['player_fta'][0, 6, 0] = 1
    data['player_ftm'][0, 6, 0] = 1
    data['player_points'][0, 6, 0], data['player_points'][0, 6, 3] = 1, 2
    data['team_points'][0, 1, 0], data['team_points'][0, 1, 3] = 1, 2
    for key, value in {'world': 0, 'period': 1, 'clock': 420., 'fouler': 0, 'shooter': 6,
                       'made': 1, 'probability': 1.}.items():
        data[f'technical_{key}'] = np.array([value])
    return data


class WorldAuditTests(unittest.TestCase):
    def test_replays_foul_replacement_periods_and_overtime(self):
        result = audit.audit_worlds(fixture())
        self.assertEqual(result['worlds'], 1)
        self.assertEqual(result['lineup_fives_checked'], 12)
        self.assertEqual(result['post_foul_snapshots'], 1)
        self.assertLess(result['max_replayed_player_minute_error'], 1e-10)

    def test_detects_a_conserved_but_wrong_individual_minute_allocation(self):
        data = fixture()
        data['minutes'][0, 0, 0] += 1
        data['minutes'][0, 1, 0] -= 1
        with self.assertRaisesRegex(ValueError, 'lineup-replayed player minutes'):
            audit.audit_worlds(data)

    def test_rejects_illegal_fives_and_unreconciled_points(self):
        data = fixture()
        data['trace_lineups'][0, 0, 1] = 0
        with self.assertRaisesRegex(ValueError, 'five distinct'):
            audit.audit_worlds(data)
        data = fixture()
        data['trace_fouls'][0, 0, 0] = 6
        with self.assertRaisesRegex(ValueError, 'disqualified'):
            audit.audit_worlds(data)
        data = fixture()
        data['player_points'][0, 0, 0] += 1
        with self.assertRaisesRegex(ValueError, 'player points do not equal'):
            audit.audit_worlds(data)

    def test_requires_an_observed_start_for_every_period(self):
        data = fixture()
        for key in ('trace_world', 'trace_period', 'trace_clock', 'trace_lineups', 'trace_fouls', 'trace_phase'):
            data[key] = np.delete(data[key], 2, axis=0)
        with self.assertRaisesRegex(ValueError, 'no traced start for period 2'):
            audit.audit_worlds(data)

    def test_audits_foul_penalty_and_technical_attempt(self):
        result = audit.audit_worlds(penalty_fixture(), foul_penalty=True)
        self.assertEqual(result['foul_penalty_events'], 1)
        self.assertEqual(result['foul_penalty_makes'], 1)
        self.assertEqual(result['foul_penalty_lineups'], 5)

    def test_rejects_missing_technical_and_available_replacement(self):
        data = penalty_fixture()
        for key in ('world', 'period', 'clock', 'fouler', 'shooter', 'made', 'probability'):
            data[f'technical_{key}'] = data[f'technical_{key}'][:0]
        with self.assertRaisesRegex(ValueError, 'no technical free throw'):
            audit.audit_worlds(data, foul_penalty=True)
        data = penalty_fixture()
        data['available'][0, 5] = True
        with self.assertRaisesRegex(ValueError, 'five eligible players'):
            audit.audit_worlds(data, foul_penalty=True)

    def test_rejects_wrong_side_or_unreconciled_technical(self):
        data = penalty_fixture()
        data['technical_shooter'][0] = 1
        with self.assertRaisesRegex(ValueError, 'opposing five'):
            audit.audit_worlds(data, foul_penalty=True)
        data = penalty_fixture()
        data['player_ftm'][0, 6, 0] = 0
        with self.assertRaisesRegex(ValueError, 'do not reconcile'):
            audit.audit_worlds(data, foul_penalty=True)


if __name__ == '__main__':
    unittest.main()
