const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const nodeCrypto = require('node:crypto');
const { once } = require('node:events');
const fs = require('node:fs');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { Keypair } = require('@solana/web3.js');

const DEX_API_URL = 'http://dex.test';
const GECKO_API_URL = 'http://gecko.test/api/v2';
const PUMP_API_URL = 'http://pump.test';
const POOL_ADDRESS = 'PoolAddress123';

process.env.DEX_API_URL = DEX_API_URL;
process.env.GECKO_API_URL = GECKO_API_URL;
process.env.PUMP_API_URL = PUMP_API_URL;

const {
  ASSET_THROTTLE_WARNING_COOLDOWN_MS,
  PROVIDER_RATE_LIMIT_COOLDOWN_MS,
  applyScreener,
  assetThrottleWarningCooldown,
  cache,
  normalizeScreener,
  providerRateLimitCooldowns,
  scorePair,
  server,
} = require('./preview-api');

test.beforeEach(() => {
  cache.clear();
  providerRateLimitCooldowns.clear();
});

function providerResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return body;
    },
  };
}

function request(baseUrl, path, fetchImpl) {
  return fetchImpl(`${baseUrl}${path}`).then(async response => ({
    status: response.status,
    body: await response.json(),
  }));
}

function post(baseUrl, path, body, fetchImpl) {
  return fetchImpl(`${baseUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(async response => ({
    status: response.status,
    body: await response.json(),
  }));
}

function signSolana(keypair, message) {
  const pkcs8Prefix = Buffer.from('302e020100300506032b657004220420', 'hex');
  const key = { key: Buffer.concat([pkcs8Prefix, Buffer.from(keypair.secretKey.subarray(0, 32))]), format: 'der', type: 'pkcs8' };
  return nodeCrypto.sign(null, Buffer.from(message), key).toString('base64');
}

test('market screeners rank observed provider signals without calling them safety signals', () => {
  const now = Date.now();
  const deepLiquidity = {
    chainId: 'solana',
    pairAddress: 'deep-liquidity',
    liquidity: { usd: 900000 },
    volume: { h24: 200000 },
    txns: { h24: { buys: 500, sells: 480 } },
    priceChange: { h1: 1, h6: 2, h24: 4 },
    pairCreatedAt: now - 5 * 86400000,
  };
  const activeVolume = {
    chainId: 'solana',
    pairAddress: 'active-volume',
    liquidity: { usd: 18000 },
    volume: { h24: 950000 },
    txns: { h24: { buys: 900, sells: 650 } },
    priceChange: { h1: 5, h6: 12, h24: 28 },
    pairCreatedAt: now - 2 * 86400000,
  };

  assert.equal(normalizeScreener('unknown', 'trending'), 'quality');
  assert.equal(normalizeScreener('', 'new'), 'new');
  assert.ok(scorePair(deepLiquidity, 'quality', now).score > 0);

  const quality = applyScreener({ label: 'Boosted discovery', pairs: [activeVolume, deepLiquidity] }, 'trending', 'quality');
  const volume = applyScreener({ label: 'Boosted discovery', pairs: [deepLiquidity, activeVolume] }, 'trending', 'volume');
  assert.equal(quality.screener, 'quality');
  assert.equal(quality.screener_label, 'Best observed setups');
  assert.equal(quality.pairs[0].pairAddress, 'deep-liquidity');
  assert.equal(volume.pairs[0].pairAddress, 'active-volume');
  assert.match(quality.screener_disclosure, /Not a security audit or trade signal/);
  assert.equal(quality.pairs[0].signals.screener, 'quality');
  assert.ok(quality.pairs[0].signals.score_reasons.length > 0);
});

test('market screeners keep cached and stale responses aligned with the requested mode', async () => {
  const originalFetch = global.fetch;
  const originalNow = Date.now;
  let available = true;
  const modes = {
    quality: 'Best observed setups',
    momentum: 'Momentum',
    volume: 'Volume leaders',
    new: 'Fresh with activity',
  };
  cache.clear();
  global.fetch = async target => {
    const url = String(target);
    if (url.startsWith(`${PUMP_API_URL}/coins?`)) {
      if (!available) return providerResponse({ detail: 'provider down' }, 503);
      return providerResponse([{
        mint: 'ModeSwitchCoin123',
        name: 'Mode Switch Coin',
        symbol: 'SWITCH',
        created_timestamp: originalNow() - 3 * 3600000,
        usd_market_cap: 250000,
      }]);
    }
    throw new Error(`Unexpected provider request: ${url}`);
  };

  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  const feedUrl = screen => `/api/market/feed?kind=trending&chain=solana&scope=pump${screen === 'quality' ? '' : `&screen=${screen}`}`;
  try {
    await Promise.all(Object.keys(modes).map(async screen => {
      const response = await request(baseUrl, feedUrl(screen), originalFetch);
      assert.equal(response.status, 200);
      assert.equal(response.body.screener, screen);
      assert.equal(response.body.screener_label, modes[screen]);
      assert.equal(response.body.pairs[0].signals.screener, screen);
      assert.equal(response.body.pairs[0].signals.score_label, modes[screen]);
      assert.ok(response.body.pairs[0].signals.score_reasons.length > 0);
      assert.ok(response.body.screener_disclosure);
    }));

    const quality = await request(baseUrl, feedUrl('quality'), originalFetch);
    Date.now = () => originalNow() + 21000;
    available = false;
    const staleMomentum = await request(baseUrl, feedUrl('momentum'), originalFetch);
    assert.equal(staleMomentum.status, 200);
    assert.equal(staleMomentum.body.stale, true);
    assert.equal(staleMomentum.body.screener, 'momentum');
    assert.equal(staleMomentum.body.screener_label, modes.momentum);
    assert.equal(staleMomentum.body.pairs[0].signals.screener, 'momentum');
    assert.equal(staleMomentum.body.pairs[0].signals.score_label, modes.momentum);
    assert.notEqual(staleMomentum.body.pairs[0].signals.score_label, quality.body.pairs[0].signals.score_label);
    assert.ok(staleMomentum.body.pairs[0].signals.score_reasons.every(reason => !/quality/i.test(reason)));
    assert.match(staleMomentum.body.screener_disclosure, /price movement and activity/i);
  } finally {
    Date.now = originalNow;
    global.fetch = originalFetch;
    cache.clear();
    await new Promise(resolve => server.close(resolve));
  }
});

async function proof(baseUrl, keypair, fetchImpl) {
  const address = keypair.publicKey.toString();
  const challenge = await post(baseUrl, '/api/profile/challenge', { address, chain: 'solana' }, fetchImpl);
  assert.equal(challenge.status, 200);
  return { address, chain: 'solana', message: challenge.body.message, signature: signSolana(keypair, challenge.body.message) };
}

async function freePort() {
  const probe = net.createServer();
  await new Promise(resolve => probe.listen(0, '127.0.0.1', resolve));
  const port = probe.address().port;
  await new Promise(resolve => probe.close(resolve));
  return port;
}

async function startPersistentPreview(statePath) {
  const port = await freePort();
  const child = spawn(process.execPath, ['scripts/preview-api.js'], {
    cwd: process.cwd(),
    env: { ...process.env, API_PORT: String(port), PREVIEW_STATE_PATH: statePath },
    stdio: ['ignore', 'ignore', 'pipe'],
  });
  const waitForReady = async () => {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      try {
        const response = await fetch(`http://127.0.0.1:${port}/api/`);
        if (response.ok) return;
      } catch {}
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    throw new Error('Preview API did not become ready for persistence test.');
  };
  try {
    await waitForReady();
  } catch (error) {
    child.kill('SIGKILL');
    throw error;
  }
  return { child, baseUrl: `http://127.0.0.1:${port}` };
}

