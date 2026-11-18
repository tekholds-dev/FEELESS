"""🎬 PoC creator flow · the SPOT step: viral video clips from Bluesky's what's-hot feed. Network faked."""
import asyncio

import proof_tools as t


def _post(handle, n, likes=10, video=True, text='words', langs=None):
    e = {'$type': 'app.bsky.embed.video#view', 'thumbnail': f'https://v/{n}.jpg', 'playlist': f'https://v/{n}.m3u8'} if video else {'$type': 'app.bsky.embed.images#view'}
    return {'post': {'uri': f'at://did:x/app.bsky.feed.post/rk{n}', 'author': {'handle': handle}, 'likeCount': likes, 'repostCount': 2,
                     'embed': e, 'record': {'text': text, **({'langs': langs} if langs else {})}}}


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
    assert rows[0] == {'src': 'bluesky', 'text': 'words', 'by': 'a.bsky', 'likes': 10, 'reposts': 2, 'thumb': 'https://v/1.jpg',
                       'video': 'https://v/1.m3u8', 'url': 'https://bsky.app/profile/a.bsky/post/rk1'}


def test_viral_keeps_english_or_untagged_posts_only(monkeypatch):
    _fake_feed(monkeypatch, [_post('es.bsky', 1, langs=['es']), _post('pt.bsky', 2, langs=['pt']), _post('en.bsky', 3, langs=['en-US']), _post('mix.bsky', 4, langs=['pt', 'en']), _post('none.bsky', 5)])
    assert [r['by'] for r in asyncio.run(t.viral(None))] == ['en.bsky', 'mix.bsky', 'none.bsky']


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


def _yt_fake(monkeypatch, answers):
    t._cache.clear(); asked = []
    async def fake(http, url, **kw):
        asked.append((url, kw.get('params') or {}))
        for k, v in answers.items():
            if k in url:
                return v
        return None
    monkeypatch.setattr(t, '_get', fake)
    return asked


def test_youtube_with_a_key_reads_the_24h_most_viewed_and_drops_live(monkeypatch):
    monkeypatch.setenv('YOUTUBE_API_KEY', 'k')
    vid = lambda i, views, live='none': {'id': i * 11 if len(i) == 1 else i, 'snippet': {'title': f't{i}', 'channelTitle': 'ch', 'liveBroadcastContent': live, 'thumbnails': {'high': {'url': f'https://i/{i}.jpg'}}}, 'statistics': {'viewCount': str(views), 'likeCount': '7'}}
    asked = _yt_fake(monkeypatch, {'youtube/v3/search': {'items': [{'id': {'videoId': 'aaaaaaaaaaa'}}, {'id': {'videoId': 'bbbbbbbbbbb'}}, {'id': {'videoId': 'ccccccccccc'}}]},
                                   'youtube/v3/videos': {'items': [vid('a', 100), vid('b', 900), vid('c', 5000, 'live')]}})
    rows = asyncio.run(t.yt_trending(None))
    assert [r['url'][-11:] for r in rows] == ['bbbbbbbbbbb', 'aaaaaaaaaaa'] and rows[0] == {'src': 'youtube', 'text': 'tb', 'by': 'ch', 'views': 900, 'likes': 7, 'thumb': 'https://i/b.jpg', 'video': None, 'url': 'https://www.youtube.com/watch?v=bbbbbbbbbbb'}
    s = asked[0][1]
    assert s['order'] == 'viewCount' and s['type'] == 'video' and s['publishedAfter'].endswith('Z') and s['key'] == 'k'


def test_youtube_without_a_key_uses_the_mirror_and_skips_live_streams(monkeypatch):
    monkeypatch.delenv('YOUTUBE_API_KEY', raising=False)
    _yt_fake(monkeypatch, {'piped': [{'url': '/watch?v=LIVELIVELIV', 'title': 'live', 'duration': -1, 'views': 9999, 'uploaderName': 'x'},
                                     {'url': '/watch?v=CLIPCLIPCLI', 'title': 'clip', 'duration': 621, 'views': 1534, 'uploaderName': 'y', 'thumbnail': 'https://t/1.jpg'}]})
    rows = asyncio.run(t.yt_trending(None))
    assert len(rows) == 1 and rows[0]['text'] == 'clip' and rows[0]['views'] == 1534 and rows[0]['likes'] is None


def test_trending_puts_youtube_first_and_says_where_it_came_from(monkeypatch):
    monkeypatch.delenv('YOUTUBE_API_KEY', raising=False)
    _yt_fake(monkeypatch, {'piped': [{'url': '/watch?v=CLIPCLIPCLI', 'title': 'clip', 'duration': 60, 'views': 5, 'uploaderName': 'y'}], 'getFeed': {'feed': [_post('a.bsky', 1)]}})
    d = asyncio.run(t.trending(None))
    assert [c.get('src', 'bluesky') for c in d['clips']] == ['youtube', 'bluesky']
    yt = [s for s in d['sources'] if s['name'] == 'YouTube'][0]
    assert yt['on'] and 'YOUTUBE_API_KEY' in yt['use']
