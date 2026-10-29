"""💵 FUND A CAT — the payment split (owner 2026-10-29, DECISIONS #2: "wallets created per user payment — part of payment goes to feeless and
the other goes into the new agent wallet"; "one-time $2 comes out of minimal $10 per agent, up to 4 cats per user"). Pure, tested
(tests/test_cat_fund.py).

ONE transaction the user's wallet signs, two SOL transfers in it: the one-time FEELESS fee (FEE_USD, the cat's FIRST funding only) to the
FEELESS fee wallet, and the rest to the cat's own Crossmint wallet. The server builds it (`build`), keeps what it built for PLAN_SEC, and
only sends a signed copy whose message is byte-for-byte the one it built, signed by the cat's owner (`verify`) — the same rule as every
FEELESS swap. A top-up later is all for the cat (no fee). Amounts are SOL at the live price, rounded DOWN to the lamport for the cat."""
import base64

from solders.hash import Hash
from solders.message import MessageV0, to_bytes_versioned
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction

MIN_USD = 10.0          # the least a first funding may be
FEE_USD = 2.0           # FEELESS's one-time cut, out of the first funding
TOPUP_MIN_USD = 1.0     # a later top-up
MAX_USD = 5000.0
MAX_CATS = 4            # cats with their own wallet, per owner wallet
PLAN_SEC = 90.0         # a built transaction is good for this long (its blockhash lives ~60-90s)
LAMPORTS = 1_000_000_000


def plan(usd, sol_usd, first, fee_usd=FEE_USD, min_usd=MIN_USD):
    """$ amount + live SOL price + is this the cat's first funding (+ HQ's fee / minimum; a creator wallet: fee 0, min $1) →
    {usd, feeUsd, solUsd, totalLamports, feeLamports, catLamports, catUsd}."""
    usd, px = float(usd or 0), float(sol_usd or 0)
    if px <= 0:
        raise ValueError('No live SOL price right now — try again in a minute.')
    fee_usd = max(0.0, float(fee_usd or 0)) if first else 0.0
    lo = max(float(min_usd or 0), fee_usd + 1) if first else TOPUP_MIN_USD
    if usd < lo and first and usd <= fee_usd + 1e-9:
        raise ValueError(f'${usd:g} only covers the ${fee_usd:g} one-time fee — a first funding starts at ${lo:g} so its wallet gets money to trade.')
    if not lo <= usd <= MAX_USD:
        raise ValueError(f'A {"first funding" if first else "top-up"} is ${lo:g} to ${MAX_USD:,.0f}.')
    total = int(usd / px * LAMPORTS)
    fee = int(fee_usd / px * LAMPORTS + 0.999999)   # FEELESS's cut rounds up to the lamport, the cat's share is the rest
    return {'usd': round(usd, 2), 'feeUsd': fee_usd, 'solUsd': round(px, 4), 'totalLamports': total, 'feeLamports': fee, 'catLamports': total - fee,
            'catUsd': round(usd - fee_usd, 2)}


def build(owner, cat_wallet, fee_wallet, p, blockhash):
    """→ base64 of the UNSIGNED v0 transaction: owner pays the fee transfer (if any) and the cat's share. Raises ValueError on a bad key."""
    try:
        payer, cat, fee = Pubkey.from_string(owner), Pubkey.from_string(cat_wallet), Pubkey.from_string(fee_wallet) if p['feeLamports'] else None
        bh = Hash.from_string(blockhash)
    except Exception:
        raise ValueError('A wallet address is not valid.')
    if payer == cat or (fee and fee in (payer, cat)):
        raise ValueError('The cat wallet, the fee wallet and yours must all differ.')
    ixs = ([transfer(TransferParams(from_pubkey=payer, to_pubkey=fee, lamports=p['feeLamports']))] if fee else []) + \
        [transfer(TransferParams(from_pubkey=payer, to_pubkey=cat, lamports=p['catLamports']))]
    msg = MessageV0.try_compile(payer, ixs, [], bh)
    return base64.b64encode(bytes(VersionedTransaction.populate(msg, [Signature.default()]))).decode()


def verify(signed_b64, built_b64, owner):
    """The signed copy must carry EXACTLY the message we built, signed by `owner`. → its signature string. Raises ValueError."""
    try:
        signed = VersionedTransaction.from_bytes(base64.b64decode(signed_b64, validate=True))
        built = VersionedTransaction.from_bytes(base64.b64decode(built_b64, validate=True))
    except Exception:
        raise ValueError('That is not a transaction.')
    if to_bytes_versioned(signed.message) != to_bytes_versioned(built.message):
        raise ValueError('The signed transaction is not the one FEELESS built — nothing was sent.')
    if str(signed.message.account_keys[0]) != owner or not all(signed.verify_with_results()):
        raise ValueError("It is not signed by the cat's owner wallet — nothing was sent.")
    return str(signed.signatures[0])
