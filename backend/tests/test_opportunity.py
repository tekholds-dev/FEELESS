"""🎯 RANK, DON'T VETO: hard danger = NO · imperfect but good = smaller yes · strong = yes (owner's spec, 2026-10-11)."""
import agents as ag
import office as of
import office_edge as oe
import opportunity as op


def row(m='X', **k):
    base = {'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': 1.0, 'go': False, 'warns': [], 'objs': [], 'why': {'lean': 0.5, 'drivers': []},
            'vitals': {'safe': True, 'mcap': 80_000, 'liq': 40_000, 'rug': 10, 'vol1h': 60_000, 'top10': 18, 'ageH': 0.5},
            'nums': {'liq': 40_000, 'd5': 3.0, 'buy': 60, 'pace': 1.6, 'c1': 600, 'age': 0.5}, 'trigger': ['wait', 'lean under the bar'],
            'chart': {'state': 'UPTREND', 'q': {'state': 'TRUSTED'}, 'risk': [0.5]}}
    for kk, vv in k.items():
        base[kk] = {**base[kk], **vv} if isinstance(vv, dict) and isinstance(base.get(kk), dict) else vv
    return base


def test_hard_safety_still_blocks():
    for bad in (row(vitals={'safe': False}), row(vitals={'safe': None}), row(nums={'liq': 5_000}, vitals={'liq': 5_000}), row(vitals={'rug': 70}),
                row(vitals={'mcap': 350_000}), row(vitals={'mcap': 9_000}), row(objs=[['rug_signs', 'x']]), row(chart={'state': 'BOT LADDER'}), row(nums={'d5': 55}), row(nums={'d5': -20}), row(px=0)):
        assert op.hard_fail(bad), bad


def test_minor_warning_is_not_a_veto_and_ranks_lower():
    clean, warned = row('A'), row('B', warns=[['young', 'new'], ['busted_read', 'WASH TRADED']])
    assert op.hard_fail(warned) is None
    got = op.rank([warned, clean])
    assert [r['mint'] for r in got] == ['A', 'B'] and got[1]['oppRaw'] < got[0]['oppRaw']   # (both may show 100: the order is the raw total)


def test_early_launch_and_huge_launch_return_are_not_overextension():
    young = row(nums={'c1': 900, 'age': 0.2, 'd5': 22}, vitals={'ageH': 0.2}, chart={'state': 'EARLY', 'q': {'state': 'SPARSE'}, 'risk': [0.5]})
    assert op.hard_fail(young) is None and op.tier_of(op.score(young)[0]) is not None   # +900% since launch, a +22% candle: ranked, not killed
    warns = []
    assert ag.devil_args('enter', {'c1': 900, 'age': 0.2}, {'lean': 2, 'drivers': []}, {'safe': True}, {}, warns=warns) == []
    assert any(w[0] == 'ran' for w in warns)                                                                # a warning, not a veto
    assert ag.devil_args('enter', {'c1': 900, 'age': 5}, {'lean': 2, 'drivers': []}, {'safe': True}, {})[0][0] == 'ran'   # a mature coin's +900% hour still vetoes
    assert ag.trigger({'d5': 25, 'age': 0.3, 'liq': 50_000, 'pts': 5}, {'lean': 3, 'drivers': []}, {'safe': True}, {})[0] != 'skip'
    assert ag.trigger({'d5': 25, 'age': 10, 'liq': 50_000, 'pts': 5}, {'lean': 3, 'drivers': []}, {'safe': True}, {})[0] == 'skip'


