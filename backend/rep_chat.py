"""🧹 Call ledger, chat, wallet profiles, blocklist, funder graph — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""



def _rs():
    import reputation_service
    return reputation_service


def _calls_load():
    rs = _rs()
    if rs.CALLS_PATH.exists():
        try:
            return rs._cached_json(rs.CALLS_PATH)  # parsed once per file version, not on every request
        except Exception:
            pass
    return {'calls': {}}


def _calls_save(d):
    rs = _rs()
    rs.CALLS_PATH.write_text(rs.json.dumps(d))


def _award_feed_call(c):
    # FEEd reputation: a post that turns into a real move pays its author once per milestone.
    rs = _rs()
    if not c['room'].startswith('feed-') or not c.get('callerAddress') or not c['priceAtCall']:
        return
    peak = c['peakPrice'] / c['priceAtCall']
    done = c.setdefault('awarded', [])
    for x, pts in rs.FEED_CALL_POINTS:
        if peak >= x and x not in done:
            done.append(x)
            rs.season_award(rs.primary_of(c['callerAddress']), pts, f"feed-call:{x}x:{c['symbol']}")
            rs.notify(c['callerAddress'], 'reward', f"📈 Your FEEd call on {c['symbol']} hit {x}× — +{pts} season points", f"/terminal/chat?chain={c['chain']}&pair={c['pairAddress']}")


def _record_feed_calls(msg):
    rs = _rs()
    async def run():
        async with rs._calls_lock:
            d = rs._calls_load()
            for t in msg['tokens']:
                p = t.get('pair') or {}
                price = float(p.get('priceUsd') or 0)
                if price <= 0:
                    continue
                cid = f"{msg['id']}:{t['pairAddress']}"
                d['calls'].setdefault(cid, {'id': cid, 'messageId': msg['id'], 'room': msg['room'], 'caller': msg['username'][:40], 'callerAddress': msg['address'],
                    'chain': t['chainId'], 'pairAddress': t['pairAddress'], 'mint': t['address'], 'symbol': t.get('symbol'),
                    'imageUrl': (p.get('info') or {}).get('imageUrl'), 'priceAtCall': price, 'mcAtCall': p.get('marketCap') or p.get('fdv'),
                    'at': rs.time.time(), 'lastPrice': price, 'peakPrice': price, 'checkedAt': rs.time.time()})
            rs._calls_save(d)
    rs.asyncio.create_task(run())


def _call_view(c):
    return {**c, 'x': c['lastPrice'] / c['priceAtCall'] if c['priceAtCall'] else None,
            'peakX': c['peakPrice'] / c['priceAtCall'] if c['priceAtCall'] else None}


async def _refresh_calls():
    rs = _rs()
    while True:
        try:
            d = rs._calls_load()
            by_chain = {}
            for c in d['calls'].values():
                if rs.time.time() - c['at'] < 30 * 86400:
                    by_chain.setdefault(c['chain'], set()).add(c['pairAddress'])
            live = {}
            async with rs.httpx.AsyncClient(timeout=10) as http:
                for chain, pairs in by_chain.items():
                    pairs = sorted(pairs)
                    for i in range(0, len(pairs), 30):
                        try:
                            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{",".join(pairs[i:i + 30])}')
                            for p in (r.json() or {}).get('pairs') or []:
                                live[p.get('pairAddress')] = float(p.get('priceUsd') or 0)
                        except Exception:
                            pass
            async with rs._calls_lock:
                d = rs._calls_load()
                for c in d['calls'].values():
                    px = live.get(c['pairAddress'])
                    if px:
                        c['lastPrice'] = px
                        c['peakPrice'] = max(c['peakPrice'], px)
                        c['checkedAt'] = rs.time.time()
                        if rs.time.time() - c['at'] < 3 * 86400:   # 📈 the receipt's mini chart (street coin cards draw it)
                            rs._stc.trail_add(c, px, rs.time.time())
                    rs._award_feed_call(c)
                rs._calls_save(d)
        except Exception as exc:
            print('calls refresh error', exc)
        await rs.asyncio.sleep(60)


def _build_caller_board(days, room):
    rs = _rs()
    since = rs.time.time() - days * 86400
    by = {}
    for c in rs._calls_load()['calls'].values():
        if c['at'] < since or (room and not c['room'].startswith(room)):
            continue
        v = rs._call_view(c)
        b = by.setdefault(c['caller'], {'caller': c['caller'], 'callerAddress': c.get('callerAddress'), 'calls': 0, 'hits': 0, 'rugs': 0, 'sumPeak': 0.0, 'best': None})
        b['calls'] += 1
        b['sumPeak'] += v['peakX'] or 1
        if (v['peakX'] or 0) >= 2:
            b['hits'] += 1
        if (v['x'] or 1) <= 0.3:
            b['rugs'] += 1
        if not b['best'] or (v['peakX'] or 0) > (b['best']['peakX'] or 0):
            b['best'] = {'symbol': v['symbol'], 'peakX': v['peakX'], 'pairAddress': v['pairAddress'], 'chain': v['chain']}
    rows = [{**b, 'hitRate': b['hits'] / b['calls'], 'avgPeakX': b['sumPeak'] / b['calls']} for b in by.values()]
    rows.sort(key=lambda r: (-r['hitRate'], -r['avgPeakX'], -r['calls']))
    return {'rows': rows[:50], 'days': days}


def _react_load():
    rs = _rs()
    if rs.REACT_PATH.exists():
        try:
            return rs._cached_json(rs.REACT_PATH)
        except Exception:
            pass
    return {'rooms': {}}


def _prof():
    """🗄 SITE-8: wallet profiles, one row per wallet in SQLite (profiles.db). A save changes ONE wallet in one transaction, so any number
    of workers can save at once and none wipes another's (the old whole-file write did). profiles.json moved in once and is kept read-only."""
    rs = _rs()
    import sql_store as _sqls
    k_ = str(rs.PROFILE_PATH)
    if k_ not in rs._prof_docs:
        rs._prof_docs[k_] = _sqls.Docs(rs.PROFILE_PATH, inner='profiles')
    return rs._prof_docs[k_]


