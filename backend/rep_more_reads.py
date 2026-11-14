"""🧩 SITE-5 slice 8 (2026-11-13): plain read routes (GET, no admin, no money, no staff checks), moved out of reputation_service by
scripts/move-routes.py. Helpers stay there and are looked up on reputation_service when a route runs, so a test that patches them still works."""
from fastapi import APIRouter, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401

router = APIRouter()


def _rs():
    import reputation_service
    return reputation_service


@router.get('/api/reputation/creator/{chain}/{address}')
async def creator_profile(chain: str, address: str):
    rs = _rs()
    store = rs._load()
    ckey = rs._creator_key(chain, address)
    entry = store['creators'].get(ckey)
    if not entry:
        raise rs.HTTPException(404, 'No observations recorded for this creator yet.')

    wallet = {'solBalance': None, 'recentSignatures': []}
    if chain == 'solana':
        try:
            async with rs.httpx.AsyncClient(timeout=8) as http:
                balance_result = await rs._rpc(http, 'getBalance', [address, {'commitment': 'confirmed'}])
                if balance_result is not None:
                    wallet['solBalance'] = (balance_result.get('value') or 0) / 1_000_000_000
                signatures = await rs._rpc(http, 'getSignaturesForAddress', [address, {'limit': 8}])
                wallet['recentSignatures'] = [{
                    'signature': s.get('signature'), 'blockTime': s.get('blockTime'), 'err': s.get('err') is not None,
                } for s in (signatures or [])]
        except Exception:
            pass

    fkey = rs._creator_key(chain, address)
    async with rs._lock:
        store2 = rs._load()
        if fkey not in store2['funding']:
            store2['funding'][fkey] = await rs.resolve_funding_source(chain, address)
            rs._save(store2)
        funding_source = store2['funding'][fkey]
    linked = []
    if funding_source:
        for other_ckey, other_entry in store2['creators'].items():
            if other_ckey == ckey:
                continue
            other_fkey = rs._creator_key(other_entry['chain'], other_entry['address'])
            if store2['funding'].get(other_fkey) == funding_source:
                linked.append({'address': other_entry['address'], 'chain': other_entry['chain'], **rs.score_creator(other_entry)})

    tokens = sorted(entry['tokens'].values(), key=lambda t: -(t.get('firstSeenAt') or 0))
    mints = [t['baseTokenAddress'] for t in tokens if t.get('baseTokenAddress')]
    markets = await rs.fetch_token_markets(chain, mints) if mints else {}
    async with rs._lock:
        store3 = rs._load()
        live = store3['creators'].get(ckey) or entry
        rs._apply_markets(live, markets)
        rs._save(store3)
        entry = live
    tokens = sorted(entry['tokens'].values(), key=lambda t: -(t.get('firstSeenAt') or 0))
    enriched = [{**t, 'outcome': rs.token_outcome(t)} for t in tokens]
    scoring = rs.score_creator(entry)
    return {**entry, 'tokens': {t['pairAddress']: t for t in enriched}, 'tokenList': enriched, 'scoring': scoring,
            'verdict': rs.trust_verdict(scoring, enriched, linked),
            'feelessLaunches': [l for l in (rs._load().get('feelessLaunches') or {}).values() if l['wallet'] == address],
            'wallet': wallet, 'fundingSource': funding_source, 'linkedWallets': linked}


@router.get('/api/reputation/watchlist/feed')
async def get_watchlist_feed(ownerWallet: str, limit: int = Query(50, le=200)):
    rs = _rs()
    store = rs._load()
    bucket = store['watchlists'].get(ownerWallet, {})
    if not bucket:
        return {'events': []}
    events = []
    for event in store.get('feed', []):
        wkey = rs._creator_key(event['chain'], event['address'])
        watch = bucket.get(wkey)
        if not watch:
            continue
        if event['type'] == 'new_token' and not watch.get('notifyNewToken', True):
            continue
        if event['type'] == 'flagged' and not watch.get('notifyFlag', True):
            continue
        events.append(event)
        if len(events) >= limit:
            break
    return {'events': events}


@router.get('/api/reputation/feed')
async def global_feed(limit: int = Query(40, ge=1, le=200)):
    """Site-wide trust signals: known creators launching again, and fresh rug flags."""
    rs = _rs()
    store = rs._load()
    events = []
    for ev in store.get('feed', [])[:limit]:
        entry = store['creators'].get(rs._creator_key(ev['chain'], ev['address']))
        events.append({**ev, **(rs.score_creator(entry) if entry else {})})
    return {'events': events}


@router.get('/api/reputation/case-studies')
async def case_studies(limit: int = Query(6, ge=1, le=20)):
    """Real flagged creators with the tokens that collapsed — teaching material from live data."""
    rs = _rs()
    store = rs._load()
    cases = []
    for entry in store['creators'].values():
        rugged = [t for t in entry['tokens'].values() if t.get('status') == 'rugged']
        scoring = rs.score_creator(entry)
        if not rugged and scoring['cloneCount'] < 3 and not scoring.get('serialDumper'):
            continue
        cases.append({
            'chain': entry['chain'], 'address': entry['address'], **scoring,
            'kind': 'rug' if rugged else 'dumper' if scoring.get('serialDumper') else 'clone-farm',
            'tickers': sorted({(t.get('symbol') or '?') for t in entry['tokens'].values()}),
            'rugged': [{'symbol': t.get('symbol'), 'pairAddress': t['pairAddress'], 'peakLiquidityUsd': t.get('peakLiquidityUsd'),
                        'lastLiquidityUsd': t.get('lastLiquidityUsd'), 'firstSeenAt': t.get('firstSeenAt'), 'lastCheckedAt': t.get('lastCheckedAt')} for t in rugged],
        })
    cases.sort(key=lambda c: (-c['ruggedCount'], -c['cloneCount'], -c['tokenCount']))
    return {'cases': cases[:limit], 'total': len(cases)}


@router.get('/api/reputation/uploads/{name}')
async def get_upload(name: str):
    rs = _rs()
    from fastapi.responses import FileResponse
    import re
    if not re.match(r'^[a-f0-9]{32}\.(png|jpg|webp|gif)$', name):
        raise rs.HTTPException(404, 'Not found')
    path = rs.UPLOAD_DIR / name
    if not path.exists():
        raise rs.HTTPException(404, 'Not found')
    return FileResponse(path, headers={'Cache-Control': 'public, max-age=31536000, immutable'})


@router.get('/api/reputation/x/oauth/callback')
async def x_oauth_callback(code: str = '', state: str = '', error: str = ''):
    rs = _rs()
    from fastapi.responses import RedirectResponse
    st_ = rs._x_states.pop(state, None)
    site_ = (rs.os.getenv('PUBLIC_SITE_URL') or '').rstrip('/')
    if not st_ or error or not code:
        return RedirectResponse(f"{site_}/terminal/profile?x=failed")
    cid_, sec_ = (rs.os.getenv('X_CLIENT_ID') or '').strip(), (rs.os.getenv('X_CLIENT_SECRET') or '').strip()
    try:
        async with rs.httpx.AsyncClient(timeout=15) as h_:
            tok_ = await h_.post('https://api.twitter.com/2/oauth2/token', data={'grant_type': 'authorization_code', 'code': code, 'redirect_uri': rs._x_redirect(), 'client_id': cid_, 'code_verifier': st_['ver']},
                                 auth=(cid_, sec_) if sec_ else None)
            at_ = (tok_.json() or {}).get('access_token')
            me_ = (await h_.get('https://api.twitter.com/2/users/me', headers={'Authorization': f'Bearer {at_}'})).json().get('data') if at_ else None
    except Exception:
        me_ = None
    if not me_ or not me_.get('username'):
        return RedirectResponse(f"{site_}/terminal/profile?x=failed")
    async with rs._profile_lock:
        rs._prof().update(st_['addr'], lambda cur: {**(cur or {}), 'xVerified': {'id': str(me_.get('id')), 'username': me_['username'][:40], 'at': rs.time.time()},
                                                     'twitter': '@' + me_['username'][:40]})
    return RedirectResponse(f"{site_}{st_['back']}{'&' if '?' in st_['back'] else '?'}x=linked")


@router.get('/api/reputation/chat/{room}')
async def chat_room(room: str, session: str = ''):
    rs = _rs()
    if room in rs._ALPHA and not await rs._alpha_allowed(room, rs.session_address(session) or ''):
        raise rs.HTTPException(403, f"{rs._ALPHA[room]['name']} unlocks at ${rs._ALPHA[room]['minUsd']:,} held in $FEE.")
    d = rs._chat_load()
    msgs = d['rooms'].get(room, [])[-120:]
    pin = (d.get('pins') or {}).get(room)
    pinned = None
    if pin and rs.time.time() - pin['at'] < rs.PIN_SECONDS:
        pinned = next((m for m in d['rooms'].get(room, []) if m['id'] == pin['id']), None)
        if pinned:
            pinned = {**pinned, 'pinnedFor': round(rs.PIN_SECONDS - (rs.time.time() - pin['at']))}
    return {'room': room, 'messages': msgs, 'pinned': pinned}


@router.get('/api/reputation/why-pump/{mint}')
async def why_pump(mint: str, request: Request):
    """❓ WHY DID IT PUMP? (Rep page). A coin checked in the last 30 min is free and instant for everyone; a new check costs one of the visitor's
    5 daily checks. Read only — never advice."""
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', mint or ''):
        raise rs.HTTPException(400, 'Paste a Solana contract address.')
    hit = rs._why_cache.get(mint)
    if hit and rs.time.time() - hit[0] < rs.WHY_TTL:
        return {**hit[1], 'cached': True}
    ip = rs._guard.request_ip(request)
    day = rs.time.strftime('%Y-%m-%d', rs.time.gmtime())
    local = ip.startswith('127.') or ip in ('::1', 'testclient')   # loopback only: a 10.x / 192.168.x peer can be a load balancer carrying everyone
    q = rs._why_quota.get(ip) or [day, 0]
    if q[0] != day:
        q = [day, 0]
    if not local and q[1] >= rs.WHY_FREE_DAY:
        raise rs.HTTPException(429, f'{rs.WHY_FREE_DAY} new checks a day — coins someone already checked stay free.')
    t_ = rs._why_busy.get(mint)
    if not t_ or t_.done():
        t_ = rs._why_busy[mint] = rs.asyncio.create_task(rs._why_build(mint))
        q[1] += 1; rs._why_quota[ip] = q
    out = await t_
    return {**out, 'left': None if local else max(0, rs.WHY_FREE_DAY - q[1])}


@router.get('/api/reputation/edge')
async def coin_edge(mints: str = Query('', max_length=3000), intel: bool = False):
    """Coin edge for up to 60 coins: pulse, snipers out, verification, forensics, runner gates + bond boxes, Fuse sources, elite
    flow — 15s cache per coin, nothing slow on the request path. intel=1 (≤3 coins) also runs the holder scan if it isn't cached
    (the trade tape's wallet tags need it)."""
    rs = _rs()
    ms = [m for m in dict.fromkeys(x.strip() for x in mints.split(',')) if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', m)][:60]
    now = rs.time.time()
    out = {m: rs._edge_cache[m][1] for m in ms if now - rs._edge_cache.get(m, (0, None))[0] < 15 and not (intel and not rs._edge_cache[m][1].get('intel'))}
    todo = [m for m in ms if m not in out]
    if intel and todo and len(todo) <= 3:
        await rs.asyncio.gather(*[rs._runner_intel(m, rs._enr.PRIO['LOOK'], 'trade tape') for m in todo], return_exceptions=True)
    # ⚡ STALE-WHILE-REVALIDATE: a record under EDGE_STALE_SEC is answered now and refreshed in the background (a cold build waited on
    # pulses + verification for ~10s and held the browser's connection slots — every other request on the page queued behind it)
    stale = [m for m in todo if not intel and m in rs._edge_cache and now - rs._edge_cache[m][0] < rs.EDGE_STALE_SEC]
    for m in stale:
        out[m] = rs._edge_cache[m][1]
    fresh = [m for m in stale if m not in rs._edge_inflight]
    if fresh:
        rs._edge_inflight.update(fresh)
        rs.asyncio.create_task(rs._edge_refresh(fresh))
    cold = [m for m in todo if m not in out]
    if cold:
        out.update(await rs._edge_build(cold, now, rs.EDGE_COLD_BUDGET))
    return {'edge': out, 'at': now}


@router.get('/api/reputation/fuses/arena-best')
async def fuses_arena_best():
    """🏆 Best settings for the Fuse Arena: styles by the Arena's own score + what the top quarter of cards share (fuse_best.best), 5 min cache."""
    rs = _rs()
    import fuse_best as _fb
    if rs.time.time() - rs._arena_best_cache['at'] > 300 or rs._arena_best_cache['v'] is None:
        rs._arena_best_cache.update(at=rs.time.time(), v=_fb.best(rs._json_load(rs.FUSE_HQ_PATH, {}).get('arena') or []))
    return rs._arena_best_cache['v']


@router.get('/api/reputation/fuses/feecat-pool')
async def fuses_feecat_pool():
    """🐱 FeeCat's candidate pool (public, cache-only: the kernel's last pass + the Arena's last league — no fetch here)."""
    rs = _rs()
    try:
        kr = rs._agent_inherit_rows(limit=25)
    except Exception:
        kr = []
    ar_ = ((rs._contenders_cache.get('data') or {}).get('all') or []) if isinstance(rs._contenders_cache.get('data'), dict) else []
    rows_ = rs.feecat_pool_rows(kr, ar_)
    now = rs.time.time()
    log_ = list((rs._g4_mem.get() or {}).get('log') or [])
    for r_ in rows_:   # 🐱 she reads every coin the way the agents + OSSY / G4 do (owner, 2026-10-18: "latest methods — HH/HL, germ")
        try:
            x_ = rs._tk.KERNEL.candidate(r_['mint']) if r_.get('mint') else None
        except Exception:
            x_ = None
        if x_:
            r_['read'] = rs.feecat_read(x_, rs._oe.setups_of(x_, rs._uni.germ_max()), rs._g4_bad_entry(x_))
        r_['duo'] = rs.duo_word(log_, r_.get('mint'), now)
    try:
        tot_ = {k_: {'n': v_['n'], 'won': round(100 * v_['won'] / v_['n']) if v_['n'] else 0, 'med': round(v_['pct'] / v_['n'], 1) if v_['n'] else 0, 'usd': v_['usd']}
                for k_, v_ in (rs._duo_totals() or {}).items() if k_ in ('OSSY', 'G4')}   # their REAL closed trades (ledger), all time
    except Exception:
        tot_ = {}
    try:   # 🐱 the agents' own band — her agents lane judges their coins on THEIR settings (her own overrides sit on top, feecat_service)
        mn_, mx_ = rs._uni.band(); lm_ = rs._uni.limits()
        lim_ = {'mcMin': mn_, 'mcMax': mx_, 'minAgeH': lm_.get('minAgeH'), 'maxAgeH': lm_.get('maxAgeH'), 'minVol1h': lm_.get('minVol'),
                'poolMin': rs._fuse._f((rs._prime_real_cfg() or {}).get('agentPoolMin')) or 8000}
        lim_ = {k_: (None if isinstance(v_, float) and v_ in (float('inf'), float('-inf')) else v_) for k_, v_ in lim_.items()}   # JSON has no Infinity
    except Exception:
        lim_ = {}
    return {'at': now, 'rows': rows_, 'duo': rs.duo_lessons(log_, tot_), 'limits': lim_}


@router.get('/api/reputation/crews/{cid}')
async def crew_public(cid: str):
    rs = _rs()
    st = rs._json_load(rs.CREWS_PATH, {}); c = (st.get('crews') or {}).get(cid)
    if not c:
        raise rs.HTTPException(404, 'No such family.')
    return {'crew': rs._crew_view(c, rs._crew_pieces(c['members'], rs.time.time()))}


@router.get('/api/reputation/updates')
async def site_updates():
    """📜 Settings › Updates: the last 60 shipped changes from git (NEW requested features + FIXES; SITE · BACKEND · MOBILE), private bits dropped
    (updates_log.py). Read once per 5 min, off the event loop."""
    rs = _rs()
    import updates_log as _ul
    if rs.time.time() - rs._UPDATES_CACHE['at'] > 300:
        def _read():
            import subprocess as _sp
            try:
                r_ = _sp.run(['git', 'log', '-n', '160', f'--format={_ul.FORMAT}', '--name-only', '--date=short'], cwd=str(rs.Path(__file__).resolve().parent.parent),
                             capture_output=True, text=True, timeout=8)
                return _ul.parse(r_.stdout if r_.returncode == 0 else '')
            except Exception:
                return []
        rows_ = await rs.asyncio.to_thread(_read)
        if rows_ or not rs._UPDATES_CACHE['rows']:
            rs._UPDATES_CACHE.update(at=rs.time.time(), rows=rows_)
    rows_ = rs._UPDATES_CACHE['rows']
    return {'rows': rows_, 'counts': _ul.counts(rows_)}


@router.get('/api/reputation/familia/broker/cdc-caps')
async def familia_broker_cdc_caps(address: str = Query('', max_length=64), session: str = Query('', max_length=400)):
    """🔑 What a Crypto.com key does in FEELESS: what the exchange lists (live) + whether THIS wallet's key reads its account."""
    rs = _rs()
    import brokers as _bk
    caps_ = _bk.cdc_caps(await rs._cdc_instruments())
    key_ = {'linked': False}
    if address and session:
        me_ = rs._session_or_401(address, session)
        ck_ = rs._brk_cdc(me_)
        if ck_:
            try:
                v_ = _bk.cdc_view(await rs._cdc_call(ck_, 'private/user-balance'))
                key_ = {'linked': True, 'reads': True, 'valueUsd': v_['value'], 'buyingPower': v_['buyingPower']}
            except rs.HTTPException as e:
                key_ = {'linked': True, 'reads': False, 'error': e.detail}
    return {**caps_, 'key': key_, 'wired': {'spot': True, 'perps': True, 'futures': False},
            'devKey': bool(rs._cdc_dev_key()),   # the Developer Platform / AI-agent key (Cronos data — it cannot trade)
            'envPair': bool((rs.os.getenv('CRYPTO_COM_API_KEY') or '').strip() and (rs.os.getenv('CRYPTO_COM_API_SECRET') or '').strip())}


@router.get('/api/reputation/familia/kalshi/proof')
async def familia_kalshi_proof(address: str = ''):
    """🪪 Is this wallet Proof-verified (DFlow's free KYC)? Public check; FEELESS never sees identity data."""
    rs = _rs()
    return {'verified': await rs._kt_proof(rs._kt_addr(address))}


@router.get('/api/reputation/familia/kalshi/status')
async def familia_kalshi_status(signature: str = '', lastValidBlockHeight: int = 0):
    """⏳ DFlow's fill status for a sent order (pending · open · closed = filled · failed · expired)."""
    rs = _rs()
    kt_ = rs._kt_need()
    try:
        r_ = await rs._fmk_http_get().get(f'{kt_.TRADE}/order-status', params={'signature': signature, 'lastValidBlockHeight': lastValidBlockHeight},
                                       headers=kt_.headers(rs.os.environ), timeout=10)
        d_ = r_.json() if r_.status_code == 200 else {}
    except Exception:
        d_ = {}
    return {'status': d_.get('status') or 'pending', 'outAmount': d_.get('outAmount'), 'reverts': d_.get('reverts')}


@router.get('/api/reputation/familia/kalshi/positions')
async def familia_kalshi_positions(address: str = ''):
    """🎫 The wallet's Kalshi outcome tokens (UP / DOWN contracts), each with its market, settled / won and redeemable — read on-chain."""
    rs = _rs()
    kt_ = rs._kt_need()
    addr_ = rs._kt_addr(address)
    async with rs.httpx.AsyncClient(timeout=12) as http_:
        accs_ = await rs._sol_token_accounts(http_, addr_)
    held_ = [a_ for a_ in accs_ if a_['raw'] > 0 and a_['mint'] != kt_.USDC][:40]
    mk_ = await rs.asyncio.gather(*[rs._kt_market(f"market/by-mint/{a_['mint']}", f"mint:{a_['mint']}", ttl=30, miss_ttl=600) for a_ in held_])
    rows_ = [kt_.position(m_, a_['mint'], a_['raw'], a_['decimals']) for a_, m_ in zip(held_, mk_) if m_]
    return {'positions': [r_ for r_ in rows_ if r_]}


@router.get('/api/reputation/familia/paper-perps')
async def familia_paper_perps(address: str = Query('', max_length=64), session: str = Query('', max_length=400)):
    """📉 Your paper perps book at live marks (liquidations settle on the read). Signed in; paper only (docs/RULINGS.md #1)."""
    rs = _rs()
    import paper_perps as _pp
    me_ = rs._session_or_401(address, session)
    if not rs._perps_cache.get('rows'):
        await rs.familia_perps()
    now_ = rs.time.time()
    async with rs._pperp_lock:
        d_ = rs._json_load(rs.PAPER_PERPS_PATH, {}) or {}
        book_ = d_.get(me_) or _pp.blank(now_)
        v_ = _pp.view(book_, rs._pperp_board(), now_)
        if v_['liquidated'] or me_ not in d_:
            d_[me_] = book_; rs._json_save(rs.PAPER_PERPS_PATH, d_)
    return v_


@router.get('/api/reputation/familia/intake')
async def familia_intake():
    """The same discovery snapshot agents receive, with their verdicts attached afterwards."""
    rs = _rs()
    now = rs.time.time()
    if now - rs._intake_cache['at'] > 30:
        rows_ = []
        ser_ = (rs._agents_mem.get() or {}).get('series') or {}
        for r_ in rs._shared_intake['rows']:
            mint = r_['mint']
            x_ = rs._tk.KERNEL.candidate(mint) or {}
            n_, d_ = x_.get('nums') or {}, rs._tk.KERNEL.dec.get(mint) or {}
            chart = x_.get('chart') or {}
            row_ = {'mint': mint, 'sym': r_.get('symbol'), 'pair': r_.get('pairAddress') or r_.get('pair'),
                    'mc': r_.get('mcap') or r_.get('cap'), 'liq': r_.get('liq'), 'ch': r_.get('chg5m'),
                    'ageMin': round(rs._fuse._f(r_['ageH']) * 60) if r_.get('ageH') is not None else None,
                    'status': d_.get('status') or 'UNREVIEWED', 'read': str(d_.get('why') or 'Awaiting agent review')[:90],
                    'sources': r_.get('sources') or ['open'],
                    'line': [p_['px'] for p_ in (ser_.get(mint) or [])[-15:] if rs._fuse._f(p_.get('px')) > 0],
                    'buy': n_.get('buy'), 'v5': r_.get('vol5m'), 'tx': n_.get('tx'), 'liqD': n_.get('liqD'), 'rank': d_.get('rank'),
                    'germ': chart.get('germDist') if chart.get('germDist') is not None else chart.get('germ5Dist')}
            row_['theory'] = __import__('trench_theory').verdict({'ageMin': row_['ageMin'], 'cap': row_['mc'], 'liq': row_['liq'], 'status': r_.get('stage')})['line'][:200]
            rows_.append(row_)
        rs._intake_cache.update(at=now, rows=rows_)
    return {'coins': rs._intake_cache['rows'], 'at': round(rs._intake_cache['at'])}


@router.get('/api/reputation/familia-town/live')
async def familia_town_live():
    """🏘 Every town building's sign number (town_live.py) in ONE shared read every 45 s: each tool's own cached read, fetched in parallel
    (a slow or failed source leaves only its sign on the plain subtitle). Public numbers only — the desk's aggregate, never a seat."""
    rs = _rs()
    import town_live as _twl
    now = rs.time.time(); c_ = rs._town_live_cache
    if c_['v'] is not None and now - c_['at'] < rs.TOWN_LIVE_SEC:
        return c_['v']
    if c_['lock'] is None:
        c_['lock'] = rs.asyncio.Lock()
    async with c_['lock']:
        if c_['v'] is not None and rs.time.time() - c_['at'] < rs.TOWN_LIVE_SEC:
            return c_['v']

        async def cat_():
            r_ = await rs._ai_http().get('http://127.0.0.1:5088/api/cats/leader/profile', timeout=4)
            return r_.json() if r_.status_code == 200 else None

        async def board_():
            return await rs.asyncio.to_thread(rs._open_board)

        jobs_ = {'tt': rs.familia_intake(), 'perps': rs.familia_perps(), 'pools': rs.familia_pools(), 'vault': rs.familia_pools_sleep(),
                 'trades': rs.familia_trade_center('', ''), 'rep': rs.rep_markets(''), 'cats': cat_(), 'radar': board_()}
        got_ = await rs.asyncio.gather(*(rs.asyncio.wait_for(j_, 12) for j_ in jobs_.values()), return_exceptions=True)
        v_ = {'signs': _twl.signs(dict(zip(jobs_, got_))), 'at': round(rs.time.time())}
        c_.update(at=rs.time.time(), v=v_)
        return v_


@router.get('/api/reputation/familia-pools/sleep')
async def familia_pools_sleep():
    """💤 THE NIGHT VAULT: money-while-you-sleep strategies (sleep_money.py) from the live Pool Hub + Kamino's public reserve rates (10 min):
    LST stack · stable lend · JLP · auto-compound vaults · loops (net APY, LTV, cushion to liquidation). Each lists the hub rows it rides on."""
    rs = _rs()
    now = rs.time.time()
    hub_, km_ = await rs.familia_pools(), None
    if rs._slm_cache['km'] is not None and now - rs._slm_cache['at'] < rs.FPL_SEC:
        km_ = rs._slm_cache['km']
    else:
        try:
            r_ = await rs._ai_http().get(f'https://api.kamino.finance/kamino-market/{rs._slm.KAMINO_MAIN}/reserves/metrics', timeout=12)
            km_ = rs._slm.kamino_rates(r_.json() if r_.status_code == 200 else [])
        except Exception:
            km_ = None
        if km_ or rs._slm_cache['km'] is None:
            rs._slm_cache.update(at=now, km=km_ or {})
        km_ = rs._slm_cache['km']
    pools_ = (hub_ or {}).get('pools') or []
    st_ = rs._slm.strategies(pools_, km_)
    want_ = {i_ for s_ in st_ for i_ in s_.get('rows') or []} | {l_['id'] for s_ in st_ for l_ in s_.get('loops') or []}
    return {'strategies': st_, 'rows': [r_ for r_ in pools_ if r_.get('id') in want_], 'kamino': bool(km_), 'at': round(now, 1)}


@router.get('/api/reputation/cats/fund-rules')
async def cat_fund_rules(address: str = Query('', max_length=64)):
    """💵 The funding rules a cat's desk shows BEFORE you type an amount (fee, minimum, top-up minimum; a creator wallet: no fee)."""
    rs = _rs()
    rules_ = rs._cat_fund_rules(address if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address or '') else None)
    left_ = await rs._openrouter_left()
    rules_['startCreditUsd'] = rs._cfund.START_CREDIT_USD   # 🧠 a user's new general agent: $5 credit + the $2 fee
    rules_['creditOpen'] = True   # SingIt bills the agent wallet per call; no provider prepayment minimum   # the free backup keeps every agent working
    if rules_['staff']:
        rules_['modelsLeftUsd'] = left_   # the balance itself is for the creator only
    return rules_


