"""Slice 3 (owner 2026-11-18: "so many integrative tools missing from static"): every PoStatic build mind gets every approved kit, each kit
the page uses is listed with what it did; every build has a new brief and a near-copy of any past build is refused before it files; the hidden
code check catches overlapping blocks, broken links, placeholder text and a page that will not load on a phone; a new version can never lose
a part the last one had working; and a studio piece is used throughout the site, not once. Network and the headless browser are faked."""
import asyncio
import json
import re

import pytest

import collective_kits as kits
import owner_models as om
import proof_record as prec
import ps_hidden as ph
import ps_keep as keep
import ps_kits as psk
import ps_unique as pu

URL = 'https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/tombstone_01/tombstone_01_1k.gltf'
STONE = {'id': 'o1', 'name': 'Tombstone', 'asset': {'id': 'tombstone_01', 'name': 'Tombstone', 'url': URL, 'files': {}}, 'height': 1.6,
         'rot': [0, 0.61, 0], 'scale': [1, 1, 1], 'spin': 6, 'pos': [0, 0, 0]}
POOLS = ('<!doctype html><html><head><meta name="viewport" content="width=device-width"><title>Pool turnover</title></head><body>'
         '<header><h1>Solana pool turnover</h1></header><main data-feeless-layout="split"><section id="chart"><h2>Turnover by pool</h2>'
         '<div id="c" data-feeless-centre="candles"></div></section><section id="pools"><h2>Top pools today</h2><table><tr><td>SOL/USDC</td></tr></table></section>'
         '<section id="how"><h2>How turnover works</h2><p>' + 'Turnover is the day volume divided by the money in the pool, read live. ' * 4 + '</p></section></main>'
         '<footer>Read from DexScreener</footer><script>addEventListener("message", e => { if (e.data && e.data.t === "feeless-live") draw(e.data.live.pools, e.data.live.candles) });'
         'const c = LightweightCharts.createChart(document.getElementById("c"), {autoSize: true}); c.addCandlestickSeries();'
         'Motion.animate("h1", {opacity: [0, 1]}); Motion.inView("section", el => Motion.animate(el, {y: [20, 0]}));</script>'
         '<script type="application/json" id="feeless-kits">{"Lightweight Charts": "SOL candles from the FEELESS index", "Motion": "headline and sections ease in"}</script></body></html>')
SHOP = ('<!doctype html><html><head><title>Candle shop</title><style>body{background:#fff6e0;color:#3a2410}</style></head><body><nav>Home Shop</nav>'
        '<article><h1>Hand poured candles</h1><p>' + 'Soy wax, cotton wicks and oils from small farms, poured by hand in small runs. ' * 5 + '</p></article>'
        '<form id="order"><label>Name<input required></label><button>Order</button></form><script>localStorage.setItem("x", 1)</script></body></html>')


# ── 🧰 the full toolkit ──
def test_every_build_mind_reads_every_approved_kit_and_the_picks_still_come_first():
    line = psk.menu_line(['motion'])
    for name in ('three.js', 'Motion', 'Recharts', 'Lightweight Charts', 'shadcn/ui', 'DexScreener + FEELESS indexes', 'Wallet connect', 'Forms', 'Leaflet'):
        assert name in line, name
    assert 'Already picked: Motion' in line and 'feeless-kits' in line and 'never asks to sign' in line   # the wallet bridge is read-only (§1)


def test_each_kit_the_page_uses_is_listed_with_what_it_did():
    rows = {r['id']: r for r in psk.did(POOLS, ['motion', 'heroui'])}
    assert rows['motion']['used'] and rows['motion']['did'] == 'headline and sections ease in' and rows['motion']['by'] == 'minds' and rows['motion']['picked']
    assert rows['lwcharts']['did'] == 'SOL candles from the FEELESS index' and not rows['lwcharts']['picked']
    assert rows['live']['used'] and 'DexScreener pools' in rows['live']['did'] and 'FEELESS 5m candles' in rows['live']['did']
    assert rows['heroui']['used'] is False and rows['heroui']['did'] == ''   # a pick the page skipped is still listed, as not used
    words_only = POOLS.replace('LightweightCharts.createChart', 'drawIt')
    assert 'lwcharts' not in {r['id'] for r in psk.did(words_only, [])}   # the minds' words never make a kit "used": only its code does


