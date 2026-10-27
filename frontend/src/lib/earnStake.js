// 💸 THE STAKE — one amount every real-money building quotes its earnings at ($100 · $1K · $10K; owner, 2026-10-23: "pools + perps ain't bringing
// no money" → then "$5 wouldn't do shit": the smallest quote is $100, the default $1K). One shared value for the page (Pool Hall rows, the combo, the Perps desk), remembered per viewer.
import { useEffect, useState } from 'react';

export const STAKES = [100, 1000, 10000];
const KEY = 'feeless.earn.stake';
export const okStake = v => Number.isFinite(Number(v)) && Number(v) >= 1 && Number(v) <= 1e7;   // any amount $1 … $10M (owner 2026-10-27: "input for pools")
let cur = (() => { try { const v = Number(localStorage.getItem(KEY)); return okStake(v) ? v : 1000; } catch { return 1000; } })();
const subs = new Set();
export function setStake(v) {
  if (!okStake(v)) return; v = Math.round(Number(v) * 100) / 100; if (v === cur) return;
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
