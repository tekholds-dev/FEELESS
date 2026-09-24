const http = require('http');

const fs = require('fs');
const { URL } = require('url');
const nodeCrypto = require('crypto');
const { PublicKey, Keypair } = require('@solana/web3.js');
const { secp256k1 } = require('@noble/curves/secp256k1');
const { keccak_256 } = require('@noble/hashes/sha3');

const PORT = Number(process.env.API_PORT || 5001);
const DEX_API = process.env.DEX_API_URL || 'https://api.dexscreener.com';
const GECKO_API = process.env.GECKO_API_URL || 'https://api.geckoterminal.com/api/v2';
const GECKO_API_KEY = process.env.GECKO_API_KEY || process.env.COINGECKO_API_KEY || '';

const PUMP_API = process.env.PUMP_API_URL || 'https://frontend-api-v3.pump.fun';
const DEX_SITE = process.env.DEX_SITE_URL || 'https://dexscreener.com';
const MARKET_CACHE_RETENTION_MS = 14 * 24 * 60 * 60 * 1000;
const ASSET_THROTTLE_WARNING_COOLDOWN_MS = 60000;
const PROVIDER_RATE_LIMIT_COOLDOWN_MS = 15000;
const GECKO_NEW_ALL_PAGE_BUDGET = 3;
const JUPITER_API = process.env.JUPITER_API_URL || 'https://api.jup.ag';
const JUPITER_PUBLIC_QUOTE_API = process.env.JUPITER_QUOTE_API_URL || 'https://lite-api.jup.ag/swap/v1';
const JUPITER_API_KEY = process.env.JUPITER_API_KEY || '';
const SOLANA_RPC_URL = process.env.SOLANA_RPC_URL || '';
const TRADING_CONFIGURED = Boolean(JUPITER_API_KEY && SOLANA_RPC_URL);
const MINTS = {
  fee: process.env.FEE_MINT || '49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump',
  feecat: process.env.FEECAT_MINT || 'AsX2abSJ2HqPqRxUbeYXE5R5ksrmUDz6BMGpg9mDpump',
  rfee: process.env.RFEE_MINT || '2vZjg2w58k4urtdNWPnNHizuSxesLCoz5QqN9xxqNray',
};

const cache = new Map();
const pendingRequests = new Map();
const providerRateLimitCooldowns = new Map();
const assetThrottleWarningCooldown = new Map();
const rooms = new Map();
const orders = new Map();
const profiles = new Map();
const profileChallenges = new Map();
const verifiedWallets = new Map();
const messageLikes = new Map();
const profileFlags = new Map();
const chatLimits = new Map();
const paperCats = new Map();
const paperActivity = [];

const PAPER_STATE_VERSION = 1;
let paperMarketCache = { pairs: [], fetchedAt: 0, provider: null, error: null };
const PAPER_STARTING_SOL = 10;
const PAPER_MAX_STARTING_SOL = 100;
const PAPER_MAX_DAILY_BUY_SOL = 100;
const PAPER_STRATEGIES = {
  balanced: { label: 'Balanced scout', description: 'Looks for observed activity with balanced entry and exit rules.', targetGain: 4, stopLoss: 5 },
  momentum: { label: 'Momentum hunter', description: 'Only enters provider-observed tokens with positive short-term movement.', targetGain: 6, stopLoss: 4 },
  conservative: { label: 'Capital guard', description: 'Requires stronger liquidity and uses smaller, tighter positions.', targetGain: 3, stopLoss: 3 },
};
const PROFILE_CATEGORIES = ['Trader', 'Builder', 'Artist', 'Collector', 'Researcher'];
const PROFILE_COOLDOWN_MS = 120000;
const PROFILE_CHALLENGE_MS = 10 * 60 * 1000;
const GECKO_NETWORKS = {
  solana: 'solana',
  ethereum: 'eth',
  base: 'base',
  bsc: 'bsc',
  arbitrum: 'arbitrum',
  avalanche: 'avax',
  polygon: 'polygon_pos',
  sui: 'sui',
};
const REVERSE_GECKO_NETWORKS = Object.fromEntries(Object.entries(GECKO_NETWORKS).map(([chain, network]) => [network, chain]));
const SUPPORTED_MARKET_CHAINS = Object.keys(GECKO_NETWORKS);

function paperSecretFor(keypair) {
  const key = nodeCrypto.createHash('sha256')
    .update(process.env.SESSION_SECRET || 'feeless-paper-agent-preview-secret')
    .digest();
  const iv = nodeCrypto.randomBytes(12);
  const cipher = nodeCrypto.createCipheriv('aes-256-gcm', key, iv);
  const encrypted = Buffer.concat([cipher.update(Buffer.from(keypair.secretKey)), cipher.final()]);
  return `${iv.toString('base64')}.${cipher.getAuthTag().toString('base64')}.${encrypted.toString('base64')}`;
}

function cleanPaperList(value, max = 20) {
  return [...new Set(String(value || '').split(/[,\s]+/).map(item => item.trim().toUpperCase()).filter(Boolean))].slice(0, max);
}

function recoveryKeyHash(value) {
  return nodeCrypto.createHash('sha256')
    .update(`${process.env.SESSION_SECRET || 'feeless-paper-agent-preview-secret'}:${value}`)
    .digest('hex');
}

function newRecoveryKey() {
  return `FEE-CAT-${nodeCrypto.randomBytes(18).toString('base64url').toUpperCase()}`;
}

function paperWalletMode(value) {
  return value === 'assigned' ? 'assigned' : 'paper';
}

function coinPlan(value) {
  return value === 'create' ? 'create' : 'later';
}

function expirePaperCat(cat) {
  if (cat.expiredAt || cat.recoveryConfirmedAt || cat.fundedAt || !cat.recoveryExpiresAt) return;
  if (Date.now() < Date.parse(cat.recoveryExpiresAt)) return;
  cat.expiredAt = new Date().toISOString();
  cat.status = 'expired';
  if (!cat.expiryEventRecorded) {
    cat.expiryEventRecorded = true;
    paperEvent(cat, 'EXPIRED', 'Cat expired after 14 days without a saved recovery key or first funding deposit.');
  }
}

function paperStrategy(value) {
  const aliases = { breakouts: 'momentum', signals: 'momentum', trend: 'momentum', conviction: 'balanced', scalping: 'conservative' };
  const normalized = aliases[value] || value;
  return Object.prototype.hasOwnProperty.call(PAPER_STRATEGIES, normalized) ? normalized : 'balanced';
}

function paperPublicCat(cat) {
  expirePaperCat(cat);
  const strategy = PAPER_STRATEGIES[cat.strategy] || PAPER_STRATEGIES.balanced;
  const realized = Number(cat.realizedPnlSol || 0);
  const positionValue = (cat.positions || []).reduce((sum, position) => sum + Number(position.notionalSol || 0), 0);
  const wins = Number(cat.wins || 0);
  const losses = Number(cat.losses || 0);
  return {
    id: cat.id,
    ownerId: cat.ownerId,
    name: cat.name,
    handle: cat.handle,
    avatar: cat.avatar,
    mode: 'paper',
    wallet: cat.wallet,
    walletMode: cat.walletMode,
    walletLabel: cat.walletMode === 'assigned' ? 'Clean assigned Solana wallet' : 'Paper Solana wallet',
    status: cat.revoked ? 'revoked' : cat.status,
    createdAt: cat.createdAt,
    balanceSol: Number(cat.balanceSol.toFixed(6)),
    startingBalanceSol: Number((cat.startingBalanceSol || PAPER_STARTING_SOL).toFixed(6)),
    withdrawnSol: Number((cat.withdrawnSol || 0).toFixed(6)),
    realizedPnlSol: Number(realized.toFixed(6)),
    unrealizedPnlSol: Number((cat.unrealizedPnlSol || 0).toFixed(6)),
    totalPnlSol: Number((realized + Number(cat.unrealizedPnlSol || 0)).toFixed(6)),
    volumeSol: Number((cat.volumeSol || 0).toFixed(6)),
    feesSol: Number((cat.feesSol || 0).toFixed(6)),
    positions: cat.positions || [],
    tradeCount: Number(cat.tradeCount || 0),
    wins,
    losses,
    winRate: wins + losses ? Number(((wins / (wins + losses)) * 100).toFixed(1)) : null,
    xp: Number(cat.xp || 0),
    level: Math.max(1, Math.floor(Number(cat.xp || 0) / 100) + 1),
    pnlHistory: (cat.pnlHistory || []).slice(-60),
    strategy: cat.strategy,
    strategyLabel: strategy.label,
    strategyDescription: strategy.description,
    risk: cat.risk,
    lastCycleAt: cat.lastCycleAt || null,
    brain: cat.brain,
    coinPlan: cat.coinPlan,
    coinStatus: cat.coinStatus,
    recovery: {
      saved: Boolean(cat.recoveryConfirmedAt),
      expiresAt: cat.recoveryExpiresAt,
      expiredAt: cat.expiredAt || null,
      funded: Boolean(cat.fundedAt),
      needsAction: !cat.recoveryConfirmedAt && !cat.fundedAt,
    },
    controls: {
      emergencyStop: cat.status !== 'running',
      revoked: Boolean(cat.revoked),
      maxPositionSol: cat.risk.maxPositionSol,
      maxDailyLossSol: cat.risk.maxDailyLossSol,
      dailyBuyLimitSol: cat.risk.dailyBuyLimitSol,
      allowlist: cat.risk.allowlist,
      blocklist: cat.risk.blocklist,
    },
  };
}

function paperEvent(cat, type, detail, extra = {}) {
  cat.unrealizedPnlSol = (cat.positions || []).reduce((sum, position) => sum + position.notionalSol * ((position.currentChange - position.entryChange) / 100), 0);
  const event = {
    id: nodeCrypto.randomUUID(),
    catId: cat.id,
    catName: cat.name,
    mode: 'paper',
    type,
    detail,
    ts: new Date().toISOString(),
    ...extra,
  };
  paperActivity.unshift(event);
  if (paperActivity.length > 500) paperActivity.length = 500;
  cat.pnlHistory = cat.pnlHistory || [];
  cat.pnlHistory.push({ at: event.ts, value: Number((Number(cat.realizedPnlSol || 0) + Number(cat.unrealizedPnlSol || 0)).toFixed(6)) });
  if (cat.pnlHistory.length > 60) cat.pnlHistory.shift();
  persistPaperState();
  return event;
}

function paperCandidates() {
  return paperMarketCache.pairs || [];
}

async function refreshPaperMarket() {
  if (Date.now() - paperMarketCache.fetchedAt < 20000 && paperMarketCache.pairs.length) return paperMarketCache;
  try {
    const result = await dexBoostFeed('trending', 1, 'solana');
    paperMarketCache = { pairs: result.pairs || [], fetchedAt: Date.now(), provider: result.provider, error: result.error || null };
  } catch (error) {
    paperMarketCache = { ...paperMarketCache, fetchedAt: Date.now(), error: publicError(error), provider: error?.provider || 'public market provider' };
  }
  return paperMarketCache;
}

function paperTokenAllowed(cat, pair) {
  const symbol = String(pair?.baseToken?.symbol || '').toUpperCase();
  const mint = String(pair?.baseToken?.address || '').toUpperCase();
  const { allowlist = [], blocklist = [] } = cat.risk;
  if (blocklist.some(value => symbol === value || mint === value)) return false;
  return !allowlist.length || allowlist.some(value => symbol === value || mint === value);
}

