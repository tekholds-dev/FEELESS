"""FUSE HQ: real position P&L, book rollup, paper arena settle + board, best style needs proof, bloodline seeds, health."""
import fuse
import fuse_hq as hq
from test_fuse import _metas


def test_position_pnl_and_book():
    pos = {'id': 'x', 'wallet': 'W', 'fuseId': 'F1', 'name': 'Core', 'legs': [{'pairAddress': 'A', 'usd': 2, 'tokens': 100}, {'pairAddress': 'B', 'usd': 3, 'tokens': 10}]}
    r = hq.position_pnl(pos, {'A': 0.03, 'B': 0})          # A doubled+, B unpriced → at cost
    assert r['valueUsd'] == 6 and r['pnlUsd'] == 1 and r['legs'][1]['priced'] is False and r['pnlPct'] == 20
    b = hq.book([r, hq.position_pnl({**pos, 'id': 'y', 'wallet': 'V'}, {'A': 0.01, 'B': 0.3})])
    assert b['positions'] == 2 and b['winners'] == 1 and b['fuses'][0]['wallets'] == 2 and b['costUsd'] == 10


def test_arena_settles_and_best_style_needs_three_winning_runs():
    champ = {'fitness': 80, 'legs': [{'pairAddress': 'A', 'weight': 50}, {'pairAddress': 'B', 'weight': 50}]}
    e = hq.arena_entry(champ, 'degen', {'A': 1, 'B': 2}, now=0, eid='e1')
    live = hq.arena_value(e, {'A': 1.2, 'B': 2}, now=3600)
    assert live['pnlPct'] == 10 and not live['due'] and hq.arena_value(e, {}, now=90000)['due']
    settled = [hq.arena_value({**e, 'close': {'A': 1.2, 'B': 2}}, {}, 99999) for _ in range(2)]
    assert hq.best_style(hq.arena_board(settled)) == 'yield'               # 2 runs isn't proof
    settled.append(settled[0])
    board = hq.arena_board(settled, sol_change_pct=3)
    assert hq.best_style(board) == 'degen' and board[0]['beatsSol'] and board[0]['winRate'] == 100


def test_bloodline_seeds_evolution_and_health_flags_beaten():
    m = _metas()
    assert hq.bloodline_seeds([{'pools': ['p1', 'p2', 'p3']}, {'pools': ['p1', 'gone', 'p2']}], set(m), 3) == [['p1', 'p2', 'p3']]
    seeded = fuse.evolve(m, legs=3, generations=1, population=8, seeds=[['p7', 'p8', 'p9']], seed=1)
    assert seeded['champions'][0]['fitness'] >= fuse.fitness(['p7', 'p8', 'p9'], m)['fitness']
    assert hq.health(50, 60)['beaten'] and not hq.health(58, 60)['beaten']


def test_outlook_is_honest_until_proven():
    assert hq.outlook([])['proven'] is False
    o = hq.outlook([{'style': 'yield', 'runs': 4, 'avgPct': 3.0, 'winRate': 75}])
    assert o['proven'] and o['per1'] == 1.03 and o['per100'] == 103.0 and 'not a promise' in o['note']
    assert hq.outlook([{'style': 'degen', 'runs': 5, 'avgPct': -4.0, 'winRate': 20}])['proven'] is False


def test_receipt_before_after_and_pending():
    q = [{'sig': 'A', 'symbol': 'AAA', 'usd': 5, 'tokens': 100, 'feeUsd': 0.05, 'networkUsd': 0.02}, {'sig': 'B', 'symbol': 'BBB', 'usd': 5, 'tokens': 10, 'feeUsd': 0.05, 'networkUsd': 0.02}]
    r = hq.receipt(q, {'A': {'usd': 5.03, 'tokens': 98, 'feelessFeeUsd': 0.05, 'networkUsd': 0.01, 'via': 'chain'}})
    a, b = r['legs']
    assert a['slippagePct'] == 2.0 and a['exact'] and a['paidFeesUsd'] == 0.06 and b['pending'] and not r['settled']
    assert r['quotedFeesUsd'] == 0.14 and r['paidUsd'] == 5.03
    full = hq.receipt(q, {'A': {'usd': 5, 'tokens': 100}, 'B': {'usd': 5, 'tokens': 10}})
    assert full['settled'] and full['feePct'] == 0.0


