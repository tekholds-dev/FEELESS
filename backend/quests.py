"""FEELESS quest engine: 40 animated badges (FEELESS set + Fee Reserve/FRSV set), each earned by tasks.

Pure functions, no I/O. Every metric is computed from data FEELESS already records (verified trades, chat, calls,
invites, follows, points, check-ins, $FEE held), so a badge can never be claimed without the activity behind it.
Admins edit any badge (name, tier, tasks, targets, on/off) and grant/revoke by hand in the Command Center;
those edits are `overrides` merged over DEFAULTS here.
"""
import math
import time

DAY = 86400
TIER_XP = {'common': 50, 'rare': 150, 'epic': 400, 'legendary': 1000, 'mythic': 2500}
LEVELS = [(0, 'Rookie'), (300, 'Degen'), (1200, 'Ape'), (3500, 'Chad'), (8000, 'Whale'), (16000, 'Legend'), (30000, 'Fee God')]
FOUNDER_CUTOFF = 1798761600  # 2027-01-01 UTC: wallets active before this can still earn Founder

# metric -> human label (shown next to every task; also the list admins pick from)
METRICS = {
    'signin_days': 'days checked in', 'streak': 'day check-in streak', 'trades': 'trades', 'volume_usd': '$ traded',
    'buys': 'buys', 'coins_traded': 'different coins traded', 'fee_buys': '$FEE buys', 'fee_usd': '$ of $FEE held',
    'diamond_days': 'days holding $FEE without selling', 'chat_msgs': 'chat messages', 'chat_rooms': 'chat rooms joined',
    'chat_chains': 'chains you chatted on', 'calls': 'coin calls', 'call_hits': 'calls that ran', 'invited': 'friends invited',
    'followers': 'followers', 'launches': 'coins launched', 'points': 'season points', 'account_days': 'days since your first visit',
    'early': 'joined before 2027', 'badges': 'badges earned',
    'cases_opened': 'case files opened', 'warroom_trades': 'trades from a war room', 'alerts_set': 'price / Dip-Rip alerts set',
}


def _t(metric, target, label=None):
    return {'metric': metric, 'target': target, 'label': label or f"{target:,} {METRICS[metric]}"}


# (id, name, tier, tasks) — FEELESS set: open to everyone, earned by what you do here.
FEELESS = [
    ('recruit', 'Recruit', 'common', [_t('signin_days', 1, 'Check in once'), _t('trades', 1, 'Make your first trade'), _t('chat_msgs', 1, 'Say gm in any chat')]),
    ('trader', 'Trader', 'common', [_t('trades', 10), _t('coins_traded', 3)]),
    ('supporter', 'Supporter', 'common', [_t('fee_buys', 1, 'Buy $FEE once'), _t('fee_usd', 5, 'Hold $5 of $FEE')]),
    ('pro', 'Pro', 'rare', [_t('trades', 50), _t('volume_usd', 1000)]),
    ('vip', 'VIP', 'rare', [_t('fee_usd', 100, 'Hold $100 of $FEE')]),
    ('hodler', 'Hodler', 'rare', [_t('diamond_days', 7)]),
    ('lp_provider', 'LP Provider', 'rare', [_t('fee_buys', 5, 'Feed the $FEE pool 5 times')]),
    ('community', 'Community', 'rare', [_t('chat_msgs', 100), _t('chat_rooms', 5)]),
    ('ambassador', 'Ambassador', 'rare', [_t('invited', 5)]),
    ('global', 'Global', 'rare', [_t('chat_chains', 3), _t('warroom_trades', 3)]),
    ('analyst', 'Analyst', 'rare', [_t('calls', 5), _t('cases_opened', 10)]),
    ('gamer', 'Gamer', 'rare', [_t('points', 1000), _t('streak', 7)]),
    ('launch', 'Launch', 'rare', [_t('launches', 1, 'Launch a coin on FEELESS')]),
    ('alpha', 'Alpha', 'epic', [_t('calls', 10), _t('call_hits', 3), _t('alerts_set', 3)]),
    ('elite', 'Elite', 'epic', [_t('volume_usd', 10000), _t('streak', 7)]),
    ('diamond_hands', 'Diamond Hands', 'epic', [_t('diamond_days', 30), _t('fee_usd', 25, 'Hold $25 of $FEE')]),
    ('creator', 'Creator', 'epic', [_t('launches', 3), _t('followers', 10)]),
    ('treasure_hunter', 'Treasure Hunter', 'epic', [_t('coins_traded', 25)]),
    ('legend', 'Legend', 'mythic', [_t('badges', 15, 'Earn 15 FEELESS badges'), _t('volume_usd', 50000)]),
    ('founder', 'Founder', 'mythic', [_t('early', 1, 'Be here before 2027'), _t('account_days', 30), _t('trades', 25)]),
]

