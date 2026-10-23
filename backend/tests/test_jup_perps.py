import base64

import pytest
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.null_signer import NullSigner
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

import jup_perps as jp

PERPS = Pubkey.from_string(jp.PERPS)
CB = Pubkey.from_string('ComputeBudget111111111111111111111111111111')
ME = Keypair()


def _tx(payer, progs, keeper=None, sign_with=None):
    ixs = [Instruction(p, b'\x01', [AccountMeta(payer, True, True)] + ([AccountMeta(keeper, True, False)] if keeper else [])) for p in progs]
    msg = MessageV0.try_compile(payer, ixs, [], Hash.default())
    signers = [sign_with or NullSigner(payer)] + ([NullSigner(keeper)] if keeper else [])
    return base64.b64encode(bytes(VersionedTransaction(msg, signers))).decode()


def test_open_bodies_follow_jupiters_rules_and_our_guards():
    me = str(ME.pubkey())
    b, w = jp.clean_open({'address': me, 'asset': 'sol', 'side': 'long', 'usd': 25, 'lev': 50}, None)
    assert b['collateralMint'] == jp.SOL and b['inputMint'] == jp.USDC and b['collateralTokenDelta'] == '25000000' and b['leverage'] == '50.0'
    assert w == {'asset': 'SOL', 'side': 'long', 'usd': 25.0, 'lev': 50.0, 'input': 'USDC'}
    b, _ = jp.clean_open({'address': me, 'asset': 'BTC', 'side': 'short', 'usd': 10, 'lev': 10, 'input': 'SOL'}, 100.0)
    assert b['collateralMint'] == jp.USDC and b['marketMint'] == jp.MARKETS['BTC'] and b['inputMint'] == jp.SOL and b['collateralTokenDelta'] == '100000000'
    for bad, why in (({'asset': 'DOGE', 'side': 'long', 'usd': 10, 'lev': 5}, 'Pick'), ({'asset': 'SOL', 'side': 'long', 'usd': 5, 'lev': 5}, 'minimum'),
                     ({'asset': 'SOL', 'side': 'long', 'usd': 10, 'lev': 150}, 'Leverage'), ({'asset': 'SOL', 'side': 'up', 'usd': 10, 'lev': 5}, 'Pick')):
        with pytest.raises(ValueError, match=why):
            jp.clean_open({'address': me, **bad}, 100.0)
    with pytest.raises(ValueError, match='SOL price'):
        jp.clean_open({'address': me, 'asset': 'SOL', 'side': 'long', 'usd': 10, 'lev': 5, 'input': 'SOL'}, None)
    assert jp.close_body({'address': me, 'positionPubkey': me})['entirePosition'] is True


def test_only_the_users_perps_transaction_passes():
    me = ME.pubkey(); keeper = Keypair().pubkey()
    assert jp.verify(_tx(me, [CB, PERPS], keeper), str(me)) == (True, None)
    assert not jp.verify(_tx(me, [CB]), str(me))[0]                                   # never calls Perps
    assert not jp.verify(_tx(me, [PERPS, Keypair().pubkey()]), str(me))[0]            # a foreign program
    assert not jp.verify(_tx(keeper, [PERPS], me), str(me))[0]                        # someone else pays
    assert not jp.verify(_tx(me, [PERPS], keeper), str(me), signed=True)[0]           # the wallet never signed
    assert jp.verify(_tx(me, [PERPS], keeper, sign_with=ME), str(me), signed=True)[0]


def test_positions_are_plain_dollars_pnl_before_fees():
    raw = {'dataList': [{'positionPubkey': 'P1', 'asset': 'SOL', 'side': 'short', 'leverage': '10.00', 'sizeUsd': '100000000', 'collateralUsd': '10000000',
                         'valueUsd': '10500000', 'entryPriceUsd': '103720000', 'markPriceUsd': '103200000', 'liquidationPriceUsd': '113810000',
                         'pnlBeforeFeesUsd': '501000', 'pnlBeforeFeesPct': '5.01', 'totalFeesUsd': '61700', 'createdTime': '100'}, {'nope': 1}]}
    p = jp.positions(raw)
    assert len(p) == 1 and p[0]['pnl'] == 0.501 and p[0]['fees'] == 0.0617 and p[0]['liq'] == 113.81 and p[0]['size'] == 100
    assert jp.positions(None) == []


def test_routes_build_verify_execute(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    me = ME.pubkey(); keeper = Keypair().pubkey(); good = _tx(me, [CB, PERPS], keeper); bad = _tx(me, [PERPS, Keypair().pubkey()]); seen = []
    state = {'tx': good}

    async def fake(method, path, **kw):
        seen.append((method, path, kw.get('json') or kw.get('params')))
        if path == 'pool-info':
            return 200, {'openFeePercent': '0.06', 'longBorrowRatePercent': '0.0016'}
        if path == 'positions':
            return 200, {'dataList': []}
        if path == 'transaction/execute':
            return 200, {'txid': 'SIG', 'action': kw['json']['action']}
        return 200, {'serializedTxBase64': state['tx'], 'quote': {'entryPriceUsd': '103.72', 'liquidationPriceUsd': '113.81'}, 'positionPubkey': 'P1'}
    monkeypatch.setattr(rs, '_jp_call', fake); rs._fjp_hits.clear(); rs._fjp_pool.clear()
    c = TestClient(rs.app)
    g = c.get('/api/reputation/familia/perps-real', params={'address': str(me)}).json()
    assert set(g['pools']) == {'SOL', 'ETH', 'BTC'} and g['pools']['SOL']['openFeePercent'] == 0.06 and g['min'] == 10
    r = c.post('/api/reputation/familia/perps-real', json={'address': str(me), 'asset': 'SOL', 'side': 'short', 'usd': 10, 'lev': 10})
    assert r.status_code == 200 and r.json()['action'] == 'increase-position' and r.json()['quote']['liquidationPriceUsd'] == '113.81'
    assert seen[-1][1] == 'positions/increase' and seen[-1][2]['collateralMint'] == jp.USDC
    r = c.post('/api/reputation/familia/perps-real', json={'act': 'close', 'address': str(me), 'positionPubkey': 'P1' * 16})
    assert r.status_code == 200 and r.json()['action'] == 'decrease-position' and seen[-1][1] == 'positions/decrease'
    assert c.post('/api/reputation/familia/perps-real', json={'address': str(me), 'asset': 'SOL', 'side': 'long', 'usd': 2, 'lev': 10}).status_code == 400
    state['tx'] = bad
    r = c.post('/api/reputation/familia/perps-real', json={'address': str(me), 'asset': 'SOL', 'side': 'long', 'usd': 10, 'lev': 10})
    assert r.status_code == 502 and 'Refused before your wallet saw it' in r.json()['detail']
    signed = _tx(me, [CB, PERPS], keeper, sign_with=ME)
    r = c.post('/api/reputation/familia/perps-real/execute', json={'address': str(me), 'action': 'increase-position', 'signed': signed})
    assert r.status_code == 200 and r.json()['txid'] == 'SIG' and seen[-1][2] == {'action': 'increase-position', 'serializedTxBase64': signed}
    assert c.post('/api/reputation/familia/perps-real/execute', json={'address': str(me), 'action': 'increase-position', 'signed': good}).status_code == 400   # unsigned
