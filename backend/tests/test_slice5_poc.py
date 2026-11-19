"""🎬 Slice 5 (owner 2026-11-18): PoC is a content studio graded on real reach. Trend first → its minds write for the trend they pick → the free
local maker makes the real files (image, short video, post, thread) in story, feed and wide → nothing posts until the OWNER approves, then it
posts through the posting service he signed his accounts into (Upload-Post / Zernio / Ayrshare) → views and engagement are read back at 24 h
and 7 d and graded against the goal set at filing, with the cost per 1,000 views. Every network call and every mind is faked here."""
import asyncio
import json
import shutil

import pytest

import poc_post as pp
import poc_studio as ps

TREND = {'kind': 'content', 'trends': {'Bluesky': ['Moon landing', 'Solar storm'], 'Google News': ['Fed holds rates'], 'Hacker News': ['A new open model'], 'CoinGecko': ['$GLINT']},
         'clips': [{'src': 'bluesky', 'text': 'Cat walks on the moon set', 'by': 'a.bsky.social', 'likes': 900, 'reposts': 100, 'thumb': 'https://video.bsky.app/t.jpg', 'url': 'https://bsky.app/profile/a/post/1'},
                   {'src': 'youtube', 'text': 'Biggest wave ever surfed', 'by': 'Surf', 'views': 2_000_000, 'url': 'https://www.youtube.com/watch?v=abcdefghijk'}]}
PITCH = {'trend': 1, 'angle': 'Records only matter if you film them', 'hook': 'The wave nobody priced', 'sub': 'Two million people watched one wave today',
         'beats': ['Two million views', 'One wave', 'Your move'], 'post': {'story': 'One wave. Two million views.', 'feed': 'Two million people watched one wave today. Attention is the trade.', 'wide': 'Long version. ' * 5},
         'thread': ['1 a wave', '2 the views', '3 the lesson'], 'goal': {'type': 'reach', 'target': 5000, 'why': 'a small slice of a huge clip'}, 'why': 'it is everywhere today'}


# ── pure: trend first ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_trends_come_from_today_biggest_first_one_source_after_another_and_never_one_already_ridden():
    rows = ps.trend_rows(TREND)
    assert rows[0]['text'] == 'Biggest wave ever surfed' and rows[0]['signal'] == 2_000_000 and rows[0]['unit'] == 'views'   # the biggest clip leads
    assert [r['source'] for r in rows[:3]] == ['YouTube', 'Bluesky', 'Google News'] and [r['n'] for r in rows] == list(range(1, len(rows) + 1))
    assert rows[1]['url'].startswith('https://bsky.app/search?q=')
    again = ps.trend_rows(TREND, ridden=['Biggest wave ever surfed', 'Moon landing'])
    assert all(r['text'] not in ('Biggest wave ever surfed', 'Moon landing') for r in again)   # a new footprint every time
    assert ps.trend_rows({}) == []


def test_a_pitch_is_parsed_without_inventing_and_gaps_are_named():
    trends = ps.trend_rows(TREND)
    p = ps.parse('Sure! ' + json.dumps(PITCH), trends)
    assert p['trend']['text'] == 'Biggest wave ever surfed' and p['gaps'] == [] and p['post']['feed'].startswith('Two million')
    thin = ps.parse(json.dumps({'trend': '3', 'hook': 'Fed holds', 'post': 'one line'}), trends)
    assert thin['trend']['n'] == 3 and set(thin['gaps']) == {'beats', 'post', 'thread', 'goal'}
    assert ps.parse('no json at all', trends) is None
    assert ps.pick([thin, p]) == (1, p) and ps.pick([None, None]) == (None, None)   # the most complete pitch makes the files
    full = ps.fill(thin)
    assert set(full['post']) == {'story', 'feed', 'wide'} and len(full['beats']) >= 2 and full['thread'] and 'post.story' in full['filled']   # filled from its own words, and said


