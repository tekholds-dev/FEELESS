"""🧹 Cat cloud, files, profile routes — moved whole out of feecat_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches feecat_service still
reaches it, and every function here is still reachable on feecat_service under its own name. Constants, classes and state live in the service."""
import feecat_service as _RSM  # noqa: E402,F401  (body models; this module is imported at the END of the service)
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401

router = APIRouter()


def _rs():
    import feecat_service
    return feecat_service


def _cloud_redirect():
    rs = _rs()
    return (rs.os.environ.get('FEELESS_PUBLIC_URL') or 'http://localhost:51367').rstrip('/') + '/api/cats/cloud/callback'


async def _cloud_token(http, cat):
    rs = _rs()
    link = cat.get('cloudLink') or {}
    if not link.get('sealed'):
        raise rs.HTTPException(400, 'Connect its cloud first.')
    try:
        return link['provider'], await rs._acl.access(http, link['provider'], rs._ck.unseal(link['sealed'], cat['id'], data_dir=rs.DATA_DIR))
    except ValueError as e:
        raise rs.HTTPException(400, str(e))


@router.get('/api/cats/cloud/callback')
async def cat_cloud_callback(code: str = '', state: str = '', error: str = ''):
    """The provider sends its sign-in back here: the code → a refresh pass sealed with the agent's own key → back to the agents page."""
    rs = _rs()
    got = rs._acl.take_state(state)
    ok = False
    if got and code and not error:
        cid, prov = got
        store = rs._load(); cat = store['cats'].get(cid)
        if cat:
            try:
                async with rs.httpx.AsyncClient() as http:
                    refresh = await rs._acl.exchange(http, prov, code, rs._cloud_redirect())
                cat['cloudLink'] = {'provider': prov, 'label': rs._acl.PROVIDERS[prov]['label'], 'sealed': rs._ck.seal(refresh, cid), 'at': round(rs.time.time())}
                rs.vault_log(cat, 'cloud connected', rs._acl.PROVIDERS[prov]['label']); rs.keep_owned(cat); rs._save(store); ok = True
            except Exception as e:
                print(f'[feecat] cloud connect failed: {str(e)[:120]}')
    return rs.Response(status_code=303, headers={'Location': f"/terminal/feecat/agents?cloud={'ok' if ok else 'failed'}"})


@router.post('/api/cats/{cat_id}/cloud/connect')
async def cat_cloud_connect(cat_id: str, p: _RSM.CloudPayload):
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Agent not found.')
    rs._owner_gate(store, cat, p.session, p.ownerId, 'connect its cloud')
    try:
        return {'url': rs._acl.start(cat_id, p.provider or '', rs._cloud_redirect())}
    except ValueError as e:
        raise rs.HTTPException(400, str(e))


@router.post('/api/cats/{cat_id}/cloud/disconnect')
async def cat_cloud_disconnect(cat_id: str, p: _RSM.CloudPayload):
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Agent not found.')
    rs._owner_gate(store, cat, p.session, p.ownerId, 'change its cloud')
    if cat.pop('cloudLink', None):
        rs.vault_log(cat, 'cloud disconnected', ''); rs.keep_owned(cat); rs._save(store)
    return {'ok': True}


def _slot_of(cat, model, default=0):
    """Which of its monitors a model owns (its place in brains) — mind B working alone never paints over mind A's last page."""
    ms = [str(m) for m in ((cat or {}).get('brainsCfg') or {}).get('brains') or []]
    return ms.index(str(model)) if str(model) in ms else default


def _last_put(cat_id, slot, jpg):
    rs = _rs()
    rs._LAST[(cat_id, slot)] = jpg
    try:
        rs.SHOTS_DIR.mkdir(parents=True, exist_ok=True); (rs.SHOTS_DIR / f'{rs.re.sub(r"[^a-z0-9]", "", cat_id.lower())[:40]}_{int(slot)}.jpg').write_bytes(jpg)
    except OSError:
        pass


def _last_get(cat_id, slot):
    rs = _rs()
    got = rs._LAST.get((cat_id, slot))
    if got is None:
        f_ = rs.SHOTS_DIR / f'{rs.re.sub(r"[^a-z0-9]", "", str(cat_id).lower())[:40]}_{int(slot)}.jpg'
        got = rs._LAST[(cat_id, slot)] = f_.read_bytes() if f_.exists() else b''
    return got or None


@router.get('/api/cats/{cat_id}/last/{slot}')
async def cat_last_page(cat_id: str, slot: int):
    """🖼 The last page this model's monitor showed — every idle / finished monitor rests on it (owner 2026-11-01), never a live browser."""
    rs = _rs()
    cat = rs._load()['cats'].get(cat_id)
    jpg = rs._last_get(cat_id, slot) if cat and not cat.get('incognito') and 0 <= slot < 8 else None
    if not jpg:
        raise rs.HTTPException(404, 'No last page yet.')
    return rs.Response(content=jpg, media_type='image/jpeg', headers={'Cache-Control': 'no-store', 'X-Last-Page': '1'})


