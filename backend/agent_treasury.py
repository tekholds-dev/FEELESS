"""🏦 THE AGENT TREASURY (owner 2026-10-31): an agent launches its own coin from ITS wallet (pump.fun · LetsBONK · LaunchLab, never FEELESS); the
creator fees people pay trading that coin pile up for the agent — its treasury. The owner sets the split: the Agent Pass holder · its model
credit (it pays for its own thinking) · a buyback of its own coin (from those fees only, capped, shown on its desk — never other money, never
fake volume). This module READS the fees on-chain (pump.fun's creator vault while on the curve, PumpSwap's after it graduates) and plans the
split. Claiming + paying out from the agent's wallet is the next, owner-tested step. Pure + one read, tested (tests/test_agent_treasury.py)."""
from solders.pubkey import Pubkey

PUMP = Pubkey.from_string('6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P')
PUMP_SWAP = Pubkey.from_string('pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA')
TOKEN = Pubkey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
ATA = Pubkey.from_string('ATokenGPvbdGVxr1b2hvZbsiqW5xWW25efv8HRWHngwM')
WSOL = Pubkey.from_string('So11111111111111111111111111111111111111112')
RENT_FLOOR = 890_880          # a 0-byte system account's rent-exempt minimum: what stays behind in the pump vault
DEFAULT_SPLIT = {'holder': 50, 'credit': 30, 'buyback': 20}
BUYBACK_MAX = 50              # the most of each payout that may buy back its own coin (owner rule: from fees only, capped, shown)


def pump_vault(creator):
    return Pubkey.find_program_address([b'creator-vault', bytes(Pubkey.from_string(creator))], PUMP)[0]


def swap_vault(creator):
    """PumpSwap keeps a graduated coin's creator fees as WSOL in its vault authority's token account."""
    auth = Pubkey.find_program_address([b'creator_vault', bytes(Pubkey.from_string(creator))], PUMP_SWAP)[0]
    return Pubkey.find_program_address([bytes(auth), bytes(TOKEN), bytes(WSOL)], ATA)[0]


def clean_split(raw):
    """The owner's split → whole percents that add up to 100 (buyback capped); anything unusable → the default."""
    try:
        s = {k: max(0, int(round(float((raw or {}).get(k, 0))))) for k in DEFAULT_SPLIT}
    except (TypeError, ValueError):
        return dict(DEFAULT_SPLIT)
    if sum(s.values()) != 100 or s['buyback'] > BUYBACK_MAX:
        return dict(DEFAULT_SPLIT)
    return s


def plan(lamports, split):
    """What each part gets from `lamports` of fees (rounded down; the rest stays for the next payout)."""
    s = clean_split(split)
    return {k: int(int(lamports or 0) * v // 100) for k, v in s.items()}


async def read(http, rpc, creator):
    """The fees waiting for this creator wallet → {'pump': lamports, 'pumpSwap': lamports, 'total'}; a read that fails counts 0."""
    out = {'pump': 0, 'pumpSwap': 0}
    try:
        v = ((await rpc(http, 'getAccountInfo', [str(pump_vault(creator)), {'encoding': 'base64'}])) or {}).get('value')
        out['pump'] = max(0, int((v or {}).get('lamports') or 0) - RENT_FLOOR)
    except Exception:
        pass
    try:
        b = ((await rpc(http, 'getTokenAccountBalance', [str(swap_vault(creator))])) or {}).get('value') or {}
        out['pumpSwap'] = int(b.get('amount') or 0)
    except Exception:
        pass
    out['total'] = out['pump'] + out['pumpSwap']
    return out

