"""🧩 SITE-5 slice 8 (2026-11-13): plain read routes (GET, no admin, no money, no staff checks), moved out of reputation_service by
scripts/move-routes.py. Helpers stay there and are looked up on reputation_service when a route runs, so a test that patches them still works."""
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
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
    ip_ = rs._guard.request_ip(request); now = rs.time.time()
    h_ = [t_ for t_ in rs._appr_hits.get(ip_, []) if now - t_ < 3600]
    if len(h_) >= 20:
        raise rs.HTTPException(429, 'Too many checks from here — try again in a while.')
    rs._appr_hits[ip_] = h_ + [now]
    if len(rs._appr_hits) > 5000:
        rs._appr_hits.clear()
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

