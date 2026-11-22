import assert from 'node:assert/strict';
import {branchWeights, correlation, distribution, grid, joint} from '../analysis/a1_weighted_browser.mjs';

const weight = (numerator, denominator) => ({numerator: String(numerator), denominator: String(denominator)});
const {weights, denominator} = branchWeights([
  {worlds: 2, weight: weight(1, 4)}, {worlds: 2, weight: weight(3, 4)},
]);
assert.equal(denominator, 8);
assert.deepEqual([...weights], [1, 1, 3, 3]);
const result = joint(weights, [1, 0, 1, 1], [1, 1, 1, 0]);
assert.equal(result.event, 7 / 8);
assert.equal(result.condition, 5 / 8);
assert.equal(result.joint, 1 / 2);
assert.equal(result.given, 4 / 5);
assert.equal(joint(weights, [1, 0, 1, 1], [0, 0, 0, 0]).given, null);
assert.equal(joint(weights, [1, 0, 1, 1], [1, 1, 1, 1], [0, 0, 0, 0]).status, 'no selected worlds');
const uneven = branchWeights([{worlds: 2, weight: weight(1, 2)}, {worlds: 3, weight: weight(1, 2)}]);
assert.equal(uneven.denominator, 12);
assert.deepEqual([...uneven.weights], [3, 3, 2, 2, 2]);
assert.equal(joint(uneven.weights, [1, 0, 1, 0, 0], [1, 1, 1, 1, 1], [0, 0, 1, 1, 1]).event, 1 / 3);

const dist = distribution([NaN, 50, 100, NaN], weights);
assert.equal(dist.selected, 8);
assert.equal(dist.defined, 4);
assert.equal(dist.undefined, 4);
assert.equal(dist.mean, 87.5);
assert.deepEqual(dist.histogram, [[50, 1], [100, 3]]);
assert.deepEqual(dist.quantiles, [50, 50, 100, 100, 100]);
assert.equal(distribution([NaN, NaN, NaN, NaN], weights).mean, null);
const precise = distribution([0.1, 29.6, 30, 30.25], weights);
assert.equal(precise.mean, (0.1 + 29.6 + 30 * 3 + 30.25 * 3) / 8);
assert.deepEqual(precise.histogram, [[0.1, 1], [29.6, 1], [30, 3], [30.25, 3]]);
assert.deepEqual(precise.quantiles, [0.1, 29.6, 30, 30.25, 30.25]);
assert.ok(Math.abs(correlation([0, 1, 2, 3], [0, 2, 4, 6], weights) - 1) < 1e-12);
assert.equal(correlation([0, 1, 2, 3], [2, 2, 2, 2], weights), null);
assert.equal(correlation([0, 1, 2, 3], [0, 2, 4, 6], weights, [1, 1, 0, 0]), null);
assert.deepEqual(grid([0, 1, 2, 3], [0, 2, 4, 6], weights,
  [-Infinity, 2, Infinity], [-Infinity, 4, Infinity]),
{cells: [[2, 0], [0, 6]], total: 8, columnMass: [2, 6], columnMean: [1, 5]});
assert.throws(() => grid([0, 1, 2, 3], [0, 2, 4, 6], weights, [-Infinity, 2, 1, Infinity], [-Infinity, Infinity]), /edges/);

const tiny = branchWeights([{worlds: 10000, weight: weight(1, 2)}, {worlds: 10000, weight: weight(1, 2)}]);
const values = new Uint8Array(20000);
values[0] = 1;
const tinyDist = distribution(values, tiny.weights);
assert.deepEqual(tinyDist.histogram, [[0, 19999], [1, 1]]);
assert.equal(tinyDist.mean, 1 / 20000);
for (const bad of [
  [{worlds: 1, weight: weight(1, 2)}],
  [{worlds: 1, weight: weight(0, 1)}],
  [{worlds: 1, weight: weight(1, '10000000000000000')}, {worlds: 1, weight: weight('9999999999999999', '10000000000000000')}],
]) assert.throws(() => branchWeights(bad));
assert.throws(() => joint(weights, [1, 0, 2, 1], [1, 1, 1, 0]), /binary/);
assert.throws(() => distribution([0, 0, Infinity, 0], weights), /Infinite/);
console.log('weighted browser research arithmetic: focused cases passed');
