"""💬 DIRECT LM CHAT + OWNER-APPROVED AGENT UPDATES (pure, tested `tests/test_ai_chat.py`; owner's spec, 2026-10-13).

Three modes: CHAT (normal language — never the case schema) · CASE REVIEW (the structured coin read, the router's CASE mode) ·
AGENT IMPROVEMENT (the model may PROPOSE changes; it can apply nothing). A proposal is a validated record:

    LM SUGGESTION → {agent, kind, key, old, new, reason, effect, rollback} → OWNER REVIEW → [APPROVE] [REJECT]

Only `decide(.., approve=True)` hands a proposal to the service's `apply` step, and only for the kinds in `SAFE`:
  cfg     one of a few advisory switches (`SAFE_CFG`) — the same values the owner's own control row offers
  lesson  a note / narrative the model reads with every fitting case (teach.py)
  weight  a ranking weight on one cause from the coach's fixed vocabulary (coach.py)
  tune    ONE Reaper setting, ONE notch → a SHADOW test only (office.model_candidate) — never live by approval alone
  idea    a suggestion with no setting behind it (which vitals to collect, which provider for which task): approved = filed, applies nothing
Everything about execution is out of reach: any key matching `PROTECTED` (slippage, price gap, sell-back, pool floor, wallet, limits, keeper,
signing, funding, sizes, stops, seats …) is refused at parse time AND again at approval. The chat history is short and in memory; the
stored proposal record is compact (no raw prompt, no raw response) and capped."""
import json
import re

MODES = ('chat', 'case', 'improve', 'build')
HIST_TURNS = 8          # the last N exchanges go back to the model (and stay on screen)
MSG_LEN = 1400
PROPOSALS_KEEP = 60
PROPOSALS_PER_REPLY = 4
AGENTS = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge', 'desk')
SAFE_CFG = {'agentAiGate': (True, False), 'agentAiLearn': (True, False), 'chartWait': (True, False), 'agentCapital': (True, False), 'agentDial': ('chill', 'normal', 'crazy')}
TUNE_KEYS = ('giveBackPct', 'protectAt', 'stopPct')
KINDS = ('cfg', 'lesson', 'weight', 'tune', 'idea')
PROTECTED = re.compile(r'slip|gap|sell.?back|pool|liq|wallet|keeper|courier.?(health|block)|sign|fund|top.?up|withdraw|deposit|limit|max.?swap|daily|impact|'
                       r'size|seat|armed|paused|halt|rpc|api.?key|secret|private|order|route|quote|agent(tp|sl|trail|maxhold|control|paper|open|curve|authority|entry|switch|mc|back|feed|learnpct|seats|take|mode)', re.I)

IMPROVE_ASK = (
    "AGENT IMPROVEMENT mode. Read CONTEXT (the desk's current truth) and the owner's message, then answer with ONE JSON object and nothing else:\n"
    '{"reply": "your answer in normal language, 2-6 sentences", "proposals": [{"agent": "tally|sherlock|weather|trigger|devil|warden|courier|reaper|archivist|judge|desk", '
    '"kind": "cfg|lesson|weight|tune|idea", "key": "...", "value": "...", "reason": "the evidence in CONTEXT, with numbers", "effect": "what should change"}]}\n'
    "You only PROPOSE: nothing is applied until the owner approves each one. At most 4 proposals; none is fine. Allowed:\n"
    f"- cfg: key one of {', '.join(SAFE_CFG)}; value true|false (agentDial: chill|normal|crazy)\n"
    "- lesson: key note|narrative; value = the lesson text the model should read with every fitting case (narrative: \"keywords: text\")\n"
    "- weight: key = one cause from CONTEXT.vocab exactly; value = why it should rank a matching coin down\n"
    f"- tune: key one of {', '.join(TUNE_KEYS)}; value up|down (one notch, into a shadow test)\n"
    "- idea: anything else (a vital to collect, which provider for which task, a prompt change) — key = a short title, value = the idea\n"
    "Never propose anything about execution: slippage, price gap, sell-back, pool floor, wallet or limits, sizes, seats, stops, orders, keys.")

