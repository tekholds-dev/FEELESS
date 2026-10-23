"""🏙 THE FAMILY BLOCK = REAL MARKETS (owner, 2026-10-22: "my family block supposed to look like the new city design and expanding — me adding
buildings for markets i wanna use, they show under construction until i actually buy whatever it is, not these fake buildings … real errands like
tighten pool, something vital and real money fun").

The Don / Underboss (or the creator) ADD market buildings to the family block — any of the city's live markets (Raydium, Orca, Meteora, Kamino,
Jito, JLP …). The block grows with every building. A building stays UNDER CONSTRUCTION until a family wallet REALLY holds a position there —
proved on-chain or by the protocol's own API, never typed in:
  · receipt tokens  JitoSOL · JupSOL · mSOL · INF · JLP     → a token balance > 0 (Helius RPC)
  · position NFTs   Orca Whirlpools · Raydium CLMM          → a position NFT of that program in the wallet (Helius DAS)
  · Kamino vaults   /kvaults/users/{wallet}/positions       → a share balance > 0
  · anything else   no reader wired yet → stays under construction and says so (never faked as built)
ERRANDS are what the real position needs next — build it (deposit there) · a better-paying LST · check the range of a concentrated position —
each opens the real tool; the wallet signs. Other families see a building's state and a value band, never an exact balance.
Pure + tested; the service does the reads (one cached read per family per minute).
"""

MAX = 16
LST = {'jito': ('J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn', 'JitoSOL', 'JITOSOL'), 'jupsol': ('jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v', 'JupSOL', 'JUPSOL'),
       'marinade': ('mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So', 'mSOL', 'MSOL'), 'sanctum': ('5oVNBeEEQvYi1cX3ir8Dx5n1P7pdxydbGF2X4TxVusJm', 'INF', 'INF')}
MINTS = {**{k: v[0] for k, v in LST.items()}, 'jlp': '27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4'}
SYMS = {**{k: v[1] for k, v in LST.items()}, 'jlp': 'JLP'}
NFT = {'orca': ('whirlpool position', 'OWP'), 'raydium': ('raydium concentrated liquidity', 'RCL')}   # (name contains, symbol)
API = {'kamino': 'kamino'}
WHY_NONE = {'meteora': 'Meteora DLMM positions are program accounts — their reader is not wired yet',
            'phoenix': 'Phoenix seats / open orders reader not wired yet', 'marginfi': 'marginfi account reader not wired yet',
            'save': 'Save (Solend) obligation reader not wired yet', 'pumpswap': 'PumpSwap LP-token reader not wired yet'}
SWITCH_PP = 0.4   # an LST paying ≥ 0.4 pp more APY gets a switch errand


def proof_of(key):
    """How a market's position is proved: ('mint', mint) · ('nft', (name, symbol)) · ('api', name) · (None, why)."""
    if key in MINTS:
        return 'mint', MINTS[key]
    if key in NFT:
        return 'nft', NFT[key]
    if key in API:
        return 'api', API[key]
    return None, WHY_NONE.get(key, 'no position reader for this market yet')


def lots_of(c):
    return [x for x in ((c or {}).get('block') or []) if isinstance(x, dict) and x.get('key')]


def _may(me, c, staff, rank):
    return staff or me == (c or {}).get('owner') or (rank or {}).get(me) == 'underboss'


def add(c, key, me, now, staff=False, rank=None, known=()):
    """The Don / Underboss / creator adds a market building. Raises ValueError with words for the owner."""
    if not _may(me, c, staff, rank):
        raise ValueError('Only the Don or the Underboss adds buildings.')
    key = str(key or '').strip().lower()
    if known and key not in known:
        raise ValueError('That market is not in the city.')
    lots = lots_of(c)
    if any(x['key'] == key for x in lots):
        raise ValueError('That market already stands on the block.')
    if len(lots) >= MAX:
        raise ValueError(f'The block holds {MAX} buildings — remove one first.')
    c['block'] = lots + [{'key': key, 'at': round(now), 'by': me}]
    return c['block']


