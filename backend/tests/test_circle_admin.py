"""Circle wallets: labels persist; sends need a valid address, a positive amount and the typed confirmation."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip('solders')
rs = pytest.importorskip('reputation_service')
TO = 'Dest111111111111111111111111111111111111WXYZ'


def test_meta_and_send_guards(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'CIRCLE_META_PATH', tmp_path / 'c.json')
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'Owner')
    monkeypatch.setattr(rs, '_admin_load', lambda: {'audit': []}); monkeypatch.setattr(rs, '_audit', lambda *a: None); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    sent = []

    async def circle(method, path, body=None):
        sent.append((path, body)); return {'id': 'tx1', 'state': 'INITIATED'}
    monkeypatch.setattr(rs, '_circle', circle)
    asyncio.run(rs.circle_wallet_meta(None, 'w1', rs.CircleMetaIn(name='Ops wallet', description='gas + airdrops')))
    assert asyncio.run(rs.circle_meta_get(None))['w1']['description'] == 'gas + airdrops'
    for bad in (dict(to='nope', confirm='nope'[-4:], amount='1'), dict(to=TO, confirm='0000', amount='1'), dict(to=TO, confirm='WXYZ', amount='-2')):
        with pytest.raises(rs.HTTPException):
            asyncio.run(rs.circle_transfer(None, rs.CircleSendIn(walletId='w1', tokenId='t1', **bad)))
    out = asyncio.run(rs.circle_transfer(None, rs.CircleSendIn(walletId='w1', tokenId='t1', to=TO, amount='2.5', confirm='WXYZ')))
    assert out['state'] == 'INITIATED' and sent[-1][0] == '/transfer' and sent[-1][1]['amount'] == '2.5'
