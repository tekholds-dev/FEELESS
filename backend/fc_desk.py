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


def _spend_owner(cat, store=None):
    """💵 → (the owner's key, his agents' ids, {id: name}): one day cap across every agent of the same owner wallet."""
    rs = _rs()
    cats = list(((store or rs._load()).get('cats') or {}).values())
    key, ids = rs._sg.group(cats, cat or {}); names = {c.get('id'): c.get('name') or 'agent' for c in cats if c.get('id') in ids}
    return key, ids, names


def _spend_cap(owner):
    rs = _rs()
    try:
        return rs._sg.clean_cap(rs._sg.caps_read(rs.SPEND_CAPS_PATH).get(owner, rs._sg.DAILY_CAP_USD))
    except ValueError:
        return rs._sg.DAILY_CAP_USD


def _ledger_size():
    try:
        return (_rs().DATA_DIR / 'model_receipts.jsonl').stat().st_size
    except OSError:
        return 0


def _spend_now(cat, store=None):
    """→ (owner, ids, names, cap, $ done today, $ still making)"""
    rs = _rs()
    owner, ids, names = rs._spend_owner(cat, store)
    since = rs._sg.day_start(); c_ = rs._SPEND_ROWS
    if c_.get('since') != since or c_.get('dir') != str(rs.DATA_DIR) or rs.time.time() - c_.get('at', 0) > 3 or c_.get('size') != _ledger_size():
        c_.update(since=since, dir=str(rs.DATA_DIR), at=rs.time.time(), size=_ledger_size(), rows=rs._sg.read_rows(rs.DATA_DIR / 'model_receipts.jsonl', since))   # 💵 re-read when it grew
    rows = c_['rows']
    making = sum(u for o, u in rs._SPEND_HOLD.values() if o == owner)
    return owner, ids, names, rs._spend_cap(owner), rs._sg.spent(rows, ids, rs._sg.day_start()), making, rows


def _spend_check(cat, est_usd, store=None):
    """💵 Raises spend_guard.OverCap before a paid call on the owner's own key would pass his day cap."""
    rs = _rs()
    _o, _i, _n, cap, done, making, _r = _spend_now(cat, store)
    rs._sg.check(done, making, est_usd, cap)


def _spend_hold(cat, mid, usd, store=None):
    rs = _rs()
    rs._SPEND_HOLD[str(mid)] = (rs._spend_owner(cat, store)[0], float(usd or 0))


def _spend_release(mid):
    _rs()._SPEND_HOLD.pop(str(mid), None)


def _spend_view(cat, store=None):
    rs = _rs()
    owner, ids, names, cap, _done, making, rows = _spend_now(cat, store)
    return rs._sg.view(rows, ids, names, cap, making)


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
            rs._spend_release(mid); return
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
                    rs._media_set(cat_id, ws_id, mid, keep, status='failed', why=rs._mg.plain_why(r.status_code, str((j_.get('error') or {}).get('message') if isinstance(j_.get('error'), dict) else 'no picture came back')[:160])); return
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
                        if md.get('modelId') in rs._mg.OR_SWAP:   # 🎭 OpenRouter: light copies as https links (clip ≤720p, no sound, the part it makes; picture ≤1280 px)
                            clip_du, img_du = await rs._swap_refs(cat_id, f_clip, rs._media_dir() / cat_id / str(md['fromImg']['url']).rsplit('/', 1)[-1], rs._mg.swap_max(md['modelId']))
                        meth, url, heads, body = rs._mg.v2v_req(md['modelId'], key, img_du, clip_du, md.get('note') or '', md.get('secs'), md.get('aspect'))
                    except (OSError, KeyError, ValueError) as e:
                        rs._media_set(cat_id, ws_id, mid, keep, status='failed', why=f'Its clip could not be used: {str(e)[:120]}'); return
                else:
                    meth, url, heads, body = rs._mg.submit_req(md['provider'], model_sub, md['prompt'], key, md.get('modelId'), image=img_du)
                r = await h.request(meth, url, headers=heads, json=body)
                try:
                    hd = rs._mg.handle_of(md['provider'], r.json() if r.headers.get('content-type', '').startswith('application/json') else {})
                except ValueError as e:
                    rs._media_set(cat_id, ws_id, mid, keep, status='failed', why=rs._mg.plain_why(r.status_code, e, md.get('modelId'))); return
                rs._media_set(cat_id, ws_id, mid, keep, status='running', handle=hd, step='queued')
            started = float(md.get('at') or rs.time.time())
            while True:
                if rs.time.time() - started > rs._mg.GIVE_UP_S:
                    rs._media_set(cat_id, ws_id, mid, keep, status='failed', why='It took longer than 15 minutes. Nothing more is charged from here.'); return
                r = await h.get(hd['status'], headers=rs._mg.auth(md['provider'], key))
                st, why = rs._mg.state_of(md['provider'], r.json() if r.status_code == 200 else {'status': 'running'})
                if st == 'failed':
                    rs._media_set(cat_id, ws_id, mid, keep, status='failed', why=rs._mg.plain_why(None, why) if why else 'The provider stopped it.'); return
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
            if md.get('keepSound') and (md.get('fromClip') or {}).get('url'):   # 🔊 the swap keeps your clip's own sound, same timing
                got = await rs._with_sound(rs._media_dir() / cat_id / name, rs._media_dir() / cat_id / str(md['fromClip']['url']).rsplit('/', 1)[-1]) or got
            rs._media_set(cat_id, ws_id, mid, keep, status='done', url=f'/api/cats/media/{cat_id}/{name}', kept=True, bytes=got, doneAt=round(rs.time.time()))
            rs._feed_push(cat_id, {'tone': 'done', 'kind': 'PoC', 'text': f"Your {md['kind']} is ready ({md.get('label') or md['model']})", 'ref': ws_id})
    except (rs.httpx.HTTPError, OSError, ValueError, KeyError) as e:
        rs._media_set(cat_id, ws_id, mid, None, status='failed', why=f'{type(e).__name__}: {str(e)[:120]}')
    finally:
        rs._MEDIA_LIVE.discard(mid)


