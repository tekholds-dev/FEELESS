"""Small networks load coins from GeckoTerminal's per-network pools."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from launchpad_board import gecko_network_pairs  # noqa: E402


def test_gecko_network_pools_become_chain_pairs():
    payload = {'data': [{'attributes': {'address': '0xpool', 'base_token_price_usd': '0.12', 'fdv_usd': '1200000', 'reserve_in_usd': '50000',
                                        'volume_usd': {'h24': '90000'}, 'price_change_percentage': {'h24': '12.5'}, 'transactions': {'h24': {'buys': 10, 'sells': 4}},
                                        'pool_created_at': '2026-09-01T00:00:00Z'},
                         'relationships': {'base_token': {'data': {'id': 'cro_0xbase'}}, 'quote_token': {'data': {'id': 'cro_0xwcro'}}, 'dex': {'data': {'id': 'vvs'}}}},
                        {'attributes': {'address': '0xorphan'}, 'relationships': {}}],
               'included': [{'id': 'cro_0xbase', 'attributes': {'address': '0xbase', 'symbol': 'MOON', 'name': 'Moon', 'image_url': 'missing.png'}},
                            {'id': 'cro_0xwcro', 'attributes': {'address': '0xwcro', 'symbol': 'WCRO', 'name': 'Wrapped CRO'}}]}
    out = gecko_network_pairs(payload, 'cronos')
    assert len(out) == 1
    p = out[0]
    assert p['chainId'] == 'cronos' and p['dexId'] == 'vvs' and p['baseToken']['symbol'] == 'MOON' and p['quoteToken']['symbol'] == 'WCRO'
    assert p['liquidity']['usd'] == 50000 and p['priceChange']['h24'] == 12.5 and p['url'].startswith('https://dexscreener.com/cronos/')
    assert p['info']['imageUrl'] is None  # GeckoTerminal's "missing.png" placeholder is dropped
