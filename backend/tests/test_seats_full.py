"""🪑 KEEP SEATS FULL (owner, 2026-10-11: "finish all fixes and they must keep seats full") — without passing a hard block.
(1) where a coin was FOUND, its cap band, narrative, launchpad, chart label = context: never a learned rug sign, never Devil's veto;
(2) an empty seat with NOTHING cleared takes the best near-ready coin after NEAR_PATIENCE_SEC — only coins whose sole open checks are the
entry moment / ENTER-grade data — at half size (Warden W19). No network, no wallet, no order."""
import agents as ag
import office as of
import office_edge as oe


def _call(drivers, rug):
    return {'drivers': drivers, 'p5': -80.0 if rug else 1.0, 'p60': 2.0}


def test_where_a_coin_was_found_is_never_a_rug_sign():
    js = [_call(['src:calls', 'band:1m+', 'narr:ai', 'thin_pool'], True) for _ in range(6)]
    js += [_call(['src:calls', 'band:1m+', 'narr:ai', 'thin_pool'], False) for _ in range(2)]
    js += [_call(['buyers'], False) for _ in range(12)]
    lift = ag.rug_lift(js)
    assert lift == {'thin_pool': 6}                                                               # the same record: the real reason is a sign, the context is not
    assert ag.is_context('src:outlet') and ag.is_context('soc:narrative') and ag.is_context('fresh') and not ag.is_context('thin_pool')
    st = {'rugSigns': {'src:calls': 9, 'band:1m+': 9, 'thin_pool': 5}}
    assert ag.rug_signs(['src:calls', 'band:1m+', 'thin_pool'], st) == ['thin_pool']


def test_devil_never_vetoes_a_coin_for_its_source_band_or_narrative():
    why = {'lean': 2.0, 'drivers': [('src:outlet', 0.5, 'found on callouts'), ('band:1m+', 0.3, '$1M+ cap band'), ('narr:ai', 0.4, 'ai narrative')]}
    learned = {'rugSigns': {'src:outlet': 40, 'band:1m+': 40, 'narr:ai': 40}}
    args = ag.devil_args('enter', {}, why, {'safe': True, 'mint': 'M'}, learned)
    assert not [a for a in args if a[0] == 'rug_signs']
    why2 = {'lean': 2.0, 'drivers': [('thin_pool', 0.5, 'thin pool'), ('dev_sold', 0.3, 'dev sold')]}
    args2 = ag.devil_args('enter', {}, why2, {'safe': True, 'mint': 'M'}, {'rugSigns': {'thin_pool': 4, 'dev_sold': 4}})
    assert [a for a in args2 if a[0] == 'rug_signs']                                              # real learned signs still veto


def _case(mint, checks, chart=None, cleared=False):
    return {'mint': mint, 'symbol': mint, 'cleared': cleared, 'checks': checks,
            'row': {'mint': mint, 'symbol': mint, 'pair': 'P' + mint, 'px': 1.0, 'chart': chart if chart is not None else {'state': 'BASE BUILDING', 'risk': [0.8, 'ok'], 'q': {'readOk': True}}}}


OK = lambda k: [k, True, k]
NO = lambda k: [k, False, f'{k} not yet']
SAFE = [OK('scan'), OK('age'), OK('pool'), OK('burn'), OK('devil')]


