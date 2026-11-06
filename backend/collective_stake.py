"""🪙 THE STAKE DEAL (owner 2026-11-06, replaces the bank deal; cfg deal='stake').
The Collective earns from the jump: every agent wallet fee and top-up is its own. A proof send is not income: it is a stake in the owner's auto-ranged yield pools.
A send is graded 0 to 100. Its boost is 1 + grade/100, so $10 at grade 87 is 1.87x: it may earn up to $18.70 back, paid ONLY from real pool profit, never from what anyone staked.
An agent's boost is also its cut: 1.87x means 1.87% of every pool profit, until its points run out. Points = dollars it may still earn: what its graded sends allow, less what it was paid, less what it burned.
Fast compound: burn points to run at the highest cut anyone holds for a while. The extra comes only from room nobody else holds, so no other agent's cut ever shrinks.
Every profit splits three ways: agents' cuts, the Collective's piece, and the rest stays compounding in the pools. Agents can never take the Collective's piece.
Pure: every function takes the ledger state. Real money only enters through a chain-verified transaction, in the endpoint that calls pay_profit."""
import uuid

GRADE_SEATS_PTS = 60.0   # all five validators passing is worth this much of the 100
PLATFORMS = ('raydium', 'meteora', 'orca', 'other')
MAX_POOLS = 40


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def grade_of(review, strength):
    """0 to 100, from the record: how many of the five validators passed, plus its print's real strength. A held proof grades 0 until the owner clears it."""
    seats = (review or {}).get('seats') or []
    passed = sum(1 for s in seats if s.get('ok')) / max(1, len(seats))
    return round(min(100.0, max(0.0, passed * GRADE_SEATS_PTS + min(100.0, max(0.0, _f(strength))) * (100 - GRADE_SEATS_PTS) / 100)), 1)


def x_of(grade):
    """Grade 87 → 1.87x. An older send with no grade counts as 1x."""
    return round(1 + min(100.0, max(0.0, _f(grade))) / 100, 4)


def of(agent, least=0.0):
    """One agent's standing, always worked out from its sends so a cleared or held proof can never leave it out of step. A send under the owner's smallest stake counts as sent and earns no points. → {sentUsd, capUsd, x, grade, paidUsd, burned, pointsLeft}"""
    a = agent or {}; sent = cap = weighted = 0.0
    for r in a.get('streams') or []:
        usd = _f(r.get('usd')); sent += usd
        if not r.get('held') and usd >= _f(r.get('least') or 0):
            g = _f(r.get('grade')); cap += usd * x_of(g); weighted += usd * g
    counted = sum(_f(r.get('usd')) for r in a.get('streams') or [] if not r.get('held'))
    paid = _f(a.get('paidUsd')); burned = _f(a.get('burned'))
    return {'sentUsd': round(sent, 4), 'capUsd': round(cap, 4), 'x': round(cap / counted, 4) if counted else 0.0, 'grade': round(weighted / counted, 1) if counted else 0.0, 'paidUsd': round(paid, 6), 'burned': round(burned, 4), 'pointsLeft': round(max(0.0, cap - paid - burned), 4)}


def cuts(state, now):
    """{agent: {base, fast, total}} as parts of a whole profit. Agents together stay under what the Collective's piece leaves. Too many agents scale down evenly. Fast only spends room nobody holds. A wallet's agents share capPct, so splitting into many agents gains nothing."""
    cfg = state['cfg']; base = {}; owners = {}
    for c, a in state['agents'].items():
        s = of(a)
        if s['pointsLeft'] > 0:
            base[c] = s['x'] * cfg['cutPerX'] / 100; owners.setdefault(a.get('owner') or c, []).append(c)
    cap = cfg['capPct'] / 100
    for rows in owners.values():
        total = sum(base[c] for c in rows)
        if total > cap:
            for c in rows:
                base[c] *= cap / total
    room = max(0.0, 1 - cfg['collectivePoolPct'] / 100); total = sum(base.values()); scale = min(1.0, room / total) if total else 1.0
    final = {c: v * scale for c, v in base.items()}; top = max(final.values(), default=0.0); free = max(0.0, room - sum(final.values()))
    want = {c: top - v for c, v in final.items() if _f(state['agents'][c].get('fastUntil')) > now and top > v}
    wanted = sum(want.values()); give = min(1.0, free / wanted) if wanted else 0.0
    return {c: {'base': round(v, 8), 'fast': round(want.get(c, 0.0) * give, 8), 'total': round(v + want.get(c, 0.0) * give, 8)} for c, v in final.items()}


