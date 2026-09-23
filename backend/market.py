"""Cached, provider-labelled public market data. No trading or custody."""
import asyncio
import hashlib
import json
import os
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

NETWORKS = {'solana': 'solana', 'ethereum': 'eth', 'base': 'base', 'bsc': 'bsc',
            'arbitrum': 'arbitrum', 'avalanche': 'avax', 'polygon': 'polygon_pos', 'sui': 'sui'}
REVERSE_NETWORKS = {v: k for k, v in NETWORKS.items()}
SUPPORTED_CHAINS = tuple(NETWORKS)
DEFAULT_MINTS = {
    'FEE': '49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump',
    'FEECAT': 'AsX2abSJ2HqPqRxUbeYXE5R5ksrmUDz6BMGpg9mDpump',
    'RFEE': '2vZjg2w58k4urtdNWPnNHizuSxesLCozQ5Pq9xxqNray',
}
MARKET_CACHE_RETENTION = timedelta(days=14)
NEW_POOL_DEAL_PERCENT = 5
PROVIDER_COVERAGE = {
    'Pump.fun': {
        'discovery': 'Pump.fun public coin index for Solana launchpad coverage',
        'snapshot': 'Pump.fun coin metadata snapshots',
        'candles': 'Not supplied; GeckoTerminal remains the candle provider',
        'liquidity': 'Only reported when Pump.fun supplies a direct liquidity field',
        'graduation': 'Pump.fun complete=true coin status',
        'stream': 'Polling snapshot; no websocket or trade stream',
    },
    'DexScreener': {
        'discovery': 'Boosted token and pair discovery across supported chains',
        'snapshot': 'DexScreener pair snapshots',
        'candles': 'Not supplied by this adapter',
        'liquidity': 'Pair liquidity snapshot',
        'graduation': 'Not established by this provider',
        'stream': 'Polling snapshot; no websocket or trade stream',
    },
    'GeckoTerminal': {
        'discovery': 'Public indexed pools across supported chains',
        'snapshot': 'Pool price, volume, and reserve snapshots',
        'candles': 'OHLCV pool candles',
        'liquidity': 'Pool reserve snapshot',
        'graduation': 'Not established by this provider',
        'stream': 'Polling snapshot; no websocket or trade stream',
    },
    'Public providers': {
        'discovery': 'No provider response available',
        'snapshot': 'Unavailable',
        'candles': 'Not evaluated',
        'liquidity': 'Unavailable',
        'graduation': 'Not established',
        'stream': 'No stream',
    },
}
PROVIDER_LABELS = {
    'Pump.fun': 'Pump.fun public coin index',
    'DexScreener': 'DexScreener boosted discovery',
    'GeckoTerminal': 'GeckoTerminal public pool index',
}
PROVIDER_URLS = {
    'Pump.fun': 'https://pump.fun',
    'DexScreener': 'https://dexscreener.com',
    'GeckoTerminal': 'https://www.geckoterminal.com',
}


def safe_float(value, default=0.0):
    try:
        result = float(value)
        return result if result == result else default
    except (TypeError, ValueError):
        return default


def is_new_pool_deal(pair, now_ms=None):
    """Return whether a provider-indexed pool is recent and down at least 5%."""
    created = safe_float(pair.get('pairCreatedAt')) if pair else 0
    change = safe_float((pair.get('priceChange') or {}).get('h24')) if pair else 0
    now_ms = now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp() * 1000
    age_ms = now_ms - created
    return (
        created > 0
        and age_ms >= 0
        and age_ms <= MARKET_CACHE_RETENTION.total_seconds() * 1000
        and change <= -NEW_POOL_DEAL_PERCENT
    )


class MarketResult(BaseModel):
    provider: str
    primary_provider: str | None = None
    fetched_at: str
    stale: bool = False
    error: str | None = None
    fallback_from: str | None = None
    fallback_reason: str | None = None
    source_label: str | None = None
    coverage: dict[str, str] = Field(default_factory=dict)
    stream: bool = False
    label: str = ''
    source_url: str | None = None
    pairs: list[dict[str, Any]] = Field(default_factory=list)
    page: int = 1


class GraduationResult(BaseModel):
    provider: str
    primary_provider: str | None = None
    source_url: str
    source_label: str
    fetched_at: str
    stale: bool = False
    error: str | None = None
    coverage: dict[str, str] = Field(default_factory=dict)
    stream: bool = False
    status: Literal['verified', 'no_verified_events', 'unavailable'] = 'no_verified_events'
    graduations: list[dict[str, Any]] = Field(default_factory=list)


