"""🧹 Traffic analytics, season drops, token search, launches, coin logos — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""



def _rs():
    import reputation_service
    return reputation_service


async def _flush_traffic():
    rs = _rs()
    while True:
        await rs.asyncio.sleep(30)
        b = rs._tr_buf
        if not any(b[k] for k in b):
            continue
        d = rs._json_load(rs.TRAFFIC_PATH, {'views': {}, 'uniques': {}, 'coins': {}, 'refs': {}, 'hours': {}})
        for day, pages in b['views'].items():
            dd = d['views'].setdefault(day, {})
            for pg, n in pages.items():
                dd[pg] = dd.get(pg, 0) + n
        for day, s in b['uniq'].items():
            d.setdefault('uniqHashes', {}).setdefault(day, [])
            merged = set(d['uniqHashes'][day]) | s
            d['uniqHashes'][day] = list(merged)[:200000]
            d['uniques'][day] = len(merged)
        for k in ('coins', 'refs'):
            for key, n in b[k].items():
                d[k][key] = d[k].get(key, 0) + n
        for hr, n in b['hours'].items():
            d['hours'][str(hr)] = d['hours'].get(str(hr), 0) + n
        keep = sorted(d['views'])[-60:]
        d['views'] = {k: d['views'][k] for k in keep}; d['uniques'] = {k: v for k, v in d['uniques'].items() if k in keep}
        d['uniqHashes'] = {k: v for k, v in d.get('uniqHashes', {}).items() if k == keep[-1]}  # only today's hashes are kept
        rs._json_save(rs.TRAFFIC_PATH, d)
        for k in b:
            b[k] = {}


async def _shield_check(mint, s):
    """Live compliance for one shielded coin. Appends (never removes) breaches."""
    rs = _rs()
    now = rs.time.time(); active = now - s['at'] < s['lockDays'] * 86400
    checks = []
    try:
        data = await rs._token_holders(mint)
        rows = data['rows']
        dev = sum((r['pct'] or 0) for r in rows if r['owner'] == s['creator'])
        lp = {r['owner'] for r in rows[:3] if (r['pct'] or 0) > 20}
        biggest = max(((r['pct'] or 0, r['owner']) for r in rows if r['owner'] not in lp and r['owner'] != s['creator']), default=(0, None))
        if s.get('devStartPct'):
            kept = dev / s['devStartPct'] * 100
            checks.append({'rule': f"Dev keeps ≥{s['devKeepPct']:.0f}% of its bag", 'ok': kept >= s['devKeepPct'] or not active, 'detail': f"dev holds {dev:.2f}% of supply ({kept:.0f}% of launch bag)"})
        checks.append({'rule': f"No wallet above {s['maxWalletPct']:.1f}%", 'ok': biggest[0] <= s['maxWalletPct'], 'detail': f"largest non-pool wallet {biggest[0]:.2f}%"})
    except Exception:
        checks.append({'rule': 'Holder read', 'ok': True, 'detail': 'chain read unavailable — retrying'})
    if s['noKnownSnipers']:
        intel = (rs._intel_cache.get(mint) or (0, None))[1]
        if intel:
            bl = rs._block_load()['wallets']
            known = [w for w in (intel.get('sniperWallets') or []) + (intel.get('bundledWallets') or []) if rs._is_blocked(bl.get(w))]
            checks.append({'rule': 'No known snipers at launch', 'ok': not known, 'detail': f"{len(known)} blocklisted wallet(s) bought the launch" if known else 'no blocklisted buyers'})
    broken = [c for c in checks if not c['ok']]
    if broken:
        d = rs._json_load(rs.SHIELD_PATH, {})
        rec = d.get(mint)
        if rec:
            for c in broken:
                if not any(b['rule'] == c['rule'] for b in rec['breaches']):
                    rec['breaches'].append({'rule': c['rule'], 'detail': c['detail'], 'at': now})
            rs._json_save(rs.SHIELD_PATH, d)
            s = rec
    status = 'broken' if s.get('breaches') else ('active' if active else 'completed')
    return {'mint': mint, **{k: s[k] for k in ('creator', 'devKeepPct', 'lockDays', 'maxWalletPct', 'noKnownSnipers', 'at')},
            'endsAt': s['at'] + s['lockDays'] * 86400, 'status': status, 'checks': checks, 'breaches': s.get('breaches', [])}


def shield_record(creator: str):
    """For trust/creator scoring: kept vs broken shields."""
    rs = _rs()
    d = rs._json_load(rs.SHIELD_PATH, {})
    mine = [s for s in d.values() if s['creator'] == creator]
    return {'kept': sum(1 for s in mine if not s['breaches'] and rs.time.time() - s['at'] >= s['lockDays'] * 86400), 'broken': sum(1 for s in mine if s['breaches']), 'active': sum(1 for s in mine if not s['breaches'] and rs.time.time() - s['at'] < s['lockDays'] * 86400)}


async def _shield_watch():
    rs = _rs()
    while True:
        await rs.asyncio.sleep(600)
        for mint, s in list(rs._json_load(rs.SHIELD_PATH, {}).items()):
            if rs.time.time() - s['at'] < s['lockDays'] * 86400 + 86400:
                try:
                    await rs._shield_check(mint, s)
                except Exception:
                    pass
                await rs.asyncio.sleep(2)


def _seasons():
    rs = _rs()
    return rs._json_load(rs.SEASONS_PATH, {'seasons': [], 'scores': {}})


def _current_season(d=None):
    rs = _rs()
    d = d or rs._seasons(); now = rs.time.time()
    return next((s for s in d['seasons'] if s['start'] <= now < s['end']), None)


def _tier(score):
    rs = _rs()
    name = rs.SEASON_TIERS[0][0]
    for n, need in rs.SEASON_TIERS:
        if score >= need:
            name = n
    nxt = next(((n, need) for n, need in rs.SEASON_TIERS if need > score), None)
    return {'tier': name, 'next': nxt[0] if nxt else None, 'toNext': round(nxt[1] - score) if nxt else 0}


def _owner_wallets():
    rs = _rs()
    return rs._hq_auth.owner_wallets(rs.os.environ.get('FEELESS_ADMIN_WALLETS', ''))


def _granted():
    rs = _rs()
    return rs._json_load(rs.ROLES_PATH, {'grants': {}})['grants']


async def wallet_trades(address: str, limit: int = 40):
    rs = _rs()
    hit = rs._wtrades_cache.get(address)
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1]
    async with rs.httpx.AsyncClient(timeout=12) as http:
        rows = [] if address.startswith('0x') else [{**r, 'chain': 'solana'} for r in await rs._maker_swaps(http, address)]
        rows.sort(key=lambda x: -x['ts'])
        rs._wtrades_all[address] = (rs.time.time(), list(rows))   # full window, used for positions
        rows = rows[:limit]
        meta = {}
        toks = list({r['token'] for r in rows})
        for i in range(0, len(toks), 30):
            try:
                pairs = (await http.get(f"https://api.dexscreener.com/latest/dex/tokens/{','.join(toks[i:i + 30])}")).json().get('pairs') or []
                for p in sorted(pairs, key=lambda p: -((p.get('liquidity') or {}).get('usd') or 0)):
                    a = (p.get('baseToken') or {}).get('address')
                    if a and a not in meta:
                        meta[a] = {'symbol': p['baseToken'].get('symbol'), 'pair': p.get('pairAddress'), 'chain': p.get('chainId'), 'imageUrl': (p.get('info') or {}).get('imageUrl')}
            except Exception:
                pass
    for r in rows:
        r.update(meta.get(r['token'], {'symbol': r['token'][:4] + '…', 'pair': None}))
    rs._wtrades_cache[address] = (rs.time.time(), rows)
    return rows


def _season_weeks(s):
    rs = _rs()
    weeks, t, i = [], s['start'], 0
    while t < s['end']:
        th = rs.WEEK_THEMES[min(i, len(rs.WEEK_THEMES) - 1)] if i < len(rs.WEEK_THEMES) - 1 or t + 7 * 86400 >= s['end'] else rs.WEEK_THEMES[i % (len(rs.WEEK_THEMES) - 1)]
        ov = (s.get('weeks') or {}).get(str(i + 1)) or {}
        weeks.append({'week': i + 1, 'start': t, 'end': min(t + 7 * 86400, s['end']), 'theme': th[0], 'name': ov.get('name') or th[1], 'glyph': ov.get('glyph') or th[2],
                      'story': ov.get('story') or th[3], 'imageUrl': ov.get('imageUrl') or None})
        t += 7 * 86400; i += 1
    return weeks


def _week_of(s, ts):
    rs = _rs()
    return next((w for w in rs._season_weeks(s) if w['start'] <= ts < w['end']), None)


def _grant(col, address, item):
    items = col.setdefault(address, [])
    if not any(x['id'] == item['id'] for x in items):
        items.append(item)


def _distribute_drops():
    rs = _rs()
    d = rs._seasons(); col = rs._json_load(rs.COLLECTION_PATH, {}); done = set(d.setdefault('distributed', []))
    now = rs.time.time(); changed = False
    for s in d['seasons']:
        for w in rs._season_weeks(s):
            key = f"{s['id']}:w{w['week']}"
            if w['end'] > now or key in done:
                continue
            board = sorted((d['scores'].get(key) or {}).items(), key=lambda kv: -kv[1]['score'])
            n = len(board)
            for i, (a, r) in enumerate(board):
                rarity = 'legendary' if i < 3 else 'epic' if i < max(1, round(n * 0.1)) else 'rare' if r['score'] >= 300 else 'common' if r['score'] >= 50 else None
                if rarity:
                    rs._grant(col, a, {'id': f"{key}:{w['theme']}", 'kind': 'weekly', 'season': s['id'], 'seasonName': s['name'], 'week': w['week'], 'name': w['name'], 'glyph': w['glyph'], 'imageUrl': w.get('imageUrl'),
                                    'story': w['story'], 'rarity': rarity, 'how': dict(rs.RARITIES)[rarity], 'rank': i + 1, 'score': r['score'], 'accent': s['accent'], 'at': now})
            done.add(key); changed = True
        if s['end'] <= now and s['id'] not in done:
            for a, r in (d['scores'].get(s['id']) or {}).items():
                t = rs._tier(r['score'])['tier']
                rs._grant(col, a, {'id': f"{s['id']}:season", 'kind': 'season', 'season': s['id'], 'seasonName': s['name'], 'name': f"Season {s['id'][1:]} · {s['name']}", 'glyph': '🏅', 'imageUrl': s.get('badgeUrl'),
                                'story': s.get('theme', ''), 'rarity': {'Legend': 'legendary', 'Diamond': 'epic', 'Gold': 'rare'}.get(t, 'common'), 'how': f'Finished the season at {t} tier',
                                'tier': t, 'score': r['score'], 'accent': s['accent'], 'reserveWallet': s.get('reserveWallet', ''),
                                'badgeRewardPct': float(s.get('badgeRewardPct') or 0), 'rewardStatus': 'planned', 'at': now})
            done.add(s['id']); changed = True
    if changed:
        d['distributed'] = sorted(done); rs._json_save(rs.SEASONS_PATH, d); rs._json_save(rs.COLLECTION_PATH, col)


async def _drops_loop():
    rs = _rs()
    while True:
        try:
            rs._distribute_drops()
        except Exception as exc:
            print('drops error', exc)
        await rs.asyncio.sleep(1800)


def _is_upload_url(u):
    # Only FEELESS-hosted uploads (validated real images) — no arbitrary links.
    rs = _rs()
    return u in (None, '') or bool(rs._re.match(r'^/api/reputation/uploads/[0-9a-f]{32}\.(png|jpg|webp|gif)$', u))


async def _feeless_fills(address: str) -> list:
    """Every confirmed FEELESS order for this wallet (trading service), so a position shows even when the
    live confirm hook was missed (old trades, a restart, a closed tab). Cached 8s."""
    rs = _rs()
    hit = rs._fills_cache.get(address)
    if hit and rs.time.time() - hit[0] < 8:
        return hit[1]
    rows = hit[1] if hit else []
    if rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        try:
            async with rs.httpx.AsyncClient(timeout=4) as http:
                r = await http.get(f'http://127.0.0.1:5001/api/trading/internal/fills/{address}', params={'sol': await rs._sol_usd()},
                                   headers={'x-feeless-internal': rs._internal_key()})
                if r.status_code == 200:
                    rows = r.json().get('fills') or []
        except Exception:
            pass
    rs._fills_cache[address] = (rs.time.time(), rows)
    return rows


async def _chain_fills(address: str, token: str) -> dict:
    """Exact fills from the wallet's own transactions (trading service RPC pool) + its live balance."""
    rs = _rs()
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) or not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', token):
        return {}
    try:
        async with rs.httpx.AsyncClient(timeout=15) as http:   # a wallet's first scan reads its history once; later ones are instant
            r = await http.get(f'http://127.0.0.1:5001/api/trading/chain-fills/{address}/{token}', headers={'x-feeless-internal': rs._internal_key()})
            return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


