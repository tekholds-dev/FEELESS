"""🧹 Desk feed, tools, proof routes — moved whole out of feecat_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches feecat_service still
reaches it, and every function here is still reachable on feecat_service under its own name. Constants, classes and state live in the service."""
import feecat_service as _RSM  # noqa: E402,F401  (body models; this module is imported at the END of the service)
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401

router = APIRouter()


def _rs():
    import feecat_service
    return feecat_service


def _feed_detail(v):
    """🔔 a proof event's detail in words: an old writer stored a Python dict as text ("{'won': False}/100") and the bell showed it raw."""
    t = str(v or '').strip()
    if not t.startswith('{'):
        return t[:120]
    import ast
    try:
        d = ast.literal_eval(t.split('}')[0] + '}')
    except (ValueError, SyntaxError):
        return ''
    if isinstance(d, dict):
        if 'won' in d:
            return 'won' if d['won'] else 'lost'
        n = d.get('score', d.get('grade'))
        if isinstance(n, (int, float)):
            return f'{n:g}/100'
    return ''


async def _or_credit(cat):
    """The REAL $ its own OpenRouter key can still spend: the account's credits − usage, capped by the key's own limit. None = no key / no read."""
    rs = _rs()
    key_ = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
    if not key_:
        return None
    hit = rs._OR_CREDIT.get(cat.get('id'))
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1]
    row = None
    try:
        async with rs.httpx.AsyncClient(timeout=6) as h_:
            c_, k_ = await rs.asyncio.gather(h_.get('https://openrouter.ai/api/v1/credits', headers={'Authorization': f'Bearer {key_}'}),
                                          h_.get('https://openrouter.ai/api/v1/key', headers={'Authorization': f'Bearer {key_}'}))
        if c_.status_code == 200:
            d_ = c_.json().get('data') or {}; left = float(d_.get('total_credits') or 0) - float(d_.get('total_usage') or 0)
            kd = (k_.json().get('data') or {}) if k_.status_code == 200 else {}
            cap = kd.get('limit_remaining')
            row = {'left': round(min(left, float(cap)) if cap is not None else left, 4), 'account': round(left, 4), 'keyLimit': kd.get('limit'),
                   'keyUsed': round(float(kd.get('usage') or 0), 4), 'at': round(rs.time.time())}
    except (rs.httpx.HTTPError, ValueError):
        row = None
    rs._OR_CREDIT[cat.get('id')] = (rs.time.time(), row)
    return row


@router.get('/api/cats/brief/proofs')
async def proofs_brief(session: str = ''):
    """🫂 Everyone sees the judges as The Collective; a staff session (the owner reviewing OSSY + G4) also gets each judge."""
    rs = _rs()
    b = await rs._proofs_brief()
    w_ = rs._fresh_session_wallet(session) if session else None
    staff_ = bool(w_) and await rs._is_creator(w_)
    return {**b, 'judges': b.get('judges') or []} if staff_ else {**b, 'judges': rs._review.collective_only(b.get('judges'))}


async def _proofs_brief():
    """📰 Today's proofs brief for every desk: per proof type from the proof record (filed, reviewed, graded) + which kits moved in 24 h.
    Rebuilt at most every 10 minutes. Public: counts and scores only."""
    rs = _rs()
    if rs._BRIEF.get('at', 0) > rs.time.time() - 600:
        return rs._BRIEF['v']
    b = await rs.asyncio.to_thread(rs._pev.brief, rs.DATA_DIR / rs._pev.DB_NAME)
    try:   # 🎯 how often each judge agrees with the real result, against a judge that fails everything
        b['judges'] = rs._review.scorecard(await rs.asyncio.to_thread(rs._pev.rows, rs.DATA_DIR / rs._pev.DB_NAME))
    except Exception as e:   # noqa: BLE001
        print(f'[brief] judges: {str(e)[:80]}'); b['judges'] = []
    try:
        kf = rs._kfresh.view(rs._kits.KIT_USE, rs.KITS_DIR)
        moved = [k for k in kf.get('kits') or [] if k.get('movedAt') and float(k['movedAt']) > rs.time.time() - 86400]
        b['kits'] = {'checkedAt': kf.get('checkedAt'), 'moved24': [{'kit': k['kit'], 'pkg': k['pkg'], 'v': k.get('v'), 'prev': k.get('prev')} for k in moved][:8], 'tracked': len(kf.get('kits') or [])}
    except Exception:
        b['kits'] = {'checkedAt': None, 'moved24': [], 'tracked': 0}
    rs._BRIEF.update(at=rs.time.time(), v=b)
    return b


def _scores_http():
    rs = _rs()
    if not rs._SCORES_HTTP:
        rs._SCORES_HTTP.append(rs.httpx.AsyncClient(headers={'User-Agent': 'Mozilla/5.0 (FEELESS watch room)'}))
    return rs._SCORES_HTTP[0]


@router.get('/api/cats/scores/{league}')
async def scores_board(league: str):
    """📺 The watch room's live games for one league (ESPN's free public scoreboard, 15 s cache). Public: scores only."""
    rs = _rs()
    try:
        rows = await rs._scores.board(rs._scores_http(), league)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    return {'league': league, 'leagues': rs._scores.LEAGUES, 'games': rows or [], 'ok': rows is not None, 'at': round(rs.time.time())}


@router.get('/api/cats/scores/{league}/{event}')
async def scores_game(league: str, event: str):
    """📺 One game beside the stream: its win chance after every play, the newest plays, the line and total."""
    rs = _rs()
    try:
        g = await rs._scores.game(rs._scores_http(), league, event)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    return {**(g or {'win': [], 'plays': [], 'spread': None, 'total': None, 'by': None}), 'ok': g is not None, 'at': round(rs.time.time())}


@router.get('/api/cats/{cat_id}/feed')
async def cat_feed(cat_id: str, since: float = 0.0, ownerId: str = '', session: str = ''):
    """🔔 The desktop's notification bar: what this agent finished or thinks is worth a look, newest first. Its owner only (failed reviews are theirs)."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Cat not found.')
    rs._owner_gate(store, cat, session, ownerId, 'see its notifications')
    rows = []
    try:
        for r in await rs.asyncio.to_thread(rs._pev.recent, rs.DATA_DIR / rs._pev.DB_NAME, cat_id, since, 30):
            tone, word = rs.FEED_WORDS.get(r['event'], (None, None))
            if tone:
                rows.append({'at': r['at'], 'tone': 'look' if r.get('bad') else tone, 'kind': rs.FEED_KIND.get(r['kind'], r['kind']), 'text': f"{rs.FEED_KIND.get(r['kind'], r['kind'])} {word}{': ' + rs._feed_detail(r['detail']) if rs._feed_detail(r.get('detail')) else ''}", 'ref': r['ref']})
    except Exception:   # a busy or missing events file never breaks the desk
        pass
    rows += [x for x in rs._FEED.get(cat_id, []) if x['at'] > since]
    rows.sort(key=lambda x: -x['at'])
    out_ = {'rows': rows[:30], 'now': rs.time.time()}
    return out_ if cat.get('ownerStaff') else rs._collective_names(out_, True)   # 🫂 the bell speaks as The Collective


def _media_house(cat):
    """🔒 Only a staff agent (its owner is a FEELESS admin wallet, or the leader) may make media on FEELESS's own OpenRouter key."""
    rs = _rs()
    return bool(rs.os.environ.get('OPENROUTER_API_KEY', '').strip()) and (bool(cat.get('isLeader')) or rs.owner_wallet(cat) in rs.owner_wallets())


def _media_house_spent(day=None):
    rs = _rs()
    try:
        return float(rs.json.loads(rs.MEDIA_HOUSE_PATH.read_text()).get(day or rs.time.strftime('%Y-%m-%d'), 0))
    except (OSError, ValueError):
        return 0.0


def _media_house_add(usd):
    rs = _rs()
    d = rs.time.strftime('%Y-%m-%d')
    try:
        book = rs.json.loads(rs.MEDIA_HOUSE_PATH.read_text())
    except (OSError, ValueError):
        book = {}
    book = {k: v for k, v in book.items() if k >= rs.time.strftime('%Y-%m-%d', rs.time.localtime(rs.time.time() - 30 * 86400))}
    book[d] = round(float(book.get(d, 0)) + usd, 4); rs.MEDIA_HOUSE_PATH.write_text(rs.json.dumps(book))


def _media_refs(cat_id, md):
    """The make's reference pictures as data URLs, read fresh from disk (never stored in the sealed doc)."""
    rs = _rs()
    out = []
    for r_ in md.get('refs') or []:
        f_ = rs._media_dir() / cat_id / str(r_.get('url') or '').rsplit('/', 1)[-1]
        if rs._mg.NAME.fullmatch(f_.name) and f_.is_file():
            e_ = f_.suffix.lstrip('.').lower()
            out.append(f"data:image/{'jpeg' if e_ in ('jpg', 'jpeg') else e_};base64,{rs.base64.b64encode(f_.read_bytes()).decode()}")
    return out


async def _media_run(cat_id, ws_id, mid):
    """🎬 One image or video: submit on the owner's own key, poll, keep the file. Every step is written to the folder, so the page shows the truth."""
    rs = _rs()
    if mid in rs._MEDIA_LIVE:
        return
    rs._MEDIA_LIVE.add(mid)
    try:
        d_ = rs._ws_load(cat_id, ws_id) or {}; m_ = rs._media_msg(d_, mid)
        if not m_:
            return
        keep = rs.json.loads(rs.json.dumps(m_)); md = m_['media']
        cat = (rs._load()['cats'].get(cat_id) or {})
        key = rs._ck.key_for(cat, md['provider'], data_dir=rs.DATA_DIR) or (rs.os.environ.get('OPENROUTER_API_KEY', '').strip() if md.get('house') and rs._media_house(cat) else None)
        if not key:
            rs._media_set(cat_id, ws_id, mid, keep, status='failed', why=f"{rs._mg.PROVIDERS[md['provider']]['name']} is not linked any more."); return
        async with rs.httpx.AsyncClient(timeout=60, follow_redirects=True) as h:
            if md['provider'] == 'openrouter' and md['kind'] == 'image':   # 🖼 OpenRouter images come back in one answer (base64), no job to poll
                r = await h.post('https://openrouter.ai/api/v1/chat/completions', timeout=180, headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                                 json={'model': md['model'], 'modalities': ['image', 'text'], 'messages': [{'role': 'user', 'content': rs._mg.ref_content(md['prompt'], rs._media_refs(cat_id, md))}]})
                j_ = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
                im_ = (((j_.get('choices') or [{}])[0].get('message') or {}).get('images') or [{}])[0].get('image_url', {}).get('url', '')
                mt_ = rs.re.match(r'data:image/(png|jpe?g|webp);base64,(.+)', im_, rs.re.S)
                if not mt_:
                    rs._media_set(cat_id, ws_id, mid, keep, status='failed', why=f"{r.status_code}: {str((j_.get('error') or {}).get('message') if isinstance(j_.get('error'), dict) else 'no picture came back')[:160]}"); return
                raw_ = rs.base64.b64decode(mt_.group(2)); ext_ = 'jpg' if mt_.group(1).startswith('jp') else mt_.group(1)
                rs._media_dir().joinpath(cat_id).mkdir(parents=True, exist_ok=True); (rs._media_dir() / cat_id / f'{mid}.{ext_}').write_bytes(raw_)
                rs._feed_push(cat_id, {'tone': 'done', 'kind': 'PoC', 'text': f"Your image is ready ({md.get('label') or md['model']})", 'ref': ws_id})
                rs._media_set(cat_id, ws_id, mid, keep, status='done', url=f'/api/cats/media/{cat_id}/{mid}.{ext_}', kept=True, bytes=len(raw_), doneAt=round(rs.time.time()),
                           **({'paidUsd': round(float((j_.get('usage') or {}).get('cost')), 4)} if (j_.get('usage') or {}).get('cost') is not None else {}))
                return
            hd = md.get('handle')
            if not hd:
                img_du = None; model_sub = md['model']
                if (md.get('fromImg') or {}).get('url'):   # 👤 image → video: the made image rides as a data URL, read fresh from disk, never stored in the sealed doc
                    f_src = rs._media_dir() / cat_id / str(md['fromImg']['url']).rsplit('/', 1)[-1]
                    try:
                        ext_i = f_src.suffix.lstrip('.').lower()
                        img_du = f"data:image/{'jpeg' if ext_i in ('jpg', 'jpeg') else ext_i or 'png'};base64,{rs.base64.b64encode(f_src.read_bytes()).decode()}"
                        model_sub = md['model'] if md.get('swap') else rs._mg.i2v_model(md['modelId'])
                    except (OSError, ValueError) as e:
                        rs._media_set(cat_id, ws_id, mid, keep, status='failed', why=f'Its start image could not be used: {str(e)[:120]}'); return
                if md.get('swap'):   # 🎭 V2V: the clip rides as a data URL too, read fresh from disk
                    try:
                        f_clip = rs._media_dir() / cat_id / str(md['fromClip']['url']).rsplit('/', 1)[-1]; ext_c = f_clip.suffix.lstrip('.').lower()
                        clip_du = f"data:video/{'quicktime' if ext_c == 'mov' else ext_c};base64,{rs.base64.b64encode(f_clip.read_bytes()).decode()}"
                        meth, url, heads, body = rs._mg.v2v_req(md['modelId'], key, img_du, clip_du, md.get('note') or '')
                    except (OSError, KeyError, ValueError) as e:
                        rs._media_set(cat_id, ws_id, mid, keep, status='failed', why=f'Its clip could not be used: {str(e)[:120]}'); return
                else:
                    meth, url, heads, body = rs._mg.submit_req(md['provider'], model_sub, md['prompt'], key, md.get('modelId'), image=img_du)
                r = await h.request(meth, url, headers=heads, json=body)
                try:
                    hd = rs._mg.handle_of(md['provider'], r.json() if r.headers.get('content-type', '').startswith('application/json') else {})
                except ValueError as e:
                    rs._media_set(cat_id, ws_id, mid, keep, status='failed', why=f'{r.status_code}: {e}'); return
                rs._media_set(cat_id, ws_id, mid, keep, status='running', handle=hd, step='queued')
            started = float(md.get('at') or rs.time.time())
            while True:
                if rs.time.time() - started > rs._mg.GIVE_UP_S:
                    rs._media_set(cat_id, ws_id, mid, keep, status='failed', why='It took longer than 15 minutes. Nothing more is charged from here.'); return
                r = await h.get(hd['status'], headers=rs._mg.auth(md['provider'], key))
                st, why = rs._mg.state_of(md['provider'], r.json() if r.status_code == 200 else {'status': 'running'})
                if st == 'failed':
                    rs._media_set(cat_id, ws_id, mid, keep, status='failed', why=why or 'The provider stopped it.'); return
                if st == 'done':
                    break
                if why != md.get('step'):
                    md['step'] = why; rs._media_set(cat_id, ws_id, mid, keep, step=why)
                await rs.asyncio.sleep(rs._mg.POLL_S)
            if md['provider'] == 'openrouter':
                src = hd['result']   # its /content link needs the key (not presigned)
            else:
                r = await h.get(hd['result'], headers=rs._mg.auth(md['provider'], key))
                src = rs._mg.output_url(md['provider'], md['kind'], r.json() if r.status_code == 200 else {})
            if not src:
                rs._media_set(cat_id, ws_id, mid, keep, status='failed', why='It finished without a file.'); return
            rs._media_dir().joinpath(cat_id).mkdir(parents=True, exist_ok=True)
            got = 0; tmp = rs._media_dir() / cat_id / f'{mid}.part'
            async with h.stream('GET', src, **({'headers': rs._mg.auth('openrouter', key)} if md['provider'] == 'openrouter' else {})) as f:   # a provider's file link gets no key; OpenRouter's /content needs it
                ext = rs._mg.ext_of(md['kind'], src, f.headers.get('content-type', ''))
                with tmp.open('wb') as out:
                    async for chunk in f.aiter_bytes():
                        got += len(chunk)
                        if got > rs._mg.MAX_BYTES:
                            break
                        out.write(chunk)
            if got > rs._mg.MAX_BYTES or not got:
                tmp.unlink(missing_ok=True)
                rs._media_set(cat_id, ws_id, mid, keep, status='done', url=src, kept=False, why='Too big to keep here: the link is the provider\'s.'); return
            name = f'{mid}.{ext}'; tmp.replace(rs._media_dir() / cat_id / name)
            rs._media_set(cat_id, ws_id, mid, keep, status='done', url=f'/api/cats/media/{cat_id}/{name}', kept=True, bytes=got, doneAt=round(rs.time.time()))
            rs._feed_push(cat_id, {'tone': 'done', 'kind': 'PoC', 'text': f"Your {md['kind']} is ready ({md.get('label') or md['model']})", 'ref': ws_id})
    except (rs.httpx.HTTPError, OSError, ValueError, KeyError) as e:
        rs._media_set(cat_id, ws_id, mid, None, status='failed', why=f'{type(e).__name__}: {str(e)[:120]}')
    finally:
        rs._MEDIA_LIVE.discard(mid)


async def _clip_len(path):
    """🎭 A clip's real length and frame rate (ffprobe) → (seconds, fps), or (None, None) when it cannot be read."""
    rs = _rs()
    try:
        pr = await rs.asyncio.create_subprocess_exec('ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate:format=duration',
                                                  '-of', 'json', str(path), stdout=rs.asyncio.subprocess.PIPE, stderr=rs.asyncio.subprocess.DEVNULL)
        out, _ = await rs.asyncio.wait_for(pr.communicate(), 15)
        j = rs.json.loads(out or b'{}'); secs = float((j.get('format') or {}).get('duration') or 0)
        num, _s, den = str(((j.get('streams') or [{}])[0]).get('r_frame_rate') or '30/1').partition('/')
        fps = float(num) / float(den or 1) if float(den or 1) else 30.0
        return (secs, fps) if secs > 0 else (None, None)
    except (OSError, ValueError, rs.asyncio.TimeoutError, ZeroDivisionError):
        return None, None


async def _media_swap(cat_id, ws_id, doc_, t_, linked, text):
    """🎭 V2V: a clip already in this folder + a finished picture (the folder's character unless one is picked) → one fal.ai job. Nothing runs
    without fal.ai linked; the list-price estimate rides on the card before it starts."""
    rs = _rs()
    mid_ = str(t_.get('swap') or '')
    if mid_ not in rs._mg.V2V:
        raise rs.HTTPException(400, 'Pick Wan Replace, Kling Motion Control or FLUX Video Edit.')
    prov_ = rs._mg.v2v_provider(mid_); edit_ = mid_ in rs._mg.V2V_NO_CHAR
    if prov_ not in linked:
        raise rs.HTTPException(400, f"Link {rs._mg.PROVIDERS[prov_]['name']} first: this runs on your own {rs._mg.PROVIDERS[prov_]['name']} account.")
    cmd_ = (rs._media_msg(doc_, str(t_.get('clip') or '')) or {}).get('media') or {}
    if not cmd_.get('clip') or cmd_.get('status') != 'done' or not str(cmd_.get('url') or '').startswith('/api/cats/media/'):
        raise rs.HTTPException(400, 'Add your clip to this folder first.')
    if edit_ and not str(text or '').strip():
        raise rs.HTTPException(400, 'Say what to change in the clip, e.g. "make it night, neon signs".')
    img_ = '' if edit_ else str(t_.get('img') or (doc_.get('character') or {}).get('mid') or '')
    smd_ = (rs._media_msg(doc_, img_) or {}).get('media') or {} if img_ else {}
    if not edit_ and (smd_.get('status') != 'done' or smd_.get('kind') != 'image' or not str(smd_.get('url') or '').startswith('/api/cats/media/')):
        raise rs.HTTPException(400, 'Make or pick the character picture first (👤 Make him the character).')
    if sum(1 for m in doc_.get('messages') or [] if (m.get('media') or {}).get('status') in ('queued', 'running')) >= 3:
        raise rs.HTTPException(429, 'Three are already making. Wait for one to finish.')
    ep_, label_ = rs._mg.V2V[mid_][:2]; usd_ = rs._mg.v2v_cost(mid_, cmd_.get('secs') or rs._mg.MAX_CLIP_S, cmd_.get('fps') or 30)
    note_ = rs.re.sub(r'\s+', ' ', str(text or '')).strip()[:500]
    jid = 'm' + rs.uuid.uuid4().hex[:12]; now_ = round(rs.time.time())
    words_ = (f"{cmd_.get('label') or 'Your clip'}, edited: {note_}" if edit_ else f"{smd_.get('label') or 'The character'} swapped into {cmd_.get('label') or 'your clip'}" + (f' · {note_}' if note_ else ''))
    doc_['messages'] = list(doc_.get('messages') or []) + [{'by': 'Media', 'text': words_, 'at': now_,
        'media': {'id': jid, 'kind': 'video', 'provider': prov_, 'model': ep_, 'modelId': mid_, 'label': label_, 'usd': usd_, 'prompt': words_, 'note': note_,
                  'status': 'queued', 'at': now_, 'swap': True, **({} if edit_ else {'fromImg': {'mid': img_, 'url': smd_['url']}}), 'fromClip': {'mid': cmd_['id'], 'url': cmd_['url']}}}]
    rs._ws_save(cat_id, doc_)
    rs.asyncio.create_task(rs._media_run(cat_id, ws_id, jid))
    return {'doc': rs._ws_view(cat_id, ws_id)}


@router.get('/api/cats/media/{cat_id}/{name}')
async def cat_media_file(cat_id: str, name: str):
    """A finished image or video. Its id is random, so the link is the permission (a post can share it)."""
    rs = _rs()
    from starlette.responses import FileResponse
    if not rs.re.fullmatch(r'[A-Za-z0-9_-]{1,64}', cat_id) or not rs._mg.NAME.fullmatch(name):
        raise rs.HTTPException(404, 'No such file.')
    f_ = rs._media_dir() / cat_id / name
    if not f_.is_file():
        raise rs.HTTPException(404, 'No such file.')
    return FileResponse(f_, headers={'Cache-Control': 'public, max-age=86400'})


def _general_mind(cat):
    """🧠 One way of working for every agent: the owner's text from Fee's Prompt Studio, with this agent's own real record. Pages, content and plans only, never a buy or sell call."""
    rs = _rs()
    import prompt_studio as _ps
    try:
        text_ = ((rs._load()['cats'].get(rs.LEADER_ID) or {}).get('studio') or {}).get('general')
    except Exception:   # noqa: BLE001 — a bad read never stops the job
        text_ = None
    b_ = cat.get('brainsCfg') or {}; kind_ = (rs._CALL_CTX.get() or {}).get('kind')   # 🎭 AGT-3 / AGT-4: a proof kind may have its own prompt and its own personality
    own_ = str((b_.get('promptBy') or {}).get(kind_) or '').strip()
    return (_ps.general_block(text_, _ps.general_record(cat)) + _ps.persona_line((b_.get('personaBy') or {}).get(kind_) or b_.get('persona'))
            + (f"{_m}\n\n" if (_m := rs._vm.line(b_.get('voice'), (b_.get('persona') or {}).get('mirror'))) else '')   # 🪞 talks the way its owner writes, as much as the owner set
            + (f"THE OWNER'S PROMPT FOR THIS KIND OF PROOF (how to work, never an order to move money):\n{own_}\n\n" if own_ else '') + rs._know.WHERE + '\n\n')


def _popular_builds(store, raw=False):
    """Only pages their owner chose to send to the Collective, the ones marked working first. The owner's name never leaves here."""
    rs = _rs()
    rows = []
    for cid, c in (store.get('cats') or {}).items():
        for f in c.get('psFolders') or []:
            if not f.get('sent') or not f.get('ws') or f.get('graded') == 'wrong':
                continue
            doc = rs._ws_load(cid, f['ws'])
            if not (doc or {}).get('versions'):
                continue
            rows.append({'id': rs.hashlib.sha256(f"{cid}:{f['ws']}".encode()).hexdigest()[:16], 'cat': cid, 'ws': f['ws'], 'name': str(doc.get('name') or 'A build')[:60], 'kits': [k.get('name') for k in doc.get('kitsUsed') or [] if k.get('used')][:4], 'cost': round(float(doc.get('cost') or 0), 4), 'pages': len(doc['versions']), 'works': f.get('graded') == 'right', 'at': round(float(f.get('at') or 0))})
    rows.sort(key=lambda r: (not r['works'], -r['at']))
    return rows[:24] if raw else [{k: v for k, v in r.items() if k not in ('cat', 'ws')} for r in rows[:24]]


def _ws_placed(cat_id, html):
    """A page with its uploaded pictures in place. Only for showing it or sending it on: what is saved stays small."""
    rs = _rs()
    if 'feeless-file:' not in str(html or ''):
        return html
    cat = (rs._load().get('cats') or {}).get(cat_id) or {}

    def read(fid):
        row = rs._af.find(cat, fid); raw = rs._af.read(rs.DATA_DIR, cat, fid) if row else None
        return f"data:{row.get('mime') or 'image/png'};base64,{rs.base64.b64encode(raw).decode()}" if raw else None
    return rs._feat.place_files(html, read)


def _eco_desk_path(cat_id):
    rs = _rs()
    return rs.DATA_DIR / 'agent_eco' / rs.re.sub(r'[^a-z0-9]', '', str(cat_id).lower())[:40] / 'desk.seal'


def _eco_desk_load(cat_id):
    """🗂 Its owner's desk. A file that cannot be opened stops the request instead of looking empty, so a save can never wipe real books."""
    rs = _rs()
    f_ = rs._eco_desk_path(cat_id)
    if not f_.exists():
        return rs._eco.empty_desk()
    try:
        return {**rs._eco.empty_desk(), **rs.json.loads(rs._ck.unseal_bytes(f_.read_bytes(), cat_id))}
    except (OSError, ValueError) as e:
        raise rs.HTTPException(500, 'Your PoEco desk could not be opened, so nothing was changed.') from e


def _eco_desk_save(cat_id, desk):
    rs = _rs()
    f_ = rs._eco_desk_path(cat_id); f_.parent.mkdir(parents=True, exist_ok=True); tmp_ = f_.with_suffix('.tmp'); tmp_.write_bytes(rs._ck.seal_bytes(rs.json.dumps(desk).encode(), cat_id)); tmp_.replace(f_)


def _play_path(cat_id, name):
    rs = _rs()
    return rs.DATA_DIR / 'agent_play' / rs.re.sub(r'[^a-z0-9]', '', str(cat_id).lower())[:40] / f'{name}.seal'


def _play_load(cat_id, name):
    rs = _rs()
    try:
        return rs.json.loads(rs._ck.unseal_bytes(rs._play_path(cat_id, name).read_bytes(), cat_id))
    except (OSError, ValueError):
        return None


def _play_save(cat_id, name, data):
    rs = _rs()
    f_ = rs._play_path(cat_id, name); f_.parent.mkdir(parents=True, exist_ok=True); tmp_ = f_.with_suffix('.tmp'); tmp_.write_bytes(rs._ck.seal_bytes(rs.json.dumps(data).encode(), cat_id)); tmp_.replace(f_)


async def _ws_ask(cat, model, sys_, user_, tokens):
    rs = _rs()
    own_ = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
    text_, usd_, _via = await rs._think(cat, model, [{'role': 'system', 'content': rs._general_mind(cat) + sys_}, {'role': 'user', 'content': user_}], own_, None, tokens)
    rs._WS_VIA.set(str(_via or ''))   # 🧾 who REALLY answered (a free stand-in when its paid route is off), read by callers that show the model
    return str(text_ or ''), float(usd_ or 0), bool(own_)


def _answered_by(model, via):
    """→ the model name to show: the asked one, or the free stand-in that answered for it (never a paid name on a free answer)."""
    return via.split(' · ', 1)[1].replace(' stood in', '') + ' (stood in)' if ' stood in' in str(via) and ' · ' in str(via) else str(model).split('/')[-1]


def talk_targets(b, to):
    """'0' / '1' / 'both' → the mind indexes that answer, only minds it really has. Pure."""
    n = len(b.get('brains') or [])
    want = [0, 1] if str(to or 'both') == 'both' else [int(to)] if str(to).isdigit() else []
    return [i for i in want if i < n]


def mind_name(b, i):
    names = b.get('mindNames') or []
    return str(names[i]) if i < len(names) and names[i] else str((b.get('brains') or [''] * (i + 1))[i]).split('/')[-1].split(':')[0][:20] or 'AB'[i]


async def _talk_reply(cat, i, text):
    rs = _rs()
    b = cat.get('brainsCfg') or {}; model = b['brains'][i]; name = rs.mind_name(b, i)
    short = str(model).split('/')[-1].split(':')[0]
    calls = '; '.join(f"{x.get('word')} ${x.get('sym')}" for x in (b.get('decisions') or []) if short in str(x.get('by') or ''))[-300:] or 'none yet'
    own_ = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
    try:
        out, usd, via = await rs.asyncio.wait_for(rs._think(cat, model, [{'role': 'system', 'content': rs.TALK_SYS.format(name=name, cat=cat.get('name') or 'its agent', calls=calls, where=rs._know.WHERE)},
                                                               {'role': 'user', 'content': text}], own_, None, 260), rs.TALK_S)
    except Exception as e:   # noqa: BLE001 — a mind that does not answer says so in the chat
        out, usd, via = '', 0.0, ''
        print(f"[talk] {cat.get('id')} {name}: {str(e)[:100]}")
    said = ' '.join(str(out or '').split())[:700]
    rs._TALK_DONE.append({'cat': cat['id'], 'i': i, 'by': name, 'at': rs.time.time(), 'usd': float(usd or 0) if not own_ and via == 'openrouter' else 0.0,
                       'text': said or f"{name} did not answer — {'its machine looks off' if str(model).startswith('local/') else 'its model did not reply'}.", 'miss': not said})


def _talk_pass(store):
    rs = _rs()
    while rs._TALK_DONE:
        o = rs._TALK_DONE.pop(0); b_ = ((store['cats'].get(o['cat']) or {}).get('brainsCfg'))
        if not b_:
            continue
        if o['usd']:
            rs._lc.charge(b_, o['usd'])
        b_['talk'] = ((b_.get('talk') or []) + [{k: o[k] for k in ('i', 'by', 'at', 'text', 'miss')}])[-rs.TALK_KEEP:]
        b_['talkWait'] = [x for x in b_.get('talkWait') or [] if x != o['i']]


def _ws_pass(store):
    rs = _rs()
    while rs._WS_DONE:
        o = rs._WS_DONE.pop(0); c_ = store['cats'].get(o['cat'])
        if not c_:
            continue
        if o['cost'] and not o['own'] and c_.get('brainsCfg'):
            rs._lc.charge(c_['brainsCfg'], o['cost'])
        if o['doc']:   # 💻 the page it built is filed as a PoStatic
            filed_ = rs._feat.file_static(c_, o['doc'], (o['doc']['versions'][-1] or {}).get('by') or 'Mind', rs.time.time())
            filed_['cost'] = round(float(o['cost'] or 0), 6)


async def _ws_page(cat, model, sys_, user_, tokens, on_part=None):
    """One whole page. The wallet's provider stops a reply at about 1,500 tokens whatever is asked (receipts, 2026-11-05), so an unfinished page is continued from where it stopped, up to 3 more calls."""
    rs = _rs()
    started_ = rs.time.time(); raw, usd, own = await rs._ws_ask(cat, model, sys_, user_, tokens)
    if on_part:   # 👀 the Code tab shows each part as it lands, and the chat's cost moves with it
        on_part(raw, usd)
    for _ in range(3):
        html = rs._aip.html_of(raw)
        if not html or rs._feat.page_complete(html):
            break
        if str(model).startswith('local/') and rs.time.time() - started_ > rs.LOCAL_PAGE_S:   # its own machine pulls its own weight, or it stops: one page never holds the Mac for 20 minutes
            break
        more, u_, own = await rs._ws_ask(cat, model, sys_, f"{user_[:6000]}\n\nYour page stopped partway. It ended with:\n{raw[-1200:]}\n\nContinue from exactly the next character.{rs._feat.cut_hint(raw)} Send only the rest of the document: no repeat, no code fences, no comment.", tokens)
        usd += u_
        if not more.strip():
            break
        more = rs.re.sub(r'```(?:html)?', '', more)
        raw = more if rs.re.match(r'\s*<(!doctype|html)', more, rs.re.I) else raw + more   # a model that starts the page over replaces it, or the two would never parse as one
        if on_part:
            on_part(raw, usd)
    return raw, usd, own


def _ws_rewind(cat, cat_id, doc, n, now):
    """↩ Back to page n. A later page that was filed as a proof keeps its own small copy, so the agent's record is never touched. Nothing else is stored: the scene comes back out of the page itself. → the request to try again"""
    rs = _rs()
    got = rs._feat.rewind(doc, n); start = len(doc.get('versions') or [])
    for f in cat.get('psFolders') or []:
        if isinstance(f, dict) and f.get('ws') == doc.get('id') and int(f.get('version') or 0) > start:
            i = int(f['version']) - start - 1
            if 0 <= i < len(got['cut']):
                keep = rs._feat.new_doc({'id': 'w' + rs.secrets.token_hex(5), 'kind': 'build', 'name': doc.get('name'), 'at': round(now)}); keep['versions'] = [got['cut'][i]]; keep['archived'] = True; rs._ws_save(cat_id, keep); f.update(ws=keep['id'], version=1)
    first, second = rs._play.scene_from_html(((doc.get('versions') or [{}])[-1] or {}).get('html'))
    if first:
        doc['scene3d'] = rs._play.clean_scene(first); doc['scene3dNext'] = rs._play.clean_scene(second) if second else None; rs._play_save(cat_id, '3d', {'scene': doc['scene3d'], 'mind': doc['scene3d']})
    talk = rs._play_load(cat_id, 'convo')
    if isinstance(talk, list) and got['at']:
        rs._play_save(cat_id, 'convo', [r for r in talk if not isinstance(r, dict) or float(r.get('at') or 0) <= got['at'] or r.get('kind') != 'pos'])
    return got['request']


async def _ws_sections(cat, minds, text, extra):
    """🧩 A page built in sections: the first mind writes a small shell, then the minds take the sections in turn, each reply short enough to finish.
    Cloud minds write their sections at the same time; a local machine writes one at a time. → (html or None, $, own key, parts written)"""
    rs = _rs()
    raw, usd, own = await rs._ws_ask(cat, minds[0], rs._feat.SECTIONS_SYS, f'BUILD THIS: {str(text)[:2000]}', 500)   # the mind plans; code writes the frame, so the frame always finishes
    shell = rs._feat.code_shell(rs._feat.plan_sections(raw, text)); parts = rs._feat.shell_parts(shell)
    async def one(i, n, brief):
        r_, u_, _o = await rs._ws_ask(cat, minds[i % len(minds)], rs._feat.PART_SYS.format(n=n) + extra[:1500], f'THE PAGE: {str(text)[:800]}\nTHIS SECTION ({n}): {brief}\nTHE OTHER SECTIONS: {'; '.join(f'{m}: {b_}' for m, b_ in parts if m != n)}', 1400)
        return n, rs._feat.part_html(r_), u_
    jobs = [(i, n, b) for i, (n, b) in enumerate(parts)]
    got = [await one(*j) for j in jobs] if any(str(m).startswith('local/') for m in minds) else await rs.asyncio.gather(*[one(*j) for j in jobs])
    usd += sum(g[2] for g in got); done = {n: h for n, h, _ in got if h.strip()}
    html = rs._aip.lock_html(rs._feat.assemble(shell, done)) if done else None
    return (html if html and rs._feat.page_complete(html) else None), usd, own, len(done)


async def _build_game(cat, doc, text, brains, order, name, to):
    """🎮 AGT-35: a mind designs the game, writes it on a real free engine, a headless browser plays it, the other mind fixes what failed.
    Only a game that passes the playtest becomes a version. → (cost, why it stopped or None, paid on its own key)"""
    rs = _rs()
    cat_id = cat.get('id'); cost = 0.0; own = False; lead, other = order[0], order[-1]
    stage = lambda st, by=None, **x: rs._ws_save(cat_id, {**doc, 'busy': {'at': round(rs.time.time()), 'to': to, 'stage': st, 'spent': round(cost, 6), **({'by': by} if by else {}), **x}})
    stage('suggest', name(lead))
    raw, usd, own = await rs._ws_ask(cat, brains[lead], rs._forge.DESIGN_SYS, f'The owner wants: {text}', 900); cost += usd
    try:
        design = rs._forge.design_of(raw)
    except ValueError as e:
        rs._feat.add_msg(doc, name(lead), f'I could not design it: {e}', rs.time.time()); return cost, str(e), own
    eng = rs._forge.ENGINES[design['engine']]
    rs._feat.add_msg(doc, name(lead), f"THE DESIGN · {design['title']} · {design['genre']} on {eng['name']}\n{design['pitch']}\nLoop: {design['coreLoop']}\nControls: {design['controls']['keys']} / touch: {design['controls']['touch']}\nWin: {design['win']} · Lose: {design['lose']}", rs.time.time())
    stage('build', name(lead))
    raw, usd, own = await rs._ws_page(cat, brains[lead], rs._forge.build_sys(design), text, 12000); cost += usd
    html = rs._forge.html_of(raw); by = name(lead); report = {'ok': False, 'why': ['it wrote no page']}
    for n in range(rs._forge.MAX_FIX + 1):
        if '<' not in html:
            report = {'ok': False, 'why': ['it wrote no page'], 'facts': {}}
        else:
            stage('review', 'playtest', step=n)
            try:
                report = await rs.asyncio.wait_for(rs._forge.playtest(html, rs._fb.chromium_path()), 120)
            except Exception as e:   # noqa: BLE001: a browser that cannot start is said plainly, never counted as a pass
                report = {'ok': False, 'why': [f'the test browser did not run: {type(e).__name__}'], 'facts': {}}
        if report['ok'] or n == rs._forge.MAX_FIX:
            break
        rs._feat.add_msg(doc, 'Playtest', 'Failed: ' + '; '.join(report['why']), rs.time.time())
        stage('review', name(other))
        raw, usd, _o = await rs._ws_page(cat, brains[other], rs._forge.fix_sys(design, report), f'{text}\n\nTHE CURRENT FILE (fix it, keep what works):\n{html[:45000]}', 12000); cost += usd
        html = rs._forge.html_of(raw) or html; by = name(other)
    if not report['ok']:
        rs._feat.add_msg(doc, 'Playtest', 'Not filed. It still fails: ' + '; '.join(report['why']), rs.time.time())
        return cost, 'The game failed its playtest: ' + '; '.join(report['why'])[:200], own
    doc['game'] = {'design': design, 'engine': design['engine'], 'license': eng['license'], 'playtest': report['facts'], 'at': round(rs.time.time())}
    doc['kitsUsed'] = [{'id': design['engine'], 'name': eng['name'], 'used': True}]
    rs._feat.add_version(doc, html, by, rs.time.time()); rs._parts_used(cat_id, doc.get('id'), html)
    f_ = report['facts']
    rs._feat.add_msg(doc, 'Playtest', f"Passed: it draws, takes input ({f_.get('changed')} pixels moved), reached \"{(f_.get('after') or {}).get('state')}\", {f_.get('fps')} fps, no errors. Page {len(doc['versions'])} is ready. Open Static to play it.", rs.time.time())
    return cost, None, own


async def _build_3d(cat, doc, text, brains, order, name, to):
    """🧊 The full prompt becomes a scene of real assets, a second pass checks it word by word against the prompt, and it becomes a real page and a new version. The owner can keep working on it in the 3D studio. → (cost, why it stopped, own key)"""
    rs = _rs()
    room_ask = bool(doc.get('scene3dNext')) and rs._play.names_room(text); wrong_ = bool(rs._play.WRONG_BUILD.search(str(text)))   # a site of two places: the words say which one changes
    slot = 'scene3dNext' if room_ask else 'scene3d'; cat_id = cat.get('id'); cost = 0.0; own = False; now_scene = rs._play.clean_scene(None if wrong_ else doc.get(slot)); seen_used = []; seen_missing = []; prompt = rs._play.prompt_of(text)
    first_ask = next((m.get('text') for m in doc.get('messages') or [] if m.get('by') == 'you'), '')
    if wrong_ and first_ask and first_ask != text:   # "that is not what I asked": build what was asked first, with this correction on top
        prompt = f'{prompt}\nTHE ORIGINAL ASK: {rs._play.prompt_of(first_ask)}'
    if rs._play.chart_only(text, now_scene, doc.get('name')):   # 📊 no model needed: the 3D, the light and the words stay exactly as they are
        doc[slot] = rs._play.ensure_asks(now_scene, text, doc.get('name'))
        if doc.get('scene3dNext') and slot == 'scene3d' and rs.re.search(r'(?i)\broom\b', str(text)):
            doc['scene3dNext'] = rs._play.ensure_asks(doc['scene3dNext'], text, doc.get('name'))
        first_, next_ = doc.get('scene3d'), doc.get('scene3dNext')
        rs._feat.add_version(doc, rs._play.lock_site(rs._play.to_html(first_, doc.get('name'), next_)), 'FEELESS', rs.time.time()); rs._play_save(cat_id, '3d', {'scene': doc[slot], 'mind': doc[slot]})
        rs._feat.add_msg(doc, 'FEELESS', f"Page {len(doc['versions'])} is ready. Open Static to try it. Read from the page: {rs._play.page_facts(first_, next_)} The numbers are samples until the coin is live. The 3D and your words did not change.", rs.time.time())
        return 0.0, '', False
    if not brains:
        rs._feat.add_msg(doc, 'FEELESS', 'Pick a model for this agent first. Nothing changed.', rs.time.time())
        return 0.0, 'This agent has no model.', False
    fit_ = rs._fit_line(cat, 'pos')
    if fit_ and doc.get('fitSaid') != fit_:
        rs._feat.add_msg(doc, 'FEELESS', fit_, rs.time.time()); doc['fitSaid'] = fit_
    def busy(stage):
        doc['stage'] = stage; rs._ws_save(cat_id, {**doc, 'busy': {'at': round(rs.time.time()), 'to': to, 'stage': stage, 'spent': round(cost, 6)}})
    async def resolve(scene):
        async with rs.httpx.AsyncClient(timeout=30) as h_:
            await rs._assets.ensure(h_, rs.KITS_DIR); scene, used, missing = await rs._assets.fill(h_, rs.KITS_DIR, scene, many=bool(rs._assets.MANY.search(prompt)), avoid=rs._play_load(cat_id, 'usedAssets') or [])
        seen_used.extend(used); seen_missing.extend(missing)
        return scene
    fresh_ = wrong_ or not (now_scene['objects'] or now_scene.get('hero')); print_ = rs._play.creative_print(f'{doc.get("id")}{rs.time.time()}{prompt[:80]}', rs._play_load(cat_id, 'prints') or [], text) if fresh_ and slot == 'scene3d' else None
    if rs._play.wants_code(prompt) and print_:   # a design no library holds is what the code-built worlds are for
        print_['mood'] = 'space'
    mode_k_, mine_k_ = rs._kits.picks_of(cat.get('brainsCfg'), 'pos'); picks_k_ = rs._kits.auto_picks(rs.KITS_DIR, 'pos', prompt, record=rs._kit_record()) if mode_k_ == 'auto' else mine_k_; stash_, stash_names_ = rs._kits.stash_line(rs.KITS_DIR, 'pos', prompt, picks_k_); doc['kitsStash'] = stash_names_
    was_ = doc.get(slot) if wrong_ else None
    kit_read_ = rs._play.rejected_line(was_) + rs._kits.line(rs.KITS_DIR, 'pos', picks_k_)[:2500] + stash_ + rs._kits.skills_line(cat.get('brainsCfg')) + rs._foot.note('pos', cat.get('psFolders')) + rs._convo(cat) + ('\n' + rs._play.print_line(print_) if print_ else '')
    busy('build'); scene = None; say = ''; by = name(order[0]); tries = [(order[0], '')]
    tries += [(i, '') for i in range(len(brains)) if i != order[0]] or [(order[0], ' Your last reply could not be read. Send one JSON object and nothing else.')]
    for i_, extra_ in tries:   # one bad reply never ends a build: the other mind tries, and a lone mind gets one more go
        raw, usd, own = await rs._ws_ask(cat, brains[i_], rs._play.SCENE_SYS + rs._play.EXACT + (rs._play.KEEP_LOOK if now_scene['objects'] else '') + rs._play.references_line(rs._play_load(cat_id, 'refs') or [], prompt) + kit_read_ + extra_ + rs._play.notes_line(cat, '3d') + rs._recall(cat, 'Code', prompt), f'THE SCENE NOW: {rs._play.scene_brief(now_scene)}\nTHE FULL PROMPT: {prompt}', 3500); cost += usd
        scene, say = rs._play.parse_reply(raw, now_scene, prompt)
        if scene:
            scene, kept_ = rs._play.keep_monitors(scene, now_scene, text, prompt); scene = {**rs._play.ensure_named(scene, kept_), 'page': rs._play.keep_page(now_scene.get('page'), scene.get('page'), text)}; by = name(i_); break
        print(f'[3d] unreadable reply from {brains[i_]}: {str(raw)[:160]!r} ... {str(raw)[-120:]!r}')
    if not scene and fresh_:   # 🧩 no model could answer: its words still name real things, so the owner gets a set and is told why
        got_ = rs._play.brief_from_words(rs.KITS_DIR, text)
        if got_:
            scene = rs._play.clean_scene(rs._play.from_brief(got_, prompt)); say = 'Your models could not answer, so this was built from your words.'; by = 'FEELESS'
    if not scene:
        rs._feat.add_msg(doc, name(order[0]), 'It did not send a usable scene. Nothing changed, and the last page is safe. Try again.', rs.time.time())
        return cost, 'It did not send a usable scene.', own
    if print_:
        scene = rs._play.apply_print(scene, print_); rs._play_save(cat_id, 'prints', ([*(rs._play_load(cat_id, 'prints') or []), print_])[-40:])
    scene = rs._play.lead_up(await resolve(scene))
    if print_ and not scene.get('hero') and not any(o.get('asset') for o in scene['objects']):   # nothing named is in the library: a code-built centrepiece holds the set, and the message names what was missing
        scene['hero'] = rs._play.HEROES[len(prompt) % len(rs._play.HEROES)]
    if not scene['objects'] and not scene.get('hero'):
        rs._feat.add_msg(doc, by, f"Nothing it asked for exists in the library: {', '.join(seen_missing[:6])}. Nothing changed. Try other words.", rs.time.time())
        return cost, 'None of its assets were found.', own
    checked = ''; checker = brains[order[-1]] if len(order) > 1 else brains[order[0]]; check_by = name(order[-1]) if len(order) > 1 else ''
    if fresh_:   # a check is against the whole prompt, so an edit skips it: it answered "the prompt has no page 5", and added things nobody asked for
        busy('review')
        try:
            raw, usd, own2 = await rs._ws_ask(cat, checker, rs._play.CHECK_SYS, f'THE FULL PROMPT: {prompt}\nTHE BUILD: {rs._play.build_summary(scene)}', 1500); cost += usd; own = own or own2
            fixed, checked = rs._play.parse_reply(raw, scene, prompt); light_ = scene.get('hdri')
            if fixed and scene.get('hero') and scene.get('mood'):   # a code-drawn centrepiece looks like an empty set to a checker: it put a literal button model under the black hole
                fixed = {**scene, 'page': rs._play.keep_page(scene.get('page'), fixed.get('page'), text)}; scene = fixed; checked = checked or 'The words were checked'
            elif fixed and len(fixed['objects']) < len(scene['objects']):   # a real checker shrank a good set to one object: a check may add, it may not take away
                checked = 'The check found nothing to add'
            elif fixed:
                fixed.pop('light_find', None); fixed['hdri'] = light_ or fixed.get('hdri'); fixed = {k: v for k, v in fixed.items() if v is not None}; fixed['page'] = rs._play.keep_page(scene.get('page'), fixed.get('page'), text); fixed, kept_ = rs._play.keep_monitors(fixed, scene, text, prompt); scene = await resolve(rs._play.ensure_named(fixed, kept_))   # the check fixes what is missing: the light the builder chose stands
            elif not checked:
                m_ = rs.re.search(r'"say"\s*:\s*"([^"]{1,160})"', str(raw)); checked = m_.group(1) if m_ else ''
        except Exception as e:   # noqa: BLE001 — the build still stands without its check
            checked = f'The check did not finish: {str(e)[:60]}'
    scene = rs._play.ensure_asks(rs._play.drop_rejected(scene, was_), text, doc.get('name'))
    rs._play_save(cat_id, 'usedAssets', list(dict.fromkeys([*(rs._play_load(cat_id, 'usedAssets') or []), *[(o.get('asset') or {}).get('id') for o in scene.get('objects') or [] if o.get('asset')]]))[-400:])
    keep_cam = scene.get('camera') if any(o['name'] == 'Back wall' for o in scene['objects']) else None; scene['camera'] = [0, 0, 0]; scene = rs._play._frame(rs._assets.compose(scene)); scene['camera'] = rs._play.room_camera(scene) if keep_cam else scene['camera']   # every build is framed by code on what really landed
    async with rs.httpx.AsyncClient(timeout=120) as h_:
        await rs._play.embed_pictures(h_, [scene])
    doc[slot] = scene
    if slot == 'scene3d' and doc.get('scene3dNext') and rs.re.search(r'(?i)\b(room|enter the room)\b', str(text)) and rs._play.ASKS_DASH.search(str(text)):   # one message about both places
        doc['scene3dNext'] = rs._play.ensure_asks(doc['scene3dNext'], text, doc.get('name'))
    first_, next_ = doc.get('scene3d') or scene, doc.get('scene3dNext')
    usable_ = [p for p in (picks_k_ or []) if p in rs._kits.KIT_USE and p != 'three'] if (first_.get('code') or {}).get('js') or (first_.get('code') or {}).get('html') else []
    html = rs._play.lock_site(rs._play.to_html(first_, doc.get('name'), next_), usable_)
    looked_ = ''
    if fresh_ and not first_.get('game'):   # 👁 a mind that can see looks at its own page once, and may fix what is wrong
        rows_ = {r['id']: r for r in ((rs._MODELS.get('rows') or {}).get('models') or [])}; eye_ = next((m for m in brains if (rows_.get(m) or {}).get('vision')), None)
        if eye_:
            busy('review')
            try:
                seen_ = await rs._look.shot(html, rs._fb.chromium_path())
                if seen_:
                    raw_, usd_ = '', 0.0
                    raw_, usd_, _o = await rs._ws_ask(cat, eye_, rs._play.LOOK_SYS, [{'type': 'text', 'text': f"THE REQUEST: {prompt[:1500]}\nWHAT IS ON THE SET: {rs._play.scene_brief(first_)}"}, {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + rs.base64.b64encode(seen_).decode()}}], 500); cost += usd_
                    fixed_, looked_ = rs._play.apply_look(first_, raw_)
                    if fixed_:
                        first_ = fixed_; doc[slot if slot == 'scene3d' else 'scene3d'] = first_; html = rs._play.lock_site(rs._play.to_html(first_, doc.get('name'), next_), usable_)
            except Exception as e:   # noqa: BLE001 — a look that fails never costs the page
                print(f'[look] {str(e)[:120]}')
    doc['scene3d'] = first_; doc['kitsUsed'] = [{'id': 'three', 'name': 'three.js', 'used': True}]; rs._feat.add_version(doc, html, by, rs.time.time()); rs._play_save(cat_id, '3d', {'scene': scene, 'mind': scene}); rs._play_save(cat_id, 'refs', rs._play.add_reference(rs._play_load(cat_id, 'refs') or [], doc.get('name'), prompt, scene))
    rs._feat.add_msg(doc, by, (f"{say} " if say else '') + f"Page {len(doc['versions'])} is ready. Open Static to try it." + (f" {by} built it, {check_by} checked it against your words{': ' + checked.rstrip('.') if checked else ''}." if check_by and check_by != by and fresh_ else '') + f" Real assets: {', '.join(dict.fromkeys(seen_used)) or 'none'}." + (f" Not in the library, so left out: {', '.join(dict.fromkeys(seen_missing))}." if seen_missing and (seen_used or not now_scene['objects']) else '') + (f" This print: {rs._play.MOODS[scene['mood']]['name']} mood, words {scene.get('layout') or 'left'}." if print_ and scene.get('mood') in rs._play.MOODS else '') + f' Read from the page: {rs._play.page_facts(first_, next_)}' + (f' The other mind said: {checked}.' if checked and not rs._play.ASKS_DASH.search(str(text)) else '') + (f' It looked at its own page: {looked_}.' if looked_ else '') + ' Open 3D studio to change it by hand.', rs.time.time())
    return cost, '', own


async def _ws_run(cat_id, ws_id, to, text, region):
    """🛠 One request in a feature folder. Build: one mind writes the page, or A writes and B improves it. Content or research: an answer per mind. It never touches the store until it has an answer."""
    rs = _rs()
    doc = rs._ws_load(cat_id, ws_id) or {}; cat = rs._load()['cats'].get(cat_id) or {}; cost = 0.0; paid_own = False
    kind = doc.get('kind'); pk_ = {'build': 'pos', 'content': 'poc'}.get(kind); brains = [rs._ads.MODEL] if doc.get('ad') else rs._lc.minds_for(cat.get('brainsCfg'), pk_); start_versions = len(doc.get('versions') or [])   # 🎬 a Showcase ad is built by the design-grade model
    if pk_:
        rs._CALL_CTX.set({'kind': pk_, 'ref': ws_id, 'minds': brains})   # 🧾 its own task (_ws_start): the context ends with it
    order = list(range(len(brains))) if to == 'both' else [1 if to == 'b' and len(brains) > 1 else 0]; name = lambda i: 'Mind ' + 'AB'[i]
    rs._OR_PLUGINS.set(tuple(rs._feat.or_plugins(rs._feat.build_cfg(doc))))
    stop_why = ''
    try:
        if kind == 'build' and rs._play.wants_game(text) and not doc.get('scene3d') and not doc.get('ad'):   # 🎮 AGT-35: a game is designed, engine-built and playtested, never a template (an ad's brief reads like a game: 'plays by itself in a loop'; it is a page)
            usd_, stop_why, paid_own = await rs._build_game(cat, doc, text, brains, order, name, to)
            cost += usd_
        elif kind == 'build' and not doc.get('ad') and (rs._assets.wants_3d(text) or rs._play.wants_code(text) or doc.get('scene3d')):   # 🧊 owner 2026-11-06: a 3D prompt is built in the 3D studio with real assets and checked against the prompt, never hand written. A plain game is written by the minds (owner 2026-11-07: the runner template came back for every arcade ask); a 3D game still goes to the studio
            lead_ = len(doc.get('versions') or []) % len(order) if to == 'both' and len(order) > 1 else 0   # 🧠🧠 owner 2026-11-07 "only ONE mind seems to work": with both picked, the minds take turns leading a 3D round and the other checks it
            usd_, stop_why, paid_own = await rs._build_3d(cat, doc, text, brains, order[lead_:] + order[:lead_], name, to)
            cost += usd_
        elif kind == 'build':
            cur = (doc.get('versions') or [{}])[-1].get('html') or ''; cfg_ = rs._feat.build_cfg(doc); pl_ = doc.get('plan') or {}
            read_ = ''
            if not cur:   # a new page learns from the best first. An edit already has its page
                read_, doc['sitesRead'] = await rs._site_reads('pos', (cat['id'], cat.get('name')))
            if not cur and not region and not pl_.get('approved') and (cfg_['research'] or cfg_['suggest']):   # 🔎 a proof proves first: read the best current builds, then suggest, before anything is built
                doc['stage'] = 'research'; rs._ws_save(cat_id, {**doc, 'busy': {'at': round(rs.time.time()), 'to': to, 'stage': 'research'}})
                async with rs.httpx.AsyncClient(timeout=12) as http_r:
                    refs_ = await rs._tools.build_refs(http_r, text, cfg_['depth'] == 'deep') if cfg_['research'] else []
                doc['stage'] = 'suggest'; rs._ws_save(cat_id, {**doc, 'busy': {'at': round(rs.time.time()), 'to': to, 'stage': 'suggest'}}); open_ = [r for r in refs_ if r.get('open')]
                menu_ = '\n'.join(f"{i + 1}. {r['title']} ({r['source']}, {r['score']}): {r['why']}" for i, r in enumerate(open_)) or 'None found.'
                plan_ = rs._OR_PLUGINS.set(tuple(rs._feat.or_plugins(cfg_, json_reply=True)))
                try:
                    raw_, usd_, own_ = await rs._ws_ask(cat, brains[order[0]], rs._feat.plan_sys(text) + rs._feat._sources.proof_line('pos') + read_ + rs._recall(cat, 'Code', text) + rs._foot.note('pos', cat.get('psFolders')), f'The owner wants: {text}\nReferences:\n{menu_}', 420)
                finally:
                    rs._OR_PLUGINS.reset(plan_)
                cost += usd_; paid_own = own_; doc['lastCost'] = round(cost, 6); doc['plan'] = {'ask': text, 'to': to, 'allRefs': refs_, 'plan': rs._feat.parse_plan(raw_, open_), 'by': name(order[0]), 'at': round(rs.time.time()), 'approved': not cfg_['suggest']}
                if cfg_['suggest']:
                    doc['stage'] = 'approve'; rs._feat.add_msg(doc, name(order[0]), 'I read the current best builds and wrote a plan. Approve it or tell me what to change.', rs.time.time())
                    doc['busy'] = None; doc['cost'] = round(float(doc.get('cost') or 0) + cost, 6); rs._ws_save(cat_id, doc)
                    if cost and not paid_own:
                        store = rs._load(); c_ = store['cats'].get(cat_id)
                        if c_ and c_.get('brainsCfg'):
                            rs._lc.charge(c_['brainsCfg'], cost); rs._save(store)
                    return
            if not cfg_['review']:
                order = order[:1]
            doc['stage'] = 'build'; ask_ = rs._feat.build_prompt(text, ((doc.get('plan') or {}).get('plan') if not cur else None))
            from_repo_ = ''
            if doc.get('source') and cat.get('projectRepo'):   # 📂 the files its owner picked, read live and kept nowhere
                try:
                    async with rs.httpx.AsyncClient(timeout=20) as http_src:
                        from_repo_ = rs._cg.source_block(await rs._cg.project_read(http_src, rs._ck.key_for(cat, 'github_project', data_dir=rs.DATA_DIR), cat['projectRepo'], doc['source']))
                except rs.httpx.HTTPError:
                    from_repo_ = ''
            rs._keep_mark_notes(doc, region)
            user = f'{ask_}{rs._know.for_ask(text)}{rs._feat.region_note(region, blank=not cur)}{rs._feat.attach_note(doc.pop("attached", None))}{from_repo_}' + (f'\nThe page now:\n{cur[:40000]}' if cur else '')
            if rs._feat.wants_live(text) or 'feeless-live' in str(cur):   # 📡 a page that asks for live data gets real numbers and how to receive them
                user += rs._feat.live_line(await rs._live_feed(cat), page=True)
            mode_k_, mine_k_ = rs._kits.picks_of(cat.get('brainsCfg'), 'pos'); picks_ = rs._kits.auto_picks(rs.KITS_DIR, 'pos', text, record=rs._kit_record()) if mode_k_ == 'auto' else mine_k_
            picks_ = list(rs._ads.KITS) if doc.get('ad') else picks_   # 🎬 an ad gets GSAP, never a game kit (Phaser dragged in the game playtest and its STATE / SCORE counter, 2026-11-11)
            stash_, doc['kitsStash'] = rs._kits.stash_line(rs.KITS_DIR, 'pos', text, picks_)
            kits_ = rs._kits.use_line(picks_) + stash_ + rs._parts.offer_line(rs._parts.offer(rs._parts_path(), text)) + rs._mark_lessons() + rs._kits.skills_line(cat.get('brainsCfg')) + rs._foot.note('pos', cat.get('psFolders')) + rs._recall(cat, 'Code', text)   # 🧰 the kits it was told to use reach the build itself, not only the plan
            for k, i in enumerate(order):
                doc['stage'] = 'review' if k else 'build'; rs._ws_save(cat_id, {**doc, 'busy': {'at': round(rs.time.time()), 'to': to, 'stage': doc['stage'], 'spent': round(cost, 6)}})
                def part_(raw_, usd_, by_=name(i)):
                    rs._ws_save(cat_id, {**doc, 'busy': {'at': round(rs.time.time()), 'to': to, 'stage': doc['stage'], 'spent': round(cost + usd_, 6), 'by': by_, 'draft': rs.re.sub(r'```(?:html)?', '', raw_)[:rs.WS_DRAFT_CHARS]}})
                raw, usd, own, html = '', 0.0, paid_own, None
                if rs._feat.wants_rewrite(cur, text):
                    raw, usd, own = await rs._ws_page(cat, brains[i], (rs._feat.REVIEW_SYS if k else rs._feat.BUILD_SYS) + rs._feat._sources.proof_line('pos') + read_ + kits_, user if not k else f'{text}\nThe page:\n{cur[:40000]}', 16000 if doc.get('ad') else 8000, on_part=part_)
                    cost += usd; paid_own = own; html = rs._aip.html_of(raw)
                if (not html or not rs._feat.page_complete(html)) and not cur and not k:   # 🧩 no page yet and the whole page did not fit in a reply: build it in sections
                    html_s_, usd_s_, own_s_, n_s_ = await rs._ws_sections(cat, [brains[j] for j in order], text, read_ + kits_); cost += usd_s_; paid_own = paid_own or own_s_
                    if html_s_:
                        html = html_s_; rs._feat.add_msg(doc, name(i), f"The whole page did not fit in one reply, so it was built in {n_s_} sections" + (f" shared by {' and '.join(name(j) for j in order)}." if len(order) > 1 else '.'), rs.time.time())
                if (not html or not rs._feat.page_complete(html)) and cur and not region and rs._feat.wants_restyle(text):   # 🎨 a new LOOK on a page too big to write whole: one CSS block that wins, never patches that must match by the letter
                    css_raw_, css_usd_, css_own_ = await rs._ws_ask(cat, brains[i], rs._feat.RESTYLE_SYS + kits_, rs._feat.restyle_prompt(text, cur), 3200)
                    cost += css_usd_; paid_own = css_own_; styled_ = rs._feat.add_css(cur, css_raw_)
                    html = styled_ if styled_ != cur else None
                if (not html or not rs._feat.page_complete(html)) and cur:
                    html, landed_, said_ = cur, 0, ''
                    for _ in range(3):   # small exact changes against the whole page, until it says nothing is left
                        patch_raw, patch_usd, patch_own = await rs._ws_ask(cat, brains[i], rs._feat.EDIT_SYS + kits_, f"Owner request: {text[:1200]}{rs._feat.region_note(region)}" + (f'\nStill left from your last reply: {said_}' if said_ else '') + f'\nCurrent page:\n{html[:rs._feat.PAGE_PROMPT_CHARS]}', 1300)
                        cost += patch_usd; paid_own = patch_own
                        next_, n_, said_ = rs._feat.apply_page_edits(html, patch_raw)
                        if not next_:
                            break
                        html, landed_ = next_, landed_ + n_
                        if not said_:
                            break
                    html = html if landed_ else None
                    stop_why = 'Its changes did not match the page. Mark the part to change with +, or say "rebuild" to have it write the whole page new.' if not landed_ else stop_why
                if html and not rs._feat.page_complete(html):
                    rs._feat.add_msg(doc, name(i), 'That answer was cut off before the page finished, so it was not kept.', rs.time.time())
                    stop_why = 'Its answer was cut off before the page finished.'
                elif html:
                    faults_ = rs._feat.page_faults(html)
                    if faults_['cutCss'] or len(faults_['classes']) >= 3:   # 🩹 it ended properly but lost styling: one small repair, not a whole new page
                        css_, fix_usd_, paid_own = await rs._ws_ask(cat, brains[i], rs._feat.REPAIR_SYS, rs._feat.repair_prompt(html, faults_), 3000); cost += fix_usd_; html = rs._feat.add_css(html, css_)
                    html = rs._kits.open_for_kits(rs._kits.with_kit_tags(html, picks_), picks_); doc['kitsUsed'] = rs._kits.kit_report(html, picks_); doc['kitsOutside'] = rs._kits.outside_files(html, picks_)
                    cur = html; rs._feat.add_version(doc, html, name(i), rs.time.time()); rs._parts_used(cat_id, ws_id, html); rs._feat.add_msg(doc, name(i), f'Page {len(doc["versions"])} is ready. Open Static to try it.', rs.time.time())
                else:
                    stop_why = stop_why or 'Its answer held no page.'
                    rs._feat.add_msg(doc, name(i), f'{stop_why} Nothing changed, and the last page is safe.', rs.time.time())
                rs._ws_save(cat_id, {**doc, 'busy': {'at': round(rs.time.time()), 'to': to, 'stage': doc['stage'], 'spent': round(cost, 6)}})
        else:
            sys_ = (rs._feat.CONTENT_SYS if kind == 'content' else rs._feat.RESEARCH_SYS) + ' ' + rs._feat.ANSWER_SHAPES.get(kind, '')
            past = '\n'.join(f"{m['by']}: {m['text'][:400]}" for m in (doc.get('messages') or [])[-6:-1]) + (rs._feat.live_line(await rs._live_feed(cat)) if rs._feat.wants_live(text) else '')
            t0_ = (doc.get('busy') or {}).get('at') or round(rs.time.time())
            for j_, i in enumerate(order):   # ⏳ the bar shows the real step (which mind, how many answered, since the job began); each save carries the answers so far, so A's shows while B works
                rs._ws_save(cat_id, {**doc, 'busy': {'at': t0_, 'to': to, 'stage': 'answer', 'by': name(i), 'step': j_, 'steps': len(order), 'spent': round(cost, 6)}})
                raw, usd, own = await rs._ws_ask(cat, brains[i], sys_, f'{past}\nThe owner asks: {text}', 700)
                cost += usd; paid_own = own; rs._feat.add_msg(doc, name(i), raw or 'No answer came back.', rs.time.time())
            if kind == 'content' and rs._assets.wants_3d(text):
                rs._feat.add_msg(doc, 'FEELESS', 'This is the idea in words. To build it for real, send the same prompt to a PoStatic folder: it builds in the 3D studio with real models, light and surfaces. For a video, use Video and image editor, then 3D.', rs.time.time())
    except Exception as e:   # noqa: BLE001 — it says so in the folder
        rs._feat.add_msg(doc, 'FEELESS', f'A model did not answer ({str(e)[:80]}). Nothing was lost.', rs.time.time())
        stop_why = 'A model did not answer.'
    doc['busy'] = None; doc['cost'] = round(float(doc.get('cost') or 0) + cost, 6); doc['lastCost'] = round(cost, 6)
    if kind == 'build' and len(doc.get('versions') or []) > start_versions:
        doc['stage'] = 'filed'; doc.pop('unfinished', None)
    elif kind == 'build' and doc.get('stage') != 'approve':
        doc['unfinished'] = {'ask': text[:3000], 'why': stop_why or 'It stopped before saving a new page.', 'region': region, 'at': round(rs.time.time())}
    rs._ws_save(cat_id, doc)
    built = kind == 'build' and len(doc.get('versions') or []) > start_versions
    if built:
        doc['pending'] = False; rs._ws_save(cat_id, doc)
    if built or (cost and not paid_own):
        rs._WS_DONE.append({'cat': cat_id, 'cost': cost, 'own': paid_own, 'doc': rs.json.loads(rs.json.dumps(doc)) if built else None}); rs._POW_WAKE.set()


def _poc_media(doc):
    """🎬 The finished images / videos of a PoC folder's chat, light enough to live on its filed proof. Pure."""
    out = []
    for m in (doc or {}).get('messages') or []:
        md = m.get('media') or {}
        if md.get('status') == 'done' and md.get('url'):
            out.append({'id': md.get('id'), 'kind': md.get('kind'), 'url': md.get('url'), 'label': md.get('label'), 'prompt': str(md.get('prompt') or '')[:200]})
    return out[:8]


def _poc_view(cat):
    rs = _rs()
    rows = []
    for f in (cat.get('pocFolders') or [])[::-1]:
        if f.get('ws') and 'media' not in f:
            hit = rs._POC_MEDIA_SEEN.get(f['ws'])
            if hit is None or rs.time.time() - hit[0] > 300:
                hit = (rs.time.time(), rs._poc_media(rs._ws_load(cat.get('id'), f['ws']) or {})); rs._POC_MEDIA_SEEN[f['ws']] = hit
            if hit[1]:
                f = {**f, 'media': hit[1]}
        rows.append({**f, 'stamp': rs._stamp.of('PoC', f, rs.time.time())})
    return rows


async def _week_file(cat_id, ws, topic):
    """🗓 Each mind writes one WHOLE week in a different style (launch / drip / hype), all three at once; each plan files as its own PoC proof
    (paper, graded like any other). Nothing is posted. A style a mind fumbles is skipped and said, never invented."""
    rs = _rs()
    try:
        cat = rs._load()['cats'].get(cat_id) or {}; brains = rs._lc.minds_for(cat.get('brainsCfg'), 'poc') or []
        if not brains:
            return
        rs._CALL_CTX.set({'kind': 'poc', 'ref': ws, 'minds': brains})
        media_ = rs._poc_media(rs._ws_load(cat_id, ws) or {}); ids_ = [m['id'] for m in media_]

        async def one(i, style):
            sys_, user_ = rs._wk.prompt(style[0], topic, media_)
            try:
                raw, usd, own = await rs.asyncio.wait_for(rs._ws_ask(cat, brains[i % len(brains)], sys_, user_, 1400), 240)
            except Exception as e:   # noqa: BLE001: one mind down never stops the other weeks
                return i, style, None, 0.0, False, f'{type(e).__name__}'
            try:
                return i, style, rs._wk.parse(raw, ids_), usd, own, None
            except ValueError as e:
                return i, style, None, usd, own, str(e)
        got = await rs.asyncio.gather(*(one(i, st) for i, st in enumerate(rs._wk.STYLES)))
        store = rs._load(); c_ = store['cats'].get(cat_id)
        if not c_:
            return
        rows = list(c_.get('pocFolders') or []); filed = []; cost = 0.0; paid_own = False
        for i, (key, name, _how), plan, usd, own, why in got:
            cost += usd or 0; paid_own = paid_own or own
            if not plan:
                print(f'[week] {cat_id} {key}: {why}'); continue
            rows.append({'id': f'poc{int(rs.time.time())}{i}', 'ws': ws, 'n': rs._next_n(rows), 'kind': 'PoC', 'at': round(rs.time.time()), 'status': 'closed', 'paper': True,
                         'topic': f'Week plan · {name}' + (f' · {topic}' if topic else ''), 'week': {**plan, 'style': key},
                         'calls': [{'mind': i, 'name': str(brains[i % len(brains)]).split('/')[-1][:24], 'angle': name, 'post': plan['idea'] or f"{len(plan['posts'])} posts", 'why': f"{len(plan['posts'])} posts over the week"}],
                         'cost': round(usd or 0, 5), **({'media': media_} if media_ else {})})
            filed.append(name)
        c_['pocFolders'] = rows[-60:]
        say_ = f"🗓 {len(filed)} week plan{'s' if len(filed) != 1 else ''} filed as PoCs ({', '.join(filed)}). Nothing was posted." if filed else '🗓 No week plan came back usable. Try again.'
        c_['chat'] = (list(c_.get('chat') or []) + [{'by': 'cats', 'text': say_, 'at': rs.time.time(), 'open': 'features'}])[-200:]
        if cost and not paid_own and c_.get('brainsCfg'):
            rs._lc.charge(c_['brainsCfg'], cost)
        rs._save(store)
    except Exception as e:   # noqa: BLE001
        print(f'[week] {cat_id}: {str(e)[:140]}')
    finally:
        rs._WEEK_BUSY.discard(cat_id)


async def _poc_file(cat_id, topic, ws=None):
    """📣 PROOF OF CONTENT: its PoI is what was trending when it decided. Each mind proposes blind; the owner marks how it did. Nothing is posted by this."""
    rs = _rs()
    try:
        async with rs.httpx.AsyncClient(timeout=10, follow_redirects=True) as http:
            tr = (await rs._tools.trending(http)).get('trends') or {}
        cat = rs._load()['cats'].get(cat_id) or {}; brains = rs._lc.minds_for(cat.get('brainsCfg'), 'poc'); cost = 0.0; paid_own = False; calls = []
        pid_ = f'poc{int(rs.time.time())}'; rs._CALL_CTX.set({'kind': 'poc', 'ref': ws or pid_, 'minds': brains})   # 🧾 its own task: the context ends with it
        lines = '\n'.join(f'{k}: ' + '; '.join(v[:5]) for k, v in tr.items() if v)
        notes = '; '.join(str(c.get('text') or '')[:120] for c in ((cat.get('brainsCfg') or {}).get('cloud') or [])[-6:])
        read_, sites_read_ = await rs._site_reads('poc', (cat['id'], cat.get('name')))
        async def one(i, m):
            return i, await rs._ws_ask(cat, m, rs._feat.POC_SYS.format(name='Mind ' + 'AB'[i]) + rs._foot.note('poc', cat.get('pocFolders'), i) + rs._feat._sources.proof_line('poc') + read_ + rs._recall(cat, 'Content', topic) + rs._know.for_ask(topic) + rs._foot.note('poc', cat.get('pocFolders'), i), f'The owner wants: {topic or "whatever fits them best right now"}\nTheir notes: {notes}\nTrending now:\n{lines}', 260)
        for i, (raw, usd, own) in await rs.asyncio.gather(*(one(i, m) for i, m in enumerate(brains))):
            cost += usd; paid_own = own
            try:
                d_ = rs.json.loads(rs.re.search(r'\{.*\}', raw, rs.re.S).group(0))
            except (AttributeError, ValueError):
                d_ = {'post': raw[:240]}
            calls.append({'mind': i, 'name': str(brains[i]).split('/')[-1][:24], **{k: str(d_.get(k) or '')[:300] for k in ('angle', 'post', 'why', 'trend')}})
        shots_ = []
        words_ = rs._marks.words_of([x for v in tr.values() for x in (v or [])[:3]] + [topic or ''])
        for n_, r_ in enumerate(await rs._fb.shots(['https://news.ycombinator.com/', 'https://news.google.com/', 'https://en.wikipedia.org/wiki/Main_Page'], words_, rs.time.time())):   # 🖍 what it found, snapshotted free, with what it read boxed
            try:
                d_ = rs.POWSHOTS_DIR / rs.re.sub(r'[^a-z0-9]', '', pid_); d_.mkdir(parents=True, exist_ok=True); name_ = f"{rs.re.sub(r'[^a-z0-9]', '', r_['site'])[:30]}_{n_}.jpg"; (d_ / name_).write_bytes(r_['jpg'])
                shots_.append({'site': r_['site'], 'url': r_['url'], 'title': r_['title'], 'file': name_, 'at': round(rs.time.time()), 'found': list(r_['found'])[:12], 'missing': r_['missing'][:12], 'sha': r_['sha']})
            except OSError as e:
                print(f'[poc] snapshot not kept: {e}')
        store = rs._load(); c_ = store['cats'].get(cat_id)
        if c_:
            rows = list(c_.get('pocFolders') or [])
            rows.append({'id': pid_, 'kits': rs._KIT_LAST.get((cat_id, 'poc')) or [], **({'ws': ws} if ws else {}), 'shots': shots_, 'sitesRead': sites_read_, 'n': rs._next_n(rows), 'kind': 'PoC', 'at': round(rs.time.time()), 'status': 'closed', 'paper': True, 'topic': topic or 'best fit now', 'trends': {k: v[:5] for k, v in tr.items()}, 'calls': calls, 'cost': round(cost, 5)})
            c_['pocFolders'] = rows[-60:]
            c_['chat'] = (list(c_.get('chat') or []) + [{'by': 'cats', 'text': f"📣 PoC #{len(rows)} is filed: {len(calls)} ideas from what is trending. Nothing was posted.", 'at': rs.time.time(), 'open': 'features'}])[-200:]
            if cost and not paid_own and c_.get('brainsCfg'):
                rs._lc.charge(c_['brainsCfg'], cost)
            rs._save(store)
    except Exception as e:   # noqa: BLE001
        print(f'[poc] {cat_id}: {str(e)[:140]}')
    finally:
        rs._POC_BUSY.discard(cat_id)


@router.get('/api/cats/tools/indicator/{ind}')
async def cat_indicator(ind: str):
    """📈 One of our own indicators as a file. Plain Pine v5, written by FEELESS, free to use."""
    rs = _rs()
    row = rs._edge.INDICATORS.get(ind)
    if not row:
        raise rs.HTTPException(404, 'No such indicator.')
    return rs.Response(content=row[1], media_type='text/plain; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="feeless-{ind}.pine"', 'X-Content-Type-Options': 'nosniff'})


@router.get('/api/cats/pool/rules')
async def pool_rules():
    """🪙 Public: the live split rules a user sees before sending, and the Pool's totals. Never a wallet or an owner."""
    rs = _rs()
    st = rs._cpool.load(rs.POOL_PATH); t = rs._cpool.totals(st, await rs._pool_px())
    px_ = await rs._pool_px(); wt_ = sum(rs._cpool._working_usd(a_, px_, rs.time.time()) * rs._cpool.levers(st['cfg'], a_.get('boost'))['weightX'] for a_ in st['agents'].values())
    return {'rules': {**rs._cpool.rules(st['cfg']), 'score': rs._stake.rung(st, px_), 'live': {'potDayUsd': round(t['usd']['pot'] * st['cfg']['potPayDayPct'] / 100, 4), 'weight': round(wt_, 4)}}, 'potUsd': t['usd']['pot'], 'lockedUsd': t['usd']['locked'], 'agents': t['agents'], 'ratePerSecUsd': t['ratePerSecUsd'], 'withdrawals': False}


@router.get('/api/cats/pool/project')
async def pool_project(usd: float = 10.0, plan: str = 'month', boost: float = 0.0, feesDay: float = 0.0, othersUsd: float = 0.0):
    """🧮 What one send does, day by day, at the fees and members the viewer picks. Runs the real pool code on a throwaway state; saves nothing."""
    rs = _rs()
    st = rs._cpool.load(rs.POOL_PATH)
    return await rs.asyncio.to_thread(rs._cpool.project, st['cfg'], usd, plan, boost, feesDay, othersUsd)


@router.get('/api/cats/pool/growth')
async def pool_growth(send: float = 20.0, plan: str = 'month', volume: float = 100.0, senders: float = 100.0, cfg: str = ''):
    """🌱 Where an agent comes out as FEELESS grows. `cfg` = the owner's unsaved settings, so HQ previews them. Saves nothing."""
    rs = _rs()
    st = rs._cpool.load(rs.POOL_PATH); over = {}
    try:
        over = rs.json.loads(cfg) if cfg else {}
    except ValueError:
        over = {}
    use = {**st['cfg'], **(over if isinstance(over, dict) else {})}
    return await rs.asyncio.to_thread(rs._cpool.growth, use, send, plan, volume, senders)


@router.get('/api/cats/collective/mine')
async def collective_mine(session: str = ''):
    """👑 The owner's side of the Collective: its agents' running result, boosts, what it put in and how much a boost is worth now. Only its own."""
    rs = _rs()
    me = rs._fresh_session_wallet(session)
    if not me:
        raise rs.HTTPException(401, 'Sign in with your wallet.')
    store = rs._load(); now = rs.time.time(); shares = rs._shares(); pst = rs._cpool.load(rs.POOL_PATH); mode = pst['cfg']['boostMode']; px = await rs._pool_px()
    out = []
    for c in store['cats'].values():
        if rs.owner_wallet(c) != me or c.get('isLeader'):
            continue
        real = sorted([f for f in c.get('powFolders') or [] if f.get('real') and f.get('pnlSol') is not None], key=lambda f: rs._num(f.get('soldAt') or f.get('at')))
        run, series = 0.0, []
        for f in real[-60:]:
            run = round(run + rs._num(f.get('pnlSol')), 6); series.append({'at': round(rs._num(f.get('soldAt') or f.get('at'))), 'v': run, 'sym': f.get('sym'), 'pct': f.get('pnlPct')})
        mine = [x for x in shares if x.get('cat') == c['id']]; pts = rs._cl.boost_total(c); pr = rs._print.build(c, now)
        hits = [rs._cl.qualifies(f) for f in real]
        out.append({'id': c['id'], 'name': c.get('name'), 'face': c.get('face'), 'series': series, 'boosts': pts, 'weight': rs._cpool.levers(pst['cfg'], rs._cpool.boost_of(c.get('boosts'), rs._print.strength(c, now), now, pst['cfg']['boostFadeDays']))['weightX'], 'strength': rs._print.strength(c, now), 'pool': rs._cpool.view(pst, c['id'], now, px), 'boostLog': (c.get('boosts') or [])[-8:][::-1], 'owedSol': round(sum(rs._num(x.get('sol')) for x in mine if not x.get('sent')), 6), 'sentSol': round(sum(rs._num(x.get('sol')) for x in mine if x.get('sent')), 6),
                    'bigWins': sum(hits), 'trades': len(real), 'auto': bool((c.get('colonyShare') or {}).get('auto') and (c.get('colonyShare') or {}).get('on')), 'pct': (c.get('colonyShare') or {}).get('pct'), 'convo': bool((c.get('convo') or {}).get('on')), 'print': rs._print.public(pr), 'strongest': [t['t'] for t in pr['traits'] if t['score'] > 0][:3], 'weakest': [t['t'] for t in pr['traits'][::-1] if t['score'] < 0][:3]})
    return {'agents': out, 'mode': mode}


def _convos_public(store):
    return [{k: c.get(k) for k in ('id', 'aName', 'bName', 'a', 'b', 'at', 'lines', 'brought', 'joint', 'entry', 'dueAt', 'stamp')} for c in (store.get('convos') or [])[-20:]][::-1]


@router.get('/api/cats/receipt/{sig}/explorer')
async def cat_receipt_explorer(sig: str):
    """🖼 The picture of the send on Solana's explorer, with what proves it boxed. Public: the transaction is public too."""
    rs = _rs()
    f_ = rs.RECEIPTS_DIR / f"{rs.re.sub(r'[^A-Za-z0-9]', '', str(sig))[:90]}.tx.jpg"
    if not f_.exists():
        raise rs.HTTPException(404, 'No picture yet.')
    return rs.Response(f_.read_bytes(), media_type='image/jpeg')


@router.get('/api/cats/proofs/value')
async def proofs_value():
    """💵📌 COL-20 P3, public: verified missions per dollar (settled proofs only, counts and $ only) and the newest daily chain tip of the proof
    record, checked against the record now. Rebuilt at most every 10 minutes."""
    rs = _rs()
    if rs._VALUE['v'] is None or rs._VALUE['at'] < rs.time.time() - 600:
        store = rs._load(); ws_ = {(k, f.get('id')): f.get('ws') for c in store['cats'].values() for k, (_c, key) in rs._mission.KINDS.items() for f in c.get(key) or [] if f.get('ws')}
        rows_ = await rs.asyncio.to_thread(rs._pev.rows, rs.DATA_DIR / rs._pev.DB_NAME)
        rs._VALUE['v'] = {**rs._review.per_dollar(rows_, rs._call_tally(), ws_), 'anchor': await rs.asyncio.to_thread(rs._pev.anchor_check, rs.DATA_DIR / rs._pev.DB_NAME, rs.DATA_DIR / rs._pev.ANCHORS)}
        rs._VALUE['at'] = rs.time.time()
    return rs._VALUE['v']


@router.get('/api/cats/stash/web')
async def stash_web():
    """🧊 Public: how much the Collective's private record holds and where it routes. Counts only: no site names and never its contents. The owner's own map has the names."""
    rs = _rs()
    st_ = await rs.asyncio.to_thread(rs._stash.stats, rs.STASH_DIR); w_ = await rs.asyncio.to_thread(rs._stash.web_public, rs.STASH_DIR)
    return {'stats': {k: st_[k] for k in ('items', 'categories', 'outcomes', 'agents', 'sources', 'lastDay')}, 'web': w_}


def _web_live_rows(store, now, private_ok=False):
    """🔥 Who is working right now, and where on the webs it lands. Names an agent and a site's feature, never a page. A private or incognito agent shows only to the creator."""
    rs = _rs()
    rows = []; host_f = rs._feat._sources.sources_web()['hostFeature']
    for c in store['cats'].values():
        if c.get('revoked') or ((c.get('handle') == 'sicarios' or c.get('incognito')) and not private_ok):
            continue
        name = c.get('name') or 'An agent'
        for w in ((rs._WORK.get(c.get('id')) or {}).get('task') or {}).get('windows') or []:
            if w.get('status') == 'running':
                h = rs._feat._sources._host(str(w.get('url') or '').split('://')[-1])
                rows.append({'agent': name, 'mind': w.get('i'), 'does': str(w.get('bubble') or w.get('goal') or 'working')[:60], 'host': h if h in host_f else None, 'feature': host_f.get(h)})
        for key, kind in (('powRun', 'pow'), ('popRun', 'pop'), ('pobRun', 'pob')):
            run = c.get(key)
            if run and (run.get('folder') if key == 'powRun' else True):   # a powRun stays on the agent between proofs; only one with a folder is working
                rows.append({'agent': name, 'does': f'running a {kind[:2].capitalize()}{kind[2:].upper()}', 'folder': rs._feat._sources.KIND_FOLDER[kind]})
        if c.get('id') in rs._POC_BUSY:
            rows.append({'agent': name, 'does': 'filing a PoC', 'folder': 'Content'})
        for w_ in c.get('workspaces') or []:
            if w_.get('busy'):
                rows.append({'agent': name, 'does': f"coding {str(w_.get('name') or '')[:30]}", 'folder': 'Code' if w_.get('kind') == 'build' else 'Content' if w_.get('kind') == 'content' else 'Research'})
    return rows[:24]


@router.get('/api/cats/sources/print')
async def cat_sources_print():
    """🧬 Which kinds of source win, weighed, from real graded proofs. No site names, no titles. Public."""
    rs = _rs()
    if rs.time.time() - rs._SOURCE_PRINT['at'] > 300:
        rs._SOURCE_PRINT['rows'] = await rs.asyncio.to_thread(rs._cg.source_print, rs.STASH_DIR, rs._feat._sources.sources_web()['hostFeature']); rs._SOURCE_PRINT['at'] = rs.time.time()
    return {'rows': rs._SOURCE_PRINT['rows']}


@router.get('/api/cats/sources/web')
async def cat_sources_web():
    """🕸 What the Collective's sources offer, as folders and features. No site names."""
    rs = _rs()
    w_ = rs._feat._sources.sources_web(); w_.pop('hostFeature')
    return w_


@router.get('/api/cats/receipt/{sig}')
async def cat_receipt(sig: str):
    """🧾 A send's snapshot, read back from the chain when it was verified. Public: the transaction is public too."""
    rs = _rs()
    f_ = rs._receipt_path(sig)
    if not f_.exists():
        raise rs.HTTPException(404, 'No receipt.')
    return rs.Response(content=f_.read_bytes(), media_type='image/jpeg', headers={'Cache-Control': 'public, max-age=86400'})


def _atoms_public(store, pool_ids, now):
    """⚛ The real proofs on the public print, and only what is safe to show: its kind, rank, result and age. No agent, coin, site, words or real id, so nothing here can be copied. Active means working now, in the Pool, or filed in the last day. Pure on what it is given."""
    rs = _rs()
    saved = rs._weights.load(rs.DATA_DIR); rows = []
    for cid, c in (store.get('cats') or {}).items():
        if c.get('incognito') or c.get('revoked'):
            continue
        for k, key in rs._PROOF_KEYS.items():
            for f in c.get(key) or []:
                if not (isinstance(f, dict) and f.get('id')) or f.get('noTrade'):
                    continue
                at = rs._num(f.get('at')); pnl = f.get('pnlPct'); graded = f.get('graded'); working = f.get('status') not in ('closed', 'filed', None)
                result = 'open' if working else 'won' if (graded == 'right' or (pnl is not None and rs._num(pnl) > 0)) else 'lost' if (graded == 'wrong' or (pnl is not None and rs._num(pnl) < 0)) else 'filed'
                try:
                    rank = (rs._proof_view(c, k, f, 300.0, saved) or {}).get('rank')
                except Exception:   # noqa: BLE001 — one odd proof never empties the print
                    rank = None
                rows.append({'id': rs.hashlib.sha256(f"atom:{cid}:{f['id']}".encode()).hexdigest()[:14], 'kind': {'pow': 'PoW', 'pop': 'PoP', 'pob': 'PoB', 'poc': 'PoC', 'pos': 'PoStatic'}.get(rs._weights.kind_of(k) or str(k), 'Proof'), 'rank': rank, 'result': result, 'age': max(0, int((now - at) // 86400)) if at else 0, 'active': bool(working or f['id'] in pool_ids or (at and now - at < rs.ATOM_ACTIVE_S))})
    return rows[-400:]


def _short_model(m):
    return str(m or '').split('/')[-1].split(':')[0].lower()


def model_prints(store):
    """🧬 Every model our agents really used, scored from its own record (owner 2026-11-07: "every ai model used gets a fingerprint score").
    Work = proofs it called + trading calls; hit = graded right vs wrong (+1/+2 smoothing, so one lucky proof is not 100); breadth = kinds it has done.
    A PoW / PoStatic names its seat, not its model: the seat's model is the agent's current one. → [{id, name, score, n, right, wrong, kinds}] best first. Pure."""
    rs = _rs()
    rows = {}; every = {rs._short_model(m): m for c in (store.get('cats') or {}).values() for m in (c.get('brainsCfg') or {}).get('brains') or []}
    def add(full, kind, graded=None):
        full = every.get(rs._short_model(full), full)
        key = rs._short_model(full)
        if not key:
            return
        r = rows.setdefault(key, {'id': full, 'name': key, 'n': 0, 'right': 0, 'wrong': 0, 'kinds': set()})
        if '/' in str(full) and '/' not in str(r['id']):
            r['id'] = full
        r['n'] += 1; r['kinds'].add(kind); r['right'] += graded == 'right'; r['wrong'] += graded == 'wrong'
    for c in (store.get('cats') or {}).values():
        brains = list((c.get('brainsCfg') or {}).get('brains') or []); full = {rs._short_model(m): m for m in brains}
        seat = lambda i: brains[i] if 0 <= i < len(brains) else None   # noqa: E731
        for k, key in rs._PROOF_KEYS.items():
            for f in c.get(key) or []:
                if not isinstance(f, dict):
                    continue
                g = f.get('graded') or ('right' if rs._num(f.get('pnlPct') or 0) > 0 else 'wrong' if rs._num(f.get('pnlPct') or 0) < 0 else None)
                if f.get('calls'):
                    for x in f['calls']:
                        if isinstance(x, dict) and x.get('name'):
                            add(seat(int(x.get('mind') or 0)) if str(x['name']).startswith('Mind ') else full.get(rs._short_model(x['name']), x['name']), k, g)
                elif k == 'pos' and str(f.get('by') or '').startswith('Mind'):
                    add(seat('AB'.find(str(f['by'])[-1])), k, g)
                elif k == 'pow':
                    for i in (f.get('picks') or {}):
                        add(seat(int(i)) if str(i).isdigit() else None, k, g)
        for d in (c.get('brainsCfg') or {}).get('decisions') or []:
            if isinstance(d, dict) and d.get('by') and d.get('word') not in ('RULES', None):
                add(full.get(rs._short_model(d['by']), d['by']), 'trade')
    out = []
    for r in rows.values():
        hit = (r['right'] + 1) / (r['right'] + r['wrong'] + 2)
        out.append({**r, 'kinds': sorted(r['kinds']), 'score': round(100 * (0.45 * hit + 0.30 * min(1, r['n'] / 25) + 0.25 * len(r['kinds']) / 6))})
    return sorted(out, key=lambda x: -x['score'])[:40]


@router.get('/api/cats/assets/thumb/{uid}')
async def asset_thumb(uid: str):
    """🖼 An Objaverse model's picture in the 3D studio search (they came with none, so 43,000 tiles were black). Public, cached, no key: it only points at Sketchfab's own image."""
    rs = _rs()
    from fastapi.responses import RedirectResponse, Response
    async with rs.httpx.AsyncClient(timeout=12) as h_:
        url = await rs._assets.sketchfab_thumb(h_, rs.KITS_DIR, uid)
    return RedirectResponse(url, status_code=302, headers={'Cache-Control': 'public, max-age=86400'}) if url else Response(status_code=404, headers={'Cache-Control': 'public, max-age=3600'})


@router.get('/api/cats/models/prints')
async def cat_model_prints():
    """🧬 The models our agents used, each with its fingerprint score. Only the model picker shows it."""
    rs = _rs()
    now = rs.time.time()
    if now - rs._PRINTS['at'] > rs.ATOMS_FRESH_S:
        rs._PRINTS['rows'] = await rs.asyncio.to_thread(rs.model_prints, rs._load()); rs._PRINTS['at'] = now
    return {'models': rs._PRINTS['rows']}


@router.get('/api/cats/collective/atoms')
async def collective_atoms():
    """⚛ Public: the real proofs on the Collective's print, basic facts only. Worked out once every 2 minutes."""
    rs = _rs()
    now = rs.time.time()
    if now - rs._ATOMS['at'] > rs.ATOMS_FRESH_S:
        st = rs._cpool.load(rs.POOL_PATH); ids = {r.get('proofId') for a in (st.get('agents') or {}).values() for r in a.get('streams') or [] if r.get('proofId')}
        rs._ATOMS['rows'] = await rs.asyncio.to_thread(rs._atoms_public, rs._load(), ids, now); rs._ATOMS['at'] = now
    return {'proofs': rs._ATOMS['rows']}


@router.get('/api/cats/collective/kalshi')
async def collective_kalshi():
    """🌐 Public: the minds' record on settled real Kalshi bids and their after-payout notes. No agent, coin, ticker or stash."""
    rs = _rs()
    now = rs.time.time()
    if now - rs._KB_PUBLIC['at'] > rs.ATOMS_FRESH_S:
        rs._KB_PUBLIC['v'] = rs._kb.public_board(list((rs._load().get('cats') or {}).values())); rs._KB_PUBLIC['at'] = now
    return rs._KB_PUBLIC['v']


@router.get('/api/cats/collective/look')
async def collective_look():
    """🎨 The colors the owner picked for the Collective."""
    rs = _rs()
    try:
        return rs.json.loads((rs.DATA_DIR / 'collective_look.json').read_text())
    except (OSError, ValueError):
        return {'theme': 'NEBULA', 'glow': 70}


@router.get('/api/cats/tools/logos/{sport}')
async def cat_tool_team_logos(sport: str):
    """🛡 A league's team logos for the PoB filing cards: {team name: ESPN logo url}. Public read, one league, cached a day."""
    rs = _rs()
    if sport not in rs._tools.SPORTS:
        raise rs.HTTPException(404, 'No such sport.')
    async with rs.httpx.AsyncClient(timeout=10, follow_redirects=True) as http:
        return {'sport': sport, 'label': rs._tools.SPORTS[sport][0], 'logos': await rs._tools.team_logos(http, sport)}


@router.get('/api/cats/tools/sources/{kind}')
async def cat_tool_proof_sources(kind: str):
    """🗂 A proof's sites, best first: the Stash's real results move them once a site has 5 graded proofs."""
    rs = _rs()
    return {'rows': rs._feat._sources.ranked(kind, await rs.asyncio.to_thread(rs._stash.trust_rows, rs.STASH_DIR, rs._feat._sources.STASH_CAT.get(kind)))}


@router.get('/api/cats/tools/team/{sport}/{tid}')
async def cat_tool_team(sport: str, tid: str):
    """🏟 A team's season averages and every player's. Free, from ESPN."""
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=12) as h:
        d = await rs._tools.team_sheet(h, sport, tid)
    if not d:
        raise rs.HTTPException(404, 'This team could not be read.')
    return d


@router.get('/api/cats/tools/athlete/{sport}/{aid}')
async def cat_tool_athlete(sport: str, aid: str):
    """🏟 One player: season, career, last 5 games. Free, from ESPN."""
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=12) as h:
        d = await rs._tools.athlete_sheet(h, sport, aid)
    if not d:
        raise rs.HTTPException(404, 'This player could not be read.')
    return d


@router.get('/api/cats/tools/print/{what}/{sport}/{xid}')
async def cat_tool_print(what: str, sport: str, xid: str):
    """🧬 A team's or a player's stats, this season against last. Free, from ESPN. Its fingerprint draws from this."""
    rs = _rs()
    if what not in ('team', 'player'):
        raise rs.HTTPException(404, 'Teams and players only.')
    async with rs.httpx.AsyncClient(timeout=8, follow_redirects=True) as http:
        got = await (rs._tools.team_print if what == 'team' else rs._tools.player_print)(http, sport, xid)
    if not got:
        raise rs.HTTPException(404, 'ESPN has no stats for this yet.')
    return got


@router.get('/api/cats/tools/game/{sport}/{gid}')
async def cat_tool_game(sport: str, gid: str, a: str = '', b: str = ''):
    """🏟 One game: records, how often each side wins, form, team stats, top players, injuries, the win chance over the game. Free: ESPN first, with fallbacks."""
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=8, follow_redirects=True) as http:
        got = await rs._tools.game_detail(http, sport, gid, (a, b))
    if not got:
        raise rs.HTTPException(404, 'This game could not be read.')
    return got


@router.get('/api/cats/tools/{kind}')
async def cat_tools(kind: str, sport: str = 'all', team: str = ''):
    """🧰 A proof folder's dash: live rows from its top 5 free sources. Read-only and public: nothing here is anyone's."""
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=10, follow_redirects=True) as http:
        if kind == 'bids':
            return await rs._tools.bids(http, sport, team[:40])
        if kind == 'pow':
            return await rs._tools.pow_tool(http)
        if kind == 'pop':
            return await rs._tools.pop_tool(http)
        if kind == 'content':
            return await rs._tools.trending(http)
        if kind == 'book':
            return await rs._tools.book(http, sport)
        if kind == 'indicators':
            return await rs._tools.indicators(http, team)
    raise rs.HTTPException(404, 'No such dash.')


async def _pob_grade_pass(http, store, now):
    """🏈 A PoB on real games stays live: its scores update, and when every game is final it is graded from the scoreboard. An owner's own mark is never overwritten."""
    rs = _rs()
    if now - float(store.get('pobGradeAt') or 0) < 300:
        return
    store['pobGradeAt'] = now
    try:
        await rs._kalshi_settle_pass(http, store, now)
    except Exception as e:   # noqa: BLE001 — the scoreboard pass still runs
        print(f'[kalshi] settle: {str(e)[:100]}')
    for c_ in store['cats'].values():   # 🧹 repeated score lines leave the chat (owner 2026-11-15: 5 copies of one score)
        if c_.get('chat'):
            kept_ = rs._pob.dedupe_scores(c_['chat'])
            if len(kept_) != len(c_['chat']):
                c_['chat'] = kept_
        for f_ in (c_.get('pobFolders') or [])[-6:]:   # 💵 a short-index warning is read again, so it clears once he moves the money
            tk_ = f_.get('kalshi') or {}
            if tk_.get('idxWarn') and tk_.get('status') == 'waiting':
                tk_.pop('idxWarn', None); await rs._kalshi_index_warn(c_, tk_)
    open_ = [f for c in store['cats'].values() for f in (c.get('pobFolders') or [])[-20:] if f.get('games') and f.get('gradedBy') not in rs._stamp.OUTSIDE]   # 🔒 a hand mark never stops the scoreboard
    owner_of = {id(f): c for c in store['cats'].values() for f in (c.get('pobFolders') or [])[-20:]}
    for sport in {g.get('sport') for f in open_ for g in f['games'] if g.get('sport')}:
        board = (await rs._tools.sport_board(http, sport)).get('games') or []
        for f in open_:
            if any(g.get('sport') == sport for g in f['games']):
                f['games'], grade = rs._tools.grade_games(f['games'], board)
                if grade:
                    if f.get('graded') in ('right', 'wrong') and not f.get('gradedBy'):
                        f.setdefault('ownerMark', f['graded'])   # the hand mark from before the results stays, as a note
                    f['graded'], f['gradedBy'] = grade, 'scoreboard'
                for g_ in f['games']:   # 🏀 once a quarter or period, the score lands in its chat
                    per_ = rs._pob.period_of(g_.get('status'))   # '8:41 - 1st' / 'End of 1st' → '1st' (it took the clock, so it posted on every pass)
                    if g_.get('state') == 'in' and per_ and g_.get('said') != per_:
                        g_['said'] = per_; c_ = owner_of.get(id(f))
                        key_ = f"{g_.get('id')}:{per_}"; said_ = c_.setdefault('scoreSaid', []) if c_ is not None else []
                        if c_ is not None and key_ not in said_:   # one line per game per period, however many readings share that game (owner 2026-11-15: 5 copies)
                            c_['scoreSaid'] = (said_ + [key_])[-60:]
                            c_['chat'] = (list(c_.get('chat') or []) + [{'by': 'cats', 'text': f"🏟 {g_.get('name') or g_.get('side') or 'Its game'}: {g_.get('score')} · {g_.get('status')}. From your PoB on {str(f.get('topic') or '')[:50]}.", 'at': now, 'open': 'bids'}])[-200:]
    for f in [x for c in store['cats'].values() for x in (c.get('pobFolders') or [])[-20:] if x.get('poly') and x.get('gradedBy') not in rs._stamp.OUTSIDE]:   # 🗳 graded when the market itself settles
        ev = await rs._tools._get(http, f"https://gamma-api.polymarket.com/events/{f['poly'].get('id')}")
        won = rs._tools.poly_winner(ev)
        if won:
            picks = ' '.join(str(p.get('pick') if isinstance(p, dict) else p) for c_ in f.get('calls') or [] for p in c_.get('picks') or []).lower()
            f['poly']['winner'] = won
            if picks:
                if f.get('graded') in ('right', 'wrong') and not f.get('gradedBy'):
                    f.setdefault('ownerMark', f['graded'])
                f['graded'], f['gradedBy'] = ('right' if won.lower() in picks else 'wrong'), 'polymarket'


@router.get('/api/cats/colony/flow')
async def colony_flow(limit: int = 40):
    """💸 THE COLONY'S MONEY, LIVE (owner 2026-11-02: crawlnet's treasury --flow, FEELESS's own): PoW trades in → profit / loss → the shares
    winning agents owe the colony → the colony pot (its live on-chain balance) → the airdrop; and the LEDGER — every real trade an agent's own
    wallet made (side · coin · SOL · tx) + every share accrued. Incognito agents are left out; nothing an owner typed."""
    rs = _rs()
    store = rs._load(); now = rs.time.time(); cfg = rs._colony_cfg(); cats = [c for c in store['cats'].values() if not c.get('incognito') and not c.get('revoked')]
    folders = [f for c in cats for f in c.get('powFolders') or []]
    real = [f for f in folders if f.get('real') and f.get('entry')]
    in_sol = round(sum(rs._num(f.get('sol')) for f in real), 6); pnl = round(sum(rs._num(f.get('pnlSol')) for f in real), 6)
    shares = rs._shares(); owed = round(sum(rs._num(x.get('sol')) for x in shares if not x.get('sent')), 6)
    pot_addr = await rs._pot_balance(now)
    names = {c['id']: str(c.get('name') or 'agent')[:24] for c in cats}
    rows = [{'at': int(t.get('at') or 0), 'kind': t.get('side'), 'agent': names[c['id']], 'sym': t.get('symbol'), 'sol': rs._num(t.get('sol')), 'sig': t.get('sig'),
             'memo': 'PoW ' + str(t.get('side')) if any(f.get('mint') == t.get('mint') for f in c.get('powFolders') or []) else str(t.get('side'))}
            for c in cats for t in c.get('agentTx') or [] if t.get('sig') and t.get('status') == 'success']
    for r in rows:   # a sell's record has no SOL back: its folder's size + P/L at the pool price (said so on the row)
        if r['kind'] == 'sell' and not r['sol']:
            f_ = next((f for c in cats if names[c['id']] == r['agent'] for f in c.get('powFolders') or [] if f.get('real') and f.get('sym') == r['sym'] and f.get('pnlSol') is not None), None)
            if f_:
                r.update(sol=round(rs._num(f_.get('sol')) + rs._num(f_.get('pnlSol')), 6), memo=r['memo'] + ' · ≈ pool price')
    rows += [{'at': int(x.get('at') or 0), 'kind': 'share', 'agent': names.get(x.get('cat'), 'agent'), 'sym': x.get('sym'), 'sol': rs._num(x.get('sol')), 'sig': x.get('sig'),
              'proof': x.get('proof'), 'reason': x.get('reason'), 'memo': 'sent to the pot' if x.get('gift') else f"{x.get('pct')}% of a win to the pot" + ('' if x.get('sent') else ' · owed')} for x in shares if x.get('cat') in names]
    rows.sort(key=lambda r: -r['at'])
    ep = rs._hv.epoch_of(now); board = rs._hv.board(rs._hive_cells(), ep)
    return rs._pub({'pow': {'folders': len(folders), 'trades': len(real), 'inSol': in_sol, 'won': sum(1 for f in real if rs._num(f.get('pnlSol')) > 0)},
                 'pnlSol': pnl, 'shares': {'owedSol': owed, 'count': len(shares), 'sharing': sum(1 for c in cats if (c.get('colonyShare') or {}).get('on'))},
                 'pot': {'address': pot_addr, 'sol': rs._FLOW_POT['sol']}, 'epoch': {'n': ep, 'left': rs._hv.epoch_left(now), 'honey': sum(int(r.get('honey') or 0) for r in board), 'agents': len(board)},
                 'airdrop': {'next': cfg.get('nextAirdrop'), 'cadence': cfg.get('cadence'), 'paidSol': round(sum(rs._num(x.get('sol')) for x in shares if x.get('sent') and not x.get('gift')), 6)},
                 'poolNow': {**rs._cpool.totals(rs._cpool.load(rs.POOL_PATH), await rs._pool_px()), 'stakedUsd': rs._stake.totals(rs._cpool.load(rs.POOL_PATH), await rs._pool_px())['stakedUsd'], 'head': rs._cpool.load(rs.POOL_PATH).get('head'), 'links': rs._cpool.load(rs.POOL_PATH).get('links'), 'seeds': {c['id']: rs._cpool.print_seed(c['id']) for c in cats[:400]}},
                 'proofs': rs._cl.proof_feed(cats, shares, now, 20), 'convos': rs._convos_public(store),
                 'sentSol': round(sum(rs._num(x.get('sol')) for x in shares if x.get('gift')), 6),
                 'rivals': rs._kalshi_rivals(cats),
                 'agents': len(cats), 'colonized': sum(1 for c in cats if rs._hive_on(c)), 'tree': rs._flow_tree(cats, shares, board), 'ledger': rows[:max(1, min(100, int(limit)))]})


def _owner_boosts(store):
    rs = _rs()
    out = {}
    for c in store['cats'].values():
        w_ = rs.owner_wallet(c)
        if w_:
            out[w_] = out.get(w_, 0) + rs._cl.boost_total(c)
    return out


@router.get('/api/cats/internal/colony')
async def cat_colony_internal(request: Request):
    """🐝 For the owner's colony pot (reputation, internal key): the epoch board, who owns each colonized agent (the payout allowlist),
    how many are colonized, and which browsers this server can use — names only, never a key."""
    rs = _rs()
    if not rs._internal_ok(request):
        raise rs.HTTPException(403, 'Internal only.')
    store = rs._load(); cells = rs._hive_cells(); now = rs.time.time(); ep = rs._hv.epoch_of(now)
    names = {k: c.get('name') for k, c in store['cats'].items()}
    on_ = [c for c in store['cats'].values() if rs._hive_on(c)]
    return {'epoch': ep, 'left': rs._hv.epoch_left(now), 'board': rs._hv.board(cells, ep, names), 'colonized': len(on_),
            'owners': {c['id']: rs.owner_wallet(c) for c in on_ if rs.owner_wallet(c) and not c.get('ownerStaff') and not c.get('isLeader')},
            'trades': sum(1 for c in cells if c.get('kind') and rs._hv.epoch_of(c.get('at') or 0) == ep), 'browsers': rs._cb.chain(rs.os.environ),
            'sharers': sorted({rs.owner_wallet(c) for c in store['cats'].values() if (c.get('colonyShare') or {}).get('on') and rs.owner_wallet(c)}),
            'shares': [x for x in rs._shares() if not x.get('sent')][-2000:], 'sentShares': [x for x in rs._shares() if x.get('sent')][-2000:],
            'boosts': rs._owner_boosts(store)}


@router.post('/api/cats/internal/supply')
async def internal_supply_set(request: Request):
    """🎟 The owner opens slots (from the command center, proxied with the internal key): 0 … SUPPLY_MAX, never below what is taken."""
    rs = _rs()
    rs._internal(request)
    body = await request.json()
    store = rs._load(); now_ = rs.supply_state(store)
    try:
        want = int((body or {}).get('open'))
    except (TypeError, ValueError):
        raise rs.HTTPException(400, 'open must be a whole number')
    want = max(now_['taken'], min(rs.SUPPLY_MAX, want))
    (rs.DATA_DIR / rs.SUPPLY_FILE).write_text(rs.json.dumps({'open': want, 'at': rs.time.time(), 'by': str((body or {}).get('by') or '')[:44]}))
    return rs.supply_state(store)


@router.get('/api/cats/internal/studio')
async def internal_studio_get(request: Request):
    rs = _rs()
    rs._internal(request)
    return rs.studio_view(rs._load()['cats'][rs.LEADER_ID])


@router.post('/api/cats/internal/studio')
async def internal_studio_set(request: Request):
    rs = _rs()
    rs._internal(request)
    body = await request.json()
    store = rs._load()
    out = rs.studio_set(store['cats'][rs.LEADER_ID], body if isinstance(body, dict) else {}, (body or {}).get('by'))
    rs._save(store)
    return out


@router.get('/api/cats/internal/rules')
async def internal_rules_get(request: Request):
    rs = _rs()
    rs._internal(request)
    store = rs._load()
    return {'rules': {k: rs.RULES[k] for k in rs.TUNABLE}, 'bounds': rs.TUNABLE, 'overrides': store.get('rulesOverride') or {}, 'strategyPreset': store.get('strategyPreset', 'feecat'),
            'leader': {k: store['cats'][rs.LEADER_ID].get(k) for k in ('status', 'risk')},
            'agentLane': store['cats'][rs.LEADER_ID].get('agentLane') or {}, 'agentLimits': rs._POOL_META.get('limits') or {}}


@router.post('/api/cats/internal/rules')
async def internal_rules_set(request: Request):
    rs = _rs()
    rs._internal(request)
    body = await request.json()
    store = rs._load()
    ov = store.setdefault('rulesOverride', {})
    for k, v in (body.get('rules') or {}).items():
        if k in rs.TUNABLE:
            lo, hi = rs.TUNABLE[k]
            ov[k] = type(rs.RULES[k])(max(lo, min(hi, float(v))))
    leader = store['cats'][rs.LEADER_ID]
    if body.get('status') in ('running', 'paused'):
        leader['status'] = body['status']
    if body.get('maxPositionSol') is not None:
        leader['risk']['maxPositionSol'] = max(0.1, min(10.0, float(body['maxPositionSol'])))
    if body.get('resetLearning'):
        leader.pop('learn', None)
    if isinstance(body.get('agentLane'), dict):   # 🐱🤖 her own tuning on top of the agents' band (empty = follow the agents)
        leader['agentLane'] = rs.clean_lane(body['agentLane'])
    if body.get('strategyPreset') in ('feecat', 'trench', 'meme', 'scalper', 'fast'):   # ⚡ fast = the one dial (agents' configs)
        store['strategyPreset'] = body['strategyPreset']
    rs._apply_overrides(store)
    rs._save(store)
    return {'ok': True, 'rules': {k: rs.RULES[k] for k in rs.TUNABLE}, 'status': leader['status']}


def _internal_headers():
    rs = _rs()
    try:
        return {'x-feeless-internal': (rs.DATA_DIR / 'internal.key').read_text().strip()}
    except OSError:
        return {}


def _internal_ok(request):
    """True when the request carries FEELESS's internal key (service to service, never a browser)."""
    rs = _rs()
    try:
        rs._internal(request); return True
    except rs.HTTPException:
        return False


def _internal(request):
    rs = _rs()
    import hmac
    try:
        key = (rs.DATA_DIR / 'internal.key').read_text().strip()
    except OSError:
        key = ''
    if not key or not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), key):
        raise rs.HTTPException(403, 'Internal only.')


def _challenge_note(cat_id, site, result):
    """Count outcomes without storing challenge tokens, URLs, cookies or private browser frames."""
    rs = _rs()
    if not site or result not in ('timedOut', 'manualPass'):
        return
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        return
    stats = cat.setdefault('challengeStats', {}).setdefault(site, {'timedOut': 0, 'manualPass': 0})
    stats[result] = int(stats.get(result) or 0) + 1
    stats['lastAt'] = round(rs.time.time())
    rs.keep_owned(cat); rs._save(store)


def _poi_owner_view(cat_id):
    rs = _rs()
    try:
        return rs._poi.owner_view(rs.DATA_DIR, cat_id)
    except (OSError, ValueError) as e:
        return {'v': rs._poi.VERSION, 'error': f'Research DNA integrity check failed: {str(e)[:80]}'}


async def _keep_pass(cat_id, page, url):
    """🍪 A bot check a person passed → that site's clearance cookies, cleaned (first-party, newest, no trackers) and sealed into its sign-ins.
    Its next windows start with them (LivePage cookies). A clearance can still be refused from another IP — then the 30 s move-on applies."""
    rs = _rs()
    try:
        site_ = rs._cv.site_of(url or page.url)
        ctx_, st_ = rs._cb.clean_context(await page.site_context(url), site_)
        if not ctx_.get('cookies'):
            return False
        store = rs._load(); cat = store['cats'].get(cat_id)
        if not cat:
            return False
        cat.setdefault('siteSessions', {})[site_] = {'ctx': rs._ck.seal(rs.json.dumps(ctx_), cat_id), 'at': rs.time.time(), 'n': st_['kept'], 'dropped': st_['dropped'], 'kind': 'pass'}
        rs.vault_log(cat, 'kept a bot-check pass', site_); rs.keep_owned(cat); rs._save(store)
        rs._src_note(site_, True)
        return True
    except Exception as e:   # noqa: BLE001 — keeping a pass never breaks the task
        print(f'[pass] {cat_id}: {str(e)[:100]}')
        return False


def _site_ctx(cat):
    """Every sign-in the owner saved for this agent → one Steel session context (None when there are none)."""
    rs = _rs()
    out = []
    for site_, v in (cat.get('siteSessions') or {}).items():
        try:
            out.append(rs._cb.clean_context(rs.json.loads(rs._ck.unseal(v['ctx'], cat.get('id'), data_dir=rs.DATA_DIR)), site_)[0])   # 🧼 cleaned on every load too
        except Exception:
            continue
    return rs._cb.merge_contexts(out)


def file_interrupted(cat, now=None):
    """🛟 The task that was running when the service stopped → its parked list (▶ resume / ✕ drop), so the owner's ask is never silently lost."""
    rs = _rs()
    n_ = cat.pop('workNow', None)
    if not n_ or not n_.get('text'):
        return False
    if any(m.get('by') == 'cats' and float(m.get('at') or 0) > float(n_.get('at') or 0) for m in cat.get('chat') or []):   # it already answered — nothing was cut off
        return False
    cat['workParked'] = (list(cat.get('workParked') or []) + [{'at': now or rs.time.time(), 'text': n_['text'], 'why': 'the agent service restarted while it worked — press ▶ to run it again'}])[-rs.HANDOFF_MAX:]
    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': '⏸ The agent service restarted while I worked on this — it is filed under ⏸; press ▶ to run it again.', 'at': now or rs.time.time()}])[-40:]
    return True


def heal_site_sessions(cat):
    """🧼 Every stored sign-in re-cut to its site's own, newest, unexpired cookies and re-sealed. → True when one changed."""
    rs = _rs()
    changed = False
    for site_, v in list((cat.get('siteSessions') or {}).items()):
        try:
            raw_ = rs.json.loads(rs._ck.unseal(v['ctx'], cat.get('id'), data_dir=rs.DATA_DIR))
        except Exception:
            cat['siteSessions'].pop(site_, None); changed = True   # unreadable / tampered → gone (sign in again)
            continue
        ctx_, st_ = rs._cb.clean_context(raw_, site_)
        if st_['dropped'] or v.get('n') != st_['kept']:
            if not ctx_['cookies'] and not ctx_['localStorage']:
                cat['siteSessions'].pop(site_, None)
            else:
                cat['siteSessions'][site_] = {**v, 'ctx': rs._ck.seal(rs.json.dumps(ctx_), cat['id']), 'n': st_['kept'], 'dropped': (v.get('dropped') or 0) + st_['dropped'], 'cleanAt': rs.time.time()}
            changed = True
    return changed


async def _seal_downloads(cat_id, session_id, page, site=''):
    """🔏 Files the owner downloaded in a window they used (a recovery PDF…) → sealed in its drawer, then deleted from the cloud browser. → how many."""
    rs = _rs()
    names = getattr(getattr(page, 'downloads', None), 'names', None) or {}
    try:
        async with rs.httpx.AsyncClient(timeout=30) as http:
            got = await rs._cb.collect_downloads(http, rs.os.environ, session_id, names)
    except (rs.httpx.HTTPError, ValueError) as exc:
        print(f'[vault] {cat_id}: download listing unavailable ({type(exc).__name__})')
        return 0  # A transient Steel file-list failure must not discard the owner's saved sign-in.
    if not got:
        return 0
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        return 0
    for name, data in got:
        try:
            rs._cv.put_secret(cat, f"{name} · from {site}" if site else name, data=data, name=name, site=site, data_dir=rs.DATA_DIR)
            rs.vault_log(cat, 'sealed', site or name)
        except ValueError as e:
            print(f'[vault] {cat_id}: {str(e)[:80]}')
    rs.keep_owned(cat); rs._save(store)
    return len(got)


def _warm_for(cat_id, site=None, now=None):
    rs = _rs()
    w_ = rs._WARM.get(cat_id)
    if not w_ or (now or rs.time.time()) - w_['at'] > rs.WARM_S or (site and w_['site'] != site):
        return None
    return w_


async def _warm_close(cat_id):
    rs = _rs()
    w_ = rs._WARM.pop(cat_id, None)
    if w_:
        async with rs.httpx.AsyncClient(timeout=15) as http:
            await rs._cb.close_session(http, rs.os.environ, {'provider': 'steel', 'id': w_['sid']})


async def _warm_expire(now):
    rs = _rs()
    for cid_ in [c for c, w_ in rs._WARM.items() if now - w_['at'] > rs.WARM_S and not w_.get('busy')]:
        await rs._warm_close(cid_)


async def _signin_close(cat_id):
    rs = _rs()
    si_ = rs._SIGNIN.pop(cat_id, None)
    if not si_:
        return
    try:
        if si_.get('page'):
            await si_['page'].close()
    except Exception:
        pass
    async with rs.httpx.AsyncClient(timeout=15) as http:
        await rs._cb.close_session(http, rs.os.environ, {'provider': 'steel', 'id': si_['sid']})


def _auto_cfg(cat, cat_id):
    rs = _rs()
    raw = cat.get('autoRun')
    if not raw:
        return None
    try:
        return rs.json.loads(rs._ck.unseal(raw, cat_id, data_dir=rs.DATA_DIR))
    except Exception:   # noqa: BLE001 — a config that will not open never runs
        return None


def _auto_put(cat, cat_id, cfg):
    rs = _rs()
    if cfg is None:
        cat.pop('autoRun', None)
    else:
        cat['autoRun'] = rs._ck.seal(rs.json.dumps(cfg), cat_id)


def _auto_busy(cat, cat_id, kind):
    rs = _rs()
    k = rs._AUTO_RUNKEY.get(kind)
    if k and (cat.get(k) or (kind == 'pob' and cat.get('pobRead'))):
        return True
    return (kind == 'poc' and cat_id in rs._POC_BUSY) or cat_id in rs._POW_WANT or cat_id in rs._POP_WANT or cat_id in rs._POB_WANT


def _auto_chat(cat, cat_id, text):
    """→ what to say when the line is an auto command or the answer to the auto setup, else None (the line goes on as usual)."""
    rs = _rs()
    now = rs.time.time(); cmd = rs._aa.command(text); pend = cat.get('autoAsk')
    if cmd and cmd[0] == 'stop':
        cfg = rs._auto_cfg(cat, cat_id); cat.pop('autoAsk', None)
        if not cfg or not cfg.get('on'):
            return '🛑 No auto run is on for this agent. Nothing will run.'
        rs._auto_put(cat, cat_id, rs._aa.kill(cfg, now)); return f"🛑 Kill-switch: auto {rs._aa.KINDS[cfg['kind']]} is OFF. Nothing else will run until you set it again."
    if cmd and cmd[0] == 'status':
        cfg = rs._auto_cfg(cat, cat_id)
        if not cfg:
            return 'No auto run set. Type `auto pob` (or pow · pop · poc · pos · poeco) to set one up.'
        return (('🟢 ON · ' if cfg.get('on') else f"⚪ OFF ({cfg.get('stopped') or 'stopped'}) · ") + rs._aa.summary(cfg, now))
    if cmd and cmd[0] == 'auto':
        if not (cat.get('brainsCfg') or {}).get('brains'):
            return 'Give this agent its models first: an auto run uses them for every proof.'
        cur = rs._auto_cfg(cat, cat_id)
        if cur and cur.get('on'):
            return f"An auto {rs._aa.KINDS[cur['kind']]} run is already ON ({rs._aa.summary(cur, now)}). Say `stop auto` first."
        pend, say = rs._aa.start(cmd[1], now); cat['autoAsk'] = pend; return say
    if pend:
        pend2, cfg, say = rs._aa.answer(pend, text, now)
        if pend2:
            cat['autoAsk'] = pend2
        else:
            cat.pop('autoAsk', None)
        if cfg:
            rs._auto_put(cat, cat_id, cfg); rs._POW_WAKE.set()
        return say
    return None


async def _auto_fire(cat_id, cfg):
    """One scheduled proof, through the owner's own chat path (same guards, same wallet signature for any real buy)."""
    rs = _rs()
    return await rs._cat_work(cat_id, rs.WorkPayload(op='ask', text=cfg['line'], session=rs._AUTO_TOKEN, auto=True))


async def _auto_tick(now=None):
    """Every agent with an auto run ON: book the fire against its bounds FIRST (sealed), then fire it. → fired cat ids."""
    rs = _rs()
    if not rs.SELF_START:   # 🛑 scheduled auto runs are self-started usage: discontinued (owner 2026-11-14)
        return []
    now = now or rs.time.time(); out = []
    store = rs._load()
    for cid, c in list((store.get('cats') or {}).items()):
        cfg = rs._auto_cfg(c, cid)
        if not cfg or not cfg.get('on'):
            continue
        ok, why = rs._aa.due(cfg, now, busy=rs._auto_busy(c, cid, cfg['kind']))
        if not ok:
            if why not in ('waiting', 'the last one is still running'):
                rs._auto_put(c, cid, rs._aa.kill(cfg, now, why)); rs._save(store)
            continue
        rs._auto_put(c, cid, rs._aa.fired(cfg, now)); rs._save(store)
        try:
            await rs._auto_fire(cid, cfg); out.append(cid)
        except rs.HTTPException as e:   # it could not file (no credit, a model missing…): say so in its chat, the run stays booked
            s2 = rs._load(); c2 = s2['cats'].get(cid)
            if c2:
                c2['chat'] = (list(c2.get('chat') or []) + [{'by': 'cats', 'text': f"🤖 Auto {rs._aa.KINDS[cfg['kind']]} could not file: {e.detail}", 'at': rs.time.time()}])[-200:]
                rs.keep_owned(c2); rs._save(s2)
        store = rs._load()
    return out


async def _auto_loop():
    rs = _rs()
    await rs.asyncio.sleep(60)
    while True:
        try:
            await rs._auto_tick()
        except Exception:   # noqa: BLE001 — the next tick tries again
            pass
        await rs.asyncio.sleep(rs.AUTO_TICK_S)


async def _week_post(cat_id, cat, p, base_, key_):
    """📮 postiz_channels / week_post after the key check (owner only, one send at a time per agent)."""
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=30, follow_redirects=False) as h_:
        try:
            chans_ = await rs._pz.channels(h_, base_, key_)
        except (ValueError, rs.httpx.HTTPError) as e:
            raise rs.HTTPException(502, str(e) if isinstance(e, ValueError) else 'Postiz did not answer.')
        if p.op == 'postiz_channels':
            return {'channels': [{'id': c.get('id'), 'name': str(c.get('name') or '')[:60], 'platform': c.get('identifier'), 'picture': c.get('picture'), 'off': bool(c.get('disabled'))} for c in chans_ if isinstance(c, dict)]}
        rows_ = cat.get('pocFolders') or []; f_ = next((x for x in rows_ if x.get('id') == str(p.job or '') and x.get('week')), None)
        if not f_:
            raise rs.HTTPException(404, 'No such week plan.')
        t_ = p.tools if isinstance(p.tools, dict) else {}; mode_ = 'draft' if t_.get('mode') == 'draft' else 'schedule'
        if (f_.get('posted') or {}).get('sent') and not t_.get('again'):
            raise rs.HTTPException(409, 'This week already went to Postiz. Change it there, or send it again on purpose.')
        try:
            start_ = rs.dt.date.fromisoformat(str(t_.get('start') or '')) if t_.get('start') else rs._pz.next_monday(rs.dt.datetime.now(rs.dt.timezone.utc).date())
            if start_.weekday() != 0:
                raise ValueError
            tz_ = max(-840, min(840, int(t_.get('tz') or 0)))
        except (ValueError, TypeError):
            raise rs.HTTPException(400, 'Pick the Monday the week starts.')
        files_ = {m.get('id'): m for m in f_.get('media') or []}

        def path_(post_):
            m_ = files_.get(post_.get('media')) or {}; nm_ = str(m_.get('url') or '').rsplit('/', 1)[-1]
            fp_ = rs._media_dir() / cat_id / nm_
            return fp_ if nm_ and rs.re.fullmatch(r'[\w-]+\.(png|jpe?g|webp|mp4|webm)', nm_) and fp_.is_file() else None
        go_, skip_ = rs._pz.plan(f_['week']['posts'], chans_, start_, tz_, rs.dt.datetime.now(rs.dt.timezone.utc), lambda q: bool(path_(q)))
        if not go_:
            raise rs.HTTPException(400, 'Nothing can go out: ' + '; '.join(f'{pl} ({why})' for _i, pl, why in skip_[:4]) + '.')
        ups_ = {}; out_ = []
        for i_, post_, ch_, utc_ in go_:
            res_ = {'i': i_, 'platform': post_['platform'], 'channel': str(ch_.get('name') or '')[:60], 'date': utc_.isoformat()}
            try:
                fp_ = path_(post_); med_ = None
                if fp_:
                    if fp_.name not in ups_:
                        ext_ = fp_.suffix[1:].lower(); ct_ = ('video/' if ext_ in ('mp4', 'webm') else 'image/') + ('jpeg' if ext_ == 'jpg' else ext_)
                        ups_[fp_.name] = await rs._pz.upload(h_, base_, key_, fp_.name, fp_.read_bytes(), ct_)
                    med_ = ups_[fp_.name]
                res_['postId'] = await rs._pz.create(h_, base_, key_, rs._pz.body(post_, ch_, utc_, mode_, med_))
            except (ValueError, rs.httpx.HTTPError) as e:
                res_['error'] = str(e)[:160] if isinstance(e, ValueError) else 'Postiz did not answer.'
            out_.append(res_)
    sent_ = sum(1 for r in out_ if r.get('postId') is not None and not r.get('error'))
    store = rs._load(); cat = store['cats'].get(cat_id) or cat; f_ = next((x for x in cat.get('pocFolders') or [] if x.get('id') == str(p.job)), None)
    if f_ is not None:
        f_['posted'] = {'at': round(rs.time.time()), 'mode': mode_, 'start': start_.isoformat(), 'sent': sent_, 'results': out_,
                        'skipped': [{'i': i, 'platform': pl, 'why': why} for i, pl, why in skip_]}
    word_ = 'left as drafts' if mode_ == 'draft' else 'scheduled'
    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"📮 {sent_} of {len(f_['week']['posts']) if f_ else sent_} posts {word_} in Postiz for the week of {start_.isoformat()}" + (f", {len(skip_)} skipped" if skip_ else '') + '.', 'at': rs.time.time(), 'open': 'features'}])[-200:]
    rs.keep_owned(cat); rs._save(store)
    return {'pocFolders': rs._poc_view(cat), 'posted': f_.get('posted') if f_ else None}


@router.post('/api/cats/{cat_id}/work')
async def cat_work(cat_id: str, p: _RSM.WorkPayload):
    """🫂 Every workbench answer passes the Collective rule on its way out (_for_users)."""
    rs = _rs()
    out = await rs._cat_work(cat_id, p)
    return rs._for_users((rs._load()['cats'].get(cat_id) or {}), out) if isinstance(out, (dict, list)) else out


def _desk_focus(cat, win, pid, now):
    """A proof picked on the main desk → the deskProof the chat talks to (proof_commands.focus + its id). Raises 400 / 404."""
    rs = _rs()
    kind = rs._PICK_KIND.get(str(win or ''))
    if not kind:
        raise rs.HTTPException(400, 'That kind of proof opens in its folder on the Desktop.')
    pid = str(pid or '')[:60]
    rows = [f for f in (cat.get(rs._PROOF_KEYS[kind]) or []) if isinstance(f, dict)] + ([cat['popFolder']] if kind == 'pop' and isinstance(cat.get('popFolder'), dict) else [])
    f = next((x for x in rows if str(x.get('id')) == pid), None)
    if not f:
        raise rs.HTTPException(404, 'That proof is not in its files any more.')
    name = str(f.get('topic') or (f'${f["sym"]}' if f.get('sym') else '') or f.get('name') or f.get('title') or '').strip()[:80]
    desk = rs._pc.focus({'kind': kind, 'name': name}, now, f.get('ws') if kind == 'pos' else None)
    return {**desk, 'id': pid}


async def _cat_work(cat_id: str, p: _RSM.WorkPayload):
    """🧠🧠 A general cat's workbench (the cat's OWNER only): ask · state · continue / stop (a human-needed window) · stop · cap ($ per task)."""
    rs = _rs()
    store = rs._load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Cat not found.')
    internal_ = bool(p.session) and rs.secrets.compare_digest(str(p.session), rs._AUTO_TOKEN)   # 🤖 only the auto loop in THIS process holds it
    if not internal_:
        p.auto = False
        rs._owner_gate(store, cat, p.session, p.ownerId)
    if rs._sicario_paused(cat) and p.op in rs.SICARIO_PAUSE_OPS and p.on is not False:
        raise rs.HTTPException(409, "Sicario's only works when you ask it, so it never loads your machines by itself. This one stays off.")
    b = cat.get('brainsCfg') or {}
    w = rs._WORK.get(cat_id)
    if p.op == 'tools':
        if w and not w.get('done'):
            raise rs.HTTPException(409, 'Stop the current task before changing its tools.')
        try:
            cat['tools'] = rs._cp.toolkit(p.job or cat.get('job', 'agent'), p.tools)
            cat['job'] = p.job or cat.get('job', 'agent')
        except ValueError as exc:
            raise rs.HTTPException(400, str(exc))
        rs._save(store)
    if p.op == 'desk_focus':   # 🎯 the MAIN desk's proof picker (owner 2026-11-15: "proof picker suppose to open on main desk as its to work in main desk and not desktop folders")
        desk_ = rs._desk_focus(cat, p.job, p.text, rs.time.time())
        cat['deskProof'] = desk_; cat.pop('proofNote', None)
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"🎯 {desk_['label']} \"{desk_['name']}\" is on the desk. Your words go to it.", 'at': rs.time.time(), 'open': desk_['open']}])[-200:]
        rs.keep_owned(cat); rs._save(store)
        return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
    if p.op == 'approvals':   # ✅ AGX-10: its Approve inbox
        return {'approvals': rs._appr.view(cat)}
    if p.op == 'approve':   # ✅ the owner's tap: only now does a usage-spending row run (text = row id, job = 'yes' | 'no')
        if internal_:
            raise rs.HTTPException(403, 'Only its owner approves usage.')
        try:
            row_ = rs._appr.decide(cat, str(p.text or ''), p.job == 'yes')
        except KeyError:
            raise rs.HTTPException(404, 'Nothing like that is waiting.')
        except ValueError as e:
            raise rs.HTTPException(409, str(e))
        rs.keep_owned(cat); rs._save(store)
        if row_['state'] == 'approved':
            try:
                await rs._cat_work(cat_id, p.model_copy(update={**row_['op'], 'finish': False, 'i': None}))
                ok_, say_ = True, 'Started: it lands in its folder.'
            except rs.HTTPException as e:
                ok_, say_ = False, str(e.detail)
            store = rs._load(); cat = store['cats'].get(cat_id) or cat
            r_ = next((r for r in cat.get('approvals') or [] if r.get('id') == row_['id']), None)
            if r_ is not None:
                rs._appr.finish(r_, ok_, say_); rs.keep_owned(cat); rs._save(store); row_ = r_
        return {'approvals': rs._appr.view(cat), 'row': row_}
    if p.op == 'incognito':   # 🕶 hide its screens from visitors — $5 once per agent from its own model credit (staff free), then on / off any time
        if p.on and not cat.get('incognitoPaid') and not (cat.get('ownerStaff') or await rs._session_staff(p.session or '')):
            if float(b.get('credit') or 0) - rs._lc.CREDIT_RESERVE < rs.INCOGNITO_USD:
                raise rs.HTTPException(402, f'Incognito is ${rs.INCOGNITO_USD:g} once, from its model credit — add credit in its wallet panel first.')
            b['credit'] = round(float(b.get('credit') or 0) - rs.INCOGNITO_USD, 6)
            cat['incognitoPaid'] = {'at': rs.time.time(), 'usd': rs.INCOGNITO_USD}
        elif p.on and not cat.get('incognitoPaid'):
            cat['incognitoPaid'] = {'at': rs.time.time(), 'usd': 0.0, 'staff': True}
        cat['incognito'] = bool(p.on)
        rs.keep_owned(cat); rs._save(store)
        return {'incognito': cat['incognito'], 'paid': cat.get('incognitoPaid'), 'credit': b.get('credit')}
    if p.op in ('ws_build', 'ask', 'poc', 'pob', 'pop') and str(p.text or '').strip():   # 🧵 one conversation across every proof type
        cat.setdefault('brainsCfg', {})['voice'] = rs._vm.learn((cat.get('brainsCfg') or {}).get('voice'), p.text)   # 🪞 how its owner writes, learned from every message
        kind_c_ = {'ws_build': {'build': 'PoStatic', 'content': 'PoC', 'research': 'Research'}.get(next((w.get('kind') for w in cat.get('workspaces') or [] if w.get('id') == p.job), ''), 'Folder'), 'ask': 'Chat', 'poc': 'PoC', 'pob': 'PoB', 'pop': 'PoP'}[p.op]
        rs._play_save(cat_id, 'convo', rs._foot.convo_add(rs._play_load(cat_id, 'convo'), kind_c_, p.text, rs.time.time()))
    if p.op == 'pop':   # 📉 the PoP desk's buttons: the engine pass does the work
        if p.job == 'adopt_alt':   # 💡 run the other mind's call instead
            card_ = cat.get('popCard') or {}; alt_ = card_.get('alt')
            if not alt_:
                raise rs.HTTPException(409, 'That proposal has one call.')
            card_.update({k: v for k, v in alt_.items() if k in ('market', 'side', 'lev', 'tp', 'sl', 'why', 'entry')}); card_.update(mark=alt_.get('entry'), alt=None); rs.keep_owned(cat); rs._save(store); p.job = 'adopt'
        if p.job not in ('start', 'stop', 'propose', 'adopt', 'pass'):
            raise rs.HTTPException(400, 'Not a PoP action.')
        ok_, say_ = rs._pop.reply(p.job, cat.get('popRun'), cat.get('popCard'))
        if not ok_:
            raise rs.HTTPException(409, say_)
        if p.job == 'start' and (room_ := rs._proof_room(cat, cat_id, 'PoP')):
            raise rs.HTTPException(409, room_)
        cat.pop('proofSite', None)
        rs._POP_WANT[cat_id] = p.job; rs._POW_WAKE.set()
        return {'ok': True}
    if p.op in ('mail_make', 'mail_read'):   # 📧 its own mailbox, from the desktop
        box_ = cat.get('mailbox') or {}
        async with rs.httpx.AsyncClient(timeout=20) as http:
            try:
                if p.op == 'mail_make':
                    if box_.get('address'):
                        raise ValueError(f"It already has {box_['address']}.")
                    made_ = await rs._am.make(http, cat_id)
                    fresh_ = rs._load(); now_ = fresh_['cats'][cat_id]
                    rs._cv.put_login(now_, rs._am.SITE, made_['address'], made_['password'], data_dir=rs.DATA_DIR)
                    now_['mailbox'] = {'address': made_['address'], 'at': round(rs.time.time())}
                    rs.vault_log(now_, 'made its mailbox', rs._am.SITE); rs.keep_owned(now_); rs._save(fresh_)
                    return {'mailbox': now_['mailbox'], 'logins': rs._cv.public_logins(now_), 'mail': []}
                if not box_.get('address'):
                    raise ValueError('It has no mailbox yet.')
                return {'mail': await rs._am.inbox(http, box_['address'], rs._cv.reveal(cat, rs._am.SITE, box_['address'], data_dir=rs.DATA_DIR))}
            except (ValueError, rs.httpx.HTTPError) as e:
                raise rs.HTTPException(400, str(e)[:160] or 'mail.tm did not answer.')
    if p.op == 'setup':   # 🚀 Priority Setup: an answer, or just how many are left
        if p.job and p.job != 'view':
            try:
                rs._as.apply(cat, p.job, str(p.text or ''), rs.time.time())
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs.keep_owned(cat); rs._save(store)
        return {'setup': rs._as.view(cat)}
    if p.op == 'site_trade':   # 🛒 the card's buttons: the same door as typing yes or no
        say_ = await rs._site_trade_chat(cat_id, None, {'yes': p.job == 'yes'})
        store = rs._load(); cat = store['cats'][cat_id]
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': say_, 'at': rs.time.time()}])[-200:]
        rs.keep_owned(cat); rs._save(store)
        return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:], 'siteTrade': cat.get('siteTrade')}
    if p.op == 'site_trade_auto':   # 🛒 On its own = its typed orders run without the question. Every guard and cap stays
        cat['siteTradeAuto'] = bool(p.on); rs.keep_owned(cat); rs._save(store)
        return {'siteTradeAuto': cat['siteTradeAuto']}
    if p.op == 'topup':   # 💸 the card's buttons: the owner's own words, the same door as typing them
        if p.job == 'no':
            cat.pop('topup', None); rs.keep_owned(cat); rs._save(store)
            return {'topup': None, 'say': '💸 Okay, no top-up. Nothing moved.'}
        if p.job == 'address':
            if not cat.get('topup'):
                raise rs.HTTPException(400, 'Nothing is waiting to be topped up.')
            out_ = rs._topup_answer(cat, {'address': (p.text or '').strip()}); rs.keep_owned(cat); rs._save(store)
            return {'topup': cat.get('topup'), 'say': out_['say']}
        try:
            usd_ = float(p.cap)
        except (TypeError, ValueError):
            raise rs.HTTPException(400, 'Say how much.')
        ok_, say_ = await rs._topup_send(cat, cat_id, round(usd_, 2), p.text)
        fresh_ = rs._load(); now_cat_ = fresh_['cats'].get(cat_id)
        if now_cat_ is not None:
            now_cat_['topups'] = cat.get('topups') or []
            if 'topup' in cat:
                now_cat_['topup'] = cat['topup']
            else:
                now_cat_.pop('topup', None)
            now_cat_['chat'] = (list(now_cat_.get('chat') or []) + [{'by': 'cats', 'text': say_, 'at': rs.time.time()}])[-200:]
            rs.keep_owned(now_cat_); rs._save(fresh_)
        if not ok_:
            raise rs.HTTPException(400, say_)
        return {'topup': None, 'say': say_, 'topups': (now_cat_ or cat).get('topups')}
    if p.op == 'site_scan':   # 🔎 the proof folder's Scan: one at a time, filed by the engine pass
        try:
            url_ = rs._ss.clean_url(p.text); site_ = rs._ss.site_of(url_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e)[:120])
        if p.job not in rs._ss.KINDS:
            raise rs.HTTPException(400, 'Scan from a PoW, PoP or Bids folder.')
        if rs._SCAN_BUSY.get(cat_id):
            raise rs.HTTPException(409, f'It is still scanning {rs._SCAN_BUSY[cat_id]}.')
        rs._SCAN_BUSY[cat_id] = site_
        rs.asyncio.create_task(rs._site_scan_run(cat_id, url_, site_, p.job, rs._site_ctx(cat)))
        return {'ok': True, 'siteScan': site_}
    if p.op == 'site_drop':
        rows_ = dict(cat.get('siteManuals') or {}); m_ = rows_.pop(rs._ss.site_of(p.text or ''), None)
        if m_ and m_.get('shot'):
            (rs.POWSHOTS_DIR / ('site' + rs.re.sub(r'[^a-z0-9]', '', cat_id.lower())[:40]) / m_['shot']).unlink(missing_ok=True)
        cat['siteManuals'] = rows_; rs.keep_owned(cat); rs._save(store)
        return {'siteManuals': rows_}
    if p.op == 'site_file':   # 🔎 the manual's command button: the same door as typing it
        got_ = rs._ss.command(p.text, cat.get('siteManuals'), set(cat.get('siteSessions') or {}))
        if not got_ or got_.get('why'):
            raise rs.HTTPException(400, (got_ or {}).get('why') or 'Not a site command.')
        ok_, say_ = rs._site_proof_start(cat, cat_id, got_['site'], got_['kind'])
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': say_, 'at': rs.time.time(), 'open': {'pop': 'pop', 'pob': 'bids'}.get(got_['kind'], 'pow')}])[-200:]
        rs.keep_owned(cat); rs._save(store)
        if not ok_:
            raise rs.HTTPException(409, say_)
        return {'ok': True, 'say': say_}
    if p.op == 'proof_review_outside':   # 🧑‍⚖️ owner 2026-11-14: the owner reviews a proof by hand (staff only), e.g. when OSSY + G4 built it
        if not await rs._session_staff(p.session or ''):
            raise rs.HTTPException(403, 'Only staff can file a review by hand.')
        t_ = p.tools or {}
        return rs._outside_review_apply(store, cat_id, str(t_.get('kind') or ''), str(p.text or ''), 'owner', t_)
    if p.op == 'pob_folder':   # 🎲 the owner's own mark on a research folder, or removing it
        rows_ = cat.get('pobFolders') or []; f_ = next((x for x in rows_ if x.get('id') == p.text), None)
        if not f_:
            raise rs.HTTPException(404, 'No such folder.')
        if p.job in ('right', 'wrong', 'clear'):
            if not f_.get('topic'):
                raise rs.HTTPException(400, 'The market grades this one.')
            if f_.get('games') or f_.get('poly'):   # 🔒 results beat grades: the scores settle it, your mark is kept as your read of it
                f_['ownerMark'] = None if p.job == 'clear' else p.job
            else:
                f_['graded'] = None if p.job == 'clear' else p.job
        elif p.job == 'delete':
            for x_ in f_.get('shots') or []:
                (rs.POWSHOTS_DIR / rs.re.sub(r'[^a-z0-9]', '', f_['id']) / rs.re.sub(r'[^a-z0-9._]', '', x_.get('file') or 'x')).unlink(missing_ok=True)
            cat['pobFolders'] = [x for x in rows_ if x is not f_]
        else:
            raise rs.HTTPException(400, 'Unknown mark.')
        rs.keep_owned(cat); rs._save(store)
        return {'pobFolders': rs._pob_view(cat)}
    if p.op == 'pob':   # 🎲 the Bids desk's button: the engine pass does the work
        ok_, say_ = rs._pob.reply(cat.get('pobRun'), bool(cat.get('pobRead')))
        if not ok_:
            raise rs.HTTPException(409, say_)
        if (room_ := rs._proof_room(cat, cat_id, 'PoB')):
            raise rs.HTTPException(409, room_)
        cat.pop('proofSite', None)
        if str(p.text or '').strip():
            cat['pobAsk'] = str(p.text).strip()[:160]; rs.keep_owned(cat); rs._save(store)
        rs._POB_WANT[cat_id] = 'start'; rs._POW_WAKE.set()
        return {'ok': True}
    if p.op == 'pool':   # 🪙 its live count, its dated returns, what its boost does and the points it can spend
        now_ = rs.time.time(); st_ = rs._cpool.load(rs.POOL_PATH); pr_ = rs._print.build(cat, now_); str_ = rs._print.strength(cat, now_); pts_ = rs._cl.boost_total(cat); pv_ = rs._cpool.view(st_, cat_id, now_, await rs._pool_px())
        top_w_ = rs._stake.rung(st_, await rs._pool_px())['top']; saved_w_ = rs._weights.load(rs.DATA_DIR)
        return {'pool': pv_, 'proofPlan': rs._plan.public(), 'weights': {f_['id']: rs._proof_view(cat, k_, f_, top_w_, saved_w_) for k_, key_ in rs._PROOF_KEYS.items() for f_ in (cat.get(key_) or []) if isinstance(f_, dict) and f_.get('id')}, 'stake': rs._stake.view(st_, cat_id, now_), 'pools': rs._stake.public_pools(st_), 'score': rs._stake.rung(st_, await rs._pool_px()), 'sends': [{**r, 'grade': x_.get('grade'), 'usd': x_.get('usd'), 'x': rs._stake.x_of(x_.get('grade')), 'scored': x_.get('scored') or [], 'kind': x_.get('kind')} for r, x_ in zip(pv_['streams'], ((st_['agents'].get(cat_id) or {}).get('streams') or [])[::-1])], 'rules': rs._cpool.rules(st_['cfg']), 'points': pts_, 'pointsLeft': round(max(0.0, pts_ - pv_['spent']), 1), 'printLevel': pr_['level'], 'strength': str_, 'boostNow': rs._cpool.boost_of(cat.get('boosts'), str_, now_, st_['cfg']['boostFadeDays']), 'boostLog': (cat.get('boosts') or [])[-8:][::-1], 'withdrawals': False, 'plan': (cat.get('colonyShare') or {}).get('plan') or 'month', 'printSeed': rs._cpool.print_seed(cat_id), 'strongest': [t for t in pr_['traits'] if t['score'] > 0][:6], 'weakest': [t for t in pr_['traits'][::-1] if t['score'] < 0][:6], 'pot': rs._cpool.totals(st_, await rs._pool_px())}
    if p.op == 'pool_fast':   # ⚡ burn points for time at the top cut. It lowers what it can ever earn, and takes nothing from anyone else
        try:
            out_ = rs._cpool.update(rs.POOL_PATH, lambda st: rs._stake.buy_fast(st, cat_id, p.cap, rs.time.time()))
            st_ = rs._cpool.load(rs.POOL_PATH)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        return {**out_, 'stake': rs._stake.view(st_, cat_id, rs.time.time())}
    if p.op == 'pool_plan':   # 🪙 which plan its next sends follow. Sends already made keep theirs.
        if p.text not in rs._cpool.PLANS:
            raise rs.HTTPException(400, 'Pick one of the plans.')
        if p.text == 'vault' and not p.on:
            raise rs.HTTPException(400, 'The Vault never comes back: confirm it first.')
        cat['colonyShare'] = {**(cat.get('colonyShare') or {}), 'plan': p.text}; rs.keep_owned(cat); rs._save(store)
        return {'plan': p.text}
    if p.op == 'pool_spend':   # ⚡ spend points to bring one send's date closer
        try:
            out_ = rs._cpool.update(rs.POOL_PATH, lambda st: rs._cpool.spend_points(st, cat_id, p.job, p.cap, rs._cl.boost_total(cat), rs.time.time()))
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        st_ = rs._cpool.load(rs.POOL_PATH)
        return {**out_, 'pool': rs._cpool.view(st_, cat_id, rs.time.time(), await rs._pool_px()), 'pointsLeft': round(max(0.0, rs._cl.boost_total(cat) - rs._num(st_['agents'][cat_id].get('spent'))), 1)}
    if p.op == 'honey':   # 🍯 the owner's four honey tanks
        shares_ = rs._shares()
        return {'honey': {**rs._colony_money(cat, shares_), 'proofs': rs._colony.proofs_of(cat, shares_)[:30], 'check': await rs._colony_reconcile(cat, shares_, rs.time.time())}}
    if p.op in ('refs_add', 'refs_drop'):   # 📚 its owner's own sites sit on top of its first list
        host_ = rs._src.host_of(p.text if str(p.text or '').startswith('http') else f'https://{str(p.text or "").strip()}')
        if p.op == 'refs_add':
            try:
                rs._cp.check_url(f'https://{host_}')
            except ValueError as e:
                raise rs.HTTPException(400, str(e)[:120])
            if not host_ or '.' not in host_:
                raise rs.HTTPException(400, 'Type a site, like pump.fun.')
            cat['refsMine'] = ([host_] + [x for x in cat.get('refsMine') or [] if x != host_])[:20]
        else:
            cat['refsMine'] = [x for x in cat.get('refsMine') or [] if x != host_]
        rs.keep_owned(cat); rs._save(store)
        return {'firstList': rs._first_list(cat)}
    if p.op == 'kind_voice':   # 🎭 AGT-3 / AGT-4: one proof kind's own prompt and personality (empty = the agent's own)
        import prompt_studio as _ps
        b_ = cat.get('brainsCfg') or {}; t_ = p.tools if isinstance(p.tools, dict) else {}; k_ = str(p.text or '')
        if k_ not in rs._lc.PROOF_KINDS or not b_:
            raise rs.HTTPException(400, 'Pick a kind of proof.')
        prompt_ = ' '.join(str(t_.get('prompt') or '').split())[:1500]
        pb_ = dict(b_.get('promptBy') or {}); vb_ = dict(b_.get('personaBy') or {})
        if prompt_:
            pb_[k_] = prompt_
        else:
            pb_.pop(k_, None)
        if t_.get('persona'):
            vb_[k_] = _ps.clean_persona(t_.get('persona'))
        elif 'persona' in t_:
            vb_.pop(k_, None)
        b_['promptBy'], b_['personaBy'] = pb_, vb_; rs.keep_owned(cat); rs._save(store)
        return {'promptBy': pb_, 'personaBy': vb_}
    if p.op == 'persona':   # 🎭 how it talks, and how hard it pushes. Words only
        import prompt_studio as _ps
        b_ = cat.setdefault('brainsCfg', {})
        if isinstance(p.tools, dict):
            b_['persona'] = _ps.clean_persona({**(b_.get('persona') or {}), **p.tools}); rs.keep_owned(cat); rs._save(store)
        return {'persona': _ps.clean_persona(b_.get('persona')), 'voice': rs._vm.view(b_.get('voice'), (b_.get('persona') or {}).get('mirror')), 'styles': list(_ps.PERSONAS), 'heat': _ps.HEAT, 'promptBy': b_.get('promptBy') or {}, 'personaBy': b_.get('personaBy') or {}}
    if p.op.startswith('watch_'):   # 👁 PoC watch (AGT-5): a page, steps, hours. It only reads; nothing is posted
        rows_ = cat.setdefault('pocWatches', [])
        try:
            if p.op == 'watch_add':
                if sum(1 for w in rows_ if w.get('status') == 'running') >= rs._pw.MAX_WATCHES:
                    raise ValueError(f'It runs {rs._pw.MAX_WATCHES} watches at once. Stop one first.')
                t_ = p.tools or {}; w_ = rs._pw.clean_watch(t_.get('url'), t_.get('steps'), t_.get('hours', 4), t_.get('perHour', 3))
                cat['pocWatches'] = rows_ = (rows_ + [w_])[-12:]
                await rs._pocwatch_check(cat, w_); rs.keep_owned(cat); rs._save(store)   # the first check now, so he sees it work (one save: a save swaps in fresh copies)
            elif p.op == 'watch_stop':   # stopping early still files what it saw
                w_ = next((w for w in rows_ if w.get('id') == p.text and w.get('status') == 'running'), None)
                if not w_:
                    raise ValueError('That watch is not running.')
                w_['stoppedEarly'] = True; rs._pocwatch_file(cat, w_); rs.keep_owned(cat); rs._save(store)
            elif p.op == 'watch_drop':
                cat['pocWatches'] = rows_ = [w for w in rows_ if not (w.get('id') == p.text and w.get('status') != 'running')]; rs.keep_owned(cat); rs._save(store)
            elif p.op != 'watch_get':
                raise ValueError('No such step.')
        except ValueError as e:
            raise rs.HTTPException(400, str(e)[:160])
        return {**rs._pocwatch_view(cat), 'pocFolders': rs._poc_view(cat)}
    if p.op.startswith('live_'):   # 📡 the ongoing PoC desk: it watches, reads the room and drafts. It never posts
        rows_ = cat.setdefault('pocWatch', []); drafts_ = cat.setdefault('pocDrafts', [])
        try:
            if p.op == 'live_add':
                if len(rows_) >= rs._pw.MAX_SITES:
                    raise ValueError('It can watch 8 pages. Remove one first.')
                t_ = p.tools or {}; rows_.append(rs._pw.clean_site(t_.get('url'), t_.get('topic'), t_.get('mood'), t_.get('voice')))
            elif p.op == 'live_drop':
                cat['pocWatch'] = rows_ = [r for r in rows_ if r.get('id') != p.text]
            elif p.op == 'live_mark':   # used or passed: its owner's word, and it is what the agent learns from
                d_ = next((x for x in drafts_ if x.get('id') == p.text), None)
                if not d_ or p.job not in ('used', 'passed'):
                    raise ValueError('That draft is gone.')
                d_['status'] = p.job
                if isinstance(p.tools, dict) and str(p.tools.get('draft') or '').strip():
                    edited_ = str(p.tools['draft'])[:900]
                    if edited_ != d_['draft']:
                        rs._play.add_note(cat, 'live', f"Rewrote a draft from: {d_['draft'][:120]} to: {edited_[:120]}")
                    d_['draft'] = edited_
                rs._play.add_note(cat, 'live', f"{p.job.capitalize()} a {d_.get('room') or ''} post: {d_['draft'][:100]}")
            elif p.op == 'live_now':
                site_ = next((r for r in rows_ if r.get('id') == p.text), None)
                if not site_:
                    raise ValueError('That page is gone.')
                got_ = await rs._live_read(cat, site_, force=True); rs.keep_owned(cat); rs._save(store)
                return {**rs._live_view(cat, rows_, (cat.get('pocDrafts') or [])[::-1]), 'said': got_}
            elif p.op != 'live_get':
                raise ValueError('No such step.')
        except ValueError as e:
            raise rs.HTTPException(400, str(e)[:160])
        if p.op != 'live_get':
            rs.keep_owned(cat); rs._save(store)
        return rs._live_view(cat, rows_, drafts_[::-1])
    if p.op.startswith('ideas_'):   # 💡 owner only, on Fee: OSSY and G4 pitch from real counts. An idea changes nothing
        if cat.get('id') != 'leader' or not await rs._is_creator(rs._session_wallet(p.session or '')):
            raise rs.HTTPException(403, 'Only the owner reads the ideas.')
        rows_ = rs._ideas.load(rs.DATA_DIR); said_ = ''
        try:
            if p.op == 'ideas_mark':
                rs._ideas.mark(rows_, str(p.text or ''), str(p.job or '')); rs._ideas.save(rs.DATA_DIR, rows_)
            elif p.op == 'ideas_ask':
                facts_ = rs._idea_facts(store); added_ = 0
                for mind_, name_ in (('local/ossy', 'OSSY'), ('local/g4', 'G4')):
                    raw_, _u = await rs._lm_call(mind_, [{'role': 'system', 'content': rs._ideas.SYS + rs._ideas.memory(rows_)}, {'role': 'user', 'content': f"THE FACTS: {facts_}{(' ASKED FOR: ' + str(p.text)[:200]) if p.text else ''}"}], 900); new_ = rs._ideas.parse(raw_, rows_, name_, rs.time.time())
                    rows_ += new_; added_ += len(new_)
                rs._ideas.save(rs.DATA_DIR, rows_); said_ = f'{added_} new ideas.' if added_ else 'OSSY and G4 sent nothing new. They may be off.'
            elif p.op != 'ideas_get':
                raise ValueError('No such step.')
        except ValueError as e:
            raise rs.HTTPException(400, str(e)[:160])
        return {'rows': rows_[::-1], 'said': said_}
    if p.op == 'desk_apps':   # 📲 a build or a game kept as an app on its desktop
        rows_ = [a for a in cat.get('deskApps') or [] if isinstance(a, dict)]
        if p.text:
            if p.on and not any(a['ws'] == p.text for a in rows_):
                w_ = next((x for x in cat.get('workspaces') or [] if x.get('id') == p.text), None)
                if not w_:
                    raise rs.HTTPException(400, 'Pick one of its folders.')
                rows_ = (rows_ + [{'ws': w_['id'], 'name': str(w_.get('name') or 'App')[:24]}])[-12:]
            elif not p.on:
                rows_ = [a for a in rows_ if a['ws'] != p.text]
            cat['deskApps'] = rows_; rs.keep_owned(cat); rs._save(store)
        if p.job == 'open':
            v_ = (rs._ws_load(cat_id, p.to) or {}).get('versions') or []
            return {'preview': rs._feat.preview(rs._ws_placed(cat_id, v_[-1]['html'])) if v_ else ''}
        return {'apps': rows_}
    if p.op.startswith('assets_'):   # 🗂 MY FILES + DISCOVER, shared by the PoC editor, the 3D studio and the Game desk (owner 2026-11-15)
        ast_ = rs._play_load(cat_id, 'assets') or {}; arows_ = list(ast_.get('rows') or [])
        adir_ = rs.DATA_DIR / 'agent_assets' / rs.re.sub(r'[^a-z0-9]', '', str(cat_id).lower())[:40]
        if p.op == 'assets_list':
            return rs._aas.view(arows_)
        if p.op == 'assets_drop':
            arows_ = rs._aas.drop(arows_, str(p.text or '')); (adir_ / rs.re.sub(r'[^a-f0-9]', '', str(p.text or ''))).unlink(missing_ok=True)
            rs._play_save(cat_id, 'assets', {'rows': arows_}); return rs._aas.view(arows_)
        if p.op in ('assets_put', 'assets_keep'):
            t_ = p.tools or {}
            if p.op == 'assets_put':
                try:
                    raw_ = rs.base64.b64decode(str(t_.get('b64') or ''), validate=True)
                except ValueError:
                    raise rs.HTTPException(400, 'That file could not be read.')
                src_, lic_, by_, url_ = 'upload', '', '', ''
            else:
                url_ = str(t_.get('url') or '')
                if not rs._aas.KEEP_FROM.match(url_):
                    raise rs.HTTPException(400, 'Files are kept only from the free libraries on this shelf.')
                async with rs.httpx.AsyncClient(timeout=60, follow_redirects=True, headers={'User-Agent': 'FEELESS/1.0 (asset shelf)'}) as h_:
                    r_ = await h_.get(url_)
                if r_.status_code != 200 or len(r_.content) > rs._aas.MAX_FILE:
                    raise rs.HTTPException(502, 'That file could not be fetched, or it is over 25 MB.')
                raw_ = r_.content; src_, lic_, by_ = str(t_.get('src') or 'Discover')[:30], t_.get('lic'), t_.get('by')
            name_ = str(t_.get('name') or '')
            if p.op == 'assets_keep' and not rs._aas.kind_of(name_):
                base_ = rs.re.sub(r'[^\w -]', '', name_).strip()[:60] or 'file'; name_ = f"{base_}.{rs._aas.ext_of(url_)}"
            try:
                arows_, row_ = rs._aas.add(arows_, name_, len(raw_), src_, lic_, by_, url_)
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            adir_.mkdir(parents=True, exist_ok=True); (adir_ / row_['id']).write_bytes(rs._ck.seal_bytes(raw_, cat_id))
            rs._play_save(cat_id, 'assets', {'rows': arows_})
            return {'row': row_, **rs._aas.view(arows_)}
        if p.op == 'assets_find':   # 🔎 the source's own API answers; nothing here is invented
            kind_ = p.job if p.job in ('image', 'video', 'audio', 'model') else 'image'; q_ = str(p.text or '').strip()[:80] or {'image': 'neon city', 'video': 'city night', 'audio': 'synthwave', 'model': 'chair'}[kind_]
            async with rs.httpx.AsyncClient(timeout=20, headers={'User-Agent': 'FEELESS/1.0 (asset shelf)'}) as h_:
                try:
                    if kind_ == 'model':
                        await rs._assets.ensure(h_, rs.KITS_DIR); return {'rows': rs._aas.model_rows(rs._assets.search(rs.KITS_DIR, q_, 'model', n=24), rs._assets.CREDIT), 'q': q_}
                    if kind_ == 'audio':
                        r_ = await h_.get(rs._aas.OPENVERSE_AUDIO, params={'q': q_, 'page_size': 20})
                        return {'rows': rs._aas.openverse_rows(r_.json()) if r_.status_code == 200 else [], 'q': q_, 'down': r_.status_code != 200}
                    r_ = await h_.get(rs._aas.commons_url(q_, video=kind_ == 'video'))
                    return {'rows': rs._aas.commons_rows(r_.json(), video=kind_ == 'video') if r_.status_code == 200 else [], 'q': q_, 'down': r_.status_code != 200}
                except (rs.httpx.HTTPError, ValueError):
                    return {'rows': [], 'q': q_, 'down': True}
        raise rs.HTTPException(400, 'No such step.')
    if p.op.startswith('gdesk_'):   # 🎮 GAME DESK (owner 2026-11-15, every user): projects of real files its mind builds, fixes or plans; checked; zipped
        gst_ = rs._play_load(cat_id, 'game') or {}; projs_ = list(gst_.get('projects') or []); style_ = list(gst_.get('style') or [])
        pid_ = str((p.tools or {}).get('id') or p.to or '')[:12]; proj_ = next((x for x in projs_ if x.get('id') == pid_), None)

        def keep_(pr=None, **more):
            if pr is not None:
                pr['checks'] = rs._gdesk.check(pr['target'], pr.get('files') or {}, pr.get('bins') or {}); pr['at'] = round(rs.time.time())
                rows = [pr] + [x for x in projs_ if x.get('id') != pr['id']]
            else:
                rows = projs_
            rs._play_save(cat_id, 'game', {**gst_, 'projects': rows[:rs._gdesk.MAX_PROJECTS], 'style': style_, **more})
            return pr

        def snap_(pr, why):   # ↩ the files before a change, so it can be undone
            rs._play_save(cat_id, f"ghist_{pr['id']}", {'rows': rs._gdesk.snap((rs._play_load(cat_id, f"ghist_{pr['id']}") or {}).get('rows'), pr, why)})

        def need_():
            if not proj_:
                raise rs.HTTPException(404, 'Open a project first.')
            return dict(proj_)
        if p.op == 'gdesk_get':
            cur_ = proj_ or (projs_[0] if projs_ else None)
            return {**rs._gdesk.view({**gst_, 'projects': projs_, 'style': style_}), 'project': cur_,
                    'undo': len((rs._play_load(cat_id, f"ghist_{cur_['id']}") or {}).get('rows') or []) if cur_ else 0,
                    'minds': [rs._answered_by(b, '') for b in ((cat.get('brainsCfg') or {}).get('brains') or [])]}
        if p.op == 'gdesk_new':
            pr_ = rs._gdesk.new_project(p.text, p.job)
            if (p.tools or {}).get('starter') and pr_['target'] in ('fivem', 'redm'):   # 🧱 a working starter, no model and no cost
                r_ = rs._game_lab.resource(pr_['name'], 'rdr3' if pr_['target'] == 'redm' else 'gta5', '')
                pr_['files'] = {**r_['files'], 'INSTALL.md': f"# {pr_['name']}\n\n{r_['install']}\n"}
            return {'project': keep_(pr_), **rs._gdesk.view({'projects': [pr_] + projs_, 'style': style_})}
        if p.op == 'gdesk_save':   # its builder's own edit of one file
            try:
                pr_ = rs._gdesk.put_file(need_(), (p.tools or {}).get('path'), (p.tools or {}).get('text'))
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            snap_(proj_, f"Before you edited {(p.tools or {}).get('path')}")
            return {'project': keep_(pr_), 'undo': 1}
        if p.op == 'gdesk_drop':
            pr_ = need_(); path_ = str((p.tools or {}).get('path') or '')
            if (pr_.get('bins') or {}).get(path_):
                b_ = rs._play_load(cat_id, f"gbin_{pr_['id']}") or {}; b_.pop(path_, None); rs._play_save(cat_id, f"gbin_{pr_['id']}", b_)
            elif path_ in (pr_.get('files') or {}):
                snap_(pr_, f'Before you removed {path_}')
            return {'project': keep_(rs._gdesk.drop(pr_, path_)), 'undo': 1}
        if p.op == 'gdesk_delete':
            projs_ = [x for x in projs_ if x.get('id') != pid_]; rs._play_save(cat_id, f'gbin_{pid_}', {}); rs._play_save(cat_id, f'ghist_{pid_}', {})
            shelf_p_ = rs.DATA_DIR / 'game_shelf.json'
            try:
                sh_ = rs.json.loads(shelf_p_.read_text())
            except (OSError, ValueError):
                sh_ = []
            shelf_p_.write_text(rs.json.dumps([r for r in sh_ if not (r.get('id') == pid_ and r.get('cat') == cat_id)]))
            keep_()
            return rs._gdesk.view({'projects': projs_, 'style': style_})
        if p.op == 'gdesk_upload':   # 📤 files from this computer: text files open in the editor, binaries ride into the zip; "learn" = its style
            t_ = p.tools or {}; path_ = str(t_.get('path') or ''); data_ = str(t_.get('b64') or '')
            if t_.get('dir') and not rs._gdesk.is_text(rs._gdesk.clean_path(path_)):
                path_ = f"{str(t_['dir']).strip().strip('/')}/{path_.rsplit('/', 1)[-1]}"   # models and textures land in the folder the page names (stream/ …)
            try:
                raw_ = rs.base64.b64decode(data_, validate=True)
            except ValueError:
                raise rs.HTTPException(400, 'That file could not be read.')
            if t_.get('learn'):
                txt_ = raw_.decode('utf-8', 'replace')[:rs._gdesk.STYLE_CHARS]
                style_ = ([{'path': rs._gdesk.clean_path(path_) or 'mine.txt', 'text': txt_}] + [s_ for s_ in style_ if s_.get('path') != path_])[:rs._gdesk.STYLE_FILES]
                keep_()
                return {'style': [{'path': s_['path'], 'chars': len(s_['text'])} for s_ in style_]}
            pr_ = need_()
            try:
                if rs._gdesk.is_text(rs._gdesk.clean_path(path_)):
                    pr_ = rs._gdesk.put_file(pr_, path_, raw_.decode('utf-8', 'replace'))
                else:
                    pr_ = rs._gdesk.put_bin(pr_, path_, len(raw_))
                    b_ = rs._play_load(cat_id, f"gbin_{pr_['id']}") or {}; b_[rs._gdesk.clean_path(path_)] = data_; rs._play_save(cat_id, f"gbin_{pr_['id']}", b_)
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            return {'project': keep_(pr_)}
        if p.op == 'gdesk_unlearn':
            style_ = [s_ for s_ in style_ if s_.get('path') != str(p.text or '')]; keep_()
            return {'style': [{'path': s_['path'], 'chars': len(s_['text'])} for s_ in style_]}
        if p.op == 'gdesk_link':   # 🎁 a real CC0 asset from the library, fetched into the zip
            async with rs.httpx.AsyncClient(timeout=30) as h_:
                await rs._assets.ensure(h_, rs.KITS_DIR); got_ = await rs._assets.resolve(h_, rs.KITS_DIR, str(p.text or ''), p.job if p.job in rs._assets.TYPES else 'model')
            if not got_:
                raise rs.HTTPException(502, 'That asset could not be read. Try another.')
            ext_ = got_['url'].rsplit('?', 1)[0].rsplit('.', 1)[-1].lower()[:5] or 'glb'
            try:
                pr_ = rs._gdesk.put_link(need_(), f"assets/{rs.re.sub(r'[^a-z0-9_]+', '_', got_['name'].lower())[:40]}.{ext_}", got_['url'], got_.get('lic') or 'CC0')
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            return {'project': keep_(pr_)}
        if p.op == 'gdesk_ask':   # 🧠 its own mind builds, fixes or plans; the check runs on what it wrote
            brains_ = (cat.get('brainsCfg') or {}).get('brains') or []
            if not brains_ or not str(p.text or '').strip():
                raise rs.HTTPException(400, 'Pick a model for this agent, and say what you want.')
            pr_ = need_(); mode_ = p.job if p.job in rs._gdesk.MODES else 'build'
            i_ = int(p.i) if isinstance(p.i, int) and 0 <= p.i < len(brains_) else 0
            sys_, user_ = rs._gdesk.prompt(pr_, mode_, p.text, style_, (p.tools or {}).get('log') or '')
            raw_, usd_, _own = await rs._ws_ask(cat, brains_[i_], sys_, user_, 3000 if mode_ == 'plan' else 16000)
            model_ = rs._answered_by(brains_[i_], rs._WS_VIA.get())
            gst_ = rs._play_load(cat_id, 'game') or {}; projs_ = list(gst_.get('projects') or []); style_ = list(gst_.get('style') or [])   # the newest state: a minute passed
            proj_ = next((x for x in projs_ if x.get('id') == pid_), None); pr_ = need_()
            if mode_ == 'plan':
                plan_, say_ = rs._gdesk.parse_plan(raw_)
                if not plan_:
                    raise rs.HTTPException(502, f"Mind {'AB'[i_]} did not send a usable plan, and nothing changed. Try again.")
                pr_['plan'] = {**plan_, 'ask': str(p.text)[:300], 'by': model_, 'at': round(rs.time.time())}
            else:
                ch_, drops_, say_ = rs._gdesk.parse_files(raw_)
                if not ch_ and not drops_:
                    raise rs.HTTPException(502, f"Mind {'AB'[i_]} did not send any files, and nothing changed. Try again, or ask for less.")
                try:
                    new_ = rs._gdesk.apply_reply(pr_, ch_, drops_)
                except ValueError as e:
                    raise rs.HTTPException(400, str(e))
                snap_(pr_, f"Before Mind {'AB'[i_]}: {str(p.text)[:80]}"); pr_ = new_
                say_ = say_ or f"Changed {', '.join(list(ch_)[:5])}."
            pr_['chat'] = (list(pr_.get('chat') or []) + [{'by': 'you', 'mode': mode_, 'text': str(p.text)[:400], 'at': round(rs.time.time())},
                           {'by': f"Mind {'AB'[i_]}", 'model': model_, 'text': str(say_ or 'Done.')[:400], 'files': [] if mode_ == 'plan' else list(ch_)[:12],
                            'usd': round(float(usd_ or 0), 5), 'at': round(rs.time.time())}])[-40:]
            return {'project': keep_(pr_), 'say': say_, 'usd': round(float(usd_ or 0), 5), 'model': model_, 'undo': len((rs._play_load(cat_id, f"ghist_{pr_['id']}") or {}).get('rows') or [])}
        if p.op == 'gdesk_undo':   # ↩ back to the files before the last change
            h_ = (rs._play_load(cat_id, f"ghist_{pid_}") or {}).get('rows') or []
            try:
                pr_, h_ = rs._gdesk.undo(h_, need_())
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs._play_save(cat_id, f"ghist_{pid_}", {'rows': h_})
            return {'project': keep_(pr_), 'undo': len(h_)}
        if p.op == 'gdesk_console':   # 🖥 the console of the owner's REAL server (or F8), pasted back: what started, what broke, per file and line
            if not str(p.text or '').strip():
                raise rs.HTTPException(400, 'Paste the server console or the F8 console first.')
            return {'console': rs._gdesk.read_console(str(p.text)[:200_000], need_())}
        if p.op == 'gdesk_take':   # 🗂 a file from its My files (Discover keeps land there too) into the project
            pr_ = need_(); aid_ = rs.re.sub(r'[^a-f0-9]', '', str(p.text or ''))[:12]
            row_ = next((r for r in ((rs._play_load(cat_id, 'assets') or {}).get('rows') or []) if r.get('id') == aid_), None)
            f_ = rs.DATA_DIR / 'agent_assets' / rs.re.sub(r'[^a-z0-9]', '', str(cat_id).lower())[:40] / aid_
            if not row_ or not f_.exists():
                raise rs.HTTPException(404, 'That file is not in My files any more.')
            raw_ = rs._ck.unseal_bytes(f_.read_bytes(), cat_id); dir_ = str((p.tools or {}).get('dir') or 'assets/')
            path_ = f"{dir_.rstrip('/')}/{row_['name']}" if dir_.strip('/') else row_['name']
            try:
                if rs._gdesk.is_text(rs._gdesk.clean_path(path_)):
                    pr_ = rs._gdesk.put_file(pr_, path_, raw_.decode('utf-8', 'replace'))
                else:
                    pr_ = rs._gdesk.put_bin(pr_, path_, len(raw_))
                    b_ = rs._play_load(cat_id, f"gbin_{pr_['id']}") or {}; b_[rs._gdesk.clean_path(path_)] = rs.base64.b64encode(raw_).decode(); rs._play_save(cat_id, f"gbin_{pr_['id']}", b_)
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            return {'project': keep_(pr_)}
        if p.op == 'gdesk_zip':   # ⬇ the whole project as a .zip, laid out to drop in; library assets are fetched now
            pr_ = need_(); bins_ = {}; held_ = rs._play_load(cat_id, f"gbin_{pr_['id']}") or {}
            async def get_(h_, path_, url_):
                try:
                    r_ = await h_.get(url_)
                    if r_.status_code == 200 and len(r_.content) <= 25_000_000:
                        bins_[path_] = r_.content
                except rs.httpx.HTTPError:
                    pass   # a library file that did not answer stays out; the page names it
            async with rs.httpx.AsyncClient(timeout=30, follow_redirects=True) as h_:
                await rs.asyncio.gather(*[get_(h_, k_, m_['url']) for k_, m_ in (pr_.get('bins') or {}).items() if m_.get('url')])
            for k_, m_ in (pr_.get('bins') or {}).items():
                if not m_.get('url') and held_.get(k_):
                    bins_[k_] = rs.base64.b64decode(held_[k_])
            z_ = rs._gdesk.zip_bytes(pr_, bins_)
            return {'name': f"{rs._gdesk.folder_name(pr_)}.zip", 'b64': rs.base64.b64encode(z_).decode(), 'size': len(z_), 'missing': [k for k in (pr_.get('bins') or {}) if k not in bins_]}
        if p.op == 'gdesk_lab':   # 🧪 its playtest log and porting checklists (game_lab.py), and the FiveM / RedM starter maker
            t_ = p.tools or {}
            if t_:
                try:
                    gst_['lab'] = rs._game_lab.apply(gst_.get('lab'), t_)
                except ValueError as e:
                    raise rs.HTTPException(400, str(e))
                keep_()
            return rs._game_lab.view(gst_.get('lab'))
        if p.op in ('gdesk_share', 'gdesk_shelf', 'gdesk_fork'):   # 🌍 DISCOVER: projects their builders chose to share, open to every agent
            shelf_p_ = rs.DATA_DIR / 'game_shelf.json'
            try:
                sh_ = rs.json.loads(shelf_p_.read_text())
            except (OSError, ValueError):
                sh_ = []
            if p.op == 'gdesk_share':
                pr_ = need_()
                if p.on and not (p.tools or {}).get('mine'):
                    raise rs.HTTPException(400, 'Only share work that is yours: confirm it first.')
                pr_['shared'] = bool(p.on)
                sh_ = rs._gdesk.shelf_put(sh_, rs._gdesk.shelf_row(pr_, cat_id, cat.get('name')), bool(p.on)); shelf_p_.write_text(rs.json.dumps(sh_))
                return {'project': keep_(pr_)}
            if p.op == 'gdesk_fork':
                row_ = next((r for r in sh_ if r.get('id') == pid_ and r.get('cat') == str((p.tools or {}).get('cat') or '')), None)
                src_ = next((x for x in ((rs._play_load(row_['cat'], 'game') or {}).get('projects') or []) if x.get('id') == pid_ and x.get('shared')), None) if row_ else None
                if not src_:
                    raise rs.HTTPException(404, 'That project is not shared any more.')
                pr_ = rs._gdesk.fork(src_); row_['forks'] = int(row_.get('forks') or 0) + 1; shelf_p_.write_text(rs.json.dumps(sh_))
                projs_ = [pr_] + projs_
                return {'project': keep_(pr_), **rs._gdesk.view({'projects': projs_, 'style': style_})}
            return {'rows': rs._gdesk.shelf_find(sh_, p.text, p.job if p.job in rs._gdesk.TARGETS else '')}
        raise rs.HTTPException(400, 'No such step.')
    if p.op.startswith('playc_'):   # 🎬 the PoC editor: media stays in the owner's browser, the edit list comes here
        saved_ = rs._play_load(cat_id, 'edit') or {}
        files_ = dict(saved_.get('files') or {}); cur_ = saved_.get('current') or 'Untitled'   # 📁 named edit files (owner 2026-11-10: "new starts a file they name to save and just go")
        if saved_.get('project') and cur_ not in files_:
            files_[cur_] = {'project': saved_['project'], 'at': saved_.get('at') or round(rs.time.time())}   # an edit from before files existed keeps its work as "Untitled"
        list_ = lambda: sorted([{'name': k, 'at': v.get('at'), 'clips': len((v.get('project') or {}).get('clips') or [])} for k, v in files_.items()], key=lambda x: -(x['at'] or 0))[:40]
        if p.op in ('playc_new', 'playc_open'):
            name_ = rs.re.sub(r'\s+', ' ', str(p.text or '')).strip()[:60]
            if not name_:
                raise rs.HTTPException(400, 'Name the file first.')
            if p.op == 'playc_new':
                if name_ in files_:
                    raise rs.HTTPException(400, 'A file with that name exists. Open it, or pick another name.')
                if len(files_) >= 40:
                    raise rs.HTTPException(400, 'Forty files is the limit. Delete one in your files first.')
                files_[name_] = {'project': None, 'at': round(rs.time.time())}
            elif name_ not in files_:
                raise rs.HTTPException(404, 'No file with that name.')
            rs._play_save(cat_id, 'edit', {**saved_, 'files': files_, 'current': name_, 'project': files_[name_].get('project')})
            return {'project': files_[name_].get('project'), 'current': name_, 'files': list_()}
        if p.op == 'playc_get':
            return {'current': cur_, 'files': list_(), 'project': saved_.get('project'), 'notes': ((cat.get('playNotes') or {}).get('edit') or [])[-3:], 'canAsk': bool((cat.get('brainsCfg') or {}).get('brains')), 'canPaid': bool(rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR))}
        if p.op == 'playc_gen':   # 🖼 free needs no key. Better uses the agent's own OpenRouter key and its own balance
            prompt_ = ' '.join(str(p.text or '').split())
            if not prompt_:
                raise rs.HTTPException(400, 'Say what to make.')
            size_ = p.tools or {}
            async with rs.httpx.AsyncClient(timeout=120, follow_redirects=True) as h_:
                if p.job == 'better':
                    key_ = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
                    if not key_:
                        raise rs.HTTPException(400, 'Better images use your own OpenRouter key. Add it in this agent\'s keys, or use Free.')
                    r_ = await h_.post('https://openrouter.ai/api/v1/chat/completions', headers={'Authorization': f'Bearer {key_}'}, json={'model': rs._play.PAID_IMAGE_MODEL, 'modalities': ['image', 'text'], 'messages': [{'role': 'user', 'content': prompt_[:800] + rs._play.IMAGE_RULES}], 'usage': {'include': True}})
                    if r_.status_code != 200:
                        raise rs.HTTPException(502, str((r_.json().get('error') or {}).get('message') if 'json' in r_.headers.get('content-type', '') else 'OpenRouter did not answer.')[:200])
                    j_ = r_.json(); im_ = ((j_.get('choices') or [{}])[0].get('message') or {}).get('images') or []
                    if not im_:
                        raise rs.HTTPException(502, 'That model sent no image. Try another prompt.')
                    if float((j_.get('usage') or {}).get('cost') or 0) > 0:   # 🧾
                        rs._receipt_write({'id': str(j_.get('id') or rs.uuid.uuid4().hex)[:40], 'cat': cat_id, 'at': rs.time.time(), 'provider': 'OpenRouter', 'model': rs._play.PAID_IMAGE_MODEL,
                                        'usd': float(j_['usage']['cost']), 'tokens': None, 'status': 'provider reported', 'funding': 'owner key'})
                    return {'image': im_[0]['image_url']['url'], 'usd': (j_.get('usage') or {}).get('cost'), 'by': rs._play.PAID_IMAGE_MODEL}
                r_ = await h_.get(rs._play.free_image_url(prompt_, size_.get('w'), size_.get('h'), rs.secrets.randbelow(999999)), headers={'User-Agent': 'FEELESS'})
                if r_.status_code != 200 or not r_.headers.get('content-type', '').startswith('image/') or len(r_.content) > rs._play.MAX_IMAGE_BYTES:
                    raise rs.HTTPException(502, 'The free image service did not answer. Try again in a minute.')
                return {'image': f"data:{r_.headers['content-type'].split(';')[0]};base64,{rs.base64.b64encode(r_.content).decode()}", 'usd': 0, 'by': 'Pollinations (free)'}
        project_ = rs._play.clean_project((p.tools or {}).get('project'))
        if p.op == 'playc_save':   # the open file keeps every save, so switching files never loses work
            files_[cur_] = {'project': project_, 'at': round(rs.time.time())}
            rs._play_save(cat_id, 'edit', {**saved_, 'project': project_, 'files': files_, 'current': cur_})
            return {'ok': True, 'current': cur_}
        if p.op == 'playc_ask':
            brains_ = (cat.get('brainsCfg') or {}).get('brains') or []
            if not brains_ or not str(p.text or '').strip():
                raise rs.HTTPException(400, 'Pick a model for this agent, and say what you want.')
            if p.job == 'image':
                raw_, usd_, _o = await rs._ws_ask(cat, brains_[0], rs._play.IMAGE_SYS + rs._play.notes_line(cat, 'edit'), f"BUILD THIS: {str(p.text)[:800]}", 900)
                rows_, say_ = rs._play.parse_layers(raw_)
                if not rows_:
                    raise rs.HTTPException(502, 'The agent did not send a usable design, and nothing changed. Try again.')
                return {'layers': rows_, 'say': say_, 'usd': round(float(usd_ or 0), 5)}
            mine_ = rs._play.style_note(rs._play.edit_stats(project_)) if saved_.get('mind') and project_ != saved_.get('mind') else ''
            if mine_:
                rs._play.add_note(cat, 'edit', mine_); rs.keep_owned(cat); rs._save(store)
            raw_, usd_, _o = await rs._ws_ask(cat, brains_[0], rs._play.EDIT_SYS + rs._play.notes_line(cat, 'edit') + rs._recall(cat, 'Content', str(p.text)), f"THE PROJECT NOW: {rs.json.dumps(project_)[:7000]}\nREQUEST: {str(p.text)[:800]}", 1800)
            plan_, say_ = rs._play.parse_edit(raw_, project_)
            if not plan_:
                raise rs.HTTPException(502, 'The agent did not send a usable edit, and nothing changed. Try again.')
            rs._play_save(cat_id, 'edit', {'project': plan_, 'mind': plan_})
            return {'project': plan_, 'say': say_, 'usd': round(float(usd_ or 0), 5), 'learned': mine_}
        if p.op == 'playc_file':
            stats_ = rs._play.edit_stats(project_) if (p.tools or {}).get('project') else {}
            what_ = (p.tools or {}).get('image') if isinstance((p.tools or {}).get('image'), dict) else None
            if not stats_.get('clips') and not what_:
                raise rs.HTTPException(400, 'Edit something first.')
            rs._play.add_note(cat, 'edit', rs._play.style_note(stats_)); rows_ = list(cat.get('pocFolders') or [])
            rows_.append({'id': f'poc{rs.secrets.token_hex(5)}', 'n': rs._next_n(rows_), 'kind': 'PoC', 'at': round(rs.time.time()), 'status': 'closed', 'paper': True, 'topic': ' '.join(str(p.job or 'An edit').split())[:60], 'calls': [], 'by': 'Editor', **({'edit': stats_} if stats_.get('clips') else {}), **({'design': {'layers': int(rs._play._num(what_.get('layers'), 0, 200, 0)), 'size': str(what_.get('size') or '')[:12]}} if what_ else {})})
            cat['pocFolders'] = rows_[-60:]; rs.keep_owned(cat); rs._save(store); rs._play_save(cat_id, 'edit', {**saved_, 'project': project_, 'mind': project_})
            return {'filed': rows_[-1], 'pocFolders': rs._poc_view(cat)}
        raise rs.HTTPException(400, 'No such step.')
    if p.op.startswith('play3d_'):   # 🧊 the PoStatic 3D playground: the owner and the agent work on one scene, and it learns from what the owner changes
        saved_ = rs._play_load(cat_id, '3d') or {}
        if p.op == 'play3d_get':
            c3_ = rs._play_load(cat_id, 'code3d') or {}
            return {'code': c3_.get('code') or '', 'codeChat': c3_.get('chat') or [], 'minds': [str(b_).split('/')[-1] for b_ in ((cat.get('brainsCfg') or {}).get('brains') or [])[:2]], 'scene': saved_.get('scene'), 'mind': saved_.get('mind'), 'notes': ((cat.get('playNotes') or {}).get('3d') or [])[-3:], 'canAsk': bool((cat.get('brainsCfg') or {}).get('brains')), **rs._play.menu()}
        now_scene_ = rs._play.clean_scene((p.tools or {}).get('scene'))
        if p.op in ('play3d_template', 'play3d_mood'):   # 🧱 a whole set in one tap, with no model and no cost
            base_ = rs._play.template_scene(p.job) if p.op == 'play3d_template' else rs._play.clean_scene(rs._play.dress(now_scene_, p.job, str(len(now_scene_['objects']))))
            if not base_ or (p.op == 'play3d_mood' and p.job not in rs._play.MOODS):
                raise rs.HTTPException(400, 'No such choice.')
            async with rs.httpx.AsyncClient(timeout=30) as h_:
                await rs._assets.ensure(h_, rs.KITS_DIR); base_, used_, missing_ = await rs._assets.fill(h_, rs.KITS_DIR, base_)
            base_ = rs._play.lead_up(base_)
            if p.op == 'play3d_template':
                base_['camera'] = [0, 0, 0]; base_ = rs._play._frame(rs._assets.compose(base_))
            rs._play_save(cat_id, '3d', {**saved_, 'scene': base_})
            return {'scene': base_, 'say': f"Ready. Real assets: {', '.join(dict.fromkeys(used_)) or 'none'}." + (f" Not in the library: {', '.join(missing_)}." if missing_ else '')}
        if p.op == 'play3d_take':   # 🗂 a 3D scene this owner filed (any of its agents) opens back in the playground
            src_ = str(p.to or cat_id); c2_ = store['cats'].get(src_)
            if not c2_ or not (src_ == cat_id or rs._same_owner(cat, c2_)):
                raise rs.HTTPException(403, 'That scene is not yours.')
            sc_ = (rs._ws_load(src_, rs.re.sub(r'[^a-z0-9]', '', str(p.job or ''))) or {}).get('scene3d')
            if not isinstance(sc_, dict):
                raise rs.HTTPException(404, 'That scene is gone.')
            sc_ = rs._play.clean_scene(sc_); rs._play_save(cat_id, '3d', {**saved_, 'scene': sc_})
            return {'scene': sc_, 'say': 'Your filed scene is open. It saves as you work.'}
        if p.op == 'play3d_preview':   # the real page, exactly as it would file
            if not now_scene_['objects'] and not now_scene_.get('game') and not now_scene_.get('hero'):
                raise rs.HTTPException(400, 'Add something to the scene first.')
            async with rs.httpx.AsyncClient(timeout=30) as h_:
                await rs._assets.ensure(h_, rs.KITS_DIR); ready_, _u, _m = await rs._assets.fill(h_, rs.KITS_DIR, now_scene_)
            return {'preview': rs._feat.preview(rs._play.lock_site(rs._play.to_html(ready_, str(p.job or '3D scene'))))}
        if p.op == 'play3d_save':
            rs._play_save(cat_id, '3d', {**saved_, 'scene': now_scene_})
            return {'ok': True}
        if p.op == 'play3d_assets':   # 🎁 real CC0 assets. The list and the real file addresses come from Poly Haven's own API
            async with rs.httpx.AsyncClient(timeout=30) as h_:
                await rs._assets.ensure(h_, rs.KITS_DIR)
                if p.to:
                    got_ = await rs._assets.resolve(h_, rs.KITS_DIR, p.to, p.job or 'model')
                    if not got_:
                        raise rs.HTTPException(502, 'That asset could not be read. Try another.')
                    return {'asset': got_}
            kind_ = p.job if p.job in rs._assets.TYPES else 'model'
            real_ = rs._rworld.resolve(rs._rworld.cards(), lambda q_: rs._assets.search(rs.KITS_DIR, q_, 'model', n=1)) if kind_ == 'model' and not str(p.text or '').strip() else []   # 🌍 real products first (owner 2026-11-15)
            return {'rows': rs._assets.search(rs.KITS_DIR, p.text, kind_), 'credit': rs._assets.CREDIT, 'real': real_, 'realCats': [list(c) for c in rs._rworld.CATS]}
        if p.op == 'play3d_ask':
            brains_ = (cat.get('brainsCfg') or {}).get('brains') or []
            if not brains_ or not str(p.text or '').strip():
                raise rs.HTTPException(400, 'Pick a model for this agent, and say what to build.')
            note_ = rs._play.diff_scene(saved_.get('mind'), now_scene_) if saved_.get('mind') else ''
            if note_:
                rs._play.add_note(cat, '3d', note_); rs.keep_owned(cat); rs._save(store)
            raw_, usd_, _own = await rs._ws_ask(cat, brains_[0], rs._play.SCENE_SYS + rs._play.notes_line(cat, '3d') + rs._recall(cat, 'Code', str(p.text)), f"THE SCENE NOW: {rs._play.scene_brief(now_scene_)}\nBUILD THIS: {str(p.text)[:800]}", 3500)
            scene_, say_ = rs._play.parse_reply(raw_, now_scene_, str(p.text))
            if not scene_:
                raise rs.HTTPException(502, 'The agent did not send a usable scene, and nothing changed. Try again, or ask for less.')
            async with rs.httpx.AsyncClient(timeout=30) as h_:
                await rs._assets.ensure(h_, rs.KITS_DIR); scene_, used_, missing_ = await rs._assets.fill(h_, rs.KITS_DIR, scene_, many=bool(rs._assets.MANY.search(str(p.text))))
            if used_ or missing_:
                say_ = f"{say_} Used: {', '.join(used_[:6]) or 'nothing real'}." + (f" Not found: {', '.join(missing_[:4])}." if missing_ else '')
            rs._play_save(cat_id, '3d', {'scene': scene_, 'mind': scene_})
            return {'scene': scene_, 'say': say_, 'usd': round(float(usd_ or 0), 5), 'learned': note_}
        if p.op == 'play3d_code':   # 💻 the code playground: a mind writes or changes the module; with two minds they take turns leading
            brains_ = (cat.get('brainsCfg') or {}).get('brains') or []
            if not brains_ or not str(p.text or '').strip():
                raise rs.HTTPException(400, 'Pick a model for this agent, and say what to make.')
            code_s_ = rs._play_load(cat_id, 'code3d') or {}; turn_ = int(code_s_.get('turn') or 0); was_ = str(p.job or code_s_.get('code') or '')[:40000]
            pick_ = str(p.to if p.to is not None else 'both'); i_ = int(pick_) if pick_ in ('0', '1') and int(pick_) < len(brains_) else turn_ % len(brains_)   # 🧠 owner 2026-11-11: pick the mind that writes, or let them take turns
            raw_, usd_, _own = await rs._ws_ask(cat, brains_[i_], rs._play.CODE_SYS + rs._recall(cat, 'Code', str(p.text)), (f'THE CODE NOW:\n{was_}\n\n' if was_ else '') + f'MAKE THIS: {str(p.text)[:1200]}', 16000)
            code_, say_ = rs._play.code_reply(raw_)
            if not code_:
                raise rs.HTTPException(502, f"Mind {'AB'[i_]} did not send usable code, and nothing changed. Try again.")
            if rs._play.code_cut(code_):   # 🛡 a reply that hit its length cap opens black: say so, keep the old code
                raise rs.HTTPException(502, f"Mind {'AB'[i_]}'s code was cut off before the end, and nothing changed. Ask for a smaller scene or try again.")
            chat_ = (list(code_s_.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': round(rs.time.time())}, {'by': f"Mind {'AB'[i_]}", 'model': rs._answered_by(brains_[i_], rs._WS_VIA.get()), 'text': str(say_ or 'Done.')[:400], 'usd': round(float(usd_ or 0), 5), 'at': round(rs.time.time())}])[-30:]
            rs._play_save(cat_id, 'code3d', {'code': code_, 'turn': turn_ + 1, 'chat': chat_, 'prev': was_})
            return {'code': code_, 'say': say_, 'by': f"Mind {'AB'[i_]}", 'model': rs._answered_by(brains_[i_], rs._WS_VIA.get()), 'usd': round(float(usd_ or 0), 5), 'chat': chat_, 'prev': was_}
        if p.op == 'play3d_code_save':   # 💾 its owner's own edits stay with the playground
            rs._play_save(cat_id, 'code3d', {**(rs._play_load(cat_id, 'code3d') or {}), 'code': str(p.job or '')[:60000]})
            return {'saved': True}
        if p.op == 'play3d_code_file':   # 📄 the running module becomes a real page and a PoStatic, the same locked page anyone opens
            code_ = str(p.job or (rs._play_load(cat_id, 'code3d') or {}).get('code') or '')
            if 'THREE' not in code_:
                raise rs.HTTPException(400, 'Write or ask for some three.js first.')
            try:
                row_ = rs._feat.new_folder(cat, 'build', str(p.text or '3D playground')[:40], rs.time.time())
            except ValueError as e:
                raise rs.HTTPException(409, str(e))
            doc_ = rs._feat.new_doc(row_); doc_['versions'] = [{'html': rs._play.code_page(code_, row_['name']), 'by': '3D playground', 'at': round(rs.time.time())}]; doc_['kitsUsed'] = [{'id': 'three', 'name': 'three.js', 'used': True}]
            filed_ = rs._feat.file_static(cat, doc_, '3D playground', rs.time.time()); rs._ws_save(cat_id, doc_); rs.keep_owned(cat); rs._save(store)
            return {'folder': row_, 'filed': filed_, 'workspaces': rs._ws_list(cat)}
        if p.op == 'play3d_file':
            if not now_scene_['objects'] and not now_scene_.get('hero'):
                raise rs.HTTPException(400, 'Add something to the scene first.')
            note_ = rs._play.diff_scene(saved_.get('mind'), now_scene_) if saved_.get('mind') else ''
            if note_:
                rs._play.add_note(cat, '3d', note_)
            async with rs.httpx.AsyncClient(timeout=120) as h_:
                await rs._play.embed_pictures(h_, [now_scene_])
            try:
                row_ = rs._feat.new_folder(cat, 'build', str(p.job or '3D scene')[:40], rs.time.time())
            except ValueError as e:
                raise rs.HTTPException(409, str(e))
            doc_ = rs._feat.new_doc(row_); doc_['scene3d'] = now_scene_; doc_['versions'] = [{'html': rs._play.lock_site(rs._play.to_html(now_scene_, row_['name'])), 'by': '3D studio', 'at': round(rs.time.time())}]; doc_['kitsUsed'] = [{'id': 'three', 'name': 'three.js', 'used': True}]; rs._ws_save(cat_id, doc_)
            filed_ = rs._feat.file_static(cat, doc_, '3D studio', rs.time.time()); rs.keep_owned(cat); rs._save(store); rs._play_save(cat_id, '3d', {**saved_, 'scene': now_scene_, 'mind': now_scene_})
            return {'filed': filed_, 'psFolders': (cat.get('psFolders') or [])[::-1], 'workspaces': rs._ws_list(cat)}
        raise rs.HTTPException(400, 'No such step.')
    if p.op.startswith('debate_'):   # ⚔ Collective Debate. The owner puts proofs on the table and allows their agent to grade. No money moves here
        b_ = cat.setdefault('brainsCfg', {}); st_ = rs._debate.load(rs.DATA_DIR)
        try:
            if p.op == 'debate_put':
                k_ = rs._weights.kind_of(p.job); f_ = next((x for x in cat.get(rs._PROOF_KEYS.get(k_) or '') or [] if isinstance(x, dict) and x.get('id') == p.text), None)
                if not f_:
                    raise ValueError('Pick one of its filed proofs.')
                rs._debate.put(st_, cat_id, cat.get('name'), k_, f_, rs._weights.facts_line(rs._proof_view(cat, k_, f_)), rs.json.dumps({x: v for x, v in rs._vv.public_folder(f_).items() if x not in ('talk', 'chat', 'shots', 'vitals')}, default=str))
            elif p.op == 'debate_pull':
                rs._debate.pull(st_, cat_id, str(p.text or ''))
            elif p.op == 'debate_offer':
                rs._debate.offer(st_, cat_id, str(p.text or ''), str(p.job or ''))
            elif p.op == 'debate_answer':
                rs._debate.answer(st_, cat_id, str(p.text or ''), bool(p.on))
            elif p.op == 'debate_allow':
                b_['debateOn'] = bool(p.on); rs.keep_owned(cat); rs._save(store)
            elif p.op in ('debate_room_open', 'debate_room_join'):
                t_ = p.tools if isinstance(p.tools, dict) else {}; k_ = rs._weights.kind_of(t_.get('kind')); f_ = next((x for x in cat.get(rs._PROOF_KEYS.get(k_) or '') or [] if isinstance(x, dict) and x.get('id') == t_.get('fid')), None)
                if not f_:
                    raise ValueError('Pick one of its filed proofs.')
                row_ = next((r for r in st_['table'] if r['cat'] == cat_id and r['fid'] == f_['id']), None); v_ = rs._proof_view(cat, k_, f_) or {}
                row_ = row_ or rs._debate.put(st_, cat_id, cat.get('name'), k_, f_, rs._weights.facts_line(v_), rs.json.dumps({x: y for x, y in rs._vv.public_folder(f_).items() if x not in ('talk', 'chat', 'shots', 'vitals')}, default=str))
                row_['vitals'] = {'rank': v_.get('rank'), 'score': v_.get('score'), 'top': v_.get('top'), 'frac': v_.get('frac'), 'parts': [{'label': x.get('label'), 'value': x.get('value')} for x in (v_.get('parts') or [])][:8]}
                who_ = rs.owner_wallet(cat) or str(cat.get('ownerId') or cat_id)
                if p.op == 'debate_room_open':
                    rs._debate.open_room(st_, cat_id, who_, cat.get('name'), row_['id'])
                else:
                    rs._debate.join_room(st_, str(t_.get('room') or ''), cat_id, who_, cat.get('name'), row_['id'])
            elif p.op == 'debate_room_say':
                t_ = p.tools if isinstance(p.tools, dict) else {}; rs._debate.say(st_, str(t_.get('room') or ''), cat_id, t_.get('text'))
            elif p.op == 'debate_room_concede':
                t_ = p.tools if isinstance(p.tools, dict) else {}; rs._debate.concede(st_, str(t_.get('room') or ''), cat_id, t_.get('i'))
            elif p.op == 'debate_room_vote':
                t_ = p.tools if isinstance(p.tools, dict) else {}; rs._debate.vote(st_, str(t_.get('room') or ''), cat_id, rs.owner_wallet(cat) or str(cat.get('ownerId') or cat_id), t_.get('side'), any(isinstance(x, dict) and x.get('status') == 'closed' for key_ in rs._PROOF_KEYS.values() for x in cat.get(key_) or []))
            elif p.op == 'debate_room_leave':
                t_ = p.tools if isinstance(p.tools, dict) else {}; rs._debate.leave_room(st_, str(t_.get('room') or ''), cat_id)
            elif p.op != 'debate_get':
                raise ValueError('No such step.')
        except ValueError as e:
            raise rs.HTTPException(400, str(e)[:160])
        moved_ = rs._debate.tick(st_)
        moved_ = rs._debate_bank(st_) or moved_
        if moved_ or p.op not in ('debate_get', 'debate_allow'):
            rs._debate.save(rs.DATA_DIR, st_)
        return {**rs._debate.view(st_, cat_id), 'room': rs._debate.rooms_view(st_, cat_id, rs.owner_wallet(cat) or str(cat.get('ownerId') or cat_id)), 'allowed': bool(b_.get('debateOn')), 'canGrade': bool(b_.get('brains'))}
    if p.op.startswith('eco_d_'):   # 🗂 the PoEco desk: sealed, its owner's only, Python does every sum, and nothing here can move money
        today_ = rs._eco.their_today(p.to, rs.time.strftime('%Y-%m-%d', rs.time.gmtime())); desk_ = rs._eco_desk_load(cat_id); said_ = None
        try:
            if p.op == 'eco_d_setup':
                rs._eco.run_setup(desk_, p.tools, today_)
            elif p.op == 'eco_d_tone':
                rs._eco.set_tone(desk_, p.text)
            elif p.op == 'eco_d_ai':   # 🤖 its owner's switch: what the agent may read
                rs._eco.set_ai(desk_, str(p.text or '')); cat['poeAi'] = rs._eco.ai_level(desk_) != 'off'; rs.keep_owned(cat); rs._save(store)
            elif p.op in ('eco_d_chat', 'eco_d_check'):
                facts_ = rs._eco.ai_facts(desk_, today_); brains_ = (cat.get('brainsCfg') or {}).get('brains') or []
                if not facts_:
                    raise ValueError('Turn your agent on first. It cannot read sealed books until you say so.')
                if not brains_:
                    raise ValueError('Pick a model for this agent first.')
                ask_ = rs._eco.CHECK_ASK if p.op == 'eco_d_check' else str(p.text or '').strip()[:800]
                if not ask_:
                    raise ValueError('Say what you want to know.')
                past_ = '\n'.join(f"{m['by']}: {m['text'][:300]}" for m in (desk_.get('chat') or [])[-6:]) if p.op == 'eco_d_chat' else ''
                raw_, _usd, _own = await rs._ws_ask(cat, brains_[0], rs._eco.ECO_SYS, f'THE BOOKS: {facts_}\n{past_}\nOWNER: {ask_}', 700); said_, rows_ = rs._eco.parse_ai(raw_)
                if not said_:
                    raise ValueError('The agent did not answer. Nothing changed.')
                if p.op == 'eco_d_check':
                    rs._eco.add_check(desk_, said_, today_)
                else:
                    rs._eco.add_chat(desk_, 'you', ask_, at=round(rs.time.time())); rs._eco.add_chat(desk_, 'agent', said_, rows_, round(rs.time.time()))
                said_ = None
            elif p.op == 'eco_d_add':
                rs._eco.add_row(desk_, str(p.job or ''), p.tools)
            elif p.op == 'eco_d_edit':
                rs._eco.edit_row(desk_, str(p.job or ''), str(p.text or ''), p.tools)
            elif p.op == 'eco_d_drop':
                rs._eco.drop_row(desk_, str(p.job or ''), str(p.text or ''))
            elif p.op == 'eco_d_entry':
                t_ = p.tools or {}; rs._eco.add_entry(desk_, t_.get('date') or today_, t_.get('desc'), rs._eco._money(t_.get('amount')), t_.get('cat'))
            elif p.op == 'eco_d_bill_paid':
                rs._eco.bill_paid(desk_, str(p.text or ''), today_)
            elif p.op == 'eco_d_invoice_paid':
                rs._eco.invoice_paid(desk_, str(p.text or ''), today_)
            elif p.op == 'eco_d_import':
                said_ = rs._eco.import_rows(desk_, p.text)
            elif p.op == 'eco_d_check':
                rs._eco.check_in(desk_, str(p.text or ''), today_)
            elif p.op == 'eco_d_clear':
                rs._eco.clear_samples(desk_)
            elif p.op == 'eco_d_prove':   # the books as they stand become a filed proof, with the same hash and receipt as before
                rows_ = sorted(({k: r[k] for k in ('date', 'desc', 'amount', 'cat')} for r in desk_['ledger'] if not r.get('sample') and (not p.text or r['date'].startswith(str(p.text)))), key=lambda r: r['date'])
                if not rows_:
                    raise ValueError('There are no real entries to prove yet. Made-up examples never count.')
                list_ = cat.setdefault('poeFolders', []); f_ = rs._eco.new_folder(len(list_) + 1, p.job or p.text or 'All books', rows_, (desk_.get('setup') or {}).get('tax', 25), rs.time.time()); list_.append(f_)
                path_ = rs.DATA_DIR / 'agent_eco' / rs.re.sub(r'[^a-z0-9]', '', str(cat_id).lower())[:40]; path_.mkdir(parents=True, exist_ok=True); (path_ / f"{f_['id']}.seal").write_bytes(rs._ck.seal_bytes(rs.json.dumps(rows_).encode(), cat_id)); rs.keep_owned(cat); rs._save(store)
            elif p.op != 'eco_d_get':
                raise ValueError('No such step.')
        except (ValueError, TypeError) as e:
            raise rs.HTTPException(400, str(e)[:160])
        if p.op != 'eco_d_get':
            rs._eco_desk_save(cat_id, desk_)
        return {'desk': desk_, 'view': rs._eco.view(desk_, today_), 'today': today_, 'said': said_, 'poeFolders': (cat.get('poeFolders') or [])[::-1]}
    if p.op == 'eco_call':   # 📊 PoEco rebuilt (owner 2026-11-13): one sealed market call on live pools, graded by reality a day later
        async with rs.httpx.AsyncClient(timeout=15) as http_:
            rows_ = await rs._eco_pools(http_)
        try:
            list_ = cat.setdefault('poeFolders', []); f_ = rs._ecm.make_call(rows_, len(list_) + 1)
        except ValueError as e:
            raise rs.HTTPException(400, str(e)[:160])
        list_.append(f_); rs.keep_owned(cat); rs._save(store)
        return {'poeFolders': cat['poeFolders'][::-1]}
    if p.op == 'eco_grade':   # grades every due market call from fresh real numbers. Pure math, no one marks it
        due_ = [f for f in cat.get('poeFolders') or [] if f.get('kind') == 'market' and not f.get('graded') and rs.time.time() >= float(f.get('due') or 0)]
        if due_:
            addrs_ = sorted({f['baseline'][k]['addr'] for f in due_ for k in ('pick', 'other')})
            async with rs.httpx.AsyncClient(timeout=15) as http_:
                rows_ = await rs._eco_pools(http_, addrs_)
            for f in due_:
                rs._ecm.grade(f, rows_)
            rs.keep_owned(cat); rs._save(store)
        return {'poeFolders': (cat.get('poeFolders') or [])[::-1], 'graded': len(due_)}
    if p.op == 'eco_file':   # 📊 PoEco: Python does the math, its entries are sealed, the folder keeps totals and a hash
        rows_, skipped_ = rs._eco.parse(p.text)
        if not rows_:
            raise rs.HTTPException(400, 'No entries could be read. Use date, description, amount, one a line.')
        list_ = cat.setdefault('poeFolders', []); f_ = rs._eco.new_folder(len(list_) + 1, p.job, rows_, p.cap if p.cap is not None else 25, rs.time.time()); list_.append(f_)
        path_ = rs.DATA_DIR / 'agent_eco' / rs.re.sub(r'[^a-z0-9]', '', str(cat_id).lower())[:40]; path_.mkdir(parents=True, exist_ok=True); (path_ / f"{f_['id']}.seal").write_bytes(rs._ck.seal_bytes(rs.json.dumps(rows_).encode(), cat_id))
        rs.keep_owned(cat); rs._save(store)
        return {'poeFolders': cat['poeFolders'][::-1], 'skipped': skipped_}
    if p.op == 'eco_mark':
        f_ = next((x for x in cat.get('poeFolders') or [] if x.get('id') == p.job), None)
        if not f_ or p.text not in ('right', 'wrong'):
            raise rs.HTTPException(400, 'Mark one of its PoEco books.')
        if f_.get('kind') == 'market':
            raise rs.HTTPException(400, 'Reality grades a market call. No hand marks.')
        f_['graded'] = p.text; rs.keep_owned(cat); rs._save(store)
        return {'poeFolders': cat['poeFolders'][::-1]}
    if p.op == 'eco_send':   # a receipt: totals and the hash, never an entry
        f_ = next((x for x in cat.get('poeFolders') or [] if x.get('id') == p.job), None)
        if not f_:
            raise rs.HTTPException(400, 'Pick one of its PoEco books.')
        f_['sent'] = round(rs.time.time()); rs.keep_owned(cat); rs._save(store)
        return {'receipt': rs._ecm.receipt(f_) if f_.get('kind') == 'market' else rs._eco.receipt(f_), 'poeFolders': cat['poeFolders'][::-1]}
    if p.op == 'desk_layout':   # 🖥 where its folders sit, kept with the agent so a refresh, a full browser or another screen never loses it
        if isinstance(p.tools, dict) and isinstance(p.tools.get('pos'), dict):
            cat['deskIcons'] = {str(k)[:24]: {'x': max(0, min(20000, int(v['x']))), 'y': max(0, min(20000, int(v['y'])))} for k, v in list(p.tools['pos'].items())[:80] if isinstance(v, dict) and isinstance(v.get('x'), (int, float)) and isinstance(v.get('y'), (int, float))}
            rs.keep_owned(cat); rs._save(store)
        return {'pos': cat.get('deskIcons') or {}}
    if p.op in ('git_clean', 'git_keep'):   # 🧹 its own record: when its least used files may go, and which to keep. Only it decides
        c_ = rs._sort.clean_view(cat)
        if p.op == 'git_clean':
            days_ = int((p.tools or {}).get('days') or c_['days']) if isinstance(p.tools, dict) else c_['days']
            cat['gitClean'] = {'auto': bool(p.on) if p.on is not None else c_['auto'], 'days': max(7, min(365, days_))}
        else:
            d_ = rs._sort.load(rs.GIT_DIR); keep_ = {str(x) for x in ((p.tools or {}).get('paths') or [])}; n_ = cat.get('gitNotice') or {}
            for x in keep_ & set(n_.get('paths') or []):
                d_['items'][x] = {**(d_['items'].get(x) or {}), 'kept': True}; d_['items'][x].pop('status', None); d_['items'][x].pop('trashedAt', None)
            rs._sort.save(rs.GIT_DIR, d_); left_ = [x for x in n_.get('paths') or [] if x not in keep_]
            if left_:
                cat['gitNotice'] = {**n_, 'paths': left_}
            else:
                cat.pop('gitNotice', None)
        rs.keep_owned(cat); rs._save(store)
        return {'clean': rs._sort.clean_view(cat), 'notice': cat.get('gitNotice')}
    if p.op in ('kalshi_state', 'kalshi_cfg', 'kalshi_bid', 'kalshi_skip', 'kalshi_check', 'kalshi_raise', 'kalshi_smaller'):   # 🎯 the real-bid door: his switch, caps, balance and the tickets waiting for his tap
        if p.op == 'kalshi_raise':   # 🔥 he took the streak offer: ONLY the exact value offered, inside the hard max
            off_ = rs._kb.raise_offer(cat.get('kalshiCfg'), cat.get('kalshiBids') or [])
            if not off_ or str(p.job or '') != f"{off_['to']:.2f}":
                raise rs.HTTPException(409, 'That offer is gone. Nothing was changed.')
            cat['kalshiCfg'] = rs._kb.cfg({**rs._kb.cfg(cat.get('kalshiCfg')), 'bidUsd': off_['to']}); rs.keep_owned(cat); rs._save(store)
            return rs._kalshi_view(cat)
        if p.op == 'kalshi_smaller':   # 🔁 a slip that got no quote, tried once more at half his per-bid cap — only on his tap
            f_k_ = next((f_ for f_ in cat.get('pobFolders') or [] if (f_.get('kalshi') or {}).get('id') == p.job), None)
            if not f_k_:
                raise rs.HTTPException(404, 'That ticket is gone.')
            new_, why_s_ = rs._kb.smaller(f_k_['kalshi'], cat.get('kalshiCfg'))
            if not new_:
                raise rs.HTTPException(409, why_s_)
            try:   # 🔒 two 'Try smaller' taps: the old ticket is claimed once, so only one smaller slip is ever sent
                rs._kb_claim(f"smaller:{p.job}")
            except rs.AlreadySent as e:
                raise rs.HTTPException(409, str(e))
            f_k_['kalshiTries'] = (list(f_k_.get('kalshiTries') or []) + [f_k_['kalshi']])[-4:]; f_k_['kalshi'] = new_
            await rs._kalshi_slip_send(cat, new_)
            rs.keep_owned(cat); rs._save(store)
            return {**rs._kalshi_view(cat), 'ticket': new_, 'pobFolders': rs._pob_view(cat)}
        if p.op == 'kalshi_cfg':
            cat['kalshiCfg'] = rs._kb.cfg(p.tools); rs.keep_owned(cat); rs._save(store)
        if p.op in ('kalshi_bid', 'kalshi_skip'):
            tk_ = next((f_.get('kalshi') for f_ in cat.get('pobFolders') or [] if (f_.get('kalshi') or {}).get('id') == p.job), None)
            if not tk_:
                raise rs.HTTPException(404, 'That ticket is gone.')
            if tk_.get('status') != 'waiting':
                raise rs.HTTPException(409, f"That ticket is already {tk_.get('status')}.")
            if p.op == 'kalshi_skip':
                tk_.update(status='skipped', doneAt=round(rs.time.time()))
            else:
                try:
                    await rs._kalshi_go(cat, tk_)
                except rs.AlreadySent as e:   # 🔒 a second tap: nothing sent
                    raise rs.HTTPException(409, str(e))
            rs.keep_owned(cat); rs._save(store)
            return {**rs._kalshi_view(cat), 'ticket': tk_, 'pobFolders': rs._pob_view(cat)}
        out_ = rs._kalshi_view(cat)
        kid_, pem_ = rs._kb.split_key(rs._ck.key_for(cat, 'kalshi', data_dir=rs.DATA_DIR) or '')
        if kid_ and p.op in ('kalshi_state', 'kalshi_check'):
            try:
                if await rs._kalshi_refresh(cat, kid_, pem_):
                    rs.keep_owned(cat); rs._save(store); out_ = {**rs._kalshi_view(cat), 'pobFolders': rs._pob_view(cat)}
                if p.op == 'kalshi_check' and p.job:
                    out_['ticket'] = next((f_.get('kalshi') for f_ in cat.get('pobFolders') or [] if (f_.get('kalshi') or {}).get('id') == p.job), None)
            except Exception as e:   # noqa: BLE001
                out_['checkErr'] = str(e)[:160]
            try:
                async with rs.httpx.AsyncClient(timeout=10) as h_:
                    out_['balance'] = await rs._kb.balance(h_, kid_, pem_)
            except Exception as e:   # noqa: BLE001
                out_['balanceErr'] = str(e)[:160]
        return out_
    if p.op == 'proof_prices':   # 💲 a proof's price before it starts
        return {'prices': await rs._proof_prices(cat)}
    if p.op.startswith('fork_'):   # 🍴 its own v1.01 of a stash build (owner 2026-11-10), kept in its git folder; Fee's desk sees every fork
        return await rs._fork_op(cat, p)
    if p.op in ('git_chat', 'git_state', 'git_read', 'sort_set', 'sort_on', 'sort_trash', 'sort_alert', 'proof_score', 'sort_bulk', 'sort_approve', 'sort_delete', 'git_connect', 'git_push', 'git_auto', 'git_drop', 'project_link', 'project_send', 'project_drop', 'project_copy', 'project_ask', 'project_edit', 'project_edit_send'):
        out_ = await rs._git_op(cat, p)
        if p.op not in ('git_state', 'git_read', 'sort_set', 'sort_on', 'sort_trash', 'sort_alert', 'proof_score', 'sort_bulk', 'sort_approve', 'sort_delete'):
            rs.keep_owned(cat); rs._save(store)
        return out_
    if p.op == 'all_work':   # 🗂 every agent's proofs and jobs, for the owner's desktop
        if not cat.get('ownerStaff') and not cat.get('isLeader'):
            raise rs.HTTPException(403, 'Owner only.')
        return rs._all_work(rs._load(), float(rs._stake.rung(rs._cpool.load(rs.POOL_PATH), await rs._pool_px())['top']))
    if p.op == 'desk_seat':   # 🎩 Sicario's only, its owner only: an agreed PoW goes to the real card's model seat
        if cat.get('handle') != 'sicarios' or not await rs._is_creator(rs._session_wallet(p.session or '')):
            raise rs.HTTPException(403, 'Only the owner runs the Sicario desk.')
        cat.setdefault('brainsCfg', {})['cardSeat'] = bool(p.on); rs.keep_owned(cat); rs._save(store)
        return {'cardSeat': bool(p.on)}
    if p.op == 'game_calls':   # 🏟 what this agent called on one game, and how each call graded. Its final fingerprint waits on these
        gid_ = str(p.job or '')
        on_ = [f for f in (cat.get('pobFolders') or [])[-40:] if any(str(g.get('id')) == gid_ for g in f.get('games') or [])]
        rows_ = [{'folder': f.get('id'), 'n': f.get('n'), 'pick': g.get('side') or g.get('short'), 'won': g.get('won'), 'score': g.get('score')} for f in on_ for g in (f.get('games') or []) if str(g.get('id')) == gid_]
        bids_ = [{'n': f.get('n'), **rs._kb.room_view(f['kalshi'])} for f in on_ if (f.get('kalshi') or {}).get('ticker')]   # 🎯 its real Kalshi bid on this game, live in the room
        return {'calls': rows_, 'bids': bids_, 'final': [x for f in on_ for x in f.get('final') or []][-2:], 'agent': cat.get('name')}
    if p.op == 'desk_seats':   # 🎩 the card's seats as they stand, for its owner's desk
        if cat.get('handle') != 'sicarios':
            raise rs.HTTPException(400, "Only Sicario's sits on the card.")
        try:
            async with rs.httpx.AsyncClient() as h_:
                r_ = await h_.get('http://127.0.0.1:5077/api/reputation/internal/sicario-want', headers={'x-feeless-internal': rs._internal_key_read()}, timeout=5)
            return {'seats': r_.json().get('seats') if r_.status_code == 200 else None}
        except (rs.httpx.HTTPError, ValueError):
            return {'seats': None}
    if p.op == 'desk_stop':   # ⏹ stop what OSSY and G4 are writing right now
        if cat.get('handle') != 'sicarios':
            raise rs.HTTPException(400, "Only Sicario's has local minds.")
        return {'stopped': rs.lm_stop(rs.time.time())}
    if p.op == 'desk_loop':   # 🎩 Sicario's only: keep filing proofs, or stop
        if cat.get('handle') != 'sicarios':
            raise rs.HTTPException(400, 'Only the Sicario desk runs this.')
        cat.setdefault('brainsCfg', {})['endless'] = bool(p.on); rs.keep_owned(cat); rs._save(store)
        return {'endless': bool(p.on)}
    if p.op == 'features':   # ✨ its Features folder: folders it has, memory, its fingerprint
        return {'firstList': rs._first_list(cat), 'workspaces': rs._ws_list(cat), 'memory': rs._feat.memory_view(cat), 'print': rs._print.build(cat, rs.time.time()), 'use': (cat.get('setup') or {}).get('use'), 'edge': rs._edge.rows(), 'edgeCats': rs._edge.CATEGORIES, 'indicators': rs._edge.indicator_list(), 'psFolders': cat.get('psFolders') or [], 'pocFolders': rs._poc_view(cat)}
    if p.op == 'feature_create':
        kind_ = rs._feat.clean_kind(p.text)
        if not kind_:
            raise rs.HTTPException(400, 'Pick a feature.')
        if kind_ == 'edge' and (cat.get('brainsCfg') or {}).get('kind') == 'general':   # 📈 indicators and the deep desk keep the trader focused, whatever model it runs
            raise rs.HTTPException(403, 'The Edge desk is for trader agents.')
        try:
            row_ = rs._feat.new_folder(cat, kind_, p.job, rs.time.time())
        except ValueError as e:
            raise rs.HTTPException(409, str(e))
        rs._ws_save(cat_id, rs._feat.new_doc(row_)); rs.keep_owned(cat); rs._save(store)
        return {'folder': row_, 'workspaces': rs._ws_list(cat)}
    if p.op == 'feature_delete':
        cat['workspaces'] = [w_ for w_ in cat.get('workspaces') or [] if w_.get('id') != p.text]
        if not any(f.get('ws') == p.text for f in cat.get('psFolders') or []) and not any(f.get('ws') == p.text for f in cat.get('pocFolders') or []):   # a filed proof keeps its page: this only takes the folder off the desk
            rs._ws_file(cat_id, p.text).unlink(missing_ok=True)
        rs.keep_owned(cat); rs._save(store)
        return {'workspaces': rs._ws_list(cat)}
    if p.op == 'ws_repo':   # 💾 a page its owner keeps: it joins this agent's own folder, sealed under its key in the Collective's store, and its own repo if one is linked. Only its owner reads it here
        if not rs._ws_load(cat_id, str(p.text or '')):
            raise rs.HTTPException(404, 'No such folder.')
        saved_ = [x for x in cat.get('savedPages') or [] if x != p.text]
        cat['savedPages'] = ([str(p.text)] + saved_)[:50] if p.on is not False else saved_
        rs.keep_owned(cat); rs._save(store)
        return {'saved': p.on is not False}
    if p.op == 'proof_hide':   # 🗂 a filed proof leaves its owner's folders; its score and record stay as filed, so hiding never improves an agent
        if p.job not in ('powFolders', 'popFolders', 'pobFolders', 'pocFolders', 'psFolders', 'poeFolders'):
            raise rs.HTTPException(400, 'No such proof list.')
        row_ = next((f_ for f_ in cat.get(p.job) or [] if isinstance(f_, dict) and f_.get('id') == p.text), None)
        if not row_:
            raise rs.HTTPException(404, 'That proof is not in this agent.')
        row_['hidden'] = p.on is not False; rs.keep_owned(cat); rs._save(store)
        return {'hidden': row_['hidden'], 'id': row_['id']}
    if p.op == 'live_feed':   # 📡 real numbers for a page that shows live data: the preview passes them into its frame
        return {'live': await rs._live_feed(cat)}
    if p.op == 'store_check':   # 📱 its latest page, checked the way App Review / Google Play would see it wrapped as an app (store_check)
        doc_ = rs._ws_load(cat_id, p.job)
        v_ = (doc_ or {}).get('versions') or []
        if not v_:
            raise rs.HTTPException(400, 'Build the page first, then check it for the stores.')
        res_ = await rs._store.check(rs._ws_placed(cat_id, v_[-1]['html']), device=True)
        res_['version'] = len(v_); doc_['storeCheck'] = {k_: res_[k_] for k_ in ('score', 'state', 'fails', 'warns', 'line', 'version', 'at')}; rs._ws_save(cat_id, doc_)
        return {'check': res_}
    if p.op == 'test_runs':   # 🧪 Proofs › Test bench: every test run on this desk, newest first, with its totals
        rows_ = rs._tbench.runs(rs.DATA_DIR, cat_id, 80)
        return {'runs': rows_, 'stats': rs._tbench.stats(rows_)}
    if p.op == 'test_run_file':   # 📄 one kept output of a test run (its code, its raw reply)
        text_ = rs._tbench.read_file(rs.DATA_DIR, cat_id, str(p.job or ''), str(p.text or ''))
        if text_ is None:
            raise rs.HTTPException(404, 'That test file is not kept here.')
        return {'text': text_[:400000]}
    if p.op == 'ws_version':   # 🗂 AGX-2: one saved version of a page, to set beside another (the drawer's compare). Read only; i is 1-based
        d_ = rs._ws_load(cat_id, p.text)
        if not d_:
            raise rs.HTTPException(404, 'No such folder.')
        v_ = d_.get('versions') or []
        if not v_ or p.i is None or not 1 <= int(p.i) <= len(v_):
            raise rs.HTTPException(400, f'Pick a version from 1 to {len(v_)}.')
        r_ = v_[int(p.i) - 1]
        return {'version': {'i': int(p.i), 'of': len(v_), 'by': r_.get('by'), 'at': r_.get('at'), 'lines': len(str(r_.get('html') or '').splitlines()), 'html': str(r_.get('html') or ''), 'preview': rs._feat.preview(rs._ws_placed(cat_id, r_.get('html') or ''))}}
    if p.op == 'ws_open':
        view_ = rs._ws_view(cat_id, p.text); view_['savedToRepo'] = p.text in (cat.get('savedPages') or []); view_['project'] = (cat.get('projectRepo') or {}).get('full')
        if p.ver is not None and p.ver == str(view_['versions']):
            for large_ in ('code', 'previousCode', 'preview'):
                view_.pop(large_, None)
        return {'doc': view_}
    if p.op == 'ws_cfg':   # ⚙ a Build folder's own steps
        doc_ = rs._ws_load(cat_id, p.job)
        if not doc_ or not isinstance(p.tools, dict):
            raise rs.HTTPException(400, 'Pick a folder and its settings.')
        doc_['cfg'] = rs._feat.build_cfg({'cfg': p.tools}); rs._ws_save(cat_id, doc_)
        return {'doc': rs._ws_view(cat_id, p.job)}
    if p.op == 'ws_approve':   # ✅ its owner approves the plan, or changes it, and only then is anything built
        doc_ = rs._ws_load(cat_id, p.job)
        if not doc_ or not (doc_.get('plan') or {}).get('plan') or doc_.get('busy'):
            raise rs.HTTPException(400, 'There is no plan waiting.')
        b_ = cat.get('brainsCfg') or {}
        if not b_.get('brains') or not (rs._lc.can_ask(b_) or rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR) or rs._pays_itself(cat)):
            raise rs.HTTPException(402, 'It needs model credit to do this.')
        note_ = str(p.text or '').strip()[:600]; pl_ = doc_['plan']; pl_['approved'] = True; ask_ = pl_.get('ask') or ''; go_ = f'{ask_}\nThe owner adds: {note_}' if note_ else ask_
        rs._feat.add_msg(doc_, 'you', note_ or 'Approved. Build it.', rs.time.time()); doc_['busy'] = {'at': round(rs.time.time()), 'to': pl_.get('to') or 'both', 'stage': 'build'}; doc_['stage'] = 'build'; rs._ws_save(cat_id, doc_)
        rs._ws_start(cat_id, p.job, str(pl_.get('to') or 'both'), go_, None)
        return {'doc': rs._ws_view(cat_id, p.job)}
    if p.op == 'poc_result':   # 💰 what a post really did, as its owner reports it
        f_ = next((x for x in cat.get('pocFolders') or [] if x.get('id') == p.job), None)
        if not f_:
            raise rs.HTTPException(400, 'Mark one of its PoCs.')
        link_ = str(p.text or '').strip()[:300]
        if link_ and not rs.re.match(r'^https://', link_):
            raise rs.HTTPException(400, 'A link starts with https://.')
        earned_ = max(0.0, min(1e7, rs._num(p.cap)))
        f_['result'] = {'link': link_, 'earnedUsd': round(earned_, 2), 'at': round(rs.time.time()), 'by': 'owner'}
        if earned_ > 0:
            f_['graded'] = 'right'
        rs._save(store)
        return {'pocFolders': rs._poc_view(cat)}
    if p.op == 'ws_source':   # 📂 which files of its owner's own repo this build continues from. They are read live at each build
        doc_ = rs._ws_load(cat_id, p.job); link_ = cat.get('projectRepo') or {}
        if not doc_:
            raise rs.HTTPException(404, 'No such folder.')
        allowed_ = link_.get('paths') or []
        if isinstance(p.tools, dict) and isinstance(p.tools.get('paths'), list):
            doc_['source'] = [x for x in p.tools['paths'] if x in allowed_][:rs._cg.PROJECT_READ_FILES]; rs._ws_save(cat_id, doc_)
        return {'source': doc_.get('source') or [], 'paths': allowed_, 'full': link_.get('full'), 'most': rs._cg.PROJECT_READ_FILES}
    if p.op == 'ws_keep':   # ✋ its owner stops here: the last page stands, and nothing is spent
        doc_ = rs._ws_load(cat_id, p.job)
        if not doc_ or doc_.get('busy') or not doc_.get('versions'):
            raise rs.HTTPException(400, 'There is no page to keep yet.')
        doc_.pop('unfinished', None); doc_['pending'] = False; doc_['stage'] = 'filed'; rs._feat.add_msg(doc_, 'you', f"Keep page {len(doc_['versions'])}.", rs.time.time()); rs._ws_save(cat_id, doc_)
        return {'doc': rs._ws_view(cat_id, p.job)}
    if p.op == 'pow_claim':   # ➕ COL-15: the owner traded a PoW proposal by hand somewhere else: his claim is kept on the folder, never a settled result until a send confirms it
        f_ = next((x for x in cat.get('powFolders') or [] if x.get('id') == p.job and x.get('propose')), None)
        if not f_:
            raise rs.HTTPException(400, 'Pick one of its proposals.')
        t_ = p.tools if isinstance(p.tools, dict) else {}
        link_ = str(t_.get('receipt') or '').strip(); venue_ = rs.re.sub(r'\s+', ' ', str(t_.get('venue') or '')).strip()[:40]
        try:
            usd_ = round(float(t_.get('resultUsd')), 2)
        except (TypeError, ValueError):
            raise rs.HTTPException(400, 'Say what it made or lost, in dollars (a minus for a loss).')
        if not venue_ or abs(usd_) > 1_000_000 or (link_ and not rs.re.match(r'^https://[^\s]{6,400}$', link_)):
            raise rs.HTTPException(400, 'Where you traded it, the result in dollars, and (optional) an https link to the receipt.')
        f_['manual'] = {'venue': venue_, 'receipt': link_ or None, 'resultUsd': usd_, 'note': str(p.text or '').strip()[:200], 'at': round(rs.time.time()), 'status': 'claim'}
        rs.keep_owned(cat); rs._save(store)
        return {'powFolders': (cat.get('powFolders') or [])[::-1]}
    if p.op == 'media_models':   # 🎬 the picker: which image / video models run on the owner's linked OpenRouter / fal.ai / Replicate (+ the viral presets)
        linked = {r['provider'] for r in rs._ck.public(cat) if r.get('saved') and r['provider'] in rs._mg.PROVIDERS}
        return {**rs._mg.catalog(linked, rs._media_house(cat)), 'houseLeftUsd': round(max(0.0, rs._mg.HOUSE_DAILY_USD - rs._media_house_spent()), 2) if rs._media_house(cat) else None}
    if p.op == 'media_make':   # 🎬 one image or video in a PoC folder, on the owner's own key; the page polls ws_open for its state
        doc_ = rs._ws_load(cat_id, p.job)
        if not doc_ or doc_.get('kind') != 'content':
            raise rs.HTTPException(400, 'Images and video are made in a PoC folder.')
        linked = {r['provider'] for r in rs._ck.public(cat) if r.get('saved') and r['provider'] in rs._mg.PROVIDERS}
        t_ = p.tools if isinstance(p.tools, dict) else {}
        house_ = rs._media_house(cat)
        if t_.get('swap'):   # 🎭 a clip in this folder + its character → one swap on the owner's own fal.ai key
            return await rs._media_swap(cat_id, p.job, doc_, t_, linked, p.text)
        try:
            text_, want_model, want_kind = (rs._mg.fill(str(t_['preset']), p.text) if t_.get('preset') else (p.text, str(t_.get('model') or '') or None, str(t_.get('kind') or '')))
            mid_, prov_, model_, kind_ = rs._mg.choose(want_model, want_kind, linked, house_)
            prompt_ = rs._mg.clean_prompt(text_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        on_house = prov_ == 'openrouter' and 'openrouter' not in linked
        if on_house and rs._media_house_spent() + float(rs._mg.MODELS[mid_][5] or 0.5) > rs._mg.HOUSE_DAILY_USD:
            raise rs.HTTPException(429, f'FEELESS\'s ${rs._mg.HOUSE_DAILY_USD:.0f} a day for media is used up. Link your own OpenRouter key, or try tomorrow.')
        img_ = str(t_.get('img') or '').strip()   # 👤 a made image becomes the video's first frame (owner 2026-11-12: "make this img an actual guy")
        if not img_ and kind_ == 'video' and (doc_.get('character') or {}).get('mid') and not t_.get('noChar'):
            img_ = str(doc_['character']['mid'])   # the folder's character leads its videos unless this make says no
        from_ = None
        if img_:
            smd_ = (rs._media_msg(doc_, img_) or {}).get('media') or {}
            if smd_.get('status') != 'done' or smd_.get('kind') != 'image' or not str(smd_.get('url') or '').startswith('/api/cats/media/'):
                raise rs.HTTPException(400, 'Pick a finished image from this folder to start from.')
            if kind_ != 'video':
                raise rs.HTTPException(400, 'An image starts a video.')
            try:
                rs._mg.i2v_model(mid_)
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            from_ = {'mid': img_, 'url': smd_['url']}
        refs_ = []   # 👤 POC-PLAY item 6: an IMAGE keeps a reference's exact look — a picked reference, else the folder's character
        if kind_ == 'image':
            want_ = [str(x) for x in (t_.get('refs') or ([t_['ref']] if t_.get('ref') else [])) if x][:3]
            if not want_ and (doc_.get('character') or {}).get('mid') and not t_.get('noChar'):
                want_ = [str(doc_['character']['mid'])]
            for r_ in want_:
                rmd_ = (rs._media_msg(doc_, r_) or {}).get('media') or {}
                if rmd_.get('status') != 'done' or rmd_.get('kind') != 'image' or not str(rmd_.get('url') or '').startswith('/api/cats/media/'):
                    raise rs.HTTPException(400, 'A reference must be a finished picture in this folder.')
                refs_.append({'mid': r_, 'url': rmd_['url']})
            if refs_ and prov_ != 'openrouter':
                raise rs.HTTPException(400, 'Only the OpenRouter picture models keep a reference. Pick Nano Banana, Gemini Flash Image or GPT-5 Image.')
        if sum(1 for m in doc_.get('messages') or [] if (m.get('media') or {}).get('status') in ('queued', 'running')) >= 3:
            raise rs.HTTPException(429, 'Three are already making. Wait for one to finish.')
        jid = 'm' + rs.uuid.uuid4().hex[:12]; row_ = rs._mg.MODELS[mid_]
        doc_['messages'] = list(doc_.get('messages') or []) + [{'by': 'Media', 'text': prompt_, 'at': round(rs.time.time()),
            'media': {'id': jid, 'kind': kind_, 'provider': prov_, 'model': model_, 'modelId': mid_, 'label': row_[3], 'usd': row_[5], 'prompt': prompt_, 'status': 'queued', 'at': round(rs.time.time()),
                      **({'house': True} if on_house else {}), **({'preset': str(t_['preset'])} if t_.get('preset') else {}), **({'fromImg': from_} if from_ else {}), **({'refs': refs_} if refs_ else {})}}]
        if on_house:
            rs._media_house_add(float(row_[5] or 0.5))   # booked up front at the list price, so two clicks can't both slip under the cap
        rs._ws_save(cat_id, doc_)
        rs.asyncio.create_task(rs._media_run(cat_id, p.job, jid))
        return {'doc': rs._ws_view(cat_id, p.job)}
    if p.op == 'media_clip':   # 🎭 V2V (owner 2026-11-14 "wire the fal vid to vid"): the owner's own clip lands in the PoC folder, ready to swap a character into
        doc_ = rs._ws_load(cat_id, p.job)
        if not doc_ or doc_.get('kind') != 'content':
            raise rs.HTTPException(400, 'Clips go in a PoC folder.')
        if not (p.tools or {}).get('rights'):
            raise rs.HTTPException(400, 'Tick that the clip is yours, or that you have the rights to use it.')
        try:
            raw_, ext_ = rs._pplay.decode(p.text)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        if rs._pplay.kind_of(ext_) != 'video':
            raise rs.HTTPException(400, 'Pick a video clip (MP4, MOV or WebM).')
        jid = 'm' + rs.uuid.uuid4().hex[:12]; f_ = rs._media_dir() / cat_id / f'{jid}.{ext_}'
        f_.parent.mkdir(parents=True, exist_ok=True); f_.write_bytes(raw_)
        secs_, fps_ = await rs._clip_len(f_)
        if secs_ is None:
            f_.unlink(missing_ok=True); raise rs.HTTPException(400, 'That clip could not be read. Export it again as an MP4.')
        if secs_ > rs._mg.MAX_CLIP_S + 0.5:
            f_.unlink(missing_ok=True); raise rs.HTTPException(400, f'That clip is {secs_:.0f} s. Trim it to {rs._mg.MAX_CLIP_S} s or less first.')
        name_ = str((p.tools or {}).get('name') or 'Your clip')[:60]
        doc_['messages'] = list(doc_.get('messages') or []) + [{'by': 'Media', 'text': name_, 'at': round(rs.time.time()),
            'media': {'id': jid, 'kind': 'video', 'provider': 'upload', 'model': 'your clip', 'label': name_, 'prompt': name_, 'status': 'done', 'clip': True,
                      'secs': round(secs_, 2), 'fps': round(fps_ or 30, 2), 'rights': True, 'url': f'/api/cats/media/{cat_id}/{jid}.{ext_}', 'kept': True, 'bytes': len(raw_), 'at': round(rs.time.time())}}]
        rs._ws_save(cat_id, doc_)
        return {'doc': rs._ws_view(cat_id, p.job)}
    if p.op == 'media_play':   # 🎨 POC-PLAY: a playground edit (made free in the browser) filed into the PoC folder as a NEW version; the original stays
        doc_ = rs._ws_load(cat_id, p.job)
        if not doc_ or doc_.get('kind') != 'content':
            raise rs.HTTPException(400, 'Playground edits live in a PoC folder.')
        try:
            raw_, ext_ = rs._pplay.decode(p.text)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        t_ = p.tools or {}; src_ = str(t_.get('from') or '')[:40]
        smd_ = ((rs._media_msg(doc_, src_) or {}).get('media') or {}) if src_ else {}
        jid = 'm' + rs.uuid.uuid4().hex[:12]; now_ = round(rs.time.time())
        (rs._media_dir() / cat_id).mkdir(parents=True, exist_ok=True); (rs._media_dir() / cat_id / f'{jid}.{ext_}').write_bytes(raw_)
        prompt_ = str(smd_.get('prompt') or t_.get('note') or 'Made in the playground')[:300]
        msg_ = {'by': 'Media', 'text': prompt_, 'at': now_, 'media': {'id': jid, 'kind': rs._pplay.kind_of(ext_), 'provider': 'playground', 'model': 'Excalidraw board' if t_.get('template') == 'wire' else 'Konva canvas' if rs._pplay.kind_of(ext_) == 'image' else 'Konva canvas + browser recorder', 'label': rs._pplay.version_label(doc_.get('messages'), t_.get('template')),
                'usd': 0, 'prompt': prompt_, 'status': 'queued', 'at': now_, **({'from': src_} if smd_ else {}), **({'template': t_['template']} if t_.get('template') in rs._pplay.TEMPLATES else {})}}
        rs._media_set(cat_id, p.job, jid, keep=msg_, status='done', url=f'/api/cats/media/{cat_id}/{jid}.{ext_}', doneAt=now_)   # also joins a filed PoC of this folder
        return {'doc': rs._ws_view(cat_id, p.job), 'id': jid}
    if p.op == 'media_ref':   # 📎 POC-PLAY item 6: a reference picture / video (upload or https link) joins this PoC folder, $0, nothing made
        doc_ = rs._ws_load(cat_id, p.job)
        if not doc_ or doc_.get('kind') != 'content':
            raise rs.HTTPException(400, 'References live in a PoC folder.')
        src_ = str(p.text or '').strip(); t_ = p.tools if isinstance(p.tools, dict) else {}
        if rs.re.match(r'^https://', src_):
            try:
                await rs._cp.public_url(src_)
                async with rs.httpx.AsyncClient(timeout=20, follow_redirects=False) as h_:
                    r_ = await h_.get(src_, headers={'User-Agent': 'FEELESS-reference/1.0'})
                ct_ = r_.headers.get('content-type', '').split(';')[0].strip().lower()
                if r_.status_code != 200 or not rs.re.fullmatch(r'image/(png|jpeg|webp)|video/(mp4|webm)', ct_):
                    raise ValueError('That link is not a PNG, JPG, WebP, MP4 or WebM file.')
                if len(r_.content) > rs._pplay.MAX_CLIP:
                    raise ValueError('That file is too big.')
                src_ = f'data:{ct_};base64,{rs.base64.b64encode(r_.content).decode()}'
            except (ValueError, rs.httpx.HTTPError) as e:
                raise rs.HTTPException(400, str(e) if isinstance(e, ValueError) else 'That link did not answer.')
        try:
            raw_, ext_ = rs._pplay.decode(src_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        jid = 'm' + rs.uuid.uuid4().hex[:12]; now_ = round(rs.time.time()); kind_ = rs._pplay.kind_of(ext_)
        (rs._media_dir() / cat_id).mkdir(parents=True, exist_ok=True); (rs._media_dir() / cat_id / f'{jid}.{ext_}').write_bytes(raw_)
        note_ = rs.re.sub(r'\s+', ' ', str(t_.get('note') or '')).strip()[:200] or ('Your reference' if not str(p.text).startswith('https://') else f'Reference from {str(p.text)[8:60]}')
        doc_['messages'] = list(doc_.get('messages') or []) + [{'by': 'Media', 'text': note_, 'at': now_, 'media': {'id': jid, 'kind': kind_, 'provider': 'reference', 'model': 'Reference', 'label': '📎 Reference',
            'usd': 0, 'prompt': note_, 'status': 'done', 'ref': True, 'url': f'/api/cats/media/{cat_id}/{jid}.{ext_}', 'kept': True, 'bytes': len(raw_), 'at': now_, 'doneAt': now_}}]
        rs._ws_save(cat_id, doc_)
        return {'doc': rs._ws_view(cat_id, p.job), 'id': jid}
    if p.op == 'media_char':   # 👤 keep a made image as this folder's CHARACTER: every video from here starts from him (empty text clears him)
        doc_ = rs._ws_load(cat_id, p.job)
        if not doc_ or doc_.get('kind') != 'content':
            raise rs.HTTPException(400, 'Characters live in a PoC folder.')
        mid_ = str(p.text or '').strip()
        if not mid_:
            doc_.pop('character', None)
        else:
            smd_ = (rs._media_msg(doc_, mid_) or {}).get('media') or {}
            if smd_.get('status') != 'done' or smd_.get('kind') != 'image' or not smd_.get('url'):
                raise rs.HTTPException(400, 'Pick a finished image.')
            doc_['character'] = {'mid': mid_, 'url': smd_['url'], 'prompt': str(smd_.get('prompt') or '')[:200], 'at': round(rs.time.time())}
        rs._ws_save(cat_id, doc_)
        return {'doc': rs._ws_view(cat_id, p.job)}
    if p.op == 'ws_build':   # 🛠 its minds work in the background; the page polls ws_open
        doc_ = rs._ws_load(cat_id, p.job)
        text_ = str(p.text or '').strip()[:12000]
        said_ = text_; left_ = rs._feat.unfinished_of(doc_)
        if left_ and left_.get('ask') and (p.finish or rs._feat.is_retry(text_)):   # "finish it" and "try again" mean the ask that stopped, not those words
            said_ = 'Finish it.' if p.finish else text_; text_ = left_['ask']
            if left_.get('region') and not isinstance(p.tools, dict):
                p.tools = {'region': left_['region']}
        if not doc_ or not text_:
            raise rs.HTTPException(400, 'Say what to make.')
        if doc_.get('busy'):
            raise rs.HTTPException(409, 'It is still working on the last one.')
        back_ = rs._feat.go_back_to(text_, len(doc_.get('versions') or [])) if doc_.get('kind') == 'build' else None
        if back_:   # "go back and retry my request from page 5" is done by code, never handed to a model to guess at
            asked_ = rs._ws_rewind(cat, cat_id, doc_, back_[0], rs.time.time()); rs._ws_save(cat_id, doc_); rs.keep_owned(cat); rs._save(store)
            if not (back_[1] and asked_):
                return {'doc': {**rs._ws_view(cat_id, p.job), 'restore': {'text': asked_, 'at': rs.time.time()}}}
            said_ = text_ = asked_
        b_ = cat.get('brainsCfg') or {}
        if not b_.get('brains') or not (rs._lc.can_ask(b_) or rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR) or rs._pays_itself(cat)):
            raise rs.HTTPException(402, 'It needs model credit to do this.')
        files_ = [rs._af.find(cat, i) for i in ((p.tools or {}).get('files') or [])[:rs._feat.ATTACH_MAX]] if isinstance(p.tools, dict) else []
        if any(files_):
            doc_['attached'] = [{'id': f['id'], 'name': f.get('name')} for f in files_ if f]
        rs._feat.add_msg(doc_, 'you', said_, rs.time.time()); doc_.pop('unfinished', None); doc_['complete'] = False; doc_['pending'] = doc_.get('kind') == 'build'; doc_['busy'] = {'at': round(rs.time.time()), 'to': str(p.to or 'both'), 'stage': 'answer' if doc_.get('kind') != 'build' else 'build' if doc_.get('versions') else 'research'}   # a PoC or research answers; only a build writes a page
        rs._ws_save(cat_id, doc_)
        rs._ws_start(cat_id, p.job, str(p.to or 'both'), text_, (p.tools or {}).get('region') if isinstance(p.tools, dict) else None)
        return {'doc': rs._ws_view(cat_id, p.job)}
    if p.op == 'ws_rewind':   # ↩ a page chosen in the chat: its later work and talk are cleared, and the next request goes back in the box
        doc_ = rs._ws_load(cat_id, str(p.job or ''))
        if not doc_ or doc_.get('busy'):
            raise rs.HTTPException(409, 'It is still working on the last one.')
        try:
            n_ = int(p.text)
        except (TypeError, ValueError):
            raise rs.HTTPException(400, 'Pick a page.')
        if not 1 <= n_ <= len(doc_.get('versions') or []):
            raise rs.HTTPException(400, 'That page is not there.')
        asked_ = rs._ws_rewind(cat, cat_id, doc_, n_, rs.time.time()); rs._ws_save(cat_id, doc_); rs.keep_owned(cat); rs._save(store)
        return {'doc': {**rs._ws_view(cat_id, p.job), 'restore': {'text': asked_, 'at': rs.time.time()}}}
    if p.op == 'memory':   # 🧠 start fresh, let its lead mind clean it, or tell it about you
        how_ = str(p.job or '')
        if how_ == 'fresh':
            rs._feat.memory_fresh(cat, rs.time.time())
        elif how_ == 'personal':
            cat['personal'] = str(p.text or '').strip()[:1500]
        elif how_ == 'clean':
            brains_ = (cat.get('brainsCfg') or {}).get('brains') or []
            if not brains_:
                raise rs.HTTPException(400, 'It has no mind to clean with.')
            cat['memoryCleanedAt'] = round(rs.time.time())
            rs.asyncio.create_task(rs._sort_cloud(cat_id, brains_[0]))
        else:
            raise rs.HTTPException(400, 'Fresh, clean or personal.')
        rs.keep_owned(cat); rs._save(store)
        return {'memory': rs._feat.memory_view(cat)}
    if p.op == 'poc':   # 📣 a Proof of Content: both minds read what is trending, blind, then it files
        if not (cat.get('brainsCfg') or {}).get('brains'):
            raise rs.HTTPException(400, 'It needs a mind first.')
        if cat_id in rs._POC_BUSY:
            raise rs.HTTPException(409, 'A PoC is already being filed.')
        if (room_ := rs._proof_room(cat, cat_id, 'PoC')):
            raise rs.HTTPException(409, room_)
        topic_ = str(p.text or '').strip()[:120]
        rs._POC_BUSY.add(cat_id); rs.asyncio.create_task(rs._poc_file(cat_id, topic_, str(p.job or '') or None))
        return {'ok': True, 'pocFolders': rs._poc_view(cat)}
    if p.op == 'week_plans':   # 🗓 its minds write 3 different weeks (launch / drip / hype) for this PoC folder; each files as a PoC
        if not (cat.get('brainsCfg') or {}).get('brains'):
            raise rs.HTTPException(400, 'It needs a mind first.')
        doc_ = rs._ws_load(cat_id, str(p.job or ''))
        if not doc_ or doc_.get('kind') != 'content':
            raise rs.HTTPException(400, 'Week plans live in a PoC folder.')
        if cat_id in rs._WEEK_BUSY:
            raise rs.HTTPException(409, 'Its minds are already writing week plans.')
        rs._WEEK_BUSY.add(cat_id); rs.asyncio.create_task(rs._week_file(cat_id, doc_['id'], str(p.text or '').strip()[:120]))
        return {'ok': True}
    if p.op == 'week_save':   # 🗓 the owner moved / edited posts on the board: the plan is saved checked; the minds' original stays as weekOrig
        rows_ = cat.get('pocFolders') or []; f_ = next((x for x in rows_ if x.get('id') == str(p.job or '') and x.get('week')), None)
        if not f_:
            raise rs.HTTPException(404, 'No such week plan.')
        try:
            plan_ = rs._wk.clean(p.cap if isinstance(p.cap, dict) else {}, [m.get('id') for m in f_.get('media') or []])
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        f_.setdefault('weekOrig', f_['week'])
        f_['week'] = {**plan_, 'style': f_['week'].get('style'), 'edited': round(rs.time.time())}
        rs.keep_owned(cat); rs._save(store)
        return {'pocFolders': rs._poc_view(cat)}
    if p.op in ('postiz_channels', 'week_post'):   # 📮 POC-PLAY item 8: the picked week goes out through the owner's OWN Postiz (official OAuth channels)
        if internal_ and p.op == 'week_post':
            raise rs.HTTPException(403, 'Only the owner sends a week out.')
        if p.op == 'week_post' and cat_id in rs._POST_BUSY:
            raise rs.HTTPException(409, 'This week is already going out.')
        saved_ = rs._ck.key_for(cat, 'postiz', data_dir=rs.DATA_DIR)
        if not saved_:
            raise rs.HTTPException(400, 'Save your Postiz API key on this agent first (Keys › Postiz). Postiz holds the X / Instagram / TikTok logins, never FEELESS.')
        try:
            base_, key_ = rs._pz.split_key(saved_)
            if base_ != rs._pz.CLOUD:
                await rs._cp.public_url(base_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        if p.op == 'week_post':
            rs._POST_BUSY.add(cat_id)
        try:
            return await rs._week_post(cat_id, cat, p, base_, key_)
        finally:
            rs._POST_BUSY.discard(cat_id)
    if p.op == 'poc_answer':   # 🧾 what the minds wrote in this folder's chat becomes its filed proof, so it can be marked and sent
        doc_ = rs._ws_load(cat['id'], str(p.job or ''))
        calls_ = rs._feat.answers_of(doc_ or {}, owner_names=('You', 'you', 'owner'))
        if not calls_:
            raise rs.HTTPException(400, 'No answer from its minds in this folder yet.')
        rows_ = list(cat.get('pocFolders') or [])
        media_ = rs._poc_media(doc_)   # 🎬 the images / video made in this folder ride on the filed proof (owner 2026-11-12: Bishop filed with nothing to see)
        rows_.append({'id': f'poc{int(rs.time.time())}', 'ws': doc_.get('id'), 'n': rs._next_n(rows_), 'kind': 'PoC', 'at': round(rs.time.time()), 'status': 'closed', 'paper': True, 'topic': str(doc_.get('name') or 'Its answer')[:120], 'calls': calls_, 'cost': doc_.get('cost'), 'fromChat': True, **({'media': media_} if media_ else {})})
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"📣 PoC #{len(rows_)} “{str(doc_.get('name') or 'Its answer')[:40]}” is filed from its folder chat" + (f' with {len(media_)} made file{"s" if len(media_) > 1 else ""}' if media_ else '') + '. Nothing was posted.', 'at': rs.time.time(), 'open': 'features'}])[-200:]
        rs._feed_push(cat['id'], {'tone': 'done', 'kind': 'PoC', 'text': f"PoC filed: {str(doc_.get('name') or 'its folder')[:40]}", 'ref': doc_.get('id')})
        cat['pocFolders'] = rows_[-60:]; rs.keep_owned(cat); rs._save(store)
        return {'pocFolders': rs._poc_view(cat)}
    if p.op == 'proof_cfg':   # 🔁 ask first, or just do it, per kind of proof
        try:
            cfg_ = rs._plan.set_auto(cat, p.text, bool(p.on))
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs.keep_owned(cat); rs._save(store)
        return {'proofCfg': cfg_}
    if p.op == 'ps_mark':   # ✅ only its owner knows if the page works
        f_ = next((x for x in cat.get('psFolders') or [] if x.get('id') == p.job), None)
        if not f_ or p.text not in ('right', 'wrong'):
            raise rs.HTTPException(400, 'Mark one of its PoStatics.')
        f_['graded'] = p.text
        why_ = ' '.join(str((p.tools or {}).get('why') or '').split())[:280]   # 🗂 AGX-2: the owner's reason travels with the grade (the next build reads it from the chat, not from here)
        if why_:
            f_['gradeWhy'] = why_
        elif 'why' in (p.tools or {}):
            f_.pop('gradeWhy', None)
        rs._save(store)
        return {'poeFolders': (cat.get('poeFolders') or [])[::-1], 'psFolders': (cat.get('psFolders') or [])[::-1]}
    if p.op == 'ws_complete':
        doc_ = rs._ws_load(cat_id, p.job)
        filed_ = [f for f in cat.get('psFolders') or [] if f.get('ws') == p.job]
        if not doc_ or doc_.get('kind') != 'build' or doc_.get('busy') or doc_.get('pending') or not filed_ or filed_[-1].get('graded') != 'right' or any(not f.get('graded') for f in filed_):
            raise rs.HTTPException(400, 'Mark every filed page, and mark the latest one working before completing this proof.')
        doc_['complete'] = True; rs._ws_save(cat_id, doc_)
        return {'doc': rs._ws_view(cat_id, p.job)}
    if p.op == 'poc_mark':   # ✅ its owner says how it did: only they know, once it is out
        f_ = next((x for x in cat.get('pocFolders') or [] if x.get('id') == p.job), None)
        if not f_ or p.text not in ('right', 'wrong'):
            raise rs.HTTPException(400, 'Mark one of its PoCs.')
        f_['graded'] = p.text; rs._save(store)
        return {'pocFolders': rs._poc_view(cat)}
    if p.op == 'convo':   # 💬 Collective convos: on or off, its owner's call
        cat['convo'] = {**(cat.get('convo') or {}), 'on': bool(p.on)}
        rs._save(store)
        return {'ok': True, 'convo': cat['convo']}
    if p.op == 'face':   # 🎭 its character: a look only, no engine reads it
        id_ = rs._face.clean_id(p.text)
        if not id_:
            raise rs.HTTPException(400, 'Pick one of the characters.')
        cat['face'] = {'id': id_, 'at': round(rs.time.time())}
        rs._save(store)
        return {'ok': True, 'face': cat['face']}
    if p.op == 'rename':   # 🪪 a name changes once every 7 days, staff any time
        name_ = str(p.text or '').strip()[:32]
        if len(name_) < 2:
            raise rs.HTTPException(400, 'A name needs at least 2 characters.')
        ok_, rec_, why_ = rs._nl.check(cat.get('nameLock'), rs.owner_wallet(cat) or cat_id, name_, await rs._session_staff(p.session or ''))
        if not ok_:
            raise rs.HTTPException(429, why_)
        cat['nameLock'] = rec_; cat['name'] = name_
        rs._save(store)
        return {'ok': True, 'name': name_, 'nameLeftS': rs._nl.left_s(rec_)}
    if p.op == 'live_key':   # 🔴 its owner's own channel: the key is sealed at once and never sent back
        plat_ = str(p.text or '').lower()
        keys_ = cat.setdefault('liveKeys', {})
        if p.on is False:
            keys_.pop(plat_, None)
        else:
            try:
                server_ = rs._al.check_server(plat_, p.user); key_ = rs._al.check_key(p.secret)
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            keys_[plat_] = {'server': server_, 'key': rs._ck.seal(key_, cat_id), 'at': round(rs.time.time())}
        rs._save(store)
        return {'ok': True, 'liveKeys': rs._al.owner_view(keys_)}
    if p.op == 'share':   # 🤝 opportunity 2: its owner SIGNS to let it send pct % of each winning trade's profit to the colony wallet → the colony airdrops back
        if p.on:
            pct_ = rs._colony.share_pct(p.cap)
            if not pct_:
                raise rs.HTTPException(400, f'Pick a share: {", ".join(f"{x}%" for x in rs._colony.SHARE_PCTS)}.')
            if not rs.share_ok(cat_id, pct_, p.ts, p.sig, rs.owner_wallet(cat) or rs._session_wallet(p.session or '')):
                raise rs.HTTPException(401, 'Sign the share with your wallet (one signature, no transaction).')
            cat['colonyShare'] = {'on': True, 'auto': True, 'pct': pct_, 'at': rs.time.time(), 'by': rs.owner_wallet(cat) or rs._session_wallet(p.session or '')}
        else:
            cat['colonyShare'] = {**(cat.get('colonyShare') or {}), 'on': False, 'offAt': rs.time.time()}   # turning it off needs no signature
        rs.keep_owned(cat); rs._save(store)
        return {'colonyShare': cat['colonyShare']}
    if p.op == 'hive':   # 🐝 COLONIZE on / off and its pace (least usage: one coin every N minutes)
        cat['hive'] = {'on': bool(p.on), 'every': rs._hv.every_s(p.cap if p.cap is not None else (cat.get('hive') or {}).get('every', 300))}
        if p.on and cat.get('handle') == 'sicarios':   # 🎩 Auto-collect on Sicario's: its PoWs go to the card's seats until they are full
            cat.setdefault('brainsCfg', {})['cardSeat'] = True
        rs.keep_owned(cat); rs._save(store)
        return {'hive': cat['hive'], 'hiveRun': cat.get('hiveRun') or {}}
    if p.op == 'duel':   # ⚔ AGX-4: both minds answered one ask; the owner taps the better one → a right-vs-wrong pair in COMP's dataset (the stash)
        tid_ = str(p.text or '')[:20]; job_ = next((j for j in cat.get('jobs') or [] if j.get('id') == tid_), None)
        ms_ = (job_ or {}).get('minds') or []
        if str(p.job) not in ('0', '1') or len(ms_) != 2 or not all(str(m.get('answer') or '').strip() for m in ms_):
            raise rs.HTTPException(400, 'A duel needs a finished ask both minds answered, and a winner: A or B.')
        won_ = int(p.job); had_ = (cat.get('duels') or {}).get(tid_)
        if had_ is not None:   # a pick is final: it is already a training pair
            return {'duels': cat.get('duels') or {}, 'stashed': False}
        pair_ = {'prompt': str(job_.get('request') or '')[:1500], 'chosen': str(ms_[won_].get('answer'))[:3000], 'rejected': str(ms_[1 - won_].get('answer'))[:3000],
                 'chosenModel': str(ms_[won_].get('model') or '').split('/')[-1][:60], 'rejectedModel': str(ms_[1 - won_].get('model') or '').split('/')[-1][:60], 'at': round(rs.time.time())}
        stashed_ = await rs.asyncio.to_thread(rs._stash.put, rs.STASH_DIR, f"duel:{cat['id']}:{tid_}", 'Duels', 'chat', cat['id'], 'won', pair_['prompt'][:160] or 'a duel', rs.json.dumps(pair_).encode())
        cat['duels'] = {**{k: v for k, v in (cat.get('duels') or {}).items() if any(j.get('id') == k for j in cat.get('jobs') or [])}, tid_: won_}
        rs.keep_owned(cat); rs._save(store)
        return {'duels': cat['duels'], 'stashed': bool(stashed_)}
    if p.op == 'rate':   # 👍 / 👎 a finished request — the engine files it into both minds' memory on its next pass
        tid_, r_ = str(p.text or '')[:20], str(p.job or '')
        if r_ not in ('up', 'down') or not any(j.get('id') == tid_ for j in cat.get('jobs') or []):
            raise rs.HTTPException(400, 'Rate a finished request: up or down.')
        cat['jobRates'] = {**{k: v for k, v in (cat.get('jobRates') or {}).items() if any(j.get('id') == k for j in cat.get('jobs') or [])}, tid_: r_}
        rs.keep_owned(cat); rs._save(store)
        return {'jobRates': cat['jobRates']}
    if p.op == 'cap':
        v = max(0.005, min(rs._task_cap_max(), float(p.cap or rs.TASK_CAP_DEFAULT)))
        cat['taskCap'] = round(v, 4); rs.keep_owned(cat); rs._save(store)   # kept: the next save laid the old remembered cap back over it (owner 2026-10-31: "$0.25 doesn't change")
        return {'cap': cat['taskCap']}
    if p.op == 'login':   # 🔑 the owner's own login for the site its window asked about: sealed in its vault, handed to the live window, the window continues
        t_ = (w or {}).get('task') or {}; wins_ = t_.get('windows') or []
        i_ = int(p.i or 0)
        if not (0 <= i_ < len(wins_)) or (wins_[i_].get('human') or {}).get('kind') != 'login':
            raise rs.HTTPException(400, 'That window is not asking for a login.')
        site_ = wins_[i_]['human'].get('site') or ''
        if not (p.user or '').strip() or not (p.secret or ''):
            raise rs.HTTPException(400, 'Type the username and the password.')
        try:
            rs._cv.put_login(cat, site_, p.user.strip(), p.secret, data_dir=rs.DATA_DIR); rs.keep_owned(cat); rs._save(store)
        except (ValueError, RuntimeError) as e:
            raise rs.HTTPException(400, str(e)[:120])
        wins_[i_]['pw'] = {'site': site_, 'user': p.user.strip()[:120], 'pw': p.secret}
        ev_ = (w or {}).get('events', {}).get(i_)
        if ev_:
            w['go'][i_] = True; ev_.set()
        return {'ok': True, 'site': site_}
    if p.op == 'save_login':   # 🔐 the credentials drawer: site + username + password, sealed; a window waiting on that site gets it and goes on
        try:
            rs._cv.put_login(cat, p.text or '', (p.user or '').strip(), p.secret or '', data_dir=rs.DATA_DIR); rs.keep_owned(cat); rs._save(store)
        except (ValueError, RuntimeError) as e:
            raise rs.HTTPException(400, str(e)[:120])
        site_ = rs._cv.site_of(p.text or '')
        rs.vault_log(cat, 'saved', site_); rs.keep_owned(cat); rs._save(store)
        for win_ in ((w or {}).get('task') or {}).get('windows') or []:
            if (win_.get('human') or {}).get('kind') == 'login' and win_['human'].get('site') == site_ and (w or {}).get('events', {}).get(win_['i']):
                win_['pw'] = {'site': site_, 'user': (p.user or '').strip()[:120], 'pw': p.secret}
                w['go'][win_['i']] = True; w['events'][win_['i']].set()
        return {'ok': True, 'site': site_, 'logins': rs._cv.public_logins(cat)}
    if p.op == 'signin_open':   # 🔓 a live window for the OWNER to sign in to a site by hand (its cookies are kept on save)
        try:
            url_ = p.text if str(p.text or '').startswith('http') else f'https://{str(p.text or "").strip()}'
            rs._cp.check_url(url_); site_ = rs._cv.site_of(url_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e)[:120])
        if not rs.os.environ.get('STEEL_API_KEY'):
            raise rs.HTTPException(400, 'Signed-in sites need the Steel browser (STEEL_API_KEY) — it is the one that keeps a sign-in.')
        await rs._signin_close(cat_id)
        w_ = rs._warm_for(cat_id, site_)
        if w_ and not w_.get('busy'):   # 🔥 the window it already cleared, not a new one that would be checked again
            rs._WARM.pop(cat_id, None)
            rs._SIGNIN[cat_id] = {'sid': w_['sid'], 'site': site_, 'page': None, 'at': w_['at'], 'connect': w_['connect'], 'live': w_['live'], 'hand': w_['hand']}
            return {'live': w_['hand'] or w_['live'], 'site': site_}
        await rs._warm_close(cat_id)
        async with rs.httpx.AsyncClient(timeout=30) as http:
            try:
                s_ = await rs._cb._steel(http, rs.os.environ, rs._site_ctx(cat))
            except Exception as e:
                raise rs.HTTPException(502, f'The browser did not open ({str(e)[:60]}).')
        page_ = None
        try:
            page_ = await rs._cb.LivePage(s_['connect']).start(); await page_.goto(url_)
            await page_.release()   # 🙋 the owner signs in ALONE: nothing routed or attached, so a "verify you are human" box can pass
        except Exception:
            pass   # the window still opens; the owner types the address
        rs._SIGNIN[cat_id] = {'sid': s_['id'], 'site': site_, 'page': page_, 'at': rs.time.time(), 'connect': s_['connect'], 'live': s_.get('live'), 'hand': s_.get('hand')}
        return {'live': s_.get('hand') or s_.get('live'), 'site': site_}   # 🔓 the owner signs in by hand: the clickable view
    if p.op == 'signin_save':   # 🔓 keep what the owner's sign-in left (cookies + local storage), sealed for this agent; its windows start with it
        si_ = rs._SIGNIN.get(cat_id)
        if not si_:
            raise rs.HTTPException(400, 'Open the site and sign in first.')
        async with rs.httpx.AsyncClient(timeout=30) as http:
            try:
                ctx_ = await rs._cb.read_context(http, rs.os.environ, si_['sid'])
            except Exception as e:
                raise rs.HTTPException(502, f'Could not read the sign-in ({str(e)[:60]}).')
        ctx_, st_ = rs._cb.clean_context(ctx_, si_['site'])   # 🧼 only the site's own, newest, unexpired cookies — no trackers, no other sites
        if not rs._cb.merge_contexts([ctx_]):
            raise rs.HTTPException(400, 'Nothing to keep yet — finish signing in, then save.')
        cat.setdefault('siteSessions', {})[si_['site']] = {'ctx': rs._ck.seal(rs.json.dumps(ctx_), cat_id), 'at': rs.time.time(), 'n': st_['kept'], 'dropped': st_['dropped']}
        rs.vault_log(cat, 'signed in', si_['site']); rs.keep_owned(cat); rs._save(store)
        sealed_ = await rs._seal_downloads(cat_id, si_['sid'], si_.get('page'), si_['site'])   # 🔏 a recovery file you downloaded there → its sealed drawer
        rs._SIGNIN.pop(cat_id, None)   # 🔥 the window stays open: its scan and its first agent window work in it
        try:
            if getattr(si_.get('page'), 'downloads', None):
                await si_['page'].downloads.stop()
        except Exception:
            pass
        rs._WARM[cat_id] = {'sid': si_['sid'], 'site': si_['site'], 'connect': si_.get('connect'), 'live': si_.get('live'), 'hand': si_.get('hand'), 'at': si_['at']}
        cat = rs._load()['cats'].get(cat_id) or cat
        return {'signedIn': rs._no_keys(cat).get('signedIn', []), 'secrets': rs._cv.public_secrets(cat), 'sealedNow': sealed_}
    if p.op == 'signin_type':   # ⌨ the type-and-paste bar under its sign-in window. The owner's words only; never stored, never logged, never sent to a model
        si_ = rs._SIGNIN.get(cat_id)
        if not si_ or not si_.get('connect'):
            raise rs.HTTPException(400, 'Open the site first.')
        try:
            await rs.asyncio.wait_for(rs._cb.type_into(si_['connect'], (p.text or '')[:2000] or None, p.job or None), 20)
        except (ValueError, rs.asyncio.TimeoutError) as e:
            raise rs.HTTPException(400, str(e)[:120] or 'The window did not answer.')
        except Exception:
            raise rs.HTTPException(502, 'The window did not answer. Click in it, then try again.')
        return {'ok': True}
    if p.op == 'human_here':   # 🙋 the owner is moving on this window's watch screen: its wait goes on
        (w or {}).setdefault('seen', {})[int(p.i or 0)] = rs.time.time()
        return {'ok': True}
    if p.op == 'win_type':   # ⌨ the same type bar, into the window of the agent that is waiting on them. The owner's words only; never stored, never logged, never sent to a model
        i_ = int(p.i or 0); to_ = ((w or {}).get('connects') or {}).get(i_)
        if not to_:
            raise rs.HTTPException(400, 'This window is not waiting for you, or it has no live browser.')
        w.setdefault('seen', {})[i_] = rs.time.time()
        try:
            await rs.asyncio.wait_for(rs._cb.type_into(to_, (p.text or '')[:2000] or None, p.job or None), 20)
        except (ValueError, rs.asyncio.TimeoutError) as e:
            raise rs.HTTPException(400, str(e)[:120] or 'The window did not answer.')
        except Exception:
            raise rs.HTTPException(502, 'The window did not answer. Click in it, then try again.')
        return {'ok': True}
    if p.op == 'signin_drop':
        (cat.get('siteSessions') or {}).pop(rs._cv.site_of(p.text or ''), None); rs.vault_log(cat, 'signed out', p.text); rs.keep_owned(cat); rs._save(store); await rs._signin_close(cat_id); await rs._warm_close(cat_id)
        return {'signedIn': rs._no_keys(cat).get('signedIn', [])}
    if p.op == 'reveal':   # 🔐 the owner's own reveal of one saved password: a FRESH wallet signature each time (a stolen session alone shows nothing)
        if not rs.reveal_ok(cat_id, p.text or '', p.ts, p.sig, rs.owner_wallet(cat) or rs._session_wallet(p.session or '')):
            raise rs.HTTPException(401, 'Sign the reveal with your wallet (one signature, no transaction).')
        try:
            pw_ = rs._cv.reveal(cat, p.text or '', p.job or '', data_dir=rs.DATA_DIR)
            rs.vault_log(cat, 'revealed', p.text); rs.keep_owned(cat); rs._save(store)
            return {'password': pw_}
        except Exception as e:
            raise rs.HTTPException(400, str(e)[:120])
    if p.op == 'agents_now':   # 🖥 the desk's Working now
        return {'agents': rs._agents_now(store, cat)}
    if p.op in ('db_list', 'db_read', 'db_share'):   # 🗄 AGT-11: its owner lists, opens and shares rows of its private database
        path_ = rs._adb.path_of(rs.DATA_DIR, cat_id)
        if p.op == 'db_read':
            body_ = rs._adb.read(path_, str(p.job or ''), lambda raw: rs._ck.unseal_bytes(raw, cat_id))
            if body_ is None:
                raise rs.HTTPException(404, 'No such row.')
            return {'id': p.job, 'body': body_}
        targets_ = [{'id': cid_, 'name': c_.get('name')} for cid_, c_ in store['cats'].items() if cid_ != cat_id and not c_.get('revoked') and rs._same_owner(cat, c_)] + [{'id': rs._adb.COLLECTIVE, 'name': 'The Collective'}]
        if p.op == 'db_share':
            if str(p.text or '') not in {t['id'] for t in targets_}:
                raise rs.HTTPException(400, 'Share only with your own agents or the Collective.')
            try:
                rs._adb.share(path_, str(p.job or ''), str(p.text), bool(p.on))
            except ValueError as e:
                raise rs.HTTPException(404, str(e))
        return {'rows': rs._adb.rows(path_), 'targets': targets_}
    if p.op == 'kit_method_approve':   # 🧪 COL-10: the owner's yes on a kit the reviews proposed (on Fee, the creator only)
        if cat.get('id') != 'leader' or not await rs._is_creator(rs._session_wallet(p.session or '')):
            raise rs.HTTPException(403, 'Only the owner approves a method kit.')
        if str(p.text or '').startswith('combo-'):   # 🧩 a pair the record proposed
            row_ = next((r for r in rs._MKIT_COMBOS if r['id'] == str(p.text) and r['proposed']), None)
            if not row_:
                raise rs.HTTPException(400, 'No such combo proposed (it may be approved already).')
            rs._mkits.approve_combo(rs.DATA_DIR, row_)
            return {'approved': [{'id': k_, **v_} for k_, v_ in rs._mkit_extra().items()]}
        row_ = next((r for r in rs._mkits.proposals(list(store['cats'].values()), rs._review.RUBRIC, rs._mkit_extra()) if r['id'] == str(p.text or '')), None)
        if not row_:
            raise rs.HTTPException(400, 'No such proposal (it may be approved already).')
        rs._mkits.approve(rs.DATA_DIR, row_)
        return {'approved': [{'id': k_, **v_} for k_, v_ in rs._mkit_extra().items()]}
    if p.op == 'engines':   # 📡 AGT-12: every engine that runs on its own, live, counts only (no wallet, prompt or page)
        now_ = rs.time.time(); lines_ = []
        try:
            with (rs.DATA_DIR / 'mind_calls.jsonl').open() as fh_:
                lines_ = fh_.readlines()[-4000:]
        except OSError:
            pass
        kf_ = rs._kfresh.view(rs._kits.KIT_USE, rs.KITS_DIR)
        if not rs._MKIT_STATE:   # measured only when Missions opened: after a restart the card read 0 / 0 / 0 (seen live 2026-11-10)
            try:
                rows_m_ = rs._mission.all_of(cat, now_, lambda k, f: rs._proof_view(cat, k, f), rs._calls_of(cat_id), rs._pev_record())
                rs._mkit_measure(cat, rows_m_)
            except Exception as e:   # noqa: BLE001
                print(f'[engines] kits: {str(e)[:80]}')
        return {'at': round(now_), 'reviewer': rs._engv.reviewer(store['cats'].values(), rs._review.VERSION, lines_, rs.REVIEW_EVERY_S, rs.REVIEW_SCOPE),
                'kits': {'checkedAt': kf_.get('checkedAt'), 'live': len(kf_['kits']), 'moved': sum(1 for k in kf_['kits'] if k.get('prev')), 'held': [r for r in kf_.get('log') or [] if not r.get('ok')][:3], 'everyH': round(rs._kfresh.CHECK_EVERY_S / 3600)},
                'reads': rs._engv.reads(rs._READS, rs._TOPIC_READS, rs.READ_FRESH_S, now_), 'methods': rs._engv.methods(rs._MKIT_STATE), 'routes': rs._engv.routes(lines_, now_),
                'proposals': {'kits': rs._mkits.proposals(list(store['cats'].values()), rs._review.RUBRIC, rs._mkit_extra()), 'proofs': rs._gaps.gaps(store['cats'].values()),
                              'approved': [{'id': k_, **v_} for k_, v_ in rs._mkit_extra().items()], 'history': rs._mkits.history(rs.DATA_DIR), 'combos': list(rs._MKIT_COMBOS),
                              'canApprove': cat.get('id') == 'leader' and await rs._is_creator(rs._session_wallet(p.session or ''))}}
    if p.op == 'show_ads':   # 🎬 owner-staff only: this agent makes one ad per proof type for the Showcase, $1.25 cap, one at a time
        if not cat.get('ownerStaff'):
            raise rs.HTTPException(403, 'Showcase ads are made by the owner\'s agents.')
        live_ = bool(rs._ADS_LIVE.get(cat_id) and not rs._ADS_LIVE[cat_id].done())
        redo_ = str(p.text or '')[5:] if str(p.text or '').startswith('redo:') else ''
        if redo_:   # ↻ one ad built again from scratch: its old build stays counted toward the cap (lostWs), its video goes. A live run picks it up next
            j_ = (cat.get('showAds') or {}).get(redo_)
            if redo_ not in rs._ads.KINDS or not (j_ or {}).get('ws'):
                raise rs.HTTPException(400, 'That ad has not been built yet.')
            if j_.get('state') in ('building', 'recording', 'fixing') and live_:
                raise rs.HTTPException(409, 'That ad is being made right now.')
            cat['showAds'][redo_] = {'state': 'waiting', 'lostWs': [*(j_.get('lostWs') or []), j_['ws']], **({'tries': j_['tries']} if j_.get('tries') else {})}; rs.keep_owned(cat); rs._save(store)
            (rs.SHOW_ADS_DIR / cat_id / f'{redo_}.webm').unlink(missing_ok=True)
        if (p.text == 'go' or redo_) and not live_:
            rs._ADS_LIVE[cat_id] = rs.asyncio.create_task(rs._ads_run(cat_id))
        return {'ads': rs._ads_view(cat_id, cat), 'running': bool(rs._ADS_LIVE.get(cat_id) and not rs._ADS_LIVE[cat_id].done())}
    if p.op == 'ad_lab':   # 🎬 owner only: every ad attempt of this owner's agents, kept as the lesson for the next build (Fee's desk › Ad lab)
        if not cat.get('ownerStaff') and not cat.get('isLeader'):
            raise rs.HTTPException(403, 'The ad lab is the owner\'s.')
        mine_ = [(cid_, c_) for cid_, c_ in store['cats'].items() if c_.get('showAds') and (cid_ == cat_id or rs._same_owner(cat, c_))]
        rows_ = [r_ for cid_, c_ in mine_ for r_ in rs._ads_lab(cid_, c_)]
        return {'rows': rows_[:240], 'spent': round(sum(r_['cost'] for r_ in rows_), 4), 'budget': rs._ads.BUDGET, 'model': rs._ads.MODEL}
    if p.op == 'media_library':   # 🗂 the editor's library: every image, video and 3D scene this owner's agents made, any proof kind
        mine_ = [(cid_, c_) for cid_, c_ in store['cats'].items() if not c_.get('revoked') and (cid_ == cat_id or rs._same_owner(cat, c_))]
        rows_ = sorted([dict(r_, cat=cid_, agent=c_.get('name') or '') for cid_, c_ in mine_ for r_ in rs._media_library(cid_, c_)], key=lambda r: -r['at'])
        rows_ = rs._mg.made_by_happy() + rows_   # 🎬 Happy's real AI results lead every user's shelf (public files, the same for everyone)
        return {'rows': rows_[:400], 'count': {t_: sum(1 for r_ in rows_ if r_['type'] == t_) for t_ in ('video', 'image', '3d')}}
    if p.op == 'showcase':   # 🎬 the Showcase's real rows: this owner's reviewed proofs per kind and its newest books (no wallet, no page)
        mine_ = [c_ for cid_, c_ in store['cats'].items() if not c_.get('revoked') and (cid_ == cat_id or rs._same_owner(cat, c_))]
        ads_ = next((dict(rs._ads_view(cid_, c_), cat=cid_) for cid_, c_ in store['cats'].items() if c_.get('showAds') and not c_.get('revoked') and (cid_ == cat_id or rs._same_owner(cat, c_))), None)
        return {**rs._review.showcase(mine_), 'ads': ads_, 'adsOk': bool(cat.get('ownerStaff')), 'fresh': rs._kfresh.view(rs._kits.KIT_USE, rs.KITS_DIR),
                'kits': [{'id': kid, 'name': c_['name'], 'what': c_['what'], 'kinds': c_.get('kinds') or [], 'license': c_.get('license'), 'live': kid in rs._kits.KIT_USE} for kid, c_ in rs._kits.CATALOG.items()]}
    if p.op == 'demo_trade':   # ⛏ this owner's best real trade, for the flight on the Proofs tab: numbers and picture names, no wallet
        best_ = None
        for cid_, c_ in store['cats'].items():
            if c_.get('revoked') or not (cid_ == cat_id or rs._same_owner(cat, c_)):
                continue
            for f_ in c_.get('powFolders') or []:
                if isinstance(f_, dict) and f_.get('real') and f_.get('pnlPct') is not None and isinstance(f_.get('line'), list) and len(f_['line']) >= 2 and (best_ is None or float(f_['pnlPct']) > float(best_[1]['pnlPct'])):
                    best_ = (cid_, f_)
        if not best_:
            return {'trade': None}
        c_, f_ = best_
        return {'trade': {'cat': c_, 'id': rs.re.sub(r'[^a-z0-9]', '', str(f_['id']).lower()), 'sym': str(f_.get('sym') or '')[:16], 'pair': {'chainId': 'solana', 'pairAddress': str(f_.get('pair') or ''), 'baseToken': {'address': str(f_.get('mint') or ''), 'symbol': str(f_.get('sym') or '')[:16]}, 'symbol': str(f_.get('sym') or '')[:16], 'mint': str(f_.get('mint') or '')}, 'pnl': round(float(f_['pnlPct']), 1), 'entry': f_.get('entry'), 'tp': f_.get('tp'), 'sl': f_.get('sl'), 'line': [float(x) for x in f_['line'] if isinstance(x, (int, float))][-200:], 'files': [{'file': str(x.get('file')), 'site': str(x.get('site') or '')[:40]} for x in f_.get('shots') or [] if isinstance(x, dict) and x.get('file')][:6],
                          'pnlSol': f_.get('pnlSol'), 'sol': f_.get('sol'), 'boughtAt': f_.get('boughtAt'), 'soldAt': f_.get('soldAt'), 'why': str(f_.get('why') or '')[:240],   # 📊 owner 2026-11-11: the best trade, meta: its real numbers + why
                          'talk': [{'by': str(x.get('by') or '')[:24], 'text': str(x.get('text') or '')[:200]} for x in (f_.get('talk') or [])[-3:] if isinstance(x, dict)]}}
    if p.op == 'tools_show':   # 🧰 real library counts for the Proofs tab
        rows_ = rs._assets._load(rs.KITS_DIR, rs._assets.INDEX).get('rows') or {}
        return {'models': rs._assets.model_count(rs.KITS_DIR), 'hdris': len(rows_.get('hdri') or []), 'textures': len(rows_.get('texture') or []), 'templates': rs._play.menu()['templates']}
    if p.op == 'tools_showcase':   # 🎬 a finished piece from the engine, for Features. No model, the same assets every time, kept once built
        if p.job not in rs._play.TEMPLATE_BY:
            raise rs.HTTPException(400, 'No such piece.')
        got_ = rs._SHOWCASE.get(p.job)
        if not got_:
            async with rs.httpx.AsyncClient(timeout=30) as h_:
                await rs._assets.ensure(h_, rs.KITS_DIR); sc_, _u, _m = await rs._assets.fill(h_, rs.KITS_DIR, rs._play.template_scene(p.job))
            sc_ = rs._play.lead_up(sc_); sc_['camera'] = [0, 0, 0]; sc_ = rs._play._frame(rs._assets.compose(sc_)); got_ = rs._SHOWCASE[p.job] = rs._feat.preview(rs._play.lock_site(rs._play.to_html(sc_, rs._play.TEMPLATE_BY[p.job]['name'])).replace('</body>', rs._play.DEMO_PLAYER + '</body>', 1))
        return {'preview': got_}
    if p.op == 'demo_gallery':   # 🖼 real proofs of every type, whitelisted, for the Features folder
        g_ = rs._demo_gallery(store, cat)
        return {'kinds': g_['kinds']}
    if p.op == 'demo_open':   # one of those pages, locked in a sandbox
        got_ = rs._demo_gallery(store, cat)['links'].get(str(p.job))
        if not got_:
            raise rs.HTTPException(404, 'That page is not in the gallery.')
        v_ = (rs._ws_load(got_[0], got_[1]) or {}).get('versions') or []; n_ = int(got_[2] or len(v_))
        return {'preview': rs._feat.preview(rs._ws_placed(got_[0], v_[min(n_, len(v_)) - 1]['html'])) if v_ else ''}
    if p.op == 'build_list':   # 🏆 builds their owners sent to the Collective, newest first, no owner shown
        return {'builds': rs._popular_builds(store)}
    if p.op == 'build_open':   # one of those, to look at. A locked page in a sandbox
        got_ = next((x for x in rs._popular_builds(store, raw=True) if x['id'] == str(p.job)), None)
        if not got_:
            raise rs.HTTPException(404, 'That build is not shared.')
        doc_ = rs._ws_load(got_['cat'], got_['ws']); v_ = (doc_ or {}).get('versions') or []
        return {'preview': rs._feat.preview(rs._ws_placed(got_['cat'], v_[-1]['html'])) if v_ else ''}
    if p.op == 'build_use':   # a new folder of its own, starting from that page
        got_ = next((x for x in rs._popular_builds(store, raw=True) if x['id'] == str(p.job)), None); doc_ = rs._ws_load(got_['cat'], got_['ws']) if got_ else None; v_ = (doc_ or {}).get('versions') or []
        if not v_:
            raise rs.HTTPException(404, 'That build is not shared.')
        try:
            row_ = rs._feat.new_folder(cat, 'build', f"From {got_['name']}"[:60], rs.time.time())
        except ValueError as e:
            raise rs.HTTPException(409, str(e))
        new_ = rs._feat.new_doc(row_); new_['versions'] = [{'html': rs._ws_placed(got_['cat'], v_[-1]['html']), 'by': 'Popular build', 'at': round(rs.time.time())}]; rs._ws_save(cat_id, new_); rs.keep_owned(cat); rs._save(store)
        return {'folder': row_, 'workspaces': rs._ws_list(cat)}
    if p.op == 'site_book':   # 📚 its sites per proof: the owner's order, on / off. No text = just read
        if p.text:
            try:
                cat.setdefault('siteBook', {})[str(p.to)] = rs._book.clean(str(p.to), rs.json.loads(p.text))
            except (ValueError, TypeError) as e:
                raise rs.HTTPException(400, str(e)[:120])
            rs.keep_owned(cat); rs._save(store)
        return {'book': {k: {'rows': rs._book.view(cat.get('siteBook'), k), 'what': rs._book.WHAT[k], 'mine': bool((cat.get('siteBook') or {}).get(k))} for k in rs._book.KINDS}}
    if p.op in ('kit_list', 'kit_pick', 'kit_skill'):   # 🧰 any agent: which kits it reads first, or the agent chooses per request
        b_ = cat.setdefault('brainsCfg', {})
        if p.op == 'kit_skill':
            try:
                rs._kits.set_skill(b_, str(p.text or ''), str(p.job or ''), bool(p.on), next((k.get('skills') for k in rs._kits.catalog_view(rs.KITS_DIR) if k['id'] == p.text), None))
            except ValueError as e:
                raise rs.HTTPException(400, str(e)[:120])
            rs.keep_owned(cat); rs._save(store)
        if p.op == 'kit_pick':
            kind_k_ = p.to if p.to in rs._kits.KINDS else None; have_ = {k['id'] for k in rs._kits.all_rows(rs.KITS_DIR)}; known_ = set(rs._kits.CATALOG) | {x['id'] for x in rs._kits.found_rows(rs.KITS_DIR)} | {rs._kits.FEELESS_ID} | have_; want_ = [x for x in str(p.text or '').split(',') if x in known_][:rs._kits.MAX_PICKS]
            for kid_ in [x for x in want_ if x not in have_ and x != rs._kits.FEELESS_ID]:   # only the catalog's fixed addresses, the guide is text
                try:
                    async with rs.httpx.AsyncClient() as h_:
                        await rs._kits.add(h_, rs.KITS_DIR, kid_)
                except (ValueError, rs.httpx.HTTPError) as e:
                    raise rs.HTTPException(400, str(e)[:160])
            if kind_k_:
                rs._kits.set_picks(b_, kind_k_, want_, p.job)
            else:
                b_['kits'] = want_; b_['kitMode'] = 'auto' if p.job == 'auto' else 'mine'
            rs.keep_owned(cat); rs._save(store)
        rec_ = await rs.asyncio.to_thread(rs._kit_record, store); view_ = [{**k, 'record': rec_.get(k['id']) or {'used': 0, 'won': 0, 'lost': 0}, 'quality': rs._kits.quality(rec_.get(k['id']))} for k in rs._kits.catalog_view(rs.KITS_DIR)]
        by_ = {k: dict(zip(('mode', 'picks'), rs._kits.picks_of(b_, k))) for k in rs._kits.KINDS}; now_k_ = by_.get(p.to) or by_['pos']
        return {'kits': view_, 'fresh': rs._kfresh.view(rs._kits.KIT_USE, rs.KITS_DIR), 'skillsOff': b_.get('kitSkillsOff') or {}, 'by': by_, 'picks': now_k_['picks'], 'mode': now_k_['mode'], 'max': rs._kits.MAX_PICKS, 'recs': {k: rs._kits.recommend(view_, k, record=rec_) for k in rs._kits.KINDS}, 'stacks': rs._proof_kits.STACKS}
    if p.op in ('kit_catalog', 'kit_add', 'kit_drop', 'kit_read', 'kit_edit', 'kit_scout', 'kit_approve', 'kit_reject', 'kit_ask'):   # 🧰 the library: the owner only, on Fee
        if cat.get('id') != 'leader' or not await rs._is_creator(rs._session_wallet(p.session or '')):
            raise rs.HTTPException(403, 'Only the owner changes the kit library.')
        try:
            if p.op == 'kit_scout':
                async with rs.httpx.AsyncClient() as h_:
                    await rs._kits.scout(h_, rs.KITS_DIR)
            elif p.op == 'kit_approve':
                async with rs.httpx.AsyncClient() as h_:
                    await rs._kits.approve(h_, rs.KITS_DIR, str(p.text or ''))
            elif p.op == 'kit_reject':
                rs._kits.reject(rs.KITS_DIR, str(p.text or ''))
            elif p.op == 'kit_ask':   # 🧠 OSSY and G4 search and rate now instead of waiting for the daily pass. Free, on his own machines
                said_ = await rs._kit_minds_pass()
                return {'said': said_, 'catalog': rs._kits.CATALOG, 'kits': [rs._kits.view(k) for k in rs._kits.rows(rs.KITS_DIR)], 'proposed': rs._kits.proposed_rows(rs.KITS_DIR), 'fresh': rs._kfresh.view(rs._kits.KIT_USE, rs.KITS_DIR)}
            elif p.op == 'kit_add':
                async with rs.httpx.AsyncClient() as h_:
                    await rs._kits.add(h_, rs.KITS_DIR, str(p.text or ''))
            elif p.op == 'kit_drop':
                rs._kits.drop(rs.KITS_DIR, str(p.text or ''))
            elif p.op == 'kit_edit':
                rs._kits.edit(rs.KITS_DIR, str(p.job or ''), text=p.text)
            elif p.op == 'kit_read':
                return {'text': (rs._kits.load(rs.KITS_DIR, str(p.text or '')) or {}).get('text') or ''}
        except (ValueError, rs.httpx.HTTPError) as e:
            raise rs.HTTPException(400, str(e)[:160])
        return {'catalog': rs._kits.CATALOG, 'kits': [rs._kits.view(k) for k in rs._kits.rows(rs.KITS_DIR)], 'proposed': rs._kits.proposed_rows(rs.KITS_DIR), 'fresh': rs._kfresh.view(rs._kits.KIT_USE, rs.KITS_DIR)}
    if p.op in ('card_link', 'card_drop'):   # 💳 no money moves here
        try:
            link_ = rs.card_link(cat, str(p.text or ''), p.job, rs.time.time()) if p.op == 'card_link' else cat.pop('cardLink', None) and None
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs.keep_owned(cat); rs._save(store)
        return {'cardLink': link_}
    if p.op in ('wallet', 'wallet_swap'):   # 👛 the desktop wallet app: its live balance + the owner's own swap inside its wallet (nothing leaves it)
        if p.op == 'wallet_think':   # 💭 what thinking costs this agent, from its own receipts. It reads and tells. Nothing is sent
            return rs._wallet_think(cat_id)
        if p.op == 'wallet' and cat.get('handle') == 'sicarios' and not (cat.get('agentWallet') or {}).get('address'):   # 🎩 it trades from the Fuse wallet: that is the wallet its owner sees
            try:
                async with rs.httpx.AsyncClient() as h_:
                    r_ = await h_.get('http://127.0.0.1:5077/api/reputation/internal/sicario-wallet', headers={'x-feeless-internal': rs._internal_key_read()}, timeout=8)
                return {**(r_.json() if r_.status_code == 200 else {}), 'fuse': True}
            except (rs.httpx.HTTPError, ValueError):
                return {'fuse': True, 'address': None}
        addr_ = (cat.get('agentWallet') or {}).get('address')
        if not addr_:
            raise rs.HTTPException(400, 'It has no wallet yet — make its wallet first.')
        async with rs.httpx.AsyncClient(timeout=25) as http:
            usdc_, sol_ = await rs._agent_usdc(http, addr_)
            if p.op == 'wallet':
                receipts_ = []
                try:
                    with (rs.DATA_DIR / 'model_receipts.jsonl').open() as ledger:
                        for line_ in ledger:
                            row_ = rs.json.loads(line_)
                            if row_.get('cat') == cat_id:
                                receipts_.append({k: row_.get(k) for k in ('id', 'at', 'provider', 'model', 'usd', 'tokens', 'status', 'funding')})
                except (FileNotFoundError, ValueError):
                    pass
                return {'cardLink': cat.get('cardLink'), 'address': addr_, 'sol': sol_, 'usdc': usdc_, 'gas': rs._at.GAS_SOL, 'canSwap': rs._pays_itself(cat), 'swaps': (cat.get('walletSwaps') or [])[-8:], 'modelReceipts': receipts_[-40:][::-1]}
            if not rs._pays_itself(cat):
                raise rs.HTTPException(400, 'Only a wallet Circle signs for this agent can swap.')
            if cat_id in rs._SWAP_BUSY:
                raise rs.HTTPException(409, 'A swap is already on its way.')
            try:
                in_, out_, amt_ = rs.swap_plan(str(p.text or ''), float(p.cap or 0), sol_, usdc_)
            except (ValueError, TypeError) as e:
                raise rs.HTTPException(400, str(e))
            rs._SWAP_BUSY.add(cat_id)
            try:
                q_ = await http.post(f'{rs._at.TRADE}/quote', json={'input_mint': in_, 'output_mint': out_, 'amount': f'{amt_:.6f}', 'wallet': addr_, 'slippage_bps': rs._at.SLIP_BPS}, headers=rs._at._internal_headers(), timeout=20)   # ⚖ an agent wallet's own swap (gated when its owner funded it)
                qj = q_.json() if q_.status_code == 200 else {}
                if qj.get('input_mint') != in_ or qj.get('output_mint') != out_ or not (qj.get('quote') or {}).get('transaction'):   # 🔒 signs only the exact swap asked
                    raise rs.HTTPException(502, 'No matching quote — nothing was signed.')
                rec_ = {'key': f"feeless-{cat_id}-wswap-{round(rs.time.time())}", 'tx': qj['quote']['transaction']}
                try:
                    await rs._at._circle_post(http, cat, rec_)
                except ValueError as e:
                    raise rs.HTTPException(400, f'{e} — nothing moved.')
                after_ = (usdc_, sol_)
                for _ in range(8):   # read it back: done only when the balance moved
                    await rs.asyncio.sleep(3)
                    after_ = await rs._agent_usdc(http, addr_)
                    if (after_[0] > usdc_) if out_ == rs._cf_usdc else (after_[1] > sol_):
                        break
            finally:
                rs._SWAP_BUSY.discard(cat_id)
        row_ = {'at': round(rs.time.time()), 'side': p.text, 'amount': amt_, 'sig': rec_.get('sig'), 'sol': after_[1], 'usdc': after_[0],
                'landed': (after_[0] > usdc_) if out_ == rs._cf_usdc else (after_[1] > sol_)}
        st_ = rs._load(); c_ = st_['cats'].get(cat_id)
        if c_:
            c_['walletSwaps'] = ((c_.get('walletSwaps') or []) + [row_])[-20:]; rs._save(st_)
        return {'address': addr_, 'sol': after_[1], 'usdc': after_[0], 'gas': rs._at.GAS_SOL, 'canSwap': True, 'swap': row_, 'swaps': ((c_ or {}).get('walletSwaps') or [])[-8:]}
    if p.op == 'pop_folder':   # 📌 keep / 🗑 delete a filed PoP folder from the desktop
        pf_ = cat.get('popFolders') or []; f_ = next((x for x in pf_ if x.get('id') == p.text), None)
        if not f_:
            raise rs.HTTPException(404, 'No such PoP folder.')
        if p.job == 'keep':
            f_['kept'] = bool(p.on)
        elif p.job == 'delete':
            cat['popFolders'] = [x for x in pf_ if x is not f_]
        else:
            raise rs.HTTPException(400, 'keep or delete.')
        rs.keep_owned(cat); rs._save(store)
        return {'ok': True, 'popFolders': rs._pop_view(cat)}
    if p.op == 'pow_folder':   # 📌 keep / 🗑 delete a PoW folder or one coin folder from the DESKTOP (owner 2026-11-02) — the forever archive is never touched
        fs_ = cat.get('powFolders') or []; f_ = next((x for x in fs_ if x.get('id') == p.text), None)
        if not f_:
            raise rs.HTTPException(404, 'No such PoW folder.')
        if p.job == 'keep':
            f_['kept'] = bool(p.on)
        elif p.job == 'delete_coin':
            f_['hidden'] = sorted(set(f_.get('hidden') or []) | {str(p.secret or '')})
            for sh_ in [x for x in f_.get('shots') or [] if x.get('mint') == p.secret]:
                try:
                    (rs.POWSHOTS_DIR / rs.re.sub(r'[^a-z0-9]', '', f_['id']) / rs.re.sub(r'[^a-z0-9._]', '', sh_['file'])).unlink(missing_ok=True)
                except OSError:
                    pass
            f_['shots'] = [x for x in f_.get('shots') or [] if x.get('mint') != p.secret]
        elif p.job == 'delete':
            import shutil as _sh
            _sh.rmtree(rs.POWSHOTS_DIR / rs.re.sub(r'[^a-z0-9]', '', f_['id']), ignore_errors=True)
            cat['powFolders'] = [x for x in fs_ if x.get('id') != p.text]
        else:
            raise rs.HTTPException(400, 'keep, delete or delete_coin.')
        rs.keep_owned(cat); rs._save(store)
        return {'powFolders': list(reversed(cat.get('powFolders') or []))[:12]}
    if p.op in ('fund_cfg', 'fund_quote', 'fund_send'):   # 💸 COL-16: the owner sends a proof WITH funds; on AUTO its agent adds its % from its own wallet
        cfg_ = cat.setdefault('fundGrade', {'auto': False, 'pct': 10.0})
        if p.op == 'fund_cfg':
            t_ = p.tools if isinstance(p.tools, dict) else {}
            if 'auto' in t_:
                cfg_['auto'] = bool(t_['auto'])
            if 'pct' in t_:
                cfg_['pct'] = max(1.0, min(rs._pf.PCT_MAX, round(float(t_['pct'] or 0), 2)))
            rs.keep_owned(cat); rs._save(store)
            return {'fundGrade': cfg_}
        kind_, f_ = rs._proof_folder(cat, p.job)
        if not f_:
            raise rs.HTTPException(400, 'Pick one of its filed proofs.')
        me_ = rs.owner_wallet(cat)
        if not me_:
            raise rs.HTTPException(400, 'Sign in with the wallet that owns this agent first.')
        try:
            pot_ = ((rs.json.loads((rs.DATA_DIR / 'colony.json').read_text()) or {}).get('wallet') or {}).get('address')
        except (OSError, ValueError):
            pot_ = None
        if not pot_:
            raise rs.HTTPException(400, 'The colony pot is not opened yet.')
        agent_ = (cat.get('agentWallet') or {}).get('address') if rs._pays_itself(cat) else None
        if p.op == 'fund_quote':
            auto_ = bool(cfg_.get('auto')) and bool(agent_)
            async with rs.httpx.AsyncClient(timeout=20) as http:
                free_ = 0.0
                if auto_:
                    _u, bal_ = await rs._agent_usdc(http, agent_); free_ = max(0.0, bal_ - rs._at.GAS_SOL)
                try:
                    q_ = rs._pf.quote(p.cap, cfg_.get('pct'), auto_, free_)
                except (ValueError, TypeError) as e:
                    raise rs.HTTPException(400, str(e))
                bh_ = ((await rs._crpc._rpc(http, 'getLatestBlockhash', [{'commitment': 'confirmed'}])) or {}).get('value', {}).get('blockhash')
            if not bh_:
                raise rs.HTTPException(503, 'No blockhash from the chain. Nothing was quoted.')
            tx_ = rs.pot_transfer_tx(me_, pot_, int(q_['userSol'] * 1e9), bh_); qh_ = rs._pf.qhash(cat_id, f_['id'], q_, tx_)
            cat['fundQuote'] = {'id': qh_, 'proof': f_['id'], 'kind': kind_, 'q': q_, 'tx': tx_, 'exp': round(rs.time.time()) + rs._pf.QUOTE_TTL}
            rs.keep_owned(cat); rs._save(store)
            return {'quote': {**q_, 'id': qh_, 'to': pot_, 'from': me_, 'exp': cat['fundQuote']['exp']}, 'tx': tx_}
        fq_ = cat.get('fundQuote') or {}
        if not fq_ or fq_.get('id') != p.text or fq_.get('proof') != f_['id']:
            raise rs.HTTPException(400, 'That quote is gone. Quote again. Nothing moved.')
        if rs.time.time() > float(fq_.get('exp') or 0):
            cat.pop('fundQuote', None); rs.keep_owned(cat); rs._save(store)
            raise rs.HTTPException(400, 'The quote expired. Quote again. Nothing moved.')
        if not rs._pf.signed_matches(p.sig or '', fq_['tx'], me_):
            raise rs.HTTPException(400, 'The signed transfer is not the one quoted. Nothing was sent.')
        cat.pop('fundQuote', None); rs.keep_owned(cat); rs._save(store)   # used once: a retry can never send it twice
        q_ = fq_['q']; agent_sig_ = None
        async with rs.httpx.AsyncClient(timeout=30) as http:
            user_sig_ = await rs._crpc._rpc(http, 'sendTransaction', [p.sig, {'encoding': 'base64', 'skipPreflight': False, 'maxRetries': 3}], scan=False)
            if not user_sig_:
                raise rs.HTTPException(502, 'The chain did not take your transfer. Nothing moved.')
            # ✅ only a LANDED transfer gets a receipt and releases the agent's share (2026-11-14: sent once, never confirmed, recorded anyway)
            state_ = await rs._crpc.land(rs._crpc.rpc_priority, rs._crpc.broadcast, rs.asyncio.sleep, http, user_sig_, p.sig, blockhash=rs._crpc.tx_blockhash(p.sig))
            if state_ != 'confirmed':
                raise rs.HTTPException(409 if state_ in ('failed', 'dropped') else 504, {
                    'failed': 'Your transfer ran and failed on chain. Nothing moved. Quote again.',
                    'dropped': 'Your transfer did not land before it expired. Nothing moved. Quote again.'}.get(
                    state_, f'Your transfer is not confirmed yet ({user_sig_[:10]}…). Check your wallet before sending again.'))
            if q_.get('auto') and q_.get('agentSol') and agent_ and cat_id not in rs._SWAP_BUSY:
                rs._SWAP_BUSY.add(cat_id)
                try:
                    bh_ = ((await rs._crpc._rpc(http, 'getLatestBlockhash', [{'commitment': 'confirmed'}])) or {}).get('value', {}).get('blockhash')
                    rec_ = {'key': f"feeless-{cat_id}-fund-{fq_['id']}", 'tx': rs.pot_transfer_tx(agent_, pot_, int(q_['agentSol'] * 1e9), bh_)}   # the key is the quote: it can't pay twice
                    await rs._at._circle_post(http, cat, rec_); agent_sig_ = rec_.get('sig')
                except (ValueError, rs.httpx.HTTPError) as e:
                    print(f'[fund] agent share not sent: {str(e)[:100]}')
                finally:
                    rs._SWAP_BUSY.discard(cat_id)
        rc_ = rs._pf.receipt(q_, f_['id'], user_sig_, agent_sig_, fq_['id'], rs.time.time())
        f_.setdefault('funds', []).append(rc_)
        rs._share_append({'cat': cat_id, 'owner': me_, 'sol': q_['userSol'], 'pct': None, 'sym': None, 'ref': user_sig_, 'at': rs.time.time(), 'sent': True, 'state': 'transferred', 'gift': True, 'sig': user_sig_, 'by': 'owner', 'proof': {'id': f_['id'], 'kind': fq_.get('kind')}}, (user_sig_, cat_id))
        if agent_sig_:
            rs._share_append({'cat': cat_id, 'owner': me_, 'sol': rc_['agentSol'], 'pct': q_['pct'], 'sym': None, 'ref': agent_sig_, 'at': rs.time.time(), 'sent': True, 'state': 'transferred', 'gift': True, 'sig': agent_sig_, 'by': 'agent', 'proof': {'id': f_['id'], 'kind': fq_.get('kind')}}, (agent_sig_, cat_id))
        rs.keep_owned(cat); rs._save(store)
        return {'receipt': rc_}
    if p.op == 'pot_send':   # 🏺 owner 2026-11-02: send SOL from ITS OWN wallet to the colony pot — the pot address is the server's (no destination input), gas stays
        addr_ = (cat.get('agentWallet') or {}).get('address')
        if not addr_ or not rs._pays_itself(cat):
            raise rs.HTTPException(400, 'Only its own Circle wallet can send to the pot.')
        try:
            pot_ = ((rs.json.loads((rs.DATA_DIR / 'colony.json').read_text()) or {}).get('wallet') or {}).get('address')
        except (OSError, ValueError):
            pot_ = None
        if not pot_:
            raise rs.HTTPException(400, 'The colony pot is not opened yet.')
        if cat_id in rs._SWAP_BUSY:
            raise rs.HTTPException(409, 'A send is already on its way.')
        sol_ = round(float(p.cap or 0), 6)
        try:
            if not p.job:
                raise ValueError('Every send goes with a proof. Pick one of its filed proofs.')   # 🧾 owner 2026-11-06: every send must come with a proof
            attach_ = rs._colony.attach_of(cat, rs._shares(), p.job, '')
            kind_, f_ = rs._proof_folder(cat, attach_['proof'].get('id'))
            if not f_:
                raise ValueError('Pick one of its filed proofs.')
            floor_ = 0.0 if cat.get('ownerStaff') else float(rs._cpool.load(rs.POOL_PATH)['cfg'].get('minStakeUsd') or 1)   # 🧪 owner 2026-11-06: the owner's own agents may send any amount, to test
            if sol_ * await rs._pool_px() < floor_:
                raise ValueError(f'Send at least ${floor_:g} with a proof.')
            if kind_ == 'PoW':   # 💎 a real trade keeps its rule: only a win of +50% or more, with at least its share
                if not rs._cl.qualifies(f_):
                    raise ValueError('A PoW goes to the Pool only if it won +50% or more.')
                if not cat.get('ownerStaff') and sol_ < rs._cl.cut_sol(f_, (cat.get('colonyShare') or {}).get('pct') or 5):
                    raise ValueError(f"Send at least {rs._cl.cut_sol(f_, (cat.get('colonyShare') or {}).get('pct') or 5)} SOL: its share of this proof.")
                if not cat.get('ownerStaff') and sol_ > rs._cl.cut_sol(f_, 25) + 1e-9:
                    raise ValueError(f"Send at most {rs._cl.cut_sol(f_, 25)} SOL: 25% of what this proof really made.")
                blocked_ = rs._cl.send_block(f_, cat, store['cats'])
                if blocked_:
                    raise ValueError(blocked_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        async with rs.httpx.AsyncClient(timeout=30) as http:
            _usdc, bal_ = await rs._agent_usdc(http, addr_)
            if sol_ < rs.POT_SEND_MIN or sol_ > bal_ - rs._at.GAS_SOL + 1e-9:
                raise rs.HTTPException(400, f'Send between {rs.POT_SEND_MIN} and {max(0.0, bal_ - rs._at.GAS_SOL):.6f} SOL (it keeps {rs._at.GAS_SOL} SOL for gas).')
            rs._SWAP_BUSY.add(cat_id)
            try:
                bh_ = ((await rs._crpc._rpc(http, 'getLatestBlockhash', [{'commitment': 'confirmed'}])) or {}).get('value', {}).get('blockhash')
                rec_ = {'key': f"feeless-{cat_id}-pot-{round(rs.time.time())}", 'tx': rs.pot_transfer_tx(addr_, pot_, int(sol_ * 1e9), bh_)}
                try:
                    await rs._at._circle_post(http, cat, rec_)
                except ValueError as e:
                    raise rs.HTTPException(400, f'{e} — nothing moved.')
            finally:
                rs._SWAP_BUSY.discard(cat_id)
        if not rec_.get('sig'):
            raise rs.HTTPException(503, 'Transfer submitted, but its on-chain signature is not confirmed yet.')
        verified_ = False
        if attach_.get('proof'):
            async with rs.httpx.AsyncClient(timeout=15) as http_v:
                try:
                    verified_ = await rs._collect_verify(http_v, cat, f_, rec_['sig'], pot_, sol_, (cat.get('colonyShare') or {}).get('pct'), rs.time.time())
                except Exception as e:   # noqa: BLE001 — the engine reads it again
                    print(f'[collect] verify later: {str(e)[:100]}')
        rs._share_append({'cat': cat_id, 'owner': rs.owner_wallet(cat), 'sol': sol_, 'pct': None, 'sym': None, 'ref': rec_.get('sig'),
                       'at': rs.time.time(), 'sent': True, 'state': 'transferred', 'gift': True, 'sig': rec_.get('sig'), **attach_, **({'verified': verified_} if attach_.get('proof') else {})}, (rec_.get('sig'), cat_id))
        rs.keep_owned(cat); rs._save(store)   # its folder now holds the send and the five checks
        return {'sent': {'sol': sol_, 'to': pot_, 'sig': rec_.get('sig')}, 'verified': verified_, 'review': f_.get('review')}
    if p.op == 'seal':   # 🔏 the owner pastes a secret (a recovery phrase…): sealed with this agent's key, never shown on the page again until opened
        try:
            out_ = rs._cv.put_secret(cat, p.job or 'sealed note', text=p.secret or '', site=p.text or '', data_dir=rs.DATA_DIR)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs.vault_log(cat, 'sealed', p.text or p.job); rs.keep_owned(cat); rs._save(store)
        return {'secrets': out_}
    if p.op == 'unseal':   # 🔏 open ONE sealed item: a fresh wallet signature each time (a stolen session alone opens nothing)
        if not rs.reveal_ok(cat_id, p.text or '', p.ts, p.sig, rs.owner_wallet(cat) or rs._session_wallet(p.session or '')):
            raise rs.HTTPException(401, 'Sign the open with your wallet (one signature, no transaction).')
        try:
            got_ = rs._cv.open_secret(cat, p.text or '', data_dir=rs.DATA_DIR)
        except (ValueError, OSError) as e:
            raise rs.HTTPException(400, str(e)[:120])
        rs.vault_log(cat, 'opened', got_.get('label')); rs.keep_owned(cat); rs._save(store)
        return got_
    if p.op == 'drop_secret':
        out_ = rs._cv.drop_secret(cat, p.text or '', data_dir=rs.DATA_DIR); rs.vault_log(cat, 'deleted', p.text); rs.keep_owned(cat); rs._save(store)
        return {'secrets': out_}
    if p.op == 'unlogin':
        rs._cv.drop_login(cat, p.text or '', p.job or ''); rs.vault_log(cat, 'forgot', p.text); rs.keep_owned(cat); rs._save(store)
        return {'logins': rs._cv.public_logins(cat)}
    if p.op == 'unmedia':
        cat['media'] = [m for m in cat.get('media') or [] if m.get('url') != p.text]; rs._save(store)
        return {'media': cat['media']}
    if p.op == 'memory_restore':
        if w and not w.get('done'):
            raise rs.HTTPException(409, 'Let its current task finish before restoring model memory.')
        b_ = cat.get('brainsCfg')
        if not b_:
            raise rs.HTTPException(400, 'This agent has no model memory.')
        try:
            version = next((r for r in rs._poi.memory_versions(rs.DATA_DIR, cat_id) if r['generation'] == p.i), None)
            if version is None:
                raise rs.HTTPException(404, 'That sealed memory version was not found.')
            rs._poi.preserve_model_memory(rs.DATA_DIR, cat_id, b_, b_.get('brains') or [], rs.time.time())
        except (OSError, ValueError) as e:
            raise rs.HTTPException(503, f'Memory restore paused: sealed versions could not be verified ({e}).')
        source = version['source']
        b_['cloud'] = source.get('cloud') or []
        b_['decisions'] = source.get('decisions') or []
        b_['minds'] = {m: note for m, note in (source.get('minds') or {}).items() if m in (b_.get('brains') or [])}
        rs._log_event(store, cat, 'LEARN', f"🔁 restored model memory version {version['generation']}")
        rs._save(store)
        return {'memoryRestored': version['generation'], 'poi': rs._poi_owner_view(cat_id)}
    if p.op == 'mode':   # 🧭 plan together → one answer · each mind its own job
        if p.job not in rs._ca.MODES:
            raise rs.HTTPException(400, 'Pick plan or jobs.')
        cat['workMode'] = p.job; rs._save(store)
        return {'workMode': cat['workMode']}
    if p.op == 'go':
        cat['workGo'] = bool(p.on)
        if not cat['workGo']:
            cat['workQueue'] = []
        rs._save(store)
    elif p.op == 'unpark':   # ⏸ drop a filed task (Resume = the desk drops it, then asks it again)
        k_ = list(cat.get('workParked') or [])
        if p.i is not None and 0 <= int(p.i) < len(k_):
            k_.pop(int(p.i)); cat['workParked'] = k_; rs._save(store)
    elif p.op == 'unqueue':
        q_ = list(cat.get('workQueue') or [])
        if p.i is not None and 0 <= int(p.i) < len(q_):
            q_.pop(int(p.i)); cat['workQueue'] = q_; rs._save(store)
    elif p.op == 'redirect' and w:   # 🧭 the owner sends a blocked window to another source (one of the book's picks, or any research site)
        i_ = int(p.i or 0); wins_ = (w.get('task') or {}).get('windows') or []
        host_ = rs._src.host_of(p.text)
        if not (0 <= i_ < len(wins_)) or not host_ or host_ in rs._src.NEVER or not rs._cp.research_ok('https://' + host_):
            raise rs.HTTPException(400, 'Not a site it may research.')
        ev = (w.get('events') or {}).get(i_)
        if ev:
            wins_[i_]['redirect'] = 'https://' + host_; w['go'][i_] = True; ev.set()
    elif p.op in ('continue', 'stop_window') and w:
        ev = (w.get('events') or {}).get(int(p.i or 0))
        if ev:
            w['go'][int(p.i or 0)] = p.op == 'continue'; ev.set()
    elif p.op == 'stop' and w and w.get('task'):
        w['task']['stop'] = True
        for i, ev in list((w.get('events') or {}).items()):
            w['go'][i] = False; ev.set()
        rs.asyncio.create_task(rs._hard_stop(w))
    elif p.op == 'ask':
        research_ = b.get('kind') == 'trading' and bool(b.get('brains')) and (cat.get('tools') or {}).get('research', True)   # 📰 a trader researches coins + narrative only
        if (b.get('kind') != 'general' and not research_) or not b.get('brains'):
            raise rs.HTTPException(400, 'Only a General AI cat — or a trader researching coins + narrative — works in browsers.')
        made_ = rs._ac.make_job(p.text)
        if made_:   # 🎨 one model call, off the engine: the reply files through the engine pass
            if rs._ac.off_lane(b.get('kind'), p.text):
                cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': rs._ac.TRADER_NOTE, 'at': rs.time.time()}])[-200:]
            why_ = rs._made_refusal(cat, made_)
            say_ = why_ or ('🎨 Making the picture. It lands here and in Creations.' if made_['kind'] == 'image' else '🧱 Building the project. It lands here and in Creations, with a preview and a .zip.' if made_['kind'] == 'project' else '🖥 Building the page. It lands here and in Creations, with a preview.')
            if not why_:
                rs._MADE_BUSY.add(cat_id); rs.asyncio.create_task(rs._made_job(cat_id, made_, cat))
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': say_, 'at': rs.time.time()}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        q_ = rs._ac.quick(p.text)
        if q_:   # ⚡ a free command: FEELESS's own data, answered now, no model call
            say_ = await rs._quick_answer(q_)
            store = rs._load(); cat = store['cats'][cat_id]   # the read can take seconds: the engine saved meanwhile, so write onto the newest store with no wait before the save
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': say_, 'at': rs.time.time()}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        watching_ = bool(rs._ac.watch_goal(p.text))
        p.text = rs._ac.watch_goal(p.text) or p.text   # 👁 Watch a Wallet: its own browser does the finding
        if rs._ac.off_lane(b.get('kind'), p.text):   # 🧭 it still does the work, and says so first
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': rs._ac.TRADER_NOTE, 'at': rs.time.time()}])[-200:]
        tu_ask_ = rs._tu.ask(p.text, cat.get('siteManuals')); tu_ans_ = rs._tu.reply(p.text) if cat.get('topup') else None
        if tu_ask_ or tu_ans_:   # 💸 only the owner's typed words reach here, never a model or a page
            who_ = {'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}
            out_ = {'say': rs._topup_start(cat, tu_ask_)} if tu_ask_ else rs._topup_answer(cat, tu_ans_)
            if out_.get('send'):
                if (cat['topup'].get('source') == 'read'):
                    say_ = '💸 It read that address from the page, so type its last 4 characters in the card, then press Yes. Nothing moved.'
                else:
                    ok_, say_ = await rs._topup_send(cat, cat_id, round(out_['send'], 2), '')
                    fresh_ = rs._load(); moved_ = fresh_['cats'].get(cat_id)
                    if moved_ is not None:   # the send took seconds: the engine saved meanwhile, so write onto the newest store
                        moved_['topups'] = cat.get('topups') or []
                        if 'topup' in cat:
                            moved_['topup'] = cat['topup']
                        else:
                            moved_.pop('topup', None)
                        store, cat = fresh_, moved_
            else:
                say_ = out_['say']
            cat['chat'] = (list(cat.get('chat') or []) + [who_, {'by': 'cats', 'text': say_, 'at': rs.time.time()}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        st_ask_ = rs._st.parse(p.text, set(cat.get('siteSessions') or {})); st_ans_ = rs._tu.reply(p.text) if cat.get('siteTrade') else None
        if st_ask_ or (st_ans_ and 'yes' in st_ans_):   # 🛒 "buy $1 of $BONK on pump": only the owner's typed words reach here, never a model or a page
            say_ = await rs._site_trade_chat(cat_id, st_ask_, st_ans_)
            store = rs._load(); cat = store['cats'][cat_id]
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': say_, 'at': rs.time.time()}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        made_ = rs._pc.parse(p.text)   # 💬 "create a PoB named Lakers v Suns 10/12", and it stays the one this chat talks about
        desk_ = cat.get('deskProof')
        if desk_ and not made_ and rs._pc.leaving(p.text):
            cat.pop('deskProof', None); cat.pop('proofNote', None)
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': f"Back at the desk. {desk_['name']} keeps its folder.", 'at': rs.time.time()}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        if made_ and made_['kind'] == 'pos':
            try:
                row_ = rs._feat.new_folder(cat, 'build', made_['name'] or 'New build', rs.time.time())
            except ValueError as e:
                raise rs.HTTPException(409, str(e))
            rs._ws_save(cat_id, rs._feat.new_doc(row_)); cat['deskProof'] = desk_ = rs._pc.focus({**made_, 'name': row_.get('name') or made_['name']}, rs.time.time(), row_['id'])
            if not made_['ask']:
                cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': f"🧱 {desk_['name']} is open. Tell me what to build, here or in its folder.", 'at': rs.time.time(), 'open': 'features'}])[-200:]
                rs.keep_owned(cat); rs._save(store)
                return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        elif made_:
            cat['deskProof'] = rs._pc.focus(made_, rs.time.time()); cat.pop('proofNote', None); p.text = rs._pc.line_for(made_)
        if desk_ and desk_.get('kind') == 'pos' and (not made_ or made_['kind'] == 'pos'):   # 🧱 words here build in its folder, the same as typing there
            said_ = made_['ask'] if made_ else str(p.text or '').strip()[:3000]; doc_ = rs._ws_load(cat_id, desk_['ws'])
            if not doc_:
                cat.pop('deskProof', None)
            else:
                if doc_.get('busy'):
                    raise rs.HTTPException(409, 'It is still working on the last one.')
                b_ = cat.get('brainsCfg') or {}
                if not b_.get('brains') or not (rs._lc.can_ask(b_) or rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR) or rs._pays_itself(cat)):
                    raise rs.HTTPException(402, 'It needs model credit to do this.')
                rs._feat.add_msg(doc_, 'you', said_, rs.time.time()); doc_['complete'] = False; doc_['pending'] = True; doc_['busy'] = {'at': round(rs.time.time()), 'to': 'both', 'stage': 'build' if doc_.get('versions') else 'research'}
                rs._ws_save(cat_id, doc_); rs._ws_start(cat_id, desk_['ws'], 'both', said_, None)
                cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': said_[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': f"🧱 Working on {desk_['name']}. Watch it in its folder.", 'at': rs.time.time(), 'open': 'features'}])[-200:]
                rs.keep_owned(cat); rs._save(store)
                return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        elif desk_ and not made_ and not cat.get('proofAsk'):   # 🎯 a follow up on a PoB, PoC, PoW or PoP: its minds hear it on every call from now on
            cat['proofNote'] = {'text': rs._pc.note_for(desk_, p.text), 'at': rs.time.time()}
            if (desk_['kind'] == 'pob' and (cat.get('pobRun') or cat.get('pobRead'))) or (desk_['kind'] == 'pop' and cat.get('popRun')) or (desk_['kind'] == 'pow' and cat.get('powRun')) or (desk_['kind'] == 'poc' and cat_id in rs._POC_BUSY):
                cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': f"🎯 Told the minds working on {desk_['name']}. They use it from their next step.", 'at': rs.time.time(), 'open': desk_['open']}])[-200:]
                rs.keep_owned(cat); rs._save(store)
                return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        auto_say_ = None if p.auto else rs._auto_chat(cat, cat_id, p.text)   # 🤖 AGENT-AUTO: `auto pob` → 3 questions → confirm; `stop auto` = kill-switch
        if auto_say_:
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': auto_say_, 'at': rs.time.time()}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        pend_ = cat.get('proofAsk'); asked_go_ = bool(made_ and made_.get('name')) or bool(p.auto)   # a proof named by its owner (or a confirmed auto run) has been told what to do: no question first
        if pend_:   # 🔁 its answer to the question it asked before filing
            how_, line_, note_ = rs._plan.answer(pend_, p.text, rs.time.time()); cat.pop('proofAsk', None)
            if how_ == 'cancel':
                cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': 'Okay, nothing filed.', 'at': rs.time.time()}])[-200:]
                rs.keep_owned(cat); rs._save(store)
                return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
            if how_ == 'go':
                asked_go_ = True; p.text = line_
                if note_:
                    cat['proofNote'] = {'text': note_, 'at': rs.time.time()}
        kind_ask_ = None if asked_go_ else rs._plan.kind_of(p.text, rs._pow.command(p.text), rs._pop.command(p.text), rs._pob.command(p.text), rs._pob.topic_of(p.text))
        if kind_ask_ and not rs._plan.auto(cat, kind_ask_) and (cat.get('brainsCfg') or {}).get('brains'):   # 🔁 it clarifies its plan first, unless this kind is set to just do it
            cat['proofAsk'] = {'kind': kind_ask_, 'text': str(p.text)[:200], 'at': rs.time.time()}
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, rs._plan.ask_message(kind_ask_, rs.time.time())])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        site_cmd_ = rs._ss.command(p.text, cat.get('siteManuals'), set(cat.get('siteSessions') or {}))
        poc_ = rs.re.match(r'^\s*(?:file|make|start)\s+a\s+poc\b\s*(.*)$', str(p.text or ''), rs.re.I)
        if poc_ and (cat.get('brainsCfg') or {}).get('brains') and cat_id not in rs._POC_BUSY:   # 📣 "file a poc lakers memes"
            rs._POC_BUSY.add(cat_id); rs.asyncio.create_task(rs._poc_file(cat_id, poc_.group(1).strip()[:120]))
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': '📣 Filing a PoC. Both minds read what is trending now and propose blind. Paid model calls. Nothing is posted.', 'at': rs.time.time(), 'open': 'features'}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        pob_topic_ = rs._pob.topic_of(p.text) if not (site_cmd_ and not site_cmd_.get('why')) else None
        ask_l_ = cat.get('pobLegsAsk') or {}
        if not pob_topic_ and ask_l_.get('topic') and rs.time.time() - float(ask_l_.get('at') or 0) < 900:   # 🧩 his answer to "how many legs?"
            n_l_ = rs._kb.legs_answer(p.text)
            if n_l_:
                pob_topic_ = f"{ask_l_['topic']} {n_l_} legs"; cat.pop('pobLegsAsk', None)
        ask_m_ = cat.get('pobModeAsk') or {}
        if not pob_topic_ and ask_m_.get('topic') and rs.time.time() - float(ask_m_.get('at') or 0) < 900:   # 🎯 his answer to "team to win, or a parlay slip?"
            mode_ = rs._kb.mode_of(p.text)
            if mode_:
                pob_topic_ = f"{ask_m_['topic']} {'parlay slip' if mode_ == 'parlay' else 'team to win'}"; cat.pop('pobModeAsk', None)
        if pob_topic_ and not p.auto and not rs._kb.mode_of(pob_topic_) and rs._kb.teams_in(pob_topic_) and rs._ck.key_for(cat, 'kalshi', data_dir=rs.DATA_DIR):
            cat['pobModeAsk'] = {'topic': pob_topic_, 'at': rs.time.time()}   # 🎯 ask first (owner 2026-11-15 'they should ask what kind of PoB like a team or leg parlay')
            bid_ = rs._pob_team_bid(cat, pob_topic_)   # 🧩 its team to win is already bid on this game: the one option left is a parlay slip
            say_m_ = (f"🎯 {pob_topic_}: the team to win is already bid on this game ({bid_}), so the play left is one parlay slip (its players, spreads, totals; every leg must hit)."
                      if bid_ else f"🎯 {pob_topic_}: a real bid on the team to win, or one parlay slip (the team plus its players, every leg must hit)?")
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': say_m_, 'at': rs.time.time(), 'ask': {'chips': ['Parlay slip'] if bid_ else ['Team to win', 'Parlay slip']}}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        if pob_topic_ and not p.auto and rs._kb.mode_of(pob_topic_) == 'parlay' and not rs._kb.legs_said(pob_topic_) and rs._ck.key_for(cat, 'kalshi', data_dir=rs.DATA_DIR):
            cat['pobLegsAsk'] = {'topic': pob_topic_, 'at': rs.time.time()}   # 🧩 how many legs (owner 2026-11-15 'leg parlay -> max legs')
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': f"🧩 {pob_topic_}: how many legs? Every leg must hit; Kalshi takes up to {rs._kb.SLIP_MAX} in one slip.", 'at': rs.time.time(), 'ask': {'chips': list(rs._kb.LEG_CHIPS)}}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        if not pob_topic_ and not site_cmd_ and rs.re.match(r'^\s*(?:file|make|start)\s+a\s+pob\s*$', str(p.text or ''), rs.re.I):   # no topic: it loops the best games on the board right now
            async with rs.httpx.AsyncClient(timeout=20) as http_b:
                pob_topic_ = await rs._tools.best_topic(http_b) or None
        if pob_topic_:   # 🏈 "file a pob best nfl picks": researched like a PoW, filed in Bids
            ok_, say_ = rs._pob.reply(cat.get('pobRun'), bool(cat.get('pobRead')))
            if ok_:
                cat.pop('proofSite', None); cat['pobAsk'] = pob_topic_; cat['pobBy'] = 'auto' if p.auto else 'you'; rs._POB_WANT[cat_id] = 'start'; rs._POW_WAKE.set()
                say_ = f'🎲 Filing a PoB on {pob_topic_}. Kalshi first, then major sites in its own windows; both minds call it blind. Paid model calls. ' + ('One parlay slip from Kalshi\'s own legs: it bids if both back the same legs, otherwise the stronger slip waits for your tap, inside your caps.' if rs._kb.mode_of(pob_topic_) == 'parlay' else 'A real Kalshi bid only if both back the same market, inside your caps.')
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': say_, 'at': rs.time.time(), 'open': 'bids'}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        if site_cmd_:   # 🔎 "file a pump pow": only after the owner scanned and signed in there
            say_ = site_cmd_.get('why') or rs._site_proof_start(cat, cat_id, site_cmd_['site'], site_cmd_['kind'])[1]
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': say_, 'at': rs.time.time(), 'open': {'pop': 'pop', 'pob': 'bids'}.get(site_cmd_['kind'], 'pow')}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        if rs._pob.command(p.text):
            ok_, say_ = rs._pob.reply(cat.get('pobRun'), bool(cat.get('pobRead')))
            if ok_:
                cat.pop('proofSite', None)
                if rs.re.search(r'\b(board|chips?|coins?)\b', str(p.text or ''), rs.re.I):   # only when asked: the free-chip coin board
                    cat['pobBoard'] = True
                cat['pobBy'] = 'auto' if p.auto else 'you'; rs._POB_WANT[cat_id] = 'start'; rs._POW_WAKE.set()
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': say_, 'at': rs.time.time(), 'open': 'bids'}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        pop_cmd_ = rs._pop.command(p.text)
        if pop_cmd_:
            ok_, say_ = rs._pop.reply(pop_cmd_.split(':')[0], cat.get('popRun'), cat.get('popCard'))
            if ok_:
                cat.pop('proofSite', None)
                rs._POP_WANT[cat_id] = pop_cmd_; rs._POW_WAKE.set()
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': say_, 'at': rs.time.time(), 'open': 'pop'}])[-200:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        cmd_ = rs._pow.command(p.text)
        if cmd_:   # ⛏ "file a PoW" / "PoW" / "/pow" / "A: file a PoW" / "stop PoW" — the engine starts (or ends) a folder on its next tick
            f_ = (cat.get('powRun') or {}).get('folder')
            if cmd_['do'] == 'start' and f_:
                why_ = f"⛏ {f_.get('name')} is still open ({f_.get('phase')}) — say \"stop PoW\" to end it first."
            elif cmd_['do'] == 'stop' and not f_:
                why_ = '⛏ No PoW folder is open.'
            elif cmd_['do'] == 'start' and not (cat.get('brainsCfg') or {}).get('brains'):
                why_ = '⛏ It needs a model first.'
            elif cmd_['do'] == 'start' and rs._proof_room(cat, cat_id, 'PoW'):
                why_ = rs._proof_room(cat, cat_id, 'PoW')
            else:
                cat.pop('proofSite', None)
                rs._POW_WANT[cat_id] = cmd_
                rs._POW_WAKE.set()
                who_ = {0: 'mind A', 1: 'mind B'}.get(cmd_.get('mind'), 'both minds')
                why_ = (f"{'💡 Proposing' if cmd_.get('propose') else '⛏ Filing'} a PoW with {who_}: 4 coins (2 FEELESS intake · 1 Pump · 1 DexScreener) → they agree on 1 → "
                        + ('filed as a proposal card, nothing bought.' if cmd_.get('propose') else 'buy it on FEELESS → chart / research / decide until it sells.')) if cmd_['do'] == 'start' else '⏹ Ending the PoW folder — it sells the coin if it bought one.'
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': str(p.text)[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': why_, 'at': rs.time.time(), 'open': 'pow'}])[-40:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:]}
        busy = bool(w and not w.get('done'))
        if busy and (w.get('task') or {}).get('pow'):   # ⛏ your ask outranks a Colony PoW: it stops (nothing filed, its browser closes) and yours starts
            w['task'].update(status='stopped', why='your ask came first')
            if w.get('runner'):
                w['runner'].cancel()
            busy = False
        if busy and not cat.get('workGo'):
            raise rs.HTTPException(409, 'It is still working on your last ask — stop it, wait, or LET IT GO to queue asks.')
        why = rs._cp.refusal(p.text)
        if why:
            cat['refusals'] = (list(cat.get('refusals') or []) + [{'at': rs.time.time(), 'why': why}])[-100:]
            rs._save(store)
            raise rs.HTTPException(400, why)
        if not rs._work_live(cat):
            raise rs.HTTPException(400, 'Model calls are off on this server (GENERAL_CAT_LIVE) — nothing was sent or charged.')
        if not rs._lc.can_ask(b):
            raise rs.HTTPException(400, 'It stopped 10 cents before its model credit ran out. Top up to ask again.')
        text = str(p.text or '').strip()
        if not text:
            raise rs.HTTPException(400, 'Type what you want it to do.')
        files_ = [f['id'] for f in rs._af.touch(cat, p.files)]   # ☁ attached files: the task text names them, its browser can upload them
        if not busy and not rs._co.parse_order(text):   # ❓ a coin / make-money ask: 2–3 questions first (no model call), the next message answers
            kept_ = list((cat.get('clarify') or {}).get('files') or [])   # files attached to the first ask ride with the answers
            step_, got_ = rs._cq.take(cat, text, bool(files_))
            if step_ == 'ask':
                cat['clarify']['files'] = files_
                cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': text[:400], 'at': rs.time.time()},
                               {'by': 'cats', 'text': 'Before I start — ' + ' · '.join(f'{n + 1}) {q}' for n, q in enumerate(got_)), 'at': rs.time.time(), 'ask': got_}])[-40:]
                rs.keep_owned(cat); rs._save(store)
                return {**rs._work_view(cat_id, owner=True), 'chat': cat['chat'][-20:], 'clarify': got_}
            text = got_
            files_ = [i for i in dict.fromkeys(kept_ + files_) if rs._af.find(cat, i)]
        text_ = text + rs._af.task_note([rs._af.find(cat, i) for i in files_]) + rs._know.for_ask(text)   # 📚 asked about FEELESS, its minds read the facts, not a search for its name
        if rs._co.parse_order(text):   # 💵 "buy 0.05 SOL of $BONK" in the chat is an ORDER on its wallet, not research: guards, then your OK (or auto)
            async with rs.httpx.AsyncClient(timeout=15) as http_o:
                row_ = await rs._run_order(store, cat, text, http_o)
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': text[:400], 'at': rs.time.time()}, {'by': 'cats', 'text': row_['why'], 'at': rs.time.time()}])[-40:]
            rs.keep_owned(cat); rs._save(store)
            return {**rs._as_collective(rs._work_view(cat_id, owner=True)), 'cap': min(float(cat.get('taskCap') or rs.TASK_CAP_DEFAULT), rs._task_cap_max()), 'credit': b.get('credit'), 'spent': b.get('spent'), 'chat': cat['chat'][-20:], 'live': rs._work_live(), 'order': row_}
        if busy:   # 🏇 let it go: it takes the next ask the moment this one ends
            q_ = list(cat.get('workQueue') or [])
            if len(q_) >= rs.HANDOFF_MAX:
                raise rs.HTTPException(400, f'Its queue is full ({rs.HANDOFF_MAX}) — let it work through some first.')
            cat['workQueue'] = q_ + [{'text': text_[:2600], 'to': p.to, 'at': rs.time.time(), 'files': files_}]; rs.keep_owned(cat); rs._save(store)
        else:
            rs._work_start(cat_id, cat, text_, p.to, files_)
            if (rs._WORK.get(cat_id) or {}).get('task') is not None and rs._know.asks_about(text):   # each mind's own steps carry it too, not only the plan
                rs._WORK[cat_id]['task']['personal'] = str(rs._WORK[cat_id]['task'].get('personal') or '') + rs._know.brief()
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': text[:400], 'at': rs.time.time()}])[-200:]   # 💬 your words show the moment you send them, not when it finishes
            if (rs._WORK.get(cat_id) or {}).get('task') is not None:
                rs._WORK[cat_id]['task']['youSaid'] = True
            if watching_:
                rs._WORK[cat_id]['task']['watch'] = True   # 👁 files as its own folder when it finishes
            rs.keep_owned(cat); rs._save(store)
    out = rs._as_collective(rs._work_view(cat_id, owner=True))
    return {**out, 'cap': min(float(cat.get('taskCap') or rs.TASK_CAP_DEFAULT), rs._task_cap_max()), 'credit': b.get('credit'), 'spent': b.get('spent'), 'chat': (cat.get('chat') or [])[-20:],
            'live': rs._work_live(cat), 'providers': rs._cb.chain(rs.os.environ), 'go': bool(cat.get('workGo')), 'workMode': cat.get('workMode') or 'plan',
            'cloud': (b.get('cloud') or [])[-8:], 'minds': {m: v[-8:] for m, v in (b.get('minds') or {}).items()}, 'handoffs': len((w.get('task') or {}).get('handoffs') or []) if w else 0, 'createdAt': cat.get('createdAt'),
            'logins': rs._cv.public_logins(cat), 'secrets': rs._cv.public_secrets(cat), 'signedIn': [{'site': k, 'at': v.get('at'), 'n': v.get('n', 0), 'dropped': v.get('dropped', 0)} for k, v in (cat.get('siteSessions') or {}).items()], 'challengeStats': cat.get('challengeStats') or {}, 'vaultLog': (cat.get('vaultLog') or [])[-12:], 'lastMoney': rs.last_money(store.get('events') or [], cat_id), 'media': rs._cv.clean_media(cat), 'storage': rs._af.public(cat), 'ipfs': list(reversed(cat.get('ipfs') or []))[:20],   # ☁ its cloud: pool, quota, files · ⛓ what it keeps on IPFS
            'job': cat.get('job', 'agent'), 'tools': rs._cp.toolkit(cat.get('job', 'agent'), cat.get('tools')), 'toolkits': rs._cp.TOOLS,
            'refusals': (cat.get('refusals') or [])[-20:] + [{'why': x} for x in ((w or {}).get('task') or {}).get('refusals', [])],
            'artifacts': (cat.get('artifacts') or [])[-10:] + ([] if (w or {}).get('settled') else ((w or {}).get('task') or {}).get('artifacts', [])),
            'queue': [{'text': q.get('text'), 'to': q.get('to')} for q in (cat.get('workQueue') or [])],
            'pow': rs._pow_view(cat),   # ⛏ each mind's latest Proof of Work
            'poi': rs._poi_owner_view(cat['id']) if not (p.ver and p.ver == rs._pow_ver(cat)) else None,
            'kernel': rs._kernel.view() if not (p.ver and p.ver == rs._pow_ver(cat)) else None,
            'mailbox': cat.get('mailbox'), 'setup': rs._as.view(cat), 'siteTrade': cat.get('siteTrade'), 'siteTrades': (cat.get('siteTrades') or [])[::-1], 'siteTradeAuto': bool(cat.get('siteTradeAuto')), 'warmSite': (rs._warm_for(cat_id) or {}).get('site'), 'topup': cat.get('topup'), 'topups': (cat.get('topups') or [])[::-1], 'siteManuals': cat.get('siteManuals') or {}, 'siteScan': rs._SCAN_BUSY.get(cat_id), 'watchFolders': (cat.get('watchFolders') or [])[::-1],
            'activeProofs': rs._active_proofs(cat, cat['id']), 'proofMax': rs.MAX_ACTIVE_PROOFS,   # 🗂 the desk's proof picker
            'popRead': cat.get('popRead'), 'pobRead': cat.get('pobRead'), 'pobRun': cat.get('pobRun') and rs._pob.folder(cat['pobRun']), 'pobFolders': rs._pob_view(cat),
            'popFolder': cat.get('popRun') and rs._pop.folder(cat['popRun']), 'popCard': cat.get('popCard') and rs._pop.folder(cat['popCard']),
            'popPoi': rs._poi_owner_view(rs._pop_dna_id(cat['id'])) if not (p.ver and p.ver == rs._pow_ver(cat)) else None,
            'stamps': {f_.get('id'): rs._stamp.of(k_, f_, rs.time.time()) for k_, key_ in (('PoW', 'powFolders'), ('PoP', 'popFolders'), ('PoB', 'pobFolders')) for f_ in (cat.get(key_) or [])[-30:] if f_.get('id')},
            'recoveryView': rs._rkit.view(cat.get('recoveryKit')), 'boosts': cat.get('boosts') or [], 'pocFolders': rs._poc_view(cat), 'psFolders': (cat.get('psFolders') or [])[::-1], 'proofCfg': cat.get('proofCfg') or {},
            'popFolders': rs._pop_view(cat) if not (p.ver and p.ver == rs._pow_ver(cat)) else None,
            'commands': rs._ac.commands_for((cat.get('brainsCfg') or {}).get('kind'), rs._pow.COMMANDS + rs._pop.COMMANDS + rs._pob.COMMANDS + rs._ss.commands(cat.get('siteManuals'), set(cat.get('siteSessions') or {}))),   # 💬 what it understands in the chat (cabinet + desktop list)
            'sources': [{'host': h, 'what': rs._src.WHAT.get(h, 'worked before'), **{k: (rs._src_book().get(h) or {}).get(k) for k in ('ok', 'blocked', 'last')}}
                        for h in dict.fromkeys(list(rs._src.SEED) + list(rs._src_book().keys()))][:80],   # 🌐 the sources book: tap one → sign its windows in
            'jobs': list(reversed(cat.get('jobs') or []))[:20], 'jobRates': cat.get('jobRates') or {}, 'duels': cat.get('duels') or {},   # 🗂 each request's log tree + your 👍 / 👎
            'powFolder': ({**rs._pow.folder_public((cat.get('powRun') or {}).get('folder') or {}), 'poiTrace': ((cat.get('powRun') or {}).get('folder') or {}).get('poiTrace'), 'owner': ((cat.get('powRun') or {}).get('folder') or {}).get('owner'), 'usedBy': ((cat.get('powRun') or {}).get('folder') or {}).get('usedBy')} if (cat.get('powRun') or {}).get('folder') else None),
            **({} if p.ver and p.ver == rs._pow_ver(cat) else {'powVer': rs._pow_ver(cat), 'powFolders': [x if x.get('report') or x.get('status') != 'closed' else {**x, 'report': rs._pow.report(x)[0]} for x in list(reversed(cat.get('powFolders') or []))[:40]]}),   # ⛏ the filed folders (~90 KB) only when they changed — the desk polls every 1.5 s
            'parked': [{'text': q.get('text'), 'why': q.get('why'), 'at': q.get('at')} for q in (cat.get('workParked') or [])]}


@router.get('/api/cats/{cat_id}/work/shot/{i}')
async def cat_work_shot(cat_id: str, i: int, ownerId: str = '', session: str = ''):
    """📸 A window's snapshot (JPEG) when its provider gives no live view — the cat's owner only."""
    rs = _rs()
    store = rs._load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Cat not found.')
    rs._owner_gate(store, cat, session, ownerId, 'see its windows')
    pages = (rs._WORK.get(cat_id) or {}).get('pages') or []
    pg = pages[i] if 0 <= i < len(pages) else None
    jpg = await pg.shot() if pg else None
    if not jpg:
        raise rs.HTTPException(404, 'No snapshot right now.')
    return rs.Response(content=jpg, media_type='image/jpeg', headers={'Cache-Control': 'no-store'})


def _owned(store, cat_id, owner_id, session=''):
    rs = _rs()
    cat = (store.get('cats') or {}).get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Agent not found.')
    rs._owner_gate(store, cat, session, owner_id, 'use its storage')
    return cat