def _profiles_load():
    """Read-only view {'profiles': {wallet: profile}} (cached until anybody writes). Never change it: write with _prof().update(wallet, fn)."""
    rs = _rs()
    try:
        return {'profiles': rs._prof().all()}
    except Exception:
        return {'profiles': {}}


def _safe_url(v, max_len=400):
    v = (v or '').strip()
    return v if (v.startswith('https://') or v.startswith('/api/reputation/uploads/')) and len(v) <= max_len else ''


def _clean_profile(p: dict) -> dict:
    rs = _rs()
    accent = str(p.get('accent') or '#00e9a0')
    accent = accent if accent.startswith('#') and len(accent) in (4, 7) and set(accent[1:]) <= rs.HEX else '#00e9a0'
    links = p.get('links') or {}
    top8 = []
    for t in (p.get('top8') or [])[:8]:
        if isinstance(t, dict) and t.get('pairAddress') and t.get('chain'):
            top8.append({'chain': str(t['chain'])[:20], 'pairAddress': str(t['pairAddress'])[:64], 'mint': str(t.get('mint') or '')[:64],
                         'symbol': str(t.get('symbol') or '')[:16], 'imageUrl': rs._safe_url(t.get('imageUrl'))})
    return {
        'displayName': str(p.get('displayName') or '')[:32], 'bio': str(p.get('bio') or '')[:280],
        'avatarUrl': rs._safe_url(p.get('avatarUrl')), 'bannerUrl': rs._safe_url(p.get('bannerUrl')), 'accent': accent,
        'mood': str(p.get('mood') or '')[:40],
        'links': {k: rs._safe_url(links.get(k)) for k in ('x', 'website', 'telegram') if rs._safe_url(links.get(k))},
        'top8': top8,
        'theme': p.get('theme') if p.get('theme') in rs.PROFILE_THEMES else 'grid',
        'friends': [str(f)[:44] for f in (p.get('friends') or [])[:8] if rs._re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', str(f))],
        'songs': [{'url': str(x.get('url'))[:300], 'title': str(x.get('title') or '')[:60]} for x in (p.get('songs') or [])[:15]
                  if isinstance(x, dict) and rs._re.match(r'^https://(www\.|m\.|music\.|open\.)?(youtube\.com|youtu\.be|spotify\.com|soundcloud\.com)/', str(x.get('url') or ''))],
        'handle': str(p.get('handle') or '').lower().lstrip('@')[:20] if rs._re.match(r'^@?[a-z0-9_]{3,20}$', str(p.get('handle') or '').lower()) else '',
        'ring': p.get('ring') if p.get('ring') in rs.RING_TIERS else 'none',
        'nameFx': p.get('nameFx') if p.get('nameFx') in rs.NAMEFX_TIERS else 'none',
        'featuredBadges': list(dict.fromkeys(str(b)[:40] for b in (p.get('featuredBadges') or []) if rs._re.match(r'^[a-z0-9-]{2,40}$', str(b))))[:rs._badge_limits()['profile']],
    }


def _verify_wallet(address: str, message: str, signature: str) -> bool:
    rs = _rs()
    if rs._re.match(r'^0x[0-9a-fA-F]{40}$', address or ''):
        return rs._verify_evm(address, message, signature)
    return rs._verify_solana(address, message, signature)


def _x_redirect():
    rs = _rs()
    return rs.os.getenv('X_REDIRECT_URI') or f"{(rs.os.getenv('PUBLIC_SITE_URL') or '').rstrip('/')}/api/reputation/x/oauth/callback"


def _protected_wallets():
    """FEELESS's own wallets can never be blocklisted (its launches buy in the mint slot by design)."""
    rs = _rs()
    extra = [a.strip() for a in rs.os.environ.get('FEELESS_PROTECTED_WALLETS', '').split(',') if a.strip()]
    return set(rs._owner_wallets()) | set(rs._admin_wallets()) | {rs.FEE_CREATOR_WALLET} | set(extra)


def _block_load():
    # ⚡ ONE filtered view per on-disk version: the runner board asks per creator, and rebuilding a 100K-wallet dict per row
    # blocked the event loop for up to 10s (loop_lag, 2026-10-12). Writers mutate the view, then write the file → a new version.
    rs = _rs()
    d = {'wallets': {}}; ver = None
    if rs.BLOCK_PATH.exists():
        try:
            d = rs._cached_json(rs.BLOCK_PATH); ver = rs._parse_cache[str(rs.BLOCK_PATH)][0]
        except Exception:
            ver = None
    safe = rs._protected_wallets()
    key = (ver, frozenset(safe))
    if ver is not None and rs._block_view['key'] == key:
        return rs._block_view['d']
    if rs._block_dirty['on'] and rs._block_view['d'] is not None:   # the view is being replaced: what it learned goes to disk first
        rs._block_flush(rs._block_view['d'])
        return rs._block_load()
    out = {**d, 'wallets': {w: r for w, r in (d.get('wallets') or {}).items() if w not in safe}}
    if ver is not None:
        rs._block_view.update(key=key, d=out)
    return out


def _block_flush(d=None):
    rs = _rs()
    d = d if d is not None else rs._block_view['d']
    if d is None:
        return
    t0 = rs.time.perf_counter()
    tmp = rs.BLOCK_PATH.with_suffix('.tmp'); tmp.write_text(rs.json.dumps(d)); tmp.replace(rs.BLOCK_PATH)
    st = rs.BLOCK_PATH.stat(); ver = (st.st_mtime_ns, st.st_size)
    rs._parse_cache[str(rs.BLOCK_PATH)] = (ver, d)   # what was written IS the current version: no 14 MB re-parse, no view rebuild
    rs._block_view.update(key=(ver, frozenset(rs._protected_wallets())), d=d)
    rs._block_dirty.update(on=False, at=rs.time.time())
    rs._json_cost_note('save', rs.BLOCK_PATH, t0)


def _block_save(d, now=False):
    """⚡ Strikes recorded by the scanner are written at most once a minute (each write was 14 MB serialized + parsed again on the event
    loop, several times a minute). The view in memory is the truth in between; a report by a person and a shutdown write at once."""
    rs = _rs()
    rs._block_dirty['on'] = True
    if now or d is not rs._block_view['d'] or rs.os.environ.get('PYTEST_CURRENT_TEST') or rs.time.time() - rs._block_dirty['at'] >= rs.BLOCK_SAVE_SEC:
        rs._block_flush(d)


def _is_blocked(rec):
    rs = _rs()
    if not rec:
        return False
    return bool(rec.get('reported')) or len(rec.get('mints', {})) >= rs.AUTO_BLOCK_STRIKES


async def _record_offenders(mint, bundled, snipers):
    rs = _rs()
    safe = rs._protected_wallets()
    bundled, snipers = [w for w in bundled if w not in safe], [w for w in snipers if w not in safe]
    if not bundled and not snipers:
        return
    async with rs._block_lock:
        d = rs._block_load()
        for role, wallets in (('bundler', bundled), ('sniper', snipers)):
            for w in wallets:
                rec = d['wallets'].setdefault(w, {'mints': {}, 'firstSeen': rs.time.time()})
                rec['mints'].setdefault(mint, role)
                rec['lastSeen'] = rs.time.time()
        rs._block_save(d)
    rs.asyncio.create_task(rs._trace_funders(mint, list(bundled) + list(snipers)))


def _funders_load():
    rs = _rs()
    return rs._json_load(rs.FUNDERS_PATH, {'funders': {}, 'offenderFunder': {}})


def _is_flagged_funder(rec):
    rs = _rs()
    if not rec:
        return False
    return len(rec.get('mints', {})) >= rs.FUNDER_STRIKE_MINTS or len(rec.get('funded', [])) >= rs.FUNDER_STRIKE_WALLETS


async def _trace_funders(mint, offenders):
    """Best-effort, capped, background: find who funded each new offender wallet's very first
    transaction, and remember it. A funder seen behind offenders on 2+ launches (or 3+ puppet
    wallets) gets flagged — and added to the blocklist itself — so their NEXT batch of fresh
    wallets is already suspect before they've sniped a single thing."""
    rs = _rs()
    todo = [w for w in offenders if w not in rs._funder_resolved][:8]
    if not todo:
        return
    for w in todo:
        rs._funder_resolved.add(w)
        try:
            funder = await rs.resolve_funding_source('solana', w)
        except Exception:
            funder = None
        if not funder or funder == w:
            continue
        async with rs._funder_lock:
            d = rs._funders_load()
            rec = d['funders'].setdefault(funder, {'mints': {}, 'funded': [], 'firstSeen': rs.time.time()})
            rec['mints'].setdefault(mint, True)
            if w not in rec['funded']:
                rec['funded'].append(w)
            rec['lastSeen'] = rs.time.time()
            d['offenderFunder'][w] = funder
            newly_flagged = rs._is_flagged_funder(rec) and funder not in (d.get('flagged') or [])
            if newly_flagged:
                d.setdefault('flagged', []).append(funder)
            rs._json_save(rs.FUNDERS_PATH, d)
        if newly_flagged:
            # The funder becomes a blocklist entry in their own right — 'funder' strikes count
            # exactly like sniping/bundling do, so they auto-block the same way.
            async with rs._block_lock:
                bl = rs._block_load()
                brec = bl['wallets'].setdefault(funder, {'mints': {}, 'firstSeen': rs.time.time()})
                for m in d['funders'][funder]['mints']:
                    brec['mints'].setdefault(m, 'funder')
                brec['lastSeen'] = rs.time.time()
                rs._block_save(bl)


def funder_lookup(wallet: str):
    """Is this wallet's funder already known to have bankrolled other snipe/bundle squads?"""
    rs = _rs()
    d = rs._funders_load()
    funder = d['offenderFunder'].get(wallet)
    if not funder:
        return None
    rec = d['funders'].get(funder) or {}
    if not rs._is_flagged_funder(rec):
        return None
    return {'funder': funder, 'otherLaunches': len(rec.get('mints', {})), 'walletsFunded': len(rec.get('funded', []))}


def _chat_load():
    rs = _rs()
    if rs.CHAT_PATH.exists():
        try:
            return rs._cached_json(rs.CHAT_PATH)
        except Exception:
            pass
    return {'rooms': {}, 'lastTs': {}}


def _display_name(address):
    rs = _rs()
    p = rs._profiles_load()['profiles'].get(address) or {}
    return p.get('displayName') or f'{address[:4]}…{address[-4:]}'


async def _room_mint(room: str):
    """coin-solana-<pairOrMint>-<side> → (mint, symbol); None for non-coin rooms."""
    rs = _rs()
    m = rs._re.match(r'^coin-solana-([1-9A-HJ-NP-Za-km-z]{32,44})-(bulls|bears|trenches)$', room)
    if not m:
        return None
    key = m.group(1)
    if key in rs._room_mint_cache:
        return rs._room_mint_cache[key]
    info = None
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/solana/{key}')
            p = ((r.json() or {}).get('pairs') or [None])[0]
            if not p:
                r = await http.get(f'https://api.dexscreener.com/tokens/v1/solana/{key}')
                arr = r.json() if r.status_code == 200 else []
                p = arr[0] if isinstance(arr, list) and arr else None
            if p:
                info = ((p.get('baseToken') or {}).get('address'), (p.get('baseToken') or {}).get('symbol'))
    except Exception:
        info = None
    if info:
        rs._room_mint_cache[key] = info
    return info


async def _holding_usd(owner: str, mint: str):
    rs = _rs()
    key = f'{owner}:{mint}'
    hit = rs._holder_cache.get(key)
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1]
    bal = await rs.token_balance(owner, mint)
    amount = float(bal.get('amount') or 0)
    price = 0.0
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f'https://lite-api.jup.ag/price/v3?ids={mint}')
            price = float(((r.json() or {}).get(mint) or {}).get('usdPrice') or 0)
    except Exception:
        pass
    value = amount * price
    rs._holder_cache[key] = (rs.time.time(), value)
    return value


