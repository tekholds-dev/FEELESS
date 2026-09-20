import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv


# Terminal command backend coverage: assets/intelligence/trading/docs safety and truth states
load_dotenv(Path('/app/frontend/.env'))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="module")
def api_client() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def base_url() -> str:
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL missing")
    return BASE_URL.rstrip("/")


def test_assets_endpoint_fee_defaults(api_client, base_url):
    res = api_client.get(f"{base_url}/api/market/assets", timeout=25)
    assert res.status_code == 200
    payload = res.json()
    assets = payload.get("assets", [])
    assert isinstance(assets, list)

    fee = next((a for a in assets if a.get("id") == "fee"), None)
    assert fee is not None
    assert fee.get("mint") == "49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump"
    assert fee.get("status") in ["awaiting_market", "market_observed", "provider_unavailable"]


def test_trading_status_surface(api_client, base_url):
    res = api_client.get(f"{base_url}/api/trading/status", timeout=20)
    assert res.status_code == 200
    data = res.json()
    assert data.get("provider") == "Jupiter"
    assert data.get("network") == "solana-mainnet"
    assert data.get("fee_back_status") == "PLANNED"
    assert "solana" in data.get("supported_execution_chains", [])


def test_quote_sol_to_usdc_success(api_client, base_url):
    payload = {
        "input_mint": "So11111111111111111111111111111111111111112",
        "output_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "amount": "0.01",
        "slippage_bps": 50,
        "wallet": None,
    }
    res = api_client.post(f"{base_url}/api/trading/quote", json=payload, timeout=40)
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body.get("order_id"), str)
    assert body["quote"].get("outAmount") is not None
    assert body.get("fee_back", {}).get("status") == "PLANNED"


def test_quote_fee_pair_surfaces_real_provider_state(api_client, base_url):
    payload = {
        "input_mint": "So11111111111111111111111111111111111111112",
        "output_mint": "49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump",
        "amount": "0.01",
        "slippage_bps": 50,
        "wallet": None,
    }
    res = api_client.post(f"{base_url}/api/trading/quote", json=payload, timeout=40)
    assert res.status_code in [200, 400, 503]
    if res.status_code != 200:
        detail = str(res.json()).lower()
        assert any(term in detail for term in ["route", "jupiter", "unavailable", "error"])


def test_quote_rejects_invalid_mint(api_client, base_url):
    res = api_client.post(
        f"{base_url}/api/trading/quote",
        json={
            "input_mint": "invalidmint",
            "output_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "amount": "0.01",
            "slippage_bps": 50,
            "wallet": None,
        },
        timeout=25,
    )
    assert res.status_code == 400
    assert "invalid solana public key" in str(res.json()).lower()


def test_quote_rejects_same_token(api_client, base_url):
    mint = "So11111111111111111111111111111111111111112"
    res = api_client.post(
        f"{base_url}/api/trading/quote",
        json={"input_mint": mint, "output_mint": mint, "amount": "0.01", "slippage_bps": 50, "wallet": None},
        timeout=25,
    )
    assert res.status_code == 400
    assert "different input and output" in str(res.json()).lower()


def test_quote_rejects_invalid_slippage(api_client, base_url):
    res = api_client.post(
        f"{base_url}/api/trading/quote",
        json={
            "input_mint": "So11111111111111111111111111111111111111112",
            "output_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "amount": "0.01",
            "slippage_bps": 501,
            "wallet": None,
        },
        timeout=25,
    )
    assert res.status_code == 422


def test_quote_rejects_precision_overflow(api_client, base_url):
    res = api_client.post(
        f"{base_url}/api/trading/quote",
        json={
            "input_mint": "So11111111111111111111111111111111111111112",
            "output_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "amount": "0.0000000001",
            "slippage_bps": 50,
            "wallet": None,
        },
        timeout=25,
    )
    assert res.status_code == 400
    assert "invalid amount" in str(res.json()).lower()


def test_intelligence_tape_has_lineage_fields(api_client, base_url):
    res = api_client.get(
        f"{base_url}/api/intelligence/tape",
        params={"chain": "solana", "venue": "all", "context": "solana", "limit": 20},
        timeout=20,
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data.get("events"), list)
    assert isinstance(data.get("unsupported"), list)
    if data["events"]:
        event = data["events"][0]
        assert event.get("provider")
        assert event.get("observed_at")
        assert event.get("pair") and event["pair"].get("pairAddress")


def test_scan_contract_case_sensitivity_solana(api_client, base_url):
    exact = "So11111111111111111111111111111111111111112"
    lower = exact.lower()
    exact_res = api_client.get(f"{base_url}/api/market/scan", params={"address": exact, "context": "solana"}, timeout=20)
    lower_res = api_client.get(f"{base_url}/api/market/scan", params={"address": lower, "context": "solana"}, timeout=20)
    assert exact_res.status_code == 200
    assert lower_res.status_code == 200
    exact_pairs = exact_res.json().get("pairs", [])
    lower_pairs = lower_res.json().get("pairs", [])
    assert len(lower_pairs) <= len(exact_pairs)


def test_whitepaper_web_has_25_chapters_and_targets(api_client, base_url):
    res = api_client.get(f"{base_url}/api/docs/whitepaper", timeout=20)
    assert res.status_code == 200
    data = res.json()
    chapters = data.get("chapters", [])
    assert len(chapters) == 25
    all_text = " ".join(c.get("text", "") for c in chapters)
    assert "Q2 2027" in all_text
    assert "70% Liquidity & Ecosystem" in all_text
    assert "$60" in all_text or "60" in all_text


def test_whitepaper_pdf_headers_inline_and_attachment(api_client, base_url):
    inline = api_client.get(f"{base_url}/api/docs/whitepaper.pdf", timeout=45)
    assert inline.status_code == 200
    assert "application/pdf" in inline.headers.get("content-type", "")
    assert "inline" in inline.headers.get("content-disposition", "").lower()
    assert len(inline.content) > 10000

    attachment = api_client.get(f"{base_url}/api/docs/whitepaper.pdf", params={"download": "true"}, timeout=45)
    assert attachment.status_code == 200
    assert "attachment" in attachment.headers.get("content-disposition", "").lower()


def test_whitepaper_pdf_text_matches_key_statements(api_client, base_url):
    try:
        from pypdf import PdfReader
    except Exception:
        pytest.skip("pypdf unavailable in environment")

    res = api_client.get(f"{base_url}/api/docs/whitepaper.pdf", timeout=45)
    assert res.status_code == 200
    assert "application/pdf" in res.headers.get("content-type", "")

    import io

    reader = PdfReader(io.BytesIO(res.content))
    # PDF line wrapping is typography, not a difference in document content.
    text = " ".join(" ".join((page.extract_text() or "") for page in reader.pages).split())
    assert "Q2 2027" in text
    assert "70% Liquidity & Ecosystem" in text
    assert "15% Marketing & Growth" in text
    assert "10% Team & Development" in text
    assert "5% Community & Airdrops" in text
    assert "$60" in text or "60" in text


def test_trading_unknown_order_guards(api_client, base_url):
    unknown = "00000000-0000-0000-0000-000000000000"

    simulate = api_client.post(f"{base_url}/api/trading/simulate", json={"order_id": unknown}, timeout=20)
    assert simulate.status_code == 409

    execute = api_client.post(
        f"{base_url}/api/trading/execute",
        json={"order_id": unknown, "signed_transaction": "A" * 120},
        timeout=20,
    )
    assert execute.status_code == 404

    check = api_client.get(f"{base_url}/api/trading/order/{unknown}", timeout=20)
    assert check.status_code == 404
