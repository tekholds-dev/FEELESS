import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useGlide } from '../../lib/useGlide';
import { perpPlan, quoteMatches, atPrice, tpOk, slOk, levelAt, rr, post, signRun } from '../../lib/perps';

// 🎟 THE TICKET (Jupiter Perps): side · collateral · leverage · TP / SL BEFORE the trade (typed, % chips, or dragged on the chart — each shows
// its $ P&L + ROE and the reward : risk) → REVIEW asks Jupiter for the real quote (entry, liquidation, fee, the P&L at each trigger) and the
// transaction (backend/jup_perps.py verifies it) → SIGN + OPEN: the wallet signs, Jupiter's keeper lands it, TP / SL ride the same transaction.
const USDS = [10, 25, 50, 100, 250]; const LEVS = [2, 5, 10, 25, 50, 100];
const TP_PCT = [2, 5, 10, 25]; const SL_PCT = [1, 2, 5, 10];
const px = v => (v == null || !Number.isFinite(v) ? '—' : v >= 1000 ? `$${v.toLocaleString('en-US', { maximumFractionDigits: 1 })}` : `$${Number(v).toFixed(v >= 10 ? 2 : 4)}`);
const $ = v => (v == null || !Number.isFinite(v) ? '—' : `${v < 0 ? '−' : '+'}$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(2)}K` : Math.abs(v).toFixed(2)}`);
const cash = v => (v == null ? '—' : `$${v >= 1000 ? `${(v / 1000).toFixed(2)}K` : v.toFixed(2)}`);

function Num({ v, fmt, cls = '' }) { const g = useGlide(v == null ? null : +v, 450); return <b className={`m-num ${cls}`}>{fmt(g)}</b>; }

export function PerpTicket({ asset, mark, pool, t, set, addr, wallet, provider, connect, onOpened }) {
  const { side, usd, lev, tp, sl } = t;
  const [built, setBuilt] = useState(null); const [busy, setBusy] = useState('');
  useEffect(() => { setBuilt(null); }, [asset, side, usd, lev, tp, sl]);
  const fee = pool?.openFeePercent ?? 0.06; const p = perpPlan(mark, usd, lev, side, fee);
  const tpR = atPrice(tp, mark, usd, lev, side); const slR = atPrice(sl, mark, usd, lev, side);
  const tpBad = !tpOk(tp, mark, side); const slBad = !slOk(sl, mark, side, p?.liq); const ratio = rr(tp, sl, mark);
  const borrow = p ? p.size * ((side === 'long' ? pool?.longBorrowRatePercent : pool?.shortBorrowRatePercent) || 0) / 100 : null;
  const q = built?.quote; const ok = quoteMatches(q, side, usd * lev);
  const need = async () => { if (!wallet?.address || !provider) { await connect?.('solana'); return false; } return true; };
  const review = async () => { if (!(await need())) return; setBusy('Asking Jupiter for the real quote…');
    try { setBuilt(await post('/api/reputation/familia/perps-real', { address: addr, asset, side, usd, lev, ...(tp ? { tp } : {}), ...(sl ? { sl } : {}), ...(tp || sl ? { mark } : {}) })); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const open = async () => { setBusy('Approve in your wallet…');
    try { const r = await signRun(provider, addr, built); toast.success(`📉 ${side.toUpperCase()} ${asset} ${lev}× is live${tp || sl ? ' · TP / SL armed' : ''} · ${String(r.txid).slice(0, 8)}…`); setBuilt(null); onOpened?.(); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const tq = k => (built?.tpsl || []).find(x => x.kind === k);
  return <section className={`pt is-${side}`} data-testid="perp-ticket">
    <div className="pt-sides" role="radiogroup" aria-label="Side">
      {[['long', '▲ LONG', `Bet ${asset} goes UP`], ['short', '▼ SHORT', `Bet ${asset} goes DOWN`]].map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={side === k}
        className={`pt-side is-${k} ${side === k ? 'is-on' : ''}`} onClick={() => set({ side: k, tp: null, sl: null })} data-tip={tip} data-testid={`pt-${k}`}>{l}</button>)}
    </div>
    <div className="pt-row"><em>COLLATERAL</em>
      <label className="pt-in"><span>$</span><input type="number" min="10" max="1000" step="1" value={usd} onChange={e => set({ usd: Math.max(0, Number(e.target.value) || 0) })} aria-label="Collateral in dollars" data-testid="pt-usd" /></label>
      <span className="pt-chips">{USDS.map(u => <button key={u} type="button" className={usd === u ? 'is-on' : ''} onClick={() => set({ usd: u })} data-tip={`Put up $${u}`} data-testid={`pt-u-${u}`}>${u}</button>)}</span></div>
    <div className="pt-row"><em>LEVERAGE <b className="pt-lev m-num">{lev}×</b></em>
      <input className="pt-slide" type="range" min="1.1" max="100" step="0.1" value={lev} onChange={e => set({ lev: +Number(e.target.value).toFixed(1) })} aria-label="Leverage" data-testid="pt-lev"
        style={{ '--f': `${((lev - 1.1) / 98.9) * 100}%` }} />
      <span className="pt-chips">{LEVS.map(l => <button key={l} type="button" className={lev === l ? 'is-on' : ''} onClick={() => set({ lev: l })} data-tip={`${l}×: a ${(100 / l).toFixed(1)}% move against you wipes it`} data-testid={`pt-l-${l}`}>{l}×</button>)}</span></div>
    <div className="pt-vit">
      <span><em>SIZE</em><Num v={p?.size} fmt={cash} /></span>
      <span><em>ENTRY ≈</em><Num v={q ? Number(q.entryPriceUsd) : mark} fmt={px} /></span>
      <span className="is-dn" data-tip={`At ${lev}× a ${p ? p.liqPct.toFixed(1) : '—'}% move against you liquidates the collateral`}><em>☠ LIQ</em><Num v={q ? Number(q.liquidationPriceUsd) : p?.liq} fmt={px} /><small>{p ? `${p.liqPct.toFixed(1)}% away` : ''}</small></span>
      <span><em>FEE</em><Num v={q ? Number(q.openFeeUsd) : p?.fee} fmt={cash} /><small>{fee}% · borrow {borrow != null ? `$${borrow.toFixed(4)}/h` : '—'}</small></span>
    </div>
    <div className="pt-tpsl" data-testid="pt-tpsl">
      {[['tp', 'TAKE PROFIT', tp, tpR, tpBad, TP_PCT], ['sl', 'STOP LOSS', sl, slR, slBad, SL_PCT]].map(([k, l, v, r, bad, pcts]) => <div key={k} className={`pt-lvl is-${k} ${bad ? 'is-bad' : ''} ${v ? 'is-set' : ''}`}>
        <em>{l}</em>
        <label className="pt-in"><span>$</span><input type="number" step="any" value={v ?? ''} placeholder={k === 'tp' ? 'price' : 'price'} onChange={e => set({ [k]: Number(e.target.value) || null })} aria-label={l} data-testid={`pt-${k}`} /></label>
        <span className="pt-chips">{pcts.map(n => <button key={n} type="button" onClick={() => set({ [k]: +levelAt(mark, n, side, k).toFixed(mark >= 1000 ? 1 : 4) })} data-tip={`${k === 'tp' ? 'Take profit' : 'Stop'} ${n}% ${(k === 'tp') === (side === 'long') ? 'above' : 'below'} the price`} data-testid={`pt-${k}-${n}`}>{k === 'tp' ? '+' : '−'}{n}%</button>)}
          {v ? <button type="button" className="pt-x" onClick={() => set({ [k]: null })} aria-label={`Clear ${l}`} data-tip="Clear">✕</button> : null}</span>
        <span className="pt-at">{bad ? <small className="is-dn">{k === 'tp' ? `must be ${side === 'long' ? 'above' : 'below'} the price` : `must sit between the price and ☠ liq`}</small>
          : r ? <><b className={`m-num ${r.pnl >= 0 ? 'is-up' : 'is-dn'}`}>{$(tq(k)?.pnl ?? r.pnl)}</b><small className="m-num">{(tq(k)?.pnlPct ?? r.roe) >= 0 ? '+' : ''}{(tq(k)?.pnlPct ?? r.roe).toFixed(1)}% ROE</small></> : <small>off · drag it on the chart</small>}</span>
      </div>)}
      {ratio ? <div className="pt-rr" data-tip="Reward : risk — what the TP makes for every $1 the SL can lose"><em>R : R</em><u><s className="is-up" style={{ transform: `scaleX(${Math.min(1, ratio / (ratio + 1))})` }} /></u><b className="m-num">{ratio.toFixed(2)}</b></div> : null}
    </div>
    {built ? <div className={`pt-quote ${ok ? '' : 'is-bad'}`} data-testid="pt-quote"><em>JUPITER'S QUOTE</em><span>{String(q?.side || side).toUpperCase()} {asset} · entry {px(Number(q?.entryPriceUsd))} · size {cash(Number(q?.positionSizeUsd || usd * lev))} · ☠ {px(Number(q?.liquidationPriceUsd))}</span>
      {!ok ? <small>The quote does not match your ticket — nothing to sign. Review again.</small> : null}</div> : null}
    <button type="button" className={`pt-go is-${side}`} disabled={!!busy || !p || usd < 10 || tpBad || slBad || (built && !ok)} onClick={built ? open : review} data-testid="pt-go"
      data-tip={built ? 'Your wallet signs Jupiter\'s transaction; Jupiter\'s keeper lands it' : 'Get Jupiter\'s real quote + the transaction (nothing is signed yet)'}>
      {busy || (!addr ? '🔌 CONNECT WALLET' : usd < 10 ? 'JUPITER\'S FLOOR IS $10' : built ? `⚡ SIGN + OPEN ${side.toUpperCase()} ${asset} ${lev}×` : `REVIEW ${side.toUpperCase()} ${asset} · $${usd} × ${lev}×${tp || sl ? ' · TP/SL' : ''}`)}</button>
  </section>;
}
