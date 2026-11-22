// Game Centre. One period selector (Q1–Q4, H1, H2, FG) drives the bezel and both views:
// Player = per-period box scores, Team = per-period team lines and distributions. Matchup is separate.
import {api, atLeast, modelPill, barChart, dayLabel, defaultLine, esc, f1, halfLine, heat, histogram, logo, over, pct, percentileOf,
        probWhere, rate, record, seg, segGroups, signed, stamp, statusTag, store, team, tipTimes} from './ui.mjs';
import * as S from './scenario.mjs';
import {gameSpotlight} from './spotlight.mjs';

export const PERIODS = [['q1', 'Q1', '1st quarter'], ['q2', 'Q2', '2nd quarter'], ['q3', 'Q3', '3rd quarter'], ['q4', 'Q4', '4th quarter'],
                        ['h1', 'H1', '1st half'], ['h2', 'H2', '2nd half'], ['fg', 'FG', 'Full game']];
const PERIOD_IDS = PERIODS.map(p => p[0]);
const periodName = id => PERIODS.find(p => p[0] === id)?.[2] || 'Full game';
const LABEL = {pts: 'PTS', reb: 'REB', oreb: 'OREB', dreb: 'DREB', ast: 'AST', fg3m: '3PM', fgm: 'FGM', ftm: 'FTM', pra: 'PRA', pr: 'P+R',
               pa: 'P+A', ra: 'R+A', stl: 'STL', blk: 'BLK', stocks: 'STL+BLK', tov: 'TOV', min: 'MIN', fga: 'FGA', fta: 'FTA', fg3a: '3PA'};
const NAME = {pts: 'Points', reb: 'Rebounds', oreb: 'Offensive rebounds', dreb: 'Defensive rebounds', ast: 'Assists', fg3m: 'Threes made',
              fgm: 'Field goals made', ftm: 'Free throws made', pra: 'Points + rebounds + assists',
              pr: 'Points + rebounds', pa: 'Points + assists', ra: 'Rebounds + assists', stl: 'Steals', blk: 'Blocks',
              stocks: 'Steals + blocks', tov: 'Turnovers', min: 'Minutes', fga: 'Field-goal attempts',
              fta: 'Free-throw attempts', fg3a: 'Three-point attempts'};
// Owner (20 Nov): makes and the main stats only — no combos or attempts; a stat shows once its distribution is stored
const SHEET_FG = ['pts', 'reb', 'oreb', 'dreb', 'ast', 'fg3m', 'fgm', 'ftm', 'stl', 'blk', 'tov', 'min'];
const SHEET_PERIOD = ['pts', 'reb', 'oreb', 'dreb', 'ast', 'fg3m', 'fgm', 'ftm', 'stl', 'blk', 'min'];
// Owner (20 Nov): Scoring · Rebounding (ALL / OFF / DEF) · Handling · Defense · Time; button text per group, LABEL elsewhere
const STAT_GROUPS = [['Scoring', [['pts', 'PTS'], ['fgm', 'FGM'], ['fg3m', '3PM'], ['ftm', 'FTM']]],
                     ['Rebounding', [['reb', 'ALL'], ['oreb', 'OFF'], ['dreb', 'DEF']]],
                     ['Handling', [['ast', 'AST'], ['tov', 'TOV']]], ['Defense', [['stl', 'STL'], ['blk', 'BLK']]], ['Time', [['min', 'MIN']]]];
const state = {mode: null, stat: store.get('stat', 'pts'), period: 'fg', lines: new Map()};

export async function render(view, {rest, current}) {
  const gid = rest[0];
  const data = await api('game/' + encodeURIComponent(gid));
  if (!current()) return;
  if (rest[1] === 'player' && rest[2]) {
    state.period = PERIOD_IDS.includes(rest[3]) ? rest[3] : state.period;
    return sheet(view, data, rest[2], current);
  }
  const matchup = rest[1] === 'matchup', scenario = rest[1] === 'scenario' && Boolean(data.worlds);
  const period = scenario ? 'fg' : sims(data) && PERIOD_IDS.includes(rest[1]) ? rest[1] : (sims(data) ? state.period : 'fg');
  const mode = rest[2] === 'team' ? 'team' : 'player';
  state.period = period;
  const base = `#/game/${gid}`;
  view.innerHTML = `<a class="crumb" href="#/today/${data.game.date}">‹ ${esc(dayLabel(data.game.date))} slate</a>
    ${bezel(data, period, {matchup, scenario, mode, base})}<div id="game-body"></div>`;
  const body = view.querySelector('#game-body');
  const go = (p, m) => location.replace(`${base}/${p}${m === 'team' ? '/team' : ''}`);
  view.querySelector('select.period')?.addEventListener('change', e => go(e.target.value, matchup ? 'player' : mode));
  view.querySelectorAll('[data-view]').forEach(b => b.onclick = () => ['matchup', 'scenario'].includes(b.dataset.view) ? location.replace(`${base}/${b.dataset.view}`) : go(period, b.dataset.view));
  if (matchup) return matchupView(body, data);
  if (scenario) return S.scenarioView(body, data, rest[2]);
  if (!sims(data) && !data.actual) {
    body.innerHTML = '<section class="panel"><p class="note">Player and period projections appear when the game simulation runs on the morning of the slate.</p></section>';
    return;
  }
  (mode === 'team' ? teamView : playerView)(body, data, period);
}

const sims = data => data.projection?.sim;

// ------------------------------------------------------------------ formatting
const mmss = sec => {
  if (sec == null || !Number.isFinite(sec)) return '—';
  const total = Math.round(sec);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
};
const spread = (margin, A, H) => Math.abs(margin) < 0.05 ? 'PK' : margin > 0 ? `${H.abbr} −${margin.toFixed(1)}` : `${A.abbr} −${(-margin).toFixed(1)}`;
const intSpread = (margin, A, H) => margin === 0 ? 'Tied' : margin > 0 ? `${H.abbr} −${margin}` : `${A.abbr} −${-margin}`;
const shoot = (m, a, projected) => {
  if (m == null || a == null) return '—';
  const p = a > 0 ? ` <small class="dim">(${(100 * m / a).toFixed(1)}%)</small>` : ' <small class="dim">(—)</small>';
  return projected ? `${f1(m)}/${f1(a)}${p}` : `${m}/${a}${p}`;  // owner (20 Nov): x/y (z%)
};

// ------------------------------------------------------------------ bezel
function actualPoints(data, side, period) {
  const g = data.game, l = data.actual?.[side]?.linescores;
  if (period === 'fg') return g[side].score;
  if (!l || l.length < 4) return null;
  return {q1: l[0], q2: l[1], q3: l[2], q4: l[3], h1: l[0] + l[1], h2: l[2] + l[3]}[period];
}

