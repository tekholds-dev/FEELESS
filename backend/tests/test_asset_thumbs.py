"""🖼 Every 3D studio search result has a picture: Poly Haven's own, or an Objaverse model's Sketchfab picture looked up once and kept."""
import asyncio

import asset_packs as a


def test_each_kind_of_row_gets_its_picture():
    assert a.thumb_of({'id': 'ox-' + 'a' * 32, 'url': 'https://huggingface.co/x.glb'}) == '/api/cats/assets/thumb/' + 'a' * 32
    assert a.thumb_of({'id': 'barrel_02'}).startswith('https://cdn.polyhaven.com/')
    assert a.thumb_of({'id': 'cc0-x', 'url': 'https://raw.githubusercontent.com/ToxSam/x.glb', 'thumb': 'https://raw.githubusercontent.com/ToxSam/t.png'}).endswith('t.png')
    assert a.thumb_of({'id': 'cc0-y', 'url': 'https://raw.githubusercontent.com/ToxSam/y.glb'}) == ''


def test_lookup_is_kept_and_a_gone_model_is_remembered(tmp_path):
    calls = []

    class R:
        def __init__(self, code, j=None): self.status_code, self._j = code, j or {}
        def json(self): return self._j

    class H:
        async def get(self, url, headers=None, timeout=None):
            calls.append(url)
            if url.endswith('b' * 32):
                return R(404)
            return R(200, {'thumbnails': {'images': [{'width': 1024, 'url': 'https://media.sketchfab.com/big.jpeg'}, {'width': 256, 'url': 'https://media.sketchfab.com/256.jpeg'}, {'width': 200, 'url': 'https://evil.example/x.jpeg'}]}})

    run = lambda uid: asyncio.run(a.sketchfab_thumb(H(), tmp_path, uid))
    assert run('a' * 32) == 'https://media.sketchfab.com/256.jpeg' and run('a' * 32) == 'https://media.sketchfab.com/256.jpeg'
    assert run('b' * 32) == '' and run('b' * 32) == '' and len(calls) == 2
    assert run('../../etc/passwd') == '' and len(calls) == 2
