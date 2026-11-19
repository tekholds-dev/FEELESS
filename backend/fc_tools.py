"""🧹 Pool rules, receipts, model prints, cat tools, internal routes — split out of fc_desk.py by scripts/split-module.py (owner 2026-11-17 cleanup); first moved whole out of feecat_service.py.
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches feecat_service still
reaches it, and every function here is still reachable on feecat_service under its own name. Constants, classes and state live in the service."""
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401

router = APIRouter()


def _rs():
    import feecat_service
    return feecat_service


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
            rows.append(rs._record_file(c_, 'poc', {'id': f'poc{int(rs.time.time())}{i}', 'ws': ws, 'n': rs._next_n(rows), 'kind': 'PoC', 'at': round(rs.time.time()), 'status': 'closed', 'paper': True,
                         'topic': f'Week plan · {name}' + (f' · {topic}' if topic else ''), 'week': {**plan, 'style': key},
                         'calls': [{'mind': i, 'name': str(brains[i % len(brains)]).split('/')[-1][:24], 'angle': name, 'post': plan['idea'] or f"{len(plan['posts'])} posts", 'why': f"{len(plan['posts'])} posts over the week"}],
                         'cost': round(usd or 0, 5), **({'media': media_} if media_ else {})}))   # 🧾 Slice 0: the true record
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


POC_SHOTS = ('https://news.ycombinator.com/', 'https://news.google.com/', 'https://en.wikipedia.org/wiki/Main_Page', 'https://github.com/trending',
             'https://www.producthunt.com/', 'https://www.bbc.com/news')   # 👣 Slice 0: the free snapshot pages a PoC rotates through (3 a proof, least used first)


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
            return i, await rs._ws_ask(cat, m, rs._feat.POC_SYS.format(name='Mind ' + 'AB'[i]) + rs._foot.note('poc', cat.get('pocFolders'), i) + rs._feat._sources.proof_line('poc') + read_ + rs._recall(cat, 'Content', topic) + rs._know.for_ask(topic) + rs._foot.note('poc', cat.get('pocFolders'), i) + rs._prec.back_line(cat.get('footBack'), 'poc', rs.time.time()), f'The owner wants: {topic or "whatever fits them best right now"}\nTheir notes: {notes}\nTrending now:\n{lines}', 260)
        for i, (raw, usd, own) in await rs.asyncio.gather(*(one(i, m) for i, m in enumerate(brains))):
            cost += usd; paid_own = own
            try:
                d_ = rs.json.loads(rs.re.search(r'\{.*\}', raw, rs.re.S).group(0))
            except (AttributeError, ValueError):
                d_ = {'post': raw[:240]}
            calls.append({'mind': i, 'name': str(brains[i]).split('/')[-1][:24], **{k: str(d_.get(k) or '')[:300] for k in ('angle', 'post', 'why', 'trend')}})
        shots_ = []
        words_ = rs._marks.words_of([x for v in tr.values() for x in (v or [])[:3]] + [topic or ''])
        shot_at_ = rs._prec.fresh_sites(cat.get('footBack'), 'poc', rs.time.time(), rs._foot.order_sites('poc', list(POC_SHOTS), cat.get('pocFolders')), keep=3)[:3]   # 👣 Slice 0: the pages used least lately first, a sent-back repeat's pages left out
        for n_, r_ in enumerate(await rs._fb.shots(shot_at_, words_, rs.time.time())):   # 🖍 what it found, snapshotted free, with what it read boxed
            try:
                d_ = rs.POWSHOTS_DIR / rs.re.sub(r'[^a-z0-9]', '', pid_); d_.mkdir(parents=True, exist_ok=True); name_ = f"{rs.re.sub(r'[^a-z0-9]', '', r_['site'])[:30]}_{n_}.jpg"; (d_ / name_).write_bytes(r_['jpg'])
                shots_.append({'site': r_['site'], 'url': r_['url'], 'title': r_['title'], 'file': name_, 'at': round(rs.time.time()), 'found': list(r_['found'])[:12], 'missing': r_['missing'][:12], 'sha': r_['sha']})
            except OSError as e:
                print(f'[poc] snapshot not kept: {e}')
        store = rs._load(); c_ = store['cats'].get(cat_id)
        if c_:
            rows = list(c_.get('pocFolders') or [])
            f_ = {'id': pid_, 'kits': rs._KIT_LAST.get((cat_id, 'poc')) or [], **({'ws': ws} if ws else {}), 'shots': shots_, 'sitesRead': sites_read_, 'n': rs._next_n(rows), 'kind': 'PoC', 'at': round(rs.time.time()), 'status': 'closed', 'paper': True, 'topic': topic or 'best fit now', 'trends': {k: v[:5] for k, v in tr.items()}, 'calls': calls, 'cost': round(cost, 5)}
            if rs._foot_back(c_, 'poc', f_):   # 👣 Slice 0: mostly what a past PoC read and said → back once, from other pages, before it files
                if cost and not paid_own and c_.get('brainsCfg'):
                    rs._lc.charge(c_['brainsCfg'], cost)
                rs._save(store)
                return await rs._poc_file(cat_id, topic, ws)
            rows.append(rs._record_file(c_, 'poc', f_))
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
    try:   # 🗺 Slice 11: every settled PoB moves the trust of each source it read, once
        rs._cahead.settle_folders(rs.DATA_DIR, list(store['cats'].values()), now)
    except Exception as e:   # noqa: BLE001
        print(f'[atlas] settle: {type(e).__name__}')
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

