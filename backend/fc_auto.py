"""🧹 Site sessions, sign-in, agent-auto — split out of fc_desk.py by scripts/split-module.py (owner 2026-11-17 cleanup); first moved whole out of feecat_service.py.
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches feecat_service still
reaches it, and every function here is still reachable on feecat_service under its own name. Constants, classes and state live in the service."""
import feecat_service as _RSM  # noqa: E402,F401  (body models / annotations; this module is imported at the END of the service)
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401

router = APIRouter()


def _rs():
    import feecat_service
    return feecat_service


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

