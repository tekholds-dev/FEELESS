"""🪙 THE POOL LEDGER (owner 2026-11-05). Every agent fee and every proof sent lands in the one Collective wallet; this file says whose part of it is whose.
THE LIVE DEAL IS 'stake' (owner 2026-11-06): see collective_stake.py. 'bank' and 'plans' below stay only for tests and streams that already ran.
THE DEAL NOW (owner 2026-11-05, cfg deal='bank'): the Collective banks all of every send, for good, and a send never pays a reward. The sealed record keeps each agent's total sent and its points: each send's dollars x its boost at that moment. Each month rewardPayPct of the fee pot becomes the month's budget. Each agent is paid its part on its own clock: rank and boost shorten the wait from rewardDays to minDays, and paying sooner only moves money sooner. floorPct of the budget is split evenly by owner, so every rank eats; the rest goes by points, up to capPct per owner. Reward payouts can never pass payoutCapPct of all fee money ever in. Points carry over each month at carryPct. Nothing is promised and a month can pay nothing. Lifetime points set a rank, which sets speed only.
The older plans below (deal='plans') still finish any stream already running:
A send: the Collective keeps skimPct. The rest follows the PLAN its owner picked: it comes back at a steady rate to a fixed date, up to the plan's part, and the remainder stays with the Collective. The Vault plan never comes back: it becomes a permanent claim on the fee pot instead, at the highest weight.
The fee pot: potPct of real trading and task fees ONLY. It pays a part of what is there every day to agents by weight: what they have working × their plan × their boost. It lands in their earnings directly.
Boost = points that scale with dollars sent, fading, graded by the print's real strength. Points can also be SPENT to bring a date closer.
NOT A PONZI, by construction: another member's deposit, send or release can never reach the pot, so nobody's return is paid from somebody else's money coming in. No reward for bringing people, no promised rate. Members earn only while members really trade.
Why it cannot break: amounts are whole units per token, every move takes from one bucket what it gives another, and payouts are a part of what is really there, so nothing is ever owed that does not exist.
Sealed: the ledger is encrypted and signed at rest, so an edited file refuses to load instead of resetting. Every dollar in is one link of a keyed hash chain; audit() walks the chain from the start and it must equal what the ledger holds to the unit. Pure apart from the locked file helpers."""
import fcntl
import hashlib
import hmac
import json
import os
import uuid

TOKENS = ('SOL', 'USDC')
UNITS = {'SOL': 1_000_000_000, 'USDC': 1_000_000}
TICK_S = 60
BOOST_POINTS_FULL = 100

PLANS = ('week', 'month', 'quarter', 'vault')
DEFAULTS = {'deal': 'stake', 'tier500Usd': 10000.0, 'tier750Usd': 100000.0, 'tier1000Usd': 1000000.0, 'kneeUsd': 1000.0, 'sizeAbovePct': 50.0, 'walletCapPct': 10.0, 'dripDays': 7.0, 'reservePct': 20.0, 'spotMaxPct': 50.0, 'minStakeUsd': 1.0, 'collectivePoolPct': 20.0, 'cutPerX': 1.0, 'fastPtsPerDay': 5.0, 'fastMaxDays': 30.0, 'maxBackX': 1.08, 'rewardDays': 30.0, 'minDays': 7.0, 'rankSpeedPct': 50.0, 'boostSpeedPct': 30.0, 'rewardPayPct': 50.0, 'payoutCapPct': 50.0, 'floorPct': 20.0, 'carryPct': 80.0, 'skimPct': 20.0, 'sitePct': 20.0, 'potPct': 50.0, 'potPayDayPct': 10.0, 'weightMaxX': 2.0, 'capPct': 3.0, 'boostFadeDays': 60.0, 'boostBackPts': 5.0, 'ptsBase': 5.0, 'ptsPerUsd': 2.0, 'ptsMaxSend': 60.0, 'ptsPerDay': 10.0,
            'weekDays': 7.0, 'weekBack': 70.0, 'weekWeight': 1.0, 'weekRoom': 1.5, 'monthDays': 30.0, 'monthBack': 85.0, 'monthWeight': 2.0, 'monthRoom': 2.0, 'quarterDays': 90.0, 'quarterBack': 95.0, 'quarterWeight': 3.0, 'quarterRoom': 3.0, 'vaultWeight': 6.0, 'vaultRoom': 6.0,
            'depositPct': 10.0, 'firstMinUsd': 50.0, 'txnSmallPct': 5.0, 'txnMidPct': 3.0, 'txnBigPct': 1.0, 'txnSmallUsd': 10.0, 'txnBigUsd': 100.0, 'boostMode': 'payout'}
BOUNDS = {'tier500Usd': (300, 10000000), 'tier750Usd': (500, 100000000), 'tier1000Usd': (1000, 1000000000), 'kneeUsd': (100, 100000), 'sizeAbovePct': (0, 100), 'walletCapPct': (1, 50), 'dripDays': (0.04, 90), 'reservePct': (0, 90), 'spotMaxPct': (5, 100), 'minStakeUsd': (0, 1000), 'collectivePoolPct': (5, 80), 'cutPerX': (0.25, 10), 'fastPtsPerDay': (0.25, 100), 'fastMaxDays': (1, 90), 'maxBackX': (1, 5), 'rewardDays': (7, 90), 'minDays': (1, 30), 'rankSpeedPct': (0, 80), 'boostSpeedPct': (0, 80), 'rewardPayPct': (0, 100), 'payoutCapPct': (0, 50), 'floorPct': (0, 100), 'carryPct': (0, 100), 'skimPct': (0, 50), 'sitePct': (0, 100), 'potPct': (0, 100), 'potPayDayPct': (1, 25), 'weightMaxX': (1, 5), 'capPct': (1, 100), 'boostFadeDays': (7, 365), 'boostBackPts': (0, 15), 'ptsBase': (0, 50), 'ptsPerUsd': (0, 20), 'ptsMaxSend': (5, 500), 'ptsPerDay': (1, 100),
          'weekDays': (1, 21), 'weekBack': (0, 100), 'weekWeight': (0, 10), 'weekRoom': (0, 10), 'monthDays': (14, 60), 'monthBack': (0, 100), 'monthWeight': (0, 10), 'monthRoom': (0, 10), 'quarterDays': (45, 365), 'quarterBack': (0, 100), 'quarterWeight': (0, 10), 'quarterRoom': (0, 10), 'vaultWeight': (0, 20), 'vaultRoom': (0, 20),
          'depositPct': (0, 20), 'firstMinUsd': (0, 500), 'txnSmallPct': (0, 5), 'txnMidPct': (0, 5), 'txnBigPct': (0, 5), 'txnSmallUsd': (1, 1000), 'txnBigUsd': (1, 100000)}