# 💬 CHAT: the desk voice (the 7B local model answered "improve decision accuracy · monitor and adjust" to "why don't we capitalize faster?")
CHAT_ASK = (
    "CHAT mode — you are the desk's sharpest trencher talking to the owner. Rules: (1) verdict in the FIRST sentence; (2) every claim carries a number, "
    "an agent name or a coin taken from CONTEXT (money / capital / trail / outcomes / seats / agents) — if it is not in CONTEXT you do not say it; "
    "(3) max 5 short lines, no headings, no numbered plans, no bold; (4) name the ONE thing costing the most money and the ONE lever that moves it; "
    "(5) money first: the capital / record / trail lines outrank any single coin; recent outcomes are trades that already CLOSED, seats are what is held now; "
    "(6) you cannot change anything from chat: when the owner asks you to fix / change / tune something, say which lever you would pull in one line and "
    "tell them to tap 🛠 Fix agents so it becomes a proposal they approve. (7) voice = FEE: a blunt degen operator, swearing is fine when it is natural, "
    "challenge a bad assumption instead of agreeing, mark what is FACT (in CONTEXT) vs INFERENCE vs UNKNOWN. Trench words are fine; filler is not.")
# 🧱 BUILD: the models help keep the product strong — ideas only, filed for the owner / the engineer, nothing applied
BUILD_ASK = (
    "BUILD mode. You help the owner and their engineer keep FEELESS strong: code, UI and vitals. Read CONTEXT and the owner's message, then answer with ONE JSON "
    'object and nothing else: {"reply": "2-5 blunt sentences", "proposals": [{"agent": "desk", "kind": "idea", "key": "short title", "value": "what to build: the '
    'surface or agent it lives on, the exact data it reads, how it is drawn or computed", "reason": "the evidence in CONTEXT, with numbers", "effect": "what the owner '
    'sees or what gets measured"}]}\n'
    "At most 3 proposals, each buildable in a day and specific (a vital that is UNKNOWN / PENDING in CONTEXT to collect, a live meter, a check an agent lacks, a "
    "test that would have caught a loss). Only kind idea: an idea changes no setting. Never anything about execution, the wallet, limits, sizes, stops or keys.")
FIX_WORDS = re.compile(r"\b(fix|change|tune|tweak|adjust|improve|make (it|them)|turn (on|off)|switch (on|off)|teach)\b", re.I)


def route_mode(mode, text):
    """A chat message that ASKS FOR A CHANGE runs as 🛠 agent improvement (proposals the owner approves) — the model can change nothing from chat,
    so "can you fix?" used to get a paragraph of advice. Everything else keeps its mode."""
    return 'improve' if mode == 'chat' and FIX_WORDS.search(str(text or '')) and len(str(text or '')) <= 400 else mode


# 🌐 BACK IT WITH A SEARCH (owner, 2026-10-15: "they need true convos like you and GPT about anything and always a quick web search to back it"):
# a 💬 chat question about the world (not a FEELESS record question, not a greeting) gets 5 web results first; the model answers from them
# and names its sources. FEELESS's own numbers still come only from CONTEXT / the evidence packet.
GREETING = re.compile(r'^\s*(yo+|yurr+|gm|gn|hey+|hi+|hello|sup|wassup|what\'?s up|thanks?|thank you|ty|ok(ay)?|lol|lmao|bet|cool|nice)\b[\s!.?]*$', re.I)
WEB_WORDS = re.compile(r'\?|\b(who|what|when|where|why|how|which|news|latest|today|price|search|look ?up|google|find|explain|meaning|is it|are they|did|does|vs\.?)\b', re.I)
WEB_RULE = ("WEB = fresh search results for the owner's question (title · url · snippet). Use them for anything about the outside world and cite the "
            "url you used in brackets. If they do not answer it, say so — never invent a source. FEELESS numbers come only from CONTEXT, never the web.")


def wants_web(text):
    t = str(text or '').strip()
    return len(t) >= 6 and not GREETING.match(t) and bool(WEB_WORDS.search(t))


def web_query(text):
    """The search words: the question without filler, ≤ 120 characters."""
    t = re.sub(r'\s+', ' ', str(text or '')).strip()
    t = re.sub(r'^((hey|yo|fee|vega|kai|bro|can you|could you|please|pls)[,\s]+)+', '', t, flags=re.I)
    return t[:120]


