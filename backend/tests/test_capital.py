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


def test_a_door_sizes_down_on_its_own_record_never_up_past_the_desk_and_the_brake_beats_them_all():
    armed = _tt([20, 20, -8] * 8, '🤖 agents · 🎯 ARMED (seat target)')                         # the armed door wins…
    ready = _tt([18, 18, 18, -25] * 6, '🤖 agents · ⚡ READY (kernel)')
    inter = [{**t, 'closedAt': i} for i, t in enumerate(x for pair in zip(armed, ready) for x in pair)]
    v = cap.view(inter, 4, True, value=5.0, peak=5.2)
    assert v['state'] == 'GROW' and v['doors']['armed']['state'] == 'GROW' and cap.door('x READY · switch') == 'ready'
    assert cap.for_door(v, 'armed')['mult'] >= 0.75 and cap.armed_size(v) == 1.0 and cap.armed_size({**v, 'on': False}) == 0.5   # armed earns the full size: desk AND door in GROW
    bad_ready = [{**t, 'closedAt': i} for i, t in enumerate(x for pair in zip(_tt([30, 30, -5] * 10, 'ARMED'), _tt([4, -12, -12] * 10, 'READY')) for x in pair)]
    w = cap.view(bad_ready, 4, True)                                                            # the desk wins overall, the ready door loses on its own
    assert w['state'] in ('STEADY', 'GROW') and w['doors']['ready']['state'] == 'PROTECT'
    assert cap.for_door(w, 'ready')['mult'] == 0.25 and 'ready door' in cap.for_door(w, 'ready')['why'] and cap.for_door(w, 'armed')['state'] == w['state']
    losing = cap.view(_tt([6, -25, -25] * 8, 'ARMED'), 4, True)
    assert losing['state'] == 'PROTECT' and cap.armed_size(losing) == 1.0                       # already the smallest seat: never halved again into an unsendable order
    assert cap.armed_size(cap.view([], 4, True)) == 0.5 and 'by door' in cap.lesson(v)
    b = cap.view(inter, 4, True, value=4.0, peak=5.0)                                           # −20% off the 24h high
    fd = cap.for_door(b, 'armed')
    assert b['brake']['on'] and b['brake']['downPct'] == 20.0 and (fd['state'], fd['mult'], fd['floor']) == ('PROTECT', 0.25, 0.25) and fd['why'].startswith('🧯') and cap.armed_size(b) == 1.0
    assert cap.brake(None, 5.0)['on'] is False and cap.brake(5.0, None)['on'] is False and cap.brake(6.0, 5.0)['on'] is False


def test_the_long_record_with_its_rugs_is_the_ceiling_and_one_rug_may_cost_only_the_rug_budget():
    """A 30-exit streak with no rug in it read GROW, seats went ×0.75 and the next rug took 17% of the card in 47 seconds ($X, 2026-10-13)."""
    old = _t([10, 10, -80, 10, -20, 10, -75, 10] * 12)                                          # 96 exits, 1 in 4 a rug: the average bet loses
    hot = [{**t, 'closedAt': 1000 + i} for i, t in enumerate(_t([15, 15, -8] * 10))]             # then 30 clean winners
    v = cap.view(old + hot, 4, True, value=4.0, peak=4.0)
    assert cap.stance(cap.record(old + hot), 4)['state'] in ('STEADY', 'GROW')                  # the window alone would press…
    assert v['state'] == 'PROTECT' and v['mult'] == 0.25 and 'rugs included' in v['why']         # …the long record does not let it
    assert v['rug']['on'] and v['rug']['rugs'] >= 20 and 9 < v['rug']['capPct'] < 12 and '☠' in cap.lesson(v)
    assert cap.view(hot, 4, True)['rug']['on'] is False and cap.view(hot, 4, True)['state'] in ('STEADY', 'GROW')   # under 50 exits: no long record to hold it back
    base = {'value': 4.0, 'putIn': 37.0, 'cash': 4.0, 'open': True}
    w = of.warden(1.0, {**base, 'capital': {'state': 'GROW', 'mult': 1.0, 'floor': 0.75, 'why': 'x', 'rugCapPct': 10.0}})
    assert w['allowed'] == 0.25 and any(r['id'].startswith('W24') for r in w['rules'])          # $1 asked, 10% of a $4 card = $0.40 → the ×0.25 step
    assert not any(r['id'].startswith('W24') for r in of.warden(0.30, {**base, 'capital': {'state': 'GROW', 'mult': 1.0, 'floor': 0.75, 'why': 'x', 'rugCapPct': 10.0}})['rules'])   # already inside the budget