async def _repair_estimates(address: str, token: str):
    """Self-heal: any of this wallet's FEELESS trades saved from a quote gets its exact on-chain fill read once and
    saved over the estimate (at most one attempt per trade per minute; never blocks the position for long)."""
    rs = _rs()
    # Estimates, and exact rows saved before the pool amount was read, both get one exact re-read.
    rows = [r for r in rs._json_load(rs.FEELESS_TRADES_PATH, {}).get(address, []) if r.get('token', '').lower() == token.lower() and not r.get('locked')]
    now = rs.time.time()
    todo = [r['tx'] for r in rows if r.get('tx') and now - rs._repair_tried.get(r['tx'], 0) > 60][:3]
    if not todo:
        return

    async def one(sig):
        rs._repair_tried[sig] = now
        try:
            async with rs.httpx.AsyncClient(timeout=6) as http:
                r = await http.get(f'http://127.0.0.1:5001/api/trading/internal/exact-fill/{sig}', headers={'x-feeless-internal': rs._internal_key()})
                return sig, (r.json().get('fill') if r.status_code == 200 else None)
        except Exception:
            return sig, None
    got = {sig: f for sig, f in await rs.asyncio.gather(*(one(s) for s in todo)) if f and f.get('tokens')}
    if not got:
        return
    px = await rs._sol_usd()
    ft = rs._json_load(rs.FEELESS_TRADES_PATH, {})
    fixed = []
    for r in ft.get(address) or []:
        f = got.get(r.get('tx'))
        usd = (f.get('usd') or (f.get('sol') or 0) * px) if f else 0
        if f and usd > 0:
            r = {**r, 'side': f['side'], 'tokens': f['tokens'], 'sol': f.get('sol'), 'networkSol': f.get('networkSol'), 'usd': round(usd, 4),
                 **{k: f[k] for k in ('poolUsd', 'feelessFeeUsd', 'networkUsd', 'solUsd', 'locked') if f.get(k) is not None},
                 'locked': True,   # read once, priced once: never re-read or re-priced again
                 'price': usd / f['tokens'], 'ts': f.get('ts') or r.get('ts'), 'via': 'chain'}
        fixed.append(r)
    ft[address] = fixed
    rs._json_save(rs.FEELESS_TRADES_PATH, ft)


