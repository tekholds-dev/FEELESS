"""🧵 Slice 35 · the task chat runner: split → saved → worked live (checklist · thoughts · logs · cost per step) → recap back in the chat it came
from and on the proof's record. Text work only (task_chats.NO_MONEY): no step can trade, bid, send, post or sign.

The live task list of each agent is held HERE (in memory) and merged into every store save (fc_core._save → merge), the way a clip run's progress
is: an older store copy saved by the engine can never undo a step, a pause or a new task. The engine pass (taskchat_pass) does what only the
store's one writer may: bill each step's cost to the agent's credit, post the recap into its chat, add the row to the proof's record, start the
next queued task, and pick up a task a restart cut off."""
import copy

import task_chats as _tc

_STATE: dict = {}    # cat id → [task]  (the truth while the service runs)
_RUN: dict = {}      # task id → asyncio.Task
_CTL: dict = {}      # task id → 'pause' | 'stop'
_POST: list = []     # finished tasks waiting for the pass to post their recap
_SPLITS: list = []   # tasks a mind split off in its answer: their card line joins the chat right after that answer
STEP_S = 150         # one model call's ceiling
PLAN_TOK, STEP_TOK, RECAP_TOK = 500, 900, 220


def _rs():
    import feecat_service
    return feecat_service


def tasks_of(cat_id, cat=None):
    """The agent's task chats (loaded once from the store, then held in memory)."""
    if cat_id not in _STATE:
        _STATE[cat_id] = copy.deepcopy(list((cat or {}).get('taskChats') or []))
        for t in _STATE[cat_id]:   # 🛟 a restart cut it off mid-step: it goes back in the queue and picks up from the first step not done
            if t.get('state') in ('starting', 'working'):
                t['state'] = 'queued'
                for s in t.get('steps') or []:
                    if s.get('state') == 'doing':
                        s['state'] = 'pending'
                _tc.log(t, 'The service restarted: it picks up from the first step not done.')
            elif t.get('state') in _tc.ENDED and not t.get('posted') and (cat_id, t.get('id')) not in _POST:
                _POST.append((cat_id, t['id']))   # 🛟 it ended just before a restart: its recap still reaches the chat and the record
    return _STATE[cat_id]


def find(cat_id, cat, tid):
    return next((t for t in tasks_of(cat_id, cat) if t.get('id') == tid), None)


def merge(store):
    """🔒 Every save: the in-memory task chats win over an older copy's."""
    for cid, rows in _STATE.items():
        c = (store.get('cats') or {}).get(cid)
        if c is not None:
            c['taskChats'] = copy.deepcopy(_tc.trim(rows))


def _minds(cat, scope):
    rs = _rs(); b = cat.get('brainsCfg') or {}
    k = scope.get('kind')
    pair = rs._lc.minds_for(b, k) if k and k != 'desk' else None
    return list(pair or b.get('brains') or [])


def _context(cat, scope):
    """What the task chat may READ: the proof folder it came from (trimmed), or the desk's last lines. Never keys, wallets or secrets."""
    k, ref = scope.get('kind'), scope.get('ref')
    if k in _tc.FOLDER_KEYS:
        rows = [f for f in cat.get(_tc.FOLDER_KEYS[k]) or [] if isinstance(f, dict)]
        f = next((x for x in rows if str(x.get('id')) == ref), None) if ref else (rows[-1] if rows else None)
        if not f:
            return f'(no {k} folder found)'
        keep = {kk: f.get(kk) for kk in ('id', 'n', 'topic', 'sym', 'name', 'title', 'stage', 'status', 'phase', 'side', 'market', 'why', 'verdict', 'listing', 'calls', 'talk', 'review', 'brief', 'goal')
                if f.get(kk) not in (None, '', [], {})}
        return _rs().json.dumps(keep, default=str)[:2200]
    lines = [f"{m.get('by')}: {str(m.get('text') or '')[:240]}" for m in (cat.get('chat') or [])[-6:]]
    return '\n'.join(lines)[:1600]


