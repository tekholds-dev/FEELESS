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
import evidence_marks as _marks
import asyncio
import json
import re
import time
from urllib.parse import quote_plus
from agent_mail import SOURCES
from cat_policy import RESEARCH_ACTIONS, RULES, check_url, refusal, research_ok
from cat_policy import is_post as _is_post
import pow as _pow

STEP_MAX = 8
SEARCH_URL = 'https://html.duckduckgo.com/html/?q='
GO_STEPS = 30     # 🏇 "let it go" (owner Q1): a task may run this many steps a window — it stops only when done, at its $ cap, or for a human
READ_MAX = 3500
BLOCKED = re.compile(r'(?i)pass(word|code)|seed|mnemonic|recovery phrase|private key|cvv|card number')

PLAN_SYS = ('You lead two AI models working for a FEELESS user. If you can answer the task well from what you already know, put the answer in "fast". '
            'Otherwise split it into two halves the two models research in their own browsers at the same time. Answer ONLY JSON: '
            '{"fast": "<answer or empty>", "a": "<your half>", "b": "<the other model\'s half>"}')
ACT_SYS = ('You are {name}, an AI model working in your OWN web browser for a FEELESS user, who watches you. Your half of the task: {goal}\n'
           'Each turn pick ONE action. On your FIRST turn also add "plan": ["step 1", "step 2", "step 3"] — your 3-step plan (<= 8 words each), then follow it. Answer ONLY JSON: {{"thought": "<= 12 words: what you are doing and why", "action": "feeless|open|search|scroll|click|type|snapshot|pull|upload|new_login|ask_login|media|human|draft|build|note|answer", '
           '"tool": "<feeless tool>", "url": "", "q": "", "text": "<visible text of the link / button to click>", "label": "<field label or placeholder>", "value": "", "facts": [{{"label":"liquidity","value":"$35K","support":"exact short page excerpt containing $35K"}}], "say": "<your answer, when action is answer>"}}\n'
           'YOU SEE THE SCREEN: the page below is what is ON SCREEN right now, top to bottom. To see more, "scroll" (q: "down" or "up"); to look closer, "click" an item by its visible text. Browse like a person — scroll, open what interests you, compare.\n'
           'FEELESS FIRST: for anything about coins, trading, perps, pools or prices use action "feeless" (tool: coin|trench|perps|pools|gaps|colony, q: the coin / ticker) '
           'BEFORE any outside website — FEELESS is where this user trades. Never launch a coin or pool or create an agent ON FEELESS (on any other site, do as the user asks); never create a FeeCat.\n'
           'ACCOUNTS — DO IT YOURSELF FIRST: when a task needs an account, use your own mailbox, then the site\'s sign-up with that email and "new_login". ' + SOURCES + ' Hand to the human ONLY for the user\'s OWN accounts (Polymarket, Kalshi, banks, '
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
           'Finish with "answer" within {steps} steps: say = at most 2 short lines (30 words) — the pick, the numbers you READ, the source. Every word costs the user: never long. '
           'Never answer before you opened the site the task names.')
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


FILLER = re.compile(r"(?i)\b(?:please|pls|can|could|you|u|i|me|my|we|our|want|wanna|wona|need|to|the|a|an|and|then|for|of|on|in|with|that|thats|this|these|those|"
                    r"it|is|are|be|do|go|get|find|give|show|tell|make|report|research|look|up|into|about|some|any|all|just|like|etc|lol|ok|okay|"
                    r"within|steps?|minutes?|mins?|now|today|feeless|support|role|partner|owns|job|check|their|facts?)\b")


def search_terms(goal):
    """🔎 What a window types into the search box: the request's KEYWORDS (coins, names, topics) — never the owner's whole sentence (owner 2026-11-01)."""
    g = str(goal or '')
    if g.startswith('SUPPORT ROLE'):
        g = g.split('"')[1] if '"' in g else g
    words = [w for w in re.sub(r'[^\w$.\-\s]', ' ', FILLER.sub(' ', g)).split() if len(w) > 1][:7]
    return ' '.join(words) or g[:60]


def job_label(goal):
    """What the owner reads above a mind's answer: its job — never the internal support instructions (owner 2026-11-01: no prompt footprints)."""
    g = str(goal or '')
    return "checked its partner's facts" if g.startswith('SUPPORT ROLE') else g[:80]


def ended_note(w, page, why):
    """A mind that stopped without an answer: what stopped it + what it had kept — never its raw inner thought."""
    kept = ' · '.join(str(x)[:120] for x in (w.get('scratch') or [])[-2:])
    where = str(getattr(page, 'title', '') or getattr(page, 'url', '') or '')[:80]
    return f"⏹ {why}" + (f" (last on {where})" if where else '') + (f". Kept: {kept}" if kept else '.')


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


