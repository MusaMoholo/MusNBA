import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.location = new URL('http://localhost/');
const {advancedPanel, advancedRates, teamAdvancedRates} = await import('../scripts/webapp/ui.mjs');

test('player rates use retained totals and leave unavailable denominators undefined', () => {
  const line = {pts: 30, fgm: 10, fga: 20, fg3m: 4, fg3a: 8, fta: 6, ast: 6, tov: 2};
  const x = advancedRates(line);
  assert.equal(x.efg, 0.6);
  assert.equal(x.ts, 30 / (2 * (20 + 0.44 * 6)));
  assert.equal(x.two, 0.5);
  assert.equal(x.threeShare, 0.4);
  assert.equal(x.ftRate, 0.3);
  assert.equal(x.astTov, 3);
  assert.equal(advancedRates({...line, fga: 0}).efg, null);
  assert.equal(advancedRates({...line, fga: 8}).two, null);
  assert.equal(advancedRates({...line, tov: 0}).astTov, null);
  assert.equal(advancedRates({...line, fg3m: null}).efg, null);
  assert.match(advancedPanel({pts: 5, fga: 1, fta: 0}, null, 'Season'), /250\.0%/);
});

test('team estimates use each side’s own box possessions and preserve missingness', () => {
  const a = {pts: 110, fga: 90, oreb: 10, dreb: 32, tov: 12, fta: 20, fgm: 40, ast: 24, stl: 8};
  const b = {pts: 100, fga: 80, oreb: 8, dreb: 30, tov: 10, fta: 25};
  const x = teamAdvancedRates(a, b), ap = 90 - 10 + 12 + 0.44 * 20, bp = 80 - 8 + 10 + 0.44 * 25;
  assert.equal(x.poss, ap);
  assert.ok(Math.abs(x.ortg - 100 * 110 / ap) < 1e-10);
  assert.ok(Math.abs(x.drtg - 100 * 100 / bp) < 1e-10);
  assert.equal(x.oreb, 10 / 40);
  assert.equal(x.dreb, 32 / 40);
  assert.equal(x.assist, 24 / 40);
  assert.equal(x.turnover, 12 / ap);
  assert.equal(x.steals, 8 / bp);
  assert.equal(teamAdvancedRates({...a, tov: null}, b).ortg, null);
  assert.equal(teamAdvancedRates(a, null).drtg, null);
  const html = advancedPanel(a, null, 'Projected', {team: true, opponent: b});
  assert.match(html, /not counted possessions/);
  assert.match(html, /per-world distribution unavailable/i);
});

test('projected panels show saved world quantiles and undefined worlds, never ratio of means', () => {
  const d = {defined: 2, total: 3, exact_q: [25, 25, 25, 100, 100], exact_mean: 62.5,
             scale: 1, min: 25, hist: [1, 0, 1], q: [25, 25, 25, 27, 27], mean: 26};
  const html = advancedPanel({fgm: 2, fg3m: 0, fga: 5}, null, 'Projected', {distributions: {efg: d}});
  assert.match(html, /25\.0%/);
  assert.match(html, /mean 62\.5%/);
  assert.match(html, /Defined in 2 of 3 worlds/);
  assert.match(html, /Show distribution/);
  assert.doesNotMatch(html, />40\.0%</);
});

test('actual-only panels do not invent projected values', () => {
  const html = advancedPanel(null, {pts: 4, fga: 2, fta: 0}, 'Projected');
  assert.match(html, /Actual/);
  assert.doesNotMatch(html, /Projected/);
});


test('weighted probability mass is never labelled as independent simulations', () => {
  const d = {defined: 70000, total: 100000, worlds: 20000, defined_worlds: 10000, weighted: true,
    exact_q: [25, 25, 25, 100, 100], exact_mean: 62.5, scale: 1, min: 25, hist: [35000, 35000]};
  const html = advancedPanel({fgm: 2}, null, 'Projected', {distributions: {efg: d}, explore: {gid: 'g', subj: 'p:1'}});
  assert.match(html, /Defined in 10,000 of 20,000 saved worlds/);
  assert.match(html, /70.0% weighted probability/);
  assert.doesNotMatch(html, /100,000.*worlds/);
  assert.match(html, /Explore 25.0% or higher/);
  const legacy = {...d}; delete legacy.worlds; delete legacy.defined_worlds; delete legacy.weighted;
  const old = advancedPanel({fgm: 2}, null, 'Projected', {distributions: {efg: legacy}, worlds: 20000, weighted: true});
  assert.match(old, /20,000 saved worlds/);
  assert.doesNotMatch(old, /100,000.*worlds/);
});

const O = await import('../scripts/webapp/outcomes.mjs');
test('expanded conditions use exact per-world rates, joint masks and defined support', () => {
  const stats = ['min', 'pts', 'reb', 'oreb', 'dreb', 'ast', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'stl', 'blk', 'tov'];
  const rows = [[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], [20,2,3,1,2,4,1,3,0,1,0,0,1,2,2], [30,12,5,2,3,6,4,8,2,4,2,2,2,1,0]];
  const raw = {worlds: 3, players: ['1'], side: [0], stats,
    lines: Buffer.from(rows.flat()).toString('base64'), team_periods: Buffer.alloc(30).toString('base64')};
  const w = O.worldData(raw);
  assert.deepEqual([...w.values('p:1', 'pra')], [0, 9, 23]);
  assert.deepEqual([...w.values('p:1', 'twoAtt')], [0, 2, 4]);
  assert.ok(Number.isNaN(w.values('p:1', 'fgpct')[0]));
  assert.equal(w.values('p:1', 'fgpct')[1], 100 / 3);
  assert.deepEqual([...O.mask(w, [{subj: 'p:1', v: 'fgpct', op: 'gt', x: 33.34}])], [0, 0, 1]);
  assert.deepEqual([...O.mask(w, [{subj: 'p:1', v: 'fga', op: 'eq', x: 3}])], [0, 1, 0]);
  assert.deepEqual([...O.mask(w, [{subj: 'p:1', v: 'fga', op: 'ge', x: 3}, {subj: 'p:1', v: 'pra', op: 'lt', x: 20}])], [0, 1, 0]);
  assert.throws(() => O.mask(w, [{subj: 'p:1', v: 'missing', op: 'ge', x: 1}]), /unavailable/);
  assert.throws(() => O.mask(w, [{subj: 'p:1', v: 'fga', op: 'wat', x: 1}]), /Invalid/);
  w.weights = Float64Array.from([1, 3, 6]); w.baseMask = Uint8Array.from([1, 1, 1]);
  const c = O.branchCalculations(w), m = O.mask(w, [{subj: 'p:1', v: 'fga', op: 'ge', x: 3}]);
  assert.equal(c.count(m), 2); assert.equal(c.mass(m), 9);
  assert.equal(c.mean(w.values('p:1', 'fgpct'), m), (100 + 300) / 9);
  assert.match(O.varOptions('p:1', 'fga', w), /Combined totals/);
});
