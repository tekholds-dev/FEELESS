"""🎓 COMP's teacher: live-priced picks, a cost shown before it runs, a hard cap, one lesson per proof, owner only, never a wallet (network faked)."""
import asyncio

import pytest

import comp_teacher as ct

MODELS = [{'id': 'anthropic/claude-opus-5.5', 'name': 'Opus', 'created': 9, 'pricing': {'prompt': '0.000004', 'completion': '0.00002'}},
          {'id': 'anthropic/claude-opus-4', 'name': 'Old', 'created': 1, 'pricing': {'prompt': '0.000015', 'completion': '0.000075'}},
          {'id': 'anthropic/claude-opus-5.5:batch', 'name': 'Batch', 'created': 10, 'pricing': {'prompt': '0.000001', 'completion': '0.00001'}},
          {'id': 'qwen/qwen3.7-plus', 'name': 'Qwen', 'created': 5, 'pricing': {'prompt': '0.00000032', 'completion': '0.00000128'}}]
PROOFS = '\n'.join(f'### PoW · $COIN{i}\nplan: bought the dip on volume {i}x, sold at +{i}0%, pool $40K, record checked by two sources.\n' for i in range(5))


def test_newest_flagship_per_family_with_a_live_price():
    t = ct.teachers(MODELS)
    assert [x['id'] for x in t] == ['anthropic/claude-opus-5.5', 'qwen/qwen3.7-plus']   # newest, never a batch variant
    assert t[0]['perLesson'] == ct.lesson_usd(4, 20) == 0.01
    assert ct.plan(t[0], 500) == {'n': 100, 'estUsd': 1.0, 'capUsd': 1.5} and ct.plan(t[0], 50, have=3)['n'] == 3
    big = {**t[0], 'perLesson': 1.0}
    assert ct.plan(big, 100)['capUsd'] == ct.MAX_USD                                     # never past the hard cap


def test_a_run_keeps_each_lesson_stops_at_the_cap_and_never_repeats(tmp_path):
    t = ct.teachers(MODELS)[0]; todo = ct.untaught(ct.blocks(PROOFS), [])
    assert len(todo) == 5
    calls = []
    post = lambda model, messages: (calls.append(model) or ('CLAIM: x\nRULE: check the pool', 0.004))
    job = {'done': 0, 'spentUsd': 0.0}
    ct.run(tmp_path, 'k', t, todo, 0.01, job, post=post)
    assert job['done'] == 2 and job['why'] == 'reached the cap' and job['spentUsd'] <= 0.01   # 0.004 + 0.004, the third would pass the cap
    lessons = ct.load(tmp_path)
    assert len(lessons) == 2 and ct.summary(lessons)['spentUsd'] == 0.008 and 'RULE' in ct.corpus(lessons)
    assert len(ct.untaught(ct.blocks(PROOFS), lessons)) == 3                                # a taught proof is never taught twice
    stopped = {'done': 0, 'spentUsd': 0.0, 'stop': True}
    ct.run(tmp_path, 'k', t, todo, 1, stopped, post=post)
    assert stopped['done'] == 0 and stopped['why'] == 'stopped'


class Req:
    headers = {}
    client = type('C', (), {'host': '127.0.0.1'})()


def test_only_the_owner_and_only_a_listed_teacher_at_the_quoted_price(tmp_path, monkeypatch):
    import rep_model_lab as lab
    import reputation_service as rs
    from fastapi import HTTPException

    def stranger(_r):
        raise HTTPException(403, 'owner only')
    monkeypatch.setattr(rs, '_require_owner', stranger)
    with pytest.raises(HTTPException):
        asyncio.run(lab.teach_start(Req(), lab.Teach(model='qwen/qwen3.7-plus', n=2)))
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER')
    monkeypatch.setattr(rs, 'DATA_DIR', tmp_path); monkeypatch.setenv('OPENROUTER_API_KEY', 'k')
    monkeypatch.setattr(lab, '_proof_text', lambda rs_: PROOFS)
    monkeypatch.setattr(lab, '_TEACH', {'job': None, 'models': ct.teachers(MODELS), 'at': 9e18})
    ran = []
    monkeypatch.setattr(lab._ct, 'run', lambda *a: ran.append(a))
    with pytest.raises(HTTPException):
        asyncio.run(lab.teach_start(Req(), lab.Teach(model='made/up', n=2)))
    with pytest.raises(HTTPException):   # the price moved above what he saw: nothing runs
        asyncio.run(lab.teach_start(Req(), lab.Teach(model='anthropic/claude-opus-5.5', n=3, quoteUsd=0.001)))
    assert not ran
    out = asyncio.run(lab.teach_start(Req(), lab.Teach(model='qwen/qwen3.7-plus', n=2, quoteUsd=0.01)))
    assert out['job']['n'] == 2 and out['job']['capUsd'] <= ct.MAX_USD
    v = lab._teach_view(rs)
    assert v['untaught'] == 5 and v['keyOk'] and [x['id'] for x in v['teachers']][0] == 'anthropic/claude-opus-5.5'
    assert 'teacher' in lab.SOURCES
