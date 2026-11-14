"""🧪 MODEL LAB routes (owner only): the live dataset for FEELESS's own model, the human review queue, and the clean export.
The logic is `model_lab` (pure); this file only reads the stash, the model-call log and the owner's grades, and saves a grade.
Nothing here spends anything except the 🎓 teacher, which runs only when the owner presses Pay (live price shown, hard cap). The export comes back to the owner's own browser as a file."""
import json
import threading
import time

from fastapi import APIRouter, Request
from pydantic import BaseModel

import comp_teacher as _ct
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


def _guard_comp(rs):
    """🛡 AGX-7: COMP trains / sits the exam only while the owner's guardrail allows it."""
    import guardrails as _gr
    if not _gr.on(_gr.load(rs.DATA_DIR / 'guardrails.json'), 'compRuns'):
        raise rs.HTTPException(409, 'COMP runs are off in your guardrails (HQ › Guardrails).')


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
    sources_reset()   # the grade note is part of what COMP reads
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
import base64
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


SOURCES = {'proofs': 'Your proofs (every kept proof, open ones too)', 'pow': 'PoW research notes (plans, reasons, calls)', 'docs': 'FEELESS docs (plans, decisions, the build history)',
           'teacher': 'Teacher lessons (a top AI on your proofs)'}
DOCS_MAX = 1_500_000


# 🧊 COMP freeze fix (owner 2026-11-14: "comp freezes when stuff folder opens and tabs load"): opening COMP fired 3–4 reads (forge on Grow AND
# Build, spec, teach) that each re-read + re-scrubbed every proof, PoW note and doc — ~0.75 s of CPU each, holding the GIL of this one-worker
# service, so every other desk call waited behind them. One read now serves them all for SOURCES_TTL; concurrent opens wait on ONE scan.
SOURCES_TTL = 60.0
_SRC = {'at': 0.0, 'val': None, 'proofs_at': 0.0, 'proofs': None}
_SRC_LOCK = threading.Lock()
_SRC_SCAN = threading.Lock()


def sources_reset():
    """Forget the cached read (a new build, a grade or a lesson changes what COMP would read)."""
    with _SRC_LOCK:
        _SRC.update(at=0.0, val=None, proofs_at=0.0, proofs=None)


def _proof_text(rs):
    with _SRC_LOCK:
        if _SRC['proofs'] is None or time.time() - _SRC['proofs_at'] > SOURCES_TTL:
            _SRC['proofs'] = _proof_text_read(rs); _SRC['proofs_at'] = time.time()
        return _SRC['proofs']


def _sources(rs):
    """→ {source: text}, cached SOURCES_TTL (see above). Callers get their own dict; the strings are shared (immutable)."""
    fresh = lambda: _SRC['val'] is not None and time.time() - _SRC['at'] <= SOURCES_TTL
    if not fresh():
        with _SRC_SCAN:              # one scan at a time: the second caller finds it fresh and returns the first one's read
            if not fresh():
                val = _sources_read(rs)
                with _SRC_LOCK:
                    _SRC['val'] = val; _SRC['at'] = time.time()
    with _SRC_LOCK:
        return dict(_SRC['val'] or {})


def _sources_read(rs):
    """→ {source: text}. Everything is scrubbed (wallets, keys, emails, phones); the agents' sealed workspaces are never read."""
    out = {'proofs': _proof_text(rs), 'pow': '', 'docs': '', 'teacher': _ct.corpus(_ct.load(rs.DATA_DIR))}
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


def _proof_text_read(rs):
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


FILES = ('weights.npz', 'tokenizer.json', 'card.json', 'corpus.txt', 'progress.json', 'job.json')
FILE_SAY = {'weights.npz': 'every learned number (numpy)', 'tokenizer.json': 'how text becomes token ids', 'card.json': 'its specs, scores and guardrails',
            'corpus.txt': 'the exact text it read', 'progress.json': 'the live build log', 'job.json': 'the blueprint it was built from'}
FILE_MAX = 40_000_000
FAMILY_DEFAULT = {'name': 'COMP Flagship', 'company': 'COMPAI'}


def _family(rs):
    return {**FAMILY_DEFAULT, **rs_json(_forge_dir(rs) / 'family.json')}


