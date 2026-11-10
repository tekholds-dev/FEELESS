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


# ── slice 4 (2026-11-10, up to 30 lines, comprehensions): moved by AST, every module global looked up on reputation_service at call time ──
@router.get('/api/reputation/admin/fuses/health')
async def fuse_health(request: Request):
    """Each published Fuse re-scored on live numbers vs a fresh champion of the same size."""
    rs = _rs()
    rs._require_admin(request)
    store = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
    raw = await rs._fuse_discover_pairs('solana')
    cands = {}
    for lens in rs._fuse.LENSES:
        for r in rs._fuse.discover(raw, lens, 'solana', now_ms=rs.time.time() * 1000, limit=12):
            cands.setdefault(r['pairAddress'], r)
    out = []
    for fid, f in store['fuses'].items():
        pairs = await rs._fuse_pairs(f['legs'])
        metas = {k: rs._fuse.leg_meta(v) for k, v in pairs.items()}
        if len(metas) < 2:
            out.append({'id': fid, 'name': f.get('name'), 'dead': True}); continue
        mine = rs._fuse.fitness(list(metas), metas)['fitness']
        champ = await rs.asyncio.to_thread(rs._fuse.evolve, {**dict(list(cands.items())[:40]), **metas}, len(metas), 10, 24, 'yield', 0.05, 150.0, 11, [list(metas)])
        out.append({'id': fid, 'name': f.get('name'), 'emoji': f.get('emoji'), **rs._hq.health(mine, champ['champions'][0]['fitness'] if champ['champions'] else 0),
                    'suggest': champ['champions'][0]['pools'] if champ['champions'] else []})
    return {'fuses': out}


@router.get('/api/reputation/admin/familia/rules')
async def admin_familia_rules(request: Request):
    """🏙 HQ › Familia control center: the rules (live + planned), what each one means, and the economy right now."""
    rs = _rs()
    rs._require_owner(request)
    import crews as _cr
    now = rs.time.time(); st = rs._json_load(rs.CREWS_PATH, {}); _cr._norm(st); w = st.get('world') or rs._fworld.blank(); r_ = rs._familia_rules()
    rs._fworld.set_rules(r_)
    crews_ = list((st.get('crews') or {}).values())
    banks = [int(rs._fcity.city_of(o, now)['bank']) for o in crews_]
    blocks = rs._fworld.block_ids(); own = rs._fworld.taken(w)
    cities = [{'key': k, 'name': n, 'plots': sum(1 for b in blocks if rs._fworld.borough_of(b) in bs), 'held': sum(1 for b in blocks if rs._fworld.borough_of(b) in bs and b in own)}
              for k, n, bs, _ in rs._fworld.CITIES]
    raids = list((w.get('raids') or {}).values())
    return {'rules': r_, 'live': list(rs._fworld.LIVE_RULES), 'range': rs._fworld.RULE_RANGE, 'prices': rs._fcity.price_rows(rs._bmk.ISLAND_MP),
            'economy': {'families': len(crews_), 'members': sum(len(o.get('members') or []) for o in crews_), 'bankMp': sum(banks), 'topBankMp': max(banks or [0]),
                        'houseMp': int(st.get('house') or 0), 'raidsLive': sum(1 for x in raids if x.get('status') == 'live'),
                        'raids24h': sum(1 for x in raids if now - float(x.get('at') or x.get('startAt') or 0) < 86400), 'cities': cities},
            'blockPrice': {b[0]: int(rs._fworld.BLOCK_MP * b[5]) for b in rs._fworld.BOROUGHS}}


@router.get('/api/reputation/admin/familia/unlocks')
async def admin_familia_unlocks(request: Request):
    """🌹 Owner: every badge part with its default unlock line, the line in force (your overrides) and the metrics they can read."""
    rs = _rs()
    import crews as _cr
    rs._require_owner(request); cfg = rs._crew_cfg()
    return {'metrics': _cr.METRICS, 'parts': {part: [{'key': o, 'label': lab, 'default': {'metric': m, 'min': n}, 'now': dict(zip(('metric', 'min'), _cr.unlock_rule(part, o, cfg)))}
                                                     for o, (lab, m, n) in opts.items()] for part, opts in _cr.PARTS.items()},
            'badgeUsd': rs._crew_badge_usd(cfg), 'createUsd': _cr.price('create', cfg), 'packUsd': _cr.price('seats', cfg)}


