"""⚔ Engine playground battles (HQ only — separate from the public Arena battles). Pure, tested.

The playground's best scenario cards fight each other on short rounds (default 5 min) with a paper $ size that fills like a
real wallet would (constant-product impact, `arena_prime.buy_px/sell_usd`). Mid-round every runner coin is watched:
  • hits the card's take-profit → sold and swapped for the best gated runner not on the card (`tp`)
  • hits the card's stop → swapped (`sl`)
  • goes DEAD (no 5m trades / volume for `deadMins`) → swapped (`dead`)
At the bell the bigger % since the bell wins (`runners.settle_battle`). Winners keep their coins (their config proved
itself); losers are re-bred from this round's picks with the same scenario. Records per scenario feed "ready for Arena".
Nothing here touches real money.
"""
import arena_prime as ap
import card_dna as _dna
import runners as rn

_f = rn._f
DEFAULT_CFG = {'on': True, 'roundMins': 5, 'cards': 4, 'sizeUsd': 100.0, 'swapOnTp': True, 'swapOnSl': True, 'swapDead': True, 'deadMins': 10}
ROUND_OPTIONS = (5, 15, 30, 60)
CARD_OPTIONS = (2, 4, 6)


def clean_cfg(c):
    c = c if isinstance(c, dict) else {}
    out = dict(DEFAULT_CFG)
    for k in ('on', 'swapOnTp', 'swapOnSl', 'swapDead'):
        if k in c:
            out[k] = bool(c[k])
    if _f(c.get('roundMins')) in ROUND_OPTIONS:
        out['roundMins'] = int(_f(c['roundMins']))
    if _f(c.get('cards')) in CARD_OPTIONS:
        out['cards'] = int(_f(c['cards']))
    if c.get('sizeUsd') is not None:
        out['sizeUsd'] = round(max(10.0, min(10000.0, _f(c['sizeUsd']))), 2)
    if c.get('deadMins') is not None:
        out['deadMins'] = int(max(3, min(60, _f(c['deadMins']))))
    return out


def _buy(pa, usd, prices, liqs):
    px = _f(prices.get(pa))
    if px <= 0 or usd <= 0:
        return None
    return usd / ap.buy_px(px, usd, liqs.get(pa))


def deal(sc, prices, liqs, now, size):
    """A scenario card → a paper battle card with real-fill units for every coin that has a live price."""
    legs = [l for l in sc.get('legs') or [] if _f(prices.get(l['pairAddress'])) > 0]
    tot = sum(_f(l.get('weight')) for l in legs) or 1
    out = []
    for l in legs:
        usd = size * _f(l.get('weight')) / tot
        units = _buy(l['pairAddress'], usd, prices, liqs)
        if units:
            out.append({'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'mint': l.get('mint'), 'role': l.get('role') or 'runner',
                        'entry': _f(prices[l['pairAddress']]), 'units': units, 'usd': round(usd, 4), 'at': now, 'liq': _f(liqs.get(l['pairAddress']))})
    return {'id': sc['id'], 'name': sc.get('vName') or sc.get('name') or sc.get('label'), 'dial': sc.get('dial'), 'tp': _f(sc.get('tp')), 'sl': _f(sc.get('sl')),
            'legs': out, 'cash': 0.0, 'startUsd': size, 'roundUsd': size, 'swaps': [], 'at': now}


def value(card, prices, liqs):
    return sum(ap.sell_usd(l['units'], _f(prices.get(l['pairAddress'])) or l['entry'], liqs.get(l['pairAddress'])) for l in card['legs']) + _f(card.get('cash'))


def round_pct(card, prices, liqs):
    base = _f(card.get('roundUsd')) or _f(card.get('startUsd')) or 1
    return round((value(card, prices, liqs) / base - 1) * 100, 2)


def tick(card, prices, liqs, quiet, candidates, cfg, now, dna=None):
    """Mid-round: swap runner coins that hit TP / stop or went dead for the best gated runner not on the card."""
    c = {**card, 'legs': [dict(l) for l in card['legs']], 'swaps': list(card.get('swaps') or [])}
    d = _dna.clean(dna or {})   # 🧬 this card's DNA plays out: payout % to cash on a TP, compound off = keep the take, hold = no stop swaps
    on_card = {l['pairAddress'] for l in c['legs']}
    pool = [r for r in candidates or [] if r.get('pairAddress') and r['pairAddress'] not in on_card and _f(prices.get(r['pairAddress']) or r.get('price')) > 0]
    for l in list(c['legs']):
        if l.get('role') == 'anchor':
            continue
        px = _f(prices.get(l['pairAddress']))
        if px <= 0:
            continue
        move = (px / l['entry'] - 1) * 100 if l['entry'] else 0
        if quiet.get(l['pairAddress']):
            l.setdefault('quietSince', now)
        else:
            l.pop('quietSince', None)
        lq, lq0 = _f(liqs.get(l['pairAddress'])), _f(l.get('liq'))
        why = ('rug' if lq0 > 0 and 0 < lq <= lq0 * ap.RUG_LIQ else   # 🚨 rug shield: liquidity pulled → swap out at once
               'tp' if cfg['swapOnTp'] and c['tp'] and move >= c['tp'] else
               'sl' if cfg['swapOnSl'] and c['sl'] and move <= -c['sl'] and d['stop'] != 'hold' else
               'dead' if cfg['swapDead'] and l.get('quietSince') and now - l['quietSince'] >= cfg['deadMins'] * 60 else None)
        if not why or not pool:
            continue
        nxt = pool.pop(0)
        usd = ap.sell_usd(l['units'], px, liqs.get(l['pairAddress']))
        if why == 'tp':   # profit split on the take: the payout share is banked (to the owner), the rest rides into the next coin
            gain = max(0.0, usd - _f(l.get('usd')))
            out_, back_ = _dna.split_profit(gain, d)
            keep = out_ + (gain - out_ if d['compound'] == 'off' else 0.0)
            c['cash'] = round(_f(c.get('cash')) + keep, 6); usd -= keep
        npx = _f(prices.get(nxt['pairAddress']) or nxt.get('price'))
        nliq = liqs.get(nxt['pairAddress']) or nxt.get('liq')
        units = usd / ap.buy_px(npx, usd, nliq)
        c['legs'][c['legs'].index(l)] = {'pairAddress': nxt['pairAddress'], 'symbol': nxt.get('symbol'), 'mint': nxt.get('mint'), 'role': 'runner',
                                         'entry': npx, 'units': units, 'usd': round(usd, 4), 'at': now, 'liq': _f(nliq)}
        c['swaps'] = (c['swaps'] + [{'at': now, 'why': why, 'out': l.get('symbol'), 'in': nxt.get('symbol'), 'move': round(move, 1)}])[-12:]
    return c


