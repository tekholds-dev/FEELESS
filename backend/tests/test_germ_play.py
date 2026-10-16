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
