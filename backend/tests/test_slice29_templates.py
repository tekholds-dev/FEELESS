"""🎨 Slice 29 add-on (owner 2026-11-20: "should be able to set edit formats and templates, and they need to make cooler captions etc no dead
colors or bulky styling"; "i was speaking of the clip farming too"). Six modern caption templates (no slab: thin stroke + soft shadow, ≤ 2
lines, the spoken word popping in the accent, safe areas that never cover a face), each rendered by ffmpeg for real; saved templates per agent
with defaults per format / platform / farm; one tap onto a clip, a run or the week; the farm makes every clip in its template (the run's, or
the minds' pick per clip, all different, each with a why). The minds are faked; ffmpeg runs for real on a synthetic video."""
import asyncio

import pytest

import clip_farm as cf
import clip_look as cl
import test_slice29_clip_studio as _cs
from test_slice29_clip_studio import FFMPEG, HOOK21, _ask, _video
svc = _cs.svc   # the clip studio's fixture, shared

MODERN = cl.PRESET_ORDER


def test_six_distinct_modern_caption_templates_with_every_transition_and_the_old_presets_kept():
    assert set(MODERN) == {'pop', 'sweep', 'lower', 'outline', 'gradient', 'emoji'}
    styles = [cl.preset(k)['cap']['style'] for k in MODERN]
    assert styles == list(MODERN) and len({cl.sig(cl.preset(k)) for k in MODERN}) == 6
    assert {cl.preset(k)['tr'] for k in MODERN} == set(cl.TRANS)
    assert all(cl.preset(k)['cap']['style'] == 'classic' for k in cl.LEGACY)   # the Slice 29 presets still work as they did (no back pedal)
    assert cl.clean_look({})['cap']['style'] == 'classic' and cl.clean_look({'cap': {'style': 'slab'}})['cap']['style'] == 'classic'


@pytest.mark.parametrize('fmt', ['story', 'feed', 'wide'])
@pytest.mark.parametrize('name', MODERN)
def test_each_caption_style_stays_inside_the_frame_in_at_most_two_lines_with_no_slab(fmt, name):
    W, H, _ = cf.FORMATS[fmt]; cap = cl.preset(name)['cap']; px = {'story': 74, 'feed': 58, 'wide': 54}[fmt] * cl.SIZES[cap['size']]
    long_ = [{'w': w} for w in ('Submersibles', 'explored', 'hydrothermal', 'chimneys', '4,000', 'meters')][:cap['words']]
    for hot in range(len(long_)):
        for sc, fr, _d in cl.frames_for(cap['style'], .6):
            im = cl.cap_pic(W, long_, hot, cap, px, done=range(hot), frac=fr, scale=sc); bb = im.getbbox()
            assert bb and bb[0] >= 0 and bb[2] <= W, (name, fmt, hot, bb)
            a = im.getchannel('A'); solid = sum(1 for v in a.getdata() if v == 255) / (im.width * im.height)
            assert solid < .25, f'{name}: a solid slab ({solid:.0%} of the band is opaque)'
    txt = [w['w'].upper() for w in long_]
    _px, _f, _ws, lines = cl.cap_layout(W, txt, cap['font'], px, 1.12)
    assert 1 <= len(lines) <= 2 and sorted(i for ln in lines for i in ln) == list(range(len(txt)))


def test_the_hook_title_is_no_longer_a_flat_slab_and_still_keeps_every_word():
    W = 1080; im = cl.hook_band(W, HOOK21, 64, cl.preset('pop')['cap'])
    a = im.getchannel('A'); assert sum(1 for v in a.getdata() if v == 255) / (im.width * im.height) < .3
    green = sum(1 for p in im.getdata() if p[:3] == cf.GREEN[:3]) / (im.width * im.height); assert green < .1   # the old bar was ~100 % green
    px, lines = cl.hook_lines(W, HOOK21, 64, 'sf', most=2)
    assert ' '.join(lines).split() == HOOK21.split() and len(lines) <= 2


