import time
import uuid


# Market feed/search/candles and chat persistence validation tests
def test_market_feed_trending_solana(api_client, base_url):
    response = api_client.get(f"{base_url}/api/market/feed", params={"kind": "trending", "chain": "solana", "page": 1}, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "DexScreener"
    assert isinstance(data["pairs"], list)
    assert data["page"] == 1
    if data["pairs"]:
        pair = data["pairs"][0]
        assert pair.get("chainId")
        assert pair.get("pairAddress")
        assert "pairCreatedAt" in pair


def test_market_feed_new_solana(api_client, base_url):
    response = api_client.get(f"{base_url}/api/market/feed", params={"kind": "new", "chain": "solana", "page": 1}, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["label"].lower().startswith("new pools")
    assert data["page"] == 1


def test_market_feed_all_chain_request(api_client, base_url):
    response = api_client.get(f"{base_url}/api/market/feed", params={"kind": "trending", "chain": "all", "page": 1}, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("pairs"), list)
    assert "stale" in data


def test_market_feed_invalid_chain(api_client, base_url):
    response = api_client.get(f"{base_url}/api/market/feed", params={"kind": "trending", "chain": "invalid-chain", "page": 1}, timeout=20)
    assert response.status_code == 400
    assert "Unsupported chain" in str(response.json())


def test_market_feed_invalid_page_bounds(api_client, base_url):
    response = api_client.get(f"{base_url}/api/market/feed", params={"kind": "trending", "chain": "solana", "page": 0}, timeout=20)
    assert response.status_code == 422
    assert "greater than or equal to 1" in response.text


def test_market_search_wrapped_sol(api_client, base_url):
    sol_ca = "So11111111111111111111111111111111111111112"
    response = api_client.get(f"{base_url}/api/market/search", params={"q": sol_ca}, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("pairs"), list)
    assert data.get("provider")


def test_market_search_empty_query_rejected(api_client, base_url):
    response = api_client.get(f"{base_url}/api/market/search", params={"q": ""}, timeout=20)
    assert response.status_code == 422


def test_market_candles_sorted_unique_timestamps(api_client, base_url):
    feed = api_client.get(f"{base_url}/api/market/feed", params={"kind": "trending", "chain": "solana", "page": 1}, timeout=20)
    assert feed.status_code == 200
    pairs = feed.json().get("pairs", [])
    assert isinstance(pairs, list)
    if not pairs:
        return

    pair = pairs[0]
    chain = pair["chainId"]
    address = pair["pairAddress"]
    candles = api_client.get(f"{base_url}/api/market/candles/{chain}/{address}", params={"interval": "1h"}, timeout=20)
    assert candles.status_code == 200
    payload = candles.json()
    rows = payload.get("candles", [])
    assert isinstance(rows, list)
    if rows:
        timestamps = [r[0] for r in rows if len(r) >= 6]
        assert timestamps == sorted(timestamps)
        assert len(timestamps) == len(set(timestamps))


def test_market_candles_invalid_interval(api_client, base_url):
    response = api_client.get(
        f"{base_url}/api/market/candles/solana/58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
        params={"interval": "2h"},
        timeout=20,
    )
    assert response.status_code == 422


def test_market_candles_invalid_chain(api_client, base_url):
    response = api_client.get(
        f"{base_url}/api/market/candles/invalid/58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
        params={"interval": "1h"},
        timeout=20,
    )
    assert response.status_code == 400
    assert "Invalid chain or pool" in str(response.json())


def test_chat_unsigned_post_is_gone_and_history_reads(api_client, base_url):
    """🔒 2026-11-11: anyone could post as anyone here (it showed in the globe bubbles); chat writes are signed in reputation_service."""
    room = f"general-{uuid.uuid4().hex[:8]}"
    r = api_client.post(f"{base_url}/api/chat/{room}", json={"username": "TEST_user", "text": "spoof"}, timeout=20)
    assert r.status_code in (404, 405)
    history = api_client.get(f"{base_url}/api/chat/{room}", params={"limit": 100}, timeout=20)
    assert history.status_code == 200 and history.json()["messages"] == []

def test_chat_blank_message_rejected(api_client, base_url):
    response = api_client.post(
        f"{base_url}/api/chat/general",
        json={"username": "TEST_user", "text": "   "},
        timeout=20,
    )
    assert response.status_code == 400
    assert "cannot be blank" in str(response.json()).lower()
