"""🪙 THE STAKE DEAL (owner 2026-11-06, replaces the bank deal; cfg deal='stake').
The Collective earns from the jump: every agent wallet fee and top-up is its own. A proof send is not income: it is a stake in the owner's auto-ranged yield pools.
A send is scored by the Collective (owner 2026-11-06). The base top score is 300, and only a flawless proof reaches it. Its boost is its score over 100: $5 at 300 is 3x, so it may earn up to $15 back, paid ONLY from real pool profit, never from what anyone staked. A score under 100 still counts as 1x.
The top score grows with the pot: 500 when the pot reaches tier500Usd, 750 at tier750Usd, 1000 at tier1000Usd. A bigger pot can afford more, so payouts also get faster: a profit releases over dripDays at 300, half that at 500, a quarter at 750, and at 1000 it lands at once.
Its cut is its boost times its size (owner 2026-11-06, "weigh by dollars, but the % gets smaller after 1k so their rank don't eat up the others"): $10 is 1x, $100 2x, $1,000 3x. Past kneeUsd each 10x adds only sizeAbovePct of a step: $10,000 3.5x, $100,000 4x.
BOOST POINTS = the value its proofs and dollars hold: what they may still earn, less what was paid, less what was burned. Burn them to run at a bigger seat. BOOST CASH = the rewards counting live: a real profit, once it lands, releases to the agent second by second over dripDays, so the count is money that already exists.
Fast compound: burn points to run at the highest cut anyone holds for a while. The extra comes only from room nobody else holds, so no other agent's cut ever shrinks.
Every profit splits three ways: agents' cuts, the Collective's piece, and the rest stays compounding in the pools. Agents can never take the Collective's piece.
Pure: every function takes the ledger state. Real money only enters through a chain-verified transaction, in the endpoint that calls pay_profit."""
import math
import uuid

GRADE_BASE = 300.0     # the top score until the pot grows. Flawless only
GRADE_MAX = 1000.0
SEATS_PART = 0.6       # all five checks passing are this much of the top score; the rest is its print's real strength
PLATFORMS = ('raydium', 'meteora', 'orca', 'other')
MAX_POOLS = 40


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def grade_of(review, strength, top=GRADE_BASE, mech=None):
    """0 to today's top score, from the record: how many of the five checks passed, then this proof's own weights (proof_weights), with its agent's print counting a little. Only all five, a full record and a full print reach the top. Without weights it falls back to the checks and the print."""
    seats = (review or {}).get('seats') or []
    passed = sum(1 for s in seats if s.get('ok')) / max(1, len(seats)); print_part = min(100.0, max(0.0, _f(strength))) / 100
    if mech is not None:
        return round(min(top, max(0.0, passed * (0.8 * max(0.0, min(1.0, _f(mech))) + 0.2 * print_part) * top)), 1)
    return round(min(top, max(0.0, (passed * SEATS_PART + print_part * (1 - SEATS_PART)) * top)), 1)


def x_of(grade):
    """Score 300 → 3x: the most it can ever earn, as a multiple of what it sent. Under 100, or no score, counts as 1x."""
    return round(max(1.0, min(GRADE_MAX, _f(grade)) / 100), 4)


def ladder(cfg):
    """The score range as the pot grows. → [{pot, top, drip}], where drip is the days a profit takes to release, and 0 is at once."""
    days = _f(cfg.get('dripDays')) or 7.0
    return [{'pot': 0.0, 'top': 300, 'drip': days}, {'pot': _f(cfg.get('tier500Usd')) or 10000.0, 'top': 500, 'drip': round(days / 2, 2)}, {'pot': _f(cfg.get('tier750Usd')) or 100000.0, 'top': 750, 'drip': round(days / 4, 2)}, {'pot': _f(cfg.get('tier1000Usd')) or 1000000.0, 'top': 1000, 'drip': 0.0}]


def rung(state, sol_usd=0.0):
    """Where the Collective stands today. The pot is what it really holds: stakes, what it kept, and what is compounding."""
    t = totals(state, sol_usd); pot = t['stakedUsd'] + t['keepUsd'] + t['compoundUsd']; rows = ladder(state['cfg']); now = rows[0]
    for r in rows:
        if pot >= r['pot']:
            now = r
    return {'potUsd': round(pot, 2), 'top': now['top'], 'drip': now['drip'], 'ladder': rows}


