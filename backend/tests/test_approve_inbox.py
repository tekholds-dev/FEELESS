"""✅ AGX-10: a proof under 1x speaks in its agent's chat (what to fix first) and a redo waits in the Approve inbox. No model is ever called
until the owner taps Approve; a decline, a second tap, a stranger or the auto loop never runs it."""
import asyncio

import pytest

import approvals as ap

PARTS = [{'key': 'a', 'label': 'Sources', 'note': 'it named one source', 'weight': 40, 'value': 0.25}, {'key': 'b', 'label': 'Speed', 'note': '', 'weight': 20, 'value': 0.5}]


def test_biggest_lift_and_due_are_pure():
    assert ap.biggest_lift(PARTS)['label'] == 'Sources' and ap.biggest_lift(PARTS)['gain'] == 30
    assert ap.biggest_lift([{'weight': 10, 'value': 1}]) is None and ap.biggest_lift(None) is None
    rows = [('poc', {'id': 'a', 'status': 'closed', 'at': 50}, {'score': 40}),        # before `since`
            ('poc', {'id': 'b', 'status': 'closed', 'at': 120}, {'score': 140}),      # over 1x
            ('poc', {'id': 'c', 'status': 'open', 'at': 130}, {'score': 10}),         # not closed
            ('pos', {'id': 'd', 'status': 'closed', 'at': 140}, {'score': 72}),
            ('poc', {'id': 'e', 'status': 'closed', 'at': 130}, {'score': 99}),
            ('poc', {'id': 'f', 'status': 'closed', 'at': 135}, {'score': 5})]        # already alerted
    assert [f['id'] for _k, f, _v in ap.due(rows, 100, {'f'})] == ['e', 'd']


def test_redo_rows_only_for_work_it_can_rebuild_never_money():
    lift = ap.biggest_lift(PARTS)
    pos = ap.redo_item('pos', {'id': 'p1', 'n': 4, 'ws': 'w9', 'cost': 0.0123}, lift, ['openai/gpt-x', 'qwen/q3'], now=5)
    assert pos['op'] == {'op': 'ws_build', 'job': 'w9', 'text': pos['op']['text'], 'to': 'both'} and 'Sources' in pos['op']['text']
    assert pos['models'] == ['gpt-x', 'q3'] and pos['estUsd'] == 0.0123 and pos['state'] == 'waiting'
    for k in ('pow', 'pop', 'pob', 'poe'):
        assert ap.redo_item(k, {'id': 'x', 'ws': 'w'}, lift, ['m']) is None
    assert ap.redo_item('pos', {'id': 'x'}, lift, ['m']) is None   # no page to rebuild
    cat = {}
    assert ap.add(cat, pos) and ap.add(cat, {**pos, 'id': 'other'}) is None   # one waiting row per proof
    assert ap.decide(cat, pos['id'], False)['state'] == 'declined'
    with pytest.raises(ValueError):
        ap.decide(cat, pos['id'], True)   # decided once
    with pytest.raises(KeyError):
        ap.decide(cat, 'nope', True)


def _store(fs):
    cat = {'id': 'g', 'name': 'G', 'brainsCfg': {'brains': ['openai/a', 'qwen/b']}, 'chat': [],
           'psFolders': [{'id': 's1', 'n': 2, 'ws': 'w1', 'status': 'closed', 'at': 1000, 'cost': 0.02}],
           'powFolders': [{'id': 'w1', 'n': 1, 'status': 'closed', 'at': 1000}]}
    return {'cats': {'g': cat}}


