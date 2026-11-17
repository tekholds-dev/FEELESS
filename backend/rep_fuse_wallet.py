"""🧹 Fuse wallet — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


def _parsed_info(acc):
    """The `parsed.info` of a jsonParsed account, or {}. Some RPC providers answer an account they can't parse (Token-2022 with
    extensions) as raw `[base64, 'base64']` — a list, not a dict. Reading `.get` on it crashed the whole holder scan (HTTP 500),
    so every coin whose top holders included one such account stayed "unscanned" and out of every list."""
    data = (acc or {}).get('data') if isinstance(acc, dict) else None
    parsed = data.get('parsed') if isinstance(data, dict) else None
    info = parsed.get('info') if isinstance(parsed, dict) else None
    return info if isinstance(info, dict) else {}


def _fw_load():
    """🗄 The Fuse wallet lives in SQLite (crash-safe, one transaction per write) — never a half-written JSON file."""
    rs = _rs()
    d = rs._store.KV(rs.FUSE_WALLET_PATH).get({}) or {}
    d.setdefault('books', {}); d.setdefault('ledger', [])
    return d


def _fw_save(d):
    rs = _rs()
    rs._store.KV(rs.FUSE_WALLET_PATH).put(d)


def _fw_peek():
    """⚡ READ-ONLY view of the Fuse wallet doc, parsed once per write (the 1.2 MB doc was parsed for every cfg / ledger look: dozens of
    times a tick). NEVER mutate or save what this returns — anything that writes uses `_fw_load()` (its own fresh copy), as before."""
    rs = _rs()
    if rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return rs._fw_load()
    kv = rs._store.KV(rs.FUSE_WALLET_PATH)
    key = (str(rs.FUSE_WALLET_PATH), kv.stamp())
    if rs._fw_peek_cache['key'] != key or key[1] is None:
        rs._fw_peek_cache.update(key=key, d=rs._fw_load())
    return rs._fw_peek_cache['d']


def _fw_cfg():
    rs = _rs()
    return rs._fw.clean_cfg(rs._fw_peek().get('cfg') or {})


def _fw_signer_ready():
    """Owner-approved Circle signing (sidecar POST /sign) is live when the Circle service is configured (cached ≤60s)."""
    rs = _rs()
    return bool(rs._fw_signer['ok'])


async def _fw_signer_check():
    rs = _rs()
    if rs.time.time() - rs._fw_signer['at'] < 60:
        return rs._fw_signer['ok']
    try:
        st = await rs._circle('GET', '/status')
        rs._fw_signer.update(ok=bool(st.get('configured')), at=rs.time.time())
    except Exception:
        rs._fw_signer.update(ok=False, at=rs.time.time())
    return rs._fw_signer['ok']


async def _fw_sign(cfg, raw_b64, memo):
    """Circle signs ONE keeper transaction — only ever for the picked Fuse wallet id. Never sends."""
    rs = _rs()
    if not cfg.get('walletId') or not raw_b64:
        raise rs.HTTPException(400, 'No Fuse wallet / transaction to sign.')
    return await rs._circle('POST', '/sign', {'walletId': cfg['walletId'], 'rawTransaction': raw_b64, 'memo': memo[:80]})


async def _fw_balances(addr):
    """SOL + every token the Fuse wallet holds (atoms + decimals), one parallel RPC read."""
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=12) as http:
        bal, *toks = await rs.asyncio.gather(rs._krpc(http, 'getBalance', [addr, {'commitment': 'confirmed'}]),
                                          *[rs._krpc(http, 'getTokenAccountsByOwner', [addr, {'programId': pg}, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}]) for pg in rs._FW_TOKEN_PROGRAMS])
    tokens, decs = {}, {}
    for t in toks:
        for a in (t or {}).get('value') or []:
            info = rs._parsed_info(a.get('account'))
            amt = info.get('tokenAmount') or {}
            if info.get('mint'):
                tokens[info['mint']] = tokens.get(info['mint'], 0) + int(amt.get('amount') or 0); decs[info['mint']] = int(amt.get('decimals') or 0)
    return {'sol': int((bal or {}).get('value') or 0) / 1e9, 'tokens': tokens, 'decimals': decs}


def _jup_keys(env=None):
    """The KEEPER's Jupiter keys (`JUPITER_API_KEY`, `_2` … `_6`, in order, no repeats) — minus the one set aside for price reads once
    there are three or more (`jup_keys.read_key`). Never logged, never returned to a page."""
    rs = _rs()
    import jup_keys as _jk
    return _jk.keeper_keys(rs.os.environ if env is None else env)


def _jup_lanes(key):
    """📡 Jupiter = LANES, like the RPC: one per key (each plan's own quota: `JUPITER_API_KEY`, `_2` … `_6`) + the public one (its own,
    separate limit). Each lane is PACED to what its plan allows and rests after a 429; a call goes to whichever lane is free first, so
    N keys ≈ N requests a second for the keeper's quotes. 2026-10-12: a $0.08 sell failed "route unavailable (HTTP 429)" four passes in
    a row (quotes were fired in bursts at the keyed lane alone), Courier read execution BAD and every seat was blocked behind it.
    2026-10-13: call → send was a median 89s — four quotes a buy through ONE ~1 rps key. Never a URL with a key in it; the key rides a header.
    `key` = one key or a list of keys."""
    rs = _rs()
    keys = [k for k in ([key] if isinstance(key, str) else list(key or [])) if k]
    for i, k in enumerate(keys):
        rs._JUP_KEY_N.setdefault(k, i + 1)
    return [('https://api.jup.ag', {'x-api-key': k}) for k in keys] + [('https://lite-api.jup.ag', {})]


def _jup_lid(lane):
    """A lane's own pacing slot: the base for the public lane and the first key, base#N for every further key."""
    rs = _rs()
    n = rs._JUP_KEY_N.get((lane[1] or {}).get('x-api-key'), 1)
    return lane[0] if n <= 1 else f'{lane[0]}#{n}'


def _jup_pick(lanes, now):
    """→ (lane, wait seconds): the lane whose next free slot comes first (its spacing and any 429 rest counted)."""
    rs = _rs()
    free = lambda l: max(rs._FW_JUP_PACE['next'].get(rs._jup_lid(l), 0.0), rs._FW_JUP_PACE['rest'].get(rs._jup_lid(l), 0.0))
    lane = min(lanes, key=free)
    return lane, max(0.0, free(lane) - now)


async def _fw_jup(method, path, **kw):
    rs = _rs()
    lanes = rs._jup_lanes(rs._jup_keys())
    if rs._FW_JUP_PACE['lock'] is None:
        rs._FW_JUP_PACE['lock'] = rs.asyncio.Lock()
    scale = rs.JUP_GAP_SEC / 0.2
    r = None
    async with rs.httpx.AsyncClient(timeout=20) as http:
        for attempt in range(max(6, len(lanes) + 3)):   # 429 / 5xx = that lane rests and the other one answers; every lane resting = wait for the first to come back
            async with rs._FW_JUP_PACE['lock']:
                lane_, wait_ = rs._jup_pick(lanes, rs.time.time())
                (base, hdr), lid = lane_, rs._jup_lid(lane_)
                if wait_ > 0:
                    await rs.asyncio.sleep(min(wait_, 6.0))
                rs._FW_JUP_PACE['next'][lid] = rs.time.time() + rs.JUP_LANE_GAP.get(base, 0.35) * scale
            try:
                r = await http.request(method, base + path, headers=hdr, **kw)
            except rs.httpx.HTTPError:   # 📡 a dropped connection / timeout = that lane rests like a 5xx — it once escaped as a raw error and killed the whole tier tick mid seat-check
                r = None
                rs._FW_JUP_PACE['rest'][lid] = rs.time.time() + rs.JUP_LANE_REST * scale
                continue
            if r.status_code != 429 and r.status_code < 500:
                break
            try:
                ra_ = float(r.headers.get('retry-after') or 0)
            except (TypeError, ValueError, AttributeError):
                ra_ = 0.0
            rs._FW_JUP_PACE['rest'][lid] = rs.time.time() + min(20.0, max(rs.JUP_LANE_REST, ra_)) * scale
    if r is None:
        rs._FW_JUP_BUSY['at'] = rs.time.time()
        raise rs.HTTPException(400, 'Jupiter route unavailable (network, HTTP 503)')
    if r.status_code == 429 or r.status_code >= 500:
        # 📡 BUSY = every lane failed THIS call. A 429 on one lane that the other lane then answered is not busy: the public lane is
        # shared with our own price reads and answers 429 most minutes, so marking busy on any 429 kept the seat pre-check standing
        # down every tick — 2026-10-12 23:05 → 23:35: four empty seats, READY coins, and not one buy sent to the keeper.
        rs._FW_JUP_BUSY['at'] = rs.time.time()
    try:
        data = r.json() if r.content else {}
    except ValueError:
        data = {}
    if r.status_code >= 400:
        raise rs.HTTPException(400, f"{str(data.get('error') or data.get('errorMessage') or 'Jupiter route unavailable')[:140]} (HTTP {r.status_code})")
    return data


async def _fw_quote(order, cfg):
    """A REAL Jupiter quote for one keeper order (SOL → coin to buy, coin → SOL to sell). Read-only."""
    rs = _rs()
    q = {'inputMint': rs._fw.SOL_MINT if order['side'] == 'buy' else order['mint'], 'outputMint': order['mint'] if order['side'] == 'buy' else rs._fw.SOL_MINT,
         'amount': str(order['lamports'] if order['side'] == 'buy' else order['atoms']), 'slippageBps': str(cfg['slippageBps'])}
    # 🎯 ONE-HOP route first (coin ⇄ SOL in one pool): a multi-hop route opens accounts for the coins it passes through (rent parked
    # until they close), builds transactions too big to send, and fails more often. Multi-hop only when one hop is missing or costly.
    if order.get('wide'):   # an exit that already failed one-hop: whatever route Jupiter rates best
        return await rs._fw_jup('GET', '/swap/v1/quote', params=q)
    try:
        direct = await rs._fw_jup('GET', '/swap/v1/quote', params={**q, 'onlyDirectRoutes': 'true'})
        if rs._fuse._f(direct.get('outAmount')) > 0 and rs._fuse._f(direct.get('priceImpactPct')) * 100 <= min(1.0, rs._fuse._f(cfg.get('maxImpactPct')) or 1.0):
            return direct
    except rs.HTTPException:
        direct = None
    multi = await rs._fw_jup('GET', '/swap/v1/quote', params={**q, 'restrictIntermediateTokens': 'true'})
    if direct and rs._fuse._f(direct.get('outAmount')) >= rs._fuse._f(multi.get('outAmount')) * 0.995:
        return direct   # one hop pays (nearly) the same → still the cleaner transaction
    return multi


async def _fw_secure_buy(order, cfg, q):
    """🛡 A buy quote is safe when it is near the market price AND the coins really sell straight back (both read-only quotes).
    → (ok, why, sell-back %)"""
    rs = _rs()
    try:
        back = await rs._fw_jup('GET', '/swap/v1/quote', params={'inputMint': order['mint'], 'outputMint': rs._fw.SOL_MINT, 'amount': str(q.get('outAmount')), 'slippageBps': str(cfg['slippageBps'])})
        back_l = rs._fuse._f(back.get('outAmount'))
    except rs.HTTPException as e:
        if any(x in str(e.detail) for x in ('(HTTP 429)', '(HTTP 5')):
            raise   # Jupiter BUSY is not "no route back": it used to read "can't sell it back to SOL (no route)" and bench a good coin for 30 min
        back_l = None
    try:   # market = Jupiter's own price (what routes really pay); a DexScreener pair can lag on young coins
        rs._jup_px_cache.pop(order['mint'], None)   # …read FRESH: the 20s-old cached price made a coin running +3% a minute read "4.6% above market" on every try
        jp = rs._fuse._f(((await rs._jup_prices([order['mint']], keyed=True)) or {}).get(order['mint']))
    except Exception:
        jp = 0.0
    ok_s, why_s = rs._fw.buy_safety({**order, 'midPx': jp or order.get('midPx'), 'maxRoundtripPct': rs._fw.clean_cfg(cfg)['pickSellBackPct']}, q.get('outAmount'), await rs._mint_decimals(order['mint']), back_l)
    return ok_s, why_s, None if back_l is None else round((back_l / max(1, order['lamports']) - 1) * 100, 2)