def test_a_local_minds_reply_is_read_through_its_thinking_fences_and_a_cut_off_end():
    trends = ps.trend_rows(TREND)
    assert ps.json_of('<think>maybe {no}</think>\n```json\n{"trend": 2, "hook": "x"}\n```') == {'trend': 2, 'hook': 'x'}
    assert ps.json_of('{"trend": 1, "hook": "Moon", "post": {"story": "ok", "fe') == {'trend': 1, 'hook': 'Moon', 'post': {'story': 'ok'}}
    assert ps.json_of('<think>still thinking and ran out of room') is None and ps.json_of('') is None
    p = ps.parse(json.dumps({**PITCH, 'trend': 'Solar storm hits'}), trends)   # the trend named by its words, not its number
    assert p['trend']['text'] == 'Solar storm' and ps.parse(json.dumps({**PITCH, 'trend': 'nothing alike'}), trends)['trend'] is None


def test_the_goal_is_the_minds_and_kept_sane_or_sized_from_the_trend_when_they_set_none():
    trends = ps.trend_rows(TREND)
    p = ps.parse(json.dumps(PITCH), trends)
    assert ps.goal(p, p['trend']) == {'type': 'reach', 'target': 5000, 'why': 'a small slice of a huge clip', 'by': 'minds', 'locked': False}
    g = ps.goal({'goal': {}}, trends[0])
    assert g['by'] == 'code' and g['target'] == 20_000 and g['type'] == 'reach'
    assert ps.goal({'goal': {'type': 'buzz', 'target': 10 ** 12}}, trends[0])['target'] == 10_000_000


# ── the real files ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg makes the clip')
def test_every_piece_is_made_as_a_real_file_in_story_feed_and_wide(tmp_path):
    from PIL import Image
    p = ps.fill(ps.parse(json.dumps(PITCH), ps.trend_rows(TREND)))
    kept = {}

    def save(piece, ext, raw):
        name = f'{piece}{len(kept)}.{ext}'; (tmp_path / name).write_bytes(raw); kept[name] = raw
        return f'/x/{name}'
    files = ps.make_files(p, p['trend'], save)
    assert ps.files_check(files) == (True, '12 of 12 files made: image, video, post and thread, each in story, feed and wide')
    for f in files:
        raw = (tmp_path / f['url'].rsplit('/', 1)[1]).read_bytes()
        if f['piece'] == 'image':
            assert Image.open(tmp_path / f['url'].rsplit('/', 1)[1]).size == ps.FORMATS[f['format']]
        if f['piece'] == 'video':
            assert raw[4:8] == b'ftyp' and f['bytes'] > 10_000
        if f['piece'] == 'thread':
            assert len(f['cards']) == 3 and f['text'].startswith('1/3 1 a wave')
        if f['piece'] == 'post':
            assert raw.decode() == p['post'][f['format']]
    assert ps.files_check(files[:-1])[0] is False and 'missing thread wide' in ps.files_check(files[:-1])[1]


# ── pure: reach, graded ───────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_metrics_read_any_service_naming_and_never_add_impressions_to_views():
    assert ps.metrics({'views': 5200, 'impressions': 9000, 'likes': 120, 'comments': 8, 'favorites': 3}) == {'views': 5200, 'likes': 123, 'comments': 8, 'shares': 0, 'saves': 0, 'clicks': 0}
    assert ps.metrics({'likeCount': 23, 'commentsCount': 1, 'sharesCount': 12, 'mediaView': 450})['views'] == 450
    bsky = ps.metrics({'likes': 4, 'reposts': 2, 'replies': 1, 'quotes': 1})
    assert bsky['views'] is None and bsky['shares'] == 3
    t = ps.total({'youtube': ps.metrics({'views': 900, 'likes': 10}), 'bluesky': bsky})
    assert t == {'views': 900, 'viewsFrom': ['youtube'], 'noViews': ['bluesky'], 'engagement': 18, 'clicks': 0}