def cap_for(cat):
    """Each task's own $ ceiling: its task cap, never past its credit (minus the reserve) or what is left of today's limit."""
    rs = _rs(); b = cat.get('brainsCfg') or {}
    cap = min(float(cat.get('taskCap') or rs.TASK_CAP_DEFAULT), rs._task_cap_max(), max(0.005, float(b.get('credit') or 0) - rs._lc.CREDIT_RESERVE))
    left = rs.day_left(cat)
    return max(0.005, min(cap, left)) if left is not None else cap


def pending(cat_id):
    """$ its task chats spent that the next pass has not billed yet (held on each task, so a restart never drops it)."""
    return round(sum(float(t.get('unbilled') or 0) for t in _STATE.get(cat_id) or []), 6)


def _ready(cat, owed=0.0):
    """'' when it may call its mind now, else why not (said on the card). `owed` = what its task chats spent that is not billed yet."""
    rs = _rs(); b = cat.get('brainsCfg') or {}
    if not b.get('brains'):
        return 'It has no mind set (Brains).'
    own = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
    if not own and not rs._lc.can_ask({**b, 'credit': float(b.get('credit') or 0) - owed}):
        return 'It is out of model credit. Top it up, then resume.'
    left = rs.day_left(cat)
    if left is not None and left - owed <= 0:
        return "It reached today's $ limit. It carries on tomorrow, or raise the limit."
    return ''


def pump(cat_id, cat):
    """Start queued task chats while its parallel setting allows (default one at a time)."""
    rows = tasks_of(cat_id, cat)
    n = _tc.can_start(rows, cat.get('taskParallel') or 1)
    for t in _tc.queue_order(rows)[:n]:
        why = _ready(cat, pending(cat_id))
        if why:
            t['why'] = why
            continue
        minds = _minds(cat, t['scope'])
        t['model'] = minds[t.get('mind', 0) % len(minds)]
        t['state'] = 'starting'; t['why'] = ''
        _tc.log(t, f"Starting on {str(t['model']).split('/')[-1]}.")
        rs = _rs()
        _RUN[t['id']] = rs.asyncio.create_task(run(cat_id, t['id']))


async def _call(cat_id, t, msgs, tok):
    """One model call through the agent's own door (rs._think: its routes, its key, its effort; logged as task:<id>). → (text, $, $ to bill)."""
    rs = _rs()
    cat = rs._load()['cats'].get(cat_id) or {}
    b = cat.get('brainsCfg') or {}; model = t['model']
    own = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
    k = t['scope'].get('kind')
    ctok = rs._CALL_CTX.set({'kind': k if k != 'desk' else 'task', 'ref': f"task:{t['id']}", 'minds': [model], 'mind': 0})
    try:
        text, usd, via = await rs.asyncio.wait_for(rs._think(cat, model, msgs, own, (b.get('efforts') or {}).get(model), tok), STEP_S)
    except Exception as e:   # noqa: BLE001 — a mind that does not answer says so on the card
        text, usd, via = '', 0.0, ''
        _tc.log(t, f'The mind did not answer ({type(e).__name__}).')
    finally:
        rs._CALL_CTX.reset(ctok)
    usd = float(usd or 0)
    bill = usd if (not own and via == 'openrouter') else 0.0   # the same rule as its chat replies: its own key / wallet pay their own bill
    return str(text or ''), usd, bill


def _owner_lines(t):
    return ' | '.join(str(m.get('text') or '') for m in (t.get('msgs') or [])[-4:])[:600]


async def _gate(t):
    """Before every call: a pause holds here (the card says paused), a stop ends it. → False when stopped."""
    rs = _rs()
    while _CTL.get(t['id']) == 'pause':
        t['state'] = 'paused'
        await rs.asyncio.sleep(1.0)
    if _CTL.get(t['id']) == 'stop':
        return False
    t['state'] = 'working'
    return True


def _spend(cat_id, t, usd, bill, step=None):
    t['cost'] = round(float(t.get('cost') or 0) + usd, 6)
    if step is not None:
        step['cost'] = round(float(step.get('cost') or 0) + usd, 6)
    if bill:
        t['unbilled'] = round(float(t.get('unbilled') or 0) + bill, 6)


def _held(cat_id, t):
    """🔒 Before each step, on the fresh store: its credit (less the reserve) and today's $ limit, counting what its task chats spent and
    the pass has not billed yet, so parallel or long task chats never run past either. → why it waits, or ''."""
    cat = _rs()._load()['cats'].get(cat_id) or {}
    return _ready(cat, pending(cat_id))


