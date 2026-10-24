import { apiUrl } from './api';

// 📉 FEELESS PERPS — the desk's pure math + the one wallet-signing path (Jupiter Perps; backend/jup_perps.py builds + verifies every transaction).
// Nothing here holds money: the wallet signs, Jupiter's keeper co-signs and lands it.

export const MKTS = ['SOL', 'ETH', 'BTC'];
export const FEE_PCT = 0.06;   // Jupiter's open (and close) fee on the position size, % — the pool row overrides it live

// the ticket preview before Jupiter's quote: size, $ per 1 % move, the open fee, the liquidation price + distance (before borrow fees)
export function perpPlan(mark, usd, lev, side, feePct = FEE_PCT) {
  if (!(mark > 0) || !(usd > 0) || !(lev > 0)) return null;
  const size = usd * lev; const fee = (size * feePct) / 100; const move = Math.max(0, (usd - fee) / size);
  return { size, fee, per1: size / 100, liq: side === 'long' ? mark * (1 - move) : mark * (1 + move), liqPct: move * 100 };
}

// Jupiter's quote must match the ticket on screen before the wallet opens (side, and size within 10 % — at 100× the fees come out of it)
export const quoteMatches = (q, side, size) => !!q && String(q.side || side).toLowerCase() === side && Math.abs(Number(q.positionSizeUsd || q.sizeUsdDelta || size) - size) <= size * 0.1 + 0.5;

// what a trigger price does to this ticket: the move %, $ P&L before fees, ROE on the collateral, and whether it sits on the right side
export function atPrice(px, mark, usd, lev, side) {
  if (!(px > 0) || !(mark > 0) || !(usd > 0)) return null;
  const move = (px / mark - 1) * (side === 'long' ? 1 : -1); const pnl = usd * lev * move;
  return { move: move * 100, pnl, roe: (pnl / usd) * 100 };
}
export const tpOk = (tp, mark, side) => !tp || (side === 'long' ? tp > mark : tp < mark);
export const slOk = (sl, mark, side, liq) => !sl || (side === 'long' ? sl < mark && (!liq || sl > liq) : sl > mark && (!liq || sl < liq));
// a TP / SL a % away from the price, on the side that makes it a TP or an SL
export const levelAt = (mark, pct, side, kind) => (mark > 0 ? mark * (1 + ((kind === 'tp') === (side === 'long') ? 1 : -1) * pct / 100) : null);
// reward : risk of a TP / SL pair (null until both exist)
export const rr = (tp, sl, mark) => (tp > 0 && sl > 0 && mark > 0 && Math.abs(mark - sl) > 0 ? Math.abs(tp - mark) / Math.abs(mark - sl) : null);

// a live position marked at the live price: P&L before fees, ROE, how far the price can go before liquidation
export function liveRow(p, mark) {
  const m = mark > 0 ? mark : p.mark; if (!(m > 0) || !(p.entry > 0) || !(p.size > 0)) return { ...p, live: p.mark };
  const dir = p.side === 'long' ? 1 : -1; const pnl = p.size * (m / p.entry - 1) * dir;
  return { ...p, live: m, pnl, pnlPct: p.collateral > 0 ? (pnl / p.collateral) * 100 : p.pnlPct, toLiq: p.liq > 0 ? Math.abs(m - p.liq) / m * 100 : null };
}

export async function post(path, body) {
  const r = await fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'The venue said no.'); return b;
}
// the wallet signs the venue's transaction (only if it is for THIS wallet); `send` posts the signed bytes to the right executor
export async function signTx(provider, address, b64) {
  const { VersionedTransaction } = await import('@solana/web3.js');
  const tx = VersionedTransaction.deserialize(Uint8Array.from(atob(b64), c => c.charCodeAt(0)));
  if (tx.message.staticAccountKeys[0].toBase58() !== address) throw new Error('This transaction is not for your wallet — refused.');
  const signed = await provider.signTransaction(tx);
  return btoa(String.fromCharCode(...signed.serialize()));
}
export async function signRun(provider, address, built) {   // Jupiter: the wallet signs, Jupiter's keeper co-signs + lands it
  const signed = await signTx(provider, address, built.transaction);
  return post('/api/reputation/familia/perps-real/execute', { address, action: built.action, signed });
}
