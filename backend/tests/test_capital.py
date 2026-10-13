"""💰 Capital desk: size follows the agents' own real record."""
import capital as cap
import office as of
import trench_crew as crew


def _t(pcts):
    return [{'realPct': p, 'closedAt': i, 'rule': 'R5 stop' if p < 0 else 'R7 trailing protection'} for i, p in enumerate(pcts)]


def test_a_losing_record_takes_the_smallest_seat_and_a_thin_one_claims_nothing():
    assert cap.stance(cap.record(_t([5, -20] * 4)))['state'] == 'PROVING'                    # 8 exits: not judged
    v = cap.view(_t([8, -25, -25] * 6))
    assert v['state'] == 'PROTECT' and v['mult'] == 0.25 and v['floor'] == 0.25 and v['record']['kelly'] <= 0 and 'smallest seats' in v['why']
    assert v['leaks'][0]['rule'] == 'R5 stop' and v['leaks'][0]['sumPct'] < 0 and 'losses come from: R5 stop' in cap.lesson(v)
    win15 = cap.view(_t([15, 15, -10] * 5))                                                    # winning, 15 exits: still proving
    assert win15['state'] == 'PROVING' and win15['mult'] is None and 'not proof yet' in win15['why']


def test_a_proven_winning_record_sizes_by_half_kelly_never_above_the_seat_and_only_the_newest_window_counts():
    v = cap.view(_t([15, 15, -10] * 8), seats=4)
    r = v['record']
    assert v['state'] == 'GROW' and r['n'] == 24 and r['wonPct'] == 67 and r['payoff'] == 1.5 and 0 < r['kelly'] < 1
    assert v['mult'] in (0.5, 0.75, 1.0) and v['mult'] <= 1 and v['floor'] <= 0.75
    thin = cap.view(_t([15, -12, 15, -12, 15, -14] * 4), seats=4)                              # winning by a hair: no pressing
    assert thin['state'] == 'STEADY' and thin['mult'] == 0.5 and 0 < thin['record']['kelly'] < 0.25
    old_wins_new_losses = _t([40] * 40 + [5, -30, -30] * 10)                                   # the window is the last 30 only
    assert cap.view(old_wins_new_losses)['state'] == 'PROTECT'
    assert cap.record(_t([900, -5000]))['avgWin'] == 100 and cap.record(_t([900, -5000]))['avgLoss'] == -100   # capped
    assert cap.record([])['n'] == 0 and cap.lesson(cap.view([])) is None


def test_the_warden_reads_the_capital_stance_and_never_returns_more_than_requested():
    base = {'value': 4.0, 'putIn': 37.0, 'cash': 4.0, 'open': True, 'kernelSize': 0.5, 'kernelWhy': 'no chart yet'}
    half = of.warden(1.0, base)
    assert half['allowed'] == 0.5                                                              # today: an uncertain coin = half a seat
    grow = of.warden(1.0, {**base, 'capital': {'state': 'GROW', 'mult': 1.0, 'floor': 0.75, 'why': 'proven'}})
    assert grow['allowed'] == 0.75 and any(r['id'].startswith('W23') for r in grow['rules'])   # proven winning: the uncertain coin gets ×0.75
    clean = of.warden(1.0, {**base, 'kernelSize': None, 'capital': {'state': 'GROW', 'mult': 0.75, 'floor': 0.75, 'why': 'half-Kelly'}})
    assert clean['allowed'] == 0.75                                                            # half-Kelly caps even a clean coin
    prot = of.warden(1.0, {**base, 'capital': {'state': 'PROTECT', 'mult': 0.25, 'floor': 0.25, 'why': 'losing'}})
    assert prot['allowed'] == 0.25 and not prot['veto']                                        # losing record: smallest seat, never a veto
    same = of.warden(1.0, {**base, 'capital': {'state': 'PROVING', 'mult': None, 'floor': None, 'why': 'thin'}})
    assert same['allowed'] == half['allowed'] and not any(r['id'].startswith('W23') for r in same['rules'])
    for c in (grow, clean, prot, same):
        assert c['allowed'] <= c['requested']
    bad = of.warden(1.0, {**base, 'courier': 'BAD', 'capital': {'state': 'GROW', 'mult': 1.0, 'floor': 0.75, 'why': 'proven'}})
    assert bad['veto']                                                                         # execution rules are untouched by it
    assert crew.warden_rules([{'id': 'W4 newborn', 'mult': 0.1, 'why': 'x'}])[0]['mult'] == crew.SHRINK_FLOOR


def _tt(pcts, tag):
    return [{'realPct': p, 'closedAt': i, 'rule': 'x', 'tag': tag} for i, p in enumerate(pcts)]


def test_each_door_is_sized_by_its_own_record_and_the_brake_beats_them_all():
    armed = _tt([20, 20, -8] * 8, '🤖 agents · 🎯 ARMED (seat target)')                         # the armed door wins…
    ready = _tt([6, -25, -25] * 8, '🤖 agents · ⚡ READY (kernel)')                             # …the ready door loses
    v = cap.view(armed + ready, 4, True, value=5.0, peak=5.2)
    assert v['doors']['armed']['state'] == 'GROW' and v['doors']['ready']['state'] == 'PROTECT' and cap.door('x READY · switch') == 'ready'
    assert cap.for_door(v, 'armed')['mult'] >= 0.75 and cap.for_door(v, 'ready')['mult'] == 0.25 and 'ready door' in cap.for_door(v, 'ready')['why']
    assert cap.armed_size(v) == 1.0 and cap.armed_size({**v, 'on': False}) == 0.5              # armed earns the full size on its own record
    assert cap.armed_size(cap.view(_tt([6, -25, -25] * 8, 'ARMED'), 4, True)) == 0.25 and cap.armed_size(cap.view([], 4, True)) == 0.5
    thin = cap.view(_tt([5, 5, -3] * 2, 'ARMED') + ready, 4, True)                              # 6 armed exits: the desk's stance stands in
    assert cap.for_door(thin, 'armed')['state'] == thin['state']
    assert v['brake']['on'] is False and 'by door' in cap.lesson(v)
    b = cap.view(armed + ready, 4, True, value=4.0, peak=5.0)                                   # −20% off the 24h high
    assert b['brake']['on'] and b['brake']['downPct'] == 20.0 and cap.for_door(b, 'armed') == {'state': 'PROTECT', 'mult': 0.25, 'floor': 0.25, 'why': '🧯 ' + b['brake']['why']}
    assert cap.brake(None, 5.0)['on'] is False and cap.brake(5.0, None)['on'] is False and cap.brake(6.0, 5.0)['on'] is False
