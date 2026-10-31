"""💵 FUND A CAT — the payment split (owner 2026-10-29, DECISIONS #2: "wallets created per user payment — part of payment goes to feeless and
the other goes into the new agent wallet"; "one-time $2 comes out of minimal $10 per agent, up to 4 cats per user"). Pure, tested
(tests/test_cat_fund.py).

ONE transaction the user's wallet signs, two SOL transfers in it: the one-time FEELESS fee (FEE_USD, the cat's FIRST funding only) to the
FEELESS fee wallet, and the rest to the cat's own Crossmint wallet. The server builds it (`build`), keeps what it built for PLAN_SEC, and
only sends a signed copy whose message is byte-for-byte the one it built, signed by the cat's owner (`verify`) — the same rule as every
FEELESS swap. A top-up later is all for the cat (no fee). Amounts are SOL at the live price, rounded DOWN to the lamport for the cat."""
import base64

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.message import MessageV0, to_bytes_versioned
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction

MIN_USD = 10.0          # the least a first funding may be
FEE_USD = 2.0           # FEELESS's one-time cut, out of the first funding
TOPUP_MIN_USD = 1.0     # a later top-up
START_CREDIT_USD = 5.0  # 🧠 a user's general agent starts with at least $5 of model credit (OpenRouter's minimum top-up) + the $2 fee = $7 (owner 2026-10-31)
MAX_USD = 5000.0
MODEL_FLOOR_USD = 5.0   # below this OpenRouter balance, model credit is not sold
MAX_CATS = 4            # cats with their own wallet, per owner wallet
PLAN_SEC = 90.0         # a built transaction is good for this long (its blockhash lives ~60-90s)
LAMPORTS = 1_000_000_000
USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
USDC_UNITS = 1_000_000
TOKEN_PROGRAM = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
ATA_PROGRAM = 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'
SYSTEM_PROGRAM = '11111111111111111111111111111111'
GAS_LAMPORTS = 3_000_000   # a USDC funding also drops this SOL in its wallet: with no SOL it could neither move nor withdraw its USDC
COMPUTE_PROGRAM = 'ComputeBudget111111111111111111111111111111'
LIGHTHOUSE_PROGRAM = 'L2TExMFKdjpN9kozasaurPirfHy9P8sbXoAN1qA3S95'
WALLET_EXTRAS = (COMPUTE_PROGRAM, LIGHTHOUSE_PROGRAM)   # what wallets like Phantom add on signing: fee settings and safety checks, neither can move money
FEE_RESERVE = 10_000       # lamports left behind for the network fee on an all-out SOL withdrawal


