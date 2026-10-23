"""🚑 The browser's RPC relay must survive a dedicated key that ran out of quota (2026-10-23: Alchemy 'Monthly capacity limit exceeded'
took every wallet action down): it falls through the pool, the keeper's own public node last. No network: httpx is faked."""
import asyncio
import json

import pytest

import reputation_service as rs


class _Resp:
    def __init__(self, code, body):
        self.status_code = code
        self.content = json.dumps(body).encode()
        self.headers = {'content-type': 'application/json'}
        self._b = body

    def json(self):
        return self._b


class _Req:
    def __init__(self, body):
        self._b = body
        self.client = type('C', (), {'host': '9.9.9.9'})()

    async def json(self):
        return self._b


def _client(answers, seen):
    class _C:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None):
            seen.append(url)
            return answers(url)
    return _C


def test_spent_answers_are_recognised():
    assert rs._relay_spent(_Resp(429, {}))
    assert rs._relay_spent(_Resp(200, {'jsonrpc': '2.0', 'error': {'code': 429, 'message': 'Monthly capacity limit exceeded'}}))
    assert rs._relay_spent(_Resp(200, [{'error': {'code': -32429}}]))
    assert not rs._relay_spent(_Resp(200, {'jsonrpc': '2.0', 'result': 123}))
    assert not rs._relay_spent(_Resp(200, {'error': {'code': -32002, 'message': 'simulation failed'}}))   # a real answer, not a quota


def test_relay_falls_through_a_spent_key(monkeypatch):
    rs._rpc_hits.clear()
    pool = ['https://dedicated', 'https://alchemy', 'https://api.mainnet-beta.solana.com', 'https://solana-rpc.publicnode.com']
    monkeypatch.setattr(rs, '_dedicated', 'https://dedicated'); monkeypatch.setattr(rs, 'RPC_POOL', pool); monkeypatch.setattr(rs, '_KEEPER_PUBLIC', 'https://api.mainnet-beta.solana.com')
    seen = []
    spent = {'https://dedicated', 'https://alchemy'}
    monkeypatch.setattr(rs.httpx, 'AsyncClient', _client(lambda u: _Resp(429, {'error': {'code': 429}}) if u in spent else _Resp(200, {'jsonrpc': '2.0', 'id': 1, 'result': 7}), seen))
    out = asyncio.run(rs.rpc_relay(_Req({'jsonrpc': '2.0', 'id': 1, 'method': 'getSlot'})))
    assert json.loads(out.body) == {'jsonrpc': '2.0', 'id': 1, 'result': 7}
    assert seen == ['https://dedicated', 'https://alchemy', 'https://solana-rpc.publicnode.com']   # the keeper's public node is spared while another answers


def test_relay_keeps_a_healthy_key(monkeypatch):
    rs._rpc_hits.clear()
    monkeypatch.setattr(rs, '_dedicated', 'https://dedicated'); seen = []
    monkeypatch.setattr(rs.httpx, 'AsyncClient', _client(lambda u: _Resp(200, {'result': 1}), seen))
    asyncio.run(rs.rpc_relay(_Req({'jsonrpc': '2.0', 'id': 1, 'method': 'getSlot'})))
    assert seen == ['https://dedicated']


@pytest.mark.parametrize('method', ['getSlot'])
def test_method_still_allow_listed(method):
    assert method in rs.RPC_ALLOW


def test_lp_reads_are_allowed_but_scans_are_not():
    """🏗 the browser reads its own LP positions (token accounts by owner) and a pool's clock (block time) — never a program-wide scan."""
    for m in ('getTokenAccountsByOwner', 'getBlockTime', 'simulateTransaction', 'sendTransaction'):
        assert m in rs.RPC_ALLOW
    assert 'getProgramAccounts' not in rs.RPC_ALLOW
