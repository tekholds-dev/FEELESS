"""🏙 LA FAMILIA CITY — every family's HOME BLOCK (owner, 2026-10-21: "named stores that represent crypto, unlock big stores that generate more MP,
CPU goons to protect / rob / boost … MP should grow so fast, all stores have real function … each recruit has levels"). Pure + tested; the service
holds the store and the clock. The bigger world (districts, bridges, turf, chess raids, the shop) is planned in docs/FAMILIA_PLAN.md.

MOB POINTS (MP) are points. BANK = MP the family EARNED (stores, robberies, dice) — it builds, hires and robs. GOLD = MP bought with SOL (shop,
planned) — only GOLD_WEEK_CAP of it a week may move into the bank, so time always beats money (no pay-to-win).

· A BLOCK = LOTS (5×5). The Don and the Underboss build, upgrade and hire; any member collects. Creator / HQ wallet: every unlock, every build free.
· STORES make MP an hour × level (≤ MAX_LEVEL) AND each does one real job (FUNC).
· PRODUCTION flows into the STASH (robbable) up to its cap; a member COLLECTS it into the bank. Members' verified FEELESS trades this week boost it
  (×1 … ×3). A daily collect STREAK adds up to +50 %. HOUSE_TAX of every collect goes to the FEELESS house pool (points, season prizes).
· RECRUITS (guard · hitter · earner · spy) have LEVELS 1–10: they train every hour (pizzeria + lounge speed it up) and earn XP on robberies.
  Levels are never bought. A hitter hurt in a failed hit sits out (the pharmacy heals faster).
"""
import random

LOTS = 25
MAX_LEVEL = 10
STASH_HOURS = 12
EARNER_BOOST = 0.05
PARK_BOOST = 0.03
ROB_TAKE = 0.25
ROB_COOLDOWN = 3600
START_MP = 600
HOUR = 3600
DAY = 86400
GOLD_WEEK_CAP = 3000
HOUSE_TAX = 0.05
STREAK_STEP, STREAK_MAX = 0.05, 0.50
XP_LEVEL = 100
HURT_SEC = 2 * HOUR
CASINO_EVERY, CASINO_MAX, CASINO_PAY = HOUR, 0.05, 1.9

#        key        name                     icon  cost    mp/h  unlock (metric, min)    what it is
CATALOG = {
    'pizza':   ('Pump Pizzeria',          '🍕', 150,    60, None,                 'a slice for every new launch on Pump'),
    'gas':     ('SOL Gas Station',        '⛽', 220,    75, None,                 'every trade on Solana fills up here'),
    'laundry': ('Bonk Laundromat',        '🧺', 300,    90, ('members', 2),       'the dog coins come out clean'),
    'pharma':  ('Pill Pharmacy',          '💊', 450,   120, ('members', 3),       'Pump pills, filled to order'),
    'mart':    ('Meteora Mart',           '🏪', 600,   150, ('mpEver', 3000),     'dynamic shelves, dynamic fees'),
    'lounge':  ('Raydium Lounge',         '🍸', 900,   210, ('mpEver', 8000),     'the oldest pools in town drink here'),
    'docks':   ('Orca Docks',             '⚓', 1200,  270, ('wars', 1),          'whales unload here at night'),
    'lab':     ('Pyth Oracle Lab',        '🧪', 1500,  330, ('mpEver', 20000),    'every price in the city is read here'),
    'casino':  ('Jupiter Casino',         '🎰', 2400,  480, ('raids', 3),         'every route in the city ends at the tables'),
    'bank':    ('Bonk Reserve Bank',      '🏦', 3600,  700, ('members', 5),       'where the family keeps the vault'),
    'tower':   ('Solana Tower',           '🏢', 6000, 1100, ('mpEver', 80000),    'the family HQ — the tallest thing on the block'),
    'park':    ('Fee Park',               '🌳', 400,     0, None,                 'a park the whole block breathes in'),
}
FUNC = {
    'pizza':   'trains every recruit +2 XP an hour per level',
    'gas':     'the engine of the block: +5 % to every store per level (≤ 40 %)',
    'laundry': '4 % per level of new production skips the stash straight into the bank (robbers can\'t touch it)',
    'pharma':  'hurt recruits heal 15 % per level faster',
    'mart':    '−3 % per level off building, upgrades and hires (≤ 30 %)',
    'lounge':  'trains every recruit +4 XP an hour per level',
    'docks':   'robberies take +2 % more of a stash per level (≤ 40 % total)',
    'lab':     'lets you hire spies: each spy level cuts a rival\'s guard power 5 %',
    'casino':  'once an hour a member rolls the dice: up to 5 % of the bank at 1.9× (earned MP only)',
    'bank':    'the stash holds +2 hours per level before it stops filling',
    'tower':   '+10 % to every store per level — the family\'s crown',
    'park':    f'+{int(PARK_BOOST * 100)} % to every store on the block',
}
GOONS = {'guard': ('Guard', '🛡', 180, 'protects the stash — its level is its block'),
         'hitter': ('Hitter', '🔫', 240, 'robs rival stashes — its level is its punch'),
         'earner': ('Earner', '💼', 330, f'+{int(EARNER_BOOST * 100)} % production for the whole block'),
         'spy': ('Spy', '🕵', 280, 'weakens rival guards on your robberies (needs the lab)')}
