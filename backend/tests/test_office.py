import asyncio
import itertools
import json

import pytest

import agents as ag
import arena_prime as ap
import office as of


def row(m, px=1.0, **k):
    return {'mint': m, 'symbol': m, 'pairAddress': 'P' + m, 'price': px, 'vol5m': 20_000, 'vol1h': 80_000, 'buyShare': 64, 'liq': 60_000,
            'ageH': 8, 'chg1h': 30, 'safe': True, 'tv': {'call': ['🔥', 'SEND IT', 'good'], 'rug': 10}, **k}


def passes(rows_at, wfn=None, st=None, n=4):
    st = st or {}
    table = []
    for i in range(n):
        st, table = ag.desk(st, rows_at(i), 1000 + i * 60, weather_fn=wfn)
    return st, table


def leg(m, entry=1.0, units=1.0, at=1, **k):
    return {'mint': m, 'symbol': m, 'pairAddress': 'P' + m, 'entry': entry, 'units': units, 'at': at, 'liq': 60_000, 'liqNow': 60_000, 'bought': {'tag': '🤖 agents GO'}, **k}


def trow(m, lean=2.0, call='enter', d5=1.0, buy=60, **v):
    return {'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': 1.0, 'why': {'lean': lean, 'drivers': []}, 'trigger': [call, ''], 'devil': ['agree', ''], 'case': ['agree', ''],
            'nums': {'d5': d5, 'buy': buy, 'liq': 60_000, 'pts': 5}, 'vitals': {'safe': True, 'ageH': 8, 'liq': 60_000, 'top10': 15, 'rug': 10, **v}, 'go': call == 'enter'}


# ── 🌦 Weather ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_weather_reads_a_regime_from_measured_inputs_and_says_what_it_could_not_measure():
    nums = lambda d5, liq=80_000: {f'm{i}': {'d5': d5 if i % 4 else -d5, 'liq': liq, 'buy': 60} for i in range(40)}
    rows = [{'mint': f'm{i}', 'ageH': 3, 'safe': True} for i in range(40)]
    w = of.weather(nums(2.0), rows, {}, 10_000)
    assert w['regime'] == 'HOT' and w['mods'] == {'barAdj': -0.25, 'size': 1.0} and w['inputs']['greenPct'] == 75
    assert 'rugPct' in w['missing'] and 0 < w['confidence'] < 1                              # no judged calls yet: said, and confidence is lower
    assert of.weather(nums(-2.0), rows, {}, 10_000)['regime'] == 'CHOP'                      # most of the board red
    assert of.weather(nums(2.0, 12_000), rows, {}, 10_000)['regime'] == 'THIN'               # shallow pools
    assert of.weather({}, [], {}, 10_000)['regime'] == 'THIN'                                # nothing read = never judged as fine
    rugged = {'done': [{'at': 9_000, 'p5': -80.0, 'p60': -100.0, 'kind': 'enter'}] * 4 + [{'at': 9_000, 'p5': 1.0, 'p60': 2.0, 'kind': 'wait'}] * 10}
    h = of.weather(nums(2.0), rows, rugged, 10_000)
    assert h['regime'] == 'HOSTILE' and h['mods'] == {'barAdj': 1.0, 'size': 0.25} and 'rugged' in h['why'][0]
    assert of.weather(nums(2.0), rows, {}, 10_000, 'BAD')['regime'] == 'HOSTILE'             # the courier's health is an input


def test_weather_can_move_triggers_bar_only_inside_its_range_and_can_never_remove_a_hard_gate():
    forged = lambda *_: {'regime': 'HOT', 'adj': -99.0, 'mods': {'barAdj': -99.0, 'size': 9.0}}   # a Weather object trying to throw the gates open
    assert of.weather_adj(forged()) == of.WEATHER_BAR_RANGE[0] and of.weather_size(forged()) == 1.0
    wfn = lambda nums, rows, st, now: (lambda w: {**w, 'adj': of.weather_adj(w)})(forged())
    bad = lambda i: [row('SCAN', 1 + i * .01, safe=False), row('THIN', 1 + i * .01, liq=9_000), row('TOP', 1 + i * .3), row('RUG', 1 + i * .01, tv={'call': ['', 'SEND IT', ''], 'rug': 80}),
                     row('NEW', 1 + i * .01, safe=None)] + [row(f'ok{j}', 1 + i * .005) for j in range(12)]
    st, table = passes(bad, wfn)
    by = {x['mint']: x for x in table}
    assert by['SCAN']['trigger'][0] == 'skip' and by['THIN']['trigger'][0] == 'skip' and by['TOP']['trigger'][0] == 'skip'   # Trigger's hard SKIPs stand
    assert not by['RUG']['go'] and not by['NEW']['go']                                           # Devil's hard objections stand (rug meter, never scanned)
    assert st['perf']['bar'] >= ag.BAR_FLOOR and st['weather']['regime'] == 'HOT'                # and the bar never goes under its floor
    hostile = lambda nums, rows, st, now: {'regime': 'HOSTILE', 'adj': 99.0, 'mods': {'barAdj': 99.0, 'size': 0.0}}
    st2, _ = passes(bad, lambda *a: (lambda w: {**w, 'adj': of.weather_adj(w)})(hostile(*a)))
    assert st2['perf']['bar'] - st['perf']['bar'] == pytest.approx(of.WEATHER_BAR_RANGE[1] - of.WEATHER_BAR_RANGE[0], abs=0.01)   # it can only add this much
    assert of.weather_size(hostile(0, 0, 0, 0)) == of.WEATHER_SIZE_RANGE[0]


