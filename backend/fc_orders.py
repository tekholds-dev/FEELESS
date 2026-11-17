"""🧹 Public cat, orders, credit, recovery — moved whole out of feecat_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches feecat_service still
reaches it, and every function here is still reachable on feecat_service under its own name. Constants, classes and state live in the service."""
import feecat_service as _RSM  # noqa: E402,F401  (body models; this module is imported at the END of the service)
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401

router = APIRouter()


def _rs():
    import feecat_service
    return feecat_service


def public_cat(cat):
    """The visitor's copy of an agent. Pure (tests)."""
    rs = _rs()
    b = cat.get('brainsCfg') or {}
    out = {k: cat[k] for k in rs.PUBLIC_CAT_KEYS if k in cat}
    if b:
        out['brainsCfg'] = {'kind': b.get('kind'), 'brains': list(b.get('brains') or [])[:2], 'cloud': list(b.get('cloud') or [])[-8:]}
    if cat.get('agentWallet'):
        out['hasWallet'] = True   # 👛 a real wallet exists — its address stays its owner's (S2 lock)
    if not cat.get('incognito'):   # 👀 its proofs show to visitors, with every email and phone number taken out
        for k_ in ('powFolders', 'popFolders', 'pobFolders', 'pocFolders', 'psFolders'):
            if cat.get(k_):
                out[k_] = [{**rs._vv.public_folder(f_), 'stamp': rs._stamp.of({'powFolders': 'PoW', 'popFolders': 'PoP', 'pobFolders': 'PoB', 'pocFolders': 'PoB', 'psFolders': 'PoB'}[k_], f_, rs.time.time())} for f_ in (cat.get(k_) or [])[-30:]]
    return out


async def _order_pair(http, coin):
    """An order's coin → its deepest Solana pool (a mint → DexScreener /tokens; a symbol → /search)."""
    rs = _rs()
    try:
        if rs.re.fullmatch(rs._co.MINT, str(coin)):
            r = await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{coin}')
        else:
            r = await http.get('https://api.dexscreener.com/latest/dex/search', params={'q': str(coin).lstrip('$')})
        return rs._co.best_pair((r.json() or {}).get('pairs') or [], coin)
    except Exception:
        return None


async def _run_order(store, cat, text, http):
    """🧭 A General cat's order: understood (words first, its brain only when the words don't parse) → guarded → REAL = a proposal your wallet
    signs · paper = a paper fill. → the order-log row (also on cat['orders'])."""
    rs = _rs()
    rs._OR_CAT.set(cat.get('id'))
    now = rs.time.time()
    b = cat.get('brainsCfg') or {}
    rs.ensure_real(cat)
    order = rs._co.parse_order(text)
    if not order and rs._brains_live() and rs._lc.can_ask(b) and b.get('brains'):
        reply, usd = await rs._or_call(b['brains'][0], [{'role': 'system', 'content': rs._co.ORDER_SYS}, {'role': 'user', 'content': str(text)[:300]}])
        rs._lc.charge(b, usd)
        order = rs._co.order_from_json(reply)
    if not order:
        return rs._co.note(cat, text, None, 'unclear', '🤔 not a buy or a sell of one coin — try "buy 0.05 SOL of $BONK" or "sell half of $WIF"', now)
    if order['side'] == 'sell':
        c_ = str(order['coin']).lstrip('$').lower()
        real_ = next(((m, v) for m, v in (cat.get('realHeld') or {}).items() if m.lower() == c_ or str(v.get('symbol') or '').lower() == c_), None) if rs._real.is_real(cat) else None
        if real_:   # a coin its own wallet really holds
            p_ = rs._real.propose(cat, 'sell', real_[0], real_[1].get('pair'), real_[1].get('symbol'), f"your order: {text}", now, fraction=order['fraction'])
            rs._notify_real(cat, p_)
            return rs._co.note(cat, text, order, 'proposed', f"✍ sell {round(order['fraction'] * 100)}% — {rs._order_wait(cat)}", now, real_[1].get('symbol'), p_['id'])
        pos = rs._co.held_of(cat.get('positions'), order['coin'])
        if not pos:
            return rs._co.note(cat, text, order, 'refused', f"🫥 it holds no ${order['coin']}", now, order['coin'])
        if rs._real.is_real(cat):
            p_ = rs._real.propose(cat, 'sell', pos.get('mint'), pos.get('pairAddress'), pos.get('symbol'), f"your order: {text}", now, fraction=order['fraction'], px=pos.get('lastPx'))
            if not p_:
                return rs._co.note(cat, text, order, 'refused', '🫥 nothing real behind that coin to sell', now, pos.get('symbol'))
            rs._notify_real(cat, p_)
            return rs._co.note(cat, text, order, 'proposed', f"✍ sell {round(order['fraction'] * 100)}% — waiting for your wallet's signature", now, pos.get('symbol'), p_['id'])
        live = (await rs._pair_prices(http, [pos['pairAddress']])).get(pos['pairAddress']) or {}
        px = rs._num(live.get('priceNative')) or rs._num(pos.get('lastPx'))
        if not px:
            return rs._co.note(cat, text, order, 'refused', '📡 no live price right now — try again in a minute', now, pos.get('symbol'))
        if order['fraction'] >= 0.999:
            cat['positions'].remove(pos)
        rs._close(store, cat, pos, px, f"🧭 your order: {text}", order['fraction'], rs._num(live.get('marketCap') or live.get('fdv')))
        return rs._co.note(cat, text, order, 'filled', f"📄 paper: sold {round(order['fraction'] * 100)}% at the live price", now, pos.get('symbol'))
    p = await rs._order_pair(http, order['coin'])
    ok, why = rs._co.buy_guards(p, now * 1000)
    if not ok:
        return rs._co.note(cat, text, order, 'refused', why, now, order['coin'])
    sym = (p.get('baseToken') or {}).get('symbol') or order['coin']
    safe, swhy, _conv = await rs._safety(http, p, cat)
    if not safe:
        return rs._co.note(cat, text, order, 'refused', f'🛡 {swhy}', now, sym)
    real = rs._real.is_real(cat)
    sol, capped = rs._co.size_of(order, rs._num((cat.get('risk') or {}).get('maxPositionSol')) or None, cat.get('budgetSol') if real else None)
    px = rs._num(p.get('priceNative'))
    if real:
        p_ = rs._real.propose(cat, 'buy', (p.get('baseToken') or {}).get('address'), p.get('pairAddress'), sym, f"your order: {text}", now, sol=sol, px=px)
        if not p_:
            return rs._co.note(cat, text, order, 'refused', '🫥 could not build the proposal', now, sym)
        rs._notify_real(cat, p_)
        return rs._co.note(cat, text, order, 'proposed', f"✍ buy {p_['sol']:g} SOL{capped} — guards passed, {rs._order_wait(cat)}", now, sym, p_['id'])
    if sol <= 0 or cat.get('balanceSol', 0) < sol or not px:
        return rs._co.note(cat, text, order, 'refused', f"💰 paper balance {cat.get('balanceSol', 0):.3f} SOL — not enough for {sol:g} SOL", now, sym)
    cat['balanceSol'] = round(cat['balanceSol'] - sol, 6)
    cat['positions'].append({'mint': (p.get('baseToken') or {}).get('address'), 'pairAddress': p.get('pairAddress'), 'symbol': sym, 'provider': 'DexScreener',
                             'url': p.get('url'), 'costSol': sol, 'notionalSol': round(sol * (1 - rs.fee_side()), 6), 'entryPriceNative': px, 'entryPriceUsd': p.get('priceUsd'),
                             'entryChange': 0, 'currentChange': 0, 'peakChange': 0, 'openedAt': now, 'reason': rs.public_words(f'🧭 your order: {text}'),
                             'entryLiq': rs._num((p.get('liquidity') or {}).get('usd')), 'conviction': 1.0, 'entryMarketCapUsd': rs._num(p.get('marketCap') or p.get('fdv')),
                             'entryVolH1': rs._num((p.get('volume') or {}).get('h1')), 'plannedSol': sol, 'firstEntryPriceNative': px, 'adds': 0, 'profitTaken': 0,
                             'peakPx': px, 'order': True})
    rs._log_event(store, cat, 'BUY', f"Bought {sol} SOL of {sym} at live price — 🧭 your order (paper).", None, p.get('pairAddress'), px, rs._num(p.get('marketCap') or p.get('fdv')))
    return rs._co.note(cat, text, order, 'filled', f"📄 paper: bought {sol:g} SOL{capped} at the live price — guards passed", now, sym)