async def _after_human(w, page):
    """Back from a handoff: the page as it is now — or, when the owner (or the timer) sent it to another source, that source instead."""
    to = w.pop('redirect', None)
    if to:
        seen = await page.goto(to)
        w['url'], w['title'] = page.url, page.title
        _step(w, f'blocked there — going to {to.split("://")[-1]} instead', 'open', to)
        w['_page'] = seen
        return f'(the last site was blocked — you are now on {to.split("://")[-1]})\n' + str(seen)
    return await page.read()


def new_task(tid, text, models, cap, steps=STEP_MAX, mode='plan', mind_caps=None):
    return {'mindCaps': list(mind_caps or []), 'id': tid, 'text': str(text)[:2000], 'mode': mode if mode in MODES else 'plan', 'status': 'planning', 'cap': float(cap), 'cost': 0.0, 'answer': None, 'fast': False, 'stepsMax': int(steps), 'tools': {'browse': True, 'forms': True},
            'windows': [{'i': i, 'model': m, 'goal': None, 'status': 'idle', 'bubble': 'waiting for the plan', 'url': None, 'title': None,
                         'steps': [], 'human': None, 'answer': None, 'cost': 0.0, 'scratch': [], 'coin': None} for i, m in enumerate(models[:8])]}


RESEARCH_HOW = ('\nRESEARCH ORDER: 1) feeless coin <symbol or contract> — it returns the live FEELESS chart snapshot (5m candles as numbers) and the coin\'s '
                'research links; 2) open those links: the X live search for the contract first (who is calling it, bots vs people), then RugCheck / Solscan / '
                'DexScreener; 3) answer with what the chart AND the research say, each fact with where you read it. Never guess a number you did not read.')


PARKED = '⏸ parked'   # ⏸ owner 2026-10-31: "no human interaction within 5 min → the agent moves on and files it to come back to"


class Stopped(Exception):
    pass


SITE_RE = re.compile(r'(?i)(?<![@\w.])((?:https?://)?(?:[a-z0-9-]+\.)+[a-z]{2,10}(?:/[^\s"\')]*)?)')


def full_url(u):
    """🔗 "pump.fun" → "https://pump.fun" (owner 2026-10-31: a model's bare address was refused 8× and the window never left about:blank)."""
    u = str(u or '').strip().rstrip('.,;')
    return u if not u or '://' in u else 'https://' + u.lstrip('/')


SCROLLS_PER_PAGE = 4   # 🖱 a page is read from its snapshot; at most this many scrolls on one page

def step_sig(act, a, url, seen=''):
    """The fingerprint of one step: what it did, where, at what. A scroll includes where the view sat, so a scroll back over the same spot repeats."""
    at = re.search(r'view (\d+)% down', str(seen or ''))
    tgt = str(a.get('url') or a.get('q') or a.get('text') or a.get('label') or '').strip().lower()[:120]
    if act == 'scroll':
        tgt = f"{'up' if tgt.startswith('up') else 'down'}@{at.group(1) if at else '?'}"
    return f"{act}|{str(url or '').split('#')[0].rstrip('/')}|{tgt}"


def repeat_why(w, act, sig, url, prior=()):
    """Why this step would repeat itself (None = new). Reading the same site again for something else is fine; the very same step is not."""
    if act in ('answer', 'note', 'human', 'ask_login', 'feeless'):
        return None
    if sig in (w.get('sigs') or []):
        return 'you already did exactly this step'
    if _pow.step_hash(sig) in set(prior or ()):
        return 'this browsing step was already filed in an earlier PoW'
    if act == 'scroll' and sum(1 for x in w.get('sigs') or [] if x.startswith(f"scroll|{str(url or '').split('#')[0].rstrip('/')}|")) >= SCROLLS_PER_PAGE:
        return f'{SCROLLS_PER_PAGE} scrolls on this page already — its PAGE SNAPSHOT has the rest'
    return None


REPEAT_MAX = 3   # 🔁 the third repeat of a read it already has ends its turn (a real run paid for 'already read this' 15×)
STEP_PACE = 2.5   # s: the least time between two moves in a live window
DONE_WORDS = frozenset({'report', 'final', 'final_answer', 'done', 'finish', 'respond', 'reply', 'result'})


def same_page(at, url):
    """pump.fun/ == https://pump.fun == pump.fun/?__cf_chl_rt_tk=… (same host + path, query ignored)."""
    from urllib.parse import urlsplit
    a, b = urlsplit(str(at or '')), urlsplit(full_url(url))
    return bool(a.hostname) and (a.hostname or '').removeprefix('www.') == (b.hostname or '').removeprefix('www.') and a.path.rstrip('/') == b.path.rstrip('/')


