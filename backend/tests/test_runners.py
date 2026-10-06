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
    assert 'Under 48h old (to 30 days while it trades hard)' in rn.failed_gates(rn.candidate(pair('a', age_h=60), CLEAN, now_ms=NOW))


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
    gone = asyncio.run(rs.fuses_preview(rs.FusePreview(pools=pools, sol=1, runnerMints=['gone'])))   # skipped + reported, never a wall
    assert [x['mint'] for x in gone['droppedRunners']] == ['gone']
    with pytest.raises(rs.HTTPException, match='3 pools \\+ 3 runners'):                          # traders: 3 runners max, refused clearly
        asyncio.run(rs.fuses_preview(rs.FusePreview(pools=pools, sol=1, runnerMints=['r1', 'r2', 'r3', 'r4'])))


def test_prebond_only_no_mayhem_and_creator_rep():
    assert 'Pre-bond or a fresh graduate (<48h)' not in rn.failed_gates(rn.candidate(pair('g', graduated=True), CLEAN, now_ms=NOW))   # young graduates run too
    assert 'Not a mayhem-mode coin' in rn.failed_gates(rn.candidate(pair('m'), CLEAN, now_ms=NOW, mayhem=True))
    assert 'Creator not a rugger (suspect = coin must prove itself)' not in rn.failed_gates(rn.candidate(pair('s'), CLEAN, now_ms=NOW, creator_rep='suspect'))   # clean numbers prove it
    assert 'Creator not a rugger (suspect = coin must prove itself)' in rn.failed_gates(rn.candidate(pair('s'), CLEAN, now_ms=NOW, creator_rep='high'))
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


def test_engine_auto_pick_switches_only_on_proven_edge():
    proof = {'safe': {'rounds': 60, 'avgPct': -10.7}, 'balanced': {'rounds': 60, 'avgPct': -8.3}, 'degen': {'rounds': 60, 'avgPct': 2.3}}
    d, why = rn.auto_pick(proof, 'balanced')
    assert d == 'degen' and 'over 60 rounds' in why
    assert rn.auto_pick(proof, 'degen') == (None, None)                                   # already on the best
    assert rn.auto_pick({'degen': {'rounds': 3, 'avgPct': 9}}, 'safe') == (None, None)    # not enough rounds
    assert rn.auto_pick({'degen': {'rounds': 30, 'avgPct': 1.0}, 'safe': {'rounds': 30, 'avgPct': 0.5}}, 'safe') == (None, None)   # under margin


def test_auto_strength_needs_agreement_across_windows():
    good = {'degen': {'rounds': 40, 'avgPct': 3}, 'balanced': {'rounds': 40, 'avgPct': -2}}
    bad = {'degen': {'rounds': 40, 'avgPct': -1}, 'balanced': {'rounds': 40, 'avgPct': 0.5}}
    assert rn.auto_pick_multi({'6h': good, '24h': good, '72h': good}, 'balanced')[0] == 'degen'
    assert rn.auto_pick_multi({'6h': good, '24h': good, '72h': bad}, 'balanced') == (None, None)       # 72h disagrees → stay
    assert rn.auto_pick_multi({'6h': good}, 'balanced') == (None, None)                                # one window is never enough


def test_engine_scenarios_cycle_21_cards_best_first():
    dials = {'safe': {'runner': (30, 15)}, 'balanced': {'runner': (50, 30)}, 'degen': {'runner': (100, 40)}}
    out = rn.scenarios([], {}, 1000, dials)
    assert len(out) == 12 + 9 and {s['kind'] for s in out} == {'exits', 'dial'} and all('label' in s for s in out)


def test_scenario_winner_becomes_the_runner_exits_only_when_windows_agree():
    g = lambda best: {'tp200_sl15': {'rounds': 30, 'avgPct': best}, 'tp100_sl30': {'rounds': 30, 'avgPct': 1.0}}
    assert rn.exits_pick({'24h': g(18), '72h': g(9)}, (100, 30))[0] == (200, 15)
    assert rn.exits_pick({'24h': g(18)}, (100, 30)) == (None, None)                          # one window is never enough
    assert rn.exits_pick({'24h': g(18), '72h': g(0.5)}, (100, 30)) == (None, None)           # 72h best is tp100 → disagree
    assert rn.exits_pick({'24h': g(18), '72h': g(9)}, (200, 15)) == (None, None)             # already running it


