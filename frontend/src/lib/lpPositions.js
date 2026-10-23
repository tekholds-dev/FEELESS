import { useEffect, useState } from 'react';
import { keepReceipt } from './receipts';
import { relayConnection, signSend } from './launchRail';
import { getSolPrice } from './solPrice';

// 🏗 YOUR LP POSITIONS, LIVE (owner, 2026-10-23: "show my LP positions as live buildings in my family town — fees earned, in range or not —
// with claim / remove / close in place"): every Meteora DAMM v2 position the wallet holds (its NFT), read straight from the chain with Meteora's
// SDK: what it is worth now, the fees it has earned and not claimed, whether the price sits inside the pool's range (= earning). Claim, remove
// (keep the position) and close (remove + close, the rent comes back) are built in the browser, SIMULATED, then the wallet signs.
export const SOL = 'So11111111111111111111111111111111111111112';
const Q64 = 2 ** 64;

async function sdk() {
  const [{ web3, connection }, amm, BN] = await Promise.all([relayConnection(), import('@meteora-ag/cp-amm-sdk'), import('bn.js').then(m => m.default)]);
  return { web3, connection, amm, BN, client: new amm.CpAmm(connection) };
}
const decCache = new Map();
async function decimalsOf(connection, mint) {
  const k = mint.toBase58(); if (decCache.has(k)) return decCache.get(k);
  const info = await connection.getParsedAccountInfo(mint); const d = info.value?.data?.parsed?.info?.decimals ?? 6; decCache.set(k, d); return d;
}
const poolMeta = new Map();   // pool → { name, coinSym, feeDay } from Meteora's own data API (labels + today's fee pace), 5 min
async function metaOf(pool) {
  const hit = poolMeta.get(pool); if (hit && Date.now() - hit.at < 300000) return hit.v;
  const v = await fetch(`https://damm-v2.datapi.meteora.ag/pools/${pool}`).then(r => (r.ok ? r.json() : null)).catch(() => null);
  const out = v ? { name: v.name, x: v.token_x?.symbol, y: v.token_y?.symbol, feeDay: v.tvl ? ((Number(v.fees?.['24h']) || 0) - (Number(v.protocol_fees?.['24h']) || 0)) / v.tvl : null } : null;
  poolMeta.set(pool, { at: Date.now(), v: out }); return out;
}

// pure: a position's numbers from raw units — the SOL side + the coin side (valued at the pool's own price), unclaimed fees, in range
export function positionView({ aIsSol, amountA, amountB, feeA, feeB, decA, decB, sqrtPrice, sqrtMin, sqrtMax, solUsd }) {
  const ui = (u, d) => Number(u) / 10 ** d; const pAinB = (Number(sqrtPrice) / Q64) ** 2 * 10 ** (decA - decB);   // price of 1 A in B
  const coinInSol = aIsSol ? (pAinB > 0 ? 1 / pAinB : 0) : pAinB;
  const [solU, coinU, fSol, fCoin] = aIsSol ? [ui(amountA, decA), ui(amountB, decB), ui(feeA, decA), ui(feeB, decB)] : [ui(amountB, decB), ui(amountA, decA), ui(feeB, decB), ui(feeA, decA)];
  const sol = solU + coinU * coinInSol; const feeSol = fSol + fCoin * coinInSol;
  const inRange = Number(sqrtPrice) > Number(sqrtMin) && Number(sqrtPrice) < Number(sqrtMax);
  return { solAmt: solU, coinAmt: coinU, feeSolAmt: fSol, feeCoinAmt: fCoin, valueSol: sol, feeValueSol: feeSol, valueUsd: solUsd ? sol * solUsd : null, feeUsd: solUsd ? feeSol * solUsd : null, inRange, coinInSol };
}

export async function readPositions(owner) {
  const { web3, connection, amm, client } = await sdk(); const me = new web3.PublicKey(owner);
  const [list, solUsd] = await Promise.all([client.getPositionsByUser(me), getSolPrice().catch(() => null)]);
  const out = [];
  for (const it of list) {
    const pos = it.positionState; const ps = await client.fetchPoolState(pos.pool);
    const aIsSol = ps.tokenAMint.toBase58() === SOL; if (!aIsSol && ps.tokenBMint.toBase58() !== SOL) continue;   // SOL pools only (what the desk joins)
    const [decA, decB, meta] = await Promise.all([decimalsOf(connection, ps.tokenAMint), decimalsOf(connection, ps.tokenBMint), metaOf(pos.pool.toBase58())]);
    const liq = pos.unlockedLiquidity.add(pos.vestedLiquidity).add(pos.permanentLockedLiquidity);
    const w = liq.isZero() ? { outAmountA: 0, outAmountB: 0 } : client.getWithdrawQuote({ liquidityDelta: liq, sqrtPrice: ps.sqrtPrice, minSqrtPrice: ps.sqrtMinPrice, maxSqrtPrice: ps.sqrtMaxPrice,
      collectFeeMode: ps.collectFeeMode, tokenAAmount: ps.tokenAAmount, tokenBAmount: ps.tokenBAmount, liquidity: ps.liquidity });
    const fee = amm.getUnClaimLpFee(ps, pos);
    const v = positionView({ aIsSol, amountA: w.outAmountA.toString(), amountB: w.outAmountB.toString(), feeA: fee.feeTokenA.toString(), feeB: fee.feeTokenB.toString(), decA, decB,
      sqrtPrice: ps.sqrtPrice.toString(), sqrtMin: ps.sqrtMinPrice.toString(), sqrtMax: ps.sqrtMaxPrice.toString(), solUsd });
    const coinSym = (aIsSol ? meta?.y : meta?.x) || (aIsSol ? ps.tokenBMint : ps.tokenAMint).toBase58().slice(0, 4);
    out.push({ id: it.position.toBase58(), position: it.position.toBase58(), nftAccount: it.positionNftAccount.toBase58(), pool: pos.pool.toBase58(), sym: meta?.name || `${coinSym}-SOL`, coinSym,
      coin: (aIsSol ? ps.tokenBMint : ps.tokenAMint).toBase58(), feeDay: meta?.feeDay ?? null, empty: liq.isZero(), locked: !pos.vestedLiquidity.isZero() || !pos.permanentLockedLiquidity.isZero(),
      ...v, solUsd });
  }
  return out.sort((a, b) => (b.valueSol || 0) - (a.valueSol || 0));
}

