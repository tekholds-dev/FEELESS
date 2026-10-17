"""🌊 COIN FLOW — live buys vs sells from a pool's own swaps (pure, tested).

Owner, 2026-10-08: "yes, flow exit — it's also a feature per coin". A stop fires AFTER the price fell; flow sees sellers take over
while it is happening. Reads the candles service's trade tape (`/api/candles/trades/{chain}/{pool}`: ts · buy/sell · $ · wallet).

  · window()   the last FLOW_SEC of swaps → buy $, sell $, trades, the price move across them, the biggest single sell
  · exit_why() 🌊 FLOW EXIT — sellers in charge (sell $ ≥ ratio × buy $, enough $ and trades) while the price slides
  · rug_why()  🚨 RUG RADAR — the creator sells, a top-10 / bundle / sniper wallet dumps, or one sell is most of the flow
  · entry_why() 🌊 FLOW ENTRY — don't buy into a minute where sellers lead (a reason, or None = flow is fine / unknown)
Thresholds are hand-set to start; every flow / rug exit is scored by what the coin did next (`trench.meta_track`), so the record
says whether they save money. A read of the tape, never a promise.
"""
from datetime import datetime, timezone

FLOW_SEC = 90
MODES = {'off': None,
         'normal': {'ratio': 2.0, 'minUsd': 60.0, 'minTrades': 6, 'minDrop': 3.0},
         'tight': {'ratio': 1.5, 'minUsd': 25.0, 'minTrades': 4, 'minDrop': 1.5}}
RUG_DEV_USD = 20.0       # the creator selling this much inside the window
RUG_WHALE_USD = 100.0    # a top-10 / bundle / sniper wallet selling this much
RUG_ONE_SHARE = 0.5      # one sell ≥ half the window's flow …
RUG_ONE_USD = 300.0      # … and at least this much
RUG_ONE_POOL_PCT = 3.0   # … and ≥ this % of the pool's liquidity (2026-10-09: the radar sold STONK / WETH / RAY / Fartcoin / DARK ×3 on a
                         # whale's $1K–13K sell into a deep pool — 23 rug exits, median −0.4% an hour later: it saved nothing, it churned)


from fnum import nan_safe as _f


def _ts(t):
    v = t.get('ts') if isinstance(t, dict) else None
    if isinstance(v, (int, float)):
        return float(v) / (1000.0 if v > 1e11 else 1.0)
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00')).astimezone(timezone.utc).timestamp()
    except (TypeError, ValueError):
        return 0.0


def window(trades, now, sec=FLOW_SEC):
    """→ {buyUsd, sellUsd, n, sellShare, pxChg (% first → last trade), bigSell {usd, wallet}, sells [(wallet, usd)]} or None (no trades)."""
    rows = sorted((t for t in (trades or []) if isinstance(t, dict) and now - _ts(t) <= sec and _ts(t) <= now + 5), key=_ts)
    if not rows:
        return None
    buy = sum(_f(t.get('usd')) for t in rows if t.get('kind') == 'buy')
    sell = sum(_f(t.get('usd')) for t in rows if t.get('kind') == 'sell')
    pxs = [_f(t.get('price')) for t in rows if _f(t.get('price')) > 0]
    big = max((t for t in rows if t.get('kind') == 'sell'), key=lambda t: _f(t.get('usd')), default=None)
    return {'buyUsd': round(buy, 2), 'sellUsd': round(sell, 2), 'n': len(rows), 'sellShare': round(sell / (buy + sell) * 100, 1) if buy + sell > 0 else None,
            'pxChg': round((pxs[-1] / pxs[0] - 1) * 100, 2) if len(pxs) >= 2 else 0.0,
            'buyers': len({t.get('wallet') for t in rows if t.get('kind') == 'buy' and t.get('wallet')}),
            'sellers': len({t.get('wallet') for t in rows if t.get('kind') == 'sell' and t.get('wallet')}),
            'bigSell': {'usd': round(_f(big.get('usd')), 2), 'wallet': big.get('wallet')} if big else None,
            'sells': [(t.get('wallet'), _f(t.get('usd'))) for t in rows if t.get('kind') == 'sell']}


