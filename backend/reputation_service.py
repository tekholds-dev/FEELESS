
def _fw_keep(d, tid, book):
    """Save a card's book without losing the miss / bench counts written meanwhile by _fw_record."""
    old = (d.get('books') or {}).get(tid) or {}
    return {**book, 'misses': old.get('misses', book.get('misses') or {}), 'benched': old.get('benched', book.get('benched') or {})}


_FW_NOT_COIN = ('not armed', 'paused', 'per-swap cap', 'daily cap', 'No Fuse wallet', 'signing not available', 'RPC pool', 'live market unavailable')


def _fw_record(d, row):
    if row.get('side') == 'buy' and row.get('status') in ('skipped', 'failed') and row.get('mint') and row.get('card') in (d.get('books') or {}) \
            and not any(x in str(row.get('err') or '') for x in _FW_NOT_COIN):   # 🪑 a coin that keeps failing its buy gets benched
        b, out = _fw.note_miss(d['books'][row['card']], row['mint'], _fuse._f(row.get('at')) or time.time(), str(row.get('err') or ''))
        d['books'][row['card']] = b
        if out:
            print(f"fuse wallet: benched {row.get('symbol')} for 1h — {row.get('err')}")
    if row.get('id') and any(r.get('id') == row['id'] and r.get('status') == row.get('status') for r in (d.get('ledger') or [])[-50:]):
        return   # the same order outcome is booked once (two ticks resolving one tx can't double the trail)
    d['ledger'] = (d.get('ledger') or [])[-1999:] + [row]   # recent 2000 for fast reads …
    try:
        _store.Ledger(FUSE_WALLET_PATH).append(row)          # … and the append-only audit table keeps EVERY row forever
    except Exception as e:
        print('fuse wallet ledger:', e)


