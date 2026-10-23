import asyncio

import town_live as tl


def test_each_town_sign_reads_its_tools_live_number():
    s = tl.signs({
        'tt': {'coins': [{'status': 'READY'}, {'status': 'CONTENDING'}, {'status': 'ready'}]},
        'perps': {'markets': [{'coin': 'ETH', 'mark': 2400.5, 'ch24': -1.2, 'fundApr': 9, 'oiUsd': 5e8}, {'coin': 'BTC', 'mark': 67120, 'ch24': 2.04, 'fundApr': 11, 'oiUsd': 9e8}]},
        'pools': {'pools': [{'sym': 'SOL-USDC', 'tvl': 5e6, 'apy': 41.6}, {'sym': 'FARM', 'tvl': 9e6, 'apy': 4000}, {'sym': 'TINY', 'tvl': 2e4, 'apy': 90}]},
        'trades': {'open': 2, 'avgPct': 3.4, 'closed': {'n': 10, 'by': {'G4': {'n': 6, 'wonPct': 50}, 'AGENTS': {'n': 4, 'wonPct': 25}}}},
        'vault': {'strategies': [{'name': 'LST stack', 'apy': 7.94}, {'name': 'JLP', 'apy': 18.2}]},
        'radar': [{'mint': 'Apump', 'symbol': 'A', 'chg5m': 12}, {'mint': 'Bpump', 'symbol': 'B', 'chg5m': 88, 'safe': False}, {'mint': 'Cxyz', 'symbol': 'C', 'chg5m': 300}],
        'cats': {'cat': {'balanceSol': 27.5, 'startingBalanceSol': 25, 'positions': [{}]}, 'discipline': {'lives': 8}},
        'rep': {'live': [{'icon': '🚀', 'sym': 'WIF', 'move': -14.2, 'closesAt': 900}, {'sym': 'X', 'move': 3, 'closesAt': 200}]},
    })
    assert s['tt'] == {'line': '2 READY · 3 on the intake', 'v': 2, 'tone': 'hot'}
    assert s['perps']['line'] == 'BTC $67,120 · +2.0% · f +11%' and s['perps']['tone'] == 'up'       # the busiest market by open interest
    assert s['pools']['line'] == 'TOP 42% APY · SOL-USDC'                                              # a farm's 4000 % and a $20K pool never quote
    assert s['trades']['line'] == '2 open +3.4% · 10 closed, 40% won'
    assert s['vault']['line'] == 'BEST 18.2% · JLP'
    assert s['radar']['line'] == '🔥 $A +12% 5m · 1 live'                                              # a failed scan and a non-Pump coin never ride
    assert s['cats']['line'] == 'FEE 27.5 SOL +10.0% · 8/9 lives · 1 held'
    assert s['rep']['line'] == '2 live · 🚀 $WIF -14.2%'                                            # the call moving most


def test_a_missing_or_failed_source_leaves_only_that_sign_plain():
    s = tl.signs({'tt': None, 'perps': RuntimeError('down'), 'pools': {'pools': []}, 'cats': {'cat': {}}, 'rep': {'live': []}, 'trades': {'open': 0, 'closed': {}}})
    assert set(s) == {'rep', 'trades'} and s['trades'] == {'line': 'desk flat', 'v': None, 'tone': 'calm'} and s['rep']['tone'] == 'calm'
    assert all(len(v['line']) <= 48 for v in tl.signs({'radar': [{'mint': 'x' * 40 + 'pump', 'symbol': 'S' * 60, 'chg5m': 1}]}).values())


def test_the_town_live_read_is_one_cached_parallel_read(monkeypatch):
    import reputation_service as rs
    calls = []

    async def fake(name, out):
        calls.append(name)
        return out
    monkeypatch.setattr(rs, 'familia_intake', lambda: fake('tt', {'coins': [{'status': 'READY'}]}))
    monkeypatch.setattr(rs, 'familia_perps', lambda: fake('perps', {'markets': []}))
    monkeypatch.setattr(rs, 'familia_pools', lambda: fake('pools', {'pools': []}))
    monkeypatch.setattr(rs, 'familia_pools_sleep', lambda: fake('vault', {'strategies': [{'name': 'LST', 'apy': 7}]}))
    monkeypatch.setattr(rs, 'familia_trade_center', lambda a, s: fake('trades', {'open': 1, 'avgPct': -2, 'closed': {}}))
    monkeypatch.setattr(rs, 'rep_markets', lambda a: fake('rep', None))
    monkeypatch.setattr(rs, '_open_board', lambda: [])

    class _H:
        async def get(self, *a, **k):
            raise RuntimeError('feecat down')
    monkeypatch.setattr(rs, '_ai_http', lambda: _H())
    rs._town_live_cache.update(at=0.0, v=None, lock=None)
    v = asyncio.run(rs.familia_town_live())
    assert v['signs']['tt']['v'] == 1 and v['signs']['vault']['line'] == 'BEST 7.0% · LST' and v['signs']['trades']['tone'] == 'down'
    assert 'cats' not in v['signs'] and 'rep' not in v['signs']
    n = len(calls)
    asyncio.run(rs.familia_town_live())
    assert len(calls) == n                                                          # a second read inside 45 s is the cached one
    rs._town_live_cache.update(at=0.0, v=None, lock=None)