async function stopPersistentPreview(child) {
  if (child.exitCode != null) return;
  child.kill('SIGTERM');
  await once(child, 'exit');
}

test('preview candle contract follows a discovered pool and rejects invalid intervals', async () => {
  const originalFetch = global.fetch;
  global.fetch = async target => {
    const url = String(target);
    if (url === `${DEX_API_URL}/token-boosts/top/v1`) return providerResponse({ error: 'not available in test' }, 503);
    if (url === `${GECKO_API_URL}/networks/solana/trending_pools?page=1`) {
      return providerResponse({
        data: [{
          id: `solana_${POOL_ADDRESS}`,
          attributes: {
            address: POOL_ADDRESS,
            name: 'TEST / SOL',
            base_token_price_usd: '1.25',
            reserve_in_usd: '100000',
          },
          relationships: {
            base_token: { data: { id: 'solana_token123' } },
            quote_token: { data: { id: 'solana_So11111111111111111111111111111111111111112' } },
          },
        }],
      });
    }
    if (url.startsWith(`${GECKO_API_URL}/networks/solana/pools/${POOL_ADDRESS}/ohlcv/hour`)) {
      return providerResponse({
        data: {
          attributes: {
            ohlcv_list: [
              [300, 3, 4, 2, 3.5, 30],
              [100, 1, 2, 0.5, 1.5, 10],
              [200, 2, 3, 1, 2.5, 20],
              [200, 2, 3, 1, 2.5, 999],
            ],
          },
        },
      });
    }
    throw new Error(`Unexpected provider request: ${url}`);
  };

  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;

  try {
    const feed = await request(baseUrl, '/api/market/feed?kind=trending&chain=solana', originalFetch);
    assert.equal(feed.status, 200);
    assert.equal(feed.body.provider, 'GeckoTerminal');
    const discoveredPool = feed.body.pairs[0];
    assert.equal(discoveredPool.pairAddress, POOL_ADDRESS);

    const candles = await request(
      baseUrl,
      `/api/market/candles/${discoveredPool.chainId}/${discoveredPool.pairAddress}?interval=1h`,
      originalFetch,
    );
    assert.equal(candles.status, 200);
    assert.equal(candles.body.provider, 'GeckoTerminal');
    assert.deepEqual(candles.body.candles.map(row => row[0]), [100, 200, 300]);
    assert.equal(candles.body.candles[1][5], 999);

    const originalConsoleError = console.error;
    console.error = () => {};
    let invalidInterval;
    try {
      invalidInterval = await request(
        baseUrl,
        `/api/market/candles/${discoveredPool.chainId}/${discoveredPool.pairAddress}?interval=2h`,
        originalFetch,
      );
    } finally {
      console.error = originalConsoleError;
    }
    assert.equal(invalidInterval.status, 400);
    assert.match(invalidInterval.body.detail, /Invalid chart interval or network/);
  } finally {
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});

test('broad new-coin discovery uses GeckoTerminal across a network and hides pools without images', async () => {
  const originalFetch = global.fetch;
  cache.clear();
  global.fetch = async target => {
    const url = String(target);
    if (url === `${GECKO_API_URL}/networks/eth/new_pools?page=1`) {
      return providerResponse({
        data: [
          {
            id: 'eth_no-image',
            attributes: { address: 'NoImagePool', name: 'NOIMAGE / WETH', base_token_price_usd: '1', image_url: null },
            relationships: {
              base_token: { data: { id: 'eth_no-image-token' } },
              quote_token: { data: { id: 'eth_0xweth' } },
            },
          },
          {
            id: 'eth_with-image',
            attributes: { address: 'ImagePool', name: 'IMAGE / WETH', base_token_price_usd: '2', image_url: 'https://logo.test/image.png' },
            relationships: {
              base_token: { data: { id: 'eth_image-token' } },
              quote_token: { data: { id: 'eth_0xweth' } },
            },
          },
        ],
      });
    }
    throw new Error(`Unexpected provider request: ${url}`);
  };
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const response = await request(baseUrl, '/api/market/feed?kind=new&chain=ethereum', originalFetch);
    assert.equal(response.status, 200);
    assert.equal(response.body.provider, 'GeckoTerminal');
    assert.equal(response.body.primary_provider, 'GeckoTerminal');
    assert.equal(response.body.image_required, true);
    assert.equal(response.body.image_filtered_count, 1);
    assert.deepEqual(response.body.pairs.map(pair => pair.pairAddress), ['ImagePool']);
    assert.equal(response.body.pairs[0].info.imageUrl, 'https://logo.test/image.png');
  } finally {
    global.fetch = originalFetch;
    cache.clear();
    await new Promise(resolve => server.close(resolve));
  }
});

