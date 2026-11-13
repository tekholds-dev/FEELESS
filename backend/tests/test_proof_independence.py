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
