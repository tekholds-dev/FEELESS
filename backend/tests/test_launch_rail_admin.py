"""Admins (not only the owner) can create the launch config; it must still be a real Meteora DBC config on-chain.
RPC is faked; nothing leaves the process."""
import asyncio

import pytest
from fastapi import HTTPException

import reputation_service as rs

ADMIN = 'Adm1n111111111111111111111111111111111111111'
CFG = 'Cfg11111111111111111111111111111111111111111'


def test_admin_can_create_the_launch_config_but_only_a_real_dbc_one(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, 'LAUNCH_RAIL_PATH', tmp_path / 'rail.json')
    monkeypatch.setattr(rs, '_require_admin', lambda request: ADMIN)
    monkeypatch.setattr(rs, '_owner_wallets', lambda: {'Owner1111111111111111111111111111111111111'})
    monkeypatch.setattr(rs, '_admin_load', lambda: {}); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    audit = []
    monkeypatch.setattr(rs, '_audit', lambda d, who, action, detail: audit.append((who, action)))
    owner = {'v': rs.DBC_PROGRAM}

    async def rpc(http, method, params):
        return {'value': {'owner': owner['v']}}
    monkeypatch.setattr(rs, '_rpc', rpc)
    body = rs.LaunchRailIn(config=CFG, feeClaimer=ADMIN, params={'initialMarketCap': 30}, scope='house', label='Reserve coins')
    out = asyncio.run(rs.launch_rail_set(None, body))
    assert out['house'][0]['config'] == CFG and out['house'][0]['setBy'] == ADMIN and audit == [(ADMIN, 'launch-rail')]
    owner['v'] = 'SomeOtherProgram111111111111111111111111111'
    with pytest.raises(HTTPException) as e:
        asyncio.run(rs.launch_rail_set(None, rs.LaunchRailIn(config=CFG, feeClaimer=ADMIN)))
    assert e.value.status_code == 409
