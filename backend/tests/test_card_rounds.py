import pytest
import fuse_hq as hq


def test_cards_start_with_5_rounds_and_spend_one_per_window():
    p = {}
    assert hq.rounds_left(p) == 5 and hq.rounds_left(p, staff=True) > 1000
    assert hq.use_round(p, 'w1') and not hq.use_round(p, 'w1')          # same window = one round
    for k in ('w2', 'w3', 'w4', 'w5'):
        hq.use_round(p, k)
    assert hq.rounds_left(p) == 0 and not hq.use_round(p, 'w6') and p['roundsUsed'] == 5


def test_extend_by_paying_or_letting_compound_pay():
    cfg = {'per5Usd': 0.5, 'compoundPay': True}
    p = {'roundsLeft': 0}
    with pytest.raises(ValueError):
        hq.extend_rounds(p, 'pay', cfg, paid_usd=0.2)                    # under-paid
    hq.extend_rounds(p, 'pay', cfg, paid_usd=0.49, sig='S')             # 97%+ counts (SOL drift)
    assert p['roundsLeft'] == 5 and not p.get('roundsOwedUsd')
    hq.extend_rounds(p, 'compound', cfg)
    assert p['roundsLeft'] == 10 and p['roundsOwedUsd'] == 0.5
    with pytest.raises(ValueError):
        hq.extend_rounds(p, 'compound', cfg)                             # one owed pack at a time
    hq.settle_owed(p, 0.5)
    assert p['roundsOwedUsd'] == 0
    with pytest.raises(ValueError):
        hq.extend_rounds({}, 'compound', {'per5Usd': 0.5, 'compoundPay': False})   # Cmd Ctr switched it off
    assert hq.clean_rounds_cfg({'per5Usd': 999})['per5Usd'] == 50


def test_paid_lamports_needs_the_payer_signature_and_a_landed_transfer():
    tx = {'meta': {'err': None, 'preBalances': [5_000_000_000, 100], 'postBalances': [4_000_000_000, 1_000_000_100]},
          'transaction': {'message': {'accountKeys': [{'pubkey': 'ME', 'signer': True}, {'pubkey': 'FEE', 'signer': False}]}}}
    assert hq.paid_lamports(tx, 'ME', 'FEE') == 1_000_000_000
    assert hq.paid_lamports(tx, 'OTHER', 'FEE') == 0
    assert hq.paid_lamports({**tx, 'meta': {**tx['meta'], 'err': {'x': 1}}}, 'ME', 'FEE') == 0


def test_rotation_options_and_per_coin_stop_mode():
    assert hq.rotate_hours(5 / 60) == 5 / 60 and hq.rotate_hours(0.25) == 0.25 and hq.rotate_hours(12) == 12 and hq.rotate_hours(3) == 24
    assert hq.next_switch_at({'lastSwitchAt': 1000, 'rotateHours': 0.0833333}) == 1000 + 300                 # every 5 minutes
    pos = {'slMode': 'sell', 'coinModes': {'P2': 'park', 'P3': 'bad'}}
    assert hq.coin_sl_mode(pos, 'P1') == 'sell' and hq.coin_sl_mode(pos, 'P2') == 'park' and hq.coin_sl_mode(pos, 'P3') == 'sell'


def test_coin_replace_clock():
    pos = {'at': 0, 'legs': [{'pairAddress': 'P1'}, {'pairAddress': 'P2', 'at': 1000}], 'coinRotate': {'P1': 1, 'P2': 0.25}}
    assert hq.coins_not_due(pos, 1500) == {'P1', 'P2'}
    assert hq.coins_not_due(pos, 1000 + 901) == {'P1'} and hq.coins_not_due(pos, 3601 + 1000) == set()


def test_backer_season_board_and_prize_split():
    log = {'A': [1, 2, 3, 4], 'B': [1, 2, 3], 'C': [1], 'D': [1, 2, 3]}
    wins = {'A': [2], 'B': [1, 2, 3], 'D': []}
    b = hq.backer_board(log, wins, 0, 10, exclude={'X'})
    assert [r['wallet'] for r in b] == ['B', 'A', 'D'] and 'C' not in {r['wallet'] for r in b}     # ≥3 backs to rank
    pz = hq.backer_prizes(b, 100)
    assert [(p['wallet'], p['usd']) for p in pz] == [('B', 50.0), ('A', 30.0)]                        # zero-win backers get nothing
    assert hq.backer_prizes(b, 0) == []                                                              # pool off


def test_lab_per_coin_configs_are_cleaned_at_build_time():
    plan = hq.clean_plan({'mode': 'swap', 'coins': {'P1': {'frozen': True, 'rotateHours': 0.25, 'slMode': 'park'}, 'P2': {'slMode': 'nope', 'rotateHours': 3}, 'ZZ': {'frozen': True}}},
                         None, ['P1', 'P2'])
    assert plan['frozen'] == ['P1'] and plan['coinRotate'] == {'P1': 0.25, 'P2': 24} and plan['coinModes'] == {'P1': 'park'}


def test_user_round_cycle_adaptive_swaps_into_majors_when_losing():
    assert hq.clean_plan({'cycle': 'adaptive'}, None, [])['cycle'] == 'adaptive' and hq.clean_plan({'cycle': 'x'}, None, [])['cycle'] == 'steady'
    assert hq.cycle_pick({'cycle': 'adaptive'}, -3) == 'majors' and hq.cycle_pick({'cycle': 'adaptive'}, 4) == 'runners'
    assert hq.cycle_pick({'cycle': 'steady'}, -9) == 'runners'
