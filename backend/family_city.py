"""🏙 LA FAMILIA CITY — every family builds its own block (owner, 2026-10-21: "families enter their block and build a city — named stores that
represent crypto and help with mob rank, unlock big stores that generate more MP (mob points), buy CPU goons to protect / rob / boost the family
city's production — like the Godfather on PSP; the creator wallet gets every unlock"). Pure + tested; the service holds the store and the clock.

POINTS ONLY, NEVER MONEY: MOB POINTS (MP) are made by the family's stores, are never bought, sent out or cashed out. Nothing here moves a token.

· A BLOCK = LOTS (5×5). The Don and the Underboss build, upgrade and hire; any member collects.
· STORES (CATALOG): each one represents a corner of crypto, costs MP, produces MP an hour (× its level, ≤ MAX_LEVEL) and unlocks by a TRACKED
  family number (members · wars won · MP the family has ever made). The creator / HQ wallet: every store unlocked, every build free.
· PRODUCTION flows into the STASH (uncollected) — up to STASH_HOURS of output; a member collects it into the BANK (what builds are paid from).
  Members' verified trades this week BOOST it (×1 … ×2, handed in by the service — real activity makes the city run).
· GOONS: 🛡 guard (protects the stash), 🔫 hitter (robs), 💼 earner (+EARNER_BOOST production each). Head-room by block level.
· ROBBERY: a family sends its hitters at another's stash: odds = hitters ÷ (hitters + 1.5 × their guards), clamped 10–85 %, a win takes ROB_TAKE of
  their STASH (never their bank), a loss costs one hitter. Once per target per ROB_COOLDOWN. Every move is logged for both families.
· CITY POWER = total store levels × 10 + goons + bank ÷ 100 → the family's mob rank (board, map heights).
"""
import random

LOTS = 25
MAX_LEVEL = 5
STASH_HOURS = 12
EARNER_BOOST = 0.04
ROB_TAKE = 0.25
ROB_COOLDOWN = 3600
START_MP = 300
HOUR = 3600

#        key        name                     icon  cost   mp/h  unlock (metric, min)   what it is
CATALOG = {
    'pizza':   ('Pump Pizzeria',          '🍕', 100,   12, None,               'a slice for every new launch on Pump'),
    'gas':     ('SOL Gas Station',        '⛽', 150,   15, None,               'every trade on Solana fills up here'),
    'laundry': ('Bonk Laundromat',        '🧺', 200,   18, ('members', 2),     'the dog coins come out clean'),
    'pharma':  ('Pill Pharmacy',          '💊', 300,   24, ('members', 3),     'Pump pills, filled to order'),
    'mart':    ('Meteora Mart',           '🏪', 400,   30, ('mpEver', 1000),   'dynamic shelves, dynamic fees'),
    'lounge':  ('Raydium Lounge',         '🍸', 600,   42, ('mpEver', 2500),   'the oldest pools in town drink here'),
    'docks':   ('Orca Docks',             '⚓', 800,   54, ('wars', 1),        'whales unload here at night'),
    'lab':     ('Pyth Oracle Lab',        '🧪', 1000,  66, ('mpEver', 6000),   'every price in the city is read here'),
    'casino':  ('Jupiter Casino',         '🎰', 1600,  96, ('wars', 3),        'every route in the city ends at the tables'),
    'bank':    ('Bonk Reserve Bank',      '🏦', 2400,  140, ('members', 5),    'where the family keeps the vault'),
    'tower':   ('Solana Tower',           '🏢', 4000,  220, ('mpEver', 25000), 'the family HQ — the tallest thing on the block'),
    'park':    ('Fee Park',               '🌳', 250,   0, None,               'a park: +2 % to every store on the block'),
}
PARK_BOOST = 0.02
GOONS = {'guard': ('Guard', '🛡', 120, 'protects the stash from robbers'),
         'hitter': ('Hitter', '🔫', 160, 'robs another family\'s stash'),
         'earner': ('Earner', '💼', 220, f'+{int(EARNER_BOOST * 100)} % production for the whole block')}
METRIC_WORD = {'members': 'members', 'wars': 'wars won', 'mpEver': 'MP made, ever'}


def blank(now):
    return {'lots': {}, 'bank': START_MP, 'stash': 0.0, 'at': now, 'mpEver': 0.0, 'goons': {'guard': 0, 'hitter': 0, 'earner': 0}, 'log': [], 'robAt': {}}


def city_of(crew, now):
    c = crew.get('city')
    if not c:
        c = crew['city'] = blank(now)
    return c


def block_level(city):
    return 1 + sum(l['lvl'] for l in city['lots'].values()) // 6


def goon_cap(city):
    return 2 + block_level(city) * 2


