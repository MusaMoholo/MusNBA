// Research validation of selected weighted worlds; production precomputes these summaries offline.
const PERIODS = ['q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg'];
const BOX = ['pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'ast', 'stl', 'blk', 'tov'];
const FULL_STATS = ['min', 'pts', 'reb', 'oreb', 'dreb', 'ast', 'fg3m', 'fgm', 'ftm', 'stl', 'blk', 'tov',
  'pra', 'pr', 'pa', 'ra', 'stocks', 'fga', 'fta', 'fg3a'];
const PERIOD_STATS = ['min', 'pts', 'reb', 'oreb', 'dreb', 'ast', 'fg3m', 'fgm', 'ftm', 'stl', 'blk',
  'pra', 'fga', 'fg3a', 'fta'];

function rounded(value) {
  const floor = Math.floor(value), fraction = value - floor;
  return fraction === 0.5 ? floor + floor % 2 : Math.round(value);
}

function summary(values, weights, mask, offset = false, conditional = false) {
  if (values.length !== weights.length || mask.length !== weights.length) throw new Error('World dimensions differ');
  const counts = new Map();
  let total = 0, defined = 0, sum = 0, square = 0;
  for (let i = 0; i < weights.length; i++) {
    if (!mask[i]) continue;
    const weight = weights[i], value = values[i];
    total += weight;
    if (Number.isNaN(value)) continue;
    if (!Number.isSafeInteger(weight) || weight <= 0 || !Number.isSafeInteger(value)) throw new Error('Invalid weighted outcome');
    defined += weight;
    sum += weight * value;
    square += weight * value * value;
    counts.set(value, (counts.get(value) || 0) + weight);
  }
  if (!Number.isSafeInteger(total) || !Number.isSafeInteger(defined) || !Number.isFinite(square)) throw new Error('Outcome mass exceeds safe limits');
  if (!defined) return null;
  const bins = [...counts].sort((a, b) => a[0] - b[0]);
  const lo = offset ? bins[0][0] : 0, hi = bins.at(-1)[0];
  if (lo < 0 && !offset) throw new Error('Unexpected negative player outcome');
  const hist = Array(hi - lo + 1).fill(0);
  for (const [value, mass] of bins) hist[value - lo] = mass;
  const quantiles = [], thresholds = [[1n, 10n], [1n, 4n], [1n, 2n], [3n, 4n], [9n, 10n]];
  let cumulative = 0n, next = 0;
  for (const [value, mass] of bins) {
    cumulative += BigInt(mass);
    while (next < thresholds.length && cumulative * thresholds[next][1] >= BigInt(defined) * thresholds[next][0]) {
      quantiles.push(value);
      next++;
    }
  }
  const mean = sum / defined;
  return {mean, sd: Math.sqrt(Math.max(0, square / defined - mean * mean)), q: quantiles, min: lo, hist,
    ...(conditional ? {defined_mass: defined, total_mass: total} : {})};
}

function mean(values, weights, mask) {
  let total = 0, sum = 0;
  for (let i = 0; i < weights.length; i++) if (mask[i]) {
    if (!Number.isFinite(values[i])) throw new Error('Invalid outcome');
    total += weights[i];
    sum += weights[i] * values[i];
  }
  if (!total || !Number.isSafeInteger(total) || !Number.isFinite(sum)) throw new Error('Invalid selected mass');
  return sum / total;
}

function combine(...values) {
  return values[0].map((_, i) => values.reduce((total, a) => total + a[i], 0));
}

export function branchGameSummary(source, choices = {}) {
  const {weights, players, side} = source, mask = source.selection(choices);
  if (!Array.isArray(players) || !Array.isArray(side) || players.length !== side.length
      || typeof source.game !== 'string' || typeof source.origin !== 'string'
      || !Array.isArray(source.selected) || !source.selected.length
      || typeof source.weightAssumptions !== 'string' || !source.weightAssumptions.trim()
      || weights.length !== source.worlds || mask.length !== source.worlds) throw new Error('Invalid source metadata');
  const selectedMass = mask.reduce((sum, value, i) => sum + value * weights[i], 0);
  if (!selectedMass || !Number.isSafeInteger(selectedMass)) throw new Error('No selected world mass');
  const selectedWorlds = mask.reduce((sum, value) => sum + value, 0);
  const out = {game: source.game, origin: source.origin, choices: {...choices},
    selected_players: source.selected, weight_assumptions: source.weightAssumptions,
    selected_mass: selectedMass, total_mass: source.denominator, selected_worlds: selectedWorlds,
    periods: {}, home: {players: [], box: {}}, away: {players: [], box: {}}};
  for (const period of PERIODS) {
    const home = source.teamPoints('home', period), away = source.teamPoints('away', period);
    const total = home.map((value, i) => value + away[i]), margin = home.map((value, i) => value - away[i]);
    const tie = margin.map(value => Number(value === 0));
    out.periods[period] = {
      total: summary(total, weights, mask, true), margin: summary(margin, weights, mask, true),
      home: {pts: summary(home, weights, mask, true), win: mean(margin.map(value => Number(value > 0)), weights, mask),
        tie: mean(tie, weights, mask)},
      away: {pts: summary(away, weights, mask, true), win: mean(margin.map(value => Number(value < 0)), weights, mask),
        tie: mean(tie, weights, mask)},
    };
    for (const s of ['home', 'away']) out[s].box[period] = Object.fromEntries([...BOX, 'reb'].map(stat => [stat, 0]));
  }
  const overtime = source.overtimePeriods();
  out.ot = mean(overtime.map(value => Number(value > 0)), weights, mask);
  out.ot_periods = summary(overtime, weights, mask).hist;
  for (let index = 0; index < players.length; index++) {
    const id = players[index], team = side[index] === 0 ? 'home' : side[index] === 1 ? 'away' : null;
    if (!team) throw new Error('Invalid player side');
    const played = source.playerValues(id, 'plays');
    const player = {id, played: mean(played, weights, mask),
      availability: mean(source.playerValues(id, 'available'), weights, mask),
      opening_share: mean(source.playerValues(id, 'starts'), weights, mask), periods: {}};
    for (const period of PERIODS) {
      const box = Object.fromEntries(BOX.map(stat => [stat, source.playerValues(id, stat, period)]));
      const minutes = source.playerValues(id, 'min', period);
      const values = {...box, reb: combine(box.oreb, box.dreb), min: minutes.map(rounded)};
      Object.assign(values, {pra: combine(values.pts, values.reb, values.ast), pr: combine(values.pts, values.reb),
        pa: combine(values.pts, values.ast), ra: combine(values.reb, values.ast), stocks: combine(values.stl, values.blk)});
      if (period === 'fg') {
        const categories = ['pts', 'reb', 'ast', 'stl', 'blk'];
        const tens = values.pts.map((_, i) => categories.reduce((n, stat) => n + Number(values[stat][i] >= 10), 0));
        for (const [key, count] of [['double_double', 2], ['triple_double', 3],
          ['quadruple_double', 4], ['quintuple_double', 5]]) {
          player[key] = mean(tens.map(value => Number(value >= count)), weights, mask);
        }
        player.five_by_five = mean(values.pts.map((_, i) => Number(categories.every(stat => values[stat][i] >= 5))), weights, mask);
        const playing = mask.map((yes, i) => Number(yes && played[i]));
        if (playing.some(Boolean) && player.played < 1) {
          player.if_plays = {min: mean(minutes, weights, playing),
            ...Object.fromEntries(['pts', 'reb', 'ast', 'fg3m'].map(stat => [stat, mean(values[stat], weights, playing)]))};
        }
      }
      const stats = Object.fromEntries((period === 'fg' ? FULL_STATS : PERIOD_STATS)
        .map(stat => [stat, summary(values[stat], weights, mask)]));
      for (const [stat, made, attempts] of [['fgpct', 'fgm', 'fga'], ['fg3pct', 'fg3m', 'fg3a'], ['ftpct', 'ftm', 'fta']]) {
        if (box[made].some((value, i) => value > box[attempts][i])) throw new Error('Made shots exceed attempts');
        const values = box[made].map((value, i) => box[attempts][i] ? Math.floor(100 * value / box[attempts][i] + 0.5) : NaN);
        const result = summary(values, weights, mask, false, true);
        if (result) stats[stat] = result;
      }
      const means = Object.fromEntries([...BOX, 'reb'].map(stat => [stat, mean(values[stat], weights, mask)]));
      for (const stat of Object.keys(means)) out[team].box[period][stat] += means[stat];
      player.periods[period] = {sec: mean(minutes, weights, mask) * 60, mean: means, stats};
    }
    out[team].players.push(player);
  }
  for (const period of PERIODS) for (const team of ['home', 'away']) {
    if (Math.abs(out[team].box[period].pts - out.periods[period][team].pts.mean) > 1e-8) {
      throw new Error('Player and team weighted scores differ');
    }
  }
  return out;
}
