"""🧹 Fuse pools — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


async def _jup_tokens(mints, keyed=False):
    """📡 Jupiter token rows for these mints (100 per call, cached 60s). The fallback for DexScreener (sitewide data rule: DexScreener, our indexes, Jupiter).
    The key is spent only for `keyed=True` (the keeper's final buy gate) — see `_jup_prices`."""
    rs = _rs()
    now, out, need = rs.time.time(), {}, []
    for m in dict.fromkeys(x for x in mints if x):
        hit = rs._jup_tok_cache.get(m)
        if hit and now - hit[0] < 60:
            out[m] = hit[1]
        else:
            need.append(m)
    if need:
        key = rs.os.getenv('JUPITER_API_KEY', '') if keyed else (rs._jkeys.read_key(rs.os.environ) or '')   # 🔑 reads: the READ key (never the keeper's)
        srcs = ([('https://api.jup.ag/tokens/v2/search', {'x-api-key': key})] if key else []) + [('https://lite-api.jup.ag/tokens/v2/search', {})]
        async with rs.httpx.AsyncClient(timeout=8) as http:
            async def one(chunk):
                # every source, twice: a 429 / blip on one (a restart's burst refused OCTO's real buy as "live market unavailable")
                # falls through to the other instead of reading as "Jupiter doesn't know this coin"
                for attempt in range(2):
                    for base, hdr in srcs:
                        try:
                            r = await http.get(base, params={'query': ','.join(chunk)}, headers=hdr)
                            if r.status_code == 200:
                                rows = r.json()
                                if isinstance(rows, list):
                                    return rows
                        except Exception:
                            pass
                    await rs.asyncio.sleep(0.6)
                return []
            for rows in await rs.asyncio.gather(*[one(need[i:i + 100]) for i in range(0, len(need), 100)]):
                for t in rows if isinstance(rows, list) else []:
                    if t.get('id'):
                        rs._jup_tok_cache[t['id']] = (now, t); out[t['id']] = t
    return out


async def _fuse_pairs(legs):
    """Live pairs for every leg, cached 60s: DexScreener first (30 a call — it used to ask for only the first 30 per chain), and for
    any Solana pair it could not answer, Jupiter's token data in the same pair shape (`source: 'jupiter'`, keyed by the leg's pair)
    — 2026-10-07 DexScreener's API answered empty for every pair and live depth, the rug shield and the final buy check went blind."""
    rs = _rs()
    out, need, mint_of = {}, {}, {}
    for leg in legs:
        hit = rs._fuse_pairs_cache.get(leg['pairAddress'])
        if hit and rs.time.time() - hit[0] < 60:
            out[leg['pairAddress']] = hit[1]
        else:
            need.setdefault(leg['chainId'], []).append(leg['pairAddress'])
            m_ = leg.get('mint') or leg.get('baseAddress') or rs._pair_mint.get(leg['pairAddress'])
            if m_:
                mint_of[leg['pairAddress']] = m_
    if need:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            async def one(chain, pairs):
                try:
                    r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{",".join(pairs)}')
                    return (r.json() or {}).get('pairs') or []
                except Exception:
                    return []
            jobs = [one(c, ps[i:i + 30]) for c, ps in need.items() for i in range(0, len(ps), 30)]
            for rows in await rs.asyncio.gather(*jobs):
                for p in rows:
                    rs._fuse_pairs_cache[p.get('pairAddress')] = (rs.time.time(), p); out[p.get('pairAddress')] = p
                    if (p.get('baseToken') or {}).get('address'):
                        rs._pair_mint[p.get('pairAddress')] = p['baseToken']['address']
        miss = {pa: m for pa, m in mint_of.items() if pa not in out and pa in (need.get('solana') or [])}
        if miss:
            toks = await rs._jup_tokens(list(miss.values()))
            for pa, m in miss.items():
                jp = rs._launchpad_board.jup_pair(toks.get(m)) if toks.get(m) else None
                if jp:
                    jp = {**jp, 'pairAddress': pa}
                    rs._fuse_pairs_cache[pa] = (rs.time.time(), jp); out[pa] = jp
    return out


def _fuse_risky(pair):
    """Launch-forensics flag from CACHED intel only (never blocks a list): heavy top-10 or repeat-rug funders."""
    rs = _rs()
    hit = rs._intel_cache.get((pair.get('baseToken') or {}).get('address'))
    d = hit[1] if hit else None
    return bool(d) and ((d.get('top10Pct') or 0) > 60 or bool(d.get('flaggedFunders')))


async def _fuse_view(fid, f, store):
    rs = _rs()
    pairs = await rs._fuse_pairs(f['legs'])
    legs = [{**leg, **(rs._fuse.leg_meta(pairs[leg['pairAddress']]) if pairs.get(leg['pairAddress']) else {'missing': True})} for leg in f['legs']]
    metas = [leg for leg in legs if not leg.get('missing')]
    now_px = {leg['pairAddress']: leg.get('priceUsd') for leg in metas}
    buys = [b for b in store.get('buys', []) if b['fuse'] == fid]
    earned = round(sum(b['creatorUsd'] for b in buys), 6); paid = round(float((store.get('paid') or {}).get(fid, 0)), 6)
    return {'id': fid, **{k: f.get(k) for k in ('name', 'emoji', 'tagline', 'creator', 'creatorBps', 'createdAt', 'enabled', 'aura', 'featured', 'arena', 'dial', 'cfg', 'fromScenario')}, 'legs': legs,
            'index': rs._fuse.index(f['legs'], f.get('basePrices') or {}, now_px), 'score': rs._fuse.score(metas, sum(1 for leg in f['legs'] if pairs.get(leg['pairAddress']) and rs._fuse_risky(pairs[leg['pairAddress']]))),
            'tvlUsd': round(sum(m['liquidityUsd'] for m in metas)), 'volume24h': round(sum(m['volume24h'] for m in metas)),
            'aprEst': round(sum(m['aprEst'] * m['weight'] for m in metas) / max(1, sum(m['weight'] for m in metas)), 1),
            'trust': {'buyers': len({b['wallet'] for b in buys}), 'trusted': len({b['wallet'] for b in buys if not b.get('selfDeal') and not b.get('bot')})},
            'stats': {'buys': len(buys), 'volumeUsd': round(sum(b['usd'] for b in buys), 2), 'creatorEarnedUsd': earned, 'creatorPaidUsd': paid, 'creatorOwedUsd': round(max(0.0, earned - paid), 6)}}


def _creator_warn(c):
    """One plain line when a scanned launch coin's creator is flagged, else ''."""
    if not c:
        return ''
    if c.get('creatorRep') == 'high':
        return 'Creator is HIGH risk (blocklist / rug report / serial sniper). The engine will not buy this coin.'
    if c.get('creatorFlagged') or c.get('creatorRep') == 'suspect':
        return 'Creator is flagged as suspect. The engine buys it only once the coin proves itself.'
    return ''


async def _fuse_discover_pairs(chain):
    """Every existing discovery rail in one deduped pool: DexScreener search/boost plus FEELESS trending/new/launchpad feeds."""
    rs = _rs()
    hit = rs._fuse_discover_cache.get(chain)
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1]
    async with rs.httpx.AsyncClient(timeout=8) as http:
        async def search(q):
            try:
                return ((await http.get('https://api.dexscreener.com/latest/dex/search', params={'q': q})).json() or {}).get('pairs') or []
            except Exception:
                return []

        async def boosted():
            try:
                toks = [t.get('tokenAddress') for t in (await http.get('https://api.dexscreener.com/token-boosts/top/v1')).json() or [] if t.get('chainId') == chain][:30]
                return (await http.get(f'https://api.dexscreener.com/tokens/v1/{chain}/{",".join(toks)}')).json() or [] if toks else []
            except Exception:
                return []
        async def feed(kind, page=1, scope=None):
            try:
                params = {'kind': kind, 'chain': chain, 'page': page}
                if scope:
                    params['scope'] = scope
                r = await http.get('http://127.0.0.1:5001/api/market/feed', params=params)
                return r.json().get('pairs') or [] if r.status_code == 200 else []
            except Exception:
                return []
        got = await rs.asyncio.gather(*[search(q) for q in rs.FUSE_DISCOVER_Q.get(chain, (chain,))], boosted(),
                                   feed('trending'), feed('new'), feed('trending', 2), feed('new', 2),
                                   feed('trending', scope='launchpads'), feed('new', scope='launchpads'), feed('trending', scope='pump'))
    pairs = []
    seen = set()
    for rows in got:
        for p in rows if isinstance(rows, list) else []:
            key = p.get('pairAddress')
            if key and key not in seen:
                seen.add(key); pairs.append(p)
    rs._fuse_discover_cache[chain] = (rs.time.time(), pairs)
    return pairs