test('all-network new-coin fallback cools down rate-limited Gecko requests and recovers on the next refresh', async () => {
  const originalFetch = global.fetch;
  const originalNow = Date.now;
  let geckoAvailable = false;
  let geckoCalls = 0;
  let dexCalls = 0;
  cache.clear();
  providerRateLimitCooldowns.clear();
  global.fetch = async target => {
    const url = String(target);
    if (url.startsWith(`${GECKO_API_URL}/networks/`) && url.includes('/new_pools?page=1')) {
      geckoCalls += 1;
      if (!geckoAvailable) return providerResponse({ detail: 'rate limited' }, 429);
      const network = url.split('/networks/')[1].split('/')[0];
      return providerResponse({
        data: [{
          id: `${network}_recovered-pool`,
          attributes: {
            address: `${network}-recovered-pool`,
            name: 'RECOVERED / TOKEN',
            base_token_price_usd: '1.25',
            image_url: 'https://logo.test/recovered.png',
          },
          relationships: {
            base_token: { data: { id: `${network}_recovered-token` } },
            quote_token: { data: { id: `${network}_quote-token` } },
          },
        }],
      });
    }
    if (url === `${DEX_API_URL}/token-boosts/latest/v1`) {
      dexCalls += 1;
      return providerResponse([
        { chainId: 'solana', tokenAddress: 'SupportedMint' },
        { chainId: 'robinhood', tokenAddress: 'UnsupportedMint' },
      ]);
    }
    if (url.startsWith(`${DEX_API_URL}/latest/dex/tokens/`)) {
      dexCalls += 1;
      return providerResponse({
        pairs: [
          {
            chainId: 'solana',
            pairAddress: 'supported-pair',
            baseToken: { address: 'SupportedMint', symbol: 'SUPPORTED', name: 'Supported Coin' },
            info: { imageUrl: 'https://logo.test/supported.png' },
            liquidity: { usd: 50000 },
            pairCreatedAt: Date.now() - 3600000,
          },
          {
            chainId: 'robinhood',
            pairAddress: 'unsupported-pair',
            baseToken: { address: 'UnsupportedMint', symbol: 'UNSUPPORTED', name: 'Unsupported Coin' },
            info: { imageUrl: 'https://logo.test/unsupported.png' },
          },
        ],
      });
    }
    throw new Error(`Unexpected provider request: ${url}`);
  };
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const fallback = await request(baseUrl, '/api/market/feed?kind=new&chain=all', originalFetch);
    assert.equal(fallback.status, 200);
    assert.equal(fallback.body.provider, 'DexScreener');
    assert.equal(fallback.body.primary_provider, 'GeckoTerminal');
    assert.equal(fallback.body.provider_status, 429);
    assert.equal(fallback.body.provider_warning.rate_limited, true);
    assert.equal(fallback.body.fallback_from, 'GeckoTerminal');
    assert.ok(fallback.body.pairs.length > 0);
    assert.ok(fallback.body.pairs.every(pair => ['solana', 'ethereum', 'base', 'bsc', 'arbitrum', 'avalanche', 'polygon', 'sui'].includes(pair.chainId)));
    assert.ok(fallback.body.pairs.every(pair => pair.info?.imageUrl));
    assert.equal(geckoCalls, 8);
    assert.equal(dexCalls, 2);

    const cooldownFallback = await request(baseUrl, '/api/market/feed?kind=new&chain=all', originalFetch);
    assert.equal(cooldownFallback.status, 200);
    assert.equal(cooldownFallback.body.provider, 'DexScreener');
    assert.equal(geckoCalls, 8);
    assert.equal(dexCalls, 2);

    Date.now = () => originalNow() + PROVIDER_RATE_LIMIT_COOLDOWN_MS + 1;
    geckoAvailable = true;
    const recovered = await request(baseUrl, '/api/market/feed?kind=new&chain=all', originalFetch);
    assert.equal(recovered.status, 200);
    assert.equal(recovered.body.provider, 'GeckoTerminal');
    assert.equal(recovered.body.primary_provider, 'GeckoTerminal');
    assert.equal(recovered.body.fallback_from, undefined);
    assert.equal(recovered.body.image_required, true);
    assert.equal(recovered.body.image_filtered_count, 0);
    assert.equal(recovered.body.pairs.length, 8);
    assert.equal(geckoCalls, 16);
    assert.equal(dexCalls, 2);
  } finally {
    Date.now = originalNow;
    global.fetch = originalFetch;
    cache.clear();
    providerRateLimitCooldowns.clear();
    await new Promise(resolve => server.close(resolve));
  }
});

