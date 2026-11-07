"""🧮 THE COLLECTIVE MATHEMATICS AUDITOR (GPT's list, "goes first"). A second set of eyes on the ledger: it recalculates what must be true from the ledger's own events and books, with no shared logic, and it stress tests with fake money. It reads and reports. It never changes the ledger, and it can only raise a problem for its owner.

The laws:
  1. Every unit that came in is somewhere: sends + fees + profit - losses absorbed = what the books and the agents hold, to the unit.
  2. A profit splits exactly: paid + the Collective's piece + compounding = the profit.
  3. No agent is ever paid more than its points allow.
  4. All agents together never take more of a profit than the room the Collective's piece leaves.
  5. The same key never counts twice.
  6. Nothing is ever negative."""
import random

import collective_pool as cp
import collective_stake as sk

UNITS_USD = {'USDC': 1e-6, 'SOL': 150 / 1e9}


def _held(state, t):
    b = state['books'][t]; agents = state['agents'].values()
    owed = sum(int(a['owed'][t]) for a in agents); drip = sum(sk.drip_left(a, t) for a in agents)
    return {'stake': int(b.get('stake') or 0), 'keep': int(b.get('keep') or 0), 'compound': int(b.get('compound') or 0), 'pot': int(b.get('pot') or 0), 'owed': owed, 'drip': drip, 'paidOut': int(b.get('paidOut') or 0)}


def laws(state, tape=None, tol_usd=1e-4):
    """Checks a ledger, and a tape of what happened when one is given. → [problem, in words]; empty means it all adds up."""
    bad = []
    for t in cp.TOKENS:
        h = _held(state, t)
        for k, v in h.items():
            if v < 0:
                bad.append(f'{t} {k} is negative: {v}')
        if tape:
            came = tape['in'][t] - tape['lost'][t]; have = sum(h.values())
            if came != have:
                bad.append(f'{t} does not add up: {came} came in after losses, the books hold {have} ({h})')
    for c, a in state['agents'].items():
        s = sk.of(a); over = s['paidUsd'] + float(a.get('burned') or 0) - s['capUsd']   # worked out here: its own points left stops at zero, so it could never show an overpayment
        if over > tol_usd:
            bad.append(f'{c} was paid past its points by {over:.6f}')
        for t in cp.TOKENS:
            if int(a['owed'][t]) < 0 or sk.drip_left(a, t) < 0:
                bad.append(f'{c} holds a negative balance in {t}')
    return bad


def _new(n, seed, cfg=None):
    st = cp.new_state(); st['cfg'] = cp.clean_cfg({**st['cfg'], 'deal': 'stake', **(cfg or {})}); st['deal'] = 'stake'; return st, random.Random(seed), {'in': {t: 0 for t in cp.TOKENS}, 'lost': {t: 0 for t in cp.TOKENS}}


def _send(st, tape, key, cat, owner, token, usd, now, grade):
    units = max(1, int(usd / UNITS_USD[token])); got = cp.send(st, key, cat, owner, token, units, usd, now)
    if got:
        tape['in'][token] += units; rows = st['agents'][cat]['streams']; rows[-1]['grade'] = grade; rows[-1]['x'] = sk.x_of(grade); rows[-1]['points'] = usd * sk.x_of(grade)
    return got


def stress(n=1000, rounds=200, seed=7, sends=True, profit=True, losses=True, dust=False, stale=False):
    """Fake money through the real ledger functions, many ways. → {problems, sent, profit, paid, ...}"""
    st, r, tape = _new(n, seed); bad = []; now = 1_000_000.0; paid_total = 0; split_checks = 0
    cats = [(f'a{i}', f'o{i % max(1, n // 2)}') for i in range(n)]
    if sends:
        for i, (c, o) in enumerate(cats):
            t = 'USDC' if r.random() < 0.7 else 'SOL'; usd = 0.000001 if dust else r.choice((1, 5, 10, 100, 1000, 10000)) * r.random() + 0.01
            _send(st, tape, f's{i}', c, o, t, usd, now, r.uniform(100, 300))
    for k in range(rounds):
        now += 3600; t = r.choice(cp.TOKENS); unit = UNITS_USD[t] * (r.uniform(0.2, 5) if stale else 1); roll = r.random()
        if profit and roll < 0.6:
            units = r.choice((1, 3, 999, 10 ** 6, 10 ** 9, r.randrange(1, 10 ** 10)))
            before = {c: sk.of(a)['pointsLeft'] for c, a in st['agents'].items()}; got = sk.pay_profit(st, f'p{k}', t, units, unit, now)
            if got:
                tape['in'][t] += units; split_checks += 1; paid_total += got['paidUnits']
                if got['paidUnits'] + got['collectiveUnits'] + got['compoundUnits'] != units:
                    bad.append(f'profit {k} did not split exactly: {got} of {units}')
                if min(got['paidUnits'], got['collectiveUnits'], got['compoundUnits']) < 0:
                    bad.append(f'profit {k} had a negative part: {got}')
                room = 1 - st['cfg']['collectivePoolPct'] / 100
                if got['paidUnits'] > units * room + len(st['agents']):
                    bad.append(f'profit {k}: agents took {got["paidUnits"]} of {units}, past the room')
                for c, a in st['agents'].items():
                    if sk.of(a)['pointsLeft'] > before.get(c, 0) + 1e-6:
                        bad.append(f'profit {k}: {c} gained points'); break
        elif losses and roll < 0.8:
            b = st['books'][t]; units = r.choice((1, 10 ** 6, 10 ** 9)); had = int(b.get('compound') or 0) + int(b.get('stake') or 0)
            if sk.pool_loss(st, f'l{k}', t, units):
                tape['lost'][t] += min(units, had)
        else:
            sk.release(st, now)
        if k % 25 == 0:
            bad += laws(st, tape)
            if bad:
                break
    again = cp.send(st, 's0', 'a0', 'o0', 'USDC', 10, 1.0, now) if sends else None
    if again:
        bad.append('the same send counted twice')
    sk.release(st, now + 400 * 86400)
    bad += laws(st, tape)
    return {'problems': bad[:20], 'agents': len(st['agents']), 'rounds': rounds, 'splits': split_checks, 'paidUnits': paid_total, 'in': tape['in'], 'lost': tape['lost'], 'cap': st['cfg'].get('walletCapPct')}


def suite(n=1000):
    """Every hard case named in the capability list."""
    return {'1000 agents, mixed': stress(n), 'zero profit': stress(n, 60, 8, profit=False), 'only losses': stress(200, 200, 9, profit=False), 'no sends, only profit': stress(10, 100, 10, sends=False), 'dust amounts': stress(300, 100, 11, dust=True), 'stale prices': stress(300, 200, 12, stale=True), 'one agent': stress(1, 300, 13)}