async def _locked_fills(address: str) -> list:
    """Every locked fill stored for this wallet (all coins), from the trading service. Same numbers as the chart."""
    rs = _rs()
    try:
        async with rs.httpx.AsyncClient(timeout=5) as http:
            r = await http.get(f'http://127.0.0.1:5001/api/trading/internal/wallet-fills/{address}', headers={'x-feeless-internal': rs._internal_key()})
            return r.json().get('fills') or [] if r.status_code == 200 else []
    except Exception:
        return []


async def _git(*args, timeout=8):
    rs = _rs()
    proc = await rs.asyncio.create_subprocess_exec('git', *args, cwd=str(rs.Path(__file__).resolve().parents[1]), stdout=rs.asyncio.subprocess.PIPE, stderr=rs.asyncio.subprocess.DEVNULL)
    try:
        out, _ = await rs.asyncio.wait_for(proc.communicate(), timeout)
    except rs.asyncio.TimeoutError:
        proc.kill(); return ''
    return out.decode().strip() if proc.returncode == 0 else ''


def _pass_site():
    rs = _rs()
    site = rs.os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/')
    host = rs._re.sub(r'^https?://', '', site).split('/')[0].split(':')[0]
    ok = site.startswith('https://') and host not in ('localhost', '127.0.0.1', '0.0.0.0') and not host.endswith('.local') and not rs._re.match(r'^(10|192\.168|172\.(1[6-9]|2\d|3[01]))\.', host)
    return site if ok else ''


