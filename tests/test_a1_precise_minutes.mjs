import assert from 'node:assert/strict';
import {minuteBins, minuteDistribution, minuteThreshold} from '../analysis/a1_precise_minutes.mjs';

const values = Float64Array.from([0, 0.001, 29.999, 30, 30.001, 30.001]);
const weights = Float64Array.from([1, 2, 3, 4, 5, 6]);
const dist = minuteDistribution(values, weights);
assert.equal(dist.mass, 21);
assert.equal(dist.worlds, 6);
assert.deepEqual(minuteThreshold(dist, 30), {below: 6, equal: 4, above: 11});
assert.deepEqual(minuteThreshold(dist, 0), {below: 0, equal: 1, above: 20});
assert.deepEqual(minuteThreshold(dist, 30.001), {below: 10, equal: 11, above: 0});
assert.deepEqual(minuteBins(dist, 30), [
  {minute: 0, atOrBelow: 3, above: 0},
  {minute: 29, atOrBelow: 3, above: 0},
  {minute: 30, atOrBelow: 4, above: 11},
]);
assert.equal(dist.mean, values.reduce((sum, value, i) => sum + value * weights[i], 0) / 21);
assert.deepEqual(dist.quantiles, [0.001, 29.999, 30.001, 30.001, 30.001]);
const selected = minuteDistribution(values, weights, [0, 1, 1, 0, 0, 0]);
assert.equal(selected.mass, 5);
assert.equal(selected.worlds, 2);
assert.deepEqual(minuteThreshold(selected, 30), {below: 5, equal: 0, above: 0});
assert.equal(minuteDistribution(values, weights, [0, 0, 0, 0, 0, 0]), null);
for (const invalid of [-1, NaN, Infinity]) {
  assert.throws(() => minuteDistribution([invalid], [1]), /Invalid minute/);
}
assert.throws(() => minuteDistribution([1], [1], [2]), /binary/);
assert.throws(() => minuteThreshold(dist, NaN), /Invalid minute threshold/);
console.log('precise minute research distribution: focused cases passed');
