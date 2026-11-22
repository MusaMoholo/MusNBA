import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.location = new URL('http://localhost/');
const payload = {
  serving: {}, backtests: [],
  lineups: {overall: {team_games: 132, slot_accuracy: 0.8273, all_five: 0.3106},
            slates: Array.from({length: 10}, () => ({}))},
};
globalThis.fetch = async () => ({ok: true, json: async () => payload});
const {render} = await import('../scripts/webapp/lab.mjs');

test('starter accuracy hides legacy scores and displays verified scores', async () => {
  const view = {innerHTML: ''};
  await render(view, {current: () => true});
  assert.match(view.innerHTML, /No verified pre-tip starter forecasts scored yet/);
  assert.match(view.innerHTML, /10 older slates are excluded: retrospective or completion timing unverified/);
  assert.doesNotMatch(view.innerHTML, /82\.7%/);

  payload.lineups = {timing_policy: 'completed_before_tip-v1', overall: {
    team_games: 2, slot_accuracy: 0.9, all_five: 0.5,
  }, slates: [], legacy_unverified_slates: 10};
  await render(view, {current: () => true});
  assert.match(view.innerHTML, /90\.0%/);
  assert.match(view.innerHTML, /10 older slates are excluded/);
});
