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
import time
from cat_policy import RESEARCH_ACTIONS, RULES, refusal, research_ok

STEP_MAX = 8
GO_STEPS = 30     # 🏇 "let it go" (owner Q1): a task may run this many steps a window — it stops only when done, at its $ cap, or for a human
READ_MAX = 3500
BLOCKED = re.compile(r'(?i)pass(word|code)|seed|mnemonic|recovery phrase|private key|cvv|card number')

PLAN_SYS = ('You lead two AI models working for a FEELESS user. If you can answer the task well from what you already know, put the answer in "fast". '
            'Otherwise split it into two halves the two models research in their own browsers at the same time. Answer ONLY JSON: '
            '{"fast": "<answer or empty>", "a": "<your half>", "b": "<the other model\'s half>"}')
ACT_SYS = ('You are {name}, an AI model working in your OWN web browser for a FEELESS user, who watches you. Your half of the task: {goal}\n'
           'Each turn pick ONE action. Answer ONLY JSON: {{"thought": "<= 12 words: what you are doing and why", "action": "feeless|open|search|click|type|upload|new_login|ask_login|media|human|draft|build|note|answer", '
           '"tool": "<feeless tool>", "url": "", "q": "", "text": "<visible text of the link / button to click>", "label": "<field label or placeholder>", "value": "", "say": "<your answer, when action is answer>"}}\n'
           'FEELESS FIRST: for anything about coins, trading, perps, pools or prices use action "feeless" (tool: coin|trench|perps|pools|gaps, q: the coin / ticker) '
           'BEFORE any outside website — FEELESS is where this user trades. Never launch a coin or pool or create an agent ON FEELESS (on any other site, do as the user asks); never create a FeeCat.\n'
           'ACCOUNTS — DO IT YOURSELF FIRST: when a task needs an account, make it: first its own email at a free provider (Proton Mail, Tuta, GMX) '
           'with "new_login", then the site\'s sign-up with that email. Hand to the human ONLY for the user\'s OWN accounts (Polymarket, Kalshi, banks, '
           'exchanges, their socials), CAPTCHAs, phone / SMS codes, payments and ID checks — never stop for anything you can do yourself.\n'
           'SIGN-UPS: action "new_login" (url = the site, label = the username / email you will use) makes a strong password that is sealed for the user; '
           'then type it with action "type" and value "{{password}}" — you never see or invent a password. A site that needs the USER\'s own account → '
           '"ask_login" (url = the site): they type it privately, then you type "{{username}}" and "{{password}}". A CAPTCHA / phone / email code / legal ID → "human". '
           'MEDIA: action "media" (url = an https image / video link, text = its title) saves it in the user\'s media drawer for campaigns. '
           'FILES the user attached: action "upload" (label = the page\'s file field / its button text, value = the file name) puts it on the page — e.g. a coin image.\n'
           'Rules: never type a password, card number or seed phrase — use "human" for any sign-in / sign-up / CAPTCHA. Never claim what the page does not show. '
           'Use draft to save writing, build to save a complete HTML page for the live sandbox preview, note to keep a fact in YOUR scratch pad (thrown away '
           'after the task unless it is the best), handoff to pass a result to your partner mind (say = what they need — e.g. your research for their post). '
           'Put artifact / note / handoff content in say. '
           'STUCK: never repeat a failed action more than twice: try another route, or report it. Needing the human never ends your work: ask with "human", saying exactly what you need, and carry on with whatever does not depend on it. '
           'Near the $ cap, stop and deliver what is done. '
           'Finish with "answer" (with the sources you used) within {steps} steps.')
MERGE_SYS = ('Combine the two halves (and their scratch notes) into ONE clear answer for the user, keep the sources, say what is still uncertain. '
             'Then pick the few facts worth keeping for next time — only what BOTH halves support or what is clearly vital. Answer ONLY JSON: '
             '{"answer": "<plain text, short>", "keep": ["<fact + source>", "..."]}')
