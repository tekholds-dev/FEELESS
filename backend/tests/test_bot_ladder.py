"""🤖 BOT LADDER + 🧭 phase hunt + 🪑 the 30-second seat (owner, 2026-10-11: "this is obviously a wash/rug chart … agent should be moving fast,
processing new coins mainly trench, majors once we broke even and doubled … no seat should be empty, 30 secs to choose").
Pure + source checks — no network, no wallet, no order."""
import inspect
import math
import random

import agents as ag
import chart_intel as ci
import office_edge as oe
import seat_ops as so


def _ladder_rows(n=30, step=0.6, vol=120.0, seed=1):
    """One bot trading against a thin pool: every candle moves ~the same step, every minute trades ~the same $ (the $ROAR shape)."""
    rnd, px, rows = random.Random(seed), 0.0095, []
    for i in range(n):
        up = i % 2 == 0 or rnd.random() < 0.15
        o = px
        c = o * (1 + (step if up else -step * 0.9) / 100)
        hi, lo = max(o, c) * (1 + 0.0001), min(o, c)
        rows.append([1_000_000 + i * 60, o, hi, lo, c, vol * (0.85 + rnd.random() * 0.3)])
        px = c
    return rows


def _real_rows(n=30, seed=7):
    """A real chart: fat-tailed moves, bursts of volume."""
    rnd, px, rows = random.Random(seed), 0.01, []
    for i in range(n):
        r = rnd.gauss(0.2, 2.5) * (3 if rnd.random() < 0.1 else 1)
        o, c = px, px * (1 + r / 100)
        hi, lo = max(o, c) * (1 + abs(rnd.gauss(0, 1.2)) / 100), min(o, c) * (1 - abs(rnd.gauss(0, 1.2)) / 100)
        rows.append([1_000_000 + i * 60, o, hi, lo, c, rnd.expovariate(1 / 800) * (5 if rnd.random() < 0.1 else 1)])
        px = c
    return rows


def test_one_bot_trading_a_coin_with_itself_reads_as_a_bot_ladder():
    r = ci.read(_ladder_rows(), 1_001_800.0, ohlc=True, src='candles')
    assert r['state'] == 'BOT LADDER' and r['entry'][0] == 'SKIP' and r['risk'][0] == 0.0
    assert ('chart_bot_ladder' in [o[0] for o in r['objs']]) and ci.CHART_RULES['chart_bot_ladder'][0] is True   # a HARD objection for Devil
    assert r['f']['steps'] >= ci.LADDER_STEPS and r['f']['volCv'] <= ci.LADDER_VOL_CV
    assert 'one bot trading it with itself' in ci.ladder_words(r['f'])


def test_a_real_chart_and_a_tape_are_never_called_a_ladder():
    for seed in range(12):
        assert ci.read(_real_rows(seed=seed), 1_001_800.0, ohlc=True, src='candles')['state'] != 'BOT LADDER'
    tape = ci.read(_ladder_rows(), 1_001_800.0, ohlc=False, src='tape')   # a tape has no ranges: never judged on this
    assert tape['state'] != 'BOT LADDER'


def test_a_held_coin_that_turns_into_a_bot_ladder_is_out_and_never_a_seat():
    ch = ci.read(_ladder_rows(), 1_001_800.0, ohlc=True, src='candles')
    rv = ci.review({'structure': 'RANGE', 'invalidation': 0.001}, ch, 1.5, 12.0)
    assert rv['verdict'] == 'invalid' and 'BOT LADDER' in rv['why'][0]
    assert so.chart_quality(ci.compact(ch))[0] == 'INVALID'
    case = {'mint': 'L', 'cleared': False, 'checks': [['scan', True, ''], ['chart', False, 'SKIP']], 'row': {'mint': 'L', 'chart': ci.compact(ch)}}
    assert oe.near_ready([case], {'L': {'score': 90}}) == []                                    # never "best available" either
    assert 'BOT LADDER' in ci.BAD and 'BOT LADDER' in ci.STATES


