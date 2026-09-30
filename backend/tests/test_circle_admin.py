"""Circle wallets: labels persist; sends need a valid address, a positive amount and the typed confirmation."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip('solders')
rs = pytest.importorskip('reputation_service')
TO = 'Dest111111111111111111111111111111111111WXYZ'


def test_meta_and_send_guards(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'CIRCLE_META_PATH', tmp_path / 'c.json')
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'Owner')
    monkeypatch.setattr(rs, '_admin_load', lambda: {'audit': []}); monkeypatch.setattr(rs, '_audit', lambda *a: None); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    sent = []

    async def circle(method, path, body=None):
        sent.append((path, body)); return {'id': 'tx1', 'state': 'INITIATED'}
    monkeypatch.setattr(rs, '_circle', circle)
    asyncio.run(rs.circle_wallet_meta(None, 'w1', rs.CircleMetaIn(name='Ops wallet', description='gas + airdrops')))
    assert asyncio.run(rs.circle_meta_get(None))['w1']['description'] == 'gas + airdrops'
    for bad in (dict(to='nope', confirm='nope'[-4:], amount='1'), dict(to=TO, confirm='0000', amount='1'), dict(to=TO, confirm='WXYZ', amount='-2')):
        with pytest.raises(rs.HTTPException):
            asyncio.run(rs.circle_transfer(None, rs.CircleSendIn(walletId='w1', tokenId='t1', **bad)))
    out = asyncio.run(rs.circle_transfer(None, rs.CircleSendIn(walletId='w1', tokenId='t1', to=TO, amount='2.5', confirm='WXYZ')))
    assert out['state'] == 'INITIATED' and sent[-1][0] == '/transfer' and sent[-1][1]['amount'] == '2.5'


def test_reserve_pays_via_circle_once(monkeypatch, tmp_path):
    """Reserve wallet is a Circle wallet: typed PAY <total>, one Circle send per holder, failed rows retry alone."""
    RES = 'Resv111111111111111111111111111111111111111'
    A, B = 'Aaaa111111111111111111111111111111111111111', 'Bbbb111111111111111111111111111111111111111'
    store = {'seasons': [{'id': 's1', 'reserveWallet': RES}]}
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'Owner')
    monkeypatch.setattr(rs, '_seasons', lambda: store)
    monkeypatch.setattr(rs, '_json_save', lambda path, d: None)
    monkeypatch.setattr(rs, '_json_load', lambda path, default=None: {})
    monkeypatch.setattr(rs, '_admin_load', lambda: {}); monkeypatch.setattr(rs, '_audit', lambda *a: None); monkeypatch.setattr(rs, '_admin_save', lambda d: None)

    async def plan(s, d):
        return {'rows': [{'address': A, 'tier': 'Gold', 'sol': 0.2}, {'address': B, 'tier': 'Bronze', 'sol': 0.1}]}
    monkeypatch.setattr(rs, '_reserve_plan', plan)
    sent, fail_b = [], [True]

    async def circle(method, path, body=None):
        if path == '/wallets':
            return {'wallets': [{'id': 'cw', 'address': RES, 'blockchain': 'SOL', 'balances': [{'symbol': 'SOL', 'tokenId': 'sol', 'amount': '1'}]}]}
        if body['to'] == B and fail_b[0]:
            raise rs.HTTPException(502, 'Circle down')
        sent.append(body); return {'id': 'tx-' + body['to'][:4], 'state': 'INITIATED'}
    monkeypatch.setattr(rs, '_circle', circle)
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_reserve_pay_circle(None, 's1', rs.CirclePayIn(confirm='PAY 1')))
    out = asyncio.run(rs.admin_reserve_pay_circle(None, 's1', rs.CirclePayIn(confirm='PAY 0.3')))
    assert out['wallets'] == 1 and out['failed'][0]['address'] == B and sent[0]['amount'] == '0.2'
    fail_b[0] = False
    out = asyncio.run(rs.admin_reserve_pay_circle(None, 's1', rs.CirclePayIn(confirm='PAY 0.1')))
    assert out['ok'] and [s['to'] for s in sent] == [A, B]
    with pytest.raises(rs.HTTPException):   # everything paid: nothing to send twice
        asyncio.run(rs.admin_reserve_pay_circle(None, 's1', rs.CirclePayIn(confirm='PAY 0')))
    assert len(store['reservePayouts']['s1']['rows']) == 2


def test_circle_autostarts_when_down(monkeypatch):
    """Owner call while the sidecar is down: it's started once, then the request goes through."""
    import httpx
    started, calls = [], []

    async def start():
        started.append(1); return True

    class Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def request(self, method, url, json=None):
            calls.append(url)
            if not started:
                raise httpx.ConnectError('down')
            return httpx.Response(200, json={'ok': True})
    monkeypatch.setattr(rs, '_circle_start', start)
    monkeypatch.setattr(rs.httpx, 'AsyncClient', Client)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(rs.asyncio, 'sleep', lambda s: real_sleep(0))
    assert asyncio.run(rs._circle('GET', '/status')) == {'ok': True} and len(started) == 1
