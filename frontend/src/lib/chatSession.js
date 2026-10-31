import { apiUrl } from './api';
import { sweepable } from './cacheSweep';

// Sign once, chat for 7 days. The token lives only in this browser for this wallet.
const key = address => `feeless:chat-session:${address}`;
const SESSION_DAYS = 7; const FRESH_MS = 86400000;   // 🔒 agent controls need a sign-in from the last 24 h (the server checks the same)
const isFresh = s => s && (s.expiresAt - SESSION_DAYS * 86400) * 1000 > Date.now() - FRESH_MS + 60000;
export function readChatSession(address, ownOnly = false, fresh = false) {   // ownOnly: this wallet's own session (a real cat must be signed by the wallet it trades for) · fresh: signed in the last 24 h
  const ok = s => s && s.expiresAt * 1000 > Date.now() + 60000 && (!fresh || isFresh(s));
  try {
    const own = JSON.parse(localStorage.getItem(key(address)) || 'null');
    if (ok(own)) return own.token;
    if (ownOnly) return null;
    // A session signed by a linked account (other network) is valid too — the server checks the link.
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith('feeless:chat-session:')) { const s = JSON.parse(localStorage.getItem(k) || 'null'); if (ok(s)) return s.token; }
    }
  } catch { /* ignore */ }
  return null;
}
export function clearChatSession(address) { try { localStorage.removeItem(key(address)); } catch { /* ignore */ } }
// 🔒 Sign out = signed out here: every chat session in this browser goes, so agents fall back to their public view (owner 2026-10-30).
export function clearAllChatSessions() {
  try { Object.keys(localStorage).filter(k => k.startsWith('feeless:chat-session:')).forEach(k => localStorage.removeItem(k)); } catch { /* ignore */ }
}
// 🔒 What every agent owner call carries: the signed-in wallet's session (the server's only owner proof) + this browser's id (claims an older agent once).
export function agentBrowserId() {
  try { let v = localStorage.getItem('feeless-paper-owner'); if (!v) { v = `browser-${crypto.randomUUID()}`; localStorage.setItem('feeless-paper-owner', v); } return v; } catch { return ''; }
}
const nowWallet = () => { try { return localStorage.getItem('feeless:wallet-now') || ''; } catch { return ''; } };   // set by useWallet while a wallet is connected
export const agentAuth = () => ({ ownerId: agentBrowserId(), session: (nowWallet() && readChatSession(nowWallet(), true, true)) || readChatSession(undefined, false, true) || '' });
export const agentSignedIn = () => !!agentAuth().session;
// 🔐 a password reveal is its own fresh signature (the server checks it against the owner wallet, 2 minutes)
export const revealMessage = (catId, site, ts) => `FEELESS reveal\nagent:${catId}\nsite:${site}\nts:${ts}`;
export const agentAuthQuery = () => { const a = agentAuth(); return `ownerId=${encodeURIComponent(a.ownerId)}&session=${encodeURIComponent(a.session)}`; };
const checked = sweepable('chatSession', new Map(), { max: 20 });
// One signature, reused everywhere (chat, DMs, follows, rewards, shop) for 7 days and across linked networks.
export async function getChatSession(address, signMessage, { own = false, fresh = false } = {}) {
  const cached = readChatSession(address, own, fresh);
  if (cached) {
    if (!checked.has(cached)) checked.set(cached, fetch(apiUrl(`/api/reputation/chat/session/check?address=${address}&session=${encodeURIComponent(cached)}`)).then(r => r.json()).then(d => d.valid).catch(() => true));
    if (await checked.get(cached)) return cached;
    clearChatSession(address);
  }
  const ts = Math.floor(Date.now() / 1000);
  const signature = await signMessage(`FEELESS chat session\naddress:${address}\nts:${ts}`);
  const res = await fetch(apiUrl('/api/reputation/chat/session'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address, ts, signature }) });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || !body.token) throw new Error(body.detail || 'Could not start a chat session.');
  try { localStorage.setItem(key(address), JSON.stringify({ token: body.token, expiresAt: body.expiresAt })); } catch { /* private mode: sign per session */ }
  claimInvite(address, body.token);
  return body.token;
}

// Invite links: /?ref=<handle>. Remembered until the invitee's first signed session, then credited once.
export function captureInvite() {
  try { const m = /^\/r\/([a-z0-9]{6,12})\/?$/i.exec(window.location.pathname); const ref = m ? m[1] : new URLSearchParams(window.location.search).get('ref'); if (m) window.history.replaceState(null, '', '/'); if (ref && /^[a-z0-9_]{3,20}$|^[1-9A-HJ-NP-Za-km-z]{32,44}$/i.test(ref)) localStorage.setItem('feeless:ref', ref); } catch { /* ignore */ }
}
export function claimInvite(address, session) {
  let ref = null;
  try { ref = localStorage.getItem('feeless:ref'); } catch { return; }
  if (!ref) return;
  fetch(apiUrl('/api/reputation/referral'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address, ref, session }) })
    .then(r => { if (r.ok || r.status === 400 || r.status === 404) { try { localStorage.removeItem('feeless:ref'); } catch { /* ignore */ } } }).catch(() => {});
}
