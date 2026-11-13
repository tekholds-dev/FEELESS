import json
import play_studio as ps

GLINT_HOME = {'objects': [], 'page': {'headline': 'GLINT', 'sub': 's', 'cta': 'Enter the room', 'sections': []}}
ROOM = {'objects': [], 'page': {'headline': 'GLINT', 'dash': {'title': 'T', 'stats': [{'label': 'Price', 'value': '$1'}, {'label': 'Holders', 'value': '9'}, {'label': 'Volume', 'value': '$2'}], 'points': list(range(9))}}}


def test_his_words_reach_the_page_he_named():
    assert not ps.names_room('ADD MORE VITAL INFO AND A REAL CHART TO THE GLINT HOME PAGE AND A BACK BUTTON')
    assert not ps.names_room('add a chart') and ps.names_room('more posters') and ps.names_room('put a chart in the room')


def test_a_reply_that_leaves_things_out_never_wipes_them():
    kept = ps.keep_page(ROOM['page'], {'headline': 'GLINT', 'sub': '', 'cta': '', 'sections': []})
    assert kept['dash']['points'] == list(range(9))
    assert ps.keep_page(GLINT_HOME['page'], {'headline': 'NOVA'}, 'rename it')['headline'] == 'NOVA' and ps.keep_page(None, None) == {}


def test_asking_for_a_chart_always_lands_one_and_says_what_is_there():
    got = ps.ensure_asks(GLINT_HOME, 'still no charts and real number data')   # 🔒 2026-11-13: nothing invented — "—" values, no chart until real prices
    d = got['page']['dash']; assert d['points'] == [] and len(d['stats']) == 4 and all(x['value'] == '—' for x in d['stats']) and 'once the coin trades' in d['note'] and got['page']['cta'] == 'Enter the room'
    assert ps.ensure_asks(ROOM, 'a chart') is ROOM and ps.ensure_asks(GLINT_HOME, 'make it darker') is GLINT_HOME
    assert ps.page_facts(got, ROOM) == 'Home page: no chart; Room: a chart and 3 numbers, a back button.'
    asked = ps.ensure_asks(GLINT_HOME, 'add fake numbers and a chart')['page']['dash']   # the owner asked for sample numbers by name: labelled, as before
    assert len(asked['points']) > 10 and 'Sample' in asked['note']
    assert ps.page_facts(GLINT_HOME, None) == 'Home page: no chart.'


def test_the_room_always_has_a_way_back():
    html = ps.to_html(GLINT_HOME, 'GLINT', ROOM)
    assert html.count('page-back" data-go="0"') == 1 and '← Back' in html
    assert 'page-back" data-go' not in ps.to_html(GLINT_HOME, 'GLINT', None)


def test_another_coin_never_gets_glints_design():
    line = ps.references_line([{'name': 'GLINT', 'prompt': 'a vintage camera', 'why': 'Real assets: Camera 01'}], 'a coin called NOVA, a collapsing star')
    assert 'camera' not in line.lower() and 'marble' not in line.lower() and 'Build ONLY' in line
    assert 'vintage camera' in ps.references_line([], 'make it like GLINT')
    assert ps.WRONG_BUILD.search('thats not what i asked for, the coins name is nova and the design idea isnt glint')


def test_a_dark_room_in_words_is_not_a_room_to_build():
    assert not any(o['name'] == 'Back wall' for o in ps.ensure_named({'objects': []}, 'Every wallet is a dark room. Button: Enter the room')['objects'])
    assert any(o['name'] == 'Back wall' for o in ps.ensure_named({'objects': []}, 'a whole room with a desk')['objects'])


def test_a_paste_keeps_its_design_and_drops_its_code():
    t = 'NOVA, a collapsing star.\n```jsx\nimport x\n' + 'y' * 9000 + '\n```\nThe mint button is inside the star.'
    got = ps.prompt_of(t); assert 'collapsing star' in got and 'mint button' in got and 'yyy' not in got


def test_a_chart_request_cannot_rewrite_his_words():
    old = {'headline': 'GLINT', 'sub': 'The coin', 'cta': 'Enter the room', 'sections': [{'title': 'A', 'body': 'B'}]}
    got = ps.keep_page(old, {'headline': 'Enter the Room', 'sub': 'x', 'dash': {'points': [1]}}, 'no charts on the glint home page FIX')
    assert got['headline'] == 'GLINT' and got['sub'] == 'The coin' and got['dash'] == {'points': [1]}
    assert ps.keep_page(old, {'headline': 'NOVA'}, 'the coins name is nova')['headline'] == 'NOVA'


