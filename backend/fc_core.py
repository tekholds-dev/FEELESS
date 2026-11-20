"""🧹 Brains, learning, swap helpers — moved whole out of feecat_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches feecat_service still
reaches it, and every function here is still reachable on feecat_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import feecat_service
    return feecat_service


def _pev_watch(items):
    """🧾 COL-3: files what a save changed in any proof. Log only: a busy or broken event file never stops or slows a save more than its short lock."""
    rs = _rs()
    try:
        path = rs.DATA_DIR / rs._pev.DB_NAME
        w = rs._PEV_W.get(str(path)) or rs._PEV_W.setdefault(str(path), rs._pev.Watcher(path))
        w.watch(items() if callable(items) else items)
    except Exception as e:   # noqa: BLE001: the record must never cost a proof
        if rs.time.time() - rs._PEV_ERR[0] > 60:
            rs._PEV_ERR[0] = rs.time.time(); print(f'[proof-events] not filed this time: {type(e).__name__}: {e}', flush=True)


def _empty_store():
    return {'cats': {}, 'events': []}


def honest_brain(cat):
    """✂ A cat saved under the retired catalog (a 'GPT-6 Astra' label that only ran the rule engine) reads as what it is. Pure (tests)."""
    rs = _rs()
    if cat.get('brainsCfg') or cat.get('modelBrain') or cat.get('isLeader') or cat.get('brain') == rs.RULE_ENGINE['id']:
        return cat
    cat.update(brain=rs.RULE_ENGINE['id'], brainLabel=rs.RULE_ENGINE['label'],
               brainProfile={**(cat.get('brainProfile') or {}), 'provider': rs.RULE_ENGINE['provider'], 'status': 'live', 'available': False})
    return cat


def _kb_remember(cat, row):
    rs = _rs()
    if row and row.get('id'):
        rs._KB_LEDGER.setdefault(cat['id'], {})[row['id']] = rs.json.loads(rs.json.dumps(row))


def _kb_merge(store):
    rs = _rs()
    for cid, rows in rs._KB_LEDGER.items():
        c = (store.get('cats') or {}).get(cid)
        if not c:
            continue
        have = {(b or {}).get('id') for b in c.get('kalshiBids') or []}
        miss = [r for i, r in rows.items() if i not in have]
        if miss:
            c['kalshiBids'] = (list(c.get('kalshiBids') or []) + [rs.json.loads(rs.json.dumps(r)) for r in miss])[-100:]
        for f in c.get('pobFolders') or []:
            tk = f.get('kalshi') if isinstance(f.get('kalshi'), dict) else None
            r = rows.get((tk or {}).get('id'))
            if r and tk.get('status') == 'waiting':
                tk.update({k: r.get(k) for k in ('status', 'orderId', 'count', 'price', 'usd', 'filled', 'why', 'kalshiStatus') if r.get(k) is not None})


def keep_owned(cat):
    """Remember the owner's fields of `cat` as they stand now (after an owner's action)."""
    rs = _rs()
    rs._KEPT[cat['id']] = rs.json.loads(rs.json.dumps({k: cat[k] for k in rs.OWNER_KEYS if k in cat}))


def _save(store: dict):
    rs = _rs()
    path_key = str(rs.STORE_PATH)
    for (path, cid), cat in rs._NEW_CATS.items():
        if path == path_key:
            store.setdefault('cats', {}).setdefault(cid, rs.json.loads(rs.json.dumps(cat)))
    for path, cid in rs._DELETED_CATS:
        if path == path_key:
            store.setdefault('cats', {}).pop(cid, None)
    rs._kb_merge(store)   # 🔒 a real bid's ledger row survives any older copy's save
    if getattr(rs, '_fc_clips', None):   # 🔒 Slice 15: a clip run's progress and its filed clip PoCs survive an older copy's save
        rs._fc_clips.merge(store)
    for cid, kept in rs._KEPT.items():
        c = (store.get('cats') or {}).get(cid)
        if not c:
            continue
        have = {x.get('sig') for x in c.get('creditPaid') or []}
        for x in kept.get('creditPaid') or []:   # bought credit an old copy has not seen: added, never lost
            if x.get('sig') not in have and c.get('brainsCfg'):
                c['brainsCfg']['credit'] = round((c['brainsCfg'].get('credit') or 0) + float(x.get('usd') or 0), 6); c.pop('brainPaused', None)
        for k in rs.OWNER_KEYS:
            if k in kept:
                c[k] = rs.json.loads(rs.json.dumps(kept[k]))
            else:
                c.pop(k, None)
    # Readers include the live agent loops. Never let one read a half-written JSON file and mistake it for an empty store.
    tmp = rs.STORE_PATH.with_name(f'{rs.STORE_PATH.name}.{rs.uuid.uuid4().hex}.tmp')
    try:
        fd = rs.os.open(tmp, rs.os.O_WRONLY | rs.os.O_CREAT | rs.os.O_EXCL, 0o600)
        with rs.os.fdopen(fd, 'w') as fh:
            rs.json.dump(store, fh, indent=2)
            fh.flush(); rs.os.fsync(fh.fileno())
        tmp.replace(rs.STORE_PATH)
    finally:
        tmp.unlink(missing_ok=True)
    rs._pev_watch(lambda: rs._pev.states(store, rs.time.time()))


def public_words(text):
    """🔒 P0-QUICK #4: internal model names (NEXA / OSSY / G4) never reach users — every public sink (events, receipts, Fee's chat posts,
    position reasons on /api/cats/leader) says 'FeeCat AI'. The owner's HQ reads the `nexa` flag instead. Pure (tests)."""
    rs = _rs()
    if not isinstance(text, str):
        return text
    text = rs._ECHO_OLD.sub('', rs._INTERNAL.sub('🔮 FeeCat AI', text))   # receipts written before nexa.real_why still carry her placeholder
    return text.replace('her AI desk', 'FeeCat AI')


def _as_collective(obj):
    """🔒 Every proof and job an owner opens speaks as The Collective (owner 2026-11-07: "users shouldnt know about ossy and g4"). Only words change. Pure (tests)."""
    rs = _rs()
    if isinstance(obj, str):
        return rs._INTERNAL.sub('The Collective', obj) if rs._INTERNAL.search(obj) else obj
    if isinstance(obj, list):
        return [rs._as_collective(x) for x in obj]
    if isinstance(obj, dict):
        return {k: rs._as_collective(v) for k, v in obj.items()}
    return obj


def _collective_names(obj, under=False):
    """🫂 Grades and scores speak as The Collective (owner 2026-11-13: "users should see ossy and g4 scores and grades as The Collective, never
    their individual names"). Inside any review / grade field, OSSY and G4 lose their names, as words AND as keys (a judge keyed 'ossy' becomes
    'collective', the next 'collective-2'), and the model behind each verdict is dropped. Everything else passes untouched. The owner's own
    (staff) agents keep the names: he reviews OSSY and G4 himself. Pure (tests)."""
    rs = _rs()
    if isinstance(obj, list):
        return [rs._collective_names(x, under) for x in obj]
    if isinstance(obj, str):
        return rs._INTERNAL.sub('The Collective', obj) if under and rs._INTERNAL.search(obj) else obj
    if not isinstance(obj, dict):
        return obj
    out, n = {}, 0
    for k, v in obj.items():
        inside = under or k in rs.REVIEW_KEYS
        if inside and k in ('answeredBy', 'families', 'oneFamily'):
            continue
        if inside and isinstance(k, str) and rs._INTERNAL.fullmatch(k.strip()):
            n += 1; k = 'collective' if n == 1 else f'collective-{n}'
        out[k] = rs._collective_names(v, inside)
    return out


def _for_users(cat, obj):
    """The owner's staff agents see the judges by name; every other owner sees The Collective."""
    rs = _rs()
    return obj if (cat or {}).get('ownerStaff') else rs._collective_names(obj)


def _no_keys(obj):
    """🔐 every cat on its way out: the sealed API keys stay on the server — the page gets the drawer (provider · last 4 · wired)."""
    rs = _rs()
    if isinstance(obj, list):
        return [rs._no_keys(x) for x in obj]
    if isinstance(obj, dict):
        out = {k: rs._no_keys(v) for k, v in obj.items() if k not in ('poeFolders', 'gitLink', 'collectiveGit', 'apiKeys', 'logins', 'secrets', 'workNow', 'ownerId', 'ownerWallet', 'recovery', 'siteSessions', 'siteManuals', 'siteBook', 'proofSite', 'watchFolders', 'topup', 'topups', 'topupRead', 'mailbox', 'proofHosts', 'pobAsk', 'siteTrade', 'siteTrades', 'siteTradeAuto', 'siteWallets', 'setup')}
        if obj.get('siteSessions'):   # 🔓 sealed sign-ins never leave the server — site · when · how many cookies only
            out['signedIn'] = [{'site': k, 'at': v.get('at'), 'n': v.get('n', 0)} for k, v in obj['siteSessions'].items()]   # 🔒 ownerId is the owner's control key — it never leaves the server
        if 'brains' in obj:   # ☁ each mind's own cloud is its owner's private notes — only the owner's /work view carries it
            out.pop('minds', None)
        if 'apiKeys' in obj or ('brainsCfg' in obj and 'ownerId' in obj):
            out['apiDrawer'] = rs._ck.public(obj)
        out.pop('recoveryKit', None)   # 🔑 a hash stays on the server too
        out.pop('liveKeys', None)   # 🔴 stream keys never leave the server, sealed or not
        out.pop('nameLock', None)
        if obj.get('logins'):   # 🔐 sealed passwords never leave the server — site · username · when only
            out['logins'] = rs._cv.public_logins(obj)
        return out
    return obj


def _pub(obj):
    """🔒 A public response with every internal model name scrubbed (old events / reasons written before the scrub included)."""
    rs = _rs()
    return rs.json.loads(rs.public_words(rs.json.dumps(rs._no_keys(obj), ensure_ascii=False)))


def _log_event(store, cat, kind, detail, pnl=None, pair=None, price=None, market_cap=None, entry_market_cap=None):
    rs = _rs()
    store['events'].insert(0, {
        'id': rs.uuid.uuid4().hex, 'catId': cat['id'], 'catName': cat['name'],
        'type': kind, 'detail': rs.public_words(detail), 'ts': rs.time.time() * 1000,
        'pnlSol': pnl, 'decisionSource': 'selected_brain' if cat.get('brainProfile', {}).get('available') else 'rule_engine',
        'brainLabel': rs.public_words(cat.get('brainLabel')), 'pairAddress': pair, 'priceNative': price,
        # Persisted with the paper receipt so shared cards never invent MC data later.
        'marketCapUsd': market_cap, 'entryMarketCapUsd': entry_market_cap,
    })
    store['events'] = store['events'][:200]


def fee_side():
    """FeeCat's paper fee per side as a fraction (HQ › Core can change it: 0–5 %)."""
    rs = _rs()
    return float(rs.RULES.get('feePerSidePct', rs.FEE_PER_SIDE * 100)) / 100


def _next_n(rows):
    """A new proof's number: the highest so far + 1. Lists keep only the newest 60, so len + 1 repeats a number once full (PoStatic sat at #61, 2026-11-11)."""
    return max([int(r.get('n') or 0) for r in rows or [] if isinstance(r, dict)] + [len(rows or [])]) + 1


