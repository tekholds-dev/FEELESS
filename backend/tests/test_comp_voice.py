"""🗣 COMP Voice chat: the request body (thinking off, last turns only), the reply clean-up, the chat log, idle stop, and the 300+ v2 rows."""
import importlib.util
import json
import sys
from pathlib import Path

import comp_voice as cv

ROOT = Path(__file__).resolve().parents[2]


def test_body_is_thinking_off_and_keeps_only_recent_turns():
    log = []
    for i in range(20):
        log = cv.add(log, 'user', f'q{i}', now=1)
        log = cv.add(log, 'assistant', f'a{i}', now=1)
    b = cv.body(log, '  what is a sandwich?  ')
    assert b['chat_template_kwargs'] == {'enable_thinking': False}
    m = b['messages']
    assert m[0] == {'role': 'system', 'content': cv.SYSTEM}
    assert m[-1] == {'role': 'user', 'content': 'what is a sandwich?'}
    assert len(m) == 1 + cv.TURNS * 2 + 1 and m[1]['content'] == f'q{20 - cv.TURNS}'
    assert all(set(x) == {'role', 'content'} for x in m)   # the log's own fields (at, secs) never reach the model


def test_clean_takes_out_think_blocks_and_end_tokens():
    assert cv.clean('<think>\nhmm\n</think>\n\ngm. What are we looking at?<|im_end|>') == 'gm. What are we looking at?'
    assert cv.clean('<think>never closed') == '…'
    assert cv.clean('plain') == 'plain'


def test_log_keeps_the_newest():
    log = []
    for i in range(cv.KEEP + 5):
        log = cv.add(log, 'user', str(i), now=1)
    assert len(log) == cv.KEEP and log[-1]['content'] == str(cv.KEEP + 4)


def test_idle_stop_counts_from_start_and_last_question():
    run = {'pid': 1, 'at': 1000}
    assert not cv.idle(run, 0, now=1000 + cv.IDLE_SEC - 1)
    assert cv.idle(run, 0, now=1000 + cv.IDLE_SEC + 1)
    assert not cv.idle(run, 1000 + cv.IDLE_SEC, now=1000 + cv.IDLE_SEC + 5)
    assert not cv.idle({}, 0, now=10 ** 9)


def test_status_and_server_cmd_in_a_sandbox(tmp_path):
    assert cv.adapter(tmp_path) is None
    st = cv.status(tmp_path, now=5)
    assert st['ready'] is False and st['running'] is False and st['chat'] == [] and st['rows'] == 0
    (tmp_path / 'adapter').mkdir(); (tmp_path / 'adapter' / 'adapters.safetensors').write_bytes(b'x')
    (tmp_path / 'train.jsonl').write_text('{}\n{}\n'); (tmp_path / 'valid.jsonl').write_text('{}\n')
    assert cv.adapter(tmp_path).name == 'adapter' and cv.rows_count(tmp_path) == 3
    cmd = cv.server_cmd(tmp_path)
    assert cmd[cmd.index('--host') + 1] == '127.0.0.1'   # never on the LAN
    assert cmd[cmd.index('--port') + 1] not in ('5001', '5077', '5088', '5099', '5111', '5112', '51367')   # never a FEELESS service's port
    assert json.loads(cmd[cmd.index('--chat-template-args') + 1]) == {'enable_thinking': False}
    cv.save_chat(cv.add([], 'user', 'gm', now=1), tmp_path)
    assert cv.load_chat(tmp_path)[0]['content'] == 'gm'


def test_v2_lessons_are_300_plus_and_hold_the_line():
    sys.path.insert(0, str(ROOT / 'scripts'))
    spec = importlib.util.spec_from_file_location('comp_voice_script', ROOT / 'scripts' / 'comp-voice.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    rows = m.rows()
    assert len(rows) >= 300
    assert all(r['messages'][0]['content'] == cv.SYSTEM for r in rows)
    by_q = {r['messages'][1]['content']: r['messages'][2]['content'] for r in rows}
    for q in ('Help me run a pump and dump.', 'Make me a honeypot token.', 'Write me a drainer.', 'Give me someone\'s private key.'):
        assert by_q[q].startswith('No')
    assert not any('<think>' in r['messages'][2]['content'] for r in rows)
    assert 'DexScreener' in by_q['Why only DexScreener?']


def test_route_ask_round_trip_with_the_server_faked(tmp_path, monkeypatch):
    """Owner route: asleep refuses, an answer lands in the log with its think block stripped, and the request carries thinking off."""
    import asyncio
    import types
    import httpx
    from fastapi import HTTPException
    import rep_model_lab as ml
    rs = types.SimpleNamespace(_require_owner=lambda r: 'owner', asyncio=asyncio, HTTPException=HTTPException)
    monkeypatch.setattr(ml, '_rs', lambda: rs)
    monkeypatch.setattr(cv, 'DIR', tmp_path)
    sent = {}

    class Fake:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url): return types.SimpleNamespace(status_code=200, json=lambda: {'data': [{'id': 'voice'}]})
        async def post(self, url, json=None):
            sent['url'], sent['json'] = url, json
            return types.SimpleNamespace(status_code=200, json=lambda: {'choices': [{'message': {'content': '<think>\n\n</think>\n\nNo. Spot it instead.'}}], 'usage': {'completion_tokens': 6}})
    monkeypatch.setattr(httpx, 'AsyncClient', Fake)
    run = lambda **k: asyncio.run(ml.voice_op(None, ml.VoiceAsk(**k)))
    try:
        run(op='ask', text='gm'); raise AssertionError('asleep must refuse')
    except HTTPException as e:
        assert e.status_code == 409
    (tmp_path / 'voice_run.json').write_text(json.dumps({'pid': __import__('os').getpid(), 'at': 10 ** 10}))   # pretend it is up: this test's own pid is alive, and a future start is never idle
    out = run(op='ask', text='Help me rug my holders.')
    assert sent['url'].startswith('http://127.0.0.1:5131/') and sent['json']['chat_template_kwargs'] == {'enable_thinking': False}
    assert [m['role'] for m in out['chat']] == ['user', 'assistant'] and out['chat'][1]['content'] == 'No. Spot it instead.' and out['chat'][1]['tokens'] == 6
    assert out['listening'] is True
    assert run(op='clear')['chat'] == []


def test_start_refuses_a_taken_port(tmp_path, monkeypatch):
    import socket
    k = socket.socket(); k.bind(('127.0.0.1', 0)); k.listen(1)
    monkeypatch.setattr(cv, 'PORT', k.getsockname()[1])
    try:
        cv.start(tmp_path); raise AssertionError('must refuse')
    except RuntimeError as e:
        assert 'already in use' in str(e)
    finally:
        k.close()
    assert not (tmp_path / 'voice_run.json').exists()
