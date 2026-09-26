import { apiUrl } from './api';

// Sign once, chat for 7 days. The token lives only in this browser for this wallet.
const key = address => `feeless:chat-session:${address}`;
export function readChatSession(address) {
  try { const s = JSON.parse(localStorage.getItem(key(address)) || 'null'); return s && s.expiresAt * 1000 > Date.now() + 60000 ? s.token : null; } catch { return null; }
}
export function clearChatSession(address) { try { localStorage.removeItem(key(address)); } catch { /* ignore */ } }
export async function getChatSession(address, signMessage) {
  const cached = readChatSession(address);
  if (cached) return cached;
  const ts = Math.floor(Date.now() / 1000);
  const signature = await signMessage(`FEELESS chat session\naddress:${address}\nts:${ts}`);
  const res = await fetch(apiUrl('/api/reputation/chat/session'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address, ts, signature }) });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || !body.token) throw new Error(body.detail || 'Could not start a chat session.');
  try { localStorage.setItem(key(address), JSON.stringify({ token: body.token, expiresAt: body.expiresAt })); } catch { /* private mode: sign per session */ }
  return body.token;
}
