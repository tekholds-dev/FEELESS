"""⚡ HQ › Fuse wallet: its network reads run together (lag catcher, 2026-11-14: p50 3.6 s), and a busy RPC still never shows an empty wallet."""
import asyncio
import time


class Req:
    headers = {}
    client = None


def _wire(monkeypatch, bal_fails=False):
    import reputation_service as rs
    import rep_money_routes as M
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER')
    async def nap(v, s=0.2):
        await asyncio.sleep(s); return v
    async def signer():
        return None
    async def wallets():
        return await nap([{'blockchain': 'SOL', 'address': 'FUSE', 'id': 'w1'}])
    async def balances(addr):
        await asyncio.sleep(0.2)
        if bal_fails:
            raise RuntimeError('429 rate limited')
        return {'sol': 0.05, 'tokens': {}, 'decimals': {}}
    async def sol():
        return await nap(80.0)
    monkeypatch.setattr(rs, '_fw_signer_check', signer)
    monkeypatch.setattr(rs, '_circle_wallets_live', wallets)
    monkeypatch.setattr(rs, '_fw_balances', balances)
    monkeypatch.setattr(rs, '_sol_usd_live', sol)
    monkeypatch.setattr(rs, '_fw_load', lambda: {'cfg': {'address': 'FUSE', 'reserveSol': 0.019}, 'books': {}, 'ledger': []})
    return rs, M


def test_the_reads_overlap(monkeypatch):
    rs, M = _wire(monkeypatch)
    t = time.time(); v = asyncio.run(M.fuse_wallet_view(Req()))
    assert time.time() - t < 0.5                                   # three 0.2 s reads together, not 0.6 s in a row
    assert v['balances']['sol'] == 0.05 and v['solUsd'] == 80.0 and v['wallets'][0]['address'] == 'FUSE' and v['error'] is None


def test_a_busy_rpc_shows_the_last_good_balance_marked_stale(monkeypatch):
    rs, M = _wire(monkeypatch, bal_fails=True)
    monkeypatch.setattr(rs, '_FW_BAL', {'bal': {'sol': 0.04, 'tokens': {}}, 'addr': 'FUSE', 'at': 1})
    v = asyncio.run(M.fuse_wallet_view(Req()))
    assert v['balances']['sol'] == 0.04 and v['balances']['stale'] is True
