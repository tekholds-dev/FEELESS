"""📮 POC-PLAY item 8: a picked week board goes out through Postiz (network faked — nothing ever posts from a test)."""
import asyncio
import datetime as dt

import pytest

import postiz as pz

CHANS = [{'id': 'i-x', 'name': 'FEELESS on X', 'identifier': 'x', 'disabled': False},
         {'id': 'i-ig', 'name': 'feeless.ig', 'identifier': 'instagram-standalone', 'disabled': False},
         {'id': 'i-li', 'name': 'old page', 'identifier': 'linkedin', 'disabled': True}]


class Resp:
    def __init__(self, code, j):
        self.status_code = code; self._j = j

    def json(self):
        return self._j


class FakeHttp:
    def __init__(self, chans=CHANS, code=200):
        self.calls = []; self.chans = chans; self.code = code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None):
        self.calls.append(('GET', url, headers, None))
        return Resp(self.code, self.chans if self.code == 200 else {'msg': 'No API Key found'})

    async def post(self, url, headers=None, json=None, files=None):
        self.calls.append(('POST', url, headers, json or files))
        if url.endswith('/upload'):
            return Resp(201, {'id': 'up1', 'path': 'https://uploads.postiz.com/up1.png'})
        return Resp(201, [{'postId': f'p{len(self.calls)}', 'integration': json['posts'][0]['integration']['id']}])


def test_keys_channels_settings_and_times():
    assert pz.split_key('abcdefghijklmnop1234') == (pz.CLOUD, 'abcdefghijklmnop1234')
    assert pz.split_key('https://postiz.me.dev/public/v1/ pos_abcdefghijklmnop') == ('https://postiz.me.dev/public/v1', 'pos_abcdefghijklmnop')
    with pytest.raises(ValueError):
        pz.split_key('http://10.0.0.1 abcdefghijklmnop1234')
    assert pz.channel_for(CHANS, 'instagram')['id'] == 'i-ig'
    assert pz.channel_for(CHANS, 'linkedin') is None          # a disabled channel is never used
    assert pz.settings_for('youtube', 'youtube', 'x')['title'] == 'New video'
    mon = pz.next_monday(dt.date(2026, 11, 13))               # a Friday → the coming Monday
    assert mon == dt.date(2026, 11, 16) and pz.next_monday(mon) == dt.date(2026, 11, 23)
    t = pz.when({'day': 'Wed', 'time': '09:30'}, mon, tz_min=300)   # browser 5 h behind UTC
    assert t.isoformat() == '2026-11-18T14:30:00+00:00'


def test_plan_skips_what_cannot_go_and_says_why():
    posts = [{'day': 'Mon', 'platform': 'x', 'time': '09:00', 'caption': 'gm'},
             {'day': 'Tue', 'platform': 'instagram', 'time': '10:00', 'caption': 'no pic'},
             {'day': 'Wed', 'platform': 'linkedin', 'time': '10:00', 'caption': 'off channel'}]
    go, skip = pz.plan(posts, CHANS, dt.date(2026, 11, 16), 0, dt.datetime(2026, 11, 13, tzinfo=dt.timezone.utc), lambda p: False)
    assert [g[0] for g in go] == [0]
    assert {(i, why) for i, _pl, why in skip} == {(1, 'needs a picture or clip'), (2, 'no connected channel in Postiz')}
    late = pz.plan(posts[:1], CHANS, dt.date(2026, 11, 16), 0, dt.datetime(2026, 11, 17, tzinfo=dt.timezone.utc), lambda p: True)
    assert late[0] == [] and late[1][0][2] == 'that time has passed'


def test_the_owner_sends_his_week_through_his_own_postiz(monkeypatch, tmp_path):
    import feecat_service as fs
    week = {'idea': 'launch', 'style': 'launch', 'posts': [
        {'day': 'Mon', 'platform': 'x', 'time': '09:00', 'caption': 'gm FEELESS'},
        {'day': 'Tue', 'platform': 'instagram', 'time': '12:00', 'caption': 'the terminal', 'media': 'm1'},
        {'day': 'Wed', 'platform': 'tiktok', 'time': '18:00', 'caption': 'no tiktok connected'}]}
    cat = {'id': 'c1', 'pocFolders': [{'id': 'poc1', 'n': 1, 'kind': 'PoC', 'week': week, 'media': [{'id': 'm1', 'kind': 'image', 'url': '/api/cats/media/c1/m1.png'}]}], 'chat': []}
    store = {'cats': {'c1': cat}}
    (tmp_path / 'c1').mkdir(); (tmp_path / 'c1' / 'm1.png').write_bytes(b'\x89PNG\r\n\x1a\nfake')
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None); monkeypatch.setattr(fs, '_media_dir', lambda: tmp_path)
    keys = {}
    monkeypatch.setattr(fs._ck, 'key_for', lambda c, prov, **k: keys.get(prov))
    run = lambda **kw: asyncio.run(fs._cat_work('c1', fs.WorkPayload(session='s', **kw)))
    with pytest.raises(fs.HTTPException) as e:                # no key saved → nothing is called
        run(op='week_post', job='poc1')
    assert 'Postiz API key' in e.value.detail
    keys['postiz'] = 'abcdefghijklmnop1234'
    http = FakeHttp(); monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **k: http)
    assert [c['platform'] for c in run(op='postiz_channels')['channels']] == ['x', 'instagram-standalone', 'linkedin']
    out = run(op='week_post', job='poc1', tools={'start': '2030-01-07', 'tz': 0, 'mode': 'draft'})
    posted = out['posted']
    assert posted['sent'] == 2 and posted['mode'] == 'draft' and [s['platform'] for s in posted['skipped']] == ['tiktok']
    sends = [c for c in http.calls if c[1].endswith('/posts')]
    assert all(c[2] == {'Authorization': 'abcdefghijklmnop1234'} for c in http.calls)
    assert sends[0][3]['type'] == 'draft' and sends[0][3]['date'] == '2030-01-07T09:00:00.000Z' and sends[0][3]['posts'][0]['settings']['__type'] == 'x'
    ig = sends[1][3]['posts'][0]
    assert ig['integration'] == {'id': 'i-ig'} and ig['value'][0]['image'] == [{'id': 'up1', 'path': 'https://uploads.postiz.com/up1.png'}]
    assert sum(1 for c in http.calls if c[1].endswith('/upload')) == 1
    with pytest.raises(fs.HTTPException) as e:                # no accidental second send
        run(op='week_post', job='poc1', tools={'start': '2030-01-07'})
    assert e.value.status_code == 409
    with pytest.raises(fs.HTTPException) as e:                # the week starts on a Monday
        run(op='week_post', job='poc1', tools={'start': '2030-01-08', 'again': True})
    assert e.value.status_code == 400
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda **k: FakeHttp(code=401))
    with pytest.raises(fs.HTTPException) as e:
        run(op='postiz_channels')
    assert 'refused the key' in e.value.detail