def test_best_scenarios_become_cards_from_this_rounds_picks():
    scen = [{'id': 'degen_6h', 'label': 'degen dial · 6h', 'window': '6h', 'tp': 100, 'sl': 40, 'rounds': 18, 'avgPct': 23.6},
            {'id': 'tp200_sl15', 'label': 'TP +200%', 'window': '24h', 'tp': 200, 'sl': 15, 'rounds': 65, 'avgPct': 19},
            {'id': 'safe_6h', 'label': 'safe', 'window': '6h', 'tp': 30, 'sl': 15, 'rounds': 18, 'avgPct': -7}]
    picks = [{'pairAddress': 'P1', 'symbol': 'A'}, {'pairAddress': 'P2', 'symbol': 'B'}]
    cards = rn.scenario_cards(scen, picks, {'chainId': 'solana', 'pairAddress': 'SOLP', 'symbol': 'SOL'})
    assert [c['id'] for c in cards] == ['degen_6h', 'tp200_sl15']                                # losing scenarios never become cards
    assert [(l['symbol'], l['weight']) for l in cards[0]['legs']] == [('SOL', 35), ('A', 32.5), ('B', 32.5)] and cards[1]['legs'][1]['tp'] == 200
    assert cards[0]['dial'] == 'degen' and cards[0]['name'] in rn.CARD_NAMES['degen'] and cards[0]['cfg']['rotateHours'] == 1   # simple degen names + configs
    assert rn.scenario_cards(scen, []) == []


def test_gate_regret_finds_gates_that_stop_winners():
    log = rn.log_drops([], [{'mint': 'A', 'pairAddress': 'PA', 'symbol': 'A', 'stage': 'curve', 'gates': ['Top 10 under 25%'], 'price': 1.0},
                            {'mint': 'B', 'pairAddress': 'PB', 'symbol': 'B', 'stage': 'curve', 'gates': ['Top 10 under 25%'], 'price': 1.0},
                            {'mint': 'C', 'pairAddress': 'PC', 'symbol': 'C', 'stage': 'graduated', 'gates': ['Pre-bond'], 'price': 1.0}], 0)
    assert [e['mint'] for e in log] == ['A', 'B'] and rn.log_drops(log, [{'mint': 'A', 'stage': 'curve', 'gates': ['x'], 'price': 2}], 100) == log
    out = rn.gate_regret(log, {'PA': 4.0, 'PB': 0.5}, 7 * 3600)
    assert out[0]['gate'] == 'Top 10 under 25%' and out[0]['stopped'] == 2 and out[0]['ran'] == 1 and out[0]['rate'] == 50.0


def test_card_names_dials_and_battle_seats():
    assert rn.dial_of(200, 15) == 'degen' and rn.dial_of(30, 15) == 'safe' and rn.dial_of(100, 25) == 'balanced' and rn.dial_of(30, 15, 'degen') == 'degen'
    n = rn.card_name('degen', 'tp200_sl40')
    assert n == rn.card_name('degen', 'tp200_sl40') and n in rn.CARD_NAMES['degen'] and 1 <= len(n.split(' ')[0]) <= 4
    st = lambda k, s: {'id': k, 'activity': {'score': s}}
    seats = rn.battle_seats([st('s1', 50)], [st('b1', 10), st('b2', 30), st('b3', 20), st('b4', 5)])
    assert len(seats) == 2 and 'b4' not in {c['id'] for p in seats for c in p}      # 4 cards → 2 battles, best runners-up fill seats
    seats = rn.battle_seats([st(f's{i}', i) for i in range(5)], [st('b1', 99)])
    assert len(seats) == 2 and all(c['id'].startswith('s') for p in seats for c in p)  # a full stage never seats the bench
    assert rn.battle_seats([], [st('b1', 1)]) == []


def test_new_runners_tight_launch_filter():
    ok = {'mint': 'A', 'ageH': 0.5, 'scanned': True, 'site': True, 'x': True, 'top10': 18, 'dev': 2, 'bundled': 0, 'buyShare': 64, 'vol1h': 9000, 'creatorRep': 'clean'}
    rows = [ok, {**ok, 'mint': 'B', 'x': False}, {**ok, 'mint': 'C', 'ageH': 5}, {**ok, 'mint': 'D', 'creatorRep': 'suspect'}, {**ok, 'mint': 'E', 'top10': 40},
            {**ok, 'mint': 'F', 'creatorRep': None, 'vol1h': 20000}]
    got = rn.new_runners(rows)
    assert [r['mint'] for r in got] == ['A', 'F'] and '🧼 clean creator' in got[0]['why']          # clean creators first
    assert rn._socials({'info': {'websites': [{'url': 'x'}], 'socials': [{'type': 'twitter'}]}}) == {'site': True, 'x': True, 'tg': False}


