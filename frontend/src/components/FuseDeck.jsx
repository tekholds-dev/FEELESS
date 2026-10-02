import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';

// How Fuse works, in one strip. Admin = the full pipeline (breed → prove → publish → traders → P&L).
// Trader = what you're buying, in plain words. Shared by Cmd Ctr and Trade › Fuse Lab.
const ADMIN = [
  ['🔎', 'Scan', 'Live Solana pools, fakes dropped'],
  ['🧬', 'Breed', 'Baskets evolve over generations'],
  ['🏟', 'Prove', 'We run $5, settles at 24h'],
  ['📣', 'Publish', 'Traders see it + chat /fuse'],
  ['💰', 'Earn', 'Real P&L + your creator cut'],
];
const TRADER = [
  ['1', 'You pick', 'or tap Find my best 3'],
  ['2', 'We weigh', 'fee APR × depth, 10–70% each'],
  ['3', 'One approval', 'one swap per pool, you sign'],
  ['4', 'You hold', 'the coins, P&L tracked live'],
];

export function FuseExplainer({ admin = false }) {
  const [open, setOpen] = useState(false);
  const steps = admin ? ADMIN : TRADER;
  return <div className={`fx-explain ${admin ? 'is-admin' : ''}`} data-testid="fuse-explainer">
    <ol className="fx-flow">{steps.map(([ic, t, s], i) => <li key={t} style={{ animationDelay: `${i * 60}ms` }}><b>{ic}</b><span>{t}<small>{s}</small></span></li>)}</ol>
    <button type="button" className="fx-more" aria-expanded={open} onClick={() => setOpen(o => !o)}>{open ? 'Less' : 'What exactly is a Fuse?'}</button>
    {open && <div className="fx-body">{admin ? <>
      <p><b>A Fuse is a basket of live pools bought in one click.</b> Each pool becomes a normal FEELESS swap paid in SOL; the trader holds the coins. Nothing is pooled, locked or custodied.</p>
      <p><b>Evolution</b> ranks baskets on today's numbers (grade, fee APR, 24h move, depth) minus size impact and fee drag. It is a ranking, not a forecast — that's why the <b>Arena</b> exists: a strategy only counts as <em>proven</em> after 3 settled $5 paper runs with a positive average. Traders' "Find my best 3" uses the proven strategy.</p>
      <p><b>Money:</b> normal FEELESS fee per leg; the creator cut (≤50% of that fee) is tracked per published Fuse. Health flags a published Fuse once a fresh champion beats it by 10%+.</p>
    </> : <>
      <p><b>A Fuse buys several coins at once.</b> Your SOL is split across the pools you picked; each one is a normal swap you approve in your wallet — all with one approval. You end up holding the coins, like any buy.</p>
      <p><b>The numbers are estimates from the last 24h.</b> "APR est." is the trading-fee rate those pools earn for liquidity providers — it shows how busy a pool is; it is not paid to you for holding. Prices can fall as easily as rise.</p>
      <p><b>Where Fuses come from:</b> the FEELESS team breeds baskets from live pools, proves each strategy with 24h $5 runs, then publishes the winners here and in chat. "Find my best 3" uses whichever strategy has actually proven itself. A FUSE Vault (deposit SOL, hold one share of many pools) is being built and audited first — it is not live.</p>
      <p><b>Tiny buys:</b> every swap pays a small network fee, so at $5 fewer pools keeps more of your money working. The Size guard warns if your slice would move a thin pool.</p>
    </>}</div>}
  </div>;
}