@router.get('/api/reputation/familia-pools/gaps')
async def familia_pools_gaps():
    """📐 PRICE GAPS (price_gap.py, READ-ONLY): the tokens the Pool Hub's pools hold, priced across every real pool they trade in — the
    cheap pool, the rich one, the gap after a swap's cost each side, how long it has stayed open. one DexScreener /token-pairs read per token a minute (≤ price_gap.TOKENS, in parallel)."""
    rs = _rs()
    if rs._pgap_c['v'] is not None and rs.time.time() - rs._pgap_c['at'] < rs.PGAP_SEC:
        return rs._pgap_c['v']
    return await rs._pgap_once(('vault',), rs._vault_gap_read)


@router.get('/api/reputation/price-gap/{mint}')
async def coin_price_gap(mint: str):
    """📐 SITE-11 (Q23) — ONE coin's price gap before you buy (READ-ONLY): every real pool it trades in, the cheap one, the rich one, the gap after
    a swap's cost each side, open only after two reads in a row (price_gap.persist). One DexScreener /token-pairs read per coin a minute. Never
    trades; the swap still routes through Jupiter and the wallet still signs."""
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', mint or ''):
        raise rs.HTTPException(400, 'Not a Solana mint.')
    c = rs._pgap_coin.get(mint)
    if c and c['v'] is not None and rs.time.time() - c['at'] < rs.PGAP_SEC:
        return c['v']
    return await rs._pgap_once(('coin', mint), lambda: rs._coin_gap_read(mint))


@router.get('/api/reputation/familia/perps-real')
async def familia_perps_real(address: str = ''):
    """📉 REAL PERPS (Jupiter Perps): each market's live pool (open fee, borrow rate per hour, room left long / short) + the wallet's
    open positions in plain dollars (P&L before fees; fees apart)."""
    rs = _rs()
    import jup_perps as _jp
    if rs.time.time() - rs._fjp_pool.get('at', 0) > 60 or not rs._fjp_pool.get('rows'):
        got_ = await rs.asyncio.gather(*[rs._jp_call('GET', 'pool-info', params={'mint': m_}) for m_ in _jp.MARKETS.values()])
        rows_ = {}
        for (a_, _m), (c_, b_) in zip(_jp.MARKETS.items(), got_):
            if c_ == 200 and isinstance(b_, dict):
                rows_[a_] = {k_: _jp._f(b_.get(k_)) for k_ in ('openFeePercent', 'longBorrowRatePercent', 'shortBorrowRatePercent', 'longUtilizationPercent',
                                                              'shortUtilizationPercent', 'longAvailableLiquidity', 'shortAvailableLiquidity')}
        if rows_:
            rs._fjp_pool.update(at=rs.time.time(), rows=rows_)
    pos_, trd_ = [], []
    if 32 <= len(address or '') <= 44:
        (c_, b_), (ct_, bt_) = await rs.asyncio.gather(rs._jp_call('GET', 'positions', params={'walletAddress': address}),
                                                     rs._jp_call('GET', 'trades', params={'walletAddress': address, 'start': 0, 'end': 20}))
        pos_ = _jp.positions(b_) if c_ == 200 else []
        trd_ = _jp.trades(bt_) if ct_ == 200 else []   # 🧾 the wallet's recent opens / closes / triggers (owner: "jup perps don't show my recent trades")
    if rs.time.time() - rs._fjp_stats.get('at', 0) > 10:   # 📊 Jupiter's own mark + 24 h range / volume per market (its oracle — what the trade fills at)
        got_ = await rs.asyncio.gather(*[rs._jp_call('GET', 'market-stats', params={'mint': m_}) for m_ in _jp.MARKETS.values()])
        st_ = {a_: {'price': _jp._f(b_.get('price')), 'ch24': _jp._f(b_.get('priceChange24H')), 'hi24': _jp._f(b_.get('priceHigh24H')),
                    'lo24': _jp._f(b_.get('priceLow24H')), 'vol24': _jp._f(b_.get('volume'))} for a_, (c_, b_) in zip(_jp.MARKETS, got_) if c_ == 200 and isinstance(b_, dict)}
        if st_:
            rs._fjp_stats.update(at=rs.time.time(), rows=st_)
    return {'pools': rs._fjp_pool.get('rows') or {}, 'stats': rs._fjp_stats.get('rows') or {}, 'positions': pos_, 'trades': trd_, 'min': _jp.MIN_USD, 'max': _jp.MAX_USD, 'maxLev': _jp.MAX_LEV}


@router.get('/api/reputation/familia/perps-real/leaders')
async def familia_perps_real_leaders(asset: str = 'SOL'):
    """🏆 Jupiter Perps' top traders THIS week on one market (P&L + volume, plain $) — the smart money on the desk; 5-min cache."""
    rs = _rs()
    import datetime as _dt
    import jup_perps as _jp
    a_ = str(asset or 'SOL').upper()
    if a_ not in _jp.MARKETS:
        raise rs.HTTPException(400, 'SOL, ETH or BTC.')
    hit_ = rs._fjp_lead.get(a_)
    if hit_ and rs.time.time() - hit_[0] < 300:
        return hit_[1]
    y_, w_, _d = _dt.datetime.utcnow().isocalendar()
    c_, b_ = await rs._jp_call('GET', 'top-traders', params={'marketMint': _jp.MARKETS[a_], 'year': y_, 'week': w_})
    if c_ != 200:
        return hit_[1] if hit_ else {'vol': None, 'pnl': [], 'busy': []}
    out_ = {**_jp.leaders(b_), 'asset': a_}
    rs._fjp_lead[a_] = (rs.time.time(), out_)
    return out_


@router.get('/api/reputation/familia/leverage')
async def familia_leverage(address: str = ''):
    """⚡ REAL LEVERAGE markets (Jupiter Lend: SOL · BTC · JUP against USDC — max leverage, liquidation threshold, borrow APR, room to
    borrow) + the wallet's open Jupiter Lend positions in them."""
    rs = _rs()
    import lend_borrow as _lb
    rows_ = await rs._jl_markets()
    pos_ = []
    if rows_ and 32 <= len(address or '') <= 44:
        code_, b_ = await rs._jl_borrow('GET', 'positions', params={'users': address})
        pos_ = _lb.positions(b_, {r_['vaultId']: r_ for r_ in rows_}) if code_ == 200 else []
    return {'markets': rows_, 'positions': pos_, 'maxUsd': _lb.MAX_USD}


@router.get('/api/reputation/fuses/prime')
async def fuse_prime():
    """⭐ Arena Prime cards — single-flight + stale-while-revalidate over `_fuse_prime_build` (every viewer and poller shares ONE build)."""
    rs = _rs()
    if rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return await rs._fuse_prime_build()
    if rs._prime_resp['data'] is None and not rs._prime_resp.get('snapTried') and not rs._prime_resp['cleared']:
        rs._prime_resp['snapTried'] = True
        sn = rs._prime_snapshot()
        if sn:
            rs._prime_resp.update(at=sn[0], data=sn[1], snap=True)
    age = rs.time.time() - rs._prime_resp['at']
    t = rs._prime_resp.get('task')
    if rs._prime_resp['data'] is not None and age < rs.PRIME_FRESH_SEC:
        return rs._prime_resp['data']
    if t is None or t.done():
        t = rs._prime_resp['task'] = rs.asyncio.create_task(rs._prime_resp_build())
    if rs._prime_resp['data'] is not None and (age < rs.PRIME_STALE_SEC or rs._prime_resp.get('snap')):   # a snapshot is served while ONE build runs
        return rs._prime_resp['data']
    return await rs.asyncio.shield(t)


@router.get('/api/reputation/evolution/{role}')
async def evolution_lab(role: str):
    rs = _rs()
    if role != 'reaper':
        raise rs.HTTPException(404, 'Only Reaper has replayable exits today.')
    return await rs.asyncio.to_thread(rs._evo_view, role)


@router.get('/api/reputation/fuse-card/{name}')
async def fuse_card_public(name: str, request: Request):
    """Public card files: collection.json, {fid}.json (Metaplex metadata), {fid}.svg (image)."""
    rs = _rs()
    if name == 'collection.json':
        return {'name': 'FEELESS Fuse Cards', 'symbol': 'FUSE', 'description': 'Each card is one published FEELESS Fuse. Its holder earns that Fuse\'s creator cut.',
                'image': f'{rs._site(request)}/api/reputation/fuse-card/collection.svg'}
    m = rs._re.match(r'^([a-f0-9]{6,16}|collection)\.(json|svg)$', name)
    store = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
    if not m:
        raise rs.HTTPException(404, 'Not found')
    if m.group(1) == 'collection':
        view = {'name': 'Fuse Cards', 'score': {'grade': 'A'}, 'legs': []}
    else:
        f = store['fuses'].get(m.group(1))
        if not f:
            raise rs.HTTPException(404, 'Not found')
        view = await rs._fuse_view(m.group(1), f, store)
    if m.group(2) == 'svg':
        return rs.Response(rs._hq.card_svg(view), media_type='image/svg+xml', headers={'Cache-Control': 'public, max-age=600'})
    return rs._hq.card_meta(m.group(1), view, rs._site(request))


@router.get('/api/reputation/vaults/pools')
async def vault_pool_search(q: str = Query(..., min_length=2, max_length=60)):
    """Pool picker for the vault designer: real pools only, tagged v2 (constant product) or v3 (concentrated)."""
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=8) as http:
        try:
            pairs = ((await http.get('https://api.dexscreener.com/latest/dex/search', params={'q': q})).json() or {}).get('pairs') or []
        except Exception:
            pairs = []
    # Solana ONLY (DexScreener search returns every chain — Base/ETH rows are dropped here), deepest first, and the real
    # coin flagged (✓ REAL major mint vs ⚠ lookalike ticker) the same way the Fuse Lab search does.
    pairs = sorted((p for p in rs._fuse.real_pools(pairs) if p.get('chainId') == 'solana'), key=lambda p: -rs._fuse._f((p.get('liquidity') or {}).get('usd')))[:15]
    rows = [{'chainId': 'solana', 'pairAddress': p.get('pairAddress'), 'kind': rs._vault.kind_of(p), 'venue': p.get('dexId'), **rs._fuse.leg_meta(p)} for p in pairs]
    return {'pools': rs._fuse.mark_real(rows, q)}


