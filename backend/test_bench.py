"""🧪 The test bench ledger (owner 2026-11-12: "if u testing on sicarios then any tests etc should show in folder etc so i can see").

Every test a Claude (or a script) runs on an agent's desk is filed here: what was tested, which models, what came back, the real cost and
time, pass / fail and why, plus the raw outputs as files. Append-only JSONL per agent, so a script can file while the service runs (no
store write, no race), and nothing is ever cleaned away. The desk's Proofs › Test bench tab reads it. Pure file I/O, no network."""
import json
import re
import time
import uuid
from pathlib import Path

MAX_FILE = 400_000      # one output file, bytes
MAX_FILES = 8
KINDS = ('3d', 'static', 'poc', 'pow', 'pob', 'pop', 'poe', 'fix', 'watch', 'ui', 'other')


def _dir(data_dir, cat_id):
    return Path(data_dir) / 'test_runs' / re.sub(r'[^a-z0-9]', '', str(cat_id).lower())[:40]


def _safe_name(n):
    n = re.sub(r'[^A-Za-z0-9._-]+', '-', str(n or 'file')).strip('-.')[:60]
    return n or 'file'


def file_run(data_dir, cat_id, *, kind, title, ok, why, models=(), cost_usd=0.0, secs=None, steps=(), files=None, by='Claude', now=None):
    """Files one test run. → the row. `files` = {name: text}; each is kept beside the row and listed on it."""
    if not str(title or '').strip():
        raise ValueError('A test needs a title.')
    now = float(now or time.time()); rid = uuid.uuid4().hex[:12]; base = _dir(data_dir, cat_id); base.mkdir(parents=True, exist_ok=True)
    kept = []
    for name, text in list((files or {}).items())[:MAX_FILES]:
        nm = _safe_name(name); body = str(text or '').encode('utf-8')[:MAX_FILE]
        (base / rid).mkdir(exist_ok=True); (base / rid / nm).write_bytes(body); kept.append({'name': nm, 'bytes': len(body)})
    row = {'id': rid, 'at': round(now), 'kind': kind if kind in KINDS else 'other', 'title': str(title)[:140], 'ok': bool(ok), 'why': str(why or '')[:600],
           'models': [str(m)[:60] for m in list(models)[:6]], 'costUsd': round(float(cost_usd or 0), 6), 'secs': None if secs is None else round(float(secs), 1),
           'steps': [str(s)[:240] for s in list(steps)[:12]], 'files': kept, 'by': str(by)[:40]}
    with (base / 'runs.jsonl').open('a') as fh:
        fh.write(json.dumps(row) + '\n')
    return row


def runs(data_dir, cat_id, limit=60):
    """→ newest first. A torn last line (a script stopped mid-write) is skipped, never fatal."""
    p = _dir(data_dir, cat_id) / 'runs.jsonl'
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get('id'):
            out.append(r)
    return sorted(out, key=lambda r: -float(r.get('at') or 0))[:max(1, int(limit))]


def read_file(data_dir, cat_id, rid, name):
    """→ the text of one kept output, or None. Names and ids are checked so nothing outside the run's own folder is read."""
    if not re.fullmatch(r'[0-9a-f]{12}', str(rid or '')) or _safe_name(name) != name:
        return None
    p = _dir(data_dir, cat_id) / rid / name
    return p.read_text(errors='replace') if p.is_file() else None


def stats(rows):
    """The bench at a glance: runs, passed, failed, $ spent, seconds."""
    return {'runs': len(rows), 'passed': sum(1 for r in rows if r.get('ok')), 'failed': sum(1 for r in rows if not r.get('ok')),
            'costUsd': round(sum(float(r.get('costUsd') or 0) for r in rows), 6), 'secs': round(sum(float(r.get('secs') or 0) for r in rows), 1)}
