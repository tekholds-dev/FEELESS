import React, { useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../lib/api';
import { toast } from 'sonner';
import { FuseGo } from './FuseGo';
import { FuseEvolve } from './FuseEvolve';
import { FusePnl } from './FuseHQ';
import { FuseRail } from './FuseRail';
import { FuseCard, legPair } from './FuseCard';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { useLivePrices } from '../lib/livePrices';
import { formatLivePrice } from '../lib/livePrice';
import { FuseExplainer, VaultMath } from './FuseDeck';
import { CardExplain } from './CardExplain';
import { RiskDial } from './RiskDial';
import { RISK_DIALS, applyRisk } from '../lib/riskDial';
import '../styles/fuseLab.css';

// ⚛️ FUSE LAB: browse the chain's real pools, tick them, and see live how FEELESS auto-weighs them (fee APR × depth,
// 10–70% each) and where one SOL amount goes. Traders fuse up to 3 pools; Cmd Ctr (pass `call`) up to 6 with manual
// weights + publish-as-Fuse. Preview is read-only; Fuse in = one wallet approval for one normal swap per pool (FuseGo).
// Caps are enforced server-side (fuse.USER_MAX_LEGS / MAX_LEGS).
const LENSES = [['popular', 'Popular'], ['yield', 'Top yield'], ['deep', 'Deepest'], ['runners', '🏃 Runners'], ['new', 'New 72h']];
const usd = v => (v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${(v || 0).toFixed(v < 10 ? 2 : 0)}`);
const pct = v => (Math.abs(v) >= 1000 ? `${(1 + v / 100).toFixed(1)}x` : `${v >= 0 ? "+" : ""}${(v || 0).toFixed(1)}%`);
const apr = v => (v >= 1000 ? `${(v / 100).toFixed(0)}x` : `${Math.round(v || 0)}%`);

// Scroll the PAGE to the preview (never scrollIntoView: it would scroll inside the clipped card).
const scrollToMix = () => { const el = document.querySelector('[data-testid="fuse-lab"] .fl-mix'); if (el) window.scrollTo({ top: Math.max(0, el.getBoundingClientRect().top + window.scrollY - 120), behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }); };

// Card pricing (public /fees/pricing, fetched once per page): a card bought all at once pays a flat $ per coin, never more
// than maxPct of a leg; legs above maxLegUsd pay the normal %. Cmd Ctr cards: no FEELESS fee.
let pricingP = null;
export const cardFee = (legs, pr) => legs.reduce((a, l) => { const u = Number(l.usd) || 0; const b = pr.bundle;
  return a + (!b.on || u > b.maxLegUsd ? u * pr.swapBps / 10000 : Math.min(b.perLegUsd, u * b.maxPct / 100)); }, 0);
export function CardPricing({ legs, admin }) {
  const [pr, setPr] = useState(null);
  useEffect(() => { let alive = true; pricingP = pricingP || fetch(apiUrl('/api/reputation/fees/pricing')).then(r => r.json()).catch(() => { pricingP = null; return null; });
    pricingP.then(d => alive && d?.bundle && setPr(d)); return () => { alive = false; }; }, []);
  if (admin) return <div className="fl-price is-free" data-testid="card-pricing"><span className="m-label">💲 CMD CTR CARD</span><b>$0 FEELESS fee</b><small>network + partner (Jupiter / pool) fees only</small></div>;
  if (!pr) return null;
  const fee = cardFee(legs, pr); const usdIn = legs.reduce((a, l) => a + (Number(l.usd) || 0), 0);
  return <div className="fl-price" data-testid="card-pricing" data-tip={`Bundle pricing: $${pr.bundle.perLegUsd.toFixed(2)} per coin, never more than ${pr.bundle.maxPct}% of a leg. Legs over $${pr.bundle.maxLegUsd} pay the normal ${(pr.swapBps / 100).toFixed(2)}%. Network fees are separate.`}>
    <span className="m-label">💲 CARD PRICING</span><b className="m-num">${fee.toFixed(fee < 1 ? 3 : 2)}</b><small>{legs.length} coins · ${pr.bundle.perLegUsd.toFixed(2)}/coin{usdIn ? ` · ${(fee / usdIn * 100).toFixed(2)}% of $${usdIn.toFixed(2)}` : ''}</small></div>;
}

// 🏃 Runners lens: This round (addable while still passing every gate) · Hot now (gated, busiest first) · Watching (failed a
// gate — shown with the reason, never addable). One /runners/discover read (20s server cache).
export function runnerSections(d, admin = false) {   // Cmd Ctr sees every passing runner; traders the busiest 24
  const byMint = Object.fromEntries((d.runners || []).map(x => [x.mint, x]));
  const round = (d.round || []).map(p => ({ ...(byMint[p.mint] || {}), ...p, runner: true, section: 'round', chg1h: p.move, blocked: p.passing ? '' : (p.gates || [])[0] || 'fails a gate now' }));
  const inRound = new Set(round.map(p => p.mint));
  const hot = (d.runners || []).filter(x => !inRound.has(x.mint)).sort((a, b) => (b.vol1h || 0) - (a.vol1h || 0)).slice(0, admin ? 80 : 24).map(x => ({ ...x, runner: true, section: 'hot' }));
  const watch = (d.watching || []).slice(0, 8).map(x => ({ ...x, runner: true, section: 'watch', blocked: (x.gates || [])[0] || 'fails a gate' }));
  return [...round, ...hot, ...watch];
}
const SECTION = { round: ['🏟 This round', 'picked by the arena · live move since the round'], hot: ['🔥 Hot now', 'passing every gate · busiest first'], watch: ['👀 Watching', 'failed a gate — not addable'] };

// Live numbers for a runner row from the shared 10s price poller: price, market cap scaled by the live price, and the move
// (since the round for round picks, else the live 5m). Falls back to the server's numbers when the poller has none.
export function liveRunner(p, lp) {
  const px = lp?.price || 0; const base = Number(p.price) || 0;
  const mcap = px && base && p.mcap ? p.mcap * (px / base) : p.mcap;
  const move = p.section === 'round' ? (px && p.entry ? (px / p.entry - 1) * 100 : p.chg1h) : (lp ? lp.m5 : p.chg1h);
  return { live: Boolean(px), price: px || base || null, mcap, move, moveLabel: p.section === 'round' ? 'ROUND' : lp ? '5M LIVE' : '1H' };
}

// 🎯 Card plan (set before Fuse in; lands on the card once the buy is verified): per-coin TP / SL, auto-profit level
// (Cmd Ctr levels, after fees), on profit 💸 collect or ♻ compound, 🔒 hold or ⇄ swap. Every trigger = an alert with
// a pre-filled one-approval action. Runners start with their lane's exits.
let rulesP = null;
export const useCardRules = () => { const [r, setR] = useState(null);
  useEffect(() => { let alive = true; rulesP = rulesP || fetch(apiUrl('/api/reputation/fuses/rules')).then(x => x.json()).catch(() => { rulesP = null; return null; });
    rulesP.then(x => alive && x && setR(x)); return () => { alive = false; }; }, []); return r; };
// One-tap TP / SL for the whole card (then fine-tune any coin in the dropdown).
export const PLAN_PRESETS = [['safe', '🛡 Safe', 30, 15, 'Take +30%, stop −15% on every coin'], ['balanced', '⚖ Balanced', 50, 25, 'Take +50%, stop −25% on every coin'],
  ['degen', '🚀 Degen', 100, 40, 'Let it run: take +100%, stop −40%'], ['lanes', '🏃 Lanes', null, null, 'Runners use their lane exits; pools +30 / −15']];
export const applyPreset = (legs, id) => { const p = PLAN_PRESETS.find(x => x[0] === id);
  return Object.fromEntries(legs.map(l => [l.pairAddress, id === 'lanes' ? (l.runner ? { tp: 50, sl: 30 } : { tp: 30, sl: 15 }) : { tp: p[2], sl: p[3] }])); };
export const defaultLegLimits = legs => Object.fromEntries(legs.filter(l => l.runner).map(l => [l.pairAddress, { tp: 50, sl: 30 }]));

export function CardPlan({ legs, plan, setPlan }) {
  const rules = useCardRules();
  const levels = rules?.yieldLevels || [25, 50, 100, 200];
  const lim = (pa, k, v) => setPlan(p => ({ ...p, risk: 'custom', legs: { ...p.legs, [pa]: { ...(p.legs[pa] || {}), [k]: v.replace(/[^0-9.]/g, '') } } }));
  const legKey = legs.map(l => l.pairAddress).join(',');
  useEffect(() => { if (plan.risk && plan.risk !== 'custom') setPlan(applyRisk(legs, plan.risk)); }, [legKey]); // eslint-disable-line react-hooks/exhaustive-deps
  const runners = legs.filter(l => l.runner || l.role === 'runner').length;
  const maxR = RISK_DIALS[plan.risk]?.runners;
  const seg = (k, opts) => <div className="m-seg" role="radiogroup">{opts.map(([v, l, tip]) => <button key={String(v)} type="button" role="radio" aria-checked={plan[k] === v} className={plan[k] === v ? 'active' : ''} data-tip={tip} onClick={() => setPlan(p => ({ ...p, risk: 'custom', [k]: v }))} data-testid={`plan-${k}-${v}`}>{l}</button>)}</div>;
  return <details className="fl-plan" open data-testid="card-plan"><summary><span className="m-label">🎯 CARD PLAN</span><small className="m-dim">one dial sets it all · alerts with one-tap actions, you approve</small></summary>
    <div className="fl-plan-row fl-risk"><span>🎚 Risk</span><RiskDial value={plan.risk || 'custom'} onChange={id => setPlan(applyRisk(legs, id))} /></div>
    {maxR != null && runners > maxR && <div className="m-note warn"><b>{RISK_DIALS[plan.risk].label} = {maxR} runner{maxR === 1 ? '' : 's'} max</b><span>You picked {runners}. Remove {runners - maxR} or pick a bolder dial.</span></div>}
    <details className="fl-plan-tune"><summary>✎ Customize (TP/SL per coin · profit trigger · collect or compound · hold or rotate)</summary>
    <div className="fl-plan-row"><span>Auto-set TP / SL</span><div className="m-seg" role="group">{PLAN_PRESETS.map(([id, l, , , tip]) => <button key={id} type="button" data-tip={tip} onClick={() => setPlan(p => ({ ...p, risk: 'custom', legs: applyPreset(legs, id) }))} data-testid={`plan-preset-${id}`}>{l}</button>)}
      <button type="button" data-tip="Clear every coin's limits" onClick={() => setPlan(p => ({ ...p, risk: 'custom', legs: {} }))}>Off</button></div></div>
    <details className="fl-plan-list" data-testid="plan-list"><summary>Per-coin TP / SL · {legs.length} coins · {Object.values(plan.legs).filter(v => Number(v.tp) || Number(v.sl)).length} set <span aria-hidden="true">▾</span></summary>
    <div className="fl-plan-legs">{legs.map(l => { const v = plan.legs[l.pairAddress] || {}; return <div key={l.pairAddress} className={`fl-plan-leg ${l.runner ? 'is-runner' : ''}`}>
      <b>{l.runner ? '🏃 ' : ''}{l.symbol}</b>
      <label data-tip="Take profit on this coin: alert + pre-filled sell when it's up this much since your buy">TP +<input className="m-input m-num" inputMode="decimal" placeholder="off" value={v.tp ?? ''} onChange={e => lim(l.pairAddress, 'tp', e.target.value)} data-testid={`plan-tp-${l.pairAddress}`} />%</label>
      <label data-tip="Stop-loss on this coin: alert + pre-filled sell when it's down this much">SL −<input className="m-input m-num" inputMode="decimal" placeholder="off" value={v.sl ?? ''} onChange={e => lim(l.pairAddress, 'sl', e.target.value)} />%</label></div>; })}</div></details>
    <div className="fl-plan-row"><span>Profit trigger (price move)</span>{seg('at', [[null, 'Off', 'No card-level auto-profit'], ...levels.map(v => [v, `+${v}%`, `Alert when the whole card is up +${v}% from your confirmed buy (fees never mixed into card P&L)`])])}</div>
    <div className="fl-plan-row"><span>On profit</span>{seg('onProfit', [['collect', '💸 Auto TP', 'At your level: a one-tap sell of just the gain back to SOL — your base stays in'], ['compound', '♻ Auto-compound', 'At your level: a one-tap roll of the gain back into the card (trim winners, top up the rest) — builds a compound streak']])}</div>
    <div className="fl-plan-row"><span>Card</span>{seg('mode', [['hold', '🔒 Hold · switch by hand', 'The card stays as built. One switch per 24h, your pick.'], ['swap', '🤖 Auto-rotate daily', `Once a day a coin that fails a gate or drops ${rules?.swapDropPct ?? 25}% gets a pre-filled swap for the best gated runner — one approval`]])}</div>
    </details>
  </details>;
}

export const planBody = plan => ({ ...plan, legs: Object.fromEntries(Object.entries(plan.legs).map(([pa, v]) => [pa, { tp: Number(v.tp) || null, sl: Number(v.sl) || null }]).filter(([, v]) => v.tp || v.sl)) });

// Leg caps mirror the server (fuse_hq.legs_ok): traders 3 pools + 3 runners; Cmd Ctr 12 legs in any mix (6/6, 12 runners…).
export const legCaps = admin => (admin ? { pools: 12, runners: 12, total: 12 } : { pools: 3, runners: 3, total: 6 });

export function FuseLab({ chain = 'solana', call, runnerPicks: picksIn, onRunnerPicks: setPicksIn, incoming, limits }) {
  const admin = Boolean(call); const caps = legCaps(admin); const MAX = caps.pools;
  const [ownRuns, setOwnRuns] = useState([]);   // Cmd Ctr Lab keeps its own runner picks; the Fuse page passes them in
  const runnerPicks = setPicksIn ? picksIn || [] : ownRuns; const onRunnerPicks = setPicksIn || setOwnRuns;
  const [manual, setManual] = useState(false); const [addon, setAddon] = useState(false); const [wts, setWts] = useState({}); const [pub, setPub] = useState({ name: '', emoji: '⚛️', creatorBps: 1000 });
  const [lens, setLens] = useState('popular');
  const [pools, setPools] = useState(null);
  const [q, setQ] = useState('');
  const [picked, setPicked] = useState([]);
  const [sol, setSol] = useState('1');
  const [prev, setPrev] = useState(null);
  const [err, setErr] = useState('');
  const [going, setGoing] = useState(false);
  const [explain, setExplain] = useState(false);
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
    const url = lens === 'runners' ? '/api/reputation/runners/discover' : `/api/reputation/fuses/discover?lens=${lens}&chain=${chain}`;
    fetch(apiUrl(url)).then(r => (r.ok ? r.json() : {})).then(d => alive && setPools(lens === 'runners' ? runnerSections(d, admin) : d.pools || [])).catch(() => alive && setPools([]));
    return () => { alive = false; }; }, [lens, chain, admin]);

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
  const [copy, setCopy] = useState(null);   // ⚡ copying another trader's card: {id, owner, pct}
  const [plan, setPlan] = useState({ risk: 'balanced', at: 50, onProfit: 'collect', mode: 'hold', legs: {} });
  const legKey = (prev?.legs || []).map(l => l.pairAddress).join(',');
  useEffect(() => { if (prev?.legs) setPlan(p => ({ ...p, legs: { ...defaultLegLimits(prev.legs), ...Object.fromEntries(Object.entries(p.legs).filter(([pa]) => legKey.includes(pa))) } })); }, [legKey]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!incoming?.n) return; const pools = incoming.legs.filter(l => !l.runner && l.role !== 'runner').slice(0, MAX);
    setCopy(incoming.copyOf ? { id: incoming.copyOf, owner: incoming.owner, pct: incoming.copyPct } : null);
    setManual(false); setPicked(pools); if (incoming.sol) setSol(incoming.sol.toFixed(4)); scrollToMix(); }, [incoming?.n]); // eslint-disable-line react-hooks/exhaustive-deps

  const live = useLivePrices(lens === 'runners' ? (pools || []).filter(p => p.runner && !p.blocked).map(p => p.pairAddress) : []);
  const shown = useMemo(() => { const s = q.trim().toLowerCase(); return (pools || []).filter(p => !s || `${p.symbol}/${p.quote || ''} ${p.dex || ''}`.toLowerCase().includes(s)); }, [pools, q]);
  const isOn = p => (p.runner ? runnerPicks.some(x => x.mint === p.mint) : picked.some(x => x.pairAddress === p.pairAddress));
  const isFull = p => !isOn(p) && (legsN >= caps.total || (p.runner ? runnerPicks.length >= caps.runners : picked.length >= MAX));
  const toggle = p => { if (p.runner) { onRunnerPicks(isOn(p) ? runnerPicks.filter(x => x.mint !== p.mint) : isFull(p) ? runnerPicks : [...runnerPicks, p]); return; }
    setPicked(list => (isOn(p) ? list.filter(x => x.pairAddress !== p.pairAddress) : isFull(p) ? list : [...list, p])); };

  return <section className={`m-card m-live fl ${admin ? 'is-admin' : ''}`} data-testid="fuse-lab">
    <header className="fl-head">
      <div><span className="m-label">⚛️ FUSE LAB</span><h3>{admin ? 'Design a mega card.' : 'Many pools. One buy.'}</h3>
        <p className="m-dim">{admin ? 'Up to 12 legs — pools, runners or any mix (6/6, 12 runners) — auto or your own weights, 24h backtest, size guard. No FEELESS fee on Cmd Ctr cards; publish it or stage it on the Arena.' : `Pick 2–${MAX} live pools. FEELESS weighs them and shows exactly where your SOL goes. One approval buys them all.`}</p></div>
      <span className="fl-badges">{admin && <span className="m-chip warn">CMD CTR · 12 LEGS</span>}<span className="m-chip ok fl-chain"><i />{chain.toUpperCase()}</span></span>
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
        {legsN >= caps.total && <small className="fl-full">All {caps.total} slots used — untick a leg to swap it.</small>}
        <div className="fl-list" role="listbox" aria-multiselectable="true" aria-label="Pools">
          {pools == null ? Array.from({ length: 6 }, (_, i) => <div key={i} className="fl-row is-ghost" />)
            : !shown.length ? <p className="m-dim fl-empty">{lens === 'runners' ? 'No runner passes every gate this minute — the scan refreshes every 20s.' : 'No live pools in this lens right now.'}</p>
            : lens === 'runners' ? shown.map((p, i) => { if (!SECTION[p.section]) return null;   // the previous lens's rows for one render
              const on = isOn(p); const full = isFull(p) || Boolean(p.blocked); const L = liveRunner(p, live.get(p.pairAddress));
              return <React.Fragment key={`${p.section}-${p.mint}`}>{(i === 0 || shown[i - 1].section !== p.section) && <div className={`fl-sec sec-${p.section}`} role="presentation"><b>{SECTION[p.section][0]}</b><small>{SECTION[p.section][1]}</small></div>}
              <button type="button" role="option" aria-selected={on} className={`fl-row fl-runrow sec-${p.section} ${on ? 'is-on' : ''} ${p.blocked ? 'is-blocked' : ''}`} style={{ '--i': Math.min(i, 12) }} disabled={full} onClick={() => toggle(p)} data-testid={`fl-runner-${p.mint}`} data-tip={p.blocked || undefined} title={!p.blocked && full ? 'Card full' : undefined}>
                <span className="fl-check" aria-hidden="true">{on ? '✓' : '+'}</span>
                <span className="fl-logo"><TokenAvatar pair={{ chainId: 'solana', baseToken: { address: p.mint, symbol: p.symbol }, info: { imageUrl: p.logo } }} size={28} /></span>
                <span className="fl-name"><b>🏃 {p.symbol || `${(p.mint || '').slice(0, 4)}…`}{L.live && <i className="fl-livedot" title="Live price (10s)" />}</b><em>{p.blocked ? `✕ ${p.blocked}` : <>{(p.sources || []).map(s => s.label).join(' · ') || `${p.lane || 'runner'} lane`}{L.price ? <span className="fl-px m-num" key={L.price}> · {formatLivePrice(L.price)}</span> : null}</>}</em></span>
                <span className="fl-cell"><small>SCORE</small><b className="m-num">{Math.round(p.score || 0)}</b></span>
                <span className="fl-cell"><small>MCAP</small><b className="m-num fl-tick" key={`m${Math.round(L.mcap || 0)}`}>{L.mcap ? usd(L.mcap) : '—'}</b></span>
                <span className="fl-cell"><small>VOL 1H</small><b className="m-num">{p.vol1h ? usd(p.vol1h) : '—'}</b></span>
                <span className="fl-cell"><small>{L.moveLabel}</small><b className={`m-num fl-tick ${L.move == null ? 'm-dim' : L.move >= 0 ? 'm-pos is-up' : 'm-neg is-down'}`} key={`v${(L.move ?? 0).toFixed(1)}`}>{L.move == null ? '—' : pct(L.move)}</b></span>
              </button></React.Fragment>; })
            : shown.map(p => { const on = isOn(p); const full = isFull(p);
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
        <div className="fl-mix-head"><span className="m-label">YOUR FUSE · {legsN}/{caps.total}</span>{legsN > 0 && <button type="button" className="m-btn fl-clear" onClick={() => { setPicked([]); onRunnerPicks([]); setCopy(null); }}>Clear</button>}</div>
        {copy && <div className="fl-copy" data-testid="fl-copy"><b>⚡ Copying {copy.owner}'s card</b><small>They earn {copy.pct ?? 10}% of the FEELESS fee you pay — not an extra cost to you.</small><button type="button" className="m-btn fl-clear" onClick={() => setCopy(null)} aria-label="Stop copying">×</button></div>}
        {runnerPicks.length > 0 && <div className="fl-runner-picks" data-testid="fl-runner-picks"><small>🏃 RUNNERS {runnerPicks.length}/{caps.runners}</small>{runnerPicks.map(r => <span key={r.mint} className="fl-rchip">{r.symbol || `${r.mint.slice(0, 4)}…`}<em>{r.lane}</em>
          <button type="button" aria-label={`Remove ${r.symbol}`} onClick={() => onRunnerPicks(runnerPicks.filter(x => x.mint !== r.mint))}>×</button></span>)}</div>}
        {legsN < 2 ? <div className="fl-hint"><b>{legsN ? 'Pick one more leg' : 'Tap pools on the left'}</b><small>{admin ? 'Up to 12 legs: pools and 🏃 Runners in any mix. ' : 'Up to 3 pools + 3 runners (🏃 Runners lens). '}The preview builds live as you pick.</small></div> : <>
          <label className="m-field fl-amt"><span>SOL in</span><div className="fl-amt-row"><input className="m-input m-num" inputMode="decimal" value={sol} onChange={e => setSol(e.target.value.replace(/[^0-9.]/g, ''))} aria-label="SOL amount" />
            <div className="m-seg">{['0.5', '1', '5'].map(v => <button type="button" key={v} className={sol === v ? 'active' : ''} onClick={() => setSol(v)}>{v}</button>)}</div></div>
            {prev && <small className="m-dim">≈ {usd(prev.usd)} at {usd(prev.solUsd)}/SOL</small>}</label>
          {!runnerPicks.length && <label className="m-toggle fl-addon" data-tip="Bolts the 2 best Fuse Runners of this round onto your basket as a 20% slice (10% each). Runners are fresh Pump.fun coins — fast, gated, and risky."><input type="checkbox" checked={addon} onChange={e => setAddon(e.target.checked)} data-testid="fl-addon" /><span>🏃 +2 Runners add-on <small>20% slice</small></span></label>}
          {admin && <div className="fl-wmode"><div className="m-seg" role="radiogroup" aria-label="Weights"><button type="button" role="radio" aria-checked={!manual} className={!manual ? 'active' : ''} onClick={() => setManual(false)}>Auto weights</button><button type="button" role="radio" aria-checked={manual} className={manual ? 'active' : ''} onClick={() => setManual(true)}>Manual</button></div>
            {manual && picked.map(p => <label key={p.pairAddress} className="fl-slider"><span>{p.symbol}</span><input type="range" min="1" max="100" value={wts[p.pairAddress] || 1} onChange={e => setWts(w => ({ ...w, [p.pairAddress]: Number(e.target.value) }))} /><b className="m-num">{wts[p.pairAddress] || 1}</b></label>)}</div>}
          {err ? <div className="m-note bad">{err}</div> : !prev ? <div className="fl-row is-ghost" /> : <>
            <div className="fl-preview-card" data-testid="fl-preview-card"><FuseCard c={{ pools: prev.legs.map(l => l.pairAddress), fitness: prev.score.points, bornGen: 0,
              parts: { grade: prev.score.grade, aprScore: Math.round(Math.min(400, prev.blendedAprPct) / 4), momentum24h: prev.backtest24hPct, calm: '—', feeDragPct: prev.usd ? Math.min(100, (0.0001 * prev.legs.length * prev.solUsd) / prev.usd * 100) : 0, impactLegs: (prev.impactWarn || []).length },
              legs: prev.legs }} style={manual ? 'steady' : 'yield'} rank={0} budget={Math.max(1, Math.round(prev.usd))} /><small className="m-dim">Live card of your picks · ⟲ for the money math</small>
              <button type="button" className="m-btn fl-explain" onClick={() => setExplain(true)} data-testid="fl-explain">🔍 Explain this card</button></div>
            {explain && <CardExplain prev={prev} onClose={() => setExplain(false)} card={<FuseCard c={{ pools: prev.legs.map(l => l.pairAddress), fitness: prev.score.points, bornGen: 0,
              parts: { grade: prev.score.grade, aprScore: Math.round(Math.min(400, prev.blendedAprPct) / 4), momentum24h: prev.backtest24hPct, calm: '—', feeDragPct: 0, impactLegs: (prev.impactWarn || []).length }, legs: prev.legs }} style={manual ? 'steady' : 'yield'} rank={0} budget={Math.max(1, Math.round(prev.usd))} autoFlip={5000} />} />}
            <div className="fl-bar">{prev.legs.map(l => <i key={l.pairAddress} style={{ flexGrow: l.weight }} title={`${l.symbol} ${l.weight}%`}><span>{l.symbol} {Math.round(l.weight)}%</span></i>)}</div>
            <ul className="fl-legs">{prev.legs.map(l => <li key={l.pairAddress} className={l.runner ? 'is-runner' : ''}><b>{l.runner ? '🏃 ' : ''}{l.symbol}</b><span className="m-num">{l.weight.toFixed(0)}%</span><span className="m-num">{l.sol} SOL</span><span className="m-num m-dim">{usd(l.usd)}</span><span className={`m-num ${(l.replayPct ?? l.change24h ?? 0) >= 0 ? 'm-pos' : 'm-neg'}`} data-tip={`What this slice did over the last ${(l.replayH ?? 24) >= 1 ? `${l.replayH ?? 24}h` : 'few minutes'} (young pools never use the since-launch move)`}>{(l.replayPct ?? l.change24h ?? 0) >= 0 ? '+' : '−'}${Math.abs(l.usd * (l.replayPct ?? l.change24h ?? 0) / 100).toFixed(2)}</span></li>)}</ul>
            <div className="fl-kpis">
              <div className="m-stat"><small>GRADE</small><b className={`fl-grade g-${prev.score.grade}`} title={prev.score.parts.map(p => `${p.part}: ${p.why}`).join('\n')}>{prev.score.grade}</b></div>
              <div className="m-stat" data-tip="Pools' trading-fee rate (how busy they are). Paid to liquidity providers, NOT to Fuse holders."><small>POOL APR</small><b className="m-num m-pos">{apr(prev.blendedAprPct)}</b></div>
              <div className="m-stat" data-tip="Your SOL × the basket's last-24h move. A replay, not a promise."><small>24H REPLAY $</small><b className={`m-num ${prev.backtest24hPct >= 0 ? 'm-pos' : 'm-neg'}`}>{prev.backtest24hPct >= 0 ? '+' : '−'}${Math.abs(prev.usd * prev.backtest24hPct / 100).toFixed(2)}</b></div>
              <div className="m-stat" title="What this mix did over the last 24h"><small>IF FUSED 24H AGO</small><b className={`m-num ${prev.backtest24hPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(prev.backtest24hPct)}</b></div>
            </div>
            {prev.impactWarn?.length > 0 && <div className="m-note warn"><b>SIZE GUARD</b><span>{prev.impactWarn.join(', ')}: your slice is over 1% of that pool — expect price impact. Lower the SOL or swap the pool.</span></div>}
            <details className="fl-why"><summary>Why these weights?</summary><p>Each pool scores <b>fee APR</b> (24h volume × 0.25% ÷ liquidity, capped 400%) × <b>depth</b> (log of liquidity). Shares are clamped to 10–70% so one pool never runs the fuse. Grade = depth + healthy turnover + calm 24h moves + forensics safety.</p>
              <ul>{prev.score.parts.map(p => <li key={p.part}><span>{p.part}</span><b className="m-num">{p.points}</b><small>{p.why}</small></li>)}</ul></details>
            {prev && <CardPlan legs={prev.legs} plan={plan} setPlan={setPlan} />}
            {prev && <CardPricing legs={prev.legs} admin={admin} />}
            {limits && !limits.canOpen && <div className="m-note warn"><b>CARD LIMIT</b><span>You have {limits.open} open Fuse cards (max {limits.max}). Withdraw one in My cards{limits.max < 3 ? ` — or hold $${limits.feeFor3rd} of $FEE for a 3rd card` : ''}.</span></div>}
            {!going ? <button type="button" className="m-btn primary m-go wide" disabled={!(Number(sol) > 0) || (limits && !limits.canOpen)} onClick={() => setGoing(true)} data-testid="fl-go">⚡ Fuse in {Number(sol) || 0} SOL · 1 click</button>
              : <FuseGo legs={prev.legs} fuse={{ name: copy ? `Copy · ${copy.owner}`.slice(0, 40) : 'Lab fuse', copyOf: copy?.id || '', plan: planBody(plan) }} onClose={() => setGoing(false)} />}
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