async def _fw_live_pairs(orders):
    """📡 FRESH live pairs for real-money buy checks (never cached), every source bounded by LIVE_SRC_SEC: DexScreener AND Pump's own coin
    record (every Pump mint, in parallel), then Jupiter only for coins neither answered. Precedence DexScreener → Pump → Jupiter.
    2026-10-12 (6h): 62 of 172 refused agent buys read "live market unavailable" — from this machine DexScreener and Jupiter's public API
    both answered 429 while Pump answered 200, but Pump was asked only after the other two failed, for at most 4 coins a call."""
    rs = _rs()
    want = {str(o.get('pair')): o.get('mint') for o in orders if o.get('pair')}
    if not want:
        return {}

    async def ds_():
        try:
            async with rs.httpx.AsyncClient(timeout=rs.LIVE_SRC_SEC) as http:
                mr = await rs.asyncio.wait_for(http.get('https://api.dexscreener.com/latest/dex/pairs/solana/' + ','.join(sorted(want)[:30])), rs.LIVE_SRC_SEC)
            return {p.get('pairAddress'): p for p in ((mr.json() if mr.status_code == 200 else {}) or {}).get('pairs') or [] if p}
        except Exception:
            return {}

    async def pump_():
        pm = [(pa, m) for pa, m in want.items() if str(m).endswith('pump')][:rs.LIVE_PUMP_MAX]
        if not pm:
            return {}
        async with rs.httpx.AsyncClient(timeout=rs.LIVE_SRC_SEC, headers={'User-Agent': 'Mozilla/5.0'}) as http:
            async def one(pa, m):
                try:
                    r = await rs.asyncio.wait_for(http.get(f'https://frontend-api-v3.pump.fun/coins-v2/{m}'), rs.LIVE_SRC_SEC)
                    pp = rs._launchpad_board.pump_pair(r.json() if r.status_code == 200 else None, pa)
                    return pa, pp if pp and (pp.get('baseToken') or {}).get('address') == m else None
                except Exception:
                    return pa, None
            return {pa: pp for pa, pp in await rs.asyncio.gather(*[one(pa, m) for pa, m in pm]) if pp}

    d_, p_ = await rs.asyncio.gather(ds_(), pump_())
    live = {**{pa: pp for pa, pp in p_.items()}, **{pa: x for pa, x in d_.items() if pa in want}}   # DexScreener wins where both answered
    miss = {pa: m for pa, m in want.items() if pa not in live and m}
    if miss:
        for m in miss.values():
            rs._jup_tok_cache.pop(m, None)
        try:
            toks = await rs.asyncio.wait_for(rs._jup_tokens(list(miss.values()), keyed=True), rs.LIVE_SRC_SEC + 2)
        except Exception:
            toks = {}
        for pa, m in miss.items():
            jp = rs._launchpad_board.jup_pair(toks.get(m)) if toks.get(m) else None
            if jp:
                live[pa] = {**jp, 'pairAddress': pa}
    return live


async def _fw_preflight(tid, buys, cfg, now):
    """🔒 Before a swap SELLS anything: can each new coin really be bought? Live pool (one fresh call for all), the owner's limits,
    then a real quote + the secure-buy checks. A coin that fails is booked as a refused buy (→ benched / re-picked) and returned, so
    the keeper keeps the old coin instead of selling it into cash. Read-only: nothing is signed here."""
    rs = _rs()
    bad = set()
    try:
        live = await rs._fw_live_pairs(buys)
    except Exception:
        return bad   # no reading = no verdict here: the buy's own final gate still fails closed
    for o in buys:
        row = {**o, 'card': tid, 'status': 'skipped', 'at': now}
        ok, why, snap = rs._fw.live_buy_market(o, live.get(o.get('pair')), cfg)
        row.update(snap)
        if ok:
            ok, why = rs._fw.check(row, cfg, rs._fw_peek().get('ledger'), now)
            if not ok and any(x in why for x in rs._FW_NOT_COIN):
                continue   # a cap / pause is not the coin's fault — nothing to hold a sell for
        if ok and o.get('lamports', 0) > 0:
            try:
                q = await rs._fw_quote(o, cfg)
                ok, why, _back = await rs._fw_secure_buy(o, cfg, q)
                if ok and rs._fuse._f(q.get('priceImpactPct')) * 100 > cfg['maxImpactPct']:
                    ok, why = False, f"price impact {rs._fuse._f(q.get('priceImpactPct')) * 100:.2f}% > {cfg['maxImpactPct']:g}%"
            except rs.HTTPException as e:
                if any(x in str(e.detail) for x in rs._FW_NOT_COIN):
                    continue
                ok, why = False, str(e.detail)[:140]
        if not ok:
            bad.add(o['mint'])
            row['err'] = f'{why} — checked before selling, the old coin is kept'[:160]
            async with rs._fw_lock:
                d = rs._fw_load()
                if not rs._fw.logged_recently(d.get('ledger'), row, now, 120):
                    rs._fw_record(d, row); rs._fw_save(d)
    return bad


def _fw_keep(d, tid, book):
    """Save a card's book without losing the miss / bench counts written meanwhile by _fw_record."""
    rs = _rs()
    old = (d.get('books') or {}).get(tid) or {}
    book = rs._fw.merge_owner(old, book)   # 🧷 a top-up written while this keeper pass was running is put back in, never overwritten
    return {**book, 'misses': old.get('misses', book.get('misses') or {}), 'benched': old.get('benched', book.get('benched') or {})}


def _fw_kick_now():
    """🏃 Run one keeper pass NOW in the background (sells first, as always). An owner button returns at once; `_fw_tick_lock` keeps passes one
    at a time and the card's swap-flow strip shows each step. 2026-10-08 owner: "confirm sell all takes a lot" — the request awaited every
    sell's send + confirm (tens of seconds) before the screen answered."""
    rs = _rs()
    if rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return
    t = rs.asyncio.ensure_future(rs._fw_tick(rs.time.time()))
    rs._fw_bg.add(t); t.add_done_callback(rs._fw_bg.discard)


def _fw_record(d, row):
    rs = _rs()
    if row.get('side') == 'buy' and row.get('status') in ('skipped', 'failed') and row.get('mint') and row.get('card') in (d.get('books') or {}) \
            and not any(x in str(row.get('err') or '') for x in rs._FW_NOT_COIN) \
            and not (row.get('status') == 'failed' and rs._fw.slip_transient(d.get('ledger'), row, rs._fuse._f(row.get('at')) or rs.time.time())):
        # 🪑 a coin that keeps failing its buy gets benched — a slippage failure is retried at once instead (the coin is fine, the price ran)
        b, out = rs._fw.note_miss(d['books'][row['card']], row['mint'], rs._fuse._f(row.get('at')) or rs.time.time(), str(row.get('err') or ''))
        d['books'][row['card']] = b
        rs._FW_KICK['at'] = rs._fuse._f(row.get('at')) or rs.time.time()
        if out:
            print(f"fuse wallet: benched {row.get('symbol')} for 1h — {row.get('err')}")
    if row.get('side') == 'buy' and row.get('status') == 'failed' and rs._fw.SLIP_ERR in str(row.get('err') or '') and row.get('card') in (d.get('books') or {}):
        d['books'][row['card']] = {**d['books'][row['card']], 'slipAt': rs._fuse._f(row.get('at')) or rs.time.time()}   # ⏳ the seat waits for the retry
    if row.get('id') and any(r.get('id') == row['id'] and r.get('status') == row.get('status') for r in (d.get('ledger') or [])[-50:]):
        return   # the same order outcome is booked once (two ticks resolving one tx can't double the trail)
    d['ledger'] = rs._fw.recent_rows((d.get('ledger') or []) + [row], rs._fuse._f(row.get('at')) or rs.time.time())   # the recent rows for fast reads …
    try:
        rs._store.Ledger(rs.FUSE_WALLET_PATH).append(row)          # … and the append-only audit table keeps EVERY row forever
    except Exception as e:
        print('fuse wallet ledger:', e)


async def _fw_execute(tid, order, book, cfg, sol_px, liq):
    """One keeper order: real Jupiter quote → the owner's hard limits → Circle signs (Fuse wallet only) → we broadcast → the confirmed
    tx's balance changes ARE the fill. Every outcome goes to the audit ledger; fills + failures reach the owner's inbox."""
    rs = _rs()
    if book.get('pending'):
        rs._FW_DUPES['n'] += 1
        return book   # defense in depth: never overwrite the one in-flight signature with a second sell or buy
    now = rs.time.time()
    # `card` must be present on every outcome. Without it, secure-quote refusals (price gap / no sell-back route) were logged but
    # never counted by _fw_record, so the same unsafe mint retried forever instead of reaching the existing bench-and-replace path.
    slip_cap, cfg0 = 300, cfg
    if order.get('side') == 'sell':   # 🚪 an exit that already failed on slippage gets more room and any route
        s0_, slip_cap, wide_ = rs._fw.sell_escalation(rs._fw_peek().get('ledger'), tid, order.get('mint'), now, cfg['slippageBps'])
        if wide_:
            cfg = {**cfg, 'slippageBps': s0_}; order = {**order, 'wide': True}
    elif order.get('side') == 'buy':   # 🚪 a buy that just failed on slippage gets a little more room (≤ 5%; the price-gap check still runs)
        s0_, slip_cap = rs._fw.buy_escalation(rs._fw_peek().get('ledger'), tid, order.get('mint'), now, cfg['slippageBps'])
        cfg = {**cfg, 'slippageBps': s0_}
    row = {**order, 'card': tid, 'liq': liq, 'status': 'quoted'}
    if order.get('side') == 'buy':
        # FINAL BUY GATE: cached radar liquidity is never authority for real money.
        # Re-fetch this exact pair immediately before quote/sign and fail closed if it cannot be verified.
        try:
            live_pair = (await rs._fw_live_pairs([order])).get(order.get('pair'))   # 📡 fresh: DexScreener, else Jupiter
            ok_live, why_live, snap = rs._fw.live_buy_market(order, live_pair, cfg)
        except Exception:
            ok_live, why_live, snap = False, 'live market unavailable — buy refused', {}
        row.update(snap)
        if not ok_live:
            row.update(status='skipped', err=why_live)
            async with rs._fw_lock:
                d = rs._fw_load()
                if not rs._fw.logged_recently(d.get('ledger'), row, now):
                    rs._fw_record(d, row)
                    rs._fw_save(d)
            return book
    async with rs._fw_lock:   # 🚦 limits a quote can't change (armed · paused · per-swap · daily cap · thin pool) are checked BEFORE quoting:
        d = rs._fw_load()        # no Jupiter calls, and the skip is booked once per 15 min instead of every tick (the cap retry loop)
        ok, why = rs._fw.check(row, cfg, d.get('ledger'), now)
        if not ok:
            skip = {**row, 'card': tid, 'status': 'skipped', 'err': why}
            if not rs._fw.logged_recently(d.get('ledger'), skip, now):
                rs._fw_record(d, skip); rs._fw_save(d)
            return book
    try:
        for attempt in range(3):   # 🔁 strong retry: a busy route gets fresh quotes, each with a little more slippage (≤ the 3% hard cap)
            try:
                q = await rs._fw_quote(order, {**cfg, 'slippageBps': min(max(300, slip_cap), int(cfg['slippageBps']) + 75 * attempt)})
                q_at = rs.time.time()
                break
            except rs.HTTPException:
                if attempt == 2:
                    raise
                await rs.asyncio.sleep(1.5)
        row['impactPct'] = round(rs._fuse._f(q.get('priceImpactPct')) * 100, 3); row['quoteOut'] = q.get('outAmount')
        if order['side'] == 'sell':   # 💧 what selling really pays → the card's value (a drained pool must not read as money); the pass saves `book`
            rs._fw.note_sell_quote(book, order, q.get('outAmount'), sol_px, now, row['impactPct'])
        if order['side'] == 'buy':   # 🛡 secure buy: near market price + it really sells back (both read-only quotes)
            ok_s, why_s, row['sellBackPct'] = await rs._fw_secure_buy(order, cfg, q)
            if not ok_s:
                raise rs.HTTPException(400, why_s)
        elif order['side'] == 'sell' and 'rug' not in str(order.get('why') or ''):   # 🛡 secure sell: the route must pay near the market price
            try:
                jp = rs._fuse._f(((await rs._jup_prices([order['mint']], keyed=True)) or {}).get(order['mint']))
            except Exception:
                jp = 0.0
            ok_s, why_s = rs._fw.sell_safety(order, q.get('outAmount'), sol_px, jp)
            if not ok_s:
                raise rs.HTTPException(400, why_s)
    except rs.HTTPException as e:
        row.update(status='skipped', err=str(e.detail)[:140])
        if order['side'] == 'sell' and 'no route' in str(e.detail).lower() and not row.get('quoteOut'):   # no route at all = worth nothing now
            rs._fw.note_sell_quote(book, order, 0, sol_px, now)
        async with rs._fw_lock:   # the same refusal is booked once per 15 min (the keeper keeps retrying quietly)
            d = rs._fw_load()
            if row.get('side') == 'buy' or not rs._fw.logged_recently(d.get('ledger'), row, now):   # buy misses all count (2 → benched)
                rs._fw_record(d, row); rs._fw_save(d)
        return book
    async with rs._fw_lock:
        ok, why = rs._fw.check(row, cfg, rs._fw_peek().get('ledger'), now, row['impactPct'])   # row carries the pool's liquidity
    if not ok or not rs._fw_signer_ready():
        row.update(status='skipped' if not ok else 'dry', err=why or 'signing not available — quoted only')
        async with rs._fw_lock:
            d = rs._fw_load(); rs._fw_record(d, row); rs._fw_save(d)
        return book
    if rs._fw.quote_stale(q_at, rs.time.time(), order):   # ⏱ the safety quotes took time: never build a tx on a quote older than its TTL
        try:
            q = await rs._fw_quote(order, cfg); q_at = rs.time.time(); row['quoteRefresh'] = 1
            row['impactPct'] = round(rs._fuse._f(q.get('priceImpactPct')) * 100, 3); row['quoteOut'] = q.get('outAmount')
            if order['side'] == 'buy':   # a fresh buy quote is checked again (near market + sells back) — safety never skipped for speed
                ok_s, why_s, row['sellBackPct'] = await rs._fw_secure_buy(order, cfg, q)
                if not ok_s:
                    raise rs.HTTPException(400, why_s)
        except rs.HTTPException as e:
            row.update(status='skipped', err=f'fresh quote: {str(e.detail)[:120]}')
            async with rs._fw_lock:
                d = rs._fw_load()
                if not rs._fw.logged_recently(d.get('ledger'), row, now):
                    rs._fw_record(d, row); rs._fw_save(d)
            return book
    async with rs._fw_lock:   # ⚡ txs that didn't land lately → this one pays a higher priority fee (24% of buys timed out at a flat fee)
        boost = rs._fw.landing_boost(rs._fw_peek().get('ledger'), tid, now)
    urgent_ = order.get('side') == 'sell' and rs._fw.urgent_order(order)   # ⚡ a stop / rug / drain / flow exit lands first (≤ 1% of the sale, ≤ half a cent)
    try:
        for attempt in range(3):   # build + sign retried too (Jupiter / Circle blips); nothing is sent until a signed tx exists
            try:
                swap = await rs._fw_jup('POST', '/swap/v1/swap', json={'quoteResponse': q, 'userPublicKey': cfg['address'], 'wrapAndUnwrapSol': True, 'dynamicComputeUnitLimit': True,
                                                                    'prioritizationFeeLamports': {'priorityLevelWithMaxLamports': {'maxLamports': rs._fw.priority_cap(attempt, boost, sol_px, rs._fuse._f(order.get('usd')) if urgent_ else 0.0), 'priorityLevel': 'veryHigh' if attempt or boost or urgent_ else 'high'}}})
                row['lastValidBlockHeight'] = swap.get('lastValidBlockHeight'); row['quoteAgeSec'] = round(rs.time.time() - q_at, 2)
                signed = await rs._fw_sign(cfg, swap.get('swapTransaction'), f"FEELESS {tid} {order['side']} {order.get('symbol')}")
                break
            except rs.HTTPException:
                if attempt == 2:
                    raise
                await rs.asyncio.sleep(1.5)
                q = await rs._fw_quote(order, cfg); q_at = rs.time.time()   # fresh quote for the rebuild
    except rs.HTTPException as e:
        row.update(status='failed', err=f'build/sign: {str(e.detail)[:120]}')
        async with rs._fw_lock:
            d = rs._fw_load(); rs._fw_record(d, row); rs._fw_save(d)
        rs._fw_notify(row)
        return book
    for slip_try in range(3):   # price moved past slippage at send time (Jupiter 0x1771) → fresh quote with a bit more room, ≤ 3%
        sig = signed.get('signature') or signed.get('txHash')
        book = {**book, 'pending': {**row, 'sig': sig, 'status': 'sent', 'sentAt': now}}
        async with rs._fw_lock:   # pending is saved BEFORE the send: a crash mid-flight can never double-buy
            d = rs._fw_load(); d['books'][tid] = rs._fw_keep(d, tid, book); rs._fw_save(d)
        try:
            async with rs.httpx.AsyncClient(timeout=15) as http:
                await rs._krpc(http, 'sendTransaction', [signed.get('signedTransaction'), {'encoding': 'base64', 'maxRetries': 3, 'preflightCommitment': 'confirmed'}])
            rs._fw_raw_keep(sig, signed.get('signedTransaction'))   # 📡 passed simulation → re-sent to every node until it lands or expires
            break
        except Exception as e:
            msg = str(e)
            if 'simulation failed' not in msg.lower():
                rs._fw_raw_keep(sig, signed.get('signedTransaction'))   # node trouble, not a bad tx → the other nodes still get it
                print('fuse wallet send:', msg[:200]); break   # network trouble: the tx may still land → resolve decides
            # simulation failed = this tx can NEVER land → clear pending now (no 2-min wait), maybe retry with more slippage
            book = {**book, 'pending': None}
            async with rs._fw_lock:
                d = rs._fw_load(); d['books'][tid] = rs._fw_keep(d, tid, book); rs._fw_save(d)
            slip = rs._fw.retry_slip(order['side'], slip_cap, cfg['slippageBps'], slip_try)   # a BUY retry opens to 5% max, first try stays normal
            if ('0x1771' not in msg and '6001' not in msg) or slip_try >= rs._fw.slip_retries(order['side']):   # a buy: ONE retry at 5% · a sell: two
                row.update(status='failed', err=('slippage exceeded at send' if ('0x1771' in msg or '6001' in msg) else 'simulation failed') + f' (tried ≤{slip / 100:.2f}%)')
                async with rs._fw_lock:
                    d = rs._fw_load(); rs._fw_record(d, row); rs._fw_save(d)
                rs._fw_notify(row)
                return book
            try:
                q = await rs._fw_quote(order, {**cfg, 'slippageBps': slip})
                swap = await rs._fw_jup('POST', '/swap/v1/swap', json={'quoteResponse': q, 'userPublicKey': cfg['address'], 'wrapAndUnwrapSol': True, 'dynamicComputeUnitLimit': True,
                                                                    'prioritizationFeeLamports': {'priorityLevelWithMaxLamports': {'maxLamports': rs._fw.priority_cap(slip_try + 1, boost, sol_px), 'priorityLevel': 'veryHigh'}}})
                row['lastValidBlockHeight'] = swap.get('lastValidBlockHeight')
                signed = await rs._fw_sign(cfg, swap.get('swapTransaction'), f"FEELESS {tid} {order['side']} {order.get('symbol')} retry")
                row['retrySlipBps'] = slip
            except rs.HTTPException as e2:
                row.update(status='failed', err=f'retry build/sign: {str(e2.detail)[:100]}')
                async with rs._fw_lock:
                    d = rs._fw_load(); rs._fw_record(d, row); rs._fw_save(d)
                return book
    book = await rs._fw_resolve(tid, book, cfg, sol_px, wait=40)
    # 🔁 SLIPPAGE = RETRY NOW, not "give the seat away": the price ran between the quote and the block (Jupiter 0x1771). The same
    # order goes again at once — fresh quote, more room (`buy_escalation` / `sell_escalation`), every live-pool / limit / secure-buy
    # check again — up to `SLIP_RETRIES` times. Before, one such failure re-picked the owner's seat 15s later ($FLY, $LOOP).
    n_ = int(order.get('slipRetry') or 0)
    if not book.get('pending') and order.get('side') in ('buy', 'sell') and n_ < rs._fw.slip_retries(order['side']):
        last_ = next((r for r in reversed(rs._fw_peek().get('ledger') or []) if r.get('id') == row.get('id')), None)
        if last_ and last_.get('status') == 'failed' and rs._fw.SLIP_ERR in str(last_.get('err') or ''):
            base_id = order.get('baseId') or order.get('id') or f"{tid}:{order.get('mint')}"
            return await rs._fw_execute(tid, {**order, 'baseId': base_id, 'id': f'{base_id}:r{n_ + 1}', 'slipRetry': n_ + 1}, book, cfg0, sol_px, liq)
    return book