def system_for(mode):
    return {'chat': CHAT_ASK, 'improve': IMPROVE_ASK, 'build': BUILD_ASK}.get(mode)


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def clean(text, n=MSG_LEN):
    return re.sub(r'[\x00-\x08\x0b-\x1f\x7f]+', ' ', str(text or '')).strip()[:n]


# ── the conversation (short, bounded, in memory) ─────────────────────────────────────────────────────────────────────────
def push(history, role, text, meta=None):
    """Append one turn; only the newest HIST_TURNS exchanges are kept (each turn bounded)."""
    h = list(history or []) + [{'role': 'user' if role == 'user' else 'assistant', 'text': clean(text), **({'meta': meta} if meta else {})}]
    return h[-HIST_TURNS * 2:]


def as_messages(history):
    """The history as chat messages for the model (text only — never the meta)."""
    return [{'role': t['role'], 'content': t['text']} for t in history or [] if t.get('text')]


# ── the compact agent truth the model is shown ───────────────────────────────────────────────────────────────────────────
def _u(v, unit=''):
    return 'UNKNOWN' if v in (None, '') else f'{v}{unit}'


def context(office, focus=None, vocab=()):
    """The desk's CURRENT truth, compact (≈ 1–1.5K tokens): the ten agents (generation · status · record), the newest decisions, seats,
    the selected coin, execution health, recent real outcomes, the money record. A vital nobody has read is the WORD UNKNOWN / PENDING —
    never a zero, never left out."""
    o = office or {}
    gens = {g.get('role'): g for g in o.get('generations') or [] if isinstance(g, dict)}
    stats = o.get('deskStats') or {}
    def _rec(r):   # 🗳 a desk's OWN vote record when it has one (judge_review.desk_votes), else the team record it shares
        st, own = stats.get(r) or {}, (stats.get(r) or {}).get('own') or {}
        if own.get('n'):
            g, b = own.get('go') or {}, own.get('doubt') or {}
            return (f"own vote right {_u(own.get('rightPct'), '%')} of {own['n']} real trades · GO {g.get('n', 0)}× typical {_u(g.get('med'), '%')} · "
                    f"DOUBT {b.get('n', 0)}× typical {_u(b.get('med'), '%')} · lone dissent {own.get('lone', 0)}× ({own.get('loneRight', 0)} right)")
        if st.get('kind') == 'landed':
            return f"{_u(st.get('accuracy'), '%')} of {int(_f(st.get('decisions')))} sends landed (last hour)"
        if st.get('kind') == 'intact':
            return f"{int(_f(st.get('decisions')))} records filed, chain {'intact' if st.get('accuracy') == 100 else 'REWRITTEN' if st.get('accuracy') == 0 else 'UNKNOWN'}"
        return f"team record only: {int(_f(st.get('decisions')))} real decisions, {_u(st.get('accuracy'), '%')} right"
    agents = [f"{r}: gen {_u((gens.get(r) or {}).get('generation'))} {_u((gens.get(r) or {}).get('status'))} · {_rec(r)}" for r in AGENTS[:-1]]
    cands = ((o.get('kernel') or {}).get('candidates') or [])
    dec = [f"{c.get('symbol')} {c.get('status')} · trigger {_u(c.get('trigger'))} · {str(c.get('why') or '')[:70]}" for c in cands[:6]]
    pos = [f"{p.get('symbol')} {_u(p.get('pct'), '%')} · {str(p.get('decision') or p.get('state') or '')[:40]}" for p in (o.get('positions') or [])[:4]]
    seat = o.get('seat') or {}
    ex = o.get('execution') or {}
    cap, tr, ms = o.get('capital') or {}, o.get('trail') or {}, o.get('mission') or {}
    sel = next((c for c in cands if focus and focus in (c.get('mint'), c.get('pair'), c.get('symbol'))), None)
    out = {'agents': agents, 'decisions': dec or ['none this pass'], 'positions': pos or ['no seat held'],
           'seats': f"{_u(seat.get('held'))} held · {_u(seat.get('empty'))} empty · {str(seat.get('state') or 'UNKNOWN')}",
           'execution': f"{_u(ex.get('health'))} · {int(_f(ex.get('fills')))} of {int(_f(ex.get('sends')))} sends landed · {int(_f(ex.get('failed')))} failed",
           'card': f"worth ${_f(ms.get('value')):.2f}, ${_f(ms.get('putIn')):.2f} put in" if ms.get('value') is not None else 'UNKNOWN',
           'money': f"{_u(cap.get('state'))}: {str(cap.get('why') or '')[:200]}", 'trail': str(tr.get('words') or 'UNKNOWN')[:200],
           'outcomes': [f"{r.get('sym')} {_f((r.get('result') or {}).get('pct')):+.1f}% · {str((r.get('result') or {}).get('rule') or '')[:40]}" for r in ((o.get('tradeTape') or {}).get('rows') or [])[:6]
                        if (r.get('result') or {}).get('pct') is not None] or ['none on file'],
           'vocab': list(vocab)[:10]}
    if sel:
        out['selected'] = {'symbol': sel.get('symbol'), 'status': sel.get('status'), 'cap': _u(sel.get('cap')), 'liq': _u(sel.get('liq')), 'vol5m': _u(sel.get('vol5m')),
                           'move5m': _u(sel.get('move5m'), '%'), 'buyShare': _u(sel.get('buyShare'), '%'), 'ageMin': _u(sel.get('ageMin')),
                           'pending': list(sel.get('unknown') or []) or 'nothing pending', 'devil': [str(d[2] if len(d) > 2 else d)[:70] for d in (sel.get('devil') or [])[:3]] or 'no objection'}
    elif focus:
        out['selected'] = f'{focus}: not on the desk right now (UNKNOWN)'
    return out


