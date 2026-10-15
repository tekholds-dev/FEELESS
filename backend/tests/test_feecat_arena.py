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
            return R({'rows': [{'pairAddress': 'P1', 'src': 'agents', 'why': 'READY'}]})
    async def prices(http, pas):
        return {pa: {'pairAddress': pa, 'baseToken': {'symbol': 'AAA'}} for pa in pas}
    monkeypatch.setattr(fs, '_pair_prices', prices)
    got = asyncio.run(fs._market_candidates(H()))
    assert got == [{'pairAddress': 'P1', 'baseToken': {'symbol': 'AAA'}, '_src': 'agents', '_srcWhy': 'READY'}]
    monkeypatch.setattr(fs, 'DATA_DIR', tmp_path)
    store = {'cats': {'x': {'id': 'x', 'engine': 'live-v2', 'balanceSol': 3, 'startingBalanceSol': 25, 'exits': [{'a': 1}], 'positions': [{'p': 1}]}}, 'events': [{'e': 1}]}
    fs._migrate(store)
    c = store['cats']['x']
    assert c['engine'] == fs.ENGINE_VERSION and c['positions'] == [] and c['exits'] == [] and c['balanceSol'] == 25 and store['events'] == []
    assert (tmp_path / 'feecats_before_arena1015.json').exists()