MODES = ('payout', 'rank')
POT_KINDS = ('txn', 'task')   # member fees on real activity: part of each reaches the pot
OUTSIDE_KINDS = ('site', 'profit')     # money from outside the members: all of it goes to the pot. This is what lets the average member come out ahead
SEAL_ID = 'collective-pool'
GENESIS = '0' * 64


class Tampered(Exception):
    """The ledger file is not what we wrote. Nothing may read or pay from it."""


def _key():
    import cat_keys
    return hashlib.sha256(f'pool-chain:{cat_keys._master()}'.encode()).digest()


def print_seed(cat_id):
    """An agent's fingerprint seed: keyed, so nobody can pick or copy one. Safe to show: it says nothing about the agent."""
    return hmac.new(_key(), f'print:{cat_id}'.encode(), hashlib.sha256).hexdigest()[:32]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def clean_cfg(c):
    c = c if isinstance(c, dict) else {}
    out = {}
    for k, d in DEFAULTS.items():
        if k == 'boostMode':
            out[k] = c.get(k) if c.get(k) in MODES else d
        elif k == 'deal':
            out[k] = c.get(k) if c.get(k) in ('plans', 'bank', 'stake') else d
        else:
            lo, hi = BOUNDS[k]
            v = c.get(k, d)
            out[k] = round(min(hi, max(lo, _f(v))), 2) if isinstance(v, (int, float)) and not isinstance(v, bool) else d
    out['txnBigUsd'] = max(out['txnSmallUsd'], out['txnBigUsd'])
    return out


def new_state():
    return {'v': 4, 'cfg': clean_cfg(None), 'at': 0, 'books': {t: {'pot': 0, 'keep': 0, 'in': {}, 'paidOut': 0} for t in TOKENS}, 'agents': {}, 'seen': {}, 'chain': None, 'head': GENESIS, 'links': 0, 'moved': {t: 0 for t in TOKENS}, 'hist': [], 'trailNew': []}


def _link(state, key, token, units, kind):
    """One dollar-in event, chained to the one before it. Change any past link and every later one stops matching."""
    ev = {'n': int(state.get('links') or 0) + 1, 'key': str(key), 'token': token, 'units': int(units), 'kind': kind}
    head = hmac.new(_key(), f"{state.get('head') or GENESIS}|{json.dumps(ev, sort_keys=True)}".encode(), hashlib.sha256).hexdigest()
    state['head'] = head; state['links'] = ev['n']; state.setdefault('moved', {t: 0 for t in TOKENS})[token] = int(state['moved'].get(token) or 0) + int(units)
    state.setdefault('trailNew', []).append({**ev, 'head': head})


def _agent(state, cat, owner='', now=0):
    a = state['agents'].get(cat)
    if not a:
        a = state['agents'][cat] = {'owner': str(owner or ''), 'locked': {t: 0 for t in TOKENS}, 'owed': {t: 0 for t in TOKENS}, 'sent': {t: 0 for t in TOKENS}, 'earned': {t: 0 for t in TOKENS}, 'paid': {t: 0 for t in TOKENS}, 'vault': {t: 0 for t in TOKENS}, 'streams': [], 'room': 0.0, 'roomAt': now, 'boost': 0.0, 'first': now, 'plan': 'month', 'spent': 0}
    if owner:
        a['owner'] = str(owner)
    return a


def _once(state, key):
    """One key moves money once, ever, with no limit on how many keys there are. → True the first time."""
    if not key:
        return False
    seen = state.get('seen')
    if isinstance(seen, list):   # the first version kept a capped list
        seen = state['seen'] = {hashlib.sha256(str(k).encode()).hexdigest()[:20]: 1 for k in seen}
    h = hashlib.sha256(str(key).encode()).hexdigest()[:20]
    if h in seen:
        return False
    seen[h] = 1
    return True


def _take_in(state, token, units, kind):
    b = state['books'][token]; units = int(units)
    if state['cfg'].get('deal') == 'stake':   # the Collective earns every fee from the jump; a send is a stake in the pools
        b['stake' if kind == 'proofs' else 'keep'] = int(b.get('stake' if kind == 'proofs' else 'keep') or 0) + units; b['in'][kind] = int(b['in'].get(kind) or 0) + units
        return
    pot = units if kind in OUTSIDE_KINDS else int(units * state['cfg']['potPct'] / 100) if kind in POT_KINDS else 0
    b['pot'] += pot; b['keep'] += units - pot
    b['in'][kind] = int(b['in'].get(kind) or 0) + units


def income(state, key, token, units, kind):
    """A fee or a kept part has really landed. → True when it counted."""
    if token not in TOKENS or int(units) <= 0 or not _once(state, key):
        return False
    _link(state, key, token, units, kind)
    _take_in(state, token, units, kind)
    return True


def book_result(state, key, token, units):
    """A real pool result, once. Profit joins the pot; a loss comes off the pot first and then off what is banked. Sends never become rewards, only profit and fees do. → True when it counted."""
    units = int(units)
    if token not in TOKENS or not units:
        return False
    if units > 0:
        return income(state, key, token, units, 'profit')
    if not _once(state, key):
        return False
    _link(state, key, token, units, 'loss'); b = state['books'][token]; hit = min(b['pot'], -units); b['pot'] -= hit; b['keep'] = max(0, b['keep'] - (-units - hit))
    b['in']['loss'] = int(b['in'].get('loss') or 0) + -units
    return True


def back_room(state, cat, token):
    """What this agent may still be paid in this token: maxBackX of what it sent, less what it was already paid. The owner can raise maxBackX once the Collective is stable."""
    a = state['agents'][cat]
    return max(0, int(int(a['sent'].get(token) or 0) * state['cfg']['maxBackX']) - int(a['earned'].get(token) or 0))


