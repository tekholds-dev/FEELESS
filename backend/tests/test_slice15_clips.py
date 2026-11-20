"""✂ Slice 15 (owner 2026-11-19): PoC clip farming. An upload up to 5 min (YouTube / Twitch / Instagram links are never downloaded) → a local
transcript with word times + loudness / laughs / scene cuts → candidate moments → both minds score them blind → each pick tracked, cut and
reframed to 9:16, 1:1 and 16:9 with word-by-word captions, a hook title and a cover → each clip files as its own PoC with a goal and cost,
and posts only through the owner's approve. The minds and the transcript are faked here; ffmpeg + OpenCV run for real on a synthetic video."""
import asyncio
import json
import shutil
import subprocess

import pytest

import clip_farm as cf
import clip_source as cs
import poc_studio as ps

FFMPEG = shutil.which('ffmpeg') and shutil.which('ffprobe')


def _words(secs=40.0, step=0.4):
    """Fake speech: a word every 0.4 s, a sentence end every 10 words, a question at the end of every 3rd sentence."""
    out, t, i = [], 0.6, 0
    while t + 0.3 < secs:
        i += 1; end = '?' if i % 30 == 0 else '.' if i % 10 == 0 else ''
        out.append({'s': round(t, 2), 'e': round(t + 0.3, 2), 'w': f'word{i}{end}'}); t += step
    return out


def _cands(secs=120.0):
    w = _words(secs); loud = [-30.0 + (5 if k % 7 == 0 else 0) for k in range(int(secs * 2))]
    return w, loud, cf.moments(w, loud, [10.0, 50.0], [33.0], secs)


# ── the file and its limits ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_only_mp4_mov_webm_up_to_5_min_with_sound_is_taken_and_the_refusals_say_what_to_do():
    assert cf.ext_of('My Stream.MOV') == 'mov' and cf.ext_of('x', 'video/webm') == 'webm' and cf.ext_of('a.m4v') == 'm4v'
    with pytest.raises(ValueError, match='MP4, MOV or WebM'):
        cf.ext_of('clip.avi')
    ok = {'secs': 300.2, 'w': 1920, 'h': 1080, 'fps': 30, 'audio': True}
    assert cf.check(ok, 100) is ok   # exactly 5:00 is fine
    with pytest.raises(ValueError, match='6:04 long. Up to 5:00'):
        cf.check({**ok, 'secs': 364.7}, 100)
    with pytest.raises(ValueError, match='MB'):
        cf.check(ok, cf.MAX_BYTES + 1)
    with pytest.raises(ValueError, match='no sound'):
        cf.check({**ok, 'audio': False}, 100)
    with pytest.raises(ValueError, match='at least 15 s'):
        cf.check({**ok, 'secs': 9}, 100)


@pytest.mark.parametrize('url,name', [('https://www.youtube.com/watch?v=abc', 'YouTube'), ('https://youtu.be/abc', 'YouTube'), ('https://www.twitch.tv/some/clip/x', 'Twitch'),
                                      ('https://clips.twitch.tv/Funny', 'Twitch'), ('https://www.instagram.com/reel/x/', 'Instagram'), ('https://www.tiktok.com/@a/video/1', 'TikTok')])
def test_youtube_twitch_instagram_links_are_never_downloaded_save_it_from_the_app_then_upload(url, name):
    with pytest.raises(ValueError, match=f"{name} doesn't allow downloading.*upload the file"):
        cs.classify(url)


def test_a_bluesky_post_or_a_direct_file_link_still_works():
    assert cs.classify('https://bsky.app/profile/a.bsky.social/post/3abcdefgh')[0] == 'bluesky'
    assert cs.classify('https://example.org/talk.webm') == ('direct', 'https://example.org/talk.webm')


