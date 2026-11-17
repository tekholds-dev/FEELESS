"""🎭 The Bishop flow on OpenRouter only (owner 2026-11-17: "goto my bishop file and add a viral video clip in there and ask for them to replace the main
character with bishop" + "assure this works through open router as im not adding more funds into a fal key"). A clip comes in from an upload, a
Bluesky post or a direct link (YouTube / TikTok / Instagram refused: their terms forbid downloading); a chat ask swaps the newest clip with
Seedance 2.0 reference-to-video (clip = video reference, character = image reference) and lays the clip's own sound back. Network + ffmpeg faked."""
import asyncio
import base64
import pathlib

import pytest

import cat_keys as ck
import clip_source as cs
import media_gen as mg
from test_media_gen import _R
from test_media_swap import MP4, _folder, du
from test_play_studio import _server

OR_KEY = 'sk-or-v1-' + 'b' * 40


# ── pure: what may be fetched, how ffmpeg cuts it ────────────────────────────────────────────────────────────────────────────────────────────
def test_links_bluesky_and_direct_files_pass_the_apps_that_forbid_downloads_do_not():
    assert cs.classify('https://bsky.app/profile/someone.bsky.social/post/3lxyzabc123') == ('bluesky', 'someone.bsky.social', '3lxyzabc123')
    assert cs.classify('https://cdn.example.com/a/dance.mp4') == ('direct', 'https://cdn.example.com/a/dance.mp4')
    for bad, word in [('https://www.youtube.com/watch?v=abc', 'YouTube'), ('https://youtu.be/abc', 'YouTube'), ('https://www.tiktok.com/@a/video/1', 'TikTok'),
                      ('https://www.instagram.com/reel/x/', 'Instagram'), ('https://x.com/a/status/1', 'X')]:
        with pytest.raises(ValueError, match=word):
            cs.classify(bad)
    for bad in ['http://cdn.example.com/a.mp4', 'file:///etc/passwd', 'https://example.com/page.html']:
        with pytest.raises(ValueError):
            cs.classify(bad)


def test_a_bluesky_video_must_sit_on_bluesky_video_servers():
    t = lambda pl: {'thread': {'post': {'record': {'text': 'when the  beat\ndrops'}, 'embed': {'playlist': pl}}}}
    assert cs.bsky_video(t('https://video.bsky.app/watch/did/cid/playlist.m3u8')) == ('https://video.bsky.app/watch/did/cid/playlist.m3u8', 'when the beat drops')
    q = {'thread': {'post': {'record': {}, 'embed': {'media': {'playlist': 'https://video.cdn.bsky.app/hls/x.m3u8'}}}}}
    assert cs.bsky_video(q)[0].startswith('https://video.cdn.bsky.app/')   # a quote post with media
    for bad in ['https://evil.example/playlist.m3u8', 'http://video.bsky.app/x.m3u8', 'file:///etc/passwd']:
        with pytest.raises(ValueError):
            cs.bsky_video(t(bad))
    with pytest.raises(ValueError, match='no video'):
        cs.bsky_video({'thread': {'post': {'embed': {}}}})


def test_ffmpeg_args_a_stream_gets_only_hls_protocols_a_file_none():
    a = cs.cut_args('https://video.bsky.app/p.m3u8', '/o.mp4', 0, 15, stream=True)
    assert a[a.index('-protocol_whitelist') + 1] == 'https,tls,tcp,crypto,hls' and '-map' not in a and '-ss' not in a
    b = cs.cut_args('/in.mov', '/o.mp4', 2.5, 15)
    assert '-protocol_whitelist' not in b and b[b.index('-ss') + 1] == '2.50' and b[b.index('-t') + 1] == '15.00' and '0:v:0' in b
    assert cs.nearest_aspect(1080, 1920) == '9:16' and cs.nearest_aspect(1920, 1080) == '16:9' and cs.nearest_aspect(None, 0) == '9:16'
    s = cs.sound_args('/made.mp4', '/clip.mp4', '/out.mp4')
    assert s[s.index('-c:v') + 1] == 'copy' and '1:a:0' in s and '-shortest' in s