JOBS_SYS = 'Each model had its OWN job. Present both results for the user, each under its job, plain text — no merging, nothing invented.'
MODES = ('plan', 'jobs')   # 🧠🤝 plan together → split → merge · 🎯 each mind its own job (owner 2026-10-30: "only 2 options")
KEEP_MAX = 6
MIND_KEEP, MIND_CLOUD_MAX = 3, 20   # ☁ each mind keeps its last 3 notes per task in its own cloud (20 max)


def split_jobs(text, n=2):
    """'A: write the video script  B: make the posts' → one job per mind. One job only (or no labels): the first mind owns it and the other SUPPORTS —
    the same job never runs twice on the owner's credit (owner 2026-10-30: "if separate jobs only one knows to work and other may get info")."""
    t = str(text or '')
    parts = re.split(r'(?im)(?:^|\s)(?:mind\s*)?([AB])\s*[:\-—]\s*', t)
    jobs = {k.upper(): v.strip() for k, v in zip(parts[1::2], parts[2::2]) if v.strip()}
    whole = t.strip()
    if n < 2:
        return [whole]
    a, b = jobs.get('A'), jobs.get('B')
    if a and b:
        return [a, b]
    if a or b:   # 🎯 addressed to ONE mind ("B: …") → only that mind works, the other stays idle and spends nothing (owner 2026-10-31: "i asked model b and model a worked")
        return [a or '', b or '']
    lead = whole
    helper = f'SUPPORT ROLE, your partner owns this job: "{lead[:300]}". Do NOT do it too. Check their facts, look up what they will need and pass it with handoff, then answer with what you checked.'
    return [lead, helper]


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


def new_task(tid, text, models, cap, steps=STEP_MAX, mode='plan', mind_caps=None):
    return {'mindCaps': list(mind_caps or []), 'id': tid, 'text': str(text)[:2000], 'mode': mode if mode in MODES else 'plan', 'status': 'planning', 'cap': float(cap), 'cost': 0.0, 'answer': None, 'fast': False, 'stepsMax': int(steps), 'tools': {'browse': True, 'forms': True},
            'windows': [{'i': i, 'model': m, 'goal': None, 'status': 'idle', 'bubble': 'waiting for the plan', 'url': None, 'title': None,
                         'steps': [], 'human': None, 'answer': None, 'cost': 0.0, 'scratch': [], 'coin': None} for i, m in enumerate(models[:8])]}


RESEARCH_HOW = ('\nRESEARCH ORDER: 1) feeless coin <symbol or contract> — it returns the live FEELESS chart snapshot (5m candles as numbers) and the coin\'s '
                'research links; 2) open those links: the X live search for the contract first (who is calling it, bots vs people), then RugCheck / Solscan / '
                'DexScreener; 3) answer with what the chart AND the research say, each fact with where you read it. Never guess a number you did not read.')


class Stopped(Exception):
    pass


async def _ask(task, w, ask, model, messages):
    # One in-flight model call per task: concurrent windows cannot both spend the same remaining budget.
    lock = task.setdefault('_ask_lock', asyncio.Lock())
    async with lock:
        if task.get('stop'):
            raise Stopped()
        if task['cost'] >= task['cap']:
            raise Stopped(f"budget reached (${task['cost']:.4f} of ${task['cap']:.4f})")
        caps = task.get('mindCaps') or []
        mine = float(caps[w['i']] or 0) if w is not None and w['i'] < len(caps) else 0.0
        if mine and w['cost'] >= mine:
            raise Stopped(f"this mind reached its ${mine:g} limit for one task")
        bound = getattr(ask, 'cost_bound', lambda *_: 0)(model, messages)
        if task['cost'] + bound > task['cap']:
            raise Stopped('budget reached: the next call could exceed your remaining cap')
        text, usd = await ask(model, messages)
        task['cost'] = round(task['cost'] + float(usd or 0), 6)
        if w is not None:
            w['cost'] = round(w['cost'] + float(usd or 0), 6)
        return text


def _step(w, thought, action, detail=''):
    w['bubble'] = f"{thought}" if thought else action
    w['steps'] = (w['steps'] + [{'action': action, 'thought': str(thought or '')[:120], 'detail': str(detail or '')[:160], 'at': time.time()}])[-40:]


