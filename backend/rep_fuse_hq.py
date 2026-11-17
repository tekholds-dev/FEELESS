"""🧹 Fuse HQ — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


def _prime_cards():
    """The tier cards on file: fuse_hq.json › prime.cards → {tpl: card} (the parsed, cached copy — read only)."""
    rs = _rs()
    return (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}


def _real_card(default=None):
    """The first real-money tier card on file, else `default`."""
    rs = _rs()
    return next((c for c in rs._prime_cards().values() if (c or {}).get('real')), default)


def _card_rules():
    rs = _rs()
    return rs._hq.clean_rules(rs._json_load(rs.FUSE_HQ_PATH, {}).get('cardRules'))


def _ledger_by_sig():
    """Fee ledger rows by signature (rebuilt only when the cached ledger object changes)."""
    rs = _rs()
    led = rs._json_load(rs.FEE_LEDGER_PATH, {})
    if rs._ledger_idx['src'] is not led:
        rs._ledger_idx.update(src=led, by={r.get('sig'): r for v in led.values() for r in (v or []) if r.get('sig')})
    return rs._ledger_idx['by']


def _card_fees(pos, by_sig=None):
    """FEELESS fees actually paid on a card (its buy + sell signatures found in the fee ledger)."""
    rs = _rs()
    by_sig = by_sig if by_sig is not None else rs._ledger_by_sig()
    sigs = {s for leg in pos.get('legs') or [] for s in [leg.get('sig'), *(leg.get('sellSigs') or [leg.get('sellSig')])] if s}
    return round(sum(rs._fuse._f((by_sig.get(s) or {}).get('feeUsd')) for s in sigs), 6)


def _exit_fee(r):
    rs = _rs()
    cfg = rs._fee_cfg(); rl = rs._card_rules()
    return rs._hq.exit_fee_usd(r, rs._hq.clean_bundle(cfg.get('bundle')), int(cfg.get('platformFeeBps') or 0), rl['netFeeUsdPerLeg'])


async def _fuse_yield_tick(d, now):
    """💸 Auto-collect: re-arm cards that just collected (base = held now); alert once when held ≥ base × (1 + at%) with a
    pre-filled Collect-profit link (sells only the gain). The holder's wallet still approves — FEELESS never signs."""
    rs = _rs()
    ys = [x for x in d.get('positions') or [] if x.get('autoYield') and not x.get('closedAt') and not x['autoYield'].get('firedAt')]
    if not ys:
        return 0
    px = await rs._hq_prices([leg for x in ys for leg in x['legs']])
    upd, fired = {}, []
    for x in ys:
        r = rs._hq.position_pnl(x, px)
        y = x['autoYield']
        if y.get('rebase'):
            upd[x['id']] = {'base': round(rs._hq.held_value(r), 6), 'rebase': False}
        elif rs._hq.yield_due(r, y):   # price move only — fees are paid per trade and shown on the receipt
            pct = rs._hq.collect_pct(r, y)
            upd[x['id']] = {'firedAt': now}
            fired.append((x, r, pct))
    if upd:
        async with rs._admin_lock:
            d2 = rs._json_load(rs.FUSE_HQ_PATH, {})
            for x in d2.get('positions') or []:
                if x['id'] in upd and x.get('autoYield'):
                    x['autoYield'].update(upd[x['id']])
            rs._json_save(rs.FUSE_HQ_PATH, d2)
    for x, r, pct in fired:
        if x.get('onProfit') == 'compound':   # ♻ compound: move the gain from the winners into the rest of the card
            rs.notify(x['wallet'], 'fuse-guard', f"♻ {x.get('name') or 'Your Fuse card'} hit your +{x['autoYield']['at']:.0f}% level — compound it: trim the winners, top up the rest. One approval (numbers in My cards).",
                   url=f"/terminal/fuse?tab=cards&rebalance={x['id']}", once=f"compound-{x['id']}-{x['autoYield'].get('armedAt')}-{int(x['autoYield']['base'] * 100)}",
                   meta={'claim': f"Held value up {x['autoYield']['at']:.0f}% on your base", 'source': 'Fuse P&L (live prices)'})
            continue
        rs.notify(x['wallet'], 'fuse-guard', f"💸 {x.get('name') or 'Your Fuse card'} hit your +{x['autoYield']['at']:.0f}% level — collect the gain (sells {pct:.0f}% of each leg, your base stays in). One approval (numbers in My cards).",
               url=f"/terminal/fuse?tab=cards&collect={x['id']}&pct={pct}", once=f"yield-{x['id']}-{x['autoYield'].get('armedAt')}-{int(x['autoYield']['base'] * 100)}",
               meta={'claim': f"Held value up {x['autoYield']['at']:.0f}% on your base", 'source': 'Fuse P&L (live prices)'})
    return len(fired)


