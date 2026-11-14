"""⚔ AGX-4 (owner 2026-11-14): both minds answer one ask; the owner taps the better one → a right-vs-wrong pair in COMP's dataset."""
import json

import model_lab as _ml
from test_play_studio import _server


def _two_minds(store, tid='t1'):
    store['cats']['g']['jobs'] = [{'id': tid, 'at': 100, 'request': 'Is $BONK worth a buy? mail me at a@b.co', 'status': 'done', 'answer': 'skip',
                                   'minds': [{'model': 'or/m-a', 'answer': 'Buy: liquidity 2x up'}, {'model': 'local/m-b', 'answer': 'Skip: dev sold 40%'}]}]


def test_a_tapped_winner_lands_as_a_pair_in_the_dataset_once(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    monkeypatch.setattr(fs, 'STASH_DIR', tmp_path / 'stash')
    _two_minds(store)
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': 'duel', **kw})
    j = post(text='t1', job='1')
    assert j.status_code == 200, j.text
    assert j.json() == {'duels': {'t1': 1}, 'stashed': True}
    assert post(text='t1', job='0').json() == {'duels': {'t1': 1}, 'stashed': False}   # a pick is final
    items = fs._stash.catalog(tmp_path / 'stash')
    assert [i['category'] for i in items] == ['Duels']
    view = _ml.summary(items, [], {})
    assert view['duels'] == 1 and view['pairs'] == 1 and view['steps']['pref'] == 'have'
    rows = [json.loads(x) for x in _ml.export_lines(items, lambda k: fs._stash.read(tmp_path / 'stash', k), {})]
    assert rows[0]['kind'] == 'Duel' and rows[0]['chosen'] == 'Skip: dev sold 40%' and rows[0]['rejected'] == 'Buy: liquidity 2x up'
    assert rows[0]['chosenModel'] == 'm-b' and '[email]' in rows[0]['prompt']


def test_a_duel_needs_two_answers_and_a_or_b(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    monkeypatch.setattr(fs, 'STASH_DIR', tmp_path / 'stash')
    _two_minds(store)
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': 'duel', **kw})
    assert post(text='t1', job='2').status_code == 400
    assert post(text='nope', job='0').status_code == 400
    store['cats']['g']['jobs'][0]['minds'][1]['answer'] = ''
    assert post(text='t1', job='0').status_code == 400
    assert not (tmp_path / 'stash').exists() or not fs._stash.catalog(tmp_path / 'stash')