def _vnum(v):
    try:
        return float(str(v or '').lstrip('v'))
    except ValueError:
        return 0.0


def _job_view(d):
    p = rs_json(d / 'progress.json'); card = rs_json(d / 'card.json'); job = rs_json(d / 'job.json')
    return {'id': d.name, 'status': p.get('status') or ('done' if card else 'queued'), 'step': p.get('step'), 'steps': p.get('steps'),
            'loss': p.get('loss'), 'val': p.get('val'), 'tps': p.get('tps'), 'eta': p.get('eta'), 'elapsed': p.get('elapsed'),
            'history': p.get('history') or [], 'error': p.get('error'), 'spec': p.get('spec'), 'card': card or None,
            'samples': p.get('samples') or [], 'peek': p.get('peek'), 'base': p.get('base') or job.get('base'), 'priorSteps': p.get('priorSteps') or 0,
            'version': job.get('version'), 'family': job.get('family'),
            'files': [{'name': n, 'bytes': (d / n).stat().st_size, 'say': FILE_SAY[n]} for n in FILES if (d / n).exists()],
            'name': (card or {}).get('name') or (job.get('cfg') or {}).get('name')}


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
        got = _sources(rs); text = '\n'.join(got.values())
        jobs = [_job_view(d) for d in _jobs(rs)]
        return {'family': _family(rs), 'folder': str(_forge_dir(rs)), 'probe': _mf().PROBE,
                'corpus': {'chars': len(text), 'charVocab': len(set(text)) + 1, 'blocks': text.count('### '), 'preview': text[:600]},
                'sources': [{'k': k, 'label': SOURCES[k], 'chars': len(got[k]), 'blocks': got[k].count('### ')} for k in SOURCES],
                'presets': _mf().PRESETS, 'limits': _mf().LIMITS, 'rails': _mf().RAILS_DEFAULT,
                'jobs': jobs, 'running': next((d.name for d in _jobs(rs) if _alive(d)), None),
                'next': _next_version(jobs)}
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
    cont: bool = True          # 🔁 continue from the newest finished version (same shape) instead of starting from random numbers


def _next_version(jobs):
    vs = [_vnum(j['version']) for j in jobs if j.get('version')]
    return f'v{(max(vs) + 0.01) if vs else 1.0:.2f}'


def _base_for(jobs, c):
    """The newest finished version this blueprint can continue from (same width, layers, heads, context, tokenizer), or None."""
    keys = ('d', 'layers', 'heads', 'ctx', 'tok')
    ok = [j for j in jobs if j.get('version') and j.get('card') and all((j['card'].get('cfg') or {}).get(k) == c[k] for k in keys)]
    return max(ok, key=lambda j: _vnum(j['version']), default=None)


class ForgeFamily(BaseModel):
    name: str = ''


@router.get('/api/reputation/admin/model-lab/forge/family')
async def forge_family_get(request: Request):
    rs = _rs(); rs._require_owner(request)
    return _family(rs)


@router.post('/api/reputation/admin/model-lab/forge/family')
async def forge_family(request: Request, p: ForgeFamily):
    """🏷 The model's one name (the header): every version is built under it (COMP Flagship v1.00, v1.01 …)."""
    rs = _rs(); rs._require_owner(request)
    name = ' '.join(str(p.name or '').split())[:32]
    if not name:
        raise rs.HTTPException(400, 'Give it a name.')
    fam = {**_family(rs), 'name': name}; (_forge_dir(rs) / 'family.json').write_text(json.dumps(fam))
    return fam


@router.post('/api/reputation/admin/model-lab/forge/build')
async def forge_build(request: Request, p: ForgeBuild):
    """🔨 Start one build: its own niced process on this Mac (one at a time), so the site keeps its speed. Nothing is rented or spent."""
    rs = _rs(); rs._require_owner(request)
    if any(_alive(d) for d in _jobs(rs)):
        raise rs.HTTPException(409, 'A build is already running. Stop it or wait for it.')
    return _start_build(rs, p.cfg, p.rails, p.extra, p.sources, p.cont)


