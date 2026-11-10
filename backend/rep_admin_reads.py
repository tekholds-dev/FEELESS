"""🧩 Q02 / SITE-5 slice 2 (2026-11-10): the owner's read-only admin views, moved out of reputation_service one safe slice at a time:
bugs, badge limits, the security guard, snapshots, ads, ideas, latency, and the AI provider / model views. No money, no trading, no writes.
Helpers stay in reputation_service and are looked up when a route runs (no import cycle), so a test that patches them still works."""
from fastapi import APIRouter, HTTPException, Query, Request  # noqa: F401

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


# ── slice 3 (2026-11-10): moved by AST, every module global looked up on reputation_service at call time ──
@router.get('/api/reputation/admin/fuses/rules')
async def admin_fuse_rules_get(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {'rules': rs._card_rules(), 'defaults': rs._hq.CARD_RULES, 'ranges': rs._hq.RULE_RANGES, 'feeback': await rs._feeback_book()}


@router.get('/api/reputation/admin/fuses/auto-yield')
async def admin_auto_yield_get(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return rs._json_load(rs.FUSE_HQ_PATH, {}).get('autoYieldDefault') or {'on': False, 'at': rs._hq.YIELD_DEFAULT_AT}


@router.get('/api/reputation/admin/fuse-wallet/report')
async def fuse_wallet_report(request: Request, card: str = Query('', max_length=40)):
    """🩺 Owner: what each real run did (from the audit ledger) + the flaws it shows, each with its fix. Read-only."""
    rs = _rs()
    rs._require_owner(request)
    return {'reports': await rs._fw_reports(card)}


@router.get('/api/reputation/admin/providers')
async def admin_providers(request: Request):
    """🔑 Owner only: which provider keys are set, by name. Never a value. Calls nothing."""
    rs = _rs()
    rs._require_owner(request)
    import provider_ready as _pr
    return _pr.status(rs.os.environ)


@router.get('/api/reputation/admin/ai-key')
async def admin_ai_key_status(request: Request):
    """🔑 Owner only: which AI providers have a key — provider, set, the last 4 characters. Never a key."""
    rs = _rs()
    rs._require_owner(request)
    return rs._aik.status(rs.os.environ)


@router.get('/api/reputation/admin/ai/seat')
async def admin_ai_seat(request: Request):
    """🧠 Owner: G4's own seat — its minute thoughts (action · why · vitals · the agents' pressure · Qwen's word) and its paper / real record."""
    rs = _rs()
    rs._require_owner(request)
    return rs._g4_view()


@router.get('/api/reputation/admin/agent-slots')
async def admin_agent_slots(request: Request):
    """🎟 Owner: agent slots open / taken / left (≤ 1,000 across all users)."""
    rs = _rs()
    rs._require_owner(request)
    try:
        r_ = await rs._ai_http().get('http://127.0.0.1:5088/api/cats/supply', timeout=6)
        return r_.json()
    except Exception:
        raise HTTPException(503, 'Fee service did not answer.')


@router.get('/api/reputation/admin/colony')
async def admin_colony(request: Request):
    """🐝 Owner: the colony pot — its Circle wallet, live value, the locked principal, what may pay out this epoch and the honey split."""
    rs = _rs()
    rs._require_owner(request)
    return await rs._colony_view()


@router.get('/api/reputation/admin/ai/prompts')
async def admin_ai_prompts(request: Request):
    """🎭 Owner: every model's live context (the layers it reads + its window), record, diagnosis and four prompt sets."""
    rs = _rs()
    rs._require_owner(request)
    return await rs._studio_view()


@router.get('/api/reputation/admin/agents/office')
async def admin_agents_office(request: Request):
    """🏢 The office in ONE payload (mission · agents · current case · pipeline · positions · execution · learning · judge · performance).
    It only returns what the last agent pass and tier tick left in memory: a page view runs no desk, no scan, no quote, no wallet call."""
    rs = _rs()
    rs._require_admin(request)
    return rs._office.get('payload') or {'cold': True, 'at': 0}


@router.get('/api/reputation/admin/agents')
async def admin_agents(request: Request):
    """🤖 HQ › Agents + the swap-in 🤖 Agents list (creator / admin wallets): the four agents, their scorecards, the live table (every agent's
    word per coin), the paper desk and the road to real money. Read-only; only the creator may switch the real-card feed (POST)."""
    rs = _rs()
    rs._require_admin(request)
    return rs.Response(rs._agents_page_body(), media_type='application/json')


@router.get('/api/reputation/admin/agents/log')
async def admin_agents_log(request: Request, hours: int = Query(24, ge=1, le=168)):
    """🧾 The agent desk's war log (calls, GO vs control, deaths + lessons, ideas, best / worst, calibration) as data + Markdown to export."""
    rs = _rs()
    rs._require_admin(request)
    log, md = rs._pd.war_log(rs._agents_mem.get(), rs.time.time(), hours)
    return {'log': log, 'md': md}


@router.get('/api/reputation/admin/runners/suggest')
async def admin_runner_suggest(request: Request):
    """⚡ Stronger engine found? Every setting where the live config is weaker than the recommended one (with why), plus each
    lane's self-tuning record. Apply = POST /admin/runners/config with the merged values (one click in HQ)."""
    rs = _rs()
    rs._require_admin(request)
    d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    cfg = rs._runner_cfg(); pr = rs._rn.lane_proofs(d['rounds'], d['paths'], rs.time.time(), cfg)
    return {'suggestions': rs._rn.suggest_cfg(cfg), 'lanes': pr, 'weights': rs._rn.lane_weights(pr), 'cfg': cfg}


@router.get('/api/reputation/admin/fuses/verdict')
async def fuse_verdict(request: Request):
    """🧾 Owner: what's working and what's not, before anything is scrapped — every engine judged on its own record (tier card runs,
    strategies, runner lanes, engine dials, playground clocks, sim configs, real runs). Fresh on open; the background keeps it hourly."""
    rs = _rs()
    rs._require_owner(request)
    out = await rs._verdict_build(real=True)
    out['history'] = (rs._json_load(rs.VERDICT_PATH, {}).get('history') or [])[-48:]
    return out


@router.get('/api/reputation/admin/fuses/sim')
async def pg_sim_view(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return rs._json_load(rs.PG_SIM_PATH, {})


@router.get('/api/reputation/admin/fuses/pg-battles')
async def pg_battles_get(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return rs._pg_battle_view(rs._json_load(rs.RUNNERS_PATH, {}))


@router.get('/api/reputation/admin/quests')
async def admin_quests(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {'badges': rs._quest_defs(), 'defaults': rs._quests.DEFAULTS, 'overrides': rs._json_load(rs.QUESTS_PATH, {}), 'metrics': rs._quests.METRICS,
            'tiers': list(rs._quests.TIER_XP), 'daily': rs._quests.DAILY, 'weekly': rs._quests.WEEKLY, 'stats': await rs._quest_rarity(), 'season': rs._quest_season()}


@router.get('/api/reputation/admin/security/defence')
async def admin_defence(request: Request):
    """🛡 The learned defence: live blocks (and why), learned rules, tarpits, every incident with its plain abuse report. Never a counter-attack."""
    rs = _rs()
    rs._require_admin(request)
    return rs._def.view(rs._def_s())


@router.get('/api/reputation/admin/stash')
async def admin_stash(request: Request):
    """🧊 Owner: what the Collective Stash holds, how much room is left and its web."""
    rs = _rs()
    rs._require_owner(request)
    root = rs.DATA_DIR / 'stash'
    return {'stats': await rs.asyncio.to_thread(rs._stash.stats, root), 'web': await rs.asyncio.to_thread(rs._stash.web, root), 'mirror': bool(rs.os.environ.get('STASH_R2_BUCKET'))}


@router.get('/api/reputation/admin/py-agents')
async def admin_py_agents(request: Request):
    """🐍 Owner: the five validators, their real record and what the local minds propose. It changes no code."""
    rs = _rs()
    rs._require_owner(request)
    import py_agents as _pa
    return {'seats': _pa.record(rs._cpool.load(rs.POOL_PATH), _pa.filed(rs._json_load(rs.DATA_DIR / 'feecats.json', {}))), 'learned': _pa.learned(rs.DATA_DIR, rs._json_load(rs.DATA_DIR / 'git_manifests' / 'collective_sort.json', {})), **_pa.load(rs.DATA_DIR)}


@router.get('/api/reputation/admin/collective')
async def admin_collective(request: Request):
    """🪙 Owner: the Pool ledger, every setting and where the money stands."""
    rs = _rs()
    rs._require_owner(request)
    return await rs._collective_view()


@router.get('/api/reputation/admin/fees')
async def admin_fees_get(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {'fees': {**rs._fee_cfg(), 'bundle': rs._hq.clean_bundle(rs._fee_cfg().get('bundle')), 'rounds': rs._rounds_cfg(), 'house': rs._house()}, 'limits': {'minBps': 0, 'maxBps': rs.SWAP_MAX_BPS, 'ultraMinBps': rs.JUP_MIN_BPS, 'ultraMaxBps': rs.JUP_MAX_BPS, 'priorityMaxLamports': rs.PRIORITY_MAX_LAMPORTS}}


@router.get('/api/reputation/admin/treasury/routes')
async def routes_get(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return rs._json_load(rs.ROUTES_PATH, {'routes': []})


@router.get('/api/reputation/admin/circle/status')
async def circle_status(request: Request):
    rs = _rs()
    rs._require_owner(request)
    return await rs._circle('GET', '/status')


@router.get('/api/reputation/admin/circle/wallets')
async def circle_wallets(request: Request):
    rs = _rs()
    rs._require_owner(request)
    return {'wallets': await rs._circle_wallets_live()}


@router.get('/api/reputation/admin/perf/loop')
async def perf_loop(request: Request, reset: int = 0):
    rs = _rs()
    rs._require_admin(request)
    out = rs._loop_lag.WATCH.view()
    if reset:
        rs._loop_lag.WATCH.reset()
    return out


@router.get('/api/reputation/admin/money-pulse')
async def admin_money_pulse(request: Request, fresh: int = 0):
    """ONE snapshot for every HQ money card: fee accounts, admin, season reserves, badge pools and Circle
    wallets (one batched chain read + Circle in parallel), their payout plans, a preflight of everything trading
    depends on, and nudges. Owners also get Circle (and calling it keeps the Circle service alive)."""
    rs = _rs()
    me = rs._require_admin(request)
    owner = me in rs._owner_wallets()
    key = 'owner' if owner else 'admin'
    hit = rs._pulse_cache.get(key)
    if hit and not fresh and rs.time.time() - hit[0] < 15:
        return {**hit[1], 'cached': True}
    out = await rs._money_pulse_build(me, owner)
    rs._pulse_cache[key] = (rs.time.time(), out)
    return out


@router.get('/api/reputation/admin/circle/destinations')
async def circle_destinations(request: Request):
    """Where a Circle wallet may send: HQ wallets + ones the owner saved."""
    rs = _rs()
    rs._require_owner(request)
    return {'destinations': await rs._circle_destinations()}


@router.get('/api/reputation/admin/circle/meta')
async def circle_meta_get(request: Request):
    rs = _rs()
    rs._require_owner(request)
    return rs._json_load(rs.CIRCLE_META_PATH, {})
