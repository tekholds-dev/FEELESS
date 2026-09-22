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
    if (url.startsWith(`${GECKO_API_URL}/networks/solana/pools/${POOL_ADDRESS}/ohlcv/`)) {
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

    for (const interval of ['5m', '15m', '1h', '4h', '1d']) {
      const candles = await request(
        baseUrl,
        `/api/market/candles/${discoveredPool.chainId}/${discoveredPool.pairAddress}?interval=${interval}`,
        originalFetch,
      );
      assert.equal(candles.status, 200, `${interval} candle request should succeed`);
      assert.equal(candles.body.provider, 'GeckoTerminal', `${interval} candle provider should be preserved`);
      assert.deepEqual(candles.body.candles.map(row => row[0]), [100, 200, 300], `${interval} candles should be ordered`);
      assert.equal(candles.body.candles[1][5], 999, `${interval} duplicate timestamps should keep the last row`);
    }

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