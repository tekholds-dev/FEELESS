"""
FEELESS Cats — the paper-trading agent lab backend.

Paper trading against REAL live markets: every entry and exit is marked at the
actual DexScreener SOL-native price of a real Solana pair at that moment, with a
1% per-side fee/slippage haircut. Only the money is simulated — never the prices.

File-backed JSON store, zero external dependencies, standalone FastAPI app.
"""
import env_loader  # noqa: F401  (must run before reading os.environ)
import asyncio
import json
import math
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
STORE_PATH = DATA_DIR / 'feecats.json'

TICK_SECONDS = 20
SIGNAL_SYMBOLS = ['BRAIN', 'HOLDSWEET', 'UPTOBER', 'CHUBBY', 'TEXTIT', 'POLAR', 'INU', 'GOONER']
BRAIN_CATALOG = [
    {'id': 'claude-opus', 'provider': 'Anthropic', 'label': 'Claude Opus 5.5'},
    {'id': 'claude-fable', 'provider': 'Anthropic', 'label': 'Claude Fable 5.1'},
    {'id': 'gpt-astra', 'provider': 'OpenAI', 'label': 'GPT-6 Astra'},
    {'id': 'gpt-sol', 'provider': 'OpenAI', 'label': 'GPT-6 Sol'},
    {'id': 'muse', 'provider': 'Meta', 'label': 'Muse Spark 1.3'},
    {'id': 'grok', 'provider': 'xAI', 'label': 'Grok 4.7'},
    {'id': 'gemini', 'provider': 'Google', 'label': 'Gemini 3.8 Flash'},
    {'id': 'qwen', 'provider': 'Alibaba', 'label': 'Qwen 3.8 Max'},
    {'id': 'kimi', 'provider': 'Moonshot', 'label': 'Kimi K3'},
    {'id': 'deepseek', 'provider': 'DeepSeek', 'label': 'DeepSeek V4 Pro'},
]
STRATEGY_LABELS = {'balanced': 'Momentum', 'momentum': 'Breakouts', 'conservative': 'Scalping', 'signals': 'On-chain signals', 'trend': 'Trend following', 'conviction': 'Conviction'}


def _empty_store():
    return {'cats': {}, 'events': []}


def _load() -> dict:
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text())
        except Exception:
            pass
    return _empty_store()


def _save(store: dict):
    STORE_PATH.write_text(json.dumps(store, indent=2))


def _log_event(store, cat, kind, detail, pnl=None):
    store['events'].insert(0, {
        'id': uuid.uuid4().hex, 'catId': cat['id'], 'catName': cat['name'],
        'type': kind, 'detail': detail, 'ts': time.time() * 1000,
        'pnlSol': pnl, 'decisionSource': 'selected_brain' if cat.get('brainProfile', {}).get('available') else 'rule_engine',
        'brainLabel': cat.get('brainLabel'),
    })
    store['events'] = store['events'][:200]


FEE_PER_SIDE = 0.01
ENGINE_VERSION = 'live-v2'
LEADER_ID = 'leader'
MARKET_FEED = 'http://127.0.0.1:5001/api/market/feed?kind={kind}&chain=solana&page={page}'
RULES = {'minLiquidity': 40_000, 'minVolume24h': 100_000, 'minMarketCap': 150_000, 'maxMarketCap': 50_000_000,
         'minAgeHours': 3, 'h1Min': 3, 'h1Max': 40, 'h6Max': 120, 'h24Max': 400, 'minBuySellRatio': 1.2,
         'stopLoss': -10, 'takeProfit': 22, 'trailArm': 12, 'trailGive': 8, 'maxHoldHours': 4, 'maxPositions': 4,
         'cooldownHours': 2}


def _num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


async def _market_candidates(http):
    pairs = {}
    for kind in ('trending', 'volume', 'gainers'):
        for page in (1, 2):
            try:
                r = await http.get(MARKET_FEED.format(kind=kind, page=page))
                for p in (r.json() or {}).get('pairs') or []:
                    pairs[p.get('pairAddress')] = p
            except Exception:
                pass
    return list(pairs.values())


async def _pair_prices(http, pair_addresses):
    out = {}
    for i in range(0, len(pair_addresses), 30):
        try:
            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/solana/{",".join(pair_addresses[i:i + 30])}')
            for p in (r.json() or {}).get('pairs') or []:
                out[p.get('pairAddress')] = p
        except Exception:
            pass
    return out


