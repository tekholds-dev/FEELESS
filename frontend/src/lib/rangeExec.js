import { keepReceipt } from './receipts';
import { relayConnection, signSend } from './launchRail';

// 🤖 AUTORANGE, FOR REAL (owner 2026-10-26: "wire AutoRange's real opens and re-centers — build the tx, simulate it, my wallet signs").
// Two venues, each with its OWN SDK, built in the browser through the FEELESS RPC relay:
//   • Meteora DLMM  (@meteora-ag/dlmm)          — a position over bins [minBin, maxBin], liquidity spread evenly (Spot)
//   • Raydium CLMM  (@raydium-io/raydium-sdk-v2) — a position NFT over ticks [lower, upper]
// Every transaction is SIMULATED on mainnet first (signSend: nothing is signed if the chain would reject it), then the user's wallet signs.
// FEELESS never holds the funds or the position: the position belongs to the wallet. RE-CENTER = close the old position (its fees are claimed
// with it) → open the new band — each a transaction the wallet signs. Rent: a new position locks a refundable deposit (returned on close);
// a DLMM range that touches untouched bins may also pay a one-time bin-array rent (not refundable) — `dlmmCost` says how much BEFORE signing.
export const SOL = 'So11111111111111111111111111111111111111112';
export const DLMM_MAX_BINS = 69;   // one position, one transaction (the SDK's default position length is 70 bins)

// ── pure helpers (tested) ──
// a ±band (lo … hi around the live price) → DLMM bin ids around the active bin, capped to one position; reports the width it really covers
export function binRange(lo, hi, price, activeId, binStep) {
  const step = Math.log(1 + binStep / 10000);
  let down = Math.max(1, Math.ceil(Math.log(price / lo) / step)); let up = Math.max(1, Math.ceil(Math.log(hi / price) / step));
  while (down + up + 1 > DLMM_MAX_BINS) { if (down >= up) down -= 1; else up -= 1; }
  return { minBinId: activeId - down, maxBinId: activeId + up, bins: down + up + 1, loPct: (1 - Math.exp(-down * step)) * 100, hiPct: (Math.exp(up * step) - 1) * 100, capped: down + up + 1 >= DLMM_MAX_BINS };
}
// how a $ deposit splits for a centered band: half the value in each coin (in UI units of each), given the coins' USD prices
export function halves(usd, pxX, pxY) { return { x: usd / 2 / pxX, y: usd / 2 / pxY }; }
const atoms = (ui, dec) => BigInt(Math.floor(Number(ui) * 10 ** dec));

async function base() {
  const [{ web3, connection }, BN] = await Promise.all([relayConnection(), import('bn.js').then(m => m.default)]);
  return { web3, connection, BN };
}

// ── Meteora DLMM ──
async function dlmmPool(ctx, pool) { const mod = await import('@meteora-ag/dlmm'); const DLMM = mod.default; return { mod, p: await DLMM.create(ctx.connection, new ctx.web3.PublicKey(pool)) }; }

/** the plan for a DLMM band: bins, the real width covered, the Y side for an X amount, and the rent it locks / spends — read before signing */
export async function dlmmPlan({ pool, w, xUi, ctx = null }) {
  const c = ctx || await base(); const { mod, p } = await dlmmPool(c, pool);
  const active = await p.getActiveBin(); const step = p.lbPair.binStep; const price = Number(p.fromPricePerLamport(Number(active.price)));
  const k = 1 + w / 100; const r = binRange(price / k, price * k, price, active.binId, step);
  const decX = p.tokenX.mint.decimals; const decY = p.tokenY.mint.decimals;
  const totalX = new c.BN(atoms(xUi, decX).toString());
  const totalY = mod.autoFillYByStrategy(active.binId, step, totalX, active.xAmount, active.yAmount, r.minBinId, r.maxBinId, mod.StrategyType.Spot);
  let cost = null;
  try { const q = await p.quoteCreatePosition({ strategy: { minBinId: r.minBinId, maxBinId: r.maxBinId, strategyType: mod.StrategyType.Spot } });
    cost = { binArrays: q.binArraysCount, binArraySol: Number(q.binArrayCost), positionSol: Number(q.positionCost) }; } catch { /* older pools: no quote */ }
  return { venue: 'meteora', pool, price, activeId: active.binId, ...r, binStep: step, mintX: p.tokenX.publicKey.toBase58(), mintY: p.tokenY.publicKey.toBase58(), decX, decY,
    x: totalX.toString(), y: totalY.toString(), yUi: Number(totalY.toString()) / 10 ** decY, cost };
}

