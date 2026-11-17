"""🧹 The office: candles, market wake, intake, research, warden, office pass — split out of rep_ai.py by scripts/split-module.py (owner 2026-11-17 cleanup); first moved whole out of reputation_service.py.
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


def _deep_bucket(why):
    """Why a coin got a deep review, as one bucket: first look · not rejected last time · news (a material change) · cooldown over."""
    return 'first look' if why == 'never deep-reviewed' else 'not rejected' if why == 'was not rejected' else 'news' if str(why).startswith('changed') else 'cooldown over'


async def _office_candles(want, now, cats=None):
    """📈 The 1-minute candles behind the chart, ONCE per coin per pass: `want` = {mint: pool}. One request per pool that is not cached
    (the candles service on this machine), in parallel; nothing is fetched twice in a pass and no desk fetches for itself.
    → {mint: rows}. Tests never fetch."""
    rs = _rs()
    t0 = rs.time.perf_counter()
    pools = {}
    rs._office['cmeta'] = {}
    for m, pa in (want or {}).items():
        if m and pa:
            pools.setdefault(pa, m)   # a pool asked for twice (two mints / two desks) is still ONE request
    fresh = {pa for pa in pools if now - (rs._office['candles'].get(pa) or (0, None))[0] <= rs.OFFICE_CANDLE_TTL}
    todo = [pa for pa in pools if pa not in fresh]
    stat = {'req': 0, 'cached': len(fresh), 'merged': len([1 for m, pa in (want or {}).items() if m and pa]) - len(pools), 'coins': len(pools), 'dup': len(todo) - len(set(todo))}   # dup = a pool requested twice in one pass: 0 by construction
    if todo and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        # 👁 THE LIVE CHART, not a snapshot: ONE batched call to the candles service for every coin on the desk — the same chart the war
        # room draws (provider history + FEELESS's live 15s ticks); each pool is marked watched, so its newest candle keeps moving
        try:
            async with rs.httpx.AsyncClient(timeout=6) as http:
                r = await http.post('http://127.0.0.1:5099/api/candles/live', json={'chain': 'solana', 'interval': '1m', 'pairs': {pa: pools[pa] for pa in todo}})
                got = (r.json() or {}).get('charts') or {}
                stat['req'] = 1; stat['live'] = len(got); stat['started'] = (r.json() or {}).get('started')
                for pa, d_ in got.items():
                    rows = list(d_.get('candles') or [])[-rs._ci.LOOK - 5:]   # 🧪 kept EXACTLY as served (Tally validates them as fetched)
                    if rows:
                        rs._office['candles'][pa] = (now, rows, {'provider': d_.get('provider'), 'source': d_.get('source'), 'tickCount': d_.get('tickCount'), 'partial': bool(d_.get('partial')), 'fetchedAt': now, 'liveAt': d_.get('liveAt')})
        except Exception as e:
            print('live charts:', e)
        for pa in [pa for pa, v in rs._office['candles'].items() if now - v[0] > 600]:
            rs._office['candles'].pop(pa, None)
    stat['ms'] = round((rs.time.perf_counter() - t0) * 1000, 1)
    if cats is not None:   # 📈 which kind of coin the real candles went to this pass (fresh 0–12h · old · held) + the first 24 requested (the builds)
        first_ = list((want or {}).keys())[:24]
        stat['allocFirst'] = {k_: sum(1 for m_ in first_ if (cats.get(m_) or 'held') == k_) for k_ in ('fresh', 'old', 'held')}
        stat['loaded'] = {k_: sum(1 for m_, pa_ in (want or {}).items() if (cats.get(m_) or 'held') == k_ and (rs._office['candles'].get(pa_) or (0, None))[1]) for k_ in ('fresh', 'old', 'held')}
    rs._office['candleStat'] = stat
    out = {}
    for m, pa in (want or {}).items():
        hit = rs._office['candles'].get(pa)
        last_t = rs._fuse._f(hit[1][-1][0]) if hit and hit[1] and isinstance(hit[1][-1], (list, tuple)) and hit[1][-1] else 0.0
        if hit and hit[1] and now - last_t <= 300:   # a candle set whose last bar is over 5 min old is stale: the tape stands in
            out[m] = hit[1]
            rs._office['cmeta'][m] = (hit[2] if len(hit) > 2 else None) or {}
    return out


def _mkt_view(mint, pair, now=None):
    """⚡ THE shared market state of one coin, composed from the caches every desk already reads (nothing fetched here): Jupiter's live
    price (`_jup_px_cache`, 20s), the 90s trade tape (`_flow_now`), the newest real candles + the chart built from them (`_office`), and the
    board's pool depth (`_open_pairs`, stamped `_open_meta.at`). → {px, pxAt, pxSrc, liq, liqAt, tapeAt, flow, candleAt, chart}"""
    rs = _rs()
    now = now or rs.time.time()
    jt, jp = rs._jup_px_cache.get(mint, (0, 0))
    bp = (next((p_ for p_ in rs._open_pairs if p_.get('pairAddress') == pair), None) or ((rs._intake.get('pairs') or {}).get(mint) if ((rs._intake.get('pairs') or {}).get(mint) or {}).get('pairAddress') == pair else None)) if pair else None
    ft, fw = rs._flow_now.get(pair, (0, None)) if pair else (0, None)
    hit = rs._office['candles'].get(pair) if pair else None
    last_c = rs._fuse._f(hit[1][-1][0]) if hit and hit[1] and isinstance(hit[1][-1], (list, tuple)) else 0.0
    if jp and jp > 0:
        px, at, src = jp, jt, 'jupiter'
    else:
        px, at, src = rs._fuse._f((bp or {}).get('priceUsd')), (rs._open_meta['at'] if bp else 0), 'board'
    return {'px': px or None, 'pxAt': at or None, 'pxSrc': src if px else None, 'liq': rs._fuse._f(((bp or {}).get('liquidity') or {}).get('usd')) or None, 'liqAt': rs._open_meta['at'] if bp else None,
            'tapeAt': ft or None, 'flow': fw, 'candleAt': (last_c / 1000 if last_c > 1e12 else last_c) or None, 'chart': (rs._office.get('charts') or {}).get(mint)}


def _office_vels(cur, px, now):
    """📈 One REAL valuation read per held seat (the tier tick's price, or the fast guard's fresh Jupiter read) → velocity per mint. Memory
    only: after a restart every seat reads UNKNOWN until it has VEL_MIN_N reads — nothing is guessed."""
    rs = _rs()
    vh = rs._office.setdefault('vel', {})
    out, on = {}, set()
    for l in cur.get('legs') or []:
        m, e = l.get('mint'), rs._fuse._f(l.get('entry'))
        if not m or l.get('placeholder') or rs._fuse._f(l.get('units')) <= 0 or e <= 0:
            continue
        on.add(m)
        p_ = rs._fuse._f((px or {}).get(l.get('pairAddress')) or (px or {}).get(m))
        vh[m] = rs._so.vel_note(vh.get(m), now, (p_ / e - 1) * 100 if p_ > 0 else None)
        out[m] = rs._so.velocity(vh[m], now)
    for m in [m for m in vh if m not in on and not (vh[m] and now - rs._fuse._f(vh[m][-1][0]) < 600)]:
        vh.pop(m, None)
    return out


async def _live_px(mints):
    """⚡ The live price the FEELESS charts draw (the candles service's stream price, its shared 5s cache) for many coins in ONE local call."""
    rs = _rs()
    ms = [m for m in dict.fromkeys(mints or []) if m][:60]
    if not ms or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return {}
    try:
        async with rs.httpx.AsyncClient(timeout=rs.LIVE_PX_SEC if len(ms) <= 12 else rs.LIVE_PX_BULK_SEC) as http:
            r = await http.get('http://127.0.0.1:5099/api/candles/prices', params={'mints': ','.join(ms)})
            return {m: rs._fuse._f(v) for m, v in (r.json() or {}).items() if rs._fuse._f(v) > 0}
    except Exception:
        return {}


def _wake_note(kind, sym, why, now):
    rs = _rs()
    rs._wake['log'] = (list(rs._wake['log']) + [{'at': now, 'kind': kind, 'sym': sym, 'why': '; '.join(why[:2])}])[-20:]


async def _market_wake(agents_c, now):
    """⚡ MARKET-EVENT WAKEUPS between office passes: the live chart price for the agents' seats and their waiting candidates → a material
    change wakes Reaper (tier tick on freshly refreshed live candles) or Trigger (an early agents' pass). → True when the tier tick should run now."""
    rs = _rs()
    pos_ = rs._office.get('pos') or {}
    legs_ = [l for c in agents_c for l in c.get('legs') or [] if l.get('mint') in pos_ and not l.get('placeholder')]
    cand_ = rs._office.get('watchC') or {}
    lp = await rs._live_px([l['mint'] for l in legs_] + list(cand_))
    if not lp:
        return False
    try:   # ⚙ every live price is an EVENT for the kernel: the held coin / candidate is re-judged at once (measured: market move → Reaper decision)
        kctx_ = None
        for m_, px_ in lp.items():
            if m_ in rs._tk.KERNEL.store.mints:
                kctx_ = kctx_ or rs._kernel_ctx(rs.time.time())
                d_px_ = rs._tk.KERNEL.price_event(m_, px_, rs.time.time(), kctx_)
                rs._tke.HUB.publish('mint_update', m_, {'mint': m_, 'price': px_, 'priceAt': round(rs.time.time(), 2), 'status': (d_px_ or {}).get('status'), 'reaper': ((d_px_ or {}).get('opinions') or {}).get('reaper')}, rs.time.time())   # 📡 a live price → the page, now
    except Exception as e:
        print('kernel price event:', str(e)[:100])
    tick = False
    for l in legs_:
        m = l['mint']
        why = rs._mw.position_wake(pos_[m], lp.get(m))
        if why and rs._mw.due(rs._wake['pos'].get(m), now, rs._mw.GAP_POS):
            rs._wake['pos'][m] = now; rs._wake['n'] += 1; tick = True
            rs._jup_px_cache[m] = (now, lp[m])   # the tick decides on THIS price (the shared 20s cache could be a candle old)
            pa = l.get('pairAddress')
            if pa and rs._office['candles'].get(pa):   # … and on a re-read live chart (the refresh skips anything younger than its TTL)
                rs._office['candles'][pa] = (0.0,) + tuple(rs._office['candles'][pa][1:])
            rs._wake_note('reaper', l.get('symbol'), why, now)
    hit = [(m, rs._mw.candidate_wake(c, lp.get(m))) for m, c in cand_.items()]
    hit = [(m, w) for m, w in hit if w]
    if hit and rs._mw.due(rs._wake['candAt'], now, rs._mw.GAP_CAND) and now - rs._fuse._f(rs._agents.get('at')) >= rs._mw.GAP_CAND:
        rs._wake['candAt'] = now; rs._wake['candN'] += 1
        rs._agents['wake'] = now   # the agents' loop runs its next pass now (≤ 2s), not at the 55s mark
        for m, w in hit[:3]:
            rs._wake_note('trigger', (cand_.get(m) or {}).get('sym'), w, now)
    return tick


async def _office_candle_refresh(want, now):
    """⚡ Between agent passes: re-read the candles of the coins a decision is about to stand on (held coins + this tick's candidates)
    whose read is older than OFFICE_CANDLE_TTL — the SAME cache, one request per pool, ≤ OFFICE_REFRESH_MAX — and rebuild their shared
    chart; the case row in the agents' table gets the new chart too (a new 1-minute candle never waits for the coin's rediscovery)."""
    rs = _rs()
    stale = {m: pa for m, pa in (want or {}).items() if m and pa and now - (rs._office['candles'].get(pa) or (0, None))[0] > rs.OFFICE_CANDLE_TTL}
    todo = dict(list(stale.items())[:rs.OFFICE_REFRESH_MAX])
    if not todo or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return 0
    try:   # 👁 the LIVE chart for every coin a decision stands on: one batched local call (provider history + live 15s ticks)
        async with rs.httpx.AsyncClient(timeout=4) as http:
            live_ = ((await http.post('http://127.0.0.1:5099/api/candles/live', json={'chain': 'solana', 'interval': '1m', 'pairs': {pa: m for m, pa in todo.items()}})).json() or {}).get('charts') or {}
    except Exception:
        live_ = {}
    got = [(pa, list((live_.get(pa) or {}).get('candles') or [])[-rs._ci.LOOK - 5:], {k_: (live_.get(pa) or {}).get(k_) for k_ in ('provider', 'source', 'tickCount', 'liveAt')} | {'partial': bool((live_.get(pa) or {}).get('partial')), 'fetchedAt': now}) for pa in todo.values()]
    rs._office['load']['candleRefresh'] = int(rs._office['load'].get('candleRefresh') or 0) + len(todo)
    by = {x_.get('mint'): x_ for x_ in rs._agents.get('table') or []}
    n = 0
    for (pa, rows, meta_), m in zip(got, todo):
        if not rows:
            continue
        rs._office['candles'][pa] = (now, rows, meta_)
        x_ = by.get(m) or {}
        nm, vt = x_.get('nums') or {}, x_.get('vitals') or {}
        bp_ = next((p_ for p_ in rs._open_pairs if p_.get('pairAddress') == pa), None) or {}
        meta = {**(meta_ or {}), 'vol5m': ((bp_.get('volume') or {}).get('m5')), 'vol1h': vt.get('vol1h'), 'txns1h': vt.get('txns1h'), 'buy': nm.get('buy'), 'liqAge': 0.0, 'ageMin': None if vt.get('ageH') is None else rs._fuse._f(vt['ageH']) * 60}
        ch = rs._ci.read(rows, now, True, 'candles', meta, buy=nm.get('buy'), liq=nm.get('liq') or None, liq_d=nm.get('liqD'), flow=(rs._flow_now.get(pa) or (0, None))[1])
        rs._office['charts'][m] = ch
        if x_:
            x_['chart'] = rs._ci.compact(ch); x_['chartAt'] = now
        n += 1
    return n


def _intake_reg():
    rs = _rs()
    if rs._intake['reg'] is None:
        rs._intake['reg'] = dict((rs._json_load(rs.INTAKE_PATH, {}) or {}).get('reg') or {})
    return rs._intake['reg']


