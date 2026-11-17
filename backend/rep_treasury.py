"""🧹 Circle wallets, treasury hub, NFT studio, dust cleanup, mini player — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""
import reputation_service as _RSM  # noqa: E402,F401  (body models / annotations; this module is imported at the END of the service)
from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401
from typing import Optional  # noqa: F401
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # quoted type hints only
    from reputation_service import TradeLanded  # noqa: F401


def _rs():
    import reputation_service
    return reputation_service


async def _circle_start(agent=False) -> bool:
    """Start a Circle sidecar if it's installed and keyed (agent: the family + agent wallets account, port 5112). At most one attempt per 20s; never raises."""
    rs = _rs()
    boot_ = 'agentAt' if agent else 'at'
    if rs.time.time() - rs._circle_boot.get(boot_, 0) < 20 or not (rs.CIRCLE_DIR / 'node_modules').exists() or not rs.os.environ.get('CIRCLE_AGENT_API_KEY' if agent else 'CIRCLE_API_KEY'):
        return False
    rs._circle_boot[boot_] = rs.time.time()
    try:
        import subprocess
        subprocess.Popen(['node', 'server.mjs'], cwd=str(rs.CIRCLE_DIR), stdout=open('/tmp/feeless-circle-agent.log' if agent else '/tmp/feeless-circle.log', 'ab'), stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True, env={**rs.os.environ, 'CIRCLE_TENANT': 'agent'} if agent else None)
    except Exception:
        return False
    await rs.asyncio.sleep(1.5)
    return True


async def _circle(method, path, body=None, agent=False):
    rs = _rs()
    r = None
    for attempt in range(3):   # sidecar down → start it (owner is signed in: every caller is owner-gated) and retry
        try:
            async with rs.httpx.AsyncClient(timeout=30) as http:
                r = await http.request(method, f"http://127.0.0.1:{5112 if agent else 5111}{path}", json=body)
            break
        except rs.httpx.ConnectError:
            if attempt == 2 or not (await rs._circle_start(agent) or attempt == 1):
                raise rs.HTTPException(503, 'Circle wallet service is not running and could not be started (check CIRCLE_API_KEY and circle/node_modules).')
            await rs.asyncio.sleep(1.5)
        except rs.httpx.HTTPError:
            raise rs.HTTPException(503, 'Circle wallet service did not answer.')
    data = r.json() if r.content else {}
    if r.status_code >= 400:
        raise rs.HTTPException(r.status_code, data.get('detail') or 'Circle request failed.')
    return data


def _require_owner(request: Request):
    rs = _rs()
    me = rs._require_admin(request)
    if me not in rs._owner_wallets():
        raise rs.HTTPException(403, 'Only the FEELESS creator wallet can do this: it moves money, routes fees or holds keys.')
    return me


# ================================================================================================
# SEASON BADGE RESERVE POOL: tiers earn weighted shares of the Fee Reserve wallet, owner-signed payouts
# ================================================================================================
async def _reserve_plan(s, d, bal=None):
    rs = _rs()
    wallet = s.get('reserveWallet') or ''
    pool = bal
    if wallet and bal is None:
        try:
            async with rs.httpx.AsyncClient(timeout=8) as http:
                pool = ((await rs._rpc(http, 'getBalance', [wallet])) or {}).get('value', 0) / 1e9
        except Exception:
            pool = None
    blocked = rs._block_load()['wallets']
    holders = [{'address': a, 'score': r['score'], 'tier': rs._tier(r['score'])['tier']}
               for a, r in (d['scores'].get(s['id']) or {}).items() if not rs._is_blocked(blocked.get(a))]
    plan = rs.reserve_pool.payout_plan(pool or 0, float(s.get('badgeRewardPct') or 0), holders, excluded=frozenset(rs._protected_wallets()))
    return {**plan, 'season': {k: s.get(k) for k in ('id', 'name', 'start', 'end', 'accent', 'reserveWallet', 'badgeRewardPct')},
            'assigned': bool(wallet), 'balanceKnown': pool is not None, 'ended': s['end'] <= rs.time.time(),
            'payout': (d.get('reservePayouts') or {}).get(s['id'])}


async def _circle_pay(wallet_addr: str, rows: list, scope: str, confirm: str) -> list:
    """Pay each row from a Circle wallet (Circle signs server-side with the entity secret). Owner-only callers.
    Deterministic idempotency keys: a retry or double click re-sends nothing that already went out."""
    rs = _rs()
    want = rs.reserve_pool.circle_confirm_phrase(rows)
    if confirm.strip() != want:
        raise rs.HTTPException(400, f'Type "{want}" to confirm.')
    ws = (await rs._circle('GET', '/wallets')).get('wallets') or []
    w = next((x for x in ws if x.get('address') == wallet_addr), None)
    if not w:
        raise rs.HTTPException(400, 'This wallet is not one of your Circle wallets. Connect it in Phantom to pay instead.')
    if w.get('blockchain') != 'SOL':
        raise rs.HTTPException(400, f"That Circle wallet is on {w.get('blockchain')}, not Solana mainnet.")
    tok = rs.reserve_pool.circle_sol_token(w)
    bal = next((float(b.get('amount') or 0) for b in w.get('balances') or [] if b.get('tokenId') == tok), 0.0)
    total = round(sum(float(r['sol']) for r in rows), 6)
    if not tok or bal < total:
        raise rs.HTTPException(400, f'The Circle wallet holds {bal} SOL; this payout needs {total} SOL plus network fees.')
    sem = rs.asyncio.Semaphore(4)

    async def one(r):
        async with sem:
            try:
                out = await rs._circle('POST', '/transfer', {'walletId': w['id'], 'tokenId': tok, 'to': r['address'], 'amount': rs.reserve_pool.circle_amount(r['sol']),
                                                          'idempotencyKey': rs.reserve_pool.circle_idem(scope, r['address'], float(r['sol']))})
                return {**r, 'circleTx': out.get('id'), 'state': out.get('state') or 'INITIATED'}
            except rs.HTTPException as e:
                return {**r, 'error': str(e.detail)[:160]}
    return list(await rs.asyncio.gather(*(one(r) for r in rows)))


def _pools():
    rs = _rs()
    return rs._json_load(rs.BADGE_POOLS_PATH, {'pools': []})


