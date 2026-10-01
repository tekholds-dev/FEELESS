import React, { useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../lib/api';
import { toast } from 'sonner';
import { FuseGo } from './FuseGo';
import { FuseEvolve } from './FuseEvolve';
import { FusePnl } from './FuseHQ';
import { FuseRail } from './FuseRail';
import { FuseCard, legPair } from './FuseCard';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { FuseExplainer, VaultMath } from './FuseDeck';
import '../styles/fuseLab.css';

// ⚛️ FUSE LAB: browse the chain's real pools, tick them, and see live how FEELESS auto-weighs them (fee APR × depth,
// 10–70% each) and where one SOL amount goes. Traders fuse up to 3 pools; Cmd Ctr (pass `call`) up to 6 with manual
// weights + publish-as-Fuse. Preview is read-only; Fuse in = one wallet approval for one normal swap per pool (FuseGo).
// Caps are enforced server-side (fuse.USER_MAX_LEGS / MAX_LEGS).
const LENSES = [['popular', 'Popular'], ['yield', 'Top yield'], ['deep', 'Deepest'], ['new', 'New 72h']];
const usd = v => (v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${(v || 0).toFixed(v < 10 ? 2 : 0)}`);
const pct = v => (Math.abs(v) >= 1000 ? `${(1 + v / 100).toFixed(1)}x` : `${v >= 0 ? "+" : ""}${(v || 0).toFixed(1)}%`);
const apr = v => (v >= 1000 ? `${(v / 100).toFixed(0)}x` : `${Math.round(v || 0)}%`);

// Scroll the PAGE to the preview (never scrollIntoView: it would scroll inside the clipped card).
const scrollToMix = () => { const el = document.querySelector('[data-testid="fuse-lab"] .fl-mix'); if (el) window.scrollTo({ top: Math.max(0, el.getBoundingClientRect().top + window.scrollY - 120), behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }); };

export function FuseLab({ chain = 'solana', call, runnerPicks = [], onRunnerPicks, incoming, limits }) {
  const admin = Boolean(call); const MAX = admin ? 10 : 3;
  const [manual, setManual] = useState(false); const [addon, setAddon] = useState(false); const [wts, setWts] = useState({}); const [pub, setPub] = useState({ name: '', emoji: '⚛️', creatorBps: 1000 });
  const [lens, setLens] = useState('popular');
  const [pools, setPools] = useState(null);
  const [q, setQ] = useState('');
  const [picked, setPicked] = useState([]);
  const [sol, setSol] = useState('1');
  const [prev, setPrev] = useState(null);
  const [err, setErr] = useState('');
  const [going, setGoing] = useState(false);
  const [best, setBest] = useState({ budget: 20, busy: false, style: null });
  const load = (legs, s) => { setManual(false); setPicked(legs); if (s) setSol(s.toFixed(4)); scrollToMix(); };
  // Find it: the best basket for EACH budget ($5 / $20 / $100 — small budgets punish many pools, big ones thin pools), as cards.
  const findBest = () => { setBest(b => ({ ...b, busy: true, cards: null }));
    Promise.all([5, 20, 100].map(budgetUsd => fetch(apiUrl('/api/reputation/fuses/best3'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ budgetUsd }) })
      .then(r => r.json()).then(d => (d.champion ? { ...d, budget: budgetUsd } : null)).catch(() => null)))
      .then(list => { const cards = list.filter(Boolean); if (!cards.length) throw new Error('No live pools right now.');
        setBest(b => ({ ...b, busy: false, cards, style: cards[0].style, proven: cards[0].proven })); })
      .catch(e => { setBest(b => ({ ...b, busy: false })); toast.error(e.message); }); };

  useEffect(() => { let alive = true; setPools(null);
    fetch(apiUrl(`/api/reputation/fuses/discover?lens=${lens}&chain=${chain}`)).then(r => (r.ok ? r.json() : { pools: [] })).then(d => alive && setPools(d.pools || [])).catch(() => alive && setPools([]));
    return () => { alive = false; }; }, [lens, chain]);

  const key = picked.map(p => `${p.pairAddress}:${manual ? wts[p.pairAddress] || 1 : ''}`).join(',') + '|' + runnerPicks.map(r => r.mint).join(',');
  const legsN = picked.length + runnerPicks.length;
  useEffect(() => {
    setGoing(false);
    if (legsN < 2) { setPrev(null); setErr(''); return undefined; }
    const body = JSON.stringify({ pools: picked.map(p => ({ chainId: p.chainId, pairAddress: p.pairAddress, symbol: p.symbol, weight: manual ? wts[p.pairAddress] || 1 : 1 })), sol: Number(sol) || 0, manual: admin && manual, runners: addon && !runnerPicks.length, runnerMints: runnerPicks.map(r => r.mint) });
    const run = () => (admin ? call('/fuses/preview', { method: 'POST', body })
      : fetch(apiUrl('/api/reputation/fuses/preview'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body }).then(async r => { const d = await r.json(); if (!r.ok) throw new Error(d.detail || 'Preview failed'); return d; }));
    const t = setTimeout(() => run().then(d => { setPrev(d); setErr(''); }).catch(e => setErr(e.message)), 250);
    return () => clearTimeout(t);
  }, [key, sol, manual, addon]); // eslint-disable-line react-hooks/exhaustive-deps
  // Featured / Runners tabs hand the Lab a basket to load (pools here, runners into the picks).
  useEffect(() => { if (!incoming?.n) return; const pools = incoming.legs.filter(l => !l.runner && l.role !== 'runner').slice(0, MAX);
    setManual(false); setPicked(pools); if (incoming.sol) setSol(incoming.sol.toFixed(4)); scrollToMix(); }, [incoming?.n]); // eslint-disable-line react-hooks/exhaustive-deps

  const shown = useMemo(() => { const s = q.trim().toLowerCase(); return (pools || []).filter(p => !s || `${p.symbol}/${p.quote} ${p.dex}`.toLowerCase().includes(s)); }, [pools, q]);
  const isOn = p => picked.some(x => x.pairAddress === p.pairAddress);
  const toggle = p => setPicked(list => (isOn(p) ? list.filter(x => x.pairAddress !== p.pairAddress) : list.length >= MAX ? list : [...list, p]));

  return <section className={`m-card m-live fl ${admin ? 'is-admin' : ''}`} data-testid="fuse-lab">
    <header className="fl-head">
      <div><span className="m-label">⚛️ FUSE LAB</span><h3>{admin ? 'Design a Fuse.' : 'Many pools. One buy.'}</h3>
        <p className="m-dim">{admin ? 'Up to 10 pools, auto or your own weights, 24h backtest, size guard — then publish it for traders.' : `Pick 2–${MAX} live pools. FEELESS weighs them and shows exactly where your SOL goes. One approval buys them all.`}</p></div>
      <span className="fl-badges">{admin && <span className="m-chip warn">CMD CTR · 10 POOLS</span>}<span className="m-chip ok fl-chain"><i />{chain.toUpperCase()}</span></span>
    </header>
    {!admin && <FuseExplainer />}
    {!admin && <details className="fl-vm"><summary>Fuse vs Vault — where a dollar's return comes from (live)</summary><VaultMath /></details>}
    {admin ? <><FuseRail call={call} onUse={load} /><FuseEvolve call={call} maxLegs={MAX} onLoad={load} /></> : <>
      <FusePnl />
      <div className="fl-best" data-testid="fl-best"><div><b>🧬 Find my best 3</b><small className="m-dim">{best.style ? `Bred with the ${best.style} strategy${best.proven ? ' — proven in our 24h arena' : ''}` : 'We breed hundreds of baskets from live pools and deal you the winner for $5, $20 and $100.'}</small></div>
        <button type="button" className="m-btn primary m-go" disabled={best.busy} onClick={findBest} data-testid="fl-best-go">{best.busy ? 'Breeding…' : best.cards ? 'Breed again' : 'Find it'}</button></div>
      {(best.busy || best.cards) && <div className="frail-track fl-best-cards" data-testid="fl-best-cards">{best.busy ? [5, 20, 100].map(v => <div key={v} className="frail-ghost" />)
        : best.cards.map((c, i) => <article key={c.budget} className="frail-item" style={{ animationDelay: `${i * 90}ms` }}>
          <FuseCard c={{ ...c.champion, style: c.style }} style={c.style} rank={i} budget={c.budget} />
          <div className="frail-meta"><b>${c.budget} basket</b><span className="m-dim">{c.style}{c.proven ? ' · arena-proven' : ''}</span></div>
          <button type="button" className="m-btn primary m-go" onClick={() => load(c.champion.legs, c.solUsd ? c.budget / c.solUsd : null)} data-testid={`fl-best-use-${c.budget}`}>Use this · ${c.budget}</button></article>)}</div>}
      <FuseRail onUse={load} />
    </>}
    <div className="fl-body">
      <div className="fl-browse">
        <div className="fl-tools"><div className="m-seg" role="radiogroup" aria-label="Pool lens">{LENSES.map(([k, l]) => <button type="button" key={k} role="radio" aria-checked={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)}>{l}</button>)}</div>
          <input className="m-input fl-q" value={q} onChange={e => setQ(e.target.value)} placeholder="Filter $SYMBOL or DEX" aria-label="Filter pools" /></div>
        {picked.length >= MAX && <small className="fl-full">All {MAX} slots used — untick a pool to swap it.</small>}
        <div className="fl-list" role="listbox" aria-multiselectable="true" aria-label="Pools">
          {pools == null ? Array.from({ length: 6 }, (_, i) => <div key={i} className="fl-row is-ghost" />)
            : !shown.length ? <p className="m-dim fl-empty">No live pools in this lens right now.</p>
            : shown.map(p => { const on = isOn(p); const full = !on && picked.length >= MAX;
              return <button type="button" role="option" aria-selected={on} key={p.pairAddress} className={`fl-row ${on ? 'is-on' : ''}`} disabled={full} onClick={() => toggle(p)} data-testid={`fl-pool-${p.pairAddress}`} title={full ? `Max ${MAX} pools` : undefined}>
                <span className="fl-check" aria-hidden="true">{on ? '✓' : '+'}</span>
                <span className="fl-logo"><TokenAvatar pair={legPair(p)} size={28} /></span>
                <span className="fl-name"><b>{p.symbol}<small>/{p.quote}</small></b><em>{p.dex}</em></span>
                <span className="fl-cell"><small>LIQ</small><b className="m-num">{usd(p.liquidityUsd)}</b></span>
                <span className="fl-cell"><small>VOL 24H</small><b className="m-num">{usd(p.volume24h)}</b></span>
                <span className="fl-cell"><small>APR EST</small><b className="m-num m-pos">{apr(p.aprEst)}</b></span>
                <span className="fl-cell"><small>24H</small><b className={`m-num ${p.change24h >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(p.change24h)}</b></span>
              </button>; })}
        </div>
      </div>
      <aside className="fl-mix" aria-live="polite">
        <div className="fl-mix-head"><span className="m-label">YOUR FUSE · {picked.length}/{MAX}</span>{picked.length > 0 && <button type="button" className="m-btn fl-clear" onClick={() => setPicked([])}>Clear</button>}</div>
        {runnerPicks.length > 0 && <div className="fl-runner-picks" data-testid="fl-runner-picks"><small>🏃 RUNNERS {runnerPicks.length}/{admin ? 6 : 3}</small>{runnerPicks.map(r => <span key={r.mint} className="fl-rchip">{r.symbol || `${r.mint.slice(0, 4)}…`}<em>{r.lane}</em>
          <button type="button" aria-label={`Remove ${r.symbol}`} onClick={() => onRunnerPicks?.(runnerPicks.filter(x => x.mint !== r.mint))}>×</button></span>)}</div>}
        {legsN < 2 ? <div className="fl-hint"><b>{legsN ? 'Pick one more leg' : 'Tap pools on the left'}</b><small>{onRunnerPicks ? 'Up to 3 pools + 3 runners (Runners tab). ' : ''}The preview builds live as you pick.</small></div> : <>
          <label className="m-field fl-amt"><span>SOL in</span><div className="fl-amt-row"><input className="m-input m-num" inputMode="decimal" value={sol} onChange={e => setSol(e.target.value.replace(/[^0-9.]/g, ''))} aria-label="SOL amount" />
            <div className="m-seg">{['0.5', '1', '5'].map(v => <button type="button" key={v} className={sol === v ? 'active' : ''} onClick={() => setSol(v)}>{v}</button>)}</div></div>
            {prev && <small className="m-dim">≈ {usd(prev.usd)} at {usd(prev.solUsd)}/SOL</small>}</label>
          {!onRunnerPicks && <label className="m-toggle fl-addon" data-tip="Bolts the 2 best Fuse Runners of this round onto your basket as a 20% slice (10% each). Runners are fresh Pump.fun coins — fast, gated, and risky."><input type="checkbox" checked={addon} onChange={e => setAddon(e.target.checked)} data-testid="fl-addon" /><span>🏃 +2 Runners add-on <small>20% slice</small></span></label>}
          {admin && <div className="fl-wmode"><div className="m-seg" role="radiogroup" aria-label="Weights"><button type="button" role="radio" aria-checked={!manual} className={!manual ? 'active' : ''} onClick={() => setManual(false)}>Auto weights</button><button type="button" role="radio" aria-checked={manual} className={manual ? 'active' : ''} onClick={() => setManual(true)}>Manual</button></div>
            {manual && picked.map(p => <label key={p.pairAddress} className="fl-slider"><span>{p.symbol}</span><input type="range" min="1" max="100" value={wts[p.pairAddress] || 1} onChange={e => setWts(w => ({ ...w, [p.pairAddress]: Number(e.target.value) }))} /><b className="m-num">{wts[p.pairAddress] || 1}</b></label>)}</div>}
          {err ? <div className="m-note bad">{err}</div> : !prev ? <div className="fl-row is-ghost" /> : <>
            <div className="fl-preview-card" data-testid="fl-preview-card"><FuseCard c={{ pools: prev.legs.map(l => l.pairAddress), fitness: prev.score.points, bornGen: 0,
              parts: { grade: prev.score.grade, aprScore: Math.round(Math.min(400, prev.blendedAprPct) / 4), momentum24h: prev.backtest24hPct, calm: '—', feeDragPct: prev.usd ? Math.min(100, (0.0001 * prev.legs.length * prev.solUsd) / prev.usd * 100) : 0, impactLegs: (prev.impactWarn || []).length },
              legs: prev.legs }} style={manual ? 'steady' : 'yield'} rank={0} budget={Math.max(1, Math.round(prev.usd))} /><small className="m-dim">Live card of your picks · ⟲ for the money math</small></div>
            <div className="fl-bar">{prev.legs.map(l => <i key={l.pairAddress} style={{ flexGrow: l.weight }} title={`${l.symbol} ${l.weight}%`}><span>{l.symbol} {Math.round(l.weight)}%</span></i>)}</div>
            <ul className="fl-legs">{prev.legs.map(l => <li key={l.pairAddress} className={l.runner ? 'is-runner' : ''}><b>{l.runner ? '🏃 ' : ''}{l.symbol}</b><span className="m-num">{l.weight.toFixed(0)}%</span><span className="m-num">{l.sol} SOL</span><span className="m-num m-dim">{usd(l.usd)}</span><span className={`m-num ${(l.change24h || 0) >= 0 ? 'm-pos' : 'm-neg'}`} data-tip="What this slice did over the last 24h (price move × your $)">{(l.change24h || 0) >= 0 ? '+' : '−'}${Math.abs(l.usd * (l.change24h || 0) / 100).toFixed(2)}</span></li>)}</ul>
            <div className="fl-kpis">
              <div className="m-stat"><small>GRADE</small><b className={`fl-grade g-${prev.score.grade}`} title={prev.score.parts.map(p => `${p.part}: ${p.why}`).join('\n')}>{prev.score.grade}</b></div>
              <div className="m-stat" data-tip="Pools' trading-fee rate (how busy they are). Paid to liquidity providers, NOT to Fuse holders."><small>POOL APR</small><b className="m-num m-pos">{apr(prev.blendedAprPct)}</b></div>
              <div className="m-stat" data-tip="Your SOL × the basket's last-24h move. A replay, not a promise."><small>24H REPLAY $</small><b className={`m-num ${prev.backtest24hPct >= 0 ? 'm-pos' : 'm-neg'}`}>{prev.backtest24hPct >= 0 ? '+' : '−'}${Math.abs(prev.usd * prev.backtest24hPct / 100).toFixed(2)}</b></div>
              <div className="m-stat" title="What this mix did over the last 24h"><small>IF FUSED 24H AGO</small><b className={`m-num ${prev.backtest24hPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(prev.backtest24hPct)}</b></div>
            </div>
            {prev.impactWarn?.length > 0 && <div className="m-note warn"><b>SIZE GUARD</b><span>{prev.impactWarn.join(', ')}: your slice is over 1% of that pool — expect price impact. Lower the SOL or swap the pool.</span></div>}
            <details className="fl-why"><summary>Why these weights?</summary><p>Each pool scores <b>fee APR</b> (24h volume × 0.25% ÷ liquidity, capped 400%) × <b>depth</b> (log of liquidity). Shares are clamped to 10–70% so one pool never runs the fuse. Grade = depth + healthy turnover + calm 24h moves + forensics safety.</p>
              <ul>{prev.score.parts.map(p => <li key={p.part}><span>{p.part}</span><b className="m-num">{p.points}</b><small>{p.why}</small></li>)}</ul></details>
            {limits && !limits.canOpen && <div className="m-note warn"><b>CARD LIMIT</b><span>You have {limits.open} open Fuse cards (max {limits.max}). Withdraw one in My cards{limits.max < 3 ? ` — or hold $${limits.feeFor3rd} of $FEE for a 3rd card` : ''}.</span></div>}
            {!going ? <button type="button" className="m-btn primary m-go wide" disabled={!(Number(sol) > 0) || (limits && !limits.canOpen)} onClick={() => setGoing(true)} data-testid="fl-go">⚡ Fuse in {Number(sol) || 0} SOL · 1 click</button>
              : <FuseGo legs={prev.legs} onClose={() => setGoing(false)} />}
            {admin && <div className="fl-pub"><span className="m-label">PUBLISH AS A FUSE</span><div className="fl-pub-row"><input className="m-input fl-emoji" value={pub.emoji} maxLength={4} onChange={e => setPub(x => ({ ...x, emoji: e.target.value }))} aria-label="Emoji" />
              <input className="m-input" value={pub.name} maxLength={40} placeholder="Fuse name" onChange={e => setPub(x => ({ ...x, name: e.target.value }))} />
              <label className="fl-cut"><small>CREATOR CUT</small><input className="m-input m-num" inputMode="numeric" value={pub.creatorBps / 100} onChange={e => setPub(x => ({ ...x, creatorBps: Math.min(5000, Math.round((Number(e.target.value) || 0) * 100)) }))} />%</label></div>
              <button type="button" className="m-btn primary" disabled={pub.name.trim().length < 2} data-testid="fl-publish" onClick={() => call('/admin/fuses', { method: 'POST', body: JSON.stringify({ ...pub, legs: prev.legs.map(l => ({ chainId: l.chainId, pairAddress: l.pairAddress, symbol: l.symbol, weight: l.weight })) }) })
                .then(() => { toast.success(`${pub.name} is live in the Fuse Lab`); setPub(x => ({ ...x, name: '' })); }).catch(e => toast.error(e.message))}>Publish for traders</button></div>}
            <small className="m-dim fl-fine">Preview only — nothing moves until you sign. Yields are estimates from the last 24h.</small>
          </>}
        </>}
      </aside>
    </div>
  </section>;
}

// Trade page: Swap | Fuse Lab as a segmented tab at the top, so the swap keeps its look and nothing stacks below it.
export function TradeTabs({ children, fuse, runners }) {
  const read = () => { const t = new URLSearchParams(window.location.search).get('tab'); return t === 'fuse' || t === 'runners' ? t : 'swap'; };
  const [tab, setTab] = useState(read);
  const go = t => { setTab(t); const u = new URL(window.location.href); if (t !== 'swap') u.searchParams.set('tab', t); else u.searchParams.delete('tab'); window.history.replaceState(null, '', u); };
  return <>
    <div className="m-seg trade-tabs" role="tablist" aria-label="Trade">{[['swap', '⇄ Swap'], ['fuse', '⚛️ Fuse Lab'], ...(runners ? [['runners', '🏃 Runners']] : [])].map(([k, l]) => <button type="button" key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => go(k)} data-testid={`trade-tab-${k}`}>{l}</button>)}</div>
    <div className="trade-tab-body" key={tab}>{tab === 'fuse' ? fuse : tab === 'runners' ? runners : children}</div>
  </>;
}