async function runPaperCycle(cat) {
  if (!cat) return null;
  expirePaperCat(cat);
  if (!cat || cat.revoked || cat.expiredAt || cat.status !== 'running') return null;
  const market = await refreshPaperMarket();
  cat.lastCycleAt = new Date().toISOString();
  const today = cat.lastCycleAt.slice(0, 10);
  if (cat.lossDay !== today) {
    cat.lossDay = today;
    cat.dailyLossSol = 0;
    cat.dailyBuySol = 0;
    cat.buyDay = today;
  }
  if (!market.pairs.length) {
    return paperEvent(cat, 'WAITING', `No provider snapshot available. The paper engine did not trade.`, { provider: market.provider || 'public market provider', error: market.error || null });
  }
  const strategy = PAPER_STRATEGIES[cat.strategy] || PAPER_STRATEGIES.balanced;
  const candidate = market.pairs
    .filter(pair => paperTokenAllowed(cat, pair))
    .filter(pair => Number(pair?.liquidity?.usd || 0) >= (cat.strategy === 'conservative' ? 100000 : 10000))
    .sort((a, b) => Number(b?.priceChange?.h1 || b?.priceChange?.h24 || 0) - Number(a?.priceChange?.h1 || a?.priceChange?.h24 || 0))[0];
  if (!candidate) return paperEvent(cat, 'SCAN', 'Scanned provider markets; risk rules blocked every candidate.', { provider: market.provider || 'public market provider' });
  const symbol = candidate.baseToken?.symbol || 'TOKEN';
  const change = Number(candidate.priceChange?.h1 ?? candidate.priceChange?.h24 ?? 0);
  const position = cat.positions.find(item => item.mint === candidate.baseToken?.address);
  const dailyLoss = Number(cat.dailyLossSol || 0);
  if (dailyLoss >= cat.risk.maxDailyLossSol) {
    cat.status = 'stopped';
    return paperEvent(cat, 'STOPPED', `Daily loss limit reached at ${dailyLoss.toFixed(4)} SOL. Emergency stop engaged.`, { reason: 'max_daily_loss' });
  }
  if (!position && cat.balanceSol > 0 && (cat.strategy !== 'momentum' || change > 0)) {
    const remainingDailyBuy = Math.max(0, cat.risk.dailyBuyLimitSol - Number(cat.dailyBuySol || 0));
    const notional = Math.min(cat.risk.maxPositionSol, cat.balanceSol, remainingDailyBuy);
    if (notional <= 0) {
      return paperEvent(cat, 'LIMIT', `Daily paper buy limit reached at ${cat.risk.dailyBuyLimitSol.toFixed(4)} SOL. No order placed.`, { reason: 'daily_buy_limit', provider: market.provider || 'public market provider' });
    }
    const next = { mint: candidate.baseToken?.address || `${symbol}-provider-mint`, symbol, name: candidate.baseToken?.name || symbol, notionalSol: notional, entryChange: change, currentChange: change, provider: market.provider || 'public market provider', openedAt: new Date().toISOString() };
    cat.balanceSol -= notional;
    cat.dailyBuySol = Number(cat.dailyBuySol || 0) + notional;
    cat.volumeSol += notional;
    cat.tradeCount += 1;
    cat.xp += 25;
    cat.positions.push(next);
    return paperEvent(cat, 'BUY', `Paper entry opened within the ${cat.risk.maxPositionSol} SOL position limit.`, { symbol, mint: next.mint, notionalSol: notional, provider: next.provider, observedChange: change });
  }
  if (position) {
    position.currentChange = change;
    const exit = change >= strategy.targetGain || change <= -strategy.stopLoss;
    if (exit) {
      const pnl = position.notionalSol * (change - position.entryChange) / 100;
      const fee = Math.abs(position.notionalSol) * 0.001;
      cat.balanceSol += position.notionalSol + pnl - fee;
      cat.realizedPnlSol += pnl - fee;
      cat.feesSol += fee;
      cat.volumeSol += position.notionalSol;
      if (pnl > 0) cat.wins += 1; else cat.losses += 1;
      cat.dailyLossSol += Math.min(0, pnl - fee) * -1;
      cat.tradeCount += 1;
      cat.xp += 50;
      cat.positions = cat.positions.filter(item => item !== position);
      return paperEvent(cat, 'SELL', `Paper exit closed ${symbol} at the strategy threshold.`, { symbol, mint: position.mint, pnlSol: pnl - fee, feeSol: fee, provider: position.provider, observedChange: change });
    }
  }
  cat.unrealizedPnlSol = cat.positions.reduce((sum, item) => sum + item.notionalSol * ((item.currentChange - item.entryChange) / 100), 0);
  return paperEvent(cat, 'SCAN', `Observed ${symbol}; no strategy threshold was met. No order placed.`, { symbol, provider: market.provider || 'public market provider', observedChange: change });
}

function createPaperCat(body) {
  const name = String(body.name || '').trim().replace(/[^\w -]/g, '').slice(0, 24);
  if (name.length < 2) throw Object.assign(new Error('Cat name must be at least 2 characters.'), { statusCode: 400 });
  const handle = String(body.handle || name.toLowerCase().replace(/\s+/g, '-')).trim().toLowerCase();
  if (!/^[a-z0-9_-]{3,20}$/.test(handle)) throw Object.assign(new Error('Handle must be 3–20 characters using letters, numbers, _ or -.'), { statusCode: 400 });
  const ownerId = String(body.ownerId || '').trim().slice(0, 100);
  if (!ownerId) throw Object.assign(new Error('A browser owner id is required.'), { statusCode: 400 });
  const keypair = Keypair.generate();
  const id = nodeCrypto.randomUUID();
  const recoveryKey = newRecoveryKey();
  const startingBalance = Math.min(PAPER_MAX_STARTING_SOL, Math.max(0.1, Number(body.startingBalanceSol) || PAPER_STARTING_SOL));
  const maxPosition = Math.min(startingBalance, 2, Math.max(0.01, Number(body.maxPositionSol) || 0.25));
  const maxDailyLoss = Math.min(5, Math.max(0.01, Number(body.maxDailyLossSol) || 0.5));
  const dailyBuyLimit = Math.min(PAPER_MAX_DAILY_BUY_SOL, Math.max(0.01, Number(body.dailyBuyLimitSol) || Math.min(startingBalance, 2)));
  const cat = {
    id, ownerId, name, handle, avatar: String(body.avatar || 'mint').slice(0, 40),
    wallet: keypair.publicKey.toString(), encryptedPaperSecret: paperSecretFor(keypair),
    recoveryKeyHash: recoveryKeyHash(recoveryKey), recoveryExpiresAt: new Date(Date.now() + (14 * 24 * 60 * 60 * 1000)).toISOString(),
    recoveryConfirmedAt: null, fundedAt: null, expiredAt: null, expiryEventRecorded: false,
    mode: 'paper', walletMode: paperWalletMode(body.walletMode), brain: String(body.brain || 'rule-engine').slice(0, 40),
    coinPlan: coinPlan(body.coinPlan), coinStatus: body.coinPlan === 'create' ? 'planned' : 'not_selected',
    createdAt: new Date().toISOString(), status: 'stopped', revoked: false,
    startingBalanceSol: startingBalance, balanceSol: startingBalance, withdrawnSol: 0, realizedPnlSol: 0, unrealizedPnlSol: 0, volumeSol: 0, feesSol: 0,
    positions: [], tradeCount: 0, wins: 0, losses: 0, xp: 0, dailyLossSol: 0, dailyBuySol: 0, lossDay: new Date().toISOString().slice(0, 10), buyDay: new Date().toISOString().slice(0, 10), lastCycleAt: null,
    strategy: paperStrategy(body.strategy),
    instructions: String(body.instructions || '').slice(0, 500),
    thinkEvery: String(body.thinkEvery || '15 min').slice(0, 20),
    bio: String(body.bio || '').slice(0, 160),
    xHandle: String(body.xHandle || '').slice(0, 40),
    pnlHistory: [],
    risk: { maxPositionSol: maxPosition, maxDailyLossSol: maxDailyLoss, dailyBuyLimitSol: dailyBuyLimit, allowlist: cleanPaperList(body.allowlist), blocklist: cleanPaperList(body.blocklist) },
  };
  paperCats.set(id, cat);
  paperEvent(cat, 'CREATED', 'Paper Cat created. No SOL was deposited and no on-chain transaction occurred.');
  return { cat, recoveryKey };
}

function paperStateSnapshot() {
  return {
    version: PAPER_STATE_VERSION,
    cats: Array.from(paperCats.values()),
    activity: paperActivity.slice(0, 500),
  };
}
function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Origin': '*',
  });
  res.end(payload);
}

function publicError(error) {
  return error?.message || 'Public market provider unavailable.';
}

function tradingError() {
  return 'Trading execution is not configured. Add backend Jupiter and Solana RPC settings.';
}

function requireTrading() {
  if (!TRADING_CONFIGURED) throw Object.assign(new Error(tradingError()), { statusCode: 503 });
}

async function rpc(method, params) {
  requireTrading();
  const response = await fetch(SOLANA_RPC_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw Object.assign(new Error('Solana RPC unavailable. No transaction was submitted.'), { statusCode: 503 });
  const data = await response.json();
  if (data.error) throw Object.assign(new Error('Solana RPC rejected the request.'), { statusCode: 503 });
  return data.result;
}

async function jupiter(method, path, options = {}) {
  requireTrading();
  const response = await fetch(`${JUPITER_API}${path}`, {
    method,
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'x-api-key': JUPITER_API_KEY },
    ...options,
    signal: AbortSignal.timeout(25000),
  });
  const data = await response.json();
  if (!response.ok) {
    throw Object.assign(new Error(data?.errorMessage || data?.error || 'Jupiter route unavailable.'), {
      statusCode: response.status >= 500 ? 503 : 400,
    });
  }
  return data;
}

async function checkPreviewStatus(order, res) {
  if (order.signature && !['confirmed', 'failed'].includes(order.state)) {
    try {
      const result = await rpc('getSignatureStatuses', [[order.signature], { searchTransactionHistory: true }]);
      const status = result?.value?.[0];
      if (status?.err) order.state = 'failed';
      else if (['confirmed', 'finalized'].includes(status?.confirmationStatus)) order.state = 'confirmed';
    } catch (error) {
      // A status lookup failure is not a failed transaction and must not trigger a resubmission.
    }
  }
  return json(res, 200, {
    state: order.state,
    signature: order.signature || null,
    order_id: order.order_id,
    fee_back: 'Eligibility not activated; no distribution has been created.',
  });
}

async function getJson(url, ttl = 30000) {
  return (await getJsonWithMeta(url, ttl)).value;
}

function providerNameForUrl(url) {
  if (String(url).startsWith(DEX_API)) return 'DexScreener';
  if (String(url).startsWith(GECKO_API)) return 'GeckoTerminal';
  if (String(url).startsWith(PUMP_API)) return 'Pump.fun';
  return 'Public market provider';
}

function warnProviderThrottle(error, warningState, cooldownState) {
  if (error?.providerStatus === 429 && error?.provider) {
    if (warningState === null) return true;
    const warningKey = `${error.provider}:${error.providerStatus}`;
    if (warningState?.has(warningKey)) return true;
    warningState?.add(warningKey);
    if (cooldownState) {
      const now = Date.now();
      const cooldownUntil = cooldownState.get(warningKey) || 0;
      if (cooldownUntil > now) return true;
      cooldownState.set(warningKey, now + ASSET_THROTTLE_WARNING_COOLDOWN_MS);
    }
    console.warn(`[preview-api] ${error.provider} rate limited (HTTP 429).`);
    return true;
  }
  return false;
}

async function getJsonWithMeta(url, ttl = 30000) {
  const hit = cache.get(url);
  if (hit && Date.now() - hit.at < ttl) return { value: hit.value, fetchedAt: hit.fetchedAt, stale: false, error: null };
  if (pendingRequests.has(url)) return pendingRequests.get(url);
  const request = (async () => {
    try {
      const cooldownUntil = providerRateLimitCooldowns.get(url) || 0;
      if (cooldownUntil > Date.now()) {
        throw Object.assign(new Error(`${providerNameForUrl(url)} rate-limit cooldown is active.`), {
          providerStatus: 429,
          provider: providerNameForUrl(url),
          rateLimitCooldown: true,
        });
      }
      const headers = { Accept: 'application/json' };
      if (String(url).startsWith(GECKO_API) && GECKO_API_KEY) headers['x-cg-pro-api-key'] = GECKO_API_KEY;
      const response = await fetch(url, { headers, signal: AbortSignal.timeout(15000) });
      if (!response.ok) throw Object.assign(new Error(`Provider returned HTTP ${response.status}.`), {
        providerStatus: response.status,
        provider: providerNameForUrl(url),
        statusCode: response.status >= 500 ? 503 : response.status,
      });
      const value = await response.json();
      const fetchedAt = new Date().toISOString();
      cache.set(url, { at: Date.now(), fetchedAt, value });
      providerRateLimitCooldowns.delete(url);
      return { value, fetchedAt, stale: false, error: null };
    } catch (error) {
      if (error?.providerStatus === 429 && !error.rateLimitCooldown) {
        providerRateLimitCooldowns.set(url, Date.now() + PROVIDER_RATE_LIMIT_COOLDOWN_MS);
      }
      if (hit && Date.now() - hit.at <= MARKET_CACHE_RETENTION_MS) {
        return {
          value: hit.value,
          fetchedAt: hit.fetchedAt,
          stale: true,
          error: publicError(error),
          providerStatus: error?.providerStatus || null,
          provider: error?.provider || providerNameForUrl(url),
        };
      }
      throw error;
    }
  })();
  pendingRequests.set(url, request);
  try { return await request; }
  finally { pendingRequests.delete(url); }
}

