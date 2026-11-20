"""✂ Slice 15 (owner 2026-11-19): the PoC clip farm, wired. An upload (or a Bluesky / direct file link; YouTube, Twitch and Instagram links keep
clip_source's rule: save it from the app, then upload) → clip_farm's free local tools → both of the agent's PoC minds pick the moments blind →
each picked clip is made in 9:16, 1:1 and 16:9 and files as its own PoC (goal + cost) beside the studio's other PoCs. Nothing posts: the clip
PoC goes out only through Slice 5's approve door (fc_poc.op 'poc_approve', the owner's click only).

  POST /api/cats/{id}/clipfarm/upload?name&ws&note&rights=1   the raw video as the body (streamed to disk, size-capped)
  POST /api/cats/{id}/clipfarm/link    {url, ws, note, rights}
  GET  /api/cats/{id}/clipfarm         the runs, each with a progress line per step, every candidate and each mind's pick and score
  POST /api/cats/{id}/clipfarm/slot    {job, day}   a clip PoC's day on the wireframe board (Mon–Sun, or '' to clear)
  GET  /api/cats/vid/{id}               🔗 an in-house FEELESS video link (the converted upload or a finished clip): unguessable id, Range, 7-day expiry
  POST /api/cats/{id}/clipfarm/unlink  {id}          the link stops working now (the converted upload's file is removed with it)
The owner signs each call (ownerId + session); Claude's TESTs use the internal key and are marked TEST."""
import asyncio
import json
import secrets
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Request

import clip_farm as _cf

router = APIRouter()
_FARMING = set()
DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
KEEP_RUNS = 12
MIND_WAIT_S = 300
LINK_S = 7 * 86400      # an in-house video link plays for 7 days, then answers 410 (its upload file is swept)
VID = __import__('re').compile(r'^v[0-9a-f]{20}$')
KEEP_S = 1800           # how long a run / clip PoC this module wrote is guarded against an older copy's save
_MEM = {}               # cat id → {'runs': {run id: (at, run)}, 'folders': {folder id: (at, folder)}}


def _remember(cat_id, run=None, folder=None):
    m = _MEM.setdefault(cat_id, {'runs': {}, 'folders': {}}); now = time.time()
    if run is not None:
        m['runs'][run['id']] = (now, json.loads(json.dumps(run)))
    if folder is not None:
        m['folders'][folder['id']] = (now, json.loads(json.dumps(folder)))


def merge(store):
    """🔒 Called by every store save (fc_core._save): an engine copy loaded before a clip run wrote its progress or filed its clips must not
    wipe them (seen 2026-11-19: a copy loaded while the minds thought was saved after 3 clips filed, and they were gone). Only adds back what
    a copy lacks, for KEEP_S after it was written; never removes, never edits a folder the owner changed since (approve, slot)."""
    now = time.time()
    for cid, m in list(_MEM.items()):
        for kind in ('runs', 'folders'):
            for k in [k for k, (t, _x) in m[kind].items() if now - t > KEEP_S]:
                m[kind].pop(k, None)
        c = (store.get('cats') or {}).get(cid)
        if not c or not (m['runs'] or m['folders']):
            continue
        if m['runs']:
            runs = list(c.get('clipRuns') or []); idx = {r.get('id'): i for i, r in enumerate(runs) if isinstance(r, dict)}
            for rid, (_t, r) in m['runs'].items():
                if rid in idx:
                    runs[idx[rid]] = json.loads(json.dumps(r))   # only this module writes a run: its last write is the newest
                else:
                    runs.append(json.loads(json.dumps(r)))
            c['clipRuns'] = sorted(runs, key=lambda r: r.get('at') or 0)[-KEEP_RUNS:]
        if m['folders']:
            rows = list(c.get('pocFolders') or []); have = {f.get('id') for f in rows if isinstance(f, dict)}
            add = [json.loads(json.dumps(f)) for fid, (_t, f) in m['folders'].items() if fid not in have]
            if add:
                c['pocFolders'] = sorted(rows + add, key=lambda f: f.get('at') or 0)[-60:]


def _rs():
    import feecat_service
    return feecat_service


def _who(request, store, cat, owner_id, session):
    """'internal' for Claude's TEST (the internal key), 'owner' for the owner's signed page; anyone else is refused."""
    rs = _rs()
    if request.headers.get('x-feeless-internal'):
        rs._internal(request)
        return 'internal'
    rs._owner_gate(store, cat, session, owner_id, 'clip its videos')
    return 'owner'


