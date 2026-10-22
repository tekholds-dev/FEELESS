"""🏦 FEE CITY'S MARKETS (owner, 2026-10-21: "80 % of the Fee City buildings need to be markets — established and newly established DeFi,
pools, vaults, v2 / v3 … real-time vitals on these plots, pop-outs for what each offers … top coins show in the city"). Pure + tested; the
service fetches (DefiLlama TVL — one tiny call a market — + one DexScreener search for the live pools and coins) and caches 60s.

· MARKET ROW (east): the DEXes — each building's live number is its TVL, its top SOL pool (liquidity, 24h volume, 24h move).
· THE VAULT DISTRICT (west): lending, perps, liquid staking — TVL and its move since our last reading.
· NEW MONEY (south): today's top Solana coins by 24h volume, live price move, each a market stall.
Read-only. A DEX pool opens on FEELESS (our engine, the wallet signs); every other market links to its own app — FEELESS never takes custody.
"""
#          key          name                 kind       llama slug                     dexIds                  url                               offer
MARKETS = [('raydium',  'Raydium',           'dex',     'raydium',                     ('raydium',),           'https://raydium.io',             'AMM v4 + CLMM (v3-style concentrated) + CPMM pools; most Solana launches graduate here'),
           ('orca',     'Orca',              'dex',     'orca',                        ('orca',),              'https://www.orca.so',            'Whirlpools: concentrated liquidity (v3-style) with tight fees'),
           ('meteora',  'Meteora',           'dex',     'meteora-dlmm',                ('meteora',),           'https://www.meteora.ag',         'DLMM: dynamic liquidity bins + dynamic fees; DAMM pools and vaults'),
           ('pumpswap', 'PumpSwap',          'dex',     'pumpswap',                    ('pumpswap',),          'https://swap.pump.fun',          'Where Pump.fun coins graduate: constant-product pools, creator fees'),
           ('phoenix',  'Phoenix',           'dex',     'phoenix',                     ('phoenix',),           'https://www.phoenix.trade',      'On-chain order book: limit orders, no AMM curve'),
           ('jlp',      'Jupiter Perps',     'perps',   'jupiter-perpetual-exchange',  (),                     'https://jup.ag/perps',           'Perps up to 100×; JLP holders are the house and earn the fees'),
           ('kamino',   'Kamino',            'lend',    'kamino-lend',                 (),                     'https://app.kamino.finance',     'Lending + automated liquidity vaults (auto-rebalanced CLMM)'),
           ('marginfi', 'marginfi',          'lend',    'marginfi-lending',            (),                     'https://app.marginfi.com',       'Borrow / lend with points; isolated risk tiers'),
           ('save',     'Save',              'lend',    'save',                        (),                     'https://save.finance',           'The old Solend: money markets for SOL, USDC and LSTs'),
           ('jito',     'Jito',              'stake',   'jito-liquid-staking',         (),                     'https://www.jito.network',       'JitoSOL: staking + MEV rewards, liquid'),
           ('jupsol',   'Jupiter SOL',       'stake',   'jupiter-staked-sol',          (),                     'https://jup.ag',                 'JupSOL: liquid staking with zero fees from Jupiter'),
           ('sanctum',  'Sanctum',           'stake',   'sanctum-infinity',            (),                     'https://app.sanctum.so',         'Infinity: one pool for every LST, swap any LST instantly'),
           ('marinade', 'Marinade',          'stake',   'marinade-liquid-staking',     (),                     'https://marinade.finance',       'mSOL + native staking across hundreds of validators')]
DISTRICTS = {'dex': 'row', 'perps': 'vault', 'lend': 'vault', 'stake': 'vault'}
COINS_MAX = 12
LIQ_FLOOR = 50_000
SOL = 'So11111111111111111111111111111111111111112'


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def top_pool(pairs, dex_ids):
    """That DEX's busiest live pool (24h volume, ≥ LIQ_FLOOR liquidity) from one DexScreener search → {pair, base, liq, vol, ch} or None."""
    rows = [p for p in pairs or [] if p.get('chainId') == 'solana' and p.get('dexId') in dex_ids and _f((p.get('liquidity') or {}).get('usd')) >= LIQ_FLOOR]
    if not rows:
        return None
    p = max(rows, key=lambda r: _f((r.get('volume') or {}).get('h24')))   # the BUSIEST real pool — a deep pool nobody trades is a stale listing
    return {'pair': p.get('pairAddress'), 'base': (p.get('baseToken') or {}).get('symbol'), 'quote': (p.get('quoteToken') or {}).get('symbol'),
            'liq': round(_f((p.get('liquidity') or {}).get('usd'))), 'vol': round(_f((p.get('volume') or {}).get('h24'))),
            'ch': round(_f((p.get('priceChange') or {}).get('h24')), 2), 'labels': p.get('labels') or []}


def top_coins(pairs, n=COINS_MAX):
    """Today's top Solana coins by 24h volume across all their pools (one row a token, opened on its deepest pool), never SOL / stables."""
    best, vol = {}, {}
    for p in pairs or []:
        b = p.get('baseToken') or {}
        if p.get('chainId') != 'solana' or b.get('address') == SOL or str(b.get('symbol', '')).upper() in ('USDC', 'USDT', 'SOL', 'WSOL'):
            continue
        a = b.get('address'); vol[a] = vol.get(a, 0.0) + _f((p.get('volume') or {}).get('h24'))   # a coin's volume = every pool of it
        cur = best.get(a)
        if not cur or _f((p.get('liquidity') or {}).get('usd')) > _f((cur.get('liquidity') or {}).get('usd')):
            best[a] = p
    rows = sorted(best.values(), key=lambda p: -vol[(p.get('baseToken') or {}).get('address')])[:n]
    return [{'mint': (p.get('baseToken') or {}).get('address'), 'sym': (p.get('baseToken') or {}).get('symbol'), 'pair': p.get('pairAddress'), 'dex': p.get('dexId'),
             'px': _f(p.get('priceUsd')), 'mc': round(_f(p.get('marketCap') or p.get('fdv'))), 'vol': round(vol[(p.get('baseToken') or {}).get('address')]),
             'liq': round(_f((p.get('liquidity') or {}).get('usd'))), 'ch': round(_f((p.get('priceChange') or {}).get('h24')), 2),
             'ch1': round(_f((p.get('priceChange') or {}).get('h1')), 2)} for p in rows]


def build(tvl, prev, pairs, now):
    """→ {'markets': [...], 'coins': [...], 'at'}. tvl = {slug: usd}; prev = {slug: (usd, at)} (our last reading → the move)."""
    out = []
    for key, name, kind, slug, dex_ids, url, offer in MARKETS:
        t = tvl.get(slug)
        was = (prev or {}).get(slug)
        move = round((t / was[0] - 1) * 100, 2) if t and was and was[0] else None
        out.append({'key': key, 'name': name, 'kind': kind, 'district': DISTRICTS[kind], 'tvl': round(t) if t else None, 'move': move,
                    'pool': top_pool(pairs, dex_ids) if dex_ids else None, 'url': url, 'offer': offer})
    return {'markets': out, 'coins': top_coins(pairs), 'at': now}
