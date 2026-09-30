"""Season badge reserve pool: weighted shares, dust handling, protected wallets, owner-signed payouts only."""
import asyncio
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reserve_pool as rp  # noqa: E402

A, B, C, D = ('A' * 32, 'B' * 32, 'C' * 32, 'D' * 32)


def test_weighted_shares_and_pot_keeps_rent():
    plan = rp.payout_plan(10, 50, [{'address': A, 'tier': 'Legend'}, {'address': B, 'tier': 'Bronze'}, {'address': C, 'tier': 'Recruit'}])
    assert plan['potSol'] == 5 and [r['address'] for r in plan['rows']] == [A, B]  # Recruit earns nothing
    assert plan['rows'][0]['sol'] == pytest.approx(5 * 12 / 13, abs=1e-6) and plan['paidSol'] <= plan['potSol']
    assert rp.payout_plan(0.005, 100, [{'address': A, 'tier': 'Gold'}])['potSol'] == 0  # never drains the rent reserve


def test_dust_dropped_and_resplit_and_protected_excluded():
    holders = [{'address': A, 'tier': 'Legend'}] + [{'address': f'{i:0>32}', 'tier': 'Bronze'} for i in range(50)]
    plan = rp.payout_plan(0.02, 50, holders)  # pot 0.01: bronze shares are dust
    assert [r['address'] for r in plan['rows']] == [A] and plan['rows'][0]['sol'] == pytest.approx(0.01) and plan['droppedDust'] == 50
    assert rp.payout_plan(10, 10, [{'address': A, 'tier': 'Gold'}], excluded={A})['rows'] == []
    assert rp.wallet_share(plan, A)['tier'] == 'Legend' and rp.wallet_share(plan, B) is None


def test_payout_record_requires_reserve_wallet_signature(monkeypatch, tmp_path):
    pytest.importorskip('solders')
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, 'SEASONS_PATH', tmp_path / 's.json'); monkeypatch.setattr(rs, 'COLLECTION_PATH', tmp_path / 'c.json')
    monkeypatch.setattr(rs, 'BLOCK_PATH', tmp_path / 'b.json')
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'Admin')
    monkeypatch.setattr(rs, '_admin_load', lambda: {'audit': []}); monkeypatch.setattr(rs, '_audit', lambda *a: None); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    now = time.time()
    rs._json_save(rs.SEASONS_PATH, {'seasons': [{'id': 's1', 'name': 'S', 'start': now - 10, 'end': now + 99, 'accent': '#00ffa3', 'reserveWallet': D, 'badgeRewardPct': 50}],
                                    'scores': {'s1': {A: {'score': 13000}, B: {'score': 300}}}})
    signer = {'v': D}

    async def fake_rpc(http, method, params):
        if method == 'getBalance':
            return {'value': 4 * 10**9}
        xfer = lambda to, sol: {'program': 'system', 'parsed': {'type': 'transfer', 'info': {'source': signer['v'], 'destination': to, 'lamports': int(sol * 1e9)}}}
        return {'meta': {'err': None}, 'transaction': {'message': {'accountKeys': [{'pubkey': signer['v'], 'signer': True}],
                                                                   'instructions': [xfer(A, 1.8), xfer(B, 0.15)]}}}
    monkeypatch.setattr(rs, '_rpc', fake_rpc)
    plan = asyncio.run(rs.admin_reserve_plan(None, 's1'))
    assert plan['potSol'] == 2 and [r['tier'] for r in plan['rows']] == ['Legend', 'Bronze']
    sig = '5' * 88
    signer['v'] = A  # signed by someone else: refused
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_reserve_paid(None, 's1', rs.ReservePaid(sigs=[sig])))
    signer['v'] = D
    out = asyncio.run(rs.admin_reserve_paid(None, 's1', rs.ReservePaid(sigs=[sig])))
    assert out['wallets'] == 2 and out['paidSol'] == 1.95  # what moved on-chain
    with pytest.raises(rs.HTTPException):  # never paid twice
        asyncio.run(rs.admin_reserve_paid(None, 's1', rs.ReservePaid(sigs=[sig])))
    pub = asyncio.run(rs.season_reserve(A))
    assert pub['active'] and pub['me']['tier'] == 'Legend'
