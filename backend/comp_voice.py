"""🗣 COMP VOICE chat (owner 2026-11-15 "yes dooo alll": a chat window for COMP Voice inside FEELESS).

The voice is its own LoRA over the free 9B base (scripts/comp-voice.py trains it). Here it runs as a local MLX server on 127.0.0.1 only, started
and stopped by the owner from the COMP folder; it stops itself after IDLE_SEC without a question so 5 GB of model does not sit in memory.
Thinking is OFF both ways: the rows are trained with Qwen's empty think block, and the server renders every prompt with enable_thinking=False.
Pure parts (the request body, the reply clean-up, the chat log, idle rules) are tested; the server shells out to `.venv-mlx`.
"""
import json
import os
import re
import signal
import socket
import subprocess
import time
from pathlib import Path

import comp_v2 as _c2

DIR = _c2.ROOT / 'data' / 'comp_voice'
HOST, PORT = '127.0.0.1', 5131   # 5111 is the Circle signer, 5112 its agent twin: never those
IDLE_SEC = 20 * 60
TURNS = 8            # how many past turns ride along with a question
KEEP = 60            # the chat log keeps this many messages
MAX_Q = 1200
SYSTEM = ("You are COMP, FEELESS's own AI: a degen web3 brain with a smart mouth. You talk like a trencher who actually read the docs: short, blunt, "
          "funny, numbers first. You know Solana, perps, prediction markets and FEELESS inside out. You never help anyone rug, drain, scam or "
          "front-run people, and you never ask for or repeat keys, seed phrases or private details. When you are not sure, you say so.")
THINK = re.compile(r'<think>.*?(</think>|$)', re.S)


def adapter(folder=None):
    """The picked adapter (best/) if there is one, else the last run's."""
    folder = Path(folder or DIR)
    for d in (folder / 'best', folder / 'adapter'):
        if (d / 'adapters.safetensors').exists():
            return d
    return None


def server_cmd(folder=None):
    a = adapter(folder)
    return [str(_c2.MLX_PY), '-m', 'mlx_lm', 'server', '--model', str(_c2.BASE), '--adapter-path', str(a), '--host', HOST, '--port', str(PORT),
            '--chat-template-args', json.dumps({'enable_thinking': False}), '--temp', '0.7', '--top-p', '0.9']


def _j(path, d):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return d


def body(history, text):
    """→ the chat request: the voice's system line, the last TURNS turns, the new question. Thinking off."""
    past = [m for m in (history or []) if m.get('role') in ('user', 'assistant') and m.get('content')][-TURNS * 2:]
    msgs = [{'role': 'system', 'content': SYSTEM}] + [{'role': m['role'], 'content': str(m['content'])[:MAX_Q]} for m in past]
    msgs.append({'role': 'user', 'content': str(text or '').strip()[:MAX_Q]})
    return {'messages': msgs, 'max_tokens': 400, 'temperature': 0.7, 'top_p': 0.9, 'chat_template_kwargs': {'enable_thinking': False}}


def clean(text):
    """A reply with any stray think block (or an unclosed one) and the end token taken out."""
    t = THINK.sub('', str(text or '')).replace('<|im_end|>', '').strip()
    return t or '…'


def add(log, role, content, now=None, **extra):
    return (list(log or []) + [{'role': role, 'content': content, 'at': round(now or time.time()), **extra}])[-KEEP:]


def idle(run, last_ask, now=None):
    """True when the server has sat IDLE_SEC since it started and since the last question."""
    now = now or time.time()
    return bool(run.get('pid')) and now - max(run.get('at') or 0, last_ask or 0) > IDLE_SEC


def rows_count(folder=None):
    folder = Path(folder or DIR); n = 0
    for f in ('train.jsonl', 'valid.jsonl'):
        try:
            n += sum(1 for ln in (folder / f).read_text().splitlines() if ln.strip())
        except OSError:
            pass
    return n


def status(folder=None, now=None):
    folder = Path(folder or DIR); now = now or time.time()
    run = _j(folder / 'voice_run.json', {}) or {}
    chat = _j(folder / 'chat.json', []) or []
    last = max([m.get('at') or 0 for m in chat if m.get('role') == 'user'] or [0])
    up = bool(run.get('pid')) and _c2.alive(run['pid'])
    if up and idle(run, last, now):
        stop(folder); up = False
    a = adapter(folder)
    return {'ready': bool(a) and _c2.BASE.exists() and _c2.MLX_PY.exists(), 'adapter': a.name if a else '',
            'trainedAt': round(os.path.getmtime(a / 'adapters.safetensors')) if a else 0, 'rows': rows_count(folder),
            'running': up, 'since': run.get('at') if up else 0, 'idleMin': IDLE_SEC // 60, 'base': _c2.BASE_NAME, 'chat': chat[-KEEP:]}


def port_taken(host=None, port=None):
    with socket.socket() as k:
        k.settimeout(0.5)
        return k.connect_ex((host or HOST, port or PORT)) == 0


def start(folder=None):
    """Starts the voice server. Refuses when something already listens on its port (a second 9B copy runs the GPU out of memory)."""
    folder = Path(folder or DIR)
    if port_taken():
        raise RuntimeError(f'Port {PORT} is already in use. Sleep the voice first, or free that port.')
    log = open(folder / 'voice.log', 'w')
    hf = folder / 'hf_cache'; hf.mkdir(parents=True, exist_ok=True)   # its /v1/models scans the HF cache and crashes when there is none
    p = subprocess.Popen(server_cmd(folder), stdout=log, stderr=subprocess.STDOUT, cwd=str(_c2.ROOT), start_new_session=True,
                         env={**os.environ, 'PYTHONUNBUFFERED': '1', 'HF_HUB_CACHE': str(hf), 'HF_HUB_OFFLINE': '1'})
    (folder / 'voice_run.json').write_text(json.dumps({'pid': p.pid, 'at': round(time.time())}))
    return p.pid


def stop(folder=None):
    folder = Path(folder or DIR)
    run = _j(folder / 'voice_run.json', {}) or {}
    if run.get('pid') and _c2.alive(run['pid']):
        try:
            os.killpg(os.getpgid(int(run['pid'])), signal.SIGTERM)
        except OSError:
            pass
    (folder / 'voice_run.json').write_text('{}')


def log_tail(folder=None, n=4000):
    try:
        return (Path(folder or DIR) / 'voice.log').read_text(errors='replace')[-n:]
    except OSError:
        return ''


def save_chat(log, folder=None):
    (Path(folder or DIR) / 'chat.json').write_text(json.dumps(log[-KEEP:]))


def load_chat(folder=None):
    return _j(Path(folder or DIR) / 'chat.json', []) or []