# Fee Reserve (FRSV) set: the holder tier. Same 20 badges, harder tasks, and every one needs $FEE held.
FRSV = [
    ('recruit', 'FRSV Recruit', 'rare', [_t('fee_usd', 100, 'Hold $100 of $FEE (Reserve entry)'), _t('signin_days', 3)]),
    ('trader', 'FRSV Trader', 'rare', [_t('fee_usd', 100, 'Hold $100 of $FEE'), _t('trades', 100)]),
    ('supporter', 'FRSV Supporter', 'rare', [_t('fee_usd', 250, 'Hold $250 of $FEE'), _t('fee_buys', 10)]),
    ('pro', 'FRSV Pro', 'epic', [_t('fee_usd', 500, 'Hold $500 of $FEE'), _t('volume_usd', 25000)]),
    ('vip', 'FRSV VIP', 'legendary', [_t('fee_usd', 1000, 'Hold $1,000 of $FEE')]),
    ('hodler', 'FRSV Hodler', 'epic', [_t('fee_usd', 250, 'Hold $250 of $FEE'), _t('diamond_days', 30)]),
    ('lp_provider', 'FRSV LP Provider', 'epic', [_t('fee_usd', 500, 'Hold $500 of $FEE'), _t('fee_buys', 25)]),
    ('community', 'FRSV Community', 'epic', [_t('fee_usd', 100, 'Hold $100 of $FEE'), _t('chat_msgs', 1000), _t('chat_rooms', 20)]),
    ('ambassador', 'FRSV Ambassador', 'epic', [_t('fee_usd', 100, 'Hold $100 of $FEE'), _t('invited', 25)]),
    ('global', 'FRSV Global', 'epic', [_t('fee_usd', 100, 'Hold $100 of $FEE'), _t('chat_chains', 8), _t('warroom_trades', 25)]),
    ('analyst', 'FRSV Analyst', 'epic', [_t('fee_usd', 100, 'Hold $100 of $FEE'), _t('calls', 50), _t('call_hits', 10), _t('cases_opened', 100)]),
    ('gamer', 'FRSV Gamer', 'epic', [_t('fee_usd', 100, 'Hold $100 of $FEE'), _t('points', 10000), _t('streak', 30)]),
    ('launch', 'FRSV Launch', 'epic', [_t('fee_usd', 250, 'Hold $250 of $FEE'), _t('launches', 3)]),
    ('alpha', 'FRSV Alpha', 'legendary', [_t('fee_usd', 1000, 'Hold $1,000 of $FEE'), _t('call_hits', 25)]),
    ('elite', 'FRSV Elite', 'legendary', [_t('fee_usd', 10000, 'Hold $10,000 of $FEE'), _t('volume_usd', 100000)]),
    ('diamond_hands', 'FRSV Diamond Hands', 'legendary', [_t('fee_usd', 1000, 'Hold $1,000 of $FEE'), _t('diamond_days', 90)]),
    ('creator', 'FRSV Creator', 'legendary', [_t('fee_usd', 1000, 'Hold $1,000 of $FEE'), _t('launches', 10), _t('followers', 100)]),
    ('treasure_hunter', 'FRSV Treasure Hunter', 'legendary', [_t('fee_usd', 500, 'Hold $500 of $FEE'), _t('coins_traded', 100)]),
    ('legend', 'FRSV Legend', 'mythic', [_t('fee_usd', 100000, 'Hold $100,000 of $FEE'), _t('badges', 30, 'Earn 30 badges')]),
    ('founder', 'FRSV Founder', 'mythic', [_t('early', 1, 'Be here before 2027'), _t('fee_usd', 1000, 'Hold $1,000 of $FEE'), _t('account_days', 60)]),
]


