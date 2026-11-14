"""🎨 POC-PLAY: a playground edit comes back as a checked picture and is filed in the PoC folder as a new version (the original stays)."""
import asyncio
import base64
import struct
import zlib

import pytest

import poc_play as pp


def _png(w=4, h=4):
    raw = b''.join(b'\x00' + b'\xff\x00\x00' * w for _ in range(h))
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


def test_decode_takes_only_real_pictures():
    raw, ext = pp.decode('data:image/png;base64,' + base64.b64encode(_png()).decode())
    assert ext == 'png' and raw.startswith(b'\x89PNG')
    for bad in ('', 'hello', 'data:text/html;base64,PGgxPg==', 'data:image/png;base64,' + base64.b64encode(b'<script>alert(1)</script>' * 4).decode(),
                'data:image/png;base64,@@@@'):
        with pytest.raises(ValueError):
            pp.decode(bad)
    with pytest.raises(ValueError, match='too big'):
        pp.decode('data:image/png;base64,' + 'A' * (pp.MAX_BYTES * 2))


def test_version_label_counts_playground_edits_and_names_the_frame():
    msgs = [{'media': {'provider': 'fal'}}, {'media': {'provider': 'playground'}}, {}]
    assert pp.version_label(msgs, 'story') == 'Playground v2 · story'
    assert pp.version_label([], 'free') == 'Playground v1' and pp.version_label(None, 'nope') == 'Playground v1'


def test_the_work_op_files_a_new_version_into_the_folder_and_its_filed_poc(monkeypatch, tmp_path):
    import feecat_service as fs
    cat = {'id': 'c1', 'pocFolders': [{'id': 'poc1', 'ws': 'w1', 'status': 'closed', 'media': [{'id': 'morig', 'kind': 'image', 'url': '/x'}]}]}
    store = {'cats': {'c1': cat}}
    doc = {'id': 'w1', 'kind': 'content', 'messages': [{'by': 'Media', 'media': {'id': 'morig', 'kind': 'image', 'status': 'done', 'url': '/x', 'prompt': 'a red shoe'}}]}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None)
    monkeypatch.setattr(fs, '_ws_load', lambda cid, ws: doc if ws == 'w1' else None)
    monkeypatch.setattr(fs, '_ws_save', lambda cid, d: None)
    monkeypatch.setattr(fs, '_ws_view', lambda cid, ws: {'messages': doc['messages']})
    monkeypatch.setattr(fs, '_media_dir', lambda: tmp_path)
    url = 'data:image/png;base64,' + base64.b64encode(_png()).decode()
    out = asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='media_play', job='w1', text=url, tools={'from': 'morig', 'template': 'phone'}, session='s')))
    md = doc['messages'][-1]['media']
    assert md['status'] == 'done' and md['provider'] == 'playground' and md['label'] == 'Playground v1 · phone' and md['from'] == 'morig' and md['usd'] == 0
    assert md['prompt'] == 'a red shoe' and (tmp_path / 'c1' / f"{out['id']}.png").read_bytes().startswith(b'\x89PNG')
    assert doc['messages'][0]['media']['id'] == 'morig'                                        # the original stays
    assert [m['id'] for m in cat['pocFolders'][0]['media']] == ['morig', out['id']]           # the filed PoC shows the new version
    with pytest.raises(fs.HTTPException):
        asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='media_play', job='w1', text='data:text/html;base64,PGgxPg==', session='s')))