async def _clip_add(cat_id, ws_id, doc_, text, tools):
    """🎞 One clip into a PoC folder (owner 2026-11-17 "add a viral video clip in there and ask them to replace the main character"): an upload
    (data URL), a Bluesky post, or a direct https video link. Longer than 30 s, or a start picked → cut to 30 s from that start (exact, H.264)."""
    rs = _rs()
    from urllib.parse import unquote as _unq, urlparse as _host
    if not tools.get('rights'):
        raise rs.HTTPException(400, 'Tick that the clip is yours, or that you have the rights to use it.')
    try:
        start = max(0.0, min(3600.0, float(tools.get('start') or 0)))
    except (TypeError, ValueError):
        start = 0.0
    src_ = str(text or '').strip(); jid = 'm' + rs.uuid.uuid4().hex[:12]
    d_ = rs._media_dir() / cat_id; d_.mkdir(parents=True, exist_ok=True); tmp = d_ / 'tmp'; tmp.mkdir(exist_ok=True)
    raw_f = tmp / f'{jid}.src'; out = d_ / f'{jid}.mp4'; stream = False; name_ = str(tools.get('name') or '')[:60]; source_ = ''
    try:
        if src_.startswith('https://'):
            try:
                how = rs._cs.classify(src_)
                async with rs.httpx.AsyncClient(timeout=25, follow_redirects=False) as h_:
                    if how[0] == 'bluesky':
                        r_ = await h_.get(rs._cs.bsky_thread_url(how[1], how[2]), headers={'User-Agent': 'FEELESS/1.0'})
                        if r_.status_code != 200:
                            raise ValueError('Bluesky did not find that post.')
                        src_, words_ = rs._cs.bsky_video(r_.json()); stream = True
                        name_ = name_ or (f'@{how[1].split(".")[0]}: {words_}' if words_ else f'@{how[1]} on Bluesky')[:60]; source_ = 'Bluesky'
                    else:
                        await rs._cp.public_url(how[1]); got = 0
                        async with h_.stream('GET', how[1], headers={'User-Agent': 'FEELESS/1.0'}) as r_:
                            if r_.status_code != 200 or not r_.headers.get('content-type', '').startswith('video/'):
                                raise ValueError('That link did not give a video file.')
                            with raw_f.open('wb') as f_:
                                async for ch_ in r_.aiter_bytes():
                                    got += len(ch_)
                                    if got > rs._pplay.MAX_CLIP:
                                        raise ValueError('That video is too big. Use a shorter clip.')
                                    f_.write(ch_)
                        src_ = raw_f; name_ = name_ or rs.re.sub(r'\.[A-Za-z0-9]+$', '', _unq(how[1].rsplit('/', 1)[-1]))[:60] or 'Linked clip'
                        source_ = _host(how[1]).hostname or ''
            except (ValueError, rs.httpx.HTTPError) as e:
                raise rs.HTTPException(400, str(e) if isinstance(e, ValueError) else 'That link did not answer. Try again, or add the file.')
        else:
            try:
                raw_, ext_ = rs._pplay.decode(src_)
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            if rs._pplay.kind_of(ext_) != 'video':
                raise rs.HTTPException(400, 'Pick a video clip (MP4, MOV or WebM).')
            raw_f = tmp / f'{jid}.{ext_}'; raw_f.write_bytes(raw_); src_ = raw_f; name_ = name_ or 'Your clip'
        secs_, _f = (None, None) if stream else await rs._clip_len(src_)
        if not stream and secs_ is None:
            raise rs.HTTPException(400, 'That clip could not be read. Export it again as an MP4.')
        cut_ = stream or start > 0 or secs_ > rs._mg.CLIP_KEEP_S + 0.5 or rs.Path(str(src_)).suffix.lower() != '.mp4'
        if cut_:
            if (await rs._ffmpeg(rs._cs.cut_args(src_, out, start, rs._mg.CLIP_KEEP_S, stream=stream), 240))[0] != 0 or not out.is_file() or not out.stat().st_size:
                out.unlink(missing_ok=True)
                raise rs.HTTPException(400, 'That clip could not be cut. Try another start, or export it again as an MP4.' if not stream else 'Bluesky\'s video did not come through. Try again in a minute.')
        else:
            rs.shutil.copyfile(src_, out)
    finally:
        raw_f.unlink(missing_ok=True)
    secs_, fps_ = await rs._clip_len(out); w_, h_ = await rs._clip_size(out)
    if secs_ is None:
        out.unlink(missing_ok=True); raise rs.HTTPException(400, 'That clip could not be read. Export it again as an MP4.')
    sha_ = rs.hashlib.sha256(out.read_bytes()).hexdigest()[:32]   # the same video added again is the clip already here, not a second card
    same_ = next((m['media']['id'] for m in doc_.get('messages') or [] if (m.get('media') or {}).get('clip') and m['media'].get('sha') == sha_), None)
    if same_:
        out.unlink(missing_ok=True)
        return {'doc': rs._ws_view(cat_id, ws_id), 'same': same_}
    now_ = round(rs.time.time())
    doc_['messages'] = list(doc_.get('messages') or []) + [{'by': 'Media', 'text': name_, 'at': now_,
        'media': {'id': jid, 'kind': 'video', 'provider': 'upload', 'model': 'your clip', 'label': name_, 'prompt': name_, 'status': 'done', 'clip': True, 'sha': sha_,
                  'secs': round(secs_, 2), 'fps': round(fps_ or 30, 2), **({'w': w_, 'h': h_} if w_ else {}), 'rights': True, 'url': f'/api/cats/media/{cat_id}/{jid}.mp4',
                  'kept': True, 'bytes': out.stat().st_size, 'at': now_, **({'cutFrom': round(start, 2)} if cut_ else {}), **({'source': source_} if source_ else {})}}]
    rs._ws_save(cat_id, doc_)
    return {'doc': rs._ws_view(cat_id, ws_id)}


