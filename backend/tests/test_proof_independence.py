"""🔒 owner 2026-11-13 (GPT · Grok · Claude agreed): a builder never judges its own proof, the judges never see the owner's grade or the
stamp, and every review records what makes it reproducible. Real case: Sicario's builds with local/ossy + local/g4, the same two judges."""
import json

import proof_review as pr


def test_a_judge_that_built_the_proof_sits_out():
    assert pr.recused(['local/ossy', 'local/g4']) == ['ossy', 'g4']
    assert pr.recused(['openai/gpt-6.1-terra', 'local/g4']) == ['g4']
    assert pr.recused(['openai/gpt-6.1-terra', 'google/gemini-4-carbon']) == []
    assert pr.builders_of({}, {'brains': ['local/ossy', 'local/g4']}, 'pos') == ['local/ossy', 'local/g4']
    assert pr.builders_of({'minds': ['x/y']}, {'brains': ['local/ossy']}, 'pos') == ['x/y']   # the folder's own record wins


def test_every_judge_recused_is_no_verdict_never_a_pass():
    v = {'score': 100, 'verdict': 'pass', 'checks': [], 'why': '', 'answeredBy': 'local · qwen/qwen3.5-9b'}
    rv = pr.combine({'ossy': v, 'g4': None}, ['ossy', 'g4'], ['local/ossy', 'local/g4'], 'BODY')
    assert rv['verdict'] is None and rv['score'] is None and rv['independent'] is False and 'built' in rv['why'] and rv['by'] == {}


def test_a_review_records_rubric_builders_families_and_the_evidence_hash():
    a = {'score': 80, 'verdict': 'pass', 'checks': [], 'why': '', 'answeredBy': 'local · qwen/qwen3.5-9b'}
    b = {'score': 60, 'verdict': 'pass', 'checks': [], 'why': '', 'answeredBy': 'lan · qwen/qwen3.5-4b'}
    rv = pr.combine({'ossy': a, 'g4': b}, [], ['openai/gpt-6.1-terra'], 'BODY')
    assert rv['rubric'] == pr.VERSION and rv['builders'] == ['openai/gpt-6.1-terra'] and rv['families'] == ['qwen'] and rv['oneFamily'] is True
    assert rv['evidenceSha'] == pr.evidence_sha('BODY') and len(rv['evidenceSha']) == 64 and rv['verdict'] == 'pass' and rv['independent'] is True


def test_the_judges_never_read_the_owners_grade_or_the_stamp():
    f = {'status': 'closed', 'topic': 'GLINT', 'graded': 'right', 'gradedBy': None, 'at': 1794000000, 'refs': []}
    body = pr.brief('pos', f, {'outcome': {'state': 'proved', 'authority': 'owner mark'}, 'title': 'GLINT'}, now=1794500000)
    d = json.loads(body.split('\n', 1)[1])
    assert 'graded' not in json.dumps(d.get('result') or {}) and 'outcome' not in d and 'owner mark' not in body and '"right"' not in body


def test_hidden_checks_catch_made_up_numbers_and_never_the_hidden_webgl_fallback():
    import ps_hidden
    base = '<html><head><title>GLINT</title><meta name="viewport" content="width=device-width"></head><body><div id="none">This scene needs WebGL.</div><h1>GLINT</h1><p>' + 'A real page that says something useful about the coin. ' * 4 + '</p>'
    ok = ps_hidden.run(base + '</body></html>')
    assert ok['passed'] == ok['total'] and ok['failed'] == []                      # our own display:none fallback is not "unfinished"
    bad = ps_hidden.run(base + '<small class="note">Sample numbers until the coin is live</small><img src="http://x/a.png"></body></html>')
    assert {'no-fake-data', 'images-load', 'no-insecure-content'} <= set(bad['failed']) and bad['pct'] < 100
    assert ps_hidden.run('') is None


def test_the_hidden_checks_never_reach_a_builder():
    """They are hidden: not in the review brief the judges read, not in the lessons the next build reads."""
    import pathlib
    src = pathlib.Path(pr.__file__).read_text()
    assert 'ps_hidden' not in src and 'no-fake-data' not in pr.lessons_line(['x'])


