"""🎓 Slice 7: COMP learns from real, judged proofs only (each with its pass / fail evidence; everything else dropped and counted), sits an
exam on held-out real proofs against the base model and OSSY / G4 / ZED, and is not shipped unless it beats the base model."""
import json
import zlib

import comp_real as cr
import comp_v2 as cv
import comp_v2_exam as ex

REVIEW = {'by': {'ossy': {'score': 80, 'verdict': 'pass', 'checks': ['JUDGE-SAID-PASS']}}}


def _pow(i, pnl, **kw):
    return {'id': f'pow{i}', 'name': f'PoW #{i}', 'status': 'closed', 'at': 1000 + i, 'pnlPct': pnl, 'entry': 1.0, 'exit': 2.0, 'tp': 1.5, 'sl': 0.8,
            'sym': 'BLUE', 'pick': {'sym': 'BLUE', 'src': 'pump', 'liq': 59000, 'vol': 2600000}, 'whys': {'0': 'deep pool, no rug signals'},
            'why': 'SELL-REASON chart rolled over, down 12%', 'review': REVIEW, **kw}


def _pob(i, graded, by='scoreboard', **kw):
    return {'id': f'pob{i}', 'status': 'closed', 'at': 2000 + i, 'topic': f'Knicks game {i}', 'graded': graded, 'gradedBy': by,
            'games': [{'label': 'Knicks at Wolves', 'short': 'Knicks', 'final': True, 'score': 'FINAL-112-108', 'won': graded == 'right'}],
            'calls': [{'mind': 0, 'name': 'deepseek', 'picks': [{'pick': 'Knicks win', 'confidence': 70, 'why': 'rest edge'}]}], 'review': REVIEW, **kw}


def _cats():
    return {'c1': {'pobFolders': [_pob(1, 'right'), _pob(2, 'wrong'), _pob(3, 'right', test=True), _pob(4, None, by=None),
                                  _pob(5, 'right', by=None),                                      # a hand mark on a scored game
                                  {**_pob(6, None, by=None), 'kalshi': {'title': 'Knicks win', 'side': 'yes', 'price': 0.4, 'count': 1, 'outcome': 'lost'}}],
                   'powFolders': [_pow(1, 12.5), _pow(2, -5.7), _pow(3, 0.0), _pow(4, None)],
                   'psFolders': [{'id': 'ps1', 'status': 'closed', 'topic': 'fun game', 'plan': 'an arcade runner', 'steps': ['spawn', 'dodge'],
                                  'graded': 'wrong', 'gradeWhy': 'the canvas is blank', 'review': REVIEW},
                                 {'id': 'ps2', 'status': 'closed', 'topic': 'quiet', 'review': REVIEW},          # only the judges graded it
                                 {'id': 'ps3', 'status': 'closed', 'topic': 'empty', 'graded': 'right'}]}}    # says nothing it did


def test_only_real_judged_proofs_are_kept_and_every_drop_is_counted():
    g = cr.collect(_cats(), extra={'market_row': 546, 'teacher_lesson': 32, 'kalshi_lesson': 2})
    ids = {r['id'] for r in g['rows']}
    assert ids == {'pob1', 'pob2', 'pob6', 'pow1', 'pow2', 'ps1'}
    assert g['dropped'] == {'test': 1, 'hand_mark_on_game': 1, 'flat': 1, 'judge_only': 3, 'no_evidence': 1,   # open but judge-reviewed = judge_only
                            'market_row': 546, 'teacher_lesson': 32, 'kalshi_lesson': 2}
    assert set(g['why']) == set(g['dropped']) and g['kept'] == {'PoB': 3, 'PoW': 2, 'PoStatic': 1}
    by = {r['id']: r for r in g['rows']}
    assert by['pob6']['settledBy'] == 'kalshi' and by['pob6']['outcome'] == 'lost'          # a real-money result beats everything
    assert by['pow1']['settledBy'] == 'pnl' and '+12.50%' in by['pow1']['proofOf'][0]
    assert by['pob1']['settledBy'] == 'scoreboard' and any('FINAL-112-108' in x for x in by['pob1']['proofOf'])
    assert by['ps1']['settledBy'] == 'owner mark' and any('canvas is blank' in x for x in by['ps1']['proofOf'])
    assert all(r['proofOf'] and r['outcome'] in ('won', 'lost') for r in g['rows'])          # each with its pass / fail evidence