def test_autopilot_once_per_hour_per_style_and_trust_rank():
    arena = [{'style': 'yield', 'auto': True, 'at': 1000}, {'style': 'degen', 'at': 1000}]
    assert not hq.autopilot_due(arena, 'yield', 2000) and hq.autopilot_due(arena, 'yield', 5000)
    assert hq.autopilot_due(arena, 'degen', 2000)                       # manual entries don't block autopilot
    assert hq.trust_rank(60, 0, 0) == 60 and hq.trust_rank(60, 10, 10) == 75 and hq.trust_rank(60, 1, 1) == 63
    assert hq.trust_rank(60, 10, 2) < hq.trust_rank(60, 10, 9)


def test_unfuse_realizes_from_sells_once():
    pos = {'id': 'x', 'legs': [{'pairAddress': 'A', 'mint': 'MA', 'usd': 2, 'tokens': 100}, {'pairAddress': 'B', 'mint': 'MB', 'usd': 3, 'tokens': 10}]}
    pos, n = hq.close_legs(pos, [{'tx': 's1', 'token': 'MA', 'usd': 2.6}])
    assert n == 1 and pos['legs'][0]['soldUsd'] == 2.6
    r = hq.position_pnl(pos, {'A': 999, 'B': 0.3})                      # sold leg ignores live price
    assert r['legs'][0]['valueUsd'] == 2.6 and not r['closed']
    pos, n2 = hq.close_legs(pos, [{'tx': 's2', 'token': 'MA', 'usd': 9}, {'tx': 's3', 'token': 'MB', 'usd': 3.3}])
    assert n2 == 1 and pos['legs'][0]['soldUsd'] == 2.6 and hq.position_pnl(pos, {})['closed']


def test_fuse_card_meta_and_svg_are_safe():
    v = {'name': '<script>x</script>', 'creatorBps': 2500, 'score': {'grade': 'A'}, 'legs': [{'symbol': 'A&B', 'weight': 60}, {'symbol': 'C', 'weight': 40}]}
    m = hq.card_meta('f1', v, 'https://feeless.app')
    assert m['symbol'] == 'FUSE' and m['image'].endswith('/fuse-card/f1.svg') and {'trait_type': 'Rarity', 'value': 'Legendary'} in m['attributes'] and '25%' in m['description']
    svg = hq.card_svg(v)
    assert '<script>' not in svg and '&lt;script&gt;' in svg and 'A&amp;B' in svg and svg.startswith('<svg')


def test_basket_limits():
    import pytest
    g = hq.clean_guard({'tp': 50, 'sl': 20, 'trail': 0})
    assert g == {'tp': 50, 'sl': 20, 'trail': None}
    with pytest.raises(ValueError):
        hq.clean_guard({})
    assert hq.guard_check(g, 55)[0] == 'tp' and hq.guard_check(g, -21)[0] == 'sl' and hq.guard_check(g, 10)[0] is None
    t = {'trail': 15, 'peak': 40}
    assert hq.guard_check(t, 30) == (None, 40) and hq.guard_check(t, 24)[0] == 'trail' and hq.guard_check(t, 60) == (None, 60)


def test_creator_season_ranks_by_buyers_real_pnl():
    fz = {'F1': {'creator': 'C1', 'name': 'Core'}, 'F2': {'creator': 'C2', 'name': 'Meme'}}
    R = lambda w, f, cost, val, at=10: {'wallet': w, 'fuseId': f, 'costUsd': cost, 'valueUsd': val, 'pnlUsd': val - cost, 'at': at}
    rows = [R('a', 'F1', 10, 12), R('b', 'F1', 10, 11), R('C1', 'F1', 100, 500), R('a', 'F2', 10, 30), R('old', 'F1', 10, 0, at=1)]
    b = hq.creator_board(rows, fz, since=5)
    assert b[0]['creator'] == 'C1' and b[0]['buyers'] == 2 and b[0]['pnlPct'] == 15.0 and b[0]['ranked']   # creator's own 5x ignored
    assert b[1]['creator'] == 'C2' and not b[1]['ranked']                                                  # one buyer can't rank


