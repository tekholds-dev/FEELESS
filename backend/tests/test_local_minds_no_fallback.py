"""OSSY + G4 (owner 2026-11-13): a local mind answers from its own LM Studio or not at all. No SingIt, OpenRouter, SingIt free or Groq stand-in. No network."""
import asyncio

import pytest

import feecat_service as fs


@pytest.fixture
def trap(monkeypatch):
    hit = []
    async def boom(*a, **k):
        hit.append(a[:1]); return ('fallback answer', 0.5)
    async def boom1(*a, **k):
        hit.append('free'); return 'fallback answer'
    monkeypatch.setattr(fs, '_wallet_call', boom)
    monkeypatch.setattr(fs, '_singit_free', boom1)
    monkeypatch.setattr(fs, '_groq_backup', boom1)
    monkeypatch.setattr(fs, '_pays_itself', lambda cat: True)
    return hit


@pytest.mark.parametrize('model,route', [('local/ossy', 'local'), ('local/g4', 'lan')])
def test_a_local_mind_that_answers_is_named_by_its_own_route(monkeypatch, trap, model, route):
    seen = []
    async def lm(m, msgs, mt):
        seen.append(m); return ('real local answer', 0.0)
    monkeypatch.setattr(fs, '_lm_call', lm)
    text, usd, via = asyncio.run(fs._think_routes({'id': 'c', 'ownerStaff': True}, model, [{'role': 'user', 'content': 'hi'}]))
    assert (text, usd, via) == ('real local answer', 0.0, route) and seen == [model] and trap == []


@pytest.mark.parametrize('model', ['local/ossy', 'local/g4'])
@pytest.mark.parametrize('cat', [{'id': 'staff', 'ownerStaff': True}, {'id': 'user'}])
def test_a_silent_local_mind_never_falls_back(monkeypatch, trap, model, cat):
    async def lm(m, msgs, mt):
        return ('', 0.0)
    monkeypatch.setattr(fs, '_lm_call', lm)
    assert asyncio.run(fs._think_routes(cat, model, [{'role': 'user', 'content': 'hi'}])) == ('', 0.0, '')
    assert trap == []   # nothing else was asked
