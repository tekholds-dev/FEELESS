"""🎭 Slice 4 (owner 2026-11-18): drop in a video → the same video with a realistic AI-made person in place, no watermark, filed into the PoC
folder with the before / after side by side and its cost. Runs on FEELESS's own HQ › Core keys (fal MiniMax H3 Max Recast, runner-up Runway
Aleph 2 on OpenRouter), only for the owner and staff agents, only at the price he saw, never sent twice. Every provider call and ffmpeg run is faked."""
import asyncio
import base64
import json

import pytest

import media_gen as mg
import provider_ready as pr
import video_swap as vs
from test_media_gen import _R
from test_play_studio import _server

MP4 = b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 80
FAL = 'abcd1234-ef56:0123456789abcdef0123456789abcdef'
ORK = 'sk-or-v1-' + 'a' * 40


# ── pure ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_prices_follow_each_engines_own_billing():
    # H3 Recast 768p: $0.085/s (5 s minimum) + 6,750 input tokens/s at $0.022 per 1,000 after the first 4,096
    assert vs.swap_usd('fal-h3-recast', 10, '768P') == round(0.85 + (67500 - 4096) * 0.022 / 1000, 2) == 2.24
    assert vs.swap_usd('fal-h3-recast', 10, '1080P') == 3.09
    assert vs.swap_usd('fal-h3-recast', 5, None) == round(0.425 + (33750 - 4096) * 0.022 / 1000, 2)   # 768p is the default (owner 2026-11-18)
    assert vs.swap_usd('or-aleph', 15) == 2.8 and vs.swap_usd('or-aleph', 1) == 0.56   # first 10 s at 28¢, 56¢ minimum
    q = vs.quote('fal-h3-recast', 10, '768P', make_person=True)
    assert q['usd'] == round(2.24 + 0.035, 2) and q['person'] == 0.035 and len(q['lines']) == 2
    assert vs.quote('or-aleph', 10, None, False)['lines'] == [{'what': 'Runway Aleph 2 · 10.0 s', 'usd': 2.8}]


def test_clip_lengths_each_engine_takes():
    assert vs.fits('fal-h3-recast', 3) and 'at least' in vs.fits('fal-h3-recast', 3)
    assert vs.fits('fal-h3-recast', 31) and not vs.fits('fal-h3-recast', 30.2)
    assert not vs.fits('or-aleph', 3) and vs.made_secs('or-aleph', 25) == 10
    assert vs.auto_engine({'fal-h3-recast': True, 'or-aleph': True}, 3) == 'or-aleph'   # too short for H3 → the runner-up
    assert vs.auto_engine({'fal-h3-recast': False, 'or-aleph': True}) == 'or-aleph' and vs.auto_engine({}) is None


def test_requests_match_the_providers_schemas_and_carry_no_watermark():
    _, url, h, b = vs.swap_req('fal-h3-recast', FAL, 'https://x/v.mp4', 'https://x/p.jpg', 'keep the gold chain', '768P')
    assert url == 'https://queue.fal.run/minimax/h3-max/recast' and h['Authorization'] == f'Key {FAL}'
    assert b['video_url'] == 'https://x/v.mp4' and b['reference_image_urls'] == ['https://x/p.jpg'] and b['resolution'] == '768P' and b['enhance_realism'] is True
    assert 'keep the gold chain' in b['prompt'] and len(b['prompt']) <= 2000
    assert set(b) <= {'video_url', 'reference_image_urls', 'prompt', 'resolution', 'seed', 'enhance_realism', 'enable_safety_checker'}   # fal's own schema, read 2026-11-18
    _, url, h, b = vs.swap_req('or-aleph', ORK, 'https://x/v.mp4', 'https://x/p.jpg', '', None, '9:16')
    assert url.endswith('/api/v1/videos') and b['model'] == 'runway/aleph-2' and b['provider']['options']['runway']['keyframes'][0]['uri'] == 'https://x/p.jpg'
    _, url, _, b = vs.portrait_req('fal', FAL, 'a woman in her 30s, short red hair')
    assert url.endswith('/seedream/v5/lite/text-to-image') and b['watermark'] is False and 'fictional adult person who does not exist' in b['prompt']
    _, url, _, b = vs.portrait_req('openrouter', ORK, 'a tall man, grey suit')
    assert url.endswith('/chat/completions') and b['modalities'] == ['image', 'text']
    with pytest.raises(ValueError):
        vs.portrait_prompt('  ')
    with pytest.raises(ValueError):
        vs.swap_req('nope', FAL, 'v', 'i')