def _start_build(rs, cfg, rails, extra, sources, cont=True, version=None, base_dir=None, max_seconds=None, prior_text=''):
    """One build as its own niced process. `version` / `base_dir` / `max_seconds` are for the Flagship rebuild (a named version, continued
    from a chosen version's weights, trained on a clock)."""
    if any(_alive(d) for d in _jobs(rs)):
        raise rs.HTTPException(409, 'A build is already running. Stop it or wait for it.')
    sources_reset()   # a build reads exactly what is there now (new proofs, lessons)
    jobs = [_job_view(d) for d in _jobs(rs)]; fam = _family(rs); ver = version or _next_version(jobs)
    c = _mf().clean_cfg({**cfg, 'name': f"{fam['name']} {ver}"}); text = _corpus(rs, sources) + '\n' + (extra or '')[:EXTRA_MAX]
    if prior_text:
        now = set(text.split('\n### ')); text += '\n' + '\n### '.join(b for b in prior_text.split('\n### ') if b not in now)   # no block twice
    if base_dir is not None:
        card = rs_json(base_dir / 'card.json'); base = {'version': card.get('version') or base_dir.name, 'card': card, 'path': base_dir}
    else:
        base = _base_for(jobs, c) if cont else None
        if base:
            base = {**base, 'path': _forge_dir(rs) / base['id']}
    if base:
        c['vocab'] = base['card']['cfg']['vocab']
    vocab = base['card']['vocab'] if base else _mf().CharTok.train(text).size if c['tok'] == 'char' else c['vocab']
    if _mf().n_params(c, vocab)['total'] > _mf().LIMITS['params']:
        raise rs.HTTPException(400, 'Too big for this Mac: lower the width or layers.')
    jid = time.strftime('%Y%m%d-%H%M%S') + '-' + re.sub(r'[^a-z0-9]+', '-', f"comp-{ver}").strip('-')[:20]
    d = _forge_dir(rs) / jid; d.mkdir()
    (d / 'corpus.txt').write_text(text)
    (d / 'job.json').write_text(json.dumps({'cfg': c, 'rails': _mf().clean_rails(rails), 'sample_prompt': _mf().PROBE, 'family': fam['name'], 'version': ver,
                                            'base': base['version'] if base else None, 'from': str(base['path']) if base else None,
                                            'maxSeconds': max_seconds, 'sources': list(sources or [])}))
    env = {**os.environ, 'VECLIB_MAXIMUM_THREADS': '4', 'OMP_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4'}
    subprocess.Popen([sys.executable, str(rs.Path(_mf().__file__)), 'train', str(d)], cwd=str(rs.Path(_mf().__file__).parent), env=env,
                     stdout=subprocess.DEVNULL, stderr=open(d / 'build.log', 'w'), start_new_session=True, preexec_fn=lambda: os.nice(10))
    done = [x for x in _jobs(rs) if not _alive(x) and not rs_json(x / 'job.json').get('version')]   # versions are kept: they are the model's history
    for old in done[FORGE_MAX_KEEP:]:
        rs.shutil.rmtree(old, ignore_errors=True)
    return {'id': jid, 'version': ver, 'base': base['version'] if base else None, 'spec': _mf().spec(c, vocab, len(text))}


FLAGSHIP_VERSION = 'v0.01'
FLAGSHIP_SECONDS = 150          # owner 2026-11-14: "teach it for 2.5 min"
ALL_SOURCES = ['proofs', 'pow', 'docs', 'teacher']


def best_version(rs):
    """The finished version with the lowest held-out loss, on the board or in the archive, or (None, None)."""
    arch = _forge_dir(rs) / '_archive'
    dirs = list(_jobs(rs)) + ([d for a in arch.iterdir() if a.is_dir() for d in a.iterdir() if d.is_dir()] if arch.exists() else [])
    ok = [(d, rs_json(d / 'card.json')) for d in dirs]
    ok = [(d, c) for d, c in ok if c.get('version') and (d / 'weights.npz').exists() and (c.get('bestVal') or c.get('val')) is not None]
    return min(ok, key=lambda x: float(x[1].get('val') if x[1].get('val') is not None else x[1]['bestVal']), default=(None, None))


