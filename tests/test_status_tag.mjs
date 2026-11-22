import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.location = new URL('http://localhost/');
const {statusTag} = await import('../scripts/webapp/ui.mjs');

test('unknown prospective status is visible while retrospective unknown stays hidden', () => {
  assert.match(statusTag('Unknown', 0.6), /Unknown · fallback 60%/);
  assert.match(statusTag('Unknown', 0.6), /uncalibrated fallback/);
  assert.match(statusTag(null, 1), /Unknown/);
  assert.equal(statusTag('Unknown (retrospective)', 0.6), '');
  assert.equal(statusTag('Active', 1), '');
});

test('report probabilities describe availability, not actual simulated participation', () => {
  assert.match(statusTag('Day-To-Day', 0.7, 'status'), /assumed available 70%/);
  assert.match(statusTag('Day-To-Day', 0.7, 'status'), /uncalibrated/);
  assert.match(statusTag('Active', 0.5, 'recent_inactivity'), /recent inactivity.*fallback 50%/i);
  assert.match(statusTag('Not specified', 0.6, 'unknown_status'), /fallback 60%/);
});