@router.get('/api/reputation/approvals/{address}')
async def token_approvals(address: str, request: Request):
    """🛡 APPROVALS CHECK (web3 defence for every user): the wallet's token accounts that let ANOTHER address move tokens (an SPL delegate —
    what a drainer leaves behind). Read-only; the page builds the revoke and the wallet signs it. 20 checks an hour per IP."""
    rs = _rs()
    if not rs._re.match(rs._B58, address or ''):
        raise rs.HTTPException(400, 'Not a Solana address.')
    if not await rs._ip_hit(rs._appr_hits, request, 20, 3600):
        raise rs.HTTPException(429, 'Too many checks from here — try again in a while.')
    now = rs.time.time()
    out = []
    async with rs.httpx.AsyncClient(timeout=12) as http:
        res = await rs.asyncio.gather(*[rs._rpc(http, 'getTokenAccountsByOwner', [address, {'programId': pid_}, {'encoding': 'jsonParsed'}])
                                     for pid_ in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')], return_exceptions=True)
    for pid_, r_ in zip(('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'), res):
        for a_ in ((r_ or {}).get('value') or []) if isinstance(r_, dict) else []:
            info_ = ((((a_.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {})
            if info_.get('delegate'):
                out.append({'account': a_.get('pubkey'), 'mint': info_.get('mint'), 'delegate': info_['delegate'], 'program': pid_,
                            'amount': ((info_.get('delegatedAmount') or {}).get('uiAmountString')), 'balance': ((info_.get('tokenAmount') or {}).get('uiAmountString'))})
    return {'address': address, 'approvals': out, 'checked': len(res), 'at': now}


@router.get('/api/reputation/internal/fees')
async def internal_fees(request: Request, wallet: str = '', inputMint: str = '', outputMint: str = '', bundle: int = Query(0, ge=0, le=12), amount: float = Query(0, ge=0), card: int = Query(0, ge=0, le=1), cardId: str = Query('', max_length=16)):
    rs = _rs()
    if not rs.hmac.compare_digest(request.headers.get('x-feeless-internal', ''), rs._internal_key()):
        raise rs.HTTPException(403, 'Internal only.')
    out = await rs.effective_fee(wallet, inputMint, outputMint, bundle, amount, card, cardId)
    return {**out, 'bps': 0, 'notes': ['Agent wallet: a flat fee per trade instead of a % fee.']} if wallet in rs._agent_wallets() else out


@router.get('/api/reputation/case/{address}')
async def case_file(address: str, fresh: bool = False):
    """One case file for any Solana address: a coin (risk score, holder clusters, launch forensics, the creator's
    case) or a wallet (verdict, cited evidence, funding trail, launches, linked wallets, caller behaviour)."""
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        raise rs.HTTPException(400, 'Paste a Solana wallet or coin address.')
    hit = rs._case_cache.get(address)
    if hit and rs.time.time() - hit[0] < (20 if fresh and hit[1].get('kind') == 'coin' else 120):
        return hit[1]
    if fresh and (rs._intel_cache.get(address) or (0,))[0] < rs.time.time() - 30:
        rs._intel_cache.pop(address, None)            # live coin case: re-read holders / snipers at most every 30s
    async with rs.httpx.AsyncClient(timeout=12) as http:
        auth = await rs._mint_authorities(http, address)
    out = await (rs._coin_case(address, auth) if auth else rs._wallet_case(address))
    if out.get('kind') == 'coin':   # live until its volume dies (−85% from peak)
        try:
            async with rs.httpx.AsyncClient(timeout=8) as http:
                prs = (await http.get(f'https://api.dexscreener.com/tokens/v1/solana/{address}')).json() or []
            top = max(prs, key=lambda p: (p.get('volume') or {}).get('h1') or 0) if prs else {}
            vol = top.get('volume') or {}
            st = rs.investigate.live_state(vol.get('m5'), vol.get('h1'), rs._case_peak.get(address, 0))
            rs._case_peak[address] = st['peakPerH']
            out['live'] = st
        except Exception:
            out['live'] = {'live': False, 'pctOfPeak': None}
    out['at'] = rs.time.time()
    rs._case_cache[address] = (rs.time.time(), out)
    if len(rs._case_cache) > 3000:
        rs._case_cache.clear()
    return out


@router.get('/api/reputation/stats')
async def live_stats():
    # Many viewers, one computation: recompute at most every 15s (and never concurrently).
    rs = _rs()
    if rs._stats_cache['data'] and rs.time.time() - rs._stats_cache['at'] < 15:
        return rs._stats_cache['data']
    if rs._stats_cache['lock'] is None:
        rs._stats_cache['lock'] = rs.asyncio.Lock()
    async with rs._stats_cache['lock']:
        if rs._stats_cache['data'] and rs.time.time() - rs._stats_cache['at'] < 15:
            return rs._stats_cache['data']
        data = await rs._live_stats_compute()
        rs._stats_cache.update(at=rs.time.time(), data=data)
        return data


@router.get('/api/reputation/referral/{address}')
async def referral_info(address: str):
    rs = _rs()
    a = rs.primary_of(address)
    d = rs._json_load(rs.REF_PATH, {'by': {}, 'of': {}})
    invited = d['by'].get(a, [])
    earned = rs._json_load(rs.REF_EARN_PATH, {}).get(a) or {}
    return {'address': a, 'code': rs.invite_code(a), 'handle': rs.handle_of(a), 'invited': len(invited), 'recent': invited[-10:][::-1], 'invitedBy': d['of'].get(a),
            'pct': float(rs._json_load(rs.REF_CFG_PATH, {}).get('pct') or 0), 'earnedUsd': earned.get('usd', 0), 'earnedSol': earned.get('sol', 0),
            'paidUsd': earned.get('paidUsd', 0), 'tradingInvitees': len(earned.get('invitees') or [])}


@router.get('/api/reputation/dm/{peer}')
async def dm_thread(peer: str, address: str, session: str):
    rs = _rs()
    me = rs._session_or_401(address, session)
    return {'me': me, 'peer': rs.primary_of(peer), 'messages': rs._json_load(rs.DM_PATH, {}).get(rs._dm_key(me, peer), [])[-150:]}


@router.get('/api/reputation/portfolio/{address}')
async def portfolio(address: str, fresh: int = 0):
    rs = _rs()
    a = rs.primary_of(address)
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a):
        return {'address': a, 'supported': False, 'tokens': [], 'totalUsd': None}
    hit = rs._pf_cache.get(a)
    if hit and rs.time.time() - hit[0] < (8 if fresh else 90):   # fresh=1 right after a trade (still shielded from hammering)
        return hit[1]
    if hit and not fresh and rs.time.time() - hit[0] < rs.PF_STALE_SEC:   # ⚡ answer the last copy now, refresh behind it (one at a time per wallet)
        if a not in rs._pf_busy:
            rs._pf_busy.add(a)
            async def _bg():
                try:
                    await rs._portfolio_build(a)
                finally:
                    rs._pf_busy.discard(a)
            rs.asyncio.create_task(_bg())
        return hit[1]
    return await rs._portfolio_build(a)


@router.get('/api/reputation/wallet-trades/{address}')
async def wallet_trades_ep(address: str):
    rs = _rs()
    if not (rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) or rs._re.match(r'^0x[0-9a-fA-F]{40}$', address)):
        raise rs.HTTPException(400, 'Bad address.')
    rows_ = await rs.wallet_trades(address)
    return {'address': address, 'trades': rows_, 'source': 'Solana RPC' if rows_ and rows_[0].get('source') == 'rpc' else 'Helius'}


@router.get('/api/reputation/copy/check/{address}')
async def copy_check(address: str):
    """Is this wallet safe to mirror? Trust, sniper record, funder links and KOL dump pattern — any
    red flag pauses copying automatically."""
    rs = _rs()
    a = rs.primary_of(address)
    t = await rs.trust_score(a)
    bl = rs._block_load()['wallets'].get(a)
    fd = rs._funders_load(); frec = fd['funders'].get(a)
    kol = rs._kol_cache.get(a, (0, None))[1]
    reasons = []
    if bl and rs._is_blocked(bl): reasons.append('blocklisted for sniping/bundling')
    elif bl: reasons.append('caught sniping/bundling')
    if frec and rs._is_flagged_funder(frec): reasons.append('bankrolls sniper wallets')
    if kol and kol.get('danger'): reasons.append('call-and-dump pattern')
    if (t.get('score') or 0) < 45: reasons.append(f"low trust ({t.get('score')})")
    return {'address': a, 'trust': t.get('score'), 'safe': not reasons, 'reasons': reasons}


@router.get('/api/reputation/launch-radar')
async def launch_radar(limit: int = Query(30, ge=1, le=100)):
    rs = _rs()
    launches = sorted((rs._load().get('feelessLaunches') or {}).values(), key=lambda l: -(l.get('at') or 0))[:limit]
    shields = rs._json_load(rs.SHIELD_PATH, {})
    rows, queued = [], 0
    for l in launches:
        hit = rs._intel_cache.get(l['mint'])
        intel = hit[1] if hit else None
        if not hit and queued < 3:
            queued += 1; rs.asyncio.create_task(rs._quiet(rs._runner_intel(l['mint'], rs._enr.PRIO['HELD'], 'card leg')))
        w = rs.primary_of(l['wallet'])
        t = rs._trust_cache.get(w)
        if not t and w not in rs._trust_pending and len(rs._trust_pending) < 8:
            rs._trust_pending.add(w); rs.asyncio.create_task(rs._trust_fill(w))
        sh = shields.get(l['mint'])
        rows.append({'mint': l['mint'], 'symbol': l.get('symbol'), 'creator': w, 'rail': l.get('rail') or 'feeless', 'config': l.get('config'), 'at': l.get('at'),
                     'snipers': None if not intel else len(intel.get('sniperWallets') or []) + len(intel.get('bundledWallets') or []),
                     'shield': None if not sh else ('broken' if sh.get('broken') else 'active'),
                     'rep': None if not t else {'score': t[1].get('score'), 'level': t[1].get('level')}, 'gold': rs._gold_creator(w)})
    return {'launches': rows}


@router.get('/api/reputation/fee-report/{address}')
async def fee_report_get(address: str):
    """FEELESS fees this wallet paid (7d + all time, linked accounts count once), the FeeBack accrued / paid / owed,
    how much of the fees came back, and what the wallet earned meanwhile (XP, rep, points, badge fee perk)."""
    rs = _rs()
    if not rs._re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', address):
        raise rs.HTTPException(400, 'Bad address.')
    me = rs.primary_of(address)
    rep = rs.fee_report.fee_report(rs._json_load(rs.FEE_LEDGER_PATH, {}).get(me) or [], rs.time.time())
    paid = round(float(rs._json_load(rs.FEEBACK_PAID_PATH, {}).get(me, 0) or 0), 6)
    # What you earned while paying those fees: XP/level + badge fee perk (quests), rep verdict, season points.
    try:
        q = await rs._quest_summary(me)
        quest = {'xp': q['level']['xp'], 'level': q['level']['name'], 'badges': q['earned'], 'badgeFeeDiscountPct': q['perks']['feeDiscountPct'],
                 'badgeFeeFrom': q['perks']['from'].get('fee'), 'seasonXp': q['season']['score']}
    except Exception:
        quest = {}
    qr = rs._quick_rep(me)
    fees = rep.get('feesTotalUsd') or 0
    back = rep.get('feeBackUsd') or 0
    return {'address': address, **rep, 'feeBackPaidUsd': paid, 'feeBackOwedUsd': round(max(0.0, back - paid), 6),
            'paidBackPct': round(back / fees * 100, 1) if fees else 0.0,
            'earned': {**quest, 'rep': {'score': qr.get('score'), 'label': qr.get('label')}, 'points': int((rs._pts().get(me) or {}).get('total') or 0)}}


@router.get('/api/reputation/wallet-watch')
async def watch_list(address: str, session: str):
    rs = _rs()
    me = rs._session_or_401(address, session)
    d = rs._json_load(rs.WATCH_PATH, {'targets': {}})
    return {'targets': [{'address': t, **rs._quick_rep(t)} for t, ws in d['targets'].items() if me in ws]}


@router.get('/api/reputation/verify/{mint}')
async def verify_one(mint: str, fresh: bool = False):
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', mint):
        raise rs.HTTPException(400, 'Bad mint.')
    hit = rs._verify_cache.get(mint)
    if hit and not fresh and rs.time.time() - hit[0] < rs.VERIFY_TTL:
        return hit[1]
    return await rs._verify_run(mint)


@router.get('/api/reputation/internal/circle-wallet')
async def internal_circle_wallet(request: Request, address: str = ''):
    rs = _rs()
    if not rs._internal_ok(request):
        raise rs.HTTPException(403, 'Internal only.')
    w_ = next((w for w in (await rs._circle_wallets_live()) or [] if w.get('address') == address), None)
    if not w_:
        raise rs.HTTPException(404, 'Not a Circle wallet of this project.')
    return {'id': w_.get('id'), 'address': w_.get('address')}


@router.get('/api/reputation/leaderboard')
async def leaderboard(chain: Optional[str] = Query(None), view: str = Query('trusted')):
    rs = _rs()
    if view not in rs.LEADERBOARD_VIEWS:
        view = 'trusted'
    store = rs._load()
    now = rs.time.time()
    rows = []
    for entry in store['creators'].values():
        if chain and entry['chain'] != chain:
            continue
        scoring = rs.score_creator(entry)
        rows.append({
            'chain': entry['chain'], 'address': entry['address'],
            'firstSeen': entry['firstSeen'], 'lastSeen': entry['lastSeen'],
            **scoring,
        })

    if view == 'feeless':
        launches = store.get('feelessLaunches', {})
        by_creator = {}
        for l in launches.values():
            by_creator.setdefault(rs._creator_key(l['chain'], l['wallet']), []).append(l)
        rows = [{**r, 'feelessLaunches': len(by_creator[rs._creator_key(r['chain'], r['address'])])} for r in rows if rs._creator_key(r['chain'], r['address']) in by_creator]
        rows.sort(key=lambda r: (-r['bigWinners'], r['dumpedCount'], -(r['score'] or 0)))
    elif view == 'flagged':
        rows = [r for r in rows if r['badge'] == 'flagged' or r['dumpedCount'] >= 2]
        rows.sort(key=lambda r: (-r['ruggedCount'], -r['dumpedCount'], -r['tokenCount']))
    elif view == 'serial':
        # Highest launch volume, regardless of outcome — the wallets flooding the market.
        rows = [r for r in rows if r['tokenCount'] >= 2]
        rows.sort(key=lambda r: (-r['tokenCount'], -r['ruggedCount']))
    elif view == 'rising':
        # New creators (first seen recently) already showing a clean, decent score.
        rows = [r for r in rows if r['badge'] != 'flagged' and r['dumpedCount'] == 0 and (now - r['firstSeen']) <= rs.RISING_WINDOW_SECONDS]
        rows.sort(key=lambda r: (-(r['score'] or 0), r['firstSeen']))
    elif view == 'active':
        rows = [r for r in rows if r['badge'] != 'flagged']
        rows.sort(key=lambda r: -(r['lastSeen'] or 0))
    else:
        rows = [r for r in rows if r['badge'] != 'flagged' and r['dumpedCount'] == 0]
        rows.sort(key=lambda r: (r['badge'] != 'trusted', -(r['score'] or 0), -(r['tokenCount'] or 0)))

    return {
        'rows': rows[:50], 'view': view,
        'totalCreators': len(store['creators']),
        'totalTokensTracked': sum(len(e['tokens']) for e in store['creators'].values()),
    }


@router.get('/api/reputation/watchlist')
async def get_watchlist(ownerWallet: str):
    rs = _rs()
    store = rs._load()
    bucket = store['watchlists'].get(ownerWallet, {})
    rows = []
    for watch in bucket.values():
        ckey = rs._creator_key(watch['chain'], watch['address'])
        entry = store['creators'].get(ckey)
        scoring = rs.score_creator(entry) if entry else {'score': None, 'badge': 'unproven', 'tokenCount': 0, 'ruggedCount': 0, 'sustainedCount': 0, 'renouncedCount': 0}
        rows.append({**watch, **scoring})
    rows.sort(key=lambda r: -r['addedAt'])
    return {'rows': rows}


@router.get('/api/reputation/clusters')
async def get_clusters(chain: Optional[str] = Query('solana')):
    """Groups tracked creators by shared on-chain funding source. A cluster of 2+
    creator wallets funded by the same upstream wallet is a real signal that they're
    the same operator running multiple "clean" identities — this is the analysis no
    other launchpad terminal surfaces."""
    rs = _rs()
    async with rs._lock:
        store = rs._load()
        creators = [e for e in store['creators'].values() if not chain or e['chain'] == chain]
        resolved_this_call = 0
        for entry in creators:
            fkey = rs._creator_key(entry['chain'], entry['address'])
            if fkey not in store['funding']:
                if resolved_this_call >= rs.CLUSTER_RESOLVE_BATCH:
                    continue
                store['funding'][fkey] = await rs.resolve_funding_source(entry['chain'], entry['address'])
                resolved_this_call += 1
        if resolved_this_call:
            rs._save(store)

        groups: dict[str, list] = {}
        for entry in creators:
            fkey = rs._creator_key(entry['chain'], entry['address'])
            source = store['funding'].get(fkey)
            if not source:
                continue
            groups.setdefault(source, []).append(entry)

        clusters = []
        for source, members in groups.items():
            if len(members) < 2:
                continue
            scored = [{'address': m['address'], 'chain': m['chain'], **rs.score_creator(m)} for m in members]
            clusters.append({
                'fundingSource': source,
                'members': sorted(scored, key=lambda r: -(r['score'] or 0)),
                'totalTokens': sum(m['tokenCount'] for m in scored),
                'totalFlags': sum(m['ruggedCount'] for m in scored),
            })
        clusters.sort(key=lambda c: (-c['totalFlags'], -len(c['members'])))

    pending = sum(1 for e in creators if rs._creator_key(e['chain'], e['address']) not in store['funding'])
    return {'clusters': clusters, 'creatorsScanned': len(creators), 'pendingResolution': pending}


@router.get('/api/reputation/roadmap/votes')
async def roadmap_votes(wallet: Optional[str] = None):
    rs = _rs()
    store = rs._load()
    votes = store.setdefault('votes', {})
    return {'counts': {k: len(v) for k, v in votes.items()}, 'mine': [k for k, v in votes.items() if wallet and wallet in v]}


@router.get('/api/reputation/intel/{chain}/{mint}')   # ⚠ keep this decorator ON token_intel: a helper inserted under it (2026-10-11) bound the route to the helper and every read answered 422
async def token_intel(chain: str, mint: str):
    """On-chain launch forensics for a token: bundles, snipers, holder concentration, dev bag.
    Bundled = distinct wallets (not the creator) buying in the mint's creation slot.
    Snipers  = distinct wallets buying within the next 3 slots (~1.2s)."""
    rs = _rs()
    if chain != 'solana':
        raise rs.HTTPException(400, 'On-chain forensics currently cover Solana.')
    hit = rs._intel_cache.get(mint)
    if hit and rs.time.time() - hit[0] < rs.INTEL_TTL:
        return hit[1]
    out = {'mint': mint, 'checkedAt': rs.time.time()}
    async with rs.httpx.AsyncClient(timeout=12) as http:
        supply_res, largest = await rs.asyncio.gather(
            rs._rpc(http, 'getTokenSupply', [mint]), rs._rpc(http, 'getTokenLargestAccounts', [mint]), return_exceptions=True)
        supply = float(((supply_res or {}).get('value') or {}).get('uiAmount') or 0) if isinstance(supply_res, dict) else 0
        if not supply and mint.endswith(('pump', 'bonk')):   # launchpad coins mint exactly 1B — an RPC hiccup must not blank the scan
            supply = 1_000_000_000.0
        holders = ((largest or {}).get('value') or []) if isinstance(largest, dict) else []
        owners = {}
        if holders:
            accs = await rs._rpc(http, 'getMultipleAccounts', [[h['address'] for h in holders], {'encoding': 'jsonParsed'}])
            for h, a in zip(holders, (accs or {}).get('value') or []):
                owners[h['address']] = rs._parsed_info(a).get('owner')
            owner_list = [o for o in owners.values() if o]
            kinds = {}
            if owner_list:
                oaccs = await rs._rpc(http, 'getMultipleAccounts', [owner_list, {'encoding': 'base64'}])
                for o, a in zip(owner_list, (oaccs or {}).get('value') or []):
                    # Wallets are system-owned (or don't exist yet); pools/curves are program-owned PDAs.
                    kinds[o] = 'wallet' if (a is None or a.get('owner') == rs.SYSTEM_PROGRAM) else 'program'
        rows = []
        for h in holders:
            owner = owners.get(h['address'])
            amt = float(h.get('uiAmount') or 0)
            rows.append({'owner': owner, 'amount': amt, 'pct': (amt / supply * 100) if supply else None,
                         'kind': kinds.get(owner, 'wallet') if owner else 'unknown'})
        wallets = [r for r in rows if r['kind'] == 'wallet']
        out['supply'] = supply
        out['topHolders'] = rows[:12]
        out['top10Pct'] = round(sum(r['pct'] or 0 for r in wallets[:10]), 2) if supply else None
        out['poolPct'] = round(sum(r['pct'] or 0 for r in rows if r['kind'] == 'program'), 2) if supply else None
        if not holders:   # 🩺 NO HOLDER READING IS NOT "0% HELD": a refused / empty getTokenLargestAccounts used to be cached as top-10 = 0% (a clean-looking scan)
            out['top10Pct'] = None   # for the whole TTL — running coins read 'scanned, top-10 0' and the board called them unscanned. None = incomplete → retried in 60s
            out['poolPct'] = None

        # 🧬 LAUNCH FACTS NEVER CHANGE. Who created the coin and who bought in its first slots is read ONCE per coin
        # (`_launch_facts`, kept on disk); every later scan re-reads only the holders (4 calls instead of ~60). The full scan every
        # 3 minutes for ~70 coins was ~80K calls an hour — it rate-limited every key, and coins sat "unscanned" for good.
        creator, bundled, snipers = None, set(), set()
        lf = rs._launch_facts.get(mint)
        if lf and lf.get('historyComplete') is False and rs.time.time() - rs._fuse._f(lf.get('at')) >= rs.LAUNCH_RETRY_SEC:   # an unread launch is retried after 6h (it re-burned 8 calls every 15 min)
            lf = None
        if lf:
            creator, bundled, snipers = lf.get('creator'), set(lf.get('bundled') or []), set(lf.get('snipers') or [])
            out['createSlot'] = lf.get('createSlot'); out['historyComplete'] = lf.get('historyComplete')
        else:
            # 🧬 page back to the LAUNCH (≤ SIG_PAGES × 1000 txs): a busy coin has > 1000 txs, and the "oldest of the last 1000" was a random
            # mid-life trader — read as the creator, with 0 bundled / 0 snipers (2026-10-08 $giftr: wrong creator, real creator held 4.4%).
            sigs, before, page, early_buys = [], None, [], []
            for _ in range(rs.SIG_PAGES):
                page = await rs._rpc(http, 'getSignaturesForAddress', [mint, {'limit': 1000, **({'before': before} if before else {})}]) or []
                sigs += page
                if len(page) < 1000:
                    break
                before = page[-1].get('signature')
            if (sigs and len(page) >= 1000) or not sigs:   # still not at the launch (or the RPC answered nothing): unknown, never a fake 0 bundles
                out['createSlot'], out['historyComplete'] = None, False
                if sigs:   # remembered: not paged again for LAUNCH_RETRY_SEC
                    rs._launch_facts[mint] = {'creator': None, 'bundled': [], 'snipers': [], 'createSlot': None, 'historyComplete': False, 'at': rs.time.time(), 'early': []}
                sigs = []
            if sigs:
                oldest = sorted(sigs, key=lambda x: (x.get('slot') or 0))[:40]
                create_slot = oldest[0].get('slot')
                early = [x for x in oldest if not x.get('err')][:28]   # 🕵 the first ~25 buyers (bundles / snipers still judged by slot below)
                sem = rs.asyncio.Semaphore(6)

                async def fetch(sig):
                    async with sem:
                        try:
                            return await rs._rpc(http, 'getTransaction', [sig['signature'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}])
                        except Exception:
                            return None
                txs = await rs.asyncio.gather(*(fetch(x) for x in early))
                for tx in sorted([t for t in txs if t], key=lambda t: t.get('slot') or 0):
                    keys = ((tx.get('transaction') or {}).get('message') or {}).get('accountKeys') or []
                    payer = keys[0].get('pubkey') if keys and isinstance(keys[0], dict) else (keys[0] if keys else None)
                    if not payer:
                        continue
                    if creator is None:
                        creator = payer
                        continue
                    if payer == creator:
                        continue
                    if (tx.get('slot') or 0) <= create_slot + 3:
                        (bundled if tx.get('slot') == create_slot else snipers).add(payer)
                    eb = rs._early_buy(tx, payer, mint, supply)
                    if eb and payer not in {e['w'] for e in early_buys}:
                        early_buys.append(eb)
                snipers -= bundled
                out['createSlot'] = create_slot
                out['historyComplete'] = True
            if creator:
                rs._launch_facts[mint] = {'creator': creator, 'bundled': sorted(bundled), 'snipers': sorted(snipers), 'createSlot': out.get('createSlot'),
                                       'historyComplete': out.get('historyComplete'), 'at': rs.time.time(), 'early': early_buys[:25]}
        if mint.endswith('pump') and not rs.os.environ.get('PYTEST_CURRENT_TEST'):   # 🟢 Pump's own record names the creator — it wins over our read (cached 60s, public)
            try:
                pc = (await rs.pump_profile_get(mint) or {}).get('creator')
                if pc:
                    creator = pc
            except Exception:
                pass
        out['creator'] = creator
        known = out.get('historyComplete') is not False   # launch never reached → bundles / snipers UNKNOWN, never a fake 0
        out['bundledWallets'] = sorted(bundled) if known else None
        out['sniperWallets'] = sorted(snipers) if known else None
        insiders = bundled | snipers
        out['insidersHoldingPct'] = round(sum(r['pct'] or 0 for r in wallets if r['owner'] in insiders), 2) if supply and known else None
        out['snipersHoldingPct'] = round(sum(r['pct'] or 0 for r in wallets if r['owner'] in snipers), 2) if supply and known else None
        out['bundledHoldingPct'] = round(sum(r['pct'] or 0 for r in wallets if r['owner'] in bundled), 2) if supply and known else None
        out['devHoldingPct'] = round(sum(r['pct'] or 0 for r in wallets if r['owner'] == creator), 2) if supply and creator else None
        # Live holding of every flagged wallet (not just top holders): 0 = sold out, shown struck through.
        if supply:
            early_w = [e['w'] for e in ((rs._launch_facts.get(mint) or {}).get('early') or [])]
            flagged = list(dict.fromkeys(sorted(bundled) + sorted(snipers) + early_w))[:36]   # 🕵 + the first buyers: what the early wallets did since
            sem = rs.asyncio.Semaphore(8)
            async def bal(w):
                async with sem:
                    try:
                        r = await rs._rpc(http, 'getTokenAccountsByOwner', [w, {'mint': mint}, {'encoding': 'jsonParsed'}])
                        amt = sum(float(((a['account']['data']['parsed']['info'].get('tokenAmount') or {}).get('uiAmount')) or 0) for a in (r or {}).get('value') or [])
                        return w, round(amt / supply * 100, 3)
                    except Exception:
                        return w, None
            fh_hit = rs._flag_hold.get(mint)   # each flagged wallet's live balance = 1 call per wallet: re-read at most every 15 min
            reuse = bool(fh_hit and rs.time.time() - fh_hit[0] < rs.FLAG_HOLD_TTL)
            out['flaggedHoldings'] = fh_hit[1] if reuse else dict(await rs.asyncio.gather(*(bal(w) for w in flagged)))
            if not reuse:
                rs._flag_hold[mint] = (rs.time.time(), out['flaggedHoldings'])
            fh = out['flaggedHoldings']
            if not reuse and len(fh) >= 3 and all(v == 0 for v in fh.values()):
                # Every sniper/bundler has sold out: the supply overhang is gone — often the dip entry.
                # Alerts link to the coin's deepest pool so the Trenches chart opens on it.
                coin = await rs._coin_card(http, mint)
                url = f"/terminal/chat?chain=solana&pair={coin['pair']}&room=bulls"
                if rs._radar_event('snipers-out', coin['pair'], coin['symbol'], f"All {len(fh)} flagged snipers/bundlers sold out. No sniper supply left to dump.",
                                mint=mint, mcap=coin['mcap'], name=coin['name'], cooldown=rs.SNIPERS_OUT_COOLDOWN):
                    rs.asyncio.create_task(rs._push_snipers_out(mint))
                # The creator hears it once per coin (it used to repeat on every intel refresh).
                if creator:
                    rs.notify(creator, 'snipers', f"Every sniper on your coin {coin['symbol']} has sold out", url, once=f'snipers:{mint}',
                           meta={'mint': mint, 'symbol': coin['symbol'], 'name': coin['name'], 'mcap': coin['mcap'], 'flagged': len(fh)})
    flags = []
    if len(out['bundledWallets'] or []) >= 3:
        flags.append(f"{len(out['bundledWallets'] or [])} wallets bought in the same block as the mint — a bundled launch.")
    if len(out['sniperWallets'] or []) >= 5:
        flags.append(f"{len(out['sniperWallets'] or [])} wallets sniped within ~1 second of launch.")
    if (out.get('insidersHoldingPct') or 0) >= 10:
        flags.append(f"Bundlers/snipers still hold {out['insidersHoldingPct']}% of supply among the top holders.")
    if (out.get('top10Pct') or 0) >= 35:
        flags.append(f"Top 10 wallets hold {out['top10Pct']}% of supply (excluding pools).")
    if (out.get('devHoldingPct') or 0) >= 5:
        flags.append(f"Creator still holds {out['devHoldingPct']}% of supply.")
    all_offenders = (out.get('bundledWallets') or []) + (out.get('sniperWallets') or [])
    flagged_funders = {w: rs.funder_lookup(w) for w in all_offenders}
    flagged_funders = {w: v for w, v in flagged_funders.items() if v}
    if flagged_funders:
        distinct_funders = {v['funder'] for v in flagged_funders.values()}
        flags.append(f"{len(flagged_funders)} sniper/bundler wallet(s) here were funded by {len(distinct_funders)} wallet(s) already linked to prior rug/snipe launches.")
    try:   # the Intel desk: are known crews inside this launch?
        crew = rs.intel_desk.check((await rs._desk_get())['snap']['index'], rs._desk['rings'], all_offenders + ([creator] if creator else []))
    except Exception:
        crew = {'known': {}, 'rings': []}
    out['knownActors'] = len(crew['known'])
    out['knownRings'] = crew['rings']
    if crew['rings']:
        r0 = max(crew['rings'], key=lambda r: r['threat'])
        rugs = f", {r0['rugs']} rugs" if r0['rugs'] else ''
        flags.append(f"Known crew inside: ring {r0['id']} ({r0['size']} wallets, {r0['launchesHit']} launches hit{rugs}).")
    out['flags'] = flags
    out['flaggedFunders'] = flagged_funders
    await rs._record_offenders(mint, out.get('bundledWallets') or [], out.get('sniperWallets') or [])
    bl = rs._block_load()
    out['walletRecords'] = {w: {'strikes': len(bl['wallets'].get(w, {}).get('mints', {})), 'blocked': rs._is_blocked(bl['wallets'].get(w)),
                                 'flaggedFunder': flagged_funders.get(w)}
                            for w in all_offenders}
    rs._intel_cache[mint] = (rs.time.time(), out)
    if out.get('top10Pct') is not None:
        rs._ENRICH.note_success(mint, rs.time.time())   # (a scan a user asked for directly is fresh evidence for the scheduler too)
    try:
        rs._absorb_intel(mint, out)
    except Exception:
        pass
    return out


@router.get('/api/reputation/calls/hot')
async def hot_calls(minutes: int = Query(60, ge=5, le=1440)):
    rs = _rs()
    since = rs.time.time() - minutes * 60
    agg = {}
    for c in rs._calls_load()['calls'].values():
        if c['at'] < since:
            continue
        v = rs._call_view(c)
        a = agg.setdefault(c['pairAddress'], {'symbol': c['symbol'], 'imageUrl': c.get('imageUrl'), 'chain': c['chain'], 'pairAddress': c['pairAddress'], 'callers': set(), 'calls': 0, 'firstX': v['x']})
        a['calls'] += 1
        a['callers'].add(c['caller'])
        a['x'] = v['x']
    rows = [{**{k: v for k, v in a.items() if k != 'callers'}, 'callers': len(a['callers'])} for a in agg.values()]
    rows.sort(key=lambda r: (-r['callers'], -r['calls']))
    return {'rows': rows[:12], 'minutes': minutes}


@router.get('/api/reputation/calls/by-room')
async def calls_by_room(room: str):
    rs = _rs()
    out = {}
    for c in rs._calls_load()['calls'].values():
        if c['room'] == room[:80] and c.get('messageId'):
            v = rs._call_view(c)
            out.setdefault(c['messageId'], []).append({'symbol': v['symbol'], 'x': v['x'], 'peakX': v['peakX'], 'mcAtCall': v['mcAtCall'], 'pairAddress': v['pairAddress']})
    return {'calls': out}


@router.get('/api/reputation/balance/{owner}/{mint}')
async def token_balance(owner: str, mint: str):
    """UI-unit balance of a token for a wallet (Solana), used for quick sells."""
    rs = _rs()
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            if mint == 'So11111111111111111111111111111111111111112':
                r = await rs._rpc(http, 'getBalance', [owner])
                return {'amount': ((r or {}).get('value') or 0) / 1e9, 'decimals': 9, 'raw': str((r or {}).get('value') or 0)}
            r = await rs._rpc(http, 'getTokenAccountsByOwner', [owner, {'mint': mint}, {'encoding': 'jsonParsed'}])
    except Exception:
        raise rs.HTTPException(502, 'Balance unavailable right now.')
    total, decimals, raw = 0.0, None, 0
    for acc in (r or {}).get('value') or []:
        info = rs._parsed_info(acc.get('account'))
        amt = (info.get('tokenAmount') or {})
        total += float(amt.get('uiAmount') or 0)
        raw += int(amt.get('amount') or 0)
        decimals = amt.get('decimals', decimals)
    return {'amount': total, 'decimals': decimals, 'raw': str(raw)}


@router.get('/api/reputation/blocklist')
async def get_blocklist(limit: int = Query(200, ge=1, le=5000)):
    rs = _rs()
    rows = []
    for w, rec in rs._block_load()['wallets'].items():
        if not rs._is_blocked(rec):
            continue
        roles = list(rec['mints'].values())
        rows.append({'wallet': w, 'strikes': max(len(rec['mints']), int(rec.get('strikes') or 0)), 'bundles': roles.count('bundler'), 'snipes': roles.count('sniper'),
                     'reported': bool(rec.get('reported')), 'auto': len(rec['mints']) >= rs.AUTO_BLOCK_STRIKES, 'lastSeen': rec.get('lastSeen')})
    rows.sort(key=lambda r: (-r['strikes'], -(r['lastSeen'] or 0)))
    return {'wallets': rows[:limit], 'total': len(rows), 'autoThreshold': rs.AUTO_BLOCK_STRIKES}


@router.get('/api/reputation/chart-wallets/{mint}')
async def chart_wallets(mint: str, pair: str = ''):
    """🐋 Who traded this chart — snipers · bundles · dev · top holders (from our own launch + holder scan) · whales · top traders (the tape).
    Public, read-only, 15s cache, the candles service's own trade tape (no extra RPC). Owner, 2026-10-18: "bubbles on each chart"."""
    rs = _rs()
    if not rs._re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', mint or '') or (pair and not rs._re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', pair)):
        raise rs.HTTPException(400, 'bad address')
    hit = rs._cw_cache.get(mint)
    if hit and rs.time.time() - hit[0] < 15:
        return hit[1]
    pair = pair or next((r_.get('pair') for r_ in (rs._agents.get('table') or []) if r_.get('mint') == mint), None) or ''
    tr = []
    if pair:
        got = rs._flow_trades.get(pair)
        if got and rs.time.time() - got[0] < 15:
            tr = got[1]
        elif not rs.os.environ.get('PYTEST_CURRENT_TEST'):
            try:
                async with rs.httpx.AsyncClient(timeout=6) as http:
                    r = await http.get(f'http://127.0.0.1:5099/api/candles/trades/solana/{pair}')
                    tr = (r.json() or {}).get('trades') or []
                    rs._flow_trades[pair] = (rs.time.time(), tr)
            except Exception:
                tr = []
    it = (rs._intel_cache.get(mint) or (0, None))[1] or {}
    out = {**rs._cw.tag_trades(tr, it), 'launchRead': it.get('historyComplete') is not False and bool(it), 'n': len(tr), 'at': round(rs.time.time())}
    rs._cw_cache[mint] = (rs.time.time(), out)
    if len(rs._cw_cache) > 400:
        for k_ in sorted(rs._cw_cache, key=lambda k_: rs._cw_cache[k_][0])[:100]:
            rs._cw_cache.pop(k_, None)
    return out


@router.get('/api/reputation/coin-read/{mint}')
async def coin_read(mint: str):
    """🫀 + 🔥/🎢/🧲 THE FEELESS EDGE for one coin (war room / chart header): its vital (grade, five bars, the three deciding facts, crew) and the
    read that fits it (new coin → SEND IT · on its curve → curve · off its high → dip). Jupiter's audit + our own scan + the runner board's flow.
    Cached 15s per coin. A read, never a promise."""
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', mint or ''):
        raise rs.HTTPException(400, 'Not a Solana mint.')
    hit = rs._coin_read_cache.get(mint)
    pace_ = rs._ja.pace((hit[1].get('row') if hit else None) or rs._cand_map().get(mint) or {})   # ⏱ busier coin → fresher read
    if hit and rs.time.time() - hit[0] < pace_['cacheSec']:
        return hit[1]
    if rs.time.time() - rs._jup_facts.get(mint, (0.0, None))[0] > pace_['jupSec'] and not rs.os.environ.get('PYTEST_CURRENT_TEST'):   # a WATCHED coin's pulse is re-read at its own pace (hot 12s · busy 25s · quiet 45s)
        try:
            t_ = (await rs.asyncio.wait_for(rs._jup_tokens([mint]), timeout=rs.COIN_READ_JUP_SEC)).get(mint)   # ⚡ a busy Jupiter never holds the chart header: the last reading answers
            if t_:
                rs._jup_facts[mint] = (rs.time.time(), rs._ja.facts(t_))
        except Exception:
            pass
    try:
        await rs.asyncio.wait_for(rs._jup_lite([mint]), timeout=rs.COIN_READ_JUP_SEC)
    except Exception:
        pass
    jf = (rs._jup_facts.get(mint) or (0, None))[1]
    c = rs._cand_map().get(mint) or {}
    row = {'mint': mint, 'symbol': c.get('symbol'), **{k: c.get(k) for k in ('ageH', 'vol1h', 'vol5m', 'chg5m', 'chg1h', 'buyShare', 'txns1h', 'mcap', 'liq', 'site', 'x', 'tg') if c.get(k) is not None}}
    row.update(rs._holder_facts(mint))
    rs._ja.fill_row(row, jf, c)
    scanning = False
    if row.get('scanned') is not True and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        # 🔍 a coin someone is LOOKING at gets our full holder scan now (insiders · bundled · snipers — Jupiter's audit has none of them);
        # one scan per coin in flight, the next read of this endpoint carries the result
        scanning = True
        rs.asyncio.ensure_future(rs._runner_intel(mint, rs._enr.PRIO['LOOK'], 'coin read'))
    if c.get('bundled') is not None and row.get('bundledN') is None and row.get('scanned') is True:   # never a 0 from a coin whose launch was not read
        row['bundledN'] = c.get('bundled')
    if jf and row.get('holders') is None:
        row['holders'] = jf.get('holders')
    vital = rs._ja.verdict(jf, row) if jf else None
    tv = rs._read_for(row) or ({**(t_ := rs._ja.trench_verdict(jf, row)), 'kind': 'trench', 'meters': [['🔥 HEAT', t_['heat']], ['☠ RUG', t_['rug']]]} if jf or c else None)
    pc_ = rs._pump_calls['map'].get(mint)
    rs._fd_rows([row])
    tape = None
    if c.get('pairAddress'):   # 🌊 THE TAPE is part of every coin read (chart header, quick look, drawer) — one pool, 12s cache
        try:
            w_ = (await rs._flow_fetch([c['pairAddress']])).get(c['pairAddress'])
            t_ = rs._flow.tape_read(w_)
            tape = {'read': t_, 'label': rs._flow.TAPES.get(t_), 'buyUsd': (w_ or {}).get('buyUsd'), 'sellUsd': (w_ or {}).get('sellUsd'), 'n': (w_ or {}).get('n'), 'pxChg': (w_ or {}).get('pxChg')} if t_ else None
        except Exception:
            tape = None
    out = {'mint': mint, 'row': row, 'vital': vital, 'tv': tv, 'tape': tape, 'facts': jf, 'onBoard': bool(c), 'pc': rs._pc.summary(pc_) if pc_ else None, 'scanning': scanning, 'pace': rs._ja.pace(row), 'at': round(rs.time.time(), 1)}
    rs._coin_read_cache[mint] = (rs.time.time() - (9 if scanning else 0), out)   # waiting on a scan: served 6s, not 15
    if len(rs._coin_read_cache) > 600:
        for k in sorted(rs._coin_read_cache, key=lambda k: rs._coin_read_cache[k][0])[:200]:
            rs._coin_read_cache.pop(k, None)
    return out


@router.get('/api/reputation/fuses/discover')
async def fuses_discover(lens: str = Query('popular'), chain: str = Query('solana')):
    """The picker lists + 🧬 holder facts on every launch-coin row (top-10 · dev · insiders · bundled / sniper wallets, from the scan cache) and
    no dead rows (under $3K traded an hour). The top rows of the list just opened get a scan queued, so the facts fill in while it is open."""
    rs = _rs()
    key_ = (lens, chain)
    got_ = rs._list_now(key_, rs.SIGNAL_CACHE_SEC if lens in rs.SIGNAL_LENSES else rs.LIST_CACHE_SEC, lambda: fuses_discover(lens, chain))
    if got_ is not None:
        return got_
    out = await rs._fuses_discover_raw(lens, chain)
    rs._disc_cache[key_] = (rs.time.time(), out)   # lists returned as they are (majors, pools…); a dressed launch list replaces this below
    rows = out.get('pools') if isinstance(out, dict) else None
    if rows and lens in ('majors', 'stocks', 'risers'):   # 🐋 the majors / stocks tab gets its own TREND read
        try:
            await rs._jup_lite([r.get('baseAddress') or r.get('mint') for r in rows])
        except Exception:
            pass
        for r in rows:
            r['tv'] = rs._read_for(r, {}, lens)
            rs._ja.fill_row(r, (rs._jup_facts.get(r.get('baseAddress') or r.get('mint')) or (0, None))[1])
    if not rows or lens in ('majors', 'stocks', 'popular', 'yield', 'deep', 'new'):
        return out
    live = [r for r in rows if r.get('vol1h') is None or rs._fuse._f(r.get('vol1h')) >= rs.PICK_DEAD_VOL1H]
    await rs._jup_lite([r.get('baseAddress') or r.get('mint') for r in live])
    rs._clean_rows(live)
    if lens in rs._ja.LENS_READ and rs._ja.LENS_READ[lens] != 'auto':   # 🚀 / 🌊 / 🧲 / 🔥 every tab its OWN read (the curve read still wins on the curve)
        cmap_l = rs._cand_map()
        for r in live:
            tv_ = rs._read_for(r, cmap_l, lens)
            if tv_:
                r['tv'] = tv_
    if not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        for r in [x for x in live if not x.get('scanned')][:rs.PICK_SCAN_TOP]:
            m = r.get('baseAddress') or r.get('mint')
            if m:
                rs.asyncio.ensure_future(rs._runner_intel(m, rs._enr.PRIO['MOVER'], 'pick list'))
    cmap_f = rs._cand_map()   # the quick look's tiles: cap, logo, 5-min volume, trades an hour, curve % on EVERY tab's rows
    for r in live:
        m_ = r.get('baseAddress') or r.get('mint')
        rs._ja.fill_row(r, (rs._jup_facts.get(m_) or (0, None))[1], cmap_f.get(m_))
    rs._pc_rows(live)
    rs._fd_rows(live)
    # 🌊 LIVE TAPE + 🎯 CLEAN ENTRY on the rows a picker actually looks at: the last 90s read (⚡ burst · 🧲 absorb · 🏔 climax · 🩸 dump ·
    # ➖ calm) for the top PICK_TAPE_TOP, and the engine's own clean-entry verdict ("clean" or the reason) on every non-trench row
    # CACHE ONLY: the tape costs a getSignatures + up to 10 transactions per coin; reading 12 coins × 11 tracked lists every 2 min spent
    # every RPC lane in minutes (2026-10-09) and blinded the real card's own flow exit + rug radar. Picker rows show the tape the card /
    # the banger doors / the quick look already read (≤ 60s old); the RPC budget stays with the coins that hold money.
    for r in live[:rs.PICK_TAPE_TOP]:
        at_, w_ = rs._flow_now.get(r.get('pairAddress')) or (0, None)
        t_ = rs._flow.tape_read(w_) if w_ and rs.time.time() - at_ < 60 else None
        if t_:
            r['tape'] = t_
    if lens != 'trench':
        for r in live:
            r['entry'] = rs._prime.entry_gate({**r, 'liq': r.get('liq') or r.get('liquidityUsd'), 'chg1h': r.get('chg1h') if r.get('chg1h') is not None else r.get('change1h'),
                                            'chg5m': r.get('chg5m') if r.get('chg5m') is not None else r.get('change5m'),
                                            'organicPct': (r.get('vital') or {}).get('organicPct')}) or 'clean'
    res_ = {**out, 'pools': live, 'dead': len(rows) - len(live)}
    rs._disc_cache[key_] = (rs.time.time(), res_)
    return res_


@router.get('/api/reputation/why-pump-board')
async def why_pump_board():
    """❓ The page around the checker: what is moving right now (the live movers, else Pump trending) + the latest checks."""
    rs = _rs()
    mv = [{'mint': r.get('mint'), 'symbol': r.get('symbol'), 'img': r.get('img') or r.get('icon') or r.get('imageUrl'), 'chg': rs._fuse._f(r.get('chg1h')) or rs._fuse._f(r.get('chg5m')), 'cap': r.get('mcap') or r.get('cap')}
          for r in (rs._live_movers() or [])[:8]]
    if len(mv) < 6:
        seen = {x['mint'] for x in mv}
        for r in sorted([x for x in (rs._open_board() or []) if x.get('mint') not in seen and rs._fuse._f(x.get('chg1h')) > 0], key=lambda x: -rs._fuse._f(x.get('chg1h')))[:8 - len(mv)]:
            mv.append({'mint': r.get('mint'), 'symbol': r.get('symbol'), 'img': r.get('img') or r.get('imageUrl'), 'chg': rs._fuse._f(r.get('chg1h')), 'cap': r.get('mcap') or r.get('cap')})
    return {'moving': mv, 'recent': rs._why_recent[:12], 'free': rs.WHY_FREE_DAY, 'at': round(rs.time.time())}


@router.get('/api/reputation/fuses/holders')
async def fuse_holders():
    """Fuse holders board (Fuse chat side panel): every wallet with verified Fuse positions, live P&L, best first. 60s cache."""
    rs = _rs()
    hit = rs._fuse_holders_cache.get('all')
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1]
    pos = rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or []
    px = await rs._hq_prices([leg for x in pos for leg in x['legs']]) if pos else {}
    by = {}
    for x in pos:
        r = rs._hq.position_pnl(x, px)
        a = by.setdefault(x['wallet'], {'address': x['wallet'], 'handle': rs.handle_of(x['wallet']), 'fuses': 0, 'costUsd': 0.0, 'valueUsd': 0.0, 'lastAt': 0, 'names': []})
        a['fuses'] += 1; a['costUsd'] += r['costUsd']; a['valueUsd'] += r['valueUsd']; a['lastAt'] = max(a['lastAt'], x.get('at') or 0)
        if r.get('name') and r['name'] not in a['names']:
            a['names'].append(r['name'])
    rows = [{**a, 'names': a['names'][:3], 'costUsd': round(a['costUsd'], 2), 'pnlPct': round((a['valueUsd'] / a['costUsd'] - 1) * 100, 2) if a['costUsd'] else 0.0}
            for a in by.values()]
    out = {'holders': sorted(rows, key=lambda r: -r['pnlPct'])[:50], 'total': len(rows)}
    for r in out['holders']:
        r.pop('valueUsd', None)
    rs._fuse_holders_cache['all'] = (rs.time.time(), out)
    return out