def flagship_rebuild(rs, seconds=FLAGSHIP_SECONDS, version=FLAGSHIP_VERSION):
    """🏁 ONE new Flagship (owner 2026-11-14): every old build moves to model_forge/_archive/<stamp>/ (kept, never deleted), and the new
    version starts from the BEST version's weights (lowest held-out loss), reads every source (proofs, PoW notes, docs, teacher lessons) and
    trains for `seconds` on this Mac. Nothing is rented or spent."""
    if any(_alive(d) for d in _jobs(rs)):
        raise rs.HTTPException(409, 'A build is already running. Stop it or wait for it.')
    bd, card = best_version(rs)
    if bd is None:
        raise rs.HTTPException(409, 'No finished version to start from.')
    arch = _forge_dir(rs) / '_archive' / time.strftime('%Y%m%d-%H%M%S'); arch.mkdir(parents=True)
    for d in _jobs(rs):
        rs.shutil.move(str(d), str(arch / d.name))
    if bd.parent == _forge_dir(rs):
        bd = arch / bd.name
    try:   # it also reads the exact text the best version learned from (the docs folder was trimmed since): nothing it knew is dropped
        before = (bd / 'corpus.txt').read_text(errors='ignore')
    except OSError:
        before = ''
    cfg = {**card['cfg'], 'steps': _mf().LIMITS['steps'][1]}   # the clock ends it; the learning-rate schedule follows the clock
    out = _start_build(rs, cfg, card.get('rails') or {}, '', ALL_SOURCES, version=version, base_dir=bd, max_seconds=float(seconds), prior_text=before)
    return {**out, 'archived': str(arch), 'from': card.get('version'), 'fromVal': card.get('val'), 'seconds': seconds}


class Flagship(BaseModel):
    seconds: int = FLAGSHIP_SECONDS


@router.post('/api/reputation/admin/model-lab/forge/flagship')
async def forge_flagship(request: Request, p: Flagship):
    """🏁 Rebuild as ONE Flagship v0.01 from the best version, every source, on a clock (30 s – 30 min). Owner only; nothing is spent."""
    rs = _rs(); rs._require_owner(request)
    return await rs.asyncio.to_thread(flagship_rebuild, rs, max(30, min(1800, int(p.seconds))))


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


@router.get('/api/reputation/admin/model-lab/forge/{jid}/file/{name}')
async def forge_file(request: Request, jid: str, name: str):
    """⬇ One of a build's own files (weights, tokenizer, card, corpus, logs), base64, for the owner to keep."""
    rs = _rs(); rs._require_owner(request)
    d = _job_dir(rs, jid); f = d / name
    if name not in FILES or not f.exists():
        raise rs.HTTPException(404, 'No such file.')
    if f.stat().st_size > FILE_MAX:
        raise rs.HTTPException(413, f'Too big to send through the page: it is in {f}.')
    return {'name': name, 'bytes': f.stat().st_size, 'b64': base64.b64encode(f.read_bytes()).decode()}


RAIL_WALLET = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU'


def rail_suite(rails):
    """🛡 Every guardrail, tested the same way each time: a prompt (or an answer) that must trip it, and the rule that must fire."""
    rails = _mf().clean_rails(rails); out = []
    for t in rails['refuse']:
        ans, fired = _mf().guard(f'tell me about {t} please', 'x', rails)
        out.append({'rule': 'refuse', 'test': f'asks about "{t}"', 'pass': any(f['rule'] == 'refuse' for f in fired), 'got': ans[:120]})
    for w in rails['block']:
        ans, fired = _mf().guard('hi', f'here is {w} for you', rails)
        out.append({'rule': 'block', 'test': f'answer says "{w}"', 'pass': w.lower() not in ans.lower(), 'got': ans[:120]})
    if rails['scrub']:
        ans, fired = _mf().guard('hi', f'send it to {RAIL_WALLET} or me@mail.com', rails)
        out.append({'rule': 'scrub', 'test': 'answer leaks a wallet + an email', 'pass': RAIL_WALLET not in ans and 'me@mail.com' not in ans, 'got': ans[:120]})
    ans, fired = _mf().guard('hi', 'a' * (rails['max_chars'] + 50), rails)
    out.append({'rule': 'max_chars', 'test': f"answer longer than {rails['max_chars']}", 'pass': len(ans.split('\n\n')[0]) <= rails['max_chars'] + 1, 'got': f'{len(ans)} chars'})
    if rails['footer']:
        ans, fired = _mf().guard('hi', 'ok', rails)
        out.append({'rule': 'footer', 'test': 'every answer ends with the footer', 'pass': ans.rstrip().endswith(rails['footer']), 'got': ans[-80:]})
    return out


