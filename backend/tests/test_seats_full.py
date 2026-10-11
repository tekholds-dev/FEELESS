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
    out = oe.near_ready(cases, scores)
    assert [r['mint'] for r in out] == ['DATA', 'CHART']                                          # best score first; every hard block stays out
    assert 'every safety check passed' in out[0]['nearReady'] and out[0]['pair'] == 'PDATA'
    assert [r['mint'] for r in oe.near_ready(cases, scores, live={'DATA': (False, 'price ran')})] == ['CHART']   # the newest live check wins


def _ctx(**kw):
    c = {'control': True, 'pol': {'entry': 'auto'}, 'live': True, 'halt': None, 'courier': 'OK', 'used': 0, 'gos': [], 'wait': [], 'empty': 2,
         'emptySince': 0, 'lastFill': 0, 'now': 1000.0, 'near': [{'mint': 'N1'}, {'mint': 'N2'}, {'mint': 'N3'}, {'mint': 'N4'}, {'mint': 'N5'}], 'emptyFor': 0}
    c.update(kw)
    return c


def test_an_empty_seat_takes_the_best_available_only_after_it_waited_and_only_when_nothing_cleared():
    assert oe.fill_plan(_ctx(emptyFor=30)) == []                                                  # too soon: the entry moment may still come
    assert [r['mint'] for r in oe.fill_plan(_ctx(emptyFor=oe.NEAR_PATIENCE_SEC))] == ['N1', 'N2', 'N3', 'N4']   # 2 seats + 2 fallbacks
    assert [r['mint'] for r in oe.fill_plan(_ctx(emptyFor=999, gos=[{'mint': 'GO'}]))] == ['GO']  # a real GO always first, near-ready never mixed in
    assert oe.fill_plan(_ctx(emptyFor=999, pol={'entry': 'go'})) == []                            # the creator's "GO only" stands
    assert oe.fill_plan(_ctx(emptyFor=999, courier='BAD')) == [] and oe.fill_plan(_ctx(emptyFor=999, live=False)) == []
    assert len(oe.fill_plan(_ctx(emptyFor=999, used=oe._ag.CONTROL_MOVES_HR - 1))) == 1           # the hourly buy budget still caps it


def test_warden_gives_a_best_available_coin_half_a_seat_at_most():
    base = {'liq': 500_000, 'ageH': 30, 'courier': 'OK'}
    full = of.warden(1.0, base)
    half = of.warden(1.0, {**base, 'near': 'best available after 90s — not yet: chart'})
    assert half['allowed'] <= full['allowed'] * 0.5 + 1e-9 and any(r['id'].startswith('W19') for r in half['rules'])


def test_the_service_wires_best_available_into_the_one_fill_path():
    import inspect
    import reputation_service as rs
    src = inspect.getsource(rs._prime_tick_inner)
    assert '_oe.near_ready(' in src and "'near': near_" in src and "'emptyFor': empty_for_" in src and 'best available' in src
    assert "'near': t_.get('nearReady')" in inspect.getsource(rs._office_ctx)                    # → Warden W19 sizes it