def test_the_key_comes_from_hq_core_env_or_its_dotenv_and_only_names_leave(tmp_path):
    env = tmp_path / '.env'; env.write_text(f'OTHER=1\nFAL_KEY="{FAL}"\n')
    assert vs.env_key('FAL_KEY', {}, env) == FAL and vs.env_key('FAL_KEY', {'FAL_KEY': 'k:v'}, env) == 'k:v'
    assert vs.ready({}, env) == {'fal-h3-recast': True, 'or-aleph': False}
    assert vs.env_key('FAL_KEY', {}, tmp_path / 'missing') == ''
    rows = {r['name']: r for r in pr.status({'FAL_KEY': FAL})['rows']}
    assert rows['fal.ai']['ready'] and rows['fal.ai']['keys'] == ['FAL_KEY'] and FAL not in json.dumps(rows)   # HQ › Core › Provider keys
    assert pr.clean_key('FAL_KEY', FAL) == ('FAL_KEY', FAL)


def test_the_new_person_is_always_ai_made():
    made = {'character': {'mid': 'm1'}, 'messages': [{'media': {'id': 'm1', 'kind': 'image', 'status': 'done', 'provider': 'openrouter', 'url': '/api/cats/media/g/m1.png'}}]}
    assert vs.person_of(made)['source'] == 'character'
    up = {'character': {'mid': 'm1'}, 'messages': [{'media': {'id': 'm1', 'kind': 'image', 'status': 'done', 'provider': 'upload', 'url': '/api/cats/media/g/m1.png'}}]}
    assert vs.person_of(up) is None   # an uploaded photo is never the new person


def test_the_filed_record_has_before_after_side_by_side_and_cost():
    job = {'id': 'vabc', 'ws': 'w1', 'engine': 'fal-h3-recast', 'res': '768P', 'at': 100, 'secs': 10, 'quote': vs.quote('fal-h3-recast', 10, '768P'),
           'before': {'url': '/b.mp4', 'label': 'Dance'}, 'after': {'url': '/a.mp4'}, 'side': '/s.mp4', 'person': {'source': 'made'}, 'paid': 'FEELESS key'}
    r = vs.record(job, 4, 160)
    assert r['kind'] == 'PoC' and r['n'] == 4 and r['cost'] == 2.24 and r['swap']['before']['url'] == '/b.mp4' and r['swap']['after']['url'] == '/a.mp4'
    assert r['swap']['side'] == '/s.mp4' and r['swap']['watermark'] == 'none' and r['swap']['runnerUp'] == 'Runway Aleph 2' and r['swap']['tookS'] == 60
    assert [m['url'] for m in r['media']] == ['/a.mp4', '/s.mp4'] and r['calls'] == [] and r['by'] == 'Video swap'


def test_side_by_side_args_stack_before_left_after_right_with_the_clips_sound():
    a = vs.side_args('b.mp4', 'a.mp4', 'o.mp4', 721)
    fc = a[a.index('-filter_complex') + 1]
    assert 'scale=-2:720' in fc and 'hstack=inputs=2:shortest=1' in fc and a[a.index('-i') + 1] == 'b.mp4' and '1:a?' in a


# ── wired: press → checks → run → filed (network + ffmpeg faked) ─────────────────────────────────────────────────────────────────────

