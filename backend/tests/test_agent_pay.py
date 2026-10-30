"""💳 An agent paying for its own model calls. Fakes everything: no network, no funds."""
import asyncio
import base64
import json

import pytest
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

import agent_pay as ap
import cat_fund as cf
import feecat_service as fs

HASH = '11111111111111111111111111111111'
ME, PAY, FEE = str(Keypair().pubkey()), str(Keypair().pubkey()), str(Keypair().pubkey())


def _entry(amount='2010', **kw):
    return {'scheme': 'exact', 'network': ap.SOLANA, 'asset': cf.USDC_MINT, 'amount': amount, 'payTo': PAY, 'extra': {'feePayer': FEE}, **kw}


def _head(*entries):
    return base64.b64encode(json.dumps({'x402Version': 2, 'resource': {'url': 'u'}, 'accepts': list(entries)}).encode()).decode()


def test_it_only_takes_a_solana_usdc_quote_inside_the_ceiling():
    assert ap.pick_quote(_head({'scheme': 'upto', 'network': ap.SOLANA}, _entry()), 0.05)[1]['amount'] == '2010'
    for bad, ceiling in ((_entry(amount='300000'), 1.0), (_entry(), 0.001), (_entry(asset='OTHER'), 1.0), (_entry(extra={}), 1.0)):
        with pytest.raises(ValueError):
            ap.pick_quote(_head(bad), ceiling)
    with pytest.raises(ValueError):
        ap.pick_quote('not a header', 1.0)


def test_the_payment_moves_exactly_the_quote_to_the_quote_and_the_provider_pays_the_fee():
    tx = VersionedTransaction.from_bytes(base64.b64decode(ap.build_payment(ME, _entry(), HASH)))
    m = tx.message; keys = [str(k) for k in m.account_keys]
    assert keys[0] == FEE and m.header.num_required_signatures == 2
    programs = [keys[i.program_id_index] for i in m.instructions]
    assert programs == [cf.COMPUTE_PROGRAM, cf.COMPUTE_PROGRAM, cf.TOKEN_PROGRAM, ap.MEMO_PROGRAM]
    send = m.instructions[2]; acc = [keys[a] for a in bytes(send.accounts)]
    assert int.from_bytes(bytes(send.data)[1:9], 'little') == 2010 and acc[0] == str(cf.ata(ME)) and acc[2] == str(cf.ata(PAY)) and FEE not in acc
    with pytest.raises(ValueError):
        ap.build_payment(ME, _entry(amount='9000000'), HASH)
    with pytest.raises(ValueError):
        ap.build_payment(ME, {**_entry(), 'extra': {'feePayer': ME}}, HASH)


def test_model_names_map_to_the_provider():
    assert ap.provider_model('anthropic/claude-haiku-5.5') == 'claude-haiku-5.5' and ap.provider_model('openai/gpt-6.1-terra') == 'gpt-6-luna'


def test_a_call_pays_once_and_a_failed_answer_falls_through(monkeypatch):
    calls = []

    class R:
        def __init__(self, code, body=None, headers=None): self.status_code, self._b, self.headers, self.text = code, body or {}, headers or {}, ''
        def json(self): return self._b

    def http(final):
        class H:
            def __init__(self, **_k): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *_a): return False
            async def post(self, url, json=None, headers=None, **_k):
                calls.append(url)
                if 'agent-x402-pay' in url:
                    return R(200, {'signedTransaction': 'S'})
                if headers and 'PAYMENT-SIGNATURE' in headers:
                    return final
                return R(402, headers={'payment-required': _head(_entry())})
        return H
    cat = {'id': 'c', 'agentWallet': {'address': ME, 'circleId': 'w'}}
    monkeypatch.setattr(fs.httpx, 'AsyncClient', http(R(200, {'choices': [{'message': {'content': '4'}}]})))
    assert asyncio.run(fs._wallet_call(cat, 'a/x', [], 300, 0.05)) == ('4', 0.00201)
    assert sum('agent-x402-pay' in c for c in calls) == 1
    monkeypatch.setattr(fs.httpx, 'AsyncClient', http(R(500)))
    assert asyncio.run(fs._wallet_call(cat, 'a/x', [], 300, 0.05)) == ('', 0.0)
    assert asyncio.run(fs._wallet_call(cat, 'a/x', [], 300, 0.001)) == ('', 0.0)   # over the ceiling: nothing signed


def test_a_flat_fee_goes_only_to_the_fee_wallet_once_and_staff_pay_nothing(monkeypatch):
    import reputation_service as rs
    from starlette.requests import Request
    me, fee_w, owner = str(Keypair().pubkey()), str(Keypair().pubkey()), str(Keypair().pubkey())
    seen = {}; book = {}
    async def circle(_m, path, body=None, agent=False):
        if path == '/wallet':
            return {'wallet': {'address': me}}
        seen['tx'] = body['rawTransaction']; assert agent is True
        return {'signedTransaction': 'x', 'signature': 'S1'}
    async def rpc(_h, method, _p):
        return {'getTokenAccountBalance': {'value': {'amount': '5000000'}}, 'getLatestBlockhash': {'value': {'blockhash': HASH}}}.get(method, 'sig')
    monkeypatch.setattr(rs, '_internal_ok', lambda _r: True); monkeypatch.setattr(rs, '_circle', circle); monkeypatch.setattr(rs, '_rpc', rpc)
    monkeypatch.setattr(rs, '_fee_cfg', lambda: {'vaultFeeWallet': fee_w, 'agentTradeFeeUsd': 0.05, 'agentOtherFeeUsd': 0.10}); monkeypatch.setattr(rs, '_is_staff', lambda a: a == 'STAFF')
    monkeypatch.setattr(rs, '_json_load', lambda _p, d=None: book); monkeypatch.setattr(rs, '_json_save', lambda _p, v: book.update(v))
    req = Request({'type': 'http', 'headers': []}); body = {'key': 'k1', 'walletId': 'w', 'address': me, 'owner': owner, 'kind': 'other'}
    assert asyncio.run(rs.internal_agent_fee(req, body))['usd'] == 0.10
    m = VersionedTransaction.from_bytes(base64.b64decode(seen['tx'])).message
    assert str(cf.ata(fee_w)) in [str(k) for k in m.account_keys] and int.from_bytes(bytes(m.instructions[-1].data)[1:9], 'little') == 100_000
    seen.clear()
    assert asyncio.run(rs.internal_agent_fee(req, body))['again'] is True and not seen            # one key, one charge
    assert asyncio.run(rs.internal_agent_fee(req, {**body, 'key': 'k2', 'owner': 'STAFF'})) == {'skipped': True}
