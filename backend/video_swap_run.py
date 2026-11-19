"""🎭 PoC VIDEO SWAP, the job (Slice 4, owner 2026-11-18). One press by the owner → the new person (the folder's AI-made character, or a
portrait made from his words) → the swap on FEELESS's own HQ › Core key (MiniMax H3 Max Recast on fal.ai, or Runway Aleph 2 on OpenRouter)
→ the clip's own sound laid back → a before | after side-by-side → filed into the PoC folder with its cost.

Money rules (CLAUDE.md §1): only the owner or a staff agent may press it; it starts only when the price he saw is the price the server quotes;
a per-swap cap and a day cap stand in front of every call; a job the provider took is never sent again (a restart only polls it). Tests fake
every provider call; the first real paid run is the owner's."""
import asyncio
import json
import os
import re
import secrets
import time
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import media_gen as _mg
import video_swap as _vs

router = APIRouter()
_LIVE = set()           # job ids with a task running in this process
POLL_S = 5
GIVE_UP_S = 20 * 60
MAX_AT_ONCE = 2         # per agent
DOTENV = Path(__file__).parent / '.env'


def _rs():
    import feecat_service
    return feecat_service


def _path():
    return _rs().DATA_DIR / 'video_swaps.json'


def _jobs():
    return _vs.jobs_read(_path())


def _job_save(job):
    """Writes one job (read-modify-write of the small book; the last 400 are kept)."""
    book = _jobs(); book[job['id']] = job
    if len(book) > 400:
        book = dict(sorted(book.items(), key=lambda kv: float(kv[1].get('at') or 0))[-400:])
    p = _path(); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.part'); tmp.write_text(json.dumps(book, separators=(',', ':'))); tmp.replace(p)
    return job


def _set(job, **kw):
    job.update(kw); return _job_save(job)


def _key(eid, cat=None, want=None):
    """→ (key, 'house' | 'owner'). FEELESS's own key from HQ › Core first; else (owner 2026-11-18 "both fal and openrouter") the owner's own
    key on his staff agents (cat_keys donor rule), which is his money and so counts on his own day cap. ('', None) when neither is set."""
    k = _vs.env_key(_vs.ENGINES[eid]['env'], os.environ, DOTENV) if want != 'owner' else ''
    if k:
        return k, 'house'
    if cat and _staff(cat) and want != 'house':
        rs = _rs(); own = rs._ck.key_for(cat, _vs.ENGINES[eid]['provider'], data_dir=rs.DATA_DIR)
        if own:
            return own, 'owner'
    return '', None


def _from_words(src, e):
    return f"FEELESS key (HQ › Core, {e['env']})" if src == 'house' else f"Your own {e['who']} key (on your agents)"


def _staff(cat):
    """🔒 The HQ › Core keys are FEELESS's money: only the owner's own staff agents (an HQ admin wallet, or the leader) may spend them."""
    rs = _rs()
    return bool(cat.get('ownerStaff') or cat.get('isLeader') or (rs.owner_wallet(cat) and rs.owner_wallet(cat) in rs.owner_wallets()))


def _day_start():
    return _rs()._sg.day_start()


def _cap(cat):
    try:
        return max(0.5, min(50.0, float(cat.get('swapCapUsd') or _vs.PER_SWAP_CAP_USD)))
    except (TypeError, ValueError):
        return _vs.PER_SWAP_CAP_USD


def _file(cat_id, url):
    """A /api/cats/media/<cat>/<name> link → its file on disk, or None (only this agent's own media folder)."""
    rs = _rs(); name = str(url or '').rsplit('/', 1)[-1]
    f = rs._media_dir() / cat_id / name
    return f if rs._mg.NAME.fullmatch(name) and str(url or '').startswith(f'/api/cats/media/{cat_id}/') and f.is_file() else None


def _mid():
    return 'm' + uuid.uuid4().hex[:12]


