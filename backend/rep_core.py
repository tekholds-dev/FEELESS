"""🧹 Core helpers, RPC layer, web push — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""
import reputation_service as _RSM  # noqa: E402,F401  (body models / annotations; this module is imported at the END of the service)
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401


def _rs():
    import reputation_service
    return reputation_service


def _empty_store():
    return {'creators': {}, 'mints': {}, 'watchlists': {}, 'feed': [], 'funding': {}}


def _load() -> dict:
    rs = _rs()
    if rs.STORE_PATH.exists():
        try:
            store = rs._cached_json(rs.STORE_PATH)
            store.setdefault('watchlists', {})
            store.setdefault('feed', [])
            store.setdefault('funding', {})
            return store
        except Exception:
            pass
    return rs._empty_store()


def _save(store: dict):
    """⚡ Debounced: /observe used to rewrite the 1.8 MB store on EVERY call (208 saves in 5 min).
    Readers get the new copy at once through the parse cache; the file is written ≤ every 15s
    (`_store_flush_loop`) and on stop. Tests write at once."""
    rs = _rs()
    if rs.os.environ.get('PYTEST_CURRENT_TEST') or not rs.STORE_PATH.exists():
        return rs._save_now(store)
    st = rs.STORE_PATH.stat()
    rs._parse_cache[str(rs.STORE_PATH)] = ((st.st_mtime_ns, st.st_size), store)
    rs._store_dirty['on'] = True


def _store_flush():
    rs = _rs()
    if rs._store_dirty['on']:
        hit = rs._parse_cache.get(str(rs.STORE_PATH))
        if hit:
            rs._store_dirty['on'] = False
            rs._save_now(hit[1])


async def _store_flush_loop():
    rs = _rs()
    while True:
        await rs.asyncio.sleep(15)
        try:
            rs._store_flush()
        except Exception:
            pass


def _save_now(store: dict):
    rs = _rs()
    t0 = rs.time.perf_counter()
    rs.STORE_PATH.write_text(rs.json.dumps(store))   # ⚡ no indent: an indented dump runs the pure-Python encoder (6.7s stalls on 2.2 MB)
    st = rs.STORE_PATH.stat()
    rs._parse_cache[str(rs.STORE_PATH)] = ((st.st_mtime_ns, st.st_size), store)   # what was written IS the current version: no re-parse
    rs._json_cost_note('save', rs.STORE_PATH, t0)


async def resolve_creator(chain: str, mint_address: str) -> _RSM.Optional[str]:
    """Resolve a Solana mint's deployer identity. Cached.

    Most pump.fun-style launches renounce mint authority immediately, so it's null
    for the vast majority of new coins and useless as an identity key. Instead we
    fall back to the fee payer of the mint's earliest known transaction — the
    standard on-chain proxy for "who deployed this" used by rug-detection tooling.
    """
    rs = _rs()
    if chain != 'solana':
        key = f'{chain}:{mint_address}'
        if key not in rs._mint_authority_cache:
            creator = await rs.resolve_evm_creator(chain, mint_address)
            rs._mint_authority_cache[key] = {'identity': creator, 'renounced': False} if creator else None
        return rs._mint_authority_cache[key]
    if mint_address in rs._mint_authority_cache:
        return rs._mint_authority_cache[mint_address]
    identity = None
    renounced = False
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            info_result = await rs._rpc(http, 'getAccountInfo', [mint_address, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}])
            info = (((info_result or {}).get('value') or {}).get('data') or {}).get('parsed', {}).get('info', {})
            identity = info.get('mintAuthority')
            renounced = identity is None and info.get('isInitialized', True)

            if not identity:
                # Jupiter's token index records the deployer ("dev") for Solana coins — exact and fast.
                try:
                    j = (await http.get('https://lite-api.jup.ag/tokens/v2/search', params={'query': mint_address})).json()
                    identity = next((t.get('dev') for t in j if t.get('id') == mint_address and t.get('dev')), None)
                except Exception:
                    identity = None
            if not identity:
                signatures = await rs._rpc(http, 'getSignaturesForAddress', [mint_address, {'limit': 1000}])
                # Only trust "oldest tx fee payer" when we can actually see the whole history; on a busy
                # coin the 1,000th-newest tx is some random trader, not the creator.
                if signatures and len(signatures) < 1000:
                    oldest = signatures[-1].get('signature')
                    tx = await rs._rpc(http, 'getTransaction', [oldest, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}])
                    keys = (((tx or {}).get('transaction') or {}).get('message') or {}).get('accountKeys', [])
                    if keys:
                        identity = keys[0].get('pubkey') if isinstance(keys[0], dict) else keys[0]
    except Exception:
        identity = None
    result = {'identity': identity, 'renounced': renounced}
    rs._mint_authority_cache[mint_address] = result
    return result


def _creator_key(chain: str, address: str) -> str:
    return f'{chain}:{address}'


async def resolve_funding_source(chain: str, wallet_address: str) -> _RSM.Optional[str]:
    """Resolves who funded a wallet's very first transaction — the standard on-chain
    signal real analytics tools (Arkham, Nansen-style) use to cluster wallets that
    look independent but are actually operated by the same person. If two "different"
    creator wallets were both funded from the same upstream wallet, that's a real,
    verifiable link — not a guess.
    """
    rs = _rs()
    if chain != 'solana':
        return None
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            signatures = await rs._rpc(http, 'getSignaturesForAddress', [wallet_address, {'limit': 1000}])
            if not signatures:
                return None
            oldest = signatures[-1].get('signature')
            tx = await rs._rpc(http, 'getTransaction', [oldest, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}])
            keys = (((tx or {}).get('transaction') or {}).get('message') or {}).get('accountKeys', [])
            if not keys:
                return None
            fee_payer = keys[0].get('pubkey') if isinstance(keys[0], dict) else keys[0]
            # The fee payer of this wallet's first-ever transaction is the funding source,
            # unless this wallet WAS the fee payer (it funded itself / was the first mover).
            return fee_payer if fee_payer != wallet_address else None
    except Exception:
        return None


def _push_feed(store: dict, chain: str, address: str, kind: str, detail: str):
    rs = _rs()
    store.setdefault('feed', []).insert(0, {
        'id': rs.uuid.uuid4().hex, 'chain': chain, 'address': address,
        'type': kind, 'detail': detail, 'ts': rs.time.time(),
    })
    store['feed'] = store['feed'][:500]


def token_outcome(t: dict, now: float = None) -> str:
    """Outcome from live market snapshots: 'dumped', 'dead', or 'alive'. Pump.fun curve coins
    have no liquidity figure, so market-cap collapse is the reliable signal there."""
    rs = _rs()
    now = now or rs.time.time()
    if t.get('status') == 'rugged':
        return 'dumped'
    m = t.get('market') or {}
    age = now - (t.get('firstSeenAt') or now)
    if not m.get('checkedAt'):
        return 'unknown'
    if not m.get('listed'):
        return 'dead' if age > 24 * 3600 else 'unknown'
    mc, peak, ch = m.get('marketCap') or 0, m.get('peakMarketCap') or 0, m.get('change24h')
    if age >= rs.DUMP_MIN_AGE and ((peak > 0 and mc <= peak * 0.3) or (ch is not None and ch <= -70) or (mc and mc < 2000 and age > 6 * 3600)):
        return 'dumped'
    return 'alive'


def score_creator(entry: dict) -> dict:
    """Brutal, evidence-only scoring. No market evidence → no score. Launch volume alone never earns trust."""
    rs = _rs()
    tokens = entry.get('tokens', {})
    total = len(tokens)
    rugged = sum(1 for t in tokens.values() if t.get('status') == 'rugged')
    sustained = sum(1 for t in tokens.values() if t.get('status') == 'sustained')
    renounced = sum(1 for t in tokens.values() if t.get('authorityRenounced'))
    symbols = [(t.get('symbol') or '').strip().upper() for t in tokens.values()]
    distinct = len({s for s in symbols if s}) or (1 if total else 0)
    clones = max(0, total - distinct)
    now = rs.time.time()
    outcomes = [rs.token_outcome(t, now) for t in tokens.values()]
    dumped, dead = outcomes.count('dumped'), outcomes.count('dead')
    judged = sum(1 for o in outcomes if o != 'unknown')
    alive = [t for t in tokens.values() if rs.token_outcome(t, now) == 'alive']
    alive_big = sum(1 for t in alive if ((t.get('market') or {}).get('marketCap') or 0) >= 100_000)
    alive_traded = sum(1 for t in alive if ((t.get('market') or {}).get('volume24h') or 0) >= 10_000)
    ghost = sum(1 for t in alive if not ((t.get('market') or {}).get('volume24h') or 0))
    # Serial launching: more than 2 launches inside any 24h window is a farm pattern.
    times = sorted(t.get('firstSeenAt') or 0 for t in tokens.values() if t.get('firstSeenAt'))
    burst = max((sum(1 for u in times if 0 <= u - x <= 86400) for x in times), default=0)
    serial_launcher = burst >= 3
    base = {'tokenCount': total, 'distinctTickers': distinct, 'cloneCount': clones, 'ruggedCount': rugged, 'dumpedCount': dumped, 'deadCount': dead,
            'judgedCount': judged, 'bigWinners': alive_big, 'sustainedCount': sustained, 'renouncedCount': renounced,
            'serialLauncher': serial_launcher, 'launchBurst24h': burst, 'ghostCount': ghost}
    if rugged:
        return {**base, 'score': max(0, 10 - 5 * rugged), 'badge': 'flagged', 'serialDumper': True, 'confidence': 'high', 'reasons': [f'{rugged} rug(s) on record']}
    if judged == 0:
        return {**base, 'score': None, 'badge': 'unproven', 'serialDumper': False, 'confidence': 'none',
                'reasons': ['No market evidence yet — FEELESS will not score a creator on launches alone.'] + (['Rapid-fire launching detected.'] if serial_launcher else [])}
    score = 40
    score += min(sustained, 5) * 10 + min(alive_big, 5) * 8 + min(alive_traded, 5) * 3
    score -= min(dumped, 8) * 15 + min(dead, 8) * 8 + min(clones, 6) * 8 + min(ghost, 6) * 5
    if serial_launcher:
        score -= 10 * (burst - 2)
    # Reputation is a long-lasting asset, not just a risk flag: a clean track record earns a
    # growing tenure bonus the longer it holds up — this is the only way to reach the top tier.
    tenure_days = (now - (entry.get('firstSeen') or now)) / 86400
    clean = not dumped and not rugged and not clones
    tenure_bonus = 0
    if clean:
        if tenure_days >= 365: tenure_bonus = 20
        elif tenure_days >= 180: tenure_bonus = 12
        elif tenure_days >= 90: tenure_bonus = 6
        elif tenure_days >= 30: tenure_bonus = 2
    score += tenure_bonus
    score = max(0, min(100, score))
    dump_rate = dumped / judged if judged else 0
    serial_dumper = dumped >= 2 and dump_rate >= 0.5
    reasons = []
    if dumped: reasons.append(f'{dumped}/{judged} judged launches dumped')
    if dead: reasons.append(f'{dead} launches died')
    if clones: reasons.append(f'{clones} cloned tickers')
    if serial_launcher: reasons.append(f'{burst} launches inside 24h (farm pattern)')
    if ghost: reasons.append(f'{ghost} listed with zero volume')
    if sustained or alive_big: reasons.append(f'{sustained} sustained, {alive_big} over $100K')
    veteran = clean and tenure_days >= 180
    if tenure_bonus: reasons.append(f'{int(tenure_days)}d clean track record (+{tenure_bonus})')
    if serial_dumper or dump_rate >= 0.34 and dumped >= 2:
        badge = 'flagged'
    elif judged >= 2 and not dumped and not clones and not serial_launcher and (sustained or alive_big) and score >= 65:
        badge = 'veteran' if veteran and score >= 80 else 'trusted'
    elif serial_launcher or dumped or clones or ghost:
        badge = 'risky'
    else:
        badge = 'building'
    return {**base, 'score': score, 'badge': badge, 'serialDumper': bool(serial_dumper), 'tenureDays': int(tenure_days), 'veteran': veteran,
            'confidence': 'high' if judged >= 6 else 'medium' if judged >= 3 else 'low', 'reasons': reasons}


def _hygiene(creator, scored):
    """Launch hygiene from FEELESS intel: snipers + bundled wallets across this creator's launches."""
    rs = _rs()
    h = rs._json_load(rs.DATA_DIR / 'hygiene.json', {}).get(creator) or {}
    launches = h.get('launches') or {}
    if not launches:
        return {'hygiene': None}
    snip = sum(v.get('snipers', 0) for v in launches.values()); bund = sum(v.get('bundled', 0) for v in launches.values())
    n = len(launches)
    penalty = min(40, round((snip / n) * 1.0 + (bund / n) * 3.0))
    score = scored.get('score')
    adj = max(0, score - penalty) if isinstance(score, (int, float)) else score
    badge = scored.get('badge')
    if n >= 2 and bund / n >= 5:
        badge = 'flagged'
    return {'score': adj, 'badge': badge, 'hygiene': {'launches': n, 'avgSnipers': round(snip / n, 1), 'avgBundled': round(bund / n, 1), 'penalty': penalty}}


