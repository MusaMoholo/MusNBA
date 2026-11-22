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
  if (!Number.isSafeInteger(selected) || !Number.isFinite(sum)) throw new Error('Distribution exceeds browser numeric limits');
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

export function correlation(a, b, weights, selection = null) {
  validate(weights, selection);
  if (a.length !== weights.length || b.length !== weights.length) throw new Error('World arrays must match');
  let mass = 0, sa = 0, sb = 0, n = 0;
  for (let i = 0; i < weights.length; i++) {
    if ((selection && !selection[i]) || Number.isNaN(a[i]) || Number.isNaN(b[i])) continue;
    if (!Number.isFinite(a[i]) || !Number.isFinite(b[i])) throw new Error('Infinite outcome is invalid');
    mass += weights[i]; sa += weights[i] * a[i]; sb += weights[i] * b[i]; n++;
  }
  if (!Number.isSafeInteger(mass) || !Number.isFinite(sa) || !Number.isFinite(sb)) throw new Error('Correlation exceeds browser numeric limits');
  if (n < 3) return null;
  const ma = sa / mass, mb = sb / mass;
  let aa = 0, bb = 0, ab = 0;
  for (let i = 0; i < weights.length; i++) {
    if ((selection && !selection[i]) || Number.isNaN(a[i]) || Number.isNaN(b[i])) continue;
    const da = a[i] - ma, db = b[i] - mb;
    aa += weights[i] * da * da; bb += weights[i] * db * db; ab += weights[i] * da * db;
  }
  if (!Number.isFinite(aa) || !Number.isFinite(bb) || !Number.isFinite(ab)) throw new Error('Correlation exceeds browser numeric limits');
  return aa > 0 && bb > 0 ? ab / Math.sqrt(aa) / Math.sqrt(bb) : null;
}

export function gridEdges(values, weights, selection = null, maxBins = 7) {
  validate(weights, selection);
  if (values.length !== weights.length || !Number.isSafeInteger(maxBins) || maxBins < 1) {
    throw new Error('Invalid grid values or bin limit');
  }
  const entries = [];
  let total = 0;
  for (let i = 0; i < values.length; i++) {
    if ((selection && !selection[i]) || Number.isNaN(values[i])) continue;
    if (!Number.isFinite(values[i])) throw new Error('Infinite outcome is invalid');
    entries.push([values[i], weights[i]]);
    total += weights[i];
  }
  if (!Number.isSafeInteger(total)) throw new Error('Grid mass exceeds browser integer limit');
  if (!total) return [];
  entries.sort((a, b) => a[0] - b[0]);
  let cumulative = 0n, lo = null, hi = null;
  for (const [value, weight] of entries) {
    cumulative += BigInt(weight);
    if (lo == null && cumulative * 100n >= BigInt(total) * 2n) lo = value;
    if (cumulative * 100n >= BigInt(total) * 98n) { hi = value; break; }
  }
  if (maxBins === 1) return [-Infinity, Infinity];
  const span = Math.max(1, hi - lo);
  if (!Number.isFinite(span)) throw new Error('Grid range exceeds browser numeric limits');
  const count = width => Math.floor(hi / width) - Math.floor(lo / width) + 1;
  let width = [1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 25].find(w => count(w) <= maxBins)
    || Math.ceil(span / (maxBins - 1));
  while (count(width) > maxBins) {
    width *= 2;
    if (!Number.isFinite(width)) throw new Error('Grid width exceeds browser numeric limits');
  }
  const edges = [-Infinity], start = Math.floor(lo / width) * width;
  if (start + width <= start) throw new Error('Grid edges exceed browser numeric limits');
  for (let next = start + width; next <= hi;) {
    edges.push(next);
    const following = next + width;
    if (following <= next || !Number.isFinite(following)) throw new Error('Grid edges exceed browser numeric limits');
    next = following;
  }
  edges.push(Infinity);
  return edges;
}

export function grid(x, y, weights, xEdges, yEdges, selection = null) {
  validate(weights, selection);
  if (x.length !== weights.length || y.length !== weights.length) throw new Error('World arrays must match');
  for (const edges of [xEdges, yEdges]) {
    if (edges.length < 2 || edges[0] !== -Infinity || edges.at(-1) !== Infinity
        || edges.some((v, i) => typeof v !== 'number' || Number.isNaN(v) || (i > 0 && v <= edges[i - 1]))) {
      throw new Error('Grid edges must increase from negative to positive infinity');
    }
  }
  const cells = Array.from({length: yEdges.length - 1}, () => Array(xEdges.length - 1).fill(0));
  const columnMass = Array(xEdges.length - 1).fill(0), columnSum = columnMass.slice();
  let total = 0;
  for (let i = 0; i < weights.length; i++) {
    if ((selection && !selection[i]) || Number.isNaN(x[i]) || Number.isNaN(y[i])) continue;
    if (!Number.isFinite(x[i]) || !Number.isFinite(y[i])) throw new Error('Infinite outcome is invalid');
    const xi = xEdges.findIndex((v, j) => j > 0 && x[i] < v) - 1;
    const yi = yEdges.findIndex((v, j) => j > 0 && y[i] < v) - 1;
    if (xi < 0 || yi < 0) throw new Error('Outcome is outside grid');
    const w = weights[i];
    cells[yi][xi] += w; columnMass[xi] += w; columnSum[xi] += w * y[i]; total += w;
  }
  if (!Number.isSafeInteger(total) || columnSum.some(v => !Number.isFinite(v))) throw new Error('Grid exceeds browser numeric limits');
  return {cells, total, columnMass, columnMean: columnMass.map((mass, i) => mass ? columnSum[i] / mass : null)};
}