class CandleResult(BaseModel):
    provider: str
    primary_provider: str | None = None
    fetched_at: str
    stale: bool = False
    error: str | None = None
    source_label: str | None = None
    coverage: dict[str, str] = Field(default_factory=dict)
    stream: bool = False
    candles: list[list[float]]


def provider_meta(provider, fetched_at, stale=False, error=None, primary_provider=None, **extra):
    return {
        'provider': provider,
        'primary_provider': primary_provider or provider,
        'fetched_at': fetched_at,
        'stale': stale,
        'error': error,
        'source_label': PROVIDER_LABELS.get(provider, f'{provider} public market data'),
        'coverage': PROVIDER_COVERAGE.get(provider, {}),
        'stream': False,
        **extra,
    }


def normalise_pools(payload):
    included = {item['id']: item.get('attributes', {}) for item in payload.get('included', [])}
    pairs = []
    for item in payload.get('data', []):
        a = item.get('attributes', {})
        rel = item.get('relationships', {})
        network = item['id'].split('_', 1)[0]
        chain = REVERSE_NETWORKS.get(network, network)
        base_id = rel.get('base_token', {}).get('data', {}).get('id', '')
        quote_id = rel.get('quote_token', {}).get('data', {}).get('id', '')
        base, quote = included.get(base_id, {}), included.get(quote_id, {})
        created = a.get('pool_created_at')
        image_url = base.get('image_url') or a.get('image_url')
        creator = base.get('creator') or base.get('creator_profile') or a.get('creator') or a.get('creator_profile')
        info = {
            'imageUrl': image_url,
            'websites': base.get('websites') or a.get('websites') or [],
            'socials': base.get('socials') or a.get('socials') or [],
        }
        if creator:
            info['creator'] = creator
        pairs.append({
            'chainId': chain, 'network': network, 'pairAddress': a['address'],
            'dexId': rel.get('dex', {}).get('data', {}).get('id', 'unknown'),
            'url': f"{os.getenv('DEX_SITE_URL', 'https://dexscreener.com')}/{chain}/{a['address']}",
            'baseToken': {'address': base.get('address', base_id.split('_', 1)[-1]),
                          'name': base.get('name', a.get('name', 'Unknown')),
                          'symbol': base.get('symbol', a.get('name', '?').split(' / ')[0])},
            'quoteToken': {'address': quote.get('address'), 'symbol': quote.get('symbol')},
            'priceUsd': a.get('base_token_price_usd'),
            'priceChange': a.get('price_change_percentage', {}),
            'liquidity': {'usd': a.get('reserve_in_usd')}, 'volume': a.get('volume_usd', {}),
            'marketCap': a.get('market_cap_usd'), 'fdv': a.get('fdv_usd'),
            'txns': a.get('transactions', {}),
            'pairCreatedAt': int(datetime.fromisoformat(created.replace('Z', '+00:00')).timestamp() * 1000) if created else None,
            'info': info,
        })
    return pairs


