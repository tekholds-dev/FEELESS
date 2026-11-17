"""🧹 Rug shield, investigations, bot shield, rug radar, inbox, social — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401


def _rs():
    import reputation_service
    return reputation_service


def shield_verdict(intel, blocklist, auth=None, creator_rep=None):
    rs = _rs()
    reasons, danger = list(intel.get('flags') or []), False
    auth = auth or {}
    if auth.get('freezeAuthority'):
        reasons.insert(0, 'Freeze authority is live: the creator can freeze your tokens so you cannot sell.'); danger = True
    if auth.get('mintAuthority'):
        reasons.append('Mint authority is live: the creator can print more supply.')
    creator = intel.get('creator')
    rec = blocklist.get(creator) if creator else None
    if creator and rs._is_blocked(rec) and rec.get('reported'):
        reasons.insert(0, 'Creator wallet was reported for a rug and is on the FEELESS blocklist.'); danger = True
    elif creator and rs._is_blocked(rec):
        # Blocklisted for sniping/bundling OTHER launches, not for rugging: a warning, not a hard stop.
        reasons.insert(0, f"Creator wallet snipes/bundles other launches ({len(rec.get('mints') or {})} on record) — no rug reported on this coin.")
    elif creator_rep and creator_rep.get('level') in ('suspect', 'high') and creator_rep.get('top'):
        # Same verdict and cited evidence as the creator's case file.
        reasons.insert(0, f"Creator case file: {creator_rep['label']} ({creator_rep['score']}/100): {creator_rep['top']['claim']}")
        danger = danger or creator_rep['level'] == 'high'
    if (intel.get('devHoldingPct') or 0) >= 20 or (intel.get('insidersHoldingPct') or 0) >= 25 or intel.get('flaggedFunders'):
        danger = True
    return {'level': 'danger' if danger else 'caution' if reasons else 'ok', 'reasons': reasons[:5],
            'devPct': intel.get('devHoldingPct'), 'insidersPct': intel.get('insidersHoldingPct'), 'top10Pct': intel.get('top10Pct')}


async def _funder_of(wallet):
    """First-transaction funder, memoised (the funding-graph store first, then one RPC trace)."""
    rs = _rs()
    known = rs._funders_load()['offenderFunder'].get(wallet)
    if known:
        return known
    if wallet not in rs._funding_memo:
        rs._funding_memo[wallet] = await rs.resolve_funding_source('solana', wallet)
    return rs._funding_memo[wallet]


async def _mint_authorities(http, mint):
    rs = _rs()
    info = await rs._rpc(http, 'getAccountInfo', [mint, {'encoding': 'jsonParsed'}])
    parsed = ((((info or {}).get('value') or {}).get('data') or {}).get('parsed') or {}) if isinstance(((info or {}).get('value') or {}).get('data'), dict) else {}
    if parsed.get('type') != 'mint':
        return None
    i = parsed.get('info') or {}
    return {'mintAuthority': i.get('mintAuthority'), 'freezeAuthority': i.get('freezeAuthority'), 'decimals': i.get('decimals')}


async def _wallet_case(address):
    rs = _rs()
    a = rs.primary_of(address)
    fund = rs._funders_load()
    squads = fund['funders'].get(a)
    funded_by = await rs._funder_of(a)
    store = rs._load()
    entry = store['creators'].get(rs._creator_key('solana', a))
    creator = rs.score_creator(entry) if entry else None
    linked = []
    fsrc = store['funding'].get(rs._creator_key('solana', a)) or funded_by
    if fsrc:
        for other in store['creators'].values():
            if other['address'] != a and store['funding'].get(rs._creator_key(other['chain'], other['address'])) == fsrc:
                sc = rs.score_creator(other)
                linked.append({'address': other['address'], 'badge': sc.get('badge'), 'ruggedCount': sc.get('ruggedCount')})
    protected = a in rs._protected_wallets()

    async def safe(coro):
        try:
            return await coro
        except Exception:
            return None
    caller, vitals = await rs.asyncio.gather(safe(rs._kol_stats(a, 'solana')), safe(rs.wallet_stats(a)))
    if protected:
        caller = None  # the official wallet moves treasury/launch funds; trader stats would mislead
    ctx = {'blocked': None if protected else rs._block_load()['wallets'].get(a), 'funderOfSquads': squads, 'fundedBy': funded_by,
           'fundedByFlagged': bool(funded_by and rs._is_flagged_funder(fund['funders'].get(funded_by))),
           'creator': creator, 'caller': caller, 'linkedCreators': linked}
    evidence = [] if protected else rs.investigate.wallet_evidence(ctx)
    if not protected:
        sh = await rs._shield_of(a)
        evidence += [{'kind': f"bot-{h['engine']}", 'weight': round(h['score'] / 2), 'claim': f"Bot shield · {h['evidence'][0]['claim']}", 'source': h['evidence'][0]['source']}
                     for h in sh['hits'] if h['score'] >= rs._shield.WATCH]
    prof = rs._profiles_load()['profiles'].get(a) or {}
    return {'kind': 'wallet', 'address': a, 'identity': {'name': prof.get('displayName'), 'handle': prof.get('handle')},
            **rs.investigate.verdict(evidence, protected), 'evidence': evidence,
            'trail': {'fundedBy': funded_by, 'fundedWallets': (squads or {}).get('funded', [])[:20], 'squadLaunches': len((squads or {}).get('mints', {}))},
            'launches': {k: (creator or {}).get(k) for k in ('tokenCount', 'ruggedCount', 'dumpedCount', 'deadCount', 'bigWinners', 'sustainedCount', 'badge')} if creator else None,
            'linked': linked[:12],
            'vitals': {k: (vitals or {}).get(k) for k in ('sol', 'tokensHeld', 'txCount', 'txCountCapped', 'firstSeen')},
            'caller': {k: (caller or {}).get(k) for k in ('tradesSeen', 'tokens', 'closed', 'quickFlipPct', 'dumpPct', 'winPct', 'netUsd', 'medianHoldMin', 'danger')} if caller else None,
            'protected': protected}


async def _coin_case(mint, auth):
    rs = _rs()
    intel = await rs.token_intel('solana', mint)
    holders = [{'owner': r['owner'], 'pct': r.get('pct')} for r in intel.get('topHolders') or [] if r.get('kind') == 'wallet' and r.get('owner')]
    sem = rs.asyncio.Semaphore(6)

    async def trace(w):
        async with sem:
            try:
                return w, await rs._funder_of(w)
            except Exception:
                return w, None
    funder_of = dict(await rs.asyncio.gather(*(trace(h['owner']) for h in holders[:12])))
    cl = rs.investigate.clusters(holders, {w: f for w, f in funder_of.items() if f})
    creator = intel.get('creator')
    blocked = bool(creator and rs._is_blocked(rs._block_load()['wallets'].get(creator)))
    risk = rs.investigate.coin_risk(intel, auth, creator_blocked=blocked, linked_pct=cl['linkedPct'])
    return {'kind': 'coin', 'address': mint, **risk, 'authorities': auth, 'clusters': cl,
            'holders': {k: intel.get(k) for k in ('top10Pct', 'devHoldingPct', 'insidersHoldingPct', 'snipersHoldingPct', 'poolPct')},
            'launch': {'bundled': len(intel.get('bundledWallets') or []), 'snipers': len(intel.get('sniperWallets') or []), 'creator': creator},
            'creatorCase': (await rs._wallet_case(creator)) if creator else None}


def _shield_features(me, ck_all=None, trades_all=None, chat_all=None):
    rs = _rs()
    mine = set(rs.linked_of(me)) | {me}
    trades_all = trades_all if trades_all is not None else rs._json_load(rs.FEELESS_TRADES_PATH, {})
    trades = [{'side': x.get('side'), 'usd': x.get('usd') or x.get('poolUsd') or 0, 'token': x.get('token'), 'ts': x.get('ts')}
              for w, rows in trades_all.items() if w in mine for x in rows or []]
    chat_all = chat_all if chat_all is not None else [m for ms in rs._chat_load()['rooms'].values() for m in ms if isinstance(m, dict) and not m.get('system')]
    chat = [{'ts': rs._ts_num(m.get('ts')), 'text': m.get('text')} for m in chat_all if (m.get('identity') or m.get('address')) in mine]
    qs = rs._qs().all()
    st = qs.get(me) or {}
    ck_all = ck_all if ck_all is not None else {w: v.get('checkinAt') or [] for w, v in qs.items()}
    inv = rs._json_load(rs.REF_PATH, {'by': {}})['by'].get(me, [])
    active = set(trades_all) | {(m.get('identity') or m.get('address')) for m in chat_all}
    fz = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
    own = {fid for fid, f in fz['fuses'].items() if rs.primary_of(f.get('creator') or '') in mine}
    return {'signin_days': st.get('days') or [], 'checkin_at': st.get('checkinAt') or [], 'trades': trades, 'chat': chat,
            'batch_days': rs._shield.batch_days(ck_all, me), 'invitees': [{'active': w in active} for w in inv],
            'own_fuse_buys': sum(1 for b in fz.get('buys') or [] if b['fuse'] in own and b.get('wallet') in mine)}


def _ts_num(v):
    if isinstance(v, (int, float)):
        return float(v)
    try:
        from datetime import datetime as _dt
        return _dt.fromisoformat(str(v).replace('Z', '+00:00')).timestamp()
    except Exception:
        return 0.0


async def _shield_of(address):
    """One wallet's Bot shield verdict (cached 5 min). FEELESS wallets are never flagged; HQ decisions win."""
    rs = _rs()
    a = rs.primary_of(address)
    hit = rs._shield_cache.get(a)
    if hit and rs.time.time() - hit[0] < 300:
        return hit[1]
    try:
        r = rs._shield.scan(rs._shield_features(a), protected=a in rs._protected_wallets(), manual=(rs._json_load(rs.SHIELD_PATH, {}).get('manual') or {}).get(a))
    except Exception:
        r = {'verdict': 'clean', 'score': 0, 'hits': [], 'why': 'scan unavailable'}
    rs._shield_cache[a] = (rs.time.time(), r)
    return r


