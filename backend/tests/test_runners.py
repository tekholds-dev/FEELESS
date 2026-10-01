"""FUSE RUNNERS engine: hard gates fail closed, scoring cites reasons, lanes, carry-over rounds, exit ladders, proof, add-on."""
import pytest
import runners as rn

rs = pytest.importorskip("reputation_service")

NOW = 1_800_000_000_000


def pair(mint, chg1h=120, chg5m=10, vol1h=60_000, mcap=40_000, curve=80, graduated=False, age_h=3, buys=600, sells=400, price=0.0001):
    return {'baseToken': {'address': mint, 'symbol': mint.upper()}, 'pairAddress': f'P{mint}', 'dexId': 'pumpswap' if graduated else 'pumpfun', 'graduated': graduated,
            'curveProgress': curve, 'pairCreatedAt': NOW - age_h * 3.6e6, 'marketCap': mcap, 'priceUsd': str(price),
            'volume': {'m5': vol1h / 10, 'h1': vol1h}, 'priceChange': {'m5': chg5m, 'h1': chg1h, 'h24': chg1h}, 'txns': {'h1': {'buys': buys, 'sells': sells}}, 'quality': {'score': 70}}


CLEAN = {'top10Pct': 18, 'insidersHoldingPct': 3, 'devHoldingPct': 2, 'bundledWallets': []}


def test_gates_fail_closed_and_flag_reasons():
    ok = rn.candidate(pair('a'), CLEAN, now_ms=NOW)
    assert rn.failed_gates(ok) == []
    assert 'Holder scan done' in rn.failed_gates(rn.candidate(pair('a'), None, now_ms=NOW))                 # unscanned = out
    assert 'Top 10 under 30%' in rn.failed_gates(rn.candidate(pair('a'), {**CLEAN, 'top10Pct': 45}, now_ms=NOW))
    assert 'Creator not flagged (Bot shield / blocklist)' in rn.failed_gates(rn.candidate(pair('a'), CLEAN, creator_flagged=True, now_ms=NOW))
    assert 'Two-sided flow (40–85% buys, 50+ trades/h)' in rn.failed_gates(rn.candidate(pair('a', buys=990, sells=10), CLEAN, now_ms=NOW))
    assert 'Under 48h old' in rn.failed_gates(rn.candidate(pair('a', age_h=60), CLEAN, now_ms=NOW))


def test_score_lanes_and_board():
    hot = rn.candidate(pair('hot', chg1h=300, chg5m=30, curve=85), CLEAN, snipers_out=True, now_ms=NOW)
    meh = rn.candidate(pair('meh', chg1h=10, chg5m=0, curve=20), CLEAN, now_ms=NOW)
    b = rn.board([meh, hot, rn.candidate(pair('bad'), {**CLEAN, 'top10Pct': 80}, now_ms=NOW)])
    assert [r['mint'] for r in b['passing']] == ['hot', 'meh'] and b['dropped'][0]['mint'] == 'bad'
    assert all(p['why'] for p in b['passing'][0]['parts'])
    assert rn.lane_of(hot) == 'scalp' and rn.lane_of(meh) == 'runner' and rn.lane_of(meh, streak=2, pts=75) == 'hold'


def test_rounds_keep_best_runners_and_count_streaks():
    cs = [rn.candidate(pair(m, chg1h=c, price=1.0), CLEAN, now_ms=NOW) for m, c in (('a', 300), ('b', 250), ('c', 200), ('d', 50), ('e', 40), ('f', 30))]
    r1 = rn.next_round(None, rn.board(cs)['passing'], now=100, size=3)
    assert [p['mint'] for p in r1['picks']] == ['a', 'b', 'c'] and all(p['streak'] == 1 for p in r1['picks'])
    cs2 = [rn.candidate(pair(m, chg1h=c, price=2.0), CLEAN, now_ms=NOW) for m, c in (('a', 400), ('x', 350), ('b', 10), ('c', 380), ('y', 300), ('z', 290), ('w', 280), ('v', 270))]
    r2 = rn.next_round(r1, rn.board(cs2)['passing'], now=200, size=3)
    kept = {p['mint']: p for p in r2['picks']}
    assert kept['a']['streak'] == 2 and kept['a']['entry'] == 1.0 and kept['c']['streak'] == 2      # stayed, keep entry
    assert 'b' not in kept and {'mint': 'b', 'symbol': 'B'} in r2['out'] and 'x' in kept


