"""👤 Owner 2026-11-12 (Bishop): a made image becomes a character — one tap animates him (image → video, Seedance-grade), he can lead every
video the folder makes after, and a PoC filed from a folder chat carries its made files, writes a desk-chat line and reaches the monitors."""
import json
import time

import pytest

import media_gen as mg
from test_play_studio import _server


def test_i2v_requests_carry_the_image_per_provider():
    img = 'data:image/png;base64,AAAA'
    _, url, _, body = mg.submit_req('openrouter', mg.I2V['or-seedance-fast'], 'he walks', 'sk-or-x', 'or-seedance-fast', image=img)
    assert url.endswith('/videos') and body['image_url'] == img and body['prompt'] == 'he walks' and body['resolution'] == '720p'
    _, url, _, body = mg.submit_req('fal', mg.i2v_model('fal-wan22-5b'), 'he walks', 'k:s', image=img)
    assert 'image-to-video' in url and body['image_url'] == img
    _, url, _, body = mg.submit_req('replicate', mg.i2v_model('rep-seedance-lite'), 'he walks', 'r8_x', image=img)
    assert 'bytedance/seedance-1-lite' in url and body['input']['image'] == img
    _, _, _, body = mg.submit_req('openrouter', 'bytedance/seedance-2.0-fast', 'plain', 'sk-or-x', 'or-seedance-fast')
    assert 'image_url' not in body   # no image, no field


def test_i2v_refuses_a_model_with_no_image_door():
    with pytest.raises(ValueError, match='cannot start from an image'):
        mg.i2v_model('or-grok-lite')
    with pytest.raises(ValueError, match='cannot start from an image'):
        mg.i2v_model('or-gpt-image-mini')


def _content_folder_with_image(fs, store, tmp_path):
    cat = store['cats']['g']
    row = fs._feat.new_folder(cat, 'content', 'Bishop', 1.0)
    doc = fs._feat.new_doc(row)
    (tmp_path / 'media' / 'g').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'media' / 'g' / 'maaaaaaaaaaa1.png').write_bytes(b'\x89PNG fake')
    doc['messages'] = [{'by': 'Media', 'text': 'Bishop in the latest gear', 'at': 1,
                        'media': {'id': 'maaaaaaaaaaa1', 'kind': 'image', 'status': 'done', 'kept': True, 'label': 'Gemini 3.1 Flash Image',
                                  'url': '/api/cats/media/g/maaaaaaaaaaa1.png', 'prompt': 'Bishop in the latest gear', 'provider': 'openrouter', 'model': 'google/gemini-3.1-flash-image', 'modelId': 'or-flash-image'}}]
    fs._ws_save('g', doc)
    return row, doc


def test_character_leads_the_folder_videos(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    row, _ = _content_folder_with_image(fs, store, tmp_path)
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    async def no_run(*a, **k):
        return None
    monkeypatch.setattr(fs, '_media_run', no_run)
    monkeypatch.setattr(fs, '_media_house', lambda cat: True)
    # 👤 keep him as the character
    j = post('media_char', job=row['id'], text='maaaaaaaaaaa1')
    assert j.status_code == 200 and j.json()['doc']['character']['mid'] == 'maaaaaaaaaaa1'
    # 🎬 a video with no image picked still starts from him
    j = post('media_make', job=row['id'], text='he nods to the beat', tools={'kind': 'video'})
    assert j.status_code == 200, j.text
    md = j.json()['doc']['messages'][-1]['media']
    assert md['fromImg'] == {'mid': 'maaaaaaaaaaa1', 'url': '/api/cats/media/g/maaaaaaaaaaa1.png'} and md['kind'] == 'video'
    # 🙅 unless this make says no
    j = post('media_make', job=row['id'], text='a plain street scene', tools={'kind': 'video', 'noChar': True})
    assert 'fromImg' not in j.json()['doc']['messages'][-1]['media']
    # 🖼 an image never starts from him, and a bad start image is refused
    j = post('media_make', job=row['id'], text='a poster of him', tools={'kind': 'image'})
    assert 'fromImg' not in j.json()['doc']['messages'][-1]['media']
    assert post('media_make', job=row['id'], text='x y z', tools={'kind': 'video', 'img': 'nope'}).status_code == 400
    # 👤 cleared = no longer used (the three queued makes are settled first: at most three run at once, by rule)
    assert post('media_char', job=row['id'], text='').json()['doc'].get('character') is None
    d_ = fs._ws_load('g', row['id'])
    for m_ in d_['messages']:
        if (m_.get('media') or {}).get('status') == 'queued':
            m_['media']['status'] = 'failed'
    fs._ws_save('g', d_)
    assert 'fromImg' not in post('media_make', job=row['id'], text='no one leads', tools={'kind': 'video'}).json()['doc']['messages'][-1]['media']


def test_poc_filed_from_chat_carries_media_and_says_so(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    row, doc = _content_folder_with_image(fs, store, tmp_path)
    doc['messages'] += [{'by': 'Mind A', 'text': 'Post him in a fit check, hook in the first second. ' * 3, 'at': 2}]
    fs._ws_save('g', doc)
    post = lambda op, **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', 'op': op, **kw})
    j = post('poc_answer', job=row['id'])
    assert j.status_code == 200, j.text
    cat = store['cats']['g']
    f = cat['pocFolders'][-1]
    assert f['media'] == [{'id': 'maaaaaaaaaaa1', 'kind': 'image', 'url': '/api/cats/media/g/maaaaaaaaaaa1.png', 'label': 'Gemini 3.1 Flash Image', 'prompt': 'Bishop in the latest gear'}]
    assert 'filed from its folder chat with 1 made file' in cat['chat'][-1]['text'] and cat['chat'][-1]['open'] == 'features'
    assert fs._FEED['g'][0]['kind'] == 'PoC' and 'PoC filed' in fs._FEED['g'][0]['text']
    # 🖥 the view serves it to the monitors; a folder filed BEFORE media rode on proofs (Bishop) gets its media joined at view time
    old = {k: v for k, v in f.items() if k != 'media'}
    cat['pocFolders'] = [old]
    fs._POC_MEDIA_SEEN.clear()
    v = fs._poc_view(cat)[0]
    assert v['media'][0]['url'] == '/api/cats/media/g/maaaaaaaaaaa1.png'


def test_media_done_reaches_an_already_filed_poc(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    row, doc = _content_folder_with_image(fs, store, tmp_path)
    cat = store['cats']['g']
    cat['pocFolders'] = [{'id': 'poc1', 'ws': row['id'], 'kind': 'PoC', 'at': 1, 'status': 'closed', 'topic': 'Bishop', 'calls': []}]
    doc['messages'] += [{'by': 'Media', 'text': 'he walks', 'at': 3, 'media': {'id': 'mbbbbbbbbbbb2', 'kind': 'video', 'status': 'running', 'label': 'Seedance 2.0 fast', 'prompt': 'he walks', 'provider': 'openrouter', 'model': 'bytedance/seedance-2.0-fast'}}]
    fs._ws_save('g', doc)
    fs._media_set('g', row['id'], 'mbbbbbbbbbbb2', None, status='done', url='/api/cats/media/g/mbbbbbbbbbbb2.mp4', kept=True, doneAt=round(time.time()))
    assert cat['pocFolders'][0]['media'][0] == {'id': 'mbbbbbbbbbbb2', 'kind': 'video', 'url': '/api/cats/media/g/mbbbbbbbbbbb2.mp4', 'label': 'Seedance 2.0 fast', 'prompt': 'he walks'}
