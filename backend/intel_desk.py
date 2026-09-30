"""FEELESS Intel desk: the reputation department's database of bad actors.

Pure functions over what FEELESS already records (blocklist strikes, the funder graph, creator launch records):
  actors  — every known rugger / dumper / sniper / bundler / funder, with a threat score where every point is cited
  rings   — crews: wallets joined by who-funded-whom (a funder and its puppets are one ring)
  moves   — what each actor is likely to do next, from their own pattern (tempo, fresh wallets, dormancy)
  check   — which known actors / rings sit inside a list of wallets (a coin's snipers, a chat, a cap table)
The rug shield, FeeCat and the radar read the same snapshot, so the platform gets the same edge everywhere.
"""
HOUR, DAY = 3600, 86400
ROLE_WEIGHT = {'rugger': 34, 'funder': 24, 'bundler': 14, 'dumper': 12, 'sniper': 8}
ROLE_ORDER = ('rugger', 'funder', 'bundler', 'dumper', 'sniper')


def build_actors(block_wallets: dict, funders: dict, creators: dict, protected=frozenset()) -> dict:
    """block_wallets: {w: {mints: {mint: role}, firstSeen, lastSeen, reported}}
    funders: {'funders': {f: {mints, funded, firstSeen, lastSeen}}, 'offenderFunder': {w: f}}
    creators: {w: {rugged, dumped, launches, launchTimes: [ts]}} (only creators with a bad record)."""
    out = {}

    def actor(w):
        return out.setdefault(w, {'address': w, 'roles': {}, 'mints': set(), 'funded': [], 'fundedBy': None, 'firstSeen': None, 'lastSeen': None,
                                  'reported': False, 'rugs': 0, 'dumps': 0, 'launches': 0, 'launchTimes': []})

    def seen(a, first, last):
        if first:
            a['firstSeen'] = min(a['firstSeen'] or first, first)
        if last or first:
            a['lastSeen'] = max(a['lastSeen'] or 0, last or first)
    for w, r in (block_wallets or {}).items():
        if w in protected:
            continue
        a = actor(w)
        for mint, role in (r.get('mints') or {}).items():
            a['roles'][role] = a['roles'].get(role, 0) + 1
            a['mints'].add(mint)
        a['reported'] = a['reported'] or bool(r.get('reported'))
        seen(a, r.get('firstSeen'), r.get('lastSeen'))
    for f, r in ((funders or {}).get('funders') or {}).items():
        if f in protected:
            continue
        a = actor(f)
        a['roles']['funder'] = max(a['roles'].get('funder', 0), len(r.get('mints') or {}))
        a['funded'] = sorted(set(a['funded']) | set(r.get('funded') or []))
        a['mints'] |= set((r.get('mints') or {}).keys())
        seen(a, r.get('firstSeen'), r.get('lastSeen'))
    for w, f in ((funders or {}).get('offenderFunder') or {}).items():
        if w in out and f not in protected:
            out[w]['fundedBy'] = f
    for w, c in (creators or {}).items():
        if w in protected or not (c.get('rugged') or c.get('dumped')):
            continue
        a = actor(w)
        if c.get('rugged'):
            a['roles']['rugger'] = c['rugged']
        if c.get('dumped'):
            a['roles']['dumper'] = c['dumped']
        a['rugs'], a['dumps'], a['launches'] = c.get('rugged') or 0, c.get('dumped') or 0, c.get('launches') or 0
        a['launchTimes'] = sorted(t for t in c.get('launchTimes') or [] if t)
        if a['launchTimes']:
            seen(a, a['launchTimes'][0], a['launchTimes'][-1])
    return out