async def _fuse_swap_tick(d, now):
    """Swap mode (holder's choice per card): when a leg fails a runner gate or drops past swapDropPct, alert ONCE per leg
    with a pre-filled ⇄ Switch (sell the weak leg, buy the best gated runner) — one approval. Hold mode is never touched."""
    rs = _rs()
    sw = [x for x in d.get('positions') or [] if x.get('mode') == 'swap' and not x.get('closedAt') and now >= rs._hq.next_switch_at(x)]   # 1 rotation / 24h
    await rs._rounds_out_notice(d, now)
    sw = [x for x in sw if rs._hq.rounds_left(x, rs._is_staff(x['wallet'])) > 0]   # 🔁 out of rounds → no auto rounds until +5
    if not sw:
        return 0
    live, px = await rs.asyncio.gather(rs._runner_live(), rs._hq_prices([leg for x in sw for leg in x['legs']]))
    failing = {x['mint']: x.get('gates') or ['failed a gate'] for x in live['dropped']}
    rules = rs._card_rules(); n = 0
    for x in sw:
        pnl_ = rs._hq.position_pnl(x, px)
        pool_ = live['passing']
        if rs._hq.cycle_pick(x, pnl_.get('pnlPct')) == 'majors':   # 🔄 adaptive cycle: a losing card swaps its weak coin into a major
            pool_ = [{'mint': m.get('baseAddress'), 'symbol': m.get('symbol'), 'pairAddress': m.get('pairAddress'), 'logo': m.get('logo'), 'score': 100} for m in await rs._majors_rows() if m.get('pairAddress')]
        s = rs._hq.swap_suggest(pnl_, failing, pool_, rules['swapDropPct'], set(x.get('frozen') or []) | rs._hq.coins_not_due(x, now))
        if not s:
            continue
        n += 1
        win = int(now // (rs._hq.rotate_hours(x.get('rotateHours')) * 3600))   # the card's own clock (5m … 24h)
        await rs._spend_round(x, f"swap-{win}")
        rs.notify(x['wallet'], 'fuse-guard', f"⇄ {x.get('name') or 'Your Fuse card'}: ${s['out']['symbol']} {s['why']} — swap it for ${s['in']['symbol']} (gated runner, score {round(rs._fuse._f(s['in'].get('score')))}). One approval.",
               url=f"/terminal/fuse?tab=cards&switch={x['id']}&out={s['out']['pairAddress']}&in={s['in']['mint']}&sym={s['in']['symbol']}&pair={s['in'].get('pairAddress') or ''}",
               once=f"swap-{x['id']}-{win}", meta={'claim': s['why'], 'source': 'Runner gates + Fuse P&L (live prices)'})
    return n


async def _spend_round(x, key):
    """Spend one of the card's rounds for this alert window (staff cards are unlimited)."""
    rs = _rs()
    if rs._is_staff(x['wallet']):
        return
    async with rs._admin_lock:
        d2 = rs._json_load(rs.FUSE_HQ_PATH, {})
        for x2 in d2.get('positions') or []:
            if x2['id'] == x['id'] and rs._hq.use_round(x2, key):
                rs._json_save(rs.FUSE_HQ_PATH, d2)
                x.update(roundsLeft=x2['roundsLeft'], lastRoundKey=key)


async def _rounds_out_notice(d, now):
    """A card that spent its last round gets ONE notice with the +5 offer (pay now, or let compound pay when allowed)."""
    rs = _rs()
    cfg = rs._rounds_cfg()
    out = [x for x in d.get('positions') or [] if not x.get('closedAt') and (x.get('mode') == 'swap' or x.get('parked')) and not x.get('outOfRoundsAt')
           and rs._hq.rounds_left(x, rs._is_staff(x['wallet'])) <= 0]
    if not out:
        return
    # 💸 cards that pay their own fees: up more than the pack price → +5 rounds charged to the compound (owed till the next take)
    auto = [x for x in out if x.get('autoFees', True)]
    px = await rs._hq_prices([l for x in auto for l in x['legs']]) if auto else {}
    pnl = {x['id']: rs._hq.position_pnl(x, px)['pnlUsd'] for x in auto}
    paid_ = set()
    async with rs._admin_lock:
        d2 = rs._json_load(rs.FUSE_HQ_PATH, {})
        for x2 in d2.get('positions') or []:
            if x2['id'] in {x['id'] for x in out}:
                if x2['id'] in pnl and x2.setdefault('autoFees', True) and rs._hq.auto_rounds(x2, cfg, pnl[x2['id']]):
                    paid_.add(x2['id'])
                else:
                    x2['outOfRoundsAt'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d2)
    for x in [x for x in out if x['id'] in paid_]:
        rs.notify(x['wallet'], 'fuse-card', f"🔁 {x.get('name') or 'Your Fuse card'} paid +{cfg['step']} rounds from its profit (${cfg['per5Usd']:.2f}, settled at the next profit take).",
               url=f"/terminal/fuse?tab=cards&card={x['id']}", once=f"rounds-auto-{x['id']}-{len(x.get('roundBuys') or [])}", meta={'claim': 'Card pays its fees from profit', 'source': 'Fuse cards'})
    out = [x for x in out if x['id'] not in paid_]
    for x in out:
        rs.notify(x['wallet'], 'fuse-card', f"🔁 {x.get('name') or 'Your Fuse card'} used its {rs._hq.ROUNDS_DEFAULT} auto rounds. +{cfg['step']} for ${cfg['per5Usd']:.2f}{' — or let its compound pay' if cfg['compoundPay'] else ''}.",
               url=f"/terminal/fuse?tab=cards&card={x['id']}", once=f"rounds-out-{x['id']}-{len(x.get('roundBuys') or [])}", meta={'claim': 'Rounds used', 'source': 'Fuse cards'})


async def _fuse_buyback_tick(d, now):
    """🅿 Park & buy-back (real cards, non-custodial): a parked coin that's been SOLD and is back at its stop-out entry with
    buyers leading → ONE alert with a pre-filled buy back into the card (the holder approves)."""
    rs = _rs()
    rows = [(x, pa, pk) for x in d.get('positions') or [] if not x.get('closedAt') for pa, pk in (x.get('parked') or {}).items()
            if not pk.get('alertedAt') and any(l['pairAddress'] == pa and l.get('soldUsd') is not None for l in x['legs']) and rs._hq.rounds_left(x, rs._is_staff(x['wallet'])) > 0]
    if not rows:
        return 0
    pairs = await rs._fuse_pairs([{'chainId': 'solana', 'pairAddress': pa} for _, pa, _ in rows])
    fired = []
    for x, pa, pk in rows:
        p = pairs.get(pa) or {}; tx = (p.get('txns') or {}).get('h1') or {}; b, s_ = rs._fuse._f(tx.get('buys')), rs._fuse._f(tx.get('sells'))
        mom = {'buyShare': b / (b + s_) * 100 if b + s_ else 0, 'chg1h': rs._fuse._f((p.get('priceChange') or {}).get('h1'))}
        if rs._hq.buyback_due(pk, rs._fuse._f(p.get('priceUsd')), mom):
            fired.append((x, pa, pk))
    if fired:
        async with rs._admin_lock:
            d2 = rs._json_load(rs.FUSE_HQ_PATH, {})
            for x2 in d2.get('positions') or []:
                for x, pa, _ in fired:
                    if x2['id'] == x['id'] and pa in (x2.get('parked') or {}):
                        x2['parked'][pa]['alertedAt'] = now
                        if not rs._is_staff(x2['wallet']):
                            rs._hq.use_round(x2, f"buyback-{pa}-{int(now)}")
            rs._json_save(rs.FUSE_HQ_PATH, d2)
    for x, pa, pk in fired:
        rs.notify(x['wallet'], 'fuse-guard', f"↩ ${pk.get('symbol')} is back at your entry with buyers leading — buy it back into {x.get('name') or 'your card'}. One approval.",
               url=f"/terminal/fuse?tab=cards&topup={x['id']}&pair={pa}", once=f"buyback-{x['id']}-{pa}-{int(pk.get('at') or 0)}",
               meta={'claim': 'Price back at the stop-out entry, buyers ≥ 50%', 'source': 'Live pool data'})
    return len(fired)


async def _fuse_leg_tick(d, now):
    """🎯 Per-coin take-profit / stop-loss: alert once per limit with that coin's sell pre-filled (one approval)."""
    rs = _rs()
    lg = [x for x in d.get('positions') or [] if (x.get('legGuard') or rs._fuse._f(x.get('rideAt')) > 0) and not x.get('closedAt')]
    if not lg:
        return 0
    px = await rs._hq_prices([leg for x in lg for leg in x['legs']])
    fired, rides = [], {}
    for x in lg:
        r_ = rs._hq.position_pnl(x, px)
        hits_, riding_, st_ = rs._hq.ride_hits(r_, x.get('rideAt'), x.get('rideTrail'), x.get('rides'))   # ❄ freeze + peak trail (alerts only)
        if st_ != (x.get('rides') or {}):
            rides[x['id']] = st_
        for leg, why in hits_:
            fired.append((x, leg, 'ride', why))
        for leg, kind, pct in rs._hq.leg_limit_hits(r_, x.get('legGuard') or {}):
            if kind == 'sl' and rs._hq.coin_sl_mode(x, leg['pairAddress']) == 'hold':   # ❄ hold: no stop alerts (card or this coin)
                continue
            if kind == 'tp' and leg['pairAddress'] in riding_:   # a riding coin's TP waits — the peak trail sells it
                continue
            fired.append((x, leg, kind, pct))
    if rides and not fired:
        async with rs._admin_lock:
            d2 = rs._json_load(rs.FUSE_HQ_PATH, {})
            for x in d2.get('positions') or []:
                if x['id'] in rides:
                    x['rides'] = rides[x['id']]
            rs._json_save(rs.FUSE_HQ_PATH, d2)
    if not fired:
        return 0
    async with rs._admin_lock:
        d2 = rs._json_load(rs.FUSE_HQ_PATH, {})
        ids = {(x['id'], leg['pairAddress']) for x, leg, k_, _ in fired if k_ != 'ride'}
        parks = {(x['id'], leg['pairAddress']): leg for x, leg, kind, _ in fired if kind == 'sl' and rs._hq.coin_sl_mode(x, leg['pairAddress']) == 'park'}
        for x in d2.get('positions') or []:
            if x['id'] in rides:
                x['rides'] = rides[x['id']]
            for pa, g in (x.get('legGuard') or {}).items():
                if (x['id'], pa) in ids:
                    g['firedAt'] = now
                if (x['id'], pa) in parks:   # 🅿 remember the stop-out entry: a buy-back alert comes when price is back here
                    lg_ = parks[(x['id'], pa)]
                    x.setdefault('parked', {})[pa] = {'entry': rs._fuse._f(lg_.get('usd')) / max(rs._fuse._f(lg_.get('tokens')), 1e-18), 'symbol': lg_.get('symbol'), 'mint': lg_.get('mint'), 'at': now}
        rs._json_save(rs.FUSE_HQ_PATH, d2)
    for x, leg, kind, pct in fired:
        if kind == 'ride':   # ❄ the frozen coin came off its peak — sell it, one approval (no P&L in the notice text)
            rs.notify(x['wallet'], 'fuse-guard', f"❄ ${leg.get('symbol')} in {x.get('name') or 'your Fuse card'} rode its run and {pct}. Sell it — one approval (numbers in My cards).",
                   url=f"/terminal/fuse?tab=cards&collect={x['id']}&pct=100&legs={leg['pairAddress']}", once=f"leg-ride-{x['id']}-{leg['pairAddress']}-{int((x.get('rides') or {}).get(leg['pairAddress'], {}).get('peak', 0) * 1000)}",
                   meta={'claim': f"Frozen at +{rs._fuse._f(x.get('rideAt')):g}%, {pct}", 'source': 'Fuse P&L (live prices)'})
            continue
        what = f"hit its +{x['legGuard'][leg['pairAddress']]['tp']:g}% take-profit" if kind == 'tp' else f"hit its −{x['legGuard'][leg['pairAddress']]['sl']:g}% stop"
        rs.notify(x['wallet'], 'fuse-guard', f"{'🎯' if kind == 'tp' else '🛑'} ${leg.get('symbol')} in {x.get('name') or 'your Fuse card'} {what}. Sell it — one approval (numbers in My cards).",
               url=f"/terminal/fuse?tab=cards&collect={x['id']}&pct=100&legs={leg['pairAddress']}", once=f"leg-{kind}-{x['id']}-{leg['pairAddress']}",
               meta={'claim': f"{leg.get('symbol')} {pct:+.1f}% since your buy", 'source': 'Fuse P&L (live prices)'})
    return len(fired)

