"""🎬 Slice 5 (owner 2026-11-18): the PoC content studio, wired. `poc_file` replaces the old pitch-only PoC filer (its calls, snapshots, sites
read and footprint gate all stay, so nothing that worked is lost): trend first → both minds write blind for the trend they pick → the free
local maker makes every piece in every format → the folder files with its goal and true record. Then:

  · poc_accounts  the accounts the owner signed into a posting service (Upload-Post / Zernio / Ayrshare), read with his sealed key
  · poc_goal      the owner changes the goal before approving (locked once posted)
  · poc_approve   the OWNER's click only (the internal key is refused): posts the pieces he picked on the platforms he picked
  · poc_reach     reads views + engagement now (the loop below reads by itself at 24 h and 7 d after it posted) and grades it

Same pattern as the other fc_ modules: every service name is looked up on feecat_service when it runs (as rs.<name>)."""
import os
import re
import secrets
from urllib.parse import urlparse

from fastapi import APIRouter

import collective_kits as _kits

import poc_post as _pp
import poc_studio as _ps

router = APIRouter()
OPS = ('poc_accounts', 'poc_goal', 'poc_approve', 'poc_reach')
REACH_EVERY_S = 600
READ_TRIES = 36          # a 24 h / 7 d read that keeps failing is retried every sweep for ~6 h before it is kept as failed
TEXT_NAME = re.compile(r'^t[0-9a-f]{12}\.txt$')
THUMB_MAX = 5 * 1024 * 1024
_POSTING = set()


def _rs():
    import feecat_service
    return feecat_service


def _saver(cat_id):
    """save(piece, ext, bytes) → the url the folder keeps. Pictures and clips live with every other PoC media file (random names: the link is the
    permission); the post and thread texts beside them, served by the route below."""
    rs = _rs(); d = rs._media_dir() / cat_id; d.mkdir(parents=True, exist_ok=True)

    def save(piece, ext, raw):
        if ext == 'txt':
            name = f't{secrets.token_hex(6)}.txt'; (d / name).write_bytes(raw)
            return f'/api/cats/poc/{cat_id}/{name}'
        name = f'm{secrets.token_hex(6)}.{ext}'; (d / name).write_bytes(raw)
        return f'/api/cats/media/{cat_id}/{name}'
    return save


def _file_bytes(cat_id, row):
    rs = _rs(); name = str((row or {}).get('url') or '').rsplit('/', 1)[-1]
    if not (rs._mg.NAME.fullmatch(name) or TEXT_NAME.fullmatch(name)):
        raise ValueError('That file is not one of this PoC’s.')
    return (rs._media_dir() / cat_id / name).read_bytes()


async def _thumb(http, url):
    """The trend's own picture (a public https thumbnail) for the files' background, or None. Third-party bytes: only ever drawn under our words."""
    try:
        if not url or not _kits._public_https(url) or not _kits._public_host(urlparse(url).hostname or ''):
            return None
        async with http.stream('GET', url, timeout=10, follow_redirects=False) as r:   # streamed: a huge body is cut off at THUMB_MAX, never buffered
            if r.status_code != 200 or not r.headers.get('content-type', '').startswith('image/'):
                return None
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                buf += chunk
                if len(buf) >= THUMB_MAX:
                    return None
            return bytes(buf)
    except Exception:   # noqa: BLE001
        return None


