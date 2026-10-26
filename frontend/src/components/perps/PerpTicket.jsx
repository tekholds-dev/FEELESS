import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { toast } from 'sonner';
import { useGlide } from '../../lib/useGlide';
import { perpPlan, quoteMatches, atPrice, tpOk, slOk, levelAt, rr, post, signRun } from '../../lib/perps';

// 🎟 THE TICKET (Jupiter Perps): side · collateral · leverage · TP / SL BEFORE the trade (typed, % chips, or dragged on the chart — each shows
// its $ P&L + ROE and the reward : risk) → REVIEW asks Jupiter for the real quote (entry, liquidation, fee, the P&L at each trigger) and the
// transaction (backend/jup_perps.py verifies it) → SIGN + OPEN: the wallet signs, Jupiter's keeper lands it, TP / SL ride the same transaction.
const USDS = [10, 25, 50, 100, 250]; const LEVS = [2, 5, 10, 25, 50, 100, 250];
export const MAX_LEV = 250; const MIN_LEV = 1.1;   // Jupiter's own cap on SOL / ETH / BTC (checked live: 300 is refused)
// the slider is logarithmic so 2× … 25× (where most trades live) keeps real travel and 250× is still one drag away
export const levToF = l => Math.log(Math.max(MIN_LEV, l) / MIN_LEV) / Math.log(MAX_LEV / MIN_LEV);
export const fToLev = f => { const l = MIN_LEV * (MAX_LEV / MIN_LEV) ** Math.max(0, Math.min(1, f)); return l >= 10 ? Math.round(l) : +l.toFixed(1); };
const USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'; const SOL_MINT = 'So11111111111111111111111111111111111111112';
// pure: which coin pays for the open — USDC when it covers it, else SOL (kept ≥ 0.01 SOL for fees), else null (not enough of either)
export function payWith(usd, bal, solPx) {
  const u = bal?.usdc; const s = bal?.sol; const solUsd = s != null && solPx > 0 ? Math.max(0, s - 0.01) * solPx : null;
  return { usdcOk: u != null && u >= usd, solOk: solUsd != null && solUsd >= usd, solUsd, best: u != null && u >= usd ? 'USDC' : solUsd != null && solUsd >= usd ? 'SOL' : null };
}
function useBalances(addr) {   // the wallet's USDC + SOL, every 20s while the ticket is open
  const [b, setB] = useState(null);
  useEffect(() => { if (!addr) { setB(null); return undefined; } let alive = true;
    const one = m => fetch(apiUrl(`/api/reputation/balance/${addr}/${m}`)).then(r => (r.ok ? r.json() : null)).then(x => (x ? Number(x.amount) || 0 : null)).catch(() => null);
    const load = () => { if (document.hidden) return; Promise.all([one(USDC_MINT), one(SOL_MINT)]).then(([usdc, sol]) => alive && setB({ usdc, sol })); };
    load(); const t = setInterval(load, 20000); return () => { alive = false; clearInterval(t); }; }, [addr]);
  return b;
}
const TP_PCT = [2, 5, 10, 25]; const SL_PCT = [1, 2, 5, 10];
const px = v => (v == null || !Number.isFinite(v) ? '—' : v >= 1000 ? `$${v.toLocaleString('en-US', { maximumFractionDigits: 1 })}` : `$${Number(v).toFixed(v >= 10 ? 2 : 4)}`);
const $ = v => (v == null || !Number.isFinite(v) ? '—' : `${v < 0 ? '−' : '+'}$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(2)}K` : Math.abs(v).toFixed(2)}`);
const cash = v => (v == null ? '—' : `$${v >= 1000 ? `${(v / 1000).toFixed(2)}K` : v.toFixed(2)}`);

function Num({ v, fmt, cls = '' }) { const g = useGlide(v == null ? null : +v, 450); return <b className={`m-num ${cls}`}>{fmt(g)}</b>; }

export function PerpTicket({ asset, mark, solPx, pool, t, set, addr, wallet, provider, connect, onOpened }) {
  const { side, usd, lev, tp, sl } = t;
  const [built, setBuilt] = useState(null); const [busy, setBusy] = useState(''); const [pay, setPay] = useState(null);
  const bal = useBalances(addr); const pw = payWith(usd, bal, solPx); const coin = pay || pw.best || 'USDC';
  const short = bal && !(coin === 'USDC' ? pw.usdcOk : pw.solOk);
  useEffect(() => { setBuilt(null); }, [asset, side, usd, lev, tp, sl, coin]);
  const fee = pool?.openFeePercent ?? 0.06; const p = perpPlan(mark, usd, lev, side, fee);
  const tpR = atPrice(tp, mark, usd, lev, side); const slR = atPrice(sl, mark, usd, lev, side);
  const tpBad = !tpOk(tp, mark, side); const slBad = !slOk(sl, mark, side, p?.liq); const ratio = rr(tp, sl, mark);
  const borrow = p ? p.size * ((side === 'long' ? pool?.longBorrowRatePercent : pool?.shortBorrowRatePercent) || 0) / 100 : null;
  const q = built?.quote; const ok = quoteMatches(q, side, usd * lev);
  const need = async () => { if (!wallet?.address || !provider) { await connect?.('solana'); return false; } return true; };
  const review = async () => { if (!(await need())) return; setBusy('Asking Jupiter for the real quote…');
    try { setBuilt(await post('/api/reputation/familia/perps-real', { address: addr, asset, side, usd, lev, input: coin, ...(tp ? { tp } : {}), ...(sl ? { sl } : {}), ...(tp || sl ? { mark } : {}) })); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const open = async () => { setBusy('✍ Approve in your wallet…');
    try { const r = await signRun(provider, addr, built, () => setBusy('⚡ Jupiter\'s keeper is landing it…'));
      toast.success(`📉 ${side.toUpperCase()} ${asset} ${lev}× LANDED${tp || sl ? ' · TP / SL armed' : ''}`, { action: { label: 'Solscan', onClick: () => window.open(`https://solscan.io/tx/${r.txid}`, '_blank', 'noopener') } });
      setBuilt(null); onOpened?.({ asset, side, usd, lev, size: usd * lev, entry: Number(q?.entryPriceUsd) || mark, txid: r.txid, at: Date.now() }); }
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
    <div className={`pt-pay ${short ? 'is-short' : ''}`} data-testid="pt-pay"><em>PAY WITH</em>
      <span className="m-seg" role="radiogroup" aria-label="Pay with">{[['USDC', bal?.usdc != null ? `$${bal.usdc.toFixed(2)}` : '—', pw.usdcOk], ['SOL', bal?.sol != null ? `${bal.sol.toFixed(3)} · $${(pw.solUsd ?? 0).toFixed(2)}` : '—', pw.solOk]].map(([k, have, ok]) =>
        <button key={k} type="button" role="radio" aria-checked={coin === k} className={`${coin === k ? 'active' : ''} ${bal && !ok ? 'is-low' : ''}`} onClick={() => setPay(k)}
          data-tip={k === 'USDC' ? 'Pay the collateral in USDC (shorts are held in USDC by Jupiter)' : 'Pay in SOL — Jupiter swaps it in the same transaction (0.01 SOL kept for fees)'} data-testid={`pt-pay-${k}`}><b>{k}</b><small className="m-num">{have}</small></button>)}</span>
      {short ? <small className="is-dn" data-testid="pt-pay-short">{pw.best ? `Not enough ${coin} — tap ${pw.best}` : `You need $${usd} of USDC or SOL in this wallet`}</small> : null}</div>
    <div className="pt-row"><em>LEVERAGE <b className="pt-lev m-num">{lev}×</b></em>
      <input className="pt-slide" type="range" min="0" max="1000" step="1" value={Math.round(levToF(lev) * 1000)} onChange={e => set({ lev: fToLev(Number(e.target.value) / 1000) })} aria-label="Leverage" data-testid="pt-lev"
        style={{ '--f': `${levToF(lev) * 100}%` }} />
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
    <button type="button" className={`pt-go is-${side}`} disabled={!!busy || !p || usd < 10 || tpBad || slBad || short || (built && !ok)} onClick={built ? open : review} data-testid="pt-go"
      data-tip={built ? 'Your wallet signs Jupiter\'s transaction; Jupiter\'s keeper lands it' : 'Get Jupiter\'s real quote + the transaction (nothing is signed yet)'}>
      {busy || (!addr ? '🔌 CONNECT WALLET' : usd < 10 ? 'JUPITER\'S FLOOR IS $10' : short ? `ADD ${coin} TO TRADE` : built ? `⚡ SIGN + OPEN ${side.toUpperCase()} ${asset} ${lev}×` : `REVIEW ${side.toUpperCase()} ${asset} · $${usd} × ${lev}×${tp || sl ? ' · TP/SL' : ''}`)}</button>
  </section>;
}
