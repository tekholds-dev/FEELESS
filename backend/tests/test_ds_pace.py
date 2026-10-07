"""📡 DexScreener pacing: requests wait for a slot instead of bursting, and a 429 pauses the host for its Retry-After."""
import asyncio

import ds_pace


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_bucket_paces_a_burst_and_a_429_pauses_everyone():
    c = Clock()
    b = ds_pace.Bucket(60, burst=3, clock=c)          # one a second, 3 at once
    assert [b.wait_for() for _ in range(3)] == [0.0, 0.0, 0.0]
    assert abs(b.wait_for() - 1.0) < 1e-9             # the 4th waits for the next slot
    c.t = 1.0
    assert b.wait_for() == 0.0
    b.cool(15)                                        # DexScreener said 429, retry after 15s
    c.t = 5.0
    assert abs(b.wait_for() - 11.0) < 1e-9
    c.t = 17.0
    assert b.wait_for() == 0.0 and b.limited == 1


def test_acquire_waits_but_never_longer_than_max_wait_and_slow_paths_have_their_own_bucket():
    c = Clock()
    ds_pace._BUCKETS.clear()
    ds_pace._BUCKETS['main'] = ds_pace.Bucket(60, burst=1, clock=c)
    ds_pace._BUCKETS['slow'] = ds_pace.Bucket(6, burst=1, clock=c)
    slept = []

    async def sleep(s):
        slept.append(s); c.t += s
    asyncio.run(ds_pace.acquire('/latest/dex/pairs/solana/x', sleep))
    asyncio.run(ds_pace.acquire('/token-boosts/top/v1', sleep))      # its own bucket: no wait
    assert slept == []
    asyncio.run(ds_pace.acquire('/tokens/v1/solana/a', sleep))
    assert abs(sum(slept) - 1.0) < 1e-9                               # waited for the main slot
    ds_pace._BUCKETS['main'].cool(60)
    slept.clear(); asyncio.run(ds_pace.acquire('/tokens/v1/solana/b', sleep))
    assert abs(sum(slept) - ds_pace.MAX_WAIT) < 1e-9                  # never stuck past MAX_WAIT


def test_both_services_install_their_share_under_the_ip_limit():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    assert 'ds_pace.install(110, 20)' in (root / 'reputation_service.py').read_text()
    assert 'ds_pace.install(150, 30)' in (root / 'server.py').read_text()
    assert 110 + 150 < 300
