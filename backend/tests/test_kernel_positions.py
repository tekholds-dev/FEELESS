"""🎮 The kernel's held-seat manager (trench_kernel/positions.py): take lines, a broken read vs a READY challenger, rotation."""
import trench_kernel.positions as pos

from kernel_helpers import row


def leg(m, entry=1.0, at=1, **k):
    return {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'units': 1.0, 'entry': entry, 'at': at, 'bought': {'tag': '🤖 agents READY'}, **k}


CH = [{'mint': 'N', 'symbol': 'N', 'pair': 'PN', 'px': 2.0}]
CFG = {'agentTakePct': 20, 'agentControl': True, 'agentScalp': False}
NOW = 40 * 60.0


def one(legs, table, px, **k):
    kw = {'control': True, 'now': NOW, 'challengers': CH, 'ranks': {'N': 200, 'A': 100}, **k}
    return pos.manage(legs, table, px, kw.pop('cfg', CFG), **kw)


def test_a_coin_under_its_take_line_holds_and_a_healthy_one_is_never_switched():
    d = one([leg('A')], [row('A')], {'PA': 0.97}, ranks={'N': 120, 'A': 100})[0]
    assert d['action'] == 'hold' and 'holding until +20%' in d['why']


def test_a_broken_read_gives_its_seat_to_a_ready_challenger_the_kernel_ranks_clearly_higher():
    d = one([leg('A')], [row('A', d5=-5.0)], {'PA': 0.95})[0]
    assert d['action'] == 'swap' and d['to']['mint'] == 'N' and '-5.0% in 5 min' in d['why']
    assert one([leg('A')], [row('A', d5=-5.0)], {'PA': 0.95}, ranks={'N': 110, 'A': 100})[0]['action'] == 'hold'          # not clearly higher (needs ×1.25)
    assert one([leg('A')], [row('A', d5=-5.0)], {'PA': 1.04})[0]['action'] == 'hold'                                       # a green coin is never switched
    assert one([leg('A', at=NOW - 300)], [row('A', d5=-5.0)], {'PA': 0.95})[0]['action'] == 'hold'                         # not in its first 15 minutes
    assert one([leg('A')], [row('A', d5=-5.0)], {'PA': 0.95}, vels={'A': {'state': 'ACCELERATING'}})[0]['action'] == 'hold'
    assert one([leg('A')], [row('A', d5=-5.0)], {'PA': 0.95}, challengers=[])[0]['action'] == 'hold'                       # no READY coin: nothing to switch into
    assert one([leg('A')], [row('A', d5=-5.0)], {'PA': 0.95}, moves_left=0)[0]['action'] == 'hold'                         # the switch budget is used
    assert one([leg('A')], [row('A', d5=-5.0)], {'PA': 0.95}, live=False)[0]['action'] == 'hold'                           # the office is refilling after a restart


def test_off_the_board_is_a_broken_read_only_past_the_grace():
    assert one([leg('A')], [], {'PA': 0.95})[0]['action'] == 'hold'                                                        # radar unknown: a missing row is OUR gap
    assert one([leg('A')], [], {'PA': 0.95}, radar={'A'})[0]['action'] == 'swap'


def test_a_long_held_loser_yields_only_to_a_much_stronger_ready_coin():
    assert one([leg('A')], [row('A')], {'PA': 0.99}, ranks={'N': 140, 'A': 100})[0]['action'] == 'hold'                    # 1.4× < 1.25 + 0.25
    d = one([leg('A')], [row('A')], {'PA': 0.99}, ranks={'N': 160, 'A': 100})[0]
    assert d['action'] == 'swap' and 'not winning' in d['why']
    assert one([leg('A')], [row('A')], {'PA': 0.99}, ranks={'N': 160, 'A': 100}, now=20 * 60.0)[0]['action'] == 'hold'     # only after 30 min


def test_a_chosen_take_line_is_banked_at_the_line_and_the_base_line_is_read():
    cfg = {**CFG, 'agentTp': 10}
    assert one([leg('A')], [row('A')], {'PA': 1.12}, cfg=cfg)[0]['action'] == 'swap'                                      # your line: banked into the READY coin
    assert one([leg('A')], [row('A')], {'PA': 1.12}, cfg={**cfg, 'agentMode': 'pull'})[0]['action'] == 'pull'
    learned = one([leg('A')], [row('A')], {'PA': 1.07}, cfg={**CFG, 'agentScalp': True}, scalp={'tp': 6})[0]
    assert learned['action'] == 'swap' and 'learned take' in learned['why']
    run = one([leg('A')], [row('A')], {'PA': 1.3})[0]
    assert run['action'] == 'hold' and 'it runs' in run['why']                                                             # base line + healthy read: it runs under the trail
    assert one([leg('A')], [row('A', buy=41)], {'PA': 1.3})[0]['action'] == 'swap'                                         # base line + broken read: banked
    assert one([leg('A')], [row('A')], {'PA': 1.3}, reviews={'A': 'invalid'}, challengers=[])[0]['action'] == 'pull'
    assert one([leg('A')], [], {'PA': 1.3})[0]['action'] == 'hold'                                                         # not read this pass: nothing is ruled on a gap


def test_manual_holds_everything_and_only_agent_seats_are_managed_out_of_control():
    assert one([leg('A')], [row('A', d5=-9)], {'PA': 0.9}, cfg={**CFG, 'agentAuthority': 'manual'})[0]['action'] == 'hold'
    mine = {**leg('B'), 'bought': {'tag': '🎯 your pick'}}
    out = pos.manage([leg('A'), mine], [row('A'), row('B')], {'PA': 1.0, 'PB': 1.0}, CFG, control=False, now=NOW, challengers=CH, ranks={})
    assert [d['symbol'] for d in out] == ['A']
    assert pos.manage([{**leg('A'), 'frozen': True}, {**leg('C'), 'placeholder': True}], [], {'PA': 1.0}, CFG, control=True, now=NOW) == []


def test_the_switch_view_shows_the_same_lines():
    v = pos.switch_view(leg('A'), -2.0, 40.0, CH[0], {'N': 200, 'A': 100}, {'switch': {'on': True, 'mode': 'agents'}})
    assert v['switch'] and v['edge'] == 100 and v['need'] == 25.0 and v['challenger']['symbol'] == 'N'
    w = pos.switch_view(leg('A'), +3.0, 40.0, CH[0], {'N': 200, 'A': 100}, {'switch': {'on': True, 'mode': 'agents'}})
    assert not w['switch'] and w['why'].startswith('position not a winner')
