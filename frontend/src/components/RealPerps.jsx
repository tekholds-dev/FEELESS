import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';
import { useGlide } from '../lib/useGlide';
import { cash } from '../lib/earnStake';
import '../styles/realPerps.css';

// 📉 REAL PERPS — Jupiter Perps from your own wallet (owner, 2026-10-23: "we tryna long or short — that's what matters"; DECISIONS #8).
// Pick SOL / ETH / BTC, LONG or SHORT, $10+ collateral (Jupiter's minimum), 1.1–100× → REVIEW asks Jupiter for the real quote (entry,
// liquidation, fee) and the transaction (backend/jup_perps.py checks it) → SIGN + OPEN: your wallet signs, Jupiter's keeper co-signs and
// lands it. Positions live below with P&L before fees (fees apart), the liquidation distance drawn, one-tap close. FEELESS never holds it.
const SIZES = [10, 25, 50, 100]; const LEVS = [2, 5, 10, 25, 50, 100];
const px = v => (v == null ? '—' : v >= 1000 ? `$${Math.round(v).toLocaleString('en-US')}` : `$${Number(v).toFixed(2)}`);
const sgn = v => `${Number(v) < 0 ? '−' : '+'}${cash(Math.abs(Number(v) || 0))}`;
// pure: the preview before Jupiter's quote — size, the move that liquidates (before fees), $ per 1 % move, the open fee
export function perpPlan(mark, usd, lev, side, feePct = 0.06) {
  if (!(mark > 0) || !(usd > 0) || !(lev > 0)) return null;
  const size = usd * lev; const fee = (size * feePct) / 100; const move = Math.max(0, (usd - fee) / size);   // fraction of price
  return { size, fee, per1: size / 100, liq: side === 'long' ? mark * (1 - move) : mark * (1 + move), liqPct: move * 100 };
}
// pure: Jupiter's quote must match the ticket on screen before the wallet opens (side, and size within 10 % — at 100× the fees come out of it)
export const quoteMatches = (q, side, size) => !!q && String(q.side || side).toLowerCase() === side && Math.abs(Number(q.positionSizeUsd || q.sizeUsdDelta || size) - size) <= size * 0.1 + 0.5;

async function post(path, body) {
  const r = await fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'Jupiter Perps said no.'); return b;
}
async function signRun(provider, address, built) {   // the wallet signs Jupiter's transaction; Jupiter's keeper co-signs + lands it
  const { VersionedTransaction } = await import('@solana/web3.js');
  const tx = VersionedTransaction.deserialize(Uint8Array.from(atob(built.transaction), c => c.charCodeAt(0)));
  if (tx.message.staticAccountKeys[0].toBase58() !== address) throw new Error('This transaction is not for your wallet — refused.');
  const signed = await provider.signTransaction(tx);
  return post('/api/reputation/familia/perps-real/execute', { address, action: built.action, signed: btoa(String.fromCharCode(...signed.serialize())) });
}

