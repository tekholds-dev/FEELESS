"""⛓ STORE ON IPFS, PAID BY THE AGENT'S OWN WALLET (owner 2026-11-02: "build it" after the live $0.13 test).

toju.network keeps a file on IPFS (Storacha, pinned on its gateway) for N days, paid in SOL on Solana, no account:
  1 QUOTE   POST /upload/deposit (multipart: file · duration seconds · publicKey) → ONE escrow instruction + the file's CID. We build the
            transaction and SIMULATE it: the real SOL it costs (≈ 0.0013 SOL — the deposit account's rent; storage itself ≈ 1 lamport).
  2 STORE   only after the owner presses it: rebuilt with a fresh blockhash, simulated again, Circle signs (the agent's own wallet),
            then POST /upload/confirm {cid, transactionHash} and /upload/history gives the gateway link.
Guards (the server's, whatever the page sends): toju's known program only · the agent's wallet the ONLY signer · ≤ MAX_SOL · the
trade gas reserve always stays · the store matches the quote it showed (cost may not rise > 10 %).
Live proof 2026-11-02: tx YE3rtSRa…RpLS, 71-byte file read back byte-for-byte.
"""
import base64

API = 'https://api.toju.network'
PROGRAM = 'CSXnfQsFWxdPB5pnS73TQDA6ivK6kcFnRwtt6TgFquxH'
SYSTEM = '11111111111111111111111111111111'
DAYS = 30
MAX_SOL = 0.004
QUOTE_TTL = 600
FEE_LAMPORTS = 5000


def check(d, addr):
    """The deposit toju answered → its one instruction, or ValueError when it is not exactly the escrow we know."""
    ins = (d or {}).get('instructions') or []
    if len(ins) != 1 or not d.get('cid'):
        raise ValueError('The storage service answered something unexpected — nothing was signed.')
    i0 = ins[0]
    if i0.get('programId') != PROGRAM:
        raise ValueError('The storage service asked for a different program — nothing was signed.')
    signers = [k.get('pubkey') for k in i0.get('keys') or [] if k.get('isSigner')]
    if signers != [addr]:
        raise ValueError('The storage service asked for another signer — nothing was signed.')
    return i0


def build(i0, addr, blockhash):
    """The unsigned transaction (base64): the agent's wallet pays the fee and is the only signer."""
    from solders.hash import Hash
    from solders.instruction import AccountMeta, Instruction
    from solders.message import Message
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
    ix = Instruction(Pubkey.from_string(i0['programId']), base64.b64decode(i0['data']),
                     [AccountMeta(Pubkey.from_string(k['pubkey']), bool(k['isSigner']), bool(k['isWritable'])) for k in i0['keys']])
    return base64.b64encode(bytes(Transaction.new_unsigned(Message.new_with_blockhash([ix], Pubkey.from_string(addr), Hash.from_string(blockhash))))).decode()


async def cost(rpc, addr, i0):
    """(lamports it would really cost, the unsigned tx) from a simulation — nothing signed. ValueError when the chain would refuse it."""
    bh = ((await rpc('getLatestBlockhash', [{'commitment': 'confirmed'}])) or {}).get('value', {}).get('blockhash')
    if not bh:
        raise ValueError('Solana did not answer — try again.')
    tx = build(i0, addr, bh)
    before = int(((await rpc('getBalance', [addr, {'commitment': 'confirmed'}])) or {}).get('value') or 0)
    sim = ((await rpc('simulateTransaction', [tx, {'encoding': 'base64', 'sigVerify': False, 'replaceRecentBlockhash': True,
                                                     'accounts': {'encoding': 'base64', 'addresses': [addr]}}])) or {}).get('value') or {}
    after = ((sim.get('accounts') or [None])[0] or {}).get('lamports')
    if sim.get('err') or after is None:
        raise ValueError(f"The chain would refuse it ({str(sim.get('err') or 'no simulation')[:80]}) — nothing was signed.")
    return before - int(after) + FEE_LAMPORTS, tx, before


def afford(lamports, balance, gas_sol):
    """None when it may pay, else why not (a hard cap + the trade gas reserve stays)."""
    if lamports > MAX_SOL * 1e9:
        return f'It would cost {lamports / 1e9:.6f} SOL — over the {MAX_SOL} SOL cap.'
    if balance - lamports < gas_sol * 1e9:
        return f'Its wallet keeps {gas_sol} SOL for gas — add {((gas_sol * 1e9 + lamports - balance) / 1e9):.6f} SOL first.'
    return None


async def deposit(http, raw, name, mime, addr, days=DAYS):
    r = await http.post(f'{API}/upload/deposit', files={'file': (name, raw, mime or 'application/octet-stream')},
                        data={'duration': str(int(days) * 86400), 'publicKey': addr}, timeout=90)
    if r.status_code != 200:
        raise ValueError(f'The storage service refused the file ({r.status_code}).')
    return r.json()


async def confirm(http, cid, sig, addr):
    """toju records the paid deposit → the gateway link of the file."""
    r = await http.post(f'{API}/upload/confirm', json={'cid': cid, 'transactionHash': sig}, timeout=60)
    if r.status_code != 200 or not (r.json() or {}).get('verified'):
        raise ValueError('Paid, but the storage service has not confirmed it yet — it is kept on its CID.')
    h = await http.get(f'{API}/upload/history', params={'userAddress': addr, 'page': 1, 'limit': 20}, timeout=30)
    row = next((x for x in ((h.json() or {}).get('data') or []) if x.get('contentCid') == cid), {}) if h.status_code == 200 else {}
    return row.get('url') or f'https://ipfs.io/ipfs/{cid}', row.get('expiresAt')
