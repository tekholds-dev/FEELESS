import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { useWallet } from '../hooks/useWallet';
import { Glyph } from './Glyph';
import { getChatSession } from '../lib/chatSession';

const post = (url, body) => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(async r => { const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'Failed'); return b; });

// Spend earned points.
export function PointsShop({ address }) {
  const { wallet, signMessage } = useWallet() || {};
  const [d, setD] = useState(null);
  const load = () => fetch(`/api/reputation/shop?address=${address}`).then(r => r.json()).then(setD).catch(() => {});
  useEffect(() => { load(); }, [address]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!d?.items || !d?.unlocks) return null;
  const bal = d.points - d.spent;
  const buy = async it => { try { const session = await getChatSession(wallet.address, signMessage); const r = await post('/api/reputation/shop/buy', { address: wallet.address, session, item: it.id }); toast.success(`Unlocked ${it.label} · ${r.balance} pts left`); load(); } catch (e) { toast.error(e.message); } };
  return <section className="wp-card shop-card" data-testid="points-shop">
    <div className="wpj-head"><h3><Glyph name="bag" tone="gold" /> Points shop</h3><span className="wpj-count"><b>{bal.toLocaleString()}</b> to spend</span></div>
    <div className="shop-grid">{d.items.map(it => { const owned = Object.keys(d.unlocks).some(k => it.grant.badge ? k === `badge:${it.grant.badge}` : Object.entries(it.grant).some(([a, b]) => k === `${a}:${b}`)); return <div key={it.id} className={`shop-item ${owned ? 'owned' : ''}`}><b>{it.label}</b><span>{it.cost} pts</span><button type="button" className={bal >= it.cost ? 'btn-primary' : 'btn-outline'} disabled={bal < it.cost} onClick={() => buy(it)} data-tip={it.kind === 'mp' ? 'Your points power your family: 1 point = 100 MP into its bank (up to 1,000 points a week)' : undefined}>{it.kind === 'mp' ? '💎 Put in' : owned ? 'Extend' : 'Unlock'}</button></div>; })}</div>
    <small className="cc-empty">Boost credits: {d.boosts} · raffle tickets: {d.tickets}. Style unlocks work without holding $FEE for their duration.</small>
  </section>;
}

// Realized PnL from verified FEELESS receipts.
export function PnlTracker({ address }) {
  const [d, setD] = useState(null);
  const [names, setNames] = useState({});
  useEffect(() => { fetch(`/api/reputation/pnl/${address}`).then(r => r.json()).then(x => { setD(x); x.tokens.slice(0, 20).forEach(t => fetch(`/api/market/search?q=${t.mint}`).then(r => r.json()).then(z => setNames(n => ({ ...n, [t.mint]: z.pairs?.[0]?.baseToken?.symbol || t.mint.slice(0, 4) }))).catch(() => {})); }).catch(() => {}); }, [address]);
  if (!d?.tokens) return null;
  const total = (d.tokens || []).reduce((s, t) => s + t.realizedSol, 0);
  return <section className="wp-card pnl-tracker" data-testid="pnl-tracker">
    <div className="wpj-head"><h3><Glyph name="chart" tone="mint" /> PnL</h3><span className="wpj-count"><b className={total >= 0 ? 'positive' : 'negative'}>{total >= 0 ? '+' : ''}{total.toFixed(4)} SOL</b> realized · {d.trades} trades</span></div>
    {!d.tokens.length ? <p className="wp-bio">No FEELESS trades yet — PnL builds from verified trade receipts.</p> : <div className="pnl-rows">{d.tokens.map(t => <div key={t.mint}><b>${names[t.mint] || '…'}</b><span>{t.trades} trades</span><span>holding {t.holding.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span><b className={t.realizedSol >= 0 ? 'positive' : 'negative'}>{t.realizedSol >= 0 ? '+' : ''}{t.realizedSol.toFixed(4)} SOL</b></div>)}</div>}
    <small className="cc-empty">{d.note}</small>
  </section>;
}

// Keyboard shortcuts (press ? for the list).
const KEYS = [['/', 'Search'], ['g h', 'Home'], ['g t', 'The Trenches'], ['g d', 'Discover'], ['g p', 'Pump radar'], ['g w', 'Watchlist'], ['g f', 'FeeCat'], ['g m', 'My profile'], ['g l', 'Leaderboard'], ['?', 'This list'], ['Esc', 'Close']];
export function Shortcuts() {
  const nav = useNavigate();
  const { wallet } = useWallet() || {};
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let g = 0;
    const onKey = e => {
      if (/input|textarea|select/i.test(document.activeElement?.tagName || '') || document.activeElement?.isContentEditable || e.metaKey || e.ctrlKey) return;
      if (e.key === '?') { setOpen(o => !o); return; }
      if (e.key === 'Escape') { setOpen(false); return; }
      if (e.key === 'g') { g = Date.now(); return; }
      if (Date.now() - g < 900) {
        const to = { h: '/terminal', t: '/terminal/chat', d: '/terminal/discover', p: '/terminal/pump', w: '/terminal/watchlist', f: '/terminal/feecat', l: '/terminal/leaderboard', m: wallet?.address ? `/terminal/profile/${wallet.address}` : null }[e.key];
        if (to) { e.preventDefault(); nav(to); }
        g = 0;
      }
    };
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey);
  }, [nav, wallet?.address]);
  if (!open) return null;
  return <div className="kb-overlay" role="dialog" aria-label="Keyboard shortcuts" onClick={() => setOpen(false)}><div className="kb-card" onClick={e => e.stopPropagation()}><h3>⌨️ Shortcuts</h3>{KEYS.map(([k, l]) => <div key={k} className="kb-row"><span>{k.split(' ').map(x => <kbd key={x}>{x}</kbd>)}</span><em>{l}</em></div>)}</div></div>;
}
