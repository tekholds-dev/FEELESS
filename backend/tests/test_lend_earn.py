import base64

from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.null_signer import NullSigner
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

import lend_earn as le

EARN = Pubkey.from_string('jup3YeL8QhtSx1e253b2FDvsMNC87fDrgQZivbrndc9')
CB = Pubkey.from_string('ComputeBudget111111111111111111111111111111')


def _tx(payer, progs, extra_signer=None):
    ixs = [Instruction(p, b'\x01', [AccountMeta(payer, True, True)] + ([AccountMeta(extra_signer, True, False)] if extra_signer else [])) for p in progs]
    msg = MessageV0.try_compile(payer, ixs, [], Hash.default())
    signers = [NullSigner(payer)] + ([NullSigner(extra_signer)] if extra_signer else [])
    return base64.b64encode(bytes(VersionedTransaction(msg, signers))).decode()


def test_base_units_round_down_and_refuse_junk():
    assert le.base_units('1.5', 6) == '1500000' and le.base_units('0.0000019', 6) == '1' and le.base_units(2, 9) == '2000000000'
    assert le.base_units('0.0000001', 6) is None and le.base_units('-1', 6) is None and le.base_units('abc', 6) is None and le.base_units('nan', 6) is None


def test_a_jupiter_lend_deposit_from_the_users_wallet_passes():
    me = Keypair().pubkey()
    ok, why, progs = le.verify(_tx(me, [CB, EARN]), str(me))
    assert ok and why is None and progs == [str(CB), str(EARN)]


def test_refused_unless_the_user_pays_signs_alone_and_only_known_programs_run():
    me, other = Keypair().pubkey(), Keypair().pubkey()
    assert le.verify(_tx(other, [EARN]), str(me))[1] == 'The fee payer is not your wallet.'
    assert le.verify(_tx(me, [EARN], extra_signer=other), str(me))[1] == 'Someone other than you would sign it.'
    ok, why, _ = le.verify(_tx(me, [EARN, Keypair().pubkey()]), str(me))
    assert not ok and 'does not know' in why
    assert le.verify(_tx(me, [CB]), str(me))[1] == 'It never calls Jupiter Lend — refused.'
    assert le.verify('not base64!!', str(me))[0] is False and le.verify('', str(me))[0] is False


def test_requests_are_cleaned():
    w = 'W' * 44
    assert le.clean_request({'side': 'withdraw', 'asset': 'A' * 44, 'address': w, 'amount': '3'}) == ('withdraw', 'A' * 44, w, '3')
    for bad in ({'side': 'borrow', 'asset': 'A' * 44, 'address': w}, {'asset': 'x', 'address': w}, {'asset': 'A' * 44}):
        try:
            le.clean_request(bad)
            raise AssertionError('should refuse')
        except ValueError:
            pass


def test_the_route_builds_verifies_and_refuses_a_foreign_program(monkeypatch):
    import asyncio
    import reputation_service as rs
    from fastapi.testclient import TestClient
    me = Keypair().pubkey(); USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
    good = _tx(me, [CB, EARN]); bad = _tx(me, [EARN, Keypair().pubkey()])
    sent = []

    class R:
        def __init__(self, code, body):
            self.status_code, self._b, self.headers = code, body, {'content-type': 'application/json'}

        def json(self):
            return self._b

    class H:
        def __init__(self, tx):
            self.tx = tx

        async def post(self, url, json=None, headers=None, timeout=None):
            sent.append((url, json))
            return R(200, {'transaction': self.tx})

    async def hub():
        return {'pools': [{'project': 'jupiter-lend', 'mints': [USDC], 'sym': 'USDC', 'apy': 6.1}]}

    async def dec(m):
        return 6
    monkeypatch.setattr(rs, 'familia_pools', hub)
    monkeypatch.setattr(rs, '_mint_decimals', dec)
    rs._fle_hits.clear()
    c = TestClient(rs.app)
    monkeypatch.setattr(rs, '_ai_http', lambda: H(good))
    r = c.post('/api/reputation/familia-pools/earn', json={'address': str(me), 'asset': USDC, 'side': 'deposit', 'amount': '2.5'})
    assert r.status_code == 200 and r.json()['units'] == '2500000' and r.json()['transaction'] == good
    assert sent[-1] == ('https://lite-api.jup.ag/lend/v1/earn/deposit', {'asset': USDC, 'signer': str(me), 'amount': '2500000'}) or sent[-1][1]['amount'] == '2500000'
    monkeypatch.setattr(rs, '_ai_http', lambda: H(bad))
    r = c.post('/api/reputation/familia-pools/earn', json={'address': str(me), 'asset': USDC, 'side': 'withdraw', 'amount': '1'})
    assert r.status_code == 502 and 'Refused before your wallet saw it' in r.json()['detail']
    r = c.post('/api/reputation/familia-pools/earn', json={'address': str(me), 'asset': 'So11111111111111111111111111111111111111112', 'amount': '1'})
    assert r.status_code == 400   # not a Jupiter Lend market on the hub