const PROVIDER_COVERAGE = {
  'Pump.fun': {
    discovery: 'Pump.fun public coin index for Solana launchpad coverage',
    snapshot: 'Pump.fun coin metadata snapshots',
    candles: 'Not supplied; GeckoTerminal remains the candle provider',
    liquidity: 'Only reported when Pump.fun supplies a direct liquidity field',
    graduation: 'Pump.fun complete=true coin status',
    stream: 'Polling snapshot; no websocket or trade stream',
  },
  DexScreener: {
    discovery: 'Boosted token and pair discovery across supported chains',
    snapshot: 'DexScreener pair snapshots',
    candles: 'Not supplied by this adapter',
    liquidity: 'Pair liquidity snapshot',
    graduation: 'Not established by this provider',
    stream: 'Polling snapshot; no websocket or trade stream',
  },
  GeckoTerminal: {
    discovery: 'Public indexed pools across supported chains',
    snapshot: 'Pool price, volume, and reserve snapshots',
    candles: 'OHLCV pool candles',
    liquidity: 'Pool reserve snapshot',
    graduation: 'Not established by this provider',
    stream: 'Polling snapshot; no websocket or trade stream',
  },
};

const SCREENER_CONFIG = {
  quality: {
    label: 'Best observed setups',
    disclosure: 'Provider score from observed liquidity, volume, transaction activity, and price movement. Not a security audit or trade signal.',
  },
  momentum: {
    label: 'Momentum',
    disclosure: 'Provider score emphasizing reported price movement and activity. It does not predict future performance.',
  },
  volume: {
    label: 'Volume leaders',
    disclosure: 'Ranked by reported 24h volume, transaction activity, and liquidity. Rolling volume can change between snapshots.',
  },
  new: {
    label: 'Fresh with activity',
    disclosure: 'Recent provider-indexed pools with observed liquidity or activity. This does not establish launchpad provenance.',
  },
};

function normalizeScreener(value, kind = 'trending') {
  const requested = String(value || '').trim().toLowerCase();
  if (Object.prototype.hasOwnProperty.call(SCREENER_CONFIG, requested)) return requested;
  return kind === 'new' ? 'new' : 'quality';
}

function finiteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp(value, min = 0, max = 100) {
  return Math.min(max, Math.max(min, value));
}

function logarithmicScore(value, floor, ceiling) {
  if (!Number.isFinite(Number(value)) || Number(value) <= 0) return 0;
  const floorLog = Math.log10(Math.max(1, floor));
  const ceilingLog = Math.log10(Math.max(floor + 1, ceiling));
  return clamp(((Math.log10(Number(value)) - floorLog) / (ceilingLog - floorLog)) * 100);
}

function transactionStats(pair) {
  const txns = pair?.txns?.h24 || pair?.txns?.h6 || pair?.txns?.h1 || {};
  return {
    buys: finiteNumber(txns.buys),
    sells: finiteNumber(txns.sells),
  };
}

function scorePair(pair, screen, now = Date.now()) {
  const liquidity = finiteNumber(pair?.liquidity?.usd);
  const volume24 = finiteNumber(pair?.volume?.h24);
  const transactions = transactionStats(pair);
  const transactionCount = transactions.buys + transactions.sells;
  const h1 = finiteNumber(pair?.priceChange?.h1);
  const h6 = finiteNumber(pair?.priceChange?.h6);
  const h24 = finiteNumber(pair?.priceChange?.h24);
  const created = finiteNumber(pair?.pairCreatedAt, NaN);
  const ageHours = Number.isFinite(created) ? (now - created) / 3600000 : null;
  const liquidityScore = logarithmicScore(liquidity, 1000, 1000000);
  const volumeScore = logarithmicScore(volume24, 500, 1000000);
  const marketCapScore = logarithmicScore(finiteNumber(pair?.marketCap), 10000, 100000000);
  const activityScore = logarithmicScore(transactionCount, 4, 1200);
  const balanceScore = transactionCount > 0
    ? (Math.min(transactions.buys, transactions.sells) / Math.max(transactions.buys, transactions.sells)) * 100
    : 0;
  const movementScore = clamp(50 + (h1 * 2) + (h6 * 0.5) + (h24 * 0.15));
  const recencyScore = ageHours == null ? 35 : clamp(100 - ((Math.max(0, ageHours) / (14 * 24)) * 100));
  const scores = {
    quality: (liquidityScore * 0.38) + (volumeScore * 0.25) + (activityScore * 0.14) + (balanceScore * 0.08) + (movementScore * 0.05) + (marketCapScore * 0.1),
    momentum: (movementScore * 0.52) + (activityScore * 0.2) + (volumeScore * 0.16) + (liquidityScore * 0.12),
    volume: (volumeScore * 0.56) + (activityScore * 0.24) + (liquidityScore * 0.2),
    new: (recencyScore * 0.42) + (liquidityScore * 0.22) + (volumeScore * 0.18) + (activityScore * 0.13) + (movementScore * 0.05),
  };
  const score = Math.round(clamp(scores[screen] ?? scores.quality) * 10) / 10;
  const reasons = [];
  if (liquidity > 0) reasons.push(`${Math.round(liquidityScore)} liquidity`);
  if (volume24 > 0) reasons.push(`${Math.round(volumeScore)} volume`);
  if (transactionCount > 0) reasons.push(`${transactionCount} reported txns`);
  if (ageHours != null && ageHours >= 0 && ageHours <= 14 * 24) reasons.push(`${Math.max(0, Math.round(ageHours))}h old`);
  return {
    score,
    score_label: SCREENER_CONFIG[screen].label,
    score_reasons: reasons.slice(0, 3),
    liquidity_usd: liquidity || null,
    volume_24h_usd: volume24 || null,
    market_cap_usd: finiteNumber(pair?.marketCap) || null,
    transactions_24h: transactionCount || null,
    age_hours: ageHours != null && ageHours >= 0 ? Math.round(ageHours * 10) / 10 : null,
  };
}

function applyScreener(feed, kind, requestedScreen) {
  const screen = normalizeScreener(requestedScreen, kind);
  const scored = (feed.pairs || []).map(pair => {
    const score = scorePair(pair, screen);
    return {
      ...pair,
      signals: { ...(pair.signals || {}), screener: screen, screener_score: score.score, ...score },
    };
  });
  const recent = screen === 'new'
    ? scored.filter(pair => pair.signals.age_hours == null || pair.signals.age_hours <= 14 * 24)
    : scored;
  const preferred = screen === 'quality'
    ? recent.filter(pair => {
      const liquidity = finiteNumber(pair?.liquidity?.usd);
      const volume = finiteNumber(pair?.volume?.h24);
      const activity = finiteNumber(pair?.signals?.transactions_24h);
      return (!liquidity || liquidity >= 5000) && (!volume || volume >= 500 || activity >= 10);
    })
    : recent;
  const visible = preferred.length >= Math.min(5, scored.length) ? preferred : recent.length ? recent : scored;
  visible.sort((a, b) => b.signals.screener_score - a.signals.screener_score
    || finiteNumber(b.liquidity?.usd) - finiteNumber(a.liquidity?.usd)
    || finiteNumber(b.volume?.h24) - finiteNumber(a.volume?.h24)
    || finiteNumber(b.marketCap) - finiteNumber(a.marketCap));
  return {
    ...feed,
    label: `${feed.label.split(' · ')[0]} · ${SCREENER_CONFIG[screen].label}`,
    screener: screen,
    screener_label: SCREENER_CONFIG[screen].label,
    screener_disclosure: SCREENER_CONFIG[screen].disclosure,
    screening: {
      candidate_count: scored.length,
      visible_count: visible.length,
      ranking: 'Provider snapshot score only',
      filters: screen === 'new' ? 'Pool age ≤14 days when provider supplies creation time' : 'No security or profitability filter',
    },
    pairs: visible,
  };
}

const PROVIDER_LABELS = {
  'Pump.fun': 'Pump.fun public coin index',
  DexScreener: 'DexScreener boosted discovery',
  GeckoTerminal: 'GeckoTerminal public pool index',
};

function providerWarningFields(error, provider = error?.provider) {
  const status = Number(error?.providerStatus);
  if (!Number.isFinite(status) && !error) return {};
  return {
    provider_warning: {
      provider: provider || 'Public market provider',
      status: Number.isFinite(status) ? status : null,
      rate_limited: status === 429,
    },
    ...(Number.isFinite(status) ? { provider_status: status } : {}),
    ...(status === 429 ? { rate_limited: true } : {}),
  };
}
function providerMeta(provider, fetchedAt, { stale = false, error = null, primaryProvider = provider, providerStatus = null, ...extra } = {}) {
  return {
    provider,
    primary_provider: primaryProvider,
    sourceUrl: provider === 'Pump.fun' ? 'https://pump.fun' : provider === 'DexScreener' ? DEX_SITE : 'https://www.geckoterminal.com',
    sourceLabel: PROVIDER_LABELS[provider] || `${provider} public market data`,
    fetched_at: fetchedAt || new Date().toISOString(),
    stale: Boolean(stale),
    ...(error ? { error } : {}),
    ...providerWarningFields(providerStatus ? Object.assign(new Error(error || ''), { providerStatus, provider }) : null, provider),
    coverage: PROVIDER_COVERAGE[provider] || {},
    stream: false,
    ...extra,
  };
}

function pairFromGecko(item) {
  const attrs = item?.attributes || {};
  const relationships = item?.relationships || {};
  const baseId = relationships.base_token?.data?.id || '';
  const quoteId = relationships.quote_token?.data?.id || '';
  const baseAddress = baseId.split('_').slice(1).join('_') || null;
  const quoteAddress = quoteId.split('_').slice(1).join('_') || null;
  const name = attrs.name || 'Unknown / SOL';
  const [fallbackSymbol] = name.split(' / ');
  const network = item?.id?.split('_', 1)[0] || 'solana';
  const chainId = REVERSE_GECKO_NETWORKS[network] || network;
  return {
    chainId,
    network,
    pairAddress: attrs.address || item?.id?.split('_').slice(1).join('_'),
    dexId: relationships.dex?.data?.id || 'unknown',
    url: `${DEX_SITE}/${chainId}/${attrs.address || ''}`,
    baseToken: { address: baseAddress, name: fallbackSymbol || 'Unknown', symbol: fallbackSymbol || '?' },
    quoteToken: { address: quoteAddress, symbol: quoteId.includes('So111') ? 'SOL' : undefined },
    priceUsd: attrs.base_token_price_usd,
    priceChange: attrs.price_change_percentage || {},
    liquidity: { usd: attrs.reserve_in_usd },
    volume: attrs.volume_usd || {},
    marketCap: attrs.market_cap_usd,
    fdv: attrs.fdv_usd,
    txns: attrs.transactions || {},
    pairCreatedAt: attrs.pool_created_at ? Date.parse(attrs.pool_created_at) : null,
    info: { imageUrl: attrs.image_url || null, websites: [], socials: [] },
  };
}

function hasProviderImage(pair) {
  const candidates = [
    pair?.info?.imageUrl,
    pair?.info?.image,
    pair?.imageUrl,
    pair?.image,
    pair?.logoUrl,
    pair?.logoURI,
    pair?.baseToken?.imageUrl,
    pair?.baseToken?.image,
    pair?.baseToken?.logoURI,
    pair?.baseToken?.logoUrl,
    pair?.baseToken?.logo,
  ];
  return candidates.some(value => typeof value === 'string' && /^(https?:\/\/|data:image\/)/i.test(value));
}

