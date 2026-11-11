"""🐝 THE HIVE (owner 2026-10-31: "a FEELESS twist on Crawl — they browse forever until turned off and compound, better than Crawl's earning").

Crawl's crawlers read the crypto web for its model and earn by staking + a scratch-card lottery — nothing checks whether a read was any good.
The Hive is PROOF OF INSIGHT: an agent with the Hive on keeps reading the trenches on its own, one coin at a time, at the least usage (FEELESS's
own data through the free reader, ONE small model call per coin) and files a CELL — its call (BUY / WATCH / AVOID) and why, at the price it read.
An hour later the Hive grades every cell against what the coin really did: right calls earn HONEY, wrong ones lose it. Honey adds up per EPOCH
(one UTC day); the epoch board ranks agents by honey, and Fee's brain reads the graded cells before she buys. Pure functions here; the service
runs the loop (feecat_service._hive_*), never a trade, never a key.
"""
import re
import time
from fnum import plain as _num

EPOCH_S = 86400          # one UTC day
GRADE_AFTER_S = 3600     # a cell is judged one hour after it was filed
FRESH_S = 6 * 3600       # a coin gets a new cell from the same agent at most every 6 h
EVERY_MIN_S = 120        # the fastest an agent may file (least usage: the owner picks 2 min … 60 min)
EVERY_MAX_S = 3600
CELLS_MAX = 800          # kept on disk (newest)
CALLS = ('BUY', 'WATCH', 'AVOID')

HIVE_SYS = ('You are {name}, a FEELESS Hive scout. Read the coin below (FEELESS live numbers + its 5m chart) and file ONE cell. '
            'Answer ONLY JSON: {{"call": "BUY|WATCH|AVOID", "why": "<= 18 words, the numbers you read"}}. '
            'BUY = you expect it higher in the next hour; AVOID = lower or a rug risk; WATCH = no edge yet. Never invent a number.')


def epoch_of(t):
    return int(float(t) // EPOCH_S)


def epoch_left(t):
    return int(EPOCH_S - float(t) % EPOCH_S)


def every_s(v):
    try:
        return max(EVERY_MIN_S, min(EVERY_MAX_S, int(v)))
    except (TypeError, ValueError):
        return 300


def pick(pairs, cells, cat_id, now):
    """The next coin for this agent: the first trench pair it has no fresh cell on (deepest pools come first from the feed)."""
    recent = {c['pair'] for c in cells if c.get('cat') == cat_id and now - float(c.get('at') or 0) < FRESH_S}
    for p in pairs or []:
        pa = p.get('pairAddress')
        price = _num((p or {}).get('priceUsd'))
        if pa and pa not in recent and price > 0:
            b = p.get('baseToken') or {}
            return {'pair': pa, 'mint': b.get('address'), 'sym': str(b.get('symbol') or '?')[:16], 'price': price}
    return None


def parse_cell(text):
    """The model's answer → {call, why}; prose still counts when it names a call, anything else is WATCH (no edge claimed)."""
    t = str(text or '')
    m = re.search(r'"call"\s*:\s*"(BUY|WATCH|AVOID)"', t, re.I)
    call = (m.group(1) if m else next((c for c in CALLS if re.search(rf'\b{c}\b', t, re.I)), 'WATCH')).upper()
    w = re.search(r'"why"\s*:\s*"([^"]{1,300})"', t)
    why = (w.group(1) if w else re.sub(r'\s+', ' ', re.sub(r'[{}"]', '', t))).strip()[:160]
    return {'call': call, 'why': why or 'no reason given'}


def honey(call, move_pct):
    """Proof of insight: what a call earns once the coin moved `move_pct` % in the hour after it.
    BUY +2 on ≥ +20 %, +1 on ≥ +5 %, −1 on ≤ −10 %, −2 on ≤ −25 % · AVOID mirrors it · WATCH +1 when it stayed inside ±10 %, −1 on a ±25 % move it missed."""
    m = float(move_pct)
    if call == 'BUY':
        return 2 if m >= 20 else 1 if m >= 5 else -2 if m <= -25 else -1 if m <= -10 else 0
    if call == 'AVOID':
        return 2 if m <= -20 else 1 if m <= -5 else -2 if m >= 25 else -1 if m >= 10 else 0
    return 1 if abs(m) < 10 else -1 if abs(m) >= 25 else 0


def due(cells, now):
    """Cells an hour old and not graded yet."""
    return [c for c in cells if c.get('honey') is None and now - float(c.get('at') or 0) >= GRADE_AFTER_S]


def grade(cell, price_now, now):
    """Grade one cell in place with the price an hour on. → the honey it earned (None when no price could be read)."""
    p0 = _num(cell.get('price')); p1 = _num(price_now)
    if p0 <= 0 or p1 <= 0:
        if now - float(cell.get('at') or 0) > 6 * 3600:   # never readable again (a dead pool): settles as no edge
            cell.update(move=None, honey=0, gradedAt=now)
            return 0
        return None
    move = round((p1 / p0 - 1) * 100, 2)
    cell.update(move=move, honey=honey(cell['call'], move), gradedAt=now, priceAfter=p1)
    return cell['honey']


def board(cells, epoch, names=None):
    """The epoch board: per agent — honey, cells, graded, right (honey > 0) — best first."""
    rows = {}
    for c in cells:
        if epoch_of(c.get('at') or 0) != epoch:
            continue
        r = rows.setdefault(c['cat'], {'cat': c['cat'], 'name': (names or {}).get(c['cat']) or c.get('name') or 'agent', 'honey': 0, 'cells': 0, 'graded': 0, 'right': 0})
        r['cells'] += 1
        if c.get('honey') is not None:
            r['graded'] += 1; r['honey'] += int(c['honey']); r['right'] += 1 if c['honey'] > 0 else 0
    return sorted(rows.values(), key=lambda r: (-r['honey'], -r['right'], -r['cells']))


def for_coin(cells, key, now, limit=3):
    """What the Hive knows about one coin — by its pair or its $SYMBOL (newest first, last 24 h). Fee's brain reads this before she buys."""
    k = str(key or '').lstrip('$').lower()
    rows = [c for c in cells if k and (str(c.get('pair') or '').lower() == k or str(c.get('sym') or '').lower() == k) and now - float(c.get('at') or 0) < EPOCH_S]
    return sorted(rows, key=lambda c: -float(c.get('at') or 0))[:limit]


def brief(cells):
    """One line for a brain's case: 'HIVE: BUY by Happy (+1 honey, +8.2%) · AVOID by Scout (pending)'."""
    if not cells:
        return ''
    parts = [f"{c['call']} by {c.get('name') or 'an agent'} ({'pending' if c.get('honey') is None else f'{c['honey']:+d} honey, {c.get('move'):+.1f}%' if c.get('move') is not None else 'settled'})" for c in cells]
    return 'HIVE (other agents\' graded calls on this coin, last 24 h): ' + ' · '.join(parts)


def public(cell):
    """What anyone may see of a cell (no costs, no model routes)."""
    return {k: cell.get(k) for k in ('id', 'cat', 'name', 'sym', 'pair', 'call', 'why', 'price', 'at', 'honey', 'move')}



def now():
    return time.time()
