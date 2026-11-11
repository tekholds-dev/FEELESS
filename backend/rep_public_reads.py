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
