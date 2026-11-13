"""🧩 Q02 / SITE-5 slice 5 (2026-11-10): small public read routes (no admin, no money, no writes), moved out of reputation_service.
Helpers stay there and are looked up when a route runs (no import cycle), so a test that patches them still works."""
from fastapi import APIRouter, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401

router = APIRouter()


def _rs():
    import reputation_service
    return reputation_service


@router.get('/api/reputation/rpc/health')
async def rpc_health():
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=6) as http:
        rows = await rs.asyncio.gather(*(rs._ping_chain(http, c) for c in ['solana', *rs.CHAIN_RPC_DEFAULTS]))
    return {'chains': rows, 'explorerKey': bool(rs.os.environ.get('ETHERSCAN_API_KEY'))}


@router.get('/api/reputation/globe-tokens')
async def globe_tokens():
    rs = _rs()
    return rs._globe_cache['data'] or {'tokens': [], 'minMarketCap': rs.GLOBE_MIN_MC, 'warming': True}


@router.get('/api/reputation/push/vapid')
async def push_vapid():
    rs = _rs()
    return {'publicKey': rs._vapid()['public']}


@router.get('/api/reputation/push/status')
async def push_status(endpoint: str):
    rs = _rs()
    entry = rs._push_load()['subs'].get(rs._sub_id({'endpoint': endpoint}))
    if not entry:
        return {'subscribed': False}
    return {'subscribed': True, 'watching': len(entry['watch']), 'prefs': entry['prefs'], 'recent': entry.get('sent', [])[-10:][::-1]}


@router.get('/api/reputation/calls/recent')
async def recent_calls(room: Optional[str] = None, pair: Optional[str] = None, mint: Optional[str] = None, limit: int = Query(30, ge=1, le=100)):
    rs = _rs()
    calls = [rs._call_view(c) for c in rs._calls_load()['calls'].values() if (not room or c['room'].startswith(room)) and (not pair or c['pairAddress'] == pair) and (not mint or c.get('mint') == mint)]
    calls.sort(key=lambda c: -c['at'])
    return {'calls': calls[:limit]}


@router.get('/api/reputation/calls/leaderboard')
async def caller_board(days: int = Query(7, ge=1, le=90), room: Optional[str] = None):
    # Profiles, the league and the feed all ask for this: rebuild at most every 20s.
    rs = _rs()
    hit = rs._board_cache.get((days, room))
    if hit and rs.time.time() - hit[0] < 20:
        return hit[1]
    out = rs._build_caller_board(days, room)
    rs._board_cache[(days, room)] = (rs.time.time(), out)
    return out


@router.get('/api/reputation/crowd/elite-flow')
async def crowd_elite_flow():
    """Coins FEELESS's proven traders bought in the last 6h (counts only — no wallets exposed). Rebuilt every ~10 min."""
    rs = _rs()
    if rs._crowd_cache['data'] and rs.time.time() - rs._crowd_cache['at'] < 900:
        return rs._crowd_cache['data']
    return await rs._crowd_build()


@router.get('/api/reputation/fuses/rules')
async def fuse_rules_public():
    """What traders can pick (auto-profit levels) and the Fee-Back / swap / Arena rules HQ set."""
    rs = _rs()
    return rs._card_rules()


@router.get('/api/reputation/fuses/yield-math')
async def fuse_yield_math():
    """Fuse vs Vault on live pools: what $1 earns from LP fees (Vault) vs what price moves did to $1 (Fuse)."""
    rs = _rs()
    return rs._hq.yield_math(await rs._fuse_candidates())


@router.get('/api/reputation/meme-terms')
async def meme_terms(term: str = ''):
    rs = _rs()
    """📖 Today's trench language: new / spiking terms with meaning (known slang) or what the engine learned (ticker wave /
    chat slang), plus how many terms it knows. ?term= explains one word."""
    st = rs._json_load(rs.MEME_PATH, {})
    if term:
        return rs._mt.explain(st, term[:24])
    now = rs.time.time()
    return {'terms': rs._mt.trending(st, now), 'learned': len(st.get('firstSeen') or {}), 'glossary': len(rs._mt.GLOSSARY),
            'today': sum(((st.get('days') or {}).get(str(rs._mt.day_of(now))) or {}).values()), 'at': now}


