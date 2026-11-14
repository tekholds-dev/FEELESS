"""🧩 SITE-5 slice 10 (2026-11-13): plain WRITE routes (POST/PUT/DELETE; no admin, money or staff words), moved out of reputation_service by
scripts/move-routes.py --writes. Helpers stay there and are looked up on reputation_service when a route runs; body models are read
off the loaded service (this module is imported at the END of reputation_service, after every model is defined)."""
import reputation_service as _RSM  # noqa: E402
from fastapi import APIRouter, Query, Request  # noqa: F401

router = APIRouter()


def _rs():
    import reputation_service
    return reputation_service


@router.post('/api/reputation/observe')
async def observe(payload: _RSM.ObservePayload):
    rs = _rs()
    mint_key = f'{payload.chain}:{payload.baseTokenAddress}'
    pre_ = None
    if 'creator' not in rs._load()['mints'].get(mint_key, {}):   # ⚡ the network lookup runs OUTSIDE the lock (every observe queued behind it: p95 38s)
        pre_ = await rs.resolve_creator(payload.chain, payload.baseTokenAddress)
    async with rs._lock:
        store = rs._load()
        now = rs.time.time()
        mint_state = store['mints'].get(mint_key, {})
        if 'creator' not in mint_state:
            resolved = pre_ or await rs.resolve_creator(payload.chain, payload.baseTokenAddress)
            mint_state['creator'] = resolved['identity']
            mint_state['renounced'] = resolved['renounced']
            store['mints'][mint_key] = mint_state
        creator_address = mint_state.get('creator')
        authority_renounced = bool(mint_state.get('renounced'))

        if not creator_address:
            rs._save(store)
            return {'creator': None, 'reason': 'Creator identity unavailable for this chain or mint.', 'score': None}

        ckey = rs._creator_key(payload.chain, creator_address)
        creator_entry = store['creators'].setdefault(ckey, {
            'chain': payload.chain, 'address': creator_address,
            'firstSeen': now, 'lastSeen': now, 'tokens': {},
        })
        creator_entry['lastSeen'] = now

        is_new_token = payload.pairAddress not in creator_entry['tokens']
        token = creator_entry['tokens'].setdefault(payload.pairAddress, {
            'pairAddress': payload.pairAddress, 'baseTokenAddress': payload.baseTokenAddress,
            'symbol': payload.symbol, 'dexId': payload.dexId,
            'firstSeenAt': now, 'firstLiquidityUsd': payload.liquidityUsd,
            'peakLiquidityUsd': payload.liquidityUsd or 0, 'lastLiquidityUsd': payload.liquidityUsd,
            'lastCheckedAt': now, 'status': 'active', 'authorityRenounced': authority_renounced,
        })
        if is_new_token and len(creator_entry['tokens']) > 1:
            # Only worth notifying once this creator has a track record — the very first
            # token observed for a brand-new creator isn't "news," it's just onboarding.
            rs._push_feed(store, payload.chain, creator_address, 'new_token', f'Launched a new token: {payload.symbol or "unnamed"}.')
        token['lastCheckedAt'] = now
        token['symbol'] = payload.symbol or token.get('symbol')
        if payload.liquidityUsd is not None:
            token['lastLiquidityUsd'] = payload.liquidityUsd
            token['peakLiquidityUsd'] = max(token.get('peakLiquidityUsd') or 0, payload.liquidityUsd)

        age = now - token['firstSeenAt']
        peak = token.get('peakLiquidityUsd') or 0
        last = token.get('lastLiquidityUsd')
        if token['status'] == 'active' and age >= rs.RUG_MIN_AGE_SECONDS and peak > 0 and last is not None:
            drop_pct = (1 - (last / peak)) * 100
            if drop_pct >= rs.RUG_LIQUIDITY_DROP_PCT:
                token['status'] = 'rugged'
                token['ruggedAt'] = now
                rs._push_feed(store, payload.chain, creator_address, 'flagged', f'{token.get("symbol") or "A token"} lost {drop_pct:.0f}% of peak liquidity — flagged as rugged.')
        if token['status'] == 'active' and age >= rs.SUSTAINED_AGE_SECONDS:
            token['status'] = 'sustained'

        scoring = rs.score_creator(creator_entry)
        creator_entry['scoring'] = scoring
        rs._save(store)
        return {'creator': creator_address, **scoring}


@router.post('/api/reputation/watch')
async def watch_creator(payload: _RSM.WatchPayload):
    rs = _rs()
    payload.ownerWallet = rs._session_or_401(payload.ownerWallet, payload.session)
    async with rs._lock:
        store = rs._load()
        bucket = store['watchlists'].setdefault(payload.ownerWallet, {})
        wkey = rs._creator_key(payload.chain, payload.address)
        existing = bucket.get(wkey, {})
        bucket[wkey] = {
            'chain': payload.chain, 'address': payload.address,
            'notifyNewToken': payload.notifyNewToken, 'notifyFlag': payload.notifyFlag,
            'addedAt': existing.get('addedAt', rs.time.time()),
        }
        rs._save(store)
        return {'ok': True, 'watch': bucket[wkey]}


@router.post('/api/reputation/unwatch')
async def unwatch_creator(payload: _RSM.UnwatchPayload):
    rs = _rs()
    payload.ownerWallet = rs._session_or_401(payload.ownerWallet, payload.session)
    async with rs._lock:
        store = rs._load()
        bucket = store['watchlists'].get(payload.ownerWallet, {})
        bucket.pop(rs._creator_key(payload.chain, payload.address), None)
        rs._save(store)
        return {'ok': True}


@router.post('/api/reputation/roadmap/vote')
async def roadmap_vote(payload: _RSM.VotePayload):
    rs = _rs()
    if len(payload.wallet) < 20 or len(payload.itemId) > 64:
        raise rs.HTTPException(400, 'Invalid vote.')
    payload.wallet = rs._session_or_401(payload.wallet, payload.session)  # one signed wallet, one vote
    async with rs._lock:
        store = rs._load()
        voters = store.setdefault('votes', {}).setdefault(payload.itemId, [])
        if payload.wallet in voters:
            voters.remove(payload.wallet)
        else:
            voters.append(payload.wallet)
        rs._save(store)
        return {'itemId': payload.itemId, 'count': len(voters), 'voted': payload.wallet in voters}


@router.post('/api/reputation/feeless-launch')
async def register_feeless_launch(payload: _RSM.FeelessLaunchPayload):
    """Tag a token as launched on FEELESS — only after the chain confirms this wallet created it."""
    rs = _rs()
    if payload.wallet in rs._any_agent_wallets():
        raise rs.HTTPException(403, 'An AI agent never launches a coin on FEELESS — on any other site it may.')
    creator = None
    if payload.signature and rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', payload.signature):
        # Proof from the launch transaction: it succeeded, this wallet signed it, and the new mint signed it.
        async with rs.httpx.AsyncClient(timeout=15) as http:
            tx = await rs._rpc(http, 'getTransaction', [payload.signature, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
        if tx and not (tx.get('meta') or {}).get('err'):
            signers = [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]
            if payload.wallet in signers and payload.mint in signers:
                creator = payload.wallet
    if not creator:
        resolved = await rs.resolve_creator(payload.chain, payload.mint)
        creator = (resolved or {}).get('identity') if isinstance(resolved, dict) else None
    if not creator:
        raise rs.HTTPException(409, 'Mint not yet visible on-chain — retry after confirmation.')
    if creator != payload.wallet:
        raise rs.HTTPException(403, 'This wallet did not create that mint.')
    async with rs._lock:
        store = rs._load()
        store.setdefault('feelessLaunches', {})[payload.mint] = {
            'chain': payload.chain, 'wallet': payload.wallet, 'mint': payload.mint, 'symbol': payload.symbol,
            'signature': payload.signature, 'at': rs.time.time(), 'rail': payload.rail if payload.rail in ('feeless', 'pump') else 'feeless',
            'config': rs._json_load(rs.LAUNCH_RAIL_PATH, {}).get('config') if payload.rail != 'pump' else None,
        }
        ckey = rs._creator_key(payload.chain, payload.wallet)
        entry = store['creators'].setdefault(ckey, {'chain': payload.chain, 'address': payload.wallet, 'firstSeen': rs.time.time(), 'lastSeen': rs.time.time(), 'tokens': {}})
        entry['lastSeen'] = rs.time.time()
        entry['tokens'].setdefault(payload.mint, {'pairAddress': payload.mint, 'baseTokenAddress': payload.mint, 'symbol': payload.symbol,
                                                  'dexId': 'feeless', 'firstSeenAt': rs.time.time(), 'status': 'active', 'launchedOnFeeless': True})
        entry['tokens'][payload.mint]['launchedOnFeeless'] = True
        rs._push_feed(store, payload.chain, payload.wallet, 'new_token', f'Launched {payload.symbol or "a token"} on FEELESS.')
        rs._save(store)
    pr = payload.profile or {}
    if isinstance(pr, dict) and any(pr.get(k) for k in ('bannerUrl', 'website', 'twitter', 'telegram', 'description')):
        ban = str(pr.get('bannerUrl') or '').strip()[:300]
        ban = rs.launch_meta.upload_path(ban) or (ban if ban.startswith('https://') else '')
        rec = {'description': str(pr.get('description') or '').strip()[:600], 'bannerUrl': ban,
               **{k: rs.launch_meta.social_url(k, str(pr.get(k) or '')) for k in ('website', 'twitter', 'telegram')}, 'claimedBy': rs.primary_of(creator), 'updatedAt': rs.time.time()}
        async with rs._admin_lock:
            d = rs._json_load(rs.COIN_PROFILES_PATH, {})
            if payload.mint not in d:
                d[payload.mint] = rec; rs._json_save(rs.COIN_PROFILES_PATH, d)
    return {'ok': True, 'creator': creator}


@router.post('/api/reputation/push/subscribe')
async def push_subscribe(payload: _RSM.PushSubscribe):
    rs = _rs()
    sub = payload.subscription
    if not str(sub.get('endpoint', '')).startswith('https://') or not (sub.get('keys') or {}).get('p256dh'):
        raise rs.HTTPException(400, 'Invalid push subscription.')
    sid = rs._sub_id(sub)
    async with rs._push_lock:
        d = rs._push_load()
        prev = d['subs'].get(sid, {})
        watch = []
        for w in payload.watch[:100]:
            if not isinstance(w, dict) or not w.get('pairAddress') or not w.get('chainId'):
                continue
            key = f"{w['chainId']}:{w['pairAddress']}"
            old = next((x for x in prev.get('watch', []) if f"{x['chainId']}:{x['pairAddress']}" == key), {})
            watch.append({'chainId': w['chainId'], 'pairAddress': w['pairAddress'], 'mint': w.get('mint'), 'symbol': w.get('symbol'),
                          'watchedPrice': w.get('watchedPrice'), 'watchedLiq': w.get('watchedLiq') or old.get('watchedLiq'),
                          'rules': {**rs.DEFAULT_RULES, **(w.get('rules') or {})}, 'state': old.get('state', {})})
        d['subs'][sid] = {'subscription': sub, 'watch': watch, 'prefs': {**rs.DEFAULT_PREFS, **rs._push_prefs(payload.prefs, prev.get('prefs'), payload.session)},
                          'createdAt': prev.get('createdAt', rs.time.time()), 'updatedAt': rs.time.time(), 'sent': prev.get('sent', [])[-50:]}
        rs._push_save(d)
    return {'ok': True, 'id': sid, 'watching': len(watch), 'walletLinked': bool(d['subs'][sid]['prefs'].get('address'))}


@router.post('/api/reputation/push/unsubscribe')
async def push_unsubscribe(payload: _RSM.PushUnsubscribe):
    rs = _rs()
    async with rs._push_lock:
        d = rs._push_load()
        d['subs'].pop(rs._sub_id({'endpoint': payload.endpoint}), None)
        rs._push_save(d)
    return {'ok': True}


@router.post('/api/reputation/push/test')
async def push_test(payload: _RSM.PushTest):
    rs = _rs()
    d = rs._push_load()
    entry = d['subs'].get(rs._sub_id({'endpoint': payload.endpoint}))
    if not entry:
        raise rs.HTTPException(404, 'Subscription not found — enable push first.')
    result = await rs.asyncio.to_thread(rs._send_push, entry['subscription'], 'FEELESS alerts are on', f"Watching {len(entry['watch'])} coin(s). You'll hear from us even with the site closed.", '/terminal/watchlist', 'feeless-test')
    return {'result': result}


@router.post('/api/reputation/calls')
async def register_call(payload: _RSM.CallPayload):
    """Price is taken by the server at registration — never trusted from the client."""
    rs = _rs()
    cid = rs.hashlib.sha256(f'{payload.messageId}:{payload.pairAddress}'.encode()).hexdigest()[:20]
    d = rs._calls_load()
    if cid in d['calls']:
        return {'ok': True, 'id': cid, 'existing': True}
    # Who called, when, and which coin all come from the signed chat message on the server —
    # a client can't register a call in someone else's name or backdate one.
    src = next((m for m in rs._chat_load()['rooms'].get(payload.room, []) if m.get('id') == payload.messageId), None)
    if not src or not any(t.get('pairAddress') == payload.pairAddress for t in (src.get('tokens') or [])):
        raise rs.HTTPException(404, 'No matching chat call.')
    payload.callerAddress = src.get('identity') or src.get('address')
    payload.caller = payload.caller if payload.caller == 'anon' else (src.get('username') or 'anon')
    payload.ts = src.get('ts')
    msg_ts = (payload.ts or rs.time.time() * 1000) / 1000 if (payload.ts or 0) > 1e11 else (payload.ts or rs.time.time())
    if rs.time.time() - msg_ts > 600:
        raise rs.HTTPException(409, 'Call is too old to price honestly.')
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{payload.chain}/{payload.pairAddress}')
            p = ((r.json() or {}).get('pairs') or [None])[0]
    except Exception:
        p = None
    price = float((p or {}).get('priceUsd') or 0)
    if not p or price <= 0:
        raise rs.HTTPException(404, 'No live market for that pair.')
    call = {'id': cid, 'messageId': payload.messageId[:80], 'room': payload.room[:80], 'caller': payload.caller[:40], 'callerAddress': (payload.callerAddress or '')[:64],
            'chain': payload.chain, 'pairAddress': payload.pairAddress, 'mint': (p.get('baseToken') or {}).get('address'),
            'symbol': (p.get('baseToken') or {}).get('symbol'), 'imageUrl': (p.get('info') or {}).get('imageUrl'),
            'priceAtCall': price, 'mcAtCall': p.get('marketCap') or p.get('fdv'), 'at': rs.time.time(),
            'lastPrice': price, 'peakPrice': price, 'checkedAt': rs.time.time()}
    async with rs._calls_lock:
        d = rs._calls_load()
        d['calls'].setdefault(cid, call)
        rs._calls_save(d)
    return {'ok': True, 'id': cid}


@router.post('/api/reputation/reactions')
async def react(payload: _RSM.ReactPayload):
    rs = _rs()
    import street_chat as _stc
    if payload.emoji not in (_stc.REACTS if payload.room.startswith('city-') else rs.REACTIONS) or not (6 <= len(payload.voter) <= 80):
        raise rs.HTTPException(400, 'Invalid reaction.')
    if not payload.voter.startswith('browser-'):   # 🔒 a wallet's vote needs that wallet's signed session; a guest votes as this browser
        owner_ = rs.session_address(payload.session) if payload.session else None
        if not owner_ or rs.primary_of(owner_) != rs.primary_of(payload.voter):
            raise rs.HTTPException(401, 'Sign in to react as this wallet.')
    async with rs._react_lock:
        d = rs._react_load()
        msg = d['rooms'].setdefault(payload.room[:120], {}).setdefault(payload.messageId[:80], {})
        voters = msg.setdefault(payload.emoji, [])
        if payload.voter in voters:
            voters.remove(payload.voter)
        else:
            voters.append(payload.voter)
        rs.REACT_PATH.write_text(rs.json.dumps(d))
    return {'ok': True}


@router.post('/api/reputation/profile/featured-badges')
async def set_featured_badges(payload: _RSM.FeaturedBadgesIn):
    """Pick which earned badges show next to your name in chat (only this field changes; chat session signs it)."""
    rs = _rs()
    owner = rs._session_or_401(payload.address, payload.session)
    ids = list(dict.fromkeys(str(b) for b in payload.badges if rs._re.match(r'^[a-z0-9-]{2,40}$', str(b))))
    earned = {b['id'] for b in (await rs.wallet_badges(owner))['badges']}
    picked = [b for b in ids if b in earned][:rs._badge_limits()['chat']]
    async with rs._profile_lock:
        rs._prof().update(owner, lambda cur: {**(cur or {}), 'featuredBadges': picked})
    return {'featuredBadges': picked}


@router.post('/api/reputation/x/oauth/start')
async def x_oauth_start(request: Request):
    rs = _rs()
    import base64 as _b64
    import hashlib as _hl
    import secrets as _sec
    b_ = await request.json()
    me_ = rs._session_or_401(str((b_ or {}).get('address') or ''), str((b_ or {}).get('session') or ''))
    cid_ = (rs.os.getenv('X_CLIENT_ID') or '').strip()
    if not cid_ or not rs._x_redirect().startswith('https://'):
        raise rs.HTTPException(409, 'Sign in with X turns on when the owner adds an X app (X_CLIENT_ID) and a public https site (PUBLIC_SITE_URL).')
    ver_ = _sec.token_urlsafe(48); st_ = _sec.token_urlsafe(18)
    ch_ = _b64.urlsafe_b64encode(_hl.sha256(ver_.encode()).digest()).rstrip(b'=').decode()
    now_ = rs.time.time(); [rs._x_states.pop(k_) for k_ in [k_ for k_, v_ in rs._x_states.items() if now_ - v_['at'] > 600]]
    rs._x_states[st_] = {'addr': me_, 'ver': ver_, 'at': now_, 'back': str((b_ or {}).get('back') or '/terminal/profile')[:200]}
    from urllib.parse import urlencode as _ue
    return {'url': 'https://twitter.com/i/oauth2/authorize?' + _ue({'response_type': 'code', 'client_id': cid_, 'redirect_uri': rs._x_redirect(), 'scope': 'users.read tweet.read',
                                                                     'state': st_, 'code_challenge': ch_, 'code_challenge_method': 'S256'})}


@router.post('/api/reputation/blocklist')
async def add_to_blocklist(payload: _RSM.BlockPayload):
    """Only wallets proven by FEELESS's own forensics to have bundled/sniped that mint are accepted.
    The reporter is the signed-in wallet, so every report is attributable. Blocklisting only adds a
    flag and a penalty line; the wallet's full record stays public."""
    rs = _rs()
    payload.reporter = rs._session_or_401(payload.reporter, payload.session)
    intel = await rs.token_intel('solana', payload.mint)
    evidence = {w: 'bundler' for w in intel.get('bundledWallets') or []}
    evidence.update({w: 'sniper' for w in intel.get('sniperWallets') or [] if w not in evidence})
    accepted, rejected, fresh = [], [], []
    async with rs._block_lock:
        d = rs._block_load()
        for w in [str(x) for x in payload.wallets[:200]]:
            if w not in evidence:
                rejected.append(w)
                continue
            rec = d['wallets'].setdefault(w, {'mints': {}, 'firstSeen': rs.time.time()})
            if not rec.get('reported'):
                fresh.append(w)
            rec['mints'].setdefault(payload.mint, evidence[w])
            rec['reported'] = True
            rec.setdefault('reports', []).append({'mint': payload.mint, 'role': evidence[w], 'by': (payload.reporter or 'anon')[:64], 'at': rs.time.time()})
            rec['reports'] = rec['reports'][-20:]
            accepted.append(w)
        rs._block_save(d, now=True)
    rs._intel_cache.pop(payload.mint, None)
    # Season points only for wallets nobody had reported yet: 25 each, capped at 100 per coin.
    if fresh:
        rs.season_award(payload.reporter, min(100, 25 * len(fresh)), f'rug-report:{payload.mint[:8]}')
    return {'accepted': accepted, 'rejected': rejected, 'newlyFlagged': len(fresh)}


@router.post('/api/reputation/internal/notify')
async def internal_notify(p: _RSM.InternalNotify, request: Request):
    """💵 A local service (FeeCat: a real cat's proposal) notifies one wallet — inbox + phone. Internal key only."""
    rs = _rs()
    import hmac
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), rs._internal_key()):
        raise rs.HTTPException(403, 'Internal endpoint.')
    rs.notify(p.address, p.kind, p.text, p.url, once=p.once, meta={'claim': 'Your cat proposes it — nothing trades until your wallet signs', 'source': 'FeeCat agent'})
    return {'ok': True}


