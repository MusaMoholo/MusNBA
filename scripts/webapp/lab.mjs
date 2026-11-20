// Forecast Lab: the engines' trust tests against real games, as logged by the pipeline (views.py → api/lab.json).
// Players first (D28): minutes and box-score outcomes by tier, then team strength and game results v the team model.
import {api, dayLabel, esc, f1, rate, signed} from './ui.mjs';

const TIERS = [['star', 'Stars (usage ≥ 25%)'], ['starter', 'Starters'], ['bench', 'Bench']];

function runLabel(r) {
  const what = r.config === 'v1.1' ? 'v1.1' : r.config === 'v1.2d' ? 'v1.2d (defence)' : r.config;
  const rot = r.rotation === 'targets' ? 'D29 minutes' : 'replayed rotations';
  return `${esc(what)} · ${rot}${r.known_starters ? ' · real starters' : ''}`;
}
const when = r => dayLabel(`${r.stamp.slice(0, 4)}-${r.stamp.slice(4, 6)}-${r.stamp.slice(6, 8)}`);

function bias(v, extra = '') {  // relative bias: within 2% good, 5% warn, beyond bad
  if (v == null) return `<td class="dim ${extra}">—</td>`;
  const a = Math.abs(v), cls = a <= 0.02 ? 'up' : a <= 0.05 ? '' : 'down';
  return `<td class="${cls} ${extra}">${signed(100 * v)}%</td>`;
}
function cover(v, extra = '') {  // 10–90% coverage: 80% is right
  if (v == null) return `<td class="dim ${extra}">—</td>`;
  const cls = Math.abs(v - 0.8) <= 0.05 ? 'up' : Math.abs(v - 0.8) <= 0.12 ? '' : 'down';
  return `<td class="${cls} ${extra}">${rate(v, 0)}</td>`;
}
const num = (v, d = 2) => (v == null ? '—' : Number(v).toFixed(d));

