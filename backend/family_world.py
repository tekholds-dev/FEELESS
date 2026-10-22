"""🗺 LA FAMILIA WORLD (owner, 2026-10-21: "the city can't be a baby grid — huge, bridges to other parts, seasons, buy blocks near rivals, CPU towns
that are hard to raid, CARTELS = the bundlers / snipers / funders with their own city from rep, chess moves when you enter a rival city, recruitment
challenges, click / drag errands for every store, points with real rewards … like Godfather PSP / Jailblock"). Pure + tested; the service holds the
store, the clock and the I/O. Everything here is POINTS (MP) — the only money paths are the gold shop and the FEECAT redeem claim, both handled by
the service (SOL the buyer signs, a claim the owner pays by hand).

· THE MAP = 6 BOROUGHS × 16 blocks (96), joined by named BRIDGES. Every family gets a free HOME block; more blocks are bought with MP (TURF:
  +4 % production and +1 recruit seat each). Turf also decides REACH: a family raids rivals in boroughs it holds or one bridge away (+1 bridge per
  3 docks levels). Relocating the home block costs MP (the gas station cuts it).
· CPU TOWNS = 8 computer families that never sleep: high-level guards, fat stashes, they answer every raid move at once with the best defence.
· CARTELS = the bundler / sniper / funder crews FEELESS's own rep has flagged (built from the blocklist by shared coins). Their city grows with
  their strikes; they rank in their own category; raiding a cartel pays a JUSTICE bonus.
· A RAID = a chess game on the target's 5×5 block: the attacker sends ONE member; that member's rank is the move power. Attacker move → defender
  move, for 2 rounds (+1 per 3 tower levels). A human defender has RESPOND_SEC to answer or the house answers for them; a CPU town / cartel answers
  at once. Dice are seeded by the raid id + move number (replayable, testable).
· RECRUITMENT CHALLENGES unlock special high-level recruits; ERRANDS (one per store type) pay MP + member points on a per-member cooldown;
  REWARDS spend MP on rushes, shields and titles; 1,000,000 MP redeem into a FEECAT claim the owner pays.
"""
import hashlib
import random

BLOCKS_PER = 16
#           key       name               icon  col row  tier  vibe
BOROUGHS = [('harbor', 'Pump Harbor',     '⚓', 0, 0, 1.0, 'launch piers, fresh coins every hour'),
            ('heights', 'Raydium Heights', '🏙', 1, 0, 1.4, 'old money, deep pools, rooftop bars'),
            ('hills', 'Jupiter Hills',     '🪐', 2, 0, 1.6, 'every route in town runs through here'),
            ('market', 'Meteora Market',   '☄', 0, 1, 1.2, 'dynamic stalls, dynamic fees'),
            ('bay', 'Bonk Bay',            '🐕', 1, 1, 1.0, 'the dog coins run the boardwalk'),
            ('docks', 'Cartel Docks',      '🕳', 2, 1, 0.8, 'bundlers, snipers and funders — the cartels\' turf'),
            ('fee', 'Fee City',            '👑', 1, 2, 2.5, 'the capital: premium plots, the Fuse Arena, the house money')]
# 👑 FEE CITY (owner, 2026-10-21: "the main city … most expensive / profitable plots … bigger than the 4 other cities, one chat box each"):
# the hub every city bridges into, 24 premium plots, never a free home block (homes seed in the outer five). The four outer CITIES group the
# old boroughs; raids, reach and turf still count by borough.
PLOTS = {'fee': 24}
CITIES = [('fee', 'FEE CITY', ['fee'], 'Capital of the Trenches'),
          ('harbor', 'Pump Harbor', ['harbor', 'market'], 'launch piers + dynamic stalls'),
          ('heights', 'Raydium Heights', ['heights', 'hills'], 'old money, every route'),
          ('bay', 'Bonk Bay', ['bay'], 'the dog coins run the boardwalk'),
          ('docks', 'Cartel Docks', ['docks'], 'the cartels\' turf')]
# the capital's landmarks (never for sale): each one is a FEELESS money-maker, its live number comes from the service
LANDMARKS = [('arena', '⚔ FUSE ARENA', 'The stadium. Family Fuse: two families\' Fuse cards (same coin count, ±1) battle for paper or MP; '
              'MP battles need 2,000 MP in the bank. The crowd bids on the winner.'),
             ('house', '🏦 THE HOUSE', 'Every collect in every city pays the house tax into this vault. The richest building in Fee City.'),
             ('mansion', '🎩 CREATOR\'S MANSION', 'Home of the creator family — the FEELESS desk. Its lights are the real card\'s trades.'),
             ('shield', '🛡 RUG SHIELD HQ', 'Every bundler, sniper and funder FEELESS has flagged. The cartels across the water fear this tower.'),
             ('launch', '🚀 LAUNCH PAD', 'Coins launched by families on FEELESS land here first.')]