def exit_why(win, mode='normal'):
    """🌊 Sellers have taken over this coin right now → the reason, else None."""
    m = MODES.get(mode)
    if not m or not win:
        return None
    b, s = _f(win.get('buyUsd')), _f(win.get('sellUsd'))
    if win.get('n', 0) < m['minTrades'] or s < m['minUsd'] or s < m['ratio'] * max(b, 0.01) or _f(win.get('pxChg')) > -m['minDrop']:
        return None
    return f"🌊 sellers took over: ${s:,.0f} sold vs ${b:,.0f} bought in {FLOW_SEC}s, price {_f(win['pxChg']):+.1f}%"


# 🩸 POOL DRAINING FAST (2026-10-15, scripts/rug-replay.py + rug-signal-test.py on 14 real rugs + 10 young winners): the pool's SOL down
# ≥ DRAIN_FAST_PCT in DRAIN_FAST_SEC caught 3/14 rugs a median 27s before the pull and would have sold 0/10 winners (shipped: ≤ 1 in 10).
# Live it is read from the tape: SOL out of the pool in 30s ≈ $ sold − $ bought, against the pool's SOL side (liquidity ÷ 2).
DRAIN_FAST_SEC = 30
DRAIN_FAST_PCT = 15.0


def pool_drain(trades, now, liq_usd, sec=DRAIN_FAST_SEC, pct=DRAIN_FAST_PCT):
    """→ the reason when the last `sec` of real swaps took ≥ `pct`% of the pool's SOL side out, else None (unknown depth = not judged)."""
    side = _f(liq_usd) / 2
    if side <= 0:
        return None
    w = window(trades, now, sec)
    if not w:
        return None
    net = _f(w.get('sellUsd')) - _f(w.get('buyUsd'))
    if net >= side * pct / 100:
        return f"🩸 pool draining fast: ${net:,.0f} net sold in {sec}s = {net / side * 100:.0f}% of the pool's SOL side"
    return None


def rug_why(win, creator=None, watch=(), liq=None):
    """🚨 a dump from a wallet that matters → the reason, else None. `watch` = top-10 / bundle / sniper wallets of this coin."""
    if not win:
        return None
    sells = win.get('sells') or []
    dev = sum(u for w, u in sells if creator and w == creator)
    if dev >= RUG_DEV_USD:
        return f"🚨 the creator sold ${dev:,.0f} in the last {FLOW_SEC}s"
    ws = set(watch or ())
    big = {}
    for w, u in sells:
        if w in ws:
            big[w] = big.get(w, 0.0) + u
    if big and max(big.values()) >= RUG_WHALE_USD:
        return f"🚨 a top holder / bundle wallet dumped ${max(big.values()):,.0f} in the last {FLOW_SEC}s"
    tot = _f(win.get('buyUsd')) + _f(win.get('sellUsd'))
    one = _f((win.get('bigSell') or {}).get('usd'))
    deep = _f(liq) > 0 and one < _f(liq) * RUG_ONE_POOL_PCT / 100   # a sell the pool absorbs easily is trading, not a rug (unknown depth = judged as before)
    if one >= RUG_ONE_USD and tot > 0 and one / tot >= RUG_ONE_SHARE and _f(win.get('pxChg')) < 0 and not deep:
        return f"🚨 one wallet sold ${one:,.0f} — {one / tot * 100:.0f}% of all flow in {FLOW_SEC}s"
    return None


TAPES = {'burst': '⚡ burst', 'absorb': '🧲 absorb', 'climax': '🏔 climax', 'dump': '🩸 dump', 'calm': '➖ calm'}


