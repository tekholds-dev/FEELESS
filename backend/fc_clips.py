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
import re
import secrets
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Request

import clip_farm as _cf
import clip_look as _cl

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
        for kind in ('runs', 'folders', 'looks'):
            for k in [k for k, (t, _x) in m.setdefault(kind, {}).items() if now - t > KEEP_S]:
                m[kind].pop(k, None)
        c = (store.get('cats') or {}).get(cid)
        if not c or not (m['runs'] or m['folders'] or m.get('looks')):
            continue
        if m['runs']:
            runs = list(c.get('clipRuns') or []); idx = {r.get('id'): i for i, r in enumerate(runs) if isinstance(r, dict)}
            for rid, (_t, r) in m['runs'].items():
                if rid in idx:
                    runs[idx[rid]] = json.loads(json.dumps(r))   # only this module writes a run: its last write is the newest
                else:
                    runs.append(json.loads(json.dumps(r)))
            c['clipRuns'] = sorted(runs, key=lambda r: r.get('at') or 0)[-KEEP_RUNS:]
        for fid, (_t, keep) in (m.get('looks') or {}).items():   # 🎨 Slice 29: a clip's look, versions, files and render state are written only here
            f = next((x for x in c.get('pocFolders') or [] if isinstance(x, dict) and x.get('id') == fid), None)
            if f is not None and isinstance(f.get('studio'), dict):
                f['studio'].update(json.loads(json.dumps(keep)))
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


def _new_run(cat_id, name, source, info, ws, note, test, ext='mp4', tpl='minds'):
    rs = _rs(); store = rs._load(); cat = store['cats'][cat_id]
    r = {'id': 'cr' + secrets.token_hex(5), 'at': round(time.time()), 'name': str(name or 'Your video')[:80], 'source': source, 'secs': info['secs'], 'w': info['w'], 'h': info['h'],
         'ws': ws or None, 'note': str(note or '')[:200], 'test': bool(test), 'status': 'running', 'cost': 0.0, 'clips': [], 'cands': [], 'picks': [],
         'steps': [{'key': k, 'label': l, 'state': 'todo'} for k, l in _cf.STEPS]}
    r['steps'][0].update(state='done', note=f"{int(info['secs'] // 60)}:{int(info['secs'] % 60):02d} · {info['w']}×{info['h']} · {info['fps']:g} fps · {info.get('box') or '?'} {info.get('vcodec')}/{info.get('acodec') or 'no sound'}", secs=0)
    r['ext'] = ext; r['links'] = []; r['tpl'] = tpl or 'minds'   # 🎨 the look every clip of this run starts in: a template, or the minds pick one per clip
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
        ks = list(r.get('links') or []) + [row]   # the upload row is never trimmed (it is what every re-render cuts from, and what sweep() deletes on day 7)
        r['links'] = [k for k in ks if k.get('kind') == 'upload'] + [k for k in ks if k.get('kind') != 'upload'][-24:]; _remember(cat_id, run=r); rs._save(store)
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
              **({'look': pick['look'], 'fmtLooks': pick.get('fmtLooks') or {}, 'tpl': pick.get('tpl'),
                  'looks': [{'v': 1, 'at': round(now), 'by': (pick.get('tpl') or {}).get('by') or 'code', 'why': (f"{pick['tpl']['name']}: {pick['tpl']['why']}" if pick.get('tpl') else
                             f"starting look: {pick['look'].get('preset') or 'classic'}, nudged so no other clip shares it")[:200],
                             'look': pick['look'], 'files': files, 'fmtLooks': pick.get('fmtLooks') or {}, 'tpl': pick.get('tpl')}]} if pick.get('look') else {}),
              'why': ' · '.join(f"Mind {'AB'[m['mind']]} {m['score']}: {m['why']}" for m in pick['minds'] if m['score'] is not None)[:400]}
    f_ = {'id': f"poc{int(now)}c{k}", **({'ws': run['ws']} if run.get('ws') else {}), 'n': rs._next_n(rows), 'kind': 'PoC', 'at': round(now), 'status': 'closed', 'paper': True,
          'topic': f"✂ {hook}"[:120], 'cost': round(cost_each, 5), 'studio': studio, 'calls': [{'mind': c['mind'], 'name': c['name'], 'angle': f"scored {c['scored']}, picked {c['picked']}",
          'post': cap if c['mind'] == pick['lead'] else '', 'why': next((m['why'] for m in pick['minds'] if m['mind'] == c['mind']), '') or c['err'], 'trend': '', 'gaps': [] if c['read'] else ['no JSON came back']} for c in calls],
          'sources': {'upload': run['name']}, 'clipRun': run['id'], 'callRefs': [run['id']],
          'kits': ['faster-whisper (word times)', 'loudness + laughs (numpy)', 'ffmpeg scdet (scene cuts)', 'OpenCV face tracker', 'ffmpeg + Pillow captions', 'clip looks (ffmpeg filters: captions, transitions, effects)'], **({'testRun': True} if test_mark else {})}
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
        # ⚡ Slice 24: the scene cuts (ffmpeg on the CPU) run beside the transcript (whisper on Apple's GPU): 5:00 HEVC .mov, both done in ~15 s, not 68
        _step(cat_id, run_id, 'words', 'running'); _step(cat_id, run_id, 'peaks', 'running'); t0 = time.time()
        cut_job = asyncio.ensure_future(asyncio.to_thread(_cf.scene_cuts, orig))
        try:
            audio = await asyncio.to_thread(_cf.pcm, orig); words = await asyncio.to_thread(_cf.transcribe, audio)
        except BaseException:
            cut_job.cancel(); raise
        _step(cat_id, run_id, 'words', 'done', f'{len(words)} words, local faster-whisper ({_cf.WHISPER}), $0', t0)
        if len(words) < 20:
            cut_job.cancel()
            raise ValueError('Almost nothing is said in it, so there is nothing to clip by words.')
        loud = _cf.loudness(audio); cuts = await cut_job; laughs = _cf.laughs(words, loud)
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
        cat = rs._load()['cats'].get(cat_id) or {}; used = _used_sigs(cat)
        rows_t, tcost, town, tmind = await _run_tpls(cat_id, cat, run, picks)   # 🎨 the add-on: each clip starts in a template (the run's, or the minds' pick per clip)
        if tcost:
            _charge(cat_id, cat, tcost, town); _set(cat_id, run_id, cost=round(cost + tcost, 5))
        fd = fmt_defaults(cat); tl = []
        for k, p in enumerate(picks):
            tp, why, by = rows_t[k]; look, note = _cl.unique(tpl_look(tp), used); used.add(_cl.sig(look)); p['look'] = look
            p['tpl'] = {'id': tp['id'], 'name': tp['name'], 'by': by, 'why': (why + (f' · {note}' if note else ''))[:200], 'at': round(time.time()), **({'mind': tmind} if by == 'minds' else {})}
            p['fmtLooks'] = {fm: tpl_look(ft) for fm, ft in fd.items() if ft['id'] != tp['id']}
            tl.append({'n': p['n'], 'tpl': tp['id'], 'name': tp['name'], 'by': by, 'why': p['tpl']['why'], 'fmts': {fm: ft['name'] for fm, ft in fd.items() if ft['id'] != tp['id']}})
        _set(cat_id, run_id, tpls=tl, tplBy={'mode': run.get('tpl') or 'minds', 'mind': tmind, 'cost': round(tcost, 5)})
        for k, p in enumerate(picks):
            keep_ = (lambda pts, p=p: _keep_data(cat_id, run_id, p['n'], src.name, [w for w in words if w['e'] > p['s'] and w['s'] < p['e']], pts))
            files, tr = await asyncio.to_thread(_cf.make_clip, src, p, words, info, cuts, _saver(cat_id), 'ffmpeg',
                                                lambda fmt, k=k: _step(cat_id, run_id, 'clips', 'running', f'clip {k + 1} of {len(picks)}: {_cf.FORMATS[fmt][2]} made'), p['look'], keep_, None, p.get('fmtLooks'))
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


def _start(cat_id, cat, who, path, name, source, ws, note, tpl=''):
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
    r = _new_run(cat_id, name, source, info, ws, note, test, path.suffix.lstrip('.').lower(), run_tpl(cat, tpl))
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
async def clip_upload(cat_id: str, request: Request, name: str = '', ws: str = '', note: str = '', rights: int = 0, ownerId: str = '', session: str = '', tpl: str = ''):
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
    return _start(cat_id, cat, who, out, rs.re.sub(r'\.[A-Za-z0-9]+$', '', str(name or 'Your video'))[:80], 'upload', str(ws or '')[:40], note, tpl)


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
    return _start(cat_id, cat, who, out, name, source, str(body.get('ws') or '')[:40], str(body.get('note') or ''), str(body.get('tpl') or ''))