@router.post('/api/reputation/internal/fee-post')
async def fee_post(payload: _RSM.FeeCallPayload, request: Request):
    """Only the local Fee engine (holder of the on-disk shared secret) may post as Fee."""
    rs = _rs()
    import hmac
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), rs._internal_key()):
        raise rs.HTTPException(403, 'Internal endpoint.')
    if payload.room == 'wall':
        cards = [t for t in payload.tokens[:3] if isinstance(t, dict) and isinstance(t.get('pair'), dict)]
        msg = rs.chat_system_post(f'wall-{rs.FEE_ADDRESS}', 'Fee 🐱', rs.FEE_ADDRESS, payload.text[:2000], tokens=cards)
        return {'ok': True, 'messageId': msg['id'], 'callId': None}
    room = f'coin-{payload.chain}-{payload.pairAddress}-trenches'
    # Attach the coin card: the call ledger only accepts calls whose message carries the coin,
    # and readers see what Fee bought right in the post.
    tokens = [{'chainId': payload.chain, 'pairAddress': payload.pairAddress}]
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{payload.chain}/{payload.pairAddress}')
            snap = ((r.json() or {}).get('pairs') or [None])[0]
        if snap:
            tokens = [{'chainId': payload.chain, 'pairAddress': payload.pairAddress, 'pair': snap,
                       'fetched_at': rs.time.strftime('%Y-%m-%dT%H:%M:%SZ', rs.time.gmtime())}]
    except Exception:
        pass
    msg = rs.chat_system_post(room, 'Fee 🐱', rs.FEE_ADDRESS, payload.text[:2000], tokens=tokens)
    try:
        head = payload.text.split('\n', 1)[0][:120]
        followers = [e for e in rs._push_load()['subs'].values() if (e.get('prefs') or {}).get('followFee')]
        for e in followers[:500]:
            rs.asyncio.get_running_loop().run_in_executor(None, rs._send_push, e['subscription'], 'Fee 🐱 just traded', head, f"/terminal/coin/solana/{payload.pairAddress}", 'fee-copy')
            if (e.get('prefs') or {}).get('address'):
                rs.notify(e['prefs']['address'], 'feecat', head, f"/terminal/coin/solana/{payload.pairAddress}", push=False,
                       meta={'claim': head, 'source': 'FeeCat trade post'})
    except Exception:
        pass
    call_id = None
    if payload.registerCall:
        res = await rs.register_call(rs.CallPayload(room=room, messageId=msg['id'], caller='Fee 🐱', callerAddress=rs.FEE_ADDRESS,
                                               chain=payload.chain, pairAddress=payload.pairAddress, ts=rs.time.time()))
        call_id = res.get('id')
    return {'ok': True, 'messageId': msg['id'], 'callId': call_id}


@router.post('/api/reputation/fuses/preview')
async def fuses_preview(payload: _RSM.FusePreview, request: Request = None):
    """Fuse Lab preview: auto-weights (fee APR × depth, 10–70% per pool) and where `sol` SOL would go. Read-only — moves nothing.
    Traders fuse up to 3 pools; HQ up to 6 and may set manual weights."""
    rs = _rs()
    admin = request is not None and rs._is_admin_req(request)
    cap = rs._fuse.legs_cap(admin)
    if len(payload.pools or []) > cap:
        raise rs.HTTPException(400, f'Fuse up to {cap} pools.')
    pools = rs._fuse.clean_legs([{**p, 'weight': p.get('weight') or 1} for p in payload.pools or []])
    n_run = len({str(x) for x in payload.runnerMints or [] if x})
    if len(pools) + n_run < 2:
        raise rs.HTTPException(400, 'Pick at least 2 legs (pools and/or runners).')
    if not rs._hq.legs_ok(len(pools), n_run, admin):
        raise rs.HTTPException(400, f'FEELESS cards hold up to {rs._hq.ADMIN_LEGS} legs (pools + runners).' if admin else
                            f'A card holds up to {rs._hq.CARD_POOLS} pools + {rs._hq.CARD_RUNNERS} runners.')
    pairs, sol_usd = await rs.asyncio.gather(rs._fuse_pairs(pools) if pools else rs.asyncio.sleep(0, {}), rs._sol_usd_live())
    metas = {k: rs._fuse.leg_meta(v) for k, v in pairs.items()}
    w = (rs._fuse.manual_weights(payload.pools) if admin and payload.manual else rs._vault.auto_weights(pools, metas, min_share=rs._fuse.min_share(len(pools)))) if pools else {}
    added = []; dropped_runners = []
    if payload.runnerMints:   # Fuse card: picked runners, 10% each, must be passing every gate right now
        live = await rs._runner_live()
        board_by = {r['mint']: r for r in live['passing'] + rs._rn.fresh_grads(live['dropped'])}   # 🎓 fresh grads are addable too
        rnd = (rs._json_load(rs.RUNNERS_PATH, {'rounds': []}).get('rounds') or [None])[-1]
        for p_ in ((rnd or {}).get('picks') or []):
            board_by.setdefault(p_['mint'], p_) if p_['mint'] in board_by else None
        lim = rs._hq.ADMIN_RUNNERS if admin else rs._hq.CARD_RUNNERS
        wanted = [m for m in dict.fromkeys(str(x) for x in payload.runnerMints) if m]
        picked = [board_by[m] for m in wanted if m in board_by][:lim]
        # a runner that JUST failed a gate is skipped (never an error for the whole card) — the Lab unticks it and says why
        why = {r['mint']: (r.get('gates') or ['left the live feed'])[0] for r in live['dropped']}
        dropped_runners = [{'mint': m, 'symbol': next((r.get('symbol') for r in live['dropped'] if r['mint'] == m), None), 'why': why.get(m, 'left the live feed')}
                           for m in wanted if m not in board_by]
        if not picked and not pools:
            raise rs.HTTPException(400, 'Every picked runner just failed a gate — pick from the live board.')
        legs = rs._rn.addon([{**p, 'weight': w[p['pairAddress']] * 100} for p in pools], picked, 10.0 * len(picked), len(picked))
        added = [l for l in legs if l.get('runner')]
        if added:
            rp = await rs._fuse_pairs(added)
            metas.update({k: rs._fuse.leg_meta(v) for k, v in rp.items()})
            pools = pools + [{k: l[k] for k in ('chainId', 'pairAddress', 'symbol')} for l in added if l['pairAddress'] in rp]
            w = {l['pairAddress']: l['weight'] / 100 for l in legs if l['pairAddress'] in metas}
    elif payload.runners:   # Runner add-on: top 2 runners of the current round as a small slice (server-picked, gated)
        live = await rs._runner_live()
        rnd = (rs._json_load(rs.RUNNERS_PATH, {'rounds': []}).get('rounds') or [None])[-1]
        tops = [p for p in ((rnd or {}).get('picks') or []) if p['mint'] in {r['mint'] for r in live['passing']}] or live['passing']
        legs = rs._rn.addon([{**p, 'weight': w[p['pairAddress']] * 100} for p in pools], [t for t in tops if t['pairAddress'] not in w], payload.runnerSlice, 2)
        added = [l for l in legs if l.get('runner')]
        if added:
            rp = await rs._fuse_pairs(added)
            metas.update({k: rs._fuse.leg_meta(v) for k, v in rp.items()})
            pools = pools + [{k: l[k] for k in ('chainId', 'pairAddress', 'symbol')} for l in added if l['pairAddress'] in rp]
            w = {l['pairAddress']: l['weight'] / 100 for l in legs if l['pairAddress'] in metas}
    out = rs._fuse.preview(pools, metas, max(0.0, min(100000.0, payload.sol)), sol_usd, w)
    if payload.runnerMints and dropped_runners:
        out = {**out, 'droppedRunners': dropped_runners}
    rinfo = {l['pairAddress']: l for l in added}
    out['legs'] = [{**x, **({'runner': True, 'exits': rinfo[x['pairAddress']]['exits'], 'lane': rinfo[x['pairAddress']]['lane']} if x['pairAddress'] in rinfo else {})} for x in out['legs']]
    return {**out, 'cap': cap, 'admin': admin, 'runners': len(added)}


