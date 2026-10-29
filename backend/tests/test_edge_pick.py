"""🧪 A06 THE PICK: a coin on the one intake that matches a proven edge rule, survived its own 1 / 5-minute watch and sits on its germ is
READY on its own — and every wall (hard wall, sellers, the gun line, already ran, washed, the owner's switch, no proven rule) still stops it."""
import trench_kernel.kernel as tk
from trench_kernel import brain, universe as uni
from kernel_helpers import row

RULE = {'rule': ['5m:5..15', 'buy:65+'], 'n': 62, 'med': 21.5, 'avg': 20.2}
CHART = {'germDist': 5.0, 'entry': ['WAIT FOR CONFIRMATION', 'E5', '']}
SURV = {'t0': 0.0, 'p0': 1.0, 'min': 0.95, 'max': 1.1, 'last': 1.05, 'lastAt': 1000.0, 'm1': 2.0, 'ok1': True, 'm5': 6.0, 'ok5': True}


def _ctx(**k):
    return {'edgeRules': [RULE], 'feats': {'M': ['5m:5..15', 'buy:65+', 'age:<15m']}, 'surv': {'M': dict(SURV)}, 'now': 1000.0, **k}


def _judge(r=None, **k):
    uni.set_band({})
    kk = tk.Kernel()
    kk.run([r or row('M', d5=1.0, buy=50, pace=0.8, chart=CHART)], 1000.0, _ctx(**k))
    return kk.dec['M'], kk


def test_a_proven_rule_on_a_confirmed_coin_at_its_germ_is_picked_ready_on_its_own():
    off, _ = _judge(edgeRules=[])
    assert off['status'] != 'READY' and 'pick' not in off            # not READY on its own rank / timing
    d, kk = _judge()
    assert d['status'] == 'READY' and d['pick']['rule'] == '5m:5..15 + buy:65+'
    assert 'germ floor' in d['why'] and '21.5% typical on 62 unseen coins' in d['why'] and 'survived 1m +2% · 5m +6%' in d['why']
    assert kk.candidate('M')['pick'] == '5m:5..15 + buy:65+' and kk.case('M')['checks'][-1][0] == 'pick'
    assert [m for m, _d in kk.ready()] == ['M']


def test_no_pick_without_its_own_survival_or_on_a_washed_or_bleeding_coin():
    for s in ({}, {**SURV, 'ok5': None, 'm5': None}, {**SURV, 'ok1': False}, {**SURV, 'm5': -25.0}, {**SURV, 'ok15': False, 'm15': -60.0}, {**SURV, 'last': 0.6}):
        d, _ = _judge(surv={'M': s} if s else {})
        assert d['status'] != 'READY', s


def test_no_pick_off_the_germ_into_sellers_after_a_run_or_when_the_owner_switches_it_off():
    far = row('M', d5=1.0, buy=50, pace=0.8, chart={**CHART, 'germDist': 40.0})
    assert _judge(far)[0]['status'] != 'READY'
    skip = row('M', d5=1.0, buy=50, pace=0.8, chart={**CHART, 'entry': ['SKIP', 'E9', '']})
    assert _judge(skip)[0]['status'] != 'READY'
    assert _judge(feats={'M': ['5m:5..15', 'buy:65+', '1h:200+']})[0]['status'] != 'READY'
    assert _judge(edgePick=False)[0]['status'] != 'READY'
    sellers = row('M', d5=1.0, buy=50, pace=0.8, chart=CHART)
    ms = {'identity': {'mint': 'M'}, 'row': sellers}
    assert brain.edge_pick(ms, _ctx(), {'flow': 'SELLERS', 'chart': 'WAIT FOR CONFIRMATION'}, {'objections': []}) is None
    assert brain.edge_pick(ms, _ctx(), {'flow': None, 'chart': 'WAIT FOR CONFIRMATION'}, {'objections': [('ran', 'WARNING', '+180%')]}) is None


def test_the_hard_wall_the_courier_and_the_review_only_list_still_stop_a_pick():
    assert _judge(row('M', d5=1.0, buy=50, pace=0.8, liq=500, chart=CHART))[0]['status'] == 'TRACKING'   # a pool the keeper cannot exit
    assert _judge(courier='BAD')[0]['status'] != 'READY'
    d, _ = _judge(watchOnly={'M'})
    assert d['status'] == 'CONTENDING' and d.get('wouldBeReady')