# ── 🛡 Warden ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_warden_only_ever_reduces_caps_or_vetoes_and_names_the_rule_that_did_it():
    full = of.warden(0.40, {'value': 4.0, 'liq': 200_000, 'ageH': 20, 'd5': 1, 'top10': 12, 'lives': 9, 'courier': 'HEALTHY', 'weather': {'regime': 'NORMAL', 'mods': {'size': 1.0}}})
    assert full['allowed'] == 0.40 and full['mult'] == 1.0 and not full['rules'] and full['decided'].startswith('none')
    young = of.warden(0.40, {'value': 4.0, 'liq': 200_000, 'ageH': 2, 'courier': 'HEALTHY'})
    assert young['allowed'] == 0.20 and young['decided'] == 'W4 age'
    assert of.warden(0.40, {'value': 4.0, 'liq': 200_000, 'ageH': 20, 'courier': 'BAD'})['veto']                      # execution BAD = no new money
    hostile = of.warden(0.40, {'value': 4.0, 'liq': 200_000, 'ageH': 20, 'weather': {'regime': 'HOSTILE', 'mods': {'size': 0.25}}})
    assert hostile['allowed'] == 0.10 and hostile['mult'] == 0.25 and hostile['decided'] == 'W2 weather'
    small = of.warden(0.12, {'value': 1.2, 'liq': 200_000, 'ageH': 20, 'weather': {'regime': 'HOSTILE', 'mods': {'size': 0.25}}})
    assert small['allowed'] == 0.05 and small['rules'][-1]['id'] == 'W11 smallest order'                              # the smallest sendable order — still under the ask
    assert of.warden(0.04, {'value': 1.0, 'liq': 200_000, 'ageH': 20})['veto']                                        # nothing sendable = a veto, not a rounded-up buy
    assert of.warden(9.0, {'value': 10.0, 'liq': 200_000, 'ageH': 20})['allowed'] <= 4.0                              # concentration cap (40% of the card), snapped down a step
    vals = {'courier': [None, 'HEALTHY', 'DEGRADED', 'BAD'], 'ageH': [None, 0.2, 3, 50], 'd5': [None, -20, 0, 30], 'top10': [None, 10, 60], 'lives': [None, 1, 9],
            'liq': [None, 0, 5_000, 5e6], 'value': [None, 0, 0.5, 100], 'peak': [None, 200], 'lastReal': [None, [-1, -1, -1], [5, 5, 5]],
            'weather': [None, {'mods': {'size': 99}}, {'mods': {'size': -5}}, {'regime': 'HOT', 'mods': {'size': 1.0}}]}
    n = 0
    for combo in itertools.product(*vals.values()):
        for req in (0.0, 0.03, 0.31, 7.5):
            w = of.warden(req, dict(zip(vals, combo)))
            n += 1
            assert 0 <= w['allowed'] <= req + 1e-9 and w['mult'] <= 1.0 and w['eff'] <= 1.0                           # NEVER more than was asked, whatever it is shown
    assert n > 20_000


# ── 📮 Courier ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_courier_never_calls_an_unconfirmed_fill_confirmed_and_grades_execution_from_the_ledger():
    fill = lambda **k: {'card': 'degen', 'side': 'buy', 'mint': 'A', 'symbol': 'A', 'status': 'filled', 'sig': 'S1', 'at': 990, 'usd': 0.3, 'midPx': 1.0, 'px': 1.002, 'feeUsd': 0.001, **k}
    assert of.confirmed(fill()) and not of.confirmed(fill(sig=None)) and not of.confirmed(fill(status='pending')) and not of.confirmed(None)
    assert of.fill_state([fill()], 'A', 'buy')['state'] == 'confirmed' and of.fill_state([fill()], 'A', 'buy')['delta'] == 0.2
    assert of.fill_state([], 'A', 'buy')['state'] == 'none'                                                     # an order in flight has no row: it is NOT a fill
    assert of.fill_state([fill(status='failed', sig=None, err='slippage exceeded on-chain')], 'A', 'buy') == {'state': 'failed', 'at': 990.0, 'err': 'slippage exceeded on-chain'}
    assert of.fill_state([fill(status='skipped', sig=None, err='pool too thin')], 'A', 'buy')['state'] == 'refused'
    assert of.fill_state([fill(status='filled', sig=None)], 'A', 'buy')['state'] == 'none'                      # "filled" without a signature is not believed
    sell = fill(side='sell', sig='S9', costUsd=1.0, realizedPnlUsd=-0.4, px=0.59, midPx=0.6)
    assert of.fill_state([sell], 'A', 'sell')['realPct'] == -40.0                                               # the REAL result comes from the ledger row
    ok = of.courier([fill(sig=f'S{i}', at=900 + i) for i in range(5)], {}, 1000, 'degen')
    assert ok['health'] == 'HEALTHY' and ok['fills'] == 5 and ok['deltaMed'] == 0.2 and ok['last'][0]['state'] == 'confirmed'
    bad = of.courier([fill(status='failed', sig=None, at=900 + i, err='expired — never landed') for i in range(3)] + [fill(sig='S', at=950)], {}, 1000, 'degen')
    assert bad['health'] == 'BAD' and bad['failed'] == 3 and bad['expired'] == 3
    assert of.courier([fill(sig='S'), fill(sig='S')], {}, 1000, 'degen')['health'] == 'BAD'                     # one signature booked twice
    assert of.courier([fill(sig=None)], {}, 1000, 'degen')['health'] == 'BAD'                                   # a filled row with no signature
    assert of.courier([], {'halt': True, 'haltWhy': 'token balance below card books'}, 1000)['health'] == 'BAD'
    assert of.courier([], {'pending': {'symbol': 'A', 'side': 'buy', 'sentAt': 900}}, 1000)['health'] == 'DEGRADED'
    slow = of.courier([fill(sig=f'S{i}', at=900 + i, px=1.05) for i in range(4)], {}, 1000)
    assert slow['health'] == 'DEGRADED' and 'worse than mid' in slow['why'][0]
    idle = of.courier([], {}, 1000)
    assert idle['health'] == 'HEALTHY' and idle['sends'] == 0 and 'nothing measured' in idle['why'][0]


