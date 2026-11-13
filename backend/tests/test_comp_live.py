"""📡 COMP-1: the COMP live frame is built only from what COMP measured (None when nothing did) and is sent only when a number moved."""
import comp_live as cl


def _st(running=True, last=40):
    return {'run': {'running': running, 'iters': 200, 'curve': {'train': [[10, 3.1], [last, 1.4]], 'val': [[last, 1.9]], 'last': last}},
            'exam': {'n': 28, 'examinees': [{'id': 'baseline', 'name': 'Always "lost"', 'score': {'acc': 0.54}},
                                             {'id': 'comp', 'name': 'COMP v2', 'score': {'acc': 0.61}}, {'id': 'gpt', 'blocked': 'no key'}]},
            'examRunning': False, 'dataset': {'won': 75, 'lost': 67}, 'market': {'rows': 12, 'open': 3, 'won': 5, 'lost': 4, 'collects': 9, 'junk': 1}}


def test_frame_reads_real_numbers_only():
    fr = cl.frame(_st(), {'id': 'j1', 'status': 'training', 'step': 120, 'steps': 400, 'loss': 2.2, 'tps': 9100, 'history': [[100, 2.4], [120, 2.2]]},
                  {'rows': 144, 'pairs': 48, 'kinds': [{'kind': 'PoW', 'rows': 38, 'won': 9, 'lost': 20}]}, 1000.04)
    c2 = fr['comp2']
    assert fr['live'] is True and c2['iter'] == 40 and c2['loss'] == 1.4 and c2['val'] == 1.9
    assert c2['examAnswered'] == 2 and c2['examTotal'] == 3 and c2['best']['id'] == 'comp' and c2['compAcc'] == 0.61 and c2['baseAcc'] is None
    assert c2['market'] == {'rows': 12, 'open': 3, 'won': 5, 'lost': 4, 'collects': 9, 'at': None, 'nextSettle': None}
    assert fr['forge']['live'] and fr['forge']['tps'] == 9100 and fr['data']['rows'] == 144 and fr['data']['kinds'][0]['lost'] == 20


def test_idle_and_empty_never_invent():
    fr = cl.frame({}, None, None, 5)
    assert fr['live'] is False and fr['forge'] is None and fr['comp2']['loss'] is None and fr['comp2']['best'] is None and fr['data']['rows'] is None


def test_changed_ignores_the_clock():
    a = cl.frame(_st(running=False), None, None, 1); b = cl.frame(_st(running=False), None, None, 2)
    assert not cl.changed(a, b)
    assert cl.changed(a, cl.frame(_st(running=False, last=41), None, None, 3)) and cl.changed(None, a)