# ── the moments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_candidates_are_15_to_60_s_cut_on_sentence_ends_never_overlap_and_carry_their_hook_and_peaks():
    w, loud, c = _cands()
    assert 3 <= len(c) <= cf.MAX_CANDS and [x['n'] for x in c] == list(range(1, len(c) + 1))
    ends = {x['e'] for x in w if x['w'].endswith(('.', '?'))}
    for x in c:
        assert cf.CLIP_MIN <= x['dur'] <= cf.CLIP_MAX
        assert any(abs(x['e'] - (e + .35)) < .01 for e in ends)   # ends on a sentence end
        assert x['first2'] and x['facts']['hookWords'] >= 3 and set(x['facts']) >= {'hookDb', 'endsOn', 'peaks', 'laughs', 'cuts', 'wordsPerS'}
    for a in c:
        for b in c:
            if a is not b:
                assert min(a['e'], b['e']) - max(a['s'], b['s']) < .25 * min(a['dur'], b['dur'])
    assert any(x['facts']['laughs'] for x in c if x['s'] <= 33 <= x['e'])
    assert cf.laughs([{'s': 0, 'e': 1, 'w': 'hi'}], [-40, -40, -40, -40, -20, -40]) == [2.0]   # loud with no word over it


def test_both_minds_answers_are_read_through_thinking_and_clamped_inside_their_candidate():
    _w, _l, c = _cands()
    raw = '<think>hmm {x}</think>```json\n' + json.dumps({'scores': [{'n': 1, 'score': 14, 'why': 'big hook'}, {'n': 2, 'score': 3}],
                                                         'picks': [{'n': 1, 'start': -5, 'end': 999, 'hook': 'You won\'t believe this', 'caption': 'wow #space #MindA', 'views': 4000},
                                                                   {'n': 99, 'hook': 'not a candidate'}, {'n': 3, 'hook': 'unscored pick'}]}) + '\n```'
    m = cf.parse_mind(raw, c)
    assert m['scores'][1] == (10.0, 'big hook') and m['scores'][2][0] == 3.0 and m['scores'][3] == (7.0, 'picked')
    p = m['picks'][0]
    assert p['start'] == c[0]['s'] and p['end'] <= c[0]['e'] and p['end'] - p['start'] <= cf.CLIP_MAX and [x['n'] for x in m['picks']] == [1, 3]
    assert p['caption'] == 'wow #space'   # a mind's seat name never rides along as a hashtag
    assert cf.parse_mind('no json', c) is None and cf.parse_mind('{"scores": []}', c) is None


def test_the_picks_rank_on_both_blind_scores_keep_every_minds_score_and_why_and_take_the_hook_from_the_higher_scorer():
    _w, _l, c = _cands()
    a = {'scores': {1: (8, 'A likes 1'), 2: (2, 'meh')}, 'picks': [{'n': 1, 'start': c[0]['s'], 'end': c[0]['e'], 'hook': 'Hook A', 'caption': 'Cap A', 'payoff': '', 'views': 5000}]}
    b = {'scores': {1: (9, 'B loves 1'), 2: (3, 'meh'), 3: (8, 'B likes 3')}, 'picks': [{'n': 1, 'start': c[0]['s'] + 1, 'end': c[0]['e'], 'hook': 'Hook B', 'caption': 'Cap B', 'payoff': 'lands', 'views': 9000},
                                                                                {'n': 3, 'start': c[2]['s'], 'end': c[2]['e'], 'hook': 'Hook 3', 'caption': 'C3', 'payoff': '', 'views': 0}]}
    keep, ranked = cf.choose(c, [a, b])
    assert keep[0]['n'] == 1 and keep[0]['hook'] == 'Hook B' and keep[0]['lead'] == 1 and keep[0]['both'] == 8.5 and keep[0]['s'] == c[0]['s'] + 1
    assert [m['why'] for m in keep[0]['minds']] == ['A likes 1', 'B loves 1'] and all(m['picked'] for m in keep[0]['minds'])
    assert 2 not in [k['n'] for k in keep]   # both scored it under 4
    assert len(ranked) == len(c) and all(len(r['minds']) == 2 for r in ranked)   # the record keeps EVERY candidate
    assert cf.goal(keep[0]) == {'type': 'reach', 'target': 9000, 'why': 'the minds’ own 7-day guess for this clip', 'by': 'minds', 'locked': False}
    none, _ = cf.choose(c, [None, None])   # no mind answered: code's own score stands in, and the hook is the first words said
    assert none and none[0]['both'] is None and none[0]['hook'] and cf.goal(none[0])['by'] == 'code'