def test_exit_ladders():
    assert rn.play_exits('scalp', 1.0, [1.2, 1.55, 3.0]) == 1.55                 # all out into the +50% rush
    assert rn.play_exits('scalp', 1.0, [0.9, 0.7]) == 0.7                        # stop −25%
    # runner: ⅓ at 1.5, ⅓ at 2.0, rest trails 25 pts from a +150% peak → out at +120%
    assert abs(rn.play_exits('runner', 1.0, [1.5, 2.0, 2.5, 2.2]) - (1.5 / 3 + 2.0 / 3 + 2.2 / 3)) < 1e-3
    assert rn.play_exits('hold', 1.0, [1.1, 1.4, 1.05]) == 1.05                  # trail 30 from +40%
    assert rn.play_exits('runner', 1.0, []) == 1.0


def test_proof_lights_only_when_winning_enough():
    rounds = [{'at': i * 10, 'picks': [{'mint': 'a', 'lane': 'scalp', 'entry': 1.0}]} for i in range(8)]
    win = rn.proof(rounds, {'a': [(t, 1.6) for t in range(1, 200)]}, now=100)
    assert win['rounds'] == 8 and win['avgPct'] == 60 and win['lights'] and win['per1'] == 1.6
    lose = rn.proof(rounds, {'a': [(t, 0.7) for t in range(1, 200)]}, now=100)
    assert not lose['lights'] and lose['winRate'] == 0
    assert rn.proof(rounds[:3], {'a': [(t, 1.6) for t in range(1, 200)]}, now=100)['need'] == 5


def test_addon_bolts_two_runners_onto_any_fuse():
    legs = [{'pairAddress': 'X', 'weight': 60}, {'pairAddress': 'Y', 'weight': 40}]
    out = rn.addon(legs, [{'pairAddress': 'R1', 'mint': 'm1', 'lane': 'scalp'}, {'pairAddress': 'R2', 'mint': 'm2'}, {'pairAddress': 'R3'}])
    assert [l['pairAddress'] for l in out] == ['X', 'Y', 'R1', 'R2'] and out[0]['weight'] == 48 and out[2]['weight'] == 10
    assert abs(sum(l['weight'] for l in out) - 100) < 0.01 and out[2]['runner'] and 'Sell all' in out[2]['exits']
    assert rn.addon(legs, []) == legs


def test_service_board_rounds_proof_and_addon(monkeypatch):
    import asyncio
    import time as _t
    import pytest
    now_ms = _t.time() * 1000
    feed = [pair(m, chg1h=c, price=1.0) for m, c in (('aaa', 300), ('bbb', 200), ('ccc', 150))] + [pair('rug', chg1h=999)]
    for p in feed:
        p['pairCreatedAt'] = now_ms - 2 * 3.6e6
    async def live_pairs():
        return None
    async def fake_intel(mint): return {**CLEAN, 'top10Pct': 90 if mint == 'rug' else 18}
    class H:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None):
            class R:
                def json(self): return {'pairs': feed if params and params.get('kind') == 'trending' else []}
            return R()
    monkeypatch.setattr(rs.httpx, 'AsyncClient', H); monkeypatch.setattr(rs, '_runner_intel', fake_intel)
    rs._runner_live_cache.update(at=0, data=None)
    b = asyncio.run(rs.runners_board())
    assert [r['mint'] for r in b['live']] == ['aaa', 'bbb', 'ccc'] and b['dropped'][0]['mint'] == 'rug' and b['round'] is None
    r1 = asyncio.run(rs._runner_tick(force=True))
    assert [p['mint'] for p in r1['picks']] == ['aaa', 'bbb', 'ccc']
    b2 = asyncio.run(rs.runners_board())
    assert b2['round']['picks'][0]['exits'] and b2['proof']['lights'] is False and b2['proof']['need'] > 0
    async def pairs(legs): return {l['pairAddress']: {'pairAddress': l['pairAddress'], 'priceUsd': '1', 'liquidity': {'usd': 9e5}, 'volume': {'h24': 5e5}, 'priceChange': {'h24': 3},
                                                        'baseToken': {'symbol': l.get('symbol') or 'X', 'address': 'B' + l['pairAddress']}} for l in legs}
    async def px(): return 150.0
    monkeypatch.setattr(rs, '_fuse_pairs', pairs); monkeypatch.setattr(rs, '_sol_usd_live', px)
    pv = asyncio.run(rs.fuses_preview(rs.FusePreview(pools=[{'chainId': 'solana', 'pairAddress': 'X1'}, {'chainId': 'solana', 'pairAddress': 'X2'}], sol=1, runners=True)))
    assert pv['runners'] == 2 and [l['pairAddress'] for l in pv['legs'] if l.get('runner')] == ['Paaa', 'Pbbb']
    assert abs(sum(l['weight'] for l in pv['legs']) - 100) < 0.1 and round(sum(l['sol'] for l in pv['legs']), 6) == 1


