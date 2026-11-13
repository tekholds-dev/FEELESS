import { apiUrl } from './api';
import { readChatSession } from './chatSession';

// ⚖ LEGAL-1 slice 2: the ONE check every money signing point calls right before the wallet opens (backend/legal.py holds every rule).
// The server decides per feature: sanctioned / closed country (the CDN's, else the one the wallet stated) and the 18+ / terms statement.
// One shared 60 s answer per wallet. Fail-open ONLY for a wallet that already accepted this version in this browser (server down ≠ locked
// out); a wallet that never accepted is held until it does.
// Bump ONLY when the Terms / Risk / Privacy text materially changes (every wallet is asked once again). A test keeps it = backend legal.VERSION.
export const LEGAL_VERSION = '2026-11-13';
const TTL = 60000; const WAIT_MS = 8000;
const cache = new Map();   // address → { at, p }
const DONE = 'feeless:legal-ok';   // { [address]: version } — this browser saw the server take this wallet's acceptance

export const LEGAL_FEATURES = ['site', 'swap', 'perps', 'agents', 'launch', 'games', 'brokers'];
export const LEGAL_NEEDED = 'feeless:legal-needed';

function seen() { try { return JSON.parse(localStorage.getItem(DONE) || '{}') || {}; } catch { return {}; } }
export function acceptedHere(address) { return !!address && seen()[address] === LEGAL_VERSION; }
export function markAccepted(address) {   // only a NEW acceptance drops the cached answer (a status read that already said 'accepted' stays cached)
  if (!address || acceptedHere(address)) return;
  try { localStorage.setItem(DONE, JSON.stringify({ ...seen(), [address]: LEGAL_VERSION })); } catch { /* private window: the server still knows */ }
  cache.delete(address);
}
export function forgetLegal(address) { if (address) cache.delete(address); else cache.clear(); }

// GET /legal/status with this wallet's own session (so its stated country counts). Shared by every caller for 60 s.
export function legalStatus(address, { now = Date.now, fresh = false } = {}) {
  const k = address || '';
  const hit = cache.get(k);
  if (!fresh && hit && now() - hit.at < TTL) return hit.p;
  const session = address ? readChatSession(address) : null;
  const ctl = typeof AbortController === 'function' ? new AbortController() : null; const t = ctl ? setTimeout(() => ctl.abort(), WAIT_MS) : null;   // a hung server = offline, never a trade stuck on 'signing'
  const p = fetch(apiUrl(`/api/reputation/legal/status${address ? `?wallet=${encodeURIComponent(address)}` : ''}`), { headers: session ? { 'x-feeless-session': session } : {}, ...(ctl ? { signal: ctl.signal } : {}) })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error(`legal ${r.status}`))))
    .finally(() => t && clearTimeout(t));
  cache.set(k, { at: now(), p });
  p.catch(() => cache.delete(k));
  return p;
}

// → { ok, why, needAccept }. Never throws.
export async function legalOk(feature, address, opts = {}) {
  if (!LEGAL_FEATURES.includes(feature)) return { ok: false, why: `Unknown feature "${feature}".` };
  let st;
  try { st = await legalStatus(address, opts); } catch {
    return acceptedHere(address) ? { ok: true, why: '', offline: true } : { ok: false, why: "Can't check the terms right now — try again in a moment.", offline: true };
  }
  const g = st?.gates?.[feature] || { ok: false, why: 'No answer for this feature.' };
  if (g.ok) return { ok: true, why: '' };
  const needAccept = !st?.accepted;
  return { ok: false, why: g.why || 'Not available.', needAccept };
}

// The line each signing point adds before it asks the wallet: throws a plain-words Error (their existing error toast shows it) and, when
// the wallet simply hasn't accepted yet, opens the accept window.
export async function assertLegal(feature, address, opts = {}) {
  const r = await legalOk(feature, address, opts);
  if (r.ok) return true;
  if (r.needAccept) { try { window.dispatchEvent(new CustomEvent(LEGAL_NEEDED, { detail: { feature } })); } catch { /* no window */ } }
  throw new Error(r.why);
}

// 🚪 EXITS ARE NEVER HELD (reduce-only, like the peers): selling back into SOL / USDC, closing or cancelling a perp, a Kalshi redeem, a Lend
// withdraw, a leverage close. A wallet whose country the owner closes later can always take its money out. The server applies the same rule.
export const EXIT_MINTS = ['So11111111111111111111111111111111111111112', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'];
export const PERPS_EXITS = ['decrease-position', 'create-tpsl', 'cancel-tpsl', 'update-tpsl'];   // a TP / SL only ever closes
export const isExitSwap = outputMint => EXIT_MINTS.includes(String(outputMint || ''));
export async function assertSwapLegal(address, outputMint, opts) { return isExitSwap(outputMint) ? true : assertLegal('swap', address, opts); }