def test_the_alert_spends_nothing_and_only_redoes_what_it_can(monkeypatch):
    import feecat_service as fs
    called = []

    async def think(*_a, **_k):
        called.append(1); return '', 0, ''
    monkeypatch.setattr(fs, '_think', think)
    monkeypatch.setattr(fs, '_proof_view', lambda c, k, f, top=300, w=None: {'score': 60, 'top': 300, 'rank': 'D', 'parts': PARTS})
    store = _store(fs); cat = store['cats']['g']; cat['potAlertSince'] = 0
    assert fs._pot_alert_pass(store, now=2000) == 2
    assert not called                                                        # writing the alert never calls a model
    says = [m['text'] for m in cat['chat']]
    assert any('PoStatic #2' in t and 'Fix first: Sources' in t and 'Approve' in t for t in says)
    assert any('PoW #1' in t and 'Approve' not in t for t in says)           # a trade is never re-run by an agent
    assert [r['proof']['id'] for r in cat['approvals']] == ['s1'] and cat['approvals'][0]['state'] == 'waiting'
    assert fs._pot_alert_pass(store, now=2100) == 0                          # once per proof


def test_first_sight_speaks_only_for_the_newest(monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, '_proof_view', lambda c, k, f, top=300, w=None: {'score': 10, 'top': 300, 'parts': PARTS})
    store = _store(fs)
    assert fs._pot_alert_pass(store, now=1500) == 1 and len(store['cats']['g']['potAlerted']) == 2


def test_only_the_owners_approve_tap_runs_it(monkeypatch):
    from test_agent_owner_lock import _client, _general
    cat = {**_general('WALLET_ME'), 'approvals': []}
    fs, store, c = _client(monkeypatch, {'g': cat})
    ran = []
    real = fs._cat_work

    async def spy(cat_id, p):
        if p.op in ('ws_build', 'poc'):
            ran.append((p.op, p.job, p.to)); return {'ok': True}
        return await real(cat_id, p)
    monkeypatch.setattr(fs, '_cat_work', spy)
    row = ap.redo_item('pos', {'id': 's1', 'n': 2, 'ws': 'w1'}, ap.biggest_lift(PARTS), ['a/b'], now=1)
    store['cats']['g']['approvals'] = [row]; fs._save(store)
    post = lambda body, sess='tok-me': c.post('/api/cats/g/work', json={'ownerId': 'browser-1', 'session': sess, **body})
    assert post({'op': 'approvals'}).json()['approvals'][0]['state'] == 'waiting' and not ran
    assert post({'op': 'approve', 'text': row['id'], 'job': 'yes'}, 'tok-them').status_code == 403 and not ran   # a stranger
    assert post({'op': 'approve', 'text': row['id'], 'job': 'yes'}, fs._AUTO_TOKEN).status_code == 403 and not ran   # the auto loop
    r = post({'op': 'approve', 'text': row['id'], 'job': 'yes'})
    assert r.status_code == 200 and ran == [('ws_build', 'w1', 'both')] and r.json()['row']['state'] == 'ran'
    assert post({'op': 'approve', 'text': row['id'], 'job': 'yes'}).status_code == 409 and len(ran) == 1   # never twice


def test_a_decline_runs_nothing(monkeypatch):
    from test_agent_owner_lock import _client, _general
    fs, store, c = _client(monkeypatch, {'g': {**_general('WALLET_ME')}})
    row = ap.redo_item('poc', {'id': 'c1', 'n': 1, 'topic': 'memes'}, ap.biggest_lift(PARTS), ['a/b'], now=1)
    store['cats']['g']['approvals'] = [row]; fs._save(store)
    started = []
    monkeypatch.setattr(fs, '_poc_file', lambda *a: started.append(a) or asyncio.sleep(0))
    r = c.post('/api/cats/g/work', json={'ownerId': 'browser-1', 'session': 'tok-me', 'op': 'approve', 'text': row['id'], 'job': 'no'})
    assert r.status_code == 200 and r.json()['row']['state'] == 'declined' and not started


def test_a_zero_recorded_cost_is_not_known_never_free():
    assert ap.redo_item('poc', {'id': 'c', 'cost': 0}, ap.biggest_lift(PARTS), ['m'])['estUsd'] is None