function requireImagesForNewFeed(feed, kind) {
  if (kind !== 'new') return feed;
  const pairs = Array.isArray(feed.pairs) ? feed.pairs : [];
  const imagePairs = pairs.filter(hasProviderImage);
  return {
    ...feed,
    pairs: imagePairs,
    image_required: true,
    image_filtered_count: pairs.length - imagePairs.length,
  };
}

function geckoResult(data, kind) {
  const pairs = (data?.data || []).map(pairFromGecko).filter(pair => pair.pairAddress);
  return {
    provider: 'GeckoTerminal',
    sourceUrl: 'https://www.geckoterminal.com',
    sourceLabel: 'GeckoTerminal public pool index',
    fetched_at: new Date().toISOString(),
    stale: false,
    label: kind === 'new' ? 'New pools' : 'Trending pools',
    pairs,
    page: 1,
  };
}

function pairFromPumpCoin(coin, kind) {
  if (!coin || typeof coin !== 'object') return null;
  const mint = coin.mint || coin.address;
  if (typeof mint !== 'string' || !/^[a-zA-Z0-9]+$/.test(mint)) return null;
  const createdValue = Number(coin.created_timestamp ?? coin.createdAt ?? coin.created_at);
  const created = Number.isFinite(createdValue) ? (createdValue < 1e12 ? createdValue * 1000 : createdValue) : null;
  const priceChange = { ...(coin.priceChange || coin.price_change || {}) };
  if (!Object.keys(priceChange).length) {
    [['price_change_5m', 'm5'], ['price_change_1h', 'h1'], ['price_change_24h', 'h24']].forEach(([source, target]) => {
      if (coin[source] != null) priceChange[target] = coin[source];
    });
  }
  const volume = { ...(coin.volume || coin.volume_usd || {}) };
  if (!Object.keys(volume).length && coin.volume_24h != null) volume.h24 = coin.volume_24h;
  const liquidity = { ...(coin.liquidity || {}) };
  if (!Object.keys(liquidity).length && coin.liquidity_usd != null) liquidity.usd = coin.liquidity_usd;
  const pair = {
    chainId: 'solana',
    network: 'solana',
    pairAddress: coin.raydium_pool || coin.pool_address || mint,
    dexId: 'pump.fun',
    url: `https://pump.fun/coin/${encodeURIComponent(mint)}`,
    baseToken: { address: mint, name: coin.name || 'Unknown', symbol: coin.symbol || '?' },
    quoteToken: { symbol: 'SOL' },
    priceUsd: coin.price_usd ?? coin.usd_price ?? null,
    priceChange,
    liquidity,
    volume,
    marketCap: coin.usd_market_cap ?? coin.market_cap_usd ?? null,
    fdv: coin.fdv_usd ?? coin.fdv ?? null,
    txns: coin.transactions && typeof coin.transactions === 'object' ? coin.transactions : {},
    pairCreatedAt: created,
    info: {
      imageUrl: coin.image_uri || coin.image_url || null,
      websites: coin.website ? [coin.website] : [],
      socials: [
        coin.twitter ? { type: 'twitter', url: coin.twitter } : null,
        coin.telegram ? { type: 'telegram', url: coin.telegram } : null,
      ].filter(Boolean),
    },
    marketKind: 'launchpad-token',
    marketStage: kind,
    launchpadId: 'pump',
  };
  if (coin.complete === true) {
    pair.graduation = {
      status: 'graduated',
      pool_address: coin.raydium_pool || coin.pool_address || null,
      source: 'Pump.fun',
    };
  }
  return pair;
}

async function pumpFeed(kind, page = 1) {
  if (String(page) !== '1') throw new Error('Pump.fun discovery is available on the first page only.');
  const query = new URLSearchParams({
    offset: '0',
    limit: '50',
    sort: kind === 'new' ? 'created_timestamp' : 'market_cap',
    order: 'DESC',
    includeNsfw: 'false',
  });
  const result = await getJsonWithMeta(`${PUMP_API}/coins?${query.toString()}`, 20000);
  const coins = Array.isArray(result.value) ? result.value : result.value?.coins || result.value?.data || [];
  const pairs = coins.map(coin => pairFromPumpCoin(coin, kind)).filter(Boolean);
  if (!pairs.length) throw new Error('Pump.fun returned no indexed coins.');
  pairs.sort((a, b) => kind === 'new'
    ? Number(b.pairCreatedAt || 0) - Number(a.pairCreatedAt || 0)
    : Number(b.marketCap || 0) - Number(a.marketCap || 0));
  return {
    ...providerMeta('Pump.fun', result.fetchedAt, {
      stale: result.stale,
      error: result.error,
      providerStatus: result.providerStatus,
    }),
    sourceLabel: 'Pump.fun public coin index · launchpad coverage',
    label: kind === 'new' ? 'Recent Pump.fun coins' : 'Pump.fun market-cap snapshot',
    pairs,
    page: 1,
  };
}

async function geckoAsset(mint, warningState, cooldownState) {
  const tokenUrl = `${GECKO_API}/networks/solana/tokens/${encodeURIComponent(mint)}`;
  const poolsUrl = `${GECKO_API}/networks/solana/tokens/${encodeURIComponent(mint)}/pools?page=1`;
  let token = null;
  let pools = null;
  let error = null;
  try { token = (await getJson(tokenUrl, 60000))?.data || null; } catch (failure) { error = error || failure; warnProviderThrottle(failure, warningState, cooldownState); }
  try { pools = (await getJson(poolsUrl, 60000))?.data || []; } catch (failure) { error = error || failure; warnProviderThrottle(failure, warningState, cooldownState); }

  const tokenAttrs = token?.attributes || {};
  const pool = (Array.isArray(pools) ? pools : [])
    .filter(item => {
      const address = item?.relationships?.base_token?.data?.id?.split('_').slice(1).join('_');
      return address === mint;
    })
    .sort((a, b) => Number(b?.attributes?.reserve_in_usd || 0) - Number(a?.attributes?.reserve_in_usd || 0))[0];
  if (!pool) {
    const poolId = token?.relationships?.top_pools?.data?.[0]?.id || '';
    const poolAddress = poolId.split('_').slice(1).join('_');
    if (!poolAddress || !tokenAttrs.price_usd) return { pair: null, imageUrl: tokenAttrs.image_url || null, error };
    return {
      pair: {
        chainId: 'solana',
        network: 'solana',
        pairAddress: poolAddress,
        dexId: 'unknown',
        url: `${DEX_SITE}/solana/${poolAddress}`,
        baseToken: { address: mint, name: tokenAttrs.name || 'Unknown', symbol: tokenAttrs.symbol || '?' },
        quoteToken: { symbol: 'SOL' },
        priceUsd: tokenAttrs.price_usd,
        priceChange: {},
        liquidity: { usd: tokenAttrs.total_reserve_in_usd },
        volume: tokenAttrs.volume_usd || {},
        marketCap: tokenAttrs.market_cap_usd,
        fdv: tokenAttrs.fdv_usd,
        pairCreatedAt: null,
        info: { imageUrl: tokenAttrs.image_url || null, websites: [], socials: [] },
      },
      imageUrl: tokenAttrs.image_url || null,
      error,
    };
  }

  const pair = pairFromGecko(pool);
  pair.baseToken = {
    ...pair.baseToken,
    address: mint,
    name: tokenAttrs.name || pair.baseToken.name,
    symbol: tokenAttrs.symbol || pair.baseToken.symbol,
  };
  pair.info = { ...pair.info, imageUrl: pair.info?.imageUrl || tokenAttrs.image_url || null };
  return { pair, imageUrl: pair.info.imageUrl, error };
}

async function geckoFeed(kind, page = 1, chain = 'solana') {
  const endpoint = kind === 'new' ? 'new_pools' : 'trending_pools';
  const chains = chain === 'all' ? SUPPORTED_MARKET_CHAINS : [chain];
  if (chains.some(value => !GECKO_NETWORKS[value])) throw Object.assign(new Error('Unsupported market chain.'), { statusCode: 400 });
  const requestedPage = Math.max(1, Math.floor(Number(page) || 1));
  const pageBudget = kind === 'new' && chain === 'all' ? GECKO_NEW_ALL_PAGE_BUDGET : 1;
  const firstProviderPage = ((requestedPage - 1) * pageBudget) + 1;
  const pages = pageBudget > 1
    ? Array.from({ length: pageBudget }, (_, index) => firstProviderPage + index)
    : [requestedPage];
  const fulfilled = [];
  const rejected = [];
  const requestedPages = [];
  for (const providerPage of pages) {
    const requests = chains.map(value => ({
      chain: value,
      page: providerPage,
      promise: getJsonWithMeta(
        `${GECKO_API}/networks/${GECKO_NETWORKS[value]}/${endpoint}?page=${providerPage}`,
        30000,
      ),
    }));
    requestedPages.push(providerPage);
    const settled = await Promise.allSettled(requests.map(request => request.promise));
    fulfilled.push(...settled.flatMap((result, index) => result.status === 'fulfilled'
      ? [{ ...requests[index], response: result.value }]
      : []));
    rejected.push(...settled.flatMap((result, index) => result.status === 'rejected'
      ? [{ ...requests[index], error: result.reason }]
      : []));
    const pageHadNoSuccessfulNetworks = settled.length > 0
      && settled.every(result => result.status === 'rejected');
    if (pageHadNoSuccessfulNetworks) break;
  }
  if (!fulfilled.length) throw rejected[0]?.error || new Error('GeckoTerminal returned no indexed pools.');
  const pairs = fulfilled.flatMap(({ response }) => geckoResult(response.value, kind).pairs);
  if (!pairs.length) throw new Error('GeckoTerminal returned no indexed pools.');
  const responses = fulfilled.map(item => item.response);
  const fetchedAt = responses.map(response => response.fetchedAt).filter(Boolean).sort().at(-1);
  const pagesReceived = [...new Set(fulfilled.map(item => item.page))].sort((a, b) => a - b);
  const partial = rejected.length > 0 || requestedPages.length < pages.length;
  return {
    ...providerMeta('GeckoTerminal', fetchedAt, {
      stale: responses.some(response => response.stale),
      error: responses.find(response => response.error)?.error
        || (rejected.length ? `Partial provider response: ${publicError(rejected[0].error)}` : null),
      providerStatus: responses.find(response => response.providerStatus)?.providerStatus
        || rejected.find(request => request.error?.providerStatus)?.error?.providerStatus,
    }),
    label: kind === 'new' ? 'New pools · image verified' : 'Trending pools',
    pairs,
    page: requestedPage,
    provider_pagination: {
      provider: 'GeckoTerminal',
      requested_page: requestedPage,
      pages_requested: requestedPages,
      pages_received: pagesReceived,
      page_budget: pages.length,
      partial,
      can_request_next_page: kind === 'new'
        && chain === 'all'
        && pairs.length > 0
        && !rejected.some(request => request.error?.providerStatus === 429),
      failed_requests: rejected.map(request => ({
        chain: request.chain,
        page: request.page,
        provider_status: request.error?.providerStatus || null,
      })),
      completeness: 'Bounded provider snapshot; additional provider pages may exist.',
    },
  };
}

