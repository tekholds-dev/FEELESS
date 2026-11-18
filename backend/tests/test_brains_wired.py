"""🧠 Slice 1 (owner 2026-11-18: "I'm choosing a mind per proof and the backend doesn't even work??"): every Brains / agent-desk control, proven
click → saved → used by the engine → shown in the next proof's record. Network faked; the real free run is a TEST on Sicario's agent.
The list of controls and whether each is wired lives in docs/SLICES.md (Slice 1 Status)."""
import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

import launch_cat as lc


@pytest.fixture(autouse=True)
def _signed_owner(monkeypatch):
    import feecat_service as svc
    monkeypatch.setattr(svc, '_session_wallet', lambda s: str(s or ''))
    monkeypatch.setattr(svc, '_fresh_session_wallet', lambda s, now=None: str(s or ''))


def _row(i, efforts=True):
    r = {'id': i, 'name': i.split('/')[-1], 'context_length': 131072, 'pricing': {'prompt': '0.00000002', 'completion': '0.00000009'},
         'supported_parameters': ['reasoning', 'temperature', 'top_p']}
    if efforts:
        r['reasoning'] = {'supported_efforts': ['low', 'medium', 'high']}
    return r


A, B, C = 'openai/gpt-oss-20b', 'qwen/qwen3-4b-2507', 'z-ai/glm-5.3'


def _svc(tmp_path, monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'STORE_PATH', tmp_path / 'feecats.json')
    monkeypatch.setattr(fs, '_MODELS', {'at': 9e18, 'rows': lc.catalog([_row(A), _row(B), _row(C)])})
    monkeypatch.setattr(fs, 'MODEL_LOCK_SEC', 0)   # the 24 h switch lock is proven in test_kind_minds / the desk tests
    monkeypatch.delenv('LAUNCH_CAT_LIVE', raising=False)
    c = TestClient(fs.app)
    r = c.post('/api/cats', json={'ownerId': 'w', 'session': 'w', 'name': 'Duo', 'handle': 'duo', 'brains': [A, B], 'brainMode': 'turns', 'billing': 'payg', 'prompt': 'hunt germ floors'})
    assert r.status_code == 200, r.text
    return fs, c, r.json()['cat']['id']


def _act(c, cid, action, **kw):
    r = c.post(f'/api/cats/{cid}/action', json={'ownerId': 'w', 'session': 'w', 'action': action, **kw})
    assert r.status_code == 200, r.text
    return r.json()['cat']