async def poc_file(cat_id, topic, ws=None, wiz=None):
    """📣 PROOF OF CONTENT, the studio: trend first, real files, a goal, nothing posted. Its PoI is the trend list it chose from."""
    rs = _rs()
    try:
        async with rs.httpx.AsyncClient(timeout=10, follow_redirects=True) as http:
            got_ = await rs._tools.trending(http)
            cat = rs._load()['cats'].get(cat_id) or {}; brains = rs._lc.minds_for(cat.get('brainsCfg'), 'poc') or []
            if not brains:
                return
            pid_ = f'poc{int(rs.time.time())}'; rs._CALL_CTX.set({'kind': 'poc', 'ref': ws or pid_, 'minds': brains})
            ridden = [((f.get('studio') or {}).get('trend') or {}).get('text') for f in cat.get('pocFolders') or [] if isinstance(f, dict)]
            trends = _ps.trend_rows(got_, ridden)
            if not trends:
                raise RuntimeError('no trend source answered')
            notes = '; '.join(str(c.get('text') or '')[:120] for c in ((cat.get('brainsCfg') or {}).get('cloud') or [])[-6:])
            read_, sites_read_ = await rs._site_reads('poc', (cat['id'], cat.get('name')))
            wiz_line_, wiz_rec_ = '', None
            if wiz:   # 🧭 Slice 33: the start wizard's kits (via _recall), research pass and the owner's direction reach both minds
                rs._wiz.CTX.set(wiz)
                found_ = await rs._wiz.research(wiz, topic or (wiz.get('direction') or {}).get('text') or '', http, rs._tools.build_refs, rs._fc_desk.wiz_ask(cat, 'poc', ws or pid_))
                base_ = rs._wiz.start_row(cat.get('pocFolders'), wiz.get('start')); wiz_line_ = rs._wiz.line(wiz, found_, base_); wiz_rec_ = rs._wiz.record(wiz, found_, base_)
            sys_ = (_ps.SYS + rs._foot.note('poc', cat.get('pocFolders'), 0) + rs._feat._sources.proof_line('poc') + read_ + rs._recall(cat, 'Content', topic)
                    + rs._know.for_ask(topic) + rs._prec.back_line(cat.get('footBack'), 'poc', rs.time.time()) + wiz_line_)
            user_ = _ps.ask_text(trends, topic, notes); cost = 0.0; paid_own = False

            async def one(i, m):
                """One mind, blind. A reply that cannot be read gets ONE stricter retry (local minds often think out loud or run out of room)."""
                usd_all, own_any, raw = 0.0, False, ''
                for n_ in range(2):
                    try:
                        raw, usd, own = await rs.asyncio.wait_for(rs._ws_ask(cat, m, sys_ + f'\nYou are Mind {"AB"[i % 2]}.' + ('\n' + _ps.RETRY if n_ else ''), user_, 2400), 420)
                    except Exception as e:   # noqa: BLE001: one mind down never stops the other
                        return i, raw, usd_all, own_any, f'{type(e).__name__}'
                    usd_all += usd or 0; own_any = own_any or own
                    if _ps.parse(raw, trends):
                        break
                    print(f"[poc] {cat_id} mind {i} reply not readable (try {n_ + 1}): {' '.join(str(raw or '').split())[:300]}")
                return i, raw, usd_all, own_any
            asked = await rs.asyncio.gather(*(one(i, m) for i, m in enumerate(brains[:2])))
            pitches, calls = [], []
            for i, raw, usd, own, *err in asked:
                cost += usd or 0; paid_own = paid_own or own; p_ = _ps.parse(raw, trends); pitches.append(p_)
                calls.append({'mind': i, 'name': str(brains[i]).split('/')[-1][:24], 'angle': (p_ or {}).get('angle', ''), 'post': ((p_ or {}).get('post') or {}).get('feed', '') or str(raw or '')[:240],
                              'why': (p_ or {}).get('why', '') or (err[0] if err else ''), 'trend': ((p_ or {}).get('trend') or {}).get('text', ''), 'gaps': (p_ or {}).get('gaps', ['no JSON came back'] if raw else ['no answer'])})
            k_, best = _ps.pick(pitches)
            if best is None:
                raise RuntimeError('no mind picked a trend and wrote a headline')
            best = _ps.fill(best); tr_ = best['trend']; goal_ = _ps.goal(best, tr_)
            bg_ = await _thumb(http, tr_.get('thumb'))
        files_ = await rs.asyncio.to_thread(_ps.make_files, best, tr_, _saver(cat_id), 'ffmpeg', bg_)
        shots_ = await _shots(cat, pid_, [t['text'] for t in trends[:6]] + [topic or ''])
        store = rs._load(); c_ = store['cats'].get(cat_id)
        if not c_:
            return
        rows = list(c_.get('pocFolders') or [])
        studio_ = {'trend': {k: tr_.get(k) for k in ('n', 'text', 'source', 'url', 'signal', 'unit', 'by', 'kind')}, 'trends': [{k: t.get(k) for k in ('n', 'text', 'source', 'url', 'signal', 'unit')} for t in trends],
                   'mind': k_, 'angle': best['angle'], 'hook': best['hook'], 'sub': best['sub'], 'beats': best['beats'], 'post': best['post'], 'thread': best['thread'],
                   'goal': goal_, 'files': files_, 'filled': best.get('filled') or [], 'gaps': best.get('gaps') or [], 'maker': {'name': 'FEELESS free maker (Pillow + ffmpeg, on this machine)', 'usd': 0.0, 'watermark': False},
                   'why': best.get('why') or '', 'bg': 'the trend’s own picture' if bg_ else 'FEELESS green field'}
        f_ = {'id': pid_, **({'wizard': wiz_rec_} if wiz_rec_ else {}), 'kits': rs._KIT_LAST.get((cat_id, 'poc')) or [], **({'ws': ws} if ws else {}), 'shots': shots_, 'sitesRead': sites_read_, 'n': rs._next_n(rows), 'kind': 'PoC',
              'at': round(rs.time.time()), 'status': 'closed', 'paper': True, 'topic': (f"{_ps._cut(tr_['text'], 60)}" + (f' · {topic}' if topic else ''))[:120],
              'trends': {k: v[:5] for k, v in ((got_ or {}).get('trends') or {}).items()}, 'calls': calls, 'cost': round(cost, 5), 'studio': studio_,
              'sources': {'trends': [{'url': t['url']} for t in trends if str(t.get('url') or '').startswith('http')]},
              **({'testRun': True} if (cat_id, 'poc') in rs._TEST_ON else {})}   # a TEST is marked here too, so the approve guard never rests on the stamp alone
        if rs._foot_back(c_, 'poc', f_):   # 👣 Slice 0: mostly what a past PoC read and said → back once, from other pages, before it files
            if cost and not paid_own and c_.get('brainsCfg'):
                rs._lc.charge(c_['brainsCfg'], cost)
            rs._save(store)
            return await rs._poc_file(cat_id, topic, ws, wiz)
        rows.append(rs._record_file(c_, 'poc', f_))
        c_['pocFolders'] = rows[-60:]
        ok_, why_ = _ps.files_check(files_)
        c_['chat'] = (list(c_.get('chat') or []) + [{'by': 'cats', 'text': f"📣 PoC #{f_['n']} is made from today's trend \"{_ps._cut(tr_['text'], 60)}\" ({tr_['source']}): {why_}. Goal: {goal_['target']:,} {_ps.GOAL_WORD[goal_['type']]} in 7 days. Approve it to post. Nothing was posted.", 'at': rs.time.time(), 'open': 'features'}])[-200:]
        if cost and not paid_own and c_.get('brainsCfg'):
            rs._lc.charge(c_['brainsCfg'], cost)
        rs._save(store)
    except Exception as e:   # noqa: BLE001
        print(f'[poc] {cat_id}: {type(e).__name__}: {str(e)[:140]}')
        try:
            store = rs._load(); c_ = store['cats'].get(cat_id)
            if c_:
                c_['chat'] = (list(c_.get('chat') or []) + [{'by': 'cats', 'text': f'📣 The PoC could not be made: {str(e)[:120]}. Nothing was filed or posted.', 'at': rs.time.time(), 'open': 'features'}])[-200:]
                rs._save(store)
        except Exception:   # noqa: BLE001
            pass
        rs._TEST_ON.pop((cat_id, 'poc'), None)   # a TEST that failed never marks the next real PoC
    finally:
        rs._POC_BUSY.discard(cat_id)