def set_score(state, cat, stream_id, score, by, why, now, sol_usd=0.0, owner=False):
    """The minds' deep read, or the owner's word. It moves no money, only how much a proof may earn. The minds never overrule the owner. → the stream, or None."""
    row = next((r for r in ((state['agents'].get(cat) or {}).get('streams') or []) if r.get('id') == stream_id), None)
    if not row or (row.get('ownerScored') and not owner):
        return None
    top = rung(state, sol_usd)['top']; val = round(max(0.0, min(float(top), _f(score))), 1)
    row['scored'] = (list(row.get('scored') or []) + [{'by': str(by)[:24], 'score': val, 'was': row.get('grade'), 'why': str(why or '')[:240], 'at': round(now), 'top': top}])[-20:]
    row['grade'] = val
    if owner:
        row['ownerScored'] = True
    return row


def size_of(cfg, usd):
    """How much its dollars lift its cut. Past the knee each 10x adds only part of a step, so size never crowds others out."""
    usd = _f(usd)
    if usd <= 0:
        return 0.0
    knee = max(10.0, _f(cfg.get('kneeUsd')) or 1000.0)
    return round(max(0.25, 1 + math.log10(min(usd, knee) / 10)) + (math.log10(usd / knee) * _f(cfg.get('sizeAbovePct', 50)) / 100 if usd > knee else 0.0), 4)


def of(agent, least=0.0):
    """One agent's standing, always worked out from its sends so a cleared or held proof can never leave it out of step. A send under the owner's smallest stake counts as sent and earns no points. → {sentUsd, capUsd, x, grade, paidUsd, burned, pointsLeft}"""
    a = agent or {}; sent = cap = weighted = 0.0
    for r in a.get('streams') or []:
        usd = _f(r.get('usd')); sent += usd
        if not r.get('held') and usd >= _f(r.get('least') or 0):
            g = _f(r.get('grade')); cap += usd * x_of(g); weighted += usd * g
    counted = sum(_f(r.get('usd')) for r in a.get('streams') or [] if not r.get('held'))
    paid = _f(a.get('paidUsd')); burned = _f(a.get('burned'))
    return {'countedUsd': round(counted, 4), 'sentUsd': round(sent, 4), 'capUsd': round(cap, 4), 'x': round(cap / counted, 4) if counted else 0.0, 'grade': round(weighted / counted, 1) if counted else 0.0, 'paidUsd': round(paid, 6), 'burned': round(burned, 4), 'pointsLeft': round(max(0.0, cap - paid - burned), 4)}


def cuts(state, now):
    """{agent: {base, fast, total}} as parts of a whole profit. Agents together stay under what the Collective's piece leaves. Too many agents scale down evenly. Fast only spends room nobody holds. A wallet's agents share walletCapPct, so splitting into many agents gains nothing."""
    cfg = state['cfg']; base = {}; owners = {}
    for c, a in state['agents'].items():
        s = of(a)
        if s['pointsLeft'] > 0:
            base[c] = s['x'] * size_of(cfg, s['countedUsd']) * cfg['cutPerX'] / 100; owners.setdefault(a.get('owner') or c, []).append(c)
    cap = cfg['walletCapPct'] / 100
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


def _pay_cuts(state, token, units, unit_usd, table, now=0, drip=False):
    """Each agent's cut of units, up to its points. Paying takes its points now. A profit then releases second by second; paying early lands at once. → whole units paid."""
    paid = 0; drip_days = _f(state['cfg'].get('dripDays'))
    if drip:   # a bigger pot pays faster, and at the top it lands at once
        drip_days = rung(state, state.get('solUsd') or 0.0)['drip']; drip = drip_days > 0
    for c, part in table.items():
        a = state['agents'][c]; want = min(int(units * part), int(of(a)['pointsLeft'] / unit_usd))
        if want > 0:
            a['paidUsd'] = round(_f(a.get('paidUsd')) + want * unit_usd, 6); paid += want
            if drip:
                release(state, now, c)
                row = a.setdefault('drip', {}).setdefault(token, {'left': 0, 'rate': 0.0, 'at': now}); row['left'] += want; row['rate'] = row['left'] / max(1.0, drip_days * 86400)
            else:
                a['owed'][token] += want; a['earned'][token] += want
    return paid


