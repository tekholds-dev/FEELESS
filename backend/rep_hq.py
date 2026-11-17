"""🧹 FEELESS HQ — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401


def _rs():
    import reputation_service
    return reputation_service


def _admin_wallets():
    rs = _rs()
    try:
        granted = rs._hq_auth.granted_wallets(rs._json_load(rs.DATA_DIR / 'roles.json', {'grants': {}})['grants'])
    except Exception:
        granted = []
    return rs._hq_auth.owner_wallets(rs.os.environ.get('FEELESS_ADMIN_WALLETS', '')) + granted


def _admin_load():
    rs = _rs()
    try:
        d = rs._cached_json(rs.ADMIN_PATH)
    except Exception:
        d = {}
    d.setdefault('badges', {}); d.setdefault('airdrops', []); d.setdefault('audit', [])
    return d


def _badge_limits():
    rs = _rs()
    raw = rs._admin_load().get('badgeLimits') or {}
    return {'profile': max(0, min(12, int(raw.get('profile', 3)))),
            'chat': max(0, min(12, int(raw.get('chat', 3))))}


def _admin_save(d):
    rs = _rs()
    rs.ADMIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = rs.ADMIN_PATH.with_suffix('.tmp'); tmp.write_text(rs.json.dumps(d)); tmp.replace(rs.ADMIN_PATH)


def _cached_json(path):
    """Parse a JSON store once per on-disk version (mtime+size). Hot endpoints read these on every
    request; re-parsing multi-MB files each time is what would melt under thousands of users."""
    rs = _rs()
    st = path.stat()
    key = (st.st_mtime_ns, st.st_size)
    hit = rs._parse_cache.get(str(path))
    if hit and hit[0] == key:
        return hit[1]
    t0 = rs.time.perf_counter()
    obj = rs.json.loads(path.read_text())
    rs._json_cost_note('load', path, t0)
    rs._parse_cache[str(path)] = (key, obj)
    return obj


def _json_cost_note(kind, path, t0):
    rs = _rs()
    c = rs._json_cost.setdefault(f'{kind}:{path.name}', [0, 0.0])
    c[0] += 1; c[1] += rs.time.perf_counter() - t0


def _json_load(path, default):
    rs = _rs()
    try:
        obj = rs._cached_json(path)
    except Exception:
        return default
    if isinstance(obj, dict) and 'paths' not in obj and str(path) == str(rs.RUNNERS_PATH):   # 🗂 runners.json's price paths come from their own store
        obj['paths'] = rs._paths_mem.get()
    return obj


def _json_save(path, d):
    rs = _rs()
    t0 = rs.time.perf_counter()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = d
    if isinstance(d, dict) and 'paths' in d and str(path) == str(rs.RUNNERS_PATH):   # 🗂 the runner price paths (1.8 MB of a 3 MB file) live in memory + their own file, written ≤ 1/min
        rs._paths_mem.put(d['paths'], rs.time.time())
        body = {k: v for k, v in d.items() if k != 'paths'}
    tmp = path.with_suffix('.tmp'); tmp.write_text(rs.json.dumps(body)); tmp.replace(path)
    if isinstance(d, dict):   # ⚡ what was written IS the current version: the next load reads it, never re-parses it (fuse_hq.json: 178 re-parses in 7 min)
        st = path.stat(); rs._parse_cache[str(path)] = ((st.st_mtime_ns, st.st_size), d)
    rs._json_cost_note('save', path, t0)


def _json_save_soft(path, d):
    """For a worker thread and a BIG store nobody mutates meanwhile: the pure-Python encoder yields the GIL between chunks, so the
    event loop keeps answering (json.dumps holds it for the whole document: 0.46s for 31 MB)."""
    rs = _rs()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        for chunk in rs.json.JSONEncoder().iterencode(d):
            f.write(chunk)
    tmp.replace(path)


def _guard_save():
    rs = _rs()
    s = rs._guard_s()
    rs._json_save(rs.GUARD_PATH, {k: s[k] for k in ('suspects', 'blocks', 'log')})


def _def_save(force=False):
    rs = _rs()
    now = rs.time.time()
    if force or now - rs._def_dirty['at'] > 15:   # an attack burst writes the file at most every 15s
        rs._def_dirty['at'] = now
        s = rs._def_s(); rs._def.prune(s, now)
        rs._json_save(rs.DEF_PATH, {k: s[k] for k in ('blocks', 'rules', 'incidents', 'uaHits')})


def _war_save(force=False):
    rs = _rs()
    now = rs.time.time()
    if force or now - rs._war_dirty['at'] > 15:
        rs._war_dirty['at'] = now
        s = rs._war_s(); rs._war.prune(s, now)
        rs._json_save(rs.WAR_PATH, {k: s[k] for k in ('seq', 'events', 'captures', 'canaries', 'hits', 'nets', 'netSeen', 'sigs', 'revoked', 'reports', 'moves')})


def _role_of(addr):
    rs = _rs()
    return rs._hq_auth.role_of(addr, rs._owner_wallets(), rs._json_load(rs.DATA_DIR / 'roles.json', {'grants': {}})['grants'])


def _role_gate(addr, request):
    rs = _rs()
    role = rs._role_of(addr)
    rs._hq_auth.check_role(role, getattr(getattr(request, 'url', None), 'path', ''), getattr(request, 'method', 'GET'))


def _audit(d, admin, action, detail):
    rs = _rs()
    d['audit'].append({'at': rs.time.time(), 'admin': admin, 'action': action, 'detail': detail})
    d['audit'] = d['audit'][-300:]


async def _token_holders(mint: str):
    rs = _rs()
    hit = rs._holder_cache.get(mint)
    if hit and rs.time.time() - hit[0] < 120:
        return hit[1]
    owners = {}
    accounts = {}
    async with rs.httpx.AsyncClient(timeout=40) as http:
        for program in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
            filters = [{'memcmp': {'offset': 0, 'bytes': mint}}]
            if program.startswith('Tokenkeg'):
                filters.insert(0, {'dataSize': 165})
            try:
                accts = await rs._rpc(http, 'getProgramAccounts', [program, {'encoding': 'jsonParsed', 'filters': filters}])
            except Exception:
                accts = None
            for a in accts or []:
                info = rs._parsed_info(a.get('account'))
                amt = float(((info.get('tokenAmount') or {}).get('uiAmount')) or 0)
                if amt > 0 and info.get('owner'):
                    owners[info['owner']] = owners.get(info['owner'], 0) + amt
                    if amt > accounts.get(info['owner'], ('', 0))[1]:
                        accounts[info['owner']] = (a.get('pubkey'), amt)
            if owners:
                break
    price = None
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            price = float(((await http.get(f'https://lite-api.jup.ag/price/v3?ids={mint}')).json().get(mint) or {}).get('usdPrice') or 0) or None
    except Exception:
        pass
    total = sum(owners.values()) or 1
    rows = sorted(({'owner': o, 'amount': v, 'pct': v / total * 100, 'usd': v * price if price else None, 'tokenAccount': accounts.get(o, (None,))[0]} for o, v in owners.items()), key=lambda r: -r['amount'])
    out = {'mint': mint, 'price': price, 'holders': len(rows), 'rows': rows, 'at': rs.time.time()}
    rs._holder_cache[mint] = (rs.time.time(), out)
    return out


def _bug_key(text, page):
    """Crash identity: the message + the component that threw (stack frames / hot-update hashes dropped) + the page path."""
    rs = _rs()
    t = rs._re.sub(r'\s+·\s+at .*$', '', str(text or '').strip())
    t = rs._re.sub(r'[0-9a-f]{12,}', '#', t)
    return f"{t[:300]}|{str(page or '').split('?')[0]}"


def _bug_seen(b):
    """When a bug report last fired, in seconds (reports carry ms or s)."""
    x = float(b.get('lastAt') or b.get('at') or 0)
    return x / 1000 if x > 1e12 else x


def _street_fams():
    """wallet → its family's street look {id, tag, color, badge, don} — badge_view once per family per read."""
    rs = _rs()
    import crews as _cr
    st_ = rs._json_load(rs.CREWS_PATH, {}) or {}
    cache_ = {}

    def fam(addr):
        c_ = _cr.crew_of(st_, rs.primary_of(addr)) or _cr.crew_of(st_, addr)
        if not c_:
            return None
        if c_['id'] not in cache_:
            b_ = _cr.badge_view(c_, st_.get('awards'), rs._crew_cfg(), rs._is_staff(c_.get('owner')))
            cache_[c_['id']] = {'id': c_['id'], 'tag': c_.get('tag'), 'name': c_.get('name'), 'color': b_.get('c1'), 'badge': b_, 'owner': c_.get('owner')}
        f_ = cache_[c_['id']]
        return {k_: v_ for k_, v_ in f_.items() if k_ != 'owner'} | {'don': rs.primary_of(addr) == rs.primary_of(f_.get('owner') or '')}
    return fam


