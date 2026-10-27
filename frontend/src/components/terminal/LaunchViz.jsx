import React, { memo, useMemo } from 'react';
import '../../styles/launchViz.css';

// 🚀 THE LAUNCH, DRAWN (owner, 2026-10-23: "Launch: every process step lit-styled — drawn, live, animated, no dead forms"; Launch = the official
// logo green on near-black). Visuals only — nothing here signs, sends or changes the launch form:
// · LaunchStage — the bonding curve your settings make (open → graduation), a light running up it, the graduation line + locked pool, and a
//   drawn rocket that RIDES the curve as you move through the steps (Identity → Economics → Protection → Review).
// · StepRing — each step's lit completion ring (how many of its boxes are filled and valid).
// · FeeDonut — where every swap fee goes as a lit ring + what each side earns per $10K of volume, live as you type.
// · SnipeDecay — the opening buy tax drawn as it falls to 0 over the protection window, the sniper's overpay marked.
// · CoinFace — the coin as a drawn minted face (rim, art or initials, the ticker engraved) with a light sweep.
// transform / opacity motion only (one keyframe set `lv*`), paused off-screen (.lv-stage is an fxPause surface), still under fx-lite +
// reduced motion; day theme + 640 px in styles/launchViz.css.

const W = 640; const H = 210; const PADX = 46; const TOP = 34; const BASE = 168;
const n = v => { const x = Number(v); return Number.isFinite(x) ? x : 0; };
const STABLE = ['USDC', 'USDT', 'USD1', 'PYUSD'];
const SOLISH = ['SOL', 'JITOSOL', 'MSOL', 'JUPSOL'];
export const money = v => { const x = n(v); return !x ? '$0' : x >= 1e6 ? `$${(x / 1e6).toFixed(1)}M` : x >= 1e3 ? `$${(x / 1e3).toFixed(x >= 1e4 ? 0 : 1)}K` : x >= 1 ? `$${x.toFixed(x >= 100 ? 0 : 2)}` : `$${x.toFixed(3)}`; };

// pure: the launch's two ends in display words — the opening valuation and the graduation target (+ ≈ $ when the quote is SOL-like or a stable)
export function launchEnds(form, { rail = null, locked = false, solPx = 0, pump = false } = {}) {
  if (pump) return { open: 'pump.fun curve', openUsd: null, grad: 'PumpSwap', gradUsd: null, ratio: null, curve: 'exponential', pump: true };   // pump.fun sets its own curve
  if (locked && rail?.params) {
    const unit = rail.params.quote === 'USDC' ? 'USDC' : 'SOL'; const px = unit === 'USDC' ? 1 : solPx;
    const o = n(rail.params.initialMarketCap ?? 30); const g = n(rail.params.migrationMarketCap ?? 500);
    return { open: `${o} ${unit}`, openUsd: px ? o * px : null, grad: `${g} ${unit} MC`, gradUsd: px ? g * px : null, ratio: g / Math.max(1e-9, o), curve: 'exponential' };
  }
  const pair = String(form?.liquidityPair || 'SOL').toUpperCase(); const px = STABLE.includes(pair) ? 1 : SOLISH.includes(pair) ? solPx : 0;
  const g = n(form?.graduationTarget);
  return { open: `$${n(form?.openingMarketCap)}K`, openUsd: null, grad: `${g} ${form?.liquidityPair || 'SOL'}`, gradUsd: px ? g * px : null, ratio: null,
    curve: form?.curveType === 'exponential' ? 'exponential' : 'linear' };
}

// pure: N points of the curve in the stage's frame — x = share of the curve sold, y = price (linear steps or exponential discovery)
export function curvePts(curve = 'linear', N = 28) {
  return Array.from({ length: N }, (_, i) => {
    const t = i / (N - 1);
    const y = curve === 'exponential' ? (Math.exp(2.6 * t) - 1) / (Math.exp(2.6) - 1) : t;
    return [PADX + t * (W - PADX * 2), BASE - 12 - y * (BASE - TOP - 22)];
  });
}
const STEP_AT = { 1: 0.12, 2: 0.46, 3: 0.78, 4: 0.97 };