def _chat_message_to_sign(room, address, ts, text):
    rs = _rs()
    return f'FEELESS chat\nroom:{room}\naddress:{address}\nts:{ts}\nhash:{rs.hashlib.sha256(text.encode()).hexdigest()[:16]}'


def feeless_post(room: str, text: str):
    """Posts from FEELESS itself go out as the one real FEELESS profile — the owner wallet's — never a stand-in account."""
    rs = _rs()
    owner = rs.primary_of(((rs._owner_wallets() or rs._admin_wallets()) or ['FEELESS'])[0])
    msg = rs.chat_system_post(room, rs._display_name(owner), owner, text)
    msg.update(system=False, identity=owner, handle=rs.handle_of(owner), official=True)
    d = rs._chat_load(); d['rooms'][room][-1] = msg; rs.CHAT_PATH.write_text(rs.json.dumps(d))
    return msg


def chat_system_post(room: str, username: str, address: str, text: str, tokens=None):
    """Server-authored message (e.g. Fee's calls). Not user-signed; flagged as system."""
    rs = _rs()
    d = rs._chat_load()
    msg = {'id': rs.uuid.uuid4().hex[:16], 'room': room, 'address': address, 'chain': 'solana', 'username': username, 'text': text,
           'ts': int(rs.time.time() * 1000), 'parentId': None, 'mentions': [], 'tokens': tokens or [], 'system': True,
           'profile': {'address': address, 'chain': 'solana'}}
    d['rooms'].setdefault(room, []).append(msg)
    d['rooms'][room] = d['rooms'][room][-300:]
    rs.CHAT_PATH.write_text(rs.json.dumps(d))
    return msg