test('preview Pump radar uses Pump.fun as the primary Solana launchpad source', async () => {
  const originalFetch = global.fetch;
  cache.clear();
  global.fetch = async target => {
    const url = String(target);
    if (url.startsWith(`${PUMP_API_URL}/coins?offset=0&limit=50&sort=created_timestamp`)) {
      return providerResponse([{
        mint: 'PumpCoin123',
        name: 'Pump Coin',
        symbol: 'PUMP',
        created_timestamp: Date.now() - 60000,
        usd_market_cap: 125000,
        image_uri: 'https://logo.test/pump.png',
        complete: false,
      }]);
    }
    throw new Error(`Unexpected provider request: ${url}`);
  };
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const response = await request(baseUrl, '/api/market/feed?kind=new&chain=solana&scope=pump', originalFetch);
    assert.equal(response.status, 200);
    assert.equal(response.body.provider, 'Pump.fun');
    assert.equal(response.body.primary_provider, 'Pump.fun');
    assert.equal(response.body.stale, false);
    assert.equal(response.body.stream, false);
    assert.equal(response.body.sourceLabel, 'Pump.fun public coin index · launchpad coverage');
    assert.match(response.body.coverage.discovery, /launchpad coverage/);
    assert.equal(response.body.pairs[0].launchpadId, 'pump');
    assert.equal(response.body.pairs[0].marketStage, 'new');
    assert.equal(response.body.pairs[0].liquidity.usd, undefined);
  } finally {
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});

test('preview Pump radar falls back to GeckoTerminal with visible source metadata', async () => {
  const originalFetch = global.fetch;
  cache.clear();
  global.fetch = async target => {
    const url = String(target);
    if (url.startsWith(`${PUMP_API_URL}/coins?`)) return providerResponse({ detail: 'rate limited' }, 429);
    if (url === `${GECKO_API_URL}/networks/solana/trending_pools?page=1`) {
      return providerResponse({
        data: [{
          id: 'solana_FallbackPool123',
          attributes: { address: 'FallbackPool123', name: 'FALLBACK / SOL', reserve_in_usd: '2500' },
          relationships: {
            base_token: { data: { id: 'solana_fallback-token' } },
            quote_token: { data: { id: 'solana_So11111111111111111111111111111111111111112' } },
          },
        }],
      });
    }
    throw new Error(`Unexpected provider request: ${url}`);
  };
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const response = await request(baseUrl, '/api/market/feed?kind=trending&chain=solana&scope=pump', originalFetch);
    assert.equal(response.status, 200);
    assert.equal(response.body.provider, 'GeckoTerminal');
    assert.equal(response.body.primary_provider, 'Pump.fun');
    assert.equal(response.body.fallback_from, 'Pump.fun');
    assert.match(response.body.fallback_reason, /Pump\.fun unavailable/);
    assert.equal(response.body.stale, false);
    assert.equal(response.body.pairs[0].pairAddress, 'FallbackPool123');
  } finally {
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});

test('preview market cache serves a stale Pump.fun snapshot before reporting unavailable', async () => {
  const originalFetch = global.fetch;
  const originalNow = Date.now;
  cache.clear();
  let available = true;
  global.fetch = async target => {
    const url = String(target);
    if (url.startsWith(`${PUMP_API_URL}/coins?`)) {
      if (!available) return providerResponse({ detail: 'down' }, 503);
      return providerResponse([{ mint: 'StalePump123', name: 'Stale Pump', symbol: 'STALE', created_timestamp: 1000 }]);
    }
    throw new Error(`Unexpected provider request: ${url}`);
  };
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const first = await request(baseUrl, '/api/market/feed?kind=trending&chain=solana&scope=pump', originalFetch);
    assert.equal(first.status, 200);
    available = false;
    Date.now = () => originalNow() + 30000;
    const stale = await request(baseUrl, '/api/market/feed?kind=trending&chain=solana&scope=pump', originalFetch);
    assert.equal(stale.status, 200);
    assert.equal(stale.body.provider, 'Pump.fun');
    assert.equal(stale.body.stale, true);
    assert.match(stale.body.error, /HTTP 503/);
    assert.equal(stale.body.pairs[0].baseToken.symbol, 'STALE');
  } finally {
    Date.now = originalNow;
    global.fetch = originalFetch;
    cache.clear();
    await new Promise(resolve => server.close(resolve));
  }
});

test('preview Pump radar returns an explicit unavailable state after primary and fallback failure', async () => {
  const originalFetch = global.fetch;
  cache.clear();
  global.fetch = async target => {
    const url = String(target);
    if (url.startsWith(`${PUMP_API_URL}/coins?`)) return providerResponse({ detail: 'down' }, 503);
    if (url === `${GECKO_API_URL}/networks/solana/trending_pools?page=1`) return providerResponse({ detail: 'down' }, 503);
    throw new Error(`Unexpected provider request: ${url}`);
  };
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const response = await request(baseUrl, '/api/market/feed?kind=trending&chain=solana&scope=pump', originalFetch);
    assert.equal(response.status, 200);
    assert.equal(response.body.primary_provider, 'Pump.fun');
    assert.equal(response.body.stale, true);
    assert.match(response.body.error, /temporarily unavailable/);
    assert.deepEqual(response.body.pairs, []);
  } finally {
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});