def _setup(monkeypatch, tmp_path, staff=True, character=True, secs=10.0, keys=('FAL_KEY',)):
    fs, c, store = _server(monkeypatch, tmp_path)
    import video_swap_run as vsr
    cat = store['cats']['g']; cat['ownerStaff'] = staff
    for k in ('FAL_KEY', 'OPENROUTER_API_KEY'):
        monkeypatch.delenv(k, raising=False)
    if 'FAL_KEY' in keys:
        monkeypatch.setenv('FAL_KEY', FAL)
    if 'OPENROUTER_API_KEY' in keys:
        monkeypatch.setenv('OPENROUTER_API_KEY', ORK)
    monkeypatch.setattr(vsr, 'DOTENV', tmp_path / 'none.env'); monkeypatch.setattr(vsr, 'POLL_S', 0)
    row = fs._feat.new_folder(cat, 'content', 'Dance trend', 1.0); doc = fs._feat.new_doc(row)
    d = tmp_path / 'media' / 'g'; d.mkdir(parents=True, exist_ok=True)
    (d / 'mcccccccccccc.mp4').write_bytes(MP4); (d / 'maaaaaaaaaaa1.png').write_bytes(b'\x89PNGperson')
    doc['messages'] = [{'by': 'Media', 'text': 'Dance', 'at': 1, 'media': {'id': 'mcccccccccccc', 'kind': 'video', 'provider': 'upload', 'clip': True, 'status': 'done',
                                                                           'label': 'Dance', 'secs': secs, 'fps': 30, 'w': 720, 'h': 1280, 'url': '/api/cats/media/g/mcccccccccccc.mp4'}}]
    if character:
        doc['messages'].append({'by': 'Media', 'text': 'Her', 'at': 2, 'media': {'id': 'maaaaaaaaaaa1', 'kind': 'image', 'status': 'done', 'provider': 'openrouter',
                                                                                 'url': '/api/cats/media/g/maaaaaaaaaaa1.png', 'prompt': 'a woman, red hair'}})
        doc['character'] = {'mid': 'maaaaaaaaaaa1', 'url': '/api/cats/media/g/maaaaaaaaaaa1.png'}
    fs._ws_save('g', doc)
    ran = []
    async def ffmpeg(args, timeout=180):
        ran.append(list(args)); open(args[-1], 'wb').write(b'OUT' + args[-1].encode()[-8:]); return 0, b''
    async def clip_len(p):
        return secs, 30.0
    async def clip_size(p):
        return 720, 1280
    async def tunnel(_d):
        return 'https://t.trycloudflare.com'
    monkeypatch.setattr(fs, '_ffmpeg', ffmpeg); monkeypatch.setattr(fs, '_clip_len', clip_len); monkeypatch.setattr(fs, '_clip_size', clip_size)
    monkeypatch.setattr(fs, '_public_site', lambda: ''); monkeypatch.setattr(fs._pubt, 'ensure', tunnel)
    started = []
    async def no_run(cat_id, jid):
        started.append(jid)
    real_run = vsr.run; monkeypatch.setattr(vsr, 'run', no_run)
    return fs, c, store, vsr, row['id'], ran, started, real_run


def _post(c, ws, **kw):
    return c.post('/api/cats/g/vswap', json={'ownerId': 'g', 'session': 'g', 'ws': ws, **kw})


def _fake_fal(monkeypatch, vsr, sent):
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, meth, url, headers=None, json=None, timeout=None):
            sent.append((url, headers, json))
            return _R(200, {'request_id': 'q', 'status_url': 'https://queue.fal.run/minimax/h3-max/recast/requests/q/status', 'response_url': 'https://queue.fal.run/minimax/h3-max/recast/requests/q'})
        async def get(self, url, headers=None):
            sent.append((url, headers, None))
            return _R(200, {'status': 'COMPLETED'}) if url.endswith('/status') else _R(200, {'video': {'url': 'https://v3.fal.media/files/recast.mp4'}, 'seed': 7})
        def stream(self, meth, url, **kw):
            sent.append((url, kw.get('headers'), None)); return _R(200, None, b'RECAST')
    monkeypatch.setattr(vsr.httpx, 'AsyncClient', lambda **kw: H())