def _pay_cuts(state, token, units, unit_usd, table):
    """Each agent's cut of units, up to its points. → whole units paid."""
    paid = 0
    for c, part in table.items():
        a = state['agents'][c]; want = min(int(units * part), int(of(a)['pointsLeft'] / unit_usd))
        if want > 0:
            a['owed'][token] += want; a['earned'][token] += want; a['paidUsd'] = round(_f(a.get('paidUsd')) + want * unit_usd, 6); paid += want
    return paid


def _log(state, row):
    state['payLog'] = (list(state.get('payLog') or []) + [row])[-200:]


def pay_early(state, key, source, token, units, unit_usd, now):
    """The owner pays agents sooner, from money that is already profit or the Collective's own: what compounded, or what it earned. Shared by each agent's cut, up to its points. A stake can never be spent here. → {paidUnits, agents} or None. Raises ValueError."""
    import collective_pool as cp
    units = int(units); unit_usd = _f(unit_usd)
    if source not in ('compound', 'keep'):
        raise ValueError('Pay from what compounded, or what the Collective earned.')
    b = (state['books'].get(token) or {})
    if token not in cp.TOKENS or units <= 0 or unit_usd <= 0:
        raise ValueError('Pick an amount.')
    if units > int(b.get(source) or 0):
        raise ValueError('There is not that much in it.')
    table = cuts(state, now); total = sum(v['total'] for v in table.values())
    if not total:
        raise ValueError('No agent has points to pay.')
    if not cp._once(state, key):
        return None
    paid = _pay_cuts(state, token, units, unit_usd, {c: v['total'] / total for c, v in table.items()})
    b[source] = int(b.get(source) or 0) - paid; state['stakePaidUsd'] = round(_f(state.get('stakePaidUsd')) + paid * unit_usd, 6)
    cp._link(state, key, token, paid, 'early'); _log(state, {'at': round(now), 'kind': 'early', 'source': source, 'usd': round(paid * unit_usd, 6)})
    return {'paidUnits': paid, 'agents': sum(1 for v in table if v)}


def bonus(state, key, cat, token, units, unit_usd, why, now):
    """A gift from what the Collective earned to one agent. It takes no points, because it is not its cut. Never from a stake. → {paidUnits} or None. Raises ValueError."""
    import collective_pool as cp
    units = int(units); unit_usd = _f(unit_usd); a = state['agents'].get(cat); b = state['books'].get(token) or {}
    if not a or token not in cp.TOKENS or units <= 0 or unit_usd <= 0:
        raise ValueError('Pick an agent and an amount.')
    if units > int(b.get('keep') or 0):
        raise ValueError('The Collective has not earned that much.')
    if not cp._once(state, key):
        return None
    b['keep'] -= units; a['owed'][token] += units; a['earned'][token] += units; a['bonusUsd'] = round(_f(a.get('bonusUsd')) + units * unit_usd, 6)
    cp._link(state, key, token, units, 'bonus'); _log(state, {'at': round(now), 'kind': 'bonus', 'cat': cat, 'name': a.get('name') or cat, 'usd': round(units * unit_usd, 6), 'why': str(why or '')[:120]})
    return {'paidUnits': units}