METRIC_WORD = {'members': 'members', 'wars': 'wars won', 'mpEver': 'MP made, ever', 'raids': 'robberies won'}


def blank(now):
    return {'lots': {}, 'bank': START_MP, 'gold': 0, 'stash': 0.0, 'at': now, 'mpEver': 0.0, 'crew': [], 'log': [], 'robAt': {}, 'raidsWon': 0,
            'streak': {'days': 0, 'day': None}, 'goldIn': {}, 'look': {}, 'nextId': 1}


def _migrate(c):
    """Old blocks kept goon COUNTS — they become level-1 recruits once."""
    if 'crew' not in c:
        c['crew'], c['nextId'] = [], 1
        for k, n in (c.get('goons') or {}).items():
            for _ in range(int(n or 0)):
                c['crew'].append({'id': c['nextId'], 'k': k if k in GOONS else 'guard', 'lvl': 1, 'xp': 0.0, 'hurt': 0})
                c['nextId'] += 1
        c.pop('goons', None)
    for k, v in (('gold', 0), ('raidsWon', 0), ('streak', {'days': 0, 'day': None}), ('goldIn', {}), ('look', {}), ('nextId', len(c['crew']) + 1)):
        c.setdefault(k, v)
    return c


def city_of(crew, now):
    c = crew.get('city')
    if not c:
        c = crew['city'] = blank(now)
    return _migrate(c)


def lvl_of(city, kind):
    return max([l['lvl'] for l in city['lots'].values() if l['b'] == kind] or [0])


def block_level(city):
    return 1 + sum(l['lvl'] for l in city['lots'].values()) // 6


def goon_cap(city):
    return 3 + block_level(city) * 2


def ready(city, now, kind=None):
    return [r for r in city['crew'] if r['hurt'] <= now and (kind is None or r['k'] == kind)]


def goons(city, now):
    out = {k: 0 for k in GOONS}
    for r in ready(city, now):
        out[r['k']] += 1
    return out


def stash_cap(city, rate_):
    return rate_ * (STASH_HOURS + 2 * lvl_of(city, 'bank'))


def mart_off(city):
    return min(0.30, 0.03 * lvl_of(city, 'mart'))


def streak_bonus(city):
    return min(STREAK_MAX, STREAK_STEP * int((city.get('streak') or {}).get('days') or 0))


def rate(city, boost=1.0, now=None):
    """MP an hour: stores × level, + parks, gas, tower, earners, streak, × the trading boost (×1 … ×3)."""
    t = now if now is not None else float(city.get('at') or 0)
    base = sum(CATALOG[l['b']][3] * l['lvl'] for l in city['lots'].values())
    parks = sum(1 for l in city['lots'].values() if l['b'] == 'park')
    earners = sum(1 for r in city['crew'] if r['k'] == 'earner' and r['hurt'] <= t)
    mult = (1 + parks * PARK_BOOST + min(0.40, 0.05 * lvl_of(city, 'gas')) + 0.10 * lvl_of(city, 'tower') + earners * EARNER_BOOST + streak_bonus(city))
    return base * mult * max(1.0, min(4.5, boost))