def _cat(cat_id):
    rs = _rs(); store = rs._load(); cat = (store.get('cats') or {}).get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'No such agent.')
    return store, cat


def _run_view(r):
    return {k: r.get(k) for k in ('id', 'at', 'name', 'source', 'secs', 'w', 'h', 'ws', 'test', 'status', 'steps', 'cands', 'picks', 'clips', 'cost', 'minds', 'err', 'firstClipS', 'doneS', 'words', 'cuts', 'laughs', 'note', 'links', 'ext', 'converted')}


def _set(cat_id, run_id, **kw):
    """Writes onto a run (kept on the agent, newest last, at most KEEP_RUNS)."""
    rs = _rs(); store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        return None
    r = next((x for x in cat.get('clipRuns') or [] if x.get('id') == run_id), None)
    if r is None:
        return None
    r.update(kw); _remember(cat_id, run=r); rs._save(store)
    return r


def _step(cat_id, run_id, key, state, note='', t0=None):
    rs = _rs(); store = rs._load(); cat = store['cats'].get(cat_id) or {}
    r = next((x for x in cat.get('clipRuns') or [] if x.get('id') == run_id), None)
    if r is None:
        return
    for s in r['steps']:
        if s['key'] == key:
            s['state'] = state; s['at'] = round(time.time(), 1)
            if note:
                s['note'] = str(note)[:200]
            if t0 is not None:
                s['secs'] = round(time.time() - t0, 1)
    _remember(cat_id, run=r); rs._save(store)


def _new_run(cat_id, name, source, info, ws, note, test, ext='mp4'):
    rs = _rs(); store = rs._load(); cat = store['cats'][cat_id]
    r = {'id': 'cr' + secrets.token_hex(5), 'at': round(time.time()), 'name': str(name or 'Your video')[:80], 'source': source, 'secs': info['secs'], 'w': info['w'], 'h': info['h'],
         'ws': ws or None, 'note': str(note or '')[:200], 'test': bool(test), 'status': 'running', 'cost': 0.0, 'clips': [], 'cands': [], 'picks': [],
         'steps': [{'key': k, 'label': l, 'state': 'todo'} for k, l in _cf.STEPS]}
    r['steps'][0].update(state='done', note=f"{int(info['secs'] // 60)}:{int(info['secs'] % 60):02d} · {info['w']}×{info['h']} · {info['fps']:g} fps · {info.get('box') or '?'} {info.get('vcodec')}/{info.get('acodec') or 'no sound'}", secs=0)
    r['ext'] = ext; r['links'] = []
    cat['clipRuns'] = (list(cat.get('clipRuns') or []) + [r])[-KEEP_RUNS:]; _remember(cat_id, run=r); rs._save(store)
    return r


def _link(cat_id, run_id, file_name, kind, label, folder=None, fmt=None):
    """🔗 A new in-house link to a file in this agent's media folder, kept on its run. → the link row"""
    now = time.time()
    row = {'id': 'v' + secrets.token_hex(10), 'file': file_name, 'kind': kind, 'label': str(label)[:80], 'at': round(now), 'exp': round(now + LINK_S),
           **({'folder': folder} if folder else {}), **({'fmt': fmt} if fmt else {}), 'url': ''}
    row['url'] = f"/api/cats/vid/{row['id']}"
    rs = _rs(); store = rs._load(); cat = store['cats'].get(cat_id) or {}
    r = next((x for x in cat.get('clipRuns') or [] if x.get('id') == run_id), None)
    if r is not None:
        r['links'] = (list(r.get('links') or []) + [row])[-24:]; _remember(cat_id, run=r); rs._save(store)
    return row


def _find_link(store, vid):
    for cid, c in (store.get('cats') or {}).items():
        for r in c.get('clipRuns') or []:
            for k in r.get('links') or []:
                if k.get('id') == vid:
                    return cid, c, r, k
    return None


def sweep(cat_id):
    """Expired upload links: their converted file is removed (clip files stay: their PoC needs them). → how many"""
    rs = _rs(); store = rs._load(); cat = store['cats'].get(cat_id) or {}; now = time.time(); n = 0
    for r in cat.get('clipRuns') or []:
        for k in r.get('links') or []:
            if k.get('exp', 0) < now and k.get('kind') == 'upload' and not k.get('swept'):
                (rs._media_dir() / cat_id / k['file']).unlink(missing_ok=True); k['swept'] = True; n += 1
                _remember(cat_id, run=r)
    if n:
        rs._save(store)
    return n


