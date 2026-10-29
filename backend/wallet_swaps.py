"""🔁 A wallet's swaps from plain Solana RPC (owner 2026-10-29, N07: "Fuse wallet's profile not showing trade swap history in Families or
Profile"). The profile / Families history read Helius's parsed-transactions API only; with Helius out of quota ("max usage reached") every
wallet's history read EMPTY. This is the fallback: `getSignaturesForAddress` → `getTransaction` (jsonParsed) → each transaction read from
the WALLET'S OWN balance changes. Pure, tested (tests/test_wallet_swaps.py).

A swap = exactly one non-quote coin moved for the wallet AND a priced quote leg moved the other way: SOL (native, fee added back when the
wallet paid it, + wrapped SOL) at the live SOL price, or a stablecoin 1:1. Token-for-token routes, plain transfers and failed transactions
are not swaps. → {ts, side, usd, price, token, tx} — the same row shape the Helius path returns."""

WSOL = 'So11111111111111111111111111111111111111112'
STABLES = {'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'}
DUST = 1e-9


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _keys(tx):
    ks = (((tx or {}).get('transaction') or {}).get('message') or {}).get('accountKeys') or []
    return [k.get('pubkey') if isinstance(k, dict) else k for k in ks]


def _tok(rows, address):
    out = {}
    for b in rows or []:
        if b.get('owner') == address and b.get('mint'):
            out[b['mint']] = out.get(b['mint'], 0.0) + _f((b.get('uiTokenAmount') or {}).get('uiAmount'))
    return out


def parse(tx, address, sol_usd):
    """One jsonParsed getTransaction result → a swap row for `address`, or None."""
    meta = (tx or {}).get('meta') or {}
    if not tx or meta.get('err') is not None:
        return None
    keys = _keys(tx)
    sol = 0.0
    if address in keys:
        i = keys.index(address)
        pre, post = meta.get('preBalances') or [], meta.get('postBalances') or []
        if i < len(pre) and i < len(post):
            sol = (_f(post[i]) - _f(pre[i]) + (_f(meta.get('fee')) if i == 0 else 0.0)) / 1e9   # the network fee is not the trade
    pre_t, post_t = _tok(meta.get('preTokenBalances'), address), _tok(meta.get('postTokenBalances'), address)
    delta = {m: post_t.get(m, 0.0) - pre_t.get(m, 0.0) for m in set(pre_t) | set(post_t)}
    sol += delta.pop(WSOL, 0.0)
    quote = sol * _f(sol_usd) + sum(delta.pop(m, 0.0) for m in list(delta) if m in STABLES)
    moved = [(m, a) for m, a in delta.items() if abs(a) > DUST]
    if len(moved) != 1 or abs(quote) < 0.01:
        return None
    mint, amt = moved[0]
    if (amt > 0) == (quote > 0):   # coin AND money both in (an airdrop + rent refund) or both out: not a swap
        return None
    usd = abs(quote)
    return {'ts': int(_f(tx.get('blockTime'))), 'side': 'buy' if amt > 0 else 'sell', 'usd': round(usd, 2), 'price': usd / abs(amt), 'token': mint,
            'tx': ((tx.get('transaction') or {}).get('signatures') or [None])[0], 'source': 'rpc'}
