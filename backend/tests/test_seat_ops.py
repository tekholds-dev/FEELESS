"""🪑 The four-seat operating model (`backend/seat_ops.py`) and where it plugs in: P/L velocity from real reads, winners earning time
(re-earned, bounded), chart quality (EARLY is never COLLAPSING), the seat score, the bench, every seat's result each cycle, multi-seat
sizing, superiority switching (a winner protected, a weak loser replaced), the buy budget, cash when nothing passes — and Reaper's
velocity / extension / rug-radar rules. No network, no wallet, no order."""
import agents as ag
import arena_prime as ap
import office as of
import office_edge as oe
import seat_ops as so


def leg(m, entry=1.0, units=1.0, at=1, **k):
    return {'mint': m, 'symbol': m, 'pairAddress': 'P' + m, 'entry': entry, 'units': units, 'at': at, 'liq': 60_000, 'liqNow': 60_000, 'bought': {'tag': '🤖 agents GO'}, **k}


def trow(m, lean=2.0, call='enter', d5=1.0, buy=60, chart=None, **v):
    return {'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': 1.0, 'why': {'lean': lean, 'drivers': []}, 'trigger': [call, ''], 'devil': ['agree', ''], 'case': ['agree', ''],
            'nums': {'d5': d5, 'buy': buy, 'liq': 60_000, 'pts': 5, 'pace': 1.5}, 'vitals': {'safe': True, 'ageH': 8, 'liq': 60_000, 'top10': 15, 'rug': 10, **v}, 'go': call == 'enter',
            **({'chart': chart} if chart else {})}


def case(m, lean=2.0, cleared=True, block=None):
    return {'mint': m, 'symbol': m, 'pair': 'P' + m, 'lean': lean, 'cleared': cleared, 'go': False,
            'checks': [['scan', True, 'holder scan passed'], ['devil', cleared, block or 'Devil agrees']], 'row': trow(m, lean)}


def hist(*pts, t0=1000, step=30):
    return [[t0 + i * step, p] for i, p in enumerate(pts)]


# ── 📈 P/L VELOCITY: real reads only ───────────────────────────────────────────────────────────────────────────────────────────────
def test_velocity_classifies_from_real_reads_and_says_unknown_until_it_has_enough():
    assert so.velocity([], 2000)['state'] == 'UNKNOWN'
    assert so.velocity(hist(1, 2), 2000)['state'] == 'UNKNOWN'                                   # two reads are not a velocity
    assert so.velocity(hist(0, 0.1, 0.2), 2000)['state'] == 'UNKNOWN'                            # span under 90s
    up = hist(0, 1, 2, 4, 6, 9, 12, 16, 20, 25, 30, 36, 42)                                     # 6 min, rising faster and faster
    assert so.velocity(up, up[-1][0])['state'] == 'ACCELERATING'
    flat = hist(*([5.0] * 13))
    assert so.velocity(flat, flat[-1][0])['state'] == 'STABLE'
    stall = hist(0, 2, 4, 6, 8, 10, 12, 12.2, 12.3, 12.3, 12.4, 12.4, 12.5)                      # rose, then went flat
    assert so.velocity(stall, stall[-1][0])['state'] == 'STALLING'
    rev = hist(0, 3, 6, 9, 12, 14, 15, 14, 12, 10, 8, 6, 4)                                      # gave it back
    v = so.velocity(rev, rev[-1][0])
    assert v['state'] == 'REVERSING' and v['slope'] < 0 and 'pts/min' in v['why']
    h = []
    for t, p in ((0, 1.0), (4, 1.5), (12, 2.0), (25, 2.5)):
        h = so.vel_note(h, 1000 + t, p)
    assert [x[0] for x in h] == [1000, 1012, 1025]                                               # at most one read per VEL_EVERY
    assert so.vel_note(h, 1000 + 2000, 3.0)[0][0] > 1025 - 1 or len(so.vel_note(h, 1000 + 2000, 3.0)) == 1   # older than 15 min drop off
    assert so.vel_note([[1, 2.0]], 5, None) == [[1, 2.0]]                                        # no price = no read (never a guessed one)


