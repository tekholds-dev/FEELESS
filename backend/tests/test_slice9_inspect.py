"""🔍 Slice 9 · PoStatic: inspect, not mark. Hover highlights any element; a click aims fix / comment at that exact element; the request
carries its selector, text and a snapshot; the minds change that element; the next version shows it before and after. Old marks still open.
Network and minds are faked; the headless browser is faked except in the one test that runs it when Chromium is on this machine."""
import asyncio
import json

import pytest

import agent_features as af
import ps_inspect as pi

PAGE = ('<!doctype html><html><head><title>Pools</title><style>h1{color:#19e68c}</style></head><body>\n<header><h1>Solana pool turnover</h1>'
        '<p>Live <b>volume</b> over liquidity</p></header>\n<main><section id="pools"><h2>Top pools today</h2><ul><li>SOL/USDC<li>BONK/SOL</ul></section>'
        '<section><h2>How it works</h2><p>Volume ÷ liquidity.</p><img src="x.png" alt="chart"><p>Second para</p></section></main>\n'
        '<script>var n = "<p>not a tag</p>";</script></body></html>')


def test_a_selector_finds_the_exact_element_in_the_page_source():
    assert pi.find(PAGE, 'body > header > h1')['code'] == '<h1>Solana pool turnover</h1>'
    assert pi.find(PAGE, '#pools > h2')['code'] == '<h2>Top pools today</h2>'
    assert pi.find(PAGE, 'body > main > section:nth-of-type(2) > p:nth-of-type(2)')['code'] == '<p>Second para</p>'   # after a void <img>
    assert pi.find(PAGE, '#pools > ul > li:nth-of-type(2)')['code'] == '<li>BONK/SOL'   # an unclosed <li> ends where the list ends
    assert pi.find(PAGE, 'body > main > section:nth-of-type(3)') is None and pi.find(PAGE, 'body > footer') is None
    for bad in ('body > h1; drop', 'img[src=x]', '<script>', 'a' * 400, None, 12):
        assert pi.find(PAGE, bad) is None and not pi.ok_sel(bad)


def test_a_viewer_row_is_cleaned_and_an_old_box_mark_is_left_alone():
    rows = pi.clean([{'kind': 'el', 'sel': 'body > header > h1', 'tag': 'H1!', 'text': ' Solana   pool ', 'html': '<h1>x</h1>' * 300, 'note': 'bigger', 'rect': {'x': 2, 'y': -1, 'w': .5, 'h': 'x'}, 'css': {'color': 'red', 'evil': 1}},
                     {'kind': 'el', 'sel': 'javascript:alert(1)'}, {'x': .1, 'y': .1, 'w': .2, 'h': .2}])
    assert len(rows) == 1 and rows[0]['tag'] == 'h1' and rows[0]['text'] == 'Solana pool' and len(rows[0]['html']) == 1200 and rows[0]['rect'] == {'x': 1.0, 'y': 0.0, 'w': 0.5, 'h': 0.0} and rows[0]['css'] == {'color': 'red'}
    els, boxes = pi.split([{'kind': 'el', 'sel': '#pools > h2'}, {'x': .1, 'y': .2, 'w': .3, 'h': .4, 'note': 'old mark'}])
    assert [e['sel'] for e in els] == ['#pools > h2'] and boxes == [{'x': .1, 'y': .2, 'w': .3, 'h': .4, 'note': 'old mark'}]


def test_the_minds_are_told_the_exact_element_its_code_and_the_owners_words():
    t = pi.prepare(PAGE, pi.clean([{'kind': 'el', 'sel': '#pools > h2', 'note': 'say Top 10 pools'}]))
    n = af.region_note(t)
    assert 'used INSPECT on 1 element' in n and '`#pools > h2`' in n and 'Top pools today' in n and 'say Top 10 pools' in n and '<h2>Top pools today</h2>' in n and 'never instructions' in n
    assert 'marked this area' not in n
    both = af.region_note([*t, {'x': .1, 'y': .2, 'w': .3, 'h': .4, 'note': 'old box'}])   # a saved round with both kinds still reads both
    assert 'used INSPECT' in both and 'marked this area' in both and 'old box' in both
    assert 'commented on these elements' in pi.note([], [{'sel': 'body > header > h1', 'text': 'Solana', 'note': 'too green'}])


