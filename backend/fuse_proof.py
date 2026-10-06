"""🧾 FUSE PROOF — what the real-money cards actually did, readable by anyone. Pure: no I/O, no clock.

Four reads built only from records that already exist (the Fuse wallet's chain-confirmed ledger + the cards' own events):
  feed    — the newest confirmed swaps of every real card, each with the ENGINE'S reason and its transaction
  record  — one real card's verified result: put in → now, closed pieces won / lost, profit takes vs full exits
  setups  — the front door: named setups side by side, each with ITS OWN record and where that record comes from
  duels   — a real card against the best other card for 24h, on % result only (points, never money)
Nothing here promises a result; a losing record is shown as a losing record."""

FEED_WINDOW = 24 * 3600
MATCH_SEC = 150          # a card event explains a ledger row of the same coin this close in time
DUEL_SEC = 24 * 3600
DUEL_DRAW = 0.5          # closer than half a point = a draw
TRIM, EXIT = 'trimmed to the card', 'not on the card any more'


def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _filled(rows, card=None):
    return [r for r in rows or [] if r.get('side') in ('buy', 'sell') and r.get('sig') and r.get('status') == 'filled' and (card is None or r.get('card') == card)]


def feed(cards, ledger, now, limit=24):
    """Newest first: [{at, card, label, side, symbol, usd, pct, why, sig}] for REAL cards over the last 24h. `pct` = a sell's realized
    result on the money that piece cost (None for buys). `why` = the engine's own words from the card event nearest that swap,
    else the keeper's order reason."""
    out = []
    real = {c.get('tpl'): c for c in cards or [] if c.get('real')}
    for r in _filled(ledger):
        c = real.get(r.get('card'))
        if not c or now - _f(r.get('at')) > FEED_WINDOW:
            continue
        # a SELL is explained by the event about that coin; a BUY by the event that brought it IN (`to`) — said as "in for $OLD: …"
        mine = (lambda e: e.get('symbol') == r.get('symbol')) if r['side'] == 'sell' else (lambda e: r.get('symbol') in (e.get('to') or []) or (e.get('symbol') == r.get('symbol') and e.get('kind') in ('seat', 'balance', 'scout', 'promote')))
        ev = min((e for e in c.get('events') or [] if e.get('why') and mine(e) and abs(_f(e.get('at')) - _f(r.get('at'))) <= MATCH_SEC),
                 key=lambda e: abs(_f(e.get('at')) - _f(r.get('at'))), default=None)
        if ev and r['side'] == 'buy' and ev.get('symbol') and ev.get('symbol') != r.get('symbol'):
            ev = {**ev, 'why': f"in for ${ev['symbol']}: {ev['why']}"}
        cost = _f(r.get('costUsd'))
        out.append({'at': _f(r.get('at')), 'card': r.get('card'), 'label': c.get('label') or r.get('card'), 'side': r['side'], 'symbol': r.get('symbol'), 'mint': r.get('mint'),
                    'pair': r.get('pair'), 'usd': round(_f(r.get('usd')), 2),
                    'pct': round(_f(r.get('realizedPnlUsd')) / cost * 100, 1) if r['side'] == 'sell' and cost > 0 else None,
                    'why': str((ev or {}).get('why') or r.get('why') or '')[:180], 'sig': r['sig']})
    out.sort(key=lambda x: -x['at'])
    return out[:limit]


def record(card, ledger, now):
    """One real card's verified record from its confirmed swaps → {putIn, nowUsd, pnlUsd, pct, swaps, days, closed, wonPct, takes, exits,
    best}. Closed pieces = sells with a known cost; `takes` = profit takes of a coin that stayed, `exits` = coins that left whole."""
    tpl = (card or {}).get('tpl')
    rows = _filled(ledger, tpl)
    sells = [r for r in rows if r['side'] == 'sell' and _f(r.get('costUsd')) > 0]
    part = lambda xs: {'n': len(xs), 'usd': round(sum(_f(x.get('realizedPnlUsd')) for x in xs), 2),
                       'wonPct': round(sum(1 for x in xs if _f(x.get('realizedPnlUsd')) > 0) / len(xs) * 100) if xs else None}
    math = (card or {}).get('math') or {}
    put, val = _f(math.get('putIn')), _f(math.get('nowUsd'))
    best = max(sells, key=lambda r: _f(r.get('realizedPnlUsd')) / _f(r['costUsd']), default=None)
    first = min((_f(r.get('at')) for r in rows), default=0.0)
    return {'tpl': tpl, 'label': (card or {}).get('label'), 'putIn': round(put, 2), 'nowUsd': round(val, 2), 'pnlUsd': round(_f(math.get('pnlUsd')), 2),
            'pct': round(_f(math.get('pnlUsd')) / put * 100, 1) if put > 0 else None, 'feesUsd': round(_f(math.get('feesUsd')), 2),
            'swaps': len(rows), 'days': round((now - first) / 86400, 1) if first else 0.0,
            'closed': len(sells), 'wonPct': part(sells)['wonPct'], 'takes': part([r for r in sells if r.get('why') == TRIM]),
            'exits': part([r for r in sells if r.get('why') != TRIM]),
            'best': {'symbol': best.get('symbol'), 'pct': round(_f(best.get('realizedPnlUsd')) / _f(best['costUsd']) * 100)} if best else None}