def test_playground_versions_and_where_listed():
    cards = [{'id': 'tp200_sl40', 'name': '🚀 Moon Mission', 'label': 'TP +200% · stop −40%', 'window': '24h', 'dial': 'degen', 'rounds': 69}, {'id': 'safe_6h', 'label': 'safe', 'window': '6h'}]
    got = rn.tag_versions(cards, {'tp200_sl40': 3}, {'tp200_sl40': 'stage'})
    assert got[0]['vName'] == '🚀 Moon Mission v.03' and got[0]['listed'] == 'stage' and 'TP +200%' in got[0]['combo']
    assert got[1]['version'] == 1 and got[1]['listed'] is None


def test_battles_may_field_losing_scenarios_but_best_cards_never_do():
    scen = [{'id': 'a', 'label': 'A', 'window': '24h', 'tp': 100, 'sl': 40, 'rounds': 9, 'avgPct': -3}]
    picks = [{'pairAddress': 'P1', 'symbol': 'X'}]
    assert rn.scenario_cards(scen, picks) == [] and len(rn.scenario_cards(scen, picks, losers_ok=True)) == 1


def test_bracket_unique_cards_winners_losers_and_champion():
    c = lambda k, sc, legs=('P1',), tp=100: {'kind': 'mega', 'id': k, 'activity': {'score': sc}, 'legs': [{'pairAddress': p} for p in legs], 'cfg': {'tp': tp, 'sl': 20}}
    dup = c('d', 99, legs=('P9',)); dup2 = c('e', 10, legs=('P9',))
    assert [x['id'] for x in rn.unique_cards([dup, dup2])] == ['d']                         # same config fights once
    cards = [c('a', 90, ('A',)), c('b', 80, ('B',)), c('x', 70, ('X',)), c('y', 60, ('Y',))]
    pairs = rn.bracket_pairs(cards, {}, battles=3)
    assert [(p[0]['id'], p[1]['id']) for p in pairs] == [('a', 'b'), ('x', 'y')]
    br = rn.bracket_update({}, [{'aKey': 'mega:a', 'bKey': 'mega:b', 'winnerKey': 'mega:a'}, {'aKey': 'mega:x', 'bKey': 'mega:y', 'winnerKey': 'mega:x'}])
    pairs = rn.bracket_pairs(cards, br, battles=3)
    assert [(p[0]['id'], p[1]['id']) for p in pairs] == [('a', 'x'), ('b', 'y')]            # winners vs winners, losers vs losers
    br = rn.bracket_update(br, [{'aKey': 'mega:a', 'bKey': 'mega:x', 'winnerKey': 'mega:a'}, {'aKey': 'mega:b', 'bKey': 'mega:y', 'winnerKey': 'mega:b'}])
    assert rn.bracket_done(cards, br) is None                                               # a 2-0, x 1-1, b 1-1 still standing
    br = rn.bracket_update(br, [{'aKey': 'mega:x', 'bKey': 'mega:b', 'winnerKey': 'mega:x'}, {'aKey': 'mega:a', 'bKey': 'mega:x', 'winnerKey': 'mega:a'}])
    assert rn.bracket_done(cards, br) == 'mega:a'                                           # last one standing = champion


def test_pick_filters_and_the_doctor():
    now = 10_000
    rounds = [{'at': 1000 + i, 'picks': [{'mint': f'w{i}', 'entry': 1.0, 'lane': 'runner', 'score': 80, 'chg5m': 3},
                                         {'mint': f'l{i}', 'entry': 1.0, 'lane': 'runner', 'score': 40, 'chg5m': -2}]} for i in range(8)]
    paths = {**{f'w{i}': [(2000, 1.6), (2100, 2.1)] for i in range(8)}, **{f'l{i}': [(2000, 0.6)] for i in range(8)}}
    f = rn.filter_proof(rounds, paths, now)
    assert f['score70']['avgPct'] > 0 and f['green5m']['picks'] == 8 and f['_all']['picks'] == 16
    d = rn.doctor(f, f)
    assert d['filter'] in ('score70', 'green5m') and not d['sitOut']
    losing = {k: {**v, 'avgPct': -5, 'ready': True} for k, v in f.items()}
    assert rn.doctor(losing, losing)['sitOut'] is True
    rows = [{'mint': 'a', 'score': 90}, {'mint': 'b', 'score': 50}, {'mint': 'c', 'score': 75}]
    assert [r['mint'] for r in rn.apply_filter(rows, 'score70', 2)] == ['a', 'c', 'b'] and rn.apply_filter(rows, 'score70', 3) == rows