def test_yield_math_is_honest():
    m = {'a': {'liquidityUsd': 2e6, 'aprEst': 365, 'change24h': 40}, 'b': {'liquidityUsd': 5e5, 'aprEst': 73, 'change24h': -30},
         'c': {'liquidityUsd': 1e6, 'aprEst': 0, 'change24h': 2}, 'tiny': {'liquidityUsd': 900, 'aprEst': 90000, 'change24h': 900}}
    y = hq.yield_math(m)
    assert y['pools'] == 3 and y['vaultAprPct'] == 146.0 and y['vaultPerDay']['1'] == 0.004       # tiny pool ignored
    assert y['aprFor20c'] == 7300 and y['fuse1'] == {'best': 1.4, 'median': 1.02, 'worst': 0.7}


def test_card_take_profit_switch_and_withdraw():
    pos = {'id': 'c', 'legs': [{'pairAddress': 'A', 'mint': 'MA', 'usd': 10, 'tokens': 100, 'role': 'pool'}, {'pairAddress': 'R', 'mint': 'MR', 'usd': 5, 'tokens': 50, 'role': 'runner'}]}
    pos, n = hq.close_legs(pos, [{'tx': 't1', 'token': 'MA', 'usd': 8, 'tokens': 40}], now=1)        # take 40% of A for $8
    a = pos['legs'][0]
    assert n == 1 and a['tokens'] == 60 and a['realizedUsd'] == 8 and a.get('soldUsd') is None
    r = hq.position_pnl(pos, {'A': 0.2, 'R': 0.1})                                                   # A: 60×0.2 + 8 = 20
    assert r['legs'][0]['valueUsd'] == 20 and r['legs'][0]['heldUsd'] == 12 and r['realizedUsd'] == 8 and r['legs'][0]['priceIn'] == 0.1
    pos, _ = hq.close_legs(pos, [{'tx': 't2', 'token': 'MR', 'usd': 6, 'tokens': 50}], now=2)       # switch-out runner R
    pos, added = hq.add_legs(pos, [{'tx': 'b1', 'token': 'MX', 'usd': 6, 'tokens': 30}], [{'pairAddress': 'X', 'symbol': 'X', 'role': 'runner'}], now=3)
    assert added == 1 and pos['legs'][1]['soldUsd'] == 6 and pos['legs'][2]['role'] == 'runner'
    pos, _ = hq.add_legs(pos, [{'tx': 'b%d' % i, 'token': 'P%d' % i, 'usd': 1, 'tokens': 1} for i in range(5)], [{'pairAddress': 'p%d' % i} for i in range(5)])
    assert sum(1 for l in pos['legs'] if l['role'] == 'pool' and l.get('soldUsd') is None) == 3                # pool cap 3
    assert [e['kind'] for e in pos['events']][:3] == ['sell', 'sell', 'buy']
    assert hq.card_limit(199) == 2 and hq.card_limit(200) == 3 and hq.card_limit(0, admin=True) == 10


def test_topup_merges_and_drift():
    pos = {'legs': [{'pairAddress': 'A', 'mint': 'MA', 'usd': 10, 'tokens': 100, 'role': 'pool'}]}
    pos, n = hq.add_legs(pos, [{'tx': 'b', 'token': 'MA', 'usd': 5, 'tokens': 40}], [{'pairAddress': 'A', 'role': 'pool'}])
    assert n == 1 and len(pos['legs']) == 1 and pos['legs'][0]['usd'] == 15 and pos['legs'][0]['tokens'] == 140 and pos['events'][-1]['kind'] == 'topup'
    row = {'legs': [{'usd': 10, 'heldUsd': 30}, {'usd': 10, 'heldUsd': 10}]}
    assert hq.drift(row) == 25.0 and hq.drift({'legs': [{'usd': 1, 'heldUsd': 1}]}) == 0.0



def test_card_entries_and_sells_use_pool_value_never_fees():
    import fuse_hq as h
    assert h.pool_usd({'usd': 10.5, 'poolUsd': 10.0}) == 10.0 and h.pool_usd({'usd': 7}) == 7.0
    pos = {'legs': [{'mint': 'M', 'tokens': 10, 'usd': 10, 'symbol': 'X'}]}
    pos, n = h.close_legs(pos, [{'token': 'M', 'tokens': 10, 'usd': 11.2, 'poolUsd': 12.0, 'tx': 's'}], now=1)
    assert n == 1 and pos['legs'][0]['soldUsd'] == 12.0                                           # gross at the pool, fee not deducted