BROWSE_FOR = re.compile(r'(?i)\b(?:for|about|around|spend)\s+(?:about\s+)?(\d{1,2})(?:\s*(?:-|to)\s*\d{1,2})?\s*(min(?:ute)?s?|m|sec(?:ond)?s?|s)\b')


def _on_list(task, url, login=False):
    """The research list, plus the one site the owner scanned, signed in to and named for this proof."""
    if research_ok(url, login):
        return True
    try:
        host = check_url(url)
    except ValueError:
        return False
    return any(host == h or host.endswith('.' + h) for h in task.get('alsoHosts') or [])


def browse_secs(goal):
    """⏱ "browse pump.fun for 1-2 minutes" → 60 (the lower bound, ≤ 10 min) — the window keeps browsing that long before it may answer (owner 2026-10-31:
    it answered from the first page in 27 s and never clicked)."""
    m = BROWSE_FOR.search(str(goal or ''))
    if not m:
        return 0
    n = int(m.group(1)) * (1 if m.group(2).lower().startswith('s') else 60)
    return max(0, min(600, n))


def named_site(goal):
    """The site the ask names ("Browse pump.fun …") → its address, or None."""
    m = SITE_RE.search(str(goal or ''))
    return full_url(m.group(1)) if m and not m.group(1).lower().startswith(('e.g', 'i.e')) else None


async def _ask(task, w, ask, model, messages):
    # One in-flight model call per task: concurrent windows cannot both spend the same remaining budget.
    # A PoW pair round is the exception: each mind has its own ceiling (mindCaps + a reply room sized to it), so each mind gets its own lane.
    lock = task.setdefault('_ask_locks', {}).setdefault(w['i'], asyncio.Lock()) if task.get('pows') and w is not None else task.setdefault('_ask_lock', asyncio.Lock())
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
        t0_ = time.time()
        text, usd = await ask(model, messages)
        task['cost'] = round(task['cost'] + float(usd or 0), 6)
        if w is not None:
            w['cost'] = round(w['cost'] + float(usd or 0), 6)
            w['modelSec'] = round(float(w.get('modelSec') or 0) + time.time() - t0_, 2); w['modelCalls'] = int(w.get('modelCalls') or 0) + 1   # ⏱ where research time goes
        return text


def _step(w, thought, action, detail=''):
    w['bubble'] = f"{thought}" if thought else action
    w['steps'] = (w['steps'] + [{'action': action, 'thought': str(thought or '')[:120], 'detail': str(detail or '')[:160], 'at': time.time()}])[-40:]


def _pow_of(task, w):
    """⛏ The PoW this window works: a pair round gives each mind its own coin, a single round lives in window 0."""
    return (task.get('pows') or {}).get(w['i']) if task.get('pows') else task.get('pow') if w['i'] == 0 else None


