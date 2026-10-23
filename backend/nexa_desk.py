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
# 🧪 the desk's own trench laws (docs/TRENCH_THEORY.md, measured on 4,000 coins + the real card's ledger), one breath each — her call
# confirms or denies a law instead of reasoning from zero (owner, 2026-10-22: "next-gen one-line desk prompts in her trench style")
ASK_BUY = ("You run FeeCat's paper trench desk on Solana memecoins. Trench laws: under 15m old loses; still on the curve is the worst bucket; "
           "cap under 30K AND graduated is the only setup that paid; pool under 5K can't be exited; sellers leading = no; top10 over 35% = no; "
           "a move must beat the 3% round trip. One coin, live numbers. Reply ONE word, YES or NO, then at most 8 words: the law it passes or breaks.")
ASK_HOLD = ("You run a coin FeeCat HOLDS on her paper trench desk. Trench laws: exits under 15m lose; 1-3h holds paid best; let +50 / -30 work; "
            "sell when buyers left, the pool thins or the move died. Reply ONE word, HOLD or SELL, then at most 8 words: the law.")
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


def stage_word(st):
    """The coin's curve stage in one word, the way trench_theory reads it: 'graduated' · 'on curve' · None (unknown)."""
    s = str(st or '').lower()
    if any(w in s for w in ('graduat', 'migrat', 'amm', 'raydium', 'pumpswap')):
        return 'graduated'
    return 'on curve' if ('curve' in s or 'bond' in s) else None


def line(c, held=None):
    """One coin as one line of numbers. `c` = {symbol, mcap, ageMin, stage, d5, c1, buy (buyers' share %), liq, top10}; `held` = {pct, peak, mins}."""
    bits = [f"${str(c.get('symbol') or '?')[:12]}"]
    if held:
        bits.append(f"you {_pct(held.get('pct')) or '?'} (peak {_pct(held.get('peak')) or '?'}) held {int(held.get('mins') or 0)}m")
    if c.get('stage') is not None and stage_word(c.get('stage')):
        bits.append(stage_word(c.get('stage')))   # 🧪 CURVE / PROVEN laws need it
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