def plan(cat, doc, ws):
    """What the swap panel shows: engines (key set or not), the folder's clips with a price per engine, the person, the caps, its jobs."""
    src = {k: _key(k, cat)[1] for k in _vs.ENGINES}; rdy = {k: bool(v) for k, v in src.items()}
    person = _vs.person_of(doc); clips = _vs.clips_of(doc)
    book = _jobs(); spent = _vs.day_spent(book, _day_start())
    rows = [{'id': k, 'label': e['label'], 'who': e['who'], 'why': e['why'], 'ready': rdy[k], 'keyFrom': _from_words(src[k], e) if src[k] else None, 'env': e['env'], 'minS': e['minS'], 'maxS': e['maxS'],
             'res': list(e['res']), 'pick': k == _vs.PICK, 'runnerUp': k == _vs.RUNNER_UP, 'sound': e['sound']} for k, e in _vs.ENGINES.items()]
    for c in clips:
        c['fit'] = {k: _vs.fits(k, c.get('secs')) for k in _vs.ENGINES}
        c['note'] = {k: _vs.heads_up(k, c.get('secs')) for k in _vs.ENGINES}
        c['quote'] = {k: {r or 'std': {'char': _vs.quote(k, c.get('secs'), r, False), 'make': _vs.quote(k, c.get('secs'), r, True)}
                          for r in (_vs.ENGINES[k]['res'] or (None,))} for k in _vs.ENGINES}   # 'char' = the folder's character, 'make' = a portrait first
    mine = sorted((j for j in book.values() if j.get('cat') == cat.get('id') and j.get('ws') == ws), key=lambda j: -float(j.get('at') or 0))[:12]
    return {'engines': rows, 'clips': clips, 'person': person, 'allowed': _staff(cat), 'cap': _cap(cat), 'dayCap': _vs.DAY_CAP_USD, 'daySpent': spent,
            'res': _vs.RES_DEFAULT, 'auto': _vs.auto_engine(rdy), 'jobs': [_vs.public_job(j) for j in mine]}


def start(cat, doc, ws, body):
    """Checks everything a paid press must pass, books the job, and returns it. The task is started by the caller."""
    if not _staff(cat):
        raise HTTPException(403, 'Video swaps run on FEELESS\'s own keys (HQ › Core): only the owner and staff agents can start one.')
    eid = str(body.get('engine') or '')
    try:
        e = _vs.engine(eid)
    except ValueError as er:
        raise HTTPException(400, str(er))
    key, src = _key(eid, cat)
    if not key:
        raise HTTPException(400, f"No {e['who']} key in HQ › Core yet ({e['env']}). Add it under HQ › Core › Provider keys, then press again. Nothing was charged.")
    clip = next((c for c in _vs.clips_of(doc) if c['mid'] == str(body.get('clip') or '')), None)
    if not clip or not _file(cat['id'], clip['url']):
        raise HTTPException(400, 'Add your clip to this folder first (Swap a person › Add your clip).')
    why = _vs.fits(eid, clip.get('secs'))
    if why:
        raise HTTPException(400, why)
    want = str(body.get('person') or 'character')
    person = _vs.person_of(doc) if want == 'character' else None
    words = _vs.clean_words(body.get('words'))
    if want == 'character' and not person:
        raise HTTPException(400, 'This folder has no AI-made character. Describe the new person instead, and one is made first.')
    if not person:
        try:
            _vs.portrait_prompt(words)
        except ValueError as er:
            raise HTTPException(400, str(er))
    res = _vs.clean_res(eid, body.get('res'))
    q = _vs.quote(eid, clip.get('secs'), res, not person)
    try:
        seen = float(body.get('usd'))
    except (TypeError, ValueError):
        seen = -1
    if abs(seen - q['usd']) > 0.011:   # 💵 the price on his screen is the price that runs (signed = quoted, for money that is not a trade)
        raise HTTPException(409, f"The price changed to ${q['usd']:.2f}. Look at it again, then press.")
    if q['usd'] > _cap(cat) + 1e-9:
        raise HTTPException(400, f"This swap is about ${q['usd']:.2f}, over the ${_cap(cat):.2f} cap per swap. Raise the cap under the swap button, or use a shorter clip.")
    book = _jobs(); spent = _vs.day_spent(book, _day_start())
    if src == 'house' and spent + q['usd'] > _vs.DAY_CAP_USD + 1e-9:
        raise HTTPException(429, f"Swaps on FEELESS's keys are at ${spent:.2f} of the ${_vs.DAY_CAP_USD:.2f} day cap. This one (${q['usd']:.2f}) would pass it. Nothing was charged.")
    if src == 'owner':
        rs = _rs()
        try:
            rs._spend_check(cat, q['usd'])   # 💵 his own key: his own day cap across all his agents
        except rs._sg.OverCap as er:
            raise HTTPException(429, str(er))
    if sum(1 for j in book.values() if j.get('cat') == cat['id'] and j.get('step') not in ('filed', 'failed')) >= MAX_AT_ONCE:
        raise HTTPException(429, f'{MAX_AT_ONCE} swaps are already running for this agent. Wait for one to finish.')
    now = time.time()
    job = {'id': 'v' + uuid.uuid4().hex[:12], 'cat': cat['id'], 'ws': ws, 'engine': eid, 'label': e['label'], 'res': res, 'step': 'person' if not person else 'sending',
           'at': round(now), 'quote': q, 'secs': _vs.made_secs(eid, clip.get('secs')), 'note': _vs.clean_words(body.get('note')),
           'before': {'mid': clip['mid'], 'url': clip['url'], 'label': clip['label'], 'secs': clip.get('secs'), 'w': clip.get('w'), 'h': clip.get('h')},
           'person': person or {'words': words, 'source': 'made'}, 'keyFrom': src, 'paid': _from_words(src, e)}
    return _job_save(job)