def owner_wallets():
    rs = _rs()
    return [w.strip() for w in rs.os.environ.get('FEELESS_ADMIN_WALLETS', '').split(',') if w.strip()]


async def _staff_heal(wait=20):
    """👑 Once after a start (reputation up first): an older agent learns whether its owner wallet is the creator / an HQ admin — they run on the
    cheapest models first, a user's agent on OpenRouter first."""
    rs = _rs()
    await rs.asyncio.sleep(wait)
    store = rs._load(); n = 0
    for c in store['cats'].values():
        if 'ownerStaff' not in c and rs.owner_wallet(c):
            c['ownerStaff'] = await rs._is_creator(rs.owner_wallet(c)); rs.keep_owned(c); n += 1
    if n:
        rs._save(store)


async def _is_creator(addr):
    """👑 the creator through ANY linked wallet (reputation's `_is_staff`) — Fee's real switch is the creator's, whichever of their wallets signed."""
    rs = _rs()
    try:
        async with rs.httpx.AsyncClient(timeout=5) as h:
            r = await h.get(f'http://127.0.0.1:5077/api/reputation/admin/is-admin/{addr}')
            return bool(r.status_code == 200 and (r.json().get('staff') or r.json().get('owner')))
    except Exception:
        return False


def free_credit_ok(cat, creator=False):
    """💳 Live model credit costs real money: a real agent buys it (/cats/{id}/fund, purpose credit); only a paper rule cat or a creator wallet refills free.
    🧭 A GENERAL agent never gets free credit — not even staff (owner 2026-10-31: "staff use paper only for trading bots, never general agents")."""
    if (cat.get('brainsCfg') or {}).get('kind') == 'general':
        return False
    return bool(creator or not cat.get('agentWallet'))


def real_credit(cat):
    """🧭 A general agent's credit = only the money that really bought it (creditPaid, never a `creator-` grant) less what it spent; never more than it shows."""
    rs = _rs()
    b = cat.get('brainsCfg') or {}
    paid = sum(rs._num(x.get('usd')) or 0.0 for x in cat.get('creditPaid') or [] if not str(x.get('sig') or '').startswith('creator-'))
    return round(max(0.0, min(rs._num(b.get('credit')) or 0.0, paid - (rs._num(b.get('spent')) or 0.0))), 6)


def heal_general_credit(store):
    """One pass at startup: every general agent's credit drops any free grant (the old $10 start, a creator top-up). Returns the ids it changed."""
    rs = _rs()
    changed = []
    for c in (store.get('cats') or {}).values():
        b = c.get('brainsCfg') or {}
        if b.get('kind') != 'general':
            continue
        real = rs.real_credit(c)
        if real != round(rs._num(b.get('credit')) or 0.0, 6):
            b['credit'] = real
            changed.append(c.get('id'))
    return changed


def fee_owner_real(cat, action, signed, owners=None):
    """💵🐱 FEE GOES REAL — owner only (2026-10-23: "see NEXA trade real money as FeeCat"): Fee belongs to the system, so only a signed-in OWNER
    wallet (FEELESS_ADMIN_WALLETS — never a granted role) may switch her real / paper or answer her proposals. Real = every buy NEXA calls is
    a proposal that wallet signs (≤ its per-buy budget); FEELESS never moves the money. Pure (tests)."""
    rs = _rs()
    return bool(cat.get('isLeader') and action in ('real', 'paper', 'proposal', 'look') + rs._LEADER_AGENT and signed and signed in (rs.owner_wallets() if owners is None else owners))


