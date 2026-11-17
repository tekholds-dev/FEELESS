"""🎭 V2V (owner 2026-11-14 "wire the fal vid to vid"): the owner's own clip + the folder's character → one fal.ai swap (Wan 2.2 Animate Replace
or Kling 3.0 Motion Control) on the owner's own key. Clips need the rights tick, a real video and ≤ 15 s; the swap needs fal.ai linked and a
finished character picture; the job sends both files as data URLs and keeps the result. Network faked."""
import asyncio
import base64
import pathlib

import pytest

import cat_keys as ck
import media_gen as mg
import poc_play as pp
from test_media_gen import FAL_KEY, _R
from test_play_studio import _server

MP4 = b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 80
MOV = b'\x00\x00\x00\x14ftypqt  ' + b'\x00' * 80


def du(kind, raw):
    return f'data:video/{kind};base64,' + base64.b64encode(raw).decode()


def test_requests_match_fal_schemas_and_costs_follow_each_models_billing():
    _, url, h, b = mg.v2v_req('fal-wan-replace', 'k:s', 'data:image/png;base64,AA', 'data:video/mp4;base64,BB')
    assert url == 'https://queue.fal.run/fal-ai/wan/v2.2-14b/animate/replace' and h['Authorization'] == 'Key k:s'
    assert b == {'image_url': 'data:image/png;base64,AA', 'video_url': 'data:video/mp4;base64,BB', 'resolution': '580p', 'video_quality': 'high'}
    _, url, _, b = mg.v2v_req('fal-kling3-motion', 'k:s', 'I', 'V', 'he dances')
    assert url.endswith('/kling-video/v3/standard/motion-control') and b == {'image_url': 'I', 'video_url': 'V', 'character_orientation': 'video', 'keep_original_sound': True, 'prompt': 'he dances'}
    with pytest.raises(ValueError):
        mg.v2v_req('or-seedance-fast', 'k', 'I', 'V')
    assert mg.v2v_cost('fal-wan-replace', 10, 32) == 1.2        # 10 s × 32 fps / 16 = 20 billed s × $0.06
    assert mg.v2v_cost('fal-kling3-motion', 10, 60) == 1.26     # Kling bills real seconds
    assert {r['id']: r['ready'] for r in mg.v2v_list({'openrouter'})} == {'fal-wan-replace': False, 'fal-kling3-motion': False, 'or-flux-edit': True, 'or-seedance-swap': True, 'or-seedance-fast-swap': True,
        'or-seedance25-flash-swap': True, 'or-seedance25-swap': True, 'or-seedance-mini-swap': True}
    assert mg.catalog({'fal'})['swapMaxS'] == 30   # a clip is kept up to 30 s (Seedance 2.5 makes 30)


def test_an_iphone_mov_is_a_real_clip():
    raw, ext = pp.decode(du('quicktime', MOV))
    assert raw == MOV and ext == 'mov' and pp.kind_of('mov') == 'video'
    with pytest.raises(ValueError):
        pp.decode(du('quicktime', b'#!/bin/sh rm -rf ~' + b'\x00' * 80))   # a renamed script is not a clip


def _folder(fs, store, tmp_path, fal=True):
    cat = store['cats']['g']
    if fal:
        ck.put(cat, 'fal', FAL_KEY, data_dir=tmp_path)
    row = fs._feat.new_folder(cat, 'content', 'Bishop', 1.0); doc = fs._feat.new_doc(row)
    (tmp_path / 'media' / 'g').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'media' / 'g' / 'maaaaaaaaaaa1.png').write_bytes(b'\x89PNGbishop')
    doc['messages'] = [{'by': 'Media', 'text': 'Bishop', 'at': 1, 'media': {'id': 'maaaaaaaaaaa1', 'kind': 'image', 'status': 'done', 'kept': True, 'label': 'Gemini 3.1 Flash Image',
                                                                          'url': '/api/cats/media/g/maaaaaaaaaaa1.png', 'prompt': 'Bishop', 'provider': 'openrouter'}}]
    doc['character'] = {'mid': 'maaaaaaaaaaa1'}
    fs._ws_save('g', doc)
    return row['id']