def test_a_design_no_library_holds_goes_to_real_code():
    assert ps.wants_code('A slowly rotating collapsing star (shader sphere), particles get sucked inward')
    assert not ps.wants_code('a vintage camera on a marble stage, a chair and old books')


def test_a_chart_request_needs_no_model_and_a_thin_dash_gets_filled():
    built = {'objects': [{'name': 'Stage'}]}
    assert ps.chart_only("still no charts and real number data on glint home page, and enter the room:you took off the chart and theres no back button  FIX", built, 'GLINT')
    assert ps.chart_only("ADD MORE VITAL INFO AND FAKE NUMBERS AND A REAL CHART TO THE GLINT HOME PAGE\nAND A BACK BUTTON TO GO BACK TO GLINT'S HOME PAGE", built, 'GLINT')
    assert not ps.chart_only('add a chart and a brass lamp to the room', built, 'GLINT')
    assert not ps.chart_only('add a chart and a brass lamp on the desk', built) and not ps.chart_only('a chart', {'objects': []}) and not ps.chart_only('make it darker', built)
    thin = {'objects': [], 'page': {'headline': 'G', 'dash': {'stats': [{'label': 'Price', 'value': '$0.042'}], 'points': [1, 2]}}}
    d = ps.ensure_asks(thin, 'a chart')['page']['dash']; assert d['stats'][0]['value'] == '$0.042' and len(d['stats']) == 4 and d['points'] == [1, 2] and d['stats'][1]['value'] == '—'
    assert '<svg' not in ps._dash_html({'stats': [], 'points': []}, str) and 'once the coin trades' in ps._dash_html({'stats': [], 'points': []}, str)   # no made-up curve


def test_moving_the_monitors_never_loses_them_and_they_sit_on_the_real_desk():
    three = {'objects': [{'name': 'Monitor screen'}, {'name': 'Monitor foot'}] * 3}; one = {'objects': [{'name': 'Monitor screen'}, {'name': 'Desk'}]}
    got, said = ps.keep_monitors(one, three, 'the monitors need to sit on the table', 'p')
    assert said == '3 monitors. p' and [o['name'] for o in got['objects']] == ['Desk'] and ps._count_of(said, r'(?:monitors?)', 1) == 3
    assert ps.keep_monitors(one, three, 'only one monitor', 'p')[1] == 'p' and ps.keep_monitors(three, three, 'x', 'p')[1] == 'p'
    html = ps.to_html({'objects': [{'prefab': 'room'}], 'page': {'headline': 'G'}}, 'G', None)
    assert 'intersectObject(desk, true)' in html and 'userData.piece' in html and '/desk|table/i.test' in html and '\x08' not in html


def test_every_request_gets_a_print_it_did_not_just_use():
    used = []
    for i in range(6):
        pr = ps.creative_print(f'r{i}', used, 'a plain page'); assert pr not in used; used.append(pr)
    assert all(a['mood'] != b['mood'] for a, b in zip(used, used[1:]))
    assert ps.creative_print('x', [], 'a neon arcade coin')['mood'] == 'neon' and ps.mood_of('not noir, make it a sunset') == 'sunset'
    sc = ps.apply_print({'objects': [{'name': 'Cannon', 'find': 'cannon', 'pos': [0, 0, 0]}], 'layout': None}, {'mood': 'noir', 'layout': 'right'})
    assert sc['mood'] == 'noir' and sc['layout'] == 'right' and [o['name'] for o in sc['objects']][:2] == ['Mood floor', 'Mood stage']
    room = ps.apply_print({'objects': [{'name': 'Back wall', 'shape': 'box'}]}, {'mood': 'noir', 'layout': 'left'})
    assert [o['name'] for o in room['objects']] == ['Back wall']   # a room keeps its walls, with no stage dropped in it
    html = ps.to_html(ps.clean_scene(sc), 'N', None); assert 'at-right' in html and 'playfair-display' in html and 'UnrealBloomPass' in html
    assert ps.WRONG_BUILD.search("USE DIFFERENT 3D ARTIFACTS AND CREATE A NEW 3D PLAYGROUND FOR THE BACKGROUND, DONT DO THE SAME THING")


