import assert from 'node:assert/strict';
import {expectedPayload} from '../analysis/a1_expected_payload.mjs';

const digest = 'a'.repeat(64), sourceHash = 'b'.repeat(64), snapshotHash = 'c'.repeat(64);
const selected = [{player_id: '10', team_id: '1', status: 'Day-To-Day', status_source: 'injury_report', impact_rank: 1}];
const fixture = {game: '123', origin: '2026-11-22', engine: 'engine-v1.3', model: 'v1.3',
  source_sha256: sourceHash, selected_players: selected, weight_assumptions: 'Uncalibrated and independent.',
  snapshot_inputs: {'data/snapshots/2026-11-22/meta.json': snapshotHash, 'data/snapshots/2026-11-22/games.json': snapshotHash},
  player_metadata: [{id: '10', name: 'A'}, {id: '20', name: 'B'}],
  branches: [{worlds: {players: ['10', '20'], side: [0, 1], lines: 'large-world-data'}}]};
const summary = {fixture_sha256: digest, result: {game: '123', origin: '2026-11-22', choices: {},
  selected_players: selected, weight_assumptions: fixture.weight_assumptions, selected_worlds: 4, selected_mass: 8,
  total_mass: 8, home: {players: [{id: '10'}]}, away: {players: [{id: '20'}]}}};
const payload = expectedPayload(fixture, summary, digest);
assert.equal(payload.engine, 'engine-v1.3');
assert.equal(payload.expected.selected_worlds, 4);
assert.equal(payload.selected_players[0].status_source, 'injury_report');
assert.equal(JSON.stringify(payload).includes('large-world-data'), false);
for (const corrupt of [
  (f, s) => { s.fixture_sha256 = sourceHash; },
  (f, s) => { s.result.choices = {'10': false}; },
  (f, s) => { s.result.selected_mass = 4; },
  (f, s) => { s.result.origin = '2026-11-21'; },
  (f, s) => { s.result.selected_players[0].status_source = 'later'; },
  (f, s) => { f.player_metadata[0].id = '20'; },
  (f, s) => { delete f.snapshot_inputs['data/snapshots/2026-11-22/games.json']; },
  (f, s) => { s.result.home.players[0].id = '20'; },
]) {
  const f = structuredClone(fixture), s = structuredClone(summary);
  corrupt(f, s);
  assert.throws(() => expectedPayload(f, s, digest));
}
console.log('research Expected-only payload: focused cases passed');
