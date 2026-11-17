"""🧹 Cat reviews, brains, listings — moved whole out of feecat_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches feecat_service still
reaches it, and every function here is still reachable on feecat_service under its own name. Constants, classes and state live in the service."""
import feecat_service as _RSM  # noqa: E402,F401  (body models; this module is imported at the END of the service)
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401

router = APIRouter()


def _rs():
    import feecat_service
    return feecat_service


def rate_ok(key, now=None, store=None):
    """Sliding window for owner doors. Pure (tests pass their own store)."""
    rs = _rs()
    store = rs._RATE if store is None else store
    now = now or rs.time.time()
    q = [t for t in store.get(key, []) if now - t < rs.RATE_WIN]
    ok = len(q) < rs.RATE_MAX
    if ok:
        q.append(now)
    store[key] = q
    if len(store) > 5000:
        store.clear()
    return ok


def _kit_pins():
    """{npm package: (pinned version, 'major' | 'exact')} for every tracked kit, from the live pins kit_fresh keeps fresh."""
    rs = _rs()
    try:
        return {pkg: (rs._kfresh.current(rs._kits.KIT_USE, kid), mode) for kid, (pkg, mode, _t) in rs._kfresh.TRACK.items() if rs._kfresh.current(rs._kits.KIT_USE, kid)}
    except Exception as e:   # noqa: BLE001
        print(f'[review] kit pins: {str(e)[:80]}'); return {}


async def _review_rows():
    """The proof record, read at most every 10 minutes for the judges' own-miss lines. [] when it can't be read (a judge still judges)."""
    rs = _rs()
    if rs._REVIEW_ROWS['at'] < rs.time.time() - 600:
        try:
            rs._REVIEW_ROWS['v'] = await rs.asyncio.to_thread(rs._pev.rows, rs.DATA_DIR / rs._pev.DB_NAME)
        except Exception as e:   # noqa: BLE001
            print(f'[review] record: {str(e)[:80]}')
        rs._REVIEW_ROWS['at'] = rs.time.time()
    return rs._REVIEW_ROWS['v']


def _review_titles(store):
    """{(kind, proof id): title} so a judge's miss names the proof it got wrong."""
    rs = _rs()
    return {(k, f.get('id')): f.get('topic') or f.get('sym') or f.get('name') for c in store['cats'].values() for k, (_c, key) in rs._mission.KINDS.items() for f in c.get(key) or []}


async def _review_one(store):
    """OSSY then G4 read the newest unreviewed proof and each gives its own verdict. Every call is logged with the model that really answered."""
    rs = _rs()
    due = rs._review.next_due(store, rs._REVIEWED, handles=rs.REVIEW_SCOPE or None)
    if not due:
        return None
    cid, kind, f = due; rs._REVIEWED.add((cid, f.get('id')))
    cat = store['cats'][cid]; f_ = dict(f)
    if kind in ('pos', 'poc') and f.get('ws'):
        vs = (rs._ws_load(cid, f['ws']) or {}).get('versions') or []; v = int(f.get('version') or len(vs)) - 1
        f_['_page'] = (vs[v] if 0 <= v < len(vs) else (vs[-1] if vs else {})).get('html') or ''
    env = rs._mission.envelope(kind, f, rs.time.time(), cat)
    body = rs._review.brief(kind, f_, env); by = {}
    builders_ = rs._review.builders_of(f, cat.get('brainsCfg'), kind); out_ = rs._review.recused(builders_)   # 🔒 a builder never judges its own proof
    sic = next((c for c in store['cats'].values() if c.get('handle') == 'sicarios'), None) or {'id': 'collective', 'ownerStaff': True}
    rows_ = await rs._review_rows(); titles_ = rs._review_titles(store)
    live_ = rs._JUDGING[cid] = rs._review.live_start(kind, f, out_)
    for key, model, name in rs._review.REVIEWERS:
        if key in out_:
            by[key] = None; continue
        rs._review.live_judge(live_, key, state='think')
        tok = rs._CALL_CTX.set({'kind': kind, 'ref': f'review:{f.get("id")}', 'minds': [m for _k, m, _n in rs._review.REVIEWERS]})
        try:
            raw, _usd, _via = await rs.asyncio.wait_for(rs._think({**sic, 'ownerStaff': True}, model, [{'role': 'system', 'content': rs._review.SYS}, {'role': 'user', 'content': body + rs._review.misses_line(rs._review.misses(rows_, key, titles_), name)}], max_tokens=700), 240)   # 🎯 COL-20: each judge reads its OWN misses (the evidence hash stays on the proof alone)
            by[key] = rs._review.verdict_of(raw, rs.time.strftime('%Y-%m-%d', rs.time.gmtime()))
            if by[key]:
                row_ = next((r for r in reversed(rs._calls_of(sic.get('id'), 50)) if r.get('ref') == f'review:{f.get("id")}' and r.get('asked') == model), {})
                by[key]['answeredBy'] = f"{row_.get('route') or '?'} · {row_.get('model') or '?'}"   # who REALLY answered, from the call log (a stand-in shows as one)
            rs._review.live_judge(live_, key, by[key])
        except Exception as e:   # noqa: BLE001: one reviewer down never stops the other
            print(f'[review] {name}: {type(e).__name__}')
            by[key] = None
            rs._review.live_judge(live_, key, None)
        finally:
            rs._CALL_CTX.reset(tok)
    rv = {**rs._review.combine(by, out_, builders_, body), 'at': round(rs.time.time())}
    live_.update(done=rv['at'], score=rv['score'], verdict=rv['verdict'], agree=rv['agree'])
    if kind == 'pos' and f_.get('_page'):   # 🕵 P1: code-run checks the builders are never shown; independent of any judge (they still run when every judge sat out)
        rv['hidden'] = rs._ps_hidden.run(f_['_page'], rs._kit_pins())   # P2: + every reused kit on today's tested pin (the review lists the kits it checked)
    rs._REVIEW_DONE.append((cid, kind, f.get('id'), rv)); rs._POW_WAKE.set()
    return rv


