"""🧠🧠 THE GENERAL CAT AT WORK (owner 2026-10-29, P2): the user hits Enter → the two chosen models either answer FAST from what they know, or split
the task, each works its half in ITS OWN browser window (cat_browser.py) while the user watches, and the first model merges both halves into one
answer. Tested with fakes (tests/test_cat_agent.py).

  plan   one call to model A → {"fast": answer-or-"", "a": half for A, "b": half for B}
  work   each window loops ≤ STEP_MAX: the model reads the page and picks ONE action (open · search · click · type · human · answer); every step
         updates the window's bubble (what it is doing + why) and its step log
  human  a sign-in / sign-up / CAPTCHA (the model says so, or `needs_human` sees it) PAUSES that window with a centred request — the user acts in
         the live window, then CONTINUE (or STOP). A model may never type a password, a card or a seed phrase (`blocked_value`) — that is always human
  merge  model A combines both halves (with their sources) into one answer
BUDGET: every call's cost is added; a task stops at its cap ($ per task, the user's setting) with what it has. Real money moves only on the user's
signal (the wallet / their auto-sign settings) — nothing here can spend from a wallet."""
import asyncio
import json
import re

STEP_MAX = 8
GO_STEPS = 30     # 🏇 "let it go" (owner Q1): a task may run this many steps a window — it stops only when done, at its $ cap, or for a human
READ_MAX = 3500
BLOCKED = re.compile(r'(?i)pass(word|code)|seed|mnemonic|recovery phrase|private key|cvv|card number')

PLAN_SYS = ('You lead two AI models working for a FEELESS user. If you can answer the task well from what you already know, put the answer in "fast". '
            'Otherwise split it into two halves the two models research in their own browsers at the same time. Answer ONLY JSON: '
            '{"fast": "<answer or empty>", "a": "<your half>", "b": "<the other model\'s half>"}')
ACT_SYS = ('You are {name}, an AI model working in your OWN web browser for a FEELESS user, who watches you. Your half of the task: {goal}\n'
           'Each turn pick ONE action. Answer ONLY JSON: {{"thought": "<= 12 words: what you are doing and why", "action": "open|search|click|type|human|answer", '
           '"url": "", "q": "", "text": "<visible text of the link / button to click>", "label": "<field label or placeholder>", "value": "", "say": "<your answer, when action is answer>"}}\n'
           'Rules: never type a password, card number or seed phrase — use "human" for any sign-in / sign-up / CAPTCHA. Never claim what the page does not show. '
           'Finish with "answer" (with the sources you used) within {steps} steps.')
MERGE_SYS = 'Combine the two research halves into ONE clear answer for the user, keep the sources, say what is still uncertain. Plain text, short.'


def parse_json(text):
    """The first JSON object in a model's text → dict ({} when none)."""
    t = str(text or '')
    for m in re.finditer(r'\{', t):
        depth = 0
        for j in range(m.start(), len(t)):
            depth += {'{': 1, '}': -1}.get(t[j], 0)
            if depth == 0:
                try:
                    v = json.loads(t[m.start():j + 1])
                    return v if isinstance(v, dict) else {}
                except ValueError:
                    break
    return {}


def blocked_value(label, value):
    """True when a model tries to type a secret (a password / seed / card) — that is always the user's job."""
    return bool(BLOCKED.search(str(label or '')) or re.search(r'\b(?:\d[ -]?){13,19}\b', str(value or '')))


def new_task(tid, text, models, cap, steps=STEP_MAX):
    return {'id': tid, 'text': str(text)[:2000], 'status': 'planning', 'cap': float(cap), 'cost': 0.0, 'answer': None, 'fast': False, 'stepsMax': int(steps),
            'windows': [{'i': i, 'model': m, 'goal': None, 'status': 'idle', 'bubble': 'waiting for the plan', 'url': None, 'title': None,
                         'steps': [], 'human': None, 'answer': None, 'cost': 0.0} for i, m in enumerate(models[:2])]}


class Stopped(Exception):
    pass


async def _ask(task, w, ask, model, messages):
    if task.get('stop'):
        raise Stopped()
    if task['cost'] >= task['cap']:
        raise Stopped(f"budget reached (${task['cost']:.4f} of ${task['cap']:.4f})")
    text, usd = await ask(model, messages)
    task['cost'] = round(task['cost'] + float(usd or 0), 6)
    if w is not None:
        w['cost'] = round(w['cost'] + float(usd or 0), 6)
    return text


def _step(w, thought, action, detail=''):
    w['bubble'] = f"{thought}" if thought else action
    w['steps'] = (w['steps'] + [{'action': action, 'thought': str(thought or '')[:120], 'detail': str(detail or '')[:160]}])[-40:]