def _room(a, now, cfg):
    """What it may still earn from the fee pot: 1x what it sent, fading by half every 30 days. It stops a big late send from draining the pot."""
    dt = max(0.0, now - _f(a.get('roomAt')))
    a['room'] = _f(a.get('room')) * 0.5 ** (dt / (30 * 86400)); a['roomAt'] = now
    return a['room']


def plan_of(cfg, name, boost=0.0):
    """One plan's numbers. A boost adds up to boostBackPts to what comes back, never past 100%, and never to the Vault."""
    n = name if name in PLANS else 'month'
    if n == 'vault':
        return {'plan': n, 'days': None, 'backPct': 0.0, 'weightX': cfg['vaultWeight'], 'roomX': cfg['vaultRoom']}
    b = 0.0 if cfg.get('boostMode') == 'rank' else max(0.0, min(1.0, _f(boost)))
    return {'plan': n, 'days': cfg[f'{n}Days'], 'backPct': round(min(100.0, cfg[f'{n}Back'] + cfg['boostBackPts'] * b), 2), 'weightX': cfg[f'{n}Weight'], 'roomX': cfg[f'{n}Room']}


def points_for(cfg, usd, strength=50.0):
    """Points for one verified send: they scale with its dollars, up to a limit, and a stronger print earns more from the same send (0.5x to 1.5x)."""
    return round(min(cfg['ptsMaxSend'], cfg['ptsBase'] + _f(usd) * cfg['ptsPerUsd']) * (0.5 + min(100.0, max(0.0, _f(strength))) / 100), 1)


def site_owed(cfg, site_fees_usd, moved_usd):
    """The Collective's share of FEELESS's swap fees from regular traders, less what has really reached its wallet. Pure."""
    return round(max(0.0, _f(site_fees_usd) * cfg['sitePct'] / 100 - _f(moved_usd)), 6)


def clear_review(state, cat, stream_id):
    """The owner clears a held proof. → True when it changed."""
    row = next((r for r in (state['agents'].get(cat) or {}).get('streams') or [] if r.get('id') == stream_id), None)
    if not row or not row.get('held'):
        return False
    row['held'] = False; row['clearedAt'] = round(_f(state.get('at')))
    if row.get('points'):   # cleared: its points count now
        a = state['agents'][cat]; a['rewardPts'] = round(_f(a.get('rewardPts')) + row['points'], 4); a['lifetimePts'] = round(_f(a.get('lifetimePts')) + row['points'], 4)
    return True


RANKS = (('Spark', 0), ('Signal', 50), ('Ridge', 250), ('Print', 1000), ('Legend', 5000), ('Myth', 25000))


def rank_of(points):
    """Where lifetime points put an agent. A name only: it changes no money."""
    p = max(0.0, _f(points)); i = max(k for k, (_, at) in enumerate(RANKS) if p >= at); nxt = RANKS[i + 1] if i + 1 < len(RANKS) else None
    return {'i': i, 'name': RANKS[i][0], 'points': round(p, 2), 'next': nxt[0] if nxt else None, 'toNext': round(nxt[1] - p, 2) if nxt else 0, 'part': round((p - RANKS[i][1]) / (nxt[1] - RANKS[i][1]), 4) if nxt else 1.0}


def points_of(cfg, usd, boost):
    """A send's points: its dollars x its boost at that moment. Rank-only mode: dollars alone."""
    return round(max(0.0, _f(usd)) * levers(cfg, boost)['weightX'], 4)


def _keep_send(state, key, cat, owner, token, units, usd, now, boost, meta):
    """The Collective keeps all of it. The record keeps the amount and its points. A held proof earns no points until it is cleared."""
    cfg = state['cfg']; a = _agent(state, cat, owner, now); a['boost'] = max(0.0, min(1.0, _f(boost))); usd = max(0.0, _f(usd)); pts = points_of(cfg, usd, a['boost'])
    _link(state, key, token, units, 'send'); _take_in(state, token, units, 'proofs'); a['sent'][token] += units; a['sentUsd'] = round(_f(a.get('sentUsd')) + usd, 4)
    row = {'id': uuid.uuid4().hex[:10], 'at': round(now), 'token': token, 'plan': 'keep', 'sent': units, 'kept': units, 'locked': 0, 'left': 0, 'back': 0, 'out': 0, 'end': None, 'start': now, 'last': now, 'usd': round(usd, 4), 'unitUsd': (usd / units) if units else 0.0, 'weightX': levers(cfg, a['boost'])['weightX'], 'points': pts, **(meta or {})}
    if not row.get('held'):
        a['rewardPts'] = round(_f(a.get('rewardPts')) + pts, 4); a['lifetimePts'] = round(_f(a.get('lifetimePts')) + pts, 4)
    row['least'] = cfg.get('minStakeUsd') or 0
    a['streams'] = (list(a.get('streams') or []) + [row])[-400:]
    return {'keptUnits': units, 'lockedUnits': 0, 'plan': 'keep', 'end': None, 'backUnits': 0, 'id': row['id'], 'points': pts}


def cycle_days(cfg, rank_i, boost):
    """How often it is paid. A higher rank and a bigger boost shorten the wait, never below minDays. Speed moves money sooner; it never adds to the month's budget."""
    b = 0.0 if cfg.get('boostMode') == 'rank' else max(0.0, min(1.0, _f(boost))); top = len(RANKS) - 1
    return round(max(cfg['minDays'], cfg['rewardDays'] * (1 - cfg['rankSpeedPct'] / 100 * max(0, min(top, int(rank_i))) / top) * (1 - cfg['boostSpeedPct'] / 100 * b)), 2)


def reward_shares(state):
    """{agent: part of a month's budget}. floorPct split evenly by owner so every rank eats; the rest by points, up to capPct per owner; what a cap holds back stays in the pot."""
    cfg = state['cfg']; rows = {c: _f(a.get('rewardPts')) for c, a in state['agents'].items() if _f(a.get('rewardPts')) > 0}; total = sum(rows.values())
    if total <= 0:
        return {}
    owners = {}
    for c, v in rows.items():
        o = state['agents'][c].get('owner') or c; owners.setdefault(o, {})[c] = v
    floor = cfg['floorPct'] / 100; cap = cfg['capPct'] / 100; out = {}
    for agents in owners.values():
        sum_ = sum(agents.values()); part = floor / len(owners) + (1 - floor) * sum_ / total
        for c, v in agents.items():
            out[c] = (v / sum_) * min(part, cap)
    return out


