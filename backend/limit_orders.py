"""🎯 LIMIT ORDERS on the real card (owner, 2026-10-15: "do limit orders"). Pure + tested.

A limit is the owner's standing order that FEELESS watches: it never signs or sends anything by itself — when the live chart price crosses
the line it hands the order to the card's NORMAL paths (a seat pick / a pick swap / ✂ sell to cash), so every keeper check still runs.
  · BUY  {side:'buy',  mint, pair, symbol, px, target: '__seat__' | <pair of the coin it replaces>, cand} — fires when price ≤ px
  · SELL {side:'sell', pair, mint, symbol, px, pct}                                                   — fires when price ≥ px (take)
                                                                                                         or ≤ px with stop=True
Each fires ONCE, then it is gone; ≤ MAX per card; a limit older than its `hours` (default 24) expires."""
import time
import uuid

MAX = 12
HOURS = (1, 6, 24, 72)
PCTS = (25, 50, 100)


from fnum import plain as _f


def make(side, px, now=None, hours=24, **k):
    """→ a clean limit dict, or raises ValueError with words for the owner."""
    if side not in ('buy', 'sell'):
        raise ValueError('A limit is a buy or a sell.')
    px = _f(px)
    if px <= 0:
        raise ValueError('Set a price above 0.')
    h = int(hours) if int(_f(hours)) in HOURS else 24
    out = {'id': uuid.uuid4().hex[:10], 'side': side, 'px': px, 'at': time.time() if now is None else now, 'hours': h,
           'mint': k.get('mint'), 'pair': k.get('pair'), 'symbol': k.get('symbol')}
    if side == 'buy':
        if not k.get('cand') or not k.get('target'):
            raise ValueError('A buy limit needs the coin and the seat it goes into.')
        out.update(target=k['target'], cand={**k['cand'], 'ack': True})
    else:
        if not k.get('pair'):
            raise ValueError('A sell limit needs a coin on the card.')
        pct = int(_f(k.get('pct')) or 100)
        out.update(pct=pct if pct in PCTS else 100, stop=bool(k.get('stop')))
    return out


def add(card, lim):
    ls = [x for x in card.get('limits') or [] if not (x['side'] == lim['side'] and x.get('mint') == lim.get('mint') and x.get('pair') == lim.get('pair'))]
    if len(ls) >= MAX:
        raise ValueError(f'Up to {MAX} limits per card — cancel one first.')
    return {**card, 'limits': ls + [lim]}


def cancel(card, lid):
    return {**card, 'limits': [x for x in card.get('limits') or [] if x.get('id') != lid]}


def due(card, px_by_mint, now):
    """→ (hit, keep, expired): limits whose line the live price crossed, the rest, and the timed-out ones."""
    hit, keep, gone = [], [], []
    for x in card.get('limits') or []:
        if now - _f(x.get('at')) > _f(x.get('hours') or 24) * 3600:
            gone.append(x); continue
        p = _f((px_by_mint or {}).get(x.get('mint')))
        if p <= 0:
            keep.append(x); continue
        if x['side'] == 'buy':
            ok = p <= x['px']
        else:
            ok = p <= x['px'] if x.get('stop') else p >= x['px']
        (hit if ok else keep).append({**x, 'firedPx': p} if ok else x)
    return hit, keep, gone


def word(x):
    """One line for the card: what this limit does."""
    sym = f"${x.get('symbol') or '?'}"
    if x['side'] == 'buy':
        where = 'an empty seat' if x.get('target') == '__seat__' else 'a seat'
        return f"🎯 BUY {sym} into {where} at ≤ {x['px']:.6g}"
    return f"{'🛑' if x.get('stop') else '💰'} SELL {x.get('pct', 100)}% {sym} at {'≤' if x.get('stop') else '≥'} {x['px']:.6g}"