async def _ffmpeg(args, timeout=180):
    """One ffmpeg / ffprobe run → (exit code, stdout). Never raises: a missing tool or a timeout is code -1."""
    rs = _rs()
    try:
        pr = await rs.asyncio.create_subprocess_exec(*args, stdout=rs.asyncio.subprocess.PIPE, stderr=rs.asyncio.subprocess.DEVNULL)
        out, _ = await rs.asyncio.wait_for(pr.communicate(), timeout)
        return pr.returncode, out or b''
    except (OSError, rs.asyncio.TimeoutError):
        return -1, b''


async def _clip_size(path):
    """A clip's width and height (ffprobe) → (w, h), or (None, None)."""
    rs = _rs()
    code, out = await rs._ffmpeg(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', str(path)], 15)
    try:
        st = (rs.json.loads(out or b'{}').get('streams') or [{}])[0]
        return (int(st['width']), int(st['height'])) if code == 0 else (None, None)
    except (ValueError, KeyError, TypeError):
        return None, None


def _public_site():
    """The site's public https address (PUBLIC_SITE_URL, e.g. the owner's tunnel), or '' when there is none."""
    u = str(_rs().os.getenv('PUBLIC_SITE_URL') or '').strip().rstrip('/')
    return u if u.startswith('https://') and '.' in u.split('/')[2] else ''


async def _swap_refs(cat_id, clip, img, max_s=None):
    """🎭 Light copies for an OpenRouter swap: the clip ≤720p without sound (only the part the model makes), the picture as a ≤1280 px JPEG.
    They go as 2-hour https links (OpenRouter refuses anything else: "Only HTTPS URLs are allowed"): on PUBLIC_SITE_URL when set, else on a
    Cloudflare quick tunnel that serves only these files (pub_tunnel). A link that cannot open stops the swap before anything is sent."""
    rs = _rs()
    tmp = rs._media_dir() / cat_id / 'tmp'; tmp.mkdir(parents=True, exist_ok=True); tag = rs.uuid.uuid4().hex[:8]
    rc, ri = tmp / f'{tag}.mp4', tmp / f'{tag}.jpg'
    try:
        if (await rs._ffmpeg(rs._cs.ref_args(clip, rc, max_s)))[0] != 0 or not rc.is_file():
            raise ValueError('your clip could not be prepared (export it again as an MP4)')
        if (await rs._ffmpeg(rs._cs.img_args(img, ri), 60))[0] != 0 or not ri.is_file():
            raise ValueError('the character picture could not be prepared')
        pub = rs._media_dir() / cat_id / 'pub'; pub.mkdir(exist_ok=True)
        for old in pub.iterdir():   # the expired ones go
            if rs.time.time() - old.stat().st_mtime > PUBREF_S:
                old.unlink(missing_ok=True)
        names = [f'{rs.secrets.token_urlsafe(24)}.{x}' for x in ('mp4', 'jpg')]
        rc.replace(pub / names[0]); ri.replace(pub / names[1])
        site = rs._public_site()
        if site:
            return tuple(f'{site}/api/cats/pubref/{cat_id}/{n}' for n in names)
        try:
            tun = await rs._pubt.ensure(rs._media_dir())
        except Exception:
            for n in names:
                (pub / n).unlink(missing_ok=True)
            raise
        return tuple(f'{tun}/{cat_id}/pub/{n}' for n in names)
    finally:
        rc.unlink(missing_ok=True); ri.unlink(missing_ok=True)


async def _with_sound(made, clip):
    """🔊 Lay the original clip's sound on the made video (in place). → the new size, or None when the clip has no sound or ffmpeg fails (the video stays as made)."""
    if made.suffix.lower() != '.mp4':
        return None
    out = made.with_name(made.stem + '.snd.mp4')
    code, _ = await _rs()._ffmpeg(_rs()._cs.sound_args(made, clip, out))
    if code != 0 or not out.is_file() or not out.stat().st_size:
        out.unlink(missing_ok=True); return None
    out.replace(made); return made.stat().st_size


async def _edit_post(cat_id, cat, store, name, video, tools):
    """📤 One tap Post (owner 2026-11-17, studio proposal 5): the finished edit, rendered on the owner's device, goes into a PoC folder (one he
    picks, or a new one named after the edit), with its source clip beside it as a 15 s clip the folder can swap a character into.
    → {'ws', 'name'}. The video must really be a video (poc_play.decode checks the bytes) and at most poc_play.MAX_CLIP."""
    rs = _rs()
    if not tools.get('rights'):
        raise rs.HTTPException(400, 'Tick that the video is yours, or that you have the rights to post it.')
    try:
        raw_, ext_ = rs._pplay.decode(video)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    if rs._pplay.kind_of(ext_) != 'video':
        raise rs.HTTPException(400, 'Post a rendered video (MP4 or WebM).')
    name_ = ' '.join(str(name or '').split())[:60] or 'Your edit'
    ws_ = str(tools.get('ws') or '')
    if ws_:
        doc_ = rs._ws_load(cat_id, ws_)
        if not doc_ or doc_.get('kind') != 'content':
            raise rs.HTTPException(400, 'Edits go in a PoC folder.')
    else:
        try:
            row_ = rs._feat.new_folder(cat, 'content', name_[:32], rs.time.time())
        except ValueError as e:
            raise rs.HTTPException(409, str(e))
        doc_ = rs._feat.new_doc(row_); ws_ = row_['id']; rs._ws_save(cat_id, doc_); rs.keep_owned(cat); rs._save(store)
    src_mid = None
    if tools.get('source'):   # 🎞 its source clip rides along through the same door as Add your clip (rights, 15 s, H.264)
        doc_ = (await rs._clip_add(cat_id, ws_, doc_, tools['source'], {'rights': True, 'name': f'Source · {name_}'[:60]})) and rs._ws_load(cat_id, ws_)
        src_mid = next((m['media']['id'] for m in reversed(doc_.get('messages') or []) if (m.get('media') or {}).get('clip')), None)
    jid = 'm' + rs.uuid.uuid4().hex[:12]; d_ = rs._media_dir() / cat_id; d_.mkdir(parents=True, exist_ok=True); f_ = d_ / f'{jid}.{ext_ if ext_ != "quicktime" else "mov"}'
    f_.write_bytes(raw_)
    secs_, fps_ = await rs._clip_len(f_); w_, h_ = await rs._clip_size(f_)
    if secs_ is None:
        f_.unlink(missing_ok=True); raise rs.HTTPException(400, 'That video could not be read. Export it again.')
    now_ = round(rs.time.time()); clip_ = rs._media_dir() / cat_id
    edit_ = rs._play.edit_stats(rs._play.clean_project(tools.get('project'))) if isinstance(tools.get('project'), dict) else {}
    doc_['messages'] = list(doc_.get('messages') or []) + [{'by': 'Media', 'text': f'Posted: {name_}', 'at': now_,
        'media': {'id': jid, 'kind': 'video', 'provider': 'upload', 'model': 'your edit', 'label': name_, 'prompt': name_, 'status': 'done', 'posted': True,
                  'secs': round(secs_, 2), 'fps': round(fps_ or 30, 2), **({'w': w_, 'h': h_} if w_ else {}), 'rights': True, 'url': f'/api/cats/media/{cat_id}/{f_.name}',
                  'kept': True, 'bytes': f_.stat().st_size, 'at': now_, **({'edit': edit_} if edit_ else {}),
                  **({'fromClip': {'mid': src_mid, 'url': f'/api/cats/media/{cat_id}/{src_mid}.mp4'}} if src_mid and (clip_ / f'{src_mid}.mp4').is_file() else {})}}]
    rs._ws_save(cat_id, doc_)
    rs._feed_push(cat_id, {'tone': 'done', 'kind': 'PoC', 'text': f'Posted your edit: {name_}', 'ref': ws_})
    return {'ws': ws_, 'name': doc_.get('name') or name_}


async def _edit_captions(cat, video, max_s=None):
    """💬 Auto captions (studio proposal 3) on the agent's OWN OpenRouter key: the clip's sound (≤ 60 s, mono MP3) → an audio-reading model →
    timed lines. The clip itself never leaves this server; only its sound goes to OpenRouter. → {'captions': [...], 'usd'}."""
    rs = _rs()
    key_ = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
    if not key_:
        raise rs.HTTPException(400, 'Link your OpenRouter key first: captions run on your own key (about $0.001 a minute).')
    try:
        raw_, ext_ = rs._pplay.decode(video)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    if rs._pplay.kind_of(ext_) != 'video':
        raise rs.HTTPException(400, 'Captions read a video clip.')
    tmp = rs._media_dir() / str(cat.get('id') or 'x') / 'tmp'; tmp.mkdir(parents=True, exist_ok=True); tag = rs.uuid.uuid4().hex[:8]
    src_, aud_ = tmp / f'{tag}.{ext_ if ext_ != "quicktime" else "mov"}', tmp / f'{tag}.mp3'
    cap_s = max(1.0, min(float(max_s or rs._cs.CAPTION_MAX_S), rs._cs.CAPTION_MAX_S))
    try:
        src_.write_bytes(raw_)
        if (await rs._ffmpeg(rs._cs.audio_args(src_, aud_, cap_s), 60))[0] != 0 or not aud_.is_file() or not aud_.stat().st_size:
            raise rs.HTTPException(400, 'That clip has no sound to caption.')
        b64_ = rs.base64.b64encode(aud_.read_bytes()).decode()
    finally:
        src_.unlink(missing_ok=True); aud_.unlink(missing_ok=True)
    body_ = {'model': rs._cs.CAPTION_MODEL, 'temperature': 0, 'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': rs._cs.CAPTION_ASK}, {'type': 'input_audio', 'input_audio': {'data': b64_, 'format': 'mp3'}}]}]}
    try:
        async with rs.httpx.AsyncClient(timeout=90) as h_:
            r_ = await h_.post('https://openrouter.ai/api/v1/chat/completions', headers={'Authorization': f'Bearer {key_}', 'Content-Type': 'application/json'}, json=body_)
        j_ = r_.json() if r_.headers.get('content-type', '').startswith('application/json') else {}
    except (rs.httpx.HTTPError, ValueError):
        raise rs.HTTPException(502, 'OpenRouter did not answer. Nothing changed; try again.')
    if r_.status_code != 200:
        why_ = (j_.get('error') or {}).get('message') if isinstance(j_.get('error'), dict) else ''
        raise rs.HTTPException(502, f'OpenRouter said {r_.status_code}: {str(why_ or "no captions")[:140]}')
    text_ = (((j_.get('choices') or [{}])[0].get('message') or {}).get('content')) or ''
    usd_ = (j_.get('usage') or {}).get('cost')
    return {'captions': rs._cs.parse_captions(text_ if isinstance(text_, str) else '', cap_s), 'usd': round(float(usd_), 5) if usd_ is not None else None, 'model': rs._cs.CAPTION_MODEL}


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


