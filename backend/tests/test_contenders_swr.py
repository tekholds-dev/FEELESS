import asyncio
import time


def test_contenders_answers_from_its_last_copy_and_rebuilds_in_the_background(monkeypatch):
    import reputation_service as rs
    calls = []

    async def fake_rebuild():
        calls.append(1)
        rs._contenders_cache.update(at=time.time(), data={'v': 'fresh'})
        return rs._contenders_cache['data']

    monkeypatch.setattr(rs, '_contenders_rebuild', fake_rebuild)

    async def run():
        rs._contenders_cache.update(at=time.time() - 100, data={'v': 'old'})
        got = await rs._contenders_build()                 # stale but ≤ 10 min: answered at once …
        assert got == {'v': 'old'}
        await asyncio.sleep(0)                             # … and one background rebuild ran
        await asyncio.sleep(0)
        assert calls and rs._contenders_cache['data'] == {'v': 'fresh'}
        rs._contenders_cache.update(at=0.0, data=None)     # cold start: the caller waits for the build
        assert await rs._contenders_build() == {'v': 'fresh'}
        rs._contenders_cache.update(at=time.time() - 100, data={'v': 'old'})
        assert await rs._contenders_build(fresh=True) == {'v': 'fresh'}   # the warm loop always rebuilds
    asyncio.run(run())
    rs._contenders_cache.update(at=0.0, data=None)