async def _agent_pass_rules():
    rs = _rs()
    cfg = rs._fee_cfg(); fee_w = ((rs._json_load(rs.COLONY_PATH, {}) or {}).get('wallet') or {}).get('address') or ''   # 🪙 an agent's fee goes to the Collective
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            rent = int(await rs._rpc(http, 'getMinimumBalanceForRentExemption', [rs._apass.ASSET_BYTES]) or 0)
    except Exception:
        rent = 0
    prov = rs._apass.provider_lamports(rent) if rent else 0
    fee = rs._apass.fee_lamports(prov, cfg.get('agentPassFeeLamports') or 0) if prov else int(cfg.get('agentPassFeeLamports') or 0)
    why = '' if rs._pass_site() else 'Minting opens when FEELESS has its public domain (PUBLIC_SITE_URL, https) — a Pass\'s picture link is permanent.'
    why = why or ('' if fee_w else 'The Collective wallet is not open yet.') or ('' if prov else 'Solana did not answer — try again in a minute.')
    return {'ready': not why, 'why': why, 'feeWallet': fee_w, 'providerLamports': prov, 'feeLamports': fee, 'royaltyBps': rs._apass.ROYALTY_BPS, 'auto': not (cfg.get('agentPassFeeLamports') or 0)}


async def _owned_cat(cat_id, me):
    rs = _rs()
    if not rs._re.match(r'^[A-Za-z0-9_-]{1,64}$', cat_id or ''):
        raise rs.HTTPException(400, 'Not an agent id.')
    r = await rs._ai_http().get(f'http://127.0.0.1:5088/api/cats/{cat_id}', headers={'x-feeless-internal': rs._internal_key()}, timeout=8)
    if r.status_code != 200:
        raise rs.HTTPException(404, 'Agent not found.')
    cat = (r.json() or {}).get('cat') or {}
    if me not in (cat.get('ownerWallet'), (cat.get('agentWallet') or {}).get('owner')):
        raise rs.HTTPException(403, "Only this agent's owner wallet can mint its Pass.")
    return cat