async def fetch_token_markets(chain: str, mints: list) -> dict:
    """Live market state per token mint from DexScreener's token endpoint (batched, 30 max).
    A mint with no pairs isn't listed on any DEX yet — for pump.fun that usually means it
    never left the bonding curve."""
    rs = _rs()
    now = rs.time.time()
    out, missing = {}, []
    for m in mints:
        hit = rs._market_cache.get(m)
        if hit and now - hit[0] < rs.MARKET_TTL:
            out[m] = hit[1]
        else:
            missing.append(m)
    async with rs.httpx.AsyncClient(timeout=8) as http:
        for i in range(0, len(missing), 30):
            batch = missing[i:i + 30]
            try:
                res = await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{",".join(batch)}')
                pairs = (res.json() or {}).get('pairs') or [] if res.status_code == 200 else None
            except Exception:
                pairs = None
            if pairs is None:
                continue
            best = {}
            for p in pairs:
                if p.get('chainId') != chain:
                    continue
                mint = (p.get('baseToken') or {}).get('address')
                liq = ((p.get('liquidity') or {}).get('usd')) or 0
                if mint in batch and (mint not in best or liq > (((best[mint].get('liquidity') or {}).get('usd')) or 0)):
                    best[mint] = p
            for mint in batch:
                p = best.get(mint)
                info = {'listed': False} if not p else {
                    'listed': True, 'url': p.get('url'), 'pairAddress': p.get('pairAddress'), 'dexId': p.get('dexId'),
                    'priceUsd': p.get('priceUsd'), 'marketCap': p.get('marketCap') or p.get('fdv'),
                    'liquidityUsd': (p.get('liquidity') or {}).get('usd'), 'volume24h': (p.get('volume') or {}).get('h24'),
                    'change24h': (p.get('priceChange') or {}).get('h24'), 'imageUrl': (p.get('info') or {}).get('imageUrl'),
                }
                rs._market_cache[mint] = (now, info)
                out[mint] = info
    return out


