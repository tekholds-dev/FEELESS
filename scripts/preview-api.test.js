const assert = require('node:assert/strict');
const { once } = require('node:events');
const test = require('node:test');

const DEX_API_URL = 'http://dex.test';
const GECKO_API_URL = 'http://gecko.test/api/v2';
const POOL_ADDRESS = 'PoolAddress123';

process.env.DEX_API_URL = DEX_API_URL;
process.env.GECKO_API_URL = GECKO_API_URL;

const { server } = require('./preview-api');

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