def test_the_plan_shows_engines_keys_by_name_and_a_price_per_clip(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, *_ = _setup(monkeypatch, tmp_path)
    r = c.get(f'/api/cats/g/vswap?ws={ws}&ownerId=g&session=g'); assert r.status_code == 200, r.text
    j = r.json()
    assert {e['id']: e['ready'] for e in j['engines']} == {'fal-h3-recast': True, 'or-aleph': False} and j['auto'] == 'fal-h3-recast' and j['allowed']
    assert j['person']['source'] == 'character' and j['res'] == '768P'
    qq = j['clips'][0]['quote']
    assert qq['fal-h3-recast']['768P']['char']['usd'] == 2.24 and qq['or-aleph']['std']['char']['usd'] == 2.8 and qq['fal-h3-recast']['768P']['make']['usd'] == round(2.24 + 0.035, 2)
    assert FAL not in r.text and ORK not in r.text
    assert c.get(f'/api/cats/g/vswap?ws={ws}&ownerId=x&session=x').status_code == 403   # only its owner


def test_only_staff_with_a_key_at_the_price_seen_under_the_caps(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, ran, started, _ = _setup(monkeypatch, tmp_path, staff=False)
    base = dict(clip='mcccccccccccc', engine='fal-h3-recast', res='768P', person='character', usd=2.24)
    r = _post(c, ws, **base); assert r.status_code == 403 and 'staff' in r.json()['detail']
    store['cats']['g']['ownerStaff'] = True
    assert _post(c, ws, **{**base, 'engine': 'or-aleph', 'usd': 2.8}).status_code == 400   # no OpenRouter key in HQ › Core
    assert 'HQ › Core' in _post(c, ws, **{**base, 'engine': 'or-aleph', 'usd': 2.8}).json()['detail']
    r = _post(c, ws, **{**base, 'usd': 1.0}); assert r.status_code == 409 and '$2.24' in r.json()['detail']   # the price on screen is the price that runs
    store['cats']['g']['swapCapUsd'] = 2.0
    r = _post(c, ws, **base); assert r.status_code == 400 and 'cap per swap' in r.json()['detail']
    store['cats']['g']['swapCapUsd'] = 3.0
    monkeypatch.setattr(vs, 'DAY_CAP_USD', 2.0)
    r = _post(c, ws, **base); assert r.status_code == 429 and 'day cap' in r.json()['detail']
    monkeypatch.setattr(vs, 'DAY_CAP_USD', 10.0)
    assert _post(c, ws, **{**base, 'person': 'make', 'words': ''}).status_code == 400   # a made person needs words
    assert not started and not vsr._jobs()   # nothing booked, nothing sent
    r = _post(c, ws, **base); assert r.status_code == 200, r.text
    assert r.json()['job']['step'] == 'sending' and started == [r.json()['job']['id']]


def test_a_press_runs_end_to_end_and_files_before_after_and_cost(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, ran, started, real_run = _setup(monkeypatch, tmp_path)
    j = _post(c, ws, clip='mcccccccccccc', engine='fal-h3-recast', res='768P', person='character', usd=2.24, note='keep the gold chain').json()['job']
    sent = []; _fake_fal(monkeypatch, vsr, sent)
    asyncio.run(real_run('g', j['id']))
    job = vsr._jobs()[j['id']]
    assert job['step'] == 'filed', job.get('why')
    url, heads, body = sent[0]
    assert url == 'https://queue.fal.run/minimax/h3-max/recast' and heads['Authorization'] == f'Key {FAL}'
    assert body['video_url'].startswith('https://t.trycloudflare.com/g/pub/') and body['reference_image_urls'][0].endswith('.jpg') and 'keep the gold chain' in body['prompt']
    assert not [x for x in sent if x[0] == 'https://v3.fal.media/files/recast.mp4' and x[1]]   # a provider's file link never gets the key
    after = tmp_path / 'media' / 'g' / f"{job['after']['mid']}.mp4"
    assert after.is_file()
    kinds = [a for a in ran if 'hstack=inputs=2:shortest=1' in ' '.join(a)]; assert kinds   # the side by side was made
    assert any('-map' in a and '1:a:0' in a for a in ran)   # the clip's own sound laid back
    row = store['cats']['g']['pocFolders'][-1]
    assert row['by'] == 'Video swap' and row['cost'] == 2.24 and row['swap']['before']['url'] == '/api/cats/media/g/mcccccccccccc.mp4'
    assert row['swap']['after']['url'] == job['after']['url'] and row['swap']['side'] == job['side'] and row['swap']['engine'] == 'MiniMax H3 Max · Recast'
    assert row['swap']['watermark'] == 'none' and 'recordError' not in row   # 🧾 the true record (Slice 0) stamped it
    rec = [json.loads(x) for x in (tmp_path / 'model_receipts.jsonl').read_text().splitlines()]
    assert rec[-1]['usd'] == 2.24 and rec[-1]['funding'] == 'FEELESS key' and rec[-1]['cat'] == 'g'
    board = [m['media'] for m in fs._ws_load('g', ws)['messages'] if (m.get('media') or {}).get('vswap')]
    assert [b['label'] for b in board] == ['MiniMax H3 Max · Recast swap', 'Before | after']
    assert FAL not in (tmp_path / 'video_swaps.json').read_text()   # the key is never written down
    assert vs.day_spent(vsr._jobs(), 0) == 2.24


def test_the_runner_up_makes_the_person_first_on_openrouter(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, ran, started, real_run = _setup(monkeypatch, tmp_path, character=False, secs=12.0, keys=('OPENROUTER_API_KEY',))
    q = vs.quote('or-aleph', 12, None, True)['usd']
    j = _post(c, ws, clip='mcccccccccccc', engine='or-aleph', person='make', words='a tall man in his 40s, grey suit', usd=q).json()['job']
    pic = 'data:image/png;base64,' + base64.b64encode(b'\x89PNGmade').decode(); sent = []
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, meth, url, headers=None, json=None, timeout=None):
            sent.append((url, json))
            if url.endswith('/chat/completions'):
                return _R(200, {'choices': [{'message': {'images': [{'image_url': {'url': pic}}]}}]})
            return _R(200, {'id': 'vid1', 'polling_url': 'https://openrouter.ai/api/v1/videos/vid1'})
        async def get(self, url, headers=None):
            return _R(200, {'status': 'completed'})
        def stream(self, meth, url, **kw):
            sent.append((url, kw.get('headers'))); return _R(200, None, b'ALEPH')
    monkeypatch.setattr(vsr.httpx, 'AsyncClient', lambda **kw: H())
    asyncio.run(real_run('g', j['id']))
    job = vsr._jobs()[j['id']]
    assert job['step'] == 'filed', job.get('why')
    assert sent[0][0].endswith('/chat/completions') and 'grey suit' in json.dumps(sent[0][1])
    assert sent[1][1]['model'] == 'runway/aleph-2' and sent[1][1]['provider']['options']['runway']['keyframes'][0]['uri'].endswith('.jpg')
    assert sent[2][0].endswith('/videos/vid1/content') and sent[2][1]['Authorization'] == f'Bearer {ORK}'
    assert (tmp_path / 'media' / 'g' / f"{job['person']['mid']}.jpg").read_bytes() == b'\x89PNGmade'
    row = store['cats']['g']['pocFolders'][-1]
    assert row['cost'] == q and row['swap']['person']['source'] == 'made' and row['swap']['runnerUp'] == 'MiniMax H3 Max · Recast'


def test_a_job_sent_once_is_never_sent_again_after_a_restart(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, ran, started, real_run = _setup(monkeypatch, tmp_path)
    j = _post(c, ws, clip='mcccccccccccc', engine='fal-h3-recast', res='768P', person='character', usd=2.24).json()['job']
    job = vsr._jobs()[j['id']]; vsr._set(job, step='submitted')   # the call went out, its answer was lost
    sent = []; _fake_fal(monkeypatch, vsr, sent)
    asyncio.run(real_run('g', j['id']))
    job = vsr._jobs()[j['id']]
    assert job['step'] == 'failed' and 'not sent again' in job['why'] and not sent and job['taken']
    assert vs.day_spent(vsr._jobs(), 0) == 2.24   # it may have been charged, so it still counts on the day cap


def test_a_provider_refusal_says_what_happened_and_files_nothing(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, ran, started, real_run = _setup(monkeypatch, tmp_path)
    j = _post(c, ws, clip='mcccccccccccc', engine='fal-h3-recast', res='768P', person='character', usd=2.24).json()['job']
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, *a, **kw):
            return _R(402, {'detail': 'Insufficient balance'})
    monkeypatch.setattr(vsr.httpx, 'AsyncClient', lambda **kw: H())
    asyncio.run(real_run('g', j['id']))
    job = vsr._jobs()[j['id']]
    assert job['step'] == 'failed' and 'out of credit' in job['why'] and not store['cats']['g'].get('pocFolders')
    assert mg.plain_why(402, 'Insufficient balance').startswith('Your provider account is out of credit')


def test_with_no_hq_key_the_owners_own_openrouter_key_runs_it_on_his_own_day_cap(monkeypatch, tmp_path):
    import cat_keys as ck
    fs, c, store, vsr, ws, ran, started, real_run = _setup(monkeypatch, tmp_path, keys=())
    ck.put(store['cats']['g'], 'openrouter', ORK, data_dir=tmp_path)
    j = c.get(f'/api/cats/g/vswap?ws={ws}&ownerId=g&session=g').json()
    eng = {e['id']: e for e in j['engines']}
    assert eng['or-aleph']['ready'] and eng['or-aleph']['keyFrom'] == 'Your own OpenRouter key (on your agents)' and not eng['fal-h3-recast']['ready']
    assert ORK not in json.dumps(j)
    monkeypatch.setattr(vs, 'DAY_CAP_USD', 0.5)   # FEELESS's swap day cap does not apply to his own key …
    def over(cat, usd, store=None):
        raise fs._sg.OverCap('Your agents are at $9.90 of your $10.00 day cap.')
    monkeypatch.setattr(fs, '_spend_check', over)   # … his own day cap does
    r = _post(c, ws, clip='mcccccccccccc', engine='or-aleph', person='character', usd=2.8); assert r.status_code == 429 and 'your $10.00 day cap' in r.json()['detail']
    monkeypatch.setattr(fs, '_spend_check', lambda cat, usd, store=None: None)
    r = _post(c, ws, clip='mcccccccccccc', engine='or-aleph', person='character', usd=2.8); assert r.status_code == 200, r.text
    jid = r.json()['job']['id']; assert r.json()['job']['paid'] == 'Your own OpenRouter key (on your agents)' and fs._SPEND_HOLD.get(jid)
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, meth, url, headers=None, json=None, timeout=None):
            assert headers['Authorization'] == f'Bearer {ORK}'
            return _R(200, {'id': 'vid2', 'polling_url': 'https://openrouter.ai/api/v1/videos/vid2'})
        async def get(self, url, headers=None):
            return _R(200, {'status': 'completed'})
        def stream(self, meth, url, **kw):
            return _R(200, None, b'ALEPH')
    monkeypatch.setattr(vsr.httpx, 'AsyncClient', lambda **kw: H())
    asyncio.run(real_run('g', jid))
    assert vsr._jobs()[jid]['step'] == 'filed' and jid not in fs._SPEND_HOLD
    rec = [json.loads(x) for x in (tmp_path / 'model_receipts.jsonl').read_text().splitlines()]
    assert rec[-1]['funding'] == 'owner key' and rec[-1]['usd'] == 2.8   # counts on his day cap, not FEELESS's
    assert vs.day_spent(vsr._jobs(), 0) == 0


# ── review fixes (2026-11-18 /code-review) ───────────────────────────────────────────────────────────────────────────────────────────

def test_long_h3_clips_carry_the_15s_shot_note_and_the_dotenv_is_read_again_only_when_saved(tmp_path):
    import os
    assert vs.heads_up('fal-h3-recast', 20) and not vs.heads_up('fal-h3-recast', 12) and not vs.heads_up('or-aleph', 20)
    env = tmp_path / '.env'; env.write_text('FAL_KEY=one\n')
    assert vs.env_key('FAL_KEY', {}, env) == 'one'
    env.write_text('# saved by HQ › Core\nFAL_KEY=two\n'); st = env.stat(); os.utime(env, (st.st_atime, st.st_mtime + 5))
    assert vs.env_key('FAL_KEY', {}, env) == 'two'


def test_the_plan_sends_the_shot_note_for_a_long_clip(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, *_ = _setup(monkeypatch, tmp_path, secs=22.0)
    clip = c.get(f'/api/cats/g/vswap?ws={ws}&ownerId=g&session=g').json()['clips'][0]
    assert '15 s' in clip['note']['fal-h3-recast'] and clip['note']['or-aleph'] == ''


def test_an_owner_key_job_keeps_the_owner_key_when_an_hq_key_appears(monkeypatch, tmp_path):
    import cat_keys as ck
    fs, c, store, vsr, ws, ran, started, real_run = _setup(monkeypatch, tmp_path, keys=())
    ck.put(store['cats']['g'], 'openrouter', ORK, data_dir=tmp_path)
    monkeypatch.setattr(fs, '_spend_check', lambda cat, usd, store=None: None)
    jid = _post(c, ws, clip='mcccccccccccc', engine='or-aleph', person='character', usd=2.8).json()['job']['id']
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-or-v1-house-key-added-later')   # HQ › Core gets a key while the job waits
    seen = []
    class H:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, meth, url, headers=None, json=None, timeout=None):
            seen.append(headers['Authorization']); return _R(200, {'id': 'vid3', 'polling_url': 'https://openrouter.ai/api/v1/videos/vid3'})
        async def get(self, url, headers=None):
            return _R(200, {'status': 'completed'})
        def stream(self, meth, url, **kw):
            return _R(200, None, b'ALEPH')
    monkeypatch.setattr(vsr.httpx, 'AsyncClient', lambda **kw: H())
    asyncio.run(real_run('g', jid))
    assert vsr._jobs()[jid]['step'] == 'filed' and seen == [f'Bearer {ORK}']   # priced on his key, run on his key, billed to his key


def test_any_error_stops_the_job_with_its_reason(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, ran, started, real_run = _setup(monkeypatch, tmp_path)
    jid = _post(c, ws, clip='mcccccccccccc', engine='fal-h3-recast', res='768P', person='character', usd=2.24).json()['job']['id']
    def boom(*a, **kw):
        raise TypeError('odd clip')
    monkeypatch.setattr(vs, 'ref_args', boom); sent = []; _fake_fal(monkeypatch, vsr, sent)
    asyncio.run(real_run('g', jid))
    job = vsr._jobs()[jid]
    assert job['step'] == 'failed' and 'odd clip' in job['why'] and not sent and jid not in vsr._LIVE


def test_a_portrait_sent_before_a_restart_is_never_sent_again(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, ran, started, real_run = _setup(monkeypatch, tmp_path, character=False, secs=8.0)
    q = vs.quote('fal-h3-recast', 8, '768P', True)['usd']
    jid = _post(c, ws, clip='mcccccccccccc', engine='fal-h3-recast', res='768P', person='make', words='a woman in a yellow coat', usd=q).json()['job']['id']
    job = vsr._jobs()[jid]; assert job['step'] == 'person'
    vsr._set(job, person={**job['person'], 'sent': True})   # the portrait call went out, then the service restarted
    sent = []; _fake_fal(monkeypatch, vsr, sent)
    asyncio.run(real_run('g', jid))
    job = vsr._jobs()[jid]
    assert job['step'] == 'failed' and 'not sent again' in job['why'] and not sent


def test_a_paid_swap_that_cannot_be_filed_still_writes_its_bill(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, ran, started, real_run = _setup(monkeypatch, tmp_path)
    jid = _post(c, ws, clip='mcccccccccccc', engine='fal-h3-recast', res='768P', person='character', usd=2.24).json()['job']['id']
    def broken(*a, **kw):
        raise RuntimeError('record store down')
    monkeypatch.setattr(fs, '_record_file', broken); sent = []; _fake_fal(monkeypatch, vsr, sent)
    asyncio.run(real_run('g', jid))
    job = vsr._jobs()[jid]
    assert job['step'] == 'failed' and 'cost is recorded' in job['why'] and job['billed']
    rec = [json.loads(x) for x in (tmp_path / 'model_receipts.jsonl').read_text().splitlines()]
    assert rec[-1]['usd'] == 2.24 and rec[-1]['funding'] == 'FEELESS key'
    board = [m['media'] for m in fs._ws_load('g', ws)['messages'] if (m.get('media') or {}).get('vswap')]
    assert board   # the made video is kept on the folder board


def test_a_link_that_cannot_open_leaves_no_copy_behind(monkeypatch, tmp_path):
    fs, c, store, vsr, ws, ran, started, real_run = _setup(monkeypatch, tmp_path)
    jid = _post(c, ws, clip='mcccccccccccc', engine='fal-h3-recast', res='768P', person='character', usd=2.24).json()['job']['id']
    async def down(_d):
        raise OSError('no tunnel')
    monkeypatch.setattr(fs._pubt, 'ensure', down); sent = []; _fake_fal(monkeypatch, vsr, sent)
    asyncio.run(real_run('g', jid))
    assert vsr._jobs()[jid]['step'] == 'failed' and not sent and not list((tmp_path / 'media' / 'g' / 'pub').iterdir())
