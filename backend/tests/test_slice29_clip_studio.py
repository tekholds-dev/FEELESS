"""🎨🗓 Slice 29 (owner 2026-11-20): the clip studio. The 9:16 caption cut-off fixed; each clip's look (captions, transition, effects) set by the
owner or the minds, rendered by ffmpeg ($0, no watermark), unique per clip, versioned with undo; one week plan (dragged, or "agent plans it" with
a why per slot) with a chat inside it that changes the plan and the clips. The minds are faked here; ffmpeg runs for real on a synthetic video."""
import json
import shutil
import subprocess

import pytest

import clip_farm as cf
import clip_look as cl

FFMPEG = shutil.which('ffmpeg') and shutil.which('ffprobe')
HOOK21 = 'I wanted to be an explorer since I was a kid.'   # PoC #21: the 9:16 bar showed "…since I was a" and lost "kid."


# ── the cut-off caption (PoC #21) ───────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize('fmt', ['story', 'feed', 'wide'])
@pytest.mark.parametrize('key', ['bold', 'impact', 'serif', 'chalk'])
def test_the_hook_title_keeps_every_word_inside_the_frame_on_every_format(fmt, key):
    W, H, _ = cf.FORMATS[fmt]
    for px in ({'story': 64, 'feed': 52, 'wide': 50}[fmt], {'story': 72, 'feed': 60, 'wide': 58}[fmt]):   # the clip's bar and the cover's
        for hook in (HOOK21, 'Why every single ocean explorer secretly wanted to become an astronaut first and what NASA taught them'):
            px2, lines = cl.hook_lines(W, hook, px, key)
            assert ' '.join(lines) == hook and len(lines) <= 3, (fmt, key, lines)   # nothing dropped
            im = cl.hook_band(W, hook, px, {**cl.DEFAULT['cap'], 'font': key})
            box = im.getbbox(); assert box and box[0] >= W * .02 and box[2] <= W * .98, box   # the bar sits inside the frame
    assert cf.hook_band(1080, HOOK21, 64).getbbox()[2] <= 1080   # the old entry point (new runs, covers) uses the fix too


def test_a_caption_band_always_fits_the_frame_even_with_a_huge_word():
    cap = {**cl.DEFAULT['cap'], 'size': 'L', 'font': 'impact', 'mode': 'box'}
    words = [{'w': 'Internationally'}, {'w': 'recognised'}, {'w': 'oceanographers!'}]
    for fmt in cf.FORMATS:
        W = cf.FORMATS[fmt][0]; im = cl.band(W, words, 1, cap, 88 * 1.2)
        box = im.getbbox(); assert box[0] >= 0 and box[2] <= W and box[2] - box[0] <= W * .9


# ── looks: valid, unique, versioned ─────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_look_is_cleaned_merged_and_made_unique_and_word_edits_never_change_its_design():
    a = cl.clean_look({'cap': {'font': 'comic-sans', 'words': 9, 'hot': 'pink'}, 'tr': 'spin', 'fx': {'grade': 'lol', 'punch': 1}, 'edit': {'w': {'3': 'kid!', 'x': 'no'}, 'off': 4}})
    assert a['cap']['font'] == 'bold' and a['cap']['words'] == 6 and a['cap']['hot'] == 'pink' and a['tr'] == 'cut' and a['fx'] == {**cl.DEFAULT['fx'], 'punch': True}
    assert a['edit'] == {'w': {'3': 'kid!'}, 'off': 1.0}
    assert cl.sig(a) == cl.sig({**a, 'edit': {'w': {}, 'off': 0}})
    b = cl.merge(a, {'fx': {'shake': True}, 'tr': 'glitch'}); assert b['fx']['shake'] and b['fx']['punch'] and b['tr'] == 'glitch' and b['edit']['w'] == {'3': 'kid!'}
    used = {cl.sig(b)}; c, why = cl.unique(b, used)
    assert cl.sig(c) not in used and 'another clip' in why
    looks = []; used = set()
    for n in range(14):   # 14 new clips in a row: all different
        lk = cl.lucky(n, used); used.add(cl.sig(lk)); looks.append(cl.sig(lk))
    assert len(set(looks)) == 14
    assert {cl.preset(k)['tr'] for k in cl.PRESET_ORDER} == set(cl.TRANS)   # the presets cover every transition


