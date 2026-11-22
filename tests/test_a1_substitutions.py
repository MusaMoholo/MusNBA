import contextlib
import io
import json
import math
import unittest

import pandas as pd

from basketball_common import NBA_TEAM_IDS
from scripts import (a1_substitution_audit, a1_substitution_dataset, a1_substitution_dataset_audit,
                     a1_substitution_fold_data, a1_substitution_in_coverage, a1_substitution_in_screen,
                     a1_substitution_in_screen_audit,
                     a1_substitution_opportunities,
                     a1_substitution_out_screen,
                     a1_substitution_screen_audit, a1_substitution_seed_audit, a1_substitution_states, a1_substitutions)


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


def audit_fixture():
    row = {'game_id': '1', 'date_et': '2025-01-01', 'period': 1, 'clock': 600., 't': 120., 'trigger_seq': 1,
           'window_id': '1:0', 'kind': 'timeout', 'home': '10', 'away': '20',
           'home_score': 0, 'away_score': 0, 'margin_home': 0, 'home_subs': 1, 'away_subs': 0,
           'home_players': ['1', '2', '3', '4', '5', '6'], 'away_players': ['7', '8', '9', '10', '11'],
           'home_five_before': ['1', '2', '3', '4', '5'], 'away_five_before': ['7', '8', '9', '10', '11'],
           'home_five_after': ['2', '3', '4', '5', '6'], 'away_five_after': ['7', '8', '9', '10', '11'],
           'home_seconds_before': [120., 120., 120., 120., 120., 0.],
           'away_seconds_before': [120., 120., 120., 120., 120.],
           'home_fouls_before': [0] * 6, 'away_fouls_before': [0] * 5,
           'home_stint_before': [120., 120., 120., 120., 120., None],
           'away_stint_before': [120.] * 5,
           'home_rest_before': [None, None, None, None, None, 120.],
           'away_rest_before': [None] * 5,
           'changes_json': json.dumps([{'seq': 2, 'team': '10', 'player_in': '6', 'player_out': '1'}])}
    raw = pd.DataFrame([
        {'game_id': 1, 'period_number': 1, 'clock_display_value': '10:00', 'sequence_number': 1,
         'type_id': 1, 'type_text': 'Full Timeout', 'home_score': 0, 'away_score': 0,
         'team_id': 10, 'athlete_id_1': None, 'athlete_id_2': None},
        {'game_id': 1, 'period_number': 1, 'clock_display_value': '10:00', 'sequence_number': 2,
         'type_id': 584, 'type_text': 'Substitution', 'home_score': 0, 'away_score': 0,
         'team_id': 10, 'athlete_id_1': 6, 'athlete_id_2': 1},
    ])
    report = {'requested_games': 1, 'rejected_games': [], 'counts': {'windows': 1, 'events': 2, 'substitutions': 1},
              'no_substitution_windows': 0}
    return pd.DataFrame([row]), raw, report