async def _jup_audit(http, mint):
    """🪐 Jupiter's public token audit for one coin → {top10, dev, authority} (None when Jupiter has nothing)."""
    try:
        rows = (await http.get('https://lite-api.jup.ag/tokens/v2/search', params={'query': mint}, timeout=6)).json()
        t = next((r for r in rows or [] if r.get('id') == mint), None)
    except Exception:
        return None
    if not t:
        return None
    a = t.get('audit') or {}
    top = a.get('topHoldersPercentage')
    return {'top10': float(top) if top is not None else None, 'dev': float(a.get('devBalancePercentage') or 0),
            'authority': a.get('mintAuthorityDisabled') is False or a.get('freezeAuthorityDisabled') is False}


async def _safety(http, p, cat=None):
    """Rug/insider gate from FEELESS on-chain intel. Returns (ok, why, conviction 0.5–1.5). Fee's learned limits count only when `cat` is Fee."""
    rs = _rs()
    mint = (p.get('baseToken') or {}).get('address')
    if not mint:
        return False, 'no mint', 0
    hit = rs._intel_cache.get(mint)
    # a complete read is kept 30 min; an EMPTY one (the RPC scan didn't reach the holders) only 60s — it used to block that coin for 30 min,
    # so 2026-10-21 Fee passed coins every scan and bought nothing ("no holder intel yet" on every one)
    if hit and rs.time.time() - hit[0] < (1800 if (hit[1] or {}).get('top10Pct') is not None else 60):
        d = hit[1]
    else:
        try:
            d = (await http.get(f'http://127.0.0.1:5077/api/reputation/intel/solana/{mint}', timeout=25)).json()
        except Exception:
            d = None
        if not d or d.get('top10Pct') is None:   # 🪐 the agents' fallback: Jupiter's own holder audit (top 10, dev, live authority)
            j = await rs._jup_audit(http, mint)
            if j and j.get('authority'):
                rs._intel_cache[mint] = (rs.time.time(), d)
                return False, 'mint or freeze authority is still live', 0
            if j and j.get('top10') is not None:
                d = {**(d or {}), 'top10Pct': j['top10'], 'devHoldingPct': j.get('dev') or 0, '_jup': True}
        rs._intel_cache[mint] = (rs.time.time(), d)
    if not d or d.get('top10Pct') is None:
        return False, 'no holder intel yet', 0
    R = {**rs.RULES, **rs._ENTRY_TUNE} if (cat or {}).get('id') == rs.LEADER_ID else rs.RULES   # owner 2026-11-04: Fee's tuning stays with Fee
    snip, bund = len(d.get('sniperWallets') or []), len(d.get('bundledWallets') or [])
    checks = [(rs._num(d.get('top10Pct')) <= R['maxTop10Pct'], f"top 10 wallets hold {rs._num(d.get('top10Pct')):.0f}%"),
              (rs._num(d.get('insidersHoldingPct')) <= R['maxInsiderPct'], f"insiders hold {rs._num(d.get('insidersHoldingPct')):.0f}%"),
              (rs._num(d.get('devHoldingPct')) <= R['maxDevPct'], f"dev holds {rs._num(d.get('devHoldingPct')):.0f}%"),
              (snip <= R['maxSnipers'], f'{snip} snipers'), (bund <= R['maxBundled'], f'{bund} bundled wallets'),
              # Learned from the FEELESS blocklist: a coin whose snipers were bankrolled by a known
              # repeat funder is the same crew running the same play — Fee never touches it.
              (not d.get('flaggedFunders'), f"{len(d.get('flaggedFunders') or {})} sniper(s) funded by a known repeat rug/snipe funder"),
              # Intel desk: a known crew (funder + puppets) inside the launch with rugs on record, or a high-threat crew, is a veto.
              (not any(r.get('rugs') or (r.get('threat') or 0) >= 60 for r in d.get('knownRings') or []),
               'known crew inside: ' + ', '.join(f"ring {r.get('id')} ({r.get('size')} wallets, {r.get('rugs') or 0} rugs)" for r in (d.get('knownRings') or [])[:2]))]
    for ok, why in checks:
        if not ok:
            return False, why, 0
    # Creator record (brutal scoring): never buy from flagged/risky creators or launch farms.
    try:
        rep = (await http.get(f'http://127.0.0.1:5077/api/reputation/token/solana/{mint}', timeout=10)).json()
    except Exception:
        rep = {}
    if rep.get('badge') in ('flagged', 'risky') or rep.get('serialLauncher'):
        return False, f"creator is {rep.get('badge')}" + (' (launch farm)' if rep.get('serialLauncher') else ''), 0
    # Cleaner distribution → more conviction.
    conviction = 1.5 - min(1.0, rs._num(d.get('top10Pct')) / R['maxTop10Pct']) * 0.6 - (0.2 if snip > 5 else 0) - (0.2 if bund else 0)
    if rep.get('badge') == 'trusted':
        conviction += 0.25
    if d.get('_jup'):   # holders from Jupiter only (no launch read): smaller bet
        conviction = min(conviction, 0.6)
    return True, f"top10 {rs._num(d.get('top10Pct')):.0f}%, insiders {rs._num(d.get('insidersHoldingPct')):.0f}%, {snip} snipers, {bund} bundled, creator {rep.get('badge') or 'unknown'}", max(0.5, min(1.75, round(conviction, 2)))


def setup_gate(p):
    """🐱 FEECAT ENTERS LIKE THE AGENTS AND OSSY / G4 (owner, 2026-10-18: "running with the latest methods — HH/HL, germ"). Pure.
    A coin the agents' chart read covers must show one of the three setups (HH/HL pullback · on its germ floor · a held breakout) and must not
    be a bad entry (gun line / chase / spike / SKIP); OSSY / G4 saying SELL on it in the last 30 min = out; their BUY = first (×1.2).
    A coin with no read yet keeps her own lanes' verdict (she never trades MORE because a read is missing). → (ok, why, mult, setups)."""
    rd, dw = p.get('_read') or None, p.get('_duo') or None
    if dw and dw.get('action') == 'SELL':
        return False, f"🤝 {dw.get('who')} said sell", 1.0, []
    if rd:
        if rd.get('bad'):
            return False, f"🔫 {str(rd['bad'])[:60]}", 1.0, []
        if not rd.get('setups'):
            return False, 'no HH/HL · germ · FVG support · breakout setup', 1.0, []
    tags = list((rd or {}).get('setups') or [])
    if dw and dw.get('action') == 'BUY':
        return True, f"🤝 {dw.get('who')} bought it", 1.2, tags
    return True, '', 1.0, tags


async def _market_candidates(http):
    """🐱 FEE TAKES ONLY ARENA / AGENT COINS (owner, 2026-10-15): her pool is what the ten agents judged READY / CONTENDING and what the Arena
    ranks — `GET /fuses/feecat-pool` on the reputation service — never the raw market feed. Each coin's live pair is read so her own safety
    gates still decide; the pool being empty means she waits."""
    rs = _rs()
    try:
        d_ = (await http.get(rs.POOL_URL, timeout=6)).json() or {}
        rows = d_.get('rows') or []
        rs._POOL_META['duo'] = d_.get('duo') or rs._POOL_META.get('duo') or {}
        rs._POOL_META['limits'] = d_.get('limits') or rs._POOL_META.get('limits') or {}
    except Exception:
        rows = []
    # 🔗 each coin's deepest SOL pool (2026-10-16: 15 of 39 pool coins came with a TRUMP / ZEC / USDC / stock pool and failed "not SOL-quoted")
    by_mint = {r['mint']: r for r in rows if r.get('mint')}
    pairs = await rs._sol_pairs(http, list(by_mint))
    out = []
    for m, p in pairs.items():
        r = by_mint.get(m) or {}
        out.append({**p, '_src': r.get('src'), '_srcWhy': r.get('why'), '_read': r.get('read'), '_duo': r.get('duo'), '_status': r.get('status')})
    return out


async def _sol_pairs(http, mints):
    """{mint: its deepest SOL / WSOL-quoted live pair} — ONE DexScreener /tokens/v1 call per 30 coins."""
    rs = _rs()
    out = {}
    for i in range(0, len(mints), 30):
        try:
            r = await http.get(f"https://api.dexscreener.com/tokens/v1/solana/{','.join(mints[i:i + 30])}")
            rows = r.json() if r.status_code == 200 else []
        except Exception:
            rows = []
        for p in rows if isinstance(rows, list) else []:
            m = (p.get('baseToken') or {}).get('address')
            if m not in mints or ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
                continue
            if m not in out or rs._num((p.get('liquidity') or {}).get('usd')) > rs._num((out[m].get('liquidity') or {}).get('usd')):
                out[m] = p
    return out


async def _pair_prices(http, pair_addresses):
    out = {}
    for i in range(0, len(pair_addresses), 30):
        try:
            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/solana/{",".join(pair_addresses[i:i + 30])}')
            for p in (r.json() or {}).get('pairs') or []:
                out[p.get('pairAddress')] = p
        except Exception:
            pass
    return out


def _qualifies(p, now):
    rs = _rs()
    if ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
        return None, 'not SOL-quoted'
    liq = rs._num((p.get('liquidity') or {}).get('usd'))
    vol = rs._num((p.get('volume') or {}).get('h24'))
    mc = rs._num(p.get('marketCap') or p.get('fdv'))
    ch = p.get('priceChange') or {}
    m5, h1, h6, h24 = rs._num(ch.get('m5')), rs._num(ch.get('h1')), rs._num(ch.get('h6')), rs._num(ch.get('h24'))
    tx = (p.get('txns') or {}).get('h1') or {}
    buys, sells = rs._num(tx.get('buys')), rs._num(tx.get('sells'))
    age_h = (now * 1000 - rs._num(p.get('pairCreatedAt'), now * 1000)) / 3_600_000
    R = {**rs.RULES, **rs._ENTRY_TUNE}
    checks = [(liq >= R['minLiquidity'], 'liquidity'), (vol >= R['minVolume24h'], 'volume'),
              (R['minMarketCap'] <= mc <= R['maxMarketCap'], 'market cap band'), (age_h >= max(R['minAgeHours'], R.get('coreMinAgeHours', 0)), 'too new'),
              (m5 > 0, '5m momentum'), (m5 <= R['maxM5Chase'], 'chasing a 5m spike'), (R['h1Min'] <= h1 <= R['h1Max'], '1h move'), (0 < h6 <= R['h6Max'], '6h trend'),
              (h24 <= R['h24Max'], 'overextended'), (sells == 0 or buys / max(sells, 1) >= R['minBuySellRatio'], 'buy pressure')]
    for ok, why in checks:
        if not ok:
            return None, why
    score = h1 * rs.math.log10(max(vol, 10)) * min(buys / max(sells, 1), 3)
    reason = f"1h +{h1:.1f}%, 6h +{h6:.1f}%, {buys:.0f}/{sells:.0f} buys/sells, ${liq/1000:.0f}K liq, ${vol/1000:.0f}K vol"
    return score, reason


def _fmt_usd(v):
    rs = _rs()
    v = rs._num(v)
    return f'${v/1e6:.2f}M' if v >= 1e6 else f'${v/1e3:.1f}K' if v >= 1e3 else f'${v:.2f}'


