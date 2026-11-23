import copy
import unittest
from unittest.mock import patch

import numpy as np

from scripts import forecast_output, pathway, projection


def toy():
    # A formatter fixture, not a legal basketball simulation: one player per side, four possible outcomes.
    teams = {}
    for side, pid in [('home', '1'), ('away', '2')]:
        box = {key: np.zeros((4, 1, 5), np.int16) for key in projection.BOX}
        makes = np.array([0, 5, 10, 15]) if side == 'home' else np.full(4, 4)
        box['fgm'][:, 0, 0] = makes
        box['fga'][:, 0, 0] = makes + (makes > 0)
        box['pts'][:, 0, 0] = 2 * makes
        minutes = np.zeros((4, 1, 5), np.float64)
        minutes[:, 0, 0] = [0., .001, 29.999, 30.001] if side == 'home' else 10.
        teams[side] = {'tid': pid, 'box': box, 'minutes': minutes,
                       'players': [{'id': pid, 'name': pid, 'pos': 'G', 'jersey': pid, 'starter': True,
                                    'status': 'Active', 'injury': None, 'availability': 1., 'base_min': 20.}]}
    return teams


def package(function, teams, weights=None):
    points = {side: team['box']['pts'].sum(1) for side, team in teams.items()}
    W = len(teams['home']['minutes'])
    args = ({'game_id': '1'}, teams, points, np.zeros(W, int), W, {'mu_home': 22., 'mu_away': 8., 'pace': 100.}, 'fixture')
    return function(*args, **({'weights': weights} if weights is not None else {}))


class ForecastOutputTests(unittest.TestCase):
    def test_integer_replication_is_an_independent_full_contract_reference(self):
        teams = toy()
        weights = np.array([3, 3, 17, 17])
        expanded = copy.deepcopy(teams)
        for team in expanded.values():
            team['minutes'] = np.repeat(team['minutes'], weights, axis=0)
            team['box'] = {key: np.repeat(value, weights, axis=0) for key, value in team['box'].items()}
        expected = package(projection.package, expanded)
        actual = package(forecast_output.game, teams, weights)
        self.assertEqual(actual.pop('probability_mass'), 40)
        self.assertEqual(actual.pop('weighted_worlds_schema'), 1)
        self.assertEqual(actual['sims'], 4)
        actual['sims'] = 40  # Only representation counts differ; every probability/moment/histogram must agree.
        self.assertEqual(actual, expected)
        player = actual['home']['players'][0]
        self.assertEqual(player['played'], .925)
        self.assertEqual(player['periods']['fg']['stats']['fgpct']['defined'], 37)
        self.assertEqual(player['if_plays']['pts'], 23.784)

    def season_fixture(self):
        teams = {str(i): {'conf': 'East' if i < 3 else 'West'} for i in range(1, 5)}
        standings = {tid: {'w': 0, 'l': 0} for tid in teams}
        master = [{'game_id': str(i), 'home_id': home, 'away_id': away, 'date_et': day,
                   'tip_utc': day + 'T20:00:00Z', 'status': 'scheduled'}
                  for i, (home, away, day) in enumerate([('1', '2', '2026-01-01'), ('1', '3', '2026-01-02'), ('2', '4', '2026-01-03')], 1)]
        won = np.array([[0, 0, 1], [0, 1, 1], [1, 0, 0], [1, 1, 0]], bool)
        points = np.stack([100 + 10 * won, 110 - 10 * won], axis=2).astype(np.int16)
        return teams, standings, master, {'home_win': won, 'points': points}

    def test_weighted_season_matches_independent_path_replication(self):
        teams, T, master, played = self.season_fixture()
        weights = np.array([3, 3, 17, 17])
        expanded = {key: np.repeat(value, weights, axis=0) for key, value in played.items()}
        ties = np.random.default_rng(123).random((4, 4))
        class FixedTies:
            def __init__(self, values):
                self.values = values
            def random(self, shape):
                if shape != self.values.shape:
                    raise ValueError('unexpected standings draw shape')
                return self.values.copy()
        with patch.object(pathway, 'play', return_value=expanded), patch.object(projection, 'rng_for', return_value=FixedTies(np.repeat(ties, weights, axis=0))):
            expected = projection.simulate_season(T, {}, master, '2026-01-01', teams, sims=40)
        actual = forecast_output.season(T, master, '2026-01-01', teams, played, FixedTies(ties), weights=weights)
        self.assertEqual(actual.pop('probability_mass'), 40)
        self.assertEqual(actual.pop('weighted_paths_schema'), 1)
        self.assertEqual(actual['sims'], 4)
        actual['sims'] = 40
        actual['notes'].pop()
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
