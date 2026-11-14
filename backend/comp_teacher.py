"""🎓 COMP's teacher (owner 2026-11-14: "a feature where i can pay real cheaply for the best ai to train it").

A top AI reads your own proofs, one at a time, and writes COMP a short lesson about each: what it claimed, whether the evidence holds, the one
rule to keep. The lessons become a source COMP reads when you build the next version (rep_model_lab SOURCES['teacher']) — distillation: a small
model learns the big one's judgement on YOUR data.

Money rules: it runs only when the owner presses Pay in COMP (owner-gated route), on OpenRouter with FEELESS's key — never a wallet, never a
fallback that pays from one. Before it runs the owner sees the live price; it stops at a hard cap (never past MAX_USD) and every lesson keeps
what it cost (OpenRouter's own report, else the price-list estimate). Pure helpers; `run` does the I/O."""
import hashlib
import json
import re
import time
from pathlib import Path

LESSONS = 'comp_teacher.jsonl'
MAX_USD = 5.0                  # a single teaching run can never spend more than this
MAX_N = 100
IN_TOK, OUT_TOK = 900, 320     # one lesson: a proof in (~900 tokens with the instructions), ~320 tokens out
PROOF_MAX = 3000
# the best of each family (newest flagship first), live-priced from OpenRouter; batch / image / vision / audio variants are skipped
FAMILIES = (('anthropic/claude-opus', 'Claude Opus'), ('anthropic/claude-sonnet', 'Claude Sonnet'), ('openai/gpt-5', 'GPT-5'),
            ('google/gemini', 'Gemini Pro'), ('x-ai/grok-4', 'Grok 4'), ('deepseek/deepseek-v4-pro', 'DeepSeek V4 Pro'),
            ('qwen/qwen3.7-plus', 'Qwen 3.7 Plus'), ('moonshotai/kimi', 'Kimi'))
SKIP = re.compile(r':batch|image|vision|audio|nano|mini|lite|flash|codex|omni|-exp|preview|luna', re.I)
SYSTEM = ('You are teaching a small model how to judge FEELESS proofs (a proof is an agent\'s filed work: a coin call, a bid, a page, a content '
          'plan). Read the proof and write ONE lesson, plain text, at most 140 words, in this shape:\n'
          'CLAIM: what it claimed, in one line.\nEVIDENCE: whether the record backs it, naming the exact facts in it.\n'
          'VERDICT: strong / weak / wrong, with the one reason.\nRULE: the one rule to remember for the next proof like it.\n'
          'Use only facts that are in the proof. Never invent numbers, names, prices or dates. Never give financial advice.')


def teachers(models):
    """OpenRouter's /models rows → the best model per family with its live price and the cost of one lesson, best first."""
    out = []
    for prefix, fam in FAMILIES:
        rows = []
        for m in models or []:
            mid = str(m.get('id') or '')
            if not mid.startswith(prefix) or SKIP.search(mid) or (fam == 'Gemini Pro' and '-pro' not in mid):
                continue
            p = m.get('pricing') or {}
            try:
                i, o = float(p.get('prompt') or 0) * 1e6, float(p.get('completion') or 0) * 1e6
            except (TypeError, ValueError):
                continue
            if o > 0:
                rows.append((float(m.get('created') or 0), mid, m.get('name') or mid, i, o))
        if rows:
            _c, mid, name, i, o = max(rows)
            out.append({'id': mid, 'family': fam, 'name': name, 'inPerM': round(i, 4), 'outPerM': round(o, 4), 'perLesson': lesson_usd(i, o)})
    return out


def lesson_usd(in_per_m, out_per_m):
    return round((IN_TOK * float(in_per_m) + OUT_TOK * float(out_per_m)) / 1e6, 6)


def plan(teacher, n, have=None):
    """What a run will cost before it runs: n lessons (clamped 1..MAX_N, and to the proofs still untaught), the estimate and the hard cap."""
    n = max(1, min(MAX_N, int(n or 0)))
    if have is not None:
        n = min(n, have)
    est = round(n * teacher['perLesson'], 4)
    return {'n': n, 'estUsd': est, 'capUsd': round(min(MAX_USD, max(0.01, est * 1.5)), 4)}


