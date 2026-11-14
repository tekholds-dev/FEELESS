"""🛡 AGX-7 routes: the owner's guardrail switches. Owner only (`_require_owner` = the creator wallet, signed HQ session); everyone else 403/401.
The rules are `guardrails` (pure, restrict-only); this file only reads and writes data/guardrails.json."""
import time

from fastapi import APIRouter, Request

import guardrails as _gr

router = APIRouter()


def _rs():
    import reputation_service
    return reputation_service


def _path(rs):
    return rs.DATA_DIR / 'guardrails.json'


@router.get('/api/reputation/admin/guardrails')
async def guardrails_view(request: Request):
    """🛡 Every switch with today's number, and the locked hard limits."""
    rs = _rs()
    rs._require_owner(request)
    g, by, at = _gr.read(_path(rs))
    return _gr.view(g, by=bool(by), at=at)


@router.post('/api/reputation/admin/guardrails')
async def guardrails_set(request: Request):
    """Flip a switch / set a value: {key: {on, value}}. Values only go down from today's number; nothing here can loosen a rule."""
    rs = _rs()
    me = rs._require_owner(request)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    try:
        g = _gr.clean(body if isinstance(body, dict) else {}, _gr.read(_path(rs))[0])
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    _gr.save(_path(rs), g, me, time.time())
    return _gr.view(g, by=True, at=round(time.time()))