def test_a_short_brief_is_enough_for_a_whole_set():
    scene, say = ps.parse_reply(json.dumps({'say': 'x', 'brief': {'mood': 'sunset', 'hero': 'motorcycle', 'props': ['barrel', 'tree'], 'page': {'headline': 'Long Road'}}}))
    rows = {o['name']: o for o in scene['objects']}
    assert say == 'x' and scene['mood'] == 'sunset' and scene['hdri_id'] in ps.MOODS['sunset']['skies'] and not scene['ground']
    assert rows['motorcycle']['pos'] == [0, 0, 0] and rows['barrel']['pos'] != [0, 0, 0] and rows['barrel']['pos'][2] < 0
    assert rows['tree']['height'] <= rows['motorcycle']['height'] * 1.5   # a tree may not push the camera back until the hero is a speck
    assert scene['page']['headline'] == 'Long Road' and scene['camera'][2] > 2


def test_a_weak_model_cannot_stack_everything_on_the_hero():
    scene, _ = ps.parse_reply(json.dumps({'objects': [{'find': 'chair'}, {'find': 'table'}, {'find': 'lamp'}]}))
    assert len({tuple(o['pos']) for o in scene['objects']}) == 3
    now = ps.clean_scene({'objects': [{'find': 'chair', 'pos': [0, 0, 0]}]})
    more, _ = ps.parse_reply(json.dumps({'add': ['old books'], 'mood': 'neon'}), now, 'make it neon and add old books')
    assert more['mood'] == 'neon' and [o['name'] for o in more['objects']] == ['chair', 'old books']


def test_every_mood_and_template_is_real():
    import asset_packs as a
    for k, m in ps.MOODS.items():
        assert m['skies'] and m['font'] and m['set'] in ('place', 'studio', 'far')
    for t in ps.TEMPLATES:
        got = ps.template_scene(t['id']); assert t['brief']['mood'] in ps.MOODS and (got['objects'] or got.get('hero'))
    assert ps.template_scene('nope') is None and len(ps.menu()['moods']) == len(ps.MOODS)
    assert a.SAFE_URL.fullmatch('https://dl.polyhaven.org/file/a.hdr')


def test_a_game_brief_makes_a_real_game_page_with_no_model():
    scene, _ = ps.parse_reply(json.dumps({'brief': {'mood': 'neon', 'game': 'runner', 'player': 'robot', 'hazards': ['crate'], 'pickup': 'gold coin', 'page': {'headline': 'Run', 'cta': 'Go'}}}))
    assert scene['game'] == 'runner' and [o.get('role') for o in scene['objects']] == ['player', 'hazard', None]   # a coin is drawn by code, it reads better than any upload
    scene['objects'][0]['asset'] = {'url': 'https://dl.polyhaven.org/x.gltf', 'files': {}}
    html = ps.to_html(scene, 'Run')
    for needed in ('window.__game', 'pointerdown', 'localStorage', 'id="go"', 'prefers-reduced-motion', 'bot('):
        assert needed in html
    assert '<script type="module">' in html and html.count('Run') > 1
    assert ps.lock_site(html).count('Content-Security-Policy') == 1
    assert ps.wants_game('make a playable arcade game') and not ps.wants_game('a landing page')
    made = ps.from_brief({'hero': 'tank'}, 'a survival arena game'); assert made['game'] == 'arena' and made['objects'][0]['role'] == 'player'


def test_a_centerpiece_alone_is_a_whole_scene_and_a_checker_cannot_put_a_hoodie_on_it():
    scene, _ = ps.parse_reply(json.dumps({'brief': {'mood': 'space', 'centerpiece': 'blackhole', 'tint': '#00ffff', 'page': {'headline': 'G'}}}))
    assert scene['hero'] == 'blackhole' and scene['tint'] == '#00ffff' and scene['world'] == 'nebula'
    assert ps._frame({**scene, 'camera': [0, 0, 0]})['camera'][2] > 5
    more, _ = ps.parse_reply(json.dumps({'add': [{'find': 'black hole with glowing particles'}, {'find': 'chain'}]}), scene)
    assert [o['name'] for o in more['objects']] == ['chain'] and more['hero'] == 'blackhole'
    assert ps.from_brief({'hero': 'black hole'})['hero'] == 'blackhole'
    assert ps.ensure_named({'mood': 'noir', 'objects': []}, 'a story about three monitors')['objects'] == []