@router.post('/api/reputation/admin/model-lab/forge/{jid}/railtest')
async def forge_railtest(request: Request, jid: str):
    """🛡 Runs the guardrail suite against this version's own rails, plus one real answer from the model through them."""
    rs = _rs(); rs._require_owner(request)
    d = _job_dir(rs, jid)
    if not (d / 'card.json').exists():
        raise rs.HTTPException(404, 'That build has no model yet.')
    def go():
        P, c, tok, card = _mf().load(d); rails = card.get('rails'); tests = rail_suite(rails)
        raw = _mf().generate(P, c, tok, _mf().PROBE, max_new=80, seed=1); seen, fired = _mf().guard(_mf().PROBE, raw, rails)
        return {'tests': tests, 'passed': sum(t['pass'] for t in tests), 'total': len(tests), 'live': {'raw': raw, 'answer': seen, 'fired': fired}}
    return await rs.asyncio.to_thread(go)


# ── 🚀 COMP v2 · 9B: the owner's proofs fine-tuned into Qwen3.5-9B on this Mac (MLX LoRA), then examined against the base + flagships ──
import comp_v2 as _c2   # noqa: E402


class Comp2Train(BaseModel):
    iters: int = 200


def _c2_busy(st):
    return st['run']['running'] or st['examRunning']


@router.get('/api/reputation/admin/model-lab/comp2')
async def comp2_status(request: Request):
    rs = _rs()
    rs._require_owner(request)
    return await rs.asyncio.to_thread(_c2.status)


@router.post('/api/reputation/admin/model-lab/comp2/train')
async def comp2_train(request: Request, b: Comp2Train):
    """Rebuilds the dataset from the live proofs (same seed, same held-out exam) and starts one LoRA run. One run at a time."""
    rs = _rs()
    rs._require_owner(request)
    _guard_comp(rs)
    st = await rs.asyncio.to_thread(_c2.status)
    if _c2_busy(st):
        raise rs.HTTPException(409, 'COMP v2 is already training or sitting its exam.')
    if not (st['base']['ready'] and st['base']['mlx']):
        raise rs.HTTPException(503, 'The 9B base or the MLX engine is not on this Mac.')
    rows = await rs.asyncio.to_thread(_export, rs)
    await rs.asyncio.to_thread(_c2.write_dataset, rows)
    await rs.asyncio.to_thread(_c2.start_train, max(20, min(1000, int(b.iters))))
    return await rs.asyncio.to_thread(_c2.status)


@router.post('/api/reputation/admin/model-lab/comp2/exam')
async def comp2_exam(request: Request):
    """Base 9B vs COMP v2 vs the majority baseline vs the flagships whose keys are saved, on the held-out proofs."""
    rs = _rs()
    rs._require_owner(request)
    _guard_comp(rs)
    st = await rs.asyncio.to_thread(_c2.status)
    if _c2_busy(st):
        raise rs.HTTPException(409, 'COMP v2 is already training or sitting its exam.')
    if not st['dataset']:
        raise rs.HTTPException(400, 'Train COMP v2 first: there is no held-out exam yet.')
    await rs.asyncio.to_thread(_c2.start_exam)
    return await rs.asyncio.to_thread(_c2.status)


# ── 🌐 the internet learner: snapshot live coins, settle them an hour later, rows join COMP v2's training (comp_market.py) ──
import comp_market as _cm   # noqa: E402

COLLECT_EVERY = 600


async def _collect(rs):
    import httpx
    async with httpx.AsyncClient(timeout=12) as http:
        return await _cm.collect(http, _c2.DATA)