def _legal_save():
    rs = _rs()
    s = rs._legal_s(); rs._json_save(rs.LEGAL_PATH, {k: s[k] for k in ('accept', 'cfg', 'requests')})


def _legal_me(wallet, session, fresh=False):
    """The signed wallet (its primary). fresh=True: signed in within the last 24 h (a delete can't ride a week-old session)."""
    rs = _rs()
    me = rs._session_or_401(wallet, session)
    if fresh:
        rec = rs._sess()['s'].get(rs.hashlib.sha256((session or '').encode()).hexdigest()) or {}
        if rec.get('exp', 0) - rs.SESSION_TTL < rs.time.time() - 86400:
            raise rs.HTTPException(401, 'Sign in again first (a delete needs a sign-in from the last 24 hours).')
    return me


def _legal_hold(wallet, feature, request=None):
    """⚖ LEGAL-1 (d): refuse a money route for a wallet the legal gate holds, so a direct API call can't skip the browser's check. Exits
    never come here (callers skip them). Agent wallets (FEELESS-made, gated when their owner funded them) pass."""
    rs = _rs()
    w_ = str(wallet or '')
    if not w_:
        return
    why_ = rs._legal.hold(rs._legal_s(), feature, rs.primary_of(w_), rs._legal.country_of(request.headers) if request is not None else None)
    if why_ and w_ not in rs._any_agent_wallets():   # the agents store is read only when the answer would refuse
        raise rs.HTTPException(403, why_)