# ── ☠ Reaper ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_reaper_rules_in_order_with_evidence_and_never_rules_on_a_missing_price():
    cfg = {'agentTakePct': 10, 'agentScalp': False}
    run = lambda l, px, table=None, pos=None, now=3600, **k: of.reap([l], table if table is not None else [trow(l['mint'])], {'P' + l['mint']: px}, cfg, pos, now, **k)
    one = lambda *a, **k: run(*a, **k)[1][0]
    assert one(leg('A'), 1.03)['state'] == 'HOLD'
    assert one(leg('A'), 0)['rule'] == 'R0 no price' and one(leg('A'), 0)['action'] is None                      # no price = no ruling
    assert one(leg('A', buying=True, units=0), 1.0)['exec'] == 'unconfirmed'                                      # a buy not on the ledger is not a position yet
    r = one(leg('A', liqNow=20_000), 1.2)
    assert (r['state'], r['rule'], r['action']) == ('EXIT INVALIDATED', 'R1 liquidity collapse', 'pull') and '33%' in r['evidence']
    assert one(leg('A'), 1.0, [trow('A', safe=False)])['rule'] == 'R2 hard invalidation' and one(leg('A'), 1.0, [trow('A', rug=70)])['rule'] == 'R2 hard invalidation'
    pos, rep, _ = run(leg('A'), 1.0, [trow('A', top10=15)])
    assert run(leg('A'), 1.0, [trow('A', top10=40)], pos)[1][0]['rule'] == 'R3 holders concentrating'           # 15% → 40% since entry
    assert one(leg('A'), 1.04, tape={'PA': 'dump'})['state'] == 'TAKE' and one(leg('A'), 0.97, tape={'PA': 'dump'})['state'] == 'PROTECT'
    assert one(leg('A'), 0.69)['rule'] == 'R5 stop' and one(leg('A'), 0.72)['state'] == 'HOLD'                   # default stop −30
    t = one(leg('A'), 1.12)
    assert (t['state'], t['rule'], t['action']) == ('TAKE', 'R6 take line', None)                                # the card's own +10% take banks it — Reaper adds no second sell
    assert of.take_line({'agentTakePct': 10}, {'tp': 8}) == 8 and of.take_line({'agentTakePct': 10, 'agentScalp': False}, {'tp': 8}) == 10
    pos, rep, _ = run(leg('A'), 1.08)
    assert rep[0]['state'] == 'PROTECT' and rep[0]['rule'] == 'R7 trailing protection' and rep[0]['action'] is None   # armed at the peak
    pos, rep, _ = run(leg('A'), 1.035, pos=pos, now=3700)
    assert (rep[0]['state'], rep[0]['action']) == ('TAKE', 'pull') and rep[0]['peak'] == 8.0 and 'gave back' in rep[0]['evidence']
    assert run(leg('A'), 1.005, pos=pos, now=3760)[1][0]['action'] is None                                       # under +1.5% there is nothing left to bank: not sold for the fee
    m = one(leg('A'), 1.03, [trow('A', lean=-1.0)])
    assert (m['state'], m['rule'], m['action']) == ('TAKE', 'R8 momentum failed', 'pull')
    assert one(leg('A', at=3500), 1.03, [trow('A', lean=-1.0)])['state'] == 'HOLD'                               # … but never inside its first 15 minutes
    assert one(leg('A'), 0.97, [trow('A', lean=-1.0)])['state'] == 'PROTECT'                                     # at a loss it is flagged, not dumped
    assert one(leg('A', at=1), 0.97, [], now=3 * 3600)['rule'] == 'R9 time'                                      # 3h, off the radar, going nowhere
    assert run(leg('A', frozen=True), 0.5)[1] == []                                                              # the creator's ❄ is never touched
    assert run({**leg('B'), 'bought': {'tag': '🎯 your pick'}}, 0.5)[1] == []                                    # not theirs, not in control → not Reaper's
    yours = {**leg('B'), 'bought': {'tag': '🎯 your pick'}}
    assert run(yours, 0.62, control=True)[1][0]['state'] == 'HOLD'                                               # in control: a coin that is not theirs keeps the CARD's own stop …
    assert run(yours, 0.5, control=True)[1][0]['rule'] == 'R5x catastrophic stop'                                # … under the hard-coded catastrophic line no coin is held
    assert run({**yours, 'liqNow': 10_000}, 0.5, control=True)[1][0]['rule'] == 'R1 liquidity collapse'          # … but a collapsing pool takes any coin out


def test_a_winner_is_never_surrendered_because_another_candidate_appears_and_reaper_only_joins_the_existing_decisions():
    table = [trow('A', lean=1.0), trow('NEW', lean=4.0)]                                                         # a much stronger read is waiting
    legs = [leg('A', at=1)]
    cfg = {'agentTakePct': 10, 'coins': 1, 'trenchMinAgeH': 1}
    dec = ag.manage(legs, table, {'PA': 1.05}, cfg, control=True, now=7200, moves_left=1, picks=[table[1]], rotate=True)
    assert [d['action'] for d in dec] == ['hold']                                                               # +5%: winning → it keeps its seat
    _, rep, _ = of.reap(legs, table, {'PA': 1.05}, cfg, None, 7200, control=True)
    assert rep[0]['state'] == 'HOLD' and of.merge_reaper(dec, rep) == dec
    swap = [{'pair': 'PA', 'symbol': 'A', 'action': 'swap', 'why': 'desk', 'to': table[1]}]
    ask = [{'pair': 'PA', 'symbol': 'A', 'action': 'pull', 'rule': 'R5 stop', 'evidence': 'x'}]
    assert of.merge_reaper(swap, ask) == swap                                                                    # a move the desk already decided stands
    out = of.merge_reaper([{'pair': 'PA', 'symbol': 'A', 'action': 'hold', 'why': 'h'}], ask)
    assert out[0]['action'] == 'pull' and out[0]['why'].startswith('☠ Reaper R5 stop') and {d['action'] for d in out} <= {'hold', 'pull', 'swap'}   # no new action kind


def test_reaper_cannot_fabricate_an_exit_only_the_ledger_closes_a_position():
    pos, rep, gone = of.reap([leg('A')], [trow('A')], {'PA': 0.6}, {}, None, 3600)
    assert rep[0]['action'] == 'pull' and gone == [] and pos['A']['askRule'] == 'R5 stop'                        # asking is not leaving
    pos, rep, gone = of.reap([], [], {}, {}, pos, 3660)                                                          # the coin left the card
    assert rep == [] and gone[0]['mint'] == 'A'
    still, closed = of.confirm_exits([], gone, [], 3670, 'degen')
    assert closed == [] and still[0]['exit']['state'] == 'requested'                                             # no ledger row → NOT closed
    refused = [{'card': 'degen', 'side': 'sell', 'mint': 'A', 'status': 'skipped', 'err': 'price impact 99%', 'at': 3665}]
    still, closed = of.confirm_exits(still, [], refused, 3680, 'degen')
    assert closed == [] and still[0]['exit']['state'] == 'refused'                                               # a refused sell is said, never booked
    sold = refused + [{'card': 'degen', 'side': 'sell', 'mint': 'A', 'status': 'filled', 'sig': 'SIG', 'at': 3690, 'costUsd': 1.0, 'realizedPnlUsd': -0.41, 'usd': 0.59, 'midPx': 0.6, 'px': 0.59}]
    _, closed = of.confirm_exits(still, [], sold, 3700, 'degen')
    assert closed[0]['confirmed'] and closed[0]['realPct'] == -41.0 and closed[0]['exit']['sig'] == 'SIG'        # the result is the ledger's, not Reaper's last read (−40)
    _, late = of.confirm_exits(still, [], [], 3660 + of.EXIT_WAIT_SEC + 1, 'degen')
    assert late[0]['confirmed'] is False and late[0]['realPct'] is None and late[0]['exit']['state'] == 'unconfirmed'