def test_tiers_and_warden_size_by_confidence():
    strong = row('S', go=True, why={'lean': 3.0, 'drivers': []})
    mid = row('M')
    weak = row('W', chart={'state': 'COMPRESSION', 'q': {'state': 'SPARSE'}, 'risk': [0.5]}, nums={'d5': -2, 'buy': 48, 'pace': 0.8}, vitals={'vol1h': 8_000, 'top10': 32})
    t = {r['mint']: r['tier'] for r in op.rank([strong, mid, weak])}
    assert t['S'] == 'A' and t['M'] in ('A', 'B') and t['W'] in ('B', 'C')
    base = {'liq': 500_000, 'ageH': 30, 'courier': 'OK', 'near': 'x'}
    a, b, c = (of.warden(1.0, {**base, 'tier': k})['allowed'] for k in ('A', 'B', 'C'))
    assert a == 1.0 and abs(b - 0.75) < 1e-9 and abs(c - 0.5) < 1e-9


def test_fresh_high_volume_coins_rank_first():
    old = row('OLD', vitals={'ageH': 60, 'vol1h': 12_000}, nums={'pace': 0.9, 'age': 60})
    fresh = row('NEW', vitals={'ageH': 0.4, 'vol1h': 250_000}, nums={'pace': 2.4})
    assert [r['mint'] for r in op.rank([old, fresh])][0] == 'NEW'


def test_accelerating_winner_is_not_banked_on_a_turn():
    import inspect
    src = inspect.getsource(of.reap)
    assert "'R7s structure turned'" in src and "vl.get('state') != 'ACCELERATING'" in src


def test_counts_for_the_page():
    st = {}
    op.rank([row('A'), row('B', vitals={'safe': False}), row('C', vitals={'mcap': 900_000})], stats=st)
    assert st['considered'] == 3 and st['hard'] == 2 and st['A'] + st['B'] + st['C'] == 1


def test_the_tier_shrinks_on_top_of_the_other_rules_never_masked_by_them():
    young = {'liq': 500_000, 'ageH': 0.1, 'courier': 'OK', 'near': 'x'}                  # W4 young already halves the seat
    a, c = (of.warden(1.0, {**young, 'tier': k})['allowed'] for k in ('A', 'C'))
    assert a == 0.5 and c == 0.25 and c < a                                              # as the "smallest rule" C was masked: both read 0.5


def test_a_lower_confidence_seat_risks_less():
    assert op.tier_of_tag('🤖 agents · C-tier') == 'C' and op.tier_of_tag('🤖 agents · best available') is None and op.tier_of_tag(None) is None
    assert op.TIER_STOP['C'] < op.TIER_STOP['B'] < op.TIER_STOP['A'] <= 30
    import inspect
    assert '_opp.TIER_STOP[tier_]' in inspect.getsource(of.reap)   # Reaper only ever tightens with it


def test_shrinking_is_never_a_veto():
    hostile = {'liq': 500_000, 'ageH': 30, 'courier': 'OK', 'near': 'x', 'tier': 'C', 'weather': {'regime': 'HOSTILE', 'mods': {'size': 0.25}}}
    w = of.warden(1.0, hostile)
    assert not w['veto'] and w['allowed'] > 0                                # HOSTILE × C-tier used to snap to 0 = a veto (bitdog)
    assert of.warden(1.0, {**hostile, 'courier': 'BAD'})['veto']             # a real ×0 rule (execution BAD) still vetoes


def test_a_collapsed_coin_waits_for_a_higher_low_and_stolen_links_are_a_no():
    import opportunity as op
    assert op.knife({'chart': {'distHigh': 45, 'hl': 0, 'll': 2}}).startswith('🔪')
    assert op.knife({'chart': {'distHigh': 45, 'hl': 2, 'll': 0}}) is None      # a higher low printed: allowed
    assert op.knife({'chart': {'distHigh': 10}}) is None and op.knife({}) is None
    assert op.links_conflict({}) is None


def test_the_owners_dip_needs_a_ten_percent_bounce_off_the_floor():
    import opportunity as op
    assert op.knife({'chart': {'distHigh': 45, 'distLow': 4}}).startswith('🔪')         # still on the floor
    assert op.knife({'chart': {'distHigh': 45, 'distLow': 14}}) is None                 # rose 14% off the floor: a dip
