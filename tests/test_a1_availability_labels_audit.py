import unittest

import pandas as pd

from scripts import a1_availability_labels_audit as audit


class LabelsAuditTests(unittest.TestCase):
    def test_prior_membership_excludes_same_day_and_ambiguous_team(self):
        history = pd.DataFrame([
            ('2026-01-01', 'a', 'old'), ('2026-01-02', 'a', 'new'),
            ('2026-01-02', 'b', 'old'), ('2026-01-02', 'b', 'new'),
            ('2026-01-03', 'a', 'future'), ('2026-01-03', 'c', 'old'),
        ], columns=['day', 'player', 'team'])
        result = audit.latest_membership(history, '2026-01-03')
        self.assertEqual(result.to_dict('records'), [{'prior_day': '2026-01-02', 'player': 'a', 'team': 'new'}])

    def test_reason_labels_do_not_infer_health_or_turn_other_reasons_into_rest(self):
        self.assertEqual(audit.reason_category("COACH'S DECISION"), 'coach')
        self.assertEqual(audit.reason_category('REST'), 'rest')
        self.assertEqual(audit.reason_category('LOWER BACK INJURY MANAGEMENT'), 'explicit_injury')
        self.assertEqual(audit.reason_category('INJURY/ILLNESS'), 'injury_or_illness')
        self.assertEqual(audit.reason_category('ILLNESS'), 'illness')
        self.assertEqual(audit.reason_category('NOT WITH TEAM'), 'other_recorded_reason')
        self.assertEqual(audit.reason_category(None), 'missing_reason')


if __name__ == '__main__':
    unittest.main()
