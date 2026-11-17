"""🧹 Crews — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


def _crew_pieces(members, now):
    """Closed track-record pieces (verified FEELESS trades, price result) per member wallet, last 7 days."""
    rs = _rs()
    import track_record as _trk
    trades = rs._json_load(rs.FEELESS_TRADES_PATH, {}); out = {}
    for m in members:
        rows = [x for w in (set(rs.linked_of(m)) | {m}) for x in (trades.get(w) or [])]
        out[m] = [p for p in _trk.trade_receipts(rows)[0] if now - p['at'] <= 7 * 86400]
    return out


def _crew_book(pieces, n=40):
    """📒 THE BOOKS (owner, P1 #5 "family wallet trades view"): every member's verified FEELESS trades this week in one tape, newest first —
    who, coin, return, $ result (price only, fees apart), how long it was held, the sell tx. Members' own wallets; nothing pooled."""
    rs = _rs()
    rows = [{'who': rs._crew_name(m), 'address': m, **{k: p.get(k) for k in ('symbol', 'mint', 'ret', 'usd', 'costUsd', 'holdMin', 'at', 'tx')}}
            for m, ps in (pieces or {}).items() for p in ps or []]
    return sorted(rows, key=lambda r: -(r.get('at') or 0))[:n]


def _crew_name(a):
    rs = _rs()
    pr = rs._profiles_load()['profiles'].get(rs.primary_of(a)) or {}
    return pr.get('displayName') or pr.get('handle') or f'{a[:4]}…{a[-4:]}'


def _seat_of(st, me):
    """👑 The wallet that holds `me`'s family seat (owner, 2026-10-22: "the creator must see THEIR OWN Sicario family"): `me` itself, else any
    wallet linked to `me`, else — for staff — any wallet linked to an HQ wallet (the creator's account is every one of them). → that wallet, or
    `me` when none of them is seated (joins / creates then seat `me`)."""
    rs = _rs()
    by_ = (st or {}).get('by') or {}
    if not me or me in by_:
        return me
    for w_ in rs.linked_of(me):
        if w_ in by_:
            return w_
    if rs._is_staff(me):
        for a_ in rs._admin_wallets():
            for w_ in rs.linked_of(a_):
                if w_ in by_:
                    return w_
    return me


def _crew_cfg():
    rs = _rs()
    try:   # 👥 the owner's families-per-wallet line (HQ › Familia) is applied on every crews read / write
        import crews as _cr0
        _cr0.PER_WALLET = int(rs._familia_rules().get('familiesPerWallet') or 1)
    except Exception:
        pass
    return (rs._fee_cfg().get('crews') or {})


def _crew_badge_usd(cfg=None):
    rs = _rs()
    import crews as _cr
    try:
        return float((cfg if cfg is not None else rs._crew_cfg()).get('badgeUsd', _cr.BADGE_USD))
    except (TypeError, ValueError):
        return _cr.BADGE_USD


def _crew_view(c, pieces, with_code=False):
    rs = _rs()
    import crews as _cr
    import family_room as _froom
    now_ = rs.time.time()
    ms_ = {m: _cr.stats(pieces.get(m, [])) for m in c['members']}
    rk_ = _froom.ranks(c, rs._fwar.ranks(c, ms_))
    posts_ = {}
    for p_ in c.get('posts') or []:
        posts_[p_.get('by')] = posts_.get(p_.get('by'), 0) + 1
    bnt_ = {}
    for b_ in c.get('bounties') or []:
        bnt_[b_.get('by')] = bnt_.get(b_.get('by'), 0) + 1
    act_ = {m: _froom.member(c, m, pieces.get(m, []), now_, posts_.get(m, 0), bnt_.get(m, 0)) for m in c['members']}
    mem = [{'address': m, 'name': rs._crew_name(m), 'owner': m == c['owner'], **ms_[m], **act_[m], 'rank': rk_.get(m, rs._fwar.RANKS[5])[0], 'rankLabel': rk_.get(m, rs._fwar.RANKS[5])[1]} for m in c['members']]
    names_ = {m['address']: m['name'] for m in mem}
    vit_ = _froom.vitals(c, act_, now_, rs._fwar.record(c))
    for k_ in ('hot', 'streak'):
        if vit_.get(k_):
            vit_[k_]['name'] = names_.get(vit_[k_]['w'])
    return {'id': c['id'], 'name': c['name'], 'tag': c['tag'], 'room': f"crew-{c['id']}", 'members': mem, 'seats': c.get('seats', _cr.BASE_SEATS), 'created': c.get('created'),
            'packUsd': _cr.price('seats', rs._crew_cfg()), 'packSeats': _cr.PACK_SEATS, **({'code': c['code']} if with_code and c.get('code') else {}),
            'codeSet': bool(c.get('codeHash')), 'codeTail': c.get('codeTail') if with_code else None,
            'badge': _cr.badge_view(c, (rs._json_load(rs.CREWS_PATH, {}) or {}).get('awards'), rs._crew_cfg(), rs._is_staff(c.get('owner'))),
            'vitals': vit_, 'roles': {k: list(v[:2]) for k, v in _froom.ROLES.items()}, 'promote': list(_froom.PROMOTE),
            'card': _cr.card_view(c), 'cardOpts': {k: list(v) for k, v in _cr.CARD.items()},
            **({'wire': _froom.wire(pieces, rk_, lambda w: names_.get(w) or w[:4])} if with_code else {}),
            'launch': c.get('launch'), 'bountiesOpen': sum(1 for b_ in c.get('bounties') or [] if b_.get('state') == 'open'), 'war': rs._fwar.record(c),
            'points': {m: int(v) for m, v in (c.get('points') or {}).items()} if with_code else None,
            # 💬 members-only: the board + bounties (names, never the code)
            **({'posts': [{**p_, 'name': rs._crew_name(p_['by'])} for p_ in (c.get('posts') or [])[-80:]],
                'bounties': [{**b_, 'byName': rs._crew_name(b_['by']) if b_.get('by') else None} for b_ in (c.get('bounties') or [])[-20:]]} if with_code else {})}


def _pay_sig_used(sig):
    """One payment buys ONE thing: crews / seats / badges, card rounds and prepay share this rule."""
    rs = _rs()
    import crews as _cr
    return sig in rs._PAY_HELD or sig in (rs._json_load(rs.FUSE_HQ_PATH, {}).get('roundSigs') or []) or _cr.sig_used(rs._json_load(rs.CREWS_PATH, {}), sig)


async def _pay_hold(sig):
    """Take a payment before the slow on-chain read: `claim` is one transaction shared by every worker, so of N requests (in any process)
    sending one signature exactly one goes on. It runs in a thread: a worker waiting on SQLite's write lock never stalls its event loop.
    → raises 409 when taken or already spent."""
    rs = _rs()
    if rs._pay_sig_used(sig) or not await rs.asyncio.to_thread(rs._PAY_HELD.claim, sig):
        raise rs.HTTPException(409, 'That payment was already used.')


async def _verify_sol_payment(sig, mine, min_usd, st):
    """💳 A SOL transfer one of `mine` signed to the fee wallet, confirmed on-chain, worth ≥ 97% of `min_usd` (SOL re-priced now) and never used before
    (crews and card rounds share the used-signature rule). → {sig, usd, lamports}; raises HTTPException."""
    rs = _rs()
    import crews as _cr
    if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', sig or ''):
        raise rs.HTTPException(400, 'Send the payment first — no signature yet.')
    if _cr.sig_used(st, sig):
        raise rs.HTTPException(409, 'That payment was already used.')
    await rs._pay_hold(sig)   # kept on success (the crew store then holds it too); released below when the payment does not check out
    try:
        return await rs._verify_sol_payment_held(sig, mine, min_usd)
    except BaseException:
        rs._PAY_HELD.discard(sig); raise


async def _verify_sol_payment_held(sig, mine, min_usd):
    rs = _rs()
    to = await rs._rounds_pay_to()
    if not to:
        raise rs.HTTPException(503, 'Fee wallet not set — families cannot be paid for right now.')
    tx = None
    async with rs.httpx.AsyncClient(timeout=20) as http:
        for _ in range(5):
            tx = await rs._rpc(http, 'getTransaction', [sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
            if tx:
                break
            await rs.asyncio.sleep(2)
    lam = max((rs._hq.paid_lamports(tx, w, to) for w in mine), default=0)
    usd = lam / 1e9 * (await rs._sol_usd_live() or 0)
    if usd <= 0:
        raise rs.HTTPException(400, 'No confirmed SOL payment from your wallet to the fee wallet in that transaction.')
    if usd < min_usd * 0.97:
        raise rs.HTTPException(400, f'That payment was ${usd:.2f} — this needs ${min_usd:.2f}. It is kept: add the difference and send again, or ask for a refund.')
    return {'sig': sig, 'usd': round(usd, 2), 'lamports': lam, 'at': rs.time.time()}


def _city_ctx(c, me, now):
    """→ (boost from the members' verified trades this week, the family's rank map)."""
    rs = _rs()
    import crews as _cr
    import family_room as _froom
    pcs_ = rs._crew_pieces(c['members'], now)
    ms_ = {m: _cr.stats(pcs_.get(m, [])) for m in c['members']}
    rk_ = {w: v[0] for w, v in _froom.ranks(c, rs._fwar.ranks(c, ms_)).items()}
    trades_ = sum(len(v) for v in pcs_.values())
    rush_ = 1.5 if float((c.get('world') or {}).get('rushUntil') or 0) > now else 1.0   # ⚡ the Rush hour reward
    return (1 + min(2.0, trades_ / 25)) * rush_, rk_   # 🏙 trading on FEELESS grows the city: ×1 … ×3 from the members' verified trades this week


def _city_rivals(st, c, now):
    rs = _rs()
    out = []
    for o_ in (st.get('crews') or {}).values():
        if o_['id'] == c['id']:
            continue
        oc_ = rs._fcity.accrue(rs._fcity.city_of(o_, now), now)
        out.append({'id': o_['id'], 'tag': o_.get('tag'), 'name': o_.get('name'), 'stash': int(oc_['stash']), 'guards': rs._fcity.goons(oc_, now).get('guard', 0),
                    'power': rs._fcity.power(oc_), 'odds': round(rs._fcity.rob_odds(rs._fcity.city_of(c, now), oc_, now), 2),
                    'cool': max(0, int(rs._fcity.ROB_COOLDOWN - (now - float((rs._fcity.city_of(c, now).get('robAt') or {}).get(o_['id']) or 0))))})
    return sorted(out, key=lambda r: -r['stash'])[:12]


def _city_tax():
    """🏦 The house tax on every collect (owner-set in HQ › Fees › La Familia, 0–20 %, default 5 %)."""
    rs = _rs()
    try:
        return max(0.0, min(0.20, float(rs._crew_cfg().get('houseTaxPct', rs._fcity.HOUSE_TAX * 100)) / 100))
    except (TypeError, ValueError):
        return rs._fcity.HOUSE_TAX


def _fblock_wallets(c):
    """The wallets whose positions build the block: the Don's seat wallet + every wallet linked to it (≤ 6)."""
    rs = _rs()
    own_ = (c or {}).get('owner')
    return [w_ for w_ in dict.fromkeys([own_, *(rs.linked_of(own_) if own_ else [])]) if w_][:6]


async def _fblock_reads(c, lots, now):
    """→ {key: {'amount', 'usd', 'n'}} for this family's buildings (cached FBLOCK_HELD_SEC). Never raises: a failed read = nothing proved."""
    rs = _rs()
    hit_ = rs._fblock_held.get(c['id'])
    keys_ = tuple(sorted(x['key'] for x in lots))
    if hit_ and now - hit_[0] < rs.FBLOCK_HELD_SEC and hit_[2] == keys_:
        return hit_[1]
    need_ = rs._bmk.needs(lots); out_ = {}
    wallets_ = rs._fblock_wallets(c)
    if not wallets_ or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        rs._fblock_held[c['id']] = (now, out_, keys_)
        return out_
    bal_ = {}; assets_ = []; kam_ = []; met_ = []
    async with rs.httpx.AsyncClient(timeout=12) as http:
        async def meteora(w_):   # 🌊 SITE-17 C03: Meteora's own by-wallet portfolio (no RPC quota spent)
            try:
                r_ = await http.get('https://dlmm.datapi.meteora.ag/portfolio/open', params={'user': w_})
                if r_.status_code == 200:
                    met_.append(r_.json())
            except Exception as e_:
                print('block meteora:', str(e_)[:80])
        async def toks(w_):
            try:
                r_ = await rs._rpc(http, 'getTokenAccountsByOwner', [w_, {'programId': rs.TOKEN_PROGRAM}, {'encoding': 'jsonParsed'}])
                for a_ in (r_ or {}).get('value') or []:
                    inf_ = (((a_.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
                    if inf_.get('mint') in need_['mints']:
                        bal_[inf_['mint']] = bal_.get(inf_['mint'], 0.0) + float((inf_.get('tokenAmount') or {}).get('uiAmount') or 0)
            except Exception as e_:
                print('block toks:', str(e_)[:80])
        async def nfts(w_):
            key_ = rs._chain.helius_key()
            if not key_:
                return
            try:
                r_ = await http.post(f'https://mainnet.helius-rpc.com/?api-key={key_}', json={'jsonrpc': '2.0', 'id': 1, 'method': 'getAssetsByOwner', 'params': {'ownerAddress': w_, 'page': 1, 'limit': 1000}})
                for it_ in ((r_.json() or {}).get('result') or {}).get('items') or []:
                    md_ = ((it_.get('content') or {}).get('metadata') or {})
                    assets_.append({'id': it_.get('id'), 'name': md_.get('name'), 'symbol': md_.get('symbol')})
            except Exception as e_:
                print('block nfts:', str(e_)[:80])
        async def kamino(w_):
            try:
                r_ = await http.get(f'https://api.kamino.finance/kvaults/users/{w_}/positions')
                for p_ in (r_.json() if r_.status_code == 200 else []) or []:
                    if isinstance(p_, dict):
                        kam_.append(p_)
            except Exception as e_:
                print('block kamino:', str(e_)[:80])
        chain_ = {k_: [] for k_ in rs._bmk.CHAIN}; lp_ = {}
        async def gpa(k_, w_):   # ⛓ SITE-17 C03: the wallet's own accounts of that program (owner field memcmp)
            prog_, size_, off_ = rs._bmk.CHAIN[k_]
            try:
                r_ = await rs._rpc(http, 'getProgramAccounts', [prog_, {'encoding': 'base64', 'filters': [{'dataSize': size_}, {'memcmp': {'offset': off_, 'bytes': w_}}]}])
                chain_[k_] += [rs._b64m.b64decode(a_['account']['data'][0]) for a_ in (r_ if isinstance(r_, list) else []) or []]
            except Exception as e_:
                print(f'block {k_}:', str(e_)[:80])
        async def lps(w_):   # 🫧 PumpSwap LP (a Token-2022 mint): every coin the wallet holds whose mint authority is a PumpSwap pool
            try:
                r_ = await rs._rpc(http, 'getTokenAccountsByOwner', [w_, {'programId': 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'}, {'encoding': 'jsonParsed'}])
                for a_ in (r_ or {}).get('value') or []:
                    inf_ = (((a_.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
                    raw_ = int((inf_.get('tokenAmount') or {}).get('amount') or 0)
                    if raw_ > 0 and (inf_.get('tokenAmount') or {}).get('decimals') == 9:
                        lp_[inf_['mint']] = lp_.get(inf_['mint'], 0) + raw_
            except Exception as e_:
                print('block pumpswap:', str(e_)[:80])
        jobs_ = [toks(w_) for w_ in wallets_] if need_['mints'] else []
        jobs_ += [nfts(w_) for w_ in wallets_] if need_['nft'] else []
        jobs_ += [kamino(w_) for w_ in wallets_] if need_['kamino'] else []
        jobs_ += [meteora(w_) for w_ in wallets_] if need_.get('meteora') else []
        jobs_ += [gpa(k_, w_) for k_ in ('marginfi', 'save', 'phoenix') if need_.get(k_) for w_ in wallets_]
        jobs_ += [lps(w_) for w_ in wallets_] if need_.get('pumpswap') else []
        await rs.asyncio.gather(*jobs_)
        bank_px_ = {}
        if chain_['marginfi']:   # the banks behind every active balance → mint, decimals, share values; then live prices
            try:
                bks_ = sorted({d_[72 + i_ * 104 + 1:72 + i_ * 104 + 33] for d_ in chain_['marginfi'] for i_ in range(16) if len(d_) >= 1736 and d_[72 + i_ * 104] == 1})
                b58_ = [rs._b58m.b58encode(b_).decode() for b_ in bks_][:100]
                acc_ = ((await rs._rpc(http, 'getMultipleAccounts', [b58_, {'encoding': 'base64'}])) or {}).get('value') or [] if b58_ else []
                banks_ = {b_: rs._b64m.b64decode(a_['data'][0]) for b_, a_ in zip(bks_, acc_) if a_}
                px_m_ = await rs._live_px([rs._b58m.b58encode(v_[8:40]).decode() for v_ in banks_.values()])
                mh2_ = rs._bmk.marginfi_held(chain_['marginfi'], banks_, {rs._b58m.b58decode(k_): v_ for k_, v_ in px_m_.items()})
                if mh2_:
                    bank_px_['marginfi'] = mh2_
            except Exception as e_:
                print('block marginfi banks:', str(e_)[:80])
        if lp_:   # held mints → their authorities → the ones that are PumpSwap pools → quote vault reserves
            try:
                ms_ = list(lp_)[:100]
                mi_ = ((await rs._rpc(http, 'getMultipleAccounts', [ms_, {'encoding': 'jsonParsed'}])) or {}).get('value') or []
                auth_ = {m_: (((a_ or {}).get('data') or {}).get('parsed') or {}).get('info') or {} for m_, a_ in zip(ms_, mi_)}
                cand_ = {m_: i_ for m_, i_ in auth_.items() if i_.get('mintAuthority')}
                pa_ = [i_['mintAuthority'] for i_ in cand_.values()]
                pacc_ = ((await rs._rpc(http, 'getMultipleAccounts', [pa_, {'encoding': 'base64'}])) or {}).get('value') or [] if pa_ else []
                pools_ = {m_: rs._b64m.b64decode(a_['data'][0]) for m_, a_ in zip(cand_, pacc_) if a_ and a_.get('owner') == rs._bmk.CHAIN['pumpswap'][0]}
                vk_ = {m_: rs._b58m.b58encode(p_[171:203]).decode() for m_, p_ in pools_.items()}
                va_ = ((await rs._rpc(http, 'getMultipleAccounts', [list(vk_.values()), {'encoding': 'jsonParsed'}])) or {}).get('value') or [] if vk_ else []
                vaults_ = {m_: float(((((a_ or {}).get('data') or {}).get('parsed') or {}).get('info') or {}).get('tokenAmount', {}).get('uiAmount') or 0) for m_, a_ in zip(vk_, va_)}
                qpx_ = await rs._live_px(sorted({rs._b58m.b58encode(p_[75:107]).decode() for p_ in pools_.values()}))
                ph_ = rs._bmk.pumpswap_held({m_: (lp_[m_], int(cand_[m_].get('supply') or 0)) for m_ in pools_}, pools_, vaults_, qpx_)
                if ph_:
                    bank_px_['pumpswap'] = ph_
            except Exception as e_:
                print('block pumpswap pools:', str(e_)[:80])
    px_ = await rs._live_px(list(bal_)) if bal_ else {}
    for k_, m_ in rs._bmk.MINTS.items():
        if bal_.get(m_):
            out_[k_] = {'amount': round(bal_[m_], 6), 'usd': round(bal_[m_] * float(px_.get(m_) or 0), 2)}
    for k_ in rs._bmk.NFT:
        n_ = rs._bmk.nft_count(assets_, k_)
        if n_:
            out_[k_] = {'n': n_, 'ranges': await rs._fblock_ranges(k_, [a_['id'] for a_ in assets_ if a_.get('id') and rs._bmk.nft_count([a_], k_)])}
    if kam_:
        usd_ = sum(rs._fuse._f(p_.get('totalValueUsd') or p_.get('usdValue') or p_.get('value')) for p_ in kam_)
        n_ = sum(1 for p_ in kam_ if rs._fuse._f(p_.get('totalShares') or p_.get('sharesAmount') or p_.get('stakedShares') or p_.get('unstakedShares')) > 0 or rs._fuse._f(p_.get('totalValueUsd') or p_.get('usdValue')) > 0)
        if n_:
            out_['kamino'] = {'n': n_, 'usd': round(usd_, 2) if usd_ else None}
    for k_, h_ in (('save', rs._bmk.save_held(chain_['save'])), ('phoenix', rs._bmk.phoenix_held(chain_['phoenix'])), *bank_px_.items()):
        if h_:
            out_[k_] = h_
    mh_ = rs._bmk.meteora_held(met_)
    if mh_:
        out_['meteora'] = mh_
    rs._fblock_held[c['id']] = (now, out_, keys_)
    return out_


async def _fblock_ranges(kind, nft_mints):
    """🎯 Each concentrated position's range vs its pool's price now (clmm_range): position PDAs → their accounts → their pools → in / out."""
    rs = _rs()
    import base64 as _b64
    import clmm_range as _cr
    if not nft_mints:
        return None
    try:
        async with rs.httpx.AsyncClient(timeout=12) as http:
            pdas_ = [_cr.position_pda(kind, m_) for m_ in nft_mints[:20]]
            acc_ = ((await rs._rpc(http, 'getMultipleAccounts', [pdas_, {'encoding': 'base64'}])) or {}).get('value') or []
            pos_ = [_cr.parse_position(kind, _b64.b64decode((a_.get('data') or [''])[0])) if a_ else None for a_ in acc_]
            pools_ = sorted({p_['pool'] for p_ in pos_ if p_})
            pacc_ = ((await rs._rpc(http, 'getMultipleAccounts', [pools_, {'encoding': 'base64'}])) or {}).get('value') or [] if pools_ else []
            pool_ = {k_: _cr.parse_pool(kind, _b64.b64decode((a_.get('data') or [''])[0])) for k_, a_ in zip(pools_, pacc_) if a_}
        return _cr.summary([_cr.status(p_, pool_[p_['pool']]) for p_ in pos_ if p_ and pool_.get(p_['pool'])])
    except Exception as e_:
        print('block ranges:', str(e_)[:80])
        return None


async def _fblock_view(c, me=None, staff=False, rank=None):
    rs = _rs()
    now = rs.time.time()
    lots_ = rs._bmk.lots_of(c)
    mk_ = (await rs.familia_markets()) or {}
    markets_ = {m_['key']: m_ for m_ in mk_.get('markets') or []}
    held_ = await rs._fblock_reads(c, lots_, now) if lots_ else {}
    try:
        pools_ = (await rs.familia_pools()).get('pools') or []
    except Exception:
        pools_ = []
    mine_ = me is not None
    rows_ = rs._bmk.view(lots_, markets_, held_, apys=rs._bmk.lst_apys(pools_), mine=mine_)
    built_ = [b_ for b_ in rows_ if b_['state'] == 'built']
    out_ = {'id': c['id'], 'tag': c.get('tag'), 'name': c.get('name'), 'buildings': rows_, 'built': len(built_), 'max': rs._bmk.MAX,
            'open': max(0, min(rs._bmk.OPEN, rs._bmk.MAX - len(rows_))), 'at': round(now),   # open plots to build on: always 4 until the block is full
            'town': rs._bmk.town_of(c), 'townMax': rs._bmk.TOWN_MAX, 'townAll': list(rs._bmk.TOWN),   # 🏘 the tool buildings the family picked
            'layout': rs._bmk.layout_of(c), 'layoutSaved': isinstance(c.get('layout'), dict), 'islandCells': rs._bmk.ISLAND_CELLS, 'layoutMax': rs._bmk.LAYOUT_MAX, 'stands': list(rs._bmk.STANDS),
            'islandsPaid': max(1, int(c.get('islands') or 1)), 'islandMp': 0 if staff else rs._bmk.island_price()}   # 🏝 its arrangement (cells in order, islands of 15)
    if mine_:
        out_['total'] = round(sum(float(b_.get('usd') or 0) for b_ in built_), 2)
        out_['canBuild'] = bool(staff or me == c.get('owner') or (rank or {}).get(me) == 'underboss')
        on_ = {b_['key'] for b_ in rows_}
        out_['catalog'] = [{'key': m_['key'], 'name': m_.get('name'), 'kind': m_.get('kind'), 'offer': m_.get('offer'), 'tvl': m_.get('tvl'),
                            'proof': rs._bmk.proof_of(m_['key'])[0] or 'none', 'why': '' if rs._bmk.proof_of(m_['key'])[0] else rs._bmk.proof_of(m_['key'])[1]}
                           for m_ in mk_.get('markets') or [] if m_.get('key') not in on_]
    return out_


def _cartels_now(now):
    """Cartels rebuilt from the blocklist at most every 10 min (in a thread: 20K wallets)."""
    rs = _rs()
    if now - rs._cartel_cache['at'] < 600 and rs._cartel_cache['rows']:
        return rs._cartel_cache['rows']
    try:
        rs._cartel_cache['rows'] = rs._fworld.cartels(rs._block_load()['wallets'], now)
    except Exception:
        pass
    rs._cartel_cache['at'] = now
    return rs._cartel_cache['rows']


def _world_target(st, w, tid, now, cartels_):
    """→ (target dict for the board, its borough, kind, stash). Families / CPU towns / cartels."""
    rs = _rs()
    if tid.startswith('cpu-'):
        t = rs._fworld.cpu_town(tid, now)
        if not t:
            raise ValueError('No such town.')
        return t, t['borough'], 'cpu', int(rs._fworld.cpu_stash(w, tid, now)['stash'])
    if tid.startswith('cartel-'):
        c = next((x for x in cartels_ if x['id'] == tid), None)
        if not c:
            raise ValueError('That cartel broke up.')
        t = rs._fworld.cartel_town(c)
        s = w['cpu'].setdefault(tid, {'stash': t['rate'] * 6, 'at': now})
        s['stash'] = min(t['rate'] * 10, s['stash'] + t['rate'] * max(0.0, now - s['at']) / 3600)
        s['at'] = now
        return t, 'docks', 'cartel', int(s['stash'])
    o = (st.get('crews') or {}).get(tid)
    if not o:
        raise ValueError('No such family.')
    oc = rs._fcity.accrue(rs._fcity.city_of(o, now), now)
    lots = [{'lot': int(k), 'b': v['b'], 'lvl': v['lvl']} for k, v in oc['lots'].items()]
    guards = [r['lvl'] for r in rs._fcity.ready(oc, now, 'guard')]
    home = rs._fworld.ensure_home(w, tid)
    return {'id': tid, 'tag': o.get('tag'), 'name': o.get('name'), 'lots': lots, 'guards': guards}, rs._fworld.borough_of(home), 'family', int(oc['stash'])


def _world_settle(st, w, r, now):
    """A finished raid moves its loot: from the target's stash into the raiders' bank; wins counted for the challenges."""
    rs = _rs()
    if r.get('settled') or r['status'] != 'done':
        return
    r['settled'] = True
    a = (st.get('crews') or {}).get(r['a']['id'])
    tid = r['b']['id']
    taken_ = int(r['loot'])
    if tid.startswith(('cpu-', 'cartel-')):
        s = w['cpu'].get(tid)
        if s:
            s['stash'] = max(0.0, s['stash'] - taken_)
    else:
        o = (st.get('crews') or {}).get(tid)
        if o:
            oc = rs._fcity.city_of(o, now)
            taken_ = min(taken_, int(oc['stash']))
            oc['stash'] = max(0.0, oc['stash'] - taken_)
            oc['log'] = ([{'at': now, 'what': f"🚨 raided by {r['a']['tag']} — lost {taken_:,} MP"}] + (oc.get('log') or []))[:40]
    if a:
        ac = rs._fcity.city_of(a, now)
        paid = int(taken_ * (rs._fworld.JUSTICE if r['kind'] == 'cartel' else 1))
        r['paid'] = paid
        ac['bank'] += paid
        ac['mpEver'] = ac.get('mpEver', 0) + paid
        m = a.setdefault('world', {})
        if paid > 0:
            m['raidsWon'] = int(m.get('raidsWon') or 0) + 1
            k = {'cpu': 'cpuWins', 'cartel': 'cartelWins'}.get(r['kind'])
            if k:
                m[k] = int(m.get(k) or 0) + 1
        if r['hurt']:
            hs = sorted(rs._fcity.ready(ac, now, 'hitter'), key=lambda x: -x['lvl'])[:r['hurt']]
            for h in hs:
                h['hurt'] = now + 3600
    w['log'] = ([{'at': now, 'what': f"⚔ {r['a']['tag']} raided {r['b']['tag']} — {r['end']}, {int(r.get('paid') or 0):,} MP"}] + w['log'])[:60]


def _familia_rules():
    """🏙 The owner's Familia rules (HQ › Build › 🏙 Familia), clamped — LIVE ones are applied to the engine on every world read / act."""
    rs = _rs()
    return rs._fworld.clean_rules(rs._admin_load().get('familiaRules') or {})


def _world_tick(st, w, now):
    rs = _rs()
    rs._fworld.set_rules(rs._familia_rules())
    for r in list(w['raids'].values()):
        rs._fworld.tick(r, now)
        rs._world_settle(st, w, r, now)
        if r['status'] == 'done' and now - float(r.get('endAt') or now) > 6 * 3600:
            w['raids'].pop(r['id'], None)


def _world_metrics(st, c, now):
    rs = _rs()
    city = rs._fcity.city_of(c, now)
    m = c.get('world') or {}
    w = st.setdefault('world', rs._fworld.blank())
    return {'errands': int(m.get('errands') or 0), 'collects': int(m.get('collects') or 0), 'streak': int((city.get('streak') or {}).get('days') or 0),
            'raidsWon': int(m.get('raidsWon') or 0), 'cpuWins': int(m.get('cpuWins') or 0), 'cartelWins': int(m.get('cartelWins') or 0),
            'members': len(c.get('members') or []), 'turf': len(rs._fworld.turf_of(w, c['id']))}


def _fuse_family_stats(now):
    """⚛ The Fuse wallet's real trades this week — shown in the creator's family (confirmed fills only, price result, fees apart)."""
    rs = _rs()
    try:
        rows = rs._fw_full_ledger()
    except Exception:
        return None
    if rs._fuse_fam_c['n'] == len(rows) and rs._fuse_fam_c['v']:
        return rs._fuse_fam_c['v']
    wk = [r for r in rows if r.get('status') == 'filled' and r.get('side') in ('buy', 'sell') and now - float(r.get('at') or 0) < 7 * 86400]
    sells = [r for r in wk if r['side'] == 'sell' and r.get('costUsd')]
    real = sum(float(r.get('usd') or 0) - float(r.get('costUsd') or 0) for r in sells)
    v = {'trades': len(wk), 'buys': sum(1 for r in wk if r['side'] == 'buy'), 'sells': len(sells),
         'won': sum(1 for r in sells if float(r.get('usd') or 0) > float(r.get('costUsd') or 0)),
         'volumeUsd': round(sum(float(r.get('usd') or 0) for r in wk), 2), 'realizedUsd': round(real, 2)}
    rs._fuse_fam_c.update(n=len(rows), v=v)
    return v


def _world_feecat_rate():
    rs = _rs()
    h_ = (rs._fee_cfg().get('house') or {})   # 🏠 HQ › Core › house fees wins (the owner sets every fee in one place)
    if h_.get('redeemMp') and h_.get('redeemFeecat'):
        return (max(10_000, int(h_['redeemMp'])), max(1, int(h_['redeemFeecat'])))
    cfg = rs._crew_cfg()
    try:
        return (max(10_000, int(cfg.get('redeemMp') or rs._fworld.FEECAT_RATE[0])), max(1, int(cfg.get('redeemFeecat') or rs._fworld.FEECAT_RATE[1])))
    except (TypeError, ValueError):
        return rs._fworld.FEECAT_RATE


def _world_view(st, c, me, now, cartels_):
    rs = _rs()
    w = st.setdefault('world', rs._fworld.blank())
    fams = []
    for o in (st.get('crews') or {}).values():
        rs._fworld.ensure_home(w, o['id'])
        oc = rs._fcity.city_of(o, now)
        ln_ = o.get('launch') or {}
        fams.append({'id': o['id'], 'tag': o.get('tag'), 'name': o.get('name'), 'power': rs._fcity.power(oc), 'color': (o.get('badge') or {}).get('c2') or ((o.get('badge') or {}).get('colors') or [None])[0],
                     'launch': {'mint': ln_.get('mint'), 'symbol': ln_.get('symbol')} if ln_.get('mint') else None})
    cpu_ = [rs._fworld.cpu_town(x[0], now) for x in rs._fworld.CPU]
    try:
        tr_ = rs._mt.trending(rs._json_load(rs.MEME_PATH, {}), now)
        word_ = (tr_[0].get('word') if tr_ and isinstance(tr_[0], dict) else (tr_[0] if tr_ else None))
    except Exception:
        word_ = None
    v = rs._fworld.map_view(w, fams, cpu_, cartels_, me=c['id'] if c else None, boom_=rs._fworld.boom(word_ or 'ai'), now=now)
    v['cpu'] = [{'id': t['id'], 'name': t['name'], 'tag': t['tag'], 'borough': t['borough'], 'level': t['level'], 'guards': len(t['guards']),
                 'stash': int(rs._fworld.cpu_stash(w, t['id'], now)['stash'])} for t in cpu_]
    v['cartels'] = cartels_
    links_ = w.get('links') or {}
    if links_:   # 🏦 a building set to a real pool wears its live APY / TVL (the hub's last read)
        live_p = {r['id']: r for r in ((rs._fpl_cache.get('v') or {}).get('pools') or [])}
        for b in v['blocks']:
            ln = links_.get(b['id'])
            if ln and b.get('owner'):
                lp_ = live_p.get(ln['pool']) or {}
                b['link'] = {**ln, 'apy': lp_.get('apy'), 'tvl': lp_.get('tvl'), 'pair': lp_.get('pair'), 'hold': lp_.get('hold'), 'app': lp_.get('app')}
    v['log'] = w['log'][:20]
    v['actions'] = {'attack': rs._fworld.ACTIONS_A, 'defend': rs._fworld.ACTIONS_D}
    v['rate'] = {'mp': rs._world_feecat_rate()[0], 'feecat': rs._world_feecat_rate()[1]}
    # 👑 the capital: five cities, Fee City's landmarks with their live numbers, the ranked ladder (power → CoD-style divisions)
    v['cities'] = [{'key': k, 'name': n, 'boroughs': bs, 'vibe': vb, 'held': sum(1 for b in v['blocks'] if b['b'] in bs and b.get('owner')),
                    'plots': sum(1 for b in v['blocks'] if b['b'] in bs)} for k, n, bs, vb in rs._fworld.CITIES]
    ladder = sorted(fams, key=lambda f: -f['power'])
    v['ranked'] = [{**f, 'place': i + 1, 'rank': rs._fworld.rank_of(f['power'], i + 1)} for i, f in enumerate(ladder[:25])]
    creator = next((o for o in (st.get('crews') or {}).values() if rs._is_staff(o.get('owner'))), None)
    stats_ = (rs._stats_cache.get('data') or {}) if isinstance(rs._stats_cache, dict) else {}
    live_ = {'arena': {'raids': sum(1 for r in w['raids'].values() if r.get('status') == 'live'), 'minMp': int(rs._familia_rules()['fuseMinMp'])},
             'house': {'mp': int(st.get('house') or 0)},
             'mansion': {'tag': creator.get('tag'), 'name': creator.get('name'), 'power': next((f['power'] for f in fams if f['id'] == creator['id']), 0)} if creator else None,
             'shield': {'flagged': int(stats_.get('blocklisted') or 0), 'snipers': int(stats_.get('snipers') or 0), 'bundlers': int(stats_.get('bundlers') or 0)},
             'launch': {'coins': sum(1 for o in (st.get('crews') or {}).values() if o.get('launch'))}}
    v['landmarks'] = [{'key': k, 'name': n, 'lore': lo, 'live': live_.get(k)} for k, n, lo in rs._fworld.LANDMARKS]
    v['rules'] = {k: rs._familia_rules()[k] for k in rs._fworld.LIVE_RULES}
    v['ffuse'] = rs._ffuse_view(st, c, now)
    v['staff'] = bool(me and rs._is_staff(me))   # 👑 the creator sees the OVERWATCH door in the city
    if c:
        city = rs._fcity.city_of(c, now)
        met = rs._world_metrics(st, c, now)
        lv = {}
        for l in city['lots'].values():
            lv[l['b']] = max(lv.get(l['b'], 0), l['lvl'])
        cd = ((c.get('world') or {}).get('errandAt') or {}).get(me) or {}
        docks = lv.get('docks', 0)
        v['me'] = {'id': c['id'], 'tag': c.get('tag'), 'home': w['home'].get(c['id']), 'turf': rs._fworld.turf_of(w, c['id']), 'bank': int(city['bank']),
                   'metrics': met, 'challenges': rs._fworld.challenge_rows(met, (c.get('world') or {}).get('done') or []),
                   'errands': [{'store': k, 'name': e[0], 'how': e[1], 'cd': e[2], 'lvl': lv.get(k, 0), 'ready': max(0, int(e[2] - (now - float(cd.get(k) or 0))))}
                               for k, e in rs._fworld.ERRANDS.items()],
                   'rewards': [{'key': k, 'name': r[0], 'what': r[1], 'cost': r[2]} for k, r in rs._fworld.REWARDS.items()],
                   'pts': int(((c.get('world') or {}).get('pts') or {}).get(me) or 0), 'title': ((c.get('world') or {}).get('titles') or {}).get(me),
                   'shield': max(0, int(float((c.get('world') or {}).get('shieldUntil') or 0) - now)),
                   'rush': max(0, int(float((c.get('world') or {}).get('rushUntil') or 0) - now)),
                   'hitters': [r['lvl'] for r in rs._fcity.ready(city, now, 'hitter')],
                   'reach': {b: rs._fworld.reach(w, c['id'], b, docks) for b in rs._fworld.BKEYS},
                   'prices': {b['id']: rs._fworld.block_price(w, c['id'], b['id']) for b in v['blocks'] if not b.get('owner')},
                   'moveMp': {b: int(rs._fworld.MOVE_MP * rs._fworld.tier(b) * (1 - 0.05 * lv.get('gas', 0))) for b in rs._fworld.BKEYS},
                   'redeems': [x for x in (st.get('redeems') or []) if x.get('cid') == c['id']][:10],
                   'rank': rs._fworld.rank_of(rs._fcity.power(city), next((r['place'] for r in v['ranked'] if r['id'] == c['id']), None)),
                   'place': next((i + 1 for i, f in enumerate(ladder) if f['id'] == c['id']), None),
                   'boss': bool(me and (rs._is_staff(me) or me == c.get('owner') or rs._city_ctx(c, me, now)[1].get(me) == 'underboss'))}
        if rs._is_staff(c.get('owner')):
            v['me']['fuse'] = rs._fuse_family_stats(now)
        v['raids'] = [rs._fworld.raid_view(r, 'a' if r['a']['id'] == c['id'] else 'b') for r in w['raids'].values()
                      if c['id'] in (r['a']['id'], r['b']['id'])][-8:]
    return v


def _kt_need():
    rs = _rs()
    import kalshi_trade as _kt
    if not _kt.key(rs.os.environ):
        raise rs.HTTPException(503, "Kalshi trading opens when DFlow's production key lands (DFLOW_API_KEY) — the odds stay live meanwhile.")
    return _kt


async def _kt_proof(addr):
    rs = _rs()
    import kalshi_trade as _kt
    if rs._kproof.get(addr):
        return True
    try:
        r_ = await rs._fmk_http_get().get(f'{_kt.PROOF}/{addr}', timeout=8)
        ok_ = bool(r_.status_code == 200 and (r_.json() or {}).get('verified'))
    except Exception:
        ok_ = False
    if ok_:
        rs._kproof[addr] = True
    return ok_


async def _kt_market(path_, cache_key, ttl=60, miss_ttl=60):
    rs = _rs()
    import kalshi_trade as _kt
    hit_ = rs._kmeta.get(cache_key)
    if hit_ and rs.time.time() - hit_[0] < (ttl if hit_[1] else miss_ttl):
        return hit_[1]
    try:
        r_ = await rs._fmk_http_get().get(f'{_kt.META}/{path_}', headers=_kt.headers(rs.os.environ), timeout=8)
        m_ = r_.json() if r_.status_code == 200 else None
        if r_.status_code not in (200, 404):
            return hit_[1] if hit_ else None   # DFlow blinked: the last good read, never a guess
    except Exception:
        return hit_[1] if hit_ else None
    rs._kmeta[cache_key] = (rs.time.time(), m_ if isinstance(m_, dict) else None)
    if len(rs._kmeta) > 3000:
        rs._kmeta.clear()
    return rs._kmeta[cache_key][1]


def _kt_addr(a):
    rs = _rs()
    a_ = str(a or '')
    if not (32 <= len(a_) <= 44) or any(c_ not in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c_ in a_):
        raise rs.HTTPException(400, 'Not a Solana wallet.')
    return a_


def _brk_seal():
    """Make sure a seal key exists (env first, else FEELESS's own 0600 file) — users' broker secrets are never stored in the clear."""
    rs = _rs()
    import brokers as _bk
    if not rs.os.environ.get('BROKER_SECRET_KEY'):
        rs.os.environ['BROKER_SECRET_KEY'] = _bk.seal_key_file(rs.BROKER_SEAL_PATH)


def _brk_need():
    rs = _rs()
    import brokers as _bk
    c_, k_ = _bk.keys(rs.os.environ)
    rs._brk_seal()
    if not c_:
        raise rs.HTTPException(503, 'Linking ANY broker opens when SnapTrade is set up (SNAPTRADE_CLIENT_ID · SNAPTRADE_CONSUMER_KEY) — Alpaca keys work now.')
    return _bk, c_, k_


async def _brk_call(method, path, query=None, body=None):
    rs = _rs()
    bk_, c_, k_ = rs._brk_need()
    url_, hd_ = bk_.signed(method, path, query, body, c_, k_)
    try:
        r_ = await rs._fmk_http_get().request(method, url_, headers=hd_, json=body if body not in (None, {}) else None, timeout=20)
    except Exception:
        raise rs.HTTPException(503, 'SnapTrade did not answer — try again.')
    try:
        d_ = r_.json()
    except Exception:
        d_ = {}
    if r_.status_code >= 400:
        raise rs.HTTPException(502 if r_.status_code >= 500 else 400, f"Broker: {str((d_ or {}).get('detail') or (d_ or {}).get('message') or r_.status_code)[:160]}")
    return d_


def _brk_q(primary):
    """The SnapTrade query for this wallet: a PERSONAL key → {} for the owner's (staff) wallets only, else None; a commercial key → its own
    sealed SnapTrade user ({userId, userSecret}) or None until it links."""
    rs = _rs()
    import brokers as _bk
    c_ = _bk.keys(rs.os.environ)[0]
    if not c_:
        return None
    if _bk.personal(c_):
        return {} if rs._is_staff(primary) else None
    u_ = rs._brk_user(primary)
    return {'userId': u_[0], 'userSecret': u_[1]} if u_ else None


def _brk_user(primary):
    """(userId, userSecret) for this wallet, or None."""
    rs = _rs()
    import brokers as _bk
    rec_ = (rs._json_load(rs.BROKERS_PATH, {}) or {}).get(primary)
    if not rec_:
        return None
    try:
        return rec_['uid'], _bk.unseal(rec_['sec'], rs.os.environ)
    except Exception:
        return None


def _brk_alpaca(primary):
    """This wallet's own Alpaca keys {key, secret, paper} (unsealed), or None."""
    rs = _rs()
    import brokers as _bk
    rec_ = ((rs._json_load(rs.BROKERS_PATH, {}) or {}).get(primary) or {}).get('alpaca')
    if not rec_:
        return None
    try:
        k_ = rs.json.loads(_bk.unseal(rec_['sec'], rs.os.environ))
        return {'key': k_['key'], 'secret': k_['secret'], 'paper': bool(rec_.get('paper'))}
    except Exception:
        return None


async def _alpaca_call(ak, method, path, body=None):
    rs = _rs()
    import brokers as _bk
    try:
        r_ = await rs._fmk_http_get().request(method, _bk.alpaca_base(ak['paper']) + path, headers=_bk.alpaca_headers(ak['key'], ak['secret']), json=body, timeout=15)
    except Exception:
        raise rs.HTTPException(503, 'Alpaca did not answer — try again.')
    try:
        d_ = r_.json()
    except Exception:
        d_ = {}
    if r_.status_code in (401, 403):
        raise rs.HTTPException(400, 'Alpaca refused these keys (check Key ID + Secret, and PAPER vs LIVE).')
    if r_.status_code >= 400:
        raise rs.HTTPException(400, f"Alpaca: {str((d_ or {}).get('message') or r_.status_code)[:160]}")
    return d_


def _brk_cdc(primary):
    """This wallet's own Crypto.com Exchange keys {key, secret} (unsealed), or None."""
    rs = _rs()
    import brokers as _bk
    rec_ = ((rs._json_load(rs.BROKERS_PATH, {}) or {}).get(primary) or {}).get('cdc')
    if not rec_:   # 🔑 the owner's own Exchange pair from backend/.env rides the owner's wallet — no pasting
        k_, s_ = (rs.os.getenv('CRYPTO_COM_API_KEY') or '').strip(), (rs.os.getenv('CRYPTO_COM_API_SECRET') or '').strip()
        return {'key': k_, 'secret': s_} if k_ and s_ and rs._is_staff(primary) else None
    try:
        k_ = rs.json.loads(_bk.unseal(rec_['sec'], rs.os.environ))
        return {'key': k_['key'], 'secret': k_['secret']}
    except Exception:
        return None


async def _cdc_call(ck, method, params=None):
    rs = _rs()
    import brokers as _bk
    try:
        r_ = await rs._fmk_http_get().post(f'{_bk.CDC_API}/{method}', json=_bk.cdc_signed(method, params or {}, ck['key'], ck['secret']), timeout=15)
    except Exception:
        raise rs.HTTPException(503, 'Crypto.com did not answer — try again.')
    try:
        d_ = r_.json()
    except Exception:
        d_ = {}
    if r_.status_code in (401, 403) or str((d_ or {}).get('code')) in ('40101', '40102', '40103'):
        raise rs.HTTPException(400, 'Crypto.com refused these keys (check the key + secret, and that the key can trade).')
    if r_.status_code >= 400 or (d_ or {}).get('code') not in (0, '0', None):
        raise rs.HTTPException(400, f"Crypto.com: {str((d_ or {}).get('message') or (d_ or {}).get('code') or r_.status_code)[:160]}")
    return (d_ or {}).get('result') or {}


def _cdc_dev_key():
    """The Crypto.com Developer Platform / AI-agent key: CRYPTO_COM_DEVELOPER_API_KEY, or the owner's own .env note ("Crypto.com api" then a cdc_ token on the next line)."""
    rs = _rs()
    k_ = (rs.os.getenv('CRYPTO_COM_DEVELOPER_API_KEY') or '').strip()
    if k_:
        return k_
    try:
        ls_ = [l_.strip() for l_ in (rs.Path(__file__).parent / '.env').read_text().splitlines()]
        for i_, l_ in enumerate(ls_[:-1]):
            if 'crypto.com' in l_.lower() and ls_[i_ + 1].startswith('cdc_'):
                return ls_[i_ + 1]
    except Exception:
        pass
    return ''


async def _cdc_instruments():
    """Crypto.com's public instrument list (spot · perpetuals · futures), one read per 10 min for everyone."""
    rs = _rs()
    import brokers as _bk
    if rs.time.time() - rs._cdc_inst['at'] < 600 and rs._cdc_inst['rows']:
        return rs._cdc_inst['rows']
    try:
        r_ = await rs._fmk_http_get().get(f'{_bk.CDC_API}/public/get-instruments', timeout=12)
        rows_ = ((r_.json() or {}).get('result') or {}).get('data') or []
        if rows_:
            rs._cdc_inst.update(at=rs.time.time(), rows=rows_)
    except Exception:
        pass
    return rs._cdc_inst['rows']


def _pperp_board():
    """The Perps desk's live board → {coin: {mark, fundApr, maxLev, venues}} (the shared 60 s read)."""
    rs = _rs()
    return {r_['coin']: r_ for r_ in (rs._perps_cache.get('rows') or []) if r_.get('coin')}


def _arena_day(now):
    rs = _rs()
    return rs.time.strftime('%Y-%m-%d', rs.time.gmtime(now))


def _tg_user(tg):
    rs = _rs()
    return rs._tga.verify(tg, (rs.os.getenv('TELEGRAM_BOT_TOKEN') or '').strip()) if tg else None


async def _tg_group(text):
    """📲 a post to the owner's Telegram group (level-ups, the day's top shooter) with a PLAY button. Silent when it isn't set up."""
    rs = _rs()
    tok_, chat_ = (rs.os.getenv('TELEGRAM_BOT_TOKEN') or '').strip(), (rs.os.getenv('TELEGRAM_GROUP_ID') or '').strip()
    if not (tok_ and chat_ and text):
        return False
    app_ = (rs.os.getenv('TELEGRAM_APP_URL') or '').strip()
    body_ = {'chat_id': chat_, 'text': text, 'disable_web_page_preview': True}
    if app_.startswith('https://'):
        body_['reply_markup'] = {'inline_keyboard': [[{'text': '🎯 PLAY STRIKE ZONE', 'url': app_}]]}
    try:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            r_ = await http.post(f'https://api.telegram.org/bot{tok_}/sendMessage', json=body_)
            return r_.status_code == 200
    except Exception:
        return False


def _arena_who(address, session, tg):
    """→ (who, name) — a wallet, a Telegram player, or (None, 'guest')."""
    rs = _rs()
    if address and session:
        return rs._session_or_401(address, session), ''
    u = rs._tg_user(tg)
    if tg and not u:
        raise rs.HTTPException(401, 'Telegram sign-in did not verify — reopen the game from the bot.')
    return (f"tg:{u['id']}", u['name']) if u else (None, 'guest')


def _arena_unlock_level(who, level):
    """👑 the creator / staff wallets own every gun + part from day one (owner 2026-10-28); everyone else unlocks by level."""
    rs = _rs()
    try:
        return 999 if who and not str(who).startswith('tg:') and rs._is_staff(who) else level
    except Exception:
        return level


def _arena_profile(players, who):
    rs = _rs()
    p = players.get(who) or {}
    lv = rs._ar.level_of(p.get('xp')); ul_ = rs._arena_unlock_level(who, lv['level'])
    return {'xp': lv['total'], 'level': lv['level'], 'into': lv['into'], 'need': lv['need'], 'loadout': rs._ar.clean_loadout(p.get('loadout'), ul_),
            'unlocked': rs._ar.unlocked(ul_), 'kills': int(p.get('kills') or 0), 'wins': int(p.get('wins') or 0), 'staff': ul_ != lv['level']}


def _ffuse_cards(st, c):
    """The cards a family can field: Fuse designs its members published + the Fuse cards its members hold (the creator family: every design)."""
    rs = _rs()
    members = {m.get('address') if isinstance(m, dict) else m for m in c.get('members') or []}
    members |= {w_ for m_ in list(members) if m_ for w_ in rs.linked_of(m_)}   # 🐛 (P1 #7) a card made / held on a member's LINKED wallet counts too
    staff_ = rs._is_staff(c.get('owner'))
    hq_ = rs._json_load(rs.FUSE_HQ_PATH, {})
    out = []
    for fid, f in (rs._json_load(rs.FUSES_PATH, {'fuses': {}}).get('fuses') or {}).items():
        if f.get('enabled', True) and (staff_ or f.get('creator') in members):
            out.append(rs._ffuse.card_of(f'design:{fid}', f.get('name'), f.get('legs')))
    for pos in hq_.get('positions') or []:
        if pos.get('wallet') in members and not pos.get('closedAt'):
            out.append(rs._ffuse.card_of(f"card:{pos['id']}", pos.get('name'), pos.get('legs')))
    if staff_:   # 👑 the creator family fields the Arena's own Prime cards too (the real card first) — the ones standing over the stadium
        for k_, pc_ in sorted(((hq_.get('prime') or {}).get('cards') or {}).items(), key=lambda kv: not (kv[1] or {}).get('real')):
            if isinstance(pc_, dict) and pc_.get('legs'):
                out.append(rs._ffuse.card_of(f'prime:{k_}', pc_.get('name') or f"{'REAL · ' if pc_.get('real') else ''}{k_.title()}", pc_.get('legs')))
    seen_, uniq_ = set(), []
    for x_ in out:
        if x_['coins'] and x_['key'] not in seen_:
            seen_.add(x_['key']); uniq_.append(x_)
    return uniq_[:30]


async def _ffuse_prices(cards):
    rs = _rs()
    legs = [{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for cd in cards if cd for l in cd['legs']]
    pairs_ = await rs._fuse_pairs(legs) if legs else {}
    return ({k: rs._fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}, {k: rs._fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_.items()})


def _ffuse_book(f, side, prices, liqs, now):
    rs = _rs()
    cd = f[side]['card']
    return rs._pgb.paper_book(f"ff:{f['id']}:{side}", {'name': cd['name'], 'legs': [{**l, 'weight': l['usd']} for l in cd['legs']]}, prices, liqs, now, 100.0)


def _ffuse_pay(st, f, now):
    """Move a settled / expired fight's MP + points: banks, bidders' member points, the house."""
    rs = _rs()
    crews_ = st.get('crews') or {}
    paid = f.get('paid') or {}
    if f['status'] == 'expired':
        paid = {'fam': {f['a']['id']: f['mp']} if f['mp'] else {}, 'bids': {w: b['pts'] for w, b in f['bids'].items()}, 'house': 0}
    for cid, mp in (paid.get('fam') or {}).items():
        if crews_.get(cid) and mp:
            rs._fcity.city_of(crews_[cid], now)['bank'] += int(mp)
    import crews as _cr
    for w, pts in (paid.get('bids') or {}).items():
        o = _cr.crew_of(st, w)
        if o and pts:
            pm = o.setdefault('world', {}).setdefault('pts', {}); pm[w] = int(pm.get(w) or 0) + int(pts)
    st['house'] = int(st.get('house') or 0) + int(paid.get('house') or 0)
    if f['status'] == 'done' and f.get('ranked') and not f.get('elo') and crews_.get(f['a']['id']) and crews_.get(f['b']['id']):   # 🎖 ranked → ratings move once
        ca_, cb_ = crews_[f['a']['id']], crews_[f['b']['id']]
        ra_, rb_ = [int(((x_.get('world') or {}).get('fuseElo')) or rs._ffuse.ELO0) for x_ in (ca_, cb_)]
        na_, nb_ = rs._ffuse.elo(ra_, rb_, {'a': 1, 'b': 0}.get(f.get('winner'), 0.5))
        ca_.setdefault('world', {})['fuseElo'] = na_; cb_.setdefault('world', {})['fuseElo'] = nb_
        f['elo'] = {'a': [ra_, na_], 'b': [rb_, nb_]}
    w_ = st.setdefault('world', rs._fworld.blank())
    w_['log'] = ([{'at': now, 'what': (f"⚔ Family Fuse: [{f[f['winner']]['tag']}] beat [{f['b' if f['winner'] == 'a' else 'a']['tag']}]" + (f" · +{(paid.get('fam') or {}).get(f[f['winner']]['id'], 0):,} MP" if f['mp'] else ' · paper'))
                  if f.get('winner') in ('a', 'b') else f"⚔ Family Fuse [{f['a']['tag']}] vs [{f['b']['tag']}] — {'draw' if f['status'] == 'done' else 'nobody took it'}"}] + (w_.get('log') or []))[:60]


async def _ffuse_tick(now, force=False):
    """Mark every live Family Fuse at live prices (≤ every 20s), settle the ones past their bell, expire untaken challenges."""
    rs = _rs()
    if not force and now - rs._ffuse_mark['at'] < 20:
        return
    rs._ffuse_mark['at'] = now
    st0 = rs._json_load(rs.CREWS_PATH, {})
    live = [f for f in ((st0.get('world') or {}).get('ffuse') or {}).values() if f['status'] == 'live']
    if not live and not any(f['status'] == 'open' for f in ((st0.get('world') or {}).get('ffuse') or {}).values()):
        return
    prices, liqs = await rs._ffuse_prices([f[s]['card'] for f in live for s in ('a', 'b')])
    async with rs._crews_lock:
        st = rs._json_load(rs.CREWS_PATH, {}); store = st.setdefault('world', rs._fworld.blank()).setdefault('ffuse', {})
        for f in list(store.values()):
            if rs._ffuse.expire(f, now):
                rs._ffuse_pay(st, f, now)
            if f['status'] != 'live':
                continue
            for s_ in ('a', 'b'):
                if f['books'].get(s_):
                    f['books'][s_] = rs._pgb.paper_mark(f['books'][s_], prices, liqs, now)
            d_ = rs._pgb.duels(f['books'].get('a'), f['books'].get('b'), f['bell'].get('a'), f['bell'].get('b'))
            f['score'] = d_
            if now >= f['ends']:
                rs._ffuse.settle(f, rs._pgb.duel_winner(d_, (f['books'].get('a') or {}).get('pct'), (f['books'].get('b') or {}).get('pct')), now, d_)
                rs._ffuse_pay(st, f, now)
        done = sorted((f for f in store.values() if f['status'] in ('done', 'expired')), key=lambda f: -f.get('endAt', 0))
        for f in done[rs._ffuse.LOG_KEEP:]:
            store.pop(f['id'], None)
        rs._json_save(rs.CREWS_PATH, st)


def _ffuse_view(st, c, now):
    rs = _rs()
    store = (st.get('world') or {}).get('ffuse') or {}
    rows = sorted(store.values(), key=lambda f: (f['status'] not in ('live', 'open'), -f['at']))
    out = {'fights': [rs._ffuse.view(f, now) for f in rows[:8]], 'mins': list(rs._ffuse.MINS), 'bid': [rs._ffuse.BID_MIN, rs._ffuse.BID_MAX], 'house': rs._ffuse.HOUSE,
           'brackets': [{'key': k_, 'word': w_, 'from': lo_} for k_, w_, lo_ in rs._ffuse.BRACKETS],
           'ladder': sorted(({'id': x_['id'], 'tag': x_.get('tag'), 'name': x_.get('name'), 'rating': int(((x_.get('world') or {}).get('fuseElo')) or rs._ffuse.ELO0),
                              'bracket': rs._ffuse.bracket(((x_.get('world') or {}).get('fuseElo')) or rs._ffuse.ELO0)[1], 'badge': x_.get('badge')} for x_ in (st.get('crews') or {}).values()),
                             key=lambda r_: -r_['rating'])[:12]}
    if c:
        out['cards'] = rs._ffuse_cards(st, c)
    return out


async def _cat_for_fund(cat_id, me):
    """The agent (from the agent service) + its own wallet, owned by `me`. Raises HTTPException."""
    rs = _rs()
    if not rs._re.match(r'^[A-Za-z0-9_-]{1,64}$', cat_id or ''):
        raise rs.HTTPException(400, 'Not an agent id.')
    r = await rs._ai_http().get(f'http://127.0.0.1:5088/api/cats/{cat_id}', headers={'x-feeless-internal': rs._internal_key()}, timeout=8)   # the full record (its wallet) — the public view hides it
    if r.status_code != 200:
        raise rs.HTTPException(404, 'Cat not found.')
    cat = (r.json() or {}).get('cat') or {}
    w = cat.get('agentWallet') or {}
    if not w.get('address'):
        raise rs.HTTPException(400, 'Give it its own wallet first.')
    if w.get('owner') != me:
        raise rs.HTTPException(403, "Only the wallet that made this agent's wallet can fund it.")
    if w.get('provider', 'crossmint') not in ('crossmint', 'circle'):
        raise rs.HTTPException(400, "That wallet is watch-only (its key isn't held by Crossmint) — fund it straight from your own wallet; FEELESS can't trade from it.")
    return cat, w


def _cat_fund_rules(me=None):
    """💵 What funding a cat costs, from HQ › Fees (owner 2026-10-29: "I wanna set how much per cat in cmd"): the one-time fee + the least a
    first funding may be. A staff / creator wallet pays NO fee and may start from $1 ("I'm the owner — it shouldn't charge me the fee")."""
    rs = _rs()
    staff_ = bool(me) and rs._is_staff(me)
    pool_ = rs._cpool.load(rs.POOL_PATH)['cfg']
    return {'feeUsd': 0.0, 'minUsd': rs._cfund.TOPUP_MIN_USD if staff_ else pool_['firstMinUsd'], 'topupMinUsd': rs._cfund.TOPUP_MIN_USD, 'depositPct': pool_['depositPct'],
            'maxUsd': rs._cfund.MAX_USD, 'staff': staff_, 'maxCats': rs._cfund.MAX_CATS}


async def _openrouter_left(fresh=False):
    """🛟 The real $ left on FEELESS's OpenRouter account (it pays every agent's model calls): read once a minute, a last good read kept 10 min, None = unknown. Low → the owner hears it, once a day."""
    rs = _rs()
    now = rs.time.time()
    if not fresh and rs._or_float['at'] and now - rs._or_float['at'] < 60:
        return rs._or_float['left']
    key_ = rs.os.environ.get('OPENROUTER_API_KEY', '').strip()
    left = None
    if key_:
        try:
            async with rs.httpx.AsyncClient(timeout=6) as http:
                r = await http.get('https://openrouter.ai/api/v1/credits', headers={'Authorization': f'Bearer {key_}'})
            if r.status_code == 200:
                d_ = r.json().get('data') or {}
                left = round(float(d_.get('total_credits') or 0) - float(d_.get('total_usage') or 0), 4)
        except Exception:
            left = None
    if left is None and rs._or_float['at'] and now - rs._or_float['at'] < 600:
        return rs._or_float['left']
    rs._or_float.update(at=now, left=left)
    if left is not None and left < rs._cfund.MODEL_FLOOR_USD:
        for w_ in rs._owner_wallets():
            rs.notify(w_, 'alert', f"🧠 OpenRouter has ${left:.2f} left. Agents can't think and model credit sales are paused until you add credit at openrouter.ai/settings/credits.", '/terminal/feecat/agents', once=f"or-float:{rs.time.strftime('%Y-%m-%d', rs.time.gmtime())}")
    return left


async def _vault_gap_read():
    rs = _rs()
    now = rs.time.time(); c = rs._pgap_c
    pools_ = sorted(((await rs.familia_pools()) or {}).get('pools') or [], key=lambda r_: -rs._fuse._f(r_.get('tvl')))
    mints_ = list(dict.fromkeys(m_ for r_ in pools_ for m_ in (r_.get('mints') or []) if isinstance(m_, str) and 32 <= len(m_) <= 44))[:rs._pgap.TOKENS]

    async def one_(m_):
        try:
            r_ = await rs._ai_http().get(f'https://api.dexscreener.com/token-pairs/v1/solana/{m_}', timeout=10)
            j_ = r_.json() if r_.status_code == 200 else []
            return j_ if isinstance(j_, list) else []
        except Exception as e_:
            print(f'[gaps] {m_[:6]}: {e_}')
            return []
    pairs_ = [p_ for ps_ in await rs.asyncio.gather(*(one_(m_) for m_ in mints_)) for p_ in ps_]
    if not pairs_ and c['v'] is not None:   # a failed read keeps the last good board
        return c['v']
    rows_ = rs._pgap.persist(c['book'], rs._pgap.gaps(pairs_, mints_), now)
    c.update(at=now, v={'gaps': rows_, 'tokens': len(mints_), 'open': sum(1 for g_ in rows_ if g_.get('open')), 'cost': rs._pgap.COST_PCT, 'at': round(now, 1)})
    return c['v']


async def _pgap_once(key, make):
    rs = _rs()
    t_ = rs._pgap_fly.get(key)
    if t_ is None:
        t_ = rs._pgap_fly[key] = rs.asyncio.ensure_future(make())
        t_.add_done_callback(lambda _t, k_=key: rs._pgap_fly.pop(k_, None))
    return await rs.asyncio.shield(t_)


async def _coin_gap_read(mint):
    rs = _rs()
    now = rs.time.time(); c = rs._pgap_coin.get(mint)
    try:
        r_ = await rs._ai_http().get(f'https://api.dexscreener.com/token-pairs/v1/solana/{mint}', timeout=10)
        pairs_ = r_.json() if r_.status_code == 200 else []
        pairs_ = pairs_ if isinstance(pairs_, list) else []
    except Exception as e_:
        print(f'[coin gap] {mint[:6]}: {e_}')
        pairs_ = []
    if not pairs_ and c and c['v'] is not None:   # a failed read keeps the last good answer
        return c['v']
    if c is None:
        if len(rs._pgap_coin) >= 400:
            rs._pgap_coin.pop(min(rs._pgap_coin, key=lambda k_: rs._pgap_coin[k_]['at']), None)
        c = rs._pgap_coin[mint] = {'at': 0.0, 'v': None, 'book': {}}
    rows_ = rs._pgap.persist(c['book'], rs._pgap.gaps(pairs_, [mint]), now)
    real_ = sum(1 for p_ in pairs_ if isinstance(p_, dict) and p_.get('chainId', 'solana') == 'solana' and rs._pgap._ok(p_))
    c.update(at=now, v={'mint': mint, 'gap': rows_[0] if rows_ else None, 'pools': len(pairs_), 'realPools': real_, 'cost': rs._pgap.COST_PCT,
                        'answered': bool(pairs_), 'at': round(now, 1)})
    return c['v']


async def _jl_borrow(method, path, **kw):
    rs = _rs()
    return await rs._jl_lend(method, f'borrow/{path}', **kw)


async def _jl_lend(method, path, **kw):
    """One Jupiter Lend call (earn/… or borrow/…) over every key (a key at its rate limit falls through), then the public host. → (status, body)."""
    rs = _rs()
    hosts_ = [('https://api.jup.ag/lend/v1', {'x-api-key': k_}) for k_ in rs._jkeys.lend_keys(rs.os.environ)] + [('https://lite-api.jup.ag/lend/v1', {})]
    last_ = (503, {'error': 'Jupiter did not answer.'})
    for base_, hdr_ in hosts_:
        try:
            r_ = await rs._ai_http().request(method, f"{base_}/{path}", headers=hdr_, timeout=12, **kw)
        except Exception:
            continue
        try:
            b_ = r_.json()
        except Exception:
            b_ = {}
        if r_.status_code == 429:
            last_ = (429, {'error': 'Jupiter is busy right now — try again in a minute.'})
            continue
        return r_.status_code, b_
    return last_


async def _jl_markets():
    rs = _rs()
    import lend_borrow as _lb
    if rs.time.time() - rs._flv_vaults.get('at', 0) > 30 or not rs._flv_vaults.get('rows'):
        code_, b_ = await rs._jl_borrow('GET', 'vaults')
        rows_ = _lb.markets(b_) if code_ == 200 else []
        if rows_:
            rs._flv_vaults.update(at=rs.time.time(), rows=rows_)
    return rs._flv_vaults.get('rows') or []


async def _jp_call(method, path, **kw):
    """One Jupiter Perps API call → (status, body)."""
    rs = _rs()
    import jup_perps as _jp
    try:
        r_ = await rs._ai_http().request(method, f"{_jp.API}/{path}", timeout=15, **kw)
    except Exception:
        return 503, {'message': 'Jupiter Perps did not answer.'}
    try:
        return r_.status_code, r_.json()
    except Exception:
        return r_.status_code, {}


async def _rng_get(key, url, params, parse):
    rs = _rs()
    hit_ = rs._rng_cache.get(key)
    if hit_ and rs.time.time() - hit_[0] < 120:
        return hit_[1]
    try:
        r_ = await rs._fmk_http_get().get(url, params=params, timeout=12)
        rows_ = parse(r_.json() if r_.status_code == 200 else {})
    except Exception:
        rows_ = None
    if rows_ is None:
        return hit_[1] if hit_ else []
    rs._rng_cache[key] = (rs.time.time(), rows_)
    if len(rs._rng_cache) > 400:
        rs._rng_cache.clear()
    return rows_


async def _collective_band_pass():
    """🏊 Each Collective pool with a band, against its live price: a ping to the owner when it sits out of range. It moves nothing."""
    rs = _rs()
    import range_pools as _rp
    rows_ = [p_ for p_ in (rs._cpool.load(rs.POOL_PATH).get('pools') or []) if p_.get('on') and p_.get('mint') and p_.get('bandLow') and p_.get('bandHigh')]
    for p_ in rows_:
        got_ = await rs.familia_pools_ranges(mint=p_['mint'], quote='', top=0); px_ = next((x_['price'] for x_ in got_.get('pools') or [] if x_['pool'] == p_['address']), None)
        band_, msg_ = _rp.watch_step({**(p_.get('watch') or {}), 'lo': p_['bandLow'], 'hi': p_['bandHigh'], 'sym': p_['pair']}, px_, rs.time.time())
        def keep(st, id_=p_['id'], b_=band_):
            r_ = next((x_ for x_ in st.get('pools') or [] if x_['id'] == id_), None)
            if r_:
                r_['watch'] = {k_: b_[k_] for k_ in ('outSince', 'alertedAt') if b_.get(k_)}
        rs._cpool.update(rs.POOL_PATH, keep)
        if msg_:
            for w_ in list(rs._admin_wallets())[:3]:
                rs.notify(w_, 'autorange', msg_.replace('(your wallet signs)', '(by hand, on the venue)'), url='/terminal', meta={'claim': 'autorange', 'source': 'collective'})


async def _autorange_watch():
    """Every minute: each armed band vs its pool's own live price (the venue API, cached 2 min) → a phone ping when a move is due."""
    rs = _rs()
    import range_pools as _rp
    while True:
        await rs.asyncio.sleep(60)
        try:
            await rs._collective_band_pass()
            st_ = rs._json_load(rs.AUTORANGE_PATH, {}) or {}
            if not st_:
                continue
            px_ = {}
            for mint_ in {r_['mint'] for rows_ in st_.values() for r_ in rows_}:
                got_ = await rs.familia_pools_ranges(mint=mint_, quote='', top=0)
                px_.update({p_['pool']: p_['price'] for p_ in got_.get('pools') or []})
            now_, changed_ = rs.time.time(), False
            for w_, rows_ in st_.items():
                for i_, r_ in enumerate(rows_):
                    nb_, msg_ = _rp.watch_step(r_, px_.get(r_['pool']), now_)
                    if nb_ != r_:
                        rows_[i_] = nb_; changed_ = True
                    if msg_:
                        rs.notify(w_, 'autorange', msg_, url='/terminal/launch?mode=pools', meta={'claim': 'autorange', 'source': r_['venue'], 'pool': r_['pool']})
            if changed_:
                rs._json_save(rs.AUTORANGE_PATH, st_)
        except Exception as e:
            print('autorange watch:', str(e)[:120])


def _lan_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))   # no packet is sent: it only picks the interface the LAN route uses
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


def _hqp_site(port):
    rs = _rs()
    ip = rs._lan_ip()
    return f"http://{ip}:{int(port)}" if ip else None


async def _wars_tick(now):
    """⚔ The family-war clock, every warm pass: void unanswered call-outs at the bell, start accepted ones, settle finished ones on the
    teams' VERIFIED trades in the window (points pot only). Winners get an inbox note."""
    rs = _rs()
    async with rs._crews_lock:
        st = rs._json_load(rs.CREWS_PATH, {})
        if not st.get('wars'):
            return
        busy = [w for w in st['wars'] if w['state'] in (rs._fwar.OPEN, rs._fwar.SET, rs._fwar.LIVE)]
        if not busy:
            return
        mem = {m for w in busy for t in (w.get('teams') or {}).values() for m in t}
        before = [w['state'] for w in busy]
        ev = rs._fwar.tick(st, rs._crew_pieces(list(mem), now) if mem else {}, now)
        if ev or any(w['state'] != b_ for w, b_ in zip(busy, before)):
            rs._json_save(rs.CREWS_PATH, st)
            rs._crew_cache['data'] = None
    for w, kind in ev:
        if kind != 'done' or not (w.get('result') or {}).get('winner'):
            continue
        win = w['result']['winner']
        for cid in [w[win]] + list((w.get('allies') or {}).get(win) or []):
            c = (st.get('crews') or {}).get(cid) or {}
            try:
                rs.notify(c.get('owner'), 'family', f"🏆 [{c.get('tag')}] won the war — the pot of {rs._fwar.pot(w)} pts is in your chest", url='/terminal/leaderboard?lens=crews', once=f"war:{w['id']}:{cid}", push=False, meta={'claim': 'family war won', 'source': 'family_wars'})
            except Exception:
                pass


async def _crew_season_tick(now):
    """Once a week (the first pass after Monday 00:00 UTC): the top 3 RANKED crews (verified results over the last 7 days) pay their members season
    points (150 / 100 / 60 each), an inbox note and a line in the Fuse chat. Recorded in crews.json so it never repeats."""
    rs = _rs()
    import crews as _cr
    week0 = int((now // 86400 - rs.time.gmtime(now).tm_wday) * 86400)
    async with rs._crews_lock:
        st = rs._json_load(rs.CREWS_PATH, {})
        if st.get('awardedWeek') == week0 or not st.get('crews'):
            return
        members = [m for c in st['crews'].values() for m in c['members']]
        top = [r for r in _cr.board(st, rs._crew_pieces(members, now), now) if r['ranked']][:3]
        st['awardedWeek'] = week0; st.setdefault('awards', []).append({'week': week0, 'top': [{'id': r['id'], 'name': r['name'], 'pct': r['pct']} for r in top]})
        st['awards'] = st['awards'][-26:]
        rs._json_save(rs.CREWS_PATH, st)
    medal = ['🥇', '🥈', '🥉']
    for i, r in enumerate(top):
        c = st['crews'].get(r['id'])
        for w in (c or {}).get('members') or []:
            rs.season_award(w, rs.CREW_PRIZES[i], 'crew-week')
            try:
                rs.notify(w, 'family', f"{medal[i]} Your family {c['name']} placed #{i + 1} this week ({r['pct']:+.1f}%): +{rs.CREW_PRIZES[i]} season points", url='/terminal/leaderboard?lens=families', once=f'family:{week0}', push=False, meta={'source': 'family'})
            except Exception:
                pass
    if top:
        try:
            rs._fuse_chat('fuse-lab', '🌹 Families of the week: ' + ' · '.join(f"{medal[i]} [{r['tag']}] {r['name']} {r['pct']:+.1f}%" for i, r in enumerate(top)), f'family-week-{week0}')
        except Exception:
            pass
    rs._crew_cache['data'] = None


def _crew_room_ok(room, address):
    """crew-<id> rooms: only members post (anyone may read — crew rooms are public to read). → (is_crew_room, allowed)."""
    rs = _rs()
    if not str(room).startswith('crew-'):
        return False, True
    c = (rs._json_load(rs.CREWS_PATH, {}).get('crews') or {}).get(room[5:])
    return True, bool(c and rs.primary_of(address) in {rs.primary_of(m) for m in c['members']})

