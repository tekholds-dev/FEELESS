"""🧹 Coin edge — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


async def _edge_pulses(mints):
    """5m pulse for many coins in ONE call to the market service (15s per coin)."""
    rs = _rs()
    now = rs.time.time()
    need = [m for m in mints if now - rs._edge_pulse.get(m, (0, None))[0] > 15]
    if need:
        try:
            async with rs.httpx.AsyncClient(timeout=6) as http:
                coins = (await http.get('http://127.0.0.1:5001/api/market/pulse', params={'mints': ','.join(need[:60])})).json().get('coins') or {}
        except Exception:
            coins = {}
        for m in need:
            rs._edge_pulse[m] = (now, coins.get(m))
    return {m: rs._edge_pulse.get(m, (0, None))[1] for m in mints}


def _germ_rec(mint, now):
    """🦠 THE GERM ON EVERY COIN (owner, 2026-10-16: "put the germ symbol on all coins site wide"): the agents' own chart read (1m + 5m real
    candles) as a compact record for the coin edge — {d: % above the 1m germ floor, w: floor | near | far | lost, d5, w5, run, e: the
    entry word (confirmed / floor / far / lost), line: the owner's germ line, ok: inside it, at}. None = no read (no 15% run yet / not on
    the desk). Read from the shared snapshot — no fetch."""
    rs = _rs()
    f_ = (((rs._office.get('charts') or {}).get(mint) or {}).get('f') or {})
    g1, g5 = f_.get('germ'), f_.get('germ5')
    if g1:
        w1, w5 = rs._ci.germ_word(g1), rs._ci.germ_word(g5)
        mx_ = rs._uni.germ_max()
        rec = {'px': g1.get('px'), 'd': g1.get('dist'), 'w': w1, 'd5': (g5 or {}).get('dist'), 'w5': w5, 'run': g1.get('runPct'), 'e': rs._ci.germ_entry({'germ': w1, 'germ5': w5}),
               'line': mx_, 'ok': (not mx_) or abs(rs._fuse._f(g1.get('dist'))) <= mx_, 'at': round(now)}
        rs._germ_seen[mint] = (now, rec)
        if len(rs._germ_seen) > 4000:
            for k_ in sorted(rs._germ_seen, key=lambda k_: rs._germ_seen[k_][0])[:800]:
                rs._germ_seen.pop(k_, None)
        return rec
    at_, rec = rs._germ_seen.get(mint, (0, None))
    return rec if rec and now - at_ <= rs.GERM_KEEP_SEC else None


async def _edge_build(todo, now, budget=None):
    """Build edge records for `todo` (pulse · verification · snipers · runner gates · sources · elite flow · buys vs sells). With a
    `budget` the slow reads are cut off and the incomplete record is cached for only ~3s, so the next poll fills it in."""
    rs = _rs()
    async def _cap(coro, default):
        try:
            return await (rs.asyncio.wait_for(coro, timeout=budget) if budget else coro)
        except Exception:
            return default
    async def _bs():
        try:
            return await rs.asyncio.wait_for(rs._bs_rows(todo), timeout=2.5)   # 🌊 buys vs sells 5m / 1h (+ the live 90s tape for held coins); never slows the edge
        except Exception:
            return {}
    pulses, ver_, bs_ = await rs.asyncio.gather(_cap(rs._edge_pulses(todo), None), _cap(rs.verify_batch(','.join(todo)), None), _bs())   # all three at once
    partial = pulses is None or ver_ is None
    pulses, ver = pulses or {}, ((ver_ or {}).get('verify') or {})
    snip = {}
    for e in rs._radar['events']:
        if e['kind'] == 'snipers-out' and now - e['at'] < 6 * 3600:
            snip.setdefault(e.get('mint') or e['pair'], e)
    live = rs._runner_live_cache.get('data') or {}
    runner = {r['mint']: r for r in (live.get('dropped') or []) + (live.get('passing') or [])}
    disc = {r['mint']: r.get('sources') or [] for r in ((rs._runner_disc_cache.get('data') or {}).get('runners') or [])}
    flow = ((rs._crowd_cache.get('data') or {}).get('flow')) or {}
    out = {}
    for m in todo:
        rec = {**rs._edge.compose(m, pulses.get(m), snip.get(m), ver.get(m), (rs._intel_cache.get(m) or (0, None))[1], runner.get(m), disc.get(m), flow.get(m)), 'bs': bs_.get(m), 'germ': rs._germ_rec(m, now)}
        rs._edge_cache[m] = (now - 12 if partial else now, rec); out[m] = rec
    if len(rs._edge_cache) > 5000:
        rs._edge_cache.clear()
    return out


async def _edge_refresh(ms):
    rs = _rs()
    try:
        await rs._edge_build(ms, rs.time.time())
    except Exception as e:
        print('edge refresh:', type(e).__name__)
    finally:
        rs._edge_inflight.difference_update(ms)


async def _feeback_book():
    """Fuse Fee-Back per wallet: earned (unlocked shares of fees paid on cards), paid, owed."""
    rs = _rs()
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    rules = rs._card_rules(); by = rs._ledger_by_sig(); now = rs.time.time(); wins = rs._season_wins()
    hot = {c['id'] for c in (rs._arena_mega_cache.get('data') or []) if c.get('kind') == 'user' and c['activity']['tier'] in ('hot', 'blazing')}
    out = {}
    for x in d.get('positions') or []:
        fb = rs._hq.card_feeback(rs._card_fees(x, by), (x.get('closedAt') or now) - rs._fuse._f(x.get('at')), x['id'] in hot, rules, x['id'] in wins)
        a = out.setdefault(x['wallet'], {'wallet': x['wallet'], 'earnedUsd': 0.0, 'cards': 0, 'copyUsd': 0.0})
        a['earnedUsd'] = round(a['earnedUsd'] + fb['usd'], 6); a['cards'] += 1
        if x.get('copyOwner'):
            o = out.setdefault(x['copyOwner'], {'wallet': x['copyOwner'], 'earnedUsd': 0.0, 'cards': 0, 'copyUsd': 0.0})
            cut = rs._hq.copy_cut(rs._card_fees(x, by), rules, champ=bool(x.get('champCopy')))
            o['earnedUsd'] = round(o['earnedUsd'] + cut, 6); o['copyUsd'] = round(o['copyUsd'] + cut, 6)
    for pz in d.get('backerPrizes') or []:   # ⚔ weekly top backers' prize share
        o = out.setdefault(pz['wallet'], {'wallet': pz['wallet'], 'earnedUsd': 0.0, 'cards': 0, 'copyUsd': 0.0})
        o['earnedUsd'] = round(o['earnedUsd'] + rs._fuse._f(pz['usd']), 6); o['backerUsd'] = round(rs._fuse._f(o.get('backerUsd')) + rs._fuse._f(pz['usd']), 6)
    paid = d.get('feebackPaid') or {}
    rows = [{**a, 'paidUsd': rs._fuse._f(paid.get(w)), 'owedUsd': round(max(0.0, a['earnedUsd'] - rs._fuse._f(paid.get(w))), 6)} for w, a in out.items()]
    return {'rows': sorted(rows, key=lambda a: -a['owedUsd'])[:200], 'owedUsd': round(sum(a['owedUsd'] for a in rows), 6), 'earnedUsd': round(sum(a['earnedUsd'] for a in rows), 6)}


async def _fuse_guard_tick():
    """Every minute: value open, guarded positions; when a limit hits, alert the holder once (inbox + phone) with a
    one-tap Unfuse link. FEELESS never signs for you — the exit is still your wallet's approval."""
    rs = _rs()
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    now = rs.time.time()
    rb = [x for x in d.get('positions') or [] if x.get('autoRebalance') and not x.get('closedAt') and now - (x['autoRebalance'].get('lastAt') or 0) > 6 * 3600]
    if rb:   # auto-rebalance: one alert (≤ every 6h) with a one-tap rebalance link when a card drifts past its tolerance
        rpx = await rs._hq_prices([leg for x in rb for leg in x['legs']])
        fired = []
        for x in rb:
            dr = rs._hq.drift(rs._hq.position_pnl(x, rpx))
            if dr >= x['autoRebalance']['tol']:
                fired.append(x['id'])
                rs.notify(x['wallet'], 'fuse-guard', f"⚖ {x.get('name') or 'Your Fuse card'} drifted {dr:.0f} pts from its weights — tap to rebalance (one approval).",
                       url=f"/terminal/fuse?tab=cards&rebalance={x['id']}", once=f"rb-{x['id']}-{int(now // (6 * 3600))}",
                       meta={'claim': f'Largest leg is {dr:.0f} points off its target share', 'source': 'Fuse P&L (live prices)'})
        if fired:
            async with rs._admin_lock:
                d2 = rs._json_load(rs.FUSE_HQ_PATH, {})
                for x in d2.get('positions') or []:
                    if x['id'] in fired and x.get('autoRebalance'):
                        x['autoRebalance']['lastAt'] = now
                rs._json_save(rs.FUSE_HQ_PATH, d2)
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
    await rs._fuse_yield_tick(d, now)
    await rs._fuse_swap_tick(d, now)
    await rs._fuse_leg_tick(d, now)
    await rs._fuse_buyback_tick(rs._json_load(rs.FUSE_HQ_PATH, {}), now)
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    live = [x for x in d.get('positions') or [] if x.get('guard') and not x['guard'].get('firedAt') and not x.get('closedAt')]
    if not live:
        return 0
    px = await rs._hq_prices([leg for x in live for leg in x['legs']])
    hits, peaks = [], {}
    for x in live:
        r = rs._hq.position_pnl(x, px)
        hit, peak = rs._hq.guard_check(x['guard'], r['pnlPct'])
        peaks[x['id']] = peak
        if hit:
            hits.append((x, hit, r))
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        by = {x['id']: x for x in d.get('positions') or []}
        for pid, pk in peaks.items():
            if pid in by and by[pid].get('guard'):
                by[pid]['guard']['peak'] = round(pk, 2)
        for x, hit, r in hits:
            if by.get(x['id'], {}).get('guard'):
                by[x['id']]['guard']['firedAt'] = rs.time.time(); by[x['id']]['guard']['hit'] = hit
        rs._json_save(rs.FUSE_HQ_PATH, d)
    label = {'tp': '🎯 Take-profit hit', 'sl': '🛑 Stop-loss hit', 'trail': '📉 Trailing stop hit'}
    for x, hit, r in hits:
        rs.notify(x['wallet'], 'fuse-guard', f"{label[hit]} on {x.get('name') or 'your Fuse'}. Tap to Unfuse — one approval (numbers in My cards).",
               url=f"/terminal/trade?tab=fuse&unfuse={x['id']}", once=f"guard-{x['id']}-{x['guard'].get('armedAt')}",
               meta={'claim': f"Basket P&L {r['pnlPct']:+.1f}% vs your limit", 'source': 'Fuse P&L (live DexScreener prices)'})
    return len(hits)