def tape_read(win):
    """🌊 THE TAPE (owner, 2026-10-09: "buy-vs-sell mechanics need to be complex for simple trenches — get us in and out at the perfect
    time"): the last 90s of real swaps read as ONE of —
      ⚡ burst  — buys ≥ 2× sells (≥ $150 bought) and the price climbing but not spiking (+0.5…+4%): the move is starting
      🧲 absorb — sells ≥ 1.5× buys (≥ $100 sold) but the price HOLDS (≥ −0.5%): buyers are soaking up the selling
      🏔 climax — buys ≥ 1.5× sells (≥ $300 bought) but the price stalls (≤ +0.3%) or the spike is past +6%: a top is forming
      🩸 dump   — sells ≥ 2× buys and the price ≤ −2%
      ➖ calm   — none of the above · None = too few trades (< 4) to read. Pure."""
    if not win or win.get('n', 0) < 4:
        return None
    b, s, px = _f(win.get('buyUsd')), _f(win.get('sellUsd')), _f(win.get('pxChg'))
    if s >= 2 * max(b, 0.01) and px <= -2.0:
        return 'dump'
    if b >= 1.5 * max(s, 0.01) and b >= 300 and (px <= 0.3 or px > 6.0):
        return 'climax'
    if b >= 2 * max(s, 0.01) and b >= 150 and 0.5 <= px <= 4.0:
        return 'burst'
    if s >= 1.5 * max(b, 0.01) and s >= 100 and px >= -0.5:
        return 'absorb'
    return 'calm'


def entry_why(win):
    """🌊 FLOW ENTRY: a reason not to buy right now, or None (flow fine, or no tape to judge). A 🩸 dump or a 🏔 climax (buying the top)
    waits; sellers leading on a sliding price waits."""
    if not win or win.get('n', 0) < 4:
        return None
    t = tape_read(win)
    if t in ('dump', 'climax'):
        return f"{TAPES[t]} on the last {FLOW_SEC}s tape — waits"
    b, s = _f(win.get('buyUsd')), _f(win.get('sellUsd'))
    if s > 1.3 * max(b, 0.01) and _f(win.get('pxChg')) < 0:
        return f"sellers lead the last {FLOW_SEC}s (${s:,.0f} sold vs ${b:,.0f} bought)"
    return None


CLIMAX_GAIN = 20.0     # 🏔 a coin up at least this much sells half its PROFIT into a buying climax (once per 15 min)
CLIMAX_PART = 0.5
CLIMAX_EVERY = 900


def leg_mode(leg, card_mode):
    """A coin's own flow-exit setting beats the card's: leg `flowExit` 'off' | 'normal' | 'tight' (missing = the card's)."""
    m = (leg or {}).get('flowExit')
    return m if m in MODES else card_mode if card_mode in MODES else 'off'


def watched(leg):
    """Coins the flow exit judges: held, not being bought, not a reserved seat, not frozen by the owner. Riders and ride-or-rug tickets
    are NOT flow-exited (their own plan decides) — the rug radar still watches them."""
    l = leg or {}
    return _f(l.get('units')) > 0 and l.get('real') and not l.get('buying') and not l.get('placeholder')


