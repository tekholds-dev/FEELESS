import { apiUrl } from './api';

// FEELESS launch rail on Meteora's Dynamic Bonding Curve. Everything here builds transactions in
// the browser for the user's own wallet to sign. The only keypairs created are the new config /
// mint addresses, which sign once to prove the address and are then discarded.
export const RAIL_DEFAULTS = { initialMarketCap: 30, migrationMarketCap: 500, startingFeeBps: 5000, endingFeeBps: 100, feeDecayMin: 5, creatorFeePct: 50, lockedLpPct: 100, supply: 1_000_000_000 };

// Solana connection through the server's allowlisted relay, so the RPC key never reaches the browser.
export async function relayConnection() {
  const [web3, { Buffer }] = await Promise.all([import('@solana/web3.js'), import('buffer')]);
  if (typeof window !== 'undefined' && !window.Buffer) window.Buffer = Buffer;
  return { web3, connection: new web3.Connection(`${window.location.origin}${apiUrl('/api/reputation/rpc')}`, { commitment: 'confirmed', disableRetryOnRateLimit: true }) };
}

async function sdk() {
  const [{ web3, connection }, dbc] = await Promise.all([relayConnection(), import('@meteora-ag/dynamic-bonding-curve-sdk')]);
  return { web3, dbc, connection, client: new dbc.DynamicBondingCurveClient(connection, 'confirmed') };
}

export function curveFor(dbc, p = RAIL_DEFAULTS) {
  const { buildCurveWithMarketCap, BaseFeeMode, CollectFeeMode, MigrationOption, MigrationFeeOption, TokenType, TokenDecimal, TokenAuthorityOption, ActivationType } = dbc;
  const locked = Math.round(Number(p.lockedLpPct));
  return buildCurveWithMarketCap({
    token: { tokenType: TokenType.SPLToken, tokenBaseDecimal: TokenDecimal.SIX, tokenQuoteDecimal: 9, tokenAuthorityOption: TokenAuthorityOption.Immutable, totalTokenSupply: Number(p.supply), leftover: 0 },
    // Anti-snipe: fees start high and decay to the base fee over the first minutes of trading.
    fee: { baseFeeParams: { baseFeeMode: BaseFeeMode.FeeSchedulerExponential, feeSchedulerParam: { startingFeeBps: Number(p.startingFeeBps), endingFeeBps: Number(p.endingFeeBps), numberOfPeriod: 30, totalDuration: Number(p.feeDecayMin) * 60 } },
      dynamicFeeEnabled: true, collectFeeMode: CollectFeeMode.QuoteToken, creatorTradingFeePercentage: Number(p.creatorFeePct), poolCreationFee: 0, enableFirstSwapWithMinFee: false },
    migration: { migrationOption: MigrationOption.MET_DAMM_V2, migrationFeeOption: MigrationFeeOption.FixedBps100, migrationFee: { feePercentage: 0, creatorFeePercentage: 0 } },
    // Graduated liquidity is split partner/creator; the locked share can never be pulled.
    liquidityDistribution: { partnerPermanentLockedLiquidityPercentage: Math.floor(locked / 2), partnerLiquidityPercentage: 50 - Math.floor(locked / 2), creatorPermanentLockedLiquidityPercentage: Math.ceil(locked / 2), creatorLiquidityPercentage: 50 - Math.ceil(locked / 2) },
    lockedVesting: { totalLockedVestingAmount: 0, numberOfVestingPeriod: 0, cliffUnlockAmount: 0, totalVestingDuration: 0, cliffDurationFromMigrationTime: 0 },
    activationType: ActivationType.Timestamp,
    initialMarketCap: Number(p.initialMarketCap), migrationMarketCap: Number(p.migrationMarketCap),
  });
}

export async function signSend(web3, connection, provider, tx, payer, extraSigners, onStatus) {
  const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('confirmed');
  tx.feePayer = payer; tx.recentBlockhash = blockhash;
  // Dry-run first: nothing is signed if the chain would reject it.
  const sim = await connection.simulateTransaction(new web3.VersionedTransaction(tx.compileMessage()), { sigVerify: false });
  if (sim.value.err) throw new Error(`Simulation failed: ${JSON.stringify(sim.value.err)} ${(sim.value.logs || []).slice(-2).join(' ')}`);
  extraSigners.forEach(k => tx.partialSign(k));
  onStatus?.('Approve in your wallet…');
  const signed = await provider.signTransaction(tx);
  const sig = await connection.sendRawTransaction(signed.serialize(), { skipPreflight: true, maxRetries: 3 });
  onStatus?.('Confirming on Solana…');
  for (let i = 0; i < 60; i++) {
    const st = (await connection.getSignatureStatuses([sig])).value[0];
    if (st?.err) throw new Error(`Transaction failed on-chain: ${JSON.stringify(st.err)}`);
    if (st?.confirmationStatus === 'confirmed' || st?.confirmationStatus === 'finalized') return sig;
    if ((await connection.getBlockHeight('confirmed')) > lastValidBlockHeight) throw new Error('Transaction expired before it landed. Nothing was spent; try again.');
    await new Promise(r => setTimeout(r, 1500));
  }
  throw new Error(`Still confirming — check ${sig} on Solscan before retrying.`);
}

// Owner, once: create the FEELESS launch config on-chain.
export async function createLaunchRail({ provider, owner, feeClaimer, params, onStatus }) {
  const { web3, dbc, connection, client } = await sdk();
  const payer = new web3.PublicKey(owner);
  const config = web3.Keypair.generate();
  const tx = await client.partner.createConfig({ ...curveFor(dbc, params), config: config.publicKey, feeClaimer: new web3.PublicKey(feeClaimer), leftoverReceiver: new web3.PublicKey(feeClaimer), quoteMint: web3.NATIVE_MINT || new web3.PublicKey('So11111111111111111111111111111111111111112'), payer });
  const signature = await signSend(web3, connection, provider, tx, payer, [config], onStatus);
  return { config: config.publicKey.toBase58(), signature };
}

// Any creator: launch a coin on the FEELESS config, optionally buying first in the same transaction.
export async function launchCoin({ provider, creator, config, name, symbol, uri, firstBuySol = 0, onStatus }) {
  const { web3, connection, client } = await sdk();
  const BN = (await import('bn.js')).default;
  const payer = new web3.PublicKey(creator);
  const mint = web3.Keypair.generate();
  const createPoolParam = { name, symbol, uri, payer, poolCreator: payer, config: new web3.PublicKey(config), baseMint: mint.publicKey };
  const tx = firstBuySol > 0
    ? await client.creator.createPoolWithFirstBuy({ createPoolParam, firstBuyParam: { buyer: payer, buyAmount: new BN(Math.round(firstBuySol * 1e9)), minimumAmountOut: new BN(1), referralTokenAccount: null } })
    : await client.creator.createPool(createPoolParam);
  const signature = await signSend(web3, connection, provider, tx, payer, [mint], onStatus);
  return { mint: mint.publicKey.toBase58(), signature };
}

export async function fetchLaunchRail() {
  const r = await fetch(apiUrl('/api/reputation/launch-rail'));
  return r.ok ? r.json() : { ready: false };
}
