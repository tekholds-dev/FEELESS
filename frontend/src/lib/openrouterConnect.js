// 🔑 Connect OpenRouter (owner 2026-11-10): one click, no key to copy or paste. OpenRouter's own sign-in (PKCE): this tab keeps a
// one-time verifier, OpenRouter's page asks the user to approve FEELESS and sends back a code, and the server swaps that code for a
// key made just for FEELESS and seals it on the agent. The key never reaches this page; the user can revoke it on OpenRouter any time.
import { apiUrl } from './api';
import { agentAuth } from './chatSession';

export const OR_AUTH = 'https://openrouter.ai/auth';
const KEY = 'feeless.orConnect';
const MAX_AGE_MS = 15 * 60 * 1000;   // an approval left open longer than this starts over

const b64url = buf => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

export async function pkcePair() {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
  const challenge = b64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)));
  return { verifier, challenge };
}

export function authUrl(challenge, back) {
  return `${OR_AUTH}?callback_url=${encodeURIComponent(back)}&code_challenge=${challenge}&code_challenge_method=S256`;
}

export async function startOpenRouterConnect(catId, loc = window.location) {
  const { verifier, challenge } = await pkcePair();
  sessionStorage.setItem(KEY, JSON.stringify({ verifier, cat: catId, at: Date.now() }));
  loc.assign(authUrl(challenge, `${loc.origin}${loc.pathname}`));
}

// On the way back: ?code=… plus this tab's verifier → the server seals the key. Runs once at start-up; a code with no verifier is ignored.
export async function finishOpenRouterConnect(loc = window.location, hist = window.history, now = Date.now()) {
  const code = new URLSearchParams(loc.search).get('code'); let s = null;
  try { s = JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch { s = null; }
  if (!code || !s?.verifier || !s.cat) return null;
  sessionStorage.removeItem(KEY);
  const u = new URL(loc.href); u.searchParams.delete('code'); hist.replaceState(null, '', `${u.pathname}${u.search}${u.hash}`);   // the code is single-use: never left in the address bar
  if (now - Number(s.at || 0) > MAX_AGE_MS) return done({ ok: false, cat: s.cat, why: 'That approval took too long. Press Connect OpenRouter again.' });
  try {
    const r = await fetch(apiUrl(`/api/cats/${s.cat}/action`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), action: 'openrouter_connect', secret: code, text: s.verifier }) });
    const j = await r.json().catch(() => ({}));
    return done(r.ok ? { ok: true, cat: s.cat, last4: (j.cat?.apiDrawer || []).find(x => x.provider === 'openrouter')?.last4 || '' } : { ok: false, cat: s.cat, why: j.detail || `HTTP ${r.status}` });
  } catch (e) { return done({ ok: false, cat: s.cat, why: e.message }); }
}

function done(out) {
  try { sessionStorage.setItem(`${KEY}.done`, JSON.stringify(out)); } catch { /* private mode: the drawer still shows the saved key */ }
  window.dispatchEvent(new CustomEvent('feeless:orConnect', { detail: out }));
  return out;
}

export function takeConnectResult(catId) {
  try { const out = JSON.parse(sessionStorage.getItem(`${KEY}.done`) || 'null'); if (out?.cat !== catId) return null; sessionStorage.removeItem(`${KEY}.done`); return out; } catch { return null; }
}
