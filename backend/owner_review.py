"""👤 OWNER COIN REVIEW (owner, 2026-10-12: "one compact intake box — a Solana mint / CA, or a Pump / DexScreener / Birdeye link").

  REVIEW  the coin is read by the SAME ten agents on the next pass (it gets a seat at the desk's table even when the board does not
          carry it); the answer is their real opinions — unknown evidence reads PENDING / UNKNOWN, never zero. Kept 30 minutes.
  TRACK   the same, kept on the owner's list until IGNORE (≤ 20 coins).
  ARM     owner priority: among coins the kernel has READY BY ITS OWN RULES, an armed one goes first for the next open seat, and its
          research is queued ahead of the pack. Kept 6 hours (then it is tracked), ≤ 4 coins.
  IGNORE  off the list.

WHAT IT CAN NEVER DO (tests): a review or a track never buys — a coin that is on the desk only because the owner asked is judged and
shown but stays CONTENDING at best ("review only"); ARM never makes a coin READY — the hard wall, Trigger, the rank line, Devil, the
Warden's sizing, Courier's execution health, the keeper's own buy checks (route / sell-back / price near market / pool floor) all decide
exactly as for any other candidate. There is no order, no quote and no wallet call in this module. Pure."""
import re

ACTIONS = ('review', 'track', 'arm', 'ignore')
MODES = ('review', 'track', 'arm')
REVIEW_TTL = 1800.0
ARM_TTL = 6 * 3600.0
TRACK_MAX, ARM_MAX, KEEP = 20, 4, 40
_B58 = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
_ADDR = re.compile(rf'^{_B58}$')
# host → path patterns (group 1 = the address). Anything else is refused: this never follows an arbitrary link.
_URLS = (
    (re.compile(r'^(?:www\.)?pump\.fun$'), re.compile(rf'^/(?:advanced/)?(?:coin/)?({_B58})/?$'), 'mint'),
    (re.compile(r'^(?:www\.)?birdeye\.so$'), re.compile(rf'^/(?:solana/)?token/({_B58})/?$'), 'mint'),
    (re.compile(r'^(?:www\.)?dexscreener\.com$'), re.compile(rf'^/solana/({_B58})/?$'), 'address'),   # a DexScreener link carries the POOL (or the mint)
)


from fnum import nan_safe as _f


def parse(text):
    """The owner's input → {'kind': 'mint' | 'address', 'address': …, 'source': 'ca' | 'pump' | 'birdeye' | 'dexscreener'} or None.
    'address' = a pool OR a mint (resolved against the coins FEELESS already knows, then one token lookup)."""
    s = str(text or '').strip()
    if not s or len(s) > 300 or any(ord(c) < 32 for c in s):
        return None
    if _ADDR.match(s):
        return {'kind': 'address', 'address': s, 'source': 'ca'}
    m = re.match(r'^https?://([^/?#]+)([^?#]*)', s, re.I)
    if not m:
        return None
    host, path = m.group(1).lower(), m.group(2) or '/'
    for h, p, kind in _URLS:
        if h.match(host):
            g = p.match(path)
            if g:
                return {'kind': kind, 'address': g.group(1), 'source': 'pump' if 'pump' in host else 'birdeye' if 'birdeye' in host else 'dexscreener'}
            return None
    return None


def prune(book, now):
    """Expired reviews leave; an expired ARM falls back to TRACK. → a new book {mint: {mode, at, symbol, source}}"""
    out = {}
    for m, e in (book or {}).items():
        if not isinstance(e, dict) or e.get('mode') not in MODES:
            continue
        age = now - _f(e.get('at'))
        if e['mode'] == 'review' and age > REVIEW_TTL:
            continue
        if e['mode'] == 'arm' and age > ARM_TTL:
            e = {**e, 'mode': 'track', 'was': 'arm'}
        out[m] = dict(e)
    return out