async def _jup_lite(mints):
    """🧪 Jupiter audit facts for these coins (batched 100 a call through `_jup_tokens`, each coin re-read at most every 3 min).
    Owner, 2026-10-08: only ~19 of 271 listed coins were ever holder-scanned (one RPC lane answers), so the lists ran in circles."""
    rs = _rs()
    now = rs.time.time()
    need = [m for m in dict.fromkeys(mints) if m and now - rs._jup_facts.get(m, (0.0, None))[0] > rs.JUP_FACTS_TTL]
    if need and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        try:
            got = await rs._jup_tokens(need[:800])
        except Exception:
            got = {}
        for m, t in (got or {}).items():
            rs._jup_facts[m] = (now, rs._ja.facts(t))
    return {m: rs._jup_facts[m][1] for m in mints if m in rs._jup_facts}


def _cand_map():
    rs = _rs()
    return {c.get('mint'): c for c in rs._runner_cands if c.get('mint')}


def _read_for(r, cmap=None, lens=None):
    """🎢 / 🧲 / 🔥 The read that fits this coin (jup_audit.pick_read), with the runner board's curve %, curve speed and 5-min flow filled in."""
    rs = _rs()
    m = r.get('mint') or r.get('baseAddress')
    c = (cmap if cmap is not None else rs._cand_map()).get(m) or {}
    x = {k: c.get(k) for k in ('vol5m', 'vol1h', 'chg5m', 'chg1h', 'chg24h', 'txns1h', 'buyShare', 'ageH', 'curveSpeed', 'top10', 'dev', 'insiders') if c.get(k) is not None}
    x.update({k: v for k, v in r.items() if v is not None})
    for a_, b_ in (('change5m', 'chg5m'), ('change1h', 'chg1h'), ('change6h', 'chg6h'), ('change24h', 'chg24h'), ('marketCap', 'mcap'), ('volume24h', 'vol24h')):
        if x.get(b_) is None and x.get(a_) is not None:
            x[b_] = x[a_]
    if c.get('stage') == 'curve' and c.get('curve') is not None:
        x['curvePct'] = c.get('curve')
    if c.get('bundled') is not None and x.get('bundledN') is None and x.get('scanned') is True:
        x['bundledN'] = c.get('bundled')
    jf_ = (rs._jup_facts.get(m) or (0, None))[1]
    return rs._ja.read_for_lens(lens, jf_, x) if lens else rs._ja.pick_read(jf_, x)


def _up_vital(u):
    """A Coming up row + 🫀 its vital and, for a coin under 6h / a trench coin, 🗑 the degen read."""
    rs = _rs()
    jf = (rs._jup_facts.get(u.get('mint')) or (0, None))[1]
    out = {**u, 'vital': rs._ja.verdict(jf, u)} if jf else dict(u)
    tv = rs._read_for(u)
    if tv:
        out['tv'] = tv
    return out


