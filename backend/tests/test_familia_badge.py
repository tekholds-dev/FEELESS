import pytest
import crews as cr

W = 'Own1111111111111111111111111111111111111111'


def _st():
    st = {}
    c = cr.create(st, W, 'Sicario', 'SIC', 0)
    return st, c


def test_metrics_read_the_weekly_awards_and_bounty_points():
    st, c = _st(); c['points'] = {W: 300, 'x': 250}
    aw = [{'week': 1, 'top': [{'id': c['id']}, {'id': 'b'}]}, {'week': 2, 'top': [{'id': 'b'}, {'id': 'z'}, {'id': c['id']}]}]
    assert cr.family_metrics(c, aw) == {'members': 1, 'podiums': 2, 'crowns': 1, 'best': 1, 'points': 550, 'wars': 0}


def test_locked_parts_are_refused_and_free_ones_build_once_then_restyle_needs_payment():
    st, c = _st()
    with pytest.raises(ValueError, match='locked'):
        cr.set_badge(st, W, {'emblem': 'crown'}, [], 1)
    cr.set_badge(st, W, {'emblem': 'rose', 'frame': 'iron', 'fx': 'none', 'c1': '#15d16a', 'c2': '#ffd36b', 'motto': 'Famiglia first'}, [], 1)
    assert c['badge']['emblem'] == 'rose' and c['badge']['v'] == 1
    with pytest.raises(ValueError, match='payment'):
        cr.set_badge(st, W, {'emblem': 'skull'}, [], 2)
    cr.set_badge(st, W, {'emblem': 'skull'}, [], 2, paid={'sig': 's1', 'usd': 2})
    assert c['badge']['v'] == 2 and 's1' in st['sigs']


def test_crown_unlocks_from_a_real_crown_and_the_creator_can_move_a_line():
    st, c = _st(); aw = [{'week': 1, 'top': [{'id': c['id']}]}]
    assert cr.clean_badge({'emblem': 'crown', 'frame': 'blood', 'fx': 'lightning'}, cr.family_metrics(c, aw))['frame'] == 'blood'
    cfg = {'unlocks': {'emblem.crown': {'metric': 'crowns', 'min': 3}}}
    with pytest.raises(ValueError):
        cr.clean_badge({'emblem': 'crown'}, cr.family_metrics(c, aw), cfg)
    c['badge'] = {'emblem': 'crown', 'frame': 'blood', 'fx': 'none'}
    assert cr.badge_view(c, aw, cfg)['emblem'] == 'rose'          # raised later → falls back, never shown unearned
    assert not [r for r in cr.catalog(cr.family_metrics(c, aw), cfg)['emblem'] if r['key'] == 'crown'][0]['ok']
