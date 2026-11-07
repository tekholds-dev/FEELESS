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
    got = ps.ensure_asks(GLINT_HOME, 'still no charts and real number data')
    d = got['page']['dash']; assert len(d['points']) > 10 and len(d['stats']) == 4 and 'Sample' in d['note'] and got['page']['cta'] == 'Enter the room'
    assert ps.ensure_asks(ROOM, 'a chart') is ROOM and ps.ensure_asks(GLINT_HOME, 'make it darker') is GLINT_HOME
    assert ps.page_facts(got, ROOM) == 'Home page: a chart and 4 numbers; Room: a chart and 3 numbers, a back button.'
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
    d = ps.ensure_asks(thin, 'a chart')['page']['dash']; assert d['stats'][0]['value'] == '$0.042' and len(d['stats']) == 4 and len(d['points']) > 8


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
    more, _ = ps.parse_reply(json.dumps({'add': ['old books'], 'mood': 'neon'}), now)
    assert more['mood'] == 'neon' and [o['name'] for o in more['objects']] == ['chair', 'old books']


def test_every_mood_and_template_is_real():
    import asset_packs as a
    for k, m in ps.MOODS.items():
        assert m['skies'] and m['font'] and m['set'] in ('place', 'studio', 'far')
    for t in ps.TEMPLATES:
        assert t['brief']['mood'] in ps.MOODS and ps.template_scene(t['id'])['objects']
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