def clean_fee_look(look):
    """🎨 The creator's look for Fee (owner, 2026-10-23: "creator controls Fee — coat / gear / eyes / name"): each part one short lowercase key
    (the page draws only keys it knows — an unknown one falls back to her default), her name ≤ 24 chars, her title ≤ 48. Pure (tests)."""
    rs = _rs()
    l = look if isinstance(look, dict) else {}
    out = {k: str(l[k]).lower()[:16] for k in rs.LOOK_KEYS if rs.re.fullmatch(r'[A-Za-z0-9-]{1,16}', str(l.get(k) or ''))}
    for k, n in (('name', 24), ('title', 48)):
        v = ' '.join(rs.re.sub(r'[<>{}\[\]]', '', str(l.get(k) or '')).split())[:n]
        if v:
            out[k] = rs.public_words(v)
    return out


@router.post('/api/cats/{cat_id}/recovery-pin')
async def cat_recovery_pin(cat_id: str, payload: _RSM.ActionPayload):
    """🔑 Its recovery PIN: made once, shown once, only the hash kept. A lost PIN can only be replaced by the owner's browser (`text` = 'replace')."""
    rs = _rs()
    store = rs._load()
    cat = store['cats'].get(cat_id)
    if not cat or cat.get('isLeader'):
        raise rs.HTTPException(404, 'Cat not found.')
    rs._owner_gate(store, cat, payload.session, payload.ownerId, 'make its recovery PIN')
    if cat.get('recovery') and payload.text != 'replace':
        raise rs.HTTPException(409, 'Its recovery PIN was already shown once.')
    pin = rs._recovery.new_pin()
    cat['recovery'], cat['recoverySet'] = rs._recovery.seal(pin), True
    rs.keep_owned(cat); rs._save(store)
    return {'pin': pin}


@router.post('/api/cats/{cat_id}/recovery-kit')
async def cat_recovery_kit(cat_id: str, payload: _RSM.ActionPayload):
    """🔑 Make or rotate its recovery key or its 12 words. Shown once, only a slow one-way hash kept. Rotating kills the old one at once."""
    rs = _rs()
    store = rs._load(); cat = store['cats'].get(cat_id); kind = str(payload.text or '')
    if not cat or cat.get('isLeader') or kind not in rs._rkit.KINDS:
        raise rs.HTTPException(404, 'Cat not found.')
    rs._owner_gate(store, cat, payload.session, payload.ownerId, 'make its recovery key or words')
    secret = rs._rkit.new_key() if kind == 'key' else rs._rkit.new_phrase()
    kit = cat.setdefault('recoveryKit', {}); kit[kind] = rs._rkit.seal(kind, secret, rs.time.time())
    rs.keep_owned(cat); rs._save(store)
    return {'kind': kind, 'secret': secret, 'kit': rs._rkit.view(kit)}


async def _key_check(provider, secret):
    """One free call that proves a key works, never a paid one: Kalshi reads the balance; fal asks the status of a request that does not exist
    (a refused key answers 401 / 403, an accepted one anything else). → {ok, why, at}."""
    rs = _rs()
    try:
        async with rs.httpx.AsyncClient(timeout=12) as h_:
            if provider == 'kalshi':
                kid_, pem_ = rs._kb.split_key(secret)
                if not kid_:
                    return {'ok': False, 'why': 'The key id or the private key did not read right.', 'at': round(rs.time.time())}
                return {'ok': True, 'why': f'Kalshi answered: balance ${await rs._kb.balance(h_, kid_, pem_):.2f}', 'at': round(rs.time.time())}
            r_ = await h_.get('https://queue.fal.run/fal-ai/flux/requests/00000000-0000-0000-0000-000000000000/status', headers={'Authorization': f'Key {secret}'})
            return {'ok': r_.status_code not in (401, 403), 'why': 'fal accepted the key (checked without spending)' if r_.status_code not in (401, 403) else f'fal refused this key ({r_.status_code})', 'at': round(rs.time.time())}
    except Exception as e:   # noqa: BLE001 — the key stays sealed; the reason is shown
        return {'ok': False, 'why': str(e)[:180], 'at': round(rs.time.time())}


