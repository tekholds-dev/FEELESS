"""🧹 Arena Prime — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


def _prime_cfg():
    rs = _rs()
    cfg = rs._prime.clean_cfg((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cfg') or {})
    cal = rs._fw.calibrate(rs._fw_peek().get('ledger'))
    if cal.get('feeUsd') is not None:   # 🎯 paper pays what a real swap from the Fuse wallet costs (network + priority)
        cfg['paperFeeUsd'] = cal['feeUsd']
    return cfg


def _ladder_value(card):
    """🪜 What the real card is worth for its ladder stage: its value at the last round bell (else its run start)."""
    rs = _rs()
    return rs._fuse._f((card or {}).get('roundStartUsd')) or rs._fuse._f((card or {}).get('startUsd'))


def _ladder_step(card, cfg, now):
    """🪜 Move the real card up / down the size ladder (hysteresis in arena_prime.ladder_stage); one event per change."""
    rs = _rs()
    if not (card and card.get('real') and cfg.get('ladder')):
        return card
    prev = card.get('ladderStage')
    st = rs._prime.ladder_stage(rs._ladder_value(card), prev)
    if st != prev:
        card['ladderStage'] = st
        v = rs._prime.ladder_view(st)
        if prev:
            card.setdefault('events', []).append({'at': now, 'kind': 'ladder', 'text': f"🪜 ${rs._ladder_value(card):.2f} card → {v['name']}: {v['why']}"})
            card['events'] = card['events'][-60:]
    return card


def _prime_real_cfg(pr=None):
    """💵 The REAL card's own config (`prime.realCfg`): separate from paper — HQ/engine tunes, meta config and tier locks only ever write the
    paper `cfg`. Not set yet → it starts as a copy of today's paper config. Any clock (5 min too) is allowed."""
    rs = _rs()
    pr = pr if pr is not None else (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {})
    paper = rs._prime_cfg()
    rc = pr.get('realCfg')
    if isinstance(rc, dict) and rc:
        out = rs._prime.clean_cfg(rc)
        if 'instantSwapPct' not in rc:
            out['instantSwapPct'] = out['rotateMinDrop']
        if out.get('ladder'):   # 🪜 the playbook of the real card's size stage (set by the tier tick) on top of the owner's config
            rcard = next((c for c in ((pr.get('cards') or {}).values()) if (c or {}).get('real')), None) or {}
            out = rs._prime.clean_cfg(rs._prime.ladder_patch(out, rcard.get('ladderStage') or rs._prime.ladder_stage(rs._ladder_value(rcard)), pr.get('ladderKeep') or ()))
            out['ladder'] = True
            if 'instantSwapPct' not in rc:
                out['instantSwapPct'] = out['rotateMinDrop']
        out = rs._ng.night_cfg(out, rs.time.localtime().tm_hour, on=rc.get('nightShift', True) is not False)   # 🌙 00:00–09:00 the tighter night profile (ceilings only)
        return {**rs._prime.real_guard(out, pr.get('realOwnerSet') or ())[0], 'paperFeeUsd': paper['paperFeeUsd']}   # 💵 hard floors (owner's OFF hold wins)

    return rs._prime.real_guard({**paper, 'instantSwapPct': paper.get('rotateMinDrop', 0)})[0]


def _open_board(n=None):
    """🚪 The open trench list: every launch coin in the feed ranked as a front-runner, each with what it has not passed. `n` = how many
    (default the list's OPEN_MAX; the agents' intake reads the WHOLE feed)."""
    rs = _rs()
    rcfg = rs._runner_cfg()
    scanned = {}
    for r in rs._runner_cands:
        if r.get('mint') and r.get('scanned') and rs._fuse._f(r.get('top10')) > 0:   # a scan with no top-10 reading is not a scan (it read "top-10 hold 0%" = safe)
            bad = rs._rn.safety_fails(r, rcfg)
            scanned[r['mint']] = (not bad, bad[:4], {k: r.get(k) for k in ('top10', 'dev', 'insiders', 'bundled')})
    for p in rs._open_pairs:   # 🕵 a coin scanned on request (the agents' investigation, a quick look) but not on the runner board: judged the same way
        m = (p.get('baseToken') or {}).get('address')
        if m and m not in scanned:
            got = rs._open_scan_judge(p, m, rcfg)
            if got:
                scanned[m] = got
    return rs._trench.open_board(rs._open_pairs, scanned, rs.time.time() * 1000, **({'n': n} if n else {}))


def _open_scan_judge(pair, mint, rcfg):
    """(safe, fails, facts) for a coin whose OWN holder scan is in the intel cache and complete, else None. The SAME candidate + safety
    gates the runner board uses (same creator flag / rep inputs); nothing is loosened. Why: the agents request scans for their strongest
    unscanned cases, the scan landed in the cache, but the open list judged safety only from the runner board's candidates — so an older
    coin off that board read "holders never scanned" forever and its case could never clear (2026-10-10, $WOSE)."""
    rs = _rs()
    it = rs._intel_fresh(mint)
    if not it or it.get('top10Pct') is None or rs._fuse._f(it.get('top10Pct')) <= 0:
        return None
    key = it.get('checkedAt')
    hit = rs._open_scan_memo.get(mint)
    if hit and hit[0] == key:
        return hit[1]
    try:
        creator = it.get('creator')
        brec = rs._block_load()['wallets'].get(creator) if creator else None
        flagged = bool(creator and ((rs._is_blocked(brec) and brec.get('reported')) or (rs._shield_cache.get(creator, (0, {}))[1] or {}).get('verdict') == 'bot'))
        crep = None
        if creator:
            try:
                crep = rs._quick_rep(creator).get('level')
            except Exception:
                crep = None
            if rs._is_blocked(brec) and not brec.get('reported') and crep != 'high':
                crep = 'suspect'
        c = rs._rn.candidate(pair, it, flagged, False, rs.time.time() * 1000, mayhem=mint in rs._mayhem_mints, creator_rep=crep)
        if not c.get('scanned') or rs._fuse._f(c.get('top10')) <= 0:
            return None
        bad = rs._rn.safety_fails(c, rcfg)
        out = (not bad, bad[:4], {k: c.get(k) for k in ('top10', 'dev', 'insiders', 'bundled')})
    except Exception:
        return None
    if len(rs._open_scan_memo) > 2000:
        rs._open_scan_memo.clear()
    rs._open_scan_memo[mint] = (key, out)
    return out


def _jup_judge(pair, mint, facts, rcfg):
    """(safe, fails, facts) from JUPITER'S AUDIT when our own RPC holder scan has not landed — the same stand-in the runner board and the
    open board already use (`lite_intel`), judged by the SAME candidate + safety gates; live mint / freeze authority = flagged. Why
    (2026-10-11): the agents' intake rows for the newest launches never got it, so every seat's best candidate read "holders not scanned"
    while the RPC scanner (≈ 1 call/s) worked through its queue, and the real card sat with 4 empty seats. Our full scan still replaces it."""
    rs = _rs()
    it = rs._ja.lite_intel(facts)
    if not it or it.get('top10Pct') is None:
        return None
    try:
        creator = it.get('creator')
        brec = rs._block_load()['wallets'].get(creator) if creator else None
        flagged = bool(creator and ((rs._is_blocked(brec) and brec.get('reported')) or (rs._shield_cache.get(creator, (0, {}))[1] or {}).get('verdict') == 'bot')) or rs._ja.authority_bad(facts)
        c = rs._rn.candidate(pair, it, flagged, False, rs.time.time() * 1000, mayhem=mint in rs._mayhem_mints)
        if not c.get('scanned') or rs._fuse._f(c.get('top10')) <= 0:
            return None
        bad = rs._rn.safety_fails(c, rcfg)
        return (not bad, bad[:4], {k: c.get(k) for k in ('top10', 'dev', 'insiders', 'bundled')})
    except Exception:
        return None


async def _pump_calls_build(force=False):
    """📣 Pump's OWN callouts (pump_calls: ranked feed + newest + today's top by profit), re-read at most once a minute; one read in
    flight; a failed read keeps the last good board. Leaderboard coins get their ticker from Jupiter (the leaderboard carries none)."""
    rs = _rs()
    now = rs.time.time()
    if (not force and now - rs._pump_calls['at'] < rs._pc.TTL) or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return rs._pump_calls['board']
    if rs._pump_calls_flight.get('t'):
        return rs._pump_calls['board']
    if not force and not rs._FUSE_FORCE.get() and (rs._pump_calls['board'].get('coins') or rs._pump_calls['board'].get('top')):
        rs._pump_calls['at'] = now   # ⚡ a viewer gets the board in memory at once; ONE refresh runs behind it (it took 2–5s inline)
        rs.asyncio.create_task(rs._pump_calls_build(force=True))
        return rs._pump_calls['board']
    rs._pump_calls_flight['t'] = True
    rs._pump_calls['at'] = now
    try:
        base = rs.os.getenv('PUMP_API_URL', 'https://frontend-api-v3.pump.fun')
        async with rs.httpx.AsyncClient(timeout=10) as http:
            async def one(path, params):
                try:
                    r = await http.get(base + path, params=params, headers={'Accept': 'application/json'})
                    return r.json() if r.status_code == 200 else None
                except Exception:
                    return None
            home, new, top = await rs.asyncio.gather(one(rs._pc.HOME_PATH, rs._pc.HOME_PARAMS), one(rs._pc.NEW_PATH, rs._pc.NEW_PARAMS), one(rs._pc.TOP_PATH, rs._pc.TOP_PARAMS))
        if home or new or top:
            b = rs._pc.board(home, new, top, now * 1000)
            need = [t['mint'] for t in b['top'] if not t.get('symbol')]
            if need:
                try:
                    toks = await rs._jup_tokens(need)
                except Exception:
                    toks = {}
                for t in b['top']:
                    k = toks.get(t['mint']) or {}
                    t['symbol'] = t.get('symbol') or k.get('symbol')
                    t['logo'] = t.get('logo') or k.get('icon')
            calls_ = b.pop('calls', [])
            rs._pump_calls['calls'] = calls_[-600:]   # 📣 the raw calls: the callout-spike sell reads who is piling in right now
            try:   # 🎯 caller scoreboard: every call noted once, judged an hour later
                rs._pump_calls['callers'] = await rs.asyncio.to_thread(rs._pump_callers_pass, calls_, now)
                rs._pc.mark_pros(b, rs._pump_calls['callers'])
            except Exception as e:
                print('pump callers:', e)
            if b['coins'] or b['top'] or not rs._pump_calls['board']['coins']:
                rs._pump_calls.update(board=b, map={c['mint']: c for c in b['coins']}, ok=now)
            try:
                rs._call_rush_alert(calls_, now)
            except Exception as e:
                print('call rush:', e)
    finally:
        rs._pump_calls_flight['t'] = False
    return rs._pump_calls['board']


def _pc_rows(rows):
    """📣 `pc` on every row whose coin Pump's users are calling out (cache read only, never a fetch). In place."""
    rs = _rs()
    m_ = rs._pump_calls['map']
    if m_:
        for r in rows or []:
            c = m_.get(r.get('mint') or r.get('baseAddress'))
            if c:
                r['pc'] = rs._pc.summary(c)
    return rows


def _pump_callers_pass(calls, now):
    """🎯 The caller scoreboard's pass, in a WORKER THREAD (one at a time: `_pump_calls_flight`). The 30 MB record lives in memory — read
    once per start, written every 10 min with the soft encoder — it used to be parsed + re-written on the event loop every minute
    (≈ 4s of frozen service). `caller_track` returns a NEW state each pass, so the copy being written is never mutated."""
    rs = _rs()
    if rs._pump_callers['st'] is None:
        try:
            rs._pump_callers['st'] = rs.json.loads(rs.PUMP_CALLERS_PATH.read_text()) if rs.PUMP_CALLERS_PATH.exists() else {}
        except Exception:
            rs._pump_callers['st'] = {}
        rs._pump_callers['saved'] = now
    st = rs._pc.caller_track(rs._pump_callers['st'], calls, now * 1000)
    rs._pump_callers['st'] = st
    if now - rs._pump_callers['saved'] >= rs.PUMP_CALLERS_SAVE_SEC:
        rs._pump_callers['saved'] = now
        rs._json_save_soft(rs.PUMP_CALLERS_PATH, st)
    return rs._pc.caller_board(st)