def _legal_parts(me):
    """Every off-chain store holding this wallet's rows (read-only). Secrets are scrubbed later by legal.scrub."""
    rs = _rs()
    def own(a):
        return bool(a) and rs.primary_of(str(a)) == me
    subs = (rs._push_load().get('subs') or {}).values()
    return {
        'profile': rs._prof().get(me),
        'follows': (rs._fol().get('following') or {}).get(me),
        'notifications': rs._notif().get(me),
        'push': [{'watch': v.get('watch'), 'prefs': v.get('prefs')} for v in subs if own((v.get('prefs') or {}).get('address'))],
        'dmPrefs': rs._json_load(rs.DM_PREFS_PATH, {}).get(me),
        'identities': {a: v for a, v in (rs._ids().get('links') or {}).items() if (v or {}).get('primary') == me and a != me},
        'dms': [m for th in rs._json_load(rs.DM_PATH, {}).values() if isinstance(th, list) for m in th if me in (m.get('from'), m.get('to'))][-2000:],
        'chat': [m for msgs in (rs._chat_load().get('rooms') or {}).values() if isinstance(msgs, list) for m in msgs
                 if m.get('identity') == me or own(m.get('address'))][-2000:],
        'sessions': {'signedIn': sum(1 for v in (rs._sess().get('s') or {}).values() if own(v.get('address')))},
        'consent': (rs._legal_s().get('accept') or {}).get(me),
        'receipts': [r for r in rs._receipt_rows() if isinstance(r, list) and len(r) > 2 and own(r[2])][-2000:],
        'points': rs._pts().get(me),
        'quests': rs._qs().get(me),
        'referrals': {'invited': (rs._json_load(rs.REF_PATH, {'by': {}}).get('by') or {}).get(me)},
    }


async def _legal_wipe(me):
    """Delete the personal / social rows (legal.DELETE). Sessions + push go first: they're matched through linked accounts."""
    rs = _rs()
    def own(a):
        return bool(a) and rs.primary_of(str(a)) == me
    n = {}
    async with rs._admin_lock:
        d = rs._sess(); s_ = d.get('s') or {}
        gone = [t for t, v in s_.items() if own(v.get('address'))]
        for t in gone:
            s_.pop(t, None)
        n['sessions'] = len(gone); rs._json_save(rs.SESSIONS_PATH, d)
        d = rs._push_load(); subs = d.get('subs') or {}
        gone = [sid for sid, v in subs.items() if own(((v or {}).get('prefs') or {}).get('address'))]
        for sid in gone:
            subs.pop(sid, None)
        n['push'] = len(gone); rs._push_save(d)
        d = rs._fol(); n['follows'] = len((d.get('following') or {}).pop(me, None) or []); rs._json_save(rs.FOLLOW_PATH, d)
        import sql_store as _sqls
        n['notifications'] = len(rs._notif().update(me, lambda box: _sqls.Result(None, box or [])) or [])
        d = rs._json_load(rs.DM_PREFS_PATH, {}); n['dmPrefs'] = 0 if d.pop(me, None) is None else 1; rs._json_save(rs.DM_PREFS_PATH, d)
        d = rs._json_load(rs.DM_PATH, {}); k_ = 0
        for key, th in list(d.items()):
            if not isinstance(th, list):
                continue
            keep = [m for m in th if m.get('from') != me]
            k_ += len(th) - len(keep)
            if keep:
                d[key] = keep
            else:
                d.pop(key, None)
        n['dms'] = k_; rs._json_save(rs.DM_PATH, d)
        d = rs._ids(); links = d.get('links') or {}
        gone = [a for a, v in links.items() if (v or {}).get('primary') == me]
        for a in gone:
            links.pop(a, None)
        n['identities'] = len([a for a in gone if a != me]); rs._json_save(rs.IDENTITY_PATH, d)
    async with rs._chat_lock:
        d = rs._chat_load(); k_ = 0
        for room, msgs in list((d.get('rooms') or {}).items()):
            if not isinstance(msgs, list):
                continue
            keep = [m for m in msgs if not (m.get('identity') == me or m.get('address') == me)]
            k_ += len(msgs) - len(keep)
            d['rooms'][room] = keep
        n['chat'] = k_; rs.CHAT_PATH.write_text(rs.json.dumps(d))
    had = rs._prof().get(me) is not None
    rs._prof().update(me, lambda _old: None)
    n['profile'] = 1 if had else 0
    return n


