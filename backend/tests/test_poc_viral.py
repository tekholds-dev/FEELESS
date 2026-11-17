"""🎬 PoC creator flow · the SPOT step: viral video clips from Bluesky's what's-hot feed. Network faked."""
import asyncio

import proof_tools as t


def _post(handle, n, likes=10, video=True, text='words'):
    e = {'$type': 'app.bsky.embed.video#view', 'thumbnail': f'https://v/{n}.jpg', 'playlist': f'https://v/{n}.m3u8'} if video else {'$type': 'app.bsky.embed.images#view'}
    return {'post': {'uri': f'at://did:x/app.bsky.feed.post/rk{n}', 'author': {'handle': handle}, 'likeCount': likes, 'repostCount': 2,
                     'embed': e, 'record': {'text': text}}}


def _fake_feed(monkeypatch, feed):
    t._cache.clear()
    async def fake(http, url, **kw):
        return {'feed': feed} if 'getFeed' in url else None
    monkeypatch.setattr(t, '_get', fake)


def test_viral_keeps_only_videos_one_per_author_capped_at_five(monkeypatch):
    feed = [_post('a.bsky', 1), _post('a.bsky', 2), _post('b.bsky', 3, video=False)] + [_post(f'c{i}.bsky', 10 + i) for i in range(6)]
    _fake_feed(monkeypatch, feed)
    rows = asyncio.run(t.viral(None))
    assert len(rows) == 5 and [r['by'] for r in rows] == ['a.bsky', 'c0.bsky', 'c1.bsky', 'c2.bsky', 'c3.bsky']
    assert rows[0] == {'text': 'words', 'by': 'a.bsky', 'likes': 10, 'reposts': 2, 'thumb': 'https://v/1.jpg',
                       'video': 'https://v/1.m3u8', 'url': 'https://bsky.app/profile/a.bsky/post/rk1'}


def test_viral_source_down_gives_an_empty_list(monkeypatch):
    t._cache.clear()
    async def fake(http, url, **kw):
        return None
    monkeypatch.setattr(t, '_get', fake)
    assert asyncio.run(t.viral(None)) == []


def test_trending_carries_the_clips_and_names_the_source(monkeypatch):
    _fake_feed(monkeypatch, [_post('a.bsky', 1)])
    d = asyncio.run(t.trending(None))
    assert d['kind'] == 'content' and len(d['clips']) == 1
    row = [s for s in d['sources'] if s['name'] == 'Bluesky video'][0]
    assert row == {'name': 'Bluesky video', 'use': 'Viral clips', 'on': True}