# ── the OpenRouter request ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_seedance_swap_request_matches_openrouters_videos_api_and_its_price():
    """Read 2026-11-17 from openrouter.ai/docs/api-reference/videos: input_references takes video_url + image_url; Seedance 2.0 makes 4–15 s."""
    _, url, h, b = mg.v2v_req('or-seedance-swap', OR_KEY, 'IMG', 'VID', 'replace the main character with bishop', 9.6, '9:16')
    assert url == 'https://openrouter.ai/api/v1/videos' and h['Authorization'] == f'Bearer {OR_KEY}'
    assert b['model'] == 'bytedance/seedance-2.0' and b['duration'] == 10 and b['aspect_ratio'] == '9:16' and b['resolution'] == '720p' and b['generate_audio'] is False
    assert b['input_references'] == [{'type': 'video_url', 'video_url': {'url': 'VID'}}, {'type': 'image_url', 'image_url': {'url': 'IMG'}}]
    assert b['prompt'].startswith(mg.SWAP_RULE) and b['prompt'].endswith('replace the main character with bishop')
    assert mg.v2v_req('or-seedance-fast-swap', OR_KEY, 'I', 'V', '', 15, '16:9')[3]['model'] == 'bytedance/seedance-2.0-fast'
    assert mg.v2v_cost('or-seedance-swap', 15) == 1.39 and mg.v2v_cost('or-seedance-fast-swap', 15) == 0.8   # 921,600 px × 24 fps × 15 s / 1024 tokens
    assert (mg.seedance_len(2), mg.seedance_len(9.6), mg.seedance_len(40)) == (4, 10, 15)
    assert mg.swap_auto({'openrouter', 'fal'}) == 'or-seedance-swap' and mg.swap_auto({'fal'}) == 'fal-wan-replace' and mg.swap_auto(set()) is None


# ── the whole flow, served ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _fake_ffmpeg(monkeypatch, fs, ran, size=(720, 1280)):
    async def ffmpeg(args, timeout=180):
        ran.append(list(args))
        if args[0] == 'ffprobe':
            return 0, ('{"streams":[{"width":%d,"height":%d}]}' % size).encode()
        out = pathlib.Path(args[-1])
        out.write_bytes(b'REF' if out.suffix == '.mp4' and '-an' in args else b'JPG' if out.suffix == '.jpg' else b'SOUND' if '1:a:0' in args else b'CUT')
        return 0, b''
    monkeypatch.setattr(fs, '_ffmpeg', ffmpeg)


def _setup(monkeypatch, tmp_path, secs=9.5):
    fs, c, store = _server(monkeypatch, tmp_path); ws = _folder(fs, store, tmp_path, fal=False)
    async def clip_len(p):
        return secs, 30.0
    monkeypatch.setattr(fs, '_clip_len', clip_len)
    return fs, c, store, ws, (lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', **kw}))


def test_a_chat_ask_swaps_the_newest_clip_on_openrouter_with_no_fal_key(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path); ran = []; _fake_ffmpeg(monkeypatch, fs, ran); real = fs._media_run
    async def no_run(*a):
        return None
    monkeypatch.setattr(fs, '_media_run', no_run)
    assert post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True}).status_code == 200
    ask = {'swap': 'auto', 'clip': 'last'}
    r = post(op='media_make', job=ws, text='replace the main character with bishop', tools=ask)
    assert r.status_code == 400 and 'OpenRouter' in r.json()['detail']   # nothing linked: no swap, and it says what to link
    ck.put(store['cats']['g'], 'openrouter', OR_KEY, data_dir=tmp_path)
    r = post(op='media_make', job=ws, text='replace the main character with bishop', tools=ask)
    assert r.status_code == 200, r.text
    md = r.json()['doc']['messages'][-1]['media']
    assert md['provider'] == 'openrouter' and md['modelId'] == 'or-seedance-swap' and md['aspect'] == '9:16' and md['keepSound'] and md['usd'] == mg.v2v_cost('or-seedance-swap', 9.5)
    assert md['fromImg']['mid'] == 'maaaaaaaaaaa1' and OR_KEY not in r.text
    said = r.json()['doc']['messages'][-1]['text']   # the folder's character by name, never the model that drew its picture
    assert said.startswith('Bishop swapped into') and 'Gemini' not in said, said
    sent = []
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, meth, url, headers=None, json=None):
            sent.append((url, headers, json))
            return _R(202, {'id': 'v9', 'polling_url': 'https://openrouter.ai/api/v1/videos/v9', 'status': 'pending'})
        async def get(self, url, headers=None):
            return _R(200, {'status': 'completed'})
        def stream(self, meth, url, **kw):
            return _R(200, None, b'SWAPPED')
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **kw: H()); monkeypatch.setattr(fs._mg, 'POLL_S', 0)
    asyncio.run(real('g', ws, md['id']))
    url, heads, body = sent[0]
    assert url == 'https://openrouter.ai/api/v1/videos' and body['model'] == 'bytedance/seedance-2.0' and body['duration'] == 10 and body['aspect_ratio'] == '9:16'
    vid, img = body['input_references']
    # the light copies go as https links (OpenRouter: "Only HTTPS URLs are allowed"), served only from the swap's own token files
    v_url, i_url = vid['video_url']['url'], img['image_url']['url']
    assert v_url.startswith('https://test-tunnel.trycloudflare.com/g/pub/') and v_url.endswith('.mp4') and i_url.startswith('https://test-tunnel.trycloudflare.com/g/pub/') and i_url.endswith('.jpg')
    assert (tmp_path / 'media' / 'g' / 'pub' / v_url.rsplit('/', 1)[-1]).read_bytes() == b'REF'
    assert 'data:' not in str(body)
    assert body['prompt'].endswith('replace the main character with bishop')
    done = [m for m in fs._ws_load('g', ws)['messages'] if m.get('media')][-1]['media']
    assert done['status'] == 'done' and (tmp_path / 'media' / 'g' / f"{md['id']}.mp4").read_bytes() == b'SOUND'   # the clip's own sound laid back
    assert not list((tmp_path / 'media' / 'g' / 'tmp').iterdir())   # the light copies are gone