def why_bought(row, tag=''):
    """The line under a seat: what the coin looked like the moment the ENGINE took it → {tag, chg1h, vol1h, ageH, buyShare, liq}."""
    g = lambda k: None if (row or {}).get(k) is None else round(_f(row.get(k)), 1)
    lv = (row or {}).get('liquidity')
    liq = _f((row or {}).get('liquidityUsd') or (row or {}).get('liq') or (lv.get('usd') if isinstance(lv, dict) else lv))
    return {'tag': tag or '', 'chg1h': g('chg1h'), 'vol1h': g('vol1h'), 'ageH': g('ageH'), 'buyShare': g('buyShare'), 'liq': round(liq) if liq else None}


def setups(strategies, real_records, live_cfg=None):
    """The front door → [{key, name, why, source, proven, n, medPct, upPct, worstPct, …}]. Replay setups carry their walk-forward
    record (`source: 'replay'`); every real card is a row with its ledger record (`source: 'real'`). Best first: a proven replay
    setup, then the rest by typical result — a real card sits where its real result puts it."""
    out = []
    for s in strategies or []:
        out.append({'key': s.get('key'), 'name': s.get('name'), 'why': s.get('why'), 'source': 'replay', 'proven': bool(s.get('profitable')),
                    'n': s.get('windows') or s.get('n'), 'medPct': s.get('medPct'), 'upPct': s.get('upPct'), 'worstPct': s.get('worstPct'), 'hours': s.get('hours'), 'cfg': s.get('cfg')})
    for r in real_records or []:
        out.append({'key': f"real:{r.get('tpl')}", 'name': f"💵 {r.get('label')}", 'why': 'a real-money card, every swap on-chain', 'source': 'real', 'proven': (r.get('pct') or 0) > 0 and (r.get('closed') or 0) >= 20,
                    'n': r.get('closed'), 'medPct': r.get('pct'), 'upPct': r.get('wonPct'), 'worstPct': None, 'days': r.get('days'), 'record': r, 'cfg': (live_cfg or {}).get(r.get('tpl'))})
    out.sort(key=lambda x: (not x['proven'], -(_f(x.get('medPct')))))
    return out


# ⚔ REAL DUELS: a real-money card against the best other card, 24h, on % result. Points and a record only — nothing is staked.
def duel_step(store, values, labels, real_keys, ranked, now, pick=None):
    """Settle duels that are due and keep ONE live duel per real card. → the new store {live, log, rec}.
    values {key: $ value incl. paid out} · ranked = other cards best first · pick {real_key: challenger_key} = the owner's choice."""
    st = {'live': [dict(d) for d in (store or {}).get('live') or []], 'log': list((store or {}).get('log') or []), 'rec': {k: dict(v) for k, v in ((store or {}).get('rec') or {}).items()}}
    keep = []
    for d in st['live']:
        va, vb = _f(values.get(d['a'])), _f(values.get(d['b']))
        gone = va <= 0 or vb <= 0
        if now - _f(d['at']) < DUEL_SEC and not gone and (pick or {}).get(d['a'], d['b']) == d['b']:
            keep.append(d)
            continue
        if gone or now - _f(d['at']) < DUEL_SEC:      # a card closed, or the owner picked another challenger: called off, no result
            continue
        pa, pb = (va / _f(d['aStart']) - 1) * 100, (vb / _f(d['bStart']) - 1) * 100
        win = None if abs(pa - pb) < DUEL_DRAW else (d['a'] if pa > pb else d['b'])
        for k, other in ((d['a'], d['b']), (d['b'], d['a'])):
            r = st['rec'].setdefault(k, {'w': 0, 'l': 0, 'd': 0})
            r['d' if win is None else 'w' if win == k else 'l'] += 1
        st['log'] = (st['log'] + [{**d, 'endAt': now, 'aPct': round(pa, 2), 'bPct': round(pb, 2), 'winner': win}])[-40:]
    st['live'] = keep
    busy = {d['a'] for d in keep}
    for a in real_keys or []:
        if a in busy or _f(values.get(a)) <= 0:
            continue
        b = (pick or {}).get(a) or next((k for k in ranked or [] if k != a and _f(values.get(k)) > 0), None)
        if not b or b == a or _f(values.get(b)) <= 0:
            continue
        st['live'].append({'id': f"{a}:{b}:{int(now)}", 'a': a, 'b': b, 'aLabel': (labels or {}).get(a) or a, 'bLabel': (labels or {}).get(b) or b,
                           'aStart': round(_f(values[a]), 6), 'bStart': round(_f(values[b]), 6), 'at': now})
    return st


def duel_view(store, values, now):
    """What the screen shows: live duels with both sides' % since the start + time left, the last results, every card's record."""
    live = []
    for d in (store or {}).get('live') or []:
        pa = (_f(values.get(d['a'])) / _f(d['aStart']) - 1) * 100 if _f(d.get('aStart')) > 0 and _f(values.get(d['a'])) > 0 else None
        pb = (_f(values.get(d['b'])) / _f(d['bStart']) - 1) * 100 if _f(d.get('bStart')) > 0 and _f(values.get(d['b'])) > 0 else None
        live.append({**d, 'aPct': None if pa is None else round(pa, 2), 'bPct': None if pb is None else round(pb, 2), 'endsAt': _f(d['at']) + DUEL_SEC,
                     'leader': None if pa is None or pb is None or abs(pa - pb) < DUEL_DRAW else (d['a'] if pa > pb else d['b'])})
    return {'live': live, 'log': list(reversed(((store or {}).get('log') or [])[-6:])), 'rec': (store or {}).get('rec') or {}, 'hours': DUEL_SEC / 3600}
