import unittest

import numpy as np
import pandas as pd

from analysis.a2_late_clock import Pool, cell, fit, predict, valid


class LateClockTests(unittest.TestCase):
    def test_exact_crps_matches_independent_pairwise_definition(self):
        values = np.array([0., 1., 3., 6., 24.])
        for cap, y in ((.4, .3), (4., 0.), (4., 4.), (24., 12.3)):
            x = np.minimum(values, cap)
            expected = np.abs(x - y).mean() - np.abs(x[:, None] - x).mean() / 2
            self.assertAlmostEqual(float(Pool(values, .2).score(y, cap)), expected)

    def frame(self):
        n = 200
        return pd.DataFrame({'game_id': np.repeat(np.arange(40).astype(str), 5), 'date_et': '2023-12-01',
                             'game_ok': True, 'start_clock': 20., 'shot_time': np.tile([1., 3., 5., 7., 20.], 40),
                             'end_type': np.tile(['shot'] * 4 + ['end_period'], 40), 'period': 4,
                             'score_off': 90., 'score_def': 95.})

    def test_cutoff_and_quiet_endings(self):
        history = self.frame()
        ending = history['end_type'].eq('end_period')
        history.loc[ending, 'shot_time'] = np.nan
        future = self.frame().assign(date_et='2024-01-01', shot_time=0)
        a = fit(history, '2023-12-31')
        b = fit(pd.concat([history, future]), '2023-12-31')
        key = int(cell(np.array([20.]), np.array([-5.]))[0])
        np.testing.assert_array_equal(a['contextual'][key].x, b['contextual'][key].x)
        self.assertEqual(a['contextual'][key].quiet, .2)
        self.assertEqual(a['contextual'][key].x[-1], 1.)
        with self.assertRaises(ValueError):
            fit(history, '2026-07-01')

    def test_fallbacks_and_period_scope(self):
        history = self.frame()
        table = fit(history, '2023-12-31')
        queries = history.iloc[:3].copy().reset_index(drop=True)
        queries.loc[1, 'score_off'] = 100  # Unsupported positive margin uses bridge.
        queries.loc[2, 'period'] = 3  # Earlier quarters must keep exact legacy.
        result = predict(table, queries)
        self.assertEqual(result['candidate_source'].tolist(), ['contextual', 'bridge', 'legacy'])
        self.assertEqual(result.loc[2, 'candidate_joint'], result.loc[2, 'legacy_joint'])
        table['bridge'] = {}
        self.assertEqual(predict(table, queries).loc[1, 'candidate_source'], 'legacy')

    def test_invalid_rows_and_disjoint_boundaries(self):
        frame = self.frame().iloc[:4].copy()
        frame['shot_time'] = [-1, 21, np.nan, 0]
        self.assertEqual(valid(frame).tolist(), [False, False, False, True])
        np.testing.assert_array_equal(cell(np.array([4, 4.1, 8, 8.1, 16, 16.1, 24]), np.zeros(7)), [3, 10, 10, 17, 17, 24, 24])


if __name__ == '__main__':
    unittest.main()