function bezel(data, period, {matchup, scenario, mode, base}) {
  const g = data.game, P = data.projection, sim = sims(data), tm = data.team_model;
  const A = team(g.away.id), H = team(g.home.id);
  const t = tipTimes(g.tip_utc, g.date, g.time_valid);
  const final = g.status === 'final';
  const per = sim?.periods?.[period];
  const actual = final ? {away: actualPoints(data, 'away', period), home: actualPoints(data, 'home', period)} : null;
  const hasActual = actual && actual.away != null && actual.home != null;
  // Δ v the team's season scoring average for this period (owner, 20 Nov: the matchup's effect at team level)
  const seasonPts = side => {
    const c = data.comparison?.[side];
    if (!c) return null;
    const q = c.quarters || [];
    return {fg: c.pts, q1: q[0], q2: q[1], q3: q[2], q4: q[3], h1: q[0] + q[1], h2: q[2] + q[3]}[period] ?? null;
  };
  const dlt = (v, base, title) => (v == null || base == null || !Number.isFinite(v - base) ? ''
    : `<small class="dlt ${v - base > 0.5 ? 'up' : v - base < -0.5 ? 'down' : ''}" title="${esc(title)} ${f1(base)}">${signed(v - base)}</small>`);
  const block = (side, info) => {
    const s = g[side];
    const proj = per?.[side];
    const pts = hasActual ? actual[side] : proj ? f1(proj.pts.mean) : tm && period === 'fg' ? f1(side === 'home' ? tm.mu_home : tm.mu_away) : '—';
    let win = proj ? pct(proj.win) : tm && period === 'fg' ? pct(side === 'home' ? tm.p_home : 1 - tm.p_home) : '—';
    let winLabel = 'Win';
    if (hasActual) {
      const mine = actual[side], theirs = actual[side === 'home' ? 'away' : 'home'];
      win = mine > theirs ? 'W' : mine < theirs ? 'L' : 'T';
      winLabel = proj ? `Win · pre ${pct(proj.win, 0)}` : 'Result';
    }
    const sub = hasActual ? (proj ? `proj ${f1(proj.pts.mean)}` : '') : proj ? `<span class="lbl">10–90%: </span>${proj.pts.q[0]}–${proj.pts.q[4]}` : '';
    return `<a class="bz-team ${side}" href="#/team/${s.id}" title="${esc(info.name)}">
      <div class="bz-id">${logo(s.id)}<span><b><span class="long">${esc(info.short)}</span><span class="short">${esc(info.abbr)}</span></b><small>${record(s.record)}</small></span></div>
      <div class="bz-stats"><div>${dlt(hasActual ? actual[side] : proj?.pts.mean, seasonPts(side), 'v season average')}<b>${pts}</b><span>Pts</span></div><div><b class="win">${win}</b><span>${winLabel}</span></div></div>
      <div class="bz-sub">${sub}</div></a>`;
  };
  let total = '—', spr = '—', note = '';
  if (hasActual) {
    total = String(actual.away + actual.home);
    spr = intSpread(actual.home - actual.away, A, H);
    note = per ? `proj ${f1(per.total.mean)} · ${spread(per.margin.mean, A, H)}` : 'Final';
  } else if (per) {
    total = f1(per.total.mean);
    spr = spread(per.margin.mean, A, H);
    note = `<span class="lbl">10–90%: </span>${per.total.q[0]}–${per.total.q[4]} · ${period === 'fg' ? `OT ${pct(sim.ot)}` : `tie ${pct(per.home.tie)}`}`;
  } else if (tm && period === 'fg') {
    total = f1(tm.mu_home + tm.mu_away);
    spr = spread(tm.mu_home - tm.mu_away, A, H);
    note = 'Team-strength estimate';
  }
  const status = final ? `Final${g.periods > 4 ? (g.periods > 5 ? `/${g.periods - 4}OT` : '/OT') : ''}` : g.status === 'live' ? esc(g.detail) : esc(t.uk) + ' UK';
  const options = groups => groups.map(([label, ids]) => `<optgroup label="${label}">${ids.map(id => `<option value="${id}"${id === period ? ' selected' : ''}>${PERIODS.find(p => p[0] === id)[1]} · ${periodName(id)}</option>`).join('')}</optgroup>`).join('');
  const select = sim
    ? `<label class="sr" for="period-select">Period</label><select id="period-select" class="period"${matchup || scenario ? ' disabled' : ''}>${options([['Quarters', ['q1', 'q2', 'q3', 'q4']], ['Halves', ['h1', 'h2']], ['Game', ['fg']]])}</select>`
    : '<span class="pill">Full game only until the game simulation runs</span>';
  const chips = P ? `<div class="chips">${modelPill(P.model)}
      <span class="pill ${P.kind === 'prospective' ? 'good' : 'warn'}">${P.kind === 'prospective' ? (P.pre_tip ? 'Pre-game' : 'Built after tip-off') : 'Retrospective'}</span>
      <span class="pill">${sim.sims.toLocaleString()} sims · ${esc(stamp(P.generated))}</span></div>`
    : tm ? '<div class="chips"><span class="pill">Team-strength estimate from the season simulation</span></div>' : '';
  return `<section class="panel bezel">
    <p class="bz-meta">${esc(dayLabel(g.date, {weekday: 'short', day: 'numeric', month: 'short'}))} · ${esc(t.label)}${g.venue ? ' · ' + esc(g.venue) : ''}${g.tv.length ? ' · ' + esc(g.tv.join(', ')) : ''}</p>
    <div class="bz-grid">${block('away', A)}
      <div class="bz-mid"><div class="bz-period">${esc(periodName(period))} · ${status}</div>
        <div class="bz-stats"><div><b>${total}</b><span>Total</span></div><div><b class="spr">${esc(spr)}</b><span>Spread</span></div></div>
        <div class="bz-sub">${note}</div></div>
      ${block('home', H)}</div>
    <div class="bz-controls">${select}
      ${seg([['player', 'Player'], ['team', 'Team']], matchup || scenario ? '' : mode, 'data-view')}
      <span class="spacer"></span>${data.worlds ? `<button type="button" class="ghost${scenario ? ' on' : ''}" data-view="scenario" aria-pressed="${scenario}">Scenarios</button>` : ''}<button type="button" class="ghost${matchup ? ' on' : ''}" data-view="matchup" aria-pressed="${matchup}">Matchup</button></div>
    ${chips}</section>`;
}

// ------------------------------------------------------------------ player view: box score per period
const COLS = [['min', 'MIN'], ['pts', 'PTS'], ['reb', 'REB'], ['ast', 'AST'], ['stl', 'STL'], ['blk', 'BLK'], ['fg', 'FG'], ['fg3', '3P'], ['ft', 'FT']];

function actualLine(r, period) {
  if (!r || r.dnp) return null;
  if (period === 'fg') return {sec: r.periods?.fg_sec ?? (r.min ?? 0) * 60, pts: r.pts, reb: r.reb, ast: r.ast, stl: r.stl, blk: r.blk,
    fgm: r.fgm, fga: r.fga, fg3m: r.fg3m, fg3a: r.fg3a, ftm: r.ftm, fta: r.fta};
  return r.periods?.[period] || null;
}
function projCell(p, key) {
  const m = p.mean;
  if (key === 'min') return mmss(p.sec);
  if (key === 'fg') return shoot(m.fgm, m.fga, true);
  if (key === 'fg3') return shoot(m.fg3m, m.fg3a, true);
  if (key === 'ft') return shoot(m.ftm, m.fta, true);
  return f1(m[key]);
}
function actCell(a, key) {
  if (key === 'min') return mmss(a.sec);
  if (key === 'fg') return shoot(a.fgm, a.fga);
  if (key === 'fg3') return shoot(a.fg3m, a.fg3a);
  if (key === 'ft') return shoot(a.ftm, a.fta);
  return a[key] ?? '—';
}