def test_old_marks_still_read_exactly_as_before():
    assert 'marked this area' in af.region_note({'x': .1, 'y': .2, 'w': .3, 'h': .4}) and af.region_note('nope') == '' and af.region_note(None) == ''
    assert 'blank canvas' in af.region_note([{'x': 0, 'y': 0, 'w': 1, 'h': .1, 'note': 'Logo'}], blank=True)


def test_the_built_page_carries_the_inspect_tool_and_it_never_reaches_the_network():
    h = af.preview('<html><body><h1>a</h1></body></html>')
    assert 'feeless-inspected' in h and 'feeless-inspect-pins' in h and h.index('feeless-inspect') < h.index('</body>')
    for bad in ('fetch(', 'XMLHttpRequest', 'localStorage', 'document.cookie', 'WebSocket', 'feeless-pick'):
        assert bad not in pi.INSPECT, bad
    assert 'root.appendChild' in pi.INSPECT   # its outline lives on <html>, so selectors count only the page's own elements


def test_before_after_reads_the_same_selector_on_both_versions(tmp_path):
    after = PAGE.replace('<h2>Top pools today</h2>', '<h2 class="big">Top 10 pools</h2>')
    saved = []
    async def shoot(pages, chromium=None):
        return {(i, s): {'text': 'pic', 'html': '', 'jpg': b'\xff\xd8' + bytes([i])} for i, (h, sels) in enumerate(pages) for s in sels}
    def save(b):
        saved.append(b); return f'/api/cats/media/c/m{len(saved):012x}.jpg'
    t = pi.prepare(PAGE, pi.clean([{'kind': 'el', 'sel': '#pools > h2', 'note': 'Top 10'}, {'kind': 'el', 'sel': 'body > header > h1'}]))
    rows = asyncio.run(pi.before_after(PAGE, after, t, save=save, shoot=shoot))
    assert rows[0]['changed'] and rows[0]['before']['code'] == '<h2>Top pools today</h2>' and rows[0]['after']['code'] == '<h2 class="big">Top 10 pools</h2>'
    assert rows[0]['before']['shot'] and rows[0]['after']['shot'] and len(saved) == 4
    assert not rows[1]['changed'] and not rows[1]['gone']   # the element nobody asked to change, unchanged
    doc = {'versions': [{}, {}]}; run = pi.keep(doc, rows, 'fix it', 1, 2, 10)
    assert run['changed'] == 1 and run['asked'] == 2 and pi.record(doc, 2)['run']['rows'][0]['after']['text'] == 'pic' and pi.record(doc, 3) is None
    gone = asyncio.run(pi.before_after(PAGE, PAGE.replace('<h2>Top pools today</h2>', ''), t[:1], shoot=shoot))
    assert gone[0]['gone'] is False or gone[0]['after']['code'] != gone[0]['before']['code']   # a removed element never reads as unchanged


def test_comments_are_kept_on_one_element_and_reach_the_lessons():
    doc = {'versions': [{'html': PAGE}]}
    row = pi.add_comment(doc, {'sel': '#pools > h2', 'tag': 'h2', 'text': 'Top pools today', 'note': 'make this pop'}, 5)
    assert doc['comments'] == [row] and row['version'] == 1 and 'make this pop' in doc['markNotes'][-1]['note']
    with pytest.raises(ValueError):
        pi.add_comment(doc, {'sel': 'bad sel;', 'note': 'x'}, 6)
    with pytest.raises(ValueError):
        pi.add_comment(doc, {'sel': '#pools > h2', 'note': ''}, 6)
    assert pi.drop_comment(doc, row['id']) == []