def test_a_clip_needs_the_rights_tick_a_real_video_and_15_s_at_most(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); ws = _folder(fs, store, tmp_path)
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', **kw})
    lens = {'v': (9.5, 30.0)}
    async def clip_len(p):
        return lens['v']
    monkeypatch.setattr(fs, '_clip_len', clip_len)
    assert post(op='media_clip', job=ws, text=du('mp4', MP4), tools={}).status_code == 400              # no rights tick
    assert post(op='media_clip', job=ws, text='data:image/png;base64,AAAA', tools={'rights': True}).status_code == 400
    ran = []
    async def ffmpeg(args, timeout=180):   # 2026-11-17: a long clip is CUT to 30 s from its start (it used to be refused)
        ran.append(args)
        if args[0] == 'ffmpeg':
            pathlib.Path(args[-1]).write_bytes(b'CUT')
        return 0, b''
    monkeypatch.setattr(fs, '_ffmpeg', ffmpeg)
    lens['v'] = (31.0, 30.0)
    r = post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True, 'start': 4})
    assert r.status_code == 200, r.text
    md = r.json()['doc']['messages'][-1]['media']
    assert md['cutFrom'] == 4.0 and (tmp_path / 'media' / 'g' / md['url'].rsplit('/', 1)[-1]).read_bytes() == b'CUT'
    cut = [a for a in ran if a[0] == 'ffmpeg'][0]
    assert cut[cut.index('-ss') + 1] == '4.00' and cut[cut.index('-t') + 1] == '30.00' and '-protocol_whitelist' not in cut   # a file never gets network protocols
    assert not list((tmp_path / 'media' / 'g' / 'tmp').iterdir())   # the upload's raw copy is gone
    lens['v'] = (9.5, 30.0)
    r = post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True, 'name': 'Dance trend'})
    assert r.status_code == 200, r.text
    md = r.json()['doc']['messages'][-1]['media']
    assert md['clip'] and md['status'] == 'done' and md['secs'] == 9.5 and md['fps'] == 30.0 and md['label'] == 'Dance trend' and md['rights']
    assert (tmp_path / 'media' / 'g' / md['url'].rsplit('/', 1)[-1]).read_bytes() == MP4


def test_the_swap_runs_on_fal_with_both_files_and_keeps_the_result(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); ws = _folder(fs, store, tmp_path); real = fs._media_run
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', **kw})
    async def clip_len(p):
        return 10.0, 32.0
    async def no_run(*a):
        return None
    monkeypatch.setattr(fs, '_clip_len', clip_len); monkeypatch.setattr(fs, '_media_run', no_run)
    clip = post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True}).json()['doc']['messages'][-1]['media']
    assert post(op='media_make', job=ws, text='', tools={'swap': 'nope', 'clip': clip['id']}).status_code == 400
    assert post(op='media_make', job=ws, text='', tools={'swap': 'fal-wan-replace', 'clip': 'mnope'}).status_code == 400
    r = post(op='media_make', job=ws, text='keep the chain gold', tools={'swap': 'fal-wan-replace', 'clip': clip['id']})
    assert r.status_code == 200, r.text
    md = r.json()['doc']['messages'][-1]['media']
    assert md['swap'] and md['provider'] == 'fal' and md['usd'] == 1.2 and md['fromImg']['mid'] == 'maaaaaaaaaaa1' and md['fromClip']['mid'] == clip['id']
    sent = []
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, meth, url, headers=None, json=None):
            sent.append((url, headers, json))
            return _R(200, {'request_id': 'q', 'status_url': 'https://queue.fal.run/x/requests/q/status', 'response_url': 'https://queue.fal.run/x/requests/q'})
        async def get(self, url, headers=None):
            return _R(200, {'status': 'COMPLETED'}) if url.endswith('/status') else _R(200, {'video': {'url': 'https://v3.fal.media/files/swap.mp4'}})
        def stream(self, meth, url, **kw):
            return _R(200, None, b'SWAPPED')
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **kw: H()); monkeypatch.setattr(fs._mg, 'POLL_S', 0)
    asyncio.run(real('g', ws, md['id']))
    url, heads, body = sent[0]
    assert url.endswith('/wan/v2.2-14b/animate/replace') and heads['Authorization'] == f'Key {FAL_KEY}'
    assert base64.b64decode(body['video_url'].split(',', 1)[1]) == MP4 and base64.b64decode(body['image_url'].split(',', 1)[1]) == b'\x89PNGbishop'
    done = [m for m in fs._ws_load('g', ws)['messages'] if m.get('media')][-1]['media']
    assert done['status'] == 'done' and (tmp_path / 'media' / 'g' / f"{md['id']}.mp4").read_bytes() == b'SWAPPED'