async def _fw_execute(tid, order, book, cfg, sol_px, liq):
    """One keeper order: real Jupiter quote → the owner's hard limits → Circle signs (Fuse wallet only) → we broadcast → the confirmed
    tx's balance changes ARE the fill. Every outcome goes to the audit ledger; fills + failures reach the owner's inbox."""
    if book.get('pending'):
        return book   # defense in depth: never overwrite the one in-flight signature with a second sell or buy
    now = time.time()
    # `card` must be present on every outcome. Without it, secure-quote refusals (price gap / no sell-back route) were logged but
    # never counted by _fw_record, so the same unsafe mint retried forever instead of reaching the existing bench-and-replace path.
    row = {**order, 'card': tid, 'liq': liq, 'status': 'quoted'}
    if order.get('side') == 'buy':
        # FINAL BUY GATE: candidate/radar liquidity can be stale. Re-fetch the exact pair immediately before any quote/sign.
        # If DexScreener cannot confirm the pair right now, fail closed: no real-money buy is allowed from cached market data.
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                mr = await http.get(f"https://api.dexscreener.com/latest/dex/pairs/solana/{order.get('pair')}")
            data = mr.json() if mr.status_code == 200 else {}
            live_pairs = (data or {}).get('pairs') or ([data.get('pair')] if isinstance(data, dict) and data.get('pair') else [])
            live_pair = next((p for p in live_pairs if p and p.get('pairAddress') == order.get('pair')), live_pairs[0] if live_pairs else None)
            ok_live, why_live, snap = _fw.live_buy_market(order, live_pair, cfg)
        except Exception:
            ok_live, why_live, snap = False, 'live market unavailable — buy refused', {}
        row.update(snap)
        if not ok_live:
            row.update(status='skipped', err=why_live)
            async with _fw_lock:
                d = _fw_load()
                if not _fw.logged_recently(d.get('ledger'), row, now):
                    _fw_record(d, row); _fw_save(d)
            return book
    async with _fw_lock:   # 🚦 limits a quote can't change (armed · paused · per-swap · daily cap · thin pool) are checked BEFORE quoting:
        d = _fw_load()        # no Jupiter calls, and the skip is booked once per 15 min instead of every tick (the cap retry loop)
        ok, why = _fw.check(row, cfg, d.get('ledger'), now)
        if not ok:
            skip = {**row, 'card': tid, 'status': 'skipped', 'err': why}
            if not _fw.logged_recently(d.get('ledger'), skip, now):
                _fw_record(d, skip); _fw_save(d)
            return book
    try:
        for attempt in range(3):   # 🔁 strong retry: a busy route gets fresh quotes, each with a little more slippage (≤ the 3% hard cap)
            try:
                q = await _fw_quote(order, {**cfg, 'slippageBps': min(300, int(cfg['slippageBps']) + 75 * attempt)})
                break
            except HTTPException:
                if attempt == 2:
                    raise
                await asyncio.sleep(1.5)
        row['impactPct'] = round(_fuse._f(q.get('priceImpactPct')) * 100, 3); row['quoteOut'] = q.get('outAmount')
        if order['side'] == 'buy':   # 🛡 secure buy: near market price + it really sells back (both read-only quotes)
            try:
                back = await _fw_jup('GET', '/swap/v1/quote', params={'inputMint': order['mint'], 'outputMint': _fw.SOL_MINT, 'amount': str(q.get('outAmount')), 'slippageBps': str(cfg['slippageBps'])})
                back_l = _fuse._f(back.get('outAmount'))
            except HTTPException:
                back_l = None
            try:   # market = Jupiter's own price (what routes really pay); a DexScreener pair can lag on young coins
                jp = _fuse._f(((await _jup_prices([order['mint']])) or {}).get(order['mint']))
            except Exception:
                jp = 0.0
            ok_s, why_s = _fw.buy_safety({**order, 'midPx': jp or order.get('midPx')}, q.get('outAmount'), await _mint_decimals(order['mint']), back_l)
            row['sellBackPct'] = None if back_l is None else round((back_l / max(1, order['lamports']) - 1) * 100, 2)
            if not ok_s:
                raise HTTPException(400, why_s)
        elif order['side'] == 'sell' and 'rug' not in str(order.get('why') or ''):   # 🛡 secure sell: the route must pay near the market price
            try:
                jp = _fuse._f(((await _jup_prices([order['mint']])) or {}).get(order['mint']))
            except Exception:
                jp = 0.0
            ok_s, why_s = _fw.sell_safety(order, q.get('outAmount'), sol_px, jp)
            if not ok_s:
                raise HTTPException(400, why_s)
    except HTTPException as e:
        row.update(status='skipped', err=str(e.detail)[:140])
        async with _fw_lock:   # the same refusal is booked once per 15 min (the keeper keeps retrying quietly)
            d = _fw_load()
            if row.get('side') == 'buy' or not _fw.logged_recently(d.get('ledger'), row, now):   # buy misses all count (2 → benched)
                _fw_record(d, row); _fw_save(d)
        return book
    async with _fw_lock:
        ok, why = _fw.check(row, cfg, _fw_load().get('ledger'), now, row['impactPct'])   # row carries the pool's liquidity
    if not ok or not _fw_signer_ready():
        row.update(status='skipped' if not ok else 'dry', err=why or 'signing not available — quoted only')
        async with _fw_lock:
            d = _fw_load(); _fw_record(d, row); _fw_save(d)
        return book
    async with _fw_lock:   # ⚡ txs that didn't land lately → this one pays a higher priority fee (24% of buys timed out at a flat fee)
        boost = _fw.landing_boost(_fw_load().get('ledger'), tid, now)
    try:
        for attempt in range(3):   # build + sign retried too (Jupiter / Circle blips); nothing is sent until a signed tx exists
            try:
                swap = await _fw_jup('POST', '/swap/v1/swap', json={'quoteResponse': q, 'userPublicKey': cfg['address'], 'wrapAndUnwrapSol': True, 'dynamicComputeUnitLimit': True,
                                                                    'prioritizationFeeLamports': {'priorityLevelWithMaxLamports': {'maxLamports': _fw.priority_cap(attempt, boost), 'priorityLevel': 'veryHigh' if attempt or boost else 'high'}}})