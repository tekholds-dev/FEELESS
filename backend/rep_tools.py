"""🧩 Q02: the owner's tool routes, split out of reputation_service (34,000 lines) one safe slice at a time. No money and no trading moves through here.

Helpers still live in reputation_service and are looked up when a route runs, so nothing is imported twice and there is no import cycle."""
import asyncio
import os
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()
DATA_DIR = Path(__file__).parent / 'data'


def _rs():
    import reputation_service
    return reputation_service


_LIMITS = {'busy': None, 'results': {}}
MODEL_LIMITS_PATH = DATA_DIR / 'model_limits.json'


def _limit_seats():
    """The free LM Studio seats this server can reach. Never a paid model."""
    out = {}
    for k_, name_, base_, key_, model_ in (('lan', 'G4', 'LAN_LLM_BASE_URL', 'LAN_LLM_API_KEY', 'LAN_LLM_MODEL'), ('local', 'OSSY', 'LOCAL_LLM_BASE_URL', 'LOCAL_LLM_API_KEY', 'LOCAL_LLM_MODEL')):
        b_ = str(os.environ.get(base_) or '').strip()
        if b_:
            out[k_] = {'name': name_, 'base': b_, 'key': os.environ.get(key_) or '', 'model': os.environ.get(model_) or ''}
    return out


async def _limits_run(k_, seat_, overlay_, label_):
    import model_limits as _ml
    try:
        async with httpx.AsyncClient() as h_:
            model_ = seat_['model']
            if not model_:
                ids_ = [m_['id'] for m_ in (await h_.get(seat_['base'].rstrip('/') + '/models', headers={'Authorization': f"Bearer {seat_['key'] or 'lm-studio'}"}, timeout=8)).json().get('data') or [] if 'embed' not in m_['id']]
                model_ = ids_[0] if ids_ else ''
            got_ = await _ml.run_one(h_, seat_['base'], seat_['key'], model_, overlay_)
        got_.update(seat=seat_['name'], prompt=label_)
        kept_ = dict(_rs()._json_load(MODEL_LIMITS_PATH, {}) or {}); kept_[f'{k_}:{label_}'] = got_; _rs()._json_save(MODEL_LIMITS_PATH, kept_)
    except (httpx.HTTPError, ValueError, KeyError) as e_:
        kept_ = dict(_rs()._json_load(MODEL_LIMITS_PATH, {}) or {}); kept_[f'{k_}:{label_}'] = {'seat': seat_['name'], 'prompt': label_, 'err': str(e_)[:120] or 'It did not answer', 'rows': [], 'score': 0, 'at': round(time.time())}; _rs()._json_save(MODEL_LIMITS_PATH, kept_)
    finally:
        _LIMITS['busy'] = None


FIX_RUNS_PATH = DATA_DIR / 'fix_runs.json'
_FIX = {'busy': None}


def _fix_seats():
    """Who may investigate. The LM Studio minds are free; the cloud one spends a fraction of a cent of the owner's OpenRouter credit."""
    out = {k_: {**v_, 'free': True} for k_, v_ in _limit_seats().items()}
    key_ = os.environ.get('OPENROUTER_API_KEY', '').strip()
    if key_:
        out['cloud'] = {'name': 'Cloud mind', 'base': 'https://openrouter.ai/api/v1', 'key': key_, 'model': 'deepseek/deepseek-v4-pro-0813', 'free': False}
    return out


def _fix_store(row_):
    runs_ = dict(_rs()._json_load(FIX_RUNS_PATH, {}) or {}); runs_[row_['id']] = row_
    _rs()._json_save(FIX_RUNS_PATH, dict(sorted(runs_.items(), key=lambda kv_: -(kv_[1].get('at') or 0))[:40]))


async def _fix_run(case_, seat_, name_):
    import fix_agent as _fa
    row_ = {'id': case_['id'], 'text': case_['text'], 'by': name_, 'at': round(time.time()), 'stage': 'reading'}; _fix_store(row_)
    try:
        async with httpx.AsyncClient() as h_:
            model_ = seat_['model']
            if not model_:
                ids_ = [m_['id'] for m_ in (await h_.get(seat_['base'].rstrip('/') + '/models', headers={'Authorization': f"Bearer {seat_['key'] or 'lm-studio'}"}, timeout=8)).json().get('data') or [] if 'embed' not in m_['id']]
                model_ = ids_[0] if ids_ else ''
            got_ = await _fa.investigate(h_, seat_['base'], seat_['key'], model_, case_['text'])
        row_.update({k_: got_.get(k_) for k_ in ('cause', 'file', 'sure', 'why')}, model=model_, diff=_fa.diff_rows(got_.get('old') or '', got_.get('new') or ''))
        if got_.get('old'):
            row_['stage'] = 'testing'; _fix_store(row_)
            tried_ = await asyncio.to_thread(_fa.try_fix, case_['id'], got_['file'], got_['old'], got_['new'])
            row_.update({k_: tried_.get(k_) for k_ in ('ok', 'branch', 'tree', 'checks')}, why=tried_.get('why') or '')
            row_['stage'] = 'review' if tried_.get('ok') else 'failed'
            if tried_.get('branch') and not tried_.get('ok'):   # a fix that failed its own checks is not kept
                await asyncio.to_thread(_fa.drop, tried_['branch'], tried_['tree']); row_.pop('branch', None); row_.pop('tree', None)
        else:
            row_['stage'] = 'failed'
    except (httpx.HTTPError, ValueError, KeyError, OSError) as e_:
        row_.update(stage='failed', why=str(e_)[:160] or 'It did not answer.')
    finally:
        _fix_store(row_); _FIX['busy'] = None