def test_the_grade_is_real_reach_against_the_goal_set_at_filing_with_cost_per_thousand_views():
    g = {'type': 'reach', 'target': 1000}
    early = ps.grade(g, {'views': 400, 'engagement': 9}, 0.0, final=False)
    assert early['verdict'] == 'on pace' and early['pct'] == 40.0 and early['cpm'] == 0.0
    final = ps.grade(g, {'views': 2000, 'engagement': 50}, 0.5, final=True)
    assert final['verdict'] == 'hit' and final['cpm'] == 0.25 and final['why'] == '2,000 of 1,000 views'
    assert ps.grade(g, {'views': 10}, 0, True)['verdict'] == 'missed'
    none = ps.grade(g, {'views': None, 'noViews': ['bluesky'], 'engagement': 7}, 0, True)
    assert none['verdict'] == 'not given' and 'bluesky' in none['why'] and none['cpm'] is None   # never a guessed view count
    assert ps.grade({'type': 'buzz', 'target': 5}, {'views': None, 'engagement': 7}, 0, True)['verdict'] == 'hit'
    assert ps.cpm(1.0, 0) is None


def test_reads_fall_due_at_24_hours_and_7_days_after_it_posted():
    f = {'posted': {'at': 1000}}
    assert ps.due(f, 1000 + 3600) == [] and ps.due(f, 1000 + 86400) == ['h24'] and ps.due(f, 1000 + 8 * 86400) == ['h24', 'd7']
    f['reach'] = {'reads': [{'key': 'h24'}]}
    assert ps.due(f, 1000 + 8 * 86400) == ['d7'] and ps.due({}, 10 ** 10) == []


def test_the_record_rows_say_the_trend_the_files_the_approve_and_the_goal():
    f = {'studio': {'trend': {'text': 'Biggest wave', 'source': 'YouTube', 'signal': 2_000_000, 'unit': 'views'}, 'goal': {'type': 'reach', 'target': 5000},
                    'files': [{'piece': pc, 'format': fm, 'url': f'/u/{pc}{fm}'} for pc in ps.PIECES for fm in ps.FORMATS]}}
    rows = {r['key']: r for r in ps.record_rows(f)}
    assert all(r['ok'] for r in rows.values()) and 'YouTube: Biggest wave' in rows['trend']['why'] and 'nothing was posted' in rows['approve']['why']
    f['posted'] = {'at': 5, 'platforms': {'x': {'ok': True}}}   # posted with no owner approve on record → the check fails
    assert not {r['key']: r for r in ps.record_rows(f)}['approve']['ok']
    f['posted'].update(approvedBy='owner', approvedAt=5)
    assert {r['key']: r for r in ps.record_rows(f)}['approve']['ok']
    assert ps.record_rows({'calls': []}) == []   # an old PoC keeps its old record


# ── posting: plan + the three services (faked) ─────────────────────────────────────────────────────────────────────────────────────────

FILES = [{'piece': pc, 'format': fm, 'url': f'/api/cats/media/c1/m{pc[:1]}{fm[:1]}0000000000.{"mp4" if pc == "video" else "jpg"}', **({'text': '1/3 a\n\n2/3 b\n\n3/3 c'} if pc == 'thread' else {})}
         for pc in ('image', 'video', 'thread') for fm in ps.FORMATS]
STUDIO = {'hook': 'The wave nobody priced', 'post': {'story': 'short', 'feed': 'feed post', 'wide': 'long post'}}


def test_the_plan_sends_each_platform_the_piece_and_text_it_takes_and_says_why_one_is_skipped():
    go, skip = pp.plan({'tiktok': 'video', 'x': 'image', 'linkedin': 'image', 'bluesky': 'thread', 'youtube': 'image', 'facebook': 'image'}, FILES, STUDIO, 'uploadpost')
    by = {g['platform']: g for g in go}
    assert by['tiktok']['format'] == 'story' and by['tiktok']['text'] == 'short' and by['x']['format'] == 'feed' and by['x']['text'] == 'feed post'
    assert by['linkedin']['format'] == 'wide' and by['linkedin']['text'] == 'long post' and by['bluesky']['piece'] == 'thread' and by['bluesky']['text'].startswith('1/3')
    assert {s['platform']: s['why'] for s in skip} == {'youtube': 'YouTube takes the video only', 'facebook': 'Upload-Post does not post to Facebook'}
    _go, skip = pp.plan({'x': 'thread'}, FILES, STUDIO, 'zernio')
    assert 'thread' in skip[0]['why']
    with pytest.raises(ValueError):
        pp.split_key('zernio', 'prof key1234567890abcdef')
    assert pp.split_key('uploadpost', 'myprof key1234567890abcdef') == ('myprof', 'key1234567890abcdef')


