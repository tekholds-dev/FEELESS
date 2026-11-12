"""🚀 COMP v2 — the owner's proofs fine-tuned into a real 9B model on this Mac (MLX LoRA over Qwen3.5-9B 4-bit), then examined.

The task is the one a trader needs: read a proof the way it was written BEFORE it settled (kind, title, ask, plan, why …) and say how it
ended: won or lost. Fields written after the result (result, verdict, report, summary) never go in the prompt.

Pure parts (dataset, split, log parsing, scoring) are tested here; the heavy parts shell out to `.venv-mlx` so the backend never imports MLX.
"""
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

import comp_market as _market

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
    """The question for one row: only what was known before the market (or the owner) settled it."""
    lines = [f"Kind: {row.get('kind', '')}", f"Title: {row.get('title', '')}", f"Source: {row.get('source', '')}"]
    lines += [f'{k.capitalize()}: {row[k]}' for k in BEFORE if row.get(k)]
    return '\n'.join(lines) + '\nWon or lost?'


def chat_of(row):
    """→ one mlx-lm chat row (system, user, assistant). Flat proofs are dropped: the exam is won vs lost."""
    if row.get('outcome') not in LABELS:
        return None
    return {'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt_of(row)},
                         {'role': 'assistant', 'content': row['outcome']}]}


def split(rows, seed=SEED, test=0.2, valid=0.1):
    """Stratified by kind × outcome with a fixed seed, so every version is examined on the same held-out proofs.
    → (train, valid, test) lists of the raw rows."""
    groups = {}
    for r in rows:
        if r.get('outcome') in LABELS:
            groups.setdefault((r.get('kind'), r['outcome']), []).append(r)
    rnd = random.Random(seed)
    tr, va, te = [], [], []
    for key in sorted(groups):
        g = sorted(groups[key], key=lambda r: (r.get('at') or 0, r.get('title') or ''))
        rnd.shuffle(g)
        n_te = max(1, round(len(g) * test)) if len(g) >= 3 else 0
        n_va = max(1, round(len(g) * valid)) if len(g) >= 6 else 0
        te += g[:n_te]; va += g[n_te:n_te + n_va]; tr += g[n_te + n_va:]
    return tr, va, te


def write_dataset(rows, folder=None):
    """Writes train/valid/test.jsonl (mlx-lm chat format) + test_rows.json (the raw rows the exam grades). → counts."""
    folder = Path(folder or DATA)
    folder.mkdir(parents=True, exist_ok=True)
    tr, va, te = split(rows)
    net = [r for r in _market.rows(folder, len(tr)) if r.get('outcome') in LABELS]   # 🌐 internet rows: train only, never more than his
    tr = tr + net
    for name, part in (('train', tr), ('valid', va or tr[:4]), ('test', te)):
        with open(folder / f'{name}.jsonl', 'w', encoding='utf-8') as f:
            for r in part:
                f.write(json.dumps(chat_of(r), ensure_ascii=False) + '\n')
    (folder / 'test_rows.json').write_text(json.dumps(te, ensure_ascii=False))
    (folder / 'train_rows.json').write_text(json.dumps(tr, ensure_ascii=False))
    (folder / 'valid_rows.json').write_text(json.dumps(va, ensure_ascii=False))
    counts = {'train': len(tr), 'net': len(net), 'valid': len(va), 'test': len(te),
              'won': sum(r['outcome'] == 'won' for r in tr + va + te), 'lost': sum(r['outcome'] == 'lost' for r in tr + va + te),
              'kinds': sorted({r.get('kind') for r in tr + va + te}), 'at': round(time.time())}
    (folder / 'dataset.json').write_text(json.dumps(counts))
    return counts


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
            'exam': j('exam.json'), 'market': j('market.json'), 'examRunning': bool((j('exam_run.json', {}) or {}).get('pid')) and alive(j('exam_run.json', {}).get('pid'))}


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


if __name__ == '__main__':   # `python comp_v2.py build` writes the dataset from the live proofs
    sys.path.insert(0, str(ROOT))
    if sys.argv[1:] == ['build']:
        import rep_model_lab
        import reputation_service
        print(write_dataset(rep_model_lab._export(reputation_service)))
