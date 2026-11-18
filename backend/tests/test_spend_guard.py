"""💵 The owner's day cap (owner 2026-11-17: "DO WHATEVER EXCEPT USE MY MONEY TO WASTE ON BULLSHIT", "assure real money readyness").
Every paid call on his own keys is checked against what his agents spent today; FEELESS's key is not his money. Network faked throughout."""
import json
import time

import pytest

import spend_guard as sg
from test_bishop_swap import MP4, OR_KEY, _fake_ffmpeg, _setup, ck, du


def _row(cat, usd, at=None, funding='owner key', model='x/y'):
    return {'cat': cat, 'usd': usd, 'at': at or time.time(), 'funding': funding, 'model': model, 'provider': 'OpenRouter', 'status': 'provider reported'}


def test_the_cap_counts_his_agents_on_his_keys_today_only():
    now = time.time(); old = sg.day_start(now) - 60
    rows = [_row('a', 3.0), _row('b', 2.0), _row('a', 9.0, at=old), _row('a', 5.0, funding=sg.HOUSE), _row('them', 50.0)]
    assert sg.spent(rows, ['a', 'b'], sg.day_start(now)) == 5.0   # yesterday, FEELESS's key and someone else's agent never count
    sg.check(5.0, 0, 4.99, 10)                                      # fits
    with pytest.raises(sg.OverCap) as e:
        sg.check(5.0, 2.0, 3.5, 10)                                 # 5 spent + 2 making + 3.50 > 10
    assert 'before it cost anything' in str(e.value) and '$10.00 day cap' in str(e.value) and '$3.50' in str(e.value)
    with pytest.raises(sg.OverCap):
        sg.check(10.0, 0, 0, 10)                                    # a priced-after call (a model reply) stops once nothing is left
    sg.check(9.0, 0, 0, 10)
    v = sg.view(rows, ['a', 'b'], {'a': 'Fee', 'b': 'Happy'}, 10, 1.5, now)
    assert v['spentUsd'] == 5.0 and v['makingUsd'] == 1.5 and v['leftUsd'] == 3.5 and v['calls'] == 2 and not v['over']
    assert {r['agent'] for r in v['rows']} == {'Fee', 'Happy'} and v['rows'][0]['usd'] in (3.0, 2.0)


def test_he_names_the_cap_and_it_stays_in_range():
    assert sg.clean_cap('25') == 25.0
    for bad in ('0.5', '501', 'lots', None):
        with pytest.raises(ValueError):
            sg.clean_cap(bad)


def test_a_make_and_a_swap_are_refused_at_the_cap_before_anything_is_sent(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path, secs=9.5); _fake_ffmpeg(monkeypatch, fs, [])
    monkeypatch.setattr(fs, '_SPEND_HOLD', {})   # other tests queue swaps with the run faked: their holds stay in the shared table
    ran = []
    async def no_run(*a):
        ran.append(a)
    monkeypatch.setattr(fs, '_media_run', no_run)
    ck.put(store['cats']['g'], 'openrouter', OR_KEY, data_dir=tmp_path)
    assert post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True}).status_code == 200
    assert post(op='spend_cap', text='0.2').status_code == 400
    v = post(op='spend_cap', text='1').json()['spend']
    assert v['capUsd'] == 1.0 and v['spentUsd'] == 0
    (fs.DATA_DIR / 'model_receipts.jsonl').write_text(json.dumps(_row('g', 0.9)) + '\n')
    r = post(op='media_make', job=ws, text='swap him for bishop', tools={'swap': 'or-aleph-swap', 'clip': 'last'})
    assert r.status_code == 429 and 'day cap' in r.json()['detail'] and not ran   # $0.90 spent + a $2.66 swap > $1: nothing queued
    assert post(op='spend_cap', text='20').json()['spend']['leftUsd'] == 19.1
    r = post(op='media_make', job=ws, text='swap him for bishop', tools={'swap': 'or-aleph-swap', 'clip': 'last'})
    assert r.status_code == 200 and len({a[2] for a in ran}) == 1
    held = post(op='spend').json()['spend']
    assert held['makingUsd'] > 2 and held['spentUsd'] == 0.9   # the queued swap is held against the cap until its receipt lands
    assert 'spend' in post(op='media_models').json()