async def run(cat_id, tid):
    """Work one task chat to its end (or until it waits for its owner)."""
    rs = _rs()
    t = find(cat_id, None, tid)
    if not t:
        return
    try:
        cat = rs._load()['cats'].get(cat_id) or {}
        ctx = _context(cat, t['scope'])
        t['started'] = t.get('started') or rs.time.time()
        if not await _gate(t):   # a pause / stop pressed before it began holds here too
            return _end(cat_id, t, 'stopped', 'You stopped it.')
        if not t.get('steps'):   # 🗒 the checklist first
            t0 = rs.time.time()
            text, usd, bill = await _call(cat_id, t, _tc.plan_msgs(t, ctx, _owner_lines(t)), PLAN_TOK)
            _spend(cat_id, t, usd, bill)
            if not text.strip():
                return _end(cat_id, t, 'failed', 'Its mind did not answer the plan. Nothing else was spent.')
            th, title, steps = _tc.read_plan(text)
            _tc.thought(t, th, rs.time.time() - t0, -1)
            t['steps'] = [{'text': s, 'state': 'pending', 'cost': 0.0} for s in (steps or [t['brief'][:160]])]
            if title:
                t['title'] = title
            t['steps'][0]['cost'] = t['cost']   # the plan's cost rides the first step's line
            _tc.log(t, f"Planned {len(t['steps'])} steps.")
        for k, s in enumerate(t['steps']):
            if s.get('state') == 'done':
                continue
            if not await _gate(t):
                return _end(cat_id, t, 'stopped', 'You stopped it.')
            if float(t.get('cost') or 0) >= float(t.get('cap') or 0):
                t['state'] = 'waiting'; t['why'] = f"It reached this task's ${t['cap']:.2f} cap. Raise the cap or stop it."
                _tc.log(t, t['why']); return
            why = _held(cat_id, t)
            if why:
                t['state'] = 'waiting'; t['why'] = why
                _tc.log(t, why); return
            s['state'] = 'doing'; s['at'] = rs.time.time()
            text, usd, bill = await _call(cat_id, t, _tc.step_msgs(t, k, ctx, _owner_lines(t)), STEP_TOK)
            _spend(cat_id, t, usd, bill, s)
            if not text.strip():
                s['state'] = 'pending'
                return _end(cat_id, t, 'failed', f'Its mind did not answer step {k + 1}.')
            r = _tc.read_step(text)
            s['secs'] = round(rs.time.time() - s['at'], 1)
            _tc.thought(t, r['think'], s['secs'], k)
            for line in r['log']:
                _tc.log(t, line, step=k)
            s['did'] = r['did']; s['state'] = 'done'
            if r['ask'] and k < len(t['steps']) - 1:   # 🙋 it needs its owner: the card says so, a typed answer resumes it
                t['state'] = 'waiting'; t['why'] = r['ask']
                _tc.log(t, f"Asks you: {r['ask']}", step=k); return
        if not await _gate(t):   # a stop pressed during the last step ends it stopped, not done
            return _end(cat_id, t, 'stopped', 'You stopped it.')
        text, usd, bill = await _call(cat_id, t, _tc.recap_msgs(t), RECAP_TOK)
        _spend(cat_id, t, usd, bill)
        t['recap'] = _tc.read_recap(text) or ' · '.join(s['text'] for s in t['steps'])[:300]
        return _end(cat_id, t, 'done', '')
    except rs.asyncio.CancelledError:   # the service is shutting down: the state stays, so the restart puts it back in the queue
        if _CTL.get(t['id']) == 'stop':
            _end(cat_id, t, 'stopped', 'You stopped it.')
        raise
    except Exception as e:   # noqa: BLE001 — one task never takes the service down
        return _end(cat_id, t, 'failed', f'It broke on its own code ({type(e).__name__}); nothing was spent past what is shown.')
    finally:
        _RUN.pop(tid, None)
        rs._POW_WAKE.set()   # the pass posts its recap / starts the next one now, not in 20 s