@router.get('/api/reputation/fuses/season')
async def fuse_season():
    """This week's live Fuse season board (top 10) + the last 4 crowned weeks. 60s cache, warmed in the background."""
    rs = _rs()
    now = rs.time.time()
    if rs._fuse_season_cache['data'] and now - rs._fuse_season_cache['at'] < 60 and not rs._FUSE_FORCE.get():
        return rs._fuse_season_cache['data']
    start = rs._hq.season_start(now)
    rows, bots = await rs._season_rows(start, start + rs._hq.WEEK)
    board = [{**b, 'handle': rs.handle_of(b['wallet']) or f"{b['wallet'][:4]}…{b['wallet'][-4:]}"} for b in rs._hq.season_board(rows, start, start + rs._hq.WEEK, bots)[:10]]
    cat = await rs._feecat_raw()
    cat_pct = rs._hq.feecat_week_pct((cat or {}).get('exits'), (cat or {}).get('positions'), start, start + rs._hq.WEEK) if cat else None
    beat = set(rs._hq.beats_cat(board, cat_pct))
    board = [{**b, 'beatsCat': b['id'] in beat} for b in board]
    if rs._FUSE_FORCE.get():   # background only: the race ticker + top-3 alerts (viewers never trigger them)
        rs._season_race(start, board, now)
    season = {**rs.QUEST_SEASON_DEFAULT, **(rs._json_load(rs.QUESTS_PATH, {}).get('season') or {})}
    hq_ = rs._json_load(rs.FUSE_HQ_PATH, {})
    data = {'week': start, 'endsAt': start + rs._hq.WEEK, 'cards': len(rows), 'board': board, 'seasonName': season.get('name'), 'feecat': {'pct': cat_pct, 'winPts': rs._hq.CAT_WIN_PTS}, 'boostPct': rs._card_rules()['seasonBoostPct'], 'moves': list(rs._season_moves['list'])[-12:],
            'past': list(reversed((rs._json_load(rs.FUSE_HQ_PATH, {}).get('seasons') or [])[-4:])), 'at': now,
            'backers': {'board': [{**r, 'handle': rs.handle_of(r['wallet']) or f"{r['wallet'][:4]}…{r['wallet'][-4:]}"} for r in rs._hq.backer_board(
                hq_.get('backLog'), hq_.get('backWins'), start, start + rs._hq.WEEK, rs._protected_wallets())[:5]],
                        'poolUsd': rs._card_rules().get('backerPoolUsd', 0), 'split': list(rs._hq.BACKER_SPLIT), 'minBacks': rs._hq.BACKER_MIN_BACKS}}
    rs._fuse_season_cache.update(at=now, data=data)
    return data


