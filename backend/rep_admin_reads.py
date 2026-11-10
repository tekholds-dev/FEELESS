"""🧩 Q02 / SITE-5 slice 2 (2026-11-10): the owner's read-only admin views, moved out of reputation_service one safe slice at a time:
bugs, badge limits, the security guard, snapshots, ads, ideas, latency, and the AI provider / model views. No money, no trading, no writes.
Helpers stay in reputation_service and are looked up when a route runs (no import cycle), so a test that patches them still works."""
from fastapi import APIRouter, Request

router = APIRouter()


def _rs():
    import reputation_service
    return reputation_service


@router.get('/api/reputation/admin/badges/limits')
async def badge_limits_admin_get(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return rs._badge_limits()


@router.get('/api/reputation/admin/bugs')
async def admin_bugs(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return rs._json_load(rs.BUGS_PATH, {'bugs': []})


@router.get('/api/reputation/admin/security/guard')
async def admin_guard(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return rs._guard.view(rs._guard_s())


@router.get('/api/reputation/admin/snapshots')
async def admin_snapshots(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {'snaps': [{k: v for k, v in s.items() if k != 'rows'} | {'holders': len(s['rows'])} for s in rs._snaps()['snaps']][::-1]}


@router.get('/api/reputation/admin/ads')
async def admin_ads(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return rs._json_load(rs.ADS_PATH, {'ads': []})


@router.get('/api/reputation/admin/ideas')
async def admin_ideas(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {'ideas': rs._json_load(rs.IDEAS_PATH, {'ideas': rs._IDEA_SEED})['ideas']}


@router.get('/api/reputation/admin/latency')
async def admin_latency(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {**await rs._probe_latency(), 'alarms': [{'name': k, 'since': v['since'], 'posted': bool(v.get('posted'))} for k, v in rs._latency_bad.items()]}


@router.get('/api/reputation/admin/ai/providers')
async def admin_ai_providers(request: Request):
    """🧠 Owner only: the AI providers in their order — state, model, latency, failures. Never a key."""
    rs = _rs()
    rs._require_owner(request)
    return rs._ai_view()


@router.get('/api/reputation/admin/ai/models')
async def admin_ai_models(request: Request):
    """🧠 Owner: Brain › Models — every model's INFO · SERVER · INFERENCE · VITALS (what LM Studio really reports) + FEELESS's MCP."""
    rs = _rs()
    rs._require_owner(request)
    return await rs._model_desk_view()
