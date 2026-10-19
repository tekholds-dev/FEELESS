"""🐱 FeeCat eats only arena / agent coins, and her paper trail restarted once (owner, 2026-10-15)."""
import asyncio


def test_pool_is_agents_first_then_arena_one_row_per_pool_no_dollar_tickers():
    import reputation_service as rs
    kr = [{'pairAddress': 'P1', 'mint': 'M1', 'symbol': 'AAA', 'tag': '🤖 READY'}, {'pairAddress': 'P2', 'mint': 'M2', 'symbol': 'USDX'}]
    ar = [{'pairAddress': 'P1', 'mint': 'M1', 'symbol': 'AAA'}, {'pairAddress': 'P3', 'mint': 'M3', 'symbol': 'BBB', 'divisionLabel': 'Volume'}]
    rows = rs.feecat_pool_rows(kr, ar)
    assert [(r['pairAddress'], r['src']) for r in rows] == [('P1', 'agents'), ('P3', 'arena')]


def test_fee_reads_only_the_pool_and_restarts_her_paper_trail_once(tmp_path, monkeypatch):
    import feecat_service as fs
    class R:
        def __init__(self, d): self.d = d
        def json(self): return self.d
    class H:
        async def get(self, url, **k):
            assert url == fs.POOL_URL   # never the raw market feed
            return R({'rows': [{'pairAddress': 'P1', 'mint': 'M1', 'src': 'agents', 'why': 'READY'}]})
    async def prices(http, mints):   # her coin's deepest SOL pool, by mint
        return {m: {'pairAddress': 'P1', 'baseToken': {'symbol': 'AAA'}} for m in mints}
    monkeypatch.setattr(fs, '_sol_pairs', prices)
    got = asyncio.run(fs._market_candidates(H()))
    assert got == [{'pairAddress': 'P1', 'baseToken': {'symbol': 'AAA'}, '_src': 'agents', '_srcWhy': 'READY', '_read': None, '_duo': None}]
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path)
    store = {'cats': {'x': {'id': 'x', 'engine': 'live-v2', 'balanceSol': 3, 'startingBalanceSol': 25, 'exits': [{'a': 1}], 'positions': [{'p': 1}]}}, 'events': [{'e': 1}]}
    fs._migrate(store)
    c = store['cats']['x']
    assert c['engine'] == fs.ENGINE_VERSION and c['positions'] == [] and c['exits'] == [] and c['balanceSol'] == 25 and store['events'] == []
    assert (tmp_path / 'feecats_before_arena1015.json').exists()


def test_the_learning_lane_takes_the_3h_to_3_day_gap_at_quarter_size():
    import feecat_service as fs, time
    now = time.time()
    p = lambda **k: {'quoteToken': {'symbol': 'SOL'}, 'pairCreatedAt': (now - k.get('age', 10) * 3600) * 1000, 'liquidity': {'usd': k.get('liq', 30_000)},
                     'volume': {'h1': k.get('v', 20_000)}, 'txns': {'h1': {'buys': k.get('b', 60), 'sells': 30}}, 'priceChange': {'m5': k.get('m5', 1), 'h1': 10}}
    assert fs._learn_qualifies(p(), now)[0] is not None and 'quarter size' in fs._learn_qualifies(p(), now)[1]
    assert fs._learn_qualifies(p(age=100), now)[1] == 'not in the learning window' and fs._learn_qualifies(p(liq=5000), now)[1] == 'thin liquidity'
    assert fs._learn_qualifies(p(b=20), now)[1] == 'buyers not ahead' and fs._learn_qualifies(p(m5=-6), now)[1] == '5m momentum'
