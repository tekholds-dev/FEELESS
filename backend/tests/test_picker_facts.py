import asyncio
import pytest


def test_picker_rows_carry_holder_facts_from_the_cache_and_drop_dead_coins(monkeypatch):
    rs = pytest.importorskip('reputation_service')

    async def raw(lens, chain):
        return {'lens': lens, 'pools': [{'baseAddress': 'SCANNED', 'vol1h': 40_000}, {'baseAddress': 'FRESH', 'vol1h': 20_000},
                                        {'baseAddress': 'DEAD', 'vol1h': 900}]}
    monkeypatch.setattr(rs, '_fuses_discover_raw', raw)
    rs._intel_cache['SCANNED'] = (9e12, {'top10Pct': 18.0, 'devHoldingPct': 2.0, 'insidersHoldingPct': 4.0, 'bundledWallets': ['a', 'b'],
                                         'sniperWallets': ['s'], 'bundledHoldingPct': 1.5})
    rs._intel_cache.pop('FRESH', None)
    out = asyncio.run(rs.fuses_discover(lens='movers', chain='solana'))
    by = {r['baseAddress']: r for r in out['pools']}
    assert 'DEAD' not in by and out['dead'] == 1
    assert by['SCANNED']['scanned'] and by['SCANNED']['insiders'] == 4.0 and by['SCANNED']['bundledN'] == 2 and by['SCANNED']['snipersN'] == 1
    assert by['FRESH']['scanned'] is False
    rs._intel_cache.pop('SCANNED', None)