async def _ffmpeg(args, timeout=300):
    return await _rs()._ffmpeg(args, timeout)


async def _pub_links(cat_id, files):
    """https links the provider can fetch for these local files (2 hours, random names): PUBLIC_SITE_URL when set, else the quick tunnel."""
    rs = _rs(); pub = rs._media_dir() / cat_id / 'pub'; pub.mkdir(parents=True, exist_ok=True)
    for old in pub.iterdir():
        if time.time() - old.stat().st_mtime > rs._fc_desk.PUBREF_S:
            old.unlink(missing_ok=True)
    names = []
    for f in files:
        n = f'{secrets.token_urlsafe(24)}{f.suffix.lower()}'; f.replace(pub / n); names.append(n)
    site = rs._public_site()
    if site:
        return [f'{site}/api/cats/pubref/{cat_id}/{n}' for n in names]
    try:
        tun = await rs._pubt.ensure(rs._media_dir())
    except Exception:   # no link could open: the copies go, nothing was sent
        for n in names:
            (pub / n).unlink(missing_ok=True)
        raise
    return [f'{tun}/{cat_id}/pub/{n}' for n in names]


def _folder_add(cat_id, ws, mid, kind, label, prompt, url, provider, extra=None):
    """A made file into the folder's own board (so it shows where the folder's other media shows)."""
    rs = _rs(); d = rs._ws_load(cat_id, ws)
    if not d:
        return
    d['messages'] = list(d.get('messages') or []) + [{'by': 'Media', 'text': label, 'at': round(time.time()), 'media': {
        'id': mid, 'kind': kind, 'provider': provider, 'model': label, 'label': label, 'prompt': prompt, 'status': 'done', 'url': url, 'kept': True,
        'at': round(time.time()), 'vswap': True, **(extra or {})}}]
    rs._ws_save(cat_id, d)


async def _poll(h, provider, handle, key, job, started, step='running'):
    while True:
        if time.time() - started > GIVE_UP_S:
            raise ValueError(f'It took longer than {GIVE_UP_S // 60} minutes. Nothing more is charged from here.')
        r = await h.get(handle['status'], headers=_mg.auth(provider, key))
        st, why = _mg.state_of(provider, r.json() if r.status_code == 200 else {'status': 'running'})
        if st == 'failed':
            raise ValueError(_mg.plain_why(None, why) if why else 'The provider stopped it.')
        if st == 'done':
            return
        if job.get('step') != step or why != job.get('state'):
            _set(job, step=step, state=why)
        await asyncio.sleep(POLL_S)


async def _download(h, url, out, headers=None):
    got = 0; tmp = out.with_suffix('.part')
    async with h.stream('GET', url, **({'headers': headers} if headers else {})) as f:
        if getattr(f, 'status_code', 200) != 200:
            raise ValueError(f'The finished file did not download ({f.status_code}).')
        with tmp.open('wb') as w:
            async for ch in f.aiter_bytes():
                got += len(ch)
                if got > _mg.MAX_BYTES:
                    tmp.unlink(missing_ok=True); raise ValueError('The finished file is too big to keep.')
                w.write(ch)
    if not got:
        tmp.unlink(missing_ok=True); raise ValueError('The finished file was empty.')
    tmp.replace(out); return got