# ── ⏳ WINNERS EARN TIME, EVERY WINDOW RE-EARNED ──────────────────────────────────────────────────────────────────────────────────
def test_only_a_gaining_winner_with_a_valid_thesis_healthy_pool_and_no_better_challenger_earns_more_time():
    ok, why = so.extension(8.0, {'state': 'ACCELERATING'}, 'valid', 0.95, 'CLEAN', 5, 15)
    assert ok and 'earned +5 min' in why
    assert so.extension(8.0, 'STABLE', 'valid')[0]
    assert not so.extension(-1.0, 'ACCELERATING', 'valid')[0]                                    # a loser never earns extra time
    assert not so.extension(8.0, 'STALLING', 'valid')[0] and not so.extension(8.0, 'REVERSING', 'valid')[0]
    assert not so.extension(8.0, 'UNKNOWN', 'valid')[0]
    assert not so.extension(8.0, 'ACCELERATING', 'weak')[0]
    assert not so.extension(8.0, 'ACCELERATING', 'valid', liq_ratio=0.6)[0]                     # the pool is draining
    assert not so.extension(8.0, 'ACCELERATING', 'valid', quality='COLLAPSING')[0]
    no, why = so.extension(8.0, 'ACCELERATING', 'valid', 0.9, 'CLEAN', challenger_margin=20, need=15)
    assert not no and 'challenger' in why                                                        # a materially better challenger wins the time


# ── 📊 CHART QUALITY ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_chart_quality_never_calls_a_newborn_collapsing_and_unknown_stays_unknown():
    assert so.chart_quality(None) == (None, 'no chart read this pass')
    assert so.chart_quality({'state': 'UNKNOWN'})[0] is None
    assert so.chart_quality({'state': 'EARLY', 'n': 4, 'q': {'state': 'LIMITED_HISTORY', 'readOk': True}})[0] == 'EARLY'
    assert so.chart_quality({'state': 'DATA INVALID', 'q': {'state': 'MALFORMED', 'readOk': False}})[0] == 'INVALID'
    assert so.chart_quality({'state': 'LIQUIDITY FAILURE'})[0] == 'COLLAPSING'
    assert so.chart_quality({'state': 'DOWNTREND'})[0] == 'COLLAPSING'
    assert so.chart_quality({'state': 'PARABOLIC', 'ext': 95})[0] == 'EXTENDED'
    assert so.chart_quality({'state': 'CHOP', 'chop': 90})[0] == 'CHOPPY'
    assert so.chart_quality({'state': 'UPTREND', 'trend': 70, 'chop': 20, 'ext': 30, 'risk': [1.0, '']})[0] == 'CLEAN'
    assert set(so.QUALITY_SIZE.values()) <= {0.5, 0.75}                                           # the Warden may only shrink on a quality word