async def _intake_dex(mints, now):
    """📡 {mint: deepest DexScreener pair} for coins Jupiter's token read did not answer (30 a call, in parallel, cached 45s)."""
    rs = _rs()
    out, need = {}, []
    for m_ in dict.fromkeys(mints):
        hit = rs._intake_ds.get(m_)
        if hit and now - hit[0] < 45:
            if hit[1]:
                out[m_] = hit[1]
        else:
            need.append(m_)
    if need:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            async def one(chunk):
                try:
                    r = await http.get('https://api.dexscreener.com/tokens/v1/solana/' + ','.join(chunk))
                    return r.json() if r.status_code == 200 else []
                except Exception:
                    return []
            rows = [p for got in await rs.asyncio.gather(*[one(need[i:i + 30]) for i in range(0, len(need), 30)]) if isinstance(got, list) for p in got]
        best = rs._in.deepest_pairs(rows, need)
        for m_ in need:
            rs._intake_ds[m_] = (now, best.get(m_))
        out.update(best)
        for m_ in [k for k, v in rs._intake_ds.items() if now - v[0] > 300]:
            rs._intake_ds.pop(m_, None)
    return out


async def _intake_pass(ob, now, owner=()):
    """🕸 Every existing outlet → the registry; rows for the coins the board does not carry → (extra rows, fresh {mint: [pulse|migr]},
    outlets {mint: [calls|feeders|radar|runner]}). One local read of the Pump pulse (PumpPortal live stream, already running) and ONE
    batched Jupiter token read for the missing rows — no new crawler, no RPC."""
    rs = _rs()
    born = lambda r: (now - rs._fuse._f(r['ageH']) * 3600) if r.get('ageH') is not None else None
    seen = {'open': [{'mint': r['mint'], 'symbol': r.get('symbol'), 'born': born(r), 'pad': 'pump' if str(r['mint']).endswith('pump') else 'bonk' if str(r['mint']).endswith('bonk') else None} for r in ob if r.get('mint')]}
    pl = {}
    if not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        try:
            async with rs.httpx.AsyncClient(timeout=3) as http:
                pl = (await http.get('http://127.0.0.1:5001/api/pump/pulse', params={'limit': 100})).json() or {}
        except Exception:
            pl = {}
    seen['pulse'] = [{'mint': l['mint'], 'symbol': l.get('symbol'), 'born': rs._fuse._f(l.get('at')) / 1000 or None, 'pad': 'pump'} for l in pl.get('launches') or [] if l.get('mint')]
    seen['migr'] = [{'mint': m_.get('mint'), 'symbol': m_.get('symbol'), 'pad': 'pump'} for m_ in pl.get('migrations') or [] if m_.get('mint')]
    seen['runner'] = [{'mint': r.get('mint'), 'symbol': r.get('symbol')} for r in rs._runner_cands if r.get('mint')]
    for k_, rows_ in (rs._lens_rows or {}).items():
        seen[f'list:{k_}'] = [{'mint': r.get('mint'), 'symbol': r.get('symbol')} for r in rows_ or [] if r.get('mint')]
    seen['calls'] = [{'mint': c.get('mint'), 'symbol': c.get('symbol')} for c in (rs._pump_calls.get('calls') or []) + ((rs._pump_calls.get('board') or {}).get('coins') or []) if c.get('mint')]
    fb = rs._feeders.get('board') or {}
    seen['feeders'] = [{'mint': m_} for m_ in list((fb.get('runners') or {}).keys()) + list((fb.get('kids') or {}).keys()) if m_]
    p2m = {p.get('pairAddress'): (p.get('baseToken') or {}).get('address') for p in rs._open_pairs}
    seen['radar'] = [{'mint': p2m[pa], 'symbol': sy} for pa, sy in (rs._radar.get('pairs') or {}).items() if p2m.get(pa)]
    seen['held'] = [{'mint': l.get('mint'), 'symbol': l.get('symbol')} for l in rs._prime_cards().get(rs._office.get('tid') or '', {}).get('legs') or [] if l.get('mint') and not l.get('placeholder')]
    reg, new_by, new_all = rs._in.note(rs._intake_reg(), seen, now)
    rs._intake['reg'] = reg
    have = {r['mint'] for r in ob if r.get('mint')}
    fresh, outlets = {}, {}
    for s_ in ('pulse', 'migr'):
        for x in seen[s_]:
            fresh.setdefault(x['mint'], []).append(s_)
    for s_ in ('calls', 'feeders', 'radar', 'runner'):
        for x in seen[s_]:
            outlets.setdefault(x['mint'], []).append(s_)
    want = [m_ for m_ in dict.fromkeys(owner or ()) if m_ not in have] + [m_ for m_ in list(dict.fromkeys(list(fresh) + list(outlets))) if m_ not in have and m_ not in (owner or ())][:rs.INTAKE_JUP]   # 👤 the owner's review coins first (never cut)
    extra = []
    if want and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        miss = [m_ for m_ in want if not (rs._jup_tok_cache.get(m_) and now - rs._fuse._f(rs._jup_tok_cache[m_][0]) < 60)]
        rs._office['load']['jupTokens'] = int(rs._office['load'].get('jupTokens') or 0) + (len(miss) + 99) // 100
        try:
            toks = await rs._jup_tokens(want)
        except Exception:
            toks = {}
        rcfg = rs._runner_cfg()
        for m_, t_ in (toks or {}).items():
            pr = rs._launchpad_board.jup_pair(t_)
            r = rs._trench.open_row(pr, now * 1000) if pr else None
            if not r:
                continue
            r['curve'] = not t_.get('graduatedPool') and (pr.get('dexId') == 'pumpfun' or t_.get('bondingCurve') is not None)   # still on its launch curve
            sc = rs._open_scan_judge(pr, m_, rcfg) or rs._jup_judge(pr, m_, rs._ja.facts(t_), rcfg)   # 🧪 Jupiter's audit stands in until our own scan lands
            r.update({'front': rs._trench.front_score(r), 'safe': None if not sc else bool(sc[0]), 'fails': ['not scanned yet — holders unknown'] if not sc else list(sc[1] or []),
                      'soft': True, 'open': True, 'outlet': True, **({k_: v_ for k_, v_ in (sc[2] or {}).items() if v_ is not None} if sc and len(sc) > 2 else {})})
            extra.append(r)
            if not any((p.get('baseToken') or {}).get('address') == m_ for p in rs._open_pairs[-400:]):
                rs._intake.setdefault('pairs', {})[m_] = pr   # the pair a fill / candle / live check needs (memory only)
        # 📡 Jupiter's read lane at its limit (429) must never starve the desk: the coins it did not answer → DexScreener (own quota)
        got_ = {r['mint'] for r in extra}
        try:
            dex_ = await rs._intake_dex([m_ for m_ in want if m_ not in got_], now)
        except Exception:
            dex_ = {}
        for m_, pr in dex_.items():
            r = rs._trench.open_row(pr, now * 1000)
            if not r:
                continue
            r['curve'] = pr.get('dexId') == 'pumpfun'
            sc = rs._open_scan_judge(pr, m_, rcfg)
            r.update({'front': rs._trench.front_score(r), 'safe': None if not sc else bool(sc[0]), 'fails': ['not scanned yet — holders unknown'] if not sc else list(sc[1] or []),
                      'soft': True, 'open': True, 'outlet': True, 'via': 'dex', **({k_: v_ for k_, v_ in (sc[2] or {}).items() if v_ is not None} if sc and len(sc) > 2 else {})})
            extra.append(r)
            if not any((p.get('baseToken') or {}).get('address') == m_ for p in rs._open_pairs[-400:]):
                rs._intake.setdefault('pairs', {})[m_] = pr
    rs._intake['last'] = {'at': now, 'newBy': {k_: len(v_) for k_, v_ in new_by.items()}, 'new': len(new_all), 'newMints': new_all[:40], 'want': len(want), 'rows': len(extra),
                       'rowsDex': sum(1 for r in extra if r.get('via') == 'dex'),
                       'pending': len(want) - len(extra), 'pulseStatus': pl.get('status'), 'pulsePerMin': (pl.get('launchesPerMinute') or [None])[-2] if pl.get('launchesPerMinute') else None,
                       'seen': rs._in.cycle(reg, seen, new_by, new_all, [], [], now)['uniqueSeen']}
    return extra, fresh, outlets


def _intake_after(table, cases, now):
    """The office stamps of this pass (agent intake · deep review · cleared) + the cycle's turnover, then the registry is saved."""
    rs = _rs()
    reg = rs._intake_reg()
    tm = [x_.get('mint') for x_ in table if x_.get('mint')]
    reg = rs._in.stamp(reg, 'intake', tm, now)
    reg = rs._in.stamp(reg, 'deep', rs._office.get('deepNow') or [], now)
    reg = rs._in.stamp(reg, 'clear', [c_['mint'] for c_ in cases if c_.get('cleared')], now)
    rs._intake['reg'] = reg
    last = rs._intake.get('last') or {}
    cy = rs._in.cycle(reg, {}, {k_: [None] * v_ for k_, v_ in (last.get('newBy') or {}).items()}, last.get('newMints') or [], tm, rs._intake.get('prev') or [], now)
    rs._intake['prev'] = tm
    rs._intake['cycle'] = {**cy, 'uniqueSeen': last.get('seen'), 'newUnique': last.get('new'), 'newBy': last.get('newBy') or {}}
    if now - rs._fuse._f(rs._intake.get('saveAt')) >= 50:
        rs._intake['saveAt'] = now
        rs._json_save(rs.INTAKE_PATH, {'reg': reg})
    return rs._intake['cycle']


def _intake_view(now):
    """🕸 The intake panel: this cycle's turnover, every outlet's funnel (seen → promoted → deep → cleared → bought → won / lost, 6h) and
    the latencies source → intake → deep → clear → seat. Context only — no source is ever a gate."""
    rs = _rs()
    reg = rs._intake_reg()
    return {'cycle': rs._intake.get('cycle'), 'last': {k_: v_ for k_, v_ in (rs._intake.get('last') or {}).items() if k_ != 'newMints'}, 'sources': rs._in.per_source(reg, now),
            'labels': {**rs._in.SOURCES, **{f'list:{k_}': rs._in.label(f'list:{k_}') for k_ in (rs._lens_rows or {})}}, 'latency': rs._in.latency(reg, now), 'registry': len(reg),
            'note': 'every outlet is an existing FEELESS stream; a source\'s record is context — every coin still earns its own decision'}


def _office_seat_payload():
    """🪑 The four-seat model for the page (memory only): every seat this cycle, the ranked bench, the summary line, each held / benched
    coin's score parts, every held seat's switch test, the newest cycle lines and the research packets' last job."""
    rs = _rs()
    return {'seatBoard': rs._agents.get('seatBoard'), 'bench': rs._agents.get('bench'), 'seatSummary': rs._agents.get('seatSummary'), 'seatScores': rs._agents.get('seatScores'),
            'switchTests': [{k_: v_ for k_, v_ in (t_ or {}).items() if k_ in ('mint', 'switch', 'why', 'edge', 'need', 'margin', 'scored', 'current', 'challenger', 'lines', 'mode')} for t_ in rs._agents.get('switchTests') or []],
            'cycleLog': [{k_: v_ for k_, v_ in x_.items() if k_ != 'mints'} for x_ in (rs._office.get('cycleLog') or [])[-12:]], 'research': rs._social.get('last'),
            'intakeView': rs._intake_view(rs.time.time()), 'util': rs._agents.get('util'), 'benchStats': rs._agents.get('benchStats'),
            'scoreNote': 'seat score = hand-set weights over measured parts (read · momentum · structure · liquidity · holders · live data · identity · penalties · velocity · thesis) — it RANKS coins that already passed every gate; it is not a learned or proven edge'}


def _office_cycle_log(table, now):
    """🔁 Append this pass's cycle line (counts from this pass's objects only) → `_office['cycleLog']` (≤ CYCLE_LOG_N, newest last)."""
    rs = _rs()
    cy, it = rs._office.get('cycle') or {}, rs._office.get('intake') or {}
    prev = (rs._office.get('cycleLog') or [None])[-1] or {}
    seen = rs._office.get('seen') or {}
    cases = rs._tk.KERNEL.cases(statuses=('READY', 'CONTENDING'))
    top5 = [c_.get('symbol') for c_ in cases[:5]]
    newin = [x_.get('symbol') for x_ in table if 'new' in (x_.get('intake') or []) and x_.get('ageH') is not None and rs._fuse._f(x_['ageH']) <= 1 and x_.get('mint') not in set(prev.get('mints') or [])]
    reviewed = set(rs._office.get('deepNow') or [])
    dw = rs._office.get('deepWhy') or {}
    repeats = [k_ for k_ in dw if k_ in ('news', 'cooldown over')]   # deep re-reviews of a REJECTED coin: only on news or after the cooldown (never every pass)
    rs._office['passN'] = int(rs._office.get('passN') or 0) + 1
    cooled = sum(1 for e_ in seen.values() if e_.get('reject') and not rs._oe.review_due(e_, now)[0])
    sb, bench_, summ = rs._agents.get('seatBoard') or [], rs._agents.get('bench') or [], rs._agents.get('seatSummary') or {}
    soc = rs._social.get('last') or {}
    line = {'n': rs._office['passN'], 'at': now, 'deepWhy': dw, 'board': it.get('board'), 'cheap': it.get('screened'), 'unique': len({x_.get('mint') for x_ in table}), 'newLaunches': it.get('newLaunches'),
            'newEntering': newin[:6], 'deep': len(reviewed), 'deepCoins': [((next((x_ for x_ in table if x_.get('mint') == m_), {}) or {}).get('symbol')) for m_ in list(reviewed)[:6]], 'scans': len((rs._office.get('scans') or {}).get('asked') or []) if rs._fuse._f((rs._office.get('scans') or {}).get('at')) >= now - 5 else 0,
            'social': None if not soc or rs._fuse._f(soc.get('at')) < rs._fuse._f(prev.get('at')) else len(soc.get('coins') or []), 'socialCoins': [c_.get('symbol') for c_ in soc.get('coins') or []][:4] if soc and rs._fuse._f(soc.get('at')) >= rs._fuse._f(prev.get('at')) else [],
            'cases': cy.get('cases'), 'cleared': cy.get('cleared'), 'occupancy': summ.get('occupancy'), 'target': summ.get('target'), 'bench': summ.get('bench'), 'benchReady': summ.get('benchReady'),
            'best': None if not bench_ else {'symbol': bench_[0].get('symbol'), 'score': bench_[0].get('score'), 'ready': bench_[0].get('ready'), 'block': bench_[0].get('block')},
            'seats': [{'symbol': x_.get('symbol'), 'result': x_.get('result'), 'vel': x_.get('vel'), 'pct': x_.get('pct')} if not x_.get('empty') else {'empty': True, 'code': x_.get('code'), 'next': (x_.get('next') or {}).get('symbol')} for x_ in sb],
            'top5': top5, 'top5Changed': None if not prev.get('top5') else len(set(top5) - set(prev.get('top5') or [])), 'repeats': sum(dw[k_] for k_ in repeats), 'cooled': cooled,
            'fresh': rs._office_fresh(now), 'buysLeft': summ.get('buysLeft'), 'mints': [x_.get('mint') for x_ in table],
            'intake': {k_: v_ for k_, v_ in (rs._intake.get('cycle') or {}).items()}, 'pulseNew': ((rs._intake.get('last') or {}).get('newBy') or {}).get('pulse'),
            'outletRows': (rs._office.get('intake') or {}).get('outletRows'), 'util': (rs._agents.get('util') or {}).get('all')}
    rs._office['cycleLog'] = (list(rs._office.get('cycleLog') or []) + [line])[-rs.CYCLE_LOG_N:]
    return line