async function pumpGraduations(mints = '') {
  const uniqueMints = [...new Set(String(mints).split(',')
    .map(value => value.trim())
    .filter(value => /^[a-zA-Z0-9]{1,64}$/.test(value)))];
  const fetchedAt = new Date().toISOString();
  if (!uniqueMints.length) {
    return {
      ...providerMeta('Pump.fun', fetchedAt),
      sourceLabel: 'Pump.fun public coin status · complete=true',
      status: 'no_verified_events',
      graduations: [],
    };
  }
  const results = [];
  let nextMint = 0;
  const readMint = async () => {
    while (nextMint < uniqueMints.length) {
      const mint = uniqueMints[nextMint];
      nextMint += 1;
      try {
        const result = await getJsonWithMeta(`${PUMP_API}/coins/${encodeURIComponent(mint)}`, 60000);
        results.push({ mint, data: result.value, meta: result });
      } catch (error) {
        warnProviderThrottle(error);
        results.push({ mint, error: publicError(error), providerStatus: error?.providerStatus || null });
      }
    }
  };
  await Promise.all([...Array(Math.min(2, uniqueMints.length))].map(() => readMint()));
  const graduations = results
    .filter(result => result.data?.complete === true)
    .map(result => ({
      mint: result.mint,
      status: 'graduated',
      pool_address: result.data.raydium_pool || result.data.pool_address || null,
      graduated_at: result.data.graduation_timestamp || result.data.completion_timestamp || null,
      observed_at: fetchedAt,
      source: 'Pump.fun',
      source_url: 'https://pump.fun',
    }));
  const errors = [...new Set(results.filter(result => result.error).map(result => result.error))];
  const observedAt = results.map(result => result.meta?.fetchedAt).filter(Boolean).sort().at(-1) || fetchedAt;
  return {
    ...providerMeta('Pump.fun', observedAt, {
      stale: results.some(result => result.meta?.stale),
      providerStatus: results.find(result => result.providerStatus || result.meta?.providerStatus)?.providerStatus
        || results.find(result => result.meta?.providerStatus)?.meta?.providerStatus,
    }),
    sourceLabel: 'Pump.fun public coin status · complete=true',
    error: errors.length ? errors.join('; ') : null,
    status: graduations.length ? 'verified' : errors.length === results.length ? 'unavailable' : 'no_verified_events',
    graduations,
  };
}
async function geckoCandles(chain, address, interval = '1h') {
  const networks = {
    solana: 'solana',
    ethereum: 'eth',
    base: 'base',
    bsc: 'bsc',
    arbitrum: 'arbitrum',
    avalanche: 'avax',
    polygon: 'polygon_pos',
    sui: 'sui',
  };
  const intervals = {
    '5m': ['minute', 5],
    '15m': ['minute', 15],
    '1h': ['hour', 1],
    '4h': ['hour', 4],
    '1d': ['day', 1],
  };
  if (!networks[chain] || !intervals[interval]) {
    throw Object.assign(new Error('Invalid chart interval or network.'), { statusCode: 400 });
  }
  const [timeframe, aggregate] = intervals[interval];
  const result = await getJsonWithMeta(
    `${GECKO_API}/networks/${networks[chain]}/pools/${encodeURIComponent(address)}/ohlcv/${timeframe}?aggregate=${aggregate}&limit=100&currency=usd&token=base`,
    90000,
  );
  const rows = result.value?.data?.attributes?.ohlcv_list || [];
  const candles = [...new Map(rows
    .filter(row => Array.isArray(row) && row.length >= 6 && Number.isFinite(row[0]))
    .map(row => [row[0], row])).values()]
    .sort((a, b) => a[0] - b[0]);
  return {
    ...providerMeta('GeckoTerminal', result.fetchedAt, {
      stale: result.stale,
      error: result.error,
      providerStatus: result.providerStatus,
    }),
    candles,
  };
}

async function dexBoostFeed(kind, page = 1, chain = 'solana') {
  if (String(page) !== '1') throw new Error('Fast discovery is available on the first page only.');
  const indexResult = await getJsonWithMeta(`${DEX_API}/token-boosts/${kind === 'new' ? 'latest' : 'top'}/v1`, 20000);
  const index = indexResult.value;
  const supportedChains = new Set(SUPPORTED_MARKET_CHAINS);
  const candidates = (Array.isArray(index) ? index : [])
    .filter(item => (
      (chain === 'all' ? supportedChains.has(item?.chainId) : item?.chainId === chain)
      && item?.tokenAddress
    ));
  const addresses = [...new Set(candidates.map(item => item.tokenAddress))].slice(0, 30);
  if (!addresses.length) throw new Error('Fast discovery returned no indexed tokens.');
  const payloadResult = await getJsonWithMeta(`${DEX_API}/latest/dex/tokens/${addresses.join(',')}`, 20000);
  const payload = payloadResult.value;
  const rank = new Map(candidates.map((item, index) => [`${item.chainId}:${item.tokenAddress}`, index]));
  const bestByToken = new Map();
  for (const pair of payload?.pairs || []) {
    if (chain === 'all' ? !supportedChains.has(pair?.chainId) : pair?.chainId !== chain) continue;
    const key = `${pair.chainId}:${pair.baseToken?.address}`;
    const liquidity = Number(pair.liquidity?.usd || 0);
    if (!bestByToken.has(key) || liquidity > Number(bestByToken.get(key).liquidity?.usd || 0)) bestByToken.set(key, pair);
  }
  const pairs = [...bestByToken.values()];
  pairs.sort((a, b) => (rank.get(`${a.chainId}:${a.baseToken?.address}`) ?? candidates.length)
    - (rank.get(`${b.chainId}:${b.baseToken?.address}`) ?? candidates.length)
    || Number(b.liquidity?.usd || 0) - Number(a.liquidity?.usd || 0));
  if (!pairs.length) throw new Error('Fast discovery returned no indexed pools.');
  return {
    ...providerMeta('DexScreener', payloadResult.fetchedAt || indexResult.fetchedAt, {
      stale: indexResult.stale || payloadResult.stale,
      error: indexResult.error || payloadResult.error,
      providerStatus: indexResult.providerStatus || payloadResult.providerStatus,
    }),
    label: kind === 'new' ? 'Recent indexed pools · image verified' : 'Boosted discovery',
    pairs,
    page: Number(page),
    provider_pagination: {
      provider: 'DexScreener',
      requested_page: Number(page),
      pages_requested: [1],
      pages_received: [1],
      page_budget: 1,
      partial: false,
      can_request_next_page: false,
      failed_requests: [],
      completeness: 'Bounded provider snapshot; additional provider pages may exist.',
    },
  };
}

function unavailableFeed(kind, chain, error, primaryProvider = 'DexScreener') {
  return {
    provider: 'Public providers',
    primary_provider: primaryProvider,
    ...providerWarningFields(error, error?.provider || primaryProvider),
    sourceUrl: 'https://www.geckoterminal.com',
    sourceLabel: 'Provider status',
    fetched_at: new Date().toISOString(),
    stale: true,
    error: `Public market providers are temporarily unavailable${error?.providerStatus ? ` (HTTP ${error.providerStatus})` : ''}. Retrying on the next refresh.`,
    label: kind === 'new' ? 'New pools · provider unavailable' : 'Trending pools · provider unavailable',
    pairs: [],
    page: 1,
    chain,
    coverage: {
      discovery: 'No provider response available',
      snapshot: 'Unavailable',
      candles: 'Not evaluated',
      liquidity: 'Unavailable',
      graduation: 'Not established',
      stream: 'No stream',
    },
    stream: false,
  };
}

async function dexSearch(query) {
  const data = await getJson(`${DEX_API}/latest/dex/search?q=${encodeURIComponent(query)}`, 15000);
  return {
    provider: 'DexScreener',
    sourceUrl: 'https://dexscreener.com',
    sourceLabel: 'DexScreener search index',
    fetched_at: new Date().toISOString(),
    stale: false,
    label: 'Search results',
    pairs: data?.pairs || [],
    page: 1,
  };
}

async function geckoPair(chain, address) {
  const networks = {
    solana: 'solana',
    ethereum: 'eth',
    base: 'base',
    bsc: 'bsc',
    arbitrum: 'arbitrum',
    avalanche: 'avax',
    polygon: 'polygon_pos',
    sui: 'sui',
  };
  const network = networks[chain];
  if (!network) throw new Error('Unsupported market network.');
  const data = await getJson(`${GECKO_API}/networks/${network}/pools/${encodeURIComponent(address)}?include=base_token,quote_token,dex`, 30000);
  const pair = pairFromGecko(data?.data);
  return pair?.pairAddress ? pair : null;
}

async function requestBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString() || '{}');
}

function whitepaper() {
  return {
    version: '1.0',
    contracts: [
      { name: 'FEE', mint: MINTS.fee },
      { name: 'FEECAT', mint: MINTS.feecat },
      { name: 'RFEE', mint: MINTS.rfee },
    ],
    chapters: Array.from({ length: 25 }, (_, index) => ({
      id: `chapter-${index + 1}`,
      number: index + 1,
      title: ['The premise', 'The connected foundation', 'Market data', 'Provider boundaries', 'FEELESS identity', 'FEECAT culture', 'Fee-Back model', 'Eligibility', 'Distribution', 'Trading safety', 'Wallet custody', 'Solana execution', 'Discovery', 'The Trenches', 'Community rules', 'Launch providers', 'Liquidity', 'Risk disclosure', 'Security posture', 'Data lineage', 'Unsupported signals', 'Roadmap', 'Public launch target', 'Governance', 'Closing note'][index],
      text: 'FEELESS connects provider-backed discovery, wallet-controlled execution, and community context. Provider observations are not security endorsements, and planned features are not activated distributions.',
    })),
  };
}