def blocks(proof_text):
    """The proofs' text (one '### ' block each) → [(hash, block)], newest-looking last as given."""
    out = []
    for b in re.split(r'(?m)^(?=### )', str(proof_text or '')):
        b = b.strip()
        if len(b) > 80:
            out.append((hashlib.sha1(b.encode()).hexdigest()[:16], b[:PROOF_MAX]))
    return out


def load(folder):
    try:
        return [json.loads(ln) for ln in (Path(folder) / LESSONS).read_text().splitlines() if ln.strip()]
    except (OSError, ValueError):
        return []


def untaught(bs, lessons):
    seen = {x.get('h') for x in lessons}
    return [(h, b) for h, b in bs if h not in seen]


def summary(lessons):
    by = {}
    for x in lessons:
        r = by.setdefault(x.get('model') or '?', {'model': x.get('model') or '?', 'lessons': 0, 'usd': 0.0})
        r['lessons'] += 1; r['usd'] = round(r['usd'] + float(x.get('usd') or 0), 6)
    return {'lessons': len(lessons), 'spentUsd': round(sum(float(x.get('usd') or 0) for x in lessons), 6), 'by': sorted(by.values(), key=lambda r: -r['lessons'])}


def corpus(lessons):
    """The lessons as COMP's reading: one '### ' block each (the proof's head + the lesson)."""
    return '\n'.join(f"### Lesson · {x.get('model', '?').split('/')[-1]}\n{x.get('proofHead', '')}\n{x.get('lesson', '')}\n" for x in lessons if x.get('lesson'))


def run(folder, key, teacher, todo, cap_usd, job, post=None, now=time.time):
    """Teach until done or the cap: each lesson is appended the moment it lands (a stop keeps what was paid for). `job` is updated live.
    `post(model, messages)` → (text, usd or None); the default calls OpenRouter with FEELESS's key."""
    post = post or (lambda model, messages: _openrouter(key, model, messages))
    path = Path(folder) / LESSONS
    for h, b in todo:
        if job.get('stop') or job['spentUsd'] >= cap_usd - teacher['perLesson'] * 0.5:
            job['why'] = 'stopped' if job.get('stop') else 'reached the cap'; break
        try:
            text, usd = post(teacher['id'], [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': b}])
        except Exception as e:   # noqa: BLE001 — one refused lesson is logged, the run goes on
            job['errors'] = job.get('errors', 0) + 1; job['last'] = f'refused: {str(e)[:80]}'
            if job['errors'] >= 3:
                job['why'] = 'the provider kept refusing'; break
            continue
        usd = teacher['perLesson'] if usd is None else float(usd)
        job['spentUsd'] = round(job['spentUsd'] + usd, 6)
        text = str(text or '').strip()
        if not text:
            job['errors'] = job.get('errors', 0) + 1; continue
        row = {'h': h, 'model': teacher['id'], 'usd': round(usd, 6), 'at': round(now()), 'proofHead': b.split('\n', 1)[0][:120], 'lesson': text[:1400]}
        with path.open('a') as fh:
            fh.write(json.dumps(row) + '\n')
        job['done'] += 1; job['last'] = text[:240]
    job['state'] = 'done'; job.setdefault('why', 'finished'); job['endedAt'] = round(now())
    return job


def _openrouter(key, model, messages):
    import httpx
    r = httpx.post('https://openrouter.ai/api/v1/chat/completions', timeout=120, headers={'Authorization': f'Bearer {key}'},
                   json={'model': model, 'messages': messages, 'max_tokens': 500, 'temperature': 0.2, 'usage': {'include': True}})
    r.raise_for_status()
    d = r.json(); cost = (d.get('usage') or {}).get('cost')
    return ((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '', (float(cost) if cost is not None else None)
