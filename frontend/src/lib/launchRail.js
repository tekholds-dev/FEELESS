import { keepReceipt } from './receipts';
import { apiUrl } from './api';

// FEELESS launch rail on Meteora's Dynamic Bonding Curve. Everything here builds transactions in
// the browser for the user's own wallet to sign. The only keypairs created are the new config /
// mint addresses, which sign once to prove the address and are then discarded.
export const RAIL_DEFAULTS = { initialMarketCap: 30, migrationMarketCap: 500, startingFeeBps: 9900, endingFeeBps: 100, feeDecayMin: 3, creatorFeePct: 50, lockedLpPct: 100, supply: 1_000_000_000, quote: 'SOL' };
export const USDC_MINT = 'EPjFWdd5AufqSSqeM2qJ1Mzybapc8G4wNGGkZwyTDt1v';

// Launch styles. Every preset keeps 100% of graduated liquidity locked (unruggable) and uses the strongest
// anti-snipe Meteora allows: a 99% launch fee that decays exponentially, plus volatility (dynamic) fees.
export const RAIL_PRESETS = [
  { id: 'shield', label: '🛡 Anti-snipe max', blurb: 'Block-0 snipers pay 99%, falling to 1% over 3 min. Best default.', params: { initialMarketCap: 30, migrationMarketCap: 500, startingFeeBps: 9900, endingFeeBps: 100, feeDecayMin: 3, creatorFeePct: 50, quote: 'SOL' } },
  { id: 'pump', label: '🚀 Pump classic', blurb: 'pump.fun-style low open and fast graduation, 1-minute snipe tax.', params: { initialMarketCap: 28, migrationMarketCap: 420, startingFeeBps: 9000, endingFeeBps: 100, feeDecayMin: 1, creatorFeePct: 30, quote: 'SOL' } },
  { id: 'reserve', label: '🏦 Deep reserve', blurb: 'Higher open, big graduation: slower candles, deep locked pool.', params: { initialMarketCap: 100, migrationMarketCap: 1500, startingFeeBps: 9900, endingFeeBps: 50, feeDecayMin: 5, creatorFeePct: 50, quote: 'SOL' } },
  { id: 'stable', label: '💵 Stable (USDC)', blurb: 'Curve priced in USDC: $5K open, $69K graduation. No SOL price swings.', params: { initialMarketCap: 5000, migrationMarketCap: 69000, startingFeeBps: 9900, endingFeeBps: 100, feeDecayMin: 3, creatorFeePct: 50, quote: 'USDC' } },
  { id: 'burn', label: '🔥 Buy & burn', blurb: 'FEELESS share goes to a buy-back wallet (set it as fee claimer) to buy & burn.', params: { initialMarketCap: 30, migrationMarketCap: 500, startingFeeBps: 9900, endingFeeBps: 150, feeDecayMin: 3, creatorFeePct: 20, quote: 'SOL', buyBurn: 1 } },
];

// Plain-English red flags for a launch config (pure; shown before anyone signs).
export function railWarnings(p) {
  const w = [];
  const n = k => Number(p[k]) || 0;
  if (n('startingFeeBps') < 8000) w.push(`Snipers only pay ${n('startingFeeBps') / 100}% in block 0. Use 90%+ (max 99%) so sniping loses money.`);
  if (n('feeDecayMin') < 1) w.push('Anti-snipe window under 1 minute: bots just wait it out.');
  if (n('feeDecayMin') > 15) w.push(`A ${n('feeDecayMin')}-minute snipe tax also taxes real early buyers. 2–5 min is the sweet spot.`);
  if (n('endingFeeBps') > 200) w.push(`Normal fee ${n('endingFeeBps') / 100}% is steep: traders and bots route around coins above ~2%.`);
  if (n('endingFeeBps') < 25) w.push('Normal fee must be at least 0.25% (Meteora minimum).');
  if (n('startingFeeBps') > 9900) w.push('Launch fee max is 99% (9900 bps).');
  if (n('lockedLpPct') < 100) w.push(`${100 - n('lockedLpPct')}% of graduated liquidity stays withdrawable: that is a rug path.`);
  if (n('creatorFeePct') >= 100) w.push('Creator gets 100% of fees: FEELESS earns nothing from this config.');
  if (n('migrationMarketCap') <= n('initialMarketCap') * 2) w.push('Graduation market cap should be well above the opening one (5×+).');
  if (p.buyBurn && !p.feeClaimerSet) w.push('Buy & burn: set the fee claimer to your buy-back wallet.');
  return w;
}

