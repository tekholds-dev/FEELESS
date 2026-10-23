import { apiUrl } from './api';
import { lendSign } from './lendEarn';
import { engineQuote, engineSwap } from './swapEngine';
import { USDC_MINT } from './launchRail';

// ⚡ REAL LEVERAGE (backend/lend_borrow.py · docs/DECISIONS.md #7): a Jupiter Lend loan opened from the user's OWN wallet — ① lock the coin
// + borrow USDC (one transaction Jupiter builds, the server checks, the chain simulates, the wallet signs) → ② the borrowed USDC buys more of
// the coin through the FEELESS swap engine. Close = ① sell enough to repay → ② repay all + unlock all. FEELESS never holds funds or keys.
// Each open is remembered on this device (Jupiter's own position list is read too) so the desk can show its P&L and close it.
export const SIZES = [10, 25, 100, 250];
const KEY = a => `feeless.lev.${a}`;
const YEAR_MS = 3.156e10;
const ui = (v, dec) => { const d = Math.min(dec, 9); return (Math.floor(v * 10 ** d + 1e-6) / 10 ** d).toFixed(d); };   // round DOWN, float-safe

// pure: the same math the server checks (lend_borrow.plan), for the live preview. usd = the money you lock.
export function levPlan(m, usd, lev) {
  if (!m || !(m.price > 0) || !(usd > 0)) return null;
  const L = Math.min(Math.max(1.05, Number(lev) || 1.05), m.maxLev); const col = usd / m.price; const debt = usd * (L - 1); const liq = debt / (col * m.lt);
  return { lev: L, col, usd, debt, exposure: col + debt / m.price, expUsd: usd + debt, liq, toLiqPct: (1 - liq / m.price) * 100,
    dayCost: (debt * m.borrowApr) / 100 / 365, tooSmall: debt < m.minDebt, minUsd: Math.ceil((m.minDebt / (L - 1)) * 1.02) };
}

// pure: an open position at `price` — P&L on the price move (never fees; the borrow interest so far shows apart), the liquidation distance
export function levPnl(r, price, now = Date.now()) {
  if (!r || !(price > 0)) return null;
  const coins = r.col + (r.bought ? r.debt / r.entry : 0); const owe = r.debt * (1 + ((r.apr / 100) * Math.max(0, now - r.at)) / YEAR_MS);
  return { pnl: coins * (price - r.entry), pnlPct: ((coins * (price - r.entry)) / (r.col * r.entry)) * 100, interest: owe - r.debt, owe, toLiqPct: (1 - r.liq / price) * 100 };
}

export const readLev = addr => { try { const v = JSON.parse(localStorage.getItem(KEY(addr)) || '[]'); return Array.isArray(v) ? v : []; } catch { return []; } };
const writeLev = (addr, rows) => { try { localStorage.setItem(KEY(addr), JSON.stringify(rows.slice(0, 20))); } catch { /* private window: the desk still reads Jupiter's list */ } };

export async function levMarkets(address) {
  const r = await fetch(apiUrl(`/api/reputation/familia/leverage?address=${encodeURIComponent(address || '')}`));
  if (!r.ok) throw new Error('Leverage markets did not load');
  return r.json();
}

async function build(body) {
  const r = await fetch(apiUrl('/api/reputation/familia/leverage'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const b = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(b.detail || 'Could not build it.');
  return b;
}

export async function levOpen({ provider, address, m, usd, lev, onStatus }) {
  const col = ui(usd / m.price, m.dec);
  onStatus?.('① Building the loan with Jupiter…');
  const q = await build({ address, act: 'open', vaultId: m.vaultId, col, lev });
  const sig = await lendSign({ provider, address, quote: q, onStatus: s => onStatus?.(`① ${s}`) });
  const rec = { nftId: q.nftId, vaultId: m.vaultId, coin: m.coin, mint: m.mint, dec: m.dec, col: Number(col), debt: q.plan.debt, entry: m.price,
    lev: q.plan.lev, liq: q.plan.liq, apr: m.borrowApr, at: Date.now(), sig, bought: false };
  writeLev(address, [rec, ...readLev(address).filter(r => r.nftId !== rec.nftId)]);
  await levBuy({ provider, address, rec, onStatus });
  return rec;
}

// ② the borrowed USDC buys the coin (also the retry when ② failed after ① landed — the USDC sits in the wallet meanwhile)
export async function levBuy({ provider, address, rec, onStatus }) {
  onStatus?.(`② Quoting ${rec.coin} with the borrowed USDC…`);
  const order = await engineQuote({ inputMint: USDC_MINT, outputMint: rec.mint, amount: ui(rec.debt * 0.998, 6), wallet: address });
  await engineSwap({ provider, wallet: address, order, onStatus: s => onStatus?.(`② ${s}`) });
  writeLev(address, readLev(address).map(r => (r.nftId === rec.nftId ? { ...r, bought: true } : r)));
}

export async function levClose({ provider, address, rec, price, onStatus }) {
  if (rec.bought && price > 0) {   // ① sell enough of the coin to repay: the loan + interest so far + 2 % room (the change stays as USDC)
    const owe = (levPnl(rec, price)?.owe || rec.debt) * 1.02 + 0.05;
    onStatus?.(`① Selling ${rec.coin} to repay…`);
    const order = await engineQuote({ inputMint: rec.mint, outputMint: USDC_MINT, amount: ui(owe / price, rec.dec ?? 9), wallet: address });
    await engineSwap({ provider, wallet: address, order, onStatus: s => onStatus?.(`① ${s}`) });
    writeLev(address, readLev(address).map(r => (r.nftId === rec.nftId ? { ...r, bought: false } : r)));
  }
  onStatus?.('② Repaying + unlocking…');
  const q = await build({ address, act: 'close', vaultId: rec.vaultId, nftId: rec.nftId });
  const sig = await lendSign({ provider, address, quote: q, onStatus: s => onStatus?.(`② ${s}`) });
  writeLev(address, readLev(address).filter(r => r.nftId !== rec.nftId));
  return sig;
}