def _pool_inputs(pool):
    """(holders, allocated %) — blocklisted and FEELESS wallets never hold a share."""
    rs = _rs()
    tiers = {}
    if pool.get('seasonId'):
        tiers = {a: rs._tier(r['score'])['tier'] for a, r in (rs._seasons()['scores'].get(pool['seasonId']) or {}).items()}
    blocked, safe = rs._block_load()['wallets'], rs._protected_wallets() | {pool['wallet']}
    tiers = {a: t for a, t in tiers.items() if a not in safe and not rs._is_blocked(blocked.get(a))}
    badges = {a: list(items) for a, items in (rs._admin_load().get('badges') or {}).items() if items and a not in safe and not rs._is_blocked(blocked.get(a))}
    for a, (at, rec) in list(rs._badge_cache.items()):   # built-in badges (creator, caller, holder…) for wallets scored in the last day
        if rs.time.time() - at < 86400 and a not in safe and not rs._is_blocked(blocked.get(a)):
            badges.setdefault(a, []).extend(b['id'] for b in (rec or {}).get('badges', []) if b.get('id') and b['id'] not in badges.get(a, []))
    pool['_tiers'], pool['_badges'] = tiers, badges
    if pool.get('mode', 'weight') == 'pct':
        return rs.reserve_pool.pct_holders(pool.get('weights') or {}, tiers, badges)
    return rs.reserve_pool.pool_holders(pool.get('weights') or {}, tiers, badges), 100.0


async def _pool_plan(pool, bal=None):
    rs = _rs()
    known = bal is not None
    if bal is None:
        try:
            async with rs.httpx.AsyncClient(timeout=8) as http:
                bal = ((await rs._rpc(http, 'getBalance', [pool['wallet']])) or {}).get('value', 0) / 1e9
            known = True
        except Exception:
            bal, known = 0, False
    holders, allocated = rs._pool_inputs(pool)
    counts = rs.badge_cards.key_counts(pool.get('_tiers'), pool.get('_badges'))
    # Fixed SOL-each badges are paid first (never more than the wallet can spare); the % pot comes from what's left.
    fixed, fixed_total = rs.reserve_pool.fixed_rows(pool.get('fixed') or {}, pool.pop('_tiers', {}), pool.pop('_badges', {}), max(0.0, bal - rs.reserve_pool.KEEP_SOL))
    rest = bal - fixed_total
    plan = rs.reserve_pool.payout_plan(rest, pool['pct'] * allocated / 100, holders, excluded=frozenset(rs._protected_wallets()) | {pool['wallet']})
    by = {r['address']: r for r in plan['rows']}
    for a, v in fixed.items():
        if a in by:
            by[a]['sol'] = round(by[a]['sol'] + v, 6); by[a]['fixedSol'] = v
        elif v >= rs.reserve_pool.DUST_SOL:
            plan['rows'].append({'address': a, 'tier': 'Recruit', 'score': 0, 'weight': 0, 'sharePct': 0, 'sol': v, 'fixedSol': v, 'why': 'fixed badge reward'})
    # What ONE holder of each badge / tier key gets from this payout: stored on the payout, summed on card backs.
    want = sum(float(v or 0) * counts.get(k, 0) for k, v in (pool.get('fixed') or {}).items())
    pct_mode = pool.get('mode', 'weight') == 'pct'
    plan['perKey'] = rs.badge_cards.per_key_each('pct' if pct_mode else 'weight', pool.get('weights') or {}, pool.get('fixed') or {}, counts,
                                              (plan['potSol'] * 100 / allocated if allocated else 0) if pct_mode else plan['potSol'], plan['totalWeight'],
                                              fixed_total / want if want else 1.0)
    plan['fixedSol'] = fixed_total; plan['potSol'] = round(plan['potSol'] + fixed_total, 6)
    plan['paidSol'] = round(sum(r['sol'] for r in plan['rows']), 6)
    plan['allocatedPct'] = allocated
    last = (pool.get('payouts') or [None])[-1]
    return {**plan, 'pool': {k: v for k, v in pool.items() if k != 'payouts'}, 'balanceKnown': known, 'lastPayout': last,
            'cooldownLeft': max(0, round(rs.POOL_COOLDOWN - (rs.time.time() - last['at']))) if last else 0}


def _code_health_scan():
    rs = _rs()
    import code_health as _ch
    rs._json_save(rs.CODE_HEALTH_PATH, _ch.scan(rs.Path(__file__).resolve().parent.parent))


async def _code_health_run():
    rs = _rs()
    if rs._code_health_busy['on']:
        return
    rs._code_health_busy['on'] = True
    try:
        await rs.asyncio.to_thread(rs._code_health_scan)   # a static file scan (~5s) — never on the loop, never on a GET
    finally:
        rs._code_health_busy['on'] = False


async def _code_health_loop():
    rs = _rs()
    while True:
        try:
            st = rs.CODE_HEALTH_PATH.stat().st_mtime if rs.CODE_HEALTH_PATH.exists() else 0
            if rs.time.time() - st > 6 * 3600:
                await rs._code_health_run()
        except Exception:
            pass
        await rs.asyncio.sleep(1800)


async def _machine_read():
    """🖥 Load + swap of the machine running the services (60s cache, a thread — sysctl is a subprocess). Mac only; elsewhere load only."""
    rs = _rs()
    if rs.time.time() - rs._mach_cache['at'] < 60:
        return rs._mach_cache['v']

    def read():
        out = {'cores': rs.os.cpu_count() or 8}
        try:
            out['load1'] = round(rs.os.getloadavg()[0], 1)
        except OSError:
            pass
        try:
            import subprocess
            t = subprocess.run(['sysctl', '-n', 'vm.swapusage'], capture_output=True, text=True, timeout=3).stdout
            nums = {k: float(v.rstrip('M')) for k, v in rs._re.findall(r'(total|used) = ([\d.]+M)', t)}
            if nums.get('total'):
                out['swapPct'] = round(100 * nums.get('used', 0) / nums['total'], 1)
        except Exception:
            pass
        return out
    rs._mach_cache.update(at=rs.time.time(), v=await rs.asyncio.to_thread(read))
    return rs._mach_cache['v']