async def _chart_fill(rows, now, limit=14):
    """📈 Candidates whose chart our own record cannot read yet (new to the board) get it from the market's 15-min candles
    (candles service, last 4h). ≤ `limit` lookups a tick, in parallel, 4 min cache; a miss leaves the row as it was. Tests never fetch."""
    rs = _rs()
    need = [x for x in rows if not x.get('cBars') and x.get('pairAddress')][:limit]
    todo = [x['pairAddress'] for x in need if now - (rs._CHART_FILL.get(x['pairAddress']) or (0, None))[0] > 240]
    if todo and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        async def one(http, pa):
            try:
                r = await http.get(f'http://127.0.0.1:5099/api/candles/solana/{pa}', params={'interval': '15m'})
                return pa, rs._pedge._chart.keys(rs._pedge._chart.points_from_candles((r.json() or {}).get('candles') or []), now)
            except Exception:
                return pa, None
        async with rs.httpx.AsyncClient(timeout=5) as http:
            for pa, k in await rs.asyncio.gather(*(one(http, pa) for pa in todo)):
                if k is not None:
                    rs._CHART_FILL[pa] = (now, k)
        if len(rs._CHART_FILL) > 400:
            for pa in sorted(rs._CHART_FILL, key=lambda q: rs._CHART_FILL[q][0])[:200]:
                rs._CHART_FILL.pop(pa, None)
    out = []
    for x in rows:
        hit = rs._CHART_FILL.get(x.get('pairAddress')) if not x.get('cBars') else None
        out.append({**x, **hit[1]} if hit and hit[1].get('cBars') else x)
    return out


def _rpc_call_ok(c) -> bool:
    rs = _rs()
    if not isinstance(c, dict):
        return False
    if c.get('method') in rs.RPC_ALLOW:
        return True
    if c.get('method') != 'getProgramAccounts':
        return False
    p_ = c.get('params') or []
    opt_ = p_[1] if len(p_) > 1 and isinstance(p_[1], dict) else {}
    return bool(p_) and p_[0] in rs.RPC_GPA_PROGRAMS and any(isinstance(f_, dict) and 'memcmp' in f_ for f_ in (opt_.get('filters') or []))


