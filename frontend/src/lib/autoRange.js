// 🤖 AUTORANGE ENGINE (owner 2026-10-26: "not an AI — an auto ranging ENGINE"). Pure, deterministic, tested (autoRange.test.js).
// The loop: OBSERVE (real candles + the live price) → DECIDE (is a move worth more than it costs?) → the wallet signs the move → COMPOUND
// (only when the fees beat the gas) → MEASURE (real P&L) → repeat. It can PAUSE (pull to the sidelines) when the coin is too wild for any band.
// Nothing here promises profit: every "expected" number is the pool's real fee rate × the band's boost × the odds of staying in range on the
// coin's own realized volatility, and `replay` runs these exact rules over the coin's real candle history (a replay, not a forecast).

// ── concentrated-liquidity math (start price 1, band [1/k, k]) ──
export function ilRange(m, k) {   // LP value vs just holding the two coins after the price moves ×m
  const pa = 1 / k, pb = k, sp = Math.sqrt;
  const x0 = 1 - 1 / sp(pb), y0 = 1 - sp(pa);
  const v = m <= pa ? (1 / sp(pa) - 1 / sp(pb)) * m : m >= pb ? sp(pb) - sp(pa) : (1 / sp(m) - 1 / sp(pb)) * m + (sp(m) - sp(pa));
  return v / (x0 * m + y0) - 1;
}
export const rangeFactor = k => 1 / (1 - 1 / Math.sqrt(k));   // fees per $ vs a full-range pool, while in range
const erf = x => { const s = Math.sign(x); const a = Math.abs(x); const t = 1 / (1 + 0.3275911 * a);
  return s * (1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-a * a)); };

// ── the pool's real fee rate ──
export const feeTier = meta => { const m = /(\d+(?:\.\d+)?)\s*%/.exec(String(meta || '')); return m ? Number(m[1]) / 100 : null; };
// pure: $ a FULL-RANGE dollar earns per day in this pool — the pool's own volume × fee ÷ TVL (real 24h), else its APY ÷ 365
export function poolDayRate(pool) {
  const f = feeTier(pool?.meta); const v = Number(pool?.vol) || 0; const t = Number(pool?.tvl) || 0;
  if (f && v > 0 && t > 0) return { rate: (v * f) / t, src: `24h volume × ${(f * 100).toFixed(2)}% fee ÷ TVL` };
  const apy = Number(pool?.apy) || 0; return apy > 0 ? { rate: apy / 100 / 365, src: 'the pool\'s APY ÷ 365' } : { rate: 0, src: 'no fee data' };
}

// ── strategies: the band width each one may use (± %) and how long it waits out of range before it re-centers ──
export const STRATEGIES = {
  tight: { name: 'Tight', min: 2, max: 5, k: 0.6, wait: 5, tip: 'Most fees per $, leaves range the fastest' },
  balanced: { name: 'Balanced', min: 5, max: 15, k: 1.0, wait: 15, tip: 'Covers about one day of the coin\'s own swings' },
  wide: { name: 'Wide', min: 15, max: 30, k: 1.5, wait: 30, tip: 'Rarely leaves range, fewer fees per $' },
  aggressive: { name: 'Aggressive', min: 30, max: 100, k: 2.2, wait: 60, tip: 'For wild meme pools — survives big candles' },
};
export const PAUSE_VOL = 1.2;   // σ per day ≥ 120 % = no band survives it → PAUSE (sit out in the coins / stable)
const BAR_MIN = 15;

// ── observe ──
export function closes(candles) { return (candles || []).map(c => Number(Array.isArray(c) ? c[4] : c?.close)).filter(v => v > 0); }
export function realizedVol(cl, barMin = BAR_MIN) {   // σ of log returns, scaled to one day
  if (cl.length < 8) return null;
  const r = []; for (let i = 1; i < cl.length; i += 1) r.push(Math.log(cl[i] / cl[i - 1]));
  const mu = r.reduce((a, b) => a + b, 0) / r.length; const v = r.reduce((a, b) => a + (b - mu) ** 2, 0) / Math.max(1, r.length - 1);
  return Math.sqrt(v) * Math.sqrt((24 * 60) / barMin);
}
const ema = (cl, n) => { const a = 2 / (n + 1); let e = cl[0]; for (let i = 1; i < cl.length; i += 1) e = cl[i] * a + e * (1 - a); return e; };
export function marketState(cl, barMin = BAR_MIN) {
  const vol = realizedVol(cl, barMin);
  if (vol == null) return { state: 'READING', vol: null, trend: 0, momentum: 0 };
  const last = cl[cl.length - 1]; const back = cl[Math.max(0, cl.length - 9)];
  const trend = (ema(cl.slice(-60), 9) / ema(cl.slice(-60), 21) - 1) * 100; const momentum = (last / back - 1) * 100;
  const barVol = vol / Math.sqrt((24 * 60) / barMin) * 100;   // one bar's typical move, %
  const state = vol >= PAUSE_VOL ? 'WILD' : trend > barVol * 0.6 && momentum > 0 ? 'RISING' : trend < -barVol * 0.6 && momentum < 0 ? 'FALLING' : 'RANGING';
  return { state, vol, trend, momentum };
}

