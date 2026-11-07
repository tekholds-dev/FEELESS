import asyncio

import reputation_service as rs

MINT = 'Bv1a7cEj5aRnJQhMw4kRQqAFesMSd5LwcDnUzq52BMmr'


class _R:
    def __init__(self, data=None, ctype='application/json', body=b''):
        self.status_code, self._d, self.headers, self.content = 200, data, {'content-type': ctype}, body

    def json(self):
        return self._d


class _Client:
    asked = []

    def __init__(self, **_k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def get(self, url, **_k):
        _Client.asked.append(url)
        if 'dexscreener' in url:
            return _R([{'info': {'imageUrl': 'https://cdn.example.com/a.jpg'}}])
        if 'cdn.example.com' in url:
            return _R(ctype='image/jpeg', body=b'\xff\xd8pic')
        await asyncio.sleep(60)   # a slow source, which used to run out the budget before any picture was fetched


def test_a_coin_with_a_logo_answers_from_the_first_source_that_has_one(monkeypatch):
    async def _no_rpc(*_a, **_k):
        await asyncio.sleep(60)
    monkeypatch.setattr(rs.httpx, 'AsyncClient', _Client)
    monkeypatch.setattr(rs, '_rpc', _no_rpc)
    _Client.asked = []
    r = asyncio.run(rs.token_logo(MINT))
    assert r.status_code == 200 and r.body == b'\xff\xd8pic'
    assert not any('jup.ag' in u for u in _Client.asked)   # nothing slower was waited on