async def _fee_usd(address: str) -> float:
    rs = _rs()
    mint = (await rs._ecosystem_mints()).get('fee')
    if not mint or not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address or ''):
        return 0.0
    try:
        return round(await rs._holding_usd(address, mint) or 0, 2)
    except Exception:
        return 0.0


def _is_staff(address: str) -> bool:
    """FEELESS HQ = the admin/creator wallets (any linked wallet of theirs). Staff get every unlock: all badges and
    their perks, every chat background, colors, Fee Reserve rooms, top perk tier."""
    rs = _rs()
    return rs._hq_auth.is_staff(address, rs._admin_wallets() if address else [], rs.primary_of)


async def _alpha_allowed(room: str, address: str) -> bool:
    rs = _rs()
    r = rs._ALPHA.get(room)
    if not r:
        return True
    a = rs.primary_of(address or '')
    return bool(a) and (rs._is_staff(a) or await rs._fee_usd(a) >= r['minUsd'])


def _norm(text):
    rs = _rs()
    return rs._re.sub(r'[^a-z0-9$]+', ' ', text.lower()).strip()[:200]


def _spam_check(d, room, address, text, tier):
    """Returns a user-facing reason to reject, or None. Stateful in the chat store (d['guard']).
    Repeat offenders are auto-muted so bots burn their wallets, not the room."""
    rs = _rs()
    now = rs.time.time(); g = d.setdefault('guard', {}); a = rs.primary_of(address)
    until = (g.get('cool') or {}).get(a, 0)
    if now < until:
        return f'Slow down — cooling off for {int(until - now)}s.'
    hist = [x for x in (g.setdefault('recent', {}).get(a) or []) if now - x[0] < 600]
    n = rs._norm(text)
    # 1) the same wallet repeating itself
    if n and any(x[1] == n for x in hist):
        g['recent'][a] = hist
        return 'You already posted that — no repeats.'
    # 2) flooding
    if sum(1 for x in hist if now - x[0] < 60) >= 8:
        g.setdefault('cool', {})[a] = now + 600
        rs._guard_log(g, 'flood', a, room, text)
        return 'Slow down — too many messages; 10 minute cooldown.'
    # 3) link spam from unproven accounts
    hosts = [h.lower().lstrip('www.') for h in rs._URL_RE.findall(text)]
    if tier < 1 and any(not any(h == s_ or h.endswith('.' + s_) for s_ in rs.SAFE_HOSTS) for h in hosts):
        rs._guard_log(g, 'link', a, room, text)
        return 'Outside links unlock at Fee Friend tier — only trusted sites (DexScreener, Solscan, X, …) for now.'
    # 4) coordinated raids: the same text from 3+ wallets inside 2 minutes
    raid = g.setdefault('texts', {}).setdefault(room, {})
    wallets = {w: t for w, t in (raid.get(n) or {}).items() if now - t < 120} if n and len(n) > 6 else {}
    wallets[a] = now
    if n and len(n) > 6:
        raid[n] = wallets
        if len(raid) > 500:
            for k in list(raid)[:250]:
                raid.pop(k, None)
    if len(wallets) >= 3:
        for w in wallets:
            g.setdefault('cool', {})[w] = now + 1800
        rs._guard_log(g, 'raid', a, room, text, wallets=list(wallets))
        return 'Coordinated copy-paste detected — these wallets are muted for 30 minutes.'
    hist.append((now, n)); g['recent'][a] = hist[-20:]
    return None