def ctx_key(ctx):
    """A key that changes only when the compact context does (the service keeps one built context per key)."""
    return str(hash(json.dumps(ctx, sort_keys=True, default=str)))


# ── proposals: validated, never applied here ─────────────────────────────────────────────────────────────────────────────
def _first_json(text):
    t = re.sub(r'```(?:json)?', '', str(text or ''))
    i = t.find('{')
    while i >= 0:
        depth = 0
        for j in range(i, len(t)):
            depth += t[j] == '{'
            depth -= t[j] == '}'
            if depth == 0:
                try:
                    return json.loads(t[i:j + 1])
                except ValueError:
                    break
        i = t.find('{', i + 1)
    return None


def protected(key, value=''):
    """True = this touches execution / money and is out of reach of the chat, whatever the model or anyone typing into it says."""
    return bool(PROTECTED.search(str(key or ''))) or (isinstance(value, str) and bool(re.search(r'slippage|wallet limit|max swap|private key|seed phrase', value, re.I)))


def check(p, vocab=()):
    """One raw proposal → the validated one {agent, kind, key, value, reason, effect}, or (None, why it was refused)."""
    if not isinstance(p, dict):
        return None, 'not an object'
    kind, key = str(p.get('kind') or '').strip().lower(), clean(p.get('key'), 60)
    agent = str(p.get('agent') or 'desk').strip().lower()
    agent = agent if agent in AGENTS else 'desk'
    val = p.get('value')
    if kind not in KINDS:
        return None, f'unknown kind {kind[:20]!r}'
    if kind != 'lesson' and kind != 'idea' and protected(key):
        return None, f'{key}: execution / money settings cannot be changed from the chat'
    if kind == 'cfg':
        if key not in SAFE_CFG:
            return None, f'{key}: not one of the advisory switches the chat may propose'
        v = {'true': True, 'on': True, 'false': False, 'off': False}.get(str(val).strip().lower(), val) if SAFE_CFG[key] == (True, False) else str(val).strip().lower()
        if v not in SAFE_CFG[key]:
            return None, f'{key}: {val!r} is not one of its options'
        val = v
    elif kind == 'lesson':
        if key not in ('note', 'narrative') or len(clean(val)) < 8:
            return None, 'a lesson needs key note|narrative and a few words'
        val = clean(val, 400)
    elif kind == 'weight':
        if key not in set(vocab or ()):
            return None, f'{key}: not a cause in the desk\'s vocabulary'
        val = clean(val, 120)
    elif kind == 'tune':
        if key not in TUNE_KEYS or str(val).strip().lower() not in ('up', 'down'):
            return None, 'a tune is one of giveBackPct | protectAt | stopPct, up | down'
        val = str(val).strip().lower()
    else:
        if protected(key, clean(val, 300)) and re.search(r'\b(set|change|raise|lower|increase|remove|disable|turn off)\b', clean(val, 300), re.I):
            return None, 'an idea that changes execution / money settings is not filed'
        key, val = key or 'idea', clean(val, 300)
    return {'agent': agent, 'kind': kind, 'key': key, 'value': val, 'reason': clean(p.get('reason'), 240), 'effect': clean(p.get('effect'), 200)}, None