async def _make_person(h, cat_id, job, key):
    """👤 The new person's portrait on the swap's own account → a file in the folder, kept as the person of this job."""
    rs = _rs(); prov = _vs.ENGINES[job['engine']]['provider']; mid = _mid(); out = rs._media_dir() / cat_id / f'{mid}.jpg'
    out.parent.mkdir(parents=True, exist_ok=True)
    meth, url, heads, body = _vs.portrait_req(prov, key, job['person'].get('words'))
    if job['person'].get('sent'):   # 🔒 a portrait already sent is never sent twice (no resubmits)
        raise ValueError('The new person was being made when the service restarted. It is not sent again: press Swap once more.')
    _set(job, person={**job['person'], 'sent': True})
    r = await h.request(meth, url, headers=heads, json=body, timeout=180)
    j = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    if prov == 'fal':
        try:
            hd = _mg.handle_of('fal', j)
        except ValueError as e:
            raise ValueError('The new person was not made: ' + _mg.plain_why(r.status_code, e))
        await _poll(h, 'fal', hd, key, job, time.time(), 'person')
        r2 = await h.get(hd['result'], headers=_mg.auth('fal', key))
        src = _vs.portrait_url('fal', r2.json() if r2.status_code == 200 else {})
        if not src:
            raise ValueError('The new person was not made: no picture came back.')
        await _download(h, src, out)
    else:
        src = _vs.portrait_url('openrouter', j)
        if not src:
            why = (j.get('error') or {}).get('message') if isinstance(j.get('error'), dict) else 'no picture came back'
            raise ValueError('The new person was not made: ' + _mg.plain_why(r.status_code, why))
        out.write_bytes(__import__('base64').b64decode(src.split(',', 1)[1]))
    url_ = f'/api/cats/media/{cat_id}/{mid}.jpg'
    _folder_add(cat_id, job['ws'], mid, 'image', 'New person (AI-made)', job['person'].get('words') or '', url_, prov, {'model': _vs.PORTRAIT[prov].get('label')})
    _set(job, person={**job['person'], 'mid': mid, 'url': url_}, step='sending')


