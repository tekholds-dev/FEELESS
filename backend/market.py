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

from ecosystem import DEFAULT_MINTS
from pydantic import BaseModel, Field

from launchpad_board import BOARD_MAX, BONK_PLATFORM_ID, JUP_LISTS, JUP_RECENT, PUMP_TREND_PARAMS, PUMP_TREND_PATH, PUMP_TREND_TTL, build_board, pump_pages, pump_trend_rows, dex_candidate, jup_candidate, launchlab_candidate, pump_candidate

BOARD_SCOPES = ('launchpads', 'pump', 'bonk', 'raydium')

NETWORKS = {'solana': 'solana', 'ethereum': 'ethereum', 'base': 'base', 'bsc': 'bsc',
            'arbitrum': 'arbitrum', 'avalanche': 'avalanche', 'polygon': 'polygon', 'sui': 'sui',
            'optimism': 'optimism', 'zksync': 'zksync', 'zora': 'zora', 'cronos': 'cronos', 'unichain': 'unichain', 'worldchain': 'worldchain'}
# Each chain's main DEXes + its name: DexScreener search on these returns that chain's live pools (filtered by chainId after).
CHAIN_QUOTES = {'solana': ['raydium', 'pumpswap', 'meteora', 'orca'], 'ethereum': ['uniswap', 'ethereum'], 'base': ['aerodrome', 'base', 'uniswap base'],
                'bsc': ['pancakeswap', 'bsc'], 'arbitrum': ['camelot', 'arbitrum'], 'avalanche': ['traderjoe', 'avalanche', 'pharaoh'],
                'polygon': ['quickswap', 'polygon'], 'sui': ['cetus', 'sui'], 'optimism': ['velodrome', 'optimism'], 'zksync': ['syncswap', 'zksync'],
                'zora': ['zora'], 'cronos': ['vvs', 'cronos', 'mm finance'], 'unichain': ['unichain'], 'worldchain': ['worldchain', 'world chain']}
THIN_FEED = 8  # fewer pools than this and a chain's feed gets topped up (no dead war rooms)
# Each thin chain's hub token: DexScreener lists every pool paired with it (/token-pairs; the hub itself is skipped).
# DexScreener doesn't index the Zora chain — Zora coins trade on Base, so that room searches Base (tagged as such).
HOST_CHAIN = {'zora': 'base'}
_WETH_OP = '0x4200000000000000000000000000000000000006'
NATIVE_POOLS = {'unichain': [('unichain', _WETH_OP)], 'worldchain': [('worldchain', _WETH_OP)], 'optimism': [('optimism', _WETH_OP)],
                'cronos': [('cronos', '0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23')],
                'zksync': [('zksync', '0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91')]}