# ================================================================================================
# LINKED ENGINE: one reputation score everywhere · trades earn season points · wallet watch · after-the-sell
# ================================================================================================
def _quick_rep(address: str) -> dict:
    """The case-file verdict without network calls: a fresh case file if one was built, else the same scoring
    over local evidence (blocklist, funder graph, creator record, cached caller stats). Same claims, same sources."""
    rs = _rs()
    a = rs.primary_of(address)
    hit = rs._case_cache.get(a)
    if hit and rs.time.time() - hit[0] < 900 and hit[1].get('kind') == 'wallet':
        c = hit[1]
        return {'score': c.get('score', 0), 'level': c.get('level'), 'label': c.get('label'), 'top': (c.get('evidence') or [None])[0]}
    if a in rs._protected_wallets():
        return {**rs.investigate.verdict([], True), 'top': None}
    fund = rs._funders_load(); store = rs._load()
    entry = store['creators'].get(rs._creator_key('solana', a))
    fsrc = store['funding'].get(rs._creator_key('solana', a))
    ctx = {'blocked': rs._block_load()['wallets'].get(a), 'funderOfSquads': fund['funders'].get(a), 'fundedBy': fsrc,
           'fundedByFlagged': bool(fsrc and rs._is_flagged_funder(fund['funders'].get(fsrc))),
           'creator': rs.score_creator(entry) if entry else None, 'caller': rs._kol_cache.get(a, (0, None))[1], 'linkedCreators': []}
    ev = rs.investigate.wallet_evidence(ctx)
    v = rs.investigate.verdict(ev)
    return {'score': v['score'], 'level': v['level'], 'label': v['label'], 'top': next((e for e in ev if e['weight'] > 0), None)}


def trade_points(in_usd: float, fee_bps: int) -> float:
    """Season points for a landed FEELESS trade: fees paid weigh most, volume counts a little, capped per trade."""
    usd = max(0.0, float(in_usd or 0))
    fee_usd = usd * max(0, int(fee_bps or 0)) / 10000
    return round(min(50.0, fee_usd * 20 + min(usd, 1000) / 200), 1)


def _fee_totals_heal():
    """Lifetime totals must match the fee ledger (the source of truth) to the trade: rebuilt whenever the trade counts
    differ or the file is missing. Totals only exist to make the fee book fast; they never get to disagree."""
    rs = _rs()
    led = rs._json_load(rs.FEE_LEDGER_PATH, {})
    tot = rs._json_load(rs.FEE_TOTALS_PATH, {}) if rs.FEE_TOTALS_PATH.exists() else None
    if tot is not None and {k: len(v or []) for k, v in led.items() if v} == {k: int(v.get('trades') or 0) for k, v in tot.items()}:
        return tot
    fresh = {}
    for who, rows_ in led.items():
        for r in rows_ or []:
            rs.fee_report.add_total(fresh, who, r)
    rs._json_save(rs.FEE_TOTALS_PATH, fresh)
    return fresh


async def _sol_usd() -> float:
    rs = _rs()
    hit = rs._sol_px.get('v')
    if hit and rs.time.time() - hit[0] < 120:
        return hit[1]
    try:
        async with rs.httpx.AsyncClient(timeout=4) as http:
            v = float(((await http.get(f'https://lite-api.jup.ag/price/v3?ids={rs.WSOL}')).json().get(rs.WSOL) or {}).get('usdPrice') or 0)
    except Exception:
        v = 0.0
    if v <= 0:   # 🛟 this free endpoint rate-limits (429): the full chain (Jupiter key → DexScreener → last good), and a miss is never remembered as the price
        try:
            v = float(await rs._sol_usd_live() or 0)
        except Exception:
            v = 0.0
    if v <= 0:
        return hit[1] if hit and rs.time.time() - hit[0] < 600 else 0.0
    rs._sol_px['v'] = (rs.time.time(), v)
    return v


def _trade_record(p: 'TradeLanded', coin: str, amt: float, side: str, sol_usd: float, fee_usd: Optional[float] = None) -> _RSM.Optional[dict]:
    """The trader's position row. The exact on-chain fill wins (what really left / reached the wallet, fees in);
    the quote is only a fallback, with the FEELESS fee added so it is never rosier than reality."""
    rs = _rs()
    f = p.fill or {}
    if f.get('token') == coin and f.get('tokens', 0) > 0 and f.get('side') == side:
        usd = f.get('usd') or (f.get('sol') or 0) * sol_usd
        if usd > 0:
            return {**{k: f[k] for k in ('side', 'tokens', 'sol', 'networkSol', 'balanceAfter', 'poolUsd', 'fillPrice', 'feelessFeeUsd', 'networkUsd', 'solUsd', 'priced', 'locked') if k in f}, 'ts': f.get('ts') or rs.time.time(),
                    'usd': round(usd, 6), 'price': usd / f['tokens'], 'token': coin, 'tx': p.signature, 'via': 'chain', 'locked': bool(f.get('locked'))}
    if amt > 0 and p.inUsd > 0:
        fee = fee_usd if fee_usd is not None else p.inUsd * max(0, p.feeBps) / 10000   # the fee actually charged beats the %
        usd = p.inUsd + fee if side == 'buy' else max(0.0, p.inUsd - fee)
        return {'ts': rs.time.time(), 'side': side, 'usd': round(usd, 4), 'price': usd / amt, 'tokens': amt, 'token': coin, 'tx': p.signature, 'via': 'estimate'}
    return None


def watch_alerts(target: str, trades: list, last_ts: float, rep: dict, name: str) -> list:
    """Pure: new trades by a watched wallet → alert lines (dumps by suspect wallets called out)."""
    out = []
    for t in sorted((x for x in trades if (x.get('ts') or 0) > last_ts), key=lambda x: x['ts'])[-5:]:
        sym = t.get('symbol') or (t.get('token') or '')[:4]
        bad = rep.get('level') in ('suspect', 'high')
        verb = 'bought' if t.get('side') == 'buy' else ('is dumping' if bad else 'sold')
        out.append({'text': f"👁 {name} {verb} ${sym} (${t.get('usd', 0):,.0f}){' · ' + rep.get('label', '') if bad else ''}",
                    'url': f"/terminal/chat?chain=solana&pair={t['pair']}" if t.get('pair') else f'/terminal/profile/{target}', 'ts': t['ts'], 'tx': t.get('tx')})
    return out


async def _watch_loop():
    rs = _rs()
    while True:
        await rs.asyncio.sleep(120)
        try:
            d = rs._json_load(rs.WATCH_PATH, {'targets': {}, 'last': {}})
            last = d.setdefault('last', {}); changed = False
            for target, watchers in list(d['targets'].items())[:150]:
                try:
                    trades = await rs.wallet_trades(target)
                except Exception:
                    continue
                newest = max((t.get('ts') or 0 for t in trades), default=0)
                if target not in last:  # first look: remember where we are, don't replay history
                    last[target] = newest; changed = True
                    continue
                name = rs._display_name(target) or f'{target[:4]}…{target[-4:]}'
                for a in rs.watch_alerts(target, trades, last[target], rs._quick_rep(target), name):
                    for w in watchers:
                        rs.notify(w, 'watch', a['text'], a['url'], actor=target, once=f"watch:{a['tx'] or a['ts']}")
                if newest > last[target]:
                    last[target] = newest; changed = True
            if changed:
                rs._json_save(rs.WATCH_PATH, d)
        except Exception as exc:
            print('watch loop error', exc)