@router.get('/api/reputation/fuses/pump-callouts')
async def fuse_pump_callouts():
    rs = _rs()
    """📣 Pump's own callouts, read from the public feeds its site uses: today's TOP callouts by the caller's profit, the newest calls and
    one row per called coin (callers, eyes on it, the cap it was called at, the multiple since). Other people's calls — a read, never advice."""
    b = await rs._pump_calls_build()
    return {'top': b.get('top') or [], 'latest': (b.get('latest') or [])[:20], 'coins': (b.get('coins') or [])[:60], 'n': b.get('n') or 0,
            'at': rs._pump_calls.get('ok') or None, 'source': 'pump.fun callouts', 'callers': rs._pc.leaders(rs._pump_calls.get('callers') or {}),
            'alertCapK': int(rs._fuse._f(((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('callAlert') or {}).get('capK'))), 'alertCaps': list(rs._pc.RUSH_CAPS_K)}


@router.get('/api/reputation/social-feed/counts')
async def social_feed_counts(ids: str, address: str = ''):
    """💬 Likes + comment counts for the posts on screen — ONE batched read per timeline refresh (≤ 60 ids)."""
    rs = _rs()
    return {'counts': rs._fsoc.counts(rs._json_load(rs.FEED_SOCIAL_PATH, {}), ids.split(','), rs.primary_of(address) if address else None)}


@router.get('/api/reputation/fuses/trench-brain')
async def fuse_trench_brain():
    """🧠 What the trench brain knows: coins judged / watching, how they ended, the walk-forward proof, best + worst learned cells."""
    rs = _rs()
    b = rs._brain_state()
    return {**(b['sum'] or {}), 'ready': rs._brain_ready()}


@router.get('/api/reputation/fuses/learn')
async def fuses_learn():
    """🧠 What the engine learned from the real card's own exits: how many lessons, the buckets that paid most / lost most (coin moves in %)."""
    rs = _rs()
    st = rs._json_load(rs.REAL_LEARN_PATH, {})
    return {'n': len(st.get('pieces') or []), **rs._rl.lessons(rs._real_table())}


@router.get('/api/reputation/fuses/list-proof')
async def fuses_list_proof():
    rs = _rs()
    """📏 Which picker list pays: each list's own record of coins held 1 hour (median, % up, n). A live list without its own record
    yet borrows the nearest callout record, labelled `src`. A record, never a promise."""
    return {'lists': rs._list_records()}


@router.get('/api/reputation/fuses/proof')
async def fuses_proof():
    rs = _rs()
    """🧾 Public: what the real-money cards did (confirmed swaps + the engine's reason + tx), their verified records, the setups
    side by side and the live 24h duels. Read-only; a losing record reads as a losing record."""
    return await rs._proof_build()


@router.get('/api/reputation/familia-fuse')
async def familia_fuse():
    """⚔ The Family Fuse fights (public, light: the Fuse tab's strip) — marked at live prices first."""
    rs = _rs()
    now = rs.time.time()
    await rs._ffuse_tick(now)
    return rs._ffuse_view(rs._json_load(rs.CREWS_PATH, {}), None, now)


@router.get('/api/reputation/crew-wars')
async def crews_wars():
    """⚔ Public: every family war (live first, then the ones with a bell set, open call-outs, the last results) + alliances. Points only."""
    rs = _rs()
    st = rs._json_load(rs.CREWS_PATH, {}) or {}
    now = rs.time.time(); crews_ = st.get('crews') or {}
    ws = rs._fwar.board(st, now)[:30]
    live = [w for w in ws if w['state'] in (rs._fwar.LIVE, rs._fwar.DONE)]
    mem = {m for w in live for t in (w.get('teams') or {}).values() for m in t}
    pcs = rs._crew_pieces(list(mem), now) if mem else {}
    return {'wars': [rs._fwar.view(w, crews_, pcs, now) for w in ws],
            'alliances': [{'a': (crews_.get(a) or {}).get('tag'), 'b': (crews_.get(b) or {}).get('tag'), 'at': t} for a, b, t in st.get('alliances') or []],
            'asks': [{'from': (crews_.get(a) or {}).get('tag'), 'to': (crews_.get(b) or {}).get('tag'), 'at': t} for a, b, t in st.get('allyAsks') or []],
            'rules': {'stake': [rs._fwar.STAKE_MIN, rs._fwar.STAKE_MAX], 'hours': list(rs._fwar.HOURS), 'teamMax': rs._fwar.TEAM_MAX, 'chestStart': rs._fwar.CHEST_START,
                      'note': 'A pot is family points, never money. Every member signs their own trades; a war counts each team member\'s verified trades inside the window.'},
            'at': round(now)}


@router.get('/api/reputation/rep-markets')
async def rep_markets(address: str = ''):
    rs = _rs()
    """🛡 Public: every live YES / NO market (crowd price + the rep-weighted price, ⚡ smart split), the last results, the week's top callers and —
    with an address — your chip bank. Free weekly chips only; nothing is bought, sent or cashed out."""
    st = rs._json_load(rs.REP_MARKETS_PATH, {}) or {}
    me = rs.primary_of(address) if address else None
    ws = {s_['w'] for m in st.get('markets') or [] for s_ in m['stakes']}
    return rs._repm.board(st, rs.time.time(), me, rs._rep_of(ws))


@router.get('/api/reputation/fuses/my-edge')
async def fuses_my_edge():
    rs = _rs()
    """🎯 Public: how the owner's hand picks did by entry type (mid-pump / thin / dip with volume) — price result of confirmed fills, fees apart.
    A record, never a promise; the pick warning quotes it and never blocks."""
    return rs._owner_edge_rec()


@router.get('/api/reputation/fuses/contenders')
async def fuses_contenders():
    """Public: the divisions, their ranked coins (score + cited parts, ▲▼, streak) and who is ⏭ next up for a card seat."""
    rs = _rs()
    return await rs._contenders_build()


@router.get('/api/reputation/alliances')
async def alliances_list(wallet: str = ''):
    """🤝 Every alliance and union: names, sizes, short wallets."""
    rs = _rs()
    return rs._alliance_view(wallet)


@router.get('/api/reputation/cats-ai')
async def cats_ai():
    """🐱🤝 FeeCat's last AI read: what BOTH duo models agreed she should skip (`avoid`) or bank (`exit`), by pairAddress. Read-only, memory."""
    rs = _rs()
    out_ = {k_: rs._feecat_ai.get(k_) for k_ in ('read', 'avoid', 'exit', 'split', 'why', 'models')}
    return out_


@router.get('/api/reputation/health')
async def health():
    rs = _rs()
    store = rs._load()
    now = rs.time.time()
    rpc_status = [{
        'endpoint': rs._chain_rpc_mod.provider_of(endpoint), 'dedicated': endpoint == rs._dedicated,
        'cooling_down': rs._rpc_cooldown_until.get(endpoint, 0) > now,
    } for endpoint in rs.RPC_POOL]
    return {
        'ok': True, 'creators': len(store['creators']), 'mints': len(store['mints']),
        'rpcPool': rpc_status, 'usingDedicatedRpc': bool(rs._dedicated),
    }


@router.get('/api/reputation/support')
async def support_board(wallet: Optional[str] = None):
    """🛟 Public support hub: reports as a cleaned, importance-sorted grid (no stack traces, wallets or security text) + community polls."""
    rs = _rs()
    import support as _sp
    st_ = rs._json_load(rs.SUPPORT_PATH, {'polls': [], 'plus': {}})
    bugs_ = rs._json_load(rs.BUGS_PATH, {'bugs': []}).get('bugs') or []
    rows_ = _sp.board(bugs_, st_.get('plus') or {})
    mine_ = [k_ for k_, v_ in (st_.get('plus') or {}).items() if wallet and wallet in v_]
    reacts_ = {k_: {'up': sum(1 for x_ in v_.values() if x_ > 0), 'down': sum(1 for x_ in v_.values() if x_ < 0), 'mine': v_.get(wallet or '', 0)} for k_, v_ in (st_.get('reacts') or {}).items()}
    return {'reacts': reacts_, 'comments': {k_: v_[-30:] for k_, v_ in (st_.get('comments') or {}).items()},
            'ideas': sorted((st_.get('ideas') or [])[-200:], key=lambda i_: -(sum(1 for x_ in ((st_.get('reacts') or {}).get(i_['id']) or {}).values() if x_ > 0))),
            'reports': rows_, 'mine': mine_, 'polls': _sp.polls_board(st_.get('polls') or [], wallet), 'ladder': [{'at': a_, 'key': k_, 'label': l_} for a_, k_, l_ in _sp.LADDER],
            'counts': {'open': sum(1 for b_ in bugs_ if b_.get('status', 'open') == 'open'), 'fixing': sum(1 for b_ in bugs_ if b_.get('status') == 'fixing'),
                       'fixed': sum(1 for b_ in bugs_ if b_.get('status') == 'fixed'), 'polls': len(st_.get('polls') or [])}}


@router.get('/api/reputation/presence')
async def presence_read(a: str = Query('', max_length=2400)):
    """🟢 Up to 50 wallets → online · away · offline (invisible reads as offline)."""
    rs = _rs()
    now = rs.time.time()
    return {x_: rs._pres.status(rs._presence, x_, now) for x_ in [y_.strip() for y_ in a.split(',') if y_.strip()][:50]}


@router.get('/api/reputation/radar')
async def radar():
    rs = _rs()
    return {'watching': len(rs._radar['pairs']), 'events': rs._radar['events'][:40], 'whales': rs._radar['whales'][:40]}


@router.get('/api/reputation/notifications')
async def notifications(address: str, session: str):
    rs = _rs()
    me = rs._session_or_401(address, session)
    box = rs._legacy_sniper_dedupe(rs._notif_box(me))
    return {'unread': sum(1 for n in box if not n['read']), 'items': box[:60]}


@router.get('/api/reputation/dm-settings')
async def dm_settings(address: str, session: str):
    rs = _rs()
    return rs._dm_pref(rs._session_or_401(address, session))


@router.get('/api/reputation/site')
async def site_config():
    rs = _rs()
    return {'publicUrl': (rs._admin_load().get('site') or {}).get('publicUrl') or ''}


@router.get('/api/reputation/shop')
async def shop(address: str = ''):
    rs = _rs()
    un, rec = rs._unlocks(address) if address else ({}, {})
    return {'items': rs.SHOP, 'points': rec.get('total', 0), 'spent': rec.get('spent', 0), 'unlocks': un, 'boosts': rec.get('boostCredits', 0), 'tickets': rec.get('tickets', 0)}


@router.get('/api/reputation/wars')
async def wars(address: str = ''):
    rs = _rs()
    d = rs._json_load(rs.WARS_PATH, {})
    wk = d.get(rs._war_week()) or {'members': {}}
    pts = rs._pts()
    week_start = rs._week_start()
    score = {f: 0 for f in rs.FACTIONS}
    count = {f: 0 for f in rs.FACTIONS}
    for a, f in wk['members'].items():
        gained = sum(l['points'] for l in (pts.get(a) or {}).get('log', []) if l['points'] > 0 and l['at'] >= week_start)
        score[f] += gained; count[f] += 1
    mine = wk['members'].get(rs.primary_of(address)) if address else None
    last = d.get(rs.time.strftime('%G-W%V', rs.time.gmtime(rs.time.time() - 7 * 86400))) or {}
    return {'week': rs._war_week(), 'factions': [{'id': f, 'label': l, 'score': score[f], 'members': count[f]} for f, l in rs.FACTIONS.items()],
            'mine': mine, 'lastWinner': last.get('winner'), 'endsAt': rs._week_start() + 7 * 86400}


@router.get('/api/reputation/snipe-risk')
async def snipe_risk(mints: str):
    rs = _rs()
    out = {}
    for m in mints.split(',')[:60]:
        hit = rs._intel_cache.get(m)
        if not hit or not hit[1]:
            continue
        d = hit[1]
        snip, bund, top10 = len(d.get('sniperWallets') or []), len(d.get('bundledWallets') or []), d.get('top10Pct') or 0
        funded_by_repeat = len(d.get('flaggedFunders') or {})
        risk = min(100, round(snip * 2 + bund * 5 + max(0, top10 - 20) + funded_by_repeat * 15))
        out[m] = {'risk': risk, 'level': 'high' if risk >= 60 else 'medium' if risk >= 30 else 'low', 'snipers': snip, 'bundled': bund, 'top10': top10, 'repeatFunders': funded_by_repeat}
    return {'risk': out}


@router.get('/api/reputation/chat/session/check')
async def session_check(address: str, session: str):
    rs = _rs()
    owner = rs.session_address(session)
    return {'valid': bool(owner) and rs.primary_of(owner) == rs.primary_of(address)}


@router.get('/api/reputation/darkside')
async def darkside(limit: int = Query(12, ge=1, le=50)):
    """The other side of the ledger: the wallets and money behind snipes, bundles and rugs."""
    rs = _rs()
    hit = rs._dark_cache.get(limit)
    if hit and rs.time.time() - hit[0] < 20:
        return hit[1]
    data = await rs._darkside_compute(limit)
    rs._dark_cache[limit] = (rs.time.time(), data)
    return data


@router.get('/api/reputation/fees/public')
async def fees_public():
    rs = _rs()
    cfg = rs._fee_cfg()
    integ = cfg.get('lifiIntegrator') or rs.os.environ.get('LIFI_INTEGRATOR', '').strip()
    lifi = {'integrator': integ, 'fee': round(cfg['lifiFeeBps'] / 10000, 4)} if integ and cfg.get('lifiFeeBps') else None
    return {'platformFeeBps': cfg['platformFeeBps'], 'tierDiscountPct': cfg['tierDiscountPct'], 'promo': cfg.get('promo'), 'lifi': lifi,
            'feelessIntoFee': True, 'note': 'Buying $FEE, FEECAT or rFEE with SOL, USDC or USDT is fee-free. Selling them and every other swap, buy, sell or bridge pays the platform fee.'}


@router.get('/api/reputation/metas')
async def metas_public():
    rs = _rs()
    return await rs.metas(refresh=False)


@router.get('/api/reputation/shields')
async def shields_list():
    rs = _rs()
    d = rs._json_load(rs.SHIELD_PATH, {})
    return {'shields': [{'mint': m, 'creator': s['creator'], 'status': 'broken' if s['breaches'] else ('active' if rs.time.time() - s['at'] < s['lockDays'] * 86400 else 'completed'),
                         'breaches': len(s['breaches']), 'at': s['at']} for m, s in sorted(d.items(), key=lambda x: -x[1]['at'])][:100]}


@router.get('/api/reputation/season/drops')
async def season_drops():
    rs = _rs()
    d = rs._seasons(); s = rs._current_season(d)
    if not s:
        return {'weeks': []}
    now = rs.time.time(); col = rs._json_load(rs.COLLECTION_PATH, {})
    holders = {}
    for items in col.values():
        for it in items:
            holders[it['id'].rsplit(':', 1)[0]] = holders.get(it['id'].rsplit(':', 1)[0], 0) + 1
    return {'season': s['id'], 'accent': s['accent'], 'rarities': rs.RARITIES,
            'weeks': [{**w, 'status': 'distributed' if w['end'] <= now else 'live' if w['start'] <= now else 'upcoming',
                       'players': len(d['scores'].get(f"{s['id']}:w{w['week']}") or {}), 'holders': holders.get(f"{s['id']}:w{w['week']}", 0)} for w in rs._season_weeks(s)]}


@router.get('/api/reputation/local/update-log')
async def local_update_log(request: Request):
    rs = _rs()
    rs._require_admin(request)   # 🔒 audit #4: through the dev proxy every LAN caller looked local
    if not rs._guard.is_local(request):
        raise rs.HTTPException(403, 'Local only.')
    try:
        return {'log': rs.Path('/tmp/feeless-update.log').read_text()[-4000:]}
    except OSError:
        return {'log': ''}


@router.get('/api/reputation/agent-pass/rules')
async def agent_pass_rules():
    rs = _rs()
    return await rs._agent_pass_rules()


@router.get('/api/reputation/season/reserve')
async def season_reserve(address: str = ''):
    """Public: the live season's reserve pot and this wallet's projected share."""
    rs = _rs()
    d = rs._seasons(); s = rs._current_season(d)
    if not s or not s.get('reserveWallet') or not float(s.get('badgeRewardPct') or 0):
        return {'active': False}
    hit = rs._reserve_pub_cache.get(s['id'])
    if not hit or rs.time.time() - hit[0] > 60:
        hit = (rs.time.time(), await rs._reserve_plan(s, d)); rs._reserve_pub_cache[s['id']] = hit
    plan = hit[1]
    me = rs.reserve_pool.wallet_share(plan, rs.primary_of(address)) if address else None
    return {'active': True, 'season': plan['season']['name'], 'pct': plan['pct'], 'potSol': plan['potSol'], 'wallets': len(plan['rows']),
            'weights': plan['weights'], 'me': me}


@router.get('/api/reputation/perf/config')
async def perf_config():
    rs = _rs()
    return {'forceLite': bool(rs._json_load(rs.PERF_CFG_PATH, {}).get('forceLite'))}


@router.get('/api/reputation/rep')
async def rep_batch(addresses: str = Query('', max_length=4000)):
    """Batch lookup for chat names, holder lists, trade tickets: {address: {score, level, label, top}}."""
    rs = _rs()
    out = {}
    for a in dict.fromkeys(x.strip() for x in addresses.split(',') if x.strip()):
        if len(out) >= 60:
            break
        if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a):
            out[a] = rs._quick_rep(a)
    return {'reps': out}