# ── the reframe ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_the_crop_follows_the_tracked_speaker_never_a_fixed_centre_and_a_wider_format_is_fitted_not_cropped():
    info = {'w': 1920, 'h': 1080}
    assert cf.crop_box(info, 'story') == (606, 1080) and cf.crop_box(info, 'feed') == (1080, 1080) and cf.crop_box(info, 'wide') == (1920, 1080)
    assert cf.crop_box({'w': 1080, 'h': 1920}, 'wide') is None   # a phone video into 16:9: fitted on a blurred fill
    cmds = cf.crop_cmds([(0, .3, .4, 1), (1, .3, .4, 1), (2, .8, .4, 1)], info, (606, 1080)).splitlines()
    xs = [int(l.split('crop x ')[1].split(',')[0]) for l in cmds]
    assert xs[0] == int(.3 * 1920 - 303) and xs[-1] == int(.8 * 1920 - 303) and xs[0] != (1920 - 606) // 2
    assert all(0 <= x <= 1920 - 606 for x in xs) and xs == sorted(xs)   # slides, never jumps outside the picture


def test_captions_are_short_word_groups_timed_from_the_clip_start():
    g = cf.groups(_words(20), 2.0, 12.0)
    assert all(1 <= len(x) <= 3 for x in g) and g[0][0]['s'] >= 0 and g[-1][-1]['e'] <= 10.0
    assert all(x[-1]['w'].endswith('.') or len(x) == 3 or x is g[-1] for x in g)


# ── the real files (ffmpeg + OpenCV on a synthetic clip) ────────────────────────────────────────────────────────────────────────────

def _video(path, secs=40):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc2=size=640x360:rate=25:duration={secs}', '-f', 'lavfi', '-i', f'sine=frequency=330:duration={secs}',
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-shortest', str(path)], check=True, timeout=120)
    return path


@pytest.mark.skipif(not FFMPEG, reason='ffmpeg is not installed')
def test_a_clip_is_made_in_9_16_1_1_and_16_9_with_its_cover_and_post_and_no_watermark(tmp_path):
    src = _video(tmp_path / 'in.mp4'); info = cf.probe(src)
    assert info['secs'] == pytest.approx(40, abs=.2) and (info['w'], info['h']) == (640, 360) and info['audio']
    clip = {'s': 2.0, 'e': 18.0, 'hook': 'The moment it all changed', 'caption': 'Watch to the end #test'}
    kept = {}

    def save(piece, ext, raw):
        p = tmp_path / f'{len(kept)}.{ext}'; p.write_bytes(raw); kept[str(p)] = piece; return str(p)
    files, tr = cf.make_clip(src, clip, _words(40), info, [], save)
    ok, why = cf.files_check(files)
    assert ok, why
    assert tr['how'] in ('face', 'motion') and tr['frames'] >= 70
    for f in files:
        if f['piece'] == 'video':
            p = cf.probe(f['url'])
            assert (p['w'], p['h']) == cf.FORMATS[f['format']][:2] and p['secs'] == pytest.approx(16, abs=.3) and p['audio']
        if f['piece'] == 'post':
            assert f['text'] == 'Watch to the end #test'
    assert {f['format'] for f in files if f['piece'] == 'image' and f.get('cover')} == {'story', 'feed', 'wide'}


# ── the service: upload → run → each clip a PoC, nothing posted ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def svc(monkeypatch, tmp_path):
    import feecat_service as fs
    cat = {'id': 'c1', 'name': "Happy's", 'handle': 'happy-assistant', 'chat': [], 'brainsCfg': {'brains': ['local/ossy', 'local/g4'], 'credit': 1.0}, 'pocFolders': []}
    store = {'cats': {'c1': cat}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None); monkeypatch.setattr(fs, '_media_dir', lambda: tmp_path)
    monkeypatch.setattr(fs, '_calls_of', lambda *a, **k: [])
    return fs, cat, store