async def _shots(cat, pid_, words):
    """🖍 The free snapshots a PoC keeps of what it read (Slice 0: the pages used least lately first)."""
    rs = _rs(); out = []
    try:
        at_ = rs._prec.fresh_sites(cat.get('footBack'), 'poc', rs.time.time(), rs._foot.order_sites('poc', list(rs._fc_tools.POC_SHOTS), cat.get('pocFolders')), keep=3)[:3]
        for n_, r_ in enumerate(await rs._fb.shots(at_, rs._marks.words_of(words), rs.time.time())):
            d_ = rs.POWSHOTS_DIR / re.sub(r'[^a-z0-9]', '', pid_); d_.mkdir(parents=True, exist_ok=True); name_ = f"{re.sub(r'[^a-z0-9]', '', r_['site'])[:30]}_{n_}.jpg"; (d_ / name_).write_bytes(r_['jpg'])
            out.append({'site': r_['site'], 'url': r_['url'], 'title': r_['title'], 'file': name_, 'at': round(rs.time.time()), 'found': list(r_['found'])[:12], 'missing': r_['missing'][:12], 'sha': r_['sha']})
    except Exception as e:   # noqa: BLE001: a snapshot that fails never stops the PoC
        print(f'[poc] snapshot not kept: {str(e)[:120]}')
    return out