# ── 🗄 Archivist ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_archivist_keeps_losses_detects_a_rewrite_and_stays_bounded():
    a = {}
    for i in range(of.ARCH_CASES + 50):
        a = of.file_case(a, {'mint': f'm{i}', 'sym': f'm{i}', 'px': 1.0, 'cleared': i % 2 == 0, 'weather': {'regime': 'NORMAL'}, 'trigger': ['enter', '', 1.5]}, 1000 + i)
        if i < 60:
            a = of.settle_cases(a, lambda m: 0.4, 1000 + i + 3700)                                               # the first ones all lost 60%
    assert len(a['cases']) == of.ARCH_CASES and a['filed'] == of.ARCH_CASES + 50 and of.verify(a) == 0
    assert a['agg']['cleared']['n'] + a['agg']['blocked']['n'] == 50 and a['agg']['cleared']['sum5'] < 0 and a['agg']['wx:NORMAL']['up'] == 0   # rotated out, losses still counted
    size = len(json.dumps(a))
    a = of.file_case(a, {'mint': 'm649', 'sym': 'dup', 'px': 1.0}, 1000 + 650)                                   # the same coin inside 30 min is one case
    assert a['filed'] == of.ARCH_CASES + 50 and abs(len(json.dumps(a)) - size) < 200
    a = of.file_case(a, {'mint': 'm649', 'sym': 'real', 'px': 1.0, 'action': 'fill'}, 1000 + 651)                # … unless it carries a real action
    assert a['cases'][-1]['d']['action'] == 'fill'
    a = of.settle_cases(a, lambda m: None, 1000 + 651 + 3700)
    assert a['cases'][-1]['out']['p60'] == -100.0                                                                # vanished = −100%, never dropped
    for p in ({'mint': 'W', 'sym': 'W', 'peak': 12, 'low': -2, 'pct': 9, 'path': [1, 12, 9], 'confirmed': True, 'realPct': 8.5, 'askRule': 'R7 trailing protection', 'exit': {'state': 'confirmed', 'sig': 'S'}},
              {'mint': 'L', 'sym': 'L', 'peak': 1, 'low': -45, 'pct': -44, 'path': [1, -20, -44], 'confirmed': True, 'realPct': -46.2, 'askRule': 'R5 stop', 'exit': {'state': 'confirmed', 'sig': 'T'}}):
        a = of.file_position(a, p, 5000)
    assert [p['realPct'] for p in a['positions']] == [8.5, -46.2] and of.verify(a) == 0                          # the loss is on file exactly as it happened
    forged = json.loads(json.dumps(a))
    forged['positions'][1]['realPct'] = 46.2                                                                     # "turn a loss into a win"
    assert of.verify(forged) == 1
    forged = json.loads(json.dumps(a)); forged['cases'][5]['d']['cleared'] = not forged['cases'][5]['d']['cleared']
    assert of.verify(forged) >= 1
    for i in range(of.ARCH_POS + 5):
        a = of.file_position(a, {'mint': f'p{i}', 'sym': 'x', 'confirmed': True, 'realPct': -10.0, 'path': [0, -10]}, 6000 + i)
    assert len(a['positions']) == of.ARCH_POS and a['posAgg']['n'] == 7 and a['posAgg']['lost'] == 6 and a['posAgg']['sum'] == pytest.approx(8.5 - 46.2 - 50)


def test_learning_lines_come_from_the_records_with_their_counts_and_never_from_thin_air():
    assert of.patterns({}, {}) == []
    a = {}
    for i in range(12):
        a = of.file_case(a, {'mint': f'm{i}', 'sym': 'x', 'px': 1.0, 'cleared': i < 6, 'ageH': 0.5, 'weather': {'regime': 'HOSTILE'}, 'trigger': ['enter', '', 1.5], 'sherlock': {'lean': 2.5}}, 1000 + i)
    assert of.patterns(a, {}) == []                                                                              # filed but not judged yet → nothing is claimed
    a = of.settle_cases(a, lambda m: 0.9 if int(m[1:]) < 6 else 0.7, 1000 + 400)
    ps = of.patterns(a, {})
    by = {p['agent']: p for p in ps}
    assert by['weather']['n'] == 12 and 'HOSTILE' in by['weather']['text'] and by['weather']['value'] == -20.0
    assert 'under 1h old' in by['trigger']['text'] and by['sherlock']['n'] == 12
    assert any(p['agent'] == 'devil' and 'cleared read -10.0%' in p['text'] and '-30.0%' in p['text'] for p in ps)
    for i in range(5):
        a = of.file_position(a, {'mint': f'p{i}', 'sym': 'x', 'peak': 10, 'path': [10, 6], 'confirmed': True, 'realPct': 5.0, 'askRule': 'R7 trailing protection', 'warden': 0.5, 'exit': {'delta': 0.4}}, 2000)
    ps = of.patterns(a, {})
    assert any(p['agent'] == 'reaper' and 'kept 50% of the peak gain' in p['text'] and p['n'] == 5 for p in ps)
    assert any(p['agent'] == 'warden' and '0.5×' in p['text'] for p in ps) and any(p['agent'] == 'courier' for p in ps)
    st = {'done': [{'at': 1, 'kind': 'enter', 'devil': 'object', 'devilWhy': 'rug meter 70', 'p5': -9.0}] * 6}
    rec = of.devil_record(st)
    assert rec[0] == {'rule': 'rug_meter', 'hard': True, 'what': 'rug meter ≥ 50', 'n': 6, 'med': -9.0, 'saved': 100}


# ── 👨‍⚖️ Judge ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_judge_cannot_demote_on_a_thin_sample_and_scores_every_agent_itself_included():
    assert of.standing(2, 0)[0] == 'alive' and 'not enough' in of.standing(2, 0)[1]                              # two bad outcomes decide nothing
    assert of.standing(of.JUDGE_MIN_N - 1, 0, violations=3, unsafe=True)[0] == 'alive'
    assert of.standing(of.JUDGE_MIN_N, 30)[0] == 'probation' and of.standing(of.JUDGE_DEMOTE_N - 1, 30)[0] == 'probation'
    assert of.standing(of.JUDGE_DEMOTE_N, 30)[0] == 'demoted' and of.standing(of.JUDGE_DEMOTE_N, 70)[0] == 'alive'
    assert of.standing(of.JUDGE_DEMOTE_N, 70, unsafe=True)[0] == 'demoted'
    cards = of.scorecards({}, {}, {}, None, None)
    assert tuple(cards) != () and set(cards) == set(of.CHAIN)
    need = {'n', 'accuracy', 'fp', 'fn', 'missed', 'badApprovals', 'usefulVetoes', 'profit', 'loss', 'drawdown', 'latency', 'stale', 'violations', 'confidence', 'gen', 'survival', 'status', 'why'}
    assert all(need <= set(c) for c in cards.values()) and all(c['status'] == 'alive' for c in cards.values())   # nothing judged yet → nobody is in trouble
    st, _ = passes(lambda i: [row('up', 1 + i * 0.02), row('dn', 1 - i * 0.004, buyShare=40)] + [row(f'c{j}') for j in range(12)])
    st = ag.record(st, _, 1300)
    st = ag.settle(st, lambda m: {'up': 1.20}.get(m, 0.9), 1300 + 16 * 60)
    a = {}
    for i in range(40):
        a = of.file_case(a, {'mint': f'm{i}', 'px': 1.0, 'cleared': True, 'weather': {'regime': 'HOT'}}, 1000 + i)
    a = of.settle_cases(a, lambda m: 0.8, 1500)                                                                  # Weather said HOT, every case lost
    for i in range(3):
        a = of.file_position(a, {'mint': f'p{i}', 'confirmed': True, 'realPct': -12.0, 'peak': 4, 'low': -15, 'path': [4, -12], 'askRule': 'R5 stop', 'warden': 0.5, 'exit': {'sig': 'S'}}, 1500)
    cards = of.scorecards(st, a, {'lat': {'weather': [0.1, 0.2, 5.0]}, 'viol': {'tally': {'stale': 7}}}, None, {'sends': 4, 'fills': 3, 'failed': 1, 'health': 'DEGRADED', 'deltaMed': 0.3})
    assert cards['weather']['n'] == 40 and cards['weather']['accuracy'] == 0 and cards['weather']['status'] == 'probation' and cards['weather']['fp'] == 40
    assert cards['weather']['latency'] == {'last': 5.0, 'p50': 0.2, 'p95': 5.0, 'max': 5.0, 'n': 3}
    assert cards['reaper']['n'] == 3 and cards['reaper']['status'] == 'alive' and cards['reaper']['loss'] == -36.0   # three losing exits: on file, counted, and still too few to judge
    assert cards['warden']['usefulVetoes'] == 3 and cards['warden']['drawdown'] == -18.0                         # half size on three −12% exits
    assert cards['courier']['accuracy'] == 75 and cards['tally']['stale'] == 7 and cards['archivist']['violations'] == 0
    assert cards['trigger']['n'] >= 1 and cards['judge']['status'] == 'alive'


