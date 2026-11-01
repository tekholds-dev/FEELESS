"""⛓ Store on IPFS from the agent's own wallet (toju.network): a free simulated quote first, then pay exactly that — every network faked."""
import asyncio

import pytest

import agent_ipfs as ip
import feecat_service as fs

ADDR = '2CkRAi2Hb3k4EAUNxTWhwSnY54qasQB7JKRLM1hcczQ7'
INS = {'programId': ip.PROGRAM, 'data': 'AQID', 'keys': [{'pubkey': 'wCZKggcLoBdrEFX492YnQkFZpyBPEXBjoepN1eSRPjv', 'isSigner': False, 'isWritable': True},
                                                         {'pubkey': ADDR, 'isSigner': True, 'isWritable': True}, {'pubkey': ip.SYSTEM, 'isSigner': False, 'isWritable': False}]}


def test_only_the_known_escrow_with_the_agent_as_the_only_signer_is_ever_built():
    assert ip.check({'cid': 'bafy', 'instructions': [INS]}, ADDR) is INS
    for bad, why in [({'cid': 'bafy', 'instructions': [{**INS, 'programId': ip.SYSTEM}]}, 'different program'),
                     ({'cid': 'bafy', 'instructions': [{**INS, 'keys': INS['keys'] + [{'pubkey': ip.SYSTEM[:-1] + '2', 'isSigner': True, 'isWritable': True}]}]}, 'another signer'),
                     ({'cid': 'bafy', 'instructions': [INS, INS]}, 'unexpected')]:
        with pytest.raises(ValueError, match=why):
            ip.check(bad, ADDR)
    assert ip.afford(1_325_721, 17_924_768, 0.01) is None                                   # the live test: $0.13, gas kept
    assert 'gas' in ip.afford(1_325_721, 10_500_000, 0.01) and 'cap' in ip.afford(5_000_000, 1e9, 0.01)


def _env(monkeypatch, tmp_path, bal=17_924_768):
    cat = {'id': 'h1', 'agentWallet': {'address': ADDR, 'circleAcct': 'agent', 'circleId': 'cid'}, 'files': [{'id': 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4', 'name': 'logo.png', 'mime': 'image/png', 'ext': 'png', 'size': 3}]}
    store = {'cats': {'h1': cat}}; signed = []; confirmed = []
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: 'OWNER'); monkeypatch.setattr(fs._af, 'read', lambda *a, **k: b'PNG')

    async def rpc(http, m, ps):
        return {'getLatestBlockhash': {'value': {'blockhash': '11111111111111111111111111111111'}}, 'getBalance': {'value': bal},
                'simulateTransaction': {'value': {'err': None, 'accounts': [{'lamports': bal - 1_320_721}]}},
                'getSignatureStatuses': {'value': [{'confirmationStatus': 'finalized', 'err': None}]}}[m]
    monkeypatch.setattr(fs._crpc, '_rpc', rpc)

    async def dep(http, raw, name, mime, addr, days=30):
        return {'cid': 'bafyX', 'instructions': [INS]}

    async def conf(http, cid, sig, addr):
        confirmed.append((cid, sig)); return f'https://gw/ipfs/{cid}/logo.png', '2026-12-02'

    async def circle(http, c, rec):
        signed.append(rec['tx']); rec['sig'] = 'SIG'

    async def nap(_):
        return None
    monkeypatch.setattr(fs._ipfs, 'deposit', dep); monkeypatch.setattr(fs._ipfs, 'confirm', conf); monkeypatch.setattr(fs._at, '_circle_post', circle)
    monkeypatch.setattr(fs.asyncio, 'sleep', nap); fs._IPFS_Q.clear()
    go = lambda pay: asyncio.run(fs.cat_file_ipfs('h1', 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4', fs.FilePayload(session='s', pay=pay)))   # noqa: E731
    return store, signed, confirmed, go


def test_the_quote_signs_nothing_and_store_pays_that_quote_then_keeps_the_link(monkeypatch, tmp_path):
    store, signed, confirmed, go = _env(monkeypatch, tmp_path)
    q = go(False)['quote']
    assert q['cid'] == 'bafyX' and abs(q['sol'] - 0.001325721) < 1e-9 and q['why'] is None and signed == []   # 💲 the real cost, nothing signed
    out = go(True)['stored']
    assert len(signed) == 1 and confirmed == [('bafyX', 'SIG')] and out['url'].endswith('logo.png') and store['cats']['h1']['ipfs'][-1]['cid'] == 'bafyX'
    assert fs._af.public(store['cats']['h1'])['files'][0]['ipfs']['cid'] == 'bafyX'
    with pytest.raises(fs.HTTPException) as e:                                              # one quote = one payment
        go(True)
    assert e.value.status_code == 409 and len(signed) == 1


def test_it_never_pays_into_the_gas_reserve(monkeypatch, tmp_path):
    _s, signed, _c, go = _env(monkeypatch, tmp_path, bal=10_800_000)
    assert 'gas' in go(False)['quote']['why']
    with pytest.raises(fs.HTTPException) as e:
        go(True)
    assert e.value.status_code == 400 and signed == []