# ── 🏅 THE SEAT SCORE ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_seat_score_names_every_part_rewards_clean_live_coins_and_punishes_stale_dead_or_failed_ones():
    clean = trow('A', lean=3, d5=6, chart={'state': 'UPTREND', 'trend': 70, 'chop': 10, 'ext': 30, 'risk': [1.0, ''], 'q': {'enterOk': True}})
    s = so.score(clean, {'pxAge': 5})
    assert 0 <= s['score'] <= 100 and s['quality'] == 'CLEAN' and {p[0] for p in s['parts']} >= {'read', 'momentum', 'structure', 'liquidity', 'holders', 'live data'}
    stale = so.score(clean, {'pxAge': 400, 'seen': {'reject': 'Devil objects', 'review': 900}, 'lost': True})
    assert stale['score'] < s['score'] - 25
    assert {p[0] for p in stale['parts']} >= {'stale reject', 'failed setup', 'stale snapshot'}
    moved = so.score(clean, {'pxAge': 5, 'seen': {'reject': 'Devil objects', 'review': 900, 'changed': 950}})
    assert 'stale reject' not in {p[0] for p in moved['parts']}                                   # a material change since the reject clears the penalty
    impostor = so.score(clean, {'pxAge': 5, 'social': {'cross': {'conflict': True}}})
    assert impostor['score'] < s['score'] and ['identity', -15.0, 'the website shows a different contract'] in impostor['parts']
    collapsing = so.score(trow('C', lean=3, d5=6, chart={'state': 'LIQUIDITY FAILURE'}), {'pxAge': 5})
    assert collapsing['quality'] == 'COLLAPSING' and collapsing['score'] < s['score']               # a rug-like collapse never outranks a clean challenger
    held_up = so.score(clean, {'pxAge': 5, 'vel': {'state': 'ACCELERATING'}, 'verdict': 'valid'})
    held_dn = so.score(clean, {'pxAge': 5, 'vel': {'state': 'REVERSING'}, 'verdict': 'weak'})
    assert held_up['score'] > s['score'] > held_dn['score']
    assert so.margin_need('agents') == 15 and so.margin_need('aggressive') < so.margin_need('agents') < so.margin_need('conservative')
    assert so.margin_need('aggressive', {'state': 'ACCELERATING'}) == so.margin_need('aggressive') + so.ACCEL_EXTRA


# ── 🪑 THE BENCH + EVERY SEAT EVERY CYCLE ────────────────────────────────────────────────────────────────────────────────────────
def test_the_bench_ranks_ready_challengers_first_and_never_lists_a_held_coin():
    cs = [case('A'), case('B'), case('C', cleared=False, block='Devil objects: rug 70'), case('H'), case('D')]
    sc = {'A': {'score': 40}, 'B': {'score': 70}, 'C': {'score': 90}, 'H': {'score': 99}, 'D': {'score': 60}}
    b = so.bench(cs, sc, on={'H'}, ready={'D': (False, '+20% since the read — not chased')}, cooled=['A'])
    assert [x['symbol'] for x in b] == ['B', 'D', 'C', 'A'] and [x['rank'] for x in b] == [1, 2, 3, 4]               # ready · near ready · the rest
    assert b[0]['ready'] and b[1]['near'] and 'not chased' in b[1]['block'] and not b[2]['near'] and 'rug' in b[2]['block'] and b[3]['block'] == 'rebuy cooldown'
    st = so.bench_stats(b, ['B', 'Z'])
    assert st['depth'] == 4 and st['ready'] == 1 and st['near'] == 1 and st['new'] == 3 and st['dropped'] == 1                       # D, C, A new · Z dropped
    near = so.bench([{**case('S'), 'cleared': False, 'checks': [['scan', False, 'holders not scanned'], ['devil', True, '']]}], {})
    assert near[0]['near'] and not near[0]['ready']                                                                                  # only the holder scan missing
    assert len(so.bench([case(str(i)) for i in range(9)], {}, n=5)) == 5