def _relay_spent(r) -> bool:
    """An RPC answer that means 'this endpoint is out of quota / rate-limited' (HTTP 429, or a JSON-RPC error with code 429)."""
    if r.status_code == 429:
        return True
    try:
        b = r.json()
    except Exception:
        return False
    return any(isinstance(x, dict) and isinstance(x.get('error'), dict) and x['error'].get('code') in (429, -32429) for x in (b if isinstance(b, list) else [b]))


def _gold_creator(a):
    """Creator streak: 3+ launches, none dumped or rugged, scored Trusted. Earns the gold R."""
    rs = _rs()
    entry = rs._load()['creators'].get(rs._creator_key('solana', a))
    if not entry:
        return False
    sc = rs.score_creator(entry)
    return sc.get('badge') == 'trusted' and sc.get('tokenCount', 0) >= 3 and not (sc.get('dumpedCount', 0) + sc.get('ruggedCount', 0))


async def _quiet(coro):
    try:
        await coro
    except Exception:
        pass


def _ipfs_variants(u):
    rs = _rs()
    m = rs._re.search(r'/ipfs/([^?#]+)', u or '') or rs._re.match(r'^ipfs://(.+)$', u or '')
    return [g + m.group(1) for g in rs.IPFS_GATEWAYS] if m else [u]


async def _public_get(http, u, hops=3):
    """🔒 SITE-9 (2026-11-10): a URL from a coin's own metadata is the launcher's to choose, so it could name 127.0.0.1 or the LAN and make this
    server call it. Every hop must be a public http(s) address (`feeless_mcp.safe_url`); redirects are followed by hand so each one is checked."""
    rs = _rs()
    import feeless_mcp as _fm
    from urllib.parse import urljoin
    for _ in range(hops + 1):
        if await rs.asyncio.to_thread(_fm.safe_url, u):
            return None
        r = await http.get(u, timeout=8, follow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get('location'):
            u = urljoin(u, r.headers['location']); continue
        return r
    return None


async def _fetch_first(http, urls, want_json=False):
    rs = _rs()
    for u in urls:
        try:
            r = await rs._public_get(http, u)
            if r is None or r.status_code != 200:
                continue
            if want_json:
                return r.json()
            ct = r.headers.get('content-type', '').split(';')[0]
            if ct.startswith('image/') and 0 < len(r.content) <= 2_500_000:
                return ct, r.content
        except Exception:
            continue
    return None


def _logo_thumb(raw, w):
    """🖼 SITE-2: a coin logo at the size it is shown (2× its CSS px). 940 px logos were decoded for 22 px rows. → webp bytes, or None to serve the original."""
    import io
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(raw))
        if getattr(im, 'is_animated', False) or max(im.size) <= w:   # an animated logo keeps its motion; a small one is already small
            return None
        im = im.convert('RGBA'); im.thumbnail((w, w), Image.LANCZOS); out = io.BytesIO(); im.save(out, 'WEBP', quality=86, method=4)
        return out.getvalue()
    except Exception:   # noqa: BLE001 — anything Pillow can't read (svg) is served as it is
        return None