def _db_grow(store):
    """🗄 AGT-11: each agent's closed proofs are added to its own database, sealed with its key. Idempotent; a write error never stops the engine."""
    rs = _rs()
    n = 0
    for cid, c in store['cats'].items():
        if c.get('revoked'):
            continue
        try:
            path_ = rs._adb.path_of(rs.DATA_DIR, cid)
            seen_ = rs._ADB_SEEN.get(cid)
            if seen_ is None:
                seen_ = rs._ADB_SEEN[cid] = rs._adb.ids(path_)
            for k, (code_, key) in rs._mission.KINDS.items():
                for f in c.get(key) or []:
                    fid = str(f.get('id') or '')
                    if not fid or fid in seen_ or f.get('status') != 'closed':
                        continue
                    rs._adb.add(path_, fid, k, f"{code_} · {f.get('topic') or f.get('sym') or f.get('name') or fid}", rs._adb.summary(k, f), lambda raw, i=cid: rs._ck.seal_bytes(raw, i),
                             tags=[k] + ([str(f.get('sym'))] if f.get('sym') else []), source='proof', now=float(f.get('closedAt') or f.get('soldAt') or f.get('at') or rs.time.time()))
                    seen_.add(fid); n += 1
        except Exception as e:   # noqa: BLE001
            print(f'[db] {cid}: {str(e)[:100]}')
    return n


def _db_shared_line(cat, kind):
    """Rows the owner's other agents shared with this one (select access), as data in its brief."""
    rs = _rs()
    try:
        store_ = rs._load(); mine_ = [cid for cid, c in store_['cats'].items() if not c.get('revoked') and rs._same_owner(cat, c)]
        return rs._adb.shared_line(rs._adb.shared_to(rs.DATA_DIR, cat.get('id'), mine_, lambda cid: (lambda raw: rs._ck.unseal_bytes(raw, cid)), kind or None))
    except Exception as e:   # noqa: BLE001
        print(f'[db] shared: {str(e)[:80]}')
        return ''


def _pot_alert_pass(store, now=None):
    """✅ AGX-10: each agent's proofs closed in the last 3 days that went into the pot under 1x get ONE chat line (what to fix first) and, for a
    PoStatic / PoC, a redo row in its Approve inbox. Never calls a model and never runs the redo: only the owner's Approve tap does.
    The first time it sees an agent, only its newest such proof speaks (no backlog flood)."""
    rs = _rs()
    now_ = rs.time.time() if now is None else now; saved_ = None; n = 0
    for c in store['cats'].values():
        if c.get('revoked') or not (c.get('brainsCfg') or {}).get('brains'):
            continue
        first_ = 'potAlertSince' not in c
        since_ = max(float(c.setdefault('potAlertSince', round(now_ - 86400))), now_ - 3 * 86400); done_ = set(c.get('potAlerted') or [])
        rows_ = []
        for k, key in rs._PROOF_KEYS.items():
            for f in c.get(key) or []:
                if isinstance(f, dict) and f.get('status') == 'closed' and f.get('id') not in done_ and float(f.get('closedAt') or f.get('soldAt') or f.get('at') or 0) >= since_:
                    saved_ = rs._weights.load(rs.DATA_DIR) if saved_ is None else saved_
                    rows_.append((k, f, rs._proof_view(c, k, f, 300.0, saved_)))
        due_ = rs._appr.due(rows_, since_, done_)
        if first_ and len(due_) > 1:
            c['potAlerted'] = (list(c.get('potAlerted') or []) + [f.get('id') for _k, f, _v in due_[:-1]])[-rs._appr.ALERTED_KEEP:]; due_ = due_[-1:]
        for k, f, v in due_[:2]:
            lift_ = rs._appr.biggest_lift(v.get('parts')); item_ = rs._appr.redo_item(k, f, lift_, (c.get('brainsCfg') or {}).get('brains'), now_)
            kept_ = rs._appr.add(c, item_) if item_ else None
            c['chat'] = (list(c.get('chat') or []) + [{'by': 'cats', 'text': rs._appr.alert_text(k, f, v, lift_, bool(kept_)), 'at': now_, **({'approve': kept_['id']} if kept_ else {})}])[-200:]
            c['potAlerted'] = (list(c.get('potAlerted') or []) + [f.get('id')])[-rs._appr.ALERTED_KEEP:]; n += 1
            if kept_ and c['id'] in rs._KEPT:   # the redo row survives the save overlay too (added only: an owner's tap meanwhile is never undone)
                ap_ = rs._KEPT[c['id']].setdefault('approvals', [])
                if isinstance(ap_, list) and not any(isinstance(x, dict) and x.get('id') == kept_['id'] for x in ap_):
                    ap_.append(rs.json.loads(rs.json.dumps(kept_)))
        rs._pot_keep(c)
    return n