@router.get('/api/reputation/fuses/ids')
async def fuse_ids(addrs: str = ''):
    """🪪 Trader chips (Arena, season board, chat): ⚛️ score + medals + battle W/L for up to 40 wallets, from the CACHE only so
    the chip never waits. Missing wallets warm in the background and show on the next poll."""
    rs = _rs()
    want = [x for x in dict.fromkeys(addrs.split(',')) if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', x)][:40]
    out, cold = {}, []
    for w in want:
        hit = rs._fuse_score_cache.get(rs.primary_of(w))
        if hit and rs.time.time() - hit[0] < 900:
            v = hit[1]; t = v.get('trader') or {}
            out[w] = {'score': v.get('score'), 'medals': t.get('medals'), 'battles': t.get('battles'), 'catWins': t.get('catWins'), 'held': t.get('held')}
        elif w not in rs._ids_warming:
            cold.append(w)
    if cold:
        rs._ids_warming.update(cold)

        async def warm():
            try:
                await rs.asyncio.gather(*[rs._fuse_score(w) for w in cold], return_exceptions=True)
            finally:
                rs._ids_warming.difference_update(cold)
        rs.asyncio.create_task(warm())
    return {'ids': out}


@router.get('/api/reputation/fuses/arena')
async def fuse_arena_public():
    """Fuse 🧬 › Arena for everyone: strategies' settled paper runs, the honest outlook, and the Runners proof — no admin data."""
    rs = _rs()
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    now = rs.time.time()
    vals = [rs._hq.arena_value(e, {}, now) for e in d.get('arena') or []]
    board = rs._hq.arena_board(vals)
    rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    cfg = rs._runner_cfg()
    rounds = []
    for r in rd['rounds'][-24:]:
        mults = [rs._rn.play_exits(p['lane'], p['entry'], [x for t, x in rd['paths'].get(p['mint'], []) if t > r['at']], cfg) for p in r['picks']]
        if mults:
            rounds.append({'at': r['at'], 'symbols': [p.get('symbol') for p in r['picks']], 'pct': round((sum(mults) / len(mults) - 1) * 100, 2)})
    mega = await rs._arena_mega(rd, cfg, now)
    bred = rs._bred_load(); hq_d = rs._json_load(rs.FUSE_HQ_PATH, {})
    board = [{**r, **({'bred': True, 'parent': bred[r['style']].get('parent'), 'against': bred[r['style']].get('against'), 'weights': bred[r['style']].get('weights')} if r['style'] in bred else {})} for r in board]
    return {'board': board, 'outlook': rs._hq.outlook(board), 'bestStyle': rs._hq.best_style(board), 'runs': [v for v in sorted(vals, key=lambda v: -v['at']) if v['settled']][:12],
            'bred': [{'style': k, **{x: v.get(x) for x in ('parent', 'against', 'weights', 'at')}, 'runs': next((r['runs'] for r in board if r['style'] == k), 0)} for k, v in bred.items()],
            'bredScrapped': [{x: r.get(x) for x in ('style', 'parent', 'runs', 'avgPct', 'medPct', 'scrappedAt')} for r in (hq_d.get('bredScrapped') or [])[-5:]][::-1],
            'runners': {'proof': rs._rn.proof(rd['rounds'], rd['paths'], now, cfg=cfg), 'rounds': rounds}, 'minSettled': rs._hq.MIN_SETTLED,
            'mega': [c for c in mega if not c.get('bench') and not c.get('fighterOnly')], 'bench': [c for c in mega if c.get('bench')], 'fighters': [c for c in mega if c.get('fighterOnly')] + rs._league_extra(mega),
            'battles': rs._battle_view(mega, now),
            # 🎚 auto paper cards per Risk dial: every round also played with each dial's TP/SL — proves a dial BEFORE it goes auto live
            'dials': {k: {**v, 'label': rs._hq.RISK_DIALS[k]['label'], 'why': rs._hq.RISK_DIALS[k]['why']} for k, v in rs._rn.dial_proof(rd['rounds'], rd['paths'], now, rs._hq.RISK_DIALS).items()},
            'engineDial': rd.get('cfgDial') or 'custom'}


@router.get('/api/reputation/fuses/paper')
async def fuse_paper(key: str = Query(..., max_length=120)):
    """📜 A card's Arena paper audit: its live battle book (entries at true fills → now, fees apart) + its finished books."""
    rs = _rs()
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    live = ((d.get('battles') or {}).get('paper') or {}).get(key)
    view = None
    if live:
        pairs_ = await rs._fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in live.get('legs') or []])
        view = rs._pgb.paper_view(live, {k: rs._fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}, {k: rs._fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_.items()})
    past = [x for x in reversed(d.get('paperLog') or []) if x.get('key') == key][:10]
    rec = {'won': sum(1 for x in past if x.get('result') == 'won'), 'lost': sum(1 for x in past if x.get('result') == 'lost'),
           'pnlUsd': round(sum(rs._fuse._f(x.get('pnlUsd')) for x in past), 4), 'feesUsd': round(sum(rs._fuse._f(x.get('feesUsd')) for x in past), 4)}
    return {'live': view, 'past': past, 'record': rec}


@router.get('/api/reputation/social-feed/thread/{pid:path}')
async def social_feed_thread(pid: str):
    """💬 One post's comments, read only when its thread is opened."""
    rs = _rs()
    return {'comments': [{k: c.get(k) for k in ('name', 'text', 'at', 'by')} for c in rs._fsoc.thread(rs._json_load(rs.FEED_SOCIAL_PATH, {}), pid)]}


@router.get('/api/reputation/social-feed')
async def social_feed(src: str = ''):
    """📰 FEEd's mixed timeline: FEELESS rooms + Pump callouts + public Telegram channels + Bluesky, newest first. `src` = comma list of the
    bubbles picked (empty = all). Each source is read at most once a minute and answered from its last copy while it refreshes."""
    rs = _rs()
    keys_ = [k for k, _ in rs._sfeed.SOURCES]
    want_ = {x for x in src.split(',') if x in keys_} or set(keys_)
    now_ = rs.time.time()
    for k_ in want_:
        c_ = rs._SF_CACHE.get(k_)
        if c_ is None:
            if k_ not in rs._SF_BUSY:
                rs._SF_BUSY.add(k_)
                try:
                    await rs.asyncio.wait_for(rs._sf_refresh(k_), 6)   # the first visitor waits for a source once (≤ 6s)
                except rs.asyncio.TimeoutError:
                    pass
        elif now_ - c_['at'] > rs._SF_TTL and k_ not in rs._SF_BUSY:
            rs._SF_BUSY.add(k_)
            rs.asyncio.create_task(rs._sf_refresh(k_))
    posts_ = rs._sfeed.mix([(rs._SF_CACHE.get(k_) or {}).get('posts') or [] for k_ in want_], want_)
    posts_ = await rs._sf_receipts(posts_, now_)
    return {'posts': posts_, 'sources': [{'key': k, 'label': l, 'n': len((rs._SF_CACHE.get(k) or {}).get('posts') or []), 'at': (rs._SF_CACHE.get(k) or {}).get('at')} for k, l in rs._sfeed.SOURCES],
            'post': ['x', 'reddit', 'bluesky', 'telegram', 'farcaster'], 'readNeedsApp': {'x': 'X API app (paid read access)', 'reddit': 'Reddit API app (registered)'}}


@router.get('/api/reputation/fuses/trench/open')
async def fuse_trench_open():
    """🚪 Open gates: every launch coin the feed sees, front-runners first, nothing filtered (each row says what it has not passed)
    + 📣 the callouts of the last hours with their result. Coin data only. A list to LOOK at; the engine never buys from it."""
    rs = _rs()
    got_ = rs._list_now(('open', ''), rs.LIST_CACHE_SEC, fuse_trench_open)
    if got_ is not None:
        return got_
    rows = rs._open_board() if rs._open_pairs else (rs._open_cache.get('rows') or [])
    await rs._jup_lite([r.get('mint') for r in rows])
    rows = rs._clean_rows([dict(r) for r in rows])
    cmap_ = rs._cand_map()
    for r in rows:   # 🚪 every coin gets a read (split view: reads column) + 🔔 its curve % when the runner board has it
        c_ = cmap_.get(r.get('mint')) or {}
        if c_.get('stage') == 'curve' and c_.get('curve') is not None:
            r['curvePct'] = round(rs._fuse._f(c_['curve']))
        if not r.get('tv'):
            x_ = {**{k: c_.get(k) for k in ('vol5m', 'chg6h', 'chg24h') if c_.get(k) is not None}, **{k: v for k, v in r.items() if v is not None}}
            r['tv'] = rs._ja.open_read((rs._jup_facts.get(r.get('mint')) or (0, None))[1], x_)
    rs._pc_rows(rows)
    rs._fd_rows(rows)
    doc = rs._json_load(rs.TRENCH_CALLOUT_PATH, {})
    now_px = {r['mint']: r['price'] for r in rows}
    proof = rs._trench.meta_proof(doc.get('state') or {}, keys=rs._trench.CALLOUTS)
    calling = {m: k for k, v in (rs._open_cache.get('calls') or {}).items() for m in v}
    res_ = {'rows': [{**r, 'call': calling.get(r['mint'])} for r in rows], 'seen': len(rs._open_pairs), 'everySec': rs._trench.CALLOUT_SEC, 'at': rs._open_cache.get('at') or None,
            'kinds': [{'key': k, 'icon': v[0], 'name': v[1], 'rule': v[2], 'proof': proof.get(k)} for k, v in rs._trench.CALLOUTS.items()],
            'earliness': rs._trench.earliness(doc.get('state') or {}),
            'feed': rs._trench.callout_feed(doc.get('state') or {}, doc.get('names') or {}, now_px, rs.time.time())}
    rs._disc_cache[('open', '')] = (rs.time.time(), res_)
    return res_


@router.get('/api/reputation/fuses/call-proof')
async def fuse_call_proof():
    """Each trench-vital call's own 1-hour record + whether the engine is taking 🔥 SEND IT coins yet."""
    rs = _rs()
    if not rs._call_cache.get('proof'):
        rs._call_cache['proof'] = rs._trench.meta_proof(rs._json_load(rs.CALL_PROOF_PATH, {}), keys=tuple(dict.fromkeys(rs.CALL_KEYS.values())))
    pro_rec = rs._trench.meta_proof(rs._json_load(rs.PROCALL_PROOF_PATH, {}), keys=('pro',)).get('pro')
    return {'proof': {**(rs._call_cache.get('proof') or {}), **({'pro': pro_rec} if pro_rec else {})}, 'auto': rs._sendit_ready(), 'autoMin': rs.CALL_AUTO_MIN, 'send': [r.get('symbol') for r in rs._call_cache.get('send') or []]}


@router.get('/api/reputation/fuses/trench')
async def fuse_trench(meta: str = Query('', max_length=20)):
    """🗑 The trench list + 🧼 the 10-point clean score and holder facts on every row (owner, 2026-10-08: $giftr, a rug, came from this list)."""
    rs = _rs()
    got_ = rs._list_now(('trench', meta), rs.LIST_CACHE_SEC, lambda: fuse_trench(meta))
    if got_ is not None:
        return got_
    out = await rs._fuse_trench_raw(meta)
    if isinstance(out, dict) and out.get('rows'):
        await rs._jup_lite([r.get('mint') or r.get('baseAddress') for r in out['rows']])
        rs._clean_rows(out['rows'])
        for r in out['rows']:   # 🗑 every row in the trench tab gets a degen read, whatever its age (curve / dip when it fits, else SEND IT)
            if 'tv' not in r:
                t_ = rs._ja.trench_verdict((rs._jup_facts.get(r.get('mint') or r.get('baseAddress')) or (0, None))[1], r)
                r['tv'] = {**t_, 'kind': 'trench', 'meters': [['🔥 HEAT', t_['heat']], ['☠ RUG', t_['rug']]]}
        for r in out['rows']:   # a trench-gate pass cleared every safety check
            if r.get('ok') and r.get('safe') is None:
                r['safe'] = True
        b_ = rs._brain_state()   # 🧠 the trench brain lives IN the trench tab: every row carries its learned play; once it has judged
        for r in out['rows']:  # enough coins the list is ordered by it (safety first: failed scans never move up)
            sc_ = rs._tb.score(r, b_['tbl'])
            if sc_:
                r['brain'] = {k: sc_[k] for k in ('est', 'hit', 'n')} | {'why': [list(w) for w in sc_['why'][:2]]}
        if int((b_['sum'] or {}).get('n') or 0) >= rs._tb.PROOF_MIN:
            out['rows'] = sorted(out['rows'], key=lambda r: (r.get('safe') is False, -rs._fuse._f((r.get('brain') or {}).get('est', -999))))
        out['brain'] = {**(b_['sum'] or {}), 'ready': rs._brain_ready()}
    rs._disc_cache[('trench', meta)] = (rs.time.time(), out)
    return out


@router.get('/api/reputation/familia-world')
async def familia_world(address: str = '', session: str = ''):
    """🗺 The whole Familia city: boroughs, bridges, every block, CPU towns, cartels, the season — and, signed in, my family's turf, raids,
    challenges, errands, rewards and the FEECAT redeem."""
    rs = _rs()
    import crews as _cr
    now = rs.time.time()
    me = rs._session_or_401(address, session) if address and session else None
    cartels_ = await rs.asyncio.to_thread(rs._cartels_now, now)
    await rs._ffuse_tick(now)
    async with rs._crews_lock:
        st = rs._json_load(rs.CREWS_PATH, {}); _cr._norm(st)
        w = st.setdefault('world', rs._fworld.blank())
        # ⚡ scale (P1): a read rewrote crews.json on EVERY GET — now only when the world moved. CPU stashes are left out of the check: they
        # refill by time (linear, capped), so recomputing them from the last saved point gives the same number.
        quiet_ = lambda: rs.json.dumps({k_: v_ for k_, v_ in w.items() if k_ != 'cpu'}, sort_keys=True, default=str)
        sig_ = quiet_()
        rs._world_tick(st, w, now)
        me = rs._seat_of(st, me) if me else None
        c = _cr.crew_of(st, me) if me else None
        v = rs._world_view(st, c, me, now, cartels_)
        if quiet_() != sig_ or not rs.CREWS_PATH.exists():
            rs._json_save(rs.CREWS_PATH, st)
    return v


