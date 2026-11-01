// 🌊 THE COLONY POOL (owner 2026-10-31: "I chose Meteora — how do I create a pool with the colony wallet?"). Builds Meteora DAMM v2's
// createCustomPool for FEECAT / SOL with the colony wallet as payer + creator, via Meteora's own SDK (@meteora-ag/cp-amm-sdk). Fees COMPOUND
// into the pool (collectFeeMode 2) so it only grows; the liquidity stays UNLOCKED (owner: it is partly disbursed). This script NEVER sends: it returns the transaction
// (signed only by the new position NFT's throwaway key) and a free on-chain SIMULATION. The Circle sidecar signs it for real only after the
// owner approves amounts in HQ. stdin: { rpc, payer, mintA, amountA, amountB, feeBps, compoundingBps, lock } → stdout JSON.
import { Connection, Keypair, PublicKey, VersionedTransaction, TransactionMessage } from '@solana/web3.js';
import BN from 'bn.js';
import { CpAmm, MIN_SQRT_PRICE, MAX_SQRT_PRICE, getBaseFeeParams, getDynamicFeeParams, BaseFeeMode, CollectFeeMode, getTokenProgram, derivePoolAddress, deriveCustomizablePoolAddress } from '@meteora-ag/cp-amm-sdk';
import { getMint } from '@solana/spl-token';

const WSOL = new PublicKey('So11111111111111111111111111111111111111112');
const read = async () => { let s = ''; for await (const c of process.stdin) s += c; return JSON.parse(s || '{}'); };
const units = (ui, dec) => new BN(String(Math.round(Number(ui) * 10 ** Math.min(dec, 9)))).mul(new BN(10).pow(new BN(Math.max(0, dec - 9))));

try {
  const p = await read();
  const conn = new Connection(p.rpc, 'confirmed');
  const payer = new PublicKey(p.payer); const mintA = new PublicKey(p.mintA);
  const infoA = await conn.getAccountInfo(mintA); if (!infoA) throw new Error('FEECAT mint not found on chain');
  const progA = infoA.owner;   // the mint's own token program (pump.fun coins can be Token-2022)
  const decA = (await getMint(conn, mintA, 'confirmed', progA)).decimals;
  const amountA = units(p.amountA, decA); const amountB = units(p.amountB, 9);
  const cp = new CpAmm(conn);
  const { initSqrtPrice, liquidityDelta } = cp.preparePoolCreationParams({ tokenAAmount: amountA, tokenBAmount: amountB, minSqrtPrice: MIN_SQRT_PRICE, maxSqrtPrice: MAX_SQRT_PRICE, collectFeeMode: CollectFeeMode.Compounding });
  const fee = Math.max(25, Math.min(500, Number(p.feeBps) || 100));
  const baseFee = getBaseFeeParams({ baseFeeMode: BaseFeeMode.FeeTimeSchedulerLinear, feeTimeSchedulerParam: { startingFeeBps: fee, endingFeeBps: fee, numberOfPeriod: 0, totalDuration: 0 } });
  const positionNft = Keypair.generate();
  const { tx, pool, position } = await cp.createCustomPool({
    payer, creator: payer, positionNft: positionNft.publicKey, tokenAMint: mintA, tokenBMint: WSOL, tokenAAmount: amountA, tokenBAmount: amountB,
    sqrtMinPrice: MIN_SQRT_PRICE, sqrtMaxPrice: MAX_SQRT_PRICE, initSqrtPrice, liquidityDelta,
    poolFees: { baseFee, compoundingFeeBps: Math.max(0, Math.min(10000, Number(p.compoundingBps) || 5000)), padding: 0, dynamicFee: getDynamicFeeParams(fee) },
    hasAlphaVault: false, activationType: 1, collectFeeMode: CollectFeeMode.Compounding, activationPoint: null,
    tokenAProgram: progA, tokenBProgram: getTokenProgram(0), isLockLiquidity: p.lock === true,   // owner 2026-10-31: NOT locked — the colony pool's liquidity is partly paid back out over time
  });
  const { blockhash } = await conn.getLatestBlockhash('confirmed');
  const msg = new TransactionMessage({ payerKey: payer, recentBlockhash: blockhash, instructions: tx.instructions }).compileToV0Message();
  const vtx = new VersionedTransaction(msg); vtx.sign([positionNft]);   // the throwaway position key signs; the colony wallet signs later via Circle
  const sim = await conn.simulateTransaction(vtx, { sigVerify: false, replaceRecentBlockhash: true });
  console.log(JSON.stringify({ ok: true, pool: pool.toBase58(), position: position.toBase58(), positionNft: positionNft.publicKey.toBase58(),
    price: Number(p.amountB) / Number(p.amountA), decA, tx: Buffer.from(vtx.serialize()).toString('base64'),
    sim: { err: sim.value.err, units: sim.value.unitsConsumed, logs: (sim.value.logs || []).slice(-8) } }));
} catch (e) {
  console.log(JSON.stringify({ ok: false, error: String(e?.message || e).slice(0, 300) }));
}