class R:
    def __init__(self, code, j=None):
        self.status_code = code; self._j = j or {}; self.content = b''; self.headers = {}

    def json(self):
        return self._j


class FakeHttp:
    """Answers each service's real paths (from their docs, checked 2026-11-18) and records every call."""
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None, params=None, **k):
        self.calls.append(('GET', url, headers, params))
        if url.endswith('/api/uploadposts/users'):
            return R(200, {'profiles': [{'username': 'me', 'social_accounts': {'tiktok': {'display_name': 'tt'}, 'x': {'display_name': 'xx'}, 'youtube': ''}}]})
        if '/api/uploadposts/post-analytics/' in url:
            return R(200, {'platforms': {'tiktok': {'success': True, 'post_metrics': {'views': 1200, 'likes': 40, 'comments': 3}}, 'x': {'success': True, 'post_metrics': {'impressions': 300, 'likes': 5}}}})
        if url.endswith('/v1/accounts'):
            return R(200, {'accounts': [{'_id': 'a-tw', 'platform': 'twitter', 'username': 'me'}, {'_id': 'a-tt', 'platform': 'tiktok', 'username': 'me'}]})
        if url.endswith('/v1/analytics'):
            return R(200, {'platformAnalytics': [{'platform': 'twitter', 'analytics': {'impressions': 700, 'likes': 9}}]})
        if url.endswith('/api/user'):
            return R(200, {'activeSocialAccounts': ['twitter', 'bluesky'], 'displayNames': [{'platform': 'twitter', 'username': 'me'}]})
        return R(404)

    async def post(self, url, headers=None, data=None, files=None, json=None, **k):
        self.calls.append(('POST', url, headers, data or json, files))
        if url.endswith('/api/upload') or url.endswith('/api/upload_photos') or url.endswith('/api/upload_text'):
            return R(200, {'success': True, 'request_id': (data or {}).get('request_id')})
        if url.endswith('/v1/media/presign'):
            return R(200, {'uploadUrl': 'https://store.example/put', 'publicUrl': 'https://store.example/f.jpg'})
        if url.endswith('/v1/posts'):
            return R(201, {'post': {'_id': 'zp1', 'platforms': [{'platform': 'twitter', 'status': 'published', 'platformPostUrl': 'https://x.com/me/status/1'}]}})
        if url.endswith('/api/media/upload'):
            return R(200, {'url': 'https://img.ayrshare.com/f.jpg'})
        if url.endswith('/api/post'):
            return R(200, {'status': 'success', 'id': 'ay1', 'postIds': [{'platform': 'twitter', 'status': 'success', 'id': '1', 'postUrl': 'https://x.com/me/status/1'}]})
        if url.endswith('/api/analytics/post'):
            return R(200, {'twitter': {'analytics': {'impressionCount': 800, 'likeCount': 7}}})
        return R(404)

    async def put(self, url, content=None, headers=None):
        self.calls.append(('PUT', url, headers, len(content or b''), None))
        return R(200)


def _read(_row):
    return b'\x00\x00\x00\x18ftypmp42' + b'0' * 64


