"""NFT studio: FEELESS cards → NFT collections on three platforms, and drops to wallets.

Pure functions only (validation, metadata, platform request shapes, results). The service does the HTTP.
  metaplex  — Metaplex Core, created and minted on-chain by the owner's wallet (the browser signs; no API key)
  crossmint — Crossmint minting API (CROSSMINT_API_KEY; sk_staging… keys hit staging)
  underdog  — Underdog Protocol API, compressed NFTs (UNDERDOG_API_KEY; UNDERDOG_ENV=devnet for devnet)
Magic Eden and Tensor index Metaplex Core collections on their own once items exist.
"""
import re

PLATFORMS = ('metaplex', 'crossmint', 'underdog')
_B58 = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')
MAX_DROP = 200


def clean_collection(p: dict) -> dict:
    name = str(p.get('name') or '').strip()[:32]
    symbol = re.sub(r'[^A-Z0-9]', '', str(p.get('symbol') or '').upper())[:10]
    if len(name) < 2 or not symbol:
        raise ValueError('A name (2+ characters) and a symbol are required.')
    if p.get('platform') not in PLATFORMS:
        raise ValueError('Pick Metaplex, Crossmint or Underdog.')
    image = str(p.get('image') or '')
    if not re.match(r'^/api/reputation/uploads/[a-f0-9]{32}\.(png|jpg|webp|gif)$', image) and not image.startswith('https://'):
        raise ValueError('The collection needs its card image.')
    royalty = max(0, min(1000, int(float(p.get('royaltyPct') or 0) * 100)))
    supply = max(0, min(100000, int(p.get('supply') or 0)))
    return {'name': name, 'symbol': symbol, 'description': str(p.get('description') or '').strip()[:500], 'image': image[:300],
            'platform': p['platform'], 'royaltyBps': royalty, 'supply': supply, 'cardKey': str(p.get('cardKey') or '')[:60]}


def abs_url(site: str, u: str) -> str:
    return site + u if u.startswith('/api/') else u


def _mime(u: str) -> str:
    ext = u.rsplit('.', 1)[-1].lower()
    return {'jpg': 'image/jpeg', 'webp': 'image/webp', 'gif': 'image/gif'}.get(ext, 'image/png')


def collection_json(c: dict, site: str) -> dict:
    img = abs_url(site, c['image'])
    return {'name': c['name'], 'symbol': c['symbol'], 'description': c['description'], 'image': img, 'external_url': site,
            'seller_fee_basis_points': c['royaltyBps'], 'properties': {'files': [{'uri': img, 'type': _mime(img)}], 'category': 'image'}}


def item_json(c: dict, site: str, n: int) -> dict:
    j = collection_json(c, site)
    return {**j, 'name': f"{c['name']} #{n}", 'attributes': [{'trait_type': 'Card', 'value': c.get('cardKey') or c['name']}, {'trait_type': 'Edition', 'value': str(n)}]}


def recipients(raw) -> list:
    """Wallet list from text or a list: Solana addresses only, deduplicated, capped."""
    items = raw if isinstance(raw, list) else re.split(r'[\s,;]+', str(raw or ''))
    out = []
    for a in items:
        a = str(a).strip()
        if _B58.match(a) and a not in out:
            out.append(a)
    return out[:MAX_DROP]


def crossmint_base(key: str) -> str:
    return 'https://staging.crossmint.com' if key.startswith(('sk_staging', 'sk_test')) else 'https://www.crossmint.com'


def underdog_base(env: str) -> str:
    return 'https://devnet.underdogprotocol.com' if (env or '').lower() == 'devnet' else 'https://mainnet.underdogprotocol.com'


def crossmint_collection_body(c: dict, site: str) -> dict:
    return {'chain': 'solana', 'metadata': {'name': c['name'], 'imageUrl': abs_url(site, c['image']), 'description': c['description'] or c['name'], 'symbol': c['symbol']},
            'fungibility': 'non-fungible', **({'supplyLimit': c['supply']} if c['supply'] else {})}


def crossmint_mint_body(c: dict, site: str, to: str, n: int) -> dict:
    j = item_json(c, site, n)
    return {'recipient': f'solana:{to}', 'metadata': {'name': j['name'], 'image': j['image'], 'description': j['description'] or c['name'], 'attributes': j['attributes']}}


def underdog_project_body(c: dict, site: str) -> dict:
    return {'name': c['name'], 'symbol': c['symbol'], 'description': c['description'], 'image': abs_url(site, c['image']), 'semifungible': False, 'isPublic': True}


def underdog_nft_body(c: dict, site: str, to: str, n: int) -> dict:
    j = item_json(c, site, n)
    return {'name': j['name'], 'image': j['image'], 'description': j['description'], 'receiverAddress': to,
            'attributes': {a['trait_type']: a['value'] for a in j['attributes']}}


def room_left(c: dict) -> int:
    """How many more can be minted under the supply cap (0 cap = unlimited)."""
    minted = sum(len(d.get('ok') or []) for d in c.get('drops') or [])
    return max(0, c['supply'] - minted) if c.get('supply') else MAX_DROP
