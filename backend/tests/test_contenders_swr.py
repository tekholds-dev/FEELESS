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


def test_arena_stage_is_served_from_disk_on_the_first_call_after_a_restart(monkeypatch):
    import reputation_service as rs
    import launchpad_board as lb
    now = time.time()
    lb.save_board_snapshot(rs.ARENA_SNAPSHOT_PATH, 'mega', [{'id': 'card-1'}], {}, now - 120)
    built = []

    async def run():
        rs._arena_mega_cache.clear(); rs._arena_mega_cache.update(at=0.0, data=None, boot=True)
        monkeypatch.setattr(rs, '_fuse_view', lambda *a, **k: built.append(1))
        got = await rs._arena_mega({'rounds': [], 'paths': {}}, {}, now)
        assert got == [{'id': 'card-1'}]                       # answered from disk at once (the stage took ≈ 13s cold)
        assert 'boot' not in rs._arena_mega_cache               # only the FIRST call after a restart reads the disk
        rs._arena_mega_cache.update(at=0.0, data=None)          # an admin change clears the stage on purpose …
        assert rs._launchpad_board.launchpad_board_snapshot(rs.ARENA_SNAPSHOT_PATH, 'mega', now) is not None
        assert rs._arena_mega_cache.get('boot') is None         # … and the old disk copy is never put back
    asyncio.run(run())
    rs._arena_mega_cache.clear(); rs._arena_mega_cache.update(at=0.0, data=None)


def test_contenders_league_is_served_from_disk_on_the_first_call_after_a_restart(monkeypatch):
    import reputation_service as rs
    import launchpad_board as lb
    lb.save_board_snapshot(rs.CONTENDERS_SNAPSHOT_PATH, 'league', {'divisions': [], 'all': [{'mint': 'M'}]}, {}, time.time() - 200)
    calls = []

    async def fake_rebuild():
        calls.append(1); return {'fresh': True}
    monkeypatch.setattr(rs, '_contenders_rebuild', fake_rebuild)

    async def run():
        rs._contenders_cache.clear(); rs._contenders_cache.update(at=0.0, data=None, boot=True)
        got = await rs._contenders_build()
        assert got['all'] == [{'mint': 'M'}]                    # the last league, at once
        await asyncio.sleep(0)
        assert calls                                             # … while a fresh one builds
    asyncio.run(run())
    rs._contenders_cache.clear(); rs._contenders_cache.update(at=0.0, data=None)