def _pump_links_put(mint, prof):
    rs = _rs()
    out = {}
    for ln in (prof or {}).get('links') or []:
        k = {'x': 'x', 'twitter': 'x', 'website': 'site', 'telegram': 'tg'}.get(str(ln.get('type') or '').lower())
        u = str(ln.get('url') or '')
        if k and u.startswith(('http://', 'https://')) and k not in out:
            out[k] = u
    if len(rs._PUMP_LINKS) > 4000:
        rs._PUMP_LINKS.clear()
    rs._PUMP_LINKS[mint] = (rs.time.time(), out)


async def _pump_links_warm(mints):
    """🔗 Read Pump's coin record for up to PUMP_LINKS_PER_PASS coins not cached in the last hour (3 at a time) — the socials the
    creator set at launch. Lists then show them (cache only, never a fetch per row)."""
    rs = _rs()
    import launchpad_board as _lb
    todo = [m for m in dict.fromkeys(mints or []) if m and (m not in rs._PUMP_LINKS or rs.time.time() - rs._PUMP_LINKS[m][0] > rs.PUMP_LINKS_TTL)][:rs.PUMP_LINKS_PER_PASS]
    if not todo:
        return 0
    sem = rs.asyncio.Semaphore(3)
    async with rs.httpx.AsyncClient(timeout=6, headers={'User-Agent': 'Mozilla/5.0'}) as http:
        async def one(m):
            async with sem:
                try:
                    r = await http.get(f'https://frontend-api-v3.pump.fun/coins-v2/{m}')
                    rs._pump_links_put(m, _lb.pump_profile(r.json() if r.status_code == 200 else None, rs.time.time() * 1000))
                except Exception:
                    pass
        await rs.asyncio.gather(*[one(m) for m in todo])
    return len(todo)


def _clean_rows(rows):
    """🧼 + 🧬 on every pick row: holder facts from the scan cache and the 10-point clean score (cache reads only, never a fetch).
    + 🫀 `vital` (jup_audit.verdict: grade, 3 deciding facts, 4 bars) and 👥 `crew` from Jupiter's audit when it has been read."""
    rs = _rs()
    cmap_ = rs._cand_map()
    for r in rows or []:
        m = r.get('baseAddress') or r.get('mint')
        if not m:
            continue
        r.update(rs._holder_facts(m))
        hit = rs._intel_cache.get(m)
        it = hit[1] if hit else {}
        rep = None
        if (it or {}).get('creator'):
            try:
                rep = rs._quick_rep(it['creator']).get('level')
            except Exception:
                rep = None
        r['clean'] = rs._clean.score(r, it if (it or {}).get('top10Pct') is not None else {}, rep)
        jf = (rs._jup_facts.get(m) or (0, None))[1]
        c_s = cmap_.get(m) or {}
        for k_ in ('site', 'x', 'tg'):   # 🔗 socials on every list row (they were on 0 of 250 trench rows): the row's own, the runner board's, else Jupiter's
            if not r.get(k_):
                v_ = (jf or {}).get(k_) or (rs._PUMP_LINKS.get(m) or (0, {}))[1].get(k_) or c_s.get(k_)   # Jupiter's / Pump's are real links; the board may only know it exists (True)
                if v_:
                    r[k_] = v_
        if jf:
            r['vital'] = rs._ja.verdict(jf, r)
            r['crew'] = r['vital'].get('crew')
        tv_ = rs._read_for(r, cmap_)   # 🎢 curve · 🧲 dip · 🔥 new coin — the read that fits it
        if tv_:
            r['tv'] = tv_
            r['holders'] = r.get('holders') or (jf or {}).get('holders')
    return rows


def _holder_facts(mint):
    """Holder facts for a picker row from the scan CACHE only (never a fetch): top-10 · dev · insiders · bundled / sniper wallets, or scanned=False."""
    rs = _rs()
    hit = rs._intel_cache.get(mint)
    it = hit[1] if hit else None
    if not it or it.get('top10Pct') is None:
        jf = (rs._jup_facts.get(mint) or (0, None))[1]
        if jf and jf.get('top10') is not None:   # 🧪 our scan has not landed: Jupiter's audit is the holder reading (insiders / bundles unknown)
            return {'scanned': 'jup', 'top10': round(rs._fuse._f(jf['top10']), 1), 'dev': jf.get('devPct'), 'insiders': None, 'bundledN': None, 'snipersN': None}
        return {'scanned': False}
    cnt = lambda v: len(v) if isinstance(v, list) else (None if v is None else int(rs._fuse._f(v)))
    return {'scanned': True, 'top10': it.get('top10Pct'), 'dev': it.get('devHoldingPct'), 'insiders': it.get('insidersHoldingPct'),
            'bundledN': cnt(it.get('bundledWallets')), 'snipersN': cnt(it.get('sniperWallets')), 'bundledPct': it.get('bundledHoldingPct')}


def _list_now(key, ttl, rebuild):
    """Stale-while-revalidate for the pick lists (trench 2–7s, open gates 2–3s to build): → the cached answer when it may be served
    (fresh, or stale with ONE background rebuild started), else None = the caller builds it now. `rebuild` = a coroutine factory
    that runs the same route; inside it this returns None so the route really builds and stores."""
    rs = _rs()
    if rs._LIST_REBUILD.get() or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return None
    hit = rs._disc_cache.get(key)
    if not hit:
        return None
    age = rs.time.time() - hit[0]
    if age < ttl:
        return hit[1]
    if age >= rs.LIST_STALE_SEC:
        return None
    t = rs._list_flight.get(key)
    if t is None or t.done():
        async def run():
            rs._LIST_REBUILD.set(True)
            try:
                await rebuild()
            except Exception as e:
                print('list rebuild:', key, str(e)[:120])
        rs._list_flight[key] = rs.asyncio.create_task(run())
        if len(rs._list_flight) > 200:
            for k in [k for k, v in rs._list_flight.items() if v.done()]:
                rs._list_flight.pop(k, None)
    return hit[1]