def rate(city, boost=1.0):
    """MP an hour: every store × its level, + parks, + earners, × the trading boost."""
    base = sum(CATALOG[l['b']][3] * l['lvl'] for l in city['lots'].values())
    parks = sum(1 for l in city['lots'].values() if l['b'] == 'park')
    mult = (1 + parks * PARK_BOOST + city['goons'].get('earner', 0) * EARNER_BOOST) * max(1.0, min(2.0, boost))
    return base * mult


def accrue(city, now, boost=1.0):
    """Production since the last read flows into the stash (capped at STASH_HOURS of output)."""
    dt = max(0.0, now - float(city.get('at') or now))
    r = rate(city, boost)
    cap = r * STASH_HOURS
    add = min(r * dt / HOUR, max(0.0, cap - city['stash']))
    city['stash'] = round(city['stash'] + add, 2)
    city['mpEver'] = round(city.get('mpEver', 0) + add, 2)
    city['at'] = now
    return city


def metrics(crew, city):
    return {'members': len(crew.get('members') or []), 'wars': int(crew.get('warWins') or 0), 'mpEver': int(city.get('mpEver') or 0)}


def unlocked(kind, met, staff=False):
    if staff:
        return True
    rule = CATALOG[kind][4]
    return not rule or (met.get(rule[0]) or 0) >= rule[1]


def need_word(kind, met):
    rule = CATALOG[kind][4]
    if not rule:
        return None
    return f"{rule[1]:,} {METRIC_WORD[rule[0]]} (now {int(met.get(rule[0]) or 0):,})"


def upgrade_cost(kind, lvl):
    return int(CATALOG[kind][2] * (1.6 ** lvl))


def _log(city, word, now):
    city['log'] = (city.get('log') or [])[-39:] + [[round(now), word]]


def _boss(crew, by, rank_of):
    if by == crew.get('owner'):
        return True
    return (rank_of or {}).get(by) == 'underboss'


def build(crew, by, lot, kind, now, staff=False, rank_of=None):
    city = city_of(crew, now)
    if by not in (crew.get('members') or []) and not staff:
        raise ValueError('Only family members build here.')
    if not staff and not _boss(crew, by, rank_of):
        raise ValueError('Only the Don or the Underboss builds.')
    lot = int(lot)
    if not 0 <= lot < LOTS:
        raise ValueError('That lot is off the block.')
    if kind not in CATALOG:
        raise ValueError('Pick a store from the list.')
    if str(lot) in city['lots']:
        raise ValueError('That lot is taken — upgrade it instead.')
    met = metrics(crew, city)
    if not unlocked(kind, met, staff):
        raise ValueError(f"{CATALOG[kind][0]} unlocks at {need_word(kind, met)}.")
    cost = 0 if staff else CATALOG[kind][2]
    if city['bank'] < cost:
        raise ValueError(f"{CATALOG[kind][0]} costs {cost:,} MP — the bank has {int(city['bank']):,}.")
    city['bank'] -= cost
    city['lots'][str(lot)] = {'b': kind, 'lvl': 1, 'at': now}
    _log(city, f"{CATALOG[kind][1]} {CATALOG[kind][0]} built on lot {lot + 1}", now)
    return city


def upgrade(crew, by, lot, now, staff=False, rank_of=None):
    city = city_of(crew, now)
    if not staff and not _boss(crew, by, rank_of):
        raise ValueError('Only the Don or the Underboss upgrades.')
    l = city['lots'].get(str(int(lot)))
    if not l:
        raise ValueError('Nothing is built on that lot.')
    if l['lvl'] >= MAX_LEVEL:
        raise ValueError('That store is at its top level.')
    cost = 0 if staff else upgrade_cost(l['b'], l['lvl'])
    if city['bank'] < cost:
        raise ValueError(f"Level {l['lvl'] + 1} costs {cost:,} MP — the bank has {int(city['bank']):,}.")
    city['bank'] -= cost
    l['lvl'] += 1
    l['at'] = now
    _log(city, f"{CATALOG[l['b']][1]} {CATALOG[l['b']][0]} → level {l['lvl']}", now)
    return city


def hire(crew, by, kind, now, staff=False, rank_of=None):
    city = city_of(crew, now)
    if not staff and not _boss(crew, by, rank_of):
        raise ValueError('Only the Don or the Underboss hires.')
    if kind not in GOONS:
        raise ValueError('Pick a goon from the list.')
    if sum(city['goons'].values()) >= goon_cap(city) and not staff:
        raise ValueError(f"The block holds {goon_cap(city)} goons at level {block_level(city)} — build and upgrade to house more.")
    cost = 0 if staff else GOONS[kind][2]
    if city['bank'] < cost:
        raise ValueError(f"A {GOONS[kind][0]} costs {cost} MP — the bank has {int(city['bank']):,}.")
    city['bank'] -= cost
    city['goons'][kind] = city['goons'].get(kind, 0) + 1
    _log(city, f"{GOONS[kind][1]} a {GOONS[kind][0].lower()} joined the crew", now)
    return city