// Dry-check the curve with Meteora's own validator; returns what it takes to graduate.
export async function checkRail(p, feeClaimer) {
  const [{ web3 }, dbc] = await Promise.all([relayConnection(), import('@meteora-ag/dynamic-bonding-curve-sdk')]);
  const c = curveFor(dbc, p);
  dbc.validateConfigParameters({ ...c, leftoverReceiver: new web3.PublicKey(feeClaimer) });
  const dec = p.quote === 'USDC' ? 6 : 9;
  return { raise: Number(c.migrationQuoteThreshold.toString()) / 10 ** dec, quote: p.quote === 'USDC' ? 'USDC' : 'SOL' };
}

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
    token: { tokenType: TokenType.SPLToken, tokenBaseDecimal: TokenDecimal.SIX, tokenQuoteDecimal: p.quote === 'USDC' ? 6 : 9, tokenAuthorityOption: TokenAuthorityOption.Immutable, totalTokenSupply: Number(p.supply), leftover: 0 },
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
  const versioned = tx instanceof web3.VersionedTransaction;
  if (versioned) tx.message.recentBlockhash = blockhash; else { tx.feePayer = payer; tx.recentBlockhash = blockhash; }
  // Dry-run first: nothing is signed if the chain would reject it.
  const sim = await connection.simulateTransaction(versioned ? tx : new web3.VersionedTransaction(tx.compileMessage()), { sigVerify: false });
  if (sim.value.err) throw new Error(`Simulation failed: ${JSON.stringify(sim.value.err)} ${(sim.value.logs || []).slice(-2).join(' ')}`);
  if (versioned) tx.sign(extraSigners); else extraSigners.forEach(k => tx.partialSign(k));
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
  const tx = await client.partner.createConfig({ ...curveFor(dbc, params), config: config.publicKey, feeClaimer: new web3.PublicKey(feeClaimer), leftoverReceiver: new web3.PublicKey(feeClaimer), quoteMint: new web3.PublicKey(params?.quote === 'USDC' ? USDC_MINT : 'So11111111111111111111111111111111111111112'), payer });
  const signature = await signSend(web3, connection, provider, tx, payer, [config], onStatus);
  keepReceipt(signature, owner, 'launch');
  return { config: config.publicKey.toBase58(), signature };
}

// Any creator: launch a coin on the FEELESS config, optionally buying first in the same transaction.
export async function launchCoin({ provider, creator, config, name, symbol, uri, firstBuySol = 0, quoteDecimals = 9, onStatus }) {
  const { web3, connection, client } = await sdk();
  const BN = (await import('bn.js')).default;
  const payer = new web3.PublicKey(creator);
  const mint = web3.Keypair.generate();
  const createPoolParam = { name, symbol, uri, payer, poolCreator: payer, config: new web3.PublicKey(config), baseMint: mint.publicKey };
  const tx = firstBuySol > 0
    ? await client.creator.createPoolWithFirstBuy({ createPoolParam, firstBuyParam: { buyer: payer, buyAmount: new BN(Math.round(firstBuySol * 10 ** quoteDecimals)), minimumAmountOut: new BN(1), referralTokenAccount: null } })
    : await client.creator.createPool(createPoolParam);
  const signature = await signSend(web3, connection, provider, tx, payer, [mint], onStatus);
  keepReceipt(signature, creator, 'launch');
  return { mint: mint.publicKey.toBase58(), signature };
}

// Creator fees on a FEELESS (Meteora DBC) coin: what the creator can claim right now, in SOL.
// null when the coin isn't on a bonding-curve pool.
export async function creatorFees(mint) {
  const { client } = await sdk();
  const pool = await client.state.getPoolByBaseMint(mint);
  if (!pool) return null;
  const m = await client.state.getPoolFeeMetrics(pool.publicKey);
  return { pool: pool.publicKey.toBase58(), creator: (pool.account.poolState || pool.account).creator.toBase58(), sol: Number(m.current.creatorQuoteFee.toString()) / 1e9 };
}

// The creator's wallet signs; fees go straight to it.
export async function claimCreatorFees({ provider, creator, mint, onStatus }) {
  const { web3, connection, client } = await sdk();
  const pool = await client.state.getPoolByBaseMint(mint);
  if (!pool) throw new Error('This coin has no FEELESS bonding-curve pool.');
  const m = await client.state.getPoolFeeMetrics(pool.publicKey);
  const payer = new web3.PublicKey(creator);
  const tx = await client.creator.claimCreatorTradingFee({ creator: payer, payer, pool: pool.publicKey, maxBaseAmount: m.current.creatorBaseFee, maxQuoteAmount: m.current.creatorQuoteFee });
  const signature = await signSend(web3, connection, provider, tx, payer, [], onStatus);
  keepReceipt(signature, creator, 'claim');
  return signature;
}

export async function fetchLaunchRail() {
  const r = await fetch(apiUrl('/api/reputation/launch-rail'));
  return r.ok ? r.json() : { ready: false };
}

// Pump.fun launch: FEELESS's server asks PumpPortal to build the create tx for this wallet; the new
// mint signs here and the creator's wallet signs last.
export async function launchOnPump({ provider, creator, session, form, onStatus }) {
  const { web3, connection } = await relayConnection();
  const mint = web3.Keypair.generate();
  onStatus?.('Uploading metadata to pump.fun…');
  const r = await fetch(apiUrl('/api/reputation/pump/create-tx'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address: creator, session, mint: mint.publicKey.toBase58(), name: form.name, symbol: form.symbol, description: form.description, image: form.imageUrl, website: form.website, twitter: form.twitter, telegram: form.telegram, devBuySol: Number(form.devBuyAmount) || 0 }) });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail || 'Pump.fun launch could not be prepared.');
  const tx = web3.VersionedTransaction.deserialize(Uint8Array.from(atob(body.tx), c => c.charCodeAt(0)));
  const signature = await signSend(web3, connection, provider, tx, new web3.PublicKey(creator), [mint], onStatus);
  keepReceipt(signature, creator, 'launch');
  return { mint: mint.publicKey.toBase58(), signature };
}
