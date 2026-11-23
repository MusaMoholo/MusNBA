// Today: the slate for one ET game date, each game a card that opens Game Centre.
import {playerFace, playerLabel, modelPill, api, esc, etToday, f1, forecastTiming, logo, longDay, pct, record, stamp, team, tipTimes, dayLabel} from './ui.mjs';
import {slateSpotlight} from './spotlight.mjs';

// Card surname with its suffix ("Michael Porter Jr." → "Porter Jr."): the last word that is not a suffix, then the suffixes.
const SUFFIX = /^(jr\.?|sr\.?|ii|iii|iv|v)$/i;
const surname = name => {
  const w = String(name || '').split(' ').filter(Boolean), tail = [];
  while (w.length > 1 && SUFFIX.test(w[w.length - 1])) tail.unshift(w.pop());
  return [w[w.length - 1] || '', ...tail].join(' ');
};

export function defaultDay(meta) {
  const day = etToday();
  if (day < meta.first_date) return meta.first_date;
  if (day > meta.last_date) return meta.last_date;
  return day;
}

function neighbour(meta, day, direction) {
  const dates = Object.keys(meta.dates).filter(d => meta.dates[d] > 0).sort();
  if (direction < 0) return dates.filter(d => d < day).at(-1) || null;
  return dates.find(d => d > day) || null;
}

export async function render(view, {rest, meta, current}) {
  const day = /^\d{4}-\d{2}-\d{2}$/.test(rest[0] || '') ? rest[0] : defaultDay(meta);
  let slate;
  try {
    slate = await api('slate/' + day);
  } catch (error) {
    if (error.status !== 404) throw error;
    slate = {date: day, games: [], snapshot: null};
  }
  if (!current()) return;
  const prev = neighbour(meta, day, -1), next = neighbour(meta, day, 1), todayEt = defaultDay(meta);
  const games = slate.games;
  const firstTip = games.find(g => g.time_valid);
  view.innerHTML = `
    <section class="panel daybar">
      <div>
        <h2>${esc(longDay(day))}${day === etToday() ? ' <span class="pill accent">Today</span>' : ''}</h2>
        <p class="note">${games.length ? `${games.length} game${games.length > 1 ? 's' : ''}${firstTip ? ` · first tip ${esc(tipTimes(firstTip.tip_utc, day).label)}` : ''}` : 'No games scheduled'}</p>
      </div>
      <div class="daynav">
        <button class="ghost" data-go="${prev || ''}" ${prev ? '' : 'disabled'} aria-label="Previous game day">‹</button>
        <input type="date" aria-label="Choose date" value="${day}" min="${meta.first_date}" max="${meta.last_date}">
        <button class="ghost" data-go="${next || ''}" ${next ? '' : 'disabled'} aria-label="Next game day">›</button>
        ${day !== todayEt ? `<button class="ghost" data-go="${todayEt}">Today</button>` : ''}
      </div>
    </section>
    ${modelNote(slate)}
    ${games.length ? `<div class="row section-heading"><h2 class="section-title">Games · ${games.length}</h2>
      ${slate.spotlight ? '<button class="ghost" data-insights>Slate insights ↓</button>' : ''}</div>` : ''}
    <div class="games">${games.map(g => card(g, slate.watch?.closest?.game_id)).join('')}</div>
    ${slateStrip(games, day)}
    ${slate.completed_at ? review(slate.review) : ''}
    ${slate.spotlight ? `<div class="games spot-grid" id="slate-insights">${slateSpotlight(slate.spotlight, slate.watch, slate.roles)}</div>` : ''}`;
  view.querySelectorAll('[data-go]').forEach(b => b.onclick = () => { if (b.dataset.go) location.hash = '#/today/' + b.dataset.go; });
  view.querySelector('input[type=date]').onchange = e => { if (e.target.value) location.hash = '#/today/' + e.target.value; };
  view.querySelector('[data-insights]')?.addEventListener('click', () => view.querySelector('#slate-insights').scrollIntoView({behavior: 'smooth'}));
}