BKEYS = [b[0] for b in BOROUGHS]
BRIDGES = [('harbor', 'heights', 'Golden Fee Bridge'), ('heights', 'hills', 'Oracle Span'), ('harbor', 'market', 'Curve Causeway'),
           ('heights', 'bay', 'Bonk Boardwalk'), ('hills', 'docks', 'Rug Bridge'), ('market', 'bay', 'Liquidity Link'), ('bay', 'docks', 'Sniper Strait'),
           ('fee', 'harbor', 'Crown Bridge'), ('fee', 'heights', 'Golden Gate of Fee'), ('fee', 'bay', 'Moonshot Span'), ('fee', 'docks', 'Last Call Bridge')]
BLOCK_MP = 2400
TURF_MAX = 12
MOVE_MP = 1500
RESPOND_SEC = 240
PAIR_COOL = 2 * 3600
LOOT_MAX = 0.35
JUSTICE = 1.5
RANK_POWER = {'don': 3, 'underboss': 3, 'consigliere': 2, 'capo': 2, 'soldier': 1, 'associate': 1}
ACTIONS_A = {'hit': 'steal that store\'s share of the stash', 'sabotage': 'shut that store down for 2 hours',
             'scout': 'see the guards on that lot and the two beside it', 'retreat': 'leave now with the loot'}
ACTIONS_D = {'guard': '+3 defence on that lot for the rest of the raid', 'counter': 'strike the raiders: hurt a hitter, win back half the loot',
             'lockdown': 'once a raid: move half the stash into the bank'}
SEASONS = {1: ('❄ Frost Run', 'snow'), 2: ('💘 Rug & Roses', 'rain'), 3: ('🍀 Green Candles', 'clear'), 4: ('🌧 Bear Showers', 'rain'),
           5: ('🌸 Moon Bloom', 'clear'), 6: ('☀ Summer Pump', 'clear'), 7: ('🎆 Firework Season', 'embers'), 8: ('🌩 Heat Storm', 'storm'),
           9: ('🍂 Autumn Static', 'fog'), 10: ('🎃 Haunted Trenches', 'fog'), 11: ('🦃 Feast of Fees', 'rain'), 12: ('🎄 Cold Wallets', 'snow')}


def _h(s):
    return int(hashlib.sha256(str(s).encode()).hexdigest()[:12], 16)


def block_ids(bk=None):
    return [f'{b}-{i}' for b in ([bk] if bk else BKEYS) for i in range(PLOTS.get(b, BLOCKS_PER))]


def borough_of(bid):
    return str(bid).split('-')[0]


def tier(bk):
    return next((b[5] for b in BOROUGHS if b[0] == bk), 1.0)


def blank():
    return {'own': {}, 'home': {}, 'raids': {}, 'pairCool': {}, 'cpu': {}, 'log': [], 'n': 0}


def season(now):
    import time as _t
    m = _t.gmtime(now).tm_mon
    name, weather = SEASONS[m]
    return {'name': name, 'weather': weather, 'month': m}


def boom(word):
    """Today's hottest narrative booms one borough (×1.25): the same word always lands on the same borough."""
    if not word:
        return None
    return {'word': str(word)[:24], 'borough': BKEYS[_h(str(word).lower()) % 5], 'mult': 1.25}   # never the docks


# ── CPU towns ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
CPU = [('cpu-1', 'Rugpull Racketeers', 'RUG', 'harbor', 6), ('cpu-2', 'The Liquidity Mob', 'LIQ', 'heights', 8),
       ('cpu-3', 'Oracle Outfit', 'ORC', 'hills', 9), ('cpu-4', 'Curve Cosa Nostra', 'CRV', 'market', 7),
       ('cpu-5', 'Boardwalk Bonkers', 'BNK', 'bay', 6), ('cpu-6', 'Gas Station Gang', 'GAS', 'harbor', 5),
       ('cpu-7', 'Penthouse Whales', 'WHL', 'heights', 10), ('cpu-8', 'Route 66 Routers', 'RTE', 'hills', 8)]
STORE_KEYS = ['pizza', 'gas', 'laundry', 'pharma', 'mart', 'lounge', 'docks', 'lab', 'casino', 'bank', 'tower', 'park']


def cpu_town(cid, now):
    """A CPU town is drawn from its seed: stores, levels, guards (levels 5–10). Hard on purpose."""
    row = next((c for c in CPU if c[0] == cid), None)
    if not row:
        return None
    rng = random.Random(_h(cid))
    st = row[4]
    lots = []
    for i in range(25):
        if rng.random() < 0.55 + st * 0.03:
            lots.append({'lot': i, 'b': STORE_KEYS[rng.randrange(len(STORE_KEYS))], 'lvl': min(10, max(1, st - 2 + rng.randrange(4)))})
    guards = [min(10, max(5, st - 1 + rng.randrange(3))) for _ in range(4 + st)]
    return {'id': cid, 'name': row[1], 'tag': row[2], 'borough': row[3], 'kind': 'cpu', 'level': st, 'lots': lots, 'guards': guards,
            'rate': sum(60 * l['lvl'] for l in lots) * (1 + st * 0.1)}


def cpu_stash(world, cid, now):
    """The stash refills from its rate since it was last hit, up to 10 hours of output."""
    t = cpu_town(cid, now)
    s = world['cpu'].setdefault(cid, {'stash': t['rate'] * 6, 'at': now})
    s['stash'] = min(t['rate'] * 10, s['stash'] + t['rate'] * max(0.0, now - s['at']) / 3600)
    s['at'] = now
    return s


