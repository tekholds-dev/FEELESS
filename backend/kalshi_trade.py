"""⏱ KALSHI TRADES FROM YOUR WALLET — DFlow's tokenized Kalshi markets (CFTC-regulated, US-legal), pure + tested (`tests/test_kalshi_trade.py`).

The flow (FEELESS never holds money, a key or identity data):
  1. 🪪 Proof — DFlow's free KYC (Stripe Identity) links the person to the wallet once. FEELESS only asks the public
     `GET proof.dflow.net/verify/{wallet}` → {verified}; the wallet signs "Proof KYC verification: {ms}" for the deep link.
  2. 🎟 the ticket — coin + UP / DOWN + $ (MIN_USD … MAX_USD). The server re-reads the live 15-minute market, maps it to its YES / NO outcome
     mint (DFlow's metadata API, production key), and asks DFlow's Trade API `/order` for USDC → that mint.
  3. 🛡 the check — the order must be exactly the ticket (input USDC, output = the side's mint, in-amount = the $), and the transaction:
     the user pays and is the ONLY signer, only ALLOW programs run (DFlow's prediction program or its router must be in it), nothing approves
     a spender, changes an owner, closes a wallet's SOL away or touches a nonce. Its fingerprint (message minus blockhash) is remembered 10 min.
  4. ✍ the wallet signs → /send broadcasts only a fingerprint FEELESS quoted, ONCE → /status follows DFlow's async fill.
  5. 🏁 redeem — after settlement the winning side's tokens → USDC through the same /order (market determined / finalized, redemption open).
Read on-chain 2026-10-23: every DFlow prediction order is signed by the user alone and calls ComputeBudget + `pReDicT…` (+ DFlow's router
`DF1ow4…` and Associated Token on a redeem / close).
"""
import base64
import hashlib
import struct
import time

from fnum import nan_safe as _f

META = 'https://prediction-markets-api.dflow.net/api/v1'   # production (key); the dev host in old guides is gone
TRADE = 'https://quote-api.dflow.net'                     # production (key)
PROOF = 'https://proof.dflow.net/verify'                  # public, no key
PROOF_LINK = 'https://dflow.net/proof'
USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
PRED = 'pReDicTmksnPfkfiz33ndSdbe2dY43KYPg4U2dbvHvb'      # DFlow's prediction-market (Kalshi CLP) program — executable on mainnet
ROUTER = 'DF1ow4tspfHX9JwWJsAb9epbkA8hmpSEAtxXy1V27QBH'    # DFlow's router
SYSTEM, TOKEN = '11111111111111111111111111111111', 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
TOKEN22 = 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'
ALLOW = {PRED: 'DFlow prediction markets', ROUTER: 'DFlow router', SYSTEM: 'System', TOKEN: 'Token', TOKEN22: 'Token-2022',
         'ComputeBudget111111111111111111111111111111': 'Compute budget', 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 'Associated token account',
         'Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo': 'Memo'}
SYS_REFUSE = {1: 'hands your wallet to a program', 4: 'touches a nonce', 5: 'touches a nonce', 6: 'touches a nonce', 7: 'touches a nonce', 10: 'hands your wallet to a program'}
TOKEN_REFUSE = {4: 'approves a spender', 6: 'changes an account owner', 13: 'approves a spender'}
MIN_USD, MAX_USD = 1, 500        # $1 — the owner's floor; $500 a ticket while it is new
SLIPPAGE_BPS = 300
MAX_TX_BYTES = 1232
QUOTE_TTL = 600
_quotes: dict = {}               # fingerprint → {'at', 'payer'}: orders FEELESS built (10 min, sent once)


def key(env):
    return str((env or {}).get('DFLOW_API_KEY') or '').strip()


def headers(env):
    k = key(env)
    return {'x-api-key': k} if k else {}


def side_mints(market, settle=USDC):
    """DFlow's market row → (yes mint, no mint) for this settlement stablecoin, or (None, None)."""
    acc = ((market or {}).get('accounts') or {}).get(settle) or {}
    return acc.get('yesMint'), acc.get('noMint')


def ticket(coin, side, usd):
    """The user's ticket → (ok, why). UP = YES ("up in the next 15 mins?" / "above the at-the-money strike at the close"), DOWN = NO."""
    import kalshi_odds as _ko
    if str(coin or '').upper() not in _ko.MARKETS:
        return False, 'Pick one of the listed markets.'
    if side not in ('up', 'down'):
        return False, 'UP or DOWN.'
    u = _f(usd)
    if not (MIN_USD <= u <= MAX_USD):
        return False, f'From ${MIN_USD} to ${MAX_USD} a ticket.'
    return True, None


def order_params(input_mint, output_mint, amount_base, user):
    return {'inputMint': input_mint, 'outputMint': output_mint, 'amount': str(int(amount_base)), 'userPublicKey': user,
            'slippageBps': str(SLIPPAGE_BPS), 'dynamicComputeUnitLimit': 'true', 'prioritizationFeeLamports': 'auto'}


