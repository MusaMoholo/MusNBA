import unittest

from scripts import a1_substitutions


def player(pid, team, starter):
    return {'id': pid, 'team': team, 'starter': starter, 'dnp': False, 'pos': 'G', 'box': {'min': None}}


def event(seq, kind, clock, *, team=None, participants=(), home_score=0, away_score=0, points=0):
    return {'seq': seq, 'type_id': '584' if kind == 'Substitution' else '1', 'type_text': kind, 'text': kind,
            'period': 1, 'clock': clock, 'team': team, 'participants': list(participants),
            'shooting': 'Free Throw' in kind, 'scoring': points > 0, 'score_value': points,
            'points_attempted': 1 if 'Free Throw' in kind else 0, 'home_score': home_score, 'away_score': away_score}


def game(events):
    return {'id': '1', 'date_et': '2025-01-01', 'season': 2025, 'season_type': 2, 'home': 'h', 'away': 'a',
            'players': [player(f'h{i}', 'h', i < 5) for i in range(6)]
            + [player(f'a{i}', 'a', i < 5) for i in range(6)], 'plays': events}


class SequentialSubstitutionTests(unittest.TestCase):
    def test_same_clock_scores_and_reversals_keep_pre_substitution_state(self):
        events = [
            event(1, 'Full Timeout', '8:00'),
            event(2, 'Substitution', '8:00', team='h', participants=('h5', 'h0')),
            event(3, 'Free Throw - 2 of 2', '8:00', team='h', home_score=1, points=1),
            event(4, 'Full Timeout', '8:00', home_score=1),
            event(5, 'Substitution', '8:00', team='h', participants=('h0', 'h5'), home_score=1),
            event(6, 'Substitution', '8:00', team='h', participants=('h5', 'h0'), home_score=1),
            event(7, 'Full Timeout', '7:00', home_score=1),
            event(8, 'Layup Shot', '6:50', home_score=1),
        ]
        windows, report = a1_substitutions.windows_for_game(game(events))
        changed = [row for row in windows if row['home_subs']]
        self.assertEqual([row['margin_home'] for row in changed], [0, 1, 1])
        self.assertIn('h0', changed[0]['home_five_before'])
        self.assertIn('h5', changed[1]['home_five_before'])
        self.assertIn('h0', changed[2]['home_five_before'])
        self.assertEqual(changed[2]['kind'], 'sequential_sub_only')
        no_sub = [row for row in windows if row['kind'] == 'timeout' and not row['home_subs'] and not row['away_subs']]
        self.assertEqual(len(no_sub), 1)
        self.assertEqual(report['substitutions'], 3)

    def test_duplicate_sequence_or_impossible_substitution_is_quarantined(self):
        duplicate = [event(1, 'Full Timeout', '8:00'), event(1, 'Layup Shot', '8:00')]
        with self.assertRaisesRegex(a1_substitutions.InvalidGame, 'duplicate sequence'):
            a1_substitutions.windows_for_game(game(duplicate))
        impossible = [event(1, 'Substitution', '8:00', team='h', participants=('h0', 'h5'))]
        with self.assertRaisesRegex(a1_substitutions.InvalidGame, 'on-court player'):
            a1_substitutions.windows_for_game(game(impossible))

    def test_clock_orders_distinct_times_before_feed_sequence(self):
        events = [event(2, 'Full Timeout', '8:00'),
                  event(1, 'Free Throw - 1 of 1', '7:59', team='h', home_score=1, points=1)]
        windows, _ = a1_substitutions.windows_for_game(game(events))
        self.assertEqual([(row['trigger_seq'], row['home_score']) for row in windows], [(2, 0), (1, 1)])

    def test_later_or_inconsistent_score_cannot_be_used(self):
        bad = [event(1, 'Full Timeout', '8:00', home_score=1)]
        with self.assertRaisesRegex(a1_substitutions.InvalidGame, 'reported scoreboard'):
            a1_substitutions.windows_for_game(game(bad))
        missing_fouler = [event(1, 'Personal Foul', '8:00')]
        with self.assertRaisesRegex(a1_substitutions.InvalidGame, 'no identified player'):
            a1_substitutions.windows_for_game(game(missing_fouler))


if __name__ == '__main__':
    unittest.main()
