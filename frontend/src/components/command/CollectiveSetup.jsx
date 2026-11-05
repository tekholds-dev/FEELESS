import React, { useEffect, useMemo, useRef, useState } from 'react';
import { LayoutGroup, MotionConfig, animate, motion } from 'motion/react';
import { Ic3 } from '../../lib/icon3d';
import { money } from './SplitFlow';
import '../../styles/collectiveSetup.css';

// 🎛 THE COLLECTIVE'S CONTROLS (owner 2026-11-05): built on Motion. Springs on real numbers, shared-layout tabs, charts drawn from the settings as they are now. Transform and opacity only.
export const SPRING = { type: 'spring', stiffness: 380, damping: 34, mass: 0.7 };
const lite = () => typeof document !== 'undefined' && document.body.classList.contains('fx-lite');
export function Fx({ children }) { return <MotionConfig reducedMotion="user" transition={lite() ? { duration: 0 } : SPRING}>{children}</MotionConfig>; }
const asText = (v, u) => (u === '$' ? `$${Math.round(v)}` : `${Number.isInteger(v) ? v : Number(v).toFixed(1)}${u || ''}`);

// A number that rolls to its new value, written straight to the element so nothing re-renders.
export function Roll({ v, fmt = String, className = 'm-num', testid }) {
  const el = useRef(null); const from = useRef(v);
  useEffect(() => { if (lite() || from.current === v) { if (el.current) el.current.textContent = fmt(v); from.current = v; return undefined; } const c = animate(from.current, v, { duration: 0.35, ease: 'easeOut', onUpdate: x => { if (el.current) el.current.textContent = fmt(x); }, onComplete: () => { from.current = v; } }); return () => c.stop(); }, [v, fmt]);
  return <b ref={el} className={className} data-testid={testid}>{fmt(v)}</b>;
}
export function Tabs({ id, rows, at, onPick }) {
  return <LayoutGroup id={id}><div className="cs-tabs" role="tablist" aria-label={id}>{rows.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={at === k} className={at === k ? 'is-on' : ''} onClick={() => onPick(k)} data-tip={tip} data-testid={`${id}-${k}`}>{at === k ? <motion.i layoutId="pill" aria-hidden="true" /> : null}<span>{l}</span></button>)}</div></LayoutGroup>;
}
// One setting. The real range input sits on top for keyboard and touch; the track, fill and thumb are drawn under it. The notch marks the starting number.
export function Slide({ k, label, u, step, lo, hi, v, start, tip, onChange, onHot }) {
  const part = Math.max(0, Math.min(1, (v - lo) / (hi - lo || 1))); const notch = start == null ? null : Math.max(0, Math.min(1, (start - lo) / (hi - lo || 1)));
  return <label className={`cof-row cs-row${start != null && v !== start ? ' is-moved' : ''}`} data-tip={tip} onMouseEnter={() => onHot?.()} onMouseLeave={() => onHot?.(true)} data-testid={`cof-${k}`}>
    <span className="cs-name">{label}</span><Roll v={v} fmt={x => asText(step < 1 ? Math.round(x * 10) / 10 : Math.round(x), u)} />
    <span className="cs-track"><i className="cs-rail" aria-hidden="true"><motion.u initial={false} animate={{ scaleX: part }} /></i>{notch != null ? <em className="cs-notch" style={{ left: `${notch * 100}%` }} aria-hidden="true" /> : null}<motion.span className="cs-run" initial={false} animate={{ x: `${part * 100}%` }} aria-hidden="true"><i className="cs-thumb" /></motion.span>
      <input type="range" min={lo} max={hi} step={step} value={v} aria-label={label} onChange={e => onChange(Number(e.target.value))} /></span></label>;
}
const PLAN_C = { week: ['1 week', '#57c7ff'], month: ['30 days', '#3ee58a'], quarter: ['90 days', '#c58bff'] };
// 📈 How fast money comes back on each plan. One axis: percent of what locked. Drawn from the settings as they stand.
export function BackCurves({ c }) {
  const [at, setAt] = useState(null); const W = 600, H = 170, L = 34, B = 22, T = 8; const maxD = Math.max(c.weekDays, c.monthDays, c.quarterDays, 7);
  const X = d => L + (d / maxD) * (W - L - 8); const Y = p => T + (1 - p / 100) * (H - T - B);
  const plans = Object.keys(PLAN_C).map(n => ({ n, days: c[`${n}Days`], back: c[`${n}Back`] })); const val = (p, d) => p.back * Math.min(1, d / Math.max(1, p.days));
  const hover = e => { const r = e.currentTarget.getBoundingClientRect(); const x = ((e.clientX - r.left) / r.width) * W; setAt(Math.max(0, Math.min(maxD, Math.round(((x - L) / (W - L - 8)) * maxD)))); };
  return <figure className="cs-chart" data-testid="cs-curves"><figcaption><b>When it comes back</b><small>Share of what locked, by day</small></figcaption>
    <div className="cs-legend">{plans.map(p => <span key={p.n}><i style={{ background: PLAN_C[p.n][1] }} />{PLAN_C[p.n][0]} · <em className="m-num">{at == null ? `${p.back}%` : `${val(p, at).toFixed(0)}%`}</em></span>)}<span className="cs-at m-num">{at == null ? 'Hover the chart' : `Day ${at}`}</span></div>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="How fast each plan pays back" onMouseMove={hover} onMouseLeave={() => setAt(null)}>
      {[0, 50, 100].map(p => <g key={p}><line x1={L} x2={W - 8} y1={Y(p)} y2={Y(p)} className="cs-grid" /><text x={L - 6} y={Y(p) + 3} textAnchor="end" className="cs-tick">{p}%</text></g>)}
      {[0, Math.round(maxD / 2), maxD].map(d => <text key={d} x={X(d)} y={H - 6} textAnchor="middle" className="cs-tick">{d}d</text>)}
      {plans.map(p => <motion.path key={p.n} fill="none" stroke={PLAN_C[p.n][1]} strokeWidth="2" strokeLinecap="round" initial={false} animate={{ d: `M${X(0)} ${Y(0)} L${X(Math.min(p.days, maxD))} ${Y(p.back)} L${X(maxD)} ${Y(p.back)}` }} />)}
      {at != null ? <g><line x1={X(at)} x2={X(at)} y1={T} y2={H - B} className="cs-cross" />{plans.map(p => <circle key={p.n} cx={X(at)} cy={Y(val(p, at))} r="4" fill={PLAN_C[p.n][1]} stroke="#071022" strokeWidth="2" />)}</g> : null}
    </svg></figure>;
}
const PART = [['back', 'Back to the agent', '#3ee58a'], ['later', 'Collective, as it comes back', '#2f7fd6'], ['now', 'Collective, right away', '#57c7ff'], ['vault', 'In the Vault for good', '#c58bff']];
export function splitFor(c) {
  const now = c.skimPct; const lock = 100 - now;
  return [...Object.keys(PLAN_C).map(n => ({ n, name: PLAN_C[n][0], now, back: lock * c[`${n}Back`] / 100, later: lock * (100 - c[`${n}Back`]) / 100, vault: 0 })), { n: 'vault', name: 'Vault', now, back: 0, later: 0, vault: lock }];
}
// ▤ Where a $100 send goes on each plan.
export function DollarBars({ c }) {
  return <figure className="cs-chart" data-testid="cs-bars"><figcaption><b>Where $100 goes</b><small>On each plan, with these settings</small></figcaption>
    <div className="cs-legend">{PART.map(([k, l, col]) => <span key={k}><i style={{ background: col }} />{l}</span>)}</div>
    <ul className="cs-bars">{splitFor(c).map(r => { let run = 0; return <li key={r.n}><small>{r.name}</small><span className="cs-stack">{PART.map(([k, l, col]) => { const v = r[k]; const left = run; run += v; return <motion.i key={k} initial={false} animate={{ x: `${left}%`, scaleX: v / 100 }} style={{ background: col }} data-tip={`${l}: ${money(v)}`} />; })}</span><em className="m-num">{r.n === 'vault' ? `${money(r.vault)} vault` : `${money(r.back)} back`}</em></li>; })}</ul></figure>;
}
const clampTo = (b, v) => Math.max(b[0], Math.min(b[1], v));
// Three starting points. Each only moves the numbers that matter, and nothing is saved until you press save.
export const PRESETS = [
  { k: 'collective', name: 'Grow the Collective', line: 'Keeps more now. Smaller returns for members.', move: { skimPct: 5, weekBack: -5, monthBack: -5, quarterBack: -3, potPct: -10 } },
  { k: 'start', name: 'Balanced', line: 'The starting numbers.', move: {} },
  { k: 'members', name: 'Pull in members', line: 'More comes back and more goes to the fee pot.', move: { skimPct: -5, weekBack: 5, monthBack: 5, quarterBack: 3, potPct: 10, sitePct: 5 } },
];
export function presetCfg(p, d) { const out = { ...d.defaults }; Object.entries(p.move).forEach(([k, m]) => { if (d.bounds[k]) out[k] = clampTo(d.bounds[k], d.defaults[k] + m); }); return out; }
export function Presets({ c, d, onPick }) {
  const keys = useMemo(() => [...new Set(PRESETS.flatMap(p => Object.keys(p.move)))], []); const on = PRESETS.find(p => { const t = presetCfg(p, d); return keys.every(k => t[k] === c[k]); })?.k;
  return <LayoutGroup id="cs-presets"><div className="cs-presets" role="radiogroup" aria-label="Starting points">{PRESETS.map(p => { const t = presetCfg(p, d); const lock = 100 - t.skimPct; return <button key={p.k} type="button" role="radio" aria-checked={on === p.k} className={on === p.k ? 'is-on' : ''} onClick={() => onPick(t)} data-tip={`Sets the sliders to this. Nothing changes until you save. ${p.line}`} data-testid={`cs-preset-${p.k}`}>{on === p.k ? <motion.i layoutId="ring" aria-hidden="true" /> : null}<b>{p.name}</b><small>{p.line}</small>
    <span className="cs-pre-n"><span><em className="m-num">{money(t.skimPct)}</em><small>Kept per $100</small></span><span><em className="m-num">{money(lock * t.monthBack / 100)}</em><small>Back in 30 days</small></span><span><em className="m-num">{t.potPct}%</em><small>Fees to the pot</small></span></span></button>; })}</div></LayoutGroup>;
}
const QUOTE_RULES = { SOL: 'SOL', USDC: 'USDC' };
const RECIPES = [
  { k: 'fee-sol', a: 'FEE', q: 'SOL', name: 'FEE and SOL', line: 'The usual home for a coin. Buyers and sellers pay the pool on every trade.' },
  { k: 'fee-usdc', a: 'FEE', q: 'USDC', name: 'FEE and USDC', line: 'Priced in dollars, so the pool does not swing with SOL.' },
  { k: 'sol-usdc', a: 'SOL', q: 'USDC', name: 'SOL and USDC', line: 'Needs no coin of ours. Bigger pools exist, so little trading may reach this one.' },
  { k: 'other', a: '', q: 'SOL', name: 'Another coin', line: 'Paste any coin address and pick SOL or USDC.' },
];
const FEES = [[25, '0.25%'], [100, '1%'], [200, '2%'], [500, '5%']];
// 🌊 Open a pool in 3 steps. The server builds the real transaction and simulates it for free; the create button only wakes after a clean simulation of exactly these choices.
export function PoolBuilder({ d, act, busy }) {
  const tokens = d.poolTokens || []; const mintOf = k => tokens.find(t => t.k === k)?.mint || '';
  const [rk, setRk] = useState('fee-sol'); const [other, setOther] = useState(''); const [quote, setQuote] = useState('SOL'); const [a, setA] = useState(''); const [b, setB] = useState(''); const [fee, setFee] = useState(100); const [lock, setLock] = useState(false); const [vol, setVol] = useState(5000);
  const r = RECIPES.find(x => x.k === rk); const q = rk === 'other' ? quote : r.q; const symA = rk === 'other' ? 'Coin' : r.a; const mintA = rk === 'other' ? other.trim() : mintOf(r.a); const na = Number(a); const nb = Number(b); const dr = d.poolDraft;
  const body = { mintA, quote: q, amountA: na, amountB: nb, feeBps: fee, lock }; const ready = mintA && na > 0 && nb > 0;
  const clean = !!(dr?.ok && dr.mintA === mintA && dr.amountA === na && dr.amountB === nb && dr.feeBps === fee && dr.lock === lock && dr.mintB === mintOf(q));
  const simWord = e => (String(e).includes('AccountNotFound') ? 'The Pool wallet has no SOL yet. Fund it first.' : /insufficient/i.test(String(e)) ? 'The Pool wallet does not hold these amounts.' : String(e).slice(0, 110));
  if (d.pool) return <section className="cs-pool" data-testid="colony-pool-open"><h5><Ic3 e="🌊" /> THE COLLECTIVE'S POOL <em>OPEN · {d.pool.platform}</em></h5><code>{d.pool.address}</code><small>{d.pool.amountA != null ? `${Number(d.pool.amountA).toLocaleString()} + ${d.pool.amountB}` : `${d.pool.feecat?.toLocaleString()} FEECAT + ${d.pool.sol} SOL`}{d.pool.lock ? ' · locked' : ' · unlocked'}</small></section>;
  return <Fx><section className="cs-pool" data-testid="colony-pool"><h5><Ic3 e="🌊" /> OPEN A POOL <em>Meteora · not open</em></h5>
    <figure className="cs-pooldiag" aria-hidden="true"><svg viewBox="0 0 560 96">
      <g className="cs-pd-box"><rect x="4" y="10" width="112" height="32" rx="9" /><text x="60" y="30" textAnchor="middle">{symA}</text><rect x="4" y="54" width="112" height="32" rx="9" /><text x="60" y="74" textAnchor="middle">{q}</text></g>
      <path d="M116 26 C160 26 160 48 214 48 M116 70 C160 70 160 48 214 48" className="cs-pd-line" />
      <g className="cs-pd-pool"><rect x="214" y="18" width="132" height="60" rx="14" /><text x="280" y="44" textAnchor="middle">The pool</text><text x="280" y="62" textAnchor="middle" className="cs-pd-sub">{(fee / 100).toFixed(2)}% per trade</text></g>
      <path d="M346 48 H444" className="cs-pd-line" /><g className="cs-pd-box"><rect x="444" y="30" width="112" height="36" rx="9" /><text x="500" y="52" textAnchor="middle">Traders</text></g>
      <motion.circle r="4" cx="444" cy="48" className="cs-pd-dot" initial={{ cx: 444 }} animate={lite() ? false : { cx: [444, 346] }} transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }} />
    </svg></figure>
    <ol className="cs-steps">
      <li><h6>1 · What goes in</h6><div className="cs-recipes" role="radiogroup" aria-label="Pair">{RECIPES.map(x => <button key={x.k} type="button" role="radio" aria-checked={rk === x.k} className={rk === x.k ? 'is-on' : ''} onClick={() => setRk(x.k)} data-tip={x.line} data-testid={`colony-pair-${x.k}`}><b>{x.name}</b><small>{x.line}</small></button>)}</div>
        {rk === 'other' ? <div className="cs-other"><input className="m-input" value={other} onChange={e => setOther(e.target.value)} placeholder="Coin address" aria-label="Coin address" spellCheck="false" data-testid="colony-pool-mint" /><span className="m-seg" role="group" aria-label="Pair it with">{Object.keys(QUOTE_RULES).map(k => <button key={k} type="button" aria-pressed={quote === k} className={quote === k ? 'active' : ''} onClick={() => setQuote(k)} data-tip={`Pair it with ${k}`} data-testid={`colony-quote-${k}`}>{k}</button>)}</span></div> : null}</li>
      <li><h6>2 · How much, and the fee</h6><div className="cs-amts"><label><small>{symA}</small><input className="m-input m-num" inputMode="decimal" value={a} onChange={e => setA(e.target.value)} placeholder="0" aria-label={`${symA} to put in`} data-testid="colony-pool-a" /></label><label><small>{q}</small><input className="m-input m-num" inputMode="decimal" value={b} onChange={e => setB(e.target.value)} placeholder="0" aria-label={`${q} to put in`} data-testid="colony-pool-b" /></label>
        <span className="cs-amt-seg"><small>Fee per trade</small><span className="m-seg" role="group" aria-label="Fee per trade">{FEES.map(([v, l]) => <button key={v} type="button" aria-pressed={fee === v} className={fee === v ? 'active' : ''} onClick={() => setFee(v)} data-tip={`Traders pay ${l} on each trade through this pool`} data-testid={`colony-fee-${v}`}>{l}</button>)}</span></span>
        <span className="cs-amt-seg"><small>Can it come back out</small><span className="m-seg" role="group" aria-label="Lock">{[[false, 'Unlocked'], [true, 'Locked for good']].map(([v, l]) => <button key={l} type="button" aria-pressed={lock === v} className={lock === v ? 'active' : ''} onClick={() => setLock(v)} data-tip={v ? 'The money can never be taken out of the pool' : 'You can take the money back out later'} data-testid={`colony-lock-${v ? 'on' : 'off'}`}>{l}</button>)}</span></span></div>
        <div className="cs-est"><Slide k="pool-vol" label="If this much trades a day" u="$" step={500} lo={500} hi={100000} v={vol} tip="Your guess. Nobody promises any trading" onChange={setVol} /><span className="cs-est-n" data-tip="What trades a day × the fee. Real only if that much really trades"><small>Pool earns about</small><Roll v={vol * fee / 10000} fmt={x => `$${x.toFixed(0)}/day`} /></span></div>
        {na > 0 && nb > 0 ? <small className="cs-px m-num" data-testid="colony-pool-px">Starts at {(nb / na).toPrecision(3)} {q} per {symA}</small> : null}<small className="cs-risk">If the price moves, the pool ends up holding more of whichever side fell.</small></li>
      <li><h6>3 · Check it, then open it</h6><div className="cs-go"><button type="button" className="m-btn" disabled={!!busy || !ready} onClick={() => act('pool_preview', body)} data-tip="Builds the real transaction and simulates it on Solana. Free. Nothing signed or sent" data-testid="colony-pool-preview">{busy === 'pool_preview' ? 'Simulating…' : 'Preview (free)'}</button>
        <button type="button" className="m-btn m-go" disabled={!!busy || !clean} onClick={() => window.confirm(`Open this pool on Meteora with ${na.toLocaleString()} ${symA} + ${nb} ${q} from the Pool wallet? ${lock ? 'It is LOCKED: the money can never come back out.' : 'It stays unlocked.'}`) && act('pool_create', body)} data-tip="Only after a clean preview of exactly these choices. Circle signs as the Pool wallet, and it is sent" data-testid="colony-pool-create">{busy === 'pool_create' ? 'Opening…' : 'Open the pool'}</button></div>
        {dr ? <small className={`cs-sim ${dr.ok ? 'is-ok' : 'is-bad'}`} data-testid="colony-pool-sim">{dr.ok ? (clean ? '✓ Simulation passed for these choices.' : 'You changed something. Preview again.') : `✗ ${simWord(dr.err)}`}</small> : null}</li>
    </ol></section></Fx>;
}