export function RealPerps({ marks = {}, coin = '', devAddress = '' }) {
  const { wallet, provider, connect } = useWallet() || {}; const addr = (wallet?.chain === 'solana' ? wallet.address : '') || devAddress;
  const [d, setD] = useState(null); const [asset, setAsset] = useState(['SOL', 'ETH', 'BTC'].includes(coin) ? coin : 'SOL'); const [side, setSide] = useState('long');
  const [usd, setUsd] = useState(10); const [lev, setLev] = useState(10); const [built, setBuilt] = useState(null); const [busy, setBusy] = useState('');
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/familia/perps-real?address=${encodeURIComponent(addr || '')}`)).then(r => (r.ok ? r.json() : null)).then(x => x && setD(x)).catch(() => {}), [addr]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 10000); return () => clearInterval(t); }, [load]);
  useEffect(() => { setBuilt(null); }, [asset, side, usd, lev]);
  const pool = d?.pools?.[asset] || {}; const mark = Number(marks[asset]) || null; const p = perpPlan(mark, usd, lev, side, pool.openFeePercent ?? 0.06);
  const size = useGlide(p?.size || 0); const pos = d?.positions || []; const total = pos.reduce((s, x) => s + (x.pnl || 0), 0);
  const need = async () => { if (!wallet?.address || !provider) { await connect?.('solana'); return false; } return true; };
  const review = async () => { if (!(await need())) return; setBusy('Asking Jupiter for the real quote…');
    try { setBuilt(await post('/api/reputation/familia/perps-real', { address: addr, asset, side, usd, lev })); } catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const open = async () => { setBusy('Approve in your wallet…');
    try { const r = await signRun(provider, addr, built); toast.success(`📉 ${side.toUpperCase()} ${asset} ${lev}× is live · ${r.txid.slice(0, 8)}…`); setBuilt(null); load(); } catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const close = async x => { if (!(await need())) return; setBusy(`Closing ${x.asset} ${x.side}…`);
    try { const b = await post('/api/reputation/familia/perps-real', { act: 'close', address: addr, positionPubkey: x.pubkey }); await signRun(provider, addr, b); toast.success(`✅ ${x.asset} ${x.side} closed — USDC back in your wallet`); load(); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const q = built?.quote; const ok = quoteMatches(q, side, usd * lev);
  const rail = p ? (side === 'long' ? 50 - Math.min(46, p.liqPct * 2) : 50 + Math.min(46, p.liqPct * 2)) : 50;
  return <section className={`rp is-${side}`} data-testid="real-perps">
    <header className="rp-head"><span><em>📉 REAL PERPS · JUPITER · YOUR WALLET SIGNS</em><b>Long or short {asset} up to {d?.maxLev || 100}×</b></span>
      {pos.length ? <i className={`rp-tot ${total >= 0 ? 'up' : 'dn'}`} data-tip="Open P&L across your positions, before fees">{sgn(total)} open</i> : <i className="rp-fee" data-tip="Jupiter's open fee on the position size">fee {pool.openFeePercent ?? 0.06}%</i>}</header>
    <div className="m-seg rp-mkts" role="radiogroup" aria-label="Market">{['SOL', 'ETH', 'BTC'].map(a => <button key={a} type="button" role="radio" aria-checked={a === asset} className={a === asset ? 'active' : ''} onClick={() => setAsset(a)}
      data-tip={`${a}-PERP on Jupiter · ${marks[a] ? px(marks[a]) : 'reading the price'}`} data-testid={`rp-a-${a}`}><b>{a}</b><small>{marks[a] ? px(marks[a]) : '…'}</small></button>)}</div>
    <div className="rp-sides"><button type="button" className={`rp-long ${side === 'long' ? 'is-on' : ''}`} onClick={() => setSide('long')} aria-pressed={side === 'long'} data-tip={`Bet ${asset} goes UP`} data-testid="rp-long">▲ LONG</button>
      <button type="button" className={`rp-short ${side === 'short' ? 'is-on' : ''}`} onClick={() => setSide('short')} aria-pressed={side === 'short'} data-tip={`Bet ${asset} goes DOWN`} data-testid="rp-short">▼ SHORT</button></div>
    <div className="rp-pick"><span className="m-seg" role="radiogroup" aria-label="Collateral">{SIZES.map(s => <button key={s} type="button" role="radio" aria-checked={usd === s} className={usd === s ? 'active' : ''} onClick={() => setUsd(s)} data-tip={`Put up $${s} (Jupiter's minimum is $10)`} data-testid={`rp-u-${s}`}>${s}</button>)}</span>
      <span className="m-seg" role="radiogroup" aria-label="Leverage">{LEVS.map(l => <button key={l} type="button" role="radio" aria-checked={lev === l} className={lev === l ? 'active' : ''} onClick={() => setLev(l)} data-tip={`${l}×: a ${(100 / l).toFixed(1)}% move against you wipes it`} data-testid={`rp-l-${l}`}>{l}×</button>)}</span></div>
    {p ? <div className="rp-vit">
      <span><em>POSITION</em><b className="m-num">{cash(size)}</b><small>{cash(usd)} × {lev}×</small></span>
      <span><em>EVERY 1% MOVE</em><b className="m-num">±{cash(p.per1)}</b><small>{side === 'long' ? 'up = you win' : 'down = you win'}</small></span>
      <span className="is-dn"><em>WIPED AT</em><b className="m-num">{px(q ? Number(q.liquidationPriceUsd) : p.liq)}</b><small>{p.liqPct.toFixed(1)}% {side === 'long' ? 'drop' : 'pump'}</small></span>
      <span><em>OPEN FEE</em><b className="m-num">{cash(q ? Number(q.openFeeUsd) : p.fee)}</b><small>{q ? 'Jupiter quote' : 'estimate'}</small></span>
      <div className="rp-rail" aria-hidden="true"><s className="rp-zone" style={{ left: side === 'long' ? 0 : `${rail}%`, right: side === 'long' ? `${100 - rail}%` : 0 }} /><i className="rp-liq" style={{ left: `${rail}%` }}>☠</i><i className="rp-now" /></div>
    </div> : <p className="rp-dim">Reading {asset}'s live price…</p>}
    {built ? <div className={`rp-quote ${ok ? '' : 'is-bad'}`} data-testid="rp-quote"><b>JUPITER'S QUOTE</b><span>{String(q?.side || side).toUpperCase()} {asset} · entry {px(Number(q?.entryPriceUsd))} · size {cash(Number(q?.positionSizeUsd || usd * lev))} · wiped at {px(Number(q?.liquidationPriceUsd))}</span>
      {!ok ? <small>The quote does not match your ticket — nothing to sign. Review again.</small> : null}</div> : null}
    <button type="button" className={`m-btn m-go rp-go is-${side}`} disabled={!!busy || !p || (built && !ok)} onClick={built ? open : review} data-testid="rp-go"
      data-tip={built ? 'Your wallet signs Jupiter\'s transaction; Jupiter\'s keeper lands it' : 'Get Jupiter\'s real quote + the transaction (nothing is signed yet)'}>
      {busy || (!addr ? '🔌 Connect wallet to trade' : built ? `⚡ SIGN + OPEN ${side.toUpperCase()} ${asset} ${lev}×` : `REVIEW ${side.toUpperCase()} ${asset} · ${cash(usd)} × ${lev}×`)}</button>
    {pos.length ? <ol className="rp-pos">{pos.map((x, i) => { const dist = x.mark && x.liq ? Math.abs(x.mark - x.liq) / x.mark * 100 : null;
      return <li key={x.pubkey} className={(x.pnl || 0) >= 0 ? 'is-up' : 'is-dn'} style={{ '--i': i }} data-testid={`rp-pos-${i}`}>
        <b className={`rp-tag is-${x.side}`}>{x.side === 'long' ? '▲' : '▼'} {x.asset} {x.lev}×</b>
        <span className="rp-n"><em className="m-num">{sgn(x.pnl)}</em><small>{x.pnlPct != null ? `${x.pnlPct >= 0 ? '+' : ''}${x.pnlPct.toFixed(1)}%` : ''} · size {cash(x.size)} · fees {cash(x.fees)} apart</small></span>
        <span className="rp-meter" data-tip={`Entry ${px(x.entry)} · now ${px(x.mark)} · wiped at ${px(x.liq)}`}><u><s style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, (dist || 0) / 50))})` }} /></u><small>{dist != null ? `${dist.toFixed(1)}% to liq` : ''}</small></span>
        <button type="button" className="m-btn" disabled={!!busy} onClick={() => close(x)} data-tip="Close it all — USDC back to your wallet" data-testid={`rp-close-${i}`}>Close</button></li>; })}</ol> : null}
    <p className="rp-lede">⚠ Perps can wipe your collateral fast: at {lev}× a {(100 / lev).toFixed(1)}% move against you liquidates it. Jupiter runs the market; FEELESS never holds your money.</p>
  </section>;
}
