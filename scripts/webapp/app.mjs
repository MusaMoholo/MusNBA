// Application glue: boot, hash routes, theme, search and the model/data panel.
import {api, esc, errorPanel, logo, meta, normalise, refreshLogos, setMeta, stamp, store, team, dayLabel} from './ui.mjs';
import * as today from './today.mjs';
import * as game from './game.mjs';
import * as league from './league.mjs';
import * as players from './players.mjs';
import * as lab from './lab.mjs';
import * as about from './about.mjs';

const VIEWS = {today, game, standings: league, teams: league, team: league, players, player: players, lab, about, season: league};
const NAV = {today: 'today', game: 'today', standings: 'standings', teams: 'teams', team: 'teams', players: 'players', player: 'players', lab: 'lab', season: 'standings'};
let token = 0;
const scrolls = new Map();
let lastHash = location.hash;

export async function boot() {
  applyTheme(new URLSearchParams(location.search).get('theme') || store.get('theme', 'auto'));
  document.getElementById('theme-toggle').onclick = () => {
    const next = {auto: 'dark', dark: 'light', light: 'auto'}[store.get('theme', 'auto')] || 'auto';
    store.set('theme', next);
    applyTheme(next);
  };
  matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => refreshLogos());
  setupSearch();
  let info;
  try {
    info = await api('meta');
  } catch (error) {
    document.getElementById('data-line').textContent = 'No data';
    document.getElementById('view').innerHTML = errorPanel(error);
    return;
  }
  setMeta(info);
  renderDataPanel(info);
  addEventListener('hashchange', route);
  route();
}

function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === 'dark' || mode === 'light') root.dataset.theme = mode;
  else delete root.dataset.theme;
  const button = document.getElementById('theme-toggle');
  button.setAttribute('aria-label', 'Theme: ' + (mode === 'auto' ? 'automatic' : mode));
  button.title = 'Theme: ' + (mode === 'auto' ? 'automatic' : mode);
  button.textContent = mode === 'dark' ? '☾' : mode === 'light' ? '☀' : '◐';
  document.querySelector('meta[name=theme-color]').content = getComputedStyle(root).getPropertyValue('--bg').trim() || '#11161d';
  refreshLogos();
}

export async function route() {
  scrolls.set(lastHash, scrollY);
  if (location.hash.startsWith('#/season')) { location.replace('#/standings/' + (location.hash.split('/')[2] || 'races')); return; }
  const hash = location.hash;
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent);
  const name = VIEWS[parts[0]] ? parts[0] : 'today';
  const rest = VIEWS[parts[0]] ? parts.slice(1) : [];
  for (const a of document.querySelectorAll('[data-nav]')) a.toggleAttribute('aria-current', a.dataset.nav === NAV[name]);
  for (const a of document.querySelectorAll('[data-nav][aria-current]')) a.setAttribute('aria-current', 'page');
  const view = document.getElementById('view');
  const mine = ++token;
  view.setAttribute('aria-busy', 'true');
  view.innerHTML = '<p class="loading" role="status">Loading view…</p>';
  try {
    await VIEWS[name].render(view, {name, rest, meta: meta(), current: () => mine === token});
  } catch (error) {
    if (mine === token) view.innerHTML = errorPanel(error);
    console.error(error);
  }
  if (mine !== token) return;
  view.removeAttribute('aria-busy');
  const saved = scrolls.get(hash);
  const sameView = hash.split('/').slice(0, 3).join('/') === lastHash.split('/').slice(0, 3).join('/');
  if (!sameView) scrollTo(0, saved ?? 0);
  lastHash = hash;
}