def test_the_upload_door_needs_the_rights_tick_refuses_a_youtube_link_and_an_over_5_min_file(svc, tmp_path, monkeypatch):
    fs, cat, _ = svc
    from fastapi.testclient import TestClient
    import fc_clips
    c = TestClient(fs.app)
    assert 'yours' in c.post('/api/cats/c1/clipfarm/upload?name=a.mp4', content=b'x' * 2000).json()['detail']
    r = c.post('/api/cats/c1/clipfarm/link', json={'url': 'https://www.youtube.com/watch?v=abc', 'rights': True})
    assert r.status_code == 400 and "YouTube doesn't allow downloading" in r.json()['detail']
    monkeypatch.setattr(cf, 'probe', lambda p: {'secs': 364.7, 'w': 1920, 'h': 1080, 'fps': 30, 'audio': True})
    r = c.post('/api/cats/c1/clipfarm/upload?name=a.mp4&rights=1', content=b'x' * 2000)
    assert r.status_code == 400 and 'Up to 5:00' in r.json()['detail'] and not list((tmp_path / 'c1' / 'tmp').glob('up*'))   # refused file removed
    assert not fc_clips._FARMING and not cat.get('clipRuns')


@pytest.mark.skipif(not FFMPEG, reason='ffmpeg is not installed')
def test_a_run_files_each_picked_clip_as_a_poc_with_goal_cost_record_and_progress_and_posts_nothing(svc, tmp_path, monkeypatch):
    fs, cat, store = svc
    import fc_clips
    src = _video(tmp_path / 'talk.mp4', 80)
    monkeypatch.setattr(cf, 'transcribe', lambda a, model=cf.WHISPER: _words(80))
    asked = []

    async def ask(cat_, m, sys_, user_, tokens):
        asked.append((m, user_)); assert 'Score EVERY candidate' in sys_ and '#1 ' in user_
        n = 1 if m == 'local/ossy' else 2
        return json.dumps({'scores': [{'n': 1, 'score': 8, 'why': f'{m} hook'}, {'n': 2, 'score': 7, 'why': f'{m} payoff'}],
                           'picks': [{'n': n, 'hook': f'Hook by {m}', 'caption': 'cap #x', 'views': 3000}]}), 0.0012, False
    monkeypatch.setattr(fs, '_ws_ask', ask)
    info = cf.probe(src); r = fc_clips._new_run('c1', 'talk', 'upload', info, None, '', False)
    asyncio.run(fc_clips.farm('c1', r['id'], src))
    run = cat['clipRuns'][-1]
    assert run['status'] == 'done', run.get('err')
    assert [s['state'] for s in run['steps']] == ['done'] * len(cf.STEPS) and all(s.get('note') for s in run['steps'])
    assert {m for m, _ in asked} == {'local/ossy', 'local/g4'} and asked[0][1] == asked[1][1]   # blind: the same ask, neither sees the other
    assert len(run['clips']) == 2 and run['firstClipS'] > 0 and run['cost'] == pytest.approx(.0024)
    for f in cat['pocFolders']:
        s = f['studio']; assert f['kind'] == 'PoC' and s['clip']['run'] == run['id'] and f['cost'] == pytest.approx(.0012)
        assert s['goal']['target'] == 3000 and s['goal']['by'] == 'minds' and not f.get('posted') and s['maker']['watermark'] is False
        rows = {x['key']: x for x in ps.record_rows(f)}
        assert set(rows) == {'source', 'moments', 'reframe', 'files', 'approve', 'reach'} and all(x['ok'] for x in rows.values()), rows
    assert not src.exists()   # the upload is not kept, only the clips made from it
    assert '✂ 2 clips cut' in cat['chat'][-1]['text'] and 'Nothing was posted' in cat['chat'][-1]['text']