def _buy_analysis(p, size, sym, safety='', conviction=1.0):
    rs = _rs()
    ch = p.get('priceChange') or {}
    tx = (p.get('txns') or {}).get('h1') or {}
    b, s = rs._num(tx.get('buys')), rs._num(tx.get('sells'))
    liq, mc, vol = rs._num((p.get('liquidity') or {}).get('usd')), rs._num(p.get('marketCap') or p.get('fdv')), rs._num((p.get('volume') or {}).get('h24'))
    age_h = (rs.time.time() * 1000 - rs._num(p.get('pairCreatedAt'), rs.time.time() * 1000)) / 3_600_000
    R = {**rs.RULES, **rs._ENTRY_TUNE}
    return (f"🐱 Fee is buying ${sym} — {size} SOL (paper trade, live price).\n\n"
            f"Why this one passed every rule:\n"
            f"• Order flow: {b:.0f} buys vs {s:.0f} sells in the last hour ({(b / max(b + s, 1)) * 100:.0f}% buys) — buyers are in control.\n"
            f"• Momentum: 5m {rs._num(ch.get('m5')):+.1f}%, 1h {rs._num(ch.get('h1')):+.1f}%, 6h {rs._num(ch.get('h6')):+.1f}% — trending up without being vertical (my cap is +{R['h1Max']}% 1h / +{R['h6Max']}% 6h).\n"
            f"• Liquidity: {rs._fmt_usd(liq)} ({(liq / mc * 100) if mc else 0:.1f}% of {rs._fmt_usd(mc)} market cap) — deep enough to get out.\n"
            f"• Activity: {rs._fmt_usd(vol)} traded in 24h; pool is {age_h:.1f}h old (I skip anything under {max(R['minAgeHours'], R.get('coreMinAgeHours', 0)):g}h).\n"
            f"• Holders (FEELESS on-chain intel): {safety or 'checked'} — I skip anything with top-10 over {R['maxTop10Pct']}%, insiders over {R['maxInsiderPct']}%, dev over {R['maxDevPct']}% or heavy sniping/bundling.\n"
            f"• Size: {conviction}× conviction — cleaner holder distribution earns a bigger position.\n\n"
            f"Plan (trench + stock mindset): this is a {int(R['starterFraction'] * 100)}% starter. If it dips {R['add1At']}% and {R['add2At']}% from here while liquidity, volume and buyers still hold, "
            f"I add and re-average my entry instead of panic-selling. I take {int(R['takeProfit1Sell'] * 100)}% profit at +{R['takeProfit1']}% and more at +{R['takeProfit2']}%, "
            f"then let the rest run with a {R['runnerTrail']}% trailing stop that never drops below break-even. "
            f"I only cut early if the thesis breaks (liquidity pulled {R['liqPullPct']}%+, sellers dumping {R['dumpSellRatio']:.0f}:1, or volume dies while red); hard stop {R['hardStop']}% from my average. "
            f"Every trade pays 1% each way so you see real costs.\n\nNot financial advice — this is how a disciplined bot thinks, out loud.")


def _tune_entries(store):
    rs = _rs()
    cat = store['cats'].get(rs.LEADER_ID)
    if not cat:
        return
    L = cat.setdefault('learn', {'params': {}, 'log': [], 'missed': 0, 'good': 0})
    E = {**{k: rs.RULES[k] for k in rs.ENTRY_BOUNDS}, **(L.get('entry') or {})}
    day = [e for e in cat.get('exits', []) if rs.time.time() - e['exitAt'] < 86400 and e.get('pnlSol') is not None]
    note = None
    if len(day) < 4:
        mode = 'warming'
    else:
        wins = [e for e in day if e['pnlSol'] > 0]; wr = len(wins) / len(day); net = sum(e['pnlSol'] for e in day)
        # Last time she opened anything: open positions, or the most recent exit.
        last_open = max([p.get('openedAt', 0) for p in cat.get('positions', [])] + [e['exitAt'] for e in cat.get('exits', [])] + [0])
        if not cat.get('positions') and rs.time.time() - last_open > 3 * 3600:
            # Drought: rules tightened so far nothing qualifies. Ease halfway back to defaults —
            # safety checks (liquidity pull, dev dump, blocklist) are untouched.
            mode = 'drought-relax'
            for k in rs.ENTRY_BOUNDS:
                E[k] = round(E[k] + (rs.RULES[k] - E[k]) * 0.5)
            note = f"No entries for {int((rs.time.time() - last_open) / 3600)}h — easing entry rules halfway back to defaults."
        elif wr < 0.4 and rs.time.time() - (L.get('tightenedAt') or 0) < 6 * 3600:
            mode = 'holding'  # tighten at most once per 6h; the same bad day must not compound every hour
        elif wr < 0.4:
            mode = 'tightening'; L['tightenedAt'] = rs.time.time()
            E['minLiquidity'] = round(E['minLiquidity'] * 1.15)
            E['maxM5Chase'] -= 1; E['maxSnipers'] -= 2; E['maxTop10Pct'] -= 3
            note = f"24h win rate {wr:.0%} over {len(day)} trades — tightening entries."
        elif wr >= 0.6 and net > 0:
            mode = 'studying'
            L['study'] = {'at': rs.time.time(), 'winRate': round(wr * 100), 'netSol': round(net, 4), 'winners': [{'symbol': e['symbol'], 'why': e.get('why'), 'change': e.get('changeAtExit')} for e in wins[:10]]}
            note = f"24h win rate {wr:.0%} (+{net:.3f} SOL) — freezing settings and studying {len(wins)} winners."
        else:
            mode = 'steady'
            for k in rs.ENTRY_BOUNDS:
                E[k] = round(E[k] + (rs.RULES[k] - E[k]) * 0.25)
    for k, (lo, hi) in rs.ENTRY_BOUNDS.items():
        E[k] = max(lo, min(hi, E[k]))
    L['entry'] = E; L['mode'] = mode; L['tunedAt'] = rs.time.time()
    # 💪 auto-strength (hourly): her own 24h + 72h record decides ×0.6 / ×1 / ×1.15 size — cold at once, hot only when proven twice
    was = (cat.get('strength') or {}).get('level')
    st = rs.feecat_brain.strength(cat.get('exits', []), rs.time.time(), cat.get('strength'), cat.get('discipline'))
    cat['strength'] = {**st, 'at': rs.time.time()}
    if st['level'] != (was or 'steady'):
        rs._log_event(store, cat, 'LEARN', f"Strength {st['label']}: {st['why']}.")
    rs._ENTRY_TUNE.clear(); rs._ENTRY_TUNE.update(E)
    if note:
        L['log'].insert(0, {'at': rs.time.time(), 'note': note, 'symbol': '', 'missed': mode == 'tightening'}); L['log'] = L['log'][:40]
        rs._log_event(store, cat, 'LEARN', note)


async def _tune_loop():
    rs = _rs()
    await rs.asyncio.sleep(30)
    while True:
        try:
            store = rs._load(); rs._tune_entries(store); rs._save(store)
        except Exception as exc:
            print('tune error', exc)
        await rs.asyncio.sleep(3600)


def _params(cat):
    rs = _rs()
    return {**rs.RULES, **((cat.get('learn') or {}).get('params') or {})}


def _learn(store, cat):
    """Adapt exits from what happened AFTER Fee sold. Runners it cut early → loosen; good exits → tighten back."""
    rs = _rs()
    done = [e for e in cat.get('exits', []) if rs.time.time() - e['exitAt'] >= 6 * 3600 and not e.get('scored')]
    if not done:
        return
    L = cat.setdefault('learn', {'params': {}, 'log': [], 'missed': 0, 'good': 0})
    P = rs._params(cat)
    for e in done:
        e['scored'] = True
        # A profit-taking or patience exit is "too early" when the coin kept running long after.
        early = e['peakAfter'] >= 60 and any(k in e['why'] for k in ('trailing', 'profit', 'dead money', 'max hold'))
        if early:
            L['missed'] += 1
            P['runnerTrail'] = min(rs.LEARN_BOUNDS['runnerTrail'][1], P['runnerTrail'] + 5)
            P['takeProfit1'] = min(rs.LEARN_BOUNDS['takeProfit1'][1], P['takeProfit1'] + 10)
            note = f"Sold {e['symbol']} at {e['changeAtExit']:+.1f}%, it ran another +{e['peakAfter']:.0f}%. Giving winners more room: runner trail {P['runnerTrail']}%, first profit at +{P['takeProfit1']}%."
        else:
            L['good'] += 1
            for k in rs.LEARN_BOUNDS:
                P[k] = round(P[k] + (rs.RULES[k] - P[k]) * 0.25, 2)  # drift back toward the defaults
            note = f"Exit on {e['symbol']} held up (best after sell +{e['peakAfter']:.0f}%, low {e['lowAfter']:.0f}%). Keeping discipline."
        L['params'] = {k: P[k] for k in rs.LEARN_BOUNDS}
        L['log'].insert(0, {'at': rs.time.time(), 'note': note, 'symbol': e['symbol'], 'missed': early})
        L['log'] = L['log'][:40]
        rs._log_event(store, cat, 'LEARN', note)


def fee_voice(text):
    """→ Fee's post with ONE opener in her voice, picked by what happened (buy / win / loss / add) and the text itself (stable). Pure (tests)."""
    rs = _rs()
    t = str(text or '')
    kind = ('add' if 'Added' in t else 'win' if ('took profit' in t or ('sold' in t and 'P&L +' in t)) else 'loss' if 'sold' in t else 'buy')
    pool = rs.FEE_OPENERS[kind]
    return f"{pool[sum(map(ord, t)) % len(pool)]}\n{t}"


def _post_as_fee(pair_address, text, register_call=False):
    rs = _rs()
    try:
        key = (rs.DATA_DIR / 'internal.key').read_text().strip()
        r = rs.httpx.post('http://127.0.0.1:5077/api/reputation/internal/fee-post', json={'pairAddress': pair_address, 'text': rs.public_words(rs.fee_voice(text)), 'registerCall': register_call},
                       headers={'x-feeless-internal': key}, timeout=15)
        if r.status_code != 200:
            print('fee post rejected', r.status_code, r.text[:200])
    except Exception as exc:
        print('fee post failed', exc)


def _notify_real(cat, p):
    """💵 Tell the cat's real wallet a proposal is waiting (inbox + phone, via reputation's internal notify). Never blocks the engine."""
    rs = _rs()
    try:
        key = (rs.DATA_DIR / 'internal.key').read_text().strip()
        verb = f"BUY ${p['symbol']} with {p['sol']} SOL" if p['side'] == 'buy' else f"SELL {round(p['fraction'] * 100)}% of your ${p['symbol']}"
        rs.httpx.post('http://127.0.0.1:5077/api/reputation/internal/notify', headers={'x-feeless-internal': key}, timeout=2,
                   json={'address': cat['realWallet'], 'kind': 'cat', 'text': f"🐱 {cat.get('name') or 'Your agent'} " + (f"is doing it from its own wallet: {verb} — {p['why'][:80]}." if (cat.get('agentWallet') or {}).get('mode') == 'auto'
                         else f"wants to {verb} — {p['why'][:80]}. " + ('Approve within 15 min — its wallet sends it.' if cat.get('agentWallet') else 'Approve within 15 min; your wallet signs.')),
                         'url': '/terminal/feecat/agents', 'once': f"cat-prop-{p['id']}"})
    except Exception:
        pass


