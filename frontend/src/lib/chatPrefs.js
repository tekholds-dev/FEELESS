import { useEffect, useState } from 'react';

// Per-viewer chat settings, shared by every chat on the site (kept in this browser only).
const KEY = 'feeless:chat-prefs';
export const CHAT_DEFAULTS = { filter: 'all', maxBadges: 3, showRep: true, showFee: true, size: 'normal' };
const read = () => { try { return { ...CHAT_DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || '{}') }; } catch { return CHAT_DEFAULTS; } };

export function useChatPrefs() {
  const [prefs, setPrefs] = useState(read);
  useEffect(() => {
    const sync = () => setPrefs(read());
    window.addEventListener('feeless:chat-prefs', sync);
    return () => window.removeEventListener('feeless:chat-prefs', sync);
  }, []);
  const update = patch => {
    const next = { ...read(), ...patch };
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* private mode: this tab only */ }
    setPrefs(next);
    window.dispatchEvent(new Event('feeless:chat-prefs'));
  };
  return [prefs, update];
}

// Which messages a filter keeps. `me` is the viewer's handle, for the mentions filter.
export function keepMessage(m, filter, me) {
  if (filter === 'calls') return (m.tokens || []).length > 0;
  if (filter === 'mentions') return !!me && (m.mentions || []).includes(me);
  if (filter === 'trusted') return (m.tier || 0) >= 1 || !!m.system;
  return true;
}