def test_reputation_is_strong_but_a_suspect_creator_s_banger_can_still_prove_itself():
    import runners as rn
    gate = dict((k, f) for k, _, f in rn.gates())['rep']
    banger = {'creatorRep': 'suspect', 'top10': 14.0, 'insiders': 2.0, 'bundled': 0, 'buyShare': 62.0, 'vol1h': 45_000.0, 'devSold': False}
    assert gate(banger) and rn.banger_proof(banger)[0]                                         # clean numbers → in (scores −12)
    assert not gate({**banger, 'top10': 34.0}) and 'top-10' in rn.banger_proof({**banger, 'top10': 34.0})[1]
    assert not gate({**banger, 'vol1h': 8_000.0})                                              # thin flow: no proof
    assert not gate({**banger, 'creatorRep': 'high'})                                          # a proven rugger never gets in
    assert gate({**banger, 'creatorRep': None, 'top10': 34.0})                                 # unknown creator: the other gates decide


def test_smart_gates_open_for_clean_coins_and_time_proven_coins_only():
    import runners as rn
    g = rn.clean_cfg({'minBuyShare': 52, 'maxBuyShare': 80, 'minTrades1h': 80})
    assert g['smartBuyShare'] == 92 and g['agedProofH'] == 12
    clean = {'buyShare': 88, 'txns1h': 200, 'scanned': True, 'top10': 14, 'insiders': 2, 'bundled': 0, 'devSold': False}
    assert rn.flow_ok({**clean, 'buyShare': 70}, g)                                      # inside the band: as before
    assert rn.flow_ok(clean, g)                                                          # 88% buys + clean holders → in (it was out at 80)
    assert not rn.flow_ok({**clean, 'top10': 28}, g) and not rn.flow_ok({**clean, 'bundled': 1}, g) and not rn.flow_ok({**clean, 'scanned': False}, g)
    assert not rn.flow_ok({**clean, 'devSold': True}, g) and not rn.flow_ok({**clean, 'buyShare': 95}, g)   # past the smart cap: still a pushed pump
    assert not rn.flow_ok({**clean, 'buyShare': 48}, g) and not rn.flow_ok({**clean, 'txns1h': 30}, g)      # sellers lead / no crowd: never
    assert not rn.flow_ok(clean, {**g, 'smartBuyShare': 80})                             # HQ can switch the smart band off
    old = {'creatorRep': 'suspect', 'ageH': 14, 'liq': 80_000, 'scanned': True, 'top10': 18, 'flaggedFunders': 0, 'devSold': False, 'buyShare': 50, 'vol1h': 3000}
    assert not rn.banger_proof(old)[0] and rn.aged_proof(old, g)[0] and rn.rep_ok(old, g)                   # lasted 14h with a real pool → passes
    assert not rn.rep_ok({**old, 'ageH': 3}, g) and not rn.rep_ok({**old, 'liq': 20_000}, g) and not rn.rep_ok({**old, 'devSold': True}, g)
    assert not rn.rep_ok({**old, 'flaggedFunders': 2}, g) and not rn.rep_ok({**old, 'scanned': False}, g)
    assert not rn.rep_ok({**old, 'creatorRep': 'high'}, g)                               # a HIGH-risk creator is never let in, however old the coin
    assert rn.rep_ok({'creatorRep': 'clean'}, g) and not rn.rep_ok(old, {**g, 'agedProofH': 48})


