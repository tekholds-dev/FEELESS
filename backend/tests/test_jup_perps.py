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
    assert w == {'asset': 'SOL', 'side': 'long', 'usd': 25.0, 'lev': 50.0, 'input': 'USDC', 'tp': None, 'sl': None} and 'tpsl' not in b
    b, _ = jp.clean_open({'address': me, 'asset': 'BTC', 'side': 'short', 'usd': 10, 'lev': 10, 'input': 'SOL'}, 100.0)
    assert b['collateralMint'] == jp.USDC and b['marketMint'] == jp.MARKETS['BTC'] and b['inputMint'] == jp.SOL and b['collateralTokenDelta'] == '100000000'
    for bad, why in (({'asset': 'DOGE', 'side': 'long', 'usd': 10, 'lev': 5}, 'Pick'), ({'asset': 'SOL', 'side': 'long', 'usd': 5, 'lev': 5}, 'minimum'),
                     ({'asset': 'SOL', 'side': 'long', 'usd': 10, 'lev': 300}, 'Leverage'), ({'asset': 'SOL', 'side': 'up', 'usd': 10, 'lev': 5}, 'Pick')):
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


ME_ = 'W' * 43


def test_tp_sl_ride_the_open_on_the_right_side_of_the_live_mark():
    b, w = jp.clean_open({'address': ME_, 'asset': 'SOL', 'side': 'long', 'usd': 10, 'lev': 10, 'tp': 110, 'sl': 98, 'mark': 102.7}, None)
    assert b['tpsl'] == [{'requestType': 'tp', 'triggerPrice': '110000000', 'desiredMint': jp.USDC, 'entirePosition': True},
                         {'requestType': 'sl', 'triggerPrice': '98000000', 'desiredMint': jp.USDC, 'entirePosition': True}]   # Jupiter's live shape
    assert w['tp'] == 110 and w['sl'] == 98
    b, _ = jp.clean_open({'address': ME_, 'asset': 'BTC', 'side': 'short', 'usd': 10, 'lev': 5, 'sl': 85000, 'mark': 80900}, None)
    assert [x['requestType'] for x in b['tpsl']] == ['sl']
    for bad in ({'tp': 100, 'mark': 102.7}, {'sl': 105, 'mark': 102.7}, {'tp': 110}):                    # TP under / SL over a long's price · no live price
        with pytest.raises(ValueError):
            jp.clean_open({'address': ME_, 'asset': 'SOL', 'side': 'long', 'usd': 10, 'lev': 10, **bad}, None)
    with pytest.raises(ValueError):
        jp.clean_open({'address': ME_, 'asset': 'SOL', 'side': 'short', 'usd': 10, 'lev': 10, 'tp': 110, 'mark': 102.7}, None)


def test_partial_closes_and_tp_sl_on_a_live_position():
    P = 'P' * 43
    assert jp.close_body({'address': ME_, 'positionPubkey': P})['entirePosition'] is True
    half = jp.close_body({'address': ME_, 'positionPubkey': P, 'pct': 50, 'size': 250})
    assert half['entirePosition'] is False and half['sizeUsdDelta'] == '125000000'
    for bad in ({'pct': 33, 'size': 100}, {'pct': 50}):
        with pytest.raises(ValueError):
            jp.close_body({'address': ME_, 'positionPubkey': P, **bad})
    m, path, body, ex = jp.tpsl_body({'address': ME_, 'act': 'tpsl-add', 'positionPubkey': P, 'side': 'long', 'tp': 120, 'mark': 103})
    assert (m, path, ex) == ('POST', 'tpsl', 'create-tpsl') and body['tpsl'][0]['triggerPrice'] == '120000000' and body['transactionType'] == 'instant'
    assert jp.tpsl_body({'address': ME_, 'act': 'tpsl-edit', 'positionRequestPubkey': P, 'price': 99.5})[2]['triggerPrice'] == '99500000'
    assert jp.tpsl_body({'address': ME_, 'act': 'tpsl-cancel', 'positionRequestPubkey': P})[:2] == ('DELETE', 'tpsl')
    with pytest.raises(ValueError):
        jp.tpsl_body({'address': ME_, 'act': 'tpsl-add', 'positionPubkey': P, 'side': 'long', 'mark': 103})
    rows = jp.positions({'dataList': [{'positionPubkey': P, 'asset': 'SOL', 'side': 'long', 'leverage': '10', 'sizeUsd': '100000000', 'entryPriceUsd': '102000000',
                                       'tpslRequests': [{'positionRequestPubkey': 'R1', 'requestType': 'tp', 'triggerPriceUsd': '110000000', 'entirePosition': True}]}]})
    assert rows[0]['tpsl'] == [{'id': 'R1', 'kind': 'tp', 'price': 110.0, 'pct': None, 'all': True}] and rows[0]['size'] == 100.0


def test_the_weeks_top_traders_in_plain_dollars():
    d = jp.leaders({'totalVolumeUsd': '368507274586035', 'startTimestamp': 1, 'endTimestamp': 2,
                    'topTradersByPnl': [{'owner': 'A', 'totalPnlUsd': '36036989827', 'totalVolumeUsd': '11134702966336'}, {'owner': ''}],
                    'topTradersByVolume': [{'owner': 'B', 'totalPnlUsd': '-7990933123', 'totalVolumeUsd': '13829085250466'}]})
    assert round(d['vol']) == 368507275 and d['pnl'] == [{'wallet': 'A', 'pnl': 36036.989827, 'vol': 11134702.966336}] and d['busy'][0]['pnl'] == -7990.933123
    assert jp.leaders(None) == {'vol': None, 'from': None, 'to': None, 'pnl': [], 'busy': []}


def test_recent_trades_read_in_plain_dollars():
    raw = {'dataList': [{'txHash': 'T1', 'positionName': 'BTC-PERP', 'side': 'long', 'action': 'Decrease', 'orderType': 'Trigger', 'price': '79342.40', 'size': '928.99',
                         'collateralUsdDelta': '4.74', 'pnl': '-3.92', 'pnlPercentage': '-41.2', 'fee': '0.68', 'createdTime': 1793000000}, {'nope': 1}]}
    t = jp.trades(raw)
    assert t == [{'tx': 'T1', 'market': 'BTC', 'side': 'long', 'action': 'Decrease', 'type': 'Trigger', 'price': 79342.4, 'size': 928.99, 'collateral': 4.74,
                  'pnl': -3.92, 'pnlPct': -41.2, 'fee': 0.68, 'at': 1793000000.0}]
    assert jp.trades(None) == []