def plan(usd, sol_usd, first, fee_usd=FEE_USD, min_usd=MIN_USD, token='SOL', credit=False, credit_usd=0.0, free_credit=False, start_credit=0.0):
    """$ amount + live SOL price + is this the cat's first funding (+ HQ's fee / minimum; a creator wallet: fee 0, min $1) →
    {usd, payUsd, feeUsd, creditUsd, solUsd, totalLamports, feeLamports, catLamports, catUsd, token, gasLamports}. The three amounts are the token's smallest unit (USDC: 1e-6).
    ONE amount, split (owner 2026-10-30): `credit_usd` of it is model credit, paid to FEELESS in the same transaction; the rest goes to its wallet. `credit` = all of it.
    `free_credit`: a creator wallet's credit costs nothing, so only its wallet share is paid.
    `start_credit`: a user's general agent's FIRST funding — at least this much model credit, and the one-time fee comes out of the rest
    (so $7 = $5 credit + $2 fee works even when nothing is left for its wallet)."""
    usd, px = float(usd or 0), 1.0 if token == 'USDC' else float(sol_usd or 0)
    credit_usd = usd if credit else min(usd, max(0.0, float(credit_usd or 0)))
    wallet_usd = round(usd - credit_usd, 2)
    start_credit = float(start_credit or 0) if first else 0.0
    if start_credit and credit_usd + 1e-9 < start_credit:
        raise ValueError(f'A new agent starts with at least ${start_credit:g} of model credit + the ${float(fee_usd or 0):g} start fee (${start_credit + float(fee_usd or 0):g} in all).')
    first = first and (wallet_usd > 0 or bool(start_credit))
    if px <= 0:
        raise ValueError('No live SOL price right now — try again in a minute.')
    fee_usd = max(0.0, float(fee_usd or 0)) if first else 0.0
    lo = (fee_usd if start_credit else max(float(min_usd or 0), fee_usd + 1)) if first else TOPUP_MIN_USD
    if start_credit and wallet_usd + 1e-9 < fee_usd:
        raise ValueError(f'Add ${fee_usd - wallet_usd:.2f} more: the ${fee_usd:g} start fee comes on top of its ${credit_usd:g} model credit.')
    if not start_credit and wallet_usd > 0 and wallet_usd < lo and first and wallet_usd <= fee_usd + 1e-9:
        raise ValueError(f'${wallet_usd:g} only covers the ${fee_usd:g} one-time fee — a first funding starts at ${lo:g} so its wallet gets money to trade.')
    if not lo <= (wallet_usd if wallet_usd > 0 else usd) <= MAX_USD:
        raise ValueError(f'A {"first funding" if first else "top-up"} is ${lo:g} to ${MAX_USD:,.0f}.')
    paid_credit = 0.0 if free_credit else credit_usd
    pay_usd = wallet_usd + paid_credit
    scale = USDC_UNITS if token == 'USDC' else LAMPORTS
    total = int(pay_usd / px * scale)
    fee = min(total, int((fee_usd + paid_credit) / px * scale + 0.999999))   # FEELESS's cut rounds up to the lamport, the cat's share is the rest
    return {'usd': round(usd, 2), 'payUsd': round(pay_usd, 2), 'feeUsd': fee_usd, 'creditUsd': round(credit_usd, 2), 'solUsd': round(px, 4), 'totalLamports': total, 'feeLamports': fee, 'catLamports': total - fee,
            'catUsd': round(wallet_usd - fee_usd, 2), 'token': token, 'gasLamports': GAS_LAMPORTS if token == 'USDC' and wallet_usd > 0 else 0}


def credit_open(left_usd, credit_usd=0.0, floor=MODEL_FLOOR_USD):
    """🛟 May FEELESS sell model credit right now? Only while its OpenRouter balance can cover it; an unknown balance means no. Pure."""
    return left_usd is not None and float(left_usd) >= max(float(floor), float(credit_usd or 0))


def ata(owner, mint=USDC_MINT):
    """The associated token account of `owner` (str or Pubkey)."""
    o = Pubkey.from_string(owner) if isinstance(owner, str) else owner
    return Pubkey.find_program_address([bytes(o), bytes(Pubkey.from_string(TOKEN_PROGRAM)), bytes(Pubkey.from_string(mint))], Pubkey.from_string(ATA_PROGRAM))[0]


def _open_usdc(payer, owner):
    """Create `owner`'s USDC account if it has none (idempotent: costs nothing when it exists)."""
    mint = Pubkey.from_string(USDC_MINT)
    return Instruction(Pubkey.from_string(ATA_PROGRAM), bytes([1]), [AccountMeta(payer, True, True), AccountMeta(ata(owner), False, True), AccountMeta(owner, False, False),
                       AccountMeta(mint, False, False), AccountMeta(Pubkey.from_string(SYSTEM_PROGRAM), False, False), AccountMeta(Pubkey.from_string(TOKEN_PROGRAM), False, False)])


def _send_usdc(payer, to, units):
    return Instruction(Pubkey.from_string(TOKEN_PROGRAM), bytes([12]) + int(units).to_bytes(8, 'little') + bytes([6]),   # TransferChecked, 6 decimals
                       [AccountMeta(ata(payer), False, True), AccountMeta(Pubkey.from_string(USDC_MINT), False, False), AccountMeta(ata(to), False, True), AccountMeta(payer, True, False)])


