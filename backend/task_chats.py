"""🧵 Slice 35 · TASK CHATS (owner 2026-11-20: "the same brain runs a separate convo window in that same original chat that redirects to the new
chat that's doing that task live … a dropdown for that thought before the mind processes something else … just like your chat!").

A mind (or its owner, with "/task …" or the Split button on a message) splits one job off the desk chat or a proof's chat into its OWN task chat:
same mind, same settings, a short brief. The task chat plans a checklist, works it one step at a time (each step: a thought, what it did, log rows,
its cost), and ends with a 2–3 line recap that lands back in the chat it came from (and on the proof's own record when it came from a proof).

§1: a task chat is TEXT WORK ONLY. It has no tool that trades, bids, sends, posts or signs, and the prompts say so. It only reads what it is given.
Pure: no I/O here (fc_taskchat.py runs it)."""
import json
import re
import time
import uuid

STATES = ('queued', 'starting', 'working', 'waiting', 'paused', 'done', 'failed', 'stopped')
ENDED = ('done', 'failed', 'stopped')
KEEP = 30            # task chats kept per agent (the oldest ended ones drop first)
STEPS_MAX = 6        # a checklist is 3–6 steps
LOG_KEEP = 60        # log rows kept per task
MSGS_KEEP = 20       # owner's steer lines kept per task
PARALLEL_MAX = 3     # 🎚 the owner may allow up to 3 at once per agent (default 1)
SCOPES = ('desk', 'pow', 'pop', 'pob', 'poc', 'pos', 'poe')
FOLDER_KEYS = {'pow': 'powFolders', 'pop': 'popFolders', 'pob': 'pobFolders', 'poc': 'pocFolders', 'pos': 'psFolders', 'poe': 'poeFolders'}
SPLIT_RE = re.compile(r'^\s*/task\s+(.{3,400})$', re.M)   # 🧠 a mind's own split: a line "/task <title>: <what done looks like>" in its answer

NO_MONEY = ('You work in a task chat: TEXT WORK ONLY. You cannot trade, buy, sell, bid, send money, post, sign or log in anywhere, and you never '
            'say you did. Plan, research from what you know and the context given, draft, compare, check.')
TASK_HINT = ('If a job needs several steps of its own, you may hand it to a task chat: write one line "/task <short title>: <what done looks like>" '
             'and it runs live in its own chat beside this one (text work only), then its recap comes back here.')


def scope_of(raw):
    """'desk' | '<kind>' | '<kind>:<folder id>' → {kind, ref}. Anything else is the desk. Pure."""
    s = str(raw or 'desk').strip().lower()[:80]
    k, _, ref = s.partition(':')
    if k not in SCOPES:
        return {'kind': 'desk', 'ref': ''}
    return {'kind': k, 'ref': re.sub(r'[^a-z0-9_-]', '', ref)[:40] if k != 'desk' else ''}


def title_of(text):
    t = ' '.join(str(text or '').split())
    head = re.split(r'[:.\n]', t, 1)[0].strip() or t
    return head[:60] + ('…' if len(head) > 60 else '')


def new(brief, scope, by='owner', mind=0, cap=0.10, now=None, test=False):
    now = time.time() if now is None else now
    b = ' '.join(str(brief or '').split())[:1200]
    return {'id': 'tc' + uuid.uuid4().hex[:10], 'title': title_of(b), 'brief': b, 'scope': scope_of(scope), 'by': by if by in ('owner', 'mind') else 'owner',
            'mind': int(mind or 0), 'model': None, 'state': 'queued', 'why': '', 'steps': [], 'at': 0, 'thoughts': [], 'logs': [], 'msgs': [],
            'cost': 0.0, 'cap': round(max(0.005, float(cap or 0)), 4), 'created': now, 'started': None, 'ended': None, 'recap': '', 'test': bool(test)}


def splits_in(answer):
    """The /task lines a mind wrote in its answer → [brief], and the answer without them. Pure."""
    a = str(answer or '')
    parts = re.split(r'(```.*?(?:```|$))', a, flags=re.S)   # a /task line inside a ``` code block is an example, never a split
    briefs = [m.strip() for i, x in enumerate(parts) if i % 2 == 0 for m in SPLIT_RE.findall(x)][:3]
    if not briefs:
        return [], a.strip()
    return briefs, ''.join(x if i % 2 else SPLIT_RE.sub('', x) for i, x in enumerate(parts)).strip()


def _json(text):
    t = str(text or '').strip()
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', t)
    i, j = t.find('{'), t.rfind('}')
    if i < 0 or j <= i:
        return None
    try:
        v = json.loads(t[i:j + 1])
    except ValueError:
        return None
    return v if isinstance(v, dict) else None


def clean(s, n):
    return ' '.join(str(s or '').split())[:n]


def read_plan(text):
    """The mind's plan reply → (thought, title, steps). A reply that is not JSON still gives one step: do the brief. Pure."""
    v = _json(text) or {}
    steps = [clean(x, 160) for x in (v.get('steps') or []) if clean(x, 160)][:STEPS_MAX]
    return clean(v.get('think'), 600), clean(v.get('title'), 60), steps


def read_step(text):
    """One step's reply → {think, did, log[], ask}. A plain-text reply is what it did. Pure."""
    v = _json(text)
    if v is None:
        return {'think': '', 'did': str(text or '').strip()[:1600], 'log': [], 'ask': ''}
    return {'think': clean(v.get('think'), 600), 'did': str(v.get('did') or '').strip()[:1600],
            'log': [clean(x, 200) for x in (v.get('log') or []) if clean(x, 200)][:6], 'ask': clean(v.get('ask'), 300)}