def test_near_ready_takes_only_coins_whose_only_open_checks_are_the_entry_moment():
    cases = [_case('CHART', SAFE + [NO('chart'), OK('data')]),
             _case('DATA', SAFE + [OK('chart'), NO('data')]),
             _case('SCAN', [NO('scan')] + SAFE[1:] + [NO('chart')]),
             _case('DEVIL', SAFE[:4] + [NO('devil'), NO('chart')]),
             _case('POOL', SAFE[:2] + [NO('pool')] + SAFE[3:] + [NO('chart')]),
             _case('INVALID', SAFE + [NO('chart')], chart={'state': 'DATA INVALID', 'risk': [0.0, 'x'], 'q': {'readOk': False}}),
             _case('HARDOBJ', SAFE + [NO('chart')], chart={'state': 'PARABOLIC', 'risk': [0.0, 'hard'], 'q': {'readOk': True}}),
             _case('CLEAR', SAFE, cleared=True),
             _case('LOW', SAFE + [NO('chart')])]
    scores = {c['mint']: {'score': 70} for c in cases}
    scores['DATA'] = {'score': 90}
    scores['LOW'] = {'score': 10}
    out = oe.near_ready(cases, scores, min_entry=0)
    assert [r['mint'] for r in out] == ['DATA', 'CHART']                                          # best score first; every hard block stays out
    assert 'every safety check passed' in out[0]['nearReady'] and out[0]['pair'] == 'PDATA'
    assert [r['mint'] for r in oe.near_ready(cases, scores, min_entry=0, live={'DATA': (False, 'price ran')})] == ['CHART']   # the newest live check wins


def _ctx(**kw):
    c = {'control': True, 'pol': {'entry': 'auto'}, 'live': True, 'halt': None, 'courier': 'OK', 'used': 0, 'gos': [], 'wait': [], 'empty': 2,
         'emptySince': 0, 'lastFill': 0, 'now': 1000.0, 'near': [{'mint': 'N1'}, {'mint': 'N2'}, {'mint': 'N3'}, {'mint': 'N4'}, {'mint': 'N5'}], 'emptyFor': 0}
    c.update(kw)
    return c


def test_an_empty_seat_takes_the_best_available_only_after_it_waited_and_only_when_nothing_cleared():
    assert oe.fill_plan(_ctx(emptyFor=oe.NEAR_PATIENCE_SEC - 5)) == []                                                  # too soon: the entry moment may still come
    assert [r['mint'] for r in oe.fill_plan(_ctx(emptyFor=oe.NEAR_PATIENCE_SEC))] == ['N1', 'N2', 'N3', 'N4']   # 2 seats + 2 fallbacks
    assert [r['mint'] for r in oe.fill_plan(_ctx(emptyFor=999, gos=[{'mint': 'GO'}]))] == ['GO']  # a real GO always first, near-ready never mixed in
    assert oe.fill_plan(_ctx(emptyFor=999, pol={'entry': 'go'})) == []                            # the creator's "GO only" stands
    assert oe.fill_plan(_ctx(emptyFor=999, courier='BAD')) == [] and oe.fill_plan(_ctx(emptyFor=999, live=False)) == []
    assert len(oe.fill_plan(_ctx(emptyFor=999, used=oe._ag.CONTROL_MOVES_HR - 1))) == 1           # the hourly buy budget still caps it


def test_warden_gives_a_best_available_coin_a_full_seat():
    """Owner, 2026-10-11: "use all card cash" — W19 no longer halves a best-available / seat-floor fill (NEAR_SIZE 1.0)."""
    base = {'liq': 500_000, 'ageH': 30, 'courier': 'OK'}
    full = of.warden(1.0, base)
    near = of.warden(1.0, {**base, 'near': 'best available after 30s — not yet: chart'})
    assert of.NEAR_SIZE == 1.0 and abs(near['allowed'] - full['allowed']) < 1e-9


def test_the_service_wires_best_available_into_the_one_fill_path():
    import inspect
    import reputation_service as rs
    src = inspect.getsource(rs._prime_tick_inner)
    assert '_oe.near_ready(' in src and "'near': near_" in src and "'emptyFor': empty_for_" in src and 'best available' in src
    assert "'near': t_.get('nearReady')" in inspect.getsource(rs._office_ctx)                    # → Warden W19 sizes it


