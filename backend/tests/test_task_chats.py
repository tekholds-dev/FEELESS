"""🧵 Slice 35 · task chats, wired end to end (network faked): split → task saved → the runner works it (checklist, thoughts, logs, cost per
step) → the card updates → the recap returns to the main chat → it is on the proof's record. Plus: the queue (one at a time by default, N when
allowed), steer / pause / stop / cap, a mind's own /task split, and §1 (text work only: no task op or prompt can move money)."""
import asyncio
import json

import pytest

import task_chats as tc

fs = pytest.importorskip('feecat_service')
ftc = fs._fc_taskchat


def _store(**extra):
    return {'cats': {'h1': {'id': 'h1', 'name': 'Happy', 'ownerId': 'b1', 'positions': [], 'risk': {}, 'status': 'stopped', 'revoked': False, 'balanceSol': 0,
                            'chat': [], 'taskCap': 0.20, 'powFolders': [{'id': 'pw1', 'n': 3, 'topic': '$WIF breakout', 'phase': 'watch'}],
                            'brainsCfg': {'kind': 'general', 'brains': ['m/a', 'm/b'], 'credit': 5.0, 'billing': 'payg'}, **extra}}, 'events': []}


@pytest.fixture
def world(monkeypatch):
    store = _store()
    calls = []

    async def think(cat, model, messages, own_key=None, effort=None, max_tokens=None):
        sys_ = messages[0]['content']; user = messages[-1]['content']
        calls.append({'model': model, 'sys': sys_, 'user': user, 'ctx': fs._CALL_CTX.get()})
        await asyncio.sleep(0)
        if '"steps"' in sys_:
            return json.dumps({'think': 'Three checks cover it.', 'title': 'Review the WIF filing', 'steps': ['Read the call', 'Check the exit', 'List fixes']}), 0.002, 'openrouter'
        if '"recap"' in sys_:
            return json.dumps({'recap': 'Read the call and the exit.\nThree fixes listed.'}), 0.001, 'openrouter'
        return json.dumps({'think': 'Looking at the numbers.', 'did': f'did: {user[-30:]}', 'log': ['read the folder'], 'ask': ''}), 0.003, 'openrouter'

    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: ftc.merge(s))
    monkeypatch.setattr(fs, '_think', think)
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: None)
    ftc._STATE.clear(); ftc._RUN.clear(); ftc._CTL.clear(); ftc._POST.clear(); ftc._SPLITS.clear()
    yield store, calls
    for t in list(ftc._RUN.values()):
        t.cancel()
    ftc._STATE.clear(); ftc._RUN.clear()


def P(op, **k):
    return fs.WorkPayload(op=op, ownerId='b1', session='b1', **k)


async def _drain():
    while ftc._RUN:
        await asyncio.gather(*list(ftc._RUN.values()), return_exceptions=True)


