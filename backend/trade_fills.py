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


def _instructions(tx: dict) -> list:
    msg = ((tx.get('transaction') or {}).get('message') or {})
    out = list(msg.get('instructions') or [])
    for inner in (tx.get('meta') or {}).get('innerInstructions') or []:
        out += inner.get('instructions') or []
    return out


def _feeless_fee(tx: dict, keys: list, wallet: str, fee_accounts) -> tuple:
    """(SOL, stable USD) the wallet sent to FEELESS in this tx. A known fee account always counts; with none known,
    a SOL transfer from the wallet into a wrapped-SOL account the wallet does not own is the FEELESS fee
    (the swap itself wraps SOL into the wallet's OWN account, and bonding curves are not token accounts)."""
    meta = tx.get('meta') or {}
    wsol_foreign = {keys[b['accountIndex']] for b in (meta.get('postTokenBalances') or []) + (meta.get('preTokenBalances') or [])
                    if b.get('mint') == SOL_MINT and b.get('owner') != wallet and b.get('accountIndex', -1) < len(keys)}
    fee_accounts = set(fee_accounts or ())
    sol = stable = 0.0
    for ix in _instructions(tx):
        p = ix.get('parsed') if isinstance(ix.get('parsed'), dict) else None
        if not p:
            continue
        info, kind = p.get('info') or {}, p.get('type')
        dest = info.get('destination')
        if ix.get('program') == 'system' and kind == 'transfer' and info.get('source') == wallet and (dest in fee_accounts or (not fee_accounts and dest in wsol_foreign)):
            sol += (info.get('lamports') or 0) / 1e9
        elif ix.get('program') in ('spl-token', 'spl-token-2022') and kind in ('transfer', 'transferChecked') and dest in fee_accounts:
            amt = (info.get('tokenAmount') or {}).get('uiAmount')
            if amt is None and info.get('mint') in STABLES:
                amt = int(info.get('amount') or 0) / 1e6
            stable += float(amt or 0) if info.get('mint', '') != SOL_MINT else 0.0
            if info.get('mint') == SOL_MINT:
                sol += float((info.get('tokenAmount') or {}).get('uiAmount') or 0)
    return sol, stable