// one shared read per wallet a minute (the block, the desk and the city all ask)
const cache = new Map();
export function positionsOf(owner, fresh = false) {
  const hit = cache.get(owner); if (hit && !fresh && Date.now() - hit.at < 60000) return hit.p;
  const entry = { at: Date.now(), p: readPositions(owner).catch(() => { cache.delete(owner); return null; }) }; cache.set(owner, entry); return entry.p;
}
export function useLpPositions(owner) {
  const [rows, setRows] = useState(null); const [tick, setTick] = useState(0);
  useEffect(() => { if (!owner || (typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent || ''))) return undefined;   // tests never read the chain
    let alive = true; const go = f => positionsOf(owner, f).then(x => alive && x && setRows(x));
    go(tick > 0); const t = setInterval(() => { if (!document.hidden) go(false); }, 60000);
    const bump = () => setTick(n => n + 1); window.addEventListener('feeless:lp-changed', bump);
    return () => { alive = false; clearInterval(t); window.removeEventListener('feeless:lp-changed', bump); }; }, [owner, tick]);
  return rows;
}
export const lpChanged = () => window.dispatchEvent(new Event('feeless:lp-changed'));

// ✍ the actions — each built with Meteora's SDK, simulated first (signSend), signed by the wallet
async function prep(owner, position) {
  const s = await sdk(); const pk = new s.web3.PublicKey(position); const pos = await s.client.fetchPositionState(pk); const ps = await s.client.fetchPoolState(pos.pool);
  const nftAcct = (await s.client.getPositionsByUser(new s.web3.PublicKey(owner))).find(x => x.position.equals(pk))?.positionNftAccount;
  if (!nftAcct) throw new Error('That position is not in this wallet.');
  return { ...s, pk, pos, ps, nftAcct, me: new s.web3.PublicKey(owner), progA: s.amm.getTokenProgram(ps.tokenAFlag), progB: s.amm.getTokenProgram(ps.tokenBFlag) };
}
// pure: the least each side may come back as when removing (slippage floor, default 2 %) — never 0, so a moved price can't empty it
export const floorOut = (units, bps = 200) => (BigInt(units) * BigInt(10000 - Number(bps))) / 10000n;

export async function lpAction({ provider, owner, position, act, onStatus }) {
  const x = await prep(owner, position); const { client, amm, BN, connection, pos, ps, pk, nftAcct, me, progA, progB } = x;
  let tx;
  if (act === 'claim') {
    tx = await client.claimPositionFee({ owner: me, position: pk, pool: pos.pool, positionNftAccount: nftAcct, tokenAMint: ps.tokenAMint, tokenBMint: ps.tokenBMint,
      tokenAVault: ps.tokenAVault, tokenBVault: ps.tokenBVault, tokenAProgram: progA, tokenBProgram: progB });
  } else {
    const liq = pos.unlockedLiquidity; if (liq.isZero()) throw new Error(act === 'close' ? 'Nothing left to remove.' : 'This position holds no removable liquidity.');
    const w = client.getWithdrawQuote({ liquidityDelta: liq, sqrtPrice: ps.sqrtPrice, minSqrtPrice: ps.sqrtMinPrice, maxSqrtPrice: ps.sqrtMaxPrice, collectFeeMode: ps.collectFeeMode,
      tokenAAmount: ps.tokenAAmount, tokenBAmount: ps.tokenBAmount, liquidity: ps.liquidity });
    const minA = new BN(floorOut(w.outAmountA.toString()).toString()); const minB = new BN(floorOut(w.outAmountB.toString()).toString());
    const currentPoint = await amm.getCurrentPoint(connection, ps.activationType);
    tx = act === 'close'
      ? await client.removeAllLiquidityAndClosePosition({ owner: me, position: pk, positionNftAccount: nftAcct, poolState: ps, positionState: pos, tokenAAmountThreshold: minA, tokenBAmountThreshold: minB, vestings: [], currentPoint })
      : await client.removeAllLiquidity({ owner: me, position: pk, pool: pos.pool, positionNftAccount: nftAcct, tokenAAmountThreshold: minA, tokenBAmountThreshold: minB, tokenAMint: ps.tokenAMint, tokenBMint: ps.tokenBMint,
        tokenAVault: ps.tokenAVault, tokenBVault: ps.tokenBVault, tokenAProgram: progA, tokenBProgram: progB, vestings: [], currentPoint });
  }
  const signature = await signSend(x.web3, connection, provider, tx, me, [], onStatus);
  keepReceipt(signature, owner, act === 'claim' ? 'claim' : 'pool'); lpChanged();
  return { signature };
}
