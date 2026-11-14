"""AGT-12: the Engine folder's numbers come from the real call log and store, counts only."""
import json

import engine_view as ev


def test_routes_reviewer_reads_methods():
    now = 10_000
    lines = [json.dumps({'at': now - 60, 'route': 'local', 'ok': True, 'usd': 0, 'ms': 2000, 'ref': 'review:a', 'asked': 'local/ossy', 'model': 'q9'}).replace(': ', ':').replace(', ', ','),
             json.dumps({'at': now - 30, 'route': 'lan', 'ok': False, 'usd': 0, 'ms': 4000}), json.dumps({'at': now - 9999, 'route': 'singit', 'ok': True, 'usd': 1})]
    r = ev.routes(lines, now)
    assert [x['route'] for x in r] == ['local', 'lan'] and r[1]['okPct'] == 0 and r[0]['avgMs'] == 2000
    cats = [{'handle': 'sicarios', 'powFolders': [{'status': 'closed', 'review': {'v': 4, 'verdict': 'pass', 'at': 5}}, {'status': 'closed'}, {'status': 'closed', 'noTrade': True}]},
            {'handle': 'happy', 'psFolders': [{'status': 'closed'}]}]
    rv = ev.reviewer(cats, 4, lines, 90, ('sicarios',))
    assert (rv['graded'], rv['waiting'], rv['passPct']) == (1, 1, 100) and rv['answered'][0]['who'] == 'OSSY · local · q9'
    rd = ev.reads({'pob': (now - 60, 'x', ['a', 'b'], 3), 'pow': (now - 9999, 'x', [], 1)}, {'nba': {'at': now - 10, 'reused': 2}}, {'pob': 1800, 'pow': 300}, now)
    assert rd['kinds'] == [{'kind': 'pob', 'ageMin': 1, 'freshMin': 30, 'reused': 3, 'sites': 2}] and rd['topicReuses'] == 2
    assert ev.methods({'a': {'kit': 'a', 'state': 'active'}, 'b': {'kit': 'b', 'state': 'quarantined'}})['quarantined'] == 1


def test_agt9_a_proofs_research_job_is_filed_in_jobs_with_its_kind():
    import feecat_service as fs
    j = fs._job_tree({'id': 't1', 'text': 'read espn', 'proofKind': 'pob', 'windows': [{'goal': 'read', 'model': 'x/a', 'answer': 'Knicks'}]})
    assert j['proof'] == 'pob' and j['minds'][0]['answer'] == 'Knicks'
    assert fs._job_tree({'id': 't2', 'pow': {'sym': 'X'}})['proof'] == 'pow' and fs._job_tree({'id': 't3', 'text': 'hi'})['proof'] is None
    src = open(fs.__file__).read()
    assert "if not t.get('pow') and not t.get('proofRead'):   # 🗂" not in src   # proofs' jobs are no longer dropped


def test_col10_reviews_propose_kits_the_owner_approves_and_their_state_history_is_kept(tmp_path):
    import method_kits as mk
    import proof_review as pr
    rv = lambda fail: {'review': {'by': {'ossy': {'checks': ['✓ a', '✗ b' if fail else '✓ b', '✓ c', '✓ d', '✓ e']}}}}
    cats = [{'powFolders': [{'id': str(i), **rv(i < 4)} for i in range(5)]}]
    rows = mk.proposals(cats, pr.RUBRIC)
    assert [r['id'] for r in rows] == ['fix-pow-2'] and rows[0]['failRate'] == 0.8 and 'reason' in rows[0]['what']
    ex = mk.approve(tmp_path, rows[0]); kit = mk.all_kits(ex)['fix-pow-2']
    assert kit['permissions'] == ('read',) and kit['kinds'] == ('pow',) and kit['check']('pow', {**rv(False)}) and not kit['check']('pow', rv(True))
    assert mk.proposals(cats, pr.RUBRIC, ex) == []                       # approved once, never proposed again
    assert 'fix-pow-2' in mk.active_line('pow', {}, ex) and 'fix-pow-2' not in mk.active_line('pob', {}, ex)
    moved = mk.log_changes(tmp_path, {'a': {'state': 'unmeasured'}}, {'a': {'state': 'quarantined'}})
    assert moved and mk.history(tmp_path)[0] == {**moved[0]}
    assert mk.log_changes(tmp_path, {}, {'a': {'state': 'quarantined'}, 'b': {'state': 'unmeasured'}}) == []   # after a restart: nothing moved, nothing logged


def test_col24_asks_no_proof_covers_become_proposed_proof_types():
    import proof_gaps as pg
    jobs = [{'request': 'Research https://crawlnet.network give me a summary'}] * 3 + [{'request': 'buy this coin'}] * 5 + [{'request': 'summary of x', 'proof': 'pob'}] * 9
    rows = pg.gaps([{'jobs': jobs}])
    assert rows == [{'name': 'Proof of Summary', 'word': 'summary', 'asks': 3, 'examples': [jobs[0]['request']] * 3}]


def test_the_trader_chat_knows_what_feeless_proofs_are():
    """2026-11-10: asked what PoStatic is, G4 made up a staking answer and OSSY did not know: the chat prompt carried no FEELESS facts."""
    import feecat_service as fs
    sys_ = fs.TALK_SYS.format(name='OSSY', cat='x', calls='none', where=fs._know.WHERE)
    for word in ('PoStatic = Proof of Static', 'PoEco = Proof of Eco', 'PoB = Proof of Bids', 'Proofing = filing a proof', 'never guess'):
        assert word in sys_
    assert len(sys_) < 1800 and fs._know.asks_about('whats a PoEco')     # short enough for a small local model


def test_a_proposal_opens_to_its_evidence_full_check_counts_and_what_the_reviewers_said():
    """owner 2026-11-14: "cant open these to see, review and approve" — each proposal carries the proofs that failed it, newest first."""
    import method_kits as mk
    import proof_review as pr
    rv = lambda fail, n: {'n': n, 'topic': f'proof {n}', 'at': n, 'review': {'by': {'ossy': {'checks': ['✓ a', f'✗ no source for pick {n}' if fail else '✓ b', '✓ c', '✓ d', '✓ e']}, 'g4': {'checks': ['✓ a', '✓ b']}}}}
    cats = [{'name': 'Happy', 'powFolders': [{'id': str(i), **rv(i < 4, i)} for i in range(5)]}]
    r = mk.proposals(cats, pr.RUBRIC)[0]
    assert r['failed'] == 4 and r['seen'] == 5 and r['full'] == pr.RUBRIC['pow'][1]
    assert [e['n'] for e in r['examples']] == [3, 2, 1]                        # newest three
    assert r['examples'][0] == {'agent': 'Happy', 'n': 3, 'title': 'proof 3', 'at': 3, 'said': [{'who': 'OSSY', 'note': 'no source for pick 3'}]}   # G4 passed it: not quoted