def test_volume_list_takes_safe_coins_even_when_a_soft_gate_keeps_them_out_of_the_round():
    import runners as rn
    g = rn.clean_cfg({'minBuyShare': 52, 'maxBuyShare': 80, 'minTrades1h': 80, 'minMcap': 20000})
    coin = {'stage': 'graduated', 'ageH': 60, 'mcap': 9000, 'vol1h': 400000, 'buyShare': 45, 'txns1h': 30, 'scanned': True, 'top10': 14, 'insiders': 2, 'bundled': 0,
            'top10Jump': 0, 'devSold': False, 'dev': 1, 'creatorFlagged': False, 'creatorRep': 'clean', 'mayhem': False, 'liq': 90000}
    assert rn.failed_gates(coin, g) and rn.safe_only(coin, g)                            # too old / small / one-sided for the round — but SAFE
    for bad in ({'scanned': False}, {'top10': 45}, {'bundled': 9}, {'devSold': True}, {'creatorFlagged': True}, {'creatorRep': 'high'}, {'mayhem': True}, {'top10Jump': 30}):
        assert not rn.safe_only({**coin, **bad}, g), bad                                 # any safety fail keeps it out of Volume too
    assert not rn.safe_only({}, g)                                                       # unknown = out


def test_top10_above_the_limit_passes_only_while_big_holders_are_holding():
    g = rn.clean_cfg({})
    assert g['smartTop10'] == 40
    c = {'scanned': True, 'top10': 34.0, 'top10Jump': 0.2, 'insiders': 1.0, 'flaggedFunders': 0, 'devSold': False, 'buyShare': 58.0, 'ageH': 3.0,
         'site': False, 'x': True, 'creatorFlagged': False, 'creatorRep': 'clean'}
    assert rn.holding(c)[0] and rn.top10_ok(c, g)                                      # 34% but holding, an X account, 3h old
    assert rn.top10_ok({**c, 'top10': 22.0, 'x': False}, g)                            # under the limit needs no proof
    for bad in ({'top10': 41.0}, {'top10Jump': 3.0}, {'devSold': True}, {'x': False}, {'ageH': 0.5}, {'buyShare': 44.0}, {'insiders': 7.0},
                {'flaggedFunders': 1}, {'creatorRep': 'suspect'}, {'creatorRep': 'high'}, {'creatorFlagged': True}, {'scanned': False}, {'top10': None}):
        assert not rn.top10_ok({**c, **bad}, g), bad
    assert not rn.top10_ok(c, {**g, 'smartTop10': 30})                                 # HQ can switch the smart band off
    assert not rn.rep_ok({'creatorRep': 'high'}, g)                                    # a reported rugger never passes, whatever the coin does


def test_older_runner_stays_on_the_board_only_while_it_trades_hard_in_a_real_pool():
    import runners as rn
    ok = {'ageH': 90, 'stage': 'graduated', 'vol1h': 80000, 'liq': 40000}
    assert rn.older_runner(ok)
    assert not rn.older_runner({**ok, 'vol1h': 20000}) and not rn.older_runner({**ok, 'liq': 9000})
    assert not rn.older_runner({**ok, 'ageH': 200}) and not rn.older_runner({**ok, 'ageH': 30}) and not rn.older_runner({**ok, 'stage': 'curve'})
    gates = {g[0]: g[2] for g in rn.GATES} if isinstance(rn.GATES[0], tuple) else None
    if gates:
        assert gates['age'](ok) and gates['prebond'](ok) and not gates['age']({**ok, 'vol1h': 1000})


def test_verified_pick_needs_every_safety_gate_but_never_a_soft_one():
    import runners as rn
    young = rn.candidate(pair('y', age_h=0.2), CLEAN, now_ms=NOW)
    ok, miss = rn.pick_check({**young, 'mcap': 1, 'vol1h': 0, 'buyShare': 99, 'txns1h': 0})     # soft gates (size, volume, flow) never block a pick
    assert ok and miss == []
    ok, miss = rn.pick_check(rn.candidate(pair('u', age_h=0.2), None, now_ms=NOW))               # no holder scan = not verified
    assert not ok and 'Holder scan done' in miss
    ok, miss = rn.pick_check({**young, 'devSold': True})
    assert not ok and any('Dev' in m for m in miss)
    ok, miss = rn.pick_check({**young, 'creatorFlagged': True})
    assert not ok
    assert rn.pick_check({'ageH': 400, 'liq': 250000})[0]                                         # an established coin needs no launch checks
    assert not rn.pick_check({'ageH': 400, 'liq': 20000})[0] and not rn.pick_check({})[0]         # old but thin / nothing known = fail closed