def test_the_library_will_not_call_a_cannon_a_barrel(tmp_path):
    import asset_packs as a
    a._save(tmp_path, a.INDEX, {'at': 9e12, 'rows': {'model': [{'id': 'cannon_01', 'name': 'cannon 01', 'tags': ['barrel', 'weapon'], 'pop': 99}, {'id': 'Barrel_01', 'name': 'Barrel 01', 'tags': ['wood'], 'pop': 1}]}})
    assert a.best(tmp_path, 'wooden barrel', 'model')['id'] == 'Barrel_01'
    assert a.best(tmp_path, 'weapon', 'model')['id'] == 'cannon_01'   # our own photoscan tags still count when nothing is named it


def test_what_was_turned_down_cannot_come_back():
    was = {'objects': [{'name': 'vintage camera', 'find': 'vintage camera', 'asset': {'id': 'Camera_01'}}, {'name': 'Stage', 'shape': 'box'}]}
    assert 'vintage camera' in ps.rejected_line(was) and ps.rejected_line(None) == ''
    got = ps.drop_rejected({'objects': [{'name': 'cam', 'find': 'vintage camera', 'asset': {'id': 'Camera_01'}}, {'name': 'other', 'asset': {'id': 'Camera_01'}}, {'name': 'x', 'find': 'star map', 'asset': {'id': 'ox-1'}}]}, was)
    assert [o['name'] for o in got['objects']] == ['x'] and ps.drop_rejected({'objects': [{'name': 'y'}]}, None)['objects'] == [{'name': 'y'}]


def test_the_plan_fits_the_work():
    import agent_features as af
    assert 'THIS IS A GAME' in af.plan_sys('make me a playable game') and 'THIS IS A SHOP' in af.plan_sys('a store with a checkout') and 'THIS IS A COIN PAGE' in af.plan_sys('landing page for my memecoin')
    assert af.plan_sys('something odd') == af.PLAN_SYS and 'the hook' in af.ANSWER_SHAPES['content'] and 'Build it:' in af.CONTENT_SYS and 'THE PLAN' in af.ANSWER_SHAPES['research']


def test_users_read_the_collective_not_the_internal_minds():
    import feecat_service as fs
    got = fs._as_collective({'talk': [{'by': 'OSSY', 'text': 'g4 agrees with ossy'}], 'n': 3, 'ok': True, 'rows': ['fine']})
    assert got == {'talk': [{'by': 'The Collective', 'text': 'The Collective agrees with The Collective'}], 'n': 3, 'ok': True, 'rows': ['fine']}


REAL_EDIT = 'find a kit that uses a good example of "the core"and put it under that section, and add some thing vital under "the descent"'
PAGE = {'headline': 'GRAVEWELL', 'sub': 'Eats jeets', 'cta': 'Enter', 'sections': [{'title': 'The Descent', 'body': 'Down'}, {'title': 'The Core', 'body': '60% burned'}]}


def test_the_owners_real_edit_changes_only_what_he_asked():
    now = ps.clean_scene({'mood': 'space', 'hero': 'blackhole', 'world': 'nebula', 'tint': '#00e5ff', 'objects': [{'find': 'torn metal fragment', 'pos': [1, 0, 0]}], 'page': PAGE})
    reply = {'say': 'x', 'brief': {'mood': 'noir', 'hero': 'torn metal fragment', 'props': ['old leather books', 'wooden crate'], 'page': {'headline': 'The Core', 'sub': 'One fragment', 'sections': [{'title': 'The Core', 'body': 'New', 'widget': 'donut', 'data': [['Burned', 60], ['Presale', 40]]}, {'title': 'The Descent', 'widget': 'steps', 'data': ['Find the mint', 'Check the pool']}]}}}
    got, _ = ps.parse_reply(json.dumps(reply), now, REAL_EDIT)
    assert got['mood'] == 'space' and got['hero'] == 'blackhole' and got['page']['headline'] == 'GRAVEWELL' and got['page']['sub'] == 'Eats jeets'
    assert [o['name'] for o in got['objects']] == ['torn metal fragment']   # no crate, no books, no second fragment
    rows = {x['title']: x for x in got['page']['sections']}; assert list(rows) == ['The Descent', 'The Core'] and rows['The Core']['widget'] == 'donut' and rows['The Descent']['widget'] == 'steps'
    html = ps.to_html(got, 'G'); assert 'wg-donut' in html and 'wg-steps' in html and 'Find the mint' in html
    assert not ps.ASKS_DASH.search(REAL_EDIT) and 'dash' not in got['page']   # "vital" is not a chart
    assert '60%' in html or '60' in html


