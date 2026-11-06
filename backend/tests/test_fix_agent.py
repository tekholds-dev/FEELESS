"""A01: a fix lives on its own branch, tested, and waits for the owner. It can never reach money, keys or main."""
import subprocess

import pytest

import fix_agent as fa


def test_only_crashes_become_cases_one_per_message():
    rows = fa.cases_from([{'text': '[panel crash] This page: cat is not defined · in <FeeCatDesk>', 'at': 5, 'page': '/x'}, {'text': '[panel crash] This page: cat is not defined · in <FeeCatDesk>', 'at': 9}, {'text': '[dead click] a sits over b', 'at': 10}, {'text': '[auto crash] Module build failed from loader', 'at': 11}])
    assert len(rows) == 1 and rows[0]['times'] == 2 and rows[0]['at'] == 9 and 'FeeCatDesk' in rows[0]['text']


def test_it_reads_the_component_and_the_words_from_a_crash():
    assert fa.parse_crash('[panel crash] This page: cat is not defined · in <FeeCatDesk>') == ('FeeCatDesk', ['cat'])
    c, w = fa.parse_crash("[panel crash] This page: Cannot read properties of undefined (reading 'x') · in <DeskIcon>")
    assert c == 'DeskIcon' and w == ['x']
    c, w = fa.parse_crash('[panel crash] This page: (d.plan || []).filter is not a function · in <ProofStatic>')
    assert c == 'ProofStatic' and 'filter' in w


@pytest.mark.parametrize('path', ['frontend/src/components/SwapBox.jsx', 'frontend/src/lib/wallet.js', 'frontend/src/components/command/FuseLab.jsx', 'frontend/src/components/StakePanel.jsx', 'frontend/src/lib/chatSession.js', 'backend/server.py', 'backend/.env', '../etc/passwd', '/etc/passwd', 'frontend/src/a.test.jsx', 'frontend/src/data.json', 'docs/HANDOFF.md'])
def test_money_keys_tests_and_anything_outside_the_front_end_are_refused(path):
    assert fa.allowed(path)


def test_ordinary_front_end_files_are_allowed():
    assert fa.allowed('frontend/src/components/command/FeeCatDesk.jsx') == '' and fa.allowed('frontend/src/components/Fees.jsx') and fa.allowed('frontend/src/components/command/GameRoom.jsx') == '' and fa.allowed('frontend/src/styles/zoomPane.css') == ''


def test_a_fix_must_be_exact_small_and_real():
    assert fa.apply_fix('abc', 'b', 'x') == ('axc', '')
    assert fa.apply_fix('abc', 'zz', 'x')[0] is None and fa.apply_fix('aa', 'a', 'x')[0] is None and fa.apply_fix('abc', '', 'x')[0] is None and fa.apply_fix('abc', 'b', 'b')[0] is None and fa.apply_fix('b', 'b', 'x' * 3000)[0] is None


def test_the_reply_is_data_and_a_think_block_is_not_the_answer():
    assert fa.parse_reply('<think>{"old":"no"}</think>{"old":"yes"}')['old'] == 'yes' and fa.parse_reply('sure thing') is None


def _repo(tmp_path):
    root = tmp_path / 'repo'; (root / 'frontend/src').mkdir(parents=True); (root / 'frontend/node_modules').mkdir()
    (root / 'frontend/src/App.jsx').write_text('const a = cat;\n'); (root / 'frontend/src/Pay.jsx').write_text('x\n')
    for c in (['init', '-q', '-b', 'main'], ['add', '-A'], ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'one']):
        subprocess.run(['git', *c], cwd=root, check=True, capture_output=True)
    return root


def _fake_checks(real):
    def run(cmd, cwd, timeout=300):
        return (0, 'Tests: 1 passed') if cmd[0] in ('npx', 'yarn') else real(cmd, cwd, timeout)
    return run


def test_a_try_lands_on_its_own_branch_and_main_never_moves(tmp_path):
    root = _repo(tmp_path); head = subprocess.run(['git', 'rev-parse', 'main'], cwd=root, capture_output=True, text=True).stdout
    got = fa.try_fix('case one', 'frontend/src/App.jsx', 'cat', 'c', root=root, work=tmp_path / 'w', run=_fake_checks(fa._run))
    assert got['ok'] and got['branch'].startswith('fix/caseone-') and all(c['ok'] for c in got['checks'])
    assert (root / 'frontend/src/App.jsx').read_text() == 'const a = cat;\n' and subprocess.run(['git', 'rev-parse', 'main'], cwd=root, capture_output=True, text=True).stdout == head
    assert 'const a = c;' in subprocess.run(['git', 'show', f"{got['branch']}:frontend/src/App.jsx"], cwd=root, capture_output=True, text=True).stdout
    fa.drop(got['branch'], got['tree'], root)
    assert got['branch'] not in subprocess.run(['git', 'branch'], cwd=root, capture_output=True, text=True).stdout


def test_a_bad_or_off_limits_fix_leaves_nothing_behind(tmp_path):
    root = _repo(tmp_path)
    assert 'money' in fa.try_fix('c', 'frontend/src/Pay.jsx', 'x', 'y', root=root, work=tmp_path / 'w')['why']
    got = fa.try_fix('c', 'frontend/src/App.jsx', 'not there', 'y', root=root, work=tmp_path / 'w', run=_fake_checks(fa._run))
    assert not got['ok'] and 'not in the file' in got['why'] and 'fix/' not in subprocess.run(['git', 'branch'], cwd=root, capture_output=True, text=True).stdout


def test_the_folder_lists_crashes_is_owner_only_and_approve_needs_a_passed_fix(monkeypatch, tmp_path):
    rs = pytest.importorskip('reputation_service')
    from fastapi.testclient import TestClient
    c = TestClient(rs.app, raise_server_exceptions=False)
    assert c.get('/api/reputation/admin/fix').status_code in (401, 403) and c.post('/api/reputation/admin/fix', json={'id': 'x', 'seat': 'lan'}).status_code in (401, 403)
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'owner'); monkeypatch.setattr(rs, 'BUGS_PATH', tmp_path / 'b.json'); monkeypatch.setattr(rs, 'FIX_RUNS_PATH', tmp_path / 'r.json'); monkeypatch.setattr(rs, 'BUILD_QUEUE_PATH', tmp_path / 'q.json')
    (tmp_path / 'b.json').write_text('{"bugs":[{"text":"[panel crash] This page: cat is not defined · in <FeeCatDesk>","at":5}]}')
    got = c.get('/api/reputation/admin/fix').json(); cid = got['cases'][0]['id']; assert got['cases'][0]['run'] is None
    assert c.post('/api/reputation/admin/fix', json={'id': cid, 'approve': True}).status_code == 400
    rs._fix_store({'id': cid, 'stage': 'review', 'branch': 'fix/a-1', 'file': 'frontend/src/A.jsx', 'cause': 'wrong name', 'at': 1})
    r = c.post('/api/reputation/admin/fix', json={'id': cid, 'approve': True}); assert r.status_code == 200, r.text
    assert 'fix/a-1' in (tmp_path / 'q.json').read_text() and c.get('/api/reputation/admin/fix').json()['cases'][0]['run']['stage'] == 'approved'