def test_a_page_loads_the_files_of_every_kit_its_code_uses_and_map_tiles_pass_the_lock():
    page = '<html><head><meta http-equiv="Content-Security-Policy" content="default-src \'none\'"></head><body><div id="m"></div><script>const R = Recharts; const m = L.map("m"); L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png").addTo(m)</script></body></html>'
    carry = psk.carry([], page); assert 'recharts' in carry and 'leaflet' in carry
    out = kits.open_for_kits(kits.with_kit_tags(page, carry), carry)
    csp = re.search(r'Content-Security-Policy" content="([^"]+)', out).group(1)
    assert 'recharts@2.15.4/umd/Recharts.js' in out and 'react@18.3.1' in csp and 'leaflet@1.9.4/dist/leaflet.js' in csp and 'https://*.basemaps.cartocdn.com' in csp


def test_the_bug_found_on_the_way_nine_kits_had_signs_that_never_matched_or_crashed():
    """Leaflet, Phaser, Matter, Howler, Tone, Anime, tsParticles, Marked, Tabulator: double-escaped signs. Leaflet's, Howler's and
    Tabulator's crashed kit_report outright ('missing ), unterminated subpattern') whenever one was picked."""
    for kid, k in kits.KIT_USE.items():
        re.compile(k['sign'])
    page = '<script>L.map(el); new Phaser.Game(); Matter.Engine.create(); new Howl({}); Tone.start(); anime.animate(x); tsParticles.load(); marked.parse(t); new Tabulator(el)</script>'
    picks = ['leaflet', 'phaser', 'matter', 'howler', 'tone', 'anime', 'particles', 'marked', 'tabulator']
    assert all(r['used'] for r in kits.kit_report(page, picks))


def test_the_live_kit_reads_dexscreener_pools_and_our_own_candles():
    pair = lambda a, sym, liq, vol, base='b1': {'pairAddress': a, 'dexId': 'raydium', 'baseToken': {'symbol': sym, 'address': base}, 'quoteToken': {'symbol': 'USDC'},
                                                 'priceUsd': '73.5', 'liquidity': {'usd': liq}, 'volume': {'h24': vol}, 'priceChange': {'h24': -1.6}, 'url': 'https://dexscreener.com/solana/' + a}
    rows = psk.pools_of([pair('p1', 'SOL', 1000, 5000), pair('p2', 'SOL', 0, 9)], [pair('p3', 'WIF', 50, 100, 'w'), pair('p4', 'WIF', 500, 100, 'w')])
    assert [r['pair'] for r in rows] == ['SOL/USDC', 'WIF/USDC'] and rows[0]['turnover'] == 5.0 and rows[1]['liqUsd'] == 500   # best pool per coin, empty pools out
    c = psk.candles_of({'candles': [[1, 2, 3, 1, 2.5, 10]]}); assert c['rows'] == [[1, 2, 3, 1, 2.5, 10]] and c['source'] == 'FEELESS candle index'
    assert psk.candles_of({}) is None


# ── 🧬 unique ──
def test_a_page_is_its_own_copy_and_two_different_pages_are_not():
    a, b = pu.fingerprint(POOLS), pu.fingerprint(SHOP)
    assert pu.likeness(a, a) == 1.0 and pu.likeness(a, b) < 0.3
    assert (a['layout'], a['centre']) == ('split', 'candles') and b['centre'] == 'tool'
    reworded = POOLS.replace('Solana pool turnover', 'Pool turnover on Solana').replace('Top pools today', 'The top pools')
    g = pu.gate(pu.fingerprint(reworded), [{'n': 7, 'ws': 'w0', 'print': a}]); assert g['copy'] and g['nearest'] == 7   # a reworded copy is still a copy
    assert not pu.gate(b, [{'n': 7, 'ws': 'w0', 'print': a}])['copy']


def test_every_build_gets_a_new_brief_never_a_past_pair_nor_a_recent_centrepiece_or_layout():
    past = []
    for i in range(12):
        b = pu.brief('a live chart of pool turnover', past, seed='w')
        assert b['new'] and (b['centre'], b['layout']) not in {(p['centre'], p['layout']) for p in past}
        assert b['centre'] not in {p['centre'] for p in past[-pu.RECENT:]} and b['layout'] not in {p['layout'] for p in past[-pu.RECENT:]}
        past.append(b)
    assert pu.brief('a live price chart', [], seed='x')['centre'] in ('candles', 'datachart')   # first, what fits the ask
    line = pu.brief_line(past[0]); assert f'data-feeless-centre="{past[0]["centre"]}"' in line and 'data-feeless-layout' in line