@router.get('/api/reputation/intel/check')
async def intel_check(addresses: str = Query('', max_length=6000)):
    """Which known ruggers / snipers / funders (and crews) are in this list of wallets. Used by FeeCat, shield, chat."""
    rs = _rs()
    d = await rs._desk_get()
    wanted = [a for a in dict.fromkeys(x.strip() for x in addresses.split(',')) if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a)][:150]
    return rs.intel_desk.check(d['snap']['index'], d['rings'], wanted)


@router.get('/api/reputation/cards')
async def cards_catalog():
    """Every FEELESS card with its look, lore, holders and money (what it earns + earned so far per holder)."""
    rs = _rs()
    return {'cards': list(rs._cards_all().values()), 'designs': list(rs.badge_cards.DESIGNS), 'rarities': list(rs.badge_cards.RARITIES)}


@router.get('/api/reputation/music/search')
async def music_search(q: str = Query(..., min_length=2, max_length=80)):
    """YouTube videos for the search (+ Spotify tracks when the owner set a Spotify key — they play through YouTube)."""
    rs = _rs()
    yt = await rs._yt_search(q.strip())
    try:
        sp = await rs._spotify_search(q.strip())
    except Exception:
        sp = None
    return {'q': q, 'youtube': yt, 'spotify': sp, 'spotifyOn': sp is not None}


@router.get('/api/reputation/music/top')
async def music_top():
    """🔥 Top played right now: Apple Music's most-played chart (US, public RSS, 1h cache). Tap one → it is found on YouTube and played."""
    rs = _rs()
    hit = rs._music_cache.get(('top',))
    if hit and rs.time.time() - hit[0] < 3600:
        return hit[1]
    try:
        async with rs.httpx.AsyncClient(timeout=10) as http:
            doc = (await http.get('https://rss.marketingtools.apple.com/api/v2/us/music/most-played/25/songs.json')).json()
        out = {'source': 'Apple Music · most played (US)', 'rows': rs._music.apple_top(doc)}
    except Exception:
        return (hit[1] if hit else {'source': '', 'rows': []})
    rs._music_cache[('top',)] = (rs.time.time(), out)
    return out


@router.get('/api/reputation/music/next')
async def music_next(title: str = Query('', max_length=160), skip: str = Query('', max_length=2000), titles: str = Query('', max_length=4000)):
    """▶ Next when the queue runs out: another song by the same artist that is not already queued (like YouTube's autoplay)."""
    rs = _rs()
    artist = rs._music.artist_of(title)
    rows = await rs._yt_search(f'{artist} songs' if artist else 'top songs this week')
    pick = rs._music.pick_next(rows, [s for s in skip.split(',') if s], [t for t in titles.split('|') if t])
    if not pick:
        pick = rs._music.pick_next(await rs._yt_search('top songs this week'), [s for s in skip.split(',') if s], [t for t in titles.split('|') if t])
    return {'next': pick, 'artist': artist}


@router.get('/api/reputation/token/{chain}/{address}')
async def token_reputation(chain: str, address: str):
    rs = _rs()
    store = rs._load()
    mint_key = f'{chain}:{address}'
    mint_state = store['mints'].get(mint_key)
    if not mint_state or not mint_state.get('creator'):
        return {'creator': None, 'score': None, 'badge': 'unproven'}
    ckey = rs._creator_key(chain, mint_state['creator'])
    entry = store['creators'].get(ckey)
    if not entry:
        return {'creator': mint_state['creator'], 'score': None, 'badge': 'unproven'}
    out = {'creator': entry['address'], **rs.score_creator(entry)}
    return {**out, **rs._hygiene(entry['address'], out)}