def test_a_page_build_stops_at_the_cap_before_the_next_paid_call(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path)
    cat = store['cats']['g']; ck.put(cat, 'openrouter', OR_KEY, data_dir=tmp_path); fs._save(store)
    monkeypatch.setattr(fs, '_SPEND_HOLD', {})
    asked = []
    async def think(*a, **k):
        asked.append(a[1]); return 'ok', 0.01, 'openrouter'
    monkeypatch.setattr(fs, '_think', think)
    fs.SPEND_CAPS_PATH.write_text(json.dumps({fs._spend_owner(cat)[0]: 1}))
    (fs.DATA_DIR / 'model_receipts.jsonl').write_text(json.dumps(_row('g', 1.0)) + '\n')
    import asyncio
    with pytest.raises(sg.OverCap):
        asyncio.run(fs._ws_ask(cat, 'anthropic/claude-sonnet-4.5', 's', 'u', 100))
    assert not asked
    assert asyncio.run(fs._ws_ask(cat, 'local/ossy', 's', 'u', 100))[0] == 'ok'                       # his own machine is free
    assert asyncio.run(fs._ws_ask(cat, 'nvidia/nemotron-nano-9b-v2:free', 's', 'u', 100))[0] == 'ok'  # so is a :free model


def test_the_comp_exam_on_his_openrouter_writes_receipts_and_stops_at_the_cap(tmp_path, monkeypatch):
    import comp_v2_exam as ex
    store = {'cats': {'fee': {'id': 'fee', 'ownerStaff': True, 'ownerWallet': 'W', 'apiKeys': {'openrouter': {'sealed': ck.seal('sk-or-test', 'fee'), 'at': 5}}},
                      'happy': {'id': 'happy', 'ownerWallet': 'W'}}}
    (tmp_path / 'feecats.json').write_text(json.dumps(store)); (tmp_path / 'spend_caps.json').write_text(json.dumps({'owner': 1}))
    led = tmp_path / 'model_receipts.jsonl'; led.write_text(json.dumps(_row('happy', 0.5)) + '\n')
    donor, check = ex.owner_spend(tmp_path / 'feecats.json', tmp_path)
    assert donor == 'fee'
    sent = []
    class R:
        def __init__(self, j): self._j = j
        def raise_for_status(self): pass
        def json(self): return self._j
    class H:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def post(self, url, json=None):
            sent.append((url, json)); return R({'id': 'gen-1', 'model': json['model'], 'choices': [{'message': {'content': 'won'}}], 'usage': {'cost': 0.3, 'total_tokens': 400}})
    import httpx
    monkeypatch.setattr(httpx, 'Client', H)
    monkeypatch.setattr(ex.cv, 'prompt_of', lambda r: 'q'); monkeypatch.setattr(ex.cv, 'answer_of', lambda t: t)
    with pytest.raises(sg.OverCap):
        ex.openrouter_answers([{}, {}, {}], 'sk-or-test', 'anthropic/claude-opus-5.5', donor, check, ledger=led)
    assert len(sent) == 2   # 0.5 + 0.3 = 0.8 < 1 → a second call; 1.1 ≥ 1 → stopped before the third
    url, body = sent[0]
    assert url == 'https://openrouter.ai/api/v1/chat/completions' and set(body) == {'model', 'max_tokens', 'messages'}   # no LM Studio switches
    rows = [json.loads(x) for x in led.read_text().splitlines()]
    assert [r['cat'] for r in rows[1:]] == ['fee', 'fee'] and all(r['funding'] == 'owner key' and r['for'] == 'COMP exam' for r in rows[1:])


def test_his_staff_agents_share_one_cap_wallet_or_not():
    cats = [{'id': 'fee', 'ownerStaff': True}, {'id': 'happy', 'ownerStaff': True, 'ownerWallet': 'W'}, {'id': 'side', 'ownerWallet': 'W'},
            {'id': 'user', 'ownerWallet': 'Z'}, {'id': 'lone'}]
    assert sg.group(cats, cats[0]) == ('owner', ['fee', 'happy', 'side'])   # Fee has no wallet but spends the owner's key
    assert sg.group(cats, cats[2]) == ('W', ['happy', 'side']) and sg.group(cats, cats[3]) == ('Z', ['user']) and sg.group(cats, cats[4]) == ('lone', ['lone'])


def test_a_short_aleph_clip_is_priced_at_its_minimum():
    import media_gen as mg
    assert mg.v2v_cost('or-aleph-swap', 1.5) == 0.56 and mg.v2v_cost('or-aleph-swap', 10) == 2.8


def test_a_hold_is_let_go_when_its_folder_is_gone(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path)
    fs._SPEND_HOLD['mgone'] = ('owner', 2.8)
    fs._media_set('g', 'wnope', 'mgone', None, status='failed', why='x')
    assert 'mgone' not in fs._SPEND_HOLD


def test_any_route_at_the_cap_answers_429_in_plain_words(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path)
    async def over(*a, **k):
        raise sg.OverCap('Stopped before it cost anything: your $1.00 day cap.')
    monkeypatch.setattr(fs, '_media_swap', over)
    r = post(op='media_make', job=ws, text='x', tools={'swap': 'auto'})
    assert r.status_code == 429 and 'day cap' in r.json()['detail']