@router.get('/api/reputation/familia-pools/chart/{pool}')
async def familia_pool_chart(pool: str):
    """📈 One pool's TVL + APY history (DefiLlama /chart, last 90 days, ≤ 90 points) + what $1,000 earned in the last 24h. Cached 30 min."""
    rs = _rs()
    if not rs._re.match(r'^[A-Za-z0-9-]{8,64}$', pool or ''):
        raise rs.HTTPException(400, 'Not a pool id.')
    now = rs.time.time(); hit = rs._fpl_charts.get(pool)
    row_ = next((r_ for r_ in ((await rs.familia_pools()) or {}).get('pools') or [] if r_.get('id') == pool), None)
    earn_ = rs._fpl.earn_24h(row_) if row_ else None
    if hit and now - hit[0] < 1800:
        return {'pool': pool, 'points': hit[1], 'earn': earn_}
    pts_ = []
    if row_ and row_.get('src') == 'llama':
        try:
            r_ = await rs._ai_http().get(f'https://yields.llama.fi/chart/{pool}', timeout=15)
            pts_ = rs._fpl.chart_points((r_.json() or {}).get('data') if r_.status_code == 200 else [])
        except Exception:
            pts_ = []
    rs._fpl_charts[pool] = (now, pts_)
    if len(rs._fpl_charts) > 300:
        for k_ in sorted(rs._fpl_charts, key=lambda k: rs._fpl_charts[k][0])[:len(rs._fpl_charts) - 300]:
            rs._fpl_charts.pop(k_, None)
    return {'pool': pool, 'points': pts_, 'earn': earn_}


@router.get('/api/reputation/familia-markets')
async def familia_markets():
    """🏦 Fee City's markets + today's top Solana coins, live (≤ 60s old)."""
    rs = _rs()
    now = rs.time.time(); c = rs._fmk_cache
    if c['v'] and now - c['at'] < 60:
        return c['v']
    if c['lock'] is None:
        c['lock'] = rs.asyncio.Lock()
    async with c['lock']:
        if c['v'] and now - c['at'] < 60:
            return c['v']
        tvl, pairs = await rs._fmk_fetch()
        v = rs._fmk.build(tvl, {k: x for k, x in c['prev'].items() if now - x[1] >= 3600 or not c['v']}, pairs, now)
        for k, t in tvl.items():   # 🕐 the "move" compares with a reading at least an hour old (the first reading of the day sets the base)
            if k not in c['prev'] or now - c['prev'][k][1] > 6 * 3600:
                c['prev'][k] = (t, now)
        c.update(at=now, v=v)
    return v


@router.get('/api/reputation/predict')
async def predict_state(address: str = ''):
    """⚡ Public: this hour's ballot with live moves since it opened, the last result, the week's top callers and (with `address`) your pick + record."""
    rs = _rs()
    import predict as _pr
    now = rs.time.time(); d = rs._json_load(rs.PREDICT_PATH, {'rounds': {}, 'players': {}}); rounds = d.get('rounds') or {}
    cur = rounds.get(str(_pr.round_id(now))) or next((r for r in sorted(rounds.values(), key=lambda r: -r['id']) if r.get('status') == 'open'), None)
    done = next((r for r in sorted(rounds.values(), key=lambda r: -r['id']) if r.get('status') == 'settled'), None)
    me = rs.primary_of(address) if address else ''
    live = {}
    if cur:
        hit = rs._predict_view_cache
        if hit['data'] and hit['data'][0] == cur['id'] and now - hit['at'] < 10:
            live = hit['data'][1]
        else:
            px = await rs._jup_prices([c['mint'] for c in cur['cands']]); live = _pr.moves(cur, px or {}); rs._predict_view_cache.update(at=now, data=(cur['id'], live))
    profs = rs._profiles_load()['profiles']
    nm = lambda a: (profs.get(rs.primary_of(a)) or {}).get('displayName') or (profs.get(rs.primary_of(a)) or {}).get('handle') or f'{a[:4]}…{a[-4:]}'
    out = {'now': now, 'round': None, 'last': None, 'me': (d.get('players') or {}).get(me) if me else None,
           'board': [{**r, 'name': nm(r['address'])} for r in _pr.board(d.get('players') or {}, now)], 'rule': f'Pick the coin that leads the next hour. +{_pr.BASE_PTS} season points for a right call, +{_pr.STREAK_PTS} more per win in a row (max +{_pr.STREAK_CAP}). Free — points only. Picks close {_pr.LOCK_SEC // 60} minutes before the bell.'}
    if cur:
        out['round'] = {'id': cur['id'], 'closesAt': cur['closesAt'], 'status': cur['status'], 'locked': now >= cur['closesAt'] - _pr.LOCK_SEC, 'mine': (cur['picks'] or {}).get(me) if me else None,
                        'players': len(cur['picks'] or {}), 'cands': [{**c, 'pct': live.get(c['mint'])} for c in cur['cands']]}
    if done:
        out['last'] = {'id': done['id'], 'winner': done.get('winner'), 'symbol': next((c['symbol'] for c in done['cands'] if c['mint'] == done.get('winner')), None),
                       'moves': done.get('moves'), 'mine': (done['picks'] or {}).get(me) if me else None, 'won': bool(me and (done['picks'] or {}).get(me) == done.get('winner'))}
    return out


@router.get('/api/reputation/bounty')
async def rug_bounty():
    """🪙 Public: the rug bounty board — recent catches (coins with the wallets FEELESS's forensics proved bundled / sniped, and who found them first) and the
    top finders this week and all time, with the season points they earned (bounty.py). Accepted reports only; anonymous ones never rank. 60s cache."""
    rs = _rs()
    import bounty as _bo
    now = rs.time.time()
    if rs._bounty_cache['data'] and now - rs._bounty_cache['at'] < 60:
        return rs._bounty_cache['data']
    b = _bo.board(rs._block_load()['wallets'], now)
    profs = rs._profiles_load()['profiles']
    name = lambda a: (profs.get(rs.primary_of(a)) or {}).get('displayName') or (profs.get(rs.primary_of(a)) or {}).get('handle') or f'{a[:4]}…{a[-4:]}'
    out = {**b, 'recent': [{**c, 'finders': [{'address': a, 'name': name(a)} for a in c['finders']]} for c in b['recent']],
           'week': [{**r, 'address': r['by'], 'name': name(r['by'])} for r in b['week']], 'all': [{**r, 'address': r['by'], 'name': name(r['by'])} for r in b['all']], 'at': now}
    rs._bounty_cache.update(at=now, data=out)
    return out


@router.get('/api/reputation/track-record/{address}')
async def wallet_track_record(address: str, limit: int = Query(40, ge=1, le=120)):
    """📜 Public: a wallet's track record — proof of what it really did — its verified FEELESS trades (closed pieces first-in-first-out + still-open lots priced live)
    and its chat calls with the result since, newest first. From FEELESS's own records only (track_record.py); price result, fees apart. 60s cache."""
    rs = _rs()
    import track_record as _rc
    primary = rs.primary_of(address); now = rs.time.time()
    hit = rs._track_cache.get(primary)
    if hit and now - hit[0] < 60:
        return hit[1]
    mine = set(rs.linked_of(primary)) | {primary, address}
    trades = rs._json_load(rs.FEELESS_TRADES_PATH, {})
    rows = [x for w in mine for x in (trades.get(w) or [])]
    calls = rs._calls_load().get('calls') or {}
    syms = {c.get('mint'): c.get('symbol') for c in calls.values() if c.get('mint') and c.get('symbol')}
    syms.update({r.get('mint'): r.get('symbol') for r in rs._runner_cands if r.get('mint') and r.get('symbol')})
    closed, open_ = _rc.trade_receipts(rows, syms)
    px = await rs._jup_prices([o['mint'] for o in open_]) if open_ else {}
    for o in open_:
        p = rs._fuse._f((px or {}).get(o['mint']))
        o['exitPx'] = p or None; o['ret'] = round(p / o['entryPx'] - 1, 4) if p > 0 and o['entryPx'] > 0 else None
        o['usd'] = round(o['tokens'] * (p - o['entryPx']), 4) if p > 0 else None
    cs = _rc.call_receipts(calls, primary, aliases=mine)
    feed = sorted(closed + open_ + cs, key=lambda r: -r['at'])[:limit]
    out = {'address': primary, 'record': feed, 'summary': _rc.summary(closed, cs), 'at': now}
    rs._track_cache[primary] = (now, out)
    return out


@router.get('/api/reputation/fuses/pay-map')
async def fuses_pay_map():
    """📊 Public: what pays on the real card — closed pieces by hold time, opener (hand pick vs engine), exit kind and hour, with plain-words
    advice that cites the numbers (pay_map.py). Confirmed fills only, price result, fees apart. 60s cache. A record, never a promise."""
    rs = _rs()
    import pay_map as _pm
    now = rs.time.time()
    if rs._paymap_cache['data'] and now - rs._paymap_cache['at'] < 60:
        return rs._paymap_cache['data']
    ledger = list(reversed(rs._fw_full_ledger()))   # every row, newest first, from the in-memory copy of the append-only table (no 100K-row re-parse)
    cards = sorted({r.get('card') for r in ledger if r.get('card') and r.get('card') != 'wallet'})
    out = {'cards': {c: _pm.pay_map(ledger, c, now) for c in cards}, 'at': now}
    rs._paymap_cache.update(at=now, data=out)
    return out


@router.get('/api/reputation/fuses/record/{tpl}')
async def fuse_card_record(tpl: str):
    """📜 A tier card's permanent public record: every run it ever finished (start → end, %), best / worst / win rate."""
    rs = _rs()
    if tpl not in rs._prime.TEMPLATES:
        raise rs.HTTPException(404, 'Unknown card.')
    rows = rs._store.Ledger(rs.CARD_RECORDS_PATH, table='runs').rows(limit=500, card=tpl)
    pcts = [rs._fuse._f(r.get('pct')) for r in rows]
    return {'card': tpl, 'runs': rows, 'n': len(rows), 'won': sum(1 for p in pcts if p > 0), 'bestPct': max(pcts) if pcts else None,
            'worstPct': min(pcts) if pcts else None, 'avgPct': round(sum(pcts) / len(pcts), 2) if pcts else None}


@router.get('/api/reputation/internal/sicario-wallet')
async def internal_sicario_wallet(request: Request):
    """🎩 The Fuse wallet Sicario's trades from, read only: its address and what the card's own books say. Never a key."""
    rs = _rs()
    import hmac
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), rs._internal_key()):
        raise rs.HTTPException(403, 'Internal endpoint.')
    cards = ((rs._json_load(rs.FUSE_HQ_PATH, {}) or {}).get('prime') or {}).get('cards') or {}; tid = next((k for k, c in cards.items() if (c or {}).get('real')), None)
    if not tid:
        return {'address': None}
    v = rs._fw_public(tid); r = v.get('reconciliation') or {}
    return {'address': v.get('wallet'), 'cardSol': r.get('cardCashSol'), 'walletSol': r.get('walletSol'), 'reserveSol': r.get('gasReserveSol'), 'outsideSol': r.get('outsideCardSol')}


@router.get('/api/reputation/internal/sicario-want')
async def internal_sicario_fate(request: Request, mint: str = ''):
    """🎩 What the card did with that coin, in its own words."""
    rs = _rs()
    import hmac
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), rs._internal_key()):
        raise rs.HTTPException(403, 'Internal endpoint.')
    f_ = rs._g4.get('fate') or {}; card = rs._real_card({}) or {}; pol = rs._oe.policy(rs._prime.clean_cfg(((rs._json_load(rs.FUSE_HQ_PATH, {}) or {}).get('prime') or {}).get('realCfg') or {}))
    return {'fate': f_.get('why') if f_.get('mint') == mint else None, 'seats': rs._seat.card_seats(card.get('legs'), pol['seats']) if pol.get('aiSeat') == 'real' else None}


@router.get('/api/reputation/runners/discover')
async def runners_discover():
    """Fuse 🧬 › Runners: one gated list of good runners, tagged by every source that independently likes them —
    arena round, lit cards, pump scan, snipers-out radar, creators' picks (proven callers + published Fuses). 20s cache."""
    rs = _rs()
    now = rs.time.time()
    if rs._runner_disc_cache['data'] and now - rs._runner_disc_cache['at'] < 40 and not rs._FUSE_FORCE.get():
        return rs._runner_disc_cache['data']
    live, board = await rs.asyncio.gather(rs._runner_live(), rs.caller_board(days=30))
    d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    cfg = rs._runner_cfg()
    tags: dict = {}
    tag = lambda m, k, v: m and tags.setdefault(m, {}).setdefault(k, v)
    rnd = d['rounds'][-1] if d['rounds'] else None
    for p in (rnd or {}).get('picks') or []:
        tag(p['mint'], 'arena', f"{p.get('lane', 'runner')} lane · round {str((rnd or {}).get('id', ''))[:4]}")
    for c in d.get('litCards') or []:
        if now - c['at'] <= 72 * 3600:
            res = rs._rn.card_result(c, d['paths'], now, cfg)
            for p in c['picks']:
                tag(p['mint'], 'lit', f"lit card {res:+.1f}% since lit")
    for r in live['passing']:   # every coin passing every gate is a pump-scan find (never a dead tab while anything passes)
        tag(r['mint'], 'pump', f"passes every gate · score {round(rs._fuse._f(r.get('score')))}")
        if r.get('bondTier') == 'watch':
            tag(r['mint'], 'watch', f"{rs._fuse._f(r.get('curve')):.0f}% up the curve, rep-confirmed — {r.get('smartBuyers')} smart buyers")
        if rs._rn.near_bond(r, cfg):
            tag(r['mint'], 'bond', f"{rs._fuse._f(r.get('curve')):.0f}% up the curve, {r.get('buyShare')}% buys — about to bond")
    for e in rs._radar['events']:
        if e.get('kind') == 'snipers-out' and now - (e.get('at') or 0) < 6 * 3600:
            tag(e.get('mint'), 'snipers', 'every flagged sniper sold')
    sharp = {r.get('callerAddress'): r for r in board['rows'] if r.get('calls', 0) >= 3 and r.get('hitRate', 0) >= 0.5}
    for c in (rs._json_load(rs.CALLS_PATH, {}).get('calls') or {}).values():
        if c.get('callerAddress') in sharp and now - (c.get('at') or 0) < 48 * 3600:
            tag(c.get('mint'), 'creator', f"called by {c.get('caller') or 'a sharp caller'} ({round(sharp[c['callerAddress']]['hitRate'] * 100)}% hit)")
    for f in (rs._json_load(rs.FUSES_PATH, {'fuses': {}}).get('fuses') or {}).values():
        if f.get('enabled', True):
            for leg in f.get('legs') or []:
                if leg.get('role') == 'runner':
                    tag(leg.get('baseAddress') or leg.get('mint'), 'creator', f"in the {f.get('name')} Fuse")
    for c in rs._arena_mega_cache.get('data') or []:   # 🏟 runner coins on the cards fighting in the Arena right now (stage, tiers, picks)
        for leg in c.get('legs') or []:
            if leg.get('runner') or c.get('kind') in ('lit', 'round'):
                tag(leg.get('baseAddress') or leg.get('mint'), 'arena', f"on {c.get('emoji') or ''} {c.get('name') or 'an Arena card'}".strip())
    passing_mints = {r['mint'] for r in live['passing']}
    for f in (rs._json_load(rs.FUSES_PATH, {'fuses': {}}).get('fuses') or {}).values():   # 📣 any passing coin inside a published HQ Fuse
        for leg in f.get('legs') or []:
            m_ = leg.get('baseAddress') or leg.get('mint')
            if f.get('enabled', True) and m_ in passing_mints:
                tag(m_, 'creator', f"in the {f.get('name')} Fuse")
    grads = rs._rn.fresh_grads(live['dropped'])
    for r in grads:
        tag(r['mint'], 'grad', f"graduated, passes every other gate · score {round(rs._fuse._f(r.get('score')))}")
    rows = [{**r, 'passedAt': now} for r in rs._rn.discover(live['passing'] + grads, tags, limit=80)]
    rows = rs._rn.sticky((rs._runner_disc_cache.get('data') or {}).get('runners'), rows, live['dropped'], now)   # 🧲 never a flickering list
    data = {'runners': rows, 'counts': {k: sum(1 for r in rows if any(s['kind'] == k for s in r['sources'])) for k in rs._rn.SOURCES},
            'sources': rs._rn.SOURCES, 'nextRoundAt': (rnd['at'] + rs._rn.ROUND_SECONDS) if rnd else now, 'gates': [g[1] for g in rs._rn.gates(cfg)],
            'swaps': ((rnd or {}).get('swaps') or [])[-5:], 'at': now, 'seen': live['seen'],
            # This round's picks with their live state (still passing = addable; failing shows why).
            'round': [{**{k: p.get(k) for k in ('mint', 'symbol', 'logo', 'lane', 'pairAddress', 'score', 'entry')}, 'passing': p['mint'] in {x['mint'] for x in live['passing']},
                       'move': rs._round_move(p, live),
                       'gates': next((x.get('gates') for x in live['dropped'] if x['mint'] == p['mint']), None) or ([] if p['mint'] in {x['mint'] for x in live['passing']} else ['left the live feed'])}
                      for p in (rnd or {}).get('picks') or []],
            # ⚠️ NEW runners: minutes-old coins through the tight launch filter (site + X, clean creator first) — riskier lane
            'newRunners': [{k: x.get(k) for k in ('mint', 'symbol', 'logo', 'pairAddress', 'mcap', 'vol1h', 'chg1h', 'buyShare', 'ageH', 'score', 'creatorRep', 'why', 'price')}
                           for x in rs._rn.new_runners(live['passing'] + [x for x in live['dropped'] if (x.get('gates') or [''])[0].startswith(('mcap', 'vol'))])],
            # Watch-only: the busiest coins that FAILED a gate, with the reason — shown so the tab is never dead, never addable.
            'watching': [{k: x.get(k) for k in ('mint', 'symbol', 'logo', 'mcap', 'vol1h', 'chg1h', 'buyShare', 'gates')}
                         for x in sorted(live['dropped'], key=lambda x: -rs._fuse._f(x.get('vol1h')))[:12]]}
    rs._runner_disc_cache.update(at=now, data=data)
    return data


@router.get('/api/reputation/runners')
async def runners_board():
    """FUSE RUNNERS: live board (every arriving coin gated + scored), the current round by lane, recent rounds' paper
    results and the proof that decides whether the Fuse button lights up."""
    rs = _rs()
    live, sol_usd = await rs.asyncio.gather(rs._runner_live(), rs._sol_usd_live())
    d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    now = rs.time.time()
    rnd = d['rounds'][-1] if d['rounds'] else None
    cfg = rs._runner_cfg(); ex = rs._rn.exits(cfg)
    hist = []
    for r in reversed(d['rounds'][-8:-1] if len(d['rounds']) > 1 else []):
        mults = [rs._rn.play_exits(p['lane'], p['entry'], [x for t, x in d['paths'].get(p['mint'], []) if t > r['at']], cfg) for p in r['picks']]
        hist.append({'id': r['id'], 'at': r['at'], 'symbols': [p.get('symbol') for p in r['picks']], 'pct': round((sum(mults) / len(mults) - 1) * 100, 2) if mults else 0.0})
    cur = {p['mint']: p for p in live['passing']}
    picks = [{**p, 'now': cur.get(p['mint'], {}).get('price') or p['price'], 'exits': ex[p['lane']]['label']} for p in (rnd or {}).get('picks', [])]
    return {'live': live['passing'][:60], 'dropped': live['dropped'][:30], 'seen': live['seen'], 'widen': live.get('widen'), 'round': rnd and {**rnd, 'picks': picks},
            'nextRoundAt': (rnd['at'] + rs._rn.ROUND_SECONDS) if rnd else now, 'history': hist, 'proof': rs._rn.proof(d['rounds'], d['paths'], now, cfg=cfg),
            'exits': {k: v['label'] for k, v in ex.items()}, 'gates': [g[1] for g in rs._rn.gates(cfg)], 'lightMinRounds': cfg['lightRounds'], 'solUsd': sol_usd,
            'litCards': [{**c, 'pct': rs._rn.card_result(c, d['paths'], now, cfg)} for c in reversed((d.get('litCards') or [])[-12:])],
            'lanes': (lp := rs._rn.lane_proofs(d['rounds'], d['paths'], now, cfg)), 'laneWeights': rs._rn.lane_weights(lp)}