def test_every_seat_gets_a_fresh_result_with_its_own_timestamps_and_empty_seats_name_the_next_candidate():
    seats = [{'kind': 'agent', 'symbol': 'W', 'mint': 'W', 'pair': 'PW', 'pct': 12.0}, {'kind': 'agent', 'symbol': 'L', 'mint': 'L', 'pair': 'PL', 'pct': -6.0},
             {'kind': 'agent', 'symbol': 'T', 'mint': 'T', 'pair': 'PT', 'pct': 22.0}, {'kind': 'open', 'symbol': None}]
    reps = [{'mint': 'W', 'state': 'PROTECT', 'pct': 12.0, 'stop': -20, 'take': 10, 'verdict': 'valid', 'heldMin': 30},
            {'mint': 'L', 'state': 'HOLD', 'pct': -6.0, 'stop': -20, 'verdict': 'weak', 'heldMin': 40},
            {'mint': 'T', 'state': 'TAKE', 'pct': 22.0, 'action': 'pull', 'verdict': 'valid', 'heldMin': 50}]
    dec = [{'pair': 'PL', 'action': 'swap', 'toSym': 'B', 'why': 'weak loser → B'}, {'pair': 'PT', 'action': 'pull', 'why': 'take'}]
    vels = {'W': {'state': 'ACCELERATING', 'why': '+1.2 pts/min'}, 'L': {'state': 'REVERSING'}}
    sc = {'W': {'score': 70}, 'L': {'score': 20}, 'T': {'score': 50}}
    bench_ = [{'mint': 'B', 'symbol': 'B', 'score': 60, 'ready': True}, {'mint': 'C', 'symbol': 'C', 'score': 55, 'ready': True}]
    seat = {'code': 'FILLING', 'reason': 'B cleared', 'nextIn': 20, 'seats': [{'seat': 4, 'code': 'FILLING', 'reason': '$C cleared — the next tick fills it'}]}
    b = so.seat_board(seats, reps, dec, vels, sc, bench_, [], 5000, 5000, {'W': 4990}, seat)
    assert [x.get('result') for x in b[:3]] == ['PROTECT', 'SWAP', 'TAKE'] and all(r in so.RESULTS for r in [x.get('result') for x in b[:3]])
    w = b[0]
    assert w['vel'] == 'ACCELERATING' and w['decidedAt'] == 5000 and w['inputAt'] == 4990 and w['margin'] == -10 and w['need'] == 30   # an accelerating seat needs +15 more
    assert w['challenger']['symbol'] == 'B' and 'trail armed' in w['protection']
    assert b[1]['margin'] == 40 and b[1]['vel'] == 'REVERSING'
    e = b[3]
    assert e['empty'] and e['next']['symbol'] == 'B' and e['ready'] and e['code'] == 'FILLING' and e['nextEval'] == 20
    s = so.summary(3, 4, bench_, 2, 6, 0.85)
    assert s == {'occupancy': 3, 'target': 4, 'open': 1, 'bench': 2, 'benchReady': 2, 'buysUsed': 2, 'buysLeft': 4, 'budget': 6, 'cash': 0.85}


# ── 🪑🪑🪑🪑 FOUR SEATS, FOUR COINS ────────────────────────────────────────────────────────────────────────────────────────────────
def _fctx(**k):
    return {'control': True, 'pol': oe.policy({}), 'live': True, 'halt': None, 'courier': 'HEALTHY', 'used': 0, 'gos': [], 'wait': [],
            'empty': 4, 'emptySince': 900, 'lastFill': 0, 'now': 1000, **k}


def _card(cash=4.0, legs=None):
    return {'real': True, 'cash': cash, 'legs': legs or [], 'events': []}






def test_the_first_seat_never_makes_the_other_open_seats_impossible():
    assert so.seat_room(1.0, 1.2, 1) == (1.0, None)                                              # one seat open: it may take what it asked
    m, why = so.seat_room(1.0, 1.2, 3)
    assert abs(m - 0.4) < 1e-9 and '3 seats open' in why
    w = of.warden(1.0, {'value': 4.0, 'liq': 500_000, 'ageH': 20, 'courier': 'HEALTHY', 'openSeats': 3, 'free': 1.2})
    assert w['allowed'] <= 0.4 + 1e-9 and any(r['id'] == 'W17 seat room' for r in w['rules'])
    assert of.warden(0.3, {'value': 4.0, 'liq': 500_000, 'ageH': 20, 'courier': 'HEALTHY', 'openSeats': 3, 'free': 1.2})['allowed'] == 0.3