function minimalPdf() {
  const body = 'BT /F1 14 Tf 72 740 Td (FEELESS Whitepaper) Tj 0 -24 Td /F1 10 Tf (Provider-backed discovery, wallet-controlled execution, and community context.) Tj ET';
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
    `<< /Length ${body.length} >>\\nstream\\n${body}\\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ];
  let pdf = '%PDF-1.4\\n';
  const offsets = [0];
  objects.forEach((object, index) => { offsets[index + 1] = Buffer.byteLength(pdf); pdf += `${index + 1} 0 obj\\n${object}\\nendobj\\n`; });
  const start = Buffer.byteLength(pdf);
  pdf += `xref\\n0 ${objects.length + 1}\\n0000000000 65535 f \\n`;
  offsets.slice(1).forEach(offset => { pdf += `${String(offset).padStart(10, '0')} 00000 n \\n`; });
  pdf += `trailer\\n<< /Size ${objects.length + 1} /Root 1 0 R >>\\nstartxref\\n${start}\\n%%EOF`;
  return Buffer.from(pdf);
}

async function assets() {
  const warningState = new Set();
  const result = await Promise.all(Object.entries(MINTS).map(async ([id, mint]) => {
    let primaryError = null;
    let fallbackError = null;
    try {
      let rows = [];
      try {
        const response = await getJsonWithMeta(`${DEX_API}/token-pairs/v1/solana/${mint}`, 60000);
        rows = response.value;
        if (response.error) {
          primaryError = Object.assign(new Error(response.error), {
            providerStatus: response.providerStatus,
            provider: response.provider || 'DexScreener',
          });
        }
      } catch (error) {
        primaryError = error;
      }
      let pair = (Array.isArray(rows) ? rows : [])
        .filter(item => item?.baseToken?.address === mint)
        .sort((a, b) => Number(b?.liquidity?.usd || 0) - Number(a?.liquidity?.usd || 0))[0] || null;
      let imageUrl = pair?.info?.imageUrl || null;
      let provider = 'DexScreener';
      if (!pair || !imageUrl) {
        const fallback = await geckoAsset(mint, primaryError ? null : warningState, assetThrottleWarningCooldown);
        fallbackError = fallback.error;
        pair = pair || fallback.pair;
        imageUrl = imageUrl || fallback.imageUrl;
        if (fallback.pair) provider = 'GeckoTerminal';
        if (pair && imageUrl) pair.info = { ...(pair.info || {}), imageUrl };
      }
      if (primaryError) warnProviderThrottle(primaryError, warningState, assetThrottleWarningCooldown);
      return {
        id,
        label: id.toUpperCase(),
        mint,
        chain: 'solana',
        pair,
        imageUrl,
        status: pair?.priceUsd ? 'market_observed' : primaryError ? 'provider_unavailable' : 'awaiting_market',
        provider,
        fetched_at: new Date().toISOString(),
        ...(primaryError ? {
          fallback_from: 'DexScreener',
          fallback_reason: pair
            ? `DexScreener unavailable; using ${provider} fallback (${publicError(primaryError)}).`
            : `DexScreener unavailable; no fallback market data is available (${publicError(primaryError)}).`,
          ...(!pair ? { error: publicError(primaryError) } : {}),
          ...providerWarningFields(primaryError, 'DexScreener'),
        } : {}),
        ...(!primaryError && fallbackError ? providerWarningFields(fallbackError, 'GeckoTerminal') : {}),
        identity: 'Owner-supplied contract; exact provider match. Not a security endorsement.',
      };
    } catch (error) {
      const reportedError = primaryError || error;
      warnProviderThrottle(reportedError, warningState, assetThrottleWarningCooldown);
      return {
        id,
        label: id.toUpperCase(),
        mint,
        chain: 'solana',
        pair: null,
        status: 'provider_unavailable',
        error: publicError(reportedError),
        provider: 'DexScreener',
        fetched_at: new Date().toISOString(),
        ...providerWarningFields(reportedError, reportedError?.provider || 'DexScreener'),
        identity: 'Owner-supplied contract; exact provider match. Not a security endorsement.',
      };
    }
  }));
  return { assets: result };
}

function roomMessages(room) {
  if (!rooms.has(room)) rooms.set(room, []);
  return rooms.get(room);
}

function identityKey(chain, address) {
  return `${chain}:${chain === 'evm' ? String(address).toLowerCase() : String(address)}`;
}

function normalizeChain(value) {
  return value === 'solana' || value === 'evm' ? value : null;
}

function normalizeAddress(chain, value) {
  const address = String(value || '').trim();
  if (chain === 'solana') {
    try { return new PublicKey(address).toString(); } catch { return null; }
  }
  return /^0x[a-fA-F0-9]{40}$/.test(address) ? address.toLowerCase() : null;
}

function base64Signature(value) {
  if (Array.isArray(value)) return Buffer.from(value);
  const text = String(value || '').trim();
  if (!text) return null;
  if (/^0x[0-9a-fA-F]+$/.test(text)) return Buffer.from(text.slice(2), 'hex');
  try { return Buffer.from(text, 'base64'); } catch { return null; }
}

function verifySignature(chain, address, message, signature) {
  const bytes = base64Signature(signature);
  if (!bytes?.length) return false;
  if (chain === 'solana') {
    if (bytes.length !== 64) return false;
    try {
      const publicKey = new PublicKey(address);
      const derPrefix = Buffer.from('302a300506032b6570032100', 'hex');
      return nodeCrypto.verify(null, Buffer.from(message), { key: Buffer.concat([derPrefix, Buffer.from(publicKey.toBytes())]), format: 'der', type: 'spki' }, bytes);
    } catch { return false; }
  }
  if (bytes.length !== 65) return false;
  try {
    let recovery = bytes[64];
    if (recovery >= 27) recovery -= 27;
    if (recovery > 1) return false;
    const prefix = Buffer.from(`\x19Ethereum Signed Message:\n${Buffer.byteLength(message)}`);
    const digest = Buffer.from(keccak_256(Buffer.concat([prefix, Buffer.from(message)])));
    const publicKey = secp256k1.Signature.fromCompact(bytes.subarray(0, 64)).addRecoveryBit(recovery).recoverPublicKey(digest).toRawBytes(false);
    const recovered = `0x${Buffer.from(keccak_256(publicKey.subarray(1))).subarray(-20).toString('hex')}`;
    return recovered.toLowerCase() === address.toLowerCase();
  } catch { return false; }
}

function profileRecord(chain, address) {
  const key = identityKey(chain, address);
  if (!profiles.has(key)) profiles.set(key, {
    chain,
    address,
    displayName: '',
    username: '',
    bio: '',
    category: 'Trader',
    avatarUrl: '',
    backgroundUrl: '',
    xUrl: '',
    websiteUrl: '',
    isPrivate: false,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  });
  return profiles.get(key);
}

function flagCount(chain, address) {
  return profileFlags.get(identityKey(chain, address))?.size || 0;
}

function profileView(profile, viewerKey = '') {
  const own = viewerKey && identityKey(profile.chain, profile.address) === viewerKey;
  if (profile.isPrivate && !own) return {
    chain: profile.chain,
    address: profile.address,
    isPrivate: true,
    flagCount: null,
    hidden: true,
  };
  return {
    ...profile,
    flagCount: flagCount(profile.chain, profile.address),
    hidden: false,
  };
}

function profileFromBody(body) {
  const chain = normalizeChain(body.chain);
  const address = normalizeAddress(chain, body.address);
  if (!chain || !address) return null;
  return { chain, address, key: identityKey(chain, address) };
}

function proofFromBody(body) {
  const identity = profileFromBody(body);
  if (!identity || !body.message || !body.signature) return null;
  const verified = verifiedWallets.get(identity.key);
  if (verified && verified.message === body.message && verified.signature === body.signature && verified.expiresAt > Date.now()) return identity;
  if (!verifySignature(identity.chain, identity.address, String(body.message), body.signature)) return null;
  const challenge = profileChallenges.get(identity.key);
  if (!challenge || challenge.message !== String(body.message) || challenge.expiresAt <= Date.now()) return null;
  verifiedWallets.set(identity.key, { message: challenge.message, signature: body.signature, expiresAt: Date.now() + PROFILE_CHALLENGE_MS });
  return identity;
}

function publicProfileForMessage(message, viewerKey = '') {
  const profile = profileRecord(message.chain || 'solana', message.address || message.wallet || '11111111111111111111111111111111');
  const view = profileView(profile, viewerKey);
  return { ...message, profile: view, likeCount: messageLikes.get(message.id)?.size || 0, likedByMe: Boolean(viewerKey && messageLikes.get(message.id)?.has(viewerKey)) };
}

function chatLimitKey(room, identity) {
  return `${room}:${identity.key}`;
}

function checkChatLimit(room, identity) {
  const key = chatLimitKey(room, identity);
  const state = chatLimits.get(key);
  if (!state) return null;
  if (state.cooldownUntil > Date.now()) return Math.ceil((state.cooldownUntil - Date.now()) / 1000);
  if (state.cooldownUntil) chatLimits.delete(key);
  return null;
}

function recordChatComment(room, identity) {
  const key = chatLimitKey(room, identity);
  const state = chatLimits.get(key) || { count: 0, cooldownUntil: 0 };
  state.count += 1;
  if (state.count >= 3) {
    state.cooldownUntil = Date.now() + PROFILE_COOLDOWN_MS;
    state.count = 0;
  }
  chatLimits.set(key, state);
}

async function route(req, res, url) {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS' });
    return res.end();
  }
  if (req.method === 'GET' && url.pathname === '/api/') return json(res, 200, { message: 'FEELESS API', mode: 'preview', market: 'live public providers' });
  if (req.method === 'GET' && url.pathname === '/api/market/assets') return json(res, 200, await assets());
  if (req.method === 'GET' && url.pathname === '/api/market/feed') {
    const kind = url.searchParams.get('kind') === 'new' ? 'new' : 'trending';
    const chain = url.searchParams.get('chain') || 'solana';
    const scope = url.searchParams.get('scope') || '';
    const screen = normalizeScreener(url.searchParams.get('screen'), kind);
    if (chain !== 'all' && !GECKO_NETWORKS[chain]) return json(res, 400, { detail: 'Unsupported market chain.' });
    let result;
    const broadNewFeed = kind === 'new' && scope !== 'pump';
    const primaryProvider = scope === 'pump' ? 'Pump.fun' : broadNewFeed ? 'GeckoTerminal' : 'DexScreener';
    try {
      if (scope === 'pump' && chain === 'solana') {
        result = await pumpFeed(kind, url.searchParams.get('page') || 1);
      } else if (broadNewFeed) {
        result = await geckoFeed(kind, url.searchParams.get('page') || 1, chain);
      } else {
        result = await dexBoostFeed(kind, url.searchParams.get('page') || 1, chain);
        if (scope === 'pump') {
          result.primary_provider = primaryProvider;
          result.fallback_from = primaryProvider;
          result.fallback_reason = 'Pump.fun coverage is limited to Solana; using public pool discovery fallback.';
        }
      }
    } catch (primaryError) {
      warnProviderThrottle(primaryError);
      try {
        result = broadNewFeed
          ? await dexBoostFeed(kind, url.searchParams.get('page') || 1, chain)
          : await geckoFeed(kind, url.searchParams.get('page') || 1, chain);
        if (scope === 'pump') {
          result.primary_provider = primaryProvider;
          result.fallback_from = primaryProvider;
          result.fallback_reason = `Pump.fun unavailable; using GeckoTerminal fallback (${publicError(primaryError)}).`;
        } else if (broadNewFeed) {
          result.primary_provider = primaryProvider;
          result.fallback_from = primaryProvider;
          result.fallback_reason = `GeckoTerminal unavailable; using DexScreener fallback (${publicError(primaryError)}).`;
        }
        Object.assign(result, providerWarningFields(primaryError, primaryProvider));
      } catch (geckoError) {
        warnProviderThrottle(geckoError);
        result = unavailableFeed(kind, chain, geckoError || primaryError, primaryProvider);
      }
    }
    return json(res, 200, applyScreener(requireImagesForNewFeed(result, kind), kind, screen));
  }
  if (req.method === 'GET' && url.pathname === '/api/market/graduations') {
    return json(res, 200, await pumpGraduations(url.searchParams.get('mints') || ''));
  }
  const candleMatch = url.pathname.match(/^\/api\/market\/candles\/([^/]+)\/([^/]+)$/);
  if (req.method === 'GET' && candleMatch) {
    const result = await geckoCandles(candleMatch[1], candleMatch[2], url.searchParams.get('interval') || '1h');
    return json(res, 200, result);
  }
  if (req.method === 'GET' && url.pathname === '/api/market/search') return json(res, 200, await dexSearch(url.searchParams.get('q') || ''));
  const pairMatch = url.pathname.match(/^\/api\/market\/pair\/([^/]+)\/([^/]+)$/);
  if (req.method === 'GET' && pairMatch) {
    const [, chain, address] = pairMatch;
    let primaryError = null;
    try {
      const data = await getJson(`${DEX_API}/latest/dex/pairs/${encodeURIComponent(chain)}/${encodeURIComponent(address)}`, 30000);
      const pairs = data?.pairs || [];
      if (pairs.length) return json(res, 200, { provider: 'DexScreener', fetched_at: new Date().toISOString(), stale: false, pairs, label: 'Pair snapshot' });
    } catch (error) {
      primaryError = error;
      warnProviderThrottle(error);
    }
    const pair = await geckoPair(chain, address);
    return json(res, 200, {
      provider: 'GeckoTerminal',
      fetched_at: new Date().toISOString(),
      stale: false,
      pairs: pair ? [pair] : [],
      label: 'Pair snapshot',
      ...(primaryError ? {
        fallback_from: 'DexScreener',
        fallback_reason: `DexScreener unavailable; using GeckoTerminal fallback (${publicError(primaryError)}).`,
        ...providerWarningFields(primaryError, 'DexScreener'),
      } : {}),
    });
  }
  if (req.method === 'GET' && url.pathname === '/api/market/scan') {
    const query = url.searchParams.get('address') || '';
    const result = await dexSearch(query);
    return json(res, 200, { ...result, label: 'Exact contract matches', pairs: result.pairs.filter(pair => pair?.baseToken?.address === query) });
  }
  if (req.method === 'GET' && url.pathname === '/api/intelligence/community') {
    return json(res, 200, { context: url.searchParams.get('context') || 'solana', window: '7 days', messages: 0, rankings: [], disclosure: 'Public, unauthenticated handles ranked by actual messages. Not verified identities.' });
  }
  if (req.method === 'GET' && url.pathname === '/api/intelligence/tape') return json(res, 200, { events: [], unsupported: ['individual whale trades', 'pool migration', 'all-time highs', 'holder concentration'] });
  if (req.method === 'GET' && url.pathname === '/api/docs/whitepaper') return json(res, 200, whitepaper());
  if (req.method === 'POST' && url.pathname === '/api/profile/challenge') {
    const identity = profileFromBody(await requestBody(req));
    if (!identity) return json(res, 400, { detail: 'A supported wallet address and chain are required.' });
    const nonce = nodeCrypto.randomBytes(18).toString('hex');
    const message = `FEELESS profile verification\nWallet: ${identity.address}\nChain: ${identity.chain}\nNonce: ${nonce}\nExpires: ${new Date(Date.now() + PROFILE_CHALLENGE_MS).toISOString()}`;
    profileChallenges.set(identity.key, { message, expiresAt: Date.now() + PROFILE_CHALLENGE_MS });
    return json(res, 200, { message, expiresAt: Date.now() + PROFILE_CHALLENGE_MS });
  }
  const profileMatch = url.pathname.match(/^\/api\/profile\/([^/]+)$/);
  if (req.method === 'GET' && profileMatch) {
    const address = decodeURIComponent(profileMatch[1]);
    const chain = normalizeChain(url.searchParams.get('chain'));
    const normalized = normalizeAddress(chain, address);
    if (!normalized) return json(res, 400, { detail: 'A supported wallet address and chain are required.' });
    const profile = profileRecord(chain, normalized);
    return json(res, 200, profileView(profile, ''));
  }
  if (req.method === 'POST' && url.pathname === '/api/profile/me') {
    const body = await requestBody(req);
    const identity = proofFromBody(body);
    if (!identity) return json(res, 401, { detail: 'Connect your wallet and sign the profile verification message.' });
    return json(res, 200, profileView(profileRecord(identity.chain, identity.address), identity.key));
  }
  if (req.method === 'POST' && url.pathname === '/api/profile/save') {
    const body = await requestBody(req);
    const identity = proofFromBody(body);
    if (!identity) return json(res, 401, { detail: 'Connect your wallet and sign the profile verification message.' });
    const profile = profileRecord(identity.chain, identity.address);
    const clean = value => String(value || '').trim().slice(0, 280);
    const cleanUrl = value => {
      const candidate = clean(value);
      try {
        const parsed = new URL(candidate);
        return ['http:', 'https:'].includes(parsed.protocol) ? candidate : '';
      } catch { return ''; }
    };
    const category = PROFILE_CATEGORIES.includes(body.category) ? body.category : 'Trader';
    profile.displayName = clean(body.displayName);
    profile.username = clean(body.username).replace(/[^a-zA-Z0-9_ .-]/g, '').slice(0, 32);
    profile.bio = clean(body.bio).slice(0, 160);
    profile.category = category;
    profile.avatarUrl = cleanUrl(body.avatarUrl);
    profile.backgroundUrl = cleanUrl(body.backgroundUrl);
    profile.xUrl = cleanUrl(body.xUrl);
    profile.websiteUrl = cleanUrl(body.websiteUrl);
    profile.isPrivate = Boolean(body.isPrivate);
    profile.updatedAt = Date.now();
    return json(res, 200, profileView(profile, identity.key));
  }
  const profileFlagMatch = url.pathname.match(/^\/api\/profile\/([^/]+)\/flag$/);
  if (req.method === 'POST' && profileFlagMatch) {
    const body = await requestBody(req);
    const reporter = proofFromBody(body);
    const chain = normalizeChain(body.targetChain);
    const targetAddress = normalizeAddress(chain, decodeURIComponent(profileFlagMatch[1]));
    if (!reporter || !targetAddress) return json(res, 401, { detail: 'Connect your wallet and sign before flagging a profile.' });
    if (identityKey(reporter.chain, reporter.address) === identityKey(chain, targetAddress)) return json(res, 400, { detail: 'You cannot flag your own profile.' });
    const targetKey = identityKey(chain, targetAddress);
    if (!profileFlags.has(targetKey)) profileFlags.set(targetKey, new Set());
    profileFlags.get(targetKey).add(reporter.key);
    return json(res, 200, { flagged: true, flagCount: flagCount(chain, targetAddress) });
  }
  const chatMatch = url.pathname.match(/^\/api\/chat\/([^/]+)(\/online)?$/);
  if (chatMatch) {
    const room = decodeURIComponent(chatMatch[1]);
    if (chatMatch[2]) return json(res, 200, { room, online: new Set(roomMessages(room).map(message => message.address || message.username)).size });
    if (req.method === 'GET') return json(res, 200, { room, messages: roomMessages(room).map(message => publicProfileForMessage(message, '')) });
    if (req.method === 'POST') {
      const body = await requestBody(req);
      const identity = proofFromBody(body);
      if (!identity) return json(res, 401, { detail: 'Connect your wallet and sign before joining the chat.' });
      const cooldown = checkChatLimit(room, identity);
      if (cooldown) return json(res, 429, { detail: `Chat cooldown active. Try again in ${cooldown}s.`, retryAfter: cooldown });
      const profile = profileRecord(identity.chain, identity.address);
      const text = String(body.text || '').trim().slice(0, 1000);
      if (!text) return json(res, 400, { detail: 'Message cannot be blank' });
      const parentId = body.parentId ? String(body.parentId) : null;
      if (parentId && !roomMessages(room).some(item => item.id === parentId)) return json(res, 400, { detail: 'Reply target is no longer in this room.' });
      const message = {
        id: crypto.randomUUID(),
        room,
        address: identity.address,
        chain: identity.chain,
        username: profile.username || profile.displayName || `${identity.address.slice(0, 6)}…${identity.address.slice(-4)}`,
        text,
        parentId,
        tokens: null,
        ts: Date.now(),
      };
      roomMessages(room).push(message);
      recordChatComment(room, identity);
      return json(res, 200, publicProfileForMessage(message, identity.key));
    }
  }
  const chatInteractionMatch = url.pathname.match(/^\/api\/chat\/([^/]+)\/([^/]+)\/(like|reply)$/);
  if (chatInteractionMatch && req.method === 'POST') {
    const room = decodeURIComponent(chatInteractionMatch[1]);
    const messageId = decodeURIComponent(chatInteractionMatch[2]);
    const action = chatInteractionMatch[3];
    const body = await requestBody(req);
    const identity = proofFromBody(body);
    const message = roomMessages(room).find(item => item.id === messageId);
    if (!identity) return json(res, 401, { detail: 'Connect your wallet and sign before interacting.' });
    if (!message) return json(res, 404, { detail: 'Message not found in this room.' });
    if (action === 'reply') {
      const cooldown = checkChatLimit(room, identity);
      if (cooldown) return json(res, 429, { detail: `Chat cooldown active. Try again in ${cooldown}s.`, retryAfter: cooldown });
      const text = String(body.text || '').trim().slice(0, 1000);
      if (!text) return json(res, 400, { detail: 'Reply cannot be blank' });
      const profile = profileRecord(identity.chain, identity.address);
      const reply = { id: crypto.randomUUID(), room, address: identity.address, chain: identity.chain, username: profile.username || profile.displayName || `${identity.address.slice(0, 6)}…${identity.address.slice(-4)}`, text, parentId: message.id, tokens: null, ts: Date.now() };
      roomMessages(room).push(reply);
      recordChatComment(room, identity);
      return json(res, 200, publicProfileForMessage(reply, identity.key));
    }
    if (!messageLikes.has(message.id)) messageLikes.set(message.id, new Set());
    const liked = messageLikes.get(message.id);
    if (liked.has(identity.key)) liked.delete(identity.key); else liked.add(identity.key);
    return json(res, 200, { liked: liked.has(identity.key), likeCount: liked.size });
  }
  if (req.method === 'GET' && url.pathname === '/api/cats/strategies') {
    return json(res, 200, { mode: 'paper', strategies: Object.entries(PAPER_STRATEGIES).map(([id, value]) => ({ id, ...value })) });
  }
  if (req.method === 'GET' && url.pathname === '/api/cats/leaderboard') {
    const view = ['pnl', 'volume', 'win_rate'].includes(url.searchParams.get('view')) ? url.searchParams.get('view') : 'pnl';
    const rows = Array.from(paperCats.values()).map(paperPublicCat);
    rows.sort((a, b) => view === 'volume' ? b.volumeSol - a.volumeSol : view === 'win_rate' ? (b.winRate || 0) - (a.winRate || 0) : b.realizedPnlSol - a.realizedPnlSol);
    return json(res, 200, { mode: 'paper', view, rows: rows.slice(0, 50), disclosure: 'Paper results from this browser session. No profit is presented as on-chain performance.' });
  }
  if (req.method === 'GET' && url.pathname === '/api/cats/activity') {
    const catId = url.searchParams.get('catId');
    return json(res, 200, { mode: 'paper', events: paperActivity.filter(event => !catId || event.catId === catId).slice(0, 80), disclosure: 'Paper activity only. Provider observations and paper orders are not blockchain transactions.' });
  }
  if (req.method === 'GET' && url.pathname === '/api/cats') {
    const ownerId = String(url.searchParams.get('ownerId') || '');
    return json(res, 200, { mode: 'paper', cats: Array.from(paperCats.values()).filter(cat => !ownerId || cat.ownerId === ownerId).map(paperPublicCat), strategies: Object.entries(PAPER_STRATEGIES).map(([id, value]) => ({ id, ...value })) });
  }
  if (req.method === 'POST' && url.pathname === '/api/cats') {
    const created = createPaperCat(await requestBody(req));
    return json(res, 201, { cat: paperPublicCat(created.cat), recoveryKey: created.recoveryKey, disclosure: 'Paper wallet only. No SOL was deposited and no private key was sent to the client. Save the recovery key; it is shown once.' });
  }
  const catActionMatch = url.pathname.match(/^\/api\/cats\/([^/]+)\/action$/);
  if (catActionMatch && req.method === 'POST') {
    const cat = paperCats.get(decodeURIComponent(catActionMatch[1]));
    if (!cat) return json(res, 404, { detail: 'Cat not found.' });
    expirePaperCat(cat);
    if (cat.expiredAt || cat.status === 'expired') {
      return json(res, 409, { detail: 'This Cat expired after 14 days without a saved recovery key or first funding deposit.' });
    }
    const body = await requestBody(req);
    const action = String(body.action || '');
    if (action === 'start') {
      if (cat.revoked) return json(res, 409, { detail: 'This agent has been revoked.' });
      cat.status = 'running';
      paperEvent(cat, 'STARTED', 'Paper agent started. It can only use paper balance and provider snapshots.');
      await runPaperCycle(cat);
    } else if (action === 'stop') {
      cat.status = 'stopped';
      paperEvent(cat, 'STOPPED', 'Emergency stop engaged. Open paper positions remain visible and withdrawable.');
    } else if (action === 'run') {
      await runPaperCycle(cat);
    } else if (action === 'withdraw') {
      const amount = Math.min(cat.balanceSol, Math.max(0, Number(body.amount) || cat.balanceSol));
      if (amount <= 0) return json(res, 400, { detail: 'No paper balance is available to withdraw.' });
      cat.balanceSol -= amount;
      cat.withdrawnSol += amount;
      paperEvent(cat, 'WITHDRAW', `${amount.toFixed(4)} SOL marked withdrawable from the paper wallet. No blockchain transfer occurred.`, { amountSol: amount });
    } else if (action === 'revoke') {
      cat.revoked = true;
      cat.status = 'stopped';
      paperEvent(cat, 'REVOKED', 'Agent controls revoked. No new paper cycles can run.');
    } else if (action === 'confirm_recovery') {
      const supplied = String(body.recoveryKey || '').trim();
      if (!supplied || recoveryKeyHash(supplied) !== cat.recoveryKeyHash) return json(res, 400, { detail: 'Recovery key does not match this Cat.' });
      cat.recoveryConfirmedAt = new Date().toISOString();
      paperEvent(cat, 'RECOVERY_SAVED', 'Recovery key marked as saved. The 14-day no-funding expiry no longer applies.');
    } else if (action === 'coin_plan') {
      cat.coinPlan = coinPlan(body.coinPlan);
      cat.coinStatus = cat.coinPlan === 'create' ? 'planned' : 'not_selected';
      paperEvent(cat, 'COIN_PLAN', cat.coinPlan === 'create' ? 'Coin creation was selected for a later supported launch flow. No coin was created in paper mode.' : 'Coin creation was deferred.');
    } else if (action === 'controls') {
      cat.risk.maxPositionSol = Math.min(2, Math.max(0.01, Number(body.maxPositionSol) || cat.risk.maxPositionSol));
      cat.risk.maxDailyLossSol = Math.min(5, Math.max(0.01, Number(body.maxDailyLossSol) || cat.risk.maxDailyLossSol));
      cat.risk.dailyBuyLimitSol = Math.min(PAPER_MAX_DAILY_BUY_SOL, Math.max(0.01, Number(body.dailyBuyLimitSol) || cat.risk.dailyBuyLimitSol));
      cat.risk.allowlist = cleanPaperList(body.allowlist);
      cat.risk.blocklist = cleanPaperList(body.blocklist);
      paperEvent(cat, 'CONTROLS', 'Risk limits updated by the Cat owner.');
    } else {
      return json(res, 400, { detail: 'Unknown Cat action.' });
    }
    return json(res, 200, { cat: paperPublicCat(cat), events: paperActivity.filter(event => event.catId === cat.id).slice(0, 40) });
  }
  const catMatch = url.pathname.match(/^\/api\/cats\/([^/]+)$/);
  if (catMatch && req.method === 'GET') {
    const cat = paperCats.get(decodeURIComponent(catMatch[1]));
    if (!cat) return json(res, 404, { detail: 'Cat not found.' });
    return json(res, 200, { mode: 'paper', cat: paperPublicCat(cat), events: paperActivity.filter(event => event.catId === cat.id).slice(0, 80), disclosure: 'Paper activity only. No on-chain transactions are represented.' });
  }
  if (req.method === 'GET' && url.pathname === '/api/trading/status') {
    return json(res, 200, { provider: 'Jupiter', network: 'solana-mainnet', signing: 'Phantom', configured: TRADING_CONFIGURED, execution_ready: TRADING_CONFIGURED, fee_back_status: 'PLANNED', eligible_fee_rules: 'Not activated', supported_execution_chains: ['solana'], detail: TRADING_CONFIGURED ? 'Backend execution is ready.' : tradingError() });
  }
  const mintMatch = url.pathname.match(/^\/api\/trading\/mint\/([^/]+)$/);
  if (req.method === 'GET' && mintMatch) {
    const mint = decodeURIComponent(mintMatch[1]);
    const symbol = Object.entries(MINTS).find(([, value]) => value === mint)?.[0] || 'TOKEN';
    return json(res, 200, { mint, decimals: 9, symbol, supply: null, mint_authority: null, freeze_authority: null, source: 'Preview metadata boundary · supply verification unavailable' });
  }
  const historyMatch = url.pathname.match(/^\/api\/trading\/history\/([^/]+)$/);
  if (req.method === 'GET' && historyMatch) {
    const wallet = decodeURIComponent(historyMatch[1]);
    const transactions = Array.from(orders.values())
      .filter(order => order.wallet === wallet && order.signature)
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .slice(0, 30)
      .map(order => ({ order_id: order.order_id, state: order.state, signature: order.signature, created_at: order.created_at, input_mint: order.input_mint, output_mint: order.output_mint }));
    return json(res, 200, { transactions, eligible_fees_usd: null, distributions: [], fee_back_status: 'PLANNED' });
  }
  const balanceMatch = url.pathname.match(/^\/api\/trading\/balance\/([^/]+)$/);
  if (req.method === 'GET' && balanceMatch) {
    const result = await rpc('getBalance', [decodeURIComponent(balanceMatch[1]), { commitment: 'confirmed' }]);
    return json(res, 200, { lamports: result.value, slot: result.context.slot, source: 'Solana RPC' });
  }
  if (req.method === 'POST' && url.pathname === '/api/trading/quote') {
    const body = await requestBody(req);
    const inputMint = String(body.input_mint || '');
    const outputMint = String(body.output_mint || '');
    const wallet = body.wallet ? String(body.wallet) : null;
    const decimals = inputMint === 'So11111111111111111111111111111111111111112' ? 9 : 6;
    const amount = Number(body.amount);
    if (!inputMint || !outputMint || inputMint === outputMint || !Number.isFinite(amount) || amount <= 0) return json(res, 400, { detail: 'Choose two different assets and enter a valid amount.' });
    const query = new URLSearchParams({ inputMint, outputMint, amount: String(Math.round(amount * (10 ** decimals))), slippageBps: String(Number(body.slippage_bps) || 50) });
    if (wallet) query.set('taker', wallet);
    let quote;
    if (TRADING_CONFIGURED) {
      quote = await jupiter('GET', `/swap/v2/order?${query.toString()}`);
    } else {
      const response = await fetch(`${JUPITER_PUBLIC_QUOTE_API}/quote?${query.toString()}`, { signal: AbortSignal.timeout(15000) });
      quote = await response.json();
      if (!response.ok) return json(res, 503, { detail: quote.error || 'Jupiter route unavailable for this pair.' });
    }
    if (quote.errorCode || quote.error || !quote.outAmount) return json(res, 400, { detail: quote.errorMessage || quote.error || 'No executable route available for this pair.' });
    const orderId = crypto.randomUUID();
    const createdAt = new Date().toISOString();
    const storedQuote = TRADING_CONFIGURED ? quote : { ...quote, transaction: null };
    orders.set(orderId, { order_id: orderId, wallet, quote: storedQuote, state: 'quoted', simulated: false, created_at: createdAt, expires_at: Date.now() / 1000 + 45, input_mint: inputMint, output_mint: outputMint });
    return json(res, 200, {
      order_id: orderId,
      created_at: createdAt,
      expires_at: orders.get(orderId).expires_at,
      input_metadata: { mint: inputMint, decimals, symbol: inputMint === 'So11111111111111111111111111111111111111112' ? 'SOL' : 'TOKEN' },
      output_metadata: { mint: outputMint, decimals: 6, symbol: 'TOKEN' },
      quote: { ...storedQuote, router: 'Jupiter' },
      fee_back: { status: 'PLANNED', eligible_usd: null, distribution: null },
    });
  }
  if (req.method === 'POST' && url.pathname === '/api/trading/simulate') {
    requireTrading();
    const body = await requestBody(req);
    const order = orders.get(String(body.order_id));
    if (!order || order.state !== 'quoted' || order.expires_at <= Date.now() / 1000) return json(res, 409, { detail: 'Order expired. Request a fresh quote.' });
    if (!order.quote.transaction || !order.wallet) return json(res, 400, { detail: 'Connect a Solana wallet and request a new quote' });
    const result = await rpc('simulateTransaction', [order.quote.transaction, { encoding: 'base64', sigVerify: false, replaceRecentBlockhash: false, commitment: 'confirmed' }]);
    const value = result?.value || {};
    if (value.err) return json(res, 400, { detail: `Simulation failed: ${JSON.stringify(value.err).slice(0, 150)}. No transaction submitted.` });
    order.simulated = true;
    return json(res, 200, { success: true, units_consumed: value.unitsConsumed, broadcast: false });
  }
  if (req.method === 'POST' && url.pathname === '/api/trading/execute') {
    requireTrading();
    const body = await requestBody(req);
    const order = orders.get(String(body.order_id));
    if (!order) return json(res, 404, { detail: 'Unknown order' });
    if (order.state !== 'quoted') return json(res, 200, { state: order.state, signature: order.signature, detail: 'Already processed. Check status; do not resubmit.' });
    if (order.expires_at <= Date.now() / 1000 || !order.simulated || !body.signed_transaction) return json(res, 409, { detail: 'Fresh quote and successful simulation required before signing' });
    order.state = 'submitted';
    order.signed_transaction = body.signed_transaction;
    try {
      const payload = { signedTransaction: body.signed_transaction, requestId: order.quote.requestId };
      if (order.quote.lastValidBlockHeight != null) payload.lastValidBlockHeight = order.quote.lastValidBlockHeight;
      const result = await jupiter('POST', '/swap/v2/execute', { body: JSON.stringify(payload) });
      order.signature = result.signature;
      if (result.status === 'Failed') order.state = 'failed';
    } catch (error) {
      return json(res, 200, { state: 'submitted', signature: order.signature || null, detail: 'Provider response uncertain. Check status before any new trade.' });
    }
    return checkPreviewStatus(order, res);
  }
  const orderMatch = url.pathname.match(/^\/api\/trading\/order\/([^/]+)$/);
  if (req.method === 'GET' && orderMatch) {
    requireTrading();
    const order = orders.get(decodeURIComponent(orderMatch[1]));
    if (!order) return json(res, 404, { detail: 'Order not found' });
    return checkPreviewStatus(order, res);
  }
  if (req.method === 'GET' && url.pathname.startsWith('/api/trading/')) return json(res, 503, { detail: tradingError() });
  if (req.method === 'GET' && url.pathname === '/api/docs/whitepaper.pdf') {
    const pdf = minimalPdf();
    res.writeHead(200, { 'Content-Type': 'application/pdf', 'Content-Length': pdf.length, 'Access-Control-Allow-Origin': '*' });
    return res.end(pdf);
  }
  return json(res, 404, { detail: 'Endpoint not found' });
}

const server = http.createServer(async (req, res) => {
  try {
    await route(req, res, new URL(req.url, `http://${req.headers.host || 'localhost'}`));
  } catch (error) {
    if (!warnProviderThrottle(error)) {
      console.error('[preview-api]', error);
    }
    json(res, error.statusCode || 503, { detail: publicError(error) });
  }
});