@router.get('/api/reputation/quests-leaderboard')
async def quest_leaderboard():
    """Season XP leaderboard (10 min cache). Paused season: no ranking, just the plan."""
    rs = _rs()
    season = rs._quest_season()
    if season.get('paused') or not season.get('start'):
        return {'season': season, 'rows': [], 'paused': True}
    if rs._quest_board_cache.get('at', 0) > rs.time.time() - 600:
        return rs._quest_board_cache['data']
    wallets = set(rs._json_load(rs.FEELESS_TRADES_PATH, {})) | set(rs._pts()) | set(rs._qs().all())
    rows = []
    for w in list(wallets)[:2000]:
        try:
            s = await rs._quest_summary(rs.primary_of(w))
        except Exception:
            continue
        if s['season']['score'] > 0:
            prof = (rs._profiles_load()['profiles'].get(s['address']) or {})
            rows.append({'address': s['address'], 'name': prof.get('displayName') or prof.get('handle') or s['address'][:4] + '…' + s['address'][-4:],
                         'xp': s['season']['score'], 'level': s['level']['name'], 'badges': s['earned']})
    rows.sort(key=lambda r: -r['xp'])
    data = {'season': season, 'rows': rows[:50], 'paused': False}
    rs._quest_board_cache.update(at=rs.time.time(), data=data)
    return data


@router.get('/api/reputation/c/{tok}')
async def war_canary(tok: str, request: Request):
    """A planted canary token was opened → log the opener's real IP/UA. Always returns a 1×1 gif; it runs nothing anywhere."""
    rs = _rs()
    try:
        ip = rs._guard.client_ip(request.headers, request.client.host if request.client else '', rs.os.environ.get('FEELESS_TRUST_PROXY') == '1')
        if rs._re.fullmatch(r'[0-9a-f]{32}', tok or '') and rs._war.canary_open(rs._war_s(), tok, ip, request.headers.get('user-agent', ''), dict(request.headers)):
            rs._war_save(force=True)
    except Exception:
        pass
    gif = bytes.fromhex('47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b')
    return rs.Response(content=gif, media_type='image/gif')


@router.get('/api/reputation/security/bounty')
async def war_bounty_scope():
    """The public bounty scope + rules (opt-in; turns probing into paid, responsible disclosure)."""
    rs = _rs()
    return rs._BOUNTY_SCOPE


@router.get('/api/reputation/legal/status')
async def legal_status(request: Request, wallet: Optional[str] = None):
    """Public: the terms version, the country a CDN saw (none on the bare Mac), whether this wallet accepted THIS version, and every
    feature's gate. The stated country only comes back (and only counts) with the wallet's own session (x-feeless-session header)."""
    rs = _rs()
    s = rs._legal_s(); c = rs._legal.country_of(request.headers)
    me = rs.primary_of(wallet) if wallet and 20 <= len(wallet) <= 64 else None
    mine = False
    sess = request.headers.get('x-feeless-session') or ''
    if me and sess:
        try:
            mine = rs._session_or_401(me, sess) == me
        except rs.HTTPException:
            mine = False
    st = rs._legal.status(s, me) if me else {'accepted': False, 'row': None}
    row = (st['row'] or {}) if st['accepted'] else {}
    used = row if mine else ({'adult': True} if st['accepted'] else None)
    return {'version': rs._legal.VERSION, 'accepted': st['accepted'], 'country': c, 'stated': row.get('country') if mine else None,
            'minAge': s['cfg'].get('minAge'), 'features': rs._legal.FEATURES, 'sanctioned': s['cfg'].get('everywhere'),
            'gates': {f: rs._legal.gate(s['cfg'], f, c, used) for f in rs._legal.FEATURES}}


@router.get('/api/reputation/receipts/{wallet}')
async def list_receipts(wallet: str, limit: int = 200):
    rs = _rs()
    rows = [r for r in rs._receipt_rows() if r[2] == wallet]
    rows.sort(key=lambda r: -(r[0] or 0))
    keys = ['t', 'sig', 'wallet', 'kind', 'tokens', 'sol', 'slot', 'fee']
    return {'wallet': wallet, 'count': len(rows), 'receipts': [dict(zip(keys, r)) for r in rows[:max(1, min(limit, 1000))]]}


@router.get('/api/reputation/wallet-stats/{address}')
async def wallet_stats(address: str):
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        return {'address': address, 'chain': 'evm' if address.startswith('0x') else None, 'supported': False}
    hit = rs._wstats_cache.get(address)
    if hit and rs.time.time() - hit[0] < 300:
        return hit[1]
    out = {'address': address, 'chain': 'solana', 'supported': True}
    async with rs.httpx.AsyncClient(timeout=25) as http:
        try:
            out['sol'] = ((await rs._rpc(http, 'getBalance', [address])) or {}).get('value', 0) / 1e9
        except Exception:
            out['sol'] = None
        try:
            toks = []
            for prog in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
                r = await rs._rpc(http, 'getTokenAccountsByOwner', [address, {'programId': prog}, {'encoding': 'jsonParsed'}])
                toks += (r or {}).get('value', [])
            held = [t for t in toks if float(((t['account']['data']['parsed']['info'].get('tokenAmount') or {}).get('uiAmount')) or 0) > 0]
            out['tokensHeld'] = len(held)
        except Exception:
            out['tokensHeld'] = None
        before, oldest, count = None, None, 0
        for _ in range(5):
            opts = {'limit': 1000}
            if before:
                opts['before'] = before
            try:
                sigs = await rs._rpc(http, 'getSignaturesForAddress', [address, opts])
            except Exception:
                break
            if not sigs:
                break
            count += len(sigs)
            oldest = sigs[-1].get('blockTime') or oldest
            before = sigs[-1]['signature']
            if len(sigs) < 1000:
                break
        out['txCount'] = count
        out['txCountCapped'] = count >= 5000
        out['firstSeen'] = oldest if not out['txCountCapped'] else None
    rs._wstats_cache[address] = (rs.time.time(), out)
    return out


@router.get('/api/reputation/activity/{address}')
async def activity(address: str, limit: int = 30):
    rs = _rs()
    me = set(rs.linked_of(address))
    rows = []
    for room, msgs in rs._chat_load()['rooms'].items():
        for m in msgs:
            if m.get('address') in me or (m.get('profile') or {}).get('address') in me:
                rows.append({'room': room, 'id': m['id'], 'text': m['text'][:200], 'ts': m['ts'], 'tokens': [t.get('symbol') for t in m.get('tokens') or []]})
    rows.sort(key=lambda r: -r['ts'])
    return {'address': address, 'posts': rows[:max(1, min(limit, 100))], 'handle': rs.handle_of(rs.primary_of(address))}


@router.get('/api/reputation/search')
async def search_profiles(q: str, limit: int = 6):
    """Profile search for the header search bar: @handle / display-name prefix matches."""
    rs = _rs()
    ql = q.strip().lstrip('@').lower()
    if len(ql) < 2:
        return {'profiles': []}
    rows = []
    for a, v in rs._profiles_load()['profiles'].items():
        v = v or {}
        h, n = (v.get('handle') or ''), str(v.get('displayName') or '').lower()
        score = 3 if h == ql else 2 if h.startswith(ql) else 1 if n.startswith(ql) or ql in h else 0
        if score:
            rows.append((score, {'address': a, 'handle': h or a[:6].lower(), 'displayName': v.get('displayName'), 'avatarUrl': v.get('avatarUrl')}))
    rows.sort(key=lambda r: -r[0])
    return {'profiles': [r[1] for r in rows[:max(1, min(limit, 20))]]}


@router.get('/api/reputation/league')
async def caller_league(week: int = 0):
    rs = _rs()
    start = rs._week_start() - week * 7 * 86400
    end = start + 7 * 86400
    board = await rs.caller_board(days=min(90, max(7, int((rs.time.time() - start) / 86400) + 1)))
    rows = []
    for r in board['rows']:
        rows.append({'caller': r.get('caller'), 'address': r.get('callerAddress'), 'calls': r.get('calls'), 'hitRate': r.get('hitRate'), 'avgPeakX': r.get('avgPeakX'),
                     'points': round((r.get('calls') or 0) * 2 + (r.get('hitRate') or 0) * 50 + min(20, (r.get('avgPeakX') or 1) * 4), 1)})
    rows = [r for r in rows if r['address'] and r['address'] != 'FEE-LEADER-CAT']
    rows.sort(key=lambda r: -r['points'])
    return {'weekStart': start, 'weekEnd': end, 'rows': rows[:50], 'prizes': ['🥇 League Champion badge + airdrop', '🥈 badge', '🥉 badge']}


@router.get('/api/reputation/dm-inbox')
async def dm_inbox(address: str, session: str):
    rs = _rs()
    me = rs._session_or_401(address, session)
    rows = []
    for k, msgs in rs._json_load(rs.DM_PATH, {}).items():
        a, b = k.split('|')
        if me in (a, b) and msgs:
            peer = b if a == me else a
            pending = rs._dm_pref(me)['policy'] == 'requests' and peer not in rs._dm_pref(me)['accepted'] and not any(m['from'] == me for m in msgs)
            rows.append({'peer': peer, 'handle': rs.handle_of(peer), 'last': msgs[-1], 'count': len(msgs), 'request': pending})
    rows.sort(key=lambda r: -r['last']['at'])
    return {'threads': rows[:50]}


@router.get('/api/reputation/rewards/{address}')
async def rewards(address: str):
    rs = _rs()
    me = rs.primary_of(address)
    rec, items, _ = await rs._reward_state(me)
    allp = rs._pts()
    rank = 1 + sum(1 for v in allp.values() if v.get('total', 0) > rec.get('total', 0))
    return {'address': me, 'total': rec.get('total', 0), 'streak': rec.get('streak', 0), 'rank': rank, 'items': items, 'log': rec.get('log', [])[:20]}


@router.get('/api/reputation/rewards-board')
async def rewards_board(limit: int = 50):
    rs = _rs()
    rows = sorted(({'address': a, 'handle': rs.handle_of(a), 'points': v.get('total', 0), 'streak': v.get('streak', 0)} for a, v in rs._pts().items()), key=lambda r: -r['points'])
    return {'rows': rows[:max(1, min(limit, 200))]}


@router.get('/api/reputation/pnl/{address}')
async def wallet_pnl(address: str):
    rs = _rs()
    me = set(rs.linked_of(address))
    rows = [r for r in rs._receipt_rows() if r[2] in me]
    by = {}
    sol_flow = 0.0
    for r in rows:
        sol_flow += r[5] or 0
        for mint, delta in r[4]:
            if mint == rs.WSOL:
                continue
            b = by.setdefault(mint, {'mint': mint, 'bought': 0.0, 'sold': 0.0, 'solIn': 0.0, 'solOut': 0.0, 'trades': 0})
            b['trades'] += 1
            if delta > 0:
                b['bought'] += delta; b['solIn'] += -(r[5] or 0)
            else:
                b['sold'] += -delta; b['solOut'] += (r[5] or 0)
    for b in by.values():
        b['realizedSol'] = round(b['solOut'] - b['solIn'] * (b['sold'] / b['bought'] if b['bought'] else 1), 6)
        b['holding'] = round(b['bought'] - b['sold'], 6)
    return {'trades': len(rows), 'netSolFlow': round(sol_flow, 6), 'tokens': sorted(by.values(), key=lambda b: -abs(b['realizedSol']))[:50],
            'note': 'From verified FEELESS trade receipts. Trades made outside FEELESS are not included.'}


@router.get('/api/reputation/familia/my-money')
async def familia_my_money(address: str = Query('', max_length=64), session: str = Query('', max_length=400)):
    """💵 YOUR MONEY tower (my_money.py): every position FEELESS can prove for this wallet, priced live — coins from its verified FEELESS trades
    (value + the coin's 24 h move, never a fee-tainted P&L) and, signed in, its family block's real market positions. One read per wallet / 45 s."""
    rs = _rs()
    import my_money as _mym
    if not address:
        return _mym.assemble([], {}, [])
    key_ = rs.primary_of(address) + ('|s' if session else '')
    hit_ = rs._mm_cache.get(key_)
    if hit_ and rs.time.time() - hit_[0] < 45:
        return hit_[1]
    held_ = [t_ for t_ in (await rs.wallet_pnl(address)).get('tokens') or [] if (t_.get('holding') or 0) > 0][:30]
    pairs_ = []
    if held_:
        try:
            r_ = await rs._ai_http().get('https://api.dexscreener.com/tokens/v1/solana/' + ','.join(t_['mint'] for t_ in held_), timeout=8)
            pairs_ = r_.json() if r_.status_code == 200 and isinstance(r_.json(), list) else []
        except Exception:
            pairs_ = []
    blds_ = []
    if session:
        try:
            blds_ = (await rs.familia_block(address, session)).get('buildings') or []
        except Exception:
            blds_ = []
    v_ = _mym.assemble(held_, _mym.best_prices(pairs_), blds_)
    rs._mm_cache[key_] = (rs.time.time(), v_)
    if len(rs._mm_cache) > 500:
        for k_ in sorted(rs._mm_cache, key=lambda k: rs._mm_cache[k][0])[:100]:
            rs._mm_cache.pop(k_, None)
    return v_


@router.get('/api/reputation/trust-batch')
async def trust_batch(addresses: str = Query('', max_length=2400)):
    """Rep marks for names on screen (chat, lists). Answers from cache instantly and scores missing
    wallets in the background, a few at a time, so a busy chat never stalls on RPC calls."""
    rs = _rs()
    out = {}
    for raw in [x for x in addresses.split(',') if x][:50]:
        a = rs.primary_of(raw.strip())
        hit = rs._trust_cache.get(a)
        if hit:
            r = hit[1]; out[raw] = {'score': r.get('score'), 'level': r.get('level'), 'blocked': any('Blocklisted' in p['label'] for p in r.get('parts', [])), 'gold': rs._gold_creator(a)}
        case = rs._quick_rep(a) if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a) else None
        if case and case.get('level') in ('watch', 'suspect', 'high'):  # the case-file verdict rides along everywhere a name shows
            out.setdefault(raw, {'score': None, 'level': None})['case'] = case
        if (not hit or rs.time.time() - hit[0] > 600) and a not in rs._trust_pending and len(rs._trust_pending) < 8:
            rs._trust_pending.add(a); rs.asyncio.create_task(rs._trust_fill(a))
    return {'trust': out}


@router.get('/api/reputation/trust/{address}')
async def trust_score(address: str):
    rs = _rs()
    a = rs.primary_of(address)
    parts, score, evidence = [], 50, 0
    st = await rs.wallet_stats(a) if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a) else {}
    age_d = (rs.time.time() - st['firstSeen']) / 86400 if st.get('firstSeen') else (365 if st.get('txCountCapped') else None)
    if age_d is not None:
        evidence += 1
        pts = 10 if age_d >= 180 else 6 if age_d >= 30 else 0 if age_d >= 7 else -8
        score += pts; parts.append({'label': f'Wallet age {int(age_d)}d', 'points': pts})
    bl = rs._block_load()['wallets'].get(a)
    if bl and rs._is_blocked(bl):
        score -= 45; evidence += 1; parts.append({'label': f"Blocklisted — caught on {len(bl.get('mints') or {})} launch(es)", 'points': -45})
    elif bl:
        score -= 15; evidence += 1; parts.append({'label': 'Seen sniping/bundling (not yet blocklisted)', 'points': -15})
    creator = rs._load()['creators'].get(rs._creator_key('solana', a))
    if creator:
        sc = rs.score_creator(creator); sc = {**sc, **rs._hygiene(a, sc)}
        if sc.get('score') is not None:
            evidence += 1
            pts = round((sc['score'] - 50) * 0.6)
            score += pts; parts.append({'label': f"Creator record: {sc['badge']} ({sc['score']})", 'points': pts})
    board = await rs.caller_board(days=90)
    me = next((r for r in board['rows'] if r.get('callerAddress') == a), None)
    if me and me['calls'] >= 3:
        evidence += 1
        pts = round((me['hitRate'] - 0.3) * 30)
        score += pts; parts.append({'label': f"Calls: {me['calls']}, {round(me['hitRate'] * 100)}% hit 2×", 'points': pts})
    fol = len([x for x, lst in rs._fol()['following'].items() if a in lst])
    if fol:
        pts = min(8, fol); score += pts; parts.append({'label': f'{fol} followers', 'points': pts})
    try:
        sh = rs.shield_record(a)
        if sh['broken']:
            score -= 35 * sh['broken']; evidence += 1; parts.append({'label': f"Broke {sh['broken']} FEELESS Shield promise(s)", 'points': -35 * sh['broken']})
        if sh['kept']:
            score += 8 * sh['kept']; evidence += 1; parts.append({'label': f"Kept {sh['kept']} FEELESS Shield(s) to the end", 'points': 8 * sh['kept']})
    except Exception:
        pass
    sh = await rs._shield_of(a)
    if rs._shield.rep_penalty(sh):
        score += rs._shield.rep_penalty(sh); evidence += 1; parts.append({'label': f"Bot shield: {sh['verdict']} — {sh['why']}", 'points': rs._shield.rep_penalty(sh)})
    fz = rs._fuse_rep(a)
    if fz:
        score += fz['points']; evidence += 1; parts.append(fz)
    fsc = (rs._fuse_score_cache.get(a) or (0, None))[1]   # cached only: trust never waits on (or loops through) the Fuse score
    if fsc and rs._hq.trust_from_fuse(fsc['perf'], fsc['cards']):
        pts = rs._hq.trust_from_fuse(fsc['perf'], fsc['cards'])
        score += pts; evidence += 1; parts.append({'label': f"Fuse score {fsc['score']} — verified card P&L, medals, copies, streaks", 'points': pts})
    if rs.is_verified(a):
        score += 10; evidence += 1; parts.append({'label': 'Verified by FEELESS', 'points': 10})
    if rs.is_muted(a):
        score -= 10; parts.append({'label': 'Currently muted by moderators', 'points': -10})
    score = max(0, min(100, score))
    if evidence == 0:
        return {'address': a, 'score': None, 'level': 'unknown', 'parts': parts, 'note': 'Not enough on-chain or FEELESS history to score this wallet yet.'}
    level = 'high' if score >= 75 else 'good' if score >= 60 else 'caution' if score >= 40 else 'risky'
    return {'address': a, 'score': score, 'level': level, 'parts': parts, 'evidence': evidence}


@router.get('/api/reputation/standing/{address}')
async def wallet_standing(address: str):
    """One wallet across every category FEELESS scores, each with the evidence behind it and a
    percentile against every wallet FEELESS has scored in that category."""
    rs = _rs()
    a = rs.primary_of(address)
    trust = await rs.trust_score(a)
    cats = [{'id': 'trust', 'label': 'Overall trust', 'score': trust.get('score'), 'detail': f"{len(trust.get('parts') or [])} signals", 'good': (trust.get('score') or 0) >= 60}]
    store = rs._load()
    creator = store['creators'].get(rs._creator_key('solana', a))
    all_creator_scores = [x.get('score') for x in (rs.score_creator(c) for c in store['creators'].values()) if x.get('score') is not None]
    if creator:
        sc = rs.score_creator(creator)
        pct = round(sum(1 for v in all_creator_scores if v <= (sc.get('score') or 0)) / max(1, len(all_creator_scores)) * 100) if sc.get('score') is not None else None
        cats.append({'id': 'creator', 'label': 'Creator record', 'score': sc.get('score'), 'percentile': pct,
                     'detail': f"{sc.get('badge')} · {sc.get('tokenCount', 0)} launches · {sc.get('dumpedCount', 0)} dumped", 'good': sc.get('badge') in ('trusted', 'veteran')})
    board = await rs.caller_board(days=90)
    me = next((r for r in board['rows'] if r.get('callerAddress') == a), None)
    if me:
        rates = sorted(r['hitRate'] for r in board['rows'] if r['calls'] >= 3)
        pct = round(sum(1 for v in rates if v <= me['hitRate']) / max(1, len(rates)) * 100) if me['calls'] >= 3 else None
        cats.append({'id': 'caller', 'label': 'Caller', 'score': round(me['hitRate'] * 100), 'percentile': pct,
                     'detail': f"{me['calls']} calls · {me['hits']} hit 2× · {me.get('rugs', 0)} rugged", 'good': me['hitRate'] >= 0.3})
    bl = rs._block_load()['wallets'].get(a)
    strikes = len((bl or {}).get('mints') or {})
    roles = sorted(set((bl or {}).get('mints', {}).values()))
    cats.append({'id': 'clean', 'label': 'Sniper / bundler record', 'score': 100 if not strikes else max(0, 100 - strikes * 30),
                 'detail': 'never caught sniping or bundling' if not strikes else f"caught on {strikes} launch(es) as {', '.join(roles)}{' · BLOCKLISTED' if rs._is_blocked(bl) else ''}",
                 'good': not strikes})
    fd = rs._funders_load()
    frec = fd['funders'].get(a)
    funded_by = fd['offenderFunder'].get(a)
    if frec or funded_by:
        cats.append({'id': 'funding', 'label': 'Funding trail', 'score': 0 if frec and rs._is_flagged_funder(frec) else 40,
                     'detail': (f"bankrolled {len(frec['funded'])} sniper/bundler wallets across {len(frec['mints'])} launch(es)" if frec else '')
                               + (f"{' · ' if frec else ''}funded by {funded_by[:4]}…{funded_by[-4:]}" if funded_by else ''), 'good': False})
    fol = len([x for x, lst in rs._fol()['following'].items() if a in lst])
    cats.append({'id': 'social', 'label': 'Community', 'score': min(100, fol * 10), 'detail': f"{fol} followers{' · verified' if rs.is_verified(a) else ''}", 'good': fol >= 3 or rs.is_verified(a)})
    return {'address': a, 'trust': trust, 'categories': cats, 'at': rs.time.time()}


