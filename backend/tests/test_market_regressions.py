from datetime import datetime, timedelta, timezone

from backend.market import MARKET_CACHE_RETENTION, PROVIDER_COVERAGE, is_new_pool_deal, normalise_pump_coins


def test_new_pool_deal_requires_recent_provider_pool_and_five_percent_drawdown():
    now = datetime.now(timezone.utc).timestamp() * 1000
    day = 24 * 60 * 60 * 1000

    assert is_new_pool_deal(
        {"pairCreatedAt": now - day, "priceChange": {"h24": -5}},
        now,
    )
    assert not is_new_pool_deal(
        {"pairCreatedAt": now - (MARKET_CACHE_RETENTION.total_seconds() * 1000 + 1),
         "priceChange": {"h24": -20}},
        now,
    )
    assert not is_new_pool_deal(
        {"pairCreatedAt": now - day, "priceChange": {"h24": -4.99}},
        now,
    )
    assert not is_new_pool_deal(
        {"pairCreatedAt": now + day, "priceChange": {"h24": -20}},
        now,
    )


def test_new_pool_deal_uses_a_fourteen_day_retention_window():
    now = datetime.now(timezone.utc).timestamp() * 1000
    boundary = MARKET_CACHE_RETENTION.total_seconds() * 1000

    assert is_new_pool_deal(
        {"pairCreatedAt": now - boundary, "priceChange": {"h24": -5}},
        now,
    )
    assert not is_new_pool_deal(
        {"pairCreatedAt": now - boundary - 1, "priceChange": {"h24": -5}},
        now,
    )


def test_pump_coin_normalisation_preserves_direct_fields_and_graduation_boundary():
    pairs = normalise_pump_coins([{
        "mint": "PumpMint123",
        "name": "Pump Coin",
        "symbol": "PUMP",
        "created_timestamp": 1_700_000_000,
        "usd_market_cap": 1000,
        "virtual_sol_reserves": 999999,
        "complete": True,
        "raydium_pool": "RaydiumPool123",
    }], "new")

    assert len(pairs) == 1
    pair = pairs[0]
    assert pair["launchpadId"] == "pump"
    assert pair["marketKind"] == "launchpad-token"
    assert pair["marketStage"] == "new"
    assert pair["marketCap"] == 1000
    assert pair["liquidity"] == {}
    assert pair["graduation"] == {
        "status": "graduated",
        "pool_address": "RaydiumPool123",
        "source": "Pump.fun",
    }
    assert PROVIDER_COVERAGE["Pump.fun"]["stream"].startswith("Polling")