def trust_verdict(scoring: dict, tokens: list, linked: list) -> dict:
    """Plain-language verdict with every reason spelled out, so a user can see WHY."""
    reasons = []
    good = bad = 0
    if scoring['ruggedCount']:
        reasons.append(('bad', f"{scoring['ruggedCount']} token(s) lost 80%+ of peak liquidity after launch (confirmed rug pattern)."))
        bad += 3
    if scoring.get('serialDumper'):
        reasons.append(('bad', f"Serial dumper: {scoring['dumpedCount']} of {scoring['judgedCount']} launches collapsed 70%+ from their peak or died under $2K market cap."))
        bad += 4
    elif scoring.get('dumpedCount'):
        reasons.append(('bad', f"{scoring['dumpedCount']} launch(es) collapsed 70%+ after launch."))
        bad += 1 + scoring['dumpedCount']
    if scoring.get('bigWinners'):
        reasons.append(('good', f"{scoring['bigWinners']} launch(es) are alive above $100K market cap right now."))
        good += 2
    if scoring['cloneCount'] >= 2:
        reasons.append(('bad', f"Relaunched the same ticker {scoring['cloneCount']} extra times — clone/spam behavior."))
        bad += 2
    listed = [t for t in tokens if (t.get('market') or {}).get('listed')]
    known = [t for t in tokens if t.get('market') is not None]
    if known:
        dead = len(known) - len(listed)
        if dead and dead / len(known) >= 0.7 and len(known) >= 3:
            reasons.append(('bad', f"{dead} of {len(known)} launches never reached a DEX listing — most launches went nowhere."))
            bad += 1
        alive = [t for t in listed if ((t['market'].get('liquidityUsd') or 0) >= 10000)]
        if alive:
            reasons.append(('good', f"{len(alive)} launch(es) currently hold $10K+ liquidity on a DEX."))
            good += 1
    if scoring['sustainedCount']:
        reasons.append(('good', f"{scoring['sustainedCount']} token(s) survived 3+ days with liquidity intact."))
        good += 2
    if scoring['renouncedCount'] == scoring['tokenCount'] and scoring['tokenCount']:
        reasons.append(('neutral', 'Mint authority renounced on every launch (standard on pump.fun — not a trust signal on its own).'))
    flagged_links = [l for l in linked if l.get('ruggedCount') or l.get('cloneCount', 0) >= 2]
    if flagged_links:
        reasons.append(('bad', f"Shares a funding wallet with {len(flagged_links)} flagged/clone-farming wallet(s)."))
        bad += 2
    elif linked:
        reasons.append(('neutral', f"Shares a funding wallet with {len(linked)} other tracked creator(s) — likely one operator."))
    if scoring['tokenCount'] < 3 and not scoring['sustainedCount']:
        reasons.append(('neutral', 'Short history — not enough launches yet to judge reliably.'))
    if bad >= 3 or scoring['ruggedCount'] or scoring.get('serialDumper'):
        level, label = 'avoid', 'High risk — avoid'
    elif bad:
        level, label = 'caution', 'Caution'
    elif good >= 2:
        level, label = 'trusted', 'Looks trustworthy'
    else:
        level, label = 'unknown', 'Not enough evidence'
    return {'level': level, 'label': label, 'reasons': [{'tone': t, 'text': x} for t, x in reasons]}


