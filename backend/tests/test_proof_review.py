"""OSSY and G4 review every filed proof: a verdict each, who really answered, filed on the folder and in the history; never the boost grade."""
import asyncio
import json

import proof_review as pr


def test_verdicts_parse_strictly_and_combine():
    v = pr.verdict_of('<think>hmm</think> ```json\n{"score": 82.4, "verdict": "PASS", "checks": ["sources real"], "why": "solid"}\n```')
    assert v == {'score': 82, 'verdict': 'pass', 'checks': ['sources real'], 'why': 'solid'}
    assert pr.verdict_of('no json') is None and pr.verdict_of('{"verdict": "pass"}') is None and pr.verdict_of('{"score": 40}')['verdict'] == 'fail'
    c = pr.combine({'ossy': {'score': 80, 'verdict': 'pass'}, 'g4': {'score': 50, 'verdict': 'fail'}})
    assert (c['score'], c['verdict'], c['agree']) == (65, 'fail', False)
    assert pr.combine({'ossy': None, 'g4': {'score': 70, 'verdict': 'pass'}})['missing'] == ['ossy']


def test_next_due_takes_the_newest_unreviewed_closed_proof():
    store = {'cats': {'a': {'pobFolders': [{'id': 'old', 'status': 'closed', 'closedAt': 1}, {'id': 'new', 'status': 'closed', 'closedAt': 9}, {'id': 'nt', 'status': 'closed', 'closedAt': 20, 'noTrade': True}]},
                      'b': {'psFolders': [{'id': 'done', 'status': 'closed', 'closedAt': 30, 'review': {}}, {'id': 'open', 'status': 'live', 'closedAt': 40}]}}}
    assert pr.next_due(store)[2]['id'] == 'new' and pr.next_due(store, {('a', 'new')})[2]['id'] == 'old'
    assert 'wallet' not in pr.brief('pob', {'id': 'x', 'ownerWallet': 'wallet', 'sites': ['espn.com'], 'why': 'w'})


def test_a_review_is_filed_with_who_answered(monkeypatch):
    import feecat_service as fs
    asked = []
    async def think(cat, model, messages, own_key=None, effort=None, max_tokens=None):
        asked.append(model)
        return json.dumps({'score': 70 if 'ossy' in model else 50, 'verdict': 'pass' if 'ossy' in model else 'fail', 'checks': ['c'], 'why': 'w'}), 0.0, 'openrouter'
    monkeypatch.setattr(fs, '_think', think)
    store = {'cats': {'s': {'id': 's', 'handle': 'sicarios', 'pobFolders': [{'id': 'b1', 'status': 'closed', 'closedAt': 5, 'sites': ['espn.com']}]}}}
    fs._REVIEWED.clear(); fs._REVIEW_DONE.clear()
    rv = asyncio.run(fs._review_one(store))
    assert asked == ['local/ossy', 'local/g4'] and (rv['score'], rv['verdict'], rv['agree']) == (60, 'fail', False)
    assert fs._review_apply(store) == 1 and store['cats']['s']['pobFolders'][0]['review']['by']['ossy']['score'] == 70
    assert asyncio.run(fs._review_one(store)) is None   # reviewed once