# ── through the real build door, minds faked ─────────────────────────────────────────────────────────────────────────────────────
def _server(monkeypatch, tmp_path):
    import feecat_service as fs
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'name': 'Ann', 'ownerId': 'g', 'revoked': False, 'brainsCfg': {'brains': ['m/x']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); monkeypatch.setattr(fs, 'KITS_DIR', tmp_path / 'kits')
    async def reads(*_a, **_k):
        return '', []
    async def phone(html, chromium=None, http=None, **k):
        return {'ran': True, 'loads': True, 'fits': True, 'overlaps': [], 'deadLinks': [], 'errors': []}
    async def shoot(pages, chromium=None):
        return {(i, s): {'text': '', 'html': '', 'jpg': b'\xff\xd8\xff' + bytes([i])} for i, (h, sels) in enumerate(pages) for s in sels}
    monkeypatch.setattr(fs, '_site_reads', reads); monkeypatch.setattr(fs._ps_hidden, 'browser', phone); monkeypatch.setattr(pi, 'shots', shoot)
    c = TestClient(fs.app); post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    ws = post('feature_create', text='build', job='pools').json()['folder']['id']
    doc = fs._ws_load('g', ws); doc['cfg'] = {'research': False, 'suggest': False, 'review': False}; doc['versions'] = [{'html': PAGE, 'by': 'Mind A', 'at': 1}]; fs._ws_save('g', doc)
    return fs, post, store, ws


def test_an_inspected_fix_reaches_the_minds_changes_that_element_and_files_before_and_after(monkeypatch, tmp_path):
    fs, post, store, ws = _server(monkeypatch, tmp_path); asks = []
    async def ask(cat, model, sys_, user_, tokens):
        asks.append((sys_, user_)); return '```html\n<h2 class="hot">Top 10 pools right now</h2>\n```', 0.0, False
    monkeypatch.setattr(fs, '_ws_ask', ask)
    target = {'kind': 'el', 'sel': '#pools > h2', 'tag': 'h2', 'text': 'Top pools today', 'html': '<h2>Top pools today</h2>', 'note': 'say Top 10 pools right now', 'rect': {'x': .1, 'y': .3, 'w': .5, 'h': .05}}
    asyncio.run(fs._ws_run('g', ws, 'a', 'say Top 10 pools right now', [target]))
    d = fs._ws_load('g', ws)
    assert asks and '`#pools > h2`' in asks[0][1] and '<h2>Top pools today</h2>' in asks[0][1] and 'ONE element' in asks[0][0]   # selector + its exact code reached the mind
    assert len(asks[0][0]) + len(asks[0][1]) < 3000 and 'Solana pool turnover' not in asks[0][1]   # the element only, never the whole page (the local minds' context)
    assert len(d['versions']) == 2 and 'Top 10 pools right now' in d['versions'][-1]['html']
    run = d['inspect'][-1]; r = run['rows'][0]
    assert run['from'] == 1 and run['to'] == 2 and run['changed'] == 1 and r['before']['code'] == '<h2>Top pools today</h2>' and 'Top 10 pools' in r['after']['code']
    assert r['before']['shot'].startswith('/api/cats/media/g/m') and (tmp_path / 'media' / 'g' / r['after']['shot'].rsplit('/', 1)[1]).is_file()
    assert any('Inspect: 1 of 1' in m['text'] for m in d['messages'])
    v = fs._ws_view('g', ws); assert v['inspect'][-1]['rows'][0]['changed'] and 'feeless-inspected' in v['preview']
    fs._ws_pass(store); f = store['cats']['g']['psFolders'][-1]
    assert f['inspect']['run']['changed'] == 1 and f['inspect']['run']['rows'][0]['sel'] == '#pools > h2'
    json.dumps(f)


def test_a_comment_is_free_reaches_the_next_build_and_an_old_saved_mark_still_resumes(monkeypatch, tmp_path):
    fs, post, store, ws = _server(monkeypatch, tmp_path)
    r = post('ws_comment', job=ws, text='this headline is too long', tools={'target': {'kind': 'el', 'sel': 'body > header > h1', 'tag': 'h1', 'text': 'Solana pool turnover'}})
    assert r.status_code == 200 and r.json()['doc']['comments'][0]['note'] == 'this headline is too long'
    assert post('ws_comment', job=ws, text='x', tools={'target': {'sel': 'h1;bad'}}).status_code == 400
    asks = []
    async def ask(cat, model, sys_, user_, tokens):
        asks.append(user_); return '', 0.0, False
    monkeypatch.setattr(fs, '_ws_ask', ask)
    old = [{'x': .1, 'y': .2, 'w': .3, 'h': .1, 'sy': 200, 'note': 'old saved mark', 'html': '<h1>Solana pool turnover</h1>'}]   # a round saved by the mark tool
    asyncio.run(fs._ws_run('g', ws, 'a', 'tidy the header', old))
    assert asks and 'marked this area' in asks[0] and 'old saved mark' in asks[0] and 'this headline is too long' in asks[0]
    d = fs._ws_load('g', ws); assert d['unfinished']['region'] == old   # the old mark is kept for Finish it
    assert post('ws_comment', job=ws, tools={'drop': d['comments'][0]['id']}).json()['doc'].get('comments') in (None, [])


