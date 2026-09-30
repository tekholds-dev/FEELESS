"""On-chain coin metadata (Metaplex Token Metadata account): name, symbol and the uri that holds the image.
Works on any Solana RPC (plain getAccountInfo), unlike Helius-only getAsset."""
import base64
import struct

METADATA_PROGRAM = 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'


def metadata_pda(mint: str) -> str:
    from solders.pubkey import Pubkey
    prog = Pubkey.from_string(METADATA_PROGRAM)
    return str(Pubkey.find_program_address([b'metadata', bytes(prog), bytes(Pubkey.from_string(mint))], prog)[0])


def parse_metadata(data_b64: str) -> dict:
    """Metadata account layout: key u8, update authority 32, mint 32, then borsh strings name / symbol / uri."""
    raw = base64.b64decode(data_b64)
    off = 1 + 32 + 32
    out = {}
    for field in ('name', 'symbol', 'uri'):
        n = struct.unpack_from('<I', raw, off)[0]
        off += 4
        out[field] = raw[off:off + n].decode('utf-8', 'ignore').rstrip('\x00').strip()
        off += n
    return out
