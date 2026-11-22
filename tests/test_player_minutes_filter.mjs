import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.location = new URL('http://localhost/');
const {minutesBenchmark, qualifiesMinutes} = await import('../scripts/webapp/players.mjs');

test('season benchmark and qualification grow with the number of team games', () => {
  const player = {gp: 4, tot: {min: 100}};
  const early = minutesBenchmark({teams: [{gp: 16}, {gp: 18}]});
  const later = minutesBenchmark({teams: [{gp: 40}, {gp: 39}]});
  assert.equal(early, 864);
  assert.equal(qualifiesMinutes(player, 0.1, early), true);
  assert.equal(qualifiesMinutes(player, 0.1, later), false);
  assert.equal(qualifiesMinutes({gp: 1, tot: {min: 96}}, 0.05, 1920), true);
});

test('all played players remain visible, while missing minutes and zero games cannot qualify', () => {
  assert.equal(qualifiesMinutes({gp: 1, tot: {}}, 0, 0), true);
  assert.equal(qualifiesMinutes({gp: 1, tot: {}}, 0.1, 480), false);
  assert.equal(qualifiesMinutes({gp: 0, tot: {min: 0}}, 0, 480), false);
  assert.equal(qualifiesMinutes({gp: 1, tot: {min: 500}}, 0.5, 0), false);
  assert.throws(() => minutesBenchmark({teams: [{gp: null}]}), /unavailable/);
});