@router.get('/api/cats/{cat_id}/clipfarm')
async def clip_runs(cat_id: str, request: Request, ownerId: str = '', session: str = ''):
    store, cat = _cat(cat_id); _who(request, store, cat, ownerId, session)
    if sweep(cat_id):
        store, cat = _cat(cat_id)
    stuck = {f['id'] for f in _clips(cat) if (f['studio'].get('render') or {}).get('state') == 'running' and f['id'] not in (_QUEUE.get(cat_id) or set())
             and time.time() - (f['studio']['render'].get('at') or 0) > 120}
    if stuck:   # 🎨 a render cut off (a service restart) or its result lost: it renders again
        _queue(cat_id, stuck)
    twins = unique_pass(cat)
    if twins:   # 🎨 clips made before the studio all share the first look: each gets its own (once, $0, local) and renders
        rs = _rs(); _keep_looks(cat); rs._save(store); _queue(cat_id, set(twins))
    return {'runs': [_run_view(r) for r in reversed(cat.get('clipRuns') or [])], 'busy': cat_id in _FARMING, 'plan': plan_view(cat), 'rendering': sorted(_QUEUE.get(cat_id) or []),
            'kit': LOOK_KIT, 'templates': tpl_view(cat),
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
    _plan_from_slots(cat, f"{'PoC #' + str(f.get('n'))} {'to ' + day if day else 'taken off the week'} (its day buttons)")   # Slice 29: the same saved plan, versioned
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


# ── 🎨🗓 Slice 29 (owner 2026-11-20): the clip studio. Each clip's look (captions, transition, effects) set by the owner or the minds and
# rendered here by ffmpeg ($0, no watermark, no two clips the same look), versioned with undo; one week plan per agent (drag, or "agent plans
# it" with a why per slot) with a chat inside it that changes the plan AND the clips. Nothing here posts: Slice 5's approve door still does.
#   POST /api/cats/{id}/clipfarm/look        {job, look | patch | preset}   the owner's look → a new version, rendered in the background
#   POST /api/cats/{id}/clipfarm/look/mind   {job, ask}                     the lead PoC mind picks this clip's look
#   POST /api/cats/{id}/clipfarm/look/undo   {job, v}                       back to look version v (its files come back, nothing re-renders)
#   GET  /api/cats/{id}/clipfarm/words?job   the clip's words with times (the editor + its live preview)
#   POST /api/cats/{id}/clipfarm/plan        {slots, why}                   the owner's dragged week → a new plan version
#   POST /api/cats/{id}/clipfarm/plan/agent  {}                             the minds fill the week from the scores + the trend reader
#   POST /api/cats/{id}/clipfarm/plan/chat   {text}                         the chat in the plan: moves + look changes, one new version
#   POST /api/cats/{id}/clipfarm/plan/undo   {v}                            back to plan version v (slots and each clip's look)
PLATS = ('tiktok', 'instagram', 'youtube', 'x')
PLAN_KEEP, CHAT_KEEP = 40, 60
BEST_TIMES = {'tiktok': ('Tue–Thu', '19:00'), 'instagram': ('Mon, Wed, Fri', '12:00'), 'youtube': ('Fri–Sun', '16:00'), 'x': ('Mon–Thu', '09:00')}   # common public guidance, a start only
LOOK_KIT = {'fonts': {k: v[0] for k, v in _cl.FONTS.items()}, 'colors': list(_cl.BASE_COLORS), 'hot': list(_cl.HOT_COLORS), 'sizes': list(_cl.SIZES), 'pos': list(_cl.POS),
            'modes': list(_cl.MODES), 'trans': list(_cl.TRANS), 'grades': list(_cl.GRADES), 'speeds': list(_cl.SPEEDS), 'presets': list(_cl.PRESET_ORDER),
            'presetLooks': {k: _cl.preset(k) for k in _cl.PRESET_ORDER}, 'plats': list(PLATS), 'days': list(DAYS)}
_QUEUE = {}       # cat id → {job, …} waiting for or in a render
_RENDERING = set()


LOOK_KEYS = ('look', 'looks', 'files', 'links', 'render', 'fmtLooks', 'tpl')


def _keep_looks(cat):
    """Remember every clip's look fields as this module last wrote them, so an older store copy's save can't undo a render (seen 2026-11-20)."""
    m = _MEM.setdefault(cat['id'], {'runs': {}, 'folders': {}}); lk = m.setdefault('looks', {}); now = time.time()
    for f in _clips(cat):
        if f['studio'].get('looks') or f['studio'].get('render'):
            lk[f['id']] = (now, json.loads(json.dumps({k: f['studio'][k] for k in LOOK_KEYS if k in f['studio']})))


def _clips(cat):
    return [f for f in cat.get('pocFolders') or [] if isinstance((f.get('studio') or {}).get('clip'), dict)]


def _used_sigs(cat, but=''):
    return {_cl.sig(f['studio']['look']) for f in _clips(cat) if f['studio'].get('look') and f.get('id') != but}


def _data_path(cat_id, run_id, n):
    return _rs()._media_dir() / cat_id / f'cd_{run_id}_{n}.json'


def _keep_data(cat_id, run_id, n, src_name, words, pts):
    """A clip's words and tracked points, kept beside its files so an edit re-renders without a new transcript or track."""
    p = _data_path(cat_id, run_id, n); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({'src': src_name, 'words': words, 'pts': pts}))


def _src_of(cat, f):
    """The converted upload this clip was cut from, if it is still kept (7 days behind its link). → Path or None"""
    run = next((r for r in cat.get('clipRuns') or [] if r.get('id') == f['studio']['clip'].get('run')), None) or {}
    up = next((k for k in run.get('links') or [] if k.get('kind') == 'upload' and not k.get('swept') and not k.get('gone')), None)
    p = _rs()._media_dir() / cat['id'] / up['file'] if up else None
    return p if p and p.is_file() else None


def _clip_data(cat, f):
    """→ {src, words, pts}; a clip made before Slice 29 gets its window transcribed and tracked once, then kept."""
    c = f['studio']['clip']; p = _data_path(cat['id'], c['run'], c['n']); src = _src_of(cat, f)
    if src is None:
        raise ValueError('The upload this clip came from is gone (it is kept 7 days). Upload the video again to edit its clips.')
    d = json.loads(p.read_text()) if p.is_file() else {}
    if not d.get('words'):
        d['words'] = _cl.window_words(src, c['s'], c['e'])
    if not d.get('pts'):
        d['pts'] = _cf.track(src, c['s'], c['e'], _cf.probe(src))['pts']
    d['src'] = src.name; p.write_text(json.dumps(d))
    return {**d, 'path': src}


def _look_now(f):
    s_ = f['studio']
    return _cl.clean_look(s_.get('look') or _cl.DEFAULT)


def _seed(f):
    """A clip from before Slice 29 (no look versions): its first version is the look and files it was made with."""
    s_ = f['studio']
    if not s_.get('looks') and s_.get('files'):
        s_['looks'] = [{'v': 1, 'at': f.get('at'), 'by': 'code', 'why': 'how it was first made', 'look': _cl.clean_look(s_.get('look') or _cl.DEFAULT), 'files': s_.get('files') or []}]
        s_['look'] = s_['looks'][0]['look']


_KEEP = object()


def _add_look(f, look, by, why, files=None, fmt_looks=_KEEP, tpl=_KEEP):
    """A new look version. `fmt_looks` {format: look} (a per-format template) and `tpl` (the template it came from) ride the version, so an
    undo brings them back; an edit by hand keeps them and marks the template edited."""
    _seed(f); s_ = f['studio']; vs = list(s_.get('looks') or [])
    fl = dict(s_.get('fmtLooks') or {}) if fmt_looks is _KEEP else {k: _cl.clean_look(x) for k, x in (fmt_looks or {}).items() if k in FMTS}
    tp = ({**s_['tpl'], 'edited': True} if s_.get('tpl') else None) if tpl is _KEEP else tpl
    v = {'v': (vs[-1]['v'] + 1) if vs else 1, 'at': round(time.time()), 'by': by, 'why': str(why or '')[:200], 'look': _cl.clean_look(look), 'files': files,
         'fmtLooks': fl, 'tpl': tp}
    s_['looks'] = (vs + [v])[-20:]; s_['look'] = v['look']; s_['fmtLooks'] = fl; s_['tpl'] = tp
    if files is not None:
        s_['files'] = files
    return v