def threat(a: dict) -> tuple:
    """(score 0–100, evidence) — every point says why and where it came from."""
    ev = []
    for role in ROLE_ORDER:
        n = a['roles'].get(role, 0)
        if not n:
            continue
        pts = min(ROLE_WEIGHT[role] * 2, ROLE_WEIGHT[role] + (n - 1) * ROLE_WEIGHT[role] // 3)
        claim = {'rugger': f'Rugged {n} launch(es)', 'dumper': f'Dumped {n} launch(es) on buyers', 'funder': f'Bankrolled offenders on {n} launch(es) ({len(a["funded"])} puppet wallets)',
                 'bundler': f'Bundled {n} launch(es)', 'sniper': f'Sniped {n} launch(es)'}[role]
        src = 'Creator launch record' if role in ('rugger', 'dumper') else 'Funder graph' if role == 'funder' else 'Launch forensics'
        ev.append({'claim': claim, 'weight': pts, 'source': src})
    if len(a['funded']) >= 5:
        ev.append({'claim': f'Runs a wallet farm ({len(a["funded"])} funded wallets)', 'weight': 10, 'source': 'Funder graph'})
    if a.get('fundedBy'):
        ev.append({'claim': 'Funded by a tracked wallet', 'weight': 6, 'source': 'Funder graph'})
    if a.get('reported'):
        ev.append({'claim': 'Reported and confirmed by FEELESS', 'weight': 15, 'source': 'Moderation'})
    return min(100, sum(e['weight'] for e in ev)), ev


def rings(actors: dict) -> list:
    """Crews = connected components of funder → funded edges (only components with 2+ tracked wallets)."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)
    for w, a in actors.items():
        for p in a['funded']:
            union(w, p)
        if a.get('fundedBy'):
            union(w, a['fundedBy'])
    groups = {}
    for w in parent:
        groups.setdefault(find(w), []).append(w)
    out = []
    for members in groups.values():
        tracked = [m for m in members if m in actors]
        if len(tracked) < 2:
            continue
        core = max(tracked, key=lambda m: (len(actors[m]['funded']), threat(actors[m])[0]))
        mints = set().union(*(actors[m]['mints'] for m in tracked))
        last = max((actors[m]['lastSeen'] or 0) for m in tracked)
        score = min(100, max(threat(actors[m])[0] for m in tracked) + 4 * (len(tracked) - 1))
        out.append({'id': core[:6], 'core': core, 'members': sorted(tracked), 'size': len(tracked), 'launchesHit': len(mints),
                    'rugs': sum(actors[m]['rugs'] for m in tracked), 'lastActive': last, 'threat': score})
    return sorted(out, key=lambda r: (-r['threat'], -r['size']))


def next_moves(a: dict, now: float) -> list:
    """What this actor is likely to do next, from its own pattern. Each move cites the pattern it comes from."""
    out = []
    last = a.get('lastSeen') or 0
    t = a.get('launchTimes') or []
    if len(t) >= 3:
        gaps = [b - x for x, b in zip(t, t[1:]) if b > x]
        if gaps:
            avg = sum(gaps) / len(gaps)
            due = t[-1] + avg
            out.append({'move': 'Next launch due' if due >= now else 'Overdue for a new launch', 'eta': due, 'confidence': 'high' if len(t) >= 5 else 'medium',
                        'why': f'Launches every ~{avg / HOUR:.0f}h ({len(t)} launches on record)'})
    if a['roles'].get('funder') and last and now - last < DAY:
        out.append({'move': 'Loading fresh wallets for the next snipe', 'eta': None, 'confidence': 'medium', 'why': f'Funded offenders in the last 24h ({len(a["funded"])} so far)'})
    if (a['roles'].get('sniper') or a['roles'].get('bundler')) and last and now - last < 6 * HOUR:
        out.append({'move': 'Active right now', 'eta': None, 'confidence': 'high', 'why': 'Hit a launch in the last 6 hours'})
    if last and now - last > 14 * DAY and sum(a['roles'].values()) >= 2:
        out.append({'move': 'Dormant — expect new wallets, same funder', 'eta': None, 'confidence': 'low', 'why': f'Quiet for {int((now - last) / DAY)} days after {sum(a["roles"].values())} strikes'})
    return out


def public_actor(a: dict, now: float) -> dict:
    score, ev = threat(a)
    return {'address': a['address'], 'roles': sorted(a['roles'], key=ROLE_ORDER.index), 'strikes': sum(a['roles'].values()), 'launches': len(a['mints']),
            'rugs': a['rugs'], 'funded': len(a['funded']), 'fundedBy': a.get('fundedBy'), 'firstSeen': a['firstSeen'], 'lastSeen': a['lastSeen'],
            'threat': score, 'evidence': ev, 'moves': next_moves(a, now)}


def snapshot(actors: dict, now: float, top: int = 60) -> dict:
    rows = [public_actor(a, now) for a in actors.values()]
    rows.sort(key=lambda r: (-r['threat'], -(r['lastSeen'] or 0)))
    rg = rings(actors)
    ring_of = {m: r['id'] for r in rg for m in r['members']}
    for r in rows:
        r['ring'] = ring_of.get(r['address'])
    by_role = {role: sum(1 for a in actors.values() if a['roles'].get(role)) for role in ROLE_ORDER}
    moves = sorted(({**m, 'address': r['address'], 'threat': r['threat'], 'ring': r['ring']} for r in rows for m in r['moves']),
                   key=lambda m: ({'high': 0, 'medium': 1, 'low': 2}[m['confidence']], -m['threat']))
    return {'at': now, 'totals': {'actors': len(actors), **by_role, 'rings': len(rg), 'active24h': sum(1 for a in actors.values() if a['lastSeen'] and now - a['lastSeen'] < DAY),
                                  'new7d': sum(1 for a in actors.values() if a['firstSeen'] and now - a['firstSeen'] < 7 * DAY)},
            'wanted': rows[:top], 'rings': rg[:30], 'moves': moves[:40], 'index': {r['address']: {'threat': r['threat'], 'roles': r['roles'], 'ring': r['ring']} for r in rows}}


def check(index: dict, rings_list: list, addresses: list) -> dict:
    """Known actors inside a list of wallets, and the crews they belong to."""
    hits = {a: index[a] for a in addresses if a in index}
    ring_ids = {h['ring'] for h in hits.values() if h.get('ring')}
    crews = [{k: r[k] for k in ('id', 'core', 'size', 'launchesHit', 'rugs', 'threat')} for r in rings_list if r['id'] in ring_ids]
    return {'known': hits, 'rings': crews, 'maxThreat': max((h['threat'] for h in hits.values()), default=0)}