def _qualifies(p, now):
    if ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
        return None, 'not SOL-quoted'
    liq = _num((p.get('liquidity') or {}).get('usd'))
    vol = _num((p.get('volume') or {}).get('h24'))
    mc = _num(p.get('marketCap') or p.get('fdv'))
    ch = p.get('priceChange') or {}
    m5, h1, h6, h24 = _num(ch.get('m5')), _num(ch.get('h1')), _num(ch.get('h6')), _num(ch.get('h24'))
    tx = (p.get('txns') or {}).get('h1') or {}
    buys, sells = _num(tx.get('buys')), _num(tx.get('sells'))
    age_h = (now * 1000 - _num(p.get('pairCreatedAt'), now * 1000)) / 3_600_000
    R = RULES
    checks = [(liq >= R['minLiquidity'], 'liquidity'), (vol >= R['minVolume24h'], 'volume'),
              (R['minMarketCap'] <= mc <= R['maxMarketCap'], 'market cap band'), (age_h >= R['minAgeHours'], 'too new'),
              (m5 > 0, '5m momentum'), (R['h1Min'] <= h1 <= R['h1Max'], '1h move'), (0 < h6 <= R['h6Max'], '6h trend'),
              (h24 <= R['h24Max'], 'overextended'), (sells == 0 or buys / max(sells, 1) >= R['minBuySellRatio'], 'buy pressure')]
    for ok, why in checks:
        if not ok:
            return None, why
    score = h1 * math.log10(max(vol, 10)) * min(buys / max(sells, 1), 3)
    reason = f"1h +{h1:.1f}%, 6h +{h6:.1f}%, {buys:.0f}/{sells:.0f} buys/sells, ${liq/1000:.0f}K liq, ${vol/1000:.0f}K vol"
    return score, reason