// U1: slate header strip — tiles (games, projected points per game, tightest projected margin, first and last tip) and a tip-time
// timeline on a UK clock axis, each game a marker (stacked when tips coincide)
function slateStrip(games, day) {
  const timed = games.filter(g => g.time_valid);
  if (games.length < 2 || !timed.length) return '';
  const pr = games.filter(g => g.proj);
  const ukHM = d => new Intl.DateTimeFormat('en-GB', {timeZone: 'Europe/London', hour: '2-digit', minute: '2-digit'}).format(d);
  const tips = timed.map(g => new Date(g.tip_utc).getTime());
  const t0 = Math.min(...tips), t1 = Math.max(...tips), span = Math.max(t1 - t0, 3600e3);
  const tight = pr.length ? pr.reduce((a, g) => (Math.abs(g.proj.margin_mean) < Math.abs(a.proj.margin_mean) ? g : a)) : null;
  const tiles = [
    ['Games', String(games.length)],
    ['Projected points per game', pr.length ? f1(pr.reduce((a, g) => a + g.proj.total, 0) / pr.length) : '—'],
    ['Tightest projected margin', tight ? `${esc(team(tight.away.id).abbr)} @ ${esc(team(tight.home.id).abbr)} · ${f1(Math.abs(tight.proj.margin_mean))}` : '—'],
    ['First / last tip (UK)', `${ukHM(new Date(t0))} – ${ukHM(new Date(t1))}`],
  ].map(([l, v]) => `<div class="tile"><span>${l}</span><b>${v}</b></div>`).join('');
  const rows = {};
  const marks = timed.slice().sort((a, b) => a.tip_utc.localeCompare(b.tip_utc)).map(g => {
    const x = 4 + 92 * (new Date(g.tip_utc).getTime() - t0) / span;
    const key = Math.round(x / 9);
    const row = rows[key] = (rows[key] ?? -1) + 1;
    return `<a class="tl-mark" href="#/game/${g.id}" style="left:${x.toFixed(1)}%;top:${4 + row * 26}px" title="${esc(team(g.away.id).name)} at ${esc(team(g.home.id).name)} · ${ukHM(new Date(g.tip_utc))} UK">${logo(g.away.id, 'sm')}${logo(g.home.id, 'sm')}</a>`;
  });
  const depth = Math.max(0, ...Object.values(rows)) + 1;
  const hours = [];
  for (let t = Math.ceil(t0 / 3600e3) * 3600e3; t <= t0 + span; t += 3600e3) hours.push(`<span class="tl-hour" style="left:${(4 + 92 * (t - t0) / span).toFixed(1)}%">${ukHM(new Date(t))}</span>`);
  return `<section class="panel slate-strip"><div class="tiles">${tiles}</div>
    <div class="timeline" style="height:${depth * 26 + 26}px" aria-label="Tip times (UK)">${marks.join('')}<div class="tl-axis" style="top:${depth * 26 + 6}px"></div>${hours.map(h => h.replace('class="tl-hour"', `class="tl-hour" data-top="${depth * 26 + 8}"`)).join('')}</div></section>`;
}

// U4: "How we did" — finished games with a pre-game projection: favourites, win-chance scores, total/margin errors and the
// players furthest from their own projected points distribution
function review(r) {
  if (!r) return '';
  const who = p => `<a class="rv-p" href="#/game/${p.game_id}/player/${p.id}">${playerFace(p.id, p.name)}<span>${esc(p.name)}</span><b>${p.actual}</b><small>proj ${f1(p.proj)} · ${Math.round(100 * p.pct)}th pct</small></a>`;
  const tiles = [['Favourites won', `${r.fav_won} of ${r.games}`], ['Win % Brier · log loss', `${r.brier.toFixed(3)} · ${r.log_loss.toFixed(3)}`],
    ['Total error (avg · bias)', `${f1(r.total_mae)} · ${r.total_bias > 0 ? '+' : ''}${f1(r.total_bias)}`], ['Margin error (avg)', f1(r.margin_mae)],
    ['Players inside 10–90%', `${Math.round(100 * r.in_range_share)}% of ${r.players}`]].map(([l, v]) => `<div class="tile"><span>${l}</span><b>${v}</b></div>`).join('');
  return `<section class="panel review"><h3 style="margin-top:0">How the projections did</h3><div class="tiles">${tiles}</div>
    <div class="rv-cols"><div><span class="spot-kicker">Beat their projection</span>${r.overs.map(who).join('')}</div>
      <div><span class="spot-kicker">Fell short</span>${r.unders.map(who).join('')}</div></div>
    <p class="note">Pre-game projections only. Brier 0.25 = coin flip; a calibrated model has ~80% of player lines inside its 10–90% range. Percentile = where the actual points fell in his simulated games.</p></section>`;
}

function modelNote(slate) {
  if (slate.snapshot) {
    const kind = slate.kind === 'prospective' ? '<span class="pill">Prospective snapshot</span>' : '<span class="pill warn" title="Rebuilt after the fact from box scores before this date; no injury news">Retrospective</span>';
    const timing = slate.completed_at ? `snapshot updated ${esc(stamp(slate.completed_at))}` : `snapshot started ${esc(stamp(slate.generated))} · completion unverified`;
    return `<div class="model-note">${modelPill(slate.model)}${kind}<span>${slate.model.sims.toLocaleString()} ${(slate.games || []).some(g => g.proj?.lineup_branches > 1) ? 'worlds per lineup branch; Expected uses all branches' : 'sims per game'} · ${timing} · game forecast times may differ</span></div>`;
  }
  if (slate.games.some(g => g.team_model)) return '<div class="model-note"><span class="pill">Team-strength estimate only</span><span>Game sims run on the morning of each slate.</span></div>';
  if (slate.games.length) return '<div class="model-note"><span class="pill">No projection retained for this date</span></div>';
  return '';
}