export const LaunchStage = memo(function LaunchStage({ form, rail, locked, pump = false, solPx, step = 1 }) {
  const e = launchEnds(form, { rail, locked, solPx, pump });
  const pts = useMemo(() => curvePts(e.curve), [e.curve]);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
  const at = STEP_AT[step] ?? 0.12; const k = Math.min(pts.length - 2, Math.floor(at * (pts.length - 1)));
  const [x0, y0] = pts[k]; const [x1, y1] = pts[k + 1]; const f = at * (pts.length - 1) - k;
  const rx = x0 + (x1 - x0) * f; const ry = y0 + (y1 - y0) * f; const ang = (Math.atan2(y1 - y0, x1 - x0) * 180) / Math.PI;
  const nodes = pump ? [['IDENTITY', 'name · art'], ['LAUNCH', 'first buy · you sign once']] : [['IDENTITY', 'name · art'], ['CURVE', 'supply · fees'], ['SHIELD', 'anti-snipe · locks'], ['LAUNCH', 'you sign once']];   // pump.fun: 2 steps, like the form
  return <div className="lv-stage" data-testid="launch-stage" aria-label={`Launch curve: opens at ${e.open}, graduates at ${e.grad}`}>
    <span className="lv-stars" aria-hidden="true" /><span className="lv-sweep" aria-hidden="true" />
    <svg viewBox={`0 0 ${W} ${H}`} className="lv-svg" aria-hidden="true">
      <defs>
        <linearGradient id="lvFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#15d16a" stopOpacity=".32" /><stop offset="1" stopColor="#15d16a" stopOpacity="0" /></linearGradient>
        <linearGradient id="lvLine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#0f5c32" /><stop offset=".55" stopColor="#15d16a" /><stop offset="1" stopColor="#45e486" /></linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map(t => <line key={t} x1={PADX} x2={W - PADX} y1={TOP + t * (BASE - TOP)} y2={TOP + t * (BASE - TOP)} className="lv-grid" />)}
      <line x1={PADX} x2={W - PADX} y1={BASE} y2={BASE} className="lv-axis" />
      <line x1={PADX} x2={W - PADX} y1={TOP} y2={TOP} className="lv-grad" />
      <path d={`${d} L${W - PADX} ${BASE} L${PADX} ${BASE} Z`} fill="url(#lvFill)" />
      <path d={d} className="lv-curve" stroke="url(#lvLine)" />
      <g className="lv-comet">{pts.filter((_, i) => i % 2 === 0).map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r="2.6" style={{ '--i': i }} />)}</g>
      <g className="lv-pool" transform={`translate(${W - PADX - 4} ${TOP - 4})`}><rect x="-26" y="-14" width="30" height="18" rx="4" /><path d="M-19 -14 v-5 a4 4 0 0 1 8 0 v5" /></g>
      <circle cx={pts[0][0]} cy={pts[0][1]} r="4.5" className="lv-open" />
      <g className="lv-rocket" style={{ transform: `translate(${rx}px, ${ry}px) rotate(${ang - 90}deg)` }}>
        <path d="M0 -15 C6 -9 6 3 4 8 L-4 8 C-6 3 -6 -9 0 -15 Z" className="lv-rk-body" /><circle cx="0" cy="-4" r="2.4" className="lv-rk-win" />
        <path d="M-4 3 L-9 10 L-4 8 Z M4 3 L9 10 L4 8 Z" className="lv-rk-fin" /><path d="M-3 9 L0 19 L3 9 Z" className="lv-rk-flame" />
      </g>
    </svg>
    <span className="lv-tag is-open"><em>OPENS</em><b>{e.open}</b>{e.openUsd ? <small>{money(e.openUsd)}</small> : null}</span>
    <span className="lv-tag is-grad"><em>GRADUATES</em><b>{e.grad}</b>{e.gradUsd ? <small>≈ {money(e.gradUsd)}</small> : null}<u>→ LOCKED POOL</u></span>
    <span className="lv-shape">{e.curve === 'exponential' ? '📈 EXPONENTIAL · fast price discovery' : '📐 LINEAR · predictable steps'}{locked ? ' · set by the rail' : e.pump ? ' · set by pump.fun' : ''}</span>
    <ol className="lv-nodes">{nodes.map(([t, s], i) => <li key={t} className={`${step > i + 1 ? 'is-done' : ''} ${step === i + 1 ? 'is-now' : ''}`} style={{ '--i': i }}><i>{step > i + 1 ? '✓' : i + 1}</i><span><b>{t}</b><small>{s}</small></span></li>)}</ol>
  </div>;
});

// pure: how far a step's boxes are filled (0–1) — required boxes filled and none of the step's keys in `errors`
export function stepFill(form, step, errors = {}) {
  const has = k => String(form?.[k] ?? '').trim() !== '';
  const keys = step === 1 ? ['name', 'symbol', 'imageUrl', 'description'] : step === 2 ? ['supply', 'openingMarketCap', 'graduationTarget', 'swapFee', 'liquidityPair'] : ['antiSniperWindow', 'antiSniperTax', 'providerId', 'lockDurationMinutes'];
  const bad = Object.keys(errors || {}).filter(k => keys.includes(k)).length;
  return Math.max(0, (keys.filter(has).length - bad) / keys.length);
}
const RC = 2 * Math.PI * 15;
export function StepRing({ fill = 0, n: num, done }) {
  return <i className={`lv-ring ${fill >= 1 ? 'is-full' : ''}`} data-testid={`step-ring-${num}`} aria-hidden="true">
    <svg viewBox="0 0 36 36"><circle cx="18" cy="18" r="15" className="t" /><circle cx="18" cy="18" r="15" className="a" strokeDasharray={`${(Math.max(0.02, fill) * RC).toFixed(1)} ${RC.toFixed(1)}`} /></svg>
    <b>{done ? '✓' : num}</b></i>;
}

