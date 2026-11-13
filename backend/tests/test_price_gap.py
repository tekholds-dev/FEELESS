"""📐 L02 price gaps: the same token across its real pools — the cheap pool, the rich one, the gap after costs, open only on a 2nd read."""
import price_gap as pg

M, SOL, USDC = 'TOKmint1111111111111111111111111111111111', 'So11111111111111111111111111111111111111112', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'


def pair(dex, px, base=M, quote=USDC, liq=200_000, vol=50_000, tx=40, nat=None, addr=None):
    return {'chainId': 'solana', 'dexId': dex, 'pairAddress': addr or f'P{dex}{px}', 'priceUsd': str(px), 'priceNative': str(nat if nat is not None else px),
            'baseToken': {'address': base, 'symbol': 'TOK' if base == M else 'SOL'}, 'quoteToken': {'address': quote, 'symbol': 'USDC' if quote == USDC else 'TOK'},
            'liquidity': {'usd': liq}, 'volume': {'h24': vol}, 'txns': {'h1': {'buys': tx // 2, 'sells': tx - tx // 2}}}


def test_the_gap_is_richest_over_cheapest_after_a_swap_each_side_and_thin_or_dead_pools_are_left_out():
    ps = [pair('raydium', 1.00), pair('orca', 1.012), pair('meteora', 1.05, liq=5_000), pair('lifinity', 0.90, vol=100), pair('pumpswap', 0.95, tx=0)]
    g = pg.gaps(ps, [M])[0]
    assert g['n'] == 2 and g['lo']['dex'] == 'raydium' and g['hi']['dex'] == 'orca'
    assert g['gapPct'] == 1.2 and g['netPct'] == round(1.2 - 2 * pg.COST_PCT, 3) and g['pools'][-1]['at'] == 1.2


def test_a_token_on_the_quote_side_is_priced_from_usd_over_native_and_one_pool_is_no_gap():
    ps = [pair('raydium', 150.0, base=SOL, quote=M, nat=150.0), pair('orca', 1.01)]   # SOL/TOK: 1 SOL = 150 TOK at $150 → TOK = $1.00
    g = pg.gaps(ps, [M])[0]
    assert round(g['lo']['px'], 6) == 1.0 and g['lo']['vs'] == 'SOL' and g['hi']['dex'] == 'orca'
    assert pg.gaps([pair('raydium', 1.0)], [M]) == [] and pg.gaps([], [M]) == []


def test_a_gap_opens_only_on_its_second_read_and_closes_when_costs_eat_it():
    book = {}
    wide = [pair('raydium', 1.0), pair('orca', 1.02)]
    assert pg.persist(book, pg.gaps(wide, [M]), 100.0)[0]['open'] is False   # one read: maybe a stale row
    g = pg.persist(book, pg.gaps(wide, [M]), 160.0)[0]
    assert g['open'] is True and g['openSec'] == 60
    shut = pg.persist(book, pg.gaps([pair('raydium', 1.0), pair('orca', 1.003)], [M]), 220.0)[0]
    assert shut['open'] is False and M not in book
    pg.persist(book, pg.gaps(wide, [M]), 300.0); assert pg.persist(book, [], 300.0 + pg.FORGET_SEC + 1) == [] and book == {}


def test_only_pools_against_sol_usdc_or_usdt_count_an_exotic_stable_invents_no_gap():
    ONE = 'ONEstable11111111111111111111111111111111'
    ps = [pair('raydium', 1.0), pair('orca', 1.001), pair('orca', 1.05, quote=ONE, addr='PX')]
    g = pg.gaps(ps, [M])[0]
    assert g['n'] == 2 and g['hi']['dex'] == 'orca' and g['gapPct'] == 0.1


def test_site11_one_coins_gap_before_buying_reads_once_a_minute_keeps_the_last_good_answer_and_refuses_junk(monkeypatch):
    """SITE-11 (Q23): GET /api/reputation/price-gap/{mint} = one coin's gap board, faked DexScreener (never the network)."""
    import asyncio
    import pytest
    import reputation_service as rs
    mint = 'So11111111111111111111111111111111111111112'[:-1] + '3'
    calls = []

    class R:
        def __init__(self, body, code=200): self.body, self.status_code = body, code
        def json(self): return self.body

    answers = [[pair('raydium', 1.0, base=mint), pair('orca', 1.02, base=mint), pair('meteora', 1.5, base=mint, liq=10)], [], [pair('raydium', 1.0, base=mint)]]

    class H:
        async def get(self, url, timeout=None):
            calls.append(url); return R(answers[min(len(calls) - 1, 2)])
    monkeypatch.setattr(rs, '_ai_http', lambda: H())
    rs._pgap_coin.clear()
    now = [1000.0]
    monkeypatch.setattr(rs.time, 'time', lambda: now[0])
    v = asyncio.run(rs.coin_price_gap(mint))
    assert v['gap']['lo']['dex'] == 'raydium' and v['gap']['hi']['dex'] == 'orca' and v['realPools'] == 2 and v['pools'] == 3 and v['gap']['open'] is False
    assert asyncio.run(rs.coin_price_gap(mint)) is v and len(calls) == 1              # cached for a minute
    now[0] += 61
    assert asyncio.run(rs.coin_price_gap(mint)) is v and len(calls) == 2              # a failed read keeps the last good board
    now[0] += 61
    one = asyncio.run(rs.coin_price_gap(mint))
    assert one['gap'] is None and one['realPools'] == 1 and one['answered'] is True    # one pool = no gap to measure
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.coin_price_gap('not-a-mint/../x'))


def test_site8_ten_callers_missing_the_cache_together_share_one_dexscreener_read(monkeypatch):
    """Load test finding (SITE-8): concurrent cache misses used to fire one outside read each."""
    import asyncio
    import reputation_service as rs
    mint = 'So11111111111111111111111111111111111111112'[:-1] + '4'
    calls = []

    class R:
        status_code = 200
        def json(self): return [pair('raydium', 1.0, base=mint), pair('orca', 1.01, base=mint)]

    class H:
        async def get(self, url, timeout=None):
            calls.append(url); await asyncio.sleep(0.05); return R()
    monkeypatch.setattr(rs, '_ai_http', lambda: H())
    rs._pgap_coin.clear()

    async def many():
        return await asyncio.gather(*(rs.coin_price_gap(mint) for _ in range(10)))
    out = asyncio.run(many())
    assert len(calls) == 1 and all(o is out[0] for o in out) and out[0]['gap']['n'] == 2 and not rs._pgap_fly
