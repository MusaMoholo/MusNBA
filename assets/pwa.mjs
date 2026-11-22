// Static (GitHub Pages) runtime: data comes from an imported bundle, the shell from the service worker.
import {cleanupInterruptedImport, importBundle, read} from './pwa-storage.mjs';
import {staticRequest} from './static-api.mjs';

export async function start(boot) {
  window.MUSNBA_STATIC = true;
  const base = new URL('../', import.meta.url).pathname;
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, options) => {
    const u = new URL(typeof input === 'string' ? input : input.url, location.href);
    return u.origin === location.origin && u.pathname.startsWith(base + 'api/') ? staticRequest(u.href) : originalFetch(input, options);
  };
  const panel = document.createElement('details');
  panel.className = 'panel data';
  panel.id = 'offline-panel';
  panel.innerHTML = `<summary>Offline data &amp; installation</summary>
    <div class="row"><div class="grow"><strong>Your simulations, on this device</strong><p id="pwa-status" class="note" role="status" aria-live="polite">Checking saved data…</p></div><button id="pwa-import">Import data</button></div>
    <input id="pwa-file" type="file" accept=".gz,.musnba,application/gzip,application/octet-stream" hidden>
    <progress id="pwa-progress" aria-label="Importing data" hidden style="width:100%"></progress>
    <p id="pwa-error" class="note err" role="alert" hidden></p>
    <details><summary class="note" style="cursor:pointer">Install &amp; updates</summary>
      <p class="note">iPhone: open this address in Safari, tap Share → Add to Home Screen, open MusNBA from its icon and import your data there (Safari and the installed app keep separate storage).</p>
      <p class="note">After the nightly run on your Mac, import the latest MusNBA.musnba.gz from Files → iCloud Drive → MusNBA. Imported data stays on this device and is never uploaded; keep the file as a backup.</p>
      <p id="pwa-offline" class="note" role="status">Preparing offline app…</p><button id="pwa-update" class="ghost" hidden>Update app</button></details>`;
  document.querySelector('.mainnav').after(panel);
  const input = panel.querySelector('#pwa-file'), button = panel.querySelector('#pwa-import'), status = panel.querySelector('#pwa-status'),
        error = panel.querySelector('#pwa-error'), progress = panel.querySelector('#pwa-progress');
  button.disabled = true;
  button.onclick = () => input.click();
  let importing = false, wake;
  const keepAwake = async () => { if (importing && document.visibilityState === 'visible') try { wake = await navigator.wakeLock?.request('screen'); } catch { /* optional */ } };
  document.addEventListener('visibilitychange', keepAwake);
  input.onchange = async () => {
    const file = input.files?.[0];
    if (!file) return;
    button.disabled = true; importing = true; await keepAwake();
    error.hidden = true; progress.hidden = false;
    status.textContent = 'Importing… keep MusNBA open and the screen unlocked until this finishes.';
    try {
      const result = await importBundle(file, ({count, savedMegabytes, added, reused}) => {
        status.textContent = `Importing… ${count.toLocaleString()} checked · ${added.toLocaleString()} new · ${reused.toLocaleString()} reused · ${savedMegabytes.toFixed(1)} MB added.`;
      });
      await navigator.storage?.persist?.().catch(() => false);
      status.textContent = `Imported data through ${result.latest}. Opening…`;
      location.reload();
    } catch (e) {
      error.textContent = e.name === 'QuotaExceededError' ? 'Not enough device storage. Your previous import is unchanged.' : `${e.message} (${e.name || 'Error'}). Any previous import is unchanged.`;
      error.hidden = false; status.textContent = 'Import failed. Any previous data is still available.';
      button.disabled = false; progress.hidden = true; input.value = '';
    } finally {
      importing = false; await wake?.release().catch(() => {}); wake = null;
    }
  };
  addEventListener('beforeunload', e => { if (importing) { e.preventDefault(); e.returnValue = ''; } });
  await cleanupInterruptedImport().catch(() => {});
  try {
    const active = await read('meta', 'active');
    if (active) {
      const info = await read('meta', active);
      status.textContent = `Saved data through ${info.latest} · ${info.snapshots.length} simulated slates · works offline`;
      button.textContent = 'Import latest data';
      await boot();
    } else {
      panel.open = true; panel.querySelector('details').open = true;
      status.textContent = 'Import your MusNBA.musnba.gz bundle from Files → iCloud Drive to open the app.';
      document.getElementById('view').innerHTML = '<section class="panel"><h2>Welcome to MusNBA</h2><p class="note">This installed app shows simulations computed on your Mac. Import the data bundle above to begin.</p></section>';
      document.getElementById('data-line').textContent = 'No data imported yet';
    }
  } catch (e) {
    status.textContent = 'Device storage is unavailable.'; error.hidden = false; error.textContent = e.message;
  }
  button.disabled = false;
  const offline = panel.querySelector('#pwa-offline');
  if (!('serviceWorker' in navigator)) { offline.textContent = 'Offline installation needs a supported browser over HTTPS.'; return; }
  try {
    const registration = await navigator.serviceWorker.register(new URL('../sw.js', import.meta.url), {type: 'module', updateViaCache: 'none'});
    await navigator.serviceWorker.ready;
    offline.textContent = 'App saved for offline use. Data is saved when you import it.';
    const offer = () => {
      if (!registration.waiting) return;
      panel.querySelector('summary').textContent = 'App update available · Offline data & installation';
      const update = panel.querySelector('#pwa-update');
      update.hidden = false;
      update.onclick = () => { if (!importing) registration.waiting.postMessage({type: 'ACTIVATE'}); };
    };
    offer();
    registration.addEventListener('updatefound', () => { const worker = registration.installing; worker?.addEventListener('statechange', () => { if (worker.state === 'installed') offer(); }); });
    let changing = Boolean(navigator.serviceWorker.controller);
    navigator.serviceWorker.addEventListener('controllerchange', () => { if (changing) location.reload(); changing = true; });
  } catch (e) {
    offline.textContent = 'Offline setup failed: ' + e.message + '. Keep a connection and reload.';
    offline.setAttribute('role', 'alert');
  }
}
