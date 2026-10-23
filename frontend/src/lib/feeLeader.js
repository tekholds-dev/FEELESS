// 🐱 FEE, LIVE — one shared read for every FeeCat surface (the shell chip, the stage, her desk, her brain, the lore): `/api/cats/leader/profile`
// and `/api/cats/leader` (her last scan + rules), each fetched once per 15 s for the whole page no matter how many panels show them
// (CLAUDE.md › Speed: shared pollers, never one per card). Paused while the tab is hidden.
import { useEffect, useState } from 'react';
import { sharedJson } from './sharedJson';

function poller(path, every) {
  let last = null; let timer = null; const subs = new Set();
  const tick = () => {
    if (typeof document !== 'undefined' && document.hidden) { timer = setTimeout(tick, every); return; }
    sharedJson(path, { maxAge: every - 500 }).then(d => { if (d) { last = d; subs.forEach(f => f(d)); } }).catch(() => {})
      .finally(() => { if (subs.size) timer = setTimeout(tick, every); else timer = null; });
  };
  return function useIt(on = true) {
    const [d, setD] = useState(last);
    useEffect(() => {
      if (!on) return undefined;
      subs.add(setD); if (last) setD(last);
      if (!timer) tick();
      return () => { subs.delete(setD); if (!subs.size && timer) { clearTimeout(timer); timer = null; } };
    }, [on]);
    return d;
  };
}

export const useLeaderProfile = poller('/api/cats/leader/profile', 15000);   // { cat, discipline, stats, trades, exits, learning, rules }
export const useLeaderScan = poller('/api/cats/leader', 15000);              // { cat, scan, rules }

// pure: Fee's headline numbers from her profile (one place, so every panel agrees)
export function feeHeadline(p) {
  const c = p?.cat || {}; const d = p?.discipline || {}; const s = p?.stats || {};
  const start = Number(c.startingBalanceSol) || 25; const bal = Number(c.balanceSol ?? start); const real = Number(c.realizedPnlSol) || 0;
  return { start, bal, real, roi: s.roiPct ?? 0, trades: s.trades || 0, wr: c.winRate ?? null, open: (c.positions || []).length, lives: d.lives ?? 9, maxLives: d.maxLives || 9,
    nap: !!(d.pause || c.status === 'paused'), size: d.sizeMult ?? null, why: d.why || '', best: s.best ?? null, worst: s.worst ?? null };
}
