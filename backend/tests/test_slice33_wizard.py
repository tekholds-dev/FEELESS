"""🧭 Slice 33 (owner 2026-11-20 night): the 3-step start wizard replaces the long confirm text before a PoC, PoEco or PoStatic job.
Every choice is wired: the click is saved on the job, used by the engine (the minds' prompt, the kits, the research pass) and shown in the
filed proof's record. Every network call and every mind is faked here."""
import asyncio
import json

import pytest

import start_wizard as wz

KITS = ['k1', 'k2', 'k3', 'k4']
OK = {'direction': {'text': 'Lead with the fee data', 'pitch': 'Write the article', 'approved': True}, 'kits': ['k1'], 'start': 'fresh', 'research': {'by': 'comp'}}
REFS = [{'title': 'fee-charts', 'url': 'https://github.com/a/fee-charts', 'why': 'live fee charts', 'source': 'GitHub', 'score': 90, 'open': True},
        {'title': 'walled', 'url': 'https://x.test/w', 'why': '', 'source': 'HN', 'score': 5, 'open': False}]


# ── the choices: checked against what is on offer ──
def test_clean_keeps_the_owners_choices_and_refuses_what_is_not_on_offer():
    w = wz.clean('poe', OK, KITS, ['e1'], now=5)
    assert w == {'kind': 'poe', 'direction': {'text': 'Lead with the fee data', 'edited': True, 'approved': True}, 'kits': ['k1'], 'kitMode': 'mine',
                 'start': 'fresh', 'research': {'by': 'comp'}, 'at': 5}
    assert not wz.clean('pos', {**OK, 'direction': {'text': 'same', 'pitch': 'same', 'approved': True}}, KITS)['direction']['edited']   # approved as pitched
    assert wz.clean('poc', {**OK, 'kits': []}, KITS)['kitMode'] == 'auto'   # no kits picked: the agent picks, as before
    assert wz.clean('poe', {**OK, 'start': 'e1'}, KITS, ['e1'])['start'] == 'e1'
    for bad, why in [({**OK, 'direction': {'text': 'x'}}, 'Approve'), ({**OK, 'kits': ['zz']}, 'Not a kit'), ({**OK, 'kits': KITS}, 'up to 3'),
                     ({**OK, 'start': 'nope'}, 'Start fresh'), ({**OK, 'research': {'by': 'gpt'}}, 'who researches')]:
        with pytest.raises(ValueError, match=why):
            wz.clean('poe', bad, KITS, ['e1'])
    with pytest.raises(ValueError):
        wz.clean('pow', OK, KITS)   # PoW / PoP / PoB start as they did


def test_the_kits_line_and_record_carry_every_choice():
    w = wz.clean('poe', OK, KITS)
    assert wz.kits_for('poe', ['a', 'b']) == ['a', 'b']   # no wizard in this task: the agent's picks
    tok = wz.CTX.set(w)
    try:
        assert wz.kits_for('poe', ['a', 'b']) == ['k1'] and wz.kits_for('poc', ['a']) == ['a']   # only its own kind
    finally:
        wz.CTX.reset(tok)
    found = {'by': 'comp', 'ok': True, 'why': '1 found', 'refs': [REFS[0]], 'usd': 0.0, 'q': 'fees'}
    base = {'n': 4, 'topic': 'fee article', 'kits': ['k2']}
    t = wz.line(w, found, base)
    assert 'START WIZARD' in t and 'Lead with the fee data' in t and '(his own edit)' in t and 'k1' in t and '#4: fee article' in t and 'https://github.com/a/fee-charts' in t
    r = wz.record(w, found, base)
    assert r['direction'] == 'Lead with the fee data' and r['edited'] and r['kits'] == ['k1'] and r['startN'] == 4 and r['research']['refs'] == ['fee-charts']
    json.dumps(r)