def _saver(cat_id):
    import fc_poc
    return fc_poc._saver(cat_id)


async def _minds(cat, run_id, cands, name, note):
    """Both PoC minds score every candidate blind (neither sees the other), one stricter retry on an unreadable answer. → (rows, cost, own, calls)"""
    rs = _rs(); brains = rs._lc.minds_for(cat.get('brainsCfg'), 'poc') or []
    rs._CALL_CTX.set({'kind': 'poc', 'ref': run_id, 'minds': brains})
    user_ = _cf.ask_text(cands, name, note)

    async def one(i, m):
        usd_all, own_any, raw, err = 0.0, False, '', ''
        for n_ in range(2):
            try:
                raw, usd, own = await asyncio.wait_for(rs._ws_ask(cat, m, _cf.SYS + f'\nYou are Mind {"AB"[i % 2]}.' + ('\n' + _cf.RETRY if n_ else ''), user_, 3200), MIND_WAIT_S)
            except Exception as e:   # noqa: BLE001: one mind down never stops the other
                err = type(e).__name__; break
            usd_all += usd or 0; own_any = own_any or own
            if _cf.parse_mind(raw, cands):
                break
        return _cf.parse_mind(raw, cands), usd_all, own_any, raw, err
    got = await asyncio.gather(*(one(i, m) for i, m in enumerate(brains[:2])))
    rows = [g[0] for g in got]; cost = sum(g[1] for g in got); own = any(g[2] for g in got)
    calls = [{'mind': i, 'name': str(brains[i]).split('/')[-1][:24], 'model': brains[i], 'read': bool(g[0]), 'err': g[4],
              'scored': len((g[0] or {}).get('scores') or {}), 'picked': [p['n'] for p in (g[0] or {}).get('picks') or []], 'raw': str(g[3] or '')[:600]} for i, g in enumerate(got)]
    return rows, cost, own, calls, brains


def _file_clip(cat_id, run, k, pick, files, tr, calls, cost_each, test_mark):
    """One clip → one PoC folder, filed through the same true record as every PoC."""
    rs = _rs(); store = rs._load(); c_ = store['cats'].get(cat_id)
    if not c_:
        return None
    rows = list(c_.get('pocFolders') or []); now = time.time()
    hook = pick['hook']; cap = pick['caption']; goal_ = _cf.goal(pick)
    studio = {'clip': {'run': run['id'], 'n': pick['n'], 'rank': k + 1, 's': pick['s'], 'e': pick['e'], 'dur': pick['dur'], 'text': pick['text'][:600], 'first2': pick['first2'],
                       'facts': pick['facts'], 'local': pick['local'], 'both': pick['both'], 'minds': [{x: m[x] for x in ('mind', 'score', 'why', 'picked')} for m in pick['minds']],
                       'lead': pick['lead'], 'payoff': pick.get('payoff') or '', 'track': tr, 'from': run['name'], 'secs': run['secs']},
              'trend': {'text': f"Your upload: {run['name']}", 'source': 'your upload' if run['source'] == 'upload' else run['source'], 'kind': 'upload'}, 'trends': [],
              'mind': pick['lead'], 'angle': f"clip {k + 1} of the upload, {pick['s']:.0f}–{pick['e']:.0f} s", 'hook': hook, 'sub': pick.get('payoff') or '',
              'post': {'story': cap, 'feed': cap, 'wide': cap}, 'links': {fl['format']: fl['link'] for fl in files if fl.get('piece') == 'video' and fl.get('link')}, 'thread': [], 'beats': [], 'goal': goal_, 'files': files, 'slot': '',
              'maker': {'name': 'FEELESS clip farm (faster-whisper + OpenCV + ffmpeg, on this machine)', 'usd': 0.0, 'watermark': False},
              'why': ' · '.join(f"Mind {'AB'[m['mind']]} {m['score']}: {m['why']}" for m in pick['minds'] if m['score'] is not None)[:400]}
    f_ = {'id': f"poc{int(now)}c{k}", **({'ws': run['ws']} if run.get('ws') else {}), 'n': rs._next_n(rows), 'kind': 'PoC', 'at': round(now), 'status': 'closed', 'paper': True,
          'topic': f"✂ {hook}"[:120], 'cost': round(cost_each, 5), 'studio': studio, 'calls': [{'mind': c['mind'], 'name': c['name'], 'angle': f"scored {c['scored']}, picked {c['picked']}",
          'post': cap if c['mind'] == pick['lead'] else '', 'why': next((m['why'] for m in pick['minds'] if m['mind'] == c['mind']), '') or c['err'], 'trend': '', 'gaps': [] if c['read'] else ['no JSON came back']} for c in calls],
          'sources': {'upload': run['name']}, 'clipRun': run['id'], 'callRefs': [run['id']],
          'kits': ['faster-whisper (word times)', 'loudness + laughs (numpy)', 'ffmpeg scdet (scene cuts)', 'OpenCV face tracker', 'ffmpeg + Pillow captions'], **({'testRun': True} if test_mark else {})}
    if test_mark:   # every clip of a TEST run carries the mark (the record takes it off after each filing)
        rs._TEST_ON[(cat_id, 'poc')] = dict(test_mark)
    rows.append(rs._record_file(c_, 'poc', f_))
    c_['pocFolders'] = rows[-60:]
    _remember(cat_id, folder=f_); rs.keep_owned(c_); rs._save(store)
    return f_