export async function dlmmOpen({ provider, owner, plan, onStatus, ctx = null }) {
  const c = ctx || await base(); const { mod, p } = await dlmmPool(c, plan.pool);
  const user = new c.web3.PublicKey(owner); const pos = c.web3.Keypair.generate();
  onStatus?.('Building the band…');
  const tx = await p.initializePositionAndAddLiquidityByStrategy({ positionPubKey: pos.publicKey, user, totalXAmount: new c.BN(plan.x), totalYAmount: new c.BN(plan.y),
    strategy: { minBinId: plan.minBinId, maxBinId: plan.maxBinId, strategyType: mod.StrategyType.Spot }, slippage: 1 });
  const signature = await signSend(c.web3, c.connection, provider, tx, user, [pos], onStatus);
  keepReceipt(signature, owner, 'pool');
  return { signature, position: pos.publicKey.toBase58() };
}

export async function dlmmPositions({ owner, pool, ctx = null }) {
  const c = ctx || await base(); const { p } = await dlmmPool(c, pool);
  const { activeBin, userPositions } = await p.getPositionsByUserAndLbPair(new c.web3.PublicKey(owner));
  const decX = p.tokenX.mint.decimals; const decY = p.tokenY.mint.decimals;
  return userPositions.map(u => { const d = u.positionData; return { venue: 'meteora', pool, position: u.publicKey.toBase58(), lowerBinId: d.lowerBinId, upperBinId: d.upperBinId,
    inRange: activeBin.binId >= d.lowerBinId && activeBin.binId <= d.upperBinId, xUi: Number(d.totalXAmount) / 10 ** decX, yUi: Number(d.totalYAmount) / 10 ** decY,
    feeXUi: Number(d.feeX?.toString() || 0) / 10 ** decX, feeYUi: Number(d.feeY?.toString() || 0) / 10 ** decY }; });
}

/** withdraw 100 % + claim its fees + close it (one or more transactions — each simulated, each signed) */
export async function dlmmClose({ provider, owner, pool, position, onStatus, ctx = null }) {
  const c = ctx || await base(); const { p } = await dlmmPool(c, pool); const user = new c.web3.PublicKey(owner);
  const pos = await p.getPosition(new c.web3.PublicKey(position));
  const txs = await p.removeLiquidity({ user, position: pos.publicKey, fromBinId: pos.positionData.lowerBinId, toBinId: pos.positionData.upperBinId, bps: new c.BN(10000), shouldClaimAndClose: true });
  const sigs = [];
  for (const [i, tx] of (Array.isArray(txs) ? txs : [txs]).entries()) { onStatus?.(`Closing the old band (${i + 1}/${(Array.isArray(txs) ? txs : [txs]).length})…`); sigs.push(await signSend(c.web3, c.connection, provider, tx, user, [], onStatus)); }
  sigs.forEach(s => keepReceipt(s, owner, 'pool'));
  return { signatures: sigs };
}

// ── Raydium CLMM ──
async function ray(ctx, owner) {
  const [R, Dec] = await Promise.all([import('@raydium-io/raydium-sdk-v2'), import('decimal.js').then(m => m.default)]);
  const raydium = await R.Raydium.load({ connection: ctx.connection, owner: new ctx.web3.PublicKey(owner), cluster: 'mainnet', disableFeatureCheck: true, disableLoadToken: true, blockhashCommitment: 'confirmed' });
  return { R, Dec, raydium };
}

/** the plan for a Raydium band: ticks (snapped to the pool's spacing), the B side for an A amount (with 2 % head-room) */
export async function rayPlan({ owner, pool, w, aUi, ctx = null }) {
  const c = ctx || await base(); const { R, Dec, raydium } = await ray(c, owner);
  const { poolInfo, poolKeys } = await raydium.clmm.getPoolInfoFromRpc(pool); const k = 1 + w / 100; const px = Number(poolInfo.price);
  const tickAt = v => R.TickUtil.getPriceAndTick({ price: new Dec(v), mintADecimals: poolInfo.mintA.decimals, mintBDecimals: poolInfo.mintB.decimals, zeroForOne: true, tickSpacing: poolInfo.config.tickSpacing }).tick;
  const t1 = tickAt(px / k); const t2 = tickAt(px * k);
  const tickLower = Math.min(t1, t2); const tickUpper = Math.max(t1, t2);
  if (tickLower === tickUpper) throw new Error('That band is narrower than one tick of this pool — widen it.');
  const epochInfo = await raydium.fetchEpochInfo(); const decA = poolInfo.mintA.decimals; const decB = poolInfo.mintB.decimals;
  const amount = new c.BN(atoms(aUi, decA).toString());
  const res = await R.PoolUtils.getLiquidityAmountOutFromAmountIn({ poolInfo, slippage: 0, inputA: true, tickUpper, tickLower, amount, add: true, amountHasFee: true, epochInfo });
  const bMax = new c.BN(res.amountSlippageB.amount.toString()).muln(102).divn(100);
  return { venue: 'raydium', pool, poolInfo, poolKeys, tickLower, tickUpper, price: Number(poolInfo.price), mintA: poolInfo.mintA.address, mintB: poolInfo.mintB.address, decA, decB,
    a: amount.toString(), bMax: bMax.toString(), bUi: Number(bMax.toString()) / 10 ** decB };
}

