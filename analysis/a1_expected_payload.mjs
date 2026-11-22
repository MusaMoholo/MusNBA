// Research-only compact Expected payload; it is not a production or phone-bundle contract.
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
const equal = (a, b) => JSON.stringify(stable(a)) === JSON.stringify(stable(b));

export function expectedPayload(fixture, summary, fixtureHash) {
  const raw = fixture.branches?.[0]?.worlds, result = summary.result;
  if (!hash(fixtureHash) || summary.fixture_sha256 !== fixtureHash || !hash(fixture.source_sha256)
      || typeof fixture.game !== 'string' || typeof fixture.origin !== 'string'
      || typeof fixture.engine !== 'string' || !fixture.engine || typeof fixture.model !== 'string' || !fixture.model
      || !Array.isArray(fixture.selected_players) || !fixture.selected_players.length
      || typeof fixture.weight_assumptions !== 'string' || !fixture.weight_assumptions.trim()
      || !fixture.snapshot_inputs || Object.keys(fixture.snapshot_inputs).length !== 2
      || !['meta', 'games'].every(name => hash(fixture.snapshot_inputs[`data/snapshots/${fixture.origin}/${name}.json`]))
      || !raw || !Array.isArray(raw.players) || !Array.isArray(raw.side)
      || raw.players.length !== raw.side.length || !Array.isArray(fixture.player_metadata)
      || fixture.player_metadata.length !== raw.players.length) throw new Error('Invalid fixture provenance or roster');
  if (!result || result.game !== fixture.game || result.origin !== fixture.origin || !result.choices
      || Object.keys(result.choices).length !== 0 || !equal(result.selected_players, fixture.selected_players)
      || result.weight_assumptions !== fixture.weight_assumptions
      || !Number.isSafeInteger(result.selected_worlds) || result.selected_worlds < 1
      || !Number.isSafeInteger(result.selected_mass) || result.selected_mass !== result.total_mass
      || result.selected_mass <= 0) throw new Error('Expected summary does not match fixture or has a fixed lineup');
  if (new Set(raw.players).size !== raw.players.length
      || raw.players.some((id, i) => fixture.player_metadata[i]?.id !== id || ![0, 1].includes(raw.side[i]))) {
    throw new Error('Identity metadata does not match fixture roster');
  }
  for (const [team, side] of [['home', 0], ['away', 1]]) {
    const ids = raw.players.filter((_, i) => raw.side[i] === side);
    if (!Array.isArray(result[team]?.players) || !equal(result[team].players.map(p => p.id), ids)) {
      throw new Error('Expected player summary does not match fixture roster');
    }
  }
  return {
    kind: 'isolated research Expected-only payload; not a forecast or production bundle',
    fixture_sha256: fixtureHash, source_sha256: fixture.source_sha256,
    game: fixture.game, origin: fixture.origin, engine: fixture.engine, model: fixture.model,
    snapshot_inputs: structuredClone(fixture.snapshot_inputs),
    selected_players: structuredClone(fixture.selected_players), weight_assumptions: fixture.weight_assumptions,
    player_metadata: structuredClone(fixture.player_metadata),
    roster: {players: [...raw.players], side: [...raw.side]},
    limitations: ['Research only; availability probabilities are uncalibrated.',
      'Joint availability independence is unvalidated.', 'No branch worlds or interactive Given/Joint data are included.'],
    expected: structuredClone(result),
  };
}