def _apply_markets(entry: dict, markets: dict):
    rs = _rs()
    now = rs.time.time()
    for t in entry.get('tokens', {}).values():
        info = markets.get(t.get('baseTokenAddress'))
        if info is None:
            continue
        prev = t.get('market') or {}
        mc = info.get('marketCap') or 0
        t['market'] = {**info, 'checkedAt': now, 'peakMarketCap': max(prev.get('peakMarketCap') or 0, mc)}


async def _refresh_all_markets():
    """Background: keep every tracked launch's market outcome fresh so scores reflect reality."""
    rs = _rs()
    while True:
        try:
            store = rs._load()
            by_chain = {}
            for entry in store['creators'].values():
                for t in entry['tokens'].values():
                    if t.get('baseTokenAddress'):
                        by_chain.setdefault(entry['chain'], []).append(t['baseTokenAddress'])
            for chain, mints in by_chain.items():
                for i in range(0, len(mints), 300):
                    markets = await rs.fetch_token_markets(chain, mints[i:i + 300])
                    async with rs._lock:
                        st = rs._load()
                        for entry in st['creators'].values():
                            if entry['chain'] == chain:
                                rs._apply_markets(entry, markets)
                        rs._save(st)
                    await rs.asyncio.sleep(2)
        except Exception:
            pass
        await rs.asyncio.sleep(300)