def _pub_cursor(c):
    try:
        if not c:
            return None
        page = {k: round(min(1, max(0, float(c[k]))), 3) for k in ('px', 'py') if c.get(k) is not None}   # 🖱 AGT-19: page shares for the screenshots
        return {'x': round(min(1, max(0, float(c['x']))), 3), 'y': round(min(1, max(0, float(c['y']))), 3), **page, 'act': str(c.get('act') or 'move')[:10], 'at': c.get('at')}
    except (KeyError, TypeError, ValueError):
        return None


def public_live(w, cat=None):
    """👀 What a VISITOR may see of an agent's windows (owner 2026-10-31: "like Crawl, but no steps"): model, status, the site's host and whether a
    live SCREEN is showing — never a step list, the full URL, the owner's ask or what it typed, never a link that can drive the browser.
    A window handed to its owner (a sign-in / a check) is FROZEN for everyone else; an incognito agent shows no screens at all. Pure."""
    rs = _rs()
    t = (w or {}).get('task') or {}
    hide = bool((cat or {}).get('incognito'))
    out = []
    for x in t.get('windows') or []:
        host = str(x.get('url') or '').split('://')[-1].split('/')[0].split('?')[0][:60]
        frozen = x.get('status') == 'human'
        private_ = (rs._vv.private_page(x.get('url')) or (bool(cat) and rs._signed_host(cat, x.get('url')))) if x.get('url') else False   # 👀 a mailbox, an account page or a site it is signed in to: blank for visitors, its address out too
        host = '' if private_ else host
        live_ = x.get('status') == 'working' and str(x.get('url') or '').startswith('http')
        slot_ = rs._slot_of(cat, x.get('model'), int(x.get('i') or 0))
        last_ = not live_ and bool(rs._last_get(str((cat or {}).get('id') or ''), slot_))   # 🖼 a finished window keeps its last page
        out.append({'i': x.get('i'), 'slot': slot_, 'model': str(x.get('model') or '').split('/')[-1][:40], 'status': x.get('status') or 'idle', 'host': '' if hide else host,
                    'frozen': frozen, 'private': private_, 'screen': bool((live_ or last_) and not hide and not frozen), 'last': bool(last_ and not hide and not frozen),
                    'cursor': None if hide or frozen else rs._pub_cursor(x.get('cursor'))})   # 🖱 where its mouse is (a position only — never what it typed)
    if not out and cat and not hide:   # no task in memory: still its last frames, if any
        out = [{'i': k, 'slot': k, 'model': '', 'status': 'idle', 'host': '', 'frozen': False, 'screen': True, 'last': True} for k in range(2) if rs._last_get(cat.get('id'), k)]
    return {'status': t.get('status') or 'idle', 'windows': out, 'incognito': hide}


def _face_file(cat_id, kind):
    rs = _rs()
    return rs.FACES_DIR / f"{rs.re.sub(r'[^a-z0-9]', '', str(cat_id).lower())[:40]}.{kind}"


@router.post('/api/cats/{cat_id}/face')
async def cat_face_save(cat_id: str, p: _RSM.FacePayload):
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Agent not found.')
    rs._owner_gate(store, cat, p.session or '', p.ownerId or '', 'change its character')
    try:
        thumb_ = rs._face.clean_thumb(rs.base64.b64decode(p.thumb.split(',')[-1]))
    except ValueError:
        thumb_ = None
    char_ = rs._face.clean_character(p.character.encode())
    if not thumb_ or not char_:
        raise rs.HTTPException(400, 'That picture could not be saved. Use a clear photo with one face.')
    rs.FACES_DIR.mkdir(parents=True, exist_ok=True)
    rs._face_file(cat_id, 'jpg').write_bytes(thumb_); rs._face_file(cat_id, 'json').write_bytes(char_)
    cat['face'] = {'id': rs._face.CUSTOM, 'at': round(rs.time.time())}
    rs._save(store)
    return {'ok': True, 'face': cat['face']}


@router.get('/api/cats/{cat_id}/face/{part}')
async def cat_face_get(cat_id: str, part: str):
    rs = _rs()
    f_ = rs._face_file(cat_id, {'thumb': 'jpg', 'character': 'json'}.get(part, 'x'))
    if part not in ('thumb', 'character') or not f_.exists():
        raise rs.HTTPException(404, 'No picture.')
    return rs.Response(content=f_.read_bytes(), media_type='image/jpeg' if part == 'thumb' else 'application/json', headers={'Cache-Control': 'public, max-age=300', 'X-Content-Type-Options': 'nosniff'})