def _with_tv(r):
    """The row with its trench read (`tv`): raw open-board rows carry none — "no read = not judged" let a busted read through."""
    rs = _rs()
    if (r or {}).get('tv') or not (r or {}).get('mint'):
        return r
    try:   # the SAME read the open list shows (jup_audit.open_read: curve · dip · flow · trench, whichever fits)
        c_ = rs._cand_map().get(r['mint']) or {}
        x_ = {**{k: c_.get(k) for k in ('vol5m', 'chg6h', 'chg24h') if c_.get(k) is not None}, **{k: v for k, v in r.items() if v is not None}}
        return {**r, 'tv': rs._ja.open_read((rs._jup_facts.get(r['mint']) or (0, None))[1], x_)}
    except Exception:
        return r


def _bangers(mine, cool, mom, lq, floor, now, gate=False):
    """🚀 BANGERS for the real card's open seats, best first: 🎯 a proven caller's fresh call (≤ 15 min, near the called cap) → 🔥 the
    TOP 3 (busiest safe coins) → 🧊 cooling off (DRYING UP / COOLING). Every one: real-buy pool floor, not on the card, not cooling,
    not dollar-named, not falling right now, no busted read / rug meter 50+. Each carries `tag` (shown as the coin's 'why it bought')."""
    rs = _rs()
    try:
        open_ = [rs._with_tv(x) for x in rs._open_board()]
        src = [(r, '🎯 proven caller') for r in rs._pc.pro_entries(rs._pump_calls.get('calls') or [], rs._pump_calls.get('callers') or {}, open_, now * 1000)]
        if rs._prebreak_ready():   # 🌅 before the break — joins the doors once its own record is positive (10+ settled)
            src += [(r, '🌅 pre-break') for r in rs._prebreak_rows()]
        if rs._wave_ready():   # 🌊 narrative leaders join the doors only once their own record is positive (10+ settled)
            src += [(r, '🌊 narrative leader') for r in rs._wave_rows()]
        src += [(r, '🔥 top 3') for r in rs._prime.top_three((rs._contenders_cache.get('data') or {}).get('divisions'), mine, cool)]
        src += [(r, '🧊 cooling off') for r in rs._exhale_rows()]
    except Exception:
        return []
    out, seen = [], set(mine or ()) | set(cool or ())
    for r, tag in src:
        m = r.get('mint')
        if not m or m in seen or lq(r) < floor or rs._fuse._f(r.get('price')) <= 0 or rs._fw.dollar_named(r.get('symbol')) or not rs._prime.entry_ok(r, mom) or not rs._prime.trench_read_ok(rs._with_tv(r)):
            continue
        if gate and rs._prime.entry_gate(r, mom):   # 🎯 clean entries: the banger doors (🔥 top 3 = the busiest = often the top) obey it too
            continue
        seen.add(m)
        out.append({**r, 'tag': tag})
    return out[:8]


def _wave_rows():
    """🌊 NARRATIVE LEADERS: the original coin of every ticker wave spiking today (meme_terms.wave_leaders) — site / X set, safe, still
    trading, rug meter < 50, no busted read."""
    rs = _rs()
    try:
        trend = rs._mt.trending(rs._json_load(rs.MEME_PATH, {}), rs.time.time())
    except Exception:
        return []
    out = []
    raw = [rs._with_tv(x) for x in rs._open_board()]
    open_tv = {x.get('mint'): x.get('tv') for x in raw}   # the open list's read — the safety check must pass it AND the picker read
    for r in rs._mt.wave_leaders(trend, rs._clean_rows([dict(x) for x in raw])):   # _clean_rows fills site / X (raw rows have none)
        if rs._prime.trench_read_ok(r) and rs._prime.trench_read_ok({'tv': open_tv.get(r.get('mint'))}) and rs._fuse._f(r.get('price')) > 0:
            w = r['wave']
            out.append({**r, 'baseAddress': r['mint'], 'priceUsd': r.get('price'), 'liquidityUsd': r.get('liq'),
                        'divisionLabel': f"🌊 the original of the \"{w['term']}\" wave — {w['today']} coins named after it today, this one leads"})
    return out


def _prebreak_rows():
    """🌅 BEFORE THE BREAK: runner-board coins that pass every SAFETY gate, are a clean entry (buyers 60%+, not chasing, not at highs,
    $50K+ pool, 6h+, $200K+/h) and whose 5-min volume is waking up (≥ 1.5× the hour's pace) while the price is still calm."""
    rs = _rs()
    rcfg = rs._runner_cfg()
    out = []
    for r in list(rs._runner_cands):
        try:
            if rs._rn.safety_fails(r, rcfg) or rs._fuse._f(r.get('price')) <= 0 or not r.get('pairAddress'):
                continue
        except Exception:
            continue
        if rs._prime.pre_break(r) and not rs._prime.entry_gate(r):
            pace = rs._fuse._f(r.get('vol5m')) * 12 / max(1.0, rs._fuse._f(r.get('vol1h')))
            out.append({**r, 'baseAddress': r.get('mint'), 'priceUsd': r.get('price'), 'liquidityUsd': r.get('liq'),
                        'divisionLabel': f"🌅 volume waking: 5-min pace {pace:.1f}× the hour, buyers {rs._fuse._f(r.get('buyShare')):.0f}%, {rs._fuse._f(r.get('chg1h')):+.0f}% 1h"})
    return sorted(out, key=lambda r: -rs._fuse._f(r.get('vol5m')))