def _pot_keep(c):
    """🔁 potAlerted / potAlertSince are owner keys, so _save lays the last owner snapshot (_KEPT) over the engine's copy: without this the alert was
    forgotten on every save and re-sent every pass (owner's PoB #16, 2026-11-15: the same 'went into the pot' line every 20 s). Adds only."""
    rs = _rs()
    k_ = rs._KEPT.get(c.get('id'))
    if k_ is None:
        return
    if 'potAlertSince' in c:
        k_.setdefault('potAlertSince', c['potAlertSince'])
    have_ = list(k_.get('potAlerted') or [])
    k_['potAlerted'] = (have_ + [x for x in c.get('potAlerted') or [] if x not in have_])[-rs._appr.ALERTED_KEEP:]


def _review_apply(store):
    """The engine files each verdict on its folder and in the proof history."""
    rs = _rs()
    n = 0
    if rs.REVIEW_SCOPE:   # a review filed on an agent outside the test bench comes off (the proof history keeps its event)
        for c_ in store['cats'].values():
            if c_.get('handle') not in rs.REVIEW_SCOPE:
                for _k, (_c, key_) in rs._mission.KINDS.items():
                    for f_ in c_.get(key_) or []:
                        if f_.pop('review', None) is not None:
                            n += 1
    while rs._REVIEW_DONE:
        cid, kind, fid, rv = rs._REVIEW_DONE.pop(0)
        key = rs._mission.KINDS[kind][1]
        f = next((x for x in (store['cats'].get(cid) or {}).get(key) or [] if x.get('id') == fid), None)
        if f is None or (((f.get('review') or {}).get('v') or 0) >= rv.get('v', 0) and not rs._review.stand_in(f.get('review'))):   # an older version's review is replaced (and a Qwen-voiced ZED one)
            continue
        f['review'] = rv; n += 1
        rs._REVIEW_LESSONS[kind] = rs._review.lessons(store, kind)
        try:
            rs._pev.append(rs.DATA_DIR / rs._pev.DB_NAME, kind, fid, 'review', {'reviewers': {k: {'score': v['score'], 'verdict': v['verdict'], 'answeredBy': v.get('answeredBy'), 'why': str(v.get('why') or '')[:120]} for k, v in rv['by'].items()}, 'score': rv['score'], 'verdict': rv['verdict'],
                                                                     **{k: rv.get(k) for k in ('rubric', 'builders', 'recused', 'families', 'oneFamily', 'evidenceSha', 'independent') if rv.get(k) not in (None, [], '')},
                                                                     **({'hidden': {**{k: rv['hidden'][k] for k in ('v', 'passed', 'total', 'failed')}, 'kits': [f"{x['pkg']}@{x['used']}{'' if x['ok'] else ' (stale, pin ' + x['pin'] + ')'}" for x in rv['hidden'].get('kits') or []][:8]}} if rv.get('hidden') else {})}, cat=cid)   # 🧾 reproducible: rubric, builders, judges, evidence hash
        except Exception as e:   # noqa: BLE001
            print(f'[review] history: {str(e)[:80]}')
    return n


