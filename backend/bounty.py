"""🪙 RUG BOUNTY (pure, read-only): who found which bad wallets, from the blocklist records themselves. Reports are accepted only when FEELESS's own
forensics prove the wallet bundled / sniped that coin (the POST /blocklist rule), so a board row is already evidence-checked. The FIRST reporter of a
wallet is its finder; a finder earns 25 season points per newly flagged wallet, capped at 100 a coin (the same rule the award uses)."""
from collections import defaultdict

PTS_EACH, PTS_CAP = 25, 100


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def finds(block_wallets):
    """→ [{wallet, mint, role, by, at}]: for every flagged wallet, its FIRST report on each coin (that reporter found it)."""
    out = []
    for w, rec in (block_wallets or {}).items():
        first = {}
        for r in sorted(rec.get('reports') or [], key=lambda r: _f(r.get('at'))):
            first.setdefault(r.get('mint'), r)
        # the finder of a WALLET is whoever reported it first overall — later coins by other reporters are confirmations, not new finds
        if first:
            f = min(first.values(), key=lambda r: _f(r.get('at')))
            out.append({'wallet': w, 'mint': f.get('mint'), 'role': f.get('role'), 'by': f.get('by') or 'anon', 'at': _f(f.get('at'))})
    return out


def points(n):
    return min(PTS_CAP, PTS_EACH * n)


def board(block_wallets, now, week=7 * 86400, recent=12, top=10):
    fs = [f for f in finds(block_wallets) if f['by'] != 'anon' and f['at'] > 0]
    by_coin = defaultdict(list)
    for f in fs:
        by_coin[f['mint']].append(f)
    coins = []
    for m, rows in by_coin.items():
        finders = defaultdict(int)
        for r in rows:
            finders[r['by']] += 1
        coins.append({'mint': m, 'wallets': len(rows), 'at': max(r['at'] for r in rows), 'finders': sorted(finders, key=lambda k: -finders[k])[:3],
                      'bundlers': sum(1 for r in rows if r['role'] == 'bundler'), 'snipers': sum(1 for r in rows if r['role'] == 'sniper')})
    coins.sort(key=lambda c: -c['at'])
    def leaders(since):
        per = defaultdict(lambda: defaultdict(int))
        for f in fs:
            if f['at'] >= since:
                per[f['by']][f['mint']] += 1
        rows = [{'by': by, 'wallets': sum(c.values()), 'coins': len(c), 'pts': sum(points(n) for n in c.values())} for by, c in per.items()]
        return sorted(rows, key=lambda r: (-r['pts'], -r['wallets']))[:top]
    return {'recent': coins[:recent], 'week': leaders(now - week), 'all': leaders(0), 'total': {'coins': len(by_coin), 'wallets': len(fs)},
            'rule': f'Only wallets FEELESS\'s own forensics prove bundled or sniped the coin are accepted. The first finder earns {PTS_EACH} season points per newly flagged wallet, max {PTS_CAP} a coin.'}


def find_events(block_wallets, mine):
    """Timestamps of the wallets one person (any linked wallet in `mine`) found first — the weekly 'flag a rug wallet' quest reads these."""
    mine = set(mine)
    return [f['at'] for f in finds(block_wallets) if f['by'] in mine]