test('preview graduation status only accepts Pump.fun complete coins', async () => {
  const originalFetch = global.fetch;
  const graduatedMint = 'GraduatedMint123';
  const pendingMint = 'PendingMint456';
  global.fetch = async target => {
    const url = String(target);
    if (url === `${PUMP_API_URL}/coins/${graduatedMint}`) {
      return providerResponse({ mint: graduatedMint, complete: true, raydium_pool: 'RaydiumPool789' });
    }
    if (url === `${PUMP_API_URL}/coins/${pendingMint}`) {
      return providerResponse({ mint: pendingMint, complete: false, raydium_pool: null });
    }
    throw new Error(`Unexpected provider request: ${url}`);
  };
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const response = await request(
      baseUrl,
      `/api/market/graduations?mints=${graduatedMint},${pendingMint},${graduatedMint}`,
      originalFetch,
    );
    assert.equal(response.status, 200);
    assert.equal(response.body.provider, 'Pump.fun');
    assert.equal(response.body.status, 'verified');
    assert.deepEqual(response.body.graduations.map(item => item.mint), [graduatedMint]);
    assert.equal(response.body.graduations[0].pool_address, 'RaydiumPool789');
    assert.match(response.body.graduations[0].observed_at, /^\d{4}-\d{2}-\d{2}T/);
  } finally {
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});

test('preview graduation status reports provider outage without inventing events', async () => {
  const originalFetch = global.fetch;
  global.fetch = async target => {
    if (String(target) === `${PUMP_API_URL}/coins/UnavailableMint999`) return providerResponse({ detail: 'down' }, 503);
    throw new Error(`Unexpected provider request: ${target}`);
  };
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const response = await request(baseUrl, '/api/market/graduations?mints=UnavailableMint999', originalFetch);
    assert.equal(response.status, 200);
    assert.equal(response.body.status, 'unavailable');
    assert.equal(response.body.graduations.length, 0);
    assert.match(response.body.error, /HTTP 503/);
  } finally {
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});

test('preview provider throttles use concise provider-aware warnings', async () => {
  const originalFetch = global.fetch;
  const originalConsoleWarn = console.warn;
  const originalConsoleError = console.error;
  const warnings = [];
  const errors = [];
  global.fetch = async () => providerResponse({ detail: 'rate limited' }, 429);
  console.warn = (...args) => warnings.push(args);
  console.error = (...args) => errors.push(args);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const response = await request(baseUrl, '/api/market/candles/solana/ThrottledPool123', originalFetch);
    assert.equal(response.status, 429);
    assert.match(response.body.detail, /HTTP 429/);
    assert.equal(errors.length, 0);
    assert.equal(warnings.length, 1);
    assert.match(warnings[0][0], /^\[preview-api\] GeckoTerminal rate limited \(HTTP 429\)\.$/);
  } finally {
    console.warn = originalConsoleWarn;
    console.error = originalConsoleError;
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});

test('preview market routes preserve throttling fallbacks and response bodies', async () => {
  const originalFetch = global.fetch;
  const originalConsoleWarn = console.warn;
  const originalConsoleError = console.error;
  const warnings = [];
  const errors = [];
  cache.clear();
  global.fetch = async target => {
    const url = String(target);
    if (url.startsWith(`${PUMP_API_URL}/coins?`)) return providerResponse({ detail: 'rate limited' }, 429);
    if (url === `${GECKO_API_URL}/networks/solana/trending_pools?page=1`) {
      return providerResponse({
        data: [{
          id: 'solana_ThrottledFallbackPool123',
          attributes: { address: 'ThrottledFallbackPool123', name: 'FALLBACK / SOL', reserve_in_usd: '2500' },
          relationships: {
            base_token: { data: { id: 'solana_fallback-token' } },
            quote_token: { data: { id: 'solana_So11111111111111111111111111111111111111112' } },
          },
        }],
      });
    }
    if (url === `${GECKO_API_URL}/networks/solana/pools/ThrottledPair123?include=base_token,quote_token,dex`) {
      return providerResponse({
        data: {
          id: 'solana_ThrottledPair123',
          attributes: { address: 'ThrottledPair123', name: 'PAIR / SOL', reserve_in_usd: '1000' },
          relationships: {
            base_token: { data: { id: 'solana_pair-token' } },
            quote_token: { data: { id: 'solana_So11111111111111111111111111111111111111112' } },
          },
        },
      });
    }
    return providerResponse({ detail: 'rate limited' }, 429);
  };
  console.warn = (...args) => warnings.push(args);
  console.error = (...args) => errors.push(args);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  const expectWarning = provider => {
    assert.equal(errors.length, 0);
    assert.deepEqual(warnings.map(args => args[0]), [`[preview-api] ${provider} rate limited (HTTP 429).`]);
    warnings.length = 0;
    errors.length = 0;
  };

  try {
    const feed = await request(baseUrl, '/api/market/feed?kind=trending&chain=solana&scope=pump', originalFetch);
    assert.equal(feed.status, 200);
    assert.equal(feed.body.provider, 'GeckoTerminal');
    assert.equal(feed.body.fallback_from, 'Pump.fun');
    assert.equal(feed.body.provider_status, 429);
    assert.equal(feed.body.provider_warning.rate_limited, true);
    assert.equal(feed.body.pairs[0].pairAddress, 'ThrottledFallbackPool123');
    expectWarning('Pump.fun');

    const candles = await request(baseUrl, '/api/market/candles/solana/ThrottledPool456', originalFetch);
    assert.equal(candles.status, 429);
    assert.match(candles.body.detail, /HTTP 429/);
    expectWarning('GeckoTerminal');

    const search = await request(baseUrl, '/api/market/search?q=throttled', originalFetch);
    assert.equal(search.status, 429);
    assert.match(search.body.detail, /HTTP 429/);
    expectWarning('DexScreener');

    const pair = await request(baseUrl, '/api/market/pair/solana/ThrottledPair123', originalFetch);
    assert.equal(pair.status, 200);
    assert.equal(pair.body.provider, 'GeckoTerminal');
    assert.equal(pair.body.provider_status, 429);
    assert.equal(pair.body.provider_warning.rate_limited, true);
    assert.equal(pair.body.pairs[0].pairAddress, 'ThrottledPair123');
    expectWarning('DexScreener');

    const assetsResponse = await request(baseUrl, '/api/market/assets', originalFetch);
    assert.equal(assetsResponse.status, 200);
    assert.equal(assetsResponse.body.assets.length, 3);
    assert.ok(assetsResponse.body.assets.every(asset => asset.status === 'provider_unavailable'));
    assert.ok(assetsResponse.body.assets.every(asset => asset.provider_status === 429 && asset.provider_warning.rate_limited));
    assert.equal(errors.length, 0);
    assert.deepEqual(
      warnings.map(args => args[0]),
      ['[preview-api] DexScreener rate limited (HTTP 429).'],
    );
    warnings.length = 0;
    errors.length = 0;

    const graduations = await request(baseUrl, '/api/market/graduations?mints=ThrottledMint789', originalFetch);
    assert.equal(graduations.status, 200);
    assert.equal(graduations.body.status, 'unavailable');
    assert.deepEqual(graduations.body.graduations, []);
    assert.match(graduations.body.error, /HTTP 429/);
    assert.equal(graduations.body.provider_status, 429);
    assert.equal(graduations.body.provider_warning.rate_limited, true);
    expectWarning('Pump.fun');
  } finally {
    console.warn = originalConsoleWarn;
    console.error = originalConsoleError;
    global.fetch = originalFetch;
    cache.clear();
    await new Promise(resolve => server.close(resolve));
  }
});

