"""🧪 MODEL LAB routes (owner only): the live dataset for FEELESS's own model, the human review queue, and the clean export.
The logic is `model_lab` (pure); this file only reads the stash, the model-call log and the owner's grades, and saves a grade.
Nothing here trains, spends or sends anything: the export comes back to the owner's own browser as a file."""
import json
import time

from fastapi import APIRouter, Request
from pydantic import BaseModel

import model_lab as _ml

router = APIRouter()
CALLS_MAX = 20000   # the model-call log is read from its newest end, at most this many lines


def _rs():
    import reputation_service
    return reputation_service


def _paths(rs):
    return rs.DATA_DIR / 'stash', rs.DATA_DIR / 'mind_calls.jsonl', rs.DATA_DIR / 'model_lab_grades.json'


def _calls(path):
    try:
        lines = path.read_text(errors='ignore').splitlines()[-CALLS_MAX:]
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def _view(rs):
    stash, calls, grades_p = _paths(rs)
    items = rs._stash.catalog(stash); grades = rs._json_load(grades_p, {})
    return {**_ml.summary(items, _calls(calls), grades), 'queue': _ml.queue(items, grades), 'at': round(time.time())}


@router.get('/api/reputation/admin/model-lab')
async def model_lab_view(request: Request):
    """🧪 The dataset as it stands, the rented minds' real record and the next proofs waiting for the owner's grade."""
    rs = _rs()
    rs._require_owner(request)
    return await rs.asyncio.to_thread(_view, rs)


class Grade(BaseModel):
    key: str
    verdict: str
    note: str = ''


@router.post('/api/reputation/admin/model-lab/grade')
async def model_lab_grade(request: Request, g: Grade):
    """👍 / 👎 / skip on one open proof: the human label a model learns from where no market settled it."""
    rs = _rs()
    rs._require_owner(request)
    _, _, grades_p = _paths(rs)
    try:
        nxt = _ml.grade(rs._json_load(grades_p, {}), g.key, g.verdict, g.note, time.time())
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    await rs.asyncio.to_thread(rs._json_save, grades_p, nxt)
    return await rs.asyncio.to_thread(_view, rs)


def _export(rs):
    stash, _, grades_p = _paths(rs)
    items = rs._stash.catalog(stash); grades = rs._json_load(grades_p, {})
    return [json.loads(x) for x in _ml.export_lines(items, lambda k: rs._stash.read(stash, k), grades)]


@router.get('/api/reputation/admin/model-lab/export')
async def model_lab_export(request: Request):
    """⬇ Every clean training row (scrubbed of wallets, addresses, emails, phones and keys). The page saves it as a .jsonl file."""
    rs = _rs()
    rs._require_owner(request)
    rows = await rs.asyncio.to_thread(_export, rs)
    return {'rows': rows, 'count': len(rows), 'at': round(time.time())}


# ─── 🏗 MODEL FORGE: build the owner's own model on this Mac (model_forge.py is the engine) ────────────────────────────────────────────────
import os
import re
import subprocess
import sys



def _mf():
    """The engine needs numpy: imported on first use, so this service always starts (2026-11-12: a top-level import took 5077 down)."""
    import model_forge
    return model_forge

FORGE_MAX_KEEP = 12          # builds kept on disk; the oldest finished one goes first
EXTRA_MAX = 400_000          # characters the owner may paste on top of the proofs


def _forge_dir(rs):
    d = rs.DATA_DIR / 'model_forge'; d.mkdir(parents=True, exist_ok=True); return d


SOURCES = {'proofs': 'Your proofs (every kept proof, open ones too)', 'pow': 'PoW research notes (plans, reasons, calls)', 'docs': 'FEELESS docs (plans, decisions, the build history)'}
DOCS_MAX = 1_500_000


def _sources(rs):
    """→ {source: text}. Everything is scrubbed (wallets, keys, emails, phones); the agents' sealed workspaces are never read."""
    out = {'proofs': _proof_text(rs), 'pow': '', 'docs': ''}
    rows = []
    try:
        for ln in (rs.DATA_DIR / 'pow_archive.jsonl').read_text(errors='ignore').splitlines():
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            body = [f'{k}: {_ml.scrub(" ".join(str(r[k]).split()))[:1500]}' for k in ('plan', 'why', 'call') if isinstance(r.get(k), str) and r[k].strip()]
            if body:
                rows.append(f"### PoW {r.get('kind') or ''} · ${_ml.scrub(str(r.get('sym') or ''))[:16]}\n" + '\n'.join(body) + '\n')
    except OSError:
        pass
    out['pow'] = '\n'.join(rows)
    docs, size = [], 0
    for f in sorted((rs.Path(__file__).resolve().parent.parent / 'docs').glob('*.md'), key=lambda f: f.stat().st_size):
        try:
            s = _ml.scrub(f.read_text(errors='ignore'))
        except OSError:
            continue
        if size + len(s) > DOCS_MAX:
            break
        docs.append(f'### {f.stem}\n{s}\n'); size += len(s)
    out['docs'] = '\n'.join(docs)
    return out


