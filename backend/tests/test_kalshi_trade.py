import asyncio
import base64

import pytest
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction

import kalshi_trade as kt

ME = Keypair()
CB = Pubkey.from_string('ComputeBudget111111111111111111111111111111')


def _tx(ixs, payer=None, signed=False, signers=None):
    payer = payer or ME.pubkey()
    msg = MessageV0.try_compile(payer, ixs, [], Hash.default())
    if signed:
        tx = VersionedTransaction(msg, [ME])
    else:
        tx = VersionedTransaction.populate(msg, [Signature.default()] * msg.header.num_required_signatures)
    return base64.b64encode(bytes(tx)).decode()


def _pred(extra_signer=None):
    metas = [AccountMeta(ME.pubkey(), True, True)] + ([AccountMeta(extra_signer, True, False)] if extra_signer else [])
    return Instruction(Pubkey.from_string(kt.PRED), b'\x01order', metas)


def test_a_real_shaped_dflow_order_passes_and_is_sent_once():
    b = _tx([Instruction(CB, b'\x02\x00\x00\x00\x00', []), _pred()])
    ok, why, fp = kt.verify(b, str(ME.pubkey()))
    assert ok and why is None and fp
    kt.remember(fp, str(ME.pubkey()), now=1000)
    assert kt.take(fp, str(ME.pubkey()), now=1001) and not kt.take(fp, str(ME.pubkey()), now=1002)   # once
    kt.remember(fp, str(ME.pubkey()), now=1000)
    assert not kt.take(fp, str(ME.pubkey()), now=1000 + kt.QUOTE_TTL + 1)                               # expired
    ok, why, _ = kt.verify(b, str(ME.pubkey()), signed=True)
    assert not ok and 'did not sign' in why
    assert kt.verify(_tx([_pred()], signed=True), str(ME.pubkey()), signed=True)[0]


def test_the_safety_check_fails_closed():
    me = str(ME.pubkey())
    assert 'fee payer' in kt.verify(_tx([_pred()]), str(Keypair().pubkey()))[1]
    assert 'besides you' in kt.verify(_tx([_pred(extra_signer=Keypair().pubkey())]), me)[1]
    assert 'does not know' in kt.verify(_tx([_pred(), Instruction(Pubkey.from_string('JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4'), b'x', [])]), me)[1]
    assert 'never goes through DFlow' in kt.verify(_tx([Instruction(CB, b'\x02\x00\x00\x00\x00', [])]), me)[1]
    tok = Pubkey.from_string(kt.TOKEN); a, b = Keypair().pubkey(), Keypair().pubkey()
    assert 'approves a spender' in kt.verify(_tx([_pred(), Instruction(tok, bytes([4]) + (5).to_bytes(8, 'little'), [AccountMeta(a, False, True), AccountMeta(b, False, False), AccountMeta(ME.pubkey(), True, False)])]), me)[1]
    assert 'moves tokens out' in kt.verify(_tx([_pred(), Instruction(tok, bytes([3]) + (5).to_bytes(8, 'little'), [AccountMeta(a, False, True), AccountMeta(b, False, True), AccountMeta(ME.pubkey(), True, False)])]), me)[1]
    sysp = Pubkey.from_string(kt.SYSTEM)
    assert 'sends SOL' in kt.verify(_tx([_pred(), Instruction(sysp, (2).to_bytes(4, 'little') + (9).to_bytes(8, 'little'), [AccountMeta(ME.pubkey(), True, True), AccountMeta(a, False, True)])]), me)[1]
    assert kt.verify('nope', me)[1] == 'Not a transaction.'


def test_the_ticket_the_order_match_and_settlement_rules():
    assert kt.ticket('SOL', 'up', 1) == (True, None) and kt.ticket('PEPE', 'up', 5)[0] is False and kt.ticket('SPX', 'down', 1) == (True, None)
    assert kt.ticket('BTC', 'up', 0.5)[0] is False and kt.ticket('BTC', 'sideways', 5)[0] is False and kt.ticket('BTC', 'down', 501)[0] is False
    o = {'inputMint': kt.USDC, 'outputMint': 'YES', 'inAmount': '1000000', 'transaction': 'x'}
    assert kt.matches(o, kt.USDC, 'YES', 1_000_000) == (True, None)
    assert 'different market' in kt.matches({**o, 'outputMint': 'NO'}, kt.USDC, 'YES', 1_000_000)[1]
    assert 'different amount' in kt.matches({**o, 'inAmount': '2000000'}, kt.USDC, 'YES', 1_000_000)[1]
    m = {'ticker': 'KXSOL15M-X', 'status': 'determined', 'result': 'yes', 'accounts': {kt.USDC: {'yesMint': 'Y', 'noMint': 'N', 'redemptionStatus': 'open'}}}
    assert kt.side_mints(m) == ('Y', 'N') and kt.redeemable(m, 'Y') == (True, None) and 'lost' in kt.redeemable(m, 'N')[1]
    assert 'not settled' in kt.redeemable({**m, 'status': 'active'}, 'Y')[1]
    assert 'not open' in kt.redeemable({**m, 'accounts': {kt.USDC: {'yesMint': 'Y', 'noMint': 'N', 'redemptionStatus': 'pending'}}}, 'Y')[1]
    p = kt.position(m, 'Y', 2_500_000)
    assert p['side'] == 'UP' and p['contracts'] == 2.5 and p['won'] is True and p['redeemable'] is True
    assert kt.position(m, 'OTHER', 1) is None
    q = kt.order_params(kt.USDC, 'Y', 5_000_000, 'W')
    assert q['amount'] == '5000000' and q['slippageBps'] == '300' and q['userPublicKey'] == 'W'


def test_no_key_no_trading_and_proof_gates_a_buy(monkeypatch):
    import reputation_service as rs
    from fastapi import HTTPException
    monkeypatch.delenv('DFLOW_API_KEY', raising=False)
    with pytest.raises(HTTPException) as e:
        rs._kt_need()
    assert e.value.status_code == 503 and 'production key' in e.value.detail
    monkeypatch.setenv('DFLOW_API_KEY', 'k')
    asked = []

    class R:
        status_code = 200

        def json(self):
            return {'verified': False}

    class C:
        async def get(self, url, **k):
            asked.append(url)
            return R()
    monkeypatch.setattr(rs, '_fmk_http', C()); monkeypatch.setattr(rs, '_kproof', {})

    class Q:
        async def json(self):
            return {'address': str(ME.pubkey()), 'coin': 'SOL', 'side': 'up', 'usd': 2}
    with pytest.raises(HTTPException) as e:
        asyncio.run(rs.familia_kalshi_order(Q()))
    assert e.value.status_code == 403 and e.value.detail.startswith('PROOF') and asked == [f'{kt.PROOF}/{ME.pubkey()}']
    assert rs._kproof == {}                                                                               # "not verified" is never cached