def test_the_spoken_word_pops_and_the_sweep_fills_in_thirds():
    assert [round(s, 2) for s, _f, _d in cl.frames_for('pop', .6)] == [1.16, 1.07, 1.0]
    assert [round(f, 2) for _s, f, _d in cl.frames_for('sweep', .6)] == [.34, .68, 1.0]
    assert sum(d for *_x, d in cl.frames_for('sweep', .6)) == pytest.approx(.6) and cl.frames_for('lower', .6) == [(1.0, 1.0, .6)]
    assert cl.frames_for('pop', .1) == [(1.0, 1.0, .1)]   # too short to animate: held


def test_the_caption_never_covers_a_face_and_stays_clear_of_the_app_buttons():
    H, bh = 1920, 230; cap = {**cl.DEFAULT['cap'], 'pos': 'low', 'safe': 'face'}
    assert cl.face_y([(0, .5, .3, 1), (1, .5, .32, 1), (2, .5, .9, 0)]) == pytest.approx(.32) and cl.face_y([(0, .5, .5, 0)]) is None
    y = cl.safe_y(H, bh, cap, face=.68); fy, half = .68 * H, .15 * H
    assert not (y < fy + half and y + bh > fy - half)   # off the face
    assert cl.safe_y(H, bh, {**cap, 'pos': 'bottom', 'safe': 'ui'}) + bh <= H * .80   # the bottom 20 % (likes, caption, share) stays clear
    assert cl.safe_y(H, bh, {**cap, 'pos': 'bottom', 'safe': 'off'}) == int(H * cl.POS['bottom'])
    assert cl.safe_y(H, bh, cap, face=.25) == int(H * cl.POS['low'])   # a face up top: the caption stays where the look put it


@pytest.mark.skipif(not FFMPEG, reason='ffmpeg is not installed')
@pytest.mark.parametrize('name', MODERN)
def test_each_template_renders_for_real_by_ffmpeg_with_sound_and_the_right_length(tmp_path, name):
    src = _video(tmp_path / 'in.mp4', 14); info = cf.probe(src)
    words = [{'s': 1.0 + i * .42, 'e': 1.33 + i * .42, 'w': ('hydrothermal' if i == 3 else '4,000' if i == 9 else f'word{i}') + ('.' if i % 6 == 5 else '')} for i in range(26)]
    out = tmp_path / 'o.mp4'; look = cl.preset(name)
    cl.render(src.resolve(), 1.0, 13.0, words, info, 'story', [(0.0, .5, .3, 1)], look, HOOK21, out, tmp_path, encoder='libx264')
    p = cf.probe(out)
    assert (p['w'], p['h']) == (1080, 1920) and p['audio'] and p['secs'] == pytest.approx(cl.out_dur(cl.segments(look, 12.0)), abs=.25)