async def _fw_execute_swap(tid, sell, buy, book, cfg, sol_px, liq):
    """🔀 ONE transaction: the old coin straight into the new one. Decided BEFORE anything moves — three read-only quotes (old → SOL,
    SOL → new, old → new); the one-step route is used only when it delivers at least as many coins as the two swaps would and its
    impact is ≤ 4% (`fuse_wallet.c2c_ok`), the new coin passes the live-pool, limit and secure-buy checks, and the old coin's sale
    is near market. Returns the book when a swap was sent (or settled); None = not suitable → the keeper does the two swaps."""
    rs = _rs()
    if book.get('pending') or not rs._fw_signer_ready():
        return None
    now = rs.time.time()
    d0 = rs._fw_load()
    if any(r.get('card') == tid and r.get('side') == 'swap' and r.get('status') == 'failed' and now - rs._fuse._f(r.get('at')) < rs.C2C_COOL_SEC for r in (d0.get('ledger') or [])[-40:]):
        return None
    brow = {**buy, 'usd': sell['usd'], 'liq': liq, 'card': tid}
    try:
        live_pair = (await rs._fw_live_pairs([buy])).get(buy.get('pair'))
        ok, _why, snap = rs._fw.live_buy_market(buy, live_pair, cfg)
        brow.update(snap)
        if ok:
            ok, _why = rs._fw.check(brow, cfg, d0.get('ledger'), now)
        if not ok:
            return None   # the normal path books the refusal (and benches the coin)
        q_sell = await rs._fw_quote(sell, cfg)
        lam = int(rs._fuse._f(q_sell.get('outAmount')))
        if lam <= 0:
            return None
        q_buy = await rs._fw_quote({**buy, 'lamports': lam}, cfg)
        q_dir = await rs._fw_jup('GET', '/swap/v1/quote', params={'inputMint': sell['mint'], 'outputMint': buy['mint'], 'amount': str(sell['atoms']),
                                                               'slippageBps': str(cfg['slippageBps']), 'restrictIntermediateTokens': 'true'})
        impact = round(rs._fuse._f(q_dir.get('priceImpactPct')) * 100, 3)
        ok, why = rs._fw.c2c_ok(q_dir.get('outAmount'), q_buy.get('outAmount'), impact)
        if not ok or impact > cfg['maxImpactPct']:
            return None
        ok_s, _why_s, back = await rs._fw_secure_buy({**buy, 'lamports': lam}, cfg, q_dir)   # near market + really sells back
        if not ok_s:
            return None
        if 'rug' not in str(sell.get('why') or ''):
            jp = rs._fuse._f(((await rs._jup_prices([sell['mint']])) or {}).get(sell['mint']))
            if not rs._fw.sell_safety(sell, q_sell.get('outAmount'), sol_px, jp)[0]:
                return None
        async with rs._fw_lock:
            boost = rs._fw.landing_boost(rs._fw_peek().get('ledger'), tid, now)
        swap = await rs._fw_jup('POST', '/swap/v1/swap', json={'quoteResponse': q_dir, 'userPublicKey': cfg['address'], 'wrapAndUnwrapSol': True, 'dynamicComputeUnitLimit': True,
                                                            'prioritizationFeeLamports': {'priorityLevelWithMaxLamports': {'maxLamports': rs._fw.priority_cap(0, boost, sol_px), 'priorityLevel': 'veryHigh' if boost else 'high'}}})
        signed = await rs._fw_sign(cfg, swap.get('swapTransaction'), f"FEELESS {tid} swap {sell.get('symbol')} to {buy.get('symbol')}")
    except Exception as e:
        print('fuse wallet c2c (falling back to two swaps):', str(getattr(e, 'detail', e))[:120])
        return None
    sig = signed.get('signature') or signed.get('txHash')
    row = {'id': f"{tid}:{now:.0f}:x:{sell['mint'][:6]}", 'card': tid, 'side': 'swap', 'mint': sell['mint'], 'pair': sell.get('pair'), 'symbol': sell.get('symbol'),
           'atoms': int(sell['atoms']), 'decimals': sell.get('decimals'), 'toMint': buy['mint'], 'toPair': buy.get('pair'), 'toSymbol': buy.get('symbol'),
           'toMidPx': brow.get('midPx') or buy.get('midPx'), 'usd': sell['usd'], 'at': now, 'why': f'🔀 one transaction — {why}', 'liq': brow.get('liq'),
           'minIn': int(rs._fuse._f(q_dir.get('otherAmountThreshold'))), 'quoteOut': q_dir.get('outAmount'), 'impactPct': impact, 'sellBackPct': back,
           'lastValidBlockHeight': swap.get('lastValidBlockHeight'), **({'cardPays': True} if sell.get('cardPays') else {})}
    book = {**book, 'pending': {**row, 'sig': sig, 'status': 'sent', 'sentAt': now}}
    async with rs._fw_lock:   # pending is saved BEFORE the send: a crash mid-flight can never double-trade
        d = rs._fw_load(); d['books'][tid] = rs._fw_keep(d, tid, book); rs._fw_save(d)
    try:
        async with rs.httpx.AsyncClient(timeout=15) as http:
            await rs._krpc(http, 'sendTransaction', [signed.get('signedTransaction'), {'encoding': 'base64', 'maxRetries': 3, 'preflightCommitment': 'confirmed'}])
        rs._fw_raw_keep(sig, signed.get('signedTransaction'))
    except Exception as e:
        if 'simulation failed' in str(e).lower():   # this tx can never land → clear it now; the two-step path takes over next tick
            book = {**book, 'pending': None}
            async with rs._fw_lock:
                d = rs._fw_load(); d['books'][tid] = rs._fw_keep(d, tid, book)
                rs._fw_record(d, {**row, 'status': 'failed', 'err': 'one-transaction swap failed simulation — doing two swaps'}); rs._fw_save(d)
            return book
        rs._fw_raw_keep(sig, signed.get('signedTransaction'))   # node trouble: it may still land → resolve decides
    return await rs._fw_resolve(tid, book, cfg, sol_px, wait=40)


def _fw_notify(row):
    """Every real fill / failure on a tier card → the owner wallets' inbox (audit trail link). No P&L in the text.
    A failing coin retries every tick, so its failure notice goes out once an hour, not once per try."""
    rs = _rs()
    once = f"fw-{row.get('id')}-{row.get('status')}" if row.get('status') != 'failed' else f"fw-fail-{row.get('card')}-{row.get('mint')}-{int(rs.time.time() // 3600)}"
    word = {'filled': '✅', 'failed': '⚠'}.get(row.get('status'), 'ℹ')
    for w in rs._owner_wallets():
        rs.notify(w, 'fuse-card', f"{word} Fuse wallet · {row.get('card')}: {row.get('side')} ${row.get('symbol') or ''} {row.get('status')}{(' — ' + row['err']) if row.get('err') else ''}",
               url='/terminal/hq?tab=fuse', push=False, once=once, meta={'claim': 'Keeper order', 'source': 'Fuse wallet audit trail'})


def _fw_raw_keep(sig, raw):
    rs = _rs()
    now = rs.time.time()
    for k in [k for k, v in rs._FW_RAW.items() if now - v[1] > 180]:
        rs._FW_RAW.pop(k, None)
    if sig and raw:
        rs._FW_RAW[sig] = (raw, now)


async def _fw_rebroadcast(http, sig):
    """📡 The perma-fix for "expired" buys / sells: the SAME signed tx goes to every RPC node again (one signature can only land once)."""
    rs = _rs()
    raw = (rs._FW_RAW.get(sig) or (None,))[0]
    if not raw or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return 0
    try:
        return await rs._rpc_broadcast(http, raw)
    except Exception:
        return 0


