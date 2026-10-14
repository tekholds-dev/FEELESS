// 🔐 The signed HQ session, for surfaces OUTSIDE the HQ deck (the mini cat's 🧠 Brain): the same headers HqDeck sends, read from the session
// the creator already signed in HQ (24h). No session = no call — it never asks a wallet to sign from here, and the server still checks
// every request (owner routes answer 403 without it).
import { apiUrl, errorText } from './api';

const SESSION_KEY = 'feeless:cc-session';
export const readHqSession = addr => { try { const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); return s && s.address === addr && Date.now() / 1000 - s.ts < 86000 ? s : null; } catch { return null; } };

export function hqCallFor(address) {
  return async (path, opts = {}) => {
    const s = readHqSession(address);
    if (!s) throw new Error('Open HQ once to sign in — then the Brain works from here.');
    const res = await fetch(apiUrl(`/api/reputation${path}`), { ...opts, headers: { 'Content-Type': 'application/json', 'x-admin-address': address, 'x-admin-ts': String(s.ts), 'x-admin-sig': s.sig, ...(opts.headers || {}) } });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(errorText(body, res.status));
    return body;
  };
}