def test_a_seat_is_never_called_stuck_before_the_keeper_had_a_buy_pass_at_it():
    import fuse_wallet as fw
    card = {'legs': [{'mint': 'NEW', 'pairAddress': 'PN', 'buying': True, 'buyingSince': 1000.0}]}
    assert fw.stuck_buys(card, 1100.0) == ['PN']                                                  # old behaviour: 30s and out
    assert fw.stuck_buys(card, 1100.0, buy_pass_at=990.0) == []                                   # the keeper never reached its buy step since
    assert fw.stuck_buys(card, 1100.0, buy_pass_at=1010.0) == ['PN']                              # it had its chance and built nothing → re-pick
    assert fw.stuck_buys({'legs': [{**card['legs'][0], 'mint': 'B'}]}, 1001.0, benched_mints={'B'}, buy_pass_at=0) == ['PN']   # benched: at once


def test_the_stuck_check_judges_a_new_coin_by_the_keepers_new_seat_floor():
    import inspect
    import fuse_wallet as fw
    import reputation_service as rs
    src = inspect.getsource(rs._prime_tick_inner)
    assert 'buy_pass_at=_FW_BUY_PASS.get(tid' in src and '_fw.NEW_SEAT_MIN if not _fw.held_units(book_s' in src
    assert '_FW_BUY_PASS[tid] = time.time()' in inspect.getsource(rs._fw_tick_inner if hasattr(rs, '_fw_tick_inner') else rs._fw_tick)
    assert fw.NEW_SEAT_MIN <= 0.05


def test_a_written_off_coin_is_never_adopted_back_into_the_card():
    import fuse_wallet as fw
    books = {'degen': {'legs': {}}}
    ledger = [{'card': 'degen', 'side': 'sell', 'mint': 'DEAD', 'pair': 'PD', 'symbol': 'DEAD', 'at': 100.0, 'status': 'skipped'},
              {'card': 'degen', 'side': 'writeoff', 'mint': 'DEAD', 'pair': 'PD', 'symbol': 'DEAD', 'at': 101.0, 'status': 'done'}]
    assert fw.strays({'DEAD': 5000}, {'DEAD': 6}, books, ledger, 10_000.0) == []
    ledger2 = ledger + [{'card': 'degen', 'side': 'sell', 'mint': 'LIVE', 'pair': 'PL', 'symbol': 'LIVE', 'at': 200.0, 'status': 'failed'}]
    assert [s['mint'] for s in fw.strays({'DEAD': 5000, 'LIVE': 7}, {}, books, ledger2, 10_000.0)] == ['LIVE']   # a real leftover still comes back


def test_the_hourly_budget_counts_real_buys_not_seats_that_never_bought():
    ev = [{'kind': 'agent', 'move': 'fill', 'mint': 'A', 'at': 1000.0}, {'kind': 'agent', 'move': 'fill', 'mint': 'B', 'at': 1000.0},   # never bought
          {'kind': 'agent', 'move': 'fill', 'mint': 'C', 'at': 1200.0}, {'kind': 'agent', 'move': 'swap', 'mint': 'D', 'at': 1300.0},
          {'kind': 'agent', 'move': 'fill', 'mint': 'E', 'at': 1950.0},                                                               # still landing
          {'kind': 'agent', 'move': 'swap', 'at': 1400.0},                                                                            # old event, no coin id: counts
          {'kind': 'agent', 'move': 'pull', 'mint': 'C', 'at': 1500.0}, {'kind': 'rotate', 'mint': 'A', 'at': 1055.0}]
    led = [{'card': 'degen', 'side': 'buy', 'status': 'filled', 'mint': 'C', 'at': 1203.0}, {'card': 'degen', 'side': 'buy', 'status': 'filled', 'mint': 'D', 'at': 1301.0},
           {'card': 'degen', 'side': 'buy', 'status': 'skipped', 'mint': 'B', 'at': 1010.0}, {'card': 'other', 'side': 'buy', 'status': 'filled', 'mint': 'A', 'at': 1010.0}]
    assert oe.real_buys(ev, led, 'degen', 2000.0) == 4                                          # C, D, E (landing), the id-less swap — never A or B
    assert oe.real_buys(ev, led, 'degen', 2000.0 + 3600) == 0                                   # an hour later the window is empty
    import inspect
    import reputation_service as rs
    src = inspect.getsource(rs._prime_tick_inner)
    assert src.count('_oe.real_buys(') >= 2 and "e.get('move') in ('fill', 'swap') and now -" not in src


