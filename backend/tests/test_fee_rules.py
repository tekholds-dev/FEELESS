"""Fee rules: only buying a FEELESS coin is free; coin->coin is refused; discounts never reach zero."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
rs = pytest.importorskip('reputation_service')

MEME, MEME2 = 'Meme1111111111111111111111111111111111111111', 'Meme2222222222222222222222222222222222222222'


@pytest.fixture
def fee(monkeypatch):
    cfg = {**rs.FEE_DEFAULTS, 'platformFeeBps': 1500, 'referralAccount': 'Ref', 'feeAccountSol': 'SolAcct',
           'feeAccountUsdc': 'UsdcAcct', 'tierDiscountPct': {'0': 100}, 'zeroFeeMints': [MEME]}
    monkeypatch.setattr(rs, '_fee_cfg', lambda: cfg)

    async def tier(_w):
        return (0, 0)
    monkeypatch.setattr(rs, '_perk_tier', tier)
    return lambda a, b: asyncio.run(rs.effective_fee('Wa11et', a, b))


def test_buying_a_feeless_coin_is_the_only_free_trade(fee):
    assert fee(rs.WSOL_MINT, rs.ecosystem_mints()['fee'])['bps'] == 0
    sell = fee(rs.ecosystem_mints()['fee'], rs.WSOL_MINT)
    assert sell['bps'] > 0 and sell['feeAccount'] == 'SolAcct'


def test_old_fee_free_list_and_full_discounts_no_longer_zero_the_fee(fee):
    buy = fee(rs.WSOL_MINT, MEME)  # MEME sits on the legacy zeroFeeMints list and the tier asks for 100% off
    assert buy['bps'] == 150 and buy['feeAccount'] == 'SolAcct'  # capped at 90% off
    assert buy['ultraBps'] == 150


def test_coin_to_coin_is_refused_instead_of_free(fee):
    assert 'SOL or USDC' in fee(MEME, MEME2)['blocked']


def test_saving_settings_with_nulls_or_big_numbers_is_cleaned_not_rejected():
    m = rs.FeeCfg(platformFeeBps='2500', engine=None, ultraFallback=None, feeAccountSol=None, priorityMaxLamports=None,
                  referralAccount=None, tierDiscountPct=None, promo=None, lifiIntegrator=None, lifiFeeBps='250')
    assert (m.platformFeeBps, m.engine, m.referralAccount, m.priorityMaxLamports, m.lifiFeeBps) == (rs.SWAP_MAX_BPS, 'swap', '', 200000, 250)


def test_self_test_reads_the_fee_from_either_engine():
    assert rs._quote_fee_bps({'platformFee': {'feeBps': 252, 'amount': '1'}}) == 252  # Swap API
    assert rs._quote_fee_bps({'feeBps': 255}) == 255  # Ultra
    assert rs._quote_fee_bps({}) == 0


def test_badge_perk_discount_shows_on_the_quote(monkeypatch):
    cfg = {**rs.FEE_DEFAULTS, 'platformFeeBps': 100, 'referralAccount': 'Ref', 'feeAccountSol': 'SolAcct', 'feeAccountUsdc': 'UsdcAcct', 'tierDiscountPct': {'0': 0}}
    monkeypatch.setattr(rs, '_fee_cfg', lambda: cfg)
    async def tier(_w):
        return (0, 0)
    monkeypatch.setattr(rs, '_perk_tier', tier)
    w = 'Wa11et'
    monkeypatch.setitem(rs._quest_cache, rs.primary_of(w), (0, {'perks': {'feeDiscountPct': 15, 'from': {'fee': 'FRSV Diamond Hands'}}}))
    out = asyncio.run(rs.effective_fee(w, rs.WSOL_MINT, MEME))
    assert out['bps'] == 85 and 'FRSV Diamond Hands badge: 15% off' in out['notes']
    assert not any('holder discount' in n for n in out['notes'])
