"""🧭 GENERAL AI CAT — YOUR ORDERS (owner, 2026-10-23: "TWO KINDS OF AI CAT … (b) GENERAL — 1-2 all-round models that do anything the user
asks with the AI wallet they fund"). You write an order in plain words; the cat turns it into ONE proposal and your own wallet signs it
(docs/DECISIONS.md #2, option A — FEELESS never holds a key or pooled funds). Today an order is a Solana swap: buy a coin with SOL, or sell
part / all of a coin the cat holds. LP / lend / DCA orders come later, each through its own verified builder.

Every buy is a NEW BUY DOOR, so it ships with the guards (memory: new-buy-doors-need-guards): a real pool (≥ $5K), not born minutes ago
(≥ 15 min), not already vertical (≤ +300% in 1h), and the rug / holder check every FeeCat buy runs (feecat_service._safety). Size is capped
by the cat's max position (and, real, by the budget you set). Pure + tested; feecat_service does the I/O (search, safety, propose).
"""
import json
import re

POOL_MIN_USD = 5_000.0
AGE_MIN_MIN = 15.0
RAN_MAX_H1 = 300.0
SOL_MAX = 5.0                 # an order never asks for more than this in one go, whatever the words say
FRACTIONS = {'all': 1.0, 'everything': 1.0, 'half': 0.5, 'a third': 1 / 3, 'a quarter': 0.25, 'quarter': 0.25}
SYMBOL = r'\$?([A-Za-z][A-Za-z0-9._-]{0,15})'
MINT = r'([1-9A-HJ-NP-Za-km-z]{32,44})'

ORDER_SYS = ('You turn a trader\'s order into JSON for a Solana trading cat. Reply with ONLY one JSON object: '
             '{"side":"buy|sell","coin":"<SYMBOL or mint address>","sol":<SOL to spend on a buy, or null>,"fraction":<0-1 of the holding to sell, or null>}. '
             'If the order is not a buy or a sell of one coin, reply {"side":"none"}. Never invent a coin the order does not name.')


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_order(text):
    """Deterministic first (no model call): "buy 0.05 SOL of $BONK" · "ape 0.1 sol into JUP" · "sell half of $WIF" · "sell all BONK" ·
    "sell 25% of POPCAT" · a pasted mint works as the coin. → {side, coin, sol?, fraction?} or None (then the brain is asked)."""
    t = ' '.join(str(text or '').split())
    if not t:
        return None
    m = re.search(rf'\b(?:buy|ape|grab|get|long)\b\s+(\d+(?:\.\d+)?)\s*(?:sol|◎)\s+(?:(?:worth of|into|of|in|on)\s+)?(?:{MINT}|{SYMBOL})', t, re.I)
    if m:
        sol = _num(m.group(1))
        coin = m.group(2) or m.group(3)
        return {'side': 'buy', 'coin': coin, 'sol': sol} if sol and coin else None
    m = re.search(rf'\b(?:buy|ape|grab|get)\b\s+(?:{MINT}|{SYMBOL})\s+(?:for|with)\s+(\d+(?:\.\d+)?)\s*(?:sol|◎)', t, re.I)
    if m:
        return {'side': 'buy', 'coin': m.group(1) or m.group(2), 'sol': _num(m.group(3))}
    m = re.search(rf'\b(?:sell|dump|exit|bank|close|trim)\b\s+(?:(all|everything|half|a third|a quarter|quarter|\d{{1,3}}\s*%)\s+(?:of\s+)?)?(?:my\s+)?(?:{MINT}|{SYMBOL})', t, re.I)
    if m:
        q = (m.group(1) or '').lower().strip()
        coin = m.group(2) or m.group(3)
        if coin and coin.lower() in ('all', 'everything', 'half', 'my', 'it', 'the', 'some'):
            return None
        frac = FRACTIONS.get(q) if q in FRACTIONS else (_num(q.rstrip('%').strip()) / 100 if q.endswith('%') else None)
        if re.search(r'\btrim\b', t, re.I) and frac is None:
            frac = 0.5
        return {'side': 'sell', 'coin': coin, 'fraction': max(0.05, min(1.0, frac if frac is not None else 1.0))}
    return None