def _queue(cat_id, jobs):
    """Renders run one agent at a time, in the background, story format first."""
    q = _QUEUE.setdefault(cat_id, set()); q.update(jobs)
    if cat_id not in _RENDERING:
        _RENDERING.add(cat_id); asyncio.ensure_future(_render_all(cat_id))


async def _render_all(cat_id):
    rs = _rs()
    try:
        while _QUEUE.get(cat_id):
            job = sorted(_QUEUE[cat_id])[0]
            try:
                await _render_one(cat_id, job)
            except Exception as e:   # noqa: BLE001: one clip's failure is shown on that clip, the rest still render
                store = rs._load(); f = next((x for x in (store['cats'].get(cat_id) or {}).get('pocFolders') or [] if x.get('id') == job), None)
                if f:
                    f['studio']['render'] = {'state': 'failed', 'at': round(time.time()), 'err': str(e)[:200] if isinstance(e, ValueError) else f'{type(e).__name__}: {str(e)[:160]}'}
                    _keep_looks(store['cats'][cat_id]); rs._save(store)
            _QUEUE[cat_id].discard(job)
    finally:
        _RENDERING.discard(cat_id); _QUEUE.pop(cat_id, None)


async def _render_one(cat_id, job):
    rs = _rs(); store = rs._load(); cat = store['cats'].get(cat_id) or {}; f = next((x for x in cat.get('pocFolders') or [] if x.get('id') == job), None)
    if not f or (f.get('posted') or {}).get('at'):
        return
    look = _look_now(f); v = (f['studio'].get('looks') or [{}])[-1].get('v'); t0 = time.time()
    f['studio']['render'] = {'state': 'running', 'at': round(t0), 'v': v}; _keep_looks(cat); rs._save(store)
    d = await asyncio.to_thread(_clip_data, cat, f); info = _cf.check(_cf.probe(d['path']), d['path'].stat().st_size)
    c = f['studio']['clip']; pick = {'s': c['s'], 'e': c['e'], 'hook': f['studio'].get('hook') or '', 'caption': (f['studio'].get('post') or {}).get('story') or f['studio'].get('hook') or ''}
    fl = {k: _cl.clean_look({**x, 'edit': look['edit']}) for k, x in (f['studio'].get('fmtLooks') or {}).items()}   # a per-format template keeps the clip's word edits
    files, _tr = await asyncio.to_thread(_cf.make_clip, d['path'], pick, d['words'], info, (), _saver(cat_id), 'ffmpeg', None, look, None, d['pts'], fl)
    for fl in files:
        if fl.get('piece') == 'video' and fl.get('url'):
            fl['link'] = _link(cat_id, c['run'], fl['url'].rsplit('/', 1)[-1], 'clip', f"{pick['hook']} · {_cf.FORMATS[fl['format']][2]} · look v{v}", fmt=fl['format'])['url']
    store = rs._load(); cat = store['cats'].get(cat_id) or {}; f = next((x for x in cat.get('pocFolders') or [] if x.get('id') == job), None)
    if not f:
        return
    s_ = f['studio']; row = next((x for x in s_.get('looks') or [] if x.get('v') == v), None)
    if row is not None:
        row['files'] = files
    if (s_.get('looks') or [{}])[-1].get('v') == v:   # a newer look while it rendered: that one renders next and wins
        s_['files'] = files; s_['links'] = {fl['format']: fl['link'] for fl in files if fl.get('piece') == 'video' and fl.get('link')}
    s_['render'] = {'state': 'done', 'at': round(time.time()), 'v': v, 'secs': round(time.time() - t0, 1), 'errs': [fl['error'] for fl in files if fl.get('error')][:3]}
    _keep_looks(cat); rs._save(store)


def unique_pass(cat):
    """No two clips the same look: every unposted clip whose look another clip already has (or that has none) gets the nearest free one,
    as a 'code' version. Only clips whose upload is still kept (so it can render). → the clip ids changed"""
    used, out = set(), []
    for f in sorted(_clips(cat), key=lambda x: (not (x.get('posted') or {}).get('at'), x.get('at') or 0)):   # posted clips keep theirs, oldest first
        lk = _look_now(f); sg = _cl.sig(lk)
        if sg in used and not (f.get('posted') or {}).get('at') and f['studio'].get('files') and _src_of(cat, f) is not None and (f['studio'].get('render') or {}).get('state') != 'running':
            new = _cl.lucky(len(used), used); _add_look(f, new, 'code', 'its own starting look: another clip had the same one'); sg = _cl.sig(new); out.append(f['id'])
        elif not f['studio'].get('look') and f['studio'].get('files'):
            _seed(f)
        used.add(sg)
    return out


def _find_clip(cat, job):
    f = next((x for x in _clips(cat) if x.get('id') == str(job or '')), None)
    if not f:
        raise _rs().HTTPException(404, 'No such clip PoC.')
    return f


def _gate(request, store, cat, body, what):
    """The owner's signed page, or Claude's TEST (internal key) inside the owner's caps. → 'owner' | 'internal'"""
    rs = _rs()
    if request.headers.get('x-feeless-internal'):
        rs._internal(request)
        return 'internal'
    rs._owner_gate(store, cat, str(body.get('session') or ''), str(body.get('ownerId') or ''), what)
    return 'owner'


def _set_look(cat, f, look, by, why, owner, tpl=_KEEP):
    """A new look version (unique among this agent's clips) → (version, note). The owner's exact copy of another clip is refused."""
    rs = _rs()
    if (f.get('posted') or {}).get('at'):
        raise rs.HTTPException(409, 'It already posted: its look is locked.')
    used = _used_sigs(cat, but=f['id']); look = _cl.clean_look(look); note = ''
    if _cl.sig(look) in used:
        twin = next((x for x in _clips(cat) if x['id'] != f['id'] and x['studio'].get('look') and _cl.sig(x['studio']['look']) == _cl.sig(look)), {})
        if owner:
            raise rs.HTTPException(409, f"PoC #{twin.get('n')} already has this exact look. Change one thing (a colour, the grade, the font…) so no two clips look the same.")
        look, note = _cl.unique(look, used)
    return _add_look(f, look, by, (why + (f' · {note}' if note else '')).strip(' ·'), None, _KEEP, tpl), note


@router.post('/api/cats/{cat_id}/clipfarm/look')
async def clip_look(cat_id: str, request: Request):
    """🎨 The owner's look for one clip (a whole look, a partial patch or a named preset) → a new version, rendered in the background."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _gate(request, store, cat, body, 'edit its clips')
    f = _find_clip(cat, body.get('job')); cur = _look_now(f)
    look = (_cl.merge(cur, {'preset': body['preset']}) if body.get('preset') else _cl.merge(cur, body['patch']) if isinstance(body.get('patch'), dict)
            else _cl.clean_look(body.get('look')))
    if _cl.sig(look) == _cl.sig(cur) and look['edit'] == cur['edit']:
        raise rs.HTTPException(400, 'Nothing changed.')
    tp = find_tpl(cat, body.get('tpl')) if body.get('tpl') else None   # picked from a template in the editor: the clip says which
    tpl = ({'id': tp['id'], 'name': tp['name'], 'by': 'owner', 'why': f"your template: {tp['name']}", 'at': round(time.time()),
            **({'edited': True} if _cl.sig(look) != _cl.sig(tpl_look(tp)) else {})} if tp else _KEEP)
    v, _n = _set_look(cat, f, look, 'TEST' if who == 'internal' else 'owner', str(body.get('why') or 'your edit'), owner=who == 'owner', tpl=tpl)
    rs.keep_owned(cat); _keep_looks(cat); rs._save(store); _queue(cat_id, {f['id']})
    return {'pocFolders': rs._poc_view(cat), 'v': v['v']}


@router.post('/api/cats/{cat_id}/clipfarm/look/undo')
async def clip_look_undo(cat_id: str, request: Request):
    """↩ Back to an earlier look of a clip: its files come back as they were (no new render), as a new version so it can be redone."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); _gate(request, store, cat, body, 'edit its clips')
    f = _find_clip(cat, body.get('job'))
    if (f.get('posted') or {}).get('at'):
        raise rs.HTTPException(409, 'It already posted: its look is locked.')
    old = next((x for x in f['studio'].get('looks') or [] if x.get('v') == int(body.get('v') or 0)), None)
    if not old:
        raise rs.HTTPException(404, 'No such look version.')
    if _cl.sig(old['look']) in _used_sigs(cat, but=f['id']):
        raise rs.HTTPException(409, 'Another clip has that look now. Change that clip first, so no two clips look the same.')
    _add_look(f, old['look'], 'undo', f"back to look v{old['v']}", old.get('files'), old.get('fmtLooks') or {}, old.get('tpl'))
    if old.get('files'):
        f['studio']['links'] = {fl['format']: fl['link'] for fl in old['files'] if fl.get('piece') == 'video' and fl.get('link')}
        f['studio']['render'] = {'state': 'done', 'at': round(time.time()), 'v': f['studio']['looks'][-1]['v'], 'secs': 0}
    rs.keep_owned(cat); _keep_looks(cat); rs._save(store)
    if not old.get('files'):
        _queue(cat_id, {f['id']})
    return {'pocFolders': rs._poc_view(cat)}


