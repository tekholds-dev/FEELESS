"""Observed market intelligence, with source and timestamp lineage."""
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

VENUES = {
    'pump': ['pump', 'pump-fun', 'pump_fun', 'pumpswap'],
    'bonk': [],  # LaunchLab venue alone does not establish BONK provenance.
    'raydium': ['raydium-launchlab'],
    'meteora': ['meteora', 'meteora-dlmm', 'meteora-dbc', 'meteora-damm-v2'],
    'moonit': ['moonit'], 'four': ['four-meme', 'four_meme'],
}

def num(value):
    try:
        result = float(value)
        return result if abs(result) < float('inf') else None
    except (ValueError, TypeError):
        return None

class TapeEvent(BaseModel):
    id: str
    kind: str
    title: str
    detail: str
    chain: str
    venue: str | None = None
    observed_at: str
    provider: str
    pair: dict[str, Any]
    context: str | None = None

class TapeResponse(BaseModel):
    events: list[TapeEvent]
    unsupported: list[str] = Field(default_factory=lambda: ['individual whale trades', 'pool migration', 'all-time highs', 'holder concentration'])

class Intelligence:
    def __init__(self, db):
        self.db = db

    async def event(self, kind, title, detail, pair, provider, stamp, context=None, unique=None):
        key = unique or f'{kind}:{provider}:{pair.get("chainId")}:{pair.get("pairAddress")}:{stamp[:16]}'
        identity = hashlib.sha256(key.encode()).hexdigest()[:24]
        doc = {'id': identity, 'kind': kind, 'title': title, 'detail': detail,
               'chain': pair['chainId'], 'venue': pair.get('dexId'), 'observed_at': stamp,
               'provider': provider, 'pair': pair, 'context': context}
        await self.db.alpha_events.update_one({'id': identity}, {'$setOnInsert': doc}, upsert=True)

    async def observe(self, pairs, meta, kind='snapshot'):
        if meta.get('stale'):
            return pairs
        for pair in pairs:
            key = f'{meta["provider"]}:{pair["chainId"]}:{pair["pairAddress"]}'
            old = await self.db.market_observations.find_one({'key': key}, {'_id': 0})
            stamp = meta['fetched_at']
            if old and old['observed_at'] == stamp:
                pair['signals'] = old.get('signals', {})
                continue
            current = {'price': num(pair.get('priceUsd')), 'liquidity': num(pair.get('liquidity', {}).get('usd')),
                       'volume': num(pair.get('volume', {}).get('h24'))}
            signals = {}
            if old:
                elapsed = (datetime.fromisoformat(stamp) - datetime.fromisoformat(old['observed_at'])).total_seconds() / 60
                if elapsed > 0:
                    for field in current:
                        previous = old.get(field)
                        if previous and current[field] is not None:
                            signals[f'{field}_change_pct'] = (current[field] - previous) / previous * 100
                    signals['elapsed_minutes'] = round(elapsed, 2)
                    signals['since'] = old['observed_at']
            changes = pair.get('priceChange', {})
            five, hour = num(changes.get('m5')), num(changes.get('h1'))
            if five is not None:
                signals['velocity_pct_min'] = five / 5
            if five is not None and hour is not None:
                signals['acceleration_indicator'] = five / 5 - (hour - five) / 55
            history = (old or {}).get('signals', {}).get('history', [])
            if current['price'] is not None:
                history = [*history, {'time': stamp, 'price': current['price']}][-40:]
            signals['history'] = history
            pair['signals'] = signals
            pair['observedAt'] = stamp
            symbol = pair.get('baseToken', {}).get('symbol', 'Token')
            if kind == 'trending' and not old:
                await self.event('TRENDING', f'{symbol} on the radar', 'Observed in the provider trending-pool feed.', pair, meta['provider'], stamp)
            created = pair.get('pairCreatedAt')
            if kind == 'new' and created:
                await self.event('NEW_PAIR', f'{symbol} · pool indexed', f'Pool creation time reported by provider: {datetime.fromtimestamp(created / 1000, timezone.utc).isoformat()}', pair, meta['provider'], stamp, unique=f'new:{pair["chainId"]}:{pair["pairAddress"]}')
            for field, threshold, event_kind, label in [('liquidity', 3, 'LIQUIDITY_CHANGE', 'Liquidity snapshot'), ('price', 1, 'PRICE_VELOCITY', 'Price snapshot'), ('volume', 20, 'VOLUME_CHANGE', 'Rolling 24h volume')]:
                delta = signals.get(f'{field}_change_pct')
                if delta is not None and abs(delta) >= threshold:
                    await self.event(event_kind, f'{symbol} · {delta:+.2f}%', f'{label} changed over {signals["elapsed_minutes"]} min. Snapshot delta, not a transaction event.', pair, meta['provider'], stamp)
            await self.db.market_observations.update_one({'key': key}, {'$set': {**current, 'observed_at': stamp, 'signals': signals}}, upsert=True)
        return pairs

    def router(self):
        router = APIRouter(prefix='/api/intelligence')

        @router.get('/tape', response_model=TapeResponse)
        async def tape(chain: str = 'solana', venue: str = 'all', context: str | None = None, limit: int = Query(30, ge=1, le=100)):
            query = {} if chain == 'all' else {'chain': chain}
            if venue in VENUES:
                query['venue'] = {'$in': VENUES[venue]}
            if context:
                query['$or'] = [{'context': None}, {'context': context}]
            docs = await self.db.alpha_events.find(query, {'_id': 0}).sort('observed_at', -1).limit(limit).to_list(limit)
            return TapeResponse(events=docs)

        @router.get('/community')
        async def community(context: str = Query('solana', pattern=r'^[a-z0-9-]{1,30}$')):
            cutoff = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 1000)
            match = {'room': {'$regex': f'^{context}-(general|alpha|launches|trading|whales|new-pools)$'}, 'ts': {'$gte': cutoff}}
            rows = await self.db.chat_messages.aggregate([
                {'$match': match}, {'$group': {'_id': '$username', 'messages': {'$sum': 1}, 'latest': {'$max': '$ts'}}},
                {'$sort': {'messages': -1, 'latest': -1}}, {'$limit': 20},
                {'$project': {'_id': 0, 'handle': '$_id', 'messages': 1, 'latest': 1}}]).to_list(20)
            total = await self.db.chat_messages.count_documents(match)
            return {'context': context, 'window': '7 days', 'messages': total, 'rankings': rows,
                    'disclosure': 'Public, unauthenticated handles ranked by actual messages. Not verified identities.'}
        return router