def _close(store, cat, pos, price_native, why):
    gross = pos['notionalSol'] * (price_native / pos['entryPriceNative'])
    proceeds = gross * (1 - FEE_PER_SIDE)
    pnl = round(proceeds - pos['costSol'], 6)
    cat['balanceSol'] = round(cat['balanceSol'] + proceeds, 6)
    cat['realizedPnlSol'] = round(cat.get('realizedPnlSol', 0) + pnl, 6)
    cat['totalPnlSol'] = cat['realizedPnlSol']
    cat['volumeSol'] = round(cat.get('volumeSol', 0) + gross, 6)
    cat['wins' if pnl >= 0 else 'losses'] = cat.get('wins' if pnl >= 0 else 'losses', 0) + 1
    cat['xp'] = cat.get('xp', 0) + (20 if pnl >= 0 else 6)
    cat['level'] = max(1, cat['xp'] // 100 + 1)
    cat.setdefault('dailyLoss', {})
    day = time.strftime('%Y-%m-%d')
    if pnl < 0:
        cat['dailyLoss'][day] = round(cat['dailyLoss'].get(day, 0) - pnl, 6)
    cat.setdefault('cooldowns', {})[pos['pairAddress']] = time.time()
    cat.setdefault('pnlHistory', []).append({'value': cat['realizedPnlSol'], 't': time.time()})
    cat['pnlHistory'] = cat['pnlHistory'][-60:]
    closed = cat.get('wins', 0) + cat.get('losses', 0)
    cat['winRate'] = round(cat['wins'] / closed * 100) if closed else None
    change = (price_native / pos['entryPriceNative'] - 1) * 100
    _log_event(store, cat, 'SELL', f"Sold {pos['symbol']} at {change:+.1f}% — {why}. Net {pnl:+.4f} SOL after fees (paper, live price).", pnl)


async def run_engine(store, cats):
    now = time.time()
    async with httpx.AsyncClient(timeout=10) as http:
        held = sorted({p['pairAddress'] for c in cats for p in c['positions'] if p.get('pairAddress')})
        prices = await _pair_prices(http, held) if held else {}
        candidates = await _market_candidates(http)
    ranked, rejections = [], {}
    for p in candidates:
        score, reason = _qualifies(p, now)
        if score is not None:
            ranked.append((score, reason, p))
        else:
            rejections[reason] = rejections.get(reason, 0) + 1
    store['scan'] = {'at': now, 'scanned': len(candidates), 'passed': len(ranked), 'rejections': rejections,
                     'top': [{'symbol': (p.get('baseToken') or {}).get('symbol'), 'reason': r, 'url': p.get('url')} for _, r, p in ranked[:5]]}
    ranked.sort(key=lambda x: -x[0])
    for cat in cats:
        R = RULES
        for pos in list(cat['positions']):
            live = prices.get(pos.get('pairAddress'))
            if not live:
                continue
            px = _num(live.get('priceNative'))
            if px <= 0:
                continue
            change = (px / pos['entryPriceNative'] - 1) * 100
            pos['currentChange'] = round(change, 2)
            pos['peakChange'] = max(pos.get('peakChange', 0), change)
            pos['lastPriceUsd'] = live.get('priceUsd')
            held_h = (now - pos['openedAt']) / 3600
            why = None
            if change <= R['stopLoss']:
                why = f'stop-loss {R["stopLoss"]}%'
            elif change >= R['takeProfit']:
                why = f'take-profit +{R["takeProfit"]}%'
            elif pos['peakChange'] >= R['trailArm'] and change <= pos['peakChange'] - R['trailGive']:
                why = f'trailing stop (peak +{pos["peakChange"]:.1f}%)'
            elif held_h >= R['maxHoldHours']:
                why = f'time exit after {R["maxHoldHours"]}h'
            if why:
                cat['positions'].remove(pos)
                _close(store, cat, pos, px, why)
        day = time.strftime('%Y-%m-%d')
        if cat.get('dailyLoss', {}).get(day, 0) >= float(cat['risk'].get('maxDailyLossSol') or 0.5):
            continue
        block = {x.upper() for x in cat['risk'].get('blocklist') or []}
        allow = {x.upper() for x in cat['risk'].get('allowlist') or []}
        for score, reason, p in ranked:
            if len(cat['positions']) >= R['maxPositions']:
                break
            sym = ((p.get('baseToken') or {}).get('symbol') or '?')
            pa = p.get('pairAddress')
            if sym.upper() in block or (allow and sym.upper() not in allow):
                continue
            if any(x['pairAddress'] == pa for x in cat['positions']):
                continue
            if now - cat.get('cooldowns', {}).get(pa, 0) < R['cooldownHours'] * 3600:
                continue
            px = _num(p.get('priceNative'))
            size = round(min(float(cat['risk']['maxPositionSol']), cat['balanceSol'] * 0.1), 4)
            if px <= 0 or size < 0.01 or cat['balanceSol'] < size:
                continue
            cat['balanceSol'] = round(cat['balanceSol'] - size, 6)
            cat['volumeSol'] = round(cat.get('volumeSol', 0) + size, 6)
            cat['positions'].append({
                'mint': (p.get('baseToken') or {}).get('address'), 'pairAddress': pa, 'symbol': sym, 'provider': 'DexScreener',
                'url': p.get('url'), 'costSol': size, 'notionalSol': round(size * (1 - FEE_PER_SIDE), 6),
                'entryPriceNative': px, 'entryPriceUsd': p.get('priceUsd'), 'entryChange': 0, 'currentChange': 0,
                'peakChange': 0, 'openedAt': now, 'reason': reason,
            })
            _log_event(store, cat, 'BUY', f"Bought {size} SOL of {sym} at live price — {reason} (paper).")
        cat['lastTick'] = now


def _migrate(store):
    for cat in store['cats'].values():
        if cat.get('engine') != ENGINE_VERSION:
            # Earlier numbers came from a random-walk simulator — reset so every figure shown is real.
            cat['balanceSol'] = float(cat.get('startingBalanceSol') or 10)
            cat.update({'positions': [], 'realizedPnlSol': 0, 'totalPnlSol': 0, 'volumeSol': 0, 'wins': 0, 'losses': 0,
                        'winRate': None, 'pnlHistory': [{'value': 0}], 'engine': ENGINE_VERSION, 'xp': 0, 'level': 1})
    if LEADER_ID not in store['cats']:
        now = time.time()
        store['cats'][LEADER_ID] = {
            'id': LEADER_ID, 'ownerId': 'feeless-system', 'name': 'Fee', 'handle': 'fee', 'avatar': 'Mint Mackerel',
            'isLeader': True, 'brain': 'rules', 'brainLabel': 'FEELESS rule engine',
            'brainProfile': {'provider': 'FEELESS', 'status': 'rule_engine', 'available': False, 'estimatedTokenCostUsd': 0},
            'strategy': 'trend', 'strategyLabel': 'Disciplined momentum', 'status': 'running', 'level': 1, 'xp': 0,
            'wallet': 'paper', 'startingBalanceSol': 25, 'balanceSol': 25, 'realizedPnlSol': 0, 'totalPnlSol': 0,
            'volumeSol': 0, 'wins': 0, 'losses': 0, 'winRate': None, 'positions': [], 'pnlHistory': [{'value': 0}],
            'risk': {'maxPositionSol': 2, 'maxDailyLossSol': 3, 'allowlist': [], 'blocklist': []},
            'revoked': False, 'createdAt': now, 'lastTick': now, 'engine': ENGINE_VERSION,
        }
    leader = store['cats'][LEADER_ID]
    leader['name'], leader['handle'] = 'Fee', 'fee'
    leader['title'] = 'The Leader of the FEELESS Cats'


async def _engine_loop():
    while True:
        try:
            store = _load()
            _migrate(store)
            running = [c for c in store['cats'].values() if c['status'] == 'running' and not c['revoked']]
            if running:
                await run_engine(store, running)
            _save(store)
        except Exception as exc:  # keep the loop alive; surface in logs
            print('engine error', exc)
        await asyncio.sleep(TICK_SECONDS)


def _score(cat):
    return {
        'id': cat['id'], 'name': cat['name'], 'avatar': cat['avatar'], 'level': cat['level'],
        'strategyLabel': cat['strategyLabel'], 'realizedPnlSol': cat['realizedPnlSol'],
        'volumeSol': cat.get('volumeSol', 0), 'winRate': cat.get('winRate'), 'isLeader': bool(cat.get('isLeader')),
        'openPositions': len(cat.get('positions', [])), 'trades': cat.get('wins', 0) + cat.get('losses', 0),
    }


app = FastAPI(title='FEELESS Cats')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


@app.on_event('startup')
async def _start_engine():
    asyncio.create_task(_engine_loop())


@app.get('/api/cats/brains')
async def brains():
    return {'brains': [{**b, 'status': 'rule_fallback', 'available': False, 'estimatedTokenCostUsd': 0} for b in BRAIN_CATALOG]}


class CreatePayload(BaseModel):
    ownerId: str
    name: str
    handle: str
    avatar: Any = 0
    brain: str = 'gpt-astra'
    strategy: str = 'momentum'
    instructions: Optional[str] = ''
    startingBalanceSol: Any = '10'
    maxPositionSol: Any = '0.25'
    dailyBuyLimitSol: Any = '2'
    maxDailyLossSol: Any = '0.5'
    walletMode: str = 'paper'
    coinPlan: str = 'later'
    allowlist: Optional[str] = ''
    blocklist: Optional[str] = ''


@app.post('/api/cats')
async def create_cat(payload: CreatePayload):
    store = _load()
    cat_id = uuid.uuid4().hex
    brain_info = next((b for b in BRAIN_CATALOG if b['id'] == payload.brain), BRAIN_CATALOG[0])
    now = time.time()
    cat = {
        'id': cat_id, 'ownerId': payload.ownerId, 'name': payload.name, 'handle': payload.handle,
        'avatar': payload.avatar, 'brain': payload.brain, 'brainLabel': brain_info['label'],
        'brainProfile': {'provider': brain_info['provider'], 'status': 'rule_fallback', 'available': False, 'estimatedTokenCostUsd': 0},
        'strategy': payload.strategy, 'strategyLabel': STRATEGY_LABELS.get(payload.strategy, 'Momentum'),
        'status': 'stopped', 'level': 1, 'xp': 0, 'wallet': 'paper',
        'balanceSol': float(payload.startingBalanceSol or 10), 'realizedPnlSol': 0, 'totalPnlSol': 0,
        'volumeSol': 0, 'wins': 0, 'losses': 0, 'winRate': None, 'positions': [], 'pnlHistory': [{'value': 0}],
        'risk': {
            'maxPositionSol': float(payload.maxPositionSol or 0.25), 'maxDailyLossSol': float(payload.maxDailyLossSol or 0.5),
            'allowlist': [s.strip() for s in (payload.allowlist or '').split(',') if s.strip()],
            'blocklist': [s.strip() for s in (payload.blocklist or '').split(',') if s.strip()],
        },
        'revoked': False, 'createdAt': now, 'lastTick': now, 'engine': ENGINE_VERSION,
        'startingBalanceSol': float(payload.startingBalanceSol or 10),
    }
    store['cats'][cat_id] = cat
    _save(store)
    recovery_key = '-'.join(uuid.uuid4().hex[:4] for _ in range(4))
    return {'cat': cat, 'recoveryKey': recovery_key}


@app.get('/api/cats')
async def list_cats(ownerId: str):
    store = _load()
    cats = [c for c in store['cats'].values() if c['ownerId'] == ownerId]
    cats.sort(key=lambda c: -c['createdAt'])
    return {'cats': cats}


@app.get('/api/cats/leader')
async def leader():
    store = _load()
    _migrate(store)
    return {'cat': store['cats'].get(LEADER_ID), 'rules': RULES, 'feePerSide': FEE_PER_SIDE, 'scan': store.get('scan')}


class EvaluatePayload(BaseModel):
    pairs: list


@app.post('/api/cats/evaluate')
async def evaluate(payload: EvaluatePayload):
    """Fee's read: runs any Solana pairs through the Leader's live entry rules."""
    addrs = [str(p.get('pairAddress')) for p in payload.pairs[:60] if isinstance(p, dict) and p.get('chainId') == 'solana' and p.get('pairAddress')]
    async with httpx.AsyncClient(timeout=10) as http:
        live = await _pair_prices(http, addrs) if addrs else {}
    now = time.time()
    out = {}
    for a in addrs:
        p = live.get(a)
        if not p:
            out[a] = {'passes': False, 'reason': 'no live market'}
            continue
        score, reason = _qualifies(p, now)
        out[a] = {'passes': score is not None, 'reason': reason}
    return {'reads': out, 'rules': RULES}


@app.get('/api/cats/leaderboard')
async def leaderboard(view: str = 'pnl'):
    store = _load()
    rows = [_score(c) for c in store['cats'].values() if not c['revoked']]
    if view == 'volume':
        rows.sort(key=lambda r: -r['volumeSol'])
    elif view == 'win_rate':
        rows = [r for r in rows if r['winRate'] is not None]
        rows.sort(key=lambda r: -r['winRate'])
    else:
        rows.sort(key=lambda r: -r['realizedPnlSol'])
    return {'rows': rows[:50]}


@app.get('/api/cats/activity')
async def activity(catId: Optional[str] = None):
    store = _load()
    events = store['events']
    if catId:
        events = [e for e in events if e['catId'] == catId]
    return {'events': events[:60]}


@app.get('/api/cats/health')
async def health():
    store = _load()
    return {'ok': True, 'cats': len(store['cats']), 'events': len(store['events'])}


@app.get('/api/cats/{cat_id}')
async def get_cat(cat_id: str):
    store = _load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise HTTPException(404, 'Cat not found.')
    return {'cat': cat}


class ActionPayload(BaseModel):
    action: str
    amount: Any = None
    recoveryKey: Optional[str] = None
    maxPositionSol: Any = None
    maxDailyLossSol: Any = None
    allowlist: Optional[str] = None
    blocklist: Optional[str] = None


@app.post('/api/cats/{cat_id}/action')
async def cat_action(cat_id: str, payload: ActionPayload):
    store = _load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise HTTPException(404, 'Cat not found.')

    if payload.action == 'confirm_recovery':
        pass
    elif payload.action == 'start':
        if cat['revoked']:
            raise HTTPException(400, 'This Cat has been revoked and cannot restart.')
        cat['status'] = 'running'
        cat['lastTick'] = time.time()
        _log_event(store, cat, 'STARTED', f'{cat["name"]} started paper trading.')
    elif payload.action == 'stop':
        cat['status'] = 'stopped'
        _log_event(store, cat, 'STOPPED', f'{cat["name"]} stopped by owner.')
    elif payload.action == 'run':
        if cat['status'] == 'running':
            await run_engine(store, [cat])
    elif payload.action == 'controls':
        if payload.maxPositionSol is not None:
            cat['risk']['maxPositionSol'] = float(payload.maxPositionSol)
        if payload.maxDailyLossSol is not None:
            cat['risk']['maxDailyLossSol'] = float(payload.maxDailyLossSol)
        if payload.allowlist is not None:
            cat['risk']['allowlist'] = [s.strip() for s in payload.allowlist.split(',') if s.strip()]
        if payload.blocklist is not None:
            cat['risk']['blocklist'] = [s.strip() for s in payload.blocklist.split(',') if s.strip()]
    elif payload.action == 'withdraw':
        amount = min(float(payload.amount or 0), cat['balanceSol'])
        cat['balanceSol'] = round(cat['balanceSol'] - amount, 6)
        _log_event(store, cat, 'WITHDRAW', f'Paper withdrawal of {amount:.4f} SOL recorded.')
    elif payload.action == 'revoke':
        cat['revoked'] = True
        cat['status'] = 'stopped'
        _log_event(store, cat, 'STOPPED', f'{cat["name"]} was revoked.')
    else:
        raise HTTPException(400, f'Unknown action: {payload.action}')

    _save(store)
    return {'cat': cat}
