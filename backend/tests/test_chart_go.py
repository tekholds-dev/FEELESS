"""🎯 a real seat needs the chart's own ENTER NOW; a missed price read is not a rug."""
import paper_desk as pd
import trench_brain as tb
from trench_kernel import brain as b


def _ms(call=None, nar_row=None):
    row = {'chart': {'entry': [call, 'E2 no chasing', 'x']} if call else None, **(nar_row or {})}
    return {'row': row, 'market': {'move5m': 2.0, 'flow': {}}, 'identity': {'ageH': 2.0}, 'chain': {'holderStatus': 'READY', 'earlyWallets': 'NEUTRAL'},
            'research': {'status': 'READY'}}


def test_wait_chart_turns_enter_into_wait(monkeypatch):
    monkeypatch.setattr(b._opp, 'narrative', lambda row: ('BREAKOUT', 'breaking out'))
    t = b.trigger(_ms('WAIT FOR PULLBACK'))
    assert t['state'] == 'WAIT' and t['chartWait'] and 'waits for ENTER NOW' in t['why']
    assert b.trigger(_ms('ENTER NOW'))['state'] == 'ENTER'
    assert b.trigger(_ms('WAIT FOR PULLBACK'), waits={'chartWait': False})['state'] == 'ENTER'   # switched off (owner / regret ledger)


def test_no_chart_is_half_a_seat():
    ms = _ms(None)
    w = b.warden(ms, {'hard': False, 'objections': []}, {'unknown': []})
    assert w['size'] == b.NO_CHART_SIZE and 'no chart' in w['why']


def test_a_missed_read_settles_at_the_last_move_not_minus_100():
    st = {'open': {'M': {'px': 1.0, 'at': 0.0, 'kind': 'wait'}}}
    st = pd.settle(st, lambda m: 1.2, 50 * 60)              # priced at minute 50
    st = pd.settle(st, lambda m: None, 61 * 60)             # missed at the hour
    assert st['done'][-1]['p60'] == 20.0
    st2 = pd.settle({'open': {'M': {'px': 1.0, 'at': 0.0}}}, lambda m: None, 61 * 60)   # never priced again = vanished
    assert st2['done'][-1]['p60'] == -100.0


def test_brain_gone_only_after_no_price_for_15_min():
    st = {'open': {'M': {'px': 1.0, 'at': 0.0, 'f': [], 'hi': 0, 'lo': 0, 'last': 5.0, 'seen': 3500.0, 'x': {}}}}
    d = tb.track(st, [], lambda m: None, 3601.0)['done'][-1]
    assert d['gone'] is False and d['end'] == 5.0
    st['open']['M']['seen'] = 100.0
    assert tb.track(st, [], lambda m: None, 3601.0)['done'][-1]['gone'] is True