function playerView(el, data, period) {
  const sim = sims(data), act = data.actual;
  const modes = [];
  if (sim) modes.push(['proj', 'Projected']);
  if (act) modes.push(['act', 'Actual']);
  if (sim && act) modes.push(['cmp', 'Actual vs projected']);
  const mode = modes.some(m => m[0] === state.mode) ? state.mode : (sim && act ? 'cmp' : modes[0][0]);
  el.innerHTML = (period === 'fg' && data.spotlight ? gameSpotlight(data.spotlight) : '') +
    (modes.length > 1 ? `<div class="controls">${seg(modes, mode, 'data-mode')}</div>` : '') +
    ['away', 'home'].map(s => teamBox(data, s, mode, period)).join('') +
    `<p class="note">${period === 'fg' ? 'Full game includes overtime.' : `${esc(periodName(period))} only; overtime counts in FG.`} Projected values are means over ${sim ? sim.sims.toLocaleString() : ''} simulated games${mode === 'proj' && period === 'fg' && data.averages ? '; small numbers: projection minus his season average (MIN, PTS, REB, AST, STL, BLK; shooting in percentage points)' : ''}. Tap a player for distributions, lines and what-ifs.</p>`;
  el.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => { state.mode = b.dataset.mode; playerView(el, data, period); });
  el.querySelectorAll('tr[data-pid]').forEach(tr => {
    tr.onclick = () => { location.hash = `#/game/${data.game.id}/player/${tr.dataset.pid}/${period}`; };
    tr.onkeydown = e => { if (e.key === 'Enter') tr.onclick(); };
  });
}

function teamBox(data, side, mode, period) {
  const tid = data.game[side].id, info = team(tid);
  const sim = sims(data)?.[side], act = data.actual?.[side];
  const head = `<tr><th class="name">Player</th>${COLS.map(([, l]) => `<th>${l}</th>`).join('')}</tr>`;
  const actualIds = new Set((act?.players || []).filter(r => !r.dnp).map(r => r.id));
  const ruledOut = mode === 'act' || !sim ? [] : sim.players.filter(p => !p.periods && !actualIds.has(p.id));
  let rows = [];
  if (mode === 'proj') {
    const avg = period === 'fg' ? data.averages || {} : {};
    rows = sim.players.filter(p => p.periods).map(p => ({id: p.id, name: p.name, pos: p.pos, starter: p.starter,
      tag: statusTag(p.status, p.availability), cells: COLS.map(([k]) => {
        const cell = projCell(p.periods[period], k), a = avg[p.id]?.season;
        if (!a) return cell;
        const m = p.periods.fg.mean;
        if (['fg', 'fg3', 'ft'].includes(k)) {  // owner (20 Nov): the shooting percentage's change, not makes and attempts
          const [mk, at] = {fg: ['fgm', 'fga'], fg3: ['fg3m', 'fg3a'], ft: ['ftm', 'fta']}[k];
          if (!(a[at] > 0) || !(m[at] > 0)) return cell;
          const d = 100 * (m[mk] / m[at] - a[mk] / a[at]);
          // owner (20 Nov): the same shape as the value, x/y (z%), each part coloured by its own sign
          const part = (v, step, text) => `<span class="${v > step ? 'up' : v < -step ? 'down' : ''}">${text}</span>`;
          return `${cell}<span class="sub" title="v season ${f1(a[mk])}-${f1(a[at])} (${(100 * a[mk] / a[at]).toFixed(1)}%)">${part(m[mk] - a[mk], 0.05, signed(m[mk] - a[mk]))}/${part(m[at] - a[at], 0.05, signed(m[at] - a[at]))} (${part(d, 0.5, signed(d) + '%')})</span>`;
        }
        if (!['pts', 'reb', 'ast', 'min', 'stl', 'blk'].includes(k)) return cell;
        const pv = k === 'min' ? p.periods.fg.sec / 60 : m[k], d = pv - a[k];
        const step = ['stl', 'blk'].includes(k) ? 0.1 : 0.25;
        return `${cell}<span class="sub ${d > step ? 'up' : d < -step ? 'down' : ''}" title="v season average ${f1(a[k])}">${signed(d)}</span>`;
      })}));
  } else if (mode === 'act') {
    rows = act.players.map(r => {
      const a = actualLine(r, period);
      return {id: r.id, name: r.name, pos: r.pos, starter: r.starter, dnp: r.dnp,
        tag: r.dnp ? `<span class="tag">${esc(r.reason || 'DNP')}</span>` : '',
        cells: COLS.map(([k]) => a ? actCell(a, k) : (r.dnp ? '' : '—'))};
    });
  } else {
    const byId = new Map(act.players.map(r => [r.id, r]));
    const seen = new Set();
    for (const p of sim.players) {
      if (!p.periods) continue;
      seen.add(p.id);
      const r = byId.get(p.id), a = actualLine(r, period), proj = p.periods[period];
      rows.push({id: p.id, name: p.name, pos: p.pos, starter: r ? r.starter : p.starter,
        tag: r?.dnp ? `<span class="tag">${esc(r.reason || 'DNP')}</span>` : !r ? '<span class="tag">not in box score</span>' : '',
        cells: COLS.map(([k]) => {
          const projected = projCell(proj, k);
          if (!a) return `<span class="sub">${projected}</span>`;
          const value = actCell(a, k), d = proj.stats?.[k];
          const cls = d && typeof value === 'number' ? (value > d.q[4] ? ' up' : value < d.q[0] ? ' down' : '') : '';
          return `<span class="act${cls}">${value}</span><span class="sub">${projected}</span>`;
        })});
    }
    for (const r of act.players) if (!seen.has(r.id) && !r.dnp) {
      const a = actualLine(r, period);
      rows.push({id: r.id, name: r.name, pos: r.pos, starter: r.starter, tag: '<span class="tag">not projected</span>',
        cells: COLS.map(([k]) => a ? `<span class="act">${actCell(a, k)}</span>` : '—')});
    }
    rows.sort((x, y) => Number(y.starter) - Number(x.starter));
  }
  const starters = rows.filter(r => r.starter), bench = rows.filter(r => !r.starter);
  const tr = r => `<tr class="link" data-pid="${esc(r.id)}" tabindex="0"><td class="name">${esc(r.name)} <span class="tag">${esc(r.pos || '')}</span>${r.tag}</td>${r.cells.map(c => `<td>${c}</td>`).join('')}</tr>`;
  const sep = label => `<tr class="sep"><td class="name">${label}</td>${COLS.map(() => '<td></td>').join('')}</tr>`;
  const projTeam = sim?.box?.[period];
  const totalRow = (label, line, projected) => `<tr class="sep"><td class="name">${label}</td>${COLS.map(([k]) =>
    `<td>${k === 'min' ? '' : k === 'fg' ? shoot(line.fgm, line.fga, projected) : k === 'fg3' ? shoot(line.fg3m, line.fg3a, projected) : k === 'ft' ? shoot(line.ftm, line.fta, projected) : projected ? f1(line[k]) : line[k]}</td>`).join('')}</tr>`;
  let totals = '';
  if (projTeam && mode !== 'act') totals += totalRow('Team (projected)', projTeam, true);
  if (act && mode !== 'proj') {
    const sum = {pts: 0, reb: 0, ast: 0, stl: 0, blk: 0, fgm: 0, fga: 0, fg3m: 0, fg3a: 0, ftm: 0, fta: 0};
    let complete = true;
    for (const r of act.players) { if (r.dnp) continue; const a = actualLine(r, period); if (!a) { complete = false; continue; } for (const k in sum) sum[k] += a[k] || 0; }
    if (period === 'fg' && act.totals) Object.assign(sum, act.totals);
    else if (complete) sum.pts = actualPoints(data, side, period) ?? sum.pts;
    totals += totalRow('Team (actual)', sum, false);
  }
  const pts = mode === 'act' ? actualPoints(data, side, period) : sim?.periods ? null : null;
  const per = sims(data)?.periods?.[period]?.[side];
  const title = mode === 'act' ? `${actualPoints(data, side, period) ?? '—'} pts` : per ? `Projected ${f1(per.pts.mean)} pts · win ${pct(per.win)}${mode === 'cmp' ? ` · actual ${actualPoints(data, side, period) ?? '—'}` : ''}` : '';
  void pts;
  return `<section class="panel"><div class="row" style="margin-bottom:8px">${logo(tid)}<h2 style="margin:0">${esc(info.name)}</h2><span class="note" style="margin:0">${title}</span></div>
    <div class="scroll"><table class="box"><thead>${head}</thead><tbody>${sep('Starters')}${starters.map(tr).join('')}${bench.length ? sep('Bench') : ''}${bench.map(tr).join('')}${totals}</tbody></table></div>
    ${ruledOut.length ? `<p class="note"><b>Out:</b> ${ruledOut.map(p => `<a href="#/game/${data.game.id}/player/${esc(p.id)}">${esc(p.name)}</a>${p.injury?.type ? ` <span class="dim">(${esc(p.injury.type)})</span>` : ''}`).join(', ')}</p>` : ''}</section>`;
}