function startServer() {
  server.listen(PORT, '127.0.0.1', () => {
    loadPaperState();
    console.log(`[preview-api] listening on http://127.0.0.1:${PORT} with live public market providers`);
    Promise.allSettled([dexBoostFeed('trending'), dexBoostFeed('new')])
      .then(() => console.log('[preview-api] DexScreener radar cache warmed'))
      .catch(() => {});
    const paperLoop = setInterval(() => {
      Promise.all(Array.from(paperCats.values()).filter(cat => cat.status === 'running').map(cat => runPaperCycle(cat)))
        .catch(error => console.warn('[preview-api] paper agent cycle failed:', publicError(error)));
    }, 20000);
    paperLoop.unref?.();
  });
}

if (require.main === module) startServer();

module.exports = {
  ASSET_THROTTLE_WARNING_COOLDOWN_MS,
  GECKO_NEW_ALL_PAGE_BUDGET,
  PROVIDER_RATE_LIMIT_COOLDOWN_MS,
  applyScreener,
  assetThrottleWarningCooldown,
  cache,
  providerRateLimitCooldowns,
  geckoCandles,
  normalizeScreener,
  route,
  scorePair,
  server,
  startServer,
};

const path = require('path');

function persistPaperState() {
  const directory = path.dirname(PAPER_STATE_PATH);
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const temporaryPath = `${PAPER_STATE_PATH}.${process.pid}.${nodeCrypto.randomUUID()}.tmp`;
  try {
    fs.writeFileSync(temporaryPath, JSON.stringify(paperStateSnapshot()), { encoding: 'utf8', mode: 0o600 });
    fs.renameSync(temporaryPath, PAPER_STATE_PATH);
    fs.chmodSync(PAPER_STATE_PATH, 0o600);
  } catch (error) {
    try { fs.rmSync(temporaryPath, { force: true }); } catch {}
    throw new Error(`Paper Cat state could not be saved: ${error.message}`);
  }
}

