"""🕵 Adversarial launch intelligence: early-buyer map, launch class, wallet actions + memory, FOMO phase, exit pressure, buyer rank,
and how it reaches the ranking, the Warden, Reaper and the Judge."""
import launch_intel as li
import office
import opportunity as opp
import judge_review as jr


def _early(n=12, sol=0.5, slot0=100, same_slot=0):
    return [{'w': f'w{i}', 'slot': slot0 if i < same_slot else slot0 + i, 'sol': sol + i * 0.11, 'pct': 2.0} for i in range(n)]


def test_early_map_concentration_and_actions():
    hold = {'w0': 2.0, 'w1': 0.0, 'w2': 1.0, 'w3': 3.0}
    m = li.early_map(_early(12), hold)
    assert m['first10Pct'] == 20.0 and m['first25Pct'] == 24.0 and m['largestPct'] == 2.0 and m['read'] == 4 and m['nowPct'] == 6.0
    acts = {w['w']: w['action'] for w in m['wallets']}
    assert acts['w0'] == 'HOLD' and acts['w1'] == 'EXIT' and acts['w2'] == 'PARTIAL SELL' and acts['w3'] == 'ADD' and acts['w5'] is None
    assert li.early_map(_early(3), {'w1': 0}, young=True)['wallets'][1]['action'] == 'DUMP'
    assert li.early_map([]) is None


def test_clusters_and_classes():
    same = li.early_map(_early(10, same_slot=4))
    assert any(c['kind'] == 'slot' for c in same['clusters'])
    assert li.classify(same, 4, 0)[0] == 'BUNDLED'
    sized = li.early_map([{'w': f'w{i}', 'slot': i, 'sol': 1.0, 'pct': 6.0} for i in range(4)])
    assert any(c['kind'] == 'size' for c in sized['clusters']) and sized['clusterPct'] == 24.0
    funded = li.early_map(_early(5), funders={'w0': 'F', 'w1': 'F'})
    assert li.classify(funded, 0, 0)[0] == 'INSIDER-LIKE CLUSTER'
    assert li.classify(li.early_map(_early(5)), 0, 6)[0] == 'HEAVY SNIPER ACTIVITY'
    assert li.classify(li.early_map(_early(5)), 0, 1)[0] == 'NORMAL'
    assert li.classify(None, None, None)[0] == 'UNKNOWN'


def test_trend_reads_the_early_supply_over_time():
    assert li.trend([[0, 30], [1, 20]]) == 'IMPROVING' and li.trend([[0, 20], [1, 30]]) == 'WORSENING' and li.trend([[0, 20], [1, 20.5]]) == 'STABLE'
    assert li.trend([[0, 20]]) is None


def test_wallet_memory_needs_three_launches_and_learns_dumpers():
    mem = {}
    for k in range(2):
        m = li.early_map([{'w': 'D', 'slot': 1, 'sol': 1, 'pct': 5}], {'D': 0}, young=True)
        mem = li.remember(mem, m, -90)
    assert li.wclass(mem['D'])[0] == 'UNKNOWN'                  # never a label from two launches
    mem = li.remember(mem, li.early_map([{'w': 'D', 'slot': 1, 'sol': 1, 'pct': 5}], {'D': 0}, young=True), 10)
    c, conf, n = li.wclass(mem['D'])
    assert n == 3 and c == 'RUG-ASSOCIATED' and conf > 0
    win = {}
    for _ in range(3):
        win = li.remember(win, li.early_map([{'w': 'W', 'slot': 1, 'sol': 1, 'pct': 5}], {'W': 5}), 120)
    assert li.wclass(win['W'])[0] == 'EARLY WINNER WALLET'
    fast = {}
    for _ in range(3):
        fast = li.remember(fast, li.early_map([{'w': 'F', 'slot': 1, 'sol': 1, 'pct': 5}], {'F': 0}, young=True), 5)
    assert li.wclass(fast['F'])[0] == 'FAST DUMPER'


def test_exit_pressure_from_early_wallets_on_the_tape():
    m = li.early_map(_early(6, same_slot=3))
    assert li.pressure({'sells': [('x', 500)]}, m) == ('NONE', None)               # a stranger selling is not early-wallet pressure
    assert li.pressure({'sells': [('w4', 80)]}, m)[0] == 'WATCH'
    assert li.pressure({'sells': [('w0', 80), ('w1', 90)]}, m)[0] == 'HIGH'
    assert li.pressure({'sells': [('C', 60)]}, m, creator='C')[0] == 'HIGH'
    assert li.pressure({'sells': [('w4', 80)]}, m, {'w4': 'FAST DUMPER'})[0] == 'HIGH'
    assert li.pressure({'sells': [('w4', 10)]}, m)[0] == 'NONE'                    # dust is not pressure


def test_fomo_phases():
    assert li.phase({'d5': -20})[0] == 'COLLAPSE'
    m = li.early_map(_early(5), {f'w{i}': 0 for i in range(5)})
    assert li.phase({'d5': 3, 'c1': 80, 'pace': 0.8, 'buy': 55}, m)[0] == 'DISTRIBUTION'
    assert li.phase({'d5': 12, 'c1': 120, 'pace': 2, 'buy': 60})[0] == 'CROWD FOMO'
    ph, healthy, _ = li.phase({'d5': 5, 'c1': 20, 'pace': 2, 'buy': 60, 'holdD': 30, 'liqD': 2})
    assert ph == 'ACCELERATING' and healthy is True
    ph, healthy, why = li.phase({'d5': 1, 'c1': 10, 'pace': 1.1, 'buy': 55, 'holdD': 5, 'liqD': -15})
    assert ph == 'EARLY FOMO' and healthy is False and 'pool weakening' in why
    assert li.phase({'d5': 0, 'pace': 0.3})[0] == 'PRE-FOMO'