def normalise_pump_coins(payload, kind='trending'):
    """Map Pump.fun coin-index fields into the shared market contract.

    Fields are copied only when Pump.fun reports them directly. In particular,
    virtual reserves are not relabelled as USD liquidity and market cap is not
    converted into a synthetic token price.
    """
    coins = payload if isinstance(payload, list) else (
        payload.get('coins') or payload.get('data') or []
        if isinstance(payload, dict) else []
    )
    pairs = []
    for coin in coins:
        if not isinstance(coin, dict):
            continue
        mint = coin.get('mint') or coin.get('address')
        if not isinstance(mint, str) or not mint.isalnum():
            continue
        created = safe_float(coin.get('created_timestamp') or coin.get('createdAt') or coin.get('created_at'))
        if created and created < 1_000_000_000_000:
            created *= 1000
        change = coin.get('priceChange') if isinstance(coin.get('priceChange'), dict) else (
            coin.get('price_change') if isinstance(coin.get('price_change'), dict) else {}
        )
        if not change:
            for source, key in [('price_change_5m', 'm5'), ('price_change_1h', 'h1'), ('price_change_24h', 'h24')]:
                if coin.get(source) is not None:
                    change[key] = coin[source]
        volume = coin.get('volume') if isinstance(coin.get('volume'), dict) else (
            coin.get('volume_usd') if isinstance(coin.get('volume_usd'), dict) else {}
        )
        if not volume and coin.get('volume_24h') is not None:
            volume = {'h24': coin.get('volume_24h')}
        liquidity = coin.get('liquidity') if isinstance(coin.get('liquidity'), dict) else {}
        if not liquidity and coin.get('liquidity_usd') is not None:
            liquidity = {'usd': coin.get('liquidity_usd')}
        pool_address = coin.get('raydium_pool') or coin.get('pool_address') or mint
        pair = {
            'chainId': 'solana',
            'network': 'solana',
            'pairAddress': pool_address,
            'dexId': 'pump.fun',
            'url': f'https://pump.fun/coin/{mint}',
            'baseToken': {
                'address': mint,
                'name': coin.get('name') or 'Unknown',
                'symbol': coin.get('symbol') or '?',
            },
            'quoteToken': {'symbol': 'SOL'},
            'priceUsd': coin.get('price_usd', coin.get('usd_price')),
            'priceChange': change,
            'liquidity': liquidity,
            'volume': volume,
            'marketCap': coin.get('usd_market_cap', coin.get('market_cap_usd')),
            'fdv': coin.get('fdv_usd', coin.get('fdv')),
            'txns': coin.get('transactions') if isinstance(coin.get('transactions'), dict) else {},
            'pairCreatedAt': int(created) if created else None,
            'info': {
                'imageUrl': coin.get('image_uri') or coin.get('image_url'),
                'websites': [coin['website']] if coin.get('website') else [],
                'socials': [
                    {'type': 'twitter', 'url': coin['twitter']} if coin.get('twitter') else None,
                    {'type': 'telegram', 'url': coin['telegram']} if coin.get('telegram') else None,
                ],
            },
            'marketKind': 'launchpad-token',
            'marketStage': kind,
            'launchpadId': 'pump',
        }
        pair['info']['socials'] = [social for social in pair['info']['socials'] if social]
        if coin.get('complete') is True:
            pair['graduation'] = {
                'status': 'graduated',
                'pool_address': coin.get('raydium_pool') or coin.get('pool_address'),
                'source': 'Pump.fun',
            }
        pairs.append(pair)
    return pairs


