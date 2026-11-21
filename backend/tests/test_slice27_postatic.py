"""💻 Slice 27 · PoStatic: inspect EVERYTHING (owner 2026-11-20: "inspect needs to be able to hover over anything in static, even the 3D stuff")
and the $0 page tools before any mind is paid. Minds are faked; the in-page inspect script runs in the real headless browser when this machine
has one, and three.js is served from the repo's own node_modules (no network)."""
import asyncio
import json
from pathlib import Path

import pytest

import agent_features as af
import ps_inspect as pi
from test_slice9_inspect import PAGE, _server

THREE = Path(__file__).resolve().parents[2] / 'frontend' / 'node_modules' / 'three' / 'build'
CDN = 'https://cdn.jsdelivr.net/npm/three@0.186.1/build/'


# ── the $0 page tools ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_simple_look_ask_is_read_as_css_and_anything_more_goes_to_a_mind():
    assert pi.style_of('make it red') == {'color': 'red'} and pi.style_of('Turn the text #19e68c!') == {'color': '#19e68c'}
    assert pi.style_of('bigger and bold', {'fontSize': '20px'}) == {'font-size': '25px', 'font-weight': '700'}
    assert pi.style_of('smaller') == {'font-size': '0.8em'} and pi.style_of('center it') == {'text-align': 'center'}
    assert pi.style_of('background to navy') == {'background-color': 'navy'}
    for more in ('make it red and add a chart', 'rewrite this headline', 'fix this h2', '', 'red ' * 40):
        assert pi.style_of(more) is None, more


def test_a_text_edit_lands_on_the_exact_words_never_inside_a_script():
    page = '<body><h1>Hi &amp; bye</h1><div id="m">Loose words <b>bold</b> tail</div><script>var s="Hi & bye"</script></body>'
    out = pi.edit_text(page, {'sel': 'body > h1', 'text': 'Hi & bye', 'edit': 'Hello <you>'})
    assert '<h1>Hello &lt;you&gt;</h1>' in out and 'var s="Hi & bye"' in out
    assert '>Loose text <b>' in pi.edit_text(page, {'sel': '#m', 'text': 'Loose words', 'edit': 'Loose text'})   # a text node beside an element
    assert pi.edit_text(page, {'sel': 'body > h1', 'text': 'not on the page', 'edit': 'x'}) is None
    assert pi.edit_text(page, {'sel': 'body > h1', 'text': 'Hi & bye', 'edit': 'Hi & bye'}) is None   # no change, no version


def test_inline_style_merges_into_its_own_tag():
    page = '<body><p style="margin:0">a</p><img src="x.png"/></body>'
    assert '<p style="margin:0;color:red">a</p>' in pi.add_style(page, {'sel': 'body > p'}, {'color': 'red'})
    assert '<img src="x.png" style="text-align:center"/>' in pi.add_style(page, {'sel': 'body > img'}, {'text-align': 'center'})
    up = '<body><nav><a href="#top" style="text-transform:uppercase">The Collective</a></nav></body>'   # the pick reads THE COLLECTIVE (as shown)
    assert '<a href="#top" style="text-transform:uppercase">Lore &amp; legends</a>' in pi.edit_text(up, {'sel': 'body > nav > a', 'text': 'THE COLLECTIVE', 'edit': 'Lore & legends'})
    sq = "<body><p style='margin:0'>a</p></body>"   # a single-quoted style merges too: a second style attribute would be ignored
    assert "<p style='margin:0;color:red'>a</p>" in pi.add_style(sq, {'sel': 'body > p'}, {'color': 'red'})
    p, said, left = pi.quick_pass(PAGE, [{'sel': '#pools > h2', 'tag': 'h2'}, {'sel': 'body > header > h1', 'tag': 'h1', 'note': 'write a better headline'}], 'make it red')
    assert '<h2 style="color:red">Top pools today</h2>' in p and said == ['h2: set color red'] and [t['tag'] for t in left] == ['h1']
    assert pi.quick(PAGE, {'sel': 'body > canvas', 'node': 'three'}, 'make it red') == (None, '')   # a 3D object is never a tag style