def test_the_question_never_holds_the_result_or_the_judges_words():
    for r in cr.collect(_cats())['rows']:
        q = cv.prompt_of(r)
        for leak in ('SELL-REASON', 'FINAL-112-108', 'JUDGE-SAID-PASS', 'canvas is blank', 'exit', 'side won', 'side lost', 'graded'):
            assert leak not in q, (r['id'], leak)
    pw = next(r for r in cr.collect(_cats())['rows'] if r['id'] == 'pow1')
    q = cv.prompt_of(pw)
    assert 'What it did:' in q and 'liq 59000' in q and 'deep pool' in q and 'take-profit 1.5' in q   # what it did BEFORE it settled


def test_stash_copies_fill_in_gone_folders_once():
    stash = {'pobFolders:pob1': _pob(1, 'right'), 'pobFolders:pob9': {**_pob(9, None, by=None)}, 'pobFolders:pob8': b'',
             'psFolders:ps7': {'id': 'ps7', 'topic': 'x', 'plan': 'p', 'test': True}}
    items = [{'key': 'pobFolders:pob1', 'category': 'Picks', 'outcome': 'won'},
             {'key': 'pobFolders:pob1:src:espn.com', 'category': 'Picks', 'outcome': 'won'},
             {'key': 'pobFolders:pob9', 'category': 'Picks', 'outcome': 'won', 'source': 'espn.com', 'at': 9},
             {'key': 'pobFolders:pob8', 'category': 'Picks', 'outcome': 'lost'},
             {'key': 'psFolders:ps7', 'category': 'Code', 'outcome': 'won'},
             {'key': 'shot:1', 'category': 'Snapshots', 'outcome': 'none'}]
    read = lambda k: zlib.compress(json.dumps(stash[k]).encode()) if isinstance(stash[k], dict) else stash[k]   # noqa: E731
    g = cr.collect({'c': {'pobFolders': [_pob(1, 'right')]}}, items, read)
    assert sorted(r['id'] for r in g['rows']) == ['pob1', 'pob9']
    assert g['dropped'] == {'duplicate': 1, 'source_marker': 1, 'unreadable': 1, 'test': 1}
    assert next(r for r in g['rows'] if r['id'] == 'pob9')['settledBy'] == 'scoreboard'


def test_owner_grade_labels_an_open_proof_but_a_judge_never_does():
    cats = {'c': {'psFolders': [{'id': 'ps5', 'status': 'closed', 'plan': 'a chart page', 'review': REVIEW}]}}
    assert cr.collect(cats)['dropped'] == {'judge_only': 1}
    g = cr.collect(cats, grades={'psFolders:ps5': {'verdict': 'good', 'note': 'works on my phone'}})
    assert g['rows'][0]['outcome'] == 'won' and g['rows'][0]['settledBy'] == 'owner grade'


def test_folds_are_fixed_by_proof_id_so_an_exam_proof_never_trains_later(tmp_path):
    rows = [{'id': f'p{i}', 'kind': 'PoW', 'title': 't', 'outcome': 'won' if i % 2 else 'lost', 'evidence': ['x'], 'proofOf': ['y']} for i in range(200)]
    first = {r['id'] for r in cr.split(rows[:120])[2]}
    later_train = {r['id'] for r in cr.split(rows)[0]}
    assert first and not first & later_train and first <= {r['id'] for r in cr.split(rows)[2]}
    c = cv.write_dataset({'rows': rows, 'dropped': {'test': 3}, 'why': {'test': cr.WHY['test']}}, tmp_path)
    assert c['only'] == 'real judged proofs' and c['droppedN'] == 3 and c['net'] == 0 and sum(k['test'] for k in c['byKind']) == c['test']


def _exam(comp, base, maj, n=20):
    return {'n': n, 'examinees': [{'id': 'comp', 'score': {'right': comp, 'n': n}}, {'id': 'base', 'score': {'right': base, 'n': n}},
                                  {'id': 'baseline', 'name': 'Always "won"', 'score': {'right': maj, 'n': n}}]}


def test_a_comp_that_does_not_beat_the_base_is_not_shipped_and_says_why(tmp_path):
    tie = cv.ship_verdict(_exam(11, 11, 10))
    assert not tie['ship'] and 'A tie is not a win' in tie['why'] and '11 of 20' in tie['why']
    assert not cv.ship_verdict(_exam(9, 11, 10))['ship'] and 'did worse' in cv.ship_verdict(_exam(9, 11, 10))['why']
    assert not cv.ship_verdict(_exam(12, 11, 13))['ship']                         # beat the base but not always guessing
    assert not cv.ship_verdict({'n': 5, 'examinees': [{'id': 'comp', 'blocked': 'not trained yet'}]})['ship']
    ok = cv.ship_verdict(_exam(14, 11, 10))
    assert ok['ship'] and ok['margin'] == 3 and ok['why'].startswith('Shipped')
    # on disk: a pass copies the picked adapter to shipped/; a later fail leaves that shipped COMP untouched
    pick = tmp_path / 'pick'; pick.mkdir(); (pick / 'adapters.safetensors').write_bytes(b'v1'); (pick / 'adapter_config.json').write_text('{}')
    e1 = _exam(14, 11, 10); assert cv.ship(tmp_path, e1, str(pick))['ship'] and e1['ship']['ship']
    assert (tmp_path / 'shipped' / 'adapters.safetensors').read_bytes() == b'v1' and cv.shipped(tmp_path)['comp'] == 14
    (pick / 'adapters.safetensors').write_bytes(b'v2')
    e2 = _exam(10, 11, 10); assert not cv.ship(tmp_path, e2, str(pick))['ship'] and 'Not shipped' in e2['ship']['why']
    assert (tmp_path / 'shipped' / 'adapters.safetensors').read_bytes() == b'v1' and cv.shipped(tmp_path)['comp'] == 14


