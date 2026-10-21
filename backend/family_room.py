"""🎩 THE FAMILY ROOM — roles, ranks, per-member activity and the family's live vitals (owner, 2026-10-20: "Familia needs a REAL layout —
family vitals, per-member activity, ranks and roles"). Pure + tested; the service hands in each member's closed verified FEELESS trades
(7 days, price result — never fees) and the crew record.

· ROLES — a job the Don gives each member (cosmetic + who-does-what, never a permission over money): 🔫 Hitter · 🔭 Scout · 🗣 Caller ·
  🛡 Enforcer · 💼 Bookkeeper · 🎲 Wildcard.
· RANKS — the Don is the head. The Don may PROMOTE a member to a fixed rank (Underboss / Consigliere / Capo / Soldier); everyone else
  is ranked by their verified trade $ this week (family_wars.ranks). Only one Underboss and one Consigliere at a time.
· ACTIVITY — per member: trades this week, won %, $ result, best trade, win streak, last trade (coin, %, when), HEAT 0–100 (how much
  they traded lately), posts + bounties, status (🔥 on fire · 🟢 active · 💤 quiet · 🆕 new).
· VITALS — the family as one number set: week $ / %, won %, trades, members active 24h, average heat, the hot hand, the longest streak,
  RESPECT 0–100 (result + activity + war record + size), and THE WIRE (the family's newest closed trades, who + rank + coin + %).
Nothing here moves money; there is no shared pot — every member signs their own trades.
"""
ROLES = {'hitter': ('🔫', 'Hitter', 'closes the trades'), 'scout': ('🔭', 'Scout', 'finds the coins'), 'caller': ('🗣', 'Caller', 'calls the plays'),
         'enforcer': ('🛡', 'Enforcer', 'watches for rugs'), 'book': ('💼', 'Bookkeeper', 'keeps the record'), 'wild': ('🎲', 'Wildcard', 'does what it takes')}
PROMOTE = ('underboss', 'consigliere', 'capo', 'soldier')
SINGLE = ('underboss', 'consigliere')
DAY = 86400


def set_role(crew, by, who, role=None, rank=None):
    """The Don sets a member's job and / or fixed rank. role / rank '' clears it. Raises ValueError."""
    if by != crew.get('owner'):
        raise ValueError('Only the Don hands out roles and ranks.')
    if who not in (crew.get('members') or []):
        raise ValueError('That wallet is not in the family.')
    if who == crew.get('owner') and rank:
        raise ValueError('The Don is the Don.')
    roles = crew.setdefault('roles', {})
    cur = dict(roles.get(who) or {})
    if role is not None:
        if role and role not in ROLES:
            raise ValueError('Pick a role from the list.')
        cur['role'] = role or None
    if rank is not None:
        if rank and rank not in PROMOTE:
            raise ValueError('Pick a rank from the list.')
        if rank in SINGLE:
            for w, r in roles.items():
                if w != who and r.get('rank') == rank:
                    r.pop('rank', None)       # one Underboss, one Consigliere — the old one steps down to the auto ladder
        cur['rank'] = rank or None
    roles[who] = {k: v for k, v in cur.items() if v}
    if not roles[who]:
        roles.pop(who)
    return roles.get(who, {})


def ranks(crew, auto):
    """family_wars' auto ladder with the Don's promotions on top. auto: {wallet: (key, label)} → same shape."""
    from family_wars import RANKS
    words = dict(RANKS)
    out = dict(auto)
    for w, r in (crew.get('roles') or {}).items():
        if w in out and w != crew.get('owner') and r.get('rank') in words:
            out[w] = (r['rank'], words[r['rank']])
    return out


def _streak(pieces):
    n = 0
    for p in sorted(pieces, key=lambda p: -p['at']):
        if p['usd'] > 0:
            n += 1
        else:
            break
    return n


def heat(pieces, now):
    """0–100: trades in the last 24h (≤ 6 count) and how recent the last one is."""
    day = [p for p in pieces if now - p['at'] <= DAY]
    if not pieces:
        return 0
    last = now - max(p['at'] for p in pieces)
    recency = max(0.0, 1 - last / (2 * DAY))
    return round(100 * (0.6 * min(1, len(day) / 6) + 0.4 * recency))


