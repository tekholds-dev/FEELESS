"""⭐ ARENA PRIME: FEELESS's own top-tier cards, run FULLY AUTO on paper (no wallet, no money) so the automation is proven in
public before any trader's config goes auto. Pure functions — the service feeds prices + candidates every tick.

Each Prime card runs its dial (Safe / Balanced / Degen) with every automation ON:
  • auto take-profit / stop-loss per coin (the dial's TP / SL),
  • auto-compound: a take-profit's gain is rolled into the card's other coins by weight (never left idle),
  • auto-rotate: every `rotateHours` (default 6h) the `rotateCount` (default 2) weakest coins are swapped for the best gated
    candidates not already on the card; a stop-loss is replaced at once,
  • every action is an event with its reason, so the card's whole life is replayable.
P&L never includes fees (same rule as real cards); a flat paper fee per trade is tracked SEPARATELY as `feesUsd`.
"""
import math

# Three top tiers. Every coin on a Prime card is rated 3–5★ (anything weaker never gets in). Each card holds a STABLE anchor
# (a real major on Solana: SOL / JitoSOL / cbBTC …, never rotated, never stopped out) + deep pools + gated runners.
TEMPLATES = {   # anchors / pools / runners per card + the dial it runs
    # 5 top tiers. Majors = solid holds; "young" runners = pre-bond runners + clean graduated coins under 48h (every gate but pre-bond).
    'safe': {'label': '💎 Prime Diamond', 'tier': 'diamond', 'anchors': 1, 'pools': 0, 'runners': 3, 'tp': 900, 'sl': 35,
             'why': 'young coins held toward 10× — momentum decides ride / bank, SOL anchors the card'},
    'balanced': {'label': '🥇 Prime Gold', 'tier': 'gold', 'anchors': 2, 'pools': 1, 'runners': 1, 'tp': 50, 'sl': 15,
                 'why': 'two majors + a deep pool + one runner kicker'},
    'degen': {'label': '🔥 Prime Blaze', 'tier': 'blaze', 'anchors': 1, 'pools': 1, 'runners': 2, 'tp': 100, 'sl': 20,
              'why': 'one major, one pool, two runners — doubles get banked'},
    'next': {'label': '⚡ Prime Next Level', 'tier': 'next', 'anchors': 0, 'pools': 0, 'runners': 4, 'tp': 300, 'sl': 25,
             'why': 'all runners, 4× take-profit, house money rides — the floor goes to cash'},
    'ever': {'label': '♾ Prime Everlasting', 'tier': 'ever', 'anchors': 4, 'pools': 1, 'runners': 0, 'tp': 40, 'sl': 0,
             'why': 'SOL / BTC / ETH / JitoSOL + PUMP — never stopped, only rotated if a pool weakens'},
}
MIN_STARS = 3
HIT_PCT = 10.0      # a "good day" = the card is up ≥ +10% over 24h
DEFAULT_CFG = {'on': True, 'sizeUsd': 100.0, 'rotateHours': 1.0, 'rotateCount': 1, 'compound': True, 'paperFeeUsd': 0.10, 'floorPct': 20.0, 'slMode': 'replace'}
SL_MODES = ('replace', 'park', 'hold')   # on a stop: auto-replace · sell + park the slot (rebuy at entry with momentum) · hold
CFG_RANGES = {'sizeUsd': (10, 10000), 'rotateHours': (0.08, 48), 'rotateCount': (1, 3), 'paperFeeUsd': (0, 5), 'floorPct': (5, 25)}