def salvage(text):
    """A JSON answer the model CUT OFF mid-way (its token cap) never reaches the chat as raw `{"reply": …`: its "reply" / "summary" text
    is pulled out, else the prose before the first brace. (Found 2026-10-13: a cut answer was shown AND queued to build as raw JSON.)"""
    t = str(text or '')
    m = re.search(r'"(?:reply|summary)"\s*:\s*"((?:[^"\\]|\\.)*)', t)
    if m:
        try:
            return clean(json.loads('"' + m.group(1).rstrip('\\') + '"'))
        except Exception:
            return clean(m.group(1).replace('\\"', '"'))
    i = t.find('{')
    return clean(t if i < 0 else t[:i] or t)


def parse_improve(text, vocab=(), only=None):
    """The model's AGENT IMPROVEMENT answer → (reply in normal language, [validated proposals], [refusals]). Prose with no JSON is just a reply."""
    j = _first_json(text)
    if not isinstance(j, dict):
        return salvage(text), [], []
    ok, bad = [], []
    for p in (j.get('proposals') or [])[:8] if isinstance(j.get('proposals'), list) else []:
        if only and isinstance(p, dict) and p.get('kind') not in only:
            bad.append(f"{p.get('kind')}: only {' / '.join(only)} in this mode"); continue
        v, why = check(p, vocab)
        (ok if v else bad).append(v or why)
    return clean(j.get('reply') or j.get('summary') or ''), ok[:PROPOSALS_PER_REPLY], bad[:6]


OLD_WORD = {'lesson': 'no such lesson', 'weight': 'no rule for this cause', 'idea': 'nothing — an idea changes no setting'}
ROLLBACK = {'cfg': 'flip the same switch back in ⚙ operator controls (or approve the opposite proposal) — old value kept on this record',
            'lesson': 'remove it in 🎓 Teach the desk (✕ on the lesson)', 'weight': 'kill the rule in 👑 Coach (✕) — it also expires by itself in 24h',
            'tune': 'nothing to roll back: it only enters a 20-exit shadow test; a test that does not beat the live rule is rejected by itself',
            'idea': 'nothing to roll back: filing an idea changes no setting'}


def propose(state, items, olds, now, source=None):
    """Validated proposals → PENDING records {id, agent, kind, key, old, new, reason, effect, rollback, status}. Nothing is applied.
    `olds` = {(kind, key): the current value / behaviour} read by the service."""
    ps = list((state or {}).get('items') or [])
    new = []
    for i, p in enumerate(items or []):
        if any(x['status'] == 'pending' and (x['kind'], x['key'], x['new']) == (p['kind'], p['key'], p['value']) for x in ps):
            continue   # the same suggestion is already waiting for the owner
        rec = {'id': f"p{int(now * 1000)}{i}", 'at': round(now, 1), 'agent': p['agent'], 'kind': p['kind'], 'key': p['key'], 'old': (olds or {}).get((p['kind'], p['key']), OLD_WORD.get(p['kind'], 'UNKNOWN')),
               'new': p['value'], 'reason': p['reason'], 'effect': p['effect'], 'rollback': ROLLBACK[p['kind']], 'status': 'pending', 'source': source}
        new.append(rec)
    return {'items': (new + ps)[:PROPOSALS_KEEP]}, new


