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
                      'b': {'psFolders': [{'id': 'done', 'status': 'closed', 'closedAt': 30, 'review': {'v': pr.VERSION}}, {'id': 'open', 'status': 'live', 'closedAt': 40}]}}}
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


def test_failed_reviews_become_the_next_proofs_lessons():
    """COL-10: what OSSY and G4 failed lately in a kind reaches the next proof of that kind; passes and other kinds do not."""
    fail = lambda why, at: {'id': f'p{at}', 'status': 'closed', 'closedAt': at, 'review': {'verdict': 'fail', 'by': {'ossy': {'verdict': 'fail', 'why': why, 'checks': []}}}}
    store = {'cats': {'a': {'pobFolders': [fail('odds were made up', 1), fail('no real sources', 3), fail('No real sources', 2),
                                          {'id': 'ok', 'status': 'closed', 'closedAt': 9, 'review': {'verdict': 'pass', 'by': {'g4': {'verdict': 'pass', 'why': 'fine'}}}}]},
                      'b': {'powFolders': [fail('rug ignored', 5)]}}}
    assert pr.lessons(store, 'pob') == ['no real sources', 'odds were made up']
    assert 'no real sources' in pr.lessons_line(pr.lessons(store, 'pob')) and pr.lessons_line([]) == ''


def test_kit_reliability_shows_review_rates_but_never_quarantines_on_them():
    import method_kits as mk
    fs = {('pob', str(i)): {'id': str(i), 'sitesRead': ['x'] if i % 2 else [], 'review': {'verdict': 'pass' if i % 2 else 'fail'}} for i in range(30)}
    env = [{'kind': 'pob', 'id': str(i), 'outcome': {}} for i in range(30)]
    row = mk.reliability(env, fs)['read-the-record-first']
    assert row['followedReview'] == 1.0 and row['skippedReview'] == 0.0 and row['state'] == 'unmeasured'


def test_the_test_bench_reviews_only_sicarios():
    """Owner 2026-11-10: OSSY and G4 test on Sicario's proofs; his own agent waits until all is confirmed."""
    f = lambda at: {'id': f'p{at}', 'status': 'closed', 'closedAt': at}
    store = {'cats': {'h': {'handle': 'happy-assistant', 'psFolders': [f(9)]}, 's': {'handle': 'sicarios', 'powFolders': [f(1)]}}}
    assert pr.next_due(store)[0] == 'h' and pr.next_due(store, handles=('sicarios',))[0] == 's'


def test_v2_brief_carries_the_kinds_evidence_and_today():
    """A trade is judged on its own prices and times; books never get the 4-source rule; an old-version review is due again."""
    f = {'id': 'w', 'status': 'closed', 'sym': 'LEEROY', 'entry': 1e-6, 'exit': 9e-7, 'boughtAt': 1793897298, 'soldAt': 1793897559, 'closedAt': 1793897559,
         'coins': [{'sym': 'LEEROY', 'liq': 6e4, 'read': 'FEELESS coin search ...'}], 'whys': {'0': 'only riser'}}
    raw = pr.brief('pow', f, now=1794336000); assert raw.startswith('TODAY IS 2026-11-10.')
    b = json.loads(raw.split('\n', 1)[1])
    assert b['today'].startswith('2026-11-10') and b['evidence']['entryPriceInSol'] == 1e-6 and b['evidence']['sold'].startswith('2026-11-05')
    assert b['compareRule'] == 'filed before the 4-source rule existed' and b['evidence']['whatWasRead']
    assert 'compareRule' not in json.loads(pr.brief('poe', {'status': 'closed', 'income': 1, 'costs': 1, 'net': 0}).split('\n', 1)[1])
    big = pr.brief('pow', {**f, 'coins': [{'sym': 'X', 'read': 'r' * 5000}] * 2, 'plan': 'p' * 3000}, now=1794336000)
    json.loads(big.split('\n', 1)[1])   # too long → whole parts dropped, still valid JSON
    old = {'cats': {'s': {'powFolders': [{**f, 'review': {'v': 1}}]}}}
    assert pr.next_due(old)[2]['id'] == 'w' and pr.next_due({'cats': {'s': {'powFolders': [{**f, 'review': {'v': pr.VERSION}}]}}}) is None


def test_v3_score_is_counted_from_the_five_checks_never_the_models_number():
    raw = '{"score": 0, "checks": [{"pass": true, "found": "a"}, {"pass": true, "found": "b"}, {"pass": true, "found": "c"}, {"pass": false, "found": "d"}, {"pass": true, "found": "e"}], "why": "w"}'
    v = pr.verdict_of(raw)
    assert v['score'] == 80 and v['verdict'] == 'pass' and v['checks'][3] == '✗ d' and v['checks'][0] == '✓ a'
    assert pr.verdict_of('{"checks": [{"pass": false, "found": "x"}]}')['verdict'] == 'fail'