def test_split_runs_live_and_returns_its_recap(world):
    store, calls = world
    cat = store['cats']['h1']

    async def go():
        out = await ftc.op('h1', cat, store, P('task_new', text='Check this PoW and list three fixes', job='pow:pw1'))
        assert out['task']['state'] in ('starting', 'working') and out['task']['scope'] == {'kind': 'pow', 'ref': 'pw1'}
        assert any(m.get('task') == out['task']['id'] for m in cat['chat'])            # the card in the original chat
        assert store['cats']['h1']['taskChats'][0]['id'] == out['task']['id']         # saved (merged into the save)
        await _drain()
        return out['task']['id']
    tid = asyncio.run(go())
    v = tc.view(ftc.find('h1', cat, tid))
    assert v['state'] == 'done' and v['title'] == 'Review the WIF filing'
    assert [s['state'] for s in v['checklist']] == ['done'] * 3 and all(s['did'] for s in v['checklist'])
    assert [t['step'] for t in v['thoughts']] == [-1, 0, 1, 2] and all('s' in t for t in v['thoughts'])   # each thought: its own fold-open row with its seconds
    assert any(l['text'] == 'read the folder' and l['step'] == 0 for l in v['logs'])
    assert v['cost'] == pytest.approx(0.002 + 3 * 0.003 + 0.001)
    assert v['checklist'][0]['cost'] == pytest.approx(0.005)                           # cost per step (the plan rides step 1)
    # same mind + settings: its PoW pair (none set → its brains), the folder as read-only context, logged as this task
    assert calls[0]['model'] == 'm/a' and '$WIF breakout' in calls[0]['user'] and calls[0]['ctx']['ref'] == f'task:{tid}' and calls[0]['ctx']['kind'] == 'pow'
    assert all(tc.NO_MONEY in c['sys'] for c in calls[:-1])                            # §1 in every working prompt
    before = cat['brainsCfg']['credit']
    fs._fc_taskchat.taskchat_pass(store)                                                # the engine's pass
    assert cat['brainsCfg']['credit'] == pytest.approx(before - v['cost'])             # billed once, to its own credit
    last = cat['chat'][-1]
    assert last['task'] == tid and 'Task done' in last['text'] and 'Three fixes listed.' in last['text']   # the recap back in the main chat
    rec = cat['powFolders'][0]['taskChats'][0]
    assert rec['id'] == tid and rec['recap'].startswith('Read the call') and rec['steps'][0] == 'Read the call'   # on the proof's record
    assert cat['jobs'][-1]['kind'] == 'task'
    ftc.taskchat_pass(store); assert sum(1 for m in cat['chat'] if m.get('task') == tid and 'done' in m['text']) == 1   # posted once


def test_queue_one_at_a_time_then_parallel(world):
    store, _ = world
    cat = store['cats']['h1']

    async def go():
        a = (await ftc.op('h1', cat, store, P('task_new', text='first job here')))['task']
        b = (await ftc.op('h1', cat, store, P('task_new', text='second job here')))['task']
        assert a['state'] == 'starting' and b['state'] == 'queued' and 'one task at a time' in b['why']
        assert (await ftc.op('h1', cat, store, P('task_parallel', cap=2)))['parallel'] == 2
        assert ftc.find('h1', cat, b['id'])['state'] == 'starting'                      # the setting is used by the queue at once
        assert cat['taskParallel'] == 2 and 'taskParallel' in fs.OWNER_KEYS             # saved, and an older copy can't undo it
        await _drain()
    asyncio.run(go())
    assert all(t['state'] == 'done' for t in ftc.tasks_of('h1', cat))


def test_steer_pause_stop_and_cap(world):
    store, calls = world
    cat = store['cats']['h1']

    async def go():
        t = (await ftc.op('h1', cat, store, P('task_new', text='a long job to steer')))['task']
        await ftc.op('h1', cat, store, P('task_say', job=t['id'], text='use only DexScreener'))
        await ftc.op('h1', cat, store, P('task_pause', job=t['id']))
        assert ftc.find('h1', cat, t['id'])['state'] == 'paused'
        await asyncio.sleep(0.05)
        assert ftc.find('h1', cat, t['id'])['state'] == 'paused' and len(calls) == 0   # paused before it began: not even the plan call runs
        await ftc.op('h1', cat, store, P('task_resume', job=t['id']))
        while not calls:
            await asyncio.sleep(0)
        await ftc.op('h1', cat, store, P('task_pause', job=t['id']))
        await asyncio.sleep(0.05)
        n = len(calls)
        await asyncio.sleep(0.05); assert len(calls) == n                              # paused: no new step runs
        await ftc.op('h1', cat, store, P('task_stop', job=t['id']))
        await _drain()
        assert ftc.find('h1', cat, t['id'])['state'] == 'stopped'
        assert any('use only DexScreener' in c['user'] for c in calls)               # the next call read the owner's line
        # cap: a task at its cap waits for the owner; raising it resumes it
        c2 = (await ftc.op('h1', cat, store, P('task_new', text='capped job here')))['task']
        ftc.find('h1', cat, c2['id'])['cap'] = 0.004
        await _drain()
        t2 = ftc.find('h1', cat, c2['id'])
        assert t2['state'] == 'waiting' and 'cap' in t2['why']
        await ftc.op('h1', cat, store, P('task_cap', job=c2['id'], cap=0.2))
        await _drain()
        assert ftc.find('h1', cat, c2['id'])['state'] == 'done'
    asyncio.run(go())


