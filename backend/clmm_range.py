"""🎯 CONCENTRATED POSITIONS — IN RANGE OR NOT (owner, 2026-10-22: "real errands like tighten pool"). Pure decoders for the family block:
a position NFT in the wallet → its position account (PDA from the NFT mint) → the tick range it covers → its pool's current tick. Out of range =
it earns nothing → an errand with the real numbers (how far out, how wide the range is, a re-centered range of the same width). Near the edge
(< EDGE_PCT inside) is a softer errand. Orca Whirlpools + Raydium CLMM. Pure + tested (synthetic account bytes); the service fetches.
Percent math is decimals-free: the price ratio between two ticks is 1.0001^(Δtick).
"""
import struct

ORCA = 'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc'
RAYDIUM = 'CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK'
PROGRAM = {'orca': ORCA, 'raydium': RAYDIUM}
EDGE_PCT = 5.0   # inside the range but within 5 % of an edge → "near the edge"


def position_pda(kind, nft_mint):
    """The position account of a position NFT: PDA ["position", mint] under the protocol's program (same seed on Orca and Raydium)."""
    from solders.pubkey import Pubkey
    return str(Pubkey.find_program_address([b'position', bytes(Pubkey.from_string(nft_mint))], Pubkey.from_string(PROGRAM[kind]))[0])


def _pk(b):
    from solders.pubkey import Pubkey
    return str(Pubkey.from_bytes(bytes(b)))


def parse_position(kind, data):
    """Position account bytes → {pool, liquidity, lo, hi} (ticks) or None when too short.
    Orca Position: 8 disc · whirlpool 32 · position_mint 32 · liquidity u128 · tick_lower i32 · tick_upper i32
    Raydium PersonalPositionState: 8 disc · bump 1 · nft_mint 32 · pool_id 32 · tick_lower i32 · tick_upper i32 · liquidity u128"""
    d = bytes(data or b'')
    if kind == 'orca' and len(d) >= 96:
        liq = int.from_bytes(d[72:88], 'little'); lo, hi = struct.unpack_from('<ii', d, 88)
        return {'pool': _pk(d[8:40]), 'liquidity': liq, 'lo': lo, 'hi': hi}
    if kind == 'raydium' and len(d) >= 97:
        lo, hi = struct.unpack_from('<ii', d, 73); liq = int.from_bytes(d[81:97], 'little')
        return {'pool': _pk(d[41:73]), 'liquidity': liq, 'lo': lo, 'hi': hi}
    return None


def parse_pool(kind, data):
    """Pool account bytes → {tick, spacing} or None.
    Orca Whirlpool: 8 disc · config 32 · bump 1 · tick_spacing u16 (41) · seed 2 · fee_rate u16 · protocol_fee u16 · liquidity u128 · sqrt_price u128 ·
      tick_current i32 (81)
    Raydium PoolState: 8 disc · bump 1 · amm_config 32 · owner 32 · mint0 32 · mint1 32 · vault0 32 · vault1 32 · observation 32 · dec0 1 · dec1 1 ·
      tick_spacing u16 (235) · liquidity u128 · sqrt_price u128 · tick_current i32 (269)"""
    d = bytes(data or b'')
    if kind == 'orca' and len(d) >= 85:
        return {'spacing': struct.unpack_from('<H', d, 41)[0], 'tick': struct.unpack_from('<i', d, 81)[0]}
    if kind == 'raydium' and len(d) >= 273:
        return {'spacing': struct.unpack_from('<H', d, 235)[0], 'tick': struct.unpack_from('<i', d, 269)[0]}
    return None


def pct(dticks):
    """The price move between two ticks, in %."""
    return (1.0001 ** dticks - 1) * 100


def status(pos, pool):
    """→ {inRange, side ('below' | 'above' | None), outPct (how far price sits outside), edgePct (room to the nearer edge when inside), widthPct,
    empty (no liquidity)}."""
    lo, hi, t = pos['lo'], pos['hi'], pool['tick']
    out = {'widthPct': round(pct(hi - lo), 2), 'empty': not pos.get('liquidity')}
    if t < lo:
        return {**out, 'inRange': False, 'side': 'below', 'outPct': round(-pct(t - lo), 2), 'edgePct': None}
    if t >= hi:
        return {**out, 'inRange': False, 'side': 'above', 'outPct': round(pct(t - hi), 2), 'edgePct': None}
    down = -pct(lo - t)   # how far price can fall before it leaves the range
    up = pct(hi - t)      # how far it can rise
    return {**out, 'inRange': True, 'side': None, 'outPct': 0.0, 'edgePct': round(min(down, up), 2)}


def recenter(pos, pool):
    """The same width, centred on the price now, snapped to the pool's tick spacing → (lo, hi) ticks + the ± % it covers."""
    half = (pos['hi'] - pos['lo']) // 2; s = max(1, int(pool.get('spacing') or 1)); t = pool['tick']
    lo = ((t - half) // s) * s; hi = lo + 2 * ((half + s - 1) // s) * s
    return {'lo': lo, 'hi': hi, 'downPct': round(-pct(lo - t), 2), 'upPct': round(pct(hi - t), 2)}


def summary(states):
    """Many positions of one market → {n, out, near, worst} (worst = the position furthest out, else the one nearest its edge)."""
    live = [s for s in states if s and not s.get('empty')]
    out = [s for s in live if not s['inRange']]
    near = [s for s in live if s['inRange'] and s['edgePct'] is not None and s['edgePct'] < EDGE_PCT]
    worst = max(out, key=lambda s: s['outPct'], default=None) or min(near, key=lambda s: s['edgePct'], default=None)
    return {'n': len(live), 'out': len(out), 'near': len(near), 'worst': worst}
