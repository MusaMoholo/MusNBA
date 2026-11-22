// Research-only selected-world view data. It is not connected to the app or a bundle.
const PERIODS = ['q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg'];
const BOX = ['pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'ast', 'stl', 'blk', 'tov', 'reb'];
const STATS = ['min', 'pts', 'reb', 'oreb', 'dreb', 'ast', 'fg3m', 'fgm', 'ftm', 'stl', 'blk', 'tov',
  'pra', 'pr', 'pa', 'ra', 'stocks', 'fga', 'fta', 'fg3a', 'fgpct', 'fg3pct', 'ftpct'];
const probability = n => Number.isFinite(n) && n >= 0 && n <= 1;
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const digest = s => typeof s === 'string' && /^[a-f0-9]{64}$/.test(s);

function distribution(d, mass) {
  if (!d || !Number.isInteger(d.min) || !Array.isArray(d.hist) || !d.hist.length
      || d.hist.some(n => !Number.isSafeInteger(n) || n < 0)
      || !Number.isFinite(d.mean) || !Number.isFinite(d.sd)
      || !Array.isArray(d.q) || d.q.length !== 5 || d.q.some(n => !Number.isFinite(n))) {
    throw new Error('Invalid selected distribution');
  }
  const defined = d.defined_mass ?? mass;
  if (!Number.isSafeInteger(defined) || defined <= 0 || defined > mass
      || (d.defined_mass != null && d.total_mass !== mass)
      || d.hist.reduce((sum, n) => sum + n, 0) !== defined) throw new Error('Invalid distribution mass');
  return {min: d.min, hist: [...d.hist], mean: d.mean, sd: d.sd, q: [...d.q],
    ...(d.defined_mass == null ? {} : {defined_mass: defined, total_mass: mass})};
}

function box(b) {
  if (!b || BOX.some(k => !Number.isFinite(b[k]))) throw new Error('Invalid selected box');
  return Object.fromEntries(BOX.map(k => [k, b[k]]));
}

export function selectedGameView(game, payload, summary) {
  const r = summary?.result, selected = payload?.selected_players;
  if (!game || game.id !== payload?.game || r?.game !== payload.game || r.origin !== payload.origin
      || !digest(payload.fixture_sha256) || summary.fixture_sha256 !== payload.fixture_sha256
      || typeof payload.engine !== 'string' || typeof payload.model !== 'string'
      || typeof payload.weight_assumptions !== 'string' || !payload.weight_assumptions.trim()
      || !Array.isArray(payload.limitations) || payload.limitations.some(x => typeof x !== 'string')
      || !Array.isArray(selected) || selected.length < 1 || selected.length > 2
      || !equal(r.selected_players, selected) || r.weight_assumptions !== payload.weight_assumptions
      || !r.choices || Array.isArray(r.choices) || typeof r.choices !== 'object'
      || Object.entries(r.choices).some(([id, value]) => !selected.some(p => p.player_id === id) || typeof value !== 'boolean')
      || !Number.isSafeInteger(r.selected_worlds) || r.selected_worlds <= 0
      || !Number.isSafeInteger(r.selected_mass) || r.selected_mass <= 0
      || !Number.isSafeInteger(r.total_mass) || r.total_mass < r.selected_mass
      || !game.home?.id || !game.away?.id || game.home.id === game.away.id) {
    throw new Error('Selected game provenance or mass differs');
  }
  if (!Array.isArray(payload.player_metadata) || !Array.isArray(payload.roster?.players)
      || !Array.isArray(payload.roster?.side) || payload.roster.players.length !== payload.roster.side.length
      || payload.player_metadata.length !== payload.roster.players.length
      || new Set(payload.roster.players).size !== payload.roster.players.length
      || payload.player_metadata.some((p, i) => p?.id !== payload.roster.players[i]
        || typeof p.name !== 'string' || !p.name || ![0, 1].includes(payload.roster.side[i]))) {
    throw new Error('Selected game roster differs');
  }
  for (const p of selected) {
    const i = payload.roster.players.indexOf(p.player_id), side = payload.roster.side[i] === 0 ? 'home' : 'away';
    if (i < 0 || p.team_id !== game[side].id) throw new Error('Selected player belongs to another team');
  }
  const mass = r.selected_mass, metadata = new Map(payload.player_metadata.map(p => [p.id, p]));
  const sides = {};
  for (const [side, value] of [['home', 0], ['away', 1]]) {
    const ids = payload.roster.players.filter((_, i) => payload.roster.side[i] === value);
    if (!Array.isArray(r[side]?.players) || !equal(r[side].players.map(p => p.id), ids)) {
      throw new Error('Selected summary roster differs');
    }
    const players = r[side].players.map(p => {
      if (![p.played, p.availability, p.opening_share].every(probability)
          || p.played > p.availability + 1e-12 || p.opening_share > p.availability + 1e-12) {
        throw new Error('Invalid selected player participation');
      }
      const m = metadata.get(p.id), periods = {};
      for (const period of PERIODS) {
        const row = p.periods?.[period];
        if (!row || !Number.isFinite(row.sec) || row.sec < 0 || !row.stats || !row.stats.pts || !row.stats.min) {
          throw new Error('Invalid selected player period');
        }
        periods[period] = {sec: row.sec, mean: box(row.mean),
          stats: Object.fromEntries(STATS.filter(k => row.stats[k] != null)
            .map(k => [k, distribution(row.stats[k], mass)]))};
      }
      const multi = ['double_double', 'triple_double', 'quadruple_double', 'quintuple_double', 'five_by_five'];
      if (multi.some(k => !probability(p[k]))) throw new Error('Invalid selected player chances');
      const ifPlays = p.if_plays;
      if (ifPlays && ['min', 'pts', 'reb', 'ast', 'fg3m'].some(k => !Number.isFinite(ifPlays[k]))) {
        throw new Error('Invalid if-plays values');
      }
      return {id: p.id, name: m.name, pos: m.pos ?? null, jersey: m.jersey ?? null,
        status: m.status ?? null, availability_basis: m.availability_basis ?? null,
        played: p.played, selected_availability: p.availability, opening_share: p.opening_share,
        ...Object.fromEntries(multi.map(k => [k, p[k]])),
        ...(ifPlays ? {if_plays: Object.fromEntries(['min', 'pts', 'reb', 'ast', 'fg3m'].map(k => [k, ifPlays[k]]))} : {}),
        periods};
    });
    sides[side] = {players, box: Object.fromEntries(PERIODS.map(k => [k, box(r[side].box?.[k])]))};
  }
  const periods = {};
  for (const period of PERIODS) {
    const p = r.periods?.[period];
    if (!p || !['home', 'away'].every(s => probability(p[s]?.win) && probability(p[s]?.tie))) {
      throw new Error('Invalid selected team period');
    }
    periods[period] = {total: distribution(p.total, mass), margin: distribution(p.margin, mass)};
    for (const side of ['home', 'away']) {
      periods[period][side] = {pts: distribution(p[side].pts, mass), win: p[side].win, tie: p[side].tie};
      if (Math.abs(sides[side].box[period].pts - p[side].pts.mean) > 1e-8) {
        throw new Error('Selected player and team scores differ');
      }
    }
  }
  if (!probability(r.ot)) throw new Error('Invalid selected overtime chance');
  const gameFields = ['id', 'date', 'tip_utc', 'time_valid', 'status', 'detail', 'tv', 'venue', 'city', 'neutral', 'notes', 'periods'];
  const sideFields = ['id', 'abbr', 'score', 'record'];
  const identity = Object.fromEntries(gameFields.filter(k => Object.hasOwn(game, k)).map(k => [k, structuredClone(game[k])]));
  for (const side of ['home', 'away']) identity[side] = Object.fromEntries(sideFields
    .filter(k => Object.hasOwn(game[side], k)).map(k => [k, structuredClone(game[side][k])]));
  return {
    game: identity,
    research: {label: 'Research only; not a validated forecast', game: payload.game, origin: payload.origin,
      engine: payload.engine, model: payload.model, fixture_sha256: payload.fixture_sha256,
      choices: {...r.choices}, selected_players: structuredClone(selected), weight_assumptions: payload.weight_assumptions,
      selected_worlds: r.selected_worlds, selected_mass: mass, total_mass: r.total_mass,
      limitations: [...payload.limitations, 'Histogram counts are probability-mass units, not numbers of worlds.',
        'Opening shares are simulated, not official or projected starters.',
        'Branch-specific minute targets, lead fan, spotlight and advanced distributions are unavailable.']},
    sim: {periods, ...sides, ot: r.ot},
  };
}
