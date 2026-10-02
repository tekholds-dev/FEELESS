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