// ── decide ──
export const targetWidth = (vol, strat) => { const s = STRATEGIES[strat] || STRATEGIES.balanced; return Math.round(Math.max(s.min, Math.min(s.max, (vol || 0.1) * 100 * s.k)) * 10) / 10; };
// The pool's fee rate (volume × fee ÷ TVL) is what its AVERAGE LP earns — and CLMM LPs already sit in bands. So a band's edge is measured against
// a typical ±20 % LP, never against a full-range pool (that would claim ×40 at ±5 %): ±5 % ≈ ×3.6, ±20 % = ×1, ±50 % ≈ ×0.5.
export const REF_W = 20;
export const bandEdge = w => rangeFactor(1 + w / 100) / rangeFactor(1 + REF_W / 100);
export const inRangeOdds = (w, vol) => (vol > 0 ? Math.max(0, Math.min(1, erf(Math.log(1 + w / 100) / (vol * Math.SQRT2)))) : 1);   // odds the price is still inside after a day
export function dayFees(amt, rate, w, vol) { return amt * rate * bandEdge(w) * inRangeOdds(w, vol); }
// a move = the network fee + swapping about half the position back into balance (slippage + the pool fee on that swap)
export const moveCost = (amt, { gas = 0.01, slip = 0.003 } = {}) => gas + (amt / 2) * slip;

/** One engine step. s = {price, band:{lo,hi}|null, amt, rate (fees per $ per day, full range), candles, strat, outSince (ms|null), now, unclaimed}
 *  → {action, why, width, band (the band it would set), gain (24h fees at that band), cost, conf, state, compound} */
export function decide(s) {
  const cl = closes(s.candles); const ms = marketState(cl); const strat = STRATEGIES[s.strat] ? s.strat : 'balanced'; const S = STRATEGIES[strat];
  const price = Number(s.price) || cl[cl.length - 1]; const amt = Number(s.amt) || 0; const rate = Number(s.rate) || 0;
  const w = targetWidth(ms.vol, strat); const cost = moveCost(amt);
  const bias = ms.state === 'RISING' ? 0.3 : ms.state === 'FALLING' ? -0.3 : 0;   // lean the new band into the trend
  const k = 1 + w / 100; const mid = price * (1 + (bias * w) / 200);
  const next = { lo: mid / k, hi: mid * k };
  const gain = dayFees(amt, rate, w, ms.vol);
  const conf = Math.round(100 * Math.max(0.2, Math.min(0.95, 0.35 + 0.3 * Math.min(1, cl.length / 96) + 0.3 * (1 - Math.min(1, (ms.vol || 1) / PAUSE_VOL)))));
  const compound = (Number(s.unclaimed) || 0) > cost * 3;
  const out = { width: w, band: next, gain, cost, conf, state: ms.state, vol: ms.vol, compound, strat, edge: bandEdge(w) };
  if (ms.state === 'READING') return { ...out, action: 'WAIT', why: 'Reading the pool — needs 8+ candles first' };
  if (ms.state === 'WILD') return { ...out, action: 'PAUSE', why: `Too wild: it swings ~${Math.round(ms.vol * 100)}% a day — no band survives that; sit out until it calms` };
  if (!s.band) return { ...out, action: 'OPEN', why: `First band ±${w}% (${S.name}, from its own ${Math.round(ms.vol * 100)}%/day swings)${gain < cost ? ` — at $${amt} a day of fees ($${gain.toFixed(3)}) is under one move ($${cost.toFixed(3)}): more size or a busier pool pays` : ''}` };
  const { lo, hi } = s.band; const inside = price >= lo && price <= hi; const curW = (Math.sqrt(hi / lo) - 1) * 100;
  const worth = gain > cost * 1.5;
  if (!inside) {
    const waited = s.outSince ? (s.now - s.outSince) / 60000 : 0;
    if (!worth) return { ...out, action: 'HOLD', why: `Out of range, but a move ($${cost.toFixed(3)}) costs more than a day of fees would pay back` };
    if (waited < S.wait) return { ...out, action: 'HOLD', why: `Out of range — waits ${Math.ceil(S.wait - waited)} more min in case it comes back (no paying for a wick)` };
    return { ...out, action: 'RECENTER', why: `Out of range ${Math.round(waited)} min — re-centers ±${w}% on the live price${bias ? (bias > 0 ? ', leaning up with the trend' : ', leaning down with the trend') : ''}` };
  }
  const edge = Math.min(price / lo - 1, hi / price - 1) / Math.max(1e-9, hi / lo - 1);
  const towardTop = hi / price < price / lo;
  if (edge < 0.12 && worth && ((towardTop && ms.state === 'RISING') || (!towardTop && ms.state === 'FALLING')))
    return { ...out, action: ms.state === 'RISING' ? 'SHIFT UP' : 'SHIFT DOWN', why: `Near the ${towardTop ? 'top' : 'bottom'} edge and ${ms.state.toLowerCase()} — moves the band before it leaves` };
  if (worth && curW > w * 1.7) return { ...out, action: 'TIGHTEN', why: `Calmer than the band: ±${curW.toFixed(1)}% → ±${w}% earns ×${(bandEdge(w) / bandEdge(curW)).toFixed(1)} more per $` };
  if (worth && curW < w * 0.55) return { ...out, action: 'WIDEN', why: `Swings outgrew the band: ±${curW.toFixed(1)}% → ±${w}% so it stops falling out` };
  return { ...out, action: 'HOLD', why: 'In range and earning — no move pays for itself right now' };
}