# ── 🕵 clean ──
def test_the_hidden_check_catches_dead_links_and_placeholder_text_and_adds_what_the_phone_saw():
    bad = '<html><head><title>x</title><meta name="viewport" content="w"></head><body><h1>Hi</h1><a href="#gone">go</a><p>[Your Company] ' + 'word ' * 40 + '</p></body></html>'
    r = ph.run(bad); assert {'no-fake-data', 'no-dead-anchors'} <= set(r['failed']) and r['v'] == 3 and r['deadAnchors'] == ['#gone']
    assert 'phone-load' not in [c['id'] for c in r['checks']]   # no phone ran: never failed for a browser that was not there
    seen = {'ran': True, 'loads': False, 'fits': False, 'overlaps': [{'on': 'phone', 'a': 'h1: Hi', 'b': 'p: x'}], 'deadLinks': [{'url': 'https://x.io/404', 'why': '404'}]}
    r2 = ph.run(POOLS, seen=seen); assert {'phone-load', 'fits-phone', 'no-overlap', 'links-alive'} <= set(r2['failed']) and r2['seen'] == seen
    assert not ph.run(POOLS, seen={'ran': True, 'loads': True, 'fits': True, 'overlaps': [], 'deadLinks': []})['failed']
    assert ph.outside_links('<a href="https://a.io">a</a><a href="https://a.io">b</a><a href="#x">c</a>') == ['https://a.io']


def test_dead_links_are_404_or_no_answer_and_a_site_that_blocks_robots_is_not_dead():
    class R:
        def __init__(self, code): self.status_code = code

    class H:
        async def head(self, u, **k):
            if 'gone' in u:
                raise OSError('no such host')
            return R({'a': 200, 'b': 404, 'c': 403}[u[-1]])

        async def get(self, u, **k):
            return R(403)
    got = asyncio.run(ph.dead_links(['https://x.io/a', 'https://x.io/b', 'https://x.io/c', 'https://gone.io/a'], H()))
    assert [d['url'] for d in got] == ['https://x.io/b', 'https://gone.io/a']


# ── ⏫ progress ──
def test_a_new_version_that_drops_a_working_part_is_caught_unless_the_owner_asked():
    worse = POOLS.replace('<section id="pools"><h2>Top pools today</h2><table><tr><td>SOL/USDC</td></tr></table></section>', '').replace('LightweightCharts.createChart', 'x')
    gone = {p['key'] for p in keep.lost(POOLS, worse, 'make it brighter')}
    assert gone == {'section:pools', 'kit:lwcharts'}
    assert {p['key'] for p in keep.lost(POOLS, worse, 'remove the top pools table and the chart')} == set()   # his own words take them out
    renamed = POOLS.replace('<section id="pools"><h2>Top pools today', '<section id="pools"><h2>Biggest pools')
    assert keep.lost(POOLS, renamed, '') == []   # same section, new title: not lost
    r = keep.record(POOLS, worse, 'brighter', 2); assert r['from'] == 2 and len(r['lost']) == 2 and r['kept'] == r['had'] - 2
    assert 'KEEP EVERY PART' in keep.keep_line(keep.lost(POOLS, worse, ''))


# ── 🪦 studio piece throughout the site ──
def test_a_studio_piece_goes_in_every_place_it_fits_not_once():
    rows = [om.take(STONE, 1)]; html = om.mount(POOLS, rows)
    assert om.places(html) == {'tombstone_01': 3} and html.index('data-feeless-model') > html.index('</header>') and html.count('data-feeless-spot="code"') == 3
    assert om.mount(html, rows).count('data-feeless-model="') == 3   # run again: never doubled
    rec = om.record(rows, html)[0]; assert rec['places'] == 3 and rec['room'] == 3 and rec['used']
    marked = POOLS.replace('<div id="c"', '<div data-feeless-model="tombstone_01"></div><div id="c"')
    m2 = om.mount(marked, rows); assert om.places(m2) == {'tombstone_01': 3} and 'data-feeless-spot="code"' in m2   # the minds' own spot + code fills the rest
    assert 'data-feeless-spot' not in om.mount(html, [])   # taken out: every code spot leaves