def _corpus(rs, sources=('proofs', 'pow', 'docs')):
    got = _sources(rs)
    return '\n'.join(got[k] for k in SOURCES if k in (sources or ()) and got.get(k))


def _proof_text(rs):
    """Every kept proof's own words (settled or open, scrubbed) and the owner's grade notes, one block per proof."""
    stash, _, grades_p = _paths(rs); grades = rs._json_load(grades_p, {}); blocks = []
    for it in rs._stash.catalog(stash):
        try:
            raw = rs._stash.read(stash, it['key']) or b''
        except Exception:   # noqa: BLE001 — a sealed item that will not open still gives its title
            raw = b''
        b = _ml.text_of(it, raw)
        if b:
            note = (grades.get(it.get('key')) or {}).get('note')
            blocks.append(b + (f'owner: {_ml.scrub(note)}\n' if note else ''))
    return '\n'.join(blocks)


def _job_view(d):
    p = rs_json(d / 'progress.json'); card = rs_json(d / 'card.json')
    return {'id': d.name, 'status': p.get('status') or ('done' if card else 'queued'), 'step': p.get('step'), 'steps': p.get('steps'),
            'loss': p.get('loss'), 'val': p.get('val'), 'tps': p.get('tps'), 'eta': p.get('eta'), 'elapsed': p.get('elapsed'),
            'history': p.get('history') or [], 'error': p.get('error'), 'spec': p.get('spec'), 'card': card or None,
            'name': (card or {}).get('name') or (rs_json(d / 'job.json').get('cfg') or {}).get('name')}


def rs_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _alive(d):
    pid = rs_json(d / 'progress.json').get('pid')
    if not pid or rs_json(d / 'progress.json').get('status') not in ('tokenizing', 'training'):
        return False
    try:
        os.kill(int(pid), 0); return True
    except (OSError, ValueError):
        return False


def _job_dir(rs, jid):
    if not re.fullmatch(r'\d{8}-\d{6}-[a-z0-9-]{0,20}', jid or ''):
        raise rs.HTTPException(404, 'No such build.')
    return _forge_dir(rs) / jid


def _jobs(rs):
    return sorted((d for d in _forge_dir(rs).iterdir() if d.is_dir() and (d / 'job.json').exists()), key=lambda d: d.name, reverse=True)


@router.get('/api/reputation/admin/model-lab/forge')
async def forge_view(request: Request):
    """🏗 What a build would learn from (live), the presets and limits, and every build with its progress or model card."""
    rs = _rs(); rs._require_owner(request)
    def go():
        got = _sources(rs); text = '\n'.join(got.values()); tok = _mf().CharTok.train(text)
        return {'corpus': {'chars': len(text), 'charVocab': tok.size, 'blocks': text.count('### '), 'preview': text[:600]},
                'sources': [{'k': k, 'label': SOURCES[k], 'chars': len(got[k]), 'blocks': got[k].count('### ')} for k in SOURCES],
                'presets': _mf().PRESETS, 'limits': _mf().LIMITS, 'rails': _mf().RAILS_DEFAULT,
                'jobs': [_job_view(d) for d in _jobs(rs)], 'running': next((d.name for d in _jobs(rs) if _alive(d)), None)}
    return await rs.asyncio.to_thread(go)


class ForgeSpec(BaseModel):
    cfg: dict = {}
    extra: str = ''
    sources: list = ['proofs', 'pow', 'docs']


@router.post('/api/reputation/admin/model-lab/forge/spec')
async def forge_spec(request: Request, p: ForgeSpec):
    """📐 The blueprint's specs before anything runs: parameters per part, memory, compute, data per parameter, an estimated time."""
    rs = _rs(); rs._require_owner(request)
    def go():
        text = _corpus(rs, p.sources) + '\n' + p.extra[:EXTRA_MAX]; c = _mf().clean_cfg(p.cfg)
        vocab = _mf().CharTok.train(text).size if c['tok'] == 'char' else c['vocab']
        toks = len(text) if c['tok'] == 'char' else int(len(text) / 3.2)   # BPE ≈ 3.2 characters a token on this text (the build counts exactly)
        return _mf().spec(c, vocab, toks)
    return await rs.asyncio.to_thread(go)


