"""🎯 Entry quality (owner, 2026-10-16: "stop agents from poor entry — enter more near germ, find dips in rush coins")."""
import opportunity as op
from trench_kernel import brain


def row(dh=None, germ=None, d5=1.0, buy=60, c1=0.0, vol1h=0.0, call=None):
    ch = {'distHigh': dh, 'germDist': germ, 'germ': 'floor' if germ is not None and germ <= 15 else None}
    if call:
        ch['entry'] = [call, 'E?']
    return {'mint': 'M', 'chart': ch, 'nums': {'d5': d5, 'buy': buy, 'c1': c1, 'pace': 1.2}, 'vitals': {'vol1h': vol1h}}


def test_the_gun_wall_blocks_a_buy_right_under_resistance_unless_it_is_on_its_germ_too():
    assert op.gun_wall(row(dh=0.9, germ=13.1))          # $SAINDRA: 0.9% under the gun line, 13% above the germ → no entry
    assert op.gun_wall(row(dh=2.0, germ=3.0)) is None    # a tight range, on the floor: the floor is the entry
    assert op.gun_wall(row(dh=8.0, germ=13.0)) is None and op.gun_wall(row()) is None


def test_a_rush_dip_is_a_coin_that_ran_pulled_back_and_steadied():
    assert op.rush_dip(row(dh=25, germ=10, d5=0.5, buy=58, c1=60))
    assert op.rush_dip(row(dh=25, germ=10, d5=0.5, buy=58, vol1h=80_000))
    assert op.rush_dip(row(dh=25, germ=10, d5=-6, buy=58, c1=60)) is None     # still falling: a knife
    assert op.rush_dip(row(dh=25, germ=-3, d5=0.5, buy=58, c1=60)) is None    # lost its germ
    assert op.rush_dip(row(dh=5, germ=10, d5=0.5, buy=58, c1=60)) is None     # not a dip, at the top
    assert op.rush_dip(row(dh=25, germ=10, d5=0.5, buy=58, c1=5)) is None     # never ran: not a rush coin
    assert op.germ_rank(row(dh=25, germ=5, d5=0.5, buy=58, c1=60))[0] > op.germ_rank(row(dh=25, germ=5, d5=0.5, buy=58))[0]


def test_trigger_never_buys_under_the_gun_line_and_arms_a_rush_dip():
    ms = lambda r, flow=None: {'row': r, 'market': {'flow': flow or {}, 'move5m': r['nums']['d5']}}
    t = brain.trigger(ms(row(dh=0.9, germ=13.1, d5=1.6, buy=45, call='WAIT FOR BREAKOUT')))
    assert t['state'] == 'WAIT'
    t = brain.trigger(ms(row(dh=25, germ=8, d5=0.5, buy=58, c1=60, call='WAIT FOR CONFIRMATION')))
    assert t['state'] in ('ARM', 'ENTER') and ('rush dip' in t['why'] or 'germ' in t['why'])
    t = brain.trigger(ms(row(dh=25, germ=8, d5=0.5, buy=58, c1=60, call='SKIP')))
    assert t['state'] != 'ENTER'
    t = brain.trigger(ms(row(dh=25, germ=8, d5=0.5, buy=58, c1=60, call='WAIT FOR CONFIRMATION'), {'state': 'SELLERS', 'why': 'sellers lead'}))
    assert t['state'] == 'WAIT'


def test_a_germ_entry_needs_room_up_to_the_gun_line():
    ms = {'row': row(dh=3.5, germ=8, call='WAIT FOR CONFIRMATION'), 'market': {}}
    assert brain.germ_entry_ok(ms, 'WAIT FOR CONFIRMATION') is None
    ms = {'row': row(dh=20, germ=8, call='WAIT FOR CONFIRMATION'), 'market': {}}
    assert brain.germ_entry_ok(ms, 'WAIT FOR CONFIRMATION')