@router.get('/api/reputation/admin/circle/profiles')
async def circle_profiles(request: Request):
    """Owner: every Circle wallet with its FEELESS profile (so it can be searched + edited from the creator wallet)."""
    rs = _rs()
    rs._require_owner(request)
    ws = await rs._circle_wallets_live()
    profs = rs._profiles_load()['profiles']
    return {'wallets': [{'id': w.get('id'), 'address': w.get('address'), 'name': w.get('name'), 'blockchain': w.get('blockchain'),
                         'profile': rs.circle_profile_view(profs.get(w.get('address')) or {})} for w in ws]}


@router.get('/api/reputation/admin/rpc')
async def admin_rpc_status(request: Request):
    """Owner only: the keeper's RPC lanes — provider domain, in quota or not, minutes until it resets. Never a URL or a key."""
    rs = _rs()
    rs._require_owner(request)
    lanes = rs._rpc_quota_state()
    return {'lanes': lanes, 'needsKey': not lanes or all(x['spent'] for x in lanes), 'slots': [{'slot': k, 'set': any(x['slot'] == k for x in lanes)} for k in rs._chain.LANE_KEYS]}


@router.get('/api/reputation/admin/ai/rig')
async def admin_ai_rig(request: Request):
    """🎛 Owner: the model rig (ai_rig.py) — what FEELESS sends G4 / OSSY and the load command that matches it."""
    rs = _rs()
    rs._require_owner(request)
    import ai_rig as _rg
    rig_ = rs._rig_apply()
    models_ = {k_: rs._air.provider(rs.os.environ, k_, rs._ai_cfg()).get('model') for k_ in _rg.KEYS}
    v_ = rs._air.ROUTER.view(rs.os.environ, rs._ai_cfg())
    live_ = {r_['key']: {'state': r_.get('state'), 'lastMs': r_.get('lastMs')} for r_ in v_.get('providers') or []}
    lms_ = await rs._lms_states()
    rs._brain_load()
    set_ = rs._chat.get('settings') or {}
    return {**_rg.view(rig_, models_, lms_), 'live': live_,
            'chat': {'temp': set_.get('temp'), 'len': set_.get('len'), 'temps': list(_rg.CHAT_TEMPS), 'lens': _rg.CHAT_LENS}, 'reloading': sorted(rs._lms_reloading),
            'presets': _rg.presets_view(rs._json_load(rs.AI_PRESETS_PATH, {}))}


@router.get('/api/reputation/admin/ai/activity')
async def admin_ai_activity(request: Request):
    """📜 Owner: one timeline of everything the models did — reads, proposals + your decisions, playground creations, background reads."""
    rs = _rs()
    rs._require_owner(request)
    pr_ = (rs._json_load(rs.FUSE_HQ_PATH, {}) or {}).get('prime') or {}
    real_ = next((c_ for c_ in (pr_.get('cards') or {}).values() if (c_ or {}).get('real')), None) or {}
    mv_ = next((v_ for v_ in (rs._json_load(rs.OWNER_MOVES_PATH, {}) or {}).values() if isinstance(v_, dict)), {}).get('rows') or []
    rv_ = ((rs._office_state() or {}).get('judge') or {}).get('reviews') or []
    return {'items': rs._aic.activity(rs._ai['log'], rs._chat_props(), (rs._json_load(rs.AI_PLAY_PATH, {}) or {}).get('items'), rs._local_lane, n=120, g4=rs._g4_state()['log'][-60:],
                                   card=(real_.get('events') or [])[-40:], moves=mv_[-30:], reviews=rv_[-20:]), 'g4': rs._g4_view(), 'at': round(rs.time.time(), 1)}


@router.get('/api/reputation/admin/ai/playground')
async def admin_ai_playground(request: Request):
    """🧩 Owner: the code lab's proposals (newest first) + the parts of FEELESS a proposal may target."""
    rs = _rs()
    rs._require_owner(request)
    return {'items': [x for x in (rs._json_load(rs.AI_PLAY_PATH, {}) or {}).get('items') or [] if x.get('code')], 'targets': [[k, v[1], v[0]] for k, v in rs._play.TARGETS.items()]}   # the retired HTML playground's items have no code


