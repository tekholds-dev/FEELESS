import { keepReceipt } from './receipts';
import { relayConnection, signSend } from './launchRail';

// 🔌 IN-PLACE LP (owner, 2026-10-23: "I tightened a v3 pool with $100 and made $120 — no redirects"): join a Meteora DAMM v2 pool from FEELESS.
// Built in the browser with Meteora's own SDK, SIMULATED first (nothing is signed if the chain would reject it), signed by the user's wallet,
// which supplies both sides. FEELESS never holds the funds. The position is an NFT in the user's wallet; fees accrue to it.
export const SOL = 'So11111111111111111111111111111111111111112';

async function sdk() {
  const [{ web3, connection }, amm, BN] = await Promise.all([relayConnection(), import('@meteora-ag/cp-amm-sdk'), import('bn.js').then(m => m.default)]);
  return { web3, connection, amm, BN, client: new amm.CpAmm(connection) };
}

// pure: the other side with slippage head-room, as integer base units (BN-free so it is testable)
export const withSlip = (units, bps = 100) => (BigInt(units) * BigInt(10000 + Number(bps))) / 10000n;

// the deposit for `solAmount` SOL into `pool`: how much of the coin it needs, and whether the wallet holds it
export async function dammQuote({ pool, solAmount, owner = null }) {
  const { web3, connection, amm, BN, client } = await sdk();
  const poolPk = new web3.PublicKey(pool); const ps = await client.fetchPoolState(poolPk);
  const aIsSol = ps.tokenAMint.toBase58() === SOL; const bIsSol = ps.tokenBMint.toBase58() === SOL;
  if (!aIsSol && !bIsSol) throw new Error('Only SOL pools can be joined from here.');
  const lamports = new BN(Math.floor(Number(solAmount) * 1e9)); if (lamports.lten(0)) throw new Error('Type an amount above zero.');
  const q = client.getDepositQuote({ inAmount: lamports, isTokenA: aIsSol, minSqrtPrice: ps.sqrtMinPrice, maxSqrtPrice: ps.sqrtMaxPrice, sqrtPrice: ps.sqrtPrice,
    collectFeeMode: ps.collectFeeMode, tokenAAmount: ps.tokenAAmount, tokenBAmount: ps.tokenBAmount, liquidity: ps.liquidity });
  const coin = aIsSol ? ps.tokenBMint : ps.tokenAMint;
  const mintInfo = await connection.getParsedAccountInfo(coin); const decimals = mintInfo.value?.data?.parsed?.info?.decimals ?? 6;
  let held = null;
  if (owner) {   // the coin side the wallet already holds (every token account of that mint)
    const accts = await connection.getParsedTokenAccountsByOwner(new web3.PublicKey(owner), { mint: coin }).catch(() => ({ value: [] }));
    held = accts.value.reduce((s, a) => s + BigInt(a.account.data.parsed.info.tokenAmount.amount || '0'), 0n);
  }
  const need = BigInt(q.outputAmount.toString());
  return { pool, ps, aIsSol, coin: coin.toBase58(), decimals, lamports: lamports.toString(), coinUnits: need.toString(), coinUi: Number(need) / 10 ** decimals,
    liquidityDelta: q.liquidityDelta.toString(), held: held == null ? null : held.toString(), short: held == null ? null : held < withSlip(need) };
}

// open a position + add the liquidity in ONE transaction (the position NFT keypair co-signs); returns the signature + the position NFT
export async function dammJoin({ provider, owner, quote, slippageBps = 100, onStatus }) {
  const { web3, connection, amm, BN, client } = await sdk();
  const ps = quote.ps; const payer = new web3.PublicKey(owner); const nft = web3.Keypair.generate();
  const coinMax = new BN(withSlip(quote.coinUnits, slippageBps).toString()); const solMax = new BN(quote.lamports);
  const [maxA, maxB] = quote.aIsSol ? [solMax, coinMax] : [coinMax, solMax];
  const tx = await client.createPositionAndAddLiquidity({ owner: payer, pool: new web3.PublicKey(quote.pool), positionNft: nft.publicKey, liquidityDelta: new BN(quote.liquidityDelta),
    maxAmountTokenA: maxA, maxAmountTokenB: maxB, tokenAAmountThreshold: maxA, tokenBAmountThreshold: maxB, tokenAMint: ps.tokenAMint, tokenBMint: ps.tokenBMint,
    tokenAProgram: amm.getTokenProgram(ps.tokenAFlag), tokenBProgram: amm.getTokenProgram(ps.tokenBFlag) });
  const signature = await signSend(web3, connection, provider, tx, payer, [nft], onStatus);
  keepReceipt(signature, owner, 'pool');   // the server's receipt kinds: an LP join files as a pool action
  return { signature, position: nft.publicKey.toBase58() };
}

// ⚡ THE ZAP (owner: "one-tap zap — swap half → join"): half the SOL buys the coin through FEELESS's own swap engine (simulated, the wallet signs,
// the server sends it once), then the other half + exactly what that bought joins the pool (simulated, the wallet signs). Two signatures, one tap.
// If the price moved between the two, the join shrinks its SOL side to fit the coin the swap really delivered — never asks for more.
export async function dammZap({ provider, owner, pool, coin, solAmount, onStatus, steps = null }) {
  const { engineQuote, engineSwap } = await import('./swapEngine');
  const half = Math.floor((Number(solAmount) / 2) * 1e9) / 1e9; if (!(half > 0)) throw new Error('Type an amount above zero.');
  onStatus?.('Quoting the swap…'); const order = await engineQuote({ inputMint: SOL, outputMint: coin, amount: half.toFixed(9), wallet: owner });
  steps?.({ swap: { sol: half, out: order.quote.outAmount } });
  const swap = await engineSwap({ provider, wallet: owner, order, onStatus });
  onStatus?.('Swap confirmed — quoting the join…');
  let q = await dammQuote({ pool, solAmount: half, owner });
  if (q.short && Number(q.held) > 0) q = await dammQuote({ pool, solAmount: half * (Number(q.held) / Number(withSlip(q.coinUnits))) * 0.995, owner });   // fit the coin we really got
  if (q.short) throw new Error('The swap landed but the coin side is still short — join with what you hold from the pool row.');
  const join = await dammJoin({ provider, owner, quote: q, onStatus });
  return { swap: swap.signature, ...join };
}