@router.get('/api/reputation/room-sentiment/{chain}/{pair}')
async def room_sentiment(chain: str, pair: str):
    """Community mood for a coin: last-24h posts and posters in its Bulls vs Bears rooms."""
    rs = _rs()
    part = lambda v: rs._re.sub(r'%[0-9a-fA-F]{2}', '_', rs.quote(str(v), safe=''))
    rooms = rs._chat_load()['rooms']; since = (rs.time.time() - 86400) * 1000
    out = {}
    for side in ('bulls', 'bears', 'trenches'):
        msgs = [m for m in rooms.get(f'coin-{part(chain)}-{part(pair)}-{side}', []) if m.get('ts', 0) >= since and not m.get('system')]
        out[side] = {'posts': len(msgs), 'posters': len({m.get('identity') or m.get('address') for m in msgs})}
    # Posters weigh double: one loud wallet can't swing the mood alone.
    bull = out['bulls']['posts'] + 2 * out['bulls']['posters']; bear = out['bears']['posts'] + 2 * out['bears']['posters']
    out['bullPct'] = round(bull / (bull + bear) * 100) if bull + bear else None
    return out


@router.get('/api/reputation/fuses')
async def fuses_list():
    rs = _rs()
    store = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
    rows = await rs.asyncio.gather(*[rs._fuse_view(fid, f, store) for fid, f in store['fuses'].items() if f.get('enabled', True)])
    return {'fuses': sorted(rows, key=lambda r: -rs._hq.trust_rank(r['score']['points'], r['trust']['buyers'], r['trust']['trusted']))}


@router.get('/api/reputation/fuses/score/{address}')
async def fuse_score_get(address: str):
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        raise rs.HTTPException(400, 'Bad address.')
    return await rs._fuse_score(address)


@router.get('/api/reputation/familia-block/{cid}')
async def familia_block_visit(cid: str):
    """🏙 Visit a family's market block (public): which markets stand, built or under construction, a value band — never a balance."""
    rs = _rs()
    import crews as _cr
    st = rs._json_load(rs.CREWS_PATH, {}); _cr._norm(st); c = (st.get('crews') or {}).get(cid)
    if not c:
        raise rs.HTTPException(404, 'No such family.')
    return await rs._fblock_view(c)


@router.get('/api/reputation/hq/pair/{code}')
async def hq_pair_poll(code: str):
    """The computer's poll: waiting · expired · the session, handed over once."""
    rs = _rs()
    return rs._hqp.take(rs._hqp_store, code[:64], rs.time.time())


@router.get('/api/reputation/quests/{address}')
async def quest_board(address: str):
    rs = _rs()
    s = await rs._quest_summary(address)
    r = await rs._quest_rarity()
    eds = rs._json_load(rs.EDITIONS_PATH, {})
    left = {b['id']: max(0, rs.EDITION_CAP - len(eds.get(b['id']) or [])) for b in s['badges']}   # edition hunt: numbered spots left
    return {**s, 'rarity': r['pct'], 'holders': r['holders'], 'editionsLeft': left, 'metricsLabels': rs._quests.METRICS}


@router.get('/api/reputation/perks/{address}')
async def perks(address: str):
    rs = _rs()
    tier, usd = await rs._perk_tier(address)
    nxt = next((t for t in rs.PERK_TIERS if t['tier'] == tier + 1), None)
    return {'address': address, 'tier': tier, 'feeUsd': round(usd, 2), 'tiers': rs.PERK_TIERS,
            'next': {'name': nxt['name'], 'needUsd': round(max(0, nxt['minUsd'] - usd), 2)} if nxt else None}


@router.get('/api/reputation/identity/{address}')
async def identity(address: str):
    rs = _rs()
    return {'address': address, 'primary': rs.primary_of(address), 'linked': rs.linked_of(address)}


@router.get('/api/reputation/rugshield/{mint}')  # its own path: /shield/{mint} is the launch-promise Shield
async def rug_shield(mint: str):
    """ok / caution / danger with the reasons. danger = the trader must tick 'I understand' before signing."""
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', mint):
        raise rs.HTTPException(400, 'Bad mint.')
    if mint in rs.FEE_SETTLEMENT_MINTS:
        return {'mint': mint, 'level': 'ok', 'reasons': []}
    try:
        if mint in set((await rs._ecosystem_mints()).values()):
            return {'mint': mint, 'level': 'ok', 'reasons': [], 'official': True, 'note': 'Official FEELESS coin.'}
    except Exception:
        pass
    try:
        async with rs.httpx.AsyncClient(timeout=10) as http:
            intel, auth = await rs.asyncio.gather(rs.token_intel('solana', mint), rs._mint_authorities(http, mint))
    except rs.HTTPException:
        return {'mint': mint, 'level': 'unknown', 'reasons': ['On-chain check unavailable right now.']}
    creator = intel.get('creator')
    if creator in rs._protected_wallets():
        intel = {**intel, 'creator': None}   # FEELESS wallets are never the risk
    return {'mint': mint, **rs.shield_verdict(intel, rs._block_load()['wallets'], auth or {}, rs._quick_rep(creator) if creator and creator not in rs._protected_wallets() else None)}


@router.get('/api/reputation/resolve/{query}')
async def resolve_profile(query: str):
    """@handle, display name or wallet address → profile address (for search + mentions)."""
    rs = _rs()
    q = query.strip().lstrip('@')
    if rs._re.match(r'^0x[0-9a-fA-F]{40}$', q):
        return {'address': rs.primary_of(q), 'handle': rs.handle_of(rs.primary_of(q))}
    if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', q):
        # Only wallets become profiles; token mints / pools stay coin searches.
        try:
            async with rs.httpx.AsyncClient(timeout=10) as http:
                info = await rs._rpc(http, 'getAccountInfo', [q, {'encoding': 'base64'}])
            owner = ((info or {}).get('value') or {}).get('owner')
        except Exception:
            owner = None
        if owner in (None, '11111111111111111111111111111111'):
            return {'address': rs.primary_of(q), 'handle': rs.handle_of(rs.primary_of(q))}
        raise rs.HTTPException(404, 'That address is a token or program, not a wallet.')
    ql = q.lower()
    for a, v in rs._profiles_load()['profiles'].items():
        if (v or {}).get('handle') == ql or str((v or {}).get('displayName') or '').lower() == ql:
            return {'address': a, 'handle': rs.handle_of(a)}
    raise rs.HTTPException(404, 'No profile with that name.')


@router.get('/api/reputation/img')
async def img_proxy(u: str):
    rs = _rs()
    if not rs._re.match(r'^https://[\w.-]+/', u) or len(u) > 600:
        raise rs.HTTPException(400, 'Bad image URL.')
    hit = rs._img_cache.get(u)
    if hit and rs.time.time() - hit[0] < 3600:
        return rs._Resp(content=hit[1], media_type=hit[2], headers={'Cache-Control': 'public, max-age=3600'})
    try:
        async with rs.httpx.AsyncClient(timeout=10, follow_redirects=True) as http:
            r = await http.get(u, headers={'accept': 'image/*'})
    except Exception:
        raise rs.HTTPException(502, 'Image host unreachable.')
    ctype = r.headers.get('content-type', '').split(';')[0]
    b = r.content[:12]
    sniff = 'image/png' if b.startswith(b'\x89PNG') else 'image/jpeg' if b.startswith(b'\xff\xd8') else 'image/gif' if b[:4] == b'GIF8' else 'image/webp' if b[:4] == b'RIFF' and b[8:12] == b'WEBP' else None
    ctype = sniff or ctype
    if r.status_code != 200 or not sniff or len(r.content) > 2_500_000:
        raise rs.HTTPException(415, 'Not a usable image.')
    if len(rs._img_cache) > 800:
        rs._img_cache.clear()
    rs._img_cache[u] = (rs.time.time(), r.content, ctype)
    return rs._Resp(content=r.content, media_type=ctype, headers={'Cache-Control': 'public, max-age=3600'})


@router.get('/api/reputation/follows/{address}')
async def follows(address: str, viewer: str = ''):
    rs = _rs()
    a = rs.primary_of(address)
    d = rs._fol()['following']
    following = d.get(a, [])
    followers = [x for x, lst in d.items() if a in lst]
    return {'address': a, 'followers': len(followers), 'following': len(following), 'followersList': followers[-30:][::-1], 'followingList': following[-30:][::-1],
            'viewerFollows': bool(viewer) and a in d.get(rs.primary_of(viewer), [])}


@router.get('/api/reputation/shield/{mint}')
async def shield_get(mint: str):
    rs = _rs()
    s = rs._json_load(rs.SHIELD_PATH, {}).get(mint)
    if not s:
        return {'mint': mint, 'status': 'none'}
    return await rs._shield_check(mint, s)