def test_research_comp_reads_free_ossy_or_g4_write_the_search_and_a_dead_local_mind_is_never_swapped():
    seen = []

    async def refs(http, q, deep):
        seen.append((q, deep)); return REFS

    async def ask(model, sys_, user_, tokens):
        seen.append(model); asked.append(user_); return 'solana fee chart widgets\nextra', 0.0, False
    asked = []

    async def down(model, *a):
        seen.append(model); raise TimeoutError

    run = lambda w, a=None: asyncio.run(wz.research(w, 'Lead with the fee data', None, refs, a))
    m = run({'research': {'by': 'minds'}})
    assert m['ok'] and m['refs'] == [] and seen == []   # its minds search as they work: nothing extra runs
    c = run({'research': {'by': 'comp'}})
    assert c['ok'] and [x['title'] for x in c['refs']] == ['fee-charts'] and seen == [('Lead with the fee data', True)] and c['usd'] == 0   # walled pages left out
    seen.clear(); g = run({'research': {'by': 'g4'}}, ask)
    assert seen == ['local/g4', ('solana fee chart widgets', True)] and g['q'] == 'solana fee chart widgets' and g['ok']
    seen.clear(); asked.clear(); run({'research': {'by': 'g4'}, 'direction': {'text': 'Make it dark'}}, ask)
    assert asked == ["The job: Lead with the fee data\nThe owner's direction: Make it dark"]   # the job is the search; his direction steers it
    seen.clear(); o = run({'research': {'by': 'ossy'}}, down)
    assert seen == ['local/ossy'] and not o['ok'] and 'No other model stands in' in o['why'] and o['refs'] == []   # no fallback, no search


def test_options_show_the_pitch_kits_starts_minds_and_cost():
    rows = [{'id': 'e1', 'n': 1, 'topic': 'a', 'cost': 0.02}, {'id': 'e2', 'n': 2, 'topic': 'b', 'cost': 0.04, 'graded': {'result': 'paid'}}]
    o = wz.options('poe', rows, ['qwen/a', 'openai/b'], [{'id': 'k1', 'name': 'Bid Desk', 'what': 'bids'}], ['k1'], 'mine', 'Brief', 'Pay $400', ['fits writing'])
    assert o['label'] == 'PoEco' and o['pitch'] == ['fits writing'] and o['kits'][0]['name'] == 'Bid Desk' and o['picks'] == ['k1']
    assert [s['id'] for s in o['starts']] == ['e2', 'e1'] and o['starts'][0]['good'] and o['minds'] == ['a', 'b'] and o['cost']['usd'] == 0.03 and o['cost']['n'] == 2
    assert {r['by'] for r in o['research']} == {'minds', 'comp', 'ossy', 'g4'}


# ── PoEco end to end: click → saved → used by the engine → shown in the record ──
from test_slice16_earn import FakeHttp, GOOD  # noqa: E402


@pytest.fixture
def eco(monkeypatch):
    import feecat_service as fs
    cat = {'id': 'c1', 'name': "Happy's", 'handle': 'happy-assistant', 'chat': [], 'brainsCfg': {'brains': ['qwen/a', 'openai/b'], 'credit': 1.0}, 'poeFolders': []}
    store = {'cats': {'c1': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None)
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **k: FakeHttp())
    seen, refs_q = [], []

    async def ask(cat_, m, sys_, user_, tokens):
        seen.append((m, sys_)); return json.dumps(GOOD if m == 'qwen/a' else {**GOOD, 'plan': ['one step']}), 0.004, False

    async def refs(http, q, deep):
        refs_q.append(q); return REFS
    monkeypatch.setattr(fs, '_ws_ask', ask); monkeypatch.setattr(fs._tools, 'build_refs', refs)
    fs._fc_earn._BUSY.clear(); fs._TEST_ON.clear()
    return fs, cat, seen, refs_q


def _run(fs, **kw):
    async def go():
        out = await fs._cat_work('c1', fs.WorkPayload(session='s', **kw))
        for _ in range(400):
            if 'c1' not in fs._fc_earn._BUSY:
                break
            await asyncio.sleep(0.01)
        return out
    return asyncio.run(go())