async def _card_signal_tick(now=None):
    """ONE signal stream (the inbox you already have — no new tab): coins on your OPEN cards that just got a coin-edge signal
    (🔔 bond run, 🎯 snipers out, ⚠ now failing a runner gate) → one inbox + phone notice each, with the card one tap away.
    Reads caches only. No P&L in the text."""
    rs = _rs()
    now = now or rs.time.time()
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    live = rs._runner_live_cache.get('data') or {}
    board = {r['mint']: r for r in (live.get('passing') or []) + (live.get('dropped') or [])}
    snip = {e.get('mint') or e['pair'] for e in rs._radar['events'] if e['kind'] == 'snipers-out' and now - e['at'] < 3600}
    n = 0
    for x in d.get('positions') or []:
        if x.get('closedAt'):
            continue
        for leg in x['legs']:
            if leg.get('soldUsd') is not None or not leg.get('mint'):
                continue
            m, sym = leg['mint'], leg.get('symbol') or '?'
            r = board.get(m) or {}
            sigs = []
            if r.get('bondTier'):
                sigs.append(('bond', f"🔔 ${sym} on {x.get('name') or 'your card'}: {r['bondTier']} — every bond box ticked.", 'Fuse Runners bond check'))
            if m in snip or leg.get('pairAddress') in snip:
                sigs.append(('snipers', f"🎯 ${sym} on {x.get('name') or 'your card'}: every flagged sniper sold out.", 'Launch forensics radar'))
            if leg.get('role') == 'runner' and r.get('gates'):
                sigs.append(('gate', f"⚠ ${sym} on {x.get('name') or 'your card'} now fails: {r['gates'][0]}. Switch or sell it — one approval.", 'Fuse Runners gates'))
            for kind, text, src in sigs:
                rs.notify(x['wallet'], 'fuse-signal', text, url=f"/terminal/fuse?tab=cards&card={x['id']}", once=f"sig-{x['id']}-{m}-{kind}-{int(now // 21600)}",
                       meta={'claim': text, 'source': src})
                n += 1
    return n