def test_a_sensed_row_tags_the_same_as_the_board_row_the_audit_learned_on():
    import trench_brain as tb
    from trench_kernel import senses as sn
    board = {'mint': 'M', 'symbol': 'M', 'pairAddress': 'P', 'price': 1.0, 'ageH': 0.1, 'mcap': 25_000, 'liq': 12_000, 'vol1h': 9_000, 'vol5m': 1_500,
             'chg5m': 8.0, 'chg1h': 30.0, 'buyShare': 70, 'top10': 20, 'bundledN': 0, 'snipersN': 0, 'txns1h': 200}
    _st, table, _c = sn.sense({}, [board], 1000.0)
    got = set(tb.feats(sn.audit_row(table[0])))
    assert set(tb.feats(board)) <= got and {'5m:5..15', 'buy:65+', '1h:0..50', 'age:<15m', 'bund:0', 'xl:<1'} <= got
    assert len(tb.feats(table[0])) < len(got)   # the nested row on its own tags almost nothing (the bug this fixed)


def test_the_ai_seat_reads_the_research_and_the_pick_comes_first():
    import ai_seat as seat
    assert seat.research([{**RULE, 'up': 58}]) == ['5m:5..15 + buy:65+: +21.5% typical, 58% up, n 62'] and seat.research([]) == []
    ready = {'symbol': 'A', 'status': 'READY', 'trigger': 'ENTER'}
    pick = {'symbol': 'B', 'status': 'READY', 'trigger': 'WAIT', 'pick': '5m:5..15 + buy:65+'}
    assert seat.agents_pick([ready, pick])['symbol'] == 'B' and seat.agents_pick([ready])['symbol'] == 'A'
    assert seat.cand_row({'mint': 'B', 'symbol': 'B', 'pick': '5m:5..15 + buy:65+'})['pick'] == '5m:5..15 + buy:65+'
    pk = seat.packet([seat.cand_row(pick)], None, proven=seat.research([RULE]))
    assert pk['RESEARCH'][0].startswith('5m:5..15 + buy:65+') and 'RESEARCH' not in seat.packet([], None)
    assert 'RESEARCH' in seat.SYSTEM and '"pick"' in seat.SYSTEM


def test_n04_a_pick_must_have_been_young_when_first_seen_and_only_the_owners_switch_lets_it_past_the_youngest_coin_line():
    old = row('M', age=0.5, d5=1.0, buy=50, pace=0.8, chart=CHART)            # 30 min old, watched ~16.7 min → first seen at ~13 min: young enough
    assert _judge(old)[0]['status'] == 'READY'
    older = row('M', age=1.0, d5=1.0, buy=50, pace=0.8, chart=CHART)          # first seen at ~43 min: the losing side of the audit
    assert _judge(older)[0]['status'] != 'READY'
    uni.set_band({'agentMinAgeH': 0.25})                                      # the owner's 15-min youngest-coin line
    kk = tk.Kernel(); kk.run([row('M', d5=1.0, buy=50, pace=0.8, chart=CHART)], 1000.0, _ctx()); d = kk.dec['M']
    assert d['status'] == 'TRACKING' and 'youngest-coin line' in d['why'] and 'pick' not in d   # switch off: the line stands
    kk = tk.Kernel(); kk.run([row('M', d5=1.0, buy=50, pace=0.8, chart=CHART)], 1000.0, _ctx(pickYoung=True)); d = kk.dec['M']
    assert d['status'] == 'READY' and d['pick'] and d['opinions']['warden']['size'] <= 0.5 and 'young pick' in d['opinions']['warden']['why']
    kk = tk.Kernel(); kk.run([row('M', d5=1.0, buy=50, pace=0.8, liq=500, chart=CHART)], 1000.0, _ctx(pickYoung=True))
    assert kk.dec['M']['status'] == 'TRACKING'                               # every OTHER wall rule still stands (a pool the keeper cannot exit)
    kk = tk.Kernel(); kk.run([row('M', d5=1.0, buy=50, pace=0.8, chart=CHART)], 1000.0, _ctx(pickYoung=True, surv={'M': {**SURV, 't0': 800.0}}))
    assert kk.dec['M']['status'] == 'TRACKING'                               # watched under 5 min: no pass
    uni.set_band({})