def test_a_section_cannot_smuggle_a_script():
    sc = ps.clean_scene({'objects': [{'name': 'a', 'shape': 'box'}], 'page': {'headline': 'H', 'sections': [{'title': 'A', 'body': 'b', 'html': '<script>x()</script>'}, {'title': 'B', 'body': 'b', 'html': '<img src=x onerror=y>'}, {'title': 'C', 'body': 'b', 'html': '<svg viewBox="0 0 1 1"></svg>'}]}})
    assert [bool(x.get('html')) for x in sc['page']['sections']] == [False, False, True]


def test_no_two_new_requests_get_the_same_print_and_the_model_cannot_pick_its_favourite():
    used = []
    for i in range(30):
        pr = ps.creative_print(f's{i}', used, 'a landing page for my brand'); used.append(pr)
    keys = [(p['mood'], tuple(p['font']), p['type'], p['cta'], p['layout']) for p in used]
    assert len(set(keys)) == 30 and len({p['mood'] for p in used}) == len(ps.MOODS)
    pr = {'mood': 'beach', 'layout': 'right', 'font': ['oswald', 700], 'type': 'outline', 'cta': 'line', 'mirror': True}
    made = ps.apply_print(ps.clean_scene(ps.from_brief({'mood': 'noir', 'hero': 'chair'}, 'x')), pr)
    assert made['mood'] == 'beach' and made['style']['font'] == ['oswald', 700]
    html = ps.to_html(made, 'N'); assert 'ty-outline' in html and 'cta-line' in html and 'oswald' in html and 'dl.polyhaven' not in html.split('const SITE')[0]
    keep = ps.apply_print(ps.clean_scene(ps.from_brief({'mood': 'space', 'centerpiece': 'blackhole'}, 'x')), pr); assert keep['mood'] == 'space'


def test_going_back_clears_after_that_page_and_hands_the_request_back():
    import agent_features as af
    page = lambda n: {'html': ps.to_html(ps.clean_scene({'mood': 'neon', 'objects': [{'name': f'thing{n}', 'shape': 'box'}], 'page': {'headline': f'H{n}'}}), 'x'), 'by': 'A', 'at': n}
    doc = {'versions': [page(1), page(2), page(3)], 'messages': [{'by': 'you', 'text': 'first'}, {'by': 'A', 'text': 'Page 1 is ready.'}, {'by': 'you', 'text': 'add a sword'}, {'by': 'A', 'text': 'Page 2 is ready.'}, {'by': 'you', 'text': 'go back and rety my request from page 1'}, {'by': 'A', 'text': 'Page 3 is ready.'}]}
    assert af.go_back_to('go back and rety my request from page 5', 7) == (5, True) and af.go_back_to('go back to page 2', 7) == (2, False) and af.go_back_to('go back to page 9', 7) is None and af.go_back_to('add a page 2 with a form', 7) is None
    got = af.rewind(doc, 1)
    assert got['request'] == 'add a sword' and len(doc['versions']) == 1 and len(got['cut']) == 2 and [m['text'] for m in doc['messages']] == ['first', 'Page 1 is ready.'] and not doc['busy']
    first, second = ps.scene_from_html(doc['versions'][0]['html']); assert ps.clean_scene(first)['objects'][0]['name'] == 'thing1' and second is None
    game = ps.to_html(ps.clean_scene(ps.from_brief({'mood': 'neon', 'game': 'runner', 'player': 'robot'})), 'R'); assert ps.clean_scene(ps.scene_from_html(game)[0])['game'] == 'runner'


def test_a_game_pick_is_never_sent_to_a_rug_checker_and_its_sites_change():
    import cat_agent as ca, cat_policy as cp, pob, proof_footprint as pf, proof_plan as pl
    assert 'site_search' in cp.RESEARCH_ACTIONS and 'site_search' in ca.ACT_SYS and 'rugcheck' not in pob.goal([{'sym': 'WIF'}]).lower()
    assert 'site_search' in pl.goal_for_bid('Lakers vs Kings', ['espn.com'])
    sites = pob.sites_for('nba lakers'); assert len(sites) >= 12 and 'rugcheck.xyz' not in sites
    firsts = {pf.plan('pob', f'nba game {i}', sites, [{'id': str(k)} for k in range(i)])['sites'][0][0] for i in range(12)}; assert len(firsts) >= 4   # espn is not first every time


