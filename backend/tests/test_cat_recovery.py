"""🔑 The recovery PIN + 💳 paid credit + 💵 USDC funding. Fakes everything: no network, no funds."""
import base64

import pytest
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

import cat_fund as cf
import cat_recovery as cr
import feecat_service as fs

HASH = '11111111111111111111111111111111'


def test_the_pin_is_stored_only_as_a_hash_and_works_whatever_the_case():
    pin = cr.new_pin(); rec = cr.seal(pin)
    assert len(pin) == 14 and pin.count('-') == 2 and pin not in str(rec)
    assert cr.check(rec, pin.lower().replace('-', ' '), 100.0) == 'ok'


def test_five_wrong_tries_lock_it_for_an_hour_even_for_the_right_pin():
    pin = cr.new_pin(); rec = cr.seal(pin)
    assert all(cr.check(rec, 'WRONG-WRONG', 10.0) == 'wrong' for _ in range(cr.MAX_TRIES))
    assert cr.check(rec, pin, 11.0) == 'locked'
    assert cr.check(rec, pin, 11.0 + cr.LOCK_SEC) == 'ok'


def test_the_pin_hash_never_leaves_the_server():
    assert 'recovery' not in fs._no_keys({'id': 'c', 'recovery': {'hash': 'x'}, 'recoverySet': True})


def test_free_credit_only_for_paper_cats_or_a_creator():
    assert fs.free_credit_ok({'brainsCfg': {'kind': 'trading'}}) is True
    assert fs.free_credit_ok({'brainsCfg': {'kind': 'general'}}) is False
    assert fs.free_credit_ok({'brainsCfg': {'kind': 'trading'}, 'agentWallet': {'address': 'x'}}) is False
    assert fs.free_credit_ok({'brainsCfg': {'kind': 'general'}}, creator=True) is True


def test_credit_goes_all_to_feeless_and_never_counts_as_the_first_funding():
    p = cf.plan(5, 200, first=True, credit=True)
    assert p['purpose'] == 'credit' and p['catLamports'] == 0 and p['feeLamports'] == p['totalLamports'] and p['feeUsd'] == 5 and p['catUsd'] == 0
    with pytest.raises(ValueError):
        cf.plan(0.5, 200, first=True, credit=True)


def test_usdc_is_one_to_one_and_builds_transfers_to_the_right_token_accounts():
    me, cat, fee = Keypair().pubkey(), Keypair().pubkey(), Keypair().pubkey()
    p = cf.plan(10, 0, first=True, fee_usd=2, token='USDC')   # no SOL price needed
    assert p['token'] == 'USDC' and p['totalLamports'] == 10_000_000 and p['feeLamports'] == 2_000_000 and p['catLamports'] == 8_000_000
    tx = VersionedTransaction.from_bytes(base64.b64decode(cf.build(str(me), str(cat), str(fee), p, HASH)))
    keys = [str(k) for k in tx.message.account_keys]
    assert str(cf.ata(cat)) in keys and str(cf.ata(fee)) in keys and str(cf.ata(me)) in keys and cf.USDC_MINT in keys
    sends = [i for i in tx.message.instructions if keys[i.program_id_index] == cf.TOKEN_PROGRAM]
    assert [int.from_bytes(bytes(i.data)[1:9], 'little') for i in sends] == [2_000_000, 8_000_000]
    assert all(bytes(i.data)[0] == 12 and bytes(i.data)[9] == 6 for i in sends)


def test_usdc_credit_has_one_leg_only():
    me, cat, fee = Keypair().pubkey(), Keypair().pubkey(), Keypair().pubkey()
    tx = VersionedTransaction.from_bytes(base64.b64decode(cf.build(str(me), str(cat), str(fee), cf.plan(3, 0, first=False, token='USDC', credit=True), HASH)))
    keys = [str(k) for k in tx.message.account_keys]
    assert str(cf.ata(fee)) in keys and str(cf.ata(cat)) not in keys


def test_spend_limits_are_clamped_and_day_left_counts_only_today():
    import time
    assert fs.clean_limits({'mindUsd': [9, 'x'], 'steps': 999, 'dayUsd': -3}) == {'mindUsd': [fs.TASK_CAP_MAX, 0.0], 'steps': fs._ca.GO_STEPS, 'dayUsd': 0.0}
    today = time.strftime('%Y-%m-%d', time.gmtime())
    cat = {'limits': {'dayUsd': 1}, 'brainsCfg': {'daySpend': {today: 0.25}}}
    assert fs.day_left(cat) == 0.75 and fs.day_left({'limits': {}}) is None


def test_one_mind_stops_at_its_own_limit_while_the_task_budget_remains():
    import asyncio
    import cat_agent as ca
    task = ca.new_task('t', 'x', ['a', 'b'], 1.0, mind_caps=[0.1, 0])
    async def ask(_m, _msgs):
        return 'ok', 0.1
    asyncio.run(ca._ask(task, task['windows'][0], ask, 'a', []))
    with pytest.raises(ca.Stopped):
        asyncio.run(ca._ask(task, task['windows'][0], ask, 'a', []))
    assert asyncio.run(ca._ask(task, task['windows'][1], ask, 'b', [])) == 'ok'   # the other mind keeps working
