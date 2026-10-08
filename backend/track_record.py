"""📜 TRACK RECORD (pure, read-only): proof of what a wallet really did, from records FEELESS itself verified — never self-reported.
• trades: a wallet's verified FEELESS swaps matched buy → sell first-in-first-out per coin (price at the pool, fees apart — the money rule:
  cost is what REACHED the pool). Lots still open are returned as `open` with their entry, the caller prices them live.
• calls: chat calls with the price at the call, the last and the peak price since.
Each entry carries what is needed to check it (coin, entry, exit, time, tx). A losing entry is shown as a losing entry."""
from collections import defaultdict


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _px(r):
    """Price per token at the pool: the fill price, else pool $ ÷ tokens."""
    p = _f(r.get('fillPrice'))
    if p > 0:
        return p
    t = _f(r.get('tokens'))
    return _f(r.get('poolUsd')) / t if t > 0 and _f(r.get('poolUsd')) > 0 else _f(r.get('price'))


def trade_receipts(rows, symbols=None):
    """→ (closed [receipt], open [lot]) from one wallet's trade rows. `symbols` = {mint: ticker}."""
    sym = symbols or {}
    lots, closed = defaultdict(list), []
    for r in sorted((x for x in rows or [] if x.get('token') and _f(x.get('tokens')) > 0 and _px(x) > 0), key=lambda x: _f(x.get('ts'))):
        m = r['token']
        if r.get('side') == 'buy':
            lots[m].append([_f(r['tokens']), _px(r), _f(r.get('ts')), r.get('tx')])
            continue
        left = _f(r['tokens'])
        while left > 1e-12 and lots[m]:
            lot = lots[m][0]; take = min(left, lot[0]); sp = _px(r)
            closed.append({'kind': 'trade', 'mint': m, 'symbol': sym.get(m) or m[:4].upper(), 'entryPx': lot[1], 'exitPx': sp, 'ret': round(sp / lot[1] - 1, 4),
                           'usd': round(take * (sp - lot[1]), 4), 'costUsd': round(take * lot[1], 4), 'holdMin': round((_f(r.get('ts')) - lot[2]) / 60.0, 1),
                           'at': _f(r.get('ts')), 'buyTx': lot[3], 'tx': r.get('tx')})
            lot[0] -= take; left -= take
            if lot[0] <= 1e-12:
                lots[m].pop(0)
    open_ = [{'kind': 'open', 'mint': m, 'symbol': sym.get(m) or m[:4].upper(), 'entryPx': l[1], 'tokens': l[0], 'costUsd': round(l[0] * l[1], 4), 'at': l[2], 'buyTx': l[3]}
             for m, ls in lots.items() for l in ls if l[0] * l[1] >= 0.01]
    return closed, open_


def call_receipts(calls, address, aliases=()):
    """→ the wallet's calls as entries: result now and the peak multiple since the call."""
    mine = {address, *aliases}
    out = []
    for c in (calls.values() if isinstance(calls, dict) else calls or []):
        if c.get('callerAddress') not in mine or _f(c.get('priceAtCall')) <= 0:
            continue
        e, last, peak = _f(c['priceAtCall']), _f(c.get('lastPrice')), _f(c.get('peakPrice'))
        out.append({'kind': 'call', 'mint': c.get('mint'), 'symbol': c.get('symbol') or (c.get('mint') or '')[:4].upper(), 'entryPx': e, 'exitPx': last or None,
                    'ret': round(last / e - 1, 4) if last > 0 else None, 'peakX': round(peak / e, 2) if peak > 0 else None, 'at': _f(c.get('at')), 'room': c.get('room')})
    return out


def summary(closed, calls):
    n = len(closed); won = sum(1 for r in closed if r['usd'] > 0)
    rets = sorted(r['ret'] for r in closed)
    cn = [c for c in calls if c.get('ret') is not None]
    return {'trades': n, 'wonPct': round(100 * won / n) if n else None, 'medianPct': round(100 * rets[n // 2], 1) if n else None,
            'netUsd': round(sum(r['usd'] for r in closed), 2), 'best': max(closed, key=lambda r: r['ret'])['symbol'] if n else None,
            'calls': len(calls), 'callHit2xPct': round(100 * sum(1 for c in cn if (c.get('peakX') or 0) >= 2) / len(cn)) if cn else None}