# ── 📜 Constitution + the learning path ─────────────────────────────────────────────────────────────────────────────────────────
def test_the_constitution_is_immutable_and_every_code_location_it_names_exists():
    assert set(of.CONSTITUTION) == set(of.CHAIN) and len(of.CHAIN) == 10
    with pytest.raises(TypeError):
        of.CONSTITUTION['reaper']['ethics'] = ('hold and hope',)
    with pytest.raises(TypeError):
        of.CONSTITUTION['warden'] = {}
    with pytest.raises((TypeError, AttributeError)):
        of.CONSTITUTION['devil']['hard'].append('nothing')
    with pytest.raises(TypeError):
        of.TUNABLE['reaper']['stopPct'] = (99, 0, 100, '')
    for a, c in of.CONSTITUTION.items():
        assert c['ideology'] and c['ethics'] and c['forbidden'] and c['hard'] and c['role']
        mod = {'backend/agents.py': ag, 'backend/office.py': of}[c['code']['file']]
        assert all(callable(getattr(mod, fn)) for fn in c['code']['fn']), a                                       # the page shows real function names
        assert all(callable(getattr(of, fn)) for fn in c.get('office', ()))
    with pytest.raises(ValueError, match='immutable core'):
        of.propose({}, 'reaper', 'ethics', 1, {'n': 99}, 1)                                                      # only tunables can even be proposed
    with pytest.raises(ValueError, match='immutable core'):
        of.propose({}, 'trigger', 'bar', 0.1, {'n': 99}, 1)
    with pytest.raises(ValueError, match='hard bounds'):
        of.propose({}, 'reaper', 'stopPct', 90, {'n': 99}, 1)
    assert of.tune({'tune': {'reaper': {'stopPct': 999}}}, 'reaper', 'stopPct') == 40.0                          # a stored value outside its bounds is clamped, never obeyed
    cards = of.agent_cards({}, {'live': {}, 'office': {}})
    assert [c['key'] for c in cards] == list(of.CHAIN) and cards[7]['code'][0] == {'file': 'backend/office.py', 'fn': ['reap', 'reaper_replay', 'merge_reaper', 'confirm_exits']}
    assert cards[7]['tunable'][0] == {'key': 'protectAt', 'value': 6.0, 'default': 6.0, 'lo': 4.0, 'hi': 15.0, 'what': 'peak gain % at which the trailing protection arms'}


def test_a_rule_changes_only_through_evidence_a_shadow_test_and_a_better_result():
    with pytest.raises(ValueError, match='archived records'):
        of.propose({}, 'reaper', 'giveBackPct', 30, {'n': 3}, 100)                                               # one or two results propose nothing
    o = of.propose({}, 'reaper', 'giveBackPct', 30, {'n': 12}, 100)
    cid = next(iter(o['candidates']))
    assert of.tune(o, 'reaper', 'giveBackPct') == 50.0 and o['candidates'][cid]['status'] == 'shadow'            # nothing live moved
    with pytest.raises(ValueError, match='already has a candidate'):
        of.propose(o, 'reaper', 'stopPct', 20, {'n': 12}, 101)
    with pytest.raises(ValueError, match='incomplete'):
        of.promote(o, cid, 200)
    o['candidates'][cid]['shadow'] = [[2.0, 1.0]] * of.SHADOW_N
    with pytest.raises(ValueError, match='did not beat'):
        of.promote(o, cid, 200)                                                                                  # a finished test that lost promotes nothing
    o['candidates'][cid]['shadow'] = [[2.0, 4.0]] * (of.SHADOW_N - 1)
    with pytest.raises(ValueError, match='incomplete'):
        of.promote(o, cid, 200)
    o['candidates'][cid]['shadow'] = [[2.0, 4.0]] * of.SHADOW_N
    p = of.promote(o, cid, 300)
    assert of.tune(p, 'reaper', 'giveBackPct') == 30.0 and p['gen']['reaper'] == 2 and p['candidates'][cid]['status'] == 'promoted' and 'shadow' in p['lineage'][-1]['why']
    # the Judge's own loop: evidence in the archive → a candidate → positions closed AFTER it → evaluated
    path = [2, 9, 12, 7, 3, 1]                                                                                   # peaks +12 then fades: a tighter give-back banks more
    a = {}
    for i in range(of.PROPOSE_N):
        a = of.file_position(a, {'mint': f'p{i}', 'confirmed': True, 'realPct': 1.0, 'path': path, 'closedAt': 1000 + i}, 1000 + i)
    cfg = {'agentTakePct': 20, 'agentScalp': False}
    o = of.judge_candidates({}, a, cfg, None, 2000)
    c = next(iter(o['candidates'].values()))
    assert c['agent'] == 'reaper' and c['status'] == 'shadow' and c['evidence']['n'] == of.PROPOSE_N and c['shadow'] == [] and not o.get('tune')
    assert of.judge_candidates(o, a, cfg, None, 2100)['candidates'][c['id']]['shadow'] == []                     # the positions it was picked from are never its test
    for i in range(of.SHADOW_N):
        a = of.file_position(a, {'mint': f'q{i}', 'confirmed': True, 'realPct': 1.0, 'path': path, 'closedAt': 3000 + i}, 3000 + i)
    done = of.judge_candidates(o, a, cfg, None, 4000)
    assert done['candidates'][c['id']]['status'] == 'promoted' and of.tune(done, 'reaper', c['key']) == c['value'] and done['gen']['reaper'] == 2
    a2 = dict(a)
    for i in range(of.SHADOW_N):
        a2 = of.file_position(a2, {'mint': f'r{i}', 'confirmed': True, 'realPct': 1.0, 'path': [1, 2, 3], 'closedAt': 5000 + i}, 5000 + i)   # positions where the change does nothing
    o2 = {**o, 'candidates': {c['id']: {**c, 'seenAt': 4999}}}
    assert of.judge_candidates(o2, a2, cfg, None, 6000)['candidates'][c['id']]['status'] == 'rejected'           # no better in shadow → rejected, the live rule stays
    demoted = of.demote(done, {'reaper': {'status': 'demoted', 'why': '30% right over 60 samples'}}, 7000)
    assert of.tune(demoted, 'reaper', c['key']) == of.TUNABLE['reaper'][c['key']][0] and demoted['gen']['reaper'] == 3   # a demoted agent goes back to the hard-coded defaults


