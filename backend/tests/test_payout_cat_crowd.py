"""💸 Fuse payouts (owner-signed, verified on-chain, credited by what moved), 🐱 FeeCat weekly challenge, 🧠 crowd edge feed."""
import asyncio
import time

import pytest

import fuse_hq as hq

A, B, FEE = 'Aaaa1111111111111111111111111111111111111111', 'Bbbb2222222222222222222222222222222222222222', 'Fee1111111111111111111111111111111111111111'
SIG = '5' * 88


@pytest.fixture
def rs(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    async def none(): return None
    async def sol(): return 100.0
    async def shield(a): return {'verdict': 'bot' if a == 'BOT' else 'clean'}
    monkeypatch.setattr(rs, '_feecat_raw', none); monkeypatch.setattr(rs, '_feecat_card', none)
    monkeypatch.setattr(rs, '_sol_usd_live', sol); monkeypatch.setattr(rs, '_shield_of', shield)
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN'); monkeypatch.setattr(rs, '_protected_wallets', lambda: {FEE})
    monkeypatch.setattr(rs, 'notify', lambda *a, **k: None)
    return rs


def tx(transfers, signer=FEE, err=None):
    return {'meta': {'err': err}, 'transaction': {'message': {'accountKeys': [{'pubkey': signer, 'signer': True}],
            'instructions': [{'program': 'system', 'parsed': {'type': 'transfer', 'info': {'source': s, 'destination': d, 'lamports': int(l * 1e9)}}} for s, d, l in transfers]}}}


def test_payout_plan_then_verified_paid_record(rs, monkeypatch):
    async def book(): return {'rows': [{'wallet': A, 'owedUsd': 2.0}, {'wallet': 'BOT', 'owedUsd': 5.0}, {'wallet': FEE, 'owedUsd': 9.0}, {'wallet': B, 'owedUsd': 0.01}]}
    monkeypatch.setattr(rs, '_feeback_book', book)
    rs._json_save(rs.FUSE_HQ_PATH, {})
    plan = asyncio.run(rs.admin_fuse_payout_plan(None))
    assert [r['wallet'] for r in plan['rows']] == [A] and plan['rows'][0]['sol'] == 0.02 and plan['bots'] == 1
    async def rpc(http, method, params): return tx([(FEE, A, 0.02), (FEE, B, 0.5), (B, A, 9)])         # B→A not signed by B: ignored
    monkeypatch.setattr(rs, '_rpc', rpc)
    out = asyncio.run(rs.admin_fuse_payout_paid(None, rs.FusePaidIn(planId=plan['id'], sigs=[SIG])))
    assert out == {'ok': True, 'paidUsd': 2.0, 'wallets': 1}
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    assert d['feebackPaid'] == {A: 2.0} and d['payouts'][0]['sigs'] == [SIG] and 'payoutPlan' not in d
    with pytest.raises(rs.HTTPException):                                                          # plan consumed / sig reused
        asyncio.run(rs.admin_fuse_payout_paid(None, rs.FusePaidIn(planId=plan['id'], sigs=[SIG])))


def test_failed_or_unrelated_transactions_are_refused(rs, monkeypatch):
    async def book(): return {'rows': [{'wallet': A, 'owedUsd': 2.0}]}
    monkeypatch.setattr(rs, '_feeback_book', book)
    rs._json_save(rs.FUSE_HQ_PATH, {})
    plan = asyncio.run(rs.admin_fuse_payout_plan(None))
    async def failed(http, m, p): return tx([(FEE, A, 0.02)], err={'x': 1})
    monkeypatch.setattr(rs, '_rpc', failed)
    with pytest.raises(rs.HTTPException, match='failed'):
        asyncio.run(rs.admin_fuse_payout_paid(None, rs.FusePaidIn(planId=plan['id'], sigs=[SIG])))
    async def elsewhere(http, m, p): return tx([(FEE, B, 0.02)])
    monkeypatch.setattr(rs, '_rpc', elsewhere)
    with pytest.raises(rs.HTTPException, match='None of those'):
        asyncio.run(rs.admin_fuse_payout_paid(None, rs.FusePaidIn(planId=plan['id'], sigs=[SIG])))


def test_cards_that_beat_feecat_last_week_are_recorded_and_scored(rs, monkeypatch):
    now = time.time(); start = hq.season_start(now); prev = start - hq.WEEK
    async def cat(): return {'exits': [{'exitAt': prev + 100, 'changeAtExit': 10}], 'positions': []}
    async def px(legs): return {'P1': 3.0}
    async def book(): return {'rows': []}
    monkeypatch.setattr(rs, '_feecat_raw', cat); monkeypatch.setattr(rs, '_hq_prices', px); monkeypatch.setattr(rs, '_feeback_book', book)
    rs._json_save(rs.FUSE_HQ_PATH, {'positions': [{'id': 'win', 'wallet': A, 'at': prev + 60, 'legs': [{'pairAddress': 'P1', 'usd': 100, 'tokens': 50}]},     # +50%
                                                  {'id': 'lose', 'wallet': B, 'at': prev + 90, 'legs': [{'pairAddress': 'P1', 'usd': 100, 'tokens': 35}]}]})  # +5%
    asyncio.run(rs._fuse_season_tick(now))
    cc = rs._json_load(rs.FUSE_HQ_PATH, {})['catChallenge'][-1]
    assert cc['catPct'] == 10 and cc['ids'] == ['win']
    s = asyncio.run(rs._fuse_score(A, fresh=True))
    assert any('Beat FeeCat 1×' in p['label'] for p in s['parts'])


def test_crowd_feed_exposes_counts_not_wallets(rs, monkeypatch):
    now = time.time()
    old = [{'side': 'buy', 'token': f'T{i}', 'fillPrice': 1, 'usd': 10, 'tokens': 10, 'ts': now - 2 * 86400} for i in range(6)]
    fresh = [{'side': 'buy', 'token': 'HOT', 'fillPrice': 1, 'usd': 25, 'tokens': 25, 'ts': now - 600}]
    rs._json_save(rs.FEELESS_TRADES_PATH, {A: old + fresh, B: old[:2]})
    async def prices(toks): return {**{f'T{i}': 1.5 for i in range(6)}, 'HOT': 1}
    monkeypatch.setattr(rs, '_token_prices', prices)
    out = asyncio.run(rs._crowd_build())
    assert out['elites'] == 1 and out['flow'] == {'HOT': {'n': 1, 'usd': 25.0}} and A not in str(out)