def release(state, now, only=None):
    """Boost cash: moves what a profit already paid into an agent's earnings as time passes. Whole units only, and never while payouts are stopped."""
    if state.get('payPaused'):
        for a in state['agents'].values():
            for row in (a.get('drip') or {}).values():
                row['at'] = now
        return
    for c, a in state['agents'].items():
        if only and c != only:
            continue
        for t, row in (a.get('drip') or {}).items():
            n = min(int(row['left']), int(row['rate'] * max(0.0, now - _f(row['at']))))
            if n > 0:
                row['left'] -= n; a['owed'][t] += n; a['earned'][t] += n; row['at'] = _f(row['at']) + n / row['rate'] if row['left'] else now


def drip_rate(state, agent, token):
    """Whole units a second it is earning right now."""
    row = ((agent or {}).get('drip') or {}).get(token) or {}
    return 0.0 if state.get('payPaused') or not row.get('left') else _f(row.get('rate'))


def drip_left(agent, token):
    return int((((agent or {}).get('drip') or {}).get(token) or {}).get('left') or 0)


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
    paid = _pay_cuts(state, token, units, unit_usd, {c: v['total'] for c, v in table.items()}, now, True); n = sum(1 for c in table)
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


def add_pool(state, platform, pair, address, note, now, mint=''):
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
    row = {'id': uuid.uuid4().hex[:10], 'platform': platform, 'pair': pair, 'address': address, 'note': str(note or '').strip()[:160], 'mint': str(mint or '').strip()[:64], 'at': round(now), 'on': True, 'profitUsd': 0.0}
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
    for k in ('bandLow', 'bandHigh'):
        if k in patch:
            row[k] = max(0.0, _f(patch[k]))
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
    a = state['agents'].get(cat) or {}; s = of(a); s['size'] = size_of(state['cfg'], s['countedUsd']); table = cuts(state, now); me = table.get(cat, {'base': 0.0, 'fast': 0.0, 'total': 0.0}); until = _f(a.get('fastUntil'))
    return {**s, 'cutPct': round(me['base'] * 100, 4), 'fastPct': round(me['fast'] * 100, 4), 'nowPct': round(me['total'] * 100, 4), 'topPct': round(max((v['base'] for v in table.values()), default=0.0) * 100, 4), 'fastUntil': round(until) if until > now else None}


def owner_view(state, sol_usd, now):
    """Everything the owner's folders read."""
    return {'stake': totals(state, sol_usd), 'pools': state.get('pools') or [], 'stakeAgents': agents_table(state, now)[:40], 'payLog': (state.get('payLog') or [])[::-1][:30], 'payPaused': bool(state.get('payPaused')), 'stops': stop_hits(state)}


def public_pools(state):
    """The pools every member can see. Names and results, no notes."""
    return [{k: p.get(k) for k in ('id', 'platform', 'pair', 'address', 'on', 'profitUsd', 'targetPct')} for p in state.get('pools') or []]


def totals(state, sol_usd):
    """The owner's big numbers."""
    import collective_pool as cp
    usd = lambda k: round(sum(cp._usd(int(state['books'][t].get(k) or 0), t, sol_usd) for t in cp.TOKENS), 6)
    return {'stakedUsd': usd('stake'), 'compoundUsd': usd('compound'), 'keepUsd': usd('keep'), 'profitUsd': round(_f(state.get('profitUsd')), 6), 'paidUsd': round(_f(state.get('stakePaidUsd')), 6), 'profitToKeepUsd': round(_f(state.get('profitToKeepUsd')), 6)}


def agents_table(state, now):
    table = cuts(state, now); rows = []
    for c, a in state['agents'].items():
        s = of(a); me = table.get(c, {'base': 0.0, 'fast': 0.0, 'total': 0.0})
        rows.append({'id': c, 'name': a.get('name') or c, 'bonusUsd': _f(a.get('bonusUsd')), 'size': size_of(state['cfg'], s['countedUsd']), **s, 'cutPct': round(me['base'] * 100, 4), 'nowPct': round(me['total'] * 100, 4), 'fast': _f(a.get('fastUntil')) > now})
    rows.sort(key=lambda r: -r['nowPct'])
    return rows