def test_poeco_wizard_choices_reach_both_minds_and_land_on_the_filed_record(eco):
    fs, cat, seen, refs_q = eco
    best = _run(fs, op='earn_find')['board']['best'][0]
    o = _run(fs, op='wizard_opts', text='poe', job=best['id'])['wizard']
    assert o['label'] == 'PoEco' and best['title'] in o['brief'] and o['pitch'] and o['minds'] == ['a', 'b'] and o['kits']
    kit = o['kits'][0]
    with pytest.raises(fs.HTTPException):   # nothing starts unless the direction is approved
        _run(fs, op='earn_bid', text=best['id'], tools={'wizard': {**OK, 'kits': [kit['id']], 'direction': {'text': 'x'}}})
    _run(fs, op='earn_bid', text=best['id'], tools={'wizard': {**OK, 'kits': [kit['id']], 'direction': {'text': 'Quote $380 and lead with real fee numbers', 'pitch': 'p', 'approved': True}}})
    f = cat['poeFolders'][-1]
    assert len(seen) == 2 and all('Quote $380 and lead with real fee numbers' in s and 'https://github.com/a/fee-charts' in s for _m, s in seen)   # used: both minds read it
    assert refs_q == [f"{best['title']} {best.get('cat') or ''}".strip()]   # COMP searched on the JOB (the listing), never his direction sentence (TEST #3 found notes apps for it)
    assert f['kits'] == [kit['name']]   # used: the job read the kit he picked, not the agent's usual pick
    w = f['wizard']
    assert w['direction'].startswith('Quote $380') and w['edited'] and w['kits'] == [kit['id']] and w['research']['by'] == 'comp' and w['research']['refs'] == ['fee-charts']


# ── PoStatic: the wizard replaces the plan text; the build reads it once and files it ──
def test_postatic_wizard_on_the_plan_is_saved_used_by_the_build_and_filed(monkeypatch, tmp_path):
    from test_slice3_postatic import POOLS, _folder, _server
    fs, c, store = _server(monkeypatch, tmp_path); ws = _folder(fs, c, 'pools')
    doc = fs._ws_load('g', ws); doc['plan'] = {'ask': 'a pool page', 'to': 'a', 'plan': {'summary': 'A turnover board', 'steps': ['chart']}, 'by': 'Mind A', 'approved': False}
    fs._ws_save('g', doc)
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    o = post('wizard_opts', text='pos', job=ws).json()['wizard']
    assert o['brief'] == 'a pool page' and o['pitch'][0] == 'Mind A: A turnover board' and o['kits']
    kit = next(k['id'] for k in o['kits'] if k['id'] != 'three')
    started = []
    monkeypatch.setattr(fs, '_ws_start', lambda *a: started.append(a)); store['cats']['g']['brainsCfg']['credit'] = 1.0
    r = post('ws_approve', job=ws, tools={'wizard': {'direction': {'text': 'Make the chart the hero', 'pitch': 'A turnover board', 'approved': True}, 'kits': [kit], 'start': 'fresh', 'research': {'by': 'comp'}}})
    assert r.status_code == 200, r.text
    d = fs._ws_load('g', ws)
    assert d['wizard']['kits'] == [kit] and d['plan']['approved'] and 'Make the chart the hero' in started[0][3]   # saved, and his edit is the ask

    seen = []

    async def page(cat, model, sys_, user_, tokens, on_part=None):
        seen.append(sys_ + user_); return POOLS, 0.0, False

    async def refs(http, q, deep):
        return REFS

    async def phone(html, chromium=None, http=None, **k):
        return {'ran': True, 'loads': True, 'fits': True, 'overlaps': [], 'deadLinks': [], 'errors': []}
    monkeypatch.setattr(fs, '_ws_page', page); monkeypatch.setattr(fs._tools, 'build_refs', refs); monkeypatch.setattr(fs._ps_hidden, 'browser', phone)
    asyncio.run(fs._ws_run('g', ws, 'a', started[0][3], None))
    assert any('START WIZARD' in s and 'fee-charts' in s and kit in s for s in seen)   # used by the build
    fs._ws_pass(store); f = store['cats']['g']['psFolders'][-1]
    assert f['wizard']['kits'] == [kit] and f['wizard']['research']['refs'] == ['fee-charts'] and f['wizard']['direction'] == 'Make the chart the hero'
    assert fs._ws_load('g', ws)['wizard']['filed']   # a later edit of the page does not carry it again
