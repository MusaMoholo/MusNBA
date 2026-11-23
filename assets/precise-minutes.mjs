// Exact weighted minute distributions; no forecasts are produced here.
import {distribution} from './weighted-worlds.mjs';

// Schema 2 stores separate CDFs, never joint samples that could imply invented dependence.
export function decodeMinuteCdfs(raw) {
  const periods = ['q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg'], ids = raw.players, offsets = raw.offsets;
  const W = raw.worlds, mass = raw.probability_mass;
  if (raw.schema !== 2 || !Number.isSafeInteger(W) || W < 1 || !Number.isSafeInteger(mass) || mass < W
      || !Array.isArray(ids) || !ids.length || new Set(ids).size !== ids.length || ids.some(id => typeof id !== 'string')
      || JSON.stringify(raw.periods) !== JSON.stringify(periods) || !Array.isArray(offsets)
      || offsets.length !== ids.length * periods.length + 1 || offsets[0] !== 0
      || offsets.some((n, i) => !Number.isSafeInteger(n) || (i && n <= offsets[i - 1]))
      || (raw.byte_shuffle != null && raw.byte_shuffle !== 8)
      || typeof raw.minutes_f64_le !== 'string' || typeof raw.cumulative_f64_le !== 'string') throw new Error('Invalid minute-CDF metadata');
  const unpack = text => {
    const bytes = Uint8Array.from(atob(text), c => c.charCodeAt(0));
    if (bytes.length !== offsets.at(-1) * 8) throw new Error('Invalid minute-CDF dimensions');
    let linear = bytes;
    if (raw.byte_shuffle === 8) {
      linear = new Uint8Array(bytes.length);
      const n = bytes.length / 8;
      for (let lane = 0; lane < 8; lane++) for (let i = 0; i < n; i++) linear[i * 8 + lane] = bytes[lane * n + i];
    }
    const view = new DataView(linear.buffer), values = new Float64Array(offsets.at(-1));
    for (let i = 0; i < values.length; i++) values[i] = view.getFloat64(i * 8, true);
    return values;
  };
  const support = unpack(raw.minutes_f64_le), cumulative = unpack(raw.cumulative_f64_le), memo = new Map();
  for (let j = 0; j < offsets.length - 1; j++) {
    for (let i = offsets[j]; i < offsets[j + 1]; i++) {
      if (!Number.isFinite(support[i]) || support[i] < 0 || !Number.isSafeInteger(cumulative[i]) || cumulative[i] <= 0
          || (i > offsets[j] && (support[i] <= support[i - 1] || cumulative[i] <= cumulative[i - 1]))) throw new Error('Invalid minute-CDF values');
    }
    if (cumulative[offsets[j + 1] - 1] !== mass) throw new Error('Invalid minute-CDF mass');
  }
  const targets = [[1n, 10n], [1n, 4n], [1n, 2n], [3n, 4n], [9n, 10n]].map(([n, d]) => Number((BigInt(mass) * n + d - 1n) / d));
  return {W, minuteDistribution(id, period) {
    const i = ids.indexOf(id), q = periods.indexOf(period);
    if (i < 0 || q < 0) throw new Error('Unknown player or minute period');
    const key = i * periods.length + q;
    if (!memo.has(key)) {
      const a = support.subarray(offsets[key], offsets[key + 1]), b = cumulative.subarray(offsets[key], offsets[key + 1]);
      let sum = 0, previous = 0, target = 0;
      const quantiles = [];
      for (let j = 0; j < a.length; j++) {
        sum += a[j] * (b[j] - previous); previous = b[j];
        while (target < targets.length && b[j] >= targets[target]) { quantiles.push(a[j]); target++; }
      }
      memo.set(key, {support: a, cumulative: b, mass, worlds: W, mean: sum / mass, quantiles});
    }
    return memo.get(key);
  }};
}

export function minuteDistribution(values, weights, selection = null) {
  for (const value of values) {
    if (!Number.isFinite(value) || value < 0) throw new Error('Invalid minute value');
  }
  const result = distribution(values, weights, selection);
  if (!result.defined) return null;
  const support = new Float64Array(result.histogram.length);
  const cumulative = new Float64Array(result.histogram.length);
  let total = 0;
  result.histogram.forEach(([value, mass], i) => {
    support[i] = value;
    total += mass;
    cumulative[i] = total;
  });
  return {support, cumulative, mass: result.defined, worlds: result.n,
    mean: result.mean, quantiles: result.quantiles};
}

// Exact threshold masses, including ties, without rounding the stored values.
export function minuteThreshold(dist, line) {
  if (!dist || !Number.isFinite(line)) throw new Error('Invalid minute threshold');
  const search = inclusive => {
    let lo = 0, hi = dist.support.length;
    while (lo < hi) {
      const mid = Math.floor((lo + hi) / 2);
      if (dist.support[mid] < line || (inclusive && dist.support[mid] === line)) lo = mid + 1;
      else hi = mid;
    }
    return lo ? dist.cumulative[lo - 1] : 0;
  };
  const below = search(false), through = search(true);
  return {below, equal: through - below, above: dist.mass - through};
}

// One-minute display intervals are [minute, minute + 1); a line may split one bar.
export function minuteBins(dist, line) {
  if (!dist || !Number.isFinite(line)) throw new Error('Invalid minute threshold');
  const bins = new Map();
  for (let i = 0, previous = 0; i < dist.support.length; i++) {
    const value = dist.support[i], mass = dist.cumulative[i] - previous;
    previous = dist.cumulative[i];
    const minute = Math.floor(value), bin = bins.get(minute) || {minute, atOrBelow: 0, above: 0};
    if (value > line) bin.above += mass;
    else bin.atOrBelow += mass;
    bins.set(minute, bin);
  }
  return [...bins.values()];
}