async def _or_left(key):
    """💵 → dollars left on an OpenRouter account (credits minus usage, or the key's own limit if lower), from two free reads; None if unknown."""
    rs = _rs()
    try:
        async with rs.httpx.AsyncClient(timeout=8) as h_:
            auth = {'Authorization': f'Bearer {key}'}
            c_ = await h_.get('https://openrouter.ai/api/v1/credits', headers=auth)
            k_ = await h_.get('https://openrouter.ai/api/v1/key', headers=auth)
        d_ = c_.json().get('data') or {} if c_.status_code == 200 else {}
        if d_.get('total_credits') is None:
            return None
        left = float(d_.get('total_credits') or 0) - float(d_.get('total_usage') or 0)
        lim = (k_.json().get('data') or {}).get('limit_remaining') if k_.status_code == 200 else None
        return round(min(left, float(lim)) if lim is not None else left, 2)
    except Exception:   # noqa: BLE001 — unknown balance: the provider still refuses for free if it is short
        return None


async def _media_swap(cat_id, ws_id, doc_, t_, linked, text, cat=None, store=None):
    """🎭 V2V: a clip already in this folder + a finished picture (the folder's character unless one is picked) → one fal.ai job. Nothing runs
    without fal.ai linked; the list-price estimate rides on the card before it starts."""
    rs = _rs()
    mid_ = str(t_.get('swap') or '')
    if mid_ == 'auto':   # 💬 a chat ask ("replace the main character with Bishop"): the model picked last, else Runway Aleph 2 (real footage) on OpenRouter, else fal.ai's Wan
        mid_ = rs._mg.swap_auto(linked, (cat or {}).get('swapLast')) or ''
        if not mid_:
            raise rs.HTTPException(400, 'Link your OpenRouter key first: the swap runs on your own OpenRouter account (Seedance 2.0).')
    if mid_ not in rs._mg.V2V:
        raise rs.HTTPException(400, 'Pick Seedance Replace, Wan Replace, Kling Motion Control or FLUX Video Edit.')
    prov_ = rs._mg.v2v_provider(mid_); edit_ = mid_ in rs._mg.V2V_NO_CHAR
    if prov_ not in linked:
        raise rs.HTTPException(400, f"Link {rs._mg.PROVIDERS[prov_]['name']} first: this runs on your own {rs._mg.PROVIDERS[prov_]['name']} account.")
    want_clip = str(t_.get('clip') or '')
    if want_clip == 'last':   # 💬 the chat swaps the newest clip in this folder
        want_clip = next((str(m['media']['id']) for m in reversed(doc_.get('messages') or []) if (m.get('media') or {}).get('clip') and m['media'].get('status') == 'done'), '')
    cmd_ = (rs._media_msg(doc_, want_clip) or {}).get('media') or {}
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
    ref_ = mid_ in rs._mg.OR_SWAP; shape_ = {}; most_ = rs._mg.swap_max(mid_)   # an OpenRouter swap makes the first `most_` s itself
    if not ref_ and float(cmd_.get('secs') or 0) > most_ + 0.5:
        raise rs.HTTPException(400, f'{rs._mg.V2V[mid_][1]} takes {most_} s at most. That clip is {float(cmd_.get("secs") or 0):.0f} s: pick an OpenRouter swap, or add it again with a start.')
    if ref_:
        if mid_ in rs._mg.SEEDANCE_SWAP and float(cmd_.get('secs') or 0) < rs._mg.SEEDANCE_MIN_S - 0.5:
            raise rs.HTTPException(400, f'Seedance makes {rs._mg.SEEDANCE_MIN_S} to {most_} s. That clip is {float(cmd_.get("secs") or 0):.1f} s: add a longer one.')
        w_, h_ = cmd_.get('w'), cmd_.get('h')
        if not (w_ and h_):
            w_, h_ = await rs._clip_size(rs._media_dir() / cat_id / str(cmd_['url']).rsplit('/', 1)[-1])
        shape_ = {'aspect': rs._cs.nearest_aspect(w_, h_), 'secs': min(float(cmd_.get('secs') or most_), most_), 'keepSound': True}
    ep_, label_ = rs._mg.V2V[mid_][:2]; usd_ = rs._mg.v2v_cost(mid_, min(float(cmd_.get('secs') or most_), most_), cmd_.get('fps') or 30)
    cap_ = float((cat or {}).get('swapCapUsd') or rs._mg.SWAP_CAP_USD)   # 💵 the owner's own cap per swap
    if usd_ > cap_ + 1e-9:
        raise rs.HTTPException(400, f'This swap is about ${usd_:.2f}, over your ${cap_:.2f} cap per swap. Raise the cap under the swap button, or pick a cheaper model or a shorter clip.')
    try:
        rs._spend_check(cat or {}, usd_)   # 💵 and the owner's day cap across all his agents
    except rs._sg.OverCap as e:
        raise rs.HTTPException(429, str(e))
    if rs._mg.swap_hold(mid_) is not None:   # 💵 Aleph: OpenRouter wants its 30 s longest on the account first; say so before a job is made (a free read)
        okey_ = rs._ck.key_for(cat or {}, 'openrouter', data_dir=rs.DATA_DIR)
        words_hold = rs._mg.hold_words(mid_, await rs._or_left(okey_) if okey_ else None, usd_)
        if words_hold:
            raise rs.HTTPException(402, words_hold)
    note_ = rs.re.sub(r'\s+', ' ', str(text or '')).strip()[:500]
    jid = 'm' + rs.uuid.uuid4().hex[:12]; now_ = round(rs.time.time())
    words_ = (f"{cmd_.get('label') or 'Your clip'}, edited: {note_}" if edit_ else f"{doc_.get('title') or doc_.get('name') or 'Your character'} swapped into {cmd_.get('label') or 'your clip'}" + (f' · {note_}' if note_ else ''))
    doc_['messages'] = list(doc_.get('messages') or []) + [{'by': 'Media', 'text': words_, 'at': now_,
        'media': {'id': jid, 'kind': 'video', 'provider': prov_, 'model': ep_, 'modelId': mid_, 'label': label_, 'usd': usd_, 'prompt': words_, 'note': note_,
                  'status': 'queued', 'at': now_, 'swap': True, **({} if edit_ else {'fromImg': {'mid': img_, 'url': smd_['url']}}), 'fromClip': {'mid': cmd_['id'], 'url': cmd_['url']}, **shape_}}]
    rs._ws_save(cat_id, doc_); rs._spend_hold(cat or {}, jid, usd_)
    if cat is not None and store is not None and not edit_:   # 📊 "most used" + the chat's next auto pick
        used_ = dict(cat.get('swapUsed') or {}); used_[mid_] = int(used_.get(mid_) or 0) + 1
        cat['swapUsed'] = used_; cat['swapLast'] = mid_; rs.keep_owned(cat); rs._save(store)
    rs.asyncio.create_task(rs._media_run(cat_id, ws_id, jid))
    return {'doc': rs._ws_view(cat_id, ws_id)}


