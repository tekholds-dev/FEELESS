"""Coin verification: hard gates, cited scored checks, gold grants and revokes that always win."""
import asyncio
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify  # noqa: E402

GOOD = {'mintAuthority': None, 'freezeAuthority': None, 'creatorBlocked': False, 'creatorLevel': 'clean', 'ageHours': 100,
        'liquidityUsd': 80_000, 'marketCapUsd': 500_000, 'bundled': 0, 'snipers': 1, 'volume24h': 60_000, 'buyRatio': 0.55, 'socials': 3, 'lpLocked': True, 'top10Pct': 22, 'insidersPct': 4, 'devPct': 1}


def test_clean_coin_is_verified_with_every_check_cited():
    r = verify.verify_report(GOOD)
    assert r['level'] == 'verified' and r['score'] == 100 and all(c['source'] for c in r['checks'] + r['gates'])


def test_any_failed_gate_blocks_the_check_even_with_perfect_score():
    for bad in ({'freezeAuthority': 'Dev'}, {'mintAuthority': 'unknown'}, {'creatorLevel': 'suspect'}, {'ageHours': 5}, {'liquidityUsd': 9000}, {'top10Pct': 55}, {'insidersPct': 30}):
        r = verify.verify_report({**GOOD, **bad})
        assert r['level'] is None and r['reason'].startswith('Missing:')


def test_score_threshold_and_manual_overrides():
    weak = {**GOOD, 'lpLocked': False, 'top10Pct': 60, 'insidersPct': 30}
    assert verify.verify_report(weak)['level'] is None  # below 75
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


def test_coin_badges_are_earned_and_lost_the_same_way():
    r = verify.verify_report(GOOD)
    assert all(b['earned'] for b in r['badges'])
    rugged = verify.verify_report({**GOOD, 'lpLocked': False, 'freezeAuthority': 'Dev', 'volume24h': 0})
    lost = {e['id'] for e in verify.transitions({'level': r['level'], 'badges': [b['id'] for b in r['badges'] if b['earned']]}, rugged) if e['kind'] == 'lost'}
    assert lost == {'verified', 'renounced', 'lp-locked', 'real-vol'}
    back = verify.transitions({'level': None, 'badges': []}, r)
    assert {e['id'] for e in back if e['kind'] == 'earned'} >= {'verified', 'lp-locked'}
    assert verify.transitions({}, r) == []   # first sighting is not news


def test_granted_gold_is_suspended_while_a_critical_gate_fails_and_returns_after():
    g = {'state': 'granted'}
    assert verify.verify_report({**GOOD, 'mintAuthority': 'Dev'}, g)['level'] is None
    assert 'suspended' in verify.verify_report({**GOOD, 'liquidityUsd': 100}, g)['reason']
    assert verify.verify_report(GOOD, g)['level'] == 'gold'
    assert verify.verify_report({**GOOD, 'mintAuthority': 'Dev'}, None, official=True)['level'] == 'gold'


def test_service_records_earned_then_lost_history(monkeypatch, tmp_path):
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, 'VERIFY_PATH', tmp_path / 'v.json')
    facts = {'f': GOOD}
    async def fake(m): return facts['f'], {'symbol': 'X'}
    async def eco(): return {}
    monkeypatch.setattr(rs, '_verify_facts', fake); monkeypatch.setattr(rs, '_ecosystem_mints', eco)
    m = 'So11111111111111111111111111111111111111112'
    assert asyncio.run(rs._verify_run(m))['history'] == []
    facts['f'] = {**GOOD, 'lpLocked': False}
    h = asyncio.run(rs._verify_run(m))['history']
    assert [(e['kind'], e['id']) for e in h] == [('lost', 'lp-locked')]
    facts['f'] = GOOD
    assert asyncio.run(rs._verify_run(m))['history'][0]['kind'] == 'earned'
