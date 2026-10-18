import { useEffect, useState } from 'react';
import { sharedJson } from './sharedJson';

// 🐋 WHO TRADED THIS CHART — on EVERY chart (owner, 2026-10-18: "all the wallet callouts like bundlers should show for users"): the tape's
// trades tagged from our own launch + holder read (backend chart_wallets.py), one bubble per tagged trade at its time + market cap.
// ONE shared read per coin (sharedJson) every 15s while the tab is visible — many charts of one coin never ask twice.
export const WALLET_TAG = { dev: ['👤', 'DEV'], sniper: ['🎯', 'SNIPER'], bundle: ['📦', 'BUNDLE'], whale: ['🐋', 'WHALE'], top: ['👑', 'TOP TRADER'], holder: ['🏦', 'TOP HOLDER'] };
const ORDER = ['dev', 'sniper', 'bundle', 'whale', 'top', 'holder'];
const money = v => `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

/** tagged trades → chart pins; `mcPerPrice` turns a trade's price into the market cap the pin sits at (0 = no pins) */
export function walletPins(cw, mcPerPrice) {
  const r = Number(mcPerPrice);
  if (!(r > 0)) return [];
  return ((cw && cw.trades) || []).filter(t => Number(t.px) > 0 && Number(t.at) > 0).map(t => {
    const tags = t.tags || []; const k = ORDER.find(x => tags.includes(x)) || tags[0]; const [icon, word] = WALLET_TAG[k] || ['•', String(k || '').toUpperCase()];
    return { id: `w-${t.at}-${t.w}-${t.usd}`, at: t.at, cap: Number(t.px) * r, who: `${word} ${String(t.w).slice(0, 4)}…${String(t.w).slice(-4)}`, kind: 'wallet', icon,
      action: t.side === 'buy' ? 'BUY' : 'SELL', text: `${t.side === 'buy' ? 'bought' : 'sold'} ${money(t.usd)} · ${tags.map(x => (WALLET_TAG[x] || [x])[0]).join(' ')}` };
  });
}

export function useChartWallets(mint, pair) {
  const [cw, setCw] = useState(null);
  useEffect(() => {
    let alive = true; setCw(null); if (!mint) return undefined;
    const load = () => sharedJson(`/api/reputation/chart-wallets/${mint}${pair ? `?pair=${pair}` : ''}`, { maxAge: 14000 }).then(x => { if (alive && x) setCw(x); }).catch(() => {});
    load(); const id = setInterval(() => { if (!document.hidden) load(); }, 15000);
    return () => { alive = false; clearInterval(id); };
  }, [mint, pair]);
  return cw;
}
