"""🌍 owner 2026-11-15: real products show first in the 3D studio, the iPhone Duo among them; nothing is faked when no free model exists."""
import real_world as rw


def test_the_newest_phones_lead_the_shelf():
    c = rw.cards()
    assert c[0]['name'] == 'iPhone Duo' and c[0]['cat'] == 'phones'
    assert {'iPhone 18 Pro', 'Galaxy Z Fold 8', 'Pixel 11 Pro Fold'} <= {x['name'] for x in c}
    assert len({x['id'] for x in c}) == len(c)


def test_a_card_starts_from_a_real_free_model_or_is_dropped():
    rows = {'galaxy z flip': [{'id': 'm1', 'name': 'Samsung Galaxy Z Flip 3'}]}
    got = rw.resolve(rw.cards()[:2], lambda q: rows.get(q, []))
    assert [g['name'] for g in got] == ['iPhone Duo']                # iPhone 18 Pro had no base here: dropped, never faked
    assert got[0]['model']['id'] == 'm1' and got[0]['remix'] is True  # the Duo starts from the closest real foldable, and says so
