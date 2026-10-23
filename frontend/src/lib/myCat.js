// 🎨 MY CAT — the cat a user BUILT (coat · pattern · look · name) in 🎨 Build a cat. Saved in this browser only (a look, never money): the FeeCat
// shell wears it, and 🤖 New agent starts from it. `feeless:my-cat` tells every open panel when it changes.
import { useEffect, useState } from 'react';

const KEY = 'feeless.myCat';
export const DEFAULT_CAT = { coat: 0, pattern: 'stripes', look: { gear: 'none', aura: 'royal', eyes: 'classic', tag: '' }, name: '' };

export function readMyCat() {
  try { const x = JSON.parse(localStorage.getItem(KEY) || 'null'); return x && Number.isInteger(x.coat) ? { ...DEFAULT_CAT, ...x, look: { ...DEFAULT_CAT.look, ...(x.look || {}) } } : null; } catch { return null; }
}
export function saveMyCat(cat) {
  const x = { ...DEFAULT_CAT, ...cat, at: Date.now() };
  try { localStorage.setItem(KEY, JSON.stringify(x)); } catch { /* private window: it still applies for this visit */ }
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('feeless:my-cat', { detail: x }));
  return x;
}
export function useMyCat() {
  const [c, setC] = useState(readMyCat);
  useEffect(() => { const f = e => setC(e.detail || readMyCat()); window.addEventListener('feeless:my-cat', f); return () => window.removeEventListener('feeless:my-cat', f); }, []);
  return c;
}
