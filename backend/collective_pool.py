"""🪙 THE POOL LEDGER (owner 2026-11-05). Every agent fee and every proof sent lands in the one Collective wallet; this file says whose part of it is whose.
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
DEFAULTS = {'skimPct': 20.0, 'sitePct': 20.0, 'potPct': 50.0, 'potPayDayPct': 10.0, 'weightMaxX': 2.0, 'capPct': 3.0, 'boostFadeDays': 60.0, 'boostBackPts': 5.0, 'ptsBase': 5.0, 'ptsPerUsd': 2.0, 'ptsMaxSend': 60.0, 'ptsPerDay': 10.0,
            'weekDays': 7.0, 'weekBack': 70.0, 'weekWeight': 1.0, 'weekRoom': 1.5, 'monthDays': 30.0, 'monthBack': 85.0, 'monthWeight': 2.0, 'monthRoom': 2.0, 'quarterDays': 90.0, 'quarterBack': 95.0, 'quarterWeight': 3.0, 'quarterRoom': 3.0, 'vaultWeight': 6.0, 'vaultRoom': 6.0,
            'depositPct': 10.0, 'firstMinUsd': 50.0, 'txnSmallPct': 5.0, 'txnMidPct': 3.0, 'txnBigPct': 1.0, 'txnSmallUsd': 10.0, 'txnBigUsd': 100.0, 'boostMode': 'payout'}
BOUNDS = {'skimPct': (0, 50), 'sitePct': (0, 100), 'potPct': (0, 100), 'potPayDayPct': (1, 25), 'weightMaxX': (1, 5), 'capPct': (1, 100), 'boostFadeDays': (7, 365), 'boostBackPts': (0, 15), 'ptsBase': (0, 50), 'ptsPerUsd': (0, 20), 'ptsMaxSend': (5, 500), 'ptsPerDay': (1, 100),
          'weekDays': (1, 21), 'weekBack': (0, 100), 'weekWeight': (0, 10), 'weekRoom': (0, 10), 'monthDays': (14, 60), 'monthBack': (0, 100), 'monthWeight': (0, 10), 'monthRoom': (0, 10), 'quarterDays': (45, 365), 'quarterBack': (0, 100), 'quarterWeight': (0, 10), 'quarterRoom': (0, 10), 'vaultWeight': (0, 20), 'vaultRoom': (0, 20),
          'depositPct': (0, 20), 'firstMinUsd': (0, 500), 'txnSmallPct': (0, 5), 'txnMidPct': (0, 5), 'txnBigPct': (0, 5), 'txnSmallUsd': (1, 1000), 'txnBigUsd': (1, 100000)}
MODES = ('payout', 'rank')
POT_KINDS = ('txn', 'task')   # member fees on real activity: part of each reaches the pot
OUTSIDE_KINDS = ('site',)     # money from outside the members: all of it goes to the pot. This is what lets the average member come out ahead
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
        else:
            lo, hi = BOUNDS[k]
            v = c.get(k, d)
            out[k] = round(min(hi, max(lo, _f(v))), 2) if isinstance(v, (int, float)) and not isinstance(v, bool) else d
    out['txnBigUsd'] = max(out['txnSmallUsd'], out['txnBigUsd'])
    return out


def new_state():
    return {'v': 3, 'cfg': clean_cfg(None), 'at': 0, 'books': {t: {'pot': 0, 'keep': 0, 'in': {}, 'paidOut': 0} for t in TOKENS}, 'agents': {}, 'seen': {}, 'chain': None, 'head': GENESIS, 'links': 0, 'moved': {t: 0 for t in TOKENS}, 'hist': [], 'trailNew': []}


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
    return True


def send(state, key, cat, owner, token, units, usd, now, boost=0.0, meta=None, plan=None):
    """A verified proof send. → {keptUnits, lockedUnits, plan, end, backUnits} or None if it already counted."""
    units = int(units)
    if token not in TOKENS or units <= 0 or not _once(state, key):
        return None
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
    pot_part = 1 - (1 - cfg['potPayDayPct'] / 100) ** (dt / 86400)
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
    rate = sum(_usd(_rate(a, t, cfg), t, sol_usd) for t in TOKENS)
    part = shares(state, sol_usd).get(cat, 0.0); pot_day = sum(_usd(state['books'][t]['pot'], t, sol_usd) for t in TOKENS) * (cfg['potPayDayPct'] / 100)
    rows = a.get('streams') or []
    extra = sum(_usd(int((r.get('out') or 0) * max(0, (r.get('back') or 0) - (r.get('baseBack') or r.get('back') or 0)) / max(1, r.get('back') or 1)), r['token'], sol_usd) for r in rows) + sum(_usd(int((a.get('boostPot') or {}).get(t) or 0), t, sol_usd) for t in TOKENS)
    extra_rate = sum(_usd(((r['left'] / max(1.0, _f(r['end']) - _f(r['last']))) * max(0, (r.get('back') or 0) - (r.get('baseBack') or r.get('back') or 0)) / r['locked']), r['token'], sol_usd) for r in rows if (r.get('left') or 0) > 0 and r.get('locked'))
    return {'boostUsd': round(extra + extra_rate * dt, 9), 'boostRateUsd': round(extra_rate, 12), 'potShare': round(part, 6), 'feeShareDayUsd': round(pot_day * part, 6), 'streams': [stream_view(r, sol_usd) for r in rows[::-1][:60]], 'hist': (a.get('hist') or [])[-120:], 'plan': a.get('plan') or 'month', 'spent': _f(a.get('spent')),
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
    return state['books'][t]['pot'] + sum(a['locked'][t] + a['owed'][t] for a in state['agents'].values())


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
    return {**{k: cfg[k] for k in keep}, 'potKinds': list(POT_KINDS), 'plans': [plan_of(cfg, n) for n in PLANS]}


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
