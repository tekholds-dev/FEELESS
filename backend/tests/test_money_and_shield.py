"""Live money view maths and the rug-shield verdict."""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip('solders')
import trading  # noqa: E402

rs = pytest.importorskip('reputation_service')
SOL, MEME = trading.SOL_MINT, 'Meme1111111111111111111111111111111111111111'


def iso(ago):
    return datetime.fromtimestamp(time.time() - ago, timezone.utc).isoformat()


def test_earnings_windows_and_top_coin():
    orders = [
        {'created_at': iso(60), 'in_usd': 100, 'fee_bps': 200, 'input_mint': SOL, 'output_mint': MEME},          # $2 · last hour
        {'created_at': iso(5 * 3600), 'in_usd': 50, 'fee_bps': 200, 'input_mint': MEME, 'output_mint': SOL},     # $1 · today
        {'created_at': iso(3 * 86400), 'in_usd': 10, 'fee_bps': 100, 'input_mint': SOL, 'output_mint': 'Other'},  # $0.10 · week
        {'created_at': iso(9 * 86400), 'in_usd': 999, 'fee_bps': 200, 'input_mint': SOL, 'output_mint': MEME},   # too old
    ]
    out = trading.summarize_orders(orders)
    assert (out['hour'], out['day'], out['week'], out['trades']) == (2.0, 3.0, 3.1, 3)
    assert out['coins'][0] == {'mint': MEME, 'feesUsd': 3.0, 'trades': 2}


def test_shield_danger_on_blocklisted_creator_or_heavy_dev_bag():
    assert rs.shield_verdict({'flags': [], 'devHoldingPct': 2}, {})['level'] == 'ok'
    assert rs.shield_verdict({'flags': ['Top 10 wallets hold 40%'], 'devHoldingPct': 2}, {})['level'] == 'caution'
    assert rs.shield_verdict({'flags': [], 'devHoldingPct': 25}, {})['level'] == 'danger'
    bad = rs.shield_verdict({'flags': [], 'creator': 'Dev1'}, {'Dev1': {'reported': True}})
    assert bad['level'] == 'danger' and 'blocklist' in bad['reasons'][0]


def test_feeless_wallets_can_never_be_blocklisted(monkeypatch, tmp_path):
    path = tmp_path / 'blocklist.json'
    path.write_text('{"wallets": {"%s": {"reported": true}, "Bad1": {"reported": true}}}' % rs.FEE_CREATOR_WALLET)
    monkeypatch.setattr(rs, 'BLOCK_PATH', path)
    wallets = rs._block_load()['wallets']
    assert rs.FEE_CREATOR_WALLET not in wallets and 'Bad1' in wallets
    assert rs.shield_verdict({'flags': [], 'creator': rs.FEE_CREATOR_WALLET}, wallets)['level'] == 'ok'


def test_profile_backdrops_free_basic_and_tiered_animated():
    free = [k for k, v in rs.PROFILE_THEMES.items() if v == 0]
    assert {'midnight', 'graphite', 'grid', 'feeglow'} <= set(free)
    assert rs.PROFILE_THEMES['alpha'] == 2 and rs.PROFILE_THEMES['whale'] == 3
    assert rs._clean_profile({'theme': 'not-a-theme'})['theme'] == 'grid'