async def _converted(cat_id, run_id, run, conv, info, ext, note_, t0):
    """The converter's step is done: the clean MP4 gets its in-house link."""
    up_ = _link(cat_id, run_id, conv.name, 'upload', run['name'])
    _set(cat_id, run_id, converted={'from': f"{info.get('box') or ext}", 'note': note_, 'url': up_['url']})
    _step(cat_id, run_id, 'convert', 'done', note_ + ' · link ' + up_['url'], t0)


async def farm(cat_id, run_id, src, note=''):
    """The whole run in the background, a progress line per step. Nothing posts."""
    rs = _rs(); t_all = time.time(); test_mark = None; src = Path(src); conv_job = None; conv = None; linked = False
    try:
        cat = rs._load()['cats'].get(cat_id) or {}; run = next(x for x in cat.get('clipRuns') or [] if x['id'] == run_id)
        test_mark = dict(rs._TEST_ON.get((cat_id, 'poc')) or {}) if run.get('test') else None
        info = _cf.probe(src)
        _step(cat_id, run_id, 'convert', 'running'); t_conv = time.time(); ext = run.get('ext') or src.suffix.lstrip('.').lower()
        (rs._media_dir() / cat_id).mkdir(parents=True, exist_ok=True); conv = rs._media_dir() / cat_id / f"m{secrets.token_hex(6)}.mp4"
        orig = src
        if _cf.clean(info, ext):
            shutil.move(str(src), conv); orig = conv; linked = True
            await _converted(cat_id, run_id, run, conv, info, ext, f"already H.264 + AAC MP4: kept as it is ({conv.stat().st_size / 1e6:.0f} MB)", t_conv)
        # ⚡ an odd file: the transcript and the peaks read the original (they need only the sound and the cut times), then the converter runs
        # while the minds think (an LM Studio wait, not this Mac's CPU). Run beside the transcript it fought it for CPU: 206 s, seen live.
        _step(cat_id, run_id, 'words', 'running'); t0 = time.time()
        audio = await asyncio.to_thread(_cf.pcm, orig); words = await asyncio.to_thread(_cf.transcribe, audio)
        _step(cat_id, run_id, 'words', 'done', f'{len(words)} words, local faster-whisper ({_cf.WHISPER}), $0', t0)
        if len(words) < 20:
            raise ValueError('Almost nothing is said in it, so there is nothing to clip by words.')
        _step(cat_id, run_id, 'peaks', 'running'); t0 = time.time()
        loud = _cf.loudness(audio); cuts = await asyncio.to_thread(_cf.scene_cuts, orig); laughs = _cf.laughs(words, loud)
        _step(cat_id, run_id, 'peaks', 'done', f'{len(cuts)} scene cuts, {len(laughs)} loud moments with no words, loudness every ½ s', t0)
        _step(cat_id, run_id, 'moments', 'running'); t0 = time.time()
        cands = _cf.moments(words, loud, cuts, laughs, info['secs'])
        if not cands:
            raise ValueError('No 15–60 s stretch of speech was found in it.')
        _set(cat_id, run_id, cands=cands, words=len(words), cuts=len(cuts), laughs=len(laughs))
        _step(cat_id, run_id, 'moments', 'done', f'{len(cands)} candidates, 15–60 s, cut on sentence ends', t0)
        if orig is not conv:
            conv_job = asyncio.ensure_future(asyncio.to_thread(_cf.convert, src, conv)); await asyncio.sleep(0.5)
            if conv_job.done():
                conv_job.result()   # a file ffmpeg can't read at all stops here, before any mind is asked
        _step(cat_id, run_id, 'minds', 'running'); t0 = time.time()
        cat = rs._load()['cats'].get(cat_id) or {}
        mrows, cost, own, calls, brains = await _minds(cat, run_id, cands, run['name'], note)
        picks, ranked = _cf.choose(cands, mrows)
        read_ = sum(1 for m in mrows if m)
        _set(cat_id, run_id, cands=ranked, cost=round(cost, 5), minds=calls, picks=[{k: p[k] for k in ('n', 's', 'e', 'dur', 'hook', 'caption', 'both', 'lead')} for p in picks])
        _step(cat_id, run_id, 'minds', 'done', f"{read_} of {len(brains[:2])} minds answered · ${cost:.4f} · {len(picks)} clips picked", t0)
        if cost and not own and cat.get('brainsCfg'):
            store = rs._load(); c_ = store['cats'].get(cat_id)
            if c_:
                rs._lc.charge(c_['brainsCfg'], cost); rs._save(store)
        if not picks:
            raise ValueError('Neither mind found a moment worth a clip (every score under 4).')
        if conv_job is not None:
            secs_ = await conv_job; src.unlink(missing_ok=True); linked = True
            await _converted(cat_id, run_id, run, conv, info, ext, f"{(info.get('box') or ext)} {info.get('vcodec')}/{info.get('acodec') or 'no sound'} → H.264/AAC .mp4, {conv.stat().st_size / 1e6:.0f} MB in {secs_} s, $0 (ran while the minds thought)", t_conv)
        src = conv; info = _cf.check(_cf.probe(src), src.stat().st_size)
        _step(cat_id, run_id, 'clips', 'running', f'0 of {len(picks)} clips'); t0 = time.time(); filed = []
        for k, p in enumerate(picks):
            files, tr = await asyncio.to_thread(_cf.make_clip, src, p, words, info, cuts, _saver(cat_id), 'ffmpeg',
                                                lambda fmt, k=k: _step(cat_id, run_id, 'clips', 'running', f'clip {k + 1} of {len(picks)}: {_cf.FORMATS[fmt][2]} made'))
            for fl in files:   # 🔗 every finished clip format gets its own in-house link, pasted into its PoC
                if fl.get('piece') == 'video' and fl.get('url'):
                    fl['link'] = _link(cat_id, run_id, fl['url'].rsplit('/', 1)[-1], 'clip', f"{p['hook']} · {_cf.FORMATS[fl['format']][2]}", fmt=fl['format'])['url']
            f_ = _file_clip(cat_id, run, k, p, files, tr, calls, cost / len(picks), test_mark)
            if f_:
                filed.append(f_['id'])
                _set(cat_id, run_id, clips=list(filed), **({'firstClipS': round(time.time() - t_all, 1)} if k == 0 else {}))
            _step(cat_id, run_id, 'clips', 'running', f'{k + 1} of {len(picks)} clips filed')
        _step(cat_id, run_id, 'clips', 'done', f'{len(filed)} clips, each in 9:16, 1:1 and 16:9 with captions and a cover', t0)
        _step(cat_id, run_id, 'file', 'done', f'{len(filed)} PoCs filed with a goal and cost · nothing posted: each waits for your approve', None)
        _set(cat_id, run_id, status='done', doneS=round(time.time() - t_all, 1))
        store = rs._load(); c_ = store['cats'].get(cat_id)
        if c_:
            c_['chat'] = (list(c_.get('chat') or []) + [{'by': 'cats', 'text': f"✂ {len(filed)} clips cut from \"{run['name'][:50]}\" in {time.time() - t_all:.0f} s, each filed as a PoC in 9:16, 1:1 and 16:9. Nothing was posted: approve each one to post.", 'at': time.time(), 'open': 'features'}])[-200:]
            rs._save(store)
    except Exception as e:   # noqa: BLE001
        print(f'[clipfarm] {cat_id[:8]} {run_id}: {type(e).__name__}: {str(e)[:200]}')
        try:
            cat = rs._load()['cats'].get(cat_id) or {}; r = next((x for x in cat.get('clipRuns') or [] if x['id'] == run_id), {})
            for s in r.get('steps') or []:
                if s['state'] == 'running':
                    _step(cat_id, run_id, s['key'], 'failed', str(e)[:160])
            _set(cat_id, run_id, status='failed', err=str(e)[:200] if isinstance(e, ValueError) else f'{type(e).__name__}: {str(e)[:160]}')
        except Exception:   # noqa: BLE001
            pass
    finally:
        if conv_job is not None and not conv_job.done():   # a run that failed beside the converter waits for it before the upload goes
            try:
                await conv_job
            except Exception:   # noqa: BLE001
                pass
        if conv is not None and not linked:
            conv.unlink(missing_ok=True)   # a half-made MP4 with no link is never kept
        _FARMING.discard(cat_id)
        if test_mark is not None:
            rs._TEST_ON.pop((cat_id, 'poc'), None)
        try:
            if src.parent.name == 'tmp':   # the raw upload (before the converter) is never kept; the converted copy lives on behind its link
                src.unlink(missing_ok=True)
        except OSError:
            pass