def test_config_changes_gates_exits_and_light_threshold():
    cfg = rn.clean_cfg({'maxTop10': 50, 'scalpTp': 80, 'lightRounds': 3, 'roundSize': 99, 'runnerTp1': 200, 'runnerTp2': 100})
    assert cfg['roundSize'] == 10 and cfg['runnerTp2'] == 210                                   # clamped + ordered
    c = rn.candidate(pair('a'), {**CLEAN, 'top10Pct': 40}, now_ms=NOW)
    assert 'Top 10 under 30%' in rn.failed_gates(c) and rn.failed_gates(c, cfg) == []
    assert rn.play_exits('scalp', 1.0, [1.6, 1.9], cfg) == 1.9 and 'Sell all at +80%' in rn.exits(cfg)['scalp']['label']
    rounds = [{'at': i, 'picks': [{'mint': 'a', 'lane': 'runner', 'entry': 1.0}]} for i in range(3)]
    assert rn.proof(rounds, {'a': [(t, 1.3) for t in range(1, 50)]}, now=10, cfg=cfg)['lights']


def test_card_preview_with_picked_runners(monkeypatch):
    import asyncio
    import time as _t
    import pytest
    live = {'passing': [{**rn.candidate(pair(m, price=1.0), CLEAN, now_ms=NOW), 'score': 80, 'lane': 'runner'} for m in ('r1', 'r2', 'r3', 'r4')], 'dropped': [], 'seen': 4}
    async def fake_live(): return live
    async def pairs(legs): return {l['pairAddress']: {'pairAddress': l['pairAddress'], 'priceUsd': '1', 'liquidity': {'usd': 9e5}, 'volume': {'h24': 5e5}, 'priceChange': {'h24': 3},
                                                        'baseToken': {'symbol': 'S', 'address': 'B' + l['pairAddress']}} for l in legs}
    async def px(): return 150.0
    monkeypatch.setattr(rs, '_runner_live', fake_live); monkeypatch.setattr(rs, '_fuse_pairs', pairs); monkeypatch.setattr(rs, '_sol_usd_live', px)
    pools = [{'chainId': 'solana', 'pairAddress': f'X{i}'} for i in range(3)]
    pv = asyncio.run(rs.fuses_preview(rs.FusePreview(pools=pools, sol=1, runnerMints=['r1', 'r2', 'r3'])))
    assert sum(1 for l in pv['legs'] if l.get('runner')) == 3 and abs(sum(l['weight'] for l in pv['legs']) - 100) < .1
    assert round(sum(l['weight'] for l in pv['legs'] if l.get('runner'))) == 30
    only = asyncio.run(rs.fuses_preview(rs.FusePreview(pools=[], sol=1, runnerMints=['r1', 'r2'])))
    assert [round(l['weight']) for l in only['legs']] == [50, 50]
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.fuses_preview(rs.FusePreview(pools=pools, sol=1, runnerMints=['gone'])))
    with pytest.raises(rs.HTTPException, match='3 pools \\+ 3 runners'):                          # traders: 3 runners max, refused clearly
        asyncio.run(rs.fuses_preview(rs.FusePreview(pools=pools, sol=1, runnerMints=['r1', 'r2', 'r3', 'r4'])))


