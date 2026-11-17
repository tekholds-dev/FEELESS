"""🧠 The COMP exam asks OSSY + G4 with thinking off and a short answer cap (2026-11-14: both timed out thinking out loud)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comp_v2_exam as ex  # noqa: E402


def test_own_minds_ask_without_thinking(monkeypatch):
    sent = []

    class Res:
        def raise_for_status(self): pass
        def json(self): return {'choices': [{'message': {'content': 'won'}}]}

    class Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def post(self, url, json): sent.append(json); return Res()

    import httpx
    monkeypatch.setattr(httpx, 'Client', Client)
    monkeypatch.setattr(ex.cv, 'prompt_of', lambda r: 'q')
    out = ex.openai_style([{}, {}], 'k', 'http://x/v1', 'qwen/qwen3.5-9b')
    assert len(out) == 2 and len(sent) == 2
    assert all(b['chat_template_kwargs'] == {'enable_thinking': False} and b['max_tokens'] == 300 and b['reasoning_effort'] == 'none' for b in sent)


def test_flagships_without_a_key_sit_the_exam_on_the_owners_openrouter(tmp_path):
    # owner 2026-11-17: "i requested my openrouterkey to be useable with comp and fee aswell"
    import json
    import cat_keys as ck
    store = {'cats': {'fee': {'id': 'fee', 'ownerStaff': True, 'apiKeys': {'openrouter': {'sealed': ck.seal('sk-or-test', 'fee'), 'at': 5}}},
                      'user': {'id': 'user', 'apiKeys': {'openrouter': {'sealed': ck.seal('sk-or-user', 'user'), 'at': 9}}}}}
    p = tmp_path / 'feecats.json'; p.write_text(json.dumps(store))
    assert ex.owner_openrouter(p) == 'sk-or-test'          # an owner agent's key, never a user's
    p.write_text(json.dumps({'cats': {'user': store['cats']['user']}}))
    assert ex.owner_openrouter(p) == '' and ex.owner_openrouter(tmp_path / 'none.json') == ''
    assert set(ex.OR_FLAGSHIP) == {'claude', 'gpt', 'grok'} and all('/' in v for v in ex.OR_FLAGSHIP.values())