async def _fw_resolve(tid, book, cfg, sol_px, wait=0):
    """Settle a sent order from the chain. RPC absence is never failure: keep the pending lock until the chain returns a
    transaction, so a delayed buy/sell cannot be submitted twice. Only validated confirmed balance changes mutate the book."""
    rs = _rs()
    p = book.get('pending')
    if not p:
        return book
    tx = None
    async with rs.httpx.AsyncClient(timeout=15) as http:
        for _ in range(max(1, int(wait / 2))):
            try:
                tx = await rs._krpc(http, 'getTransaction', [p['sig'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
            except Exception:
                tx = None
            if tx:
                break
            await rs._fw_rebroadcast(http, p['sig'])
            if wait <= 0:
                break
            await rs.asyncio.sleep(2)
    if not tx:
        failed, chain_err = False, None
        try:
            async with rs.httpx.AsyncClient(timeout=15) as http:
                st = await rs._krpc(http, 'getSignatureStatuses', [[p['sig']], {'searchTransactionHistory': True}])
                status = ((st or {}).get('value') or [None])[0]
                failed = bool(status and status.get('err'))
                chain_err = status.get('err') if failed else None
                if not failed and p.get('lastValidBlockHeight') is not None:
                    height = await rs._krpc(http, 'getBlockHeight', [{'commitment': 'confirmed'}])
                    failed = int(height or 0) > int(p['lastValidBlockHeight'])
        except Exception:
            pass
        if not failed:
            return book   # unknown is not failed; retain the lock and retry the same signature next tick
        row = {k: v for k, v in p.items() if k != 'sentAt'}
        # two different problems, two different fixes: "expired" = never reached a block (landing) · "failed on-chain" = it ran and
        # reverted (price moved past slippage) — the audit trail now says which
        row.update(status='failed', err=(rs._fw.chain_err(chain_err) if rs._fw.SLIP_ERR in rs._fw.chain_err(chain_err) else f'failed on-chain: {str(chain_err)[:60]}') if chain_err else 'transaction expired — never landed')
        rs._FW_RAW.pop(p.get('sig'), None)
        book = {**book, 'pending': None}
        async with rs._fw_lock:
            d = rs._fw_load(); d['books'][tid] = rs._fw_keep(d, tid, book); rs._fw_record(d, row); rs._fw_save(d)
        rs._fw_notify(row)
        return book
    if p.get('side') == 'swap':   # 🔀 one transaction, two coins: booked as a sell row + a buy row on the same signature
        rs._FW_RAW.pop(p.get('sig'), None)
        base = {k: v for k, v in p.items() if k not in ('sentAt', 'toMidPx')}
        sfill = None if (tx.get('meta') or {}).get('err') else rs._fw.swap_fill_from_meta(tx, cfg['address'], p['mint'], p['toMint'])
        bad = rs._fw.swap_fill_error(p, sfill, book) if sfill else ''
        rows_ = []
        if sfill and not bad:
            try:
                px_in = rs._fuse._f(((await rs._jup_prices([p['toMint']])) or {}).get(p['toMint']))
            except Exception:
                px_in = 0.0
            book, f = rs._fw.apply_swap(book, p, sfill, sol_px, px_in or rs._fuse._f(p.get('toMidPx')))
            fee_usd = round(sfill['feeSol'] * sol_px, 6)
            rows_ = [{**base, 'id': p['id'] + ':s', 'side': 'sell', 'status': 'filled', 'usd': f['usd'], 'proceedsUsd': f['usd'], 'costUsd': f['costUsd'], 'realizedPnlUsd': f['realizedPnlUsd'],
                      'units': f['unitsOut'], 'sol': 0.0, 'feeSol': sfill['feeSol'], 'feeUsd': fee_usd, 'openedSol': 0.0, 'why': f"🔀 swapped straight into ${p.get('toSymbol')} (one transaction)"},
                     {**base, 'id': p['id'] + ':b', 'side': 'buy', 'mint': p['toMint'], 'pair': p.get('toPair'), 'symbol': p.get('toSymbol'), 'status': 'filled', 'usd': f['usd'],
                      'units': f['unitsIn'], 'px': f['px'], 'sol': 0.0, 'feeSol': 0.0, 'feeUsd': 0.0, 'why': f"🔀 swapped straight from ${p.get('symbol')} (one transaction)"}]
            rs._FW_GAS['at'] = 0.0; rs._FW_BAL.pop('bal', None)
        elif bad:
            rows_ = [{**base, 'status': 'failed', 'err': bad}]
            book = {**book, 'halt': True, 'haltWhy': bad}
        else:
            rows_ = [{**base, 'status': 'failed', 'err': rs._fw.chain_err((tx.get('meta') or {}).get('err'))}]
        book = {**book, 'pending': None}
        async with rs._fw_lock:
            d = rs._fw_load(); d['books'][tid] = rs._fw_keep(d, tid, book)
            for r_ in rows_:
                rs._fw_record(d, r_)
            rs._fw_save(d)
        rs._fw_notify(rows_[0])
        return book
    fill = rs._fw.fill_from_meta(tx, cfg['address'], p['mint']) if tx else None
    rs._FW_RAW.pop(p.get('sig'), None)
    row = {k: v for k, v in p.items() if k != 'sentAt'}
    mismatch = rs._fw.fill_error(p, fill, book) if not ((tx.get('meta') or {}).get('err')) else ''
    if fill and not mismatch:
        if p.get('side') == 'sell':   # 🧾 use the confirmed token debit, never the requested/quoted amount
            row['costUsd'] = rs._fw.cost_of(book, p['mint'], abs(int(fill.get('atoms') or 0)))
        book, f = rs._fw.apply_fill(book, p, fill, sol_px)
        row.update(status='filled', px=f['px'], units=f['units'], usd=f['usd'] or row['usd'], sol=f['sol'], feeSol=fill['feeSol'], feeUsd=round(fill['feeSol'] * sol_px, 6),
                   openedSol=rs._fuse._f(fill.get('openedSol')))
        if p.get('sentAt'):
            row['landSec'] = round(max(0.0, rs.time.time() - rs._fuse._f(p['sentAt'])), 1)   # 📮 send → booked from the chain (the Courier's landing time)
            row['sentAt'], row['confirmedAt'] = round(rs._fuse._f(p['sentAt']), 2), round(rs.time.time(), 2)   # 📏 order submitted · fill confirmed (kernel timings)
        if p.get('side') == 'sell':
            row.update(proceedsUsd=f['usd'], realizedPnlUsd=round(f['usd'] - row['costUsd'], 6))
        # The cached wallet balance predates this confirmed fill. Force the keeper's
        # post-tick balance read so a sold token cannot remain displayed as recoverable.
        rs._FW_GAS['at'] = 0.0
        rs._FW_BAL.pop('bal', None)
    elif mismatch:
        row.update(status='failed', err=mismatch)
        book = {**book, 'halt': True, 'haltWhy': mismatch}
    else:
        row.update(status='failed', err=rs._fw.chain_err((tx.get('meta') or {}).get('err')))
    book = {**book, 'pending': None}
    async with rs._fw_lock:
        d = rs._fw_load(); d['books'][tid] = rs._fw_keep(d, tid, book); rs._fw_record(d, row); rs._fw_save(d)
    rs._fw_notify(row)
    return book


def _fw_catch_up():
    """⚡ DECISIONS DON'T WAIT FOR THE NEXT TRIGGER. A keeper pass sends its orders one at a time and waits for each to confirm
    (2026-10-13: a median 24s each), so a pass with three orders runs well over a minute — and every decision made meanwhile (a
    stop, a filled seat) used to be SKIPPED until some later trigger: decision → send was a median 89s, 5 min at the slow end, and
    the price had moved 15%+ by the fill. Now a request that found the keeper busy runs ONE pass as soon as the running one ends.
    Still one pass at a time (`_fw_tick_lock`), still sells first, nothing about an order changes."""
    rs = _rs()
    if rs._FW_AGAIN.get('at') and not rs._fw_tick_lock.locked() and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        rs._FW_AGAIN['at'] = 0.0
        rs._fw_kick_now()


async def _fw_tick(now):
    """ONE keeper at a time: the round bell and the warm loop both call this after their tier tick — two keepers at once traded the
    same orders twice (sold WETH ×2, bought SPEC ×2 at 14:56). A tick that finds one running skips; the next tick catches up."""
    rs = _rs()
    if not rs._is_keeper():
        return 0
    if rs._fw_tick_lock.locked():
        rs._FW_AGAIN['at'] = rs.time.time()   # ⚡ asked for while a pass was running → ONE more pass the moment it ends (below)
        return 0
    async with rs._fw_tick_lock:
        rs._FW_AGAIN['at'] = 0.0
        n = await rs._fw_tick_inner(now)
        if rs.time.time() - rs._FW_GAS.get('at', 0) > 60:   # ⛽ one balance read a minute (never per viewer)
            try:
                cfg = rs._fw_cfg()
                if cfg.get('address'):
                    bal = await rs._fw_balances(cfg['address'])
                    rs._FW_GAS.update(sol=bal['sol'], at=rs.time.time()); rs._FW_BAL.update(bal=bal, at=rs.time.time(), addr=cfg['address'])
                    owed_in_done = {}
                    async with rs._fw_lock:   # 🧹 adopt keeper coins no card books (they sell back to SOL inside their card next tick)
                        d = rs._fw_load()
                        missing = rs._fw.reconcile(bal.get('tokens'), d['books'])
                        sol_short = rs._fw.reconcile_sol(bal.get('sol'), d['books'])
                        if missing:   # a SMALL shortage (rounding, transfer tax): the book follows the wallet, no halt; a big one still halts
                            d['books'], fits = rs._fw.fit_small_shortage(d['books'], missing)
                            for ft in fits:
                                rs._fw_record(d, {'id': f"fit:{ft['card']}:{ft['mint'][:6]}:{rs.time.time():.0f}", 'card': ft['card'], 'side': 'fix', 'mint': ft['mint'], 'symbol': ft['symbol'], 'at': rs.time.time(), 'status': 'done',
                                               'why': f"📏 book matched to the wallet: ${ft['symbol']} {ft['pct']:.2f}% fewer coins than booked (rounding / transfer tax) — the wallet is the truth"})
                            missing = rs._fw.reconcile(bal.get('tokens'), d['books'])
                        if missing:   # 👻 a shortage that is EXACTLY a confirmed sale the book missed: the wallet is the truth, no halt
                            d['books'], missed_ = rs._fw.fit_missed_sells(d['books'], missing, d.get('ledger') or rs._fw_full_ledger(), rs.time.time())
                            for ms_ in missed_:
                                rs._fw_record(d, {'id': f"missed:{ms_['card']}:{ms_['mint'][:6]}:{rs.time.time():.0f}", 'card': ms_['card'], 'side': 'fix', 'mint': ms_['mint'], 'symbol': ms_['symbol'], 'at': rs.time.time(), 'status': 'done',
                                               'why': f"📏 book matched to the wallet: a confirmed sale of {ms_['sold'] / 10 ** (ms_['decimals'] or 0):g} ${ms_['symbol']} ({str(ms_['sig'] or '')[:8]}…) was never taken off the book — its SOL was already in the card; no halt"})
                            if missed_:
                                missing = rs._fw.reconcile(bal.get('tokens'), d['books'])
                        if missing:   # 👻 a $0-cost leftover the wallet holds none of was already sold — off the book, no halt
                            d['books'], ghosts = rs._fw.drop_phantoms(d['books'], missing)
                            for gh in ghosts:
                                rs._fw_record(d, {'id': f"ghost:{gh['card']}:{gh['mint'][:6]}:{rs.time.time():.0f}", 'card': gh['card'], 'side': 'fix', 'mint': gh['mint'], 'symbol': gh['symbol'], 'at': rs.time.time(), 'status': 'done',
                                               'why': f"👻 ${gh['symbol']} was booked as a leftover but the wallet holds none — already sold; off the book ($0 cost, P&L unchanged)"})
                            missing = rs._fw.reconcile(bal.get('tokens'), d['books'])
                        if sol_short and not any(b.get('pending') or b.get('defund') for b in d['books'].values()):   # ⛽ a gas-sized SOL gap: the cards paid the fees, no halt
                            d['books'], gas_ = rs._fw.fit_gas_shortage(d['books'], sol_short)
                            for tid, sol_ in gas_.items():
                                rs._fw_record(d, {'id': f'gasfit:{tid}:{rs.time.time():.0f}', 'card': tid, 'side': 'fix', 'sol': sol_, 'at': rs.time.time(), 'status': 'done',
                                               'why': f"⛽ the gas reserve ran dry — the card paid {sol_:.6f} SOL of network fees / rent (booked as fees, P&L unchanged); top up the reserve to stop this"})
                            if gas_:
                                sol_short = rs._fw.reconcile_sol(bal.get('sol'), d['books'])
                        if missing or sol_short:   # confirmed wallet balances beat our books; stop every affected card before another order
                            bad = {x['mint'] for x in missing}
                            for tid, b in d['books'].items():
                                if sol_short or bad.intersection((b.get('legs') or {})):
                                    why = 'confirmed wallet SOL is below card books' if sol_short else 'confirmed wallet token balance is below card books'
                                    d['books'][tid] = {**b, 'halt': True, 'haltWhy': why}
                        for tid, b in list(d['books'].items()):   # 🔓 an automatic halt lifts once the wallet shows it's fixed
                            if rs._fw.halt_cleared(b, sol_short, [x['mint'] for x in missing]):
                                d['books'][tid] = {**b, 'halt': False, 'haltWhy': None}
                                rs._fw_record(d, {'id': f'unhalt:{tid}:{rs.time.time():.0f}', 'card': tid, 'side': 'fix', 'at': rs.time.time(), 'status': 'done',
                                               'why': f"🔓 resumed by itself — {b.get('haltWhy')} is fixed (wallet and card books match)"})
                        if not sol_short and not missing:   # 🏦 rent is the reserve's: old card-paid deposits go back to work in the card
                            d['books'], freed = rs._fw.release_rent_deposits(d['books'], rs._fw.free_sol(bal.get('sol'), d['books'], cfg.get('reserveSol')))
                            for tid, sol_ in freed.items():
                                rs._fw_record(d, {'id': f'rentfree:{tid}:{rs.time.time():.0f}', 'card': tid, 'side': 'fix', 'sol': sol_, 'at': rs.time.time(), 'status': 'done',
                                               'why': f'🏦 {sol_:.5f} SOL of coin-account rent moved to the wallet reserve — it is card cash again (the card never pays rent now)'})
                        # ↘ TOP-UPS THE BOOKS LOST come back from the wallet's free SOL (owner, 2026-10-07: "assign what's supposed to be
                        # in card and what's supposed to be in wallet"). Found once per book from the ledger (`lost_topups`), then
                        # credited as free SOL allows; the card's run baseline rises by the same $ (money in, not a gain).
                        if not sol_short and not missing:
                            for tid, b in list(d['books'].items()):
                                if not b.get('lostTopFix') and not b.get('pending') and not b.get('defund'):
                                    lost_ = rs._fw.lost_topups(b, rs._fw_full_ledger(), tid)
                                    b = d['books'][tid] = {**b, 'lostTopFix': rs.time.time(), **({'owedInSol': lost_['sol'], 'owedInUsd': lost_['usd']} if lost_ else {})}
                                    if lost_:
                                        rs._fw_record(d, {'id': f'losttop:{tid}', 'card': tid, 'side': 'fix', 'sol': lost_['sol'], 'usd': lost_['usd'], 'at': rs.time.time(), 'status': 'done',
                                                       'why': f"↘ ${lost_['usd']:.2f} of your top-ups ({len(lost_['rows'])}) never reached this card's books (a save bug, fixed) — it is being put into the card from the wallet's unassigned SOL"})
                                free_in = rs._fw.free_for_owed(bal.get('sol'), d['books'], cfg.get('reserveSol'), rs._fuse._f((rs._fw_rent_parked or {}).get('sol')))
                                nb_, in_sol, in_usd = rs._fw.settle_owed_in(b, free_in, rs.time.time()) if not b.get('pending') else (b, 0.0, 0.0)
                                if in_sol > 0:
                                    d['books'][tid] = nb_; owed_in_done[tid] = owed_in_done.get(tid, 0.0) + in_usd
                                    rs._fw_record(d, {'id': f'owedin:{tid}:{rs.time.time():.0f}', 'card': tid, 'side': 'fix', 'sol': in_sol, 'usd': in_usd, 'at': rs.time.time(), 'status': 'done',
                                                   'why': f"↘ {in_sol:.5f} SOL (${in_usd:.2f}) of a lost top-up is in the card now — PUT IN ${rs._fuse._f(nb_.get('fundedUsd')):.2f} ({rs._fuse._f(nb_.get('owedInSol')):.5f} SOL still to come as wallet SOL frees up)"})
                        for tid, b in list(d['books'].items()):   # ↗ money that is not the card's leaves as card cash appears
                            nb_, out_ = rs._fw.settle_owed(b)
                            if out_ > 0 and not b.get('pending'):
                                d['books'][tid] = nb_
                                rs._fw_record(d, {'id': f'owedout:{tid}:{rs.time.time():.0f}', 'card': tid, 'side': 'fix', 'sol': out_, 'at': rs.time.time(), 'status': 'done',
                                               'why': f"↗ {out_:.5f} SOL that was never put into this card is unassigned wallet SOL again ({rs._fuse._f(nb_.get('owedOutSol')):.5f} SOL still to move)"})
                        for st in rs._fw.strays(bal.get('tokens'), bal.get('decimals'), d['books'], d['ledger'], rs.time.time()):
                            d['books'][st['card']] = rs._fw.adopt(d['books'][st['card']], st)
                            rs._fw_record(d, {'card': st['card'], 'side': 'adopt', 'mint': st['mint'], 'symbol': st['symbol'], 'atoms': st['atoms'], 'usd': 0.0, 'at': rs.time.time(),
                                           'status': 'done', 'why': '🧹 recovered: keeper coins no card counted — sold back to SOL inside the card'})
                            print(f"fuse wallet: adopted stray {st['symbol']} into {st['card']}")
                        rs._fw_save(d)
                    if owed_in_done:   # the card's run baseline rises by the money that came in (it is not a gain)
                        async with rs._admin_lock:
                            h = rs._json_load(rs.FUSE_HQ_PATH, {})
                            for tid_, usd_ in owed_in_done.items():
                                cd = ((h.get('prime') or {}).get('cards') or {}).get(tid_)
                                if cd and cd.get('real'):
                                    for k_ in ('startUsd', 'dayStartUsd', 'roundStartUsd'):
                                        cd[k_] = round(rs._fuse._f(cd.get(k_)) + usd_, 4)
                                    cd['events'] = list(cd.get('events') or []) + [{'at': rs.time.time(), 'kind': 'topup', 'usd': round(usd_, 4), 'to': ['card'],
                                        'why': f"↘ ${usd_:.2f} of a top-up the books had lost is in the card now — baseline raised by the same $ (money in, not a gain)"}]
                            rs._json_save(rs.FUSE_HQ_PATH, h)
                    await rs._fw_deposit_scan(cfg, rs.time.time())
                    rs._rpc_quota_notice()
            except Exception as e:
                print('fuse wallet gas:', e)
        if rs._FW_AGAIN.get('at'):
            rs.asyncio.get_event_loop().call_soon(rs._fw_catch_up)   # runs once this pass has let go of the lock
        return n


async def _fw_deposit_scan(cfg, now):
    """💰 Every 10 min: new signatures on the Fuse wallet that the keeper did NOT make are read once; a tx the wallet did not sign that
    raised its SOL is a DEPOSIT (booked forever + owner inbox). This is what makes "unassigned SOL" explainable instead of a mystery."""
    rs = _rs()
    if now - rs._fw_dep_at['t'] < 600 or not cfg.get('address'):
        return 0
    rs._fw_dep_at['t'] = now
    dd = rs._json_load(rs.FUSE_DEPOSITS_PATH, {})
    if dd.get('address') != cfg['address']:
        dd = {'address': cfg['address'], 'cursor': None, 'rows': []}
    ours = {r.get('sig') for r in rs._fw_peek().get('ledger') or [] if r.get('sig')}
    added = 0
    async with rs.httpx.AsyncClient(timeout=15) as http:
        sigs = await rs._krpc(http, 'getSignaturesForAddress', [cfg['address'], {'limit': 40, **({'until': dd['cursor']} if dd.get('cursor') else {})}]) or []
        have = {r.get('sig') for r in dd['rows']}
        for srow in sigs[::-1]:   # oldest first
            sig = srow.get('signature')
            if not sig or srow.get('err') or sig in ours or sig in have:
                continue
            tx = await rs._krpc(http, 'getTransaction', [sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
            dep = rs._fw.deposit_from_tx(tx, cfg['address'])
            if dep:
                dd['rows'].append({'sig': sig, 'at': (tx or {}).get('blockTime') or now, **dep}); added += 1
                for w in rs._owner_wallets():
                    rs.notify(w, 'fuse-card', f"💰 Fuse wallet received {dep['sol']:.4f} SOL — it is UNASSIGNED until you put it in a card.", url='/terminal/hq?tab=fuse',
                           push=False, once=f'fw-dep-{sig[:16]}', meta={'claim': 'Deposit', 'source': 'Confirmed on-chain transfer'})
    if sigs:
        dd['cursor'] = sigs[0].get('signature')
    if sigs or added:
        rs._json_save(rs.FUSE_DEPOSITS_PATH, dd)
    return added


async def _fw_tick_inner(now):
    """After every tier tick: each funded card's REAL book is moved to what the engine says it holds (sells, then buys), then the
    card shows its true coins, entries and fees. Paused / unarmed / missing-coin cards wait. Paper learns from the fills."""
    rs = _rs()
    await rs._fw_signer_check()
    d = rs._fw_load()
    cal = rs._fw_calibration(d)
    rs._prime.IMPACT_MULT = cal['impactMult']; rs._prime.SPREAD = cal.get('spread') or 0.0
    cfg = rs._fw.clean_cfg(d.get('cfg') or {})
    if not d['books'] or not cfg['armed'] or cfg['paused'] or not cfg['address']:
        return 0
    hq = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (hq.get('prime') or {}).get('cards') or {}
    pairs_ = await rs._fuse_pairs([{'chainId': 'solana', 'pairAddress': pa} for tid, b in d['books'].items()
                                for pa in [l['pairAddress'] for l in (cards.get(tid) or {}).get('legs') or []] + [l.get('pair') for l in (b.get('legs') or {}).values() if l.get('pair')]])
    px = {k: rs._fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}
    jup = await rs._jup_prices([l.get('mint') for c in cards.values() for l in c.get('legs') or []] +
                            [m for b in d['books'].values() for m in (b.get('legs') or {})])
    for c in cards.values():
        for l in c.get('legs') or []:
            if jup.get(l.get('mint')):
                px[l['pairAddress']] = jup[l['mint']]
    for b in d['books'].values():
        for mint, l in (b.get('legs') or {}).items():
            if jup.get(mint) and l.get('pair'):
                px[l['pair']] = jup[mint]
    liqs = {k: rs._fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_.items()}
    sol_px = await rs._sol_usd_live()
    done = 0
    for tid, book in list(d['books'].items()):
        card = cards.get(tid)
        if not card or (book.get('halt') and not rs._fw.halt_allows_sells(book)):
            continue
        if book.get('pending'):
            book = await rs._fw_resolve(tid, book, cfg, sol_px)
            if book.get('pending'):
                continue
        equity_usd = rs._fw.book_value(book, px, sol_px)
        book, returned_sol = rs._fw.enforce_principal_floor(book, equity_usd, sol_px)
        if returned_sol > 0:
            equity_usd = rs._fw.book_value(book, px, sol_px)
        book = rs._fw.bank(book, card.get('walletUsd'), sol_px, equity_usd)
        want = {**card, 'legs': []} if book.get('defund') else card
        # 🔒 check the buy BEFORE the sell: a swap whose new coin can't be bought keeps the old coin (≤ 45s) while the engine re-picks
        plan0 = rs._fw.orders(tid, want, book, px, sol_px, cfg, now, count_sells=True)
        new_buys = [o for o in plan0 if o['side'] == 'buy' and not rs._fw.held_units(book, o['mint'])]
        hold = False
        # only a SWAP-OUT waits for its replacement — a cut of a coin that stays (bank at the lock, 💰 skim, ✂) never does
        swap_out = lambda o: o['side'] == 'sell' and not o.get('manualCash') and o.get('why') == 'not on the card any more'
        if new_buys and any(swap_out(o) for o in plan0) and not book.get('defund') and not book.get('halt'):
            book, hold = rs._fw.hold_sells(book, card, await rs._fw_preflight(tid, new_buys, cfg, now), now)
        elif book.get('sellHoldAt'):
            book, _h = rs._fw.hold_sells(book, card, set(), now)
        if cfg.get('coinToCoin') and not hold and not book.get('halt') and not book.get('defund') and not book.get('pending'):
            for s_o, b_o in rs._fw.swap_pairs(plan0, book)[:1]:   # 🔀 one swap per tick, like every other order
                leg_liq = next((rs._fuse._f(l.get('liqNow')) or rs._fuse._f(l.get('liq')) for l in card.get('legs') or [] if l.get('mint') == b_o.get('mint')), 0.0)
                done_ = await rs._fw_execute_swap(tid, {**s_o, 'cardPays': int(card.get('rounds') or 0) >= 5}, b_o, book, cfg, sol_px, liqs.get(b_o.get('pair')) or leg_liq)
                if done_ is not None:
                    book = done_
        drained_ = []
        for side in (('sell',) if book.get('halt') or book.get('pending') else ('sell', 'buy')):   # ⏸ halted = sells only (owner's queued sells still land)
            if side == 'buy':
                rs._FW_BUY_PASS[tid] = rs.time.time()   # ⏳ the keeper reached its buy step for this card (a coin wanted before `now` had its chance)
            for o in [rs._fw.mark_urgent({**x, 'cardPays': int(card.get('rounds') or 0) >= 5}, card, rs.time.time()) for x in rs._fw.orders(tid, want, book, px, sol_px, cfg, now, count_sells=side == 'sell') if x['side'] == side]:
                if hold and swap_out(o):
                    continue   # the replacement isn't buyable yet → this coin stays (cuts and the owner's own ✂ always go through)
                leg_liq = next((rs._fuse._f(l.get('liqNow')) or rs._fuse._f(l.get('liq')) for l in card.get('legs') or [] if l.get('mint') == o.get('mint')), 0.0)
                book = await rs._fw_execute(tid, o, book, cfg, sol_px, liqs.get(o.get('pair')) or leg_liq)   # pair read blank → the engine's own liquidity reading
                if book.get('pending'):
                    break
            if book.get('pending'):
                break   # one card, one in-flight transaction; a pending sell must never be overwritten by a buy
            if side == 'sell' and not book.get('pending'):
                # Confirmed sell proceeds fund payouts first. Paid-out SOL is segregated before any subsequent compound buys.
                equity_usd = rs._fw.book_value(book, px, sol_px)
                book, returned_sol = rs._fw.enforce_principal_floor(book, equity_usd, sol_px)
                if returned_sol > 0:
                    equity_usd = rs._fw.book_value(book, px, sol_px)
                book = rs._fw.bank(book, card.get('walletUsd'), sol_px, equity_usd)
                # 🔒 SELL-BEFORE-BUY BARRIER: if ANY sell is still required after the sell pass
                # (route refused, tx expired, partial max-swap chunk, etc.), do not buy anything yet.
                # The next keeper tick retries the remaining sell first. This prevents a failed sell
                # from leaving the old coin held while spare SOL buys its replacement too.
                book, dr_ = rs._fw.write_off_drained(book, [l.get('mint') for l in card.get('legs') or [] if not l.get('placeholder')], rs.time.time())
                drained_.extend(dr_)   # 🩸 a drained pool's leftovers leave the book — they must never hold the buys hostage
                remaining_sells = [x for x in rs._fw.orders(tid, want, book, px, sol_px, cfg, rs.time.time(), count_sells=True) if x['side'] == 'sell']
                if remaining_sells:
                    break
        written_off = []
        if book.get('defund') and not book.get('pending'):   # 🧹 a dead coin's dust can't be sold — it must not keep "selling…" on screen forever
            book, written_off = rs._fw.write_off_dust(book, px)
        async with rs._fw_lock:
            d2 = rs._fw_load()
            for w in drained_:
                rs._fw_record(d2, {'card': tid, 'side': 'writeoff', 'mint': w['mint'], 'pair': w.get('pair'), 'symbol': w['symbol'], 'usd': w['usd'], 'costUsd': w['costUsd'], 'at': now, 'status': 'done',
                                'why': f"drained pool written off: selling it all pays ${w['usd']:.4f} (cost ${w['costUsd']:.2f}) — the coins stay in the wallet, the keeper stops trying"})
            for w in written_off:
                rs._fw_record(d2, {'card': tid, 'side': 'writeoff', 'mint': w['mint'], 'pair': w.get('pair'), 'symbol': w['symbol'], 'usd': w['usd'], 'costUsd': w['costUsd'], 'at': now, 'status': 'done',
                                'why': f"dead coin written off: worth ${w['usd']:.4f} (cost ${w['costUsd']:.2f}) — too small for any route; the coins stay in the wallet"})
            if book.get('defund') and not book.get('legs') and not book.get('pending'):
                d2['books'].pop(tid, None)
                rs._fw_record(d2, {'card': tid, 'side': 'defund', 'usd': round(rs._fw.book_value(book, px, sol_px), 4), 'at': now, 'status': 'done'})
            else:
                d2['books'][tid] = rs._fw_keep(d2, tid, book)
            rs._fw_save(d2)
        async with rs._admin_lock:
            h = rs._json_load(rs.FUSE_HQ_PATH, {}); cs = (h.get('prime') or {}).get('cards') or {}
            if cs.get(tid):
                still_real = tid in rs._fw_peek()['books']
                was_label = cs[tid].get('label')
                cs[tid] = rs._fw.sync_card(cs[tid], book, px, sol_px) if still_real else rs._fw.back_to_paper(cs[tid], rs._fw.book_value(book, px, sol_px), now)
                rs._json_save(rs.FUSE_HQ_PATH, h)
                if not still_real and cs[tid].get('runs'):   # 📜 the sell-all IS the end of a real run — it goes on the permanent record
                    try:                                       # (the tier tick only records runs it ends itself, so this one was lost)
                        rs._store.Ledger(rs.CARD_RECORDS_PATH, table='runs').append({**cs[tid]['runs'][-1], 'card': tid, 'label': was_label, 'real': True, 'closed': True})
                    except Exception as e:
                        print('card records (defund):', e)
        done += 1
    await rs._fw_close_empty(cfg, now)
    return done


async def _fw_rent_credit(cfg):
    """♻ A CONFIRMED close puts its rent back into the card that opened those coin accounts (`fuse_wallet.rent_back`); a close that
    failed or never landed credits nothing. Each close is credited once (its 'credited' row)."""
    rs = _rs()
    d = rs._fw_load()
    if not d.get('rentFix1'):   # 🩹 undo the first rule's phantom credits (every historical refund was credited into the card again)
        sol_px0 = await rs._sol_usd_live()
        if sol_px0 <= 0:
            return
        async with rs._fw_lock:
            d = rs._fw_load()
            d['books'], gone = rs._fw.undo_rent_credits(d['books'], d['ledger'], sol_px0)
            bal_sol = rs._FW_GAS.get('sol')
            for tid, b in d['books'].items():   # the shortage that halted the card is gone → it may trade again (owner sees why)
                if b.get('halt') and 'below card books' in str(b.get('haltWhy') or '') and bal_sol is not None and not rs._fw.reconcile_sol(bal_sol, d['books']):
                    d['books'][tid] = {**b, 'halt': False, 'haltWhy': None}
            for tid, sol in gone.items():
                rs._fw_record(d, {'id': f'rentfix:{tid}', 'card': tid, 'side': 'fix', 'sol': -sol, 'usd': round(-sol * sol_px0, 4), 'at': rs.time.time(), 'status': 'done',
                               'why': '🩹 removed rent credited by mistake (old refunds the reserve had already re-used) — card books match the wallet again'})
            d['rentFix1'] = rs.time.time()
            rs._fw_save(d)
        if gone:
            rs._fw_notify({'card': next(iter(gone)), 'side': 'fix', 'status': 'done', 'usd': 0, 'why': 'rent credit mistake repaired — card books match the wallet again'})
    if not d.get('rentFix2'):   # 🩹 the first repair priced the removed SOL at today's price → PUT IN drifted (5.00 read 4.82): rebuild it
        async with rs._fw_lock:
            d = rs._fw_load()
            for tid, b in d['books'].items():
                if any(r.get('id') == f'rentfix:{tid}' for r in d['ledger']):
                    f_ = rs._fw.funded_from_ledger(b, rs._fw_full_ledger(), tid)
                    if f_ > 0:
                        d['books'][tid] = {**b, 'fundedUsd': f_}
            d['rentFix2'] = rs.time.time()
            rs._fw_save(d)
    if not d.get('routeFix1') and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        # 🩹 sells whose multi-hop route parked rent in accounts it opened were booked as price losses (baton −87%, ORCA −50%). That SOL
        # came back to the wallet when the accounts closed; it is the card's sale money → back into card cash, once, from the chain.
        try:
            found, checked = {}, {}
            sol_px0 = await rs._sol_usd_live()
            if sol_px0 <= 0:
                raise RuntimeError('no SOL price')
            async with rs.httpx.AsyncClient(timeout=20) as http:
                for r in rs._fw.route_fix_rows(d['ledger'], rs.time.time() - 3 * 86400)[-40:]:
                    tx = await rs._krpc(http, 'getTransaction', [r['sig'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
                    if not tx:
                        raise RuntimeError('tx not readable yet')
                    checked[r['sig']] = rs._fw.opened_sol(tx, cfg['address'])
                    await rs.asyncio.sleep(0.6)   # paced: this may run on public nodes
                    if checked[r['sig']] > 0:
                        found[r.get('card')] = round(found.get(r.get('card'), 0.0) + checked[r['sig']], 9)
            async with rs._fw_lock:
                d = rs._fw_load()
                bal_sol = rs._FW_GAS.get('sol')
                if found and bal_sol is None:
                    raise RuntimeError('wallet balance not read yet')
                d['books'], credits = rs._fw.route_fix(d['books'], found, rs._fw.free_sol(bal_sol, d['books'], cfg.get('reserveSol')) if found else 0.0, sol_px0)
                for r in d['ledger']:
                    if r.get('sig') in checked and r.get('side') == 'sell':
                        r['openedSol'] = checked[r['sig']]
                        if checked[r['sig']] > 0 and r.get('card') in credits:   # the trail shows the true price result of that sale
                            r['usd'] = r['proceedsUsd'] = round(rs._fuse._f(r.get('usd')) + checked[r['sig']] * sol_px0, 6)
                            r['realizedPnlUsd'] = round(r['usd'] - rs._fuse._f(r.get('costUsd')), 6)
                for tid, sol in credits.items():
                    rs._fw_record(d, {'id': f'routefix:{tid}', 'card': tid, 'side': 'fix', 'sol': sol, 'usd': round(sol * sol_px0, 4), 'at': rs.time.time(), 'status': 'done',
                                   'why': f'🩹 {sol:.5f} SOL of route rent was booked as a sale loss — it came back to the wallet and is back in this card'})
                if not found or credits:
                    d['routeFix1'] = rs.time.time()
                rs._fw_save(d)
            if credits:   # the run that restarted on the short value gets the same $ in its baseline: the money is back, it is not a gain
                async with rs._admin_lock:
                    h = rs._json_load(rs.FUSE_HQ_PATH, {}); cs = (h.get('prime') or {}).get('cards') or {}
                    for tid, sol in credits.items():
                        if cs.get(tid):
                            for k_ in ('startUsd', 'roundStartUsd', 'dayStartUsd'):
                                if cs[tid].get(k_) is not None:
                                    cs[tid][k_] = round(rs._fuse._f(cs[tid][k_]) + sol * sol_px0, 4)
                    rs._json_save(rs.FUSE_HQ_PATH, h)
            for tid in credits:
                rs._fw_notify({'card': tid, 'side': 'fix', 'status': 'done', 'usd': 0, 'why': 'route rent booked as a loss is back in the card'})
        except Exception as e:
            print('fuse wallet route fix (retries next sweep):', str(e)[:120])
    if not d.get('cashFix1'):   # 🩹 recovery sells used to park their SOL as "owner's held cash" (never re-spent) → back to work, once
        async with rs._fw_lock:
            d = rs._fw_load()
            for tid, b in d['books'].items():
                held = rs._fuse._f(b.get('manualCashSol'))
                if held > 0:
                    d['books'][tid] = {**b, 'manualCashSol': 0.0}
                    rs._fw_record(d, {'id': f'cashfix:{tid}', 'card': tid, 'side': 'fix', 'sol': held, 'at': rs.time.time(), 'status': 'done',
                                   'why': '♻ recovered-coin cash released — it trades in the card again (it was always counted in IN CARD)'})
            d['cashFix1'] = rs.time.time()
            rs._fw_save(d)
    if not d.get('thinPoolFix1'):
        # 💧 OWNER'S CALL (2026-10-08, "fix the coins coming in, the card is getting cooked"): once, the real-buy pool floors (general · Arena · pick) go up to $40K — see
        # fuse_wallet.THIN_POOL_FLOOR for the evidence. The old values are saved in data/fwcfg_before_thinpool.json; Edit Fuse › Limits changes them back any time.
        async with rs._fw_lock:
            d = rs._fw_load(); cfg0 = d.get('cfg') or {}; raised = rs._fw.thin_pool_cfg(cfg0)
            if raised:
                rs._json_save(rs.DATA_DIR / 'fwcfg_before_thinpool.json', {k: rs._fw.clean_cfg(cfg0).get(k) for k in raised})
                d['cfg'] = {**cfg0, **raised}
                rs._fw_record(d, {'id': 'thinpool:fix', 'card': 'wallet', 'side': 'fix', 'sol': 0.0, 'usd': 0.0, 'at': rs.time.time(), 'status': 'done',
                               'why': f"💧 real-buy pool floors raised to ${rs._fw.THIN_POOL_FLOOR:,.0f} ({', '.join(raised)}): 12 of the last day's 15 crashes were pools under $40K. Trench tickets keep their own floor."})
            d['thinPoolFix1'] = rs.time.time(); rs._fw_save(d)
    if not d.get('strayFix1'):
        # ↗ OWNER'S CALL (2026-10-05, "pull the 1.51 out, make this all true money"): the chain audit shows the degen book holding
        # 0.012552 SOL more than its own swaps explain — duplicate buys a second keeper process paid from UNASSIGNED wallet SOL.
        # It is owed out of the card (`fuse_wallet.settle_owed`), every coin is cut by the same share so the cash to move appears,
        # and the run baseline drops by the same $ (money out, not a loss). Once.
        try:
            sol_px_s = await rs._sol_usd_live()
            STRAY_SOL, STRAY_SINCE = 0.012552, 1791180297.888952
            async with rs._fw_lock:
                d = rs._fw_load(); b = d['books'].get('degen')
                hit = bool(b) and abs(rs._fuse._f(b.get('since')) - STRAY_SINCE) < 1 and not b.get('pending') and not b.get('defund') and sol_px_s > 0
                if hit:
                    gross = rs._fw.book_value(b, {}, sol_px_s)
                    d['books']['degen'] = {**b, 'owedOutSol': STRAY_SOL}
                    rs._fw_record(d, {'id': 'strayfix:degen', 'card': 'degen', 'side': 'fix', 'sol': STRAY_SOL, 'usd': round(STRAY_SOL * sol_px_s, 4), 'at': rs.time.time(), 'status': 'done',
                                   'why': f"↗ {STRAY_SOL} SOL (${STRAY_SOL * sol_px_s:.2f}) in this card was never put in by you (duplicate buys paid from unassigned wallet SOL) — it leaves the card; PUT IN stays ${rs._fuse._f(b.get('fundedUsd')):.2f}"})
                if hit or not b or abs(rs._fuse._f((b or {}).get('since')) - STRAY_SINCE) >= 1:
                    d['strayFix1'] = rs.time.time(); rs._fw_save(d)
            if hit:
                usd_s = STRAY_SOL * sol_px_s
                keep_s = max(0.05, min(1.0, (gross - usd_s) / gross)) if gross > 0 else 1.0
                async with rs._admin_lock:
                    h = rs._json_load(rs.FUSE_HQ_PATH, {}); cd = ((h.get('prime') or {}).get('cards') or {}).get('degen')
                    if cd and cd.get('real'):
                        for l in cd.get('legs') or []:
                            if rs._fuse._f(l.get('units')) > 0:
                                l['units'] = rs._fuse._f(l['units']) * keep_s; l['costUsd'] = round(rs._fuse._f(l.get('costUsd')) * keep_s, 6); l['trimAt'] = rs.time.time()
                        for k in ('startUsd', 'dayStartUsd', 'roundStartUsd'):
                            cd[k] = round(max(0.01, rs._fuse._f(cd.get(k)) - usd_s), 4)
                        cd['events'] = list(cd.get('events') or []) + [{'at': rs.time.time(), 'kind': 'brain', 'usd': round(usd_s, 4),
                            'why': f"↗ ${usd_s:.2f} that was never put into this card is leaving it — every coin cut to {keep_s * 100:.0f}%, baseline lowered by the same $ (not a loss)"}]
                        rs._json_save(rs.FUSE_HQ_PATH, h)
        except Exception as e:
            print('fuse wallet stray fix (retries next sweep):', str(e)[:120])
    done = {r.get('id') for r in d['ledger'] if r.get('side') == 'close' and r.get('status') in ('credited', 'lost')}
    # only closes that list their coin accounts (this rule) — a refund goes back only to the card that paid that coin's deposit
    todo = [r for r in d['ledger'][-2000:] if r.get('side') == 'close' and r.get('status') == 'sent' and r.get('sig') and r.get('closed') and r['id'] not in done]
    if not todo:
        return
    try:
        async with rs.httpx.AsyncClient(timeout=10) as http:
            st = ((await rs._krpc(http, 'getSignatureStatuses', [[r['sig'] for r in todo], {'searchTransactionHistory': True}])) or {}).get('value') or []
    except Exception:
        return
    sol_px = await rs._sol_usd_live()
    async with rs._fw_lock:
        d = rs._fw_load()
        for r, s_ in zip(todo, st):
            ok = bool(s_) and not s_.get('err') and s_.get('confirmationStatus') in ('confirmed', 'finalized')
            if ok and sol_px > 0:
                d['books'], cr = rs._fw.rent_back(d['books'], r['closed'], sol_px)
                rs._fw_record(d, {**{k: v for k, v in r.items() if k != 'closed'}, 'status': 'credited', 'credits': cr, 'at': rs.time.time(),
                               'why': 'rent deposit back into the card' if cr else 'rent back to the reserve (it fronted it)'})
            elif (s_ and s_.get('err')) or (not s_ and rs.time.time() - rs._fuse._f(r.get('at')) > 600):
                rs._fw_record(d, {**{k: v for k, v in r.items() if k != 'closed'}, 'status': 'lost', 'at': rs.time.time(), 'why': 'close never landed — nothing credited'})
        rs._fw_save(d)


async def _fw_close_empty(cfg, now):
    """♻ Every 2 rounds of the real card's clock (5-min rounds → every 10 min; never under 10, never over 30): close the Fuse wallet's
    EMPTY token accounts (coins fully sold) → their rent deposits come back to the wallet reserve, which paid them (the card never pays
    rent, so its numbers stay exact). One tx, CloseAccount only (destination = the wallet itself), Circle signs, logged + owner inbox."""
    rs = _rs()
    await rs._fw_rent_credit(cfg)
    every = rs._fw.close_every(rs._fuse._f(rs._prime_real_cfg().get('rotateHours')))
    d = rs._fw_load()
    held_ = {m for b in d['books'].values() for m in (b.get('legs') or {})}
    sold_out = {r.get('mint') for r in (d.get('ledger') or [])[-200:] if r.get('side') == 'sell' and r.get('status') == 'filled'
                and rs._fuse._f(r.get('at')) > rs._fw_close_at['t'] and r.get('mint') not in held_}   # coins sold whole since the last sweep = empty accounts
    gas_ = rs._fw.gas_tank(rs._FW_GAS.get('sol'), d['books'], cfg.get('reserveSol'))['sol'] if rs._FW_GAS.get('sol') is not None else 1.0
    if not rs._fw.sweep_due(now, rs._fw_close_at['t'], every, gas_, len(sold_out)) or not cfg.get('armed') or cfg.get('paused') or not rs._fw_signer_ready():
        return
    rs._fw_close_at['t'] = now
    if any(b.get('pending') for b in d['books'].values()):
        return
    keep = {m for b in d['books'].values() for m in (b.get('legs') or {})}
    try:
        async with rs.httpx.AsyncClient(timeout=15) as http:
            res = await rs.asyncio.gather(*[rs._krpc(http, 'getTokenAccountsByOwner', [cfg['address'], {'programId': pg}, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}]) for pg in rs._FW_TOKEN_PROGRAMS])
            rows = [{'pubkey': a.get('pubkey'), 'program': pg, 'lamports': (a.get('account') or {}).get('lamports'),
                     'info': (rs._parsed_info(a.get('account')))} for pg, r in zip(rs._FW_TOKEN_PROGRAMS, res) for a in (r or {}).get('value') or []]
            empty = rs._fw.empty_accounts(rows, keep)
            # ♻ what is parked right now (every open coin account's rent), for the card's rent line
            rs._fw_rent_parked.update(sol=sum(rs._fuse._f(r.get('lamports')) for r in rows) / 1e9, accounts=len(rows), empty=len(empty), at=now)
            if not empty:
                return
            bh = ((await rs._krpc(http, 'getLatestBlockhash', [{'commitment': 'finalized'}])) or {}).get('value', {}).get('blockhash')
            signed = await rs._fw_sign(cfg, rs._fw.close_tx(cfg['address'], empty, bh), f'FEELESS close {len(empty)} empty accounts')
            sig = signed.get('signature') or signed.get('txHash')
            await rs._krpc(http, 'sendTransaction', [signed.get('signedTransaction'), {'encoding': 'base64', 'maxRetries': 3, 'preflightCommitment': 'confirmed'}])
        rent = round(sum(rs._fuse._f(r.get('lamports')) for r in rows if r['pubkey'] in {e['pubkey'] for e in empty}) / 1e9, 9)
        closed = [{'mint': e.get('mint'), 'lamports': next((r.get('lamports') for r in rows if r['pubkey'] == e['pubkey']), 0)} for e in empty]
        row = {'id': f'close:{now:.0f}', 'card': 'wallet', 'side': 'close', 'n': len(empty), 'sol': rent, 'sig': sig, 'at': now, 'status': 'sent', 'closed': closed,
               'why': 'empty coin accounts closed — their rent comes back to the wallet once confirmed'}
    except Exception as e:
        err = str(getattr(e, 'detail', e))[:120]
        # Empty-account cleanup is maintenance, not a card trade. When the shared
        # public RPC pool is busy, back off quietly instead of hammering it every
        # three minutes and filling the audit trail with zero-dollar failures.
        if 'RPC pool exhausted' in err:
            rs._fw_close_at['t'] = now - 1800 + 900   # retry in ~15 min
            return
        row = {'id': f'close:{now:.0f}', 'card': 'wallet', 'side': 'close', 'at': now, 'status': 'failed', 'err': err}
        rs._fw_close_at['t'] = now - 1800 + 300   # non-rate-limit failure → retry in 5 min
    async with rs._fw_lock:
        d = rs._fw_load(); rs._fw_record(d, row); rs._fw_save(d)
    rs._fw_notify(row)


async def _mint_decimals(mint):
    rs = _rs()
    if mint in rs._mint_dec:
        return rs._mint_dec[mint]
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            r = await rs._krpc(http, 'getTokenSupply', [mint])
        rs._mint_dec[mint] = int(((r or {}).get('value') or {}).get('decimals'))
    except Exception:
        return None
    return rs._mint_dec[mint]


async def _paper_quote_audit(now):
    """📏 Paper ⇄ real, every ~5 min: up to 4 coins on the tier cards are priced the way paper fills them AND with a REAL Jupiter quote
    for the same $ (read-only, nothing signed). The gap is logged and the paper impact model learns from it before any money moves."""
    rs = _rs()
    cards = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    legs = [l for c in cards.values() for l in c.get('legs') or [] if l.get('mint') and l['mint'] != rs._fw.SOL_MINT]
    if not legs:
        return 0
    k = int(now // 300)
    pick = [legs[(k * 4 + i) % len(legs)] for i in range(min(4, len(legs)))]
    pairs_ = await rs._fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in pick])
    sol_px = await rs._sol_usd_live()
    rows = []
    for l in pick:
        p_ = pairs_.get(l['pairAddress']) or {}
        mid, liq = (await rs._jup_prices([l['mint']])).get(l['mint']) or rs._fuse._f(p_.get('priceUsd')), rs._fuse._f((p_.get('liquidity') or {}).get('usd'))
        dec = await rs._mint_decimals(l['mint'])
        if mid <= 0 or dec is None or sol_px <= 0:
            continue
        usd = max(5.0, min(300.0, rs._fuse._f(l.get('units')) * mid))
        try:
            q = await rs._fw_jup('GET', '/swap/v1/quote', params={'inputMint': rs._fw.SOL_MINT, 'outputMint': l['mint'], 'amount': str(int(usd / sol_px * 1e9)), 'slippageBps': '100'})
        except rs.HTTPException:
            continue
        rows.append({**rs._fw.quote_row(l.get('symbol'), usd, mid, liq, rs._prime.buy_px(mid, usd, liq), int(q.get('outAmount') or 0) / 10 ** dec, now), 'mint': l['mint']})
    if rows:
        async with rs._fw_lock:
            d = rs._fw_load(); d['quoteAudit'] = (d.get('quoteAudit') or [])[-199:] + rows; rs._fw_save(d)
    return len(rows)


def _fw_calibration(d):
    """Real fills win; until there are 3, paper learns from the real-quote audit."""
    rs = _rs()
    real = rs._fw.calibrate(d.get('ledger'))
    return real if real['n'] >= 3 else {**rs._fw.calibrate(d.get('quoteAudit')), 'feeUsd': real.get('feeUsd'), 'fees': real.get('fees'), 'from': 'quotes'}


def _fw_full_ledger():
    """🧾 EVERY ledger row, oldest first — from the append-only SQLite table (never trimmed). The KV doc keeps only the newest
    2,000 rows, and card totals read from it undercounted once the card passed that: fees showed $1.33 of $2.18, top-ups $15.50 of
    $22.50, and realized / you-vs-engine lost their oldest fills. Re-read only when the table grew (one COUNT per call)."""
    rs = _rs()
    lg = rs._store.Ledger(rs.FUSE_WALLET_PATH)
    n = lg.last_id()   # ⚡ MAX(id), not COUNT(*): the table only grows, so the newest id says the same thing for free
    if n != rs._fw_full_cache['n'] or rs._fw_full_cache.get('db') != str(lg.db):
        fresh = rs._fw_full_cache.get('db') != str(lg.db) or n < rs._fw_full_cache['n'] or rs._fw_full_cache['n'] < 0
        new, last = lg.since(0 if fresh else rs._fw_full_cache.get('last') or 0)   # ⚡ only the rows appended since the last read
        rs._fw_full_cache.update(n=n, db=str(lg.db), last=last, rows=new if fresh else rs._fw_full_cache['rows'] + new)
    return rs._fw_full_cache['rows'] or (rs._fw_peek().get('ledger') or [])


def _vs_cached(full_, tid):
    """(versus, realized) for a card — rebuilt when the ledger grew or after 60s, never on every public read."""
    rs = _rs()
    c_ = rs._vs_c.get(tid)
    if c_ and c_[0] == len(full_) and rs.time.time() - c_[1] < 60:
        return c_[2]
    v_ = (rs._fw.versus(full_, tid, rs.time.time()), rs._fw.realized_split(full_, tid))
    rs._vs_c[tid] = (len(full_), rs.time.time(), v_)
    return v_


def _fw_led_memo(kind, card, fn):
    """⚡ A sum over the WHOLE ledger, recomputed only when a row was added (the loop-lag catcher charged `totals` + the paid-out sum
    ~8s a window: they re-walked thousands of rows on every /fuses/prime build)."""
    rs = _rs()
    L = rs._fw_full_ledger()
    k = (kind, card)
    hit = rs._FW_LED_MEMO.get(k)
    if hit and hit[0] == len(L):
        return hit[1]
    v = fn(L)
    rs._FW_LED_MEMO[k] = (len(L), v)
    return v


def _fw_public(tid, equity_usd=None, sol_px=None, prices=None):
    """What everyone sees on a REAL tier card: since when, $ funded, the last swaps with their tx, real network fees."""
    rs = _rs()
    d = rs._fw_peek(); b = d['books'].get(tid)   # read-only: this view only reads the doc (lists it builds are its own)
    if not b:
        return None
    seen, rows = set(), []
    for o in reversed(d['ledger']):   # newest first, each tx / funding once
        if o.get('card') != tid or o.get('side') not in ('buy', 'sell', 'topup') or not (o.get('status') in ('filled', 'done') or o.get('side') == 'topup'):
            continue
        k = (o.get('sig'), o.get('side')) if o.get('sig') else f"{o.get('id')}:{o.get('side')}:{o.get('at')}"
        if k not in seen:
            seen.add(k); rows.append(o)
        if len(rows) >= 12:
            break
    cfg = rs._fw_cfg(); pend = b.get('pending') or {}
    dead = []
    seen_dead = set()
    for o in reversed(d['ledger']):
        if o.get('card') != tid or o.get('side') not in ('buy', 'sell'):
            continue
        kdead = (o.get('side'), o.get('mint') or o.get('symbol'))
        if kdead in seen_dead:
            continue
        seen_dead.add(kdead)
        if o.get('status') not in ('failed', 'skipped'):
            continue
        dead.append({k: o.get(k) for k in ('side', 'symbol', 'mint', 'pair', 'usd', 'at', 'status', 'err')})
        if len(dead) >= 8:
            break
    fail = dead[0] if dead else None
    keeper = {'armed': bool(cfg.get('armed')), 'paused': bool(cfg.get('paused') or b.get('halt')), 'halt': bool(b.get('halt')), 'haltWhy': (b.get('haltWhy') or None) if b.get('halt') else None, 'selling': bool(b.get('defund')),
              'minLiqUsd': cfg.get('minLiqUsd'), 'arenaMinLiqUsd': cfg.get('arenaMinLiqUsd'), 'pickMinLiqUsd': cfg.get('pickMinLiqUsd'), 'pickSellBackPct': cfg.get('pickSellBackPct'), 'minOrderUsd': cfg.get('minOrderUsd'), 'maxSwapUsd': cfg.get('maxSwapUsd'), 'slippageBps': cfg.get('slippageBps'),
              'maxImpactPct': cfg.get('maxImpactPct'), 'dailyUsd': cfg.get('dailyUsd'), 'pending': pend.get('symbol') and f"{pend.get('side')} ${pend.get('symbol')}",
              'lastFail': fail and {'symbol': fail.get('symbol'), 'side': fail.get('side'), 'mint': fail.get('mint'), 'pair': fail.get('pair'), 'err': (fail.get('err') or '')[:90], 'at': fail.get('at')},
              'lastFill': next((o.get('at') for o in rows if o.get('status') == 'filled'), None),
              'gas': rs._fw.gas_tank(rs._FW_GAS['sol'], d['books'], cfg.get('reserveSol')) if 'sol' in rs._FW_GAS else None,
              'landing': rs._fw.landing(d['ledger'], tid, rs.time.time(), broadcast_only=True),
              'rent': {**rs._fw.rent_story(d['ledger'], rs.time.time(), rs._fw_rent_parked or None, rs._fuse._f(sol_px)), 'everySec': rs._fw.close_every(rs._fuse._f(rs._prime_real_cfg().get('rotateHours')))},
              'rpc': rs._rpc_quota_state()}
    # walletUsd is the engine's cumulative realized-profit payout counter and survives reinvests; old real ledgers did not
    # stamp payoutUsd on sell rows, which made PAID OUT EVER falsely show $0. Never infer history from current bankSol.
    card = rs._prime_cards().get(tid) or {}
    visible = {l.get('mint') for l in card.get('legs') or []}
    off_card = []
    for mint, leg in (b.get('legs') or {}).items():
        if mint in visible or not int(rs._fuse._f(leg.get('atoms'))):
            continue
        units = int(rs._fuse._f(leg.get('atoms'))) / 10 ** int(leg.get('decimals') or 0)
        px_now = rs._fw.leg_px(b, mint, leg, prices or {}, rs.time.time())   # 💧 what selling pays, never a drained pool's quoted price
        off_card.append({'mint': mint, 'symbol': leg.get('symbol') or mint[:6], 'usd': round(units * px_now, 4),
                         'costUsd': round(rs._fuse._f(leg.get('costUsd')), 4), 'status': 'awaiting confirmed sell'})
    ledger_paid = rs._fw_led_memo('paid', tid, lambda L: sum(max(0.0, rs._fuse._f(o.get('payoutUsd'))) for o in L if o.get('card') == tid and o.get('status') == 'filled' and o.get('side') == 'sell'))
    paid_ever = round(max(rs._fuse._f(card.get('walletUsd')), rs._fuse._f(b.get('payoutSeenUsd')), ledger_paid, rs._fuse._f(b.get('manualProfitPaidUsd'))), 4)
    profit_available = rs._fw.profit_available(b, equity_usd, sol_px) if equity_usd is not None and sol_px else 0.0
    payout_cash = min(profit_available, max(0.0, rs._fuse._f(b.get('sol')) - rs._fuse._f(b.get('manualCashSol'))) * rs._fuse._f(sol_px)) if sol_px else 0.0
    wallet_sol = rs._fuse._f(rs._FW_GAS.get('sol')) if rs._FW_GAS.get('sol') is not None else None
    all_book_sol = sum(rs._fuse._f(bb.get('sol')) + rs._fuse._f(bb.get('bankSol')) for bb in d['books'].values())
    reserve_sol = rs._fuse._f(cfg.get('reserveSol'))
    outside_sol = max(0.0, wallet_sol - all_book_sol - reserve_sol) if wallet_sol is not None else None
    recoverable = []
    bal = rs._FW_BAL.get('bal') if rs._FW_BAL.get('addr') == cfg.get('address') else None
    newest_fill = max((rs._fuse._f(o.get('at')) for o in d.get('ledger') or [] if o.get('status') == 'filled'), default=0.0)
    balance_is_current = rs._fuse._f(rs._FW_BAL.get('at')) >= newest_fill
    if bal and bal.get('source') != 'circle' and balance_is_current:
        booked = {}
        for bb in d['books'].values():
            for mint, leg in (bb.get('legs') or {}).items():
                booked[mint] = booked.get(mint, 0) + int(rs._fuse._f(leg.get('atoms')))
        for mint, held in (bal.get('tokens') or {}).items():
            excess = int(rs._fuse._f(held)) - int(booked.get(mint, 0))
            if excess <= 0:
                continue
            hist = [o for o in d['ledger'] if o.get('card') == tid and o.get('mint') == mint and o.get('pair')]
            if not hist:
                continue
            last = hist[-1]
            if last.get('side') == 'writeoff':   # 🩸 written off (dead dust / drained pool): offering "sell it" again would re-book it and jam the buys
                continue
            recoverable.append({'mint': mint, 'symbol': last.get('symbol') or mint[:6], 'atoms': excess,
                                'lastStatus': last.get('status'), 'lastErr': (last.get('err') or '')[:90], 'lastAt': last.get('at')})
    try:   # 👁 the swap as steps (done → sending → next), one transaction at a time
        plan = rs._fw.orders(tid, {**card, 'legs': []} if b.get('defund') else card, b, prices or {}, sol_px, cfg, rs.time.time()) if sol_px and card else []
        keeper['flow'] = rs._fw.swap_flow(b, d['ledger'], tid, plan, rs.time.time())
    except Exception:
        keeper['flow'] = []
    keeper['holdingSell'] = bool(b.get('sellHoldAt'))
    full_ = rs._fw_full_ledger()
    return {'since': b.get('since'), 'fundedUsd': b.get('fundedUsd'),
            'paidOutEverUsd': paid_ever, 'paidOutSol': round(rs._fuse._f(b.get('bankSol')), 9),
            'profitAvailableUsd': round(profit_available, 4), 'profitCashAvailableUsd': round(payout_cash, 4), 'recoverable': recoverable, 'offCard': off_card,
            'wallet': cfg['address'], 'keeper': keeper, 'versus': rs._vs_cached(full_, tid)[0], 'realized': rs._vs_cached(full_, tid)[1], 'deadOrders': dead,
            'reconciliation': {'cardEquityUsd': round(rs._fuse._f(equity_usd), 4),
                               'cardCashSol': round(rs._fuse._f(b.get('sol')), 9),
                               'cardCashUsd': round(rs._fuse._f(b.get('sol')) * rs._fuse._f(sol_px), 4) if sol_px else None,
                               'walletSol': round(wallet_sol, 9) if wallet_sol is not None else None,
                               'gasReserveSol': round(reserve_sol, 9),
                               'outsideCardSol': round(outside_sol, 9) if outside_sol is not None else None,
                               'outsideCardUsd': round(outside_sol * rs._fuse._f(sol_px), 4) if outside_sol is not None and sol_px else None},
            'orders': [{k: o.get(k) for k in ('side', 'symbol', 'usd', 'proceedsUsd', 'realizedPnlUsd', 'sol', 'px', 'sig', 'at', 'status', 'feeUsd', 'why', 'costUsd')} for o in rows],
            **rs._fw_led_memo('tot', tid, lambda L: rs._fw.totals(L, tid)), 'feesUsd': round(rs._fuse._f(b.get('feesUsd')), 4)}   # 🧾 the book's fee total (each fill at its own SOL price) — never a partial sum


async def _circle_wallets_live():
    """Circle supplies token ids needed for sends; confirmed chain lamports supply the display truth for Solana wallets.
    A Circle balance-endpoint error must never turn a funded wallet into an apparently empty wallet in HQ."""
    rs = _rs()
    wallets = list((await rs._circle('GET', '/wallets')).get('wallets') or [])
    sol = [w for w in wallets if str(w.get('blockchain') or '').upper().startswith('SOL') and w.get('address')]
    if not sol:
        return wallets
    try:
        async with rs.httpx.AsyncClient(timeout=12) as http:
            got = await rs._rpc(http, 'getMultipleAccounts', [[w['address'] for w in sol], {'encoding': 'base64', 'commitment': 'confirmed'}])
        lamports = {w['address']: int((a or {}).get('lamports') or 0) for w, a in zip(sol, (got or {}).get('value') or [])}
        out = []
        for w in wallets:
            if w.get('address') not in lamports:
                out.append(w); continue
            rows = [dict(b) for b in (w.get('balances') or [])]
            old = next((b for b in rows if str(b.get('symbol') or '').upper() == 'SOL'), None)
            amount = str(lamports[w['address']] / 1e9)
            if old:
                old['amount'] = amount
            elif lamports[w['address']] > 0:
                rows.insert(0, {'symbol': 'SOL', 'amount': amount, 'tokenId': None, 'source': 'chain'})
            out.append({**w, 'balances': rows, 'balanceSource': 'confirmed-chain'})
        try:   # 💲 each coin's $ value (Jupiter, public lane) so the row reads what the leftovers are worth — SOL by its own price
            mints = list({b.get('mint') for w in out for b in w.get('balances') or [] if b.get('mint')})
            px = await rs._jup_prices(mints) if mints else {}
            sol_px = await rs._sol_usd_live()
            for w in out:
                for b in w.get('balances') or []:
                    p_ = sol_px if str(b.get('symbol') or '').upper() == 'SOL' and not b.get('mint') else rs._fuse._f(px.get(b.get('mint')))
                    b['usd'] = round(rs._fuse._f(b.get('amount')) * p_, 4) if p_ else None
        except Exception as e:
            print('circle usd:', str(e)[:80])
        return out
    except Exception:
        return wallets


async def _fw_reports(card=''):
    rs = _rs()
    d = rs._fw_load(); hq = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    ids = [card] if card else sorted({r.get('card') for r in d.get('ledger') or [] if r.get('card') and r.get('card') != 'wallet'})
    sol_px = await rs._sol_usd_live()
    mints = [m for tid in ids for m in ((d['books'].get(tid) or {}).get('legs') or {})]
    jup = await rs._jup_prices(mints) if mints else {}
    out = []
    for tid in ids:
        b = d['books'].get(tid) or {}
        c = hq.get(tid) or {}
        px = {l.get('pair'): rs._fuse._f(jup.get(m)) or rs._fuse._f(l.get('entryPx')) for m, l in (b.get('legs') or {}).items()}   # live Jupiter value
        eq = rs._fw.book_value(b, px, sol_px) if b else None
        hold = round((sol_px / rs._fuse._f(c['solStart']) - 1) * 100, 2) if sol_px and rs._fuse._f(c.get('solStart')) else None
        out.append({**rs._fw.run_report(rs._fw_full_ledger(), tid, rs.time.time(), b.get('fundedUsd'), eq, hold), 'label': c.get('label') or tid, 'open': bool(b)})
    return out


async def _fw_recover_sell(me, tid, mint):
    rs = _rs()
    if tid not in rs._prime.TEMPLATES or not mint:
        raise rs.HTTPException(400, 'Pick a real tier card and token.')
    cfg = rs._fw_cfg()
    if not cfg.get('address') or not cfg.get('armed') or cfg.get('paused'):
        raise rs.HTTPException(400, 'Fuse wallet must be armed and running.')
    bal = await rs._fw_balances(cfg['address'])
    async with rs._fw_tick_lock, rs._fw_lock:   # 🧷 waits for a keeper pass in flight: an owner write and a swap pass never interleave
        d = rs._fw_load()
        if tid not in d['books']:
            raise rs.HTTPException(404, 'That tier has no real card book.')
        booked_total = sum(int(rs._fuse._f(((b.get('legs') or {}).get(mint) or {}).get('atoms'))) for b in d['books'].values())
        held = int(rs._fuse._f((bal.get('tokens') or {}).get(mint)))
        excess = max(0, held - booked_total)
        hist = [r for r in d['ledger'] if r.get('card') == tid and r.get('mint') == mint and r.get('pair')]
        if excess <= 0:
            raise rs.HTTPException(400, 'No unbooked wallet balance remains for that token.')
        if not hist:
            raise rs.HTTPException(400, 'Refused: this wallet token has no keeper history for that card.')
        last = hist[-1]
        st = {'card': tid, 'mint': mint, 'atoms': excess,
              'decimals': int((bal.get('decimals') or {}).get(mint) or last.get('decimals') or 0),
              'pair': last.get('pair'), 'symbol': last.get('symbol') or mint[:6]}
        book = rs._fw.adopt(d['books'][tid], st)
        book['legs'][mint]['manualCash'] = True
        book['legs'][mint]['recovered'] = True
        d['books'][tid] = book
        rs._fw_record(d, {'card': tid, 'side': 'adopt', 'mint': mint, 'symbol': st['symbol'], 'atoms': excess,
                       'usd': 0.0, 'at': rs.time.time(), 'status': 'done',
                       'why': '🧹 owner recovered old keeper balance for force sell → proceeds stay in card cash'})
        rs._fw_save(d)
    rs._fw_kick_now()
    ad = rs._admin_load(); rs._audit(ad, me, 'fuse-wallet-recover-sell', f'{tid} {st["symbol"]} {excess} atoms'); rs._admin_save(ad)
    return {'ok': True, 'card': tid, 'symbol': st['symbol'], 'atoms': excess, 'status': 'sell queued/running'}


def _alliance_view(wallet=''):
    rs = _rs()
    import alliances as _al
    st = rs._json_load(rs.ALLIANCES_PATH, {}) or {}; days = int(st.get('days') or _al.DEFAULT_DAYS); now = rs.time.time()
    return {'days': days, 'rows': [_al.public(a, days, now, wallet) for a in sorted(st.get('rows') or [], key=lambda x: -len(x['members']))]}

