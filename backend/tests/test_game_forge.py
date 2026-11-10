"""AGT-35: a game is designed, written on a real engine, played by a headless browser, fixed by the other mind with the failures AND the
code, and filed only when it passes. Found live 2026-11-10: a reasoning model spent a whole page budget thinking and wrote nothing."""
import asyncio
import json

import pytest

import game_forge as gf

DESIGN = {'title': 'Rugpull Run', 'genre': 'shooter', 'engine': 'phaser', 'pitch': 'dodge red, shoot green', 'coreLoop': 'weave and shoot',
          'controls': {'keys': 'arrows + space', 'touch': 'drag + tap'}, 'win': 'score', 'lose': 'three hits', 'progression': ['faster'], 'juice': ['shake'],
          'entities': ['ship', 'candle'], 'screens': ['title', 'play', 'over']}


def test_design_is_parsed_cleaned_and_must_have_a_loop_and_controls():
    d = gf.design_of('here you go ```json\n' + json.dumps(DESIGN) + '\n```')
    assert d['engine'] == 'phaser' and d['controls']['touch'] == 'drag + tap' and d['title'] == 'Rugpull Run'
    assert gf.design_of(json.dumps({**DESIGN, 'engine': 'unity'}))['engine'] in gf.ENGINES   # never an engine it cannot load
    for bad in ('no json', json.dumps({**DESIGN, 'coreLoop': ''}), json.dumps({**DESIGN, 'controls': {}})):
        with pytest.raises(ValueError):
            gf.design_of(bad)


def test_the_build_brief_pins_the_engine_and_the_hook():
    b = gf.build_sys(gf.design_of(json.dumps(DESIGN)))
    assert 'phaser@3.80.1' in b and 'window.__game' in b and 'touch' in b and 'Rugpull Run' in b
    assert 'THE CURRENT' not in b and 'FAILED THE PLAYTEST' in gf.fix_sys(gf.design_of(json.dumps(DESIGN)), {'why': ['no canvas']})
    assert gf.html_of('Sure!\n```html\n<!doctype html><html></html>\n```') == '<!doctype html><html></html>'


def test_fail_fix_pass_then_file(monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, '_ws_save', lambda *a: None); monkeypatch.setattr(fs, '_parts_used', lambda *a: [])
    asks = []
    async def ask(cat, model, sys_, user_, tokens):
        asks.append(('design', model)); return json.dumps(DESIGN), 0.001, False
    async def page(cat, model, sys_, user_, tokens, on_part=None):
        asks.append(('fix' if 'FAILED THE PLAYTEST' in sys_ else 'build', model, 'THE CURRENT FILE' in user_)); return f'<!doctype html><html><body>{len(asks)}</body></html>', 0.01, False
    plays = iter([{'ok': False, 'why': ['no canvas was drawn'], 'facts': {}}, {'ok': True, 'why': [], 'facts': {'fps': 60, 'changed': 900, 'after': {'state': 'play'}}}])
    async def play(html, chromium):
        return next(plays)
    monkeypatch.setattr(fs, '_ws_ask', ask); monkeypatch.setattr(fs, '_ws_page', page); monkeypatch.setattr(fs._forge, 'playtest', play); monkeypatch.setattr(fs._fb, 'chromium_path', lambda: 'x')
    doc = {'id': 'w', 'messages': [], 'versions': []}
    cost, why, own = asyncio.run(fs._build_game({'id': 'c'}, doc, 'a shooter game', ['a/one', 'b/two'], [0, 1], lambda i: 'Mind ' + 'AB'[i], 'both'))
    assert why is None and len(doc['versions']) == 1 and doc['versions'][0]['by'] == 'Mind B' and round(cost, 3) == 0.021
    assert asks == [('design', 'a/one'), ('build', 'a/one', False), ('fix', 'b/two', True)]   # the fixer gets the failing code
    assert doc['game']['engine'] == 'phaser' and doc['kitsUsed'] == [{'id': 'phaser', 'name': 'Phaser 3', 'used': True}]
    assert 'Passed' in doc['messages'][-1]['text'] and 'Failed: no canvas' in doc['messages'][-2]['text']


def test_a_game_that_keeps_failing_is_never_filed(monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, '_ws_save', lambda *a: None)
    async def ask(*a): return json.dumps(DESIGN), 0.0, False
    async def page(*a, **k): return '<!doctype html><html></html>', 0.0, False
    async def play(html, chromium): return {'ok': False, 'why': ['nothing on screen changed while keys were pressed'], 'facts': {}}
    monkeypatch.setattr(fs, '_ws_ask', ask); monkeypatch.setattr(fs, '_ws_page', page); monkeypatch.setattr(fs._forge, 'playtest', play); monkeypatch.setattr(fs._fb, 'chromium_path', lambda: 'x')
    doc = {'id': 'w', 'messages': [], 'versions': []}
    _c, why, _o = asyncio.run(fs._build_game({'id': 'c'}, doc, 'a game', ['a', 'b'], [0, 1], lambda i: 'Mind ' + 'AB'[i], 'both'))
    assert doc['versions'] == [] and 'failed its playtest' in why and doc['messages'][-1]['text'].startswith('Not filed')


def test_a_long_write_turns_thinking_off_and_retries_when_it_still_only_thinks(monkeypatch):
    import feecat_service as fs
    sent = []
    class R:
        def __init__(self, body): self.status_code, self._b = 200, body
        def json(self): return self._b
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers=None, json=None):
            sent.append(json.get('reasoning'))
            if len(sent) == 1:
                return R({'choices': [{'finish_reason': 'length', 'message': {'content': ''}}], 'usage': {'cost': 0.007}})
            return R({'choices': [{'finish_reason': 'stop', 'message': {'content': '<html>game</html>'}}], 'usage': {'cost': 0.002}})
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **k: H())
    text, usd = asyncio.run(fs._or_call('z-ai/glm', [{'role': 'user', 'content': 'x'}], max_tokens=12000, key='k'))
    assert text == '<html>game</html>' and round(usd, 6) == 0.009 and sent == [{'enabled': False}, {'max_tokens': 300}]   # both calls' cost counted
    sent.clear(); asyncio.run(fs._or_call('z-ai/glm', [{'role': 'user', 'content': 'x'}], max_tokens=600, key='k'))
    assert sent[0] is None   # a short decision keeps the model's own thinking


def test_every_engine_kit_passes_the_real_playtest():
    """Each kit is what a mind builds on: it must already play (real headless Chromium, the same gate a game must pass)."""
    import free_browser as fb
    chromium = fb.chromium_path()
    if not chromium:
        pytest.skip('no Chromium on this machine')
    for eng in gf.ENGINES:
        r = asyncio.run(gf.playtest(gf.kit_of(eng), chromium))
        fps_only = lambda r_: r_['why'] and all('frames a second' in w for w in r_['why'])
        if not r['ok'] and fps_only(r):   # the gate runs 4 workers beside it: frame rate is load, not the kit (2026-11-10, 13 fps under the gate, 60 alone)
            r = asyncio.run(gf.playtest(gf.kit_of(eng), chromium))
        assert r['ok'] or (fps_only(r) and (r['facts'].get('fps') or 0) > 0), (eng, r['why'])   # it must still start, move, change and draw
        assert 'GAME LOGIC GOES HERE' in gf.kit_of(eng) and 'window.__game' in gf.kit_of(eng)
