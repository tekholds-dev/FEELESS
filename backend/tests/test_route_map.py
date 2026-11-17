"""🗺 cleanup 2026-11-17: the gate's route map. Moving code between modules must never change which function answers a route."""
import importlib.util
import pathlib

_p = pathlib.Path(__file__).resolve().parents[2] / 'scripts' / 'route-map.py'
_s = importlib.util.spec_from_file_location('route_map', _p); rm = importlib.util.module_from_spec(_s); _s.loader.exec_module(rm)


def test_a_route_that_reaches_another_function_or_none_is_red_and_a_new_one_is_only_listed():
    base = {'GET       /api/cats': 'list_cats', 'POST      /api/cats/x1y/action': 'cat_action', 'GET       /api/cats/old': 'old_view'}
    now = {'GET       /api/cats': 'list_cats', 'POST      /api/cats/x1y/action': 'cat_recover', 'GET       /api/cats/new': 'new_view'}
    bad, new = rm.compare(base, now)
    assert bad == ['GET       /api/cats/old: was old_view, now gone', 'POST      /api/cats/x1y/action: was cat_action, now cat_recover']
    assert new == ['GET       /api/cats/new']
    assert rm.compare(base, dict(base)) == ([], [])


def test_the_saved_map_reads_back_exactly():
    m = {'GET       /api/cats': 'list_cats', 'WEBSOCKET /api/cats/x1y/stream': 'cat_stream'}
    assert rm.parse(rm.render(m)) == m
