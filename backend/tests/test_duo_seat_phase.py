"""🏁 owner, 2026-10-22 ("my trade disappeared"): the minute after a model trade closes (its review) the seat must read SOLD — never
'G4 is running $?' with the trading step lit over an EMPTY seat."""
import inspect

import reputation_service as rs


def test_a_leftover_holding_with_no_coin_reads_sold():
    assert rs._duo_phase('HOLDING', None) == 'SOLD'
    assert rs._duo_phase('HOLDING', {'mint': 'M'}) == 'HOLDING'


def test_a_coin_in_the_seat_is_always_holding_and_the_rest_pass_through():
    assert rs._duo_phase('HUNTING', {'mint': 'M'}) == 'HOLDING'
    assert rs._duo_phase('SOLD', {'mint': 'M'}) == 'HOLDING'
    assert rs._duo_phase(None, None) == 'HUNTING'
    assert rs._duo_phase('SEATS FULL', None) == 'SEATS FULL'


def test_the_review_minute_marks_the_seat_sold_and_rooms_carry_the_cash_back():
    src = inspect.getsource(rs._g4_tick) if hasattr(rs, '_g4_tick') else inspect.getsource(rs)
    assert "_g4['phase'] = 'SOLD'" in src
    rooms = inspect.getsource(rs._duo_rooms)
    assert "'back'" in rooms and "'inUsd'" in rooms
    view = inspect.getsource(rs._duo_view)
    assert "'seats'" in view and "'hunt'" in view and '_duo_phase(' in view