function playerTables(runs) {
  return TIERS.map(([tier, title]) => {
    const rows = runs.filter(r => r.players[tier]).map(r => {
      const p = r.players[tier];
      const s = k => p[k] || {};
      return `<tr><td class="name l">${runLabel(r)}<div class="note" style="margin:0">${esc(when(r))} · ${r.games} games</div></td>
        <td class="opt">${f1(s('min').actual)}</td><td class="opt">${f1(s('min').sim)}</td>${bias(s('min').rel_bias)}${cover(s('min').coverage_10_90)}
        <td class="opt">${f1(s('pts').actual)}</td><td class="opt">${f1(s('pts').sim)}</td>${bias(s('pts').rel_bias)}${cover(s('pts').coverage_10_90)}
        ${bias(s('reb').rel_bias, 'opt')}${bias(s('ast').rel_bias, 'opt')}<td class="dim opt">${num(s('pts').crps)}</td></tr>`;
    }).join('');
    return `<h3 style="margin:12px 0 4px">${title}</h3><div class="scroll"><table><thead><tr><th class="name l">Run</th>
      <th class="opt">Min real</th><th class="opt">Min sim</th><th>Min bias</th><th>Min 10–90%</th><th class="opt">Pts real</th><th class="opt">Pts sim</th><th>Pts bias</th><th>Pts 10–90%</th>
      <th class="opt">Reb bias</th><th class="opt">Ast bias</th><th class="opt">Pts CRPS</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }).join('');
}

function strengthTable(runs) {
  const rows = runs.map(r => {
    const sim = r.strength?.sim || {}, real = r.strength?.real || {};
    const share = (a, b) => (a != null && b ? `${Math.round(100 * a / b)}%` : '—');
    const vs = (a, b, lowerBetter = true, extra = '') => {
      if (a == null || b == null) return `<td class="dim ${extra}">—</td>`;
      const better = lowerBetter ? a < b : a > b;
      return `<td class="${better ? 'up' : 'down'} ${extra}">${num(a)} <span class="dim">v ${num(b)}</span></td>`;
    };
    return `<tr><td class="name l">${runLabel(r)}<div class="note" style="margin:0">${esc(when(r))}</div></td>
      <td>${num(sim.opp_defence)} <span class="dim">v ${num(real.opp_defence)}</span></td><td>${share(sim.opp_defence, real.opp_defence)}</td>
      <td class="opt">${num(sim.offence)} <span class="dim">v ${num(real.offence)}</span></td><td>${num(r.margin.slope_real_on_sim)}</td>
      ${vs(r.margin.crps, r.team_model.margin_crps)}${vs(r.total.crps, r.team_model.total_crps, true, 'opt')}${vs(r.win_log_loss, r.team_model.win_log_loss, true, 'opt')}
      <td class="opt">${signed(r.total.bias)}</td>${cover(r.total.coverage_10_90, 'opt')}</tr>`;
  }).join('');
  return `<div class="scroll"><table><thead><tr><th class="name l">Run</th><th>Defence loading</th><th>Expressed</th><th class="opt">Offence loading</th>
    <th>Margin slope</th><th>Margin CRPS v team</th><th class="opt">Total CRPS v team</th><th class="opt">Win log loss v team</th><th class="opt">Total bias</th><th class="opt">Total 10–90%</th></tr></thead>
    <tbody>${rows}</tbody></table></div>
    <p class="note">Loading: points per 100 of each side regressed on its offensive rating and the opponent's defensive rating (before the date); the engine's should match real games' (shown after "v"). Margin slope: real margin on the simulated one — 1 is right, above 1 means team quality is under-expressed. CRPS and log loss: lower is better; green where the engine beats the team-rating model on the same games.</p>`;
}

function lineupPanel(l) {
  if (!l || !l.overall) return '<p class="note">No finished slates scored yet.</p>';
  const rows = l.slates.slice().reverse().map(s => `<tr><td class="l">${esc(dayLabel(s.slate))}</td><td class="l dim opt">${esc(s.model || '')}</td><td>${s.team_games}</td>
    <td>${rate(s.slot_accuracy, 1)}</td><td>${rate(s.all_five, 0)}</td></tr>`).join('');
  return `<div class="tiles"><div class="tile"><div class="note" style="margin:0">Starter slots right</div><b>${rate(l.overall.slot_accuracy, 1)}</b></div>
      <div class="tile"><div class="note" style="margin:0">All five right</div><b>${rate(l.overall.all_five, 1)}</b></div>
      <div class="tile"><div class="note" style="margin:0">Team-games</div><b>${l.overall.team_games}</b></div></div>
    <div class="scroll" style="margin-top:8px"><table><thead><tr><th class="l">Slate</th><th class="l opt">Model</th><th>Team-games</th><th>Slots right</th><th>All five</th></tr></thead>
    <tbody>${rows}</tbody></table></div>
    <p class="note">Each saved slate's projected starters against the real ones once its games are final. Our own projection (start share, then priority) gets 89.4% of slots right on Jan–Apr 2026 with known availability — the bar for any lineup source (D33).</p>`;
}

function allocatorPanel(a) {
  if (!a) return '';
  const rows = TIERS.filter(([t]) => a[t]).map(([t, title]) => `<tr><td class="l">${title}</td><td>${f1(a[t].actual)}</td><td>${f1(a[t].alloc)}</td>
    ${bias(a[t].rel_bias)}<td>${f1(a[t].mae)}</td><td class="dim opt">${f1(a[t].ewma_min_avg_mae)}</td>${cover(a[t].coverage_10_90)}</tr>`).join('');
  return `<section class="panel"><h2>Minutes allocator (D29) — no engine</h2><div class="scroll"><table><thead><tr><th class="l">Tier (tonight's starter flag)</th>
    <th>Real min</th><th>Allocated</th><th>Bias</th><th>MAE</th><th class="opt">MAE recent avg</th><th>10–90%</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="note">Healthy-role minutes allocated to exactly 240 per team by priority, with the return ramp and per-world draws, against real regulation minutes in Jan–Apr 2026 (the players who played). Run ${esc(a.run)}.</p></section>`;
}

export async function render(view, {current}) {
  const lab = await api('lab');
  if (!current()) return;
  const runs = lab.backtests || [];
  view.innerHTML = `
    <section class="panel"><div class="row" style="justify-content:space-between">
      <div><h2 style="margin:0">Forecast Lab</h2><p class="note" style="margin:0">The engines against real games — every change is promoted only if these tests say it is better (D22).</p></div>
      <span class="pill good" title="${esc(lab.serving?.label || '')}">Serving ${esc(lab.serving?.version || lab.serving?.id || '')}</span></div></section>
    <section class="panel"><h2>Players first — engine backtest (M9)</h2>
      <p class="note">Held-out games played forward by the engine with only what was known before each date (known availability), scored against real box scores. Bias: green within ±2%; 10–90% coverage: green within 75–85% (80% is right).</p>
      ${runs.length ? playerTables(runs) : '<p class="note">No backtest runs logged.</p>'}</section>
    <section class="panel"><h2>Team strength and game results</h2>${runs.length ? strengthTable(runs) : ''}</section>
    <section class="panel"><h2>Projected starters — nightly record</h2>${lineupPanel(lab.lineups)}</section>
    ${allocatorPanel(lab.minutes_allocator)}`;
}
