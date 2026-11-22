import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.location = new URL('http://localhost/');
const {forecastTiming} = await import('../scripts/webapp/ui.mjs');

test('forecast labels require verified completion before tip', () => {
  const completed = '2026-11-21T23:00:00Z';
  assert.equal(forecastTiming('prospective', true, completed), 'Pre-game');
  assert.equal(forecastTiming('prospective', false, completed), 'Built after tip-off');
  assert.equal(forecastTiming('prospective', null, completed), 'Timing unverified');
  assert.equal(forecastTiming('prospective', true), 'Timing unverified');
  assert.equal(forecastTiming('prospective', 'true', completed), 'Timing unverified');
  assert.equal(forecastTiming('retrospective', true), 'Retrospective');
  assert.equal(forecastTiming(undefined, undefined), 'Timing unverified');
});