def test_seedance_needs_four_seconds_and_a_character(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path, secs=2.0); _fake_ffmpeg(monkeypatch, fs, [])
    ck.put(store['cats']['g'], 'openrouter', OR_KEY, data_dir=tmp_path)
    post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True})
    r = post(op='media_make', job=ws, text='swap him for bishop', tools={'swap': 'auto', 'clip': 'last'})
    assert r.status_code == 400 and '4 to 15 s' in r.json()['detail']


def test_no_clip_yet_says_add_one(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path)
    ck.put(store['cats']['g'], 'openrouter', OR_KEY, data_dir=tmp_path)
    r = post(op='media_make', job=ws, text='swap him for bishop', tools={'swap': 'auto', 'clip': 'last'})
    assert r.status_code == 400 and 'clip' in r.json()['detail'].lower()


def test_a_bluesky_post_becomes_a_15_s_clip_read_from_its_own_video_servers(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path); ran = []; _fake_ffmpeg(monkeypatch, fs, ran)
    asked = []
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url, headers=None):
            asked.append(url)
            return _R(200, {'thread': {'post': {'record': {'text': 'the dance'}, 'embed': {'playlist': 'https://video.bsky.app/watch/d/c/playlist.m3u8'}}}})
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **kw: H())
    r = post(op='media_clip', job=ws, text='https://bsky.app/profile/dancer.bsky.social/post/3abcdefgh12', tools={'rights': True})
    assert r.status_code == 200, r.text
    md = r.json()['doc']['messages'][-1]['media']
    assert asked[0].startswith(cs.BSKY_API) and 'dancer.bsky.social' in asked[0]
    cut = [a for a in ran if a[0] == 'ffmpeg'][0]
    assert cut[cut.index('-i') + 1] == 'https://video.bsky.app/watch/d/c/playlist.m3u8' and '-protocol_whitelist' in cut
    assert md['clip'] and md['source'] == 'Bluesky' and md['label'] == '@dancer: the dance' and md['w'] == 720 and md['h'] == 1280
    r = post(op='media_clip', job=ws, text='https://bsky.app/profile/dancer.bsky.social/post/3abcdefgh12', tools={})
    assert r.status_code == 400   # the rights tick still counts for a link


def test_youtube_and_tiktok_links_are_refused_with_what_to_do(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path)
    for u, name in [('https://www.youtube.com/shorts/abc', 'YouTube'), ('https://www.tiktok.com/@a/video/1', 'TikTok')]:
        r = post(op='media_clip', job=ws, text=u, tools={'rights': True})
        assert r.status_code == 400 and name in r.json()['detail'] and 'Add your clip' in r.json()['detail']