@router.get('/api/cats/{cat_id}/screen/{i}')
async def cat_screen(cat_id: str, i: int, ownerId: str = '', session: str = ''):
    """🖼 A visitor's live screen: a real JPEG of the agent's window, at most one capture per window per 4 s (cached for every viewer) — never the live
    link (a link could be turned back into control). Nothing while it is incognito, handed to its owner, or idle."""
    rs = _rs()
    cat = rs._load()['cats'].get(cat_id)
    w = rs._WORK.get(cat_id) or {}
    wins = (w.get('task') or {}).get('windows') or []
    x = wins[i] if 0 <= i < len(wins) else None
    key = (cat_id, i); now = rs.time.time(); got = rs._SHOTS.get(key)
    mine_ = bool(cat) and rs.owner_check(cat, rs._fresh_session_wallet(session), ownerId) == 'ok'
    if not cat or (cat.get('incognito') and not mine_):
        raise rs.HTTPException(404, 'No screen right now.')
    if mine_ and x and x.get('status') == 'working':   # 👑 its owner sees exactly what the agent sees
        pages_ = w.get('pages') or []; pg_ = pages_[i] if i < len(pages_) else None
        jpg_ = await pg_.shot() if pg_ and getattr(pg_, 'live', False) else None
        if jpg_:
            return rs.Response(content=jpg_, media_type='image/jpeg', headers={'Cache-Control': 'no-store'})
    if (x or {}).get('status') == 'human' or (x and not mine_ and rs._signed_host(cat, x.get('url') or '')):   # handed to its owner, or a site it is signed in to (its account could show): blank for everyone else
        return rs.Response(content=rs._vv.blank_jpg(), media_type='image/jpeg', headers={'Cache-Control': 'no-store', 'X-Private': '1'})
    if not x or x.get('status') != 'working':   # 🖼 idle / done: the last page it was on, until it works again
        if not got:
            raise rs.HTTPException(404, 'No screen right now.')
        return rs.Response(content=got[1], media_type='image/jpeg', headers={'Cache-Control': 'no-store', 'X-Last-Page': '1'})
    if not got or now - got[0] > rs.SHOT_TTL_S:
        pages = w.get('pages') or []
        pg = pages[i] if i < len(pages) else None
        jpg = await rs._vv.visitor_frame(pg, x.get('url') or '') if pg and getattr(pg, 'live', False) else None   # 👀 a stranger's frame: emails, phones and password fields covered, a private page blank
        if not jpg:
            raise rs.HTTPException(404, 'No screen right now.')
        got = rs._SHOTS[key] = (now, jpg)
        if jpg != rs._vv.blank_jpg():
            rs._last_put(cat_id, rs._slot_of(cat, x.get('model'), i), jpg)   # 🖼 the newest frame is also where its monitor will rest
    return rs.Response(content=got[1], media_type='image/jpeg', headers={'Cache-Control': 'no-store'})


@router.get('/api/cats/{cat_id}/live')
async def cat_live(cat_id: str):
    rs = _rs()
    cat = rs._load()['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Agent not found.')
    cloud = (cat.get('brainsCfg') or {}).get('cloud') or []   # 🗄 what it stored last (already public on its card) → the visitor's drawer pops
    return {**rs.public_live(rs._WORK.get(cat_id), cat), 'stored': len(cloud), 'lastStored': (lambda c: {'text': str(c.get('text') or f"{c.get('word', '')} ${c.get('sym', '')}")[:140], 'at': c.get('at')} if c else None)(cloud[-1] if cloud else None),
            'level': cat.get('level'), 'wins': cat.get('wins'), 'losses': cat.get('losses'), 'pnlSol': cat.get('totalPnlSol'), **rs._colony_vitals(cat)}


def _colony_vitals(cat):
    """🐝 the visitor's colony vitals beside its windows: colonized, honey + right calls this epoch, its newest call (public fields only)."""
    rs = _rs()
    cells = [c for c in rs._hive_cells() if c.get('cat') == cat.get('id')]
    ep = rs._hv.epoch_of(rs.time.time()); row = next(iter(rs._hv.board(cells, ep)), {})
    last = max(cells, key=lambda c: float(c.get('at') or 0)) if cells else None
    return {'colonized': rs._hive_on(cat), 'honey': int(row.get('honey') or 0), 'right': int(row.get('right') or 0), 'graded': int(row.get('graded') or 0),
            'lastCall': {k: last.get(k) for k in ('call', 'sym', 'honey', 'kind')} if last else None, 'pow': rs._pow_view(cat)}


@router.get('/api/cats/{cat_id}/judging')
async def cat_judging(cat_id: str, session: str = '', ownerId: str = ''):
    """⚖ AGX-9: the proof The Collective is judging on this agent right now, each judge's score + reason as it lands (kept 10 min after).
    Its owner only (the private desk). Judges show as The Collective except on the owner's staff agents (the same rule as every review)."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Agent not found.')
    rs._owner_gate(store, cat, session, ownerId, 'see its judging')
    j = rs._review.live_view(rs._JUDGING.get(cat_id))
    return {'judging': rs._for_users(cat, {'judges': j['judges'], **{k: v for k, v in j.items() if k != 'judges'}}) if j else None}


@router.get('/api/cats/{cat_id}/treasury')
async def cat_treasury(cat_id: str, ownerId: str = '', session: str = ''):
    """🏦 Its treasury: its coin, the creator fees waiting for its wallet (read on-chain now), the split and what each part would get."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Agent not found.')
    rs._owner_gate(store, cat, session, ownerId, 'see its treasury')
    t = cat.get('treasury') or {}; split = rs._tr.clean_split(t.get('split') or rs._tr.DEFAULT_SPLIT); creator = (cat.get('agentWallet') or {}).get('address') or ''
    fees = {'pump': 0, 'pumpSwap': 0, 'total': 0}
    if creator:
        async with rs.httpx.AsyncClient(timeout=10) as http:
            fees = await rs._tr.read(http, rs._crpc._rpc, creator)
    return {'mint': t.get('mint') or '', 'split': split, 'creator': creator, 'fees': fees, 'plan': rs._tr.plan(fees['total'], split), 'buybackMax': rs._tr.BUYBACK_MAX}


