import { apiUrl } from './api';

// Sign once, chat for 7 days. The token lives only in this browser for this wallet.
const key = address => `feeless:chat-session:${address}`;
export function readChatSession(address) {
  const ok = s => s && s.expiresAt * 1000 > Date.now() + 60000;
  try {
    const own = JSON.parse(localStorage.getItem(key(address)) || 'null');
    if (ok(own)) return own.token;
    // A session signed by a linked account (other network) is valid too — the server checks the link.
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith('feeless:chat-session:')) { const s = JSON.parse(localStorage.getItem(k) || 'null'); if (ok(s)) return s.token; }
    }
  } catch { /* ignore */ }
  return null;
}
export function clearChatSession(address) { try { localStorage.removeItem(key(address)); } catch { /* ignore */ } }
const checked = new Map();
// One signature, reused everywhere (chat, DMs, follows, rewards, shop) for 7 days and across linked networks.
export async function getChatSession(address, signMessage) {
  const cached = readChatSession(address);
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
