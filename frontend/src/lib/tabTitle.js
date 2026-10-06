import { useEffect } from 'react';

// 🏷 Live browser-tab title: the open chart's market cap + price, or the real card's P&L on My cards — readable from another tab.
// A stack: the surface mounted LAST owns the title; when it unmounts the one before it (or the page's own title) comes back.
const stack = [];
let base = null;
const paint = () => { if (typeof document === 'undefined') return; if (base == null) base = document.title; const top = stack[stack.length - 1]; document.title = top && top.text ? top.text : base; };

export function useTabTitle(text) {
  useEffect(() => {
    if (!text) return undefined;
    const me = { text }; stack.push(me); paint();
    return () => { const i = stack.indexOf(me); if (i >= 0) stack.splice(i, 1); paint(); };
  }, [text]);
}

const compact = v => { const n = Number(v) || 0; return n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${n.toFixed(0)}`; };
const px = v => { const n = Number(v) || 0; return n >= 1 ? `$${n.toFixed(2)}` : n >= 0.01 ? `$${n.toFixed(4)}` : `$${n.toPrecision(3)}`; };
export const chartTitle = pair => { const s = pair?.baseToken?.symbol; if (!s || !(Number(pair.priceUsd) > 0)) return ''; return `$${s} ${Number(pair.marketCap) > 0 ? `${compact(pair.marketCap)} MC · ` : ''}${px(pair.priceUsd)}`; };
export const cardTitle = (name, pnlUsd, pnlPct) => (name && Number.isFinite(pnlUsd) ? `${pnlUsd >= 0 ? '▲ +' : '▼ −'}$${Math.abs(pnlUsd).toFixed(2)}${Number.isFinite(pnlPct) ? ` (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%)` : ''} · ${name}` : '');