def flow_exits(card, flows, px_by_mint, cfg, now, sell_usd=None, intel=None):
    """Apply flow exits + the rug radar to a REAL card → (new card or the SAME object, [(symbol, kind, why)]).
    A coin that trips leaves the card like a fast stop: its seat becomes a reserved placeholder, the keeper sells next pass."""
    c, hits = None, []
    mode_card = (cfg or {}).get('flowExit', 'off')
    rug_on = (cfg or {}).get('rugRadar', True)
    for i, l in enumerate((card or {}).get('legs') or []):
        if not watched(l):
            continue
        win = (flows or {}).get(l.get('pairAddress'))
        it = (intel or {}).get(l.get('mint')) or {}
        why, kind = None, None
        if rug_on:
            why = rug_why(win, it.get('creator'), it.get('watch') or (), l.get('liqNow') or l.get('liq'))
            kind = 'rug' if why else None
        held_ok = now - float(l.get('at') or 0) >= float((cfg or {}).get('flowMinHoldMins') or 0) * 60   # 🌊 tight exits wait out the first wobble
        px_c, e_c = _f((px_by_mint or {}).get(l.get('mint'))), _f(l.get('entry'))
        if (cfg or {}).get('flowExit', 'off') != 'off' and tape_read(win) == 'climax' and px_c > 0 and e_c > 0 and (px_c / e_c - 1) * 100 >= CLIMAX_GAIN \
                and now - _f(l.get('climaxAt')) >= CLIMAX_EVERY and not l.get('frozen'):
            # 🏔 SELL INTO STRENGTH: buyers are still piling in but the price stopped going up — half the profit goes now, the rest rides
            units, cost = _f(l['units']), _f(l.get('costUsd')) or _f(l['units']) * e_c
            part = max(0.0, (units * px_c - cost) * CLIMAX_PART) / (units * px_c)
            if part > 0:
                if c is None:
                    c = {**card, 'legs': [dict(x) for x in card['legs']], 'events': list(card.get('events') or [])}
                got = sell_usd(units * part, px_c, l.get('liq')) if sell_usd else units * part * px_c
                c['legs'][i] = {**c['legs'][i], 'units': units * (1 - part), 'costUsd': round(cost * (1 - part), 6), 'trimAt': now, 'climaxAt': now}
                c['cash'] = round(_f(c.get('cash')) + got, 6)
                c['events'].append({'at': now, 'kind': 'skim', 'flowKind': 'climax', 'mint': l.get('mint'), 'px': px_c, 'symbol': l.get('symbol'), 'usd': round(got, 4), 'to': ['card'], 'fast': True,
                                    'why': f"🏔 buying climax on ${l.get('symbol')} (+{(px_c / e_c - 1) * 100:.0f}%): ${_f(win.get('buyUsd')):,.0f} bought in {FLOW_SEC}s but the price stalled — half its profit sold into the buying"})
                hits.append((l.get('symbol'), 'climax', 'buying climax'))
                continue
        if not why and held_ok and not l.get('frozen') and not l.get('ride') and not l.get('rideOrRug'):
            why = exit_why(win, leg_mode(l, mode_card))
            kind = 'flow' if why else None
        if not why:
            continue
        px = _f((px_by_mint or {}).get(l.get('mint')))
        if px <= 0:
            continue
        if c is None:
            c = {**card, 'legs': [dict(x) for x in card['legs']], 'events': list(card.get('events') or [])}
        out = sell_usd(_f(l['units']), px, l.get('liq')) if sell_usd else _f(l['units']) * px
        pct = (px / _f(l.get('entry')) - 1) * 100 if _f(l.get('entry')) > 0 else 0.0
        c['legs'][i] = {**{k: v for k, v in l.items() if k not in ('wantUnits', 'buyingSince')}, 'units': 0.0, 'costUsd': 0.0, 'reserveUsd': round(out, 6),
                        'buying': False, 'entry': px, 'at': now, 'placeholder': True}
        c['cash'] = round(_f(c.get('cash')) + out, 6)
        c['events'].append({'at': now, 'kind': kind, 'symbol': l.get('symbol'), 'usd': round(out, 4), 'to': ['cash'], 'fast': True, 'pct': round(pct, 1),
                            'mint': l.get('mint'), 'px': px, 'why': f"{why} — sold at {pct:+.0f}%, seat reserved for the next coin"})
        hits.append((l.get('symbol'), kind, why))
    return (c if c is not None else card), hits


