// Stored-only adapter: /api/* requests are answered from the imported bundle. Nothing is computed.
import {read, recordResponse, stored} from './pwa-storage.mjs';

const json = (value, status) => new Response(JSON.stringify(value), {status, headers: {'Content-Type': 'application/json'}});

export async function staticRequest(url) {
  try {
    const active = await read('meta', 'active');
    if (!active) return json({error: 'Import a MusNBA data bundle (Offline data & installation → Import data) to start.'}, 404);
    const base = new URL('./', location.href).pathname;
    const path = new URL(url, location.href).pathname;
    if (!path.startsWith(base)) return json({error: 'Outside the app.'}, 404);
    return recordResponse(await stored('/' + path.slice(base.length), active));
  } catch (error) {
    return json({error: error.message}, 500);
  }
}
