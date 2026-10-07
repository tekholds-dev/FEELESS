"""📡 The browser never calls DexScreener's API itself: it goes through /api/market/* (search, tokens, pair), which fall back to
Jupiter. 2026-10-07 DexScreener's API answered empty for everyone and the site search, price chart, held signals and coin resolve —
all calling it straight from the browser — went blank with no fallback. Logos (dd.dexscreener.com) and page links are fine."""
import pathlib


def test_no_frontend_code_calls_the_dexscreener_api_directly():
    src = pathlib.Path(__file__).resolve().parents[2] / 'frontend' / 'src'
    bad = [str(p.relative_to(src)) for p in src.rglob('*.js*') if '.test.' not in p.name and 'api.dexscreener.com' in p.read_text(errors='ignore')]
    assert bad == [], f'route these through /api/market/*: {bad}'


def test_market_has_the_fallback_routes_the_browser_uses():
    m = (pathlib.Path(__file__).resolve().parents[1] / 'market.py').read_text()
    assert "@router.get('/tokens/{chain}/{mints}')" in m and 'jup_search_pairs(http_j' in m
