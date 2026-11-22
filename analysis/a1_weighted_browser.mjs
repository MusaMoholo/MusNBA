// Research-only weighted-world arithmetic; not connected to the served dashboard.
const MAX = BigInt(Number.MAX_SAFE_INTEGER);
const gcd = (a, b) => b === 0n ? a : gcd(b, a % b);
const lcm = (a, b) => a / gcd(a, b) * b;

function fraction(value) {
  if (!value || !/^[0-9]+$/.test(value.numerator) || !/^[0-9]+$/.test(value.denominator)) throw new Error('Invalid branch fraction');
  const n = BigInt(value.numerator), d = BigInt(value.denominator);
  if (n <= 0n || d <= 0n) throw new Error('Branch fractions must be positive');
  return [n, d];
}

export function branchWeights(branches) {
  if (!Array.isArray(branches) || !branches.length) throw new Error('Branches required');
  let denominator = 1n;
  const pieces = branches.map(branch => {
    const n = branch.worlds;
    if (!Number.isSafeInteger(n) || n < 1) throw new Error('Invalid branch world count');
    const [num, den] = fraction(branch.weight);
    const divisor = gcd(num, den * BigInt(n));
    const each = [num / divisor, den * BigInt(n) / divisor];
    denominator = lcm(denominator, each[1]);
    return {n, each};
  });
  if (denominator > MAX) throw new Error('Exact weight denominator exceeds browser integer limit');
  const weights = [];
  let total = 0n;
  for (const {n, each} of pieces) {
    const units = each[0] * (denominator / each[1]);
    total += units * BigInt(n);
    if (units > MAX || total > MAX) throw new Error('Exact world weights exceed browser integer limit');
    for (let i = 0; i < n; i++) weights.push(Number(units));
  }
  if (total !== denominator) throw new Error('Branch weights must sum exactly to one');
  return {weights: Float64Array.from(weights), denominator: Number(denominator)};
}

function validate(weights, ...arrays) {
  if (!weights.length || arrays.some(a => a && a.length !== weights.length)) throw new Error('World arrays must match');
  for (let i = 0; i < weights.length; i++) {
    if (!Number.isSafeInteger(weights[i]) || weights[i] <= 0) throw new Error('Invalid world weight');
    for (const mask of arrays) if (mask && mask[i] !== 0 && mask[i] !== 1) throw new Error('Masks must be binary');
  }
}

export function joint(weights, event, condition, selection = null) {
  validate(weights, event, condition, selection);
  let selected = 0, e = 0, c = 0, both = 0;
  for (let i = 0; i < weights.length; i++) {
    if (selection && !selection[i]) continue;
    const w = weights[i];
    selected += w;
    if (event[i]) e += w;
    if (condition[i]) c += w;
    if (event[i] && condition[i]) both += w;
  }
  if (!Number.isSafeInteger(selected)) throw new Error('Selected mass exceeds browser integer limit');
  if (!selected) return {status: 'no selected worlds', selected: 0, event: null, condition: null, joint: null, given: null};
  return {status: c ? 'defined' : 'no matching condition worlds', selected,
    event: e / selected, condition: c / selected, joint: both / selected, given: c ? both / c : null,
    eventMass: e, conditionMass: c, jointMass: both};
}

export function distribution(values, weights, selection = null) {
  validate(weights, selection);
  if (values.length !== weights.length) throw new Error('World arrays must match');
  const histogram = new Map();
  let selected = 0, defined = 0, sum = 0, n = 0;
  for (let i = 0; i < weights.length; i++) {
    if (selection && !selection[i]) continue;
    const w = weights[i], value = values[i];
    selected += w;
    if (Number.isNaN(value)) continue;
    if (!Number.isFinite(value)) throw new Error('Infinite outcome is invalid');
    defined += w;
    sum += value * w;
    n++;
    histogram.set(value, (histogram.get(value) || 0) + w);
  }
  if (!Number.isSafeInteger(selected)) throw new Error('Selected mass exceeds browser integer limit');
  if (!defined) return {selected, defined: 0, undefined: selected, mean: null, quantiles: null, histogram: [], n};
  const bins = [...histogram].sort((a, b) => a[0] - b[0]);
  const targets = [[1n, 10n], [1n, 4n], [1n, 2n], [3n, 4n], [9n, 10n]];
  let cumulative = 0n, target = 0;
  const quantiles = [];
  for (const [value, mass] of bins) {
    cumulative += BigInt(mass);
    while (target < targets.length && cumulative * targets[target][1] >= BigInt(defined) * targets[target][0]) {
      quantiles.push(value);
      target++;
    }
  }
  return {selected, defined, undefined: selected - defined, mean: sum / defined, quantiles, histogram: bins, n};
}
