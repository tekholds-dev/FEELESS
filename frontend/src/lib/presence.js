import { useEffect, useState } from 'react';
import { apiUrl } from './api';
import { readChatSession } from './chatSession';
import { sharedJson } from './sharedJson';

// 🟢 ONLINE STATUS (backend/presence.py — memory only on the server): your signed-in tab beats every minute while visible with the mode you
// picked (Online · Away · Invisible, remembered in this browser); anyone's dot reads online · away · offline (invisible reads offline).
export const PRESENCE_MODES = [['online', '🟢 Online', 'Everyone sees you online while a FEELESS tab is open'], ['away', '🌙 Away', 'Shown as away'], ['invisible', '👻 Invisible', 'Always shown offline — you still see everyone']];
const KEY = 'feeless.presence';
export const readMode = () => { try { const m = localStorage.getItem(KEY); return PRESENCE_MODES.some(([k]) => k === m) ? m : 'online'; } catch { return 'online'; } };
export function setMode(m) { try { localStorage.setItem(KEY, m); } catch { /* private mode */ } window.dispatchEvent(new Event('feeless:presence')); }

export function usePresenceBeat(address) {
  useEffect(() => {
    if (!address) return undefined;
    let t = null; let on = true;
    const beat = () => { const sess = readChatSession(address);
      if (sess && !document.hidden) fetch(apiUrl('/api/reputation/presence'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address, session: sess, mode: readMode() }) }).catch(() => {});
      if (on) t = setTimeout(beat, 60000); };
    beat(); const now = () => { clearTimeout(t); beat(); };
    window.addEventListener('feeless:presence', now); document.addEventListener('visibilitychange', now);
    return () => { on = false; clearTimeout(t); window.removeEventListener('feeless:presence', now); document.removeEventListener('visibilitychange', now); };
  }, [address]);
}

export function usePresence(addresses) {
  const key = (addresses || []).filter(Boolean).slice(0, 50).sort().join(',');
  const [m, setM] = useState({});
  useEffect(() => { if (!key) return undefined; let on = true;
    const go = () => sharedJson(`/api/reputation/presence?a=${key}`, { maxAge: 30000 }).then(d => on && d && setM(d)).catch(() => {});
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 60000); return () => { on = false; clearInterval(t); }; }, [key]);
  return m;
}