@router.get('/api/cats/{cat_id}/earn')
async def cat_earn(cat_id: str, ownerId: str = '', session: str = ''):
    """⚡ Earn Mode's plan right now: the live gap / vault / pool feeds ranked for its risk and $ (owner only; it never signs)."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Agent not found.')
    rs._owner_gate(store, cat, session, ownerId, 'see its earn plan')
    e = rs._em.clean(cat.get('earn'))
    async def get(path):
        try:
            async with rs.httpx.AsyncClient(timeout=8) as h:
                r = await h.get(f'http://127.0.0.1:5077/api/reputation/familia-pools{path}')
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}
    gaps, vault, pools = await rs.asyncio.gather(get('/gaps'), get('/sleep'), get(''))
    return {'earn': e, 'plays': rs._em.plays(gaps, vault, pools, e['risk'], e['budgetUsd']), 'gapsOpen': len([g for g in gaps.get('gaps') or [] if g.get('open')]),
            'feeds': {'gaps': bool(gaps), 'vault': bool(vault), 'pools': bool(pools)}}


@router.get('/api/cats/{cat_id}/cloud')
async def cat_cloud(cat_id: str, ownerId: str = '', session: str = ''):
    """☁ The cloud drawer: which clouds FEELESS can connect, the one connected, its space and its 5 newest files (owner only)."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Agent not found.')
    rs._owner_gate(store, cat, session, ownerId, 'see its cloud')
    ready = rs._acl.configured()
    out = {'providers': [{'key': k, 'label': v['label'], 'free': v['free'], 'ready': k in ready} for k, v in rs._acl.PROVIDERS.items()],
           'link': {k: v for k, v in (cat.get('cloudLink') or {}).items() if k in ('provider', 'label', 'at')} or None}
    if out['link']:
        try:
            async with rs.httpx.AsyncClient() as http:
                prov, tok = await rs._cloud_token(http, cat)
                out.update(await rs._acl.overview(http, prov, tok, cat))
        except Exception as e:
            out['error'] = str(getattr(e, 'detail', e))[:120]
    return out


@router.post('/api/cats/{cat_id}/files/{file_id}/keep')
async def cat_file_keep(cat_id: str, file_id: str, p: _RSM.FilePayload):
    """☁ An attachment → its owner's own cloud (FEELESS keeps nothing past 24 h)."""
    rs = _rs()
    store = rs._load()
    cat = rs._owned(store, cat_id, p.ownerId, p.session)
    f = rs._af.find(cat, file_id); raw = rs._af.read(rs.DATA_DIR, cat, file_id)
    if not f or not raw:
        raise rs.HTTPException(404, 'No such file.')
    async with rs.httpx.AsyncClient() as http:
        prov, tok = await rs._cloud_token(http, cat)
        try:
            return {'kept': await rs._acl.upload(http, prov, tok, cat, f['name'], raw, f['mime'])}
        except Exception:
            raise rs.HTTPException(502, 'Its cloud did not take the file — try again.')