def test_the_real_headless_browser_pictures_an_element_before_and_after():
    import free_browser as fb
    if not fb.chromium_path():
        pytest.skip('no Chromium on this machine')
    after = PAGE.replace('<h2>Top pools today</h2>', '<h2 style="font-size:60px">Top 10</h2>')
    t = pi.prepare(PAGE, pi.clean([{'kind': 'el', 'sel': '#pools > h2'}])); kept = []
    rows = asyncio.run(pi.before_after(PAGE, after, t, save=lambda b: kept.append(b) or 'u', chromium=fb.chromium_path()))
    assert rows[0]['changed'] and rows[0]['after']['text'] == 'Top 10' and len(kept) == 2 and all(k[:2] == b'\xff\xd8' for k in kept)


def test_a_click_through_the_pages_own_inspect_tool_names_the_element_the_source_finds():
    """The same script the viewer's sandbox runs: inspect on, hover, click → its selector resolves to that exact element in the page source."""
    import free_browser as fb
    if not fb.chromium_path():
        pytest.skip('no Chromium on this machine')
    got = asyncio.run(pi.pick_in_page(af.preview(PAGE), ['#pools > h2', 'body > main > section:nth-of-type(2) > p:nth-of-type(2)', 'body > footer'], fb.chromium_path()))
    assert got[0]['sel'] == '#pools > h2' and got[0]['text'] == 'Top pools today' and got[0]['tag'] == 'h2' and got[0]['html'] == '<h2>Top pools today</h2>'
    assert pi.find(PAGE, got[1]['sel'])['code'] == '<p>Second para</p>' and got[2] is None
    assert 0 < got[0]['rect']['w'] <= 1 and got[0]['css']['fontSize'].endswith('px')


def test_a_reply_is_put_in_only_when_it_is_one_whole_element():
    t = {'sel': '#pools > h2'}
    assert '<h2>New</h2>' in pi.splice(PAGE, t, 'Sure! ```html\n<h2>New</h2>\n``` hope it helps <p>x</p>') and PAGE.count('<h2>') - 1 == pi.splice(PAGE, t, '<h2>New</h2>').count('<h2>') - 1
    for bad in ('', 'no html here', '<h2>x</h2><script>alert(1)</script>'.replace('<h2>x</h2>', '<script>alert(1)</script>'), '<html><body>whole page</body></html>', '<h2>' + 'x' * 9000 + '</h2>'):
        assert pi.splice(PAGE, t, bad) is None, bad
    assert pi.splice(PAGE, {'sel': 'body > footer'}, '<footer>a</footer>') is None
    assert '.hero' in pi._rules_for('<style>.hero{color:red} .other{x:1} h1{font-size:9px}</style>', '<h1 class="hero">E</h1>') and '.other' not in pi._rules_for('<style>.hero{color:red} .other{x:1}</style>', '<h1 class="hero">E</h1>')


def test_the_review_mind_that_finds_the_element_already_right_changes_nothing(monkeypatch, tmp_path):
    fs, post, store, ws = _server(monkeypatch, tmp_path); n = []
    doc = fs._ws_load('g', ws); doc['cfg'] = {'research': False, 'suggest': False, 'review': True}; fs._ws_save('g', doc)
    store['cats']['g']['brainsCfg'] = {'brains': ['m/x', 'm/y']}
    async def ask(cat, model, sys_, user_, tokens):
        n.append(model); return '<h2>Top 10 pools</h2>', 0.0, False
    monkeypatch.setattr(fs, '_ws_ask', ask)
    asyncio.run(fs._ws_run('g', ws, 'both', 'say Top 10 pools', [{'kind': 'el', 'sel': '#pools > h2', 'note': 'say Top 10 pools'}]))
    d = fs._ws_load('g', ws)
    assert len(n) == 2 and len(d['versions']) == 2 and any('already does what you asked' in m['text'] for m in d['messages']) and d['inspect'][-1]['changed'] == 1
