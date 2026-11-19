"""🚀 COMP v2 — the owner's proofs fine-tuned into a real 9B model on this Mac (MLX LoRA over Qwen3.5-9B 4-bit), then examined.

The task is the one a trader needs: read a proof the way it was written BEFORE it settled (kind, title, ask, plan, why …) and say how it
ended: won or lost. Fields written after the result (result, verdict, report, summary) never go in the prompt.

Pure parts (dataset, split, log parsing, scoring) are tested here; the heavy parts shell out to `.venv-mlx` so the backend never imports MLX.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import comp_real as _real

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'comp_v2'
MLX_PY = ROOT.parent / '.venv-mlx' / 'bin' / 'python'
BASE = Path(os.path.expanduser('~/.lmstudio/models/lmstudio-community/Qwen3.5-9B-MLX-4bit'))
BASE_NAME = 'Qwen3.5-9B (4-bit, MLX)'
LABELS = ('won', 'lost')
BEFORE = ('ask', 'topic', 'plan', 'why', 'angle')          # written before it settled — the only text the model may see
SYSTEM = ('You are COMP, the FEELESS judge. You read one proof an agent wrote before it settled and say how it ended. '
          'Answer with exactly one word: won or lost.')
SEED = 7


def prompt_of(row):
    """The question for one row: only what was known before the market (or the owner) settled it, and what the proof DID before then
    (Slice 7: the minds' calls and reasons, the bid, the coin at entry, the build plan; comp_real.evidence)."""
    lines = [f"Kind: {row.get('kind', '')}", f"Title: {row.get('title', '')}", f"Source: {row.get('source', '')}"]
    lines += [f'{k.capitalize()}: {row[k]}' for k in BEFORE if row.get(k)]
    if row.get('evidence'):
        lines += ['What it did:'] + [f'- {e}' for e in row['evidence'][:14]]
    return '\n'.join(lines) + '\nWon or lost?'


def chat_of(row):
    """→ one mlx-lm chat row (system, user, assistant). Flat proofs are dropped: the exam is won vs lost."""
    if row.get('outcome') not in LABELS:
        return None
    return {'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt_of(row)},
                         {'role': 'assistant', 'content': row['outcome']}]}


KALSHI_ROWS = 'kalshi_rows.jsonl'


