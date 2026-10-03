import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiUrl } from '../lib/api';
import '../styles/fuseMoney.css';
import { LiveFuseCard } from './FuseCard';

// 💵 Fuse money, in plain words — shared by every card surface (tier cards, My cards, battle corners, profile, Lab):
// MoneyMath (PUT IN → STILL IN CARD + PAID OUT = NOW, profit apart from fees), RoundBell (10s countdown into every round),
// PaperAudit (a card's paper book: true-fill entries → now), CardShowcase (3-card 3D shuffle), CardCosts (fee receipt).
export const usd = v => { const a = Math.abs(v || 0); return `${(v || 0) < 0 ? '−' : ''}$${a >= 10000 ? `${(a / 1000).toFixed(1)}K` : a.toFixed(2)}`; };
export const pct = v => `${(v || 0) >= 0 ? '+' : ''}${Math.abs(v || 0) >= 1000 ? `${((v || 0) / 100 + 1).toFixed(1)}x` : `${(v || 0).toFixed(1)}%`}`;
// compact for tight tiles: $1.3K · $517 · $1.75
export const usdK = v => { const a = Math.abs(v || 0); return `${(v || 0) < 0 ? '−' : ''}$${a >= 1000 ? `${(a / 1000).toFixed(1)}K` : a >= 100 ? a.toFixed(0) : a.toFixed(2)}`; };
export const txUrl = sig => `https://solscan.io/tx/${sig}`;
const ago = t => { const s = Date.now() / 1000 - t; return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };

export function MoneyMath({ putIn = 0, held = 0, paidOut = 0, fees, compounded = 0, compact = false, label }) {
  const now = held + paidOut; const pnl = now - putIn; const p = putIn ? (now / putIn - 1) * 100 : 0;
  return <div className={`mm ${compact ? 'is-compact' : ''}`} data-testid="money-math">
    {label && <span className="mm-label">{label}</span>}
    <div className="mm-eq">
      <span data-tip="What went into the card — money that reached the pools (fees apart)"><small>PUT IN</small><b className="m-num">{usd(putIn)}</b></span><i>→</i>
      <span data-tip="Coins + cash still in the card at live prices (gains that compounded back in are here)"><small>IN CARD</small><b className="m-num fl-tick" key={Math.round(held * 100)}>{usd(held)}</b></span><i>+</i>
      <span data-tip="Profit already paid out to the wallet — it's SOL there now"><small>PAID OUT</small><b className="m-num m-pos">{usd(paidOut)}</b></span><i>=</i>
      <span data-tip="Everything the card is worth to its owner right now"><small>NOW</small><b className="m-num">{usd(now)}</b></span></div>
    <div className={`mm-pnl ${pnl >= 0 ? 'is-up' : 'is-down'}`}><b className="m-num">{pnl >= 0 ? '+' : '−'}{usd(Math.abs(pnl))} <em>({pct(p)})</em></b>
      <small>profit = NOW − PUT IN · price moves only</small></div>
    {(compounded > 0 || fees != null) && <small className="mm-note">{compounded > 0 ? `♻ ${usd(compounded)} of take-profits rolled back in (already inside IN CARD)` : ''}{compounded > 0 && fees != null ? ' · ' : ''}{fees != null ? `fees ${usd(fees)} paid apart, never in profit` : ''}</small>}
  </div>;
}

// 🔔 Every round opens with a 10s countdown: the clock runs to the round, the last 10 seconds take over the card.
export function RoundBell({ at, sec = 10, label = 'NEXT ROUND' }) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 250); return () => clearInterval(t); }, []);
  const left = Math.max(0, (at || 0) - now);
  const bell = left > 0 && left <= sec;
  // at zero the new round is dealt on the server — pull it straight away (and again shortly) instead of waiting for the next poll
  useEffect(() => { if (!at) return undefined; const ms = at * 1000 - Date.now(); if (ms < -20000) return undefined;
    const ts = [1500, 5000, 10000].map(d => setTimeout(() => window.dispatchEvent(new Event('feeless:prime')), Math.max(0, ms) + d)); return () => ts.forEach(clearTimeout); }, [at]);
  const mm = Math.floor(left / 60); const ss = Math.floor(left % 60);
  return <span className={`rbell ${bell ? 'is-bell' : ''} ${left <= 0 ? 'is-due' : ''}`} data-testid="round-bell" data-tip={`${label.toLowerCase()} · a 10s countdown opens every round`}>
    {bell ? <b className="rbell-n" key={Math.ceil(left)}>{Math.ceil(left)}</b> : <b className="m-num">{left <= 0 ? 'dealing…' : mm >= 60 ? `${Math.floor(mm / 60)}h ${mm % 60}m` : `${mm}:${String(ss).padStart(2, '0')}`}</b>}
    <small>{bell ? `🔔 ${label} · dealing in` : left <= 0 ? `🔔 ${label} · dealt` : label}</small></span>;
}