@router.get('/api/cats/{cat_id}/clipfarm/words')
async def clip_words(cat_id: str, request: Request, job: str = '', ownerId: str = '', session: str = ''):
    """The clip's words (times from the clip start) for the caption editor and its live preview."""
    rs = _rs(); store, cat = _cat(cat_id); _who(request, store, cat, ownerId, session); f = _find_clip(cat, job); c = f['studio']['clip']
    try:
        d = await asyncio.to_thread(_clip_data, cat, f)
    except ValueError as e:
        raise rs.HTTPException(410, str(e))
    ws = [{'i': i, 'w': w['w'], 's': round(w['s'] - c['s'], 2), 'e': round(w['e'] - c['s'], 2)} for i, w in enumerate(x for x in d['words'] if x['e'] > c['s'] and x['s'] < c['e'])]
    return {'words': ws, 'dur': round(c['e'] - c['s'], 2), 'face': _cl.face_y(d.get('pts'))}   # where the speaker's face sits: the preview keeps captions off it too


# ── the week plan ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def clean_slots(slots, cat):
    """Any slots (the page's, a mind's) → valid ones: a known clip once each, Mon–Sun, HH:MM, known platforms. A posted clip keeps its day. Pure but for the clip list."""
    ids = {f['id']: f for f in _clips(cat)}; out, seen = [], set()
    for x in slots if isinstance(slots, list) else []:
        if not isinstance(x, dict):
            continue
        j = str(x.get('job') or ''); day = str(x.get('day') or '')[:3].title()
        if j not in ids or j in seen or day not in DAYS:
            continue
        t = str(x.get('time') or '18:00'); m = __import__('re').match(r'^(\d{1,2}):(\d{2})$', t)
        t = f'{min(23, int(m[1])):02d}:{min(59, int(m[2])):02d}' if m else '18:00'
        pl = [p for p in (x.get('plats') or ['tiktok', 'instagram', 'youtube']) if p in PLATS] or ['tiktok']
        seen.add(j); out.append({'job': j, 'day': day, 'time': t, 'plats': sorted(set(pl), key=PLATS.index), 'why': ' '.join(str(x.get('why') or '').split())[:200]})
    for j, f in ids.items():   # a posted clip's day never moves
        if (f.get('posted') or {}).get('at') and f['studio'].get('slot') and j not in seen:
            out.append({'job': j, 'day': f['studio']['slot'], 'time': f['studio'].get('slotTime') or '18:00', 'plats': f['studio'].get('slotPlats') or ['tiktok'], 'why': 'posted'})
    return sorted(out, key=lambda r: (DAYS.index(r['day']), r['time']))


def plan_view(cat):
    p = cat.get('clipPlan') or {}
    return {'versions': [{k: v.get(k) for k in ('v', 'at', 'by', 'why', 'slots', 'looks', 'cost', 'mind', 'test')} for v in (p.get('versions') or [])[-PLAN_KEEP:]],
            'cur': p.get('cur'), 'chat': (p.get('chat') or [])[-CHAT_KEEP:]}


def _new_plan(cat, slots, by, why, cost=0.0, mind='', test=False):
    """One new version of the week (slots + every clip's look version at that moment); the clips' days follow it."""
    p = cat.setdefault('clipPlan', {'versions': [], 'chat': []}); vs = p.setdefault('versions', [])
    slots = clean_slots(slots, cat)
    for f in _clips(cat):
        _seed(f)
    v = {'v': (vs[-1]['v'] + 1) if vs else 1, 'at': round(time.time()), 'by': by, 'why': str(why or '')[:300], 'slots': slots,
         'looks': {f['id']: (f['studio'].get('looks') or [{}])[-1].get('v') for f in _clips(cat) if f['studio'].get('looks')}, 'cost': round(float(cost or 0), 5), 'mind': mind, 'test': bool(test)}
    p['versions'] = (vs + [v])[-PLAN_KEEP:]; p['cur'] = v['v']
    by_job = {s['job']: s for s in slots}
    for f in _clips(cat):
        if (f.get('posted') or {}).get('at'):
            continue
        s_ = by_job.get(f['id']); st = f['studio']
        st['slot'] = s_['day'] if s_ else ''; st['slotTime'] = s_['time'] if s_ else ''; st['slotPlats'] = s_['plats'] if s_ else []; st['slotWhy'] = s_['why'] if s_ else ''
        st['slotAt'] = round(time.time())
    return v


def _plan_from_slots(cat, why):
    cur = {s['job']: s for s in (plan_view(cat)['versions'] or [{}])[-1].get('slots') or []}
    slots = [{**cur.get(f['id'], {}), 'job': f['id'], 'day': f['studio']['slot']} for f in _clips(cat) if f['studio'].get('slot')]
    return _new_plan(cat, slots, 'owner', why)


def _clip_lines(cat):
    rows = []
    for f in sorted(_clips(cat), key=lambda x: -(x['studio']['clip'].get('both') or 0)):
        s_ = f['studio']; c = s_['clip']
        rows.append(f"{f['id']} | PoC #{f.get('n')} | score {c.get('both') if c.get('both') is not None else '—'}/10 | {round(c.get('dur') or 0)} s | hook: {s_.get('hook')} | "
                    f"look: {_cl.describe(_look_now(f))} | {'POSTED (locked)' if (f.get('posted') or {}).get('at') else ('planned ' + s_['slot'] + ' ' + (s_.get('slotTime') or '')) if s_.get('slot') else 'not planned'}")
    return '\n'.join(rows)


async def _trend_lines():
    try:
        rs = _rs()
        async with rs.httpx.AsyncClient(timeout=8, follow_redirects=True) as http:
            d = await rs._tools.trending(http)
        tops = [t for _k, v in (d.get('trends') or {}).items() for t in (v or [])[:3]][:8]
        clips = [str(c.get('text') or '')[:70] for c in (d.get('clips') or [])[:4]]
        return '; '.join(map(str, tops + clips))[:900]
    except Exception:   # noqa: BLE001: the plan still gets made from the scores alone
        return ''


async def _ask_lead(cat, sys_, user_, tokens=1800):
    """The agent's lead PoC mind (the free local one first). → (raw, usd, own, model)"""
    rs = _rs(); brains = rs._lc.minds_for(cat.get('brainsCfg'), 'poc') or []
    if not brains:
        raise ValueError('This agent has no PoC minds set (Brains).')
    m = brains[0]; rs._CALL_CTX.set({'kind': 'poc', 'ref': 'clip-plan', 'minds': brains[:1]})
    raw, usd, own = await asyncio.wait_for(rs._ws_ask(cat, m, sys_, user_, tokens), MIND_WAIT_S)
    return raw, float(usd or 0), own, str(m)


def _charge(cat_id, cat, cost, own):
    rs = _rs()
    if cost and not own and cat.get('brainsCfg'):
        store = rs._load(); c_ = store['cats'].get(cat_id)
        if c_:
            rs._lc.charge(c_['brainsCfg'], cost); rs._save(store)