@router.post('/api/cats/{cat_id}/files/{file_id}/ipfs')
async def cat_file_ipfs(cat_id: str, file_id: str, p: _RSM.FilePayload):
    """⛓ Keep an attachment on IPFS for 30 days, paid in SOL by ITS OWN wallet (agent_ipfs.py). pay=false → the real cost from a
    simulation (nothing signed); pay=true → that same quote, simulated again, signed by Circle, confirmed, the link kept on the file."""
    rs = _rs()
    store = rs._load()
    cat = rs._owned(store, cat_id, p.ownerId, p.session)
    f = rs._af.find(cat, file_id); raw = rs._af.read(rs.DATA_DIR, cat, file_id)
    if not f or not raw:
        raise rs.HTTPException(404, 'No such file.')
    w_ = cat.get('agentWallet') or {}; addr_ = w_.get('address')
    if not addr_ or not rs._pays_itself(cat):
        raise rs.HTTPException(400, 'Only its own Circle wallet can pay for IPFS — make its wallet first.')
    k_ = f'{cat_id}:{file_id}'; now = rs.time.time()
    async with rs.httpx.AsyncClient(timeout=60) as http:
        rpc_ = lambda m, ps: rs._crpc._rpc(http, m, ps)   # noqa: E731
        try:
            if not p.pay:
                d_ = await rs._ipfs.deposit(http, raw, f['name'], f.get('mime'), addr_)
                i0_ = rs._ipfs.check(d_, addr_)
                lam_, _tx, bal_ = await rs._ipfs.cost(rpc_, addr_, i0_)
                rs._IPFS_Q[k_] = {'ins': i0_, 'cid': d_['cid'], 'lamports': lam_, 'at': now}
                return {'quote': {'cid': d_['cid'], 'sol': lam_ / 1e9, 'days': rs._ipfs.DAYS, 'why': rs._ipfs.afford(lam_, bal_, rs._at.GAS_SOL)}}
            q_ = rs._IPFS_Q.get(k_)
            if not q_ or now - q_['at'] > rs._ipfs.QUOTE_TTL:
                raise rs.HTTPException(409, 'Get the price again first (a quote lasts 10 minutes).')
            lam_, tx_, bal_ = await rs._ipfs.cost(rpc_, addr_, q_['ins'])
            if lam_ > q_['lamports'] * 1.1 + 1000:
                raise rs.HTTPException(409, f'The price moved to {lam_ / 1e9:.6f} SOL — get the price again.')
            why_ = rs._ipfs.afford(lam_, bal_, rs._at.GAS_SOL)
            if why_:
                raise rs.HTTPException(400, why_)
            rs._IPFS_Q.pop(k_, None)
            rec_ = {'key': f"feeless-{cat_id}-ipfs-{q_['cid'][-16:]}", 'tx': tx_}
            await rs._at._circle_post(http, cat, rec_)
            sig_ = rec_.get('sig')
            for _ in range(20):
                await rs.asyncio.sleep(3)
                st_ = ((await rpc_('getSignatureStatuses', [[sig_]])) or {}).get('value', [None])[0]
                if st_ and st_.get('err'):
                    raise rs.HTTPException(400, f'The chain refused it — nothing kept ({str(st_["err"])[:60]}).')
                if st_ and st_.get('confirmationStatus') in ('confirmed', 'finalized'):
                    break
            url_, exp_ = await rs._ipfs.confirm(http, q_['cid'], sig_, addr_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
    row_ = {'file': file_id, 'name': f['name'], 'cid': q_['cid'], 'url': url_, 'sig': sig_, 'sol': round(lam_ / 1e9, 6), 'days': rs._ipfs.DAYS, 'at': round(now), 'expires': exp_}
    st = rs._load(); c_ = st['cats'].get(cat_id)
    if c_:
        c_['ipfs'] = ((c_.get('ipfs') or []) + [row_])[-50:]; rs.keep_owned(c_); rs._save(st)
    return {'stored': row_}


@router.get('/api/cats/{cat_id}/files')
async def cat_files(cat_id: str, ownerId: str = '', session: str = ''):
    """☁ Its storage: files, links, used / quota (owner only). Files unused for 7 days are cleaned first."""
    rs = _rs()
    store = rs._load()
    cat = rs._owned(store, cat_id, ownerId, session)
    if rs._af.clean(rs.DATA_DIR, {'cats': {cat_id: cat}}):
        rs.keep_owned(cat); rs._save(store)
    return rs._af.public(cat)


@router.post('/api/cats/{cat_id}/files')
async def cat_file_add(cat_id: str, p: _RSM.FilePayload):
    """☁ The owner drops an image in its chat (+): stored in the agent's own storage (images / GIFs, 1 GB, 7-day clean)."""
    rs = _rs()
    store = rs._load()
    cat = rs._owned(store, cat_id, p.ownerId, p.session)
    rs._af.clean(rs.DATA_DIR, {'cats': {cat_id: cat}})
    try:
        row = rs._af.save(rs.DATA_DIR, cat, p.dataUrl, p.name)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    rs.keep_owned(cat); rs._save(store)
    return {'file': next(f for f in rs._af.public(cat)['files'] if f['id'] == row['id']), **{k: v for k, v in rs._af.public(cat).items() if k != 'files'}}


@router.post('/api/cats/{cat_id}/files/{file_id}/delete')
async def cat_file_delete(cat_id: str, file_id: str, p: _RSM.FilePayload):
    rs = _rs()
    store = rs._load()
    cat = rs._owned(store, cat_id, p.ownerId, p.session)
    if not rs._af.delete(rs.DATA_DIR, cat, file_id):
        raise rs.HTTPException(404, 'No such file.')
    rs.keep_owned(cat); rs._save(store)
    return rs._af.public(cat)


@router.get('/api/cats/{cat_id}/files/{name}')
async def cat_file_get(cat_id: str, name: str):
    """One stored file by its unguessable id (how the chat chip and the page show it)."""
    rs = _rs()
    cat = (rs._load().get('cats') or {}).get(cat_id) or {}
    fid = str(name).split('.')[0]
    raw_ = rs._af.read(rs.DATA_DIR, cat, fid) if cat else None
    if not raw_:
        raise rs.HTTPException(404, 'No such file.')
    mime_ = rs._af.find(cat, fid)['mime']
    locked_ = {'Content-Security-Policy': 'sandbox', 'Content-Disposition': 'attachment'} if mime_ == 'text/html' else {}   # 🖥 a page an agent built never runs on this origin
    return rs.Response(content=raw_, media_type=mime_, headers={'Cache-Control': 'private, max-age=3600', 'X-Content-Type-Options': 'nosniff', **locked_})


def _pev_record():
    """COL-3's history for the envelopes: per-proof counts in one read, and the whole chain verified once per new head."""
    rs = _rs()
    path = rs.DATA_DIR / rs._pev.DB_NAME
    try:
        h_ = rs._pev.head(path) if path.exists() else None
        if h_ != rs._PEV_OK['head'] or rs._PEV_OK['v'] is None:
            rs._PEV_OK.update(head=h_, v=rs._pev.verify(path) if h_ else {'ok': True, 'count': 0})
        return {'rows': rs._pev.counts(path), 'intact': bool(rs._PEV_OK['v'] and rs._PEV_OK['v']['ok']), 'count': (rs._PEV_OK['v'] or {}).get('count', 0), 'why': (rs._PEV_OK['v'] or {}).get('why')}
    except Exception as e:   # noqa: BLE001: the envelopes still show, saying the record could not be read
        return {'rows': {}, 'intact': None, 'count': 0, 'why': f'{type(e).__name__}: {e}'}


def _calls_of(cat_id, limit=20000):
    rs = _rs()
    p_ = rs.DATA_DIR / 'mind_calls.jsonl'
    if not p_.exists():
        return []
    out = []
    with p_.open() as fh:
        for line in fh.readlines()[-limit:]:
            if f'"cat":"{cat_id}"' in line:
                try:
                    out.append(rs.json.loads(line))
                except ValueError:
                    pass
    return out


def _route_words(cat):
    """The order a model call takes for this agent, in plain words (AGT-14)."""
    rs = _rs()
    own_ = bool(rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)); staff_ = bool(cat.get('ownerStaff') or cat.get('isLeader')); wallet_ = rs._pays_itself(cat)
    if own_:
        return ['your own OpenRouter key (you pay OpenRouter)'] + (['SingIt, paid from its own wallet'] if wallet_ else []) + ['no free stand-in: it says so instead']
    if staff_:
        return ["FEELESS's OpenRouter"] + (['SingIt, paid from its own wallet'] if wallet_ else []) + ['the free stand-ins (SingIt free, Groq)']
    return (['SingIt, paid from its own wallet'] if wallet_ else []) + (["FEELESS's OpenRouter"] if rs._brains_live() else []) + ['the free stand-ins (SingIt free, Groq)']


