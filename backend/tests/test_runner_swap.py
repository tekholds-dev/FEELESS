"""Runner rounds stay clean: one failing pick swapped per check, closed on paper; lit rounds become tracked cards."""
import runners as rn


def pick(m, price=1.0, score=80):
    return {'mint': m, 'symbol': m, 'price': price, 'score': score, 'stage': 'graduated', 'curve': 100, 'chg1h': 10, 'ageH': 5}


def test_one_failing_pick_is_swapped_and_closed_on_paper():
    rnd = {'id': 'r1', 'at': 100, 'picks': [{**pick('A'), 'entry': 1.0, 'lane': 'runner', 'streak': 1}, {**pick('B'), 'entry': 1.0, 'lane': 'runner', 'streak': 1},
                                           {**pick('C'), 'entry': 1.0, 'lane': 'runner', 'streak': 1}]}
    paths = {'A': [[150, 1.2]], 'B': [[150, 0.9]]}
    out, swap = rn.swap_failing(rnd, [pick('B'), pick('D', price=2.0)], {'A': ['dev now holds 18%'], 'C': ['insiders 30%']}, paths, now=200)
    assert swap['out']['mint'] == 'A' and swap['in']['mint'] == 'D' and swap['why'] == ['dev now holds 18%']
    assert [p['mint'] for p in out['picks']] == ['D', 'B', 'C']             # only ONE swap per check
    assert out['picks'][0]['entry'] == 2.0 and out['picks'][0]['swappedIn'] == 200
    assert swap['mult'] == 1.2                                               # A's paper result up to the swap
    again, s2 = rn.swap_failing(out, [pick('E')], {'C': ['insiders 30%']}, paths, now=300)
    assert s2['out']['mint'] == 'C' and len(again['swaps']) == 2
    assert rn.swap_failing(rnd, [], {'A': ['x']}, paths, now=200)[1] is None   # nothing passing → keep it


def test_proof_counts_swapped_out_results_and_new_pick_only_after_joining():
    rnd = {'id': 'r', 'at': 100, 'picks': [{'mint': 'D', 'entry': 2.0, 'lane': 'runner', 'swappedIn': 200}], 'swaps': [{'mult': 1.2}]}
    paths = {'D': [[150, 9.0], [250, 2.2]]}                                  # the 9.0 print was BEFORE D joined → ignored
    p = rn.proof([rnd], paths, now=300)
    assert p['rounds'] == 1 and p['avgPct'] == 15.0                          # (1.2 + 1.1) / 2


def test_lit_card_snapshot_and_result():
    rnd = {'id': 'r9', 'at': 100, 'picks': [{'mint': 'A', 'symbol': 'A', 'lane': 'runner', 'entry': 1.0}, {'mint': 'B', 'symbol': 'B', 'lane': 'runner', 'entry': 1.0}]}
    card = rn.lit_card(rnd, {'rounds': 9, 'avgPct': 6.5, 'winRate': 66, 'lights': True})
    assert card['proof'] == {'rounds': 9, 'avgPct': 6.5, 'winRate': 66} and len(card['picks']) == 2
    assert rn.card_result(card, {'A': [[150, 1.3]], 'B': [[150, 0.9]]}, now=200) == 10.0


