"""🧑‍⚖️ COL-20: each judge reads its own misses, a third non-Qwen judge, one issue counts once, kit pins, missions per dollar, daily chain tip."""
import asyncio
import json
import os

import proof_events as pev
import proof_review as pr
import ps_hidden


def _rows():
    return [('pos', 'a', 'review', {'reviewers': {'ossy': {'verdict': 'fail', 'why': 'no sources'}, 'g4': {'verdict': 'pass'}}}),
            ('pos', 'a', 'stamp', {'stamp': 'proved'}),
            ('pob', 'b', 'review', {'reviewers': {'ossy': {'verdict': 'pass'}, 'g4': {'verdict': 'pass'}}}),
            ('pob', 'b', 'stamp', {'stamp': 'proved'}),
            ('pob', 'b', 'correction', {'event': 'stamp', 'to': 'not'}),
            ('pop', 'c', 'review', {'reviewers': {'ossy': {'verdict': 'fail'}}}),
            ('pop', 'c', 'stamp', {'stamp': 'not'})]


def test_a_judge_reads_only_its_own_misses_against_the_real_stamp_after_corrections():
    m = pr.misses(_rows(), 'ossy', titles={('pos', 'a'): 'GLINT page'})
    assert m['n'] == 3 and m['right'] == 1 and m['baseline'] == 67
    assert m['lines'][0].startswith("POB 'b': you said PASS") and 'NOT PROVED' in m['lines'][0]   # newest first; the corrected stamp counts
    assert "POS 'GLINT page': you said FAIL (no sources)" in m['lines'][1]
    g = pr.misses(_rows(), 'g4')
    assert g['n'] == 2 and len(g['lines']) == 1 and 'ossy' not in json.dumps(g).lower()


def test_the_misses_line_is_data_and_warns_a_fail_everything_judge():
    line = pr.misses_line(pr.misses(_rows(), 'ossy'), 'OSSY')
    assert 'YOUR RECORD (OSSY): right 33% on 3' in line and 'Failing by default does NOT beat that' in line
    assert pr.misses_line({'n': 0}, 'ZED') == '' and pr.misses_line(None, 'ZED') == ''


def test_a_third_judge_from_another_family_and_a_new_rubric_version():
    keys = [k for k, _m, _n in pr.REVIEWERS]
    assert keys == ['ossy', 'g4', 'zed'] and pr.VERSION == 7
    assert pr.family('local · google/gemma-3-12b') == 'google' and pr.family('local · gemma-3-12b') == 'gemma'


def test_one_issue_written_into_five_checks_fails_once_not_five_times():
    raw = json.dumps({'checks': [{'pass': False, 'found': 'No sources are cited for the numbers'}, {'pass': False, 'found': 'no sources cited for these numbers'},
                                 {'pass': True, 'found': 'It does what the plan asked'}, {'pass': False, 'found': 'Sources for the numbers are not cited'},
                                 {'pass': True, 'found': 'Works on a phone'}], 'why': 'sources'})
    v = pr.verdict_of(raw, '2026-11-13')
    assert v['score'] == 67   # 2 passes of 3 counted checks, not 2 of 5 (40)
    assert v['checks'][1].startswith('· ') and 'counted once' in v['checks'][1] and v['checks'][0].startswith('✗ ')
    two = json.dumps({'checks': [{'pass': False, 'found': 'No sources cited'}, {'pass': False, 'found': 'The chart shows sample data'}] + [{'pass': True, 'found': 'ok'}] * 3})
    assert pr.verdict_of(two, '2026-11-13')['score'] == 60   # different issues still count separately
    assert 'Judge each check on ITS OWN question' in pr.SYS


def test_zed_never_answers_with_another_family_model(monkeypatch):
    import feecat_service as fs
    monkeypatch.delenv('ZED_LLM_MODEL', raising=False)
    assert fs._lm_which('local/zed') == 'ZED' and fs._lm_which('local/g4') == 'LAN' and fs._lm_which('local/ossy') == 'LOCAL'
    assert fs._lm_pick('ZED', ['qwen/qwen3.5-9b', 'google/gemma-3-12b']) == 'google/gemma-3-12b'
    assert fs._lm_pick('ZED', ['qwen/qwen3.5-9b']) is None   # a Qwen never stands in
    monkeypatch.setenv('ZED_LLM_MODEL', 'mistral-small')
    assert fs._lm_pick('ZED', ['mistral-small', 'qwen/qwen3.5-9b']) == 'mistral-small'
    assert fs._INTERNAL.search('ZED said pass')   # users only see The Collective