def decide(state, pid, approve, now):
    """The owner's APPROVE / REJECT → (state, the proposal to apply | None, error | None). A proposal is decided ONCE; a rejected one is
    never handed back; one whose key is protected is refused even now (defence in depth)."""
    ps = [dict(x) for x in (state or {}).get('items') or []]
    p = next((x for x in ps if x.get('id') == pid), None)
    if not p:
        return state, None, 'no such proposal'
    if p['status'] != 'pending':
        return state, None, f"already {p['status']}"
    if approve and p['kind'] not in ('lesson', 'idea') and protected(p['key']):
        p.update(status='rejected', decidedAt=round(now, 1), note='refused: execution / money setting')
        return {'items': ps}, None, 'execution / money settings cannot be changed from the chat'
    p.update(status='approved' if approve else 'rejected', decidedAt=round(now, 1))
    return {'items': ps}, (dict(p) if approve else None), None


def applied(state, pid, note):
    """What the service's apply step did with an approved proposal (kept on the record: the audit line)."""
    ps = [dict(x) for x in (state or {}).get('items') or []]
    for x in ps:
        if x.get('id') == pid:
            x['applied'] = clean(note, 200)
    return {'items': ps}


# 🧵 ONE THREAD PER MODE (owner: "each chat convo is different"): chat · case · fix · build keep their own short history
THREAD_TURNS = 6


def threads_view(threads):
    return {m: list((threads or {}).get(m) or []) for m in MODES}


def push_thread(threads, mode, role, text, meta=None):
    t = dict(threads or {})
    t[mode] = push(t.get(mode) or [], role, text, meta)[-THREAD_TURNS * 2:]
    return t


# 📋 THE BUILD QUEUE (owner: "do me approving actually build?"): an approved build idea — or any model line the owner taps 🧱 Build this on — is
# QUEUED for the engineer (the next Claude Code session reads data/build_queue.json first). The model never writes code in the app; approval = permission.
BUILD_KEEP = 40
BUILD_STATUS = ('queued', 'building', 'shipped', 'dropped')


def build_add(state, title, text, src, now):
    st = dict(state or {}); items = list(st.get('items') or [])
    title_, text_ = clean(title, 80) or clean(text, 80), clean(text, 600)
    if len(text_) < 8:
        raise ValueError('Nothing to build.')
    if any(x['text'] == text_ and x['status'] in ('queued', 'building') for x in items):
        raise ValueError('Already in the build queue.')
    n = int(st.get('n') or 0) + 1
    item = {'id': f'b{n}', 'title': title_, 'text': text_, 'src': clean(src, 40) or 'owner', 'status': 'queued', 'at': round(now, 1)}
    st.update(n=n, items=([item] + items)[:BUILD_KEEP])
    return st, item


def build_set(state, bid, status, now):
    if status not in BUILD_STATUS:
        raise ValueError('Unknown status.')
    st = dict(state or {}); items = [dict(x) for x in st.get('items') or []]
    hit = next((x for x in items if x['id'] == bid), None)
    if not hit:
        raise ValueError('No such build item.')
    hit.update(status=status, doneAt=round(now, 1))
    st['items'] = items
    return st


def build_view(state, n=12):
    items = list((state or {}).get('items') or [])
    live = [x for x in items if x['status'] in ('queued', 'building')]
    return {'open': len(live), 'items': (live + [x for x in items if x['status'] not in ('queued', 'building')])[:n]}


# ⚙ the owner's Brain settings: chat tuning + the SMALL-THINGS allowance (lessons and build ideas apply without a tap; switches, weights and
# exit notches still wait for ✅ — and execution / limits / the wallet are never reachable at all)
TEMPS = (0.1, 0.3, 0.6, 0.9)
LENS = {'short': 250, 'normal': 600, 'long': 1200}
SMALL_KINDS = ('lesson', 'idea')
SETTINGS = {'temp': 0.3, 'len': 'normal', 'allowSmall': False, 'localBoostUntil': 0.0}