async def _window(task, w, ask, page, wait_human, name):
    """One model working its half in its own browser. → its answer (or what it has when stopped)."""
    w['status'] = 'working'
    seen = ''
    n_max = int(task.get('stepsMax') or STEP_MAX)
    for _n in range(n_max):
        msgs = [{'role': 'system', 'content': ACT_SYS.format(name=name, goal=w['goal'], steps=n_max)},
                {'role': 'user', 'content': f"URL: {page.url or '(blank)'}\nTITLE: {page.title or ''}\nPAGE:\n{seen[:READ_MAX]}"}]
        a = parse_json(await _ask(task, w, ask, w['model'], msgs))
        act = str(a.get('action') or '').lower()
        thought = str(a.get('thought') or '').strip()
        if act == 'answer' or not act:
            w['answer'] = str(a.get('say') or thought or 'no answer')[:4000]
            _step(w, thought or 'done', 'answer')
            break
        if act == 'type' and blocked_value(a.get('label'), a.get('value')):
            act, a['why'] = 'human', 'it wanted to type a secret — that is yours to type'
        if act == 'human':
            w['human'] = {'why': str(a.get('why') or thought or 'a person is needed here')[:160], 'url': page.url}
        else:
            try:
                if act == 'open':
                    seen = await page.goto(str(a.get('url') or ''))
                elif act == 'search':
                    seen = await page.search(str(a.get('q') or w['goal']))
                elif act == 'click':
                    seen = await page.click(str(a.get('text') or ''))
                elif act == 'type':
                    seen = await page.type(str(a.get('label') or ''), str(a.get('value') or ''))
                else:
                    seen = f'(unknown action {act})'
            except Exception as e:
                seen = f'(that did not work: {str(e)[:120]})'
            w['url'], w['title'] = page.url, page.title
            from cat_browser import needs_human
            why = needs_human(page.url, seen)
            if why:
                w['human'] = {'why': why, 'url': page.url}
        _step(w, thought, act, a.get('url') or a.get('q') or a.get('text') or '')
        if w['human']:
            w['status'], w['bubble'] = 'human', f"✋ needs you: {w['human']['why']}"
            go = await wait_human(w['i'])
            w['human'] = None
            if not go:
                raise Stopped('stopped by you')
            w['status'] = 'working'
            seen = await page.read()
    else:
        w['answer'] = w['answer'] or f'(ran out of steps) {thought}'
    w['status'] = 'done'
    return w['answer']


async def run(task, ask, pages, wait_human, names=('Model A', 'Model B')):
    """The whole task. `ask(model, messages)` → (text, $) · `pages[i]` = window i's page driver · `wait_human(i)` → True continue / False stop."""
    ws = task['windows']
    try:
        lead = ws[0]['model']
        p = parse_json(await _ask(task, ws[0], ask, lead, [{'role': 'system', 'content': PLAN_SYS}, {'role': 'user', 'content': task['text']}]))
        if str(p.get('fast') or '').strip():
            task.update(answer=str(p['fast']).strip()[:4000], fast=True, status='done')
            for w in ws:
                w.update(status='done', bubble='answered from memory — no browsing needed')
            return task
        halves = [str(p.get('a') or task['text']), str(p.get('b') or task['text'])]
        for w, g in zip(ws, halves):
            w['goal'] = g
        task['status'] = 'working'
        got = await asyncio.gather(*(_window(task, w, ask, pages[w['i']], wait_human, names[w['i']]) for w in ws), return_exceptions=True)
        if any(isinstance(g, Stopped) for g in got) and not any(isinstance(g, str) for g in got):
            raise next(g for g in got if isinstance(g, Stopped))
        parts = [f"{names[w['i']]} ({w['goal']}):\n{w['answer'] or '(nothing)'}" for w in ws]
        task['status'] = 'merging'
        if len(ws) > 1:
            task['answer'] = (await _ask(task, None, ask, lead, [{'role': 'system', 'content': MERGE_SYS}, {'role': 'user', 'content': '\n\n'.join(parts)}])).strip()[:6000]
        else:
            task['answer'] = ws[0]['answer']
        task['status'] = 'done'
    except Stopped as e:
        task.update(status='stopped', why=str(e) or 'stopped by you')
        task['answer'] = task['answer'] or '\n\n'.join(f"{names[w['i']]}: {w['answer']}" for w in ws if w.get('answer')) or None
    except Exception as e:
        task.update(status='error', why=str(e)[:160])
    for w in ws:
        if w['status'] not in ('done',):
            w['status'] = 'done' if task['status'] == 'done' else task['status']
    return task