// ------------------------------------------------------------------ team view: period lines
const lineKey = (data, id) => data.game.id + '|' + id;
const ordinal = n => n + ({1: 'st', 2: 'nd', 3: 'rd'}[n % 100 > 10 && n % 100 < 14 ? 0 : n % 10] || 'th');
function marginText(line, A, H) {
  return line >= 0 ? `${H.abbr} by more than ${line}` : `${A.abbr} by fewer than ${-line}, or ${H.abbr} wins`;
}
function stepLadder(d, {suffix = '+', minStep = 1} = {}) {
  const span = Math.max(1, d.q[4] - d.q[0]);
  const step = Math.max(minStep, span > 60 ? 10 : span > 16 ? 5 : span > 8 ? 2 : 1);
  const lo = Math.max(1, d.q[0] - step), hi = d.q[4] + step;
  const out = [];
  for (let k = Math.ceil(lo / step) * step; k <= hi && out.length < 10; k += step) out.push([`${k}${suffix}`, atLeast(d, k)]);
  if (out.length < 3) for (let k = 1; out.length < 3; k++) if (!out.some(([l]) => l === k + suffix)) out.push([`${k}${suffix}`, atLeast(d, k)]);
  return out.sort((a, b) => parseInt(a[0]) - parseInt(b[0]));
}
function distBlock(data, b) {
  const key = lineKey(data, b.id);
  const line = state.lines.has(key) ? halfLine(state.lines.get(key)) : defaultLine(b.d);
  const pOver = over(b.d, line);  // x.5 lines: no push
  return `<section class="panel" data-block="${b.id}">
    <div class="row" style="justify-content:space-between"><h2 style="margin:0">${esc(b.title)}</h2>
      <span class="note" style="margin:0">mean ${f1(b.d.mean)} · median ${b.d.q[2]} · 10–90%: ${b.d.q[0]} to ${b.d.q[4]}</span></div>
    <div class="dist" style="margin-top:8px"><div>${histogram(b.d, {line: b.side ? null : line, side: b.side, actual: b.actual ?? null})}
        <div class="lineinput"><label for="line-${b.id}">${b.side ? 'Margin over' : 'Over'}</label>
          <input id="line-${b.id}" type="number" step="1" value="${line}" data-line="${b.id}">
          <output>${b.side ? esc(marginText(line, b.A, b.H)) + ': ' : 'Over: '}${pct(pOver)}</output>
          ${b.side ? '' : `<span class="dim">Under: ${pct(1 - pOver)}</span>`}</div>
        ${b.actual != null ? `<p class="note">Actual: <b>${b.actual}</b> · ${ordinal(Math.round(100 * percentileOf(b.d, b.actual)))} percentile of the simulations</p>` : ''}</div>
      <div class="scroll"><table><thead><tr><th class="l">${b.side ? 'Outcome' : 'Line'}</th><th>Chance</th></tr></thead><tbody>
        ${b.ladder(b.d).map(([label, p]) => `<tr><td class="l">${esc(label)}</td>${heat(p, {digits: 1})}</tr>`).join('')}</tbody></table></div></div></section>`;
}
function wireBlocks(el, data, paint) {
  el.querySelectorAll('input[data-line]').forEach(input => input.onchange = () => {
    const v = Number(input.value);
    if (Number.isFinite(v)) { state.lines.set(lineKey(data, input.dataset.line), halfLine(v)); paint(); }
  });
  el.querySelectorAll('[data-block] svg.hist').forEach(svg => svg.onclick = e => {
    const v = e.target.closest('rect.hit')?.dataset.v;
    if (v != null) { state.lines.set(lineKey(data, svg.closest('[data-block]').dataset.block), Number(v) - 0.5); paint(); }
  });
}