def _budget_left(state, t):
    """Whole units still payable this month: the month's budget, the pot, and the all-time cap on fee money."""
    cfg = state['cfg']; b = state['books'][t]; fee_in = max(0, sum(int(v or 0) for k, v in b['in'].items() if k in POT_KINDS or k in OUTSIDE_KINDS) - int(b['in'].get('loss') or 0))
    return max(0, min(int((state.get('budget') or {}).get(t) or 0), b['pot'], int(fee_in * cfg['payoutCapPct'] / 100) - int(b.get('rewardPaid') or 0)))


def month_open(state, now):
    """A new month: its budget is set from the pot, and points carry over."""
    cfg = state['cfg']; state['budget'] = {t: int(state['books'][t]['pot'] * cfg['rewardPayPct'] / 100) for t in TOKENS}; state['budgetFull'] = dict(state['budget']); state['monthEnd'] = now + 30 * 86400
    if _f(state.get('monthStarted')):
        for a in state['agents'].values():
            a['rewardPts'] = round(_f(a.get('rewardPts')) * cfg['carryPct'] / 100, 4)
    state['monthStarted'] = now


def pay_rewards(state, now):
    """Pays each agent whose clock is up its part of the month, scaled to its wait. Only fees sit in the pot, so a send can never reach this. → how many were paid."""
    cfg = state['cfg']; part = reward_shares(state); n = 0
    for c, p in part.items():
        a = state['agents'][c]; days = cycle_days(cfg, rank_of(a.get('lifetimePts'))['i'], a.get('boost'))
        if not _f(a.get('nextPay')):
            a['nextPay'] = now + days * 86400
            continue
        if now < _f(a['nextPay']):
            continue
        for t in TOKENS:
            want = min(int(int((state.get('budgetFull') or {}).get(t) or 0) * p * min(1.0, days / 30)), _budget_left(state, t), back_room(state, c, t))
            if want > 0:
                b = state['books'][t]; b['pot'] -= want; b['rewardPaid'] = int(b.get('rewardPaid') or 0) + want; state['budget'][t] -= want; a['owed'][t] += want; a['earned'][t] += want
        a['nextPay'] = now + days * 86400; a['paidAt'] = round(now); n += 1
    return n


def send(state, key, cat, owner, token, units, usd, now, boost=0.0, meta=None, plan=None):
    """A verified proof send. → {keptUnits, lockedUnits, plan, end, backUnits} or None if it already counted."""
    units = int(units)
    if token not in TOKENS or units <= 0 or not _once(state, key):
        return None
    if state['cfg'].get('deal') in ('bank', 'stake'):
        return _keep_send(state, key, cat, owner, token, units, usd, now, boost, meta)
    cfg = state['cfg']; a = _agent(state, cat, owner, now); a['boost'] = max(0.0, min(1.0, _f(boost))); pl = plan_of(cfg, plan or a.get('plan'), a['boost'])
    kept = int(units * cfg['skimPct'] / 100); locked = units - kept; usd = max(0.0, _f(usd)); rate = (usd / units) if units else 0.0
    _link(state, key, token, units, 'send')
    if kept:
        _take_in(state, token, kept, 'proofs')
    _room(a, now, cfg); a['room'] += usd * pl['roomX']; a['sent'][token] += units
    row = {'id': uuid.uuid4().hex[:10], 'at': round(now), 'token': token, 'plan': pl['plan'], 'sent': units, 'kept': kept, 'usd': round(usd, 4), 'unitUsd': rate, 'weightX': pl['weightX'], **(meta or {})}
    if pl['plan'] == 'vault':   # it never comes back: the Collective holds it, and the agent holds a claim on the pot
        _take_in(state, token, locked, 'vault')
        a.setdefault('vault', {t: 0 for t in TOKENS})[token] += locked
        row.update(locked=locked, left=0, back=0, end=None, start=now, last=now, vault=locked)
    else:
        base_ = plan_of({**cfg, 'boostBackPts': 0}, pl['plan'])['backPct']; row.update(locked=locked, left=locked, back=int(locked * pl['backPct'] / 100), baseBack=int(locked * base_ / 100), out=0, start=now, last=now, end=now + pl['days'] * 86400, span=pl['days'] * 86400, backPct=pl['backPct'])
        a['locked'][token] += locked
    a['streams'] = (list(a.get('streams') or []) + [row])[-400:]
    return {'keptUnits': kept, 'lockedUnits': locked, 'plan': pl['plan'], 'end': row['end'], 'backUnits': row['back'], 'id': row['id']}


def boost_of(rows, strength, now, fade_days=60.0):
    """0 to 1. Points fade, then the print's real strength grades them: a 0 print earns half of what a 100 print earns from the same points."""
    pts = sum(_f(r.get('pts')) * 0.5 ** (max(0.0, now - _f(r.get('at'))) / (max(1.0, fade_days) * 86400)) for r in rows or [])
    return round(min(1.0, pts / BOOST_POINTS_FULL) * (0.5 + 0.5 * min(100.0, max(0.0, _f(strength))) / 100), 4)


def levers(cfg, boost):
    """What a boost changes right now. Rank-only mode: nothing."""
    b = 0.0 if cfg.get('boostMode') == 'rank' else max(0.0, min(1.0, _f(boost)))
    return {'backPlus': round(cfg['boostBackPts'] * b, 2), 'weightX': round(1 + (cfg['weightMaxX'] - 1) * b, 3)}


def spend_points(state, cat, stream_id, pts, available, now):
    """Spend points to bring one send's date closer. ptsPerDay points = one day. A date can move to no less than a third of its plan from its start. → {days, spent, end}. Raises ValueError."""
    a = state['agents'].get(cat); pts = _f(pts)
    row = next((r for r in (a or {}).get('streams') or [] if r.get('id') == stream_id), None)
    if not row or not row.get('end') or row.get('left', 0) <= 0:
        raise ValueError('That send has no date to move.')
    if pts <= 0 or pts > _f(available) - _f(a.get('spent')) + 1e-9:
        raise ValueError('It does not have that many points to spend.')
    cfg = state['cfg']; floor = row['start'] + _f(row.get('span')) / 3; end = max(floor, now + 3600, row['end'] - pts / cfg['ptsPerDay'] * 86400)
    if end >= row['end']:
        raise ValueError('That date cannot move any closer.')
    used = (row['end'] - end) / 86400 * cfg['ptsPerDay']; row['end'] = end; a['spent'] = round(_f(a.get('spent')) + used, 2)
    return {'days': round(used / cfg['ptsPerDay'], 2), 'spent': round(used, 2), 'end': round(end)}