def gain_xp(r, xp):
    r['xp'] = float(r.get('xp') or 0) + xp
    while r['lvl'] < MAX_LEVEL and r['xp'] >= XP_LEVEL * r['lvl']:
        r['xp'] -= XP_LEVEL * r['lvl']
        r['lvl'] += 1
    if r['lvl'] >= MAX_LEVEL:
        r['xp'] = 0.0


def accrue(city, now, boost=1.0):
    """Production since the last read: the laundered share straight into the bank, the rest into the stash (capped); recruits train."""
    _migrate(city)
    dt = max(0.0, now - float(city.get('at') or now))
    r = rate(city, boost, now)
    made = r * dt / HOUR
    clean = made * min(0.6, 0.04 * lvl_of(city, 'laundry'))
    dirty = min(made - clean, max(0.0, stash_cap(city, r) - city['stash']))
    city['stash'] = round(city['stash'] + dirty, 2)
    city['bank'] = round(city['bank'] + clean, 2)
    city['mpEver'] = round(city.get('mpEver', 0) + dirty + clean, 2)
    if dt:
        per = 1 + 2 * lvl_of(city, 'pizza') + 4 * lvl_of(city, 'lounge')
        for rec in city['crew']:
            gain_xp(rec, per * dt / HOUR)
    city['at'] = now
    return city


def metrics(crew, city):
    return {'members': len(crew.get('members') or []), 'wars': int(crew.get('warWins') or 0), 'mpEver': int(city.get('mpEver') or 0),
            'raids': int(city.get('raidsWon') or 0)}


def unlocked(kind, met, staff=False):
    rule = CATALOG[kind][4]
    return staff or not rule or (met.get(rule[0]) or 0) >= rule[1]


def need_word(kind, met):
    rule = CATALOG[kind][4]
    return None if not rule else f"{rule[1]:,} {METRIC_WORD[rule[0]]} (now {int(met.get(rule[0]) or 0):,})"


def upgrade_cost(kind, lvl, city=None):
    return int(CATALOG[kind][2] * (1.55 ** lvl) * (1 - (mart_off(city) if city else 0)))


def build_cost(kind, city):
    return int(CATALOG[kind][2] * (1 - mart_off(city)))


def hire_cost(kind, city):
    return int(GOONS[kind][2] * (1 - mart_off(city)) * (1 + 0.08 * len(city['crew'])))


def _log(city, word, now):
    city['log'] = (city.get('log') or [])[-59:] + [[round(now), word]]


def _boss(crew, by, rank_of):
    return by == crew.get('owner') or (rank_of or {}).get(by) == 'underboss'


def _pay(city, cost, what):
    if city['bank'] < cost:
        raise ValueError(f"{what} costs {cost:,} MP — the bank has {int(city['bank']):,}.")
    city['bank'] -= cost


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
    _pay(city, 0 if staff else build_cost(kind, city), CATALOG[kind][0])
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
    _pay(city, 0 if staff else upgrade_cost(l['b'], l['lvl'], city), f"Level {l['lvl'] + 1}")
    l['lvl'] += 1
    l['at'] = now
    _log(city, f"{CATALOG[l['b']][1]} {CATALOG[l['b']][0]} → level {l['lvl']}", now)
    return city


def hire(crew, by, kind, now, staff=False, rank_of=None):
    city = city_of(crew, now)
    if not staff and not _boss(crew, by, rank_of):
        raise ValueError('Only the Don or the Underboss hires.')
    if kind not in GOONS:
        raise ValueError('Pick a recruit from the list.')
    if kind == 'spy' and not lvl_of(city, 'lab') and not staff:
        raise ValueError('Spies work out of the Pyth Oracle Lab — build it first.')
    if len(city['crew']) >= goon_cap(city) and not staff:
        raise ValueError(f"The block houses {goon_cap(city)} recruits at level {block_level(city)} — build and upgrade to house more.")
    _pay(city, 0 if staff else hire_cost(kind, city), f"A {GOONS[kind][0]}")
    city['crew'].append({'id': city['nextId'], 'k': kind, 'lvl': 1, 'xp': 0.0, 'hurt': 0})
    city['nextId'] += 1
    _log(city, f"{GOONS[kind][1]} a {GOONS[kind][0].lower()} joined the crew", now)
    return city


