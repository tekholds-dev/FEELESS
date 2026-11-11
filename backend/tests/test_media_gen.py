"""🎬 PoC images and video on the owner's own fal.ai / Replicate key: picks, guards, a whole job (submit → poll → keep the file),
failures said plainly, and the key never sent to the file's own link."""
import asyncio
import json

import pytest

import cat_keys as ck
import media_gen as mg
from test_play_studio import _server

FAL_KEY = 'abcdef12-3456-7890-abcd-ef1234567890:' + 'f' * 32
REP_KEY = 'r8_' + 'A' * 37


def test_picks_only_what_a_linked_provider_runs():
    c = mg.catalog({'fal'})
    assert c['pick'] == {'image': 'fal-flux-schnell', 'video': 'fal-wan22-5b'} and c['linked'] == ['fal']
    assert all(r['ready'] == (r['provider'] == 'fal') for r in c['models'])
    assert mg.catalog(set())['pick'] == {'image': None, 'video': None}
    assert mg.choose(None, 'video', {'replicate'})[:3] == ('rep-wan22-fast', 'replicate', 'wan-video/wan-2.2-t2v-fast')
    for args, why in (((None, 'video', set()), 'Link OpenRouter, fal.ai or Replicate'), (('fal-wan22-5b', 'video', {'replicate'}), 'Link fal.ai first'),
                      (('fal-flux-schnell', 'video', {'fal'}), 'makes images'), ((None, 'audio', {'fal'}), 'image or video')):
        with pytest.raises(ValueError, match=why):
            mg.choose(*args)
    assert mg.clean_prompt('  a   rat  in a  graveyard ') == 'a rat in a graveyard'
    with pytest.raises(ValueError):
        mg.clean_prompt('x')


def test_provider_shapes():
    assert mg.submit_req('fal', 'fal-ai/wan/v2.2-5b/text-to-video', 'p', 'K')[1:] == ('https://queue.fal.run/fal-ai/wan/v2.2-5b/text-to-video', {'Authorization': 'Key K', 'Content-Type': 'application/json'}, {'prompt': 'p'})
    assert mg.submit_req('replicate', 'wan-video/wan-2.2-t2v-fast', 'p', 'K')[1] == 'https://api.replicate.com/v1/models/wan-video/wan-2.2-t2v-fast/predictions'
    assert mg.handle_of('fal', {'status_url': 's', 'response_url': 'r', 'request_id': 'x'}) == {'status': 's', 'result': 'r', 'rid': 'x'}
    with pytest.raises(ValueError, match='Authentication'):
        mg.handle_of('fal', {'detail': 'Authentication is required'})
    assert mg.state_of('fal', {'status': 'IN_PROGRESS'}) == ('running', 'in_progress') and mg.state_of('fal', {'status': 'COMPLETED'}) == ('done', '')
    assert mg.state_of('replicate', {'status': 'failed', 'error': 'NSFW'}) == ('failed', 'NSFW') and mg.state_of('replicate', {'status': 'succeeded'}) == ('done', '')
    assert mg.output_url('fal', 'video', {'video': {'url': 'https://v.fal.media/a.mp4'}}) == 'https://v.fal.media/a.mp4'
    assert mg.output_url('fal', 'image', {'images': [{'url': 'https://v.fal.media/a.png'}]}) == 'https://v.fal.media/a.png'
    assert mg.output_url('replicate', 'video', {'output': 'https://replicate.delivery/x.mp4'}) == 'https://replicate.delivery/x.mp4'
    assert mg.output_url('replicate', 'image', {'output': ['https://replicate.delivery/x.webp']}).endswith('.webp') and mg.output_url('replicate', 'image', {'output': 'file:///etc/passwd'}) is None
    assert mg.ext_of('video', 'https://x/a.mp4?sig=1') == 'mp4' and mg.ext_of('image', 'https://x/a', 'image/webp') == 'webp' and mg.ext_of('image', 'https://x/a.jpeg') == 'jpg'


class _R:
    def __init__(self, status, body=None, raw=b''):
        self.status_code, self._b, self._raw = status, body, raw
        self.headers = {'content-type': 'application/json' if body is not None else 'video/mp4'}

    def json(self):
        return self._b

    async def aiter_bytes(self):
        yield self._raw

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass


def _fake_http(monkeypatch, fs, script):
    calls = []
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, meth, url, headers=None, json=None):
            calls.append(('submit', url, headers)); return script['submit']
        async def get(self, url, headers=None):
            calls.append(('get', url, headers)); return script['polls'].pop(0) if url.endswith('/status') else script['result']
        def stream(self, meth, url):
            calls.append(('file', url, None)); return script['file']
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **kw: H())
    monkeypatch.setattr(fs._mg, 'POLL_S', 0)
    return calls