def read_recap(text):
    v = _json(text)
    r = (v or {}).get('recap') if v else text
    lines = [clean(x, 200) for x in str(r or '').splitlines() if clean(x, 200)][:3]
    return '\n'.join(lines)


def plan_msgs(t, context, owner_lines):
    return [{'role': 'system', 'content': NO_MONEY + ' Reply with JSON only: {"think": "your reasoning, 1-3 sentences", "title": "≤ 6 words", '
             '"steps": ["3 to 6 short steps, one line each"]}.'},
            {'role': 'user', 'content': f"TASK: {t['brief']}\n" + (f"CONTEXT (read only):\n{context}\n" if context else '') + (f"OWNER'S NOTES: {owner_lines}\n" if owner_lines else '')}]


def step_msgs(t, k, context, owner_lines):
    done = '\n'.join(f"{i + 1}. {s['text']} → {s.get('did', '')[:500]}" for i, s in enumerate(t['steps'][:k]))
    last = k == len(t['steps']) - 1
    return [{'role': 'system', 'content': NO_MONEY + ' Do ONLY the step asked. Reply with JSON only: {"think": "your reasoning, 1-3 sentences", '
             '"did": "what this step produced (markdown ok, ≤ 900 chars)", "log": ["short log lines of what you checked"], '
             '"ask": "a question for your owner ONLY if you truly cannot go on, else empty"}.'},
            {'role': 'user', 'content': f"TASK: {t['brief']}\n" + (f"CONTEXT (read only):\n{context}\n" if context else '')
             + (f"DONE SO FAR:\n{done}\n" if done else '') + (f"OWNER'S NOTES (follow them): {owner_lines}\n" if owner_lines else '')
             + f"NOW DO STEP {k + 1} of {len(t['steps'])}: {t['steps'][k]['text']}" + (' (the last step: finish the task here)' if last else '')}]


def recap_msgs(t):
    done = '\n'.join(f"- {s['text']}: {s.get('did', '')[:400]}" for s in t['steps'])
    return [{'role': 'system', 'content': 'Write the recap of a finished task for the chat it came from. JSON only: {"recap": "2 or 3 short lines: what was done and what came out"}.'},
            {'role': 'user', 'content': f"TASK: {t['brief']}\nSTEPS:\n{done}"}]


def log(t, text, now=None, step=None):
    t['logs'] = (t.get('logs') or []) + [{'at': round(now or time.time(), 2), 'text': clean(text, 200), **({'step': step} if step is not None else {})}]
    t['logs'] = t['logs'][-LOG_KEEP:]


def thought(t, text, secs, step):
    if text:
        t['thoughts'] = (t.get('thoughts') or []) + [{'step': step, 'text': text, 's': round(max(0.0, secs), 1)}]


def current(t):
    """The step being worked (index) or None. Pure."""
    return next((i for i, s in enumerate(t.get('steps') or []) if s.get('state') == 'doing'), None)


def queue_order(tasks):
    """Queued tasks oldest first. Pure."""
    return sorted([t for t in tasks if t.get('state') == 'queued'], key=lambda t: t.get('created') or 0)


def can_start(tasks, parallel):
    """How many more may start now under the agent's parallel setting. Pure."""
    live = sum(1 for t in tasks if t.get('state') in ('starting', 'working'))
    return max(0, max(1, min(PARALLEL_MAX, int(parallel or 1))) - live)


def trim(tasks):
    """Keep the newest KEEP; live ones are never dropped. Pure."""
    if len(tasks) <= KEEP:
        return tasks
    ended = [t for t in tasks if t.get('state') in ENDED]
    drop = {t['id'] for t in sorted(ended, key=lambda t: t.get('created') or 0)[:len(tasks) - KEEP]}
    return [t for t in tasks if t['id'] not in drop]


def card(t, now=None):
    """What the original chat's card shows. Pure."""
    now = time.time() if now is None else now
    k = current(t)
    end = t.get('ended') or now
    return {'id': t['id'], 'title': t.get('title'), 'state': t.get('state'), 'why': t.get('why') or '', 'step': (t['steps'][k]['text'] if k is not None else ''),
            'stepN': (k + 1) if k is not None else sum(1 for s in t.get('steps') or [] if s.get('state') == 'done'), 'steps': len(t.get('steps') or []),
            'secs': round(end - (t.get('started') or t.get('created') or now)) if (t.get('started') or t.get('state') in ENDED) else 0,
            'cost': round(float(t.get('cost') or 0), 6), 'recap': t.get('recap') or '', 'scope': t.get('scope'), 'by': t.get('by'), 'test': bool(t.get('test'))}


def view(t, now=None):
    """The whole task chat: card + checklist + thoughts + logs + the owner's lines. Pure."""
    return {**card(t, now), 'brief': t.get('brief'), 'model': t.get('model'), 'cap': t.get('cap'),
            'checklist': [{k: s.get(k) for k in ('text', 'state', 'cost', 'did', 'at', 'secs')} for s in t.get('steps') or []],
            'thoughts': list(t.get('thoughts') or []), 'logs': list(t.get('logs') or [])[-LOG_KEEP:], 'msgs': list(t.get('msgs') or [])[-MSGS_KEEP:],
            'created': t.get('created'), 'started': t.get('started'), 'ended': t.get('ended')}


def record_row(t):
    """The line a finished task leaves on its proof's record. Pure."""
    return {'id': t['id'], 'title': t.get('title'), 'state': t.get('state'), 'recap': t.get('recap') or t.get('why') or '', 'cost': round(float(t.get('cost') or 0), 6),
            'steps': [s.get('text') for s in t.get('steps') or []], 'model': t.get('model'), 'at': t.get('ended') or t.get('created'), 'test': bool(t.get('test'))}