async def _window(task, w, ask, page, wait_human, name, feeless=None):
    """One model working its half in its own browser. → its answer (or what it has when stopped)."""
    w['status'] = 'working'
    seen = ''
    n_max = int(task.get('stepsMax') or STEP_MAX)
    pw = _pow_of(task, w)   # ⛏ a Proof-of-Work run (pow.py): its rules are code, whatever the model
    if pw and task.get('powPlan'):   # 🗺 a folder's research round follows the folder's ONE joint plan — no second plan of its own
        w['plan'] = list(task['powPlan'])[:3]
    site = _pow.start_url(pw) if pw else named_site(w['goal']) or (None if str(page.url or '').startswith('http') else SEARCH_URL + quote_plus(search_terms(w['goal'])))   # 🔎 a blank window starts on a search
    if site and (_on_list(task, site) if task.get('research') else True):   # 🧭 the ask names a site → its window opens there first (a model once answered "I haven't visited pump.fun")
        try:
            seen = w['_page'] = await page.goto(site)
            w['url'], w['title'] = page.url, page.title
            _step(w, f'opening {site.split("://")[-1]}', 'open', site)
            from cat_browser import needs_human
            why_ = needs_human(page.url, seen)
            if why_ and 'duckduckgo.com' in site:   # the search engine walled us: the coin's DexScreener page / a plain dex search instead — no person needed
                site = _pow.start_url(pw, blocked=True) if pw else 'https://dexscreener.com/search?q=' + quote_plus(str(w['goal'] or '')[:40])
                seen = w['_page'] = await page.goto(site)
                w['url'], w['title'] = page.url, page.title
                why_ = needs_human(page.url, seen)
            if why_:   # a checkpoint on the very first page → straight to the person, no steps burned on it
                w['human'] = {'why': why_, 'url': page.url}
                w['status'], w['bubble'] = 'human', f"✋ needs you: {why_}"
                go_ = await wait_human(w['i'])
                w['human'] = None
                if not go_:
                    raise Stopped(w.pop('parked', None) or 'stopped by you')
                w['status'] = 'working'
                seen = w['_page'] = await _after_human(w, page)
        except Exception as e:
            seen = f'(could not open {site}: {str(e)[:120]})'
    if pw and feeless:   # ⛏ FEELESS first, done by the engine (free, server-side): it is the PoW's first site — the model only pulls from it
        try:
            fr_, coin_ = await feeless('coin', pw.get('mint') or pw['sym'])
            w.setdefault('asked', []).append(f"coin {str(pw.get('mint') or '').lower()}")
            if coin_:
                w['coin'] = coin_
            w['url'], w['title'] = 'feeless:coin', 'FEELESS'
            _pow._site(pw, 'feeless:coin')
            seen = w['_page'] = f"FEELESS LIVE READ (your first site — save a verified fact snapshot):\n{str(fr_)[:READ_MAX // 2]}\n\nTHE SEARCH PAGE:\n{str(seen)[:READ_MAX // 2]}"
            _step(w, 'reads the coin on FEELESS first', 'feeless', f"coin ${pw['sym']}")
        except Exception as e:   # noqa: BLE001 — no FEELESS read: the route still runs
            seen = f'(FEELESS read failed: {str(e)[:80]})\n' + str(seen)
    min_s = browse_secs(w['goal']); t_start = time.time()
    if min_s:   # enough steps to fill the time it was asked to browse (~6 s a step), never past the long budget
        n_max = max(n_max, min(GO_STEPS, min_s // 6 + 3))
    last_ = 0.0
    for _n in range(n_max):
        if getattr(page, 'live', False) and time.time() - last_ < STEP_PACE:   # 🐢 a live window moves at a pace you can follow (owner: "not so quick")
            await asyncio.sleep(STEP_PACE - (time.time() - last_))
        last_ = time.time()
        if pw and (w.pop('powNext', False) or _pow.site_done(pw, w.get('url') or page.url)):   # ⛏ this site is done: the engine opens the coin's next page
            seen = await _pow_advance(w, pw, page, wait_human)
        mine = (task.get('clouds') or {}).get(w['i']) or []   # ☁ its own cloud from earlier tasks
        got = [h['text'] for h in task.get('handoffs') or [] if h['from'] != w['i'] and h.get('only', w['i']) == w['i']][-4:]   # 📦 what its partner handed over
        extra = str(task.get('personal') or '') + (f"\nYOUR CLOUD (your notes from earlier tasks): {' | '.join(mine)[:600]}" if mine else '') + (f"\nFROM YOUR PARTNER: {' | '.join(got)[:900]}" if got else '')
        if w.get('plan'):   # 🗺 its own 3-step plan rides every step (owner 2026-11-01: "plan in 3 steps, then execute")
            extra += '\nYOUR 3-STEP PLAN: ' + ' → '.join(f'{k + 1}) {x}' for k, x in enumerate(w['plan']))
        partner_ = next((x.get('plan') for x in task.get('windows') or [] if x is not w and x.get('plan')), None)
        if partner_:   # 🤝 how its partner attacks its half
            extra += "\nYOUR PARTNER'S PLAN: " + ' → '.join(partner_)
        if task.get('knowhow'):   # 🐝 the Colony + 🧭 the sources book: every mind knows both, whatever its prompt
            extra += '\n' + str(task['knowhow'])[:2600]
        if pw:
            extra += '\n' + _pow.RULES + "\nTHE COIN'S PAGES: " + ' · '.join(_pow.links(pw)) + f"\nPOW SO FAR: {_pow.public(pw)['pulls'] or 'no vitals pulled yet'}"
        if task.get('research'):   # 📰 a trader: FEELESS's chart first, then the chart's own research doors (X search by the contract — signed in when the owner saved X)
            extra += RESEARCH_HOW
        # the job + JSON format lead: a short-context model (the free backup keeps the first 4,000 chars) once lost both and answered in prose
        msgs = [{'role': 'system', 'content': ACT_SYS.format(name=name, goal=w['goal'], steps=n_max) + extra + '\n' + RULES + '\nEnabled tools: ' + str(task.get('tools', {}))},
                {'role': 'user', 'content': f"URL: {page.url or '(blank)'}\nTITLE: {page.title or ''}\n"
                 + ((f'The user asked you to BROWSE for {min_s // 60 or min_s} {"min" if min_s >= 60 else "s"} — {max(0, int(min_s - (time.time() - t_start)))} s left: click into the coins / posts you are weighing (click their name), compare them, then answer.\n'
                     if min_s and time.time() - t_start < min_s else
                     'This page is OPEN in your window — read it first; answer from it when it holds what the task needs (another load can hit a bot check).\n') if str(page.url or '').startswith('http') else '')
                 + f"PAGE:\n{seen[:READ_MAX]}"}]
        raw = await _ask(task, w, ask, w['model'], msgs)
        a = parse_json(raw)
        act = str(a.get('action') or '').lower()
        if not w.get('plan'):   # 🗺 its 3-step plan, from its first reply (no extra call) — the engine's when it gave none
            pl_ = [str(x)[:60] for x in (a.get('plan') if isinstance(a.get('plan'), list) else [])[:3] if str(x).strip()]
            w['plan'] = pl_ if len(pl_) == 3 else (['FEELESS read', "one evidence snapshot per coin page", 'the call'] if pw else ['open the best source', 'read the numbers it needs', 'answer short'])
            _step(w, 'plan: ' + ' → '.join(w['plan']), 'plan')
        if act in DONE_WORDS:   # "report" / "final" / "done" = its answer (a real run was refused twice for saying "report")
            act, a['say'] = 'answer', a.get('say') or '; '.join(f'{k}: {v}' for k, v in a.items() if k not in ('action', 'thought', 'url', 'text', 'label', 'value', 'tool', 'q') and v)
        if act in ('open', 'ask_login') and a.get('url'):
            a['url'] = full_url(a['url'])
        thought = str(a.get('thought') or '').strip()
        if task.get('research') and act not in RESEARCH_ACTIONS and (act or a):   # 📰 a trader's window only reads coins + narrative (plain prose = its answer, below)
            _step(w, f'research only: no "{act}"' if act else 'no action in its reply', 'refused')
            seen = (f'(research only: "{act}" is not allowed — read coin data, crypto news or X, then answer)' if act else
                    '(your reply had no "action" — answer ONLY the JSON object, one action)') + '\n' + str(w.get('_page') or '')[:READ_MAX // 2]
            continue
        if task.get('research') and act in ('open', 'ask_login') and not _on_list(task, a.get('url') or '', act == 'ask_login'):
            _step(w, thought or 'stays on research sites', 'blocked', str(a.get('url') or '')[:120])
            seen = '(research only: that site is not on the research list — use FEELESS, coin data sites, crypto news or X)'
            continue
        if act in ('answer', '') and min_s and time.time() - t_start < min_s and _n < n_max - 1:   # ⏱ asked to browse longer: not yet
            left_ = int(min_s - (time.time() - t_start))
            _step(w, f'keeps browsing — {left_} s left of the time you asked', 'browse')
            seen = f'(not yet — the user asked you to browse for {min_s} s, {left_} s left. Click into one of the coins you are weighing by its name, read it, compare.)\n' + str(w.get('_page') or seen)[:READ_MAX]
            continue
        if act == 'snapshot':
            got_ = _pow.snapshot(pw, w.get('url') or page.url, w.get('_page') or seen, a.get('facts')) if pw else {'saved': 0, 'why': 'snapshot is for PoW research'}
            if got_['saved']:
                await _pow_snap(pw, page, w.get('_page') or seen, True)
                task.setdefault('filed', []).extend({'site': x['site'], 'text': f"{x['label']} {x['value']}"[:120]}
                    for x in _pow.pulls(pw)[-got_['saved']:])
            _step(w, thought or got_['why'], 'snapshot' if got_['saved'] else 'refused', got_['why'])
            seen = f"({got_['why']})\n" + str(w.get('_page') or seen)[:READ_MAX // 2]
            continue
        if act == 'pull':   # ⛏ one vital fact read on this page — the PoW rules decide if it is kept
            ok_, why_p = _pow.pull(pw, w.get('url') or page.url, a.get('label'), a.get('value')) if pw else (False, 'pull is for a Proof-of-Work run — use note')
            if ok_:
                await _pow_snap(pw, page, w.get('_page') or seen, True)   # 📸 the page the vital came from
            if ok_:   # 📥 filed to the owner's cabinet the moment it is read
                task.setdefault('filed', []).append({'site': _pow.host_of(w.get('url') or page.url), 'text': f"{_pow.vital(a.get('label'))} {a.get('value')}"[:120]})
            _step(w, thought or why_p, 'pull' if ok_ else 'refused', why_p)
            seen = f'({why_p})\n' + str(w.get('_page') or seen)[:READ_MAX // 2]
            continue
        if pw and (act == 'answer' or not act) and len(_pow.pulls(pw)) < _pow.SITE_PULLS and not w.get('powDone') and _n < n_max - 2:
            w['powNext'] = not act   # ⛏ no answer before the work: pull vitals first (an unreadable reply = a stall: the engine moves on)
            _step(w, 'not yet — pull the vitals first' if act else 'unreadable reply — on to the next site', 'refused')
            seen = '(NOT YET — a PoW answers only after it has pulled vitals: use action "pull" with label + value from THIS page.)\n' + str(w.get('_page') or seen)[:READ_MAX]
            continue
        if act == 'answer' or not act:
            w['answer'] = str(a.get('say') or thought or str(raw or '').strip() or 'no answer')[:600]   # short, always (owner: least usage)   # a model that just answers in plain words still answers
            _step(w, thought or 'done', 'answer')
            break
        need = {'open': 'browse', 'search': 'browse', 'scroll': 'browse', 'click': 'forms', 'type': 'forms', 'draft': 'storage', 'build': 'build'}.get(act)   # note = its own scratch pad, always on
        if need and not task.get('tools', {}).get(need, False):
            why = f'Refused: {need} tool is disabled for this job.'
            task.setdefault('refusals', []).append(why)
            _step(w, why, 'refused')
            seen = why
            continue
        if act == 'click' and _is_post(a.get('text')) and not task.get('tools', {}).get('post', False):   # 📣 only a content agent posts, whatever a page or a model says
            why = 'Refused: only an agent with the content job may post, reply or publish. Its owner can change its job.'
            task.setdefault('refusals', []).append(why)
            _step(w, why, 'refused')
            seen = why
            continue
        if act == 'feeless':   # 🧰 our own tools first — read-only, always on
            key_ = f"{str(a.get('tool') or '').lower()} {str(a.get('q') or '').lower().lstrip('$')}".strip()
            if pw and key_ in w.setdefault('asked', []):   # ⛏ in a PoW a re-read is a stall: the engine moves it to the next site
                w['powNext'] = True
                _step(w, 'already read — on to the next site', 'refused', key_)
                continue
            if key_ in w.setdefault('asked', []):   # 🔁 the same read again = a stuck loop (a real run asked "coin BONK" 4×, another 15×): point it forward
                w['repeats'] = int(w.get('repeats') or 0) + 1
                if w['repeats'] >= REPEAT_MAX:   # 🔀 never stopped, never paid twice: the ENGINE moves it to a page it has not used (owner 2026-11-01)
                    seen = await _divert(task, w, page, wait_human)
                    continue
                _step(w, 'already read this', 'feeless', key_)
                seen = f'(you already read "{key_}" — its result is above in your notes. Move on: open the research links it gave you, or answer.)\n' + seen[:READ_MAX // 2]
                continue
            w['asked'].append(key_)
            seen, coin = await feeless(a.get('tool'), a.get('q') or '') if feeless else ('FEELESS tools are not connected right now.', None)
            if w.get('_page'):   # 📄 the page it read stays in view — it never has to reload it (pump.fun's bot check fires on a reload)
                seen = f"{str(seen)[:READ_MAX // 2]}\n\nTHE PAGE STILL OPEN IN YOUR WINDOW ({page.url}):\n{w['_page'][:READ_MAX // 2]}"
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
            task.setdefault('filed', []).append({'site': _pow.host_of(page.url) or 'its notes', 'text': str(a.get('say') or thought)[:120]})   # 📥 its notes reach the cabinet too
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
            sig_ = step_sig(act, a, page.url, w.get('_page') or seen)
            why_rep = repeat_why(w, act, sig_, page.url, (pw or {}).get('priorSteps'))
            if why_rep:   # 🔁 NEVER the same step twice (owner 2026-10-31: "it scrolled up and down 20 times") — refused, not paid for again
                w['repeats'] = int(w.get('repeats') or 0) + 1
                if w['repeats'] >= REPEAT_MAX:
                    seen = await _divert(task, w, page, wait_human)
                    continue
                _step(w, f'refused a repeat: {why_rep}', 'refused', act)
                seen = f'(REFUSED — {why_rep}. Do something NEW: click a link you have not opened, open another source, or answer now.)\n' + str(seen)[:READ_MAX // 2]
                continue
            why_pw = _pow.step(pw, a.get('url') if act == 'open' else page.url) if pw and act in ('open', 'click', 'scroll') else None
            if why_pw:   # ⛏ the PoW's per-site / site budget — refused before it is paid for; the engine moves it on
                _step(w, f'refused: {why_pw}', 'refused', act)
                seen = f'(REFUSED — {why_pw}.)\n' + str(seen)[:READ_MAX // 2]
                w['powNext'] = True
                continue
            w.setdefault('sigs', []).append(sig_)
            try:
                page.on_cursor = lambda c, w=w: w.__setitem__('cursor', c)   # 🖱 the desk's cursor starts gliding the moment the real mouse does
                if act == 'open' and same_page(page.url, a.get('url')):   # already there: what it read, never a reload (a reload of pump.fun tripped Cloudflare)
                    seen = w.get('_page') or await page.read()
                elif act == 'open':
                    seen = await page.goto(str(a.get('url') or ''))
                elif act == 'scroll':
                    way_ = 'up' if str(a.get('q') or 'down').lower().startswith('up') else 'down'
                    prev_ = [x for x in w['steps'] if x.get('action') == 'scroll'][-1:]
                    if prev_ and (prev_[0].get('detail') or 'down').lower().startswith('up') != (way_ == 'up') and w['steps'][-1].get('action') == 'scroll':
                        raise ValueError('you just scrolled the other way — that part was already read (see the PAGE SNAPSHOT). Act on it, click something, or open another page')
                    page.mind = w['i']
                    seen = await page.scroll(way_)
                elif act == 'search':
                    seen = await page.search(str(a.get('q') or w['goal']))
                elif act == 'click':
                    seen = await page.click(str(a.get('text') or ''))
                    if task.get('research') and page.url and not _on_list(task, page.url):   # a link off the research list → straight back
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
                try:   # what the window shows NOW — a click that timed out on a bot check is handed to the person, never retried blind
                    seen += '\nTHE PAGE NOW:\n' + str(await page.read())[:READ_MAX // 2]
                except Exception:
                    pass
                if isinstance(e, ValueError):
                    task.setdefault('refusals', []).append(str(e)[:160])
            w['url'], w['title'] = page.url, page.title
            if task.get('keepShots') and act in ('open', 'click'):   # 📸 a topic PoB keeps one snapshot of each site, up to 4 per mind
                h_ = _pow.host_of(page.url); rows_ = w.setdefault('_shots', [])
                if h_ and len(rows_) < 4 and not any(x['site'] == h_ for x in rows_):
                    m_ = await _marks.marked_shot(page, _marks.words_of([task.get('topic') or task.get('text') or '']), time.time())   # 🖍 what it read is boxed on the picture
                    if m_:
                        rows_.append({'site': h_, 'url': str(page.url)[:200], 'title': str(page.title or '')[:90], 'jpg': m_['jpg'], 'at': round(time.time()), 'found': list(m_['found'])[:12], 'sha': m_['sha']})
            if pw and act == 'open':
                seen = await _pow_find(w, pw, page) or seen   # a site the model opened itself (CoinMarketCap…): its search gets the CA
            if pw and act in ('open', 'click'):
                await _pow_snap(pw, page, w.get('_page') or seen)
            if getattr(page, 'cursor', None):
                w['cursor'] = page.cursor   # 🖱 its cursor in the live view
            if act in ('open', 'search', 'click', 'scroll') and seen and not str(seen).startswith('('):
                w['_page'] = str(seen)
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
                raise Stopped(w.pop('parked', None) or 'stopped by you')
            w['status'] = 'working'
            seen = await _after_human(w, page)
    else:
        w['answer'] = w['answer'] or ended_note(w, page, 'it ran out of steps before answering')
    if pw:
        _pow.finish(pw, w['answer'])
    w['status'] = 'done'
    return w['answer']


DIVERT = ('https://dexscreener.com/solana', 'https://rugcheck.xyz', 'https://solscan.io', 'https://www.coingecko.com', 'https://defillama.com')


async def _divert(task, w, page, wait_human=None):
    """🔀 A mind that keeps repeating is never stopped (owner 2026-11-01): the engine opens a source it has NOT used this task — the task's best
    sources first (the sources book), then the trusted list, then a fresh search — and it carries on from there."""
    w['repeats'] = 0
    pw = _pow_of(task, w)
    if pw:   # a PoW moves to the coin's next page
        w['powNext'] = True
        return await _pow_advance(w, pw, page, wait_human)
    been = {_pow.host_of(str(x.get('detail') or '')) for x in w.get('steps') or []} | {_pow.host_of(page.url)}
    pool = [u for u in list(task.get('alts') or []) + list(DIVERT) if _pow.host_of(u) not in been and (_on_list(task, u) if task.get('research') else True)]
    u = pool[0] if pool else SEARCH_URL + quote_plus(f"{str(w.get('goal') or '')[:70]} {len(w.get('steps') or [])}")
    try:
        got = await page.goto(u)
    except Exception as e:   # noqa: BLE001 — a dead page is just skipped next time
        got = f'(could not open: {str(e)[:80]})'
    w['url'], w['title'], w['_page'] = page.url or u, page.title, str(got)
    _step(w, f'diverted to {_pow.host_of(u)} — no repeats', 'open', u)
    return f'DIVERTED — you repeated yourself, so the engine opened a NEW page ({_pow.host_of(u)}). Read it and act on it.\n' + str(got)[:READ_MAX]


SNAPS_PER_SITE = 1


async def _pow_snap(pw, page, seen='', saved=False):
    """📸 One snapshot a site, of the page the facts came from (owner 2026-11-03: no same sites, no bot checks): an arrival shot is replaced once when a vital is saved there;
    a bot check or sign-in wall is never kept. It costs nothing: the research browser is already open."""
    if not pw or not getattr(page, 'live', False):
        return
    from cat_browser import needs_human   # the same wall check the research route uses
    h = _pow.host_of(page.url)
    if not h or h.endswith('duckduckgo.com') or h in (pw.get('walled') or []) or needs_human(page.url, seen):
        return
    had = next((x for x in pw.get('_shots') or [] if x['site'] == h), None)
    if had and (had.get('saved') or not saved):
        return
    try:
        marked_ = await asyncio.wait_for(_marks.marked_shot(page, [], time.time()), 8)   # 🖍 the numbers on the page are boxed on the picture
        jpg = (marked_ or {}).get('jpg')
    except Exception:   # noqa: BLE001 — a missed snapshot never stops the research
        jpg = None
    if jpg:
        if had:
            had.update(jpg=jpg, at=round(time.time()), saved=True)
        else:
            pw.setdefault('_shots', []).append({'site': h, 'n': 1, 'jpg': jpg, 'at': round(time.time()), 'saved': saved})


async def _pow_find(w, pw, page):
    """🔎 On a site whose page is not about the coin yet, the engine uses the SITE's search: types the CA, Enter. → the page, or None."""
    m = str(pw.get('mint') or '')
    if not m or m.lower() in str(page.url or '').lower() or not hasattr(page, 'site_search'):
        return None
    got = await page.site_search(m)
    if got:
        w['url'], w['title'] = page.url, page.title
        _step(w, f"searched {_pow.host_of(page.url)} for the CA", 'search', m[:12] + '…')
    return got


async def _pow_advance(w, pw, page, wait_human=None):
    """⛏ Open the coin's next research page (a walled one is skipped — a PoW never waits for a person). → what the window now reads."""
    from cat_browser import needs_human
    while True:
        nxt = _pow.next_link(pw)
        if not nxt:
            w['powDone'] = True
            return '(ALL SITES DONE — answer now with action "answer", say = "BUY|WATCH|AVOID — why", from the vitals you pulled.)\n' + str(_pow.public(pw)['pulls'])
        _pow.step(pw, nxt)
        w['url'] = nxt
        _step(w, f'opening {_pow.host_of(nxt)}', 'open', nxt)   # said BEFORE the page loads: the window shows its browser at once, even when a wall comes next
        try:
            got = await page.goto(nxt)
        except Exception as e:   # noqa: BLE001 — a page that won't load is skipped like a wall
            got = f'(could not open: {str(e)[:80]})'
        w['url'], w['title'] = page.url or nxt, page.title
        challenge = needs_human(page.url, got)
        if challenge and wait_human:
            w['human'] = {'why': challenge, 'url': _pow.source_url(page.url or nxt), 'kind': 'challenge', 'seconds': 45}
            w['status'], w['bubble'] = 'human', f'✋ {challenge} · 45 s to continue'
            resumed = await wait_human(w['i'])
            w['human'], w['status'] = None, 'working'
            if resumed and not w.get('redirect'):
                got = await _after_human(w, page)
                challenge = needs_human(page.url, got)
        if challenge or str(got).startswith('(could not open'):
            w.pop('redirect', None)  # A timed-out manual challenge cannot redirect a later site.
            _pow.wall(pw, nxt)   # never counted, never opened again
            _step(w, f'{_pow.host_of(nxt)} is walled — skipped', 'refused', nxt)
            continue
        got = await _pow_find(w, pw, page) or got
        w['_page'] = str(got)
        await _pow_snap(pw, page, got)
        return f'NOW ON {_pow.host_of(nxt)} — save every visible vital in one verified snapshot, then it moves on.\n' + str(got)


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
            for w, job in zip(ws, task.get('jobs') or split_jobs(task['text'], len(ws))):
                w['goal'] = job
                if not job:
                    w.update(status='done', bubble='not asked — idle')
            on = [w for w in ws if w['goal']]
            task['status'] = 'working'
            got = await asyncio.gather(*(_window(task, w, ask, pages[w['i']], wait_human, names[w['i']], feeless) for w in on), return_exceptions=True)
            _failed(on, got)
            if any(isinstance(g, Stopped) for g in got) and not any(isinstance(g, str) for g in got):
                raise next(g for g in got if isinstance(g, Stopped))
            task['answer'] = '\n\n'.join(f"{names[w['i']]} · {job_label(w['goal'])}\n{w['answer'] or '(nothing)'}" for w in on)[:8000]
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
        task.update(status='parked' if str(e).startswith(PARKED) else 'stopped', why=str(e) or 'stopped by you')
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
        w.pop('pw', None); w.pop('_page', None)
    return task
