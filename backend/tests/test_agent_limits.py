"""🎛 The owner's limits on agent buys (price gap · sell-back · smallest pool · curve depth) and the ARMED entry mode."""
import fuse_wallet as fw
import office_edge as oe
import ai_router as air
import ai_learn as ail


def _pair(liq, dex='raydium', mc=20000.0):
    return {'baseToken': {'address': 'M'}, 'priceUsd': '0.00002', 'liquidity': {'usd': liq}, 'dexId': dex, 'marketCap': mc}


def test_the_owners_pool_floor_and_curve_switch_reach_the_keepers_gate():
    cfg = fw.clean_cfg({})
    o = {'side': 'buy', 'mint': 'M', 'agent': True, 'trench': True}
    fw.set_agent_limits({})
    assert fw.live_buy_market(o, _pair(5000), cfg)[0] is False                 # the $8K trench floor
    fw.set_agent_limits({'agentPoolMin': 5000})
    assert fw.live_buy_market(o, _pair(5000), cfg)[0] is True                  # the owner's own $5K floor
    fw.set_agent_limits({'agentPoolMin': 1000})
    assert fw.live_buy_market(o, _pair(2900), cfg)[0] is False                 # never under $3K
    # a coin still on its curve: refused as a "$2.4K pool" unless the owner's agentCurve is on — then the curve's own depth is used
    fw.set_agent_limits({})
    assert fw.live_buy_market(o, _pair(2400, 'pumpfun'), cfg)[0] is False
    fw.set_agent_limits({'agentCurve': True})
    ok, _why, lv = fw.live_buy_market(o, _pair(2400, 'pumpfun'), cfg)
    assert ok and lv['liq'] > 8000
    assert fw.live_buy_market({**o, 'agent': False}, _pair(2400, 'pumpfun'), cfg)[0] is False   # an engine order never reads the agents' switch
    fw.set_agent_limits({})


def test_the_owners_price_gap_and_sell_back_limits_reach_buy_safety():
    o = {'agent': True, 'usd': 1.0, 'midPx': 1.0, 'lamports': 1_000_000}
    q_out = int(1 / 1.05 * 1e6)                                              # a quote 5% over the market reading
    fw.set_agent_limits({})
    assert fw.buy_safety(o, q_out, 6, 990_000)[0] is False                    # the agents' default 2.5%
    fw.set_agent_limits({'agentGapPct': 6})
    assert fw.buy_safety(o, q_out, 6, 990_000)[0] is True
    assert fw.buy_safety(o, int(1e6), 6, 930_000)[0] is False                 # sells back 7% lower > 3.5%
    fw.set_agent_limits({'agentGapPct': 6, 'agentBackPct': 10})
    assert fw.buy_safety(o, int(1e6), 6, 930_000)[0] is True
    assert fw.buy_safety(o, int(1e6), 6, 0)[0] is False                       # no route back never moves
    fw.set_agent_limits({})


def test_armed_entry_fills_an_empty_seat_past_the_owners_target_at_half_a_seat():
    c = [{'mint': 'A', 'status': 'CONTENDING', 'trigger': 'ARM', 'rank': 90, 'size': 0.75},
         {'mint': 'B', 'status': 'CONTENDING', 'trigger': 'ARM', 'rank': 110, 'size': 1.0},
         {'mint': 'C', 'status': 'CONTENDING', 'trigger': 'WAIT', 'rank': 200, 'size': 1.0},
         {'mint': 'D', 'status': 'CONTENDING', 'trigger': 'ARM', 'rank': 300, 'size': 0.0},
         {'mint': 'E', 'status': 'CONTENDING', 'trigger': 'ARM', 'rank': 250, 'size': 1.0}]
    assert oe.armed_fill(c, 100.0, 15, 110.0, have=0, need=2) == []            # the seat has not waited the owner's 15s yet
    got = oe.armed_fill(c, 100.0, 15, 120.0, have=0, need=2, blocked={'E'})
    assert [x['mint'] for x in got] == ['B', 'A']                               # never WAIT, never a 0 size, never a blocked coin
    assert oe.armed_fill(c, 100.0, 15, 120.0, have=2, need=2) == []            # enough READY coins: nothing armed comes in
    assert 0 < oe.ARMED_SIZE < 1
    p = oe.policy({'agentEntry': 'armed', 'agentSeatTarget': 15, 'agentGapPct': 6, 'agentBackPct': 7, 'agentPoolMin': 5000})
    assert p['entry'] == 'armed' and p['seatTarget'] == 15 and (p['gapPct'], p['backPct'], p['poolMin']) == (6, 7, 5000)
    assert oe.clean_policy({'agentGapPct': 99, 'agentPoolMin': 1})['agentGapPct'] == 0 and oe.clean_policy({'agentPoolMin': 1})['agentPoolMin'] == 0