def test_tick_swaps_a_failing_pick_and_snapshots_lit_rounds(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    live = {'passing': [pick('B'), pick('D', price=2.0)], 'dropped': [{**pick('A'), 'gates': ['dev now holds 18%']}], 'seen': 3}
    async def lv(): return live
    async def tp(m): return {}
    monkeypatch.setattr(rs, '_runner_live', lv); monkeypatch.setattr(rs, '_token_prices', tp)
    rs._json_save(rs.RUNNERS_PATH, {'rounds': [{'id': 'r1', 'at': 1000, 'picks': [{**pick('A'), 'entry': 1.0, 'lane': 'runner', 'streak': 1, 'enteredAt': 1000}, {**pick('B'), 'entry': 1.0, 'lane': 'runner', 'streak': 1, 'enteredAt': 1000}]}], 'paths': {}})
    asyncio.run(rs._runner_tick(now=1100))                                   # mid-round → swap, not a new round
    d = rs._json_load(rs.RUNNERS_PATH, {})
    assert len(d['rounds']) == 1 and [p['mint'] for p in d['rounds'][0]['picks']] == ['D', 'B'] and d['rounds'][0]['swaps'][0]['why'] == ['dev now holds 18%']
    monkeypatch.setattr(rs._rn, 'proof', lambda *a, **k: {'rounds': 9, 'avgPct': 5.0, 'winRate': 60, 'lights': True, 'per1': 1.05, 'need': 0})
    asyncio.run(rs._runner_tick(now=1000 + rs._rn.ROUND_SECONDS + 1))         # new round while lit → lit card
    assert len(rs._json_load(rs.RUNNERS_PATH, {})['litCards']) == 1


def test_discovery_is_gated_and_ranks_by_independent_sources():
    passing = [pick('A', score=70), pick('B', score=90), pick('C', score=95)]
    tags = {'A': {'arena': 'in round', 'creator': 'called by @sharp'}, 'B': {'pump': 'top scan'}, 'X': {'creator': 'called'}}   # X fails gates → hidden
    out = rn.discover(passing, tags)
    assert [r['mint'] for r in out] == ['A', 'B']                        # C has no source; X isn't passing
    assert [s['kind'] for s in out[0]['sources']] == ['arena', 'creator'] and out[0]['sources'][1]['label'] == "📣 Creators' pick"


def test_discover_endpoint_tags_every_source(monkeypatch):
    import asyncio
    import time
    import pytest
    rs = pytest.importorskip('reputation_service')
    now = time.time()
    live = {'passing': [pick('A'), pick('B'), pick('C')], 'dropped': [], 'seen': 3}
    async def lv(): return live
    async def board(days=30): return {'rows': [{'callerAddress': 'K', 'calls': 5, 'hitRate': 0.6}]}
    monkeypatch.setattr(rs, '_runner_live', lv); monkeypatch.setattr(rs, 'caller_board', board)
    rs._runner_disc_cache.update(at=0, data=None)
    rs._json_save(rs.RUNNERS_PATH, {'rounds': [{'id': 'r1', 'at': now, 'picks': [{**pick('A'), 'entry': 1, 'lane': 'runner'}]}], 'paths': {}})
    rs._json_save(rs.CALLS_PATH, {'calls': {'c1': {'callerAddress': 'K', 'caller': 'sharp', 'mint': 'B', 'at': now}}})
    monkeypatch.setitem(rs._radar, 'events', [{'kind': 'snipers-out', 'mint': 'C', 'at': now, 'pair': 'pC'}])
    out = asyncio.run(rs.runners_discover())
    kinds = {r['mint']: [s['kind'] for s in r['sources']] for r in out['runners']}
    assert 'arena' in kinds['A'] and 'creator' in kinds['B'] and 'snipers' in kinds['C']
    assert out['counts']['arena'] == 1 and out['counts']['snipers'] == 1


def test_lit_card_rebuilds_with_two_strong_and_comes_down_when_weak_wins():
    card = {'id': 'L', 'at': 100, 'picks': [{'mint': m, 'symbol': m, 'lane': 'runner', 'entry': 1.0} for m in ('A', 'B', 'C')]}
    paths = {'A': [[150, 1.2]], 'B': [[150, 1.1]], 'C': [[150, 0.6]]}                       # C is −40%
    passing = [pick('A'), pick('B'), pick('N', price=2.0, score=95)]
    c2, what = rn.rebuild_lit(card, paths, passing, {}, 200)
    assert what == 'swap' and [p['mint'] for p in c2['picks']] == ['A', 'B', 'N'] and c2['picks'][2]['swappedIn'] == 200
    assert c2['swaps'][0]['out']['mint'] == 'C' and 'down -40.0%' in c2['swaps'][0]['why']
    assert rn.card_result(c2, paths, 200) == round(((1.2 + 1.1 + 0.6 + 1.0) / 4 - 1) * 100, 2)   # C's result is kept
    # only one strong left → the card is taken down (kept in history)
    down, what = rn.rebuild_lit(card, paths, [pick('A')], {'B': ['dev now holds 18%']}, 200)
    assert what == 'down' and down['downAt'] == 200 and '1 strong of 3' in down['downWhy']
    assert rn.rebuild_lit(down, paths, passing, {}, 300) == (down, None)
    healthy = {**card, 'picks': card['picks'][:2]}
    assert rn.rebuild_lit(healthy, paths, passing, {}, 200) == (healthy, None)


def test_bond_run_needs_every_box_and_cmd_ctr_tunes_them():
    base = {'stage': 'curve', 'curve': 93, 'buyShare': 64, 'chg5m': 4, 'chg1h': 40, 'vol1h': 20000, 'mcap': 40000, 'snipersOut': True, 'quality': 50,
            'creatorRep': 'clean', 'top10': 25, 'curveSpeed': 10, 'buysAccel': 1.5}
    assert rn.near_bond(base) and rn.bond_tier(base) == 'run'
    assert [x['id'] for x in rn.bond_check(base)] == ['curve', 'buys', 'green', 'vol', 'holders', 'creator', 'speed', 'accel']
    for k, v in (('buyShare', 58), ('chg5m', -1), ('vol1h', 9000), ('creatorRep', None), ('curveSpeed', 3), ('curveSpeed', None), ('buysAccel', 1.0)):
        assert not rn.near_bond({**base, k: v}), k                                              # stiff: one miss = no boost
    assert not rn.near_bond({**base, 'snipersOut': False}) and rn.near_bond({**base, 'snipersOut': False, 'top10': 12})
    assert rn.bond_check({**base, 'stage': 'graduated'}) == [] and rn.bond_check({**base, 'curve': 60}) == []
    pts, parts = rn.score(base); pts0, _ = rn.score({**base, 'chg5m': -0.1})
    assert any(p['part'] == 'bond run' and p['points'] == 15 for p in parts) and pts > pts0
    full = {**base, 'mint': 'M', 'symbol': 'M', 'liq': 5000, 'scanned': True, 'insiders': 0, 'dev': 0, 'bundled': 0, 'ageH': 1, 'txns1h': 200,
            'mayhem': False, 'creatorFlagged': False, 'chg24h': 40, 'price': 1, 'vol5m': 1000}
    row = (rn.board([full])['passing'] or rn.board([full])['dropped'])[0]
    assert len(row['bond']) == 8 and row['bondTier'] == 'run' and rn.lane_of(row) == 'bond'
    assert rn.SOURCES['bond'] == '🔔 About to bond'


def test_bond_watch_at_75_is_rep_confirmed():
    w = {'stage': 'curve', 'curve': 80, 'buyShare': 64, 'chg5m': 4, 'vol1h': 20000, 'snipersOut': True, 'creatorRep': 'clean', 'curveSpeed': 10, 'buysAccel': 1.5,
         'smartBuyers': 3, 'flaggedFunders': 0, 'devSold': False}
    assert rn.bond_tier(w) == 'watch' and not rn.near_bond(w) and len(rn.bond_check(w)) == 11
    for k, v in (('smartBuyers', 2), ('flaggedFunders', 1), ('devSold', True)):
        assert rn.bond_tier({**w, k: v}) is None, k                                              # the rep confirmation is required
    pts, parts = rn.score({**w, 'chg1h': 0, 'mcap': 1, 'quality': 0})
    assert any(p['part'] == 'bond watch' and p['points'] == 7.5 for p in parts)
    assert rn.bond_tier({**w, 'curve': 74}) is None and rn.bond_tier({**w, 'curve': 74}, {'bondWatchCurve': 70}) == 'watch'


def test_kill_switch_gates_and_tunable_flow():
    c = {'stage': 'curve', 'mayhem': False, 'ageH': 1, 'mcap': 50000, 'vol1h': 20000, 'buyShare': 60, 'txns1h': 100, 'scanned': True, 'top10': 10,
         'insiders': 1, 'bundled': 0, 'dev': 1, 'creatorFlagged': False, 'creatorRep': 'clean', 'top10Jump': 2, 'devSold': False}
    assert rn.failed_gates(c) == []
    assert any('top-10 spike' in g for g in rn.failed_gates({**c, 'top10Jump': 12}))
    assert "Dev hasn't sold" in rn.failed_gates({**c, 'devSold': True})
    assert rn.failed_gates({**c, 'bundled': 2}) == [] and rn.failed_gates({**c, 'bundled': 2}, {'maxBundled': 1})
    assert rn.failed_gates({**c, 'buyShare': 50}, {'minBuyShare': 52})


def test_stronger_engine_suggestions_only_where_weaker():
    s = {x['key']: x for x in rn.suggest_cfg({})}
    assert s['minMcap']['to'] == 12000 and s['maxTop10']['to'] == 25 and s['roundSize']['to'] == 4 and s['maxDev']['why']
    assert rn.suggest_cfg({k: v[0] for k, v in rn.RECOMMENDED.items()}) == []
    assert 'maxTop10' not in {x['key'] for x in rn.suggest_cfg({'maxTop10': 20})}                 # already stricter: leave it


def test_lanes_self_tune_from_their_own_results():
    now = 10 * 86400
    rounds = [{'at': now - d * 86400 - 60, 'picks': [{'mint': f'L{d}', 'lane': 'scalp', 'entry': 1.0}, {'mint': f'W{d}', 'lane': 'runner', 'entry': 1.0}]} for d in range(3)]
    paths = {**{f'L{d}': [[now - d * 86400, 0.7]] for d in range(3)}, **{f'W{d}': [[now - d * 86400, 1.2]] for d in range(3)}}
    pr = rn.lane_proofs(rounds, paths, now)
    assert pr['scalp']['losingDays'] == 3 and pr['runner']['losingDays'] == 0 and pr['runner']['n'] == 3
    w = rn.lane_weights(pr)
    assert w['scalp'] == 0.5 and w['runner'] == 1.0                                               # <10 picks: not "best proven" yet
    assert rn.lane_weights({'runner': {'n': 12, 'avgPct': 5, 'winRate': 60, 'losingDays': 0}})['runner'] == 1.25
    ranked = rn.next_round(None, [pick('A', score=80), {**pick('B', score=60), 'stage': 'graduated'}], now, size=1, weights={'runner': 1.0, 'scalp': 0.5})
    assert ranked['picks'][0]['mint'] == 'A'



def test_arena_build_takes_best_coins_and_pools_with_honest_entries():
    passing = [pick('A', price=1.0, score=70), pick('B', price=2.0, score=90), {**pick('C', price=3.0, score=50), 'stage': 'curve', 'curve': 95, 'buyShare': 70, 'chg5m': 3,
               'vol1h': 50000, 'snipersOut': True, 'creatorRep': 'clean', 'curveSpeed': 12, 'buysAccel': 2}, pick('D', price=1.0, score=40), pick('E', price=1.0, score=30)]
    pools = [{'pairAddress': f'pool{i}', 'symbol': f'P{i}', 'priceUsd': 1.0 + i, 'liquidityUsd': 500000, 'aprEst': 50 * i, 'change24h': 2} for i in range(5)]
    pools.append({'pairAddress': 'thin', 'priceUsd': 1, 'liquidityUsd': 5000, 'aprEst': 999, 'change24h': 5})
    passing = [{**x, 'pairAddress': f"pa{x['mint']}"} for x in passing]
    card = rn.auto_card(passing, pools, 100)
    coins = [l for l in card['legs'] if l.get('runner')]
    assert [l['baseAddress'] for l in coins] == ['C', 'B', 'A', 'D']                              # bond run first, then score
    assert [l['pairAddress'] for l in card['legs'] if not l.get('runner')] == ['pool4', 'pool3', 'pool2']   # thin pool never
    assert round(sum(l['weight'] for l in card['legs'])) == 100 and coins[0]['entry'] == 3.0
    assert len([l for l in rn.auto_card(passing, pools, 1, {'autoCoins': 2, 'autoPools': 1})['legs']]) == 3


def test_battles_pair_by_heat_and_settle_on_the_move_since_the_bell():
    cards = [{'id': i, 'activity': {'score': s}} for i, s in ((1, 10), (2, 90), (3, 50), (4, 70), (5, 5))]
    assert [(a['id'], b['id']) for a, b in rn.pair_battles(cards)] == [(2, 4), (3, 1)]
    assert rn.settle_battle(0, 5, 10, 12) == 'a' and rn.settle_battle(0, 1, 0, 4) == 'b' and rn.settle_battle(0, 1, 5, 6.02) == 'draw'