def test_best_available_has_its_own_live_check_the_entry_moment_may_wait_a_broken_chart_may_not():
    row = {'px': 1.0, 'nums': {'liq': 100_000}}
    mkt = {'px': 1.01, 'liq': 95_000}
    wait = {'src': 'candles', 'n': 30, 'f': {'stepN': 30, 'volCv': 0.9}, 'state': 'RANGE', 'entry': ['WAIT FOR BREAKOUT', 'x', 'waits for a close above 1.05'], 'risk': [0.75, 'range'], 'q': {'readOk': True}}
    assert oe.live_check(row, mkt, wait, 1000.0)['ok'] is False                                  # a cleared case: the chart must still say ENTER NOW
    assert oe.live_check(row, mkt, wait, 1000.0, near=True)['ok'] is True                        # best available: that is what "near" means
    assert oe.live_check(row, mkt, {**wait, 'entry': ['SKIP', 'x', 'falling']}, 1000.0, near=True)['ok'] is False
    assert oe.live_check(row, mkt, {**wait, 'state': 'DATA INVALID', 'risk': [0.0, 'bad']}, 1000.0, near=True)['ok'] is False
    assert oe.live_check(row, {'px': 1.2, 'liq': 95_000}, wait, 1000.0, near=True)['ok'] is False   # a chase is still a chase
    assert oe.live_check(row, {'px': 1.0, 'liq': 30_000}, wait, 1000.0, near=True)['ok'] is False   # a drained pool is still out
    assert oe.fill_plan(_ctx(emptyFor=999, wait=[{'mint': 'CLEARED'}], lastFill=999.0, emptySince=990.0)) == []   # a cleared coin on the seat timer beats best-available


def test_time_exits_wait_while_the_buy_budget_is_used_safety_exits_never_do():
    dec = [{'pair': 'A', 'action': 'hold'}, {'pair': 'B', 'action': 'hold'}, {'pair': 'C', 'action': 'hold'}, {'pair': 'D', 'action': 'hold'}]
    rep = [{'pair': 'A', 'action': 'pull', 'rule': 'R9 windows used', 'evidence': '3 of 3', 'pct': -4.0}, {'pair': 'B', 'action': 'pull', 'rule': 'R5 stop', 'evidence': '-30%'},
           {'pair': 'C', 'action': 'pull', 'rule': 'R9c creator max hold', 'evidence': 'yours'}, {'pair': 'D', 'action': 'pull', 'rule': 'R9e no extension earned', 'evidence': 'x', 'pct': -5.0}]
    got = {d['pair']: d['action'] for d in of.merge_reaper(dec, [dict(r) for r in rep], buys_left=0)}
    assert got == {'A': 'hold', 'B': 'pull', 'C': 'pull', 'D': 'hold'}
    assert {d['pair']: d['action'] for d in of.merge_reaper(dec, [dict(r) for r in rep], buys_left=2)} == {'A': 'pull', 'B': 'pull', 'C': 'pull', 'D': 'pull'}
    r_ = [dict(r) for r in rep]
    of.merge_reaper(dec, r_, buys_left=0)
    assert 'no replacement is ready' in r_[0]['deferred'] and 'deferred' not in r_[1]
    import inspect
    import reputation_service as rs
    assert 'min(fills_left_, ready_n) - open_n' in inspect.getsource(rs._prime_tick_inner)                            # the open seats take the free buys first


def test_a_deferred_time_exit_reads_hold_on_the_seat_board():
    import seat_ops as so
    r = {'action': 'pull', 'rule': 'R9 windows used', 'state': 'EXIT INVALIDATED', 'pct': -1.0, 'deferred': 'the hourly buy budget is used'}
    assert so.seat_result(r, {'action': 'hold'}) == 'HOLD' and so.seat_result({**r, 'deferred': None}, {'action': 'hold'}) == 'EXIT'