def test_a_mind_splits_its_own_task(world):
    store, _ = world
    cat = store['cats']['h1']

    async def go():
        rest = ftc.split_answer('h1', cat, 'Here is the short answer.\n/task Compare 3 pools: a table of fees and depth')
        assert rest == 'Here is the short answer.'
        t = ftc.tasks_of('h1', cat)[-1]
        assert t['by'] == 'mind' and t['title'] == 'Compare 3 pools' and t['brief'].endswith('fees and depth')
        ftc.taskchat_pass(store)
        assert cat['chat'][-1]['task'] == t['id'] and 'Split into a task chat' in cat['chat'][-1]['text']
        await _drain()
    asyncio.run(go())
    assert tc.TASK_HINT.startswith('If a job needs')


def test_route_wiring_and_owner_gate(world, monkeypatch):
    from fastapi.testclient import TestClient
    store, _ = world
    store['cats']['h1']['brainsCfg']['brains'] = []                                    # no mind: it saves and says why, it never runs
    c = TestClient(fs.app)
    r = c.post('/api/cats/h1/work', json={'op': 'task_new', 'ownerId': 'b1', 'session': 'b1', 'text': 'write a plan', 'job': 'desk'})
    assert r.status_code == 200 and r.json()['task']['why'] == 'It has no mind set (Brains).'
    assert c.post('/api/cats/h1/work', json={'op': 'task_list', 'ownerId': 'b1', 'session': 'b1'}).json()['tasks'][0]['title'] == 'write a plan'
    assert c.post('/api/cats/h1/work', json={'op': 'task_list', 'ownerId': 'x9', 'session': 'x9'}).status_code in (401, 403)   # owner only
    assert c.post('/api/cats/h1/work', json={'op': 'task_bogus', 'ownerId': 'b1', 'session': 'b1', 'job': 'nope'}).status_code == 404


def test_restart_requeues_from_the_first_step_not_done():
    cat = {'taskChats': [{**tc.new('job', 'desk'), 'state': 'working', 'steps': [{'text': 'a', 'state': 'done'}, {'text': 'b', 'state': 'doing'}]}]}
    ftc._STATE.pop('rz', None)
    t = ftc.tasks_of('rz', cat)[0]
    assert t['state'] == 'queued' and [s['state'] for s in t['steps']] == ['done', 'pending'] and 'restarted' in t['logs'][-1]['text']
    ftc._STATE.pop('rz', None)


def test_pure_helpers():
    assert tc.scope_of('pow:PW1!') == {'kind': 'pow', 'ref': 'pw1'} and tc.scope_of('bogus') == {'kind': 'desk', 'ref': ''}
    assert tc.read_plan('not json') == ('', '', [])
    assert tc.read_step('plain words')['did'] == 'plain words'
    assert tc.can_start([{'state': 'working'}], 1) == 0 and tc.can_start([{'state': 'working'}], 9) == 2   # capped at 3
    rows = [{**tc.new(f'j{i}', 'desk', now=i), 'state': 'done'} for i in range(tc.KEEP + 5)] + [{**tc.new('live', 'desk', now=0), 'state': 'working'}]
    kept = tc.trim(rows); assert len(kept) == tc.KEEP and any(t['state'] == 'working' for t in kept)


def test_no_task_path_reaches_money():
    """§1: every service door the task chat code touches is on this list — its mind (_think), billing its credit, its chat. None trades, bids,
    sends, signs or posts. A new door used here fails this test until someone checks it."""
    import ast
    import inspect
    used = set()
    for mod in (ftc, tc):
        for n in ast.walk(ast.parse(inspect.getsource(mod))):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'rs':
                used.add(n.attr)
    allowed = {'_load', '_save', '_think', '_CALL_CTX', '_ck', 'DATA_DIR', '_lc', 'asyncio', 'time', 'json', 'HTTPException', '_num', 'keep_owned',
               '_POW_WAKE', 'TASK_CAP_DEFAULT', '_task_cap_max', 'day_left', 'JOBS_KEEP'}
    assert used <= allowed, used - allowed
    lc_used = {n.attr for n in ast.walk(ast.parse(inspect.getsource(ftc))) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute) and n.value.attr == '_lc'}
    assert lc_used <= {'minds_for', 'charge', 'can_ask', 'CREDIT_RESERVE'}, lc_used   # launch_cat: minds + billing only