async def _window(task, w, ask, page, wait_human, name, feeless=None):
    """One model working its half in its own browser. → its answer (or what it has when stopped)."""
    w['status'] = 'working'
    seen = ''
    n_max = int(task.get('stepsMax') or STEP_MAX)
    for _n in range(n_max):
        mine = (task.get('clouds') or {}).get(w['i']) or []   # ☁ its own cloud from earlier tasks
        got = [h['text'] for h in task.get('handoffs') or [] if h['from'] != w['i']][-4:]   # 📦 what its partner handed over
        extra = (f"\nYOUR CLOUD (your notes from earlier tasks): {' | '.join(mine)[:600]}" if mine else '') + (f"\nFROM YOUR PARTNER: {' | '.join(got)[:900]}" if got else '')
        if task.get('research'):   # 📰 a trader: FEELESS's chart first, then the chart's own research doors (X search by the contract — signed in when the owner saved X)
            extra += RESEARCH_HOW
        msgs = [{'role': 'system', 'content': RULES + '\nEnabled tools: ' + str(task.get('tools', {})) + '\n' + ACT_SYS.format(name=name, goal=w['goal'], steps=n_max) + extra},
                {'role': 'user', 'content': f"URL: {page.url or '(blank)'}\nTITLE: {page.title or ''}\nPAGE:\n{seen[:READ_MAX]}"}]
        raw = await _ask(task, w, ask, w['model'], msgs)
        a = parse_json(raw)
        act = str(a.get('action') or '').lower()
        thought = str(a.get('thought') or '').strip()
        if task.get('research') and act not in RESEARCH_ACTIONS:   # 📰 a trader's window only reads coins + narrative
            _step(w, f'research only: no "{act}"', 'refused')
            seen = f'(research only: "{act}" is not allowed — read coin data, crypto news or X, then answer)'
            continue
        if task.get('research') and act in ('open', 'ask_login') and not research_ok(a.get('url') or '', act == 'ask_login'):
            _step(w, thought or 'stays on research sites', 'blocked', str(a.get('url') or '')[:120])
            seen = '(research only: that site is not on the research list — use FEELESS, coin data sites, crypto news or X)'
            continue
        if act == 'answer' or not act:
            w['answer'] = str(a.get('say') or thought or str(raw or '').strip() or 'no answer')[:4000]   # a model that just answers in plain words still answers
            _step(w, thought or 'done', 'answer')
            break
        need = {'open': 'browse', 'search': 'browse', 'click': 'forms', 'type': 'forms', 'draft': 'storage', 'build': 'build'}.get(act)   # note = its own scratch pad, always on
        if need and not task.get('tools', {}).get(need, False):
            why = f'Refused: {need} tool is disabled for this job.'
            task.setdefault('refusals', []).append(why)
            _step(w, why, 'refused')
            seen = why
            continue
        if act == 'feeless':   # 🧰 our own tools first — read-only, always on
            key_ = f"{str(a.get('tool') or '').lower()} {str(a.get('q') or '').lower().lstrip('$')}".strip()
            if key_ in w.setdefault('asked', []):   # 🔁 the same read again = a stuck loop (a real run asked "coin BONK" 4×): point it forward
                _step(w, 'already read this', 'feeless', key_)
                seen = f'(you already read "{key_}" — its result is above in your notes. Move on: open the research links it gave you, or answer.)\n' + seen[:READ_MAX // 2]
                continue
            w['asked'].append(key_)
            seen, coin = await feeless(a.get('tool'), a.get('q') or '') if feeless else ('FEELESS tools are not connected right now.', None)
            if coin:
                w['coin'] = coin
            w['url'], w['title'] = f"feeless:{str(a.get('tool') or '')[:12]}", 'FEELESS'
            _step(w, thought, 'feeless', f"{a.get('tool') or ''} {a.get('q') or ''}".strip())
            continue
        if act == 'handoff':   # 📦 pass a result to the other mind — even on separate jobs they work together
            task['handoffs'] = (task.get('handoffs') or []) + [{'from': w['i'], 'text': str(a.get('say') or thought)[:600]}]
            _step(w, thought, 'handoff', 'handed to its partner')
            seen = 'Handed to your partner.'
            continue
        if act == 'note':   # 🗒 its own throwaway scratch pad — the merge keeps only the best for the main cloud
            w['scratch'] = (w['scratch'] + [str(a.get('say') or thought)[:400]])[-12:]
            _step(w, thought, 'note', 'kept in its scratch pad')
            seen = 'Noted in your scratch pad.'
            continue
        if act in ('draft', 'build'):
            content = str(a.get('say') or '')[:50000]
            task.setdefault('artifacts', []).append({'kind': act, 'title': str(a.get('text') or act)[:80], 'content': content, 'model': w['model']})
            _step(w, thought, act, 'Saved for owner review')
            seen = 'Artifact saved for owner review.'
            continue
        if act == 'new_login':   # 🔐 a strong password, sealed for the owner at settle — the model only ever types the {{password}} placeholder
            from cat_vault import new_password, site_of
            site = site_of(a.get('url') or page.url)
            w['pw'] = {'site': site, 'user': str(a.get('label') or '')[:120], 'pw': new_password()}
            task.setdefault('logins', []).append(w['pw'])
            _step(w, thought, 'new_login', f"{site} · {w['pw']['user']}")
            seen = f'A strong password for {site} is ready and sealed for the user. Type it with value "{{{{password}}}}".'
            continue
        if act == 'media':
            task.setdefault('media', []).append({'url': str(a.get('url') or '')[:500], 'title': str(a.get('text') or '')[:80]})
            _step(w, thought, 'media', str(a.get('text') or a.get('url') or '')[:80])
            seen = 'Saved to the media drawer.'
            continue
        placeholder = act == 'type' and any(x in str(a.get('value') or '') for x in ('{{password}}', '{{username}}')) and w.get('pw')
        if act == 'type' and not placeholder and blocked_value(a.get('label'), a.get('value')):
            act, a['why'] = 'human', 'it wanted to type a secret — that is yours to type'
        if act == 'ask_login':   # 🔑 the USER's own login: a private form in their window — sealed for them, the model only ever types the placeholders
            from cat_vault import site_of
            w['human'] = {'why': f"log in to {site_of(a.get('url') or page.url)}", 'url': page.url, 'kind': 'login', 'site': site_of(a.get('url') or page.url)}
        elif act == 'human':
            w['human'] = {'why': str(a.get('why') or thought or 'a person is needed here')[:160], 'url': page.url}
        else:
            try:
                if act == 'open':
                    seen = await page.goto(str(a.get('url') or ''))
                elif act == 'search':
                    seen = await page.search(str(a.get('q') or w['goal']))
                elif act == 'click':
                    seen = await page.click(str(a.get('text') or ''))
                    if task.get('research') and page.url and not research_ok(page.url):   # a link off the research list → straight back
                        seen = '(research only: that link left the research sites — you are back)\n' + await page.goto(w['url'] if str(w.get('url') or '').startswith('http') else 'https://html.duckduckgo.com/html/?q=bitcoin')
                elif act == 'upload':   # ☁ a file the owner attached (its storage) onto this page's file field
                    f_ = next((f for f in task.get('files') or [] if f['name'] == str(a.get('value') or '')), None) or ((task.get('files') or [None])[0] if len(task.get('files') or []) == 1 else None)
                    seen = await page.upload(str(a.get('label') or ''), f_) if f_ else '(no attached file by that name — the user attached: ' + (', '.join(f['name'] for f in task.get('files') or []) or 'none') + ')'
                elif act == 'type':
                    val = str(a.get('value') or '').replace('{{password}}', w['pw']['pw']).replace('{{username}}', w['pw']['user']) if placeholder else str(a.get('value') or '')
                    seen = await page.type(str(a.get('label') or ''), val)
                else:
                    seen = f'(unknown action {act})'
            except Exception as e:
                seen = f'(that did not work: {str(e)[:120]})'
                if isinstance(e, ValueError):
                    task.setdefault('refusals', []).append(str(e)[:160])
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


def _failed(ws, got):
    """A window whose model call or page blew up says so — never left 'working' forever under a 'done' task (owner 2026-10-31: a stuck window)."""
    for w, g in zip(ws, got):
        if isinstance(g, Exception) and not isinstance(g, Stopped):
            w.update(status='error', bubble=f'error: {str(g)[:80]}', answer=w['answer'] or f'(error) {str(g)[:160]}')


async def run(task, ask, pages, wait_human, names=('Model A', 'Model B'), feeless=None):
    """The whole task. `ask(model, messages)` → (text, $) · `pages[i]` = window i's page driver · `wait_human(i)` → True continue / False stop."""
    ws = task['windows']
    try:
        why = refusal(task['text'])
        if why:
            task.setdefault('refusals', []).append(why)
            raise Stopped(why)
        lead = ws[0]['model']
        if len(ws) > 1 and sum(map(bool, split_jobs(task['text'], len(ws)))) == 1:   # 🎯 "A: …" / "B: …" in either mode = that mind alone
            task['mode'] = 'jobs'
        if task.get('mode') == 'jobs':   # 🎯 each mind its own job: no plan call, no merge — both results, each under its job
            for w, job in zip(ws, split_jobs(task['text'], len(ws))):
                w['goal'] = job
                if not job:
                    w.update(status='done', bubble='not asked — idle')
            on = [w for w in ws if w['goal']]
            task['status'] = 'working'
            got = await asyncio.gather(*(_window(task, w, ask, pages[w['i']], wait_human, names[w['i']], feeless) for w in on), return_exceptions=True)
            _failed(on, got)
            if any(isinstance(g, Stopped) for g in got) and not any(isinstance(g, str) for g in got):
                raise next(g for g in got if isinstance(g, Stopped))
            task['answer'] = '\n\n'.join(f"{names[w['i']]} · {w['goal'][:80]}\n{w['answer'] or '(nothing)'}" for w in on)[:8000]
            task['keep'] = [f"{names[w['i']]}: {str(w['answer'] or '')[:200]}" for w in on if w.get('answer')][:KEEP_MAX]
            task['status'] = 'done'
            return _clean(task)
        p = parse_json(await _ask(task, ws[0], ask, lead, [{'role': 'system', 'content': RULES + '\n' + PLAN_SYS}, {'role': 'user', 'content': task['text']}]))
        if str(p.get('fast') or '').strip():
            task.update(answer=str(p['fast']).strip()[:4000], fast=True, status='done')
            for w in ws:
                w.update(status='done', bubble='answered from memory — no browsing needed')
            return task
        halves = [str(p.get('a') or task['text']), str(p.get('b') or task['text'])]
        for i, w in enumerate(ws):
            w['goal'] = halves[i] if i < len(halves) else f'Independently verify the evidence and fill gaps: {task["text"]}'
        task['status'] = 'working'
        got = await asyncio.gather(*(_window(task, w, ask, pages[w['i']], wait_human, names[w['i']], feeless) for w in ws), return_exceptions=True)
        _failed(ws, got)
        if any(isinstance(g, Stopped) for g in got) and not any(isinstance(g, str) for g in got):
            raise next(g for g in got if isinstance(g, Stopped))
        parts = [f"{names[w['i']]} ({w['goal']}):\n{w['answer'] or '(nothing)'}" + (f"\nscratch: {' | '.join(w['scratch'])}" if w.get('scratch') else '') for w in ws]
        task['status'] = 'merging'
        if len(ws) > 1:
            raw = (await _ask(task, None, ask, lead, [{'role': 'system', 'content': MERGE_SYS}, {'role': 'user', 'content': '\n\n'.join(parts)}])).strip()
            m = parse_json(raw)
            task['answer'] = str(m.get('answer') or raw).strip()[:6000]
            task['keep'] = [str(x)[:240] for x in (m.get('keep') or []) if str(x).strip()][:KEEP_MAX]
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
    return _clean(task)


def _clean(task):
    """🧹 the scratch pads are throwaway: what mattered is in task['keep'] (→ the agent's main cloud); the rest is dropped, its count kept.
    A window's live password leaves the window here (task['logins'] carries it to the sealed vault at settle, then is cleared)."""
    for w in task['windows']:
        w['scratchN'] = len(w.get('scratch') or []); w['best'] = (w.get('scratch') or [])[-MIND_KEEP:]; w['scratch'] = []   # ☁ its best notes → its own cloud
        w.pop('pw', None)
    return task