def test_a_time_exit_is_a_swap_the_weakest_flat_coin_uses_the_one_spare_replacement():
    dec = [{'pair': 'A', 'action': 'hold'}, {'pair': 'B', 'action': 'hold'}]
    rep = [{'pair': 'A', 'action': 'pull', 'rule': 'R9 windows used', 'evidence': 'x', 'pct': -3.5}, {'pair': 'B', 'action': 'pull', 'rule': 'R9 windows used', 'evidence': 'x', 'pct': -6.0}]
    got = {d['pair']: d['action'] for d in of.merge_reaper(dec, [dict(r) for r in rep], buys_left=1)}
    assert got == {'A': 'hold', 'B': 'pull'}                                                     # one replacement ready → only the weaker coin is swapped
    r_ = [dict(r) for r in rep]
    of.merge_reaper(dec, r_, buys_left=0)
    assert all('no replacement is ready' in x['deferred'] for x in r_)
    import inspect
    import reputation_service as rs
    src = inspect.getsource(rs._prime_tick_inner)
    assert 'ready_n = len([c_ for c_ in pool_ if c_[\'cleared\']]) + len(_oe.near_ready(pool_, scores_))' in src and 'min(fills_left_, ready_n) - open_n' in src


def test_a_flat_coin_keeps_its_seat_unless_it_is_losing_or_a_clearly_better_coin_is_ready():
    dec = [{'pair': p, 'action': 'hold'} for p in 'ABCD']
    rep = [{'pair': 'A', 'mint': 'a', 'action': 'pull', 'rule': 'R9 windows used', 'evidence': 'x', 'pct': 0.4},     # flat, nothing better
           {'pair': 'B', 'mint': 'b', 'action': 'pull', 'rule': 'R9 windows used', 'evidence': 'x', 'pct': -4.0},    # losing: cut
           {'pair': 'C', 'mint': 'c', 'action': 'pull', 'rule': 'R9e no extension earned', 'evidence': 'x', 'pct': 1.0},   # flat, a clearly better coin
           {'pair': 'D', 'mint': 'd', 'action': 'pull', 'rule': 'R5 stop', 'evidence': 'x', 'pct': -9.0}]           # a stop always acts
    edge = {'a': (5.0, 15.0), 'c': (22.0, 15.0)}
    r_ = [dict(r) for r in rep]
    got = {d['pair']: d['action'] for d in of.merge_reaper(dec, r_, buys_left=4, edge=edge)}
    assert got == {'A': 'hold', 'B': 'pull', 'C': 'pull', 'D': 'pull'}
    assert 'a swap costs ~2% round trip' in r_[0]['deferred'] and 'needs +15' in r_[0]['deferred']
    assert {d['pair']: d['action'] for d in of.merge_reaper(dec, [dict(r) for r in rep], buys_left=None, edge=edge)} == {p: 'pull' for p in 'ABCD'}   # engine cards: unchanged
    import inspect
    import reputation_service as rs
    assert 'spare_, edge=margins_)' in inspect.getsource(rs._prime_tick_inner)


def test_the_agents_work_three_times_as_fast():
    """Owner, 2026-10-11: "seats never empty — agents must work 3× as fast": a pass every 18s (was 55), an empty seat ticks every 8s (was 25),
    best available after 10s (was 30), a candidate's live move wakes a pass after 8s (was 20), the cleared-case seat timer 10s (was 30)."""
    import reputation_service as rs, market_wake as mw
    assert rs.AGENTS_EVERY <= 20 and rs.SEAT_HEARTBEAT_SEC <= 10 and oe.NEAR_PATIENCE_SEC <= 10 and mw.GAP_CAND <= 10 and oe.SEAT_TARGET_AUTO <= 10
    assert oe._ag.FILL_MOVES_HR >= 36   # the fill guard grows with the pace (switches keep CONTROL_MOVES_HR)