def _test_caps(cat_id, cat):
    """Claude's TEST asks the minds only inside the owner's caps (Happy) or on free local minds (Sicario)."""
    rs = _rs(); import fc_test as _ft
    if cat.get('handle') not in set(_ft.AGENTS.values()):
        raise rs.HTTPException(403, 'A TEST runs on the TEST agents only.')
    pair = rs._lc.minds_for(cat.get('brainsCfg'), 'poc')
    if cat.get('handle') == _ft.SICARIO and (not pair or not str(pair[0]).startswith('local/')):
        raise rs.HTTPException(409, "Sicario's TEST runs only on free local minds.")
    if cat.get('handle') != _ft.SICARIO:
        rows_ = rs._calls_of(cat_id)
        if _ft.spent_since(rows_) >= _ft.TEST_BUDGET_USD or _ft.spent_since(rows_, kind='poc') >= _ft.KIND_BUDGET_USD:
            raise rs.HTTPException(402, "TESTs on this agent have reached the owner's caps.")


def code_plan(cat):
    """The week from the scores alone (when no mind answers): best clips on the strongest days, one a day. Pure but for the clip list."""
    order = ['Tue', 'Thu', 'Fri', 'Wed', 'Mon', 'Sat', 'Sun']; out = []
    free = [f for f in sorted(_clips(cat), key=lambda x: -(x['studio']['clip'].get('both') or 0)) if not (f.get('posted') or {}).get('at')]
    for k, f in enumerate(free[:7]):
        out.append({'job': f['id'], 'day': order[k], 'time': '19:00', 'plats': ['tiktok', 'instagram', 'youtube'],
                    'why': f"score {f['studio']['clip'].get('both')}/10, {k + 1}{'st' if k == 0 else 'nd' if k == 1 else 'rd' if k == 2 else 'th'} best: on {order[k]}, a strong day for short video"})
    return out


PLAN_SYS = ('You plan one posting week (Mon–Sun) for short vertical clips. Use the clips\' scores, hooks and what is trending now. Spread them: at most one clip a '
            'day unless there are more than 7, the best ones on the strongest days, and a clear reason for every slot (score, trend fit, platform timing). '
            f'Platforms: {", ".join(PLATS)}. Times are HH:MM local. Posted clips are locked. Answer ONLY with JSON: '
            '{"slots":[{"job":"<clip id>","day":"Mon","time":"19:00","plats":["tiktok","instagram"],"why":"at most 20 words"}],"note":"one line"}')


@router.post('/api/cats/{cat_id}/clipfarm/plan')
async def plan_save(cat_id: str, request: Request):
    """🗓 The owner's week (dragged on the board) → a new plan version."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _gate(request, store, cat, body, 'plan its week')
    v = _new_plan(cat, body.get('slots'), 'TEST' if who == 'internal' else 'owner', str(body.get('why') or 'your week'), test=who == 'internal')
    rs.keep_owned(cat); _keep_looks(cat); rs._save(store)
    return {'plan': plan_view(cat), 'pocFolders': rs._poc_view(cat), 'v': v['v']}


@router.post('/api/cats/{cat_id}/clipfarm/plan/agent')
async def plan_agent(cat_id: str, request: Request):
    """🧠 "Agent plans it": the lead PoC mind fills the week from the clip scores and the trend reader, with a why for each slot."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _gate(request, store, cat, body, 'plan its week')
    if who == 'internal':
        _test_caps(cat_id, cat)
    if not _clips(cat):
        raise rs.HTTPException(400, 'No clips yet: clip a video first.')
    trends = await _trend_lines()
    user_ = (f"CLIPS (id | PoC | score | length | hook | look | status):\n{_clip_lines(cat)}\n\nTRENDING NOW: {trends or 'the trend reader could not be read'}\n"
             f"BEST TIMES (common guidance): " + '; '.join(f'{k} {d} {t}' for k, (d, t) in BEST_TIMES.items()) + f"\nOWNER NOTE: {str(body.get('note') or '')[:200]}")
    cost, mind, slots, note = 0.0, '', [], ''
    try:
        raw, cost, own, mind = await _ask_lead(cat, PLAN_SYS, user_)
        j = _cf._json(raw) or {}; slots = clean_slots(j.get('slots'), cat); note = str(j.get('note') or '')[:200]
        _charge(cat_id, cat, cost, own)
    except Exception as e:   # noqa: BLE001: no answer → the code's plan, said plainly
        note = f'the mind did not answer ({type(e).__name__})'
    by = 'minds' if slots else 'code'
    if not slots:
        slots = code_plan(cat); note = (note + ' · ' if note else '') + 'planned by code from the scores'
    store, cat = _cat(cat_id)
    v = _new_plan(cat, slots, by, f"{'Agent plans it' if by == 'minds' else 'Code plan'}: {note}".strip(': '), cost, mind.split('/')[-1], who == 'internal')
    rs.keep_owned(cat); _keep_looks(cat); rs._save(store)
    return {'plan': plan_view(cat), 'pocFolders': rs._poc_view(cat), 'v': v['v']}


CHAT_SYS = ('You are the clip editor inside the owner\'s posting-week plan. He asks for changes in plain words ("move the best one to Friday, make Tuesday '
            'funnier"). You change the plan (moves) and the clips\' looks. A look patch may set: "preset" (' + ', '.join(_cl.PRESET_ORDER) + '), '
            '"cap" {font: ' + '/'.join(_cl.FONTS) + ', color: ' + '/'.join(_cl.BASE_COLORS) + ', hot: ' + '/'.join(_cl.HOT_COLORS) + ', size: S/M/L, pos: '
            + '/'.join(_cl.POS) + ', style: ' + '/'.join(_cl.STYLES) + ' (never a flat slab: prefer the modern ones), safe: face/ui/off, mode: ' + '/'.join(_cl.MODES)
            + ' (classic style only), words: 1-6, case: upper/said}, "tr": ' + '/'.join(_cl.TRANS) + ', "fx" {punch: bool, shake: bool, '
            'grade: ' + '/'.join(_cl.GRADES) + ', speed: ' + '/'.join(_cl.SPEEDS) + ', pop: bool}. Funnier = faster speed, word pops, bouncy captions, zoom or glitch. '
            'Posted clips are locked. Answer ONLY with JSON: {"reply":"one or two short sentences to the owner","moves":[{"job":"<id>","day":"Fri","time":"19:00",'
            '"plats":["tiktok"],"why":"…"}],"looks":[{"job":"<id>","patch":{…},"why":"…"}],"remove":["<id taken off the week>"]}')