@router.get('/api/cats/{cat_id}/record')
async def cat_public_record(cat_id: str):
    """👀 AGT-10: an agent's public vitals for visitors: per kind, proofs filed, PROVED / NOT PROVED by the 24-hour stamp, and the wins settled from
    outside (chain, scoreboard, true prices). Counts only: no folder, no model, no wallet, no owner. → {kinds: [...], total}"""
    rs = _rs()
    cat = rs._load()['cats'].get(cat_id)
    if not cat or cat.get('revoked'):
        raise rs.HTTPException(404, 'Cat not found.')
    rows = rs._mission.all_of(cat, rs.time.time()); out = {}
    for e in rows:
        r = out.setdefault(e['kind'], {'kind': e['kind'], 'code': e['code'], 'filed': 0, 'proved': 0, 'not': 0, 'verified': 0, 'verifiedWon': 0})
        r['filed'] += 1; st = (e.get('outcome') or {}).get('state')
        if st in ('proved', 'not'):
            r[st] += 1
            if (e.get('outcome') or {}).get('strength') in ('chain', 'outside'):
                r['verified'] += 1; r['verifiedWon'] += 1 if st == 'proved' else 0
    kinds = sorted(out.values(), key=lambda r: -r['filed'])
    tot = {k: sum(r[k] for r in kinds) for k in ('filed', 'proved', 'not', 'verified', 'verifiedWon')}
    return {'kinds': kinds, 'total': tot}


