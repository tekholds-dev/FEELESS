"""🔑 the keeper keeps its keys; price reads get the last key once there are three (jup_keys)."""
import jup_keys as jk


def test_three_keys_set_one_aside_for_reads():
    env = {'JUPITER_API_KEY': 'a' * 20, 'JUPITER_API_KEY_2': 'b' * 20, 'JUPITER_API_KEY_3': 'c' * 20}
    assert jk.read_key(env) == 'c' * 20 and jk.keeper_keys(env) == ['a' * 20, 'b' * 20]


def test_fewer_keys_stay_the_keepers_and_reads_go_public():
    env = {'JUPITER_API_KEY': 'a' * 20, 'JUPITER_API_KEY_2': 'b' * 20, 'JUPITER_API_KEY_3': 'a' * 20}   # a repeat is one key
    assert jk.read_key(env) is None and jk.keeper_keys(env) == ['a' * 20, 'b' * 20]
    assert jk.read_key({'JUPITER_API_KEY': 'a' * 20, 'JUPITER_READ_KEY': 'r' * 20}) == 'r' * 20


def test_candles_reads_never_use_the_keepers_key():
    src = open(__file__.replace('tests/test_jup_keys.py', 'candles_service.py')).read()
    i = src.index('async def _px_fetch(')
    assert "os.environ.get('JUPITER_API_KEY'" not in src[i:i + 2500] and '_jk.read_key(os.environ)' in src[i:i + 2500]


def test_a_60_coin_price_read_is_one_batch_not_eight():
    """8 at a time fed the batcher 8 coins a window: 60 coins took 5–7s, the graders' 3s read got nothing and coins were filed as vanished."""
    import asyncio
    import candles_service as cs
    calls = []

    async def fake(mints):
        calls.append(list(mints))
        return {m: 1.0 for m in mints}

    async def run():
        old, cs._px_fetch = cs._px_fetch, fake
        cs._px_cache.clear(); cs._px_q.clear(); cs._px_loop['task'] = None
        try:
            ms = ['M' + 'abcdefghij'[i // 10] + 'abcdefghij'[i % 10] + 'x' * 40 for i in range(60)]
            got = await cs.live_prices(','.join(ms))
            return ms, got
        finally:
            cs._px_fetch = old
            if cs._px_loop['task']:
                cs._px_loop['task'].cancel()
    ms, got = asyncio.run(run())
    assert len(got) == 60 and len(calls) == 2 and len(calls[0]) == 50


def test_a_refused_price_lane_rests_instead_of_being_asked_every_half_second():
    import candles_service as cs
    assert cs.px_rest_sec('3') == 3.0 and cs.px_rest_sec(None) == cs.PX_REST_SEC and cs.px_rest_sec('900') == cs.PX_REST_SEC and cs.px_rest_sec('x') == cs.PX_REST_SEC
    src = open(cs.__file__).read()
    i = src.index('async def _px_fetch(')
    assert '_px_rest.get(url, 0)' in src[i:i + 1500] and 'r.status_code == 429' in src[i:i + 1500]
