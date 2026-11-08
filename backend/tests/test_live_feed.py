"""📡 Real numbers for any proof: read by the server (its own Helius key when saved), never by the page. Network faked."""
import asyncio

import agent_features as af
import feecat_service as fs


def test_live_words_and_line():
    assert af.wants_live('a live SOL desk') and af.wants_live('show my wallet balance') and not af.wants_live('a quiz about space')
    line = af.live_line({'solUsd': 89.25, 'slot': 5, 'source': 'its own Helius key', 'at': 1, 'secret': 'x'}, page=True)
    assert '89.25' in line and 'feeless-live' in line and 'secret' not in line and 'never fetch' in line
    assert af.live_line({}) == ''


def test_feed_uses_its_own_helius_key_and_never_returns_it(monkeypatch):
    calls = []

    class R:
        def __init__(self, j, code=200): self._j, self.status_code = j, code
        def json(self): return self._j

    class H:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None):
            calls.append(url)
            return R({'result': 123 if json['method'] == 'getSlot' else [{'numTransactions': 600, 'samplePeriodSecs': 60}]})
        async def get(self, url, timeout=None):
            return R({'pairs': [{'priceUsd': '90.5', 'priceChange': {'h24': 1.5}}]})

    monkeypatch.setattr(fs.httpx, 'AsyncClient', H)
    monkeypatch.setattr(fs._ck, 'key_for', lambda cat, p, data_dir=None: 'KEY123' if p == 'helius' else None)
    fs._LIVE.clear()
    feed = asyncio.run(fs._live_feed({'id': 'c1'}))
    assert feed['solUsd'] == 90.5 and feed['slot'] == 123 and feed['tps'] == 10 and feed['source'] == 'its own Helius key'
    assert calls and all('helius-rpc.com' in u for u in calls) and 'KEY123' not in str(feed)
