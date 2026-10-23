"""⚡ REAL LEVERAGE — Jupiter Lend Borrow, in FEELESS (owner, 2026-10-23: "too many damn steps to do perps with coinbase — find another way").

Not a perp: a Jupiter Lend loan the user opens from their OWN wallet — lock a coin, borrow USDC against it, buy more of the coin with the
USDC. Same shape as a long perp (1.3–1.7× exposure, a liquidation price on screen), borrow interest instead of funding, no account, no KYC,
no venue hand-off. FEELESS never holds the collateral, the loan or a key (docs/DECISIONS.md #7).

Jupiter's Borrow API builds the UNSIGNED transaction (POST /lend/v1/borrow/operate {signer, vaultId, positionId (0 = new), colAmount,
debtAmount in base units} → {nftId, transaction}); `lend_earn.verify` opens it and refuses it unless the user pays + signs alone and only
Jupiter Lend's vaults program + Solana's own programs run. Simulated on mainnet 2026-10-23 for a wallet with plain SOL and no USDC account
(the vault program wraps SOL and opens the accounts itself). Close = repay ALL + withdraw ALL (the i128 minimum is Jupiter's "max" sentinel).
Guards: only the vaults below (a coin against USDC), leverage capped 10 points under the vault's max loan-to-value, a minimum and a
maximum size. Pure: no network here.
"""
import lend_earn

BORROW = 'https://api.jup.ag/lend/v1/borrow'
BORROW_PUBLIC = 'https://lite-api.jup.ag/lend/v1/borrow'
VAULTS = 'jupr81YtYssSyPt8jbnGuiWon5f6x9TcDEFxYe3Bdzi'
ALLOW = {**lend_earn.ALLOW, VAULTS: 'Jupiter Lend · Vaults'}
USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
COINS = {'WSOL': 'SOL', 'cbBTC': 'BTC', 'JUP': 'JUP'}   # the vault's collateral symbol → the coin you go long
ORDER = ('SOL', 'BTC', 'JUP')
ALL = str(-(2 ** 127))   # repay all / withdraw all
SAFETY = 0.10            # never open within 10 points of the vault's max loan-to-value
MAX_USD = 2000           # one open, at most (raise in code with the owner)


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def markets(vaults):
    """Jupiter's /borrow/vaults → one row per coin (the deepest USDC vault), SOL · BTC · JUP. Rates come as hundredths of a percent
    (831 = 8.31 %), loan-to-value and liquidation as tenths (800 = 80 %)."""
    best = {}
    for v in vaults if isinstance(vaults, list) else []:
        try:
            s, b = v['supplyToken'], v['borrowToken']
            coin = COINS.get(s.get('symbol'))
            if not coin or b.get('address') != USDC:
                continue
            cf, lt, price = _f(v['collateralFactor']) / 1000, _f(v['liquidationThreshold']) / 1000, _f(s.get('price'))
            bdec = int(b.get('decimals') or 6)
            row = {'vaultId': int(v['id']), 'coin': coin, 'mint': s['address'], 'dec': int(s.get('decimals') or 9), 'price': price,
                   'cf': cf, 'lt': lt, 'penalty': _f(v.get('liquidationPenalty')) / 100, 'borrowApr': round(_f(v.get('borrowRate')) / 100, 2),
                   'borrowableUsd': round(_f(v.get('borrowable')) / 10 ** bdec * _f(b.get('price'), 1.0)),
                   'minDebt': round(_f(v.get('minimumBorrowing')) / 10 ** bdec, 2), 'maxLev': round(1 + cf - SAFETY, 2)}
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0 or not 0 < cf < lt < 1 or row['maxLev'] <= 1.05:
            continue
        if coin not in best or row['borrowableUsd'] > best[coin]['borrowableUsd']:
            best[coin] = row
    return [best[c] for c in ORDER if c in best]


def plan(m, col, lev):
    """What one open does: lock `col` coins, borrow (lev − 1) × their value in USDC, buy the coin with it. → dict or raises ValueError."""
    col, lev = _f(col), round(_f(lev), 2)
    if col <= 0:
        raise ValueError('Type an amount above zero.')
    if not 1.05 <= lev <= m['maxLev']:
        raise ValueError(f"Leverage runs 1.05× to {m['maxLev']}× on {m['coin']}.")
    usd = col * m['price']
    if usd > MAX_USD:
        raise ValueError(f'One open is capped at ${MAX_USD:,} for now.')
    debt = round(usd * (lev - 1), 6)
    if debt < m['minDebt']:
        raise ValueError(f"Jupiter lends at least ${m['minDebt']:.2f} — size up to about ${m['minDebt'] / (lev - 1) * 1.02:.2f}.")
    if debt > m['borrowableUsd']:
        raise ValueError('The vault cannot lend that much right now.')
    liq = debt / (col * m['lt'])
    return {'coin': m['coin'], 'col': col, 'lev': lev, 'usd': round(usd, 2), 'debt': round(debt, 2), 'exposure': round(col + debt / m['price'], 9),
            'liq': liq, 'toLiqPct': round((1 - liq / m['price']) * 100, 1), 'dayCost': round(debt * m['borrowApr'] / 100 / 365, 4),
            'colUnits': lend_earn.base_units(f'{col:.9f}', m['dec']), 'debtUnits': lend_earn.base_units(f'{debt:.6f}', 6)}


def clean_request(raw):
    """→ (act, signer, vaultId, positionId, col, lev) or raises ValueError with words the panel shows."""
    raw = raw if isinstance(raw, dict) else {}
    act, signer = str(raw.get('act') or 'open'), str(raw.get('address') or '').strip()
    if act not in ('open', 'close'):
        raise ValueError('Open or close.')
    if not 32 <= len(signer) <= 44:
        raise ValueError('Connect your wallet first.')
    try:
        vid, pid = int(raw.get('vaultId')), int(raw.get('nftId') or 0)
    except (TypeError, ValueError):
        raise ValueError('Pick a market.')
    if act == 'close' and pid <= 0:
        raise ValueError('Pick the position to close.')
    return act, signer, vid, pid, raw.get('col'), raw.get('lev')


def body_for(act, signer, vid, pid, p=None):
    """The /borrow/operate request: a new position (positionId 0) or repay-all + withdraw-all on an existing one."""
    if act == 'close':
        return {'signer': signer, 'vaultId': vid, 'positionId': pid, 'colAmount': ALL, 'debtAmount': ALL}
    return {'signer': signer, 'vaultId': vid, 'positionId': 0, 'colAmount': p['colUnits'], 'debtAmount': p['debtUnits']}


def verify(b64, signer):
    return lend_earn.verify(b64, signer, allow=ALLOW, must=(VAULTS,))


def positions(raw, mk):
    """Jupiter's /borrow/positions?users= rows → [{vaultId, nftId, coin}] for our vaults (the amounts come from the user's own open record
    when Jupiter's row does not carry them in a shape we know). Unknown shapes are skipped, never guessed into money numbers."""
    out = []
    for p in raw if isinstance(raw, list) else []:
        if not isinstance(p, dict):
            continue
        vault = p.get('vault') if isinstance(p.get('vault'), dict) else {}
        try:
            vid = int(p.get('vaultId') if p.get('vaultId') is not None else vault.get('id'))
            nft = int(next(p[k] for k in ('nftId', 'positionId', 'id') if p.get(k) is not None))
        except (StopIteration, TypeError, ValueError):
            continue
        m = mk.get(vid)
        if m:
            out.append({'vaultId': vid, 'nftId': nft, 'coin': m['coin']})
    return out
