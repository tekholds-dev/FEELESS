"""🧹 Fuse runners — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


def _runner_cfg():
    rs = _rs()
    return rs._rn.clean_cfg(rs._json_load(rs.RUNNERS_PATH, {}).get('cfg') or {})


def _intel_boot():
    """Once per process, BEFORE the first scan request is judged: scan results + the scheduler's freshness book come back from disk."""
    rs = _rs()
    if not rs._fuse_warm_n.get('restored') and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        rs._fuse_warm_n['restored'] = True
        print('intel restored:', rs._intel_restore())


def _intel_fresh(mint, prio=3):
    """The cached scan when it is still fresh for a request of this priority (a complete scan: the TTL — ×4 for a coin nobody is acting
    on; an incomplete one: 60s), else None."""
    rs = _rs()
    hit = rs._intel_cache.get(mint)
    if not hit:
        return None
    if (hit[1] or {}).get('top10Pct') is None:
        return hit[1] if rs.time.time() - hit[0] < 60 else None
    return hit[1] if rs.time.time() - hit[0] < rs._ENRICH.ttl_for(prio) else None


async def _enrich_scan(mint):
    """ONE deep scan, started by the scheduler: every RPC call it makes is tagged with the mint (calls per coin), its outcome goes back
    to the scheduler (fresh · failed · rate-limited) and everyone waiting on it gets the result."""
    rs = _rs()
    out, r429 = None, rs._chain.RPC_STATS['r429']
    tok = rs._chain.RPC_TAG.set(mint)
    try:
        out = await rs.asyncio.wait_for(rs.token_intel('solana', mint), 12)
    except Exception:
        out = None
    finally:
        rs._chain.RPC_TAG.reset(tok)
    ok = bool(out and out.get('top10Pct') is not None)
    now = rs.time.time()
    rs._ENRICH.finished(mint, now, ok, rate_limited=(not ok and rs._chain.RPC_STATS['r429'] > r429))
    if ok:
        rs._intel_failed.pop(mint, None)
    else:
        rs._intel_failed[mint] = now
        if len(rs._intel_failed) > 2000:
            for k in sorted(rs._intel_failed, key=rs._intel_failed.get)[:500]:
                rs._intel_failed.pop(k, None)
    fut = rs._intel_waiters.pop(mint, None)
    if fut is not None and not fut.done():
        fut.set_result(out)
    rs._enrich_pump()


def _enrich_pump():
    """Start whatever the scheduler says is due (priority first, inside the concurrency limit and the call budget) and set ONE timer for
    the next moment something could start. Called on every request and every finished scan — there is no polling loop."""
    rs = _rs()
    if rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return
    now = rs.time.time()
    for m in rs._ENRICH.due(now):
        rs._ENRICH.started(m, now)
        rs.asyncio.ensure_future(rs._enrich_scan(m))
    nxt = rs._ENRICH.next_in(now)
    if nxt is not None and (rs._enrich_timer['h'] is None or rs._enrich_timer['h'].cancelled() or rs._enrich_timer.get('at', 0) <= now):
        try:
            loop = rs.asyncio.get_event_loop()
            rs._enrich_timer['at'] = now + nxt

            def _fire():
                rs._enrich_timer['h'] = None
                rs._enrich_pump()
            rs._enrich_timer['h'] = loop.call_later(nxt, _fire)
        except RuntimeError:
            pass