// U5 + U6: game flow — the home lead at each break as a fan (10–90 and 25–75 bands, median) and each side's points per
// quarter with 10–90 whiskers (actual dots once final). From the stored worlds and period distributions.
function flowCharts(data) {
  const sim = sims(data), fan = data.lead_fan;
  if (!sim) return '';
  const A = team(data.game.away.id), H = team(data.game.home.id);
  let fanSvg = '';
  if (fan) {
    const W = 420, Hh = 190, pl = 34, pr = 12, pt = 12, pb = 40;
    const lo = Math.min(-5, ...fan.q.map(q => q[0])), hi = Math.max(5, ...fan.q.map(q => q[4]));
    const x = i => pl + i * (W - pl - pr) / (fan.q.length - 1), y = v => pt + (hi - v) * (Hh - pt - pb) / (hi - lo);
    const band = (a, b) => fan.q.map((q, i) => `${x(i).toFixed(1)},${y(q[a]).toFixed(1)}`).join(' ') + ' ' + fan.q.map((q, i) => `${x(i).toFixed(1)},${y(q[b]).toFixed(1)}`).reverse().join(' ');
    const med = fan.q.map((q, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(q[2]).toFixed(1)}`).join(' ');
    const ticks = [lo, 0, hi].map(v => `<text x="${pl - 6}" y="${(y(v) + 3).toFixed(1)}" text-anchor="end">${v > 0 ? '+' : ''}${v}</text>`).join('');
    const anc = i => (i === 0 ? 'start' : i === fan.breaks.length - 1 ? 'end' : 'middle');
    const labels = fan.breaks.map((b, i) => `<text x="${x(i).toFixed(1)}" y="${Hh - pb + 14}" text-anchor="${anc(i)}">${b}</text><text x="${x(i).toFixed(1)}" y="${Hh - pb + 28}" text-anchor="${anc(i)}" class="dim">${esc(H.abbr)} ${Math.round(100 * fan.p_lead[i])}%</text>`).join('');
    fanSvg = `<div><h4>${esc(H.abbr)} lead at each break</h4><svg class="flow" viewBox="0 0 ${W} ${Hh}" role="img" aria-label="Home lead by break">
      <polygon class="b90" points="${band(0, 4)}"></polygon><polygon class="b50" points="${band(1, 3)}"></polygon>
      <line class="zero" x1="${pl}" x2="${W - pr}" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}"></line><path class="med" d="${med}"></path>
      ${fan.q.map((q, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(q[2]).toFixed(1)}" r="3"></circle>`).join('')}${ticks}${labels}</svg>
      <p class="note">Median lead (line), middle half (dark band) and 10–90% (light band) of the simulated games; % = chance ${esc(H.abbr)} leads at that break.</p></div>`;
  }
  const qs = ['q1', 'q2', 'q3', 'q4'].filter(k => sim.periods?.[k]);
  let qSvg = '';
  if (qs.length) {
    const W = 420, Hh = 190, pl = 30, pt = 10, pb = 34;
    const vals = qs.flatMap(k => ['away', 'home'].map(sd => sim.periods[k][sd].pts.q));
    const hi = Math.max(...vals.map(q => q[4])) + 2, lo = Math.max(0, Math.min(...vals.map(q => q[0])) - 4);
    const gw = (W - pl - 8) / qs.length, y = v => pt + (hi - v) * (Hh - pt - pb) / (hi - lo);
    const act = data.actual ? k => ({away: actualPoints(data, 'away', k), home: actualPoints(data, 'home', k)}) : null;
    const bars = qs.map((k, i) => ['away', 'home'].map((sd, j) => {
      const d = sim.periods[k][sd].pts, cx = pl + i * gw + gw * (j ? 0.62 : 0.32), a = act?.(k)?.[sd];
      return `<rect class="q-${sd}" x="${(cx - 9).toFixed(1)}" y="${y(d.mean).toFixed(1)}" width="18" height="${(y(lo) - y(d.mean)).toFixed(1)}"></rect>
        <line class="wh" x1="${cx.toFixed(1)}" x2="${cx.toFixed(1)}" y1="${y(d.q[4]).toFixed(1)}" y2="${y(d.q[0]).toFixed(1)}"></line>
        ${a != null ? `<circle class="act" cx="${cx.toFixed(1)}" cy="${y(a).toFixed(1)}" r="4"><title>${a} actual</title></circle>` : ''}
        <text x="${cx.toFixed(1)}" y="${(y(d.q[4]) - 3).toFixed(1)}" text-anchor="middle">${d.mean.toFixed(1)}</text>`;
    }).join('') + `<text x="${(pl + i * gw + gw / 2).toFixed(1)}" y="${Hh - pb + 16}" text-anchor="middle">${k.toUpperCase()}</text>`).join('');
    qSvg = `<div><h4>Points per quarter</h4><svg class="flow" viewBox="0 0 ${W} ${Hh}" role="img" aria-label="Points per quarter">${bars}</svg>
      <p class="note"><i class="lg q-away"></i> ${esc(A.abbr)} <i class="lg q-home"></i> ${esc(H.abbr)} · bar = mean, whisker = 10–90%${act ? ' · dot = actual' : ''}.</p></div>`;
  }
  return fanSvg || qSvg ? `<section class="panel"><h3 style="margin-top:0">Game flow</h3><div class="flow-grid">${fanSvg}${qSvg}</div></section>` : '';
}

function teamView(el, data, period) {
  const sim = sims(data);
  const A = team(data.game.away.id), H = team(data.game.home.id);
  const per = sim?.periods?.[period];
  const act = data.actual;
  const actual = act ? {away: actualPoints(data, 'away', period), home: actualPoints(data, 'home', period)} : null;
  const has = actual && actual.away != null && actual.home != null;
  const rows = [];
  for (const side of ['away', 'home']) {
    const info = team(data.game[side].id);
    if (sim) {
      const b = sim[side].box[period];
      rows.push(`<tr><td class="name">${logo(data.game[side].id, 'sm')} ${esc(info.abbr)} <span class="tag">proj</span></td><td><b>${f1(per[side].pts.mean)}</b></td>${heat(per[side].win)}<td>${f1(b.reb)}</td><td>${f1(b.ast)}</td><td>${f1(b.stl)}</td><td>${f1(b.blk)}</td><td>${f1(b.tov)}</td><td>${shoot(b.fgm, b.fga, true)}</td><td>${shoot(b.fg3m, b.fg3a, true)}</td><td>${shoot(b.ftm, b.fta, true)}</td></tr>`);
    }
    if (act) {
      const sum = {reb: 0, ast: 0, stl: 0, blk: 0, tov: 0, fgm: 0, fga: 0, fg3m: 0, fg3a: 0, ftm: 0, fta: 0};
      for (const r of act[side].players) { if (r.dnp) continue; const a = period === 'fg' ? r : r.periods?.[period]; if (a) for (const k in sum) sum[k] += a[k] || 0; }
      if (period === 'fg' && act[side].totals) Object.assign(sum, act[side].totals);
      const won = has ? (actual[side] > actual[side === 'home' ? 'away' : 'home'] ? 'W' : actual[side] < actual[side === 'home' ? 'away' : 'home'] ? 'L' : 'T') : '';
      rows.push(`<tr><td class="name">${logo(data.game[side].id, 'sm')} ${esc(info.abbr)} <span class="tag">actual</span></td><td><b>${actual?.[side] ?? '—'}</b></td><td class="c">${won}</td><td>${sum.reb}</td><td>${sum.ast}</td><td>${sum.stl}</td><td>${sum.blk}</td><td>${sum.tov}</td><td>${shoot(sum.fgm, sum.fga)}</td><td>${shoot(sum.fg3m, sum.fg3a)}</td><td>${shoot(sum.ftm, sum.fta)}</td></tr>`);
    }
  }
  const lines = act ? linescore(data) : '';
  const boxPanel = `<section class="panel"><h3>${esc(periodName(period))} · team box</h3>${lines}<div class="scroll"><table class="box"><thead><tr><th class="name">Team</th><th>PTS</th><th>Win</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>TOV</th><th>FG</th><th>3P</th><th>FT</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>
    ${per && period !== 'fg' ? `<p class="note">Tie in the period: ${pct(per.home.tie)}. Overtime is part of FG only.</p>` : per ? `<p class="note">Overtime in ${pct(sim.ot)} of simulations.</p>` : ''}</section>`;
  if (!per) { el.innerHTML = boxPanel; return; }
  const margins = d => [1, 3, 5, 7, 10, 15].map(k => [`${H.abbr} by ${k}+`, atLeast(d, k)]).concat([1, 3, 5, 7, 10, 15].map(k => [`${A.abbr} by ${k}+`, probWhere(d, v => v <= -k)]));
  const blocks = [
    {id: period + '-away', title: `${A.name} points`, d: per.away.pts, ladder: d => stepLadder(d), actual: has ? actual.away : null},
    {id: period + '-home', title: `${H.name} points`, d: per.home.pts, ladder: d => stepLadder(d), actual: has ? actual.home : null},
    {id: period + '-total', title: `Total points`, d: per.total, ladder: d => stepLadder(d), actual: has ? actual.away + actual.home : null},
    {id: period + '-margin', title: `Margin (${H.abbr} minus ${A.abbr})`, d: per.margin, side: true, A, H, ladder: margins, actual: has ? actual.home - actual.away : null},
  ];
  const paint = () => {
    el.innerHTML = boxPanel + flowCharts(data) + blocks.map(b => distBlock(data, b)).join('') + '<p class="note">Over = strictly more than the line. Tap a bar to move the line there.</p>'
      + (data.worlds && period === 'fg' ? '<div id="drivers"></div>' : '');
    wireBlocks(el, data, paint);
    const drivers = el.querySelector('#drivers');
    if (drivers) S.driversPanel(drivers, data);
  };
  paint();
}

function linescore(data) {
  const a = data.actual.away.linescores, h = data.actual.home.linescores, n = Math.max(a.length, h.length);
  const heads = Array.from({length: n}, (_, i) => `<th>${i < 4 ? 'Q' + (i + 1) : i === 4 ? 'OT' : 'OT' + (i - 3)}</th>`).join('');
  const row = (id, xs, total) => `<tr><td class="l">${logo(id, 'sm')} ${esc(team(id).abbr)}</td>${xs.map(x => `<td>${x}</td>`).join('')}<td><b>${total}</b></td></tr>`;
  return `<div class="scroll" style="margin:0 0 12px;max-width:520px"><table><thead><tr><th class="l">Final</th>${heads}<th>T</th></tr></thead><tbody>
    ${row(data.game.away.id, a, data.game.away.score)}${row(data.game.home.id, h, data.game.home.score)}</tbody></table></div>`;
}

// ------------------------------------------------------------------ matchup
function matchupView(el, data) {
  const c = data.comparison, a = c.away, h = c.home, lg = a.league;
  const A = team(data.game.away.id), H = team(data.game.home.id);
  const rk = (s, key) => s.ranks?.[key] ? ` <span class="tag">${s.ranks[key]}</span>` : '';
  const rows = [
    ['Record', record([a.w, a.l]), record([h.w, h.l]), ''], ['Home', record(a.home), record(h.home), ''], ['Away', record(a.away), record(h.away), ''],
    ['Last 10', record(a.last10), record(h.last10), ''], ['Streak', a.streak || '—', h.streak || '—', ''],
    ['Points', f1(a.pts), f1(h.pts), f1(lg.pts)], ['Opponent points', f1(a.opp_pts), f1(h.opp_pts), f1(lg.pts)],
    ['Offensive rating', f1(a.ortg) + rk(a, 'ortg'), f1(h.ortg) + rk(h, 'ortg'), f1(lg.ortg)],
    ['Defensive rating', f1(a.drtg) + rk(a, 'drtg'), f1(h.drtg) + rk(h, 'drtg'), f1(lg.ortg)],
    ['Net rating', signed(a.net) + rk(a, 'net'), signed(h.net) + rk(h, 'net'), '0.0'],
    ['Pace', f1(a.pace) + rk(a, 'pace'), f1(h.pace) + rk(h, 'pace'), f1(lg.pace)],
    ['Effective FG%', rate(a.efg), rate(h.efg), rate(lg.efg)], ['Opponent eFG%', rate(a.opp_efg), rate(h.opp_efg), rate(lg.efg)],
    ['Turnover rate', rate(a.tov_pct), rate(h.tov_pct), rate(lg.tov_pct)], ['Forced turnover rate', rate(a.opp_tov_pct), rate(h.opp_tov_pct), rate(lg.tov_pct)],
    ['Offensive rebound %', rate(a.oreb_pct), rate(h.oreb_pct), rate(lg.oreb_pct)], ['Defensive rebound %', rate(a.dreb_pct), rate(h.dreb_pct), rate(1 - lg.oreb_pct)],
    ['Free-throw rate', rate(a.ftr), rate(h.ftr), rate(lg.ftr)], ['Three-point attempt rate', rate(a.fg3a_rate), rate(h.fg3a_rate), rate(lg.fg3a_rate)],
    ['3P%', rate(a.fg3_pct), rate(h.fg3_pct), ''], ['FT%', rate(a.ft_pct), rate(h.ft_pct), ''], ['Assisted FG rate', rate(a.ast_rate), rate(h.ast_rate), ''],
    ...[0, 1, 2, 3].map(k => [`Q${k + 1} points`, f1(a.quarters?.[k]), f1(h.quarters?.[k]), '']),
  ];
  el.innerHTML = `<section class="panel"><div class="scroll"><table>
    <thead><tr><th class="l">Season to date</th><th>${logo(data.game.away.id, 'sm')} ${esc(A.abbr)}</th><th>${logo(data.game.home.id, 'sm')} ${esc(H.abbr)}</th><th>League</th></tr></thead>
    <tbody>${rows.map(r => `<tr><td class="l">${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td class="dim">${r[3]}</td></tr>`).join('')}</tbody></table></div>
    <p class="note">Games through ${esc(dayLabel(data.comparison_as_of))} (exclusive) · ratings per 100 possessions · small numbers are league ranks.</p></section>
    ${duelsPanel(data)}`;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const sinceLabel = iso => { const [y, m, d] = String(iso).split('-').map(Number); return `${d} ${MONTHS[m - 1]} ${y}`; };

// One player's own head-to-head (player sheet): who guarded him in earlier meetings with tonight's opponents and, once
// final, in this game; and whom he guarded (he as the defender) — from the same real-matchup rows as the Matchup view.
function guardedPanel(data, pid) {
  const d = data.duels;
  if (!d) return '';
  const mine = ['away', 'home'].map(s => (d.sides[s] || []).find(r => r.id === String(pid))).find(Boolean);
  const asDef = ['away', 'home'].flatMap(s => (d.sides[s] || []).flatMap(r => (r.past || []).filter(x => x.id === String(pid)).map(x => ({att: r.name, ...x}))))
    .sort((a, b) => b.pposs - a.pposs).slice(0, 5);
  if (!mine && !asDef.length) return '';
  const line = x => `${x.pts} pts · ${x.fgm}/${x.fga} FG${x.fg3a ? ` · ${x.fg3m}/${x.fg3a} 3P` : ''}${x.meetings > 1 ? ` · ${x.meetings} games` : ''}`;
  const rows = (list, who) => list.map(x => `<tr><td class="l name">${esc(who(x))}</td><td>${pct(x.share, 0)}</td><td class="l">${line(x)}</td></tr>`).join('');
  const table = (title, list, who, head) => list?.length ? `<h3>${title}</h3><div class="scroll"><table><thead><tr><th class="l">${head}</th><th>Share</th><th class="l">His line while guarded</th></tr></thead><tbody>${rows(list, who)}</tbody></table></div>` : '';
  return `<section class="panel" style="margin-top:12px">
    ${table('Who guarded him · this game', mine?.tonight, x => x.name, 'Defender')}
    ${table('Who guards him · earlier meetings', mine?.past, x => x.name, 'Defender')}
    ${asDef.length ? `<h3>Whom he guards · earlier meetings</h3><div class="scroll"><table><thead><tr><th class="l">Attacker</th><th>Share</th><th class="l">Attacker's line while he guarded</th></tr></thead>
      <tbody>${rows(asDef, x => x.att)}</tbody></table></div>` : ''}
    <p class="note">Real NBA matchups since ${esc(sinceLabel(d.since))}, games before this date only (meetings on any team). Share = of the attacker's partial possessions against tonight's opponents. "Whom he guards" lists attackers for whom he is one of the three main defenders.</p></section>`;
}

// Who guards whom (D32): real NBA matchups — each attacker's main defenders among tonight's opponents in earlier meetings
// (games before the date only) and, once final, in this game. Share = of his partial possessions against these players.
function duelsPanel(data) {
  const d = data.duels;
  if (!d) return '';
  const short = n => { const p = String(n || '').split(' '); return p.length > 1 ? `${p[0][0]}. ${p.slice(1).join(' ')}` : n; };
  const cell = x => x ? `<td class="l duel"><span class="name">${esc(short(x.name))}</span> <span class="tag">${pct(x.share, 0)}</span><br>
    <span class="dim">${x.pts} pts · ${x.fgm}/${x.fga} FG${x.fg3a ? ` · ${x.fg3m}/${x.fg3a} 3P` : ''}${x.meetings > 1 ? ` · ${x.meetings} g` : ''}</span></td>` : '<td class="l dim">—</td>';
  const table = (side, key) => {
    const rows = (d.sides[side] || []).filter(r => r[key]?.length);
    if (!rows.length) return '';
    const att = team(data.game[side].id), def = team(data.game[side === 'home' ? 'away' : 'home'].id);
    return `<div class="scroll"><table class="duels"><thead><tr><th class="l">${logo(data.game[side].id, 'sm')} ${esc(att.abbr)} attacker</th>
      <th class="l">Main defender (${esc(def.abbr)})</th><th class="l">2nd</th><th class="l">3rd</th></tr></thead>
      <tbody>${rows.map(r => `<tr><td class="l name">${esc(short(r.name))}</td>${[0, 1, 2].map(i => cell(r[key][i])).join('')}</tr>`).join('')}</tbody></table></div>`;
  };
  const tonight = ['away', 'home'].some(s => (d.sides[s] || []).some(r => r.tonight?.length));
  const block = (key, title, note) => {
    const body = table('away', key) + table('home', key);
    return body ? `<h3>${title}</h3>${body}<p class="note">${note}</p>` : '';
  };
  return `<section class="panel">
    ${tonight ? block('tonight', 'Who guarded whom · this game', 'Real NBA matchups: share of the attacker\'s partial possessions, his points and shots while guarded.') : ''}
    ${block('past', 'Who guards whom · earlier meetings', `Real NBA matchups between tonight's players since ${esc(sinceLabel(d.since))}, games before this date only (players' meetings on any team) · share of the attacker's partial possessions against these opponents.`)}
  </section>`;
}

// ------------------------------------------------------------------ player sheet (period-aware)
// Double, triple, quadruple and quintuple doubles: 10+ in 2–5 of points, rebounds, assists, steals and blocks, counted
// in every stored world (views; snapshot fields as the fallback). Rare ones show only when above 0.1%.
function multiRows(p, m) {
  const v = m || {double: p.double_double, triple: p.triple_double, quadruple: p.quadruple_double, quintuple: p.quintuple_double, five_by_five: p.five_by_five};
  const row = (label, x, always) => (x == null || (!always && x < 0.001) ? null : [label, pct(x, x < 0.1 ? 1 : 0)]);
  return [row('Double-double', v.double, true), row('Triple-double', v.triple, true), row('Quadruple-double', v.quadruple),
          row('Quintuple-double', v.quintuple), row('5×5', v.five_by_five, true)].filter(Boolean);
}
// A tile holding several aligned lines (owner: stack related numbers rather than spreading them over many tiles)
const stackTile = (title, rows) => `<div class="tile stack"><span>${esc(title)}</span><div class="lines">${rows.map(([k, v]) => `<em>${esc(k)}</em><b>${v}</b>`).join('')}</div></div>`;

function actualValue(r, period, key) {
  const a = actualLine(r, period);
  if (!a) return null;
  const reb = a.reb ?? ((a.oreb || 0) + (a.dreb || 0));
  if (key === 'min') return Math.round(a.sec / 60);
  if (key === 'reb') return reb;
  if (key === 'pra') return a.pts + reb + a.ast;
  if (key === 'pr') return a.pts + reb;
  if (key === 'pa') return a.pts + a.ast;
  if (key === 'ra') return reb + a.ast;
  if (key === 'stocks') return a.stl + a.blk;
  return a[key] ?? null;
}

async function sheet(view, data, pid, current) {
  const sim = sims(data);
  let side = null, p = null, actualRow = null;
  for (const s of ['away', 'home']) {
    const hit = sim?.[s].players.find(x => x.id === pid);
    if (hit) { side = s; p = hit; }
    const row = data.actual?.[s].players.find(x => x.id === pid);
    if (row) { actualRow = row; side = side || s; }
  }
  if (!p && !actualRow) throw Object.assign(new Error('This player is not in this game.'), {status: 404});
  const context = await api('player/' + pid).catch(() => null);
  if (!current()) return;
  const tid = data.game[side].id, opp = data.game[side === 'home' ? 'away' : 'home'].id;
  const name = p?.name || actualRow.name;
  const period = state.period;
  const proj = p?.periods?.[period];
  const choices = (period === 'fg' ? SHEET_FG : SHEET_PERIOD).filter(k => !proj || proj.stats?.[k]);
  if (!choices.includes(state.stat)) state.stat = 'pts';
  const key = () => `${data.game.id}|${pid}|${period}|${state.stat}`;
  const options = [['Quarters', ['q1', 'q2', 'q3', 'q4']], ['Halves', ['h1', 'h2']], ['Game', ['fg']]].map(([label, ids]) =>
    `<optgroup label="${label}">${ids.map(id => `<option value="${id}"${id === period ? ' selected' : ''}>${PERIODS.find(x => x[0] === id)[1]} · ${periodName(id)}</option>`).join('')}</optgroup>`).join('');
  const statBlock = () => {
    const d = proj.stats[state.stat];
    const act = actualValue(actualRow, period, state.stat);
    const line = state.lines.has(key()) ? halfLine(state.lines.get(key())) : defaultLine(d);
    const pOver = over(d, line);  // x.5 lines: no push
    return `<section class="panel"><div class="row" style="justify-content:space-between"><h2 style="margin:0">${esc(NAME[state.stat] || LABEL[state.stat])} · ${esc(periodName(period))}</h2>
      <span class="note" style="margin:0">mean ${f1(d.mean)} · median ${d.q[2]} · 10–90%: ${d.q[0]} to ${d.q[4]}</span></div>
      <div class="dist" style="margin-top:8px"><div>${histogram(d, {line, actual: act})}
        <div class="lineinput"><label for="line-stat">Over</label><input id="line-stat" type="number" step="1" min="0.5" value="${line}" data-line="stat">
          <output>Over: ${pct(pOver)}</output><span class="dim">Under: ${pct(1 - pOver)}</span></div>
        ${act != null ? `<p class="note">Actual: <b>${act}</b> · ${ordinal(Math.round(100 * percentileOf(d, act)))} percentile of the simulations</p>` : ''}</div>
        <div class="scroll"><table><thead><tr><th class="l">${esc(LABEL[state.stat])}</th><th>Chance</th></tr></thead><tbody>
        ${stepLadder(d).map(([label, pr]) => `<tr><td class="l">${esc(label)}</td>${heat(pr, {digits: 1})}</tr>`).join('')}</tbody></table></div></div></section>`;
  };
  const tiles = proj ? `<div class="tiles" style="margin-top:12px">
      <div class="tile"><span>Minutes</span><b>${mmss(proj.sec)}</b></div>
      <div class="tile"><span>Points</span><b>${f1(proj.mean.pts)}</b></div>
      <div class="tile"><span>Rebounds</span><b>${f1(proj.mean.reb)}</b></div>
      <div class="tile"><span>Assists</span><b>${f1(proj.mean.ast)}</b></div>
      ${stackTile('Shooting', [['FG', shoot(proj.mean.fgm, proj.mean.fga, true)], ['3P', shoot(proj.mean.fg3m, proj.mean.fg3a, true)], ['FT', shoot(proj.mean.ftm, proj.mean.fta, true)]])}
      ${stackTile('Chances', [['Plays', pct(p.played, 0)], ...(period === 'fg' ? multiRows(p, data.multi?.[pid]) : [])])}</div>
      ${p.minutes_basis ? `<p class="note">Minutes basis: healthy role ${f1(p.minutes_basis.healthy)} min${p.minutes_basis.rotation < 0.95 ? ` · plays ${pct(p.minutes_basis.rotation, 0)} of the games he is available for` : ''} · target ${f1(p.minutes_basis.target)} if the listed roster plays${p.minutes_basis.k_back > 0 && p.minutes_basis.ramp < 0.995 ? ` · game ${p.minutes_basis.k_back} back after ${p.minutes_basis.missed} missed (ramp ×${p.minutes_basis.ramp.toFixed(2)})` : ''}${p.starter ? ' · projected starter' : ''}. Team minutes are shared to exactly 240 by priority, so an absent teammate's minutes pass down the rotation.</p>` : ''}
      ${p.if_plays ? `<p class="note">If he plays (full game): ${f1(p.if_plays.min)} min · ${f1(p.if_plays.pts)} pts · ${f1(p.if_plays.reb)} reb · ${f1(p.if_plays.ast)} ast. ${esc(p.status)}${p.injury?.comment ? ' — ' + esc(p.injury.comment) : ''}</p>` : ''}`
    : `<p class="note">${p && !p.periods ? `Ruled out in every simulation (${esc(p.status)}).` : 'No projection for this player in this game.'}</p>`;
  const paint = () => {
    view.innerHTML = `<a class="crumb" href="#/game/${data.game.id}/${period}">‹ ${esc(team(data.game.away.id).abbr)} @ ${esc(team(data.game.home.id).abbr)} · ${esc(dayLabel(data.game.date))}</a>
      <section class="panel"><div class="row">${logo(tid, 'lg')}<div class="grow"><h2 style="margin:0;font-size:20px">${esc(name)}</h2>
        <p class="note" style="margin:0">${esc(team(tid).name)} · ${esc(p?.pos || actualRow?.pos || '')}${p?.jersey ? ' · #' + esc(p.jersey) : ''} · ${side === 'home' ? 'vs' : '@'} ${esc(team(opp).abbr)} ${p ? statusTag(p.status, p.availability) : ''}</p></div>
        ${sim ? `<label class="sr" for="sheet-period">Period</label><select id="sheet-period" class="period">${options}</select>` : ''}
        <a class="btn ghost" href="#/player/${pid}">Player page</a></div>${tiles}</section>
      ${proj ? `${segGroups(STAT_GROUPS.map(([g, ks]) => [g, ks.filter(([k]) => choices.includes(k))]), state.stat, 'data-stat')}<div id="stat-block">${statBlock()}</div>` : ''}
      ${proj && period === 'fg' && data.worlds ? '<div id="what-if"></div>' : ''}
      ${proj && period === 'fg' ? S.averagesPanel(data, pid, proj) : ''}
      ${period === 'fg' ? guardedPanel(data, pid) : ''}
      ${context ? contextPanel(context, period) : ''}
      <p class="note">${sim ? `${sim.sims.toLocaleString()} simulated games from the ${esc(data.projection.kind)} snapshot of ${esc(dayLabel(data.projection.snapshot))}. Distributions include simulations where he does not play${period === 'fg' ? '' : '; overtime counts in FG only'}.` : ''}</p>`;
    view.querySelector('#sheet-period')?.addEventListener('change', e => location.replace(`#/game/${data.game.id}/player/${pid}/${e.target.value}`));
    view.querySelectorAll('[data-stat]').forEach(b => b.onclick = () => { state.stat = b.dataset.stat; store.set('stat', state.stat); paint(); });
    const block = view.querySelector('#stat-block');
    const input = block?.querySelector('input[data-line]');
    if (input) input.onchange = () => { const v = Number(input.value); if (Number.isFinite(v)) { state.lines.set(key(), halfLine(Math.max(0, v))); paint(); } };
    const svg = block?.querySelector('svg.hist');
    if (svg) svg.onclick = e => { const v = e.target.closest('rect.hit')?.dataset.v; if (v != null) { state.lines.set(key(), Number(v) - 0.5); paint(); } };
    const whatIf = view.querySelector('#what-if');
    if (whatIf) {
      const d = proj.stats[state.stat];
      S.sheetPanels(whatIf, data, pid, state.stat, state.lines.has(key()) ? halfLine(state.lines.get(key())) : defaultLine(d));
    }
  };
  paint();
}

function contextPanel(context, period) {
  const q = context.quarters;
  const qi = {q1: [0], q2: [1], q3: [2], q4: [3], h1: [0, 1], h2: [2, 3], fg: [0, 1, 2, 3]}[period];
  let table = '';
  if (q) {
    const g = Math.max(1, q[0].games);
    const per = (k, i) => q[i][k] / g;
    const row = (label, idx, hl) => {
      const sum = k => idx.reduce((s, i) => s + per(k, i), 0);
      return `<tr${hl ? ' class="hl"' : ''}><td class="l">${label}</td><td>${mmss(sum('sec'))}</td><td><b>${f1(sum('pts'))}</b></td><td>${f1(sum('oreb') + sum('dreb'))}</td><td>${f1(sum('ast'))}</td><td>${f1(sum('fg3m'))}</td><td>${shoot(sum('fgm'), sum('fga'), true)}</td></tr>`;
    };
    table = `<div class="scroll" style="margin-top:12px"><table><thead><tr><th class="l">Per game</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>3PM</th><th>FG</th></tr></thead><tbody>
      ${['q1', 'q2', 'q3', 'q4'].map((id, i) => row(PERIODS[i][1], [i], qi.length === 1 && qi[0] === i)).join('')}
      ${row('1st half', [0, 1], period === 'h1')}${row('2nd half', [2, 3], period === 'h2')}${row('Regulation', [0, 1, 2, 3], period === 'fg')}</tbody></table></div>
      <p class="note">Season per-game splits from play-by-play over ${q[0].games} games (overtime excluded).</p>`;
  }
  const items = context.log.slice(-15).map(r => ({v: r.dnp ? null : r.pts, label: r.date.slice(8), title: `${r.date} ${r.home ? 'vs' : '@'} ${team(r.opp).abbr}: ${r.dnp ? (r.reason || 'DNP') : r.pts + ' pts'}`}));
  return `<section class="panel"><h3>Season by period (latest data)</h3>${table}
    ${items.length ? `<h3 style="margin-top:14px">Points by game</h3>${barChart(items)}<p class="note">Last ${items.length} team games · grey marks are games he did not play.</p>` : ''}</section>`;
}
