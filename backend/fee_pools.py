"""🏦 THE POOL HUB — every top and rising Solana pool / vault / staking / lending market in ONE list (owner, 2026-10-22: "a pools building of every
top and rising pool / v2, v3 / staking and rapid compounding in one popout, then we set our building … without running to each site").

Two sources, both read-only and cached by the service:
  · DefiLlama yields (one call, every Solana pool with TVL + APY + 7-day APY change): AMM v2 / CLMM v3 (Raydium, Orca), compounding vaults
    (Kamino liquidity), lending (Kamino, Jupiter Lend, Save, marginfi, Loopscale), liquid staking (Jito, Marinade, JupSOL, INF …), RWA / perps.
  · our own pair feed (DexScreener pairs we already pull): DEX pools WITH their on-chain address (Meteora DLMM, PumpSwap, Raydium CLMM / CPMM,
    Orca whirlpools) → the exact pool opens in our war room (our engine, the wallet signs) and its exact deposit page.
Pure: no network here. FEELESS never takes custody — a deposit happens on the protocol's own page, a trade goes through our engine.
"""
import re

SOL = 'So11111111111111111111111111111111111111112'
QUOTES = {SOL, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'}
KINDS = ('v2', 'v3', 'dlmm', 'vault', 'lend', 'stake', 'perps', 'rwa')
MIN_TVL = 150_000
ROWS_MAX = 160
# liquid staking: DefiLlama lists the DEPOSIT asset (SOL) — the token you hold is the LST, so trading in = staking
LST = {'jito-liquid-staking': 'J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn', 'marinade-liquid-staking': 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',
       'jupiter-staked-sol': 'jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v', 'sanctum-infinity': '5oVNBeEEQvYi1cX3ir8Dx5n1P7pdxydbGF2X4TxVusJm',
       'blazestake': 'bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1', 'drift-staked-sol': 'Dso1bDeDjCQxTrWHqUUi63oBvV7Mdm6WaobLbQ7gnPQ'}
APP = {'raydium-amm': 'https://raydium.io/liquidity-pools/', 'orca-dex': 'https://www.orca.so/pools', 'kamino-liquidity': 'https://app.kamino.finance/liquidity',
       'kamino-lend': 'https://app.kamino.finance/', 'jupiter-lend': 'https://jup.ag/lend/earn', 'save': 'https://save.finance/', 'project-0': 'https://app.marginfi.com/',
       'loopscale-lending': 'https://app.loopscale.com/', 'jito-liquid-staking': 'https://www.jito.network/staking/', 'marinade-liquid-staking': 'https://marinade.finance/',
       'jupiter-staked-sol': 'https://jup.ag/', 'sanctum-infinity': 'https://app.sanctum.so/infinity', 'gmx-solana': 'https://gmxsol.io/', 'drift-staked-sol': 'https://app.drift.trade/'}
NAME = {'raydium-amm': 'Raydium', 'orca-dex': 'Orca', 'kamino-liquidity': 'Kamino Vaults', 'kamino-lend': 'Kamino Lend', 'jupiter-lend': 'Jupiter Lend', 'save': 'Save',
        'project-0': 'marginfi', 'loopscale-lending': 'Loopscale', 'gmx-solana': 'GMX Solana', 'meteora': 'Meteora', 'pumpswap': 'PumpSwap', 'raydium': 'Raydium', 'orca': 'Orca'}


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def kind_of(project, meta=''):
    """A DefiLlama project (+ its poolMeta) → v2 · v3 · vault · lend · stake · perps · rwa (None = not a pool we show)."""
    p = str(project or '').lower(); m = str(meta or '').lower()
    if 'staked-sol' in p or 'liquid-staking' in p or p in ('sanctum-infinity', 'blazestake', 'jpool', 'phantom-sol', 'backpack-sol', 'hylo-lsts', 'save-sol'):
        return 'stake'
    if p == 'raydium-amm':
        return 'v3' if 'concentrated' in m or 'clmm' in m else 'v2'
    if p == 'orca-dex':
        return 'v3'
    if 'liquidity' in p or 'vault' in p or 'tranche' in p or 'curator' in p:
        return 'vault'
    if 'lend' in p or p in ('save', 'project-0', 'credix'):
        return 'lend'
    if p in ('gmx-solana', 'jupiter-perpetual-exchange', 'drift', 'neutral-trade'):
        return 'perps'
    if any(w in p for w in ('buidl', 'treasury', 'ondo', 'fund', 'securitize', 'onre', 'uscc')):
        return 'rwa'
    return None


def from_llama(rows):
    """DefiLlama /pools rows → hub rows (Solana, ≥ MIN_TVL, a kind we show)."""
    out = []
    for r in rows or []:
        if r.get('chain') != 'Solana' or _f(r.get('tvlUsd')) < MIN_TVL:
            continue
        k = kind_of(r.get('project'), r.get('poolMeta'))
        if not k or r.get('outlier'):
            continue
        if k in ('v2', 'v3') and _f(r.get('apy')) < 0.1 and _f(r.get('volumeUsd1d')) < 25_000:   # a parked pool (no fees, no trades) is not a market
            continue
        proj = r.get('project'); mints = [m for m in (r.get('underlyingTokens') or []) if isinstance(m, str)][:2]
        hold = LST.get(proj) if k == 'stake' else next((m for m in mints if m not in QUOTES), mints[0] if mints else None)
        out.append({'id': str(r.get('pool'))[:64], 'src': 'llama', 'kind': k, 'project': proj, 'proto': NAME.get(proj) or str(proj or '').replace('-', ' ').title(),
                    'sym': re.sub(r'\bWSOL\b', 'SOL', str(r.get('symbol') or '?'))[:24], 'meta': str(r.get('poolMeta') or '')[:40] or None, 'tvl': round(_f(r.get('tvlUsd'))),
                    'apy': round(_f(r.get('apy')), 2), 'base': round(_f(r.get('apyBase')), 2), 'reward': round(_f(r.get('apyReward')), 2),
                    'd7': round(_f(r.get('apyPct7D')), 2), 'vol': round(_f(r.get('volumeUsd1d'))), 'il': r.get('ilRisk') == 'yes', 'stable': bool(r.get('stablecoin')),
                    'mints': mints, 'hold': hold, 'pair': None, 'app': APP.get(proj) or f'https://defillama.com/yields/pool/{r.get("pool")}'})
    return out


DEX_KIND = {'meteora': 'dlmm', 'pumpswap': 'v2', 'orca': 'v3'}


def deposit_url(dex, pair, labels=()):
    """The EXACT pool's own deposit page (the wallet signs there)."""
    lab = ' '.join(labels or []).lower()
    if dex == 'meteora':
        return f'https://app.meteora.ag/{"dlmm" if "dlmm" in lab or not lab else "pools"}/{pair}'
    if dex == 'raydium':
        return f'https://raydium.io/liquidity/increase/?mode=add&pool_id={pair}'
    if dex == 'orca':
        return f'https://www.orca.so/pools/{pair}'
    if dex == 'pumpswap':
        return f'https://swap.pump.fun/?input={SOL}'
    return f'https://dexscreener.com/solana/{pair}'


def from_pairs(pairs):
    """Our DexScreener pair feed → hub rows for the DEX pools we can open EXACTLY (address known): Meteora DLMM, PumpSwap, Raydium, Orca."""
    out, seen = [], set()
    for p in pairs or []:
        dex = str(p.get('dexId') or '').lower(); addr = p.get('pairAddress')
        if p.get('chainId') != 'solana' or not addr or addr in seen or dex not in ('meteora', 'pumpswap', 'raydium', 'orca'):
            continue
        liq = _f((p.get('liquidity') or {}).get('usd'))
        if liq < 25_000:
            continue
        seen.add(addr); labels = [str(x) for x in (p.get('labels') or [])][:3]; lab = ' '.join(labels).lower()
        k = 'dlmm' if dex == 'meteora' and ('dlmm' in lab or not lab) else DEX_KIND.get(dex) or ('v3' if 'clmm' in lab else 'v2')
        b = p.get('baseToken') or {}; q = p.get('quoteToken') or {}
        out.append({'id': addr, 'src': 'pair', 'kind': k, 'project': dex, 'proto': NAME.get(dex, dex.title()), 'sym': f"{b.get('symbol', '?')}-{q.get('symbol', '?')}"[:24],
                    'meta': ' · '.join(labels) or None, 'tvl': round(liq), 'apy': None, 'base': None, 'reward': None, 'd7': None,
                    'vol': round(_f((p.get('volume') or {}).get('h24'))), 'ch': round(_f((p.get('priceChange') or {}).get('h24')), 2), 'il': True, 'stable': False,
                    'mints': [b.get('address'), q.get('address')], 'hold': b.get('address') if b.get('address') not in QUOTES else q.get('address'),
                    'pair': addr, 'app': deposit_url(dex, addr, labels)})
    return out


def rising(r):
    """How hard a pool is RISING: the APY's 7-day move for yield rows, 24h volume ÷ liquidity (turnover) for a DEX pool."""
    if r.get('d7') is not None and r.get('apy') is not None:
        return _f(r.get('d7'))
    return _f(r.get('vol')) / max(1.0, _f(r.get('tvl'))) * 10


def worth(r):
    """Which pools a city shows first: deep AND earning (√TVL × the yield or the turnover) — a $90M pool paying 0.01 % loses to a busy $5M one."""
    earn = _f(r.get('apy')) if r.get('apy') is not None else _f(r.get('vol')) / max(1.0, _f(r.get('tvl'))) * 100
    return (_f(r.get('tvl')) ** 0.5) * (1 + min(earn, 300) / 10)


def hub(llama_rows, pairs, now):
    """→ {'pools': [...top by TVL per kind + the risers...], 'cities': {harbor, heights, bay, docks}, 'kinds': {kind: n}, 'at'}."""
    rows = from_llama(llama_rows) + from_pairs(pairs)
    rows = [r for r in rows if not re.search(r'test|deprecated', r['sym'], re.I)]
    by = {k: sorted([r for r in rows if r['kind'] == k], key=lambda r: -r['tvl']) for k in KINDS}
    keep, ids = [], set()
    for k in KINDS:   # the top of every kind + its fastest risers, never one kind crowding out the rest
        top = by[k][:18]; rise = sorted([r for r in by[k] if r['tvl'] >= 250_000], key=lambda r: -rising(r))[:6]
        for r in top + rise:
            if r['id'] not in ids:
                ids.add(r['id']); keep.append({**r, 'rise': round(rising(r), 2)})
    keep = keep[:ROWS_MAX]
    pick = lambda pred, n: sorted([r for r in keep if pred(r)], key=lambda r: -worth(r))[:n]
    cities = {   # 🌉 each outer city's real-money district (owner, 5th list 1c)
        'harbor': pick(lambda r: r['kind'] == 'v2', 8),                                   # launch piers: constant-product pools (PumpSwap, Raydium AMM)
        'heights': pick(lambda r: r['kind'] == 'v3', 8),                                  # old money: concentrated liquidity (Raydium CLMM, Orca)
        'bay': pick(lambda r: r['kind'] in ('dlmm', 'stake'), 8),                         # the boardwalk: DLMM bins + liquid staking
        'docks': pick(lambda r: r['kind'] in ('vault', 'lend', 'perps', 'rwa'), 8),      # the laundromat: compounding vaults, lending, perps, RWA
    }
    return {'pools': keep, 'cities': cities, 'kinds': {k: len(by[k]) for k in KINDS}, 'at': now}


def link_row(r):
    """What a family building shows once it is SET to a pool (stored on the block — sym, kind, protocol, never a balance)."""
    return {'pool': r['id'], 'sym': r['sym'], 'kind': r['kind'], 'proto': r['proto']}