/** 🔁 REPLAY these exact rules over real candles: start $amt, a band from the first day's vol, earn fees only while a close sits inside,
 *  re-center after the strategy's wait (paying `moveCost` and booking the IL of the band it leaves). → the honest result + the path for the chart. */
export function replay(candles, { amt = 5, rate = 0, strat = 'balanced', barMin = BAR_MIN } = {}) {
  const cl = closes(candles); if (cl.length < 24) return null;
  const S = STRATEGIES[strat] || STRATEGIES.balanced; const perBar = barMin / (24 * 60);
  let val = amt; let fees = 0; let costs = 0; let il = 0; let drift = 0; let moves = 0; let inBars = 0; let outBars = 0; let paused = 0;
  const warm = 16; const vol0 = realizedVol(cl.slice(0, warm), barMin); let w = targetWidth(vol0, strat); let c0 = cl[warm - 1];
  const path = [];
  for (let i = warm; i < cl.length; i += 1) {
    const p = cl[i]; const k = 1 + w / 100; const lo = c0 / k; const hi = c0 * k;
    const vol = realizedVol(cl.slice(Math.max(0, i - 96), i + 1), barMin);
    if (vol != null && vol >= PAUSE_VOL) { paused += 1; path.push({ i, lo, hi, p, out: true }); continue; }
    if (p >= lo && p <= hi) { const f = val * rate * bandEdge(w) * perBar; fees += f; val += f; inBars += 1; outBars = 0; }
    else { outBars += 1;
      if (outBars * barMin >= S.wait && val * rate * bandEdge(targetWidth(vol, strat)) > moveCost(val) * 1.5) {
        const m = p / c0; const hold = val * (1 + m) / 2; const loss = ilRange(m, k) * hold;   // the band's two coins re-priced (drift) + its IL
        drift += hold - val; il += loss; val = hold + loss; const c = moveCost(val); costs += c; val -= c; moves += 1;
        w = targetWidth(vol, strat); c0 = p; outBars = 0; } }
    path.push({ i, lo, hi, p, out: !(p >= lo && p <= hi), move: outBars === 0 && moves && path.length && path[path.length - 1]?.lo !== lo });
  }
  const m = cl[cl.length - 1] / c0; const hold = val * (1 + m) / 2; const openIl = ilRange(m, 1 + w / 100) * hold;   // the open band, marked to the last price
  const bars = cl.length - warm;
  return { start: amt, end: hold + openIl, fees, costs, il: il + openIl, drift: drift + hold - val, moves, inPct: Math.round((100 * inBars) / Math.max(1, bars - paused)), paused, bars, hours: (bars * barMin) / 60, path };
}

/** 📐 the next 24h as a fan from the coin's own volatility: price bands at ±1σ and the band's value at +20% / 0 / −20%. */
export function projection(price, vol, w, amt, rate) {
  const k = 1 + w / 100; const pts = [0, 4, 8, 12, 18, 24].map(h => { const s = (vol || 0) * Math.sqrt(h / 24); return { h, up: price * Math.exp(s), dn: price * Math.exp(-s) }; });
  const fee = dayFees(amt, rate, w, vol);
  const at = m => ({ price: price * m, value: amt * ((1 + m) / 2) * (1 + ilRange(m, k)) + (m >= 1 / k && m <= k ? fee : 0) });   // a 50/50 band: the coins re-priced, its IL, + a day of fees while inside
  return { pts, up: at(1.2), base: at(1), dn: at(0.8) };
}
