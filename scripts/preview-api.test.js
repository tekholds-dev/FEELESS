const assert = require('node:assert/strict');
const nodeCrypto = require('node:crypto');
const { once } = require('node:events');
const test = require('node:test');
const { Keypair } = require('@solana/web3.js');

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

async function proof(baseUrl, keypair, fetchImpl) {
  const address = keypair.publicKey.toString();
  const challenge = await post(baseUrl, '/api/profile/challenge', { address, chain: 'solana' }, fetchImpl);
  assert.equal(challenge.status, 200);
  return { address, chain: 'solana', message: challenge.body.message, signature: signSolana(keypair, challenge.body.message) };
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