def _prebreak_ready():
    rs = _rs()
    rec = (rs._list_records() or {}).get('prebreak') or {}
    return int(rec.get('n') or 0) >= rs.WAVE_PROVE_MIN and rs._fuse._f(rec.get('medPct')) > 0


def _wave_ready():
    rs = _rs()
    rec = (rs._list_records() or {}).get('wave') or {}
    return int(rec.get('n') or 0) >= rs.WAVE_PROVE_MIN and rs._fuse._f(rec.get('medPct')) > 0


def _exhale_rows():
    """🧊 COOLING OFF: launch coins that ran and are now exhaling — read DRYING UP or COOLING, passed the safety scan, rug meter < 50,
    a site or X set, and real volume (organic ≥ 10% when Jupiter has read it). Owner, 2026-10-09: "IBM is a wash rug" — it read DRYING
    UP with no site and no X."""
    rs = _rs()
    raw = [rs._with_tv(x) for x in rs._open_board()]
    open_tv = {x.get('mint'): x.get('tv') for x in raw}
    out = []
    for r in rs._clean_rows([dict(x) for x in raw]):
        r = {**r, 'tv': open_tv.get(r.get('mint')) or r.get('tv')}
        call = ((r.get('tv') or {}).get('call') or [None, None])[1]
        org = (r.get('vital') or {}).get('organicPct')
        if org is not None and rs._fuse._f(org) < rs.EXHALE_ORGANIC_MIN:
            continue
        if not (r.get('site') or r.get('x')):
            continue
        if call in rs.EXHALE_READS and r.get('safe') and rs._prime.trench_read_ok(r) and rs._fuse._f(r.get('price')) > 0:
            out.append({**r, 'baseAddress': r['mint'], 'priceUsd': r.get('price'), 'liquidityUsd': r.get('liq'),
                        'divisionLabel': f"🧊 {call.lower()} after its run — {rs._fuse._f(r.get('chg1h')):+.0f}% 1h, {rs._fuse._f(r.get('chg5m')):+.0f}% 5m"})
    return sorted(out, key=lambda r: (rs.EXHALE_READS.index(r['tv']['call'][1]), -rs._fuse._f(r.get('vol1h'))))


def _procall_rows():
    """🎯 PROVEN CALLERS: the last hour's calls by callers who were right before, on safe coins still near the called cap."""
    rs = _rs()
    rows = rs._pc.pro_entries(rs._pump_calls.get('calls') or [], rs._pump_calls.get('callers') or {}, [rs._with_tv(x) for x in rs._open_board()], rs.time.time() * 1000, max_min=60)
    return [{**r, 'baseAddress': r['mint'], 'priceUsd': r.get('price'), 'liquidityUsd': r.get('liq'),
             'divisionLabel': f"🎯 @{r['proCall']['user']} called it {r['proCall']['mins']:.0f}m ago — their record {r['proCall']['medMult']}× typical, {r['proCall']['wonPct']}% up"}
            for r in rows if rs._prime.trench_read_ok(r)]


def _live_movers():
    """🚀 LIVE MOVERS (owner, 2026-10-09: "tabs showing true data and real movers"): what is moving in the LAST 5 MINUTES on real money —
    ≥ $3K traded in those 5 min, up ≥ 3%, buyers ≥ 50%, 60+ trades an hour, a safety scan that did not fail — straight from the live
    feed, ranked by 5-min $ × move. Each row says the move and the money behind it. Its own 1h record is kept like every list."""
    rs = _rs()
    out = []
    for r in [rs._with_tv(x) for x in rs._open_board() or []]:
        v5, c5, bs = rs._fuse._f(r.get('vol5m')), rs._fuse._f(r.get('chg5m')), r.get('buyShare')
        if r.get('safe') is False or rs._fuse._f(r.get('price')) <= 0 or v5 < rs.LIVE_MIN_VOL5M or c5 < rs.LIVE_MIN_CHG5M or int(r.get('txns1h') or 0) < rs.LIVE_MIN_TX1H:
            continue
        if bs is not None and rs._fuse._f(bs) < rs.LIVE_MIN_BUY:
            continue
        out.append({**r, 'baseAddress': r['mint'], 'priceUsd': r.get('price'), 'liquidityUsd': r.get('liq'), 'live': round(v5 * min(c5, 60.0)),
                    'divisionLabel': f"🚀 {c5:+.0f}% in 5m on ${v5 / 1000:.1f}K traded · {rs._fuse._f(bs):.0f}% buys" + ('' if r.get('safe') else ' · ❔ not scanned')})
    return rs._clean_rows(sorted(out, key=lambda r: -r['live'])[:60]) or []


async def _why_pair(mint):
    """The coin's market pair: DexScreener's deepest pool, else Jupiter's (same shape)."""
    rs = _rs()
    import launchpad_board as _lb
    best = None
    try:
        r = await rs._ai_http().get(f'https://api.dexscreener.com/tokens/v1/solana/{mint}', timeout=8)
        if r.status_code == 200 and isinstance(r.json(), list):
            ps = [x for x in r.json() if (x.get('baseToken') or {}).get('address') == mint]
            best = max(ps, key=lambda x: rs._fuse._f((x.get('liquidity') or {}).get('usd')), default=None)
    except Exception:
        pass
    if best is None:
        try:
            best = await _lb.jup_lookup(rs._ai_http(), mint)
        except Exception:
            best = None
    return best