@router.post('/api/reputation/fuses/guard')
async def fuse_guard(p: _RSM.FuseGuardIn):
    """Basket limits on YOUR Fuse position. Setting them costs nothing: fees are only paid if and when you Unfuse."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    mine = set(rs.linked_of(me)) | {me}
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine), None)
        if not pos:
            raise rs.HTTPException(404, 'No such Fuse position for this wallet.')
        if p.rebalance or (p.off and not (p.tp or p.sl or p.trail) and pos.get('autoRebalance')):
            pos['autoRebalance'] = {'tol': round(min(50.0, max(3.0, p.rebalance)), 1), 'lastAt': 0} if p.rebalance and not p.off else None
            if not pos['autoRebalance']:
                pos.pop('autoRebalance')
            rs._json_save(rs.FUSE_HQ_PATH, d)
            return {'ok': True, 'autoRebalance': pos.get('autoRebalance')}
        if p.off:
            pos.pop('guard', None)
        else:
            try:
                g = rs._hq.clean_guard(p.dict())
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            pos['guard'] = {**g, 'peak': 0.0, 'armedAt': rs.time.time(), 'firedAt': None}
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return {'ok': True, 'guard': pos.get('guard')}


@router.post('/api/reputation/fuses/mode')
async def fuse_mode(p: _RSM.FuseModeIn):
    """Per card: 'hold' (stay together) or 'swap' (alert + pre-filled switch when a leg turns weak)."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    if p.mode not in ('hold', 'swap'):
        raise rs.HTTPException(400, 'Mode is hold or swap.')
    mine = set(rs.linked_of(me)) | {me}
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise rs.HTTPException(404, 'No such open Fuse card for this wallet.')
        pos['mode'] = p.mode
        rs._json_save(rs.FUSE_HQ_PATH, d)
    rs._arena_mega_cache.update(at=0.0, data=None)
    return {'ok': True, 'mode': p.mode}


@router.post('/api/reputation/fuses/auto-yield')
async def fuse_auto_yield(p: _RSM.FuseYieldIn):
    """Arm / disarm 💸 auto-collect on YOUR card: alert + pre-filled Collect profit when held value is up `at`%."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    mine = set(rs.linked_of(me)) | {me}
    rules = rs._card_rules()
    if not p.off:
        at = float(p.at or rules['yieldDefault'])
        if at not in rules['yieldLevels']:
            raise rs.HTTPException(400, f"Pick one of the auto-profit levels: {', '.join(f'+{v:g}%' for v in rules['yieldLevels'])}.")
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
    if not pos:
        raise rs.HTTPException(404, 'No such open Fuse card for this wallet.')
    # Entry = your confirmed buy + its FEELESS fee; after a collect, what's still held.
    rr = None if p.off else rs._hq.position_pnl(pos, await rs._hq_prices(pos['legs']))
    base = 0.0 if p.off else round(rr['costUsd'] if not rr['realizedUsd'] else rs._hq.held_value(rr), 6)   # entry = confirmed buy at the pool, no fees
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        pos = next(x for x in d['positions'] if x['id'] == p.id)
        if p.off:
            pos.pop('autoYield', None)
        else:
            pos['autoYield'] = {'at': at, 'base': base, 'armedAt': rs.time.time(), 'firedAt': None}
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return {'ok': True, 'autoYield': pos.get('autoYield')}


@router.post('/api/reputation/fuses/freeze')
async def fuse_freeze(p: _RSM.FuseFreezeIn):
    """❄ Freeze a coin / pool on YOUR card: the engine (swap mode, auto-rotate suggestions) never touches it — only you can
    switch or sell it. Freeze 1, 2 or all of them; unfreeze any time."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    mine = set(rs.linked_of(me)) | {me}
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise rs.HTTPException(404, 'No open Fuse card with that id for this wallet.')
        if not any(leg['pairAddress'] == p.pairAddress and leg.get('soldUsd') is None for leg in pos['legs']):
            raise rs.HTTPException(400, 'That coin is not open on this card.')
        fz = [x for x in pos.get('frozen') or [] if x != p.pairAddress] + ([p.pairAddress] if p.frozen else [])
        pos['frozen'] = fz
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return {'ok': True, 'frozen': fz}


@router.post('/api/reputation/fuses/coin-mode')
async def fuse_coin_mode(p: _RSM.CoinModeIn):
    """Per-coin stop mode on YOUR card: ✂ sell · 🅿 park (sell to SOL, one-tap buy-back when it's back with buyers) · ❄ hold —
    or 'card' to follow the card's setting. Pairs with ❄ freeze (engine hands off the coin)."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    mine = set(rs.linked_of(me)) | {me}
    if p.slMode and p.slMode not in (*rs._hq.SL_MODES, 'card'):
        raise rs.HTTPException(400, 'slMode must be sell, park, hold or card.')
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise rs.HTTPException(404, 'No open Fuse card with that id for this wallet.')
        if not any(leg['pairAddress'] == p.pairAddress and leg.get('soldUsd') is None for leg in pos['legs']):
            raise rs.HTTPException(400, 'That coin is not open on this card.')
        cm = dict(pos.get('coinModes') or {})
        if p.slMode:
            cm.pop(p.pairAddress, None)
            if p.slMode != 'card':
                cm[p.pairAddress] = p.slMode
        pos['coinModes'] = cm
        if p.tp is not None or p.sl is not None:   # 🎯 this coin's own TP / SL (alerts once, one-tap sell)
            g = {**(pos.get('legGuard') or {}).get(p.pairAddress, {})}
            if p.tp is not None:
                g['tp'] = max(0.0, min(5000.0, float(p.tp)))
            if p.sl is not None:
                g['sl'] = max(0.0, min(95.0, float(p.sl)))
            g['firedAt'] = None
            pos.setdefault('legGuard', {})[p.pairAddress] = g
        if p.rotateHours is not None:
            cr = {k: v for k, v in (pos.get('coinRotate') or {}).items() if k != p.pairAddress}
            if p.rotateHours:
                cr[p.pairAddress] = rs._hq.rotate_hours(p.rotateHours)
            pos['coinRotate'] = cr
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return {'ok': True, 'coinModes': cm, 'legGuard': (pos.get('legGuard') or {}).get(p.pairAddress), 'coinRotate': pos.get('coinRotate') or {}}


@router.post('/api/reputation/fuses/bracket/pick')
async def bracket_pick(p: _RSM.BracketPick):
    """🔮 Call the bracket champion — free, one call per wallet per bracket, locked once made. Right = season XP + inbox."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    keys = {f"{c['kind']}:{c['id']}" for c in rs._rn.unique_cards(rs._arena_mega_cache.get('data') or [])}
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); br = d.setdefault('bracket', {})
        if p.key not in keys or int(((br.get('cards') or {}).get(p.key) or {}).get('l') or 0) >= 2:
            raise rs.HTTPException(400, 'That card is not standing in this bracket.')
        picks = br.setdefault('picks', {})
        if me in picks:
            raise rs.HTTPException(409, 'You already called this bracket.')
        picks[me] = p.key; rs._json_save(rs.FUSE_HQ_PATH, d)
    return {'ok': True, 'key': p.key, 'season': br.get('season') or 1}