def matches(order, input_mint, output_mint, amount_base):
    """DFlow's order must be exactly the ticket on screen: same mints, same in-amount, a transaction. → (ok, why)."""
    o = order or {}
    if o.get('inputMint') != input_mint or o.get('outputMint') != output_mint:
        return False, 'The order is for a different market or side than your ticket — refused.'
    if int(_f(o.get('inAmount'))) != int(amount_base):
        return False, 'The order spends a different amount than your ticket — refused.'
    if not o.get('transaction'):
        return False, 'DFlow returned no transaction.'
    return True, None


def fingerprint(msg):
    """The message minus its recent blockhash: the wallet may sign it with a fresh blockhash, nothing else may change."""
    raw = bytes(msg)
    return hashlib.sha256(raw.replace(bytes(msg.recent_blockhash), bytes(32), 1)).hexdigest()


def verify(b64, payer, signed=False):
    """A DFlow order transaction → (ok, why, fingerprint). Fail closed: anything unknown is refused. Pure."""
    from solders.transaction import VersionedTransaction
    try:
        raw = base64.b64decode(str(b64 or ''), validate=True)
        tx = VersionedTransaction.from_bytes(raw)
    except Exception:
        return False, 'Not a transaction.', None
    if len(raw) > MAX_TX_BYTES:
        return False, 'Not a transaction.', None
    msg = tx.message
    keys = [str(k) for k in msg.account_keys]
    if not keys or keys[0] != payer:
        return False, 'The fee payer is not your wallet.', None
    if msg.header.num_required_signatures != 1:
        return False, 'Someone besides you would sign it — refused.', None
    progs = set()
    for ix in msg.instructions:
        if ix.program_id_index >= len(keys):
            return False, 'It calls a program it does not list.', None
        prog, data = keys[ix.program_id_index], bytes(ix.data)
        acc = [keys[a] if a < len(keys) else None for a in ix.accounts]
        progs.add(prog)
        if prog == SYSTEM and len(data) >= 4:
            tag = struct.unpack('<I', data[:4])[0]
            if tag in SYS_REFUSE:
                return False, f'It {SYS_REFUSE[tag]} — refused.', None
            if tag == 2:
                return False, 'It sends SOL out of your wallet — refused.', None
        elif prog in (TOKEN, TOKEN22) and data:
            if data[0] in TOKEN_REFUSE:
                return False, f'It {TOKEN_REFUSE[data[0]]} — refused.', None
            if data[0] in (3, 12):
                return False, 'It moves tokens out of your wallet outside DFlow — refused.', None
            if data[0] == 9 and len(acc) > 1 and acc[1] != payer:
                return False, 'It closes an account into someone else\'s wallet — refused.', None
    bad = sorted(p for p in progs if p not in ALLOW)
    if bad:
        return False, f'It calls a program FEELESS does not know ({bad[0][:6]}…) — refused.', None
    if not progs & {PRED, ROUTER}:
        return False, 'It never goes through DFlow — refused.', None
    if signed and bytes(tx.signatures[0]) == bytes(64):
        return False, 'Your wallet did not sign it.', None
    return True, None, fingerprint(msg)


def remember(fp, payer, now=None):
    now = now or time.time()
    for k in [k for k, v in _quotes.items() if now - v['at'] > QUOTE_TTL]:
        _quotes.pop(k, None)
    if len(_quotes) > 2000:
        _quotes.clear()
    _quotes[fp] = {'at': now, 'payer': payer}


def take(fp, payer, now=None):
    """A built, unexpired fingerprint for this payer → True once (no resubmits)."""
    hit = _quotes.get(fp)
    if not hit or hit['payer'] != payer or (now or time.time()) - hit['at'] > QUOTE_TTL:
        return False
    _quotes.pop(fp, None)
    return True


def redeemable(market, mint, settle=USDC):
    """May these outcome tokens be cashed now? → (ok, why). Settled, redemption open, and the token is the winning side (scalar: both)."""
    m = market or {}
    if m.get('status') not in ('determined', 'finalized'):
        return False, 'The market has not settled yet.'
    acc = ((m.get('accounts') or {}).get(settle) or {})
    if acc.get('redemptionStatus') != 'open':
        return False, 'Redemption is not open yet.'
    if m.get('scalarOutcomePercent') is not None:
        return (True, None) if mint in (acc.get('yesMint'), acc.get('noMint')) else (False, 'Not this market\'s token.')
    win = acc.get('yesMint') if m.get('result') == 'yes' else acc.get('noMint') if m.get('result') == 'no' else None
    return (True, None) if win and mint == win else (False, 'That side lost — nothing to redeem.')


def position(market, mint, raw, decimals=6, settle=USDC):
    """One outcome-token balance → a dash row: side, contracts, the market, settled / won / redeemable."""
    m = market or {}
    yes, no = side_mints(m, settle)
    side = 'UP' if mint == yes else 'DOWN' if mint == no else None
    if not side:
        return None
    ok, _ = redeemable(m, mint, settle)
    won = None if m.get('status') not in ('determined', 'finalized') else ((m.get('result') == 'yes') == (side == 'UP'))
    return {'mint': mint, 'side': side, 'contracts': round(int(raw) / 10 ** int(decimals), 2), 'raw': int(raw), 'ticker': m.get('ticker'), 'title': m.get('title'),
            'status': m.get('status'), 'closes': m.get('closeTime'), 'won': won, 'redeemable': ok}