def _guard_log(g, kind, address, room, text, wallets=None):
    rs = _rs()
    log = g.setdefault('log', [])
    log.insert(0, {'kind': kind, 'address': address, 'room': room, 'text': text[:120], 'wallets': wallets, 'at': rs.time.time()})
    g['log'] = log[:300]


def _track_pin(d, room, msgs, parent_id):
    """The first message in a room to draw PIN_REPLIES replies gets pinned for PIN_SECONDS."""
    rs = _rs()
    if not parent_id:
        return
    replies = sum(1 for m in msgs if m.get('parentId') == parent_id)
    pins = d.setdefault('pins', {})
    cur = pins.get(room)
    if replies >= rs.PIN_REPLIES and (not cur or rs.time.time() - cur['at'] >= rs.PIN_SECONDS) and (not cur or cur['id'] != parent_id):
        pins[room] = {'id': parent_id, 'at': rs.time.time(), 'replies': replies}


def _internal_key():
    rs = _rs()
    if not rs.INTERNAL_KEY_PATH.exists():
        rs.INTERNAL_KEY_PATH.write_text(rs.uuid.uuid4().hex + rs.uuid.uuid4().hex)
        try:
            rs.os.chmod(rs.INTERNAL_KEY_PATH, 0o600)
        except OSError:
            pass
    return rs.INTERNAL_KEY_PATH.read_text().strip()


async def _ecosystem_mints():
    # Config only (env or launch defaults): no network round trip on the fee / quote path.
    rs = _rs()
    return rs.ecosystem_mints()