def collect(crew, by, now):
    city = city_of(crew, now)
    if by not in (crew.get('members') or []):
        raise ValueError('Only family members collect.')
    got = int(city['stash'])
    if got < 1:
        raise ValueError('The stash is empty — come back when the stores have produced.')
    city['bank'] += got
    city['stash'] = round(city['stash'] - got, 2)
    _log(city, f"💰 {got:,} MP collected from the stash", now)
    return got


def rob_odds(attacker, defender):
    h, g = attacker['goons'].get('hitter', 0), defender['goons'].get('guard', 0)
    if h <= 0:
        return 0.0
    return max(0.10, min(0.85, h / (h + 1.5 * g)))


def rob(att_crew, def_crew, by, now, staff=False, rank_of=None, rng=None):
    """Send the hitters at another family's stash. → result dict. Raises ValueError when not allowed."""
    if att_crew['id'] == def_crew['id']:
        raise ValueError("You can't rob your own family.")
    a, d = city_of(att_crew, now), city_of(def_crew, now)
    if not staff and not _boss(att_crew, by, rank_of):
        raise ValueError('Only the Don or the Underboss sends the hitters.')
    if a['goons'].get('hitter', 0) <= 0:
        raise ValueError('Hire a hitter first.')
    last = float((a.get('robAt') or {}).get(def_crew['id']) or 0)
    if now - last < ROB_COOLDOWN:
        raise ValueError(f"Your hitters hit them {int((now - last) // 60)} min ago — they lie low for an hour.")
    odds = rob_odds(a, d)
    win = (rng or random).random() < odds
    a.setdefault('robAt', {})[def_crew['id']] = now
    tag_a, tag_d = att_crew.get('tag'), def_crew.get('tag')
    if win:
        take = int(d['stash'] * ROB_TAKE)
        d['stash'] = round(d['stash'] - take, 2)
        a['bank'] += take
        _log(a, f"🔫 robbed [{tag_d}] — took {take:,} MP ({int(odds * 100)} % odds)", now)
        _log(d, f"🚨 [{tag_a}] robbed the stash — {take:,} MP gone", now)
    else:
        a['goons']['hitter'] -= 1
        take = 0
        _log(a, f"☠ the hit on [{tag_d}] failed — one hitter lost ({int(odds * 100)} % odds)", now)
        _log(d, f"🛡 the guards stopped [{tag_a}]'s hitters", now)
    return {'win': win, 'take': take, 'odds': round(odds, 2)}


def power(city):
    return int(sum(l['lvl'] for l in city['lots'].values()) * 10 + sum(city['goons'].values()) + city['bank'] / 100)


def view(crew, now, staff=False, boost=1.0, mine=False):
    """The block as the page draws it: lots, rate, stash, bank, goons, catalog with locks + costs, power, the log (the family's own only)."""
    city = accrue(city_of(crew, now), now, boost)
    met = metrics(crew, city)
    lots = [{'lot': i, **({'b': l['b'], 'lvl': l['lvl'], 'at': l['at'], 'name': CATALOG[l['b']][0], 'icon': CATALOG[l['b']][1],
                           'mph': round(CATALOG[l['b']][3] * l['lvl'], 1), 'next': upgrade_cost(l['b'], l['lvl']) if l['lvl'] < MAX_LEVEL else None,
                           'what': CATALOG[l['b']][5]} if (l := city['lots'].get(str(i))) else {})} for i in range(LOTS)]
    out = {'id': crew.get('id'), 'tag': crew.get('tag'), 'name': crew.get('name'), 'lots': lots, 'rate': round(rate(city, boost), 1), 'boost': round(max(1.0, min(2.0, boost)), 2),
           'stash': int(city['stash']), 'stashCap': int(rate(city, boost) * STASH_HOURS), 'bank': int(city['bank']), 'mpEver': int(city.get('mpEver') or 0),
           'goons': dict(city['goons']), 'goonCap': goon_cap(city), 'level': block_level(city), 'power': power(city), 'staff': bool(staff)}
    if mine:
        out['catalog'] = [{'key': k, 'name': v[0], 'icon': v[1], 'cost': 0 if staff else v[2], 'mph': v[3], 'what': v[5], 'ok': unlocked(k, met, staff),
                           'need': None if unlocked(k, met, staff) else need_word(k, met)} for k, v in CATALOG.items()]
        out['goonTypes'] = [{'key': k, 'name': v[0], 'icon': v[1], 'cost': 0 if staff else v[2], 'what': v[3]} for k, v in GOONS.items()]
        out['log'] = [[t, w] for t, w in (city.get('log') or [])[-16:]][::-1]
        out['metrics'] = met
    return out