def pair_up(ids):
    """1 v 2, 3 v 4 … in the order given (best scenario first) — the odd one out sits."""
    return [{'a': ids[i], 'b': ids[i + 1]} for i in range(0, len(ids) - 1, 2)]


def settle(pairs, pcts, record, now):
    """Bell: bigger % since the bell wins; W/L/D per scenario id. Returns (results, record, losers)."""
    rec = {k: dict(v) for k, v in (record or {}).items()}
    results, losers = [], set()
    for p in pairs or []:
        a, b = p['a'], p['b']
        if a not in pcts or b not in pcts:
            continue
        w = rn.settle_battle(0, pcts[a], 0, pcts[b])
        for side, key in (('a', a), ('b', b)):
            r = rec.setdefault(key, {'w': 0, 'l': 0, 'd': 0})
            r['d' if w == 'draw' else 'w' if w == side else 'l'] += 1
        if w != 'draw':
            losers.add(b if w == 'a' else a)
        results.append({'at': now, 'a': a, 'b': b, 'aPct': pcts[a], 'bPct': pcts[b], 'winner': {'a': a, 'b': b}.get(w), 'draw': w == 'draw'})
    return results, rec, losers


def champion(record, cards, min_w=2):
    """🏆 The engine's top battle winner (≥ min_w wins, more wins than losses, best W−L then wins) — the ONLY engine card that
    goes to the public Arena on its own (HQ can still 🎨 pick others). Returns the card id or None."""
    ok = [(k, r) for k, r in (record or {}).items() if k in (cards or {}) and int(r.get('w') or 0) >= min_w and int(r.get('w') or 0) > int(r.get('l') or 0)]
    return max(ok, key=lambda kr: (kr[1]['w'] - kr[1]['l'], kr[1]['w']))[0] if ok else None


def ready_rows(record, names, min_w=3):
    """Playground battle records for the engine's Ready list: ≥ min_w wins and at least 2 wins per loss."""
    out = []
    for k, r in (record or {}).items():
        w, l = int(r.get('w') or 0), int(r.get('l') or 0)
        ok = w >= min_w and w >= 2 * l
        out.append((ok, {'kind': 'battle card', 'name': (names or {}).get(k) or k, 'id': k,
                         'why': f"{w}–{l} in playground battles" + ('' if ok else f" · needs {max(0, min_w - w)} more wins at 2:1")}))
    return out


PHASE_ANCHOR = {'anchor': 0.7, 'mixed': 0.5, 'degen': 0.15}   # share of the card held in the anchor (majors) per phase


def cycle_rebalance(card, dna, last_pct, prices, liqs):
    """🔄 The card's DNA cycle plays out at every bell: the next phase (arena_prime.next_phase — classic / adaptive / safe / press)
    sets how much sits in the anchor vs the runners; everything is re-entered at live prices with true fills (impact both ways).
    No anchor or cycle 'off' → unchanged."""
    d = _dna.clean(dna or {})
    phase = ap.next_phase(d['cycle'], card.get('rounds'), last_pct)
    anchors = [l for l in card['legs'] if l.get('role') == 'anchor']
    runners_ = [l for l in card['legs'] if l.get('role') != 'anchor']
    if not phase or not anchors or not runners_:
        return {**card, 'rounds': int(card.get('rounds') or 0) + 1}
    px = lambda l: _f(prices.get(l['pairAddress'])) or l['entry']
    total = sum(ap.sell_usd(l['units'], px(l), liqs.get(l['pairAddress'])) for l in card['legs']) + _f(card.get('cash'))
    share = PHASE_ANCHOR[phase]
    legs = []
    for grp, part in ((anchors, share), (runners_, 1 - share)):
        for l in grp:
            usd = total * part / len(grp)
            p_ = px(l)
            legs.append({**l, 'entry': p_, 'units': usd / ap.buy_px(p_, usd, liqs.get(l['pairAddress'])) if p_ > 0 else 0, 'usd': round(usd, 4)})
    return {**card, 'legs': legs, 'cash': 0.0, 'phase': phase, 'rounds': int(card.get('rounds') or 0) + 1}