async def _why_build(mint):
    """❓ One coin's WHY: our read + its live pair + Pump callers + web / X search + the two best pages → the model's story (every driver cites
    a source from the case) or, when no model answers, the engine's own drivers from the numbers."""
    rs = _rs()
    import why_pump as _wp, feeless_mcp as _mcp, fee_voice as _fv
    try:
        read = await rs.coin_read(mint)
    except Exception:
        read = {}
    pair = await rs._why_pair(mint)
    n = _wp.from_pair(pair, _wp.numbers(read))
    soc = _wp.socials_of(pair)
    sym = n.get('symbol')
    qs = [f'"{mint}"'] + ([f'${sym} solana crypto', f'site:x.com ${sym}'] if sym else [])
    web = []
    try:
        res = await rs.asyncio.wait_for(rs.asyncio.gather(*[rs.asyncio.to_thread(_mcp._search_rows, q, 6) for q in qs], return_exceptions=True), timeout=12)
        seen = set()
        for rows in res:
            for w in (rows if isinstance(rows, list) else []):
                if w.get('url') and w['url'] not in seen:
                    seen.add(w['url']); web.append(w)
    except Exception:
        pass
    pages = []
    try:
        pick = [x['url'] for x in _fv.pick_sources(web, 2)] + ([soc['site']] if soc.get('site') else [])
        pages = await rs.asyncio.wait_for(rs.asyncio.to_thread(_mcp._read_many, pick[:3], 1200), timeout=10) if pick else []
    except Exception:
        pages = []
    eng = _wp.engine_drivers(n)
    model, src = None, None
    if not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        try:
            pk = _wp.packet(n, eng, web, pages)
            r_ = await rs.asyncio.wait_for(rs._air.ROUTER.ask(rs._ai_http(), rs.os.environ, rs._ai_cfg(), 'Why did it move? Answer the JSON.', context=pk, role='owner',
                                                        system=_wp.WHY_ASK, only_system=True, tune={'temp': 0.2, 'maxTok': 900}), timeout=60)
            model = _wp.parse(r_.get('text'), [w.get('url') for w in web] + [u for u, _t, _x in pages])
            src = r_.get('source') if model else None
        except Exception:
            model = None
    out = {**_wp.answer(n, eng, model, web), 'mint': mint, 'socials': soc, 'pair': (pair or {}).get('pairAddress'), 'model': src, 'at': round(rs.time.time())}
    rs._why_cache[mint] = (rs.time.time(), out)
    rs._why_recent[:] = ([{'mint': mint, 'symbol': sym, 'headline': out['headline'], 'verdict': out['verdict'], 'move': out['move'], 'img': n.get('img'), 'at': out['at']}]
                      + [x for x in rs._why_recent if x['mint'] != mint])[:20]
    return out


def _swap_clean(rows):
    """🧹 The ⇄ hand swap's candidates (owner, 2026-10-09: "the auto swap button pulls BS coins — rug-worthy / washed"): the engine's own
    🏆 Best list first (every door, clean entry, tape-checked), then only coins whose read is not a busted / wash / blow-off / down-trend
    call, whose rug meter is < 50, that are alive and a clean entry (not chasing, not at its highs, sellers not leading), busiest first.
    Nothing clean → the list is empty and the swap says so (never the biggest pump)."""
    rs = _rs()
    best_ = [x.get('mint') for x in rs._best_rows]
    out = []
    for x in rows or []:
        m = x.get('mint')
        if m in best_:
            out.append((0, best_.index(m), x)); continue
        tv = (rs._with_tv({**x, 'mint': m}) or {}).get('tv') or {}
        call = ((tv.get('call') or [None, None])[1])
        if call in rs.SWAP_BAD_READS or call in rs._prime.TRENCH_BAD_READS or rs._fuse._f(tv.get('rug')) >= rs._prime.TRENCH_RUG_MAX or rs._ja.dead_why(x) or rs._prime.entry_gate(x, None, core=True):
            continue
        out.append((1, -rs._fuse._f(x.get('vol1h')), x))
    return [x for *_k, x in sorted(out, key=lambda t: (t[0], t[1]))]