def after_sell_lessons(trades: list, prices: dict) -> list:
    """Pure: your recent sells vs the coin's price now. A coin that ran 40%+ after you sold = 'sold a runner'."""
    out = []
    for t in trades:
        if t.get('side') != 'sell' or not t.get('price'):
            continue
        now = prices.get(t.get('token'))
        if not now:
            continue
        move = round((now / t['price'] - 1) * 100, 1)
        out.append({'token': t['token'], 'symbol': t.get('symbol'), 'pair': t.get('pair'), 'soldAt': t['price'], 'now': now, 'movePct': move,
                    'soldUsd': t.get('usd'), 'ts': t.get('ts'), 'lesson': 'runner' if move >= 40 else 'saved' if move <= -30 else 'fair'})
    return sorted(out, key=lambda x: -x['movePct'])[:12]


async def _money_pulse_build(me: str, owner: bool) -> dict:
    rs = _rs()
    cfg = rs._fee_cfg(); d = rs._seasons(); pools = rs._pools()['pools']
    seasons = [x for x in d['seasons'] if x.get('reserveWallet')][-4:]
    addrs = list(dict.fromkeys([a for a in (cfg.get('feeAccountSol'), cfg.get('feeAccountUsdc'), me) if a] + [x['reserveWallet'] for x in seasons] + [p['wallet'] for p in pools]))

    async def chain():
        try:
            async with rs.httpx.AsyncClient(timeout=10) as http:
                res = await rs._rpc(http, 'getMultipleAccounts', [addrs[:100], {'encoding': 'jsonParsed', 'commitment': 'confirmed'}])
            return rs.money_pulse.parse_accounts(addrs, (res or {}).get('value') or []), True
        except Exception:
            return {}, False

    async def circle():
        if not owner:
            return {'configured': False}
        try:
            # Money Pulse deliberately performs one batched chain read for its own cards. The dedicated Circle-wallet endpoint
            # enriches wallet rows with confirmed SOL without adding a second RPC call to this overview.
            return {'configured': True, 'up': True, 'wallets': (await rs._circle('GET', '/wallets')).get('wallets') or []}
        except rs.HTTPException as e:
            return {'configured': bool(rs.os.environ.get('CIRCLE_API_KEY')), 'up': False, 'error': str(e.detail)[:160], 'wallets': []}

    async def trading():
        try:
            async with rs.httpx.AsyncClient(timeout=4) as http:
                return (await http.get('http://127.0.0.1:5001/api/trading/status')).json()
        except Exception:
            return {}
    (acc, chain_ok), circ, trade = await rs.asyncio.gather(chain(), circle(), trading())
    sol = lambda a: (acc.get(a) or {}).get('sol') if chain_ok else None
    reserves, pool_plans = await rs.asyncio.gather(
        rs.asyncio.gather(*(rs._reserve_plan(x, d, bal=sol(x['reserveWallet'])) for x in seasons)),
        rs.asyncio.gather(*(rs._pool_plan(dict(p), bal=sol(p['wallet'])) for p in pools)))
    fee_rows = []
    for label, a, asset in (('SOL fee account (wSOL)', cfg.get('feeAccountSol') or '', 'wSOL'), ('USDC fee account', cfg.get('feeAccountUsdc') or '', 'USDC')):
        t = (acc.get(a) or {}).get('token') if a else None
        fee_rows.append({'label': label, 'address': a, 'asset': asset, 'ok': bool(t), **(t or {})})
    ledger = rs._json_load(rs.FEE_LEDGER_PATH, {})
    last = max((r[-1]['t'] for r in ledger.values() if r), default=0)
    now = rs.time.time()
    fees_day = round(sum(x['feeUsd'] for r in ledger.values() for x in r if now - x['t'] < 86400), 4)
    fees_week = round(sum(x['feeUsd'] for r in ledger.values() for x in r if now - x['t'] < 7 * 86400), 4)
    env = {k: rs.os.environ.get(k, '').strip() for k in ('SOLANA_RPC_URL', 'JUPITER_API_KEY')}
    env['_internal_key'] = (rs.Path(__file__).parent / 'data' / 'internal.key').exists()
    checks = rs.money_pulse.preflight(env, cfg, fee_rows, trade, last, rs.time.time(), circ)
    if not chain_ok:
        checks.insert(0, {'key': 'chain', 'label': 'Chain read', 'ok': False, 'fix': 'RPC did not answer; balances below may be stale.'})
    trim = lambda plan: {**plan, 'rows': plan['rows'][:60]}
    out = {'at': rs.time.time(), 'owner': owner, 'chainOk': chain_ok, 'feesTodayUsd': fees_day, 'fees7dUsd': fees_week, 'feesSince': min((x['t'] for r in ledger.values() for x in r), default=None), 'admin': me, 'adminSol': sol(me), 'feeAccounts': fee_rows,
           'reserves': {r['season']['id']: trim(r) for r in reserves}, 'pools': {p['pool']['id']: trim(p) for p in pool_plans},
           'circle': circ, 'checks': checks, 'alerts': rs.money_pulse.alerts(reserves, pool_plans, circ.get('wallets'))}
    return out


async def _preflight_watch():
    """Every 10 min: re-run the money preflight; when a check turns red (or recovers) the owners get a bell + phone push."""
    rs = _rs()
    await rs.asyncio.sleep(90)
    while True:
        try:
            owners = sorted(rs._owner_wallets())
            if owners:
                snap = await rs._money_pulse_build(owners[0], True)
                rs._pulse_cache['owner'] = (rs.time.time(), snap)
                prev = rs._json_load(rs.PREFLIGHT_STATE_PATH, {})
                bad, fixed, state = rs.money_pulse.check_flips(prev, snap['checks'])
                rs._json_save(rs.PREFLIGHT_STATE_PATH, state)
                for c in bad:
                    for o in owners:
                        rs.notify(o, 'system', f"⚠ Money check failing: {c['label']}. {c.get('fix') or ''}".strip(), '/terminal', once=f"pf-bad:{c['key']}:{int(rs.time.time() // 3600)}")
                for c in fixed:
                    for o in owners:
                        rs.notify(o, 'system', f"✅ Back to green: {c['label']}", '/terminal', once=f"pf-ok:{c['key']}:{int(rs.time.time() // 3600)}")
        except Exception:
            pass
        await rs.asyncio.sleep(600)