def create_market_router(db, intelligence=None):
    router = APIRouter(prefix='/api/market')
    locks = defaultdict(asyncio.Lock)
    requests = defaultdict(deque)
    cooldown = {}
    bases = {
        'DexScreener': os.getenv('DEX_API_URL', 'https://api.dexscreener.com'),
        'GeckoTerminal': os.getenv('GECKO_API_URL', 'https://api.geckoterminal.com/api/v2'),
        'Pump.fun': os.getenv('PUMP_API_URL', 'https://frontend-api-v3.pump.fun'),
    }
    gecko_api_key = os.getenv('GECKO_API_KEY') or os.getenv('COINGECKO_API_KEY')

    async def cached(provider, path, params=None, ttl=60):
        params = params or {}
        key = hashlib.sha256(json.dumps([provider, path, params], sort_keys=True).encode()).hexdigest()
        async with locks[key]:
            hit = await db.market_cache.find_one({'key': key}, {'_id': 0})
            now = datetime.now(timezone.utc)
            if hit:
                fetched_at = datetime.fromisoformat(hit['fetched_at'])
                if now - fetched_at > MARKET_CACHE_RETENTION:
                    await db.market_cache.delete_one({'key': key})
                    hit = None
            if hit and (now - datetime.fromisoformat(hit['fetched_at'])).total_seconds() < ttl:
                return hit['data'], provider_meta(provider, hit['fetched_at'])
            error = None
            queue = requests[provider]
            while queue and monotonic() - queue[0] > 60:
                queue.popleft()
            limit = 9 if provider == 'GeckoTerminal' else 45
            if monotonic() < cooldown.get(key, 0) or len(queue) >= limit:
                error = 'Provider refresh limit reached. Try again in a minute.'
            else:
                queue.append(monotonic())
                try:
                    async with httpx.AsyncClient(timeout=12) as http:
                        headers = {'Accept': 'application/json;version=20230203'}
                        if provider == 'GeckoTerminal' and gecko_api_key:
                            headers['x-cg-pro-api-key'] = gecko_api_key
                        res = await http.get(bases[provider] + path, params=params, headers=headers)
                        res.raise_for_status()
                        data = res.json()
                    fetched = now.isoformat()
                    await db.market_cache.update_one({'key': key}, {'$set': {
                        'data': data, 'fetched_at': fetched, 'provider': provider}}, upsert=True)
                    return data, provider_meta(provider, fetched)
                except (httpx.HTTPError, ValueError):
                    cooldown[key] = monotonic() + 45
                    error = f'{provider} is temporarily unavailable.'
            if hit:
                return hit['data'], provider_meta(provider, hit['fetched_at'], stale=True, error=error)
            raise HTTPException(503, detail=error)

    async def pump_feed(kind, page=1):
        if page != 1:
            raise HTTPException(503, 'Pump.fun discovery is available on the first page only.')
        sort = 'created_timestamp' if kind == 'new' else 'market_cap'
        data, meta = await cached(
            'Pump.fun',
            '/coins',
            {'offset': 0, 'limit': 50, 'sort': sort, 'order': 'DESC', 'includeNsfw': 'false'},
            ttl=20,
        )
        pairs = normalise_pump_coins(data, kind)
        if not pairs:
            raise HTTPException(503, 'Pump.fun returned no indexed coins.')
        pairs.sort(key=lambda pair: pair.get('pairCreatedAt') or 0, reverse=kind == 'new')
        return pairs, {
            **meta,
            'source_label': 'Pump.fun public coin index · launchpad coverage',
            'coverage': PROVIDER_COVERAGE['Pump.fun'],
        }

    async def graduation_status(mints):
        """Use Pump.fun's completion flag; market indexes cannot prove graduation."""
        unique_mints = list(dict.fromkeys(
            mint for mint in mints
            if isinstance(mint, str) and mint.isalnum() and len(mint) <= 64
        ))
        observed_at = datetime.now(timezone.utc).isoformat()
        if not unique_mints:
            return GraduationResult(
                provider='Pump.fun',
                source_url='https://pump.fun',
                source_label='Pump.fun public coin status · complete=true',
                fetched_at=observed_at,
            )

        async def read_mint(mint):
            try:
                data, meta = await cached('Pump.fun', f'/coins/{mint}', ttl=60)
                return mint, data, meta, None
            except HTTPException as exc:
                return mint, None, {}, str(exc.detail)

        limiter = asyncio.Semaphore(2)

        async def limited_read(mint):
            async with limiter:
                return await read_mint(mint)

        results = await asyncio.gather(*(limited_read(mint) for mint in unique_mints))
        graduations = []
        errors = []
        fetched_values = []
        stale = False
        for mint, data, meta, error in results:
            if error:
                errors.append(error)
                continue
            fetched_values.append(meta.get('fetched_at'))
            stale = stale or meta.get('stale', False)
            if data.get('complete') is True:
                graduations.append({
                    'mint': mint,
                    'status': 'graduated',
                    'pool_address': data.get('raydium_pool') or data.get('pool_address'),
                    'graduated_at': data.get('graduation_timestamp') or data.get('completion_timestamp'),
                    'observed_at': meta.get('fetched_at') or observed_at,
                    'source': 'Pump.fun',
                    'source_url': 'https://pump.fun',
                })

        return GraduationResult(
            provider='Pump.fun',
            primary_provider='Pump.fun',
            source_url='https://pump.fun',
            source_label='Pump.fun public coin status · complete=true',
            fetched_at=max(fetched_values or [observed_at]),
            stale=stale,
            error='; '.join(dict.fromkeys(errors)) if errors else None,
            coverage=PROVIDER_COVERAGE['Pump.fun'],
            status='verified' if graduations else ('unavailable' if errors and not fetched_values else 'no_verified_events'),
            graduations=graduations,
        )

    @router.get('/feed', response_model=MarketResult)
    async def feed(kind: Literal['trending', 'new'] = 'trending',
                   chain: str = 'solana', page: int = Query(1, ge=1, le=10),
                   scope: str | None = Query(None, pattern=r'^[a-z0-9-]{1,30}$')):
        if chain != 'all' and chain not in NETWORKS:
            raise HTTPException(400, 'Unsupported chain')
        fallback_reason = None
        primary_provider = 'Pump.fun' if scope == 'pump' else 'DexScreener'
        try:
            if scope == 'pump' and chain == 'solana':
                pairs, meta = await pump_feed(kind, page)
            elif scope == 'pump':
                fallback_reason = 'Pump.fun coverage is limited to Solana; using public pool discovery fallback.'
                pairs, meta = await dex_boost_feed(kind, chain, page)
            else:
                pairs, meta = await dex_boost_feed(kind, chain, page)
            if fallback_reason:
                meta = {
                    **meta,
                    'primary_provider': primary_provider,
                    'fallback_from': primary_provider,
                    'fallback_reason': fallback_reason,
                }
        except HTTPException as primary_error:
            if scope == 'pump':
                fallback_reason = f'Pump.fun unavailable; using public pool discovery fallback ({primary_error.detail}).'
            chains = SUPPORTED_CHAINS if chain == 'all' else (chain,)
            try:
                responses = await asyncio.gather(*[
                    cached(
                        'GeckoTerminal',
                        f'/networks/{NETWORKS[value]}/{"new_pools" if kind == "new" else "trending_pools"}',
                        {'include': 'base_token,quote_token,dex', 'page': page},
                        ttl=90,
                    )
                    for value in chains
                ])
            except HTTPException as fallback_error:
                unavailable = provider_meta(
                    'Public providers',
                    datetime.now(timezone.utc).isoformat(),
                    stale=True,
                    error=f'Public market providers are temporarily unavailable. {fallback_error.detail}',
                    primary_provider=primary_provider,
                    fallback_from=primary_provider,
                    fallback_reason=fallback_reason,
                )
                return MarketResult(
                    **unavailable,
                    source_url=PROVIDER_URLS['GeckoTerminal'],
                    label='New pools · provider unavailable' if kind == 'new' else 'Trending pools · provider unavailable',
                    pairs=[],
                    page=page,
                )
            pairs = [pair for data, _meta in responses for pair in normalise_pools(data)]
            meta = responses[0][1]
            if len(responses) > 1:
                meta = {
                    **meta,
                    'fetched_at': max(item[1].get('fetched_at', '') for item in responses),
                    'stale': any(item[1].get('stale', False) for item in responses),
                    'error': next((item[1].get('error') for item in responses if item[1].get('error')), None),
                }
            if kind == 'new':
                pairs = [pair for pair in pairs if is_new_pool_deal(pair)]
                pairs.sort(key=lambda pair: (
                    safe_float((pair.get('priceChange') or {}).get('h24')),
                    -(pair.get('pairCreatedAt') or 0),
                ))
            meta = {
                **meta,
                'primary_provider': primary_provider,
                'fallback_from': primary_provider if fallback_reason else None,
                'fallback_reason': fallback_reason,
            }
        if intelligence:
            pairs = await intelligence.observe(pairs, meta, kind)
        source_url = PROVIDER_URLS.get(meta.get('provider'), 'https://www.geckoterminal.com')
        label = meta.get('source_label') or ('New pools · deals ≥5% 24h drawdown' if kind == 'new' else 'Trending pools')
        return MarketResult(**meta, source_url=source_url, label=label, pairs=pairs, page=page)

    @router.get('/graduations', response_model=GraduationResult)
    async def graduations(mints: str = Query('', max_length=4000)):
        return await graduation_status(mints.split(','))

    @router.get('/search', response_model=MarketResult)
    async def search(q: str = Query(min_length=1, max_length=120)):
        if not q.strip():
            raise HTTPException(400, 'Enter a token or contract address')
        data, meta = await cached('DexScreener', '/latest/dex/search', {'q': q.strip()}, ttl=30)
        return MarketResult(**meta, source_url=PROVIDER_URLS['DexScreener'], label='Search results', pairs=data.get('pairs') or [])

    async def resolve_ca(address):
        data, meta = await cached('DexScreener', '/latest/dex/search', {'q': address}, ttl=60)
        pairs = [p for p in data.get('pairs') or [] if (
            p.get('baseToken', {}).get('address', '').lower() == address.lower() if address.startswith('0x')
            else p.get('baseToken', {}).get('address') == address)]
        pairs.sort(key=lambda p: float(p.get('liquidity', {}).get('usd') or 0), reverse=True)
        return pairs, meta

    async def dex_boost_feed(kind, chain='solana', page=1):
        """Use DexScreener's fast boost index for the first radar page."""
        if page != 1:
            raise HTTPException(503, 'Fast discovery is available on the first page only.')
        boost_path = f'/token-boosts/{"latest" if kind == "new" else "top"}/v1'
        boosts, boost_meta = await cached('DexScreener', boost_path, ttl=20)
        candidates = [
            item for item in (boosts if isinstance(boosts, list) else [])
            if item.get('tokenAddress') and (chain == 'all' or item.get('chainId') == chain)
        ]
        addresses = list(dict.fromkeys(item['tokenAddress'] for item in candidates))[:30]
        if not addresses:
            raise HTTPException(503, 'Fast discovery returned no indexed tokens.')
        payload, pair_meta = await cached(
            'DexScreener', f'/latest/dex/tokens/{",".join(addresses)}', ttl=20,
        )
        rank = {(item.get('chainId'), item.get('tokenAddress')): index
                for index, item in enumerate(candidates)}
        pairs = [
            pair for pair in (payload.get('pairs') or [])
            if chain == 'all' or pair.get('chainId') == chain
        ]
        best_by_token = {}
        for pair in pairs:
            key = (pair.get('chainId'), pair.get('baseToken', {}).get('address'))
            liquidity = safe_float((pair.get('liquidity') or {}).get('usd'))
            if key not in best_by_token or liquidity > safe_float(
                    (best_by_token[key].get('liquidity') or {}).get('usd')):
                best_by_token[key] = pair
        pairs = list(best_by_token.values())
        if kind == 'new':
            pairs = [pair for pair in pairs if is_new_pool_deal(pair)]
        pairs.sort(key=lambda pair: (
            rank.get((pair.get('chainId'), pair.get('baseToken', {}).get('address')), len(rank)),
            -safe_float((pair.get('liquidity') or {}).get('usd')),
        ))
        if not pairs:
            raise HTTPException(503, 'Fast discovery returned no qualifying pools.')
        return pairs, {
            **provider_meta(
                'DexScreener',
                pair_meta.get('fetched_at') or boost_meta.get('fetched_at'),
                stale=boost_meta.get('stale', False) or pair_meta.get('stale', False),
                error=boost_meta.get('error') or pair_meta.get('error'),
            ),
        }

    @router.get('/scan', response_model=MarketResult)
    async def scan(address: str = Query(min_length=32, max_length=64, pattern=r'^[a-zA-Z0-9]+$'), context: str = 'solana'):
        pairs, meta = await resolve_ca(address)
        if pairs and intelligence and not meta.get('stale'):
            await intelligence.event('CONTRACT_SCANNED', f'{pairs[0]["baseToken"]["symbol"]} · contract resolved', 'Exact contract matched to a provider pool. Not a security audit.', pairs[0], meta['provider'], meta['fetched_at'], context=context)
        return MarketResult(**meta, source_url=PROVIDER_URLS['DexScreener'], pairs=pairs, label='Exact contract matches')

    @router.get('/assets')
    async def assets():
        items = []
        for name in ['FEE', 'RFEE', 'FEECAT']:
            mint = os.getenv(f'{name}_MINT', DEFAULT_MINTS[name])
            try:
                data, meta = await cached('DexScreener', f'/token-pairs/v1/solana/{mint}', ttl=90)
                pairs = [p for p in data if p.get('baseToken', {}).get('address') == mint]
                pairs.sort(key=lambda p: float(p.get('liquidity', {}).get('usd') or 0), reverse=True)
                pair = pairs[0] if pairs else None
                image_url = (pair or {}).get('info', {}).get('imageUrl')
                if not pair or not image_url:
                    try:
                        token_data, token_meta = await cached('GeckoTerminal', f'/networks/solana/tokens/{mint}', ttl=90)
                        token = token_data.get('data') or {}
                        token_attrs = token.get('attributes') or {}
                        pools_data, pools_meta = await cached('GeckoTerminal', f'/networks/solana/tokens/{mint}/pools',
                                                              {'page': 1}, ttl=90)
                        pools = pools_data.get('data') or []
                        matching = [
                            pool for pool in pools
                            if pool.get('relationships', {}).get('base_token', {}).get('data', {}).get('id', '').split('_', 1)[-1] == mint
                        ]
                        matching.sort(key=lambda pool: float((pool.get('attributes') or {}).get('reserve_in_usd') or 0), reverse=True)
                        if not pair and matching:
                            pair = normalise_pools({'data': [matching[0]]})[0]
                        image_url = image_url or token_attrs.get('image_url')
                        if not pair and token_attrs.get('price_usd'):
                            top_pool = ((token.get('relationships') or {}).get('top_pools') or {}).get('data') or []
                            pool_id = top_pool[0].get('id', '') if top_pool else ''
                            pool_address = pool_id.split('_', 1)[-1] if pool_id else ''
                            if pool_address:
                                pair = {
                                    'chainId': 'solana',
                                    'network': 'solana',
                                    'pairAddress': pool_address,
                                    'dexId': 'unknown',
                                    'url': f'{os.getenv("DEX_SITE_URL", "https://dexscreener.com")}/solana/{pool_address}',
                                    'baseToken': {'address': mint, 'name': token_attrs.get('name', 'Unknown'),
                                                  'symbol': token_attrs.get('symbol', '?')},
                                    'quoteToken': {'symbol': 'SOL'},
                                    'priceUsd': token_attrs.get('price_usd'),
                                    'priceChange': {},
                                    'liquidity': {'usd': token_attrs.get('total_reserve_in_usd')},
                                    'volume': token_attrs.get('volume_usd') or {},
                                    'marketCap': token_attrs.get('market_cap_usd'),
                                    'fdv': token_attrs.get('fdv_usd'),
                                    'pairCreatedAt': None,
                                    'info': {'imageUrl': image_url, 'websites': [], 'socials': []},
                                }
                        if pair:
                            pair['info'] = {**(pair.get('info') or {}), 'imageUrl': image_url}
                            pair['baseToken'] = {
                                **(pair.get('baseToken') or {}),
                                'address': mint,
                                'name': token_attrs.get('name') or pair.get('baseToken', {}).get('name'),
                                'symbol': token_attrs.get('symbol') or pair.get('baseToken', {}).get('symbol'),
                            }
                            meta = {
                                **provider_meta(
                                    'GeckoTerminal',
                                    max(token_meta.get('fetched_at', ''), pools_meta.get('fetched_at', '')),
                                    stale=token_meta.get('stale', False) or pools_meta.get('stale', False),
                                    error=token_meta.get('error') or pools_meta.get('error'),
                                ),
                            }
                    except HTTPException:
                        pass
                items.append({'id': name.lower(), 'label': name, 'mint': mint, 'chain': 'solana', 'pair': pair,
                              'imageUrl': image_url,
                              'status': 'market_observed' if pair and pair.get('priceUsd') else 'awaiting_market', **meta,
                              'identity': 'Owner-supplied contract; exact provider match. Not a security endorsement.'})
            except HTTPException as exc:
                items.append({'id': name.lower(), 'label': name, 'mint': mint, 'chain': 'solana', 'pair': None,
                              'status': 'provider_unavailable', 'error': exc.detail})
        return {'assets': items}

    @router.get('/pair/{chain}/{address}', response_model=MarketResult)
    async def pair(chain: str, address: str):
        if chain not in NETWORKS or not address.isalnum() or len(address) > 100:
            raise HTTPException(400, 'Invalid chain or pair')
        data, meta = await cached('DexScreener', f'/latest/dex/pairs/{chain}/{address}', ttl=30)
        pairs = data.get('pairs') or []
        if intelligence:
            pairs = await intelligence.observe(pairs, meta)
        return MarketResult(**meta, source_url=PROVIDER_URLS['DexScreener'], pairs=pairs, label='Pair snapshot')

    @router.get('/candles/{chain}/{address}', response_model=CandleResult)
    async def candles(chain: str, address: str, interval: Literal['5m', '15m', '1h', '4h', '1d'] = '1h'):
        if chain not in NETWORKS or not address.isalnum() or len(address) > 100:
            raise HTTPException(400, 'Invalid chain or pool')
        timeframe, aggregate = {'5m': ('minute', 5), '15m': ('minute', 15), '1h': ('hour', 1),
                                '4h': ('hour', 4), '1d': ('day', 1)}[interval]
        data, meta = await cached('GeckoTerminal', f'/networks/{NETWORKS[chain]}/pools/{address}/ohlcv/{timeframe}',
                                  {'aggregate': aggregate, 'limit': 100, 'currency': 'usd', 'token': 'base'}, ttl=90)
        rows = data.get('data', {}).get('attributes', {}).get('ohlcv_list', [])
        unique = {row[0]: row for row in rows if len(row) >= 6}
        return CandleResult(**meta, source_label=PROVIDER_LABELS['GeckoTerminal'],
                            coverage=PROVIDER_COVERAGE['GeckoTerminal'],
                            candles=sorted(unique.values(), key=lambda row: row[0]))

    router.resolve_ca = resolve_ca
    return router