def _outside_review_apply(store, cat_id, kind, fid, judge, t_):
    """File an outside judge's review (owner or Claude) on one proof folder + its proof-history event. → the folder's new review."""
    rs = _rs()
    if kind not in rs._mission.KINDS:
        raise rs.HTTPException(400, 'Unknown proof kind.')
    cat = (store.get('cats') or {}).get(cat_id) or {}
    f = next((x for x in cat.get(rs._mission.KINDS[kind][1]) or [] if x.get('id') == fid), None)
    if f is None:
        raise rs.HTTPException(404, 'No such proof.')
    try:
        rv = rs._review.outside(f.get('review'), judge, str(t_.get('verdict') or ''), t_.get('score') if t_.get('score') is not None else -1, t_.get('why'), t_.get('checks') or [])
    except (ValueError, TypeError) as e:
        raise rs.HTTPException(400, str(e))
    f['review'] = rv; rs.keep_owned(cat); rs._save(store)
    try:
        v = rv['by'][judge]
        rs._pev.append(rs.DATA_DIR / rs._pev.DB_NAME, kind, fid, 'review', {'reviewers': {judge: {'score': v['score'], 'verdict': v['verdict'], 'answeredBy': v['answeredBy'], 'why': v['why'][:120]}},
                                                                   'score': rv['score'], 'verdict': rv['verdict'], 'outside': judge, 'recused': rv.get('recused') or []}, cat=cat_id)
    except Exception as e:   # noqa: BLE001
        print(f'[review] outside history: {str(e)[:80]}')
    return {'review': rv}


@router.post('/api/cats/internal/week-plans')
async def week_plans_internal(p: _RSM.WeekRunIn, request: Request):
    """🗓 Readiness runs (internal key only): its minds write the 3 week scenarios into a PoC folder — `ws`, or a new content folder named
    `name` — exactly as the Week tab's button does. Paper only: nothing is posted."""
    rs = _rs()
    rs._internal(request)
    store = rs._load(); cat = (store.get('cats') or {}).get(p.cat)
    if not cat or not (cat.get('brainsCfg') or {}).get('brains'):
        raise rs.HTTPException(404, 'No agent with a mind.')
    ws = p.ws
    if not ws:
        try:
            row_ = rs._feat.new_folder(cat, 'content', p.name[:32], rs.time.time())
        except ValueError as e:
            raise rs.HTTPException(409, str(e))
        rs._ws_save(p.cat, rs._feat.new_doc(row_)); rs.keep_owned(cat); rs._save(store); ws = row_['id']
    if (rs._ws_load(p.cat, ws) or {}).get('kind') != 'content':
        raise rs.HTTPException(400, 'Week plans live in a PoC folder.')
    if p.cat in rs._WEEK_BUSY:
        raise rs.HTTPException(409, 'Already writing week plans.')
    rs._WEEK_BUSY.add(p.cat); rs.asyncio.create_task(rs._week_file(p.cat, ws, p.topic[:120]))
    return {'ok': True, 'ws': ws}


@router.post('/api/cats/internal/review-outside')
async def review_outside_internal(p: _RSM.OutsideReviewIn, request: Request):
    """🧑‍⚖️ Claude's outside review (owner 2026-11-14: "I or you can grade the proof"): internal key only, filed as judge `claude`."""
    rs = _rs()
    rs._internal(request)
    return rs._outside_review_apply(rs._load(), p.cat, p.kind, p.fid, 'claude', p.model_dump())


async def _review_loop():
    """🧑‍⚖️ Every REVIEW_EVERY_S, one proof: OSSY and G4 review the newest one nobody reviewed. Off with FEELESS_REVIEW=0."""
    rs = _rs()
    await rs.asyncio.sleep(45)
    while True:
        try:
            st_ = rs._load()
            if not rs._REVIEW_LESSONS:
                rs._REVIEW_LESSONS.update({k: rs._review.lessons(st_, k) for k in rs._mission.KINDS})
            await rs._review_one(st_)
        except Exception as e:   # noqa: BLE001
            print(f'[review] {type(e).__name__}: {str(e)[:120]}')
        try:   # 📌 COL-20 P3: once a UTC day, keep the proof record's chain tip outside the database
            if await rs.asyncio.to_thread(rs._pev.anchor, rs.DATA_DIR / rs._pev.DB_NAME, rs.DATA_DIR / rs._pev.ANCHORS):
                rs._VALUE['at'] = 0
        except Exception as e:   # noqa: BLE001
            print(f'[anchor] {str(e)[:100]}')
        await rs.asyncio.sleep(rs.REVIEW_EVERY_S)


