import unittest

import numpy as np
import pandas as pd

from analysis.rule3_final import prior_medians
from scripts import engine


class FinalCutoffTests(unittest.TestCase):
    def test_same_date_and_future_profiles_cannot_change_prior_fills(self):
        columns = engine.OFF_REL + engine.DEF_REL
        rows = pd.DataFrame({'date_et': ['2026-10-01', '2026-10-10', '2026-10-11'],
                             **{c: [2., 100., 10000.] for c in columns}})
        actual = prior_medians(rows, ['2026-10-10', '2026-10-11'])
        self.assertTrue(all(x == 2. for x in actual['2026-10-10'].values()))
        self.assertTrue(all(x == 51. for x in actual['2026-10-11'].values()))
        changed = rows.copy()
        changed.loc[changed.date_et.ge('2026-10-10'), list(columns)] = -99999.
        self.assertEqual(prior_medians(changed, ['2026-10-10'])['2026-10-10'], actual['2026-10-10'])

    def test_missing_prior_support_fails_instead_of_using_future(self):
        frame = pd.DataFrame({'date_et': ['2026-10-10'], **{c: [1.] for c in engine.OFF_REL + engine.DEF_REL}})
        with self.assertRaises(ValueError):
            prior_medians(frame, ['2026-10-10'])


if __name__ == '__main__':
    unittest.main()