@router.get('/api/reputation/collection/{address}')
async def collection(address: str):
    rs = _rs()
    items = rs._json_load(rs.COLLECTION_PATH, {}).get(rs.primary_of(address), [])
    return {'address': rs.primary_of(address), 'items': sorted(items, key=lambda x: -x['at'])}


@router.get('/api/reputation/version')
async def version():
    """Which code this machine is running vs GitHub main, so a stale copy is obvious (footer shows it)."""
    rs = _rs()
    hit = rs._version_cache.get('v')
    if hit and rs.time.time() - hit[0] < 30:
        return hit[1]
    if rs.time.time() - rs._version_cache.get('fetched', 0) > 300:
        rs._version_cache['fetched'] = rs.time.time()
        await rs._git('fetch', '-q', 'origin', 'main', timeout=20)
    head, branch, behind, dirty = await rs.asyncio.gather(rs._git('rev-parse', '--short', 'HEAD'), rs._git('rev-parse', '--abbrev-ref', 'HEAD'),
                                                       rs._git('rev-list', '--count', 'HEAD..origin/main'), rs._git('status', '--porcelain', '--untracked-files=no'))
    v = {'head': head or None, 'branch': branch or None, 'behind': int(behind) if behind.isdigit() else None,
         'dirty': [l[3:] for l in dirty.splitlines()][:8], 'fix': 'bash scripts/update.sh'}
    rs._version_cache['v'] = (rs.time.time(), v)
    return v


@router.get('/api/reputation/launch-rail')
async def launch_rail():
    rs = _rs()
    r = rs._json_load(rs.LAUNCH_RAIL_PATH, {})
    return {'ready': bool(r.get('config')), **r, 'tab': rs.launch_meta.clean_tab(r.get('tab') or rs.launch_meta.TAB_DEFAULT), 'costs': rs.launch_meta.clean_costs(r.get('costs')), 'siteUrl': rs.os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/')}


@router.get('/api/reputation/pump-profile/{mint}')
async def pump_profile_get(mint: str):
    rs = _rs()
    """🟢 What Pump says about a coin (logo, links, creator, graduated, cap vs its ATH, 1h volume, replies, live). 60s cache; {} when
    Pump has no record. Read-only, public data."""
    if not (mint.isalnum() and 30 <= len(mint) <= 48):
        raise rs.HTTPException(400, 'Not a mint.')
    hit = rs._PUMP_PROFILE.get(mint)
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1] or {}
    import launchpad_board as _lb
    try:
        async with rs.httpx.AsyncClient(timeout=6, headers={'User-Agent': 'Mozilla/5.0'}) as http:
            r = await http.get(f'https://frontend-api-v3.pump.fun/coins-v2/{mint}')
        prof = _lb.pump_profile(r.json() if r.status_code == 200 else None, rs.time.time() * 1000)
    except Exception:
        return (hit[1] if hit else None) or {}      # Pump busy: the last copy, never an error wall
    if len(rs._PUMP_PROFILE) > 600:
        rs._PUMP_PROFILE.clear()
    rs._PUMP_PROFILE[mint] = (rs.time.time(), prof)
    rs._pump_links_put(mint, prof)
    return prof or {}


@router.get('/api/reputation/coin-profile/{mint}')
async def coin_profile_get(mint: str):
    rs = _rs()
    return rs._json_load(rs.COIN_PROFILES_PATH, {}).get(mint) or {}


@router.get('/api/reputation/token-meta/{name}')
async def token_meta_get(name: str):
    rs = _rs()
    from fastapi.responses import FileResponse
    if not rs._re.match(r'^[a-f0-9]{32}\.json$', name) or not (rs.TOKEN_META_DIR / name).exists():
        raise rs.HTTPException(404, 'Not found')
    return FileResponse(rs.TOKEN_META_DIR / name, media_type='application/json')


@router.get('/api/reputation/rugproof/{mint}')
async def rugproof(mint: str):
    rs = _rs()
    if not rs._re.match(rs._B58, mint):
        raise rs.HTTPException(400, 'Solana mint required.')
    hit = rs._rugproof_cache.get(mint)
    if hit and rs.time.time() - hit[0] < 600:
        return hit[1]
    async with rs.httpx.AsyncClient(timeout=10) as http:
        info = await rs._rpc(http, 'getAccountInfo', [mint, {'encoding': 'jsonParsed'}])
    parsed = rs._parsed_info((info or {}).get('value'))
    if not parsed:
        raise rs.HTTPException(404, 'Not a token mint.')
    launch = (rs._load().get('feelessLaunches') or {}).get(mint) or {}
    rail = rs._json_load(rs.LAUNCH_RAIL_PATH, {})
    reg = [p for p in rs._json_load(rs.POOLS_REG_PATH, {'pools': []})['pools'] if p['mint'] == mint]
    if any(p.get('locked') for p in reg):
        lp = {'ok': True, 'how': 'FEELESS pool with liquidity permanently locked'}
    elif launch.get('rail') == 'feeless' and launch.get('config') == rail.get('config') and float((rail.get('params') or {}).get('lockedLpPct', 100)) >= 100:
        lp = {'ok': True, 'how': 'FEELESS rail locks 100% of graduated liquidity forever'}
    else:
        lp = {'ok': False, 'how': 'No verified permanent liquidity lock known to FEELESS'}
    out = {'mint': mint, 'mintRevoked': not parsed.get('mintAuthority'), 'freezeRevoked': not parsed.get('freezeAuthority'), 'lpLocked': lp}
    out['rugProof'] = out['mintRevoked'] and out['freezeRevoked'] and lp['ok']
    rs._rugproof_cache[mint] = (rs.time.time(), out)
    return out


@router.get('/api/reputation/nft-meta/{name}')
async def nft_meta(name: str, request: Request):
    """Public metadata JSON: {id}.json for the collection, {id}-{n}.json for item n."""
    rs = _rs()
    m = rs._re.match(r'^([a-f0-9]{12})(?:-(\d{1,6}))?\.json$', name)
    c = m and next((x for x in rs._nft_load()['collections'] if x['id'] == m.group(1)), None)
    if not c:
        raise rs.HTTPException(404, 'Not found')
    site = rs.os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/') or str(request.base_url).rstrip('/')
    return rs.nft_studio.item_json(c, site, int(m.group(2))) if m.group(2) else rs.nft_studio.collection_json(c, site)


@router.get('/api/reputation/reactions')
async def reactions(room: str, voter: Optional[str] = None):
    rs = _rs()
    msgs = rs._react_load()['rooms'].get(room[:120], {})
    return {'reactions': {mid: {e: {'count': len(v), 'mine': bool(voter and voter in v)} for e, v in em.items() if v} for mid, em in msgs.items()},
            'emojis': rs.REACTIONS}


@router.get('/api/reputation/profile/{address}')
async def get_profile(address: str):
    rs = _rs()
    p = rs._profiles_load()['profiles'].get(address)
    board = await rs.caller_board(days=30)
    caller = next((r for r in board['rows'] if r.get('callerAddress') == address), None)
    return {'address': address, 'profile': {k: v for k, v in p.items() if k != 'nameLock'} if p else p, 'caller': caller, 'verified': rs.is_verified(address)}


@router.get('/api/reputation/profiles')
async def get_profiles(addresses: str):
    rs = _rs()
    d = rs._profiles_load()['profiles']
    return {'profiles': {a: {**{k: d[a].get(k) for k in ('displayName', 'avatarUrl', 'accent', 'mood', 'featuredBadges', 'ring', 'nameFx', 'handle')}, 'verified': rs.is_verified(a)} for a in addresses.split(',')[:100] if a in d}}