async def _kit_fresh_loop():
    """🧰♻️ Saved pins first (so a restart never goes back to stale), then once a day: npm → smoke test in a headless browser → move or roll back."""
    rs = _rs()
    try:
        n_ = rs._kfresh.apply(rs._kits.KIT_USE, rs._kfresh.load(rs.KITS_DIR))
        print(f'[kits] fresh pins applied: {n_}')
    except Exception as e:   # noqa: BLE001
        print(f'[kits] apply: {str(e)[:100]}')
    await rs.asyncio.sleep(120)
    while True:
        try:
            if rs.time.time() - float(rs._kfresh.load(rs.KITS_DIR).get('checkedAt') or 0) >= rs._kfresh.CHECK_EVERY_S:
                ch_ = rs._fb.chromium_path()
                async def smoke_(html, expr): return await rs.asyncio.wait_for(rs._kfresh.browser_smoke(ch_, html, expr), 60)
                async with rs.httpx.AsyncClient(timeout=20) as h_:
                    rows_ = await rs._kfresh.run(h_, rs._kits.KIT_USE, rs.KITS_DIR, smoke_)
                print(f'[kits] fresh pass: {[(r["kit"], r["from"], r["to"], r["ok"]) for r in rows_]}')
        except Exception as e:   # noqa: BLE001: a failed pass changes nothing
            print(f'[kits] fresh: {type(e).__name__}: {str(e)[:100]}')
        await rs.asyncio.sleep(3600)


async def _pow2_relink_once(delay=30):
    """🧾 COL-25 at start: chain reads happen on a copy; only the fixed folders' fields go onto a FRESH store, saved at once (never a stale overwrite)."""
    rs = _rs()
    await rs.asyncio.sleep(delay)
    try:
        copy_ = rs._load()
        if not await rs._pow2_relink(copy_):
            return
        fresh = rs._load(); n = 0; keys_ = ('pid', 'sellPid', 'buySig', 'sellSig', 'settlementVerified', 'netPnlSol', 'cashSpentSol', 'cashReturnedSol', 'sigsFrom', 'pnlSol', 'pnlPct')
        for cid, c in copy_['cats'].items():
            got = {f['id']: f for f in c.get('powFolders') or [] if f.get('settlementVerified') and f.get('sigsFrom')}
            for f in (fresh['cats'].get(cid) or {}).get('powFolders') or []:
                if f.get('id') in got and not f.get('settlementVerified'):
                    f.update({k: got[f['id']].get(k) for k in keys_}); n += 1
        if n:
            rs._save(fresh); print(f'[pow2] {n} real PoW folders read back from the chain (COL-25)')
    except Exception as e:   # noqa: BLE001: a read that fails just waits for the next start
        print(f'[pow2] relink skipped: {type(e).__name__}: {str(e)[:100]}')


def heal_thinking(cat):
    """🧠 Notes filed before the thinking filter: any cloud or mind note that is a model's private thinking comes off. → True if any did."""
    rs = _rs()
    b_ = cat.get('brainsCfg') or {}; hit_ = False
    if b_.get('cloud') and len(rs._cp.no_thinking(b_['cloud'])) != len(b_['cloud']):
        b_['cloud'] = rs._cp.no_thinking(b_['cloud']); hit_ = True
    for m_, v_ in list((b_.get('minds') or {}).items()):
        if len(rs._cp.no_thinking(v_)) != len(v_ or []):
            b_['minds'][m_] = rs._cp.no_thinking(v_); hit_ = True
    for f_ in cat.get('pobFolders') or []:   # a PoB's browse note was the same leak
        for v_ in (f_.get('browsed') or {}).values():
            if isinstance(v_, dict) and rs._cp.thinking_leak(v_.get('note')):
                v_['note'] = 'Its window gave no readable note.'; hit_ = True
    return hit_


def _drop_nexa(store):
    """🪟→🧠 (owner 2026-10-31: NEXA retired — free cloud models beat her): a cat still pointed at her goes back to its own engine + its brains."""
    n = 0
    for c in (store.get('cats') or {}).values():
        if str(c.get('modelBrain') or '').lower() == 'nexa' or str(c.get('brain') or '').lower() == 'nexa':
            c.pop('modelBrain', None); c['brain'] = 'rules'; c['brainLabel'] = 'FeeCat AI' if c.get('isLeader') else 'Rule engine'
            c['brainProfile'] = {**(c.get('brainProfile') or {}), 'status': 'live', 'available': True}
            n += 1
    return n


def clean_look(x):
    """🐆 A cat's look: listed options only + a ≤ 12-char name tag (letters, digits, space . $ - _). Pure look, the engine never reads it."""
    rs = _rs()
    x = x if isinstance(x, dict) else {}
    out = {k: (x.get(k) if x.get(k) in opts else opts[0 if k != 'aura' else 1]) for k, opts in rs.LOOK_OPTIONS.items()}
    out['tag'] = rs.re.sub(r'[^\w .$-]', '', str(x.get('tag') or ''))[:12]
    return out


async def _model_limit(session=''):
    rs = _rs()
    try:
        async with rs.httpx.AsyncClient(timeout=5) as h:
            r = await h.post('http://127.0.0.1:5077/api/reputation/cats/model-limit', json={'session': session})
        if r.status_code == 200:
            return max(1, min(8, int(r.json()['maxModels'])))
    except Exception:
        pass
    return 2