def test_reaper_replay_is_the_same_price_rules_reaper_runs_live():
    p = of.tunes({}, 'reaper')
    assert of.reaper_replay([2, 9, 12, 7, 3], p, 20) == 3 and of.reaper_replay([2, 9, 12, 5.9], p, 20) == 5.9
    assert of.reaper_replay([5, 22], p, 20) == 20 and of.reaper_replay([-5, -31, 40], p, 20) == -31 and of.reaper_replay([], p, 20) == 0.0


# ── the lock, the four desks' exposure, the pipeline ─────────────────────────────────────────────────────────────────────────────
def test_the_breakeven_lock_reads_only_the_real_cards_value_against_its_put_in():
    st = {'done': [{'at': i * 400, 'kind': 'enter', 'go': True, 'devil': 'agree', 'p5': 60.0, 'p15': 60.0, 'p60': 60.0, 'mint': f'm{i}', 'lean': 3} for i in range(40)]}
    assert ag.paper(st)['x'] >= ag.PROVE_X                                                                       # the paper desk is far past 10× …
    # 🎓 breakeven is milestone 1, NOT graduation: the 5-minute stage stays locked until REAL equity ≥ 2× the real put-in
    for money, under, phase, locked in (({'value': 1.24, 'putIn': 29.5}, True, 'RECOVERY', True), ({'value': 29.49, 'putIn': 29.5}, True, 'RECOVERY', True),
                                        ({'value': 29.5, 'putIn': 29.5}, False, 'GROWTH', True), ({'value': 40, 'putIn': 29.5}, False, 'GROWTH', True),
                                        ({'value': 58.99, 'putIn': 29.5}, False, 'GROWTH', True), ({'value': 59.0, 'putIn': 29.5}, False, 'GRADUATED', False),
                                        ({'value': 80, 'putIn': 29.5}, False, 'GRADUATED', False)):
        s = {**st, 'money': money}
        assert ag.underwater(s) is under and ag.real_phase(money)['phase'] == phase
        assert (ag.stage(s)['h'] == 5 and 5 not in ag.stage(s)['conquered']) is locked                           # … and only real value ≥ 2× real put-in moves the stage
        m = of.mission(money, 9, ag.stage(s), 100, 400, None, ag.underwater(s))
        assert m['locked'] is locked and m['lock'] == ('LOCKED' if locked else 'ELIGIBLE') and m['nextStage'] == m['lock'] and m['toBreakeven'] == round(money['value'] - money['putIn'], 2)
        assert m['phase'] == phase and m['breakevenTarget'] == 29.5 and m['doubleTarget'] == 59.0 and m['toDouble'] == round(money['value'] - 59.0, 2) and m['unlock'] == 'real equity ≥ $59.00'
        assert m['putIn'] == money['putIn'] and m['value'] == money['value'] and (m['stage'] == 5) is locked    # the card's own numbers, passed through
    # paper performance can never unlock a real-money stage: a 10× paper desk with NO real card money read, or with any paper number, stays locked
    assert ag.stage(st)['h'] == 5 and ag.stage(st)['need2x'] and ag.real_phase(None)['phase'] == 'UNKNOWN' and not ag.real_phase({'putIn': 29.5})['eligible']
    assert ag.stage({**st, 'money': {'value': 10.0, 'putIn': 29.5, 'paper': 9999, 'paidOut': 500, 'takenUsd': 900}})['h'] == 5       # gross proceeds / paid-out / paper totals are not read
    assert of.mission({}, 9, {'h': 5}, 0, 0)['locked'] and of.mission({}, 9, {'h': 5}, 0, 0)['lock'] == 'UNKNOWN'
    m = of.mission({'value': 1.24, 'putIn': 29.5}, 9, {'h': 5}, 100, 400, None, True)
    assert m['needX'] == 23.8 and m['nextDutyIn'] == 300 and m['priority'][0] == 'SURVIVE' and 'real put-in' in m['lockRule']
    assert of.mission({}, 9, {'h': 5}, 0, 400, None, False)['lock'] == 'UNKNOWN'                                 # no card numbers = it says so, it does not guess


def test_the_exposure_helpers_show_the_same_checks_the_desks_rule_by():
    rows_at = lambda i: [row('ok', 1 + i * .005), row('thin', 1.0, liq=9_000), row('top', 1 + i * .3), row('fall', 1 - i * .05), row('bad', 1.0, safe=False),
                         row('weak', 1.0, buyShare=50, vol5m=1000)] + [row(f'c{j}', 1 + i * .002, src=['open', 'ptrend']) for j in range(10)]
    st, table = passes(rows_at)
    for x in table:
        chk = of.trigger_checks(x, st['perf'])
        assert all(c[1] for c in chk) == (x['trigger'][0] == 'enter'), (x['mint'], x['trigger'], chk)           # every check green ⇔ Trigger really said ENTER
        assert (not all(c[1] for c in chk if c[3])) == (x['trigger'][0] == 'skip')                               # a failed HARD check ⇔ SKIP
    x = next(t for t in table if t['mint'] == 'c0')
    t = of.tally_read(x, st['series']['c0'], 1000 + 3 * 60 + 5)
    assert t['readings'] == 4 and t['ageSec'] == 5.0 and t['intervalSec'] == 60.0 and not t['stale'] and t['sources'][-1] == 'Pump trending' and 'holdD' in t['missing']
    assert of.tally_read(x, st['series']['c0'], 1000 + 3 * 60 + 400)['stale']                                    # an old tape is said to be old
    s = of.sherlock_read(x, ag.learn(st, 5))
    assert s['lean'] == x['why']['lean'] and all({'key', 'weight', 'words', 'n', 'med'} <= set(r) for r in s['for'] + s['against']) and 'top-10 share unknown' in s['unresolved']
    assert [of.scan_status(True, now=10), of.scan_status(None), of.scan_status(None, inflight=True), of.scan_status(None, failed_at=100, now=150), of.scan_status(True, scanned_at=1, now=5000)] == ['DONE', 'REQUESTED', 'RUNNING', 'FAILED', 'STALE']
    assert all(ag.devil_rule_of(text) == rule for rule, text in ag.devil_args('enter', {'c1': 300, 'age': 0.1}, {'drivers': [], 'lean': 2}, {'safe': None, 'tv': {'rug': 70, 'call': ['', 'X', '']}}, {'busted': {'X'}}))
    objs = ag.devil_args('enter', {'c1': 300, 'age': 0.1}, {'drivers': [], 'lean': 2}, {'safe': None, 'tv': {'rug': 70, 'call': ['', 'X', '']}}, {'busted': {'X'}})
    assert [o[0] for o in objs] == ['busted_read', 'rug_meter', 'ran', 'young', 'unscanned'] and all(ag.DEVIL_RULES[o[0]][0] for o in objs)   # every objection has its rule, all hard


