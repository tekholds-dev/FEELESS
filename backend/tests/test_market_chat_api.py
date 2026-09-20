import time
import uuid


# Market feed/search/candles and chat persistence validation tests
def test_market_feed_trending_solana(api_client, base_url):
    response = api_client.get(f"{base_url}/api/market/feed", params={"kind": "trending", "chain": "solana", "page": 1}, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] in ["GeckoTerminal", "DexScreener"]
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


def test_chat_post_and_history_order(api_client, base_url):
    room = f"general-{uuid.uuid4().hex[:8]}"
    payload_1 = {"username": "TEST_user", "text": "first test message"}
    payload_2 = {"username": "TEST_user", "text": "second test message"}

    first = api_client.post(f"{base_url}/api/chat/{room}", json=payload_1, timeout=20)
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["room"] == room
    assert first_data["text"] == payload_1["text"]
    assert isinstance(first_data["ts"], int)

    time.sleep(0.05)
    second = api_client.post(f"{base_url}/api/chat/{room}", json=payload_2, timeout=20)
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["text"] == payload_2["text"]

    history = api_client.get(f"{base_url}/api/chat/{room}", params={"limit": 100}, timeout=20)
    assert history.status_code == 200
    messages = history.json().get("messages", [])
    assert len(messages) >= 2

    ids = [m["id"] for m in messages]
    assert first_data["id"] in ids
    assert second_data["id"] in ids

    ts_values = [m["ts"] for m in messages]
    assert ts_values == sorted(ts_values)


def test_chat_blank_message_rejected(api_client, base_url):
    response = api_client.post(
        f"{base_url}/api/chat/general",
        json={"username": "TEST_user", "text": "   "},
        timeout=20,
    )
    assert response.status_code == 400
    assert "cannot be blank" in str(response.json()).lower()
