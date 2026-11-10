"""Owner 2026-11-09: the owner's and admins' agents (and Fee) think on SingIt only: SingIt's own models, paid from its wallet, never OpenRouter or Groq."""
import asyncio

import launch_cat as lc

OR_RAW = [{'id': 'z-ai/glm-5.3-flash', 'name': 'Z.ai: GLM 5.3 Flash', 'pricing': {'prompt': '0.00000015', 'completion': '0.0000005'}, 'context_length': 1000},
          {'id': 'z-ai/glm-5.3-flash:free', 'name': 'GLM free', 'pricing': {'prompt': '0', 'completion': '0'}},
          {'id': 'openai/gpt-only-on-or', 'name': 'Only on OpenRouter', 'pricing': {'prompt': '0.000001', 'completion': '0.000002'}}]
SINGIT = {'data': [
    {'id': 'glm-5.3-flash', 'name': 'GLM 5.3 Flash', 'modality': 'chat', 'available': True, 'singitUsdPerMillionTokens': {'input': 0.009, 'output': 0.03}},
    {'id': 'hy4', 'name': 'Hy4', 'modality': 'chat', 'available': True, 'usdPerMillionTokens': {'input': 0.2, 'output': 0.8}, 'contextLength': 256000},
    {'id': 'free/deepseek-v4.1-flash', 'modality': 'chat', 'available': True, 'free': True},   # the free tier is the stand-in route, not a pick
    {'id': 'singit/auto', 'modality': 'chat', 'available': True, 'router': True},
    {'id': 'down-model', 'modality': 'chat', 'available': False},
    {'id': 'minimax/music-2', 'modality': 'music', 'available': True}]}


def test_singit_list_reuses_the_openrouter_row_at_singit_price():
    c = lc.singit_catalog(SINGIT, lc.catalog(OR_RAW)['models'])
    by = {m['id']: m for m in c['models']}
    assert c['via'] == 'singit' and set(by) == {'z-ai/glm-5.3-flash', 'singit/hy4'}   # Happy's own id still matches; OpenRouter-only models are gone
    g = by['z-ai/glm-5.3-flash']
    assert (g['name'], g['inUsd'], g['outUsd'], g['singit'], g['free']) == ('Z.ai: GLM 5.3 Flash', 0.009, 0.03, 'glm-5.3-flash', False)
    assert g['perDecision'] < lc.catalog(OR_RAW)['models'][0]['perDecision']   # priced at SingIt's rate, not OpenRouter's
    tiny = lc.singit_catalog({'data': [{'id': 'oss-tiny', 'modality': 'chat', 'available': True, 'singitUsdPerMillionTokens': {'input': 0.00004, 'output': 0.0001}}]}, [])['models'][0]
    assert tiny['free'] is False and tiny['perTask'] > 0   # a tiny price is still a price (found on the live list: gpt-oss-20b read 'free')
    assert by['singit/hy4']['ctx'] == 256000 and {x['key'] for x in c['cats']} == set(lc.CATS)


def test_staff_pick_from_singits_list_everyone_else_from_openrouters(monkeypatch):
    import feecat_service as fs
    async def or_m():
        return {'models': [{'id': 'openai/gpt-only-on-or'}]}
    async def sg_m():
        return {'models': [{'id': 'z-ai/glm-5.3-flash'}], 'via': 'singit'}
    monkeypatch.setattr(fs, '_or_models', or_m); monkeypatch.setattr(fs, '_singit_models', sg_m)
    assert asyncio.run(fs._model_ids({'ownerStaff': True})) == {'z-ai/glm-5.3-flash'}
    assert asyncio.run(fs._model_ids({'isLeader': True})) == {'z-ai/glm-5.3-flash'}
    assert asyncio.run(fs._model_ids({'ownerId': 'someone'})) == {'openai/gpt-only-on-or'}


def _routes(fs, monkeypatch, singit_text):
    hit = []
    async def wallet_call(cat, model, messages, max_tokens, ceiling):
        hit.append('singit'); return (singit_text, 0.002 if singit_text else 0.0)
    async def or_call(model, messages, **k):
        hit.append('openrouter:' + model); return ('or answer', 0.01)
    async def sing_free(messages, max_tokens):
        hit.append('singit free'); return ''
    async def groq(messages, max_tokens):
        hit.append('groq'); return 'groq answer'
    monkeypatch.setattr(fs, '_wallet_call', wallet_call); monkeypatch.setattr(fs, '_or_call', or_call)
    monkeypatch.setattr(fs, '_singit_free', sing_free); monkeypatch.setattr(fs, '_groq_backup', groq)
    monkeypatch.setattr(fs, '_brains_live', lambda: True); monkeypatch.setattr(fs, '_pays_itself', lambda c: True)
    return hit


def test_a_staff_agent_never_reaches_openrouter_or_groq(monkeypatch):
    import feecat_service as fs
    hit = _routes(fs, monkeypatch, '')   # SingIt paid fails
    staff = {'id': 'h', 'ownerStaff': True}
    assert asyncio.run(fs._think_routes(staff, 'z-ai/glm-5.3-flash', [{'role': 'user', 'content': 'hi'}]))[0] == ''
    assert hit == ['singit', 'singit free']   # no OpenRouter, no Groq: it says it could not answer instead
    hit.clear()
    assert asyncio.run(fs._think_routes(staff, 'local/ossy', [{'role': 'user', 'content': 'hi'}]))[2] == 'local'   # the owner's own LM Studio still answers
    hit.clear()
    user = {'id': 'u', 'ownerId': 'someone'}
    assert asyncio.run(fs._think_routes(user, 'z-ai/glm-5.3-flash', [{'role': 'user', 'content': 'hi'}]))[2] == 'openrouter'   # a user's agent is unchanged
    hit2 = _routes(fs, monkeypatch, 'paid answer')
    assert asyncio.run(fs._think_routes(staff, 'z-ai/glm-5.3-flash', [{'role': 'user', 'content': 'hi'}]))[:3:2] == ('paid answer', 'singit') and hit2 == ['singit']