def test_a_direct_link_is_checked_public_and_must_be_a_video(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path); _fake_ffmpeg(monkeypatch, fs, [])
    checked = []
    async def public(u):
        checked.append(u)
    monkeypatch.setattr(fs._cp, 'public_url', public)
    kind = {'ct': 'video/mp4'}
    class S(_R):
        def __init__(self):
            super().__init__(200, None, MP4); self.headers = {'content-type': kind['ct']}
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        def stream(self, meth, url, **kw):
            return S()
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **kw: H())
    r = post(op='media_clip', job=ws, text='https://cdn.example.com/clips/Big%20Dance.mp4', tools={'rights': True})
    assert r.status_code == 200, r.text
    md = r.json()['doc']['messages'][-1]['media']
    assert checked == ['https://cdn.example.com/clips/Big%20Dance.mp4'] and md['label'] == 'Big Dance' and md['source'] == 'cdn.example.com'
    kind['ct'] = 'text/html'
    r = post(op='media_clip', job=ws, text='https://cdn.example.com/clips/x.mp4', tools={'rights': True})
    assert r.status_code == 400 and 'video' in r.json()['detail']


# ── studio: one-tap Post and auto captions ──────────────────────────────────────────────────────────────────────────────────────────────────
def test_captions_parse_only_the_json_asked_for_inside_the_clip():
    raw = 'Sure! {"lines":[{"s":2.5,"e":4,"t":"  watch   this "},{"s":0,"e":1.2,"t":"yo"},{"s":70,"e":71,"t":"late"},{"s":"x","e":1,"t":"bad"},{"s":5,"e":40,"t":"long one"}]}'
    assert cs.parse_captions(raw, 60) == [{'at': 0.0, 'dur': 1.2, 'text': 'yo'}, {'at': 2.5, 'dur': 1.5, 'text': 'watch this'}, {'at': 5.0, 'dur': 8.0, 'text': 'long one'}]
    assert cs.parse_captions('no json here') == [] and cs.parse_captions('{"lines": "nope"}') == []
    a = cs.audio_args('/in.mp4', '/o.mp3', 30)
    assert '-vn' in a and a[a.index('-t') + 1] == '30.00' and a[a.index('-ar') + 1] == '16000'


def test_captions_run_on_the_agents_own_openrouter_key_and_send_only_the_sound(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path); ran = []
    async def ffmpeg(args, timeout=180):
        ran.append(list(args)); pathlib.Path(args[-1]).write_bytes(b'MP3SOUND'); return 0, b''
    monkeypatch.setattr(fs, '_ffmpeg', ffmpeg)
    r = post(op='playc_captions', text=du('mp4', MP4), tools={})
    assert r.status_code == 400 and 'OpenRouter' in r.json()['detail']
    ck.put(store['cats']['g'], 'openrouter', OR_KEY, data_dir=tmp_path)
    sent = []
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers=None, json=None):
            sent.append((url, headers, json))
            return _R(200, {'choices': [{'message': {'content': '{"lines":[{"s":0.4,"e":1.6,"t":"this is bishop"}]}'}}], 'usage': {'cost': 0.0007}})
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **kw: H())
    r = post(op='playc_captions', text=du('mp4', MP4), tools={'max': 12})
    assert r.status_code == 200, r.text
    assert r.json()['captions'] == [{'at': 0.4, 'dur': 1.2, 'text': 'this is bishop'}] and r.json()['usd'] == 0.0007 and OR_KEY not in r.text
    url, heads, body = sent[0]
    assert url == 'https://openrouter.ai/api/v1/chat/completions' and heads['Authorization'] == f'Bearer {OR_KEY}' and body['model'] == cs.CAPTION_MODEL
    aud = body['messages'][0]['content'][1]
    assert aud == {'type': 'input_audio', 'input_audio': {'data': base64.b64encode(b'MP3SOUND').decode(), 'format': 'mp3'}}   # the sound only, never the video
    assert ran[0][ran[0].index('-t') + 1] == '12.00' and not list((tmp_path / 'media' / 'g' / 'tmp').iterdir())


def test_post_puts_the_edit_and_its_source_clip_in_a_poc_folder(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path); _fake_ffmpeg(monkeypatch, fs, [])
    edit = MP4 + b'EDIT'
    assert post(op='playc_post', job='Bishop dance', text=du('mp4', edit), tools={}).status_code == 400   # the rights tick
    assert post(op='playc_post', job='x', text='data:image/png;base64,AAAA', tools={'rights': True}).status_code == 400
    r = post(op='playc_post', job='Bishop dance', text=du('mp4', edit), tools={'rights': True, 'ws': ws, 'source': du('mp4', MP4),
                                                                                 'project': {'aspect': '9:16', 'sources': [], 'clips': [], 'texts': [], 'music': []}})
    assert r.status_code == 200, r.text
    assert r.json()['ws'] == ws
    media = [m['media'] for m in fs._ws_load('g', ws)['messages'] if m.get('media')]
    src, done = media[-2], media[-1]
    assert src['clip'] and src['label'] == 'Source · Bishop dance'
    assert done['posted'] and done['label'] == 'Bishop dance' and done['fromClip']['mid'] == src['id'] and not done.get('clip')
    assert (tmp_path / 'media' / 'g' / done['url'].rsplit('/', 1)[-1]).read_bytes() == edit
    r = post(op='playc_post', job='Fresh one', text=du('mp4', edit), tools={'rights': True})   # no folder picked → a new PoC folder named after it
    assert r.status_code == 200 and r.json()['ws'] != ws and fs._ws_load('g', r.json()['ws'])['kind'] == 'content'
    assert any(p['id'] == r.json()['ws'] for p in post(op='playc_get').json()['pocs'])