def test_a_prompt_placeholder_never_lands_on_the_page_and_nothing_stands_inside_a_black_hole():
    got = ps.keep_page(PAGE, {'sections': [{'title': 'The Core', 'body': 'One line', 'widget': 'donut'}]}, 'put it under the core')
    assert next(x for x in got['sections'] if x['title'] == 'The Core')['body'] == '60% burned'
    assert ps.clean_scene({'objects': [{'name': 'a', 'shape': 'box'}], 'page': {'headline': 'H', 'sections': [{'title': 'A', 'body': 'One line'}]}})['page']['sections'][0]['body'] == ''
    sc = ps.lead_up({'mood': 'space', 'hero': 'blackhole', 'objects': [{'name': 'x', 'asset': {'id': 'x'}, 'pos': [0, 0, 0]}, {'name': 'y', 'asset': {'id': 'y'}, 'pos': [4, 0, -3]}]})
    assert [o['name'] for o in sc['objects']] == ['y']


def test_a_matchup_goes_to_sports_sites_even_with_no_league_named():
    import pob
    for topic in ('Nets vs Hawks', 'Chiefs vs Bills', 'Yankees at Dodgers', 'Oilers vs Stars', 'Arsenal vs Chelsea'):
        got = pob.sites_for(topic); assert 'wikipedia.org' not in got and 'npr.org' not in got and any(x in got for x in ('espn.com', 'covers.com')), topic
    assert 'nba.com' in pob.sites_for('Nets vs Hawks') and 'nfl.com' in pob.sites_for('Chiefs vs Bills')
    assert 'wikipedia.org' in pob.sites_for('who wins the oscar for best film')


def test_what_a_mind_says_it_read_gets_a_box():
    import asyncio
    import cat_agent as ca
    import evidence_marks as em
    assert em.mark_words({'mark': ['Nets +4.5', 'x'], 'facts': [{'label': 'odds', 'value': '-110'}]}) == ['nets +4.5', '-110'] and em.mark_words({'mark': 'Hawks 112'}) == ['hawks 112'] and em.mark_words({}) == [] and em.mark_words(None) == []
    assert '"mark"' in ca.ACT_SYS
    drawn = []
    class Live:
        async def draw_marks(self, js):
            drawn.append(js); return {'rects': [[1, 2, 3, 4]], 'found': {'nets': 1}} if 'createTreeWalker' in js else {'n': 1, 'pts': [[0.5, 0.4]]}
    class Reader:
        pass
    assert asyncio.run(em.live_marks(Live(), ['nets', 'hawks'])) == {'n': 1, 'pts': [[0.5, 0.4]], 'found': ['nets']} and 'feeless-marks' in drawn[-1] and 'pointer-events:none' in drawn[-1]
    assert asyncio.run(em.live_marks(Reader(), ['nets']))['n'] == 0
    class Broken:
        async def draw_marks(self, js):
            raise RuntimeError('page gone')
    assert asyncio.run(em.live_marks(Broken(), ['nets']))['n'] == 0   # a box never stops the work


def test_the_public_print_shows_only_basic_facts_and_only_active_proofs_glow(monkeypatch, tmp_path):
    import feecat_service as fs, json as _j
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path); now = 1_800_000_000
    store = {'cats': {'secretcat': {'id': 'secretcat', 'name': 'Secret Agent Name', 'powFolders': [
        {'id': 'p1', 'at': now - 5 * 86400, 'status': 'closed', 'pnlPct': 40, 'sym': 'SECRETCOIN', 'mint': 'SECRETMINT', 'shots': [{'site': 'secret-site.com'}], 'talk': [{'text': 'secret reasoning'}]},
        {'id': 'p2', 'at': now - 9 * 86400, 'status': 'closed', 'pnlPct': -3},
        {'id': 'p3', 'at': now - 86400 * 9, 'status': 'open'},
        {'id': 'p4', 'at': now - 3600, 'status': 'closed'},
        {'id': 'p5', 'at': now - 86400 * 20, 'status': 'closed'},
        {'id': 'x', 'at': now, 'status': 'closed', 'noTrade': True}]},
        'hidden': {'id': 'hidden', 'incognito': True, 'powFolders': [{'id': 'h', 'at': now, 'status': 'closed'}]}}}
    rows = fs._atoms_public(store, {'p5'}, now); text = _j.dumps(rows)
    assert len(rows) == 5 and all(set(r) == {'id', 'kind', 'rank', 'result', 'age', 'active'} for r in rows)
    for secret in ('Secret', 'SECRET', 'secret', 'p1'):
        assert secret not in text
    assert [r['active'] for r in rows] == [False, False, True, True, True]   # running, filed today, and in the Pool. Old closed proofs do not glow
    assert [r['result'] for r in rows][:3] == ['won', 'lost', 'open'] and rows[0]['age'] == 5 and rows[0]['kind'] == 'PoW'