def test_one_rotation_per_24h():
    assert hq.next_switch_at({}) == 0 and hq.next_switch_at({'lastSwitchAt': 1000}) == 1000 + 86400
    assert hq.next_switch_at({'lastSwitchAt': 1000}, staff=True) == 0


def test_risk_dial_sets_the_whole_plan_server_side():
    legs = [{'pairAddress': 'P'}, {'pairAddress': 'R', 'runner': True}]
    p = hq.risk_plan('degen', legs)
    assert p['legs'] == {'P': {'tp': 100, 'sl': 40}, 'R': {'tp': 100, 'sl': 40}} and p['mode'] == 'swap' and p['onProfit'] == 'compound'
    c = hq.clean_plan({'risk': 'safe', 'legs': {'P': {'tp': 999}}, 'at': 7}, {}, ['P', 'R'], runner_pairs=['R'])
    assert c['risk'] == 'safe' and c['legs']['P'] == {'tp': 30, 'sl': 15} and c['at'] in hq.clean_rules({})['yieldLevels'] and c['mode'] == 'hold'
    assert hq.clean_plan({'legs': {'P': {'tp': 40}}}, {}, ['P'])['risk'] == 'custom'
    import pytest
    with pytest.raises(ValueError):
        hq.risk_plan('yolo', legs)


def test_yield_math_uses_replay_and_drops_outliers():
    metas = {'a': {'liquidityUsd': 2e5, 'aprEst': 50, 'change24h': 3400, 'replayPct': 12}, 'b': {'liquidityUsd': 3e5, 'aprEst': 20, 'change24h': -5},
             'c': {'liquidityUsd': 4e5, 'aprEst': 10, 'replayPct': 900}}
    y = hq.yield_math(metas)
    assert y['fuse1']['best'] == 1.12 and y['fuse1']['worst'] == 0.95      # 3400% since launch never counts; 900% replay = outlier


def test_feecat_weekly_note_has_no_holder_pnl():
    t = hq.feecat_weekly('degen', 2, True, 4.25)
    assert 'degen dial' in t and '2 engine settings tuned' in t and '+4.2%' in t and 'beat her' in t
    t2 = hq.feecat_weekly(None, 0, False, None)
    assert 'custom dial' in t2 and 'tuned' not in t2 and 'no trades' in t2 and 'she beat your cards' in t2


def test_card_rotation_interval_and_park_buyback():
    pos = {'lastSwitchAt': 1000, 'plan': {'rotateHours': 6}}
    assert hq.next_switch_at(pos) == 1000 + 6 * 3600
    assert hq.next_switch_at({'lastSwitchAt': 1000, 'plan': {'rotateHours': 99}}) == 1000 + 24 * 3600   # not an option → 24h
    assert hq._extras({'slMode': 'park', 'rotateHours': 1}) == {'rotateHours': 1, 'slMode': 'park'}
    assert hq._extras({}) == {'rotateHours': 24, 'slMode': 'sell'}
    assert hq.buyback_due({'entry': 1.0}, 1.02, {'buyShare': 60, 'chg1h': 3}) and not hq.buyback_due({'entry': 1.0}, 0.9, {'buyShare': 60})
    assert not hq.buyback_due({'entry': 1.0}, 1.1, {'buyShare': 40, 'chg1h': -2})


def test_playground_lists_what_is_ready_for_the_arena():
    board = [{'style': 'degen', 'runs': 5, 'avgPct': 4.2, 'winRate': 60}, {'style': 'steady', 'runs': 1, 'avgPct': 2, 'winRate': 100}]
    dials = {'6h': {'degen': {'rounds': 10, 'avgPct': 3}, 'safe': {'rounds': 10, 'avgPct': -2}}, '24h': {'degen': {'rounds': 30, 'avgPct': 2}, 'safe': {'rounds': 30, 'avgPct': -1}}}
    prime = [{'label': 'Gold', 'pnlPct': 13, 'lowPct': -3}, {'label': 'Blaze', 'pnlPct': -6, 'lowPct': -14}]
    out = hq.playground_ready(board, dials, prime, min_settled=3)
    ready = {(r['kind'], r['name']) for r in out['ready']}
    assert ready == {('strategy', 'degen'), ('dial', 'degen'), ('tier card', 'Gold')}
    assert any(p['name'] == 'steady' and 'needs 2 more' in p['why'] for p in out['proving'])
