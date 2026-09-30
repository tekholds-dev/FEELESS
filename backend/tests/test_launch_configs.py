"""Public vs house launch configs: a house config never replaces the site's public one."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip('solders')
rs = pytest.importorskip('reputation_service')
OWNER, PUB, HOUSE, CLAIM = 'O' * 43, 'P' * 43, 'H' * 43, 'C' * 43


def test_house_config_sits_beside_public(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'LAUNCH_RAIL_PATH', tmp_path / 'r.json')
    monkeypatch.setattr(rs, '_require_admin', lambda r: OWNER); monkeypatch.setattr(rs, '_owner_wallets', lambda: [OWNER])

    async def rpc(http, method, params):
        return {'value': {'owner': rs.DBC_PROGRAM}}
    monkeypatch.setattr(rs, '_rpc', rpc)
    asyncio.run(rs.launch_rail_set(None, rs.LaunchRailIn(config=PUB, feeClaimer=CLAIM, params={'initialMarketCap': 30})))
    asyncio.run(rs.launch_rail_set(None, rs.LaunchRailIn(config=HOUSE, feeClaimer=CLAIM, params={'initialMarketCap': 100}, scope='house', label='Reserve coins')))
    d = asyncio.run(rs.launch_rail())
    assert d['ready'] and d['config'] == PUB and d['params']['initialMarketCap'] == 30
    assert d['house'][0]['config'] == HOUSE and d['house'][0]['label'] == 'Reserve coins'
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.launch_rail_set(None, rs.LaunchRailIn(config=HOUSE, feeClaimer=CLAIM, scope='weird')))