def test_rank_band():
    assert li.rank_band(7) == ('FIRST 10', 'exact') and li.rank_band(None, 30) == ('FIRST 50', '≈ holders at entry')
    assert li.rank_band(None, 200)[0] == 'LATER' and li.rank_band() == (None, None)


def test_note_settle_memory_and_class_record():
    m = li.early_map(_early(3), {'w0': 2})
    st = li.note({}, 'M', m, 'BUNDLED', 1.0, 0, 0.2, 'C')
    st = li.note(st, 'M', {**m, 'nowPct': 1.0}, 'BUNDLED', 1.0, 200)
    assert len(st['open']['M']['hist']) == 2
    st = li.settle(st, lambda mt: None, 100)                          # not an hour yet
    assert 'M' in st['open']
    st = li.settle(st, lambda mt: 0.05, 4000)                         # −95% → a rug
    assert not st['open'] and st['done'][0]['res'] == -95.0 and st['mem']['w0']['rug'] == 1
    assert li.by_class(st['done'])['BUNDLED'] == {'n': 1, 'med': -95.0, 'up': 0, 'rug': 100}


def _row(li_):
    return {'mint': 'M', 'px': 1.0, 'nums': {'v5': 5000, 'pace': 1, 'liq': 50_000, 'd5': 1}, 'vitals': {'safe': True, 'mcap': 100_000, 'liq': 50_000, 'ageH': 1.0}, 'li': li_}


def test_ranking_never_buys_into_distribution_and_ranks_early_fomo_up():
    assert opp.hard_fail(_row({'phase': 'DISTRIBUTION', 'phaseWhy': ['early wallets selling']})).startswith('distribution')
    assert opp.hard_fail(_row({'press': 'HIGH', 'pressWhy': 'the creator sold $90'})).startswith('early wallets unloading')
    a = opp.score(_row({'phase': 'ACCELERATING', 'healthy': True}))[0]
    b = opp.score(_row({'phase': 'CROWD FOMO', 'healthy': False}))[0]
    assert a > b
    # a launch class is ranked by its OWN settled record only once it has 20 launches
    few = opp.score(_row({'cls': 'BUNDLED', 'clsRec': {'n': 5, 'med': -60}}))[0]
    many = opp.score(_row({'cls': 'BUNDLED', 'clsRec': {'n': 25, 'med': -60}}))[0]
    assert few == opp.score(_row({}))[0] and many < few


def test_warden_w20_shrinks_for_exit_risk_and_vetoes_on_live_unloading():
    w = office.warden(1.0, {'li': {'cls': 'INSIDER-LIKE CLUSTER', 'early': 30}}, floor=0.05)
    assert w['allowed'] <= 0.5 and any(r['id'] == 'W20 exit risk' for r in w['rules'])
    assert office.warden(1.0, {'li': {'press': 'HIGH', 'pressWhy': 'x'}}, floor=0.05)['veto']
    assert office.warden(1.0, {'li': {'cls': 'NORMAL'}}, floor=0.05)['allowed'] == office.warden(1.0, {}, floor=0.05)['allowed']   # a normal launch adds nothing
    assert not any(r['id'] == 'W20 exit risk' for r in office.warden(1.0, {'li': {'cls': 'NORMAL'}}, floor=0.05)['rules'])


def test_judge_names_the_launch_mistake_and_records_winner_shape():
    loss = {'mint': 'M', 'realPct': -20, 'path': [-1, -2], 'peak': 1, 'low': -20, 'rule': 'R5 stop', 'li': {'phase': 'CROWD FOMO'}}
    assert jr.review(loss)['cause'] == 'crowd_fomo'
    assert jr.review({**loss, 'li': {'press': 'WATCH'}})['cause'] == 'after_distribution'
    assert jr.review({**loss, 'li': {'cls': 'BUNDLED', 'early': 30}})['cause'] == 'bundled_exit'
    win = jr.review({'mint': 'W', 'realPct': 30, 'li': {'phase': 'ACCELERATING', 'rank': ['FIRST 25', 'exact'], 'cls': 'NORMAL', 'early': 12}})
    assert win['phase'] == 'ACCELERATING' and win['rank'] == 'FIRST 25' and 'buyer rank FIRST 25' in win['why']
    shape = jr.launch_shape([win, {**jr.review(loss), 'phase': 'CROWD FOMO'}])
    assert shape['phase']['ACCELERATING']['won'] == 100 and shape['phase']['CROWD FOMO']['won'] == 0


def test_early_buy_reads_a_buy_from_public_tx_balances():
    import reputation_service as rs
    tx = {'slot': 7, 'meta': {'preBalances': [2_000_000_000], 'postBalances': [1_500_000_000],
                              'preTokenBalances': [], 'postTokenBalances': [{'mint': 'M', 'owner': 'P', 'uiTokenAmount': {'uiAmount': 20_000_000}}]}}
    assert rs._early_buy(tx, 'P', 'M', 1_000_000_000) == {'w': 'P', 'slot': 7, 'sol': 0.5, 'pct': 2.0}
    sell = {**tx, 'meta': {**tx['meta'], 'preTokenBalances': [{'mint': 'M', 'owner': 'P', 'uiTokenAmount': {'uiAmount': 30_000_000}}]}}
    assert rs._early_buy(sell, 'P', 'M', 1_000_000_000) is None
