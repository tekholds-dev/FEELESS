"""🏦 The agent treasury: its coin's creator fees read from the right vaults, a split that always adds to 100 (buyback capped), the plan per part."""
import asyncio

import pytest


def test_split_is_clean_and_buyback_capped():
    tr = pytest.importorskip('agent_treasury')
    assert tr.clean_split({'holder': 60, 'credit': 30, 'buyback': 10}) == {'holder': 60, 'credit': 30, 'buyback': 10}
    assert tr.clean_split({'holder': 60, 'credit': 30, 'buyback': 30}) == tr.DEFAULT_SPLIT          # not 100
    assert tr.clean_split({'holder': 20, 'credit': 20, 'buyback': 60}) == tr.DEFAULT_SPLIT          # buyback over its cap
    assert tr.plan(1_000_000_001, {'holder': 50, 'credit': 30, 'buyback': 20}) == {'holder': 500_000_000, 'credit': 300_000_000, 'buyback': 200_000_000}


def test_reads_both_vaults_minus_the_rent_floor():
    tr = pytest.importorskip('agent_treasury')
    creator = 'HjJpRhG8' + 'a' * 0
    creator = 'So11111111111111111111111111111111111111112'
    seen = []

    async def rpc(http, method, params):
        seen.append((method, params[0]))
        return {'value': {'lamports': tr.RENT_FLOOR + 5_000}} if method == 'getAccountInfo' else {'value': {'amount': '7000'}}
    out = asyncio.run(tr.read(None, rpc, creator))
    assert out == {'pump': 5_000, 'pumpSwap': 7_000, 'total': 12_000}
    assert seen[0] == ('getAccountInfo', str(tr.pump_vault(creator))) and seen[1] == ('getTokenAccountBalance', str(tr.swap_vault(creator)))

    async def down(http, method, params):
        raise RuntimeError('rpc down')
    assert asyncio.run(tr.read(None, down, creator)) == {'pump': 0, 'pumpSwap': 0, 'total': 0}
