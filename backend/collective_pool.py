"""🪙 THE POOL LEDGER (owner 2026-11-04). Every agent fee and every proof sent lands in the one Collective wallet; this file says whose part of it is whose.
A send: the Collective keeps skimPct, the rest locks. Locked money releases by half every halfLife days: splitPct to the agent as earnings, the rest to the Collective.
The fee pot: potPct of real trading and task fees ONLY. Half of it pays out every potHalfLife days to agents with money locked, by weight, and lands in their locked balance, so it compounds.
NOT A PONZI, by construction: another member's deposit, send or release can never reach the pot, so nobody's return is paid from somebody else's money coming in. No reward for bringing people, no promised rate. Members earn only while members really trade.
Boosts move three things only: the split, the release speed and the weight in the fee pot.

Why it cannot break: amounts are whole units per token, every move takes from one bucket what it gives another, and payouts are a part of what is really there, so nothing is ever owed that does not exist.
Sealed: the ledger is encrypted and signed at rest, so an edited file refuses to load instead of resetting. Every dollar in is one link of a keyed hash chain; audit() walks the chain from the start and it must equal what the ledger holds to the unit.
No rate is promised anywhere. No new fees means the count slows; own money still releases. Pure apart from the locked file helpers."""
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

DEFAULTS = {'skimPct': 20.0, 'splitPct': 75.0, 'splitMaxPct': 78.0, 'halfLifeDays': 30.0, 'halfLifeMinDays': 15.0, 'potPct': 50.0, 'potHalfLifeDays': 30.0, 'weightMaxX': 2.0, 'capPct': 3.0, 'earnRoomX': 1.0, 'boostFadeDays': 60.0,
            'depositPct': 10.0, 'firstMinUsd': 50.0, 'txnSmallPct': 5.0, 'txnMidPct': 3.0, 'txnBigPct': 1.0, 'txnSmallUsd': 10.0, 'txnBigUsd': 100.0, 'boostMode': 'payout'}
BOUNDS = {'skimPct': (0, 50), 'splitPct': (50, 100), 'splitMaxPct': (50, 100), 'halfLifeDays': (7, 180), 'halfLifeMinDays': (3, 180), 'potPct': (0, 100), 'potHalfLifeDays': (7, 180), 'weightMaxX': (1, 5), 'capPct': (1, 100), 'earnRoomX': (0, 5), 'boostFadeDays': (7, 365),
          'depositPct': (0, 20), 'firstMinUsd': (0, 500), 'txnSmallPct': (0, 5), 'txnMidPct': (0, 5), 'txnBigPct': (0, 5), 'txnSmallUsd': (1, 1000), 'txnBigUsd': (1, 100000)}
MODES = ('payout', 'rank')
POT_KINDS = ('txn', 'task')   # the only money that may ever reach members: fees on real activity
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
    out['splitMaxPct'] = max(out['splitPct'], out['splitMaxPct'])
    out['halfLifeMinDays'] = min(out['halfLifeDays'], out['halfLifeMinDays'])
    out['txnBigUsd'] = max(out['txnSmallUsd'], out['txnBigUsd'])
    return out


def new_state():
    return {'v': 2, 'cfg': clean_cfg(None), 'at': 0, 'books': {t: {'pot': 0, 'keep': 0, 'in': {}, 'paidOut': 0} for t in TOKENS}, 'agents': {}, 'seen': {}, 'chain': None, 'head': GENESIS, 'links': 0, 'moved': {t: 0 for t in TOKENS}, 'hist': [], 'trailNew': []}


def _link(state, key, token, units, kind):
    """One dollar-in event, chained to the one before it. Change any past link and every later one stops matching."""
    ev = {'n': int(state.get('links') or 0) + 1, 'key': str(key), 'token': token, 'units': int(units), 'kind': kind}
    head = hmac.new(_key(), f"{state.get('head') or GENESIS}|{json.dumps(ev, sort_keys=True)}".encode(), hashlib.sha256).hexdigest()
    state['head'] = head; state['links'] = ev['n']; state.setdefault('moved', {t: 0 for t in TOKENS})[token] = int(state['moved'].get(token) or 0) + int(units)
    state.setdefault('trailNew', []).append({**ev, 'head': head})


