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
    box = rs._legacy_sniper_dedupe(rs._json_load(rs.NOTIF_PATH, {}).get(me, []))
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
    host = (request.client.host if request.client else '') or ''
    if host not in ('127.0.0.1', '::1', 'localhost'):
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