def _close(store, cat, pos, price_native, why, fraction=1.0, market_cap=None):
    rs = _rs()
    if rs._real.is_real(cat):   # 💵 a REAL cat: its exit becomes a proposal for the coin the user really bought (sell X % — the wallet signs)
        p_ = rs._real.propose(cat, 'sell', pos.get('mint'), pos.get('pairAddress'), pos.get('symbol'), why, rs.time.time(), fraction=fraction, px=price_native)
        if p_:
            rs._notify_real(cat, p_)
    gross = pos['notionalSol'] * fraction * (price_native / pos['entryPriceNative'])
    # 🎯 TRUE FILL on the sell: price impact against the pool (entry liquidity, SOL→$ at entry) — what a wallet would receive
    r_usd = rs._num(pos.get('entryLiq')) / 2; su = rs._num(pos.get('solUsdAtEntry'))
    if r_usd > 0 and su > 0:
        gross = gross / (1 + gross * su / r_usd)
    proceeds = gross * (1 - rs.fee_side())
    # 🔒 Same rule as real cards: P&L = the price move on the money that reached the pool (fees apart). The balance still
    # receives `proceeds` (real money after the sell fee); both sides' fees are tracked in `feesSol`, never inside P&L.
    pnl = round(gross - pos['notionalSol'] * fraction, 6)
    fee_sol = (pos['costSol'] - pos['notionalSol']) * fraction + (gross - proceeds)
    cat['feesSol'] = round(cat.get('feesSol', 0) + fee_sol, 6)
    if fraction < 1:
        pos['realizedPartialSol'] = round(pos.get('realizedPartialSol', 0) + pnl, 6)
        pos.setdefault('costBasisSol', pos['costSol'])
        pos['notionalSol'] = round(pos['notionalSol'] * (1 - fraction), 6)
        pos['costSol'] = round(pos['costSol'] * (1 - fraction), 6)
    cat['balanceSol'] = round(cat['balanceSol'] + proceeds, 6)
    cat['realizedPnlSol'] = round(cat.get('realizedPnlSol', 0) + pnl, 6)
    cat['totalPnlSol'] = cat['realizedPnlSol']
    cat['volumeSol'] = round(cat.get('volumeSol', 0) + gross, 6)
    cat['wins' if pnl >= 0 else 'losses'] = cat.get('wins' if pnl >= 0 else 'losses', 0) + 1
    cat['xp'] = cat.get('xp', 0) + (20 if pnl >= 0 else 6)
    cat['level'] = max(1, cat['xp'] // 100 + 1)
    cat.setdefault('dailyLoss', {})
    day = rs.time.strftime('%Y-%m-%d')
    if pnl < 0:
        cat['dailyLoss'][day] = round(cat['dailyLoss'].get(day, 0) - pnl, 6)
    cat.setdefault('cooldowns', {})[pos['pairAddress']] = rs.time.time()
    bc = cat.get('brainsCfg')
    if bc:   # 🚀 a cat with brains: 'profit pays' settles what its model calls owe from a winning sale (fees apart from P&L, like every fee)
        su_ = rs._num(pos.get('solUsdAtEntry'))
        paid = rs._lc.settle(bc, pnl * su_) if su_ > 0 else 0.0
        if paid > 0:
            cat['balanceSol'] = round(cat['balanceSol'] - paid / su_, 6)
            cat['brainFeesUsd'] = round(cat.get('brainFeesUsd', 0) + paid, 6)
        if fraction >= 1 and pos.get('brainBy'):
            rec = bc.setdefault('record', {}).setdefault(pos['brainBy'], {'n': 0, 'won': 0, 'pnlSol': 0.0})
            rec['n'] += 1; rec['won'] += 1 if pnl + pos.get('realizedPartialSol', 0) >= 0 else 0
            rec['pnlSol'] = round(rec['pnlSol'] + pnl + pos.get('realizedPartialSol', 0), 6)
    if fraction >= 1:
        cat.setdefault('exits', []).append({'pairAddress': pos['pairAddress'], 'symbol': pos['symbol'], 'exitPx': price_native, 'exitAt': rs.time.time(),
                                            'why': why, 'pnlSol': pnl, 'changeAtExit': round((price_native / pos['entryPriceNative'] - 1) * 100, 2), 'peakAfter': 0.0, 'lowAfter': 0.0,
                                            'peak': round(pos.get('peakChange', 0), 2), 'heldMin': round((rs.time.time() - pos.get('openedAt', rs.time.time())) / 60, 1)})   # 🎭 Prompt Studio reads hold + peak
        cat['exits'] = cat['exits'][-60:]
        ep_ = rs._num(pos.get('entryPriceNative')); rs._colony_trade(cat, 'sell', pos, price_native * rs._num(pos.get('entryPriceUsd')) / ep_ if ep_ > 0 else 0)
        # This is a paper price simulation, even when a real-wallet proposal exists.
        # Colony accrual belongs to the confirmed wallet-fill path only.
        # File the whole trade (partial profits included) under its setup so the next entry learns from it.
        total_pnl = round(pnl + pos.get('realizedPartialSol', 0), 6)
        ret = total_pnl / max(pos.get('costBasisSol') or pos['costSol'], 1e-9) * 100
        cat['setupMemory'] = rs.feecat_brain.remember(cat.get('setupMemory') or [], pos.get('setup'), ret, total_pnl, rs.time.time())
    cat.setdefault('pnlHistory', []).append({'value': cat['realizedPnlSol'], 't': rs.time.time()})
    cat['pnlHistory'] = cat['pnlHistory'][-60:]
    closed = cat.get('wins', 0) + cat.get('losses', 0)
    cat['winRate'] = round(cat.get('wins', 0) / closed * 100) if closed else None
    change = (price_native / pos['entryPriceNative'] - 1) * 100
    part = f'{int(fraction * 100)}% of ' if fraction < 1 else ''
    rs._log_event(store, cat, 'SELL', f"Sold {part}{pos['symbol']} at {change:+.1f}% — {why}. P&L {pnl:+.4f} SOL on the price move (fees apart, paper, live price).", pnl, pos.get('pairAddress'), price_native, market_cap, pos.get('entryMarketCapUsd'))
    if cat.get('isLeader') and pos.get('pairAddress'):
        held = (rs.time.time() - pos.get('openedAt', rs.time.time())) / 3600
        verdict = 'Took the win.' if pnl >= 0 else 'The thesis broke, so I cut it — protecting capital beats hoping.'
        if fraction < 1:
            rs._post_as_fee(pos['pairAddress'], f"🐱 Fee took profit on ${pos['symbol']}: sold {int(fraction * 100)}% at {change:+.1f}% — {why}. Locked {pnl:+.4f} SOL.\nThe rest keeps riding with a trailing stop, and it can't turn into a loss: the floor is my break-even.")
            return
        rs._post_as_fee(pos['pairAddress'], f"🐱 Fee sold ${pos['symbol']} at {change:+.1f}% after {held:.1f}h — {why}.\nP&L {pnl:+.4f} SOL on the price move — fees shown apart (peak was {pos.get('peakChange', 0):+.1f}%).\n{verdict} The rules decide the exit, not feelings.")


def _fresh_qualifies(p, now):
    """Fresh-launch lane (the 'could be a moon' read): brand-new coin with a real narrative footprint
    (X account + website), buyers in control and volume moving fast relative to its liquidity."""
    rs = _rs()
    if ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
        return None, 'not SOL-quoted'
    age_min = (now * 1000 - rs._num(p.get('pairCreatedAt'), now * 1000)) / 60_000
    info = p.get('info') or {}
    socials = {(x.get('type') or '').lower() for x in info.get('socials') or []}
    liq = rs._num((p.get('liquidity') or {}).get('usd')); vh1 = rs._num((p.get('volume') or {}).get('h1'))
    t1 = (p.get('txns') or {}).get('h1') or {}; buys, sells = rs._num(t1.get('buys')), rs._num(t1.get('sells'))
    m5 = rs._num((p.get('priceChange') or {}).get('m5'))
    checks = [(rs.RULES['freshMinMinutes'] <= age_min < rs.RULES['minAgeHours'] * 60, 'not in fresh window'), (liq >= rs.RULES['freshMinLiquidity'], 'thin liquidity'),
              ('twitter' in socials, 'no X account'), (bool(info.get('websites')), 'no website'), (buys >= 1.5 * max(sells, 1), 'buyers not in control'),
              (vh1 >= 0.5 * liq, 'volume not moving'), (0 < m5 <= rs.RULES['maxM5Chase'], '5m momentum')]
    for ok, why in checks:
        if not ok:
            return None, why
    return vh1 / max(liq, 1) * min(buys / max(sells, 1), 3), f"fresh launch {age_min:.0f}m old: X + site, {buys:.0f}/{sells:.0f} buys/sells, 1h vol {vh1 / max(liq, 1):.1f}× liquidity"


def agent_lane(base, own=None):
    """🐱🤖 The agents' band for her agents lane, with HER own overrides on top (HQ › Fee › agents lane; None / missing = the agents' value)."""
    rs = _rs()
    out = {k: rs._num((base or {}).get(k)) for k in rs.AGENT_LANE_KEYS}
    for k, v in (own or {}).items():
        if k in rs.AGENT_LANE_KEYS and v is not None and rs._num(v) >= 0:
            out[k] = rs._num(v)
    return out


def clean_lane(raw):
    """🐱 Her agents-lane overrides from HQ: only the band keys, a number ≥ 0; empty / None = follow the agents (key dropped)."""
    rs = _rs()
    out = {}
    for k, v in (raw or {}).items():
        if k in rs.AGENT_LANE_KEYS and v not in (None, '') and rs._num(v, -1) >= 0:
            out[k] = min(rs._num(v), 1e9)
    return out


def _agents_qualifies(p, now, lim):
    """🐱🤖 FEECAT = THE AGENTS + OSSY / G4 (owner, 2026-10-19: "same intake, same agents, she has my agents settings but I can tune hers"):
    a coin the ten agents put READY / CONTENDING is judged on the agents' own band (live cap, age, pool, 1h volume) instead of her old core /
    fresh lanes — those refused all 39 of their coins (cap band 16, liquidity 11, too new 7). Not dumping, not chasing, buyers not outsold.
    Her safety scan, setup gate, discipline and proof gate still decide after this. READY = full size, CONTENDING = half."""
    rs = _rs()
    if ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
        return None, 'not SOL-quoted'
    R = {**rs.RULES, **rs._ENTRY_TUNE}
    age_h = (now * 1000 - rs._num(p.get('pairCreatedAt'), now * 1000)) / 3_600_000
    mc = rs._num(p.get('marketCap') or p.get('fdv')); liq = rs._num((p.get('liquidity') or {}).get('usd')); vh1 = rs._num((p.get('volume') or {}).get('h1'))
    t5 = (p.get('txns') or {}).get('m5') or {}; b5, s5 = rs._num(t5.get('buys')), rs._num(t5.get('sells'))
    m5 = rs._num((p.get('priceChange') or {}).get('m5'))
    mx_age = lim.get('maxAgeH') or 0
    checks = [(not lim.get('mcMin') or mc >= lim['mcMin'], 'under the agents\' MC floor'), (not lim.get('mcMax') or mc <= lim['mcMax'], 'over the agents\' MC top'),
              (age_h >= (lim.get('minAgeH') or 0), 'younger than the agents\' min age'), (not mx_age or mx_age == float('inf') or age_h <= mx_age, 'older than the agents\' max age'),
              (liq >= (lim.get('poolMin') or 8000), 'under the agents\' pool floor'), (vh1 >= (lim.get('minVol1h') or 0), 'under the agents\' 1h volume'),
              (m5 >= -5, 'dumping (5m)'), (m5 <= R['maxM5Chase'], 'chasing (5m)'), (b5 >= s5 * 0.8, 'sellers lead the 5m')]
    for ok, why in checks:
        if not ok:
            return None, why
    full = p.get('_status') == 'READY'
    return (vh1 / max(liq, 1) + 1) * (1.0 if full else 0.6), f"🤖 agents lane: {p.get('_status') or 'CONTENDING'} on the agents' desk · {age_h:.1f}h old · {'full' if full else 'half'} size"


def _learn_qualifies(p, now):
    """🎓 LEARNING LANE (owner, 2026-10-16: "the cat isn't trading"): her core lane only buys coins 3+ days old and her fresh lane only < 3h
    launches with X + site — her pool (the agents' + the Arena's coins) is mostly 3h–3 days old, so she sat out every coin. This lane takes
    that gap at LEARN_SIZE: a SOL pool ≥ $15K, buyers ahead (≥ 1.3× sells in the hour), not dumping (5m ≥ −2%), not a spike (5m ≤ her
    chase cap), 1h volume ≥ a third of the pool. Her safety scan, discipline, proof gate and setup memory still decide after this."""
    rs = _rs()
    if ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
        return None, 'not SOL-quoted'
    R = {**rs.RULES, **rs._ENTRY_TUNE}
    age_h = (now * 1000 - rs._num(p.get('pairCreatedAt'), now * 1000)) / 3_600_000
    liq = rs._num((p.get('liquidity') or {}).get('usd')); vh1 = rs._num((p.get('volume') or {}).get('h1'))
    t1 = (p.get('txns') or {}).get('h1') or {}; buys, sells = rs._num(t1.get('buys')), rs._num(t1.get('sells'))
    m5, h1 = rs._num((p.get('priceChange') or {}).get('m5')), rs._num((p.get('priceChange') or {}).get('h1'))
    checks = [(R['minAgeHours'] <= age_h < max(R['minAgeHours'], R.get('coreMinAgeHours', 0)), 'not in the learning window'), (liq >= rs.LEARN_MIN_LIQ, 'thin liquidity'),
              (buys >= 1.3 * max(sells, 1), 'buyers not ahead'), (-2 <= m5 <= R['maxM5Chase'], '5m momentum'), (vh1 >= liq / 3, 'volume not moving'), (h1 <= R['h1Max'], '1h move')]
    for ok, why in checks:
        if not ok:
            return None, why
    return vh1 / max(liq, 1) * min(buys / max(sells, 1), 3) * 0.5, f"🎓 learning lane: {age_h:.0f}h old, {buys:.0f}/{sells:.0f} buys/sells, 1h vol {vh1 / max(liq, 1):.1f}× pool — quarter size"


async def _fvg(http, pair_address, price_usd):
    """Bullish fair value gap on 5m candles: a bar whose low sits above the high two bars earlier leaves
    an unfilled gap. Price trading back inside the most recent such gap is a retest entry."""
    try:
        c = (await http.get(f'http://127.0.0.1:5099/api/candles/solana/{pair_address}', params={'interval': '5m'})).json().get('candles') or []
    except Exception:
        return None
    c = c[-40:]
    for i in range(len(c) - 1, 1, -1):
        lo, hi = c[i - 2][2], c[i][3]  # gap between bar i-2's high and bar i's low
        if hi > lo:
            filled = any(x[3] <= lo for x in c[i + 1:])
            if not filled and lo <= price_usd <= hi:
                return lo, hi
            return None
    return None


def _thesis(pos, live, R):
    """Is the reason Fee bought still true? Returns (broken_reason | None, ok_to_add, h1 volume vs entry)."""
    rs = _rs()
    liq_now = rs._num((live.get('liquidity') or {}).get('usd'))
    vol_h1 = rs._num((live.get('volume') or {}).get('h1'))
    t5 = (live.get('txns') or {}).get('m5') or {}
    t1 = (live.get('txns') or {}).get('h1') or {}
    b5, s5, b1, s1 = rs._num(t5.get('buys')), rs._num(t5.get('sells')), rs._num(t1.get('buys')), rs._num(t1.get('sells'))
    change = (rs._num(live.get('priceNative')) / pos['entryPriceNative'] - 1) * 100
    entry_liq, entry_vol = rs._num(pos.get('entryLiq')), rs._num(pos.get('entryVolH1'))
    vol_ratio = vol_h1 / entry_vol if entry_vol else None
    if entry_liq and liq_now and liq_now < entry_liq * (1 - R['liqPullPct'] / 100):
        return f"liquidity pulled ({rs._fmt_usd(entry_liq)} → {rs._fmt_usd(liq_now)})", False, vol_ratio
    if s5 >= 10 and s5 >= b5 * R['dumpSellRatio'] and change < 0:
        return f'sellers dumping ({s5:.0f} sells vs {b5:.0f} buys in 5m)', False, vol_ratio
    if vol_ratio is not None and vol_ratio < R['thesisVolKeep'] and change < -10:
        return f'volume dried up ({vol_ratio:.0%} of entry-hour volume) while red', False, vol_ratio
    if s1 >= 40 and s1 > b1 * 1.6 and change < 0:
        return f'sellers own the hour ({s1:.0f} sells vs {b1:.0f} buys)', False, vol_ratio
    ok_to_add = b5 >= s5 and (vol_ratio is None or vol_ratio >= 0.5) and (not entry_liq or liq_now >= entry_liq * 0.85)
    return None, ok_to_add, vol_ratio


async def _crowd_feed(http):
    """Coins FEELESS's elite traders bought in the last 6h (counts only), so she learns from the best users."""
    try:
        r = await http.get('http://127.0.0.1:5077/api/reputation/crowd/elite-flow', timeout=4)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


async def _duo_read(http):
    """🐱🤝 Her one duo AI read (every 10 min, reputation service `/cats-ai`): pairs BOTH models said to skip / bank. {} when unread or stale."""
    rs = _rs()
    try:
        r = await http.get('http://127.0.0.1:5077/api/reputation/cats-ai', timeout=3)
        d = r.json() if r.status_code == 200 else {}
        return d if rs.time.time() - float(d.get('read') or 0) <= 900 else {}
    except Exception:
        return {}


async def _fuse_discover(http):
    """The Fuse runner engine's view (gated runners + sources + coins that failed a gate). Served from its warm cache."""
    try:
        r = await http.get('http://127.0.0.1:5077/api/reputation/runners/discover', timeout=4)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def creator_adjust(ranked, reps, rejections):
    """Fresh launches lean on WHO made them: a clean creator (rep engine) is a better chance → score ×1.25 + cited; a suspect /
    high-risk creator → out. Unknown creators keep their score. Only ever filters or re-ranks, never adds an entry."""
    out = []
    for score, reason, p in ranked:
        rep = reps.get((p.get('baseToken') or {}).get('address')) if p.get('_fresh') else None
        if rep in ('suspect', 'high'):
            rejections['creator rep'] = rejections.get('creator rep', 0) + 1
            continue
        out.append((score * 1.25, f"{reason} · 🧼 clean creator", p) if rep == 'clean' else (score, reason, p))
    return out


async def _creator_check(ranked, rejections):
    rs = _rs()
    mints = [(p.get('baseToken') or {}).get('address') for _, _, p in ranked if p.get('_fresh')][:10]
    if not mints:
        return ranked
    try:
        async with rs.httpx.AsyncClient(timeout=5) as http:
            recs = (await http.get('http://127.0.0.1:5077/api/reputation/edge', params={'mints': ','.join(m for m in mints if m)})).json()
        recs = recs.get('edge', recs) if isinstance(recs, dict) else {}
        reps = {m: ((r or {}).get('runner') or {}).get('creatorRep') for m, r in recs.items() if isinstance(r, dict)}
    except Exception:
        reps = {}
    return rs.creator_adjust(ranked, reps, rejections)


async def _or_models():
    """OpenRouter's public model list, cached an hour (the last good copy is kept when it fails)."""
    rs = _rs()
    if rs._MODELS['rows'] is not None and rs.time.time() - rs._MODELS['at'] < 3600:
        return rs._MODELS['rows']
    try:
        async with rs.httpx.AsyncClient(timeout=15) as h:
            r = await h.get('https://openrouter.ai/api/v1/models')
        if r.status_code == 200:
            rs._MODELS.update(at=rs.time.time(), rows=rs._lc.catalog(r.json().get('data') or []))
    except Exception:
        pass
    return rs._MODELS['rows'] or rs._lc.catalog([])


def _model_knobs_clean(catalog, knobs):
    """🎛 {model: {knob: value}} → only the knobs each model's live OpenRouter row lists, each clamped to its range; empty models dropped."""
    rs = _rs()
    rows = {m['id']: m for m in (catalog or {}).get('models') or []}
    out = {}
    for model, cfg in (knobs or {}).items():
        if not isinstance(cfg, dict):
            continue
        c = rs._lc.clamp_knobs((rows.get(model) or {}).get('knobs'), cfg)
        if c:
            out[model] = c
    return out


async def _est_usd(model, in_chars, out_tokens):
    """💲 What one model call should cost BEFORE it runs (owner 2026-11-10: "show price for stuff so users aren't blind"): OpenRouter's own
    $ per 1M tokens for this model, prompt at ~3.5 characters a token. A model on his own machines is free. None = no price listed."""
    rs = _rs()
    if not model or str(model).startswith('local/'):
        return 0.0
    row = next((m for m in (await rs._or_models()).get('models') or [] if m.get('id') == model), None)
    if not row:
        return None
    return round((float(in_chars or 0) / 3.5) * float(row.get('inUsd') or 0) / 1e6 + float(out_tokens or 0) * float(row.get('outUsd') or 0) / 1e6, 5)


def _brains_live():
    rs = _rs()
    return rs.os.environ.get('LAUNCH_CAT_LIVE', '').lower() in ('1', 'true', 'on') and bool(rs.os.environ.get('OPENROUTER_API_KEY'))


def _kept(text, n):
    """The note numbers the model kept, in range and unique — anything unreadable keeps everything (a sort never loses memory by mistake)."""
    rs = _rs()
    m = rs.re.search(r'\{.*\}', str(text or ''), rs.re.S)
    try:
        keep = rs.json.loads(m.group(0)).get('keep') if m else None
    except ValueError:
        keep = None
    if not isinstance(keep, list):
        return list(range(n))
    return sorted({int(i) for i in keep if str(i).lstrip('-').isdigit() and 0 <= int(i) < n})


async def _sort_cloud(cat_id, model):
    """🧠 owner 2026-10-30: on a model swap the new lead sorts the old cloud — keeps what helps, deletes the rest. One call, charged like any other."""
    rs = _rs()
    rs._OR_CAT.set(cat_id)
    await rs.asyncio.sleep(1)   # after the switch itself is saved
    cat = rs._load()['cats'].get(cat_id)
    items = ((cat or {}).get('brainsCfg') or {}).get('cloud') or []
    if not items:
        return
    items = items[-rs.SORT_MAX:]
    note = lambda c: c.get('text') or f"{c.get('word', '')} ${c.get('sym', '')} {c.get('why', '')}"
    lines = '\n'.join(f'{i}: {note(c)}'[:240] for i, c in enumerate(items))
    try:
        own = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
        text, cost = await rs._or_call(model, [{'role': 'system', 'content': rs.SORT_SYS}, {'role': 'user', 'content': lines}], max_tokens=400, **({'key': own} if own else {}))
    except Exception as e:   # the model is down: its memory stays exactly as it was
        print(f'cloud sort failed for {cat_id}: {e}')
        return
    keep = rs._kept(text, len(items))
    store = rs._load(); cat = store['cats'].get(cat_id)
    if not cat or not cat.get('brainsCfg'):
        return
    cat['brainsCfg']['cloud'] = [items[i] for i in keep]
    if not own:
        rs._lc.charge(cat['brainsCfg'], cost or 0)
    rs._log_event(store, cat, 'LEARN', f"🧠 {model.split('/')[-1]} sorted its memory: kept {len(keep)} of {len(items)} notes")
    rs._save(store)


async def _agent_usdc(http, addr):
    """(usdc, sol) live in an agent's wallet."""
    rs = _rs()
    h_ = await http.get(f'{rs._at.TRADE}/holdings/{addr}', timeout=15)
    if h_.status_code != 200:
        return 0.0, 0.0
    tk_ = {t_.get('mint'): float(t_.get('amount') or 0) for t_ in ((h_.json() or {}).get('tokens') or [])}
    return tk_.get(rs._cf_usdc, 0.0), tk_.get(rs._at.SOL, 0.0)


async def _thinking_money(cat):
    """💳 USDC ready for this agent's model calls: its wallet's own, topped up from its own SOL when low. No manual swap for the owner. → usdc available."""
    rs = _rs()
    w_ = cat.get('agentWallet') or {}; addr = w_.get('address'); now = rs.time.time()
    async with rs.httpx.AsyncClient(timeout=25) as http:
        usdc, sol = await rs._agent_usdc(http, addr)
        keep_ = rs.think_keep_sol(cat)   # 💵 its trading SOL is never turned into thinking money (owner 2026-11-01: "all the money go?")
        amount = min(rs.THINK_SWAP_SOL, sol - keep_)
        if usdc >= rs.THINK_MIN_USDC or amount < 0.002 or now - rs._THINK_AT.get(cat['id'], 0) < 180:
            return usdc
        rs._THINK_AT[cat['id']] = now
        try:
            q_ = await http.post(f'{rs._at.TRADE}/quote', json={'input_mint': rs._at.SOL, 'output_mint': rs._cf_usdc, 'amount': f'{amount:.6f}', 'wallet': addr, 'slippage_bps': rs._at.SLIP_BPS}, headers=rs._at._internal_headers(), timeout=20)   # ⚖ an agent wallet's own swap (gated when its owner funded it)
            qj = q_.json() if q_.status_code == 200 else {}
            if qj.get('input_mint') != rs._at.SOL or qj.get('output_mint') != rs._cf_usdc or not (qj.get('quote') or {}).get('transaction'):
                return usdc
            await rs._at._circle_post(http, cat, {'key': f"feeless-{cat['id']}-think-{round(now)}", 'tx': qj['quote']['transaction']})
        except (ValueError, rs.httpx.HTTPError) as e:
            print(f"[agent think swap] {cat['id']}: {str(e)[:120]}")
            return usdc
        for _ in range(8):
            await rs.asyncio.sleep(3)
            now_usdc, _sol = await rs._agent_usdc(http, addr)
            if now_usdc > usdc:
                return now_usdc
    return usdc


def swap_plan(side, amount, sol, usdc, gas=None):
    """👛 The owner's swap inside the agent's OWN wallet (SOL ⇄ USDC, nothing leaves it). → (input mint, output mint, amount) or raises ValueError.
    SOL → USDC always leaves the gas reserve; 0 = everything it can."""
    rs = _rs()
    gas = rs._at.GAS_SOL if gas is None else gas
    if side not in ('SOL>USDC', 'USDC>SOL'):
        raise ValueError('Swap SOL → USDC or USDC → SOL.')
    tok = side.split('>')[0]; have = max(0.0, sol - gas) if tok == 'SOL' else usdc
    amt = have if not amount else float(amount)
    if amt <= 0 or amt > have + 1e-9:
        raise ValueError(f"It has {have:.6g} {tok} it can swap" + (f' (it keeps {gas:g} SOL for gas)' if tok == 'SOL' else '') + '.')
    if amt < rs.WALLET_SWAP_MIN[tok]:
        raise ValueError(f'The smallest swap is {rs.WALLET_SWAP_MIN[tok]:g} {tok}.')
    return (rs._at.SOL, rs._cf_usdc, round(amt, 6)) if tok == 'SOL' else (rs._cf_usdc, rs._at.SOL, round(amt, 6))


def pot_transfer_tx(src, dst, lamports, blockhash):
    """The one transfer the pot send may sign: the agent's wallet → the colony pot, this many lamports (base64, unsigned)."""
    import base64 as _b64
    from solders.hash import Hash
    from solders.message import Message
    from solders.pubkey import Pubkey
    from solders.system_program import TransferParams, transfer
    from solders.transaction import Transaction
    ix = transfer(TransferParams(from_pubkey=Pubkey.from_string(src), to_pubkey=Pubkey.from_string(dst), lamports=int(lamports)))
    return _b64.b64encode(bytes(Transaction.new_unsigned(Message.new_with_blockhash([ix], Pubkey.from_string(src), Hash.from_string(blockhash))))).decode()


def think_keep_sol(cat):
    """The SOL its thinking top-up must leave alone: one full trade + the trade gas reserve + this swap's own fee room."""
    rs = _rs()
    trade_ = max(rs._num(cat.get('budgetSol')), rs._num((cat.get('risk') or {}).get('maxPositionSol')))
    return round(max(rs.THINK_KEEP_SOL, trade_ + rs._at.GAS_SOL + 0.002), 6)


def _pays_itself(cat):
    """💳 A wallet Circle signs for this cat: its own agent wallet, or Fee's wallet the creator made in FEELESS's Circle project."""
    w_ = cat.get('agentWallet') or {}
    return w_.get('circleAcct') == 'agent' or bool(cat.get('isLeader') and w_.get('provider') == 'circle' and w_.get('circleId'))


async def _heal_fee_wallet(store):
    """👛 owner 2026-10-31: "I added a Circle wallet I made for Fee and it says read only" — it was linked before Circle listed it, so it stayed
    WATCH-ONLY for good. Re-check: if FEELESS's Circle project holds it now, Circle signs for her (trades inside her caps + her model calls)."""
    rs = _rs()
    cat = store['cats'].get(rs.LEADER_ID) or {}
    w_ = cat.get('agentWallet') or {}
    if w_.get('provider') != 'watch' or not w_.get('address'):
        return False
    async with rs.httpx.AsyncClient(timeout=15) as http:
        r = await http.get('http://127.0.0.1:5077/api/reputation/internal/circle-wallet', params={'address': w_['address']}, headers=rs._internal_headers())
    if r.status_code != 200 or not (r.json() or {}).get('id'):
        return False
    w_.update(provider='circle', circleId=r.json()['id'])
    rs._log_event(store, cat, 'STARTED', f"{cat['name']}'s wallet {w_['address'][:6]}… is a Circle wallet of FEELESS — she can pay for her own thinking from it now.")
    return True


async def _wallet_call(cat, model, messages, max_tokens, ceiling):
    """💳 One model call paid from this agent's own USDC (agent_pay.py). → (text, $ paid); ('', 0.0) = nothing paid, the next route takes it.
    A model the provider does not list (400) or cannot answer right now (503 "no billable answer", never charged) → its default model once
    (found live 2026-10-31: every Claude Haiku 5.5 call fell through to the free backup)."""
    rs = _rs()
    for m_ in dict.fromkeys([rs._ap.provider_model(model), rs._ap.FALLBACK_MODEL]):
        text, usd = await rs._wallet_once(cat, m_, messages, max_tokens, ceiling)
        if text or usd:
            return text, usd
    return '', 0.0


async def _wallet_once(cat, model_id, messages, max_tokens, ceiling):
    rs = _rs()
    w_ = cat.get('agentWallet') or {}
    try:
        async with rs.httpx.AsyncClient(timeout=70) as h:
            body = {'model': model_id, 'messages': messages, 'max_tokens': int(max_tokens or 1000)}
            r = await h.post(rs._ap.PROVIDER, json=body)
            if r.status_code != 402:   # nothing paid — say why (an image it cannot take, a model it does not list…), never silent
                print(f"[agent pay] {cat['id']}: {model_id} answered {r.status_code} before payment: {r.text[:120]}")
                return '', 0.0
            doc, entry = rs._ap.pick_quote(r.headers.get('payment-required'), ceiling)
            s_ = await h.post('http://127.0.0.1:5077/api/reputation/internal/agent-x402-pay', headers=rs._internal_headers(), json={'catId': cat['id'], 'walletId': w_.get('circleId'), 'address': w_.get('address'), 'entry': entry, 'creator': w_.get('circleAcct') != 'agent'})
            if s_.status_code != 200:
                return '', 0.0
            head = rs._ap.payment_header(doc, entry, s_.json()['signedTransaction'])
            r2 = await h.post(rs._ap.PROVIDER, json=body, headers={'PAYMENT-SIGNATURE': head, 'X-PAYMENT': head})
            if r2.status_code != 200:
                print(f"[agent pay] {cat['id']}: provider {r2.status_code} {r2.text[:400]}")
                return '', 0.0
            answer = r2.json()
            # A receipt records the accepted x402 charge without retaining the
            # signed transaction, bearer header, prompt, or model response.
            receipt = {'id': rs.hashlib.sha256(head.encode()).hexdigest()[:20], 'cat': cat['id'], 'at': rs.time.time(),
                       'provider': 'SingIt', 'model': model_id, 'usd': int(entry['amount']) / rs._ap.USDC_SCALE,
                       'tokens': (answer.get('usage') or {}).get('total_tokens'), 'status': 'provider accepted'}
            rs._receipt_write(receipt)   # a disk error never turns an accepted payment into a free call or another route
            said_ = str(answer.get('model') or '')
            rs._heard(route='singit', model=model_id if not said_ or said_.startswith('singit') else said_, tokens=receipt['tokens'])   # SingIt names its router ('singit-ask'): the model we paid for is the one that answered (found live 2026-11-09)
            return ((answer.get('choices') or [{}])[0].get('message') or {}).get('content') or '', receipt['usd']
    except (ValueError, KeyError, rs.httpx.HTTPError) as e:
        print(f"[agent pay] {cat['id']}: {str(e)[:120]}")
        return '', 0.0


async def _singit_free(messages, max_tokens=None):
    """🆓 The no-minimum caller's free tier (no wallet, no key): 20 calls a day, ≤ 400 tokens. → text ('' = used up / refused)."""
    rs = _rs()
    try:
        async with rs.httpx.AsyncClient(timeout=40) as h:
            r = await h.post(rs._ap.PROVIDER, json={'model': rs._ap.FREE_URL_MODEL, 'messages': rs._ap.free_messages(messages), 'max_tokens': min(int(max_tokens or 400), rs._ap.FREE_MAX_TOKENS)})
        if r.status_code != 200:
            return ''
        j_ = r.json(); rs._heard(route='singit free', model=j_.get('model') or rs._ap.FREE_URL_MODEL, tokens=(j_.get('usage') or {}).get('total_tokens'))
        return ((j_.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
    except (rs.httpx.HTTPError, ValueError):
        return ''


async def _think(cat, model, messages, own_key=None, effort=None, max_tokens=None):
    """🧠 The one door for an agent's model call. Inside a proof (COL-2) it also files who really answered: route, model, $, tokens, time."""
    rs = _rs()
    ans = {}; tok = rs._ANSWER.set(ans); t0 = rs.time.perf_counter()
    ktok_ = rs._OR_KNOBS.set((cat.get('brainsCfg') or {}).get('knobs') or None) if isinstance(cat, dict) else None
    try:
        text, usd, via = await rs._think_routes(cat, model, messages, own_key, effort, max_tokens)
    finally:
        if ktok_ is not None:
            rs._OR_KNOBS.reset(ktok_)
        rs._ANSWER.reset(tok)
    ctx = rs._CALL_CTX.get()
    if ctx:
        rs._mind_call(cat, model, ctx, ans, text, usd, via, rs.time.perf_counter() - t0)
    return text, usd, via


async def _think_routes(cat, model, messages, own_key=None, effort=None, max_tokens=None):
    """🧠 ONE route for a trading cat's brain call (owner 2026-10-31: "my agents and Fee default to the no-minimum caller, OpenRouter is my
    fallback; users default to OpenRouter, my caller is theirs"). → (text, $, via). Fee / staff: SingIt from its own wallet → OpenRouter →
    SingIt free → Groq free. A user's cat: its own key / OpenRouter → its wallet on SingIt → the free routes. Never charges FEELESS's
    OpenRouter while the owner switch is off."""
    rs = _rs()
    rs._OR_CAT.set(cat.get('id'))
    if str(model).startswith('local/'):   # 🖥 owner 2026-11-13: OSSY and G4 answer from their own LM Studio or not at all — never a paid or free stand-in
        text, usd = await rs._lm_call(model, messages, max_tokens)
        return (text, 0.0, 'lan' if rs._lm_which(model) == 'LAN' else 'local') if str(text or '').strip() else ('', 0.0, '')
    wallet = rs._pays_itself(cat)   # 💳 owner 2026-11-10: an agent on its own OpenRouter key still falls back to SingIt from its wallet when OpenRouter runs dry
    if (cat.get('personal') or cat.get('proofNote')) and messages and messages[0].get('role') == 'system':   # 🧠 what its owner told it about themselves
        messages = [{**messages[0], 'content': str(messages[0].get('content')) + rs._feat.personal_line(cat)}, *messages[1:]]
    async def paid():
        return await rs._wallet_call(cat, model, messages, max_tokens or rs._lc.OUT_TOK, rs._ap.MAX_CALL_USD) if wallet else ('', 0.0)
    staff = bool(cat.get('ownerStaff') or cat.get('isLeader')) and not own_key   # 🔑 owner 2026-11-10: the owner's and admins' agents (and Fee) think on FEELESS's OpenRouter first, SingIt behind it
    async def router():
        if not own_key and not staff and not rs._brains_live() and not str(model).startswith('local/'):
            return '', 0.0
        return await rs._or_call(model, messages, max_tokens=max_tokens, effort=effort, key=own_key)
    for name, step in ((('openrouter', router), ('singit', paid)) if own_key or staff else (('singit', paid), ('openrouter', router))):
        text, usd = await step()
        if str(text or '').strip():
            return text, usd, name   # 🧾 the OpenRouter receipt is written inside _or_call (every caller, billed even when empty)
    if own_key:
        return '', 0.0, ''
    for name, step in ((f"SingIt free · {rs._ap.FREE_URL_MODEL.split('/')[-1]} stood in", lambda: rs._singit_free(messages, max_tokens)),
                       (f"Groq free · {(rs.os.environ.get('GROQ_MODEL', '').strip() or rs.BACKUP_MODEL).split('/')[-1]} stood in", lambda: rs._groq_backup(messages, max_tokens))):   # the model that REALLY answered
        text = await step()
        if str(text or '').strip():
            return text, 0.0, name
    return '', 0.0, ''


async def _groq_backup(messages, max_tokens=None):
    """🛟 FEELESS covers an agent when OpenRouter can't (owner 2026-10-30): Groq's free tier answers instead. Costs the agent nothing. → text ('' = no backup either)."""
    rs = _rs()
    key = rs.os.environ.get('GROQ_API_KEY', '').strip()
    if not key:
        return ''
    try:
        async with rs.httpx.AsyncClient(timeout=40) as h:
            r = await h.post('https://api.groq.com/openai/v1/chat/completions', headers={'Authorization': f'Bearer {key}'},
                             json={'model': rs.os.environ.get('GROQ_MODEL', '').strip() or rs.BACKUP_MODEL, 'messages': messages, 'max_tokens': min(int(max_tokens or 2000), 4000), 'temperature': 0.2})
        if r.status_code == 200:
            j_ = r.json(); rs._heard(route='groq free', model=j_.get('model') or rs.os.environ.get('GROQ_MODEL', '').strip() or rs.BACKUP_MODEL, tokens=(j_.get('usage') or {}).get('total_tokens'))
            return ((j_.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
        rs._OR_LAST['err'] = 'OpenRouter is out of credit and the free backup is busy. Nothing was charged. Try again in a minute.' if r.status_code == 429 else f'OpenRouter is out of credit and the backup refused the call ({r.status_code}). Nothing was charged.'
    except Exception:
        rs._OR_LAST['err'] = 'OpenRouter is out of credit and the backup did not answer. Nothing was charged.'
    return ''


def _receipt_write(row):
    """🧾 THE model receipt ledger (owner 2026-11-11: $1.66 of Sonnet billed with no row — only _think wrote one). Never raises."""
    rs = _rs()
    try:
        with (rs.DATA_DIR / 'model_receipts.jsonl').open('a') as ledger:
            ledger.write(rs.json.dumps(row, separators=(',', ':')) + '\n')
    except OSError as e:
        print(f"[receipts] write failed: {type(e).__name__}")


def _heard(**kw):
    """The route, model and tokens that really answered, said by the caller that got the answer. The last one to answer wins."""
    rs = _rs()
    a = rs._ANSWER.get()
    if a is not None:
        a.clear(); a.update(kw)


def _mind_call(cat, model, ctx, ans, text, usd, via, secs):
    """🧾 One line per model call made for a proof (data/mind_calls.jsonl): who answered, $, tokens, time. A write error never stops the proof."""
    rs = _rs()
    minds = list(ctx.get('minds') or []); mind = ctx.get('mind') if ctx.get('mind') is not None else (minds.index(model) if model in minds else None)
    row = rs._mission.call_row(cat.get('id'), ctx.get('kind'), ctx.get('ref'), mind, model, ans, via, usd, secs * 1000, bool(str(text or '').strip()), rs.time.time())
    b_ = (cat.get('brainsCfg') or {}) if isinstance(cat, dict) else {}   # Slice 1: what Brains asked this call to use, so the record can show it
    eff_, kn_ = (b_.get('efforts') or {}).get(model), (b_.get('knobs') or {}).get(model)
    if eff_:
        row['effort'] = str(eff_)[:20]
    if kn_:
        row['knobs'] = dict(kn_)
    if rs._kind_voice_on(b_, ctx.get('kind')):
        row['voice'] = True
    try:
        with (rs.DATA_DIR / 'mind_calls.jsonl').open('a') as f_:
            f_.write(rs.json.dumps(row, separators=(',', ':')) + '\n')
    except OSError as e:
        print(f'[mind calls] write failed: {type(e).__name__}')


def lm_stop(now):
    """⏹ Stops what OSSY and G4 are writing, and everything queued behind it. A job asked after this still runs. → how many calls were writing."""
    rs = _rs()
    rs._LM_STOP['at'] = now; n = len(rs._LM_LIVE)
    for t_ in list(rs._LM_LIVE):
        t_.cancel()
    return n


async def _mac_cool(step=5.0):
    """Waits for the Mac to calm down before its model starts. G4 on the desktop does not wait for it. → seconds waited"""
    rs = _rs()
    waited = 0.0; limit = (rs.os.cpu_count() or 8) * rs.MAC_LOAD_PER_CORE
    while waited < rs.MAC_WAIT_S and rs.os.getloadavg()[0] > limit:
        await rs.asyncio.sleep(step); waited += step
    if waited:
        print(f'[lm] the Mac was busy: waited {waited:.0f}s')
    return waited


def _lm_which(model):
    """Which LM Studio answers: local/g4 = the LAN desktop, local/zed = the third judge (its own model on this Mac unless ZED_LLM_BASE_URL says
    otherwise), anything else = this Mac's OSSY."""
    m = str(model)
    return 'LAN' if m.endswith('g4') else 'ZED' if m.endswith('zed') else 'LOCAL'


def _lm_pick(which, ids):
    """The model to ask for. OSSY / G4: their set model if loaded, else what is loaded. ZED: its set model, else a loaded Gemma — NEVER another
    family's model (a Qwen answering as ZED would give two Qwens three votes). None = ZED has nothing it may use."""
    rs = _rs()
    want = rs.os.environ.get(f'{which}_LLM_MODEL')
    if which == 'ZED':
        return want if want and want in ids else next((i for i in ids if 'gemma' in str(i).lower()), None)
    return want if want in ids else (ids[0] if ids else want)


async def _lm_call(model, messages, max_tokens):
    rs = _rs()
    which_ = rs._lm_which(model); asked = rs.time.time()
    if which_ == 'ZED' and not rs.os.environ.get('ZED_LLM_BASE_URL'):
        which_ = 'LOCAL'   # same Mac, same one-at-a-time gate and cool-down as OSSY
    if not rs._SORT_CALL.get():
        rs._LM_ASKED['at'] = asked
    async with rs._LM_GATE.setdefault(which_, rs.asyncio.Semaphore(1)):
        if rs._LM_STOP['at'] >= asked:
            rs._OR_LAST['err'] = 'You stopped it.'
            return '', 0.0
        if which_ == 'LOCAL':
            await rs._mac_cool(); max_tokens = min(int(max_tokens or 1200), rs.MAC_MAX_TOKENS)
        t_ = rs.asyncio.create_task(rs._lm_call_one(model, messages, max_tokens)); rs._LM_LIVE.add(t_)
        try:
            return await t_
        except rs.asyncio.CancelledError:
            if not t_.cancelled():   # the job above was cancelled, not this call
                t_.cancel(); raise
            rs._OR_LAST['err'] = 'You stopped it.'
            return '', 0.0
        finally:
            rs._LM_LIVE.discard(t_)


async def _lm_call_one(model, messages, max_tokens):
    """🖥 One answer from the owner's own LM Studio: local/ossy = this Mac, local/g4 = the desktop on the LAN. Free. → (text, 0.0); '' when it is off. The loaded model is asked for by name, so a stale setting cannot fail it."""
    rs = _rs()
    which = rs._lm_which(model); who = {'LAN': 'G4', 'ZED': 'ZED'}.get(which, 'OSSY')
    base = (rs.os.environ.get(f'{which}_LLM_BASE_URL') or (rs.os.environ.get('LOCAL_LLM_BASE_URL') or 'http://127.0.0.1:1234/v1' if which in ('LOCAL', 'ZED') else '')).rstrip('/')
    if not base:
        rs._OR_LAST['err'] = f'{who} has no LM Studio address.'
        return '', 0.0
    auth = {'Authorization': f"Bearer {rs.os.environ.get(f'{which}_LLM_API_KEY') or (rs.os.environ.get('LOCAL_LLM_API_KEY') if which == 'ZED' else None) or 'lm-studio'}"}
    try:
        async with rs.httpx.AsyncClient(timeout=rs.LOCAL_CALL_S) as h:   # 🕰 a local mind that cannot finish in time is timed out, and the folder says so
            name = (rs._LM_SEEN.get(which) or {}).get('id')
            if not name or rs.time.time() - rs._LM_SEEN[which]['at'] > 300:
                ids = [m.get('id') for m in (await h.get(f'{base}/models', headers=auth, timeout=8)).json().get('data') or [] if 'embed' not in str(m.get('id'))]
                name = rs._lm_pick(which, ids)
                if not name:
                    rs._OR_LAST['err'] = 'ZED needs a Gemma model loaded in LM Studio.'
                    return '', 0.0
                rs._LM_SEEN[which] = {'id': name, 'at': rs.time.time()}
            r = await h.post(f'{base}/chat/completions', headers=auth, json={'model': name, 'messages': messages, 'max_tokens': min(int(max_tokens or 1200), 8000), 'temperature': 0.4, 'stream': False, 'reasoning_effort': 'none'})
        if r.status_code != 200:
            rs._OR_LAST['err'] = f'LM Studio answered {r.status_code}.'
            return '', 0.0
        j_ = r.json(); rs._heard(route='lan' if which == 'LAN' else 'local', model=j_.get('model') or name, tokens=(j_.get('usage') or {}).get('total_tokens'))
        return ((j_.get('choices') or [{}])[0].get('message') or {}).get('content') or '', 0.0
    except Exception as e:
        rs._OR_LAST['err'] = f'{who} timed out.' if isinstance(e, rs.httpx.TimeoutException) else f'LM Studio did not answer ({type(e).__name__}).'
        return '', 0.0


async def _or_call(model, messages, max_tokens=None, effort=None, key=None, backup=False):
    """One decision from OpenRouter; returns (text, $ it cost). The cost is OpenRouter's own report, else the price list estimate.
    `key` = the cat owner's own OpenRouter key from its API drawer (they pay OpenRouter; FEELESS's key is not used)."""
    rs = _rs()
    est = next((m['perDecision'] for m in ((rs._MODELS['rows'] or {}).get('models') or []) if m['id'] == model), 0.0)
    if str(model).startswith('local/'):
        return await rs._lm_call(model, messages, max_tokens)
    plugins = list(rs._OR_PLUGINS.get())
    try:
        async with rs.httpx.AsyncClient(timeout=240 if (max_tokens or 0) >= rs.LONG_WRITE_TOK else 40) as h:   # a whole page is minutes of writing: at 40 s every Sonnet ad page timed out, fell to the 1,500-token route and was stitched into broken scripts (2026-11-11)
            long_write = not effort and (max_tokens or 0) >= rs.LONG_WRITE_TOK   # 🧾 found 2026-11-10: Hy4 spent a whole 6,000-token page budget thinking, wrote nothing and still billed; off, it wrote the full game in half the time and cost
            body = {'model': model, 'messages': messages, 'max_tokens': max_tokens or rs._lc.OUT_TOK, 'temperature': 0.2, **({'reasoning': {'effort': effort}} if effort else {'reasoning': {'enabled': False}} if long_write else {}), 'usage': {'include': True}}
            kn_ = rs._lc.body_knobs(((rs._OR_KNOBS.get() or {}).get(model)) or {})   # 🎛 the owner's saved knobs for THIS model (already clamped to what it supports)
            if kn_:
                body.update({k: v for k, v in kn_.items() if k != 'max_tokens'})
                if kn_.get('max_tokens'):
                    body['max_tokens'] = min(int(kn_['max_tokens']), int(body['max_tokens'])) if not long_write else body['max_tokens']
            extra = {'plugins': plugins, **({'response_format': {'type': 'json_object'}} if any(x['id'] == 'response-healing' for x in plugins) else {})} if plugins else {}
            auth = {'Authorization': f"Bearer {key or rs.os.environ.get('OPENROUTER_API_KEY')}"}
            r = await h.post('https://openrouter.ai/api/v1/chat/completions', headers=auth, json={**body, **extra})
            if extra and r.status_code == 400:   # a model that refuses a plugin still answers without it
                r = await h.post('https://openrouter.ai/api/v1/chat/completions', headers=auth, json=body)
            if long_write and r.status_code == 400:   # a model that must think: ask again with its own default
                r = await h.post('https://openrouter.ai/api/v1/chat/completions', headers=auth, json={**{k: v for k, v in body.items() if k != 'reasoning'}, **extra})
        if r.status_code != 200:   # a refused call costs nothing and says why (it used to read as 'no answer' and bill the estimate)
            rs._OR_LAST['err'] = 'The AI provider account is out of credit. Add credit at OpenRouter, then ask again. Nothing was charged.' if r.status_code == 402 else f'The AI provider refused the call ({r.status_code}). Nothing was charged.'
            if r.status_code == 402:   # the owner hears it (once a day) and credit sales pause
                try:
                    async with rs.httpx.AsyncClient(timeout=8) as h2:
                        await h2.post('http://127.0.0.1:5077/api/reputation/internal/openrouter-check', headers=rs._internal_headers())
                except Exception:
                    pass
                if backup and not key:   # never on the owner's own key: that bill is theirs to fix
                    text_ = await rs._groq_backup(messages, max_tokens)
                    rs._OR_LAST['backup'] = bool(text_)
                    return text_, 0.0
            return '', 0.0
        d = r.json()
        ch_ = (d.get('choices') or [{}])[0]; text = (ch_.get('message') or {}).get('content') or ''
        if not text.strip() and ch_.get('finish_reason') == 'length':   # some models ignore 'off' (GLM), hy4 thinks its whole budget away (owner 2026-11-15 PoB #19): once more with thinking capped
            async with rs.httpx.AsyncClient(timeout=40) as h:
                r2 = await h.post('https://openrouter.ai/api/v1/chat/completions', headers=auth, json={**body, 'reasoning': {'max_tokens': 300}, **extra})
            if r2.status_code == 200:
                d2 = r2.json(); c2 = (d2.get('choices') or [{}])[0]
                if ((c2.get('message') or {}).get('content') or '').strip():
                    d = {**d2, 'usage': {**(d2.get('usage') or {}), 'cost': float((d2.get('usage') or {}).get('cost') or 0) + float((d.get('usage') or {}).get('cost') or 0)}}; ch_ = c2; text = c2['message']['content']
        if not text.strip() and ch_.get('finish_reason') == 'length':   # all thinking, no answer: said plainly (it is still billed by the provider)
            rs._OR_LAST['err'] = f'{model} used its whole reply budget thinking and wrote no answer.'
        rs._heard(route='openrouter (own key)' if key else 'openrouter', model=d.get('model') or model, tokens=(d.get('usage') or {}).get('total_tokens'))
        billed_ = float((d.get('usage') or {}).get('cost') or 0)
        if billed_ > 0:   # 🧾 every billed call, whoever asked and even when the reply came back empty or cut off
            rs._receipt_write({'id': str(d.get('id') or rs.uuid.uuid4().hex)[:40], 'cat': rs._OR_CAT.get(), 'at': rs.time.time(), 'provider': 'OpenRouter', 'model': d.get('model') or model,
                            'usd': billed_, 'tokens': (d.get('usage') or {}).get('total_tokens'), 'status': 'provider reported',
                            'funding': 'owner key' if key else 'FEELESS key', 'finish': ch_.get('finish_reason')})
        return text, float((d.get('usage') or {}).get('cost') or est)
    except Exception:
        return '', 0.0


async def _brain_decide(store, cat, kind, sym, case, owner=None):
    """🚀 Launch a Cat: ask the cat's brain(s). Returns (word, by, why) or None = the rule engine decides (calls off / no credit)."""
    rs = _rs()
    b = cat.get('brainsCfg')
    if not b:
        return None
    now = rs.time.time()
    own_key = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)   # 🔐 its owner's own OpenRouter key: their bill, no FEELESS credit, no owner switch
    if not own_key and not rs._lc.can_ask(b):
        if b.get('billing') == 'payg' and cat.get('status') == 'running':
            cat['status'] = 'stopped'; cat['brainPaused'] = 'out of model credit — top up to start again'
            rs._log_event(store, cat, 'STOPPED', f"{cat['name']} paused: its model credit is used up (pay as you go). Top up to start it again.")
        return None
    if not own_key and not rs._brains_live() and not (cat.get('isLeader') or cat.get('ownerStaff')):   # Fee + staff cats think on the no-minimum caller
        rs._lc.note(b, kind, sym, 'RULES', 'rule engine', 'model calls are off (owner switch) — the rule engine decided', 0, now)
        return None
    models = [owner] if owner else rs._lc.who_asks(b, b.get('asks') or 0)
    answers, partner, why, cost = [], None, '', 0.0
    for m in models:
        mind_ = '\n'.join(x for x in ((cat.get('studio') or {}).get('text'), rs._hv.brief(rs._hv.for_coin(rs._hive_cells(), sym, now))) if x) or None   # 🐝 what the Hive graded on this coin
        text, usd, via = await rs._think(cat, m, rs._lc.ask_messages(b, case, partner, mind_), own_key, (b.get('efforts') or {}).get(m))
        w, why = rs._lc.parse_word(text, kind)
        if via and via not in ('singit', 'openrouter'):   # a stand-in answered: say which model, never pass it off as hers
            why = f"{why} ({via})".strip()
        if not own_key and via == 'openrouter':   # what its wallet / the free routes paid never comes off its FEELESS credit
            rs._lc.charge(b, usd)
        cost += usd
        answers.append((m, w))
        partner = f"{w or 'no answer'}: {why}"
    word = rs._lc.merge(b, answers, kind)
    by = ' + '.join(m.split('/')[-1] for m in models)
    if rs._lc.cloud_check(b, sym, word, by, why, now, together=answers if len(answers) > 1 else None):   # ☁ both brains agree → the head cloud
        rs._log_event(store, cat, 'LEARN', f"☁ head cloud: both brains say {word} ${sym}")
    rs._lc.note(b, kind, sym, word, by, why, cost, now)
    rs._log_event(store, cat, 'LEARN', f"🧠 {by}: {word} ${sym} — {why or 'no reason given'}")
    return word, models[-1], why

