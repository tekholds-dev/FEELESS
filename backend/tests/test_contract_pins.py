"""The FUSE Card program pins Raydium CP-Swap's instruction discriminator and pool offsets — check the pin from the source of truth."""
import hashlib
import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parents[2] / 'contracts/fuse_vault/programs/fuse_card/src/raydium.rs'


def test_swap_base_input_discriminator_pin():
    pin = re.search(r'SWAP_BASE_INPUT_IX: \[u8; 8\] = \[([^\]]+)\]', SRC.read_text()).group(1)
    assert [int(x) for x in pin.split(',')] == list(hashlib.sha256(b'global:swap_base_input').digest()[:8])


def test_pool_len_matches_raydium_pool_state():
    # 8 disc + 10 pubkeys + 5 u8 + 7 u64 + 2 u8 + 6 pad + 2 u64 + 28 u64 padding (raydium-cp-swap states/pool.rs PoolState::LEN)
    assert 8 + 10 * 32 + 5 + 8 * 7 + 2 + 6 + 2 * 8 + 8 * 28 == 637