def remove(c, key, me, staff=False, rank=None):
    if not _may(me, c, staff, rank):
        raise ValueError('Only the Don or the Underboss removes buildings.')
    lots = lots_of(c)
    if not any(x['key'] == key for x in lots):
        raise ValueError('No such building on the block.')
    c['block'] = [x for x in lots if x['key'] != key]
    return c['block']


def needs(lots):
    """What the service must read for these buildings: {'mints': set, 'nft': bool, 'kamino': bool}."""
    ks = {x['key'] for x in lots}
    return {'mints': {MINTS[k] for k in ks if k in MINTS}, 'nft': any(k in NFT for k in ks), 'kamino': 'kamino' in ks}


def nft_count(assets, key):
    """Position NFTs of a market among DAS assets [{name, symbol}] (name match or exact symbol)."""
    name, sym = NFT[key]
    return sum(1 for a in assets or [] if name in str(a.get('name') or '').lower() or str(a.get('symbol') or '').upper() == sym)


def band(usd):
    """What other families see instead of a balance."""
    u = float(usd or 0)
    return '' if u <= 0 else '$' if u < 100 else '$$' if u < 1000 else '$$$' if u < 10000 else '$$$$'


def lst_apys(pools):
    """Pool-hub rows → {market key: APY} for the liquid-staking tokens."""
    by = {v[2]: k for k, v in LST.items()}
    out = {}
    for r in pools or []:
        k = by.get(str(r.get('sym') or '').upper())
        if k and r.get('kind') == 'stake' and r.get('apy') is not None:
            out[k] = max(out.get(k, 0.0), float(r['apy']))
    return out


def errands(b, apys, url=None):
    """What a building needs next — real actions only, each with the tool that does it (the wallet signs there)."""
    k, out = b['key'], []
    if b['state'] == 'construction':
        out.append({'kind': 'build', 'icon': '🏗', 'text': f"Build it — open a position in {b['name']}", 'url': url, 'urgent': False})
        return out
    if b['state'] != 'built':
        return out
    if k in LST and apys.get(k) is not None:
        best = max(((kk, a) for kk, a in apys.items() if kk != k), key=lambda x: x[1], default=None)
        if best and best[1] - apys[k] >= SWITCH_PP:
            out.append({'kind': 'switch', 'icon': '⚖', 'text': f"{SYMS[best[0]]} pays {best[1]:.2f}% vs your {SYMS[k]} {apys[k]:.2f}% — switch?",
                        'swap': {'from': MINTS[k], 'to': MINTS[best[0]]}, 'urgent': False, 'gain': round(best[1] - apys[k], 2)})
    if k in NFT:
        out.append({'kind': 'range', 'icon': '🎯', 'text': f"Check your {b['name']} range — out of range earns nothing", 'tool': 'range', 'urgent': False})
    if k == 'jlp':
        out.append({'kind': 'hedge', 'icon': '⚖', 'text': 'JLP is the house: it loses when traders win — size it against your SOL', 'tool': 'perps', 'urgent': False})
    return out


def view(lots, markets, held, prices=None, apys=None, mine=False):
    """The block's buildings. `markets` = {key: market row} (familia-markets), `held` = {key: {'amount', 'usd', 'n'}} from the reads (missing =
    nothing held). Own family: amounts, $ value, errands. Everyone else: state + a value band."""
    out = []
    for i, x in enumerate(lots):
        k = x['key']; m = (markets or {}).get(k) or {}
        how, what = proof_of(k)
        h = (held or {}).get(k) or {}
        has = float(h.get('usd') or 0) > 0 or float(h.get('amount') or 0) > 0 or int(h.get('n') or 0) > 0
        state = 'built' if how is not None and has else 'construction'   # no reader → never shown as built
        b = {'key': k, 'i': i, 'name': m.get('name') or k.title(), 'kind': m.get('kind') or 'dex', 'tvl': m.get('tvl'), 'url': m.get('url'), 'offer': m.get('offer'),
             'state': state, 'proof': how or 'none', 'why': (what if how is None else ''), 'apy': (apys or {}).get(k), 'band': band(h.get('usd')), 'at': x.get('at')}
        if mine:
            b.update(amount=h.get('amount'), usd=h.get('usd'), n=h.get('n'), sym=SYMS.get(k))
            b['errands'] = errands(b, apys or {}, m.get('url'))
        out.append(b)
    return out