def agent_wallets(store):
    """🚫 every AI agent's own wallet address (owner 2026-10-31: agents never launch a coin or make an agent ON FEELESS)."""
    return {str((c.get('agentWallet') or {}).get('address')) for c in (store.get('cats') or {}).values() if (c.get('agentWallet') or {}).get('address')}


def _session_wallet(session):
    """The wallet behind a signed chat session (the same check every cat action uses), or ''."""
    rs = _rs()
    try:
        return str(rs._real.session_wallet(rs._real.load_sessions(rs.DATA_DIR / 'chat_sessions.json'), session) or '') if session else ''
    except Exception:
        return ''


def _fresh_session_wallet(session, now=None):
    """The wallet behind a session signed in the last 24 h, or ''."""
    rs = _rs()
    try:
        rec = ((rs._real.load_sessions(rs.DATA_DIR / 'chat_sessions.json') or {}).get('s') or {}).get(rs.hashlib.sha256(str(session).encode()).hexdigest()) if session else None
    except Exception:
        rec = None
    now = now or rs.time.time()
    if not rec or now > float(rec.get('exp') or 0) or now - (float(rec.get('exp') or 0) - rs.SESSION_TTL_S) > rs.OWNER_FRESH_S:
        return ''
    return str(rec.get('address') or '')


def share_message(cat_id, pct, ts):
    """🤝 What the owner signs to let its agent send pct % of each winning trade's profit to the colony wallet (opportunity 2)."""
    return f"FEELESS auto-collect\nSend this % of each winning proof of +50% or more to the Pool\nagent:{cat_id}\npct:{int(pct or 0)}\nts:{int(ts or 0)}"


def share_ok(cat_id, pct, ts, sig, wallet, now=None):
    rs = _rs()
    if not (sig and wallet and ts) or abs((now or rs.time.time()) - int(ts)) > 120:
        return False
    try:
        import hq_auth
        return bool(hq_auth.verify_wallet(wallet, rs.share_message(cat_id, pct, ts), sig))
    except Exception:
        return False


def reveal_message(cat_id, site, ts):
    rs = _rs()
    return f"FEELESS reveal\nagent:{cat_id}\nsite:{rs._cv.site_of(site)}\nts:{int(ts or 0)}"


def reveal_ok(cat_id, site, ts, sig, wallet, now=None):
    """A reveal signed by the owner wallet in the last 2 minutes."""
    rs = _rs()
    if not (sig and wallet and ts) or abs((now or rs.time.time()) - int(ts)) > 120:
        return False
    try:
        import hq_auth
        return bool(hq_auth.verify_wallet(wallet, rs.reveal_message(cat_id, site, ts), sig))
    except Exception:
        return False


def last_money(events, cat_id):
    """💵 The last money it made or lost (a closed trade's P&L, fees apart) — the desk shows it until a newer one lands. Pure."""
    e = next((x for x in events if x.get('catId') == cat_id and x.get('pnlSol') is not None), None)   # events are newest first
    return {'sol': round(float(e['pnlSol']), 6), 'at': round(float(e.get('ts') or 0) / 1000), 'what': str(e.get('type') or 'trade').lower()} if e else None


def vault_log(cat, what, site):
    """🔐 The vault's audit trail the owner sees: saved / used / revealed / forgot, which site, when — never a value."""
    rs = _rs()
    cat['vaultLog'] = (list(cat.get('vaultLog') or []) + [{'what': what, 'site': rs._cv.site_of(site or ''), 'at': round(rs.time.time())}])[-40:]


def owner_wallet(cat):
    """🔒 The wallet that owns an agent: set on create / first signed visit (its agent wallet's signer for older ones), or ''."""
    return str(cat.get('ownerWallet') or (cat.get('agentWallet') or {}).get('owner') or '')


def owner_check(cat, signed, owner_id=''):
    """🔒 Owner = the SIGNED-IN WALLET, never a browser id (owner 2026-10-30: signed out, refreshed, still chatted with and drove the agent).
    'ok' · 'claim' (an older agent with no owner wallet: its creating browser + a signed wallet takes it once) · 'signin' · 'no'. Pure (tests)."""
    rs = _rs()
    import hmac as _hm
    if not signed:
        return 'signin'
    ow = rs.owner_wallet(cat)
    if ow:
        return 'ok' if _hm.compare_digest(ow, str(signed)) else 'no'
    return 'claim' if owner_id and _hm.compare_digest(str(owner_id), str(cat.get('ownerId') or '')) else 'no'


