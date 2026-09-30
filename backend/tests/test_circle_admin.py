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
    monkeypatch.setattr(rs, 'CIRCLE_DEST_PATH', tmp_path / 'd.json')
    monkeypatch.setattr(rs, '_seasons', lambda: {'seasons': []}); monkeypatch.setattr(rs, '_pools', lambda: {'pools': []})
    monkeypatch.setattr(rs, 'ROUTES_PATH', tmp_path / 'r.json'); monkeypatch.setattr(rs, '_owner_wallets', lambda: {'Owner'}); monkeypatch.setattr(rs, '_admin_wallets', lambda: {'Owner'})
    with pytest.raises(rs.HTTPException) as unknown:   # not a Command Center wallet and not saved → refused
        asyncio.run(rs.circle_transfer(None, rs.CircleSendIn(walletId='w1', tokenId='t1', to=TO, amount='2.5', confirm='WXYZ')))
    assert unknown.value.status_code == 403
    asyncio.run(rs.circle_destination_save(None, rs.CircleDestIn(address=TO, label='Cold wallet')))
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


def test_money_pulse_one_read_for_every_card(monkeypatch):
    """Pulse: one getMultipleAccounts for all wallets, Circle listed, reserve plan fed from that read."""
    RES = 'Resv111111111111111111111111111111111111111'
    rpc_calls = []
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'Owner')
    monkeypatch.setattr(rs, '_owner_wallets', lambda: {'Owner'})
    monkeypatch.setattr(rs, '_fee_cfg', lambda: {'platformFeeBps': 50, 'engine': 'swap'})
    monkeypatch.setattr(rs, '_seasons', lambda: {'seasons': [{'id': 's1', 'name': 'S1', 'reserveWallet': RES, 'badgeRewardPct': 10, 'start': 0, 'end': 1}], 'scores': {}})
    monkeypatch.setattr(rs, '_pools', lambda: {'pools': []})
    monkeypatch.setattr(rs, '_json_load', lambda path, default=None: {} if default is None else default)
    rs._pulse_cache.clear()

    async def rpc(http, method, params):
        rpc_calls.append(method); return {'value': [{'lamports': 3_000_000_000, 'data': ['', 'base64']} for _ in params[0]]}

    async def circle(method, path, body=None):
        return {'wallets': [{'id': 'c', 'address': RES, 'blockchain': 'SOL', 'balances': []}]}
    monkeypatch.setattr(rs, '_rpc', rpc); monkeypatch.setattr(rs, '_circle', circle)
    out = asyncio.run(rs.admin_money_pulse(None))
    assert rpc_calls == ['getMultipleAccounts']
    assert out['reserves']['s1']['poolSol'] == 3.0 and out['circle']['up'] and out['circle']['wallets'][0]['address'] == RES
    assert any(c['key'] == 'jup' for c in out['checks'])
    assert asyncio.run(rs.admin_money_pulse(None)).get('cached')


def test_card_edit_and_catalog(monkeypatch, tmp_path):
    """Owner edits a badge card; the catalog carries the look plus what the card earns from pools."""
    monkeypatch.setattr(rs, 'CARDS_PATH', tmp_path / 'cards.json')
    monkeypatch.setattr(rs, 'COLLECTION_PATH', tmp_path / 'col.json')
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'Owner')
    monkeypatch.setattr(rs, '_admin_load', lambda: {'badges': {'W1': {'custom-og': {'id': 'custom-og', 'label': 'OG', 'icon': '⭐', 'tone': 'gold'}}}})
    monkeypatch.setattr(rs, '_admin_save', lambda d: None); monkeypatch.setattr(rs, '_audit', lambda *a: None)
    monkeypatch.setattr(rs, '_seasons', lambda: {'seasons': [], 'scores': {}})
    monkeypatch.setattr(rs, '_pools', lambda: {'pools': [{'name': 'OG pool', 'mode': 'pct', 'weights': {'badge:custom-og': 30}, 'payouts': [{'perKey': {'badge:custom-og': 0.2}}]}]})
    rs._cards_cache.clear()

    class Req:
        async def json(self): return {'title': 'Original Gangster', 'design': 'glitch', 'lore': 'Here before the chart.'}
    card = asyncio.run(rs.admin_card_edit(Req(), 'badge:custom-og'))
    assert card['title'] == 'Original Gangster' and card['design'] == 'glitch' and card['holders'] == 1
    assert card['earnedEach'] == 0.2 and card['earns'][0]['pct'] == 30
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_card_edit(Req(), 'nope:<script>'))
