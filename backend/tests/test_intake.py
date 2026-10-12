"""🕸 ONE DEDUPED LIVE INTAKE (`backend/intake.py` + the service's `_intake_pass`): every existing outlet feeds one registry — dedupe,
first-seen kept, every source preserved, new unique mints per cycle, per-source funnel, latencies, fresh launches never crowded out.
No network, no wallet, no order."""
import asyncio

import intake as it
import office_edge as oe


def test_one_registry_dedupes_every_outlet_keeps_first_seen_and_every_source():
    r, new_by, new_all = it.note({}, {'pulse': [{'mint': 'A', 'symbol': 'AAA', 'born': 990, 'pad': 'pump'}], 'open': [{'mint': 'A'}, {'mint': 'B', 'symbol': 'BBB'}]}, 1000)
    assert set(r) == {'A', 'B'} and new_all == ['A', 'B'] and new_by == {'pulse': ['A'], 'open': ['A', 'B']}
    assert r['A']['first'] == 1000 and r['A']['born'] == 990 and r['A']['symbol'] == 'AAA' and set(r['A']['src']) == {'pulse', 'open'}
    r2, nb2, na2 = it.note(r, {'open': [{'mint': 'A'}, {'mint': 'B'}], 'calls': [{'mint': 'B'}], 'list:movers': [{'mint': 'C'}]}, 1060)
    assert na2 == ['C'] and nb2 == {'calls': ['B'], 'list:movers': ['C']}                     # B was seen before: new TO callouts only
    assert r2['A']['first'] == 1000 and r2['A']['last'] == 1060 and r2['B']['src'] == {'open': 1000, 'calls': 1060}   # first seen never moves
    assert it.srcs_of(r2['B']) == ['open', 'calls'] and it.label('list:movers') == 'list · movers' and it.label('pulse').startswith('Pump pulse')
    big = {f'M{i}': {'first': 0, 'last': i, 'src': {'open': 0}} for i in range(it.KEEP + 50)}
    r3, _, _ = it.note(big, {'open': [{'mint': 'NEW'}]}, it.KEEP + 60)
    assert len(r3) <= it.KEEP and 'NEW' in r3                                                  # bounded, newest kept


def test_the_office_stamps_each_stage_once_and_latency_is_measured_between_them():
    r, _, _ = it.note({}, {'pulse': [{'mint': 'A', 'born': 950}], 'open': [{'mint': 'B'}]}, 1000)
    r = it.stamp(r, 'intake', ['A', 'B'], 1000)
    r = it.stamp(r, 'intake', ['A'], 1100)                                                     # set once
    r = it.stamp(r, 'deep', ['A'], 1060)
    r = it.stamp(r, 'clear', ['A'], 1120)
    r = it.stamp(r, 'seat', ['A'], 1150)
    r = it.stamp(r, 'seat', ['ZZ'], 1150)                                                      # unknown coin: nothing invented
    assert r['A']['intake'] == 1000 and 'ZZ' not in r
    lat = it.latency(r, 1200)
    assert lat['sourceToIntake'] == {'med': 0.0, 'n': 2} and lat['intakeToDeep'] == {'med': 60.0, 'n': 1} and lat['deepToClear'] == {'med': 60.0, 'n': 1}
    assert lat['clearToSeat'] == {'med': 30.0, 'n': 1} and lat['birthToSeen'] == {'med': 50.0, 'n': 1}
    r = it.outcome(r, 'A', 12.5, 1300)
    f = it.per_source(r, 1300)
    assert f['pulse'] == {'seen': 1, 'firstFinder': 1, 'promoted': 1, 'deep': 1, 'cleared': 1, 'bought': 1, 'won': 1, 'lost': 0,
                          'winRate': 100, 'medPct': 12.5, 'rugRate': 0, 'timeToEntry': 150.0}
    assert f['open']['promoted'] == 1 and f['open']['bought'] == 0


def test_each_cycle_counts_unique_seen_new_unique_and_desk_turnover():
    r, nb, na = it.note({}, {'pulse': [{'mint': 'P1'}, {'mint': 'P2'}], 'open': [{'mint': 'O1'}, {'mint': 'P1'}]}, 1000)
    cy = it.cycle(r, {'pulse': [{'mint': 'P1'}, {'mint': 'P2'}], 'open': [{'mint': 'O1'}, {'mint': 'P1'}]}, nb, na, ['P1', 'O1'], ['O1', 'OLD'], 1000)
    assert cy['uniqueSeen'] == 3 and cy['newUnique'] == 3 and cy['newBy'] == {'pulse': 2, 'open': 2} and cy['desk'] == 2 and cy['deskNew'] == 1
    assert cy['mix'] == {'pulse': 1, 'open': 1}


def test_fresh_launches_get_reserved_room_and_old_volume_leaders_never_crowd_them_out():
    old = [{'mint': f'V{i}', 'symbol': f'V{i}', 'ageH': 300, 'front': 90, 'vol1h': 1e6, 'vol5m': 1e5} for i in range(400)]
    fresh = [{'mint': f'F{i}', 'symbol': f'F{i}', 'ageH': 0.01 * i, 'front': 1, 'vol5m': 100} for i in range(10)]
    out = oe.intake(old + fresh, fresh={f'F{i}': ['pulse'] for i in range(10)})
    tags = {x['mint']: x['intake'] for x in out}
    assert all(f'F{i}' in tags and 'fresh' in tags[f'F{i}'] for i in range(10)) and len(out) <= oe.INTAKE_MAX
    oth = oe.intake(old + [{'mint': 'CALLED', 'ageH': 300, 'front': 0.1}], outlets={'CALLED': ['calls']})
    assert 'outlets' in {x['mint']: x['intake'] for x in oth}['CALLED']                        # a callout the board ranks last still reaches the desk
    cooled = oe.intake(old + fresh, fresh={'F1': ['pulse']}, cool={'V0', 'V1'})
    assert 'V0' not in {x['mint'] for x in cooled} and 'F1' in {x['mint'] for x in cooled}     # a rejected coin with nothing new makes room