VAULT_FADE_DAYS = 45.0
FRESH_X = 2.0
FRESH_DAYS = 7.0


def _working_usd(a, sol_usd, now):
    """What is working for an agent: its unreleased money and its Vault claim, each × its plan's weight. A Vault claim fades by half every 45 days, so it pays those still sending good proofs, not those who simply got here first."""
    w = 0.0
    for r in a.get('streams') or []:
        if r.get('held'):   # the validators held it: no fee share until it is cleared
            continue
        amt = r.get('vault') or (r.get('locked') if (r.get('left') or 0) > 0 else 0) or 0   # a send earns on its whole amount until its date
        if amt:
            age = max(0.0, now - _f(r.get('at')))
            fade = 0.5 ** (age / (VAULT_FADE_DAYS * 86400)) if r.get('vault') else 1.0
            fresh = 1 + FRESH_X * 0.5 ** (age / (FRESH_DAYS * 86400))   # a fresh proof earns the most, so proving often is what pays
            w += amt * (r.get('unitUsd') or (sol_usd / UNITS['SOL'] if r.get('token') == 'SOL' else 1 / UNITS['USDC'])) * _f(r.get('weightX')) * fade * fresh
    return w


def _locked_usd(a, sol_usd):
    return a['locked']['SOL'] / UNITS['SOL'] * sol_usd + a['locked']['USDC'] / UNITS['USDC']


def shares(state, sol_usd):
    """{cat: part of the pot, 0 to 1}. Weight = money working × plan × boost. Every wallet of one owner counts together, capped so nobody takes more than capPct once there are enough owners to share."""
    cfg = state['cfg']; per = {}; by_owner = {}
    for cat, a in state['agents'].items():
        w = _working_usd(a, sol_usd, _f(state.get('at'))) * levers(cfg, a.get('boost'))['weightX']
        if w > 0:
            per[cat] = w; o = a.get('owner') or cat; by_owner[o] = by_owner.get(o, 0.0) + w
    if not per:
        return {}
    cap = max(cfg['capPct'] / 100, min(1.0, 3 / len(by_owner)))
    scaled = dict(by_owner)
    for _ in range(8):   # capping one owner raises everyone else's part, so settle it
        tot = sum(scaled.values()); over = [o for o, w in scaled.items() if w > cap * tot + 1e-12]
        if not over:
            break
        rest = sum(w for o, w in scaled.items() if o not in over)
        if rest <= 0:
            break
        limit = rest * cap / max(1e-9, 1 - cap * len(over))
        for o in over:
            scaled[o] = limit
    tot = sum(scaled.values())
    return {cat: (w / by_owner[state['agents'][cat].get('owner') or cat]) * (scaled[state['agents'][cat].get('owner') or cat] / tot) for cat, w in per.items()}


def tick(state, now, sol_usd):
    """Move time forward: the pot pays by weight into earnings, then every send releases along its line to its date. Only whole units move, and each comes out of the bucket it goes into another from."""
    last = _f(state.get('at'))
    if not last:
        state['at'] = now
        return False
    dt = now - last
    if dt < TICK_S:
        return False
    state['at'] = now; cfg = state['cfg']; part = shares(state, sol_usd)
    pot_part = 0.0 if cfg.get('deal') in ('bank', 'stake') else 1 - (1 - cfg['potPayDayPct'] / 100) ** (dt / 86400)
    if cfg.get('deal') == 'stake':
        import collective_stake as _stake
        _stake.release(state, now)
        return True
    if cfg.get('deal') == 'bank':
        if now >= _f(state.get('monthEnd')):
            month_open(state, now)
        pay_rewards(state, now)
    for t in TOKENS:
        b = state['books'][t]; pay = int(b['pot'] * pot_part); usd_each = (sol_usd / UNITS['SOL']) if t == 'SOL' else (1 / UNITS['USDC'])
        for cat, p in part.items():
            a = state['agents'][cat]; want = int(pay * p)
            if want <= 0:
                continue
            room = _room(a, now, cfg)
            want = min(want, int(room / usd_each)) if usd_each > 0 else 0   # past its limit, it stays in the pot
            if want <= 0:
                continue
            b['pot'] -= want; a['owed'][t] += want; a['earned'][t] += want
            bp = a.setdefault('boostPot', {x: 0 for x in TOKENS}); bp[t] = int(bp.get(t) or 0) + int(want * (1 - 1 / max(1.0, levers(cfg, a.get('boost'))['weightX'])))
            a['room'] = max(0.0, room - want * usd_each)
    for a in state['agents'].values():
        for r in a.get('streams') or []:
            left = int(r.get('left') or 0)
            if left <= 0:
                continue
            t = r['token']; span = max(1.0, _f(r['end']) - _f(r['last']))
            out = left if now >= r['end'] else int(left * min(1.0, (now - _f(r['last'])) / span))
            if out <= 0:
                continue
            r['left'] = left - out; r['last'] = now; a['locked'][t] -= out
            mine = min(out, r['back'] - int(r.get('out') or 0)) if r['left'] == 0 else int(out * r['back'] / r['locked'])
            mine = max(0, min(mine, r['back'] - int(r.get('out') or 0)))
            r['out'] = int(r.get('out') or 0) + mine; a['owed'][t] += mine
            if out - mine:
                _take_in(state, t, out - mine, 'release')
    return True


def _rate(a, t, cfg, now=None):
    r_ = 0.0
    for r in a.get('streams') or []:
        if r.get('token') == t and (r.get('left') or 0) > 0 and r.get('locked'):
            r_ += (r['left'] / max(1.0, _f(r['end']) - _f(r['last']))) * (r['back'] / r['locked'])
    return r_


def _usd(units, t, sol_usd):
    return units / UNITS[t] * (sol_usd if t == 'SOL' else 1)


