import assert from 'node:assert/strict';
import {decodeMinuteCdfs, minuteThreshold} from '../scripts/webapp/precise-minutes.mjs';
const pack = values => {
  const buffer = Buffer.alloc(values.length * 8);
  values.forEach((value, i) => buffer.writeDoubleLE(value, i * 8));
  return buffer.toString('base64');
};
const raw = {schema: 2, worlds: 2, probability_mass: 20, players: ['1'],
  periods: ['q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg'], offsets: [0, 2, 4, 6, 8, 10, 12, 14],
  minutes_f64_le: pack(Array.from({length: 7}, () => [.001, 30.001]).flat()),
  cumulative_f64_le: pack(Array.from({length: 7}, () => [3, 20]).flat())};
const cdf = decodeMinuteCdfs(raw);
assert.equal(cdf.W, 2);
const d = cdf.minuteDistribution('1', 'fg');
assert.equal(d.mass, 20);
assert.equal(d.worlds, 2);
assert.deepEqual(minuteThreshold(d, 30), {below: 3, equal: 0, above: 17});
assert.deepEqual(minuteThreshold(d, 30.001), {below: 3, equal: 17, above: 0});
assert.deepEqual(d.quantiles, [.001, 30.001, 30.001, 30.001, 30.001]);
assert.equal(cdf.minuteValues, undefined); // Separate marginal CDFs cannot be mistaken for joint world samples.
assert.throws(() => cdf.minuteDistribution('2', 'fg'), /Unknown/);
for (const corrupt of [
  r => { r.probability_mass = 19; },
  r => { r.offsets[1] = 0; },
  r => { r.cumulative_f64_le = pack(Array(14).fill(20)); },
  r => { r.minutes_f64_le = pack(Array(14).fill(30)); },
]) {
  const bad = structuredClone(raw); corrupt(bad);
  assert.throws(() => decodeMinuteCdfs(bad), /Invalid/);
}
console.log('weighted minute CDF: exact threshold and corrupt-payload checks passed');