def test_zed_with_no_gemma_loaded_gives_no_answer(monkeypatch):
    import feecat_service as fs
    monkeypatch.delenv('ZED_LLM_MODEL', raising=False); fs._LM_SEEN.pop('ZED', None)
    posted = []

    class R:
        def __init__(self, j, code=200):
            self._j, self.status_code = j, code

        def json(self):
            return self._j

    class H:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, **k):
            return R({'data': [{'id': 'qwen/qwen3.5-9b'}]})

        async def post(self, url, **k):
            posted.append(k); return R({'choices': [{'message': {'content': 'x'}}]})
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **k: H())
    text, usd = asyncio.run(fs._lm_call_one('local/zed', [{'role': 'user', 'content': 'hi'}], 50))
    assert text == '' and usd == 0.0 and not posted and 'Gemma' in fs._OR_LAST['err']


def test_kits_on_a_page_are_checked_against_todays_pins():
    page = ('<html><head><title>T</title><meta name="viewport" content="x"><script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>'
            '<script src="https://cdn.jsdelivr.net/npm/three@0.187.0/build/three.module.js"></script></head><body><h1>Hi</h1>' + '<p>words here</p>' * 20 + '</body></html>')
    pins = {'echarts': ('6', 'major'), 'three': ('0.187.0', 'exact'), 'gsap': ('3', 'major')}
    r = ps_hidden.run(page, pins)
    assert {k['pkg']: k['ok'] for k in r['kits']} == {'echarts': False, 'three': True} and 'kits-current' in r['failed']
    r2 = ps_hidden.run(page.replace('echarts@5.4.3', 'echarts@6.0.0'), pins)
    assert 'kits-current' not in r2['failed'] and r2['total'] == 10
    assert ps_hidden.run(page)['total'] == 9 and ps_hidden.run(page)['kits'] == []   # no pins = the old nine checks


def test_verified_missions_per_dollar_counts_settled_proofs_and_their_workspace_spend():
    tally = {('pos', 'w1'): {'usd': 0.5}, ('pob', 'b'): {'usd': 0.25}, ('pop', 'c'): {'usd': 0.25}}
    v = pr.per_dollar(_rows() + [('pow', 'open', 'stamp', {'stamp': 'pending'})], tally, {('pos', 'a'): 'w1'})
    assert v['total'] == {'proved': 1, 'settled': 3, 'usd': 1.0, 'perDollar': 1.0}
    assert v['byKind']['pos']['perDollar'] == 2.0 and v['byKind']['pob']['proved'] == 0
    assert pr.per_dollar(_rows(), {})['total']['perDollar'] is None   # all free: no fake ratio


def test_the_chain_tip_is_kept_once_a_day_and_a_cut_back_record_fails_it(tmp_path, monkeypatch):
    monkeypatch.setenv('PROOF_EVENTS_KEY', 'test-key')
    db, an = tmp_path / 'e.db', tmp_path / 'a.jsonl'
    assert pev.anchor(db, an, now=1_800_000_000) is None or True   # an empty record keeps nothing
    for i in range(3):
        pev.append(db, 'pow', f'r{i}', 'plan', {'i': i})
    day1 = pev.anchor(db, an, now=1_800_000_000)
    assert day1['n'] == 3 and pev.anchor(db, an, now=1_800_000_100) is None   # once a day
    assert pev.anchor_check(db, an)['ok'] is True
    import sqlite3
    c = sqlite3.connect(db); c.execute('DELETE FROM events WHERE n = 3'); c.commit(); c.close()
    chk = pev.anchor_check(db, an)
    assert chk['ok'] is False and 'cut back' in chk['why'] and chk['days'] == 1
    assert pev.anchor_check(db, tmp_path / 'none.jsonl')['ok'] is None
    assert os.path.exists(an)


def test_a_review_whose_zed_vote_came_from_a_qwen_is_judged_again():
    f = {'id': 'p', 'status': 'closed', 'closedAt': 5, 'review': {'v': pr.VERSION, 'by': {'zed': {'answeredBy': 'local · qwen/qwen3.5-9b'}}}}
    assert pr.next_due({'cats': {'s': {'psFolders': [f]}}})[2]['id'] == 'p'
    f['review']['by']['zed']['answeredBy'] = 'local · google/gemma-3-4b'
    assert pr.next_due({'cats': {'s': {'psFolders': [f]}}}) is None