def project(cfg, usd, plan='month', boost=0.0, fees_day=0.0, others_usd=0.0, owners=20, outside_day=0.0):
    """What one send does, day by day, by running the real send() and tick() on a throwaway state: the same code that moves real money, with the fees and other members the viewer picks. An example, never a promise. Pure, touches nothing saved."""
    usd = max(0.01, min(100000.0, _f(usd))); fees_day = max(0.0, min(1000000.0, _f(fees_day))); others_usd = max(0.0, min(1000000000.0, _f(others_usd))); plan = plan if plan in PLANS else 'month'
    st = new_state(); st['cfg'] = clean_cfg(cfg); cfg_ = st['cfg']; t0 = 1000000.0; st['at'] = t0; u = UNITS['USDC']; pl = plan_of(cfg_, plan, boost); span = int(min(120, max(30, pl['days'] or 90)))
    def others(day):
        if others_usd > 0:
            each = others_usd / 3 / owners
            for i in range(owners):
                send(st, f'o{i}:{day}', f'o{i}', f'o{i}', 'USDC', int(each * u), each, t0 + day * 86400, plan='month')
    others(0); send(st, 'me', 'me', 'me', 'USDC', int(usd * u), usd, t0, boost=boost, plan=plan)
    me = st['agents']['me']; out = [{'day': 0, 'back': 0.0, 'pot': 0.0}]; even = None; capped = False
    for d in range(1, span + 1):
        now = t0 + d * 86400
        if d % 10 == 0:
            others(d)
        if fees_day > 0:
            income(st, f'f{d}', 'USDC', int(fees_day * u), 'txn')
        if outside_day > 0:
            income(st, f's{d}', 'USDC', int(outside_day * u), 'site')
        tick(st, now, 1.0)
        pot = me['earned']['USDC'] / u; back = max(0.0, me['owed']['USDC'] / u - pot)
        out.append({'day': d, 'back': round(back, 4), 'pot': round(pot, 4)})
        if even is None and back + pot >= usd:
            even = d
        capped = capped or (me.get('room') or 0) <= 0.0001
    end = out[-1]
    return {'sent': round(usd, 4), 'kept': round(usd * cfg_['skimPct'] / 100, 4), 'plan': pl['plan'], 'days': span, 'series': out, 'back': end['back'], 'pot': end['pot'], 'profit': round(end['back'] + end['pot'] - usd, 4), 'breakEven': even, 'capped': capped, 'capPct': cfg_['capPct']}


GROW_SENDERS = (100, 1000, 10000)
GROW_SWAPS = (0.0, 100000.0, 1000000.0, 10000000.0, 100000000.0)


def growth(cfg, send=20.0, plan='month', volume_day=100.0, sender_pct=100.0, swap_fee_pct=0.5):
    """Where an agent comes out as FEELESS grows: the result of one send, for each number of senders against how much everyone else swaps. More senders split the pot; more trading fills it. Each point is project(), the real pool code. Pure."""
    cfg_ = clean_cfg(cfg); send = max(1.0, min(10000.0, _f(send))); volume_day = max(0.0, min(1000000.0, _f(volume_day))); sender_pct = max(1.0, min(100.0, _f(sender_pct)))
    fee_each = txn_fee_usd(cfg_, volume_day)[0]; rows = []
    for swaps in GROW_SWAPS:
        row = {'swaps': swaps}
        for n in GROW_SENDERS:
            p = project(cfg_, send, plan, fees_day=fee_each * n / (sender_pct / 100), others_usd=n * send, outside_day=swaps * swap_fee_pct / 100 * cfg_['sitePct'] / 100)
            row[f's{n}'] = p['profit']; row[f'b{n}'] = p['back']; row[f'p{n}'] = p['pot']
        rows.append(row)
    return {'rows': rows, 'send': send, 'plan': plan, 'senders': list(GROW_SENDERS), 'feeEach': round(fee_each, 4), 'swapFeePct': swap_fee_pct, 'sitePct': cfg_['sitePct'], 'potPct': cfg_['potPct'], 'skimPct': cfg_['skimPct'], 'days': plan_of(cfg_, plan)['days'] or 90, 'capPct': cfg_['capPct'], 'roomX': plan_of(cfg_, plan)['roomX']}


def pays_for_itself(usd, back_usd, weight_x, pot_day_usd, total_weight):
    """At today's fee pot, about how many days until a send has returned what it sent, or None when the pot pays nothing yet. An estimate, never a promise. Pure."""
    gap = max(0.0, _f(usd) - _f(back_usd)); w = _f(usd) * _f(weight_x); per_day = _f(pot_day_usd) * (w / max(1e-9, _f(total_weight) + w))
    return None if per_day <= 0 else round(gap / per_day, 1)


def stream_view(r, sol_usd):
    t = r['token']; back = r.get('back') or 0; out = r.get('out') or 0
    return {k: r.get(k) for k in ('id', 'at', 'plan', 'token', 'end', 'name', 'sym', 'pct', 'sig', 'backPct', 'start', 'held', 'review')} | {'sent': r['sent'] / UNITS[t], 'kept': r['kept'] / UNITS[t], 'locked': r['locked'] / UNITS[t], 'backTotal': back / UNITS[t], 'backSoFar': out / UNITS[t], 'backUsd': round(_usd(back, t, sol_usd), 4), 'soFarUsd': round(_usd(out, t, sol_usd), 4), 'sentUsd': round(_usd(r['sent'], t, sol_usd), 4), 'vaultUsd': round(_usd(r.get('vault') or 0, t, sol_usd), 4), 'done': not r.get('vault') and (r.get('left') or 0) <= 0}


