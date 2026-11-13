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