def _restamp(cat, f):
    """The record's checks again after an approve or a read (they say what is true NOW)."""
    rs = _rs()
    try:
        f['proofChecks'] = rs._prec.checks('poc', f, rs._lc.minds_for(cat.get('brainsCfg'), 'poc'))
    except Exception as e:   # noqa: BLE001
        print(f'[poc] record: {str(e)[:120]}')


async def _read_reach(cat_id, fid, keys=None, force=False):
    """Reads each posted platform's numbers through the service it posted with, grades them, keeps the read. → the folder or None"""
    rs = _rs(); store = rs._load(); cat = store['cats'].get(cat_id) or {}
    f = next((x for x in cat.get('pocFolders') or [] if x.get('id') == fid), None)
    po = (f or {}).get('posted') or {}
    if not f or po.get('svc') not in _pp.SERVICES or not isinstance(po.get('platforms'), dict):
        return None
    saved = rs._ck.key_for(cat, po['svc'], data_dir=rs.DATA_DIR)
    now = rs.time.time(); due = keys if keys is not None else _ps.due(f, now)
    if not due and not force:
        return f
    if not saved:
        raw = {'_errors': {pl: f"the {_pp.SERVICES[po['svc']]['name']} key was removed from this agent" for pl in po.get('platforms') or {}}}
    else:
        async with rs.httpx.AsyncClient(timeout=30, follow_redirects=False) as h_:
            raw = await _pp.reach(h_, po['svc'], saved, po.get('platforms'))
    errs = raw.pop('_errors', {}); per = {pl: _ps.metrics(v) for pl, v in raw.items()}; t = _ps.total(per)
    store = rs._load(); cat = store['cats'].get(cat_id) or {}; f = next((x for x in cat.get('pocFolders') or [] if x.get('id') == fid), None)
    if not f:
        return None
    r_ = f.setdefault('reach', {'reads': []}); g = (f.get('studio') or {}).get('goal') or {}; cost = float(f.get('cost') or 0) + float(((f.get('studio') or {}).get('maker') or {}).get('usd') or 0)
    blank = errs and not any(v.get('views') is not None or v.get('engagement') for v in per.values())
    if blank and due:   # the service was down / the key gone: try again next sweep; after READ_TRIES misses the read is kept as failed
        miss = r_.setdefault('misses', {})
        for k in due:
            miss[k] = int(miss.get(k) or 0) + 1
        keep = [k for k in due if miss[k] >= READ_TRIES]
        r_['last'] = {'key': due[0], 'label': 'not read', 'at': round(now), 'platforms': per, 'errors': errs, **t, 'grade': _ps.grade(g, t, cost, False), 'tries': miss[due[0]]}
        if not keep:
            _restamp(cat, f); rs.keep_owned(cat); rs._save(store)
            return f
        due = keep
    for k in (due or ['now']):
        label = dict((a, c) for a, _b, c in _ps.CHECKS).get(k, 'now')
        row = {'key': k, 'label': label, 'at': round(now), 'platforms': per, 'errors': errs, **t, 'grade': _ps.grade(g, t, cost, k == 'd7')}
        if k != 'now':
            r_['reads'] = [x for x in r_.get('reads') or [] if x.get('key') != k] + [row]
        r_['last'] = row
    final = next((x for x in r_.get('reads') or [] if x.get('key') == 'd7'), None)
    if final:
        f['grade'] = final['grade']
        if final['grade']['verdict'] in ('hit', 'missed') and not f.get('graded'):
            f['graded'] = 'right' if final['grade']['verdict'] == 'hit' else 'wrong'; f['gradedBy'] = 'reach at 7 d'
    _restamp(cat, f); rs.keep_owned(cat); rs._save(store)
    return f