def clean_settings(d, old=None):
    out = {**SETTINGS, **(old or {})}
    d = d or {}
    if d.get('temp') is not None and _f(d.get('temp'), -1) in TEMPS:
        out['temp'] = _f(d['temp'])
    if d.get('len') in LENS:
        out['len'] = d['len']
    if isinstance(d.get('allowSmall'), bool):
        out['allowSmall'] = d['allowSmall']
    if d.get('localBoostUntil') is not None and d.get('localBoost') is None:   # the saved state (a restart keeps the boost running)
        out['localBoostUntil'] = max(0.0, _f(d['localBoostUntil']))
    if isinstance(d.get('localBoost'), bool) and d.get('now') is not None:   # 💻 24h boost: switching it on (again) starts a fresh 24h
        out['localBoostUntil'] = round(_f(d['now']) + BOOST_SEC, 1) if d['localBoost'] else 0.0
    return out


# 💻 LOCAL BOOST (owner, 2026-10-13: "local be beefed over 24hrs maxed, watch"): for 24h the local model's own lane reads a case every
# BOOST_EVERY s instead of every 180s. It backs off by itself — to the normal 180s — whenever a browser on the site reports lag (avg fps
# under LAG_FPS or > LAG_MS blocked per report in the last 2 min: the local model shares the GPU Chrome draws with), and it never runs
# more than half the time (the next read waits at least as long as the last one took). Every hour is logged for the watch.
BOOST_SEC, BOOST_EVERY, NORMAL_EVERY, LAG_FPS, LAG_MS = 86400.0, 45.0, 180.0, 30, 400


SHARED_LAG_EVERY = 900.0   # a local model on THIS Mac while a browser lags: one background read per 15 min at most


def lane_every(settings, now, perf_rows, last_ms=None, base=NORMAL_EVERY, shared_gpu=False):
    """→ (seconds until the next local read, why). `perf_rows` = the lag catcher's reports from the last 2 min. `shared_gpu` = LM Studio
    runs on this Mac (the GPU Chrome draws with): any lag report pauses the background reads — the owner's own chat is never paused."""
    st = settings or {}
    boost = _f(st.get('localBoostUntil')) > now
    lag = [r for r in perf_rows or [] if (r.get('fps') and _f(r['fps']) < LAG_FPS) or _f(r.get('longMs')) > LAG_MS]
    if shared_gpu and lag:
        return max(SHARED_LAG_EVERY, 2 * _f(last_ms) / 1000.0), f'paused — the model shares this Mac\'s GPU and {len(lag)} browser report{"s" if len(lag) != 1 else ""} of lag in 2 min'
    if boost and lag:
        e, why = base, f'boost paused — {len(lag)} browser report{"s" if len(lag) != 1 else ""} of lag in 2 min'
    elif boost:
        e, why = BOOST_EVERY, 'boost on'
    else:
        e, why = base, 'normal'
    return max(e, 2 * _f(last_ms) / 1000.0), why


