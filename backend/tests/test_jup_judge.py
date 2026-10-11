"""🧪 The agents' newest-launch rows get Jupiter's holder audit while our own RPC scan is queued (2026-10-11: 4 empty seats, every
candidate "holders not scanned"). Same candidate + safety gates; a live mint / freeze authority is never safe."""
import reputation_service as rs

M = 'J' * 43
PAIR = {'chainId': 'solana', 'pairAddress': 'P' * 43, 'baseToken': {'address': M, 'symbol': 'NEW'}, 'priceUsd': '0.0001', 'marketCap': 300_000,
        'liquidity': {'usd': 40_000}, 'volume': {'h1': 60_000, 'm5': 6_000}, 'txns': {'h1': {'buys': 400, 'sells': 300}}, 'priceChange': {'h1': 12, 'm5': 1},
        'pairCreatedAt': 0, 'dexId': 'pumpswap'}
CLEAN = {'top10': 18.0, 'devPct': 0.5, 'dev': 'D' * 43, 'holders': 900, 'mintOff': True, 'freezeOff': True}


def test_clean_jupiter_audit_reads_as_a_holder_reading():
    got = rs._jup_judge(PAIR, M, CLEAN, rs._runner_cfg())
    assert got is not None and got[2]['top10'] == 18.0


def test_live_mint_authority_is_never_safe():
    got = rs._jup_judge(PAIR, M, {**CLEAN, 'mintOff': False}, rs._runner_cfg())
    assert got is not None and got[0] is False


def test_no_holder_figure_is_no_reading():
    assert rs._jup_judge(PAIR, M, {**CLEAN, 'top10': None}, rs._runner_cfg()) is None
    assert rs._jup_judge(PAIR, M, None, rs._runner_cfg()) is None