def test_picks_carry_their_kind_and_the_minds_read_each_one():
    rows = pi.clean([{'sel': 'body > canvas', 'node': 'three', 'three': {'name': 'Hero <cube>', 'type': 'Mesh', 'geometry': 'BoxGeometry', 'material': 'MeshStandardMaterial', 'color': '#19e68c', 'path': 'Group > Hero cube'}},
                     {'sel': 'body > canvas', 'node': 'canvas', 'part': {'x': 0.66, 'y': 0, 'w': 0.33, 'h': 9}}, {'sel': '#m', 'node': 'text', 'text': 'Loose words', 'edit': 'New\nwords'}, {'sel': 'body > p', 'node': 'evil'}])
    assert rows[0]['three']['name'] == 'Hero cube' and rows[1]['part'] == {'x': 0.66, 'y': 0.0, 'w': 0.33, 'h': 1.0} and rows[2]['edit'] == 'New words' and 'node' not in rows[3]
    n = pi.note(rows)
    assert "3D object named 'Hero cube' (Mesh, BoxGeometry, MeshStandardMaterial, #19e68c)" in n and 'script code that creates or moves that object' in n
    assert 'from 66% to 99% across' in n and 'The text "Loose words" directly inside' in n
    page = '<body><canvas></canvas><script type="module">import * as T from "three";\nconst g = new T.BoxGeometry(1,1,1);\nconst m = new T.Mesh(g, mat);\nm.name = "Hero cube";\nscene.add(m);</script></body>'
    t = pi.prepare(page, pi.clean([{'sel': 'body > canvas', 'node': 'three', 'three': {'name': 'Hero cube', 'geometry': 'BoxGeometry'}}]))[0]
    assert 'm.name = "Hero cube"' in t['source'] and 'BoxGeometry' in t['source']   # the minds get the script that makes it, not the <canvas> tag


def test_the_three_hook_rides_only_a_page_whose_importmap_names_three():
    with3 = f'<html><head><script type="importmap">{{"imports":{{"three": "{CDN}three.module.js"}}}}</script></head><body><canvas></canvas></body></html>'
    assert pi.THREE_HOOK in af.preview(with3) and pi.THREE_HOOK not in af.preview(PAGE)
    assert af.preview(with3).count(pi.THREE_HOOK) == 1 and pi.with_hook(pi.with_hook(with3)).count(pi.THREE_HOOK) == 1
    for bad in ('fetch(', 'localStorage', 'document.cookie', 'XMLHttpRequest', 'WebSocket'):
        assert bad not in pi.INSPECT and bad not in pi.THREE_HOOK


# ── through the real build door, minds faked ─────────────────────────────────────────────────────────────────────────────────────
def test_a_look_ask_on_a_pick_files_a_new_version_and_no_mind_is_paid(monkeypatch, tmp_path):
    fs, post, store, ws = _server(monkeypatch, tmp_path)
    async def ask(*_a, **_k):
        raise AssertionError('no mind may be called for a page-tools edit')
    monkeypatch.setattr(fs, '_ws_ask', ask); monkeypatch.setattr(fs, '_ws_page', ask)
    asyncio.run(fs._ws_run('g', ws, 'a', 'make it red', [{'kind': 'el', 'sel': '#pools > h2', 'tag': 'h2', 'text': 'Top pools today'}]))
    asyncio.run(fs._ws_run('g', ws, 'a', 'Change this text', [{'kind': 'el', 'sel': 'body > header > h1', 'node': 'text', 'text': 'Solana pool turnover', 'edit': 'Pool turnover, live'}]))
    d = fs._ws_load('g', ws)
    assert len(d['versions']) == 3 and '<h2 style="color:red">Top pools today</h2>' in d['versions'][1]['html'] and '<h1>Pool turnover, live</h1>' in d['versions'][2]['html']
    assert sum('Page tools, $0 (no mind called)' in m['text'] for m in d['messages']) == 2 and d['lastCost'] == 0
    assert d['inspect'][-1]['changed'] == 1   # before / after still filed for the picked element


def test_a_mixed_round_pays_a_mind_only_for_what_the_tools_cannot_do_and_sends_it_the_stash(monkeypatch, tmp_path):
    fs, post, store, ws = _server(monkeypatch, tmp_path); asks = []
    async def ask(cat, model, sys_, user_, tokens):
        asks.append((sys_, user_)); return '<h1>Turnover, ranked</h1>', 0.001, False
    monkeypatch.setattr(fs, '_ws_ask', ask)
    monkeypatch.setattr(fs._stash, 'best_for', lambda root, words, cat=None, n=2: [{'id': 's1', 'name': 'hero-headline', 'by': 'x'}])
    monkeypatch.setattr(fs._feat._sources, 'best_line', lambda rows, tag=None: '\nSTASH: hero-headline' if rows else '')
    asyncio.run(fs._ws_run('g', ws, 'a', 'fix these', [{'kind': 'el', 'sel': '#pools > h2', 'tag': 'h2', 'note': 'make it red'}, {'kind': 'el', 'sel': 'body > header > h1', 'tag': 'h1', 'note': 'a better headline'}]))
    d = fs._ws_load('g', ws); last = d['versions'][-1]['html']
    assert len(asks) == 1 and '`body > header > h1`' in asks[0][1] and '#pools' not in asks[0][1] and 'STASH: hero-headline' in asks[0][0]
    assert '<h2 style="color:red">Top pools today</h2>' in last and '<h1>Turnover, ranked</h1>' in last
    assert any('Page tools, $0: h2: set color red. The rest goes to Mind A' in m['text'] for m in d['messages'])