def test_no_fal_no_swap_and_no_character_no_swap(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); ws = _folder(fs, store, tmp_path, fal=False)
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', **kw})
    async def clip_len(p):
        return 5.0, 30.0
    monkeypatch.setattr(fs, '_clip_len', clip_len)
    clip = post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True}).json()['doc']['messages'][-1]['media']
    r = post(op='media_make', job=ws, text='', tools={'swap': 'fal-kling3-motion', 'clip': clip['id']})
    assert r.status_code == 400 and 'Link fal.ai' in r.json()['detail']
    ck.put(store['cats']['g'], 'fal', FAL_KEY, data_dir=tmp_path)
    d = fs._ws_load('g', ws); d.pop('character', None); d['messages'] = [m for m in d['messages'] if m['media']['kind'] != 'image']; fs._ws_save('g', d)
    r = post(op='media_make', job=ws, text='', tools={'swap': 'fal-kling3-motion', 'clip': clip['id']})
    assert r.status_code == 400 and 'character' in r.json()['detail']


OR_KEY = 'sk-or-v1-' + 'a' * 40


def test_flux_edit_request_matches_openrouters_videos_schema():
    """✏ owner 2026-11-16: FLUX Video Edit on OpenRouter (read from /api/v1/videos/models + the model's llms.txt the same day)."""
    _, url, h, b = mg.v2v_req('or-flux-edit', OR_KEY, None, 'data:video/mp4;base64,BB', 'make it night')
    assert url == 'https://openrouter.ai/api/v1/videos' and h['Authorization'] == f'Bearer {OR_KEY}'
    assert b == {'model': 'black-forest-labs/flux-video-edit', 'prompt': 'make it night', 'input_references': [{'type': 'video_url', 'video_url': {'url': 'data:video/mp4;base64,BB'}}]}
    with pytest.raises(ValueError):
        mg.v2v_req('or-flux-edit', OR_KEY, None, 'V', '  ')   # an edit with no words is refused before any call
    assert mg.v2v_cost('or-flux-edit', 10) == 0.3 and mg.v2v_provider('or-flux-edit') == 'openrouter' and mg.v2v_provider('fal-wan-replace') == 'fal'


def test_flux_edit_runs_on_openrouter_with_the_clip_and_no_character(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); ws = _folder(fs, store, tmp_path, fal=False); real = fs._media_run
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', **kw})
    async def clip_len(p):
        return 10.0, 30.0
    async def no_run(*a):
        return None
    monkeypatch.setattr(fs, '_clip_len', clip_len); monkeypatch.setattr(fs, '_media_run', no_run)
    d = fs._ws_load('g', ws); d.pop('character', None); fs._ws_save('g', d)   # no character: an edit does not need one
    clip = post(op='media_clip', job=ws, text=du('mp4', MP4), tools={'rights': True}).json()['doc']['messages'][-1]['media']
    r = post(op='media_make', job=ws, text='make it night', tools={'swap': 'or-flux-edit', 'clip': clip['id']})
    assert r.status_code == 400 and 'Link OpenRouter' in r.json()['detail']
    ck.put(store['cats']['g'], 'openrouter', OR_KEY, data_dir=tmp_path)
    r = post(op='media_make', job=ws, text='', tools={'swap': 'or-flux-edit', 'clip': clip['id']})
    assert r.status_code == 400 and 'what to change' in r.json()['detail']
    r = post(op='media_make', job=ws, text='make it night, neon signs', tools={'swap': 'or-flux-edit', 'clip': clip['id']})
    assert r.status_code == 200, r.text
    md = r.json()['doc']['messages'][-1]['media']
    assert md['provider'] == 'openrouter' and md['usd'] == 0.3 and 'fromImg' not in md and md['fromClip']['mid'] == clip['id']
    sent = []
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, meth, url, headers=None, json=None):
            sent.append((url, headers, json))
            return _R(202, {'id': 'vid1', 'polling_url': 'https://openrouter.ai/api/v1/videos/vid1', 'status': 'pending'})
        async def get(self, url, headers=None):
            return _R(200, {'status': 'completed'})
        def stream(self, meth, url, **kw):
            sent.append((url, kw.get('headers'), None))
            return _R(200, None, b'EDITED')
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **kw: H()); monkeypatch.setattr(fs._mg, 'POLL_S', 0)
    asyncio.run(real('g', ws, md['id']))
    url, heads, body = sent[0]
    assert url == 'https://openrouter.ai/api/v1/videos' and heads['Authorization'] == f'Bearer {OR_KEY}' and body['model'] == 'black-forest-labs/flux-video-edit'
    assert base64.b64decode(body['input_references'][0]['video_url']['url'].split(',', 1)[1]) == MP4 and body['prompt'].endswith('make it night, neon signs')
    assert sent[-1][0] == 'https://openrouter.ai/api/v1/videos/vid1/content'
    done = [m for m in fs._ws_load('g', ws)['messages'] if m.get('media')][-1]['media']
    assert done['status'] == 'done' and (tmp_path / 'media' / 'g' / f"{md['id']}.mp4").read_bytes() == b'EDITED'