def apply(book, mint, action, now, symbol=None, source=None):
    """One owner action → the new book. Raises ValueError with a plain reason when a cap is hit."""
    if action not in ACTIONS:
        raise ValueError('action must be review, track, arm or ignore')
    if not (isinstance(mint, str) and _ADDR.match(mint)):
        raise ValueError('that is not a Solana mint address')
    b = prune(book, now)
    if action == 'ignore':
        b.pop(mint, None)
        return b
    others = {m: e for m, e in b.items() if m != mint}
    if action == 'arm' and sum(1 for e in others.values() if e['mode'] == 'arm') >= ARM_MAX:
        raise ValueError(f'{ARM_MAX} coins are armed already — IGNORE one first')
    if action == 'track' and sum(1 for e in others.values() if e['mode'] in ('track', 'arm')) >= TRACK_MAX:
        raise ValueError(f'{TRACK_MAX} coins are tracked already — IGNORE one first')
    prev = b.get(mint) or {}
    b[mint] = {'mode': action, 'at': now, 'first': prev.get('first') or now, 'symbol': symbol or prev.get('symbol'), 'source': source or prev.get('source')}
    if len(b) > KEEP:   # the oldest plain reviews go first
        for m in sorted((m for m, e in b.items() if e['mode'] == 'review'), key=lambda m: _f(b[m].get('at')))[:len(b) - KEEP]:
            b.pop(m, None)
    return b


def modes(book, now):
    return {m: e['mode'] for m, e in prune(book, now).items()}


def armed(book, now):
    return {m for m, mode in modes(book, now).items() if mode == 'arm'}


def _sev(objs):
    rank = {'HARD_VETO': 3, 'STRONG_WARNING': 2, 'WARNING': 1, 'INFO': 0}
    top = max(objs or [], key=lambda o: rank.get(o[1], 0), default=None)
    return (top[1], str(top[2])[:120]) if top else (None, None)


def result(mint, entry, ms, dec, scan, now, only=False):
    """ONE review row for the page, from the kernel's own state. No MintState yet = RESOLVING (the next pass reads it); every unknown
    number is None (the page prints UNKNOWN / PENDING — never 0)."""
    e = entry or {}
    base = {'mint': mint, 'symbol': e.get('symbol'), 'mode': e.get('mode'), 'at': e.get('at'), 'source': e.get('source'), 'only': bool(only)}
    if not ms or not dec:
        return {**base, 'state': 'RESOLVING', 'why': 'waiting for the next agent pass to read it', 'pending': ['market', 'chart', 'holders', 'early wallets', 'site / X']}
    op, mk, ch, cn, idn = dec.get('opinions') or {}, ms.get('market') or {}, ms.get('chart') or {}, ms.get('chain') or {}, ms.get('identity') or {}
    t, sh, tr, dv, wa, co = (op.get(k) or {} for k in ('tally', 'sherlock', 'trigger', 'devil', 'warden', 'courier'))
    sev, sev_why = _sev(dv.get('objections'))
    sup = _f(mk.get('supply'))
    px = _f(mk.get('price'))
    return {**base, 'symbol': idn.get('symbol') or e.get('symbol'), 'pair': idn.get('pair'), 'state': dec.get('status'), 'why': dec.get('why'), 'rank': dec.get('rank'),
            'ageMin': t.get('ageMin'), 'price': px or None, 'supply': sup or None, 'mc': round(px * sup, 2) if px > 0 and sup > 0 else None,
            'liq': mk.get('liquidity'), 'vol5m': mk.get('volume5m'), 'vol1h': mk.get('volume1h'), 'buyerVelocity': t.get('bpm'), 'volVelocity': t.get('vpm'),
            'buyShare': mk.get('buyShare'), 'move5m': mk.get('move5m'), 'sources': list(idn.get('sources') or [])[:6],
            'chartPhase': ch.get('phase'), 'chartState': ch.get('state'), 'chartQuality': ch.get('quality'),
            'earlyWallets': cn.get('earlyWallets'), 'walletWhy': cn.get('pressWhy'), 'creator': cn.get('cls'), 'holderStatus': cn.get('holderStatus'),
            'holderSafe': cn.get('holderSafe'), 'top10': cn.get('top10'), 'scan': scan,
            'sherlock': {'known': sh.get('known') or [], 'unknown': sh.get('unknown') or []},
            'trigger': {'state': tr.get('state'), 'narrative': tr.get('narrative'), 'why': tr.get('why')},
            'devil': {'severity': sev, 'why': sev_why, 'n': len(dv.get('objections') or []), 'hard': bool(dv.get('hard'))},
            'warden': {'size': wa.get('size'), 'why': wa.get('why')}, 'courier': {'ok': co.get('ok'), 'why': co.get('why')},
            'pending': list(sh.get('unknown') or []), 'decidedAt': now}