def kalshi_rows(folder=None):
    """🎓 Settled real Kalshi bids, written by the service when Kalshi settles them (owner 2026-11-14: agents learn from their Kalshi results)."""
    try:
        return [json.loads(x) for x in (Path(folder or DATA) / KALSHI_ROWS).read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def add_kalshi_row(row, folder=None):
    """Appends one lesson once (by id). → True when it was new."""
    folder = Path(folder or DATA); folder.mkdir(parents=True, exist_ok=True)
    if row.get('outcome') not in LABELS or any(r.get('id') == row.get('id') for r in kalshi_rows(folder)):
        return False
    with open(folder / KALSHI_ROWS, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return True


def write_dataset(gate, folder=None):
    """Slice 7: `gate` = comp_real.collect(...): real, judged proofs only, each with its pass / fail evidence. Writes train/valid/test.jsonl
    (mlx-lm chat format) + the raw rows the exam grades. The folds come from a hash of each proof's id (comp_real.fold), so a proof that
    sat one exam is never trained on later. Internet market rows and Kalshi lessons no longer train COMP: they are counted as dropped. → counts"""
    folder = Path(folder or DATA)
    folder.mkdir(parents=True, exist_ok=True)
    rows = [r for r in gate['rows'] if r.get('outcome') in LABELS]
    tr, va, te = _real.split(rows)
    for name, part in (('train', tr), ('valid', va), ('test', te)):
        with open(folder / f'{name}.jsonl', 'w', encoding='utf-8') as f:
            for r in part:
                f.write(json.dumps(chat_of(r), ensure_ascii=False) + '\n')
    (folder / 'test_rows.json').write_text(json.dumps(te, ensure_ascii=False))
    (folder / 'train_rows.json').write_text(json.dumps(tr, ensure_ascii=False))
    (folder / 'valid_rows.json').write_text(json.dumps(va, ensure_ascii=False))
    by_kind = {}
    for part, rs_ in (('train', tr), ('valid', va), ('test', te)):
        for r in rs_:
            k = by_kind.setdefault(r['kind'], {'kind': r['kind'], 'train': 0, 'valid': 0, 'test': 0, 'won': 0, 'lost': 0})
            k[part] += 1; k[r['outcome']] += 1
    settled = {}
    for r in rows:
        settled[r.get('settledBy') or '?'] = settled.get(r.get('settledBy') or '?', 0) + 1
    counts = {'only': 'real judged proofs', 'train': len(tr), 'net': 0, 'valid': len(va), 'test': len(te),
              'won': sum(r['outcome'] == 'won' for r in rows), 'lost': sum(r['outcome'] == 'lost' for r in rows),
              'kinds': sorted(by_kind), 'byKind': sorted(by_kind.values(), key=lambda k: k['kind']), 'settledBy': settled,
              'dropped': gate.get('dropped') or {}, 'droppedN': sum((gate.get('dropped') or {}).values()), 'why': gate.get('why') or {},
              'at': round(time.time())}
    (folder / 'dataset.json').write_text(json.dumps(counts))
    return counts


def extra_counts(folder=None, teacher=None):
    """The sources that are not proofs and so never train COMP (Slice 7), counted for the report."""
    folder = Path(folder or DATA)
    def lines(p):
        try:
            return sum(1 for ln in Path(p).read_text().splitlines() if ln.strip())
        except OSError:
            return 0
    return {'market_row': lines(folder / 'market_rows.jsonl'),
            'kalshi_lesson': len(kalshi_rows(folder)), 'teacher_lesson': lines(teacher or (ROOT / 'data' / 'comp_teacher.jsonl'))}


_ITER = re.compile(r'Iter (\d+): (Train|Val) loss ([\d.]+)')
_ANSI = re.compile(r'\x1b\[[0-9;]*m')
_ROW_VAL = re.compile(r'^\s*(\d+)\s+val\s+([\d.]+)', re.M)
_ROW_TRAIN = re.compile(r'^\s*(\d+)\s+(\d+\.\d+)\b', re.M)


def parse_log(text):
    """mlx_lm lora's log (the old 'Iter N: Train loss' lines or the newer table rows) → {'train': [[iter, loss]], 'val': [...], 'last'}."""
    t = _ANSI.sub('', text or '')
    out = {'train': [], 'val': [], 'last': 0}
    for it, kind, loss in _ITER.findall(t):
        out['train' if kind == 'Train' else 'val'].append([int(it), float(loss)])
    if not out['train'] and not out['val']:
        out['val'] = [[int(i), float(v)] for i, v in _ROW_VAL.findall(t)]
        out['train'] = [[int(i), float(v)] for i, v in _ROW_TRAIN.findall(t)]
    out['last'] = max([x[0] for x in out['train'] + out['val']] or [0])
    return out


_WORD = re.compile(r"[a-z0-9$]{3,}")


def _words(row):
    return set(_WORD.findall(prompt_of(row).lower())) - {'kind', 'title', 'source', 'plan', 'won', 'lost'}


def neighbours(row, train, k=5):
    """🧠 Memory: the k past proofs most like this one (word overlap, same kind first) — COMP reads them and how they ended before it
    answers. Nothing is trained: this is recall, so a proof settled an hour ago helps on the very next question."""
    w = _words(row)
    def sim(t):
        tw = _words(t)
        return (t.get('kind') == row.get('kind'), len(w & tw) / (len(w | tw) or 1))
    return sorted((t for t in train if t is not row and t.get('title') != row.get('title')), key=sim, reverse=True)[:k]


def memory_prompt(row, train, k=5):
    past = '\n'.join(f"- {t.get('kind')} · {t.get('title')} → {t['outcome']}" for t in neighbours(row, train, k))
    return f"Past proofs like this one and how they ended:\n{past}\n\nNow this one:\n{prompt_of(row)}"


def answer_of(text):
    """The first won / lost the model said (after any thinking block). None when it said neither."""
    t = re.sub(r'<think>.*?</think>', ' ', str(text or ''), flags=re.S).lower()
    m = re.search(r'\b(won|lost|win|loss|lose)\b', t)
    if not m:
        return None
    return 'won' if m.group(1) in ('won', 'win') else 'lost'


def score(rows, answers):
    """→ {'n', 'right', 'acc', 'kinds': {kind: {n, right}}, 'unsure'} for one examinee's answers against the held-out rows."""
    out = {'n': len(rows), 'right': 0, 'unsure': 0, 'kinds': {}}
    for r, a in zip(rows, answers):
        k = out['kinds'].setdefault(r.get('kind') or '?', {'n': 0, 'right': 0})
        k['n'] += 1
        if a is None:
            out['unsure'] += 1
        elif a == r['outcome']:
            out['right'] += 1; k['right'] += 1
    out['acc'] = round(out['right'] / out['n'], 4) if out['n'] else 0
    return out


def majority(train):
    """The baseline any model must beat: always answer the most common result in the training proofs."""
    won = sum(r['outcome'] == 'won' for r in train)
    return 'won' if won * 2 >= len(train) else 'lost'


def ship_verdict(exam):
    """🚦 Slice 7: a COMP that does not beat the base model on the held-out real proofs is NOT shipped, and this says why in plain words.
    Ships only when COMP (the fine-tune alone, no memory: like for like with the base) gets strictly more questions right than the base 9B
    AND at least as many as always guessing the majority. → {'ship', 'why', 'comp', 'base', 'baseline', 'n', 'margin'}"""
    ex = {e['id']: e for e in (exam or {}).get('examinees') or []}
    def right(i):
        s = (ex.get(i) or {}).get('score') or {}
        return s.get('right'), s.get('n')
    (c, n), (b, _), (m, _) = right('comp'), right('base'), right('baseline')
    out = {'ship': False, 'comp': c, 'base': b, 'baseline': m, 'n': n or (exam or {}).get('n') or 0, 'margin': None}
    if c is None:
        why = (ex.get('comp') or {}).get('blocked') or 'COMP did not sit the exam'
        return {**out, 'why': f'Not shipped: {why}.'}
    if b is None:
        return {**out, 'why': 'Not shipped: the base model did not sit the exam, so there is nothing to beat.'}
    out['margin'] = c - b
    pts = round(100 / n, 1) if n else 0
    if c <= b:
        return {**out, 'why': f'Not shipped: COMP got {c} of {n} right and the base 9B got {b} of {n}. '
                              f'{"A tie is not a win" if c == b else "COMP did worse"}: the fine-tune taught it nothing the base did not already know '
                              f'on these proofs (one answer = {pts} points).'}
    if m is not None and c < m:
        return {**out, 'why': f'Not shipped: COMP beat the base ({c} vs {b} of {n}) but not always guessing "{(ex.get("baseline") or {}).get("name", "")}" ({m}).'}
    return {**out, 'ship': True, 'why': f'Shipped: COMP got {c} of {n} right vs the base 9B {b} (+{c - b}, one answer = {pts} points).'}


def ship(folder, exam, chosen):
    """Writes the verdict into the exam; on a pass, copies the chosen adapter to shipped/ (what COMP serves). On a fail the last shipped
    COMP stays as it was (or none), so a worse COMP never replaces a better one. → the verdict"""
    import shutil
    folder = Path(folder); v = ship_verdict(exam); v['at'] = round(time.time())
    if v['ship'] and chosen and (Path(chosen) / 'adapters.safetensors').exists():
        dst = folder / 'shipped'
        tmp = folder / 'shipped.new'
        shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
        for name in ('adapters.safetensors', 'adapter_config.json'):
            src = Path(chosen) / name if (Path(chosen) / name).exists() else folder / 'adapter' / name
            shutil.copy(src, tmp / name)
        shutil.rmtree(dst, ignore_errors=True); tmp.rename(dst)
        (folder / 'shipped.json').write_text(json.dumps({**v, 'exam': exam.get('at'), 'picked': exam.get('picked')}))
    elif v['ship']:
        v = {**v, 'ship': False, 'why': 'Not shipped: the picked adapter is missing on disk.'}
    exam['ship'] = v
    return v


def shipped(folder=None):
    """→ what COMP serves now: the last verdict that passed ({} when none ever has)."""
    try:
        return json.loads((Path(folder or DATA) / 'shipped.json').read_text())
    except (OSError, ValueError):
        return {}


# ── the heavy parts (subprocess; never imported by the backend) ─────────────────────────────────────────────────────────────────────

def train_cmd(iters=300, folder=None):
    folder = Path(folder or DATA)
    return [str(MLX_PY), '-m', 'mlx_lm', 'lora', '--model', str(BASE), '--train', '--data', str(folder),
            '--adapter-path', str(folder / 'adapter'), '--iters', str(iters), '--batch-size', '1', '--num-layers', '8',
            '--learning-rate', '3e-5', '--max-seq-length', '768', '--mask-prompt', '--grad-checkpoint',
            '--steps-per-report', '10', '--steps-per-eval', '50', '--save-every', '50', '--seed', str(SEED)]


def start_train(iters=300, folder=None):
    """Starts the LoRA run in the background; its log is train.log. → pid."""
    folder = Path(folder or DATA)
    log = open(folder / 'train.log', 'w')
    p = subprocess.Popen(train_cmd(iters, folder), stdout=log, stderr=subprocess.STDOUT, cwd=str(ROOT), start_new_session=True,
                         env={**os.environ, 'PYTHONUNBUFFERED': '1', 'NO_COLOR': '1'})
    (folder / 'train.json').write_text(json.dumps({'pid': p.pid, 'iters': iters, 'at': round(time.time())}))
    return p.pid


def alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def status(folder=None):
    """→ everything the COMP v2 tab shows: the base model, dataset counts, the run's live loss, the exam."""
    folder = Path(folder or DATA)
    def j(name, d=None):
        try:
            return json.loads((folder / name).read_text())
        except (OSError, ValueError):
            return d
    run = j('train.json', {}) or {}
    try:
        log = (folder / 'train.log').read_text(errors='replace')
    except OSError:
        log = ''
    curve = parse_log(log)
    err = next((ln.strip() for ln in log.splitlines()[::-1] if 'Error' in ln or 'Traceback' in ln), '')
    running = bool(run.get('pid')) and alive(run['pid'])
    done = (folder / 'adapter' / 'adapters.safetensors').exists() and not running
    return {'base': {'name': BASE_NAME, 'ready': BASE.exists(), 'params': '9B', 'bits': 4, 'engine': 'MLX LoRA',
                     'mlx': MLX_PY.exists()},
            'dataset': j('dataset.json'), 'run': {**run, 'running': running, 'done': done, 'curve': curve,
                                                  'error': '' if running else _say(err)},
            'exam': j('exam.json'), 'shipped': shipped(folder), 'race': history(folder, j('exam.json')), 'market': j('market.json'), 'examRunning': bool((j('exam_run.json', {}) or {}).get('pid')) and alive(j('exam_run.json', {}).get('pid'))}


def race_row(exam):
    """🏁 AGX-6: one finished exam → one point per examinee on the race: {at, n, scores: {id: acc}, names: {id: name}, kinds: {id: kind}}."""
    ex = [e for e in (exam or {}).get('examinees') or [] if (e.get('score') or {}).get('n')]
    return {'at': int((exam or {}).get('done') or (exam or {}).get('at') or 0), 'n': int((exam or {}).get('n') or 0),
            'scores': {e['id']: e['score']['acc'] for e in ex}, 'names': {e['id']: str(e.get('name') or e['id'])[:40] for e in ex},
            'kinds': {e['id']: e.get('kind') or '' for e in ex}}


def keep_history(folder, exam):
    """Appends a finished exam to exam_history.jsonl (once per exam: same `at` never twice)."""
    row = race_row(exam)
    if not row['scores']:
        return False
    p = Path(folder) / 'exam_history.jsonl'
    if any(r.get('at') == row['at'] for r in history(folder)):
        return False
    with open(p, 'a') as f:
        f.write(json.dumps(row) + '\n')
    return True


def history(folder=None, exam=None):
    """Every exam so far, oldest first. An exam that finished before the history existed counts as the first point."""
    out = []
    try:
        for ln in (Path(folder or DATA) / 'exam_history.jsonl').read_text().splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
    except OSError:
        pass
    if not out and exam and exam.get('done'):
        r = race_row(exam)
        out = [r] if r['scores'] else []
    return sorted(out, key=lambda r: r.get('at') or 0)


def _say(err):
    """A crash line in plain words (the adapter from the last checkpoint is kept either way)."""
    if not err:
        return ''
    if 'Insufficient Memory' in err or 'OutOfMemory' in err:
        return 'Stopped: the GPU ran out of memory. The last saved checkpoint is kept; close other apps and train again.'
    return err[:200]


def start_exam(folder=None):
    """Runs the exam in the background (comp_v2_exam.py under .venv-mlx). → pid."""
    folder = Path(folder or DATA)
    log = open(folder / 'exam.log', 'w')
    p = subprocess.Popen([str(MLX_PY), str(ROOT / 'comp_v2_exam.py'), str(folder)], stdout=log, stderr=subprocess.STDOUT,
                         cwd=str(ROOT), start_new_session=True,
                         env={**os.environ, 'PYTHONUNBUFFERED': '1'})
    (folder / 'exam_run.json').write_text(json.dumps({'pid': p.pid, 'at': round(time.time())}))
    return p.pid


def real_gate(rs_dir=None, folder=None):
    """Slice 7: comp_real.collect over the agents' real proofs (their live folders + the stash copies + the owner's Model Lab grades). Read only."""
    import collective_stash as _st
    d = Path(rs_dir or ROOT / 'data')
    try:
        cats = json.loads((d / 'feecats.json').read_text()).get('cats') or {}
    except (OSError, ValueError):
        cats = {}
    try:
        grades = json.loads((d / 'model_lab_grades.json').read_text())
    except (OSError, ValueError):
        grades = {}
    root = d / 'stash'
    return _real.collect(cats, _st.catalog(root) if (root / 'index.db').exists() else [], lambda k: _st.read(root, k),
                         extra=extra_counts(folder, d / 'comp_teacher.jsonl'), grades=grades)


def build_real(rs_dir=None, folder=None):
    return write_dataset(real_gate(rs_dir, folder), folder)


if __name__ == '__main__':   # `python comp_v2.py build` writes the dataset from the real proofs
    sys.path.insert(0, str(ROOT))
    if sys.argv[1:] == ['build']:
        print(json.dumps(build_real()))
