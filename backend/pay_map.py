"""📊 WHAT PAYS (pure, read-only): the real card's closed pieces from CONFIRMED fills only, matched buy → sell first-in-first-out per coin
(price result, fees apart). Each piece has a hold time, an opener (the owner's hand pick or the engine), an exit kind (a trim of a winner
vs a whole coin leaving) and an hour. Grouped, they show WHICH behaviour makes money and which bleeds, and `advice` turns the numbers
into plain sentences that cite them. It never changes a card: the owner decides what to switch.
2026-10-07 record (943 pieces): held under 15 min −$15.2 (25–31% won) · held 30+ min +$5.5 (60% won) · trims of winners +$17.6 (74% won)
· whole coins leaving −$23.8 (24% won)."""
from collections import defaultdict

HOLD_BUCKETS = (('<5m', 0, 5), ('5-15m', 5, 15), ('15-30m', 15, 30), ('30-60m', 30, 60), ('1-3h', 60, 180), ('3h+', 180, 1e9))
TRIM_WORDS = ('trim', 'lock', 'skim', 'peak', 'bank', 'recycle', 'profit')


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def exit_kind(why):
    w = str(why or '').lower()
    if 'recover' in w:
        return 'recovery'
    if any(k in w for k in TRIM_WORDS):
        return 'trim'
    return 'whole'


def pieces(ledger, card, since=0.0):
    """→ closed pieces [{mint, sym, usd, cost, ret, hold (min), you (bool), kind, at}] from filled buys / sells of `card`."""
    rows = sorted({(r.get('sig') or r.get('id'), r.get('side')): r for r in ledger or [] if r.get('card') == card and r.get('status') == 'filled'
                   and r.get('side') in ('buy', 'sell') and _f(r.get('px')) > 0 and _f(r.get('units')) > 0}.values(), key=lambda r: _f(r.get('at')))
    lots, out = defaultdict(list), []
    for r in rows:
        m = r.get('mint') or r.get('symbol')
        if r['side'] == 'buy':
            lots[m].append([_f(r['units']), _f(r['px']), _f(r['at']), str(r.get('picked')) == 'True'])
            continue
        left = _f(r['units'])
        while left > 1e-9 and lots[m]:
            lot = lots[m][0]; take = min(left, lot[0])
            if _f(r['at']) >= since:
                out.append({'mint': m, 'sym': r.get('symbol'), 'usd': take * (_f(r['px']) - lot[1]), 'cost': take * lot[1], 'ret': _f(r['px']) / lot[1] - 1,
                            'hold': (_f(r['at']) - lot[2]) / 60.0, 'bat': lot[2], 'you': lot[3], 'kind': exit_kind(r.get('why')), 'at': _f(r['at'])})
            lot[0] -= take; left -= take
            if lot[0] <= 1e-9:
                lots[m].pop(0)
    return out


def _agg(ps):
    n = len(ps)
    if not n:
        return {'n': 0, 'wonPct': None, 'usd': 0.0, 'cost': 0.0, 'pct': None, 'avgRet': None}
    usd, cost = sum(p['usd'] for p in ps), sum(p['cost'] for p in ps)
    return {'n': n, 'wonPct': round(100 * sum(1 for p in ps if p['usd'] > 0) / n), 'usd': round(usd, 2), 'cost': round(cost, 2),
            'pct': round(100 * usd / cost, 1) if cost > 0 else None, 'avgRet': round(100 * sum(p['ret'] for p in ps) / n, 1)}


def bucket_of(minutes):
    return next(l for l, a, b in HOLD_BUCKETS if a <= minutes < b)


