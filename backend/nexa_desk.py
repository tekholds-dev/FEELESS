"""🪟🐱 NEXA TRADES AS FEECAT (owner, 2026-10-22: "nexa can do 2-3 calls every 5 mins to trade AS feecat — only sending her MC, pressure,
simple shit for her to decide yay or nay"). Owner-only: the switch lives in HQ › Fee › NEXA's desk and it drives FeeCat herself (paper).

Every EVERY seconds, at most CALLS tiny questions to her CPU model — one coin each, one line of numbers, one word back:
  · a coin FeeCat HOLDS  → HOLD / SELL   (held coins first: protecting money beats finding more)
  · a coin FeeCat would BUY (her ranked scan + the agents' top coins) → YES / NO
FeeCat buys only on a YES that is still fresh (FRESH) and only after every guard of hers passes it (cat_model.buy_ok); a SELL is sold at the
live price; stops / trails / rug rules keep running underneath. Pure + tested; reputation_service does the calls, feecat_service the trades.
"""
import re

EVERY = 300.0      # one desk round per 5 min
CALLS = 3          # ≤ 3 questions a round (~10 s each on her i5 with a short prompt)
FRESH = 900.0      # a YES / SELL counts for 15 min
ASK_GAP = 900.0    # a coin she is NOT holding is asked again at most every 15 min
MAX_TOK = 14
KEEP = 60
ASK_BUY = ("You trade FeeCat's paper desk on Solana memecoins. One coin, its live numbers. Reply with ONE word, YES (buy it now) or NO, "
           "then at most 8 words why. Fresh pumps with sellers leading, tiny pools and top-heavy holders are NO.")
ASK_HOLD = ("You trade FeeCat's paper desk on Solana memecoins. A coin she HOLDS, its live numbers. Reply with ONE word, HOLD or SELL, "
            "then at most 8 words why. Sell when buyers left or the move is dying; hold a clean trend.")
WORDS = {'buy': ('YES', 'NO'), 'hold': ('HOLD', 'SELL')}


def _k(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return f"{v / 1e6:.1f}M" if abs(v) >= 1e6 else f"{v / 1e3:.0f}K" if abs(v) >= 1e3 else f"{v:.0f}"


def _pct(v):
    try:
        return f"{float(v):+.1f}%"
    except (TypeError, ValueError):
        return None


def line(c, held=None):
    """One coin as one line of numbers. `c` = {symbol, mcap, ageMin, d5, c1, buy (buyers' share %), liq, top10}; `held` = {pct, peak, mins}."""
    bits = [f"${str(c.get('symbol') or '?')[:12]}"]
    if held:
        bits.append(f"you {_pct(held.get('pct')) or '?'} (peak {_pct(held.get('peak')) or '?'}) held {int(held.get('mins') or 0)}m")
    for w, v in (('MC', _k(c.get('mcap'))), ('age', f"{int(c['ageMin'])}m" if c.get('ageMin') is not None else None), ('5m', _pct(c.get('d5'))),
                 ('1h', _pct(c.get('c1'))), ('buyers', f"{float(c['buy']):.0f}%" if c.get('buy') is not None else None),
                 ('pool', _k(c.get('liq'))), ('top10', f"{float(c['top10']):.0f}%" if c.get('top10') is not None else None)):
        if v is not None:
            bits.append(f"{w} {v}")
    return ' · '.join(bits)


def parse(text, kind):
    """Her answer → (word, why). word ∈ WORDS[kind] or None when she said neither."""
    t = re.sub(r'<[^>]+>', ' ', str(text or '')).strip()
    m = re.search(r'\b(' + '|'.join(WORDS[kind]) + r')\b', t, re.I)
    if not m:
        return None, ''
    why = ' '.join(t[m.end():].strip(' :.-—,').split())[:80]
    return m.group(1).upper(), why


def due(st, now):
    return now - float((st or {}).get('deskAt') or 0) >= EVERY


def pick(held, cands, calls, now, n=CALLS):
    """→ ≤ n jobs [{kind, pair, symbol, line}]: every held coin first (asked once per round), then candidates not asked in ASK_GAP,
    never one FeeCat already holds."""
    last = {}
    for c in calls or []:
        last[c.get('pair')] = max(last.get(c.get('pair'), 0.0), float(c.get('at') or 0))
    jobs, mine = [], {h.get('pair') for h in held or []}
    for h in held or []:
        if h.get('pair') and len(jobs) < n:
            jobs.append({'kind': 'hold', 'pair': h['pair'], 'mint': h.get('mint'), 'symbol': h.get('symbol'), 'line': line(h, h)})
    for c in cands or []:
        p = c.get('pair')
        if len(jobs) >= n:
            break
        if p and p not in mine and now - last.get(p, 0.0) >= ASK_GAP and all(j['pair'] != p for j in jobs):
            jobs.append({'kind': 'buy', 'pair': p, 'mint': c.get('mint'), 'symbol': c.get('symbol'), 'line': line(c)})
    return jobs


def note(calls, job, word, why, ms, now):
    return (list(calls or []) + [{'pair': job['pair'], 'mint': job.get('mint'), 'symbol': job.get('symbol'), 'kind': job['kind'], 'word': word, 'why': why, 'line': job['line'][:160],
                                  'ms': ms, 'at': round(now)}])[-KEEP:]


def merge(calls, now):
    """Her latest fresh word per coin → {favor: [pairs she said YES], exit: [pairs she said SELL], at: newest fresh call} (cat_model reads it)."""
    latest = {}
    for c in calls or []:
        if c.get('word') and now - float(c.get('at') or 0) <= FRESH:
            latest[c['pair']] = c
    fav = sorted(p for p, c in latest.items() if c['word'] == 'YES')
    out = sorted(p for p, c in latest.items() if c['word'] == 'SELL')
    return {'favor': fav, 'exit': out, 'at': max((float(c['at']) for c in latest.values()), default=0.0)}
