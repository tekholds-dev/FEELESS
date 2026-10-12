"""Coin edge: one record per coin; signals cite their source; warnings flagged; no field invented when a cache is empty."""
import coin_edge as ce


def test_empty_caches_give_an_honest_empty_record():
    e = ce.compose('M')
    assert e == {'mint': 'M', 'pulse': None, 'snipersOut': None, 'verify': None, 'intel': None, 'runner': None, 'sources': [], 'elite': None, 'signals': []}


def test_signals_cite_sources_and_warnings():
    e = ce.compose('M', pulse={'m5Change': 4}, sniper={'text': 'All 3 snipers sold out'}, verify={'level': 'verified'},
                   intel={'creator': 'C', 'top10Pct': 18, 'topHolders': [{'owner': str(i)} for i in range(15)], 'secret': 1},
                   runner={'score': 80, 'lane': 'scalp', 'gates': [], 'bondTier': '🔔 Bond run', 'curve': 92.4, 'bond': [{'label': 'curve ≥90%', 'ok': True}]},
                   sources=[{'kind': 'arena', 'label': '🏟 arena pick'}], elite={'n': 3, 'usd': 410})
    kinds = [s['kind'] for s in e['signals']]
    assert kinds == ['snipers-out', 'bond', 'elite', 'fuse', 'verified'] and all(s['source'] for s in e['signals'])
    assert len(e['intel']['topHolders']) == 10 and 'secret' not in e['intel'] and e['runner']['passing'] and e['runner']['bond'][0]['ok']
    bad = ce.compose('M', runner={'gates': ['Top 10 under 30%', 'Dev holds under 10%']}, verify={'level': 'revoked'})
    assert [s['kind'] for s in bad['signals']] == ['gate', 'revoked'] and all(s.get('warn') for s in bad['signals']) and '(+1)' in bad['signals'][0]['text']


def test_edge_endpoint_reads_caches_in_one_call(monkeypatch):
    import asyncio
    import time
    import pytest
    rs = pytest.importorskip('reputation_service')
    M = 'So11111111111111111111111111111111111111112'
    async def pulses(ms): return {m: {'m5Change': 5.0} for m in ms}
    async def vb(mints): return {'verify': {M: {'level': 'verified', 'score': 90}}}
    monkeypatch.setattr(rs, '_edge_pulses', pulses); monkeypatch.setattr(rs, 'verify_batch', vb)
    rs._edge_cache.clear()
    rs._radar['events'].insert(0, {'kind': 'snipers-out', 'pair': 'P', 'mint': M, 'text': 'All snipers sold out', 'at': time.time()})
    rs._runner_live_cache.update(at=time.time(), data={'passing': [{'mint': M, 'score': 81, 'lane': 'scalp', 'gates': [], 'bond': [], 'curve': 70}], 'dropped': []})
    e = asyncio.run(rs.coin_edge(mints=f'{M},bad,{M}'))['edge']
    assert list(e) == [M] and e[M]['pulse']['m5Change'] == 5 and e[M]['snipersOut'] and e[M]['runner']['score'] == 81
    assert [s['kind'] for s in e[M]['signals']] == ['snipers-out', 'verified']


def test_edge_never_waits_on_a_slow_read_and_never_clears_the_ranking_cache(monkeypatch):
    """⚡ A coin with a record answers at once (refreshed in the background); a cold coin waits ≤ the budget and its incomplete record
    refills soon; the coin cache and the 🧬 ranking cache are different objects (one name once made a clear() crash the ranking)."""
    import asyncio
    import time
    import pytest
    rs = pytest.importorskip('reputation_service')
    assert rs._edge_cache is not rs._edge_rank_cache and 'rows' in rs._edge_rank_cache
    M, N = 'So11111111111111111111111111111111111111112', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'

    async def slow(*a, **k):
        await asyncio.sleep(5)
        return {}
    monkeypatch.setattr(rs, '_edge_pulses', slow); monkeypatch.setattr(rs, 'verify_batch', slow)
    monkeypatch.setattr(rs, 'EDGE_COLD_BUDGET', 0.05)
    rs._edge_cache.clear(); rs._edge_inflight.clear()
    rs._edge_cache[M] = (time.time() - 60, {'mint': M, 'old': True})        # 60s old: stale but shown at once

    async def go():
        t0 = time.time()
        r = await rs.coin_edge(mints=f'{M},{N}')
        return r, time.time() - t0, set(rs._edge_inflight)
    r, took, infl = asyncio.run(go())
    assert took < 1.0 and r['edge'][M] == {'mint': M, 'old': True} and N in r['edge'] and M in infl
    assert time.time() - rs._edge_cache[N][0] >= 11                           # incomplete → refills on the next poll
