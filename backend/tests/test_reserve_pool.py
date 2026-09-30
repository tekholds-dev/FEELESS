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


def test_pool_holders_sum_tier_and_custom_badge_weights():
    hs = rp.pool_holders({'tier:Gold': 3, 'badge:custom-og': 5}, {A: 'Gold', B: 'Bronze'}, {A: ['custom-og'], C: ['custom-og', 'custom-x']})
    by = {h['address']: h for h in hs}
    assert by[A]['weight'] == 8 and by[C]['weight'] == 5 and B not in by
    plan = rp.payout_plan(10.01, 100, hs)
    assert plan['potSol'] == 10 and rp.wallet_share(plan, A)['sol'] == pytest.approx(10 * 8 / 13, abs=1e-6)


def test_badge_pool_any_wallet_payout_verified_never_recorded_twice(monkeypatch, tmp_path):
    pytest.importorskip('solders')
    rs = pytest.importorskip('reputation_service')
    for k, f in (('SEASONS_PATH', 's.json'), ('BADGE_POOLS_PATH', 'p.json'), ('BLOCK_PATH', 'b.json')):
        monkeypatch.setattr(rs, k, tmp_path / f)
    admin = {'badges': {A: {'custom-og': {'id': 'custom-og', 'label': 'OG'}}, B: {'custom-og': {'id': 'custom-og', 'label': 'OG'}}}, 'audit': []}
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'Admin'); monkeypatch.setattr(rs, '_admin_load', lambda: admin)
    monkeypatch.setattr(rs, '_audit', lambda *a: None); monkeypatch.setattr(rs, '_admin_save', lambda d: None)

    async def fake_rpc(http, method, params):
        if method == 'getBalance':
            return {'value': 2 * 10**9}
        return {'meta': {'err': None}, 'transaction': {'message': {'accountKeys': [{'pubkey': D, 'signer': True}],
                'instructions': [{'program': 'system', 'parsed': {'type': 'transfer', 'info': {'source': D, 'destination': A, 'lamports': 5 * 10**8}}}]}}}
    monkeypatch.setattr(rs, '_rpc', fake_rpc)
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_badge_pool_save(None, rs.BadgePoolIn(name='OG pool', wallet=D, pct=50, weights={'bad key': 1})))
    pid = asyncio.run(rs.admin_badge_pool_save(None, rs.BadgePoolIn(name='OG pool', wallet=D, pct=50, weights={'badge:custom-og': 2}, mode='weight')))['pool']['id']
    plan = asyncio.run(rs.admin_badge_pool_plan(None, pid))
    assert plan['potSol'] == 1 and {r['address'] for r in plan['rows']} == {A, B}
    assert asyncio.run(rs.admin_badge_pool_paid(None, pid, rs.ReservePaid(sigs=['6' * 88])))['paidSol'] == 0.5
    with pytest.raises(rs.HTTPException):  # same transaction can't be recorded twice
        asyncio.run(rs.admin_badge_pool_paid(None, pid, rs.ReservePaid(sigs=['6' * 88])))
    pub = asyncio.run(rs.badge_pools_public(A))
    assert pub['pools'][0]['me']['sol'] == 0.5 and pub['pools'][0]['earns'] == ['custom-og']


def test_pct_mode_each_badge_gets_its_own_slice_rest_stays():
    rows, used = rp.pct_holders({'badge:og': 30, 'badge:bug': 20, 'tier:Gold': 10, 'badge:nobody': 25},
                                {A: 'Gold'}, {A: ['og'], B: ['og', 'bug'], C: ['bug']})
    by = {r['address']: r['weight'] for r in rows}
    assert used == 60  # the 25% nobody holds stays in the wallet
    assert by[A] == pytest.approx(15 + 10) and by[B] == pytest.approx(15 + 10) and by[C] == pytest.approx(10)
    plan = rp.payout_plan(10.01, 100 * used / 100, rows)
    assert plan['potSol'] == pytest.approx(6.006, abs=1e-3) and rp.wallet_share(plan, C)['sol'] == pytest.approx(1.0, abs=0.01)


def test_pct_mode_rejects_over_100(monkeypatch, tmp_path):
    pytest.importorskip('solders')
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, 'BADGE_POOLS_PATH', tmp_path / 'p.json')
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'Admin')
    with pytest.raises(rs.HTTPException):
        asyncio.run(rs.admin_badge_pool_save(None, rs.BadgePoolIn(name='Big', wallet=D, pct=50, weights={'badge:a': 60, 'badge:b': 50})))


def test_route_split_never_overspends():
    rows = rp.route_split(1.0, [{'address': A, 'pct': 33.333}, {'address': B, 'pct': 33.333}, {'address': C, 'pct': 33.334}], 6)
    assert sum(r['amount'] for r in rows) <= 1.0 and rows[0]['amount'] == 0.33333


def test_parsed_transfers_only_what_the_signer_moved():
    tx = {'transaction': {'message': {'instructions': [
        {'program': 'system', 'parsed': {'type': 'transfer', 'info': {'source': D, 'destination': A, 'lamports': 5 * 10**8}}},
        {'program': 'system', 'parsed': {'type': 'transfer', 'info': {'source': B, 'destination': D, 'lamports': 10**9}}}]}},
          'meta': {'innerInstructions': [{'instructions': [{'program': 'spl-token', 'parsed': {'type': 'transferChecked', 'info': {
              'authority': D, 'destination': 'Ata1', 'mint': 'USDC', 'tokenAmount': {'uiAmount': 12.5}}}}]}]}}
    assert rp.parsed_transfers(tx, D) == [{'asset': 'SOL', 'to': A, 'amount': 0.5}, {'asset': 'USDC', 'to': 'Ata1', 'amount': 12.5}]