# ── 2026-11-17 round 2: the model picker, the cap, a 17 s reel, public links ────────────────────────────────────────────────────────────────
def test_every_seedance_swap_takes_the_clip_and_the_longest_it_makes():
    rows = {r['id']: r for r in mg.v2v_list({'openrouter'})}
    assert {k for k, r in rows.items() if r.get('rec')} == set(mg.SEEDANCE) and rows['or-seedance-swap']['rec'] == 1
    assert rows['or-seedance25-flash-swap']['maxS'] == 30 and rows['or-seedance-swap']['maxS'] == 15 and rows['or-seedance25-flash-swap']['added'] == '2026-11-15'
    b = mg.v2v_req('or-seedance25-flash-swap', OR_KEY, 'I', 'V', '', 17.2, '9:16')[3]
    assert b['model'] == 'bytedance/seedance-2.5-flash' and b['duration'] == 17          # a whole 17 s reel on 2.5
    assert mg.v2v_req('or-seedance-swap', OR_KEY, 'I', 'V', '', 17.2, '9:16')[3]['duration'] == 15   # 2.0 makes its first 15 s
    assert mg.v2v_cost('or-seedance25-flash-swap', 17) == 1.58 and mg.v2v_cost('or-seedance25-swap', 17) == 2.35
    assert mg.swap_auto({'openrouter'}, 'or-seedance25-swap') == 'or-seedance25-swap' and mg.swap_auto({'openrouter'}, 'fal-wan-replace') == 'or-seedance-swap'
    assert cs.ref_args('/c.mp4', '/o.mp4', 15)[cs.ref_args('/c.mp4', '/o.mp4', 15).index('-t') + 1] == '15.00'


def test_the_same_video_added_twice_is_one_clip_card(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path); _fake_ffmpeg(monkeypatch, fs, [])
    first = post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True}).json()
    again = post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True, 'name': 'IMG_0062'}).json()
    clips = [m for m in again['doc']['messages'] if (m.get('media') or {}).get('clip')]
    assert len(clips) == 1 and again['same'] == first['doc']['messages'][-1]['media']['id']
    assert len(list((tmp_path / 'media' / 'g').glob('m*.mp4'))) == 1   # no second file left on disk


def test_a_17_s_reel_is_kept_whole_and_the_cap_and_most_used_follow_the_owner(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path, secs=17.2); _fake_ffmpeg(monkeypatch, fs, [])
    async def no_run(*a):
        return None
    monkeypatch.setattr(fs, '_media_run', no_run)
    ck.put(store['cats']['g'], 'openrouter', OR_KEY, data_dir=tmp_path)
    md = post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True}).json()['doc']['messages'][-1]['media']
    assert 'cutFrom' not in md   # 17 s is under 30: kept whole, nothing cut
    assert post(op='media_cap', text='0.2').status_code == 400 and post(op='media_cap', text='2').json()['swapCapUsd'] == 2.0
    r = post(op='media_make', job=ws, text='swap him for bishop', tools={'swap': 'or-seedance25-swap', 'clip': 'last'})
    assert r.status_code == 400 and 'over your $2.00 cap' in r.json()['detail']   # $2.35 > $2.00: refused before anything runs
    r = post(op='media_make', job=ws, text='swap him for bishop', tools={'swap': 'or-seedance25-flash-swap', 'clip': 'last'})
    assert r.status_code == 200, r.text
    made = r.json()['doc']['messages'][-1]['media']
    assert made['usd'] == 1.58 and made['secs'] == 17.2 and made['modelId'] == 'or-seedance25-flash-swap'
    cat = fs._load()['cats']['g']
    assert cat['swapUsed'] == {'or-seedance25-flash-swap': 1} and cat['swapLast'] == 'or-seedance25-flash-swap'
    m = post(op='media_models').json()
    assert m['swapCapUsd'] == 2.0 and m['swapUsed'] == {'or-seedance25-flash-swap': 1} and m['publicRefs'] is False
    r = post(op='media_make', job=ws, text='replace the main character with bishop', tools={'swap': 'auto', 'clip': 'last'})
    assert r.json()['doc']['messages'][-1]['media']['modelId'] == 'or-seedance25-flash-swap'   # the chat uses the one picked last