# ── 🧾 the record ──
def test_the_record_carries_unique_clean_progress_and_kits_rows_for_postatic():
    f = {'kits': ['motion'], 'kitsDid': [{'name': 'Motion', 'did': 'hero entrance'}],
         'unique': {'briefNew': True, 'copy': False, 'want': {'centre': 'candles', 'layout': 'split'}, 'centre': 'candles', 'layout': 'split', 'like': 0.2, 'nearest': 4, 'nearestPair': ['3d', 'scroll']},
         'codeCheck': {'passed': 13, 'total': 13, 'failed': [], 'seen': {'ran': True}}, 'keep': {'from': 1, 'kept': 5, 'had': 5, 'lost': []}}
    rows = {c['key']: c for c in prec.checks('pos', f, [])}
    assert rows['kits']['why'] == 'Motion: hero entrance' and rows['unique']['ok'] and rows['clean']['ok'] and 'real phone' in rows['clean']['why'] and rows['progress']['ok']
    bad = {c['key']: c for c in prec.checks('pos', {**f, 'unique': {**f['unique'], 'copy': True}, 'codeCheck': {'failed': ['no-overlap']}, 'keep': {'from': 1, 'lost': ['the map']}}, [])}
    assert not bad['unique']['ok'] and not bad['clean']['ok'] and 'no-overlap' in bad['clean']['why'] and not bad['progress']['ok']
    same = {c['key']: c for c in prec.checks('pos', {**f, 'unique': {**f['unique'], 'nearestPair': ['candles', 'split']}}, [])}
    assert not same['unique']['ok']   # the same centrepiece AND layout as its nearest past build is not new
    assert [c['key'] for c in prec.checks('pos', {'kits': ['three']}, [])] == ['minds', 'sources', 'footprint', 'kits']   # an old folder: the four checks as before
    st = prec.checks('pos', {'kits': ['three'], 'studio': [{'name': 'T', 'used': True, 'places': 1, 'pagePlaces': 1, 'room': 3}]}, [])[-1]
    assert st['key'] == 'studio' and not st['ok'] and 'in 1 of the 3 places' in st['why']


# ── the build path end to end (minds faked) ──
def _server(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'name': 'Ann', 'ownerId': 'g', 'revoked': False, 'brainsCfg': {'brains': ['m/x']}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); monkeypatch.setattr(fs, 'KITS_DIR', tmp_path / 'kits')
    async def reads(*_a, **_k):
        return '', []
    async def live(cat):
        return {'solUsd': 73.5, 'slot': 1, 'pools': [], 'candles': None}
    monkeypatch.setattr(fs, '_site_reads', reads); monkeypatch.setattr(fs, '_page_live', live)
    return fs, TestClient(fs.app), store


def _folder(fs, c, name, page=None):
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    ws = post('feature_create', text='build', job=name).json()['folder']['id']
    doc = fs._ws_load('g', ws); doc['cfg'] = {'research': False, 'suggest': False, 'review': False}
    if page:
        doc['versions'] = [{'html': page, 'by': 'Mind A', 'at': 1}]
    fs._ws_save('g', doc)
    return ws


def test_a_build_reads_the_whole_toolkit_and_its_brief_and_files_every_slice3_row(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); ws = _folder(fs, c, 'pools'); seen = []
    async def page(cat, model, sys_, user_, tokens, on_part=None):
        seen.append(sys_); return POOLS, 0.0, False
    async def phone(html, chromium=None, http=None, **k):
        return {'ran': True, 'loads': True, 'fits': True, 'overlaps': [], 'deadLinks': [], 'errors': []}
    monkeypatch.setattr(fs, '_ws_page', page); monkeypatch.setattr(fs._ps_hidden, 'browser', phone)
    asyncio.run(fs._ws_run('g', ws, 'a', 'a live tool for Solana pool turnover', None))
    d = fs._ws_load('g', ws); assert len(d['versions']) == 1
    assert 'THE FULL POSTATIC TOOLKIT' in seen[0] and "THIS BUILD'S BRIEF" in seen[0] and d['brief']['new']
    assert {k['id'] for k in d['kitsUsed'] if k['used']} >= {'lwcharts', 'motion', 'live'} and 'lightweight-charts@4' in d['versions'][-1]['html']   # its files were added for it
    fs._ws_pass(store); f = store['cats']['g']['psFolders'][-1]
    assert f['kitsDid'] and f['unique']['briefNew'] and not f['unique']['copy'] and f['codeCheck']['seen']['ran'] and f['print']['centre'] == 'candles'
    keys = {ch['key']: ch['ok'] for ch in f['proofChecks']}; assert keys['unique'] and keys['clean'] and keys['kits'], f['proofChecks']
    json.dumps(f)