test('fee asset fallback throttles warn once per provider while keeping each asset response', async () => {
  const originalFetch = global.fetch;
  const originalConsoleWarn = console.warn;
  const originalConsoleError = console.error;
  const warnings = [];
  const errors = [];
  cache.clear();
  global.fetch = async target => {
    const url = String(target);
    if (url.includes('/token-pairs/v1/solana/')) return providerResponse([]);
    if (url.includes('/networks/solana/tokens/')) return providerResponse({ detail: 'rate limited' }, 429);
    throw new Error(`Unexpected provider request: ${url}`);
  };
  console.warn = (...args) => warnings.push(args);
  console.error = (...args) => errors.push(args);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;

  try {
    const response = await request(baseUrl, '/api/market/assets', originalFetch);
    assert.equal(response.status, 200);
    assert.equal(response.body.assets.length, 3);
    assert.ok(response.body.assets.every(asset => asset.status === 'awaiting_market'));
    assert.deepEqual(
      warnings.map(args => args[0]),
      ['[preview-api] GeckoTerminal rate limited (HTTP 429).'],
    );
    assert.equal(errors.length, 0);
  } finally {
    console.warn = originalConsoleWarn;
    console.error = originalConsoleError;
    global.fetch = originalFetch;
    cache.clear();
    await new Promise(resolve => server.close(resolve));
  }
});

test('fee asset throttle warnings cool down across refreshes and recover after expiry', async () => {
  const originalFetch = global.fetch;
  const originalConsoleWarn = console.warn;
  const originalConsoleError = console.error;
  const originalNow = Date.now;
  const warnings = [];
  const errors = [];
  cache.clear();
  assetThrottleWarningCooldown.clear();
  global.fetch = async target => {
    const url = String(target);
    if (url.includes('/token-pairs/v1/solana/')) return providerResponse([]);
    if (url.includes('/networks/solana/tokens/')) return providerResponse({ detail: 'rate limited' }, 429);
    throw new Error(`Unexpected provider request: ${url}`);
  };
  console.warn = (...args) => warnings.push(args);
  console.error = (...args) => errors.push(args);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const first = await request(baseUrl, '/api/market/assets', originalFetch);
    assert.equal(first.status, 200);
    assert.equal(warnings.length, 1);
    assert.equal(errors.length, 0);
    const firstAssetStates = first.body.assets.map(asset => ({
      id: asset.id,
      status: asset.status,
      provider: asset.provider,
      provider_status: asset.provider_status,
      provider_warning: asset.provider_warning,
    }));

    const second = await request(baseUrl, '/api/market/assets', originalFetch);
    assert.equal(second.status, 200);
    assert.equal(warnings.length, 1);
    assert.deepEqual(
      second.body.assets.map(asset => ({
        id: asset.id,
        status: asset.status,
        provider: asset.provider,
        provider_status: asset.provider_status,
        provider_warning: asset.provider_warning,
      })),
      firstAssetStates,
    );

    Date.now = () => originalNow() + ASSET_THROTTLE_WARNING_COOLDOWN_MS + 1;
    const recoveredWarning = await request(baseUrl, '/api/market/assets', originalFetch);
    assert.equal(recoveredWarning.status, 200);
    assert.equal(warnings.length, 2);
    assert.equal(errors.length, 0);
    assert.ok(recoveredWarning.body.assets.every(asset => asset.provider_status === 429));
  } finally {
    Date.now = originalNow;
    assetThrottleWarningCooldown.clear();
    console.warn = originalConsoleWarn;
    console.error = originalConsoleError;
    global.fetch = originalFetch;
    cache.clear();
    await new Promise(resolve => server.close(resolve));
  }
});

