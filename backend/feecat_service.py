"""
FEELESS Cats — the paper-trading agent lab backend.

Everything here is explicitly a simulation: balances, positions and P/L are a
deterministic random-walk ledger, never real market data or real signing. The
frontend already labels this "PAPER TRADING · NO REAL SOL" throughout — this
service exists to make that promise actually functional instead of 404ing.

File-backed JSON store, zero external dependencies, standalone FastAPI app.
"""
import json
import random
import string
import time
import uuid
from pathlib import Path
from typing import Any, Optional

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


def _fake_wallet() -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for _ in range(44))


def _log_event(store, cat, kind, detail, pnl=None):
    store['events'].insert(0, {
        'id': uuid.uuid4().hex, 'catId': cat['id'], 'catName': cat['name'],
        'type': kind, 'detail': detail, 'ts': time.time() * 1000,
        'pnlSol': pnl, 'decisionSource': 'selected_brain' if cat.get('brainProfile', {}).get('available') else 'rule_engine',
        'brainLabel': cat.get('brainLabel'),
    })
    store['events'] = store['events'][:200]


def _tick(store: dict, cat: dict, force=False):
    now = time.time()
    if not force and cat['status'] != 'running':
        return
    elapsed = now - cat.get('lastTick', now)
    if not force and elapsed < TICK_SECONDS:
        return
    cat['lastTick'] = now
    rng = random.Random()

    for position in cat['positions']:
        position['currentChange'] = round(position['currentChange'] + rng.uniform(-4, 4.4), 2)

    if len(cat['positions']) < 3 and rng.random() < 0.55:
        symbol = rng.choice(SIGNAL_SYMBOLS)
        size = round(min(cat['balanceSol'], float(cat['risk']['maxPositionSol'])) * rng.uniform(0.3, 1), 4)
        if size > 0.0001 and cat['balanceSol'] >= size:
            cat['balanceSol'] = round(cat['balanceSol'] - size, 6)
            cat['positions'].append({
                'mint': uuid.uuid4().hex[:40], 'symbol': symbol, 'provider': 'DexScreener',
                'notionalSol': size, 'entryChange': 0, 'currentChange': 0,
            })
            _log_event(store, cat, 'BUY', f'Opened {size} SOL into {symbol} (paper).')

    if cat['positions'] and rng.random() < 0.4:
        position = cat['positions'].pop(rng.randrange(len(cat['positions'])))
        pnl = round(position['notionalSol'] * (position['currentChange'] / 100), 6)
        cat['balanceSol'] = round(cat['balanceSol'] + position['notionalSol'] + pnl, 6)
        cat['realizedPnlSol'] = round(cat.get('realizedPnlSol', 0) + pnl, 6)
        cat['totalPnlSol'] = round(cat.get('totalPnlSol', 0) + pnl, 6)
        if pnl >= 0:
            cat['wins'] = cat.get('wins', 0) + 1
        else:
            cat['losses'] = cat.get('losses', 0) + 1
        cat['xp'] = cat.get('xp', 0) + (15 if pnl >= 0 else 5)
        cat['level'] = max(1, cat['xp'] // 100 + 1)
        cat.setdefault('pnlHistory', []).append({'value': cat['totalPnlSol']})
        cat['pnlHistory'] = cat['pnlHistory'][-30:]
        _log_event(store, cat, 'SELL', f'Closed {position["symbol"]} (paper).', pnl)

    closed = cat.get('wins', 0) + cat.get('losses', 0)
    cat['winRate'] = round(cat['wins'] / closed * 100) if closed else None


def _score(cat):
    return {
        'id': cat['id'], 'name': cat['name'], 'avatar': cat['avatar'], 'level': cat['level'],
        'strategyLabel': cat['strategyLabel'], 'realizedPnlSol': cat['realizedPnlSol'],
        'volumeSol': cat.get('volumeSol', 0), 'winRate': cat.get('winRate'),
    }


app = FastAPI(title='FEELESS Cats')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


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
        'status': 'stopped', 'level': 1, 'xp': 0, 'wallet': _fake_wallet(),
        'balanceSol': float(payload.startingBalanceSol or 10), 'realizedPnlSol': 0, 'totalPnlSol': 0,
        'volumeSol': 0, 'wins': 0, 'losses': 0, 'winRate': None, 'positions': [], 'pnlHistory': [{'value': 0}],
        'risk': {
            'maxPositionSol': float(payload.maxPositionSol or 0.25), 'maxDailyLossSol': float(payload.maxDailyLossSol or 0.5),
            'allowlist': [s.strip() for s in (payload.allowlist or '').split(',') if s.strip()],
            'blocklist': [s.strip() for s in (payload.blocklist or '').split(',') if s.strip()],
        },
        'revoked': False, 'createdAt': now, 'lastTick': now,
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
    _tick(store, cat)
    _save(store)
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
        _tick(store, cat, force=True)
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

    _tick(store, cat)
    _save(store)
    return {'cat': cat}