def test_word_edits_timing_speed_and_where_the_effects_land():
    words = [{'s': 10.0 + i * .5, 'e': 10.3 + i * .5, 'w': f'w{i}' + ('.' if i % 6 == 5 else '')} for i in range(40)]
    look = cl.clean_look({'edit': {'w': {'0': 'Hello', '1': ''}, 'off': .2}})
    ws = cl.clip_words(words, 10.0, 30.0, look)
    assert ws[0]['w'] == 'Hello' and ws[0]['s'] == pytest.approx(.2) and all(w['w'] != 'w1' for w in ws)   # edited, dropped, shifted
    segs = cl.segments({'fx': {'speed': 'ramp'}}, 20.0)
    assert segs == [(0.0, 17.5, 1.25), (17.5, 20.0, 1.0)] and cl.out_dur(segs) == pytest.approx(16.5) and cl.tmap(17.5, segs) == pytest.approx(14.0)
    assert cl.segments({'fx': {'speed': 'tight'}}, 10)[0][2] == 1.1 and cl.segments({}, 10) == [(0.0, 10, 1.0)]
    bts = cl.beats(cl.clip_words(words, 10.0, 30.0, {}), 20.0); assert bts[0] == 0 and all(b - a >= 2.5 for a, b in zip(bts, bts[1:]))
    hype = cl.preset('hype'); chain = cl.fx_chain(hype, 1080, 1920, 20.0, bts, [3.0])
    assert 'eval=frame' in chain and 'crop=1080:1920' in chain and 'sin(t*41)' in chain and 'contrast=1.12' in chain   # punch + zoom, shake, punchy grade
    assert 'rgbashift' in cl.fx_chain(cl.preset('glitch'), 1080, 1920, 20, bts, []) and 'tmix' in cl.fx_chain(cl.preset('story'), 1080, 1920, 20, bts, [])
    assert 'fade=t=in' in cl.fx_chain(cl.preset('cinema'), 1080, 1920, 20, bts, []) and cl.fx_chain(cl.preset('classic'), 1080, 1920, 20, bts, []) == 'null'
    assert cl.pops([{'s': 1, 'e': 1.2, 'w': 'the'}, {'s': 2, 'e': 2.3, 'w': 'submersible'}, {'s': 3, 'e': 3.3, 'w': '1969'}, {'s': 6, 'e': 6.3, 'w': '1969'}], 20) == [(2, 'SUBMERSIBLE'), (6, '1969')]


def _video(path, secs=24):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc2=size=640x360:rate=25:duration={secs}', '-f', 'lavfi', '-i', f'sine=frequency=330:duration={secs}',
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-shortest', str(path)], check=True, timeout=120)
    return path


@pytest.mark.skipif(not FFMPEG, reason='ffmpeg is not installed')
@pytest.mark.parametrize('name', ['hype', 'cinema', 'glitch', 'story'])
def test_each_look_renders_for_real_with_sound_the_right_length_and_no_watermark(tmp_path, name):
    src = _video(tmp_path / 'in.mp4'); info = cf.probe(src)
    words = [{'s': 2.0 + i * .45, 'e': 2.35 + i * .45, 'w': ('submersible' if i == 4 else f'word{i}') + ('.' if i % 7 == 6 else '')} for i in range(36)]
    out = tmp_path / 'o.mp4'; look = cl.preset(name)
    secs = cl.render(src.resolve(), 2.0, 18.0, words, info, 'story', [(0.0, .5, .45, 0)], look, HOOK21, out, tmp_path, encoder='libx264')
    p = cf.probe(out); want = cl.out_dur(cl.segments(look, 16.0))
    assert (p['w'], p['h']) == (1080, 1920) and p['audio'] and p['secs'] == pytest.approx(want, abs=.25) and secs > 0
    assert b'watermark' not in out.read_bytes()[:4000].lower()