def exit_plan(gain_pct, mom=None):
    """WHEN TO HODL vs SELL, from live momentum (chg1h, buyShare, vol accel = vol5m×12 vs vol1h):
      • 🚀 ride  — strong (1h ≥ +10%, buys ≥ 55%, volume not fading): take out ONLY the original cost (house money) once the
        coin has doubled, else just half the gain — the rest keeps running (this is how a 100×+ is held, not sold at +50%).
      • 🏦 bank  — fading (1h < 0, buys < 45% or volume dying): sell 75% of the coin now.
      • 💰 gain  — otherwise: sell just the gain, keep the cost basis riding.
    Returns (mode, fraction_of_units_to_sell, why). No momentum data → 'gain'."""
    m = mom or {}
    g = max(0.0, _f(gain_pct))
    if not m or g <= 0:
        return 'gain', (g / (100 + g)) if g else 0.0, 'no live momentum — sold the gain'
    ch, bs = _f(m.get('chg1h')), _f(m.get('buyShare'))
    accel = (_f(m.get('vol5m')) * 12 / _f(m.get('vol1h'))) if _f(m.get('vol1h')) else 1.0
    if ch >= 10 and bs >= 55 and accel >= 0.8:
        frac = (100 / (100 + g)) if g >= 100 else (g / (100 + g)) / 2
        return 'ride', frac, f"momentum strong (1h {ch:+.0f}%, {bs:.0f}% buys) — {'took out the original cost, house money rides' if g >= 100 else 'took half the gain, the rest rides'}"
    if ch < 0 or bs < 45 or accel < 0.4:
        return 'bank', 0.75, f"momentum fading (1h {ch:+.0f}%, {bs:.0f}% buys, volume ×{accel:.1f}) — banked 75%"
    return 'gain', g / (100 + g), 'steady momentum — sold the gain, cost keeps riding'


def fading(mom):
    m = mom or {}
    return bool(m) and (_f(m.get('chg1h')) < 0 and _f(m.get('buyShare')) < 50)


def stars(c, role):
    """1–5★ for a candidate. Anchors (real majors) = 5. Pools: 3 + deep (≥$1M) + busy (24h vol ≥ ½ depth). Runners by their
    gated score: ≥88 → 5, ≥75 → 4, ≥60 → 3, else 2 (kept off Prime)."""
    if role == 'anchor':
        return 5
    if role == 'pool':
        liq, vol = _f(c.get('liquidityUsd')), _f(c.get('volume24h'))
        return 3 + (liq >= 1_000_000) + (liq > 0 and vol / liq >= 0.5)
    sc = _f(c.get('score'))
    return 5 if sc >= 88 else 4 if sc >= 75 else 3 if sc >= 60 else 2


def rated(cands, role):
    """Only 3★+ candidates. ARENA-backed coins (on a battle / stage card, this round's runner picks, a lit card — `arena`
    flag set by the service) come first, then best stars; input order kept inside a level."""
    out = [{**c, 'stars': stars(c, role)} for c in cands]
    return sorted((c for c in out if c['stars'] >= MIN_STARS), key=lambda c: (not c.get('arena'), -c['stars']))


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def clean_cfg(p):
    out = dict(DEFAULT_CFG)
    for k, (lo, hi) in CFG_RANGES.items():
        if k in (p or {}):
            out[k] = min(hi, max(lo, _f(p[k])))
    out['rotateHours'], out['rotateCount'] = round(float(out['rotateHours']), 2), int(out['rotateCount'])
    for k in ('on', 'compound'):
        if k in (p or {}):
            out[k] = bool(p[k])
    if (p or {}).get('slMode') in SL_MODES:
        out['slMode'] = p['slMode']
    return out


def _leg(c, usd, now, role):
    px = _f(c.get('price'))
    return {'mint': c['mint'], 'pairAddress': c['pairAddress'], 'symbol': c.get('symbol'), 'role': role, 'entry': px, 'units': usd / px if px > 0 else 0.0,
            'costUsd': round(usd, 6), 'at': now, 'stars': c.get('stars') or stars(c, role), 'firstEntry': px}


def _picks(t, pools, runners, anchors):
    """anchors → pools → runners, 3★+ only, one slot per coin (a SOL pool never doubles the SOL anchor)."""
    seen, out = set(), []
    for src, role, n in ((anchors, 'anchor', t['anchors']), (pools, 'pool', t['pools']), (runners, 'runner', t['runners'])):
        k = 0
        for c in rated(src, role):
            if k >= n:
                break
            if _f(c.get('price')) > 0 and c.get('mint') not in seen:
                seen.add(c.get('mint')); out.append((c, role)); k += 1
    return out


