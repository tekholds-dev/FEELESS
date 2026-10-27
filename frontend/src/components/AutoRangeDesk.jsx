import React, { useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../lib/api';
import { fetchFeelessCandles } from '../lib/candles';
import { useLivePrice } from '../lib/livePriceHub';
import { STRATEGIES, decide, replay, projection, closes, marketState, targetWidth, dayFees, feeTier, poolDayRate, bandEdge, REF_W } from '../lib/autoRange';
import '../styles/autoRange.css';

// 🤖 AUTORANGE DESK (owner 2026-10-26 mock-up: Pool Hall / Night Vault / Launch › Pools). The ENGINE (lib/autoRange.js) on this pool's REAL data:
// its token's 15-minute candles (FEELESS candle service), the live price (price hub, 2s), the pool's real fee rate (24h volume × fee tier ÷ TVL).
// The chart shows the bands the engine WOULD have run over those candles (replay) + every re-center; the side shows what it does NOW and why,
// gain vs cost; the bottom the replay's books and the next-24h fan. Your wallet signs every real move — FEELESS never holds the position.
const $ = (v, d = 2) => (v == null || !Number.isFinite(v) ? '—' : `${v < 0 ? '−' : ''}$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(1)}K` : Math.abs(v).toFixed(d)}`);
const big = v => (!(v > 0) ? '—' : v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${v.toFixed(0)}`);
const px = v => (!(v > 0) ? '—' : v >= 1 ? `$${v.toFixed(4)}` : `$${v.toPrecision(4)}`);
const pc = v => (v == null || !Number.isFinite(v) ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`);
const AMTS = [5, 10, 25, 50, 100];
const ARM_KEY = id => `feeless.autorange.${id}`;

function usePoolTape(mint) {   // the token's deepest pool → its 15-minute candles (refreshed each minute while open)
  const [d, setD] = useState({ pair: null, candles: [], state: 'loading' });
  useEffect(() => {
    if (!mint) { setD({ pair: null, candles: [], state: 'none' }); return undefined; }
    let alive = true; let pair = null;
    const load = async () => {
      try {
        if (!pair) { const r = await fetch(apiUrl(`/api/market/tokens/solana/${mint}`)); const list = r.ok ? await r.json() : [];
          pair = (Array.isArray(list) ? list : []).sort((a, b) => (b?.liquidity?.usd || 0) - (a?.liquidity?.usd || 0))[0] || null; }
        if (!pair) { if (alive) setD({ pair: null, candles: [], state: 'none' }); return; }
        const c = await fetchFeelessCandles('solana', pair.pairAddress, '15m', null, mint);
        if (alive) setD({ pair, candles: (c?.candles || []).slice(-300), state: 'ok' });
      } catch { if (alive) setD(x => ({ ...x, state: x.candles.length ? 'ok' : 'error' })); }
    };
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 60000);
    return () => { alive = false; clearInterval(t); };
  }, [mint]);
  return d;
}

// pure: candles + the replay's bands → SVG paths for the band chart (W×H)
export function bandChart(candles, path, W = 600, H = 220, live = null) {
  const cs = (candles || []).slice(-120); if (cs.length < 2) return null;
  const off = (candles || []).length - cs.length; const bands = (path || []).filter(p => p.i >= off);
  const vals = cs.flatMap(c => [c[2], c[3]]).concat(bands.flatMap(b => [b.lo, b.hi])).concat(live > 0 ? [live] : []).filter(v => v > 0);
  const lo = Math.min(...vals) * 0.995; const hi = Math.max(...vals) * 1.005; const y = v => H - 6 - ((v - lo) / (hi - lo)) * (H - 12);
  const bw = W / cs.length; const x = i => i * bw + bw / 2;
  const candlesOut = cs.map((c, i) => ({ x: x(i), o: y(c[1]), h: y(c[2]), l: y(c[3]), c: y(c[4]), up: c[4] >= c[1], w: Math.max(1.2, bw * 0.6) }));
  const step = k => bands.map((b, j) => `${j ? 'L' : 'M'}${x(b.i - off).toFixed(1)},${y(b[k]).toFixed(1)}`).join(' ');
  const fill = bands.length ? `${step('hi')} ${bands.slice().reverse().map(b => `L${x(b.i - off).toFixed(1)},${y(b.lo).toFixed(1)}`).join(' ')} Z` : '';
  const moves = bands.filter((b, j) => j && (b.lo !== bands[j - 1].lo)).map(b => ({ x: x(b.i - off), y: y(b.hi) - 7, up: b.p >= bands[bands.indexOf(b) - 1].p }));
  const last = live > 0 ? live : cs[cs.length - 1][4];
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(f => ({ y: 6 + f * (H - 12), v: hi - f * (hi - lo) }));
  return { candles: candlesOut, upper: step('hi'), lower: step('lo'), fill, moves, lastY: y(last), last, ticks, times: [0, 0.25, 0.5, 0.75, 1].map(f => ({ x: f * W, t: cs[Math.min(cs.length - 1, Math.round(f * (cs.length - 1)))][0] })) };
}

function Ring({ v }) { return <i className="arx-ring" style={{ '--v': Math.max(0, Math.min(100, v || 0)) }} aria-hidden="true" />; }

export function AutoRangeDesk({ pool, amt: amt0 = null }) {
  const mint = pool?.hold || null; const tape = usePoolTape(mint);
  const live = useLivePrice(mint ? { chainId: 'solana', baseToken: { address: mint } } : null); const price = live?.live ? live.usd : (tape.candles.length ? tape.candles[tape.candles.length - 1][4] : null);
  const [strat, setStrat] = useState('balanced'); const [amt, setAmt] = useState(amt0 || 5); const [custom, setCustom] = useState(null);
  const [on, setOn] = useState(true); const [comp, setComp] = useState(true);
  const [armed, setArmed] = useState(() => { try { return JSON.parse(localStorage.getItem(ARM_KEY(pool?.id)) || 'null'); } catch { return null; } });
  useEffect(() => { if (amt0) setAmt(amt0); }, [amt0]);
  const { rate, src } = poolDayRate(pool);
  const cl = useMemo(() => closes(tape.candles), [tape.candles]); const ms = useMemo(() => marketState(cl), [cl]);
  const w = custom || targetWidth(ms.vol, strat);
  const rp = useMemo(() => (tape.candles.length ? replay(tape.candles, { amt, rate, strat }) : null), [tape.candles, amt, rate, strat]);
  const band = armed?.band || (price ? { lo: price / (1 + w / 100), hi: price * (1 + w / 100) } : null);
  const [outSince, setOutSince] = useState(null);
  useEffect(() => { if (!band || !price) return; const inside = price >= band.lo && price <= band.hi; setOutSince(o => (inside ? null : o || Date.now())); }, [price, band?.lo, band?.hi]); // eslint-disable-line react-hooks/exhaustive-deps
  const now = Date.now();
  const dec = useMemo(() => (tape.candles.length && price ? decide({ price, band: armed?.band || null, amt, rate, candles: tape.candles, strat, outSince, now, unclaimed: 0 }) : null), [tape.candles, price, armed, amt, rate, strat, outSince]); // eslint-disable-line react-hooks/exhaustive-deps
  const chart = useMemo(() => bandChart(tape.candles, rp?.path, 600, 220, price), [tape.candles, rp, price]);
  const proj = price ? projection(price, ms.vol, w, amt, rate) : null;
  const ch24 = Number(tape.pair?.priceChange?.h24); const inside = band && price ? price >= band.lo && price <= band.hi : null;
  const arm = () => { const a = { band: dec?.band || band, strat, amt, w, at: Date.now() }; try { localStorage.setItem(ARM_KEY(pool.id), JSON.stringify(a)); } catch { /* private mode */ } setArmed(a); };
  const disarm = () => { try { localStorage.removeItem(ARM_KEY(pool.id)); } catch { /* private */ } setArmed(null); };
  const slider = band && price ? Math.max(0, Math.min(1, Math.log(price / band.lo) / Math.log(band.hi / band.lo))) : 0.5;
  if (!mint) return null;
  return <section className={`arx ${on ? '' : 'is-off'} is-${(dec?.state || 'reading').toLowerCase()}`} data-testid="autorange">
    <header className="arx-top">
      <span className="arx-id">{tape.pair?.info?.imageUrl ? <img src={tape.pair.info.imageUrl} alt="" /> : <i>{String(pool.sym || '?').slice(0, 2)}</i>}
        <span><b>${String(pool.sym || '').split('-')[0]} <em>/ {String(pool.sym || '').split('-')[1] || 'USDC'}</em></b><small>{pool.proto} · {pool.kind === 'dlmm' ? 'DLMM' : 'v3 CLMM'} · {feeTier(pool.meta) != null ? `${(feeTier(pool.meta) * 100).toFixed(2)}% fee` : 'fee n/a'}</small></span></span>
      <span className="arx-chips"><i className={`is-${(dec?.state || 'reading').toLowerCase()}`}>{dec?.state || 'READING'}</i><i className={ms.vol >= 0.6 ? 'is-hot' : 'is-ok'}>{ms.vol == null ? 'risk —' : ms.vol >= 0.6 ? '⚠ high risk' : ms.vol >= 0.25 ? 'medium risk' : 'low risk'}</i></span>
      <span className="arx-price"><b className="m-num" key={price}>{px(price)}</b><small className={`m-num ${ch24 >= 0 ? 'is-up' : 'is-dn'}`}>{pc(ch24)} (24h)</small></span>
      <dl className="arx-kv"><div><dt>MKT CAP</dt><dd className="m-num">{big(tape.pair?.marketCap || tape.pair?.fdv)}</dd></div><div><dt>24H VOLUME</dt><dd className="m-num">{big(pool.vol || tape.pair?.volume?.h24)}</dd></div>
        <div><dt>POOL TVL</dt><dd className="m-num">{big(pool.tvl)}</dd></div><div><dt>SWINGS / DAY</dt><dd className="m-num">{ms.vol == null ? '—' : `±${Math.round(ms.vol * 100)}%`}</dd></div></dl>
    </header>

    <div className="arx-main">
      <div className="arx-chart" data-tip="15-minute candles (FEELESS candle service) with the bands the engine would have run on them — ▲▼ = a re-center">
        <div className="arx-cbar"><span className="arx-leg"><i className="is-px" />PRICE <i className="is-hi" />UPPER <i className="is-lo" />LOWER <i className="is-mv" />RE-CENTER</span>
          <label className="arx-switch" data-tip="Engine on: it reads every tick and says what to do"><input type="checkbox" checked={on} onChange={e => setOn(e.target.checked)} aria-label="AutoRange on" /><span />AUTORANGE {on ? 'ON' : 'OFF'}</label></div>
        {chart ? <svg viewBox="0 0 660 240" className="arx-svg" role="img" aria-label="Price with the engine's bands">
          <g transform="translate(0,6)">
            {chart.ticks.map((t, i) => <line key={i} x1="0" x2="600" y1={t.y} y2={t.y} className="arx-grid" />)}
            {on && chart.fill ? <path d={chart.fill} className="arx-bandfill" /> : null}
            {chart.candles.map((c, i) => <g key={i} className={c.up ? 'arx-up' : 'arx-dn'}><line x1={c.x} x2={c.x} y1={c.h} y2={c.l} /><rect x={c.x - c.w / 2} y={Math.min(c.o, c.c)} width={c.w} height={Math.max(1, Math.abs(c.c - c.o))} /></g>)}
            {on ? <><path d={chart.upper} className="arx-hi" /><path d={chart.lower} className="arx-lo" />{chart.moves.map((m, i) => <text key={i} x={m.x} y={m.y} className="arx-mv" textAnchor="middle">{m.up ? '▲' : '▼'}</text>)}</> : null}
            <line x1="0" x2="600" y1={chart.lastY} y2={chart.lastY} className="arx-last" />
            <g transform={`translate(602,${chart.lastY - 9})`}><rect width="58" height="18" rx="4" className="arx-tag" /><text x="29" y="13" textAnchor="middle" className="arx-tagt">{px(chart.last).slice(1, 9)}</text></g>
            {chart.ticks.filter(t => Math.abs(t.y - chart.lastY) > 12).map((t, i) => <text key={`t${i}`} x="606" y={t.y + 3} className="arx-axis">{px(t.v).slice(1, 9)}</text>)}
            {chart.times.map((t, i) => <text key={`x${i}`} x={Math.min(570, t.x)} y="226" className="arx-axis">{new Date(t.t * 1000).toTimeString().slice(0, 5)}</text>)}
          </g></svg>
          : <p className="arx-empty">{tape.state === 'loading' ? 'Reading the pool\'s candles…' : tape.state === 'none' ? 'No live pool found for this token.' : 'Candles unavailable right now — retrying.'}</p>}
      </div>

      <aside className="arx-engine">
        <header><i className="arx-bot" aria-hidden="true"><s /><s /></i><span><b>AUTORANGE ENGINE</b><small>rules on live data — no AI, no guesses</small></span>
          <em className={armed ? 'is-on' : ''}>{armed ? '● ARMED' : on ? '● LIVE' : '○ OFF'}</em></header>
        <div className="arx-strats" role="radiogroup" aria-label="Strategy">{Object.entries(STRATEGIES).map(([k, s]) => <button key={k} type="button" role="radio" aria-checked={strat === k && !custom}
          className={strat === k && !custom ? 'is-on' : ''} onClick={() => { setStrat(k); setCustom(null); }} data-tip={s.tip} data-testid={`arx-s-${k}`}><b>{s.name}</b><small>{s.min} – {s.max}%</small></button>)}
          <button type="button" className={custom ? 'is-on' : ''} onClick={() => setCustom(custom || w)} data-tip="Set your own width — the engine still decides when to move it"><b>Custom</b><small>{custom ? `±${custom}%` : 'you set it'}</small></button></div>
        {custom ? <label className="arx-custom"><span>±</span><input type="range" min="1" max="100" value={custom} onChange={e => setCustom(Number(e.target.value))} aria-label="Custom width" /><b>{custom}%</b></label> : null}
        <div className="arx-range"><span><em>{armed ? 'YOUR RANGE (ARMED)' : 'RANGE IT WOULD SET'}</em><b className="m-num">{band ? `${px(band.lo)} – ${px(band.hi)}` : '—'}</b>
          <u className={inside === false ? 'is-out' : ''} aria-hidden="true"><i style={{ left: `${slider * 100}%` }} /></u></span>
          <span><em>WIDTH</em><b className="m-num">±{w}%</b><small>{rate > 0 ? `${$(dayFees(amt, rate, w, ms.vol), 3)}/day on ${$(amt, 0)} · ×${bandEdge(w).toFixed(1)} a ±${REF_W}% LP` : 'no fee data'}</small></span></div>
        <div className="arx-cells">
          <span className="arx-state"><em>MARKET STATE</em><b>{dec?.state || 'READING'}</b><small>{ms.vol == null ? 'needs 8 candles' : `trend ${pc(ms.trend)} · 2h ${pc(ms.momentum)}`}</small></span>
          <span className="arx-conf" data-tip="How much data + how calm: more candles and smaller swings = higher"><em>CONFIDENCE</em><span><Ring v={dec?.conf || 0} /><b className="m-num">{dec?.conf ?? '—'}%</b></span></span>
          <span className={`arx-next is-${(dec?.action || 'wait').toLowerCase().replace(' ', '-')}`}><em>NEXT ACTION</em><b>{dec?.action || 'WAIT'}</b><small>{dec?.why || 'Reading the pool…'}</small>
            <span className="arx-gc"><i><em>EST. 24H FEES</em><b className="m-num is-up">+{$(dec?.gain, 3)}</b></i><i><em>MOVE COST</em><b className="m-num">{$(dec?.cost, 3)}</b></i></span></span>
        </div>
      </aside>
    </div>

    <div className="arx-low">
      <div className="arx-replay" data-tip="These exact rules run over this coin's real candles — fees only while a close sat inside, moves paid for, IL booked">
        <header><b>🔁 REPLAY · LAST {rp ? Math.round(rp.hours) : '—'}H</b><small>{STRATEGIES[strat].name} · {$(amt, 0)} in · real candles, not a promise</small></header>
        {rp ? <div className="arx-tiles">
          <span><em>WORTH NOW</em><b className={`m-num ${rp.end >= rp.start ? 'is-up' : 'is-dn'}`}>{$(rp.end)}</b><small>{pc((rp.end / rp.start - 1) * 100)}</small></span>
          <span><em>FEES EARNED</em><b className="m-num is-up">+{$(rp.fees, 3)}</b><small>{src}</small></span>
          <span><em>PRICE + IL</em><b className={`m-num ${rp.drift + rp.il >= 0 ? 'is-up' : 'is-dn'}`}>{$(rp.drift + rp.il, 3)}</b><small>coins re-priced · IL {$(rp.il, 3)}</small></span>
          <span><em>TIME IN RANGE</em><b className="m-num">{rp.inPct}%</b><u aria-hidden="true"><s style={{ transform: `scaleX(${rp.inPct / 100})` }} /></u></span>
          <span><em>RE-CENTERS</em><b className="m-num">{rp.moves}</b><small>cost {$(rp.costs, 3)}{rp.paused ? ` · paused ${Math.round((rp.paused * 15) / 60)}h` : ''}</small></span>
        </div> : <p className="arx-empty">Needs 24+ candles to replay.</p>}
      </div>
      <div className="arx-rules">
        <header><b>♻ AUTO-COMPOUND</b><label className="arx-switch"><input type="checkbox" checked={comp} onChange={e => setComp(e.target.checked)} aria-label="Auto-compound" /><span />{comp ? 'ON' : 'OFF'}</label></header>
        <ul>{[['Harvest fees', 'only when they beat 3× the gas'], ['Reinvest to grow', 'back into the same band'], ['Keep in range', `re-center after ${STRATEGIES[strat].wait} min out`], ['Skip if not profitable', 'a move must beat its cost ×1.5'], ['Pause when wild', 'swings ≥ 120% a day → sit out']].map(([a, b], i) =>
          <li key={a} className={comp || i > 1 ? 'is-on' : ''} style={{ '--i': i }}><i aria-hidden="true" /><b>{a}</b><small>{b}</small></li>)}</ul>
      </div>
    </div>

    <div className="arx-low is-b">
      <div className="arx-proj">
        <header><b>📐 NEXT 24H</b><small>the coin's own swings (±1σ) · what {$(amt, 0)} in a ±{w}% band is worth</small></header>
        {proj ? <div className="arx-proj-in">
          <svg viewBox="0 0 300 100" preserveAspectRatio="none" className="arx-fan" aria-hidden="true">
            <path d={`M0,50 ${proj.pts.map(p => `L${(p.h / 24) * 300},${50 - Math.min(48, (p.up / price - 1) * 300)}`).join(' ')} ${proj.pts.slice().reverse().map(p => `L${(p.h / 24) * 300},${50 + Math.min(48, (1 - p.dn / price) * 300)}`).join(' ')} Z`} className="arx-fanfill" />
            <line x1="0" x2="300" y1="50" y2="50" className="arx-fanmid" /></svg>
          <ol>{[['UPPER (+20%)', proj.up, 'is-up'], ['BASE (0%)', proj.base, 'is-base'], ['LOWER (−20%)', proj.dn, 'is-dn']].map(([l, r, c]) => <li key={l} className={c}><span><b>{l}</b><small className="m-num">{px(r.price)}</small></span>
            <span><em>{$(amt, 0)} →</em><b className="m-num">{$(r.value)}</b><small className="m-num">{pc((r.value / amt - 1) * 100)}</small></span></li>)}</ol>
        </div> : null}
      </div>
      <div className="arx-go">
        <header><b>🚀 DEPOSIT & RUN</b><small>{pool.proto} · Solana · your wallet signs each move</small></header>
        <div className="arx-amts" role="radiogroup" aria-label="Amount">{AMTS.map(a => <button key={a} type="button" role="radio" aria-checked={amt === a} className={amt === a ? 'is-on' : ''} onClick={() => setAmt(a)} data-tip={`Plan it with $${a}`}>${a}</button>)}</div>
        <button type="button" className="m-btn m-go arx-start" onClick={armed ? disarm : arm} disabled={!dec || dec.action === 'WAIT'} data-testid="arx-start"
          data-tip={armed ? 'Stop watching this band' : 'Arms the engine on this band: it watches every tick and tells you the moment a move pays — each move is a transaction your wallet signs'}>
          {armed ? '■ STOP AUTORANGE' : dec?.action === 'PAUSE' ? '⏸ TOO WILD — WATCH ONLY' : `⚡ START AUTORANGE & COMPOUND · ${$(amt, 0)}`}</button>
        <small className="arx-fine">Fees: the pool's own rate ({src}) × your band's edge over a typical ±{REF_W}% LP. Est. move cost {$(dec?.cost, 3)} · {pool.proto} {pool.kind === 'dlmm' ? 'DLMM' : 'CLMM'} positions open in its own app until its SDK lands in FEELESS — the engine plans + watches here. Meme pools are never "safe"; fees are not a promise.</small>
      </div>
    </div>
  </section>;
}

// pure: the pools AutoRange can run on — concentrated (v3 / DLMM), a real token to chart, real 24h volume — busiest fee rate first
export function rangeable(pools, n = 4) {
  return (pools || []).filter(p => ['v3', 'dlmm'].includes(p?.kind) && p.hold && (Number(p.tvl) || 0) >= 50000 && (Number(p.vol) || 0) > 0)
    .map(p => ({ p, rate: poolDayRate(p).rate })).filter(x => x.rate > 0).sort((a, b) => b.rate - a.rate).slice(0, n).map(x => x.p);
}

// 🤖 one row of the busiest rangeable pools (chips with their real fee rate a day) → the AutoRange desk on the one picked
export function AutoRangePicker({ pools, amt = null, title = '🤖 AUTORANGE · THE BUSIEST BANDS RIGHT NOW' }) {
  const list = useMemo(() => rangeable(pools), [pools]); const [id, setId] = useState(null);
  const pick = list.find(p => p.id === id) || list[0] || null;
  if (!pick) return <p className="arx-empty">{pools ? 'No concentrated pool with live volume right now.' : 'Reading the pools…'}</p>;
  return <div className="arx-pick" data-testid="autorange-picker">
    <header><b>{title}</b><small>fees a day per $ in a ±20% band · tap one</small></header>
    <div className="arx-pools" role="radiogroup" aria-label="Pool">{list.map(p => <button key={p.id} type="button" role="radio" aria-checked={p === pick} className={p === pick ? 'is-on' : ''} onClick={() => setId(p.id)}
      data-tip={`${p.proto} · ${p.meta || p.kind} · TVL ${big(p.tvl)}`}><b>{p.sym}</b><small className="m-num">{(poolDayRate(p).rate * 100).toFixed(3)}%/day · {big(p.vol)} vol</small></button>)}</div>
    <AutoRangeDesk key={pick.id} pool={pick} amt={amt} />
  </div>;
}