async def reach_loop():
    """⏱ Every 10 minutes: any posted PoC whose 24 h or 7 d read is due is read and graded. A quiet one costs nothing (no model is asked)."""
    rs = _rs()
    while True:
        try:
            now = rs.time.time(); cats = list((rs._load().get('cats') or {}).items())
        except Exception as e:   # noqa: BLE001
            print(f'[poc reach] {str(e)[:140]}'); cats = []
        for cid, cat in cats:
            for f in cat.get('pocFolders') or []:
                try:   # per folder: one bad folder never starves the rest
                    if isinstance(f, dict) and _ps.due(f, now):
                        await _read_reach(cid, f['id'])
                except Exception as e:   # noqa: BLE001
                    print(f'[poc reach] {cid[:8]} {str((f or {}).get("id"))[:20]}: {str(e)[:140]}')
        await rs.asyncio.sleep(REACH_EVERY_S)


@router.on_event('startup')
async def _start_reach():
    rs = _rs()
    if not os.environ.get('PYTEST_CURRENT_TEST') and not os.environ.get('FEELESS_NO_LOOPS'):
        rs.asyncio.create_task(reach_loop())


def _folder(cat, job):
    f = next((x for x in cat.get('pocFolders') or [] if x.get('id') == str(job or '')), None)
    if not f or not isinstance(f.get('studio'), dict):
        raise _rs().HTTPException(404, 'No such PoC from the content studio.')
    return f