def test_the_phase_decides_what_the_seats_hunt():
    assert so.universe({'value': 1.26, 'putIn': 29.5})[0] == 'trench'
    assert so.universe({'value': 35, 'putIn': 29.5})[0] == 'mixed'
    assert so.universe({'value': 60, 'putIn': 29.5})[0] == 'majors'
    assert so.universe({})[0] == 'mixed'
    young = {'vitals': {'ageH': 2.0, 'liq': 40_000}, 'nums': {'liq': 40_000}}
    old = {'vitals': {'ageH': 400.0, 'liq': 900_000}, 'nums': {'liq': 900_000}}
    assert so.universe_pts(young, 'trench')[0] > 0 and so.universe_pts(old, 'trench')[0] < 0
    assert so.universe_pts(old, 'majors')[0] > 0 and so.universe_pts(young, 'majors')[0] < 0
    assert so.universe_pts(young, 'mixed') is None
    a = so.score(young, {'universe': 'trench'})['score']
    b = so.score(young, {'universe': 'majors'})['score']
    assert a > b                                                                                 # a tilt on the RANK only


def test_an_empty_seat_is_decided_in_thirty_seconds_and_fills_have_their_own_guard():
    assert oe.NEAR_PATIENCE_SEC <= 30 and oe.SEAT_TARGET_AUTO <= 30
    assert ag.FILL_MOVES_HR >= 4 * ag.CONTROL_MOVES_HR // 2 and ag.CONTROL_MOVES_HR == 6     # switches keep their 6; fills get room for 4 seats
    ctx = {'control': True, 'pol': {'entry': 'auto'}, 'live': True, 'courier': 'OK', 'used': 6, 'gos': [{'mint': 'G'}], 'wait': [], 'empty': 1, 'now': 1000.0}
    assert oe.fill_plan(ctx) == [] and [r['mint'] for r in oe.fill_plan({**ctx, 'cap': ag.FILL_MOVES_HR})] == ['G']
    ev = [{'kind': 'agent', 'move': 'fill', 'mint': 'A', 'at': 990.0}, {'kind': 'agent', 'move': 'swap', 'mint': 'B', 'at': 990.0}]
    assert oe.real_buys(ev, [], 'c', 1000.0, moves=('fill',)) == 1 and oe.real_buys(ev, [], 'c', 1000.0, moves=('swap',)) == 1
    import reputation_service as rs
    tick = inspect.getsource(rs._prime_tick_inner)
    assert "moves=('swap',)" in tick and "moves=('fill',)" in tick and "'cap': _ag.FILL_MOVES_HR" in tick
    guard = inspect.getsource(rs._real_guard_loop)
    assert 'EMPTY-SEAT HEARTBEAT' in guard and rs.SEAT_HEARTBEAT_SEC <= 30


def test_recovery_sends_more_deep_reviews_to_young_coins():
    import reputation_service as rs
    src = inspect.getsource(rs._agents_tick)
    assert "_so.universe(_agents.get('money'))" in src and 'young_min_' in src
    assert math.isclose(so.YOUNG_H, 6.0)


def test_a_flat_filled_volume_figure_is_not_judged_a_bot():
    rows = [[r[0], r[1], r[2], r[3], r[4], 1000.0] for r in _ladder_rows()]   # the same $ every minute to the cent = a filled value
    assert ci.read(rows, 1_001_800.0, ohlc=True, src='candles')['state'] != 'BOT LADDER'


def test_best_available_needs_a_real_candle_read():
    row, mkt = {'px': 1.0, 'nums': {'liq': 100_000}}, {'px': 1.0, 'liq': 100_000}
    tape = {'src': 'tape', 'state': 'RANGE', 'entry': ['WAIT FOR DATA', 'x', 'tape'], 'risk': [0.5, 'x'], 'q': {'readOk': True}}
    assert oe.live_check(row, mkt, tape, 1.0, near=True)['ok'] is False
    assert oe.live_check(row, mkt, {**tape, 'src': 'candles'}, 1.0, near=True)['ok'] is True


def test_recovery_scans_young_coins_first():
    mk = lambda m, age, lean: {'mint': m, 'lean': lean, 'row': {'vitals': {'safe': None, 'ageH': age}, 'nums': {}}}
    cs = [mk('OLD', 900, 3.0), mk('YOUNG', 2.0, 0.5), mk('MID', 30, 2.0)]
    assert [c['mint'] for c in oe.scan_order(cs, 1, universe='trench')] == ['YOUNG']
    assert [c['mint'] for c in oe.scan_order(cs, 1, universe='mixed')] == ['OLD']
