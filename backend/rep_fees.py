"""🧹 Trading fees and discounts — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""



def _rs():
    import reputation_service
    return reputation_service


def _fee_cfg():
    rs = _rs()
    d = rs._admin_load()
    cfg = {**rs.FEE_DEFAULTS, **(d.get('fees') or {})}
    cfg['tierDiscountPct'] = {**rs.FEE_DEFAULTS['tierDiscountPct'], **(cfg.get('tierDiscountPct') or {})}
    return cfg


def _engine_cfg(cfg):
    rs = _rs()
    return {'engine': cfg.get('engine') if cfg.get('engine') in ('swap', 'ultra') else 'swap', 'ultraFallback': bool(cfg.get('ultraFallback')),
            'priorityMaxLamports': max(0, min(rs.PRIORITY_MAX_LAMPORTS, int(cfg.get('priorityMaxLamports') or 0)))}


def _fee_owner_sol(acct):
    """🩹 which admin / owner wallet owns the SOL fee account (its wSOL ATA) — trading pays that wallet plain SOL while the account is closed."""
    rs = _rs()
    if not acct:
        return None
    if acct not in rs._fee_owner_cache:
        import fee_tx as _ftx
        rs._fee_owner_cache[acct] = _ftx.fee_owner(acct, list(dict.fromkeys(rs._owner_wallets() + rs._admin_wallets())))
    return rs._fee_owner_cache[acct]


def _swap_fee_accounts(cfg, input_mint, output_mint):
    """FEELESS token accounts that can take this swap's fee (their mint must be one side of the trade),
    pay side first, then receive side. Jupiter is tried with each in order."""
    rs = _rs()
    by_mint = {rs.WSOL_MINT: cfg.get('feeAccountSol'), rs.USDC_MINT: cfg.get('feeAccountUsdc')}
    return [by_mint[m] for m in (input_mint, output_mint) if by_mint.get(m)]


def _swap_fee_account(cfg, input_mint, output_mint):
    rs = _rs()
    return (rs._swap_fee_accounts(cfg, input_mint, output_mint) or [None])[0]


async def _leg_usd(input_mint, amount):
    """$ size of a swap from its pay side (SOL/USDC instantly; a coin from its live price, ≤3s)."""
    rs = _rs()
    amount = rs._fuse._f(amount)
    if amount <= 0:
        return 0.0
    if input_mint in (rs.USDC_MINT, 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'):
        return amount
    if input_mint == rs.WSOL_MINT:
        return amount * (await rs._sol_usd_live() or 0)
    try:
        px = (await rs.asyncio.wait_for(rs._token_prices([input_mint]), 3)).get(input_mint) or 0
    except Exception:
        px = 0
    return amount * px


def _agent_owner(wallet: str) -> str:
    """👛 the wallet that OWNS an agent wallet (FeeCat's own Crossmint wallet per cat): `agentWallet.owner` is the signed-in wallet that made it
    (feecat_service checks the signature before it records it). '' when this isn't a live agent wallet."""
    rs = _rs()
    if not wallet:
        return ''
    cats = (rs._json_load(rs.DATA_DIR / 'feecats.json', {}) or {}).get('cats') or {}
    for c in cats.values():
        w = c.get('agentWallet') or {}
        if w.get('address') == wallet and not c.get('revoked'):
            return str(w.get('owner') or '')
    return ''


async def effective_fee(wallet: str, input_mint: str = '', output_mint: str = '', bundle: int = 0, amount: float = 0, card: int = 0, card_id: str = ''):
    """The fee for one trade plus how each engine collects it.
    bps: Swap API fee (paid to feeAccount). ultraBps / referralAccount: the Ultra fallback's fee.
    bundle ≥ 2 = one leg of a Fuse / runner card bought all at once → bundle pricing (flat $ per coin); HQ (staff)
    pays no FEELESS fee on bundles — only the network / partner fees."""
    rs = _rs()
    cfg = rs._fee_cfg()
    eng = rs._engine_cfg(cfg)
    base = int(cfg['platformFeeBps'] or 0)
    fee_account = rs._swap_fee_account(cfg, input_mint, output_mint)
    none = lambda note: {'bps': 0, 'ultraBps': 0, 'baseBps': base, 'notes': [note] if note else [], 'referralAccount': None, 'feeAccount': None, **eng}
    if not base:
        return none('No FEELESS fee on this trade.')
    if wallet and rs._is_staff(wallet):   # 👑 owner 2026-10-29: "creator wallet or admins don't pay fees site wide" — every trade, any engine
        return none('Creator / admin wallet: no FEELESS fee, site-wide.')
    if wallet and rs._is_staff(rs._agent_owner(wallet)):   # 👑 owner 2026-10-30: "no fee for staff" — an agent wallet a staff wallet owns trades fee-free too
        return none("Staff-owned agent wallet: no FEELESS fee.")
    mints = await rs._ecosystem_mints()
    # The ONLY fee-free trades: buying a FEELESS coin. There is no other exemption.
    # FEELESS coins ($FEE, FEECAT, rFEE) are free to BUY with SOL, USDC or USDT. Selling them, buying them with
    # any other token, and every other swap pays the platform fee.
    eco = {m: k for k, m in mints.items() if k in ('fee', 'feecat', 'rfee') and m}
    if output_mint in eco and input_mint in rs.FEE_SETTLEMENT_MINTS:
        return none(f"Buying ${eco[output_mint].upper()} with SOL or USD is fee-free.")
    notes = []
    tier = (await rs._perk_tier(wallet))[0] if wallet else 0
    disc = min(90.0, float(cfg['tierDiscountPct'].get(str(tier), 0)))
    # Badge perk (e.g. Diamond Hands): read from the cached quest summary only, so a quote never waits on it.
    qhit = rs._quest_cache.get(rs.primary_of(wallet)) if wallet else None
    if qhit and qhit[1]['perks']['feeDiscountPct'] > disc:
        disc = min(90.0, qhit[1]['perks']['feeDiscountPct'])
        notes.append(f"{qhit[1]['perks']['from'].get('fee', 'Badge')} badge: {disc:.0f}% off")
    promo = cfg.get('promo') or {}
    if promo.get('discountPct') and rs.time.time() < float(promo.get('until') or 0):
        disc = min(90.0, max(disc, float(promo['discountPct'])))
        notes.append(f"{promo.get('label') or 'Promo'}: {promo['discountPct']:.0f}% off")
    bps = min(round(base * (1 - disc / 100)), rs.SWAP_MAX_BPS)
    if disc and not any(' badge: ' in n for n in notes):
        notes.append(f'{disc:.0f}% holder discount (tier {tier})')
    if (bundle >= 2 or card) and wallet and rs._is_staff(wallet):
        return none('FEELESS card: no FEELESS fee — only network / partner fees.')
    if card and card_id and wallet:   # 💳 a card with prepaid swaps left pays no FEELESS fee on its swaps
        mine_ = set(rs.linked_of(rs.primary_of(wallet))) | {wallet}
        pos_ = next((x for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or [] if x.get('id') == card_id and x.get('wallet') in mine_), None)
        if pos_ and int(pos_.get('prepaidSwaps') or 0) > 0:
            return none(f"Prepaid swap ({pos_['prepaidSwaps']} left) — no FEELESS fee.")
    if card and bundle < 2:   # a card's swap / sell / switch leg: flat $ per coin
        bcfg = rs._hq.clean_bundle(cfg.get('bundle'))
        flat = rs._hq.card_swap_bps(await rs._leg_usd(input_mint, amount), bcfg)
        if flat is not None:
            bps = min(round(flat * (1 - disc / 100)), rs.SWAP_MAX_BPS)
            notes.append(f"Card swap: ${bcfg['swapUsd']:.2f} per coin (max {bcfg['maxPct']:g}% of the leg)")
    if bundle >= 2:
        bcfg = rs._hq.clean_bundle(cfg.get('bundle'))
        flat = rs._hq.bundle_bps(await rs._leg_usd(input_mint, amount), bcfg)
        if flat is not None:
            bps = min(round(flat * (1 - disc / 100)), rs.SWAP_MAX_BPS)
            notes.append(f"Bundle pricing: ${bcfg['perLegUsd']:.2f} per coin (max {bcfg['maxPct']:g}% of the leg)")
    # Ultra can't charge below 0.5%: round a discounted fee up to its minimum instead of waiving it.
    ultra = max(rs.JUP_MIN_BPS, min(bps, rs.JUP_MAX_BPS)) if cfg['referralAccount'] and bps else 0
    out = {'bps': bps, 'ultraBps': ultra, 'baseBps': base, 'notes': notes,
           'referralAccount': cfg['referralAccount'] if ultra else None, 'feeAccount': fee_account if bps else None,
           'feeAccounts': rs._swap_fee_accounts(cfg, input_mint, output_mint) if bps else [],
           'feeAccountsByMint': {m: a for m, a in ((rs.WSOL_MINT, cfg.get('feeAccountSol')), (rs.USDC_MINT, cfg.get('feeAccountUsdc'))) if a and m in (input_mint, output_mint)} if bps else {},
           'feeOwnerSol': rs._fee_owner_sol(cfg.get('feeAccountSol')) if bps else None,
           **eng}
    if bps and not fee_account and eng['engine'] == 'swap':
        # The fee is collected in SOL or USDC. A coin-to-coin trade has neither side, so it can't pay: refuse it
        # rather than let it through free.
        out['blocked'] = 'Every FEELESS trade pays the platform fee in SOL or USDC. Put SOL or USDC on one side (coin → SOL → coin).'
    return out


def _agent_wallets():
    rs = _rs()
    return {(c.get('agentWallet') or {}).get('address') for c in (rs._json_load(rs.DATA_DIR / 'feecats.json', {}).get('cats') or {}).values() if (c.get('agentWallet') or {}).get('circleAcct') == 'agent'}


async def _grow_rows():
    """💰 Every option, read from each venue's own numbers, at most every 5 minutes. A venue that fails only shrinks the list."""
    rs = _rs()
    import grow_board as _gb
    if rs._GROW['rows'] and rs.time.time() - rs._GROW['at'] < 300:
        return rs._GROW['rows']

    async def llama():
        r_ = await rs._fmk_http_get().get('https://yields.llama.fi/pools', timeout=25)
        return _gb.lend_rows((await rs.asyncio.to_thread(rs.json.loads, r_.content)).get('data') if r_.status_code == 200 else [])

    async def stocks():
        r_ = await rs._fmk_http_get().get('https://api.dexscreener.com/latest/dex/search', params={'q': 'xStock'}, timeout=12)
        return _gb.stock_rows(r_.json().get('pairs') if r_.status_code == 200 else [])

    async def planned():
        out_ = []; state_ = rs._cpool.load(rs.POOL_PATH)
        for p_ in (state_.get('pools') or [])[:12]:
            if p_.get('address') and p_.get('mint'):
                out_ += [x_ for x_ in (await rs.familia_pools_ranges(mint=p_['mint'], quote='', top=0, reads=1))['pools'] if x_['pool'] == p_['address']]
        return out_
    top_, lends_, stocks_, plan_ = await rs.asyncio.gather(rs.familia_pools_ranges(mint='', quote='', top=1, reads=1), llama(), stocks(), planned(), return_exceptions=True)
    ok_ = lambda v_: [] if isinstance(v_, BaseException) else v_
    rows_ = _gb.board(ok_(plan_) + (ok_(top_) or {}).get('pools', [] if not isinstance(top_, BaseException) else []) if not isinstance(top_, BaseException) else ok_(plan_), ok_(lends_), ok_(stocks_))
    rs._GROW.update(at=rs.time.time(), rows=rows_, detail={})
    return rows_


def _site_landed(tx, pot):
    """(token, units) a successful transaction really added to the Collective wallet, or None."""
    rs = _rs()
    meta = (tx or {}).get('meta') or {}
    if not tx or meta.get('err') is not None:
        return None
    keys = [str(k.get('pubkey') if isinstance(k, dict) else k) for k in ((tx.get('transaction') or {}).get('message') or {}).get('accountKeys') or []]
    if pot in keys:
        i = keys.index(pot); gain = int((meta.get('postBalances') or [0] * (i + 1))[i]) - int((meta.get('preBalances') or [0] * (i + 1))[i])
        if gain > 0:
            return 'SOL', gain
    bal = lambda rows: sum(int((r.get('uiTokenAmount') or {}).get('amount') or 0) for r in rows or [] if r.get('owner') == pot and r.get('mint') == rs.USDC_MINT)
    gain = bal(meta.get('postTokenBalances')) - bal(meta.get('preTokenBalances'))
    return ('USDC', gain) if gain > 0 else None


def _site_fees_total():
    """Every swap fee FEELESS has really taken from regular traders, from its own ledger."""
    rs = _rs()
    return sum(float(r.get('feeUsd') or 0) for v in (rs._json_load(rs.FEE_LEDGER_PATH, {}) or {}).values() for r in (v or []) if isinstance(r, dict))


async def _collective_view():
    rs = _rs()
    try:
        st = rs._cpool.load(rs.POOL_PATH)
    except rs._cpool.Tampered as e:
        raise rs.HTTPException(503, f'The ledger failed its seal and is locked: {e}')
    px = float(await rs._sol_usd() or 0)
    rows = sorted(((rs._cpool._locked_usd(a, px) + sum(rs._cpool._usd(a['owed'][t], t, px) for t in rs._cpool.TOKENS), c, a) for c, a in st['agents'].items()), key=lambda r: -r[0])[:12]
    return {**rs._stake.owner_view(st, px, rs.time.time()), 'cfg': st['cfg'], 'defaults': rs._cpool.DEFAULTS, 'bounds': rs._cpool.BOUNDS, 'totals': rs._cpool.totals(st, px), 'chain': st.get('chain'), 'solUsd': px, 'wallet': ((rs._json_load(rs.COLONY_PATH, {}) or {}).get('wallet') or {}).get('address'),
            'agents': [{'id': c, 'name': a.get('name'), 'owner': (a.get('owner') or '')[:6], **{k: v for k, v in rs._cpool.view(st, c, st.get('at') or 0, px).items() if k in ('lockedUsd', 'owedUsd', 'sentUsd', 'earnedUsd', 'boost', 'levers')}} for _, c, a in rows], 'log': (st.get('cfgLog') or [])[::-1], 'withdrawals': False, 'site': {'feesUsd': round(rs._site_fees_total(), 4), 'movedUsd': round(float(st.get('siteMovedUsd') or 0), 4), 'owedUsd': rs._cpool.site_owed(st['cfg'], rs._site_fees_total(), st.get('siteMovedUsd'))}, 'held': [{'cat': c, 'name': a.get('name'), **{k: r.get(k) for k in ('id', 'sym', 'at', 'review', 'sig')}} for c, a in st['agents'].items() for r in a.get('streams') or [] if r.get('held')][:30], 'reviewed': sum(1 for a in st['agents'].values() for r in a.get('streams') or [] if r.get('review')), 'hist': (st.get('hist') or [])[-180:], 'audit': st.get('auditNow'), 'head': st.get('head'), 'links': st.get('links') or 0, 'potKinds': list(rs._cpool.POT_KINDS)}


def _rounds_cfg():
    rs = _rs()
    return rs._hq.clean_rounds_cfg(rs._fee_cfg().get('rounds'))


async def _rounds_pay_to():
    """🔁 Where round packs are paid: the wallet that owns the SOL fee account (on-chain, cached 10 min)."""
    rs = _rs()
    if rs.time.time() - rs._rounds_pay_cache['at'] < 600:
        return rs._rounds_pay_cache['to']
    try:
        async with rs.httpx.AsyncClient(timeout=10) as http:
            to = await rs._fee_wallet_owner(http, rs._fee_cfg())
    except Exception:
        to = None
    rs._rounds_pay_cache.update(at=rs.time.time(), to=to)
    return to


async def _fuse_rounds(p):
    """🔁 +5 rounds on YOUR card: 'pay' = a confirmed SOL transfer YOU signed to the fee wallet (checked on-chain, never reused);
    'compound' = rounds now, the card owes the price until its next profit take; 'settle' = pay what the card owes."""
    rs = _rs()
    me = rs._session_or_401(p.address, p.session)
    mine = set(rs.linked_of(me)) | {me}
    cfg = rs._rounds_cfg(); paid_usd = 0.0
    if p.mode in ('pay', 'settle') and (cfg['per5Usd'] > 0 or p.mode == 'settle'):
        if not rs._re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', p.signature or ''):
            raise rs.HTTPException(400, 'Send the payment first — no signature yet.')
        to = await rs._rounds_pay_to()
        if not to:
            raise rs.HTTPException(503, 'Fee wallet not set — rounds cannot be bought right now.')
        tx = None
        async with rs.httpx.AsyncClient(timeout=20) as http:
            for _ in range(5):
                tx = await rs._rpc(http, 'getTransaction', [p.signature, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
                if tx:
                    break
                await rs.asyncio.sleep(2)
        lam = max((rs._hq.paid_lamports(tx, w, to) for w in mine), default=0)
        paid_usd = lam / 1e9 * (await rs._sol_usd_live() or 0)
        if paid_usd <= 0:
            raise rs.HTTPException(400, 'No confirmed SOL payment from your wallet to the fee wallet in that transaction.')
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise rs.HTTPException(404, 'Open card not found.')
        try:
            if p.mode == 'settle':
                rs._hq.settle_owed(pos, paid_usd)
            else:
                rs._hq.extend_rounds(pos, p.mode, cfg, paid_usd, rs.time.time(), p.signature)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        if p.signature:
            d['roundSigs'] = (d.get('roundSigs') or [])[-500:] + [p.signature]
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return {'ok': True, 'roundsLeft': rs._hq.rounds_left(pos), 'roundsOwedUsd': pos.get('roundsOwedUsd') or 0}


def _house():
    rs = _rs()
    h_ = rs._fee_cfg().get('house') or {}
    return {**rs.HOUSE_DEFAULTS, **{k_: h_[k_] for k_ in rs.HOUSE_DEFAULTS if h_.get(k_) is not None}}


async def _swap_fee_health():
    """Swap API engine: each fee account must be a live token account for its coin (wSOL / USDC)."""
    rs = _rs()
    cfg = rs._fee_cfg()
    wanted = [(label, acct, mint) for label, acct, mint in (('SOL', cfg.get('feeAccountSol'), rs.WSOL_MINT), ('USDC', cfg.get('feeAccountUsdc'), rs.USDC_MINT)) if acct]
    if not wanted:
        return {'ok': False, 'problem': 'No fee account set, so the Swap engine collects nothing.',
                'fix': 'Create a wSOL token account owned by your treasury wallet (e.g. spl-token create-account So11111111111111111111111111111111111111112) and paste it.'}
    async with rs.httpx.AsyncClient(timeout=20) as http:
        info = await rs._rpc(http, 'getMultipleAccounts', [[a for _, a, _ in wanted], {'encoding': 'jsonParsed'}])
    for (label, acct, mint), value in zip(wanted, (info or {}).get('value') or [None] * len(wanted)):
        parsed = (((value or {}).get('data') or {}).get('parsed') or {}) if isinstance((value or {}).get('data'), dict) else {}
        if not value or value.get('owner') not in rs.TOKEN_PROGRAMS or parsed.get('type') != 'account':
            return {'ok': False, 'problem': f'{label} fee account {acct[:6]}… is not a token account on-chain.', 'fix': f'Create a {label} token account for your treasury and paste that address.'}
        if (parsed.get('info') or {}).get('mint') != mint:
            return {'ok': False, 'problem': f'{label} fee account holds a different coin.', 'fix': f'Use a token account whose mint is {mint}.'}
    fallback = 'on' if cfg.get('ultraFallback') else 'off'
    return {'ok': True, 'note': f"Swap engine ready: fees land in your {' + '.join(l for l, _, _ in wanted)} fee account(s). Ultra fallback {fallback}."}

