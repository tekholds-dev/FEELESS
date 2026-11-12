import React, { useEffect, useRef, useState } from 'react';
import { MotionConfig, animate, motion } from 'motion/react';
import { Ic3 } from '../../lib/icon3d';
import { money } from './SplitFlow';
import '../../styles/collectiveSetup.css';
import { twoTap } from '../ActBtn';

// 🎛 THE COLLECTIVE'S CONTROLS (owner 2026-11-05): built on Motion. Springs on real numbers, shared-layout tabs, charts drawn from the settings as they are now. Transform and opacity only.
export const SPRING = { type: 'spring', stiffness: 380, damping: 34, mass: 0.7 };
const lite = () => typeof document !== 'undefined' && document.body.classList.contains('fx-lite');
export function Fx({ children }) { return <MotionConfig reducedMotion="user" transition={lite() ? { duration: 0 } : SPRING}>{children}</MotionConfig>; }

// A number that rolls to its new value, written straight to the element so nothing re-renders.
export function Roll({ v, fmt = String, className = 'm-num', testid }) {
  const el = useRef(null); const from = useRef(v);
  useEffect(() => { if (lite() || from.current === v) { if (el.current) el.current.textContent = fmt(v); from.current = v; return undefined; } const c = animate(from.current, v, { duration: 0.35, ease: 'easeOut', onUpdate: x => { if (el.current) el.current.textContent = fmt(x); }, onComplete: () => { from.current = v; } }); return () => c.stop(); }, [v, fmt]);
  return <b ref={el} className={className} data-testid={testid}>{fmt(v)}</b>;
}
// One setting: a number you type, with its place in the range and a notch at the starting number under it. No slider walls.
export function NumCell({ k, label, u = '', step = 1, lo, hi, v, start, onChange, compact = false, tip }) {
  const [text, setText] = useState(String(v)); useEffect(() => setText(String(v)), [v]);
  const part = Math.max(0, Math.min(1, (v - lo) / (hi - lo || 1))); const notch = start == null ? null : Math.max(0, Math.min(1, (start - lo) / (hi - lo || 1)));
  const edit = e => { setText(e.target.value); const n = Number(e.target.value); if (e.target.value !== '' && Number.isFinite(n) && n >= lo && n <= hi) onChange(n); };
  return <span className={`cs-num${start != null && v !== start ? ' is-moved' : ''}${compact ? ' is-compact' : ''}`} data-tip={tip} data-testid={`cof-${k}`}><span className="cs-num-in">{u === '$' ? <i>$</i> : null}<input className="m-num" type="number" min={lo} max={hi} step={step} value={text} onChange={edit} onBlur={() => setText(String(v))} aria-label={label} />{u && u !== '$' ? <i>{u}</i> : null}</span>
    <span className="cs-rail" aria-hidden="true"><motion.u initial={false} animate={{ scaleX: part }} />{notch != null ? <em style={{ left: `${notch * 100}%` }} /> : null}</span></span>;
}
// Three starting points. Each only moves the numbers that matter, and nothing is saved until you press save.
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
  const [again, setAgain] = useState(false); const r = RECIPES.find(x => x.k === rk); const q = rk === 'other' ? quote : r.q; const symA = rk === 'other' ? 'Coin' : r.a; const mintA = rk === 'other' ? other.trim() : mintOf(r.a); const na = Number(a); const nb = Number(b); const dr = d.poolDraft;
  const body = { mintA, quote: q, amountA: na, amountB: nb, feeBps: fee, lock, name: `${symA}-${q}` }; const ready = mintA && na > 0 && nb > 0;
  const clean = !!(dr?.ok && dr.mintA === mintA && dr.amountA === na && dr.amountB === nb && dr.feeBps === fee && dr.lock === lock && dr.mintB === mintOf(q));
  const simWord = e => (String(e).includes('AccountNotFound') ? 'The Pool wallet has no SOL yet. Fund it first.' : /insufficient/i.test(String(e)) ? 'The Pool wallet does not hold these amounts.' : String(e).slice(0, 110));
  if (d.pool && !again) return <section className="cs-pool" data-testid="colony-pool-open"><h5><Ic3 e="🌊" /> THE COLLECTIVE'S POOL <em>OPEN · {d.pool.platform}</em></h5><code>{d.pool.address}</code><small>{d.pool.amountA != null ? `${Number(d.pool.amountA).toLocaleString()} + ${d.pool.amountB}` : `${d.pool.feecat?.toLocaleString()} FEECAT + ${d.pool.sol} SOL`}{d.pool.lock ? ' · locked' : ' · unlocked'}</small><button type="button" className="m-btn" onClick={() => setAgain(true)} data-tip="Build another with the same checks. Each one gets its own desktop folder" data-testid="colony-pool-again">Open another pool</button></section>;
  return <Fx><section className="cs-pool" data-testid="colony-pool"><h5><Ic3 e="🌊" /> OPEN A POOL <em>Meteora · {d.pool ? 'another one' : 'not open'}</em></h5>
    <ol className="cs-steps">
      <li><h6>1 · What goes in</h6><div className="cs-recipes" role="radiogroup" aria-label="Pair">{RECIPES.map(x => <button key={x.k} type="button" role="radio" aria-checked={rk === x.k} className={rk === x.k ? 'is-on' : ''} onClick={() => setRk(x.k)} data-tip={x.line} data-testid={`colony-pair-${x.k}`}><b>{x.name}</b><small>{x.line}</small></button>)}</div>
        {rk === 'other' ? <div className="cs-other"><input className="m-input" value={other} onChange={e => setOther(e.target.value)} placeholder="Coin address" aria-label="Coin address" spellCheck="false" data-testid="colony-pool-mint" /><span className="m-seg" role="group" aria-label="Pair it with">{Object.keys(QUOTE_RULES).map(k => <button key={k} type="button" aria-pressed={quote === k} className={quote === k ? 'active' : ''} onClick={() => setQuote(k)} data-tip={`Pair it with ${k}`} data-testid={`colony-quote-${k}`}>{k}</button>)}</span></div> : null}</li>
      <li><h6>2 · How much, and the fee</h6><div className="cs-amts"><label><small>{symA}</small><input className="m-input m-num" inputMode="decimal" value={a} onChange={e => setA(e.target.value)} placeholder="0" aria-label={`${symA} to put in`} data-testid="colony-pool-a" /></label><label><small>{q}</small><input className="m-input m-num" inputMode="decimal" value={b} onChange={e => setB(e.target.value)} placeholder="0" aria-label={`${q} to put in`} data-testid="colony-pool-b" /></label>
        <span className="cs-amt-seg"><small>Fee per trade</small><span className="m-seg" role="group" aria-label="Fee per trade">{FEES.map(([v, l]) => <button key={v} type="button" aria-pressed={fee === v} className={fee === v ? 'active' : ''} onClick={() => setFee(v)} data-tip={`Traders pay ${l} on each trade through this pool`} data-testid={`colony-fee-${v}`}>{l}</button>)}</span></span>
        <span className="cs-amt-seg"><small>Can it come back out</small><span className="m-seg" role="group" aria-label="Lock">{[[false, 'Unlocked'], [true, 'Locked for good']].map(([v, l]) => <button key={l} type="button" aria-pressed={lock === v} className={lock === v ? 'active' : ''} onClick={() => setLock(v)} data-tip={v ? 'The money can never be taken out of the pool' : 'You can take the money back out later'} data-testid={`colony-lock-${v ? 'on' : 'off'}`}>{l}</button>)}</span></span></div>
        <div className="cs-est"><span className="cs-amt-seg"><small>If this much trades a day</small><span className="m-seg" role="group" aria-label="Trades a day">{[1000, 5000, 25000, 100000].map(v => <button key={v} type="button" aria-pressed={vol === v} className={vol === v ? 'active' : ''} onClick={() => setVol(v)} data-tip="Your guess. Nobody promises any trading" data-testid={`colony-vol-${v}`}>${v >= 1000 ? `${v / 1000}K` : v}</button>)}</span></span><span className="cs-est-n" data-tip="What trades a day × the fee. Real only if that much really trades"><small>Pool earns about</small><Roll v={vol * fee / 10000} fmt={x => `$${x.toFixed(0)}/day`} /></span></div>
        {na > 0 && nb > 0 ? <small className="cs-px m-num" data-testid="colony-pool-px">Starts at {(nb / na).toPrecision(3)} {q} per {symA}</small> : null}<small className="cs-risk">If the price moves, the pool ends up holding more of whichever side fell.</small></li>
      <li><h6>3 · Check it, then open it</h6><div className="cs-go"><button type="button" className="m-btn" disabled={!!busy || !ready} onClick={() => act('pool_preview', body)} data-tip="Builds the real transaction and simulates it on Solana. Free. Nothing signed or sent" data-testid="colony-pool-preview">{busy === 'pool_preview' ? 'Simulating…' : 'Preview (free)'}</button>
        <button type="button" className="m-btn m-go" disabled={!!busy || !clean} onClick={() => twoTap(`Open this pool on Meteora with ${na.toLocaleString()} ${symA} + ${nb} ${q} from the Pool wallet? ${lock ? 'It is LOCKED: the money can never come back out.' : 'It stays unlocked.'}`) && act('pool_create', body)} data-tip="Only after a clean preview of exactly these choices. Circle signs as the Pool wallet, and it is sent" data-testid="colony-pool-create">{busy === 'pool_create' ? 'Opening…' : 'Open the pool'}</button></div>
        {dr ? <small className={`cs-sim ${dr.ok ? 'is-ok' : 'is-bad'}`} data-testid="colony-pool-sim">{dr.ok ? (clean ? '✓ Simulation passed for these choices.' : 'You changed something. Preview again.') : `✗ ${simWord(dr.err)}`}</small> : null}</li>
    </ol></section></Fx>;
}