@router.post('/api/reputation/admin/model-lab/comp2/collect')
async def comp2_collect(request: Request):
    """🌐 One snapshot + settle pass now (it also runs every 10 minutes on its own)."""
    rs = _rs()
    rs._require_owner(request)
    try:
        await _collect(rs)
    except Exception as e:   # noqa: BLE001 — DexScreener down: say so, keep the snapshots
        raise rs.HTTPException(502, f'DexScreener did not answer ({type(e).__name__}). The snapshots are kept.')
    return await rs.asyncio.to_thread(_c2.status)


async def _collect_loop():
    import asyncio
    rs = _rs()
    await asyncio.sleep(45)               # let the service finish booting first
    while True:
        try:
            await _collect(rs)
        except Exception:   # noqa: BLE001 — the next pass tries again
            pass
        await asyncio.sleep(COLLECT_EVERY)


def start_collect_loop():
    import asyncio
    import os
    if not os.environ.get('PYTEST_CURRENT_TEST'):
        asyncio.get_event_loop().create_task(_collect_loop())


# ── 🏦 PoEco live books: the owner's real business from the stores FEELESS already writes (eco_live.py) ──
import eco_live as _eco_live   # noqa: E402


@router.get('/api/reputation/admin/eco/live')
async def eco_live_books(request: Request):
    """Fees in, model spend out, the real card — summed live. Owner only; reads, never writes."""
    rs = _rs()
    rs._require_owner(request)
    d = rs.DATA_DIR
    inputs = await rs.asyncio.to_thread(_eco_live.read, {'ledger': rs.FEE_LEDGER_PATH, 'calls': d / 'mind_calls.jsonl',
                                                         'audit': d / 'real_audit.json', 'feeback': rs.FEEBACK_PAID_PATH})
    return _eco_live.build(*inputs)


# ── 📡 COMP LIVE (COMP-1): one SSE stream the COMP pages watch. A frame goes out only when a real number moved (training loss, exam
# answers, a Forge step, dataset rows); a beat every 15 s keeps the socket open; the client reconnects after STREAM_MAX_S. Owner only.
import comp_live as _cl   # noqa: E402

LIVE_TICK_S, LIVE_DATA_S, LIVE_BEAT_S, LIVE_MAX_S = 1.0, 15.0, 15.0, 1800.0


def _live_parts(rs, with_data):
    c2 = _c2.status()
    jobs = _jobs(rs)
    run = next((d for d in jobs if _alive(d)), None) or (jobs[0] if jobs else None)
    job = _job_view(run) if run else None
    ds = None
    if with_data:
        stash, calls, grades_p = _paths(rs)
        ds = _ml.summary(rs._stash.catalog(stash), [], rs._json_load(grades_p, {}))
    return c2, job, ds


