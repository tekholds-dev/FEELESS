"""🎯 Concentrated positions: decode Orca / Raydium position + pool accounts, in range or out (by how much), a re-centred range."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
cr = pytest.importorskip('clmm_range')
Pubkey = pytest.importorskip('solders.pubkey').Pubkey

POOL = Pubkey.from_string('So11111111111111111111111111111111111111112')
MINT = Pubkey.from_string('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')


def orca_position(lo, hi, liq=10**9):
    return b'\0' * 8 + bytes(POOL) + bytes(MINT) + liq.to_bytes(16, 'little') + struct.pack('<ii', lo, hi) + b'\0' * 120


def orca_pool(tick, spacing=64):
    d = bytearray(260)
    struct.pack_into('<H', d, 41, spacing); struct.pack_into('<i', d, 81, tick)
    return bytes(d)


def ray_position(lo, hi, liq=10**9):
    return b'\0' * 8 + b'\1' + bytes(MINT) + bytes(POOL) + struct.pack('<ii', lo, hi) + liq.to_bytes(16, 'little') + b'\0' * 100


def ray_pool(tick, spacing=60):
    d = bytearray(400)
    struct.pack_into('<H', d, 235, spacing); struct.pack_into('<i', d, 269, tick)
    return bytes(d)


def test_both_layouts_decode_to_the_same_shape():
    for kind, pos, pool in (('orca', orca_position(-1000, 1000), orca_pool(250)), ('raydium', ray_position(-1000, 1000), ray_pool(250, 60))):
        p, q = cr.parse_position(kind, pos), cr.parse_pool(kind, pool)
        assert p == {'pool': str(POOL), 'liquidity': 10**9, 'lo': -1000, 'hi': 1000} and q['tick'] == 250
    assert cr.parse_position('orca', b'short') is None and cr.parse_pool('raydium', b'\0' * 50) is None
    assert len(cr.position_pda('orca', str(MINT))) >= 32 and cr.position_pda('orca', str(MINT)) != cr.position_pda('raydium', str(MINT))


def test_in_range_out_of_range_and_near_the_edge():
    pos = {'lo': -1000, 'hi': 1000, 'liquidity': 1}
    mid = cr.status(pos, {'tick': 0})
    assert mid['inRange'] and 9.5 < mid['edgePct'] < 10 and 22 < mid['widthPct'] < 22.3            # ±10 % around the price, 22 % wide
    above = cr.status(pos, {'tick': 2000})
    assert not above['inRange'] and above['side'] == 'above' and 10 < above['outPct'] < 10.6      # price 10.5 % over the top: earns nothing
    below = cr.status(pos, {'tick': -1500})
    assert below['side'] == 'below' and 4.8 < below['outPct'] < 5.0
    near = cr.status(pos, {'tick': 900})
    assert near['inRange'] and near['edgePct'] < cr.EDGE_PCT
    s = cr.summary([above, below, mid, near, {**mid, 'empty': True}])
    assert (s['n'], s['out'], s['near']) == (4, 2, 1) and s['worst'] is above


def test_recenter_keeps_the_width_on_the_tick_spacing():
    r = cr.recenter({'lo': -1000, 'hi': 1000}, {'tick': 2000, 'spacing': 64})
    assert r['lo'] % 64 == 0 and r['hi'] % 64 == 0 and r['lo'] < 2000 < r['hi'] and 1990 <= r['hi'] - r['lo'] <= 2100
    assert 9 < r['downPct'] < 11 and 9 < r['upPct'] < 11.5