PUBREF_S = 2 * 3600   # a public reference link lives 2 hours: long enough for the provider to fetch it, then it is gone


@router.get('/api/cats/pubref/{cat_id}/{name}')
async def cat_pubref(cat_id: str, name: str):
    """🔗 A swap's reference copy (clip ≤720p without sound, or the character JPEG) for the video provider to fetch (OpenRouter asks for public
    https links). The name is a random 32-character token: the link is the permission, and it stops working after 2 hours."""
    rs = _rs()
    from starlette.responses import FileResponse
    if not rs.re.fullmatch(r'[A-Za-z0-9_-]{1,64}', cat_id) or not rs.re.fullmatch(r'[A-Za-z0-9_-]{32}\.(mp4|jpg)', name):
        raise rs.HTTPException(404, 'No such file.')
    f_ = rs._media_dir() / cat_id / 'pub' / name
    if not f_.is_file() or rs.time.time() - f_.stat().st_mtime > PUBREF_S:
        raise rs.HTTPException(404, 'No such file.')
    return FileResponse(f_, headers={'Cache-Control': 'no-store'})


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


def _studio_slot(base, ws_id=''):
    """🗂 The 3D studio's own save (scene '3d', module 'code3d'): one per PoStatic folder, and one for a scene started from the PoStatic home."""
    return f'{base}_{ws_id}' if ws_id else base


