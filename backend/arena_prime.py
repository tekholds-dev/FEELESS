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

TEMPLATES = {   # pools / runners per card + the dial it runs
    'safe': {'label': '🛡 Prime Safe', 'pools': 3, 'runners': 1, 'tp': 30, 'sl': 15},
    'balanced': {'label': '⚖ Prime Balanced', 'pools': 3, 'runners': 2, 'tp': 50, 'sl': 25},
    'degen': {'label': '🚀 Prime Degen', 'pools': 2, 'runners': 3, 'tp': 100, 'sl': 40},
}
DEFAULT_CFG = {'on': True, 'sizeUsd': 100.0, 'rotateHours': 6, 'rotateCount': 2, 'compound': True, 'paperFeeUsd': 0.10}
CFG_RANGES = {'sizeUsd': (10, 10000), 'rotateHours': (1, 48), 'rotateCount': (1, 3), 'paperFeeUsd': (0, 5)}


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
    out['rotateHours'], out['rotateCount'] = int(out['rotateHours']), int(out['rotateCount'])
    for k in ('on', 'compound'):
        if k in (p or {}):
            out[k] = bool(p[k])
    return out


def _leg(c, usd, now, role):
    px = _f(c.get('price'))
    return {'mint': c['mint'], 'pairAddress': c['pairAddress'], 'symbol': c.get('symbol'), 'role': role, 'entry': px, 'units': usd / px if px > 0 else 0.0,
            'costUsd': round(usd, 6), 'at': now}


def deal(tid, pools, runners, cfg, now):
    """A fresh Prime card from the best candidates (already gated + ranked by the caller). Equal $ per coin."""
    t = TEMPLATES[tid]
    picks = [(c, 'pool') for c in pools[:t['pools']]] + [(c, 'runner') for c in runners[:t['runners']]]
    picks = [(c, r) for c, r in picks if _f(c.get('price')) > 0]
    if not picks:
        return None
    each = cfg['sizeUsd'] / len(picks)
    return {'id': f'prime-{tid}', 'tpl': tid, 'label': t['label'], 'at': now, 'lastRotateAt': now, 'legs': [_leg(c, each, now, r) for c, r in picks],
            'cash': 0.0, 'feesUsd': round(cfg['paperFeeUsd'] * len(picks), 4), 'compoundedUsd': 0.0, 'takenUsd': 0.0, 'events': [{'kind': 'deal', 'at': now, 'n': len(picks)}],
            'startUsd': cfg['sizeUsd']}


def value(card, prices):
    v = sum(l['units'] * (_f(prices.get(l['pairAddress'])) or l['entry']) for l in card['legs']) + card['cash']
    return round(v, 4)


def tick(card, prices, pools, runners, cfg, now):
    """One automation pass. Returns the updated card (mutated copy) — all actions logged as events with reasons."""
    t = TEMPLATES[card['tpl']]
    c = {**card, 'legs': [dict(l) for l in card['legs']], 'events': list(card['events'])}
    have = lambda: {l['mint'] for l in c['legs']}
    ev = lambda **e: c['events'].append({'at': now, **e})
    fee = cfg['paperFeeUsd']

    def best(role):
        src = runners if role == 'runner' else pools
        return next((x for x in src if x['mint'] not in have() and _f(x.get('price')) > 0), None)

    # 1) auto take-profit (sell just the gain) → compound into the other coins, or keep as cash
    for l in c['legs']:
        px = _f(prices.get(l['pairAddress']))
        if px <= 0 or l['entry'] <= 0:
            continue
        g = (px / l['entry'] - 1) * 100
        if g >= t['tp']:
            gain_units = l['units'] * (1 - l['entry'] / px)          # sell back down to the cost basis
            gain = gain_units * px
            l['units'] -= gain_units; l['entry'] = px; c['feesUsd'] += fee
            c['takenUsd'] += gain
            others = [o for o in c['legs'] if o is not l and _f(prices.get(o['pairAddress'])) > 0]
            if cfg['compound'] and others:
                each = gain / len(others)
                for o in others:
                    opx = _f(prices.get(o['pairAddress']))
                    o['units'] += each / opx; o['costUsd'] += each
                c['compoundedUsd'] += gain; c['feesUsd'] += fee * len(others)
                ev(kind='tp', symbol=l['symbol'], usd=round(gain, 4), why=f"+{g:.0f}% ≥ +{t['tp']}%", to=[o['symbol'] for o in others])
            else:
                c['cash'] += gain
                ev(kind='tp', symbol=l['symbol'], usd=round(gain, 4), why=f"+{g:.0f}% ≥ +{t['tp']}%", to=['cash'])
    # 2) auto stop-loss → replaced at once by the best gated candidate of the same role
    for i, l in enumerate(list(c['legs'])):
        px = _f(prices.get(l['pairAddress']))
        if px <= 0 or l['entry'] <= 0 or (px / l['entry'] - 1) * 100 > -t['sl']:
            continue
        out_usd = l['units'] * px
        nxt = best(l['role'])
        c['feesUsd'] += fee
        if nxt:
            c['legs'][c['legs'].index(l)] = _leg(nxt, out_usd, now, l['role']); c['feesUsd'] += fee
            ev(kind='sl', symbol=l['symbol'], usd=round(out_usd, 4), why=f"{(px / l['entry'] - 1) * 100:.0f}% ≤ −{t['sl']}%", to=[nxt.get('symbol')])
        else:
            c['legs'].remove(l); c['cash'] += out_usd
            ev(kind='sl', symbol=l['symbol'], usd=round(out_usd, 4), why=f"{(px / l['entry'] - 1) * 100:.0f}% ≤ −{t['sl']}%", to=['cash'])
    # 3) auto-rotate every rotateHours: the rotateCount weakest coins out, the best candidates in
    if now - c['lastRotateAt'] >= cfg['rotateHours'] * 3600:
        ranked = sorted(c['legs'], key=lambda l: (_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] if l['entry'] else 1)
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
    # 4) idle cash goes back to work when compounding
    if cfg['compound'] and c['cash'] > 0.01 and c['legs']:
        each = c['cash'] / len(c['legs'])
        for l in c['legs']:
            px = _f(prices.get(l['pairAddress'])) or l['entry']
            l['units'] += each / px; l['costUsd'] += each
        c['compoundedUsd'] += c['cash']; ev(kind='compound', usd=round(c['cash'], 4), why='idle cash back into the card', to=[l['symbol'] for l in c['legs']]); c['cash'] = 0.0
    c['feesUsd'] = round(c['feesUsd'], 4)
    c['events'] = c['events'][-60:]
    return c


def summary(card, prices):
    v = value(card, prices)
    start = _f(card.get('startUsd')) or 1
    legs = [{**{k: l[k] for k in ('mint', 'pairAddress', 'symbol', 'role', 'entry', 'units', 'costUsd')}, 'now': _f(prices.get(l['pairAddress'])) or l['entry'],
             'pnlPct': round(((_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] - 1) * 100, 2) if l['entry'] else 0.0,
             'usd': round(l['units'] * (_f(prices.get(l['pairAddress'])) or l['entry']), 4)} for l in card['legs']]
    return {**{k: card[k] for k in ('id', 'tpl', 'label', 'at', 'lastRotateAt', 'compoundedUsd', 'takenUsd', 'feesUsd', 'startUsd')}, 'cash': round(card['cash'], 4),
            'valueUsd': v, 'pnlPct': round((v / start - 1) * 100, 2), 'legs': legs, 'events': card['events'][-12:][::-1],
            'tp': TEMPLATES[card['tpl']]['tp'], 'sl': TEMPLATES[card['tpl']]['sl']}
