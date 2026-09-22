const http = require('http');
const { URL } = require('url');

const PORT = Number(process.env.API_PORT || 5001);
const DEX_API = process.env.DEX_API_URL || 'https://api.dexscreener.com';
const GECKO_API = process.env.GECKO_API_URL || 'https://api.geckoterminal.com/api/v2';
const DEX_SITE = process.env.DEX_SITE_URL || 'https://dexscreener.com';
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
const rooms = new Map();
const orders = new Map();

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
  const hit = cache.get(url);
  if (hit && Date.now() - hit.at < ttl) return hit.value;
  if (pendingRequests.has(url)) return pendingRequests.get(url);
  const request = (async () => {
    const response = await fetch(url, { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error(`Provider returned HTTP ${response.status}.`);
    const value = await response.json();
    cache.set(url, { at: Date.now(), value });
    return value;
  })();
  pendingRequests.set(url, request);
  try { return await request; }
  finally { pendingRequests.delete(url); }
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
  return {
    chainId: network === 'solana' ? 'solana' : network,
    network,
    pairAddress: attrs.address || item?.id?.split('_').slice(1).join('_'),
    dexId: relationships.dex?.data?.id || 'unknown',
    url: `${DEX_SITE}/${network === 'solana' ? 'solana' : network}/${attrs.address || ''}`,
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

function geckoResult(data, kind) {
  const pairs = (data?.data || []).map(pairFromGecko).filter(pair => pair.pairAddress);
  return {
    provider: 'GeckoTerminal',
    fetched_at: new Date().toISOString(),
    stale: false,
    label: kind === 'new' ? 'New pools' : 'Trending pools',
    pairs,
    page: 1,
  };
}

async function geckoFeed(kind, page = 1) {
  const endpoint = kind === 'new' ? 'new_pools' : 'trending_pools';
  const data = await getJson(`${GECKO_API}/networks/solana/${endpoint}?page=${page}`, 30000);
  return geckoResult(data, kind);
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
  const data = await getJson(
    `${GECKO_API}/networks/${networks[chain]}/pools/${encodeURIComponent(address)}/ohlcv/${timeframe}?aggregate=${aggregate}&limit=100&currency=usd&token=base`,
    90000,
  );
  const rows = data?.data?.attributes?.ohlcv_list || [];
  const candles = [...new Map(rows
    .filter(row => Array.isArray(row) && row.length >= 6 && Number.isFinite(row[0]))
    .map(row => [row[0], row])).values()]
    .sort((a, b) => a[0] - b[0]);
  return {
    provider: 'GeckoTerminal',
    fetched_at: new Date().toISOString(),
    stale: false,
    candles,
  };
}

async function dexBoostFeed(kind, page = 1, chain = 'solana') {
  if (String(page) !== '1') throw new Error('Fast discovery is available on the first page only.');
  const index = await getJson(`${DEX_API}/token-boosts/${kind === 'new' ? 'latest' : 'top'}/v1`, 20000);
  const candidates = (Array.isArray(index) ? index : [])
    .filter(item => (chain === 'all' || item?.chainId === chain) && item?.tokenAddress);
  const addresses = [...new Set(candidates.map(item => item.tokenAddress))].slice(0, 30);
  if (!addresses.length) throw new Error('Fast discovery returned no indexed tokens.');
  const payload = await getJson(`${DEX_API}/latest/dex/tokens/${addresses.join(',')}`, 20000);
  const rank = new Map(candidates.map((item, index) => [`${item.chainId}:${item.tokenAddress}`, index]));
  const bestByToken = new Map();
  for (const pair of payload?.pairs || []) {
    if (chain !== 'all' && pair?.chainId !== chain) continue;
    const key = `${pair.chainId}:${pair.baseToken?.address}`;
    const liquidity = Number(pair.liquidity?.usd || 0);
    if (!bestByToken.has(key) || liquidity > Number(bestByToken.get(key).liquidity?.usd || 0)) bestByToken.set(key, pair);
  }
  let pairs = [...bestByToken.values()];
  if (kind === 'new') pairs = pairs.filter(pair => {
    const age = Date.now() - Number(pair.pairCreatedAt || 0);
    return age >= 0 && age <= 14 * 24 * 60 * 60 * 1000 && Number(pair.priceChange?.h24 || 0) <= -5;
  });
  pairs.sort((a, b) => (rank.get(`${a.chainId}:${a.baseToken?.address}`) ?? candidates.length)
    - (rank.get(`${b.chainId}:${b.baseToken?.address}`) ?? candidates.length)
    || Number(b.liquidity?.usd || 0) - Number(a.liquidity?.usd || 0));
  if (!pairs.length) throw new Error('Fast discovery returned no qualifying pools.');
  return {
    provider: 'DexScreener',
    fetched_at: new Date().toISOString(),
    stale: false,
    label: kind === 'new' ? 'New pools · deals ≥5% 24h drawdown' : 'Boosted discovery',
    pairs,
    page: 1,
  };
}

async function dexSearch(query) {
  const data = await getJson(`${DEX_API}/latest/dex/search?q=${encodeURIComponent(query)}`, 15000);
  return {
    provider: 'DexScreener',
    fetched_at: new Date().toISOString(),
    stale: false,
    label: 'Search results',
    pairs: data?.pairs || [],
    page: 1,
  };
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
  const result = await Promise.all(Object.entries(MINTS).map(async ([id, mint]) => {
    try {
      const rows = await getJson(`${DEX_API}/token-pairs/v1/solana/${mint}`, 60000);
      const pair = (Array.isArray(rows) ? rows : [])
        .filter(item => item?.baseToken?.address === mint)
        .sort((a, b) => Number(b?.liquidity?.usd || 0) - Number(a?.liquidity?.usd || 0))[0] || null;
      return {
        id,
        label: id.toUpperCase(),
        mint,
        chain: 'solana',
        pair,
        status: pair?.priceUsd ? 'market_observed' : 'awaiting_market',
        provider: 'DexScreener',
        fetched_at: new Date().toISOString(),
        identity: 'Owner-supplied contract; exact provider match. Not a security endorsement.',
      };
    } catch (error) {
      return {
        id,
        label: id.toUpperCase(),
        mint,
        chain: 'solana',
        pair: null,
        status: 'provider_unavailable',
        error: publicError(error),
        provider: 'DexScreener',
        fetched_at: new Date().toISOString(),
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
    let result;
    try { result = await dexBoostFeed(kind, url.searchParams.get('page') || 1, chain); }
    catch { result = await geckoFeed(kind, url.searchParams.get('page') || 1); }
    return json(res, 200, result);
  }
  const candleMatch = url.pathname.match(/^\/api\/market\/candles\/([^/]+)\/([^/]+)$/);
  if (req.method === 'GET' && candleMatch) {
    return json(res, 200, await geckoCandles(candleMatch[1], candleMatch[2], url.searchParams.get('interval') || '1h'));
  }
  if (req.method === 'GET' && url.pathname === '/api/market/search') return json(res, 200, await dexSearch(url.searchParams.get('q') || ''));
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
  const chatMatch = url.pathname.match(/^\/api\/chat\/([^/]+)(\/online)?$/);
  if (chatMatch) {
    const room = decodeURIComponent(chatMatch[1]);
    if (chatMatch[2]) return json(res, 200, { room, online: new Set(roomMessages(room).map(message => message.username)).size });
    if (req.method === 'GET') return json(res, 200, { room, messages: roomMessages(room) });
    if (req.method === 'POST') {
      const body = await requestBody(req);
      const message = { id: crypto.randomUUID(), room, username: String(body.username || 'degen').slice(0, 40), text: String(body.text || '').trim().slice(0, 1000), tokens: null, ts: Date.now() };
      if (!message.text) return json(res, 400, { detail: 'Message and username cannot be blank' });
      roomMessages(room).push(message);
      return json(res, 200, message);
    }
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
    console.error('[preview-api]', error);
    json(res, error.statusCode || 503, { detail: publicError(error) });
  }
});

function startServer() {
  server.listen(PORT, '127.0.0.1', () => {
    console.log(`[preview-api] listening on http://127.0.0.1:${PORT} with live public market providers`);
    Promise.allSettled([dexBoostFeed('trending'), dexBoostFeed('new')])
      .then(() => console.log('[preview-api] DexScreener radar cache warmed'))
      .catch(() => {});
  });
}

if (require.main === module) startServer();

module.exports = { geckoCandles, route, server, startServer };