def test_mid_run_credit_and_day_limit_hold_it(world):
    """🔒 Checked before EVERY step on the fresh store, counting what is spent but not billed yet: parallel / long task chats never pass the
    credit reserve or today's $ limit."""
    store, calls = world
    cat = store['cats']['h1']
    cat['taskCap'] = 0.2

    async def go():
        t = (await ftc.op('h1', cat, store, P('task_new', text='spend past the reserve')))['task']   # its cap is set while credit is $5
        cat['brainsCfg']['credit'] = 0.105                                              # then its chat / other tasks spend: 0.005 above the reserve
        await _drain()
        return ftc.find('h1', cat, t['id'])
    t = asyncio.run(go())
    assert t['state'] == 'waiting' and 'credit' in t['why'] and len(calls) == 2         # plan ($0.002) + step 1 ($0.003), then it holds
    assert t['unbilled'] == pytest.approx(0.005) and ftc.pending('h1') == pytest.approx(0.005)
    ftc.merge(store); assert store['cats']['h1']['taskChats'][0]['unbilled'] == pytest.approx(0.005)   # on the saved task: a restart keeps it
    ftc.taskchat_pass(store)
    assert cat['brainsCfg']['credit'] == pytest.approx(0.10) and ftc.pending('h1') == 0  # billed once from the task itself
    cat2 = _store(limits={'dayUsd': 0.004})['cats']['h1']
    assert ftc._ready(cat2, 0.004).startswith("It reached today's") and ftc._ready(cat2, 0.0) == ''


def test_stop_during_the_last_step_ends_stopped_not_done(world):
    store, calls = world
    cat = store['cats']['h1']

    async def go():
        t = (await ftc.op('h1', cat, store, P('task_new', text='stop me at the end')))['task']
        while len(calls) < 4:                                                           # plan + 3 steps sent
            await asyncio.sleep(0)
        await ftc.op('h1', cat, store, P('task_stop', job=t['id']))
        await _drain()
        return ftc.find('h1', cat, t['id'])
    t = asyncio.run(go())
    assert t['state'] == 'stopped' and not any('"recap"' in c['sys'] for c in calls)


def test_restart_posts_a_recap_it_missed_and_resumes_unasked(world):
    store, _ = world
    cat = store['cats']['h1']
    done = {**tc.new('ended before the reload', 'pow:pw1'), 'state': 'done', 'recap': 'All read.', 'steps': [{'text': 'a', 'state': 'done'}]}
    live = {**tc.new('cut off mid-step', 'desk'), 'state': 'working', 'steps': [{'text': 'a', 'state': 'doing'}]}
    cat['taskChats'] = [done, live]

    async def go():
        ftc.taskchat_pass(store)                                                        # nobody opened the desk: the pass loads it
        assert ftc.find('h1', cat, live['id'])['state'] in ('starting', 'working')
        await _drain()
    asyncio.run(go())
    assert any(m.get('task') == done['id'] and 'All read.' in m['text'] for m in cat['chat'])
    assert cat['powFolders'][0]['taskChats'][0]['id'] == done['id']
    assert ftc.find('h1', cat, live['id'])['state'] == 'done'


def test_a_task_line_in_a_code_block_is_not_a_split():
    briefs, rest = tc.splits_in('You can type:\n```\n/task compare pools\n```\nThat is all.')
    assert briefs == [] and '/task compare pools' in rest
    briefs, rest = tc.splits_in('Short.\n```\n/task not me\n```\n/task Real one here')
    assert briefs == ['Real one here'] and '/task not me' in rest and 'Real one' not in rest
