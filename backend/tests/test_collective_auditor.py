import collective_auditor as ca
import collective_pool as cp
import collective_stake as sk


def test_every_hard_case_adds_up_to_the_unit():
    for name, r in ca.suite(300).items():
        assert r['problems'] == [], (name, r['problems'][:3])


def test_the_auditor_catches_what_it_is_for():
    st, _r, tape = ca._new(2, 1); ca._send(st, tape, 'k', 'a', 'o', 'USDC', 100.0, 1000.0, 300)
    assert ca.laws(st, tape) == []
    st['books']['USDC']['keep'] += 5; assert 'does not add up' in ca.laws(st, tape)[0]     # a single unit found
    st['books']['USDC']['keep'] -= 5; st['agents']['a']['owed']['USDC'] = -1; assert any('negative' in x for x in ca.laws(st, tape))
    st['agents']['a']['owed']['USDC'] = 0; st['agents']['a']['paidUsd'] = 1e9; assert any('past its points' in x for x in ca.laws(st))
    st2 = cp.new_state(); assert ca.laws(st2) == [] and sk.pay_profit(st2, 'x', 'USDC', 0, 1e-6, 1.0) is None


def test_a_parlay_is_counted_in_legs_and_a_pop_needs_a_real_reason():
    import pob
    import pop
    assert pob.legs_of('nba 3 leg parlay') == 3 and pob.legs_of('five-leg parlay') == 5 and pob.legs_of('parlay tonight') == 3 and pob.legs_of('best nba picks') == 0 and pob.legs_of('12 leg parlay') == 3
    assert 'parlay of 4 legs' in pob.topic_sys('A', '4 leg parlay') and 'parlay' not in pob.topic_sys('A', 'nba picks').lower()
    good = '{"market":"SOL","side":"long","lev":2,"tp_pct":2,"sl_pct":1,"why":"Funding -0.0035%/h on Hyperliquid and OI up 12%, wrong below 88"}'
    assert pop.parse_call(good)['side'] == 'long' and pop.parse_call(good.replace('Funding -0.0035%/h on Hyperliquid and OI up 12%, wrong below 88', 'Momentum looks good here')) is None


def test_debate_points_keep_every_law_when_real_profit_pays_them():
    import collective_auditor as au
    got = au.stress(n=300, debate=True, rounds=120)
    assert got['problems'] == [] and got['splits'] > 10


def test_the_money_trail_of_a_debate_point():
    """In: nothing. It only lets a stake keep earning longer. Out: only from a real profit, never past the room, and what it held stays the same."""
    import collective_auditor as au
    import collective_stake as sk
    def run(debate):
        st, _r, tape = au._new(2, 1)
        au._send(st, tape, 's1', 'a', 'oa', 'USDC', 100, 1000, 100.0); au._send(st, tape, 's2', 'b', 'ob', 'USDC', 100, 1000, 100.0)
        cut_before = sk.cuts(st, 1000)
        if debate:
            assert sk.add_debate(st, 'room1', 'a', 200, 1000) == 10.0
            assert sk.cuts(st, 1000) == cut_before   # the cut does not move, and nobody else's does
        for k in range(400):
            sk.pay_profit(st, f'p{k}', 'USDC', 10 ** 9, 1e-6, 1000 + k)
        return sk.of(st['agents']['a']), sk.of(st['agents']['b'])
    plain_a, plain_b = run(False); more_a, more_b = run(True)
    assert plain_a['paidUsd'] == plain_a['capUsd'] and more_a['paidUsd'] == plain_a['paidUsd'] + 10.0   # it earned $10 more, only from profit
    assert more_b['paidUsd'] == plain_b['paidUsd'] and more_a['sentUsd'] == 100