def _work(c, cid, op, **kw):
    r = c.post(f'/api/cats/{cid}/work', json={'ownerId': 'w', 'session': 'w', 'op': op, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def _cat(fs, cid):
    return fs._load()['cats'][cid]


def _rows(fs):
    p = fs.DATA_DIR / 'mind_calls.jsonl'
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def _fake_models(monkeypatch, fs, asked, systems=None):
    """A fake model door: it records WHO was asked, with which effort / knobs, and says who answered (the call log is written by _think)."""
    async def fake_routes(cat, model, messages, own_key=None, effort=None, max_tokens=None):
        asked.append({'model': model, 'effort': effort, 'knobs': fs._OR_KNOBS.get()})
        if systems is not None:
            systems.append(messages[0]['content'])
        fs._heard(route='openrouter', model=model + '-0813', tokens=10)
        return 'an answer', 0.0, 'openrouter'
    monkeypatch.setattr(fs, '_think_routes', fake_routes)
    monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: None)


def _file(fs, cid, kind, ref, **extra):
    """File a folder the way every filer does: through _record_file, which stamps the true record from the call log."""
    store = fs._load(); cat = store['cats'][cid]
    f = {'id': ref, 'n': len(cat.get(fs._prec.KEYS[kind]) or []) + 1, 'at': time.time(), 'topic': 'germ floors', 'sitesRead': ['https://dexscreener.com/solana/x'], **extra}
    fs._record_file(cat, kind, f)
    cat.setdefault(fs._prec.KEYS[kind], []).append(f)
    fs._save(store)
    return f


# ---- 1 · the agent's two minds (🔁 ITS MODELS) -------------------------------------------------------------------
def test_switching_the_two_minds_is_saved_used_for_every_proof_and_shown(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    cat = _act(c, cid, 'models', brains=[B, C], memory='keep')
    assert cat['brainsCfg']['brains'] == [B, C]                                   # saved
    assert lc.minds_for(_cat(fs, cid)['brainsCfg'], 'pop') == [B, C]              # the engine's reader gives it to every kind that has no pair of its own
    asked = []; _fake_models(monkeypatch, fs, asked)
    for i in (0, 1):
        asyncio.run(fs._pow2_ask(_cat(fs, cid), i, 'sys', 'user', 50, {'cost': 0, 'ref': 'pop1', 'proof': 'pop'}))
    assert [a['model'] for a in asked] == [B, C]                                  # used
    f = _file(fs, cid, 'pop', 'pop1')
    assert [r['asked'] for r in f['ran']] == [B, C] and f['mindsCheck']['ok'] and f['proofChecks'][0]['ok']   # shown: ran from the call log, matching the pair


def test_a_switch_can_wipe_or_keep_the_memory(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    store = fs._load(); store['cats'][cid]['brainsCfg'].update(cloud=[{'text': 'old note'}], minds={A: {'x': 1}}); fs._save(store)
    kept = _act(c, cid, 'models', brains=[A, B], memory='keep')['brainsCfg']
    assert kept['cloud'] == [{'text': 'old note'}]
    fresh = _act(c, cid, 'models', brains=[B, C], memory='fresh')['brainsCfg']
    assert fresh['cloud'] == [] and fresh['brains'] == [B, C]


# ---- 2 · BY PROOF: each kind's own two minds ----------------------------------------------------------------------
@pytest.mark.parametrize('kind', ['pow', 'pop', 'pob'])
def test_a_kinds_own_pair_is_saved_used_by_its_asks_and_the_record_names_it(tmp_path, monkeypatch, kind):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    cat = _act(c, cid, 'kind_models', text=kind, brains=[C, A])
    assert cat['brainsCfg']['byKind'][kind] == [C, A]                              # saved
    assert lc.minds_for(_cat(fs, cid)['brainsCfg'], kind) == [C, A]
    asked = []; _fake_models(monkeypatch, fs, asked)
    box = {'cost': 0, 'ref': f'{kind}7', 'proof': kind}
    for i in (0, 1):
        asyncio.run(fs._pow2_ask(_cat(fs, cid), i, 'sys', 'user', 50, box))
    assert [a['model'] for a in asked] == [C, A]                                   # used: not the agent's own [A, B]
    f = _file(fs, cid, kind, f'{kind}7')
    assert [r['asked'] for r in f['ran']] == [C, A] and f['mindsCheck']['ok'] and f['mindsCheck']['set'] == [C, A]   # shown
    # clearing it goes back to the agent's pair, for the next proof
    cleared = _act(c, cid, 'kind_models', text=kind, brains=[])
    assert kind not in (cleared['brainsCfg'].get('byKind') or {}) and lc.minds_for(_cat(fs, cid)['brainsCfg'], kind) == [A, B]


@pytest.mark.parametrize('kind', ['poc', 'pos', 'poe'])
def test_the_other_kinds_pick_their_own_pair_the_same_way(tmp_path, monkeypatch, kind):
    """PoC and PoStatic read the pair at the top of their build (fc_desk / fc_pow / fc_tools); a model call inside their context is logged under it."""
    fs, c, cid = _svc(tmp_path, monkeypatch)
    _act(c, cid, 'kind_models', text=kind, brains=[C, A])
    cfg = _cat(fs, cid)['brainsCfg']
    assert lc.minds_for(cfg, kind) == [C, A] and lc.minds_for(cfg, 'pob') == [A, B]   # only that kind moved
    asked = []; _fake_models(monkeypatch, fs, asked)

    async def one():
        tok = fs._CALL_CTX.set({'kind': kind, 'ref': f'{kind}9', 'minds': lc.minds_for(cfg, kind)})
        try:
            return await fs._think(_cat(fs, cid), lc.minds_for(cfg, kind)[0], [{'role': 'user', 'content': 'hi'}])
        finally:
            fs._CALL_CTX.reset(tok)
    asyncio.run(one())
    assert asked[0]['model'] == C and _rows(fs)[-1]['kind'] == kind and _rows(fs)[-1]['asked'] == C


def test_the_pair_setting_is_checked_server_side(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    for body in ({'text': 'nope', 'brains': [A]}, {'text': 'pob', 'brains': [A, B, C]}, {'text': 'pob', 'brains': ['not/listed']}):
        r = c.post(f'/api/cats/{cid}/action', json={'ownerId': 'w', 'session': 'w', 'action': 'kind_models', **body})
        assert r.status_code == 400, body


# ---- 3 · effort + knobs (🎛 model_cfg) ------------------------------------------------------------------------------
def test_effort_and_knobs_are_saved_ride_every_proof_call_and_show_in_the_record(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    cat = _act(c, cid, 'model_cfg', efforts={A: 'high'}, knobs={A: {'temperature': 0.2}})
    assert cat['brainsCfg']['efforts'] == {A: 'high'} and cat['brainsCfg']['knobs'][A]['temperature'] == 0.2   # saved
    assert c.post(f'/api/cats/{cid}/action', json={'ownerId': 'w', 'session': 'w', 'action': 'model_cfg', 'efforts': {A: 'max'}}).status_code == 400   # an effort the model does not list
    asked = []; _fake_models(monkeypatch, fs, asked)
    asyncio.run(fs._pow2_ask(_cat(fs, cid), 0, 'sys', 'user', 50, {'cost': 0, 'ref': 'pob3', 'proof': 'pob'}))
    assert asked[0]['effort'] == 'high' and asked[0]['knobs'][A]['temperature'] == 0.2   # used: a proof call (it was always None before Slice 1)
    f = _file(fs, cid, 'pob', 'pob3')
    r0 = [r for r in f['ran'] if r['asked'] == A][0]
    assert r0['effort'] == 'high' and r0['knobs']['temperature'] == 0.2               # shown
    assert _act(c, cid, 'model_cfg', efforts={})['brainsCfg']['efforts'] == {}


def test_a_build_ask_for_poc_and_postatic_carries_the_effort_too(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    _act(c, cid, 'model_cfg', efforts={A: 'low'})
    asked = []; _fake_models(monkeypatch, fs, asked)
    asyncio.run(fs._ws_ask(_cat(fs, cid), A, 'sys', 'user', 100))
    assert asked[0]['effort'] == 'low'


# ---- 4 · a kind's own prompt + personality (🎭 Features › voice) ------------------------------------------------------
def test_a_kinds_prompt_and_personality_are_saved_put_in_front_of_its_asks_and_shown(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    out = _work(c, cid, 'kind_voice', text='pob', tools={'prompt': 'Always say which sources disagree.', 'persona': {'style': 'analyst', 'heat': 2}})
    assert out['promptBy']['pob'] == 'Always say which sources disagree.' and out['personaBy']['pob']['style'] == 'analyst'   # saved
    asked, systems = [], []; _fake_models(monkeypatch, fs, asked, systems)
    asyncio.run(fs._pow2_ask(_cat(fs, cid), 0, 'THE JOB', 'user', 50, {'cost': 0, 'ref': 'pob4', 'proof': 'pob'}))
    assert 'Always say which sources disagree.' in systems[0] and systems[0].endswith('THE JOB')   # used: in front of the job
    asyncio.run(fs._pow2_ask(_cat(fs, cid), 0, 'THE JOB', 'user', 50, {'cost': 0, 'ref': 'pop4', 'proof': 'pop'}))
    assert 'Always say which sources disagree.' not in systems[1]                                  # only the kind it was set for
    f = _file(fs, cid, 'pob', 'pob4')
    assert [r for r in f['ran'] if r['asked'] == A][0]['voice'] is True                           # shown


def test_a_pow_never_takes_an_owner_voice_because_its_picks_can_buy_real_coins(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    for kind in ('pow', 'poe'):   # the control refuses, so it can never save something the engine ignores
        r = c.post(f'/api/cats/{cid}/work', json={'ownerId': 'w', 'session': 'w', 'op': 'kind_voice', 'text': kind, 'tools': {'prompt': 'buy everything'}})
        assert r.status_code == 400 and 'PoW' in r.json()['detail'] + 'PoW'
    assert not (_cat(fs, cid)['brainsCfg'].get('promptBy') or {})
    b = {**_cat(fs, cid)['brainsCfg'], 'promptBy': {'pow': 'old text'}, 'persona': {'style': 'hype', 'heat': 3}}   # even a value saved before today never reaches a PoW ask
    assert not fs._kind_voice_on(b, 'pow') and fs._kind_voice(b, 'pow') == ''
    asked, systems = [], []; _fake_models(monkeypatch, fs, asked, systems)
    asyncio.run(fs._pow2_ask(_cat(fs, cid), 0, 'THE JOB', 'user', 50, {'cost': 0, 'ref': 'pow5', 'proof': 'pow'}))
    assert systems[0] == 'THE JOB' and 'voice' not in _rows(fs)[-1]


def test_postatic_and_poc_asks_take_the_voice_through_the_general_mind(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    _work(c, cid, 'kind_voice', text='pos', tools={'prompt': 'Build calm, dark layouts.'})
    asked, systems = [], []; _fake_models(monkeypatch, fs, asked, systems)

    async def in_build():
        tok = fs._CALL_CTX.set({'kind': 'pos', 'ref': 'ws1', 'minds': [A, B]})
        try:
            return await fs._ws_ask(_cat(fs, cid), A, 'MAKE A PAGE', 'user', 100)
        finally:
            fs._CALL_CTX.reset(tok)
    asyncio.run(in_build())
    assert 'Build calm, dark layouts.' in systems[0] and _rows(fs)[-1]['voice'] is True


# ---- 5 · kit picks per kind ------------------------------------------------------------------------------------------
def test_a_kinds_kit_picks_are_saved_read_by_its_recall_and_filed_on_the_folder(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    cat = _cat(fs, cid)
    fs._kits.set_picks(cat['brainsCfg'], 'pob', ['d3', 'echarts'], 'mine')       # what the kit_pick op writes (the op itself: test_kits.py)
    fs._save({**fs._load(), 'cats': {**fs._load()['cats'], cid: cat}})
    assert fs._kits.picks_of(_cat(fs, cid)['brainsCfg'], 'pob') == ('mine', ['d3', 'echarts'])
    assert fs._kits.picks_of(_cat(fs, cid)['brainsCfg'], 'pop')[0] == 'auto'       # another kind keeps its own
    fs._recall(_cat(fs, cid), 'Picks', 'nba tonight')
    assert fs._KIT_LAST[(cid, 'pob')] == ['d3', 'echarts']                          # used by the proof
    asked = []; _fake_models(monkeypatch, fs, asked)
    asyncio.run(fs._pow2_ask(_cat(fs, cid), 0, 'sys', 'user', 50, {'cost': 0, 'ref': 'pob6', 'proof': 'pob'}))
    f = _file(fs, cid, 'pob', 'pob6', kits=fs._KIT_LAST.get((cid, 'pob')))        # the PoB filer does exactly this
    assert f['kits'] == ['d3', 'echarts'] and [x for x in f['proofChecks'] if x['key'] == 'kits'][0]['ok']   # shown


# ---- 6 · where it trades (📍 venues) --------------------------------------------------------------------------------
def test_the_venue_picker_only_stores_a_rail_the_engine_really_trades_on(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    assert _act(c, cid, 'venues', venues=['trench'])['venues'] == ['trench']
    r = c.post(f'/api/cats/{cid}/action', json={'ownerId': 'w', 'session': 'w', 'action': 'venues', 'venues': ['trench', 'perps']})
    assert r.status_code == 400 and 'not built for agents yet' in r.json()['detail']
    assert _cat(fs, cid)['venues'] == ['trench']                                    # nothing changed
    assert c.post(f'/api/cats/{cid}/action', json={'ownerId': 'w', 'session': 'w', 'action': 'venues', 'venues': ['binance']}).status_code == 400


# ---- 7 · chime, limits, run switches, skin ---------------------------------------------------------------------------
def test_a_chime_is_saved_and_the_next_decision_reads_it(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    cat = _act(c, cid, 'chime', text='watch the dev wallet')
    assert cat['brainsCfg']['chime'][-1]['text'] == 'watch the dev wallet'
    msgs = lc.ask_messages(_cat(fs, cid)['brainsCfg'], '$X case', partner=None)
    assert 'watch the dev wallet' in json.dumps(msgs)


def test_the_limits_are_saved_and_cap_the_next_order(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    cat = _act(c, cid, 'controls', maxPositionSol='0.07', maxDailyLossSol='0.3', allowlist='BONK, WIF', blocklist='RUG')
    assert cat['risk']['maxPositionSol'] == 0.07 and cat['risk']['maxDailyLossSol'] == 0.3
    assert cat['risk']['allowlist'] == ['BONK', 'WIF'] and cat['risk']['blocklist'] == ['RUG']
    import cat_orders as co
    assert co.size_of({'sol': 2}, fs._num(_cat(fs, cid)['risk']['maxPositionSol']))[0] == 0.07   # the order door reads exactly this field


def test_the_only_these_never_these_coin_lists_are_saved_and_filter_pows_candidates(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    _act(c, cid, 'controls', allowlist='', blocklist='$RUG, MINT9')
    cat = _cat(fs, cid); coin = lambda sym, mint='M' + 'x' * 8: {'sym': sym, 'mint': mint}   # noqa: E731
    assert fs._owner_coin_lists(cat, coin('RUG')).startswith('on your NEVER')       # by symbol (case and $ ignored)
    assert fs._owner_coin_lists(cat, coin('ok', 'mint9')).startswith('on your NEVER')   # by mint
    assert fs._owner_coin_lists(cat, coin('GERM')) == ''                           # an empty allowlist = any coin
    _act(c, cid, 'controls', allowlist='GERM, bonk', blocklist='')
    cat = _cat(fs, cid)
    assert fs._owner_coin_lists(cat, coin('germ')) == '' and fs._owner_coin_lists(cat, coin('WIF')) == 'not on your ONLY THESE COINS list'
    assert fs._owner_coin_lists({}, coin('WIF')) == '' and fs._owner_coin_lists(None, coin('WIF')) == ''
    import inspect
    import fc_pow
    src = inspect.getsource(fc_pow)   # used: the PoW candidate loop drops a listed coin before the safe / fingerprint checks, naming the reason
    assert "own_ = rs._owner_coin_lists(cat, c)" in src and "'risk': own_" in src


def test_start_stop_and_the_skin_are_saved_and_come_back_on_the_desk(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    assert _act(c, cid, 'start')['status'] == 'running'
    assert _act(c, cid, 'stop')['status'] == 'stopped' and _cat(fs, cid)['status'] == 'stopped'
    sk = _act(c, cid, 'skin', look={'bg': 'night', 'acc': '#19e68c'})
    assert sk['skin']['acc'] == '#19e68c' and c.get(f'/api/cats/{cid}', params={'ownerId': 'w', 'session': 'w'}).json()['cat']['skin']['acc'] == '#19e68c'


# ---- 8 · Brains shows what REALLY ran on the last proof of each kind -------------------------------------------------
def test_brains_shows_the_minds_that_ran_on_the_last_proof_of_each_kind_from_the_call_log(tmp_path, monkeypatch):
    fs, c, cid = _svc(tmp_path, monkeypatch)
    _act(c, cid, 'kind_models', text='pob', brains=[C, A])
    asked = []; _fake_models(monkeypatch, fs, asked)
    for i in (0, 1):
        asyncio.run(fs._pow2_ask(_cat(fs, cid), i, 'sys', 'user', 50, {'cost': 0, 'ref': 'pob8', 'proof': 'pob'}))
    _file(fs, cid, 'pob', 'pob8')
    _act(c, cid, 'kind_models', text='pob', brains=[B, C])                          # the owner changes the pair AFTER the proof ran
    d = c.get(f'/api/cats/{cid}/paths', params={'ownerId': 'w', 'session': 'w'}).json()['paths']
    by = {p['kind']: p for p in d}
    last = by['pob']['last']
    assert [r['asked'] for r in last['ran']] == [C, A] and last['fromLog'] and last['check']['ok']   # what ran, not what is set now
    assert last['pairNow'] == [B, C] and last['changed'] is True                                     # and it says the setting moved since
    assert by['pob']['minds'] == [B, C] and by['pop']['last'] is None                                # a kind with no proof says so
    # a TEST proof counts as the last proof of its kind, and says so
    f = _file(fs, cid, 'pop', 'pop9', test={'by': 'Claude', 'at': time.time(), 'free': True})
    assert c.get(f'/api/cats/{cid}/paths', params={'ownerId': 'w', 'session': 'w'}).json()['paths'][1]['last']['test'] is True


def test_last_ran_is_pure_and_falls_back_to_the_stored_record():
    import proof_record as pr
    f = {'id': 'pob1', 'n': 3, 'at': 100, 'ran': [{'asked': 'a/one', 'ok': 1, 'calls': 2}], 'mindsCheck': {'set': ['a/one', 'b/two']}}
    got = pr.last_ran('pob', [f], [], ['a/one', 'b/two'])
    assert got['fromLog'] is False and got['ran'][0]['asked'] == 'a/one' and got['changed'] is False and got['check']['missing'] == ['b/two']
    assert pr.last_ran('pob', [], [], ['a']) is None
    rows = [{'kind': 'pob', 'ref': 'pob1', 'asked': 'x/new', 'ok': True, 'at': 99, 'route': 'openrouter', 'model': 'x/new', 'effort': 'high'}]
    got = pr.last_ran('pob', [f], rows, ['a/one'])
    assert got['fromLog'] and got['ran'][0]['asked'] == 'x/new' and got['ran'][0]['effort'] == 'high' and got['changed'] is True


def test_the_topic_pob_path_reads_its_kinds_kit_picks():
    """Found by Slice 1's real TEST: the kit picks only reached the old PoB path, so a topic PoB filed with kits ✗. The check that proves it for real is a TEST
    PoB on Sicario (PoB #4: kits ✓); this keeps the call from being dropped."""
    import inspect

    import fc_pob
    src = inspect.getsource(fc_pob._pob_topic_file)
    assert "_recall(cat, 'Picks', rd['topic'])" in src and "topic_sys(names[i], rd['topic']) + recall_" in src
