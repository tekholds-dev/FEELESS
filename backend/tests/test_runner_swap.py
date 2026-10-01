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


def test_near_bond_runners_get_the_boost_and_their_own_source():
    base = {'stage': 'curve', 'curve': 92, 'buyShare': 62, 'chg5m': 4, 'chg1h': 40, 'vol1h': 20000, 'mcap': 40000, 'snipersOut': False, 'quality': 50}
    assert rn.near_bond(base) and not rn.near_bond({**base, 'curve': 70}) and not rn.near_bond({**base, 'chg5m': -1})
    assert not rn.near_bond({**base, 'stage': 'graduated'}) and not rn.near_bond({**base, 'buyShare': 40})
    pts, parts = rn.score(base); pts0, _ = rn.score({**base, 'chg5m': -0.1})
    assert any(p['part'] == 'bond run' and p['points'] == rn.BOND_PTS for p in parts) and pts > pts0
    assert rn.SOURCES['bond'] == '🔔 About to bond'
