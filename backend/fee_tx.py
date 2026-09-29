"""Builds the Swap API transaction ourselves so the FEELESS fee is its own transfer inside the trade.
Jupiter's built-in platform fee is stored on-chain as one byte (max 255 bps = 2.55%; higher values fail with
'out of range integral type conversion'), so FEELESS collects its fee directly: from the SOL/USDC paid (before
the swap) or from the SOL/USDC received (after the swap, on the guaranteed minimum output)."""
import base64
import struct

from solders.address_lookup_table_account import AddressLookupTable, AddressLookupTableAccount
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction

TOKEN_PROGRAM = Pubkey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
ATA_PROGRAM = Pubkey.from_string('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
WSOL = 'So11111111111111111111111111111111111111112'
DECIMALS = {WSOL: 9, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 6, 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB': 6}


def split_fee(amount_atoms: int, bps: int):
    """(fee, amount that actually gets swapped). The trader pays amount_atoms in total."""
    fee = amount_atoms * bps // 10000
    return fee, amount_atoms - fee


def jup_instruction(d):
    return Instruction(Pubkey.from_string(d['programId']), base64.b64decode(d['data']),
                       [AccountMeta(Pubkey.from_string(a['pubkey']), a['isSigner'], a['isWritable']) for a in d['accounts']])


def ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    return Pubkey.find_program_address([bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)], ATA_PROGRAM)[0]


def fee_instructions(payer: str, fee_mint: str, fee_account: str, atoms: int):
    """SOL: send lamports into the wSOL fee account and sync it. SPL (USDC/USDT): transferChecked from the
    trader's token account into the FEELESS fee account."""
    payer_k, dest = Pubkey.from_string(payer), Pubkey.from_string(fee_account)
    if fee_mint == WSOL:
        return [transfer(TransferParams(from_pubkey=payer_k, to_pubkey=dest, lamports=atoms)),
                Instruction(TOKEN_PROGRAM, bytes([17]), [AccountMeta(dest, False, True)])]  # SyncNative
    mint = Pubkey.from_string(fee_mint)
    data = bytes([12]) + struct.pack('<QB', atoms, DECIMALS[fee_mint])  # TransferChecked
    return [Instruction(TOKEN_PROGRAM, data, [AccountMeta(ata(payer_k, mint), False, True), AccountMeta(mint, False, False),
                                             AccountMeta(dest, False, True), AccountMeta(payer_k, True, False)])]


def lookup_tables(keys, rpc_values):
    tables = []
    for key, value in zip(keys, rpc_values):
        if value:
            raw = base64.b64decode(value['data'][0])
            tables.append(AddressLookupTableAccount(Pubkey.from_string(key), list(AddressLookupTable.deserialize(raw).addresses)))
    return tables


def build_transaction(payer: str, parts: dict, fee_ixs, tables, blockhash: str, after: bool = False) -> str:
    """Unsigned v0 transaction. Fee paid from the input: compute budget → FEELESS fee → setup → swap → cleanup.
    Fee paid from the output (after=True): … swap → cleanup (SOL unwrapped back to the wallet) → FEELESS fee. Base64."""
    ixs = [jup_instruction(i) for i in parts.get('computeBudgetInstructions') or []] + ([] if after else list(fee_ixs))
    ixs += [jup_instruction(i) for i in parts.get('setupInstructions') or []] + [jup_instruction(parts['swapInstruction'])]
    if parts.get('cleanupInstruction'):
        ixs.append(jup_instruction(parts['cleanupInstruction']))
    ixs += list(fee_ixs) if after else []
    ixs += [jup_instruction(i) for i in parts.get('otherInstructions') or []]
    msg = MessageV0.try_compile(Pubkey.from_string(payer), ixs, tables, Hash.from_string(blockhash))
    return base64.b64encode(bytes(VersionedTransaction.populate(msg, [Signature.default()]))).decode()