@router.post('/api/cats/{cat_id}/clipfarm/plan/chat')
async def plan_chat(cat_id: str, request: Request):
    """💬 The chat in the plan: the owner asks, the lead mind changes the plan and the clips. One new version, every change undoable."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _gate(request, store, cat, body, 'plan its week')
    text = ' '.join(str(body.get('text') or '').split())[:500]
    if not text:
        raise rs.HTTPException(400, 'Say what to change.')
    if who == 'internal':
        _test_caps(cat_id, cat)
    pv = plan_view(cat); cur = (pv['versions'] or [{}])[-1].get('slots') or []
    hist = '\n'.join(f"{m['by']}: {m['text']}" for m in pv['chat'][-6:])
    user_ = (f"THE WEEK NOW: {json.dumps(cur)}\n\nCLIPS (id | PoC | score | length | hook | look | status):\n{_clip_lines(cat)}\n\nCHAT SO FAR:\n{hist or '—'}\n\nOWNER: {text}")
    p = cat.setdefault('clipPlan', {'versions': [], 'chat': []}); at = round(time.time())
    try:
        raw, cost, own, mind = await _ask_lead(cat, CHAT_SYS, user_)
    except Exception as e:   # noqa: BLE001
        raise rs.HTTPException(502, f'The mind did not answer ({type(e).__name__}). Nothing changed.')
    j = _cf._json(raw) or {}
    store, cat = _cat(cat_id); _charge(cat_id, cat, cost, own); p = cat.setdefault('clipPlan', {'versions': [], 'chat': []})
    slots = {s['job']: dict(s) for s in ((p.get('versions') or [{}])[-1].get('slots') or [])}
    for jid in j.get('remove') or []:
        f = next((x for x in _clips(cat) if x['id'] == str(jid)), None)
        if f and not (f.get('posted') or {}).get('at'):
            slots.pop(str(jid), None)
    for mv in j.get('moves') or []:
        if isinstance(mv, dict) and str(mv.get('job')) in {f['id'] for f in _clips(cat)}:
            slots[str(mv['job'])] = {**slots.get(str(mv['job']), {}), **{k: mv[k] for k in ('day', 'time', 'plats', 'why') if mv.get(k)}, 'job': str(mv['job'])}
    changed, notes = [], []
    for lk in j.get('looks') or []:
        f = next((x for x in _clips(cat) if isinstance(lk, dict) and x['id'] == str(lk.get('job'))), None)
        if not f or (f.get('posted') or {}).get('at') or not isinstance(lk.get('patch'), dict):
            continue
        new = _cl.merge(_look_now(f), lk['patch'])
        if _cl.sig(new) == _cl.sig(_look_now(f)):
            continue
        _v, note = _set_look(cat, f, new, 'chat', str(lk.get('why') or text)[:160], owner=False); changed.append(f['id'])
        if note:
            notes.append(f"PoC #{f.get('n')}: {note}")
    reply = str(j.get('reply') or '').strip()[:400] or ('Done.' if (changed or j.get('moves') or j.get('remove')) else 'I could not read a change in that. Nothing changed.')
    v = None
    if changed or j.get('moves') or j.get('remove'):
        v = _new_plan(cat, list(slots.values()), 'chat', f'Chat: {text[:120]}', cost, mind.split('/')[-1], who == 'internal')
    p['chat'] = (list(p.get('chat') or []) + [{'by': 'owner' if who == 'owner' else 'TEST', 'text': text, 'at': at},
                                              {'by': 'mind', 'mind': mind.split('/')[-1], 'text': reply + (f" ({'; '.join(notes)})" if notes else ''), 'at': round(time.time()),
                                               'v': v['v'] if v else None, 'looks': changed, 'cost': round(cost, 5)}])[-CHAT_KEEP:]
    rs.keep_owned(cat); _keep_looks(cat); rs._save(store)
    if changed:
        _queue(cat_id, set(changed))
    return {'plan': plan_view(cat), 'pocFolders': rs._poc_view(cat), 'v': v['v'] if v else None}


@router.post('/api/cats/{cat_id}/clipfarm/plan/undo')
async def plan_undo(cat_id: str, request: Request):
    """↩ Back to plan version v: its slots, and every clip back to the look it had then (as new versions, so it can be redone)."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _gate(request, store, cat, body, 'plan its week')
    p = cat.get('clipPlan') or {}; old = next((x for x in p.get('versions') or [] if x.get('v') == int(body.get('v') or 0)), None)
    if not old:
        raise rs.HTTPException(404, 'No such plan version.')
    redo = []
    for f in _clips(cat):
        want = (old.get('looks') or {}).get(f['id']); now = (f['studio'].get('looks') or [{}])[-1].get('v')
        if want and want != now and not (f.get('posted') or {}).get('at'):
            row = next((x for x in f['studio'].get('looks') or [] if x.get('v') == want), None)
            if row:
                _add_look(f, row['look'], 'undo', f"plan back to v{old['v']}", row.get('files'), row.get('fmtLooks') or {}, row.get('tpl'))
                if row.get('files'):
                    f['studio']['links'] = {fl['format']: fl['link'] for fl in row['files'] if fl.get('piece') == 'video' and fl.get('link')}
                else:
                    redo.append(f['id'])
    _new_plan(cat, old.get('slots'), 'undo', f"back to plan v{old['v']}", test=who == 'internal')
    rs.keep_owned(cat); _keep_looks(cat); rs._save(store)
    if redo:
        _queue(cat_id, set(redo))
    return {'plan': plan_view(cat), 'pocFolders': rs._poc_view(cat)}


@router.post('/api/cats/{cat_id}/clipfarm/look/mind')
async def clip_look_mind(cat_id: str, request: Request):
    """🧠 The lead PoC mind designs this clip's look (unique among its clips), with a why; rendered like any other look."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _gate(request, store, cat, body, 'edit its clips')
    if who == 'internal':
        _test_caps(cat_id, cat)
    f = _find_clip(cat, body.get('job'))
    if (f.get('posted') or {}).get('at'):
        raise rs.HTTPException(409, 'It already posted: its look is locked.')
    others = '\n'.join(f"PoC #{x.get('n')}: {_cl.describe(_look_now(x))}" for x in _clips(cat) if x['id'] != f['id'])
    user_ = (f"THIS CLIP: hook \"{f['studio'].get('hook')}\", {round(f['studio']['clip'].get('dur') or 0)} s, said: \"{str(f['studio']['clip'].get('text') or '')[:400]}\"\n"
             f"ITS LOOK NOW: {_cl.describe(_look_now(f))}\nOTHER CLIPS' LOOKS (yours must differ):\n{others or '—'}\nOWNER ASKS: {str(body.get('ask') or 'make it stand out')[:200]}")
    sys_ = CHAT_SYS.split('Answer ONLY')[0] + 'Design ONE look for this clip that fits what is said. Answer ONLY with JSON: {"patch":{…},"why":"at most 20 words"}'
    try:
        raw, cost, own, mind = await _ask_lead(cat, sys_, user_, 900)
    except Exception as e:   # noqa: BLE001
        raise rs.HTTPException(502, f'The mind did not answer ({type(e).__name__}). Nothing changed.')
    j = _cf._json(raw) or {}
    store, cat = _cat(cat_id); _charge(cat_id, cat, cost, own); f = _find_clip(cat, body.get('job'))
    if not isinstance(j.get('patch'), dict):
        raise rs.HTTPException(502, 'The mind\'s answer had no look in it. Nothing changed.')
    v, note = _set_look(cat, f, _cl.merge(_look_now(f), j['patch']), 'minds', f"{mind.split('/')[-1]}: {str(j.get('why') or '')[:140]}", owner=False)
    v['cost'] = round(cost, 5)
    rs.keep_owned(cat); _keep_looks(cat); rs._save(store); _queue(cat_id, {f['id']})
    return {'pocFolders': rs._poc_view(cat), 'v': v['v'], 'note': note}


# ── 🎨 Slice 29 add-on (owner 2026-11-20: "should be able to set edit formats and templates … cooler captions"; "i was speaking of the clip
# farming too"): saved templates (a whole look: captions, transitions, effects, safe area, which formats), per-agent defaults per format,
# per platform and for the farm, one tap to apply to a clip, a run or the week; the farm makes every clip in its template. Nothing posts.
FMTS = ('story', 'feed', 'wide')
PLAT_FMT = {'tiktok': 'story', 'instagram': 'story', 'youtube': 'story', 'x': 'wide'}   # the file each platform posts
DEF_DEFAULTS = {'farm': 'minds', 'story': '', 'feed': '', 'wide': '', 'tiktok': '', 'instagram': '', 'youtube': '', 'x': ''}
TPL_KEEP = 40


def builtins():
    """The six modern caption templates first, then the six Slice 29 presets (kept: nothing that worked is lost). Pure."""
    return [{'id': f'b:{k}', 'name': _cl.TEMPLATE_NAMES[k], 'look': _cl.preset(k), 'fmts': list(FMTS), 'by': 'FEELESS', 'builtin': True, 'legacy': k in _cl.LEGACY}
            for k in _cl.PRESET_ORDER + _cl.LEGACY]


def tpl_store(cat):
    t = cat.get('clipTpl') if isinstance(cat.get('clipTpl'), dict) else {}
    return {'list': [x for x in t.get('list') or [] if isinstance(x, dict) and x.get('id')], 'defaults': {**DEF_DEFAULTS, **{k: v for k, v in (t.get('defaults') or {}).items() if k in DEF_DEFAULTS}}}


def all_tpls(cat):
    return builtins() + tpl_store(cat)['list']


def find_tpl(cat, tid):
    return next((x for x in all_tpls(cat) if x['id'] == str(tid or '')), None)


def tpl_look(tp, edit=None):
    """A template's look for one clip (the clip's own word edits kept). Pure."""
    lk = _cl.clean_look(tp['look'])
    if edit:
        lk['edit'] = _cl.clean_look({'edit': edit})['edit']
    return lk


def run_tpl(cat, tpl):
    """What a new run starts in: the tap on the upload card, else the owner's farm default, else the minds. → 'minds' | template id"""
    want = str(tpl or '') or tpl_store(cat)['defaults']['farm'] or 'minds'
    return want if want == 'minds' or find_tpl(cat, want) else 'minds'


def fmt_defaults(cat):
    """The per-format defaults in force: a format's own default, else the first platform default that posts that format. → {fmt: template}"""
    d = tpl_store(cat)['defaults']; out = {}
    for fm in FMTS:
        tid = d.get(fm) or next((d[p] for p, f in PLAT_FMT.items() if f == fm and d.get(p)), '')
        tp = find_tpl(cat, tid) if tid else None
        if tp:
            out[fm] = tp
    return out