def fill_from_tx(tx: dict, wallet: str, mint: str, sol_usd: float, fee_accounts=()) -> dict | None:
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
    # Read the account's real lamports (Token-2022 accounts rent more than classic ones); fall back to the classic rent.
    def rent(bals, lamports):
        for x in bals or []:
            if x.get('owner') == wallet and x.get('mint') == mint:
                try:
                    return lamports[x['accountIndex']] / 1e9
                except (KeyError, IndexError, TypeError):
                    break
        return ATA_RENT_SOL
    if has and not had:
        sol += rent(post_t, meta.get('postBalances'))
    elif had and not has:
        sol -= rent(pre_t, meta.get('preBalances'))
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
    network = (meta.get('fee') or 0) / 1e9 if keys and keys[0] == wallet else 0.0   # only the fee payer pays it
    fee_sol, fee_stable = _feeless_fee(tx, keys, wallet, fee_accounts)
    # What actually went into / came out of the pool: the wallet's cash move with FEELESS's cut and the network fee taken out.
    pool_sol = abs(sol) - network - fee_sol if side == 'buy' else abs(sol) + network + fee_sol
    pool_usd = max(0.0, pool_sol) * sol_usd + (abs(stable) - fee_stable if side == 'buy' else abs(stable) + fee_stable)
    return {'ts': tx.get('blockTime') or 0, 'side': side, 'usd': round(usd, 4), 'price': usd / abs(coin), 'tokens': abs(coin),
            'sol': round(abs(sol), 9), 'networkSol': network, 'token': mint, 'tx': sig, 'via': 'chain',
            'poolUsd': round(pool_usd, 6), 'fillPrice': pool_usd / abs(coin) if pool_usd > 0 else None,
            'feelessFeeUsd': round(fee_sol * sol_usd + fee_stable, 6), 'networkUsd': round(network * sol_usd, 6),
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


def trade_costs(r: dict, fees_by_sig: dict) -> float:
    """FEELESS fee + network fee (USD) baked into an on-chain fill's SOL amount."""
    if r.get('via') != 'chain':
        return 0.0
    if r.get('poolUsd') is not None:   # read straight from the tx: the exact gap between your money and the pool
        return abs(r['usd'] - r['poolUsd'])
    sol_px = r['usd'] / r['sol'] if r.get('sol') else 0.0
    return (fees_by_sig.get(r['tx']) or 0.0) + (r.get('networkSol') or 0.0) * sol_px


def market_usd(r: dict, fees_by_sig: dict) -> float:
    """What the coins themselves cost (buy) or fetched (sell) at the pool, fees taken out — the price you traded at."""
    if r.get('poolUsd') is not None:
        return r['poolUsd']
    c = trade_costs(r, fees_by_sig)
    return max(0.0, r['usd'] - c) if r['side'] == 'buy' else r['usd'] + c


def position(rows: list, held_chain: float | None = None, fees_by_sig: dict | None = None) -> dict | None:
    """Average-cost position on real money: avgEntry is the break-even price (fees included), so P&L against the live price
    is exactly what you're up or down. fillPrice is the pool price you got. `held_chain` beats the sum of fills."""
    fees_by_sig = fees_by_sig or {}
    buys = [r for r in rows if r['side'] == 'buy']
    if not buys:
        return None
    tok = lambda r: r.get('tokens') or r['usd'] / r['price']
    # Real money: what left / reached the wallet, fees included. P&L against this is what you're actually up or down.
    buy_usd = sum(r['usd'] for r in buys); buy_tok = sum(tok(r) for r in buys)
    sells = [r for r in rows if r['side'] == 'sell']
    sell_usd = sum(r['usd'] for r in sells); sell_tok = sum(tok(r) for r in sells)
    avg = buy_usd / buy_tok                                                   # break-even price, fees included
    fill = sum(market_usd(r, fees_by_sig) for r in buys) / buy_tok           # the pool price you actually got
    held = max(0.0, buy_tok - sell_tok) if held_chain is None else max(0.0, held_chain)
    fees = sum(trade_costs(r, fees_by_sig) if r.get('via') == 'chain' else fees_by_sig.get(r['tx'], 0) for r in rows)
    trades = []
    for r in rows[-30:]:
        t = {k: r.get(k) for k in ('ts', 'side', 'usd', 'price', 'tx', 'tokens', 'via', 'networkSol')}
        t['feeUsd'] = fees_by_sig.get(r['tx'])
        # Per trade: the pool price you got (fees out) and that trade's own break-even (every dollar in / coins).
        t['fillPrice'] = r['poolUsd'] / tok(r) if r.get('poolUsd') else market_usd(r, fees_by_sig) / tok(r)
        t['breakEven'] = r['usd'] / tok(r)
        if r['side'] == 'sell':
            t['pnlUsd'] = round(r['usd'] - tok(r) * avg, 2)   # what actually landed in the wallet vs the coins' entry cost
        trades.append(t)
    return {'avgEntry': avg, 'fillPrice': fill, 'tokensHeld': held, 'costUsd': round(avg * held, 2), 'realizedUsd': round(sell_usd - sell_tok * avg, 2),
            'entryIncludes': 'FEELESS + network fees (break-even)',
            'investedUsd': round(buy_usd, 2), 'feesUsd': round(fees, 4), 'exact': all(r.get('via') == 'chain' for r in rows),
            'coverage': round(min(1.0, max(0.0, buy_tok - sell_tok) / held), 3) if held > 0 else 1.0,
            'buys': len(buys), 'sells': len(sells), 'lastTradeAt': max(r['ts'] for r in rows), 'trades': trades}
