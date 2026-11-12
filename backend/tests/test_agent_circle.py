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

    async def circle(method, path, body=None, agent=False):
        calls['sign'] += 1
        return {'signedTransaction': 'SIGNED', 'signature': 'SIGC1'}

    async def krpc(http, method, params):
        calls['send'] += 1
        return 'SIGC1'
    monkeypatch.setattr(rs, '_circle_wallets_live', wallets)
    monkeypatch.setattr(rs, '_circle', circle)
    monkeypatch.setattr(rs, '_krpc', krpc)

    async def quiet(signed, sig, seconds=75):
        calls['loop'] = sig
    monkeypatch.setattr(rs, '_agent_send_loop', quiet)
    monkeypatch.setattr(rs, '_internal_key', lambda: 'IK')
    c = TestClient(rs.app)
    h = {'x-feeless-internal': 'IK'}
    body = {'key': 'feeless-leader-p1', 'tx': 'B64', 'walletId': 'w-1', 'address': 'ADDR1', 'catId': 'leader'}
    # the signer policy itself is tested on real transactions in test_cat_fund; here: a refusal signs nothing, a pass signs once
    monkeypatch.setattr(rs._cfund, 'agent_tx_policy', lambda tx, addr, sol_to=(): 'a SOL transfer to someone else')
    assert c.post('/api/reputation/internal/agent-circle-send', json=body, headers=h).status_code == 403
    monkeypatch.setattr(rs._cfund, 'agent_tx_policy', lambda tx, addr, sol_to=(): None)
    assert c.post('/api/reputation/internal/agent-circle-send', json=body).status_code == 403             # no internal key
    assert c.post('/api/reputation/internal/agent-circle-send', json={**body, 'address': 'OTHER'}, headers=h).status_code == 403
    assert c.post('/api/reputation/internal/agent-circle-send', json=body, headers=h).json()['signature'] == 'SIGC1'
    assert c.post('/api/reputation/internal/agent-circle-send', json=body, headers=h).json()['again'] is True
    assert calls == {'sign': 1, 'send': 1, 'loop': 'SIGC1'}


def _circle_cat(rec):
    return {'id': 'c1', 'mode': 'real', 'agentWallet': {'address': 'AD', 'provider': 'circle', 'circleId': 'w', 'mode': 'auto'}, 'agentTx': [rec],
            'proposals': [{'id': 'p1', 'side': 'buy', 'mint': 'M', 'status': 'pending', 'at': 1, 'until': 1e12, 'agentTx': 'k'}]}


class _Rpc:
    def __init__(self, status=200, value=(None,)):
        self.status, self.value = status, value

    async def post(self, url, **k):
        status, value = self.status, self.value

        class R:
            status_code = status

            def json(self):
                return {'result': {'value': list(value)}} if status == 200 else {}
        return R()


def test_a_send_the_chain_never_saw_cannot_hold_the_wallet_forever():
    rec = {'pid': 'p1', 'side': 'buy', 'status': 'pending', 'sig': 'S', 'at': 1000, 'key': 'k'}
    cat = _circle_cat(rec)
    asyncio.run(at.poll(_Rpc(), '', cat, 1000 + at.NEVER_LANDED_S - 1))
    assert rec['status'] == 'pending' and at.in_flight(cat)                  # still inside the window: it may land
    asyncio.run(at.poll(_Rpc(), '', cat, 1000 + at.NEVER_LANDED_S))
    assert rec['status'] == 'failed' and 'never landed' in rec['error'] and not at.in_flight(cat)   # the wallet is free for the next buy or sell
    assert cat['proposals'][0]['status'] == 'failed' and 'no funds moved' in cat['proposals'][0]['why2']


def test_a_dead_rpc_is_never_read_as_a_dropped_trade():
    rec = {'pid': 'p1', 'side': 'buy', 'status': 'pending', 'sig': 'S', 'at': 1000, 'key': 'k'}
    cat = _circle_cat(rec)
    asyncio.run(at.poll(_Rpc(status=503), '', cat, 1000 + 10 * at.NEVER_LANDED_S))
    assert rec['status'] == 'pending'                                       # no answer proves nothing: a trade that may have landed is never written off


def test_a_seen_but_unconfirmed_signature_keeps_waiting_and_a_landed_one_settles():
    rec = {'pid': 'p1', 'side': 'buy', 'status': 'pending', 'sig': 'S', 'at': 1000, 'key': 'k'}
    cat = _circle_cat(rec)
    asyncio.run(at.poll(_Rpc(value=({'confirmationStatus': 'processed', 'err': None},)), '', cat, 1000 + 10 * at.NEVER_LANDED_S))
    assert rec['status'] == 'pending'
    asyncio.run(at.poll(_Rpc(value=({'confirmationStatus': 'finalized', 'err': None},)), '', cat, 1000 + 10 * at.NEVER_LANDED_S))
    assert rec['status'] == 'success' and cat['proposals'][0]['status'] == 'done'


def test_a_send_is_rebroadcast_until_the_chain_has_it_and_never_signed_twice(monkeypatch):
    import pytest
    rs = pytest.importorskip('reputation_service')
    sent, reads = [], [{'value': [None]}, {'value': [{'confirmationStatus': 'processed'}]}]

    async def broadcast(http, signed):
        sent.append(signed)
        return 3

    async def krpc(http, method, params):
        return reads.pop(0)

    async def nap(_s):
        return None
    monkeypatch.setattr(rs, '_rpc_broadcast', broadcast)
    monkeypatch.setattr(rs, '_krpc', krpc)
    monkeypatch.setattr(rs.asyncio, 'sleep', nap)
    asyncio.run(rs._agent_send_loop('SIGNED', 'SIG'))
    assert sent == ['SIGNED', 'SIGNED'] and not reads                       # the same bytes, so the same signature: it can only land once