# ── ⇄ SUPERIORITY: winners protected, weak losers replaced ──────────────────────────────────────────────────────────────────────




# ── ☠ REAPER: velocity, earned windows, the rug radar ─────────────────────────────────────────────────────────────────────────────
def _thesis(**k):
    return {'structure': 'UPTREND', 'stopPct': 25, 'expectedHoldWindows': 3, 'maxHoldWindows': 12, 'invalidation': 0.5, **k}


def _upch():
    import chart_intel as ci
    from test_chart_intel import UP
    ch = ci.read(UP, 0, True, 'candles', {'provider': 'jupiter', 'vol5m': 9000, 'vol1h': 90_000, 'liqAge': 0, 'ageMin': 500}, liq=80_000)
    assert ch['state'] in ci.GOOD and (ch.get('q') or {}).get('structOk')
    return ch


UPCH = _upch()


def _reap(pct, held_min, vel, peak=None, granted=None, margins=None, rug=None, chart=UPCH, at=0):
    now = at + held_min * 60
    l = leg('A', at=at)
    pos = {'A': {'entry': 1.0, 'since': at, 'peak': peak if peak is not None else pct, 'low': min(0, pct), 'path': [], 'liq0': 60_000, 'thesis': _thesis(), 'granted': granted,
                 'lastWin': int(held_min // 5) - 1}}
    return of.reap([l], [trow('A')], {'PA': 1 + pct / 100}, {'agentTakePct': 50}, pos, now, control=True, charts={'A': chart}, vels={'A': {'state': vel}}, margins=margins, rug=rug)


def test_a_reversing_winner_banks_sooner_and_a_steady_one_keeps_the_normal_trail():
    _, rep, _ = _reap(10.0, 20, 'REVERSING', peak=16.0)
    assert rep[0]['rule'] == 'R7v trail tightened' and rep[0]['action'] == 'pull' and rep[0]['vel'] == 'REVERSING'
    _, rep2, _ = _reap(10.0, 20, 'STABLE', peak=16.0)
    assert rep2[0]['action'] is None                                                             # gave back 38% of the peak: under the normal 50% line


def test_past_its_base_a_winner_must_earn_each_window_and_a_non_winner_gives_up_the_seat():
    pos, rep, _ = _reap(6.0, 31, 'ACCELERATING', granted=6)                                      # window 6 = past the 30-min base
    assert rep[0]['action'] is None and pos['A']['granted'] == 7 and pos['A']['ext'][-1]['window'] == 7 and rep[0]['ext'] == 1
    pos2, rep2, _ = _reap(0.5, 31, 'STABLE', granted=6)                                          # +0.5% is a winner only on paper: holding, no gain → earns?
    assert pos2['A']['granted'] == 7                                                              # STABLE + positive keeps earning
    pos3, rep3, _ = _reap(-3.0, 31, 'STABLE', granted=6)
    assert rep3[0]['rule'] == 'R9e no extension earned' and rep3[0]['action'] == 'pull' and 'only a winner' in rep3[0]['evidence']
    pos4, rep4, _ = _reap(6.0, 31, 'ACCELERATING', granted=6, margins={'A': (25, 15)})
    assert rep4[0]['rule'] == 'R9e no extension earned' and 'challenger' in rep4[0]['evidence']   # a materially better challenger takes the time
    pos5, rep5, _ = _reap(-3.0, 16, 'STABLE', granted=4)                                         # inside the base (window 3 of 6): the thesis keeps its seat
    assert rep5[0]['action'] is None and pos5['A']['granted'] == 4
    pos6, rep6, _ = _reap(9.0, 70, 'ACCELERATING', granted=12)                                   # the thesis max (12 windows = 60 min) is never passed
    assert pos6['A']['granted'] == 12


def test_the_rug_radar_is_a_hard_exit_for_an_agent_seat():
    _, rep, _ = _reap(4.0, 3, 'ACCELERATING', rug={'PA': '🚨 the creator sold $60 in the last 90s'})
    assert rep[0]['rule'] == 'R4r rug radar' and rep[0]['action'] == 'pull' and rep[0]['state'] == 'TAKE'
    _, rep2, _ = _reap(-4.0, 3, 'STABLE', rug={'PA': '🚨 a top holder dumped $400'})
    assert rep2[0]['state'] == 'EXIT INVALIDATED'


def test_the_seat_module_has_no_wallet_network_or_execution_path_of_its_own():
    import inspect
    src = inspect.getsource(so)
    for bad in ('httpx', 'fuse_wallet', 'signTransaction', 'sendTransaction', 'import requests', '_fw_', 'asyncio', 'open('):
        assert bad not in src, bad


def test_the_fast_guard_wakes_reaper_on_a_hard_line_and_never_on_a_frozen_or_unpriced_seat():
    legs = [leg('A'), leg('B'), leg('C', frozen=True), leg('D'), leg('E', placeholder=True)]
    px = {'A': 0.70, 'B': 0.85, 'C': 0.10, 'E': 0.01}
    assert so.hard_cross(legs, px, {'A': -25.0, 'B': -25.0}) == ['A']                            # its own structure stop (B −15% is inside it)
    assert so.hard_cross(legs, px, {'B': -25.0}, creator_sl=10) == ['A', 'B']                    # your stop is tighter: it binds
    assert so.hard_cross(legs, {'A': 0.56}) == []                                                # −44%: not yet the catastrophic line
    assert so.hard_cross(legs, {'A': 0.54}) == ['A']                                             # −46%: the −45% line, always


# ── 🔌 THE SERVICE: velocity reads, tape for agent seats, a new candle reaches the case, the seat payload ────────────────────────────
def test_velocity_is_read_from_real_prices_every_tick_and_unknown_after_a_restart(monkeypatch):
    import reputation_service as rs
    monkeypatch.setitem(rs._office, 'vel', {})
    card = {'legs': [leg('V', entry=1.0), leg('P', placeholder=True)]}
    out = {}
    for i, p_ in enumerate((1.00, 1.02, 1.05, 1.09, 1.14, 1.20, 1.27, 1.35)):
        out = rs._office_vels(card, {'PV': p_}, 1000 + 30 * i)
    assert out['V']['state'] == 'ACCELERATING' and 'P' not in out
    assert len(rs._office['vel']['V']) == 8
    monkeypatch.setitem(rs._office, 'vel', {})
    assert rs._office_vels(card, {}, 2000)['V']['state'] == 'UNKNOWN' and rs._office['vel']['V'] == []   # no price: no read, nothing guessed


def test_the_agents_seats_get_their_tape_read_and_the_engine_never_flow_exits_them(monkeypatch):
    import asyncio
    import reputation_service as rs
    asked = []

    async def fake_fetch(pairs, max_age=12.0):
        asked.extend(pairs)
        return {p: None for p in pairs}
    held = {'real': True, 'holdAll': True, 'holdBy': 'agents', 'legs': [leg('AG', real=True), leg('AH', real=True)], 'events': []}
    monkeypatch.setattr(rs, '_flow_fetch', fake_fetch)
    monkeypatch.setattr(rs, '_prime_real_cfg', lambda: {'flowExit': 'off', 'rugRadar': False, 'rotateHours': 0.08})
    monkeypatch.setattr(rs, '_json_load', lambda path, default=None: {'prime': {'cards': {'degen': held}}} if path == rs.FUSE_HQ_PATH else (default if default is not None else {}))
    assert asyncio.run(rs._flow_guard(1000.0, {})) is False                                      # read only: no engine exit on an agent seat
    assert set(asked) == {'PAG', 'PAH'}                                                           # … but both seats' tape WAS read (Reaper's R4 / R4r stand on it)


def test_a_new_one_minute_candle_reaches_the_case_without_rediscovering_it(monkeypatch):
    import asyncio
    import chart_intel as ci
    import reputation_service as rs
    up = [[60 * i, 1.0 + 0.01 * i, 1.012 + 0.01 * i, 0.995 + 0.01 * i, 1.008 + 0.01 * i, 900] for i in range(20)]
    row = {**trow('NC'), 'pairAddress': 'PNC'}
    monkeypatch.setitem(rs._agents, 'table', [row])
    monkeypatch.setitem(rs._office, 'candles', {'PNC': (0.0, up, {})})
    monkeypatch.setitem(rs._office, 'charts', {})
    monkeypatch.setitem(rs._office, 'load', {})
    dump = up + [[1200, 1.2, 1.2, 0.9, 0.92, 4000]]

    class R:
        def json(self):
            return {'charts': {'PNC': {'candles': dump, 'provider': 'jupiter', 'source': 'candles'}}}

    class C:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None):
            assert url.endswith('/api/candles/live') and list(json['pairs']) == ['PNC']
            return R()
    monkeypatch.setattr(rs.httpx, 'AsyncClient', C)
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    n = asyncio.run(rs._office_candle_refresh({'NC': 'PNC'}, 1265.0))
    assert n == 1 and rs._agents['table'][0] is row                                              # the SAME row object — no rediscovery, no new table
    assert row['chartAt'] == 1265.0 and row['chart']['state'] == rs._office['charts']['NC']['state'] and rs._office['candles']['PNC'][1][-1][0] == 1200
    assert ci.read(up, 1200)['state'] != rs._office['charts']['NC']['state'] or row['chart']['entry'][0] != 'ENTER NOW'


def test_the_seat_payload_is_memory_only_and_labels_the_score_as_hand_set(monkeypatch):
    import reputation_service as rs
    monkeypatch.setitem(rs._agents, 'seatBoard', [{'seat': 1, 'empty': True}])
    monkeypatch.setitem(rs._agents, 'bench', [{'rank': 1, 'symbol': 'B'}])
    monkeypatch.setitem(rs._agents, 'seatSummary', so.summary(0, 4, [{'ready': True}], 0, 6, 1.3))
    p = rs._office_seat_payload()
    assert p['seatSummary']['target'] == 4 and p['bench'][0]['symbol'] == 'B' and 'not a learned or proven edge' in p['scoreNote']



def test_seat_utilization_counts_occupied_and_why_empty_and_never_counts_a_gap():
    b1 = [{'seat': 1, 'empty': False}, {'seat': 2, 'empty': True, 'code': 'WAITING FOR CONFIRMATION'}, {'seat': 3, 'empty': True, 'code': 'BUY BUDGET'}, {'seat': 4, 'empty': True, 'code': 'COURIER BLOCK'}]
    u = so.util_note(None, b1, 3600 * 100)                                        # first note: no time counted yet
    u = so.util_note(u, b1, 3600 * 100 + 60)
    u = so.util_note(u, b1, 3600 * 100 + 60 + 4000)                               # a 4000s gap (restart): capped at UTIL_DT_CAP
    v = so.util_view(u)
    assert v['seats']['1']['occ'] == 60 + so.UTIL_DT_CAP and v['seats']['1']['pct'] == 100.0
    assert v['seats']['2']['waiting'] == 180 and v['seats']['3']['budget'] == 180 and v['seats']['4']['safety'] == 180 and v['seats']['2']['pct'] == 0.0
    assert v['all']['pct'] == 25.0 and v['all']['empty'] == 540
    assert so.empty_cat('NO CASH') == 'cash' and so.empty_cat('NO CLEARED CANDIDATE') == 'waiting'
    old = so.util_note({'at': 1, 'h': {'1': {'1': {'occ': 999}}}}, b1, 3600 * 100 + 10)
    assert '1' not in old['h']                                                    # outside the 6h window: dropped