# ── 🧬 TRENCH META: the vitals of a coin too young for a chart (owner, 2026-10-11: "add on vitals needed for them to TRENCH META") ──────
META_SEC = 300            # the last 5 minutes of real swaps
META_MIN_TRADES = 8       # fewer = THIN (nothing to judge)
META_MIN_WALLETS = 6      # distinct wallets trading
META_ONE_WALLET = 45.0    # one wallet's share of all buying ≥ this = ONE WALLET (a one-man pump)
META_SAME_SIZE = 50.0     # trades of the exact same $ size ≥ this % = BOT (a loop, not a crowd)
META_SELL_RATIO = 1.5     # sells ≥ 1.5× buys = DUMPING


VITAL_MIN_TRADES = 4      # fewer swaps in the window = THIN (not judged — never a block on its own)
VITAL_MIN_USD = 25.0      # … or this little money moved
VITAL_SELL_RATIO = 1.5    # sells ≥ 1.5× buys on a falling price = SELLERS lead
VITAL_BUY_RATIO = 1.3     # buys ≥ 1.3× sells with ≥ VITAL_MIN_BUYERS different wallets = BUYERS lead
VITAL_MIN_BUYERS = 3
VITAL_HOT_BUYERS = 8      # this many different buyers inside 90s = a crowd (owner: "volume jumping with hella buyers")
VITAL_SPIKE_PCT = 6.0     # the price up this much inside the window = the top of a spike (not an entry)
VITAL_STATES = ('BUYERS', 'BALANCED', 'SELLERS', 'PEAK', 'THIN')


def vital(win):
    """🌊 THE BUY / SELL VITAL (owner, 2026-10-13: "buy/sell bar should be a vital and be wired to Reaper and whomever else who watches";
    "learn not to buy at the peak"). The last 90s of REAL swaps → ONE state every desk reads the same way:
      BUYERS   — buys ≥ 1.3× sells by $ with ≥ 3 different buyers (`hot` = ≥ 8 buyers: a crowd)
      SELLERS  — sells ≥ 1.5× buys on a falling price, or the tape reads 🩸 dump
      PEAK     — a 🏔 buying climax (buyers pay up, the price stalls) or the price already +6% inside the window: the top, not an entry
      BALANCED — neither side leads · THIN — too few swaps to judge (never a block by itself)
    → {state, why, buyUsd, sellUsd, buyPct, n, buyers, sellers, pxChg, tape, hot} or None (no tape). Pure; a reading, never a promise."""
    if not win:
        return None
    b, s, n, px = _f(win.get('buyUsd')), _f(win.get('sellUsd')), int(_f(win.get('n'))), _f(win.get('pxChg'))
    nb, ns = int(_f(win.get('buyers'))), int(_f(win.get('sellers')))
    tot = b + s
    tp = tape_read(win)
    out = {'buyUsd': round(b, 2), 'sellUsd': round(s, 2), 'buyPct': round(b / tot * 100) if tot > 0 else None, 'n': n, 'buyers': nb, 'sellers': ns,
           'pxChg': round(px, 2), 'tape': tp, 'hot': nb >= VITAL_HOT_BUYERS}
    money = f"${b:,.0f} bought by {nb} vs ${s:,.0f} sold by {ns} in {FLOW_SEC}s"
    if n < VITAL_MIN_TRADES or tot < VITAL_MIN_USD:
        return {**out, 'state': 'THIN', 'why': f"{n} swaps, ${tot:,.0f} in {FLOW_SEC}s — too thin to read"}
    if tp == 'dump' or (s >= VITAL_SELL_RATIO * max(b, 0.01) and px < 0):
        return {**out, 'state': 'SELLERS', 'why': f"sellers lead: {money}, price {px:+.1f}%"}
    if tp == 'climax' or px >= VITAL_SPIKE_PCT:
        return {**out, 'state': 'PEAK', 'why': (f"buying climax: {money} but the price stalls ({px:+.1f}%)" if tp == 'climax' and px < VITAL_SPIKE_PCT
                                              else f"already {px:+.1f}% inside {FLOW_SEC}s — the top of the spike")}
    if b >= VITAL_BUY_RATIO * max(s, 0.01) and nb >= VITAL_MIN_BUYERS:
        return {**out, 'state': 'BUYERS', 'why': f"{'a crowd is buying' if nb >= VITAL_HOT_BUYERS else 'buyers lead'}: {money}, price {px:+.1f}%"}
    return {**out, 'state': 'BALANCED', 'why': f"no side leads: {money}, price {px:+.1f}%"}


