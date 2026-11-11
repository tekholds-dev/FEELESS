"""💸 A real send survives a spent primary: the same signed bytes go to the next keyed lane that takes them; a refusal never took them."""
import asyncio

import pytest

import trading as tr


class _Res:
    def __init__(self, code, body):
        self.status_code = code; self._b = body

    def json(self):
        return self._b

    def raise_for_status(self):
        return None


class _Http:
    is_closed = False

    def __init__(self, plan):
        self.plan = plan; self.seen = []

    async def post(self, url, json=None, timeout=None):
        self.seen.append((url, json['method'], json['params'][0] if json['params'] else None))
        return self.plan[url]


@pytest.fixture
def lanes(monkeypatch):
    for k in ('SOLANA_RPC_FALLBACKS', 'ALCHEMY_API_KEY'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv('SOLANA_RPC_URL', 'https://spent.example'); monkeypatch.setenv('SOLANA_RPC_URL_2', 'https://limited.example')
    monkeypatch.setenv('SOLANA_RPC_URL_5', 'https://up.example')
    for n in (3, 4, 6):
        monkeypatch.delenv(f'SOLANA_RPC_URL_{n}', raising=False)


def test_the_pool_holds_the_keyed_lanes_after_the_primary(lanes):
    assert tr.rpc_pool()[:3] == ['https://spent.example', 'https://limited.example', 'https://up.example']


def test_a_send_moves_past_refusals_with_the_same_signed_bytes(lanes, monkeypatch):
    svc = tr.TradingService.__new__(tr.TradingService)
    http = _Http({'https://spent.example': _Res(429, {'error': 'max usage reached'}), 'https://limited.example': _Res(200, {'error': {'code': 429, 'message': 'slow down'}}),
                  'https://up.example': _Res(200, {'result': 'SIG'})})
    svc._http = http; monkeypatch.setattr(svc, 'require_configured', lambda: None, raising=False)
    assert asyncio.run(svc.rpc('sendTransaction', ['SIGNED', {'encoding': 'base64'}])) == 'SIG'
    assert [s[0] for s in http.seen] == ['https://spent.example', 'https://limited.example', 'https://up.example'] and {s[2] for s in http.seen} == {'SIGNED'}
