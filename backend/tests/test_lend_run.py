import lend_earn as le

USDC, SOL = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'So11111111111111111111111111111111111111112'
TOKENS = [{'address': 'jlUSDS', 'decimals': 6, 'totalRate': '900', 'asset': {'address': 'USDSwr9ApdHk5bvJKMjzff41FfuX8bSxdKcR81vTwcA', 'decimals': 6, 'price': '1'}},
          {'address': 'jlSOL', 'decimals': 9, 'totalRate': '383', 'asset': {'address': SOL, 'decimals': 9, 'price': '100'}},
          {'address': 'jlUSDC', 'decimals': 6, 'totalRate': '728', 'asset': {'address': USDC, 'decimals': 6, 'price': '1'}}, 'junk']


def test_the_run_offers_usdc_then_sol_at_the_live_rate():
    a = le.run_assets(TOKENS)
    assert [x['sym'] for x in a] == ['USDC', 'SOL'] and a[0]['apy'] == 7.28 and a[0]['jl'] == 'jlUSDC' and a[1]['price'] == 100
    assert le.run_assets(None) == []


def test_positions_are_the_wallets_own_deposits_worth_now_with_jupiters_earnings():
    a = le.run_assets(TOKENS)
    pos = [{'token': {'address': 'jlUSDC'}, 'shares': '4690000', 'underlyingAssets': '5000420'},
           {'token': {'address': 'jlSOL'}, 'shares': '0', 'underlyingAssets': '0', 'underlyingBalance': '11946494'},   # wallet SOL, not deposited
           {'token': {'address': 'jlUSDS'}, 'shares': '9', 'underlyingAssets': '9'}, {'nope': 1}]
    r = le.run_positions(pos, a, {'jlUSDC': '420'})
    assert len(r) == 1 and r[0]['sym'] == 'USDC' and r[0]['balance'] == 5.00042 and r[0]['usd'] == 5.00042 and r[0]['earned'] == 0.00042


def test_the_route_reads_the_wallets_run(monkeypatch):
    import reputation_service as rs
    from fastapi.testclient import TestClient
    seen = []

    async def fake(method, path, **kw):
        seen.append((path, kw.get('params')))
        if path == 'earn/tokens':
            return 200, TOKENS
        if path == 'earn/positions':
            return 200, [{'token': {'address': 'jlUSDC'}, 'shares': '1', 'underlyingAssets': '5000420'}]
        return 200, [{'address': 'jlUSDC', 'earnings': '420'}]
    monkeypatch.setattr(rs, '_jl_lend', fake); rs._frun_tok.clear()
    me = 'H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS'
    b = TestClient(rs.app).get('/api/reputation/familia-pools/run', params={'address': me}).json()
    assert b['minUsd'] == 5 and [x['sym'] for x in b['assets']] == ['USDC', 'SOL']
    assert b['positions'][0]['earned'] == 0.00042 and ('earn/earnings', {'user': me, 'positions': 'jlUSDC'}) in seen