# ── the service: looks, the plan, the chat, undo ────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def svc(monkeypatch, tmp_path):
    import feecat_service as fs
    import fc_clips
    clips = [{'id': f'p{i}', 'n': 20 + i, 'at': 1, 'studio': {'hook': f'Hook {i}', 'clip': {'run': 'r1', 'n': i, 's': 0, 'e': 20, 'dur': 20, 'both': 9 - i, 'text': 'said'},
              'files': [{'piece': 'video', 'format': 'story', 'url': f'/m/old{i}.mp4', 'link': f'/api/cats/vid/old{i}'}], 'look': cl.lucky(i, set()), 'post': {'story': 'cap'}}} for i in range(3)]
    cat = {'id': 'c1', 'name': "Happy's", 'handle': 'happy-assistant', 'chat': [], 'brainsCfg': {'brains': ['local/ossy', 'local/g4'], 'credit': 1.0}, 'pocFolders': clips, 'clipRuns': []}
    store = {'cats': {'c1': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None); monkeypatch.setattr(fs, '_media_dir', lambda: tmp_path)
    monkeypatch.setattr(fs, '_calls_of', lambda *a, **k: []); monkeypatch.setattr(fs, '_internal', lambda r: None)
    queued = []; monkeypatch.setattr(fc_clips, '_queue', lambda cid, jobs: queued.append(set(jobs)))

    async def no_trends():
        return 'ocean exploration; NASA'
    monkeypatch.setattr(fc_clips, '_trend_lines', no_trends)
    from fastapi.testclient import TestClient
    return fs, cat, TestClient(fs.app), queued


def _ask(monkeypatch, fs, answer, seen=None):
    async def ask(cat_, m, sys_, user_, tokens):
        if seen is not None:
            seen.append((m, sys_, user_))
        return json.dumps(answer) if not isinstance(answer, str) else answer, 0.002, False
    monkeypatch.setattr(fs, '_ws_ask', ask)


def test_the_owner_sets_a_look_it_renders_a_copy_of_another_clip_is_refused_and_undo_brings_the_old_files_back(svc):
    fs, cat, c, queued = svc; p0 = cat['pocFolders'][0]
    r = c.post('/api/cats/c1/clipfarm/look', json={'job': 'p0', 'patch': {'cap': {'hot': 'orange', 'size': 'L'}, 'fx': {'pop': True}}})
    assert r.status_code == 200 and queued == [{'p0'}]
    vs = p0['studio']['looks']; assert [v['v'] for v in vs] == [1, 2] and vs[0]['files'][0]['url'] == '/m/old0.mp4'   # the first-made files are version 1
    assert p0['studio']['look']['cap']['hot'] == 'orange' and p0['studio']['look']['fx']['pop'] and vs[1]['by'] == 'owner'
    twin = cat['pocFolders'][1]['studio']['look']
    r = c.post('/api/cats/c1/clipfarm/look', json={'job': 'p0', 'look': twin})
    assert r.status_code == 409 and 'PoC #21 already has this exact look' in r.json()['detail']
    assert c.post('/api/cats/c1/clipfarm/look', json={'job': 'p0', 'patch': {}}).status_code == 400   # nothing changed
    p0['studio']['looks'][-1]['files'] = [{'piece': 'video', 'format': 'story', 'url': '/m/new.mp4', 'link': '/api/cats/vid/new'}]; p0['studio']['files'] = p0['studio']['looks'][-1]['files']
    r = c.post('/api/cats/c1/clipfarm/look/undo', json={'job': 'p0', 'v': 1})
    assert r.status_code == 200 and p0['studio']['files'][0]['url'] == '/m/old0.mp4' and p0['studio']['looks'][-1]['by'] == 'undo' and len(queued) == 1   # no re-render
    assert p0['studio']['links'] == {'story': '/api/cats/vid/old0'}
    p0['posted'] = {'at': 1}
    assert c.post('/api/cats/c1/clipfarm/look', json={'job': 'p0', 'patch': {'tr': 'fade'}}).status_code == 409   # posted = locked


def test_the_minds_pick_a_look_never_the_same_as_another_clip(svc, monkeypatch):
    fs, cat, c, queued = svc; seen = []
    _ask(monkeypatch, fs, {'patch': {'preset': 'clean'}, 'why': 'calm explainer'}, seen)   # p2 sits on lucky(2) = clean already … for p0 it must be nudged
    cat['pocFolders'][2]['studio']['look'] = cl.preset('clean')
    r = c.post('/api/cats/c1/clipfarm/look/mind', json={'job': 'p0', 'ask': 'calmer'})
    assert r.status_code == 200 and r.json()['note'] and queued == [{'p0'}]
    sigs = [cl.sig(f['studio']['look']) for f in cat['pocFolders']]; assert len(set(sigs)) == 3
    assert "OTHER CLIPS' LOOKS" in seen[0][2] and seen[0][0] == 'local/ossy' and cat['pocFolders'][0]['studio']['looks'][-1]['by'] == 'minds'


def test_the_week_is_one_saved_plan_whether_dragged_picked_on_the_clip_or_made_by_the_agent(svc, monkeypatch):
    fs, cat, c, _q = svc
    r = c.post('/api/cats/c1/clipfarm/plan', json={'slots': [{'job': 'p0', 'day': 'fri', 'time': '19:30', 'plats': ['tiktok', 'myspace']}, {'job': 'p0', 'day': 'Mon'}, {'job': 'zz', 'day': 'Mon'}]})
    j = r.json(); assert r.status_code == 200 and j['plan']['cur'] == 1
    assert j['plan']['versions'][0]['slots'] == [{'job': 'p0', 'day': 'Fri', 'time': '19:30', 'plats': ['tiktok'], 'why': ''}]
    assert cat['pocFolders'][0]['studio']['slot'] == 'Fri' and cat['pocFolders'][0]['studio']['slotTime'] == '19:30'
    assert c.post('/api/cats/c1/clipfarm/slot', json={'job': 'p1', 'day': 'Tue'}).status_code == 200   # the old day buttons land in the same plan
    assert cat['clipPlan']['cur'] == 2 and {s['job'] for s in cat['clipPlan']['versions'][-1]['slots']} == {'p0', 'p1'}
    seen = []
    _ask(monkeypatch, fs, {'slots': [{'job': 'p0', 'day': 'Tue', 'time': '19:00', 'plats': ['tiktok', 'instagram'], 'why': 'best score on the best day'},
                                     {'job': 'p1', 'day': 'Thu', 'time': '12:00', 'plats': ['instagram'], 'why': 'NASA trend'}], 'note': 'two strong days'}, seen)
    j = c.post('/api/cats/c1/clipfarm/plan/agent', json={}).json(); v = j['plan']['versions'][-1]
    assert v['by'] == 'minds' and all(s['why'] for s in v['slots']) and v['cost'] == .002 and 'Agent plans it' in v['why']
    assert 'ocean exploration' in seen[0][2] and 'score 9/10' in seen[0][2]   # it read the scores and the trend reader
    _ask(monkeypatch, fs, 'sorry, no JSON')
    v = c.post('/api/cats/c1/clipfarm/plan/agent', json={}).json()['plan']['versions'][-1]
    assert v['by'] == 'code' and [s['day'] for s in v['slots']] == ['Tue', 'Thu', 'Fri'] and all('score' in s['why'] for s in v['slots'])


def test_the_chat_in_the_plan_moves_clips_changes_their_looks_and_undo_puts_both_back(svc, monkeypatch):
    fs, cat, c, queued = svc
    c.post('/api/cats/c1/clipfarm/plan', json={'slots': [{'job': 'p0', 'day': 'Mon'}, {'job': 'p1', 'day': 'Tue'}]})
    before = {f['id']: cl.sig(f['studio']['look']) for f in cat['pocFolders']}
    _ask(monkeypatch, fs, {'reply': 'Moved the best one to Friday and made Tuesday funnier.', 'moves': [{'job': 'p0', 'day': 'Fri', 'time': '18:00', 'why': 'best one on Friday'}],
                           'looks': [{'job': 'p1', 'patch': {'fx': {'pop': True, 'speed': 'ramp'}, 'tr': 'glitch'}, 'why': 'funnier'}]})
    r = c.post('/api/cats/c1/clipfarm/plan/chat', json={'text': 'move the best one to Friday, make Tuesday funnier'})
    j = r.json(); assert r.status_code == 200 and j['v'] == 2 and queued == [{'p1'}]
    days = {s['job']: s['day'] for s in j['plan']['versions'][-1]['slots']}; assert days == {'p0': 'Fri', 'p1': 'Tue'}
    p1 = cat['pocFolders'][1]['studio']; assert p1['look']['fx']['pop'] and p1['look']['tr'] == 'glitch' and p1['looks'][-1]['by'] == 'chat'
    chat = j['plan']['chat']; assert [m['by'] for m in chat] == ['owner', 'mind'] and chat[1]['v'] == 2 and chat[1]['looks'] == ['p1']
    r = c.post('/api/cats/c1/clipfarm/plan/undo', json={'v': 1}); j = r.json()
    assert {s['job']: s['day'] for s in j['plan']['versions'][-1]['slots']} == {'p0': 'Mon', 'p1': 'Tue'} and j['plan']['versions'][-1]['by'] == 'undo'
    assert cl.sig(p1['look']) == before['p1'] and cat['pocFolders'][0]['studio']['slot'] == 'Mon'   # the look is back too
    _ask(monkeypatch, fs, {'reply': 'Hmm.'})
    assert c.post('/api/cats/c1/clipfarm/plan/chat', json={'text': 'whatever'}).json()['v'] is None   # no change → no new version


def test_a_test_asks_the_minds_only_inside_the_owners_caps_and_nothing_here_posts(svc, monkeypatch):
    fs, cat, c, _q = svc
    import fc_test
    monkeypatch.setattr(fc_test, 'spent_since', lambda rows, kind=None: 99.0)
    r = c.post('/api/cats/c1/clipfarm/plan/agent', json={}, headers={'x-feeless-internal': 'k'})
    assert r.status_code == 402
    import fc_clips
    src = open(fc_clips.__file__).read().split('# ── 🎨🗓 Slice 29')[1]
    assert 'poc_approve' not in src and 'upload-post' not in src.lower() and 'postiz' not in src.lower()   # nothing in the studio can post


def test_an_older_store_copy_never_undoes_a_render_and_a_lost_render_runs_again(svc, monkeypatch):
    """Seen live 2026-11-20: a render's "done" (new files) was wiped by an older copy saved by another pass; the clip sat on "running"."""
    import copy
    import time
    import fc_clips
    fs, cat, c, queued = svc; fc_clips._MEM.clear()
    old = copy.deepcopy({'cats': {'c1': cat}})   # a copy loaded before the render finished
    p0 = cat['pocFolders'][0]; fc_clips._add_look(p0, cl.preset('cinema'), 'owner', 'x', [{'piece': 'video', 'format': 'story', 'url': '/m/new.mp4'}])
    p0['studio']['render'] = {'state': 'done', 'v': 2}; fc_clips._keep_looks(cat)
    fc_clips.merge(old)
    s0 = old['cats']['c1']['pocFolders'][0]['studio']
    assert s0['render']['state'] == 'done' and s0['files'][0]['url'] == '/m/new.mp4' and len(s0['looks']) == 2
    cat['pocFolders'][1]['studio']['render'] = {'state': 'running', 'at': time.time() - 600}
    assert c.get('/api/cats/c1/clipfarm').status_code == 200 and queued == [{'p1'}]
    fc_clips._MEM.clear()


def test_clips_made_before_the_studio_that_share_a_look_each_get_their_own_and_render(svc, monkeypatch, tmp_path):
    import fc_clips
    fs, cat, c, queued = svc; fc_clips._MEM.clear()
    for f in cat['pocFolders']:
        f['studio'].pop('look')   # all three from before Slice 29: the same plain look
    cat['clipRuns'] = [{'id': 'r1', 'links': [{'kind': 'upload', 'file': 'up.mp4', 'exp': 9e9}]}]; (tmp_path / 'c1').mkdir(exist_ok=True); (tmp_path / 'c1' / 'up.mp4').write_bytes(b'x')
    cat['pocFolders'][2]['posted'] = {'at': 1}
    assert c.get('/api/cats/c1/clipfarm').status_code == 200
    sigs = [cl.sig(f['studio']['look']) for f in cat['pocFolders']]; assert len(set(sigs)) == 3
    assert queued == [{'p0', 'p1'}] or queued == [{'p1', 'p0'}]   # the posted one keeps its look; the other two render their own
    assert cat['pocFolders'][0]['studio']['looks'][-1]['by'] == 'code'
    queued.clear(); c.get('/api/cats/c1/clipfarm'); assert queued == []   # once
    fc_clips._MEM.clear()