def target_fixture():
    return pd.DataFrame([{'game_id': '1', 'team': '10' if player <= 6 else '20', 'player': str(player),
                          'date_et': '2025-01-01', 'prior_day': '2024-12-31',
                          'prior_profile_date': pd.Timestamp('2024-12-30'), 'tier': 'bench', 'control_mean': 20.}
                         for player in range(1, 12)])


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

    def test_jump_shots_do_not_create_no_substitution_opportunities(self):
        events = [event(1, 'Jump Shot', '8:00'), event(2, 'Pullup Jump Shot', '7:50'),
                  event(3, 'Jumpball', '7:40')]
        windows, _ = a1_substitutions.windows_for_game(game(events))
        self.assertEqual([(row['trigger_seq'], row['kind']) for row in windows], [(3, 'jump_ball')])

    def test_excess_timeout_technical_is_not_a_timeout_opportunity(self):
        events = [event(1, 'Excess Timeout Technical', '8:00'), event(2, 'Full Timeout', '7:50')]
        windows, _ = a1_substitutions.windows_for_game(game(events))
        self.assertEqual([(row['trigger_seq'], row['kind']) for row in windows], [(2, 'timeout')])

    def test_later_or_inconsistent_score_cannot_be_used(self):
        bad = [event(1, 'Full Timeout', '8:00', home_score=1)]
        with self.assertRaisesRegex(a1_substitutions.InvalidGame, 'reported scoreboard'):
            a1_substitutions.windows_for_game(game(bad))
        missing_fouler = [event(1, 'Personal Foul', '8:00')]
        with self.assertRaisesRegex(a1_substitutions.InvalidGame, 'no identified player'):
            a1_substitutions.windows_for_game(game(missing_fouler))

    def test_independent_audit_detects_changed_score_and_lineup(self):
        rows, raw, report = audit_fixture()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = a1_substitution_audit.audit(rows, raw, report)
        self.assertIn('windows 1/1', output.getvalue())
        self.assertEqual(result['counts']['substitutions'], 1)
        changed = rows.copy()
        changed.at[0, 'home_score'] = 1
        with self.assertRaisesRegex(ValueError, 'score differs'):
            a1_substitution_audit.audit(changed, raw, report)
        changed = pd.DataFrame([{**rows.to_dict('records')[0], 'home_five_after': ['1', '2', '3', '4', '5']}])
        with self.assertRaisesRegex(ValueError, 'final lineup'):
            a1_substitution_audit.audit(changed, raw, report)

    def test_timeout_opportunities_reject_other_same_clock_substitutions(self):
        rows, raw, _ = audit_fixture()
        retained, counts = a1_substitution_opportunities.timeout_opportunities(rows, raw)
        self.assertEqual(len(retained), 1)
        self.assertEqual(counts['window_counts']['with_substitution'], 1)
        no_change = pd.DataFrame([{**rows.to_dict('records')[0], 'home_subs': 0, 'changes_json': '[]'}])
        retained, counts = a1_substitution_opportunities.timeout_opportunities(no_change, raw.iloc[:1])
        self.assertEqual(counts['window_counts']['without_substitution'], 1)
        self.assertEqual(len(retained), 1)
        with self.assertRaisesRegex(ValueError, 'empty or incomplete'):
            a1_substitution_opportunities.timeout_opportunities(no_change, raw)

    def test_state_response_uses_before_lineup_and_pre_game_role(self):
        rows, _, _ = audit_fixture()
        roles = pd.DataFrame([{'game_id': '1', 'player': '1', 'tier': 'star', 'team_control': '10',
                               'date_et_control': '2025-01-01', 'role_missing': False}])
        states = a1_substitution_states.player_states(rows, roles).set_index('player')
        self.assertEqual(states.loc['1', 'decision'], 'out')
        self.assertTrue(states.loc['1', 'changed'])
        self.assertEqual(states.loc['1', 'tier'], 'star')
        self.assertEqual(states.loc['6', 'decision'], 'in')
        self.assertTrue(states.loc['6', 'changed'])
        self.assertTrue(states.loc['6', 'role_missing'])
        self.assertEqual(states.loc['1', 'margin'], 'close_5_or_less')

    def test_target_deficit_uses_pre_window_seconds_and_unknown_incoming_labels(self):
        windows, raw, _ = audit_fixture()
        targets = target_fixture()
        states, counts = a1_substitution_dataset.build(windows, targets, raw)
        out = states[(states['decision'] == 'out') & (states['player'] == '1')].iloc[0]
        incoming = states[(states['decision'] == 'in') & (states['player'] == '6')].iloc[0]
        self.assertAlmostEqual(out['target_deficit'], 20 * 120 / 2880 - 2)
        self.assertTrue(out['label'])
        self.assertTrue(incoming['label'])
        self.assertEqual(incoming['eligibility'], 'current_unknown')
        self.assertEqual(counts['incoming_outside_pre_window_candidates'], 0)
        altered = targets.copy()
        altered.loc[altered['player'] == '1', 'prior_day'] = '2025-01-01'
        with self.assertRaisesRegex(ValueError, 'prior roster dates'):
            a1_substitution_dataset.build(windows, altered, raw)

    def test_future_participant_does_not_change_pre_window_candidate_features(self):
        windows, raw, _ = audit_fixture()
        row = {**windows.to_dict('records')[0], 'home_subs': 0, 'changes_json': '[]',
               'home_five_after': ['1', '2', '3', '4', '5']}
        without_future = dict(row)
        for field in ('players', 'seconds_before', 'fouls_before', 'stint_before', 'rest_before'):
            without_future[f'home_{field}'] = row[f'home_{field}'][:5]
        first, _ = a1_substitution_dataset.build(pd.DataFrame([without_future]), target_fixture(), raw.iloc[:1])
        second, _ = a1_substitution_dataset.build(pd.DataFrame([row]), target_fixture(), raw.iloc[:1])
        first_player = first[(first['decision'] == 'in') & (first['player'] == '6')].reset_index(drop=True)
        second_player = second[(second['decision'] == 'in') & (second['player'] == '6')].reset_index(drop=True)
        pd.testing.assert_frame_equal(first_player, second_player)
        self.assertTrue(pd.isna(first_player.loc[0, 'label']))
        self.assertTrue(pd.isna(first_player.loc[0, 'rest_before']))

    def test_earlier_ejection_marks_incoming_candidate_ineligible(self):
        windows, raw, _ = audit_fixture()
        row = {**windows.to_dict('records')[0], 'home_subs': 0, 'changes_json': '[]',
               'home_five_after': ['1', '2', '3', '4', '5']}
        ejection = {'game_id': 1, 'period_number': 1, 'clock_display_value': '11:00', 'sequence_number': 3,
                    'type_id': 1, 'type_text': 'Ejection', 'home_score': 0, 'away_score': 0,
                    'team_id': 10, 'athlete_id_1': 6, 'athlete_id_2': None}
        prior = pd.concat([raw.iloc[:1], pd.DataFrame([ejection])], ignore_index=True)
        states, _ = a1_substitution_dataset.build(pd.DataFrame([row]), target_fixture(), prior)
        incoming = states[(states['decision'] == 'in') & (states['player'] == '6')].iloc[0]
        self.assertEqual(incoming['eligibility'], 'known_ineligible')
        self.assertTrue(pd.isna(incoming['label']))

    def test_independent_dataset_audit_rejects_tampered_target(self):
        windows, raw, _ = audit_fixture()
        targets = target_fixture()
        states, _ = a1_substitution_dataset.build(windows, targets, raw)
        accounting = a1_substitution_dataset_audit.audit(states, windows, targets, raw)
        self.assertEqual(accounting['raw_substitutions'], 1)
        changed = states.copy()
        changed.loc[0, 'target_deficit'] = 999.
        with self.assertRaisesRegex(ValueError, 'target deficit differs'):
            a1_substitution_dataset_audit.audit(changed, windows, targets, raw)

    def test_seed_selection_ignores_future_games_and_rejects_ambiguous_sides(self):
        teams = sorted(NBA_TEAM_IDS)
        games = pd.DataFrame([{'game_id': str(index), 'date_et': '2023-02-01', 'game_ok': True,
                               'season_type': 2, 'offense': teams[0], 'defense': teams[1], 'off_home': True}
                              for index in range(210)])
        expected = a1_substitution_fold_data.seed_games(games)
        future = pd.DataFrame([{**games.iloc[0].to_dict(), 'game_id': '999999', 'date_et': '2026-07-01'}])
        pd.testing.assert_frame_equal(expected, a1_substitution_fold_data.seed_games(pd.concat([games, future])))
        changed_side = pd.DataFrame([{**games.iloc[0].to_dict(), 'defense': teams[2]}])
        with self.assertRaisesRegex(ValueError, 'ambiguous sides'):
            a1_substitution_fold_data.seed_games(pd.concat([games, changed_side]))

    def test_unidentified_ejection_quarantines_only_its_game(self):
        windows, raw, _ = audit_fixture()
        ejection = {'game_id': 1, 'period_number': 1, 'clock_display_value': '11:00', 'sequence_number': 3,
                    'type_id': 1, 'type_text': 'Ejection', 'athlete_id_1': None}
        mixed = pd.concat([raw, pd.DataFrame([ejection])], ignore_index=True)
        retained, excluded = a1_substitution_fold_data.exclude_unidentified_ejections(windows, mixed)
        self.assertTrue(retained.empty)
        self.assertEqual(excluded[0]['game_id'], '1')
        mixed.loc[mixed['type_text'].eq('Ejection'), 'athlete_id_1'] = 6
        retained, excluded = a1_substitution_fold_data.exclude_unidentified_ejections(windows, mixed)
        self.assertEqual(len(retained), 1)
        self.assertEqual(excluded, [])

    def test_prior_ejection_with_player_still_on_court_quarantines_game(self):
        windows, raw, _ = audit_fixture()
        ejection = {'game_id': 1, 'period_number': 1, 'clock_display_value': '11:00', 'sequence_number': 3,
                    'type_id': 1, 'type_text': 'Ejection', 'athlete_id_1': 1}
        mixed = pd.concat([raw, pd.DataFrame([ejection])], ignore_index=True)
        retained, excluded = a1_substitution_fold_data.exclude_ejected_on_court(windows, mixed)
        self.assertTrue(retained.empty)
        self.assertEqual(excluded, [{'game_id': '1', 'window_id': '1:0', 'player': '1'}])
        mixed.loc[mixed['type_text'].eq('Ejection'), 'athlete_id_1'] = 6
        retained, excluded = a1_substitution_fold_data.exclude_ejected_on_court(windows, mixed)
        self.assertEqual(len(retained), 1)
        self.assertEqual(excluded, [])

    def test_out_screen_rejects_future_training_and_uses_reported_baseline_fallback(self):
        seed = pd.DataFrame({'game_id': ['a', 'b', 'c', 'd'], 'date_et': ['2023-02-01'] * 4,
                             'period': [1, 1, 2, 2], 'prior_tier': ['bench'] * 4,
                             'label': [True, False, False, False]})
        validation = pd.DataFrame({'game_id': ['e', 'e'], 'date_et': ['2024-01-01'] * 2,
                                   'period': [1, 3], 'prior_tier': ['bench', 'unknown']})
        train = a1_substitution_out_screen.training_rows({'seed': seed, 'F1': validation}, 'F1')
        probabilities, fallback = a1_substitution_out_screen.conditional_baseline(train, validation)
        self.assertAlmostEqual(probabilities[0], (1 + 20 * .25) / 22)
        self.assertAlmostEqual(probabilities[1], .25)
        self.assertEqual(fallback, 1)
        leaked = seed.copy()
        leaked.loc[0, 'date_et'] = '2024-01-01'
        with self.assertRaisesRegex(ValueError, 'validation-date or future'):
            a1_substitution_out_screen.training_rows({'seed': leaked, 'F1': validation}, 'F1')

    def test_out_features_ignore_postgame_columns(self):
        windows, raw, _ = audit_fixture()
        rows, _ = a1_substitution_dataset.build(windows, target_fixture(), raw)
        outgoing = rows[rows['decision'].eq('out')].copy()
        expected = a1_substitution_out_screen.feature_matrix(outgoing)
        outgoing['final_margin'] = 999
        pd.testing.assert_frame_equal(expected, a1_substitution_out_screen.feature_matrix(outgoing))
        outgoing.loc[outgoing.index[0], 'margin'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'missing observed game state'):
            a1_substitution_out_screen.feature_matrix(outgoing)

    def test_seed_roster_audit_ignores_future_and_rejects_tampered_prior_dates(self):
        boxes = pd.DataFrame([{'day': '2023-01-01', 'player': '1', 'team': '10'},
                              {'day': '2023-01-02', 'player': '2', 'team': '10'},
                              {'day': '2023-01-06', 'player': '1', 'team': '20'}])
        targets = pd.DataFrame([{'game_id': 'a', 'date_et': '2023-01-05', 'team': '10',
                                 'player': '1', 'prior_day': '2023-01-01'},
                                {'game_id': 'a', 'date_et': '2023-01-05', 'team': '10',
                                 'player': '2', 'prior_day': '2023-01-02'}])
        self.assertEqual(a1_substitution_seed_audit.audit_membership(targets, boxes)['candidate_rows'], 2)
        targets.loc[0, 'prior_day'] = '2023-01-03'
        with self.assertRaisesRegex(ValueError, 'roster or prior box date differs'):
            a1_substitution_seed_audit.audit_membership(targets, boxes)

    def test_out_screen_native_model_predicts_deterministically(self):
        rows = pd.DataFrame([{'window_id': str(index), 'game_id': str(index // 10), 'date_et': '2023-02-01',
                              'team': '10', 'player': str(index), 'period': 1, 'clock': 600.,
                              'margin': index % 20, 'fouls_before': 0, 'seconds_before': 120.,
                              'stint_before': 120., 'target_mean_proxy': 20., 'target_deficit': -1.,
                              'prior_tier': 'bench', 'label': index % 3 == 0}
                             for index in range(240)])
        first, first_details = a1_substitution_out_screen.predictions(rows, rows.iloc[:10])
        second, second_details = a1_substitution_out_screen.predictions(rows, rows.iloc[:10])
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(first_details, second_details)
        self.assertTrue(first['candidate_probability'].between(0, 1).all())

    def test_out_screen_independent_metric_audit_rejects_tampering(self):
        rows = pd.DataFrame({'game_id': ['a', 'b'], 'player': ['1', '2'], 'label': [1, 0],
                             'baseline_probability': [0.5, 0.5], 'candidate_probability': [0.7, 0.4]})
        baseline_log = math.log(2)
        candidate_log = -0.5 * (math.log(0.7) + math.log(0.6))
        recorded = {'observations': 2, 'games': 2, 'player_games': 2, 'outgoing_count': 1,
                    'status': 'insufficient_sample',
                    'brier': {'baseline': 0.25, 'candidate': 0.125, 'change': -0.125, 'ci_95': None},
                    'log_loss': {'baseline': baseline_log, 'candidate': candidate_log,
                                 'change': candidate_log - baseline_log, 'ci_95': None}}
        self.assertLess(a1_substitution_screen_audit.audit_metrics(rows, recorded), 1e-12)
        rows.loc[0, 'candidate_probability'] = 0.9
        with self.assertRaisesRegex(ValueError, 'estimate or direct-resampling bootstrap differs'):
            a1_substitution_screen_audit.audit_metrics(rows, recorded)

    def test_incoming_positions_use_only_recorded_prior_profile(self):
        rows = pd.DataFrame([{'player': '1', 'date_et': '2024-01-03', 'prior_profile_date': '2024-01-01'}])
        profiles = pd.DataFrame([{'player': '1', 'date_et': '2024-01-01', 'pos': 'PG'},
                                 {'player': '1', 'date_et': '2024-01-04', 'pos': 'C'}])
        result = a1_substitution_in_coverage.attach_positions(rows, profiles)
        self.assertEqual(result.loc[0, 'prior_position'], 'G')
        rows.loc[0, 'prior_profile_date'] = '2024-01-04'
        with self.assertRaisesRegex(ValueError, 'strictly earlier date'):
            a1_substitution_in_coverage.attach_positions(rows, profiles)

    def test_incoming_context_keeps_unknown_nonentries_and_remaining_positions(self):
        rows = []
        for index, position in enumerate(('G', 'G', 'F', 'F', 'C')):
            rows.append({'window_id': 'w', 'team': '10', 'player': str(index), 'decision': 'out',
                         'label': index == 0, 'prior_position': position})
        rows.extend([{'window_id': 'w', 'team': '10', 'player': '5', 'decision': 'in', 'label': True,
                      'prior_position': 'G', 'eligibility': 'current_unknown', 'prior_tier': 'bench'},
                     {'window_id': 'w', 'team': '10', 'player': '6', 'decision': 'in', 'label': None,
                      'prior_position': None, 'eligibility': 'current_unknown', 'prior_tier': 'unknown'},
                     {'window_id': 'w', 'team': '10', 'player': '7', 'decision': 'in', 'label': None,
                      'prior_position': 'C', 'eligibility': 'known_ineligible', 'prior_tier': 'bench'}])
        population = a1_substitution_in_screen.conditional_population(pd.DataFrame(rows))
        self.assertEqual(set(population['player']), {'5', '6'})
        self.assertTrue(pd.isna(population.loc[population['player'].eq('6'), 'label'].iloc[0]))
        self.assertEqual(population.iloc[0][['remaining_G', 'remaining_F', 'remaining_C']].tolist(), [1, 2, 1])
        self.assertTrue(population['entry_count'].eq(1).all())
        self.assertTrue(population['pool_count'].eq(2).all())

    def test_joint_selection_honours_active_disqualified_and_distinct_players(self):
        five = ['1', '2', '3', '4', '5']
        active = set(five + ['6', '7', '8', '9'])
        scores = {'6': 0.5, '7': 0.9, '8': 0.4, '9': 0.6}
        lineup, entrants = a1_substitution_in_screen.select_lineup(five, ['1', '2'], active, {'7'}, scores)
        self.assertEqual(entrants, ['9', '6'])
        self.assertEqual(set(lineup), {'3', '4', '5', '6', '9'})
        with self.assertRaisesRegex(ValueError, 'insufficient scoreable active replacements'):
            a1_substitution_in_screen.select_lineup(five, ['1', '2'], set(five + ['6']), set(), scores)
        with self.assertRaisesRegex(ValueError, 'five distinct players'):
            a1_substitution_in_screen.select_lineup(['1', '1', '3', '4', '5'], ['1'], active, set(), scores)

    def test_incoming_case_mixture_fit_keeps_unknown_labels_and_is_deterministic(self):
        rows = pd.DataFrame([{'window_id': str(index // 60), 'team': '10', 'player': str(index),
                              'label': True if index % 60 < 2 else None,
                              'period': 1, 'clock': 600., 'margin': 0, 'fouls_before': 0,
                              'seconds_before': 120., 'rest_before': 60., 'target_mean_proxy': 20.,
                              'target_deficit': -1., 'prior_tier': 'bench', 'prior_position': 'G',
                              'remaining_G': 1, 'remaining_F': 1, 'remaining_C': 1, 'remaining_unknown': 0,
                              'entry_count': 2, 'pool_count': 60}
                             for index in range(240)])
        first, details = a1_substitution_in_screen.fit_score(rows, rows.iloc[:10])
        second, _ = a1_substitution_in_screen.fit_score(rows, rows.iloc[:10])
        pd.testing.assert_series_equal(pd.Series(first), pd.Series(second))
        self.assertEqual(details['case_rows'], 8)
        self.assertEqual(details['reference_rows'], 240)
        self.assertEqual(int(rows['label'].isna().sum()), 232)

    def test_incoming_independent_audit_detects_changed_joint_selection(self):
        outgoing = [{'window_id': 'w', 'team': '10', 'player': str(index), 'decision': 'out',
                     'label': index == 0, 'fouls_before': 0, 'ejected_before': False}
                    for index in range(5)]
        scored = pd.DataFrame([{'window_id': 'w', 'team': '10', 'player': '5', 'decision': 'in',
                                'label': True, 'entry_count': 1, 'target_deficit': 2., 'target_mean_proxy': 20.,
                                'baseline_score': 2., 'candidate_score': 1., 'baseline_selected': True,
                                'candidate_selected': True, 'oracle_scored': True, 'oracle_baseline_selected': True,
                                'oracle_candidate_selected': True, 'fouls_before': 0, 'ejected_before': False},
                               {'window_id': 'w', 'team': '10', 'player': '6', 'decision': 'in',
                                'label': None, 'entry_count': 1, 'target_deficit': 1., 'target_mean_proxy': 10.,
                                'baseline_score': 1., 'candidate_score': 0., 'baseline_selected': False,
                                'candidate_selected': False, 'oracle_scored': True, 'oracle_baseline_selected': False,
                                'oracle_candidate_selected': False, 'fouls_before': 0, 'ejected_before': False}])
        raw = pd.concat([pd.DataFrame(outgoing), scored], ignore_index=True)
        windows = pd.DataFrame([{'window_id': 'w', 'home': '10', 'away': '20',
                                 'home_players': [str(index) for index in range(7)], 'away_players': []}])
        self.assertEqual(a1_substitution_in_screen_audit.audit_selections(scored, raw, windows)['team_windows'], 1)
        scored.loc[0, 'oracle_candidate_selected'] = False
        scored.loc[1, 'oracle_candidate_selected'] = True
        with self.assertRaisesRegex(ValueError, 'participant-oracle lineup'):
            a1_substitution_in_screen_audit.audit_selections(scored, raw, windows)


if __name__ == '__main__':
    unittest.main()
