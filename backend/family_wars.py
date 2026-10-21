"""⚔ FAMILY WARS — battle-trench PvP between families (owner, 2026-10-20: "families can partner or bid up a pot to set a date to battle-trench,
PvP team vs team, exclusive perks by crew and individual rank"). Pure + tested; the service holds the store (crews.json) and the lock.

THE MONEY RULE: a pot is FAMILY POINTS (the war chest), never money, never a bet on a coin. Each family starts with CHEST_START points and earns more by
winning wars. Every member still signs their own trades; a war only COUNTS what each team member's VERIFIED FEELESS trades did inside the window
(price result, fees apart — the same pieces the weekly board reads).

Life of a war: the head of family A challenges family B with a stake + a date (≥ 15 min, ≤ 7 days out) and a length (1 / 4 / 12 / 24h) → B's head
accepts (matching at least A's stake) or declines (A is refunded) → before the bell either head may raise its own side; an ALLY of a side may join
it (its stake + its members) → at the bell the war is LIVE → at the end the side with the better % result over its team's closed trades takes the
whole pot into its chest; a side with no closed trade loses; neither = a draw, every stake goes home. Not answered by the bell = void, refunded.
"""
import uuid

CHEST_START = 500
STAKE_MIN, STAKE_MAX = 25, 5000
HOURS = (1, 4, 12, 24)
LEAD_MIN, LEAD_MAX = 15 * 60, 7 * 86400
TEAM_MAX = 5
WARS_KEPT = 120
OPEN, SET, LIVE, DONE, VOID, DECLINED = 'open', 'set', 'live', 'done', 'void', 'declined'
# 🎩 member ranks inside a family (by what the member's verified trades made this week; the head is always the Don)
RANKS = (('don', '🎩 Don'), ('underboss', '🥃 Underboss'), ('consigliere', '📜 Consigliere'), ('capo', '🔫 Capo'), ('soldier', '🗡 Soldier'), ('associate', '🤝 Associate'))


def _crews(st):
    return st.setdefault('crews', {})


def chest(c):
    """The family's war chest (points). Families made before wars start with CHEST_START."""
    if c.get('chest') is None:
        c['chest'] = CHEST_START
    return int(c['chest'])


def _head(st, wallet):
    c = next((c for c in _crews(st).values() if c.get('owner') == wallet), None)
    if not c:
        raise ValueError('Only the head of a family (its Don) can do that.')
    return c


def _find(st, vs):
    vs = str(vs or '').strip().upper()
    for c in _crews(st).values():
        if c['id'] == vs or str(c.get('tag') or '').upper() == vs:
            return c
    raise ValueError('No family with that tag.')


def _war(st, wid):
    w = next((w for w in st.get('wars') or [] if w['id'] == wid), None)
    if not w:
        raise ValueError('No such war.')
    return w


def _take(c, n):
    n = int(n)
    if n < 1:
        raise ValueError('Stake at least 1 point.')
    if chest(c) < n:
        raise ValueError(f'The war chest holds {chest(c)} points — not enough for {n}.')
    c['chest'] = chest(c) - n
    return n


def allied(st, a, b):
    return any({a, b} == {x[0], x[1]} for x in st.get('alliances') or [])


def side_of(w, cid):
    if cid == w['a'] or cid in (w.get('allies') or {}).get('a', []):
        return 'a'
    if cid == w['b'] or cid in (w.get('allies') or {}).get('b', []):
        return 'b'
    return None