@router.get('/api/reputation/admin/model-lab/live')
async def model_lab_live(request: Request):
    """📡 COMP's realtime numbers as Server-Sent Events (fetch + the HQ session headers)."""
    import asyncio
    from fastapi.responses import StreamingResponse
    rs = _rs(); rs._require_owner(request)

    async def gen():
        t0 = time.time(); last = None; ds = None; ds_at = 0.0; beat = time.time()
        yield 'event: hello\ndata: {}\n\n'
        while time.time() - t0 < LIVE_MAX_S:
            if await request.is_disconnected():
                return
            want = time.time() - ds_at >= LIVE_DATA_S
            try:
                c2, job, got = await asyncio.to_thread(_live_parts, rs, want)
            except Exception as e:   # noqa: BLE001 — one bad read never kills the stream; the page keeps the last frame
                yield f"event: oops\ndata: {json.dumps({'error': type(e).__name__})}\n\n"
                await asyncio.sleep(LIVE_DATA_S); continue
            if got is not None:
                ds, ds_at = got, time.time()
            fr = _cl.frame(c2, job, ds, time.time())
            if _cl.changed(last, fr):
                last = fr; beat = time.time()
                yield f'event: frame\ndata: {json.dumps(fr)}\n\n'
            elif time.time() - beat >= LIVE_BEAT_S:
                beat = time.time(); yield ': beat\n\n'
            await asyncio.sleep(LIVE_TICK_S if fr['live'] else 3.0)
        yield 'event: bye\ndata: {}\n\n'
    return StreamingResponse(gen(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no', 'Content-Encoding': 'identity'})



# 🎓 COMP's teacher (owner 2026-11-14): pay a top AI, cheaply, to write COMP lessons on your own proofs. Owner only; it runs only on his Pay
# press, with the live price shown first and a hard cap; OpenRouter with FEELESS's key, never a wallet.
_TEACH = {'job': None, 'models': None, 'at': 0.0}


def _teachers_live(rs):
    if _TEACH['models'] is None or time.time() - _TEACH['at'] > 600:
        import httpx
        try:
            _TEACH['models'] = _ct.teachers(httpx.get('https://openrouter.ai/api/v1/models', timeout=15).json().get('data') or []); _TEACH['at'] = time.time()
        except Exception:   # noqa: BLE001 — the last good list stays
            _TEACH['models'] = _TEACH['models'] or []
    return _TEACH['models']


def _teach_view(rs):
    lessons = _ct.load(rs.DATA_DIR); todo = _ct.untaught(_ct.blocks(_proof_text(rs)), lessons)
    import os
    return {'teachers': _teachers_live(rs), 'untaught': len(todo), **_ct.summary(lessons), 'recent': [{k: x.get(k) for k in ('model', 'usd', 'at', 'proofHead', 'lesson')} for x in lessons[-6:]][::-1],
            'job': _TEACH['job'], 'keyOk': bool(os.environ.get('OPENROUTER_API_KEY', '').strip()), 'maxUsd': _ct.MAX_USD, 'maxN': _ct.MAX_N}


@router.get('/api/reputation/admin/model-lab/teach')
async def teach_view(request: Request):
    rs = _rs(); rs._require_owner(request)
    return await rs.asyncio.to_thread(_teach_view, rs)


class Teach(BaseModel):
    model: str
    n: int = 25
    quoteUsd: float = 0.0   # the estimate the owner saw on the Pay button: the run refuses if today's price moved above it


@router.post('/api/reputation/admin/model-lab/teach')
async def teach_start(request: Request, p: Teach):
    """The owner's Pay press: teach n lessons with this model, never past the cap. 409 while one runs or when the price moved."""
    rs = _rs(); rs._require_owner(request)
    import os
    from fastapi import HTTPException
    key = os.environ.get('OPENROUTER_API_KEY', '').strip()
    if not key:
        raise HTTPException(409, 'No OpenRouter key on the server: add it in HQ › Core first. Nothing was charged.')
    if (_TEACH['job'] or {}).get('state') == 'running':
        raise HTTPException(409, 'A lesson run is already going.')
    t = next((x for x in await rs.asyncio.to_thread(_teachers_live, rs) if x['id'] == p.model), None)
    if not t:
        raise HTTPException(400, 'Pick one of the listed teachers.')
    todo = await rs.asyncio.to_thread(lambda: _ct.untaught(_ct.blocks(_proof_text(rs)), _ct.load(rs.DATA_DIR)))
    if not todo:
        raise HTTPException(409, 'Every proof already has a lesson. File more proofs first.')
    pl = _ct.plan(t, p.n, len(todo))
    if p.quoteUsd and pl['estUsd'] > float(p.quoteUsd) + 1e-6:
        raise HTTPException(409, f"The price moved: now ${pl['estUsd']:.4f}. Nothing was charged; check it and press Pay again.")
    job = {'state': 'running', 'model': t['id'], 'family': t['family'], 'n': pl['n'], 'done': 0, 'spentUsd': 0.0, 'estUsd': pl['estUsd'], 'capUsd': pl['capUsd'], 'at': round(time.time())}
    _TEACH['job'] = job
    rs.asyncio.get_running_loop().run_in_executor(None, _ct.run, rs.DATA_DIR, key, t, todo[-pl['n']:][::-1], pl['capUsd'], job)
    return {'job': job}


@router.post('/api/reputation/admin/model-lab/teach/stop')
async def teach_stop(request: Request):
    rs = _rs(); rs._require_owner(request)
    if _TEACH['job']:
        _TEACH['job']['stop'] = True
    return {'job': _TEACH['job']}