def test_the_pipeline_shows_each_desk_and_everything_after_a_stop_waits():
    st, table = passes(lambda i: [row('ok', 1 + i * .005), row('new', 1 + i * .005, safe=None)] + [row(f'c{j}', 1 + i * .002) for j in range(10)])
    assert [p['state'] for p in of.pipeline(None, {})] == ['WAITING'] * 10
    case = next(c for c in ag.investigate(table, set(), 1, {}, top=0) if c['mint'] == 'ok')
    ctx = {'tally': of.tally_read(case['row'], st['series']['ok'], 1185), 'sherlock': of.sherlock_read(case['row']), 'weather': {'regime': 'NORMAL', 'mods': {'barAdj': 0, 'size': 1}},
           'courier': {'health': 'HEALTHY', 'why': ['ok']}, 'ms': {'tally': 0.4}, 'filed': True}
    p = of.pipeline(case, ctx)
    assert [x['agent'] for x in p] == list(of.CHAIN) and p[0]['ms'] == 0.4 and all(x['state'] in of.STAGE_STATES for x in p)
    assert [x['state'] for x in p][:5] == ['PASS', 'PASS', 'PASS', 'PASS', 'PASS'] and p[5]['state'] == 'WAITING' and p[8]['state'] == 'DONE'
    wd = of.warden(0.3, {'value': 3, 'liq': 60_000, 'ageH': 8, 'courier': 'BAD'})
    p = of.pipeline(case, {**ctx, 'warden': wd, 'courier': {'health': 'BAD', 'why': ['halted']}})
    assert p[5]['state'] == 'VETO' and p[6]['state'] == 'WAITING' and p[7]['state'] == 'WAITING'                 # a veto stops the line
    blocked = next(c for c in ag.investigate(table, set(), 1, {}, top=0) if c['mint'] == 'new')
    p = of.pipeline(blocked, {**ctx, 'tally': of.tally_read(blocked['row'], st['series']['new'], 1185)})
    assert p[3]['state'] == 'VETO' and 'holders not scanned' in p[3]['word'] and p[4]['state'] == 'WAITING'
    d = of.lineage_of(blocked, {**ctx, 'bar': 1.5})
    assert d['blocked'][0] == 'scan' and d['weather']['regime'] == 'NORMAL' and d['tally']['pts'] == 4 and d['devil'][1][0] == 'unscanned' and len(json.dumps(d)) < 900


# ── the real card's money + the service: the page observes, it never works ───────────────────────────────────────────────────────
def test_the_wardens_cap_can_only_shrink_an_agent_seat_and_the_cards_money_still_adds_up():
    card = {'cash': 2.0, 'legs': [{'mint': 'X', 'symbol': 'X', 'pairAddress': 'PX', 'units': 2.0, 'entry': 1.0}], 'events': []}
    cfg, px = {'coins': 4}, {'PX': 1.0}
    r = {'mint': 'N', 'symbol': 'N', 'pairAddress': 'PN', 'price': 0.5, 'liquidityUsd': 90_000}
    assert ap.agent_seat_usd(card, px, cfg) == 1.0                                                               # an equal share of a $4 card
    total = lambda c: round(c['cash'] + sum(l['units'] * (0.5 if l['mint'] == 'N' else 1.0) for l in c['legs']), 6)
    plain = ap.agent_seat(card, r, px, cfg, 10)
    assert plain['legs'][-1]['units'] * 0.5 == pytest.approx(1.0, rel=1e-3) and plain['cash'] == 1.0 and total(plain) == pytest.approx(4.0, rel=1e-3)
    half = ap.agent_seat(card, r, px, cfg, 10, max_usd=0.5)
    assert half['legs'][-1]['units'] * 0.5 == pytest.approx(0.5, rel=1e-3) and half['cash'] == 1.5 and total(half) == pytest.approx(4.0, rel=1e-3) and half['events'][-1]['mint'] == 'N'
    assert half['events'][-1]['usd'] == 0.5 < plain['events'][-1]['usd'] == 1.0
    more = ap.agent_seat(card, r, px, cfg, 10, max_usd=50)
    assert more['legs'][-1]['units'] == plain['legs'][-1]['units'] and more['cash'] == plain['cash']             # a cap above the card's own rule changes nothing
    with pytest.raises(ValueError):
        ap.agent_seat(card, r, px, cfg, 10, max_usd=0.01)                                                        # too small to send = no seat, the cash stays
    assert card == {'cash': 2.0, 'legs': [{'mint': 'X', 'symbol': 'X', 'pairAddress': 'PX', 'units': 2.0, 'entry': 1.0}], 'events': []}


def _fresh(rs):
    rs._office.update(state=None, pos={}, exiting=[], gone=[], lat={}, sized={}, reports=[], warden=None, courier=None, payload=None, last=None, vetoAt={}, dutyAt=0)
    rs._agents.update(table=[], view=None, card=None, money={'value': 1.24, 'putIn': 29.5}, weather=None, decisions=None)


def _one_pass(rs, st, i, n=30):
    now = 5000 + i * 60
    rows = [row(f'c{j}', 1 + i * .004 * (1 if j % 3 else -1), ageH=1 + j) for j in range(n)]
    cour = of.courier([], {}, now, 'degen', rs._office_state())
    st, table = ag.desk(st, rows, now, weather_fn=lambda a, b, c, d: (lambda w: {**w, 'adj': of.weather_adj(w)})(of.weather(a, b, c, d, cour['health'], rs._office_state())))
    rs._agents['weather'] = st.get('weather')
    st = ag.record(st, table, now)
    st = ag.settle(st, lambda m: 1.0, now)
    st['money'] = rs._agents['money']
    rs._agents.update(table=table, view=ag.view(st, table, False, rs._agents_real(), None, {'agentControl': True}, None, now, None, rs._agents['money']))
    rs._office_pass(st, table, now, {'agentControl': True, 'agentTakePct': 10}, {r['mint']: r['price'] for r in rows}, rs._json_load(rs.ARCHIVE_PATH, {}), cour, 'degen', 4.0)
    return st