def pay_profit(state, key, token, units, unit_usd, now, pool_id=''):
    """A real pool profit, once. Each agent is paid its cut up to its points; the Collective takes its piece; the rest stays compounding. → {paidUnits, collectiveUnits, compoundUnits, agents} or None when it already counted."""
    import collective_pool as cp
    units = int(units); unit_usd = _f(unit_usd)
    if token not in cp.TOKENS or units <= 0 or unit_usd <= 0 or not cp._once(state, key):
        return None
    cp._link(state, key, token, units, 'profit'); b = state['books'][token]; b['in']['profit'] = int(b['in'].get('profit') or 0) + units; table = {} if state.get('payPaused') else cuts(state, now)
    paid = _pay_cuts(state, token, units, unit_usd, {c: v['total'] for c, v in table.items()}); n = sum(1 for c in table)
    mine = min(int(units * state['cfg']['collectivePoolPct'] / 100), units - paid); rest = units - paid - mine
    b['keep'] += mine; b['compound'] = int(b.get('compound') or 0) + rest; state['stakePaidUsd'] = round(_f(state.get('stakePaidUsd')) + paid * unit_usd, 6); state['profitUsd'] = round(_f(state.get('profitUsd')) + units * unit_usd, 6); state['profitToKeepUsd'] = round(_f(state.get('profitToKeepUsd')) + mine * unit_usd, 6)
    row = next((p for p in state.get('pools') or [] if p.get('id') == pool_id), None)
    if row:
        row['profitUsd'] = round(_f(row.get('profitUsd')) + units * unit_usd, 6)
    return {'paidUnits': paid, 'collectiveUnits': mine, 'compoundUnits': rest, 'agents': n}


def pool_loss(state, key, token, units):
    """A real pool loss, once: off what compounded, then off the stake. Nobody's points change, and nothing is promised back."""
    import collective_pool as cp
    units = abs(int(units))
    if token not in cp.TOKENS or not units or not cp._once(state, key):
        return False
    cp._link(state, key, token, -units, 'loss'); b = state['books'][token]; hit = min(int(b.get('compound') or 0), units); b['compound'] = int(b.get('compound') or 0) - hit; b['stake'] = max(0, int(b.get('stake') or 0) - (units - hit)); b['in']['loss'] = int(b['in'].get('loss') or 0) + units
    return True


def fast_price(cfg, days):
    return round(max(0.0, _f(days)) * cfg['fastPtsPerDay'], 4)


def buy_fast(state, cat, days, now):
    """Burn points for days at the top cut. Time stacks up to fastMaxDays ahead. Burned points lower what it can ever earn: that is the trade. → {days, burned, until}. Raises ValueError."""
    a = state['agents'].get(cat); cfg = state['cfg']; days = _f(days)
    if not a or days <= 0:
        raise ValueError('Pick how long.')
    start = max(now, _f(a.get('fastUntil'))); until = min(now + cfg['fastMaxDays'] * 86400, start + days * 86400); got = (until - start) / 86400
    if got <= 0:
        raise ValueError(f"It already has the most fast time, {cfg['fastMaxDays']:g} days.")
    cost = fast_price(cfg, got)
    if cost > of(a)['pointsLeft'] + 1e-9:
        raise ValueError('It does not have that many points.')
    a['burned'] = round(_f(a.get('burned')) + cost, 4); a['fastUntil'] = round(until)
    return {'days': round(got, 3), 'burned': cost, 'until': round(until)}


def add_pool(state, platform, pair, address, note, now):
    """One pool the owner opened. It holds a label and an address: it moves nothing. → the row. Raises ValueError."""
    rows = state.setdefault('pools', [])
    if platform not in PLATFORMS:
        raise ValueError('Pick the platform.')
    pair = str(pair or '').strip()[:32]; address = str(address or '').strip()[:64]
    if not pair:
        raise ValueError('Name the pair.')
    if address and any(p.get('address') == address for p in rows):
        raise ValueError('That pool is already listed.')
    if len(rows) >= MAX_POOLS:
        raise ValueError('That is the most pools it can list.')
    row = {'id': uuid.uuid4().hex[:10], 'platform': platform, 'pair': pair, 'address': address, 'note': str(note or '').strip()[:160], 'at': round(now), 'on': True, 'profitUsd': 0.0}
    rows.append(row)
    return row