def test_make_clip_gives_a_format_its_own_template(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(cl, 'render', lambda src, s, e, words, info, fmt, pts, look, hook, out, tmp, ffmpeg='ffmpeg': (seen.__setitem__(fmt, look['cap']['style']), out.write_bytes(b'v'), 0.1)[2])
    monkeypatch.setattr(cf, 'cover', lambda *a, **k: b'jpg')
    files, _tr = cf.make_clip(tmp_path / 'x.mp4', {'s': 0, 'e': 10, 'hook': 'h'}, [], {'w': 1920, 'h': 1080}, (), lambda p, e, b: f'/m/{p}.{e}', look=cl.preset('pop'),
                              pts=[(0, .5, .5, 1)], looks={'wide': cl.preset('lower')})
    assert seen == {'story': 'pop', 'feed': 'pop', 'wide': 'lower'} and all(f.get('url') for f in files)


# ── the service: templates, defaults, one tap, the minds' pick, the farm ───────────────────────────────────────────────────────────
def test_templates_save_update_delete_and_defaults_per_format_platform_and_farm(svc):
    fs, cat, c, _q = svc; import fc_clips
    look = {**cl.preset('sweep'), 'cap': {**cl.preset('sweep')['cap'], 'hot': 'green', 'safe': 'ui'}}
    r = c.post('/api/cats/c1/clipfarm/template/save', json={'name': 'My sweep', 'look': {**look, 'edit': {'w': {'1': 'x'}}}, 'fmts': ['story']})
    assert r.status_code == 200; tid = r.json()['id']; row = fc_clips.find_tpl(cat, tid)
    assert row['by'] == 'owner' and row['fmts'] == ['story'] and row['look']['edit']['w'] == {} and row['look']['cap']['safe'] == 'ui'   # word edits stay with clips
    assert c.post('/api/cats/c1/clipfarm/template/save', json={'name': 'Twin', 'look': look, 'fmts': ['story']}).status_code == 409   # the same look twice: no
    assert c.post('/api/cats/c1/clipfarm/template/save', json={'id': 'b:pop', 'name': 'x', 'look': look}).status_code == 400   # FEELESS's own stay
    assert c.post('/api/cats/c1/clipfarm/template/save', json={'id': tid, 'name': 'My sweep 2', 'look': look, 'fmts': ['story', 'feed']}).json()['id'] == tid
    assert fc_clips.find_tpl(cat, tid)['name'] == 'My sweep 2'
    for key, val in (('farm', tid), ('wide', 'b:lower'), ('tiktok', tid)):
        assert c.post('/api/cats/c1/clipfarm/template/default', json={'key': key, 'tpl': val}).status_code == 200
    assert c.post('/api/cats/c1/clipfarm/template/default', json={'key': 'story', 'tpl': 'minds'}).status_code == 404   # 'minds' is the farm's only
    fd = fc_clips.fmt_defaults(cat); assert fd['wide']['id'] == 'b:lower' and fd['story']['id'] == tid and 'feed' not in fd   # TikTok posts the 9:16 file
    assert fc_clips.run_tpl(cat, '') == tid and fc_clips.run_tpl(cat, 'b:emoji') == 'b:emoji' and fc_clips.run_tpl(cat, 'nope') == 'minds'
    g = c.get('/api/cats/c1/clipfarm').json()['templates']
    assert [x['id'] for x in g['list'][:6]] == [f'b:{k}' for k in MODERN] and g['inForce'] == {'story': tid, 'wide': 'b:lower'} and g['list'][0]['describe']
    assert c.post('/api/cats/c1/clipfarm/template/delete', json={'id': 'b:pop'}).status_code == 400
    assert c.post('/api/cats/c1/clipfarm/template/delete', json={'id': tid}).status_code == 200
    assert fc_clips.tpl_store(cat)['defaults']['farm'] == 'minds' and fc_clips.tpl_store(cat)['defaults']['tiktok'] == ''   # its defaults fall back


def _upload(fs, cat):
    """The run's converted upload, still kept (a template re-renders from it)."""
    cat['clipRuns'] = [{'id': 'r1', 'links': [{'kind': 'upload', 'file': 'up.mp4', 'exp': 9e9}]}]
    d = fs._media_dir() / 'c1'; d.mkdir(parents=True, exist_ok=True); (d / 'up.mp4').write_bytes(b'x')


def test_one_tap_puts_a_template_on_a_run_unique_per_clip_rerendered_and_undo_brings_the_old_one_back(svc):
    fs, cat, c, queued = svc
    _upload(fs, cat)
    r = c.post('/api/cats/c1/clipfarm/template/apply', json={'tpl': 'b:outline', 'run': 'r1'})
    assert r.status_code == 200 and set(r.json()['changed']) == {'p0', 'p1', 'p2'} and queued[-1] == {'p0', 'p1', 'p2'}
    sigs = {cl.sig(f['studio']['look']) for f in cat['pocFolders']}; assert len(sigs) == 3   # one template, three different clips (nudged)
    assert all(f['studio']['look']['cap']['style'] == 'outline' and f['studio']['tpl']['id'] == 'b:outline' for f in cat['pocFolders'])
    assert len(r.json()['notes']) == 2   # two of them were nudged, and it says how
    p0 = cat['pocFolders'][0]; v_before = p0['studio']['looks'][-2]['v']
    tid = c.post('/api/cats/c1/clipfarm/template/save', json={'name': 'Wide calm', 'look': cl.preset('lower'), 'fmts': ['wide']}).json()['id']
    c.post('/api/cats/c1/clipfarm/template/apply', json={'tpl': tid, 'job': 'p0'})
    assert p0['studio']['look']['cap']['style'] == 'outline' and p0['studio']['fmtLooks']['wide']['cap']['style'] == 'lower'   # only its format changed
    assert c.post('/api/cats/c1/clipfarm/look', json={'job': 'p0', 'patch': {'cap': {'size': 'S'}}}).status_code == 200
    assert p0['studio']['tpl'] == {**p0['studio']['tpl'], 'id': tid, 'edited': True} and p0['studio']['fmtLooks']['wide']   # a hand edit keeps it, marked edited
    r = c.post('/api/cats/c1/clipfarm/look/undo', json={'job': 'p0', 'v': v_before})
    assert r.status_code == 200 and p0['studio']['fmtLooks'] == {} and p0['studio']['tpl'] is None   # back to before any template
    cat['pocFolders'][1]['studio']['slot'] = 'Fri'
    assert c.post('/api/cats/c1/clipfarm/template/apply', json={'tpl': 'b:emoji', 'week': True}).json()['changed'] == ['p1']
    cat['pocFolders'][1]['posted'] = {'at': 1}
    assert c.post('/api/cats/c1/clipfarm/template/apply', json={'tpl': 'b:emoji', 'week': True}).status_code == 404   # posted = locked


def test_the_minds_pick_a_different_template_per_clip_with_a_why_and_the_code_fills_a_twin(svc, monkeypatch):
    fs, cat, c, queued = svc; seen = []; _upload(fs, cat)
    _ask(monkeypatch, fs, {'picks': [{'k': 0, 'tpl': 'b:gradient', 'why': 'NASA numbers, the figure glows'}, {'k': 1, 'tpl': 'b:gradient', 'why': 'twin'},
                                     {'k': 2, 'tpl': 'b:lower', 'why': 'calm story, keep the face clear'}]}, seen)
    r = c.post('/api/cats/c1/clipfarm/template/minds', json={'run': 'r1'})
    assert r.status_code == 200 and r.json()['cost'] == pytest.approx(.002) and 'b:pop' in seen[0][2] and 'k=2' in seen[0][2]
    t = [f['studio']['tpl'] for f in cat['pocFolders']]
    assert [x['id'] for x in t][0::2] == ['b:gradient', 'b:lower'] and t[1]['id'] not in ('b:gradient', 'b:lower') and t[1]['by'] == 'code'
    assert t[0]['by'] == 'minds' and 'NASA numbers' in t[0]['why'] and len({x['id'] for x in t}) == 3 and queued[-1] == {'p0', 'p1', 'p2'}


def test_a_clip_whose_upload_is_gone_keeps_its_look_and_nobody_pays_for_it(svc, monkeypatch):
    fs, cat, c, queued = svc; seen = []
    _ask(monkeypatch, fs, {'picks': [{'k': 0, 'tpl': 'b:gradient', 'why': 'x'}]}, seen)
    before = [cl.sig(f['studio']['look']) for f in cat['pocFolders']]
    for path, body in (('apply', {'tpl': 'b:outline', 'run': 'r1'}), ('minds', {'run': 'r1'})):
        r = c.post(f'/api/cats/c1/clipfarm/template/{path}', json=body)
        assert r.status_code == 409 and 'gone' in r.json()['detail']
    assert not seen and not queued and [cl.sig(f['studio']['look']) for f in cat['pocFolders']] == before and all(not f['studio'].get('tpl') for f in cat['pocFolders'])
    _upload(fs, cat); cat['pocFolders'][2]['studio']['clip']['run'] = 'r2'; cat['pocFolders'][2]['studio']['slot'] = 'Mon'; cat['pocFolders'][0]['studio']['slot'] = 'Tue'
    r = c.post('/api/cats/c1/clipfarm/template/apply', json={'tpl': 'b:emoji', 'week': True})
    assert r.json()['changed'] == ['p0'] and 'PoC #22: its upload is gone, left as it was' in r.json()['notes'] and queued[-1] == {'p0'}


def test_the_minds_design_a_new_template_saved_under_its_own_name(svc, monkeypatch):
    fs, cat, c, _q = svc; import fc_clips
    _ask(monkeypatch, fs, {'name': 'Neon whisper', 'base': 'sweep', 'patch': {'cap': {'hot': 'pink', 'font': 'demi'}, 'fx': {'grade': 'cool'}}, 'why': 'soft neon for late posts'})
    r = c.post('/api/cats/c1/clipfarm/template/mind', json={'ask': 'something for night posts'})
    row = fc_clips.find_tpl(cat, r.json()['id'])
    assert row['by'] == 'minds' and row['name'] == 'Neon whisper' and row['look']['cap']['style'] == 'sweep' and row['look']['cap']['hot'] == 'pink' and 'neon' in row['why']


def test_the_farm_makes_every_clip_in_its_template_the_runs_pick_or_the_minds_and_records_it(svc, monkeypatch):
    fs, cat, c, _q = svc; import fc_clips
    picks = [{'n': i, 'hook': ('Deep', 'Wait', 'Slow')[i], 'text': t, 'dur': d, 'both': b} for i, (t, d, b) in enumerate((('It cost $4,000 a day', 30, 7), ('why would anyone?', 20, 6), ('a calm long story', 50, 5)))]
    pairs, cost, _own, mind = asyncio.run(fc_clips._run_tpls('c1', cat, {'tpl': 'b:outline'}, picks))
    assert [p[0]['id'] for p in pairs] == ['b:outline'] * 3 and pairs[0][2] == 'owner' and cost == 0
    _ask(monkeypatch, fs, 'no json here')   # a mind that answers nonsense: the code picks by mood, all different
    pairs, cost, _own, mind = asyncio.run(fc_clips._run_tpls('c1', cat, {'tpl': 'minds'}, picks))
    assert [p[0]['id'] for p in pairs] == ['b:gradient', 'b:emoji', 'b:lower'] and all(p[2] == 'code' and p[1] for p in pairs)
    run = {'id': 'r9', 'name': 'up', 'source': 'upload', 'secs': 60}
    p = {'n': 1, 'hook': 'h', 'caption': 'c', 's': 0, 'e': 10, 'dur': 10, 'text': 't', 'first2': 'f', 'facts': {}, 'local': 5, 'both': 7, 'minds': [], 'lead': 0,
         'look': cl.preset('emoji'), 'tpl': {'id': 'b:emoji', 'name': 'Emoji accent', 'by': 'minds', 'why': 'a joke'}, 'fmtLooks': {'wide': cl.preset('lower')}}
    monkeypatch.setattr(fs, '_record_file', lambda c_, kind, f_: f_)
    f_ = fc_clips._file_clip('c1', run, 0, p, [], {'how': 'face'}, [], 0.0, None)
    assert f_['studio']['tpl']['name'] == 'Emoji accent' and f_['studio']['fmtLooks']['wide']['cap']['style'] == 'lower' and f_['studio']['looks'][0]['by'] == 'minds'
    assert 'Emoji accent: a joke' in f_['studio']['looks'][0]['why']