def _end(cat_id, t, state, why):
    rs = _rs()
    t['state'] = state; t['why'] = why; t['ended'] = rs.time.time(); _CTL.pop(t['id'], None)
    for s in t.get('steps') or []:
        if s.get('state') == 'doing':
            s['state'] = 'pending'
    _tc.log(t, {'done': 'Done.', 'failed': why, 'stopped': why or 'Stopped.'}.get(state, state))
    _POST.append((cat_id, t['id']))


def taskchat_pass(store):
    """The engine's part (the store's one writer): bill, post recaps + record rows, start what waits."""
    rs = _rs()
    for cid, c in (store.get('cats') or {}).items():   # 🛟 after a restart, every agent with task chats is loaded (a requeued one resumes unasked)
        if c and c.get('taskChats') and cid not in _STATE:
            tasks_of(cid, c)
    for cid, rows in _STATE.items():   # 💳 bill what its task chats spent (the same rule as its chat replies)
        b = ((store['cats'].get(cid) or {}).get('brainsCfg'))
        for t in rows:
            usd = float(t.get('unbilled') or 0)
            if b is not None and usd:
                rs._lc.charge(b, usd)
                t['unbilled'] = 0.0
    while _SPLITS:   # 🧵 the card of a task its mind split off, under the answer that split it
        cid, tid = _SPLITS.pop(0)
        cat = store['cats'].get(cid); t = find(cid, cat, tid) if cat else None
        if t:
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"🧵 Split into a task chat: {t['title']}", 'at': rs.time.time(), 'task': tid}])[-200:]
    while _POST:
        cid, tid = _POST.pop(0)
        cat = store['cats'].get(cid); t = find(cid, cat, tid) if cat else None
        if not t or t.get('posted'):
            continue
        t['posted'] = True
        word = {'done': '✅ Task done', 'failed': '⚠ Task failed', 'stopped': '⏹ Task stopped'}.get(t['state'], 'Task')
        body = t.get('recap') if t['state'] == 'done' else (t.get('why') or '')
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"{word}: {t.get('title')}\n{body}".strip(), 'at': rs.time.time(), 'task': tid, 'cost': t.get('cost')}])[-200:]
        k, ref = t['scope'].get('kind'), t['scope'].get('ref')
        if k in _tc.FOLDER_KEYS:   # 🧾 the proof's own record carries it
            rows = [f for f in cat.get(_tc.FOLDER_KEYS[k]) or [] if isinstance(f, dict)]
            f = next((x for x in rows if str(x.get('id')) == ref), None) if ref else None
            if f is not None:
                f['taskChats'] = ([x for x in f.get('taskChats') or [] if x.get('id') != tid] + [_tc.record_row(t)])[-12:]
        cat['jobs'] = (list(cat.get('jobs') or []) + [{'kind': 'task', 'at': rs.time.time(), 'text': t.get('brief'), 'task': _tc.record_row(t)}])[-rs.JOBS_KEEP:]
    for cid in list(_STATE):
        cat = store['cats'].get(cid)
        if cat:
            pump(cid, cat)


def split(cat_id, cat, brief, scope, by='owner', mind=0, test=False):
    """A new task chat (queued), started at once when its parallel setting allows. → the task."""
    rows = tasks_of(cat_id, cat)
    t = _tc.new(brief, scope, by, mind, cap_for(cat), test=test)
    t['state'] = 'queued'
    rows.append(t)
    if by == 'mind':
        _SPLITS.append((cat_id, t['id']))
    _STATE[cat_id] = _tc.trim(rows)
    pump(cat_id, cat)
    if t['state'] == 'queued' and not t.get('why'):
        t['why'] = 'Queued: it works one task at a time. Allow more in its desk settings.'
    return t


def split_answer(cat_id, cat, answer, scope='desk'):
    """🧠 A mind's own /task lines in its answer → task chats. → the answer without those lines."""
    briefs, rest = _tc.splits_in(answer)
    for b_ in briefs:
        split(cat_id, cat, b_, scope, by='mind')
    return (rest or 'I split this into a task chat.') if briefs else answer