# ── cartels (from FEELESS rep) ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
CARTEL_NAMES = {'bundler': ['Bundle Brothers', 'The Packing House', 'Wrapped & Rugged', 'Box Syndicate', 'Cluster Kings', 'The Batch Mob'],
                'sniper': ['Block Zero Snipers', 'First-Slot Family', 'The Front-Runners', 'Scope Gang', 'Launch Hawks', 'Millisecond Mafia'],
                'funder': ['Seed Money Mob', 'The Funders Club', 'Fresh Wallet Factory', 'Drip Feeders', 'The Faucet', 'Root Wallet Ring']}
CARTEL_ICON = {'bundler': '📦', 'sniper': '🎯', 'funder': '💸'}


def cartels(wallets, now, per_role=6, min_hits=3):
    """Cartels from the blocklist (FEELESS's own rep): wallets of one role that hit the SAME coins are one crew (union-find on shared coins).
    → [{id, name, tag, role, icon, members, hits, coins, active7d, power, level}] — the biggest crews per role. Pure."""
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    by = {}
    for w, v in (wallets or {}).items():
        ms = v.get('mints') or {}
        if len(ms) < min_hits:
            continue
        roles = {}
        for m, r in ms.items():
            roles.setdefault(r, []).append(m)
        role = max(roles, key=lambda r: len(roles[r]))
        if role not in CARTEL_NAMES:
            continue
        parent.setdefault(w, w)
        for m in roles[role]:
            k = (role, m)
            if k in by:
                union(w, by[k])
            else:
                by[k] = w
    groups = {}
    for w in parent:
        v = wallets[w]
        ms = v.get('mints') or {}
        role = max(set(ms.values()), key=lambda r: sum(1 for x in ms.values() if x == r))
        g = groups.setdefault((role, find(w)), {'role': role, 'members': 0, 'hits': 0, 'coins': set(), 'active7d': 0})
        g['members'] += 1
        g['hits'] += int(v.get('strikes') or len(ms))
        g['coins'].update(ms)
        if now - float(v.get('lastSeen') or 0) < 7 * 86400:
            g['active7d'] += 1
    out = []
    for role in CARTEL_NAMES:
        rows = sorted((g for (r, _), g in groups.items() if r == role), key=lambda g: (-g['hits'], -g['members']))[:per_role]
        for i, g in enumerate(rows):
            power = int(g['hits'] * 3 + g['members'] * 20 + g['active7d'] * 40)
            out.append({'id': f'cartel-{role}-{i + 1}', 'name': CARTEL_NAMES[role][i], 'tag': f"{role[:2].upper()}{i + 1}", 'role': role,
                        'icon': CARTEL_ICON[role], 'members': g['members'], 'hits': g['hits'], 'coins': len(g['coins']), 'active7d': g['active7d'],
                        'power': power, 'level': max(1, min(10, power // 400 + 1)), 'kind': 'cartel', 'borough': 'docks'})
    return out


def cartel_town(c):
    """A cartel's block: its level sets the stores and the guards (grows with its strikes)."""
    rng = random.Random(_h(c['id']))
    lv = int(c['level'])
    lots = [{'lot': i, 'b': STORE_KEYS[rng.randrange(len(STORE_KEYS))], 'lvl': max(1, min(10, lv + rng.randrange(-1, 2)))} for i in range(25) if rng.random() < 0.5 + lv * 0.04]
    return {**c, 'lots': lots, 'guards': [max(2, min(10, lv + rng.randrange(-1, 2))) for _ in range(3 + lv)], 'rate': sum(60 * l['lvl'] for l in lots)}


# ── blocks: home, turf, reach ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def taken(world):
    """Blocks held by anyone (families, CPU towns, cartels' docks are open to buy too — the cartels hold their own reserved blocks)."""
    t = dict(world['own'])
    for c in CPU:
        t[cpu_block(c[0])] = c[0]
    return t


def cpu_block(cid):
    """Each CPU town's reserved block: fixed, and two towns in one borough never share it."""
    row = next(c for c in CPU if c[0] == cid)
    k = [c[0] for c in CPU if c[3] == row[3]].index(cid)
    return f"{row[3]}-{(3 + 7 * k) % BLOCKS_PER}"


def ensure_home(world, cid):
    """A family's free HOME block — the first free one in its seeded borough, else anywhere."""
    if cid in world['home']:
        return world['home'][cid]
    t = taken(world)
    start = _h(cid) % 5
    for k in range(6):
        bk = BKEYS[(start + k) % 5] if k < 5 else 'docks'
        for i in range(BLOCKS_PER):
            bid = f'{bk}-{(i + _h(cid + bk)) % BLOCKS_PER}'
            if bid not in t:
                world['own'][bid] = cid
                world['home'][cid] = bid
                return bid
    raise ValueError('The city is full.')


def turf_of(world, cid):
    return sorted(b for b, o in world['own'].items() if o == cid and world['home'].get(cid) != b)


def block_price(world, cid, bid):
    return int(BLOCK_MP * tier(borough_of(bid)) * (1 + 0.6 * len(turf_of(world, cid))))


def buy_block(world, cid, bank, bid, staff=False):
    """→ cost. Raises ValueError. The bank is the caller's (it takes the MP)."""
    if borough_of(bid) not in BKEYS or bid not in block_ids(borough_of(bid)):
        raise ValueError('No such block.')
    if bid in taken(world):
        raise ValueError('That block is held — raid its owner or pick a free one.')
    if len(turf_of(world, cid)) >= TURF_MAX and not staff:
        raise ValueError(f'A family holds at most {TURF_MAX} blocks of turf.')
    cost = 0 if staff else block_price(world, cid, bid)
    if bank < cost:
        raise ValueError(f'That block costs {cost:,} MP — the bank has {int(bank):,}.')
    world['own'][bid] = cid
    return cost


def sell_block(world, cid, bid):
    if world['own'].get(bid) != cid or world['home'].get(cid) == bid:
        raise ValueError('You can only sell turf you hold (never the home block).')
    del world['own'][bid]
    return int(block_price(world, cid, bid) * 0.5 / 1.6)


def relocate(world, cid, bank, bid, gas_off=0.0, staff=False):
    if bid in taken(world):
        raise ValueError('That block is held.')
    if borough_of(bid) not in BKEYS:
        raise ValueError('No such block.')
    cost = 0 if staff else int(MOVE_MP * tier(borough_of(bid)) * (1 - gas_off))
    if bank < cost:
        raise ValueError(f'Moving costs {cost:,} MP — the bank has {int(bank):,}.')
    old = world['home'].get(cid)
    if old:
        world['own'].pop(old, None)
    world['own'][bid] = cid
    world['home'][cid] = bid
    return cost


def hops(a, b):
    """Bridges between two boroughs (BFS on BRIDGES)."""
    if a == b:
        return 0
    adj = {}
    for x, y, _ in BRIDGES:
        adj.setdefault(x, set()).add(y)
        adj.setdefault(y, set()).add(x)
    seen, front, d = {a}, [a], 0
    while front:
        d += 1
        nxt = []
        for x in front:
            for y in adj.get(x, ()):
                if y == b:
                    return d
                if y not in seen:
                    seen.add(y)
                    nxt.append(y)
        front = nxt
    return 99


def reach(world, cid, target_borough, docks_lvl=0):
    """Can this family raid in that borough? Boroughs it holds + 1 bridge (+1 per 3 docks levels)."""
    mine = {borough_of(b) for b, o in world['own'].items() if o == cid}
    lim = 1 + int(docks_lvl) // 3
    return min([hops(m, target_borough) for m in mine] or [99]) <= lim


# ── raids: a chess game on the target's block ───────────────────────────────────────────────────────────────────────────────────────────────
def board_of(target):
    """The 5×5 board: each built lot with its share of the output, and the guards placed on the richest lots."""
    lots = [dict(l) for l in target.get('lots') or [] if l.get('b')]
    tot = sum(max(1, l.get('lvl', 1)) for l in lots) or 1
    gs = sorted(target.get('guards') or [], reverse=True)
    lots.sort(key=lambda l: -l.get('lvl', 1))
    for i, l in enumerate(lots):
        l['share'] = round(max(1, l.get('lvl', 1)) / tot, 4)
        l['def'] = gs[i] if i < len(gs) else 0
        l['shield'] = 0
        l['seen'] = False
    return sorted(lots, key=lambda l: l['lot'])


def start(world, att, target, sender, rank, hitters, stash, now, rounds=2, kind='family'):
    """att/target = {'id','tag','name'}; hitters = levels of the attacker's ready hitters; stash = the target's stash now."""
    if att['id'] == target['id']:
        raise ValueError("You can't raid your own family.")
    if not hitters:
        raise ValueError('Send at least one ready hitter.')
    key = f"{att['id']}>{target['id']}"
    if now - float(world['pairCool'].get(key) or 0) < PAIR_COOL:
        raise ValueError(f"Your crew hit them {int((now - world['pairCool'][key]) // 60)} min ago — lie low for 2 hours between raids.")
    live = [r for r in world['raids'].values() if r['status'] == 'live' and r['a']['id'] == att['id']]
    if live:
        raise ValueError('Finish the raid you are in first.')
    world['n'] = int(world.get('n') or 0) + 1
    rid = f"r{world['n']}-{_h(key + str(now)) % 100000}"
    r = {'id': rid, 'a': {k: att[k] for k in ('id', 'tag', 'name')}, 'b': {k: target[k] for k in ('id', 'tag', 'name')}, 'kind': kind,
         'sender': sender, 'rank': rank, 'power': RANK_POWER.get(rank, 1), 'hitters': sorted(hitters, reverse=True)[:6],
         'stash': int(stash), 'board': board_of(target), 'round': 1, 'rounds': int(rounds), 'turn': 'a', 'moves': [],
         'loot': 0, 'locked': False, 'hurt': 0, 'status': 'live', 'at': now, 'deadline': now + RESPOND_SEC}
    world['raids'][rid] = r
    world['pairCool'][key] = now
    return r


def _rng(r):
    return random.Random(_h(f"{r['id']}:{len(r['moves'])}"))


def strength(r):
    return r['power'] * 2 + sum(r['hitters'][:3]) - 2 * r['hurt']


def odds(r, lot):
    s = max(1, strength(r))
    d = lot['def'] + lot['shield']
    return max(0.08, min(0.88, s / (s + 1.4 * d + 1)))


def _lot(r, n):
    l = next((x for x in r['board'] if x['lot'] == int(n)), None)
    if not l:
        raise ValueError('Pick a built lot on their block.')
    return l


def attack(r, action, lot, now):
    if r['status'] != 'live' or r['turn'] != 'a':
        raise ValueError('Not your move.')
    if action not in ACTIONS_A:
        raise ValueError('Pick a move.')
    word = ''
    if action == 'retreat':
        return finish(r, now, 'retreated')
    l = _lot(r, lot)
    p = odds(r, l)
    win = _rng(r).random() < p
    if action == 'hit':
        cap = int(r['stash'] * LOOT_MAX) - r['loot']
        take = max(0, min(cap, int(r['stash'] * l['share'] * 0.8))) if win else 0
        r['loot'] += take
        word = f"🔫 hit lot {l['lot'] + 1} ({l['b']}) — {'took ' + format(take, ',') + ' MP' if win else 'stopped by the guards'} ({int(p * 100)} %)"
    elif action == 'sabotage':
        if win:
            l['down'] = True
        word = f"💣 sabotage lot {l['lot'] + 1} — {'down for 2 h' if win else 'spotted and chased off'} ({int(p * 100)} %)"
    elif action == 'scout':
        for x in r['board']:
            if abs(x['lot'] - l['lot']) <= 1:
                x['seen'] = True
        win = True
        word = f"🕵 scouted lot {l['lot'] + 1} — guards on view"
    r['moves'].append({'side': 'a', 'act': action, 'lot': l['lot'], 'win': win, 'word': word, 'at': now})
    r['turn'] = 'b'
    r['deadline'] = now + (0 if r['kind'] in ('cpu', 'cartel') else RESPOND_SEC)
    return r


def best_defence(r):
    """What the house plays: lockdown when loot is big and unused, a counter when the raiders are strong, else guard the richest unshielded lot."""
    if not r['locked'] and r['loot'] >= r['stash'] * 0.15:
        return 'lockdown', None
    if strength(r) >= 14 and r['hurt'] < 2:
        return 'counter', None
    free = [x for x in r['board'] if not x['shield']]
    tgt = max(free or r['board'], key=lambda x: (x['share'], -x['def']))
    return 'guard', tgt['lot']


def defend(r, action, lot, now, auto=False):
    if r['status'] != 'live' or r['turn'] != 'b':
        raise ValueError('Not your move.')
    if action not in ACTIONS_D:
        raise ValueError('Pick a move.')
    if action == 'guard':
        l = _lot(r, lot)
        l['shield'] += 3
        word = f"🛡 guarded lot {l['lot'] + 1}"
    elif action == 'counter':
        gp = sum(sorted((x['def'] for x in r['board']), reverse=True)[:3]) + 2
        p = max(0.1, min(0.8, gp / (gp + strength(r))))
        win = _rng(r).random() < p
        if win:
            r['hurt'] += 1
            back = r['loot'] // 2
            r['loot'] -= back
        word = f"🔪 counter — {'a hitter is down, half the loot won back' if win else 'the raiders held'} ({int(p * 100)} %)"
    else:
        if r['locked']:
            raise ValueError('Lockdown already used.')
        r['locked'] = True
        r['stash'] = r['stash'] // 2
        r['loot'] = min(r['loot'], int(r['stash'] * LOOT_MAX))
        word = '🔒 lockdown — half the stash went into the bank'
    r['moves'].append({'side': 'b', 'act': action, 'lot': lot, 'word': word + (' · the house played it' if auto else ''), 'at': now})
    r['round'] += 1
    if r['round'] > r['rounds']:
        return finish(r, now, 'bell')
    r['turn'] = 'a'
    r['deadline'] = now + RESPOND_SEC
    return r


def tick(r, now):
    """A defender who doesn't answer in time (or any CPU town / cartel) gets the house's best defence; an attacker who doesn't move loses the raid's
    remaining rounds (the raid ends with what it has)."""
    if r['status'] != 'live':
        return r
    if r['turn'] == 'b' and now >= r['deadline']:
        act, lot = best_defence(r)
        return defend(r, act, lot, now, auto=True)
    if r['turn'] == 'a' and now >= r['deadline']:
        return finish(r, now, 'walked away')
    return r


def finish(r, now, why):
    r['status'] = 'done'
    r['end'] = why
    r['endAt'] = now
    mult = JUSTICE if r['kind'] == 'cartel' else 1.0
    r['paid'] = int(r['loot'] * mult)
    r['downLots'] = [x['lot'] for x in r['board'] if x.get('down')]
    return r


def raid_view(r, side):
    """What a side sees: the defender sees its guards; the attacker sees only scouted lots' guards."""
    board = [{**x, 'def': x['def'] if (side == 'b' or x['seen']) else None} for x in r['board']]
    return {**{k: v for k, v in r.items() if k != 'board'}, 'board': board, 'actions': ACTIONS_A if side == 'a' else ACTIONS_D}


# ── recruitment challenges · errands · rewards ───────────────────────────────────────────────────────────────────────────────────────────────
#            key            name                          metric      need  recruit (kind, level)  MP bonus
CHALLENGES = [('first-run', '🍕 First Delivery',          'errands',   5,  ('earner', 3),   500),
              ('streetwise', '🧭 Streetwise',               'errands',  40,  ('spy', 4),     2500),
              ('collector', '💰 The Collector',             'collects', 10,  ('guard', 4),   1500),
              ('loyal', '🔥 Seven Straight',                'streak',    7,  ('guard', 6),   5000),
              ('made-man', '🎖 Made Man',                    'raidsWon',  3,  ('hitter', 5),  3000),
              ('cpu-breaker', '🤖 Town Breaker',            'cpuWins',   1,  ('hitter', 7),  8000),
              ('justice', '⚖ Cartel Buster',                'cartelWins', 1, ('spy', 8),     10000),
              ('crew-5', '👥 Full Table',                    'members',   5,  ('earner', 6),  4000),
              ('turf-3', '🗺 Three Blocks',                  'turf',      3,  ('guard', 8),   6000),
              ('kingpin', '👑 Kingpin',                      'raidsWon', 25,  ('hitter', 10), 50000)]
ERRANDS = {'pizza': ('🍕 Slice run', 'drag the pizza to a hungry block', 300), 'gas': ('⛽ Fuel the getaway car', 'tap to pump the tank', 300),
           'laundry': ('🧺 Wash the bags', 'drag the bag into the machine', 420), 'pharma': ('💊 Pharmacy delivery', 'drag the pills to the address', 420),
           'mart': ('🏪 Restock shelves', 'tap the empty shelves', 480), 'lounge': ('🍸 Serve the VIPs', 'drag the drink to the table', 540),
           'docks': ('⚓ Unload the crates', 'drag the crates off the boat', 600), 'lab': ('🧪 Read the oracle', 'tap when the price lines up', 600),
           'casino': ('🎰 Deal a hand', 'tap to deal', 600), 'bank': ('🏦 Count the vault', 'tap the stacks', 720),
           'tower': ('🏢 Hold the meeting', 'drag the chairs to the table', 900), 'park': ('🌳 Clean the park', 'tap the litter', 300)}
REWARDS = {'rush': ('⚡ Rush hour', '×1.5 production for 1 hour', 4000), 'shield': ('🛡 Truce flag', 'no raids on your block for 2 hours', 6000),
           'title-capo': ('🎩 Title: Capo', 'a status title on your name in the family', 2500),
           'title-boss': ('👔 Title: Boss of Bosses', 'the top title', 25000), 'badge-boost': ('🏅 Badge shine', 'your family badge glows for 24 hours', 8000),
           'season': ('🏆 Season points ×500', '500 season points for the member who buys it', 12000)}
FEECAT_RATE = (1_000_000, 10_000)    # MP → FEECAT (owner can change it)


def challenge_rows(met, done):
    return [{'key': k, 'name': n, 'metric': m, 'need': need, 'have': int(met.get(m) or 0), 'recruit': {'k': rk[0], 'lvl': rk[1]}, 'mp': mp,
             'ready': int(met.get(m) or 0) >= need and k not in (done or []), 'done': k in (done or [])} for k, n, m, need, rk, mp in CHALLENGES]


def claim_challenge(key, met, done):
    row = next((c for c in challenge_rows(met, done) if c['key'] == key), None)
    if not row:
        raise ValueError('No such challenge.')
    if row['done']:
        raise ValueError('Already claimed.')
    if not row['ready']:
        raise ValueError(f"{row['name']}: {row['have']}/{row['need']} so far.")
    return row


def errand(store_lvls, member_cd, store, now, mph):
    """→ (MP, member points, next-ready time). `store_lvls` = {store: highest level}; `member_cd` = {store: last time}."""
    if store not in ERRANDS:
        raise ValueError('No such errand.')
    lv = int(store_lvls.get(store) or 0)
    if not lv:
        raise ValueError('Build that store first.')
    cd = ERRANDS[store][2]
    last = float(member_cd.get(store) or 0)
    if now - last < cd:
        raise ValueError(f"{ERRANDS[store][0]} again in {int((cd - (now - last)) // 60) + 1} min.")
    member_cd[store] = now
    mp = int(80 + float(mph) * 0.25 * lv)
    return mp, 10 + 2 * lv, now + cd


def reward(key, bank):
    if key not in REWARDS:
        raise ValueError('No such reward.')
    cost = REWARDS[key][2]
    if bank < cost:
        raise ValueError(f"{REWARDS[key][0]} costs {cost:,} MP — the bank has {int(bank):,}.")
    return cost


def redeem_feecat(mp, rate=FEECAT_RATE):
    per_mp, per_fc = rate
    if mp < per_mp:
        raise ValueError(f'Redeeming starts at {per_mp:,} MP.')
    units = int(mp // per_mp)
    return units * per_mp, units * per_fc


# 💡 ACTIVE / SHUT (owner, 2026-10-21: "buildings ACTIVE or SHUT DOWN by funding; members add to it"): every TURF block (not the home) has a
# FUND of MP that its upkeep drains by the hour. Funded = ACTIVE (lit, counts on the map); empty = SHUT (dark) until a member funds it again.
# Points today — once the custody pick lands, the same fund can be real money. A block first seen gets a grace day (nobody wakes up dark).
UPKEEP_MP = 10            # MP an hour per turf block (owner rule 'upkeepMp')
FUND_MAX_H = 24 * 14      # a fund holds at most two weeks
GRACE_H = 24
CARTEL_BLOCKS = 6         # Cartel Docks shows its six strongest cartels as buildings (it was all 16 blocks — "congested")


def fund_until(world, bid, now):
    """When this block's fund runs dry (a never-funded block gets a grace day from the first time it is seen)."""
    f = world.setdefault('funds', {})
    if bid not in f:
        f[bid] = now + GRACE_H * 3600
    return float(f[bid])


def block_state(world, cid, bid, now):
    """→ ('active' | 'shut', hours left). The home block never shuts; a block you don't hold has no state."""
    if world['home'].get(cid) == bid:
        return 'active', None
    left = (fund_until(world, bid, now) - now) / 3600
    return ('active' if left > 0 else 'shut'), max(0.0, round(left, 1))


def fund_block(world, cid, bid, mp, now, upkeep=UPKEEP_MP):
    """A member puts MP into one of the family's turf blocks → (MP taken, hours added). Never past FUND_MAX_H."""
    if taken(world).get(bid) != cid:
        raise ValueError('Hold that block first.')
    if world['home'].get(cid) == bid:
        raise ValueError('Your home block never shuts — fund your turf.')
    mp = int(mp)
    if mp < upkeep:
        raise ValueError(f'Put in at least {upkeep} MP (one hour).')
    start = max(now, fund_until(world, bid, now))
    room_h = max(0.0, (now + FUND_MAX_H * 3600 - start) / 3600)
    hours = min(mp / upkeep, room_h)
    if hours < 1:
        raise ValueError('That block is funded for two weeks already.')
    take = int(round(hours * upkeep))
    world['funds'][bid] = start + hours * 3600
    return take, round(hours, 1)


def link_block(world, cid, bid, row):
    """🏦 SET YOUR BUILDING to a real pool (owner, 2026-10-22): a block you hold wears that pool's name, kind and live APY / TVL. Display only —
    no funds move; the deposit itself happens on the pool's own page, the wallet signs. row=None clears it."""
    if taken(world).get(bid) != cid:
        raise ValueError('Hold that block first.')
    links = world.setdefault('links', {})
    if row is None:
        links.pop(bid, None)
        return None
    if len(links) > 400 and bid not in links:
        raise ValueError('Too many linked buildings right now.')
    links[bid] = {k: row[k] for k in ('pool', 'sym', 'kind', 'proto')}
    return links[bid]


def map_view(world, families, cpu_rows, cartel_rows, me=None, boom_=None, now=0):
    """The whole city for the page: every block (owner, tag, power, kind), the boroughs, bridges, season and today's boom."""
    owners = {f['id']: {'tag': f.get('tag'), 'name': f.get('name'), 'power': f.get('power', 0), 'color': f.get('color'), 'kind': 'family', 'launch': f.get('launch')} for f in families}
    for c in cpu_rows:
        owners[c['id']] = {'tag': c['tag'], 'name': c['name'], 'power': int(c['rate'] / 10), 'kind': 'cpu', 'level': c['level']}
    t = taken(world)
    blocks = []
    cartel_slots = iter(block_ids('docks'))
    cart_blocks = {}
    for c in sorted(cartel_rows or [], key=lambda x: -int(x.get('power') or 0))[:CARTEL_BLOCKS]:
        b = next(cartel_slots, None)
        if b and b not in t:
            cart_blocks[b] = c
    for bid in block_ids():
        o = t.get(bid)
        row = {'id': bid, 'b': borough_of(bid), 'i': int(bid.split('-')[1])}
        if o and o in owners:
            row.update(owner=o, **{k: v for k, v in owners[o].items() if k != 'launch'}, home=world['home'].get(o) == bid, mine=o == me)
            if owners[o]['kind'] == 'family':
                st_, left_ = block_state(world, o, bid, now) if now else ('active', None)
                row.update(state=st_, fundH=left_)
                if row['home'] and owners[o].get('launch'):
                    row['launch'] = owners[o]['launch']   # 🚀 the family's pinned launch stands as a tower on its home block
        elif bid in cart_blocks:
            c = cart_blocks[bid]
            row.update(owner=c['id'], tag=c['tag'], name=c['name'], power=c['power'], kind='cartel', role=c['role'], icon=c['icon'])
        blocks.append(row)
    return {'boroughs': [{'key': k, 'name': n, 'icon': i, 'col': c, 'row': r, 'tier': t_, 'vibe': v} for k, n, i, c, r, t_, v in BOROUGHS],
            'bridges': [{'a': a, 'b': b, 'name': n} for a, b, n in BRIDGES], 'blocks': blocks, 'season': season(now) if now else None, 'boom': boom_}


# ── owner rules (HQ › 🏙 Familia) ───────────────────────────────────────────────────────────────────────────────────────────────────────────
# LIVE = applied to the engine now (points). PLANNED = the real-money side, stored so the owner can price it, applied once custody is picked.
RULES = {'blockMp': BLOCK_MP, 'feeTier': 2.5, 'turfMax': TURF_MAX, 'moveMp': MOVE_MP, 'fuseMinMp': 2000, 'upkeepMp': UPKEEP_MP,
         'familiesPerWallet': 2, 'createUsd': 25.0, 'createFeeUsd': 5.0, 'hitRate': 0.000025, 'hitCapUsd': 0.10, 'hitMinUsd': 1.0}
RULE_RANGE = {'blockMp': (100, 1_000_000), 'feeTier': (1.0, 20.0), 'turfMax': (1, 60), 'moveMp': (0, 1_000_000), 'fuseMinMp': (0, 1_000_000), 'upkeepMp': (0, 100_000),
              'familiesPerWallet': (1, 10), 'createUsd': (0, 1000), 'createFeeUsd': (0, 1000), 'hitRate': (0, 0.01), 'hitCapUsd': (0, 100), 'hitMinUsd': (0, 1000)}
LIVE_RULES = ('blockMp', 'feeTier', 'turfMax', 'moveMp', 'fuseMinMp', 'upkeepMp', 'familiesPerWallet')


def clean_rules(raw, prev=None):
    """Owner input → rules: known keys only, each clamped to its range; the create fee never exceeds the create price."""
    out = dict(RULES, **(prev or {}))
    for k, (lo, hi) in RULE_RANGE.items():
        try:
            if k in (raw or {}):
                out[k] = max(lo, min(hi, float(raw[k])))
        except (TypeError, ValueError):
            pass
    for k in ('turfMax', 'familiesPerWallet'):
        out[k] = int(out[k])
    out['createFeeUsd'] = min(out['createFeeUsd'], out['createUsd'])
    return out


def set_rules(r):
    """Apply the LIVE rules to the engine (the service calls it under its lock before every world read / act)."""
    global BLOCK_MP, TURF_MAX, MOVE_MP, BOROUGHS
    BLOCK_MP, TURF_MAX, MOVE_MP = int(r['blockMp']), int(r['turfMax']), int(r['moveMp'])
    BOROUGHS = [b if b[0] != 'fee' else b[:5] + (float(r['feeTier']),) + b[6:] for b in BOROUGHS]


def family_fuse_ok(a_coins, b_coins, bank_mp=0, stake='paper', min_mp=2000):
    """⚔ FAMILY FUSE: cards must match (same coin count, or one apart — never 4 vs 6); an MP battle needs `min_mp` in the family bank."""
    a, b = int(a_coins), int(b_coins)
    if a < 1 or b < 1:
        return False, 'Both families need a Fuse card.'
    if abs(a - b) > 1:
        return False, f'{a} coins vs {b}: cards must have the same coin count or one apart.'
    if stake == 'mp' and bank_mp < min_mp:
        return False, f'An MP Family Fuse needs {int(min_mp):,} MP in the bank.'
    return True, ''


# ── ranked (Call-of-Duty style divisions, FEELESS names) ────────────────────────────────────────────────────────────────────────────────────
# thresholds are family POWER (family_city.power: lot levels × 10 + recruits × 2 + bank / 100)
RANKS = [('Street Rat', 0), ('Runner', 40), ('Made Man', 160), ('Capo', 500), ('Underboss', 1_200), ('Boss', 3_000), ('Kingpin', 8_000)]
TOP_TITLE, TOP_N = 'Don of Fee City', 25


def rank_of(points, place=None):
    """→ {name, div (III → I), tier index, pct to the next division}. The top 25 families by power wear 'Don of Fee City' (a CoD Top-250)."""
    p = max(0.0, float(points or 0))
    if place is not None and place <= TOP_N and p >= RANKS[-1][1]:
        return {'name': TOP_TITLE, 'div': f'#{place}', 'tier': len(RANKS), 'pct': 100}
    i = max(k for k, (_, lo) in enumerate(RANKS) if p >= lo)
    lo = RANKS[i][1]; hi = RANKS[i + 1][1] if i + 1 < len(RANKS) else lo * 2.5
    step = (hi - lo) / 3; d = min(2, int((p - lo) // step)) if step else 2
    nxt = lo + step * (d + 1)
    return {'name': RANKS[i][0], 'div': ('III', 'II', 'I')[d], 'tier': i, 'pct': int(min(100, 100 * (p - (lo + step * d)) / step)) if step else 100, 'next': int(nxt)}


# ── paid hits (PLANNED — real money waits for the custody decision; this is the math the owner tunes in HQ) ──────────────────────────────
def paid_hit_payout(stake_usd, sender_usd, target_usd, rate=0.000025, cap_usd=0.10):
    """What a WON paid hit takes from the target's family wallet: stake × rate, nudged by the size gap (punching up pays a little more,
    bullying a smaller family a lot less), never above the cap, never above 0.01 % of the target's wallet.
    Owner's anchors: $5 on a 10× bigger family ≈ $0.0001; two equal $4K families, a whole-wallet hit ≈ $0.10 at most."""
    stake, s, t = max(0.0, float(stake_usd)), max(0.01, float(sender_usd)), max(0.0, float(target_usd))
    gap = min(2.0, max(0.05, t / s)) ** 0.5
    return round(min(cap_usd, stake * rate * gap, t * 0.0001), 6)