def vital_block(v):
    """The vital's reason NOT to enter right now (Trigger + the fill gate), else None. THIN / no tape = not judged."""
    if v and v.get('state') in ('SELLERS', 'PEAK'):
        return v['why']
    return None


def trench_meta(trades, now, sec=META_SEC):
    """🧬 A launch's crowd from its tape alone — what a trencher checks before a candle chart exists. → {verdict, why, wallets, buyers,
    trades, buyUsd, sellUsd, topBuyerPct, sameSizePct, pxChg} · verdict ORGANIC (a real crowd buying) · BOT (same-size loop) · ONE WALLET
    (one buyer is the pump) · DUMPING (sellers lead) · THIN (too few trades). Pure; a reading, never a promise."""
    rows = sorted((t for t in (trades or []) if isinstance(t, dict) and 0 <= now - _ts(t) <= sec), key=_ts)
    n = len(rows)
    buy = sum(_f(t.get('usd')) for t in rows if t.get('kind') == 'buy'); sell = sum(_f(t.get('usd')) for t in rows if t.get('kind') == 'sell')
    wallets = {t.get('wallet') for t in rows if t.get('wallet')}
    by = {}
    for t in rows:
        if t.get('kind') == 'buy' and t.get('wallet'):
            by[t['wallet']] = by.get(t['wallet'], 0.0) + _f(t.get('usd'))
    top = round(max(by.values()) / buy * 100, 1) if by and buy > 0 else None
    sizes = {}
    for t in rows:
        k = round(_f(t.get('usd')), 2)
        if k > 0:
            sizes[k] = sizes.get(k, 0) + 1
    same = round(max(sizes.values()) / n * 100, 1) if sizes and n else None
    pxs = [_f(t.get('price')) for t in rows if _f(t.get('price')) > 0]
    out = {'trades': n, 'wallets': len(wallets), 'buyers': len(by), 'buyUsd': round(buy, 2), 'sellUsd': round(sell, 2), 'topBuyerPct': top, 'sameSizePct': same,
           'pxChg': round((pxs[-1] / pxs[0] - 1) * 100, 2) if len(pxs) >= 2 else 0.0}
    if n < META_MIN_TRADES or len(wallets) < 3:
        return {**out, 'verdict': 'THIN', 'why': f'{n} trades by {len(wallets)} wallets in {sec // 60} min — nothing to judge yet'}
    if same is not None and same >= META_SAME_SIZE and n >= 10:
        return {**out, 'verdict': 'BOT', 'why': f'{same:.0f}% of {n} trades are the exact same size — a loop, not a crowd'}
    if top is not None and top >= META_ONE_WALLET:
        return {**out, 'verdict': 'ONE WALLET', 'why': f'one wallet did {top:.0f}% of all buying — the pump is one buyer'}
    if sell >= META_SELL_RATIO * max(buy, 0.01):
        return {**out, 'verdict': 'DUMPING', 'why': f'${sell:,.0f} sold vs ${buy:,.0f} bought in {sec // 60} min'}
    if len(wallets) < META_MIN_WALLETS:
        return {**out, 'verdict': 'THIN', 'why': f'only {len(wallets)} wallets trading — not a crowd yet'}
    return {**out, 'verdict': 'ORGANIC', 'why': f'{len(by)} buyers · {len(wallets)} wallets · top buyer {top or 0:.0f}% · same-size {same or 0:.0f}% · ${buy:,.0f} in / ${sell:,.0f} out'}