// 📜 Paper audit for any Arena card: its live battle book (each coin's TRUE fill — impact included — → now, $ in → $ now),
// fees apart, and its finished books (won / lost, $). Centered pop-up, click outside / Esc closes.
export function PaperAudit({ k, name, onClose }) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; fetch(apiUrl(`/api/reputation/fuses/paper?key=${encodeURIComponent(k)}`)).then(r => r.json()).then(x => alive && setD(x)).catch(() => alive && setD({ live: null, past: [] }));
    const esc = e => e.key === 'Escape' && onClose(); window.addEventListener('keydown', esc); return () => { alive = false; window.removeEventListener('keydown', esc); }; }, [k, onClose]);
  const b = d?.live;
  return createPortal(<div className="ce-shade is-pop" role="presentation" onClick={onClose} data-testid="paper-audit">
    <aside className="pa m-card m-live" role="dialog" aria-modal="true" aria-label={`${name} paper audit`} onClick={e => e.stopPropagation()}>
      <header className="m-row"><span className="m-label">📜 PAPER AUDIT · TRUE FILLS</span><b>{name}</b><button type="button" className="cx-x" onClick={onClose} aria-label="Close">×</button></header>
      <p className="m-dim pa-how">Every card in an Arena battle runs $100 of paper dealt at the price a wallet would really get (pool impact both ways, learned from real Fuse-wallet fills). The trader's per-coin fee is booked apart, never in profit.</p>
      {!d ? <div className="frail-ghost" /> : b ? <>
        <div className="pa-top"><LiveFuseCard label="📄 PAPER · TRUE FILLS" aura="fire" r={{ id: `paper-${k}`, name, closed: false, costUsd: b.startUsd, valueUsd: b.valueUsd, realizedUsd: 0, baseUsd: b.startUsd, extraUsd: 0,
          pnlUsd: b.pnlUsd, pnlPct: b.pct, legs: b.legs.map(l => ({ pairAddress: l.pairAddress, symbol: l.symbol, role: l.role, usd: l.inUsd, tokens: l.units, valueUsd: l.nowUsd, pnlUsd: l.nowUsd - l.inUsd, pnlPct: l.pct, priced: true, priceNow: l.now, liq: l.liq })) }} />
          <div className="pa-side"><MoneyMath putIn={b.startUsd} held={b.valueUsd} paidOut={0} fees={b.feesUsd} compact />
            <TrailSummary events={[]} legs={b.legs.map(l => ({ symbol: l.symbol, usd: l.nowUsd }))} /></div></div>
        <div className="pa-rows" role="table">{b.legs.map(l => <div key={l.pairAddress} className="pa-row" role="row">
          <b>${l.symbol}</b><span data-tip={`mid $${l.mid} · paid $${l.entry} (impact included)`}>in @ <i className="m-num">${Number(l.entry).toPrecision(4)}</i> → <i className="m-num">${Number(l.now).toPrecision(4)}</i></span>
          <span className="m-num">{usd(l.inUsd)} → {usd(l.nowUsd)}</span><em className={`m-num ${l.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(l.pct)}</em></div>)}</div>
        <small className="m-dim">this battle: best {pct(b.hiPct)} · worst {pct(b.loPct)} · dealt {ago(b.at)} ago</small></>
        : <small className="m-dim">Not fighting right now — its finished books are below.</small>}
      {d?.past?.length > 0 && <section className="pa-past"><span className="m-label">FINISHED BOOKS · {d.record.won}W {d.record.lost}L · {usd(d.record.pnlUsd)} · fees {usd(d.record.feesUsd)}</span>
        {d.past.map(x => <div key={x.endedAt} className={`pa-done r-${x.result}`}><b>{x.result === 'won' ? '🏆 won' : x.result === 'lost' ? '✕ lost' : '🤝 draw'}</b>
          <span className="m-num">{usd(x.startUsd)} → {usd(x.valueUsd)}</span><em className={`m-num ${x.pnlUsd >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(x.pct)}</em><time className="m-dim">{ago(x.endedAt)} ago</time></div>)}</section>}
    </aside></div>, document.body);
}