def test_the_service_reads_every_outlet_once_and_builds_rows_for_coins_the_board_does_not_carry(monkeypatch):
    import reputation_service as rs
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    monkeypatch.setitem(rs._intake, 'reg', {})
    monkeypatch.setitem(rs._office, 'load', {})
    monkeypatch.setattr(rs, '_runner_cands', [{'mint': 'RUN', 'symbol': 'RUN'}])
    monkeypatch.setattr(rs, '_lens_rows', {'movers': [{'mint': 'MOV', 'symbol': 'MOV'}]})
    monkeypatch.setitem(rs._pump_calls, 'calls', [{'mint': 'CALL', 'symbol': 'CALL'}])
    monkeypatch.setitem(rs._feeders, 'board', {'runners': {'FEDR': {}}, 'kids': {}})
    monkeypatch.setitem(rs._radar, 'pairs', {})

    class R:
        def json(self):
            return {'status': 'live', 'launches': [{'mint': 'NEWBpump', 'symbol': 'NEWBpump', 'at': 999_000.0}], 'migrations': [{'mint': 'MIGR', 'symbol': 'MIGR'}], 'launchesPerMinute': [3, 4, 5]}

    class C:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None):
            assert url.endswith('/api/pump/pulse')
            return R()
    asked = []

    async def jt(mints):
        asked.extend(mints)
        return {'NEWBpump': {'id': 'NEWBpump', 'symbol': 'NEWBpump', 'usdPrice': 0.0001, 'liquidity': 9000, 'mcap': 100_000, 'firstPool': {'id': 'CURVE1', 'createdAt': '2026-10-10T20:00:00Z'},
                         'stats5m': {'buyVolume': 3000, 'sellVolume': 1000, 'numBuys': 40, 'numSells': 10, 'priceChange': 12}, 'stats1h': {'buyVolume': 3000, 'sellVolume': 1000}}}
    monkeypatch.setattr(rs.httpx, 'AsyncClient', C)
    monkeypatch.setattr(rs, '_jup_tokens', jt)
    monkeypatch.setattr(rs, '_json_load', lambda path, default=None: default if default is not None else {})
    extra, fresh, outl = asyncio.run(rs._intake_pass([{'mint': 'BOARD', 'symbol': 'BOARD', 'ageH': 2}], 1000.0))
    reg = rs._intake['reg']
    assert {'BOARD', 'NEWBpump', 'MIGR', 'RUN', 'MOV', 'CALL', 'FEDR'} <= set(reg)
    assert set(reg['NEWBpump']['src']) == {'pulse'} and reg['NEWBpump']['born'] == 999.0 and reg['MOV']['src'] == {'list:movers': 1000.0}
    assert fresh == {'NEWBpump': ['pulse'], 'MIGR': ['migr']} and outl['CALL'] == ['calls'] and outl['FEDR'] == ['feeders'] and outl['RUN'] == ['runner']
    assert 'BOARD' not in asked and {'NEWBpump', 'MIGR', 'CALL'} <= set(asked)                    # ONE batched read, only for coins the board does not carry
    assert [r['mint'] for r in extra] == ['NEWBpump'] and extra[0]['curve'] is True and extra[0]['safe'] is None and extra[0]['outlet']
    assert rs._intake['last']['new'] == 7 and rs._intake['last']['newBy']['pulse'] == 1 and rs._intake['last']['pending'] >= 1   # MIGR / CALL: no market data yet — seen, not invented
    v = rs._intake_view(1000.0)
    assert v['registry'] == 7 and 'pulse' in v['sources'] and 'context' in v['note']


def test_tallys_tape_keeps_at_least_every_coin_the_intake_can_read():
    import agents as ag
    assert ag.SERIES_COINS >= oe.INTAKE_MAX                                                     # a coin read this pass never loses its tape to the next


def test_the_agents_pass_runs_on_its_own_sixty_second_loop_never_behind_the_warm_loop():
    import inspect
    import reputation_service as rs
    assert '_agents_tick' not in inspect.getsource(rs._fuse_warm)                               # it rode the warm loop and ran every ~3 min
    src = inspect.getsource(rs._agents_loop)
    assert '_agents_tick' in src and '_runner_live' in src
    assert rs.AGENTS_EVERY <= 60


def test_two_callers_share_one_board_build(monkeypatch):
    import reputation_service as rs
    built = []

    async def slow():
        built.append(1)
        await asyncio.sleep(0.05)
        rs._runner_live_cache.update(at=1e12, data={'rows': ['x']})
        return {'rows': ['x']}
    monkeypatch.setattr(rs, '_runner_live_build', slow)
    monkeypatch.setattr(rs, '_runner_live_cache', {'at': 0.0, 'data': {'rows': ['old']}})

    async def both():
        return await asyncio.gather(rs._runner_live(), rs._runner_live())
    a, b = asyncio.run(both())
    assert len(built) == 1 and {'rows': ['old']} in (a, b)                                   # the second caller read the last board while one build ran


def test_a_deep_review_always_says_why_the_coin_was_due():
    import reputation_service as rs
    assert rs._deep_bucket('never deep-reviewed') == 'first look' and rs._deep_bucket('was not rejected') == 'not rejected'
    assert rs._deep_bucket('changed: price +6.0%') == 'news' and rs._deep_bucket('cooldown over') == 'cooldown over'
    assert rs.OFFICE_CANDLE_CASES + rs.OFFICE_CANDLE_NEW <= 30                                # deep review stays selective
