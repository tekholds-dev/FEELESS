// 💸 THE STAKE — one amount every real-money building quotes its earnings at ($5 · $100 · $1K; owner, 2026-10-23: "pools + perps ain't bringing
// no money — show what $5 / $100 earns live"). One shared value for the page (Pool Hall rows, the combo, the Perps desk), remembered per viewer.
import { useEffect, useState } from 'react';

export const STAKES = [5, 100, 1000];
const KEY = 'feeless.earn.stake';
let cur = (() => { try { const v = Number(localStorage.getItem(KEY)); return STAKES.includes(v) ? v : 100; } catch { return 100; } })();
const subs = new Set();
export function setStake(v) {
  if (!STAKES.includes(v) || v === cur) return;
  cur = v; try { localStorage.setItem(KEY, String(v)); } catch { /* storage blocked */ }
  subs.forEach(f => f(v));
}
export function useStake() {
  const [v, setV] = useState(cur);
  useEffect(() => { subs.add(setV); setV(cur); return () => { subs.delete(setV); }; }, []);
  return v;
}
// pure: $ in a compact word that still shows cents on small stakes ($5 at 8 % APY earns $0.0011 a day)
export const cash = v => { const x = Number(v) || 0; const a = Math.abs(x); return a >= 1000 ? `$${(x / 1000).toFixed(1)}K` : a >= 10 ? `$${x.toFixed(0)}` : a >= 1 ? `$${x.toFixed(2)}` : a >= 0.01 ? `$${x.toFixed(3)}` : `$${x.toFixed(4)}`; };