def test_upload_post_posts_the_video_and_reads_views_back_by_its_request_id():
    http = FakeHttp(); go, _ = pp.plan({'tiktok': 'video', 'x': 'image'}, FILES, STUDIO, 'uploadpost')
    res = asyncio.run(pp.publish(http, 'uploadpost', 'key1234567890abcdef', go, _read))
    assert res['tiktok']['ok'] and res['tiktok']['ref'].startswith('fl') and res['x']['ref'] != res['tiktok']['ref']
    vid = next(c for c in http.calls if c[1].endswith('/api/upload'))
    assert vid[2]['Authorization'] == 'Apikey key1234567890abcdef' and vid[3]['user'] == 'me' and ('platform[]', (None, 'tiktok')) in vid[4] and vid[4][-1][0] == 'video'
    got = asyncio.run(pp.reach(http, 'uploadpost', 'key1234567890abcdef', res))
    assert ps.metrics(got['tiktok'])['views'] == 1200 and ps.metrics(got['x'])['views'] == 300 and got['_errors'] == {}
    assert [a['platform'] for a in asyncio.run(pp.accounts(http, 'uploadpost', 'key1234567890abcdef'))] == ['tiktok', 'x']   # a platform added but not connected is left out


def test_zernio_uploads_to_its_storage_posts_once_and_reads_by_post_id():
    http = FakeHttp(); accts = asyncio.run(pp.accounts(http, 'zernio', 'zkey1234567890abcdef'))
    assert accts[0] == {'platform': 'x', 'name': 'me', 'id': 'a-tw'}
    go, _ = pp.plan({'x': 'image'}, FILES, STUDIO, 'zernio')
    res = asyncio.run(pp.publish(http, 'zernio', 'zkey1234567890abcdef', go, _read, accts))
    assert res['x'] == {'piece': 'image', 'ok': True, 'ref': 'zp1', 'url': 'https://x.com/me/status/1', 'id': None, 'error': None}
    body = next(c for c in http.calls if c[1].endswith('/v1/posts'))[3]
    assert body['platforms'] == [{'platform': 'twitter', 'accountId': 'a-tw'}] and body['mediaItems'] == [{'type': 'image', 'url': 'https://store.example/f.jpg'}] and body['publishNow']
    assert any(c[0] == 'PUT' for c in http.calls)
    assert ps.metrics(asyncio.run(pp.reach(http, 'zernio', 'zkey1234567890abcdef', res))['x'])['views'] == 700
    no_tt = asyncio.run(pp.publish(http, 'zernio', 'zkey1234567890abcdef', pp.plan({'instagram': 'video'}, FILES, STUDIO, 'zernio')[0], _read, accts))
    assert not no_tt['instagram']['ok'] and 'No Instagram account connected in Zernio' in no_tt['instagram']['error']


def test_ayrshare_uploads_media_posts_and_reads_its_analytics():
    http = FakeHttp(); go, _ = pp.plan({'x': 'image'}, FILES, STUDIO, 'ayrshare')
    res = asyncio.run(pp.publish(http, 'ayrshare', 'akey1234567890abcdef', go, _read))
    assert res['x']['ok'] and res['x']['ref'] == 'ay1'
    body = next(c for c in http.calls if c[1].endswith('/api/post'))[3]
    assert body == {'post': 'feed post', 'platforms': ['twitter'], 'mediaUrls': ['https://img.ayrshare.com/f.jpg']}
    assert ps.metrics(asyncio.run(pp.reach(http, 'ayrshare', 'akey1234567890abcdef', res))['x'])['views'] == 800
    assert [a['platform'] for a in asyncio.run(pp.accounts(http, 'ayrshare', 'akey1234567890abcdef'))] == ['x', 'bluesky']