function card(g, closestId) {
  const final = g.status === 'final', live = g.status === 'live';
  const pr = g.proj, tm = g.team_model;
  const pA = pr ? pr.p_away : tm ? 1 - tm.p_home : null, pH = pr ? pr.p_home : tm ? tm.p_home : null;
  const t = tipTimes(g.tip_utc, g.date, g.time_valid);
  const scored = (final || live) && g.away.score != null;
  const winner = final ? (g.home.score > g.away.score ? 'home' : 'away') : null;
  const side = (key, p, proj) => {
    const s = g[key], info = team(s.id);
    const cls = winner ? (winner === key ? 'won' : 'lost') : '';
    const pts = scored ? s.score : proj != null ? f1(proj) : '';
    return `<div class="side ${cls}">${logo(s.id)}<span class="nm">${esc(info.short)}<small>${record(s.record)}</small></span><span class="p">${p != null ? pct(p, 0) : ''}</span><span class="pts${scored ? '' : ' proj'}">${pts}</span></div>`;
  };
  const muA = pr ? pr.mu_away : tm?.mu_away, muH = pr ? pr.mu_home : tm?.mu_home;
  let foot;
  if (final) {
    const fav = pr ? (pr.p_home >= pr.p_away ? 'home' : 'away') : null;
    foot = `<span>Final${g.periods > 4 ? (g.periods > 5 ? `/${g.periods - 4}OT` : '/OT') : ''}</span>` +
      (pr ? `<span>${forecastTiming(pr.kind, pr.pre_tip, pr.completed_at)}: ${esc(team(g[fav].id).abbr)} ${pct(Math.max(pr.p_home, pr.p_away), 0)} ${fav === winner ? '<span class="up" title="Favourite won">✓</span>' : '<span class="down" title="Underdog won">✗</span>'}</span><span>Proj total ${f1(pr.total)} · actual ${g.home.score + g.away.score}</span>` : '<span>No pre-game projection retained</span>');
  } else if (pr) {
    const m = pr.margin_mean ?? pr.margin_median, fav = m >= 0 ? g.home : g.away;
    foot = `<span>Total ${f1(pr.total)}</span><span>${Math.abs(m) < 0.05 ? 'PK' : `${esc(team(fav.id).abbr)} −${Math.abs(m).toFixed(1)}`}</span><span>OT ${pct(pr.ot, 0)}</span>`;
  } else if (tm) foot = `<span>${tm.source === 'pathway' ? 'Regulation points · ' : ''}Team-strength estimate</span>`;
  else foot = '<span>No projection</span>';
  const right = live ? `<span class="pill bad">${esc(g.detail)}</span>` : final ? '' :
    `${g.id === closestId ? '<span class="pill accent" title="Highest chance of a finish within 5 on this slate">Closest</span> ' : ''}${esc(g.tv[0] || '')}`;
  const rep = pr?.report && !final ? ['away', 'home'].map(k => {
    const r = pr.report[k], ab = esc(team(g[k].id).abbr), bits = [];
    if (r.out.length) bits.push(`<span class="down" title="${esc(r.out.join(', '))}">out ${r.out.length}</span>`);
    if (r.maybe.length) bits.push(`<span title="${esc(r.maybe.join(', '))}">maybe ${r.maybe.length}</span>`);
    return bits.length ? `<span><b>${ab}</b> ${bits.join(' · ')}</span>` : '';
  }).filter(Boolean).join('') : '';
  return `<a class="game-card" href="#/game/${g.id}" aria-label="${esc(team(g.away.id).name)} at ${esc(team(g.home.id).name)}">
    <div class="when"><span>${esc(t.label)}</span><span>${right}</span></div>
    ${side('away', pA, muA)}${side('home', pH, muH)}
    ${pA != null ? `<div class="winbar" aria-hidden="true"><i class="a" style="width:${(100 * pA).toFixed(1)}%"></i><i class="h" style="width:${(100 * pH).toFixed(1)}%"></i></div>` : ''}
    ${pr?.leaders && !final ? `<div class="leaders">${['away', 'home'].map(k => (pr.leaders[k] || []).map(l => `<span><b>${esc(surname(l.name))}</b> ${f1(l.pts)} pts · ${f1(l.reb)} reb · ${f1(l.ast)} ast</span>`).join('')).join('')}</div>` : ''}
    ${pr?.duel && !final ? (() => { const last = k => esc(surname(pr.leaders[k][0].name)); return `<div class="duel-line" title="Chance each top scorer outscores the other, over the engine's simulated games">Duel: <b>${last('away')}</b> outscores ${pct(pr.duel.p_a, 0)} · <b>${last('home')}</b> ${pct(pr.duel.p_b, 0)} · level ${pct(pr.duel.p_level, 0)}</div>`; })() : ''}
    ${rep ? `<div class="report-line" title="Injury report as the simulations used it (hover for names)">Report: ${rep}</div>` : ''}
    <div class="foot">${foot}</div></a>`;
}

export {dayLabel};
