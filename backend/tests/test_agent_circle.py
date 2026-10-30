import asyncio
import json
import agent_trade as at

SOL = at.SOL


class R:
    def __init__(self, code, body):
        self.status_code, self._b, self.content, self.headers = code, body, b'x', {'content-type': 'application/json'}

    def json(self):
        return self._b


class Http:
    def __init__(self, sig_status='confirmed'):
        self.sent, self.sig_status = [], sig_status

    async def get(self, url, **k):
        return R(200, {'tokens': [{'mint': SOL, 'amount': 1.0}]})

    async def post(self, url, json=None, **k):
        if url.endswith('/quote'):
            return R(200, {'input_mint': json['input_mint'], 'output_mint': json['output_mint'], 'quote': {'transaction': 'B64TX'}})
        if url.endswith('/agent-circle-send'):
            self.sent.append(json)
            return R(200, {'signature': 'SIGC1'})
        if url.endswith('/rpc'):
            return R(200, {'result': {'value': [{'confirmationStatus': self.sig_status, 'err': None}]}})
        return R(404, {})


def test_fee_trades_from_her_circle_wallet_with_the_same_guards_and_never_twice():
    cat = {'id': 'leader', 'mode': 'real', 'budgetSol': 0.1, 'agentWallet': {'address': 'CiRcLe1111111111111111111111111111111111111', 'provider': 'circle', 'circleId': 'w-1', 'mode': 'auto'},
           'proposals': [{'id': 'p1', 'side': 'buy', 'mint': 'MINTX', 'symbol': 'GERM', 'sol': 0.05, 'status': 'pending', 'at': 1, 'until': 1e12}]}
    http = Http()
    words = asyncio.run(at.run(http, '', cat, 2e9))
    assert http.sent and http.sent[0]['walletId'] == 'w-1' and http.sent[0]['tx'] == 'B64TX' and http.sent[0]['key'] == 'feeless-leader-p1'
    rec = cat['agentTx'][0]
    assert rec['via'] == 'circle' and rec['sig'] == 'SIGC1' and 'tx' not in rec and any('sent from its wallet' in w for w in words)
    asyncio.run(at.run(http, '', cat, 2e9 + 10))                    # next pass: confirmed on-chain → done, no second send
    assert cat['agentTx'][0]['status'] == 'success' and len(http.sent) == 1 and cat['proposals'][0]['status'] == 'done'


def test_circle_send_endpoint_signs_only_the_assigned_wallet_and_never_twice(monkeypatch):
    import pytest
    rs = pytest.importorskip('reputation_service')
    from fastapi.testclient import TestClient
    calls = {'sign': 0, 'send': 0}

    async def wallets():
        return [{'id': 'w-1', 'address': 'ADDR1'}]

    async def circle(method, path, body=None):
        calls['sign'] += 1
        return {'signedTransaction': 'SIGNED', 'signature': 'SIGC1'}

    async def krpc(http, method, params):
        calls['send'] += 1
        return 'SIGC1'
    monkeypatch.setattr(rs, '_circle_wallets_live', wallets)
    monkeypatch.setattr(rs, '_circle', circle)
    monkeypatch.setattr(rs, '_krpc', krpc)
    monkeypatch.setattr(rs, '_internal_key', lambda: 'IK')
    c = TestClient(rs.app)
    h = {'x-feeless-internal': 'IK'}
    body = {'key': 'feeless-leader-p1', 'tx': 'B64', 'walletId': 'w-1', 'address': 'ADDR1', 'catId': 'leader'}
    assert c.post('/api/reputation/internal/agent-circle-send', json=body).status_code == 403             # no internal key
    assert c.post('/api/reputation/internal/agent-circle-send', json={**body, 'address': 'OTHER'}, headers=h).status_code == 403
    assert c.post('/api/reputation/internal/agent-circle-send', json=body, headers=h).json()['signature'] == 'SIGC1'
    assert c.post('/api/reputation/internal/agent-circle-send', json=body, headers=h).json()['again'] is True
    assert calls == {'sign': 1, 'send': 1}