def test_a_coin_the_agents_just_left_is_not_bought_back():
    """2026-10-11: $Rupshld was filled → rug-radar exit → filled again 3× in a minute (real buys), then its pool was pulled."""
    import arena_prime as ap
    card = {'cash': 0.0, 'legs': [{'mint': 'RUG', 'symbol': 'RUG', 'pairAddress': 'P1', 'units': 100.0, 'entry': 0.001},
                                  {'mint': 'OK', 'symbol': 'OK', 'pairAddress': 'P2', 'units': 100.0, 'entry': 0.001}]}
    c = ap.agent_pull(card, 'P1', {'P1': 0.001}, {}, 1000.0, '☠ Reaper R4r rug radar: 🚨 a top holder dumped $226')
    c = ap.agent_pull(c, 'P2', {'P2': 0.001}, {}, 1000.0, '☠ Reaper R7s structure turned: +3.2%')
    assert ap.agent_out(c, 1100.0) == {'RUG', 'OK'}                       # nothing comes straight back
    assert ap.agent_out(c, 1000.0 + ap.AGENT_OUT_SEC + 1) == {'RUG'}      # a plain exit: 10 min
    assert ap.agent_out(c, 1000.0 + ap.AGENT_OUT_DANGER_SEC + 1) == set()  # a rug exit: 6h
    src = open(__import__('reputation_service').__file__).read()
    assert 'cool = set(cool) | _prime.agent_out(cur, now)' in src and "if t_['mint'] in _prime.agent_out(cur, now):" in src


def test_a_chart_that_says_no_chasing_or_too_violent_is_never_bought_by_any_door():
    """Real record 2026-10-11: E2 (no chasing) median −16.8%, E3 (too violent) −13.2% — 11 of 26 stop-outs, bought by best available / ranked."""
    ch = lambda rule: {'src': 'candles', 'state': 'PARABOLIC', 'entry': ['WAIT FOR PULLBACK', rule, 'x'], 'f': {'stepN': 30, 'volCv': 0.3}, 'risk': [0.5]}
    row, mkt = {'px': 1.0, 'nums': {'liq': 20000}}, {'px': 1.0, 'liq': 20000}
    for rule in ('E2 no chasing', 'E2e no chasing (early)', 'E3 too violent'):
        r = oe.live_check(row, mkt, ch(rule), 100.0, near=True, ranked=True)
        assert not r['ok'] and 'never bought' in r['why'], rule
    assert oe.live_check(row, mkt, ch('E4 no direction yet'), 100.0, near=True, ranked=True)['ok']   # the rest keep the old rules


def test_the_six_second_guard_stops_an_agent_seat_at_reapers_own_line():
    import office as of
    legs = [{'mint': 'A', 'pairAddress': 'PA', 'units': 10, 'entry': 1.0, 'real': True, 'at': 0, 'bought': {'tag': '🤖 agents · B-tier'}},
            {'mint': 'B', 'pairAddress': 'PB', 'units': 10, 'entry': 1.0, 'real': True, 'at': 0, 'bought': {'tag': '🎯 your pick'}},
            {'mint': 'C', 'pairAddress': 'PC', 'units': 10, 'entry': 1.0, 'real': True, 'at': 995, 'bought': {'tag': '🤖 agents'}}]
    pos = {m: {'stopNow': 12.0} for m in 'ABC'}
    hits = of.fast_reap(legs, {'A': 0.86, 'B': 0.5, 'C': 0.3}, pos, 1000.0)
    assert [h[0] for h in hits] == ['PA']               # B is yours (the card's own stop) · C: −70% in its first 5s = a feed gap
    assert of.fast_reap(legs, {'A': 0.9}, pos, 1000.0) == []
    src = open(__import__('reputation_service').__file__).read()
    assert '_of.fast_reap(c_.get(\'legs\'), px, _office.get(\'pos\') or {}, now)' in src