def test_with_a_public_site_the_references_go_as_2_hour_links(monkeypatch, tmp_path):
    fs, c, store, ws, post = _setup(monkeypatch, tmp_path); _fake_ffmpeg(monkeypatch, fs, [])
    monkeypatch.setenv('PUBLIC_SITE_URL', 'https://feeless.example.com/')
    clip = tmp_path / 'media' / 'g' / 'c.mp4'; clip.write_bytes(MP4)
    v, i = asyncio.run(fs._swap_refs('g', clip, tmp_path / 'media' / 'g' / 'maaaaaaaaaaa1.png', 15))
    assert v.startswith('https://feeless.example.com/api/cats/pubref/g/') and v.endswith('.mp4') and i.endswith('.jpg')
    got = c.get(v.replace('https://feeless.example.com', ''))
    assert got.status_code == 200 and got.content == b'REF'
    assert c.get('/api/cats/pubref/g/' + 'x' * 32 + '.mp4').status_code == 404 and c.get('/api/cats/pubref/g/..%2Fc.mp4').status_code == 404
    f = tmp_path / 'media' / 'g' / 'pub' / v.rsplit('/', 1)[-1]; import os; os.utime(f, (1, 1))
    assert c.get(v.replace('https://feeless.example.com', '')).status_code == 404   # after 2 hours it is gone
    # not public https → never a data URL (OpenRouter: "Only HTTPS URLs are allowed"): the quick tunnel's links
    monkeypatch.setenv('PUBLIC_SITE_URL', 'http://localhost:3000')
    async def _tun(root):
        return 'https://abc-def.trycloudflare.com'
    monkeypatch.setattr(fs._pubt, 'ensure', _tun)
    v2, i2 = asyncio.run(fs._swap_refs('g', clip, tmp_path / 'media' / 'g' / 'maaaaaaaaaaa1.png'))
    assert v2.startswith('https://abc-def.trycloudflare.com/g/pub/') and v2.endswith('.mp4') and i2.startswith('https://abc-def.trycloudflare.com/g/pub/')
    assert (tmp_path / 'media' / 'g' / 'pub' / v2.rsplit('/', 1)[-1]).is_file()

    async def _down(root):
        raise ValueError('the public link for your clip did not open')
    monkeypatch.setattr(fs._pubt, 'ensure', _down)
    n_before = len(list((tmp_path / 'media' / 'g' / 'pub').iterdir()))
    with pytest.raises(ValueError, match='did not open'):
        asyncio.run(fs._swap_refs('g', clip, tmp_path / 'media' / 'g' / 'maaaaaaaaaaa1.png'))
    assert len(list((tmp_path / 'media' / 'g' / 'pub').iterdir())) == n_before   # its files do not stay behind


def test_the_tunnel_server_serves_only_fresh_token_files(tmp_path):
    import os, urllib.request, urllib.error
    import pub_tunnel as pt
    d = tmp_path / 'g' / 'pub'; d.mkdir(parents=True); tok = 'A' * 32
    (d / f'{tok}.mp4').write_bytes(b'CLIP'); (tmp_path / 'g' / 'secret.png').write_bytes(b'NO')
    assert pt.url_in('INF |  https://red-fox-12.trycloudflare.com  |') == 'https://red-fox-12.trycloudflare.com' and pt.url_in('no url') == ''
    port = pt.serve(tmp_path); base = f'http://127.0.0.1:{port}'
    assert urllib.request.urlopen(f'{base}/g/pub/{tok}.mp4').read() == b'CLIP'
    assert urllib.request.urlopen(f'{base}/ok').read() == b'ok'
    for bad in ('/', '/g/', '/g/pub/', '/g/secret.png', f'/g/pub/../secret.png', '/g/pub/short.mp4', f'/g/pub/{tok}.png'):
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + bad)
        assert e.value.code == 404, bad
    os.utime(d / f'{tok}.mp4', (1, 1))
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(f'{base}/g/pub/{tok}.mp4')   # older than 2 hours: gone