def _office_fresh(now):
    """⏱ The six ages, separately, for the coins decisions stand on (held coins + this tick's live-checked candidates)."""
    rs = _rs()
    tid = rs._office.get('tid')
    legs = [l for l in rs._prime_cards().get(tid or '', {}).get('legs') or [] if l.get('mint') and not l.get('placeholder')]
    cands = [x_ for x_ in (rs._agents.get('table') or [])[:12]]
    hv = [rs._mkt_view(l.get('mint'), l.get('pairAddress'), now) for l in legs]
    views = hv + [rs._mkt_view(x_.get('mint'), x_.get('pair'), now) for x_ in cands]
    f = rs._oe.freshness(now, [v_['pxAt'] for v_ in views], [v_['tapeAt'] for v_ in (hv or views)], [v_['candleAt'] for v_ in views], rs._open_meta.get('at'), rs._agents.get('passAt'), rs._office.get('tickAt'))
    # the OLDEST held-seat input (the number a decision must not stand on if it is stale), alongside the newest of anything
    old_ = lambda ts: None if not [t for t in ts if t] else round(max(0.0, now - min(rs._fuse._f(t) for t in ts if t)), 1)
    f['held'] = {'price': old_([v_['pxAt'] for v_ in hv]), 'tape': old_([v_['tapeAt'] for v_ in hv]), 'candle': old_([v_['candleAt'] for v_ in hv]), 'n': len(hv)} if hv else None
    return f


def _office_load_pass():
    """Expensive calls since the last agent pass (deltas of process counters): candle reads, holder scans asked, Jupiter price requests,
    browser research fetches."""
    rs = _rs()
    cur = {'candles': int(rs._office['candleStat'].get('req') or 0) + int(rs._office['load'].get('candleRefresh') or 0), 'scans': int(rs._office['load'].get('scansAsked') or 0),
           'jupiter': rs._jup_calls['n'], 'browser': int(rs._office['load'].get('browser') or 0), 'scanWakes': int(rs._office['load'].get('scanWakes') or 0)}
    tot = rs._office.setdefault('loadTot', {'candles': 0})
    tot['candles'] = int(tot.get('candles') or 0) + int(rs._office['candleStat'].get('req') or 0)
    cur['candles'] = tot['candles'] + int(rs._office['load'].get('candleRefresh') or 0)
    prev = rs._office.get('loadPrev') or {k: 0 for k in cur}
    rs._office['loadPrev'] = cur
    return {k: cur[k] - int(prev.get(k) or 0) for k in cur}


def _social_cache():
    rs = _rs()
    if rs._social['cache'] is None:
        d_ = rs._json_load(rs.SOCIAL_PATH, {}) or {}
        rs._social['cache'] = dict(d_.get('packets') or {}) if d_.get('v') == rs.SOCIAL_V else {}   # an older parser's packets are re-read, never trusted
    return rs._social['cache']


def _social_flush(now=None):
    rs = _rs()
    if not rs._social.get('dirty') or rs._social.get('cache') is None:
        return
    rs._json_save(rs.SOCIAL_PATH, {'v': rs.SOCIAL_V, 'packets': rs._social['cache']}); rs._social['dirty'] = False; rs._social['savedAt'] = rs.time.time() if now is None else now


async def _research_tick(cases, rows_by, now):
    """🔎 ONE research job at a time, after the agent pass: the strongest due candidates (social_research.pick, ≤ PER_PASS) are read
    through local headless Chromium — their own website / X first, one search only when they carry no link. Never blocks the desks."""
    rs = _rs()
    if rs._social['busy'] or rs.os.environ.get('PYTEST_CURRENT_TEST') or not rs._sr.chrome_path():
        return 0
    rs._social['busy'] = True
    n = 0
    try:
        rs._office['load']['orphansKilled'] = int(rs._office['load'].get('orphansKilled') or 0) + await rs.asyncio.to_thread(rs._sr.reap_orphans)   # (off the event loop: its ps call stalled every request up to 5s — Lag catcher 2026-10-30) a browser left by a restart mid-fetch never keeps running
        cache = rs._social_cache()
        done_ = []
        picks_ = rs._sr.pick(cases, cache, now)
        try:   # 🔗 the creator's own links from Pump's coin record FIRST: the desk row often carries none, so coins WITH an X / site were filed "no socials" (2 of 4 checked, 2026-10-13)
            await rs._pump_links_warm([c_['mint'] for c_ in picks_ if str(c_.get('mint') or '').endswith('pump')])
        except Exception:
            pass
        for c_ in picks_:
            row = {**(rows_by.get(c_['mint']) or {}), 'mint': c_['mint'], 'symbol': c_.get('symbol'), 'launch': (c_.get('row') or {}).get('launch')}
            pl_ = (rs._PUMP_LINKS.get(c_['mint']) or (0, {}))[1]
            for k_ in ('site', 'x', 'tg'):
                if not (isinstance(row.get(k_), str) and row[k_].startswith('http')):
                    row[k_] = pl_.get(k_)   # a real link or nothing (the board's True = "set" is not a URL to read)
            try:
                pk, k = await rs._sr.research(row, now=rs.time.time(), cache_search=rs._social['searched'])
            except Exception as e:
                print('research:', e); continue
            n += k
            if pk.get('search') is not None:
                rs._social['searched'][c_['mint']] = now
            cache[c_['mint']] = pk
            done_.append({'symbol': c_.get('symbol'), 'narrative': (pk.get('narrative') or {}).get('class'), 'confidence': (pk.get('cross') or {}).get('confidence'),
                          'conflict': bool((pk.get('cross') or {}).get('conflict')), 'social': pk.get('social'), 'failed': bool(pk.get('failed'))})
        if len(cache) > rs.SOCIAL_KEEP:
            for k_ in sorted(cache, key=lambda k_: rs._fuse._f(cache[k_].get('at')))[:len(cache) - rs.SOCIAL_KEEP]:
                cache.pop(k_, None)
        rs._social['searched'] = {k_: t_ for k_, t_ in rs._social['searched'].items() if now - t_ < rs._sr.TTL['search']}
        rs._office['load']['browser'] = int(rs._office['load'].get('browser') or 0) + n
        rs._office['load']['researched'] = int(rs._office['load'].get('researched') or 0) + 1
        rs._social['last'] = {'at': rs.time.time(), 'requests': n, 'coins': done_}
        rs._social['dirty'] = True
        if now - rs._fuse._f(rs._social.get('savedAt')) >= rs.SOCIAL_SAVE_SEC:   # 💾 ≤ every 2 min (it was every research run)
            rs._social_flush(now)
    finally:
        rs._social['busy'] = False
    return n


def _seat_wake_maybe(now, why=''):
    """🪑 Wake the existing tier tick NOW when Agent Control is on, a seat is open, the office is LIVE, the keeper is healthy, the buy budget
    is not used, and at least one case in the table CLEARS — at most once per SEAT_TARGET_AUTO. No new loop, no new fetch."""
    rs = _rs()
    try:
        rcfg_ = ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {})
        seat_ = rs._agents.get('seat') or {}
        if not (rcfg_.get('agentControl') and seat_.get('empty') and seat_.get('movesLeft') and rs._is_keeper()) or rs.os.environ.get('PYTEST_CURRENT_TEST'):
            return False
        if now - rs._fuse._f(rs._office.get('seatWakeAt')) < rs._oe.SEAT_TARGET_AUTO or (rs._office.get('courier') or {}).get('health') == 'BAD' or rs._oe.policy(rcfg_)['manual'] or not rs._oe.ready(rs._office['boot'], now)['live']:
            return False
        on_ = {x_.get('mint') for x_ in ((rs._agents.get('card') or {}).get('seats') or []) if x_.get('mint')}
        if not rs._tk.KERNEL.ready(n=1, exclude=on_):   # nothing READY in the kernel: no reason to wake a fill
            return False
        rs._office['seatWakeAt'] = now; rs._office['seatWakes'] = int(rs._office.get('seatWakes') or 0) + 1; rs._office['seatWakeWhy'] = why
        rs.asyncio.ensure_future(rs._prime_tick(rs.time.time()))
        return True
    except Exception as e:
        print('seat wake:', e)
        return False


def _office_state():
    """The office's small state, read from disk ONCE per process and kept in memory (the page never causes a read)."""
    rs = _rs()
    if rs._office['state'] is None:
        d = rs._json_load(rs.OFFICE_PATH, {})
        rs._office.update(state=d, pos=dict(d.get('pos') or {}), exiting=list(d.get('exiting') or []), lat={k: list(v) for k, v in (d.get('lat') or {}).items()}, sized=dict(d.get('sized') or {}), theses=dict(d.get('theses') or {}))
    return rs._office['state']


def _office_lat(agent, ms):
    rs = _rs()
    rs._office['lat'][agent] = (list(rs._office['lat'].get(agent) or []) + [round(ms, 3)])[-rs.OFFICE_LAT_N:]


def _office_ledger(n=600):
    """The newest ledger rows (the append-only table, cached by row count — one COUNT per call, no re-read)."""
    rs = _rs()
    try:
        return (rs._fw_full_ledger() or [])[-n:]
    except Exception:
        return []


def _office_real():
    """→ (the real card's id, its wallet book) — read once per agent pass, never per page view."""
    rs = _rs()
    try:
        tid = next((k for k, c in rs._prime_cards().items() if c.get('real')), None)
        return tid, ((rs._fw_load().get('books') or {}).get(tid) or {}) if tid else {}
    except Exception:
        return None, {}


def _office_ctx(cur, t_, now):
    """What the Warden is shown: the card's own money, the candidate's measured numbers, the weather and the courier's health."""
    rs = _rs()
    v, n = t_.get('vitals') or {}, t_.get('nums') or {}
    st = rs._office_state()
    hrs = {int(k): rs._fuse._f(x) for k, x in (st.get('peaks') or {}).items() if now - int(k) * 3600 <= rs._cap.BRAKE_HOURS * 3600}
    money = rs._agents.get('money') or {}
    return {'value': money.get('value'), 'putIn': money.get('putIn'), 'peak': max(hrs.values()) if hrs else None, 'cash': max(0.0, rs._fuse._f(cur.get('cash')) - rs._fuse._f(cur.get('holdCashUsd'))),
            'seats': len(cur.get('legs') or []), 'liq': n.get('liq') or v.get('liq'), 'ageH': v.get('ageH'), 'd5': n.get('d5'), 'top10': v.get('top10'),
            'lastReal': (rs._agents_real().get('last') or [])[-3:], 'weather': rs._agents.get('weather'), 'courier': (rs._office.get('courier') or {}).get('health'),
            'chart': (rs._office.get('charts') or {}).get(t_.get('mint')), 'social': (rs._social_cache() or {}).get(t_.get('mint')), 'near': t_.get('nearReady'), 'tier': t_.get('tier'), 'policy': rs._oe.policy((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}), 'launch': rs._oe.launch_context(t_), 'li': t_.get('li'), 'holderSoft': (t_.get('vitals') or {}).get('holderSoft')}


