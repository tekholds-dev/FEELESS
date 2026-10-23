"""📉 PAPER PERPS — the Perps building's own order desk (docs/DECISIONS.md #1: FEELESS never places, routes or holds a perps order or margin;
the real order is a one-tap handoff to a regulated venue). Pure + tested; the service keeps one paper book per wallet and the live board.

A paper book starts with START paper dollars. Open a LONG / SHORT on a live market (its real mark price) with a margin and a leverage up to
the market's own max: size = margin × leverage at the entry mark. Every read marks it to the live price, accrues the market's real funding
(positive = longs pay shorts) and LIQUIDATES it when the move eats the margin (minus MAINT maintenance), exactly like a venue would.
Close = realized P&L back into the paper cash. Paper only — nothing here is money, an order or advice."""
import time
import uuid

START = 10_000.0       # paper dollars a new book gets (reset any time)
MAX_OPEN = 6
MIN_MARGIN = 10.0
MAINT = 0.005          # maintenance margin: liquidation lands this much before the margin is fully gone
KEEP_CLOSED = 40
YEAR = 365 * 86400


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def blank(now=None):
    return {'cash': START, 'open': [], 'closed': [], 'realized': 0.0, 'since': now or time.time()}


def liq_price(entry, side, lev):
    """The mark at which the margin (less maintenance) is gone."""
    k = max(0.0, 1.0 / lev - MAINT)
    return entry * (1 - k) if side == 'long' else entry * (1 + k)


def open_pos(book, coin, side, margin, lev, mark, max_lev, now):
    """→ the new position (the book is changed in place) or raises ValueError with the reason."""
    side = str(side).lower()
    margin, lev, mark = _f(margin), int(_f(lev)), _f(mark)
    if side not in ('long', 'short'):
        raise ValueError('Long or short.')
    if mark <= 0:
        raise ValueError('That market has no live price right now.')
    if not 1 <= lev <= int(max_lev or 1):
        raise ValueError(f'{coin} goes up to {int(max_lev or 1)}× here.')
    if margin < MIN_MARGIN:
        raise ValueError(f'The smallest margin is ${MIN_MARGIN:.0f}.')
    if margin > book['cash'] + 1e-9:
        raise ValueError(f"Only ${book['cash']:,.2f} paper cash is free.")
    if len(book['open']) >= MAX_OPEN:
        raise ValueError(f'{MAX_OPEN} paper positions at once — close one first.')
    p = {'id': uuid.uuid4().hex[:10], 'coin': coin, 'side': side, 'margin': round(margin, 2), 'lev': lev, 'entry': mark,
         'size': round(margin * lev / mark, 10), 'liq': liq_price(mark, side, lev), 'at': now, 'fundAt': now, 'fund': 0.0}
    book['cash'] = round(book['cash'] - margin, 6)
    book['open'].append(p)
    return p


def mark(p, px, fund_apr, now):
    """Mark one open position: accrue funding since its last mark (longs pay a positive rate, shorts receive it), then its live P&L,
    equity and distance to liquidation. → a view dict (the position keeps its funding)."""
    px = _f(px)
    notional = p['size'] * px if px > 0 else p['size'] * p['entry']
    dt = max(0.0, now - _f(p.get('fundAt'), now))
    pay = notional * _f(fund_apr) / 100 * dt / YEAR
    p['fund'] = round(_f(p.get('fund')) + (-pay if p['side'] == 'long' else pay), 6)
    p['fundAt'] = now
    move = (px - p['entry']) * p['size'] * (1 if p['side'] == 'long' else -1) if px > 0 else 0.0
    pnl = move + p['fund']
    eq = p['margin'] + pnl
    gone = px > 0 and ((p['side'] == 'long' and px <= p['liq']) or (p['side'] == 'short' and px >= p['liq']) or eq <= 0)
    return {**p, 'mark': px, 'notional': round(notional, 2), 'pnl': round(pnl, 2), 'pnlPct': round(100 * pnl / p['margin'], 1), 'equity': round(eq, 2),
            'toLiqPct': round(abs(px - p['liq']) / px * 100, 2) if px > 0 else None, 'liquidated': bool(gone)}


def close_pos(book, pid, px, fund_apr, now, why='closed'):
    """Close at the live mark (or at the liquidation price): the margin ± P&L back to cash (never below 0). → the closed record."""
    p = next((x for x in book['open'] if x['id'] == pid), None)
    if not p:
        raise ValueError('That paper position is gone already.')
    v = mark(p, px, fund_apr, now)
    out_px = p['liq'] if why == 'liquidated' else v['mark']
    move = (out_px - p['entry']) * p['size'] * (1 if p['side'] == 'long' else -1)
    pnl = -p['margin'] if why == 'liquidated' else max(-p['margin'], move + p['fund'])   # a liquidation takes the whole margin, as on a venue
    book['cash'] = round(book['cash'] + p['margin'] + pnl, 6)
    book['realized'] = round(book['realized'] + pnl, 6)
    book['open'] = [x for x in book['open'] if x['id'] != pid]
    rec = {k: p[k] for k in ('id', 'coin', 'side', 'margin', 'lev', 'entry', 'at')}
    rec.update(exit=out_px, pnl=round(pnl, 2), pnlPct=round(100 * pnl / p['margin'], 1), heldMin=round((now - p['at']) / 60, 1), why=why, closedAt=now)
    book['closed'] = ([rec] + book['closed'])[:KEEP_CLOSED]
    return rec


def view(book, board, now):
    """The book at live prices: liquidations settle on the read. `board` = {coin: {mark, fundApr}} (the Perps desk's live rows)."""
    liq = []
    for p in list(book['open']):
        b = board.get(p['coin']) or {}
        v = mark(p, b.get('mark'), b.get('fundApr'), now)
        if v['liquidated']:
            liq.append(close_pos(book, p['id'], b.get('mark'), b.get('fundApr'), now, 'liquidated'))
    rows = [mark(p, (board.get(p['coin']) or {}).get('mark'), (board.get(p['coin']) or {}).get('fundApr'), now) for p in book['open']]
    margin = sum(p['margin'] for p in book['open'])
    upnl = sum(r['pnl'] for r in rows)
    won = [c for c in book['closed'] if c['pnl'] > 0]
    return {'cash': round(book['cash'], 2), 'equity': round(book['cash'] + margin + upnl, 2), 'start': START, 'open': rows, 'closed': book['closed'][:12],
            'realized': round(book['realized'], 2), 'upnl': round(upnl, 2), 'liquidated': liq, 'winPct': round(100 * len(won) / len(book['closed'])) if book['closed'] else None,
            'trades': len(book['closed'])}
