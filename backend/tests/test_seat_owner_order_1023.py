"""🫡 The Godfather's SELL is final + 💵 each model sees its OWN live P&L (owner, 2026-10-23: "I told him to sell … he won't do what I want
when he's losing badly · they need to be aware of their individual live PnL")."""
import asyncio
import json

import ai_seat as seat


def test_owner_words_that_are_orders():
    for t in ('sell it now', 'SELL', 'get out', 'cut it', 'exit now you idiot', "why didn't you sell", 'asshole! shouldve been sold, poor trading !!!', 'take profit'):
        assert seat.owner_order(t) == {'action': 'SELL'}, t
    assert seat.owner_order('sell half') == {'action': 'TRIM', 'pct': 50} and seat.owner_order('trim 25%') == {'action': 'TRIM', 'pct': 25}


def test_owner_words_that_are_not_orders():
    for t in ('dont sell this', "don't sell yet, hold it", 'should we sell?', 'take profit 60', 'tp 80 sl 15', 'hold', 'its going up', '', None):
        assert seat.owner_order(t) is None, t


def test_obey_turns_a_hold_into_the_owners_sell_and_drops_its_lines():
    d = seat.obey({'action': 'HOLD', 'why': "I'm not selling", 'tp': 85, 'sl': 12, 'trail': 35}, {'action': 'SELL'}, True)
    assert d['action'] == 'SELL' and d['obeyed'] == 'HOLD' and not any(k in d for k in ('tp', 'sl', 'trail')) and d['why'].startswith("(🫡 the Godfather's order")
    t = seat.obey({'action': 'HOLD', 'why': 'x', 'tp': 60}, {'action': 'TRIM', 'pct': 75}, True)
    assert t['action'] == 'TRIM' and t['trim'] == 75 and t['tp'] == 60
    assert seat.obey({'action': 'SELL', 'why': 'x'}, {'action': 'TRIM', 'pct': 50}, True)['action'] == 'SELL'   # a full sell already covers a trim
    assert seat.obey({'action': 'HOLD'}, None, True) == {'action': 'HOLD'} and seat.obey({'action': 'WAIT'}, {'action': 'SELL'}, False) == {'action': 'WAIT'}


def test_pnl_words_carry_its_own_dollars_its_partner_and_the_live_trade():
    w = seat.pnl_words('G4', {'n': 77, 'won': 15, 'usd': -1.554, 'pct': -254}, 'OSSY', {'n': 101, 'won': 26, 'usd': 0.048, 'pct': -30},
                       {'symbol': 'ETCHY', 'pct': 2.6, 'pnlUsd': 0.01, 'inUsd': 0.4, 'peak': 38.2})
    assert w.startswith('YOU (G4): −$1.55 real over 77 closed · 19% won · avg -3.3% a trade — DOWN money, behind OSSY')
    assert 'OSSY: +$0.05 real over 101 closed' in w and 'THIS TRADE $ETCHY: +2.6% (+$0.01 on $0.40 in)' in w and '35.6 points given back' in w
    assert seat.pnl_words('OSSY', None) == 'YOU (OSSY): no closed real trades yet'


def test_packet_reads_owner_then_its_own_money_and_the_adviser_never_wears_the_holders():
    pk = seat.packet([], {'symbol': 'ETCHY', 'pct': 2.6}, 'rec', learn={'ownerSays': 'sell it'}, pnl='YOU (G4): −$1.55')
    assert list(pk)[:3] == ['OWNER', 'YOURPNL', 'yourSeat'] and pk['YOURPNL'] == 'YOU (G4): −$1.55'
    ad = seat.advise_packet(pk, 'G4', 'OSSY', mine='YOU (OSSY): +$0.05')
    assert ad['G4PnL'] == 'YOU (G4): −$1.55' and ad['YOURPNL'] == 'YOU (OSSY): +$0.05'
    assert 'YOURPNL' not in seat.advise_packet(pk, 'G4', 'OSSY')   # no own line given → never the holder's re-labelled as "yours"
    assert 'THE GODFATHER\'S SELL IS FINAL' in seat.SYSTEM and 'YOURPNL' in seat.SYSTEM


def test_owner_sell_in_the_trade_room_sells_the_seats_coin(monkeypatch):
    import reputation_service as rs

    class Req:
        async def json(self):
            return {'comment': 'sell it now, you are losing', 'mint': 'MINT1'}
    leg = {'mint': 'MINT1', 'symbol': 'ETCHY', 'pairAddress': 'PAIR1', 'aiSeat': True, 'aiBy': 'lan', 'entry': 1.0, 'units': 1.0, 'at': 1}
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cards': {'degen': {'real': True, 'legs': [leg]}}}})
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER')
    monkeypatch.setattr(rs, '_duo_card_legs', lambda: [leg])
    monkeypatch.setattr(rs, '_duo_view', lambda *a, **k: {'ok': True})
    monkeypatch.setattr(rs, '_duo_push', lambda: None)

    async def px(ms):
        return {m: 1.0 for m in ms}
    monkeypatch.setattr(rs, '_live_px', px)
    rs._g4['want'] = None
    asyncio.run(rs.admin_ai_seat_post(Req()))
    w = rs._g4['want']
    assert w['action'] == 'SELL' and w['pair'] == 'PAIR1' and w['by'] == 'owner' and w['model'] == 'YOU' and rs._seat.fresh(w, w['at'])
    row = (rs._g4_mem.get() or {})['log'][-1]
    assert row['by'] == 'owner' and row['view'] == 'SELL' and '🫡 selling it now' in row['why']
    rs._g4['want'] = None


def test_a_question_in_the_trade_room_sells_nothing(monkeypatch):
    import reputation_service as rs

    class Req:
        async def json(self):
            return {'comment': 'should we sell?', 'mint': 'MINT1'}
    leg = {'mint': 'MINT1', 'symbol': 'ETCHY', 'pairAddress': 'PAIR1', 'aiSeat': True}
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cards': {'degen': {'real': True, 'legs': [leg]}}}})
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER')
    monkeypatch.setattr(rs, '_duo_card_legs', lambda: [leg])
    monkeypatch.setattr(rs, '_duo_view', lambda *a, **k: {'ok': True})
    monkeypatch.setattr(rs, '_duo_push', lambda: None)
    rs._g4['want'] = None
    asyncio.run(rs.admin_ai_seat_post(Req()))
    assert rs._g4['want'] is None
    assert json.dumps((rs._g4_mem.get() or {})['log'][-1]).find('🫡') == -1


def test_each_models_record_is_its_own():
    import reputation_service as rs
    rs._json_save(rs.ARCHIVE_PATH, {'positions': [{'g4': True, 'aiBy': 'lan', 'realPct': -10}, {'g4': True, 'aiBy': 'local', 'realPct': 20},
                                                  {'g4': True, 'aiBy': 'local', 'realPct': 4}, {'realPct': 50}]})
    assert rs._g4_real_record('lan') == {'n': 1, 'won': 0, 'avg': -10.0, 'med': -10.0, 'best': -10.0, 'worst': -10.0}
    assert rs._g4_real_record('local')['n'] == 2 and rs._g4_real_record()['n'] == 3   # no `by` = the duo (the agents' trade never counts)
