// Validated stored lineup worlds. Reads and slices saved arrays; never simulates or fits.
import {branchWeights} from './weighted-worlds.mjs';

function probabilityFraction(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0 || value >= 1) throw new Error('Invalid selected player probability');
  const [digits, exponent = '0'] = String(value).split('e');
  const places = (digits.split('.')[1] || '').length - Number(exponent);
  return [BigInt(digits.replace('.', '')) * 10n ** BigInt(Math.max(0, -places)), 10n ** BigInt(Math.max(0, places))];
}

function bytes(value) {
  if (typeof value !== 'string' || value.length % 4 || /[^A-Za-z0-9+/=]/.test(value)
      || (value.includes('=') && value.indexOf('=') < value.length - 2)) throw new Error('Invalid base64 data');
  const padding = value.endsWith('==') ? 2 : value.endsWith('=') ? 1 : 0;
  const out = new Uint8Array(value.length / 4 * 3 - padding);
  let offset = 0;
  for (let i = 0; i < value.length; i += 32768) {
    const chunk = atob(value.slice(i, i + 32768));
    for (let j = 0; j < chunk.length; j++) out[offset++] = chunk.charCodeAt(j);
  }
  if (offset !== out.length) throw new Error('Invalid base64 data');
  return out;
}
const allEqual = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
const SLICES = {fg: [0, 1, 2, 3, 4], q1: [0], q2: [1], q3: [2], q4: [3], h1: [0, 1], h2: [2, 3], ot: [4]};