SUPPORTED_CHAINS = tuple(NETWORKS)
MARKET_CACHE_RETENTION = timedelta(days=14)
NEW_POOL_DEAL_PERCENT = 5
PROVIDER_COVERAGE = {
    'Pump.fun': {
        'discovery': 'Pump.fun public coin index for Solana launchpad coverage',
        'snapshot': 'Pump.fun coin metadata snapshots',
        'candles': 'Not supplied (FEELESS candle service)',
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
}
PROVIDER_URLS = {
    'FEELESS launchpad board': 'https://pump.fun',
    'Pump.fun': 'https://pump.fun',
    'DexScreener': 'https://dexscreener.com',
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



def _pump_curve(mint: str):
    try:
        from solders.pubkey import Pubkey
        return str(Pubkey.find_program_address([b'bonding-curve', bytes(Pubkey.from_string(mint))], Pubkey.from_string('6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'))[0])
    except Exception:
        return None


def _mongo_safe(v):
    """MongoDB stores at most 8-byte ints; raw token supplies exceed that and crashed the feed cache."""
    if isinstance(v, bool):
        return v
    if isinstance(v, int) and not -2**63 <= v < 2**63:
        return str(v)
    if isinstance(v, dict):
        return {k: _mongo_safe(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_mongo_safe(x) for x in v]
    return v


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


# Pump Pulse: a coin is "pulsing" when the last 5 minutes show real, rising, two-sided flow.
# Minimum average trade size and a buy-share ceiling filter out micro-buy volume bots.
PULSE_MIN_TRADES = 20
PULSE_MIN_VOLUME = 5_000
PULSE_MIN_AVG_TRADE = 20
PULSE_BUY_SHARE = (0.55, 0.97)
PULSE_MIN_CHANGE = 2.0


def pulse_stats(pair):
    m5 = (pair.get('txns') or {}).get('m5') or {}
    buys, sells = int(safe_float(m5.get('buys')) or 0), int(safe_float(m5.get('sells')) or 0)
    trades = buys + sells
    volume = safe_float((pair.get('volume') or {}).get('m5')) or 0
    change = safe_float((pair.get('priceChange') or {}).get('m5'), None)
    avg = volume / trades if trades else 0
    share = buys / trades if trades else 0
    pulse = (trades >= PULSE_MIN_TRADES and volume >= PULSE_MIN_VOLUME and avg >= PULSE_MIN_AVG_TRADE
             and PULSE_BUY_SHARE[0] <= share <= PULSE_BUY_SHARE[1] and change is not None and change >= PULSE_MIN_CHANGE)
    return {'pairAddress': pair.get('pairAddress'), 'dexId': pair.get('dexId'), 'm5Change': change, 'buys': buys, 'sells': sells,
            'volumeM5': round(volume, 2), 'avgTradeUsd': round(avg, 2), 'buyShare': round(share * 100),
            'marketCap': safe_float(pair.get('marketCap')), 'pulse': pulse,
            'level': 0 if not pulse else 3 if volume >= 50_000 else 2 if volume >= 20_000 else 1}


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
        # Still on the curve → the real pool is pump.fun's bonding-curve PDA (pump.fun's own
        # `pool_address` for these coins can point at an account that doesn't exist yet).
        pool_address = (coin.get('raydium_pool') or coin.get('pool_address') or mint) if coin.get('complete') else (_pump_curve(mint) or mint)
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
        'Pump.fun': os.getenv('PUMP_API_URL', 'https://frontend-api-v3.pump.fun'),
        'LaunchLab': os.getenv('LAUNCHLAB_API_URL', 'https://launch-mint-v1.raydium.io'),
        'Jupiter': os.getenv('JUP_TOKENS_API_URL', 'https://lite-api.jup.ag'),
        'PumpBoard': os.getenv('PUMP_BOARD_API_URL', 'https://advanced-indexer.pump.fun'),   # 🔥 Pump's own trending board
    }

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
            if monotonic() < cooldown.get(key, 0) or len(queue) >= 240:
                error = 'Provider refresh limit reached. Try again in a minute.'
            else:
                queue.append(monotonic())
                try:
                    async with httpx.AsyncClient(timeout=12) as http:
                        headers = {'Accept': 'application/json;version=20230203'}
                        res = await http.get(bases[provider] + path, params=params, headers=headers)
                        res.raise_for_status()
                        data = res.json()
                    fetched = now.isoformat()
                    await db.market_cache.update_one({'key': key}, {'$set': {
                        'data': _mongo_safe(data), 'fetched_at': fetched, 'provider': provider}}, upsert=True)
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
        if kind == 'new':
            pairs.sort(key=lambda pair: pair.get('pairCreatedAt') or 0, reverse=True)
        return pairs, {
            **meta,
            'source_label': 'Pump.fun public coin index · launchpad coverage',
            'coverage': PROVIDER_COVERAGE['Pump.fun'],
        }

    board_cache = {}

    async def launchpad_board(kind):
        """Ranked Pump.fun + LetsBONK + LaunchLab coins (see launchpad_board.py). Cached 20s per kind."""
        hit = board_cache.get(kind)
        if hit and monotonic() - hit[0] < 20:
            return hit[1], hit[2]
        # 🌊 WIDE PULL (launchpad_board.pump_pages): Pump's 250 biggest coins + its 200 most recently traded (it was 50 + 100, so
        # most of the bigger runners / new majors never reached FEELESS). Deep pages change slowly → cached longer, so the wider
        # pull costs Pump about the same calls a minute (it rate-limits bursts).
        lab_sorts = ['new', 'lastTrade'] if kind == 'new' else ['lastTrade', 'marketCap']
        jobs = [('pump', cached('Pump.fun', '/coins', {'offset': off, 'limit': 50, 'sort': s, 'order': 'DESC', 'includeNsfw': 'false'}, ttl=ttl)) for s, off, ttl in pump_pages(kind)]
        jobs.append(('pump', cached('Pump.fun', '/coins/currently-live', {'offset': 0, 'limit': 30, 'includeNsfw': 'false'}, ttl=30)))
        for s in lab_sorts:
            jobs.append(('bonk', cached('LaunchLab', '/get/list', {'sort': s, 'size': 50, 'mintType': 'default', 'includeNsfw': 'false', 'platformId': BONK_PLATFORM_ID}, ttl=20)))
            jobs.append(('raydium', cached('LaunchLab', '/get/list', {'sort': s, 'size': 50, 'mintType': 'default', 'includeNsfw': 'false'}, ttl=20)))
        if kind != 'new':   # 🌊 movers: Jupiter's live trending / most-traded lists (launch coins only are kept)
            jobs += [('jup', cached('Jupiter', f'/tokens/v2/{cat}/{iv}', {'limit': 100}, ttl=45)) for cat, iv in JUP_LISTS]
        jobs.append(('jup', cached('Jupiter', JUP_RECENT, {'limit': 100}, ttl=30)))   # 🆕 the newest launches on every launchpad (both boards)
        jobs.append(('ptrend', cached('PumpBoard', PUMP_TREND_PATH, dict(PUMP_TREND_PARAMS), ttl=PUMP_TREND_TTL)))   # 🔥 Pump's Trending tab, every 10 min
        results = await asyncio.gather(*[job for _pad, job in jobs], return_exceptions=True)
        candidates, meta, movers, trend_first = {}, None, [], []
        for (pad, _job), res in zip(jobs, results):
            if isinstance(res, Exception):
                continue
            data, m = res
            if pad == 'ptrend':   # 🔥 Pump's own trending order goes FIRST
                for cand in pump_trend_rows(data):
                    if cand['mint'] not in candidates:
                        candidates[cand['mint']] = cand; trend_first.append(cand['mint'])
                    elif not candidates[cand['mint']].get('pumpTrend'):
                        candidates[cand['mint']]['pumpTrend'] = cand['pumpTrend']; trend_first.append(cand['mint'])
                continue
            if pad == 'jup':
                for tok in data if isinstance(data, list) else []:
                    cand = jup_candidate(tok)
                    if cand and cand['mint'] not in candidates:
                        candidates[cand['mint']] = cand; movers.append(cand['mint'])
                continue
            meta = meta or m
            rows = data if isinstance(data, list) else (((data or {}).get('data') or {}).get('rows') or [])
            for row in rows:
                cand = pump_candidate(row) if pad == 'pump' else launchlab_candidate(row, pad)
                if cand and cand['mint'] not in candidates and (cand['marketCap'] >= 5_000 or kind == 'new'):
                    candidates[cand['mint']] = cand
        seeded = {}
        try:  # migrated Pump/LetsBONK coins that DexScreener discovery is already surfacing
            boosted, _ = await dex_boost_feed(kind, 'solana', 1)
            for pair in boosted:
                cand = dex_candidate(pair)
                if cand and cand['mint'] not in candidates:
                    candidates[cand['mint']] = cand
                    seeded[cand['mint']] = pair
        except HTTPException:
            pass
        if not candidates:
            raise HTTPException(503, 'Launchpad indexes returned no coins.')
        # Priority order, not alphabetical: discovery-seeded, then Pump's active lists, then LaunchLab.
        first = trend_first + [m for m in list(seeded) + movers if m not in set(trend_first)]   # Pump trending + movers are never cut by the board cap
        first = list(dict.fromkeys(first))
        mints = (first + [m for m in candidates if m not in set(first)])[:BOARD_MAX]
        dex_pairs = dict(seeded)
        lookup = sorted(m for m in mints if m not in seeded)
        chunks = await asyncio.gather(*[cached('DexScreener', '/tokens/v1/solana/' + ','.join(lookup[i:i + 30]), ttl=20)
                                        for i in range(0, len(lookup), 30)], return_exceptions=True)
        for res in chunks:
            if isinstance(res, Exception):
                continue
            for pair in res[0] if isinstance(res[0], list) else []:
                mint = (pair.get('baseToken') or {}).get('address')
                if mint in candidates and pair.get('chainId') == 'solana':
                    best = dex_pairs.get(mint)
                    if not best or safe_float((pair.get('volume') or {}).get('h1')) > safe_float((best.get('volume') or {}).get('h1')):
                        dex_pairs[mint] = pair
        for m in movers:   # a mover's stage (curve / graduated) comes from its live pair, not from the trending row
            if m in dex_pairs and dex_candidate(dex_pairs[m]):
                candidates[m] = {**candidates[m], 'graduated': dex_candidate(dex_pairs[m])['graduated']}
        ranked = build_board({m: candidates[m] for m in mints}, dex_pairs, kind)
        meta = {**(meta or provider_meta('DexScreener', datetime.now(timezone.utc).isoformat())), 'provider': 'FEELESS launchpad board',
                'source_label': 'Pump.fun + LetsBONK + LaunchLab indexes · ranked on DexScreener 5m/1h flow',
                'coverage': {'discovery': 'Launchpad indexes (recent trades, top market cap, newest, live)', 'snapshot': 'DexScreener pair snapshots',
                             'graduation': 'Launchpad completion flags', 'stream': 'Polling snapshot, 20s'}}
        board_cache[kind] = (monotonic(), ranked, meta)
        return ranked, meta

    @router.get('/pump/callouts/{mint}')
    async def pump_callouts(mint: str):
        if not 32 <= len(mint) <= 44 or any(c not in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in mint):
            raise HTTPException(400, 'Invalid Solana mint.')
        token = os.getenv('PUMP_CALLOUT_TOKEN', '')
        if not token:
            raise HTTPException(503, 'Pump callouts require authorized provider access. Configure PUMP_CALLOUT_TOKEN on the server.')
        try:
            async with httpx.AsyncClient(timeout=12) as http:
                response = await http.get(bases['Pump.fun'] + '/coin-activity/' + mint,
                    params={'includeCallouts': 'true', 'includeTweets': 'false', 'includeTrades': 'false', 'includeNarrative': 'false'},
                    headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
                if response.status_code in (401, 403):
                    raise HTTPException(503, 'Pump callout access is not authorized. Update the server provider credentials.')
                response.raise_for_status()
                data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get('items'), list) or data.get('degraded', {}).get('callouts'):
                raise HTTPException(503, 'Pump callouts are temporarily unavailable.')
            return {'provider': 'Pump.fun', 'items': [item for item in data['items']
                    if isinstance(item, dict) and item.get('kind') == 'callout'
                    and isinstance(item.get('data'), dict) and item['data'].get('coinMint') == mint],
                    'fetchedAt': datetime.now(timezone.utc).isoformat()}
        except (httpx.HTTPError, ValueError):
            raise HTTPException(503, 'Pump callouts are temporarily unavailable.')

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
                data, meta = await cached('Pump.fun', f'/coins-v2/{mint}', ttl=60)
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
                   scope: str | None = Query(None, pattern=r'^[a-z0-9-]{1,30}$'),
                   source: str | None = Query(None, pattern=r'^(search)$')):
        if chain != 'all' and chain not in NETWORKS:
            raise HTTPException(400, 'Unsupported chain')
        fallback_reason = None
        primary_provider = 'Pump.fun' if scope == 'pump' else 'DexScreener'
        try:
            if source == 'search':
                raise HTTPException(503, 'Main-DEX search requested.')
            if scope in BOARD_SCOPES and chain == 'solana' and page == 1:
                pairs, meta = await launchpad_board(kind)
                if scope != 'launchpads':
                    pairs = [pair for pair in pairs if pair.get('launchpadId') == scope]
                if not pairs and scope == 'pump':
                    pairs, meta = await pump_feed(kind, page)   # quiet market: fall back to the raw index
                elif not pairs and scope != 'launchpads':
                    pairs, meta = await dex_boost_feed(kind, chain, page)   # quiet launchpad: show the live market
            elif scope == 'pump' and chain == 'solana':
                pairs, meta = await pump_feed(kind, page)
            elif scope == 'pump':
                fallback_reason = 'Pump.fun coverage is limited to Solana; using public pool discovery fallback.'
                pairs, meta = await dex_boost_feed(kind, chain, page)
            else:
                pairs, meta = await chain_feed(kind, chain, page)
                if chain == 'solana' and page == 1 and scope not in BOARD_SCOPES:
                    # 🌊 the Solana room shows what is moving NOW: the launch board (Pump / LetsBONK / LaunchLab + Jupiter's live
                    # movers, rebuilt every 20s) is woven into the chain list — it used to be DexScreener discovery only, which
                    # changes slowly, so the room looked frozen while the launch tabs moved.
                    try:
                        board, _ = await launchpad_board(kind)
                    except HTTPException:
                        board = []
                    seen_m, woven = set(), []
                    for a_, b_ in zip(board[:40] + [None] * 60, list(pairs) + [None] * 60):
                        for p_ in (a_, b_):
                            m_ = ((p_ or {}).get('baseToken') or {}).get('address')
                            if m_ and m_ not in seen_m:
                                seen_m.add(m_); woven.append(p_)
                    pairs = woven or pairs
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
            queries = [(c, q) for c in chains for q in CHAIN_QUOTES.get(c, [])]
            results = await asyncio.gather(*[cached('DexScreener', '/latest/dex/search', {'q': q}, ttl=60) for _c, q in queries], return_exceptions=True)
            best, meta = {}, None
            for (c, _q), res in zip(queries, results):
                if isinstance(res, Exception):
                    continue
                data, m = res
                meta = meta or m
                for pair in data.get('pairs') or []:
                    if pair.get('chainId') != c:  # never mix chains
                        continue
                    key = (c, (pair.get('baseToken') or {}).get('address'))
                    if key not in best or safe_float((pair.get('volume') or {}).get('h24')) > safe_float((best[key].get('volume') or {}).get('h24')):
                        best[key] = pair
            if meta is None:
                unavailable = provider_meta('DexScreener', datetime.now(timezone.utc).isoformat(), stale=True,
                                            error='Market provider is temporarily unavailable.', primary_provider=primary_provider,
                                            fallback_from=primary_provider, fallback_reason=fallback_reason)
                return MarketResult(**unavailable, source_url=PROVIDER_URLS['DexScreener'], label='Provider unavailable', pairs=[], page=page)
            pairs = sorted(best.values(), key=lambda p: -safe_float((p.get('volume') or {}).get('h24')))
            pairs = pairs[(page - 1) * 40: page * 40]
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
        source_url = PROVIDER_URLS.get(meta.get('provider'), 'https://dexscreener.com')
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

    async def chain_feed(kind, chain, page):
        """Boosted DexScreener coins first; thin chains are topped up from their own DEXes (no GeckoTerminal, ever)."""
        if chain in ('solana', 'all') or page != 1:
            return await dex_boost_feed(kind, chain, page)
        try:
            pairs, meta = await dex_boost_feed(kind, chain, page)
        except HTTPException:
            pairs, meta = [], None
        # Meta engine: no dead war rooms. A thin chain is topped up from its own main DEXes (DexScreener search,
        # filtered to this chain); a quiet "new" list adds the chain's youngest active pools, labelled as such.
        if len(pairs) < THIN_FEED:
            extra, m2 = await chain_search_pairs(chain)
            seen = {(p.get('baseToken') or {}).get('address', '').lower() for p in pairs}
            extra = [p for p in extra if (p.get('baseToken') or {}).get('address', '').lower() not in seen]
            if kind == 'new':
                fresh = [p for p in extra if is_new_pool_deal(p)]
                rising = sorted((p for p in extra if not is_new_pool_deal(p) and p.get('pairCreatedAt')), key=lambda p: -safe_float(p.get('pairCreatedAt')))
                extra = fresh + [{**p, 'discovery': 'rising'} for p in rising]
            pairs = pairs + extra
            meta = meta or m2
        if not pairs or meta is None:
            raise HTTPException(503, f'No live pools indexed for {chain} right now.')
        return pairs[:60], meta

    async def chain_search_pairs(chain):
        """This chain's live pools via its main DEX names (one cached search each), deepest-volume first."""
        queries = CHAIN_QUOTES.get(chain, [])
        hubs = NATIVE_POOLS.get(chain, [])
        results = await asyncio.gather(*[cached('DexScreener', '/latest/dex/search', {'q': q}, ttl=120) for q in queries],
                                       *[cached('DexScreener', f'/token-pairs/v1/{c}/{a}', ttl=120) for c, a in hubs], return_exceptions=True)
        hub_addrs = {a.lower() for _c, a in hubs}
        allowed = {chain, HOST_CHAIN.get(chain, chain)} | {c for c, _a in hubs}
        best, meta = {}, None
        for res in results:
            if isinstance(res, BaseException):
                continue
            data, m = res
            meta = meta or m
            for pair in (data if isinstance(data, list) else data.get('pairs') or []):
                addr = (pair.get('baseToken') or {}).get('address')
                if pair.get('chainId') not in allowed or not addr or addr.lower() in hub_addrs or safe_float((pair.get('liquidity') or {}).get('usd')) < 1000:
                    continue
                if pair['chainId'] != chain:
                    pair = {**pair, 'via': f"{chain} coin on {pair['chainId']}"}
                if addr not in best or safe_float((pair.get('volume') or {}).get('h24')) > safe_float((best[addr].get('volume') or {}).get('h24')):
                    best[addr] = pair
        return sorted(best.values(), key=lambda p: -safe_float((p.get('volume') or {}).get('h24'))), meta

    async def dex_boost_feed(kind, chain='solana', page=1):
        """Use DexScreener's fast boost index for the first radar page."""
        if page != 1:
            raise HTTPException(503, 'Fast discovery is available on the first page only.')
        # Several DexScreener discovery lists merged, so the radar isn't the same dozen boosted coins.
        primary = f'/token-boosts/{"latest" if kind == "new" else "top"}/v1'
        sources = [primary, '/token-boosts/latest/v1' if kind != 'new' else '/token-boosts/top/v1',
                   '/token-profiles/latest/v1', '/community-takeovers/latest/v1']
        candidates, boost_meta = [], None
        for path in sources:
            try:
                items, meta = await cached('DexScreener', path, ttl=30)
            except Exception:
                continue
            boost_meta = boost_meta or meta
            candidates += [item for item in (items if isinstance(items, list) else [])
                           if item.get('tokenAddress') and (chain == 'all' or item.get('chainId') == chain)]
        addresses = list(dict.fromkeys(item['tokenAddress'] for item in candidates))[:90]
        if not addresses:
            raise HTTPException(503, 'Fast discovery returned no indexed tokens.')
        payload, pair_meta = {'pairs': []}, None
        for i in range(0, len(addresses), 30):
            try:
                chunk, meta = await cached('DexScreener', f'/latest/dex/tokens/{",".join(addresses[i:i + 30])}', ttl=20)
            except Exception:
                continue
            pair_meta = pair_meta or meta
            payload['pairs'] += chunk.get('pairs') or []
        if pair_meta is None:
            raise HTTPException(503, 'Fast discovery returned no indexed tokens.')
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
                    # No DEX pool indexed yet (e.g. still on the pump.fun curve): Jupiter prices it directly.
                    try:
                        async with httpx.AsyncClient(timeout=8) as http:
                            jr = await http.get('https://api.jup.ag/tokens/v2/search', params={'query': mint},
                                                headers={'x-api-key': os.getenv('JUPITER_API_KEY', '')})
                        jt = next((t for t in (jr.json() if jr.status_code == 200 else []) if t.get('id') == mint), None)
                        if jt and jt.get('usdPrice'):
                            image_url = image_url or jt.get('icon')
                            if not pair:
                                pool_address = ((jt.get('firstPool') or {}).get('id')) or mint
                                st = jt.get('stats24h') or {}
                                pair = {'chainId': 'solana', 'network': 'solana', 'pairAddress': pool_address, 'dexId': 'jupiter',
                                        'url': f'https://jup.ag/tokens/{mint}',
                                        'baseToken': {'address': mint, 'name': jt.get('name'), 'symbol': jt.get('symbol')},
                                        'quoteToken': {'symbol': 'SOL'}, 'priceUsd': str(jt['usdPrice']),
                                        'priceChange': {'h24': st.get('priceChange')} if st.get('priceChange') is not None else {},
                                        'liquidity': {'usd': jt.get('liquidity')},
                                        'volume': {'h24': (st.get('buyVolume') or 0) + (st.get('sellVolume') or 0)} if st else {},
                                        'marketCap': jt.get('mcap'), 'fdv': jt.get('fdv'), 'pairCreatedAt': None,
                                        'info': {'imageUrl': image_url, 'websites': [], 'socials': []}}
                            meta = {**provider_meta('Jupiter', datetime.now(timezone.utc).isoformat())}
                    except Exception:
                        pass
                    try:
                        pass
                    except HTTPException:
                        pass
                # FEELESS serves a cached copy of every ecosystem logo (IPFS gateways rate-limit).
                image_url = f'/api/reputation/token-logo/{mint}'
                if pair:
                    pair.setdefault('info', {})['imageUrl'] = image_url
                items.append({'id': name.lower(), 'label': name, 'mint': mint, 'chain': 'solana', 'pair': pair,
                              'imageUrl': image_url,
                              'status': 'market_observed' if pair and pair.get('priceUsd') else 'awaiting_market', **meta,
                              'identity': 'Owner-supplied contract; exact provider match. Not a security endorsement.'})
            except HTTPException as exc:
                items.append({'id': name.lower(), 'label': name, 'mint': mint, 'chain': 'solana', 'pair': None,
                              'status': 'provider_unavailable', 'error': exc.detail})
        return {'assets': items}

    @router.get('/pulse')
    async def pump_pulse(mints: str = Query(..., max_length=2800)):
        """Pump Pulse: 5-minute activity per Solana mint (DexScreener batch), plus the pulse verdict."""
        ids = sorted({m for m in mints.split(',') if 32 <= len(m) <= 44 and m.isalnum()})[:60]
        best = {}
        for i in range(0, len(ids), 30):
            try:
                data, _ = await cached('DexScreener', '/tokens/v1/solana/' + ','.join(ids[i:i + 30]), ttl=20)
            except HTTPException:
                continue
            for pair in data if isinstance(data, list) else []:
                mint = (pair.get('baseToken') or {}).get('address')
                vol = safe_float((pair.get('volume') or {}).get('m5')) or 0
                if mint in ids and vol >= (best.get(mint, {}).get('_vol') or -1):
                    best[mint] = {**pair, '_vol': vol}
        return {'coins': {mint: pulse_stats(pair) for mint, pair in best.items()},
                'fetched_at': datetime.now(timezone.utc).isoformat()}

    @router.get('/pair/{chain}/{address}', response_model=MarketResult)
    async def pair(chain: str, address: str):
        if chain not in NETWORKS or not address.isalnum() or len(address) > 100:
            raise HTTPException(400, 'Invalid chain or pair')
        data, meta = await cached('DexScreener', f'/latest/dex/pairs/{chain}/{address}', ttl=30)
        pairs = data.get('pairs') or []
        if not pairs and chain == 'solana':
            # Fresh pump.fun curves can take minutes to reach DexScreener; the Pump network saw the launch live.
            from pump_network import network as pump_network
            streamed = pump_network.pair_for(address, await pump_network.sol_price())
            if streamed:
                return MarketResult(**{**meta, 'provider': 'PumpPortal'}, source_url='https://pumpportal.fun', pairs=[streamed], label='Pump network launch snapshot')
        if intelligence:
            pairs = await intelligence.observe(pairs, meta)
        return MarketResult(**meta, source_url=PROVIDER_URLS['DexScreener'], pairs=pairs, label='Pair snapshot')

    router.resolve_ca = resolve_ca
    return router
