"""Fee's setup memory: learns which setups win, sizes up/down, vetoes proven losers, never overreacts to luck."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import feecat_brain as fb  # noqa: E402

NOW = time.time()
PAIR = {'priceChange': {'h1': 22, 'm5': 2}, 'txns': {'h1': {'buys': 300, 'sells': 100}}, 'liquidity': {'usd': 60_000}, 'marketCap': 600_000, 'pairCreatedAt': (NOW - 10 * 3600) * 1000}


def test_features_bucket_the_setup():
    f = fb.setup_features(PAIR, NOW, gap=True)
    assert f == {'h1': '15-30%', 'flow': '2x+', 'depth': '10%+', 'age': '6-24h', 'm5': '1-3%', 'mc': '250K-1M', 'lane': 'core', 'gap': 'fvg', 'fuse': 'none', 'crowd': 'none'}


def test_new_setups_trade_at_probation_size_and_luck_does_not_rewrite_the_playbook():
    setup = fb.setup_features(PAIR, NOW)
    assert fb.setup_edge(setup, {})['mult'] == fb.PROBATION_MULT == 0.25   # untested: small until it proves itself
    lucky = fb.edge_table([{'setup': setup, 'ret': 80, 'win': True, 'at': NOW}] * 3)   # 3 trades < MIN_N
    assert fb.setup_edge(setup, lucky)['mult'] == fb.PROBATION_MULT        # 3 lucky wins are not proof


def test_proven_winner_sizes_up_proven_loser_is_vetoed():
    win = fb.setup_features(PAIR, NOW)
    lose = fb.setup_features({**PAIR, 'priceChange': {'h1': 45, 'm5': 6}}, NOW)
    mem = []
    for i in range(8):
        mem = fb.remember(mem, win, 35 if i % 4 else -10, 0.1 if i % 4 else -0.02, NOW)
        mem = fb.remember(mem, lose, -18, -0.05, NOW)
    table = fb.edge_table(mem)
    up = fb.setup_edge(win, table)
    assert up['mult'] > 1.0 and not up['veto']
    down = fb.setup_edge(lose, table)
    assert down['veto'] and 'lost 8/8' in down['why']
    book = fb.playbook(table)
    assert book['best'][0]['edge'] > 0 and book['worst'][0]['setup'] in ('h1=30%+', 'm5=3%+')


def test_memory_is_bounded():
    mem = []
    for _ in range(fb.MEMORY + 50):
        mem = fb.remember(mem, {'h1': '<5%'}, 1, 0.01, NOW)
    assert len(mem) == fb.MEMORY


def test_discipline_sizes_down_on_streaks_and_steps_away_on_tilt():
    from feecat_brain import discipline
    now = 1_000_000
    ex = lambda pnls, gap=600: [{'pnlSol': p, 'exitAt': now - gap * (len(pnls) - i)} for i, p in enumerate(pnls)]
    assert discipline([], now)['sizeMult'] == 1.0
    three = discipline(ex([0.2, -0.1, -0.1, -0.1]), now)
    assert three['sizeMult'] == 0.5 and three['streak'] == 3 and not three['pause']
    tilt = discipline(ex([-0.1] * 5), now)
    assert tilt['pause'] and 'revenge' in tilt['why']
    assert not discipline(ex([-0.1] * 5, gap=4 * 3600), now)['pause']            # cooled off after 3h
    cold = discipline(ex([-0.1, -0.1, 0.02, -0.1, -0.1, -0.2, -0.1, 0.01, -0.1, -0.1]), now)   # 2/10 won, net red
    assert cold['pause'] and 'cold market' in cold['why']
    neg = discipline(ex([0.1, -0.2, 0.1, -0.2, 0.05]), now)
    assert neg['sizeMult'] == 0.7 and neg['expectancySol'] < 0
    good = discipline(ex([0.3, -0.1, 0.2, 0.1, -0.05, 0.2]), now)
    assert good['sizeMult'] == 1.2 and good['winRate'] >= 50


def test_v3_rules_cut_losers_fast_and_never_average_down():
    import feecat_service as fs
    R = fs.RULES
    assert R['hardStop'] >= -20 and R['add1Fraction'] == 0 and R['add2Fraction'] == 0 and R['pyramidAt'] > 0
    assert R['takeProfit1'] > abs(R['hardStop']) and R['timeStopHours'] <= 3   # winners bigger than losers, dead trades cut


def test_nine_lives_cost_on_losses_regrow_on_wins_and_nap_at_zero():
    import feecat_brain as b
    now = 1_800_000_000
    ex = lambda pnl, ago: {'pnlSol': pnl, 'exitAt': now - ago}
    # spaced out so the 5-in-a-row tilt guard is not what pauses her
    mixed = [ex(-0.01, 80000), ex(-0.01, 70000), ex(0.02, 60000), ex(-0.01, 50000)]
    assert b.discipline(mixed, now)['lives'] == 7 and not b.discipline(mixed, now)['pause']
    nine = [ex(-0.01, 80000 - i * 5000) if i % 4 else ex(-0.01, 80000 - i * 5000) for i in range(9)]
    d = b.discipline([*nine[:4], ex(0.0, 59000), *nine[4:]], now)   # a flat trade breaks the losing streak, not the lives
    assert d['lives'] == 0 and d['pause'] and 'out of lives' in d['why']
    old = [ex(-0.01, 90000 + i) for i in range(9)]                     # losses older than 24h cost nothing
    assert b.discipline(old, now)['lives'] == 9


def test_fuse_edge_vetoes_gate_failures_and_boosts_multi_source_runners():
    import feecat_brain as fb
    disc = {'watching': [{'mint': 'RUG', 'gates': ['top10 holds 61%']}],
            'runners': [{'mint': 'HOT', 'sources': [{'kind': 'arena', 'label': '🏟 Arena pick'}, {'kind': 'pump', 'label': '🚀 Pump scan'}]},
                        {'mint': 'ONE', 'sources': [{'kind': 'pump', 'label': '🚀 Pump scan'}]}]}
    assert fb.fuse_edge('RUG', disc) == {'veto': True, 'mult': 0.0, 'tag': 'gate-fail', 'why': 'Fuse runner gate: top10 holds 61%'}
    hot = fb.fuse_edge('HOT', disc)
    assert hot['mult'] == 1.1 and hot['tag'] == 'fuse-2+' and 'Arena pick' in hot['why']
    assert fb.fuse_edge('ONE', disc)['tag'] == 'fuse-1'
    assert fb.fuse_edge('NEW', disc) == {'veto': False, 'mult': 1.0, 'tag': 'none', 'why': ''}
    assert fb.fuse_edge('HOT', {}) == {'veto': False, 'mult': 1.0, 'tag': 'none', 'why': ''}         # Fuse down → no change
    assert fb.fuse_edge('X', {'runners': [{'mint': 'X', 'sources': [{}] * 9}]})['mult'] == 1.2      # capped
    assert fb.setup_features({}, 0, fuse='fuse-2+')['fuse'] == 'fuse-2+'


def test_feecat_learns_from_elite_traders_and_files_the_tag():
    import feecat_brain as fb
    feed = {'flow': {'HOT': {'n': 2, 'usd': 300}, 'ONE': {'n': 1, 'usd': 20}}}
    hot = fb.crowd_edge('HOT', feed)
    assert hot['mult'] == 1.1 and hot['tag'] == 'elite-2+' and '2 elite FEELESS traders' in hot['why']
    assert fb.crowd_edge('ONE', feed)['tag'] == 'elite-1' and fb.crowd_edge('X', feed) == {'mult': 1.0, 'tag': 'none', 'why': ''}
    assert fb.crowd_edge('HOT', {'flow': {'HOT': {'n': 9}}})['mult'] == 1.15                       # capped
    assert fb.setup_features({}, 0, crowd='elite-1')['crowd'] == 'elite-1'


def test_feecat_pnl_is_the_price_move_fees_apart(monkeypatch):
    import pytest
    fs = pytest.importorskip('feecat_service')
    monkeypatch.setattr(fs, '_log_event', lambda *a, **k: None); monkeypatch.setattr(fs, '_post_as_fee', lambda *a, **k: None)
    cat = {'balanceSol': 0.0, 'positions': []}
    pos = {'pairAddress': 'P', 'symbol': 'X', 'costSol': 1.0, 'notionalSol': 1.0 * (1 - fs.FEE_PER_SIDE), 'entryPriceNative': 1.0, 'openedAt': 0}
    fs._close({}, cat, pos, 1.5, 'tp')                                                       # +50% price move
    assert abs(cat['realizedPnlSol'] - 0.99 * 0.5) < 1e-6                                     # P&L = the move on pool money
    assert abs(cat['feesSol'] - (0.01 + 0.99 * 1.5 * fs.FEE_PER_SIDE)) < 1e-6                # both sides' fees, apart
    assert abs(cat['balanceSol'] - 0.99 * 1.5 * (1 - fs.FEE_PER_SIDE)) < 1e-6                # balance = real money after fees