def _fuse_rep(a):
    """Fuse ties into rep: published Fuses with real outside buyers earn trust; self-dealing costs it."""
    rs = _rs()
    fz = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
    own = {fid for fid, f in fz['fuses'].items() if rs.primary_of(f.get('creator') or '') == a}
    if not own:
        return None
    buys = [b for b in fz.get('buys') or [] if b['fuse'] in own]
    real = len({b['wallet'] for b in buys if not b.get('selfDeal') and not b.get('bot')})
    selfd = sum(1 for b in buys if b.get('selfDeal'))
    pts = min(10, real) - 10 * min(3, selfd)
    return {'label': f'Fuse creator: {real} outside buyer(s)' + (f', {selfd} self-buy(s)' if selfd else ''), 'points': pts} if pts else None


def _shield_scan_all():
    """Every known wallet through every engine, data loaded once (HQ list + hourly alerts)."""
    rs = _rs()
    qs = rs._qs().all()
    trades_all = rs._json_load(rs.FEELESS_TRADES_PATH, {})
    chat_all = [m for ms in rs._chat_load()['rooms'].values() for m in ms if isinstance(m, dict) and not m.get('system')]
    ck_all = {w: v.get('checkinAt') or [] for w, v in qs.items()}
    wallets = set(qs) | set(trades_all) | {m.get('identity') or m.get('address') for m in chat_all} | set(rs._json_load(rs.REF_PATH, {'by': {}})['by'])
    wallets = {w for w in wallets if isinstance(w, str) and rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', w)}
    manual = rs._json_load(rs.SHIELD_PATH, {}).get('manual') or {}
    prot = rs._protected_wallets()
    rows = []
    for w in wallets:
        r = rs._shield.scan(rs._shield_features(w, ck_all, trades_all, chat_all), protected=w in prot, manual=manual.get(w))
        rs._shield_cache[w] = (rs.time.time(), r)
        rows.append({'address': w, **r, 'manual': manual.get(w)})
    return rows


async def _fee_wallet_owner(http, cfg):
    """The wallet that owns the SOL/USDC fee account (read on-chain), used as the self-test's trader."""
    rs = _rs()
    for acct in (cfg.get('feeAccountSol'), cfg.get('feeAccountUsdc')):
        if not acct:
            continue
        try:
            info = await rs._rpc(http, 'getAccountInfo', [acct, {'encoding': 'jsonParsed'}])
            owner = rs._parsed_info((info or {}).get('value')).get('owner')
            if owner:
                return owner
        except Exception:
            continue
    return None


def _quote_fee_bps(q):
    """The fee Jupiter says it will take on this quote: Swap API reports platformFee.feeBps, Ultra reports feeBps."""
    return int((q.get('platformFee') or {}).get('feeBps') or q.get('feeBps') or 0)


def _sess():
    rs = _rs()
    return rs._json_load(rs.SESSIONS_PATH, {'s': {}})


def session_address(token: str):
    rs = _rs()
    if not token:
        return None
    rec = rs._sess()['s'].get(rs.hashlib.sha256(token.encode()).hexdigest())
    if not rec or rs.time.time() > rec['exp']:
        return None
    return rec['address']


def handle_of(address: str) -> str:
    rs = _rs()
    p = rs._profiles_load()['profiles'].get(address) or {}
    return p.get('handle') or address[:6].lower()


def _hygiene_flush():
    rs = _rs()
    hp = rs.DATA_DIR / 'hygiene.json'
    if rs._hygiene_mem['d'] is None or not rs._hygiene_mem['dirty']:
        return
    rs._json_save(hp, rs._hygiene_mem['d'])
    st = hp.stat()
    rs._parse_cache[str(hp)] = ((st.st_mtime_ns, st.st_size), rs._hygiene_mem['d'])   # readers (`_hygiene`) keep reading the copy in memory
    rs._hygiene_mem.update(dirty=False, at=rs.time.time())


def _absorb_intel(mint, out):
    rs = _rs()
    creator = out.get('creator') if isinstance(out.get('creator'), str) else (out.get('creator') or {}).get('address')
    if creator:
        hp = rs.DATA_DIR / 'hygiene.json'
        d = rs._hygiene_mem['d'] if rs._hygiene_mem['d'] is not None and not rs.os.environ.get('PYTEST_CURRENT_TEST') else rs._json_load(hp, {})
        rs._hygiene_mem['d'] = d
        rec = {'snipers': len(out.get('sniperWallets') or []), 'bundled': len(out.get('bundledWallets') or [])}
        la = d.setdefault(creator, {'launches': {}})['launches']
        if la.get(mint) != rec:   # ⚡ a re-scan with the same counts writes nothing (the 6 MB store was re-written + re-parsed per scan)
            la[mint] = rec
            rs._hygiene_mem['dirty'] = True
        if rs._hygiene_mem['dirty'] and (rs.os.environ.get('PYTEST_CURRENT_TEST') or rs.time.time() - rs._hygiene_mem['at'] >= 60):
            rs._hygiene_flush()
    for w in out.get('sniperWallets') or []:
        rs._marked['snipers'].add(w if isinstance(w, str) else (w or {}).get('wallet') or (w or {}).get('owner'))
    for w in out.get('bundledWallets') or []:
        rs._marked['bundlers'].add(w if isinstance(w, str) else (w or {}).get('wallet') or (w or {}).get('owner'))
    rs._marked['mints'].add(mint)


async def _live_stats_compute():
    rs = _rs()
    for mint, (_, out) in list(rs._intel_cache.items()):
        if out:
            rs._absorb_intel(mint, out)
    bl = rs._block_load()['wallets']
    for w, r in bl.items():
        kinds = set(((r or {}).get('mints') or {}).values())
        if kinds & {'sniper', 'snipe'}:
            rs._marked['snipers'].add(w)
        if kinds & {'bundler', 'bundle'}:
            rs._marked['bundlers'].add(w)
    store = rs._load()
    scores = [rs.score_creator(c) for c in store['creators'].values()]
    fd = rs._funders_load()
    return {'snipers': len(rs._marked['snipers'] - {None}), 'bundlers': len(rs._marked['bundlers'] - {None}),
            'blocklisted': sum(1 for r in bl.values() if rs._is_blocked(r)), 'mintsScanned': len(rs._marked['mints'] | set(store['mints'])),
            'creators': len(store['creators']), 'trustedCreators': sum(1 for x in scores if x.get('badge') == 'trusted'),
            'flaggedCreators': sum(1 for x in scores if x.get('badge') == 'flagged'),
            'flaggedFunders': len(fd.get('flagged') or []), 'walletsTraced': len(fd.get('offenderFunder') or {}), 'at': rs.time.time()}


def is_muted(address: str) -> float:
    rs = _rs()
    until = rs._json_load(rs.MUTES_PATH, {}).get(rs.primary_of(address), 0)
    return until if until > rs.time.time() else 0


async def _evm_room(room: str):
    rs = _rs()
    m = rs._re.match(r'^coin-(ethereum|base|bsc|arbitrum|avalanche|polygon|optimism|zksync|zora|cronos|unichain|worldchain)-(0x[0-9a-fA-F]{40})-(bulls|bears|trenches)$', room)
    if not m:
        return None
    chain, pair = m.group(1), m.group(2)
    hit = rs._evm_room_cache.get(pair)
    if hit and rs.time.time() - hit[0] < 300:
        return hit[1]
    info = None
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            p = ((await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{pair}')).json().get('pairs') or [None])[0]
            if p:
                info = (chain, p['baseToken']['address'], p['baseToken']['symbol'], float(p.get('priceUsd') or 0))
    except Exception:
        pass
    rs._evm_room_cache[pair] = (rs.time.time(), info)
    return info


async def _evm_holding_usd(owner: str, chain: str, token: str, price: float):
    rs = _rs()
    call = lambda data: {'jsonrpc': '2.0', 'id': 1, 'method': 'eth_call', 'params': [{'to': token, 'data': data}, 'latest']}
    async with rs.httpx.AsyncClient(timeout=10) as http:
        bal = int((await http.post(rs.EVM_RPC[chain], json=call('0x70a08231' + owner[2:].lower().rjust(64, '0')))).json().get('result') or '0x0', 16)
        dec = int((await http.post(rs.EVM_RPC[chain], json=call('0x313ce567'))).json().get('result') or '0x12', 16)
    return bal / (10 ** dec) * price


def _evm_account_for(address: str):
    rs = _rs()
    if address.startswith('0x'):
        return address
    return next((a for a in rs.linked_of(address) if a.startswith('0x')), None)


async def evm_gate(room: str, address: str):
    rs = _rs()
    info = await rs._evm_room(room)
    if not info:
        return None
    chain, token, symbol, price = info
    acct = rs._evm_account_for(address) if address else None
    if not address:
        return {'gated': True, 'allowed': False, 'symbol': symbol, 'minUsd': rs.MIN_HOLD_USD, 'holdingUsd': None}
    if not acct:
        return {'gated': True, 'allowed': False, 'symbol': symbol, 'minUsd': rs.MIN_HOLD_USD, 'holdingUsd': None, 'needsChain': 'evm'}
    try:
        usd = await rs._evm_holding_usd(acct, chain, token, price)
    except Exception:
        usd = 0.0
    return {'gated': True, 'allowed': usd >= rs.MIN_HOLD_USD, 'symbol': symbol, 'minUsd': rs.MIN_HOLD_USD, 'holdingUsd': round(usd, 4), 'chain': chain}


def _week_start(ts=None):
    rs = _rs()
    t = rs.time.gmtime(ts or rs.time.time())
    return rs.time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, 0)) - t.tm_wday * 86400 - rs.time.timezone


def _radar_pairs():
    rs = _rs()
    pairs = {}
    try:
        for c in sorted(rs._calls_load()['calls'].values(), key=lambda c: -c.get('at', 0))[:200]:
            if rs.time.time() - c.get('at', 0) < 86400 and c.get('chain') == 'solana':
                pairs[c['pairAddress']] = c.get('symbol') or '?'
    except Exception:
        pass
    for e in rs._push_load()['subs'].values():
        for w in e.get('watch', [])[:30]:
            if w.get('chainId') == 'solana':
                pairs[w['pairAddress']] = w.get('symbol') or '?'
    return dict(list(pairs.items())[:90])


async def _radar_loop():
    rs = _rs()
    await rs.asyncio.sleep(30)
    rot = 0
    while True:
        try:
            pairs = rs._radar_pairs()
            rs._radar['pairs'] = pairs
            now = rs.time.time()
            async with rs.httpx.AsyncClient(timeout=12) as http:
                keys = list(pairs)
                for i in range(0, len(keys), 30):
                    r = await http.get(f"https://api.dexscreener.com/latest/dex/pairs/solana/{','.join(keys[i:i + 30])}")
                    try:   # a 429 answers an HTML page — skip this batch (it printed "radar error Expecting value" every minute)
                        rj_ = r.json() if r.status_code == 200 else {}
                    except ValueError:
                        rj_ = {}
                    for p in (rj_ or {}).get('pairs') or []:
                        pa = p['pairAddress']; sym = p['baseToken']['symbol']
                        liq = float((p.get('liquidity') or {}).get('usd') or 0); px = float(p.get('priceUsd') or 0)
                        h = rs._radar['hist'].setdefault(pa, [])
                        h.append((now, liq, px)); h[:] = [x for x in h if now - x[0] < 1800]
                        old = next((x for x in h if now - x[0] <= 900), None)
                        if old and old[1] > 5000 and liq < old[1] * 0.7:
                            rs._radar_event('rug', pa, sym, f'${sym} liquidity pulled {(1 - liq / old[1]) * 100:.0f}% in {int((now - old[0]) / 60)}m (${old[1]/1e3:.1f}K → ${liq/1e3:.1f}K)')
                        if old and old[2] > 0 and px < old[2] * 0.5:
                            rs._radar_event('dump', pa, sym, f'${sym} dumped {(1 - px / old[2]) * 100:.0f}% in {int((now - old[0]) / 60)}m')
                # whale trades: a few pairs per minute from FEELESS's Helius-parsed swap feed
                for pa in keys[rot:rot + 3]:
                    try:
                        r = await http.get(f'http://127.0.0.1:5099/api/candles/trades/solana/{pa}')
                        rows = (r.json() or {}).get('trades') or []
                    except Exception:
                        rows = []
                    for t in rows[:50]:
                        usd = float(t.get('usd') or 0)
                        if usd >= 2500 and not any(w['tx'] == t.get('tx') for w in rs._radar['whales']):
                            rs._radar['whales'].insert(0, {'pair': pa, 'symbol': pairs.get(pa), 'kind': t.get('kind'), 'usd': round(usd), 'wallet': t.get('wallet'), 'tx': t.get('tx'), 'at': t.get('ts')})
                    rs._radar['whales'] = rs._radar['whales'][:120]
                rot = (rot + 3) % max(1, len(keys))
        except Exception as exc:
            print('radar error', exc)
        await rs.asyncio.sleep(60)


def _radar_event(kind, pa, sym, text, cooldown=3600, **extra):
    rs = _rs()
    last = next((e for e in rs._radar['events'] if e['pair'] == pa and e['kind'] == kind), None)
    if last and rs.time.time() - last['at'] < cooldown:
        return False
    rs._radar['events'].insert(0, {'kind': kind, 'pair': pa, 'symbol': sym, 'text': text, 'at': rs.time.time(), **extra})
    rs._radar['events'] = rs._radar['events'][:100]
    return True


async def _push_snipers_out(mint):
    # Phones with push on and this coin on their watchlist hear it first; tapping opens the buy.
    rs = _rs()
    for entry in list(rs._push_load()['subs'].values()):
        w = next((x for x in entry['watch'] if mint in (x.get('mint'), x.get('pairAddress'))), None)
        if w:
            if (entry.get('prefs') or {}).get('address'):
                rs.notify(entry['prefs']['address'], 'snipers', f"Every flagged sniper/bundler on {w.get('symbol') or mint[:4]} has sold out",
                       f"/terminal/chat?chain=solana&pair={w['pairAddress']}&room=bulls", once=f'snipers-{mint}', push=False,
                       meta={'symbol': w.get('symbol'), 'claim': 'All flagged sniper/bundler wallets sold', 'source': 'Launch forensics (holder scan)'})
            await rs.asyncio.to_thread(rs._send_push, entry['subscription'], f"🎯 {w.get('symbol') or mint[:4]}: snipers are out",
                                    'Every flagged sniper/bundler has sold. Tap to buy.', f"/terminal/chat?chain=solana&pair={w['pairAddress']}&room=bulls&buy=1", f'snipers-{mint}')


def _feecat_pins(positions, top, now=None):
    """🤖🔁 HQ's Fee desk: for each coin she holds or would take next — the agents' current verdict (kernel status + why, at the coin's live cap)
    and OSSY / G4 / Reaper lines on it (the duo log, same rows the Agents chart pins). {mint: {agents: {...} | None, duo: [rows]}}. HQ only: users
    see Fee's own calls, never these."""
    rs = _rs()
    now = rs.time.time() if now is None else now
    mints = [m for m in dict.fromkeys([p.get('mint') for p in positions or []] + [t.get('mint') for t in top or []]) if m][:10]
    if not mints:
        return {}
    try:
        rows = rs._duo_chart_rows(rs._g4_state()['log'], card=mints)
    except Exception:
        rows = []
    out = {}
    for m in mints:
        try:
            x = rs._tk.KERNEL.candidate(m)
        except Exception:
            x = None
        cap = rs._duo_cap(m)
        ag = {'status': x.get('status'), 'why': str(x.get('kwhy') or '')[:200], 'rank': round(rs._fuse._f(x.get('rank')), 1), 'cap': cap, 'at': now} if x else None
        out[m] = {'agents': ag, 'duo': [{**r, 'cap': r.get('cap') or cap} for r in rows if r.get('mint') == m][-20:]}
    return out


def _feecat_fast_trench():
    """⚡ FeeCat's ONE dial (owner, 2026-10-16: "one dial only and that's FAST trench, same configs as the agents tab to start"): her rules seeded
    from the agents' live realCfg (MC floor, youngest age, pool floor, 1h volume, take / stop, seats). The page clamps each to her own bounds."""
    rs = _rs()
    c_ = rs._prime_real_cfg() or {}
    f_ = lambda k_, d_: rs._fuse._f(c_.get(k_)) or d_
    vol_ = f_('agentMinVol1h', 5000)
    return {'minMarketCap': f_('agentMcMin', 12000), 'minAgeHours': max(0.05, f_('agentMinAgeH', 0.25)), 'minLiquidity': f_('agentPoolMin', 8000),
            'minVolume24h': vol_ * 24, 'takeProfit1': f_('agentTp', 30), 'takeProfit2': f_('agentTp', 30) * 2.5, 'hardStop': -f_('agentSl', 25),
            'runnerTrail': 20, 'maxHoldHours': 2, 'maxM5Chase': 4, 'maxPositions': 4, 'add1At': -15, 'add2At': -25, 'maxExposure': 0.4,
            'from': {k_: c_.get(k_) for k_ in ('agentMcMin', 'agentMcMax', 'agentMinAgeH', 'agentPoolMin', 'agentMinVol1h', 'agentTp', 'agentSl')}}


def _notif():
    """🗄 SITE-8: the inbox, one row per wallet in SQLite (notifications.db). A new alert changes ONE wallet's row in one transaction, so
    any number of workers can notify at once and none wipes another's (the old whole-file write rewrote 4 MB per alert and lost races).
    notifications.json moved in once and is kept read-only."""
    rs = _rs()
    import sql_store as _sqls
    k_ = str(rs.NOTIF_PATH)
    if k_ not in rs._notif_docs:
        rs._notif_docs[k_] = _sqls.Docs(rs.NOTIF_PATH)
    return rs._notif_docs[k_]


def _notif_box(wallet):
    """One wallet's inbox, newest first ([] when none or the store is unreadable)."""
    rs = _rs()
    try:
        return rs._notif().get(wallet) or []
    except Exception:
        return []


def notify(address: str, kind: str, text: str, url: str = '', actor: str = '', once: str = '', meta: Optional[dict] = None, push: bool = True):
    """once: a dedupe key — a notification with the same key is never sent to this wallet twice.
    push=False: inbox only (the caller already pushed to the phone)."""
    rs = _rs()
    to = rs.primary_of(address)
    if not to or to in ('FEE-LEADER-CAT', 'FEELESS-HQ') or rs.primary_of(actor or '') == to:
        return
    import sql_store as _sqls
    row = {'id': rs.uuid.uuid4().hex[:10], 'kind': kind, 'text': text[:200], 'url': url, 'actor': actor, 'at': rs.time.time(), 'read': False,
           **({'once': once} if once else {}), **({'meta': meta} if meta else {})}

    def add(box):
        box = box or []
        if once and any(n.get('once') == once for n in box):
            return _sqls.Result(box or None, False)
        return _sqls.Result([row, *box][:200], True)
    if not rs._notif().update(to, add):
        return
    if not push:
        return
    try:
        for e in rs._push_load()['subs'].values():
            if rs.primary_of((e.get('prefs') or {}).get('address') or '') == to:
                rs.asyncio.get_running_loop().run_in_executor(None, rs._send_push, e['subscription'], {'dm': '💬 New message', 'follow': '➕ New follower', 'wall': '🧱 New wall post', 'mention': '📣 You were mentioned', 'reward': '🎁 Reward ready', 'invite': '🎉 Invite joined', 'snipers': '🎯 Snipers are out', 'watch': '👁 Watched wallet moved', 'autorange': '🤖 AutoRange'}.get(kind, 'FEELESS'), text[:120], url or '/terminal', f'n-{kind}')
    except Exception:
        pass


def _session_or_401(address, session):
    rs = _rs()
    owner = rs.session_address(session)
    if not owner or rs.primary_of(owner) != rs.primary_of(address):
        raise rs.HTTPException(401, 'Sign in to chat first (one signature, 7 days).')
    return rs.primary_of(address)


def _legacy_sniper_dedupe(box):
    """Older builds repeated the snipers-out alert on every intel refresh: keep only the newest per coin."""
    seen, out = set(), []
    for n in box:
        legacy = n.get('kind') == 'reward' and 'sniper on your coin' in n.get('text', '')
        key = n.get('text') if legacy else None
        if key and key in seen:
            continue
        if key:
            seen.add(key)
            n = {**n, 'kind': 'snipers'}
        out.append(n)
    return out


def _dm_key(a, b):
    rs = _rs()
    return '|'.join(sorted([rs.primary_of(a), rs.primary_of(b)]))


def _dm_pref(addr):
    rs = _rs()
    p = rs._json_load(rs.DM_PREFS_PATH, {}).get(addr) or {}
    return {'policy': p.get('policy', 'everyone'), 'accepted': p.get('accepted', [])}


def _pts():
    rs = _rs()
    return rs._json_load(rs.POINTS_PATH, {})


async def _reward_state(me: str):
    rs = _rs()
    rec = rs._pts().get(me) or {'total': 0, 'claims': {}, 'streak': 0, 'log': []}
    day = rs.time.strftime('%Y-%m-%d', rs.time.gmtime())
    claims = rec['claims']
    prof = rs._profiles_load()['profiles'].get(me) or {}
    msgs_today = any(m for ms in rs._chat_load()['rooms'].values() for m in ms if isinstance(m, dict) and (m.get('identity') or m.get('address')) == me and rs.time.strftime('%Y-%m-%d', rs.time.gmtime(m.get('ts', 0) / 1000)) == day)
    board = await rs.caller_board(days=90)
    hits = next((r['hits'] for r in board['rows'] if r.get('callerAddress') == me), 0)
    invited = len(rs._json_load(rs.REF_PATH, {'by': {}})['by'].get(me, []))
    fee_ok = (await rs._perk_tier(me))[1] >= 1
    linked = len(rs.linked_of(me)) > 1
    out = []
    for r in rs.REWARDS:
        c = claims.get(r['id'])
        if r['id'] == 'daily':
            ok, amount = c != day, 10 + min(50, 5 * rec.get('streak', 0))
        elif r['id'] == 'profile':
            ok, amount = not c and all(prof.get(k) for k in ('displayName', 'handle', 'avatarUrl', 'bio')), r['points']
        elif r['id'] == 'post':
            ok, amount = msgs_today and c != day, r['points']
        elif r['id'] == 'call-hit':
            n = hits - int(c or 0); ok, amount = n > 0, n * r['points']
        elif r['id'] == 'invite':
            n = invited - int(c or 0); ok, amount = n > 0, n * r['points']
        elif r['id'] == 'fee-holder':
            ok, amount = fee_ok and c != day, r['points']
        else:
            ok, amount = linked and not c, r['points']
        out.append({**r, 'claimable': bool(ok), 'amount': amount, 'claimed': c})
    return rec, out, {'hits': hits, 'invited': invited, 'day': day}


def is_verified(address: str) -> bool:
    rs = _rs()
    a = rs.primary_of(address or '')
    return bool(a) and (rs._is_staff(a) or a == rs.FEE_RESERVE_WALLET or a in (rs._admin_load().get('verified') or []))


def invite_code(address: str) -> str:
    rs = _rs()
    a = rs.primary_of(address)
    h = rs.hashlib.sha256(f'feeless-invite:{a}'.encode()).digest()
    alphabet = '23456789abcdefghjkmnpqrstuvwxyz'
    n = int.from_bytes(h[:8], 'big')
    return ''.join(alphabet[(n >> (5 * i)) % len(alphabet)] for i in range(8))


def _code_owner(code: str):
    rs = _rs()
    code = (code or '').lower()
    cands = set(rs._profiles_load()['profiles']) | set(rs._json_load(rs.REF_PATH, {'by': {}})['by']) | set(rs._pts()) | set(rs._admin_wallets())
    return next((a for a in cands if rs.invite_code(a) == code), None)


def _unlocks(address: str):
    rs = _rs()
    rec = rs._pts().get(rs.primary_of(address)) or {}
    now = rs.time.time()
    return {k: v for k, v in (rec.get('unlocks') or {}).items() if v == 'forever' or float(v) > now}, rec


def _war_week():
    rs = _rs()
    return rs.time.strftime('%G-W%V', rs.time.gmtime())


def _webhook_secret():
    rs = _rs()
    sec = rs.os.environ.get('HELIUS_WEBHOOK_SECRET') or (rs._admin_load().get('helius') or {}).get('secret')
    if not sec:
        import secrets as _s
        sec = _s.token_urlsafe(32)
        d = rs._admin_load(); d.setdefault('helius', {})['secret'] = sec; rs._admin_save(d)
    return sec


async def sync_helius_webhook(public_url: str):
    """Create or update FEELESS's Helius webhook to point at the current public domain."""
    rs = _rs()
    key = rs._helius_key()
    if not key or not public_url:
        return {'ok': False, 'reason': 'Needs a public domain and a Helius key in SOLANA_RPC_URL.'}
    mints = list((await rs._ecosystem_mints()).values())
    body = {'webhookURL': f'{public_url.rstrip("/")}/api/reputation/webhooks/helius', 'transactionTypes': ['SWAP', 'TRANSFER'],
            'accountAddresses': sorted(set(mints + rs._admin_wallets()))[:100], 'webhookType': 'enhanced', 'authHeader': rs._webhook_secret()}
    d = rs._admin_load(); hid = (d.get('helius') or {}).get('webhookId')
    async with rs.httpx.AsyncClient(timeout=20) as http:
        if hid:
            r = await http.put(f'https://api.helius.xyz/v0/webhooks/{hid}?api-key={key}', json=body)
            if r.status_code == 404:
                hid = None
        if not hid:
            r = await http.post(f'https://api.helius.xyz/v0/webhooks?api-key={key}', json=body)
    if r.status_code >= 300:
        return {'ok': False, 'reason': f'Helius said {r.status_code}: {r.text[:120]}'}
    d = rs._admin_load(); d.setdefault('helius', {}).update({'webhookId': r.json().get('webhookID') or hid, 'url': body['webhookURL'], 'at': rs.time.time()}); rs._admin_save(d)
    return {'ok': True, 'url': body['webhookURL'], 'watching': len(body['accountAddresses'])}


async def _portfolio_build(a):
    rs = _rs()
    held = {}
    sol = 0.0
    async with rs.httpx.AsyncClient(timeout=25) as http:
        try:
            sol = ((await rs._rpc(http, 'getBalance', [a])) or {}).get('value', 0) / 1e9
        except Exception:
            pass
        for prog in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
            try:
                r = await rs._rpc(http, 'getTokenAccountsByOwner', [a, {'programId': prog}, {'encoding': 'jsonParsed'}])
            except Exception:
                r = None
            for acc in (r or {}).get('value', []):
                info = acc['account']['data']['parsed']['info']
                amt = float((info.get('tokenAmount') or {}).get('uiAmount') or 0)
                if amt > 0:
                    held[info['mint']] = held.get(info['mint'], 0) + amt
        mints = list(held)[:60]
        market = {}
        async def ds_batch(chunk):   # ⚡ ONE DexScreener call per 30 coins (it was 2 calls per coin, paced: a 60-coin wallet waited > 1 min)
            try:
                rows_ = (await http.get(f"https://api.dexscreener.com/tokens/v1/solana/{','.join(chunk)}", timeout=8)).json() or []
            except Exception:
                rows_ = []
            for x in rows_ if isinstance(rows_, list) else []:
                m = (x.get('baseToken') or {}).get('address')
                if m in held and (m not in market or float((x.get('liquidity') or {}).get('usd') or 0) > float((market[m].get('liquidity') or {}).get('usd') or 0)):
                    market[m] = x
        await rs.asyncio.gather(*(ds_batch(mints[i:i + 30]) for i in range(0, len(mints), 30)))
        miss = [m for m in mints if m not in market]
        if miss:   # Jupiter covers pump.fun curve tokens DexScreener hasn't indexed — batched, cached
            try:
                jt = await rs._jup_tokens(miss)
            except Exception:
                jt = {}
            for m in miss:
                j = (jt or {}).get(m)
                if j and j.get('usdPrice'):
                    market[m] = {'baseToken': {'address': m, 'symbol': j.get('symbol'), 'name': j.get('name')}, 'priceUsd': j.get('usdPrice'),
                                 'info': {'imageUrl': j.get('icon')}, 'priceChange': {'h24': (j.get('stats24h') or {}).get('priceChange')}, 'chainId': 'solana'}
        sol_px = 0.0
        try:
            sol_px = float(((await http.get('https://lite-api.jup.ag/price/v3?ids=So11111111111111111111111111111111111111112')).json().get('So11111111111111111111111111111111111111112') or {}).get('usdPrice') or 0)
        except Exception:
            pass
    rows = []
    for m, amt in held.items():
        p = market.get(m)
        px = float(p.get('priceUsd') or 0) if p else 0
        rows.append({'mint': m, 'amount': amt, 'symbol': (p or {}).get('baseToken', {}).get('symbol'), 'name': (p or {}).get('baseToken', {}).get('name'),
                     'logo': ((p or {}).get('info') or {}).get('imageUrl'), 'priceUsd': px or None, 'usd': round(amt * px, 2) if px else None,
                     'change24h': ((p or {}).get('priceChange') or {}).get('h24'), 'chain': (p or {}).get('chainId'), 'pairAddress': (p or {}).get('pairAddress')})
    rows.sort(key=lambda r: -(r['usd'] or 0))
    priced = [r for r in rows if r['usd']]
    out = {'address': a, 'supported': True, 'sol': round(sol, 6), 'solUsd': round(sol * sol_px, 2), 'tokens': rows[:60],
           'unpriced': len(rows) - len(priced), 'totalUsd': round(sol * sol_px + sum(r['usd'] for r in priced), 2)}
    rs._pf_cache[a] = (rs.time.time(), out)
    return out


def _fol():
    rs = _rs()
    return rs._json_load(rs.FOLLOW_PATH, {'following': {}})


async def _trust_fill(a):
    rs = _rs()
    try:
        rs._trust_cache[a] = (rs.time.time(), await rs.trust_score(a))
    except Exception:
        pass
    finally:
        rs._trust_pending.discard(a)


def _edge_grade(score):
    return 'A' if score >= 80 else 'B' if score >= 65 else 'C' if score >= 50 else 'D' if score >= 35 else 'F'


def _edge_price_ok(sent, live):
    """🔒 The browser's price is only believed near the server's own: a forged observation can't plant fake grades. With no live read, it is not filed."""
    return bool(live) and live / 3 <= sent <= live * 3


async def _refresh_edge_memory():
    rs = _rs()
    while True:
        try:
            d = rs._json_load(rs.EDGE_MEM_PATH, {'open': {}, 'done': []})
            by_chain = {}
            for o in d['open'].values():
                by_chain.setdefault(o['chain'], []).append(o['pair'])
            live = {}
            async with rs.httpx.AsyncClient(timeout=10) as http:
                for chain, pairs in by_chain.items():
                    for i in range(0, len(pairs), 30):
                        try:
                            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{",".join(pairs[i:i + 30])}')
                            for p in (r.json() or {}).get('pairs') or []:
                                live[f"{chain}:{p.get('pairAddress')}"] = float(p.get('priceUsd') or 0)
                        except Exception:
                            pass
                        await rs.asyncio.sleep(0.3)
            async with rs._edge_lock:
                d = rs._json_load(rs.EDGE_MEM_PATH, {'open': {}, 'done': []})
                now = rs.time.time()
                for key, o in list(d['open'].items()):
                    px = live.get(key)
                    if px:
                        o['last'] = px; o['peak'] = max(o['peak'], px); o['low'] = min(o['low'], px); o['seen'] = now
                    if now - o['at'] >= rs.EDGE_HORIZON:
                        # Pool gone from DexScreener for the whole window's end = liquidity pulled.
                        vanished = not px and now - o.get('seen', o['at']) > 6 * 3600
                        end = px or o.get('last') or o['price']
                        d['done'].append({'chain': o['chain'], 'grade': o['grade'], 'ret': -100.0 if vanished else round((end / o['price'] - 1) * 100, 2),
                                          'peak': round((o['peak'] / o['price'] - 1) * 100, 2), 'rug': vanished or end / o['price'] <= 0.3, 'at': now})
                        d['open'].pop(key)
                d['done'] = d['done'][-20000:]
                rs._json_save(rs.EDGE_MEM_PATH, d)
        except Exception as exc:
            print('edge memory refresh error', exc)
        await rs.asyncio.sleep(1200)


async def _darkside_compute(limit):
    rs = _rs()
    bl = rs._block_load()['wallets']
    offenders = sorted(({'wallet': w, 'strikes': len(r.get('mints') or {}), 'roles': sorted(set((r.get('mints') or {}).values())),
                         'blocked': rs._is_blocked(r), 'lastSeen': r.get('lastSeen')} for w, r in bl.items() if r.get('mints')),
                       key=lambda x: (-x['strikes'], -(x['lastSeen'] or 0)))[:limit]
    fd = rs._funders_load()
    funders = sorted(({'wallet': w, 'walletsFunded': len(r.get('funded') or []), 'launches': len(r.get('mints') or {}),
                       'flagged': rs._is_flagged_funder(r), 'lastSeen': r.get('lastSeen')} for w, r in fd['funders'].items()),
                     key=lambda x: (-x['walletsFunded'], -x['launches']))[:limit]
    return {'offenders': offenders, 'funders': funders, 'whales': rs._radar['whales'][:limit],
            'rugs': [e for e in rs._radar['events'] if e['kind'] in ('rug', 'dump')][:limit], 'at': rs.time.time()}


async def _native_prices(http):
    rs = _rs()
    if rs.time.time() - rs._native_px['at'] < 300 and rs._native_px['px']:
        return rs._native_px['px']
    px = {}
    for sym, q in (('ETH', 'WETH'), ('BNB', 'WBNB'), ('AVAX', 'WAVAX'), ('POL', 'WPOL'), ('CRO', 'WCRO')):
        try:
            pairs = (await http.get('https://api.dexscreener.com/latest/dex/search', params={'q': f'{q} USDC'})).json().get('pairs') or []
            best = max((p for p in pairs if (p.get('baseToken') or {}).get('symbol') == q), key=lambda p: (p.get('liquidity') or {}).get('usd') or 0, default=None)
            if best:
                px[sym] = float(best.get('priceUsd') or 0)
        except Exception:
            pass
    rs._native_px.update(at=rs.time.time(), px=px)
    return px


def _themes():
    """🗄 SITE-8: saved looks / colours, one row per wallet in SQLite (themes.db); themes.json moved in once and is kept read-only."""
    rs = _rs()
    import sql_store as _sqls
    k_ = str(rs.THEMES_PATH)
    if k_ not in rs._theme_docs:
        rs._theme_docs[k_] = _sqls.Docs(rs.THEMES_PATH)
    return rs._theme_docs[k_]


async def _eco_holding_usd(address: str) -> float:
    rs = _rs()
    if address.startswith('0x'):
        return 0.0
    hit = rs._eco_hold_cache.get(address)
    if hit and rs.time.time() - hit[1] < 60:   # ⚡ the theme route waited ~10s p95 on one lookup per coin, one after another
        return hit[0]

    async def one(mint):
        try:
            return await rs._holding_usd(address, mint) or 0
        except Exception:
            return 0
    vals = await rs.asyncio.gather(*(one(m) for m in (await rs._ecosystem_mints()).values()))
    total = round(sum(vals), 2)
    if len(rs._eco_hold_cache) > 5000:
        rs._eco_hold_cache.clear()
    rs._eco_hold_cache[address] = (total, rs.time.time())
    return total


def _meta_words(p):
    rs = _rs()
    bt = p.get('baseToken') or {}
    raw = f"{bt.get('name') or ''} {bt.get('symbol') or ''}".lower()
    words = set(rs._re.findall(r'[a-z]{2,}', raw)) - rs._META_STOP
    fams = {f for f, vocab in rs.META_FAMILIES.items() if words & vocab or any(v in raw.replace(' ', '') for v in vocab if len(v) >= 4)}
    return words, fams


async def metas(refresh: bool = False):
    # Users always get the background-computed snapshot instantly; only the loop recomputes.
    rs = _rs()
    if not refresh and rs._meta_cache['data']:
        return rs._meta_cache['data']
    if not refresh and not rs._meta_cache['data']:
        return {'metas': [], 'coinsScanned': 0, 'chains': len(rs.META_CHAINS), 'warming': True, 'at': rs.time.time()}
    pairs = []
    async with rs.httpx.AsyncClient(timeout=20) as http:
        async def pull(chain, kind):
            try:
                r = await http.get('http://127.0.0.1:5001/api/market/feed', params={'chain': chain, 'kind': kind})
                return r.json().get('pairs') or [] if r.status_code == 200 else []
            except Exception:
                return []
        for batch in await rs.asyncio.gather(*(pull(c, k) for c in rs.META_CHAINS for k in ('trending', 'new'))):
            pairs += batch
    uniq = {}
    for p in pairs:
        k = (p.get('chainId'), (p.get('baseToken') or {}).get('address'))
        if k[1] and k not in uniq:
            uniq[k] = p
    pairs = [p for p in uniq.values() if ((p.get('baseToken') or {}).get('symbol') or '').upper().strip() not in rs._MAJOR_SYMBOLS
             and not rs._re.search(r'usd|tether|bitcoin|wrapped|staked|bridged', ((p.get('baseToken') or {}).get('name') or '').lower())]
    groups, word_count = {}, {}
    for p in pairs:
        words, fams = rs._meta_words(p)
        for f in fams:
            groups.setdefault(f, []).append(p)
        for w in words:
            word_count.setdefault(w, []).append(p)
    # Emergent metas: a fresh word 3+ unrelated coins share that isn't already a family.
    for w, members in word_count.items():
        if len(members) >= 3 and len(w) >= 3 and not any(w in v for v in rs.META_FAMILIES.values()):
            if len({(m.get('baseToken') or {}).get('symbol', '').upper() for m in members}) >= 3:
                groups.setdefault(w, members)
    total_vol = sum(float((p.get('volume') or {}).get('h24') or 0) for p in pairs) or 1
    now_ms = rs.time.time() * 1000
    prev = next((h for t, h in reversed(rs._meta_hist) if rs.time.time() - t >= 3000), None)
    out = []
    for name, members in groups.items():
        vol = sum(float((m.get('volume') or {}).get('h24') or 0) for m in members)
        ch = sorted(c for c in (float((m.get('priceChange') or {}).get('h24')) for m in members if (m.get('priceChange') or {}).get('h24') is not None) if abs(c) < 2000)
        fresh = sum(1 for m in members if m.get('pairCreatedAt') and now_ms - m['pairCreatedAt'] < 86400000)
        flagged = 0
        for m in members:
            hit = rs._intel_cache.get((m.get('baseToken') or {}).get('address'))
            if hit and hit[1] and (len(hit[1].get('sniperWallets') or []) >= 5 or len(hit[1].get('bundledWallets') or []) >= 3 or hit[1].get('flaggedFunders')):
                flagged += 1
        share = vol / total_vol
        trend = None if not prev or name not in prev else round((share - prev[name]) / max(prev[name], 1e-6) * 100, 1)
        top = sorted(members, key=lambda m: -float((m.get('volume') or {}).get('h24') or 0))[:8]
        out.append({'meta': name, 'family': name in rs.META_FAMILIES, 'coins': len(members), 'volume24h': round(vol), 'volumeShare': round(share * 100, 2),
                    'avgChange24h': round(ch[len(ch) // 2], 1) if ch else None, 'freshLaunches24h': fresh,
                    'chains': sorted({m.get('chainId') for m in members}), 'riskShare': round(flagged / len(members) * 100) if members else 0,
                    'trend1h': trend, 'status': 'forming' if fresh >= max(2, len(members) * 0.5) else ('rising' if (trend or 0) > 10 else 'fading' if (trend or 0) < -10 else 'steady'),
                    'top': [{'symbol': (m.get('baseToken') or {}).get('symbol'), 'chain': m.get('chainId'), 'pairAddress': m.get('pairAddress'),
                             'change24h': (m.get('priceChange') or {}).get('h24'), 'volume24h': (m.get('volume') or {}).get('h24'),
                             'imageUrl': (m.get('info') or {}).get('imageUrl')} for m in top]})
    out.sort(key=lambda x: (-x['volume24h']))
    seen, deduped = set(), []
    for m in out:  # the same coins under two words = one meta (keep the family / longer name)
        sig = tuple(sorted(t['pairAddress'] or '' for t in m['top']))
        if sig in seen:
            continue
        seen.add(sig); deduped.append(m)
    out = deduped
    rs._meta_hist.append((rs.time.time(), {m['meta']: m['volumeShare'] / 100 for m in out}))
    del rs._meta_hist[:-40]
    data = {'metas': out[:24], 'coinsScanned': len(pairs), 'chains': len(rs.META_CHAINS), 'at': rs.time.time()}
    rs._meta_cache.update(at=rs.time.time(), data=data)
    return data


async def _maker_swaps(http, address):
    """[{ts, side, usd, price, token, tx}] for the wallet's recent swaps. SOL legs are priced at the
    live SOL rate; stablecoin legs count 1:1. [] when Helius is not configured."""
    rs = _rs()
    key_ = rs._helius_key()
    sol_usd = await rs._sol_usd_live()   # Jupiter → DexScreener SOL/USDC → the last good price (a 0 here dropped every SOL-priced swap)
    txs = None
    if key_:
        try:
            r_ = await http.get(f'https://api.helius.xyz/v0/addresses/{address}/transactions', params={'api-key': key_, 'type': 'SWAP', 'limit': 100})
            txs = r_.json() if r_.status_code == 200 else None
        except Exception:
            txs = None
    if not isinstance(txs, list):   # 🔁 N07: Helius out of quota / down / not set → the wallet's own Solana RPC history (wallet_swaps.py), never an empty page
        return await rs._rpc_wallet_swaps(http, address, sol_usd)
    out = []
    for tx in txs if isinstance(txs, list) else []:
        delta, quote_usd = {}, 0.0
        for t in tx.get('tokenTransfers') or []:
            amt = float(t.get('tokenAmount') or 0) * (1 if t.get('toUserAccount') == address else -1 if t.get('fromUserAccount') == address else 0)
            if not amt:
                continue
            if t.get('mint') == rs.WSOL:
                quote_usd += amt * sol_usd
            elif t.get('mint') in rs._STABLES:
                quote_usd += amt
            else:
                delta[t['mint']] = delta.get(t['mint'], 0) + amt
        if not quote_usd:  # native SOL leg only when there was no wrapped-SOL/stable leg (else it's the same SOL twice)
            for n in tx.get('nativeTransfers') or []:
                lam = float(n.get('amount') or 0) / 1e9
                quote_usd += lam * sol_usd * (1 if n.get('toUserAccount') == address else -1 if n.get('fromUserAccount') == address else 0)
        moved = [(m, a) for m, a in delta.items() if a]
        if len(moved) != 1 or not quote_usd:
            continue  # token-for-token routes or transfers without a priced leg
        mint, amt = moved[0]
        usd = abs(quote_usd)
        out.append({'ts': tx.get('timestamp') or 0, 'side': 'buy' if amt > 0 else 'sell', 'usd': round(usd, 2),
                    'price': usd / abs(amt), 'token': mint, 'tx': tx.get('signature')})
    return out


async def _rpc_wallet_swaps(http, address, sol_usd):
    """The wallet's last RPC_SWAP_SIGS transactions from Solana RPC (the pooled lanes: Alchemy / Helius RPC / public) → its swaps, read from
    its own balance changes (wallet_swaps.parse). RPC_SWAP_PAR reads at a time; a read that fails is skipped, never guessed."""
    rs = _rs()
    try:
        sigs = await rs._rpc(http, 'getSignaturesForAddress', [address, {'limit': rs.RPC_SWAP_SIGS, 'commitment': 'confirmed'}]) or []
    except Exception:
        return []
    sem = rs.asyncio.Semaphore(rs.RPC_SWAP_PAR)

    async def one(sig):
        async with sem:
            try:
                return await rs._rpc(http, 'getTransaction', [sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
            except Exception:
                return None
    txs = await rs.asyncio.gather(*(one(x_['signature']) for x_ in sigs if x_.get('signature') and x_.get('err') is None))
    return [r_ for r_ in (rs._wswaps.parse(t_, address, sol_usd) for t_ in txs if t_) if r_]


async def _kol_stats(address, chain):
    rs = _rs()
    hit = rs._kol_cache.get(address)
    if hit and rs.time.time() - hit[0] < 300:
        return hit[1]
    if chain != 'solana' or not rs._helius_key():
        return None
    async with rs.httpx.AsyncClient(timeout=15) as http:
        items = await rs._maker_swaps(http, address)
    by = {}
    for e in items:
        t = by.setdefault(e['token'], {'buys': [], 'sells': []})
        t['buys' if e['side'] == 'buy' else 'sells'].append((e['ts'], e['usd']))
    tokens, holds, flips, dumps, wins, closed = [], [], 0, 0, 0, 0
    for tok, t in by.items():
        bought = sum(u for _, u in t['buys']); sold = sum(u for _, u in t['sells'])
        # A position only counts as closed once a real part of it (20%+) was sold: dust/fee sells are not exits.
        if t['buys'] and t['sells'] and bought and sold >= bought * 0.2:
            first_buy = min(ts for ts, _ in t['buys']); first_sell = min((ts for ts, _ in t['sells'] if ts >= first_buy), default=None)
            if first_sell:
                closed += 1
                hold = (first_sell - first_buy) / 60; holds.append(hold)
                flips += hold <= 60
                dumps += (sold >= bought * 0.8 and hold <= 120)
                wins += sold > bought
        tokens.append({'token': tok, 'boughtUsd': round(bought), 'soldUsd': round(sold), 'pnlUsd': round(sold - bought) if t['sells'] else None, 'trades': len(t['buys']) + len(t['sells'])})
    tokens.sort(key=lambda x: -(x['boughtUsd'] + x['soldUsd']))
    avg_hold = sorted(holds)[len(holds) // 2] if holds else None
    flags = []
    if closed >= 3 and flips / closed >= 0.5:
        flags.append(f"Flips {round(flips / closed * 100)}% of positions within an hour — anyone buying after their call is likely their exit liquidity.")
    if closed >= 3 and dumps / closed >= 0.4:
        flags.append(f"Dumped most of the bag within 2h on {round(dumps / closed * 100)}% of coins — the classic call-and-dump pattern.")
    if closed >= 3 and wins / closed >= 0.7 and avg_hold is not None and avg_hold < 90:
        flags.append("Wins mostly by selling fast into buying pressure — their profit is often their followers' loss.")
    if not flags and closed >= 3:
        flags.append('No call-and-dump pattern in their recent trades.')
    stats = {'tradesSeen': len(items), 'tokens': len(by), 'closed': closed, 'medianHoldMin': round(avg_hold) if avg_hold is not None else None,
             # Percentages need a sample: one or two closed positions say nothing about a trader.
             'quickFlipPct': round(flips / closed * 100) if closed >= 3 else None, 'dumpPct': round(dumps / closed * 100) if closed >= 3 else None,
             'winPct': round(wins / closed * 100) if closed >= 3 else None, 'netUsd': round(sum((x['pnlUsd'] or 0) for x in tokens)),
             'flags': flags, 'topTokens': tokens[:8], 'danger': bool(closed >= 3 and (flips / closed >= 0.5 or dumps / closed >= 0.4))}
    rs._kol_cache[address] = (rs.time.time(), stats)
    return stats