def test_a_3d_pick_goes_to_the_page_edit_with_its_script_not_the_canvas_tag(monkeypatch, tmp_path):
    fs, post, store, ws = _server(monkeypatch, tmp_path); asks = []
    page3 = PAGE.replace('<main>', '<main><canvas id="stage"></canvas><script type="module">const m = new Mesh(new BoxGeometry(), mat); m.name = "Hero cube";</script>')
    doc = fs._ws_load('g', ws); doc['versions'] = [{'html': page3, 'by': 'Mind A', 'at': 1}]; fs._ws_save('g', doc)
    async def ask(cat, model, sys_, user_, tokens):
        asks.append((sys_, user_)); return '', 0.0, False
    monkeypatch.setattr(fs, '_ws_ask', ask)
    asyncio.run(fs._ws_run('g', ws, 'a', 'make it spin', [{'kind': 'el', 'sel': '#stage', 'tag': 'canvas', 'node': 'three', 'three': {'name': 'Hero cube', 'type': 'Mesh', 'geometry': 'BoxGeometry'}}]))
    assert asks and "3D object named 'Hero cube'" in asks[0][1] and 'm.name = "Hero cube"' in asks[0][1] and 'ONE element' not in asks[0][0]


# ── the page's own inspect script, in a real headless browser ──────────────────────────────────────────────────────────────────────
def _browser():
    import free_browser as fb
    if not fb.chromium_path():
        pytest.skip('no Chromium on this machine')
    return fb.chromium_path()


async def _hover_click(html, points, chromium):
    """Inspect on, hover then click each (x, y). → [(pick, hover label, labels drawn in the page)] + the pin rows the page posted."""
    from playwright.async_api import async_playwright
    out = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        try:
            ctx = await b.new_context(viewport={'width': 800, 'height': 600}); pg = await ctx.new_page()
            async def serve(route):   # three.js from the repo's own node_modules: no network
                name = route.request.url.rsplit('/', 1)[1]
                await route.fulfill(path=str(THREE / name), content_type='text/javascript')
            await pg.route(f'{CDN}*', serve)
            await pg.route('https://feeless.test/', lambda r: r.fulfill(body=html, content_type='text/html'))
            await pg.goto('https://feeless.test/', wait_until='load'); await pg.wait_for_timeout(1500)
            await pg.evaluate("() => { window.__fi = {picks: [], hover: [], pins: []}; addEventListener('message', e => { const d = e.data || {}; if (d.t === 'feeless-inspected') __fi.picks.push(d); if (d.t === 'feeless-inspect-hover') __fi.hover.push(d.label); if (d.t === 'feeless-inspect-pinpos') __fi.pins.push(d.rows); }); }")
            for x, y in points:
                await pg.evaluate("() => postMessage({t: 'feeless-inspect', on: true}, '*')"); await pg.wait_for_timeout(120)
                await pg.mouse.move(x - 3, y); await pg.mouse.move(x, y); await pg.wait_for_timeout(200)
                label = await pg.evaluate('() => __fi.hover.filter(Boolean).pop() || ""')
                drawn = await pg.evaluate("() => (document.getElementById('feeless-inspect') || {innerText: ''}).innerText")
                await pg.mouse.click(x, y); await pg.wait_for_timeout(250)
                out.append((await pg.evaluate('() => __fi.picks.pop() || null'), label, drawn))
            await pg.evaluate("() => postMessage({t: 'feeless-inspect-pins', rows: [{n: 1, sel: '#mix', kind: 'fix'}]}, '*')"); await pg.wait_for_timeout(150)
            pins = await pg.evaluate('() => __fi.pins.pop() || []')
            await ctx.close()
        finally:
            await b.close()
    return out, pins