async def run(cat_id, jid):
    """One swap, start to filed. Every step is written to the job, so the page shows the truth and a restart picks up where it was."""
    rs = _rs()
    if jid in _LIVE:
        return
    _LIVE.add(jid)
    try:
        job = _jobs().get(jid)
        if not job or job.get('step') in ('filed', 'failed'):
            return
        e = _vs.ENGINES[job['engine']]; prov = e['provider']
        key, _src = _key(job['engine'], rs._load()['cats'].get(cat_id), job.get('keyFrom', 'house'))   # the same key it was priced on, also after a restart
        if not key:
            _set(job, step='failed', why=f"The {e['who']} key it was priced on is gone." + ('' if job.get('handle') else ' Nothing was sent.')); return
        d = rs._media_dir() / cat_id; d.mkdir(parents=True, exist_ok=True); tmp = d / 'tmp'; tmp.mkdir(exist_ok=True)
        before = _file(cat_id, job['before']['url'])
        if not before:
            _set(job, step='failed', why='Its clip is gone from the folder. Nothing was sent.'); return
        async with httpx.AsyncClient(timeout=90, follow_redirects=True) as h:
            if job['step'] == 'person':
                await _make_person(h, cat_id, job, key)
            hd = job.get('handle')
            if not hd:
                if job.get('step') == 'submitted':   # 🔒 sent once already and the answer was lost: never sent twice (no resubmits)
                    _set(job, step='failed', taken=True, why=f"It was sent to {e['who']} but its answer was lost in a restart. It is not sent again: check your {e['who']} dashboard."); return
                img = _file(cat_id, (job.get('person') or {}).get('url'))
                if not img:
                    _set(job, step='failed', why='The new person\'s picture is gone. Nothing was sent.'); return
                tag = uuid.uuid4().hex[:8]; rc, ri = tmp / f'{tag}.mp4', tmp / f'{tag}.jpg'
                if (await _ffmpeg(_vs.ref_args(before, rc, job['secs'], 1080 if job.get('res') == '1080P' else 768)))[0] != 0 or not rc.is_file():
                    _set(job, step='failed', why='Your clip could not be prepared. Add it again as an MP4. Nothing was sent.'); return
                if (await _ffmpeg(rs._cs.img_args(img, ri), 60))[0] != 0 or not ri.is_file():
                    rc.unlink(missing_ok=True); _set(job, step='failed', why='The new person\'s picture could not be prepared. Nothing was sent.'); return
                vurl, iurl = await _pub_links(cat_id, [rc, ri])
                w_, h_ = job['before'].get('w'), job['before'].get('h')
                meth, url, heads, body = _vs.swap_req(job['engine'], key, vurl, iurl, job.get('note'), job.get('res'), rs._cs.nearest_aspect(w_, h_))
                _set(job, step='submitted')   # 🔒 written BEFORE the call: a crash between here and the answer is never sent again
                r = await h.request(meth, url, headers=heads, json=body)
                try:
                    hd = _mg.handle_of(prov, r.json() if r.headers.get('content-type', '').startswith('application/json') else {})
                except ValueError as er:
                    _set(job, step='failed', why=_mg.plain_why(r.status_code, er, 'or-aleph-swap' if prov == 'openrouter' else None)); return
                _set(job, step='queued', handle=hd, taken=True)
            await _poll(h, prov, hd, key, job, float(job.get('at') or time.time()))
            if prov == 'openrouter':
                src, auth = hd['result'], _mg.auth('openrouter', key)
            else:
                r = await h.get(hd['result'], headers=_mg.auth(prov, key))
                src, auth = _mg.output_url(prov, 'video', r.json() if r.status_code == 200 else {}), None
            if not src:
                _set(job, step='failed', why='It finished without a file.'); return
            amid = _mid(); after = d / f'{amid}.mp4'
            await _download(h, src, after, auth)
        _set(job, step='sound')
        await rs._with_sound(after, before)   # 🔊 the clip's own sound, same timing (H3 keeps it too; this makes sure it is the original)
        secs_, _f = await rs._clip_len(after); aw, ah = await rs._clip_size(after)
        after_ = {'mid': amid, 'url': f'/api/cats/media/{cat_id}/{amid}.mp4', 'secs': round(secs_, 2) if secs_ else None, 'w': aw, 'h': ah, 'bytes': after.stat().st_size}
        _set(job, step='side', after=after_)
        smid = _mid(); side = d / f'{smid}.mp4'
        hgt = min(1080, max(360, int(ah or 720)))
        side_url = f'/api/cats/media/{cat_id}/{smid}.mp4' if (await _ffmpeg(_vs.side_args(before, after, side, hgt)))[0] == 0 and side.is_file() and side.stat().st_size else None
        if not side_url:
            side.unlink(missing_ok=True)
        _set(job, side=side_url)
        _folder_add(cat_id, job['ws'], amid, 'video', f"{e['label']} swap", f"The new person in {job['before'].get('label') or 'your clip'}", after_['url'], prov,
                    {'secs': after_['secs'], 'w': aw, 'h': ah, 'fromClip': {'mid': job['before']['mid'], 'url': job['before']['url']}})
        if side_url:
            _folder_add(cat_id, job['ws'], smid, 'video', 'Before | after', 'Side by side', side_url, 'ffmpeg')
        _file_it(cat_id, job)
    except Exception as er:   # noqa: BLE001: any failure stops the job with its reason, so it never sits half-way and gets retried on every poll
        j = _jobs().get(jid) or {}
        if j and j.get('step') not in ('filed', 'failed'):
            _set(j, step='failed', why=str(er)[:300] if isinstance(er, ValueError) else f'{type(er).__name__}: {str(er)[:160]}')
    finally:
        _LIVE.discard(jid); _settle(cat_id, jid)


def _settle(cat_id, jid):
    """💵 A finished job leaves the owner's day cap hold; one his own key paid for that the provider took and then failed is still a bill
    (list price: it may have been charged), so his cap never under-counts. FEELESS-key jobs count on the swap day cap instead (day_spent)."""
    rs = _rs(); j = _jobs().get(jid) or {}
    if j.get('step') not in ('filed', 'failed'):
        return
    rs._spend_release(jid)
    if j.get('step') == 'failed' and j.get('taken') and j.get('keyFrom') == 'owner' and not j.get('billed'):
        e = _vs.ENGINES[j['engine']]
        rs._receipt_write({'id': jid, 'cat': cat_id, 'at': time.time(), 'provider': e['who'], 'model': e['endpoint'], 'usd': float((j.get('quote') or {}).get('usd') or 0),
                           'tokens': None, 'status': 'failed after the provider took it (list price, may be charged)', 'funding': 'owner key'})
        _set(j, billed=True)