def _guard_s():
    """Counters live in memory; suspects, approved blocks and the decision log persist (guard.json)."""
    rs = _rs()
    if rs._guard_state is None:
        rs._guard_state = rs._guard.new_state()
        saved = rs._json_load(rs.GUARD_PATH, {})
        for k in ('suspects', 'blocks', 'log'):
            if isinstance(saved.get(k), type(rs._guard_state[k])):
                rs._guard_state[k] = saved[k]
    return rs._guard_state


def _def_s():
    rs = _rs()
    if rs._def_state is None:
        rs._def_state = rs._def.new_state()
        saved = rs._json_load(rs.DEF_PATH, {})
        for k in ('blocks', 'rules', 'incidents', 'uaHits'):
            if isinstance(saved.get(k), type(rs._def_state[k])):
                rs._def_state[k] = saved[k]
    return rs._def_state


def _war_s():
    rs = _rs()
    if rs._war_state is None:
        rs._war_state = rs._war.new_state()
        saved = rs._json_load(rs.WAR_PATH, {})
        for k in ('seq', 'events', 'captures', 'canaries', 'hits', 'nets', 'netSeen', 'sigs', 'revoked', 'reports', 'moves'):
            if k in saved and isinstance(saved[k], type(rs._war_state[k])):
                rs._war_state[k] = saved[k]
    return rs._war_state


def _require_admin(request: Request) -> str:
    """Session proof: the admin wallet signs `FEELESS HQ\\naddress:{a}\\nts:{ts}` (valid a day) — rules in hq_auth.py."""
    rs = _rs()
    addr = rs._hq_auth.check_session(request.headers.get('x-admin-address', ''), request.headers.get('x-admin-ts', ''),
                                  request.headers.get('x-admin-sig', ''), rs._admin_wallets(), rs._verify_wallet, rs.time.time())
    try:   # 🛡 the same HQ signature from a new fingerprint = a stolen session (flagged + tarpitted, the owner sees it in Security)
        ip_ = rs._guard.client_ip(request.headers, request.client.host if request.client else '', rs.os.environ.get('FEELESS_TRUST_PROXY') == '1')
        sig_ = request.headers.get('x-admin-sig', ''); ua_ = request.headers.get('user-agent', '')
        if rs._def.seen_sig(rs._def_s(), sig_, ip_, ua_, request.url.path):
            rs._def_save(force=True)
        if rs._war.note_sig(rs._war_s(), sig_, ip_, ua_):   # ⚔️ same HQ signature from a second device → revoke (owner re-signs)
            rs._war_save(force=True)
        if rs._war.sig_revoked(rs._war_s(), sig_):
            raise rs.HTTPException(401, 'This session was used from another device and has been revoked — sign in again.')
    except rs.HTTPException:
        raise
    except Exception:
        pass
    rs._role_gate(addr, request)
    return addr


def _legal_s():
    rs = _rs()
    if rs._legal_state is None:
        st = rs._legal.new_state(); saved = rs._json_load(rs.LEGAL_PATH, {})
        if isinstance(saved.get('accept'), dict):
            st['accept'] = saved['accept']
        if isinstance(saved.get('cfg'), dict):
            st['cfg'] = rs._legal.clean_cfg(saved['cfg'])
        if isinstance(saved.get('requests'), list):
            st['requests'] = saved['requests']
        rs._legal_state = st
    return rs._legal_state