// Cmd Ctr › Fuse: live KPI ribbon, a left rail (each stop says what it is), one panel at a time. Tab remembered per viewer.
// panels: [key, label, node, blurb, group] — consecutive panels with the same group sit under one rail heading. call = admin fetch (ribbon reads /admin/fuses/hq once a minute).
const KEY = 'feeless-fuse-deck';
const money = v => `${v < 0 ? '−' : ''}$${Math.abs(v || 0).toFixed(2)}`;
export function FuseDeck({ panels, call }) {
  const read = () => { try { return localStorage.getItem(KEY) || panels[0][0]; } catch { return panels[0][0]; } };
  const [tab, setTab] = useState(read);
  const [hq, setHq] = useState(null);
  useEffect(() => {
    if (!call) return undefined;
    const load = () => call('/admin/fuses/hq').then(setHq).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 60000); window.addEventListener('feeless:fuse-hq', load);
    return () => { clearInterval(t); window.removeEventListener('feeless:fuse-hq', load); };
  }, [call]);
  useEffect(() => { const on = e => { if (panels.some(p => p[0] === e.detail?.panel)) setTab(e.detail.panel); }; window.addEventListener('feeless:fuse-deck-go', on);
    return () => window.removeEventListener('feeless:fuse-deck-go', on); }, [panels]);
  const cur = panels.find(p => p[0] === tab) || panels[0];
  const go = k => { setTab(k); try { localStorage.setItem(KEY, k); } catch { /* private mode */ } };
  const o = hq?.outlook; const b = hq?.book;
  return <section className="fdeck" data-testid="fuse-deck">
    <header className="fdeck-head"><div><span className="m-label">⚛️ FUSE DECK</span><h3>Breed it. Prove it. Ship it.</h3></div><FuseExplainer admin /></header>
    {hq && <div className="fdeck-kpis" data-testid="fuse-kpis">
      <div className={`fdeck-kpi ${b.pnlUsd > 0 ? 'up' : b.pnlUsd < 0 ? 'down' : ''}`}><small>REAL FUSE P&L</small><b className="m-num">{money(b.pnlUsd)}</b><em>{b.positions} fuses · {b.winners}▲ {b.losers}▼</em></div>
      <div className={`fdeck-kpi is-outlook ${o.proven ? 'up' : ''}`} title={o.note}><small>24H OUTLOOK · ARENA</small>
        {o.style ? <><b className="m-num">$1 → ${o.per1.toFixed(2)}</b><em>{o.style} · {o.runs} runs · {o.winRate}% won</em></> : <><b className="m-num">unproven</b><em>run champions in the arena</em></>}</div>
      <div className="fdeck-kpi"><small>PUBLISHED</small><b className="m-num">{hq.published}</b><em>live for traders</em></div>
      <div className="fdeck-kpi"><small>BLOODLINE</small><b className="m-num">{hq.bloodline.length}</b><em>saved champions</em></div>
      <div className="fdeck-kpi"><small>SHIELD</small><b className="m-num">{hq.blockedCuts}</b><em>self/bot cuts blocked</em></div>
    </div>}
    <div className="fdeck-main">
      <nav className="fdeck-rail" role="tablist" aria-label="Fuse deck">{panels.map(([k, l, , blurb, group], i) => <React.Fragment key={k}>
        {group && group !== panels[i - 1]?.[4] && <span className="fdeck-group">{group}</span>}
        <button type="button" role="tab" aria-selected={cur[0] === k} className={cur[0] === k ? 'active' : ''} onClick={() => go(k)} data-testid={`fdeck-${k}`}>
        <b>{l}</b>{blurb && <small>{blurb}</small>}</button></React.Fragment>)}</nav>
      <div className="fdeck-body" key={cur[0]}>{cur[3] && <p className="fdeck-intro">{cur[3]}</p>}{cur[2]}</div>
    </div>
  </section>;
}

// Fuse vs Vault on LIVE pools: where a dollar's return can actually come from. Fuse = price moves (fast, both ways);
// Vault = pool trading fees (slow, steady, needs the audited contract). Numbers from /fuses/yield-math (no promises).
const c$ = v => (v >= 1 ? `$${v.toFixed(2)}` : `${(v * 100).toFixed(v < 0.01 ? 2 : 1)}¢`);
export function VaultMath() {
  const [y, setY] = useState(null);
  useEffect(() => { let alive = true; fetch(apiUrl('/api/reputation/fuses/yield-math')).then(r => r.json()).then(d => alive && setY(d)).catch(() => {}); return () => { alive = false; }; }, []);
  if (!y?.fuse1) return <div className="fl-row is-ghost" />;
  const pct = v => `${v >= 1 ? '+' : '−'}${Math.abs((v - 1) * 100).toFixed(0)}%`;
  return <div className="vmath" data-testid="vault-math">
    <div className="vmath-col is-fuse"><span className="m-label">⚛️ FUSE · PRICE MOVES</span><p>$1 split into live pools rides their prices. Last 24h (6h / 1h on young pools; ±95% outliers dropped) on {y.pools} deep Solana pools:</p>
      <dl><dt>Best pool</dt><dd className="m-pos">$1 → ${y.fuse1.best.toFixed(2)} <small>{pct(y.fuse1.best)}</small></dd><dt>Typical</dt><dd>$1 → ${y.fuse1.median.toFixed(2)}</dd><dt>Worst</dt><dd className="m-neg">$1 → ${y.fuse1.worst.toFixed(2)} <small>{pct(y.fuse1.worst)}</small></dd></dl>
      <small className="m-dim">This is where +20¢…+50¢ on $1 in a day can happen — and where −30¢ happens too. The engine's job: pick baskets that lean to the good side (grade, depth, momentum) and the Arena proves whether it does.</small></div>
    <div className="vmath-col is-vault"><span className="m-label">🏦 VAULT · POOL FEES</span><p>The Vault would hold real liquidity positions, so it EARNS the trading fees a Fuse never does. Best deep pools now ≈ <b>{y.vaultAprPct}% APR</b>:</p>
      <dl><dt>$1</dt><dd>+{c$(y.vaultPerDay['1'])}/day</dd><dt>$20</dt><dd>+{c$(y.vaultPerDay['20'])}/day</dd><dt>$100</dt><dd>+{c$(y.vaultPerDay['100'])}/day</dd></dl>
      <small className="m-dim">Fees alone can't make +20¢/day on $1 — that needs {y.aprFor20c.toLocaleString()}% APR, which only shows up in tiny pools for hours (and they bleed on price). What the Vault adds: one shared rebalance instead of 3 network fees per person, fee income on top of the price moves, and true auto take-profit / stop-loss (the contract can act; your wallet can't be signed for). Not live until audited.</small></div>
  </div>;
}
