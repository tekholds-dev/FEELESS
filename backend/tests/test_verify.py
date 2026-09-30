"""Coin verification: hard gates, cited scored checks, gold grants and revokes that always win."""
import asyncio
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify  # noqa: E402

GOOD = {'mintAuthority': None, 'freezeAuthority': None, 'creatorBlocked': False, 'creatorLevel': 'clean', 'ageHours': 100,
        'liquidityUsd': 80_000, 'volume24h': 60_000, 'buyRatio': 0.55, 'socials': 3, 'lpLocked': True, 'top10Pct': 22, 'insidersPct': 4, 'devPct': 1}


def test_clean_coin_is_verified_with_every_check_cited():
    r = verify.verify_report(GOOD)
    assert r['level'] == 'verified' and r['score'] == 100 and all(c['source'] for c in r['checks'] + r['gates'])


def test_any_failed_gate_blocks_the_check_even_with_perfect_score():
    for bad in ({'freezeAuthority': 'Dev'}, {'mintAuthority': 'unknown'}, {'creatorLevel': 'suspect'}, {'ageHours': 5}, {'liquidityUsd': 9000}):
        r = verify.verify_report({**GOOD, **bad})
        assert r['level'] is None and r['reason'].startswith('Missing:')


def test_score_threshold_and_manual_overrides():
    weak = {**GOOD, 'lpLocked': False, 'top10Pct': 60, 'insidersPct': 30}
    assert verify.verify_report(weak)['level'] is None  # 50/100
    assert verify.verify_report(weak, {'state': 'granted'})['level'] == 'gold'
    assert verify.verify_report(GOOD, {'state': 'revoked', 'note': 'Team dumped'})['level'] == 'revoked'
    assert verify.verify_report({**GOOD, 'freezeAuthority': 'x'}, official=True)['level'] == 'gold'


def test_batch_reflects_revoke_immediately_and_schedules_missing(monkeypatch, tmp_path):
    pytest.importorskip('solders')
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, 'VERIFY_PATH', tmp_path / 'v.json')
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'Admin')
    monkeypatch.setattr(rs, '_admin_load', lambda: {'audit': []}); monkeypatch.setattr(rs, '_audit', lambda *a: None); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    m = 'M' * 43
    rs._verify_cache[m] = (time.time(), {'level': 'verified', 'score': 90})
    assert asyncio.run(rs.verify_batch(m))['verify'][m]['level'] == 'verified'
    asyncio.run(rs.verify_admin(None, rs.VerifyAdminIn(mint=m, action='revoke', note='rug')))
    assert asyncio.run(rs.verify_batch(m))['verify'][m]['level'] == 'revoked'
    asyncio.run(rs.verify_admin(None, rs.VerifyAdminIn(mint=m, action='grant')))
    assert asyncio.run(rs.verify_batch(m))['verify'][m]['level'] == 'gold'