@router.get('/api/reputation/gas/{address}')
async def gas_check(address: str, sol: str = ''):
    """Which chains this wallet can (and can't) pay gas on — so the trade desk can offer a one-click
    route that converts something it already holds into gas where it's missing. `sol`: the same wallet's Solana side, read as a SOURCE
    (SOL pays for gas on any listed chain through LI.FI)."""
    rs = _rs()
    if not rs._re.match(r'^0x[0-9a-fA-F]{40}$', address):
        raise rs.HTTPException(400, 'EVM address required (0x…).')
    async with rs.httpx.AsyncClient(timeout=8) as http:
        px = await rs._native_prices(http)

        async def bal(chain, url):
            for u in dict.fromkeys([url, rs.GAS_RPC_PUBLIC.get(chain)]):
                if not u:
                    continue
                try:
                    r = await http.post(u, json={'jsonrpc': '2.0', 'id': 1, 'method': 'eth_getBalance', 'params': [address, 'latest']})
                    return chain, int(r.json()['result'], 16) / 1e18
                except Exception:
                    continue
            return chain, None

        async def sol_bal():
            if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', sol or ''):
                return None
            try:
                return (((await rs._rpc(http, 'getBalance', [sol])) or {}).get('value') or 0) / 1e9
            except Exception:
                return None
        res, sol_amt, sol_px = await rs.asyncio.gather(rs.asyncio.gather(*(bal(c, u) for c, u in rs.EVM_RPC.items() if c in rs.GAS_RPC_PUBLIC)), sol_bal(),
                                                    rs._sol_usd() if sol else rs.asyncio.sleep(0, None))
    out = []
    for chain, amt in res:
        sym = rs.NATIVE_SYMBOL.get(chain, 'ETH'); usd = amt * px.get(sym, 0) if amt is not None else None
        need = rs.GAS_MIN_USD.get(chain, 0.25)
        out.append({'chain': chain, 'symbol': sym, 'balance': amt, 'usd': round(usd, 2) if usd is not None else None,
                    'enough': usd is not None and usd >= need, 'minUsd': need})
    src = None
    if sol_amt is not None:
        usd = sol_amt * (sol_px or 0) if sol_px else None
        src = {'chain': 'solana', 'symbol': 'SOL', 'address': sol, 'balance': sol_amt, 'usd': round(usd, 2) if usd is not None else None}
    return {'address': address, 'chains': sorted(out, key=lambda x: -(x['usd'] or 0)), 'solana': src, 'at': rs.time.time()}


@router.get('/api/reputation/tokens/search')
async def token_search(q: str = Query(..., min_length=1, max_length=64)):
    """Name, $ticker or contract → Solana coins, biggest market cap first.
    Jupiter (keyed, then the keyless lite API) and DexScreener are merged, so one provider being down,
    rate-limited or missing a fresh Pump coin never leaves the swap picker empty."""
    rs = _rs()
    q = q.strip().lstrip('$')
    hit = rs._tok_search_cache.get(q.lower())
    if hit and rs.time.time() - hit[0] < 30:
        return hit[1]
    found: dict = {}
    blocks = rs._block_load()['wallets']

    def add(mint, **row):
        if not mint:
            return
        cur = found.setdefault(mint, {'mint': mint, 'symbol': None, 'name': None, 'icon': None, 'decimals': None,
                                      'price': None, 'mcap': None, 'liquidity': None, 'verified': False, 'blocked': False})
        for k, v in row.items():
            if v not in (None, '') and (cur.get(k) in (None, '', False) or k in ('mcap', 'liquidity') and (v or 0) > (cur.get(k) or 0)):
                cur[k] = v

    async with rs.httpx.AsyncClient(timeout=8) as http:
        async def jupiter():
            key = rs._jkeys.read_key(rs.os.environ) or ''
            urls = ([('https://api.jup.ag/tokens/v2/search', {'x-api-key': key})] if key else []) + [('https://lite-api.jup.ag/tokens/v2/search', {})]
            for url, headers in urls:
                try:
                    r = await http.get(url, params={'query': q}, headers=headers)
                    if r.status_code == 200 and isinstance(r.json(), list):
                        return r.json()[:30]
                except Exception:
                    continue
            return []

        async def dexscreener():
            try:
                r = await http.get('https://api.dexscreener.com/latest/dex/search', params={'q': q})
                return [p for p in ((r.json() or {}).get('pairs') or []) if p.get('chainId') == 'solana'][:40] if r.status_code == 200 else []
            except Exception:
                return []

        jup, dex = await rs.asyncio.gather(jupiter(), dexscreener())
    for t in jup:
        add(t.get('id'), symbol=t.get('symbol'), name=t.get('name'), icon=t.get('icon'), decimals=t.get('decimals'), price=t.get('usdPrice'),
            mcap=t.get('mcap') or t.get('fdv'), liquidity=t.get('liquidity'), verified=bool(t.get('isVerified')),
            blocked=rs._is_blocked(blocks.get(t.get('dev') or '')))
    for p in dex:
        b = p.get('baseToken') or {}
        add(b.get('address'), symbol=b.get('symbol'), name=b.get('name'), icon=(p.get('info') or {}).get('imageUrl'),
            price=float(p['priceUsd']) if p.get('priceUsd') else None, mcap=p.get('marketCap') or p.get('fdv'),
            liquidity=(p.get('liquidity') or {}).get('usd'))
    # An exact contract paste leads, then Jupiter-verified coins, then market cap (owner 2026-11-11: a fake "USDC " reporting a $76B cap
    # outranked the real USDC — a self-reported cap is not trust).
    rows = sorted(found.values(), key=lambda x: (x['mint'] != q, not x['verified'], -(x['mcap'] or 0), -(x['liquidity'] or 0)))[:20]
    data = {'q': q, 'tokens': rows, 'ok': bool(jup or dex)}
    if rows:  # never cache a miss: a provider hiccup must not blank the picker for 30s
        rs._tok_search_cache[q.lower()] = (rs.time.time(), data)
    if len(rs._tok_search_cache) > 2000:
        rs._tok_search_cache.clear()
    return data


@router.get('/api/reputation/position/{address}/{token}')
async def position(address: str, token: str):
    """A wallet's position in one coin: exact on-chain fills first (any app), then the wallet-history provider, then
    FEELESS's own order records. Average entry, real balance, fees paid, per-trade P&L. Feeds the chart line + badge."""
    rs = _rs()
    if not (rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) or rs._re.match(r'^0x[0-9a-fA-F]{40}$', address)) or len(token) > 64:
        raise rs.HTTPException(400, 'Bad address.')

    async def history():
        try:
            await rs.wallet_trades(address)
        except Exception:
            pass   # wallet-history provider down: the chain + FEELESS's own records still give the position
    await rs._repair_estimates(address, token)
    _, fills, chain = await rs.asyncio.gather(history(), rs._feeless_fills(address), rs._chain_fills(address, token))
    tok = token.lower()
    provider = [r for r in (rs._wtrades_all.get(address) or (0, []))[1] if r['token'].lower() == tok]
    own = [r for r in rs._json_load(rs.FEELESS_TRADES_PATH, {}).get(address, []) + fills if r['token'].lower() == tok]
    # Locked rows first — every one of them was read from the chain once and priced at its own moment (FEELESS trades
    # at signing, outside trades at their block time) — then anything still waiting for its price, then estimates.
    cf = chain.get('fills') or []
    rows = rs.trade_fills.merge([r for r in cf if r.get('locked')], [r for r in own if r.get('locked')],
                             [r for r in cf if not r.get('locked')], [r for r in own if not r.get('locked')], provider)
    fees = {r.get('sig'): r.get('feeUsd') or 0 for r in rs._json_load(rs.FEE_LEDGER_PATH, {}).get(rs.primary_of(address), [])}
    pos = rs.trade_fills.position(rows, chain.get('balance') if 'balance' in chain else None, fees)
    if pos:
        pos['sources'] = {k: sum(1 for r in rows if (r.get('via') or 'provider') == k) for k in ('chain', 'estimate', 'feeless', 'provider')}
        pos['chainRead'] = 'balance' in chain
    return {'address': address, 'token': token, 'position': pos, 'balance': chain.get('balance')}


@router.get('/api/reputation/trade-cards/{address}')
async def trade_cards(address: str):
    """A wallet's recent FEELESS trades as shareable cards: side, size, per-sell P&L (average cost), fee, tx, coin."""
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        raise rs.HTTPException(400, 'Bad address.')
    own = rs._json_load(rs.FEELESS_TRADES_PATH, {}).get(address, [])
    rows = rs.trade_fills.merge(await rs._locked_fills(address), [r for r in own if r.get('locked')], own, await rs._feeless_fills(address))
    fees = {r.get('sig'): r.get('feeUsd') or 0 for r in rs._json_load(rs.FEE_LEDGER_PATH, {}).get(rs.primary_of(address), [])}
    cards = []
    for tok in {r['token'] for r in rows}:
        mine = [r for r in rows if r['token'] == tok]
        pos = rs.trade_fills.position(mine, None, fees)
        for t in (pos or {}).get('trades') or []:
            cost = (t.get('tokens') or (t['usd'] / t['price'])) * pos['avgEntry']
            cards.append({**t, 'token': tok, 'pnlPct': round(t['pnlUsd'] / cost * 100, 2) if t.get('pnlUsd') is not None and cost else None})
    cards = sorted(cards, key=lambda c: -(c.get('ts') or 0))[:24]

    async def sym(mint):
        try:
            async with rs.httpx.AsyncClient(timeout=4) as http:
                r = await http.get(f'http://127.0.0.1:5001/api/trading/mint/{mint}')
                return mint, (r.json().get('symbol') if r.status_code == 200 else None)
        except Exception:
            return mint, None
    symbols = dict(await rs.asyncio.gather(*(sym(m) for m in list({c['token'] for c in cards})[:12])))
    for c in cards:
        c['symbol'] = symbols.get(c['token'])
    return {'address': address, 'cards': cards}


@router.get('/api/reputation/shields/leaderboard')
async def shield_leaderboard():
    rs = _rs()
    now = rs.time.time(); by = {}
    for mint, s in rs._json_load(rs.SHIELD_PATH, {}).items():
        r = by.setdefault(s['creator'], {'creator': s['creator'], 'kept': 0, 'broken': 0, 'active': 0, 'coins': []})
        st = 'broken' if s['breaches'] else ('active' if now - s['at'] < s['lockDays'] * 86400 else 'kept')
        r[st] += 1; r['coins'].append({'mint': mint, 'status': st})
    rows = sorted(by.values(), key=lambda r: (-(r['kept'] * 3 + r['active'] - r['broken'] * 10), -r['kept']))
    for r in rows:
        r['handle'] = rs.handle_of(r['creator']); r['score'] = r['kept'] * 3 + r['active'] - r['broken'] * 10
    return {'rows': rows[:50]}


@router.get('/api/reputation/launch-check/{mint}')
async def launch_check(mint: str, rail: str = 'pump'):
    """After a launch: is the coin really live? Mint on-chain (RPC), listed on pump.fun (pump rail), seen by DexScreener."""
    rs = _rs()
    if not rs._re.match(rs._B58, mint):
        raise rs.HTTPException(400, 'Bad address.')

    async def chain():
        try:
            async with rs.httpx.AsyncClient(timeout=8) as http:
                return bool(((await rs._rpc(http, 'getAccountInfo', [mint, {'encoding': 'base64', 'commitment': 'confirmed'}])) or {}).get('value'))
        except Exception:
            return None

    async def pump():
        if rail != 'pump':
            return None
        try:
            async with rs.httpx.AsyncClient(timeout=8, headers={'User-Agent': 'Mozilla/5.0'}) as http:
                r = await http.get(f'https://frontend-api-v3.pump.fun/coins-v2/{mint}')
            return r.status_code == 200 and (r.json() or {}).get('mint') == mint
        except Exception:
            return None

    async def dex():
        try:
            async with rs.httpx.AsyncClient(timeout=8) as http:
                r = await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{mint}')
            return bool((r.json() or {}).get('pairs'))
        except Exception:
            return None
    on_chain, on_pump, on_dex = await rs.asyncio.gather(chain(), pump(), dex())
    return {'mint': mint, 'rail': rail, 'onChain': on_chain, 'onPump': on_pump, 'onDex': on_dex,
            'pumpUrl': f'https://pump.fun/coin/{mint}' if rail == 'pump' else None}


@router.get('/api/reputation/token-logo/{mint}')
async def token_logo(mint: str, w: int = 0):
    """A coin's logo. `?w=64|128|256` answers a small webp of it (cached on disk per size), for rows and chips that show it at ≤ 128 px."""
    rs = _rs()
    from fastapi.responses import FileResponse, Response
    got = await rs._token_logo_any(mint)
    if w not in rs.LOGO_THUMBS:
        return got
    over = isinstance(got, FileResponse) and 'max-age=300' in str(got.headers.get('cache-control') or '')   # the owner's own logo can change: never kept as a thumb
    tdir = rs.LOGO_DIR / 'w'; tf = tdir / f'{mint}-{w}.webp'
    if not over and tf.exists():
        return FileResponse(tf, media_type='image/webp', headers={'Cache-Control': 'public, max-age=604800, immutable'})
    raw = rs.Path(got.path).read_bytes() if isinstance(got, FileResponse) else bytes(got.body)
    small = await rs.asyncio.to_thread(rs._logo_thumb, raw, w)
    if not small:
        return got
    if not over:
        tdir.mkdir(parents=True, exist_ok=True); tf.write_bytes(small)
    return Response(small, media_type='image/webp', headers={'Cache-Control': 'public, max-age=300' if over else 'public, max-age=604800, immutable'})


@router.get('/api/reputation/wallet-dust/solana/{address}')
async def wallet_dust_solana(address: str):
    """Every coin account in this Solana wallet: $ value, the rent it locks, and the cleanup it allows (swap · burn + close · close). Read-only."""
    rs = _rs()
    if not rs._re.match(rs._B58, address):
        raise rs.HTTPException(400, 'Not a Solana address.')
    async with rs.httpx.AsyncClient(timeout=15) as http:
        accts = await rs._sol_token_accounts(http, address)
    meta = await rs._jup_tokens([a['mint'] for a in accts]) if accts else {}
    prices = {m: (v or {}).get('usdPrice') for m, v in (meta or {}).items()}
    rows = rs._dust.classify(accts, prices, meta)
    return {'chain': 'solana', 'address': address, 'rows': rows, 'summary': rs._dust.summary(rows), 'swapMinUsd': rs._dust.SWAP_MIN_USD}


@router.get('/api/reputation/wallet-dust/cronos/{address}')
async def wallet_dust_cronos(address: str, add: str = Query('')):
    """EVERY Cronos token this wallet holds, each balance read on-chain by us (balanceOf). Which contracts to read: the swap router's list, a DEX
    list, the contracts a wallet index reports for this wallet (discovery only) and any contract pasted in `add`. Read-only; swaps go through LI.FI."""
    rs = _rs()
    if not rs._re.match(rs._EVM_ADDR, address):
        raise rs.HTTPException(400, 'Not an EVM address.')
    async with rs.httpx.AsyncClient(timeout=15) as http:
        toks, indexed = await rs._cronos_candidates(http, address)
        known = {str(t.get('address')).lower() for t in toks}
        extra = [a for a in rs._dust.clean_contracts(add) if a not in known]
        if extra:   # a pasted contract no list knows: its own decimals() + symbol()
            toks = rs._dust.merge_tokens(toks, rs._dust.meta_tokens(extra, await rs._cronos_batch(http, rs._dust.meta_calls(extra))))
        res = await rs._cronos_batch(http, rs._dust.balance_calls(address, toks))
        if not res:
            raise rs.HTTPException(503, 'Cronos RPC did not answer — try again in a few seconds.')
    rows = rs._dust.evm_rows(toks, res)
    native = int(res.get(0) or '0x0', 16) / 1e18 if res.get(0) else 0.0
    return {'chain': 'cronos', 'address': address, 'rows': rows, 'nativeCro': native, 'swapMinUsd': rs._dust.SWAP_MIN_USD, 'checked': len(toks), 'indexed': indexed,
            'summary': {'coins': len(rows), 'swapUsd': round(sum(r['usd'] or 0 for r in rows if r['best'] == 'swap'), 2)}}


@router.get('/api/reputation/wallet-dust/evm/{address}')
async def wallet_dust_evm(address: str, add: str = Query('')):
    """🌐 EVERY eco this EVM wallet holds something on (owner: "every single eco positive account"): LI.FI's wallet balances across all the chains
    FEELESS signs on, plus our own Cronos read (LI.FI's list missed Cronos). Native coin = that chain's gas; tokens swap to it through LI.FI."""
    rs = _rs()
    if not rs._re.match(rs._EVM_ADDR, address):
        raise rs.HTTPException(400, 'Not an EVM address.')

    cro_meta: dict = {}

    async def lifi():
        try:
            async with rs.httpx.AsyncClient(timeout=20) as http:
                r = await http.get(f'https://li.quest/v1/wallets/{address}/balances', params={'extended': 'true'})
                return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    async def cro():
        try:
            d = await rs.wallet_dust_cronos(address, add)
        except Exception:
            return []
        cro_meta.update(checked=d.get('checked'), indexed=d.get('indexed'))
        rows = [{**r, 'chain': 'cronos', 'chainId': 25, 'native': False} for r in d.get('rows') or []]
        if rs._fuse._f(d.get('nativeCro')) > 0:
            px = next((rs._fuse._f(t.get('priceUSD')) for t in (rs._lifi_tok_cache.get(25) or (0, []))[1] if (t.get('symbol') or '').upper() == 'WCRO'), 0.0)
            rows.append({'chain': 'cronos', 'chainId': 25, 'address': rs._dust.NATIVE_EVM, 'symbol': 'CRO', 'name': 'Cronos', 'logo': '', 'decimals': 18,
                         'raw': str(int(rs._fuse._f(d['nativeCro']) * 1e18)), 'ui': rs._fuse._f(d['nativeCro']), 'usd': round(rs._fuse._f(d['nativeCro']) * px, 4) if px else None,
                         'price': px or None, 'native': True, 'best': 'gas', 'actions': []})
        return rows
    doc, cro_rows = await rs.asyncio.gather(lifi(), cro())
    rows = rs._dust.merge_evm(rs._dust.lifi_rows(doc), cro_rows)
    rows.sort(key=lambda r: (r['chain'], not r['native'], -(r['usd'] or 0)))
    return {'chain': 'evm', 'address': address, 'rows': rows, 'chains': rs._dust.by_chain(rows), 'swapMinUsd': rs._dust.SWAP_MIN_USD, 'cronos': cro_meta,
            'summary': {'coins': len(rows), 'chains': len({r['chain'] for r in rows}), 'usd': round(sum(r['usd'] or 0 for r in rows), 2),
                        'swapUsd': round(sum(r['usd'] or 0 for r in rows if r['best'] == 'swap'), 2), 'dust': sum(1 for r in rows if r['best'] == 'dust')}}

