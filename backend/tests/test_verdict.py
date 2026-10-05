"""🧾 What's working / what's not: one verdict over every engine's own record."""
import verdict as v


def test_judge_needs_samples_and_both_average_and_median():
    assert v.judge(2, 9, 9, 5)[0] == 'watch'                    # too few to call
    assert v.judge(10, 4, 1.5, 5)[0] == 'keep'
    assert v.judge(10, -3, -1, 5)[0] == 'scrap'
    assert v.judge(10, 12, -2, 5)[0] == 'watch'                 # one moonshot lifts the average, the typical run still loses


def test_build_ranks_losers_first_and_says_nothing_is_proven_when_nothing_wins():
    out = v.build(tiers={'degen': {'label': '🔥 Prime Blaze', 'pcts': [-8, -3, -12, 2, -5, -6]}},
                  strategies=[{'style': 'dip', 'runs': 4, 'avgPct': -2.0, 'medPct': -1.0, 'winRate': 25}],
                  lanes={'scalp': {'n': 3, 'avgPct': 5, 'winRate': 66}},
                  sim_score={'clock': {'5': {'n': 60, 'medPct': -4.0, 'avgPct': -2.0, 'upPct': 30.0}}},
                  real=[{'label': '🔥 Prime Blaze', 'pnlPct': -12.5, 'feesPct': 4.2, 'perHour': 9, 'swaps': 120, 'holdSolPct': 1.0}])
    assert out['keep'] == 0 and out['rows'][0]['verdict'] == 'scrap' and 'Nothing is proven' in out['headline']
    names = {(r['area'], r['name']): r['verdict'] for r in out['rows']}
    assert names[('🏃 Runner lane', 'scalp')] == 'watch'                              # 3 rounds isn't proof
    assert names[('🧠 Sim config', 'round length (min) = 5')] == 'scrap'
    real = next(r for r in out['rows'] if r['area'] == '💵 Real run')
    assert real['verdict'] == 'scrap' and 'fees 4.2%' in real['why'] and 'SOL did +1.0%' in real['why']


def test_build_names_the_strongest_working_thing():
    out = v.build(tiers={'safe': {'label': '💎 Prime Diamond', 'pcts': [3, 5, 2, 8, 1]}}, clocks={'60': {'bells': 6, 'avgPct': 1.2}, '5': {'bells': 9, 'avgPct': -0.8}})
    assert out['keep'] == 2 and out['scrap'] == 1 and 'Prime Diamond' in out['headline']


def test_verdict_endpoint_reads_the_records_without_touching_anything(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER')
    rs._store.Ledger(rs.CARD_RECORDS_PATH, table='runs').append({'card': 'safe', 'pct': 4.0, 'at': 1.0, 'real': False})
    rs._json_save(rs.PG_SIM_PATH, {'score': {'clock': {'60': {'n': 40, 'medPct': 1.0, 'avgPct': 2.0, 'upPct': 60.0}}}})
    out = asyncio.run(rs.fuse_verdict(None))
    by = {(r['area'], r['name']): r for r in out['rows']}
    assert by[('⭐ Tier card', '💎 Prime Diamond')]['n'] == 1 and by[('🧠 Sim config', 'round length (min) = 60')]['verdict'] == 'keep'