def _office_warden(cur, t_, requested, cfg_t, now, move):
    """🛡 The Warden sizes ONE existing agent move (a seat fill, or a veto-only look at a switch). A failure here falls back to full
    size — exactly the card's rule as it was — and is printed; it can never return more than `requested`."""
    rs = _rs()
    try:
        t0 = rs.time.perf_counter()
        ctx_ = rs._office_ctx(cur, t_, now)
        ctx_['surv'] = rs._surv.coin(rs._SURV, t_.get('mint'), now)   # ⏱ its own 1 / 5 / 15-min survival → the risk scale
        ctx_['feats'] = rs._FEATS.get(t_.get('mint'))   # 🧪 P1 proven edge: its tags vs the rules that held on unseen coins
        ctx_['edgeRules'] = (rs._json_load(rs.EDGE_AUDIT_PATH, {}) or {}).get('rules') or []
        cap_ = rs._capital_view()
        if cap_.get('on'):   # 💰 size follows the agents' own real record (W23) — this fill's own DOOR once that door has a record, 🧯 the drawdown brake first
            ctx_['capital'] = rs._cap.for_door(cap_, 'armed' if t_.get('armed') else 'ready')
        ctx_['open'] = True   # 🪖 every agent move is a kernel candidate: execution rules as they are, uncertainty only SHRINKS (trench_crew.warden_rules)
        if t_.get('size') is not None:   # the brain's Warden opinion (uncertainty → size) enters the ONE sizing as rule W0
            ctx_.update(kernelSize=t_.get('size'), kernelWhy=t_.get('sizeWhy'))
        if move == 'fill':   # 🪑 multi-seat sizing: how many seats are still open and the free cash they share (W17)
            seats_ = int(rs._fuse._f(rs._oe.policy(cfg_t).get('seats') or cfg_t.get('coins') or 0))
            held_ = len([l for l in cur.get('legs') or [] if not (l.get('placeholder') and not l.get('manualCash'))])
            ctx_.update(openSeats=max(0, seats_ - held_), free=ctx_.get('cash'))
            rs._shadow_cost(now); ctx_.update(rtPct=rs._shadow.get('rt'), feeUsd=rs._shadow.get('feeUsd'))   # 💸 W22: the card's measured round trip
        wd = rs._of.warden(requested, ctx_, rs._office_state(), floor=max(0.05, rs._fuse._f(cfg_t.get('minOrderUsd'))))
        rs._office_lat('warden', (rs.time.perf_counter() - t0) * 1000)
    except Exception as e:
        print('warden:', e)
        return {'veto': False, 'allowed': requested, 'requested': requested, 'eff': 1.0, 'rules': [], 'decided': 'error — the card\'s own size stands'}
    rs._office['warden'] = {**wd, 'sym': t_.get('symbol'), 'mint': t_.get('mint'), 'at': now, 'move': move}
    st = rs._office_state()
    cnt = dict(st.get('count') or {})
    if wd['veto']:
        if now - rs._fuse._f(rs._office['vetoAt'].get(t_.get('mint'))) >= 600:   # one line per coin per 10 min — a veto is re-checked every tick
            rs._office['vetoAt'][t_.get('mint')] = now
            cnt['wardenVeto'] = int(cnt.get('wardenVeto') or 0) + 1
            st['wardenLog'] = (list(st.get('wardenLog') or []) + [{'at': now, 'sym': t_.get('symbol'), 'move': move, 'req': wd['requested'], 'allowed': 0, 'rule': wd['decided'], 'why': min(wd['rules'], key=lambda r: r['mult'])['why']}])[-30:]
            cur.setdefault('events', []).append({'at': now, 'kind': 'agent', 'move': 'veto', 'symbol': t_.get('symbol'), 'why': f"🛡 Warden vetoed ${t_.get('symbol')} ({move}): {min(wd['rules'], key=lambda r: r['mult'])['why']}"})
            rs._tk.KERNEL.note('warden', 'VETO', f"{move}: {min(wd['rules'], key=lambda r: r['mult'])['why']}", now, mint=t_.get('mint'), key=f'veto:{int(now // 600)}')
    else:
        rs._office['sized'][t_.get('mint')] = wd['eff']
        ch_ = (rs._office.get('charts') or {}).get(t_.get('mint'))
        if ch_:   # 🧾 the entry thesis is written the moment the move is allowed — what the structure was and what would prove it wrong
            v_, n_ = t_.get('vitals') or {}, t_.get('nums') or {}
            rs._office['theses'][t_.get('mint')] = rs._ci.thesis(ch_, now, {'liq': n_.get('liq') or v_.get('liq'), 'ageH': v_.get('ageH'), 'courier': (rs._office.get('courier') or {}).get('health')},
                                                           rs._of.tune(st, 'reaper', 'stopPct'), rs._of.take_line(cfg_t, rs._agents.get('scalp')),
                                                           germ_stop_on=rs._oe.clean_policy(cfg_t)['agentGermStop'] == 'on')   # 🦠 the germ stop (owner's switch, on by default)
            fv_ = (rs._office.get('flow') or {}).get(t_.get('mint')) or t_.get('fv')
            rs._office['theses'][t_.get('mint')].update(flow={'state': fv_.get('state'), 'buyPct': fv_.get('buyPct'), 'buyers': fv_.get('buyers')} if fv_ else None,
                                                     distHigh=t_.get('distHigh') if t_.get('distHigh') is not None else ((ch_.get('f') or {}).get('distHigh')),
                                                     germ=rs._ci.germ_word((ch_.get('f') or {}).get('germ')), germDist=((ch_.get('f') or {}).get('germ') or {}).get('dist'),
                                                     germEntry=rs._ci.germ_entry({'germ': rs._ci.germ_word((ch_.get('f') or {}).get('germ')), 'germ5': rs._ci.germ_word((ch_.get('f') or {}).get('germ5'))}),   # 🦠 1m + 5m at the buy   # 🦠 the floor at the buy (rule lab learns it)
                                                     pred=rs._agent_pred(t_, ch_, now),   # 🔮 the agents' own prediction for this trade (real-money memory), graded at the exit
                                                     votes=rs._jr.votes_of((rs._tk.KERNEL.dec.get(t_.get('mint')) or {}).get('opinions')))   # 🗳 each entry desk's OWN vote (judge_review.desk_votes scores it on the real result)
        if move == 'fill':
            rs._tk.KERNEL.note('warden', f"SIZE ${rs._fuse._f(wd['allowed']):.2f}", (min(wd['rules'], key=lambda r: r['mult'])['why'] if wd['rules'] else 'no rule bit — full size'), now, mint=t_.get('mint'),
                            result={'usd': round(rs._fuse._f(wd['allowed']), 4), 'requested': round(rs._fuse._f(wd['requested']), 4)}, key=f"sized:{int(now)}")
            cnt['wardenSized'] = int(cnt.get('wardenSized') or 0) + 1
            st['wardenLog'] = (list(st.get('wardenLog') or []) + [{'at': now, 'sym': t_.get('symbol'), 'move': move, 'req': wd['requested'], 'allowed': wd['allowed'], 'rule': wd['decided'], 'why': (min(wd['rules'], key=lambda r: r['mult'])['why'] if wd['rules'] else 'no rule bit — full size')}])[-30:]
    st['count'] = cnt
    return wd


def _office_reap(cur, px, cfg_t, ctl, now, dec, pol=None, live=True, vels=None, margins=None, buys_left=None, edge=None):
    """☠ Reaper looks at the open positions on the real card each tier tick and adds its exit requests to the agents' own decision
    list. Any failure leaves the list exactly as `agents.manage` returned it."""
    rs = _rs()
    try:
        t0 = rs.time.perf_counter()
        rs._office_state()
        tape, rug, press, fv_ = {}, {}, {}, {}
        for l in cur.get('legs') or []:
            at_, w_ = rs._flow_now.get(l.get('pairAddress')) or (0, None)
            if w_ and now - rs._fuse._f(at_) <= 90:
                tape[l.get('pairAddress')] = rs._flow.tape_read(w_)
                fv_[l.get('pairAddress')] = rs._flow.vital(w_)   # 🌊 the buy / sell vital Reaper reads (R4f / R4c, the tighter stop on a red seat)
                if l.get('mint') and fv_[l.get('pairAddress')]:
                    rs._flow_mark(l.get('mint'), fv_[l.get('pairAddress')], l.get('symbol'), now, held=True)
                if ctl and l.get('mint'):   # 🚨 the rug radar on the SAME tape for the agents' seats (creator / top-holder / bundle wallets dumping)
                    it_ = rs._flow_intel(l.get('mint'))
                    why_ = rs._flow.rug_why(w_, it_.get('creator'), it_.get('watch'), rs._fuse._f(l.get('liqNow')) or rs._fuse._f(l.get('liq')) or None)
                    if not why_:   # 🩸 the pool's SOL leaving fast (replay-proven: 3/14 rugs caught ~27s early, 0/10 winners sold)
                        tr_at_, tr_ = rs._flow_trades.get(l.get('pairAddress')) or (0, None)
                        if tr_ and now - rs._fuse._f(tr_at_) <= 60:
                            why_ = rs._flow.pool_drain(tr_, now, rs._fuse._f(l.get('liqNow')) or rs._fuse._f(l.get('liq')))
                    if why_:
                        rug[l.get('pairAddress')] = why_
                    try:   # 🕵 the launch's early buyers selling on the same tape → exit pressure (Reaper R4e / a tighter trail)
                        m_, _c, _e, pl_, cr_ = rs._li_parts(l.get('mint'))
                        press[l.get('pairAddress')] = rs._li.pressure(w_, m_, pl_, cr_)
                    except Exception:
                        pass
        pos, rep, gone = rs._of.reap(cur.get('legs'), rs._agents.get('table'), px, cfg_t, rs._office['pos'], now, rs._agents.get('scalp'), ctl, rs._agents.get('weather'), tape, rs._office_state(), rs._office['sized'], rs._office.get('charts'), rs._office.get('theses'), pol=pol, live=live, real=bool(cur.get('real')),
                                  vels=vels, margins=margins, rug=rug, press=press, flows=fv_, ai_exit=rs._ai_exit_effects(cfg_t, now), ai_words=rs._ai_exit_words(cfg_t, now), plan=rs._consig_plans(now))
        for g in gone:
            g['take'] = rs._of.take_line(cfg_t, rs._agents.get('scalp'))
            if not g.get('askRule'):   # 🧾 WHO removed it: the newest card event naming this coin (agent pull / swap · model sell · your ✂ · engine) — 63 of 67 sales read "left the card by another rule"
                ev_ = next((e_ for e_ in reversed(cur.get('events') or []) if now - rs._fuse._f(e_.get('at')) < 900 and g.get('sym') and (e_.get('symbol') == g.get('sym') or f"${g.get('sym')}" in str(e_.get('why') or ''))), None)
                if ev_:
                    g['askRule'] = f"left: {ev_.get('kind')} · {str(ev_.get('why') or '')[:90]}"
        by_ = {x_.get('mint'): x_ for x_ in rs._agents.get('table') or []}
        for r_ in rep:   # ⏱ DATA FRESHNESS per seat: nothing is called LIVE on stale inputs
            m_, pa_ = r_.get('mint'), r_.get('pair')
            r_['fresh'] = rs._mw.ages(now, (rs._jup_px_cache.get(m_) or (None,))[0], (rs._flow_now.get(pa_) or (None,))[0], (rs._office['candles'].get(pa_) or (None,))[0],
                                   (by_.get(m_) or {}).get('chartAt') or rs._agents.get('passAt'), now)
            r_['phase'] = rs._mw.market_phase((rs._office.get('charts') or {}).get(m_), (by_.get(m_) or {}).get('li'))
        rs._office.update(pos=pos, reports=rep, gone=list(rs._office.get('gone') or []) + gone)
        rs._chart_widen_note(rep, rs.time.time())   # 🪜 a red seat holding higher lows over its floor: noted as a chart WIDEN read and graded like the models' words
        rs._tape_reaper(rep, now)
        rs._office_lat('reaper', (rs.time.perf_counter() - t0) * 1000)
        return rs._of.merge_reaper(dec, rep, buys_left, edge)
    except Exception as e:
        print('reaper:', e)
        return dec


def _office_chart_view(ch, row=None):
    """The chart-intelligence box for one coin: the state, its evidence and contradictions, the four scores, Trigger's entry call,
    Devil's chart objections, the Warden's chart multiplier and the measured features behind them."""
    rs = _rs()
    if not ch:
        return None
    f = ch.get('f') or {}
    keep = ('px', 'r1', 'r5', 'r10', 'r15', 'r30', 'hh', 'hl', 'lh', 'll', 'lastHigh', 'lastLow', 'slope', 'fit', 'distHigh', 'distLow', 'germ', 'germ5', 'fvg', 'fvg5', 'rangePct', 'pos', 'vol', 'atr', 'body', 'wick', 'upWick', 'loWick', 'seq', 'up', 'down',
            'pullback', 'recovery', 'breakTries', 'breakHeld', 'breakFailed', 'supTests', 'resTests', 'squeeze', 'accel', 'decay', 'extPct', 'volTrend', 'buy', 'imbalance', 'trades', 'liq', 'liqD', 'impact', 'support', 'resistance')
    stop, parts = rs._ci.stop_for(f, ch.get('state'), {'liq': f.get('liq'), 'ageH': ((row or {}).get('vitals') or {}).get('ageH'), 'courier': (rs._office.get('courier') or {}).get('health')}, rs._of.tune(rs._office_state(), 'reaper', 'stopPct'))
    return {'state': ch.get('state'), 'src': ch.get('src'), 'n': ch.get('n'), 'conf': ch.get('conf'), 'ev': ch.get('ev'), 'con': ch.get('con'), 'trend': ch.get('trend'), 'chop': ch.get('chop'), 'mom': ch.get('mom'), 'ext': ch.get('ext'),
            'entry': ch.get('entry'), 'objs': ch.get('objs'), 'risk': ch.get('risk'), 'stop': stop, 'stopParts': parts, 'hardStop': rs._ci.CATASTROPHIC_STOP, 'f': {k: f.get(k) for k in keep},
            'q': rs._md.compact(ch.get('q')), 'qChecks': (ch.get('q') or {}).get('checks')}


def _office_bars(pair, mint=None, n=40):
    """The rows the page draws for one coin — the SAME rows the agents read this pass, with Tally's data-quality verdict on them.
    `src` candles = the candles service's 1-minute bars (v = that bar's own volume figure, None where the bar carries none — never a
    made-up bar); `src` tape = Tally's readings as close-only points: RECONSTRUCTED, drawn as a line, no volume at all. Memory only.
    → {src, rows: [[t, o, h, l, c, v|None]], q, volume} | None"""
    rs = _rs()
    q = rs._md.compact(((rs._office.get('charts') or {}).get(mint) or {}).get('q')) if mint else None
    hit = rs._office['candles'].get(pair)
    if hit and hit[1]:
        rows = []
        for r in hit[1][-n:]:
            try:
                rows.append([int(rs._fuse._f(r[0])), r[1], r[2], r[3], r[4], (r[5] if len(r) > 5 and r[5] is not None and rs._fuse._f(r[5]) > 0 else None)])
            except Exception:
                continue   # a row that cannot even be indexed is not drawn (Tally's verdict already says MALFORMED)
        return {'src': 'candles', 'rows': rows, 'q': q, 'volume': (q or {}).get('volume') or ('PARTIAL' if any(r[5] for r in rows) else 'UNAVAILABLE')}
    ser = ((rs._agents_mem.get().get('series') or {}).get(mint) or []) if mint else []
    rows = rs._ci.from_tape(ser)[-n:]
    return {'src': 'tape', 'rows': [[int(r[0]), r[1], r[2], r[3], r[4], None] for r in rows], 'q': q, 'volume': 'UNAVAILABLE'} if len(rows) >= 2 else None