export async function rayOpen({ provider, owner, plan, onStatus, ctx = null }) {
  const c = ctx || await base(); const { R, raydium } = await ray(c, owner);
  onStatus?.('Building the band…');
  const built = await raydium.clmm.openPositionFromBase({ poolInfo: plan.poolInfo, poolKeys: plan.poolKeys, tickLower: plan.tickLower, tickUpper: plan.tickUpper, base: 'MintA',
    ownerInfo: { useSOLBalance: true }, baseAmount: new c.BN(plan.a), otherAmountMax: new c.BN(plan.bMax), txVersion: R.TxVersion.V0,
    computeBudgetConfig: { units: 600000, microLamports: 50000 } });
  const signature = await signSend(c.web3, c.connection, provider, built.transaction, new c.web3.PublicKey(owner), built.signers || [], onStatus);
  keepReceipt(signature, owner, 'pool');
  return { signature, position: built.extInfo?.nftMint?.toBase58?.() || null };
}

export async function rayPositions({ owner, pool, ctx = null }) {
  const c = ctx || await base(); const { raydium } = await ray(c, owner);
  const { poolInfo, computePoolInfo } = await raydium.clmm.getPoolInfoFromRpc(pool);
  const all = await raydium.clmm.getOwnerPositionInfo({ programId: poolInfo.programId });
  const cur = computePoolInfo?.tickCurrent ?? 0;
  return all.filter(x => x.poolId.toBase58() === pool && !x.liquidity.isZero()).map(x => ({ venue: 'raydium', pool, position: x.nftMint.toBase58(), tickLower: x.tickLower, tickUpper: x.tickUpper,
    inRange: cur >= x.tickLower && cur < x.tickUpper, liquidity: x.liquidity.toString() }));
}

export async function rayClose({ provider, owner, pool, position, onStatus, ctx = null }) {
  const c = ctx || await base(); const { R, raydium } = await ray(c, owner);
  const { poolInfo, poolKeys } = await raydium.clmm.getPoolInfoFromRpc(pool);
  const all = await raydium.clmm.getOwnerPositionInfo({ programId: poolInfo.programId });
  const pos = all.find(x => x.nftMint.toBase58() === position); if (!pos) throw new Error('That position is not in this wallet any more.');
  const epochInfo = await raydium.fetchEpochInfo();
  const out = await R.PoolUtils.getAmountsFromLiquidity({ poolInfo, tickLower: pos.tickLower, tickUpper: pos.tickUpper, liquidity: pos.liquidity, slippage: 0.02, add: false, epochInfo });
  const built = await raydium.clmm.decreaseLiquidity({ poolInfo, poolKeys, ownerPosition: pos, ownerInfo: { useSOLBalance: true, closePosition: true }, liquidity: pos.liquidity,
    amountMinA: new c.BN(out.amountSlippageA.amount.toString()), amountMinB: new c.BN(out.amountSlippageB.amount.toString()), txVersion: R.TxVersion.V0,
    computeBudgetConfig: { units: 600000, microLamports: 50000 } });
  onStatus?.('Closing the old band…');
  const signature = await signSend(c.web3, c.connection, provider, built.transaction, new c.web3.PublicKey(owner), built.signers || [], onStatus);
  keepReceipt(signature, owner, 'pool');
  return { signatures: [signature] };
}

// ── one door for the desk ──
export const venueOf = row => (row?.venue === 'raydium' ? 'raydium' : row?.venue === 'meteora' ? 'meteora' : null);
export async function positionsOf({ owner, row }) { return venueOf(row) === 'raydium' ? rayPositions({ owner, pool: row.pool }) : dlmmPositions({ owner, pool: row.pool }); }
export async function closeBand({ provider, owner, row, position, onStatus }) {
  return venueOf(row) === 'raydium' ? rayClose({ provider, owner, pool: row.pool, position, onStatus }) : dlmmClose({ provider, owner, pool: row.pool, position, onStatus });
}

/** 💸 THE ZAP: $ in SOL → both sides of the pool → a ±w % band on the pool's own price → open it. The FEELESS swap engine buys each side that is
 *  not SOL (simulated, the wallet signs each); only what THOSE swaps delivered goes in (never coins the wallet already held), and the band shrinks to
 *  fit if one side came up short. xUsd = the USD price of the pool's X coin. `planOnly` = read the band + its rent with no swap, nothing signed. */