def tpl_view(cat):
    st = tpl_store(cat)
    return {'list': [{**x, 'describe': _cl.describe(x['look'])} for x in all_tpls(cat)], 'defaults': st['defaults'], 'styles': _cl.STYLES, 'safes': _cl.SAFES,
            'platFmt': PLAT_FMT, 'inForce': {fm: tp['id'] for fm, tp in fmt_defaults(cat).items()}}


def code_tpl(c, free):
    """The template that fits a clip's mood when no mind answers: numbers → gradient keyword, a question or a laugh → emoji accent, long and
    calm → lower-third, a top score → bold outline, else pop highlight; the first free one when that is taken in this run. → (id, why) Pure."""
    txt = f"{c.get('hook') or ''} {c.get('text') or ''}"
    want, why = (('b:gradient', 'numbers in it: the key figure gets the gradient') if re.search(r'\d|\$', txt) else
                 ('b:emoji', 'a question or a laugh: an emoji lands the feeling') if re.search(r'\?|haha|funny|laugh', txt.lower()) else
                 ('b:lower', 'long and calm: a quiet lower-third keeps the face clear') if float(c.get('dur') or 0) >= 40 else
                 ('b:outline', 'a top score: the loudest look') if float(c.get('both') or 0) >= 8 else ('b:pop', 'a talking moment: word-by-word pop keeps eyes on it'))
    if want in free:
        return want, why
    return (free[0], f"{why.split(':')[0]}, but another clip in this run has that one") if free else (want, why)


def _code_pairs(cat, items):
    """Every clip its mood's template by code, all different. → [(template, why, 'code')]"""
    free = [x['id'] for x in all_tpls(cat) if not x.get('legacy')]; out = []
    for c in items:
        tid, why = code_tpl(c, free); free = [x for x in free if x != tid] or free; out.append((find_tpl(cat, tid), why, 'code'))
    return out


TPL_SYS = ('You pick a caption TEMPLATE for each short vertical clip so its look fits the clip\'s mood and hook (calm → minimal, numbers → gradient '
           'keyword, a joke → emoji, a big claim → bold outline …). Every clip gets a DIFFERENT template. Answer ONLY with JSON: '
           '{"picks":[{"k":<clip k>,"tpl":"<template id>","why":"at most 14 words, about the clip"}]}')


async def _pick_tpls(cat_id, cat, items, ask=''):
    """The lead PoC mind picks a template per clip (all different), code fills any gap. items: [{k, hook, text, dur, both}] → ([(template, why, by)], cost, own, mind)"""
    tps = [x for x in all_tpls(cat) if not x.get('legacy')]; ids = [x['id'] for x in tps]; got, cost, own, mind = {}, 0.0, False, ''
    try:
        user_ = ('TEMPLATES:\n' + '\n'.join(f"{x['id']}: {x['name']} — {_cl.describe(x['look'])}" for x in tps) + '\nCLIPS:\n'
                 + '\n'.join(f"k={c['k']}: hook \"{c.get('hook')}\", {round(float(c.get('dur') or 0))} s, score {c.get('both')}, said \"{str(c.get('text') or '')[:260]}\"" for c in items)
                 + (f"\nOWNER ASKS: {str(ask)[:200]}" if ask else ''))
        raw, cost, own, mind = await _ask_lead(cat, TPL_SYS, user_, 900)
        for r in (_cf._json(raw) or {}).get('picks') or []:
            if isinstance(r, dict) and r.get('tpl') in ids and str(r.get('k')) not in got:
                got[str(r.get('k'))] = (r['tpl'], ' '.join(str(r.get('why') or '').split())[:140])
    except Exception as e:   # noqa: BLE001: no mind → the code's pick, said so on the clip
        mind = f'code ({type(e).__name__})'
    out, taken = [], set()
    for c in items:
        tid, why = got.get(str(c['k']), ('', ''))
        by = 'minds' if tid else 'code'
        if not tid or tid in taken:   # no answer for it, or a twin of another clip's: the code picks a free one by its mood
            tid, why = code_tpl(c, [i for i in ids if i not in taken]); by = 'code'
        taken.add(tid); out.append((find_tpl(cat, tid), why or 'its own template', by))
    return out, cost, own, mind.split('/')[-1]


async def _run_tpls(cat_id, cat, run, picks):
    """The farm's templates for a run's picks: the run's chosen one for all, or the minds' pick per clip. → ([(template, why, by)], cost, own, mind)"""
    want = run.get('tpl') or 'minds'
    if want != 'minds':
        tp = find_tpl(cat, want) or find_tpl(cat, 'b:pop')
        return [(tp, f"your pick for this run: {tp['name']}", 'owner')] * len(picks), 0.0, False, ''
    if run.get('test'):
        try:
            _test_caps(cat_id, cat)
        except Exception:   # noqa: BLE001: past the TEST caps the code picks
            return _code_pairs(cat, picks), 0.0, False, 'code'
    return await _pick_tpls(cat_id, cat, [{'k': i, 'hook': p.get('hook'), 'text': p.get('text'), 'dur': p.get('dur'), 'both': p.get('both')} for i, p in enumerate(picks)])


def _targets(cat, body):
    """The clips a template goes onto: one clip (job), a whole run, or the planned week. Posted clips are locked."""
    rs = _rs(); cs = [f for f in _clips(cat) if not (f.get('posted') or {}).get('at')]
    if body.get('job'):
        out = [f for f in cs if f['id'] == str(body['job'])]
    elif body.get('run'):
        out = [f for f in cs if f['studio']['clip'].get('run') == str(body['run'])]
    elif body.get('week'):
        out = [f for f in cs if f['studio'].get('slot')]
    else:
        raise rs.HTTPException(400, 'Say which clips: one clip, a run or the week.')
    if not out:
        raise rs.HTTPException(404, 'No clip to change there (posted clips are locked).')
    live = [f for f in out if _src_of(cat, f) is not None]   # a clip whose upload is gone can't re-render: it keeps its look and nobody pays for it
    if not live:
        raise rs.HTTPException(409, 'The upload these clips came from is gone (it is kept 7 days). Upload the video again to restyle them.')
    return live, [f"PoC #{f['n']}: its upload is gone, left as it was" for f in out if f not in live]


def _apply(cat, f, tp, by, why, used, extra=None):
    """One template onto one clip: a whole-format template becomes its look (per-format overrides cleared); a template for some formats only
    becomes those formats' look. Nudged so no two clips share a look. → note"""
    cur = _look_now(f); lk = tpl_look(tp, cur['edit']); fm = [x for x in tp.get('fmts') or FMTS if x in FMTS] or list(FMTS)
    if set(fm) == set(FMTS):
        base, fl = lk, {}
    else:
        base, fl = cur, {**(f['studio'].get('fmtLooks') or {}), **{x: lk for x in fm}}
    base, note = _cl.unique(base, used)
    _add_look(f, base, by, (why + (f' · {note}' if note else ''))[:200], None, fl, {'id': tp['id'], 'name': tp['name'], 'by': by, 'why': why[:200], 'at': round(time.time()), **(extra or {})})
    used.add(_cl.sig(base))
    return note


def _apply_many(cat, fs, pairs, by_default):
    used = _used_sigs(cat) - {_cl.sig(_look_now(f)) for f in fs}; notes = []
    for f, (tp, why, by) in zip(fs, pairs):
        n_ = _apply(cat, f, tp, by or by_default, why, used)
        if n_:
            notes.append(f"PoC #{f.get('n')}: {n_}")
    return notes