def _start(cat_id, cat, who, path, name, source, ws, note):
    """Probe → limits → a run → the farm in the background. Removes the file on any refusal."""
    rs = _rs()
    try:
        info = _cf.check(_cf.probe(path), path.stat().st_size)
    except ValueError as e:
        path.unlink(missing_ok=True)
        raise rs.HTTPException(400, str(e))
    test = who == 'internal'
    if test:
        rs._TEST_ON[(cat_id, 'poc')] = {'at': time.time(), 'by': 'Claude', 'run': secrets.token_hex(5), 'topic': f'clip farm: {name}'[:120]}
    r = _new_run(cat_id, name, source, info, ws, note, test, path.suffix.lstrip('.').lower())
    _FARMING.add(cat_id)
    asyncio.create_task(farm(cat_id, r['id'], path, note))
    return {'run': _run_view(r)}


def _gate_start(cat_id, cat, who):
    rs = _rs()
    if cat_id in _FARMING:
        raise rs.HTTPException(409, 'A clip run is already going on this agent. It takes a minute or two.')
    if not shutil.which('ffmpeg'):
        raise rs.HTTPException(503, 'ffmpeg is not installed on this machine.')
    import fc_test as _ft
    if who != 'internal':
        return
    if cat.get('handle') not in set(_ft.AGENTS.values()):
        raise rs.HTTPException(403, 'A TEST runs on the TEST agents only.')
    pair = rs._lc.minds_for(cat.get('brainsCfg'), 'poc')
    if cat.get('handle') == _ft.SICARIO and (not pair or any(not str(m).startswith('local/') for m in pair)):   # §1: Sicario's TEST runs on free local minds only
        raise rs.HTTPException(409, f"Sicario's PoC pair is {pair or 'not set'}: a TEST runs only on free local minds (local/…).")
    if cat.get('handle') != _ft.SICARIO:   # 💸 Happy's: the owner's TEST caps, the same count test-proof uses
        rows_ = rs._calls_of(cat_id); all_, kind_ = _ft.spent_since(rows_), _ft.spent_since(rows_, kind='poc')
        if all_ >= _ft.TEST_BUDGET_USD or kind_ >= _ft.KIND_BUDGET_USD:
            raise rs.HTTPException(402, f"TESTs on {cat.get('name')} have spent ${all_:.2f} of ${_ft.TEST_BUDGET_USD:.2f} in all and ${kind_:.2f} of ${_ft.KIND_BUDGET_USD:.2f} on PoC: the owner's caps.")
    if _ft._test_live(cat, 'poc'):
        raise rs.HTTPException(409, 'A TEST PoC is still running on this agent.')