def test_a_recorded_clip_is_checked_and_files_as_a_video_version(monkeypatch, tmp_path):
    """POC-PLAY: Export clip → Save into the proof (MP4 from Chrome's recorder, WebM elsewhere); a renamed file is refused."""
    mp4 = b'\x00\x00\x00\x18ftypisom' + b'\x00' * 80
    webm = b'\x1a\x45\xdf\xa3' + b'\x00' * 80
    assert pp.decode('data:video/mp4;base64,' + base64.b64encode(mp4).decode()) == (mp4, 'mp4')
    assert pp.decode('data:video/webm;codecs=vp9,opus;base64,' + base64.b64encode(webm).decode())[1] == 'webm'
    assert pp.kind_of('mp4') == 'video' and pp.kind_of('png') == 'image'
    for bad in ('data:video/mp4;base64,' + base64.b64encode(webm).decode(), 'data:video/webm;base64,' + base64.b64encode(mp4).decode()):
        with pytest.raises(ValueError, match='real clip'):
            pp.decode(bad)
    with pytest.raises(ValueError, match='too big'):
        pp.decode('data:video/mp4;base64,' + 'A' * (pp.MAX_CLIP * 2))
    import feecat_service as fs
    cat = {'id': 'c1', 'pocFolders': []}; store = {'cats': {'c1': cat}}
    doc = {'id': 'w1', 'kind': 'content', 'messages': [{'by': 'Media', 'media': {'id': 'mv', 'kind': 'video', 'status': 'done', 'url': '/v', 'prompt': 'a launch'}}]}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None)
    monkeypatch.setattr(fs, '_ws_load', lambda cid, ws: doc)
    monkeypatch.setattr(fs, '_ws_save', lambda cid, d: None)
    monkeypatch.setattr(fs, '_ws_view', lambda cid, ws: {'messages': doc['messages']})
    monkeypatch.setattr(fs, '_media_dir', lambda: tmp_path)
    out = asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='media_play', job='w1', text='data:video/mp4;base64,' + base64.b64encode(mp4).decode(), tools={'from': 'mv', 'template': 'story'}, session='s')))
    md = doc['messages'][-1]['media']
    assert md['kind'] == 'video' and md['url'].endswith('.mp4') and md['from'] == 'mv' and md['usd'] == 0
    assert (tmp_path / 'c1' / f"{out['id']}.mp4").read_bytes() == mp4 and doc['messages'][0]['media']['id'] == 'mv'


def test_references_join_the_folder_and_images_keep_the_exact_character(monkeypatch, tmp_path):
    """POC-PLAY item 6: upload a reference ($0) → make it the character → an image make sends it to the model with the keep-exact rule."""
    import feecat_service as fs
    import media_gen as mg
    cat = {'id': 'c1', 'pocFolders': []}; store = {'cats': {'c1': cat}}
    doc = {'id': 'w1', 'kind': 'content', 'messages': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None)
    monkeypatch.setattr(fs, '_ws_load', lambda cid, ws: doc if ws == 'w1' else None)
    monkeypatch.setattr(fs, '_ws_save', lambda cid, d: doc.update(d))
    monkeypatch.setattr(fs, '_ws_view', lambda cid, ws: {'messages': doc['messages']})
    monkeypatch.setattr(fs, '_media_dir', lambda: tmp_path)
    W = lambda **k: asyncio.run(fs._cat_work('c1', fs.WorkPayload(job='w1', session='s', **k)))
    out = W(op='media_ref', text='data:image/png;base64,' + base64.b64encode(_png()).decode(), tools={'note': 'my mascot'})
    md = doc['messages'][-1]['media']
    assert md['provider'] == 'reference' and md['status'] == 'done' and md['usd'] == 0 and md['prompt'] == 'my mascot' and (tmp_path / 'c1' / f"{out['id']}.png").is_file()
    for bad in ('data:text/html;base64,PGgxPg==', 'http://127.0.0.1/x.png'):
        with pytest.raises(fs.HTTPException):
            W(op='media_ref', text=bad)
    with pytest.raises(fs.HTTPException):                                   # a private address is never fetched
        W(op='media_ref', text='https://127.0.0.1/x.png')
    W(op='media_char', text=out['id'])
    monkeypatch.setattr(fs._ck, 'public', lambda c: [{'provider': 'openrouter', 'saved': True}])
    monkeypatch.setattr(fs.asyncio, 'create_task', lambda c: c.close())
    W(op='media_make', text='him on a beach', tools={'kind': 'image', 'model': 'or-nano-banana'})
    made = doc['messages'][-1]['media']
    assert made['refs'] == [{'mid': out['id'], 'url': md['url']}]                    # the folder's character rides on the image
    sent = mg.ref_content(made['prompt'], fs._media_refs('c1', made))
    assert sent[0]['text'].startswith('him on a beach') and 'EXACT same character' in sent[0]['text'] and sent[1]['image_url']['url'].startswith('data:image/png;base64,')
    W(op='media_make', text='just a beach', tools={'kind': 'image', 'model': 'or-nano-banana', 'noChar': True})
    assert 'refs' not in doc['messages'][-1]['media'] and mg.ref_content('x', []) == 'x'