def test_zed_answers_only_from_a_gemma():
    class R:
        def __init__(self, ids): self.ids = ids
        def json(self): return {'data': [{'id': i} for i in self.ids]}
    assert ex.zed_pick('http://x/v1', '', lambda u: R(['qwen/qwen3.5-9b'])) == ''
    assert ex.zed_pick('http://x/v1', '', lambda u: R(['qwen/qwen3.5-9b', 'google/gemma-3-12b'])) == 'google/gemma-3-12b'
    def boom(u): raise OSError('down')
    assert ex.zed_pick('http://x/v1', '', boom) == ''
    zed = ex.own_minds({'LOCAL_LLM_ENABLED': 'true', 'ZED_LLM_MODEL': 'google/gemma-3-12b'})[2]
    assert zed[0] == 'zed' and zed[3] == 'google/gemma-3-12b' and zed[5] is None
    zed = ex.own_minds({'ZED_LLM_MODEL': 'qwen/qwen3.5-9b'}, lambda b, k: '')[2]          # a Qwen named as ZED is never used
    assert zed[3] == '' and zed[5].startswith('no Gemma')


def test_the_free_exam_scores_everyone_on_the_same_proofs_and_rules_on_ship(tmp_path, monkeypatch):
    rows = [{'id': f'p{i}', 'kind': 'PoB', 'title': f't{i}', 'outcome': 'won' if i % 2 else 'lost', 'evidence': ['x'], 'proofOf': ['y']} for i in range(10)]
    (tmp_path / 'test_rows.json').write_text(json.dumps(rows)); (tmp_path / 'valid_rows.json').write_text('[]'); (tmp_path / 'train_rows.json').write_text('[]')
    (tmp_path / 'train.jsonl').write_text(json.dumps(cv.chat_of(rows[0])) + '\n')
    (tmp_path / 'adapter').mkdir(); (tmp_path / 'adapter' / 'adapters.safetensors').write_bytes(b'a'); (tmp_path / 'adapter' / 'adapter_config.json').write_text('{}')
    truth = [1.0 if r['outcome'] == 'won' else -1.0 for r in rows]
    def margins(sets, adapter=None, makers=(cv.prompt_of,)):
        good = truth if adapter else [1.0] * len(rows)            # COMP knows them all, the base always says won
        return [[[], good] for _ in makers]
    monkeypatch.setattr(ex, 'local_margins', margins)
    monkeypatch.setattr(ex, 'pick_checkpoint', lambda f, v: (str(tmp_path / 'adapter'), []))
    asked = []
    monkeypatch.setattr(ex, 'openai_style', lambda qs, k, b, m, timeout=60: asked.append(m) or ['won'] * len(qs))
    monkeypatch.setattr(ex, 'env_keys', lambda: {k: '' for k in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'XAI_API_KEY', 'OPENAI_MODEL', 'XAI_MODEL')} |
                        {'LOCAL_LLM_ENABLED': 'true', 'LAN_LLM_BASE_URL': 'http://lan/v1', 'ZED_LLM_MODEL': 'google/gemma-3'})
    def no_paid(*a, **k): raise AssertionError('a free exam never reads the paid key')
    monkeypatch.setattr(ex, 'owner_openrouter', no_paid)
    monkeypatch.setattr(cv, 'keep_history', lambda f, e: None)
    ex.main(tmp_path, free=True)
    e = json.loads((tmp_path / 'exam.json').read_text()); by = {x['id']: x for x in e['examinees']}
    assert by['comp']['score']['right'] == 10 and by['base']['score']['right'] == 5
    assert all(by[j]['score']['n'] == 10 for j in ('ossy', 'g4', 'zed')) and 'google/gemma-3' in asked
    assert all(by[f]['blocked'] == 'free exam: no paid call' for f in ('claude', 'gpt', 'grok'))
    assert e['ship']['ship'] and (tmp_path / 'shipped' / 'adapters.safetensors').exists()