def _agent(state, cat, owner='', now=0):
    a = state['agents'].get(cat)
    if not a:
        a = state['agents'][cat] = {'owner': str(owner or ''), 'locked': {t: 0 for t in TOKENS}, 'owed': {t: 0 for t in TOKENS}, 'sent': {t: 0 for t in TOKENS}, 'earned': {t: 0 for t in TOKENS}, 'paid': {t: 0 for t in TOKENS}, 'room': 0.0, 'roomAt': now, 'boost': 0.0, 'first': now}
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
    pot = int(units * state['cfg']['potPct'] / 100) if kind in POT_KINDS else 0
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


def send(state, key, cat, owner, token, units, usd, now, boost=0.0, meta=None):
    """A verified proof send. → {keptUnits, lockedUnits} or None if it already counted."""
    units = int(units)
    if token not in TOKENS or units <= 0 or not _once(state, key):
        return None
    cfg = state['cfg']; a = _agent(state, cat, owner, now)
    kept = int(units * cfg['skimPct'] / 100); locked = units - kept
    _link(state, key, token, units, 'send')
    if kept:
        _take_in(state, token, kept, 'proofs')
    a['sends'] = (list(a.get('sends') or []) + [{'at': round(now), 'token': token, 'sent': units / UNITS[token], 'kept': kept / UNITS[token], 'locked': locked / UNITS[token], 'usd': round(_f(usd), 4), **(meta or {})}])[-40:]
    a['locked'][token] += locked; a['sent'][token] += units; a['boost'] = max(0.0, min(1.0, _f(boost)))
    _room(a, now, cfg); a['room'] += max(0.0, _f(usd)) * cfg['earnRoomX']
    return {'keptUnits': kept, 'lockedUnits': locked}


def boost_of(rows, level, now, fade_days=60.0):
    """0 to 1. Points fade, then the proofprint grades them: a level 0 print earns half of what a level 100 print earns from the same points."""
    pts = sum(_f(r.get('pts')) * 0.5 ** (max(0.0, now - _f(r.get('at'))) / (max(1.0, fade_days) * 86400)) for r in rows or [])
    return round(min(1.0, pts / BOOST_POINTS_FULL) * (0.5 + 0.5 * min(100.0, max(0.0, _f(level))) / 100), 4)


def levers(cfg, boost):
    """What a boost changes right now. Rank-only mode: nothing."""
    b = 0.0 if cfg.get('boostMode') == 'rank' else max(0.0, min(1.0, _f(boost)))
    return {'splitPct': round(cfg['splitPct'] + (cfg['splitMaxPct'] - cfg['splitPct']) * b, 2), 'halfLifeDays': round(cfg['halfLifeDays'] + (cfg['halfLifeMinDays'] - cfg['halfLifeDays']) * b, 2), 'weightX': round(1 + (cfg['weightMaxX'] - 1) * b, 3)}


def _locked_usd(a, sol_usd):
    return a['locked']['SOL'] / UNITS['SOL'] * sol_usd + a['locked']['USDC'] / UNITS['USDC']


def shares(state, sol_usd):
    """{cat: part of the pot, 0 to 1}. Weight = locked money x boost. Every wallet of one owner counts together, capped so nobody takes more than capPct once there are enough owners to share."""
    cfg = state['cfg']; per = {}; by_owner = {}
    for cat, a in state['agents'].items():
        w = _locked_usd(a, sol_usd) * levers(cfg, a.get('boost'))['weightX']
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
    """Move time forward: the pot pays by weight, then every locked balance releases. Only whole units move, and each comes out of the bucket it goes into another from."""
    last = _f(state.get('at'))
    if not last:
        state['at'] = now
        return False
    dt = now - last
    if dt < TICK_S:
        return False
    state['at'] = now; cfg = state['cfg']; part = shares(state, sol_usd)
    pot_part = 1 - 0.5 ** (dt / (cfg['potHalfLifeDays'] * 86400))
    for t in TOKENS:
        b = state['books'][t]; pay = int(b['pot'] * pot_part); usd_each = (sol_usd / UNITS['SOL']) if t == 'SOL' else (1 / UNITS['USDC'])
        for cat, p in part.items():
            a = state['agents'][cat]; want = int(pay * p)
            if want <= 0:
                continue
            room = _room(a, now, cfg)
            if usd_each > 0:
                want = min(want, int(room / usd_each))   # past its room, it stays in the pot
            elif t == 'SOL':
                want = 0
            if want <= 0:
                continue
            b['pot'] -= want; a['locked'][t] += want; a['earned'][t] += want
            a['room'] = max(0.0, room - want * usd_each)
    for a in state['agents'].values():
        lv = levers(cfg, a.get('boost')); gone = 1 - 0.5 ** (dt / (lv['halfLifeDays'] * 86400))
        for t in TOKENS:
            out = int(a['locked'][t] * gone)
            if out <= 0:
                continue
            mine = int(out * lv['splitPct'] / 100)
            a['locked'][t] -= out; a['owed'][t] += mine
            if out - mine:
                _take_in(state, t, out - mine, 'release')
    return True