def _row(i, **k):
    return {'id': i, 'cats': [], 'free': False, 'vision': False, 'tools': True, 'json': True, 'ctx': 100000, 'intel': None, 'coding': None, 'agentic': None, **k}


def test_model_discovery_finds_all_rounders_and_masters_from_real_scores_and_blanks_stay_unplaced():
    import launch_cat as lc
    rows = [_row(f'c{i}', coding=90 - i) for i in range(12)] + [_row('allround', intel=95, coding=99, agentic=95, vision=True), _row('nothing'), _row('agents', agentic=99, intel=10)]
    lc.place_proofs(rows); by = {r['id']: r for r in rows}
    assert 'any-proof' in by['allround']['cats'] and 'master' not in by['allround']['cats']
    assert by['c0']['masterOf'] == ['pos'] and 'master' in by['c0']['cats'] and by['nothing']['cats'] == [] and 'masterOf' not in by['nothing']
    assert lc.fit_score(by['nothing'], 'pos') is None and lc.fit_score({**by['c0'], 'vision': True}, 'pos') > lc.fit_score(by['c0'], 'pos')
    assert set(lc.CATS) >= {'any-proof', 'master', 'best-pos', 'best-poc', 'best-pow', 'best-pop', 'best-pob'}


def test_a_model_is_warned_about_never_blocked_and_one_mind_that_can_see_is_enough(monkeypatch):
    import launch_cat as lc, feecat_service as fs
    assert 'cannot see pictures' in lc.limits_of({'vision': False, 'ctx': 100000}, 'pos')[0] and lc.limits_of({'vision': True, 'ctx': 100000}, 'pos') == [] and lc.limits_of(None) == []
    assert 'its reports' in lc.limits_of({'tools': False, 'json': False}, 'pob')[0]
    monkeypatch.setitem(fs._MODELS, 'rows', {'models': [{'id': 'a/blind', 'vision': False, 'ctx': 100000}, {'id': 'b/sees', 'vision': True, 'ctx': 100000}]})
    cat = lambda *b: {'brainsCfg': {'brains': list(b)}}
    assert 'blind cannot see' in fs._fit_line(cat('a/blind'), 'pos') and fs._fit_line(cat('a/blind', 'b/sees'), 'pos') == '' and fs._fit_line(cat('unknown/model'), 'pos') == ''


def test_a_mind_looking_at_its_page_can_only_make_small_safe_fixes():
    sc = ps.clean_scene({'mood': 'noir', 'layout': 'left', 'camera': [2, 1, 5], 'tint': '#ffffff', 'objects': [{'name': 'Chair', 'asset': {'id': 'c', 'url': 'https://dl.polyhaven.org/c.gltf'}, 'pos': [0, 0, 0]}, {'name': 'Crate', 'asset': {'id': 'd', 'url': 'https://dl.polyhaven.org/d.gltf'}, 'pos': [1, 0, 0]}], 'page': {'headline': 'H'}})
    got, say = ps.apply_look(sc, json.dumps({'say': 'The crate covers the words', 'layout': 'right', 'remove': ['Crate'], 'closer': True, 'headline': 'HACKED', 'mood': 'neon'}))
    assert say.startswith('The crate') and got['layout'] == 'right' and [o['name'] for o in got['objects']] == ['Chair'] and got['camera'][2] < 5 and got['mood'] == 'noir' and got['page']['headline'] == 'H'
    assert ps.apply_look(sc, json.dumps({'say': 'It looks right'})) == (None, 'It looks right') and ps.apply_look(sc, 'no json')[0] is None
    only, _ = ps.apply_look(sc, json.dumps({'remove': ['Chair', 'Crate']})); assert only is None   # it may not empty its own set


