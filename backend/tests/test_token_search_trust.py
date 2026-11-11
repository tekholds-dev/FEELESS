"""🛡 The swap picker never ranks a lookalike above the real coin (owner 2026-11-11: a fake "USDC " reporting a $76B cap led the list)."""
import asyncio

import reputation_service as rs

REAL, FAKE = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', '8r5mco9UCh6Ub8dZQSvbPSmRiD6KRTcCR3ofYQeMKfxF'


class _R:
    def __init__(self, body): self.status_code, self._b = 200, body
    def json(self): return self._b


class _H:
    def __init__(self, **_k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *_a): return False

    async def get(self, url, **_k):
        if 'jup.ag' in url:
            return _R([{'id': FAKE, 'symbol': 'USDC  ', 'name': 'USD Coin', 'mcap': 76e9, 'liquidity': 9.6e8, 'isVerified': False},
                       {'id': REAL, 'symbol': 'USDC', 'name': 'USD Coin', 'mcap': 8.9e9, 'liquidity': 3.9e8, 'isVerified': True}])
        return _R({'pairs': []})


def test_a_verified_coin_outranks_a_lookalike_with_a_bigger_reported_cap(monkeypatch):
    monkeypatch.setattr(rs.httpx, 'AsyncClient', _H)
    rs._tok_search_cache.clear()
    rows = asyncio.run(rs.token_search(q='USDC'))['tokens']
    assert [r['mint'] for r in rows[:2]] == [REAL, FAKE]


def test_a_pasted_contract_still_leads(monkeypatch):
    monkeypatch.setattr(rs.httpx, 'AsyncClient', _H)
    rs._tok_search_cache.clear()
    assert asyncio.run(rs.token_search(q=FAKE))['tokens'][0]['mint'] == FAKE
