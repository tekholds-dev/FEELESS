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


def test_crest_layers_shape_field_banner_are_free_and_the_charge_keeps_its_adjustments():
    st, c = _st(); met = cr.family_metrics(c, [])
    b = cr.clean_badge({'shape': 'kite', 'field': 'quarterly', 'banner': 'scroll', 'emblem': 'skull', 'c3': '#D4AF37', 'es': 1.18, 'er': -12, 'ef': 1}, met)
    assert (b['shape'], b['field'], b['banner'], b['c3'], b['es'], b['er'], b['ef']) == ('kite', 'quarterly', 'scroll', '#d4af37', 1.18, -12, True)
    # out-of-range adjustments are clamped, junk falls back to the default — never refused
    b = cr.clean_badge({'es': 9, 'er': -400, 'ef': 0}, met)
    assert (b['es'], b['er'], b['ef']) == (1.3, -30, False)
    assert cr.clean_badge({'es': 'big', 'er': None}, met)['es'] == 1.0
    with pytest.raises(ValueError):
        cr.clean_badge({'shape': 'pentagram'}, met)
    with pytest.raises(ValueError, match='palette'):
        cr.clean_badge({'c3': '#123456'}, met)
    # changing the shape keeps the charge's adjustments (they are separate keys)
    cr.set_badge(st, W, {'shape': 'heater', 'emblem': 'rose', 'es': 0.8, 'er': 20}, [], 1)
    cr.set_badge(st, W, {**c['badge'], 'shape': 'coin'}, [], 2, paid={'sig': 's2', 'usd': 2})
    v = cr.badge_view(c, [])
    assert (v['shape'], v['es'], v['er']) == ('coin', 0.8, 20)


def test_an_old_badge_reads_with_crest_defaults_and_every_listed_colour_pair_is_in_the_palette():
    st, c = _st(); c['badge'] = {'emblem': 'dice', 'frame': 'iron', 'fx': 'none', 'c1': '#ff4d6d', 'c2': '#111111'}
    v = cr.badge_view(c, [])
    assert (v['shape'], v['field'], v['banner'], v['c3'], v['es'], v['er'], v['ef']) == ('heater', 'plain', 'ribbon', '#ffffff', 1.0, 0, False)
    assert '#d4af37' in cr.COLORS   # the workshop's gold pair saves (it was refused before)