def _tmp(cat_id, ext):
    rs = _rs(); d = rs._media_dir() / cat_id / 'tmp'; d.mkdir(parents=True, exist_ok=True)
    return d / f"up{secrets.token_hex(6)}.{ext}"


@router.post('/api/cats/{cat_id}/clipfarm/upload')
async def clip_upload(cat_id: str, request: Request, name: str = '', ws: str = '', note: str = '', rights: int = 0, ownerId: str = '', session: str = ''):
    """📤 The video itself as the request body (no JSON, no base64): streamed to disk, stopped at the size cap, read by ffprobe before anything runs."""
    rs = _rs(); store, cat = _cat(cat_id); who = _who(request, store, cat, ownerId, session)
    if not rights:
        raise rs.HTTPException(400, 'Tick that the video is yours, or that you have the rights to use it.')
    _gate_start(cat_id, cat, who)
    try:
        ext = _cf.ext_of(name, request.headers.get('content-type', ''))
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    if int(request.headers.get('content-length') or 0) > _cf.MAX_BYTES:
        raise rs.HTTPException(413, f'Up to {_cf.MAX_BYTES // 1_000_000} MB: export it smaller.')
    out = _tmp(cat_id, ext); got = 0
    try:
        with out.open('wb') as fh:
            async for ch in request.stream():
                got += len(ch)
                if got > _cf.MAX_BYTES:
                    raise rs.HTTPException(413, f'Up to {_cf.MAX_BYTES // 1_000_000} MB: export it smaller.')
                fh.write(ch)
    except BaseException:
        out.unlink(missing_ok=True)
        raise
    if got < 1000:
        out.unlink(missing_ok=True)
        raise rs.HTTPException(400, 'The file did not come through. Try again.')
    return _start(cat_id, cat, who, out, rs.re.sub(r'\.[A-Za-z0-9]+$', '', str(name or 'Your video'))[:80], 'upload', str(ws or '')[:40], note)


