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
MARKET_CACHE_RETENTION = timedelta(days=14)
NEW_POOL_DEAL_PERCENT = 5


def safe_float(value, default=0.0):
    try:
        result = float(value)
        return result if result == result else default
    except (TypeError, ValueError):
        return default


class MarketResult(BaseModel):
    provider: str
    fetched_at: str
    stale: bool = False
    error: str | None = None
    label: str = ''
    pairs: list[dict[str, Any]] = Field(default_factory=list)
    page: int = 1


class CandleResult(BaseModel):
    provider: str
    fetched_at: str
    stale: bool = False
    error: str | None = None
    candles: list[list[float]]


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
            'url': f"{os.environ['DEX_SITE_URL']}/{chain}/{a['address']}",
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


def create_market_router(db, intelligence=None):
    router = APIRouter(prefix='/api/market')
    locks = defaultdict(asyncio.Lock)
    requests = defaultdict(deque)
    cooldown = {}
    bases = {'DexScreener': os.environ['DEX_API_URL'], 'GeckoTerminal': os.environ['GECKO_API_URL']}

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
                return hit['data'], {'provider': provider, 'fetched_at': hit['fetched_at'], 'stale': False}
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
                        res = await http.get(bases[provider] + path, params=params,
                                             headers={'Accept': 'application/json;version=20230203'})
                        res.raise_for_status()
                        data = res.json()
                    fetched = now.isoformat()
                    await db.market_cache.update_one({'key': key}, {'$set': {
                        'data': data, 'fetched_at': fetched, 'provider': provider}}, upsert=True)
                    return data, {'provider': provider, 'fetched_at': fetched, 'stale': False}
                except (httpx.HTTPError, ValueError):
                    cooldown[key] = monotonic() + 45
                    error = f'{provider} is temporarily unavailable.'
            if hit:
                return hit['data'], {'provider': provider, 'fetched_at': hit['fetched_at'], 'stale': True, 'error': error}
            raise HTTPException(503, detail=error)

    @router.get('/feed', response_model=MarketResult)
    async def feed(kind: Literal['trending', 'new'] = 'trending',
                   chain: str = 'solana', page: int = Query(1, ge=1, le=10)):
        if chain != 'all' and chain not in NETWORKS:
            raise HTTPException(400, 'Unsupported chain')
        network = f'/{NETWORKS[chain]}' if chain != 'all' else ''
        path = f'/networks{network}/{"new_pools" if kind == "new" else "trending_pools"}'
        data, meta = await cached('GeckoTerminal', path, {'include': 'base_token,quote_token,dex', 'page': page}, ttl=90)
        pairs = normalise_pools(data)
        if kind == 'new':
            cutoff = datetime.now(timezone.utc).timestamp() * 1000 - MARKET_CACHE_RETENTION.total_seconds() * 1000
            pairs = [
                pair for pair in pairs
                if pair.get('pairCreatedAt') and pair['pairCreatedAt'] >= cutoff
                and safe_float((pair.get('priceChange') or {}).get('h24')) <= -NEW_POOL_DEAL_PERCENT
            ]
            pairs.sort(key=lambda pair: (
                safe_float((pair.get('priceChange') or {}).get('h24')),
                -(pair.get('pairCreatedAt') or 0),
            ))
        if intelligence:
            pairs = await intelligence.observe(pairs, meta, kind)
        return MarketResult(**meta, label='New pools · deals ≥5% 24h drawdown' if kind == 'new' else 'Trending pools', pairs=pairs, page=page)

    @router.get('/search', response_model=MarketResult)
    async def search(q: str = Query(min_length=1, max_length=120)):
        if not q.strip():
            raise HTTPException(400, 'Enter a token or contract address')
        data, meta = await cached('DexScreener', '/latest/dex/search', {'q': q.strip()}, ttl=30)
        return MarketResult(**meta, label='Search results', pairs=data.get('pairs') or [])

    async def resolve_ca(address):
        data, meta = await cached('DexScreener', '/latest/dex/search', {'q': address}, ttl=60)
        pairs = [p for p in data.get('pairs') or [] if (
            p.get('baseToken', {}).get('address', '').lower() == address.lower() if address.startswith('0x')
            else p.get('baseToken', {}).get('address') == address)]
        pairs.sort(key=lambda p: float(p.get('liquidity', {}).get('usd') or 0), reverse=True)
        return pairs, meta

    @router.get('/scan', response_model=MarketResult)
    async def scan(address: str = Query(min_length=32, max_length=64, pattern=r'^[a-zA-Z0-9]+$'), context: str = 'solana'):
        pairs, meta = await resolve_ca(address)
        if pairs and intelligence and not meta.get('stale'):
            await intelligence.event('CONTRACT_SCANNED', f'{pairs[0]["baseToken"]["symbol"]} · contract resolved', 'Exact contract matched to a provider pool. Not a security audit.', pairs[0], meta['provider'], meta['fetched_at'], context=context)
        return MarketResult(**meta, pairs=pairs, label='Exact contract matches')

    @router.get('/assets')
    async def assets():
        items = []
        for name in ['FEE', 'RFEE', 'FEECAT']:
            mint = os.environ[f'{name}_MINT']
            try:
                data, meta = await cached('DexScreener', f'/token-pairs/v1/solana/{mint}', ttl=90)
                pairs = [p for p in data if p.get('baseToken', {}).get('address') == mint]
                pairs.sort(key=lambda p: float(p.get('liquidity', {}).get('usd') or 0), reverse=True)
                pair = pairs[0] if pairs else None
                items.append({'id': name.lower(), 'label': name, 'mint': mint, 'chain': 'solana', 'pair': pair,
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
        return MarketResult(**meta, pairs=pairs, label='Pair snapshot')

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
        return CandleResult(**meta, candles=sorted(unique.values(), key=lambda row: row[0]))

    router.resolve_ca = resolve_ca
    return router