def test_a_near_copy_of_another_agents_build_is_sent_back_once_then_refused(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    store['cats']['h'] = {'id': 'h', 'name': 'Bo', 'psFolders': [{'id': 'ps1', 'n': 9, 'ws': 'wold', 'at': 1, 'version': 1, 'print': pu.fingerprint(POOLS)}]}
    ws = _folder(fs, c, 'again'); calls = []
    async def page(cat, model, sys_, user_, tokens, on_part=None):
        calls.append(sys_); return POOLS, 0.0, False
    monkeypatch.setattr(fs, '_ws_page', page)
    asyncio.run(fs._ws_run('g', ws, 'a', 'a pool page', None))
    d = fs._ws_load('g', ws)
    assert len(calls) == 2 and 'TOO CLOSE' in calls[1] and 'PoStatic #9' in calls[1]   # sent back once, told what it copied
    assert not d.get('versions') and d['refused'][-1]['copy'] and d['refused'][-1]['nearest'] == 9 and 'never files' in d['messages'][-1]['text']
    fs._ws_pass(store); assert not store['cats']['g'].get('psFolders')   # nothing filed


def test_a_version_that_would_lose_a_working_part_is_sent_back_then_kept_when_it_puts_it_back(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); ws = _folder(fs, c, 'pools', page=POOLS); calls = []
    worse = POOLS.replace('<section id="pools"><h2>Top pools today</h2><table><tr><td>SOL/USDC</td></tr></table></section>', '')
    better = POOLS.replace('<h1>Solana pool turnover</h1>', '<h1>Solana pool turnover, live</h1>')
    async def page(cat, model, sys_, user_, tokens, on_part=None):
        calls.append(sys_); return (worse if len(calls) == 1 else better), 0.0, False
    monkeypatch.setattr(fs, '_ws_page', page)
    asyncio.run(fs._ws_run('g', ws, 'a', 'rebuild it brighter', None))
    d = fs._ws_load('g', ws)
    assert len(calls) == 2 and 'KEEP EVERY PART' in calls[1] and 'Top pools today' in calls[1]
    assert len(d['versions']) == 2 and 'live</h1>' in d['versions'][-1]['html'] and d['keep']['lost'] == [] and d['keep']['from'] == 1
    fs._ws_pass(store); f = store['cats']['g']['psFolders'][-1]; assert [ch for ch in f['proofChecks'] if ch['key'] == 'progress'][0]['ok']


def test_a_version_that_still_loses_the_part_is_refused_and_the_last_page_stays(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); ws = _folder(fs, c, 'pools', page=POOLS)
    worse = POOLS.replace('LightweightCharts.createChart', 'noChart')
    async def page(cat, model, sys_, user_, tokens, on_part=None):
        return worse, 0.0, False
    monkeypatch.setattr(fs, '_ws_page', page)
    asyncio.run(fs._ws_run('g', ws, 'a', 'rebuild it', None))
    d = fs._ws_load('g', ws)
    assert len(d['versions']) == 1 and d['versions'][0]['html'] == POOLS and 'Lightweight Charts' in d['refused'][-1]['lost'][0] and 'Not kept' in d['messages'][-1]['text']


def test_a_page_built_in_sections_takes_its_brief_and_the_centrepiece_writer_gets_its_kit(monkeypatch, tmp_path):
    """The real TEST PoStatic #7 (2026-11-18): local minds built in sections; the section writers' prompt was cut at 1,500 characters, so
    the toolkit and the brief never reached them, and the code-written frame was one template for every page (no <h1>)."""
    fs, c, store = _server(monkeypatch, tmp_path); ws = _folder(fs, c, 'pools'); asks = []
    plan = json.dumps({'title': 'Pool Turnover', 'tagline': 'live', 'accent': '#19e68c', 'sections': [{'name': 'Hero', 'brief': 'the idea'}, {'name': 'Turnover chart', 'brief': 'the chart of turnover'}, {'name': 'How', 'brief': 'how it works'}]})
    async def page(*a, **k):
        return '', 0.0, False   # the whole page never fits one local reply
    async def ask(cat, model, sys_, user_, tokens):
        asks.append((sys_, user_)); return (plan if 'You plan one web page' in sys_ else '<h2>Part</h2><p>' + 'Real words about the pools on Solana. ' * 6 + '</p><script>const R = Recharts; R.AreaChart</script>'), 0.0, False
    monkeypatch.setattr(fs, '_ws_page', page); monkeypatch.setattr(fs, '_ws_ask', ask)
    asyncio.run(fs._ws_run('g', ws, 'a', 'a live tool for pool turnover with a chart', None))
    d = fs._ws_load('g', ws); html = d['versions'][-1]['html']; b = d['brief']
    assert f'data-feeless-layout="{b["layout"]}"' in html and f'data-feeless-centre="{b["centre"]}"' in html and '<h1>Pool Turnover</h1>' in html
    centre = [s_ for s_, u_ in asks if 'THIS SECTION IS THE CENTREPIECE' in s_]; others = [s_ for s_, u_ in asks if 'KITS YOU MAY USE' in s_]
    assert len(centre) == 1 and others and 'Never draw a chart by hand' in others[0]
    assert pu.layout_of(html) == (b['layout'], 'said') and pu.centre_of(html) == (b['centre'], 'said') and d['unique']['briefKept']


def test_each_section_gets_the_kits_its_own_brief_names():
    """Real TEST #8 (EMBER): the map, wallet and live-price sections drew no kit because only the centrepiece got kit how-tos."""
    import ps_kits as pk
    assert pk.part_kits('Interactive map showing global meetup locations') == ['leaflet']
    assert pk.part_kits('Secure Solana wallet connection button') == ['wallet']
    assert 'live' in pk.part_kits('Displays current Solana price in real-time')
    line = pk.part_line({'centre': 'story'}, False, '', 'Interactive map of the meetup cities')
    assert 'L.map' in line and 'fake a wallet' in line


def test_a_cut_off_section_script_never_swallows_the_next_section():
    """Real TEST #8: the wallet section's reply stopped mid-<script>, the form section landed inside it, the page threw on a phone."""
    import agent_features as af
    assert af.part_html('<div id="w">Connect</div><script>const b = document.getElementById(') == '<div id="w">Connect</div>'
    assert af.part_html('<div>x</div><script>ok()</script>') == '<div>x</div><script>ok()</script>'
    assert af.part_html('<style>.a{color:red}').endswith('</style>')


def test_a_form_field_hint_is_not_fake_data():
    import ps_hidden as ph
    page = '<html><head><title>t</title></head><body><h1>Hi</h1><input type="email" placeholder="you@example.com"></body></html>'
    assert 'no-fake-data' not in ph.run(page)['failed']
    assert 'no-fake-data' in ph.run(page.replace('<h1>Hi</h1>', '<h1>Hi</h1><p>Mail us at hi@example.com</p>'))['failed']


def test_section_writers_are_told_never_to_lay_words_over_a_map_chart_or_scene():
    """Real TEST #9 (EMBER): the map section laid its title over the map, on Leaflet's zoom buttons; the hidden phone check failed it."""
    import ps_kits as pk
    side = pk.part_line({'centre': 'story'}, False, '', 'Interactive map of the meetup cities')
    centre = pk.part_line({'centre': 'map'}, True, '')
    for line in (side, centre):
        assert 'Never lay words on top' in line
    assert 'height:360px' in pk.MENU['leaflet']['how'] and 'never laid on the map' in pk.MENU['leaflet']['how']


def test_a_section_cut_off_mid_tag_ends_before_the_broken_tag():
    """Real TEST #10: the price section's reply stopped at '<span id'."""
    import agent_features as af
    assert af.part_html('<div><span id="p">$1</span> <span id') == '<div><span id="p">$1</span> '