def member(crew, wallet, pieces, now, posts=0, bounties=0):
    ps = sorted(pieces or [], key=lambda p: p['at'])
    n = len(ps)
    usd = sum(p['usd'] for p in ps)
    cost = sum(p.get('costUsd') or 0 for p in ps)
    best = max(ps, key=lambda p: p.get('ret') or 0, default=None)
    last = ps[-1] if ps else None
    h = heat(ps, now)
    joined = (crew.get('joined') or {}).get(wallet) or crew.get('created') or 0
    status = 'fire' if h >= 70 else 'active' if h >= 25 else 'new' if now - joined < 2 * DAY else 'quiet'
    role = (crew.get('roles') or {}).get(wallet, {}).get('role')
    return {'trades': n, 'wonPct': round(100 * sum(1 for p in ps if p['usd'] > 0) / n) if n else None, 'usd': round(usd, 2),
            'pct': round(100 * usd / cost, 1) if cost > 0 else None, 'streak': _streak(ps), 'heat': h, 'status': status,
            'best': {'sym': best['symbol'], 'pct': round(100 * (best.get('ret') or 0), 1)} if best and (best.get('ret') or 0) > 0 else None,
            'last': {'sym': last['symbol'], 'pct': round(100 * (last.get('ret') or 0), 1), 'at': last['at']} if last else None,
            'role': role, 'roleIcon': ROLES[role][0] if role in ROLES else None, 'roleLabel': ROLES[role][1] if role in ROLES else None,
            'posts': int(posts), 'bounties': int(bounties), 'joined': joined}


def vitals(crew, mems, now, war=None, place=None):
    """The family as one set of live numbers. mems: {wallet: member()}"""
    ms = list(mems.values())
    trades = sum(m['trades'] for m in ms)
    usd = round(sum(m['usd'] for m in ms), 2)
    won = [m for m in ms if m['trades']]
    won_pct = round(sum(m['wonPct'] * m['trades'] for m in won) / trades) if trades else None
    active = sum(1 for m in ms if m['last'] and now - m['last']['at'] <= DAY)
    avg_heat = round(sum(m['heat'] for m in ms) / len(ms)) if ms else 0
    hot = max(mems.items(), key=lambda kv: (kv[1]['heat'], kv[1]['usd']), default=(None, None))
    streak = max(mems.items(), key=lambda kv: kv[1]['streak'], default=(None, None))
    w = war or {}
    wars = int(w.get('wins') or 0) - int(w.get('losses') or 0)
    respect = round(max(0, min(100, 35 * max(-1, min(1, usd / 50)) / 2 + 17.5     # the week's $ (±$50 = the full swing)
                               + 30 * (active / max(1, len(ms)))                   # who is actually working
                               + 15 * max(0, min(1, (wars + 3) / 6))               # the war record
                               + 10 * min(1, len(ms) / 10)                         # size
                               + 10 * ((won_pct or 0) / 100))))
    return {'trades': trades, 'usd': usd, 'wonPct': won_pct, 'active': active, 'members': len(ms), 'heat': avg_heat, 'respect': respect,
            'hot': {'w': hot[0], 'heat': hot[1]['heat']} if hot[0] and hot[1]['heat'] else None,
            'streak': {'w': streak[0], 'n': streak[1]['streak']} if streak[0] and streak[1]['streak'] else None, 'place': place}


def wire(pieces_by, rank_of, name_of, limit=14):
    """The family's newest closed trades: who, rank, coin, %, $, when."""
    rows = [{'w': w, 'name': name_of(w), 'rank': rank_of.get(w, ('associate', ''))[1], 'sym': p['symbol'], 'pct': round(100 * (p.get('ret') or 0), 1),
             'usd': round(p['usd'], 2), 'at': p['at']} for w, ps in pieces_by.items() for p in ps]
    return sorted(rows, key=lambda r: -r['at'])[:limit]