# Badge perks (admin-editable per badge): a FEELESS fee discount (the best one applies, shown on the quote, capped with
# holder tiers at 90%) and chat backgrounds. Earned badges are real utility, not just art.
PERKS = {
    'q-supporter': [{'kind': 'chat_bg', 'id': 'aurora'}], 'q-community': [{'kind': 'chat_bg', 'id': 'stars'}],
    'q-gamer': [{'kind': 'chat_bg', 'id': 'grid'}], 'q-hodler': [{'kind': 'chat_bg', 'id': 'pulse'}],
    'q-diamond_hands': [{'kind': 'fee_discount', 'pct': 5}], 'q-elite': [{'kind': 'chat_bg', 'id': 'warp'}, {'kind': 'fee_discount', 'pct': 5}],
    'q-legend': [{'kind': 'fee_discount', 'pct': 10}], 'q-founder': [{'kind': 'chat_bg', 'id': 'matrix'}],
    'frsv-vip': [{'kind': 'chat_bg', 'id': 'vortex'}], 'frsv-diamond_hands': [{'kind': 'fee_discount', 'pct': 15}, {'kind': 'chat_bg', 'id': 'lava'}],
    'frsv-elite': [{'kind': 'chat_bg', 'id': 'gold'}, {'kind': 'fee_discount', 'pct': 15}], 'frsv-legend': [{'kind': 'fee_discount', 'pct': 25}],
}


def perks_of(badges):
    """What your earned badges unlock: best fee discount (%), chat backgrounds, rings."""
    out = {'feeDiscountPct': 0, 'chatBgs': [], 'rings': [], 'from': {}}
    for b in badges:
        if not b.get('earned'):
            continue
        for p in b.get('perks') or []:
            if p.get('kind') == 'fee_discount' and float(p.get('pct') or 0) > out['feeDiscountPct']:
                out['feeDiscountPct'] = min(50.0, float(p['pct'])); out['from']['fee'] = b['name']
            elif p.get('kind') == 'chat_bg' and p.get('id') not in out['chatBgs']:
                out['chatBgs'].append(p['id'])
            elif p.get('kind') == 'ring' and p.get('id') not in out['rings']:
                out['rings'].append(p['id'])
    return out


def _defs(set_id, rows):
    art = 'feeless' if set_id == 'feeless' else 'frsv'
    return [{'id': f'{"q" if set_id == "feeless" else "frsv"}-{bid}', 'set': set_id, 'name': name, 'tier': tier, 'enabled': True,
             'art': f'/assets/badges/{art}/{bid}', 'tasks': [{**t, 'id': f'{bid}-{i}'} for i, t in enumerate(tasks)],
             'perks': PERKS.get(f'{"q" if set_id == "feeless" else "frsv"}-{bid}', [])}
            for bid, name, tier, tasks in rows]


DEFAULTS = _defs('feeless', FEELESS) + _defs('frsv', FRSV)

# Daily + weekly quests (UTC). Derived from timestamps, so nothing to "claim" — they tick as you play.
DAILY = [('checkin', 'Check in', 'signin', 1, 10), ('trade', 'Make a trade', 'trades', 1, 15), ('chat', 'Post in any chat', 'chat_msgs', 1, 10),
         ('volume', 'Trade $50', 'volume_usd', 50, 20), ('call', 'Call a coin', 'calls', 1, 15), ('case', 'Open a case file', 'case_open', 1, 10)]
WEEKLY = [('checkins', 'Check in 5 days', 'signin', 5, 60), ('trades', '10 trades', 'trades', 10, 80), ('volume', 'Trade $500', 'volume_usd', 500, 120),
          ('rooms', 'Chat in 3 rooms', 'chat_rooms', 3, 50), ('warroom', 'Trade from a war room', 'warroom_trade', 1, 70), ('cases', 'Open 5 case files', 'case_open', 5, 40)]


def merge(defaults, overrides):
    """Admin edits (Command Center) over the defaults. Unknown ids in overrides are admin-made badges."""
    ov = (overrides or {}).get('badges') or {}
    out = []
    for d in defaults:
        o = ov.get(d['id']) or {}
        out.append({**d, **{k: v for k, v in o.items() if k in ('name', 'tier', 'enabled', 'tasks', 'art', 'perks')}})
    for bid, o in ov.items():
        if not any(d['id'] == bid for d in defaults) and o.get('tasks'):
            out.append({'id': bid, 'set': o.get('set', 'feeless'), 'name': o.get('name', bid), 'tier': o.get('tier', 'rare'),
                        'enabled': o.get('enabled', True), 'art': o.get('art', ''), 'tasks': o['tasks'], 'perks': o.get('perks') or []})
    return out