async def _loop_lag_dump():
    # the catcher's own page for checking without an HQ sign-in (function names only, never data)
    rs = _rs()
    while True:
        await rs.asyncio.sleep(30)
        try:
            await rs.asyncio.to_thread(rs._json_save, rs.DATA_DIR / 'loop_lag.json', {**rs._loop_lag.WATCH.view(), 'json': sorted(([k, v[0], round(v[1], 2)] for k, v in rs._json_cost.items()), key=lambda r: -r[2])[:25]})
        except Exception:
            pass
        try:   # 🩺 what browsers FEEL (the lag catcher's own reports, last 15 min): routes by p95, pages by fps / blocked ms, the FX governor's counts — route + page names only
            cut_ = rs.time.time() - 900
            rec_ = [x for x in rs._perf_samples if x['at'] >= cut_]
            fx_ = [x.get('fx') for x in rec_ if x.get('fx')][-6:]
            await rs.asyncio.to_thread(rs._json_save, rs.DATA_DIR / 'perf_view.json', {**rs.perf.summarize(rec_), 'fx': fx_, 'at': rs.time.time()})
        except Exception:
            pass


def upload_cap(mime: str, role: str) -> int:
    """Bytes allowed per upload. Everyone: 15 MB stills / 40 MB GIFs (owner 2026-10-26: "backgrounds shouldn't have an MB cap" — uploads need no sign-in,
    so a ceiling stays against disk-filling; 20 / hour / IP). HQ admins: 40 MB. The creator: 40 MB stills, GIFs up to the memory guard."""
    rs = _rs()
    if role == 'owner':
        return rs.OWNER_GIF_CAP if mime == 'image/gif' else 40_000_000
    if role == 'admin':
        return 40_000_000
    return 40_000_000 if mime == 'image/gif' else 15_000_000


async def _ip_hit(store, request, n, win):
    """🔒 Audit #8: one per-device limiter (real IP via _guard.request_ip). → False when this device used its n calls in win seconds.
    🚦 SITE-8: `store` is a SharedHits, so the limit holds across every worker; the transaction runs in a thread (never stalls the loop)."""
    rs = _rs()
    ip = rs._guard.request_ip(request)
    try:
        return await rs.asyncio.to_thread(store.hit, ip, n, win)
    except Exception:   # the shared file is locked/broken: keep limiting in this process instead of failing the route
        now = rs.time.time(); k = (store.ns, ip)
        hits = [t for t in rs._IP_HIT_LOCAL.get(k, []) if now - t < win]
        if len(hits) >= n:
            return False
        rs._IP_HIT_LOCAL[k] = hits + [now]
        if len(rs._IP_HIT_LOCAL) > 5000:
            rs._IP_HIT_LOCAL.clear()
        return True