@router.post('/api/cats/{cat_id}/clipfarm/link')
async def clip_link(cat_id: str, request: Request):
    """🔗 A Bluesky post or a direct .mp4 / .webm / .mov link. YouTube, Twitch, Instagram, TikTok, X, Facebook: refused with what to do instead."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _who(request, store, cat, str(body.get('ownerId') or ''), str(body.get('session') or ''))
    if not body.get('rights'):
        raise rs.HTTPException(400, 'Tick that the video is yours, or that you have the rights to use it.')
    _gate_start(cat_id, cat, who)
    url = str(body.get('url') or '').strip()
    try:
        how = rs._cs.classify(url)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    out = _tmp(cat_id, 'mp4'); name = ''
    try:
        async with rs.httpx.AsyncClient(timeout=25, follow_redirects=False) as h_:
            if how[0] == 'bluesky':
                r_ = await h_.get(rs._cs.bsky_thread_url(how[1], how[2]), headers={'User-Agent': 'FEELESS/1.0'})
                if r_.status_code != 200:
                    raise ValueError('Bluesky did not find that post.')
                pl, words_ = rs._cs.bsky_video(r_.json()); name = (f'@{how[1].split(".")[0]}: {words_}' if words_ else f'@{how[1]} on Bluesky')[:80]
                if (await rs._ffmpeg(rs._cs.cut_args(pl, out, 0, _cf.MAX_S + 1, stream=True), 300))[0] != 0 or not out.is_file():
                    raise ValueError("Bluesky's video did not come through. Try again in a minute.")
                source = 'Bluesky'
            else:
                await rs._cp.public_url(how[1]); got = 0
                async with h_.stream('GET', how[1], headers={'User-Agent': 'FEELESS/1.0'}) as r_:
                    if r_.status_code != 200 or not r_.headers.get('content-type', '').startswith('video/'):
                        raise ValueError('That link did not give a video file.')
                    with out.open('wb') as fh:
                        async for ch in r_.aiter_bytes():
                            got += len(ch)
                            if got > _cf.MAX_BYTES:
                                raise ValueError(f'That video is over {_cf.MAX_BYTES // 1_000_000} MB.')
                            fh.write(ch)
                from urllib.parse import unquote, urlparse
                name = rs.re.sub(r'\.[A-Za-z0-9]+$', '', unquote(how[1].rsplit('/', 1)[-1]))[:80] or 'Linked video'; source = urlparse(how[1]).hostname or 'link'
    except (ValueError, rs.httpx.HTTPError) as e:
        out.unlink(missing_ok=True)
        raise rs.HTTPException(400, str(e) if isinstance(e, ValueError) else 'That link did not answer. Try again, or upload the file.')
    return _start(cat_id, cat, who, out, name, source, str(body.get('ws') or '')[:40], str(body.get('note') or ''))


@router.get('/api/cats/{cat_id}/clipfarm')
async def clip_runs(cat_id: str, request: Request, ownerId: str = '', session: str = ''):
    store, cat = _cat(cat_id); _who(request, store, cat, ownerId, session)
    if sweep(cat_id):
        store, cat = _cat(cat_id)
    return {'runs': [_run_view(r) for r in reversed(cat.get('clipRuns') or [])], 'busy': cat_id in _FARMING,
            'limits': {'secs': _cf.MAX_S, 'mb': _cf.MAX_BYTES // 1_000_000, 'types': sorted(_cf.EXTS), 'clip': [_cf.CLIP_MIN, _cf.CLIP_MAX]}}


@router.post('/api/cats/{cat_id}/clipfarm/slot')
async def clip_slot(cat_id: str, request: Request):
    """🗓 A clip PoC's day on the wireframe board. The owner's page only; locked once it posted."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id)
    if request.headers.get('x-feeless-internal'):
        raise rs.HTTPException(403, 'Only its owner plans the week.')
    rs._owner_gate(store, cat, str(body.get('session') or ''), str(body.get('ownerId') or ''), 'plan its week')
    day = str(body.get('day') or '')
    if day and day not in DAYS:
        raise rs.HTTPException(400, 'Pick a day, Mon to Sun.')
    f = next((x for x in cat.get('pocFolders') or [] if x.get('id') == str(body.get('job') or '') and isinstance((x.get('studio') or {}).get('clip'), dict)), None)
    if not f:
        raise rs.HTTPException(404, 'No such clip PoC.')
    if (f.get('posted') or {}).get('at'):
        raise rs.HTTPException(409, 'It already posted.')
    f['studio']['slot'] = day; f['studio']['slotAt'] = round(time.time())
    rs.keep_owned(cat); rs._save(store)
    return {'pocFolders': rs._poc_view(cat)}


