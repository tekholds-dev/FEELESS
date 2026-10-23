import asyncio

import my_money as mm


def test_your_money_prices_every_proved_position_and_keeps_pnl_out():
    pairs = [{'baseToken': {'address': 'A', 'symbol': 'AAA'}, 'priceUsd': '0.5', 'liquidity': {'usd': 9000}, 'priceChange': {'h24': 12.5}, 'pairAddress': 'PA'},
             {'baseToken': {'address': 'A', 'symbol': 'AAA'}, 'priceUsd': '0.6', 'liquidity': {'usd': 100}, 'pairAddress': 'thin'},     # a thin pool never sets the price
             {'baseToken': {'address': 'B', 'symbol': 'BBB'}, 'priceUsd': '0.000001', 'liquidity': {'usd': 5000}, 'pairAddress': 'PB'}]
    prices = mm.best_prices(pairs)
    assert prices['A']['priceUsd'] == 0.5 and prices['A']['pairAddress'] == 'PA'
    held = [{'mint': 'A', 'holding': 20}, {'mint': 'B', 'holding': 100}, {'mint': 'C', 'holding': 5}, {'mint': 'D', 'holding': 0}]
    blds = [{'key': 'jito', 'name': 'Jito', 'sym': 'JitoSOL', 'state': 'built', 'usd': 30, 'apy': 7.1}, {'key': 'orca', 'state': 'construction', 'usd': 0}]
    v = mm.assemble(held, prices, blds)
    assert v['total'] == 40.0 and [x['sym'] for x in v['positions']] == ['JitoSOL', 'AAA'] and v['positions'][0]['share'] == 0.75
    assert v['positions'][1]['ch24'] == 12.5 and 'pnl' not in str(v['positions']).lower()                        # value + the coin's move, never a P&L
    assert v['dust'] == 1 and v['unpriced'] == 1 and v['coins'] == 1 and v['markets'] == 1
    assert mm.assemble([], {}, []) == {'total': 0, 'positions': [], 'coins': 0, 'markets': 0, 'dust': 0, 'unpriced': 0}


def test_the_endpoint_reads_receipts_prices_and_the_block_once_per_45s(monkeypatch):
    import reputation_service as rs
    calls = []

    async def pnl(address):
        calls.append('pnl')
        return {'tokens': [{'mint': 'A', 'holding': 10}]}

    class _R:
        status_code = 200

        def json(self):
            return [{'baseToken': {'address': 'A', 'symbol': 'AAA'}, 'priceUsd': '2', 'liquidity': {'usd': 9e4}, 'pairAddress': 'PA'}]

    class _H:
        async def get(self, url, **kw):
            calls.append(url)
            return _R()

    async def block(address, session):
        return {'buildings': [{'key': 'jlp', 'sym': 'JLP', 'state': 'built', 'usd': 5.0, 'apy': 20}]}
    monkeypatch.setattr(rs, 'wallet_pnl', pnl); monkeypatch.setattr(rs, '_ai_http', lambda: _H()); monkeypatch.setattr(rs, 'familia_block', block)
    rs._mm_cache.clear()
    v = asyncio.run(rs.familia_my_money('W' * 44, 'sess'))
    assert v['total'] == 25.0 and v['markets'] == 1 and any('tokens/v1/solana/A' in str(c) for c in calls)
    n = len(calls)
    asyncio.run(rs.familia_my_money('W' * 44, 'sess'))
    assert len(calls) == n                                                                    # cached
    assert asyncio.run(rs.familia_my_money('', ''))['total'] == 0
    rs._mm_cache.clear()
