import React, { useState } from 'react';

// How Fuse works, in one strip. Admin = the full pipeline (breed → prove → publish → traders → P&L).
// Trader = what you're buying, in plain words. Shared by Cmd Ctr and Trade › Fuse Lab.
const ADMIN = [
  ['🔎', 'Scan', 'Live Solana pools, fakes dropped'],
  ['🧬', 'Breed', 'Baskets evolve over generations'],
  ['🏟', 'Prove', '$5 paper run, settles at 24h'],
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
      <p><b>Tiny buys:</b> every swap pays a small network fee, so at $5 fewer pools keeps more of your money working. The Size guard warns if your slice would move a thin pool.</p>
    </>}</div>}
  </div>;
}

// Cmd Ctr › Fuse: one deck, one panel at a time (no scroll wall). Tab remembered per viewer.
const KEY = 'feeless-fuse-deck';
export function FuseDeck({ panels }) {
  const read = () => { try { return localStorage.getItem(KEY) || panels[0][0]; } catch { return panels[0][0]; } };
  const [tab, setTab] = useState(read);
  const cur = panels.find(p => p[0] === tab) || panels[0];
  const go = k => { setTab(k); try { localStorage.setItem(KEY, k); } catch { /* private mode */ } };
  return <section className="fdeck" data-testid="fuse-deck">
    <header className="fdeck-head"><div><span className="m-label">⚛️ FUSE DECK</span><h3>Breed it. Prove it. Ship it.</h3></div><FuseExplainer admin /></header>
    <nav className="m-seg fdeck-nav" role="tablist" aria-label="Fuse deck">{panels.map(([k, l]) => <button type="button" key={k} role="tab" aria-selected={cur[0] === k} className={cur[0] === k ? 'active' : ''} onClick={() => go(k)} data-testid={`fdeck-${k}`}>{l}</button>)}</nav>
    <div className="fdeck-body" key={cur[0]}>{cur[2]}</div>
  </section>;
}