def build(owner, cat_wallet, fee_wallet, p, blockhash):
    """→ base64 of the UNSIGNED v0 transaction: owner pays the fee transfer (if any) and the cat's share. Raises ValueError on a bad key."""
    try:
        payer, cat, fee = Pubkey.from_string(owner), Pubkey.from_string(cat_wallet), Pubkey.from_string(fee_wallet) if p['feeLamports'] else None
        bh = Hash.from_string(blockhash)
    except Exception:
        raise ValueError('A wallet address is not valid.')
    if payer == cat or (fee and fee in (payer, cat)):
        raise ValueError('The cat wallet, the fee wallet and yours must all differ.')
    legs = ([(fee, p['feeLamports'])] if fee else []) + ([(cat, p['catLamports'])] if p['catLamports'] else [])
    if p.get('token') == 'USDC':
        ixs = [i for to, n in legs for i in (_open_usdc(payer, to), _send_usdc(payer, to, n))]
        if p.get('gasLamports'):
            ixs.append(transfer(TransferParams(from_pubkey=payer, to_pubkey=cat, lamports=p['gasLamports'])))
    else:
        ixs = [transfer(TransferParams(from_pubkey=payer, to_pubkey=to, lamports=n)) for to, n in legs]
    ixs = [set_compute_unit_limit(200_000 if p.get('token') == 'USDC' else 20_000), set_compute_unit_price(50_000)] + ixs   # fee settings in place: wallets then leave them alone
    msg = MessageV0.try_compile(payer, ixs, [], bh)
    return base64.b64encode(bytes(VersionedTransaction.populate(msg, [Signature.default()]))).decode()


def build_out(agent_wallet, owner, token, units, blockhash):
    """↩ An unsigned withdrawal: `units` of SOL / USDC from its wallet to `owner`, the agent's own wallet paying. → base64."""
    try:
        payer, to, bh = Pubkey.from_string(agent_wallet), Pubkey.from_string(owner), Hash.from_string(blockhash)
    except Exception:
        raise ValueError('A wallet address is not valid.')
    if payer == to or int(units) <= 0:
        raise ValueError('Nothing to withdraw.')
    ixs = [_open_usdc(payer, to), _send_usdc(payer, to, units)] if token == 'USDC' else [transfer(TransferParams(from_pubkey=payer, to_pubkey=to, lamports=int(units)))]
    return base64.b64encode(bytes(VersionedTransaction.populate(MessageV0.try_compile(payer, ixs, [], bh), [Signature.default()]))).decode()


def _moves(msg):
    """What a message really does: every instruction but the wallet's harmless extras, as (program, accounts, data)."""
    keys = list(msg.account_keys)
    rows = [(str(keys[i.program_id_index]), tuple(str(keys[a]) for a in bytes(i.accounts)), bytes(i.data)) for i in msg.instructions]
    return [x for x in rows if x[0] not in WALLET_EXTRAS]


def verify(signed_b64, built_b64, owner):
    """The signed copy must carry EXACTLY the message we built, signed by `owner`. → its signature string. Raises ValueError."""
    try:
        signed = VersionedTransaction.from_bytes(base64.b64decode(signed_b64, validate=True))
        built = VersionedTransaction.from_bytes(base64.b64decode(built_b64, validate=True))
    except Exception:
        raise ValueError('That is not a transaction.')
    a, b = signed.message, built.message
    if to_bytes_versioned(a) != to_bytes_versioned(b):   # a wallet may add fee settings or safety checks, or refresh the blockhash; every money move must stay exactly as built, same payer
        if getattr(a, 'address_table_lookups', None) or _moves(a) != _moves(b) or a.account_keys[0] != b.account_keys[0]:
            print(f"[cat fund] refused a signed copy: lookups {bool(getattr(a, 'address_table_lookups', None))} · payer same {a.account_keys[0] == b.account_keys[0]} · programs {sorted({str(a.account_keys[i.program_id_index])[:8] for i in a.instructions})}")
            raise ValueError('The signed transaction is not the one FEELESS built — nothing was sent.')
    if str(signed.message.account_keys[0]) != owner or not all(signed.verify_with_results()):
        raise ValueError("It is not signed by the cat's owner wallet — nothing was sent.")
    return str(signed.signatures[0])