async def op(cat_id, cat, store, p, internal_):
    """The studio's ops on a filed PoC (the owner's own page; the approve refuses the internal key)."""
    rs = _rs(); t_ = p.tools if isinstance(p.tools, dict) else {}
    svc = str(t_.get('svc') or '')
    if p.op == 'poc_accounts':
        if svc not in _pp.SERVICES:
            return {'services': [{'id': k, 'name': v['name'], 'site': v['site'], 'keys': v['keys'], 'how': v['how'], 'platforms': list(v['platforms']), 'thread': v['thread'],
                                  'saved': bool(rs._ck.key_for(cat, k, data_dir=rs.DATA_DIR))} for k, v in _pp.SERVICES.items()]}
        saved = rs._ck.key_for(cat, svc, data_dir=rs.DATA_DIR)
        if not saved:
            raise rs.HTTPException(400, f"Save your {_pp.SERVICES[svc]['name']} key on this agent first (Vault › API keys). It holds your logins; FEELESS never sees them.")
        try:
            async with rs.httpx.AsyncClient(timeout=20, follow_redirects=False) as h_:
                return {'svc': svc, 'accounts': await _pp.accounts(h_, svc, saved)}
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        except rs.httpx.HTTPError:
            raise rs.HTTPException(502, f"{_pp.SERVICES[svc]['name']} did not answer.")
    f = _folder(cat, p.job)
    if p.op == 'poc_goal':
        if internal_ or p.auto:
            raise rs.HTTPException(403, 'Only its owner edits the goal.')
        if (f.get('posted') or {}).get('at'):
            raise rs.HTTPException(409, 'The goal is locked: it was set before this PoC posted.')
        typ = str(t_.get('type') or '').lower(); n = _ps._int(t_.get('target'))
        if typ not in _ps.GOALS or not 10 <= n <= 10_000_000:
            raise rs.HTTPException(400, 'Pick reach, followers, clicks or buzz, and a number from 10 to 10,000,000.')
        g = f['studio']['goal']; f['studio']['goal'] = {**g, 'type': typ, 'target': n, 'by': 'owner', 'was': g.get('was') or {'type': g.get('type'), 'target': g.get('target'), 'by': g.get('by')}}
        _restamp(cat, f); rs.keep_owned(cat); rs._save(store)
        return {'pocFolders': rs._poc_view(cat)}
    if p.op == 'poc_reach':
        if not (f.get('posted') or {}).get('at'):
            raise rs.HTTPException(400, 'It has not posted yet: approve it first.')
        await _read_reach(cat_id, f['id'], keys=[], force=True)
        return {'pocFolders': rs._poc_view(rs._load()['cats'].get(cat_id) or cat)}
    # ✅ poc_approve: the owner's click is the ONLY way a PoC posts
    if internal_ or p.auto:
        raise rs.HTTPException(403, 'Only its owner approves a post. Nothing posts by itself.')
    if ((f.get('test') or {}).get('by') or f.get('testRun')) and t_.get('realPost') is not True:
        raise rs.HTTPException(409, 'This is a TEST PoC. Approve it on purpose (tick “post this test for real”) if you want it public.')
    if (f.get('posted') or {}).get('at') and t_.get('again') is not True:
        raise rs.HTTPException(409, 'This PoC already posted. Post it again on purpose if you mean to.')
    if svc not in _pp.SERVICES:
        raise rs.HTTPException(400, 'Pick the posting service your accounts are signed into.')
    saved = rs._ck.key_for(cat, svc, data_dir=rs.DATA_DIR)
    if not saved:
        raise rs.HTTPException(400, f"Save your {_pp.SERVICES[svc]['name']} key on this agent first (Vault › API keys).")
    choice = {k: v for k, v in (t_.get('platforms') or {}).items() if isinstance(k, str)}
    if not choice:
        raise rs.HTTPException(400, 'Pick at least one platform.')
    go, skip = _pp.plan(choice, f['studio'].get('files'), f['studio'], svc)
    if not go:
        raise rs.HTTPException(400, 'Nothing can go out: ' + '; '.join(f"{_pp.PLAT.get(s['platform'], s['platform'])} ({s['why']})" for s in skip[:4]) + '.')
    if cat_id in _POSTING:
        raise rs.HTTPException(409, 'A PoC is already posting.')
    _POSTING.add(cat_id)
    try:
        async with rs.httpx.AsyncClient(timeout=90, follow_redirects=False) as h_:
            accts = await _pp.accounts(h_, svc, saved) if svc == 'zernio' else None
            res = await _pp.publish(h_, svc, saved, go, lambda row: _file_bytes(cat_id, row), accts)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    finally:
        _POSTING.discard(cat_id)
    store = rs._load(); cat = store['cats'].get(cat_id) or cat; f = _folder(cat, p.job); now = round(rs.time.time())
    f['posted'] = {'at': now, 'svc': svc, 'approvedBy': 'owner', 'approvedAt': now, 'platforms': res, 'skipped': skip,
                   'sent': sum(1 for r in res.values() if r.get('ok'))}
    f['studio']['goal'] = {**f['studio']['goal'], 'locked': True, 'lockedAt': now}
    f.pop('reach', None)
    _restamp(cat, f)
    bad = [f"{_pp.PLAT[k]} ({str(v.get('error') or '')[:60]})" for k, v in res.items() if not v.get('ok')]
    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"📮 PoC #{f.get('n')} posted on {f['posted']['sent']} of {len(res)} through {_pp.SERVICES[svc]['name']}, after your approve" + (f"; not posted: {', '.join(bad)}" if bad else '') + '. Reach is read at 24 h and 7 d.', 'at': rs.time.time(), 'open': 'features'}])[-200:]
    rs.keep_owned(cat); rs._save(store)
    return {'pocFolders': rs._poc_view(cat), 'posted': f['posted']}


@router.get('/api/cats/poc/{cat_id}/{name}')
async def poc_text_file(cat_id: str, name: str):
    """A PoC's post or thread text as a file. Its name is random, so the link is the permission (the same rule as its pictures)."""
    rs = _rs()
    from starlette.responses import FileResponse
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', cat_id) or not TEXT_NAME.fullmatch(name):
        raise rs.HTTPException(404, 'No such file.')
    f_ = rs._media_dir() / cat_id / name
    if not f_.is_file():
        raise rs.HTTPException(404, 'No such file.')
    return FileResponse(f_, media_type='text/plain; charset=utf-8', headers={'Cache-Control': 'public, max-age=86400', 'X-Content-Type-Options': 'nosniff'})