def _owner_gate(store, cat, session, owner_id='', what='work with it'):
    """Every owner door: 401 signed out, 403 not yours; a legacy agent is claimed by the signed wallet on the spot."""
    rs = _rs()
    signed = rs._fresh_session_wallet(session or '')
    verdict = rs.owner_check(cat, signed, owner_id)
    if verdict == 'signin':
        raise rs.HTTPException(401, 'Sign in with your wallet (one signature, no transaction) — agent controls need a sign-in from the last 24 h.')
    if verdict == 'no':
        raise rs.HTTPException(403, f"Only this agent's owner can {what}.")
    if verdict == 'claim':
        cat['ownerWallet'] = signed
        rs.keep_owned(cat); rs._save(store)
    return signed


async def _session_staff(session=''):
    """🧪 The paper rule trader is a STAFF test door (owner 2026-10-30, D1): users only ever launch real Trading / General agents.
    Staff = reputation's `_is_staff` on the signed chat session (any linked wallet); no session or reputation down ⇒ not staff."""
    rs = _rs()
    if not session:
        return False
    try:
        async with rs.httpx.AsyncClient(timeout=5) as h:
            r = await h.post('http://127.0.0.1:5077/api/reputation/cats/model-limit', json={'session': session})
        return bool(r.status_code == 200 and r.json().get('staff'))
    except Exception:
        return False


def supply_state(store):
    """🎟 Slots: `open` (what the owner opened, ≤ SUPPLY_MAX) · `taken` (users' live agents — staff agents never count) · `left`."""
    rs = _rs()
    try:
        opened = int((rs.json.loads((rs.DATA_DIR / rs.SUPPLY_FILE).read_text()) or {}).get('open', rs.SUPPLY_MAX))
    except (OSError, ValueError, TypeError):
        opened = rs.SUPPLY_MAX
    opened = max(0, min(rs.SUPPLY_MAX, opened))
    taken = sum(1 for c in (store.get('cats') or {}).values() if c.get('brainsCfg') and not c.get('revoked') and not c.get('ownerStaff') and not c.get('isLeader'))
    return {'open': opened, 'taken': taken, 'left': max(0, opened - taken), 'max': rs.SUPPLY_MAX}


def agent_max(staff):
    rs = _rs()
    return rs.STAFF_AGENT_MAX if staff else rs.AGENT_MAX


@router.post('/api/cats')
async def create_cat(payload: _RSM.CreatePayload):
    rs = _rs()
    store = rs._load()
    signed_ = rs._session_wallet(payload.session or '')
    if not signed_:   # 🔒 an agent belongs to a wallet from its first second
        raise rs.HTTPException(401, 'Sign in with your wallet first (one signature, no transaction).')
    staff_ = await rs._session_staff(payload.session or ''); max_ = rs.agent_max(staff_)
    if sum(1 for c in store['cats'].values() if (rs.owner_wallet(c) == signed_ or c.get('ownerId') == payload.ownerId) and not c.get('revoked')) >= max_:
        raise rs.HTTPException(400, f'You run {max_} agents — retire one to start another.')
    if not staff_ and payload.brains and rs.supply_state(store)['left'] <= 0:   # 🎟 every open slot is taken — the owner opens more in the command center
        raise rs.HTTPException(409, 'Every agent slot is taken right now — new slots open soon. Check back on the FeeCats page.')
    if rs._session_wallet(payload.session or '') in rs.agent_wallets(store):   # 🚫 an agent's own wallet never makes another agent on FEELESS
        raise rs.HTTPException(403, 'An AI agent never creates another agent on FEELESS.')
    if not payload.brains and not await rs._session_staff(payload.session or ''):
        raise rs.HTTPException(403, 'The paper test is staff only — launch a Trading or General agent.')
    cat_id = rs.uuid.uuid4().hex
    now = rs.time.time()
    cat = {
        **({'face': {'id': rs._face.clean_id(payload.face), 'at': round(rs.time.time())}} if rs._face.clean_id(payload.face) else {}),
        'id': cat_id, 'ownerId': payload.ownerId, 'ownerWallet': signed_, 'ownerStaff': bool(staff_), 'name': payload.name, 'handle': payload.handle,
        'avatar': payload.avatar, 'brain': rs.RULE_ENGINE['id'], 'brainLabel': rs.RULE_ENGINE['label'],
        'brainProfile': {'provider': rs.RULE_ENGINE['provider'], 'status': 'live', 'available': False, 'estimatedTokenCostUsd': 0},
        'strategy': payload.strategy, 'strategyLabel': rs.STRATEGY_LABELS.get(payload.strategy, 'Momentum'),
        'status': 'stopped', 'level': 1, 'xp': 0, 'wallet': 'paper',
        'balanceSol': float(payload.startingBalanceSol or 10), 'realizedPnlSol': 0, 'totalPnlSol': 0,
        'volumeSol': 0, 'wins': 0, 'losses': 0, 'winRate': None, 'positions': [], 'pnlHistory': [{'value': 0}],
        'risk': {
            'maxPositionSol': float(payload.maxPositionSol or 0.25), 'maxDailyLossSol': float(payload.maxDailyLossSol or 0.5),
            'allowlist': [s.strip() for s in (payload.allowlist or '').split(',') if s.strip()],
            'blocklist': [s.strip() for s in (payload.blocklist or '').split(',') if s.strip()],
        },
        'revoked': False, 'createdAt': now, 'lastTick': now, 'engine': rs.ENGINE_VERSION,
        'startingBalanceSol': float(payload.startingBalanceSol or 10), 'look': rs.clean_look(payload.look),
    }
    if payload.brains:
        cat_ = await rs._or_models()
        ids_ = {m['id'] for m in cat_.get('models') or []}
        try:
            cat['brainsCfg'] = rs._lc.clean(payload.model_dump(), None, ids_ or None, max_models=await rs._model_limit(payload.session or ''))
            cat['job'] = payload.job if payload.brainKind == 'general' else 'trading'
            cat['tools'] = rs._cp.toolkit(cat['job'], payload.tools)
            if payload.brainKind != 'general':
                cat['venues'] = rs._ck.venues(payload.venues)   # 📈 FEELESS rails only (trench · perps)
            else:
                cat['workMode'] = payload.workMode if payload.workMode in rs._ca.MODES else 'plan'
                if payload.taskCap: cat['taskCap'] = max(0.005, min(rs._task_cap_max(), float(payload.taskCap)))
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        for model, effort in cat['brainsCfg'].get('efforts', {}).items():
            row = next((m for m in cat_.get('models', []) if m['id'] == model), {})
            if effort not in row.get('efforts', []):
                raise rs.HTTPException(400, 'That model does not expose the selected effort level.')
        cat['brainsCfg']['knobs'] = rs._model_knobs_clean(cat_, cat['brainsCfg'].get('knobs'))   # 🎛 only what each model supports, each clamped
        cat['brainLabel'] = ' + '.join(x.split('/')[-1] for x in cat['brainsCfg']['brains'])
        cat['brainProfile'] = {'provider': 'OpenRouter', 'status': 'live' if rs._brains_live() else 'calls off', 'available': rs._brains_live(), 'estimatedTokenCostUsd': 0}
    store['cats'][cat_id] = cat
    rs._NEW_CATS[(str(rs.STORE_PATH), cat_id)] = rs.json.loads(rs.json.dumps(cat))
    rs._save(store)
    return {'cat': {**rs._no_keys(cat), 'mine': True}}   # (a random "recovery key" used to ride here — it unlocked nothing; the wallet's safe-keeping is SafeKeeping on the desk)