def _office_positions():
    """Reaper's reports as the page gets them: + the position's own % path since entry and the candles behind its chart."""
    rs = _rs()
    out = []
    led_ = None
    for r in rs._office.get('reports') or []:
        p_ = (rs._office.get('pos') or {}).get(r.get('mint')) or {}
        mk_ = ((rs._tk.KERNEL.store.mints.get(r.get('mint')) or {}).get('market')) or {}
        sup_ = mk_.get('supply')
        if led_ is None:
            led_ = rs._office_ledger(400)
        fills_ = [{'at': rs._fuse._f(x_.get('at')), 'side': x_.get('side'), 'px': rs._fuse._f(x_.get('px')) or None, 'usd': round(rs._fuse._f(x_.get('usd')), 4), 'mc': rs._tks.mc(x_.get('px'), sup_)}
                  for x_ in led_ if x_.get('mint') == r.get('mint') and x_.get('side') in ('buy', 'sell') and rs._of.confirmed(x_) and (not rs._office.get('tid') or x_.get('card') == rs._office.get('tid'))][-6:]
        ent_ = rs._fuse._f(r.get('entry'))
        out.append({**r, 'path': list(p_.get('path') or [])[-40:], 'bars': rs._office_bars(r.get('pair'), r.get('mint')),
                    'supply': sup_, 'supplySrc': mk_.get('supplySrc'), 'mc': rs._tks.mc(r.get('px'), sup_), 'entryMc': rs._tks.mc(ent_, sup_),   # 📊 the chart language: price × supply (None = unavailable)
                    'peakMc': rs._tks.mc(ent_ * (1 + rs._fuse._f(r.get('peak')) / 100), sup_) if r.get('peak') is not None else None, 'fills': fills_,
                    'ghosts': [{'at': g_.get('at'), 'pct': g_.get('pct'), 'rule': str(g_.get('rule') or '').split(' ')[0]} for g_ in (p_.get('study') or []) if isinstance(g_, dict) and g_.get('sell')][-6:]})   # ✂ where the agents WOULD have sold (your picks)
    return out


def _hub_publish(now, light=False):
    """📡 Turn the page's payload into DELTAS on the kernel's hub: each kernel candidate, hunter lane set, position, agent card,
    generation book, execution state and metric block is sent only when its content changed. `light` (a tier tick between passes):
    positions, seats and execution only. Memory only — it reads nothing and never raises into its caller."""
    rs = _rs()
    try:
        p = rs._office.get('payload')
        if not p:
            return
        H = rs._tke.HUB
        rs._tape_flush(now)
        H.sync('position_update', {x_['mint']: {k_: v_ for k_, v_ in x_.items() if k_ not in rs._POS_DROP} for x_ in p.get('positions') or [] if x_.get('mint')}, now)
        H.publish('execution_update', 'office', {'courier': {k_: (rs._office.get('courier') or {}).get(k_) for k_ in ('health', 'why', 'pending', 'sends', 'fills', 'failed', 'landMed')},
                                                 'ready': p.get('ready'), 'seat': p.get('seat'), 'ops': p.get('ops'), 'lastAction': (p.get('mission') or {}).get('lastAction'),
                                                 'seatBoard': p.get('seatBoard'), 'seatSummary': p.get('seatSummary'), 'wake': p.get('wake'), 'armed': rs._office.get('armed'), 'regret': p.get('regret'), 'lab': p.get('lab')}, now)
        if light:
            return
        k = p.get('kernel') or {}
        H.sync('candidate_update', {c_['mint']: {k_: v_ for k_, v_ in c_.items() if k_ not in rs._DELTA_DROP} for c_ in k.get('candidates') or []}, now)
        H.publish('hunter_update', 'lanes', k.get('lanes') or [], now)
        H.sync('agent_update', {a_['key']: {k_: a_.get(k_) for k_ in ('key', 'task', 'decision', 'decisionAt', 'rule', 'card')} for a_ in p.get('agents') or []}, now)
        H.publish('lifecycle_update', 'generations', p.get('generations') or [], now)
        H.publish('metric_update', 'metrics', {'kernel': k.get('metrics'), 'enrich': p.get('enrich'), 'rpc': p.get('rpcStats'), 'stream': H.stats()}, now)
        if p.get('ai'):
            H.publish('ai_update', 'ai', p.get('ai'), now)
        H.publish('snapshot', 'office', {'at': p.get('at')}, now, force=True)
    except Exception as e:
        print('hub:', str(e)[:140])


def _net_stats(now=None):
    """📏 SSE streams (active · connects / disconnects / resyncs and their rate a minute) + RPC (logical · physical · 429 a minute, top
    methods, requests per mint) since the service started — for HQ diagnostics and agent_office_view.json. Memory only."""
    rs = _rs()
    now = rs.time.time() if now is None else now
    mins = max(1 / 60, (now - rs._SSE['since']) / 60)
    r = rs._chain.rpc_metrics(now)
    rm = max(1 / 60, rs._fuse._f(r.get('sinceSec')) / 60) if r else mins
    return {'sse': {**{k: v for k, v in rs._SSE.items() if k != 'since'}, 'subscribers': len(rs._tke.HUB.subs), 'connectsPerMin': round(rs._SSE['connects'] / mins, 3), 'minutes': round(mins, 1)},
            'rpc': {'logicalPerMin': round(rs._fuse._f(r.get('logical')) / rm, 1), 'physicalPerMin': round(rs._fuse._f(r.get('physical')) / rm, 1), 'r429PerMin': round(rs._fuse._f(r.get('r429')) / rm, 1),
                    'topMethods': sorted(((k_, v_.get('physical')) for k_, v_ in (r.get('requestsByMethod') or {}).items()), key=lambda kv: -(kv[1] or 0))[:6],
                    'perMint': r.get('requestsPerMint'), 'minutes': round(rm, 1)}, 'prime': dict(rs._prime_stages)}


def _office_light(tid, cur, now):
    """Between agent passes: the last real agent action (with what the LEDGER says about it), the duty clock and Reaper's positions
    are refreshed on the cached payload. Memory only — no read, no quote, no scan."""
    rs = _rs()
    ev = next((e for e in reversed(cur.get('events') or []) if e.get('kind') == 'agent' and e.get('move') in ('fill', 'swap', 'pull', 'veto')), None)
    last = None
    if ev:
        side = 'sell' if ev.get('move') == 'pull' else 'buy'
        res = {'state': 'vetoed'} if ev.get('move') == 'veto' else rs._of.fill_state(rs._office_ledger(), ev.get('mint'), side, rs._fuse._f(ev.get('at')) - 5, tid, symbol=ev.get('symbol'))
        last = {'at': ev.get('at'), 'move': ev.get('move'), 'sym': ev.get('symbol'), 'usd': ev.get('usd'), 'why': str(ev.get('why') or '')[:160], 'result': res}
    rs._office.update(last=last, dutyAt=rs._fuse._f(cur.get('agentDutyAt')), tid=tid)
    p = rs._office.get('payload')
    if p:
        p['positions'] = rs._office_positions()
        p['mission'] = {**p['mission'], 'lastAction': last}
        p['seat'], p['switchEval'], p['ready'] = rs._agents.get('seat'), rs._agents.get('switchEval'), rs._oe.ready(rs._office['boot'], now)
        p['ops'] = rs._oe.ops(p['ready'], p['seat'], rs._office.get('courier'), rs._is_keeper(), rs._uni.FILL_MOVES_HR)
        p['index'] = (rs._office.get('index') or [])[:80]
        p['rpc'] = {'lanes': rs._rpc_quota_state(), 'note': 'keyed lanes = keeper sends / balances first, then holder scans (budgeted); discovery comes from Pump\'s live stream + the launch boards — no RPC first-seen listener runs'}
        p['wake'] = {'reaper': rs._wake['n'], 'trigger': rs._wake['candN'], 'log': list(rs._wake['log'])[-8:], 'watching': len(rs._office.get('watchC') or {})}   # ⚡ market-event wakeups
        p['flowWait'] = rs._office.get('flowWait')   # 🌊 READY coins the live tape held back this tick (sellers lead / top of a spike)
        p['cycle'] = {**(rs._office.get('cycle') or {}), 'nextIn': max(0, round(rs._fuse._f((rs._office.get('cycle') or {}).get('at')) + rs.AGENTS_EVERY - now)) if rs._office.get('cycle') else None}
        p['seatActions'] = rs._oe.seat_actions(((rs._agents.get('card') or {}).get('seats')), rs._agents.get('decisions'), rs._agents.get('switchEval'), rs._agents.get('seat'))
        p.update(rs._office_seat_payload())
        try:
            p['fresh'] = rs._office_fresh(now); p['live'] = rs._office.get('live'); p['scans'] = rs._office.get('scans')
        except Exception as e:
            print('fresh:', e)
        rs._tape_ledger(now)
        p['tape'] = rs._tk.KERNEL.tape.view()
        rs._hub_publish(now, light=True)   # 📡 positions · seats · the last real action → the delta stream (only what changed)