export async function zapOpen({ provider, owner, row, usd, w, solPx, xUsd, onStatus, planOnly = false }) {
  const { engineQuote, engineSwap } = await import('./swapEngine');
  const c = await base(); const X = row.mintX; const Y = row.mintY; const sigs = []; const ray_ = venueOf(row) === 'raydium';
  const bal = async m => { if (m === SOL) return (await c.connection.getBalance(new c.web3.PublicKey(owner))) / 1e9;
    const a = await c.connection.getParsedTokenAccountsByOwner(new c.web3.PublicKey(owner), { mint: new c.web3.PublicKey(m) }).catch(() => ({ value: [] }));
    return a.value.reduce((s, x) => s + Number(x.account.data.parsed.info.tokenAmount.uiAmount || 0), 0); };
  const got = { [X]: X === SOL ? usd / 2 / solPx : usd / 2 / xUsd, [Y]: Y === SOL ? usd / 2 / solPx : null };
  if (!planOnly) for (const m of [X, Y]) {
    if (m === SOL) continue;
    onStatus?.(`Buying the ${m === X ? row.symX : row.symY} side…`); const before = await bal(m);
    const order = await engineQuote({ inputMint: SOL, outputMint: m, amount: (usd / 2 / solPx).toFixed(9), wallet: owner });
    sigs.push((await engineSwap({ provider, wallet: owner, order, onStatus })).signature);
    got[m] = Math.max(0, (await bal(m)) - before);
  }
  const planFor = xUi => (ray_ ? rayPlan({ owner, pool: row.pool, w, aUi: xUi, ctx: c }) : dlmmPlan({ pool: row.pool, w, xUi, ctx: c }));
  onStatus?.('Reading the band…');
  let plan = await planFor(got[X] * 0.995);
  const needY = ray_ ? plan.bUi : plan.yUi;
  if (!planOnly && got[Y] != null && needY > got[Y] * 0.995) plan = await planFor(got[X] * 0.995 * (got[Y] * 0.99 / needY));   // fit the side we really have
  if (planOnly) return { plan, sigs };
  const open = ray_ ? await rayOpen({ provider, owner, plan, onStatus, ctx: c }) : await dlmmOpen({ provider, owner, plan, onStatus, ctx: c });
  return { plan, sigs: [...sigs, open.signature], position: open.position };
}

/** ⟲ RE-CENTER: close the old band (its fees come with it) → open a ±w % band on the live price with EXACTLY what the close returned (the wallet's
 *  balance change), keeping RENT_KEEP SOL back for the new position's refundable deposit. Every step simulated; the wallet signs each. */
export const RENT_KEEP = 0.08;
export async function recenter({ provider, owner, row, position, w, onStatus }) {
  const c = await base(); const X = row.mintX; const Y = row.mintY; const ray_ = venueOf(row) === 'raydium';
  const bal = async m => { if (m === SOL) return (await c.connection.getBalance(new c.web3.PublicKey(owner))) / 1e9;
    const a = await c.connection.getParsedTokenAccountsByOwner(new c.web3.PublicKey(owner), { mint: new c.web3.PublicKey(m) }).catch(() => ({ value: [] }));
    return a.value.reduce((s, x) => s + Number(x.account.data.parsed.info.tokenAmount.uiAmount || 0), 0); };
  const [x0, y0] = await Promise.all([bal(X), bal(Y)]);
  const closed = await closeBand({ provider, owner, row, position, onStatus });
  const [x1, y1] = await Promise.all([bal(X), bal(Y)]);
  const dx = Math.max(0, x1 - x0 - (X === SOL ? RENT_KEEP : 0)); const dy = Math.max(0, y1 - y0 - (Y === SOL ? RENT_KEEP : 0));
  if (!(dx > 0) && !(dy > 0)) throw new Error('The old band closed but returned nothing to re-open with.');
  const planFor = xUi => (ray_ ? rayPlan({ owner, pool: row.pool, w, aUi: xUi, ctx: c }) : dlmmPlan({ pool: row.pool, w, xUi, ctx: c }));
  onStatus?.('Reading the new band…');
  let plan = await planFor(dx * 0.995); const needY = ray_ ? plan.bUi : plan.yUi;
  if (needY > dy * 0.995 && needY > 0) plan = await planFor(dx * 0.995 * (dy * 0.99 / needY));
  const open = ray_ ? await rayOpen({ provider, owner, plan, onStatus, ctx: c }) : await dlmmOpen({ provider, owner, plan, onStatus, ctx: c });
  return { plan, sigs: [...closed.signatures, open.signature], position: open.position };
}
