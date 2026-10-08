"""A crew is bought with ONE SOL transfer the buyer signed to the fee wallet. The server re-reads it on-chain (fake RPC here — never the network),
re-prices it in SOL now, and accepts it once: too small, someone else's, failed, already used → refused."""
import asyncio

import pytest
from fastapi import HTTPException

SIG = '5' * 80
FEE, ME = 'FeeWalletOwner1111111111111111111111111111111', 'BuyerWallet11111111111111111111111111111111'


def _tx(payer, to, lamports, err=None):
    key = lambda pk, signer=False: {'pubkey': pk, 'signer': signer}
    return {'meta': {'err': err, 'preBalances': [10 * 10**9, 0], 'postBalances': [10 * 10**9 - lamports - 5000, lamports]}, 'transaction': {'message': {'accountKeys': [key(payer, True), key(to)]}}}


def _patch(monkeypatch, rs, tx, sol_usd=100.0, to=FEE):
    async def rpc(http, method, params):
        return tx
    async def pay_to():
        return to
    async def sol():
        return sol_usd
    monkeypatch.setattr(rs, '_rpc', rpc); monkeypatch.setattr(rs, '_rounds_pay_to', pay_to); monkeypatch.setattr(rs, '_sol_usd_live', sol)
    monkeypatch.setattr(rs, '_json_load', lambda *a, **k: {})


def _run(rs, sig, min_usd, st=None):
    return asyncio.run(rs._verify_sol_payment(sig, {ME}, min_usd, st or {}))


def test_a_full_payment_to_the_fee_wallet_is_accepted_and_priced_in_usd(monkeypatch):
    import reputation_service as rs
    _patch(monkeypatch, rs, _tx(ME, FEE, int(0.25 * 1e9)))                                     # 0.25 SOL at $100 = $25
    paid = _run(rs, SIG, 25.0)
    assert paid['usd'] == 25.0 and paid['sig'] == SIG and paid['lamports'] == 250_000_000


def test_a_payment_a_few_percent_short_is_ok_but_a_real_shortfall_is_refused_with_the_amount(monkeypatch):
    import reputation_service as rs
    _patch(monkeypatch, rs, _tx(ME, FEE, int(0.2425 * 1e9)))                                   # $24.25 = 97% of $25
    assert _run(rs, SIG, 25.0)['usd'] == 24.25
    _patch(monkeypatch, rs, _tx(ME, FEE, int(0.2 * 1e9)))                                      # $20
    with pytest.raises(HTTPException) as e:
        _run(rs, SIG, 25.0)
    assert e.value.status_code == 400 and '$20.00' in e.value.detail and '$25.00' in e.value.detail


def test_someone_elses_transfer_a_failed_tx_a_wrong_recipient_and_a_reused_signature_are_refused(monkeypatch):
    import reputation_service as rs
    _patch(monkeypatch, rs, _tx('SomeoneElse' + '1' * 32, FEE, 10**9))
    with pytest.raises(HTTPException): _run(rs, SIG, 25.0)                                     # the payer must be the buyer's own wallet
    _patch(monkeypatch, rs, _tx(ME, FEE, 10**9, err={'InstructionError': [0, 'x']}))
    with pytest.raises(HTTPException): _run(rs, SIG, 25.0)                                     # a failed transaction pays nothing
    _patch(monkeypatch, rs, _tx(ME, 'NotTheFeeWallet' + '1' * 29, 10**9))
    with pytest.raises(HTTPException): _run(rs, SIG, 25.0)                                     # it has to reach the fee wallet
    _patch(monkeypatch, rs, _tx(ME, FEE, 10**9))
    with pytest.raises(HTTPException) as e: _run(rs, SIG, 25.0, {'sigs': [SIG]})
    assert e.value.status_code == 409                                                          # a payment is never reused
    with pytest.raises(HTTPException) as e2: _run(rs, 'short', 25.0)
    assert e2.value.status_code == 400
