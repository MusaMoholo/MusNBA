// Research-only exact weighted minute distributions; no forecasts are produced here.
import {distribution} from '../scripts/webapp/weighted-worlds.mjs';

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