function loadPaperState() {
  if (!fs.existsSync(PAPER_STATE_PATH)) return;
  let state;
  try {
    state = JSON.parse(fs.readFileSync(PAPER_STATE_PATH, 'utf8'));
  } catch (error) {
    throw new Error(`Paper Cat state could not be loaded: ${error.message}`);
  }
  if (state?.version !== PAPER_STATE_VERSION || !Array.isArray(state.cats) || !Array.isArray(state.activity)) {
    throw new Error(`Paper Cat state has unsupported format at ${PAPER_STATE_PATH}.`);
  }
  state.cats.map(hydratePaperCat).forEach(cat => paperCats.set(cat.id, cat));
  paperActivity.push(...state.activity.slice(0, 500));
  for (const cat of paperCats.values()) expirePaperCat(cat);
}

const PAPER_STATE_PATH = process.env.PREVIEW_STATE_PATH
  || process.env.PAPER_CATS_STATE_PATH
  || path.join(process.cwd(), '.preview-data', 'paper-state.json');

function hydratePaperCat(record) {
  if (!record || typeof record !== 'object' || !record.id || !record.ownerId || !record.recoveryKeyHash) {
    throw new Error('Paper Cat state contains an invalid Cat record.');
  }
  return {
    ...record,
    mode: 'paper',
    walletMode: paperWalletMode(record.walletMode),
    coinPlan: coinPlan(record.coinPlan),
    coinStatus: record.coinStatus || (record.coinPlan === 'create' ? 'planned' : 'not_selected'),
    positions: Array.isArray(record.positions) ? record.positions : [],
    pnlHistory: Array.isArray(record.pnlHistory) ? record.pnlHistory : [],
    risk: {
      maxPositionSol: Number(record.risk?.maxPositionSol) || 0.25,
      maxDailyLossSol: Number(record.risk?.maxDailyLossSol) || 0.5,
      dailyBuyLimitSol: Number(record.risk?.dailyBuyLimitSol) || 2,
      allowlist: Array.isArray(record.risk?.allowlist) ? record.risk.allowlist : [],
      blocklist: Array.isArray(record.risk?.blocklist) ? record.risk.blocklist : [],
    },
  };
}