@router.get('/api/reputation/fuses/search')
async def fuses_search(request: Request, q: str = Query(..., min_length=2, max_length=60)):
    rs = _rs()
    """Pool picker for the Fuse builder: live pools with the meta a builder needs (depth, volume, APR est., turnover).
    A pasted CA does a direct token lookup (search can miss fresh coins). HQ sees EVERY pool (thin ones flagged, not hidden)."""
    is_ca = bool(rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', q.strip()))
    async with rs.httpx.AsyncClient(timeout=8) as http:
        try:
            url = f'https://api.dexscreener.com/tokens/v1/solana/{q.strip()}' if is_ca else 'https://api.dexscreener.com/latest/dex/search'
            got = (await http.get(url, params=None if is_ca else {'q': q})).json()
            pairs = got if isinstance(got, list) else (got or {}).get('pairs') or []
        except Exception:
            pairs = []
        if not pairs:   # 📡 DexScreener silent (outage / not indexed yet) → Jupiter's data for the same CA or ticker, same pair shape
            try:
                key = rs._jkeys.read_key(rs.os.environ) or ''
                base, hdr = ('https://api.jup.ag/tokens/v2/search', {'x-api-key': key}) if key else (rs._launchpad_board.JUP_SEARCH, {})
                jr = await http.get(base, params={'query': q.strip().lstrip('$')}, headers=hdr)
                toks = jr.json() if jr.status_code == 200 else []
                pairs = [p_ for p_ in (rs._launchpad_board.jup_pair(t) for t in (toks if isinstance(toks, list) else [])[:12]) if p_]
            except Exception:
                pairs = []
    pairs = [rs._fuse.with_curve(p) for p in pairs]   # 🆕 a coin still on Pump's launch curve is tradable: its curve depth stands in for a pool
    admin = rs._is_admin_req(request)
    real = {p.get('pairAddress') for p in rs._fuse.real_pools(pairs)}
    src = pairs if admin else [p for p in pairs if p.get('pairAddress') in real]
    rows = [{'chainId': p.get('chainId'), 'pairAddress': p.get('pairAddress'), **rs._fuse.leg_meta(p), **({'thin': True} if p.get('pairAddress') not in real else {}), **({'curve': True} if p.get('curve') else {})}
            for p in src[:20] if p.get('chainId') == 'solana']
    qu = q.strip().upper().lstrip('$')
    if qu in rs._fuse.MAJOR_ALIASES or any(qu == v[0].upper() for v in rs._fuse.MAJORS.values()):   # 'BTC' → the real ones, always
        have = {r['pairAddress'] for r in rows}
        rows += [r for r in await rs._majors_rows() if r['pairAddress'] not in have]
    hidden = sum(1 for p in pairs if p.get('chainId') == 'solana' and p.get('pairAddress') not in real) if not admin else 0
    seen_ = {r.get('mint'): r for r in rs._runner_cands}
    for r in rows:   # ⚠ what the runner board already knows about this coin's creator (cache only — informs a pick, never blocks it)
        w = rs._creator_warn(seen_.get(r.get('baseAddress')))
        if w:
            r['warn'] = w
    return {'pools': rs._fuse.mark_real(rows, qu)[:15], 'hidden': hidden,
            'why': ('That coin has no tradable pool yet (still on its launch curve, or no volume) — a card can only swap into a live pool.' if is_ca and not rows
                    else f'{hidden} pool{"s" if hidden != 1 else ""} hidden: no volume or a parked pool.' if hidden and not rows else '')}


@router.get('/api/reputation/fuses/creators')
async def fuse_creators():
    """Fuse creator season (this week, from Monday 00:00 UTC): ranked by buyers' real P&L. 60s cache."""
    rs = _rs()
    hit = rs._fuse_holders_cache.get('creators')
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1]
    now = rs.time.time(); since = now - ((rs.time.gmtime(now).tm_wday * 86400) + now % 86400)
    pos = [x for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or [] if (x.get('at') or 0) >= since and x.get('fuseId')]
    px = await rs._hq_prices([leg for x in pos for leg in x['legs']]) if pos else {}
    fz = {fid: {'creator': f.get('creator'), 'name': f.get('name')} for fid, f in rs._json_load(rs.FUSES_PATH, {'fuses': {}})['fuses'].items()}
    board = rs._hq.creator_board([{**rs._hq.position_pnl(x, px), 'wallet': x['wallet'], 'fuseId': x['fuseId'], 'at': x.get('at')} for x in pos], fz, since)
    out = {'since': since, 'endsAt': since + 7 * 86400, 'minBuyers': rs._hq.MIN_BUYERS, 'rows': [{**r, 'handle': rs.handle_of(r['creator'])} for r in board[:30]]}
    rs._fuse_holders_cache['creators'] = (rs.time.time(), out)
    return out


@router.get('/api/reputation/fuses/replay/{kind}/{cid}')
async def fuse_replay(kind: str, cid: str):
    """▶ Card replay: each coin's last 24h path (15m) + the card's moments (buys, take-profits, swaps, compounds) as markers."""
    rs = _rs()
    now = rs.time.time(); legs, marks = [], []
    if kind == 'user':
        pos = next((x for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or [] if x['id'] == cid), None)
        if not pos:
            raise rs.HTTPException(404, 'No such card.')
        legs = [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'entry': round(rs._fuse._f(l.get('usd')) / rs._fuse._f(l.get('tokens0') or l.get('tokens')), 12) if rs._fuse._f(l.get('tokens0') or l.get('tokens')) else None,
                 'at': l.get('addedAt') or pos.get('at')} for l in pos['legs']]
        marks = [{'at': e.get('at'), 'kind': e.get('kind'), 'label': f"{e.get('kind')} {e.get('symbol') or ''}".strip()} for e in pos.get('events') or [] if e.get('at')]
        marks.insert(0, {'at': pos.get('at'), 'kind': 'open', 'label': 'card opened'})
    elif kind in ('lit', 'round'):
        rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': []})
        c = next((x for x in (rd.get('litCards') or []) + (rd.get('rounds') or []) if str(x.get('id')) == cid), None)
        if not c:
            raise rs.HTTPException(404, 'No such card.')
        legs = [{'pairAddress': p.get('pairAddress') or p['mint'], 'symbol': p.get('symbol'), 'entry': p.get('entry'), 'at': p.get('swappedIn') or c['at']} for p in c['picks']]
        marks = [{'at': c['at'], 'kind': 'open', 'label': 'lit' if kind == 'lit' else 'round dealt'}] + [{'at': s['at'], 'kind': 'swap', 'label': f"swap ${s['out'].get('symbol')} → ${s['in'].get('symbol')}"} for s in c.get('swaps') or []]
    elif kind == 'mega':
        f = (rs._json_load(rs.FUSES_PATH, {'fuses': {}}).get('fuses') or {}).get(cid)
        if not f:
            raise rs.HTTPException(404, 'No such card.')
        legs = [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'entry': (f.get('basePrices') or {}).get(l['pairAddress']), 'at': f.get('createdAt')} for l in f['legs']]
    elif kind == 'auto':
        ac = rs._json_load(rs.RUNNERS_PATH, {}).get('autoCard') or {}
        if cid not in (ac.get('id'), 'arena-pick'):
            raise rs.HTTPException(404, 'No such card.')
        legs = [{k: l.get(k) for k in ('pairAddress', 'symbol', 'entry')} | {'at': ac['at']} for l in ac['legs']]
        marks = [{'at': ac['at'], 'kind': 'open', 'label': 'arena dealt it'}]
    elif kind == 'feecat':
        fc = await rs._feecat_card()
        legs = [{k: l.get(k) for k in ('pairAddress', 'symbol', 'entry', 'at')} for l in (fc or {}).get('legs') or []]
        marks = [{'at': l['at'], 'kind': 'buy', 'label': f"🐱 bought ${l['symbol']}"} for l in legs if l.get('at')]
    else:
        raise rs.HTTPException(400, 'Unknown card kind.')
    legs = legs[:12]
    series = await rs.asyncio.gather(*[rs._series_24h(l['pairAddress']) for l in legs])
    return {'from': now - 86400, 'to': now, 'legs': [{**l, 'series': s} for l, s in zip(legs, series)],
            'markers': [m for m in marks if rs._fuse._f(m.get('at')) >= now - 86400]}


@router.get('/api/reputation/fuses/battles/{address}')
async def fuse_my_battles(address: str):
    """⚔ A wallet's cards in Arena battles: the live ones (with both sides' move since the bell) + the last results."""
    rs = _rs()
    me = rs.primary_of(address); mine = set(rs.linked_of(me)) | {me}
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    keys = {f"user:{x['id']}": x.get('name') or 'Fuse card' for x in d.get('positions') or [] if x['wallet'] in mine}
    view = rs._battle_view(rs._arena_mega_cache.get('data') or [], rs.time.time())
    live = [{**p_, 'mine': 'a' if p_['a']['key'] in keys else 'b'} for p_ in view['pairs'] if p_['a']['key'] in keys or p_['b']['key'] in keys]
    past = [{**r, 'mine': 'a' if r.get('aKey') in keys else 'b', 'won': r.get('winnerKey') in keys} for r in reversed(d.get('battleLog') or [])
            if r.get('aKey') in keys or r.get('bKey') in keys][:20]
    rec = {'w': sum(1 for r in past if r['won']), 'l': sum(1 for r in past if not r['won'] and not r.get('draw')), 'd': sum(1 for r in past if r.get('draw'))}
    return {'live': live, 'past': past, 'record': rec, 'endsAt': view.get('endsAt'), 'cards': len(keys)}


