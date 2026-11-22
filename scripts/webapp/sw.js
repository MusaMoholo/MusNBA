import {recordResponse, stored} from './assets/pwa-storage.mjs';
const BASE = new URL('./', self.location.href).pathname;
const PREFIX = 'musnba-shell-' + encodeURIComponent(BASE) + '-';
const CACHE = PREFIX + '__SHELL_VERSION__';
const MODULES = ['app', 'ui', 'today', 'game', 'league', 'players', 'lab', 'season', 'about', 'spotlight', 'outcomes', 'scenario', 'pwa', 'pwa-storage', 'static-api', 'weighted-worlds'];
const FILES = ['', 'index.html', 'manifest.webmanifest', 'icon.svg', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png',
               ...MODULES.map(n => 'assets/' + n + '.mjs')].map(path => BASE + path);
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache =>
  cache.addAll(FILES.map(path => new Request(path, {cache: 'reload'}))))));
self.addEventListener('activate', event => event.waitUntil((async () => {
  for (const name of await caches.keys()) if (name.startsWith(PREFIX) && name !== CACHE) await caches.delete(name);
  await self.clients.claim();
})()));
self.addEventListener('message', event => { if (event.data?.type === 'ACTIVATE') self.skipWaiting(); });
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) return;
  const local = '/' + url.pathname.slice(BASE.length);
  if (/^\/(logos\/\d+(-dark)?\.png|api\/.+)$/.test(local)) { event.respondWith(stored(local).then(recordResponse)); return; }
  if (event.request.mode === 'navigate') { event.respondWith(caches.open(CACHE).then(c => c.match(BASE + 'index.html')).then(r => r || fetch(event.request))); return; }
  if (FILES.includes(url.pathname)) event.respondWith(caches.open(CACHE).then(async cache => await cache.match(url.pathname) || fetch(event.request)));
});