def _verify_store():
    rs = _rs()
    return rs._json_load(rs.VERIFY_PATH, {'mints': {}, 'requests': []})


async def _verify_facts(mint):
    """Everything the checks need, gathered in parallel: holder forensics, mint account, the live pool."""
    rs = _rs()
    async def market():
        async with rs.httpx.AsyncClient(timeout=10) as http:
            return (await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{mint}')).json().get('pairs') or []

    async def safe(coro, default):
        try:
            return await coro
        except Exception:
            return default
    async with rs.httpx.AsyncClient(timeout=10) as http:
        intel, auth, pairs = await rs.asyncio.gather(safe(rs.token_intel('solana', mint), {}), safe(rs._mint_authorities(http, mint), None), safe(market(), []))
    pairs = sorted((p for p in pairs if p.get('chainId') == 'solana'), key=lambda p: -((p.get('liquidity') or {}).get('usd') or 0))
    top = pairs[0] if pairs else {}
    info = top.get('info') or {}
    tx = (top.get('txns') or {}).get('h24') or {}
    buys, sells = tx.get('buys') or 0, tx.get('sells') or 0
    reg = [p for p in rs._json_load(rs.POOLS_REG_PATH, {'pools': []})['pools'] if p.get('mint') == mint and p.get('locked')]
    creator = intel.get('creator')
    rep = rs._quick_rep(creator) if creator else {}
    created = min((p.get('pairCreatedAt') or 9e15 for p in pairs), default=None)
    facts = {
        'mintAuthority': (auth or {}).get('mintAuthority') if auth is not None else 'unknown',
        'freezeAuthority': (auth or {}).get('freezeAuthority') if auth is not None else 'unknown',
        'creatorBlocked': bool(creator and rs._is_blocked(rs._block_load()['wallets'].get(creator))), 'creatorLevel': rep.get('level'),
        'ageHours': (rs.time.time() * 1000 - created) / 3.6e6 if created and created < 9e15 else 0,
        'liquidityUsd': (top.get('liquidity') or {}).get('usd') or 0, 'volume24h': (top.get('volume') or {}).get('h24') or 0,
        'buyRatio': buys / (buys + sells) if buys + sells >= 50 else None,
        'socials': len(info.get('socials') or []) + len(info.get('websites') or []),
        'lpLocked': bool(reg) or str(top.get('dexId') or '').lower() == 'pumpswap',
        'top10Pct': intel.get('top10Pct'), 'insidersPct': intel.get('insidersHoldingPct'), 'devPct': intel.get('devHoldingPct'),
        'marketCapUsd': top.get('marketCap') or top.get('fdv') or 0,
        'bundled': len(intel.get('bundledWallets') or []), 'snipers': len(intel.get('sniperWallets') or []),
    }
    return facts, {'symbol': (top.get('baseToken') or {}).get('symbol'), 'pair': top.get('pairAddress'), 'dexId': top.get('dexId')}


async def _verify_run(mint):
    rs = _rs()
    facts, meta = await rs._verify_facts(mint)
    manual = rs._verify_store()['mints'].get(mint)
    try:
        official = mint in set((await rs._ecosystem_mints()).values())
    except Exception:
        official = False
    rep = {**rs.verify.verify_report(facts, manual, official), 'mint': mint, **meta, 'at': rs.time.time()}
    snap = {'level': rep['level'], 'badges': [b['id'] for b in rep['badges'] if b['earned']]}
    d = rs._verify_store()
    prev = (d.get('last') or {}).get(mint)
    if prev != snap:   # coins earn AND lose checks + badges the same way: every run is compared with the last one
        events = [{**e, 'at': rep['at']} for e in rs.verify.transitions(prev, rep)]
        d.setdefault('last', {})[mint] = snap
        if events:
            d.setdefault('history', {})[mint] = ((d.get('history') or {}).get(mint, []) + events)[-20:]
        rs._json_save(rs.VERIFY_PATH, d)
    rep['history'] = list(reversed((d.get('history') or {}).get(mint, [])))[:10]
    rs._verify_cache[mint] = (rs.time.time(), rep)
    if len(rs._verify_cache) > 5000:
        rs._verify_cache.clear()
    return rep


async def _verify_fill(mint):
    rs = _rs()
    try:
        await rs._verify_run(mint)
    except Exception:
        pass
    finally:
        rs._verify_pending.discard(mint)


def _nft_load():
    rs = _rs()
    return rs._json_load(rs.NFT_PATH, {'collections': []})


def _public_site(request: Request) -> str:
    """NFT + coin metadata is permanent: it must live on a public https domain, never localhost."""
    rs = _rs()
    site = rs.os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/') or (request.headers.get('origin') or '').rstrip('/')
    host = rs._re.sub(r'^https?://', '', site).split('/')[0].split(':')[0]
    if not site.startswith('https://') or host in ('localhost', '127.0.0.1', '0.0.0.0') or host.endswith('.local') or rs._re.match(r'^(10|192\.168|172\.(1[6-9]|2\d|3[01]))\.', host):
        raise rs.HTTPException(503, 'NFTs need a public https domain for their metadata (set PUBLIC_SITE_URL). A local address would break them forever.')
    return site


def _nft_platforms() -> dict:
    rs = _rs()
    cm, ud = rs.os.environ.get('CROSSMINT_API_KEY', '').strip(), rs.os.environ.get('UNDERDOG_API_KEY', '').strip()
    return {'metaplex': {'ready': True, 'how': 'Your connected wallet signs. ~0.003 SOL rent per NFT + network fee. No key needed.'},
            'crossmint': {'ready': bool(cm), 'env': 'staging' if cm.startswith(('sk_staging', 'sk_test')) else 'production' if cm else None,
                          'how': 'Add CROSSMINT_API_KEY (console.crossmint.com, scopes collections.create + nfts.create) to backend/.env.'},
            'underdog': {'ready': bool(ud), 'env': rs.os.environ.get('UNDERDOG_ENV', 'mainnet'),
                         'how': 'Add UNDERDOG_API_KEY (app.underdogprotocol.com) to backend/.env; UNDERDOG_ENV=devnet to test.'}}


async def _nft_api(platform: str, method: str, path: str, body=None):
    rs = _rs()
    if platform == 'crossmint':
        key = rs.os.environ.get('CROSSMINT_API_KEY', '').strip()
        url, headers = rs.nft_studio.crossmint_base(key) + path, {'X-API-KEY': key}
    else:
        key = rs.os.environ.get('UNDERDOG_API_KEY', '').strip()
        url, headers = rs.nft_studio.underdog_base(rs.os.environ.get('UNDERDOG_ENV', '')) + path, {'Authorization': f'Bearer {key}'}
    if not key:
        raise rs.HTTPException(400, f'{platform.title()} is not connected yet (API key missing).')
    try:
        async with rs.httpx.AsyncClient(timeout=30) as http:
            r = await http.request(method, url, json=body, headers=headers)
    except rs.httpx.HTTPError as e:
        raise rs.HTTPException(502, f'{platform.title()} did not answer ({e.__class__.__name__}).')
    data = r.json() if r.content else {}
    if r.status_code >= 400:
        raise rs.HTTPException(502, f"{platform.title()}: {str(data.get('message') or data.get('error') or data)[:160]}")
    return data


async def _nft_verify(sig: str, signer: str, must_touch: list):
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=20) as http:
        tx = await rs._rpc(http, 'getTransaction', [sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
    if not tx or (tx.get('meta') or {}).get('err'):
        raise rs.HTTPException(400, 'That transaction is not confirmed on-chain (or it failed).')
    keys = tx['transaction']['message']['accountKeys']
    if signer not in [k['pubkey'] for k in keys if k.get('signer')]:
        raise rs.HTTPException(400, 'Signed by a different wallet.')
    if any(a not in [k['pubkey'] for k in keys] for a in must_touch):
        raise rs.HTTPException(400, 'That transaction does not create this collection / these NFTs.')


def _desk_build(force=False):
    """Rebuild the desk from the blocklist, funder graph and creator records (cheap: local data only). Cached 10 min;
    the saved file keeps a daily history so the owner can see the department's catch grow."""
    rs = _rs()
    if not force and rs._desk['snap'] and (rs._desk.get('bg') or rs.time.time() - rs._desk['at'] < 600):
        return rs._desk   # with the background loop running a reader NEVER rebuilds inline (it froze the service ~7s every 10 min)
    creators = {}
    for key, rec in (rs._load().get('creators') or {}).items():
        if not str(key).startswith('solana:'):
            continue
        sc = rs.score_creator(rec)
        if sc.get('ruggedCount') or sc.get('dumpedCount'):
            creators[rec.get('address') or key.split(':', 1)[1]] = {'rugged': sc['ruggedCount'], 'dumped': sc['dumpedCount'], 'launches': sc['tokenCount'],
                                                                    'launchTimes': [t.get('firstSeenAt') for t in (rec.get('tokens') or {}).values()]}
    actors = rs.intel_desk.build_actors(rs._block_load()['wallets'], rs._funders_load(), creators, protected=frozenset(rs._protected_wallets()))
    now = rs.time.time()
    snap = rs.intel_desk.snapshot(actors, now)
    rg = rs.intel_desk.rings(actors)
    rs._desk.update({'at': now, 'snap': snap, 'rings': rg, 'actors': actors})
    saved = rs._json_load(rs.INTEL_DESK_PATH, {'history': []})
    day = rs.time.strftime('%Y-%m-%d', rs.time.gmtime(now))
    hist = [h for h in saved.get('history', []) if h.get('day') != day] + [{'day': day, **snap['totals']}]
    rs._json_save(rs.INTEL_DESK_PATH, {'at': now, 'totals': snap['totals'], 'history': hist[-90:], 'index': snap['index'],
                                 'rings': [{k: r[k] for k in ('id', 'core', 'size', 'launchesHit', 'rugs', 'threat', 'members')} for r in rg[:200]]})
    return rs._desk


def _desk_build_bg(force=False):
    # in a worker thread: ~7s of pure Python over the blocklist + funder graph. The loop may change a store mid-read → try again.
    rs = _rs()
    for _ in range(3):
        try:
            return rs._desk_build(force)
        except RuntimeError:
            rs.time.sleep(0.5)
    return rs._desk


async def _desk_get(force=False):
    """The desk for an async reader: the copy in memory, or (first read after a start / a forced sweep) ONE shared build in a worker thread."""
    rs = _rs()
    if rs._desk['snap'] is not None and not force:
        return rs._desk
    t = rs._desk_flight.get('t')
    if t is None or t.done():
        t = rs._desk_flight['t'] = rs.asyncio.ensure_future(rs.asyncio.to_thread(rs._desk_build_bg, True))
    try:
        await rs.asyncio.shield(t)
    except Exception:
        pass
    return rs._desk


async def _desk_loop():
    rs = _rs()
    rs._desk['bg'] = True
    await rs.asyncio.sleep(5)
    while True:
        await rs._desk_get(force=True)
        await rs.asyncio.sleep(600)


def _card_defaults() -> dict:
    """Every card that exists: catalog badges, custom awards, built-ins seen lately, season + weekly drops."""
    rs = _rs()
    out, holders = {}, {}
    for b in rs.BADGE_CATALOG:
        out[f"badge:{b['id']}"] = rs.badge_cards.default_badge_card(b)
    for a, items in (rs._admin_load().get('badges') or {}).items():
        for b in items.values():
            k = f"badge:{b['id']}"
            out.setdefault(k, rs.badge_cards.default_badge_card({**b, 'tier': 4 if b.get('tone') == 'gold' else 3}))
            holders[k] = holders.get(k, 0) + 1
    for a, (at, rec) in list(rs._badge_cache.items()):
        if rs.time.time() - at < 86400:
            for b in (rec or {}).get('badges', []):
                k = f"badge:{b['id']}"
                out.setdefault(k, rs.badge_cards.default_badge_card(b))
                holders[k] = holders.get(k, 0) + 1
    col = rs._json_load(rs.COLLECTION_PATH, {})
    for s in rs._seasons()['seasons']:
        out[f"season:{s['id']}"] = rs.badge_cards.default_season_card(s)
        for w in rs._season_weeks(s):
            out[f"week:{s['id']}:w{w['week']}"] = rs.badge_cards.default_week_card(s, w)
    for items in col.values():
        for it in items:
            k = rs._collection_card_key(it)
            if k:
                holders[k] = holders.get(k, 0) + 1
    return out, holders


def _collection_card_key(it):
    if it.get('kind') == 'season':
        return f"season:{it.get('season')}"
    if it.get('kind') == 'weekly':
        return f"week:{it.get('season')}:w{it.get('week')}"
    return None


def _cards_all() -> dict:
    rs = _rs()
    hit = rs._cards_cache.get('all')
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1]
    defaults, holders = rs._card_defaults()
    edits = rs._json_load(rs.CARDS_PATH, {})
    pools = rs._pools()['pools']; d = rs._seasons()
    season_pct = {s['id']: float(s.get('badgeRewardPct') or 0) for s in d['seasons'] if s.get('reserveWallet')}
    cards = {k: {**rs.badge_cards.merge(v, edits.get(k)), 'holders': holders.get(k, 0), **rs.badge_cards.card_money(k, pools, d.get('reservePayouts') or {}, season_pct)}
             for k, v in defaults.items()}
    rs._cards_cache['all'] = (rs.time.time(), cards)
    return cards


async def _circle_destinations(circle_wallets=None) -> list:
    rs = _rs()
    d = rs._seasons()
    if circle_wallets is None:
        try:
            circle_wallets = (await rs._circle('GET', '/wallets')).get('wallets') or []
        except rs.HTTPException:
            circle_wallets = []
    snap = (rs._pulse_cache.get('owner') or (0, {}))[1]   # fee account owners, as last read on-chain by the money pulse
    fee_owners = [f['owner'] for f in snap.get('feeAccounts') or [] if f.get('owner')]
    return rs.money_pulse.known_destinations(sorted(rs._owner_wallets()), sorted(rs._admin_wallets()), fee_owners,
                                          [(f"Season reserve · {x['name']}", x['reserveWallet']) for x in d['seasons'] if x.get('reserveWallet')],
                                          [(f"Badge pool · {x['name']}", x['wallet']) for x in rs._pools()['pools']],
                                          rs._json_load(rs.ROUTES_PATH, {'routes': []}).get('routes', []), circle_wallets,
                                          rs._json_load(rs.CIRCLE_DEST_PATH, {'saved': []}).get('saved', []))


def _fuse_card_free_sol(card_sol, wallet_sol):
    """SOL a Fuse card's wallet may send out by hand: everything except the card's own cash (its trading money), less one network fee."""
    rs = _rs()
    return max(0.0, rs._fuse._f(wallet_sol) - rs._fuse._f(card_sol) - 0.00001)


async def _fuse_send_guard(wallet_id, token_id, amount):
    """🧯 A Circle send of SOL from a REAL Fuse card's wallet never takes the card's own cash (2026-11-11): the card's books would claim SOL
    that left. Withdraw from the card first (that moves the book), then send. Other wallets and tokens pass untouched."""
    rs = _rs()
    w = next((x for x in (await rs._circle_wallets_live()) or [] if x.get('id') == wallet_id), None)
    if not w:
        return
    row = next((b for b in w.get('balances') or [] if b.get('tokenId') == token_id), None)
    if not row or str(row.get('symbol') or '').upper() != 'SOL' or row.get('mint'):
        return
    cards = ((rs._json_load(rs.FUSE_HQ_PATH, {}) or {}).get('prime') or {}).get('cards') or {}
    for tid, c in cards.items():
        if not (c or {}).get('real'):
            continue
        v = rs._fw_public(tid)
        if v.get('wallet') != w.get('address'):
            continue
        r = v.get('reconciliation') or {}
        free = rs._fuse_card_free_sol(r.get('cardCashSol'), r.get('walletSol') if r.get('walletSol') is not None else row.get('amount'))
        if amount > free + 1e-9:
            raise rs.HTTPException(409, f"That would take the Fuse card's own trading cash. This wallet can send up to {free:.6f} SOL now. "
                                     "Withdraw from the card first (Fuse › Withdraw), then send. Nothing moved.")
        return


async def _sol_token_accounts(http, owner):
    rs = _rs()
    async def read(pg):   # a busy public node is retried twice (1s apart) before the wallet reads as "busy"
        for k in range(3):
            try:
                return await rs._rpc(http, 'getTokenAccountsByOwner', [owner, {'programId': pg}, {'encoding': 'jsonParsed'}], scan=False)
            except Exception as e:
                if k == 2:
                    return e
                await rs.asyncio.sleep(1.0)
    res = await rs.asyncio.gather(*[read(pg) for pg in rs._dust.TOKEN_PROGRAMS])
    out = []
    for pg, r in zip(rs._dust.TOKEN_PROGRAMS, res):
        if isinstance(r, Exception):
            raise rs.HTTPException(503, 'Solana RPC is busy — try again in a few seconds.')
        for a in (r or {}).get('value') or []:
            info = rs._parsed_info(a.get('account'))
            amt = info.get('tokenAmount') or {}
            if not info.get('mint'):
                continue
            out.append({'pubkey': a.get('pubkey'), 'program': pg, 'mint': info['mint'], 'owner': info.get('owner'), 'raw': int(amt.get('amount') or 0),
                        'decimals': int(amt.get('decimals') or 0), 'ui': rs._fuse._f(amt.get('uiAmount')), 'lamports': (a.get('account') or {}).get('lamports') or 0})
    return out


async def _cronos_batch(http, calls):
    """JSON-RPC calls → {id: result}, 10 a batch across the public nodes (a big batch comes back as ONE error object)."""
    rs = _rs()
    res = {}

    async def batch(chunk):
        for rpc_ in rs.CRONOS_RPCS:
            try:
                j = (await http.post(rpc_, json=chunk)).json()
                if isinstance(j, list):
                    return {x.get('id'): x.get('result') for x in j}
            except Exception:
                continue
        return {}
    for got in await rs.asyncio.gather(*[batch(calls[k:k + 10]) for k in range(0, len(calls), 10)]):
        res.update(got)
    return res


async def _cronos_candidates(http, address):
    """Every contract worth a balance read for this wallet: the swap router's list + a DEX list + what a wallet index says it holds."""
    rs = _rs()
    now = rs.time.time()
    hit = rs._lifi_tok_cache.get(25)
    if not hit or now - hit[0] > 600:
        try:
            r = await http.get('https://li.quest/v1/tokens', params={'chains': 25})
            toks = [t for t in ((r.json().get('tokens') or {}).get('25') or []) if t.get('address') and t['address'] != rs._dust.NATIVE_EVM]
            rs._lifi_tok_cache[25] = hit = (now, toks)
        except Exception:
            hit = hit or (0, [])
    dex = rs._cro_list_cache.get('dex')
    if not dex or now - dex[0] > 3600:
        try:
            r = await http.get(rs.CRONOS_DEX_LIST)
            dex = (now, [t for t in r.json() if isinstance(t, dict) and t.get('chainId') == 25]) if r.status_code == 200 else (dex or (0, []))
        except Exception:
            dex = dex or (0, [])
        rs._cro_list_cache['dex'] = dex
    idx = rs._cro_idx_cache.get(address.lower())
    if not idx or now - idx[0] > 60:
        got, ok = [], False
        try:
            r = await http.get(rs.CRONOS_WALLET_INDEX, params={'id': address, 'chain_id': 'cro', 'is_all': 'true'}, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                got, ok = rs._dust.index_tokens(r.json()), True
        except Exception:
            pass
        idx = (now, got, ok) if ok or not idx else idx   # a failed read keeps the last answer
        rs._cro_idx_cache[address.lower()] = idx
        if len(rs._cro_idx_cache) > 300:
            for k in sorted(rs._cro_idx_cache, key=lambda k: rs._cro_idx_cache[k][0])[:100]:
                rs._cro_idx_cache.pop(k, None)
    return rs._dust.merge_tokens(hit[1], dex[1], idx[1]), bool(len(idx) > 2 and idx[2])


async def _yt_search(q):
    rs = _rs()
    key = ('yt', q.lower())
    hit = rs._music_cache.get(key)
    if hit and rs.time.time() - hit[0] < 600:
        return hit[1]
    rows = []
    async with rs.httpx.AsyncClient(timeout=10, headers=rs._UA, follow_redirects=True) as http:
        try:
            r = await http.get('https://www.youtube.com/results', params={'search_query': q, 'sp': 'EgIQAQ%3D%3D'})
            rows = rs._music.yt_results(r.text)
        except Exception:
            rows = []
        if not rows:   # fallback: a public Piped node (same videos, its own JSON)
            try:
                j = (await http.get('https://api.piped.private.coffee/search', params={'q': q, 'filter': 'videos'})).json()
                rows = [{'id': (x.get('url') or '').split('v=')[-1][:11], 'title': x.get('title'), 'channel': x.get('uploaderName'), 'length': '', 'views': '',
                         'url': f"https://www.youtube.com{x.get('url')}", 'thumb': x.get('thumbnail')} for x in (j.get('items') or []) if x.get('type') == 'stream'][:20]
            except Exception:
                rows = []
    if len(rs._music_cache) > 400:
        rs._music_cache.clear()
    rs._music_cache[key] = (rs.time.time(), rows)
    return rows


async def _spotify_search(q):
    rs = _rs()
    cid, sec = rs.os.getenv('SPOTIFY_CLIENT_ID', ''), rs.os.getenv('SPOTIFY_CLIENT_SECRET', '')
    if not (cid and sec):
        return None
    async with rs.httpx.AsyncClient(timeout=8) as http:
        tok = rs._music_cache.get(('sp-token',))
        if not tok or rs.time.time() - tok[0] > 3000:
            r = await http.post('https://accounts.spotify.com/api/token', data={'grant_type': 'client_credentials'}, auth=(cid, sec))
            tok = rs._music_cache[('sp-token',)] = (rs.time.time(), r.json().get('access_token'))
        r = await http.get('https://api.spotify.com/v1/search', params={'q': q, 'type': 'track', 'limit': 10}, headers={'Authorization': f'Bearer {tok[1]}'})
        return rs._music.spotify_tracks(r.json())


def _internal_ok(request):
    rs = _rs()
    return bool(rs._internal_key()) and rs.hmac.compare_digest(request.headers.get('x-feeless-internal', ''), rs._internal_key())


def _agent_sol_to(cat_id):
    """Where an agent's SOL may go besides its own wrapped SOL: the Collective pot, and the top-up address its owner confirmed. Read from
    the server's own files, never from the request."""
    rs = _rs()
    out = []
    try:
        pot = ((rs._json_load(rs.DATA_DIR / 'colony.json', {}) or {}).get('wallet') or {}).get('address')
        out += [pot] if pot else []
        topup = ((((rs._json_load(rs.DATA_DIR / 'feecats.json', {}) or {}).get('cats') or {}).get(cat_id) or {}).get('topup') or {}).get('address')
        out += [topup] if topup else []
    except Exception:   # noqa: BLE001 — an unreadable file only narrows where it may send
        pass
    return out


async def _agent_circle_sign_send(body, key_, tx_, wid_, addr_):
    rs = _rs()
    acct_ = body.get('acct') == 'agent'   # 🟦 an agent's own wallet lives on the separate account; Fee's assigned wallet on the FEELESS one
    w_ = (await rs._circle('POST', '/wallet', {'id': wid_}, agent=True)).get('wallet') if acct_ else next((w for w in (await rs._circle_wallets_live()) or [] if w.get('id') == wid_), None)
    if not w_ or w_.get('address') != addr_:
        raise rs.HTTPException(403, 'That Circle wallet is not this agent\'s assigned wallet.')
    signed_ = await rs._circle('POST', '/sign', {'walletId': wid_, 'rawTransaction': tx_, 'memo': f"FEELESS agent {str(body.get('catId') or '')[:20]}"}, agent=acct_)
    sig_ = str(signed_.get('signature') or signed_.get('txHash') or '')
    if not signed_.get('signedTransaction') or not sig_:
        raise rs.HTTPException(502, 'Circle did not sign it.')
    async with rs._admin_lock:   # reloaded under the lock: an overlapping send's key is never overwritten by a stale copy
        rs._json_save(rs.AGENT_CIRCLE_SENT, {**rs._json_load(rs.AGENT_CIRCLE_SENT, {}), key_: sig_})   # written BEFORE the send
    async with rs.httpx.AsyncClient(timeout=20) as http_:
        took_ = await rs._krpc(http_, 'sendTransaction', [signed_['signedTransaction'], {'encoding': 'base64', 'maxRetries': 3, 'preflightCommitment': 'confirmed'}])
    if not took_:
        print(f"[agent send] {key_}: the first RPC refused it or gave no answer; broadcasting until its blockhash dies")
    rs.asyncio.create_task(rs._agent_send_loop(signed_['signedTransaction'], sig_))
    return {'signature': sig_}


async def _agent_send_loop(signed, sig, seconds=75):
    """📡 The keeper's rule on an agent's send too: one send through one busy node is why trades expire. The same signed bytes go to every node until the
    chain has them or the blockhash is dead. Same signature: it can only ever land once."""
    rs = _rs()
    end_ = rs.time.time() + seconds
    async with rs.httpx.AsyncClient(timeout=8) as http_:
        while rs.time.time() < end_:
            try:
                await rs._rpc_broadcast(http_, signed)
                await rs.asyncio.sleep(2.5)
                st_ = await rs._krpc(http_, 'getSignatureStatuses', [[sig]])
                if ((st_ or {}).get('value') or [None])[0]:
                    return
            except (rs.httpx.HTTPError, ValueError) as e:
                print(f'[agent send] {sig[:10]}: {str(e)[:80]}')
                await rs.asyncio.sleep(2.5)