def test_the_judge_scorecard_checks_each_verdict_against_the_real_stamp():
    rows = [('pow', 'a', 'stamp', {'stamp': 'proved'}), ('pow', 'b', 'stamp', {'stamp': 'not'}), ('pow', 'c', 'stamp', {'stamp': 'not'}),
            ('pow', 'a', 'review', {'reviewers': {'ossy': {'verdict': 'fail'}, 'g4': {'verdict': 'fail'}}}),
            ('pow', 'a', 'review', {'reviewers': {'ossy': {'verdict': 'pass'}, 'g4': {'verdict': 'fail'}}}),   # the newest review counts
            ('pow', 'b', 'review', {'reviewers': {'ossy': {'verdict': 'fail'}, 'g4': {'verdict': 'fail'}}}),
            ('pow', 'c', 'review', {'reviewers': {'ossy': {'verdict': 'pass'}, 'g4': {'verdict': 'fail'}}}),
            ('pow', 'c', 'correction', {'event': 'stamp', 'to': 'proved'}),                                    # a corrected stamp is the one that counts
            ('pow', 'd', 'review', {'reviewers': {'ossy': {'verdict': 'pass'}}})]                              # no stamp yet → not counted
    sc = {r['judge']: r for r in pr.scorecard(rows)}
    assert (sc['ossy']['n'], sc['ossy']['right'], sc['ossy']['baselinePct'], sc['ossy']['beats']) == (3, 3, 33, True) and sc['ossy']['say'].startswith('OSSY is right 100%')
    assert (sc['g4']['n'], sc['g4']['right'], sc['g4']['beats']) == (3, 1, False) and sc['g4']['say'].startswith('G4')


def test_users_see_the_judges_as_the_collective_never_by_name():
    """Owner 2026-11-13: users see OSSY and G4 scores and grades as The Collective; only the owner's staff view keeps each judge."""
    rows = [('pow', 'a', 'stamp', {'stamp': 'proved'}), ('pow', 'b', 'stamp', {'stamp': 'not'}),
            ('pow', 'a', 'review', {'verdict': 'pass', 'reviewers': {'ossy': {'verdict': 'pass'}, 'g4': {'verdict': 'pass'}}}),
            ('pow', 'b', 'review', {'verdict': 'fail', 'reviewers': {'ossy': {'verdict': 'pass'}, 'g4': {'verdict': 'fail'}}})]
    cards = pr.scorecard(rows)
    assert [c['judge'] for c in cards] == ['collective', 'g4', 'ossy']
    pub = pr.collective_only(cards)
    assert [c['judge'] for c in pub] == ['collective'] and pub[0]['rightPct'] == 100 and pub[0]['say'].startswith('The Collective is right')
    import feecat_service as fs
    row = {'name': 'a page', 'review': {'by': {'ossy': {'score': 80, 'verdict': 'pass', 'answeredBy': 'local/ossy', 'checks': ['✓ G4 liked it']},
                                               'g4': {'score': 60, 'verdict': 'fail'}}, 'recused': ['ossy'], 'families': ['qwen'], 'why': 'OSSY sat out'},
           'chat': 'OSSY is my model'}
    out = fs._for_users({'ownerStaff': False}, row)
    assert set(out['review']['by']) == {'collective', 'collective-2'} and 'answeredBy' not in out['review']['by']['collective']
    assert out['review']['by']['collective']['checks'] == ['✓ The Collective liked it'] and out['review']['recused'] == ['The Collective']
    assert 'families' not in out['review'] and 'ossy' not in str(out['review']).lower() and 'g4' not in str(out['review']).lower()
    assert out['chat'] == 'OSSY is my model'   # only grades and scores change; nothing else is touched
    assert fs._for_users({'ownerStaff': True}, row) is row   # the owner reviews OSSY + G4 by name


def test_proofs_stay_private_to_visitors_and_other_owners(monkeypatch):
    """Owner 2026-11-13: visitors see no proofs; an owner sees their own; the staff (Fee's desk) every agent's."""
    import asyncio
    import feecat_service as fs
    store = {'cats': {'a': {'id': 'a', 'ownerWallet': 'W1', 'name': 'A'}, 'b': {'id': 'b', 'ownerWallet': 'W2', 'name': 'B'}}}
    monkeypatch.setattr(fs, '_load', lambda: store)
    monkeypatch.setattr(fs, '_hive_cells', lambda: [{'id': 'x', 'cat': 'a', 'pow': {'sym': 'X'}, 'folder': {'id': 'f1'}}])
    monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: {'s1': 'W1', 's2': 'W2', 'st': 'STAFF'}.get(s))

    async def creator(w):
        return w == 'STAFF'
    monkeypatch.setattr(fs, '_is_creator', creator)
    feed = lambda **k: asyncio.run(fs.pow_feed(**k))   # noqa: E731
    visitor = feed(limit=12)
    assert visitor['folders'] == [] and visitor['rows'] == [] and visitor['private'] and visitor['rules']['sites']
    assert feed(limit=12, cat='a', session='s2')['rows'] == []          # another owner never reads it
    assert len(feed(limit=12, cat='a', session='s1')['rows']) == 1      # its owner does
    assert len(feed(limit=12, session='st')['rows']) == 1               # the staff desk sees every agent