test('preview unexpected provider errors retain the actionable stack trace', async () => {
  const originalFetch = global.fetch;
  const originalConsoleWarn = console.warn;
  const originalConsoleError = console.error;
  const warnings = [];
  const errors = [];
  const failure = new Error('Unexpected provider failure');
  global.fetch = async () => { throw failure; };
  console.warn = (...args) => warnings.push(args);
  console.error = (...args) => errors.push(args);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const response = await request(baseUrl, '/api/market/candles/solana/UnexpectedPool123', originalFetch);
    assert.equal(response.status, 503);
    assert.match(response.body.detail, /Unexpected provider failure/);
    assert.equal(warnings.length, 0);
    assert.equal(errors.length, 1);
    assert.equal(errors[0][0], '[preview-api]');
    assert.match(errors[0][1].stack, /Unexpected provider failure/);
  } finally {
    console.warn = originalConsoleWarn;
    console.error = originalConsoleError;
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});

test('fee assets fall back to exact GeckoTerminal CA matches with prices and logos', async () => {
  const originalFetch = global.fetch;
  const mints = {
    fee: '49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump',
    feecat: 'AsX2abSJ2HqPqRxUbeYXE5R5ksrmUDz6BMGpg9mDpump',
    rfee: '2vZjg2w58k4urtdNWPnNHizuSxesLCoz5QqN9xxqNray',
  };
  const tokens = {
    [mints.fee]: { name: 'Feeless', symbol: 'FEE', price: '0.0000031', image: 'https://logo.test/fee.png', pool: 'FeePool123' },
    [mints.feecat]: { name: 'FEELESS CAT', symbol: 'FEECAT', price: '0.0000028', image: 'https://logo.test/feecat.png', pool: 'CatPool123' },
    [mints.rfee]: { name: 'RFEE', symbol: 'RFEE', price: '0.0000012', image: 'https://logo.test/rfee.png', pool: null, topPool: 'RfeeTop123' },
  };
  global.fetch = async target => {
    const url = String(target);
    const dexMatch = url.match(/\/token-pairs\/v1\/solana\/([^?]+)/);
    if (dexMatch) return providerResponse([]);
    const tokenMatch = url.match(/\/networks\/solana\/tokens\/([^/]+)$/);
    if (tokenMatch) {
      const token = tokens[tokenMatch[1]];
      return providerResponse({
        data: {
          attributes: { name: token.name, symbol: token.symbol, image_url: token.image, price_usd: token.price },
          relationships: token.topPool ? { top_pools: { data: [{ id: `solana_${token.topPool}` }] } } : undefined,
        },
      });
    }
    const poolsMatch = url.match(/\/networks\/solana\/tokens\/([^/]+)\/pools\?page=1$/);
    if (poolsMatch) {
      const mint = poolsMatch[1];
      const token = tokens[mint];
      return providerResponse({
        data: token.pool ? [{
          id: `solana_${token.pool}`,
          attributes: {
            address: token.pool,
            name: `${token.symbol} / SOL`,
            base_token_price_usd: token.price,
            reserve_in_usd: '1000',
          },
          relationships: {
            base_token: { data: { id: `solana_${mint}` } },
            quote_token: { data: { id: 'solana_So11111111111111111111111111111111111111112' } },
          },
        }] : [],
      });
    }
    throw new Error(`Unexpected provider request: ${url}`);
  };

  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const response = await request(baseUrl, '/api/market/assets', originalFetch);
    assert.equal(response.status, 200);
    const assets = Object.fromEntries(response.body.assets.map(asset => [asset.id, asset]));
    assert.equal(assets.fee.provider, 'GeckoTerminal');
    assert.equal(assets.fee.status, 'market_observed');
    assert.equal(assets.fee.pair.priceUsd, '0.0000031');
    assert.equal(assets.fee.imageUrl, 'https://logo.test/fee.png');
    assert.equal(assets.feecat.pair.baseToken.symbol, 'FEECAT');
    assert.equal(assets.feecat.pair.info.imageUrl, 'https://logo.test/feecat.png');
    assert.equal(assets.rfee.status, 'market_observed');
    assert.equal(assets.rfee.pair.priceUsd, '0.0000012');
    assert.equal(assets.rfee.pair.pairAddress, 'RfeeTop123');
    assert.equal(assets.rfee.imageUrl, 'https://logo.test/rfee.png');
  } finally {
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});

test('signed profiles enforce public privacy, social actions, flags, and chat cooldowns', async () => {
  const originalFetch = global.fetch;
  const first = Keypair.generate();
  const second = Keypair.generate();
  global.fetch = async () => providerResponse({});
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const { port } = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const firstProof = await proof(baseUrl, first, originalFetch);
    const saved = await post(baseUrl, '/api/profile/save', { ...firstProof, username: 'first_alpha', category: 'Builder', bio: 'Watching the curve.', isPrivate: false }, originalFetch);
    assert.equal(saved.status, 200);
    const firstMessage = await post(baseUrl, '/api/chat/signed-room', { ...firstProof, text: 'first alpha' }, originalFetch);
    assert.equal(firstMessage.status, 200);
    assert.equal(firstMessage.body.profile.username, 'first_alpha');
    const secondMessage = await post(baseUrl, '/api/chat/signed-room', { ...firstProof, text: 'second alpha' }, originalFetch);
    const thirdMessage = await post(baseUrl, '/api/chat/signed-room', { ...firstProof, text: 'third alpha' }, originalFetch);
    assert.equal(secondMessage.status, 200);
    assert.equal(thirdMessage.status, 200);
    const cooldown = await post(baseUrl, '/api/chat/signed-room', { ...firstProof, text: 'fourth alpha' }, originalFetch);
    assert.equal(cooldown.status, 429);
    assert.match(cooldown.body.detail, /cooldown/i);

    const secondProof = await proof(baseUrl, second, originalFetch);
    const liked = await post(baseUrl, `/api/chat/signed-room/${firstMessage.body.id}/like`, secondProof, originalFetch);
    assert.equal(liked.status, 200);
    assert.equal(liked.body.likeCount, 1);
    const reply = await post(baseUrl, `/api/chat/signed-room/${firstMessage.body.id}/reply`, { ...secondProof, text: 'replying with a receipt' }, originalFetch);
    assert.equal(reply.status, 200);
    assert.equal(reply.body.parentId, firstMessage.body.id);

    const flagged = await post(baseUrl, `/api/profile/${encodeURIComponent(first.publicKey.toString())}/flag`, { ...secondProof, targetChain: 'solana' }, originalFetch);
    assert.equal(flagged.status, 200);
    assert.equal(flagged.body.flagCount, 1);
    const publicProfile = await request(baseUrl, `/api/profile/${encodeURIComponent(first.publicKey.toString())}?chain=solana`, originalFetch);
    assert.equal(publicProfile.body.flagCount, 1);

    const privateSave = await post(baseUrl, '/api/profile/save', { ...firstProof, username: 'first_alpha', isPrivate: true }, originalFetch);
    assert.equal(privateSave.status, 200);
    const hiddenProfile = await request(baseUrl, `/api/profile/${encodeURIComponent(first.publicKey.toString())}?chain=solana`, originalFetch);
    assert.equal(hiddenProfile.body.hidden, true);
    assert.equal(hiddenProfile.body.flagCount, null);
    assert.equal(hiddenProfile.body.username, undefined);
    const hiddenMessages = await request(baseUrl, '/api/chat/signed-room', originalFetch);
    assert.equal(hiddenMessages.body.messages[0].profile.hidden, true);
    assert.equal(hiddenMessages.body.messages[0].profile.flagCount, null);
  } finally {
    global.fetch = originalFetch;
    await new Promise(resolve => server.close(resolve));
  }
});