async def _token_logo_any(mint: str):
    rs = _rs()
    from fastapi.responses import FileResponse, Response
    if not rs._re.match(rs._B58, mint):
        raise rs.HTTPException(400, 'Solana mint required.')
    rs.LOGO_DIR.mkdir(parents=True, exist_ok=True)
    hit = next(rs.LOGO_DIR.glob(f'{mint}.*'), None)
    headers = {'Cache-Control': 'public, max-age=604800, immutable'}
    over = rs._json_load(rs.LOGO_OVERRIDE_PATH, {}).get(mint)
    if over and (rs.UPLOAD_DIR / over.rsplit('/', 1)[-1]).exists():   # owner-set logo (HQ) always wins
        return FileResponse(rs.UPLOAD_DIR / over.rsplit('/', 1)[-1], headers={'Cache-Control': 'public, max-age=300'})
    if hit:
        return FileResponse(hit, headers=headers)
    if rs.time.time() - rs._logo_miss.get(mint, 0) < 600:
        raise rs.HTTPException(404, 'No logo found.')
    lock = rs._logo_locks.setdefault(mint, rs.asyncio.Lock())
    async with lock:
        hit = next(rs.LOGO_DIR.glob(f'{mint}.*'), None)
        if hit:
            return FileResponse(hit, headers=headers)
        async def _find():
            # Each source's picture is tried the moment it is known: DexScreener answers in 0.1 s, and waiting
            # for the slower sources first ran out LOGO_BUDGET and answered 404 for coins that do have a logo.
            async with rs.httpx.AsyncClient(headers={'User-Agent': 'Mozilla/5.0'}) as http:
                async def _try(cands):
                    for u in [x for x in cands if x]:
                        got = await rs._fetch_first(http, rs._ipfs_variants(u))
                        if got:
                            return got
                    return None
                try:
                    d = (await http.get(f'https://api.dexscreener.com/tokens/v1/solana/{mint}', timeout=8)).json()
                    got = await _try([(p.get('info') or {}).get('imageUrl') for p in (d or [])[:3]])
                    if got:
                        return got
                except Exception:
                    pass
                try:
                    d = (await http.get(f'https://lite-api.jup.ag/tokens/v2/search?query={mint}', timeout=8)).json()
                    got = await _try([x.get('icon') for x in d if x.get('id') == mint])
                    if got:
                        return got
                except Exception:
                    pass
                try:   # on-chain Metaplex metadata: works on any RPC (getAsset below is Helius-only)
                    acct = await rs._rpc(http, 'getAccountInfo', [rs.coin_meta.metadata_pda(mint), {'encoding': 'base64'}])
                    data = (((acct or {}).get('value') or {}).get('data') or [None])[0]
                    if data:
                        uri = rs.coin_meta.parse_metadata(data).get('uri')
                        if uri:
                            meta = await rs._fetch_first(http, rs._ipfs_variants(uri), want_json=True)
                            got = await _try([(meta or {}).get('image')])
                            if got:
                                return got
                except Exception:
                    pass
                if mint.endswith('pump'):
                    try:
                        d = (await http.get(f'https://frontend-api-v3.pump.fun/coins-v2/{mint}', timeout=8)).json()
                        got = await _try([(d or {}).get('image_uri')])
                        if got:
                            return got
                    except Exception:
                        pass
                try:
                    a = await rs._rpc(http, 'getAsset', {'id': mint})
                    c = (a or {}).get('content') or {}
                    cands = [f.get('cdn_uri') for f in c.get('files') or []] + [(c.get('links') or {}).get('image')]
                    if c.get('json_uri'):
                        meta = await rs._fetch_first(http, rs._ipfs_variants(c['json_uri']), want_json=True)
                        cands.append((meta or {}).get('image'))
                    return await _try(cands)
                except Exception:
                    return None

        try:   # ⏱ every source together gets LOGO_BUDGET; a slow miss answers 404 at once (the page falls back to the next logo / glyph)
            got = await rs.asyncio.wait_for(_find(), timeout=rs.LOGO_BUDGET)
        except rs.asyncio.TimeoutError:
            got = None
            rs._logo_miss[mint] = rs.time.time() - (600 - rs.LOGO_SLOW_RETRY)   # a SLOW coin is retried after LOGO_SLOW_RETRY, a missing one after 10 min
            raise rs.HTTPException(404, 'No logo found in time.')
        if not got:
            rs._logo_miss[mint] = rs.time.time()
            raise rs.HTTPException(404, 'No logo found.')
        ct, body = got
        ext = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif', 'image/svg+xml': 'svg'}.get(ct, 'img')
        if rs._strim.cache_logo_ok(body):   # a huge logo is served, never cached (the cache had grown to 1.0 GB)
            (rs.LOGO_DIR / f'{mint}.{ext}').write_bytes(body)
        return Response(body, media_type=ct, headers=headers)


