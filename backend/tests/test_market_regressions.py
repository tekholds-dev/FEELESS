from datetime import datetime, timedelta, timezone

from backend.market import MARKET_CACHE_RETENTION, is_new_pool_deal


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