test('paper Cat lifecycle survives a preview restart without persisting recovery keys', async () => {
  const stateDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'feeless-paper-state-'));
  const statePath = path.join(stateDirectory, 'paper-state.json');
  let preview;
  let restartedPreview;
  try {
    preview = await startPersistentPreview(statePath);
    const createdResponse = await post(preview.baseUrl, '/api/cats', {
      name: 'Durable Cat',
      ownerId: 'restart-owner',
      walletMode: 'assigned',
      coinPlan: 'create',
    }, global.fetch);
    assert.equal(createdResponse.status, 201);
    assert.equal(createdResponse.body.cat.mode, 'paper');
    assert.equal(createdResponse.body.cat.walletMode, 'assigned');
    assert.equal(createdResponse.body.cat.coinPlan, 'create');
    assert.equal(createdResponse.body.cat.recoveryKeyHash, undefined);
    assert.ok(createdResponse.body.recoveryKey);

    const confirmedResponse = await post(
      preview.baseUrl,
      `/api/cats/${createdResponse.body.cat.id}/action`,
      { action: 'confirm_recovery', recoveryKey: createdResponse.body.recoveryKey },
      global.fetch,
    );
    assert.equal(confirmedResponse.status, 200);
    assert.equal(confirmedResponse.body.cat.recovery.saved, true);

    const expiringResponse = await post(preview.baseUrl, '/api/cats', {
      name: 'Expiry Cat',
      ownerId: 'restart-owner',
    }, global.fetch);
    assert.equal(expiringResponse.status, 201);
    const stateBeforeRestart = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    assert.equal(stateBeforeRestart.version, 1);
    assert.equal(fs.statSync(statePath).mode & 0o777, 0o600);
    assert.ok(stateBeforeRestart.cats[0].recoveryKeyHash);
    assert.equal(JSON.stringify(stateBeforeRestart).includes(createdResponse.body.recoveryKey), false);
    const expiringRecord = stateBeforeRestart.cats.find(cat => cat.id === expiringResponse.body.cat.id);
    expiringRecord.recoveryExpiresAt = new Date(Date.now() - 1000).toISOString();
    fs.writeFileSync(statePath, JSON.stringify(stateBeforeRestart));

    await stopPersistentPreview(preview.child);
    preview = null;
    restartedPreview = await startPersistentPreview(statePath);

    const restoredResponse = await request(restartedPreview.baseUrl, '/api/cats?ownerId=restart-owner', global.fetch);
    assert.equal(restoredResponse.status, 200);
    const restored = Object.fromEntries(restoredResponse.body.cats.map(cat => [cat.name, cat]));
    assert.equal(restored['Durable Cat'].mode, 'paper');
    assert.equal(restored['Durable Cat'].walletMode, 'assigned');
    assert.equal(restored['Durable Cat'].coinPlan, 'create');
    assert.equal(restored['Durable Cat'].recovery.saved, true);
    assert.equal(restored['Durable Cat'].recovery.funded, false);
    assert.equal(restored['Expiry Cat'].status, 'expired');
    assert.ok(restored['Expiry Cat'].recovery.expiredAt);
    assert.equal(restoredResponse.body.cats.some(cat => cat.recoveryKeyHash), false);

    const blockedResponse = await post(
      restartedPreview.baseUrl,
      `/api/cats/${expiringResponse.body.cat.id}/action`,
      { action: 'start' },
      global.fetch,
    );
    assert.equal(blockedResponse.status, 409);
    const activityResponse = await request(
      restartedPreview.baseUrl,
      `/api/cats/activity?catId=${encodeURIComponent(expiringResponse.body.cat.id)}`,
      global.fetch,
    );
    assert.equal(activityResponse.status, 200);
    assert.ok(activityResponse.body.events.some(event => event.type === 'EXPIRED'));
  } finally {
    if (preview) await stopPersistentPreview(preview.child);
    if (restartedPreview) await stopPersistentPreview(restartedPreview.child);
    fs.rmSync(stateDirectory, { recursive: true, force: true });
  }
});