def test_the_collective_stash_reaches_minds_only_as_method(tmp_path):
    import collective_stash as st, agent_refs as ar
    st.put(tmp_path, 'k1', 'Code', 'x.com', 'cat-a', 'won', 'black hole landing page', json.dumps({'plan': 'One strong centerpiece, words low on the left'}).encode())
    st.put(tmp_path, 'k2', 'Code', 'x.com', 'cat-b', 'lost', 'black hole bad page', json.dumps({'plan': 'crowded'}).encode())
    rows = st.best_for(tmp_path, ['black', 'hole'])
    assert len(rows) == 1 and rows[0]['gist'].startswith('One strong')
    line = ar.best_line(rows, 'someone'); assert 'do not quote' in line and 'a winning proof' in line and 'cat-a' not in line and ar.best_line([]) == ''


def test_a_page_can_carry_a_minds_own_code_and_only_the_kits_it_used():
    html = ps.to_html(ps.clean_scene({'mood': 'noir', 'objects': [{'name': 'a', 'shape': 'box'}], 'code': {'js': 'addEventListener("feeless",e=>{})'}}), 'N')
    assert "new CustomEvent('feeless'" in html and 'onFrame' in html
    locked = ps.lock_site(html, ['gsap', 'nope']); assert 'gsap' in locked and 'nope' not in locked and locked.count('Content-Security-Policy') == 1
    assert 'gsap' not in ps.lock_site(html)


def test_a_window_that_repeats_on_a_game_goes_to_another_sports_site_never_a_coin_checker():
    import asyncio
    import cat_agent as ca
    class Page:
        url = 'https://espn.com/nba'; title = 't'
        async def goto(self, u):
            self.url = u; return 'page'
    w = {'i': 0, 'steps': [{'detail': 'https://espn.com/nba'}], 'goal': 'Rangers vs Kraken'}
    asyncio.run(ca._divert({'research': True, 'notCoins': True, 'alts': ['https://birdeye.so'], 'alsoHosts': ['espn.com', 'theathletic.com', 'oddsshark.com']}, w, Page()))
    assert w['url'] == 'https://theathletic.com'   # the general source book (Birdeye) never takes a game pick
    w2 = {'i': 0, 'steps': [{'detail': x} for x in ('https://espn.com', 'https://theathletic.com', 'https://oddsshark.com')], 'goal': 'g'}
    asyncio.run(ca._divert({'research': True, 'notCoins': True, 'alsoHosts': ['espn.com', 'theathletic.com', 'oddsshark.com']}, w2, Page()))
    assert 'rugcheck' not in w2['url'] and 'jup.ag' not in w2['url'] and 'dexscreener' not in w2['url']



def test_every_model_used_gets_a_fingerprint_score_from_its_own_record():
    import feecat_service as fs
    store = {'cats': {'a': {'brainsCfg': {'brains': ['z-ai/glm-5.3-flash', 'openai/gpt-6.1-terra'], 'decisions': [{'by': 'glm-5.3-flash', 'word': 'BUY'}]},
                            'pobFolders': [{'id': 'p1', 'graded': 'right', 'calls': [{'mind': 0, 'name': 'glm-5.3-flash'}, {'mind': 1, 'name': 'Mind B'}]}],
                            'psFolders': [{'id': 's1', 'by': 'Mind A', 'graded': 'wrong'}]}}}
    rows = {r['id']: r for r in fs.model_prints(store)}
    assert set(rows) == {'z-ai/glm-5.3-flash', 'openai/gpt-6.1-terra'}   # "Mind B" is its seat's model, never a model of its own
    g = rows['z-ai/glm-5.3-flash']; assert g['n'] == 3 and g['right'] == 1 and g['wrong'] == 1 and g['kinds'] == ['pob', 'pos', 'trade']
    assert 0 < rows['openai/gpt-6.1-terra']['score'] < g['score'] <= 100


def test_talking_picks_which_mind_answers():
    import feecat_service as fs
    b = {'brains': ['local/ossy', 'local/g4'], 'mindNames': ['OSSY', 'G4']}
    assert fs.talk_targets(b, 'both') == [0, 1] and fs.talk_targets(b, '1') == [1] and fs.talk_targets({'brains': ['x']}, '1') == [] and fs.mind_name(b, 1) == 'G4'
