"""Owner 2026-11-10: the stash's kits always fresh, never stale. A newer version moves the pin only after it is a week old and its real CDN file
passes a smoke test; a pin that stops loading rolls back; three moves for every kit that shares it."""
import asyncio
import copy

import collective_kits as ck
import kit_fresh as kf

DAY = 86400


def test_want_moves_only_to_a_newer_settled_release():
    now = 100 * DAY
    assert kf.want('major', '5', '6.1.0', now - 8 * DAY, now) == '6'
    assert kf.want('major', '6', '6.9.0', now - 8 * DAY, now) is None          # same major: the CDN already serves it
    assert kf.want('major', '12', '14.0.0', now - 1 * DAY, now) is None        # too young
    assert kf.want('exact', '0.170.0', '0.187.0', now - 9 * DAY, now) == '0.187.0'
    assert kf.want('exact', '1.0.0', '2.0.0-beta.1', now - 30 * DAY, now) is None   # never a pre-release


def test_a_pass_moves_tested_pins_rolls_back_broken_ones(monkeypatch, tmp_path):
    use = copy.deepcopy(ck.KIT_USE)
    vers = {'three': ('0.187.0', DAY), 'echarts': ('6.1.0', DAY), 'konva': ('10.9.1', DAY)}
    async def latest(http, pkg):
        return vers.get({'three': 'three', 'echarts': 'echarts', 'konva': 'konva'}.get(pkg, ''), (None, None))
    monkeypatch.setattr(kf, 'latest', latest)
    async def smoke(html, expr): return ('konva@10' not in html), 'boom'
    rows = asyncio.run(kf.run(None, use, tmp_path, smoke, now=30 * DAY))
    got = {r['kit']: r['ok'] for r in rows}
    assert got == {'echarts': True, 'three': True, 'konva': False}
    assert kf.current(use, 'echarts') == '6' and kf.current(use, 'konva') == '9'
    assert '@0.187.0/' in use['r3f']['tags'][0] and 'three@0.187.0/examples/jsm/' in use['three']['tags'][0]   # shared + addons path
    fresh = copy.deepcopy(ck.KIT_USE); assert kf.apply(fresh, kf.load(tmp_path)) == 2 and kf.current(fresh, 'three') == '0.187.0'   # a restart keeps them
    async def broken(html, expr): return ('echarts@6' not in html), 'echarts 6 no longer loads'
    rows = asyncio.run(kf.run(None, use, tmp_path, broken, now=31 * DAY))
    assert any(r.get('rollback') and r['kit'] == 'echarts' for r in rows) and kf.current(use, 'echarts') == '5'


def test_every_tracked_kit_is_a_real_page_kit_and_new_kits_are_catalogued():
    for kid in kf.TRACK:
        assert kid in ck.KIT_USE and kf.current(ck.KIT_USE, kid), kid
    for kid in ('phaser', 'matter', 'howler', 'tone', 'anime', 'particles', 'marked', 'tabulator', 'leaflet'):
        assert kid in ck.CATALOG and kid in ck.USES and ck.CATALOG[kid]['license'] in ('MIT', 'BSD-2-Clause')
    html, expr = kf.smoke_page(ck.KIT_USE['heroui']['tags'], 'css'); assert 'onload=' in html and expr == 'window.__css > 0'
    html, expr = kf.smoke_page(ck.KIT_USE['three']['tags'], 'module:three:Scene'); assert 'import * as M from "three"' in html


def test_no_startup_hook_is_an_endless_loop():
    """2026-11-10: a decorator landed on the daily loop itself, so start-up never finished (every TestClient hung; a restart would have too).
    A startup hook starts its loop with create_task; it never runs one."""
    import inspect
    import feecat_service as fs
    for h in fs.app.router.on_startup:
        src = inspect.getsource(h)
        assert 'while True' not in src, h.__name__