// 🍩 where every swap fee goes: the split as a lit ring + each side's take per $10K of volume
const SIDES = [['creatorFeeShare', 'CREATOR', '#45e486'], ['referralShare', 'REFERRAL', '#8fd8ff'], ['holderRewardShare', 'HOLDERS', '#ffd36b'], ['buybackBurnShare', 'BUYBACK + BURN', '#ff8f6b']];
export function feeSplit(form, volume = 10000) {
  const fee = n(form?.swapFee) / 100; let at = 0;
  const parts = SIDES.map(([k, label, color]) => { const pct = n(form?.[k]); const p = { k, label, color, pct, from: at, usd: volume * fee * (pct / 100) }; at += pct; return p; });
  return { parts, total: Math.round(at * 10) / 10, perVol: volume * fee };
}
export function FeeDonut({ form }) {
  const { parts, total, perVol } = feeSplit(form); const R = 42; const C = 2 * Math.PI * R;
  return <div className={`lv-fees ${total === 100 ? 'is-ok' : 'is-off'}`} data-testid="fee-donut">
    <svg viewBox="0 0 110 110" className="lv-donut" aria-hidden="true"><circle cx="55" cy="55" r={R} className="t" />
      {parts.filter(p => p.pct > 0).map((p, i) => <circle key={p.k} cx="55" cy="55" r={R} className="seg" stroke={p.color} style={{ '--i': i }}
        strokeDasharray={`${Math.max(0, (Math.min(p.pct, 100 - Math.min(100, p.from)) / 100) * C - 1.5).toFixed(1)} ${C.toFixed(1)}`} strokeDashoffset={(-(p.from / 100) * C).toFixed(1)} transform="rotate(-90 55 55)" />)}
    </svg>
    <span className="lv-donut-mid"><b>{total}%</b><small>{total === 100 ? 'ROUTED' : 'MUST = 100'}</small></span>
    <ul className="lv-fee-legend">{parts.map((p, i) => <li key={p.k} style={{ '--c': p.color, '--i': i }}><i /><span>{p.label}</span><b>{p.pct}%</b>
      <em data-tip={`On $10K of trading volume at a ${form?.swapFee || 0}% swap fee`}>{money(p.usd)}<small>/ $10K vol</small></em>
      <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, p.pct / 100)})` }} /></u></li>)}</ul>
    <p className="lv-fee-foot">Every $10K traded pays <b>{money(perVol)}</b> in fees · split live as you type</p>
  </div>;
}

// ⏱ the opening protection: tax % falling to 0 over the window; bots at t = 0 pay the top of it
export function SnipeDecay({ tax, window: win }) {
  const t = Math.max(0, Math.min(100, n(tax))); const w = Math.max(0, n(win));
  if (!t || !w) return <p className="lv-snipe-off" data-testid="snipe-decay">No opening tax — the first block trades like any other (snipers welcome).</p>;
  const X = s => 30 + (s / w) * 250; const Y = p => 92 - (p / 100) * 76;
  const d = Array.from({ length: 13 }, (_, i) => { const s = (i / 12) * w; return `${i ? 'L' : 'M'}${X(s).toFixed(1)} ${Y(t * (1 - s / w)).toFixed(1)}`; }).join(' ');
  return <div className="lv-snipe" data-testid="snipe-decay">
    <svg viewBox="0 0 300 110" aria-hidden="true"><line x1="30" x2="285" y1="92" y2="92" className="lv-axis" />
      <path d={`${d} L${X(w)} 92 L30 92 Z`} className="lv-snipe-fill" /><path d={d} className="lv-snipe-line" />
      <g transform={`translate(${X(0)} ${Y(t)})`}><g className="lv-bot"><circle r="7" /><text y="3.5" textAnchor="middle">🤖</text></g></g>
      <text x={X(0) + 12} y={Y(t) - 6} className="lv-snipe-lbl">{`sniper pays ${t}%`}</text>
      <text x={X(w)} y="105" textAnchor="end" className="lv-snipe-ax">{`${w}s`}</text><text x="30" y="105" className="lv-snipe-ax">t+0</text>
    </svg>
    <span className="lv-snipe-read"><b>{t}% → 0%</b><small>over {w}s · the tax goes to holders, never a hidden wallet</small></span>
  </div>;
}

// 🪙 the coin, minted: rim + face (art or initials) + the ticker engraved, a light sweep across it
export function CoinFace({ form }) {
  const sym = String(form?.symbol || 'TICKER').toUpperCase().slice(0, 10);
  return <div className="lv-coin" data-testid="coin-face" data-tip="How your coin's face reads in every list, chart and chat on FEELESS">
    <span className="lv-coin-disc"><span className="lv-coin-face">{form?.imageUrl ? <img src={form.imageUrl} alt="" onError={e => { e.currentTarget.style.display = 'none'; }} /> : <b>{(form?.symbol || '?').slice(0, 2).toUpperCase()}</b>}</span><i className="lv-coin-shine" /></span>
    <span className="lv-coin-id"><b>{form?.name || 'Your coin'}</b><em>${sym}</em><small>{n(form?.supply) ? `${Number(form.supply).toLocaleString('en-US')} supply · fixed forever` : 'set the supply next'}</small></span>
  </div>;
}