def test_prebond_only_no_mayhem_and_creator_rep():
    assert 'Pre-bond (still on the curve)' in rn.failed_gates(rn.candidate(pair('g', graduated=True), CLEAN, now_ms=NOW))
    assert 'Not a mayhem-mode coin' in rn.failed_gates(rn.candidate(pair('m'), CLEAN, now_ms=NOW, mayhem=True))
    assert 'Creator reputation not suspect / high-risk' in rn.failed_gates(rn.candidate(pair('s'), CLEAN, now_ms=NOW, creator_rep='suspect'))
    clean = rn.score(rn.candidate(pair('c'), CLEAN, now_ms=NOW, creator_rep='clean'))[0]
    watch = rn.score(rn.candidate(pair('c'), CLEAN, now_ms=NOW, creator_rep='watch'))[0]
    assert round(clean - watch, 1) == 15 and rn.failed_gates(rn.candidate(pair('c'), CLEAN, now_ms=NOW, creator_rep='watch')) == []


def test_engine_dial_and_dial_proof():
    c = rn.engine_dial('safe')
    assert c['dial'] == 'safe' and c['roundSize'] == 3 and c['maxTop10'] == 22 and rn.engine_dial('balanced')['maxTop10'] == rn.RECOMMENDED['maxTop10'][0]
    with pytest.raises(ValueError):
        rn.engine_dial('x')
    rounds = [{'at': i, 'picks': [{'mint': 'a', 'entry': 1.0}]} for i in range(8)]
    paths = {'a': [(t, 1.0 + 0.1 * (t % 10)) for t in range(1, 60)]}       # climbs to 1.9 then resets
    pr = rn.dial_proof(rounds, paths, 50, {'safe': {'runner': (30, 15)}, 'degen': {'runner': (100, 40)}})
    assert pr['safe']['avgPct'] == 48.75 and pr['safe']['lit'] and pr['degen']['rounds'] == 8


def test_prebond_volume_goes_a_long_way():
    base = {'mint': 'M', 'chg1h': 40, 'chg5m': 4, 'mcap': 60000, 'buyShare': 62, 'stage': 'curve', 'curve': 80, 'snipersOut': False, 'quality': 50}
    thin, busy = rn.score({**base, 'vol1h': 8000}), rn.score({**base, 'vol1h': 300000})
    part = lambda r, k: next(p['points'] for p in r[1] if p['part'] == k)
    assert part(busy, 'volume') > 13 and part(thin, 'volume') < 2
    assert part(thin, 'stage') == 5.0 and part(busy, 'stage') == 10.0          # thin pre-bond curve gets half
    grad = rn.score({**base, 'stage': 'graduated', 'vol1h': 300000})
    assert part(grad, 'volume') == round(part(busy, 'volume') / 2, 1)          # pre-bond weighs volume double
    assert busy[0] - thin[0] > 15


def test_fresh_grads_fill_the_board_only_when_every_other_gate_passes():
    rows = [{'mint': 'G', 'stage': 'graduated', 'gates': ['Pre-bond (still on the curve)']},
            {'mint': 'X', 'stage': 'graduated', 'gates': ['Pre-bond (still on the curve)', 'Top 10 under 25%']},
            {'mint': 'C', 'stage': 'curve', 'gates': ['Top 10 under 25%']}]
    assert [r['mint'] for r in rn.fresh_grads(rows)] == ['G'] and 'grad' in rn.SOURCES


def test_dead_board_widens_soft_gates_only_within_floors():
    base = rn.clean_cfg({'maxTop10': 25, 'minMcap': 12000, 'minVol1h': 10000, 'maxInsiders': 10, 'maxDev': 5})
    w3 = rn.widen(base, 3)
    assert w3['maxTop10'] == 35 and w3['minMcap'] == 6000 and w3['minVol1h'] == 4000          # soft gates loosened, clamped
    assert w3['maxInsiders'] == 10 and w3['maxDev'] == 5                                        # safety gates never move
    assert rn.widen(base, 9) == w3 and rn.widen(rn.clean_cfg({'minMcap': 8000}), 3)['minMcap'] == 5000   # max 3 steps, never past the floor
    assert rn.widen(base, 0) == base
    assert rn.widen_level(0, 0) == 1 and rn.widen_level(3, 0) == 3 and rn.widen_level(2, 9) == 1 and rn.widen_level(1, 5) == 1