@router.get('/api/cats/{cat_id}/paths')
async def cat_paths(cat_id: str, ownerId: str = '', session: str = ''):
    """🧭 AGT-14: how each kind of proof runs for this agent, in plain steps: what it reads first and in what order, which two minds, the route a
    call takes and its fallbacks, the checks before it may settle, and its method kits. Read from the live config, never written up by hand. Owner only."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Cat not found.')
    rs._owner_gate(store, cat, session, ownerId)
    b_ = cat.get('brainsCfg') or {}; route_ = rs._route_words(cat); out = []; calls_ = await rs.asyncio.to_thread(_calls_of, cat_id)   # 🧠 Slice 1: the last proof of each kind, from the call log
    checks = {'pow': ['compare before settling: recorded, never blocks a real buy', 'the 24-hour stamp', 'real trades read back from the chain'],
              'pop': ['compare before settling: a thin call is not traded', 'the 24-hour stamp, priced at true prices'],
              'pob': ['compare before settling: a thin pick is not bid', 'the final score or the market settles it'],
              'poc': ['the owner marks it', 'the 24-hour stamp'], 'pos': ['a game must pass a headless playtest before it is filed', 'the owner marks the page', 'the 24-hour stamp'],
              'poe': ['a hash of the books: it proves nothing changed']}
    for k in rs._lc.PROOF_KINDS:
        try:
            order_ = rs._feat._sources.read_order(k, await rs.asyncio.to_thread(rs._stash.trust_rows, rs.STASH_DIR, rs._feat._sources.STASH_CAT.get(k))) if k in rs._feat._sources.STASH_CAT else []
        except Exception:   # noqa: BLE001: the rest of the path still shows
            order_ = []
        out.append({'kind': k, 'reads': [{'host': r.get('host'), 'name': r.get('name') or r.get('host'), 'why': r.get('why') or r.get('use') or ''} for r in order_[:6]],
                    'freshMin': round(rs.READ_FRESH_S.get(k, 600) / 60), 'minds': rs._lc.minds_for(b_, k), 'ownMinds': bool((b_.get('byKind') or {}).get(k)), 'route': route_,
                    'checks': checks.get(k, []), 'kits': [kid for kid, kt in rs._mkits.all_kits(rs._mkit_extra()).items() if k in kt['kinds'] and (rs._MKIT_STATE.get(kid) or {}).get('state') != 'quarantined'],
                    'prompt': bool((b_.get('promptBy') or {}).get(k)), 'persona': ((b_.get('personaBy') or {}).get(k) or {}).get('style'), 'voiceOn': rs._kind_voice_on(b_, k),
                    'efforts': {m: (b_.get('efforts') or {}).get(m) for m in rs._lc.minds_for(b_, k) if (b_.get('efforts') or {}).get(m)},
                    'last': rs._prec.last_ran(k, [f for f in cat.get(rs._prec.KEYS.get(k)) or [] if isinstance(f, dict)], calls_, rs._lc.minds_for(b_, k))})
    return {'paths': out}


@router.get('/api/cats/{cat_id}/parts')
async def cat_parts(cat_id: str, ownerId: str = '', session: str = ''):
    """🧩 COL-26: the Collective's proven parts, each with its family tree (which proofs reused it), licenses and whether it went stale. Owner only."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Cat not found.')
    rs._owner_gate(store, cat, session, ownerId)
    rows = rs._parts.family(rs._parts_path())
    return {'parts': [{**r, 'mine': r['cat'] == cat_id} for r in rows], 'staleDays': rs._parts.STALE_S // 86400}


@router.get('/api/cats/{cat_id}/missions')
async def cat_missions(cat_id: str, ownerId: str = '', session: str = ''):
    """🧾 COL-4: every proof of this agent in one shape, its three evaluations kept apart (quality = the rubric, outcome = the stamp and who
    settled it, improvement = unverified until a matched baseline), plus who really answered (COL-2) and its tamper-proof history (COL-3). Owner only."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Cat not found.')
    rs._owner_gate(store, cat, session, ownerId)
    rec = rs._pev_record()
    calls_ = rs._calls_of(cat_id); rows = rs._mission.all_of(cat, rs.time.time(), lambda k, f: rs._proof_view(cat, k, f), calls_, rec)
    kits_ = rs._mkit_measure(cat, rows)
    return rs._for_users(cat, {'missions': rows, 'vitals': rs._mission.vitals(rows, calls_), 'contribution': rs._mission.contribution(cat, rows, calls_), 'methods': list(kits_.values()), 'chain': {k: rec[k] for k in ('intact', 'count', 'why')}, 'at': round(rs.time.time())})


@router.get('/api/cats/{cat_id}/agent-wallet')
async def cat_agent_wallet(cat_id: str, ownerId: str = '', session: str = ''):
    """👛 The cat's own wallet: address, mode and its live SOL / USDC — its owner's only (a visitor never learns what an agent holds)."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Cat not found.')
    rs._owner_gate(store, cat, session, ownerId, 'see its wallet')
    w = cat.get('agentWallet')
    if not w:
        return {'wallet': None, 'kind': (cat.get('brainsCfg') or {}).get('kind')}
    try:
        async with rs.httpx.AsyncClient(timeout=15) as http_b:
            if w.get('provider', 'crossmint') == 'crossmint':
                bal = await rs._aw.balances(http_b, rs.os.environ.get('CROSSMINT_API_KEY', '').strip(), w['address'])
            else:   # 👁 watch-only: its balance from the chain (the trading service's holdings read)
                h_ = await http_b.get(f"{rs._at.TRADE}/holdings/{w['address']}", timeout=15)
                tk_ = {t_.get('mint'): float(t_.get('amount') or 0) for t_ in ((h_.json() or {}).get('tokens') or [])} if h_.status_code == 200 else None
                bal = {'sol': tk_.get(rs._at.SOL, 0.0), 'usdc': tk_.get('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 0.0)} if tk_ is not None else {'error': 'no chain read'}
    except (ValueError, rs.httpx.HTTPError) as e:
        bal = {'error': str(e)}
    return {'wallet': {k: w.get(k) for k in ('address', 'mode', 'provider', 'at', 'assigned')}, 'balance': bal, 'kind': (cat.get('brainsCfg') or {}).get('kind')}


@router.get('/api/cats/{cat_id}/profile')
async def cat_profile(cat_id: str):
    rs = _rs()
    store = rs._load()
    rs._migrate(store)
    cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Cat not found')
    trades = [e for e in store.get('events', []) if e.get('catId') == cat_id and e.get('type') in ('BUY', 'SELL')]
    learn = cat.get('learn') or {}
    closed = cat.get('wins', 0) + cat.get('losses', 0)
    pnls = [e.get('pnlSol') for e in trades if e.get('pnlSol') is not None]
    return rs._pub({
        'cat': {k: cat.get(k) for k in ('id', 'name', 'title', 'avatar', 'strategyLabel', 'level', 'xp', 'balanceSol', 'startingBalanceSol', 'realizedPnlSol',
                                        'volumeSol', 'wins', 'losses', 'winRate', 'positions', 'pnlHistory', 'status', 'lastTick', 'look', 'skin')},   # 🎨 her look rides along: every viewer sees the creator's style
        'stats': {'trades': closed, 'best': max(pnls) if pnls else None, 'worst': min(pnls) if pnls else None,
                  'roiPct': round((cat.get('balanceSol', 0) + sum(p.get('costSol', 0) for p in cat.get('positions', [])) - cat.get('startingBalanceSol', 0)) / max(cat.get('startingBalanceSol', 1), 1e-9) * 100, 2)},
        # Live discipline: 9 lives, size mode and why — computed now, the same rule the trading loop enforces.
        'discipline': rs.feecat_brain.discipline(cat.get('exits', []), rs.time.time()),
        'strength': cat.get('strength') or {'level': 'steady', 'mult': 1.0, 'label': rs.feecat_brain.STRENGTH['steady']['label'], 'why': 'warming up — needs trades on record'},
        'trades': trades[:80],
        'exits': list(reversed(cat.get('exits', [])))[:30],
        'learning': {'params': {**{k: rs.RULES[k] for k in rs.LEARN_BOUNDS}, **{k: v for k, v in (learn.get('params') or {}).items() if k in rs.LEARN_BOUNDS}}, 'defaults': {k: rs.RULES[k] for k in rs.LEARN_BOUNDS},
                     'entry': {**{k: rs.RULES[k] for k in rs.ENTRY_BOUNDS}, **(learn.get('entry') or {})}, 'mode': learn.get('mode', 'warming'), 'tunedAt': learn.get('tunedAt'), 'study': learn.get('study'),
                     'missed': learn.get('missed', 0), 'good': learn.get('good', 0), 'log': learn.get('log', []),
                     'playbook': rs.feecat_brain.playbook(rs.feecat_brain.edge_table(cat.get('setupMemory') or [])), 'memory': len(cat.get('setupMemory') or []),
                     'vetoes': (store.get('scan') or {}).get('brainRejects', [])[-5:] if cat.get('isLeader') else []},
        'rules': {k: rs.RULES[k] for k in ('hardStop', 'add1At', 'add2At', 'takeProfit1', 'takeProfit2', 'runnerTrail', 'maxHoldHours', 'maxTop10Pct', 'maxInsiderPct', 'maxSnipers', 'maxBundled', 'maxM5Chase')},
    })


@router.get('/api/cats/{cat_id}')
async def get_cat(cat_id: str, request: Request = None, ownerId: str = '', session: str = ''):
    """One cat, public view. `mine` = this signed-in wallet owns it (signed out ⇒ never mine); the owner id / wallet are never returned."""
    rs = _rs()
    store = rs._load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Cat not found.')
    if rs._real.is_real(cat) and rs._real.expire(cat, rs.time.time()):
        rs._save(store)
    mine = rs.owner_check(cat, rs._fresh_session_wallet(session), ownerId) in ('ok', 'claim')
    inside = request is not None and bool(request.headers.get('x-feeless-internal')) and rs._internal_ok(request)   # 🔒 FEELESS's own services (funding, withdraw) read the full record
    full_ = {'cat': {k: v for k, v in cat.items() if k not in ('artifacts', 'refusals')} if mine or inside or cat.get('isLeader') else rs.public_cat(cat)}
    out = rs.json.loads(rs.json.dumps(rs._no_keys(full_), ensure_ascii=False)) if (mine or inside) else rs._pub(full_)   # 👤 AGT-2: its owner sees its real minds (OSSY, G4); visitors still read "FeeCat AI"
    if cat.get('isLeader') and not (mine or inside):   # 🔒 the leader's desk is public, its private drawers are not (found in the 2026-11-04 audit)
        for k_ in rs.LEADER_PRIVATE:
            out['cat'].pop(k_, None)
    out['cat']['mine'] = mine
    out['cat']['live'] = rs._al.public_row(rs._LIVE.get(cat_id))
    out['cat']['printPublic'] = rs._print.public(rs._print.build(cat, rs.time.time()))   # 🧬 a level: never what is in it
    if mine:   # 🧠 the record each mind has by topic is its owner's
        out['cat']['mindBoard'] = rs._pl.mind_board(cat)
        out['cat']['orCredit'] = await rs._or_credit(cat)   # 💳 owner 2026-11-11: the desk said $5.55 (its model credit) while it really thinks on its OpenRouter balance
        out['cat']['payRoute'] = rs._route_words(cat)   # 💳 AGT-1: who really pays for its thinking, in call order (the desk names the first)
        out['cat']['liveKeys'] = rs._al.owner_view(cat.get('liveKeys'))   # 🔴 whether each channel is set, never the key
        out['cat']['nameLeftS'] = rs._nl.left_s(cat.get('nameLock'))
        out['cat']['recoveryView'] = rs._rkit.view(cat.get('recoveryKit'))
        out['cat']['print'] = rs._print.build(cat, rs.time.time())
        out['cat']['recoveryHold'] = rs._rkit.on_hold(cat, rs.time.time())
    return out