@router.get('/api/reputation/fuses/prebuilt')
async def fuses_prebuilt(request: Request, legs: int = Query(3, ge=2, le=12), budget: float = Query(20, ge=1, le=10000)):
    rs = _rs()
    """Discover rail: the best basket for EACH strategy right now (bred from live pools), with that strategy's arena record.
    Traders get 3-pool baskets; HQ may ask for up to 12. Cached 5 min per size."""
    legs = legs if rs._is_admin_req(request) else min(legs, rs._fuse.USER_MAX_LEGS)
    # Breeding buckets (fee drag + size guard depend on size): $1 · $5 · $20 · $100. The buyer's exact amount is used at Fuse in.
    key = (legs, 1 if budget < 3 else 5 if budget < 12 else 20 if budget < 60 else 100)
    hit = rs._fuse_prebuilt_cache.get(key)
    if hit and rs.time.time() - hit[0] < 300:
        return hit[1]
    metas, sol_usd = await rs.asyncio.gather(rs._fuse_candidates(), rs._sol_usd_live())
    board = {r['style']: r for r in rs._hq.arena_board([rs._hq.arena_value(e, {}, rs.time.time()) for e in rs._json_load(rs.FUSE_HQ_PATH, {}).get('arena') or []])}
    seed = int(rs.time.time() // 300)
    runs = await rs.asyncio.gather(*[rs.asyncio.to_thread(rs._fuse.evolve, metas, legs, 14, 28, st, key[1] / sol_usd, sol_usd, seed) for st in rs._fuse.STYLES])
    dead = rs._retired(list(board.values()))   # ☠ strategies the arena proved to lose never reach a trader's rail
    cards = [{'style': st, 'arena': board.get(st), **rs._champ_view(ev['champions'][0], metas)} for st, ev in zip(rs._fuse.STYLES, runs) if ev['champions'] and st not in dead]
    out = {'legs': legs, 'budgetUsd': key[1], 'solUsd': sol_usd, 'retired': sorted(dead), 'cards': sorted(cards, key=lambda c: -((c['arena'] or {}).get('avgPct') or -999))}
    rs._fuse_prebuilt_cache[key] = (rs.time.time(), out)
    return out


@router.get('/api/reputation/fuses/edge')
async def fuses_edge():
    """🧬 The swap-in lists ranked by evidence + Coming up's own record + the learned combos that have settled. A ranking, never a promise."""
    rs = _rs()
    st = rs._json_load(rs.EDGE_PROOF_PATH, {})
    proof = rs._trench.meta_proof(st, keys=tuple(st))
    return {'rows': [{k: r.get(k) for k in ('mint', 'symbol', 'pairAddress', 'baseAddress', 'logo', 'priceUsd', 'price', 'tv', 'vital', 'edge')} for r in rs._edge_rank()[:60]],
            'up': proof.get('up'), 'combos': {k: v for k, v in proof.items() if k != 'up' and v.get('n')}}


@router.get('/api/reputation/fuses/forecast')
async def fuses_forecast():
    """🌦 Public: the runner weather and where it is heading (sim cards + live launch-coin breadth). Caches only — answers in ms."""
    rs = _rs()
    rcfg = rs._runner_cfg()
    safe = [r for r in rs._runner_cands if rs._rn.safe_only(r, rcfg) and rs._fuse._f(r.get('liq')) >= 10000]   # setups only among coins clearing every SAFETY gate
    proof = rs._trench.meta_proof(rs._json_load(rs.ENTRY_PROOF_PATH, {}), keys=rs._prime.ENTRY_SETUPS)
    eg = rs._edge_load()
    return {**rs._prime.forecast(rs._json_load(rs.PG_SIM_PATH, {}), rs._runner_cands), 'edge': {k: eg.get(k) for k in ('n', 'base', 'proof', 'best', 'worst', 'at')} | {'on': bool(eg.get('table'))}, 'entries': [{**e, 'proof': proof.get(e['setup'])} for e in rs._prime.entries(safe)],
            'setups': [{'key': k, 'ico': v[0], 'name': v[1], 'why': v[2], **(proof.get(k) or {})} for k, v in rs._prime.ENTRY_SETUPS.items()]}


@router.get('/api/reputation/arena')
async def arena_home(address: str = Query('', max_length=64), session: str = Query('', max_length=400), tg: str = Query('', max_length=4096)):
    """🎯 the catalog (guns + attachments + the level curve), your profile, today's leaders, the online rooms."""
    rs = _rs()
    now = rs.time.time(); who_, _n = rs._arena_who(address, session, tg)
    players_ = (rs._json_load(rs.ARENA_PATH, {}) or {}).get('players') or {}
    return {'guns': rs._ar.GUNS, 'parts': {k: [{'id': i, 'name': n, 'level': lv, 'mod': m} for i, n, lv, m in v] for k, v in rs._ar.PARTS.items()}, 'default': rs._ar.DEFAULT,
            'xp': rs._ar.XP, 'me': rs._arena_profile(players_, who_) if who_ else {**rs._arena_profile({}, ''), 'guest': True},
            'board': rs._ar.board(players_, rs._arena_day(now)), 'rooms': [{'room': k, 'n': len(v)} for k, v in rs._arena_rooms.items() if v][:20]}


@router.get('/api/reputation/fuses/sparks')
async def fuse_sparks(mints: str = Query('', max_length=4000)):
    rs = _rs()
    """📈 Mini chart lines for coin lists: the last ~2 hours of recorded prices (5-min readings) per mint, from the runner board's own
    record. ≤ 60 mints a call; a coin the board has not tracked returns nothing (the row just shows no line). Cache only — ms."""
    paths = rs._json_load(rs.RUNNERS_PATH, {}).get('paths') or {}
    cut = rs.time.time() - 2.5 * 3600
    out = {}
    for m in [x for x in mints.split(',') if 32 <= len(x) <= 44][:60]:
        pts = [float(p) for t, p in (paths.get(m) or []) if t >= cut and p]
        if len(pts) >= 3:
            out[m] = [round(v / pts[0], 5) for v in pts[-30:]]   # indexed to 1.0 at the first point: shape, not price
    return {'sparks': out}


@router.get('/api/reputation/fuses/strategies')
async def fuse_strategies(hours: float = Query(1.0, ge=0.01, le=48)):
    rs = _rs()
    """🎯 3 strategies for a card's round length (🛡 Steady · 🧠 Engine pick · 🔥 Hunt) from the background sims on REAL recorded prices
    (fees in, re-run every ~15 min). Longer clocks than the sims play read the nearest one (said so). Never a promise."""
    bc = rs._json_load(rs.PG_SIM_PATH, {}).get('byClock') or {}
    rows = [(float(k), v) for k, v in bc.items() if v.get('strategies')]
    if not rows:
        return {'clock': None, 'strategies': [], 'note': 'The sim brain needs ~15 min of recorded prices first.'}
    want = hours * 60
    clock, v = min(rows, key=lambda kv: abs(kv[0] - want))
    note = '' if abs(clock - want) < 1 else f"Sims play 5–60 min rounds; these are for {int(clock)} min, the nearest to your clock."
    sniper = (rs._json_load(rs.PG_SIM_PATH, {}).get('setups') or {}).get(str(int(clock))) or []   # 🚀 🎯 whole setups first, each with its own walk-forward proof
    rows_all = sniper + v['strategies']
    win = [x for x in rows_all if x.get('profitable')]
    if win:   # 🏆 only setups that ENDED UP on the replay are offered; the losing ones are counted, not shown
        hid = len(rows_all) - len(win)
        note = (note + ' ' if note else '') + (f"{hid} setup{'s' if hid != 1 else ''} that lost on the replay {'are' if hid != 1 else 'is'} hidden." if hid else '')
        rows_all = win
    return {'clock': int(clock), 'n': v.get('n'), 'strategies': rows_all, 'note': note.strip(), 'at': rs._json_load(rs.PG_SIM_PATH, {}).get('at')}


@router.get('/api/reputation/fuses/dna/unique')
async def fuse_dna_unique(dial: str = '', seed: str = ''):
    """🎲 A card DNA nobody on FEELESS holds right now (every Arena card + every open trader card) — so a new card plays its own way."""
    rs = _rs()
    taken = dict((rs._json_load(rs.FUSE_HQ_PATH, {}).get('cardDna') or {}))
    for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or []:
        if not x.get('closedAt'):
            taken[f"user:{x['id']}"] = rs._dna.clean({'cycle': x.get('cycle') if x.get('cycle') in ('classic', 'adaptive', 'safe', 'press', 'rescue', 'auto') else 'off', 'compound': x.get('compoundStyle') or 'smart',
                                                   'payoutPct': x.get('payoutPct', 100), 'clock': x.get('rotateHours') or 24, 'stop': x.get('slMode') or 'sell'})
    new_id = f"new:{seed or rs.uuid.uuid4().hex[:8]}"
    d = rs._dna.assign([*({'id': k} for k in taken), {'id': new_id, 'dial': dial if dial in ('safe', 'balanced', 'degen') else None}], known=taken)[new_id]
    return {'dna': d, 'label': rs._dna.label(d)}


@router.get('/api/reputation/fuses/brain')
async def fuse_brain():
    """🧠 The engine's best card DNA so far (learned from playground battles) — the Lab offers it as a one-tap setup."""
    rs = _rs()
    br = (rs._json_load(rs.RUNNERS_PATH, {}).get('pgBattle') or {}).get('brain') or {}
    best = rs._dna.best(br)
    return {**best, 'label': rs._dna.label(best['dna']), 'fights': sum(v['n'] for vals in br.values() for v in vals.values()) // 5 if br else 0}


@router.get('/api/reputation/clicks/top')
async def top_clicks(kind: str = '', limit: int = 10):
    rs = _rs()
    d = rs._json_load(rs.CLICKS_PATH, {})
    rows = [{'kind': k.split(':', 1)[0], 'value': k.split(':', 1)[1], 'count': v[0], 'lastAt': v[1]} for k, v in d.items() if not kind or k.startswith(kind + ':')]
    rows.sort(key=lambda r: -r['count'])
    return {'rows': rows[:max(1, min(limit, 50))]}


@router.get('/api/reputation/calls/following/{address}')
async def following_calls(address: str, hours: int = Query(24, ge=1, le=168)):
    rs = _rs()
    me = rs.primary_of(address)
    following = set(rs._fol()['following'].get(me, []))
    if not following:
        return {'calls': [], 'following': 0}
    since = rs.time.time() - hours * 3600
    board = {r.get('callerAddress'): r for r in (await rs.caller_board(days=30))['rows']}
    calls = [rs._call_view(c) for c in rs._calls_load()['calls'].values() if c['at'] >= since and rs.primary_of(c.get('callerAddress') or '') in following]
    calls.sort(key=lambda c: -c['at'])
    for c in calls:
        b = board.get(c.get('callerAddress')) or {}
        c['callerHitRate'] = b.get('hitRate'); c['callerCalls'] = b.get('calls')
    return {'calls': calls[:30], 'following': len(following)}


@router.get('/api/reputation/ads')
async def public_ads(placement: str = 'banner'):
    rs = _rs()
    now = rs.time.time()
    ads = [a for a in rs._json_load(rs.ADS_PATH, {'ads': []})['ads'] if a['active'] and a['placement'] == placement and (not a['startsAt'] or a['startsAt'] <= now) and (not a['endsAt'] or now < a['endsAt'])]
    return {'ads': [{k: a[k] for k in ('id', 'title', 'text', 'url', 'imageUrl', 'sponsor')} for a in ads]}


@router.get('/api/reputation/kols')
async def kols():
    rs = _rs()
    d = rs._json_load(rs.KOLS_PATH, {})
    rows = await rs.asyncio.gather(*(rs._kol_stats(a, v['chain']) for a, v in d.items()))
    return {'kols': [{'address': a, **v, 'stats': s} for (a, v), s in zip(d.items(), rows)], 'at': rs.time.time()}


@router.get('/api/reputation/season')
async def season_get(address: str = ''):
    rs = _rs()
    d = rs._seasons(); s = rs._current_season(d)
    upcoming = sorted((x for x in d['seasons'] if x['start'] > rs.time.time()), key=lambda x: x['start'])[:1]
    if not s:
        return {'season': None, 'upcoming': upcoming[0] if upcoming else None, 'tiers': rs.SEASON_TIERS}
    sc = d['scores'].get(s['id'], {})
    board = sorted(sc.items(), key=lambda kv: -kv[1]['score'])
    top = [{'rank': i + 1, 'address': a, 'handle': rs.handle_of(a), 'name': rs._display_name(a), 'score': r['score'], **rs._tier(r['score'])} for i, (a, r) in enumerate(board[:25])]
    me = None
    if address:
        a = rs.primary_of(address); r = sc.get(a)
        rank = next((i + 1 for i, (x, _) in enumerate(board) if x == a), None)
        me = {'address': a, 'score': r['score'] if r else 0, 'rank': rank, 'players': len(board), **rs._tier(r['score'] if r else 0)}
    return {'season': s, 'endsIn': round(s['end'] - rs.time.time()), 'players': len(board), 'top': top, 'me': me, 'tiers': rs.SEASON_TIERS,
            'upcoming': upcoming[0] if upcoming else None}


@router.get('/api/reputation/rug-report')
async def rug_report(days: int = Query(7, ge=1, le=30)):
    """The week's receipts: who got caught, who funded them, which promises broke."""
    rs = _rs()
    since = rs.time.time() - days * 86400
    bl = rs._block_load()['wallets']
    caught = [{'wallet': w, 'roles': sorted(set((r.get('mints') or {}).values())), 'launches': len(r.get('mints') or {}), 'blocked': rs._is_blocked(r)}
              for w, r in bl.items() if (r.get('firstSeen') or 0) >= since]
    fd = rs._funders_load()
    funders = [{'wallet': w, 'walletsFunded': len(r.get('funded') or []), 'launches': len(r.get('mints') or {})}
               for w, r in fd['funders'].items() if rs._is_flagged_funder(r) and (r.get('lastSeen') or 0) >= since]
    broken = [{'mint': m, 'creator': s['creator'], 'rules': [b['rule'] for b in s['breaches']]}
              for m, s in rs._json_load(rs.SHIELD_PATH, {}).items() if any(b['at'] >= since for b in s['breaches'])]
    rugs = [e for e in rs._radar['events'] if e['kind'] in ('rug', 'dump') and e['at'] >= since]
    return {'days': days, 'from': since, 'to': rs.time.time(),
            'totals': {'caught': len(caught), 'blocklisted': sum(1 for c in caught if c['blocked']), 'funders': len(funders), 'brokenShields': len(broken), 'rugs': len(rugs)},
            'caught': sorted(caught, key=lambda c: -c['launches'])[:10], 'funders': sorted(funders, key=lambda f: -f['walletsFunded'])[:5],
            'brokenShields': broken[:5], 'rugs': rugs[:8]}


@router.get('/api/reputation/badge-pools')
async def badge_pools_public(address: str = ''):
    """Public: every live badge pool, its pot and what this wallet's badges earn from it."""
    rs = _rs()
    hit = rs._pool_pub_cache.get('all')
    if not hit or rs.time.time() - hit[0] > 60:
        plans = await rs.asyncio.gather(*(rs._pool_plan(p) for p in rs._pools()['pools'] if p.get('pct')))
        hit = (rs.time.time(), plans); rs._pool_pub_cache['all'] = hit
    a = rs.primary_of(address) if address else ''
    return {'pools': [{'id': pl['pool']['id'], 'name': pl['pool']['name'], 'pct': pl['pct'], 'potSol': pl['potSol'], 'wallets': len(pl['rows']),
                       'earns': [k.split(':', 1)[1] for k in pl['pool'].get('weights', {})], 'me': rs.reserve_pool.wallet_share(pl, a) if a else None} for pl in hit[1]]}


@router.get('/api/reputation/after-sell/{address}')
async def after_sell(address: str):
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        raise rs.HTTPException(400, 'Bad address.')
    trades = [t for t in await rs.wallet_trades(address) if t.get('side') == 'sell'][:20]
    toks = list({t['token'] for t in trades})[:30]
    prices = {}
    if toks:
        try:
            async with rs.httpx.AsyncClient(timeout=8) as http:
                for p in (await http.get(f"https://api.dexscreener.com/latest/dex/tokens/{','.join(toks)}")).json().get('pairs') or []:
                    a = (p.get('baseToken') or {}).get('address')
                    if a and a not in prices and p.get('priceUsd'):
                        prices[a] = float(p['priceUsd'])
        except Exception:
            pass
    rows = rs.after_sell_lessons(trades, prices)
    return {'address': address, 'rows': rows, 'runners': sum(r['lesson'] == 'runner' for r in rows), 'saved': sum(r['lesson'] == 'saved' for r in rows)}