async def _runner_intel(mint, prio=5, why='board', wait=None):
    """THE one door to a coin's deep scan. Fresh in the cache → that. Otherwise the request joins the scheduler's queue at `prio`
    (trench_kernel.enrich.PRIO: 0 HELD · 1 READY · 2 hunter lane / someone is looking · 3 top CONTENDING · 4 movers · 5 the rest) and:
    a caller with priority ≤ 2 (or `wait=True`) waits for the result (≤ ENRICH_WAIT_SEC); everyone else gets the last known scan (maybe
    stale, maybe None) at once — the result lands in the cache for their next read. A coin whose scan is pending, rate-limited or
    unavailable is never rejected for it."""
    rs = _rs()
    if not mint:
        return None
    rs._intel_boot()
    got = rs._intel_fresh(mint, prio)
    now = rs.time.time()
    if got is not None:   # the cache answers: no scan, no queue (a complete scan also refreshes the scheduler's own book)
        if got.get('top10Pct') is not None:
            rs._ENRICH.note_success(mint, (rs._intel_cache.get(mint) or (0,))[0])
        rs._ENRICH.count['skippedFresh'] += 1
        return got
    st = rs._ENRICH.request(mint, prio, why, now, known=mint in rs._launch_facts)
    stale = (rs._intel_cache.get(mint) or (0, None))[1]
    if st in ('fresh', 'deferred') or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return stale
    fut = rs._intel_waiters.get(mint)
    if fut is None or fut.done():
        fut = rs._intel_waiters[mint] = rs.asyncio.get_event_loop().create_future()
    rs._enrich_pump()
    if not (wait if wait is not None else prio <= 2):
        return stale
    try:
        return await rs.asyncio.wait_for(rs.asyncio.shield(fut), rs.ENRICH_WAIT_SEC)
    except Exception:
        return stale


async def _meme_tick(now):
    """📖 Feed the meme-term learner: names + tickers of today's launchpad coins (trending + new + the live launch stream)
    and the last hour of FEELESS chat. Counts only — nothing here trades."""
    rs = _rs()
    samples = []
    async with rs.httpx.AsyncClient(timeout=10) as http:
        async def get(url, params, key):
            try:
                return (await http.get(url, params=params)).json().get(key) or []
            except Exception:
                return []
        tr, nw, pl = await rs.asyncio.gather(get('http://127.0.0.1:5001/api/market/feed', {'kind': 'trending', 'chain': 'solana', 'page': 1, 'scope': 'launchpads'}, 'pairs'),
                                          get('http://127.0.0.1:5001/api/market/feed', {'kind': 'new', 'chain': 'solana', 'page': 1, 'scope': 'launchpads'}, 'pairs'),
                                          get('http://127.0.0.1:5001/api/pump/pulse', {'limit': 100}, 'launches'))
    for x in tr + nw:
        b = x.get('baseToken') or {}
        if b.get('address'):
            samples.append((f"{b.get('name') or ''} {b.get('symbol') or ''}", 'coin', b['address']))
    for x in pl:
        if x.get('mint'):
            samples.append((f"{x.get('name') or ''} {x.get('symbol') or ''}", 'coin', x['mint']))
    chat = rs._json_load(rs.CHAT_PATH, {})
    rooms = chat.get('rooms', chat) if isinstance(chat, dict) else {}
    for room, msgs in rooms.items():
        for m in (msgs if isinstance(msgs, list) else [])[-200:]:
            ts = (m.get('ts', 0) / (1000 if m.get('ts', 0) > 1e12 else 1)) if isinstance(m, dict) else 0
            if ts and now - ts < 3600 and m.get('text'):
                samples.append((str(m['text'])[:280], 'chat', str(m.get('id') or f"{room}-{ts}")))
    async with rs._admin_lock:
        st = rs._mt.learn(rs._json_load(rs.MEME_PATH, {}), samples, now)
        rs._json_save(rs.MEME_PATH, st)
    return len(samples)


async def _runner_live():
    """Every launchpad coin the feed sees right now (trending + new, pre-bond + graduated), forensics for the busiest,
    gated + scored. 30s cache — the board is shared by every viewer."""
    rs = _rs()
    if rs._runner_live_cache['data'] and rs.time.time() - rs._runner_live_cache['at'] < 40 and not rs._FUSE_FORCE.get():   # warmed every 25s in the background
        return rs._runner_live_cache['data']
    if rs._runner_live_cache.get('busy') and rs._runner_live_cache['data'] and rs.time.time() - rs._runner_live_cache['busy'] < 90:
        return rs._runner_live_cache['data']   # one build at a time: a second caller (the agents' loop, the warm loop) reads the last board
    rs._runner_live_cache['busy'] = rs.time.time()
    try:
        return await rs._runner_live_build()
    finally:
        rs._runner_live_cache['busy'] = 0.0