@router.post('/api/reputation/fuses/battle/back')
async def battle_back(p: _RSM.BattleBack):
    """⚔ Back a side in the live battle — free, points only (no money). One pick per wallet per battle, locked once made."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); b = d.get('battles') or {}
        if not any(p.key in (x['a']['key'], x['b']['key']) for x in b.get('pairs') or []):
            raise rs.HTTPException(400, 'That card is not in the current battle.')
        backs = b.setdefault('backs', {})
        if me in backs:
            raise rs.HTTPException(409, 'You already backed a side this battle.')
        backs[me] = p.key; d['battles'] = b
        d.setdefault('backLog', {})[me] = ((d.get('backLog') or {}).get(me) or [])[-199:] + [rs.time.time()]
        rs._json_save(rs.FUSE_HQ_PATH, d)
    rec = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('backRecord') or {}).get(me) or {'w': 0, 'l': 0}
    return {'ok': True, 'key': p.key, 'record': rec}


@router.post('/api/reputation/social-feed/react')
async def social_feed_react(p: _RSM.FeedReact):
    """♥ / 💬 on any FEEd post (signed-in chat session; the guard's write-flood limit applies like every write)."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    if rs._is_blocked(rs._block_load()['wallets'].get(me)):
        raise rs.HTTPException(403, 'This wallet cannot post here.')
    async with rs._fsoc_lock:
        st = rs._json_load(rs.FEED_SOCIAL_PATH, {})
        try:
            out = {}
            if p.like:
                out['liked'], out['likes'] = rs._fsoc.like(st, me, p.id, rs.time.time())
            if p.comment.strip():
                out['comment'] = rs._fsoc.comment(st, me, rs._crew_name(me), p.id, p.comment, rs.time.time())
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs._json_save(rs.FEED_SOCIAL_PATH, st)
    return {**out, **rs._fsoc.counts(st, [p.id], me)}


@router.post('/api/reputation/crews/switch')
async def crew_switch(p: _RSM.CrewSwitch):
    """👥 Make another of MY families the active one (every Familia page then shows that family)."""
    rs = _rs()
    import crews as _cr
    me = rs._session_or_401(p.address, p.session)
    async with rs._crews_lock:
        st = rs._json_load(rs.CREWS_PATH, {})
        try:
            c = _cr.switch(st, me, p.cid)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs._json_save(rs.CREWS_PATH, st)
    return {'crew': {'id': c['id'], 'tag': c.get('tag'), 'name': c.get('name')}}


@router.post('/api/reputation/crews/join')
async def crew_join(p: _RSM.CrewJoin):
    rs = _rs()
    import crews as _cr
    me = rs._session_or_401(p.address, p.session)
    if rs._is_blocked(rs._block_load()['wallets'].get(me)):
        raise rs.HTTPException(403, 'This wallet cannot join a family.')
    async with rs._crews_lock:
        st = rs._json_load(rs.CREWS_PATH, {})
        try:
            rs._crew_cfg(); c = _cr.join(st, me, p.code, rs.time.time())
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs._json_save(rs.CREWS_PATH, st)
    rs._crew_cache['data'] = None
    return {'crew': rs._crew_view(c, rs._crew_pieces(c['members'], rs.time.time()), with_code=True)}


@router.post('/api/reputation/familia/broker/keys')
async def familia_broker_keys(request: Request):
    """🔑 Add (or remove) YOUR OWN Alpaca keys: checked live against your account first, then sealed to your wallet — no SnapTrade, no owner
    setup, $0 to start (a free Alpaca account; paper keys work the same minute). {remove: true} deletes them."""
    rs = _rs()
    import brokers as _bk
    b_ = await request.json()
    me_ = rs._session_or_401(str((b_ or {}).get('address') or ''), str((b_ or {}).get('session') or ''))
    rs._brk_seal()
    st_ = rs._json_load(rs.BROKERS_PATH, {}) or {}
    rec_ = dict(st_.get(me_) or {})
    venue_ = 'cdc' if str((b_ or {}).get('venue') or '') == 'cdc' else 'alpaca'
    if (b_ or {}).get('remove'):
        rec_.pop(venue_, None)
        if rec_:
            st_[me_] = rec_
        else:
            st_.pop(me_, None)
        rs._json_save(rs.BROKERS_PATH, st_); rs._brk_cache.pop(me_, None)
        return {'ok': True}
    key_, sec_, paper_ = str(b_.get('key') or '').strip(), str(b_.get('secret') or '').strip(), bool(b_.get('paper'))
    if venue_ == 'cdc':   # 🔑 Crypto.com Exchange: proved against the user's own balance before anything is stored
        if not _bk.cdc_keys_ok(key_, sec_):
            raise rs.HTTPException(400, 'That does not look like a Crypto.com Exchange API key + secret.')
        bal_ = await rs._cdc_call({'key': key_, 'secret': sec_}, 'private/user-balance')
        rec_['cdc'] = {'sec': _bk.seal(rs.json.dumps({'key': key_, 'secret': sec_}), rs.os.environ), 'at': rs.time.time()}
        st_[me_] = rec_
        rs._json_save(rs.BROKERS_PATH, st_); rs._brk_cache.pop(me_, None)
        return {'ok': True, 'account': _bk.cdc_view(bal_)}
    if not _bk.alpaca_keys_ok(key_, sec_):
        raise rs.HTTPException(400, 'That does not look like an Alpaca Key ID + Secret.')
    acct_ = await rs._alpaca_call({'key': key_, 'secret': sec_, 'paper': paper_}, 'GET', '/v2/account')   # proves the keys before anything is stored
    rec_['alpaca'] = {'sec': _bk.seal(rs.json.dumps({'key': key_, 'secret': sec_}), rs.os.environ), 'paper': paper_, 'at': rs.time.time()}
    st_[me_] = rec_
    rs._json_save(rs.BROKERS_PATH, st_); rs._brk_cache.pop(me_, None)
    return {'ok': True, 'account': _bk.alpaca_view(acct_, [], paper_)}


@router.post('/api/reputation/familia/broker/order')
async def familia_broker_order(request: Request):
    """🎟 BUY / SELL in YOUR linked account (stocks · ETFs · crypto where the broker allows): Market by $ or units, or Limit — checked here
    (your own account, a real ticker, ≤ brokers.MAX_ORDER_USD) then sent through SnapTrade to the broker."""
    rs = _rs()
    import brokers as _bk
    b_ = await request.json()
    me_ = rs._session_or_401(str((b_ or {}).get('address') or ''), str((b_ or {}).get('session') or ''))
    if str((b_ or {}).get('action') or '').upper() != 'SELL':   # ⚖ LEGAL-1 (d): a buy is checked; a sell is an exit
        rs._legal_hold(me_, 'brokers', request)
    rs._brk_seal()
    if str((b_ or {}).get('accountId') or '') == 'cdc':   # 🔑 the user's own Crypto.com Exchange keys
        ck_ = rs._brk_cdc(me_)
        if not ck_:
            raise rs.HTTPException(409, 'Add your Crypto.com keys first.')
        try:
            if str((b_ or {}).get('market') or '') == 'perp':   # 📉 a perps order in the user's own account (Crypto.com decides eligibility)
                sym_ = rs._re.sub(r'[^A-Z0-9]', '', str((b_ or {}).get('symbol') or '').upper().replace('USD-PERP', '').replace('USD', '')) or 'BTC'
                inst_ = next((r_ for r_ in await rs._cdc_instruments() if r_.get('symbol') == f'{sym_}USD-PERP'), None)
                if not inst_:
                    raise ValueError(f'Crypto.com lists no {sym_} perpetual.')
                tk_ = await rs._fmk_http_get().get(f'{_bk.CDC_API}/public/get-tickers', params={'instrument_name': inst_['symbol']}, timeout=10)
                mark_ = rs._fuse._f((((tk_.json() or {}).get('result') or {}).get('data') or [{}])[0].get('a'))
                ob_ = _bk.cdc_perp_order(b_, inst_, mark_)
            else:
                ob_ = _bk.cdc_order(b_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        d_ = await rs._cdc_call(ck_, 'private/create-order', ob_)
        rs._brk_cache.pop(me_, None)
        return {'status': 'ACCEPTED', 'id': d_.get('order_id'), 'filled': None, 'price': None, 'symbol': ob_['instrument_name'], 'action': ob_['side']}
    if str((b_ or {}).get('accountId') or '') == 'alpaca':   # 🔑 the user's own Alpaca keys
        ak_ = rs._brk_alpaca(me_)
        if not ak_:
            raise rs.HTTPException(409, 'Add your Alpaca keys first.')
        try:
            ob_ = _bk.alpaca_order(b_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        d_ = await rs._alpaca_call(ak_, 'POST', '/v2/orders', ob_)
        rs._brk_cache.pop(me_, None)
        return {'status': d_.get('status'), 'id': d_.get('id'), 'filled': d_.get('filled_qty'), 'price': d_.get('filled_avg_price'), 'symbol': ob_['symbol'], 'action': ob_['side'].upper()}
    rs._brk_need()
    q_ = rs._brk_q(me_)
    if q_ is None:
        raise rs.HTTPException(409, 'Link a broker first.')
    ids_ = [a_.get('id') for a_ in (await rs._brk_call('GET', '/accounts', q_) or []) if a_.get('id')]
    try:
        body_ = _bk.order_body(b_, ids_)
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    d_ = await rs._brk_call('POST', '/trade/place', q_, body_)
    rs._brk_cache.pop(me_, None)
    return {'status': d_.get('status'), 'id': d_.get('brokerage_order_id'), 'filled': d_.get('filled_quantity'), 'price': d_.get('execution_price'),
            'symbol': body_['symbol'], 'action': body_['action']}


@router.post('/api/reputation/familia/broker/unlink')
async def familia_broker_unlink(request: Request):
    """✂ Unlink: deletes this wallet's SnapTrade user (every broker connection with it) and FEELESS's sealed secret."""
    rs = _rs()
    b_ = await request.json()
    me_ = rs._session_or_401(str((b_ or {}).get('address') or ''), str((b_ or {}).get('session') or ''))
    u_ = rs._brk_user(me_)
    if u_:
        try:
            await rs._brk_call('DELETE', '/snapTrade/deleteUser', {'userId': u_[0]})
        except rs.HTTPException:
            pass
    st_ = rs._json_load(rs.BROKERS_PATH, {}) or {}
    st_.pop(me_, None)
    rs._json_save(rs.BROKERS_PATH, st_)
    rs._brk_cache.pop(me_, None)
    return {'ok': True}


@router.post('/api/reputation/familia/kalshi/order')
async def familia_kalshi_order(request: Request):
    """🎟 Build a Kalshi order the wallet signs: {address, coin, side: up | down, usd[, ticker]} buys this 15-minute window's (or a ladder strike's) YES (up) / NO (down);
    {address, act: 'redeem', mint, amount} cashes settled winners. DFlow builds it; FEELESS checks it is exactly the ticket and safe."""
    rs = _rs()
    kt_ = rs._kt_need()
    b_ = await request.json()
    addr_ = rs._kt_addr((b_ or {}).get('address'))
    if (b_ or {}).get('act') == 'redeem':
        mint_, amt_ = str(b_.get('mint') or ''), int(rs._fuse._f(b_.get('amount')))
        m_ = await rs._kt_market(f'market/by-mint/{mint_}', f'mint:{mint_}', ttl=30, miss_ttl=600)
        ok_, why_ = kt_.redeemable(m_, mint_)
        if not ok_ or amt_ <= 0:
            raise rs.HTTPException(400, why_ or 'Nothing to redeem.')
        in_, out_, amount_ = mint_, kt_.USDC, amt_
        meta_ = {'act': 'redeem', 'ticker': m_.get('ticker')}
    else:
        coin_, side_, usd_ = str(b_.get('coin') or '').upper(), str(b_.get('side') or ''), rs._fuse._f(b_.get('usd'))
        rs._legal_hold(addr_, 'games', request)   # ⚖ LEGAL-1 (d): a buy is checked; a redeem is an exit
        ok_, why_ = kt_.ticket(coin_, side_, usd_)
        if not ok_:
            raise rs.HTTPException(400, why_)
        if not await rs._kt_proof(addr_):
            raise rs.HTTPException(403, 'PROOF: verify this wallet with DFlow Proof first (free, one time) — Kalshi is a regulated market.')
        row_k_ = (await rs.familia_kalshi())['coins'].get(coin_) or {}
        live_ = row_k_.get('up') or {}
        want_ = str(b_.get('ticker') or '')
        if want_:   # 🎯 a strike from the ladder: only a ticker on the server's OWN current ladder for this coin (UP = YES above it, DOWN = NO)
            hit_ = next((r_ for r_ in row_k_.get('ladder') or [] if r_.get('ticker') == want_), None)
            if not hit_:
                raise rs.HTTPException(409, 'That strike is no longer on the board — pick one from the live ladder.')
            live_ = {'ticker': hit_['ticker'], 'target': hit_['strike'], 'closes': hit_.get('closes')}
        if not live_.get('ticker'):
            raise rs.HTTPException(409, f'No live {coin_} window right now — the next one opens soon.')
        m_ = await rs._kt_market(f"market/{live_['ticker']}", f"t:{live_['ticker']}", ttl=60, miss_ttl=30)
        yes_, no_ = kt_.side_mints(m_)
        if not m_ or m_.get('status') not in ('active', 'open') or not (yes_ and no_):
            raise rs.HTTPException(409, 'This window is not tradable on Solana yet — try the next one.')
        in_, out_, amount_ = kt_.USDC, yes_ if side_ == 'up' else no_, int(round(usd_ * 1e6))
        meta_ = {'act': 'buy', 'coin': coin_, 'side': side_, 'usd': usd_, 'ticker': live_['ticker'], 'target': live_.get('target'), 'closes': live_.get('closes'),
                 'ask': live_.get('yes') if side_ == 'up' else live_.get('no')}
    try:
        r_ = await rs._fmk_http_get().get(f'{kt_.TRADE}/order', params=kt_.order_params(in_, out_, amount_, addr_), headers=kt_.headers(rs.os.environ), timeout=12)
        o_ = r_.json() if r_.status_code == 200 else None
    except Exception:
        o_ = None
    if not o_:
        raise rs.HTTPException(502, 'DFlow did not build the order — try again.')
    ok_, why_ = kt_.matches(o_, in_, out_, amount_)
    if not ok_:
        raise rs.HTTPException(502, why_)
    ok_, why_, fp_ = kt_.verify(o_['transaction'], addr_)
    if not ok_:
        raise rs.HTTPException(502, f'Refused by FEELESS safety check: {why_}')
    kt_.remember(fp_, addr_)
    return {**meta_, 'transaction': o_['transaction'], 'outAmount': o_.get('outAmount'), 'executionMode': o_.get('executionMode'),
            'lastValidBlockHeight': o_.get('lastValidBlockHeight'), 'safety': {'verified': True, 'fingerprint': fp_}}


@router.post('/api/reputation/familia/paper-perps')
async def familia_paper_perps_act(p: _RSM.PaperPerpAct):
    """📉 open · close · reset a paper perps position at the live mark. Paper only — nothing is sent to any venue."""
    rs = _rs()
    import paper_perps as _pp
    me_ = rs._session_or_401(p.address, p.session)
    if not rs._perps_cache.get('rows'):
        await rs.familia_perps()
    bd_ = rs._pperp_board(); now_ = rs.time.time()
    async with rs._pperp_lock:
        d_ = rs._json_load(rs.PAPER_PERPS_PATH, {}) or {}
        book_ = d_.get(me_) or _pp.blank(now_)
        try:
            if p.act == 'open':
                r_ = bd_.get(p.coin.upper())
                if not r_:
                    raise ValueError('That market is not on the board right now.')
                _pp.open_pos(book_, r_['coin'], p.side, p.margin, p.lev, r_.get('mark'), r_.get('maxLev'), now_)
            elif p.act == 'close':
                pos_ = next((x_ for x_ in book_['open'] if x_['id'] == p.id), None)
                b_ = bd_.get((pos_ or {}).get('coin')) or {}
                _pp.close_pos(book_, p.id, b_.get('mark'), b_.get('fundApr'), now_)
            elif p.act == 'reset':
                book_ = _pp.blank(now_)
            else:
                raise ValueError('open, close or reset.')
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        d_[me_] = book_
        if len(d_) > 5000:
            for k_ in sorted(d_, key=lambda k: (d_[k].get('since') or 0))[:500]:
                d_.pop(k_, None)
        rs._json_save(rs.PAPER_PERPS_PATH, d_)
        return _pp.view(book_, bd_, now_)


@router.post('/api/reputation/internal/openrouter-check')
async def internal_openrouter_check(request: Request):
    rs = _rs()
    if not rs._internal_ok(request):
        raise rs.HTTPException(403, 'Internal only.')
    return {'left': await rs._openrouter_left(fresh=True)}


@router.post('/api/reputation/familia/perps-real/execute')
async def familia_perps_real_execute(request: Request):
    """📉 The wallet-signed perps transaction → Jupiter's /transaction/execute (its keeper co-signs and lands it). Checked again first."""
    rs = _rs()
    import jup_perps as _jp
    body = await request.json()
    if not await rs._ip_hit(rs._fjx_hits, request, 30, 3600):   # 🔒 audit #8: no quota burn on FEELESS's Jupiter key
        raise rs.HTTPException(429, 'Too many perps sends from here — try again in a while.')
    act_, tx_, me_ = str((body or {}).get('action') or ''), str((body or {}).get('signed') or ''), str((body or {}).get('address') or '')
    if act_ not in ('increase-position', 'decrease-position', 'create-tpsl', 'update-tpsl', 'cancel-tpsl'):
        raise rs.HTTPException(400, 'Open, close or TP / SL only.')
    if act_ not in rs._legal.PERPS_EXITS:   # ⚖ LEGAL-1 (d): the last stop before Jupiter lands it; closing / cancelling is never held
        rs._legal_hold(me_, 'perps', request)
    ok_, bad_ = _jp.verify(tx_, me_, signed=True)
    if not ok_:
        raise rs.HTTPException(400, f'Refused: {bad_}')
    c_, b_ = await rs._jp_call('POST', 'transaction/execute', json={'action': act_, 'serializedTxBase64': tx_})
    if c_ != 200 or not (b_ or {}).get('txid'):
        raise rs.HTTPException(502, f"Jupiter did not land it: {str((b_ or {}).get('message') or c_)[:160]}")
    return {'txid': b_['txid'], 'action': act_}


@router.post('/api/reputation/familia-pools/autorange/arm')
async def familia_autorange_arm(request: Request):
    """📲 Arm (or with {remove: position} disarm) the AutoRange watcher on a band the wallet really opened: venue · pool · position · the band's
    edges in the pool's own price · the strategy's wait. Signed session; ≤ 10 bands per wallet. The watcher only ever NOTIFIES — the wallet signs every move."""
    rs = _rs()
    b_ = await request.json()
    me_ = rs._session_or_401(str((b_ or {}).get('address') or ''), str((b_ or {}).get('session') or ''))
    st_ = rs._json_load(rs.AUTORANGE_PATH, {}) or {}
    rows_ = [r_ for r_ in (st_.get(me_) or []) if r_.get('position') != (b_.get('remove') or b_.get('position'))]
    if not b_.get('remove'):
        lo_, hi_ = rs._fuse._f(b_.get('lo')), rs._fuse._f(b_.get('hi'))
        if b_.get('venue') not in ('raydium', 'meteora') or not (0 < lo_ < hi_) or not 32 <= len(str(b_.get('pool') or '')) <= 44 or not 32 <= len(str(b_.get('mint') or '')) <= 44:
            raise rs.HTTPException(400, 'A Raydium / Meteora band with its pool, token and edges.')
        rows_ = (rows_ + [{'venue': b_['venue'], 'pool': b_['pool'], 'mint': b_['mint'], 'sym': str(b_.get('sym') or '')[:24], 'position': str(b_.get('position') or '')[:64],
                           'lo': lo_, 'hi': hi_, 'wait': max(1.0, min(240.0, rs._fuse._f(b_.get('wait')) or 15.0)), 'at': rs.time.time()}])[-10:]
    if rows_:
        st_[me_] = rows_
    else:
        st_.pop(me_, None)
    rs._json_save(rs.AUTORANGE_PATH, st_)
    return {'ok': True, 'bands': len(rows_)}


@router.post('/api/reputation/hq/pair')
async def hq_pair_new(request: Request, port: int = Query(51367, ge=1, le=65535)):
    """A fresh one-time code (3 min; at most 20 waiting — hq_pair.MAX_OPEN) + the QR link: Phantom CONNECT answering to this computer's
    page on the Wi-Fi (Phantom's deeplink protocol — no in-app browser)."""
    rs = _rs()
    if not await rs._ip_hit(rs._hqp_ip, request, 6, 180):   # 🔒 audit #8: one device can't flood the 20 waiting codes and evict the owner's QR
        raise rs.HTTPException(429, 'Too many sign-in codes — wait a minute.')
    now = rs.time.time(); code = rs._hqp.new_code(rs._hqp_store, now); site = rs._hqp_site(port)
    return {'code': code, 'ttl': rs._hqp.TTL, 'lan': rs._lan_ip(), 'link': rs._hqp.connect_link(rs._hqp_store, code, site, now) if site else None}


@router.post('/api/reputation/hq/pair/{code}/connect')
async def hq_pair_connect(code: str, p: _RSM.HqPairAnswer):
    """Phantom's CONNECT answer (opened on the phone's browser) → the SIGN-MESSAGE deeplink for the HQ message."""
    rs = _rs()
    site = rs._hqp_site(p.port)
    try:
        out = rs._hqp.on_connect(rs._hqp_store, code[:64], site, p.pub, p.nonce, p.data, rs.time.time())
    except KeyError as e:
        raise rs.HTTPException(410, str(e.args[0]))
    except Exception:
        raise rs.HTTPException(400, 'Phantom\'s answer could not be read — scan a fresh QR.')
    if out['address'] not in rs._admin_wallets():
        raise rs.HTTPException(403, 'This wallet is not a FEELESS HQ wallet.')
    return out


@router.post('/api/reputation/hq/pair/{code}/signed')
async def hq_pair_signed(code: str, p: _RSM.HqPairAnswer):
    """Phantom's SIGN-MESSAGE answer → verified like a normal HQ sign-in → the computer's poll receives it once."""
    rs = _rs()
    now = rs.time.time()
    try:
        address, ts, sig = rs._hqp.on_signed(rs._hqp_store, code[:64], p.nonce, p.data, now)
    except KeyError as e:
        raise rs.HTTPException(410, str(e.args[0]))
    except Exception:
        raise rs.HTTPException(400, 'Phantom\'s answer could not be read — scan a fresh QR.')
    rs._hq_auth.check_session(address, str(ts), sig, rs._admin_wallets(), rs._verify_wallet, now)
    try:
        rs._hqp.put(rs._hqp_store, code[:64], {'address': address, 'ts': ts, 'sig': sig}, now)
    except KeyError as e:
        raise rs.HTTPException(410, str(e.args[0]))
    return {'ok': True}


@router.post('/api/reputation/hq/pair/{code}')
async def hq_pair_sign(code: str, p: _RSM.HqPairSig):
    """The phone posts its signed HQ session — verified like a normal sign-in (owner / admin wallet, fresh, the signature matches)."""
    rs = _rs()
    now = rs.time.time()
    rs._hq_auth.check_session(p.address, str(p.ts), p.sig, rs._admin_wallets(), rs._verify_wallet, now)
    try:
        rs._hqp.put(rs._hqp_store, code[:64], {'address': p.address, 'ts': p.ts, 'sig': p.sig}, now)
    except KeyError as e:
        raise rs.HTTPException(410, str(e.args[0]))
    return {'ok': True}


@router.post('/api/reputation/crews/leave')
async def crew_leave(p: _RSM.CrewWho):
    rs = _rs()
    import crews as _cr
    me = rs._session_or_401(p.address, p.session)
    async with rs._crews_lock:
        st = rs._json_load(rs.CREWS_PATH, {})
        try:
            _cr.leave(st, me)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs._json_save(rs.CREWS_PATH, st)
    rs._crew_cache['data'] = None
    return {'ok': True}


@router.post('/api/reputation/rep-markets/stake')
async def rep_market_stake(p: _RSM.RepStake):
    """Back YES or NO with chips (chat session). Your trust score at that moment is stored on the stake (the rep-weighted price)."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session); now = rs.time.time()
    rep_ = rs._rep_of([me]).get(me, 50.0)
    async with rs._rm_lock:
        st = rs._json_load(rs.REP_MARKETS_PATH, {}) or {}
        try:
            rs._repm.stake(st, me, p.market, p.side, p.chips, now, rep_)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs._json_save(rs.REP_MARKETS_PATH, st)
    ws = {s_['w'] for m in st.get('markets') or [] for s_ in m['stakes']}
    return rs._repm.board(st, now, me, rs._rep_of(ws))


@router.post('/api/reputation/internal/agent-image')
async def internal_agent_image(request: Request, body: dict):
    """🎨 An agent's picture: the same image model and daily spend cap as the owner's. feecat charges that agent's own budget what it really cost."""
    rs = _rs()
    if not rs._internal_ok(request):
        raise rs.HTTPException(403, 'Internal only.')
    res = await rs._air.ROUTER.gen_image(rs._ai_http(), rs.os.environ, rs._ai_cfg(), str(body.get('prompt') or '')[:1200])
    return {'url': res['url'], 'usd': res.get('usd') or 0} if res.get('ok') else {'why': res.get('why') or 'no picture came back'}


@router.post('/api/reputation/internal/agent-bid')
async def internal_agent_bid(request: Request, body: dict):
    """🎲 A PoB's door to the board: free chips only, staked or read under the board's lock, as `agent:<id>`. Its chips never earn season points."""
    rs = _rs()
    if not rs._internal_ok(request):
        raise rs.HTTPException(403, 'Internal only.')
    who = f"agent:{str(body.get('catId') or '')[:40]}"; mid = str(body.get('market') or '')[:16]; now = rs.time.time()
    async with rs._rm_lock:
        st = rs._json_load(rs.REP_MARKETS_PATH, {}) or {}
        if body.get('op') == 'stake':
            try:
                rs._repm.stake(st, who, mid, str(body.get('side') or ''), int(body.get('chips') or 0), now, 50)
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs._json_save(rs.REP_MARKETS_PATH, st)
        m = next((x for x in st.get('markets') or [] if x['id'] == mid), None)
    return {'market': rs._repm.view(m, now, who) if m else None}


@router.post('/api/reputation/predict/pick')
async def predict_pick(p: _RSM.PredictPick):
    """⚡ Pick the coin you think leads the next hour — free, points only. One pick per round, locked once made; closes 2 minutes before the bell."""
    rs = _rs()
    import predict as _pr
    me = rs._session_or_401(p.address, p.session); now = rs.time.time()
    if rs._is_blocked(rs._block_load()['wallets'].get(me)):
        raise rs.HTTPException(403, 'This wallet cannot play.')
    async with rs._predict_lock:
        d = rs._json_load(rs.PREDICT_PATH, {'rounds': {}, 'players': {}}); r = (d.get('rounds') or {}).get(str(p.round))
        ok, why = _pr.can_pick(r, p.mint, now)
        if not ok:
            raise rs.HTTPException(400, why)
        if me in r['picks']:
            raise rs.HTTPException(409, 'You already made your call this round.')
        r['picks'][me] = p.mint
        pl = d.setdefault('players', {}).setdefault(me, {'picks': 0, 'wins': 0, 'streak': 0, 'best': 0, 'pickAt': [], 'winAt': []})
        pl['pickAt'] = (pl.get('pickAt') or [])[-199:] + [now]
        rs._json_save(rs.PREDICT_PATH, d)
    return {'ok': True, 'round': p.round, 'mint': p.mint}


@router.post('/api/reputation/alliances')
async def alliances_act(request: Request):
    """🤝 create · join · leave · union, as the signed wallet."""
    rs = _rs()
    import alliances as _al
    b = await request.json(); wallet = rs._session_or_401(str(b.get('wallet') or ''), str(b.get('session') or ''))
    async with rs._alliance_lock:
        st = rs._json_load(rs.ALLIANCES_PATH, {}) or {}; rows = st.setdefault('rows', []); days = int(st.get('days') or _al.DEFAULT_DAYS); now = rs.time.time()
        try:
            op = b.get('op')
            if op == 'create':
                _al.create(rows, wallet, b.get('name'), now, b.get('reply'))
            elif op == 'join':
                _al.join(rows, wallet, str(b.get('id') or ''))
            elif op == 'leave':
                _al.leave(rows, wallet)
            elif op == 'union':
                _al.found_union(rows, wallet, b.get('name'), days, now)
            else:
                raise ValueError('Unknown action.')
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs._json_save(rs.ALLIANCES_PATH, st)
    return rs._alliance_view(wallet)


@router.post('/api/reputation/internal/sicario-want')
async def internal_sicario_want(request: Request):
    """🎩 Sicario's PoW agreed on a coin: it asks for a free seat on the card, any of the 4. It is the same `want` a model files, so every seat guard still decides (fresh, seat on, night guard, gun line, desk picks only, refused coins, keeper precheck). Desk buys off stops it here. Internal key only; nothing is bought in this call."""
    rs = _rs()
    import hmac
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), rs._internal_key()):
        raise rs.HTTPException(403, 'Internal endpoint.')
    b = await request.json(); mint = str(b.get('mint') or ''); now = rs.time.time()
    if not mint or not b.get('pair'):
        return {'ok': False, 'why': 'no coin to send'}
    card = rs._real_card({}) or {}; pol = rs._oe.policy(rs._prime.clean_cfg(((rs._json_load(rs.FUSE_HQ_PATH, {}) or {}).get('prime') or {}).get('realCfg') or {}))
    if pol.get('aiSeat') != 'real':
        return {'ok': False, 'why': 'the model seats are off on the card'}
    no_ = rs._seat.sicario_refusal(rs._g4.get('want'), card.get('legs'), pol['seats'], mint, now)
    if no_:
        return {'ok': False, 'why': no_}
    rs._g4['want'] = {'action': 'BUY', 'source': 'sicario', 'mint': mint, 'pair': b.get('pair'), 'symbol': b.get('symbol'), 'why': str(b.get('why') or '')[:110], 'by': 'local', 'model': "Sicario's PoW", 'tp': b.get('tp'), 'sl': b.get('sl'), 'at': now}
    return {'ok': True}


@router.post('/api/reputation/fuses/best3')
async def fuse_best3(p: _RSM.FuseLiteIn):
    """Traders' one button: the best 3-pool basket for this budget, bred with the strategy that has PROVEN itself in the
    paper arena (else yield). Cached 2 min per budget bucket so it stays cheap."""
    rs = _rs()
    bucket = 5 if p.budgetUsd < 12 else 20 if p.budgetUsd < 60 else 100
    hit = rs._fuse_lite_cache.get(bucket)
    if hit and rs.time.time() - hit[0] < 120 and not p.again and not p.avoid:
        return hit[1]
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    style = rs._hq.best_style(rs._hq.arena_board([rs._hq.arena_value(e, {}, rs.time.time()) for e in d.get('arena') or []]))
    raw = await rs._fuse_discover_pairs('solana')
    cands = {}
    for lens in rs._fuse.LENSES:
        for r in rs._fuse.discover(raw, lens, 'solana', now_ms=rs.time.time() * 1000, limit=12):
            cands.setdefault(r['pairAddress'], r)
    metas = dict(list(cands.items())[:40])
    seed = int(rs.time.time() // 120) + bucket * 7919 + p.again   # each budget breeds its own random basket, 'Breed again' a new one
    if p.again or p.avoid:
        taken = set(p.avoid)
        fresh_ = {k: v for k, v in metas.items() if v.get('baseAddress') not in taken}
        if len(fresh_) >= 8:
            metas = fresh_
        keys_ = sorted(metas)
        rs.random.Random(seed).shuffle(keys_)
        metas = {k: metas[k] for k in keys_[:max(8, int(len(keys_) * 0.6))]}   # a random 60% of the pools: no two breeds start alike
    sol_usd = await rs._sol_usd_live()
    ev = await rs.asyncio.to_thread(rs._fuse.evolve, metas, 3, 14, 28, style, bucket / sol_usd, sol_usd, seed)
    c = ev['champions'][0] if ev['champions'] else None
    out = {'style': style, 'solUsd': sol_usd, 'proven': style != 'yield' or any(r['style'] == 'yield' and r['runs'] >= rs._hq.MIN_SETTLED for r in rs._hq.arena_board([rs._hq.arena_value(e, {}, rs.time.time()) for e in d.get('arena') or []])),
           'champion': c and rs._champ_view(c, metas)}
    if not p.again and not p.avoid:
        rs._fuse_lite_cache[bucket] = (rs.time.time(), out)
    return out


@router.post('/api/reputation/quests/checkin')
async def quest_checkin(payload: _RSM.QuestCheckin):
    rs = _rs()
    me = rs._session_or_401(payload.address, payload.session)
    day = rs.time.strftime('%Y-%m-%d', rs.time.gmtime())
    now_ = rs.time.time()
    st = rs._qs().update(me, lambda cur: {**(cur or {'days': [], 'first': now_}), 'checkinAt': (((cur or {}).get('checkinAt') or []) + [now_])[-60:]})   # Bot shield: clockwork / batch engines
    if (await rs._shield_of(me))['verdict'] == 'bot':   # bots don't earn daily rewards
        return {'ok': True, 'fresh': False, 'streak': rs._streak(st.get('days') or []), 'days': len(st.get('days') or []), 'shield': 'bot'}
    fresh = day not in (st.get('days') or [])
    if fresh:   # one transaction per wallet: two workers checking two wallets in never wipe each other (SITE-8)
        st = rs._qs().update(me, lambda cur: {**cur, 'days': ((cur.get('days') or []) + ([day] if day not in (cur.get('days') or []) else []))[-400:]})
    rs._quest_cache.pop(me, None); rs._badge_cache.pop(me, None)
    return {'ok': True, 'fresh': fresh, 'streak': rs._streak(st.get('days') or []), 'days': len(st.get('days') or [])}


@router.post('/api/reputation/quests/event')
async def quest_event(payload: _RSM.QuestEvent):
    """Tool quests. case_open: one per wallet looked at per day (max 30/day). warroom_trade: only a signature that is
    already one of YOUR verified FEELESS trades counts, once."""
    rs = _rs()
    me = rs._session_or_401(payload.address, payload.session)
    if payload.kind not in ('case_open', 'warroom_trade') or not payload.ref:
        raise rs.HTTPException(400, 'Unknown quest event.')
    if payload.kind == 'warroom_trade':
        mine = set(rs.linked_of(me)) | {me}
        if not any(x.get('tx') == payload.ref for w, rows in rs._json_load(rs.FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or []):
            raise rs.HTTPException(400, 'That trade is not a confirmed FEELESS trade from your wallet (yet).')
    now = rs.time.time(); day = rs.time.strftime('%Y-%m-%d', rs.time.gmtime(now))
    import sql_store as _sqls
    key = f'{payload.kind}:{payload.ref}' + (f':{day}' if payload.kind == 'case_open' else '')

    def ev_(cur):   # one transaction: the count and the dedupe can't race across workers (SITE-8)
        st = cur or {'days': [], 'first': now}
        ev = st.setdefault('events', {}); refs = st.setdefault('eventRefs', {})
        today = sum(1 for x in ev.get(payload.kind, []) if x >= now // 86400 * 86400)
        ok_ = key not in refs and not (payload.kind == 'case_open' and today >= 30)
        if ok_:
            ev.setdefault(payload.kind, []).append(now); ev[payload.kind] = ev[payload.kind][-2000:]
            refs[key] = now
            if len(refs) > 4000:
                st['eventRefs'] = dict(sorted(refs.items(), key=lambda kv: kv[1])[-3000:])
        return _sqls.Result(st, ok_)
    counted = rs._qs().update(me, ev_)
    rs._quest_cache.pop(me, None)
    return {'ok': True, 'counted': counted}


@router.post('/api/reputation/bugs')
async def report_bug(request: Request, payload: _RSM.BugReport):
    rs = _rs()
    if not await rs._ip_hit(rs._bug_ip_hits, request, 3, 60):
        raise rs.HTTPException(429, 'Slow down — 3 reports a minute.')
    kind = payload.kind if payload.kind in ('bug', 'security', 'idea') else 'bug'
    async with rs._admin_lock:
        d = rs._json_load(rs.BUGS_PATH, {'bugs': []})
        key = rs._bug_key(payload.text, payload.page)
        same = next((b for b in reversed(d['bugs']) if b.get('status', 'open') == 'open' and rs._bug_key(b['text'], b.get('page', '')) == key), None)
        if same:   # the same crash on the same page is ONE report with a count, never 33 rows
            same['count'] = int(same.get('count') or 1) + 1; same['lastAt'] = rs.time.time()
            rs._json_save(rs.BUGS_PATH, d)
            return {'ok': True, 'merged': True}
        d['bugs'].append({'id': rs.uuid.uuid4().hex[:10], 'text': payload.text.strip(), 'page': payload.page, 'kind': kind,
                          'address': (payload.address or '')[:44] or None, 'status': 'open', 'at': rs.time.time(), 'count': 1})
        d['bugs'] = d['bugs'][-1000:]
        rs._json_save(rs.BUGS_PATH, d)
    return {'ok': True}


@router.post('/api/reputation/support')
async def support_act(p: _RSM.SupportAct):
    """🛟 Signed wallet only: +1 a report · propose a poll (≤ 3 a day) · vote on one. One wallet, one mark."""
    rs = _rs()
    import support as _sp
    w_ = rs._session_or_401(p.wallet, p.session)
    async with rs._admin_lock:
        st_ = rs._json_load(rs.SUPPORT_PATH, {'polls': [], 'plus': {}})
        card_ids_ = lambda: ({b_.get('id') for b_ in rs._json_load(rs.BUGS_PATH, {'bugs': []}).get('bugs') or []} | {x_.get('id') for x_ in st_.get('polls') or []} | {x_.get('id') for x_ in st_.get('ideas') or []})
        if p.react:
            if p.react not in card_ids_() or p.v not in (1, -1):
                raise rs.HTTPException(400, 'No such card.')
            r_ = st_.setdefault('reacts', {}).setdefault(p.react, {})
            if r_.get(w_) == p.v:
                r_.pop(w_, None)
            else:
                r_[w_] = p.v
        elif p.comment:
            t_ = ' '.join(str(p.text or '').split())[:280]
            if p.comment not in card_ids_() or len(t_) < 2:
                raise rs.HTTPException(400, 'Say something (2–280 characters) on a real card.')
            st_.setdefault('comments', {}).setdefault(p.comment, []).append({'by': w_, 'text': t_, 'at': rs.time.time()})
            st_['comments'][p.comment] = st_['comments'][p.comment][-50:]
        elif p.idea:
            t_ = ' '.join(str(p.text or '').split())[:280]
            if len(t_) < 8:
                raise rs.HTTPException(400, 'An idea needs at least a short sentence.')
            if sum(1 for i_ in st_.get('ideas') or [] if i_.get('by') == w_ and rs.time.time() - i_.get('at', 0) < 86400) >= 5:
                raise rs.HTTPException(429, '5 ideas a day — try again tomorrow.')
            st_.setdefault('ideas', []).append({'id': 'i' + rs.uuid.uuid4().hex[:9], 'text': t_, 'by': w_, 'at': rs.time.time()})
            st_['ideas'] = st_['ideas'][-300:]
        elif p.plus:
            ids_ = {b_.get('id') for b_ in rs._json_load(rs.BUGS_PATH, {'bugs': []}).get('bugs') or []}
            if p.plus not in ids_:
                raise rs.HTTPException(404, 'No such report.')
            lst_ = st_.setdefault('plus', {}).setdefault(p.plus, [])
            lst_.remove(w_) if w_ in lst_ else lst_.append(w_)
        elif p.q is not None:
            if not _sp.can_post(st_.get('polls'), w_):
                raise rs.HTTPException(429, f'{_sp.POLL_DAY_MAX} polls a day — try again tomorrow.')
            try:
                q_, opts_ = _sp.clean_poll(p.q, p.options or [])
            except ValueError as e_:
                raise rs.HTTPException(400, str(e_))
            st_.setdefault('polls', []).append({'id': rs.uuid.uuid4().hex[:10], 'q': q_, 'options': opts_, 'votes': {}, 'by': w_, 'at': rs.time.time()})
            st_['polls'] = st_['polls'][-300:]
        elif p.poll:
            pl_ = next((x_ for x_ in st_.get('polls') or [] if x_.get('id') == p.poll), None)
            if not pl_:
                raise rs.HTTPException(404, 'No such poll.')
            if pl_.get('status') in _sp.OWNER_STATES:
                raise rs.HTTPException(400, 'This poll is decided.')
            try:
                _sp.vote(pl_, w_, int(p.opt if p.opt is not None else -1))
            except ValueError as e_:
                raise rs.HTTPException(400, str(e_))
        else:
            raise rs.HTTPException(400, 'Nothing to do.')
        rs._json_save(rs.SUPPORT_PATH, st_)
    return await rs.support_board(w_)


@router.post('/api/reputation/presence')
async def presence_beat(p: _RSM.PresenceBeat):
    """🟢 A signed-in tab's heartbeat with its chosen mode (online · away · invisible). Memory only."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    return {'mode': rs._pres.beat(rs._presence, me, p.mode, rs.time.time()), 'every': rs._pres.BEAT_SEC}


@router.post('/api/reputation/familia/street/{city}/typing')
async def familia_street_typing(city: str, p: _RSM.StreetTyping):
    """✍ A signed-in wallet is typing on this street (the client beats at most every 3 s while the box has text). Memory only."""
    rs = _rs()
    if not rs._stc.room_of(city):
        raise rs.HTTPException(400, 'No such city.')
    me_ = rs.primary_of(rs._session_or_401(p.address, p.session))
    rs._stc.typing_beat(rs._street_typing, city, me_, rs.time.time())
    return {'ok': True}


@router.post('/api/reputation/legal/accept')
async def legal_accept(p: _RSM.LegalAccept, request: Request):
    """The wallet states 18+, not sanctioned / not restricted, and its country — stored per wallet with this terms version."""
    rs = _rs()
    me = rs._legal_me(p.wallet, p.session)
    try:
        row = rs._legal.accept(rs._legal_s(), me, p.version, p.country, p.adult, p.notRestricted, ip_country=rs._legal.country_of(request.headers))
    except ValueError as e:
        raise rs.HTTPException(400, str(e))
    rs._legal_save()
    return {'ok': True, 'version': row['v'], 'country': row['country']}


@router.post('/api/reputation/legal/export')
async def legal_export(p: _RSM.LegalMine):
    """Everything FEELESS holds off-chain for this wallet, as one JSON file (tokens / sealed secrets / push keys scrubbed)."""
    rs = _rs()
    me = rs._legal_me(p.wallet, p.session)
    parts = rs._legal_parts(me)
    bundle = rs._legal.export_bundle(me, parts)
    rs._legal.note_request(rs._legal_s(), me, 'export', {k: (len(v) if isinstance(v, (list, dict)) else 1) for k, v in bundle['data'].items()})
    rs._legal_save()
    return bundle


@router.post('/api/reputation/clicks')
async def track_click(request: Request, payload: _RSM.ClickIn):
    rs = _rs()
    if payload.kind not in ('ticker', 'ca', 'mention', 'command'):
        raise rs.HTTPException(400, 'Bad kind.')
    if not await rs._ip_hit(rs._click_ip, request, 60, 60):
        raise rs.HTTPException(429, 'Too many clicks.')
    value = payload.value.strip()
    if payload.kind == 'ticker':
        value = value.upper().lstrip('$')[:12]
    async with rs._admin_lock:
        d = rs._json_load(rs.CLICKS_PATH, {})
        key = f'{payload.kind}:{value}'
        if key not in d and len(d) >= rs.CLICKS_MAX:   # 🔒 audit #8: the click map never grows past CLICKS_MAX keys
            return {'ok': False, 'count': 0}
        rec = d.get(key) or [0, 0, 0]  # [total, last-at, 24h-bucket-start]
        rec[0] += 1
        rec[1] = rs.time.time()
        d[key] = rec
        rs._json_save(rs.CLICKS_PATH, d)
    return {'ok': True, 'count': rec[0]}


@router.post('/api/reputation/identity/link')
async def identity_link(payload: _RSM.LinkIn):
    rs = _rs()
    cats = rs._json_load(rs.DATA_DIR / 'feecats.json', {}).get('cats', {})
    if any((c.get('agentWallet') or {}).get('address') == payload.solana for c in cats.values()):
        raise rs.HTTPException(403, 'FeeCat wallets cannot sign in to FEELESS.')
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', payload.solana) or not rs._re.match(r'^0x[0-9a-fA-F]{40}$', payload.evm):
        raise rs.HTTPException(400, 'Need one Solana and one 0x address.')
    if abs(rs.time.time() - payload.ts) > 300:
        raise rs.HTTPException(401, 'Link expired — try again.')
    msg = f'FEELESS link wallets\nsolana:{payload.solana}\nevm:{payload.evm}\nts:{payload.ts}'
    if not rs._verify_solana(payload.solana, msg, payload.solanaSig) or not rs._verify_evm(payload.evm, msg, payload.evmSig):
        raise rs.HTTPException(401, 'Both accounts must sign the link.')
    async with rs._admin_lock:
        d = rs._ids()
        d['links'][payload.evm] = {'primary': payload.solana, 'at': rs.time.time()}
        d['links'][payload.solana] = {'primary': payload.solana, 'at': rs.time.time()}
        rs._json_save(rs.IDENTITY_PATH, d)
    rs._badge_cache.pop(payload.evm, None); rs._perk_cache.pop(payload.evm, None)
    return {'ok': True, 'primary': payload.solana, 'linked': rs.linked_of(payload.solana)}


@router.post('/api/reputation/chat/delete')
async def chat_delete(payload: _RSM.ChatDelete):
    """Posts can only be deleted on profile walls: by the wall owner (any network they've linked) or by the poster."""
    rs = _rs()
    m = rs._re.match(r'^wall-(.+)$', payload.room)
    if not m:
        raise rs.HTTPException(403, 'Posts can only be deleted on profile walls.')
    if abs(rs.time.time() - payload.ts) > 120:
        raise rs.HTTPException(401, 'Signature expired.')
    if payload.session:
        if rs.primary_of(rs.session_address(payload.session) or "") != rs.primary_of(payload.address) or not rs.session_address(payload.session):
            raise rs.HTTPException(401, 'Chat session expired.')
    elif not rs._verify_wallet(payload.address, f'FEELESS delete\nroom:{payload.room}\nid:{payload.id}\nts:{payload.ts}', payload.signature):
        raise rs.HTTPException(401, 'Signature does not match this wallet.')
    me = set(rs.linked_of(payload.address))
    async with rs._chat_lock:
        d = rs._chat_load()
        msgs = d['rooms'].get(payload.room, [])
        msg = next((x for x in msgs if x['id'] == payload.id), None)
        if not msg:
            raise rs.HTTPException(404, 'Post not found.')
        if rs.primary_of(m.group(1)) not in me and msg.get('address') not in me:
            raise rs.HTTPException(403, 'Only the wall owner or the poster can delete this.')
        d['rooms'][payload.room] = [x for x in msgs if x['id'] != payload.id]
        rs.CHAT_PATH.write_text(rs.json.dumps(d))
    return {'ok': True}


@router.post('/api/reputation/fuses/rounds')
async def fuse_rounds(p: _RSM.RoundsIn):
    rs = _rs()
    held = bool(p.signature) and p.mode in ('pay', 'settle')
    if held and rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', p.signature or ''):
        await rs._pay_hold(p.signature)
    try:
        return await rs._fuse_rounds(p)
    except BaseException:
        rs._PAY_HELD.discard(p.signature or ''); raise


@router.post('/api/reputation/chat/session')
async def chat_session(payload: _RSM.SessionIn):
    rs = _rs()
    cats = rs._json_load(rs.DATA_DIR / 'feecats.json', {}).get('cats', {})
    if any((c.get('agentWallet') or {}).get('address') == payload.address for c in cats.values()):
        raise rs.HTTPException(403, 'FeeCat wallets cannot sign in to FEELESS.')
    if abs(rs.time.time() - payload.ts) > 300:
        raise rs.HTTPException(401, 'Signature expired — try again.')
    if not rs._verify_wallet(payload.address, f'FEELESS chat session\naddress:{payload.address}\nts:{payload.ts}', payload.signature):
        raise rs.HTTPException(401, 'Signature does not match this wallet.')
    token = rs._secrets.token_urlsafe(32)
    async with rs._admin_lock:
        d = rs._sess()
        now = rs.time.time()
        d['s'] = {k: v for k, v in d['s'].items() if v['exp'] > now}
        d['s'][rs.hashlib.sha256(token.encode()).hexdigest()] = {'address': payload.address, 'exp': now + rs.SESSION_TTL}
        rs._json_save(rs.SESSIONS_PATH, d)
    return {'token': token, 'expiresAt': rs.time.time() + rs.SESSION_TTL}


@router.post('/api/reputation/referral')
async def claim_referral(payload: _RSM.RefIn):
    """Credit the inviter once. Proof of wallet ownership = the invitee's signed chat session."""
    rs = _rs()
    if rs.primary_of(rs.session_address(payload.session) or "") != rs.primary_of(payload.address) or not rs.session_address(payload.session):
        raise rs.HTTPException(401, 'Sign in to chat first.')
    inviter = rs._code_owner(payload.ref)
    if not inviter:
        try:
            inviter = (await rs.resolve_profile(payload.ref))['address']
        except rs.HTTPException:
            raise rs.HTTPException(404, 'Unknown invite code.')
    me = rs.primary_of(payload.address)
    if inviter == me:
        raise rs.HTTPException(400, "You can't invite yourself.")
    async with rs._admin_lock:
        d = rs._json_load(rs.REF_PATH, {'by': {}, 'of': {}})
        if me in d['of']:
            return {'ok': True, 'already': True, 'inviter': d['of'][me]}
        d['of'][me] = inviter
        d['by'].setdefault(inviter, []).append({'address': me, 'at': rs.time.time()})
        rs._json_save(rs.REF_PATH, d)
    rs._badge_cache.pop(inviter, None)
    rs.notify(inviter, 'invite', f'@{rs.handle_of(me)} joined with your invite link — claim +75 points.', f'/terminal/profile/{inviter}', me)
    return {'ok': True, 'inviter': inviter}


@router.post('/api/reputation/ads/{ad_id}/event')
async def ad_event(ad_id: str, request: Request, kind: str = Query('view')):
    rs = _rs()
    if kind not in ('view', 'click'):
        raise rs.HTTPException(400, 'Bad event.')
    # 🔒 audit #8: a real ad id only, 60 events/min per device, and the file is rewritten only when an ad was counted
    if not rs._re.fullmatch(r'[A-Za-z0-9_-]{1,40}', ad_id) or not any(a.get('id') == ad_id for a in rs._json_load(rs.ADS_PATH, {'ads': []})['ads']):
        return {'ok': False}
    if not await rs._ip_hit(rs._ad_ev_ip, request, 60, 60):
        raise rs.HTTPException(429, 'Too many ad events.')
    async with rs._admin_lock:
        d = rs._json_load(rs.ADS_PATH, {'ads': []})
        hit = False
        for a in d['ads']:
            if a['id'] == ad_id:
                a[kind + 's'] = a.get(kind + 's', 0) + 1; hit = True
        if hit:
            rs._json_save(rs.ADS_PATH, d)
    return {'ok': hit}


@router.post('/api/reputation/notifications/read')
async def notifications_read(payload: dict):
    rs = _rs()
    me = rs._session_or_401(payload.get('address', ''), payload.get('session', ''))
    rs._notif().update(me, lambda box: [{**n, 'read': True} for n in box] if box else None)
    return {'ok': True}


@router.post('/api/reputation/dm-settings')
async def dm_settings_set(payload: _RSM.DmPrefsIn):
    rs = _rs()
    me = rs._session_or_401(payload.address, payload.session)
    if payload.policy and payload.policy not in rs.DM_POLICIES:
        raise rs.HTTPException(400, 'Unknown message setting.')
    async with rs._admin_lock:
        d = rs._json_load(rs.DM_PREFS_PATH, {}); cur = {**rs._dm_pref(me), **(d.get(me) or {})}
        if payload.policy:
            cur['policy'] = payload.policy
        if payload.accept:
            cur['accepted'] = sorted(set(cur.get('accepted', [])) | {rs.primary_of(payload.accept)})[-500:]
        d[me] = cur; rs._json_save(rs.DM_PREFS_PATH, d)
    return rs._dm_pref(me)


@router.post('/api/reputation/rewards/claim')
async def rewards_claim(payload: _RSM.ClaimIn):
    rs = _rs()
    me = rs._session_or_401(payload.address, payload.session)
    async with rs._admin_lock:
        rec, items, ctx = await rs._reward_state(me)
        it = next((i for i in items if i['id'] == payload.reward), None)
        if not it or not it['claimable']:
            raise rs.HTTPException(400, 'Nothing to claim for that yet.')
        d = rs._pts()
        rec = d.get(me) or rec
        day = ctx['day']
        if it['id'] == 'daily':
            yesterday = rs.time.strftime('%Y-%m-%d', rs.time.gmtime(rs.time.time() - 86400))
            rec['streak'] = rec.get('streak', 0) + 1 if rec['claims'].get('daily') == yesterday else 1
        rec['claims'][it['id']] = ctx['hits'] if it['id'] == 'call-hit' else ctx['invited'] if it['id'] == 'invite' else day if it['id'] in ('daily', 'post', 'fee-holder') else True
        rec['total'] = rec.get('total', 0) + it['amount']
        rec.setdefault('log', []).insert(0, {'id': it['id'], 'label': it['label'], 'points': it['amount'], 'at': rs.time.time()})
        try:
            rs.season_award(me, it['amount'], it['id'])
        except Exception:
            pass
        rec['log'] = rec['log'][:100]
        d[me] = rec
        rs._json_save(rs.POINTS_PATH, d)
    return {'ok': True, 'gained': it['amount'], 'total': rec['total'], 'streak': rec.get('streak', 0)}


@router.post('/api/reputation/wars/join')
async def wars_join(payload: _RSM.JoinIn):
    rs = _rs()
    me = rs._session_or_401(payload.address, payload.session)
    if payload.faction not in rs.FACTIONS:
        raise rs.HTTPException(400, 'Pick bulls, bears or degens.')
    async with rs._admin_lock:
        d = rs._json_load(rs.WARS_PATH, {})
        wk = d.setdefault(rs._war_week(), {'members': {}})
        if me in wk['members']:
            raise rs.HTTPException(400, f"You're already fighting for {rs.FACTIONS[wk['members'][me]]} this week.")
        wk['members'][me] = payload.faction
        rs._json_save(rs.WARS_PATH, d)
    return {'ok': True, 'faction': payload.faction}


@router.post('/api/reputation/follow')
async def follow(payload: _RSM.FollowIn):
    rs = _rs()
    me = rs._session_or_401(payload.address, payload.session)
    t = rs.primary_of(payload.target)
    if t == me or not rs._re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', t):
        raise rs.HTTPException(400, "Can't follow that.")
    async with rs._admin_lock:
        d = rs._fol()
        lst = d['following'].setdefault(me, [])
        if payload.follow and t not in lst:
            lst.append(t); d['following'][me] = lst[-2000:]
            rs.notify(t, 'follow', f'@{rs.handle_of(me)} started following you', f'/terminal/profile/{me}', me)
        elif not payload.follow and t in lst:
            lst.remove(t)
        rs._json_save(rs.FOLLOW_PATH, d)
    return {'ok': True, 'following': payload.follow}


@router.post('/api/reputation/edge/observe')
async def edge_observe(o: _RSM.EdgeObservation, request: Request):
    rs = _rs()
    import re
    if not await rs._ip_hit(rs._edge_ip, request, 120, 3600):   # 🔒 audit #8: one device can't pin hundreds of coins' predictions
        raise rs.HTTPException(429, 'Too many observations from here.')
    if not (0 <= o.score <= 100) or o.priceUsd <= 0 or len(o.pairAddress) > 80 or len(o.chain) > 24 or not re.fullmatch(r'[A-Za-z0-9]+', o.pairAddress) or not re.fullmatch(r'[a-z0-9-]+', o.chain):
        raise rs.HTTPException(400, 'bad observation')
    if o.chain == 'solana':   # the live price read covers Solana; other chains keep their score only until they have one
        try:
            async with rs.httpx.AsyncClient(timeout=4) as http_:
                live_ = rs._num_or_0(((await http_.get(f'http://127.0.0.1:5099/api/candles/price/solana/{o.pairAddress}')).json() or {}).get('p'))
        except (rs.httpx.HTTPError, ValueError):
            live_ = 0.0
        if not rs._edge_price_ok(o.priceUsd, live_):
            return {'ok': False, 'why': 'no matching live price'}
    async with rs._edge_lock:
        d = rs._json_load(rs.EDGE_MEM_PATH, {'open': {}, 'done': []})
        key = f'{o.chain}:{o.pairAddress}'
        prev = d['open'].get(key)
        if prev and rs.time.time() - prev['at'] < 6 * 3600:  # one open prediction per coin per 6h
            return {'ok': True, 'dedup': True}
        d['open'][key] = {'chain': o.chain, 'pair': o.pairAddress, 'grade': rs._edge_grade(o.score), 'score': round(o.score, 1),
                          'price': o.priceUsd, 'peak': o.priceUsd, 'low': o.priceUsd, 'at': rs.time.time()}
        if len(d['open']) > 5000:  # hard cap: drop the oldest
            for k in sorted(d['open'], key=lambda k: d['open'][k]['at'])[:len(d['open']) - 5000]:
                d['open'].pop(k)
        rs._json_save(rs.EDGE_MEM_PATH, d)
    return {'ok': True}


@router.post('/api/reputation/pv')
async def page_view(request: Request, p: _RSM.PageView):
    rs = _rs()
    ip = rs._guard.request_ip(request).strip()
    now = rs.time.time()
    if not await rs._ip_hit(rs._tr_ip, request, 120, 60):
        return {'ok': False}
    day = rs.time.strftime('%Y-%m-%d', rs.time.gmtime(now))
    if rs._tr_salt['day'] != day:
        rs._tr_salt.update(day=day, salt=rs._secrets.token_hex(16))
    who = rs._hashlib.sha256(f"{rs._tr_salt['salt']}{ip}".encode()).hexdigest()[:16]
    path = rs._re.sub(r'[^a-zA-Z0-9/_-]', '', p.path.split('?')[0])[:80] or '/'
    page = rs._re.sub(r'/(profile|coin)/[^/]+', r'/\1/:id', path)
    b = rs._tr_buf
    cap_ = lambda m_, k_: k_ in m_ or len(m_) < rs.TR_MAP_MAX   # 🔒 audit #8: request-made keys never grow a map past TR_MAP_MAX
    b['views'].setdefault(day, {})
    if cap_(b['views'][day], page):
        b['views'][day][page] = b['views'][day].get(page, 0) + 1
    b['uniq'].setdefault(day, set()).add(who)
    m = rs._re.search(r'[?&]pair=([A-Za-z0-9]+)', p.path) or rs._re.search(r'coin=([a-z]+):([A-Za-z0-9]+)', p.path)
    if m:
        key = m.group(m.lastindex)[:64]
        if cap_(b['coins'], key):
            b['coins'][key] = b['coins'].get(key, 0) + 1
    host = (rs._re.match(r'https?://([^/]+)', p.ref or '') or [None, None])[1]
    if host and 'localhost' not in host and cap_(b['refs'], host[:80]):
        b['refs'][host[:80]] = b['refs'].get(host[:80], 0) + 1
    h = rs.time.gmtime(now).tm_hour
    b['hours'][h] = b['hours'].get(h, 0) + 1
    return {'ok': True}


@router.post('/api/reputation/shield')
async def shield_commit(p: _RSM.ShieldPayload):
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.mint):
        raise rs.HTTPException(400, 'Solana mint address required.')
    if not (50 <= p.devKeepPct <= 100 and 7 <= p.lockDays <= 365 and 0.5 <= p.maxWalletPct <= 20):
        raise rs.HTTPException(400, 'Shield terms out of range (keep 50–100%, lock 7–365 days, max wallet 0.5–20%).')
    d = rs._json_load(rs.SHIELD_PATH, {})
    if p.mint in d:
        raise rs.HTTPException(409, 'This coin already has a Shield — promises can’t be rewritten.')
    try:
        data = await rs._token_holders(p.mint)
        mine = sum((r['pct'] or 0) for r in data['rows'] if r['owner'] == me)
    except Exception:
        mine = None
    d[p.mint] = {'creator': me, 'devKeepPct': p.devKeepPct, 'lockDays': p.lockDays, 'maxWalletPct': p.maxWalletPct,
                 'noKnownSnipers': p.noKnownSnipers, 'devStartPct': mine, 'at': rs.time.time(), 'breaches': []}
    rs._json_save(rs.SHIELD_PATH, d)
    return {'ok': True, 'shield': d[p.mint]}


@router.post('/api/reputation/agent-pass/{cat_id}/prepare')
async def agent_pass_prepare(cat_id: str, p: _RSM.AgentPassIn):
    """🎫 Its number + its metadata (hosted with coin launches' token-meta). Only its owner, only after its recovery PIN is confirmed, once."""
    rs = _rs()
    rs._session_or_401(p.address, p.session)
    cat = await rs._owned_cat(cat_id, p.address)
    if not cat.get('recoveryConfirmedAt'):
        raise rs.HTTPException(400, 'Confirm its recovery PIN first — the Pass comes after its safe-keeping.')
    if (cat.get('pass') or {}).get('asset'):
        raise rs.HTTPException(409, f"It already has Pass #{cat['pass'].get('number')}.")
    rules = await rs._agent_pass_rules()
    if not rules['ready']:
        raise rs.HTTPException(503, rules['why'])
    if not rs._re.match(r'^/api/reputation/uploads/[A-Za-z0-9._-]{1,80}$', p.image or ''):
        raise rs.HTTPException(400, 'Its picture did not upload — try again.')
    book = rs._json_load(rs.APASS_FILE, {}) or {}
    num = (book.get('byCat') or {}).get(cat_id, {}).get('number') or int(book.get('next') or 1)
    site = rs._pass_site()
    meta = rs._apass.metadata(site, cat, num, site + p.image)
    rs.TOKEN_META_DIR.mkdir(parents=True, exist_ok=True)
    mid = rs.uuid.uuid4().hex
    (rs.TOKEN_META_DIR / f'{mid}.json').write_text(rs.json.dumps(meta))
    if cat_id not in (book.get('byCat') or {}):
        book.setdefault('byCat', {})[cat_id] = {'number': num, 'at': round(rs.time.time())}; book['next'] = num + 1
        rs._json_save(rs.APASS_FILE, book)
    return {'number': num, 'name': meta['name'], 'uri': f'{site}/api/reputation/token-meta/{mid}.json', 'feeWallet': rules['feeWallet'],
            'feeLamports': rules['feeLamports'], 'royaltyBps': rules['royaltyBps']}


@router.post('/api/reputation/agent-pass/{cat_id}/confirm')
async def agent_pass_confirm(cat_id: str, p: _RSM.AgentPassIn):
    """🎫 Records a Pass only after checking its transaction on-chain (owner signed · fee reached FEELESS · a Core asset · no error)."""
    rs = _rs()
    rs._session_or_401(p.address, p.session)
    await rs._owned_cat(cat_id, p.address)   # ownership check: raises when it is not theirs
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{60,100}$', p.signature or '') or not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.asset or ''):
        raise rs.HTTPException(400, 'Not a transaction / asset.')
    rules = await rs._agent_pass_rules()
    async with rs.httpx.AsyncClient(timeout=15) as http:
        tx = await rs._rpc(http, 'getTransaction', [p.signature, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
    why = rs._apass.check_mint(tx, p.address, rules['feeWallet'], rules['feeLamports'], p.asset)
    if why:
        raise rs.HTTPException(400, why)
    rs._cpool.update(rs.POOL_PATH, lambda st: rs._cpool.income(st, f'pass:{p.signature}', 'SOL', rules['feeLamports'], 'pass'))
    num = ((rs._json_load(rs.APASS_FILE, {}) or {}).get('byCat') or {}).get(cat_id, {}).get('number')
    r = await rs._ai_http().post(f'http://127.0.0.1:5088/api/cats/{cat_id}/action', headers={'x-feeless-internal': rs._internal_key()}, timeout=8,
                              json={'action': 'pass_minted', 'passInfo': {'number': num, 'asset': p.asset, 'sig': p.signature, 'owner': p.address}})
    if r.status_code != 200:
        raise rs.HTTPException(502, 'The Pass is minted, but its agent did not record it — confirm again in a minute.')
    return {'ok': True, 'number': num, 'asset': p.asset}


@router.post('/api/reputation/token-meta')
async def token_meta_create(p: _RSM.TokenMetaIn, request: Request):
    """Hosts the Metaplex metadata JSON a new coin's `uri` points to (name, image, links)."""
    rs = _rs()
    rs._session_or_401(p.address, p.session)
    name, symbol = p.name.strip()[:32], p.symbol.strip().upper()[:10]
    if not name or not rs._re.match(r'^[A-Z0-9$]{1,10}$', symbol):
        raise rs.HTTPException(400, 'Name and a 1–10 character ticker are required.')
    site = rs.os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/') or (request.headers.get('origin') or '').rstrip('/')
    # FEELESS-rail coins are minted with IMMUTABLE metadata: a localhost/LAN uri would leave the coin
    # nameless and imageless forever, so refuse anything that isn't a public https address.
    host = rs._re.sub(r'^https?://', '', site).split('/')[0].split(':')[0]
    if not site.startswith('https://') or host in ('localhost', '127.0.0.1', '0.0.0.0') or host.endswith('.local') or rs._re.match(r'^(10|192\.168|172\.(1[6-9]|2\d|3[01]))\.', host):
        raise rs.HTTPException(503, 'FEELESS launches need a public https domain (set PUBLIC_SITE_URL). Coin metadata is permanent, so a local address would break the coin forever. Pump.fun launches work now.')
    meta = rs.launch_meta.token_metadata(site, name, symbol, p.description, p.image, p.banner, p.website, p.twitter, p.telegram)
    rs.TOKEN_META_DIR.mkdir(parents=True, exist_ok=True)
    mid = rs.uuid.uuid4().hex
    (rs.TOKEN_META_DIR / f'{mid}.json').write_text(rs.json.dumps(meta))
    return {'uri': f'{site}/api/reputation/token-meta/{mid}.json'}


@router.post('/api/reputation/rpc')
async def rpc_relay(request: Request):
    rs = _rs()
    if not await rs._ip_hit(rs._rpc_hits, request, 60, 10):
        raise rs.HTTPException(429, 'Too many RPC calls.')
    body = await request.json()
    calls = body if isinstance(body, list) else [body]
    if len(calls) > 10 or any(not rs._rpc_call_ok(c) for c in calls):
        raise rs.HTTPException(403, 'RPC method not allowed.')
    endpoint = rs._dedicated or rs._next_rpc_endpoint()
    async with rs.httpx.AsyncClient(timeout=20) as http:
        r = await http.post(endpoint, json=body)
        # 🚑 2026-10-23: the dedicated key ran out of monthly quota and EVERY wallet action (swaps, Jupiter Lend, LP joins, launches) died with it.
        # A spent / rate-limited answer now falls through the other keyed lanes, then the public nodes — the keeper's own public node last.
        if rs._relay_spent(r):
            for alt in [e for e in rs.RPC_POOL if e not in (endpoint, rs._KEEPER_PUBLIC)] + [rs._KEEPER_PUBLIC]:
                try:
                    r2 = await http.post(alt, json=body)
                except Exception:
                    continue
                if not rs._relay_spent(r2):
                    r = r2
                    break
    from fastapi.responses import Response
    return Response(r.content, status_code=r.status_code, media_type='application/json')


@router.post('/api/reputation/perf')
async def perf_report(p: _RSM.PerfIn):
    rs = _rs()
    api = {str(k)[:160]: [float(x) for x in v[:50] if isinstance(x, (int, float))] for k, v in list(p.api.items())[:40] if isinstance(v, list)}
    fx = {k: float(v) for k, v in list(p.fx.items())[:6] if k in ('running', 'paused', 'shed', 'pressure') and isinstance(v, (int, float))}
    er = {str(k)[:110]: int(v) for k, v in list(p.errRoutes.items())[:20] if isinstance(v, (int, float)) and 0 < v < 1000}
    lay = p.layout or {}
    lay = {'sideways': int(min(5000, max(0, rs._fuse._f(lay.get('sideways'))))), 'spills': [str(x)[:40] for x in (lay.get('spills') or [])[:5]],
           'covered': [str(x)[:40] for x in (lay.get('covered') or [])[:5]]} if isinstance(lay, dict) and lay else None
    rs._perf_samples.append({**p.dict(), 'api': api, 'fx': fx, 'errRoutes': er, 'layout': lay, 'at': rs.time.time()})
    return {'ok': True}


@router.post('/api/reputation/internal/trade')
async def internal_trade(request: Request, p: _RSM.TradeLanded):
    """Called by the trading service once a FEELESS trade is confirmed on-chain (idempotent per signature)."""
    rs = _rs()
    if not rs.hmac.compare_digest(request.headers.get('x-feeless-internal', ''), rs._internal_key()):
        raise rs.HTTPException(403, 'Internal only.')
    who = rs.primary_of(p.wallet)
    px = await rs._sol_usd() if p.feeAtoms and p.feeMint == rs.WSOL else 0
    eco = set((await rs._ecosystem_mints()).values())
    row = rs.fee_report.ledger_row(rs.time.time(), p.signature, p.inUsd, p.feeBps, p.feeAtoms, p.feeMint, px, feeback=bool(eco & {p.inputMint, p.outputMint}))
    # The trader's position row is saved on EVERY call (idempotent per tx) — before the points dedupe below, which once
    # skipped it and left a trade with no locked entry. A locked row is never replaced by a weaker (unlocked) one.
    stable_ = {rs.WSOL, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'}
    coin, amt, side_ = (p.outputMint, p.outAmount, 'buy') if p.inputMint in stable_ else (p.inputMint, p.inAmount, 'sell')
    rec = rs._trade_record(p, coin, amt, side_, await rs._sol_usd(), row.get('feeUsd')) if coin not in stable_ else None
    if rec:
        ft = rs._json_load(rs.FEELESS_TRADES_PATH, {})
        mine = ft.get(p.wallet) or []
        old = next((r for r in mine if r.get('tx') == p.signature), None)
        if not (old and old.get('locked') and not rec.get('locked')):
            ft[p.wallet] = ([r for r in mine if r.get('tx') != p.signature] + [rec])[-300:]
            rs._json_save(rs.FEELESS_TRADES_PATH, ft)
    d = rs._seasons(); seen = d.setdefault('tradeSigs', [])
    if p.signature in seen:
        return {'ok': True, 'points': 0, 'duplicate': True}
    pts = rs.trade_points(p.inUsd, p.feeBps)
    d['tradeSigs'] = (seen + [p.signature])[-5000:]
    rs._json_save(rs.SEASONS_PATH, d)
    led = rs._json_load(rs.FEE_LEDGER_PATH, {})
    led[who] = (led.get(who) or [])[-1999:] + [row]
    rs._json_save(rs.FEE_LEDGER_PATH, led)
    rs._json_save(rs.FEE_TOTALS_PATH, rs.fee_report.add_total(rs._json_load(rs.FEE_TOTALS_PATH, {}), who, row))   # lifetime, never trimmed
    inviter = rs._json_load(rs.REF_PATH, {'by': {}, 'of': {}})['of'].get(who)
    # The trade is confirmed on-chain (the trading service checked): tell the trader and refresh their holdings,
    # whether or not their browser is still open. Deduped with the receipt notification by signature.
    stable = {rs.WSOL, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'}
    side = 'Buy' if p.inputMint in stable and p.outputMint not in stable else 'Sell' if p.outputMint in stable else 'Swap'
    try:
        rs._pf_cache.pop(who, None); rs._badge_cache.pop(who, None)
        rs.notify(p.wallet, 'reward', f"✅ {side} confirmed on-chain" + (f" · ${p.inUsd:,.2f}" if p.inUsd else '') + (f" · +{pts:g} season pts" if pts > 0 else ''),
               f'https://solscan.io/tx/{p.signature}', once=f'tx:{p.signature}')
    except Exception:
        pass
    pct = float(rs._json_load(rs.REF_CFG_PATH, {}).get('pct') or 0)
    if inviter and pct > 0:
        rs._json_save(rs.REF_EARN_PATH, rs.fee_report.referral_credit(rs._json_load(rs.REF_EARN_PATH, {}), inviter, who, row, pct, rs.time.time()))
    if pts > 0:
        rs.season_award(rs.primary_of(p.wallet), pts, f'trade:{p.signature[:10]}')
    return {'ok': True, 'points': pts}


@router.post('/api/reputation/wallet-watch')
async def watch_set(p: _RSM.WatchIn):
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.target):
        raise rs.HTTPException(400, 'Watch a Solana wallet address.')
    d = rs._json_load(rs.WATCH_PATH, {'targets': {}, 'last': {}})
    mine = [t for t, ws in d['targets'].items() if me in ws]
    if p.on and p.target not in mine and len(mine) >= rs.WATCH_MAX_PER_USER:
        raise rs.HTTPException(409, f'You can watch up to {rs.WATCH_MAX_PER_USER} wallets.')
    ws = set(d['targets'].get(p.target, []))
    (ws.add if p.on else ws.discard)(me)
    if ws:
        d['targets'][p.target] = sorted(ws)
    else:
        d['targets'].pop(p.target, None)
    rs._json_save(rs.WATCH_PATH, d)
    return {'watching': p.on, 'count': len([t for t, w in d['targets'].items() if me in w])}


@router.post('/api/reputation/verify/request')
async def verify_request(p: _RSM.VerifyRequest):
    """A creator asks for review (e.g. a strong coin that just misses a gate)."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.mint):
        raise rs.HTTPException(400, 'Bad mint.')
    d = rs._verify_store()
    if any(r['mint'] == p.mint and r.get('status') == 'open' for r in d['requests']):
        return {'ok': True, 'queued': False}
    d['requests'] = (d['requests'] + [{'mint': p.mint, 'by': me, 'note': p.note[:280], 'at': rs.time.time(), 'status': 'open'}])[-300:]
    rs._json_save(rs.VERIFY_PATH, d)
    return {'ok': True, 'queued': True}


@router.post('/api/reputation/wallet-dust/solana/close-tx')
async def wallet_dust_close_tx(p: _RSM.DustCloseIn):
    """Unsigned transactions (base64) that burn the leftover of each picked account and close it → rent back to the owner. Every account is
    re-read from the chain and must belong to `address`. FEELESS never signs — the owner's wallet does."""
    rs = _rs()
    if not rs._re.match(rs._B58, p.address) or not p.accounts or any(not rs._re.match(rs._B58, a) for a in p.accounts):
        raise rs.HTTPException(400, 'Bad address or accounts.')
    async with rs.httpx.AsyncClient(timeout=15) as http:
        accts = {a['pubkey']: a for a in await rs._sol_token_accounts(http, p.address)}
        bh = ((await rs._rpc(http, 'getLatestBlockhash', [{'commitment': 'finalized'}], scan=False)) or {}).get('value', {}).get('blockhash')
    items = [accts[a] for a in dict.fromkeys(p.accounts) if a in accts and accts[a].get('owner') == p.address]
    if not items or not bh:
        raise rs.HTTPException(409, 'None of those accounts belong to this wallet any more — refresh the list.')
    return {'txs': [{'tx': rs._dust.burn_close_tx(p.address, b, bh), 'accounts': [x['pubkey'] for x in b],
                     'rentSol': round(sum(x['lamports'] for x in b) / 1e9, 6), 'burns': sum(1 for x in b if x['raw'] > 0)} for b in rs._dust.batches(items)]}


@router.post('/api/reputation/internal/agent-circle-send')
async def internal_agent_circle_send(request: Request, body: dict):
    rs = _rs()
    if not rs._internal_ok(request):
        raise rs.HTTPException(403, 'Internal only.')
    key_, tx_, wid_, addr_ = str(body.get('key') or ''), str(body.get('tx') or ''), str(body.get('walletId') or ''), str(body.get('address') or '')
    if not (key_ and tx_ and wid_ and addr_):
        raise rs.HTTPException(400, 'key, tx, walletId and address are required.')
    book_ = rs._json_load(rs.AGENT_CIRCLE_SENT, {})
    if book_.get(key_):   # asked again with the same key → the same trade, never a second one
        return {'signature': book_[key_], 'again': True}
    if key_ in rs._CIRCLE_HELD:   # 🔒 audit #7: two overlapping sends with one key used to sign twice (the second saved a stale book)
        raise rs.HTTPException(409, 'That send is already being signed.')
    why_ = rs._cfund.agent_tx_policy(tx_, addr_, rs._agent_sol_to(str(body.get('catId') or '')))
    if why_:
        print(f"[agent send] {key_}: refused by the signer policy: {why_}")
        raise rs.HTTPException(403, f'The agent signer refused it: {why_}.')
    rs._CIRCLE_HELD.add(key_)
    try:
        return await rs._agent_circle_sign_send(body, key_, tx_, wid_, addr_)
    finally:
        rs._CIRCLE_HELD.discard(key_)


@router.post('/api/reputation/internal/agent-close-empty')
async def internal_agent_close_empty(request: Request, body: dict):
    """♻ An agent's wallet closes its EMPTY coin accounts, the same CloseAccount-only tx the Fuse sweep sends: the rent returns to that wallet. The send route above checks it is this cat's wallet."""
    rs = _rs()
    if not rs._internal_ok(request):
        raise rs.HTTPException(403, 'Internal only.')
    addr_ = str(body.get('address') or '')
    if not addr_:
        raise rs.HTTPException(400, 'address is required.')
    async with rs.httpx.AsyncClient(timeout=15) as http_:
        res_ = await rs.asyncio.gather(*[rs._krpc(http_, 'getTokenAccountsByOwner', [addr_, {'programId': pg}, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}]) for pg in rs._FW_TOKEN_PROGRAMS])
        rows_ = [{'pubkey': a.get('pubkey'), 'program': pg, 'lamports': (a.get('account') or {}).get('lamports'), 'info': rs._parsed_info(a.get('account'))} for pg, r in zip(rs._FW_TOKEN_PROGRAMS, res_) for a in (r or {}).get('value') or []]
        empty_ = rs._fw.empty_accounts(rows_, body.get('keep') or [])
        if not empty_:
            return {'closed': 0}
        bh_ = ((await rs._krpc(http_, 'getLatestBlockhash', [{'commitment': 'finalized'}])) or {}).get('value', {}).get('blockhash')
    if not bh_:
        raise rs.HTTPException(502, 'No blockhash.')
    sent_ = await rs.internal_agent_circle_send(request, {**body, 'tx': rs._fw.close_tx(addr_, empty_, bh_), 'key': f'close-{addr_[:12]}-{bh_[:16]}'})
    closing_ = {e['pubkey'] for e in empty_}
    return {'closed': len(empty_), 'sol': round(sum(rs._fuse._f(r.get('lamports')) for r in rows_ if r['pubkey'] in closing_) / 1e9, 9), 'signature': sent_['signature']}

