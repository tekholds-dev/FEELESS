import base64
import struct

import pytest

from coin_meta import parse_metadata


def pad(s, n):
    b = s.encode()
    return struct.pack('<I', n) + b + b'\x00' * (n - len(b))


def test_parse_metadata_strings():
    raw = bytes([4]) + b'\x01' * 32 + b'\x02' * 32 + pad('FEELESS', 32) + pad('FEE', 10) + pad('https://ipfs.io/ipfs/Qm123', 200)
    m = parse_metadata(base64.b64encode(raw).decode())
    assert m == {'name': 'FEELESS', 'symbol': 'FEE', 'uri': 'https://ipfs.io/ipfs/Qm123'}


def test_metadata_pda_is_stable():
    pytest.importorskip('solders')
    from coin_meta import metadata_pda
    wsol = 'So11111111111111111111111111111111111111112'
    assert metadata_pda(wsol) == metadata_pda(wsol) and len(metadata_pda(wsol)) >= 32