def test_the_week_slot_is_saved_by_the_owner_only_and_locked_once_posted(svc):
    fs, cat, _ = svc
    from fastapi.testclient import TestClient
    cat['pocFolders'] = [{'id': 'p1', 'n': 1, 'studio': {'clip': {'run': 'r'}, 'files': []}}]
    c = TestClient(fs.app)
    r = c.post('/api/cats/c1/clipfarm/slot', json={'job': 'p1', 'day': 'Wed'})
    assert r.status_code == 200 and cat['pocFolders'][0]['studio']['slot'] == 'Wed'
    assert c.post('/api/cats/c1/clipfarm/slot', json={'job': 'p1', 'day': 'Someday'}).status_code == 400
    assert c.post('/api/cats/c1/clipfarm/slot', json={'job': 'p1', 'day': 'Mon'}, headers={'x-feeless-internal': 'k'}).status_code == 403
    cat['pocFolders'][0]['posted'] = {'at': 1}
    assert c.post('/api/cats/c1/clipfarm/slot', json={'job': 'p1', 'day': 'Fri'}).status_code == 409


def test_an_older_copys_save_never_wipes_a_clip_run_or_its_filed_clips():
    """Seen live 2026-11-19: a copy loaded while the minds thought was saved after 3 clips filed, and they were gone. merge() adds them back."""
    import fc_clips
    fc_clips._MEM.clear()
    fc_clips._remember('c9', run={'id': 'r1', 'at': 5, 'status': 'done', 'clips': ['f1']})
    fc_clips._remember('c9', folder={'id': 'f1', 'at': 7, 'studio': {'clip': {}}})
    stale = {'cats': {'c9': {'clipRuns': [{'id': 'r1', 'at': 5, 'status': 'running', 'clips': []}], 'pocFolders': [{'id': 'old', 'at': 1}]}}}
    fc_clips.merge(stale)
    c = stale['cats']['c9']
    assert c['clipRuns'] == [{'id': 'r1', 'at': 5, 'status': 'done', 'clips': ['f1']}] and [f['id'] for f in c['pocFolders']] == ['old', 'f1']
    newer = {'cats': {'c9': {'pocFolders': [{'id': 'old', 'at': 1}, {'id': 'f1', 'at': 7, 'posted': {'at': 9}}]}}}
    fc_clips.merge(newer)
    assert newer['cats']['c9']['pocFolders'][1]['posted'] == {'at': 9}   # a folder the owner changed since is never overwritten
    fc_clips._MEM['c9']['folders']['f1'] = (0, {'id': 'f1'}); fc_clips._MEM['c9']['runs'].clear()
    gone = {'cats': {'c9': {'pocFolders': []}}}
    fc_clips.merge(gone)
    assert gone['cats']['c9']['pocFolders'] == []   # after KEEP_S it is no longer guarded (an owner's delete stays deleted)
    fc_clips._MEM.clear()


def test_a_local_minds_reply_cut_off_mid_way_still_gives_every_score_it_finished():
    """Seen live 2026-11-19: OSSY's answer was valid JSON that ran out of room in its 5th "why"; the 4 scores it finished count."""
    _w, _l, c = _cands()
    cut = '{"scores":[{"n":1,"score":9,"why":"the \\"tomato\\" seed {moment}"},{"n":2,"score":4,"why":"slow"},{"n":3,"score":3,"why":"dry"},{"n":4,"score":8,"why":"tension"},{"n":5,"score":5,"why":"Fly it is okay but the spe'
    m = cf.parse_mind(cut, c)
    assert {k: v[0] for k, v in m['scores'].items()} == {1: 9.0, 2: 4.0, 3: 3.0, 4: 8.0} and m['scores'][1][1] == 'the "tomato" seed {moment}' and m['picks'] == []
    more = cut[:cut.index(',{"n":5')] + '],"picks":[{"n":4,"hook":"Two parts showed up","caption":"c","views":900},{"n":1,"hook":"cut he'
    m = cf.parse_mind(more, c)
    assert [p['n'] for p in m['picks']] == [4] and m['picks'][0]['hook'] == 'Two parts showed up'