@router.get('/api/cats')
async def list_cats(ownerId: str = '', session: str = ''):
    """My agents = the signed-in wallet's (plus this browser's older unclaimed ones, so they can be claimed). Signed out ⇒ none."""
    rs = _rs()
    store = rs._load()
    signed = rs._fresh_session_wallet(session)
    cats = [c for c in store['cats'].values() if signed and rs.owner_check(c, signed, ownerId) in ('ok', 'claim')]
    max_ = rs.agent_max(await rs._session_staff(session)) if signed else rs.AGENT_MAX
    cats.sort(key=lambda c: -c['createdAt'])
    return {'cats': [{**x, 'mine': True} for x in rs._no_keys(cats)], 'max': max_}


def _apply_overrides(store):
    rs = _rs()
    for k, v in (store.get('rulesOverride') or {}).items():
        if k in rs.TUNABLE:  # clamp: settings saved under an older engine may sit outside today's safe range
            lo, hi = rs.TUNABLE[k]
            rs.RULES[k] = type(rs.RULES[k])(max(lo, min(hi, float(v))))


# 🎭 FEE IN PROMPT STUDIO (owner 2026-10-31: HQ › Fee › Prompts, "prompts that strengthen themselves — I approve each"): her closed exits → the
# same record, diagnosis and four mindsets G4 / OSSY get (prompt_studio.py). AUTO-TUNED is rewritten from her latest record on every read; only
# the owner's Apply puts a version on (no auto switch for Fee). The applied text rides every brain call as YOUR MINDSET (launch_cat.ask_messages).
def _studio_trades(cat):
    """Her closed exits → [{pct, peak, heldMin, at = when the trade OPENED}] (older exits carry no hold / peak: those stay None)."""
    out = []
    for e in cat.get('exits', []):
        if e.get('changeAtExit') is None or not e.get('exitAt'):
            continue
        out.append({'pct': e['changeAtExit'], 'peak': e.get('peak'), 'heldMin': e.get('heldMin'), 'after': e.get('peakAfter'), 'usd': None, 'at': e['exitAt'] - 60 * (e.get('heldMin') or 0)})
    return sorted(out, key=lambda t: t['at'])