def _poc(fs, store, tmp_path, key=FAL_KEY, provider='fal'):
    cat = store['cats']['g']; ck.put(cat, provider, key, data_dir=tmp_path)
    row = fs._feat.new_folder(cat, 'content', 'GONE', 1.0); fs._ws_save('g', fs._feat.new_doc(row))
    return row['id']


def test_a_whole_video_job_keeps_the_file_and_never_sends_the_key_to_it(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path); ws = _poc(fs, store, tmp_path); real = fs._media_run
    started = []
    async def no_run(*a): started.append(a)
    monkeypatch.setattr(fs, '_media_run', no_run)
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', **kw})
    assert post(op='media_models').json()['pick']['video'] == 'fal-wan22-5b'
    r = post(op='media_make', job=ws, text='a chrome rat dancing on a tombstone', tools={'kind': 'video'})
    assert r.status_code == 200, r.text
    md = r.json()['doc']['messages'][-1]['media']
    assert (md['status'], md['provider'], md['model'], md['usd'], md['label']) == ('queued', 'fal', 'fal-ai/wan/v2.2-5b/text-to-video', 0.15, 'Wan 2.2 5B') and started
    calls = _fake_http(monkeypatch, fs, {'submit': _R(200, {'request_id': 'q1', 'status_url': 'https://queue.fal.run/x/requests/q1/status', 'response_url': 'https://queue.fal.run/x/requests/q1'}),
                                         'polls': [_R(200, {'status': 'IN_QUEUE'}), _R(200, {'status': 'IN_PROGRESS'}), _R(200, {'status': 'COMPLETED'})],
                                         'result': _R(200, {'video': {'url': 'https://v3.fal.media/files/rat.mp4'}}), 'file': _R(200, None, b'MP4DATA')})
    asyncio.run(real('g', ws, md['id']))
    done = [m for m in fs._ws_load('g', ws)['messages'] if m.get('media')][-1]['media']
    assert done['status'] == 'done' and done['kept'] is True and done['url'] == f"/api/cats/media/g/{md['id']}.mp4" and done['bytes'] == 7
    assert (tmp_path / 'media' / 'g' / f"{md['id']}.mp4").read_bytes() == b'MP4DATA'
    assert [x[0] for x in calls] == ['submit', 'get', 'get', 'get', 'get', 'file'] and calls[-1][2] is None   # the file's own link never gets the key
    assert calls[0][2]['Authorization'] == f'Key {FAL_KEY}'
    got = c.get(done['url']); assert got.status_code == 200 and got.content == b'MP4DATA'
    assert c.get('/api/cats/media/g/..%2Fsecrets.mp4').status_code == 404 and c.get('/api/cats/media/g/m123.mp4').status_code == 404


def test_guards_and_plain_failures(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    post = lambda **kw: c.post('/api/cats/g/work', json={'ownerId': 'g', 'session': 'g', **kw})
    row = fs._feat.new_folder(store['cats']['g'], 'content', 'X', 1.0); fs._ws_save('g', fs._feat.new_doc(row))
    r = post(op='media_make', job=row['id'], text='a rat', tools={'kind': 'video'})
    assert r.status_code == 400 and 'Link OpenRouter, fal.ai or Replicate' in r.json()['detail']   # nothing linked: told how, nothing queued
    b = fs._feat.new_folder(store['cats']['g'], 'build', 'B', 1.0); fs._ws_save('g', fs._feat.new_doc(b))
    assert post(op='media_make', job=b['id'], text='a rat', tools={'kind': 'image'}).status_code == 400   # PoC folders only
    ws = _poc(fs, store, tmp_path, REP_KEY, 'replicate'); real = fs._media_run
    async def no_run(*a): pass
    monkeypatch.setattr(fs, '_media_run', no_run)
    md = post(op='media_make', job=ws, text='a rat', tools={'kind': 'image'}).json()['doc']['messages'][-1]['media']
    _fake_http(monkeypatch, fs, {'submit': _R(422, {'detail': 'Invalid input'}), 'polls': [], 'result': None, 'file': None})
    asyncio.run(real('g', ws, md['id']))
    m = [x for x in fs._ws_load('g', ws)['messages'] if x.get('media')][-1]['media']
    assert m['status'] == 'failed' and '422' in m['why'] and 'Invalid input' in m['why']
