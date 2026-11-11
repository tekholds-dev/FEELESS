"""🧯 A refused read backs off instead of hammering the provider (owner 2026-11-11: 417 refusals in 10 min with one user)."""
import asyncio

import pump_network as pn


def test_a_refused_sol_price_waits_a_minute_and_keeps_the_last_price(monkeypatch):
    calls = []

    class H:
        def __init__(self, **_k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_a): return False
        async def get(self, url, **_k):
            calls.append(url); raise RuntimeError('429')
    monkeypatch.setattr(pn.httpx, 'AsyncClient', H)
    net = pn.PumpNetwork.__new__(pn.PumpNetwork); net.sol_usd, net._sol_at = 84.8, 0
    assert asyncio.run(net.sol_price()) == 84.8
    n = len(calls)
    for _ in range(5):
        assert asyncio.run(net.sol_price()) == 84.8
    assert len(calls) == n   # no new calls inside the minute