def challenge(st, wallet, vs, stake, start_at, hours, now, team=None):
    me = _head(st, wallet)
    them = _find(st, vs)
    if them['id'] == me['id']:
        raise ValueError('A family cannot go to war with itself.')
    if allied(st, me['id'], them['id']):
        raise ValueError('You are allies — break the alliance before you go to war.')
    if any(w['state'] in (OPEN, SET, LIVE) and {w['a'], w['b']} == {me['id'], them['id']} for w in st.get('wars') or []):
        raise ValueError('There is already a war on between these families.')
    stake = int(stake)
    if not STAKE_MIN <= stake <= STAKE_MAX:
        raise ValueError(f'Stake {STAKE_MIN}–{STAKE_MAX} points.')
    start_at = float(start_at)
    if not now + LEAD_MIN <= start_at <= now + LEAD_MAX:
        raise ValueError('Set the bell 15 minutes to 7 days from now.')
    if int(hours) not in HOURS:
        raise ValueError('A war lasts 1, 4, 12 or 24 hours.')
    _take(me, stake)
    w = {'id': uuid.uuid4().hex[:10], 'a': me['id'], 'b': them['id'], 'pot': {'a': stake, 'b': 0}, 'paid': {me['id']: stake}, 'startAt': start_at,
         'hours': int(hours), 'state': OPEN, 'by': wallet, 'createdAt': now, 'allies': {'a': [], 'b': []},
         'teams': {me['id']: _team(me, team)}, 'log': [[now, f"[{me['tag']}] called out [{them['tag']}] for {stake} pts"]]}
    st.setdefault('wars', []).append(w)
    st['wars'] = st['wars'][-WARS_KEPT:]
    return w


def _team(c, team):
    mem = list(c.get('members') or [])
    pick = [m for m in (team or []) if m in mem][:TEAM_MAX]
    return pick or mem[:TEAM_MAX]


def answer(st, wallet, wid, ok, stake=None, now=None, team=None):
    w = _war(st, wid)
    me = _head(st, wallet)
    if me['id'] != w['b'] or w['state'] != OPEN:
        raise ValueError('Only the challenged family answers an open call-out.')
    a = _crews(st)[w['a']]
    if not ok:
        a['chest'] = chest(a) + w['pot']['a']
        w['state'] = DECLINED
        w['log'].append([now, f"[{me['tag']}] declined — {w['pot']['a']} pts back to [{a['tag']}]"])
        return w
    n = _take(me, max(int(stake or 0), w['pot']['a']))
    w['pot']['b'] += n
    w['paid'][me['id']] = w['paid'].get(me['id'], 0) + n
    w['teams'][me['id']] = _team(me, team)
    w['state'] = SET
    w['log'].append([now, f"[{me['tag']}] accepted with {n} pts — pot {pot(w)}"])
    return w


def pot(w):
    return int(w['pot']['a']) + int(w['pot']['b'])


def raise_pot(st, wallet, wid, add, now):
    """🔥 Bid up the pot before the bell: a head adds points to ITS side."""
    w = _war(st, wid)
    me = _head(st, wallet)
    sd = side_of(w, me['id'])
    if not sd or w['state'] not in (OPEN, SET) or now >= w['startAt']:
        raise ValueError('Only a side of this war can raise, before the bell.')
    n = _take(me, add)
    w['pot'][sd] += n
    w['paid'][me['id']] = w['paid'].get(me['id'], 0) + n
    w['log'].append([now, f"[{me['tag']}] raised +{n} — pot {pot(w)}"])
    return w


def join_side(st, wallet, wid, add, now, team=None):
    """🤝 An ally joins a side before the bell: its stake goes in the pot, its team trades for that side."""
    w = _war(st, wid)
    me = _head(st, wallet)
    if w['state'] != SET or now >= w['startAt']:
        raise ValueError('Allies join an accepted war, before the bell.')
    if side_of(w, me['id']):
        raise ValueError('Your family is already in this war.')
    sd = 'a' if allied(st, me['id'], w['a']) else 'b' if allied(st, me['id'], w['b']) else None
    if not sd:
        raise ValueError('Only an ally of one side can join.')
    n = _take(me, max(STAKE_MIN, int(add or 0)))
    w['pot'][sd] += n
    w['paid'][me['id']] = w['paid'].get(me['id'], 0) + n
    w['allies'][sd].append(me['id'])
    w['teams'][me['id']] = _team(me, team)
    w['log'].append([now, f"[{me['tag']}] joined their ally with {n} pts — pot {pot(w)}"])
    return w