async def _fuses_discover_raw(lens, chain):
    """Fuse Lab: browse real pools on the chain you're on, by lens (popular / yield / deep / new)."""
    rs = _rs()
    if lens == 'exhale':
        return {'lens': 'exhale', 'chain': 'solana', 'pools': rs._exhale_rows()}
    if lens == 'best':   # 🏆 the engine's own pick list (every door, clean entry, tape-checked) — what an open seat takes next
        if rs._best_rows:
            return {'lens': 'best', 'chain': 'solana', 'pools': [{**x, 'baseAddress': x.get('mint'), 'priceUsd': x.get('price'), 'liquidityUsd': x.get('liq'),
                                                                   'divisionLabel': x.get('tag')} for x in rs._best_rows]}
        # nothing clears the engine's full line right now → the evidence ranking (🧬 edge: every list's own record + the read's record),
        # with live numbers from the runner board — never an empty tab
        cm_ = rs._cand_map()
        rows_ = []
        for x in (rs._edge_rank_cache.get('rows') or [])[:20]:
            c_ = cm_.get(x.get('mint')) or {}
            rows_.append({**x, **{k: c_.get(k) for k in ('liq', 'chg5m', 'chg1h', 'vol1h', 'ageH', 'buyShare', 'mcap') if c_.get(k) is not None},
                          'liquidityUsd': c_.get('liq'), 'priceUsd': x.get('priceUsd') or c_.get('price'),
                          'divisionLabel': f"🧬 evidence {rs._fuse._f((x.get('edge') or {}).get('edge')):+.1f}%/1h — nothing clears the engine's full line right now"})
        return {'lens': 'best', 'chain': 'solana', 'pools': rows_}
    if lens == 'wave':
        return {'lens': 'wave', 'chain': 'solana', 'pools': rs._wave_rows()}
    if lens == 'prebreak':
        return {'lens': 'prebreak', 'chain': 'solana', 'pools': rs._prebreak_rows()}
    if lens == 'procall':
        return {'lens': 'procall', 'chain': 'solana', 'pools': rs._procall_rows()}
    if lens == 'brain':
        return {'lens': 'brain', 'chain': 'solana', 'pools': rs._brain_rows()}
    if lens == 'live':
        return {'lens': 'live', 'chain': 'solana', 'pools': rs._live_movers()}
    if lens == 'fresh':   # 🔄 NEW TO YOU (owner, 2026-10-08: "no new coins, I'm running in circles — cycle different coins from the Arena and FEELESS
        # sitewide"): every list FEELESS shows (Pump trending · movers · Pump live · volume · dips · the Arena's ranked coins) woven together one
        # coin from each in turn, MINUS every coin the real card bought, sold or holds in the last 24h. Safety facts ride on every row as usual.
        now_ = rs.time.time()
        touched = {r.get('mint') for r in (rs._fw_peek().get('ledger') or []) if now_ - rs._fuse._f(r.get('at')) < 86400 and r.get('status') in ('filled', 'confirmed', 'sent', None)}
        for c_ in rs._prime_cards().values():
            if c_.get('real'):
                touched |= {l.get('mint') for l in c_.get('legs') or []}
        srcs = await rs.asyncio.gather(*[rs._fuses_discover_raw(k, chain) for k in ('ptrend', 'movers', 'pump', 'volume', 'bottom')], return_exceptions=True)
        lists = [list((x or {}).get('pools') or []) if isinstance(x, dict) else [] for x in srcs]
        try:
            arena_ = (await rs._contenders_build()).get('all') or []
        except Exception:
            arena_ = []
        lists.append([{**r, 'baseAddress': r.get('mint') or r.get('baseAddress')} for r in arena_ if not r.get('watch')])
        tags = ['🔥 Pump trending', '🚀 Movers', '🆕 Pump live', '🌊 Volume', '🟢 Dips', '🏁 Arena']
        out_, seen_ = [], set(touched)
        for i in range(max((len(x) for x in lists), default=0)):
            for k, rows_ in enumerate(lists):
                if i < len(rows_):
                    r = rows_[i]; m = r.get('baseAddress') or r.get('mint') or (r.get('baseToken') or {}).get('address')
                    if m and m not in seen_:
                        seen_.add(m); out_.append({**r, 'baseAddress': m, 'from': tags[k]})
        return {'lens': 'fresh', 'chain': 'solana', 'pools': out_[:300], 'skipped': len(touched)}
    if lens == 'stocks':   # 📈 tokenized stocks in real Solana pools (a subset of the majors rows)
        return {'lens': 'stocks', 'chain': 'solana', 'pools': [x for x in await rs._majors_rows() if x.get('stock')]}
    if lens == 'majors':   # 🪙 the REAL SOL / BTC / ETH / … on Solana (hard-coded mints), deepest pool each
        return {'lens': 'majors', 'chain': 'solana', 'pools': await rs._majors_rows()}
    if lens == 'risers':   # 🚀 new majors: young coins that arrived big with real volume
        base_ = await rs._fuse_discover_pairs('solana')
        rs_ = rs._fuse.risers(base_, rs.time.time() * 1000)
        try:   # 🟢 + Pump's top 15 graduated coins (trending pump board), never duplicated
            async with rs.httpx.AsyncClient(timeout=8) as http:
                pump_ = (await http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': 'trending', 'chain': 'solana', 'page': 1, 'scope': 'pump'})).json().get('pairs') or []
        except Exception:
            pump_ = []
        have_ = {(r.get('baseToken') or {}).get('address') or r.get('baseAddress') for r in rs_}
        return {'lens': 'risers', 'chain': 'solana', 'pools': rs_ + rs._fuse.pump_majors(pump_ + base_, have_)}
    if lens == 'bottom':   # 🟢 Buy bottom: coins far under their high, at the low of their range, no longer sliding
        rows_b = await rs._bottom_rows(rs.time.time())
        try:   # 📉 + today's dip buys (the Gauntlet's own division) in the SAME list — one tab, not two
            have_b = {r.get('baseAddress') for r in rows_b}
            dips_ = next((dv.get('rows') or [] for dv in ((await rs._contenders_build()).get('divisions') or []) if dv.get('key') == 'dip'), [])
            rows_b = list(rows_b) + [{**r, 'divisionLabel': f"📉 dip buy{' · watch' if r.get('watch') else ''}: down on the day, buyers back"} for r in dips_ if r.get('mint') not in have_b]
        except Exception:
            pass
        return {'lens': 'bottom', 'chain': 'solana', 'pools': rows_b, 'proof': rs._trench.meta_proof(rs._json_load(rs.BOTTOM_PROOF_PATH, {}), keys=('bottom',)).get('bottom')}
    if lens == 'calls':   # 📣 the coins Pump's own users are calling out, loudest first
        return {'lens': 'calls', 'chain': 'solana', 'pools': await rs._pump_call_rows()}
    if lens == 'double':   # 🔥🔥 called out AND fed — the overlap of the two Pump signals
        return {'lens': 'double', 'chain': 'solana', 'pools': await rs._double_rows()}
    if lens == 'fed':   # 🧲 runners new Pump launches are paired with — every buy of those coins routes through the runner's pool
        return {'lens': 'fed', 'chain': 'solana', 'pools': await rs._feeder_rows()}
    feed_lens = lens if lens in ('pump', 'movers', 'volume', 'ptrend') else None   # 🆕 New launches (newest first) · 🚀 Movers · 🌊 Volume (busiest first): one live launch feed
    if feed_lens:
        mv_ = lens == 'movers'
    if feed_lens:   # 🆕 Pump live: the newest + busiest Pump coins RIGHT NOW, launch-curve coins included (owner picks only)
        try:
            async with rs.httpx.AsyncClient(timeout=10) as http:
                got_ = await rs.asyncio.gather(*[http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': k, 'chain': 'solana', 'page': pg, 'scope': 'launchpads'})
                                              for k in ('new', 'trending') for pg in (1, 2, 3, 4, 5, 6)], return_exceptions=True)
            raw_ = [x for g in got_ if not isinstance(g, Exception) for x in (g.json().get('pairs') or [])]
        except Exception:
            raw_ = []
        seen_p, rows_p = set(), []
        for p_ in sorted((rs._fuse.with_curve(x) for x in raw_), key=lambda x: -rs._fuse._f((x.get('volume') or {}).get('h1'))):
            m_ = (p_.get('baseToken') or {}).get('address')
            if not m_ or m_ in seen_p or rs._fuse._f(p_.get('priceUsd')) <= 0 or rs._fuse._f((p_.get('volume') or {}).get('h1')) < 1000 or rs._fuse._f((p_.get('liquidity') or {}).get('usd')) < 5000:
                continue
            seen_p.add(m_)
            age_ = round((rs.time.time() * 1000 - rs._fuse._f(p_.get('pairCreatedAt'))) / 3.6e6, 1) if p_.get('pairCreatedAt') else None
            v1_ = rs._fuse._f((p_.get('volume') or {}).get('h1'))
            rows_p.append({'chainId': 'solana', 'pairAddress': p_.get('pairAddress'), **rs._fuse.leg_meta(p_), **({'curve': True} if p_.get('curve') else {}), 'ageH': age_, 'vol1h': v1_,
                           **({'pumpTrend': p_['pumpTrend']} if p_.get('pumpTrend') else {}),
                           # shown under the ticker: how old it is and how hard it trades — what tells one list's coin from another's
                           'divisionLabel': f"{'?' if age_ is None else f'{age_ * 60:.0f}m' if age_ < 1 else f'{age_:.0f}h' if age_ < 48 else f'{age_ / 24:.0f}d'} old · ${v1_ / 1000:,.0f}K/h"})
        if mv_:   # 🚀 MOVERS: up ≥ 10% on the hour on ≥ $20K traded in a ≥ $10K pool, biggest hourly move first; no dollar-named tickers
            rows_p = sorted((r for r in rows_p if r['vol1h'] >= 20000 and rs._fuse._f(r.get('liquidityUsd')) >= 10000 and rs._fuse._f(r.get('change1h')) >= 10
                             and not rs._fw.dollar_named(r.get('symbol'))), key=lambda r: -rs._fuse._f(r.get('change1h')))
            return {'lens': 'movers', 'chain': 'solana', 'pools': rows_p[:150]}
        if lens == 'ptrend':   # 🔥 Pump's own Trending tab, in Pump's order (refreshed every 10 min)
            rows_p = sorted((r for r in rows_p if r.get('pumpTrend')), key=lambda r: r['pumpTrend'])
            for r in rows_p:
                r['divisionLabel'] = f"🔥 Pump #{r['pumpTrend']} · {r['divisionLabel']}"
            return {'lens': 'ptrend', 'chain': 'solana', 'pools': rows_p[:150]}
        if lens == 'pump':   # 🆕 newest first (≤ 48h old; unknown age last)
            rows_p = sorted((r for r in rows_p if r.get('ageH') is None or r['ageH'] <= 48), key=lambda r: (r.get('ageH') is None, r.get('ageH') or 0))
        return {'lens': lens, 'chain': 'solana', 'pools': rows_p[:300]}   # 🌊 owner: "more than 80 — flood with coins"
    lens = lens if lens in rs._fuse.LENSES else 'popular'
    return {'lens': lens, 'chain': chain, 'pools': rs._fuse.discover(await rs._fuse_discover_pairs(chain), lens, chain, now_ms=rs.time.time() * 1000)}


async def _majors_rows():
    rs = _rs()
    if rs._majors_cache['rows'] and rs.time.time() - rs._majors_cache['at'] < 120:
        return rs._majors_cache['rows']
    by, by_s = {}, {}
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            async def batch(table):
                return (await http.get(f"https://api.dexscreener.com/tokens/v1/solana/{','.join(table)}")).json() or []
            got_m, got_s = await rs.asyncio.gather(batch(rs._fuse.MAJORS), batch(rs._fuse.STOCKS), return_exceptions=True)   # 📈 stocks = their own batch (≤ 30 mints a call)
            if isinstance(got_m, Exception):
                raise got_m
            for p in got_m:
                by.setdefault((p.get('baseToken') or {}).get('address'), []).append(p)
            for p in ([] if isinstance(got_s, Exception) else got_s):
                by_s.setdefault((p.get('baseToken') or {}).get('address'), []).append(p)
    except Exception:
        by, by_s = {}, {}
    # 📡 a major / stock DexScreener left out (outage answered `pairs: null` for everything on 2026-10-07) → Jupiter's data, same shape
    miss = [m for m in list(rs._fuse.MAJORS) + list(rs._fuse.STOCKS) if m not in by and m not in by_s]
    if miss:
        toks = await rs._jup_tokens(miss)
        for m in miss:
            jp = rs._launchpad_board.jup_pair(toks.get(m)) if toks.get(m) else None
            if jp:
                (by_s if m in rs._fuse.STOCKS else by).setdefault(m, []).append(jp)
    rows = rs._fuse.majors_pools(by) + rs._fuse.majors_pools(by_s, rs._fuse.STOCKS)
    if not rows:
        return rs._majors_cache['rows']   # never replace a good list with an empty one
    rs._majors_cache.update(at=rs.time.time(), rows=rows)
    return rows


def _is_admin_req(request):
    rs = _rs()
    try:
        rs._require_admin(request)
        return True
    except Exception:
        return False

