"""⚡ FREE HOURLY CALL (pure, read-only logic): every hour the engine's own doors (Pump trending · Volume · Movers · New launches) each put their top coin on
a ballot at its price. A wallet picks the coin it thinks leads the NEXT hour; at the bell the biggest move wins. Points only — no money, no stake,
nothing to deposit. One pick a round, locked once made; picks close 2 minutes before the bell. Wins build a streak (more points, capped).
Everything is judged on recorded prices, so a result can be checked."""
ROUND_SEC = 3600
LOCK_SEC = 120
BASE_PTS, STREAK_PTS, STREAK_CAP = 10, 5, 20
DOORS = (('ptrend', '🔥 Pump trending'), ('volume', '🌊 Volume'), ('movers', '🚀 Movers'), ('pump', '🆕 New launches'))


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def round_id(now):
    return int(now // ROUND_SEC * ROUND_SEC)


def candidates(lists, prices, symbols=None, taken=(), n=4):
    """One coin per door (its top-most coin that has a live price and is not already on the ballot), best door order first."""
    sym, out, seen = symbols or {}, [], set(taken)
    for key, label in DOORS:
        for row in (lists or {}).get(key) or []:
            m = row.get('mint')
            if not m or m in seen or _f((prices or {}).get(m)) <= 0:
                continue
            seen.add(m); out.append({'mint': m, 'symbol': sym.get(m) or m[:4].upper(), 'door': key, 'doorLabel': label, 'px0': _f(prices[m])})
            break
        if len(out) >= n:
            break
    return out


def new_round(now, cands):
    rid = round_id(now)
    return {'id': rid, 'opensAt': now, 'closesAt': rid + ROUND_SEC, 'cands': cands, 'picks': {}, 'status': 'open'}


def can_pick(rnd, mint, now):
    """(ok, why)"""
    if not rnd or rnd.get('status') != 'open':
        return False, 'No open round.'
    if now >= _f(rnd.get('closesAt')) - LOCK_SEC:
        return False, 'Picks are closed for this round — the next one opens at the bell.'
    if mint not in {c['mint'] for c in rnd.get('cands') or []}:
        return False, 'That coin is not on this round\'s ballot.'
    return True, ''


def moves(rnd, prices_now):
    """{mint: % move since the round opened} for every ballot coin with a price now."""
    return {c['mint']: round((_f(prices_now.get(c['mint'])) / c['px0'] - 1) * 100, 2) for c in rnd.get('cands') or [] if c['px0'] > 0 and _f(prices_now.get(c['mint'])) > 0}


def settle(rnd, prices_now):
    """→ {'winner': mint|None, 'moves': {...}}. Needs ≥ 2 priced coins; the biggest move wins, a tie goes to the earlier ballot place."""
    mv = moves(rnd, prices_now)
    if len(mv) < 2:
        return {'winner': None, 'moves': mv}
    order = [c['mint'] for c in rnd['cands']]
    return {'winner': max(mv, key=lambda m: (mv[m], -order.index(m))), 'moves': mv}


def award(players, rnd, winner, now):
    """Update every player of the round (picks / wins / streak / event times); → [(wallet, points)] for the winners."""
    paid = []
    for w, mint in (rnd.get('picks') or {}).items():
        p = players.setdefault(w, {'picks': 0, 'wins': 0, 'streak': 0, 'best': 0, 'pickAt': [], 'winAt': []})
        p['picks'] += 1
        if winner and mint == winner:
            p['wins'] += 1; p['streak'] += 1; p['best'] = max(p['best'], p['streak']); p['winAt'] = (p['winAt'] + [now])[-200:]
            paid.append((w, BASE_PTS + min(STREAK_CAP, STREAK_PTS * (p['streak'] - 1))))
        elif winner:
            p['streak'] = 0
    return paid


def board(players, now, week=7 * 86400, top=8):
    rows = []
    for w, p in players.items():
        wins = sum(1 for t in p.get('winAt') or [] if now - t < week); picks = sum(1 for t in p.get('pickAt') or [] if now - t < week)
        if picks:
            rows.append({'address': w, 'wins': wins, 'picks': picks, 'streak': p.get('streak', 0)})
    return sorted(rows, key=lambda r: (-r['wins'], -r['streak'], r['picks']))[:top]