def test_the_text_scout_is_parsed_strictly_and_judged_like_every_read():
    a = air.parse_advice({'summary': 'copy of the og, callers pasting one line', 'confidence_delta': -0.1,
                          'scout': {'original': False, 'thesis': 'swarm', 'site': 'weird', 'tech': 140}, 'rules': [{'act': 'avoid', 'when': ['flow:SELLERS'], 'name': 'into sellers'}]})
    assert a['scout'] == {'original': False, 'thesis': 'swarm', 'tech': 100} and a['rules'][0]['when'] == ['flow:SELLERS']
    b = ail.note({}, 'devil', 'M', 'CAUTION', 1.0, 100.0, 'M', 1, a['scout'], True)
    c = b['open'][0]
    assert c['atFill'] and set(ail.buckets_of(c)) >= {'SCOUT:COPY', 'SCOUT:SWARM', 'SCOUT:TECH', 'AT:FILL'}
    # the same stance on the same coin minutes later at the scan is a separate record from the fill read
    b = ail.note(b, 'sherlock', 'M', 'CAUTION', 1.0, 200.0)
    assert len(b['open']) == 2


def test_the_keepers_last_look_uses_the_same_agent_pool_floor_as_the_pre_check():
    """The live gate read the agents' $5K floor while `check` read the $8K trench floor: a seat was made, then its buy refused, on a loop."""
    cfg = fw.clean_cfg({'armed': True, 'walletId': 'w', 'address': 'A'})
    o = {'side': 'buy', 'mint': 'M', 'agent': True, 'trench': True, 'usd': 0.25, 'liq': 6200}
    fw.set_agent_limits({})
    assert fw.buy_floor(o, cfg) == 8000 and 'too thin' in fw.check(o, cfg, [], 0.0)[1]
    fw.set_agent_limits({'agentPoolMin': 5000})
    assert fw.buy_floor(o, cfg) == 5000 and fw.check(o, cfg, [], 0.0)[0] is True
    assert fw.live_buy_market(o, _pair(6200), cfg)[0] is True
    assert fw.buy_floor({**o, 'agent': False}, cfg) == 8000        # an engine order keeps the keeper's own floor
    fw.set_agent_limits({})


def test_the_owners_band_is_judged_on_the_live_cap_before_a_seat_exists():
    import asyncio
    import reputation_service as rs
    import trench_kernel.universe as uni
    plan = [{'mint': 'LIVEpump', 'pair': 'P1', 'symbol': 'LIVE', 'vitals': {}}, {'mint': 'DEADpump', 'pair': 'P2', 'symbol': 'DEAD', 'vitals': {}}]

    async def live(_orders):
        return {'P1': {'baseToken': {'address': 'LIVEpump'}, 'priceUsd': '0.5', 'liquidity': {'usd': 50000}, 'dexId': 'pumpswap', 'marketCap': 40000},
                'P2': {'baseToken': {'address': 'DEADpump'}, 'priceUsd': '0.5', 'liquidity': {'usd': 50000}, 'dexId': 'pumpswap', 'marketCap': 2993}}
    old, band = rs._fw_live_pairs, uni.band()
    rs._fw_live_pairs = live
    uni.set_band({'agentMcMin': 12000, 'agentMcMax': 500000})
    rs._agent_refused.clear(); rs._seat_pre_ok.clear()
    try:
        ok = asyncio.run(rs._seat_precheck(plan, {}, 1000.0, need=3))
    finally:
        rs._fw_live_pairs = old
        uni.set_band({'agentMcMin': band[0], 'agentMcMax': band[1]})
    assert set(ok) == {'LIVEpump'} and 'outside your' in rs._agent_refused['DEADpump'][1]
    rs._agent_refused.clear(); rs._seat_pre_ok.clear()
