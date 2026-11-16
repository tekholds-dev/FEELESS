"""🔁 Both minds work on every filing (owner 2026-11-16): a mind that comes back blank is asked once more, and a slow mind never blanks
the other one's answer. No model or network is called: _think is faked."""
import asyncio

import feecat_service as fs

CAT = {'id': 'c1', 'brainsCfg': {'kind': 'general', 'brains': ['m/a', 'm/b']}}


def test_a_blank_mind_is_asked_once_more_with_room_to_answer(monkeypatch):
    seen = []

    async def think(cat, model, msgs, own, _x, max_tokens):
        seen.append((model, max_tokens, msgs[-1]['content'])); return ('' if len(seen) == 1 else 'PICK: Thunder 70%'), 0, ''
    monkeypatch.setattr(fs, '_think', think)
    out = asyncio.run(fs._pow2_ask(dict(CAT), 0, 'sys', 'who wins?', 320, {'proof': 'pob'}))
    assert out == 'PICK: Thunder 70%' and len(seen) == 2
    assert seen[1][1] == 640 and 'last reply was empty' in seen[1][2]   # the second ask has twice the room and says why


def test_an_answer_is_never_asked_twice_and_two_blanks_stay_blank(monkeypatch):
    n = []

    async def ok(*_a, **_k):
        n.append(1); return 'PICK: Kings', 0, ''
    monkeypatch.setattr(fs, '_think', ok)
    assert asyncio.run(fs._pow2_ask(dict(CAT), 1, 's', 'u', 100, {'proof': 'pob'})) == 'PICK: Kings' and len(n) == 1
    n.clear()

    async def blank(*_a, **_k):
        n.append(1); raise RuntimeError('no model')
    monkeypatch.setattr(fs, '_think', blank)
    assert asyncio.run(fs._pow2_ask(dict(CAT), 1, 's', 'u', 100, {'proof': 'pob'})) == '' and len(n) == 2   # tried twice, then a pass


def test_a_slow_mind_never_blanks_the_other():
    async def fast():
        return 'A answered'

    async def slow():
        await asyncio.sleep(5); return 'too late'
    assert asyncio.run(fs._minds_ask([fast(), slow()], 0.05)) == ['A answered', '']