async def op(cat_id, cat, store, p):
    """The owner's task chat ops (through /api/cats/{id}/work, owner-gated there). Text work only: none of these can move money."""
    rs = _rs()
    now = rs.time.time()
    if p.op == 'task_new':
        brief = str(p.text or '').strip()
        if len(brief) < 3:
            raise rs.HTTPException(400, 'Say what the task is.')
        t = split(cat_id, cat, brief, p.job or 'desk', 'owner', int(p.to) if str(p.to or '').isdigit() else 0, test=bool((p.tools or {}).get('test')) and p.auto)
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': f'/task {brief}'[:400], 'at': now}, {'by': 'cats', 'text': f"🧵 Split into a task chat: {t['title']}", 'at': now, 'task': t['id']}])[-200:]
        rs.keep_owned(cat); rs._save(store)
        return {'task': _tc.view(t), 'tasks': [_tc.card(x) for x in tasks_of(cat_id, cat)]}
    if p.op == 'task_list':
        rows = tasks_of(cat_id, cat)
        sc = _tc.scope_of(p.job) if p.job else None
        if sc:
            rows = [t for t in rows if t['scope'] == sc or (sc['kind'] != 'desk' and not sc['ref'] and t['scope']['kind'] == sc['kind'])]
        return {'tasks': [_tc.card(t) for t in rows][::-1], 'parallel': int(cat.get('taskParallel') or 1)}
    if p.op == 'task_parallel':
        n = max(1, min(_tc.PARALLEL_MAX, int(rs._num(p.cap) or 1)))
        cat['taskParallel'] = n
        pump(cat_id, cat)
        rs.keep_owned(cat); rs._save(store)
        return {'parallel': n}
    t = find(cat_id, cat, str(p.job or ''))
    if not t:
        raise rs.HTTPException(404, 'No such task chat.')
    if p.op == 'task_get':
        return {'task': _tc.view(t)}
    if t.get('state') in _tc.ENDED and p.op != 'task_say':
        raise rs.HTTPException(409, f"That task is {t['state']}.")
    if p.op == 'task_say':   # 💬 steer it: the next step reads it; an answer to its question resumes it
        line = str(p.text or '').strip()[:400]
        if not line:
            raise rs.HTTPException(400, 'Say something.')
        if t.get('state') in _tc.ENDED:
            raise rs.HTTPException(409, f"That task is {t['state']}: split a new one from its recap.")
        t['msgs'] = (list(t.get('msgs') or []) + [{'by': 'you', 'text': line, 'at': now}])[-_tc.MSGS_KEEP:]
        _tc.log(t, f'You: {line}')
        if t['state'] == 'waiting':
            t['state'] = 'queued'; t['why'] = ''
            pump(cat_id, cat)
    elif p.op == 'task_pause':
        _CTL[t['id']] = 'pause'
        if t['state'] in ('working', 'starting'):
            t['state'] = 'paused'
        _tc.log(t, 'You paused it (it stops after the step it is on).')
    elif p.op == 'task_resume':
        _CTL.pop(t['id'], None)
        if t['state'] == 'paused' and t['id'] in _RUN:
            t['state'] = 'working'
        elif t['state'] in ('paused', 'waiting'):
            t['state'] = 'queued'; t['why'] = ''
            pump(cat_id, cat)
        _tc.log(t, 'You resumed it.')
    elif p.op == 'task_cap':   # 🎚 raise (or lower) this one task's cap, never past its credit / today's limit
        t['cap'] = round(max(0.005, min(float(rs._num(p.cap) or 0), cap_for(cat) + float(t.get('cost') or 0))), 4)
        _tc.log(t, f"Cap set to ${t['cap']:.2f}.")
        if t['state'] == 'waiting' and float(t.get('cost') or 0) < t['cap']:
            t['state'] = 'queued'; t['why'] = ''
            pump(cat_id, cat)
    elif p.op == 'task_stop':
        _CTL[t['id']] = 'stop'
        if t['id'] not in _RUN:   # queued / waiting: it ends now
            _end(cat_id, t, 'stopped', 'You stopped it.')
        else:   # working: it ends after the step it is on (a paused one at once)
            _tc.log(t, 'Stopping after the step it is on.')
    else:
        raise rs.HTTPException(400, 'Unknown task op.')
    rs._save(store)
    return {'task': _tc.view(t)}