def collect(crew, by, now, tax=HOUSE_TAX):
    """The stash into the bank → (MP banked, MP to the FEELESS house). A collect on a new day grows the streak; a missed day resets it."""
    city = city_of(crew, now)
    if by not in (crew.get('members') or []):
        raise ValueError('Only family members collect.')
    got = int(city['stash'])
    if got < 1:
        raise ValueError('The stash is empty — come back when the stores have produced.')
    house = int(got * max(0.0, min(0.5, tax)))
    city['bank'] += got - house
    city['stash'] = round(city['stash'] - got, 2)
    s, d = city['streak'], int(now // DAY)
    if s.get('day') != d:
        s['days'] = s['days'] + 1 if s.get('day') == d - 1 else 1
        s['day'] = d
    _log(city, f"💰 {got - house:,} MP collected · streak {s['days']}d", now)
    return got - house, house


def rob_odds(attacker, defender, now=0):
    h = sum(r['lvl'] for r in ready(attacker, now, 'hitter'))
    spies = sum(r['lvl'] for r in ready(attacker, now, 'spy'))
    g = sum(r['lvl'] for r in ready(defender, now, 'guard')) * max(0.3, 1 - 0.05 * spies)
    if h <= 0:
        return 0.0
    return max(0.10, min(0.85, h / (h + 1.5 * g)))


def rob(att_crew, def_crew, by, now, staff=False, rank_of=None, rng=None):
    """A hit on another family's stash. → result dict. Raises ValueError when not allowed."""
    if att_crew['id'] == def_crew['id']:
        raise ValueError("You can't rob your own family.")
    a, d = city_of(att_crew, now), city_of(def_crew, now)
    if not staff and not _boss(att_crew, by, rank_of):
        raise ValueError('Only the Don or the Underboss sends the hitters.')
    hitters = ready(a, now, 'hitter')
    if not hitters:
        raise ValueError('Hire a hitter first (or wait for yours to heal).')
    last = float((a.get('robAt') or {}).get(def_crew['id']) or 0)
    if now - last < ROB_COOLDOWN:
        raise ValueError(f"Your hitters hit them {int((now - last) // 60)} min ago — they lie low for an hour.")
    odds = rob_odds(a, d, now)
    win = (rng or random).random() < odds
    a.setdefault('robAt', {})[def_crew['id']] = now
    tag_a, tag_d = att_crew.get('tag'), def_crew.get('tag')
    if win:
        take = int(d['stash'] * min(0.40, ROB_TAKE + 0.02 * lvl_of(a, 'docks')))
        d['stash'] = round(d['stash'] - take, 2)
        a['bank'] += take
        a['raidsWon'] = int(a.get('raidsWon') or 0) + 1
        for r in hitters:
            gain_xp(r, 25)
        _log(a, f"🔫 robbed [{tag_d}] — took {take:,} MP ({int(odds * 100)} % odds)", now)
        _log(d, f"🚨 [{tag_a}] robbed the stash — {take:,} MP gone", now)
    else:
        top = max(hitters, key=lambda r: r['lvl'])
        top['hurt'] = now + HURT_SEC * (1 - min(0.75, 0.15 * lvl_of(a, 'pharma')))
        take = 0
        for r in ready(d, now, 'guard'):
            gain_xp(r, 15)
        _log(a, f"☠ the hit on [{tag_d}] failed — a hitter is hurt ({int(odds * 100)} % odds)", now)
        _log(d, f"🛡 the guards stopped [{tag_a}]'s hitters", now)
    return {'win': win, 'take': take, 'odds': round(odds, 2)}


def casino(crew, by, stake, now, rng=None):
    """🎰 Points only, earned MP only: a member stakes ≤ 5 % of the bank once an hour; a win pays 1.9×."""
    city = city_of(crew, now)
    if by not in (crew.get('members') or []):
        raise ValueError('Only family members play the tables.')
    if not lvl_of(city, 'casino'):
        raise ValueError('Build the Jupiter Casino first.')
    last = float((city.setdefault('dice', {})).get(by) or 0)
    if now - last < CASINO_EVERY:
        raise ValueError(f"The tables let you back in {int((CASINO_EVERY - (now - last)) // 60) + 1} min.")
    stake, top = int(stake), int(city['bank'] * CASINO_MAX)
    if stake < 10 or stake > top:
        raise ValueError(f'Stake 10 … {top:,} MP (5 % of the bank).')
    city['dice'][by] = now
    win = (rng or random).random() < 0.5
    city['bank'] += int(stake * (CASINO_PAY - 1)) if win else -stake
    _log(city, f"🎰 dice: {'won' if win else 'lost'} {int(stake * (CASINO_PAY - 1)) if win else stake:,} MP", now)
    return {'win': win, 'stake': stake}


def power(city, now=0):
    return int(sum(l['lvl'] for l in city['lots'].values()) * 10 + sum(r['lvl'] for r in city['crew']) * 2 + city['bank'] / 100)


def view(crew, now, staff=False, boost=1.0, mine=False, tax=HOUSE_TAX):
    """The block as the page draws it: lots (with each store's job), rate, stash, bank, recruits with levels, catalog, power, the streak;
    the log only for the family's own members."""
    city = accrue(city_of(crew, now), now, boost)
    met = metrics(crew, city)
    r_ = rate(city, boost, now)
    lots = [{'lot': i, **({'b': l['b'], 'lvl': l['lvl'], 'at': l['at'], 'name': CATALOG[l['b']][0], 'icon': CATALOG[l['b']][1],
                           'mph': round(CATALOG[l['b']][3] * l['lvl'], 1), 'next': upgrade_cost(l['b'], l['lvl'], city) if l['lvl'] < MAX_LEVEL else None,
                           'what': CATALOG[l['b']][5], 'func': FUNC[l['b']]} if (l := city['lots'].get(str(i))) else {})} for i in range(LOTS)]
    out = {'id': crew.get('id'), 'tag': crew.get('tag'), 'name': crew.get('name'), 'lots': lots, 'rate': round(r_, 1), 'boost': round(max(1.0, min(4.5, boost)), 2),
           'stash': int(city['stash']), 'stashCap': int(stash_cap(city, r_)), 'bank': int(city['bank']), 'mpEver': int(city.get('mpEver') or 0),
           'goons': goons(city, now), 'goonCap': goon_cap(city), 'level': block_level(city), 'power': power(city, now), 'staff': bool(staff),
           'raidsWon': int(city.get('raidsWon') or 0), 'streak': int(city['streak'].get('days') or 0), 'streakBonus': round(streak_bonus(city) * 100),
           'crew': [{'id': r['id'], 'k': r['k'], 'icon': GOONS[r['k']][1], 'lvl': r['lvl'], 'xp': int(r.get('xp') or 0),
                     'next': XP_LEVEL * r['lvl'] if r['lvl'] < MAX_LEVEL else None, 'hurt': max(0, int(r['hurt'] - now)), 'special': r.get('special')} for r in city['crew']]}
    if mine:
        out['catalog'] = [{'key': k, 'name': v[0], 'icon': v[1], 'cost': 0 if staff else build_cost(k, city), 'mph': v[3], 'what': v[5], 'func': FUNC[k],
                           'ok': unlocked(k, met, staff), 'need': None if unlocked(k, met, staff) else need_word(k, met)} for k, v in CATALOG.items()]
        out['goonTypes'] = [{'key': k, 'name': v[0], 'icon': v[1], 'cost': 0 if staff else hire_cost(k, city), 'what': v[3],
                             'ok': k != 'spy' or bool(lvl_of(city, 'lab')) or staff} for k, v in GOONS.items()]
        out['log'] = [[t, w] for t, w in (city.get('log') or [])[-24:]][::-1]
        out['metrics'] = met
        out['houseTax'] = round(tax * 100, 1)
        out['casino'] = bool(lvl_of(city, 'casino'))
    return out