@router.get('/api/reputation/admin/ai/chat')
async def admin_ai_chat_get(request: Request):
    rs = _rs()
    rs._require_owner(request)
    v_ = rs._air.ROUTER.view(rs.os.environ, rs._ai_cfg())
    live_ = next((r_ for r_ in v_.get('providers') or [] if r_.get('state') == 'ONLINE'), None)
    rs._brain_load()
    return {'history': rs._chat['th'].get('chat') or [], **rs._chat_extra(), 'build': rs._aic.build_view(rs._build_state()), 'proposals': rs._aic.view(rs._chat_props()), 'modes': list(rs._aic.MODES), 'learned': rs._chat_learned(),
            'brain': {'provider': (live_ or {}).get('label'), 'model': (live_ or {}).get('model'), 'ms': (live_ or {}).get('lastMs')},
            'providers': [{'key': r_['key'], 'label': r_['label'], 'state': r_['state'], 'model': r_.get('model')} for r_ in v_.get('providers') or [] if r_.get('enabled') and not r_.get('why')]}


@router.get('/api/reputation/admin/runners/funnel')
async def admin_runner_funnel(request: Request):
    """⚡ HQ › Engine, top of the screen: every coin the board sees right now against every gate — how many each gate stops, how
    many it stops ALONE (its real cost), and what the coins it stopped earlier went on to do. Plus the real card's own pipeline."""
    rs = _rs()
    rs._require_admin(request)
    rd = rs._json_load(rs.RUNNERS_PATH, {})
    now = rs.time.time()
    try:
        regret = rs._rn.gate_regret(rd.get('dropLog') or [], await rs._hq_prices([{'chainId': 'solana', 'pairAddress': e['pairAddress']} for e in (rd.get('dropLog') or [])[-120:] if e.get('pairAddress')]), now)
    except Exception:
        regret = []
    out = rs._rn.gate_funnel(list(rs._runner_cands), rs._runner_cfg(), regret)
    cards = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    real = next((c for c in cards.values() if c and c.get('real') and c.get('pipeline')), None)
    return {**out, 'dial': rd.get('cfgDial') or 'custom', 'at': now, 'card': real and {'label': real.get('label') or real.get('tpl'), **real['pipeline']}}


