import pytest
from nft_studio import (clean_collection, collection_json, item_json, recipients, crossmint_base, underdog_base,
                        crossmint_mint_body, underdog_nft_body, room_left)

IMG = '/api/reputation/uploads/' + 'a' * 32 + '.png'
A = 'Aaaa1111111111111111111111111111111111111111'


def good(**k):
    return clean_collection({'name': 'OG Cards', 'symbol': 'og-1', 'platform': 'metaplex', 'image': IMG, 'royaltyPct': 5, 'supply': 100, **k})


def test_clean_collection():
    c = good()
    assert c['symbol'] == 'OG1' and c['royaltyBps'] == 500 and c['supply'] == 100
    for bad in ({'platform': 'opensea'}, {'image': 'javascript:1'}, {'name': 'x'}):
        with pytest.raises(ValueError):
            good(**bad)


def test_metadata_is_absolute_and_numbered():
    c = good(cardKey='badge:og')
    assert collection_json(c, 'https://f.xyz')['image'] == 'https://f.xyz' + IMG
    j = item_json(c, 'https://f.xyz', 7)
    assert j['name'] == 'OG Cards #7' and {'trait_type': 'Edition', 'value': '7'} in j['attributes']


def test_recipients_and_platform_shapes():
    assert recipients(f'{A}, {A}\nnope 0xabc') == [A]
    assert crossmint_base('sk_staging_1').startswith('https://staging') and crossmint_base('sk_production_1') == 'https://www.crossmint.com'
    assert underdog_base('devnet').startswith('https://devnet') and 'mainnet' in underdog_base('')
    assert crossmint_mint_body(good(), 'https://f.xyz', A, 1)['recipient'] == f'solana:{A}'
    assert underdog_nft_body(good(), 'https://f.xyz', A, 2)['receiverAddress'] == A


def test_supply_cap():
    c = good(supply=3)
    c['drops'] = [{'ok': [1, 2]}]
    assert room_left(c) == 1
    assert room_left(good(supply=0)) == 200
