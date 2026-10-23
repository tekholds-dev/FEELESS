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
HELD_EVERY = 120.0  # ⏱ while FeeCat HOLDS a coin: a held-only check every 2 min (owner, 2026-10-23: "quick questions to her faster — hold · skim · new SL · new TP")
SL_RANGE, TP_RANGE = (5.0, 40.0), (10.0, 300.0)   # her stop / take, in % from FeeCat's average entry (the rug stops stay underneath)
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
            "sell when buyers left, the pool thins or the move died; bank half into a fast spike. Reply ONE word — HOLD, SELL or SKIM (bank half) — "
            "or move a line: SL 15 (stop at -15%) / TP 60 (take at +60%). Then at most 8 words: the law.")
WORDS = {'buy': ('YES', 'NO'), 'hold': ('HOLD', 'SELL', 'SKIM')}


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


def lines_of(text):
    """'SL 15' / 'stop -12' / 'TP 60' / 'take +80' in her answer → {'sl': 15.0, 'tp': 60.0} clamped to SL_RANGE / TP_RANGE ({} = none)."""
    t, out = str(text or ''), {}
    for k, pat, (lo, hi) in (('sl', r'\b(?:SL|stop)\s*[:=]?\s*-?(\d{1,3}(?:\.\d)?)\s*%?', SL_RANGE), ('tp', r'\b(?:TP|take)\s*[:=]?\s*\+?(\d{1,3}(?:\.\d)?)\s*%?', TP_RANGE)):
        m = re.search(pat, t, re.I)
        if m:
            out[k] = round(max(lo, min(hi, float(m.group(1)))), 1)
    return out


def parse(text, kind):
    """Her answer → (word, why). word ∈ WORDS[kind] or None when she said neither. A held answer that only moves a line ("SL 15") is a HOLD."""
    t = re.sub(r'<[^>]+>', ' ', str(text or '')).strip()
    m = re.search(r'\b(' + '|'.join(WORDS[kind]) + r')\b', t, re.I)
    if not m:
        ln = re.search(r'\b(?:SL|TP)\s*[:=]?\s*[-+]?\d', t, re.I) if kind == 'hold' else None
        if not ln:
            return None, ''
        return 'HOLD', ' '.join(t[ln.start():].strip(' :.-—,').split())[:80]
    why = ' '.join(t[m.end():].strip(' :.-—,').split())[:80]
    return m.group(1).upper(), why


def due(st, now):
    return now - float((st or {}).get('deskAt') or 0) >= EVERY


def round_kind(st, now, holding):
    """→ 'full' (her 5-min round: held coins + buy questions) · 'held' (only the coins FeeCat holds, every HELD_EVERY) · None (not yet)."""
    if due(st, now):
        return 'full'
    if holding and now - max(float((st or {}).get('deskAt') or 0), float((st or {}).get('heldAt') or 0)) >= HELD_EVERY:
        return 'held'
    return None


def pick(held, cands, calls, now, n=CALLS, held_only=False):
    """→ ≤ n jobs [{kind, pair, symbol, line}]: every held coin first (asked once per round), then candidates not asked in ASK_GAP,
    never one FeeCat already holds. `held_only` = the 2-min check of a live trade (no buy questions)."""
    last = {}
    for c in calls or []:
        last[c.get('pair')] = max(last.get(c.get('pair'), 0.0), float(c.get('at') or 0))
    jobs, mine = [], {h.get('pair') for h in held or []}
    for h in held or []:
        if h.get('pair') and len(jobs) < n:
            jobs.append({'kind': 'hold', 'pair': h['pair'], 'mint': h.get('mint'), 'symbol': h.get('symbol'), 'line': line(h, h), 'mc': h.get('mcap')})
    if held_only:
        return jobs
    for c in cands or []:
        p = c.get('pair')
        if len(jobs) >= n:
            break
        if p and p not in mine and now - last.get(p, 0.0) >= ASK_GAP and all(j['pair'] != p for j in jobs):
            jobs.append({'kind': 'buy', 'pair': p, 'mint': c.get('mint'), 'symbol': c.get('symbol'), 'line': line(c), 'mc': c.get('mcap')})
    return jobs


def note(calls, job, word, why, ms, now, lines=None):
    return (list(calls or []) + [{'pair': job['pair'], 'mint': job.get('mint'), 'symbol': job.get('symbol'), 'kind': job['kind'], 'word': word, 'why': why, 'line': job['line'][:160],
                                  'ms': ms, 'at': round(now), **({'lines': lines} if lines and job['kind'] == 'hold' else {}), **({'mc': round(float(job['mc']))} if job.get('mc') else {})}])[-KEEP:]


TALK_SEC, TALK_N = 3 * 3600.0, 24


def talk(calls, now, sec=TALK_SEC, n=TALK_N):
    """💬 Her words as chart bubbles (P0-QUICK #4): every call that got a word and knows the coin's market cap when she said it, newest TALK_N
    of the last 3 h → [{pair, word, why, at, mc}]. Public as '🔮 FeeCat AI' (feecat_service scrubs every name)."""
    out = []
    for c in calls or []:
        mc = float(c.get('mc') or 0) or line_mc(c.get('line'))   # calls written before 'mc' carry it in their own line ("MC 28K")
        if c.get('word') and c.get('pair') and mc > 0 and now - float(c.get('at') or 0) <= sec:
            out.append({**{k: c.get(k) for k in ('pair', 'word', 'why', 'at')}, 'mc': round(mc)})
    return out[-n:]


def line_mc(text):
    """'$AAA · MC 28K · age 40m' → 28000.0 (our own line format, `_k`); 0.0 when it has none."""
    m = re.search(r'\bMC (\d+(?:\.\d+)?)([KM]?)\b', str(text or ''))
    return float(m.group(1)) * {'K': 1e3, 'M': 1e6, '': 1}[m.group(2)] if m else 0.0


def merge(calls, now):
    """Her latest fresh word per coin → {favor: [pairs she said YES], exit: [pairs she said SELL], at: newest fresh call} (cat_model reads it)."""
    latest = {}
    for c in calls or []:
        if c.get('word') and now - float(c.get('at') or 0) <= FRESH:
            latest[c['pair']] = c
    fav = sorted(p for p, c in latest.items() if c['word'] == 'YES')
    out = sorted(p for p, c in latest.items() if c['word'] == 'SELL')
    skim = {p: c['at'] for p, c in latest.items() if c['word'] == 'SKIM'}   # pair → the call's time (FeeCat skims ONCE per call)
    lines = {}
    for c in calls or []:   # her newest stop / take per coin (a later line call overwrites an older one)
        if c.get('lines') and now - float(c.get('at') or 0) <= FRESH:
            lines[c['pair']] = {**lines.get(c['pair'], {}), **c['lines']}
    return {'favor': fav, 'exit': out, 'skim': skim, 'lines': lines, 'at': max((float(c['at']) for c in latest.values()), default=0.0)}
