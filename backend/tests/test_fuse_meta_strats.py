"""Anchors ranked by activity (no SOL head start), dip / dex-paid strategies, retiring proven losers."""
import contenders
import fuse
import fuse_hq
import runners


def _maj(sym, liq=5e6, vol=5e6, c1=0.0, c6=0.0, c24=0.0, bs=50, mint=None, **kw):
    return {'symbol': sym, 'baseAddress': mint or f'{sym}mint', 'pairAddress': f'{sym}pair', 'priceUsd': 1.0, 'liquidityUsd': liq, 'volume24h': vol,
            'turnover': vol / liq, 'change1h': c1, 'change6h': c6, 'change24h': c24, 'buyShare': bs, **kw}


def test_anchors_rank_by_activity_not_by_name():
    sol = _maj('SOL', liq=50e6, vol=20e6, c1=0.1, c6=0.2, c24=0.3)        # deep but flat today
    pump = _maj('PUMP', liq=8e6, vol=24e6, c1=2.5, c6=6, c24=11, bs=58)  # moving with buyers
    rows = fuse.rank_anchors([sol, pump])
    assert [r['symbol'] for r in rows] == ['PUMP', 'SOL']
    assert rows[0]['anchorWhy'] and all('part' in p for p in rows[0]['anchorWhy'])


def test_stables_lsts_and_thin_majors_never_anchor():
    rows = fuse.rank_anchors([_maj('USDC'), _maj('JitoSOL'), _maj('BONK', liq=100_000), _maj('JUP', c24=4)])
    assert [r['symbol'] for r in rows] == ['JUP']


def test_falling_knife_major_pays_and_new_majors_are_capped_and_aged():
    knife = fuse.rank_anchors([_maj('WIF', c24=-30)])[0]
    assert any(p['part'] == 'falling' and p['points'] < 0 for p in knife['anchorWhy'])
    now = 10 * 8.64e7
    risers = [_maj(f'N{i}', liq=600_000, vol=4e6, c24=12, mcap=9e6, createdAt=now - 3 * 8.64e7) for i in range(6)]
    risers += [_maj('BABY', liq=900_000, vol=9e6, c24=40, mcap=20e6, createdAt=now - 3600_000)]   # an hour old: not a major yet
    risers += [_maj('SMALL', liq=900_000, vol=9e6, c24=40, mcap=2e6, createdAt=now - 3 * 8.64e7)]  # under $5M
    rows = fuse.rank_anchors([_maj('SOL')], risers, now_ms=now, max_new=4)
    new = [r for r in rows if r.get('newMajor')]
    assert len(new) == 4 and not {'BABY', 'SMALL'} & {r['symbol'] for r in rows}


def test_majors_list_has_the_movers_and_flags_lookalikes():
    syms = {v[0] for v in fuse.MAJORS.values()}
    assert {'PUMP', 'POPCAT', 'TRUMP', 'PENGU', 'FARTCOIN', 'JUP', 'BONK', 'WIF'} <= syms
    assert len(fuse.MAJORS) <= 30   # DexScreener tokens/v1 takes at most 30 mints in one call
    out = fuse.mark_real([{'baseAddress': 'fake', 'symbol': 'TRUMP', 'liquidityUsd': 1}], 'TRUMP')
    assert out[0]['impostor']


def test_dip_score_needs_buyers_back():
    assert fuse.dip_score({'change24h': -3}) == 0
    bounce = fuse.dip_score({'change24h': -30, 'change1h': 2, 'buyShare': 60})
    knife = fuse.dip_score({'change24h': -30, 'change1h': -4, 'buyShare': 40})
    assert bounce == 75.0 and knife == round(75 * 0.3, 1)


def test_dip_and_meta_styles_pick_their_coins():
    def m(pa, c24, c1, bs, paid=False):
        return {'pairAddress': pa, 'baseAddress': pa, 'symbol': pa, 'liquidityUsd': 2e6, 'volume24h': 2e6, 'aprEst': 30, 'change24h': c24,
                'change1h': c1, 'buyShare': bs, 'paid': paid, 'priceUsd': 1, 'turnover': 1.0}
    metas = {'dipA': m('dipA', -30, 3, 62), 'dipB': m('dipB', -25, 1, 60), 'flatA': m('flatA', 1, 0, 50), 'flatB': m('flatB', 2, 0, 50),
             'paidA': m('paidA', 8, 2, 58, True), 'paidB': m('paidB', 6, 1, 56, True)}
    assert set(fuse.evolve(metas, legs=2, style='dip', generations=10, population=12)['champions'][0]['pools']) == {'dipA', 'dipB'}
    assert set(fuse.evolve(metas, legs=2, style='meta', generations=10, population=12)['champions'][0]['pools']) == {'paidA', 'paidB'}
    assert fuse.fitness(['dipA', 'dipB'], metas, 'dip')['parts']['dipScore'] > 0


def test_dex_paid_needs_a_real_paid_profile():
    assert fuse.dex_paid({'info': {'header': 'x'}})
    assert fuse.dex_paid({'boosts': {'active': 10}})
    assert not fuse.dex_paid({'info': {'imageUrl': 'logo'}})   # a logo alone is not a paid profile


