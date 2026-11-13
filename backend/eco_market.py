"""📊 PoEco rebuilt (owner 2026-11-13: scrap the books idea, build a proof that competes with the others).

PROOF OF ECONOMY: a sealed call on the real Solana economy. The agent reads live DexScreener pools,
states ONE plain rule, makes ONE measurable call, seals the exact numbers it saw under a hash, and a day
later the REAL numbers grade it — right or wrong is pure math, no model, no human mark, no money.
It is the only proof graded entirely by reality: the same baseline always gives the same hash.
"""
import hashlib
import json
import secrets
import time

DAY = 86400
RULE = 'Turnover momentum: the pool working its liquidity harder (24h volume ÷ liquidity) keeps the 24h volume lead.'


def _num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def rows_of(pairs):
    """Normalize raw DexScreener pair dicts → sorted rows, deepest first. Broken rows are dropped, never guessed."""
    rows = []
    for p in pairs or []:
        if not isinstance(p, dict) or not p.get('pairAddress'):
            continue
        liq = _num((p.get('liquidity') or {}).get('usd'))
        vol = _num((p.get('volume') or {}).get('h24'))
        if liq <= 0 or vol <= 0:
            continue
        base = (p.get('baseToken') or {}).get('symbol') or '?'
        quote = (p.get('quoteToken') or {}).get('symbol') or '?'
        rows.append({'pair': f'{base}/{quote}'[:24], 'addr': p['pairAddress'], 'priceUsd': _num(p.get('priceUsd')),
                     'vol24h': round(vol, 2), 'liqUsd': round(liq, 2), 'chg24h': _num((p.get('priceChange') or {}).get('h24'))})
    return sorted(rows, key=lambda r: -r['liqUsd'])


def seal(payload):
    """The same call always gives the same hash."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:32]


def make_call(rows, n, now=None, horizon=DAY):
    """One measurable call from the two deepest live pools. Raises ValueError when the market read is too thin."""
    now = now or time.time()
    if len(rows) < 2:
        raise ValueError('Fewer than two live pools came back. No call without a real read.')
    a, b = rows[0], rows[1]
    turn = lambda r: r['vol24h'] / r['liqUsd']   # noqa: E731
    pick = a if turn(a) >= turn(b) else b
    other = b if pick is a else a
    q = f"In {round(horizon / 3600)}h, {pick['pair']} posts more 24h volume than {other['pair']}."
    baseline = {'pick': pick, 'other': other}
    body = {'q': q, 'rule': RULE, 'baseline': baseline, 'at': round(now), 'due': round(now + horizon)}
    return {'id': f'poe{secrets.token_hex(5)}', 'n': n, 'kind': 'market', 'topic': q, 'q': q, 'rule': RULE,
            'baseline': baseline, 'hash': seal(body), 'at': round(now), 'due': round(now + horizon), 'status': 'open'}


def grade(f, rows, now=None):
    """Grades a due market call from fresh rows: right/wrong + the after-numbers, written on the folder. Pure math."""
    now = now or time.time()
    if f.get('kind') != 'market' or f.get('graded'):
        return f
    if now < _num(f.get('due')):
        raise ValueError('Not due yet. Reality grades it at the horn.')
    by = {r['addr']: r for r in rows}
    pick = by.get(f['baseline']['pick']['addr'])
    other = by.get(f['baseline']['other']['addr'])
    if not pick or not other:
        f['graded'] = 'wrong'
        f['after'] = {'note': 'A pool it called went dark before the horn. A dead pool is a wrong call.'}
    else:
        f['graded'] = 'right' if pick['vol24h'] > other['vol24h'] else 'wrong'
        f['after'] = {'pick': pick, 'other': other, 'marginUsd': round(pick['vol24h'] - other['vol24h'], 2)}
    f['status'] = 'closed'
    f['gradedAt'] = round(now)
    return f


def receipt(f):
    """What leaves the folder: the call, both number sets and the hash. Enough for anyone to recheck the math."""
    return {'proof': 'PoEco', 'n': f.get('n'), 'q': f.get('q'), 'rule': f.get('rule'), 'baseline': f.get('baseline'),
            'after': f.get('after'), 'graded': f.get('graded'), 'hash': f.get('hash'), 'at': f.get('at'), 'due': f.get('due')}
