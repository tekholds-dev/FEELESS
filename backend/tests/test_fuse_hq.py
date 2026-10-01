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