def byte_range(header, size):
    """'bytes=a-b' / 'bytes=a-' / 'bytes=-n' → (start, end) inside the file, None when absent or several ranges, 'bad' when unsatisfiable. Pure."""
    m = __import__('re').fullmatch(r'\s*bytes=(\d*)-(\d*)\s*', str(header or ''))
    if not m or (not m.group(1) and not m.group(2)):
        return None
    if not m.group(1):
        n = int(m.group(2)); return (max(0, size - n), size - 1) if n else 'bad'
    a = int(m.group(1)); b = min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
    return (a, b) if a < size and a <= b else 'bad'


@router.get('/api/cats/vid/{vid}')
async def video_link(vid: str, request: Request):
    """🔗 An in-house FEELESS video link: the id is the permission (80 random bits, never listed anywhere public), Range requests so it seeks
    at once, inline in the browser (a phone opens it straight away), 410 after its 7 days or once deleted."""
    rs = _rs()
    from starlette.responses import FileResponse
    if not VID.fullmatch(str(vid or '')):
        raise rs.HTTPException(404, 'No such video.')
    hit = _find_link(rs._load(), vid)
    if not hit:
        raise rs.HTTPException(404, 'No such video.')
    cid, _c, _r, k = hit
    if k.get('exp', 0) < time.time() or k.get('gone'):
        raise rs.HTTPException(410, 'This video link has ended.')
    f_ = rs._media_dir() / cid / str(k.get('file') or '')
    if not rs._mg.NAME.fullmatch(f_.name) or not f_.is_file():
        raise rs.HTTPException(410, 'This video link has ended.')
    head = {'Cache-Control': 'private, max-age=3600', 'X-Robots-Tag': 'noindex, nofollow', 'Content-Disposition': 'inline', 'X-Content-Type-Options': 'nosniff',
            'Accept-Ranges': 'bytes'}
    size = f_.stat().st_size; rg = byte_range(request.headers.get('range'), size)
    if rg == 'bad':
        return rs.Response(status_code=416, headers={**head, 'Content-Range': f'bytes */{size}'})
    if rg is None:
        return FileResponse(f_, media_type='video/mp4', headers=head)
    from starlette.responses import StreamingResponse
    a, b = rg

    def chunks():   # seeks straight to the asked part, 1 MB at a time: a phone scrubbing a 100 MB clip never waits for the whole file
        with f_.open('rb') as fh:
            fh.seek(a); left = b - a + 1
            while left > 0:
                buf = fh.read(min(1 << 20, left))
                if not buf:
                    break
                left -= len(buf); yield buf
    return StreamingResponse(chunks(), status_code=206, media_type='video/mp4', headers={**head, 'Content-Range': f'bytes {a}-{b}/{size}', 'Content-Length': str(b - a + 1)})


@router.post('/api/cats/{cat_id}/clipfarm/unlink')
async def unlink(cat_id: str, request: Request):
    """The link stops now. An upload link also removes the converted upload's file; a clip link only ends the link (its PoC keeps the clip)."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); _who(request, store, cat, str(body.get('ownerId') or ''), str(body.get('session') or ''))
    vid = str(body.get('id') or '')
    for r in cat.get('clipRuns') or []:
        for k in r.get('links') or []:
            if k.get('id') == vid and not k.get('gone'):
                k['gone'] = round(time.time())
                if k.get('kind') == 'upload':
                    (rs._media_dir() / cat_id / k['file']).unlink(missing_ok=True)
                _remember(cat_id, run=r); rs._save(store)
                return {'run': _run_view(r)}
    raise rs.HTTPException(404, 'No such link.')