def _file_it(cat_id, job):
    """🧾 Into the PoC folder: the record (before / after / side by side / cost / engine), its receipt on FEELESS's key, a bell."""
    rs = _rs(); now = time.time(); store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        _set(job, step='failed', why='The agent is gone.'); return
    q = job.get('quote') or {}
    rs._receipt_write({'id': job['id'], 'cat': cat_id, 'at': now, 'provider': _vs.ENGINES[job['engine']]['who'], 'model': _vs.ENGINES[job['engine']]['endpoint'],
                       'usd': float(q.get('usd') or 0), 'tokens': None, 'status': 'list price', 'funding': rs._sg.HOUSE if job.get('keyFrom', 'house') == 'house' else 'owner key'})
    _set(job, billed=True)   # 🧾 the bill is written first: a filing that breaks below never loses it
    rows = list(cat.get('pocFolders') or [])
    try:
        row = rs._record_file(cat, 'poc', _vs.record(job, rs._next_n(rows), now))
        rows.append(row); cat['pocFolders'] = rows[-60:]; rs.keep_owned(cat); rs._save(store)
    except Exception as er:   # noqa: BLE001
        _set(job, step='failed', why=f'Made and kept on the folder board, but it could not be filed as a PoC ({type(er).__name__}). Its cost is recorded.'); return
    rs._feed_push(cat_id, {'tone': 'done', 'kind': 'PoC', 'text': f"Video swap filed: PoC #{row.get('n')} ({_vs.ENGINES[job['engine']]['label']}, ${float(q.get('usd') or 0):.2f})", 'ref': job.get('ws')})
    _set(job, step='filed', poc=row['id'], doneAt=round(now))


def resume(cat_id):
    """A job left mid-way by a restart picks up again (it polls a job the provider took; it never sends one twice)."""
    for j in _jobs().values():
        if j.get('cat') == cat_id and j.get('step') not in ('filed', 'failed') and j['id'] not in _LIVE:
            _spawn(run(cat_id, j['id']))


_TASKS = set()


def _spawn(coro):
    """A background job kept referenced until it ends (the loop holds tasks only weakly)."""
    t = asyncio.create_task(coro); _TASKS.add(t); t.add_done_callback(_TASKS.discard)
    return t


class SwapIn(BaseModel):
    ownerId: str = ''
    session: str = ''
    ws: str = ''
    clip: str = ''
    engine: str = ''
    res: str = ''
    person: str = 'character'
    words: str = ''
    note: str = ''
    usd: float = -1


def _gate(cat_id, owner_id, session, ws):
    rs = _rs(); store = rs._load(); cat = (store.get('cats') or {}).get(cat_id)
    if not cat:
        raise HTTPException(404, 'Agent not found.')
    rs._owner_gate(store, cat, session, owner_id, 'swap a video')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', str(ws or '')):
        raise HTTPException(400, 'Open a PoC folder first.')
    doc = rs._ws_load(cat_id, ws)
    if not doc or doc.get('kind') != 'content':
        raise HTTPException(400, 'Video swaps live in a PoC folder.')
    return cat, doc


@router.get('/api/cats/{cat_id}/vswap')
async def vswap_plan(cat_id: str, ws: str = '', ownerId: str = '', session: str = ''):
    """🎭 The swap panel: engines + HQ › Core keys (set or not, never a value), clips with prices, the person, caps, this folder's swaps."""
    cat, doc = _gate(cat_id, ownerId, session, ws)
    resume(cat_id)
    return plan(cat, doc, ws)


@router.post('/api/cats/{cat_id}/vswap')
async def vswap_start(cat_id: str, p: SwapIn):
    """🎭 The owner's press: checked (staff, key, clip, person, the price he saw, caps), booked, then run in the background."""
    cat, doc = _gate(cat_id, p.ownerId, p.session, p.ws)
    job = start(cat, doc, p.ws, p.model_dump())
    if job.get('keyFrom') == 'owner':
        _rs()._spend_hold(cat, job['id'], (job.get('quote') or {}).get('usd'))
    _spawn(run(cat_id, job['id']))
    return {'job': _vs.public_job(job), **plan(cat, _rs()._ws_load(cat_id, p.ws) or doc, p.ws)}