// 🃏 3-card shuffle above the battle: the top three cards orbit in 3D, the front one is the spotlight. Tap a card to bring
// it forward. Pure transform/opacity; still under fx-lite / reduced motion.
export function CardShowcase({ cards = [], onOpen }) {
  const [front, setFront] = useState(0);
  const [hold, setHold] = useState(false);
  const n = Math.min(3, cards.length);
  useEffect(() => { if (n < 2 || hold || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;
    const t = setInterval(() => setFront(f => (f + 1) % n), 4200); return () => clearInterval(t); }, [n, hold]);
  if (n < 2) return null;
  return <section className="sc3" onMouseEnter={() => setHold(true)} onMouseLeave={() => setHold(false)} data-testid="card-showcase" aria-label="Top cards">
    <span className="m-label sc3-k">🏆 TOP 3 WINNERS · LIVE SHUFFLE</span>
    <div className="sc3-ring" style={{ '--n': n }}>{cards.slice(0, n).map((c, i) => { const pos = (i - front + n) % n;
      return <div key={c.key} role="button" tabIndex={0} className={`sc3-card p-${pos} t-${c.tone || 'gold'} ${c.node ? 'has-card' : ''}`} onClick={e => { if (e.target.closest('.fcd-flip')) return; pos === 0 ? onOpen?.(c) : setFront(i); }}
        onKeyDown={e => e.key === 'Enter' && (pos === 0 ? onOpen?.(c) : setFront(i))} aria-label={`${c.name} ${pct(c.pct)}`} data-testid={`sc3-${i}`}>
        <span className="sc3-shine" aria-hidden="true" />
        {c.node ? <span className="sc3-real">{c.node}</span> : null}
        <span className="sc3-meta"><small>{c.badge}</small><b>{c.name}</b><em className={`m-num ${c.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(c.pct)}</em>{c.sub && <i className="m-num">{c.sub}</i>}</span></div>; })}</div>
  </section>;
}

// 💲 What a card costs BEFORE you buy it: first buy (per coin), the auto rounds (5 included, then packs), card swaps — in $ and
// % of the card, from the live HQ prices. HQ / creator wallets: no FEELESS fee, only network.
export function CardCosts({ coins = 3, amount = 20, staff = false, rounds = 10, autoFees, onAutoFees }) {
  const [p, setP] = useState(null);
  useEffect(() => { let alive = true; const t = setTimeout(() => fetch(apiUrl(`/api/reputation/fees/pricing?coins=${coins}&usd=${Math.max(1, amount || 0)}&rounds=${rounds}`)).then(r => r.json()).then(x => alive && setP(x)).catch(() => {}), 250);
    return () => { alive = false; clearTimeout(t); }; }, [coins, amount, rounds]);
  const x = p?.plan;
  if (!x) return <div className="ccost m-card"><span className="m-label">💲 WHAT THIS CARD COSTS</span><small className="m-dim">loading prices…</small></div>;
  return <div className="ccost m-card" data-testid="card-costs"><span className="m-label">💲 WHAT THIS CARD COSTS</span>
    {amount > 0 && amount <= 10 && amount / coins < 0.5 && <p className="m-note warn" data-testid="ccost-min">Cards of $10 or less buy at least $0.50 per coin — use {Math.max(1, Math.floor(amount / 0.5))} coins or more $.</p>}
    {staff ? <p className="ccost-free">HQ card · <b>$0 FEELESS fee</b> — only Solana network fees (~$0.001 per swap).</p> : <>
      <ul className="ccost-list">
        <li data-tip={`$${x.perCoinUsd.toFixed(2)} per coin, never more than ${p.bundle.maxPct}% of a coin's slice`}><span>🃏 First buy · {coins} coins</span><b className="m-num">{usd(x.buyUsd)}</b></li>
        <li data-tip="Every card runs 5 auto rounds free; each +5 is one round pack"><span>🔁 Rounds · first {x.free} free{x.packs ? ` · +${x.packs} pack${x.packs > 1 ? 's' : ''}` : ''}</span><b className="m-num">{usd(x.roundsUsd)}</b></li>
        <li data-tip={`One rotation = sell the old coin + buy the new one, $${p.bundle.swapUsd.toFixed(2)} each — it comes out of the swap, your wallet never pays it separately`}><span>⇄ Swaps · {x.rounds} rounds × {usd(x.swapUsd)}</span><b className="m-num">{usd(x.swapsUsd)}</b></li>
        {p.prepay?.usd > 0 && <li data-tip="Paid with the first buy (same approval); those swaps then pay no FEELESS fee"><span>💳 Prepaid · first {p.prepay.rounds} rounds' swaps</span><b className="m-num">{usd(p.prepay.usd)}</b></li>}
        <li className="ccost-tot"><span>Total over {x.rounds} rounds</span><b className="m-num">{usd(x.totalUsd)} <em>({x.pct}% of {usd(amount)})</em></b></li></ul>
      {onAutoFees && <label className="m-toggle ccost-auto" data-tip="When rounds run out and the card is up more than the pack price, the card pays +5 rounds from its profit (owed until the next take). Never while it's flat or down."><input type="checkbox" checked={autoFees !== false} onChange={e => onAutoFees(e.target.checked)} data-testid="auto-fees" /><span>💸 Card pays its fees from profit</span></label>}</>}
    <small className="m-dim">Network fees (~$0.001/swap) go to Solana, not FEELESS. Fees are never counted in profit.</small></div>;
}

// ✅ What did good · 🪙 what stays · ✂ what was cut — the profit trail in three lines, from the card's own events + coins.
export function TrailSummary({ events = [], legs = [] }) {
  const sum = k => events.filter(e => k.includes(e.kind)).reduce((a, e) => a + (e.usd || 0), 0);
  const winners = [...new Set(events.filter(e => ['tp', 'payout'].includes(e.kind) && e.symbol).map(e => e.symbol))];
  const cut = [...new Set(events.filter(e => ['sl', 'rug', 'rotate', 'park', 'floor'].includes(e.kind) && e.symbol).map(e => e.symbol))];
  return <div className="ts" data-testid="trail-summary">
    <span className="ts-good"><small>✅ DID GOOD</small><b>{winners.length ? winners.slice(0, 4).map(s => `$${s}`).join(' · ') : '—'}</b><em className="m-num">{usd(sum(['tp', 'payout']))} taken</em></span>
    <span className="ts-stay"><small>🪙 STAYS</small><b>{legs.length ? legs.slice(0, 4).map(l => `$${l.symbol}`).join(' · ') : '—'}</b><em className="m-num">{usd(legs.reduce((a, l) => a + (l.usd ?? l.valueUsd ?? 0), 0))} held</em></span>
    <span className="ts-cut"><small>✂ CUT / SWAPPED</small><b>{cut.length ? cut.slice(0, 4).map(s => `$${s}`).join(' · ') : '—'}</b><em className="m-num">{usd(sum(['sl', 'rug', 'park']))} sold</em></span></div>;
}

// 📊 Entry · P&L per coin (My cards, profile): your real entry (from your confirmed buy) → live price, $ in → $ now, %.
export function CoinTable({ legs = [] }) {
  if (!legs.length) return null;
  return <div className="ctab" role="table" aria-label="Entry and P&L per coin" data-testid="coin-table">
    <div className="ctab-row is-head" role="row"><span>COIN</span><span>ENTRY → NOW</span><span>$ IN → NOW</span><span>P&L</span></div>
    {legs.map(l => <div key={l.pairAddress} className="ctab-row" role="row"><b>{l.role === 'runner' ? '🏃 ' : ''}${l.symbol}</b>
      <span className="m-num">{l.entryPx ? `$${Number(l.entryPx).toPrecision(3)}` : '—'} → {l.nowPx ? `$${Number(l.nowPx).toPrecision(3)}` : '—'}</span>
      <span className="m-num">{usd(l.inUsd)} → {usd(l.nowUsd)}</span>
      <em className={`m-num fl-tick ${l.pct >= 0 ? 'm-pos' : 'm-neg'}`} key={(l.pct || 0).toFixed(1)}>{l.nowPx ? pct(l.pct) : '—'}</em></div>)}</div>;
}


// 🔄 Pick-3 cycle: choose up to 3 shapes in order (anchor · degen · mixed · 🛡 safest · ⚖ breakeven) — or keep a named / auto cycle.
const SHAPES = [['anchor', '⚓ Anchor'], ['degen', '🔥 Degen'], ['mixed', '⚖ Mixed'], ['safest', '🛡 Safest'], ['breakeven', '⚖ Breakeven']];
export function CycleBuilder({ value, onChange }) {
  const custom = typeof value === 'string' && value.includes(',') ? value.split(',') : [];
  const [parts, setParts] = useState(custom.length ? custom : ['', '', '']);
  const set = (i, v) => { const n = [...parts]; n[i] = v; setParts(n); const pick = n.filter(Boolean); if (pick.length >= 2) onChange(pick.join(',')); };
  return <span className="cyb" data-testid="cycle-builder" data-tip="Your own cycle: up to 3 shapes, played in order each round. Any card ≤ −50% still switches to 🛟 rescue by itself.">
    <small>OR PICK 3</small>{[0, 1, 2].map(i => <select key={i} className="m-input" value={parts[i] || ''} onChange={e => set(i, e.target.value)} aria-label={`Cycle shape ${i + 1}`} data-testid={`cyb-${i}`}>
      <option value="">{i < 2 ? `shape ${i + 1}` : '(optional)'}</option>{SHAPES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>)}
    {custom.length > 0 && <b className="m-num">✓ {custom.join(' → ')}</b>}</span>;
}