def view(state, cat, now, sol_usd):
    """One agent's numbers for its owner. owedUsd + ratePerSecUsd x seconds is the live count."""
    cfg = state['cfg']; a = state['agents'].get(cat)
    if not a:
        return {'boostUsd': 0, 'boostRateUsd': 0, 'owedUsd': 0, 'ratePerSecUsd': 0, 'lockedUsd': 0, 'sentUsd': 0, 'earnedUsd': 0, 'vaultUsd': 0, 'backLeftUsd': 0, 'owed': {'SOL': 0, 'USDC': 0}, 'locked': {'SOL': 0, 'USDC': 0}, 'boost': 0, 'levers': levers(cfg, 0), 'plan': 'month', 'spent': 0, 'streams': [], 'at': round(now), 'solUsd': sol_usd, 'empty': True}
    dt = max(0.0, now - _f(state.get('at')))
    import collective_stake as _stake
    rate = sum(_usd(_rate(a, t, cfg) + _stake.drip_rate(state, a, t), t, sol_usd) for t in TOKENS)
    part = shares(state, sol_usd).get(cat, 0.0); pot_day = sum(_usd(state['books'][t]['pot'], t, sol_usd) for t in TOKENS) * (cfg['potPayDayPct'] / 100)
    rows = a.get('streams') or []
    rp_ = reward_shares(state).get(cat, 0.0); rk_ = rank_of(a.get('lifetimePts')); cy_ = cycle_days(cfg, rk_['i'], a.get('boost')); deal_ = {'deal': cfg.get('deal'), 'rewardPts': round(_f(a.get('rewardPts')), 2), 'rank': rk_, 'rewardShare': round(rp_, 6), 'cycleDays': cy_, 'rewardEnd': round(_f(a.get('nextPay'))) or None, 'rewardNextUsd': round(sum(_usd(int(int((state.get('budgetFull') or {}).get(t) or 0) * rp_ * min(1.0, cy_ / 30)), t, sol_usd) for t in TOKENS), 6)}
    extra = sum(_usd(int((r.get('out') or 0) * max(0, (r.get('back') or 0) - (r.get('baseBack') or r.get('back') or 0)) / max(1, r.get('back') or 1)), r['token'], sol_usd) for r in rows) + sum(_usd(int((a.get('boostPot') or {}).get(t) or 0), t, sol_usd) for t in TOKENS)
    extra_rate = sum(_usd(((r['left'] / max(1.0, _f(r['end']) - _f(r['last']))) * max(0, (r.get('back') or 0) - (r.get('baseBack') or r.get('back') or 0)) / r['locked']), r['token'], sol_usd) for r in rows if (r.get('left') or 0) > 0 and r.get('locked'))
    deal_ = {**deal_, 'maxBackX': cfg['maxBackX'], 'backCapUsd': round(sum(_usd(int(a['sent'][t] * cfg['maxBackX']), t, sol_usd) for t in TOKENS), 6), 'backRoomUsd': round(sum(_usd(back_room(state, cat, t), t, sol_usd) for t in TOKENS), 6)}
    return {**deal_, 'boostUsd': round(extra + extra_rate * dt, 9), 'boostRateUsd': round(extra_rate, 12), 'potShare': round(part, 6), 'feeShareDayUsd': round(pot_day * part, 6), 'streams': [stream_view(r, sol_usd) for r in rows[::-1][:60]], 'hist': (a.get('hist') or [])[-120:], 'plan': a.get('plan') or 'month', 'spent': _f(a.get('spent')),
            'owedUsd': round(sum(_usd(a['owed'][t], t, sol_usd) for t in TOKENS) + rate * dt, 9), 'ratePerSecUsd': round(rate, 12), 'lockedUsd': round(sum(_usd(a['locked'][t], t, sol_usd) for t in TOKENS), 6), 'vaultUsd': round(sum(_usd((a.get('vault') or {}).get(t) or 0, t, sol_usd) for t in TOKENS), 6),
            'backLeftUsd': round(sum(_usd((r.get('back') or 0) - (r.get('out') or 0), r['token'], sol_usd) for r in rows), 6), 'nextEnd': min((r['end'] for r in rows if (r.get('left') or 0) > 0), default=None),
            'sentUsd': round(sum(_usd(a['sent'][t], t, sol_usd) for t in TOKENS), 6), 'earnedUsd': round(sum(_usd(a['earned'][t], t, sol_usd) for t in TOKENS), 6),
            'owed': {t: a['owed'][t] / UNITS[t] for t in TOKENS}, 'locked': {t: a['locked'][t] / UNITS[t] for t in TOKENS}, 'boost': a.get('boost') or 0, 'levers': levers(cfg, a.get('boost')), 'at': round(now), 'solUsd': sol_usd}