async def _fuse_guard_loop():
    rs = _rs()
    await rs.asyncio.sleep(45)
    while True:
        try:
            await rs._fuse_guard_tick()
            await rs._card_signal_tick()
        except Exception as e:
            print('fuse guard:', e)
        await rs.asyncio.sleep(60)


async def _hq_prices(legs):
    rs = _rs()
    pairs = await rs._fuse_pairs([{'chainId': leg.get('chainId', 'solana'), 'pairAddress': leg['pairAddress']} for leg in legs])
    return {k: rs._fuse._f(v.get('priceUsd')) for k, v in pairs.items()}


async def _wallet_held(wallets, mints):
    """{mint: tokens} summed over these wallets from chain (both token programs), cached 60s. None = RPC unavailable (never guess)."""
    rs = _rs()
    key = tuple(wallets)
    hit = rs._held_cache.get(key)
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1]
    try:
        async with rs.httpx.AsyncClient(timeout=10) as http:
            res = await rs.asyncio.gather(*[rs._rpc(http, 'getTokenAccountsByOwner', [w, {'programId': pg}, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}])
                                         for w in wallets[:6] for pg in rs._FW_TOKEN_PROGRAMS])
    except Exception:
        return None
    held = {}
    for r in res:
        for a in (r or {}).get('value') or []:
            info = rs._parsed_info(a.get('account'))
            if info.get('mint'):
                held[info['mint']] = held.get(info['mint'], 0.0) + rs._fuse._f((info.get('tokenAmount') or {}).get('uiAmountString') or (info.get('tokenAmount') or {}).get('uiAmount'))
    rs._held_cache[key] = (rs.time.time(), held)
    return held


async def _arena_settle(px=None, now=None):
    """Close every arena run older than 24h at today's prices, once. Returns the saved store."""
    rs = _rs()
    now = now or rs.time.time()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        due = [e for e in d.get('arena') or [] if not e.get('close') and now - e['at'] >= rs._hq.ARENA_HOURS * 3600]
        if due:
            px = px if px is not None else await rs._hq_prices([leg for e in due for leg in e['legs']])
            for e in due:
                e['close'] = {leg['pairAddress']: px.get(leg['pairAddress']) or leg['start'] for leg in e['legs']}; e['closedAt'] = now
            rs._json_save(rs.FUSE_HQ_PATH, d)
    return d