def set_team(st, wallet, wid, members, now):
    w = _war(st, wid)
    me = _head(st, wallet)
    if not side_of(w, me['id']) or w['state'] not in (OPEN, SET) or now >= w['startAt']:
        raise ValueError('Pick your team before the bell.')
    w['teams'][me['id']] = _team(me, members)
    return w


def ally(st, wallet, vs, now):
    """🤝 Propose an alliance; the other head proposing back (or accepting) seals it."""
    me = _head(st, wallet)
    them = _find(st, vs)
    if them['id'] == me['id']:
        raise ValueError('Pick another family.')
    if allied(st, me['id'], them['id']):
        raise ValueError('Already allies.')
    asks = st.setdefault('allyAsks', [])
    back = next((x for x in asks if x[0] == them['id'] and x[1] == me['id']), None)
    if back:
        asks.remove(back)
        st.setdefault('alliances', []).append([me['id'], them['id'], now])
        return 'sealed'
    if not any(x[0] == me['id'] and x[1] == them['id'] for x in asks):
        asks.append([me['id'], them['id'], now])
    return 'asked'


def break_ally(st, wallet, vs):
    me = _head(st, wallet)
    them = _find(st, vs)
    st['alliances'] = [x for x in st.get('alliances') or [] if {x[0], x[1]} != {me['id'], them['id']}]


def side_score(w, sd, pieces_by_wallet):
    """A side's result over the window: every team member (the family + its allies) and their closed trades inside it."""
    t0, t1 = w['startAt'], w['startAt'] + w['hours'] * 3600
    fams = [w[sd]] + list((w.get('allies') or {}).get(sd) or [])
    wallets = {m for f in fams for m in (w.get('teams') or {}).get(f) or []}
    ps = [p for m in wallets for p in pieces_by_wallet.get(m, []) if t0 <= float(p.get('at') or 0) <= t1]
    usd, cost = sum(float(p['usd']) for p in ps), sum(float(p['costUsd']) for p in ps)
    return {'trades': len(ps), 'usd': round(usd, 2), 'pct': round(100 * usd / cost, 2) if cost > 0 else None, 'team': len(wallets),
            'won': sum(1 for p in ps if float(p['usd']) > 0)}


def tick(st, pieces_by_wallet, now):
    """⏱ The war clock: unanswered at the bell → void (refund) · accepted at the bell → LIVE · LIVE past its end → settled. → [event lines]"""
    out = []
    crews = _crews(st)
    for w in st.get('wars') or []:
        if w['state'] == OPEN and now >= w['startAt']:
            for cid, n in (w.get('paid') or {}).items():
                if cid in crews:
                    crews[cid]['chest'] = chest(crews[cid]) + int(n)
            w['state'] = VOID
            w['log'].append([now, 'no answer by the bell — stakes returned'])
        elif w['state'] == SET and now >= w['startAt']:
            w['state'] = LIVE
            w['log'].append([now, f"🔔 the bell — {w['hours']}h battle trench, pot {pot(w)} pts"])
            out.append((w, 'live'))
        elif w['state'] == LIVE and now >= w['startAt'] + w['hours'] * 3600:
            a, b = side_score(w, 'a', pieces_by_wallet), side_score(w, 'b', pieces_by_wallet)
            win = _winner(a, b)
            w['result'] = {'a': a, 'b': b, 'winner': win}
            if win is None:
                for cid, n in (w.get('paid') or {}).items():
                    if cid in crews:
                        crews[cid]['chest'] = chest(crews[cid]) + int(n)
                w['log'].append([now, 'draw — every stake went home'])
            else:
                lose = 'b' if win == 'a' else 'a'
                fams = [w[win]] + list(w['allies'].get(win) or [])
                stake_in = {f: int((w.get('paid') or {}).get(f, 0)) for f in fams}
                tot = sum(stake_in.values()) or 1
                for f in fams:   # the pot is split over the winning side by what each put in
                    if f in crews:
                        crews[f]['chest'] = chest(crews[f]) + round(pot(w) * stake_in[f] / tot)
                        crews[f]['warWins'] = int(crews[f].get('warWins') or 0) + 1
                for f in [w[lose]] + list(w['allies'].get(lose) or []):
                    if f in crews:
                        crews[f]['warLosses'] = int(crews[f].get('warLosses') or 0) + 1
                w['log'].append([now, f"🏆 [{crews.get(w[win], {}).get('tag', '?')}] took the pot of {pot(w)} pts"])
            w['state'] = DONE
            w['endedAt'] = now
            out.append((w, 'done'))
    return out