def set_pool(state, pool_id, patch):
    """Open or closed, its target part of the plan, and its stop. A target stays inside spotMaxPct, and every target plus the reserve stays inside 100."""
    row = next((p for p in state.get('pools') or [] if p.get('id') == pool_id), None)
    if not row:
        raise ValueError('No pool like that.')
    patch = patch if isinstance(patch, dict) else {'on': patch}; cfg = state['cfg']
    if 'on' in patch:
        row['on'] = bool(patch['on'])
    if 'stopPct' in patch:
        row['stopPct'] = round(min(100.0, max(0.0, _f(patch['stopPct']))), 2)
    if 'lossUsd' in patch:
        row['lossUsd'] = round(max(0.0, _f(patch['lossUsd'])), 6)
    if 'inUsd' in patch:
        row['inUsd'] = round(max(0.0, _f(patch['inUsd'])), 6)
    if 'targetPct' in patch:
        want = _f(patch['targetPct']); others = sum(_f(p.get('targetPct')) for p in state.get('pools') or [] if p is not row)
        if want > cfg['spotMaxPct']:
            raise ValueError(f"No spot may hold over {cfg['spotMaxPct']:g}%. Change that in Safety.")
        if want + others + cfg['reservePct'] > 100:
            raise ValueError(f"That leaves under the {cfg['reservePct']:g}% reserve.")
        row['targetPct'] = round(max(0.0, want), 2)
    return row


def stop_hits(state):
    """Pools past the loss the owner set. It only warns: nothing here can move money."""
    return [p['id'] for p in state.get('pools') or [] if _f(p.get('stopPct')) and _f(p.get('inUsd')) and _f(p.get('lossUsd')) / _f(p['inUsd']) * 100 >= _f(p['stopPct'])]


def view(state, cat, now):
    """What its owner sees. Every number comes from the ledger."""
    a = state['agents'].get(cat) or {}; s = of(a); table = cuts(state, now); me = table.get(cat, {'base': 0.0, 'fast': 0.0, 'total': 0.0}); until = _f(a.get('fastUntil'))
    return {**s, 'cutPct': round(me['base'] * 100, 4), 'fastPct': round(me['fast'] * 100, 4), 'nowPct': round(me['total'] * 100, 4), 'topPct': round(max((v['base'] for v in table.values()), default=0.0) * 100, 4), 'fastUntil': round(until) if until > now else None}


def owner_view(state, sol_usd, now):
    """Everything the owner's folders read."""
    return {'stake': totals(state, sol_usd), 'pools': state.get('pools') or [], 'stakeAgents': agents_table(state, now)[:40], 'payLog': (state.get('payLog') or [])[::-1][:30], 'payPaused': bool(state.get('payPaused')), 'stops': stop_hits(state)}


def public_pools(state):
    """The pools every member can see. Names and results, no notes."""
    return [{k: p.get(k) for k in ('id', 'platform', 'pair', 'address', 'on', 'profitUsd')} for p in state.get('pools') or []]


def totals(state, sol_usd):
    """The owner's big numbers."""
    import collective_pool as cp
    usd = lambda k: round(sum(cp._usd(int(state['books'][t].get(k) or 0), t, sol_usd) for t in cp.TOKENS), 6)
    return {'stakedUsd': usd('stake'), 'compoundUsd': usd('compound'), 'keepUsd': usd('keep'), 'profitUsd': round(_f(state.get('profitUsd')), 6), 'paidUsd': round(_f(state.get('stakePaidUsd')), 6), 'profitToKeepUsd': round(_f(state.get('profitToKeepUsd')), 6)}


def agents_table(state, now):
    table = cuts(state, now); rows = []
    for c, a in state['agents'].items():
        s = of(a); me = table.get(c, {'base': 0.0, 'fast': 0.0, 'total': 0.0})
        rows.append({'id': c, 'name': a.get('name') or c, 'bonusUsd': _f(a.get('bonusUsd')), **s, 'cutPct': round(me['base'] * 100, 4), 'nowPct': round(me['total'] * 100, 4), 'fast': _f(a.get('fastUntil')) > now})
    rows.sort(key=lambda r: -r['nowPct'])
    return rows