class ForgeBuild(BaseModel):
    cfg: dict = {}
    rails: dict = {}
    extra: str = ''
    sources: list = ['proofs', 'pow', 'docs']


@router.post('/api/reputation/admin/model-lab/forge/build')
async def forge_build(request: Request, p: ForgeBuild):
    """🔨 Start one build: its own niced process on this Mac (one at a time), so the site keeps its speed. Nothing is rented or spent."""
    rs = _rs(); rs._require_owner(request)
    if any(_alive(d) for d in _jobs(rs)):
        raise rs.HTTPException(409, 'A build is already running. Stop it or wait for it.')
    c = _mf().clean_cfg(p.cfg); text = _corpus(rs, p.sources) + '\n' + p.extra[:EXTRA_MAX]
    vocab = _mf().CharTok.train(text).size if c['tok'] == 'char' else c['vocab']
    if _mf().n_params(c, vocab)['total'] > _mf().LIMITS['params']:
        raise rs.HTTPException(400, 'Too big for this Mac: lower the width or layers.')
    jid = time.strftime('%Y%m%d-%H%M%S') + '-' + re.sub(r'[^a-z0-9]+', '-', c['name'].lower()).strip('-')[:20]
    d = _forge_dir(rs) / jid; d.mkdir()
    (d / 'corpus.txt').write_text(text); (d / 'job.json').write_text(json.dumps({'cfg': c, 'rails': _mf().clean_rails(p.rails), 'sample_prompt': '### PoW · won · '}))
    env = {**os.environ, 'VECLIB_MAXIMUM_THREADS': '4', 'OMP_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4'}
    subprocess.Popen([sys.executable, str(rs.Path(_mf().__file__)), 'train', str(d)], cwd=str(rs.Path(_mf().__file__).parent), env=env,
                     stdout=subprocess.DEVNULL, stderr=open(d / 'build.log', 'w'), start_new_session=True, preexec_fn=lambda: os.nice(10))
    done = [x for x in _jobs(rs) if not _alive(x)]
    for old in done[FORGE_MAX_KEEP:]:
        rs.shutil.rmtree(old, ignore_errors=True)
    return {'id': jid, 'spec': _mf().spec(c, vocab, len(text))}


@router.get('/api/reputation/admin/model-lab/forge/{jid}')
async def forge_job(request: Request, jid: str):
    rs = _rs(); rs._require_owner(request)
    d = _job_dir(rs, jid)
    if not (d / 'job.json').exists():
        raise rs.HTTPException(404, 'No such build.')
    return {**_job_view(d), 'alive': _alive(d)}


@router.post('/api/reputation/admin/model-lab/forge/{jid}/stop')
async def forge_stop(request: Request, jid: str):
    """⏹ Ends a build at its next step; the weights it reached are saved and can be tried."""
    rs = _rs(); rs._require_owner(request)
    d = _job_dir(rs, jid)
    if not (d / 'job.json').exists():
        raise rs.HTTPException(404, 'No such build.')
    (d / 'stop').write_text('1')
    return {'ok': True}


class ForgeAsk(BaseModel):
    prompt: str = ''
    temperature: float = 0.8
    max_new: int = 200
    rails: dict | None = None


@router.post('/api/reputation/admin/model-lab/forge/{jid}/ask')
async def forge_ask(request: Request, jid: str, p: ForgeAsk):
    """💬 Ask a built model. Its guardrails wrap the answer and say which rule fired; the raw answer is shown next to it."""
    rs = _rs(); rs._require_owner(request)
    d = _job_dir(rs, jid)
    if not (d / 'card.json').exists():
        raise rs.HTTPException(404, 'That build has no model yet.')
    def go():
        P, c, tok, card = _mf().load(d); rails = _mf().clean_rails(p.rails if p.rails is not None else card.get('rails'))
        refused, fired = _mf().guard(p.prompt, '', {**rails, 'block': [], 'scrub': False, 'footer': '', 'max_chars': 4000})
        if fired:
            return {'answer': refused, 'raw': '', 'fired': fired, 'ms': 0}
        t0 = time.time(); raw = _mf().generate(P, c, tok, p.prompt[:2000], max_new=min(600, max(10, p.max_new)), temperature=min(2.0, max(0.1, p.temperature)))
        answer, fired = _mf().guard(p.prompt, raw, rails)
        return {'answer': answer, 'raw': raw, 'fired': fired, 'ms': round((time.time() - t0) * 1000)}
    return await rs.asyncio.to_thread(go)