def test_one_office_payload_carries_everything_and_stays_bounded_pass_after_pass(monkeypatch):
    import reputation_service as rs
    monkeypatch.setattr(rs, '_fw_full_ledger', lambda: [])
    _fresh(rs)
    st, sizes = {}, []
    for i in range(70):
        st = _one_pass(rs, st, i)
        if i in (9, 39, 69):
            sizes.append(len(json.dumps(rs._office['payload'])))
    p = rs._office['payload']
    assert {'mission', 'office', 'agents', 'currentCase', 'pipeline', 'positions', 'execution', 'learning', 'judge', 'performance'} <= set(p)
    assert [a['key'] for a in p['agents']] == list(of.CHAIN) and [s['agent'] for s in p['pipeline']] == list(of.CHAIN)
    assert p['mission']['locked'] is True and p['mission']['stage'] == 5 and p['mission']['putIn'] == 29.5 and p['mission']['value'] == 1.24 and p['mission']['toBreakeven'] == -28.26
    assert all(a['code'] and a['ethics'] and a['card']['status'] and a['card']['latency'] is not None for a in p['agents'])
    assert p['performance']['agents']['weather']['n'] > 0 and p['performance']['agents']['judge']['p95'] is not None and p['performance']['deskMs'] == 4.0
    assert p['currentCase'] and p['currentCase']['trigger']['checks'] and p['currentCase']['tally']['readings'] >= 3 and p['currentCase']['sherlock']['scan'] in ('DONE', 'STALE')
    assert sizes[2] < 60_000 and sizes[2] < sizes[0] * 1.6                                                       # 70 passes later the payload is about the same size
    arch = rs._json_load(rs.ARCHIVE_PATH, {})
    assert 0 < len(arch['cases']) <= of.ARCH_CASES and of.verify(arch) == 0 and any((c.get('out') or {}).get('p5') is not None for c in arch['cases'])
    assert len(json.dumps(rs._json_load(rs.OFFICE_PATH, {}))) < 40_000 and all(len(v) <= rs.OFFICE_LAT_N for v in rs._office['lat'].values())


def test_viewing_the_agents_page_runs_no_desk_scan_quote_save_or_wallet_action(monkeypatch):
    import reputation_service as rs
    monkeypatch.setattr(rs, '_fw_full_ledger', lambda: [])
    _fresh(rs)
    _one_pass(rs, {}, 0)
    calls = {}

    def spy(name, is_async=True):
        async def a(*_, **__):
            calls[name] = calls.get(name, 0) + 1
        def s(*_, **__):
            calls[name] = calls.get(name, 0) + 1
        monkeypatch.setattr(rs, name, a if is_async else s)
    for n in ('_runner_intel', '_fw_quote', '_fw_jup', '_jup_prices', '_fw_execute', '_fw_tick', '_prime_tick', '_agents_tick', '_fw_sign', '_flow_fetch', '_rpc', '_krpc'):
        assert hasattr(rs, n), n
        spy(n)
    for n in ('_json_save', '_fw_save', '_fw_record', '_office_pass', '_office_warden', '_office_reap', '_fw_kick_now'):
        assert hasattr(rs, n), n
        spy(n, False)
    monkeypatch.setattr(rs, '_require_admin', lambda r: None)
    monkeypatch.setattr(ag, 'desk', lambda *a, **k: calls.__setitem__('desk', 1))
    before = (json.dumps(rs._office['payload'], sort_keys=True, default=str), json.dumps(rs._office['state'], sort_keys=True, default=str), dict(rs._intel_inflight))
    first = asyncio.run(rs.admin_agents_office(None))
    for _ in range(200):                                                                                         # a page left open, polling
        assert asyncio.run(rs.admin_agents_office(None)) is first
        v = asyncio.run(rs.admin_agents(None))
        assert v['office'] is first and v['agents']
    assert calls == {}                                                                                           # nothing ran: no scan, no quote, no price read, no save, no wallet call
    assert (json.dumps(rs._office['payload'], sort_keys=True, default=str), json.dumps(rs._office['state'], sort_keys=True, default=str), dict(rs._intel_inflight)) == before
    rs._office['payload'] = None
    assert asyncio.run(rs.admin_agents_office(None)) == {'cold': True, 'at': 0}                                  # before the first pass it says so — it does not start one


def test_the_service_sizes_real_seats_through_the_warden_and_reapers_requests_use_the_cards_own_exits(monkeypatch):
    import reputation_service as rs
    monkeypatch.setattr(rs, '_fw_full_ledger', lambda: [])
    _fresh(rs)
    rs._agents['weather'] = {'regime': 'HOSTILE', 'mods': {'barAdj': 1.0, 'size': 0.25}}
    cur = {'cash': 2.0, 'legs': [], 'events': []}
    t = trow('N')
    wd = rs._office_warden(cur, t, 0.80, {'coins': 4}, 1000, 'fill')
    assert wd['allowed'] == 0.20 and wd['requested'] == 0.80 and rs._office['sized']['N'] == 0.25 and rs._office['state']['count']['wardenSized'] == 1
    rs._office['courier'] = {'health': 'BAD'}
    assert rs._office_warden(cur, t, 0.80, {'coins': 4}, 1001, 'fill')['veto'] and cur['events'][-1]['move'] == 'veto' and '🛡 Warden vetoed $N' in cur['events'][-1]['why']
    rs._office_warden(cur, t, 0.80, {'coins': 4}, 1002, 'fill')
    assert sum(1 for e in cur['events'] if e.get('move') == 'veto') == 1                                         # a veto re-checked every tick is one line, not a flood
    monkeypatch.setattr(of, 'warden', lambda *a, **k: 1 / 0)
    assert rs._office_warden(cur, t, 0.80, {'coins': 4}, 2000, 'fill')['allowed'] == 0.80                        # if the Warden breaks, the card's own size stands — never more
    monkeypatch.undo()
    card = {'legs': [leg('A', at=1), leg('B', at=1)], 'events': [], 'cash': 0}
    rs._agents['table'] = [trow('A'), trow('B')]
    dec = [{'pair': 'PA', 'symbol': 'A', 'action': 'hold', 'why': 'h'}, {'pair': 'PB', 'symbol': 'B', 'action': 'hold', 'why': 'h'}]
    out = rs._office_reap(card, {'PA': 0.6, 'PB': 1.02}, {'agentTakePct': 10}, True, 4000, dec)
    assert [d['action'] for d in out] == ['pull', 'hold'] and out[0]['reaper'] == 'R5 stop' and [r['state'] for r in rs._office['reports']] == ['EXIT INVALIDATED', 'HOLD']
    rs._office_light('degen', {**card, 'agentDutyAt': 3900, 'events': [{'at': 3990, 'kind': 'agent', 'move': 'fill', 'symbol': 'A', 'mint': 'A', 'usd': 0.3, 'why': 'x'}]}, 4000)
    assert rs._office['last']['result'] == {'state': 'none'} and rs._office['dutyAt'] == 3900                    # the buy is not on the ledger: it is NOT reported as done
    monkeypatch.setattr(rs, '_fw_full_ledger', lambda: [{'card': 'degen', 'side': 'buy', 'mint': 'A', 'symbol': 'A', 'status': 'filled', 'sig': 'SIG', 'at': 3995, 'usd': 0.3, 'midPx': 1, 'px': 1.001}])
    rs._office_light('degen', {**card, 'events': [{'at': 3990, 'kind': 'agent', 'move': 'fill', 'symbol': 'A', 'mint': 'A', 'usd': 0.3, 'why': 'x'}]}, 4001)
    assert rs._office['last']['result']['state'] == 'confirmed' and rs._office['last']['result']['sig'] == 'SIG'
