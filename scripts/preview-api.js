const http = require('http');
const { URL } = require('url');

const PORT = Number(process.env.API_PORT || 5001);
const DEX_API = process.env.DEX_API_URL || 'https://api.dexscreener.com';
const GECKO_API = process.env.GECKO_API_URL || 'https://api.geckoterminal.com/api/v2';
const DEX_SITE = process.env.DEX_SITE_URL || 'https://dexscreener.com';
const JUPITER_API = process.env.JUPITER_API_URL || 'https://lite-api.jup.ag/swap/v1';
const MINTS = {
  fee: process.env.FEE_MINT || '49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump',
  feecat: process.env.FEECAT_MINT || 'AsX2abSJ2HqPqRxUbeYXE5R5ksrmUDz6BMGpg9mDpump',
  rfee: process.env.RFEE_MINT || '2vZjg2w58k4urtdNWPnNHizuSxesLCoz5QqN9xxqNray',
};

const cache = new Map();
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

async function getJson(url, ttl = 30000) {
  const hit = cache.get(url);
  if (hit && Date.now() - hit.at < ttl) return hit.value;
  const response = await fetch(url, { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`Provider returned HTTP ${response.status}.`);
  const value = await response.json();
  cache.set(url, { at: Date.now(), value });
  return value;
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
    const result = await geckoFeed(url.searchParams.get('kind') === 'new' ? 'new' : 'trending', url.searchParams.get('page') || 1);
    return json(res, 200, result);
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
    return json(res, 200, { provider: 'Jupiter', network: 'solana-mainnet', signing: 'Phantom', configured: false, fee_back_status: 'PLANNED', eligible_fee_rules: 'Not activated', supported_execution_chains: ['solana'], detail: 'Live market discovery is enabled. Trading execution needs backend Jupiter/RPC configuration.' });
  }
  const mintMatch = url.pathname.match(/^\/api\/trading\/mint\/([^/]+)$/);
  if (req.method === 'GET' && mintMatch) {
    const mint = decodeURIComponent(mintMatch[1]);
    const symbol = Object.entries(MINTS).find(([, value]) => value === mint)?.[0] || 'TOKEN';
    return json(res, 200, { mint, decimals: 9, symbol, supply: null, mint_authority: null, freeze_authority: null, source: 'Preview metadata boundary · supply verification unavailable' });
  }
  const historyMatch = url.pathname.match(/^\/api\/trading\/history\/([^/]+)$/);
  if (req.method === 'GET' && historyMatch) return json(res, 200, { transactions: [], eligible_fees_usd: null, distributions: [], fee_back_status: 'PLANNED' });
  const balanceMatch = url.pathname.match(/^\/api\/trading\/balance\/([^/]+)$/);
  if (req.method === 'GET' && balanceMatch) return json(res, 200, { lamports: null, slot: null, source: 'Preview metadata boundary · balance unavailable' });
  if (req.method === 'POST' && url.pathname === '/api/trading/quote') {
    const body = await requestBody(req);
    const inputMint = String(body.input_mint || '');
    const outputMint = String(body.output_mint || '');
    const decimals = inputMint === 'So11111111111111111111111111111111111111112' ? 9 : 6;
    const amount = Number(body.amount);
    if (!inputMint || !outputMint || inputMint === outputMint || !Number.isFinite(amount) || amount <= 0) return json(res, 400, { detail: 'Choose two different assets and enter a valid amount.' });
    const response = await fetch(`${JUPITER_API}/quote?inputMint=${encodeURIComponent(inputMint)}&outputMint=${encodeURIComponent(outputMint)}&amount=${Math.round(amount * (10 ** decimals))}&slippageBps=${Number(body.slippage_bps) || 50}`, { signal: AbortSignal.timeout(15000) });
    const quote = await response.json();
    if (!response.ok || quote.error) return json(res, 503, { detail: quote.error || 'Jupiter route unavailable for this pair.' });
    const orderId = crypto.randomUUID();
    orders.set(orderId, { wallet: body.wallet || null, quote, expires_at: Date.now() / 1000 + 45 });
    return json(res, 200, {
      order_id: orderId,
      created_at: new Date().toISOString(),
      expires_at: Date.now() / 1000 + 45,
      input_metadata: { mint: inputMint, decimals, symbol: inputMint === 'So11111111111111111111111111111111111111112' ? 'SOL' : 'TOKEN' },
      output_metadata: { mint: outputMint, decimals: 6, symbol: 'TOKEN' },
      quote: { ...quote, router: 'Jupiter', transaction: null },
      fee_back: { status: 'PLANNED', eligible_usd: null, distribution: null },
    });
  }
  if (req.method === 'GET' && url.pathname.startsWith('/api/trading/')) return json(res, 503, { detail: 'Trading execution is not configured in this preview. Connect Phantom after a Jupiter/RPC backend is configured.' });
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
    json(res, 503, { detail: publicError(error) });
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[preview-api] listening on http://127.0.0.1:${PORT} with live public market providers`);
});