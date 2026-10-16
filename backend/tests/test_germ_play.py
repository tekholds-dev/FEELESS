"""🦠 The germ play end to end: the stop under the germ, the second entry on a new germ, the moon bag word in Reaper's rule book."""
import chart_intel as ci
import arena_prime as ap
import office


def test_the_germ_stop_sits_just_under_the_floor_inside_its_bounds():
    assert ci.germ_stop({'germ': {'px': 1.0, 'dist': 6.0, 'lost': False}}) == (9.0, 1.0)
    assert ci.germ_stop({'germ': {'px': 1.0, 'dist': 1.0, 'lost': False}})[0] == ci.STOP_FLOOR      # never tighter than the floor
    assert ci.germ_stop({'germ': {'px': 1.0, 'dist': 28.0, 'lost': False}}, 30.0)[0] == 30.0         # never wider than the ceiling
    assert ci.germ_stop({'germ': {'px': 1.0, 'dist': 40.0, 'lost': False}}) is None                  # too far: the structure stop stands
    assert ci.germ_stop({'germ': {'px': 1.0, 'dist': 5.0, 'lost': True}}) is None and ci.germ_stop({}) is None


def test_the_thesis_takes_the_germ_stop_only_when_the_switch_is_on():
    ch = {'f': {'germ': {'px': 0.5, 'dist': 7.0, 'lost': False}, 'px': 0.535}, 'state': 'UPTREND'}
    on, off = ci.thesis(ch, 0, germ_stop_on=True), ci.thesis(ch, 0)
    assert on['stopPct'] == 10.0 and on['germStop'] and on['germPx'] == 0.5 and 'germ stop' in on['stopParts'][0]
    assert not off['germStop']


def test_a_coin_sold_green_comes_back_early_on_a_new_germ_floor_above_our_exit():
    card = {'agentOut': {'M': {'at': 100, 'px': 1.0, 'green': True}, 'D': {'at': 100, 'px': 1.0, 'green': True, 'danger': True}}}
    assert ap.agent_out(card, 200) == {'M', 'D'}
    assert ap.agent_out(card, 200, germ_of=lambda m: (1.2, 6.0)) == {'D'}             # new floor above where we sold, sitting on it
    assert ap.agent_out(card, 200, germ_of=lambda m: (0.9, 6.0)) == {'M', 'D'}        # floor under our exit: not a new base
    assert ap.agent_out(card, 200, germ_of=lambda m: (1.2, 30.0)) == {'M', 'D'}       # already ran off the new floor


def test_the_moon_bag_is_a_soft_exit_with_a_word():
    assert 'R7m' in office.SOFT_EXITS


def test_your_pick_locks_half_its_peak_once_it_has_been_up_10():
    assert office.pick_lock(9.9) is None and office.pick_lock(10) == 5.0 and office.pick_lock(30) == 15.0
    assert 'R5b' in office.OWNER_HARD and office.PICK_LOCK_SELL == 50.0   # your own rule: ONE half trim without asking, the rest rides your stop


def test_a_coin_on_its_germ_is_armed_through_a_waiting_chart_but_never_a_skip():
    from trench_kernel import brain, universe as uni
    uni.set_band({})
    on = {'row': {'chart': {'germDist': 6.0, 'entry': ['WAIT FOR CONFIRMATION', 'E5', '']}}}
    assert brain.germ_entry_ok(on, 'WAIT FOR CONFIRMATION') == '6% above it'
    assert brain.germ_entry_ok(on, 'SKIP') is None and brain.germ_entry_ok(on, 'WAIT FOR DATA') is None
    assert brain.germ_entry_ok({'row': {'chart': {'germDist': 22.0}}}, 'WAIT FOR PULLBACK') is None


def test_gstop_sells_on_the_lens_you_picked_and_certify_and_gstop_live_on_the_leg():
    ch = {'f': {'germ': {'lost': True}, 'germ5': {'lost': False}}}
    assert office.gstop_lost({'gstop': '1m'}, ch) == '1m' and office.gstop_lost({'gstop': '5m'}, ch) is None
    assert office.gstop_lost({'gstop': 'both'}, ch) == '1m' and office.gstop_lost({}, ch) is None and office.gstop_lost({'gstop': '1m'}, {}) is None
    card = {'legs': [{'pairAddress': 'P', 'symbol': 'X'}]}
    c2 = ap.set_leg(card, 'P', certified=True, gstop='5m', now=10)
    assert c2['legs'][0]['certified'] == 10 and c2['legs'][0]['gstop'] == '5m'
    c3 = ap.set_leg(c2, 'P', certified=False, gstop='off')
    assert 'certified' not in c3['legs'][0] and 'gstop' not in c3['legs'][0]
    import pytest
    with pytest.raises(ValueError):
        ap.set_leg(card, 'P', gstop='3m')
    assert 'R5g' in office.OWNER_HARD
