"""SITE-2 abuse cases, in process (no network, no live service): oversize bodies, a slowloris body, and a flooded endpoint that must not starve
the others. Every service mounts the same middleware (checked at the bottom)."""
import asyncio

import httpx
from fastapi import FastAPI, Request

import http_armor as ha


def _app(**kw):
    app = FastAPI(); gate = asyncio.Event()

    @app.post('/api/x/echo')
    async def echo(request: Request):
        return {'n': len(await request.body())}

    @app.get('/api/slow/hang')
    async def hang():
        await gate.wait(); return {'ok': True}

    @app.get('/api/fast/ping')
    async def ping():
        return {'ok': True}
    return ha.HttpArmor(app, **kw), gate


def _run(coro):
    return asyncio.run(coro)


def test_an_oversize_body_is_refused_before_the_route_reads_it():
    async def go():
        armored, _ = _app()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=armored, client=('8.8.8.8', 1)), base_url='http://t') as c:
            ok = await c.post('/api/x/echo', content=b'a' * 1000)
            big = await c.post('/api/x/echo', content=b'a' * (ha.MAX_BODY + 1))
            async def chunks():   # no Content-Length: counted as it arrives
                for _ in range(9):
                    yield b'a' * (1024 * 1024)
            streamed = await c.post('/api/x/echo', content=chunks())
        return ok, big, streamed
    ok, big, streamed = _run(go())
    assert ok.json() == {'n': 1000} and big.status_code == 413 and streamed.status_code == 413
    assert ha.cap_for('/api/cats/x/files', False) == ha.MAX_UPLOAD and ha.cap_for('/api/x', True) == ha.MAX_INTERNAL


def test_a_slowloris_body_gets_408():
    async def go():
        armored, _ = _app(chunk_s=0.2, body_s=0.5)
        async def slow():
            yield b'a'
            await asyncio.sleep(1.0)
            yield b'b'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=armored, client=('8.8.8.8', 1)), base_url='http://t') as c:
            return await c.post('/api/x/echo', content=slow())
    assert _run(go()).status_code == 408


def test_one_flooded_endpoint_never_starves_the_rest_and_internal_is_never_bulkheaded():
    async def go():
        armored, gate = _app(per_route=4, is_internal=lambda ip: ip == '127.0.0.1')
        out = {}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=armored, client=('8.8.8.8', 1)), base_url='http://t', timeout=5) as c:
            stuck = [asyncio.create_task(c.get('/api/slow/hang')) for _ in range(4)]
            await asyncio.sleep(0.1)
            out['over'] = await c.get('/api/slow/hang')
            out['other'] = await asyncio.gather(*[c.get('/api/fast/ping') for _ in range(20)])
            gate.set(); out['stuck'] = await asyncio.gather(*stuck)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=armored, client=('127.0.0.1', 1)), base_url='http://t') as c:
            out['internal'] = await c.post('/api/x/echo', content=b'a' * (ha.MAX_BODY + 1))
        out['busy'] = dict(armored.busy)
        return out
    o = _run(go())
    assert o['over'].status_code == 503 and o['over'].headers['retry-after'] == '2'
    assert all(r.status_code == 200 for r in o['other']) and all(r.status_code == 200 for r in o['stuck'])
    assert o['internal'].status_code == 200 and o['busy'] == {}    # lanes empty again


def test_every_service_mounts_the_armor():
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    for f in ('server.py', 'reputation_service.py', 'feecat_service.py', 'candles_service.py'):
        assert 'HttpArmor' in (root / f).read_text(), f


def test_a_clip_farm_video_streams_past_the_upload_cap_never_buffered_and_is_still_capped(monkeypatch):
    """✂ Slice 15: a 5-min video (up to 600 MB) flows through to the route chunk by chunk; past MAX_VIDEO the route hears the client left."""
    from starlette.requests import ClientDisconnect
    app = FastAPI(); seen = []

    @app.post('/api/cats/c1/clipfarm/upload')
    async def up(request: Request):
        n = 0
        try:
            async for ch in request.stream():
                n += len(ch); seen.append(len(ch))
        except ClientDisconnect:
            return {'cut': n}
        return {'n': n}
    armor = ha.HttpArmor(app)

    async def go(size, chunks=8):
        async def body():
            for _ in range(chunks):
                yield b'x' * (size // chunks)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=armor), base_url='http://t') as c:
            return await c.post('/api/cats/c1/clipfarm/upload', content=body())
    r = _run(go(48 * 1024 * 1024))   # over the 40 MB upload cap, under the video cap
    assert r.status_code == 200 and r.json() == {'n': 48 * 1024 * 1024} and len(seen) >= 8   # it arrived in pieces, not one buffered blob
    monkeypatch.setattr(ha, 'MAX_VIDEO', 4 * 1024 * 1024)
    assert ha.cap_for('/api/cats/c1/clipfarm/upload', True) == 4 * 1024 * 1024   # even our own services stay under the video cap
    r = _run(go(8 * 1024 * 1024))
    assert r.json()['cut'] <= 4 * 1024 * 1024
    async def declared():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=armor), base_url='http://t') as c:
            return await c.post('/api/cats/c1/clipfarm/upload', content=b'x' * (5 * 1024 * 1024))
    assert _run(declared()).status_code == 413
    assert ha.cap_for('/api/x/echo', False) == ha.MAX_BODY and not ha.is_stream('/api/cats/c1/media/upload')   # every other route is unchanged
