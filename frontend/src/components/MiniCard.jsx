import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import '../styles/miniChart.css';
import '../styles/miniCard.css';

const MiniCardBody = React.lazy(() => import('./MiniCardBody'));   // the card + its chart load only when a mini card is open
const KEY = 'feeless.miniCard';
const SIZES = ['s', 'm', 'l']; const SZ_CLASS = { s: 'sz-s', m: 'sz-m', l: 'sz-l' }; const SZ_NAME = { s: 'small', m: 'medium', l: 'large' };
const read = () => { try { const v = JSON.parse(window.localStorage.getItem(KEY) || 'null'); return v?.src?.kind ? v : null; } catch { return null; } };
const write = v => { try { if (v) window.localStorage.setItem(KEY, JSON.stringify(v)); else window.localStorage.removeItem(KEY); } catch { /* private window: lasts for this visit */ } };
const slim = r => ({ id: r.id, name: r.name, closed: !!r.closed, costUsd: r.costUsd, valueUsd: r.valueUsd, realizedUsd: r.realizedUsd, pnlUsd: r.pnlUsd, pnlPct: r.pnlPct, baseUsd: r.baseUsd, extraUsd: r.extraUsd,
  legs: (r.legs || []).map(l => ({ pairAddress: l.pairAddress, symbol: l.symbol, role: l.role, mint: l.mint || l.baseAddress || '', usd: l.usd, tokens: l.tokens, valueUsd: l.valueUsd, pnlUsd: l.pnlUsd, pnlPct: l.pnlPct,
    realizedUsd: l.realizedUsd, soldUsd: l.soldUsd, priceNow: l.priceNow, sig: l.sig })) });

// 📌 MINI CARD: openMiniCard(src) from any Fuse card → the card floats on EVERY page like the mini chart. Two sides: 🃏 the card
// itself (still flips to its live money) ⇄ 📈 the chart of any of its coins with the card's entry / stop / lock; three sizes.
// src = { kind: 'prime', tpl, name } (a tier card: always the live one) or { kind: 'row', row, name, aura } (a card you hold).
export const openMiniCard = src => { if (!src?.kind) return;
  const s = src.kind === 'row' ? (src.row?.legs?.length ? { kind: 'row', row: slim(src.row), name: src.name || src.row.name || 'My Fuse', aura: src.aura || '' } : null) : src.tpl ? { kind: 'prime', tpl: src.tpl, name: src.name || 'Fuse card' } : null;
  if (s) window.dispatchEvent(new CustomEvent('feeless:mini-card', { detail: s })); };

export function MiniCardHost() {
  const [st, setSt] = useState(read);   // { src, pos, size, side, tf }
  const drag = useRef(null);
  useEffect(() => { const on = e => setSt(o => ({ pos: o?.pos || null, size: o?.size || 'm', tf: o?.tf || '5m', side: 'card', src: e.detail })); window.addEventListener('feeless:mini-card', on); return () => window.removeEventListener('feeless:mini-card', on); }, []);
  useEffect(() => { write(st); }, [st]);
  if (!st) return null;
  const { src, pos } = st; const size = SIZES.includes(st.size) ? st.size : 'm'; const side = st.side === 'chart' ? 'chart' : 'card'; const set = p => setSt(o => (o ? { ...o, ...p } : o));
  const down = e => { if (e.target.closest('button, a')) return; const r = e.currentTarget.parentElement.getBoundingClientRect(); drag.current = { dx: e.clientX - r.left, dy: e.clientY - r.top }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const move = e => { if (!drag.current) return; set({ pos: { x: Math.max(4, Math.min(window.innerWidth - 120, e.clientX - drag.current.dx)), y: Math.max(4, Math.min(window.innerHeight - 60, e.clientY - drag.current.dy)) } }); };
  const up = () => { drag.current = null; };
  return createPortal(<aside className={`mch mcd ${SZ_CLASS[size]}`} style={pos ? { left: pos.x, top: pos.y, bottom: 'auto' } : undefined} data-testid="mini-card" aria-label={`Mini card ${src.name}`}>
    <i className="mch-edge" aria-hidden />
    <header className="mch-head" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} data-tip="Drag to move">
      <b className="mcd-name">{src.name}</b>
      <span className="mch-acts">
        <button type="button" className={side === 'card' ? 'active' : ''} onClick={() => set({ side: 'card' })} aria-pressed={side === 'card'} data-testid="mcd-side-card" data-tip="The card (tap ⟲ on it for its live money)">🃏</button>
        <button type="button" className={side === 'chart' ? 'active' : ''} onClick={() => set({ side: 'chart' })} aria-pressed={side === 'chart'} data-testid="mcd-side-chart" data-tip="Flip to the chart of its coins, with the card's entry, stop and lock">📈</button>
        <button type="button" onClick={() => set({ size: SIZES[(SIZES.indexOf(size) + 1) % SIZES.length] })} data-testid="mcd-size" data-tip={`Size: ${SZ_NAME[size]} — tap to change`} aria-label={`Size ${SZ_NAME[size]}, change`}>⤢</button>
        <button type="button" onClick={() => setSt(null)} data-testid="mcd-close" aria-label="Close mini card">×</button></span>
    </header>
    <div className="mch-body mcd-body"><React.Suspense fallback={<p className="m-dim mch-wait">Loading card…</p>}>
      <MiniCardBody src={src} side={side} size={size} tf={st.tf || '5m'} setTf={tf => set({ tf })} /></React.Suspense></div>
  </aside>, document.body);
}