def _call_rush_alert(calls, now):
    """🔔 The owner's early-caller alert (prime.callAlert.capK, off by default): 3+ different Pump callers on one coin inside 10 minutes
    while its cap is under the owner's line → ONE inbox + phone notice per coin per 6h. A heads-up only: nothing is bought."""
    rs = _rs()
    cap_k = int(rs._fuse._f(((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('callAlert') or {}).get('capK')))
    if cap_k not in rs._pc.RUSH_CAPS_K or cap_k <= 0:
        return []
    hits = [h for h in rs._pc.rush(calls, now * 1000, cap_k * 1000) if now - rs._rush_sent.get(h['mint'], 0) > 6 * 3600]
    for h in hits[:3]:
        rs._rush_sent[h['mint']] = now
        for w in rs._owner_wallets():
            rs.notify(w, 'fuse-signal', f"🔔 Call rush: {h['callers']} Pump callers on ${h.get('symbol') or h['mint'][:4]} in 10 minutes — cap ${h['mcap'] / 1000:,.0f}K. Other people's calls, not advice.",
                   url=f"/terminal/coin/solana/{h['mint']}", once=f"rush-{h['mint']}-{int(now // 21600)}", meta={'claim': f"{h['callers']} different callers inside 10 minutes", 'source': 'Pump callouts feed'})
    return hits


async def _mint_rows(mints, extra):
    """Coins known only by their mint → picker rows in the same shape as every other launch list (pair from Jupiter's token data)."""
    rs = _rs()
    try:
        toks = await rs._jup_tokens(list(mints))
    except Exception:
        toks = {}
    rows = []
    for m in mints:
        p_ = rs._launchpad_board.jup_pair(toks.get(m))
        if not p_ or rs._fuse._f(p_.get('priceUsd')) <= 0:
            continue
        p_ = rs._fuse.with_curve(p_)
        age_ = round((rs.time.time() * 1000 - rs._fuse._f(p_.get('pairCreatedAt'))) / 3.6e6, 1) if p_.get('pairCreatedAt') else None
        rows.append({'chainId': 'solana', 'pairAddress': p_.get('pairAddress'), **rs._fuse.leg_meta(p_), **({'curve': True} if p_.get('curve') else {}), 'ageH': age_,
                     'vol1h': rs._fuse._f((p_.get('volume') or {}).get('h1')), **extra(m)})
    return rows


async def _pump_call_rows():
    """📣 The picker's Pump callouts list: one row per called coin, loudest first."""
    rs = _rs()
    by = {c['mint']: c for c in (await rs._pump_calls_build()).get('coins') or []}
    return await rs._mint_rows(list(by), lambda m: {'divisionLabel': rs._pc.label(by[m]), 'pc': rs._pc.summary(by[m]), 'score': by[m].get('heat')})


async def _feeders_build():
    """🧲 Which runners new Pump launches are paired with (feeders.board), from Pump's newest + most recently traded coins. Re-read every
    2 min, pages one after another (Pump refuses bursts); a failed read keeps the last board."""
    rs = _rs()
    now = rs.time.time()
    if now - rs._feeders['at'] < rs.FEEDERS_TTL or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return rs._feeders['board']
    rs._feeders['at'] = now
    base = rs.os.getenv('PUMP_API_URL', 'https://frontend-api-v3.pump.fun')
    coins = []
    try:
        async with rs.httpx.AsyncClient(timeout=10) as http:
            for sort, offs in rs._fd.SOURCES:
                for off in offs:
                    try:
                        r = await http.get(base + '/coins', params={'offset': off, 'limit': 50, 'sort': sort, 'order': 'DESC', 'includeNsfw': 'false'})
                        if r.status_code == 200 and isinstance(r.json(), list):
                            coins += r.json()
                    except Exception:
                        pass
                    await rs.asyncio.sleep(0.25)
    except Exception:
        pass
    if coins:
        b = rs._fd.board(coins, now * 1000)
        names = dict(rs._feeders.get('names') or {})
        need = [m for m in b['runners'] if m not in names]
        if need:
            try:
                for m, t in (await rs._jup_tokens(need[:100])).items():
                    names[m] = t.get('symbol')
            except Exception:
                pass
        rs._feeders.update(board=b, names={m: v for m, v in names.items() if m in b['runners']})
    return rs._feeders['board']


async def _sf_read(src):
    """One source → posts in the shared shape (social_feed.py). Never raises: a source that fails returns [] and keeps its last copy."""
    rs = _rs()
    try:
        if src == 'pump':
            b_ = await rs._pump_calls_build()
            return rs._sfeed.from_pump((b_.get('latest') or [])[:40] + (b_.get('top') or [])[:20])
        if src == 'feeless':
            d_ = rs._chat_load()
            return [p_ for r_ in ('feed-general', 'feed-alpha', 'feed-memes', 'feed-launches', 'feeless-updates') for p_ in rs._sfeed.from_feeless([m_ for m_ in (d_['rooms'].get(r_) or [])[-60:] if not rs._OPS_PING.search(str(m_.get('text') or ''))][-40:], r_)]
        if src == 'x':
            return list((rs._json_load(rs.FEED_X_PATH, {}) or {}).get('posts') or [])
        if src == 'telegram':
            out_ = []
            for ch_ in rs._sfeed.TG_CHANNELS:
                r_ = await rs._sf_client().get(f'https://t.me/s/{ch_}')
                if r_.status_code == 200:
                    out_ += rs._sfeed.parse_telegram(r_.text, ch_)
            return out_
        if src == 'bluesky':
            r_ = await rs._sf_client().get('https://api.bsky.app/xrpc/app.bsky.feed.searchPosts', params={'q': rs._sfeed.BSKY_QUERY, 'limit': 40, 'sort': 'latest'})
            return rs._sfeed.parse_bluesky(r_.json()) if r_.status_code == 200 else []
    except Exception as e:
        print('social feed', src, str(e)[:100])
    return []


async def _sf_refresh(src):
    rs = _rs()
    try:
        posts_ = await rs._sf_read(src)
        if posts_ or src not in rs._SF_CACHE:
            rs._SF_CACHE[src] = {'at': rs.time.time(), 'posts': posts_}
        else:
            rs._SF_CACHE[src]['at'] = rs.time.time()
    finally:
        rs._SF_BUSY.discard(src)


async def _sf_receipts(posts, now):
    """🧾 Every post that names a coin gets its CALL RECEIPT: cap when first seen (or Pump's called cap) → cap now (Jupiter, 60s cache) = ×."""
    rs = _rs()
    out, need = [], []
    for p_ in posts:
        p_ = dict(p_)
        if not (p_.get('coin') or {}).get('mint'):
            m_ = rs._sfeed.find_mint(p_.get('text'))
            if m_:
                p_['coin'] = {'mint': m_, 'symbol': None}
        if (p_.get('coin') or {}).get('mint'):
            need.append(p_['coin']['mint'])
        out.append(p_)
    if not need:
        return out
    try:
        rows_ = await rs.asyncio.wait_for(rs._jup_tokens(need[:120]), 4)
    except Exception:
        rows_ = {}
    for p_ in out:
        m_ = (p_.get('coin') or {}).get('mint')
        if not m_:
            continue
        t_ = rows_.get(m_) or {}
        if not t_ and not (p_.get('coin') or {}).get('symbol'):
            p_['coin'] = None          # a random address, not a coin Jupiter knows
            continue
        r_ = rs._sfeed.receipt(p_, t_.get('mcap') or (p_.get('coin') or {}).get('mcap'), rs._SF_FIRST, now)
        if r_:
            r_['symbol'] = r_.get('symbol') or t_.get('symbol'); r_['icon'] = t_.get('icon')
        p_['coin'] = r_
    if len(rs._SF_FIRST) > 4000:
        for k_ in list(rs._SF_FIRST)[:1000]:
            rs._SF_FIRST.pop(k_, None)
    return out


async def _callout_tick(now):
    """📣 Every ~3.5 min: who the open list calls out (volume leader · mover · fresh launch), each noted once and settled 1h later."""
    rs = _rs()
    if now - rs._open_cache['at'] < rs._trench.CALLOUT_SEC or rs.os.environ.get('PYTEST_CURRENT_TEST') or not rs._open_pairs:
        return rs._open_cache
    rs._open_cache['at'] = now
    board = rs._open_board()
    calls = rs._trench.callouts(board)
    doc = rs._json_load(rs.TRENCH_CALLOUT_PATH, {})
    st = doc.get('state') or {}
    due = [m for s_ in st.values() for m, o in (s_.get('open') or {}).items() if now - rs._fuse._f(o.get('at')) >= rs._trench.PROOF_SEC]
    jp = await rs._jup_prices(due, judge=True) if due else {}
    st = rs._trench.meta_track(st, {k: [(r['mint'], r['price'], r.get('ageH')) for r in v] for k, v in calls.items()}, lambda m: (jp or {}).get(m), now, keys=rs._trench.CALLOUTS)
    names = dict(doc.get('names') or {})
    for v in calls.values():
        for r in v:
            names[r['mint']] = {'symbol': r['symbol'], 'pairAddress': r['pairAddress']}
    keep = {m for s_ in st.values() for m in list((s_.get('open') or {})) + [d.get('mint') for d in s_.get('done') or []]}
    rs._json_save(rs.TRENCH_CALLOUT_PATH, {'state': st, 'names': {m: v for m, v in names.items() if m in keep}, 'at': now})
    rs._open_cache.update(rows=board, calls={k: [r['mint'] for r in v] for k, v in calls.items()})
    return rs._open_cache


async def _trench_build(now):
    """🗑 Every ~2 min (warm loop): fresh launches breaking out with a real crowd. Cheap checks on the whole runner feed, then the
    on-chain holder count + mint/freeze authority for the busiest survivors only. Result cached for the tier tick (never fetched
    inside it). `checked` keeps why each finalist passed or failed (HQ / tests)."""
    rs = _rs()
    if now - rs._trench_cache['at'] < 120 or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return rs._trench_cache
    rs._trench_cache['at'] = now
    live = await rs._runner_live()
    seen, pool = set(), []
    own0 = rs._trench.clean_own((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('trenchCfg'))
    # finalists by the LOOSEST soft checks (the strictest level that passes wins) — or by the owner's own checks
    own_g0 = rs._trench.own_gate(own0) if own0['mode'] in ('own', 'meta') else None
    loose = rs._trench.loosest(own_g0)   # wide enough for EVERY meta (and the owner's own filter) to have finalists
    every = list(rs._runner_cands) or (live.get('passing') or []) + (live.get('dropped') or [])
    rs._trench_cache['seen'], rs._trench_cache['funnel'] = len(every), rs._trench.funnel(every, loose)[:8]   # 🔎 why coins didn't make it
    # ⏩ coins that pass EVERY cheap check and only wait on their holder scan get it now (busiest 12), instead of waiting their turn
    # on the runner board — they join the finalists on the next pass
    need = sorted((r for r in every if r.get('mint') and rs._trench.precheck(r, loose) == ['holder scan not done yet']), key=lambda r: -rs._fuse._f(r.get('vol1h')))[:12]
    if need:
        rs.asyncio.ensure_future(rs.asyncio.gather(*[rs._runner_intel(r['mint'], rs._enr.PRIO['MOVER'], 'trench finalist') for r in need], return_exceptions=True))
    for r in every:
        if r.get('mint') and r['mint'] not in seen and not rs._trench.precheck(r, loose):
            seen.add(r['mint']); pool.append(r)
    # 🎛 coins that fit the OWNER's filter take the holder-count seats first (busiest first inside each group)
    pool = sorted(pool, key=lambda r: (bool(own_g0) and bool(rs._trench.precheck(r, own_g0)), -rs._fuse._f(r.get('vol1h'))))[:rs.TRENCH_SCAN]
    async def one(r):
        try:
            h = await rs.asyncio.wait_for(rs._token_holders(r['mint']), 25)
            async with rs.httpx.AsyncClient(timeout=8) as http:
                auth = await rs._mint_authorities(http, r['mint'])
        except Exception:
            return None
        return r, (h or {}).get('holders'), auth
    got = [x for x in await rs.asyncio.gather(*[one(r) for r in pool]) if x]
    rs._trench_cache['got'] = got   # raw finalists (coin, holders, authorities): every 🧪 meta is judged on these
    rs._trench_judge()
    try:   # 📈 paper proof per meta: note what each passes now, settle what it passed an hour ago (Jupiter price; gone = −100%)
        gate_ = lambda x, cfg: rs._trench.gate(x[0], x[1], x[2], cfg)
        passing = {k: [(x[0]['mint'], x[0].get('price')) for x in got if gate_(x, rs._trench.meta_gate(k))[0]] for k in rs._trench.METAS}
        st = rs._json_load(rs.TRENCH_META_PATH, {})
        due = [m for s in st.values() for m, o in (s.get('open') or {}).items() if now - rs._fuse._f(o.get('at')) >= rs._trench.PROOF_SEC]
        jp = await rs._jup_prices(due, judge=True) if due else {}
        rs._json_save(rs.TRENCH_META_PATH, rs._trench.meta_track(st, passing, lambda m: (jp or {}).get(m), now))
    except Exception as e:
        print('trench proof:', e)
    try:   # 🎯 the same paper record for the three ENTRY setups: noted once when a safe coin shows the setup, settled 1h later
        safe = [r for r in rs._runner_cands if rs._rn.safe_only(r, rs._runner_cfg()) and rs._fuse._f(r.get('liq')) >= 10000]
        hits = {k: [] for k in rs._prime.ENTRY_SETUPS}
        for r in safe:
            hit = rs._prime.entry_setup(r)
            if hit and r.get('mint'):
                hits[hit[0]].append((r['mint'], r.get('price')))
        st = rs._json_load(rs.ENTRY_PROOF_PATH, {})
        due = [m for s_ in st.values() for m, o in (s_.get('open') or {}).items() if now - rs._fuse._f(o.get('at')) >= rs._trench.PROOF_SEC]
        jp = await rs._jup_prices(due, judge=True) if due else {}
        rs._json_save(rs.ENTRY_PROOF_PATH, rs._trench.meta_track(st, hits, lambda m: (jp or {}).get(m), now, keys=rs._prime.ENTRY_SETUPS))
    except Exception as e:
        print('entry proof:', e)
    await rs._bottom_track(now)
    await rs._call_track(now)
    await rs._procall_track(now)
    await rs._brain_track(now)
    await rs._li_track(now)
    try:   # 🔗 Pump's own socials for the open list's busiest coins + the real card's coins (lists read the cache)
        legs_ = [l.get('mint') for c_ in rs._prime_cards().values() if c_.get('real') for l in c_.get('legs') or []]
        await rs._pump_links_warm(legs_ + [r.get('mint') for r in (rs._open_board() or [])[:60]])
    except Exception as e:
        print('pump links:', e)
    await rs._lens_track(now)
    await rs._smart_track(now)
    await rs._edge_track(now)
    await rs._flow_settle(now)
    await rs._owner_moves_tick(now)
    await rs._study_tick(now)   # 👤 the owner study → 🗄 the AI memory + proposals (2026-10-15)
    return rs._trench_cache


def _owner_study(now):
    """👤 The owner study (owner_study.report) from the records FEELESS already keeps. Cached STUDY_EVERY."""
    rs = _rs()
    if rs._study['v'] is not None and now - rs._study['at'] < rs.STUDY_EVERY:
        return rs._study['v']
    log_ = next((v for k_, v in rs._json_load(rs.OWNER_MOVES_PATH, {}).items() if isinstance(v, dict)), {})
    arch_ = (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions')
    words_ = rs._ps.words(rs._ps.profile((rs._json_load(rs.PICK_STYLE_PATH, {}) or {}).get('log') or []))
    rep_ = rs._ost.report(rs._om.summary(log_), rs._of.owner_seats(arch_), rs._of.owner_hand(arch_), words_)
    rs._study.update(at=now, v=rep_)
    return rep_


async def _hint_grade(now):
    """✋ / 👍 your seat hints, graded 30 min later on the live price (right = the coin did not fall after you said hold / good entry).
    → the record the models read (`learn.ownerHints`) and the AI memory files."""
    rs = _rs()
    of_ = rs._office_state(); hl_ = list(of_.get('hintLog') or [])
    due_ = [h for h in hl_ if h.get('res') is None and now - rs._fuse._f(h.get('at')) >= rs._of.HINT_SEC and rs._fuse._f(h.get('px')) > 0]
    if due_:
        pm_ = await rs._live_px(list({h['mint'] for h in due_}))
        for h in due_:
            p_ = rs._fuse._f(pm_.get(h['mint'])) or rs._fuse._f((rs._jup_px_cache.get(h['mint']) or (0, 0))[1])
            if p_ > 0:
                h['res'] = round((p_ / rs._fuse._f(h['px']) - 1) * 100, 2)
        of_['hintLog'] = hl_
        rs._json_save(rs.OFFICE_PATH, of_)
    g_ = [h for h in hl_ if h.get('res') is not None]
    wins_ = [h for h in g_ if h['res'] >= rs.HOLD_WIN_PCT][-3:]
    if wins_:   # ✋ your HOLD that paid = a lesson both models read: what the chart showed, what Reaper wanted, how far it ran after
        rs._study['holdWins'] = [f"✋ the owner held ${h.get('sym')} at {rs._fuse._f(h.get('pct')):+.1f}%" + (f" while Reaper wanted {h['reaper']}" if h.get('reaper') else '')
                              + (f" ({h['base']})" if h.get('base') else '') + f" — 30 min later it was {h['res']:+.1f}% higher" for h in wins_]
    if g_:
        ok_ = sum(1 for h in g_ if h['res'] >= 0)
        rs._study['hints'] = {'n': len(g_), 'right': round(100 * ok_ / len(g_)), 'typical': sorted(h['res'] for h in g_)[len(g_) // 2],
                           'line': f"the owner's one-click HOLD / GOOD ENTRY calls: {len(g_)} graded, {round(100 * ok_ / len(g_))}% right (the coin held or rose 30 min later), typical {sorted(h['res'] for h in g_)[len(g_) // 2]:+.1f}%"}
    return rs._study.get('hints')


async def _study_tick(now):
    """Every STUDY_EVERY: rebuild the owner study, file its findings + the owner's lessons + live rules + the desk's closest coins into the
    AI memory (capped drawers), and file the study's suggestions as PENDING proposals in the Brain (the owner ✅ / ✕ each one)."""
    rs = _rs()
    try:
        await rs._hint_grade(now)
    except Exception as e:
        print('hint grade:', str(e)[:80])
    if now - rs._study['at'] < rs.STUDY_EVERY and rs._study['v'] is not None:
        return
    try:   # 🎙 this Mac's LM Studio preset re-reads what FEELESS learned (the desktop re-pulls /lan-install hourly)
        import feeless_mcp as _mcp_
        if await rs.asyncio.to_thread(_mcp_.write_local_preset):
            print('fee preset: updated from memory')
    except Exception as e_:
        print('fee preset:', str(e_)[:80])
    try:
        rep_ = await rs.asyncio.to_thread(rs._owner_study, now)
        mem_ = rs._aim.seed_site(rs._aim_mem.get() or {}, now)
        for i_, f_ in enumerate(rep_.get('findings') or []):
            mem_ = rs._aim.file(mem_, 'owner', f'study{i_}', f_, now)
        try:   # 🔁 every closed OSSY / G4 trade + its conversation becomes a lesson both models (and the chat) recall
            lg_ = rs._g4_state()['log']
            for p_ in [p_ for p_ in (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or [] if p_.get('g4') and p_.get('realPct') is not None][-20:]:
                m_ = p_.get('mint'); who_ = rs._air.model_name(rs.os.environ, p_.get('aiBy')) if p_.get('aiBy') else 'a model'
                buy_ = next((r_ for r_ in reversed(lg_) if r_.get('mint') == m_ and r_.get('action') == 'BUY'), None)
                talk_ = [r_ for r_ in lg_ if r_.get('mint') == m_ and r_.get('talk')][-2:]
                mem_ = rs._aim.file(mem_, 'lessons', f"duo:{m_}:{p_.get('at') or ''}", f"🔁 {who_} ${p_.get('sym') or p_.get('symbol') or '?'} {rs._fuse._f(p_['realPct']):+.1f}% ({str((p_.get('exit') or {}).get('rule') or '').split(' ')[0] or 'exit'})"
                                 + (f" — bought: {str(buy_.get('why') or '')[:90]}" if buy_ else '') + ''.join(f" · {t_.get('model')} said {str(t_.get('why') or '')[:70]}" for t_ in talk_), now)
        except Exception as e:
            print('duo lessons:', str(e)[:80])
        hl_ = rs._of.hold_lessons((rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions'))   # 🎓 your held trades: where the agents would have sold you early
        for i_, l_ in enumerate(hl_['lines']):
            mem_ = rs._aim.file(mem_, 'lessons', f'hold{i_}', '🎓 HOLD LESSON — ' + l_, now)
        if hl_['early']:
            mem_ = rs._aim.file(mem_, 'owner', 'holdEarly', 'Rules that would have sold the owner early (held ≥ 5 pts more): ' + ', '.join(f'{k} ×{v}' for k, v in sorted(hl_['early'].items(), key=lambda kv: -kv[1])), now)
        for k_, w_ in enumerate(rs._study.get('holdWins') or []):   # ✋ the owner's holds that ran → the lessons drawer every model case recalls
            mem_ = rs._aim.file(mem_, 'lessons', f'holdWin{k_}', w_, now)
        rs._study['holds'] = hl_
        for it_ in (rs._teach_state().get('items') or [])[-40:]:
            mem_ = rs._aim.file(mem_, 'lessons', f"{it_.get('kind')}:{str(it_.get('text'))[:40]}", f"{it_.get('kind')}: {it_.get('text')}" + (f" (${it_.get('sym')})" if it_.get('sym') else ''), rs._fuse._f(it_.get('at')) or now)
        for r_ in [x_ for x_ in (rs._json_load(rs.LAB_PATH, {}) or {}).get('rules') or [] if x_.get('status') == 'live'][:12]:
            mem_ = rs._aim.file(mem_, 'rules', f"lab:{r_.get('id')}", f"{r_.get('name')} ({r_.get('desk')}): {r_.get('why') or ''}", now)
        for m_, d_ in list(rs._tk.KERNEL.dec.items())[:400]:
            if d_.get('status') in ('READY', 'CONTENDING'):
                x_ = rs._tk.KERNEL.candidate(m_, d_) or {}
                mem_ = rs._aim.file(mem_, 'coins', m_, f"${x_.get('symbol')} {d_.get('status')} rank {rs._fuse._f(d_.get('rank')):.0f} · {str((d_.get('why') or [''])[0] if isinstance(d_.get('why'), list) else d_.get('why') or '')[:120]}", now)
        rs._aim_mem.put(rs._aim.prune(mem_, now), now)
        if rep_.get('suggestions'):
            items_ = [it_ for it_ in (rs._aic.check(x_)[0] for x_ in rep_['suggestions']) if it_]
            if items_:
                rs._chat['props'], new_ = rs._aic.propose(rs._chat_props(), items_, rs._chat_olds(), now, '👤 owner study')
                if new_:
                    rs._json_save(rs.AI_PROPOSALS_PATH, rs._chat['props'])
    except Exception as e:
        print('study tick:', str(e)[:120])


async def _owner_moves_tick(now):
    """🧾 Every ~2 min: note the owner's new moves on each real card (from the card's own activity), judge the ones that are 30 min
    old, and post what is worth knowing in the Fuse room: a lock as it happens, a move that turned out good, a callout that ran.
    Coin moves in % only — never the card's $ result."""
    rs = _rs()
    try:
        hq = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
        st = rs._json_load(rs.OWNER_MOVES_PATH, {})
        led = rs._fw_peek().get('ledger') or []
        posts = []
        for tid, c in hq.items():
            if not c.get('real'):
                continue
            log = dict(st.get(tid) or {})
            if not log.get('seenAt'):
                log['seenAt'] = now - 150   # first look: only what just happened (older events have no price of their moment)
            sym = {r['symbol']: {'mint': r['mint'], 'pair': r.get('pair')} for r in led[-800:] if r.get('card') == tid and r.get('symbol') and r.get('mint')}
            sym.update({l.get('symbol'): {'mint': l.get('mint'), 'pair': l.get('pairAddress')} for l in c.get('legs') or [] if l.get('mint')})
            fresh = {h_[1] for e in c.get('events') or [] if rs._fuse._f(e.get('at')) > rs._fuse._f(log.get('seenAt')) for h_ in [rs._om.classify(e)] if h_ and h_[1]}
            due = [r['mint'] for r in log.get('rows') or [] if (r.get('pct') is None and now - rs._fuse._f(r.get('at')) >= rs._om.SETTLE_SEC)
                   or (r.get('pct2h') is None and now - rs._fuse._f(r.get('at')) >= rs._om.LATE_SEC)]
            ob_ctx = {r_['mint']: r_ for r_ in (rs._open_board() if rs._open_pairs else (rs._open_cache.get('rows') or [])) if r_.get('mint')}   # 📸 the market at the move
            mine_ = {l.get('symbol') for l in c.get('legs') or [] if l.get('picked') or l.get('ownerLvAt')}
            mints = list(dict.fromkeys([sym[x]['mint'] for x in fresh if x in sym] + due))
            jp = (await rs._jup_prices(mints, judge=True)) if mints else {}
            log, added = rs._om.collect(log, c, lambda x: ({**sym[x], 'px': (jp or {}).get(sym[x]['mint']), 'ctx': ob_ctx.get(sym[x]['mint'])} if x in sym else None), now, mine=mine_)
            log, done = rs._om.settle(log, lambda m: (jp or {}).get(m), now)
            st[tid] = log
            posts += rs._om.calls(added, done)
        rs._json_save(rs.OWNER_MOVES_PATH, st)
        doc = rs._json_load(rs.TRENCH_CALLOUT_PATH, {})   # 📣 a callout that ran
        now_px = {r['mint']: r['price'] for r in (rs._open_board() if rs._open_pairs else (rs._open_cache.get('rows') or []))}
        for x in rs._trench.callout_feed(doc.get('state') or {}, doc.get('names') or {}, now_px, now):
            if x.get('live') and x.get('pct') is not None and x['pct'] >= rs.CALL_RUN_PCT and x.get('symbol'):
                mins = max(1, round((now - rs._fuse._f(x.get('at'))) / 60))
                posts.append((f"callrun:{x['mint']}:{x['kind']}", f"📣 ${x['symbol']} was called out as a {rs._trench.CALLOUTS[x['kind']][1].lower()} {mins}m ago — {x['pct']:+.0f}% since the call."))
        for key, text in posts[:4]:
            rs._fuse_chat('fuse-lab', text, key)
    except Exception as e:
        print('owner moves:', str(e)[:120])


async def _call_track(now):
    """🗑 Score the trench vital's calls (owner, 2026-10-08: "do all suggestions"): every coin on the open list gets its call; each coin is noted
    ONCE per call at its price and settled an hour later (no price then = −100%) → `call_proof.json`, `meta_proof` per call. The SAFE 🔥 SEND IT
    coins are kept in `_call_cache['send']` for the engine — used only once `send` is proven with ≥ CALL_AUTO_MIN settled."""
    rs = _rs()
    try:
        rows = rs._open_board() if rs._open_pairs else []
        await rs._jup_lite([r.get('mint') for r in rows])
        by, send, cmap_ = {k: [] for k in dict.fromkeys(rs.CALL_KEYS.values())}, [], rs._cand_map()
        for r in rows:
            m = r.get('mint')
            if not m or rs._fuse._f(r.get('price')) <= 0:
                continue
            tv = rs._ja.trench_verdict((rs._jup_facts.get(m) or (0, None))[1], r)
            k = rs.CALL_KEYS.get(tv['call'][1])
            rd = rs._read_for(r, cmap_)   # 🎢 / 🧲 calls are scored too (each coin once per call)
            if rd and rd.get('kind') in ('curve', 'dip') and rs.CALL_KEYS.get(rd['call'][1]) not in (None, 'watch', k):
                by[rs.CALL_KEYS[rd['call'][1]]].append((m, r['price']))
            if k:
                by[k].append((m, r['price']))
            if k == 'send' and r.get('safe') is True:
                send.append({**r, 'tv': tv})
        for (lens_, _c), (_at, doc_) in list(rs._disc_cache.items()):   # 🚀 / 🌊 / 🐋 each tab's own calls are scored too (the dressed lists in the cache)
            if lens_ not in ('movers', 'ptrend', 'volume', 'majors', 'stocks') or not isinstance(doc_, dict):
                continue
            for r in doc_.get('pools') or []:
                k_ = rs.CALL_KEYS.get(((r.get('tv') or {}).get('call') or [None, None])[1])
                m_ = r.get('baseAddress') or r.get('mint'); p_ = rs._fuse._f(r.get('priceUsd') or r.get('price'))
                if k_ and k_ != 'watch' and m_ and p_ > 0 and (m_, p_) not in by[k_]:
                    by[k_].append((m_, p_))
        st = rs._json_load(rs.CALL_PROOF_PATH, {})
        due = [m for s_ in st.values() for m, o in (s_.get('open') or {}).items() if now - rs._fuse._f(o.get('at')) >= rs._trench.PROOF_SEC]
        jp = await rs._jup_prices(due, judge=True) if due else {}
        st = rs._trench.meta_track(st, by, lambda m: (jp or {}).get(m), now, keys=tuple(by))
        rs._json_save(rs.CALL_PROOF_PATH, st)
        rs._call_cache.update(at=now, send=sorted(send, key=lambda x: -rs._fuse._f(x['tv'].get('heat')))[:10], proof=rs._trench.meta_proof(st, keys=tuple(by)))
    except Exception as e:
        print('call proof:', e)


def _sendit_ready():
    rs = _rs()
    p = (rs._call_cache.get('proof') or {}).get('send') or {}
    return bool(p.get('proven') and int(p.get('n') or 0) >= rs.CALL_AUTO_MIN)


async def _procall_track(now):
    """🎯 The pro-call entry's own record: every coin it would hand the trench seat is noted once and settled an hour later
    (no price = −100%) — the same honest scoring as every other list."""
    rs = _rs()
    try:
        rows = rs._pc.pro_entries(rs._pump_calls.get('calls') or [], rs._pump_calls.get('callers') or {}, rs._open_board(), now * 1000)
        st = rs._json_load(rs.PROCALL_PROOF_PATH, {})
        due = [m for s_ in st.values() for m, o in (s_.get('open') or {}).items() if now - rs._fuse._f(o.get('at')) >= rs._trench.PROOF_SEC]
        jp = await rs._jup_prices(due, judge=True) if due else {}
        rs._json_save(rs.PROCALL_PROOF_PATH, rs._trench.meta_track(st, {'pro': [(r['mint'], r.get('price')) for r in rows]}, lambda m: (jp or {}).get(m), now, keys=('pro',)))
    except Exception as e:
        print('procall proof:', e)


def _li_state():
    rs = _rs()
    if rs._li_st['st'] is None:
        rs._li_st['st'] = rs._json_load(rs.LI_PATH, {})
    return rs._li_st['st']


def _li_parts(mint, ageH=None):
    """🕵 (early map, class, evidence, players, creator) for one coin from the CACHES only (launch facts + holder scan + funder links)."""
    rs = _rs()
    lf = rs._launch_facts.get(mint) or {}
    hit = rs._intel_cache.get(mint)
    it = (hit[1] if hit else {}) or {}
    creator = it.get('creator') or lf.get('creator')
    ff = it.get('flaggedFunders') or {}
    early = lf.get('early') or []
    m = rs._li.early_map(early, it.get('flaggedHoldings'), {e['w']: (ff.get(e['w']) or {}).get('funder') for e in early}, creator, young=ageH is not None and rs._fuse._f(ageH) < 1)
    bn = None if it.get('bundledWallets') is None and not lf else len(it.get('bundledWallets') or lf.get('bundled') or [])
    sn = None if it.get('sniperWallets') is None and not lf else len(it.get('sniperWallets') or lf.get('snipers') or [])
    cls, ev = rs._li.classify(m, bn, sn, it.get('insidersHoldingPct'), bool(it.get('knownRings')))
    players = rs._li.known_players(m, rs._li_state().get('mem'))
    return m, cls, ev, players, creator


def _li_row(x, now):
    """The launch-intel line for one desk row (dict) — every field carries its evidence; None-safe."""
    rs = _rs()
    v, n, mint = x.get('vitals') or {}, x.get('nums') or {}, x.get('mint')
    m, cls, ev, players, creator = rs._li_parts(mint, v.get('ageH'))
    e = (rs._li_state().get('open') or {}).get(mint) or {}
    tr = rs._li.trend(e.get('hist'))
    at_, w_ = rs._flow_now.get(x.get('pair') or x.get('pairAddress')) or (0, None)
    press, pwhy = rs._li.pressure(w_ if w_ and now - rs._fuse._f(at_) <= 90 else None, m, players, creator)
    ph, healthy, why = rs._li.phase(n, m, tr, press, (x.get('chart') or {}).get('ext'))
    band = rs._li.rank_band(None, v.get('holders'))
    out = rs._li.view(m, cls, ev, tr, ph, healthy, why, press, pwhy, players, band, v.get('ageH'), v.get('mcap'))
    ch_ = x.get('chart') or {}
    out['pump'] = rs._li.pump_phase(n, ch_.get('state'), ph, None if v.get('ageH') is None else rs._fuse._f(v['ageH']) * 60, int(rs._fuse._f((ch_.get('f') or {}).get('n'))) or None)
    vpm_, bpm_ = rs._opp.velocity(x)
    out['vpm'], out['bpm'], out['fresh'] = vpm_, bpm_, rs._opp.fresh_bucket(x)[0]
    out['clsRec'] = (rs._li_state().get('byClass') or {}).get(cls)   # how this launch class really did (1h, settled) — learned, never assumed
    return out


def _li_attach(table, now):
    rs = _rs()
    for x in table or []:
        try:
            x['li'] = rs._li_row(x, now)
            x['mp'] = rs._mw.market_phase(x.get('chart'), x['li'])   # the trench phase (market_wake.PHASES)
        except Exception as e:
            print('launch intel:', e)
            break


async def _li_track(now):
    """🕵 Note every desk coin that has an early-buyer map (and the real card's coins), append its early-supply history, settle launches
    an hour old at Jupiter's price → wallet memory + the record per launch class. A pass where Jupiter answers nothing is skipped."""
    rs = _rs()
    try:
        st = dict(rs._li_state())
        for x in (rs._agents.get('table') or []):
            mint = x.get('mint')
            if not mint or not (rs._launch_facts.get(mint) or {}).get('early'):
                continue
            m, cls, _ev, _p, creator = rs._li_parts(mint, (x.get('vitals') or {}).get('ageH'))
            st = rs._li.note(st, mint, m, cls, x.get('px'), now, (x.get('vitals') or {}).get('ageH'), creator)
        due = [mt for mt, e in (st.get('open') or {}).items() if now - rs._fuse._f(e.get('t')) >= rs._li.SETTLE_SEC]
        jp = await rs._jup_prices(due, judge=True) if due else {}
        if not due or jp:
            st = rs._li.settle(st, lambda mt: (jp or {}).get(mt), now)
        st['byClass'] = rs._li.by_class(st.get('done'))
        rs._li_st['st'] = st
        rs._json_save(rs.LI_PATH, st)
    except Exception as e:
        print('launch intel track:', e)


async def _brain_track(now):
    """🧠 TRENCH BRAIN pass (~2 min, with the trench build): watched coins see their Jupiter price (first touch of +50 / −30 settles
    them), new open-list coins are noted with their features, the learned table + walk-forward proof are rebuilt for the lens / engine.
    A pass where Jupiter answers nothing is skipped (an outage must not read as every coin vanishing)."""
    rs = _rs()
    try:
        st = rs._json_load(rs.BRAIN_PATH, {})
        ob = rs._open_board() or []
        young = sorted((x for x in ob if x.get('ageH') is not None and rs._fuse._f(x['ageH']) <= rs.BRAIN_NEW_H), key=lambda x: rs._fuse._f(x['ageH']))[:rs.BRAIN_NEW]
        seen_ = {x.get('mint') for x in young}
        raw = [rs._with_tv(x) for x in young + [x for x in ob if x.get('mint') not in seen_][:rs.BRAIN_SEE]]   # 🆕 the NEWEST launches first, then the busiest
        tv_ = {x.get('mint'): x.get('tv') for x in raw}
        rows = [{**r, 'tv': tv_.get(r.get('mint')) or r.get('tv')} for r in rs._clean_rows([dict(x) for x in raw])]
        watch = list((st.get('open') or {}).keys())
        jp = await rs._jup_prices(watch, judge=True) if watch else {}
        if watch and not jp:
            return
        clean_ = rs._fuse._f(st.get('cleanFrom')) or now   # 🩹 results from here on were graded with every price source reachable (see edge_audit `since`)
        st = {**rs._tb.track(st, rows, lambda m: (jp or {}).get(m), now), 'cleanFrom': clean_}
        rs._json_save(rs.BRAIN_PATH, st)
        cl_ = rs._brain_clean(st)

        def _learn_tables():   # pure Python on a copy, in a worker thread: the table + summary + drain odds held the loop ~4.5s a pass
            return rs._tb.table(cl_['done']), rs._tb.summary(cl_), rs._drn.odds_table(cl_['done'])
        tbl_, sum_, odds_ = await rs.asyncio.to_thread(_learn_tables)
        rs._brain.update(at=now, tbl=tbl_, sum=sum_)
        rs._drn.set_table(odds_)   # 🔮 drain odds: the rug share per feature, from the same judged coins
    except Exception as e:
        print('trench brain:', e)


def _brain_clean(st):
    """The brain LEARNS only from coins settled since `cleanFrom`: before it a refused price source was filed as a vanished coin (−100%)."""
    rs = _rs()
    since = rs._fuse._f((st or {}).get('cleanFrom'))
    return {**(st or {}), 'done': [x for x in (st or {}).get('done') or [] if rs._fuse._f(x.get('at')) >= since]}


def _brain_state():
    rs = _rs()
    if rs._brain['sum'] is None:
        st = rs._brain_clean(rs._json_load(rs.BRAIN_PATH, {}))
        rs._brain.update(tbl=rs._tb.table(st.get('done') or []), sum=rs._tb.summary(st))
        rs._drn.set_table(rs._drn.odds_table(st.get('done') or []))
    return rs._brain


def _rush_rows():
    """⚡ The Rush board, server side: trench-gate passes + open-list coins whose holder scan PASSED, each with its read and the brain's
    learned play, scored by `arena_prime.rush_score` (the same rule the board draws) → best first, `trenchScore` 500 + score so the
    trench drop keeps this order. Never an unscanned or failed coin."""
    rs = _rs()
    b = rs._brain_state()
    seen, out = set(), []
    for x in list(rs._trench_cache.get('rows') or []) + [y for y in rs._open_board() or [] if y.get('safe') is True]:
        m = x.get('mint')
        if not m or m in seen:
            continue
        seen.add(m)
        r = rs._with_tv({**x, 'safe': True if x.get('safe') is None and x.get('ok') else x.get('safe')})
        sc = rs._tb.score(r, b['tbl'])
        if sc:
            r = {**r, 'brain': sc}
        v = rs._prime.rush_score(r)
        if v is not None:
            out.append({**r, 'rush': v, 'trenchScore': 500 + v, 'tag': '⚡ rush'})
    return sorted(out, key=lambda r: -r['rush'])[:12]


def _brain_ready():
    """The engine may take brain picks only once its walk-forward proof holds (top third positive, ≥ 10 pts over the bottom)."""
    rs = _rs()
    return bool(((rs._brain_state()['sum'] or {}).get('proof') or {}).get('proven'))


def _brain_rows():
    """🧠 Trench brain list: safe open-list coins ranked by their LEARNED play (what coins like this did — +50% first or −30% first),
    busted reads and rug ≥ 50 left out. Each row says the play, the hit rate and the cell that decides it."""
    rs = _rs()
    b = rs._brain_state()
    raw = [rs._with_tv(x) for x in rs._open_board() or []]
    tv_ = {x.get('mint'): x.get('tv') for x in raw}
    out = []
    for r in rs._clean_rows([dict(x) for x in raw]):
        r = {**r, 'tv': tv_.get(r.get('mint')) or r.get('tv')}
        sc = rs._tb.score(r, b['tbl'])
        if not sc or r.get('safe') is False or not rs._prime.trench_read_ok(r) or rs._fuse._f(r.get('price')) <= 0:   # unscanned newest coins stay (marked); a failed scan never
            continue
        lead = (sc['why'] or [None])[0]
        out.append({**r, 'baseAddress': r['mint'], 'priceUsd': r.get('price'), 'liquidityUsd': r.get('liq'),
                    'brain': sc, 'trenchScore': 300 + sc['est'],
                    'divisionLabel': f"🧠 learned play {sc['est']:+.0f}% · {sc['hit']}% hit +{rs._tb.TP_PCT:.0f}% first"
                                     + (f" · {lead[0]} → {lead[1]:+.0f}% (n {lead[2]})" if lead else ' · still learning')
                                     + ('' if r.get('safe') else ' · ❔ holders not scanned yet')})
    return sorted(out, key=lambda r: (-r['brain']['est'], -int(r.get('safe') is True), rs._fuse._f(r.get('ageH') if r.get('ageH') is not None else 99)))


async def _bottom_rows(now):
    """🟢 The Buy-bottom list (arena_prime.buy_bottom) from the live launch feed, deepest + turning first; 60s cache. Each coin's own
    chart read (the board's recorded prices) joins its row when we have one."""
    rs = _rs()
    if now - rs._bottom_cache['at'] < 60 or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return rs._bottom_cache['rows']
    rs._bottom_cache['at'] = now
    try:
        async with rs.httpx.AsyncClient(timeout=10) as http:
            got = await rs.asyncio.gather(*[http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': k, 'chain': 'solana', 'page': pg, 'scope': 'launchpads'})
                                         for k in ('trending', 'new') for pg in (1, 2, 3, 4)], return_exceptions=True)
        raw = [x for g in got if not isinstance(g, Exception) for x in (g.json().get('pairs') or [])]
    except Exception:
        return rs._bottom_cache['rows']
    paths = rs._json_load(rs.RUNNERS_PATH, {}).get('paths') or {}
    seen, rows = set(), []
    for p_ in raw:
        m_ = (p_.get('baseToken') or {}).get('address')
        if not m_ or m_ in seen or rs._fuse._f(p_.get('priceUsd')) <= 0 or rs._fuse._f((p_.get('liquidity') or {}).get('usd')) < 8000:
            continue
        seen.add(m_)
        meta = rs._fuse.leg_meta(p_); tx = (p_.get('txns') or {}).get('h1') or {}
        b_, s_ = rs._fuse._f(tx.get('buys')), rs._fuse._f(tx.get('sells'))
        row = {'chainId': 'solana', 'pairAddress': p_.get('pairAddress'), **meta, 'vol1h': rs._fuse._f((p_.get('volume') or {}).get('h1')),
               'buyShare': round(b_ / (b_ + s_) * 100) if b_ + s_ else meta.get('buyShare'), **rs._pedge._chart.keys(paths.get(m_) or [], now)}
        hit = rs._prime.buy_bottom(row)
        if hit and not rs._fw.dollar_named(row.get('symbol')):
            rows.append({**row, 'score': hit['score'], 'bottom': True, 'divisionLabel': hit['why']})
    rows.sort(key=lambda r: -r['score'])
    rs._bottom_cache['rows'] = rows[:120]
    return rs._bottom_cache['rows']


async def _lens_track(now):
    """📏 Each live list's top coins are noted once and settled an hour later (no price = −100%) — the owner can see which list
    pays before picking from it (2026-10-07: hand picks closed inside 15 min lost $8.74 on $97 in a day)."""
    rs = _rs()
    try:
        got = await rs.asyncio.gather(*[rs.fuses_discover(lens=k, chain='solana') for k in rs.LENS_TRACK], return_exceptions=True)
        passing = {k: [(r.get('baseAddress') or r.get('mint'), r.get('priceUsd') or r.get('price')) for r in ((g or {}).get('pools') or [])[:rs.LENS_TOP]]
                   for k, g in zip(rs.LENS_TRACK, got) if isinstance(g, dict)}
        for k, g in zip(rs.LENS_TRACK, got):   # ⏭ Coming up walks these lists from the top
            if isinstance(g, dict):
                rs._lens_rows[k] = [{'mint': r.get('baseAddress') or r.get('mint')} for r in (g.get('pools') or [])[:60]]
        st = rs._json_load(rs.LENS_PROOF_PATH, {})
        due = [m for s_ in st.values() for m, o in (s_.get('open') or {}).items() if now - rs._fuse._f(o.get('at')) >= rs._trench.PROOF_SEC]
        jp = await rs._jup_prices(due, judge=True) if due else {}
        rs._json_save(rs.LENS_PROOF_PATH, rs._trench.meta_track(st, passing, lambda m: (jp or {}).get(m), now, keys=rs.LENS_TRACK))
    except Exception as e:
        print('lens proof:', e)


def _swapin_lists():
    """🧬 The owner's swap-in lists as the picker last dressed them (≤ 5 min old): {list: [rows in its own order]}."""
    rs = _rs()
    now, out = rs.time.time(), {}
    for k in ('ptrend', 'calls', 'double', 'fed', 'movers', 'volume', 'pump'):
        hit = rs._disc_cache.get((k, 'solana'))
        if hit and now - hit[0] < 300 and isinstance(hit[1], dict):
            out[k] = [{**r, 'mint': r.get('baseAddress') or r.get('mint')} for r in (hit[1].get('pools') or [])[:60]]
    out['bottom'] = [{**r, 'mint': r.get('baseAddress') or r.get('mint')} for r in (rs._bottom_cache.get('rows') or [])[:60]]
    out['trench'] = [dict(r) for r in (rs._trench_cache.get('rows') or [])[:60]]
    return out


def _edge_rank():
    """🧬 Every swap-in coin ranked by evidence (confluence.rank), 20s cache."""
    rs = _rs()
    if rs.time.time() - rs._edge_rank_cache['at'] < 20 and rs._edge_rank_cache['rows']:
        return rs._edge_rank_cache['rows']
    combo = rs._trench.meta_proof(rs._json_load(rs.EDGE_PROOF_PATH, {}), keys=tuple(k for k in rs._json_load(rs.EDGE_PROOF_PATH, {}) if k != 'up'))
    calls = rs._call_cache.get('proof') or {}
    rows = rs._cf.rank(rs._swapin_lists(), rs._list_records(), calls, combo, lambda r: rs.CALL_KEYS.get(((r.get('tv') or {}).get('call') or [None, None])[1]), rs._real_table())
    sp_ = rs._trench.meta_proof(rs._json_load(rs.EDGE_PROOF_PATH, {}), keys=('smart',)).get('smart') or {}
    for r in rows:   # 🐳 smart wallets buying it now: a badge; it moves the score only once the radar's own record is in (≥ 5 settled)
        h_ = rs._smart_on(r['mint'])
        if h_:
            r['smart'] = len(h_)
            if rs._fuse._f(sp_.get('n')) >= 5:
                r['edge'] = {**r['edge'], 'edge': round(r['edge']['edge'] + rs._fuse._f(sp_.get('medPct')) / 2, 1), 'parts': r['edge']['parts'] + [[f"🐳 smart wallets buying ({len(h_)}) — radar record", sp_.get('medPct')]]}
    rows.sort(key=lambda x: (-x['edge']['edge'], -x['edge']['known']))
    rs._edge_rank_cache.update(at=rs.time.time(), rows=rows)
    return rows


async def _edge_track(now):
    """🧬 The learned layer: each top-ranked coin's combo bucket is noted once and settled an hour later; Coming up's ready coins too ('up')."""
    rs = _rs()
    try:
        rows = rs._edge_rank()[:rs.EDGE_TRACK_TOP]
        st = rs._json_load(rs.EDGE_PROOF_PATH, {})
        passing = {}
        for r in rows:
            p_ = rs._fuse._f(r.get('priceUsd') or r.get('price'))
            if p_ > 0:
                passing.setdefault(r['edge']['bucket'], []).append((r['mint'], p_))
        passing['up'] = [(m, p_) for m, p_ in rs._up_last if p_ > 0]
        passing['burst'] = [(m, p_) for m, p_ in rs._burst_last if p_ > 0]
        passing['smart'] = [(r['mint'], rs._fuse._f(r.get('priceUsd') or r.get('price'))) for r in rs._edge_rank()[:60] if rs._smart_on(r['mint']) and rs._fuse._f(r.get('priceUsd') or r.get('price')) > 0]
        keys = tuple(dict.fromkeys(list(st) + list(passing)))
        due = [m for s_ in st.values() for m, o in (s_.get('open') or {}).items() if now - rs._fuse._f(o.get('at')) >= rs._trench.PROOF_SEC]
        jp = await rs._jup_prices(due, judge=True) if due else {}
        rs._json_save(rs.EDGE_PROOF_PATH, rs._trench.meta_track(st, passing, lambda m: (jp or {}).get(m), now, keys=keys))
    except Exception as e:
        print('edge track:', e)


async def _bs_rows(ms):
    """🌊 BUYS vs SELLS per coin for the 5m and 1h windows (Jupiter's own window stats: $ bought vs $ sold, trades, price move) +, for a coin
    the real card holds, the live 90s tape. Rides on the coin-edge record (`bs`) — one shared poller for every bar on screen."""
    rs = _rs()
    now = rs.time.time()
    stale = [m for m in ms if now - rs._jup_facts.get(m, (0.0, None))[0] > rs.BS_FRESH]
    if stale and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        try:
            got = await rs._jup_tokens(stale)
            for m, t in (got or {}).items():
                rs._jup_facts[m] = (rs.time.time(), rs._ja.facts(t))
        except Exception:
            pass
    tape = {}
    for c in rs._prime_cards().values():
        for l in (c or {}).get('legs') or [] if (c or {}).get('real') else []:
            at, w = rs._flow_now.get(l.get('pairAddress'), (0, None))
            if w and now - at < 90 and l.get('mint') in ms:
                tape[l['mint']] = {k: w.get(k) for k in ('buyUsd', 'sellUsd', 'n', 'pxChg')}
    out = {}
    for m in ms:
        win = ((rs._jup_facts.get(m) or (0, None))[1] or {}).get('win') or {}
        row = {}
        for k in ('5m', '1h'):
            w = win.get(k) or {}
            if w.get('vol') and w.get('buyPct') is not None:
                b = w['vol'] * w['buyPct'] / 100
                row[k] = {'buyUsd': round(b, 2), 'sellUsd': round(w['vol'] - b, 2), 'n': w.get('trades'), 'pxChg': w.get('priceChg')}
        if m in tape:
            row['90s'] = tape[m]
        if row:
            out[m] = row
    return out


def feecat_pool_rows(kernel_rows, arena_rows, limit=60, agents_max=20):
    """🐱 FEECAT EATS ONLY WHAT THE ARENA AND THE AGENTS FOUND (owner, 2026-10-15: "have fee only taking arena / agent coins"): the agents'
    READY / CONTENDING coins first (their own order), then every coin the Arena ranks, one row per pool, dollar tickers dropped. Pure."""
    rs = _rs()
    out, seen = [], set()
    for src, rows in (('agents', (kernel_rows or [])[:agents_max]), ('arena', arena_rows)):   # 🐱 the agents' fresh coins AND the Arena's established ones — her core lane only buys 3-day+ coins (her own record)
        for r in rows or []:
            pa = r.get('pairAddress') or r.get('pair')
            if not pa or pa in seen or rs._fw.dollar_named(r.get('symbol')):
                continue
            seen.add(pa)
            out.append({'pairAddress': pa, 'mint': r.get('mint'), 'symbol': r.get('symbol'), 'src': src, 'why': r.get('tag') or r.get('divisionLabel') or src,
                        'status': ('READY' if 'READY' in str(r.get('tag') or '') else 'CONTENDING') if src == 'agents' else None})
            if len(out) >= limit:
                return out
    return out


def feecat_read(c, setups, bad):
    """🐱 One coin's chart read for FeeCat (pure): the three setups it shows, why it is a bad entry (gun line / chase / spike / SKIP), and the
    numbers behind them — germ distance, structure, higher / lower lows, how far under its high."""
    rs = _rs()
    ch = (c or {}).get('chart') or {}
    gd = ch.get('germDist') if ch.get('germDist') is not None else ch.get('germ5Dist')
    fd = ch.get('fvgDist') if ch.get('fvgDist') is not None else ch.get('fvg5Dist')
    return {'setups': list(setups or []), 'bad': bad or None, 'struct': ch.get('state'), 'germ': None if gd is None else round(rs._fuse._f(gd), 1),
            'fvg': None if fd is None else round(rs._fuse._f(fd), 1),
            'hl': int(rs._fuse._f(ch.get('hl'))), 'll': int(rs._fuse._f(ch.get('ll'))), 'distHigh': None if ch.get('distHigh') is None else round(rs._fuse._f(ch.get('distHigh')), 1)}


def duo_word(log, mint, now, window=1800.0):
    """🤝 OSSY / G4's newest BUY or SELL on this coin in the last 30 min (pure) → {who, action, why, ago} or None."""
    rs = _rs()
    for r in reversed(log or []):
        if r.get('mint') != mint or now - rs._fuse._f(r.get('at')) > window:
            continue
        act = r.get('action') if r.get('action') in ('BUY', 'SELL') else (r.get('view') if r.get('view') in ('BUY', 'SELL') else None)
        if act and r.get('model') in ('OSSY', 'G4'):
            return {'who': r['model'], 'action': act, 'why': str(r.get('why') or '')[:160], 'ago': round(now - rs._fuse._f(r.get('at')))}
    return None


def duo_lessons(log, by_model):
    """🎓 What FeeCat learns from OSSY / G4 (pure): each model's own closed-trade record + their newest final-review lessons."""
    les = [{'who': r.get('model') or r.get('by'), 'symbol': r.get('symbol'), 'pct': r.get('pct'), 'at': r.get('at'), 'lesson': str(r.get('why') or '')[:220]}
           for r in reversed(log or []) if r.get('action') == 'REVIEW'][:6]
    return {'record': by_model or {}, 'lessons': les}


def _list_records():
    rs = _rs()
    lens_ = rs._trench.meta_proof(rs._json_load(rs.LENS_PROOF_PATH, {}), keys=rs.LENS_TRACK)
    call_ = rs._trench.meta_proof((rs._json_load(rs.TRENCH_CALLOUT_PATH, {}) or {}).get('state') or {}, keys=('leader', 'mover', 'fresh'))
    meta_ = rs._trench.meta_proof(rs._json_load(rs.TRENCH_META_PATH, {}))
    tmeta = ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('trenchCfg') or {}).get('meta') or 'baby'
    return rs._trench.list_records(lens_, call_, rs._trench.meta_proof(rs._json_load(rs.BOTTOM_PROOF_PATH, {}), keys=('bottom',)).get('bottom'), meta_.get(tmeta), tmeta)


async def _bottom_track(now):
    """Note each coin on the Buy-bottom list once and settle it an hour later (no price then = −100%) → the list's own record."""
    rs = _rs()
    try:
        rows = await rs._bottom_rows(now)
        st = rs._json_load(rs.BOTTOM_PROOF_PATH, {})
        due = [m for s_ in st.values() for m, o in (s_.get('open') or {}).items() if now - rs._fuse._f(o.get('at')) >= rs._trench.PROOF_SEC]
        jp = await rs._jup_prices(due, judge=True) if due else {}
        rs._json_save(rs.BOTTOM_PROOF_PATH, rs._trench.meta_track(st, {'bottom': [(r['baseAddress'], r.get('priceUsd')) for r in rows[:40] if r.get('baseAddress')]},
                                                         lambda m: (jp or {}).get(m), now, keys=('bottom',)))
    except Exception as e:
        print('bottom proof:', e)


def _human_style():
    """👤 The owner's pick style for the paper cards switched to it → (tiers, profile | None, picks noted)."""
    rs = _rs()
    log = rs._json_load(rs.PICK_STYLE_PATH, {}).get('log') or []
    tiers = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('humanTiers')
    return (rs.HUMAN_TIERS_DEFAULT if tiers is None else [t for t in tiers if t in rs._prime.TEMPLATES]), rs._ps.profile(log), len(log)


async def _pick_style_note(mint, symbol, pair_address):
    """Note what a hand-picked coin looks like right now (the board's own row, else a fresh read of its pool). Never raises."""
    rs = _rs()
    try:
        c = next((r for r in rs._runner_cands if r.get('mint') == mint), None)
        if not c and pair_address:
            lp = (await rs._fuse_pairs([{'chainId': 'solana', 'pairAddress': pair_address}])).get(pair_address) or {}
            c = rs._rn.candidate(lp, None, False, False, rs.time.time() * 1000) if lp else None
        feats = rs._ps.snap(c)
        if feats:
            d = rs._json_load(rs.PICK_STYLE_PATH, {})
            d['log'] = rs._ps.note(d.get('log'), mint, symbol, feats, rs.time.time()); rs._json_save(rs.PICK_STYLE_PATH, d)
    except Exception:
        pass


def _trench_judge():
    """Judge the scanned finalists (`_trench_cache.got`) by the saved trench setting. Runs after each scan AND at once when the owner
    changes the setting (no 2-minute wait to see what the new rules find)."""
    rs = _rs()
    got = rs._trench_cache.get('got') or []
    own = rs._trench.clean_own((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('trenchCfg'))
    if own['mode'] in ('own', 'meta'):   # 🎛 own numbers, or a 🧪 named meta the owner's own soft checks (crowd, trades, volume, cap band, age) — the safety checks never move
        g_own = rs._trench.own_gate(own)
        res = [(g, *rs._trench.gate(g[0], g[1], g[2], g_own)) for g in got]
        rows = [{**rs._trench_row(g[0], g[1], g[2], g_own), 'trenchLevel': own['mode']} for g, _ok, _f in res]
        fb = []
        if not any(x['ok'] for x in rows):   # 👀 nothing fits those settings right now → what the ENGINE's scan (strict → widened) finds
            lvl_f, res_f = rs._trench.best_level(got, lambda g, cfg: rs._trench.gate(g[0], g[1], g[2], cfg))
            if lvl_f is not None:
                fb = [{**rs._trench_row(g[0], g[1], g[2], rs._trench.widen(lvl_f)), 'fallback': True} for g, ok_f, _x in res_f if ok_f]
        rs._trench_cache.update(rows=[x for x in rows if x['ok']], checked=rows, level=own['mode'], own=own, fallback=fb)
        return rs._trench_cache
    lvl, res = rs._trench.best_level(got, lambda g, cfg: rs._trench.gate(g[0], g[1], g[2], cfg))
    rows = [{**rs._trench_row(g[0], g[1], g[2], rs._trench.widen(lvl or 0)), 'trenchLevel': lvl or 0} for g, _ok, _f in res]
    rs._trench_cache.update(rows=[x for x in rows if x['ok']], checked=rows, level=lvl, own=own, fallback=[])
    return rs._trench_cache


async def _fuse_trench_raw(meta=''):
    """🗑 The trench scan's latest finalists (coin data only): holders, market cap, age and every check passed / failed.
    `meta` = VIEW the same finalists through a named 🧪 meta (read-only; the cards follow HQ's saved setting)."""
    rs = _rs()
    keys = ('mint', 'symbol', 'pairAddress', 'price', 'liq', 'holders', 'mcap', 'ageH', 'vol1h', 'buyShare', 'ok', 'fails', 'trenchWhy', 'trenchScore', 'trenchLevel')
    own = rs._trench.clean_own((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('trenchCfg'))
    g = rs._trench.own_gate(own) if own['mode'] in ('own', 'meta') else rs._trench.widen(rs._trench_cache.get('level') if isinstance(rs._trench_cache.get('level'), int) else 0)
    got = rs._trench_cache.get('got') or []
    proof_ = rs._trench.meta_proof(rs._json_load(rs.TRENCH_META_PATH, {}))
    board = [{**b, 'proof': proof_.get(b['key'])} for b in rs._trench.meta_board(got, lambda x, cfg: rs._trench.gate(x[0], x[1], x[2], cfg))]
    if meta in rs._trench.METAS:   # 👁 view-only: the finalists judged by that meta
        g = rs._trench.meta_gate(meta)
        view = [{**rs._trench_row(x[0], x[1], x[2], g), 'trenchLevel': meta} for x in got]
        return {'cfg': own, 'view': meta, 'metas': board, 'options': rs._trench.OWN_OPTIONS, 'checked': [{k: v.get(k) for k in keys} for v in view], 'pass': sum(1 for v in view if v['ok']),
                'rows': [], 'floor': rs._fw.clean_cfg(rs._fw_peek().get('cfg') or {})['trenchMinLiqUsd'], 'level': meta, 'seen': rs._trench_cache.get('seen', 0), 'funnel': [], 'at': rs._trench_cache.get('at'),
                'rules': f"≤ {g['maxAgeH']:g}h old · ${g['minMcap'] / 1000:g}K–${g['maxMcap'] / 1000:g}K cap · ≥ {g['minHolders']} holders · ≥ {g['minTxns1h']} trades/h · ≥ ${g['minVol1h'] / 1000:g}K 1h volume · safety checks as always"}
    have_ = {x.get('mint') for x in (rs._trench_cache.get('rows') or [])} | {x.get('mint') for x in (rs._trench_cache.get('checked') or []) if rs._trench.soft_only(x.get('fails'))} | {x.get('mint') for x in (rs._trench_cache.get('fallback') or [])}
    # 👀 never an empty picker: nothing passing and no near-miss → the busiest SAFE fresh coins that only miss soft checks right now
    close_ = [] if have_ else [{**{k: c_.get(k) for k in keys}, 'score': c_.get('score'), 'soft': True, 'fails': fl_} for c_, fl_ in rs._trench.closest(rs._runner_cands, rs._trench.loosest(g if own['mode'] in ('own', 'meta') else None))]
    # 🗑 pickable: the coins that pass — then the NEAR-MISSES (every safety check passed, only crowd / volume / candles missed, and
    # INSIDE the filter's age + cap band) — then, flagged `outside`, safe coins that are NOT in the owner's band, each with the exact
    # number that puts it outside ("6.3h old — filter ≤ 1h"). Never auto-seated; the owner may still pick one.
    strict = own['mode'] in ('own', 'meta')
    def tag(r):
        miss = rs._trench.band_miss(r, g) if strict else []
        return {**r, 'outside': True, 'soft': True, 'fails': miss} if miss else r
    extra = [tag(x) for x in
             [{**{k: r.get(k) for k in keys}, 'score': r.get('trenchScore'), 'soft': True} for r in rs._trench_cache.get('checked') or [] if not r.get('ok') and rs._trench.soft_only(r.get('fails'))]
             + [{**{k: r.get(k) for k in keys}, 'score': r.get('trenchScore'), 'soft': True, 'fails': ['passes the engine scan']} for r in rs._trench_cache.get('fallback') or []] + close_]
    seen_m, extra_u = {r.get('mint') for r in rs._trench_cache.get('rows') or []}, []
    for x in sorted(extra, key=lambda x: bool(x.get('outside'))):
        if x.get('mint') not in seen_m:
            seen_m.add(x.get('mint')); extra_u.append(x)
    # 🚪 OPEN GATES (owner: "make the trench category the open gates"): after the coins that pass and the near-misses, EVERY other
    # launch coin the feed sees, front-runners first, each with what it has not passed. Pickable by hand; never auto-seated.
    for r in (rs._open_board() if rs._open_pairs else []):
        if r.get('mint') not in seen_m:
            seen_m.add(r.get('mint')); extra_u.append({**{k: r.get(k) for k in keys}, 'chg5m': r.get('chg5m'), 'chg1h': r.get('chg1h'), 'score': r.get('front'), 'soft': True, 'open': True, 'fails': r.get('fails'), 'safe': r.get('safe'), 'vol5m': r.get('vol5m'), 'txns1h': r.get('txns1h'), 'logo': r.get('logo')})   # the scan result travels (the ⚡ Rush board read every open coin as unscanned)
    return {'cfg': own, 'metas': board, 'options': rs._trench.OWN_OPTIONS, 'checked': [{k: r.get(k) for k in keys} for r in rs._trench_cache.get('checked') or []], 'pass': len(rs._trench_cache.get('rows') or []),
            'inBand': sum(1 for r in rs._runner_cands if not rs._trench.band_miss(r, g)), 'nearMiss': sum(1 for x in extra_u if not x.get('outside')),
            'rows': [{**{k: r.get(k) for k in keys}, 'score': r.get('trenchScore'), 'trench': True} for r in rs._trench_cache.get('rows') or []] + extra_u,
            'floor': rs._fw.clean_cfg(rs._fw_peek().get('cfg') or {})['trenchMinLiqUsd'], 'level': rs._trench_cache.get('level'),
            'seen': rs._trench_cache.get('seen', 0), 'funnel': rs._trench_cache.get('funnel') or [],
            'at': rs._trench_cache.get('at'), 'rules': f"≤ {g['maxAgeH']:g}h old · broke ${g['minMcap'] / 1000:g}K · ≥ {g['minHolders']} holders · ≥ {g['minTxns1h']} trades/h · "
                                                     f"≥ {g['minBuyShare']:g}% buys · top-10 < {g['maxTop10']:g}% · dev < {g['maxDev']:g}% · creator not suspect / high · mint + freeze revoked"}


def _trench_row(r, holders, auth, cfg=None):
    rs = _rs()
    ok, fails = rs._trench.gate(r, holders, auth, cfg)
    sc, parts = rs._trench.score(r, holders)
    return {'mint': r['mint'], 'pairAddress': r.get('pairAddress'), 'symbol': r.get('symbol'), 'price': r.get('price'), 'liq': r.get('liq'),
            'ageH': r.get('ageH'), 'mcap': r.get('mcap'), 'vol1h': r.get('vol1h'), 'buyShare': r.get('buyShare'), 'holders': holders,
            'score': max(60.0, sc), 'trenchScore': sc, 'trenchWhy': parts, 'fails': fails, 'ok': ok, 'trenchOnly': True, 'division': 'trench'}


def _real_weather():
    """🌦 Runner weather for the real card, from the sim brain's last run (pg_sim.json)."""
    rs = _rs()
    return rs._prime.weather(rs._json_load(rs.PG_SIM_PATH, {}))


def _prime_cool_candidates(rows, cooling_mints, minimum, strict=False):
    """Keep recently exited mints out. Real money is strict: a thin candidate
    set may leave a slot in cash, but must never bypass its stop cooldown and
    immediately rebuy the same loser. Paper keeps the historical fallback."""
    fresh = [x for x in rows if x.get('mint') not in cooling_mints]
    return fresh if strict or len(fresh) >= minimum else rows


async def _prime_candidates():
    """Pools: the deepest busy pools from the Fuse gene pool. Runners: pre-bond coins passing every runner gate, best first."""
    rs = _rs()
    metas = await rs._fuse_candidates()
    pools = sorted(({'mint': m.get('baseAddress'), 'pairAddress': pa, 'symbol': m.get('symbol'), 'price': m.get('priceUsd'),
                     'liquidityUsd': m.get('liquidityUsd'), 'volume24h': m.get('volume24h'), 'rank': min(400.0, rs._fuse._f(m.get('aprEst'))) * rs.math.log10(max(10.0, rs._fuse._f(m.get('liquidityUsd'))))} for pa, m in metas.items()
                    if m.get('baseAddress') and rs._fuse._f(m.get('priceUsd')) > 0 and rs._fuse._f(m.get('liquidityUsd')) >= 100_000), key=lambda x: -x['rank'])
    # 🏁 every coin the site already ranks is a candidate: the Gauntlet's pool divisions (popular · top yield · deepest · new 72h, built
    # from the same feeds as the Lab, Trenches and Pump radar) join the gene pool — from the warm cache, never a new fetch
    seen_p = {x['mint'] for x in pools}
    for dv in ((rs._contenders_cache.get('data') or {}).get('divisions') or []):
        if dv.get('role') != 'pool':
            continue
        for r in dv.get('rows') or []:
            if r.get('mint') and r['mint'] not in seen_p and rs._fuse._f(r.get('liq')) >= 100_000 and rs._fuse._f(r.get('price')) > 0:
                seen_p.add(r['mint'])
                pools.append({'mint': r['mint'], 'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'price': r['price'], 'liquidityUsd': r['liq'],
                              'volume24h': r.get('vol24h'), 'rank': rs._fuse._f(r.get('score')), 'contender': dv['key']})
    live = await rs._runner_live()
    # runners = pre-bond coins passing every gate + CLEAN GRADUATED young coins (<48h, failing ONLY the pre-bond gate)
    young = list(live.get('passing') or []) + [r for r in live.get('dropped') or [] if r.get('gates') == ['Pre-bond (still on the curve)']]
    runners = sorted(({'mint': r['mint'], 'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'price': r.get('price'), 'score': r.get('score'),
                      'vol1h': r.get('vol1h'), 'buyShare': r.get('buyShare'), 'liq': r.get('liq'), 'ageH': r.get('ageH'),
                      'mcap': r.get('mcap'), 'chg1h': r.get('chg1h'), 'chg5m': r.get('chg5m'), 'stage': r.get('stage')} for r in young if rs._fuse._f(r.get('price')) > 0),   # depth travels with the coin (else every runner read $0 and failed the real-buy floor)
                     key=lambda x: -rs._fuse._f(x['score']))
    # 🚀 NEW MAJORS (young coins that arrived big: ≤14d, $800K–$50M, $300K+ volume, $100K+ pool) — the secure growth slot when no
    # runner is safe to buy, so a card is never ONLY old majors
    try:
        if rs.os.environ.get('PYTEST_CURRENT_TEST'):
            raise RuntimeError('tests never fetch live pools')
        have = {r['mint'] for r in runners}
        # a "new major" is DAYS old: Pump's top-by-volume list also carries coins minutes old with a huge seeded pool — those are
        # launch coins and must pass the launch-coin rules (age, the owner's selection), never the big-pool door
        _age_h = lambda r: ((rs.time.time() * 1000 - rs._fuse._f(r.get('createdAt'))) / 3.6e6) if rs._fuse._f(r.get('createdAt')) > 0 else None
        runners += [{'mint': r.get('baseAddress'), 'pairAddress': r.get('pairAddress'), 'symbol': r.get('symbol'), 'price': r.get('priceUsd'), 'score': 60,
                     'liquidity': r.get('liquidityUsd'), 'buyShare': r.get('buyShare'), 'change24h': r.get('change24h'), 'newMajor': (_age_h(r) or 0) >= 24,
                     'ageH': _age_h(r), 'liq': r.get('liquidityUsd'), 'chg1h': r.get('change1h'),
                     'change1h': r.get('change1h'), 'change6h': r.get('change6h'), 'mcap': r.get('mcap'), 'createdAt': r.get('createdAt'), 'volume24h': r.get('volume24h')}
                    for r in (await rs.fuses_discover(lens='risers', chain='solana')).get('pools') or [] if r.get('baseAddress') not in have and rs._fuse._f(r.get('priceUsd')) > 0
                    and not ((_age_h(r) or 0) >= 24 and rs._fuse.solid_major(r))]   # 🪙 a new major must trade like one (fuse.solid_major) — else it is not offered at all   # 🚀 risers + 🟢 Pump's top 15 by volume (same as the Lab lens)
    except Exception as e:
        if not rs.os.environ.get('PYTEST_CURRENT_TEST'):
            print('new majors:', e)
    # ⚓ Anchors: every real major (BTC, ETH, SOL, JUP, PUMP, BONK, WIF, POPCAT, TRUMP, PENGU, …) + big NEW majors, ranked by what
    # they are DOING right now (turnover, 1h/6h/24h moves, buyers, depth) — SOL gets no head start; stables / LSTs never anchor
    nm_rows = [r for r in runners if r.get('newMajor')]
    risers_a = [{'baseAddress': r['mint'], 'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'priceUsd': r.get('price'), 'liquidityUsd': r.get('liquidity'),
                 'mcap': r.get('mcap'), 'createdAt': r.get('createdAt'), 'change1h': r.get('change1h'), 'change6h': r.get('change6h'), 'change24h': r.get('change24h'),
                 'volume24h': r.get('volume24h'), 'buyShare': r.get('buyShare')} for r in nm_rows]
    anchors = [{'mint': r.get('baseAddress'), 'pairAddress': r.get('pairAddress'), 'symbol': r.get('symbol'), 'price': r.get('priceUsd'), 'liquidityUsd': r.get('liquidityUsd'),
                'anchorScore': r.get('anchorScore'), 'anchorWhy': r.get('anchorWhy'), 'volume24h': r.get('volume24h'), **({'newMajor': True} if r.get('newMajor') else {})}
               for r in rs._fuse.rank_anchors(await rs._majors_rows(), risers_a, now_ms=rs.time.time() * 1000)]
    # ARENA-backed coins go first: this round's runner picks, live lit cards, and every coin on a stage / battle card
    rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': []}); rnd = (rd.get('rounds') or [None])[-1] or {}
    arena = {p.get('mint') for p in rnd.get('picks') or []} | {p.get('mint') for c in rd.get('litCards') or [] if not c.get('downAt') for p in c.get('picks') or []}
    arena |= {leg.get(k) for c in (rs._arena_mega_cache.get('data') or []) for leg in c.get('legs') or [] for k in ('pairAddress', 'mint', 'baseAddress')}
    arena |= set(((rs._contenders_cache.get('data') or {}).get('nextUp') or {}))   # 🏁 ⏭ next-up contenders earned an Arena-backed seat
    arena.discard(None)
    # 🏁 every candidate carries the Gauntlet division it ranks in (shown on the card: where each new coin came from)
    div_of = {}
    for dv in ((rs._contenders_cache.get('data') or {}).get('divisions') or []):
        for r in dv.get('rows') or []:
            div_of.setdefault(r.get('mint'), dv['key'])
    for x in pools + runners + anchors:
        if div_of.get(x.get('mint')):
            x['division'] = div_of[x['mint']]
        elif x.get('contender'):
            x['division'] = x['contender']
    for x in pools + runners:
        if x.get('mint') in arena or x.get('pairAddress') in arena:
            x['arena'] = True
    # 🎭 lookalikes are out of every seat: a coin wearing a major's ticker that is not that major (a "SOL" at $0.0004)
    real_ = lambda xs: [x for x in xs if not rs._fw.lookalike(x.get('symbol'), x.get('mint'), rs._fuse.ALL_MAJORS)]
    return real_(pools), real_(runners), anchors


async def _contenders_build(fresh=False):
    """⚡ Never make a viewer wait for the rebuild (it took 0.4–4.4s every time the 30s copy ran out): a copy ≤ 10 min old is answered
    at once and ONE background rebuild starts. No copy yet (cold start) or `fresh` (the warm loop) → build and wait."""
    rs = _rs()
    if rs._contenders_cache.pop('boot', False) and not rs._contenders_cache['data']:   # ⚡ first call after a restart: last league from disk (13s cold)
        snap_ = rs._launchpad_board.launchpad_board_snapshot(rs.CONTENDERS_SNAPSHOT_PATH, 'league', rs.time.time())
        if snap_:
            rs._contenders_cache.update(at=rs.time.time() - max(30.0, snap_[0]), data=snap_[1])
    d_, age = rs._contenders_cache['data'], rs.time.time() - rs._contenders_cache['at']
    if d_ and not fresh and age < rs.CONTENDERS_STALE_SEC:
        if age >= 30 and not rs._contenders_lock.locked():
            rs.asyncio.create_task(rs._contenders_rebuild())
        return d_
    return await rs._contenders_rebuild()


async def _contenders_rebuild():
    """🏁 The Arena qualifier league: every pick list is a division, ranked on live facts; rebuilt at most every 30s (one build at a time)."""
    rs = _rs()
    if rs._contenders_cache['data'] and rs.time.time() - rs._contenders_cache['at'] < 30:
        return rs._contenders_cache['data']
    async with rs._contenders_lock:
        if rs._contenders_cache['data'] and rs.time.time() - rs._contenders_cache['at'] < 30:
            return rs._contenders_cache['data']
        now = rs.time.time()
        pairs, majors, risers, live = await rs.asyncio.gather(rs._fuse_discover_pairs('solana'), rs._majors_rows(), rs.fuses_discover(lens='risers', chain='solana'),
                                                           rs._runner_live(), return_exceptions=True)
        pairs = pairs if isinstance(pairs, list) else []
        live = live if isinstance(live, dict) else {}
        young = list(live.get('passing') or []) + [r for r in live.get('dropped') or [] if r.get('gates') == ['Pre-bond (still on the curve)']]
        src = {'majors': majors if isinstance(majors, list) else [], 'risers': (risers.get('pools') if isinstance(risers, dict) else []) or [],
               'fresh': young, 'proven': young,
               **{k: rs._fuse.discover(pairs, lens, 'solana', now_ms=now * 1000) for k, lens in (('yield', 'yield'), ('deep', 'deep'), ('popular', 'popular'), ('new', 'new'))}}
        # 📉 dip buys + 💳 dex paid read every pool the site already has (popular · new · risers), no extra fetch
        src['dip'] = src['paid'] = (rs._fuse.discover(pairs, 'popular', 'solana', now_ms=now * 1000, limit=120) + src['new'] + src['risers'])
        # 🌊 VOLUME FIRST: every launch coin that passes the SAFETY gates (scan done, holders, dev, creator …) — even when its flow
        # band, size or age keeps it out of the round — busiest first. The list was one coin deep; real volume was being hidden.
        rcfg_v = rs._runner_cfg()
        src['volume'] = sorted({r.get('mint'): r for r in list(young) + [r for r in rs._runner_cands if rs._rn.safe_only(r, rcfg_v)] if r.get('mint')}.values(),
                               key=lambda r: -rs._fuse._f(r.get('vol1h')))
        try:   # ⚡ Pump Pulse on the busiest volume coins: ONE batched call (15s per coin), pulsing coins lead the list
            pz = await rs._edge_pulses([r['mint'] for r in src['volume'][:40]])
            src['volume'] = sorted(({**r, 'pulse': bool((pz.get(r['mint']) or {}).get('pulse'))} for r in src['volume']), key=lambda r: (not r['pulse'], -rs._fuse._f(r.get('vol1h'))))
        except Exception:
            pass
        src['trench'] = list(rs._trench_cache.get('rows') or [])
        # 👀 never an empty Trench list: nothing passing → the scan's closest misses, else the busiest fresh launches (watch only)
        src['trench_watch'] = [{**r, 'trenchOnly': False} for r in (rs._trench_cache.get('checked') or []) if not r.get('ok')] or \
            sorted((r for r in rs._runner_cands if r.get('ageH') is not None and rs._fuse._f(r.get('ageH')) <= 24), key=lambda r: -rs._fuse._f(r.get('vol1h')))[:8]
        cards = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
        on_card = {l.get('mint') for c in cards.values() for l in c.get('legs') or []}
        on_card |= {leg.get(k) for c in (rs._arena_mega_cache.get('data') or []) for leg in c.get('legs') or [] for k in ('mint', 'baseAddress')}
        on_card.discard(None)
        data = {**rs._ct.league(src, on_card, rs._contenders_cache.get('data')), 'at': now, 'weather': rs._real_weather(),
                'all': rs._ct.everyone(src, on_card)}   # 🏁 every ranked coin in one list → the swap picker's Arena lens
        rs._contenders_cache.update(at=now, data=data)
        if data and now - rs._contenders_cache.get('savedAt', 0) >= 60:
            rs._contenders_cache['savedAt'] = now
            try:
                await rs.asyncio.to_thread(rs._launchpad_board.save_board_snapshot, rs.CONTENDERS_SNAPSHOT_PATH, 'league', data, {}, now)
            except Exception:
                pass
        return data


def _creator_state(it):
    """(flagged, rep level) of a scanned coin's creator — the same rule the runner board uses."""
    rs = _rs()
    creator = (it or {}).get('creator')
    if not creator:
        return False, None
    brec = rs._block_load()['wallets'].get(creator)
    flagged = bool((rs._is_blocked(brec) and brec.get('reported')) or (rs._shield_cache.get(creator, (0, {}))[1] or {}).get('verdict') == 'bot')
    try:
        crep = rs._quick_rep(creator).get('level')
    except Exception:
        crep = None
    if rs._is_blocked(brec) and not brec.get('reported') and crep != 'high':
        crep = 'suspect'
    return flagged, crep


async def _pick_verify(mint, pair_address):
    """✅ Verify an owner's pick for a REAL card → (ok, [missing], candidate). Majors / stocks pass. A coin the runner board is
    already tracking is judged on that record (its history catches a dev sale / top-10 spike); any other coin gets a fresh holder
    scan on its own live pool. Nothing known = not verified (fail closed)."""
    rs = _rs()
    if mint in rs._fuse.ALL_MAJORS:
        return True, [], None
    c = next((r for r in rs._runner_cands if r.get('mint') == mint), None)
    if not c or not c.get('scanned'):
        lp = (await rs._fuse_pairs([{'chainId': 'solana', 'pairAddress': pair_address}])).get(pair_address) or {}
        if (lp.get('baseToken') or {}).get('address') != mint:
            return False, ['no live pool reading for this coin right now'], None
        it = await rs._runner_intel(mint, rs._enr.PRIO['LOOK'], 'owner pick', wait=True)
        flagged, crep = rs._creator_state(it)
        c = rs._rn.candidate(lp, it, flagged, False, rs.time.time() * 1000, mayhem=mint in rs._mayhem_mints, creator_rep=crep,
                          hist=rs._runner_track(mint, rs.time.time(), rs._fuse._f(lp.get('curveProgress')), (it or {}).get('top10Pct'), (it or {}).get('devHoldingPct')))
    ok, miss = rs._rn.pick_check(c, rs._runner_cfg())
    return ok, miss, c


def _pick_row(pair, mint, floor=25_000):
    """A live DexScreener pair → a swap-pick row, or None: the pool must be THIS mint, have a live price, ≥ the pick floor (the owner's `pickMinLiqUsd`), and not be a
    dollar coin (it never moves). Real cards additionally need the real-buy floor (checked by the caller)."""
    rs = _rs()
    if not pair or (pair.get('baseToken') or {}).get('address') != mint:
        return None
    m = rs._fuse.leg_meta(pair)
    if m['priceUsd'] <= 0 or m['liquidityUsd'] < max(5_000, floor) or str(m.get('symbol') or '').upper() in rs._ct.STABLES or rs._fw.lookalike(m.get('symbol'), mint, rs._fuse.ALL_MAJORS):
        return None
    return {'mint': mint, 'pairAddress': pair.get('pairAddress'), 'symbol': m.get('symbol'), 'price': m['priceUsd'], 'liq': m['liquidityUsd']}


def _pick_why(pair, mint, floor=25_000):
    """Why `_pick_row` refused, in the owner's words — the real reason with its numbers, never a vague "no live pool"."""
    rs = _rs()
    if not pair or (pair.get('baseToken') or {}).get('address') != mint:
        return 'Could not read that coin\'s pool just now (the price source did not answer for it) — try again in a few seconds.'
    m = rs._fuse.leg_meta(pair)
    sym = m.get('symbol') or 'That coin'
    if m['priceUsd'] <= 0:
        return f"${sym} has no live price yet — it has not traded enough to quote."
    if str(sym).upper() in rs._ct.STABLES:
        return f"${sym} is a dollar coin — it never moves, so it is not a swap-in."
    if rs._fw.lookalike(m.get('symbol'), mint, rs._fuse.ALL_MAJORS):
        return f"${sym} wears a major's ticker but is not that coin (lookalike) — not picked."
    fl = max(5_000, floor)
    kind = 'launch curve' if pair.get('curve') else 'pool'
    return (f"${sym}'s {kind} holds ${m['liquidityUsd']:,.0f} — under your ${fl:,.0f} pick floor. That floor is your own setting: "
            f"Edit Fuse › wallet limits › My own pick min pool (trench coins: Trench min pool). It can go down to $5,000.")


async def _proof_build(force=False):
    """🧾 Fuse proof (fuse_proof.py): the real cards' confirmed swaps with the engine's reason, each real card's verified record, the
    setups side by side, and the 24h real duels (settled + opened here, own file). 30s cache; kept warm by `_fuse_warm`."""
    rs = _rs()
    import fuse_proof as _proof
    now = rs.time.time()
    if not force and rs._proof_cache['data'] and now - rs._proof_cache['at'] < 30:
        return rs._proof_cache['data']
    cards = await rs._prime_view()
    ledger = rs._fw_load().get('ledger') or []
    real = [c for c in cards if c.get('real')]
    recs = [_proof.record(c, ledger, now) for c in real]
    try:
        strat = (await rs.fuse_strategies(hours=rs._fuse._f(((real[0].get('cfgEff') or {}).get('rotateHours')) if real else 0) or 1.0)).get('strategies') or []
    except Exception:
        strat = []
    val = lambda c: rs._fuse._f((c.get('math') or {}).get('nowUsd')) or rs._fuse._f(c.get('valueUsd'))
    key = lambda c: f"prime:{c.get('tpl')}"
    values, labels = {key(c): val(c) for c in cards}, {key(c): c.get('label') for c in cards}
    store = rs._json_load(rs.DUELS_PATH, {})
    st = _proof.duel_step(store, values, labels, [key(c) for c in real], [key(c) for c in sorted((c for c in cards if not c.get('real')), key=lambda c: -rs._fuse._f(c.get('pnlPct')))], now, pick=store.get('pick'))
    st['pick'] = store.get('pick') or {}
    if {k: st.get(k) for k in ('live', 'log', 'rec')} != {k: store.get(k) for k in ('live', 'log', 'rec')}:
        rs._json_save(rs.DUELS_PATH, st)
    data = {'at': now, 'feed': _proof.feed(cards, ledger, now), 'records': recs,
            'setups': _proof.setups(strat, recs, {c.get('tpl'): {k: (c.get('cfgEff') or {}).get(k) for k in rs.PROOF_CFG_KEYS} for c in real}),
            'duels': {**_proof.duel_view(st, values, now), 'real': [key(c) for c in real], 'cards': [{'key': key(c), 'label': c.get('label'), 'real': bool(c.get('real'))} for c in cards]},
            'realLegs': {c.get('tpl'): [{'mint': l.get('mint'), 'pairAddress': l.get('pairAddress'), 'symbol': l.get('symbol')} for l in c.get('legs') or [] if not l.get('buying')] for c in real}}
    rs._proof_cache.update(at=now, data=data)
    return data