@router.post('/api/cats/{cat_id}/clipfarm/template/save')
async def tpl_save(cat_id: str, request: Request):
    """💾 Save a look as a named template (new, or an update of one of this agent's): captions, transition, effects, safe area, its formats."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _gate(request, store, cat, body, 'save clip templates')
    name = ' '.join(str(body.get('name') or '').split())[:40]
    if not name:
        raise rs.HTTPException(400, 'Give the template a name.')
    fm = [x for x in body.get('fmts') or FMTS if x in FMTS]
    if not fm:
        raise rs.HTTPException(400, 'Pick at least one format for it.')
    look = _cl.clean_look(body.get('look')); look['edit'] = _cl.clean_look({})['edit']; look.pop('preset', None)   # word edits belong to a clip, not a template
    st = tpl_store(cat); lst = st['list']; tid = str(body.get('id') or '')
    if tid.startswith('b:'):
        raise rs.HTTPException(400, "FEELESS's own templates can't be changed: save it under a new name.")
    if any(_cl.sig(x['look']) == _cl.sig(look) and x['id'] != tid and set(x.get('fmts') or FMTS) == set(fm) for x in all_tpls(cat)):
        twin = next(x for x in all_tpls(cat) if _cl.sig(x['look']) == _cl.sig(look) and x['id'] != tid)
        raise rs.HTTPException(409, f"\"{twin['name']}\" is already this exact look. Change one thing first.")
    row = next((x for x in lst if x['id'] == tid), None)
    if tid and not row:
        raise rs.HTTPException(404, 'No such template.')
    if row:
        row.update(name=name, look=look, fmts=fm, at=round(time.time()), why=str(body.get('why') or row.get('why') or '')[:160])
    else:
        row = {'id': 't' + secrets.token_hex(5), 'name': name, 'look': look, 'fmts': fm, 'by': 'TEST' if who == 'internal' else 'owner', 'at': round(time.time()), 'why': str(body.get('why') or '')[:160]}
        lst.append(row)
    cat['clipTpl'] = {'list': lst[-TPL_KEEP:], 'defaults': st['defaults']}; rs.keep_owned(cat); _keep_looks(cat); rs._save(store)
    return {'templates': tpl_view(cat), 'id': row['id']}


@router.post('/api/cats/{cat_id}/clipfarm/template/delete')
async def tpl_delete(cat_id: str, request: Request):
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); _gate(request, store, cat, body, 'delete clip templates')
    tid = str(body.get('id') or ''); st = tpl_store(cat)
    if tid.startswith('b:') or not any(x['id'] == tid for x in st['list']):
        raise rs.HTTPException(400 if tid.startswith('b:') else 404, "FEELESS's own templates stay." if tid.startswith('b:') else 'No such template.')
    d = {k: ('minds' if k == 'farm' else '') if v == tid else v for k, v in st['defaults'].items()}   # a default that pointed at it falls back
    cat['clipTpl'] = {'list': [x for x in st['list'] if x['id'] != tid], 'defaults': d}; rs.keep_owned(cat); _keep_looks(cat); rs._save(store)
    return {'templates': tpl_view(cat)}


@router.post('/api/cats/{cat_id}/clipfarm/template/default')
async def tpl_default(cat_id: str, request: Request):
    """⭐ A default: the farm's ('minds' or a template: every new run starts in it), a format's (9:16 / 1:1 / 16:9) or a platform's (its file's format)."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); _gate(request, store, cat, body, 'set clip template defaults')
    key, val = str(body.get('key') or ''), str(body.get('tpl') or '')
    if key not in DEF_DEFAULTS:
        raise rs.HTTPException(400, 'No such default.')
    if val and not (val == 'minds' and key == 'farm') and not find_tpl(cat, val):
        raise rs.HTTPException(404, 'No such template.')
    st = tpl_store(cat); st['defaults'][key] = val or ('minds' if key == 'farm' else '')
    cat['clipTpl'] = st; rs.keep_owned(cat); _keep_looks(cat); rs._save(store)
    return {'templates': tpl_view(cat)}


@router.post('/api/cats/{cat_id}/clipfarm/template/apply')
async def tpl_apply(cat_id: str, request: Request):
    """👆 One tap: a template onto one clip, a whole run or the week → new look versions (undo-able), re-rendered in the background ($0)."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _gate(request, store, cat, body, 'edit its clips')
    tp = find_tpl(cat, body.get('tpl'))
    if not tp:
        raise rs.HTTPException(404, 'No such template.')
    fs, gone = _targets(cat, body); by = 'TEST' if who == 'internal' else 'owner'
    notes = _apply_many(cat, fs, [(tp, f"your template: {tp['name']}", by)] * len(fs), by) + gone
    rs.keep_owned(cat); _keep_looks(cat); rs._save(store); _queue(cat_id, {f['id'] for f in fs})
    return {'pocFolders': rs._poc_view(cat), 'changed': [f['id'] for f in fs], 'notes': notes}


@router.post('/api/cats/{cat_id}/clipfarm/template/minds')
async def tpl_minds(cat_id: str, request: Request):
    """🧠 The minds pick a template per clip (one clip, a run or the week), each different, each with a why on its tile; re-rendered ($0)."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _gate(request, store, cat, body, 'edit its clips')
    if who == 'internal':
        _test_caps(cat_id, cat)
    fs, gone = _targets(cat, body)
    items = [{'k': i, 'hook': f['studio'].get('hook'), 'text': f['studio']['clip'].get('text'), 'dur': f['studio']['clip'].get('dur'), 'both': f['studio']['clip'].get('both')} for i, f in enumerate(fs)]
    pairs, cost, own, mind = await _pick_tpls(cat_id, cat, items, str(body.get('ask') or ''))
    store, cat = _cat(cat_id); _charge(cat_id, cat, cost, own); fs = [_find_clip(cat, f['id']) for f in fs]
    notes = _apply_many(cat, fs, [(tp, f"{mind}: {why}" if by == 'minds' else why, by) for tp, why, by in pairs], 'minds') + gone
    for f in fs:
        if cost:
            f['studio']['looks'][-1]['cost'] = round(cost / len(fs), 5)
    rs.keep_owned(cat); _keep_looks(cat); rs._save(store); _queue(cat_id, {f['id'] for f in fs})
    return {'pocFolders': rs._poc_view(cat), 'changed': [f['id'] for f in fs], 'notes': notes, 'cost': round(cost, 5), 'mind': mind}


@router.post('/api/cats/{cat_id}/clipfarm/template/mind')
async def tpl_mind(cat_id: str, request: Request):
    """🧠 The lead mind designs a NEW template (a different look from every saved one) and saves it under its own name, with a why."""
    rs = _rs(); body = await request.json(); store, cat = _cat(cat_id); who = _gate(request, store, cat, body, 'save clip templates')
    if who == 'internal':
        _test_caps(cat_id, cat)
    have = '\n'.join(f"{x['name']}: {_cl.describe(x['look'])}" for x in all_tpls(cat) if not x.get('legacy'))
    sys_ = (CHAT_SYS.split('Posted clips are locked.')[0] + 'Design ONE new caption template, different from every one listed. Modern short-form: no flat slabs, '
            'thin stroke or soft shadow, the accent on the spoken word. Answer ONLY with JSON: {"name":"2-4 words","base":"<one of: '
            + ', '.join(_cl.PRESET_ORDER) + '>","patch":{…},"why":"at most 16 words"}')
    try:
        raw, cost, own, mind = await _ask_lead(cat, sys_, f"TEMPLATES NOW:\n{have}\nOWNER ASKS: {str(body.get('ask') or 'something new for this week')[:200]}", 900)
    except Exception as e:   # noqa: BLE001
        raise rs.HTTPException(502, f'The mind did not answer ({type(e).__name__}). Nothing changed.')
    j = _cf._json(raw) or {}
    store, cat = _cat(cat_id); _charge(cat_id, cat, cost, own)
    look = _cl.merge(_cl.preset(j.get('base') if j.get('base') in _cl.PRESET_ORDER else 'pop'), j.get('patch') if isinstance(j.get('patch'), dict) else {})
    look, note = _cl.unique(look, {_cl.sig(x['look']) for x in all_tpls(cat)}); look.pop('preset', None)
    st = tpl_store(cat); name = ' '.join(str(j.get('name') or '').split())[:40] or 'Minds pick'
    if any(x['name'].lower() == name.lower() for x in all_tpls(cat)):
        name = f"{name} {len(st['list']) + 1}"
    row = {'id': 't' + secrets.token_hex(5), 'name': name, 'look': look, 'fmts': list(FMTS), 'by': 'minds', 'mind': mind.split('/')[-1], 'at': round(time.time()),
           'why': (' '.join(str(j.get('why') or '').split())[:140] + (f' · {note}' if note else '')), 'cost': round(cost, 5)}
    st['list'].append(row); cat['clipTpl'] = {'list': st['list'][-TPL_KEEP:], 'defaults': st['defaults']}; rs.keep_owned(cat); _keep_looks(cat); rs._save(store)
    return {'templates': tpl_view(cat), 'id': row['id'], 'cost': round(cost, 5)}