def deal(tid, pools, runners, cfg, now, anchors=(), usd=None, keep=None):
    """A fresh Prime card from the best 3★+ candidates (gated + ranked by the caller). Equal $ per coin. `keep` re-deals an
    existing card (after its floor) while keeping its start, events and record — P&L stays honest across re-deals."""
    t = TEMPLATES[tid]
    picks = _picks(t, pools, runners, anchors)
    if not picks:
        return None
    size = usd if usd is not None else cfg['sizeUsd']
    each = size / len(picks)
    base = {'id': f'prime-{tid}', 'tpl': tid, 'label': t['label'], 'at': now, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': cfg['sizeUsd'], 'dayAt': now, 'dayStartUsd': cfg['sizeUsd'], 'days': [], 'lowPct': 0.0}
    c = {**base, **(keep or {})}
    c.update(lastRotateAt=now, legs=[_leg(x, each, now, r) for x, r in picks], cash=0.0, flooredAt=None)
    c['startUsd'] = (keep or {}).get('startUsd', cfg['sizeUsd'])
    c['feesUsd'] = round(_f(c['feesUsd']) + cfg['paperFeeUsd'] * len(picks), 4)
    c['events'] = list(c['events']) + [{'kind': 'deal', 'at': now, 'n': len(picks), 'why': 're-dealt after the floor' if keep else 'fresh card'}]
    return c


def value(card, prices):
    v = sum(l['units'] * (_f(prices.get(l['pairAddress'])) or l['entry']) for l in card['legs']) + card['cash'] + sum(_f(p['usd']) for p in (card.get('parked') or {}).values())
    return round(v, 4)


def tick(card, prices, pools, runners, cfg, now, anchors=(), mom=None):
    """One automation pass. Returns the updated card (mutated copy) — all actions logged as events with reasons."""
    t = TEMPLATES[card['tpl']]
    c = {**card, 'legs': [dict(l) for l in card['legs']], 'events': list(card['events'])}
    have = lambda: {l['mint'] for l in c['legs']}
    ev = lambda **e: c['events'].append({'at': now, **e})
    fee = cfg['paperFeeUsd']

    def best(role):
        src = rated(runners if role == 'runner' else anchors if role == 'anchor' else pools, role)
        return next((x for x in src if x['mint'] not in have() and _f(x.get('price')) > 0), None)
    c.setdefault('dayAt', c['at']); c.setdefault('dayStartUsd', c['startUsd']); c.setdefault('days', []); c.setdefault('lowPct', 0.0)

    # 0) a floored card sits in its anchor (cash-like) until the next day, then is re-dealt fresh at its current value
    if c.get('flooredAt') and now - c['flooredAt'] >= cfg['rotateHours'] * 3600:   # re-deal = the rotation clock (Cmd Ctr › Rotate every)
        v0 = value(c, prices)
        keep = {k: c[k] for k in c if k not in ('legs', 'cash', 'lastRotateAt')}
        # a NEW run starts at today's value (its own −floor); the ended run is kept on the record, never hidden
        keep['runs'] = (list(c.get('runs') or []) + [{'at': now, 'startUsd': c['startUsd'], 'endUsd': round(v0, 4), 'pct': round((v0 / (_f(c['startUsd']) or 1) - 1) * 100, 2)}])[-10:]
        keep.update(startUsd=round(v0, 4), dayStartUsd=round(v0, 4), dayAt=now, lowPct=0.0)
        nc = deal(c['tpl'], pools, runners, cfg, now, anchors, usd=v0, keep=keep)
        if nc:
            c = nc

    # 1) auto take-profit — HOW MUCH depends on momentum (exit_plan): ride / gain / bank → compound into the others or cash
    mom = mom or {}
    for l in c['legs']:
        px = _f(prices.get(l['pairAddress']))
        if px <= 0 or l['entry'] <= 0:
            continue
        g = (px / l['entry'] - 1) * 100
        if g >= t['tp']:
            mode, frac, why = exit_plan(g, mom.get(l['pairAddress']))
            sold = l['units'] * frac
            gain = sold * px
            l['units'] -= sold; l['entry'] = px; c['feesUsd'] += fee
            c['takenUsd'] += gain
            others = [o for o in c['legs'] if o is not l and _f(prices.get(o['pairAddress'])) > 0]
            label = f"+{g:.0f}% ≥ +{t['tp']}% · {why}"
            if cfg['compound'] and others:
                each = gain / len(others)
                for o in others:
                    opx = _f(prices.get(o['pairAddress']))
                    o['units'] += each / opx; o['costUsd'] += each
                c['compoundedUsd'] += gain; c['feesUsd'] += fee * len(others)
                ev(kind='tp', symbol=l['symbol'], usd=round(gain, 4), why=label, mode=mode, to=[o['symbol'] for o in others])
            else:
                c['cash'] += gain
                ev(kind='tp', symbol=l['symbol'], usd=round(gain, 4), why=label, mode=mode, to=['cash'])
    # 2) stop-loss (sl 0 = never stopped) — what happens follows cfg slMode:
    #    replace → sold and swapped at once for the best gated coin of the same role
    #    park    → sold to cash, the SLOT is kept; bought back when price is back at the stop-out entry with momentum
    #    hold    → never sold on a stop (the floor still protects the card)
    mode = cfg.get('slMode', 'replace')
    c['parked'] = dict(c.get('parked') or {})
    for l in list(c['legs']):
        px = _f(prices.get(l['pairAddress']))
        if l.get('role') == 'anchor' or not t['sl'] or mode == 'hold' or px <= 0 or l['entry'] <= 0:
            continue
        dd = (px / l['entry'] - 1) * 100
        if dd > -t['sl'] and not (dd <= -t['sl'] / 2 and fading(mom.get(l['pairAddress']))):   # early cut: half the stop + fading
            continue
        out_usd = l['units'] * px
        why = f"{dd:.0f}% ≤ −{t['sl']}%" if dd <= -t['sl'] else f"{dd:.0f}% and fading (1h down, sellers lead) — cut early"
        c['feesUsd'] += fee
        nxt = best(l['role']) if mode == 'replace' else None
        if nxt:
            c['legs'][c['legs'].index(l)] = _leg(nxt, out_usd, now, l['role']); c['feesUsd'] += fee
            ev(kind='sl', symbol=l['symbol'], usd=round(out_usd, 4), why=why, to=[nxt.get('symbol')])
        elif mode == 'park':
            c['legs'].remove(l)
            c['parked'][l['pairAddress']] = {**{k: l.get(k) for k in ('mint', 'pairAddress', 'symbol', 'role', 'stars', 'firstEntry')}, 'usd': round(out_usd, 6),
                                             'backAt': l['entry'], 'at': now, 'price': px}
            ev(kind='park', symbol=l['symbol'], usd=round(out_usd, 4), why=f"{why} — sold to SOL, slot kept; buys back at ${l['entry']:.6g} with momentum", to=['parked'])
        else:
            c['legs'].remove(l); c['cash'] += out_usd
            ev(kind='sl', symbol=l['symbol'], usd=round(out_usd, 4), why=why, to=['cash'])
    # 2b) parked coins come back: price ≥ the entry they stopped out from AND momentum not fading → bought back with the parked $
    for pa, pk in list(c['parked'].items()):
        px = _f(prices.get(pa))
        if px > 0 and px >= _f(pk['backAt']) and not fading(mom.get(pa)):
            c['legs'].append(_leg({**pk, 'price': px}, pk['usd'], now, pk.get('role') or 'runner')); c['feesUsd'] += fee
            del c['parked'][pa]
            ev(kind='rebuy', symbol=pk['symbol'], usd=round(pk['usd'], 4), why='back at its entry with momentum — bought back', to=[pk['symbol']])
    # 3) auto-rotate every rotateHours: the rotateCount weakest coins out, the best candidates in
    if now - c['lastRotateAt'] >= cfg['rotateHours'] * 3600 and not c.get('flooredAt'):
        ranked = sorted((l for l in c['legs'] if l.get('role') != 'anchor' and (t['sl'] or l.get('role') == 'pool')), key=lambda l: (_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] if l['entry'] else 1)
        swapped = 0
        for l in ranked[:cfg['rotateCount']]:
            nxt = best(l['role'])
            if not nxt:
                continue
            px = _f(prices.get(l['pairAddress'])) or l['entry']
            usd = l['units'] * px
            c['legs'][c['legs'].index(l)] = _leg(nxt, usd, now, l['role']); c['feesUsd'] += 2 * fee; swapped += 1
            ev(kind='rotate', symbol=l['symbol'], usd=round(usd, 4), why=f"weakest after {cfg['rotateHours']}h", to=[nxt.get('symbol')])
        c['lastRotateAt'] = now
        # one ROUND per rotation: log this round's move, start the next one from today's value
        v_now = value(c, prices)
        c['rounds'] = int(c.get('rounds') or 0) + 1
        c['lastRoundPct'] = round((v_now / (_f(c.get('roundStartUsd')) or _f(c['startUsd']) or 1) - 1) * 100, 2)
        c['roundStartUsd'] = round(v_now, 4); c['roundCrowned'] = False
    # 4) idle cash goes back to work when compounding
    if cfg['compound'] and c['cash'] > 0.01 and c['legs']:
        each = c['cash'] / len(c['legs'])
        for l in c['legs']:
            px = _f(prices.get(l['pairAddress'])) or l['entry']
            l['units'] += each / px; l['costUsd'] += each
        c['compoundedUsd'] += c['cash']; ev(kind='compound', usd=round(c['cash'], 4), why='idle cash back into the card', to=[l['symbol'] for l in c['legs']]); c['cash'] = 0.0
    # 5) 🛡 FLOOR: the card is never allowed to sit below −floorPct (default −20%, so −25% is never reached short of a gap):
    #    every pool / runner is sold into the anchor (or cash) at once; the card re-deals fresh the next day.
    v = value(c, prices); start = _f(c['startUsd']) or 1
    pct = (v / start - 1) * 100
    if pct <= -cfg['floorPct'] and not c.get('flooredAt'):
        anc = [l for l in c['legs'] if l.get('role') == 'anchor' and _f(prices.get(l['pairAddress'])) > 0]
        out = [l for l in c['legs'] if l.get('role') != 'anchor']
        usd = sum(l['units'] * (_f(prices.get(l['pairAddress'])) or l['entry']) for l in out)
        c['feesUsd'] += fee * len(out)
        if anc:
            for a in anc:
                apx = _f(prices.get(a['pairAddress'])); a['units'] += usd / len(anc) / apx; a['costUsd'] += usd / len(anc)
        else:
            c['cash'] += usd
        c['legs'] = anc or []
        c['flooredAt'] = now
        ev(kind='floor', usd=round(usd, 4), why=f"card {pct:.0f}% ≤ −{cfg['floorPct']:g}% floor — everything into the anchor", to=[a['symbol'] for a in anc] or ['cash'])
    c['lowPct'] = round(min(_f(c.get('lowPct')), pct), 2)
    # 6) the day record: every 24h the card's day move is logged — a good day is ≥ +10%
    if now - c['dayAt'] >= 86400:
        c['days'] = (c['days'] + [{'at': now, 'pct': round((v / (_f(c['dayStartUsd']) or 1) - 1) * 100, 2)}])[-30:]
        c['dayAt'], c['dayStartUsd'] = now, round(v, 4)
    c['feesUsd'] = round(c['feesUsd'], 4)
    c['events'] = c['events'][-60:]
    return c


def summary(card, prices):
    v = value(card, prices)
    start = _f(card.get('startUsd')) or 1
    legs = [{**{k: l[k] for k in ('mint', 'pairAddress', 'symbol', 'role', 'entry', 'units', 'costUsd')}, 'stars': l.get('stars') or 3,
             'firstEntry': l.get('firstEntry') or l['entry'], 'at': l.get('at'), 'now': _f(prices.get(l['pairAddress'])) or l['entry'],
             'pnlPct': round(((_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] - 1) * 100, 2) if l['entry'] else 0.0,
             'usd': round(l['units'] * (_f(prices.get(l['pairAddress'])) or l['entry']), 4)} for l in card['legs']]
    return {**{k: card[k] for k in ('id', 'tpl', 'label', 'at', 'lastRotateAt', 'compoundedUsd', 'takenUsd', 'feesUsd', 'startUsd')}, 'cash': round(card['cash'], 4),
            'flooredAt': card.get('flooredAt'), 'rounds': int(card.get('rounds') or 0), 'lastRoundPct': card.get('lastRoundPct'),
            'roundPct': round((v / (_f(card.get('roundStartUsd')) or start) - 1) * 100, 2), 'roundWins': int(card.get('roundWins') or 0),
            'valueUsd': v, 'pnlPct': round((v / start - 1) * 100, 2), 'legs': legs, 'events': card['events'][-12:][::-1],
            'tp': TEMPLATES[card['tpl']]['tp'], 'sl': TEMPLATES[card['tpl']]['sl'], 'tier': TEMPLATES[card['tpl']]['tier'], 'why': TEMPLATES[card['tpl']].get('why'),
            'parked': list((card.get('parked') or {}).values()),
            **record(card)}


def record(card):
    """Honest scoreboard: of the last 10 logged days, how many were up ≥ +10%; the worst the card has ever been."""
    days = (card.get('days') or [])[-10:]
    return {'days': days, 'goodDays': sum(1 for d in days if _f(d.get('pct')) >= HIT_PCT), 'loggedDays': len(days),
            'lowPct': _f(card.get('lowPct')), 'floored': bool(card.get('flooredAt')), 'runs': (card.get('runs') or [])[-5:]}


def replace_leg(card, pair, prices, pools, runners, anchors, cfg, now):
    """Cmd Ctr ⇄: swap ONE coin on a Prime card for the best 3★+ candidate of the same role not already on it (same $)."""
    c = {**card, 'legs': [dict(l) for l in card['legs']], 'events': list(card['events'])}
    l = next((x for x in c['legs'] if x['pairAddress'] == pair), None)
    if not l:
        raise ValueError('That coin is not on this card.')
    have = {x['mint'] for x in c['legs']}
    src = {'runner': runners, 'anchor': anchors}.get(l['role'], pools)
    nxt = next((x for x in rated(src, l['role']) if x['mint'] not in have and _f(x.get('price')) > 0), None)
    if not nxt:
        raise ValueError('No 3★+ replacement available right now.')
    usd = l['units'] * (_f(prices.get(pair)) or l['entry'])
    c['legs'][c['legs'].index(l)] = _leg(nxt, usd, now, l['role'])
    c['feesUsd'] = round(_f(c['feesUsd']) + 2 * cfg['paperFeeUsd'], 4)
    c['events'].append({'at': now, 'kind': 'rotate', 'symbol': l['symbol'], 'usd': round(usd, 4), 'why': 'replaced from Cmd Ctr', 'to': [nxt.get('symbol')]})
    return c


def crown_round(cards):
    """🏆 The finished round's best card (highest lastRoundPct, must be > 0) gets a round win. Mutates + returns the winner id."""
    done = [c for c in cards.values() if c.get('lastRoundPct') is not None and not c.get('roundCrowned')]
    if not done:
        return None
    best = max(done, key=lambda c: c['lastRoundPct'])
    for c in done:
        c['roundCrowned'] = True
    if best['lastRoundPct'] > 0:
        best['roundWins'] = int(best.get('roundWins') or 0) + 1
        return best['id']
    return None