def _office_pass(st, table, now, rcfg, jp, arch, cour, tid, desk_ms):
    """🏢 Once a pass, after the four desks: exits are confirmed against the ledger, the Archivist files the pass's cases + settles the
    open ones, the Judge runs its shadow tests and scores all ten, and ONE payload is built for the page. Pure compute + two saves."""
    rs = _rs()
    of = rs._office_state()
    perf = st.get('perf') or {}
    for a in ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'chart'):
        if perf.get(a) is not None:
            rs._office_lat(a, rs._fuse._f(perf[a]))
    view = rs._agents.get('view') or {}
    bust_seen = {(x_.get('vitals') or {}).get('read') for x_ in table if any(e_[0] == 'busted_read' for e_ in x_.get('ev') or [])} - {None}
    on = {x.get('mint') for x in ((rs._agents.get('card') or {}).get('seats') or []) if x.get('mint')}
    # 📮→☠ exits: a position that left the card is closed only when the ledger confirms the sale
    t0 = rs.time.perf_counter()
    still, closed = rs._of.confirm_exits(rs._office['exiting'], rs._office.get('gone') or [], rs._office_ledger(), now, tid,
                                      used={(p_.get('exit') or {}).get('sig') for p_ in ((arch or {}).get('positions') or [])[-120:] if p_.get('confirmed')} - {None})
    rs._office.update(exiting=still, gone=[])
    if closed:   # 🔁 every confirmed agent exit at a loss → no re-buy for 6h (any rule) · 🧠 every confirmed result → a real-money lesson
        try:
            of['lostAt'] = rs._oe.note_lost(of.get('lostAt'), closed, now)
            rl_ = rs._json_load(rs.REAL_LEARN_PATH, {})
            for p_ in closed:
                rl_ = rs._rl.note_closed(rl_, p_, now)
            rs._json_save(rs.REAL_LEARN_PATH, rl_); rs._rl_cache['at'] = 0.0
        except Exception as e:
            print('lost / learn:', e)
    if closed:   # 👁 every confirmed exit is watched 30 more minutes: what the coin did AFTER we left is what a wider trail would have kept
        rs._after_mem.put(rs._ap.watch(rs._after_mem.get(), [{**p_, 'closedAt': p_.get('closedAt') or now} for p_ in closed], now), now)
    if not of.get('judgeYoursFix'):   # ✋ once: the Judge's old reviews of YOUR trades stop blaming agent desks
        of['judge'] = rs._jr.mark_yours(of.get('judge'), {(p_.get('mint'), round(rs._fuse._f(p_.get('closedAt')))) for p_ in arch.get('positions') or [] if p_.get('pick')})
        of['judgeYoursFix'] = now
    if not of.get('germBackfill1016'):   # 🦠 once: YOUR past trades get their germ-at-entry from the recorded price ticks of the hour before
        of['germBackfill1016'] = now
        try:
            tk_ = rs._json_load(rs.DATA_DIR / 'candle_ticks.json', {}) or {}
            pair_ = {r_.get('mint'): r_.get('pair') for r_ in rs._fw_full_ledger() if r_.get('side') == 'buy' and r_.get('mint') and r_.get('pair')}
            for p_ in arch.get('positions') or []:
                if p_.get('pick') and ((p_.get('snaps') or {}).get('entry') or {}).get('germ') is None and pair_.get(p_.get('mint')) and p_.get('since'):
                    g_ = rs._co.germ_at(tk_.get(f"solana:{pair_[p_['mint']]}"), rs._fuse._f(p_['since']))
                    if g_ is not None:   # kept BESIDE the hash-chained records (editing a filed record would read as a rewrite)
                        arch.setdefault('germFill', {})[f"{p_['mint']}:{round(rs._fuse._f(p_['since']))}"] = g_
        except Exception as e_:
            print('germ backfill:', str(e_)[:100])
    for p_ in closed:
        arch = rs._of.file_position(arch, {**p_, 'closedAt': p_.get('closedAt') or now}, now)
        rs._tk.KERNEL.note('archivist', 'FILED', f"{'confirmed' if p_.get('confirmed') else 'UNCONFIRMED'} exit" + (f" {rs._fuse._f(p_.get('pct')):+.1f}%" if p_.get('pct') is not None else '') + (f" · {p_.get('askRule')}" if p_.get('askRule') else ''),
                        now, mint=p_.get('mint'), result={'pct': p_.get('pct')}, key=f"filed:{p_.get('leftAt') or int(now)}")
        if p_.get('confirmed'):   # 👨‍⚖️ every confirmed exit gets the Judge's review (root cause · desk · severity · change · confidence)
            try:
                of['judge'] = rs._jr.note(of.get('judge'), arch['positions'][-1], now)
                rv_ = (((of.get('judge') or {}).get('reviews')) or [{}])[-1]
                rs._tk.KERNEL.note('judge', 'REVIEW', f"{rv_.get('kind') or 'exit'}: {rv_.get('cause') or '—'}" + (f" → {rv_.get('resp')}" if rv_.get('resp') else ''), now, mint=p_.get('mint'),
                                result={'pct': p_.get('pct')}, key=f"review:{p_.get('leftAt') or int(now)}")
            except Exception as e:
                print('judge review:', e)
        if p_.get('confirmed') and p_.get('mint'):   # 🕸 how this coin's real seat ended → its outlets' win / loss record (context, never a gate)
            rs._intake['reg'] = rs._in.outcome(rs._intake_reg(), p_['mint'], rs._fuse._f(p_.get('realPct') if p_.get('realPct') is not None else p_.get('pct')), now,
                                         (rs._fuse._f(p_.get('closedAt') or now) - rs._fuse._f(p_.get('since'))) / 60 if p_.get('since') else None,
                                         (p_.get('launch') or {}).get('ageH'), (p_.get('li') or {}).get('mcap'))
    if not (of.get('judge') or {}).get('reviews'):   # first run: the Judge reviews the positions already on file (once)
        for p_ in [x for x in (arch.get('positions') or []) if x.get('confirmed')][-40:]:
            of['judge'] = rs._jr.note(of.get('judge'), p_, now)
    rs._office['court'] = rs._jr.court(of.get('judge'), now)
    if closed:   # 🪑 an exit was confirmed: the empty seat looks for its replacement now (the bench), not a pass later
        rs._seat_wake_maybe(now, 'exit confirmed')
    # 🗄 the pass's case files (strongest first) + every real agent action since the last pass
    wx = st.get('weather') or {}
    ctx0 = {'weather': wx, 'courier': cour}
    cases = rs._tk.KERNEL.cases(exclude=on, top=8, statuses=('READY', 'CONTENDING'))   # ⚙ the kernel's own candidates — the Archivist files what the KERNEL decided
    for c_ in cases:
        arch = rs._of.file_case(arch, rs._tkv.lineage(c_, {**ctx0, 'evidence': rs._of.evidence_refs(c_['row'].get('social'))}), now)
    seen = rs._fuse._f(of.get('actionSeen'))
    wd = rs._office.get('warden')
    by_m = {x['mint']: x for x in table}
    for e in [e for e in rs._prime_cards().get(tid or '', {}).get('events') or [] if e.get('kind') == 'agent' and e.get('move') in ('fill', 'swap', 'pull', 'veto') and rs._fuse._f(e.get('at')) > seen]:
        x_ = by_m.get(e.get('mint')) or next((x for x in table if x.get('symbol') == e.get('symbol')), None)
        full = rs._tk.KERNEL.case(x_['mint']) if x_ else None
        d_ = rs._tkv.lineage(full, {**ctx0, 'warden': wd if wd and wd.get('mint') == (x_ or {}).get('mint') else None, 'evidence': rs._of.evidence_refs(full['row'].get('social'))}, e.get('move')) if full else {'mint': e.get('mint'), 'sym': e.get('symbol'), 'action': e.get('move'), 'px': None}
        arch = rs._of.file_case(arch, {**d_, 'usd': e.get('usd'), 'eventAt': e.get('at'), 'why': str(e.get('why') or '')[:140]}, now)
        of['actionSeen'] = max(rs._fuse._f(of.get('actionSeen')), rs._fuse._f(e.get('at')))
    if jp:
        arch = rs._of.settle_cases(arch, lambda m: (jp or {}).get(m), now)
    rs._office_lat('archivist', (rs.time.perf_counter() - t0) * 1000)
    # 👨‍⚖️ shadow tests → promotion / rejection, then every agent's scorecard
    t0 = rs.time.perf_counter()
    ask_ = rs._coach.pop('tuneAsk', None)
    if ask_ and now - rs._fuse._f(ask_.get('at')) < 1800:   # 🧠 the model coach's notch → a shadow candidate (or refused, with the reason on the tape)
        n_full_ = sum(1 for p_ in arch.get('positions') or [] if p_.get('confirmed') and rs._ap.full(p_, (rs._after_mem.get() or {}).get('done')))
        of, no_ = rs._of.model_candidate(of, ask_.get('key'), ask_.get('dir'), n_full_, ask_.get('why'), now)
        rs._tk.KERNEL.note('judge', 'AI TUNE', f"🧠 asks Reaper {ask_.get('key')} {ask_.get('dir')}: {ask_.get('why') or ''} → " + (f'refused ({no_})' if no_ else 'in shadow — the next 20 exits decide'), now, key=f"aitune:{int(now // 600)}")
        rs._coach['tuneSaid'] = {'at': now, **{k_: ask_.get(k_) for k_ in ('key', 'dir', 'why')}, 'refused': no_}
    ha_ = rs._of.hold_ask((rs._study.get('holds') or {}).get('early'))
    if ha_ and now - rs._fuse._f(of.get('holdAskAt')) > 6 * 3600:   # 🎓 your holds: a trail rule that kept selling you early asks for one notch more room (shadow only)
        of['holdAskAt'] = now
        n_full_h = sum(1 for p_ in arch.get('positions') or [] if p_.get('confirmed') and rs._ap.full(p_, (rs._after_mem.get() or {}).get('done')))
        of, no_h = rs._of.model_candidate(of, 'giveBackPct', 'up', n_full_h, f"the owner held past {ha_[0]} {ha_[1]}× and ended ≥ 5 pts higher", now)
        rs._tk.KERNEL.note('judge', 'HOLD TUNE', f"🎓 {ha_[0]} sold the owner early {ha_[1]}× → " + (f'refused ({no_h})' if no_h else 'one notch more give-back in shadow — the next 20 exits decide'), now, key=f"holdtune:{int(now // 3600)}")
    mt_ = rs._seat.models_trail((rs._g4_mem.get() or {}).get('log'), now)
    if mt_ is not None and now - rs._fuse._f(of.get('modelTrailAt')) > 6 * 3600 and abs(mt_ - rs._of.tune(of, 'reaper', 'giveBackPct')) >= 5:   # 🧠 the agents learn their trail from OSSY / G4 (shadow only)
        of['modelTrailAt'] = now
        n_full_m = sum(1 for p_ in arch.get('positions') or [] if p_.get('confirmed') and rs._ap.full(p_, (rs._after_mem.get() or {}).get('done')))
        dir_m = 'up' if mt_ > rs._of.tune(of, 'reaper', 'giveBackPct') else 'down'
        of, no_m = rs._of.model_candidate(of, 'giveBackPct', dir_m, n_full_m, f"OSSY / G4 run their trades on a {mt_:g}% give-back", now)
        rs._tk.KERNEL.note('judge', 'LEARN', f"🧠 the models trail at {mt_:g}% → Reaper giveBackPct {dir_m}: " + (f'refused ({no_m})' if no_m else 'one notch in shadow — the next 20 exits decide'), now, key=f"mtrail:{int(now // 3600)}")
    ps_ = arch.get('positions') or []
    rfp_ = (len(ps_), (ps_[-1].get('h') if ps_ else None), len((rs._after_mem.get() or {}).get('done') or {}), rs.json.dumps(rs._of.tunes(of, 'reaper'), sort_keys=True),
            sum(1 for c_ in (of.get('candidates') or {}).values() if c_.get('status') == 'shadow'))
    if rs._office.get('trailFp') != rfp_ or now - rs._fuse._f(rs._office.get('trailAt')) > 600 or not rs._office.get('trail'):   # ⚡ the replays only when an exit / after-path / tune changed (they cost ~10s a window every pass)
        of = rs._of.judge_candidates(of, arch, rcfg, st.get('scalp'), now, after=(rs._after_mem.get() or {}).get('done') or {})   # 👁 on WHOLE moves: a path ending at our own sale can only favour a tighter trail
        rs._office['trail'] = rs._trail_view(of, arch, rcfg, st.get('scalp'))
        rs._office['trailFp'], rs._office['trailAt'] = rfp_, now
    ser = st.get('series') or {}
    stale = sum(1 for x in table if len(ser.get(x['mint']) or []) >= 2 and rs._fuse._f(ser[x['mint']][-1]['t']) - rs._fuse._f(ser[x['mint']][-2]['t']) > rs._of.STALE_SEC)
    viol = {k: dict(v) for k, v in (of.get('viol') or {}).items()}
    for a_ in ('tally', 'courier', 'archivist', 'reaper'):
        viol.setdefault(a_, {})
    viol['tally']['stale'] = int(viol['tally'].get('stale') or 0) + stale
    viol.setdefault('courier', {})['rule'] = int(cour.get('duplicates') or 0) + int(cour.get('unsigned') or 0)
    viol.setdefault('archivist', {})['rule'] = rs._arch_verify(arch)
    viol.setdefault('reaper', {})['rule'] = sum(1 for p_ in arch.get('positions') or [] if p_.get('confirmed') and not (p_.get('exit') or {}).get('sig'))
    money = rs._agents.get('money') or {}
    if money.get('value') is not None:
        pk = {k: v for k, v in (of.get('peaks') or {}).items() if now - int(k) * 3600 <= 90000}
        pk[str(int(now // 3600))] = max(rs._fuse._f(pk.get(str(int(now // 3600)))), rs._fuse._f(money['value']))
        of['peaks'] = pk
    if wx.get('regime') and (not of.get('weatherLog') or of['weatherLog'][-1]['regime'] != wx['regime']):
        of['weatherLog'] = (list(of.get('weatherLog') or []) + [{'at': now, 'regime': wx['regime'], 'why': (wx.get('why') or [''])[0]}])[-40:]
    rs._office['theses'] = {m: v for m, v in rs._office['theses'].items() if m in rs._office['pos'] or m in on or now - rs._fuse._f(v.get('at')) < 900}
    of.update(viol=viol, lat=rs._office['lat'], pos=rs._office['pos'], exiting=rs._office['exiting'], sized={m: v for m, v in rs._office['sized'].items() if m in rs._office['pos'] or m in on}, theses=rs._office['theses'])
    try:   # 🔎 the winners we missed: an autopsy for every coin the board watched for an hour that ran and that the card did not hold —
        # from files already on disk (the brain's settled watch list, the case files, Tally's tape). Paper only: nothing here can trade.
        arch, new_m = rs._oe.missed_winners(arch, [d_ for d_ in (rs._json_load(rs.BRAIN_PATH, {}).get('done') or [])[-600:] if rs._fuse._f(d_.get('at')) > rs._fuse._f(of.get('missedAt'))], ser, now, on, rs._fuse._f(of.get('missedAt')), st.get('first'))
        of['missedAt'] = now
    except Exception as e:
        print('missed winners:', e)
    try:   # 🧬 ONE lifecycle for all ten roles: real-money evidence only; a failed generation is replaced on this call
        of, lc_ev_ = rs._lc_evaluate(of, arch, cour, now)
        for e_ in lc_ev_:
            line_ = (f"🧬 generation {e_['gen']} replaced by generation {e_['to']} — {e_['why']}. New lesson: {e_['changed']}" if e_['kind'] == 'replaced'
                     else f"🧬 generation {e_['gen']} on PROBATION — {e_['why']}" if e_['kind'] == 'probation' else f"🧬 generation {e_['gen']} back to ACTIVE — {e_['why']}")
            st['feed'] = (list(st.get('feed') or []) + [{'at': now, 'who': e_['role'], 'sym': '', 'text': line_}])[-rs._pd.FEED_KEEP:]
            rs._tk.KERNEL.note('judge', {'replaced': 'GENERATION REPLACED', 'probation': 'PROBATION'}.get(e_['kind'], 'BACK TO ACTIVE'), f"{e_['role']} gen {e_['gen']} — {e_['why']}", now, key=f"lc:{e_['role']}:{e_['kind']}:{e_['gen']}")
            if e_['kind'] == 'replaced':
                ad_ = rs._admin_load(); rs._audit(ad_, 'agents', 'agent-generation', f"{e_['role']} gen {e_['gen']} → {e_['to']}: {e_['why']} · {e_['changed']}"[:300]); rs._admin_save(ad_)
    except Exception as e:
        print('lifecycle:', str(e)[:160])
    cards = rs._of.scorecards(st, arch, of, rs._agents_real(), cour, life={g_['role']: g_ for g_ in rs._tkl.generations(rs._lc_book(now), now)})
    rs._office_lat('judge', (rs.time.perf_counter() - t0) * 1000)
    of['lat'] = rs._office['lat']
    rs._office['state'] = of
    rs._json_save(rs.OFFICE_PATH, of); rs._json_save(rs.ARCHIVE_PATH, arch)
    # the CURRENT candidate, desk by desk
    case = cases[0] if cases else None
    cur_ctx, cur_case = {}, None
    if case:
        row = case['row']
        m = case['mint']
        scan = rs._of.scan_status((row.get('vitals') or {}).get('safe'), m in rs._intel_inflight, rs._fuse._f(rs._intel_failed.get(m)), rs._fuse._f((rs._intel_cache.get(m) or (0,))[0]) if isinstance(rs._intel_cache.get(m), (tuple, list)) else 0.0, now, rs.INTEL_TTL)
        cur_ctx = {'tally': rs._of.tally_read(row, ser.get(m), now), 'weather': wx, 'courier': cour, 'scan': scan,
                   'warden': wd if wd and wd.get('mint') == m and now - rs._fuse._f(wd.get('at')) <= 900 else None, 'filed': True}
        cur_case = {**rs._tkv.case_view(case, cur_ctx), 'chart': rs._office_chart_view(rs._office['charts'].get(m), row)}
    ms = {a: (rs._office['lat'].get(a) or [None])[-1] for a in rs._of.CHAIN}
    dv_rec = rs._of.devil_record(st, 72, now)   # 📝 the practice desk's objection record (display)
    gens_ = {g_['role']: g_ for g_ in rs._tkl.generations(rs._lc_book(now), now)}
    reviews_ = ((of.get('judge') or {}).get('reviews')) or []
    kmet_ = rs._tk.KERNEL.metrics(now)
    pl_all = [(c_, rs._tkv.pipeline(c_, {'courier': cour, 'ms': {}})) for c_ in cases[:4]]
    krec = lambda who: [{'at': now, 'text': f"${c_['symbol']} · " + next((s_['word'] for s_ in pl_ if s_['agent'] == who), '')[:150]} for c_, pl_ in pl_all]   # what THIS desk said about the top candidates of this pass
    top_ = cases[0] if cases else None
    op_ = (top_ or {}).get('op') or {}
    live = {
        'tally': {'task': f"measured {perf.get('coins')} coins this pass", 'at': perf.get('at'), 'rule': 'one MintState per mint · every section its own timestamp', 'decision': f"{perf.get('coins')} coins read · {stale} stale tapes · {kmet_['mints']} mints in state",
                  'inputs': cur_ctx.get('tally'), 'output': op_.get('tally'), 'recent': krec('tally')},
        'sherlock': {'task': f"evidence for {len(cases)} candidates · {(rs._office.get('enrich') or {}).get('queue', 0)} scan(s) queued", 'at': perf.get('at'), 'rule': 'UNKNOWN is research, never a rejection', 'decision': None if not top_ else f"${top_['symbol']} known: {', '.join(op_['sherlock']['known']) or 'nothing yet'}",
                     'inputs': None if not top_ else {'vitals': top_['row'].get('vitals'), 'scan': cur_ctx.get('scan')}, 'output': op_.get('sherlock'), 'recent': krec('sherlock')},
        'weather': {'task': f"read {(wx.get('inputs') or {}).get('coins')} coins + {(wx.get('inputs') or {}).get('rugN')} judged calls", 'at': wx.get('at'), 'rule': 'regime → rank ×' + f"{(op_.get('weather') or {}).get('factor', 1):g}" + f" · size ×{rs._of.weather_size(wx):g}",
                    'decision': f"{wx.get('regime')} ({round(rs._fuse._f(wx.get('confidence')) * 100)}% confidence)", 'inputs': wx.get('inputs'), 'output': {'regime': wx.get('regime'), 'why': wx.get('why'), 'mods': wx.get('mods'), 'missing': wx.get('missing')},
                    'recent': [{'at': w_['at'], 'text': f"{w_['regime']} — {w_['why']}"} for w_ in (of.get('weatherLog') or [])[-4:]][::-1]},
        'trigger': {'task': f"timing for {len(cases)} candidates from the live narrative", 'at': perf.get('at'), 'rule': f"ENTER on hot early move · breakout · running; READY from rank {rs._tk._b.READY_MIN:g}",
                    'decision': None if not top_ else f"${top_['symbol']} {op_['trigger']['state']}", 'inputs': {'readyMin': rs._tk._b.READY_MIN, 'lesson': (gens_.get('trigger') or {}).get('lessonVector')},
                    'output': op_.get('trigger'), 'recent': krec('trigger')},
        'devil': {'task': f"challenged {len(cases)} candidates", 'at': perf.get('at'), 'rule': 'evidence lowers the rank; only the hard wall blocks', 'decision': None if not top_ else f"${top_['symbol']} {rs._tkv.devil_view(op_)['word']}",
                  'inputs': {'bustedReads': sorted(bust_seen) if bust_seen else None, 'lesson': (gens_.get('devil') or {}).get('lessonVector')}, 'output': None if not top_ else rs._tkv.devil_view(op_), 'recent': krec('devil'), 'record': dv_rec[:10]},
        'warden': {'task': 'sizes each agent seat before it is filled', 'at': (wd or {}).get('at'), 'rule': (wd or {}).get('decided'), 'decision': None if not wd else f"${wd.get('sym')} ${wd['requested']:.2f} → ${wd['allowed']:.2f}" + (' VETO' if wd['veto'] else ''),
                   'inputs': None if not wd else {k: v for k, v in wd.items() if k in ('requested', 'limits')}, 'output': None if not wd else {k: wd[k] for k in ('allowed', 'mult', 'eff', 'veto', 'rules', 'decided')},
                   'recent': [{'at': w_['at'], 'text': f"${w_['sym']} {w_['move']} ${w_['req']:.2f} → ${w_['allowed']:.2f} · {w_['rule']}: {w_['why']}"} for w_ in (of.get('wardenLog') or [])[-4:]][::-1]},
        'courier': {'task': f"read {cour.get('sends')} sends + {cour.get('refused')} refusals of the last hour", 'at': cour.get('at'), 'rule': 'confirmed = filled row + signature', 'decision': cour.get('health'),
                    'inputs': {k: cour.get(k) for k in ('sends', 'fills', 'failed', 'expired', 'refused', 'retries', 'duplicates', 'unsigned', 'pending')}, 'output': {k: cour.get(k) for k in ('health', 'why', 'deltaMed', 'deltaWorst', 'landMed', 'feeMed')},
                    'recent': [{'at': r_['at'], 'text': f"${r_['sym']} {r_['side']} ${r_['usd']:.2f} — {r_['state']}" + (f" · {r_['delta']:+.2f}% vs mid" if r_.get('delta') is not None else '') + (f" · {r_['err']}" if r_.get('err') else '')} for r_ in (cour.get('last') or [])[:4]]},
        'reaper': {'task': f"watching {len(rs._office.get('reports') or [])} open position(s) · {len(rs._office['exiting'])} exit(s) waiting on the ledger", 'at': now, 'rule': 'R1–R9, first that fires',
                   'decision': ' · '.join(f"${r_['symbol']} {r_['state']}" for r_ in (rs._office.get('reports') or [])[:4]) or None, 'inputs': rs._of.tunes(of, 'reaper') | {'takeLine': rs._of.take_line(rcfg, st.get('scalp'))},
                   'output': [{k: r_.get(k) for k in ('symbol', 'state', 'rule', 'evidence')} for r_ in (rs._office.get('reports') or [])],
                   'recent': [{'at': p_.get('closedAt'), 'text': f"${p_.get('sym')} {p_.get('rule')} → " + (f"{p_['realPct']:+.1f}% real (confirmed)" if p_.get('confirmed') and p_.get('realPct') is not None else 'exit NOT confirmed')} for p_ in (arch.get('positions') or [])[-4:]][::-1]},
        'archivist': {'task': f"filed {len(cases)} case(s) this pass · {len(closed)} position(s) closed", 'at': now, 'rule': 'hash-chained · bounded · losses kept', 'decision': f"{len(arch.get('cases') or [])} cases · {len(arch.get('positions') or [])} positions on file",
                      'inputs': {'caseCap': rs._of.ARCH_CASES, 'positionCap': rs._of.ARCH_POS, 'filedEver': arch.get('filed')}, 'output': {'hashBreaks': viol['archivist']['rule'], 'folded': sum(v['n'] for k, v in (arch.get('agg') or {}).items() if k in ('cleared', 'blocked'))},
                      'recent': [{'at': c_['at'], 'text': f"${c_['d'].get('sym')} {'cleared' if c_['d'].get('cleared') else 'blocked'}" + (f" · {c_['d']['action']}" if c_['d'].get('action') else '') + (f" → {c_['out']['p5']:+.1f}% at 5 min" if (c_.get('out') or {}).get('p5') is not None else '')} for c_ in (arch.get('cases') or [])[-4:]][::-1]},
        'judge': {'task': f"{len(reviews_)} real exits reviewed · {sum(1 for c_ in (of.get('candidates') or {}).values() if c_['status'] == 'shadow')} tunable(s) in shadow", 'at': now,
                  'rule': f"one lifecycle for ten roles: PROBATION at net {rs._tkl.PROBATION_N} real losses pinned · replaced at {rs._tkl.REPLACE_N}",
                  'decision': 'on probation: ' + (', '.join(r_ for r_, g_ in gens_.items() if g_['status'] == 'PROBATION') or 'nobody'),
                  'inputs': {'reviews': len(reviews_)}, 'output': {'probation': [r_ for r_, g_ in gens_.items() if g_['status'] == 'PROBATION'], 'generations': {r_: g_['generation'] for r_, g_ in gens_.items()}},
                  'recent': [{'at': x_.get('retiredAt'), 'text': f"{x_.get('role')} gen {x_.get('gen')} replaced — {x_.get('why')}"} for x_ in (rs._lc_book(now).get('lineage') or [])[-4:]][::-1]},
    }
    cands = [{**{k: v for k, v in c_.items() if k != 'shadow'}, 'eval': c_.get('eval') or rs._of.evaluate(c_)} for c_ in sorted((of.get('candidates') or {}).values(), key=lambda c_: -c_['at'])[:6]]
    pipe = rs._tkv.pipeline(case, {**cur_ctx, 'ms': ms})
    if cur_case:
        cur_case['bars'] = rs._office_bars(case.get('pair'), case['mint'])
    queue = []   # every kernel candidate of this pass with the desk it stands at right now (the first desk that has not passed it)
    for c_ in cases[:6]:
        cx_ = cur_ctx if c_ is case else {'tally': rs._of.tally_read(c_['row'], ser.get(c_['mint']), now), 'weather': wx, 'courier': cour}
        pl_ = pipe if c_ is case else rs._tkv.pipeline(c_, {**cx_, 'ms': {}})
        at_ = next((s_ for s_ in pl_ if s_['agent'] not in ('archivist', 'judge', 'reaper') and s_['state'] not in ('PASS', 'DONE', 'WARN')), pl_[5])
        ch_ = c_['row'].get('chart') or {}
        queue.append({'mint': c_['mint'], 'symbol': c_.get('symbol'), 'lean': c_.get('rank'), 'rank': c_.get('rank'), 'status': c_['status'], 'cleared': c_.get('cleared'), 'go': c_.get('cleared'), 'at': at_['agent'], 'state': at_['state'], 'word': str(at_['word'])[:140],
                      'structure': ch_.get('state'), 'entry': (ch_.get('entry') or [None])[0], 'conf': ch_.get('conf'), 'data': ch_.get('q'), 'launch': c_['row'].get('launch'),
                      'pair': c_.get('pair'), 'bars': rs._office_bars(c_.get('pair'), c_['mint']), 'chart': rs._office_chart_view(rs._office['charts'].get(c_['mint']), c_['row']),
                      'devil': rs._tkv.devil_view(c_['op']), 'trace': rs._tkv.trace(c_, cx_)})
    if cur_case:
        cur_case['trace'] = queue[0]['trace'] if queue and queue[0]['mint'] == cur_case['mint'] else rs._tkv.trace(case, cur_ctx)
    dq_ = {}
    for c_ in rs._office['charts'].values():
        k_ = ((c_.get('q') or {}).get('state')) or 'NOT READ'
        dq_[k_] = dq_.get(k_, 0) + 1
    try:   # ✋ your answers to Reaper's questions, graded 15 min later (kept your line → right if the coin held · approved → right if it fell)
        st['askLog'], ask_rec_ = rs._of.ask_grade(st.get('askLog'), lambda m_: (rs._jup_px_cache.get(m_) or (0, 0))[1], now)
    except Exception:
        ask_rec_ = None
    rs._office['payload'] = {
        'at': now, 'mission': rs._of.mission(money, view.get('stage'), now, rs._office.get('last'), view.get('underwater')) | {'control': bool(rcfg.get('agentControl')), 'probation': [r_ for r_, g_ in gens_.items() if g_['status'] == 'PROBATION']},
        'office': {'chain': list(rs._of.CHAIN), 'priority': list(rs._of.PRIORITY), 'coins': perf.get('coins'), 'cases': len(cases), 'cleared': sum(1 for c_ in cases if c_['cleared'])},
        'agents': rs._of.agent_cards(cards, {'live': live, 'office': of}), 'currentCase': cur_case, 'pipeline': pipe,
        'queue': queue, 'positions': rs._office_positions(), 'exiting': [{'mint': p_['mint'], 'sym': p_.get('sym'), 'rule': p_.get('askRule'), 'state': (p_.get('exit') or {}).get('state'), 'since': p_.get('leftAt')} for p_ in rs._office['exiting']],
        'execution': {**cour, 'metrics': rs._fw.exec_metrics(rs._fw_peek().get('ledger'), now, dupes=rs._FW_DUPES['n'])}, 'ownerHand': rs._of.owner_hand(arch.get('positions')), 'survival': rs._surv.cohort(rs._SURV, now), 'edge': rs._edge_view(), 'ownerSeats': rs._of.owner_seats(arch.get('positions')), 'ownerStudy': rs._study['v'], 'aiMemory': rs._aim.size(rs._aim_mem.get() or {}), 'askRec': ask_rec_, 'agentPredict': rs._of.pred_record(arch.get('positions')), 'tid': tid, 'learning': {'patterns': rs._of.patterns(arch, st), 'candidates': cands, 'lineage': [{'agent': x_.get('role'), 'gen': x_.get('gen'), 'why': f"{x_.get('status') or 'replaced'} — {x_.get('why') or ''}" + (f" · next generation: {x_['changed']}" if x_.get('changed') else ''), 'at': x_.get('retiredAt')}
                                                         for x_ in reversed((rs._lc_book(now).get('lineage') or [])[-12:])], 'devil': dv_rec[:10], 'needShadow': rs._of.SHADOW_N, 'needPropose': rs._of.PROPOSE_N},
        'index': (rs._office.get('index') or [])[:80], 'rpc': {'lanes': rs._rpc_quota_state(), 'note': 'keyed lanes = keeper sends / balances first, then holder scans (budgeted); discovery comes from Pump\'s live stream + the launch boards — no RPC first-seen listener runs'},
        'court': rs._office.get('court'), 'opp': rs._office.get('opp'), 'coach': rs._coach_view(now), 'tradeTape': rs._trade_tape(now),   # 👑 the directives in force · 🎬 every real agent trade as one story
          # 👨‍⚖️ the Judge's loss / win reviews + rules · 🎯 this pass's A / B / C ranking counts
        'judge': {'probation': [r_ for r_, g_ in gens_.items() if g_['status'] == 'PROBATION'], 'rulings': len(reviews_), 'probationAt': rs._tkl.PROBATION_N, 'replaceAt': rs._tkl.REPLACE_N,
                  'contribution': rs._of.contribution(st, arch, of, cour, rs._agents_real(), money)},
        'data': {'states': dq_, 'trusted': dq_.get('TRUSTED', 0), 'enterGrade': dq_.get('TRUSTED', 0) + dq_.get('USABLE_WITH_CAUTION', 0), 'coins': len(rs._office['charts']),
                 'meaning': 'TRUSTED = real 1-minute OHLC from the candles service, every integrity check passed, newest bar ≤ 240s old, per-candle volume on ≥ 80% of moving bars, a live pool reading, confidence ≥ 80',
                 'sources': {'candles': 'candles service on this machine: the price-history provider named on each chart (today: Jupiter) sharpened with FEELESS-recorded prices', 'tape': "Tally's own tape: one launch-board price a pass (closes only) — RECONSTRUCTED",
                             'volume': 'per-candle: the provider bars that carry a figure · totals: the launch board\'s 5-min / 1-hour volume', 'trades': 'the 90-second trade tape (parsed swaps), only for coins whose tape the service already holds',
                             'liquidity': 'the launch board\'s pool depth, read each pass onto Tally\'s tape'}},
        'take': rs._of.take_info(rcfg, st.get('scalp')),
        'policy': {**rs._oe.policy(rcfg), 'controls': rs._oe.controls(rcfg, rs._oe.agents_now(rs._of.take_info(rcfg, st.get('scalp')), {**rs._of.tunes(of, 'reaper'), 'maxSeatPct': rs._of.tune(of, 'warden', 'maxSeatPct')},
                                                                                    next(({'stopPct': r_['thesis']['stopPct'], 'sym': r_.get('symbol')} for r_ in rs._office.get('reports') or [] if (r_.get('thesis') or {}).get('stopPct')), None)))},
        'ready': rs._oe.ready(rs._office['boot'], now), 'seat': rs._agents.get('seat'), 'switchEval': rs._agents.get('switchEval'),
        'review': rs._oe.review(st, arch, of, now, marks=of.get('reviewMarks')), 'launch': {'record': rs._oe.pad_record(rs._pd._judged(st, 5)), 'pads': dict(rs._oe.PADS), 'types': list(rs._oe.TYPES),
                                                           'source': 'mint suffix + the launch board row (curve flag, pool age) — anything else is UNKNOWN'},
        'performance': {'deskMs': round(desk_ms, 1), 'agents': {a: {**rs._of.lat(rs._office['lat'].get(a)), 'series': list(rs._office['lat'].get(a) or [])[-30:]} for a in rs._of.CHAIN}, 'chart': rs._of.lat(rs._office['lat'].get('chart')),
                        'speed': {**rs._oe.speed_view(of.get('speed')), 'seatWakes': int(rs._office.get('seatWakes') or 0), 'tickEvery': (rs._agents.get('seat') or {}).get('tickEvery')},
                        'candles': {**rs._office['candleStat'], 'tape': sum(1 for c_ in rs._office['charts'].values() if c_.get('src') == 'tape'), 'real': sum(1 for c_ in rs._office['charts'].values() if c_.get('src') == 'candles')}},
    }
    rs._office['payload']['ops'] = rs._oe.ops(rs._office['payload']['ready'], rs._office['payload']['seat'], rs._office.get('courier'), rs._is_keeper(), rs._uni.FILL_MOVES_HR)
    rs._office['payload']['cycle'] = {**(rs._office.get('cycle') or {}), 'nextIn': rs.AGENTS_EVERY}
    rs._office['payload']['seatActions'] = rs._oe.seat_actions(((rs._agents.get('card') or {}).get('seats')), rs._agents.get('decisions'), rs._agents.get('switchEval'), rs._agents.get('seat'))
    rs._office['payload'].update(rs._office_seat_payload())
    try:
        sc_ = rs._social_cache()
        want_ = {x_.get('mint') for x_ in (rs._agents.get('table') or [])[:30]} | set(rs._office.get('pos') or {})
        rs._office['payload']['social'] = {m_: {k_: v_ for k_, v_ in sc_[m_].items() if k_ not in ('search',)} for m_ in want_ if m_ in sc_}
        rs._office['payload'].update(fresh=rs._office_fresh(now), live=rs._office.get('live'), open=rs._office.get('open'), scans=rs._office.get('scans'), loadPass=rs._office_load_pass(),
                                  lifecycle=rs._lifecycle(now),
                                  kernel=rs._kernel_view(now), rpcStats=rs._chain.rpc_metrics(now), enrich={**(rs._office.get('enrich') or {}), **rs._ENRICH.metrics(now)},
                                  generations=rs._tkl.generations(rs._lc_book(now), now, rs._lc_shadows()),
                                  deskStats=rs._desk_stats_view(now), dialLab=rs._dial_lab(now),
                                  rounds={**rs._tr.summary(rs._rounds_state(), now), 'roundSec': rs._tr.ROUND_SEC, 'desk': {'n': int(now // rs._tr.ROUND_SEC) % int(86400 // rs._tr.ROUND_SEC) + 1, 'left': round(rs._tr.ROUND_SEC - now % rs._tr.ROUND_SEC, 1)},
                                          'live': sorted([{'mint': m_, 'sym': e_.get('sym'), 'round': e_.get('round'), 'left': rs._tr.time_left(e_['first'], now),
                                                           'tier': ((e_.get('reads') or [{}])[-1]).get('tier'), 'score': ((e_.get('reads') or [{}])[-1]).get('score'),
                                                           'phase': ((e_.get('reads') or [{}])[-1]).get('phase')}
                                                          for m_, e_ in (rs._rounds_state().get('c') or {}).items() if not e_.get('decision')], key=lambda r_: (-(r_['round'] or 0), -rs._fuse._f(r_['score'])))[:12],
                                          'recent': [{k_: h_.get(k_) for k_ in ('sym', 'decision', 'why', 'at', 'rounds')} | {'reads': [{k_: r_.get(k_) for k_ in ('round', 'tier', 'score', 'px', 'phase')} for r_ in h_.get('reads') or []]}
                                                     for h_ in (rs._rounds_state().get('hist') or [])[-12:]][::-1]},
                                  memory={k_: v_ for k_, v_ in (rs._real_mem(now) or {}).items() if k_ != 'cells'} | {'worst': sorted(((v_['est'], k_, v_['n']) for k_, v_ in ((rs._real_mem(now) or {}).get('cells') or {}).items()))[:6]})
    except Exception as e:
        print('fresh:', e)
    rs._office['payload']['performance']['passMs'] = round(sum(rs._fuse._f(ms.get(a)) for a in rs._of.CHAIN), 2)
    rs._tape_ledger(now)
    rs._office['payload'].update(nightGuard=rs._ng.view(rs._night['st'], rs._night['v'], now) if rs._night.get('v') else None, tape=rs._tk.KERNEL.tape.view(), ownerReview=rs._owner_view(now), ai=rs._ai_view(now, light=True), net=rs._net_stats(now), armed=rs._office.get('armed'), valve=rs._office.get('valve'), lab=rs._lab_view(now), regret=rs._rg.view(rs._regret_book(), now), capital=rs._capital_view(), trail=rs._office.get('trail'), teach={**rs._tch.view(rs._teach_state()), 'rules': rs._taught_view()},
                              universe={'capUsd': rs._uni.band()[1], 'minCapUsd': rs._uni.band()[0], 'word': rs._uni.band_word(), 'maxAgeH': rs._uni.limits()['maxAgeH'], 'minVol1h': rs._uni.limits()['minVol'], 'pumpTrend': rs._uni.limits()['trend'], 'trendingN': rs._uni.limits()['trendingN'], 'inLane': len(rs._agents.get('table') or []),
                                        'board': (rs._office.get('intake') or {}).get('board'), 'mints': len(rs._tk.KERNEL.store.mints)})
    rs._hub_publish(now)   # 📡 this pass as DELTAS: only what changed since the last one
    try:   # a read-only snapshot of what the page was handed (like agents_duty.json) — for checking the office without signing in to HQ (≤ once a minute)
        if now - rs._fuse._f(rs._office.get('viewSavedAt')) >= rs.VIEW_SAVE_SEC:
            rs._json_save(rs.DATA_DIR / 'agent_office_view.json', rs._office['payload']); rs._office['viewSavedAt'] = now
    except Exception:
        pass


def _agents_real():
    """💵 The REAL-money Fuse card test: every coin the agents put on the owner's real card (leg tag '🤖 agents GO') that has left it,
    judged on the card's own exit vs entry (real_learn). → {n, med, won}"""
    rs = _rs()
    ps = [rs._fuse._f(p.get('pct')) for p in (rs._json_load(rs.REAL_LEARN_PATH, {}).get('pieces') or []) if 'tag:🤖' in (p.get('k') or [])]
    last_ = list(ps)   # in the order they left the card (for the win / loss pips)
    last_sg = [rs._fuse._f(p.get('pct')) for p in (rs._json_load(rs.REAL_LEARN_PATH, {}).get('pieces') or []) if 'tag:🤝' in (p.get('k') or [])]
    n = len(ps); ps.sort()
    out = {'n': n, 'med': None if not n else round(ps[n // 2] if n % 2 else (ps[n // 2 - 1] + ps[n // 2]) / 2, 2), 'won': None if not n else round(sum(1 for x in ps if x > 0) / n * 100)}
    sg = sorted(rs._fuse._f(p.get('pct')) for p in (rs._json_load(rs.REAL_LEARN_PATH, {}).get('pieces') or []) if 'tag:🤝' in (p.get('k') or []))
    out['suggested'] = {'n': len(sg), 'med': None if not sg else round(sg[len(sg) // 2], 2), 'won': None if not sg else round(sum(1 for x in sg if x > 0) / len(sg) * 100)}   # 🤝 coins the owner took from their alert
    out['last'] = last_[-16:]; out['suggested']['last'] = last_sg[-16:]; out['w'] = sum(1 for x in last_ if x > 0)
    out['styles'] = rs._rl.style_record(rs._json_load(rs.REAL_LEARN_PATH, {}).get('pieces') or [])   # ⚡ AUTO / SCALP / RIDE, each its own real record
    return out


def _kernel_row(x):
    """A kernel candidate as a tier-card candidate row (the fields the engine's own rows carry)."""
    return {'mint': x['mint'], 'symbol': x['symbol'], 'pairAddress': x['pair'], 'price': x['px'], 'liq': (x.get('nums') or {}).get('liq'), 'safe': (x.get('vitals') or {}).get('safe') is True, 'ageH': (x.get('vitals') or {}).get('ageH')}


def _agent_inherit_rows(limit=8):
    """🤖 INHERIT, NEVER REDO (owner, 2026-10-13: "have the engine build new strats from the agents' work — never waste the agents' time,
    just inherit"): the runner candidates of a PAPER card on pick style `agents` are the kernel's own judged list — READY first, then
    CONTENDING, best rank first — exactly what the ten agents already read, ranked, weighed with real-money memory, the Judge's and
    the coach's penalties this pass. No second scan, no model call, no fetch. A coin the agents rejected is simply not on the list.
    Paper only: the real card's seats are filled by the agents themselves."""
    rs = _rs()
    rows = sorted([(m_, d_) for m_, d_ in rs._tk.KERNEL.dec.items() if d_.get('status') in ('READY', 'CONTENDING') and m_ in rs._tk.KERNEL.store.mints],
                  key=lambda kv: (kv[1]['status'] != 'READY', -rs._fuse._f(kv[1].get('rank'))))
    out = []
    for m_, d_ in rows:
        x = rs._tk.KERNEL.candidate(m_, d_)
        if x and x.get('px') and x.get('pair') and not rs._fw.dollar_named(x.get('symbol')):
            out.append({**rs._kernel_row(x), 'score': 60 + min(40.0, rs._fuse._f(x.get('rank')) / 10), 'tag': f"🤖 inherits the agents · {d_['status']} · rank {rs._fuse._f(x.get('rank')):.0f}"})
    return out[:limit]


def _agents_go_rows(legs=(), seats=2, learn=False, learn_pct=100, trust=False):
    """The team's GO coins for the real card's rush. PROVEN (5-min stage conquered + `agentFeed`): up to `agentSeats` coins, normal tickets.
    🎓 LEARNING (`agentLearn`, before they are proven): ONE coin at a time — a WHOLE seat at `learn_pct` 100 (default), else a % ticket.
    The other seats stay the owner's: the agents only SUGGEST for them (My cards alert → 🤝 tagged, scored apart)."""
    rs = _rs()
    v = rs._agents.get('view') or {}
    held = sum(1 for l in legs or [] if rs._prime.agent_leg(l))
    if v.get('feed'):
        if held >= int(seats or 2):
            return []
        learning = False
    elif learn:
        if held >= (2 if trust and rs._pos.trusted(rs._agents_real()) else 1):   # 🤝 earned trust: a 2nd seat
            return []
        learning = True
    else:
        return []
    on_ = {l.get('mint') for l in legs or []}
    out = []
    for m_, d_ in rs._tk.KERNEL.ready(exclude=on_):   # ⚙ the kernel's READY candidates (never a paper GO): the engine's trench drop still applies every one of its own checks
        x = rs._tk.KERNEL.candidate(m_, d_)
        if x and not rs._fw.dollar_named(x.get('symbol')):
            out.append({**rs._kernel_row(x),
                        'trenchOnly': True, 'trenchScore': 900 + x['rank'], 'tag': '🤖 agents READY' + (' · 🎓 learning seat' if learning else ''), **({'stakePct': int(learn_pct or 100)} if learning else {})})
    return out[:1 if learning else 4]


def _agents_snapshot():
    """Everything the last agent pass + tier tick left in memory (the office rides on the same answer). Runs nothing."""
    rs = _rs()
    if not rs._agents.get('view'):
        st = rs._agents_mem.get()
        rcfg_ = ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {})
        rs._agents['view'] = rs._paper_view(st, rs._agents.get('paper') or [], rcfg_, rs.time.time())
    v_ = {**rs._agents['view'], 'impostors': rs._agents.get('impostors') or []}   # 🎭 fakes of real coins dropped at intake (Tally's guard)
    if rs._agents.get('card') and (v_.get('card') or {}) != rs._agents['card']:   # the card moves every tier tick; the view is rebuilt once a minute
        v_ = {**v_, 'card': rs._agents['card']}
    return {**v_, 'office': rs._office.get('payload')}   # 🏢 the office rides on the SAME response: the Agents page makes one request

