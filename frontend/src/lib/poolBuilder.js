import { relayConnection, signSend } from './launchRail';

// Meteora DAMM v2 pool for an existing token, paired with SOL. Built in the browser, simulated,
// then signed by the connected wallet — which also supplies both sides of the liquidity.
const SOL = 'So11111111111111111111111111111111111111112';

async function sdk() {
  const [{ web3, connection }, amm, BN] = await Promise.all([relayConnection(), import('@meteora-ag/cp-amm-sdk'), import('bn.js').then(m => m.default)]);
  return { web3, connection, amm, BN, client: new amm.CpAmm(connection) };
}

// What the pool would be: mint decimals/program, and whether this pair already has a custom pool.
export async function inspectPool(mint) {
  const { web3, connection, amm } = await sdk();
  const a = new web3.PublicKey(mint);
  const info = await connection.getParsedAccountInfo(a);
  const parsed = info.value?.data?.parsed;
  if (parsed?.type !== 'mint') throw new Error('That address is not a token mint.');
  const pool = amm.deriveCustomizablePoolAddress(a, new web3.PublicKey(SOL));
  const exists = Boolean((await connection.getAccountInfo(pool))?.data);
  return { decimals: parsed.info.decimals, supply: Number(parsed.info.supply) / 10 ** parsed.info.decimals, program: info.value.owner.toBase58(), freeze: Boolean(parsed.info.freezeAuthority), pool: pool.toBase58(), exists };
}

export async function createSolPool({ provider, owner, mint, tokenAmount, solAmount, feeBps, launchFeeBps, launchMinutes, lock, onStatus }) {
  const { web3, connection, amm, BN, client } = await sdk();
  const meta = await inspectPool(mint);
  if (meta.exists) throw new Error('A FEELESS-style pool for this token/SOL pair already exists.');
  const payer = new web3.PublicKey(owner);
  const aAmt = new BN(BigInt(Math.round(Number(tokenAmount) * 10 ** meta.decimals)).toString());
  const bAmt = new BN(Math.round(Number(solAmount) * 1e9));
  const { initSqrtPrice, liquidityDelta } = client.preparePoolCreationParams({ tokenAAmount: aAmt, tokenBAmount: bAmt, minSqrtPrice: amm.MIN_SQRT_PRICE, maxSqrtPrice: amm.MAX_SQRT_PRICE, collectFeeMode: amm.CollectFeeMode.OnlyB });
  // Optional anti-snipe: fee starts at launchFeeBps and decays to feeBps over launchMinutes.
  const decay = Number(launchFeeBps) > Number(feeBps) && Number(launchMinutes) > 0;
  const baseFee = amm.getBaseFeeParams({ baseFeeMode: amm.BaseFeeMode.FeeTimeSchedulerExponential,
    feeTimeSchedulerParam: decay ? { startingFeeBps: Number(launchFeeBps), endingFeeBps: Number(feeBps), numberOfPeriod: 30, totalDuration: Number(launchMinutes) * 60 } : { startingFeeBps: Number(feeBps), endingFeeBps: Number(feeBps), numberOfPeriod: 0, totalDuration: 0 } });
  const nft = web3.Keypair.generate();
  const { tx, pool } = await client.createCustomPool({ payer, creator: payer, positionNft: nft.publicKey, tokenAMint: new web3.PublicKey(mint), tokenBMint: new web3.PublicKey(SOL),
    tokenAAmount: aAmt, tokenBAmount: bAmt, sqrtMinPrice: amm.MIN_SQRT_PRICE, sqrtMaxPrice: amm.MAX_SQRT_PRICE, liquidityDelta, initSqrtPrice,
    poolFees: { baseFee, compoundingFeeBps: 0, padding: 0, dynamicFee: amm.getDynamicFeeParams(Number(feeBps)) }, hasAlphaVault: false,
    activationType: amm.ActivationType.Timestamp, collectFeeMode: amm.CollectFeeMode.OnlyB, activationPoint: null,
    tokenAProgram: new web3.PublicKey(meta.program), tokenBProgram: new web3.PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'), isLockLiquidity: Boolean(lock) });
  const signature = await signSend(web3, connection, provider, tx, payer, [nft], onStatus);
  return { pool: pool.toBase58(), signature };
}