async def _probe_latency():
    rs = _rs()
    out = []
    async with rs.httpx.AsyncClient(timeout=8) as http:
        for name, role, env, url in rs.LATENCY_PROBES:
            t0 = rs.time.time(); ok, note = False, ''
            try:
                if name == 'Helius RPC':
                    rpc = rs.os.environ.get('SOLANA_RPC_URL', '').strip()
                    r = await http.post(rpc, json={'jsonrpc': '2.0', 'id': 1, 'method': 'getSlot'}) if rpc else None
                    ok = bool(r and r.status_code == 200 and 'result' in r.json()); note = '' if rpc else 'not configured'
                else:
                    r = await http.get(url()); ok = r.status_code == 200; note = '' if ok else f'HTTP {r.status_code}'
            except Exception as exc:
                note = type(exc).__name__
            out.append({'name': name, 'role': role, 'env': env, 'ok': ok, 'ms': round((rs.time.time() - t0) * 1000), 'note': note})
    return {'providers': out, 'chartOrder': ['Jupiter chart data', 'Alchemy', 'Helius swaps', 'FEELESS-recorded ticks'],
            'checkedAt': rs.time.time()}


async def _latency_alarm():
    # Any provider down or >1.5s for 5 straight minutes gets posted to the admin Updates room, once per outage.
    rs = _rs()
    while True:
        await rs.asyncio.sleep(60)
        try:
            rows = (await rs._probe_latency())['providers']
            for r in rows:
                bad = r['note'] != 'not configured' and (not r['ok'] or r['ms'] > 1500)
                st = rs._latency_bad.get(r['name'])
                if not bad:
                    if st and st.get('posted'):
                        rs._ops_note(f"✅ {r['name']} recovered ({r['ms']} ms).")
                    rs._latency_bad.pop(r['name'], None)
                    continue
                st = rs._latency_bad.setdefault(r['name'], {'since': rs.time.time()})
                if not st.get('posted') and rs.time.time() - st['since'] >= 300:
                    st['posted'] = True
                    why = r['note'] or 'down' if not r['ok'] else f"{r['ms']} ms"
                    rs._ops_note(f"⚠️ {r['name']} ({r['role']}) degraded for 5+ min: {why}. Fallbacks are serving.")
        except Exception as exc:
            print('latency alarm error', exc)


def _ops_note(text):
    """🛠 Service health goes to the owners' private inbox (HQ), never the public FEEd (owner 2026-10-26: a social feed full of 'Jupiter price recovered' isn't real)."""
    rs = _rs()
    for w_ in (rs._owner_wallets() or [])[:3]:
        rs.notify(w_, 'ops', text, url='/terminal/hq', push=False, meta={'claim': 'ops', 'source': 'latency'})


async def _three_day_movers():
    """% move over the last 72h for the globe's most-traded coins, from FEELESS's own hourly candles."""
    rs = _rs()
    if rs.time.time() - rs._movers_cache['at'] < 1800:
        return rs._movers_cache['rows']
    toks = sorted(((rs._globe_cache['data'] or {}).get('tokens') or []), key=lambda t: -(t.get('volume24h') or 0))[:40]
    sem = rs.asyncio.Semaphore(6)
    async with rs.httpx.AsyncClient(timeout=15) as http:
        async def one(t):
            async with sem:
                try:
                    c = (await http.get(f"http://127.0.0.1:5099/api/candles/{t['chain']}/{t['pairAddress']}", params={'interval': '1h'})).json().get('candles') or []
                except Exception:
                    return None
            cutoff = rs.time.time() - 72 * 3600
            past = next((x for x in c if x[0] >= cutoff), None)
            if not past or not c or past[4] <= 0:
                return None
            return {**{k: t.get(k) for k in ('chain', 'symbol', 'name', 'imageUrl', 'pairAddress', 'marketCap')}, 'move3d': round((c[-1][4] / past[4] - 1) * 100, 1)}
        rows = [r for r in await rs.asyncio.gather(*(one(t) for t in toks)) if r]
    rows.sort(key=lambda r: -r['move3d'])
    rs._movers_cache.update(at=rs.time.time(), rows=rows)
    return rows


def _post_text(r):
    up = r['move3d'] >= 0
    return (f"${r['symbol']} {'+' if up else ''}{r['move3d']}% in 3 days on {r['chain'].title()} {'🚀' if up else '🩸'}\n"
            f"Chart it, chat it and trade it fee-free on FEELESS — every call on the record.\n#{r['chain']} #memecoins #FEELESS")