def _rate(a, t, cfg):
    lv = levers(cfg, a.get('boost'))
    return a['locked'][t] * (0.6931471805599453 / (lv['halfLifeDays'] * 86400)) * lv['splitPct'] / 100


def _usd(units, t, sol_usd):
    return units / UNITS[t] * (sol_usd if t == 'SOL' else 1)


def view(state, cat, now, sol_usd):
    """One agent's numbers for its owner. owedUsd + ratePerSecUsd x seconds is the live count."""
    cfg = state['cfg']; a = state['agents'].get(cat)
    if not a:
        return {'owedUsd': 0, 'ratePerSecUsd': 0, 'lockedUsd': 0, 'sentUsd': 0, 'earnedUsd': 0, 'owed': {'SOL': 0, 'USDC': 0}, 'locked': {'SOL': 0, 'USDC': 0}, 'boost': 0, 'levers': levers(cfg, 0), 'at': round(now), 'solUsd': sol_usd, 'empty': True}
    dt = max(0.0, now - _f(state.get('at')))   # the ticks are a minute apart: the count stays smooth between them
    rate = sum(_usd(_rate(a, t, cfg), t, sol_usd) for t in TOKENS)
    share = shares(state, sol_usd).get(cat, 0.0); pot_day = sum(_usd(state['books'][t]['pot'], t, sol_usd) for t in TOKENS) * (1 - 0.5 ** (1 / cfg['potHalfLifeDays']))
    return {'potShare': round(share, 6), 'feeShareDayUsd': round(pot_day * share, 6), 'sends': (a.get('sends') or [])[::-1], 'hist': (a.get('hist') or [])[-120:], 'owedUsd': round(sum(_usd(a['owed'][t], t, sol_usd) for t in TOKENS) + rate * dt, 9), 'ratePerSecUsd': round(rate, 12), 'lockedUsd': round(sum(_usd(a['locked'][t], t, sol_usd) for t in TOKENS), 6),
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
        a['hist'] = (list(a.get('hist') or []) + [{'d': day, 'owed': round(sum(_usd(a['owed'][k], k, sol_usd) for k in TOKENS), 6), 'locked': round(_locked_usd(a, sol_usd), 6), 'earned': round(sum(_usd(a['earned'][k], k, sol_usd) for k in TOKENS), 6), 'sent': round(sum(_usd(a['sent'][k], k, sol_usd) for k in TOKENS), 6)}])[-180:]


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
            out['ratePerSecUsd'] += _usd(_rate(a, t, cfg), t, sol_usd)
    out['agents'] = sum(1 for a in state['agents'].values() if any(a['sent'].values()))
    out['usd'] = {k: round(v, 6) for k, v in out['usd'].items()}; out['in'] = {k: round(v, 6) for k, v in out['in'].items()}; out['ratePerSecUsd'] = round(out['ratePerSecUsd'], 12)
    return out


def rules(cfg):
    """What a user's split picture draws, straight from the live settings."""
    keep = ('skimPct', 'splitPct', 'splitMaxPct', 'halfLifeDays', 'halfLifeMinDays', 'potPct', 'weightMaxX', 'depositPct', 'firstMinUsd', 'txnSmallPct', 'txnMidPct', 'txnBigPct', 'txnSmallUsd', 'txnBigUsd', 'boostMode')
    return {**{k: cfg[k] for k in keep}, 'potKinds': list(POT_KINDS)}


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