@router.post('/api/cats/{cat_id}/action')
async def cat_action(cat_id: str, payload: _RSM.ActionPayload, request: Request):
    rs = _rs()
    rs._OR_CAT.set(cat_id)   # 🧾 its model calls' receipts carry this agent
    if payload.action in rs._INTERNAL_ONLY:   # 🔒 2026-11-12 audit #1: a signed-in owner could post a made-up payment and get free model credit
        rs._internal(request)
    store = rs._load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise rs.HTTPException(404, 'Cat not found.')
    signed = rs._real.session_wallet(rs._real.load_sessions(rs.DATA_DIR / 'chat_sessions.json'), payload.session)
    if cat.get('isLeader') and payload.action in ('real', 'paper', 'proposal', 'look') + rs._LEADER_AGENT and not request.headers.get('x-feeless-internal'):
        if not signed:   # a missing / expired sign-in used to fall through to the internal-key check and read as a mystery 403
            raise rs.HTTPException(401, 'Sign in with your wallet first (one signature, no transaction) — your sign-in expired.')
        if not rs.fee_owner_real(cat, payload.action, signed) and not await rs._is_creator(signed):
            raise rs.HTTPException(403, "Only the creator's wallets can switch Fee real — this wallet isn't linked to the creator.")
    elif not rs.fee_owner_real(cat, payload.action, signed) and not request.headers.get('x-feeless-internal'):   # 🔒 the signed-in owner wallet only …
        rs._owner_gate(store, cat, payload.session, payload.ownerId)
    elif not rs.fee_owner_real(cat, payload.action, signed):
        rs._internal(request)                                             # … or HQ (reputation's admin run, internal key)
    if payload.action in ('real', 'proposal', 'agent_wallet', 'agent_mode', 'agent_approve', 'agent_assign') and (not signed or signed != payload.address):
        raise rs.HTTPException(401, 'Sign in with your wallet first (one signature, no transaction).')

    if payload.action == 'real':   # 💵 option A: the cat proposes, this wallet signs every trade
        try:
            rs._real.go_real(cat, signed, payload.budgetSol, rs.time.time()); cat.pop('paperByOwner', None)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs._log_event(store, cat, 'STARTED', f"{cat['name']} is REAL now: it proposes every trade to your wallet (≤ {cat['budgetSol']} SOL a buy); you sign each one.")
    elif payload.action == 'paper':
        rs._real.go_paper(cat); cat['paperByOwner'] = True
        rs._log_event(store, cat, 'STOPPED', f"{cat['name']} is back on paper — no more proposals.")
    elif payload.action == 'agent_wallet':   # 👛 its own Crossmint wallet (DECISIONS #2, owner 2026-10-29): the same wallet on a repeat
        if not cat.get('agentWallet'):
            mine_ = sum(1 for c_ in store['cats'].values() if (c_.get('agentWallet') or {}).get('owner') == signed)
            if mine_ >= rs._AGENT_MAX:
                raise rs.HTTPException(400, f'Up to {rs._AGENT_MAX} cats with their own wallet per owner — you have {mine_}.')
            try:
                async with rs.httpx.AsyncClient(timeout=40) as http_w:
                    if rs.os.environ.get('CIRCLE_AGENT_API_KEY', '').strip():   # 🟦 the separate Circle account for family + agent wallets (never the FEELESS creator account)
                        rc_ = await http_w.post('http://127.0.0.1:5077/api/reputation/internal/agent-circle-wallet', headers=rs._internal_headers(), json={'catId': cat_id})
                        if rc_.status_code != 200:
                            raise ValueError(f"Circle did not make the wallet: {str((rc_.json() if rc_.content else {}).get('detail') or rc_.status_code)[:140]}")
                        w_ = rc_.json().get('wallet') or {}
                        store = rs._load(); cat = store['cats'][cat_id]   # the call took seconds: work on the store as it is now
                        cat['agentWallet'] = {**rs._aw.record('cat', cat_id, {'address': w_.get('address'), 'locator': f"circle:{w_.get('id')}"}, signed, rs.time.time(), (cat.get('brainsCfg') or {}).get('kind')),
                                              'provider': 'circle', 'circleAcct': 'agent', 'circleId': w_.get('id')}
                    else:
                        rep_ = await rs._aw.create(http_w, rs.os.environ.get('CROSSMINT_API_KEY', '').strip(), 'cat', cat_id)
                        cat['agentWallet'] = rs._aw.record('cat', cat_id, rep_, signed, rs.time.time(), (cat.get('brainsCfg') or {}).get('kind'))
            except ValueError as e:
                raise rs.HTTPException(400, str(e))
            rs.ensure_real(cat)
            rs._log_event(store, cat, 'STARTED', f"{cat['name']} has its own wallet now: {cat['agentWallet']['address'][:6]}… — fund it to put it to work.")
    elif payload.action == 'agent_withdrew':   # ↩ reputation's /cats/{id}/withdraw (internal key only): the money went back to the owner's wallet
        a_ = payload.amount if isinstance(payload.amount, dict) else {}
        rs._log_event(store, cat, 'WITHDRAW', f"{a_.get('amount')} {a_.get('token')} sent back to its owner's wallet ({str(payload.sig)[:10]}…).")
        store['events'][0]['sig'] = str(payload.sig or '')[:100]   # the FULL signature, so a staff strike can check this exact transaction on chain
    elif payload.action == 'event_void':   # ✗ reputation's staff strike (internal key only, after it proved on chain the money move never landed)
        ev_ = next((e for e in store['events'] if e.get('id') == payload.sig and e.get('catId') == cat_id), None)
        if not ev_:
            raise rs.HTTPException(404, 'No such line on this agent.')
        ev_['voided'] = {'why': str(payload.text or 'never landed on chain')[:200], 'at': round(rs.time.time())}
    elif payload.action == 'agent_funded':   # 💵 reputation's /cats/{id}/fund/send (internal key only — the branch above): a verified, sent funding
        a_ = payload.amount if isinstance(payload.amount, dict) else {}
        if not payload.sig or any(str(x.get('sig')) == payload.sig for x in (cat.get('agentFunded') or []) + (cat.get('creditPaid') or [])):
            raise rs.HTTPException(400, 'No signature, or that funding is on the record already.')
        if payload.result != 'confirmed':
            raise rs.HTTPException(400, 'Funding must be confirmed on-chain before credit is recorded.')
        if isinstance(a_.get('deposit'), dict):   # 💵 what this deposit paid, and what counts toward the every-3rd rule
            cat['deposits'] = (list(cat.get('deposits') or []) + [{'sig': str(payload.sig)[:100], 'usd': rs._num(a_.get('usd')), 'at': round(rs.time.time()), **{k: a_['deposit'].get(k) for k in ('ratePct', 'feelessUsd', 'collectiveUsd', 'third')}}])[-200:]
        cr_ = max(0.0, rs._num(a_.get('creditUsd')) or 0.0)
        if cr_:   # 🧠 the model-credit share of this payment
            cat['creditPaid'] = (list(cat.get('creditPaid') or []) + [{'sig': str(payload.sig)[:100], 'usd': cr_, 'token': a_.get('token'), 'at': round(rs.time.time())}])[-50:]
            if cat.get('brainsCfg'):
                cat['brainsCfg']['credit'] = round((cat['brainsCfg'].get('credit') or 0) + cr_, 6); cat.pop('brainPaused', None)
            rs._log_event(store, cat, 'STARTED', f"{cat['name']}: ${cr_:g} of model credit added.")
        if not a_.get('catLamports'):   # all of it was credit: no wallet funding on the record
            rs.keep_owned(cat); rs._save(store)
            return {'cat': {**rs._no_keys(cat), 'mine': not cat.get('isLeader')}}
        cat['agentFunded'] = (list(cat.get('agentFunded') or []) + [{'sig': str(payload.sig)[:100], 'state': payload.result or 'confirmed', 'at': round(rs.time.time()),
                              **{k: a_.get(k) for k in ('usd', 'feeUsd', 'catLamports', 'feeLamports', 'solUsd', 'token')}}])[-50:]
        rs.ensure_real(cat)   # funded: its orders now use its wallet
        got_ = f"{(a_.get('catLamports') or 0) / 1e6:.2f} USDC" if a_.get('token') == 'USDC' else f"{round((a_.get('catLamports') or 0) / 1e9, 4)} SOL"
        rs._log_event(store, cat, 'STARTED', f"{cat['name']} funded: ${a_.get('usd')} — {got_} into its wallet"
                   + (f" (one-time FEELESS fee ${a_.get('feeUsd'):g})" if a_.get('feeUsd') else '') + '.')
    elif payload.action == 'agent_assign':   # 👛 N16: Fee takes a wallet the creator already has (a user's cat always gets a fresh one)
        if not cat.get('isLeader'):
            raise rs.HTTPException(400, 'Only Fee takes an assigned wallet — your own cats get a fresh wallet of their own.')
        addr_ = str(payload.text or '').strip()
        try:
            async with rs.httpx.AsyncClient(timeout=15) as http_l:
                rep_ = await rs._aw.lookup(http_l, rs.os.environ.get('CROSSMINT_API_KEY', '').strip(), addr_)
            cat['agentWallet'] = rs._aw.assigned(addr_, rep_, signed, rs.time.time())
            if rep_ is None:   # 🟦 not Crossmint's — one of the creator's own CIRCLE wallets? then Circle signs and she trades from it
                async with rs.httpx.AsyncClient(timeout=15) as http_c:
                    rc_ = await http_c.get('http://127.0.0.1:5077/api/reputation/internal/circle-wallet', params={'address': addr_}, headers=rs._internal_headers())
                if rc_.status_code == 200 and (rc_.json() or {}).get('id'):
                    cat['agentWallet'].update(provider='circle', circleId=rc_.json()['id'])
        except (ValueError, rs.httpx.HTTPError) as e:
            raise rs.HTTPException(400, str(e))
        prov_ = cat['agentWallet'].get('provider')
        rs._log_event(store, cat, 'STARTED', f"{cat['name']}'s wallet is {addr_[:6]}… — " + ('she trades from it (Crossmint holds its key).' if prov_ == 'crossmint'
                   else 'she trades from it (your Circle wallet — Circle signs, inside her caps).' if prov_ == 'circle'
                   else "WATCH-ONLY: neither Crossmint nor your Circle project holds its key, so she shows it but never trades from it."))
    elif payload.action == 'pass_minted':   # 🎫 internal only (reputation checked the mint on-chain): its Agent Pass, shown on its card
        if not request.headers.get('x-feeless-internal'):
            raise rs.HTTPException(403, 'Only FEELESS records a Pass, after checking it on-chain.')
        pi = payload.passInfo or {}
        cat['pass'] = {'number': int(pi.get('number') or 0), 'asset': str(pi.get('asset') or '')[:44], 'sig': str(pi.get('sig') or '')[:100], 'owner': str(pi.get('owner') or '')[:44], 'at': round(rs.time.time())}
        rs._log_event(store, cat, 'STARTED', f"{cat['name']} got Agent Pass #{cat['pass']['number']:04d}.")
    elif payload.action == 'treasury':   # 🏦 its coin + how its creator fees split (owner only — the gate above)
        t_ = payload.treasury or {}
        mint_ = str(t_.get('mint') or '').strip()
        if mint_ and not rs.re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', mint_):
            raise rs.HTTPException(400, 'That is not a Solana coin address.')
        cat['treasury'] = {'mint': mint_, 'split': rs._tr.clean_split(t_.get('split')), 'at': round(rs.time.time())}
    elif payload.action == 'earn':   # ⚡ Earn Mode on / off + its risk and the $ it plans for (it never signs — Launch › Pools does)
        cat['earn'] = rs._em.clean(payload.earn)
        rs._log_event(store, cat, 'STARTED' if cat['earn']['on'] else 'STOPPED', f"{cat['name']}: Earn Mode {'on' if cat['earn']['on'] else 'off'} · {cat['earn']['risk']}.")
    elif payload.action == 'agent_mode':   # 👛 a GENERAL cat: approve every AI move, or let it do its thing
        if not cat.get('agentWallet'):
            raise rs.HTTPException(400, 'Make its wallet first.')
        try:
            cat['agentWallet'] = rs._aw.set_mode(cat['agentWallet'], payload.mode, (cat.get('brainsCfg') or {}).get('kind'))
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs._log_event(store, cat, 'STARTED', f"{cat['name']}: {'does its thing — AI moves go ahead on its own' if payload.mode == 'auto' else 'asks first — every AI move waits for your OK'}.")
    elif payload.action == 'agent_approve':   # ✋ ASK ME: the owner's OK on one proposal → its wallet sends it on the engine's next pass
        p_ = next((x for x in cat.get('proposals') or [] if x.get('id') == payload.proposal), None)
        if not (cat.get('agentWallet') or {}).get('address') or not p_ or p_.get('status') != 'pending':
            raise rs.HTTPException(400, 'Nothing waiting to approve.')
        p_['approved'], p_['approvedBy'] = rs.time.time(), signed
        rs._log_event(store, cat, 'TRADE', f"{cat['name']}: you approved {p_['side'].upper()} ${p_.get('symbol')} — its wallet sends it now.")
    elif payload.action == 'proposal':
        if signed != cat.get('realWallet'):
            raise rs.HTTPException(403, "Only the agent's real wallet answers its proposals.")
        try:
            rs._real.resolve(cat, payload.proposal, payload.result, rs.time.time(), payload.sig)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
    elif payload.action == 'confirm_recovery':   # 🔐 the owner ticked "I saved my recovery phrase" before the first funding (kept as a timestamp)
        cat['recoveryConfirmedAt'] = rs.time.time()
    elif payload.action == 'api_key':   # 🔐 the API drawer: seal one key (or remove it) — the response carries the last 4 only
        try:
            rs._ck.put(cat, payload.provider, payload.secret, data_dir=rs.DATA_DIR) if payload.secret else rs._ck.drop(cat, payload.provider)
        except (ValueError, RuntimeError) as e:
            raise rs.HTTPException(400, str(e))
        if payload.secret and payload.provider in ('kalshi', 'fal'):   # 🔑 owner 2026-11-11 "assure it's ready": one free live call the moment it is sealed
            cat['apiKeys'][payload.provider]['check'] = await rs._key_check(payload.provider, str(payload.secret).strip())
    elif payload.action == 'openrouter_connect':   # 🔑 owner 2026-11-10: one-click Connect OpenRouter. OpenRouter's sign-in code + this tab's verifier → a key made for FEELESS, sealed here; it never goes back to the page
        code_, verifier_ = str(payload.secret or '').strip(), str(payload.text or '').strip()
        if not code_ or not 20 <= len(verifier_) <= 128:
            raise rs.HTTPException(400, 'Connect OpenRouter again: the approval came back incomplete.')
        try:
            async with rs.httpx.AsyncClient(timeout=20) as h_:
                r_ = await h_.post('https://openrouter.ai/api/v1/auth/keys', json={'code': code_, 'code_verifier': verifier_, 'code_challenge_method': 'S256'})
        except rs.httpx.HTTPError:
            raise rs.HTTPException(502, 'OpenRouter did not answer. Try Connect again in a minute.')
        key_ = (r_.json() if r_.status_code == 200 else {}).get('key') if r_.headers.get('content-type', '').startswith('application/json') else None
        if not key_:
            raise rs.HTTPException(400, 'OpenRouter did not accept that approval (it works once, for a few minutes). Press Connect OpenRouter again.')
        try:
            rs._ck.put(cat, 'openrouter', key_, data_dir=rs.DATA_DIR)
        except (ValueError, RuntimeError) as e:
            raise rs.HTTPException(400, str(e))
    elif payload.action == 'venues':   # 📈 where a trading cat trades — FEELESS rails only
        try:
            cat['venues'] = rs._ck.venues(payload.venues)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
    elif payload.action == 'chime':   # 🚀 the owner's advice — the brain reads it, it never trades on it
        if not cat.get('brainsCfg'):
            raise rs.HTTPException(400, 'This Agent has no AI brain.')
        try:
            rs._lc.chime(cat['brainsCfg'], payload.text)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
    elif payload.action == 'talk':   # 💬 the owner talks with one mind or both: each picked mind answers in its own bubble (owner 2026-11-07: "dont have option for which")
        b_ = cat.get('brainsCfg')
        if not b_:
            raise rs.HTTPException(400, 'This Agent has no AI brain.')
        who_ = rs.talk_targets(b_, payload.to)
        if not who_:
            raise rs.HTTPException(400, 'Pick a mind it has.')
        if b_.get('talkWait') and rs.time.time() - float(b_.get('talkAt') or 0) < rs.TALK_S + 30:   # a restart mid-reply never locks the chat
            raise rs.HTTPException(409, 'Still answering your last message.')
        try:
            rs._lc.chime(b_, payload.text)
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        b_['chime'][-1]['to'] = 'both' if len(who_) > 1 else str(who_[0])
        b_['talkWait'] = who_; b_['talkAt'] = rs.time.time()
        for i_ in who_:
            t_ = rs.asyncio.create_task(rs._talk_reply(rs.json.loads(rs.json.dumps(cat)), i_, b_['chime'][-1]['text'])); rs._TALK_RUN.add(t_); t_.add_done_callback(rs._TALK_RUN.discard)
    elif payload.action == 'look':   # 🎨 the creator restyles Fee (a signed owner wallet only — fee_owner_real; a user's cat look lives in Build a cat)
        if not cat.get('isLeader') or not rs.fee_owner_real(cat, 'look', signed):
            raise rs.HTTPException(403, "Only FEELESS's creator wallet styles Fee — sign in with it.")
        cat['look'] = rs.clean_fee_look(payload.look)
        if cat['look'].get('name'):
            cat['name'] = cat['look']['name']
        if cat['look'].get('title'):
            cat['title'] = cat['look']['title']
    elif payload.action == 'order':   # 🧭 a GENERAL cat: your order in plain words → one guarded proposal (real) or a paper fill
        if (cat.get('brainsCfg') or {}).get('kind') != 'general':
            raise rs.HTTPException(400, 'Only a General AI cat takes orders — a Trading cat hunts on its own.')
        if not str(payload.text or '').strip():
            raise rs.HTTPException(400, 'Write the order first — e.g. "buy 0.05 SOL of $BONK".')
        async with rs.httpx.AsyncClient(timeout=15) as http_o:
            await rs._run_order(store, cat, payload.text, http_o)
    elif payload.action == 'pull':   # 🚀 pull everything: positions sold at the last live price, balance out, locked until a top-up
        for pos in list(cat['positions']):
            cat['positions'].remove(pos)
            rs._close(store, cat, pos, rs._num(pos.get('lastPx')) or pos['entryPriceNative'], 'owner pulled all funds')
        amount = cat['balanceSol']; cat['balanceSol'] = 0.0; cat['status'] = 'stopped'; cat['needsTopup'] = True
        rs._log_event(store, cat, 'WITHDRAW', f'Owner pulled all funds ({amount:.4f} SOL, paper). The Cat is locked until a top-up.')
    elif payload.action == 'topup':   # paper top-up: the starting balance back, and (pay as you go) the model credit back
        cat['balanceSol'] = round(cat['balanceSol'] + float(cat.get('startingBalanceSol') or 10), 6); cat['needsTopup'] = False
        if cat.get('brainsCfg') and rs.free_credit_ok(cat, bool(signed and await rs._is_creator(signed))):
            cat['brainsCfg']['credit'] = round((cat['brainsCfg'].get('credit') or 0) + rs._lc.START_CREDIT, 6); cat.pop('brainPaused', None)
        rs._log_event(store, cat, 'STARTED', f'{cat["name"]} topped up.')
    elif payload.action == 'start':
        if cat.get('needsTopup'):
            raise rs.HTTPException(400, 'Funds were pulled — top up before starting this Agent again.')
        if cat.get('brainsCfg') and not rs._lc.can_ask(cat['brainsCfg']) and cat['brainsCfg'].get('billing') == 'payg':
            raise rs.HTTPException(400, 'Model credit is used up — top up to start again.')
        if cat['revoked']:
            raise rs.HTTPException(400, 'This Agent has been revoked and cannot restart.')
        cat['status'] = 'running'
        cat['lastTick'] = rs.time.time()
        rs._log_event(store, cat, 'STARTED', f'{cat["name"]} started paper trading.')
    elif payload.action == 'stop':
        cat['status'] = 'stopped'
        w_ = rs._WORK.get(cat_id)
        if w_ and w_.get('task') and not w_.get('done'):   # ⏹ the desk's big Stop also stops its minds (it only stopped new trades — a browse kept running and paying)
            w_['task']['stop'] = True
            for i_, ev_ in list((w_.get('events') or {}).items()):
                w_['go'][i_] = False; ev_.set()
            rs.asyncio.create_task(rs._hard_stop(w_))
        rs._log_event(store, cat, 'STOPPED', f'{cat["name"]} stopped by owner.')
    elif payload.action == 'run':
        if cat['status'] == 'running':
            await rs.run_engine(store, [cat])
    elif payload.action == 'controls':
        if payload.maxPositionSol is not None:
            cat['risk']['maxPositionSol'] = float(payload.maxPositionSol)
        if payload.maxDailyLossSol is not None:
            cat['risk']['maxDailyLossSol'] = float(payload.maxDailyLossSol)
        if payload.allowlist is not None:
            cat['risk']['allowlist'] = [s.strip() for s in payload.allowlist.split(',') if s.strip()]
        if payload.blocklist is not None:
            cat['risk']['blocklist'] = [s.strip() for s in payload.blocklist.split(',') if s.strip()]
        if rs._real.is_real(cat) and payload.maxPositionSol is not None and cat.get('agentWallet'):   # its wallet's per-buy budget follows MAX A TRADE
            cat['budgetSol'] = round(max(rs._real.MIN_BUDGET, min(rs._real.MAX_BUDGET, float(payload.maxPositionSol))), 4)
        if payload.limits is not None:   # 🎚 a general agent: $ a task · $ a mind · steps · $ a day (enforced in _work_start + cat_agent._ask)
            cat['limits'] = rs.clean_limits(payload.limits)
            if rs._num(payload.limits.get('taskUsd')):
                cat['taskCap'] = round(max(0.005, min(rs._task_cap_max(), float(rs._num(payload.limits.get('taskUsd'))))), 4)
    elif payload.action == 'withdraw':
        amount = min(float(payload.amount or 0), cat['balanceSol'])
        cat['balanceSol'] = round(cat['balanceSol'] - amount, 6)
        rs._log_event(store, cat, 'WITHDRAW', f'Paper withdrawal of {amount:.4f} SOL recorded.')
    elif payload.action == 'skin':   # 🎨 its desk look (backdrop clip + card colour), set by its owner — everyone who opens this agent sees the same desk
        sk_ = payload.look or {}
        bg_, acc_ = str(sk_.get('bg') or ''), str(sk_.get('acc') or '')
        if bg_ not in rs.DESK_SCENES or not rs.re.fullmatch(r'#[0-9a-fA-F]{6}', acc_):
            raise rs.HTTPException(400, 'Pick a backdrop and a card colour.')
        cat['skin'] = {'bg': bg_, 'acc': acc_.lower()}
    elif payload.action in ('brief', 'brief_propose', 'brief_approve', 'brief_dismiss'):   # 📜 a GENERAL agent's one brief for both minds (owner 2026-10-30)
        b_ = cat.get('brainsCfg') or {}
        if b_.get('kind') != 'general' and not cat.get('isLeader'):
            raise rs.HTTPException(400, "A trader's brief is sealed when you buy it — only a general agent's brief can change.")
        if not b_.get('brains'):
            raise rs.HTTPException(400, 'Give it a model first — its brief rides on its models.')
        now_ = rs.time.time()
        if payload.action == 'brief':   # you rewrite it — once an hour (Fee's: the creator, any time)
            left_ = rs.BRIEF_EVERY - (now_ - float(b_.get('briefAt') or 0))
            if left_ > 0 and not cat.get('isLeader'):
                raise rs.HTTPException(400, f'You can change its brief once an hour — {max(1, round(left_ / 60))} min to go.')
            txt_ = ' '.join(str(payload.text or '').split())[:rs._lc.PROMPT_MAX]
            if len(txt_) < 20:
                raise rs.HTTPException(400, 'Write a brief of at least a sentence.')
            b_.update(prompt=txt_, briefAt=now_, briefProposal=None)
        elif payload.action == 'brief_propose':   # its minds propose ONE better brief for both of them — at most once an hour, live only when you approve
            if now_ - float(b_.get('briefAskAt') or 0) < rs.BRIEF_EVERY:
                raise rs.HTTPException(400, 'Its minds can propose a new brief once an hour.')
            recent_ = ' | '.join(str(m.get('text') or '')[:160] for m in (cat.get('chat') or [])[-8:])
            msgs_ = [{'role': 'system', 'content': 'You and the other mind share ONE standing brief from your owner. Propose a better single brief that makes BOTH of you more useful '
                      'for what the owner actually asks, keeping every safety line. Answer ONLY JSON {"brief": "<= 1100 chars", "why": "one sentence"}.'},
                     {'role': 'user', 'content': f"Current brief: {b_.get('prompt') or '(none)'}\nRecent asks + answers: {recent_ or '(none yet)'}"}]
            text_, usd_ = await rs._or_call(b_['brains'][0], msgs_, max_tokens=700, **({'key': k_} if (k_ := rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)) else {}))
            got_ = rs._ca.parse_json(text_)
            if not k_:
                rs._lc.charge(b_, usd_)
            b_['briefAskAt'] = now_
            if not str(got_.get('brief') or '').strip():
                raise rs.HTTPException(502, 'Its minds did not propose a brief this time.')
            b_['briefProposal'] = {'text': ' '.join(str(got_['brief']).split())[:rs._lc.PROMPT_MAX], 'why': str(got_.get('why') or '')[:200], 'at': now_}
        elif payload.action == 'brief_approve':
            pr_ = b_.get('briefProposal')
            if not pr_:
                raise rs.HTTPException(400, 'Nothing to approve.')
            b_.update(prompt=pr_['text'], briefAt=now_, briefProposal=None)
        else:
            b_['briefProposal'] = None
        cat['brainsCfg'] = b_
    elif payload.action == 'work_mode':   # 🧭 how a general cat's two minds work: plan together → split → merge, or each its own job
        if payload.workMode not in rs._ca.MODES:
            raise rs.HTTPException(400, 'Pick plan or jobs.')
        cat['workMode'] = payload.workMode
    elif payload.action == 'models':   # 🔁 owner 2026-10-30: you keep your agent forever; its models can be switched 24 h after you got it (Fee: any time, the creator)
        left = rs.MODEL_LOCK_SEC - (rs.time.time() - float(cat.get('createdAt') or 0))
        if left > 0 and not cat.get('isLeader'):
            raise rs.HTTPException(400, f'Its models can change 24 h after you got it — {left / 3600:.1f} h to go.')
        if not cat.get('brainsCfg') and not cat.get('isLeader'):
            raise rs.HTTPException(400, 'This agent has no AI models.')
        cat_ = await rs._or_models()
        prev_ = cat.get('brainsCfg') or {'kind': 'trading', 'billing': 'payg'}
        try:   # the brief and credit carry over; the old model context is sealed before a fresh or sorted copy replaces it
            next_ = rs._lc.clean({'brains': payload.brains, 'brainKind': prev_.get('kind') or 'trading', 'billing': prev_.get('billing') or 'payg', 'prompt': payload.text or ''},
                              prev_ if cat.get('brainsCfg') else None, {m['id'] for m in cat_.get('models') or []} or None, max_models=await rs._model_limit(payload.session or ''))
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        if cat.get('brainsCfg'):
            try:
                rs._poi.preserve_model_memory(rs.DATA_DIR, cat_id, prev_, next_['brains'], rs.time.time())
            except (OSError, ValueError) as e:
                raise rs.HTTPException(503, f'Model switch paused: prior memory could not be sealed ({e}).')
        cat['brainsCfg'] = next_
        if payload.memory == 'fresh':   # 🧹 clean active context; the original sealed version remains recoverable
            cat['brainsCfg'].update(cloud=[], decisions=[], minds={})
        elif payload.memory == 'sort':   # 🧠 the NEW lead model reads its old cloud and keeps only what still helps (the rest is deleted)
            rs.asyncio.create_task(rs._sort_cloud(cat_id, cat['brainsCfg']['brains'][0]))
        rs._log_event(store, cat, 'LEARN', f"🔁 new models: {' + '.join(m.split('/')[-1] for m in cat['brainsCfg']['brains'])}")
    elif payload.action == 'model_cfg':   # 🎛 MODEL-CFG: tune effort + knobs for its current models any time (a tune, not a switch: no 24 h lock)
        if not cat.get('brainsCfg'):
            raise rs.HTTPException(400, 'This agent has no AI models.')
        cat_ = await rs._or_models(); brains_ = cat['brainsCfg'].get('brains') or []
        rows_ = {m['id']: m for m in cat_.get('models') or []}
        eff_ = {}
        for model, effort in (payload.efforts or {}).items():
            if model in brains_ and effort:
                if effort not in (rows_.get(model) or {}).get('efforts', []):
                    raise rs.HTTPException(400, 'That model does not expose the selected effort level.')
                eff_[model] = effort
        if payload.efforts is not None:
            cat['brainsCfg']['efforts'] = eff_
        if payload.knobs is not None:
            cat['brainsCfg']['knobs'] = rs._model_knobs_clean(cat_, {m: v for m, v in payload.knobs.items() if m in brains_})
        rs._log_event(store, cat, 'LEARN', '🎛 model settings tuned')
    elif payload.action == 'kind_models':   # 🧠🧠 COL-2: one proof kind's own two minds (empty = back to the agent's pair); budgets, credit and memory stay the agent's
        left = rs.MODEL_LOCK_SEC - (rs.time.time() - float(cat.get('createdAt') or 0))
        if left > 0 and not cat.get('isLeader'):
            raise rs.HTTPException(400, f'Its models can change 24 h after you got it — {left / 3600:.1f} h to go.')
        b_ = cat.get('brainsCfg')
        if not b_:
            raise rs.HTTPException(400, 'This agent has no AI models.')
        ids_ = {m['id'] for m in (await rs._or_models()).get('models') or []} | set(b_.get('brains') or [])   # the owner's own LM Studio only where the agent already runs on it
        try:
            rs._lc.set_minds(b_, str(payload.text or ''), payload.brains or [], ids_, max_models=await rs._model_limit(payload.session or ''))
        except ValueError as e:
            raise rs.HTTPException(400, str(e))
        rs._log_event(store, cat, 'LEARN', f"🧠 {str(payload.text).upper()} minds: {' + '.join(m.split('/')[-1] for m in rs._lc.minds_for(b_, payload.text))}")
    elif payload.action == 'delete':   # 🗑 forever means until YOU delete it: retired first, typed name, and never while its own wallet still holds money
        if not cat.get('revoked'):
            raise rs.HTTPException(400, 'Retire it first, then delete it for good.')
        if str(payload.text or '').strip().lower() != str(cat.get('name') or '').strip().lower():
            raise rs.HTTPException(400, "Type the agent's name to delete it for good.")
        w_ = (cat.get('agentWallet') or {}).get('address')
        if w_:
            try:
                async with rs.httpx.AsyncClient(timeout=15) as h_:
                    bal_ = await rs._aw.balances(h_, rs.os.environ.get('CROSSMINT_API_KEY', ''), w_)
            except ValueError as e:
                raise rs.HTTPException(409, f"Couldn't read its wallet ({e}) — nothing deleted.")
            if float(bal_.get('sol') or 0) > 0.001 or float(bal_.get('usdc') or 0) > 0.01:
                raise rs.HTTPException(409, f"Its wallet still holds {bal_.get('sol')} SOL / {bal_.get('usdc')} USDC — withdraw it first.")
        store['cats'].pop(cat_id, None)
        rs._DELETED_CATS.add((str(rs.STORE_PATH), cat_id)); rs._NEW_CATS.pop((str(rs.STORE_PATH), cat_id), None); rs._KEPT.pop(cat_id, None)
        rs._WORK.pop(cat_id, None)
        rs._save(store)
        return {'cat': None, 'deleted': cat_id}
    elif payload.action == 'revoke':
        cat['revoked'] = True
        cat['status'] = 'stopped'
        rs._log_event(store, cat, 'STOPPED', f'{cat["name"]} was revoked.')
    else:
        raise rs.HTTPException(400, f'Unknown action: {payload.action}')

    rs.keep_owned(cat); rs._save(store)
    return {'cat': {**rs._no_keys(cat), 'mine': not cat.get('isLeader')}}   # the action passed the owner check (Fee's: the creator's signature)

