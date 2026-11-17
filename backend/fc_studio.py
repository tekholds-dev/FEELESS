"""🧹 Prompt studio, ads, workspaces — moved whole out of feecat_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches feecat_service still
reaches it, and every function here is still reachable on feecat_service under its own name. Constants, classes and state live in the service."""
import feecat_service as _RSM  # noqa: E402,F401  (body models; this module is imported at the END of the service)
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401

router = APIRouter()


def _rs():
    import feecat_service
    return feecat_service


def studio_view(cat, now=None):
    rs = _rs()
    import prompt_studio as _ps
    now = now or rs.time.time()
    b, st = cat.get('brainsCfg') or {}, cat.get('studio') or {}
    tr = rs._studio_trades(cat)
    calls = [{'action': d.get('word') or 'NO ANSWER'} for d in (b.get('decisions') or []) if isinstance(d, dict) and d.get('word') != 'RULES']
    s = _ps.stats(tr, calls)
    fx = _ps.diagnose(s)
    a = {k: st[k] for k in ('set', 'text', 'at', 'by', 'edited') if k in st} if st.get('text') else None
    lad = _ps.ladder(tr, st.get('history'), 'fee', now, a)
    sets = _ps.sets('fee', s, fx, _ps.best_rung(lad))
    tuned = next((x['text'] for x in sets if x['set'] == 'tuned'), '')
    lay = lambda k, label, text, note=None: {'k': k, 'label': label, 'chars': len(text or ''), 'tok': (len(text or '') + 3) // 4, 'text': (text or '')[:4000], **({'note': note} if note else {})}
    return {'key': 'fee', 'name': 'FEE', 'state': 'ONLINE' if cat.get('status') == 'running' else 'PAUSED', 'model': ' + '.join(str(m).split('/')[-1] for m in b.get('brains') or []) or 'rule engine',
            'ctx': None, 'record': s, 'fixes': fx, 'sets': sets, 'ladder': lad, 'auto': None, 'approve': True,
            'layers': [lay('job', 'Brain prompt', rs._lc.SYS), lay('identity', "Owner's brief", b.get('prompt') or '', None if b.get('prompt') else 'none'),
                       lay('studio', 'Applied mindset', a['text'] if a else '', None if a else 'none applied')],
            'active': {**a, 'since': _ps.since(tr, a['at']), 'seen': None} if a else None,
            'general': {'text': st.get('general') or _ps.GENERAL, 'edited': bool(st.get('general')), 'max': _ps.MAX_CHARS['fee'], 'record': _ps.general_record(cat), 'line': _ps.general_line(_ps.general_record(cat))},
            'fresh': bool(a and a.get('set') == 'tuned' and not a.get('edited') and tuned and tuned != a['text'])}   # 🆕 a stronger AUTO-TUNED is waiting for your Apply


def studio_set(cat, body, by, now=None):
    """{set, text?} applies a version (text = the owner's edit) · {revert: true} back to her plain brief. Every change goes on the ladder's history."""
    rs = _rs()
    import prompt_studio as _ps
    now = now or rs.time.time()
    st = dict(cat.get('studio') or {})
    if 'general' in body:   # 🧠 the general mind only: her trading mindset stays exactly as it is
        txt = ' '.join(str(body.get('general') or '').split())[:_ps.MAX_CHARS['fee']]
        cat['studio'] = {**st, 'general': txt if txt and txt != _ps.GENERAL else None}
        return rs.studio_view(cat, now)
    keep_general = st.get('general')
    if body.get('revert'):
        st = {'history': _ps.hist_add(st.get('history'), 'fee', None, now, by)}
    else:
        set_ = body.get('set')
        if set_ not in _ps.SETS:
            raise rs.HTTPException(400, 'unknown prompt set')
        gen = next((x['text'] for x in rs.studio_view(cat, now)['sets'] if x['set'] == set_), '')
        txt = ' '.join(str(body.get('text') or '').split())[:_ps.MAX_CHARS['fee']] or gen
        if not txt:
            raise rs.HTTPException(400, 'empty prompt')
        st = {'set': set_, 'text': txt, 'at': now, 'by': str(by or '')[:44], 'edited': txt != gen, 'history': _ps.hist_add(st.get('history'), 'fee', set_, now, by)}
    cat['studio'] = {**st, 'general': keep_general} if keep_general else st
    return rs.studio_view(cat, now)


def _signed_host(cat, url):
    """True when this address is on a site the owner signed in to. Its window may show their account, so a visitor never sees it."""
    rs = _rs()
    try:
        host = str(rs._cv.site_of(url or '')).lower()
    except Exception:   # noqa: BLE001 — an address it can't read is treated as private
        return True
    return any(host == s or host.endswith('.' + s) or s.endswith('.' + host) for s in (cat.get('siteSessions') or {}))


def _shot_private(cat, folder, name):
    """🔒 A PoB's snapshots (their names do not say which site they came from, so one could be a signed-in page), and any page from a site the owner signed in to, are its owner's alone. So is everything while it is incognito."""
    return bool(cat.get('incognito')) or str(folder).startswith('pob') or any(s in str(name) for s in (cat.get('siteSessions') or {}))


@router.get('/api/cats/{cat_id}/showad/{kind}')
async def show_ad_video(cat_id: str, kind: str, ownerId: str = '', session: str = '', dl: int = 0, ws: str = ''):
    """🎬 One Showcase ad video (or, with ws, one kept attempt's): its owner only (owner 2026-11-11: only the owner can download them)."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id); w_ = rs.re.sub(r'[^a-z0-9]', '', ws)
    f_ = rs.SHOW_ADS_DIR / rs.re.sub(r'[^a-z0-9]', '', cat_id) / f"{rs.re.sub(r'[^a-z]', '', kind)}{'-' + w_ if w_ else ''}.webm"
    if not cat or kind not in rs._ads.KINDS or not f_.exists():
        raise rs.HTTPException(404, 'No ad yet.')
    rs._owner_gate(store, cat, session, ownerId, 'see its ads')
    head_ = {'Cache-Control': 'private, max-age=600'}
    if dl:
        head_['Content-Disposition'] = f'attachment; filename="feeless-{rs._ads.NAME[kind].lower()}-ad.webm"'
    return rs.Response(content=f_.read_bytes(), media_type='video/webm', headers=head_)


@router.get('/api/cats/{cat_id}/asset/{aid}')
async def agent_asset(cat_id: str, aid: str, ownerId: str = '', session: str = '', dl: int = 0):
    """🗂 One file from an agent's My files: its owner only."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id); a_ = rs.re.sub(r'[^a-f0-9]', '', aid)[:12]
    row_ = next((r for r in ((rs._play_load(cat_id, 'assets') or {}).get('rows') or []) if r.get('id') == a_), None) if cat else None
    f_ = rs.DATA_DIR / 'agent_assets' / rs.re.sub(r'[^a-z0-9]', '', str(cat_id).lower())[:40] / a_
    if not row_ or not f_.exists():
        raise rs.HTTPException(404, 'No such file.')
    rs._owner_gate(store, cat, session, ownerId, 'open its files')
    head_ = {'Cache-Control': 'private, max-age=3600'}
    if dl:
        head_['Content-Disposition'] = f'attachment; filename="{row_["name"]}"'
    return rs.Response(content=rs._ck.unseal_bytes(f_.read_bytes(), cat_id), media_type=rs._aas.MIME.get(row_['ext'], 'application/octet-stream'), headers=head_)


@router.get('/api/cats/{cat_id}/powshot/{folder}/{name}')
async def pow_snapshot(cat_id: str, folder: str, name: str, ownerId: str = '', session: str = ''):
    """📸 One research snapshot of a proof folder. Public research pages stay public; anything private asks for its owner's signed session."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    f_ = rs.POWSHOTS_DIR / rs.re.sub(r'[^a-z0-9]', '', folder) / rs.re.sub(r'[^a-z0-9._]', '', name)
    if not cat or not (name.endswith('.jpg') or name == 'report.md') or not f_.exists():
        raise rs.HTTPException(404, 'No snapshot.')
    if rs._shot_private(cat, folder, name):
        rs._owner_gate(store, cat, session, ownerId, 'see this snapshot')
    return rs.Response(content=rs._ck.unseal_bytes(f_.read_bytes(), cat_id), media_type='image/jpeg' if name.endswith('.jpg') else 'text/markdown; charset=utf-8', headers={'Cache-Control': 'private, max-age=3600'})


@router.get('/api/cats/{cat_id}/sitesnap/{name}')
async def site_snapshot(cat_id: str, name: str, ownerId: str = '', session: str = ''):
    """🔎 A scanned site's snapshot. It may show the owner's signed-in page, so only they get it."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'No snapshot.')
    rs._owner_gate(store, cat, session, ownerId, 'see its site snapshots')
    f_ = rs.POWSHOTS_DIR / ('site' + rs.re.sub(r'[^a-z0-9]', '', cat_id.lower())[:40]) / rs.re.sub(r'[^a-z0-9.]', '', name)
    if not name.endswith('.jpg') or not f_.exists():
        raise rs.HTTPException(404, 'No snapshot.')
    return rs.Response(content=f_.read_bytes(), media_type='image/jpeg', headers={'Cache-Control': 'no-store'})


@router.get('/api/cats/pow/archive')
async def pow_archive(q: str = '', limit: int = 20):
    """Public coin facts only; private agent plans, step fingerprints and page excerpts stay sealed."""
    rs = _rs()
    private = {c['id'] for c in rs._load()['cats'].values() if c.get('incognito')}
    available = [r for r in rs._pow_archive_rows() if r.get('cat') not in private]
    rows = rs._pow.archive_find(available, q, max(1, min(100, int(limit))))
    public = [rs._pow.archive_public(r) for r in rows]
    return rs._pub({'rows': public, 'brief': rs._pow.archive_brief(public) if q else '', 'total': len(available)})


async def _pot_balance(now):
    """🏺 The colony pot's address, its balance read on-chain at most once a minute (kept in _FLOW_POT). Read only."""
    rs = _rs()
    try:
        pot_addr = ((rs.json.loads((rs.DATA_DIR / 'colony.json').read_text()) or {}).get('wallet') or {}).get('address')
    except (OSError, ValueError):
        pot_addr = None
    if pot_addr and now - rs._FLOW_POT['at'] > 60:
        try:
            async with rs.httpx.AsyncClient(timeout=10) as http:
                rs._FLOW_POT.update(at=now, sol=int(((await rs._crpc._rpc(http, 'getBalance', [pot_addr, {'commitment': 'confirmed'}])) or {}).get('value') or 0) / 1e9)
        except Exception:   # noqa: BLE001
            rs._FLOW_POT['at'] = now
    return pot_addr


async def _colony_reconcile(cat, shares, now):
    """🧾 Read-only check of the ledger against the chain: every transfer this agent's ledger claims has a confirmed signature, and what the pot holds next to what the ledger says went in and out. Moves nothing."""
    rs = _rs()
    sigs = sorted({x['sig'] for x in shares if x.get('cat') == cat.get('id') and x.get('sent') and x.get('sig')})
    todo = [x for x in sigs if x not in rs._SIG_CONFIRMED][:100]; read = True
    if todo:
        try:
            async with rs.httpx.AsyncClient(timeout=10) as http:
                got = ((await rs._crpc._rpc(http, 'getSignatureStatuses', [todo, {'searchTransactionHistory': True}])) or {}).get('value') or []
            rs._SIG_CONFIRMED.update(s for s, st in zip(todo, got) if st and not st.get('err') and st.get('confirmationStatus') in ('confirmed', 'finalized'))
        except Exception:   # noqa: BLE001 — no read: it says so rather than passing or failing the ledger
            read = False
    pot_addr = await rs._pot_balance(now)
    return {'transfers': len(sigs), 'confirmed': sum(1 for x in sigs if x in rs._SIG_CONFIRMED), 'read': read, 'potOpen': bool(pot_addr), 'potSol': rs._FLOW_POT['sol'] if pot_addr else None,
            'ledgerInSol': round(sum(rs._num(x.get('sol')) for x in shares if x.get('gift') or x.get('state') == 'transferred'), 9),
            'ledgerOutSol': round(sum(rs._num(x.get('sol')) for x in shares if x.get('sent') and not x.get('gift') and x.get('state') != 'transferred'), 9)}


def _flow_tree(cats, shares, board):
    rs = _rs()
    t = rs._colony.tree(cats, shares, board)
    for a in t['agents']:   # ⚡ working right now: this is what zaps the crystal
        c = next((x for x in cats if x.get('id') == a['id']), {})
        a['print'] = rs._print.public(rs._print.build(c, rs.time.time()))['level']
        a['active'] = bool((c.get('powRun') or {}).get('folder')) or any(w.get('status') == 'working' for w in ((rs._WORK.get(a['id']) or {}).get('task') or {}).get('windows') or [])
    return t


def _active_proofs(cat, cid):
    """→ the proof kinds this agent is running now, in a fixed order."""
    rs = _rs()
    out = []
    if (cat.get('powRun') or {}).get('folder') or cid in rs._POW_WANT:
        out.append('PoW')
    if cat.get('popRun') or cat.get('popCard') or cat.get('popRead') or cid in rs._POP_WANT:
        out.append('PoP')
    if cat.get('pobRun') or cat.get('pobRead') or cat.get('pobAsk') or cid in rs._POB_WANT:
        out.append('PoB')
    if cid in rs._POC_BUSY:
        out.append('PoC')
    return out


def _proof_room(cat, cid, kind):
    """→ None when a new `kind` proof may start, else what to tell the owner."""
    rs = _rs()
    on = rs._active_proofs(cat, cid)
    if kind in on or len(on) < rs.MAX_ACTIVE_PROOFS:
        return None
    return f"🗂 {cat.get('name') or 'This agent'} is already running {len(on)} proofs ({', '.join(on)}), the most at once. Stop one or let it finish first."


def _ws_file(cat_id, ws_id):
    rs = _rs()
    return rs.WS_DIR / rs.re.sub(r'[^a-z0-9]', '', str(cat_id).lower())[:40] / (rs.re.sub(r'[^a-z0-9]', '', str(ws_id).lower())[:24] + '.seal')


def _ws_save(cat_id, doc):
    rs = _rs()
    f_ = rs._ws_file(cat_id, doc.get('id')); f_.parent.mkdir(parents=True, exist_ok=True)
    f_.write_bytes(rs._ck.seal_bytes(rs.json.dumps(doc).encode(), cat_id))   # 🔒 its owner's work, sealed with this agent's key
    st_ = rs._pev.ws_state(cat_id, doc)
    if st_:
        rs._pev_watch([st_])


def _ws_load(cat_id, ws_id):
    rs = _rs()
    f_ = rs._ws_file(cat_id, ws_id)
    try:
        return rs.json.loads(rs._ck.unseal_bytes(f_.read_bytes(), cat_id))
    except (OSError, ValueError):
        return None


def _ws_start(cat_id, ws_id, *args):
    rs = _rs()
    t_ = rs.asyncio.create_task(rs._ws_run(cat_id, ws_id, *args)); rs._WS_LIVE[(cat_id, ws_id)] = t_
    return t_


def _ads_cost(cat_id):
    rs = _rs()
    return lambda ws: (rs._ws_load(cat_id, ws) or {}).get('cost') or 0 if ws else 0


def _ads_set(cat_id, k, **row):
    rs = _rs()
    store = rs._load(); c_ = store['cats'].get(cat_id)
    if c_ is None:
        return None
    c_.setdefault('showAds', {}).setdefault(k, {}).update(row); rs._save(store)
    return c_


def _ads_try(cat_id, k, ws, faults, outcome):
    """🎬 One ad attempt, kept for good (owner 2026-11-11: "that's my money spent … future agents see what to do and what not to"): its folder,
    model, the frame check's words and how it ended. Its video is kept beside the current one as <kind>-<folder>.webm."""
    rs = _rs()
    d_ = rs.SHOW_ADS_DIR / cat_id; cur_ = d_ / f'{k}.webm'
    if cur_.exists():
        rs.shutil.copyfile(cur_, d_ / f'{k}-{rs.re.sub(r"[^a-z0-9]", "", str(ws))}.webm')
    j_ = ((((rs._load()['cats'].get(cat_id) or {}).get('showAds')) or {}).get(k)) or {}
    row_ = {'ws': ws, 'at': round(rs.time.time()), 'model': rs._ads.MODEL, 'faults': [str(f)[:300] for f in (faults or [])][:8], 'outcome': outcome}
    rs._ads_set(cat_id, k, tries=[*(j_.get('tries') or []), row_][-40:])


def _media_library(cat_id, cat):
    """🗂 Everything one agent made, every proof kind, newest first (owner 2026-11-11: the editor's Video / Image / 3D tabs reuse it):
    its Showcase ad videos, the images and videos it made, and the 3D scenes it filed. Links only, no bytes. Site snapshots are evidence, never content (owner 2026-11-11)."""
    rs = _rs()
    rows = []; cid_ = rs.re.sub(r'[^a-z0-9]', '', cat_id)
    d_ = rs.SHOW_ADS_DIR / cid_
    for f_ in (sorted(d_.glob('*.webm')) if d_.is_dir() else []):
        k_, _, w_ = f_.stem.partition('-')
        if k_ in rs._ads.KINDS:
            rows.append({'id': f'ad{k_}{w_}', 'type': 'video', 'proof': rs._ads.NAME[k_], 'title': f"{rs._ads.NAME[k_]} ad{' · ' + w_ if w_ else ''}", 'at': round(f_.stat().st_mtime),
                         'src': f'/api/cats/{cat_id}/showad/{k_}', 'q': f'ws={w_}' if w_ else '', 'from': 'Showcase ad'})
    for w in rs._ws_list(cat)[-80:]:
        if w.get('kind') not in ('content', 'build'):
            continue
        doc_ = rs._ws_load(cat_id, w['id']) or {}
        for m_ in doc_.get('messages') or []:
            md_ = m_.get('media') if isinstance(m_, dict) else None
            if md_ and md_.get('status') == 'done' and md_.get('url'):
                rows.append({'id': md_.get('id'), 'type': 'video' if md_.get('kind') == 'video' else 'image', 'proof': 'PoC', 'title': str(md_.get('prompt') or 'made')[:40], 'at': int(md_.get('doneAt') or md_.get('at') or 0),
                             'src': md_['url'], 'q': '', 'from': f"{md_.get('label') or 'made'} · {w.get('name') or ''}".strip(' ·')})
        sc_ = doc_.get('scene3d')
        if isinstance(sc_, dict) and (sc_.get('objects') or sc_.get('hero')):
            rows.append({'id': w['id'], 'type': '3d', 'proof': 'PoStatic', 'title': str(w.get('name') or '3D scene')[:40], 'at': int(w.get('at') or 0), 'ws': w['id'],
                         'objects': len(sc_.get('objects') or []), 'from': 'PoStatic 3D'})
    rows.sort(key=lambda r: -r['at'])
    return rows


def _ads_lab(cat_id, cat):
    """→ every ad attempt of one agent, newest first: proof type, folder, model, $, page versions, the exact faults it was sent back with, the end."""
    rs = _rs()
    rows = []; own_ = ' + '.join(str(m).split('/')[-1] for m in ((cat.get('brainsCfg') or {}).get('brains') or [])[:2]) or 'its own minds'
    for k, j in (cat.get('showAds') or {}).items():
        tries = {}
        for t_ in j.get('tries') or []:
            tries.setdefault(t_.get('ws'), []).append(t_)
        for ws in [*(j.get('lostWs') or []), *([j['ws']] if j.get('ws') else [])]:
            doc = rs._ws_load(cat_id, ws) or {}; at_ = doc.get('at') or 0; mine_ = tries.get(ws) or []
            asks_ = [str(m.get('text') or '') for m in doc.get('messages') or [] if m.get('by') == 'you'][1:]   # every ask after the brief is a fix it was sent back with
            last_ = mine_[-1] if mine_ else {}
            rows.append({'kind': k, 'name': rs._ads.NAME.get(k, k), 'cat': cat_id, 'ws': ws, 'at': at_, 'cost': round(float(doc.get('cost') or 0), 4),
                         'versions': len(doc.get('versions') or []), 'model': last_.get('model') or (rs._ads.MODEL if at_ >= rs.AD_SONNET_AT else own_),
                         'faults': [f for t_ in mine_ for f in t_.get('faults') or []][:12] or [a_[:400] for a_ in asks_][:4],
                         'outcome': last_.get('outcome') or (('now · ' + str(j.get('state') or '')) if ws == j.get('ws') else 'replaced'),
                         'current': ws == j.get('ws'), 'video': (rs.SHOW_ADS_DIR / cat_id / f'{k}-{ws}.webm').exists()})
    return sorted(rows, key=lambda r: -(r['at'] or 0))


async def _ads_write(cat_id, k, ws, fix=None):
    """🎬 One ad page written whole by show_ads.MODEL with the ad writer's own brief and every earlier attempt's faults as lessons; filed as a new
    version of its folder (the folder and its cost stay the record). → True when a whole page came back."""
    rs = _rs()
    rs._OR_CAT.set(cat_id)
    cat_ = rs._load()['cats'].get(cat_id) or {}; doc_ = rs._ws_load(cat_id, ws) or {}; cur_ = ((doc_.get('versions') or [{}])[-1]).get('html') or ''
    past_ = [f_ for c_ in rs._load()['cats'].values() if c_.get('showAds') and rs._same_owner(cat_, c_) for r_ in rs._ads_lab(c_['id'] if c_.get('id') else cat_id, c_) for f_ in r_['faults']]
    user_ = rs._ads.ask_for(k) + rs._ads.lessons(past_) + (f"\n\nTHE FILE NOW:\n{cur_[:60000]}\n\nREWRITE THE WHOLE FILE. {fix}" if fix and cur_ else '')
    text_, usd_ = await rs._or_call(rs._ads.MODEL, [{'role': 'system', 'content': rs._ads.AD_SYS}, {'role': 'user', 'content': user_}], max_tokens=16000)
    html_ = rs._aip.html_of(text_) if text_ else ''; ok_ = bool(html_ and rs._feat.page_complete(html_)); now_ = rs.time.time()
    doc_ = rs._ws_load(cat_id, ws) or doc_; doc_['cost'] = round(float(doc_.get('cost') or 0) + float(usd_ or 0), 6); doc_.pop('busy', None); doc_['pending'] = False
    if fix:
        rs._feat.add_msg(doc_, 'you', fix, now_)
    if ok_:
        doc_.setdefault('versions', []).append({'html': html_, 'at': round(now_), 'by': rs._ads.MODEL.split('/')[-1]})
    rs._feat.add_msg(doc_, rs._ads.MODEL.split('/')[-1], f"{'Ad page ' + str(len(doc_.get('versions') or [])) + ' written whole' if ok_ else 'The reply was not a whole page'} · ${float(usd_ or 0):.3f}", now_)
    rs._ws_save(cat_id, doc_)
    return ok_


async def _ads_film(cat_id, k, ws):
    """🎬 Records one ad. A page that crashes while it plays, or breaks its own frame (text past the edges or on top of text), gets ONE fix pass in its own folder with its exact errors (counted toward the cap,
    only while the cap allows another build), then is recorded again; still crashing → 'page error' with the error, never a blank video called done."""
    rs = _rs()
    for attempt_ in (0, 1):
        html_ = ((rs._ws_load(cat_id, ws) or {}).get('versions') or [{}])[-1].get('html') or ''
        if not html_:
            rs._ads_set(cat_id, k, ws=ws, state='no page'); return
        rs._ads_set(cat_id, k, ws=ws, state='recording'); errs_ = []; lay_ = []
        got_ = await rs._ads.record(rs._kits.open_for_kits(rs._ws_placed(cat_id, html_)), rs.SHOW_ADS_DIR / cat_id / f'{k}.webm', rs._fb.chromium_path(), errs=errs_, lay=lay_)
        if not errs_ and not lay_:
            rs._ads_set(cat_id, k, ws=ws, state='done' if got_ else 'no video', err=None, fit=1); rs._ads_try(cat_id, k, ws, [], 'passed' if got_ else 'no video'); return
        why_ = (errs_ or lay_)[0][:200]
        if attempt_ or not rs._ads.may_start(((rs._load()['cats'].get(cat_id) or {}).get('showAds')) or {}, rs._ads_cost(cat_id))[0]:
            rs._ads_set(cat_id, k, ws=ws, state='page error', err=why_, fit=1); rs._ads_try(cat_id, k, ws, errs_ + lay_, 'failed the check'); return
        fix_ = rs._ads.fix_ask(errs_, lay_)
        rs._ads_set(cat_id, k, ws=ws, state='fixing', err=why_); rs._ads_try(cat_id, k, ws, errs_ + lay_, 'sent back once')
        try:
            await rs._ads_write(cat_id, k, ws, fix=fix_)
        except Exception as e_:   # noqa: BLE001 — the page stays as it was and is filmed again
            print(f'[ads] fix write failed: {type(e_).__name__}')


async def _ads_run(cat_id):
    """🎬 One ad per proof type, one at a time, under the $1.25 cap; each finished page is recorded to a video."""
    rs = _rs()
    # Once per run (no ad task is alive here): a built page with no video (no ffmpeg, a deleted .webm) is recorded again, never rebuilt (no new spend);
    # a build or recording a restart killed (2026-11-11) is recorded if its page exists, else built again, its spend kept in lostWs for the cap.
    for k_, j_ in list((((rs._load()['cats'].get(cat_id) or {}).get('showAds')) or {}).items()):
        st_ = j_.get('state'); cut_ = st_ in ('building', 'recording', 'fixing')
        if not j_.get('ws') or not (cut_ or st_ == 'no video' or (st_ == 'done' and not (j_.get('fit') and (rs.SHOW_ADS_DIR / cat_id / f'{k_}.webm').exists()))):   # a done ad filmed before the frame check is checked once
            continue
        html_ = ((rs._ws_load(cat_id, j_['ws']) or {}).get('versions') or [{}])[-1].get('html') or ''
        if html_:
            await rs._ads_film(cat_id, k_, j_['ws'])
        elif cut_:
            rs._ads_set(cat_id, k_, ws=None, state='waiting', lostWs=[*(j_.get('lostWs') or []), j_['ws']])
    while True:
        store = rs._load(); cat = store['cats'].get(cat_id)
        if not cat:
            return
        jobs = cat.get('showAds') or {}
        k = rs._ads.next_kind(jobs)
        if not k:
            return
        ok, _s = rs._ads.may_start(jobs, rs._ads_cost(cat_id))
        if not ok:
            rs._ads_set(cat_id, k, state='over budget'); return
        now = rs.time.time()
        try:
            row_ = rs._feat.new_folder(cat, 'build', f'{rs._ads.NAME[k]} ad', now, ad=True)
        except ValueError:
            rs._ads_set(cat_id, k, state='no room for a folder'); return
        doc_ = rs._feat.new_doc(row_); doc_['cfg'] = {'research': False, 'suggest': False, 'review': False}; text_ = rs._ads.ask_for(k)
        rs._feat.add_msg(doc_, 'you', text_, now); doc_['complete'] = False; doc_['pending'] = True
        rs._ws_save(cat_id, doc_); cat.setdefault('showAds', {})[k] = {'ws': row_['id'], 'state': 'building', 'at': round(now), **{x_: jobs[k][x_] for x_ in ('lostWs', 'tries') if (jobs.get(k) or {}).get(x_)}}; rs.keep_owned(cat); rs._save(store)
        try:
            await rs._ads_write(cat_id, k, row_['id'])
        except Exception as e_:   # noqa: BLE001 — no page: the film step says so
            print(f'[ads] write failed: {type(e_).__name__}')
        await rs._ads_film(cat_id, k, row_['id'])


def _ws_list(cat):
    """🗂 The folders the owner sees: an ad folder a newer build replaced (its showAds lostWs) folds away, kept on disk, still counted in the cap."""
    gone_ = {w for j in (cat.get('showAds') or {}).values() for w in (j.get('lostWs') or [])}
    return [w for w in cat.get('workspaces') or [] if w.get('id') not in gone_]


def _ads_view(cat_id, cat):
    rs = _rs()
    return rs._ads.view(cat.get('showAds') or {}, rs._ads_cost(cat_id), lambda k: (rs.SHOW_ADS_DIR / cat_id / f'{k}.webm').exists())


def _ws_dead(cat_id, ws_id, at, now):
    """A folder's run is dead if its task ended or a restart lost it, or after WS_MAX_S. A slow model is not dead (owner 2026-11-05: OSSY and G4 kept "stopping" at the old 240 seconds while still writing). Pure on its inputs."""
    rs = _rs()
    t_ = rs._WS_LIVE.get((cat_id, ws_id))
    if t_ is not None and not t_.done():
        return now - at > rs.WS_MAX_S
    return now - at > rs.WS_ORPHAN_S


def _ws_view(cat_id, ws_id):
    rs = _rs()
    d_ = rs._ws_load(cat_id, ws_id)
    if not d_:
        raise rs.HTTPException(404, 'No such folder.')
    if d_.get('busy') and rs._ws_dead(cat_id, ws_id, float(d_['busy'].get('at') or 0), rs.time.time()):   # a run that died never locks the folder, and says so
        d_['busy'] = None; d_['messages'] = list(d_.get('messages') or []) + [{'by': 'Working', 'text': 'That run stopped before it finished, so nothing was filed.', 'at': round(rs.time.time())}]; rs._ws_save(cat_id, d_)
    rs._media_resume(cat_id, d_)
    v_ = d_.get('versions') or []
    return {**{k: d_.get(k) for k in ('id', 'kind', 'name', 'messages', 'busy', 'stage', 'plan', 'complete', 'pending', 'cost', 'lastCost', 'character')}, 'unfinished': rs._feat.unfinished_of(d_), 'cfg': rs._feat.build_cfg(d_), 'versions': len(v_), 'code': v_[-1]['html'] if v_ else '', 'previousCode': v_[-2]['html'] if len(v_) > 1 else '', 'preview': rs._feat.preview(rs._ws_placed(cat_id, v_[-1]['html'])) if v_ else '', 'source': d_.get('source') or [], 'models3d': rs._om.view(d_.get('models3d')), 'cut': bool(v_) and not rs._feat.page_complete(v_[-1]['html']), 'by': v_[-1].get('by') if v_ else None, 'storeCheck': d_.get('storeCheck')}


def _media_dir():
    rs = _rs()
    return rs.DATA_DIR / 'media'


def _media_msg(doc, mid):
    return next((m for m in doc.get('messages') or [] if (m.get('media') or {}).get('id') == mid), None)


def _media_set(cat_id, ws_id, mid, keep=None, **fields):
    """Writes a job's state into its folder message. A run that saved over it puts the message back (never a lost job)."""
    rs = _rs()
    d_ = rs._ws_load(cat_id, ws_id)
    if not d_:
        return None
    m_ = rs._media_msg(d_, mid)
    if m_ is None and keep:
        m_ = rs.json.loads(rs.json.dumps(keep)); d_['messages'] = list(d_.get('messages') or []) + [m_]
    if m_ is None:
        return None
    m_['media'] = {**(m_.get('media') or {}), **fields}
    rs._ws_save(cat_id, d_)
    md_ = m_['media']
    if fields.get('status') == 'done' and fields.get('url'):   # 🎬 a filed PoC of this folder gets the new file too (made after filing, it still shows)
        try:
            st_ = rs._load(); c_ = st_['cats'].get(cat_id)
            f_ = next((f for f in (c_ or {}).get('pocFolders') or [] if f.get('ws') == ws_id), None)
            if f_ is not None:
                f_['media'] = ([x for x in f_.get('media') or [] if x.get('id') != str(mid)]
                               + [{'id': str(mid), 'kind': md_.get('kind'), 'url': md_.get('url'), 'label': md_.get('label'), 'prompt': str(md_.get('prompt') or '')[:200]}])[-8:]
                rs._save(st_)
        except (KeyError, OSError, ValueError) as e:
            print(f'[media] folder not updated: {e}')
    if fields.get('status') == 'done' and (md_.get('paidUsd') or md_.get('usd')):   # 🧾 a made image / video is a bill too (provider's own cost, else its list price)
        rs._receipt_write({'id': str(mid), 'cat': cat_id, 'at': rs.time.time(), 'provider': (rs._mg.PROVIDERS.get(md_.get('provider')) or {}).get('name') or md_.get('provider'),
                        'model': md_.get('model'), 'usd': float(md_.get('paidUsd') or md_.get('usd') or 0), 'tokens': None,
                        'status': 'provider reported' if md_.get('paidUsd') else 'list price', 'funding': 'FEELESS key' if md_.get('house') else 'owner key'})
    return m_


def _media_resume(cat_id, doc):
    rs = _rs()
    for m_ in doc.get('messages') or []:
        md = m_.get('media') or {}
        if md.get('status') in ('queued', 'running') and md.get('id') not in rs._MEDIA_LIVE:
            try:
                rs.asyncio.get_running_loop().create_task(rs._media_run(cat_id, doc.get('id'), md['id']))
            except RuntimeError:
                return


def _feed_push(cat_id, item):
    rs = _rs()
    q = rs._FEED.setdefault(cat_id, []); q.insert(0, {**item, 'at': round(rs.time.time(), 3)}); del q[30:]

