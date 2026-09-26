import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { useWallet } from '../hooks/useWallet';
import { getChatSession } from '../lib/chatSession';

const post = (url, body) => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(async r => { const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'Failed'); return b; });

// Spend earned points.
export function PointsShop({ address }) {
  const { wallet, signMessage } = useWallet() || {};
  const [d, setD] = useState(null);
  const load = () => fetch(`/api/reputation/shop?address=${address}`).then(r => r.json()).then(setD).catch(() => {});
  useEffect(() => { load(); }, [address]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!d) return null;
  const bal = d.points - d.spent;
  const buy = async it => { try { const session = await getChatSession(wallet.address, signMessage); const r = await post('/api/reputation/shop/buy', { address: wallet.address, session, item: it.id }); toast.success(`Unlocked ${it.label} · ${r.balance} pts left`); load(); } catch (e) { toast.error(e.message); } };
  return <section className="wp-card shop-card" data-testid="points-shop">
    <div className="wpj-head"><h3>🛍️ Points shop</h3><span className="wpj-count"><b>{bal.toLocaleString()}</b> to spend</span></div>
    <div className="shop-grid">{d.items.map(it => { const owned = Object.keys(d.unlocks).some(k => it.grant.badge ? k === `badge:${it.grant.badge}` : Object.entries(it.grant).some(([a, b]) => k === `${a}:${b}`)); return <div key={it.id} className={`shop-item ${owned ? 'owned' : ''}`}><b>{it.label}</b><span>{it.cost} pts</span><button type="button" className={bal >= it.cost ? 'btn-primary' : 'btn-outline'} disabled={bal < it.cost} onClick={() => buy(it)}>{owned ? 'Extend' : 'Unlock'}</button></div>; })}</div>
    <small className="cc-empty">Boost credits: {d.boosts} · raffle tickets: {d.tickets}. Style unlocks work without holding $FEE for their duration.</small>
  </section>;
}

// Weekly faction battle.
export function TrenchWars() {
  const { wallet, signMessage } = useWallet() || {};
  const [d, setD] = useState(null);
  const load = () => fetch(`/api/reputation/wars${wallet?.address ? `?address=${wallet.address}` : ''}`).then(r => r.json()).then(setD).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [wallet?.address]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!d) return null;
  const max = Math.max(1, ...d.factions.map(f => f.score));
  const left = Math.max(0, d.endsAt - Date.now() / 1000);
  const join = async f => { if (!wallet) { toast('Connect a wallet to pick a side.'); return; } try { const session = await getChatSession(wallet.address, signMessage); await post('/api/reputation/wars/join', { address: wallet.address, session, faction: f }); toast.success('You\'re in. Every point you earn this week counts for your side.'); load(); } catch (e) { toast.error(e.message); } };
  return <section className="meta-panel wars" data-testid="trench-wars">
    <div className="mp-head"><h2 className="live-gradient-text">⚔️ Trench Wars · {d.week}</h2><span>ends in {Math.floor(left / 86400)}d {Math.floor((left % 86400) / 3600)}h{d.lastWinner ? ` · last winner ${d.lastWinner}` : ''}</span></div>
    <p className="wp-bio">Pick a side once a week. Every reward point members earn counts for their faction. The winning side gets a badge and a boosted airdrop share.</p>
    <div className="wars-grid">{d.factions.map(f => <div key={f.id} className={`war-f f-${f.id} ${d.mine === f.id ? 'mine' : ''}`}><b>{f.label}</b><div className="war-bar"><i style={{ width: `${(f.score / max) * 100}%` }} /></div><span>{f.score.toLocaleString()} pts · {f.members} fighters</span>{!d.mine && <button type="button" className="btn-outline" onClick={() => join(f.id)}>Join</button>}{d.mine === f.id && <em>your side</em>}</div>)}</div>
  </section>;
}

// Realized PnL from verified FEELESS receipts.
export function PnlTracker({ address }) {
  const [d, setD] = useState(null);
  const [names, setNames] = useState({});
  useEffect(() => { fetch(`/api/reputation/pnl/${address}`).then(r => r.json()).then(x => { setD(x); x.tokens.slice(0, 20).forEach(t => fetch(`https://api.dexscreener.com/latest/dex/tokens/${t.mint}`).then(r => r.json()).then(z => setNames(n => ({ ...n, [t.mint]: z.pairs?.[0]?.baseToken?.symbol || t.mint.slice(0, 4) }))).catch(() => {})); }).catch(() => {}); }, [address]);
  if (!d) return null;
  const total = d.tokens.reduce((s, t) => s + t.realizedSol, 0);
  return <section className="wp-card pnl-tracker" data-testid="pnl-tracker">
    <div className="wpj-head"><h3>📈 PnL</h3><span className="wpj-count"><b className={total >= 0 ? 'positive' : 'negative'}>{total >= 0 ? '+' : ''}{total.toFixed(4)} SOL</b> realized · {d.trades} trades</span></div>
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