def _play_save(cat_id, name, data):
    rs = _rs()
    f_ = rs._play_path(cat_id, name); f_.parent.mkdir(parents=True, exist_ok=True); tmp_ = f_.with_suffix('.tmp'); tmp_.write_bytes(rs._ck.seal_bytes(rs.json.dumps(data).encode(), cat_id)); tmp_.replace(f_)


async def _ws_ask(cat, model, sys_, user_, tokens):
    rs = _rs()
    own_ = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
    if own_ and not str(model).startswith('local/') and not str(model).endswith(':free'):
        rs._spend_check(cat, 0)   # 💵 the owner's day cap: refused before the call, never after
    text_, usd_, _via = await rs._think(cat, model, [{'role': 'system', 'content': rs._general_mind(cat) + sys_}, {'role': 'user', 'content': user_}], own_, ((cat.get('brainsCfg') or {}).get('efforts') or {}).get(model), tokens)   # Slice 1: Brains' effort for this mind
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
            rs._record_file(c_, 'pos', filed_)   # 🧾 Slice 0: the minds that really built it (PoStatic folders recorded none), its sources, its footprint (and TEST)


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
        doc['scene3d'] = rs._play.clean_scene(first); doc['scene3dNext'] = rs._play.clean_scene(second) if second else None; rs._play_save(cat_id, rs._studio_slot('3d', doc.get('id')), {'scene': doc['scene3d'], 'mind': doc['scene3d']})
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
    cur_ = (doc.get('versions') or [{}])[-1].get('html') or ''; had_ = (doc.get('game') or {}).get('design')
    if had_ and cur_ and had_.get('engine') in rs._forge.ENGINES:
        # 🎮 owner's real run 2026-11-17 ("fix the game so it actually works"): a game that already exists is changed, never re-designed from
        # the ask alone (that sent 'Game Fix Needed … send the game code' and threw his game away). Its design stays; the current file + the ask go in.
        design = had_; eng = rs._forge.ENGINES[design['engine']]
        stage('build', name(lead))
        raw, usd, own = await rs._ws_page(cat, brains[lead], rs._forge.change_sys(design, text), f'{text}\n\nTHE CURRENT FILE (change it as asked, keep what works):\n{cur_[:60000]}', 12000); cost += usd
    else:
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
        rs._feat.add_version(doc, rs._play.lock_site(rs._play.to_html(first_, doc.get('name'), next_)), 'FEELESS', rs.time.time()); rs._play_save(cat_id, rs._studio_slot('3d', doc.get('id')), {'scene': doc[slot], 'mind': doc[slot]})
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
    kit_read_ = rs._play.rejected_line(was_) + rs._kits.line(rs.KITS_DIR, 'pos', picks_k_)[:2500] + stash_ + rs._kits.skills_line(cat.get('brainsCfg')) + rs._foot.note('pos', cat.get('psFolders')) + rs._convo(cat, page=True) + ('\n' + rs._play.print_line(print_) if print_ else '') + rs._om.scene_line(doc.get('models3d'))
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
    scene = rs._om.on_set(rs._play.lead_up(await resolve(scene)), doc.get('models3d'))   # 🪦 the owner's own models stand on the set, exact files
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
    scene = rs._om.on_set(rs._play.ensure_asks(rs._play.drop_rejected(scene, was_), text, doc.get('name')), doc.get('models3d'))   # a check never takes them away
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
    doc['scene3d'] = first_; doc['kitsUsed'] = [{'id': 'three', 'name': 'three.js', 'used': True}]; rs._feat.add_version(doc, html, by, rs.time.time()); rs._play_save(cat_id, rs._studio_slot('3d', doc.get('id')), {'scene': scene, 'mind': scene}); rs._play_save(cat_id, 'refs', rs._play.add_reference(rs._play_load(cat_id, 'refs') or [], doc.get('name'), prompt, scene))
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
        if kind == 'build' and (rs._play.wants_game(text) or (doc.get('game') or {}).get('design')) and not doc.get('scene3d') and not doc.get('ad'):   # 🎮 a folder that holds a game: every ask ("Finish it.", "fix marked area") changes that game through the playtest, never as text patches that missed 6 times on 2026-11-17   # 🎮 AGT-35: a game is designed, engine-built and playtested, never a template (an ad's brief reads like a game: 'plays by itself in a loop'; it is a page)
            usd_, stop_why, paid_own = await rs._build_game(cat, doc, text + rs._feat.region_note(region), brains, order, name, to)
            cost += usd_
        elif kind == 'build' and not doc.get('ad') and rs._play.wants_scene_builder(text, doc):   # 🧊 owner 2026-11-17 ("regardless of model it chooses the same 3D layout"): the photoscan set builder is for a scene he asks for by name; every other 3D or page ask is written by the picked minds themselves   # 🧊 owner 2026-11-06: a 3D prompt is built in the 3D studio with real assets and checked against the prompt, never hand written. A plain game is written by the minds (owner 2026-11-07: the runner template came back for every arcade ask); a 3D game still goes to the studio
            lead_ = len(doc.get('versions') or []) % len(order) if to == 'both' and len(order) > 1 else 0   # 🧠🧠 owner 2026-11-07 "only ONE mind seems to work": with both picked, the minds take turns leading a 3D round and the other checks it
            usd_, stop_why, paid_own = await rs._build_3d(cat, doc, text, brains, order[lead_:] + order[:lead_], name, to)
            cost += usd_
        elif kind == 'build':
            if doc.get('scene3d'):
                doc['pageOwned'] = True   # the minds now own this page: the set builder comes back only when an ask names the scene (play_studio.wants_scene_builder)
            cur = (doc.get('versions') or [{}])[-1].get('html') or ''; cfg_ = rs._feat.build_cfg(doc); pl_ = doc.get('plan') or {}
            read_ = ''
            if not cur:   # a new page learns from the best first. An edit already has its page
                read_, doc['sitesRead'] = await rs._site_reads('pos', (cat['id'], cat.get('name')))
            if not cur and not region and not pl_.get('approved') and (cfg_['research'] or cfg_['suggest']):   # 🔎 a proof proves first: read the best current builds, then suggest, before anything is built
                doc['stage'] = 'research'; rs._ws_save(cat_id, {**doc, 'busy': {'at': round(rs.time.time()), 'to': to, 'stage': 'research'}})
                async with rs.httpx.AsyncClient(timeout=12) as http_r:
                    refs_ = await rs._tools.build_refs(http_r, text, cfg_['depth'] == 'deep') if cfg_['research'] else []
                doc['stage'] = 'suggest'; rs._ws_save(cat_id, {**doc, 'busy': {'at': round(rs.time.time()), 'to': to, 'stage': 'suggest'}}); open_ = [r for r in refs_ if r.get('open')]
                back_ = None
                for try_ in range(2):   # 👣 Slice 0: a plan that reads mostly the references a past PoStatic read is sent back ONCE, with those left out
                    menu_ = '\n'.join(f"{i + 1}. {r['title']} ({r['source']}, {r['score']}): {r['why']}" for i, r in enumerate(open_)) or 'None found.'
                    plan_ = rs._OR_PLUGINS.set(tuple(rs._feat.or_plugins(cfg_, json_reply=True)))
                    try:
                        raw_, usd_, own_ = await rs._ws_ask(cat, brains[order[0]], rs._feat.plan_sys(text) + rs._feat._sources.proof_line('pos') + read_ + rs._recall(cat, 'Code', text) + rs._foot.note('pos', cat.get('psFolders')) + (rs._prec.back_line({'pos': back_}, 'pos', rs.time.time()) if try_ else ''), f'The owner wants: {text}\nReferences:\n{menu_}', 420)
                    finally:
                        rs._OR_PLUGINS.reset(plan_)
                    cost += usd_; paid_own = own_; doc['lastCost'] = round(cost, 6); doc['plan'] = {'ask': text, 'to': to, 'allRefs': refs_, 'plan': rs._feat.parse_plan(raw_, open_), 'by': name(order[0]), 'at': round(rs.time.time()), 'approved': not cfg_['suggest']}
                    draft_ = {'id': 'draft', 'ws': ws_id, 'topic': str(doc.get('name') or 'Page')[:60], 'refs': [{k: r.get(k) for k in ('title', 'url', 'source')} for r in doc['plan']['plan'].get('refs') or []]}
                    store_b_ = rs._load(); c_b_ = store_b_['cats'].get(cat_id)
                    if try_ or not c_b_ or not rs._foot_back(c_b_, 'pos', draft_):
                        break
                    back_ = c_b_['footBack']['pos']; rs._save(store_b_); bad_ = set(back_.get('avoid') or [])
                    kept_ = [r for r in open_ if rs._prec._host(r.get('url')) not in bad_]
                    open_ = kept_ if len(kept_) >= 2 else open_
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
            if (rs._assets.wants_3d(text) or doc.get('scene3d')) and 'three' not in picks_ and not doc.get('ad'):   # 🧊 a 3D ask written by the minds: real three.js, their own design
                picks_ = ['three', *picks_]
            picks_ = list(rs._ads.KITS) if doc.get('ad') else picks_   # 🎬 an ad gets GSAP, never a game kit (Phaser dragged in the game playtest and its STATE / SCORE counter, 2026-11-11)
            stash_, doc['kitsStash'] = rs._kits.stash_line(rs.KITS_DIR, 'pos', text, picks_)
            kits_ = rs._kits.use_line(picks_) + stash_ + rs._parts.offer_line(rs._parts.offer(rs._parts_path(), text)) + rs._mark_lessons() + rs._kits.skills_line(cat.get('brainsCfg')) + rs._foot.note('pos', cat.get('psFolders')) + rs._recall(cat, 'Code', text) + rs._om.page_line(doc.get('models3d'))   # 🧰 the kits it was told to use reach the build itself, not only the plan
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
                        patch_raw, patch_usd, patch_own = await rs._ws_ask(cat, brains[i], rs._feat.EDIT_SYS + kits_, f"Owner request: {text[:1200]}{rs._feat.region_note(region)}" + (f'\nStill left from your last reply: {said_}' if said_ else '') + f'\nCurrent page:\n{html[:rs._feat.PAGE_PROMPT_CHARS]}', rs._feat.EDIT_REPLY_TOKENS)
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
                    pk3_ = [*picks_, 'three'] if doc.get('models3d') and 'three' not in picks_ else picks_   # 🪦 the owner's models are live three.js
                    html = rs._kits.open_for_kits(rs._kits.with_kit_tags(rs._om.mount(html, doc.get('models3d')), pk3_), pk3_); doc['kitsUsed'] = rs._kits.kit_report(html, picks_); doc['kitsOutside'] = rs._kits.outside_files(html, picks_)
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
    except rs._sg.OverCap as e:   # 💵 his day cap: it stops before the next paid call, and says so
        rs._feat.add_msg(doc, 'FEELESS', str(e), rs.time.time())
        stop_why = str(e)
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