export function branchWorldSource(fixture) {
  const selected = fixture.selected_players, records = fixture.branches;
  if (!Array.isArray(selected) || selected.length < 1 || selected.length > 2
      || typeof fixture.game !== 'string' || !/^[0-9]+$/.test(fixture.game)
      || typeof fixture.origin !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(fixture.origin)
      || !Number.isFinite(Date.parse(fixture.origin + 'T00:00:00Z'))
      || new Date(fixture.origin + 'T00:00:00Z').toISOString().slice(0, 10) !== fixture.origin
      || typeof fixture.weight_assumptions !== 'string' || !fixture.weight_assumptions.trim()
      || selected.some(p => !p || typeof p !== 'object')
      || new Set(selected.map(p => p.player_id)).size !== selected.length
      || new Set(selected.map(p => p.team_id)).size !== selected.length
      || !Array.isArray(records) || records.length !== 2 ** selected.length) throw new Error('Invalid branch selection');
  for (const p of selected) {
    if (typeof p.player_id !== 'string' || typeof p.team_id !== 'string'
        || !/^[0-9]+$/.test(p.player_id) || !/^[0-9]+$/.test(p.team_id)
        || typeof p.probability !== 'number') throw new Error('Invalid selected player');
    probabilityFraction(p.probability);
  }
  const combinations = new Set(), prepared = [];
  let roster = null, offset = 0, hasPeriods = null, hasFinalPeriod = null, hasOpening = null;
  for (const record of records) {
    const raw = record.worlds;
    if (!raw || !Array.isArray(record.assignments) || record.assignments.length !== selected.length
        || !Array.isArray(raw.players) || !raw.players.length || !Array.isArray(raw.side)
        || !Array.isArray(raw.stats) || new Set(raw.players).size !== raw.players.length
        || new Set(raw.stats).size !== raw.stats.length || raw.side.length !== raw.players.length
        || !Array.isArray(raw.periods) || !allEqual(raw.periods, ['q1', 'q2', 'q3', 'q4', 'ot'])
        || (selected.length === 2 && raw.side[raw.players.indexOf(selected[0].player_id)]
            === raw.side[raw.players.indexOf(selected[1].player_id)])
        || raw.side.some(s => s !== 0 && s !== 1)) throw new Error('Invalid branch world metadata');
    let numerator = 1n, denominator = 1n;
    const assignments = new Map(), choices = [];
    for (let i = 0; i < selected.length; i++) {
      if (!Array.isArray(record.assignments[i]) || record.assignments[i].length !== 3) throw new Error('Invalid branch assignments');
      const [team, player, plays] = record.assignments[i], source = selected[i];
      if (team !== source.team_id || player !== source.player_id || typeof plays !== 'boolean'
          || !raw.players.includes(player)) throw new Error('Invalid branch assignments');
      const [p, d] = probabilityFraction(source.probability);
      numerator *= plays ? p : d - p;
      denominator *= d;
      assignments.set(player, plays);
      choices.push(plays ? '1' : '0');
    }
    const combination = choices.join('');
    if (combinations.has(combination)) throw new Error('Duplicate branch assignments');
    combinations.add(combination);
    if (!record.weight || !/^[0-9]+$/.test(record.weight.numerator) || !/^[0-9]+$/.test(record.weight.denominator)
        || BigInt(record.weight.numerator) * denominator !== numerator * BigInt(record.weight.denominator)) {
      throw new Error('Branch weight does not match availability assumptions');
    }
    const current = [raw.players, raw.side, raw.stats];
    if (roster && current.some((v, i) => !allEqual(v, roster[i]))) throw new Error('Branch rosters or statistics differ');
    roster = current;
    const n = raw.worlds, p = raw.players.length, k = raw.stats.length;
    if (!Number.isSafeInteger(n) || n < 1) throw new Error('Invalid world count');
    const lines = bytes(raw.lines), available = bytes(raw.availability), played = bytes(raw.played);
    const mins = bytes(raw.minutes_f64_le), periods = bytes(raw.team_periods);
    const hasFinal = 'final_period' in raw;
    if (hasFinalPeriod != null && hasFinal !== hasFinalPeriod) throw new Error('Branches differ in final-period data');
    hasFinalPeriod = hasFinal;
    const finalPeriod = hasFinal ? bytes(raw.final_period) : null;
    const openingPresent = 'opening_lineups' in raw;
    if (hasOpening != null && openingPresent !== hasOpening) throw new Error('Branches differ in opening lineups');
    hasOpening = openingPresent;
    const opening = openingPresent ? bytes(raw.opening_lineups) : null;
    if (lines.length !== n * p * k || available.length !== n * p || played.length !== n * p
        || mins.length !== n * p * 8 || periods.length !== n * 10
        || (hasFinal && finalPeriod.length !== n) || (openingPresent && opening.length !== n * 10)) throw new Error('Invalid packed-world lengths');
    const minuteView = new DataView(mins.buffer, mins.byteOffset, mins.byteLength);
    const fields = ['period_stats', 'period_lines', 'period_minutes_f64_le'];
    const has = fields.some(field => field in raw);
    if (hasPeriods != null && has !== hasPeriods) throw new Error('Branches differ in player-period data');
    hasPeriods = has;
    let periodLines = null, periodMinuteView = null;
    if (has) {
      if (!Array.isArray(raw.period_stats) || !allEqual(raw.period_stats, raw.stats.filter(s => s !== 'min'))
          || !raw.stats.includes('min') || typeof raw.period_lines !== 'string'
          || typeof raw.period_minutes_f64_le !== 'string') throw new Error('Invalid player-period metadata');
      periodLines = bytes(raw.period_lines);
      const pm = bytes(raw.period_minutes_f64_le);
      if (periodLines.length !== n * p * 5 * (k - 1) || pm.length !== n * p * 5 * 8) throw new Error('Invalid player-period lengths');
      periodMinuteView = new DataView(pm.buffer, pm.byteOffset, pm.byteLength);
    }
    const pointsCol = raw.stats.indexOf('pts');
    if (pointsCol < 0) throw new Error('Player points are missing');
    for (let w = 0; w < n; w++) {
      if (openingPresent) for (let side = 0; side < 2; side++) {
        const lineup = opening.subarray(w * 10 + side * 5, w * 10 + side * 5 + 5);
        if (new Set(lineup).size !== 5 || [...lineup].some(i => i >= p || raw.side[i] !== side || available[w * p + i] !== 1)) {
          throw new Error('Invalid opening lineup');
        }
      }
      if (hasFinal && (finalPeriod[w] < 4
          || (finalPeriod[w] === 4 && (periods[w * 10 + 4] || periods[w * 10 + 9])))) {
        throw new Error('Invalid final period');
      }
      const score = [0, 0], periodScore = [new Array(5).fill(0), new Array(5).fill(0)];
      for (let i = 0; i < p; i++) {
        const cell = w * p + i, a = available[cell], didPlay = played[cell], minutes = minuteView.getFloat64(cell * 8, true);
        if ((a !== 0 && a !== 1) || (didPlay !== 0 && didPlay !== 1) || !Number.isFinite(minutes)
            || minutes < 0 || didPlay !== Number(minutes > 0) || (!a && didPlay)) throw new Error('Invalid availability or playing time');
        const assigned = assignments.get(raw.players[i]);
        if (assigned != null && a !== Number(assigned)) throw new Error('World availability differs from its branch');
        if (!a && raw.stats.some((_, j) => lines[cell * k + j] !== 0)) throw new Error('Unavailable player has recorded stats');
        score[raw.side[i]] += lines[cell * k + pointsCol];
        if (has) {
          let total = 0;
          for (let q = 0; q < 5; q++) {
            const value = periodMinuteView.getFloat64((cell * 5 + q) * 8, true);
            if (!Number.isFinite(value) || value < 0) throw new Error('Invalid player-period minutes');
            total += value;
          }
          if (Math.abs(total - minutes) > 1e-10) throw new Error('Player-period minutes do not sum to game');
          for (let j = 0; j < raw.period_stats.length; j++) {
            let sum = 0;
            for (let q = 0; q < 5; q++) {
              const value = periodLines[(cell * 5 + q) * (k - 1) + j];
              sum += value;
              if (raw.period_stats[j] === 'pts') periodScore[raw.side[i]][q] += value;
            }
            if (sum !== lines[cell * k + raw.stats.indexOf(raw.period_stats[j])]) throw new Error('Player-period stats do not sum to game');
          }
        }
      }
      for (let side = 0; side < 2; side++) {
        let total = 0;
        for (let q = 0; q < 5; q++) {
          const value = periods[w * 10 + side * 5 + q];
          if (has && periodScore[side][q] !== value) throw new Error('Player-period and team scores differ');
          total += value;
        }
        if (score[side] !== total) throw new Error('Player and team scores differ');
      }
    }
    prepared.push({raw, lines, available, played, minuteView, periodLines, periodMinuteView, periods, finalPeriod, opening, offset, assignments});
    offset += n;
  }
  const {weights, denominator} = branchWeights(prepared.map((b, i) => ({worlds: b.raw.worlds, weight: records[i].weight})));
  const playerValues = (id, stat, period = 'fg') => {
    const index = roster[0].indexOf(id), col = roster[2].indexOf(stat);
    if (index < 0 || (col < 0 && !['plays', 'sits', 'available', 'unavailable', 'starts'].includes(stat))) throw new Error('Unknown player or statistic');
    if (stat === 'starts' && !hasOpening) throw new Error('Opening lineup data unavailable');
    if (!Object.hasOwn(SLICES, period)) throw new Error('Invalid period');
    if (period !== 'fg' && (!hasPeriods || ['plays', 'sits', 'available', 'unavailable', 'starts'].includes(stat))) {
      throw new Error('Player-period data or statistic unavailable');
    }
    const result = new Float64Array(offset);
    for (const branch of prepared) {
      const p = branch.raw.players.length, k = branch.raw.stats.length;
      for (let w = 0; w < branch.raw.worlds; w++) {
        const cell = w * p + index;
        if (period !== 'fg') {
          const periodCol = branch.raw.period_stats.indexOf(stat);
          result[branch.offset + w] = SLICES[period].reduce((sum, q) => sum + (stat === 'min'
            ? branch.periodMinuteView.getFloat64((cell * 5 + q) * 8, true)
            : branch.periodLines[(cell * 5 + q) * (k - 1) + periodCol]), 0);
          continue;
        }
        result[branch.offset + w] = stat === 'min' ? branch.minuteView.getFloat64(cell * 8, true)
          : stat === 'plays' ? branch.played[cell] : stat === 'sits' ? 1 - branch.played[cell]
            : stat === 'available' ? branch.available[cell] : stat === 'unavailable' ? 1 - branch.available[cell]
              : stat === 'starts' ? Number(branch.opening.subarray(w * 10, w * 10 + 10).includes(index))
              : branch.lines[cell * k + col];
      }
    }
    return result;
  };
  const teamPoints = (side, period = 'fg') => {
    if ((side !== 'home' && side !== 'away') || !Object.hasOwn(SLICES, period)) throw new Error('Invalid team side or period');
    const result = new Float64Array(offset), base = side === 'home' ? 0 : 5;
    for (const branch of prepared) for (let w = 0; w < branch.raw.worlds; w++) {
      for (const q of SLICES[period]) result[branch.offset + w] += branch.periods[w * 10 + base + q];
    }
    return result;
  };
  const selection = choices => {
    if (!choices || typeof choices !== 'object' || Array.isArray(choices)
        || Object.entries(choices).some(([id, value]) => !selected.some(p => p.player_id === id) || typeof value !== 'boolean')) {
      throw new Error('Invalid lineup choices');
    }
    const mask = new Uint8Array(offset);
    for (const branch of prepared) if (Object.entries(choices).every(([id, value]) => branch.assignments.get(id) === value)) {
      mask.fill(1, branch.offset, branch.offset + branch.raw.worlds);
    }
    return mask;
  };
  const overtimePeriods = () => {
    if (!hasFinalPeriod) throw new Error('Final-period data unavailable');
    const result = new Uint8Array(offset);
    for (const branch of prepared) for (let w = 0; w < branch.raw.worlds; w++) {
      result[branch.offset + w] = branch.finalPeriod[w] - 4;
    }
    return result;
  };
  return {worlds: offset, weights, denominator, game: fixture.game, origin: fixture.origin,
    selected, weightAssumptions: fixture.weight_assumptions,
    players: roster[0], side: roster[1], stats: roster[2],
    playerValues, teamPoints, selection, overtimePeriods};
}
