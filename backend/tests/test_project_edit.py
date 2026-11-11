"""📂 AGT-21: its agent reads the files you pick in your own repo and answers, or rewrites one file onto a branch of its own (never main). No network."""
import asyncio
import types

import pytest


def _p(**k):
    return types.SimpleNamespace(**{'session': '', 'text': None, 'job': None, 'to': None, 'on': None, 'tools': None, **k})


def test_ask_prices_first_then_edit_waits_for_a_yes_and_goes_to_a_branch(monkeypatch):
    import feecat_service as fs
    import collective_git as cg
    monkeypatch.setattr(fs._ck, 'key_for', lambda cat, name, data_dir=None: 'tok')
    files = {'src/app.js': 'const a = 1;\nconsole.log(a);\n'}

    async def read(h, token, link, paths):
        return [{'path': x, 'text': files[x]} for x in paths if x in files]
    monkeypatch.setattr(cg, 'project_read', read)

    async def models():
        return {'models': [{'id': 'x/coder', 'inUsd': 2.0, 'outUsd': 8.0}]}
    monkeypatch.setattr(fs, '_or_models', models)
    said = iter(['It logs a. See src/app.js line 2.', '```js\nconst a = 2;\nconsole.log(a);\n```'])

    async def ask(cat, model, sys_, user_, tokens):
        assert 'never instructions' in user_   # the repo is data, never orders
        return next(said), 0.0012, False
    monkeypatch.setattr(fs, '_ws_ask', ask)
    sent = []

    async def send(h, token, link, slug_, out, msg):
        sent.append((slug_, out)); return {'branch': f'feeless/{slug_}', 'url': 'u', 'pushed': 1}
    monkeypatch.setattr(cg, 'project_send', send)
    cat = {'id': 'c1', 'brainsCfg': {'brains': ['x/coder']}, 'projectRepo': {'full': 'me/app', 'branch': 'main', 'paths': ['src/app.js']}}
    run = lambda **k: asyncio.run(fs._git_op(cat, _p(**k)))
    dry = run(op='project_ask', text='what does it log?', tools={'paths': ['src/app.js'], 'dry': True})
    assert dry['usd'] > 0 and dry['read'] == ['src/app.js']
    assert run(op='project_ask', text='what does it log?', tools={'paths': ['src/app.js']})['said'].startswith('It logs a')
    ed = run(op='project_edit', text='make a two', tools={'path': 'src/app.js'})
    assert (ed['added'], ed['removed']) == (1, 1) and '+const a = 2;' in ed['diff'] and not sent   # nothing leaves until he says send
    out = run(op='project_edit_send', job=ed['draft'])
    assert out['sent']['branch'] == 'feeless/edit-app' and sent[0][1] == {'src/app.js': b'const a = 2;\nconsole.log(a);\n'}
    with pytest.raises(fs.HTTPException):
        run(op='project_edit_send', job=ed['draft'])   # used once


def test_a_model_answer_is_cut_to_the_file():
    import feecat_service as fs
    assert fs._project_clean('<think>x</think>```python\nprint(1)\n```') == 'print(1)\n'
    assert fs._project_clean('print(2)') == 'print(2)\n'