def pay_map(ledger, card, now, hours=None):
    since = now - hours * 3600 if hours else 0.0
    ps = pieces(ledger, card, since)
    by_hold = {l: _agg([p for p in ps if bucket_of(p['hold']) == l]) for l, _, _ in HOLD_BUCKETS}
    by_kind = {k: _agg([p for p in ps if p['kind'] == k]) for k in ('trim', 'whole', 'recovery')}
    by_opener = {'you': _agg([p for p in ps if p['you']]), 'engine': _agg([p for p in ps if not p['you']])}
    blocks = {}
    for p in ps:
        import time as _t
        h = (_t.gmtime(p['at']).tm_hour // 4) * 4
        blocks.setdefault(h, []).append(p)
    by_hour = {f'{h:02d}-{h + 4:02d}': _agg(v) for h, v in sorted(blocks.items())}
    short = _agg([p for p in ps if p['hold'] < 15]); long_ = _agg([p for p in ps if p['hold'] >= 30])
    you_short = _agg([p for p in ps if p['you'] and p['hold'] < 15])
    adv = []
    if short['n'] >= 40 and short['usd'] < 0 and long_['n'] >= 20 and long_['usd'] > 0:
        adv.append({'key': 'hold', 'text': f"Coins sold inside 15 min: {short['n']} pieces, {short['wonPct']}% won, ${short['usd']:+.2f}. Held 30+ min: {long_['n']} pieces, {long_['wonPct']}% won, ${long_['usd']:+.2f}. "
                    "The money is made by letting a coin run — set Round min hold to 20–30 min (Edit Fuse › Rounds); the 5-minute clock can stay."})
    if by_kind['trim']['n'] >= 20 and by_kind['trim']['usd'] > 0 and by_kind['whole']['n'] >= 20 and by_kind['whole']['usd'] < 0:
        adv.append({'key': 'exits', 'text': f"Taking profit on winners made ${by_kind['trim']['usd']:+.2f} ({by_kind['trim']['wonPct']}% won, {by_kind['trim']['n']} pieces); whole coins leaving lost ${by_kind['whole']['usd']:+.2f} "
                    f"({by_kind['whole']['wonPct']}% won). Keep the lock bank and skims on; every extra whole-coin exit is where the card bleeds."})
    y, e = by_opener['you'], by_opener['engine']
    if y['n'] >= 40 and e['n'] >= 40 and y['pct'] is not None and e['pct'] is not None and abs(y['pct'] - e['pct']) >= 1.0:
        who = 'Your hand picks' if y['pct'] > e['pct'] else 'The engine'
        adv.append({'key': 'opener', 'text': f"{who} did better: you {y['pct']:+.1f}% on ${y['cost']:.0f} ({y['wonPct']}% won), engine {e['pct']:+.1f}% on ${e['cost']:.0f} ({e['wonPct']}% won)."
                    + (f" Your picks sold inside 15 min: {you_short['n']} pieces, ${you_short['usd']:+.2f} — the winners came from the ones you held." if you_short['n'] >= 20 and you_short['usd'] < 0 else '')})
    good = [(k, v) for k, v in by_hour.items() if v['n'] >= 40]
    if len(good) >= 2:
        best, worst = max(good, key=lambda kv: kv[1]['pct'] if kv[1]['pct'] is not None else -999), min(good, key=lambda kv: kv[1]['pct'] if kv[1]['pct'] is not None else 999)
        if best[1]['pct'] is not None and worst[1]['pct'] is not None and best[1]['pct'] - worst[1]['pct'] >= 3:
            adv.append({'key': 'hour', 'text': f"Best 4-hour window (UTC): {best[0]} at {best[1]['pct']:+.1f}% ({best[1]['n']} pieces). Worst: {worst[0]} at {worst[1]['pct']:+.1f}% ({worst[1]['n']} pieces)."})
    return {'pieces': len(ps), 'netUsd': round(sum(p['usd'] for p in ps), 2), 'byHold': by_hold, 'byKind': by_kind, 'byOpener': by_opener, 'byHour': by_hour, 'advice': adv,
            'note': 'Price result of confirmed fills, matched first-in-first-out; fees apart. A record of what happened, never a promise.'}