def metrics(raw, now=None):
    """raw: trades [{side, usd, token, ts}], chat [{room, chain, ts}], call_ts [ts], call_hits int, invited int, followers int,
    launches int, points int, signin_days [YYYY-MM-DD], streak int, fee_usd float, fee_mints set, first_seen float."""
    now = now or time.time()
    trades = raw.get('trades') or []; chat = raw.get('chat') or []
    fee_mints = set(raw.get('fee_mints') or [])
    fee_trades = sorted((t for t in trades if t.get('token') in fee_mints), key=lambda t: t.get('ts') or 0)
    last_sell = max((t.get('ts') or 0 for t in fee_trades if t.get('side') == 'sell'), default=0)
    first_buy_after = min((t.get('ts') or 0 for t in fee_trades if t.get('side') == 'buy' and (t.get('ts') or 0) > last_sell), default=0)
    diamond = int((now - first_buy_after) // DAY) if first_buy_after and (raw.get('fee_usd') or 0) > 0 else 0
    first = raw.get('first_seen') or min([t.get('ts') or now for t in trades] + [m.get('ts') or now for m in chat] + [now])
    return {
        'signin_days': len(set(raw.get('signin_days') or [])), 'streak': int(raw.get('streak') or 0),
        'trades': len(trades), 'volume_usd': round(sum(float(t.get('usd') or 0) for t in trades), 2),
        'buys': sum(1 for t in trades if t.get('side') == 'buy'), 'coins_traded': len({t.get('token') for t in trades if t.get('token')}),
        'fee_buys': sum(1 for t in fee_trades if t.get('side') == 'buy'), 'fee_usd': round(float(raw.get('fee_usd') or 0), 2),
        'diamond_days': diamond, 'chat_msgs': len(chat), 'chat_rooms': len({m.get('room') for m in chat}),
        'chat_chains': len({m.get('chain') for m in chat if m.get('chain')}), 'calls': len(raw.get('call_ts') or []),
        'call_hits': int(raw.get('call_hits') or 0), 'invited': int(raw.get('invited') or 0), 'followers': int(raw.get('followers') or 0),
        'launches': int(raw.get('launches') or 0), 'points': int(raw.get('points') or 0),
        'account_days': int((now - first) // DAY), 'early': 1 if first < FOUNDER_CUTOFF else 0,
        'cases_opened': len((raw.get('events') or {}).get('case_open') or []), 'warroom_trades': len((raw.get('events') or {}).get('warroom_trade') or []),
        'alerts_set': int(raw.get('alerts_set') or 0),
    }


def _progress(task, m):
    have = m.get(task['metric'], 0); target = task['target'] or 1
    return {**task, 'have': have, 'done': have >= target, 'pct': min(100, round(have / target * 100))}


def evaluate(defs, m, manual=None):
    """Badge list with per-task progress. `badges` metric (Legend) counts earned badges of the same set first."""
    manual = manual or {}
    grant, revoke = set(manual.get('grant') or []), set(manual.get('revoke') or [])
    live = [d for d in defs if d.get('enabled', True)]
    out = []
    for phase in (0, 1):   # pass 0: badges without the 'badges' metric; pass 1: the ones that count earned badges
        for d in live:
            needs_count = any(t['metric'] == 'badges' for t in d['tasks'])
            if needs_count != bool(phase):
                continue
            earned_so_far = sum(1 for b in out if b['earned'] and (b['set'] == d['set'] or d['set'] == 'frsv'))
            mm = {**m, 'badges': earned_so_far}
            tasks = [_progress(t, mm) for t in d['tasks']]
            done = all(t['done'] for t in tasks)
            earned = (done or d['id'] in grant) and d['id'] not in revoke
            out.append({**d, 'tasks': tasks, 'earned': earned, 'granted': d['id'] in grant and not done,
                        'pct': round(sum(t['pct'] for t in tasks) / max(1, len(tasks))), 'xp': TIER_XP.get(d['tier'], 100)})
    order = {d['id']: i for i, d in enumerate(defs)}
    return sorted(out, key=lambda b: order.get(b['id'], 999))


def _window(raw, since, until=float('inf')):
    trades = [t for t in raw.get('trades') or [] if since <= (t.get('ts') or 0) < until]
    chat = [c for c in raw.get('chat') or [] if since <= (c.get('ts') or 0) < until]
    day0 = time.strftime('%Y-%m-%d', time.gmtime(since))
    day1 = time.strftime('%Y-%m-%d', time.gmtime(until)) if until != float('inf') else '9999'
    return {'signin': sum(1 for d in set(raw.get('signin_days') or []) if day0 <= d < day1), 'trades': len(trades),
            'volume_usd': round(sum(float(t.get('usd') or 0) for t in trades), 2), 'chat_msgs': len(chat),
            'chat_rooms': len({c.get('room') for c in chat}), 'calls': sum(1 for x in raw.get('call_ts') or [] if since <= x < until),
            **{k: sum(1 for x in v if since <= x < until) for k, v in (raw.get('events') or {}).items()}}


def quests(raw, now=None):
    now = now or time.time()
    day_start = now // DAY * DAY
    week_start = day_start - ((time.gmtime(now).tm_wday) * DAY)   # Monday 00:00 UTC
    def run(rows, since, resets):
        w = _window(raw, since)
        return {'resetsAt': resets, 'tasks': [{'id': i, 'label': label, 'have': w.get(metric, 0), 'target': target, 'xp': xp,
                                               'done': w.get(metric, 0) >= target} for i, label, metric, target, xp in rows]}
    return {'daily': run(DAILY, day_start, day_start + DAY), 'weekly': run(WEEKLY, week_start, week_start + 7 * DAY)}


def level(xp):
    lvl, name, nxt = 1, LEVELS[0][1], None
    for i, (need, label) in enumerate(LEVELS):
        if xp >= need:
            lvl, name = i + 1, label
            nxt = LEVELS[i + 1][0] if i + 1 < len(LEVELS) else None
    return {'level': lvl, 'name': name, 'xp': xp, 'next': nxt}


def summary(defs, raw, manual=None, now=None):
    m = metrics(raw, now)
    badges = evaluate(defs, m, manual)
    q = quests(raw, now)
    xp = sum(b['xp'] for b in badges if b['earned']) + sum(t['xp'] for t in q['daily']['tasks'] + q['weekly']['tasks'] if t['done'])
    # "Next up": the three unearned badges you're closest to — the hook that keeps people coming back.
    nxt = sorted((b for b in badges if not b['earned']), key=lambda b: -b['pct'])[:3]
    return {'metrics': m, 'badges': badges, 'quests': q, 'level': level(xp), 'next': [b['id'] for b in nxt], 'perks': perks_of(badges),
            'earned': sum(1 for b in badges if b['earned']), 'total': len(badges)}


def rarity(holders, wallets):
    """% of active wallets holding each badge (shown on every badge: 'held by 3.2%')."""
    return {bid: round(n / wallets * 100, 1) if wallets else 0.0 for bid, n in holders.items()}


def is_valid_def(d):
    return bool(d.get('name')) and isinstance(d.get('tasks'), list) and d['tasks'] and all(
        t.get('metric') in METRICS and isinstance(t.get('target'), (int, float)) and t['target'] > 0 and math.isfinite(t['target']) for t in d['tasks'])


def season_score(badges, raw, earned_at, season, now=None):
    """Season XP: badges earned inside the season + every daily/weekly quest finished inside it. A paused or
    not-started season scores 0 (XP still counts toward your level)."""
    now = now or time.time()
    start = float((season or {}).get('start') or 0)
    if not season or season.get('paused') or not start or now < start:
        return 0
    xp = sum(b['xp'] for b in badges if b.get('earned') and start <= float((earned_at or {}).get(b['id']) or 0) <= now)
    day = start // DAY * DAY
    while day < now and day < start + 200 * DAY:
        w = _window(raw, day, day + DAY)
        xp += sum(q[4] for q in DAILY if w.get(q[2], 0) >= q[3])
        day += DAY
    week = start // DAY * DAY - time.gmtime(start).tm_wday * DAY
    while week < now and week < start + 30 * 7 * DAY:
        w = _window(raw, week, week + 7 * DAY)
        xp += sum(q[4] for q in WEEKLY if w.get(q[2], 0) >= q[3])
        week += 7 * DAY
    return xp