async def _coin_card(http, mint):
    """Deepest pool + symbol/name/market cap for alerts. DexScreener first, Jupiter when the coin isn't indexed yet."""
    card = {'pair': mint, 'symbol': None, 'name': None, 'mcap': None}
    try:
        pools = (await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{mint}')).json().get('pairs') or []
        if pools:
            top = max(pools, key=lambda p: (p.get('liquidity') or {}).get('usd') or 0)
            base = top.get('baseToken') or {}
            card.update(pair=top.get('pairAddress') or mint, symbol=base.get('symbol'), name=base.get('name'), mcap=top.get('marketCap') or top.get('fdv'))
    except Exception:
        pass
    if not card['symbol']:
        try:
            hit = next((t for t in (await http.get('https://lite-api.jup.ag/tokens/v2/search', params={'query': mint})).json() if t.get('id') == mint), None)
            if hit:
                card.update(symbol=hit.get('symbol'), name=hit.get('name'), mcap=card['mcap'] or hit.get('mcap'))
        except Exception:
            pass
    card['symbol'] = card['symbol'] or f'{mint[:4]}…{mint[-4:]}'
    return card


def _early_buy(tx, payer, mint, supply):
    """🕵 One early transaction → {w, slot, sol, pct} when the payer RECEIVED this coin (a buy), else None. Public tx data only."""
    rs = _rs()
    try:
        meta = tx.get('meta') or {}
        amt = lambda bals: sum(rs._fuse._f((b.get('uiTokenAmount') or {}).get('uiAmount')) for b in bals or [] if b.get('mint') == mint and b.get('owner') == payer)
        got = amt(meta.get('postTokenBalances')) - amt(meta.get('preTokenBalances'))
        if got <= 0:
            return None
        pre, post = meta.get('preBalances') or [0], meta.get('postBalances') or [0]
        sol = max(0.0, (rs._fuse._f(pre[0]) - rs._fuse._f(post[0])) / 1e9)
        return {'w': payer, 'slot': tx.get('slot'), 'sol': round(sol, 4), 'pct': round(got / supply * 100, 3) if supply else None}
    except Exception:
        return None


def chain_rpc_url(chain: str) -> _RSM.Optional[str]:
    rs = _rs()
    if chain == 'solana':
        return rs.RPC_POOL[0] if rs.RPC_POOL else None
    return rs.os.environ.get(f'{chain.upper()}_RPC_URL') or rs.CHAIN_RPC_DEFAULTS.get(chain)


async def _ping_chain(http, chain):
    rs = _rs()
    url = rs.chain_rpc_url(chain)
    if not url:
        return {'chain': chain, 'ok': False, 'error': 'no endpoint'}
    method = 'getSlot' if chain == 'solana' else 'sui_getLatestCheckpointSequenceNumber' if chain == 'sui' else 'eth_blockNumber'
    started = rs.time.time()
    try:
        r = await http.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': []})
        body = r.json()
        result = body.get('result')
        head = int(result, 16) if isinstance(result, str) and result.startswith('0x') else int(result) if result is not None else None
        return {'chain': chain, 'ok': head is not None, 'head': head, 'latencyMs': round((rs.time.time() - started) * 1000),
                'dedicated': bool(rs.os.environ.get('SOLANA_RPC_URL' if chain == 'solana' else f'{chain.upper()}_RPC_URL')),
                'host': url.split('/')[2].split('?')[0]}
    except Exception as exc:
        return {'chain': chain, 'ok': False, 'error': type(exc).__name__, 'host': url.split('/')[2].split('?')[0]}


async def resolve_evm_creator(chain: str, token: str) -> _RSM.Optional[str]:
    """Contract deployer via Etherscan API v2 (one key covers every EVM chain we support)."""
    rs = _rs()
    key = rs.os.environ.get('ETHERSCAN_API_KEY')
    cid = rs.EVM_CHAIN_IDS.get(chain)
    if not key or not cid:
        return None
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            r = await http.get('https://api.etherscan.io/v2/api', params={'chainid': cid, 'module': 'contract', 'action': 'getcontractcreation', 'contractaddresses': token, 'apikey': key})
            rows = (r.json() or {}).get('result') or []
            return rows[0].get('contractCreator') if isinstance(rows, list) and rows else None
    except Exception:
        return None


async def _refresh_globe():
    """$1M+ coins per chain for the globe, from FEELESS's own DexScreener-backed market feed
    (strictly per chain — a coin only ever orbits the network it actually trades on)."""
    rs = _rs()
    await rs.asyncio.sleep(20)
    while True:
        tokens, ok_chains = {}, set()
        async with rs.httpx.AsyncClient(timeout=20) as http:
            for chain in rs.GLOBE_NETS:
                # page 1 = boosted/trending; page 2 = the chain's main-DEX pools (where the $10M+ coins live)
                for params in ({'kind': 'trending'}, {'kind': 'trending', 'source': 'search'}, {'kind': 'new'}):
                    try:
                        r = await http.get('http://127.0.0.1:5001/api/market/feed', params={'chain': chain, **params})
                        pairs = r.json().get('pairs') or [] if r.status_code == 200 else []
                    except Exception:
                        pairs = []
                    for p in pairs:
                        if p.get('chainId') != chain:
                            continue
                        mc = p.get('marketCap') or p.get('fdv') or 0
                        if not mc or mc < rs.GLOBE_MIN_MC:
                            continue
                        ok_chains.add(chain)
                        bt = p.get('baseToken') or {}
                        row = {'chain': chain, 'address': bt.get('address'), 'symbol': bt.get('symbol'), 'name': bt.get('name'),
                               'imageUrl': (p.get('info') or {}).get('imageUrl'), 'marketCap': mc, 'mcKind': 'market cap' if p.get('marketCap') else 'FDV',
                               'liquidityUsd': (p.get('liquidity') or {}).get('usd'), 'priceUsd': p.get('priceUsd'),
                               'change24h': (p.get('priceChange') or {}).get('h24'), 'volume24h': (p.get('volume') or {}).get('h24') or 0,
                               'pairAddress': p.get('pairAddress')}
                        key = f"{chain}:{row['address']}"
                        if key not in tokens or tokens[key]['volume24h'] < row['volume24h']:
                            tokens[key] = row
                    await rs.asyncio.sleep(0.5)
        if tokens:
            prev = (rs._globe_cache['data'] or {}).get('tokens') or []
            kept = [t for t in prev if t['chain'] not in ok_chains]
            rs._globe_cache.update(at=rs.time.time(), data={'tokens': sorted(list(tokens.values()) + kept, key=lambda t: -t['marketCap']),
                                                      'minMarketCap': rs.GLOBE_MIN_MC, 'source': 'DexScreener via FEELESS market feed',
                                                      'chains': sorted(ok_chains | {t['chain'] for t in kept}), 'at': rs.time.time()})
        await rs.asyncio.sleep(300)


def _any_agent_wallets():
    """🚫 Every AI agent's OWN wallet (feecats.json, parsed once per version). An agent may launch coins on any other site, but these
    wallets can never launch a coin or make an agent ON FEELESS (owner 2026-10-31: "hardcode that the general agents can't")."""
    rs = _rs()
    store = rs._json_load(rs.DATA_DIR / 'feecats.json', {})
    return {str((c.get('agentWallet') or {}).get('address')) for c in (store.get('cats') or {}).values() if (c.get('agentWallet') or {}).get('address')}


def _vapid():
    rs = _rs()
    if rs.VAPID_PATH.exists():
        return rs.json.loads(rs.VAPID_PATH.read_text())
    from py_vapid import Vapid01
    from cryptography.hazmat.primitives import serialization
    v = Vapid01()
    v.generate_keys()
    priv = v.private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    pub_raw = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    data = {'private': priv, 'public': rs.base64.urlsafe_b64encode(pub_raw).decode().rstrip('=')}
    rs.VAPID_PATH.write_text(rs.json.dumps(data))
    try:
        rs.os.chmod(rs.VAPID_PATH, 0o600)
    except OSError:
        pass
    return data


def _push_load():
    rs = _rs()
    if rs.PUSH_PATH.exists():
        try:
            return rs._cached_json(rs.PUSH_PATH)
        except Exception:
            pass
    return {'subs': {}}


def _push_save(d):
    rs = _rs()
    rs.PUSH_PATH.write_text(rs.json.dumps(d))


def _sub_id(sub):
    rs = _rs()
    return rs.hashlib.sha256((sub.get('endpoint') or '').encode()).hexdigest()[:24]


def _push_prefs(prefs, prev, session):
    """🔒 A phone only gets a wallet's alerts if it proved that wallet (its signed session) or this same phone already held it. A claim without proof keeps the watchlist alerts and drops the wallet."""
    rs = _rs()
    out = dict(prefs or {}); claim = str(out.get('address') or '')
    if claim and claim != (prev or {}).get('address'):
        owner = rs.session_address(session) if session else None
        if not owner or rs.primary_of(owner) != rs.primary_of(claim):
            out.pop('address', None)
    return out


def _inbox_alert(entry, kind, text, w):
    """A phone alert also lands in the wallet's in-app inbox (one stream), with the rule and its data source."""
    rs = _rs()
    address = (entry.get('prefs') or {}).get('address')
    if address:
        rs.notify(address, 'alert', text, f"/?coin={w['chainId']}:{w['pairAddress']}", push=False,
               meta={'symbol': w.get('symbol'), 'rule': kind, 'claim': text, 'source': rs.ALERT_SOURCE.get(kind, 'Watchlist rule')})


def _send_push(sub, title, body, url='/terminal/watchlist', tag=None):
    rs = _rs()
    from pywebpush import webpush, WebPushException
    from py_vapid import Vapid01
    v = rs._vapid()
    try:
        webpush(subscription_info=sub, data=rs.json.dumps({'title': title, 'body': body, 'url': url, 'tag': tag}),
                vapid_private_key=Vapid01.from_pem(v['private'].encode()), vapid_claims={'sub': 'mailto:alerts@feeless.app'}, ttl=600)
        return 'ok'
    except WebPushException as exc:
        code = getattr(getattr(exc, 'response', None), 'status_code', None)
        return 'gone' if code in (404, 410) else f'error {code}'
    except Exception as exc:
        return f'error {type(exc).__name__}'


def _in_quiet(prefs):
    rs = _rs()
    qs, qe = prefs.get('quietStart'), prefs.get('quietEnd')
    if qs is None or qe is None:
        return False
    h = rs.time.localtime().tm_hour
    return (qs <= h < qe) if qs < qe else (h >= qs or h < qe)


async def _evaluate_alerts():
    """Server-side watcher: every 30s, evaluate every subscriber's rules against live data."""
    rs = _rs()
    while True:
        try:
            d = rs._push_load()
            watched = {}
            for entry in d['subs'].values():
                for w in entry['watch']:
                    watched.setdefault(w['chainId'], set()).add(w['pairAddress'])
            live = {}
            async with rs.httpx.AsyncClient(timeout=10) as http:
                for chain, pairs in watched.items():
                    pairs = sorted(pairs)
                    for i in range(0, len(pairs), 30):
                        try:
                            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{",".join(pairs[i:i + 30])}')
                            for p in (r.json() or {}).get('pairs') or []:
                                live[f"{chain}:{p.get('pairAddress')}"] = p
                        except Exception:
                            pass
                sol_mints = sorted({w['mint'] for e in d['subs'].values() for w in e['watch'] if w['chainId'] == 'solana' and w.get('mint')})
                jup = {}
                for i in range(0, len(sol_mints), 50):
                    try:
                        r = await http.get(f'https://lite-api.jup.ag/price/v3?ids={",".join(sol_mints[i:i + 50])}')
                        jup.update({k: float(v.get('usdPrice') or 0) for k, v in (r.json() or {}).items()})
                    except Exception:
                        pass
                fee_reads = {}
                sol_pairs = [{'chainId': 'solana', 'pairAddress': a} for a in sorted(watched.get('solana', set()))]
                if sol_pairs:
                    try:
                        r = await http.post('http://127.0.0.1:5088/api/cats/evaluate', json={'pairs': sol_pairs})
                        fee_reads = (r.json() or {}).get('reads') or {}
                    except Exception:
                        pass
            rep = rs._load()
            creator_of = {}
            for c in rep['creators'].values():
                for t in c['tokens'].values():
                    if t.get('baseTokenAddress'):
                        creator_of[t['baseTokenAddress']] = c
            now = rs.time.time()
            dead = []
            for sid, entry in d['subs'].items():
                prefs = entry['prefs']
                cooldown = max(5, int(prefs.get('cooldownMin') or 30)) * 60
                quiet = rs._in_quiet(prefs)
                for w in entry['watch']:
                    p = live.get(f"{w['chainId']}:{w['pairAddress']}")
                    if not p:
                        continue
                    rules, state = w['rules'], w.setdefault('state', {})
                    sym = w.get('symbol') or (p.get('baseToken') or {}).get('symbol') or 'coin'
                    price = jup.get(w.get('mint')) or float(p.get('priceUsd') or 0)
                    liq = float((p.get('liquidity') or {}).get('usd') or 0)
                    if not w.get('watchedLiq') and liq:
                        w['watchedLiq'] = liq
                    if prefs.get('minLiquidity') and liq < float(prefs['minLiquidity']):
                        continue
                    fired = []
                    base = float(w.get('watchedPrice') or 0)
                    if base and price:
                        move = (price / base - 1) * 100
                        if rules.get('up') and move >= rules['up']:
                            fired.append(('up', f'{sym} is up {move:+.1f}% since you starred it'))
                        elif rules.get('down') and move <= -rules['down']:
                            fired.append(('down', f'{sym} is down {move:+.1f}% since you starred it'))
                        elif abs(move) < min(rules.get('up') or 999, rules.get('down') or 999) / 2:
                            state.pop('up', None); state.pop('down', None)
                    if rules.get('above') and price >= float(rules['above']):
                        fired.append(('above', f"{sym} hit your target {price:.8g} (≥ {float(rules['above']):.8g})"))
                    if rules.get('below') and price and price <= float(rules['below']):
                        fired.append(('below', f"{sym} fell to {price:.8g} (≤ {float(rules['below']):.8g})"))
                    h24 = float((p.get('priceChange') or {}).get('h24') or 0)
                    if rules.get('move24h') and abs(h24) >= rules['move24h']:
                        fired.append(('move24h', f'{sym} moved {h24:+.1f}% in 24h'))
                    if rules.get('liqDrain') and w.get('watchedLiq') and liq and liq <= w['watchedLiq'] * (1 - rules['liqDrain'] / 100):
                        fired.append(('liqDrain', f'{sym} liquidity drained {(1 - liq / w["watchedLiq"]) * 100:.0f}% — possible exit'))
                    vol = p.get('volume') or {}
                    m5, h24v = float(vol.get('m5') or 0), float(vol.get('h24') or 0)
                    if rules.get('volSpike') and h24v > 0 and m5 * 288 >= rules['volSpike'] * h24v and m5 > 500:
                        fired.append(('volSpike', f'{sym} volume spike: last 5m running {m5 * 288 / h24v:.1f}× its daily pace'))
                    read = fee_reads.get(w['pairAddress'])
                    if rules.get('feeRead') and read and read.get('passes') and not state.get('feeWasPass'):
                        fired.append(('feeRead', f"Fee would buy {sym} now — it just passed every entry rule"))
                    if read:
                        state['feeWasPass'] = bool(read.get('passes'))
                    creator = creator_of.get(w.get('mint'))
                    if rules.get('creatorFlag') and creator and rs.score_creator(creator)['badge'] == 'flagged' and not state.get('flagSent'):
                        fired.append(('creatorFlag', f'{sym} creator is now flagged on FEELESS reputation'))
                        state['flagSent'] = True
                    for kind, text in fired:
                        last = state.get(kind)
                        if last and now - last < cooldown and kind not in ('up', 'down'):
                            continue
                        if kind in ('up', 'down') and last:
                            continue
                        state[kind] = now
                        rs._inbox_alert(entry, kind, text, w)
                        if quiet:
                            continue
                        res = await rs.asyncio.to_thread(rs._send_push, entry['subscription'], f'FEELESS · {sym}', text,
                                                      f"/?coin={w['chainId']}:{w['pairAddress']}", f"{w['pairAddress']}-{kind}")
                        entry.setdefault('sent', []).append({'at': now, 'kind': kind, 'text': text, 'result': res})
                        entry['sent'] = entry['sent'][-50:]
                        if res == 'gone':
                            dead.append(sid)
                            break
            async with rs._push_lock:
                fresh = rs._push_load()
                for sid, entry in d['subs'].items():
                    if sid in fresh['subs'] and sid not in dead:
                        fresh['subs'][sid]['watch'] = entry['watch']
                        fresh['subs'][sid]['sent'] = entry.get('sent', [])
                for sid in dead:
                    fresh['subs'].pop(sid, None)
                rs._push_save(fresh)
        except Exception as exc:
            print('push watcher error', exc)
        await rs.asyncio.sleep(30)