def watch_note(watch, now, ok, ms=None, why=None):
    """The 24h watch: {hourStart: {n, ok, fail, msSum, paused}} — one row an hour, the last 24 kept."""
    h = str(int(now // 3600 * 3600))
    w = dict(watch or {})
    r = dict(w.get(h) or {'n': 0, 'ok': 0, 'fail': 0, 'msSum': 0.0, 'paused': 0})
    if why == 'paused':
        r['paused'] += 1
    else:
        r['n'] += 1; r['ok' if ok else 'fail'] += 1; r['msSum'] += _f(ms)
    w[h] = r
    return dict(sorted(w.items())[-24:])


def watch_view(watch, settings, now, every=None, why=None):
    w = watch or {}
    rows = [{'hour': int(k), 'n': v['n'], 'ok': v['ok'], 'fail': v['fail'], 'avgSec': round(v['msSum'] / v['ok'] / 1000, 1) if v['ok'] else None, 'paused': v['paused']} for k, v in sorted(w.items())]
    until = _f((settings or {}).get('localBoostUntil'))
    return {'boost': until > now, 'leftH': round(max(0.0, until - now) / 3600, 1), 'every': every, 'why': why, 'hours': rows,
            'reads24h': sum(r['ok'] for r in rows), 'fails24h': sum(r['fail'] for r in rows), 'paused24h': sum(r['paused'] for r in rows)}


def tune_of(st):
    st = clean_settings(st)
    return {'temp': st['temp'], 'maxTok': LENS[st['len']]}


# 🗂 SAVED CONVERSATIONS: "＋ New" files the current thread (≤ 20 kept, text only), "🗂" reopens one
SAVED_KEEP = 20


def save_convo(saved, mode, thread, now):
    th = [t for t in thread or [] if t.get('text')]
    if not th:
        return list(saved or [])
    first = next((t['text'] for t in th if t['role'] == 'user'), th[0]['text'])
    item = {'id': f"c{int(now * 1000)}", 'mode': mode, 'title': clean(first, 60), 'at': round(now, 1), 'msgs': th[-THREAD_TURNS * 2:]}
    return ([item] + list(saved or []))[:SAVED_KEEP]


def saved_view(saved):
    return [{k: x[k] for k in ('id', 'mode', 'title', 'at')} | {'n': len(x.get('msgs') or [])} for x in saved or []]


def view(state, n=12):
    ps = list((state or {}).get('items') or [])
    return {'pending': [x for x in ps if x['status'] == 'pending'][:n], 'decided': [x for x in ps if x['status'] != 'pending'][:n]}


# ── 📜 ACTIVITY: everything the models did, one timeline ──────────────────────────────────────────────────────────────────────
ACT_ROLE = {'sherlock': '🔍', 'devil': '😈', 'judge': '👨‍⚖️', 'owner': '👤', 'manager': '⚖', 'coach': '👑', 'lab': '🧪', 'exit': '☠'}


def activity(log=None, props=None, play=None, lane=None, n=60):
    """The Brain's 📜 Activity pane (owner, 2026-10-14: "show log for all activity"): every model READ (role, coin, stance, which model,
    how long), every PROPOSAL (made / approved / rejected / applied), every PLAYGROUND creation, newest first. Display only — built from
    records the service already keeps; nothing here is read back by an agent. → [{at, kind, icon, who, title, sub, tone, mint}]"""
    out = []
    for r in log or []:
        st = r.get('stance')
        out.append({'at': r.get('at'), 'kind': 'read', 'icon': ACT_ROLE.get(r.get('role'), '🧠'), 'who': r.get('label') or r.get('source'),
                    'title': f"{(r.get('role') or 'model').upper()} read ${r.get('symbol') or '?'}" + (f" → {st}" if st else ' → no answer'),
                    'sub': str(r.get('summary') or r.get('why') or '')[:140], 'tone': 'bad' if st == 'CAUTION' else 'ok' if st == 'FAVOR' else 'mute',
                    'mint': r.get('mint'), 'ms': r.get('ms')})
    for p in ((props or {}).get('items') or []):
        out.append({'at': p.get('at'), 'kind': 'proposal', 'icon': '🛠', 'who': p.get('source'), 'title': f"proposed: {p.get('agent')} · {p.get('kind')} {p.get('key')}",
                    'sub': str(p.get('reason') or '')[:140], 'tone': 'gold'})
        if p.get('decidedAt'):
            ok = p.get('status') == 'approved'
            out.append({'at': p.get('decidedAt'), 'kind': 'decision', 'icon': '✅' if ok else '✕', 'who': 'you', 'title': f"{'approved' if ok else 'rejected'}: {p.get('kind')} {p.get('key')}",
                        'sub': str(p.get('applied') or '')[:140], 'tone': 'ok' if ok else 'mute'})
    for x in play or []:
        out.append({'at': x.get('at'), 'kind': 'play', 'icon': '🧩', 'who': x.get('by'), 'title': f"code: {str(x.get('title') or x.get('prompt') or '')[:70]}",
                    'sub': f"{x.get('file') or 'Code lab'} · {x.get('status') or 'proposed'}", 'tone': 'ok' if x.get('status') == 'approved' else 'ice'})
    if (lane or {}).get('last'):
        l = lane['last']
        out.append({'at': l.get('at'), 'kind': 'lane', 'icon': '🖥', 'who': l.get('via'), 'title': f"background read ${l.get('symbol')} → {l.get('stance') or '—'}",
                    'sub': f"{lane.get('n', 0)} background reads so far", 'tone': 'ice'})
    return sorted([x for x in out if x.get('at')], key=lambda x: -float(x['at']))[:n]