def order_from_json(text):
    """The brain's JSON → the same order shape, or None (it said none / gave nothing usable)."""
    s = str(text or '')
    i, j = s.find('{'), s.rfind('}')
    if i < 0 or j <= i:
        return None
    try:
        d = json.loads(s[i:j + 1])
    except ValueError:
        return None
    side = str(d.get('side') or '').lower()
    coin = str(d.get('coin') or '').strip().lstrip('$')[:44]
    if side not in ('buy', 'sell') or not coin or not re.fullmatch(r'[A-Za-z0-9._-]{1,44}', coin):
        return None
    if side == 'buy':
        sol = _num(d.get('sol'))
        return {'side': 'buy', 'coin': coin, 'sol': sol} if sol and sol > 0 else None
    fr = _num(d.get('fraction'))
    return {'side': 'sell', 'coin': coin, 'fraction': max(0.05, min(1.0, fr if fr else 1.0))}


def best_pair(pairs, coin):
    """DexScreener pairs → the Solana pool for THIS coin with the deepest liquidity (symbol or mint must match the base token)."""
    c = str(coin or '').lstrip('$').lower()
    rows = [p for p in pairs or [] if p.get('chainId') == 'solana' and (str((p.get('baseToken') or {}).get('symbol') or '').lower() == c
                                                                       or str((p.get('baseToken') or {}).get('address') or '').lower() == c)]
    return max(rows, key=lambda p: _num((p.get('liquidity') or {}).get('usd')) or 0.0) if rows else None


def buy_guards(p, now_ms):
    """The new-buy-door guards on the pool the order would buy → (ok, why). The rug / holder check runs after this (needs the network)."""
    if not p:
        return False, '🔎 no Solana pool found for that coin'
    liq = _num((p.get('liquidity') or {}).get('usd')) or 0.0
    if liq < POOL_MIN_USD:
        return False, f'💧 pool ${liq:,.0f} — under the ${POOL_MIN_USD:,.0f} floor (you could not get out)'
    born = _num(p.get('pairCreatedAt'))
    if born and (now_ms - born) / 60000 < AGE_MIN_MIN:
        return False, f'🐣 {((now_ms - born) / 60000):.0f} min old — under {AGE_MIN_MIN:.0f} min loses (trench law)'
    h1 = _num((p.get('priceChange') or {}).get('h1'))
    if h1 is not None and h1 > RAN_MAX_H1:
        return False, f'🚀 +{h1:.0f}% in 1h — already ran, that is the top-buyer seat'
    return True, ''


def size_of(order, max_pos_sol, budget_sol=None):
    """A buy's SOL, capped: the cat's max position, the real budget left, SOL_MAX. → (sol, capped_note)."""
    want = _num(order.get('sol')) or 0.0
    caps = [x for x in (max_pos_sol, budget_sol, SOL_MAX) if x is not None and x > 0]
    sol = round(min([want] + caps), 4)
    return sol, ('' if sol >= want else f' (capped from {want:g} SOL)')


def held_of(positions, coin):
    """The position this sell order means (symbol or mint), or None."""
    c = str(coin or '').lstrip('$').lower()
    return next((p for p in positions or [] if str(p.get('symbol') or '').lower() == c or str(p.get('mint') or '').lower() == c), None)


def note(cat, text, order, state, why, now, sym=None, pid=None):
    """One line in the cat's order log (newest last, 20 kept): what you said, what it understood, what happened."""
    row = {'at': now, 'text': ' '.join(str(text or '').split())[:200], 'order': order, 'state': state, 'why': why[:200], 'symbol': sym, 'pid': pid}
    cat['orders'] = (list(cat.get('orders') or []) + [row])[-20:]
    return row