function renderDataPanel(info) {
  const last = info.snapshots.at(-1);
  document.getElementById('data-line').textContent =
    `Results through ${info.data.last_final ? dayLabel(info.data.last_final) : '—'} · ${info.model.kind === 'placeholder' ? 'placeholder model' : ['engine', 'preview'].includes(info.model.kind) ? `engine ${info.model.version || 'v1'}` : info.model.id}`;
  const rows = info.snapshots.slice().reverse().map(s =>
    `<tr><td class="l"><a href="#/today/${s.date}">${dayLabel(s.date)}</a></td><td class="l">${s.kind}</td><td>${s.games}</td><td class="l">${esc(stamp(s.generated))}</td><td class="l">${esc(s.model)}</td></tr>`).join('');
  document.getElementById('data-body').innerHTML = `
    <p class="note"><a href="#/about">About the model →</a></p><p class="note"><b>${esc(info.model.label)}</b>. Each game is simulated ${info.model.sims.toLocaleString()} times; the season sims every unplayed fixture ${(info.model.season_sims || info.model.sims).toLocaleString()} times. ${['engine', 'preview'].includes(info.model.kind) ? 'The possession engine plays every possession of today\'s games; it is the floor — a new model replaces it only if the backtest says it is better (PLAN.md). Past dates rebuilt after the fact use the placeholder.' : 'Placeholder model — the possession engine is the default for today\'s slate (PLAN.md).'}</p>
    <p class="note">Season ${esc(info.season)} · ${info.data.finals} of ${info.data.games} scheduled games final · collection run ${esc(info.data.collected_run)} · views built ${esc(stamp(info.built))}. Sources: ESPN and NBA Stats (retained matchups/tracking). Times in UK with ET.</p>
    <div class="scroll" style="margin-top:10px"><table><thead><tr><th class="l">Slate</th><th class="l">Kind</th><th>Games</th><th class="l">Generated</th><th class="l">Model</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="note">Pre-game timing requires a recorded completion before tip-off. Older snapshots may have unverified timing; retrospective snapshots use earlier box scores without dated injury news.</p>`;
  if (last && last.kind === 'retrospective') document.getElementById('data-line').textContent += ' · no pre-game run today';
}

// ------------------------------------------------------------------ search
function setupSearch() {
  const dialog = document.getElementById('search-dialog'), input = document.getElementById('search-input'), list = document.getElementById('search-results');
  let index = null;
  const open = async () => {
    dialog.showModal();
    input.focus();
    input.select();
    if (!index) {
      list.innerHTML = '<li class="note">Loading…</li>';
      try {
        const data = await api('players');
        index = [
          ...Object.values(meta().teams).map(t => ({kind: 'team', id: t.id, name: t.name, key: normalise(`${t.name} ${t.abbr} ${t.location}`), href: `#/team/${t.id}`, team: t.id, sub: `${t.conf} · ${t.div}`})),
          ...data.players.map(p => ({kind: 'player', id: p.id, name: p.name, key: normalise(p.name), href: `#/player/${p.id}`, team: p.team, sub: `${team(p.team).abbr} · ${p.pos || ''}`, pts: p.tot?.pts || 0})),
        ];
      } catch (error) {
        list.innerHTML = `<li class="note err">${esc(error.message)}</li>`;
        return;
      }
    }
    show();
  };
  const show = () => {
    if (!index) return;
    const q = normalise(input.value);
    const hits = q ? index.filter(x => x.key.includes(q)).sort((a, b) => (a.key.startsWith(q) ? 0 : 1) - (b.key.startsWith(q) ? 0 : 1) || (a.kind === 'team' ? -1 : 1) - (b.kind === 'team' ? -1 : 1) || (b.pts || 0) - (a.pts || 0)).slice(0, 25) : [];
    list.innerHTML = hits.map(x => `<li><a href="${x.href}">${logo(x.team, 'sm')}<span>${esc(x.name)}</span><small>${esc(x.sub)}</small></a></li>`).join('') || (q ? '<li class="note">No matches</li>' : '<li class="note">Type a player or team name</li>');
  };
  document.getElementById('search-open').onclick = open;
  document.getElementById('search-close').onclick = () => dialog.close();
  input.addEventListener('input', show);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') { const first = list.querySelector('a'); if (first) { location.hash = first.getAttribute('href'); dialog.close(); } } });
  list.addEventListener('click', e => { if (e.target.closest('a')) dialog.close(); });
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
  addEventListener('keydown', e => {
    if (e.key === '/' && !dialog.open && !/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement?.tagName)) { e.preventDefault(); open(); }
  });
}