def _winner(a, b):
    ta, tb = a['trades'] > 0 and a['pct'] is not None, b['trades'] > 0 and b['pct'] is not None
    if not ta and not tb:
        return None
    if ta != tb:
        return 'a' if ta else 'b'
    if abs(a['pct'] - b['pct']) < 0.01:
        return None
    return 'a' if a['pct'] > b['pct'] else 'b'


def view(w, crews, pieces_by_wallet, now):
    """The page's card for one war: both sides (tag, name, badge colors), pot, clock, live score while LIVE."""
    def fam(cid):
        c = crews.get(cid) or {}
        return {'id': cid, 'tag': c.get('tag'), 'name': c.get('name'), 'badge': (c.get('badge') or {})}
    end = w['startAt'] + w['hours'] * 3600
    live = w['state'] in (LIVE, DONE)
    sc = w.get('result') or ({'a': side_score(w, 'a', pieces_by_wallet), 'b': side_score(w, 'b', pieces_by_wallet)} if live else None)
    return {'id': w['id'], 'state': w['state'], 'a': fam(w['a']), 'b': fam(w['b']), 'allies': {k: [fam(x) for x in v] for k, v in (w.get('allies') or {}).items()},
            'pot': pot(w), 'potSides': dict(w['pot']), 'startAt': w['startAt'], 'endAt': end, 'hours': w['hours'],
            'clock': round((w['startAt'] if w['state'] in (OPEN, SET) else end) - now), 'score': sc, 'winner': (w.get('result') or {}).get('winner'),
            'teams': {k: len(v) for k, v in (w.get('teams') or {}).items()}, 'log': [[round(t), x] for t, x in (w.get('log') or [])[-8:]]}


def ranks(crew, mem_stats):
    """🎩 Each member's rank: the head is the Don; the rest by their verified trade $ this week — Underboss, Consigliere, two Capos, then
    Soldiers; a member with no closed trade this week is an Associate. → {wallet: (key, label)}"""
    out = {}
    owner = crew.get('owner')
    out[owner] = RANKS[0]
    rest = sorted((m for m in crew.get('members') or [] if m != owner), key=lambda m: -float((mem_stats.get(m) or {}).get('usd') or 0))
    ladder = [RANKS[1], RANKS[2], RANKS[3], RANKS[3]]
    for i, m in enumerate(rest):
        if not (mem_stats.get(m) or {}).get('trades'):
            out[m] = RANKS[5]
        else:
            out[m] = ladder[i] if i < len(ladder) else RANKS[4]
    return out


def record(crew):
    return {'wins': int(crew.get('warWins') or 0), 'losses': int(crew.get('warLosses') or 0), 'chest': chest(crew)}


def board(st, now):
    """⚔ The war room's public list: live first, then set (by bell), open call-outs, then the last finished ones."""
    order = {LIVE: 0, SET: 1, OPEN: 2, DONE: 3, VOID: 4, DECLINED: 5}
    ws = sorted(st.get('wars') or [], key=lambda w: (order.get(w['state'], 9), w['startAt'] if w['state'] in (SET, OPEN) else -(w.get('endedAt') or w['createdAt'])))
    return ws

