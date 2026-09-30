"""Trade fills read straight from the chain, and the position math built on them.

Pure functions (no I/O): the trading service fetches transactions, these turn them into exact fills.
  fill_from_tx  — one parsed Solana transaction → a buy/sell of `mint` by `wallet`, with the real amounts that moved
                  (network fee and any FEELESS fee included; refundable token-account rent excluded)
  position      — fills → average entry, size, realized/unrealized-ready numbers, fees paid
"""
SOL_MINT = 'So11111111111111111111111111111111111111112'
STABLES = {'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'}
ATA_RENT_SOL = 0.00203928


def _key(k):
    return k.get('pubkey') if isinstance(k, dict) else k


def _tok(balances, wallet, mint):
    """Sum of `mint` held by `wallet` in a pre/post token balance list, and whether any account existed."""
    total, seen = 0.0, False
    for b in balances or []:
        if b.get('owner') == wallet and b.get('mint') == mint:
            ui = b.get('uiTokenAmount') or {}
            try:
                total += int(ui.get('amount') or 0) / 10 ** int(ui.get('decimals') or 0)
            except (TypeError, ValueError):
                total += float(ui.get('uiAmount') or 0)
            seen = True
    return total, seen


def fill_from_tx(tx: dict, wallet: str, mint: str, sol_usd: float) -> dict | None:
    if not tx or not (tx.get('meta') or {}) or (tx['meta'].get('err') is not None):
        return None
    meta, msg = tx['meta'], ((tx.get('transaction') or {}).get('message') or {})
    keys = [_key(k) for k in msg.get('accountKeys') or []]
    keys += (meta.get('loadedAddresses') or {}).get('writable') or []
    pre_t, post_t = meta.get('preTokenBalances'), meta.get('postTokenBalances')
    (a, had), (b, has) = _tok(pre_t, wallet, mint), _tok(post_t, wallet, mint)
    coin = b - a
    if abs(coin) <= 0:
        return None
    sol = 0.0
    if wallet in keys:
        i = keys.index(wallet)
        try:
            sol = (meta['postBalances'][i] - meta['preBalances'][i]) / 1e9
        except (KeyError, IndexError, TypeError):
            sol = 0.0
    sol += _tok(post_t, wallet, SOL_MINT)[0] - _tok(pre_t, wallet, SOL_MINT)[0]
    # Opening the coin's token account parks refundable rent; closing it hands it back. Neither is a trade cost.
    if has and not had:
        sol += ATA_RENT_SOL
    elif had and not has:
        sol -= ATA_RENT_SOL
    stable = sum(_tok(post_t, wallet, m)[0] - _tok(pre_t, wallet, m)[0] for m in STABLES)
    if coin > 0 and (sol < 0 or stable < 0):
        side = 'buy'
    elif coin < 0 and (sol > 0 or stable > 0):
        side = 'sell'
    else:
        return None   # a transfer or airdrop, not a trade
    usd = abs(sol) * sol_usd + abs(stable)
    if usd <= 0:
        return None
    sig = ((tx.get('transaction') or {}).get('signatures') or [''])[0]
    return {'ts': tx.get('blockTime') or 0, 'side': side, 'usd': round(usd, 4), 'price': usd / abs(coin), 'tokens': abs(coin),
            'sol': round(abs(sol), 9), 'networkSol': (meta.get('fee') or 0) / 1e9, 'token': mint, 'tx': sig, 'via': 'chain',
            'signer': wallet, 'balanceAfter': b}


def merge(*sources):
    """First source wins per signature (chain fills are exact, so they go first)."""
    out, seen = [], set()
    for rows in sources:
        for r in rows or []:
            tx = r.get('tx')
            if not tx or tx in seen or not (r.get('price') or 0) > 0:
                continue
            seen.add(tx)
            out.append(r)
    return sorted(out, key=lambda r: r.get('ts') or 0)


def position(rows: list, held_chain: float | None = None, fees_by_sig: dict | None = None) -> dict | None:
    """Average-cost position. `held_chain` (the wallet's real balance) beats the sum of fills when known."""
    fees_by_sig = fees_by_sig or {}
    buys = [r for r in rows if r['side'] == 'buy']
    if not buys:
        return None
    buy_usd = sum(r['usd'] for r in buys); buy_tok = sum(r.get('tokens') or r['usd'] / r['price'] for r in buys)
    sells = [r for r in rows if r['side'] == 'sell']
    sell_usd = sum(r['usd'] for r in sells); sell_tok = sum(r.get('tokens') or r['usd'] / r['price'] for r in sells)
    avg = buy_usd / buy_tok
    held = max(0.0, buy_tok - sell_tok) if held_chain is None else max(0.0, held_chain)
    fees = sum(fees_by_sig.get(r['tx'], 0) for r in rows)
    trades = []
    for r in rows[-30:]:
        t = {k: r.get(k) for k in ('ts', 'side', 'usd', 'price', 'tx', 'tokens', 'via', 'networkSol')}
        t['feeUsd'] = fees_by_sig.get(r['tx'])
        if r['side'] == 'sell':
            t['pnlUsd'] = round(r['usd'] - (r.get('tokens') or r['usd'] / r['price']) * avg, 2)
        trades.append(t)
    return {'avgEntry': avg, 'tokensHeld': held, 'costUsd': round(avg * held, 2), 'realizedUsd': round(sell_usd - sell_tok * avg, 2),
            'investedUsd': round(buy_usd, 2), 'feesUsd': round(fees, 4), 'exact': any(r.get('via') == 'chain' for r in rows),
            'buys': len(buys), 'sells': len(sells), 'lastTradeAt': max(r['ts'] for r in rows), 'trades': trades}