@router.get('/api/reputation/admin/fix')
async def admin_fix(request: Request):
    """🛠 Owner: logged crashes, and each one's try: its cause, its change, its checks."""
    import fix_agent as _fa
    _rs()._require_owner(request)
    runs_ = _rs()._json_load(FIX_RUNS_PATH, {}) or {}
    return {'busy': _FIX['busy'], 'seats': [{'key': k_, 'name': v_['name'], 'free': v_['free']} for k_, v_ in _fix_seats().items()], 'cases': [{**c_, 'run': {k_: v_ for k_, v_ in (runs_.get(c_['id']) or {}).items() if k_ != 'tree'} or None} for c_ in _fa.cases_from((_rs()._json_load(_rs().BUGS_PATH, {'bugs': []}) or {}).get('bugs') or [])]}


@router.post('/api/reputation/admin/fix')
async def admin_fix_act(request: Request):
    """🛠 Owner: {id, seat} investigates. {id, approve} queues its branch for the engineer. {id, drop} forgets the try. Nothing merges or pushes here."""
    import fix_agent as _fa
    _rs()._require_owner(request)
    body = await request.json(); body = body if isinstance(body, dict) else {}; id_ = str(body.get('id') or '')
    runs_ = dict(_rs()._json_load(FIX_RUNS_PATH, {}) or {}); run_ = runs_.get(id_)
    if body.get('drop'):
        if run_ and run_.get('branch'):
            await asyncio.to_thread(_fa.drop, run_['branch'], run_.get('tree'))
        runs_.pop(id_, None); _rs()._json_save(FIX_RUNS_PATH, runs_)
        return {'ok': True}
    if body.get('approve'):
        if not run_ or run_.get('stage') != 'review':
            raise HTTPException(400, 'That fix has not passed its checks.')
        _rs()._chat['build'], it_ = _rs()._aic.build_add(_rs()._build_state(), f"Fix agent: {run_.get('file')}"[:80], f"Merge branch {run_['branch']}: {run_.get('cause')}", 'fix agent · owner approved', time.time())
        _rs()._json_save(_rs().BUILD_QUEUE_PATH, _rs()._chat['build']); run_['stage'] = 'approved'; run_['build'] = it_['id']; _fix_store(run_)
        return {'ok': True, 'build': it_['id']}
    case_ = next((c_ for c_ in _fa.cases_from((_rs()._json_load(_rs().BUGS_PATH, {'bugs': []}) or {}).get('bugs') or []) if c_['id'] == id_), None); seat_ = _fix_seats().get(body.get('seat'))
    if not case_ or not seat_:
        raise HTTPException(400, 'Pick a crash and a mind.')
    if _FIX['busy']:
        raise HTTPException(409, 'It is still working on one.')
    if run_ and run_.get('branch'):
        await asyncio.to_thread(_fa.drop, run_['branch'], run_.get('tree'))
    _FIX['busy'] = {'id': id_, 'by': seat_['name'], 'at': round(time.time())}
    asyncio.create_task(_fix_run(case_, seat_, seat_['name']))
    return {'busy': _FIX['busy']}


@router.get('/api/reputation/admin/ai/limits')
async def admin_ai_limits(request: Request):
    """🧪 Owner: the last free limit test on each LM Studio model."""
    _rs()._require_owner(request)
    return {'busy': _LIMITS['busy'], 'seats': [{'key': k_, 'name': v_['name']} for k_, v_ in _limit_seats().items()], 'results': sorted((_rs()._json_load(MODEL_LIMITS_PATH, {}) or {}).values(), key=lambda r_: -(r_.get('at') or 0))}


@router.post('/api/reputation/admin/ai/limits')
async def admin_ai_limits_run(request: Request):
    """🧪 Owner: one exam per proof on a free local model, with its live prompt or a set from the studio. No paid model and no money."""
    _rs()._require_owner(request)
    body = await request.json(); body = body if isinstance(body, dict) else {}; k_ = body.get('key'); seat_ = _limit_seats().get(k_)
    if not seat_:
        raise HTTPException(400, 'That model is not connected.')
    if _LIMITS['busy']:
        raise HTTPException(409, 'A test is still running.')
    set_ = str(body.get('set') or ''); text_ = ''
    if set_:
        text_ = next((x_['text'] for m_ in (await _rs()._studio_view())['models'] if m_['key'] == k_ for x_ in m_['sets'] if x_['set'] == set_), '')
        if not text_:
            raise HTTPException(400, 'unknown prompt set')
    _LIMITS['busy'] = {'key': k_, 'name': seat_['name'], 'set': set_ or 'none', 'at': round(time.time())}
    asyncio.create_task(_limits_run(k_, seat_, text_, _rs()._pstu.LABEL.get(set_, 'No overlay')))
    return {'busy': _LIMITS['busy']}


@router.get('/api/reputation/pool-rates')
async def pool_rates():
    """🪙 Public: today's typical yearly rates, for examples of what a stake could earn. Read from the same board the owner sees, at most every 5 minutes. Rates only, no wallets."""
    import grow_board as _gb
    return _gb.rates(await _rs()._grow_rows())
