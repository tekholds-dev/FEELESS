"""🧹 WALLET DUST CLEANUP (pure, tested). Reads every coin a wallet holds and says, per coin, what can be done with it:
  • swap   — worth ≥ SWAP_MIN_USD with a price: sell it for the chain's gas coin (SOL / CRO) through the normal swap path
  • burn   — Solana dust (unpriced or under SWAP_MIN_USD): burn the leftover and CLOSE the account → its rent (~0.002 SOL) comes back
  • close  — an EMPTY Solana coin account: close it → rent back
Non-custodial: FEELESS only builds the transaction; the WALLET OWNER signs it. A burned coin is gone — the screen says so."""
import base64

SWAP_MIN_USD = 0.50      # under this a swap costs more in fees + impact than it returns — burn + close (rent back) instead
CLOSE_BATCH = 8          # burn + close pairs per transaction (fits a legacy tx comfortably)
TOKEN_PROGRAMS = ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def classify(accounts, prices=None, meta=None, swap_min=SWAP_MIN_USD):
    """accounts = [{pubkey, program, mint, raw, decimals, ui, lamports}] → rows with {usd, rentSol, actions, best, symbol, logo}."""
    out = []
    for a in accounts or []:
        px = _f((prices or {}).get(a['mint']))
        usd = round(_f(a.get('ui')) * px, 6) if px > 0 else None
        raw = int(a.get('raw') or 0)
        m = (meta or {}).get(a['mint']) or {}
        if raw == 0:
            actions = ['close']
        elif usd is not None and usd >= swap_min:
            actions = ['swap', 'burn']
        else:
            actions = ['burn', 'swap'] if usd is not None and usd > 0 else ['burn']
        out.append({**a, 'usd': usd, 'price': px or None, 'rentSol': round(_f(a.get('lamports')) / 1e9, 6), 'actions': actions, 'best': actions[0],
                    'symbol': m.get('symbol') or a['mint'][:4] + '…', 'logo': m.get('icon') or m.get('logoURI') or '', 'name': m.get('name') or ''})
    return sorted(out, key=lambda r: (r['best'] != 'close', r['best'] != 'burn', -(r['usd'] or 0)))


def summary(rows):
    burnable = [r for r in rows if r['best'] in ('burn', 'close')]
    return {'coins': len(rows), 'dust': len(burnable), 'rentBackSol': round(sum(r['rentSol'] for r in burnable), 6),
            'dustUsd': round(sum(r['usd'] or 0 for r in burnable), 4), 'swapUsd': round(sum(r['usd'] or 0 for r in rows if r['best'] == 'swap'), 2)}


def burn_close_tx(owner, items, blockhash):
    """Unsigned legacy tx (base64) for ONE owner: Burn (8) the leftover of each non-empty account, then CloseAccount (9) → rent to the owner.
    items = [{pubkey, program, mint, raw}] — the caller re-read each from the chain and checked it belongs to `owner`."""
    from solders.pubkey import Pubkey
    from solders.instruction import Instruction, AccountMeta
    from solders.message import Message
    from solders.transaction import Transaction
    from solders.hash import Hash
    me = Pubkey.from_string(owner)
    ixs = []
    for a in items:
        acct, prog = Pubkey.from_string(a['pubkey']), Pubkey.from_string(a['program'])
        if int(a.get('raw') or 0) > 0:
            ixs.append(Instruction(prog, bytes([8]) + int(a['raw']).to_bytes(8, 'little'),
                                   [AccountMeta(acct, False, True), AccountMeta(Pubkey.from_string(a['mint']), False, True), AccountMeta(me, True, False)]))
        ixs.append(Instruction(prog, bytes([9]), [AccountMeta(acct, False, True), AccountMeta(me, False, True), AccountMeta(me, True, False)]))
    msg = Message.new_with_blockhash(ixs, me, Hash.from_string(blockhash))
    return base64.b64encode(bytes(Transaction.new_unsigned(msg))).decode()


def batches(items, n=CLOSE_BATCH):
    return [items[i:i + n] for i in range(0, len(items), n)]


# ---- EVM (Cronos): balanceOf for every listed token, one JSON-RPC batch ----
def balance_calls(owner, tokens):
    """JSON-RPC batch: eth_getBalance (native) + eth_call balanceOf(owner) per token."""
    o = owner.lower().replace('0x', '').rjust(64, '0')
    calls = [{'jsonrpc': '2.0', 'id': 0, 'method': 'eth_getBalance', 'params': [owner, 'latest']}]
    for i, t in enumerate(tokens, start=1):
        calls.append({'jsonrpc': '2.0', 'id': i, 'method': 'eth_call', 'params': [{'to': t['address'], 'data': '0x70a08231' + o}, 'latest']})
    return calls


def evm_rows(tokens, results, swap_min=SWAP_MIN_USD):
    """tokens = LI.FI token list (index-aligned with calls 1..n); results = {id: hex}. → held coins with $ value + action."""
    out = []
    for i, t in enumerate(tokens, start=1):
        h = results.get(i)
        try:
            raw = int(h, 16) if h and h != '0x' else 0
        except ValueError:
            raw = 0
        if raw <= 0:
            continue
        dec = int(t.get('decimals') or 18)
        ui = raw / 10 ** dec
        px = _f(t.get('priceUSD'))
        usd = round(ui * px, 6) if px > 0 else None
        out.append({'address': t['address'], 'symbol': t.get('symbol'), 'name': t.get('name'), 'logo': t.get('logoURI') or '', 'decimals': dec,
                    'raw': str(raw), 'ui': ui, 'usd': usd, 'price': px or None, 'best': 'swap' if (usd or 0) >= swap_min else 'dust',
                    'actions': ['swap']})
    return sorted(out, key=lambda r: -(r['usd'] or 0))
