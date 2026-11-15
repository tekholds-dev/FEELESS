"""🎮 owner 2026-11-15: the Game lab folder — playtests, porting checklists, a real FiveM / RedM resource starter."""
import pytest
import game_lab as gl


def test_a_playtest_is_logged_cleanly_and_bad_ones_refused():
    st = gl.apply({}, {'log': {'game': 'Night Run', 'platform': 'vita', 'fps': 58.7, 'bugs': ['crash on level 2', ' '], 'verdict': 'fix'}}, now=100)
    r = st['log'][0]
    assert (r['game'], r['platform'], r['fps'], r['bugs'], r['at']) == ('Night Run', 'vita', 58, ['crash on level 2'], 100)
    with pytest.raises(ValueError):
        gl.apply({}, {'log': {'game': 'x', 'platform': 'xbox-cracked'}})
    assert gl.apply(st, {'drop': r['id']})['log'] == []


def test_porting_steps_tick_and_untick():
    st = gl.apply({}, {'check': 'fivem', 'step': 2})
    assert st['checks']['fivem'] == [2]
    assert gl.apply(st, {'check': 'fivem', 'step': 2})['checks']['fivem'] == []
    with pytest.raises(ValueError):
        gl.apply({}, {'check': 'fivem', 'step': 99})


def test_the_resource_starter_is_a_real_fivem_and_redm_resource():
    r = gl.resource('My Garage!', 'gta5', 'Park cars')
    assert r['name'] == 'my_garage' and set(r['files']) == {'fxmanifest.lua', 'config.lua', 'client.lua', 'server.lua'}
    m = r['files']['fxmanifest.lua']
    assert "fx_version 'cerulean'" in m and "game 'gta5'" in m and 'rdr3_warning' not in m
    assert "RegisterNetEvent('my_garage:hello'" in r['files']['server.lua'] and 'ensure my_garage' in r['install']
    assert "rdr3_warning '" in gl.resource('ranch', 'rdr3')['files']['fxmanifest.lua']