def snapshot(state, now, sol_usd):
    """One row a day for the growth charts, the Collective's and each agent's."""
    day = int(now // 86400)
    if (state.get('hist') or [{}])[-1].get('d') == day:
        return
    t = totals(state, sol_usd)['usd']
    state['hist'] = (list(state.get('hist') or []) + [{'d': day, **t}])[-400:]
    for a in state['agents'].values():
        a['hist'] = (list(a.get('hist') or []) + [{'d': day, 'back': round(sum(_usd((r.get('back') or 0) - (r.get('out') or 0), r['token'], sol_usd) for r in a.get('streams') or []), 6), 'owed': round(sum(_usd(a['owed'][k], k, sol_usd) for k in TOKENS), 6), 'locked': round(_locked_usd(a, sol_usd), 6), 'earned': round(sum(_usd(a['earned'][k], k, sol_usd) for k in TOKENS), 6), 'sent': round(sum(_usd(a['sent'][k], k, sol_usd) for k in TOKENS), 6)}])[-180:]


def backed(state, t):
    """What the wallet must always hold of this token."""
    import collective_stake as _stake
    return state['books'][t]['pot'] + sum(a['locked'][t] + a['owed'][t] + _stake.drip_left(a, t) for a in state['agents'].values())


def check_chain(state, balances, now):
    """Compare the real wallet with what must be there. A shortfall stops any payout the moment payouts exist."""
    rows = {t: {'chain': int(balances.get(t) or 0), 'need': backed(state, t)} for t in TOKENS}
    state['chain'] = {'at': round(now), 'tokens': rows, 'short': [t for t, r in rows.items() if r['chain'] < r['need']]}
    return state['chain']


def totals(state, sol_usd):
    cfg = state['cfg']; out = {'agents': 0, 'usd': {'pot': 0.0, 'keep': 0.0, 'locked': 0.0, 'owed': 0.0}, 'in': {}, 'ratePerSecUsd': 0.0}
    for t in TOKENS:
        b = state['books'][t]
        out['usd']['pot'] += _usd(b['pot'], t, sol_usd); out['usd']['keep'] += _usd(b['keep'], t, sol_usd)
        for k, v in b['in'].items():
            out['in'][k] = out['in'].get(k, 0.0) + _usd(int(v), t, sol_usd)
        for a in state['agents'].values():
            out['usd']['locked'] += _usd(a['locked'][t], t, sol_usd); out['usd']['owed'] += _usd(a['owed'][t], t, sol_usd)
            out['usd']['vault'] = out['usd'].get('vault', 0.0) + _usd((a.get('vault') or {}).get(t) or 0, t, sol_usd)
            out['ratePerSecUsd'] += _usd(_rate(a, t, cfg), t, sol_usd)
    out['agents'] = sum(1 for a in state['agents'].values() if any(a['sent'].values()))
    out['usd'] = {k: round(v, 6) for k, v in out['usd'].items()}; out['in'] = {k: round(v, 6) for k, v in out['in'].items()}; out['ratePerSecUsd'] = round(out['ratePerSecUsd'], 12)
    return out


def rules(cfg):
    """What a user's picture draws, straight from the live settings."""
    keep = ('skimPct', 'sitePct', 'potPct', 'potPayDayPct', 'weightMaxX', 'boostBackPts', 'ptsBase', 'ptsPerUsd', 'ptsMaxSend', 'ptsPerDay', 'depositPct', 'firstMinUsd', 'txnSmallPct', 'txnMidPct', 'txnBigPct', 'txnSmallUsd', 'txnBigUsd', 'boostMode', 'boostFadeDays')
    return {**{k: cfg[k] for k in keep}, 'deal': cfg.get('deal'), **{k: cfg[k] for k in ('collectivePoolPct', 'cutPerX', 'fastPtsPerDay', 'fastMaxDays', 'kneeUsd', 'sizeAbovePct', 'dripDays', 'tier500Usd', 'tier750Usd', 'tier1000Usd', 'walletCapPct')}, **{k: cfg[k] for k in ('maxBackX', 'rewardDays', 'minDays', 'rankSpeedPct', 'boostSpeedPct', 'rewardPayPct', 'payoutCapPct', 'floorPct', 'carryPct', 'capPct')}, 'ranks': [{'name': n, 'at': v, 'days': cycle_days(cfg, i, 0), 'fastest': cycle_days(cfg, i, 1)} for i, (n, v) in enumerate(RANKS)], 'potKinds': list(POT_KINDS), 'plans': [plan_of(cfg, n) for n in PLANS]}


def txn_fee_usd(cfg, usd):
    """A % of each agent trade, by its size: small trades pay most."""
    usd = max(0.0, _f(usd))
    pct = cfg['txnSmallPct'] if usd < cfg['txnSmallUsd'] else cfg['txnMidPct'] if usd < cfg['txnBigUsd'] else cfg['txnBigPct']
    return round(usd * pct / 100, 6), pct


def _seal(raw):
    import cat_keys
    return b'FP1:' + cat_keys.seal_bytes(raw, SEAL_ID)


def _unseal(raw):
    import cat_keys
    return cat_keys.unseal_bytes(raw[4:], SEAL_ID)


def _trail_path(path):
    return path.with_suffix('.trail')


def load(path):
    """No file yet: a new ledger. A file that fails its seal raises Tampered: it never quietly starts again from zero."""
    try:
        raw = path.read_bytes()
    except OSError:
        return new_state()
    base = new_state()
    if not raw.startswith(b'FP1:'):   # the first plain version, sealed on its next write
        try:
            d = json.loads(raw)
        except ValueError as e:
            raise Tampered(str(e))
    else:
        try:
            d = json.loads(_unseal(raw))
        except Exception as e:   # noqa: BLE001 — any failed seal is the same answer
            raise Tampered(str(e)[:120])
    if int(d.get('v') or 1) < 3:   # the first plans: nothing was ever sent under the older rules
        d['cfg'] = {}; d['v'] = 3
    if int(d.get('v') or 1) < 4:   # owner 2026-11-06: the stake deal. The ledger had no sends when it changed
        d['cfg'] = {**(d.get('cfg') or {}), 'deal': 'stake'}; d['v'] = 4
    return {**base, **d, 'cfg': clean_cfg(d.get('cfg')), 'trailNew': []}


def audit(path):
    """Walk the whole chain from the first dollar. It must end on the ledger's head, and the money it counted must equal what the ledger holds. → {ok, links, head, why}"""
    st = load(path); head = GENESIS; n = 0; moved = {t: 0 for t in TOKENS}
    try:
        rows = _trail_path(path).read_bytes().splitlines()
    except OSError:
        rows = []
    for row in rows:
        try:
            ev = json.loads(_unseal(row))
        except Exception:   # noqa: BLE001
            return {'ok': False, 'links': n, 'head': head, 'why': f'link {n + 1} failed its seal'}
        claim = ev.pop('head', '')
        head = hmac.new(_key(), f"{head}|{json.dumps(ev, sort_keys=True)}".encode(), hashlib.sha256).hexdigest(); n += 1
        if not hmac.compare_digest(head, claim) or ev.get('n') != n:
            return {'ok': False, 'links': n, 'head': head, 'why': f'link {n} does not match'}
        moved[ev['token']] += int(ev['units'])
    if head != (st.get('head') or GENESIS) or n != int(st.get('links') or 0):
        return {'ok': False, 'links': n, 'head': head, 'why': 'the chain does not end where the ledger says'}
    for t in TOKENS:
        holds = st['books'][t]['keep'] + st['books'][t]['paidOut'] + backed(st, t)
        if holds != moved[t]:
            return {'ok': False, 'links': n, 'head': head, 'why': f'{t}: the ledger holds {holds}, the chain counted {moved[t]}'}
    return {'ok': True, 'links': n, 'head': head, 'why': ''}


def update(path, fn):
    """Read, change and write under one lock, across both services. fn(state) → its result. A failed fn writes nothing."""
    with path.with_suffix('.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = load(path); out = fn(state); fresh = state.pop('trailNew', [])
            if fresh:   # the trail first: a crash here leaves a link the ledger never counted, which audit() reports
                with _trail_path(path).open('ab') as fh:
                    for ev in fresh:
                        fh.write(_seal(json.dumps(ev, sort_keys=True).encode()) + b'\n')
                    fh.flush(); os.fsync(fh.fileno())
            tmp = path.with_name(f'{path.name}.{uuid.uuid4().hex}.tmp')
            try:
                with tmp.open('wb') as fh:
                    fh.write(_seal(json.dumps(state, separators=(',', ':')).encode()))
                    fh.flush(); os.fsync(fh.fileno())
                os.replace(tmp, path)
            finally:
                tmp.unlink(missing_ok=True)
            return out
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