def test_hover_finds_a_text_node_a_canvas_region_and_a_3d_object_and_draws_no_label_on_the_page():
    chromium = _browser()
    if not (THREE / 'three.module.js').is_file():
        pytest.skip('three is not installed in frontend/node_modules')
    page = f'''<!doctype html><html><head><script type="importmap">{{"imports":{{"three": "{CDN}three.module.js"}}}}</script>
<style>body{{margin:0;font:20px sans-serif}} #mix{{position:absolute;left:10px;top:10px;width:380px}} #flat{{position:absolute;left:420px;top:10px}} #gl{{position:absolute;left:10px;top:200px}}</style></head>
<body><div id="mix">Loose words here <b>bold</b></div><canvas id="flat" width="300" height="150"></canvas><canvas id="gl" width="400" height="300"></canvas>
<script type="module">import * as THREE from 'three';
const r = new THREE.WebGLRenderer({{canvas: document.getElementById('gl')}}); r.setSize(400, 300, false);
const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(50, 4 / 3, 0.1, 100); cam.position.z = 4;
const cube = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.4, 1.4), new THREE.MeshBasicMaterial({{color: 0x19e68c}})); cube.name = 'Hero cube'; scene.add(cube);
(function loop() {{ r.render(scene, cam); requestAnimationFrame(loop); }})();</script></body></html>'''
    html = pi.with_hook(page.replace('</body>', pi.INSPECT + '</body>'))
    (txt, tlab, tdrawn), (cv, clab, _), (gl, glab, _) = asyncio.run(_hover_click(html, [(40, 22), (440, 30), (210, 350)], chromium))[0]
    assert txt and txt['node'] == 'text' and txt['text'] == 'Loose words here' and txt['sel'] == '#mix' and tlab.startswith('text · "Loose words here"')
    assert tdrawn.strip() == ''   # the label goes to the host, never on top of the page's own content
    assert cv['node'] == 'canvas' and cv['sel'] == '#flat' and cv['part'] == {'x': 0, 'y': 0, 'w': 1 / 3, 'h': 1 / 3} and 'top left' in clab
    if gl['node'] != 'three':
        pytest.skip('this headless browser has no WebGL (the canvas region is the fallback)')
    assert gl['three']['name'] == 'Hero cube' and gl['three']['geometry'] == 'BoxGeometry' and gl['three']['color'] == '#19e68c' and glab.startswith('3D · Hero cube')
    assert pi.find(page, gl['sel'])['tag'] == 'canvas'
    json.dumps([txt, cv, gl])


def test_the_page_tells_the_host_where_each_pin_is_so_its_number_sits_in_a_gutter():
    chromium = _browser()
    html = ('<!doctype html><html><body style="margin:0"><div id="mix" style="margin-top:120px;height:60px">Pinned</div></body></html>').replace('</body>', pi.INSPECT + '</body>')
    _, pins = asyncio.run(_hover_click(html, [], chromium))
    assert pins and pins[0]['n'] == 1 and abs(pins[0]['top'] - 120 / 600) < 0.01 and abs(pins[0]['h'] - 60 / 600) < 0.01


def test_a_3d_scene_behind_the_page_content_still_inspects():
    """The Collective Landing's shape: a fixed full-page canvas with pointer-events none under a content layer. Hovering empty space over the
    scene picks the 3D object; hovering a heading still picks the heading."""
    chromium = _browser()
    if not (THREE / 'three.module.js').is_file():
        pytest.skip('three is not installed in frontend/node_modules')
    page = f'''<!doctype html><html><head><meta charset="utf-8"><script type="importmap">{{"imports":{{"three": "{CDN}three.module.js"}}}}</script>
<style>body{{margin:0}} canvas{{position:fixed;inset:0;z-index:0;pointer-events:none}} main{{position:relative;z-index:1;height:600px}} h1{{margin:0;padding:20px;font:32px sans-serif;color:#fff}}</style></head>
<body><main><h1>The Collective</h1></main>
<script type="module">import * as THREE from 'three';
const r = new THREE.WebGLRenderer(); r.setSize(800, 600); document.body.appendChild(r.domElement);
const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 100); cam.position.z = 4;
const orb = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), new THREE.MeshBasicMaterial({{color: 0x5cc8ff}})); orb.name = 'Orb'; scene.add(orb);
(function loop() {{ r.render(scene, cam); requestAnimationFrame(loop); }})();</script></body></html>'''
    html = pi.with_hook(page.replace('</body>', pi.INSPECT + '</body>'))
    (orb, olab, _), (h1, _, _) = asyncio.run(_hover_click(html, [(400, 300), (60, 40)], chromium))[0]
    if orb['node'] == 'canvas':
        pytest.skip('this headless browser has no WebGL')
    assert orb['node'] == 'three' and orb['three']['name'] == 'Orb' and orb['tag'] == 'canvas' and olab.startswith('3D · Orb')
    assert h1['tag'] == 'h1' and h1['node'] == 'el'
