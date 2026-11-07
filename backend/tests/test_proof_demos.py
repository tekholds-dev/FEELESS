import json

import proof_demos as pd

VIEW = {'rank': 'B', 'score': 200, 'top': 300, 'frac': .66, 'parts': [{'label': 'Result', 'value': 1, 'weight': 40, 'note': 'x'}], 'kind': 'PoW'}


def test_a_card_only_carries_what_is_named():
    f = {'id': 'pow1', 'status': 'closed', 'sym': 'WIF', 'pnlPct': -11, 'real': True, 'why': 'OSSY: stop', 'mint': 'MINTSECRET', 'pair': 'PAIRSECRET', 'owner': 'NOTESECRET', 'talk': ['PROMPTSECRET'], 'shots': [1, 2], 'boughtAt': 100, 'soldAt': 700}
    c = pd.card('PoW', 'cat1', f, VIEW, 'PoW #1', lambda s: s.replace('OSSY', 'AI'))
    blob = json.dumps(c)
    assert 'SECRET' not in blob and 'cat1' not in blob and 'OSSY' not in blob
    assert c['title'] == '$WIF' and c['tone'] == 'bad' and c['said'] == '-11.0%' and ['Held', '10 min'] in c['facts'] and ['Money', 'Real'] in c['facts'] and not c['page']


def test_verdicts_come_from_the_record_never_a_default_win():
    assert pd.verdict('PoW', {'status': 'closed'}) == ('open', 'No fill')
    assert pd.verdict('PoP', {'noTrade': True})[0] == 'open'
    assert pd.verdict('PoB', {'graded': 'right'})[0] == 'good' and pd.verdict('PoB', {'graded': 'wrong'})[0] == 'bad' and pd.verdict('PoC', {})[0] == 'open'


def test_it_picks_the_best_and_a_real_failure_and_nothing_unfiled():
    v = lambda fr: {**VIEW, 'frac': fr, 'kind': 'PoB'}
    rows = [({'id': 'a', 'status': 'closed', 'graded': 'right'}, v(.8)), ({'id': 'b', 'status': 'closed', 'graded': 'wrong'}, v(.3)), ({'id': 'c', 'status': 'open', 'graded': 'right'}, v(.99)), ({'id': 'd', 'status': 'closed'}, v(.5))]
    assert [f['id'] for f, _ in pd.pick(rows)] == ['a', 'b']
    assert [f['id'] for f, _ in pd.pick(rows[3:])] == ['d'] and pd.pick([rows[2]]) == [] and pd.pick([]) == []


def test_an_owner_sees_only_their_own_agents_proofs(monkeypatch, tmp_path):
    import pytest
    fs = pytest.importorskip('feecat_service')
    f = lambda i: {'id': i, 'at': 5, 'status': 'closed', 'topic': i, 'graded': 'right'}
    store = {'cats': {'mine1': {'id': 'mine1', 'ownerWallet': 'W1', 'pobFolders': [f('m1')]}, 'mine2': {'id': 'mine2', 'ownerWallet': 'W1', 'pobFolders': [f('m2')]}, 'theirs': {'id': 'theirs', 'ownerWallet': 'W2', 'ownerStaff': True, 'pobFolders': [f('t1')], 'psFolders': [{**f('t2'), 'ws': 'wx'}]}}}
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); fs._DEMOS.clear()
    got = fs._demo_gallery(store, store['cats']['mine1']); blob = json.dumps(got['kinds'])
    assert 't1' not in blob and 'm1' in blob and not got['links']
    assert 't1' in json.dumps(fs._demo_gallery(store, store['cats']['theirs'])['kinds'])