def test_losing_strategies_retire_and_only_probe_daily():
    board = [{'style': 'yield', 'runs': 5, 'avgPct': -4.0, 'medPct': -2.0}, {'style': 'dip', 'runs': 5, 'avgPct': 3.0, 'medPct': 1.0},
             {'style': 'degen', 'runs': 2, 'avgPct': -9.0, 'medPct': -9.0}, {'style': 'meta', 'runs': 6, 'avgPct': -1.0, 'medPct': 0.5}]
    dead = fuse_hq.retired_styles(board)
    assert dead == {'yield'}                         # too few runs and a positive median both keep a style alive
    arena = [{'style': 'yield', 'auto': True, 'at': 0}]
    assert fuse_hq.autopilot_due(arena, 'yield', 7200)                      # alive: hourly
    assert not fuse_hq.autopilot_due(arena, 'yield', 7200, retired=dead)    # retired: waits for the daily probe
    assert fuse_hq.autopilot_due(arena, 'yield', 25 * 3600, retired=dead)


def _runner(**kw):
    base = {'mint': 'm', 'pairAddress': 'p', 'stage': 'graduated', 'curve': 0, 'mcap': 1e6, 'vol1h': 50_000, 'chg5m': 4, 'chg1h': 1, 'chg24h': -40,
            'buyShare': 60, 'quality': 0, 'snipersOut': False, 'buysAccel': 1.5, 'paid': False}
    return {**base, **kw}


def test_runner_dip_buy_and_dex_paid_parts():
    assert runners.is_dip(_runner())
    assert not runners.is_dip(_runner(chg1h=-12))       # still sliding
    assert not runners.is_dip(_runner(buyShare=45))     # sellers in charge
    pts, parts = runners.score(_runner(paid=True, boosts=20))
    names = {p['part'] for p in parts}
    assert {'dip buy', 'dex paid'} <= names
    base, _ = runners.score(_runner(chg24h=0, paid=False))
    assert pts > base


def test_runner_discover_tags_dips_and_paid_on_their_own():
    rows = runners.discover([_runner(mint='a', score=50), _runner(mint='b', chg24h=0, paid=True, score=40), _runner(mint='c', chg24h=0, score=90)], {})
    tags = {r['mint']: {s['kind'] for s in r['sources']} for r in rows}
    assert tags == {'a': {'dip'}, 'b': {'paid'}}


def test_gauntlet_dip_and_paid_divisions():
    pool = lambda sym, **kw: {'baseAddress': sym, 'pairAddress': sym + 'p', 'symbol': sym, 'priceUsd': 1, 'liquidityUsd': 400_000, 'volume24h': 900_000, **kw}
    rows = [pool('DIP', change24h=-30, change1h=3, buyShare=62), pool('KNIFE', change24h=-30, change1h=-3, buyShare=40),
            pool('PAID', change24h=4, change1h=1, buyShare=55, paid=True, boosts=30)]
    lg = contenders.league({'dip': rows, 'paid': rows})
    div = {d['key']: [r['symbol'] for r in d['rows']] for d in lg['divisions']}
    assert div['dip'] == ['DIP'] and div['paid'] == ['PAID']


def test_swap_pick_accepts_any_live_coin_but_never_a_stable_thin_or_wrong_pool():
    import pytest
    rs = pytest.importorskip('reputation_service')
    pair = lambda mint, sym, liq, px=1.0: {'pairAddress': 'p' + sym, 'baseToken': {'address': mint, 'symbol': sym}, 'priceUsd': px, 'liquidity': {'usd': liq}}
    assert rs._pick_row(pair('M', 'POP', 400_000), 'M') == {'mint': 'M', 'pairAddress': 'pPOP', 'symbol': 'POP', 'price': 1.0, 'liq': 400_000}
    assert rs._pick_row(pair('M', 'POP', 10_000), 'M') is None          # too thin
    assert rs._pick_row(pair('U', 'USDC', 9e6), 'U') is None            # a dollar never moves
    assert rs._pick_row(pair('OTHER', 'POP', 9e6), 'M') is None         # pool is for another coin
    assert rs._pick_row(pair('M', 'POP', 9e6, px=0), 'M') is None       # no live price


def test_runners_list_stays_full_while_a_coin_is_only_rescanned():
    prev = [{'mint': 'A', 'passedAt': 100}, {'mint': 'B', 'passedAt': 100}, {'mint': 'C', 'passedAt': 100}, {'mint': 'OLD', 'passedAt': -1000}, {'mint': 'NOTIME'}]
    now_rows = [{'mint': 'A', 'passedAt': 400}]
    dropped = [{'mint': 'B', 'gates': ['Holder scan done']}, {'mint': 'C', 'gates': ['Top 10 under 30%']}]
    out = runners.sticky(prev, now_rows, dropped, 400, keep=600)
    by = {r['mint']: r for r in out}
    assert set(by) == {'A', 'B'}                      # C failed a REAL gate → gone; OLD too old → gone
    assert by['B']['rechecking'] and not by['A'].get('rechecking')