@router.get('/api/reputation/admin/runners/config')
async def runners_cfg_get(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {'cfg': rs._runner_cfg(), 'defaults': rs._rn.DEFAULT_CFG, 'ranges': rs._rn.CFG_RANGES, 'dial': rs._json_load(rs.RUNNERS_PATH, {}).get('cfgDial') or 'custom',
            'dials': {k: {'label': v['label'], 'why': v['why']} for k, v in rs._rn.ENGINE_DIALS.items()}, 'autoTune': rs._json_load(rs.RUNNERS_PATH, {}).get('autoTune') is not False}


@router.get('/api/reputation/admin/fuses/cards')
async def fuse_cards_admin(request: Request):
    """NFT tab: collection status + every published Fuse with its card, current holder (paid the cut) and owed amount."""
    rs = _rs()
    rs._require_admin(request)
    store = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
    views = await rs.asyncio.gather(*[rs._fuse_view(fid, f, store) for fid, f in store['fuses'].items()])
    pay = await rs.asyncio.gather(*[rs._fuse_pay_to(f) for f in store['fuses'].values()])
    rows = [{**v, 'card': store['fuses'][v['id']].get('card'), 'payTo': p} for v, p in zip(views, pay)]
    return {'collection': store.get('cardCollection'), 'rows': rows, 'site': rs._site(request)}


@router.get('/api/reputation/admin/fuses')
async def admin_fuses(request: Request):
    rs = _rs()
    rs._require_admin(request)
    store = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
    views = await rs.asyncio.gather(*[rs._fuse_view(fid, f, store) for fid, f in store['fuses'].items()])
    pay = await rs.asyncio.gather(*[rs._fuse_pay_to(store['fuses'][v['id']]) for v in views])
    return {'fuses': [{**v, 'payTo': p, 'card': store['fuses'][v['id']].get('card')} for v, p in zip(views, pay)], 'maxCreatorBps': rs._house()['fuseCreatorMaxBps'], 'maxLegs': rs._fuse.MAX_LEGS}


@router.get('/api/reputation/admin/vaults')
async def admin_vaults(request: Request, deposit: float = Query(10.0, gt=0, le=100000)):
    rs = _rs()
    rs._require_admin(request)
    d = rs._json_load(rs.VAULTS_PATH, {'vaults': {}})
    return {'vaults': await rs.asyncio.gather(*[rs._vault_view(vid, v, deposit) for vid, v in d['vaults'].items()]), 'maxPools': rs._vault.MAX_POOLS,
            'maxMgmtBps': rs.VAULT_MAX_MGMT_BPS, 'maxPerfBps': rs.VAULT_MAX_PERF_BPS, 'feeWallet': rs._fee_cfg().get('vaultFeeWallet') or ''}


@router.get('/api/reputation/admin/holders')
async def admin_holders(request: Request, asset: str = 'fee'):
    rs = _rs()
    rs._require_admin(request)
    mints = await rs._ecosystem_mints()
    mint = mints.get(asset) or (asset if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', asset) else None)
    if not mint:
        raise HTTPException(404, 'Unknown asset.')
    data = await rs._token_holders(mint)
    d = rs._admin_load(); bl = rs._block_load()['wallets']
    lp_like = set()
    for r in data['rows'][:3]:
        if r['pct'] > 20:
            lp_like.add(r['owner'])  # bonding curve / pool vaults usually dominate the top
    rows = [{**r, 'customBadges': list(d['badges'].get(r['owner'], {}).values()), 'blocked': rs._is_blocked(bl.get(r['owner'])),
             'likelyPool': r['owner'] in lp_like, 'isAdmin': r['owner'] in rs._admin_wallets()} for r in data['rows'][:2000]]
    return {**data, 'rows': rows, 'assets': list(mints.keys())}


@router.get('/api/reputation/admin/security/stores')
async def admin_stores(request: Request):
    """🗄 Every store under backend/data with its class, cap and state (ok · watch · over · stale snapshot · money kept whole). Read-only."""
    rs = _rs()
    import store_caps as _sc
    rs._require_admin(request)
    rows = []
    for f in rs.DATA_DIR.iterdir():
        try:
            if f.is_file():
                st_ = f.stat(); rows.append((f.name, st_.st_size, st_.st_mtime))
            elif f.is_dir():
                size_, mt_ = 0, 0.0
                for g in f.rglob('*'):
                    if g.is_file():
                        gs_ = g.stat(); size_ += gs_.st_size; mt_ = max(mt_, gs_.st_mtime)
                rows.append((f.name + '/', size_, mt_))
        except OSError:
            continue
    return _sc.audit(rows, rs.time.time())


@router.get('/api/reputation/admin/contract/golive')
async def contract_golive(request: Request):
    rs = _rs()
    rs._require_admin(request)
    g = rs._admin_load().get('golive') or {}
    return {'steps': {k: g.get(k) or {} for k in rs.GOLIVE_STEPS}, 'ready': all((g.get(k) or {}).get('done') for k in rs.GOLIVE_STEPS)}


@router.get('/api/reputation/admin/grow')
async def admin_grow(request: Request):
    """💰 Owner: the money board. It reads and measures. It never picks and never moves money."""
    rs = _rs()
    rs._require_owner(request)
    import grow_board as _gb
    return {'rows': [_gb.view(r_) for r_ in await rs._grow_rows()], 'at': round(rs._GROW['at'])}


@router.get('/api/reputation/admin/fuses/fees')
async def admin_fuse_fees(request: Request):
    """HQ › Fees: live $ from people fusing (Fuse card legs matched to the fee ledger by signature)."""
    rs = _rs()
    rs._require_admin(request)
    rows = [r for v in rs._json_load(rs.FEE_LEDGER_PATH, {}).values() for r in (v or [])]
    return rs._hq.fuse_fees(rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or [], rows, rs.time.time())


@router.get('/api/reputation/admin/fuses/fee-list')
async def admin_fuse_fee_list(request: Request):
    """HQ › Fuse › 💲 Fees: every card fee (buy · swap · sell · round packs) with totals — each row links its transaction."""
    rs = _rs()
    rs._require_admin(request)
    rows = [r for v in rs._json_load(rs.FEE_LEDGER_PATH, {}).values() for r in (v or [])]
    cfg = rs._fee_cfg()
    return {**rs._hq.fee_list(rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or [], rows), 'bundle': rs._hq.clean_bundle(cfg.get('bundle')), 'rounds': rs._rounds_cfg(), 'crews': {'createUsd': __import__('crews').price('create', cfg.get('crews')), 'packUsd': __import__('crews').price('seats', cfg.get('crews'))}, 'prepay': rs._hq.clean_prepay(cfg.get('prepay')),
            'swapBps': int(cfg['platformFeeBps'] or 0), 'example': rs._hq.fee_plan(cfg.get('bundle'), rs._rounds_cfg(), 3, 20, 10)}


@router.get('/api/reputation/admin/fees/balances')
async def admin_fee_balances(request: Request):
    rs = _rs()
    rs._require_admin(request)
    referral = str(rs._fee_cfg().get('referralAccount') or '').strip()
    if not referral:
        return {'referralAccount': '', 'accounts': [], 'totalAccounts': 0}
    accounts = []
    async with rs.httpx.AsyncClient(timeout=20) as http:
        for program in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
            result = await rs._rpc(http, 'getTokenAccountsByOwner', [referral, {'programId': program}, {'encoding': 'jsonParsed'}])
            for row in (result or {}).get('value', []):
                info = rs._parsed_info(row.get('account'))
                amount = info.get('tokenAmount') or {}
                if int(amount.get('amount') or 0) <= 0:
                    continue
                accounts.append({'tokenAccount': row.get('pubkey'), 'mint': info.get('mint'), 'amount': amount.get('uiAmountString') or '0', 'decimals': amount.get('decimals', 0), 'program': 'Token-2022' if program.startswith('Tokenz') else 'SPL Token'})
    return {'referralAccount': referral, 'accounts': accounts, 'totalAccounts': len(accounts),
            'note': 'Unclaimed on-chain referral-token balances. Claiming requires the referral authority wallet signature.'}


@router.get('/api/reputation/admin/treasury')
async def admin_treasury(request: Request):
    rs = _rs()
    admin = rs._require_admin(request)
    stats = await rs.wallet_stats(admin) if not admin.startswith('0x') else {}
    mints = await rs._ecosystem_mints()
    held = {}
    for aid, mint in mints.items():
        try:
            held[aid] = round(await rs._holding_usd(admin, mint), 2)
        except Exception:
            held[aid] = None
    recent = []
    try:
        async with rs.httpx.AsyncClient(timeout=15) as http:
            recent = [{'sig': s['signature'], 'at': s.get('blockTime'), 'ok': not s.get('err')} for s in (await rs._rpc(http, 'getSignaturesForAddress', [admin, {'limit': 12}])) or []]
    except Exception:
        pass
    return {'wallet': admin, 'sol': stats.get('sol'), 'holdingsUsd': held, 'recent': recent}


@router.get('/api/reputation/admin/seasons')
async def admin_seasons(request: Request):
    rs = _rs()
    rs._require_admin(request)
    d = rs._seasons()
    return {'seasons': d['seasons'], 'players': {k: len(v) for k, v in d['scores'].items()}}


@router.get('/api/reputation/admin/roles')
async def admin_roles(request: Request):
    rs = _rs()
    me = rs._require_admin(request)
    return {'owners': rs._owner_wallets(), 'grants': rs._granted(), 'youAreOwner': me in rs._owner_wallets(), 'roles': rs.ROLE_NAMES,
            'yourRole': rs._role_of(me), 'scopes': {k: sorted(v) for k, v in rs.ROLE_SCOPES.items()}}


@router.get('/api/reputation/admin/setup')
async def admin_setup(request: Request):
    rs = _rs()
    rs._require_admin(request)
    return {'keys': [{'key': k, 'name': n, 'why': w, 'required': req, 'set': bool(rs.os.environ.get(k, '').strip())} for k, n, w, req in rs.SETUP_KEYS],
            'launchRail': bool(rs._json_load(rs.LAUNCH_RAIL_PATH, {}).get('config')), 'owners': rs._owner_wallets()}


@router.get('/api/reputation/admin/reserve/{sid}')
async def admin_reserve_plan(request: Request, sid: str):
    rs = _rs()
    rs._require_admin(request)
    d = rs._seasons(); s = next((x for x in d['seasons'] if x['id'] == sid), None)
    if not s:
        raise HTTPException(404, 'Season not found.')
    return await rs._reserve_plan(s, d)


@router.get('/api/reputation/admin/badge-pools/{pid}/plan')
async def admin_badge_pool_plan(request: Request, pid: str):
    rs = _rs()
    rs._require_admin(request)
    pool = next((x for x in rs._pools()['pools'] if x['id'] == pid), None)
    if not pool:
        raise HTTPException(404, 'Pool not found.')
    return await rs._pool_plan(pool)


@router.get('/api/reputation/admin/perf/code-health')
async def perf_code_health(request: Request):
    """🧹 HQ › Lag catcher › Code health: the last scan (scripts/code-health.py · backend/code_health.py). Reads the cached file only."""
    rs = _rs()
    rs._require_admin(request)
    queued_ = [i_.get('title', '')[len(rs.CH_QUEUE_TAG):] for i_ in (rs._build_state().get('items') or []) if str(i_.get('title', '')).startswith(rs.CH_QUEUE_TAG) and i_.get('status') in ('queued', 'building')]
    return {**rs._json_load(rs.CODE_HEALTH_PATH, {}), 'scanning': rs._code_health_busy['on'], 'queued': queued_}


@router.get('/api/reputation/admin/perf')
async def perf_admin(request: Request, hours: float = Query(1, ge=0.1, le=24)):
    rs = _rs()
    rs._require_admin(request)
    since = rs.time.time() - hours * 3600
    import lag_advice as _la
    summ = rs.perf.summarize([s for s in rs._perf_samples if s['at'] >= since])
    loop_ = rs._loop_lag.WATCH.view()
    mach = await rs._machine_read()
    fx_ = (summ.get('fx') or {}) if isinstance(summ.get('fx'), dict) else {}
    return {**summ, 'forceLite': bool(rs._json_load(rs.PERF_CFG_PATH, {}).get('forceLite')), 'hours': hours,
            'advice': _la.advise(summ, loop_, mach), 'vitals': _la.vitals(summ, loop_, mach, fx_), 'machine': mach}


@router.get('/api/reputation/admin/fee-book')
async def admin_fee_book(request: Request, format: str = ''):
    """Every account's lifetime FEELESS fees, FeeBack earned, paid and still owed (CSV with ?format=csv)."""
    rs = _rs()
    rs._require_admin(request)
    rs._fee_totals_heal()
    rows = rs.fee_report.fee_book(rs._json_load(rs.FEE_TOTALS_PATH, {}), rs._json_load(rs.FEEBACK_PAID_PATH, {}))
    if format == 'csv':
        from fastapi.responses import Response
        cols = ['address', 'trades', 'volumeUsd', 'feeUsd', 'feeSol', 'feeUsdc', 'feeBackUsd', 'paidUsd', 'owedUsd', 'first', 'last']
        body = ','.join(cols) + '\n' + '\n'.join(','.join(str(r.get(c, '')) for c in cols) for r in rows)
        return Response(body, media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=feeless-fee-book.csv'})
    return {'accounts': len(rows), 'totalFeesUsd': round(sum(r['feeUsd'] for r in rows), 4), 'owedUsd': round(sum(r['owedUsd'] for r in rows), 4),
            'feeBackPct': rs.fee_report.FEEBACK_PCT, 'rows': rows[:500]}


@router.get('/api/reputation/admin/nft/holders/{key:path}')
async def nft_card_holders(request: Request, key: str):
    """Wallets that hold a card (badge or season card): the natural drop list for that card's collection."""
    rs = _rs()
    rs._require_admin(request)
    out = set()
    if key.startswith('badge:'):
        bid = key.split(':', 1)[1]
        out |= {a for a, items in (rs._admin_load().get('badges') or {}).items() if bid in items}
        out |= {a for a, (at, rec) in rs._badge_cache.items() if any(b.get('id') == bid for b in (rec or {}).get('badges', []))}
    else:
        out |= {a for a, items in rs._json_load(rs.COLLECTION_PATH, {}).items() if any(rs._collection_card_key(it) == key for it in items)}
    safe = rs._protected_wallets()
    return {'key': key, 'wallets': sorted(a for a in out if rs._re.match(rs._B58, a) and a not in safe)[:rs.nft_studio.MAX_DROP]}


@router.get('/api/reputation/admin/intel-desk')
async def intel_desk_view(request: Request):
    """Most wanted, crews, predicted next moves and the department's daily catch."""
    rs = _rs()
    rs._require_admin(request)
    d = await rs._desk_get()
    snap = {k: v for k, v in d['snap'].items() if k != 'index'}
    return {**snap, 'history': rs._json_load(rs.INTEL_DESK_PATH, {'history': []}).get('history', [])[-30:]}


@router.get('/api/reputation/admin/intel-desk/actor/{address}')
async def intel_desk_actor(request: Request, address: str):
    rs = _rs()
    rs._require_admin(request)
    d = await rs._desk_get()
    a = d['actors'].get(address)
    if not a:
        raise HTTPException(404, 'Not in the database (no strikes, no funding links, no bad launches).')
    ring = next((r for r in d['rings'] if address in r['members']), None)
    return {**rs.intel_desk.public_actor(a, rs.time.time()), 'fundedWallets': a['funded'][:50], 'mints': sorted(a['mints'])[:50], 'crew': ring}