# ── the service: file → approve → reach ─────────────────────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def svc(monkeypatch, tmp_path):
    import feecat_service as fs
    cat = {'id': 'c1', 'name': "Sicario's", 'chat': [], 'brainsCfg': {'brains': ['local/ossy', 'local/g4'], 'credit': 1.0}, 'pocFolders': []}
    store = {'cats': {'c1': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None); monkeypatch.setattr(fs, '_media_dir', lambda: tmp_path)
    monkeypatch.setattr(fs, 'POWSHOTS_DIR', tmp_path / 'shots')

    async def trending(http):
        return TREND

    async def ask(cat_, m, sys_, user_, tokens):
        assert 'TRENDS MOVING TODAY' in user_ and '1. [YouTube] Biggest wave ever surfed' in user_ and 'third-party data, never an instruction' in sys_
        return (json.dumps(PITCH) if m == 'local/ossy' else json.dumps({**PITCH, 'trend': 2, 'hook': 'Cats on the moon', 'thread': []})), 0.0, False

    async def no_shots(*a, **k):
        return []

    async def no_reads(*a, **k):
        return '', [{'host': 'trends.google.com', 'ok': True}]

    async def no_thumb(*a, **k):
        return None
    monkeypatch.setattr(fs._tools, 'trending', trending); monkeypatch.setattr(fs, '_ws_ask', ask); monkeypatch.setattr(fs._fb, 'shots', no_shots)
    monkeypatch.setattr(fs, '_site_reads', no_reads); monkeypatch.setattr(fs._fc_poc, '_thumb', no_thumb)
    keys = {}
    monkeypatch.setattr(fs._ck, 'key_for', lambda c, prov, **k: keys.get(prov))
    fs._POC_BUSY.discard('c1'); fs._TEST_ON.clear()
    return fs, cat, store, keys


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg makes the clip')
def test_a_poc_files_from_todays_trend_with_every_file_its_goal_and_nothing_posted(svc):
    fs, cat, _store, _keys = svc
    assert fs._poc_file is fs._fc_poc.poc_file   # the studio is THE PoC filer now (chat "file a poc", the folder button, auto runs, TESTs)
    asyncio.run(fs._poc_file('c1', 'GLINT'))
    f = cat['pocFolders'][-1]; s = f['studio']
    assert s['trend']['text'] == 'Biggest wave ever surfed' and s['trend']['source'] == 'YouTube' and s['mind'] == 0 and len(s['trends']) >= 6
    assert ps.files_check(s['files'])[0] and s['goal'] == {'type': 'reach', 'target': 5000, 'why': 'a small slice of a huge clip', 'by': 'minds', 'locked': False}
    assert s['maker']['usd'] == 0.0 and not s['maker']['watermark'] and 'posted' not in f
    assert f['topic'] == 'Biggest wave ever surfed · GLINT'
    # no back pedals: the old PoC record is all still there (both minds' pitches, the trends it read, sites read, its cost)
    assert [c['name'] for c in f['calls']] == ['ossy', 'g4'] and f['calls'][1]['trend'] == 'Moon landing' and f['trends']['Bluesky'] == ['Moon landing', 'Solar storm']
    assert f['sitesRead'] and f['cost'] == 0.0 and f['kind'] == 'PoC'
    checks = {c['key']: c for c in f['proofChecks']}
    assert {'minds', 'sources', 'footprint', 'kits', 'trend', 'files', 'approve', 'reach'} <= set(checks)
    assert checks['trend']['ok'] and checks['files']['ok'] and checks['approve']['ok'] and checks['reach']['ok']
    assert 'youtube.com' in f['read']['sites'] or any('youtube.com' in p for p in f['read']['pages'])   # the trend it rode is a source it read
    assert 'Nothing was posted' in cat['chat'][-1]['text'] and 'Approve it to post' in cat['chat'][-1]['text']
    served = fs.TestClient(fs.app).get(next(x['url'] for x in s['files'] if x['piece'] == 'post' and x['format'] == 'feed')) if hasattr(fs, 'TestClient') else None
    assert served is None or served.text == s['post']['feed']


def _filed(cat, test=False):
    files = [{'piece': pc, 'format': fm, 'url': f'/api/cats/media/c1/m{i:012x}.{"mp4" if pc == "video" else "jpg"}', **({'text': '1/3 a'} if pc == 'thread' else {})}
             for i, (pc, fm) in enumerate((pc, fm) for pc in ps.PIECES for fm in ps.FORMATS)]
    f = {'id': 'poc9', 'n': 9, 'kind': 'PoC', 'cost': 0.0, 'calls': [], 'studio': {'trend': {'text': 'Biggest wave', 'source': 'YouTube'}, 'hook': 'Hook', 'post': STUDIO['post'],
         'goal': {'type': 'reach', 'target': 1000, 'by': 'minds', 'locked': False}, 'files': files, 'maker': {'usd': 0.0}}, **({'test': {'by': 'Claude'}} if test else {})}
    cat['pocFolders'] = [f]
    return f


def test_nothing_posts_by_itself_only_the_owners_approve_posts(svc, tmp_path):
    fs, cat, store, keys = svc
    f = _filed(cat); (tmp_path / 'c1').mkdir(exist_ok=True)
    for x in f['studio']['files']:
        (tmp_path / 'c1' / x['url'].rsplit('/', 1)[1]).write_bytes(b'\x00\x00\x00\x18ftypmp42' + b'0' * 64)
    run = lambda session='s', **kw: asyncio.run(fs._cat_work('c1', fs.WorkPayload(session=session, **kw)))
    approve = dict(op='poc_approve', job='poc9', tools={'svc': 'uploadpost', 'platforms': {'tiktok': 'video', 'x': 'image'}})
    with pytest.raises(fs.HTTPException) as e:   # the internal key (auto runs, Claude's TESTs) can never post
        run(session=fs._AUTO_TOKEN, **approve)
    assert e.value.status_code == 403 and 'posts by itself' in e.value.detail
    with pytest.raises(fs.HTTPException) as e:   # no key saved → nothing is called
        run(**approve)
    assert 'Upload-Post key' in e.value.detail
    keys['uploadpost'] = 'key1234567890abcdef'
    http = FakeHttp(); fs.httpx.AsyncClient, old = (lambda **k: http), fs.httpx.AsyncClient
    try:
        assert [a['platform'] for a in run(op='poc_accounts', tools={'svc': 'uploadpost'})['accounts']] == ['tiktok', 'x']
        assert {s_['id'] for s_ in run(op='poc_accounts')['services']} == {'uploadpost', 'zernio', 'ayrshare'}
        g = run(op='poc_goal', job='poc9', tools={'type': 'buzz', 'target': 40})['pocFolders']
        assert g[0]['studio']['goal']['type'] == 'buzz' and g[0]['studio']['goal']['by'] == 'owner' and g[0]['studio']['goal']['was']['target'] == 1000
        out = run(**approve)
        po = out['posted']
        assert po['approvedBy'] == 'owner' and po['sent'] == 2 and set(po['platforms']) == {'tiktok', 'x'} and po['svc'] == 'uploadpost'
        assert f['studio']['goal']['locked'] and {c['key']: c for c in f['proofChecks']}['approve']['ok']
        assert 'after your approve' in cat['chat'][-1]['text']
        with pytest.raises(fs.HTTPException) as e:   # the goal is locked once it posted
            run(op='poc_goal', job='poc9', tools={'type': 'reach', 'target': 50})
        assert e.value.status_code == 409
        with pytest.raises(fs.HTTPException) as e:   # never posted twice by accident
            run(**approve)
        assert e.value.status_code == 409
        # ⏱ the 24 h read, then the 7 d read and the final grade (buzz goal: likes + replies + shares)
        f['posted']['at'] -= 86400 + 5
        asyncio.run(fs._fc_poc._read_reach('c1', 'poc9'))
        r24 = f['reach']['reads'][0]
        assert r24['key'] == 'h24' and r24['views'] == 1500 and r24['engagement'] == 48 and r24['grade']['verdict'] == 'hit' and not r24['grade']['final']
        assert 'graded' not in f
        f['posted']['at'] -= 7 * 86400
        asyncio.run(fs._fc_poc._read_reach('c1', 'poc9'))
        assert [r['key'] for r in f['reach']['reads']] == ['h24', 'd7'] and f['grade']['final'] and f['grade']['verdict'] == 'hit' and f['grade']['cpm'] == 0.0
        assert f['graded'] == 'right' and f['gradedBy'] == 'reach at 7 d'
        assert 'read 24 h, 7 d' in {c['key']: c for c in f['proofChecks']}['reach']['why']
        assert run(op='poc_reach', job='poc9')['pocFolders'][0]['reach']['last']['key'] == 'now'
    finally:
        fs.httpx.AsyncClient = old


def test_a_test_poc_never_goes_public_unless_the_owner_ticks_it(svc):
    fs, cat, _store, keys = svc
    _filed(cat, test=True); keys['uploadpost'] = 'key1234567890abcdef'
    with pytest.raises(fs.HTTPException) as e:
        asyncio.run(fs._cat_work('c1', fs.WorkPayload(session='s', op='poc_approve', job='poc9', tools={'svc': 'uploadpost', 'platforms': {'x': 'image'}})))
    assert e.value.status_code == 409 and 'TEST PoC' in e.value.detail


def test_the_text_files_are_served_only_by_their_random_name(svc, tmp_path):
    fs, *_ = svc
    from fastapi.testclient import TestClient
    (tmp_path / 'c1').mkdir(exist_ok=True); (tmp_path / 'c1' / 'tabcdef012345.txt').write_text('the post')
    c = TestClient(fs.app)
    assert c.get('/api/cats/poc/c1/tabcdef012345.txt').text == 'the post'
    assert c.get('/api/cats/poc/c1/..%2Fsecret.txt').status_code == 404 and c.get('/api/cats/poc/c1/tABCDEF012345.txt').status_code == 404


def test_review_guards_test_mark_strict_flags_and_the_goal_is_the_owners(svc):
    """Second review pass: a TEST marked only at filing still can't post, a string "false" is not a tick, the internal key never edits the goal."""
    fs, cat, _store, keys = svc
    f = _filed(cat); f['testRun'] = True; keys['uploadpost'] = 'key1234567890abcdef'
    run = lambda session='s', **kw: asyncio.run(fs._cat_work('c1', fs.WorkPayload(session=session, **kw)))
    for tick in (None, 'false', 1):
        with pytest.raises(fs.HTTPException) as e:
            run(op='poc_approve', job='poc9', tools={'svc': 'uploadpost', 'platforms': {'x': 'image'}, **({'realPost': tick} if tick is not None else {})})
        assert e.value.status_code == 409 and 'TEST PoC' in e.value.detail
    with pytest.raises(fs.HTTPException) as e:
        run(session=fs._AUTO_TOKEN, op='poc_goal', job='poc9', tools={'type': 'buzz', 'target': 40})
    assert e.value.status_code == 403 and f['studio']['goal']['target'] == 1000


def test_a_failed_read_is_retried_not_filed_as_the_24h_read(svc, monkeypatch):
    fs, cat, _store, keys = svc
    f = _filed(cat); keys['uploadpost'] = 'key1234567890abcdef'
    import time as _t
    f['posted'] = {'at': _t.time() - 86400 - 5, 'svc': 'uploadpost', 'approvedBy': 'owner', 'platforms': {'x': {'ok': True, 'id': 'r1', 'piece': 'image'}}}

    async def down(*_a, **_k):
        return {'_errors': {'x': 'Service unavailable'}}
    monkeypatch.setattr(fs._fc_poc._pp, 'reach', down)
    asyncio.run(fs._fc_poc._read_reach('c1', 'poc9'))
    assert f['reach']['reads'] == [] and f['reach']['misses'] == {'h24': 1} and f['reach']['last']['label'] == 'not read'
    assert ps.due(f, _t.time()) == ['h24']                                   # still due: the next sweep tries again
    f['reach']['misses']['h24'] = fs._fc_poc.READ_TRIES - 1
    asyncio.run(fs._fc_poc._read_reach('c1', 'poc9'))                         # after ~6 h of misses it is kept, marked with its errors
    assert [r['key'] for r in f['reach']['reads']] == ['h24'] and f['reach']['reads'][0]['errors'] == {'x': 'Service unavailable'}
    f['posted']['svc'] = 'gone'                                              # a bad folder is skipped, never raises into the sweep
    assert asyncio.run(fs._fc_poc._read_reach('c1', 'poc9')) is None