async def _runner_live_build():
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=10) as http:
        async def feed(kind, page=1):
            try:
                return (await http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': kind, 'chain': 'solana', 'page': page, 'scope': 'launchpads'})).json().get('pairs') or []
            except Exception:
                return []

        async def pulse():   # the live launch stream is the only place mayhem-mode is flagged: remember every one seen
            try:
                return (await http.get('http://127.0.0.1:5001/api/pump/pulse', params={'limit': 100})).json().get('launches') or []
            except Exception:
                return []
        # 🌊 4 pages each (it was 2): the feed now carries Pump's 250 biggest + 200 most recently traded coins
        got, launches = await rs.asyncio.gather(rs.asyncio.gather(*[feed(k, pg) for pg in (1, 2, 3, 4) for k in ('trending', 'new')]), pulse())
    rs._mayhem_mints.update(x['mint'] for x in launches if x.get('mayhem') and x.get('mint'))
    now_ms = rs.time.time() * 1000
    seen, pairs = set(), []
    for p in [x for rows in got for x in rows]:
        m = (p.get('baseToken') or {}).get('address')
        age_ms = now_ms - rs._fuse._f(p.get('pairCreatedAt'))
        old_ok = (age_ms <= rs._rn.OLD_AGE_H * 3.6e6 and rs._fuse._f((p.get('volume') or {}).get('h1')) >= rs._rn.OLD_MIN_VOL1H
                  and rs._fuse._f((p.get('liquidity') or {}).get('usd')) >= rs._rn.OLD_MIN_LIQ)   # 🚀 older runners still trading hard stay on the board
        if m and m not in seen and (age_ms <= rs._rn.MAX_AGE_H * 3.6e6 or old_ok):
            seen.add(m); pairs.append(p)
    rs._open_pairs[:] = [x for rows in got for x in rows]   # 🚪 the open trench list reads EVERY feed pair, whatever its age
    rs._open_meta['at'] = rs.time.time()   # ⏱ when the board's prices / pool depths were read (the LIVE price comes from Jupiter's shared cache)
    busiest = sorted(pairs, key=lambda p: -rs._fuse._f((p.get('volume') or {}).get('h1')))[:rs.RUNNER_SCANS]   # warmed in the background (cached scans)
    # 🗑 trench breakouts get a holder scan too (they're rarely among the 40 busiest — the scan never reached them before)
    # 🎛 the OWNER's trench filter first: coins inside their own band (age, cap, trades, volume) are scanned before the engine's
    # band — with "≤ 1h · $10K–$100K" set, none of the scanned coins were ever in that band, so the filter could only read 0
    own_t = rs._trench.clean_own((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('trenchCfg'))
    own_g = rs._trench.own_gate(own_t) if own_t['mode'] in ('own', 'meta') else None
    by_vol = lambda p: -rs._fuse._f((p.get('volume') or {}).get('h1'))
    mine_t = sorted((p for p in pairs if p not in busiest and own_g and rs._trench.market_pair(p, now_ms, own_g)), key=by_vol)[:10]
    busiest += mine_t
    busiest += sorted((p for p in pairs if p not in busiest and rs._trench.market_pair(p, now_ms, rs._trench.widen(len(rs._trench.WIDEN) - 1))), key=by_vol)[:max(4, 10 - len(mine_t))]
    # ⏭ THE TOP OF EVERY CATEGORY LIST is on the board and scanned first: Coming up picks from the top of 🔥 Pump trending / 🌊 Volume /
    # 🚀 Movers / 🆕 New / 🟢 Bottoms, and those coins read "holder scan not done" or "not on the runner board yet" (older than the
    # board's age window). Top 8 a list, ≤ 30 extra scans (launch facts are read once per coin; a re-scan is 4 RPC calls).
    cat_m = {r.get('mint') for rows in rs._lens_rows.values() for r in rows[:60]} | {r.get('baseAddress') for r in (rs._bottom_cache.get('rows') or [])[:60]}   # top 60 a list = what Coming up walks (Jupiter's audit judges the ones our scan can't reach)
    feed_by = {(x.get('baseToken') or {}).get('address'): x for rows in got for x in rows}
    miss_c = [m_c for m_c in cat_m if m_c and m_c not in feed_by and m_c not in seen]
    if miss_c and not rs.os.environ.get('PYTEST_CURRENT_TEST'):   # 📡 a list's top coin the launch feed never carried ("43 not on the runner board yet"):
        try:                                                    # its pair is built from Jupiter's row (same shape) so it is judged like any other
            for m_c, t_c in (await rs._jup_tokens(miss_c[:300])).items():
                pr_c = rs._launchpad_board.jup_pair(t_c)
                if pr_c:
                    feed_by[m_c] = pr_c
        except Exception:
            pass
    for m_c in cat_m:
        if m_c and m_c in feed_by and m_c not in seen:
            seen.add(m_c); pairs.append(feed_by[m_c])
    busiest += [p for p in pairs if (p.get('baseToken') or {}).get('address') in cat_m and p not in busiest][:30]
    # Never block the board on scans: wait ≤6s, the rest keep running and land in the cache for the next refresh.
    tasks = {(p.get('baseToken') or {}).get('address'): rs.asyncio.ensure_future(rs._runner_intel((p.get('baseToken') or {}).get('address'), rs._enr.PRIO['REST'], 'board')) for p in busiest}   # the board ASKS (lowest priority): it gets the last known scan now, the fresh one on a later build
    if tasks:
        await rs.asyncio.wait(list(tasks.values()), timeout=6)
    intel = {m: t.result() for m, t in tasks.items() if t.done() and not t.cancelled() and t.exception() is None}
    try:   # 🧪 every coin gets a holder reading: Jupiter's audit stands in until our own scan lands (one batched read, 3-min cache)
        jlite = await rs._jup_lite([(p.get('baseToken') or {}).get('address') for p in pairs])
    except Exception:
        jlite = {}
    blocks = rs._block_load()['wallets']
    out_pairs = {e['pair'] for e in rs._radar['events'] if e['kind'] == 'snipers-out'}
    cands = []
    smart = rs._smart_buyers(rs.time.time())
    for p in pairs:
        m = (p.get('baseToken') or {}).get('address'); it = intel.get(m) or (rs._intel_cache.get(m) or (0, None))[1]
        if not it or it.get('top10Pct') is None:
            it = rs._ja.lite_intel(jlite.get(m)) or it
        creator = (it or {}).get('creator')
        brec = blocks.get(creator) if creator else None
        # ⛔ hard out: a creator REPORTED for a rug, or a bot. One blocklisted only for sniping OTHER launches is a warning (same as the
        # rug shield) — treated as suspect, so its coin must prove itself on its own numbers (`runners.banger_proof`).
        flagged = bool(creator and ((rs._is_blocked(brec) and brec.get('reported')) or (rs._shield_cache.get(creator, (0, {}))[1] or {}).get('verdict') == 'bot')) \
            or rs._ja.authority_bad(jlite.get(m))   # ⛔ the dev can still mint / freeze

        crep = None
        if creator:
            try:
                crep = rs._quick_rep(creator).get('level')
            except Exception:
                crep = None
            if rs._is_blocked(brec) and not brec.get('reported') and crep != 'high':
                crep = 'suspect'
        hist = rs._runner_track(m, rs.time.time(), rs._fuse._f(p.get('curveProgress')), *((None, None) if (it or {}).get('source') == 'jupiter' else ((it or {}).get('top10Pct'), (it or {}).get('devHoldingPct'))))   # Jupiter's % is another method — never mix it into the spike / dev-sold history
        cands.append(rs._rn.candidate(p, it, flagged, p.get('pairAddress') in out_pairs or m in out_pairs, now_ms, mayhem=m in rs._mayhem_mints, creator_rep=crep,
                                   hist=hist, smart=smart.get(m, 0)))
    # 🔧 auto-widen: a dead board (fewer than 3 passing) loosens the SOFT gates a step (max 3, hard floors); a full board
    # (8+) steps back toward the configured engine. At most one step per 2 minutes; every step is logged with what moved.
    base = rs._runner_cfg(); wz = rs._runner_widen
    eff = rs._rn.widen(base, wz['level'])
    rs._runner_cands[:] = cands   # 🗑 every candidate (not just passing + the top 30 dropped) — the trench scan reads all of them
    data = {**rs._rn.board(cands, eff), 'seen': len(cands), 'at': rs.time.time()}
    if rs.time.time() - wz['at'] >= 120:
        nxt = rs._rn.widen_level(wz['level'], len(data['passing']))
        if nxt != wz['level']:
            wz.update(level=nxt, at=rs.time.time()); wz['log'] = (wz['log'] + [{'at': rs.time.time(), 'level': nxt, 'passing': len(data['passing'])}])[-20:]
            eff = rs._rn.widen(base, nxt)
            data = {**rs._rn.board(cands, eff), 'seen': len(cands), 'at': rs.time.time()}
    if int(rs.time.time()) % 300 < 40:   # ~every 5 min: remember rejected pre-bond coins for gate regret (cheap, capped)
        try:
            async with rs._admin_lock:
                rd_ = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); rd_['dropLog'] = rs._rn.log_drops(rd_.get('dropLog'), data['dropped'], rs.time.time()); rs._json_save(rs.RUNNERS_PATH, rd_)
        except Exception:
            pass
    data['widen'] = {'level': wz['level'], 'max': rs._rn.WIDEN_MAX, 'moved': {k: [base.get(k), eff.get(k)] for k in rs._rn.WIDEN_STEPS if base.get(k) != eff.get(k)}}
    rs._runner_live_cache.update(at=rs.time.time(), data=data)
    return data


def _runner_track(mint, now, curve, top10, dev):
    """Remember this coin's curve / top-10 / dev % and derive: curve speed (pts gained over ~10 min), top-10 jump over 5 min,
    and whether the dev sold (dev % fell ≥1 pt from its recent high)."""
    rs = _rs()
    if not mint:
        return {}
    h = [x for x in rs._runner_hist.get(mint, []) if now - x[0] <= 20 * 60] + [(now, curve, top10, dev)]
    rs._runner_hist[mint] = h[-60:]
    old = [x for x in h if now - x[0] >= 8 * 60]
    speed = round(curve - old[-1][1], 2) if old and curve else None
    t5 = [x[2] for x in h if now - x[0] <= 5 * 60 and x[2] is not None]
    jump = round(t5[-1] - min(t5), 2) if len(t5) >= 2 else 0.0
    devs = [x[3] for x in h if x[3] is not None]
    sold = bool(devs) and max(devs) > 0.5 and devs[-1] < max(devs) - 1
    if len(rs._runner_hist) > 3000:
        for k in [k for k, v in rs._runner_hist.items() if now - v[-1][0] > 20 * 60]:
            rs._runner_hist.pop(k, None)
    return {'curveSpeed': speed, 'top10Jump': jump, 'devSold': sold}


def _smart_buyers(now, window=30 * 60):
    """Smart FEELESS buyers per coin in the last 30 min: wallets with cached trust ≥ 75 or on the elite list (verified buys only)."""
    rs = _rs()
    elites = rs._crowd_cache.get('elites_set') or set()
    out: dict = {}
    for w, rows in rs._json_load(rs.FEELESS_TRADES_PATH, {}).items():
        smart = w in elites or rs._fuse._f(((rs._trust_cache.get(w) or (0, {}))[1] or {}).get('score')) >= 75
        if not smart:
            continue
        for x in rows or []:
            if x.get('side', 'buy') == 'buy' and now - rs._fuse._f(x.get('ts')) <= window and x.get('token'):
                out.setdefault(x['token'], set()).add(w)
    return {m: len(ws) for m, ws in out.items()}


async def _token_prices(mints):
    """Best-liquidity USD price per mint (DexScreener tokens/v1, 30 per call, in parallel)."""
    rs = _rs()
    out = {}
    async with rs.httpx.AsyncClient(timeout=10) as http:
        async def batch(chunk):
            try:
                for p in (await http.get(f"https://api.dexscreener.com/tokens/v1/solana/{','.join(chunk)}")).json() or []:
                    m = (p.get('baseToken') or {}).get('address')
                    liq = rs._fuse._f((p.get('liquidity') or {}).get('usd'))
                    if m and (m not in out or liq > out[m][0]):
                        out[m] = (liq, rs._fuse._f(p.get('priceUsd')))
            except Exception:
                pass
        ms = list(mints)
        await rs.asyncio.gather(*[batch(ms[i:i + 30]) for i in range(0, len(ms), 30)])
    return {m: v[1] for m, v in out.items() if v[1] > 0}


async def _jup_prices(mints, keyed=False, judge=False):
    """🎯 Jupiter's own USD price per mint (price v3 — the price its routes trade at, across every pool), cached 20s. Paper fills
    and values use THIS so paper sees the same price real money gets (a single DexScreener pair can sit 20–40% away on runners).
    🔑 THE KEY BELONGS TO THE MONEY PATH (2026-10-13): reads use the public lane; only `keyed=True` (the keeper's own buy / sell price
    check) may spend the key. Price reads went keyed-first, unpaced, and ate the ~1 request/s the keeper's quotes need: 30 of 55
    skipped agent buys overnight were "Jupiter route unavailable (HTTP 429)"."""
    rs = _rs()
    now = rs.time.time()
    want = [m for m in dict.fromkeys(mints or []) if m]
    out = {m: v for m in want for t, v in [rs._jup_px_cache.get(m, (0, 0))] if now - t < 20 and v > 0}
    miss = [m for m in want if m not in out]
    if miss:
        key = rs.os.environ.get('JUPITER_API_KEY') if keyed else rs._jkeys.read_key(rs.os.environ)
        sources = ([('https://api.jup.ag/price/v3', {'x-api-key': key})] if key else []) + [('https://lite-api.jup.ag/price/v3', {})]   # the money path: the keeper's key; every read: the READ key (jup_keys) else public
        async with rs.httpx.AsyncClient(timeout=6) as http:
            for base, hdr in sources:
                todo = [m for m in miss if m not in out]
                if not todo:
                    break
                for i in range(0, len(todo), 50):   # 🩹 one refused batch never drops the batches after it (it did: 70% of watched coins read "vanished")
                    try:
                        rs._jup_calls['n'] += 1
                        d = (await http.get(base, params={'ids': ','.join(todo[i:i + 50])}, headers=hdr)).json() or {}
                        for m, v in (d.items() if isinstance(d, dict) else ()):
                            px = rs._fuse._f((v or {}).get('usdPrice'))
                            if px > 0:
                                out[m] = px; rs._jup_px_cache[m] = (now, px)
                    except Exception:
                        continue   # this batch only; callers fall back to the pool price when Jupiter has none
    if judge:   # 🩹 a RESULT read (a call / a coin judged later): a coin Jupiter did not price this time is NOT a rug
        out.update(await rs._judge_fill([m for m in want if m not in out], now))
    return out


async def _judge_fill(miss, now):
    """The coins Jupiter did not price, from every other place a live price lives: the chart's own live price (candles service), the
    launch board's last build, then a ≤ 5-min-old Jupiter reading. Only result graders use it — never a stop, a buy or a sale."""
    rs = _rs()
    got = {}
    if not miss:
        return got
    try:
        for i in range(0, len(miss), 60):
            got.update(await rs._live_px(miss[i:i + 60]))
    except Exception:
        pass
    left = {m for m in miss if m not in got}
    if left:
        for p in rs._open_pairs:
            m = (p.get('baseToken') or {}).get('address')
            if m in left and rs._fuse._f(p.get('priceUsd')) > 0:
                got[m] = rs._fuse._f(p['priceUsd']); left.discard(m)
    for m in list(left):
        t, v = rs._jup_px_cache.get(m, (0, 0))
        if v > 0 and now - t <= rs.JUDGE_STALE_SEC:
            got[m] = v
    return got


async def _runner_tick(now=None, force=False):
    """Every 5 min: record prices for every pick of the last 24h (the proof's price paths); every 15 min (or forced): a new
    round — the best runners stay, newcomers fill the rest."""
    rs = _rs()
    now = now or rs.time.time()
    live = await rs._runner_live()
    d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    recent = [r for r in d['rounds'] if now - r['at'] <= 24 * 3600]
    lit_recent = [c for c in d.get('litCards') or [] if now - c['at'] <= 72 * 3600]   # lit cards are tracked for 72h
    watch = {p['mint'] for r in recent for p in r['picks']} | {p['mint'] for c in lit_recent for p in c['picks']}
    px = {r['mint']: r['price'] for r in live['passing'] + live['dropped'] if r.get('price')}
    missing = [m for m in watch if m not in px]
    if missing:
        px.update(await rs._token_prices(missing))
    async with rs._admin_lock:
        d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
        for m in watch:
            if px.get(m):
                d['paths'].setdefault(m, []).append([now, px[m]])
        d['paths'] = {m: pts[-900:] for m, pts in d['paths'].items() if m in watch or pts and now - pts[-1][0] < 26 * 3600}
        last = d['rounds'][-1] if d['rounds'] else None
        cfg = rs._runner_cfg()
        if force or not last or now - last['at'] >= rs._rn.ROUND_SECONDS:
            weights = rs._rn.lane_weights(rs._rn.lane_proofs(d['rounds'], d['paths'], now, cfg))   # self-tuning lanes
            pool_ = rs._rn.apply_filter(live['passing'], d.get('pickFilter'), cfg['roundSize'])   # 🩺 the doctor's pick filter first
            new = rs._rn.next_round(last, pool_, now, size=cfg['roundSize'], rid=rs.uuid.uuid4().hex[:8], weights=weights, cooled=rs._rn.recently_out(d['rounds']))   # 🧊 3-round cool-down
            pf = rs._rn.proof(d['rounds'], d['paths'], now, cfg=cfg)
            d['rounds'] = (d['rounds'] + [new])[-200:]
            if pf['lights'] and new['picks']:   # dealt while lit → it joins the lit-cards list
                d['litCards'] = ((d.get('litCards') or []) + [rs._rn.lit_card(new, pf)])[-30:]
        elif last:
            # Auto-swap: one pick that now FAILS a gate is replaced by the best passing runner (closed on paper, reason kept)
            failing = {x['mint']: x.get('gates') or ['failed a gate'] for x in live['dropped']}
            d['rounds'][-1], _swap = rs._rn.swap_failing(last, live['passing'], failing, d['paths'], now, cfg, cooled=rs._rn.recently_out(d['rounds']))
        # Lit cards stay strong: 2+ strong + 1 weak → the weak coin is swapped for a new runner; fewer than 2 strong → taken down.
        failing = {x['mint']: x.get('gates') or ['failed a gate'] for x in live['dropped']}
        for i, c in enumerate(d.get('litCards') or []):
            if now - c['at'] <= 72 * 3600:
                d['litCards'][i], _ = rs._rn.rebuild_lit(c, d['paths'], live['passing'], failing, now, cfg)
        rs._json_save(rs.RUNNERS_PATH, d)
    return d['rounds'][-1] if d['rounds'] else None


async def _runner_loop():
    """Price paths every 5 min, and wake exactly when the next round is due (the countdown never sits at 00:00)."""
    rs = _rs()
    await rs.asyncio.sleep(60)
    while True:
        try:
            await rs._runner_tick()
        except Exception as e:
            print('runners:', e)
        rounds = rs._json_load(rs.RUNNERS_PATH, {'rounds': []}).get('rounds') or []
        due = (rounds[-1]['at'] + rs._rn.ROUND_SECONDS - rs.time.time()) if rounds else 300
        await rs.asyncio.sleep(max(5.0, min(300.0, due + 2)))

