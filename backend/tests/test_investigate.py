"""Investigation engine: every score point is cited evidence; FEELESS is never a suspect."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import investigate as inv  # noqa: E402


def test_serial_rugger_with_snipe_record_is_high_risk_with_cited_evidence():
    ev = inv.wallet_evidence({'blocked': {'reported': True, 'mints': {'m1': 'sniper', 'm2': 'sniper'}},
                              'creator': {'ruggedCount': 2, 'dumpedCount': 1, 'launchBurst24h': 4}})
    v = inv.verdict(ev)
    assert v['level'] == 'high' and v['score'] == 100
    kinds = {e['kind'] for e in ev}
    assert {'blocklist', 'sniper', 'rugs', 'dumps', 'farm'} <= kinds
    assert all(e['source'] and e['claim'] for e in ev)


def test_clean_wallet_and_track_record_lower_the_score():
    assert inv.verdict(inv.wallet_evidence({}))['level'] == 'clean'
    ev = inv.wallet_evidence({'creator': {'dumpedCount': 1, 'bigWinners': 2}})
    assert inv.verdict(ev)['score'] == 0  # 10 for the dump, −20 for two live winners, floored at 0


def test_feeless_wallets_are_never_suspects():
    ev = inv.wallet_evidence({'blocked': {'reported': True}})
    assert inv.verdict(ev, protected=True)['level'] == 'feeless'


def test_funding_clusters_group_holders_by_shared_funder():
    holders = [{'owner': 'A', 'pct': 5}, {'owner': 'B', 'pct': 4}, {'owner': 'C', 'pct': 3}, {'owner': 'D', 'pct': 2}]
    out = inv.clusters(holders, {'A': 'F1', 'B': 'F1', 'C': 'F2', 'D': 'C'})
    assert out['clusters'][0] == {'funder': 'F1', 'wallets': ['A', 'B'], 'pct': 9}
    assert {'funder': 'C', 'wallets': ['C', 'D'], 'pct': 5} in out['clusters']  # C funded D and holds too
    assert out['linkedPct'] == 14


def test_coin_risk_freeze_authority_alone_is_serious():
    r = inv.coin_risk({}, {'freezeAuthority': 'X'})
    assert r['score'] == 40 and r['level'] == 'caution'
    r = inv.coin_risk({'devHoldingPct': 25, 'top10Pct': 55}, {'freezeAuthority': 'X', 'mintAuthority': 'Y'})
    assert r['level'] == 'danger' and r['evidence'][0]['kind'] == 'freeze'
    assert inv.coin_risk({}, {})['level'] == 'ok'


def test_wallet_case_wiring(monkeypatch, tmp_path):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, 'FUNDERS_PATH', tmp_path / 'f.json')
    (tmp_path / 'f.json').write_text('{"funders": {"Boss": {"mints": {"m1": 1, "m2": 1}, "funded": ["W1", "W2", "W3"]}}, "offenderFunder": {"Sus1": "Boss"}}')
    monkeypatch.setattr(rs, 'BLOCK_PATH', tmp_path / 'b.json')
    (tmp_path / 'b.json').write_text('{"wallets": {"Sus1": {"mints": {"m1": "sniper"}}}}')

    async def none(*a, **k):
        return None
    monkeypatch.setattr(rs, 'resolve_funding_source', none)
    monkeypatch.setattr(rs, '_kol_stats', none)
    monkeypatch.setattr(rs, '_load', lambda: {'creators': {}, 'funding': {}})
    case = asyncio.run(rs._wallet_case('Sus1'))
    assert case['kind'] == 'wallet' and case['trail']['fundedBy'] == 'Boss'
    assert {e['kind'] for e in case['evidence']} == {'sniper', 'funded-by'} and case['level'] in ('watch', 'suspect')
    boss = asyncio.run(rs._wallet_case('Boss'))
    assert boss['trail']['fundedWallets'] == ['W1', 'W2', 'W3'] and boss['evidence'][0]['kind'] == 'funder'
