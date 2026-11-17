"""🧹 Free hourly call — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


def _predict_symbols():
    rs = _rs()
    sym = {r.get('mint'): r.get('symbol') for r in rs._runner_cands if r.get('mint') and r.get('symbol')}
    sym.update({r['mint']: r.get('symbol') for r in (rs._open_board() if rs._open_pairs else (rs._open_cache.get('rows') or [])) if r.get('mint') and r.get('symbol')})
    return sym


def _rm_rows():
    """🛡 Rep markets' coins: Pump's own trending board first, then the open board's busiest — each with its age and rug meter (the same read
    the trench list shows)."""
    rs = _rs()
    by = {r['mint']: r for r in (rs._open_board() if rs._open_pairs else (rs._open_cache.get('rows') or [])) if r.get('mint')}
    out, seen = [], set()
    for src, mints in (('ptrend', [r.get('mint') for r in (rs._lens_rows.get('ptrend') or [])[:12]]), ('open', list(by)[:40])):
        for m in mints:
            if not m or m in seen:
                continue
            seen.add(m); r = rs._with_tv(by.get(m) or {'mint': m})
            out.append({'mint': m, 'symbol': r.get('symbol') or (rs._predict_symbols().get(m)), 'src': src, 'ageH': r.get('ageH'), 'rug': (r.get('tv') or {}).get('rug')})
    return [r for r in out if r.get('symbol')]


async def _rm_tick(now):
    """Every warm pass: mark open markets on live prices, settle what can be decided (season points for the week's net), open the hour's markets."""
    rs = _rs()
    async with rs._rm_lock:
        st = rs._json_load(rs.REP_MARKETS_PATH, {}) or {}
        opn = [m for m in st.get('markets') or [] if m['state'] == 'open']
        if opn:
            px = await rs._jup_prices(sorted({m['mint'] for m in opn if m.get('mint')}), judge=True)
            for m in opn:
                if m.get('mint') and (px or {}).get(m['mint']):
                    rs._repm.mark(m, px[m['mint']], now)
        try:   # 🤖 live PoWs and PoPs open bid markets; their real results settle them
            async with rs.httpx.AsyncClient(timeout=5) as http_:
                rs._repm.sync_agents(st, (await http_.get('http://127.0.0.1:5088/api/cats/bids/feed')).json().get('rows'), now)
        except (rs.httpx.HTTPError, ValueError) as e:
            print(f'[rep-markets] agent feed: {str(e)[:100]}')
        done = rs._repm.settle(st, now)
        for m in done:
            for s_ in m['stakes']:
                b_ = rs._repm.bank(st, s_['w'], now); pts_ = rs._repm.season_pts(b_)
                if str(s_['w']).startswith('agent:'):   # an agent's chips never earn season points
                    continue
                if pts_ > b_.get('pts', 0):
                    rs.season_award(s_['w'], pts_ - b_.get('pts', 0), 'rep-market'); b_['pts'] = pts_
        hr = int(now // 3600)
        if st.get('openedHour') != hr:
            rows = rs._rm_rows()
            if rows:
                px = await rs._jup_prices([r['mint'] for r in rows[:30]], judge=True)
                rs._repm.new_markets(st, rows, px or {}, now)
                st['openedHour'] = hr
        rs._json_save(rs.REP_MARKETS_PATH, st)


def _rep_of(wallets):
    rs = _rs()
    out = {}
    for w in wallets:
        hit = rs._trust_cache.get(w)
        if hit:
            out[w] = rs._fuse._f((hit[1] or {}).get('score'))
        else:
            out[w] = 50.0
            try:
                rs.asyncio.get_running_loop().create_task(rs._trust_fill(w))
            except RuntimeError:
                pass
    return out


async def _predict_tick(now):
    """Every ~minute: settle rounds whose hour is over (biggest move wins, points via season_award, quest events, inbox note) and open this hour's ballot."""
    rs = _rs()
    import predict as _pr
    async with rs._predict_lock:
        d = rs._json_load(rs.PREDICT_PATH, {'rounds': {}, 'players': {}}); rounds, players = d.setdefault('rounds', {}), d.setdefault('players', {})
        due = [r for r in rounds.values() if r.get('status') == 'open' and now >= r['closesAt']]
        if due:
            px = await rs._jup_prices(sorted({c['mint'] for r in due for c in r['cands']}), judge=True)
            for r in due:
                res = _pr.settle(r, px or {})
                r.update(winner=res['winner'], moves=res['moves'], settledAt=now, status='settled' if res['winner'] else 'void')
                if res['winner']:
                    win_sym = next((c['symbol'] for c in r['cands'] if c['mint'] == res['winner']), '')
                    for w, pts in _pr.award(players, r, res['winner'], now):
                        rs.season_award(w, pts, 'free-call')
                        try:
                            rs.notify(w, 'free-call', f"⚡ You called it: ${win_sym} led the hour (+{pts} pts)", url='/terminal/radar', once=f"fcall:{r['id']}", push=False, meta={'source': 'free-call'})
                        except Exception:
                            pass
        rid = _pr.round_id(now)
        if str(rid) not in rounds and now - rid < 3000:
            lists = {k: v for k, v in rs._lens_rows.items()}
            mints = [row.get('mint') for k, _l in _pr.DOORS for row in (lists.get(k) or [])[:8]]
            px = await rs._jup_prices([m for m in mints if m], judge=True)
            cands = _pr.candidates(lists, px or {}, rs._predict_symbols())
            if len(cands) >= 2:
                rounds[str(rid)] = _pr.new_round(now, cands)
        for k in sorted(rounds)[:-48]:
            rounds.pop(k, None)
        rs._json_save(rs.PREDICT_PATH, d)


def _owner_edge_rec():
    """🎯 The owner's own record by entry type (owner_edge.py): their logged hand picks joined to what the card's closed pieces did. 5 min cache."""
    rs = _rs()
    import owner_edge as _oe, pay_map as _pm
    now = rs.time.time()
    if rs._myedge_cache['data'] and now - rs._myedge_cache['at'] < 300:
        return rs._myedge_cache['data']
    ledger = list(reversed(rs._fw_full_ledger()))   # newest first, from the in-memory copy (re-parsing 100K rows blocked the loop)
    log = rs._json_load(rs.PICK_STYLE_PATH, {}).get('log') or []
    rec = _oe.records(log, _pm.pieces(ledger, 'degen'))
    rec['thresholds'] = {'chase5m': _oe.CHASE_5M, 'thinVol': _oe.THIN_VOL, 'setupDip': _oe.SETUP_DIP, 'setupVol': _oe.SETUP_VOL}
    rs._myedge_cache.update(at=now, data=rec)
    return rec


def _is_keeper():
    """🔒 Only ONE process on this machine may tick the cards and trade the Fuse wallet (see single.py). A process that is shutting
    down, or that does not hold the lock, does nothing."""
    rs = _rs()
    if rs._keeper_state['stopping'] or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return not rs._keeper_state['stopping']
    ok = rs._single.acquire(rs.KEEPER_LOCK)
    if not ok and rs.time.time() - rs._keeper_state['said'] > 300:
        rs._keeper_state['said'] = rs.time.time(); print('keeper: another backend process holds the keeper lock — this one will not trade')
    return ok


async def _prime_tick(now):
    rs = _rs()
    if not rs._is_keeper():
        return 0
    async with rs._prime_tick_lock:   # the warm loop and the 🔔 round bell never run two ticks at once
        n = await rs._prime_tick_inner(now)
    try:
        await rs._fw_tick(rs.time.time())   # 👛 real tier cards follow the engine with real swaps (its OWN clock: the tier tick above took seconds)
    except Exception as e:
        print('fuse wallet:', e)
    return n


async def _prime_bell_loop():
    """🔔 Wake exactly when the next tier round is due (the 10s countdown on screen ends on time, never at 00:00 for a minute)."""
    rs = _rs()
    await rs.asyncio.sleep(30)
    while True:
        try:
            cards = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
            rcfg = rs._prime_real_cfg(); pcfg_b = rs._prime_cfg(); locks_b = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('locks') or {}
            # ⏱ every card has its OWN clock: the real card's, a locked tier's, or the tier's entry in `clocks`
            rot_of = lambda c: (rcfg if c.get('real') else rs._prime.clean_cfg(locks_b[c['tpl']]) if c.get('tpl') in locks_b else rs._prime.tier_cfg(pcfg_b, c.get('tpl')))['rotateHours'] * 3600
            # deal time = round end + 10s bell (💵 real: `dealLeadSec` earlier · a floored card wakes when its rest ends, not every 5s)
            due = min(((rs._fuse._f(c['flooredAt']) + max(60.0, rs._fuse._f(rcfg.get('floorRestMins') if c.get('real') else 0) * 60)) if c.get('flooredAt') else
                       (rs._fuse._f(c.get('lastRotateAt')) + rot_of(c) + rs._prime.BELL_SEC - (rs._fuse._f(rcfg.get('dealLeadSec')) if c.get('real') else 0))
                       for c in cards.values() if c.get('lastRotateAt')), default=rs.time.time() + 60)
            wait = due - rs.time.time()
            kick = rs._FW_KICK.get('at')   # ⏳ a real buy was just refused → re-pick that seat 15s later (never a whole tick later)
            if kick and rs.time.time() >= kick + rs._fw.RETRY_SEC:
                rs._FW_KICK.pop('at', None)
                wait = min(wait, 0.0)
            if 0.5 < wait <= 12:   # 🔔 inside the 10s countdown: warm the candidates + prices now, so the re-deal is instant at 0
                await rs._prime_candidates()
                await rs.asyncio.sleep(max(0.0, due - rs.time.time()))
                wait = 0
            if wait <= 0.5:
                await rs._prime_tick(rs.time.time())
                wait = 5
            if rs._FW_KICK.get('at'):
                wait = min(wait, rs._FW_KICK['at'] + rs._fw.RETRY_SEC - rs.time.time())
            await rs.asyncio.sleep(max(1.0, min(60.0, wait + 0.2)))
        except Exception as e:
            print('prime bell:', e)
            await rs.asyncio.sleep(30)


async def _smart_track(now):
    """🐳 Every ~2 min: read the tapes of the real card's coins + Coming up's top 8, note each wallet's first buy, settle buys an hour old,
    re-derive the smart set, flag coins a smart wallet is buying now. The radar's own record = edge proof key 'smart'."""
    rs = _rs()
    try:
        rows = [r for r in rs._edge_rank()[:8] if r.get('pairAddress')]
        held = [l for c in rs._prime_cards().values() if (c or {}).get('real') for l in c.get('legs') or [] if l.get('pairAddress') and l.get('mint') and l.get('symbol') != 'SOL']
        pm = {r['pairAddress']: r['mint'] for r in rows}
        pm.update({l['pairAddress']: l['mint'] for l in held})
        await rs._flow_fetch(list(pm), max_age=60)
        st = rs._json_load(rs.SMART_PATH, {})
        for p_, m_ in pm.items():
            at_, tr_ = rs._flow_trades.get(p_, (0, []))
            if tr_ and now - at_ < 120:
                st = rs._dg.note_buys(st, m_, tr_, now)
        due = list({b['m'] for b in st.get('buys') or [] if now - rs._fuse._f(b.get('at')) >= rs._dg.SETTLE_SEC})
        jp = await rs._jup_prices(due, judge=True) if due else {}
        st = rs._dg.settle(st, lambda m: (jp or {}).get(m), now)
        await rs.asyncio.to_thread(rs._json_save, rs.SMART_PATH, st)   # ⚙ a big file: write it off the loop (Lag catcher: 1.9s stalls)
        rs._smart.update(set=rs._dg.smart_set(st), at=now)
        for p_, m_ in pm.items():
            at_, tr_ = rs._flow_trades.get(p_, (0, []))
            hits = rs._dg.smart_hits(tr_, rs._smart['set']) if now - at_ < 120 else []
            if hits:
                rs._smart_now[m_] = (now, hits)
    except Exception as e:
        print('smart wallets:', e)


def _smart_on(mint):
    rs = _rs()
    at, hits = rs._smart_now.get(mint, (0, []))
    return hits if rs.time.time() - at < 600 else []


def _learn_drops(before, after, price_of, now):
    """🧠 Coins that LEFT a real card between two versions of it (gone, turned into a reserved seat, or replaced) → one lesson each."""
    rs = _rs()
    if not (before and before.get('real') and after):
        return 0
    stay = {l.get('mint') for l in after.get('legs') or [] if not l.get('placeholder') and rs._fuse._f(l.get('units')) > 0}
    gone = [l for l in before.get('legs') or [] if l.get('mint') and not l.get('placeholder') and rs._fuse._f(l.get('units')) > 0 and l.get('mint') not in stay and l.get('symbol') != 'SOL']
    if not gone:
        return 0
    st = rs._json_load(rs.REAL_LEARN_PATH, {})
    why = ((after.get('events') or [{}])[-1] or {}).get('kind') or ''
    for l in gone:
        st = rs._rl.note(st, l, price_of(l), now, why)
    rs._json_save(rs.REAL_LEARN_PATH, st)
    rs._rl_cache['at'] = 0.0
    return len(gone)


def _real_table():
    rs = _rs()
    if rs.time.time() - rs._rl_cache['at'] > 120:
        rs._rl_cache.update(at=rs.time.time(), tbl=rs._rl.table(rs._json_load(rs.REAL_LEARN_PATH, {})))
    return rs._rl_cache['tbl']


async def _flow_fetch(pairs, max_age=12.0):
    """🌊 The last 90s of real swaps for these pools (candles service trade tape, its own 15s cache) → {pair: window}. Parallel, 4s budget."""
    rs = _rs()
    now = rs.time.time()
    need = [p for p in dict.fromkeys(pairs) if p and now - rs._flow_now.get(p, (0, None))[0] > max_age]
    async def one(http, p):
        try:
            r = await http.get(f'http://127.0.0.1:5099/api/candles/trades/solana/{p}')
            tr = (r.json() or {}).get('trades') or []
            rs._flow_trades[p] = (rs.time.time(), tr)   # 🐳 the raw tape: the smart-wallet radar reads who bought
            return p, rs._flow.window(tr, rs.time.time())
        except Exception:
            return p, None
    if need and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        async with rs.httpx.AsyncClient(timeout=4) as http:
            for p, w in await rs.asyncio.gather(*[one(http, p) for p in need[:12]]):
                rs._flow_now[p] = (rs.time.time(), w)
    return {p: (rs._flow_now.get(p) or (0, None))[1] for p in pairs}


def _flow_mark(mint, v, sym, now, held=False):
    """🌊 Keep the newest buy / sell vital per coin for the page (held seats + coins checked before a seat) — bounded, 5 min."""
    rs = _rs()
    fm = rs._office.setdefault('flow', {})
    fm[mint] = {**v, 'at': round(now, 1), 'sym': sym, 'held': held}
    if len(fm) > 60:
        for k_ in [k_ for k_, x_ in fm.items() if now - rs._fuse._f(x_.get('at')) > 300][:40]:
            fm.pop(k_, None)


def _flow_intel(mint):
    """The wallets the rug radar watches for this coin: creator + top-10 wallets + bundle / sniper wallets (scan cache only)."""
    rs = _rs()
    hit = rs._intel_cache.get(mint)
    it = (hit[1] if hit else {}) or {}
    watch = {h.get('owner') for h in (it.get('topHolders') or [])[:10] if h.get('kind') == 'wallet' and h.get('owner')}
    watch |= set((it.get('bundledWallets') or [])[:30]) | set((it.get('sniperWallets') or [])[:30])
    watch.discard(it.get('creator'))
    return {'creator': it.get('creator'), 'watch': watch}


def _consig_plans(now):
    """🤵 The Consigliere's live plan per coin type, re-learned from the real record every 5 min (consigliere.plans)."""
    rs = _rs()
    if now - rs._consig_c['at'] > 300:
        try:
            mtp_ = rs._seat.models_take((rs._g4_mem.get() or {}).get('log'), now)   # 🧠 the models' own take line competes with the spikes — kept only if it pays on real trades
            rs._consig_c.update(at=now, v=rs._cg.plans((rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or [], (rs._after_mem.get() or {}).get('done') or {}, rs._ap.key_of, extra_spikes=(mtp_,) if mtp_ else ()))
            rs._office['consigliere'] = rs._consig_c['v']
        except Exception as e:
            print('consigliere:', str(e)[:80])
            rs._consig_c['at'] = now
    return rs._consig_c['v']


async def _reaper_lines(now, px):
    """☠ REAPER TRADES HIS COINS LIVE (owner, 2026-10-18: "I barely see Reaper adjusting TP / SL"): for every agent coin on the real card, the
    tape since our buy is tagged (chart_wallets: dev · snipers · bundles · top holders · whales · top traders) and Reaper moves its lines
    (office.reaper_adjust) — written as the coin's own aiTp / aiSl, which his rules R6m / R5m obey. Your coins, your lines, OSSY / G4's seat: never."""
    rs = _rs()
    async with rs._prime_tick_lock, rs._admin_lock:   # 🔒 SITE-8: every fuse_hq save holds the admin lock (was the tick lock only)
        d_ = rs._json_load(rs.FUSE_HQ_PATH, {}); cs_ = dict((d_.get('prime') or {}).get('cards') or {}); hit_ = False
        reps_ = {r_.get('mint'): r_ for r_ in rs._office.get('reports') or []}
        for tid_, c_ in cs_.items():
            if not (c_ and c_.get('real') and c_.get('holdBy') == 'agents'):
                continue
            for l in c_.get('legs') or []:
                m_ = l.get('mint')
                if (not rs._uni.is_agent(l) or l.get('aiSeat') or l.get('picked') or l.get('ownerLvAt') or l.get('placeholder') or not l.get('real')
                        or rs._fuse._f(l.get('units')) <= 0 or now - rs._fuse._f(l.get('reapAdjAt')) < rs.REAP_ADJ_SEC):
                    continue
                tr_ = rs._flow_trades.get(l.get('pairAddress'))
                pxn, ent = rs._fuse._f(px.get(m_)), rs._fuse._f(l.get('entry'))
                if not tr_ or now - tr_[0] > 30 or pxn <= 0 or ent <= 0:
                    continue
                wm_ = rs._cw.moves_since(rs._cw.tag_trades(tr_[1], (rs._intel_cache.get(m_) or (0, None))[1] or {}), rs._fuse._f(l.get('at')))
                rp_ = reps_.get(m_) or {}
                adj_ = rs._of.reaper_adjust((pxn / ent - 1) * 100, rs._fuse._f(rp_.get('take')), rs._fuse._f(rp_.get('stop')), wm_, l.get('aiTp'), l.get('aiSl'))
                if not adj_:
                    continue
                if adj_.get('tp'):
                    l['aiTp'] = adj_['tp']
                if adj_.get('sl'):
                    l['aiSl'] = adj_['sl']
                l['aiBy'], l['reapAdjAt'] = 'Reaper', now
                c_.setdefault('events', []).append({'at': now, 'kind': 'agent', 'symbol': l.get('symbol'), 'mint': m_, 'why': f"☠ Reaper moved ${l.get('symbol')}: {adj_['why']} — {wm_['words']}"})
                hit_ = True
        if hit_:
            d_['prime'] = {**(d_.get('prime') or {}), 'cards': cs_}; rs._json_save(rs.FUSE_HQ_PATH, d_)
    return hit_


async def _flow_guard(now, px):
    """🌊 + 🚨 on the real card(s): read each held coin's tape, sell what flow / the rug radar flags (like a fast stop), score each exit."""
    rs = _rs()
    rcfg = rs._prime_real_cfg()
    all_c = [c for c in rs._prime_cards().values() if c.get('real') and not c.get('flooredAt')]
    cards = [c for c in all_c if not c.get('holdAll')]
    # 🎮 the AGENTS' seats: their tape is read on the same cadence (Reaper's R4 dump + R4r rug radar stand on it — the agents' card is held,
    # so the engine's flow exit never touched it and the tape sat 60–160s old); nothing here exits an agent seat, Reaper decides
    agent_legs = [l for c in all_c if c.get('holdAll') and c.get('holdBy') == 'agents' for l in c.get('legs') or [] if rs._flow.watched(l) and not rs._prime.safe_anchor(l)]
    engine_on = not (rcfg.get('flowExit', 'off') == 'off' and not rcfg.get('rugRadar', True))
    legs = [l for c in cards for l in c.get('legs') or [] if rs._flow.watched(l) and not rs._prime.safe_anchor(l)] if engine_on else []
    if not legs and not agent_legs:
        return False
    flows = await rs._flow_fetch([l.get('pairAddress') for l in legs + agent_legs])
    if agent_legs:
        try:
            await rs._reaper_lines(now, px)   # ☠ Reaper moves his own TP / SL from what the wallets did since the buy (never a sale here)
        except Exception as e:
            print('reaper lines:', str(e)[:100])
    if not legs:
        return False
    intel = {l.get('mint'): rs._flow_intel(l.get('mint')) for l in legs}
    hit_any, noted = False, []
    async with rs._prime_tick_lock, rs._admin_lock:   # 🔒 SITE-8: every fuse_hq save holds the admin lock (was the tick lock only)
        d_ = rs._json_load(rs.FUSE_HQ_PATH, {}); cs_ = dict((d_.get('prime') or {}).get('cards') or {})
        for tid_, c_ in list(cs_.items()):
            if not (c_ and c_.get('real') and not c_.get('flooredAt') and not c_.get('holdAll')):
                continue
            nw_, hits = rs._flow.flow_exits(c_, flows, px, rcfg, now, rs._prime.sell_usd, intel)
            if hits:
                rs._learn_drops(c_, nw_, lambda l: rs._fuse._f(px.get(l.get('mint'))), now)
                cs_[tid_] = rs._prime.note_dropped(c_, nw_, now, rcfg['rotateHours'], {l.get('pairAddress'): px.get(l.get('mint')) for l in c_.get('legs') or []})
                hit_any = True
                noted += [(e.get('flowKind') or e.get('kind'), e.get('mint'), e.get('px')) for e in nw_['events'][-len(hits):]]   # 🏔 climax sells keep their own record
        if hit_any:
            d_['prime'] = {**(d_.get('prime') or {}), 'cards': cs_}; rs._json_save(rs.FUSE_HQ_PATH, d_)
    if noted:   # 📏 the exit's own record: the coin's move in the hour AFTER we sold (negative = the exit saved money)
        st = rs._json_load(rs.FLOW_PROOF_PATH, {})
        passing = {}
        for k, m, p_ in noted:
            if m and rs._fuse._f(p_) > 0:
                passing.setdefault(k, []).append((m, rs._fuse._f(p_)))
        rs._json_save(rs.FLOW_PROOF_PATH, rs._trench.meta_track(st, passing, lambda m: None, now, keys=tuple(dict.fromkeys(list(st) + list(passing)))))
    return hit_any


async def _flow_settle(now):
    """Settle flow / rug exits an hour after they sold (with the lens pass)."""
    rs = _rs()
    try:
        st = rs._json_load(rs.FLOW_PROOF_PATH, {})
        due = [m for s_ in st.values() for m, o in (s_.get('open') or {}).items() if now - rs._fuse._f(o.get('at')) >= rs._trench.PROOF_SEC]
        if due:
            jp = await rs._jup_prices(due, judge=True)
            rs._json_save(rs.FLOW_PROOF_PATH, rs._trench.meta_track(st, {}, lambda m: (jp or {}).get(m), now, keys=tuple(st)))
    except Exception as e:
        print('flow settle:', e)


async def _limit_check(now):
    """🎯 LIMIT ORDERS: every guard pass, ONE batched live-price read for the real cards' limits; a crossed line hands the order to the card's
    NORMAL path (buy → your seat pick / pick swap now · sell → ✂ to card cash) and the keeper is kicked. It never signs anything itself."""
    rs = _rs()
    cards_ = [c for c in rs._prime_cards().values() if c.get('real') and c.get('limits')]
    ms_ = sorted({x.get('mint') for c in cards_ for x in c.get('limits') or [] if x.get('mint')})
    if not ms_:
        return
    px_ = await rs._live_px(ms_)
    fired = False
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
        for tpl_, c in list(cards.items()):
            if not (c.get('real') and c.get('limits')):
                continue
            hit, keep, gone = rs._lim.due(c, px_, now)
            if not hit and not gone:
                continue
            c = {**c, 'limits': keep, 'events': list(c.get('events') or [])}
            for x in hit:
                try:
                    if x['side'] == 'buy':
                        cand = {**x['cand'], 'price': x['firedPx']}
                        c = rs._prime.queue_seat(c, cand, more=True) if x['target'] == '__seat__' else rs._prime.queue_swap(c, x['target'], {**cand, 'now': True})
                    else:
                        c = rs._prime.sell_leg_to_cash(c, x['pair'], {x['pair']: x['firedPx']}, now, x.get('pct') or 100)
                    c['events'].append({'at': now, 'kind': 'limit', 'symbol': x.get('symbol'), 'why': f"{rs._lim.word(x)} — hit at {x['firedPx']:.6g}"})
                    fired = True
                except Exception as e:
                    c['events'].append({'at': now, 'kind': 'limit', 'symbol': x.get('symbol'), 'why': f"{rs._lim.word(x)} — hit, but could not be placed: {str(e)[:80]}"})
            for x in gone:
                c['events'].append({'at': now, 'kind': 'limit', 'symbol': x.get('symbol'), 'why': f"{rs._lim.word(x)} — expired"})
            cards[tpl_] = c
        rs._json_save(rs.FUSE_HQ_PATH, d)
    if fired:
        rs._fw_kick_now(); rs.asyncio.ensure_future(rs._prime_tick(rs.time.time()))


async def _real_guard_loop():
    """⚡ FAST GUARD for real-money cards: every ~10s ONE batched Jupiter price read for the coins a real card holds; a coin at
    its stop / instant-swap line (or a rider off its trail) wakes the tier tick at once instead of waiting for the next
    ~1-minute pass. Reads only; every decision and every order still goes through the normal tick + keeper checks."""
    rs = _rs()
    await rs.asyncio.sleep(45)
    while True:
        try:
            if rs._is_keeper():
                # 🎮 a card the AGENTS control (holdAll by 'agents') is read too: its seats get the same fresh price every ~6s (P/L velocity +
                # Reaper's hard lines wake the tick) — the engine's own fast stop / instant swap still act only on cards the engine runs
                cards_all = [c for c in rs._prime_cards().values() if c.get('real') and not c.get('flooredAt') and (not c.get('holdAll') or c.get('holdBy') == 'agents')]
                cards = [c for c in cards_all if not c.get('holdAll')]
                agents_c = [c for c in cards_all if c.get('holdAll')]
                try:
                    await rs._limit_check(rs.time.time())
                except Exception as e:
                    print('limit check:', str(e)[:100])
                rs._guard_agents['held'] = any(not l.get('placeholder') and l.get('mint') for c in agents_c for l in c.get('legs') or [])
                mints = [l.get('mint') for c in cards_all for l in c.get('legs') or [] if l.get('mint') and not rs._prime.safe_anchor(l)]
                try:   # 🪑 EMPTY-SEAT HEARTBEAT (owner: "no seat should be empty, 30 secs to choose"): while an agent seat is empty the tier tick runs at
                    # least every SEAT_HEARTBEAT_SEC, so the 30-second decision (cleared → best available) happens on time; the tick decides, nothing else
                    now_h, seat_h = rs.time.time(), rs._agents.get('seat') or {}
                    if (agents_c and seat_h.get('empty') and seat_h.get('movesLeft') and not rs._prime_tick_lock.locked()
                            and now_h - rs._fuse._f(rs._office.get('tickAt')) >= rs.SEAT_HEARTBEAT_SEC and now_h - rs._fuse._f(rs._office.get('heartAt')) >= rs.SEAT_HEARTBEAT_SEC):
                        rs._office['heartAt'] = now_h; rs._office['heartbeats'] = int(rs._office.get('heartbeats') or 0) + 1
                        rs.asyncio.ensure_future(rs._prime_tick(now_h))
                except Exception as e:
                    print('seat heartbeat:', e)
                if mints:
                    for m in [l.get('mint') for c in cards for l in c.get('legs') or [] if l.get('mint') and not rs._prime.safe_anchor(l)]:
                        rs._jup_px_cache.pop(m, None)   # a FRESH read for the ENGINE's stops (the shared 20s cache is too slow for a stop) — the agents' seats ride the shared cache (Reaper's ticks act on them; no extra Jupiter calls)
                    px = await rs._jup_prices(mints)
                    am_ = [l.get('mint') for c in agents_c for l in c.get('legs') or [] if l.get('mint') and not l.get('placeholder')]
                    if am_:   # ⚡ the agents' seats are judged on the LIVE chart price (≤ 5s old, 1s after a swap), not the shared 20s cache: Reaper's stop
                        try:  # / trail in `fast_reap` acted on a price up to 26s old — stops set at −12…−25% were first SEEN at −21…−84%
                            px = {**px, **(await rs._live_px(am_))}
                        except Exception as e:
                            print('guard live px:', e)
                    rcfg = rs._prime_real_cfg(); now = rs.time.time()
                    wake_ = False
                    for c in agents_c:   # 📈 one real valuation read per agent seat + ☠ Reaper's hard lines (its stop · −45% · your stop) wake the tick at once
                        rs._office_vels(c, px, now)
                        stops_ = {r_.get('mint'): rs._fuse._f(r_.get('stop')) for r_ in rs._office.get('reports') or [] if r_.get('stop') is not None}
                        for m_ in rs._so.hard_cross(c.get('legs'), px, stops_, rs._fuse._f(rs._oe.policy(rcfg).get('sl')) or None, rs._ci.CATASTROPHIC_STOP):
                            if now - rs._guard_seen.get(m_, 0) >= 30:
                                rs._guard_seen[m_] = now; wake_ = True
                    if agents_c:
                        try:   # ⚡ the chart drives the timing: a material live move on a seat / a waiting candidate wakes Reaper / Trigger now
                            wake_ = (await rs._market_wake(agents_c, now)) or wake_
                        except Exception as e:
                            print('market wake:', e)
                    if wake_:
                        await rs._prime_tick(rs.time.time())
                    if now - rs._flow_at['t'] >= rs.FLOW_EVERY:   # 🌊 + 🚨 flow exits and the rug radar, every ~15s
                        rs._flow_at['t'] = now
                        if await rs._flow_guard(now, px):
                            try:
                                await rs._fw_tick(now)
                            except Exception as e:
                                print('flow exit keeper:', str(e)[:120])
                            await rs._prime_tick(rs.time.time())
                    # ☠⚡ AGENT SEATS: the card is held by the agents (`holdAll`) and their coins carry no card stop, so `fast_stop` never ran
                    # for them — Reaper's stop for each seat is applied here, every 6s, not at the next tick
                    try:
                        reaped_ = False
                        async with rs._prime_tick_lock, rs._admin_lock:   # 🔒 SITE-8: every fuse_hq save holds the admin lock (was the tick lock only)
                            d_ = rs._json_load(rs.FUSE_HQ_PATH, {}); cs_ = dict((d_.get('prime') or {}).get('cards') or {})
                            for tid_, c_ in list(cs_.items()):
                                if not (c_ and c_.get('real')):
                                    continue
                                hits_ = rs._of.fast_reap(c_.get('legs'), px, rs._office.get('pos') or {}, now, rs._office_state(), prev=rs._reap_prev, ai_words=rs._ai_exit_words(None, now))
                                try:   # 🎯 OSSY / G4's take-profit, every few seconds: honoured, or raised on a volume rush (office.rush_take)
                                    fl_ = {l.get('pairAddress'): rs._flow.vital(w_) for l in c_.get('legs') or [] for at_, w_ in [(rs._flow_now.get(l.get('pairAddress')) or (0, None))] if w_ and now - rs._fuse._f(at_) <= 90}
                                    tp_pulls_, tp_raise_ = rs._of.rush_take(c_.get('legs'), px, fl_, now)
                                    if tp_raise_:
                                        rz_ = {pr_: (pt_, wy_) for pr_, pt_, wy_ in tp_raise_}
                                        c_ = {**c_, 'legs': [({**l, **rz_[l.get('pairAddress')][0]} if l.get('pairAddress') in rz_ else l) for l in c_.get('legs') or []],
                                              'events': (list(c_.get('events') or []) + [{'at': now, 'kind': 'agent', 'move': 'lines', 'why': wy_} for _p, (_t, wy_) in rz_.items()])[-200:]}
                                        cs_[tid_] = c_; reaped_ = True
                                    hits_ = list(hits_) + [h_ for h_ in tp_pulls_ if h_[0] not in {x_[0] for x_ in hits_}]
                                except Exception as e:
                                    print('rush take:', str(e)[:120])
                                rs._reap_prev.update({m_: (now, rs._fuse._f(v_)) for m_, v_ in (px or {}).items() if rs._fuse._f(v_) > 0})   # 🕯 the last live read per coin (spike confirm)
                                nw_ = c_
                                for pair_, why_ in hits_:
                                    try:
                                        nw_ = rs._prime.agent_pull(nw_, pair_, {pair_: px.get(next((l.get('mint') for l in nw_.get('legs') or [] if l.get('pairAddress') == pair_), None))}, {}, now, why_)
                                        nw_['agentExitAt'] = now
                                        rs._tk.KERNEL.note('reaper', 'EXIT (live chart)', str(why_)[:140], now, mint=next((l.get('mint') for l in c_.get('legs') or [] if l.get('pairAddress') == pair_), None), key=f'fast:{int(now)}')
                                    except ValueError:
                                        pass
                                if nw_ is not c_:
                                    rs._learn_drops(c_, nw_, lambda l: rs._fuse._f(px.get(l.get('mint'))), now)
                                    cs_[tid_] = nw_; reaped_ = True
                            if reaped_:
                                d_['prime'] = {**(d_.get('prime') or {}), 'cards': cs_}; rs._json_save(rs.FUSE_HQ_PATH, d_)
                        if reaped_:
                            await rs._fw_tick(now)
                            await rs._prime_tick(rs.time.time())
                    except Exception as e:
                        print('fast reap:', str(e)[:120])
                    hit = [s for c in cards for s in rs._prime.guard_hits(c, px, rcfg)]
                    due = [l.get('mint') for c in cards for l in c.get('legs') or [] if l.get('symbol') in hit and now - rs._guard_seen.get(l.get('mint'), 0) >= 30]
                    if due:
                        rs._guard_seen.update({m: now for m in due})
                        # ⚡ FAST STOP first: the coin at its stop leaves the card and the keeper sells NOW; the full tick (refill,
                        # riders, instant swaps) runs after. Waking the whole tick first cost ~2 minutes ($AGENCY: −15% stop sold −31%).
                        stopped = False
                        async with rs._prime_tick_lock, rs._admin_lock:   # 🔒 SITE-8: every fuse_hq save holds the admin lock (was the tick lock only)
                            d_ = rs._json_load(rs.FUSE_HQ_PATH, {}); cs_ = dict((d_.get('prime') or {}).get('cards') or {})
                            for tid_, c_ in list(cs_.items()):
                                if c_ and c_.get('real') and not c_.get('flooredAt') and not c_.get('holdAll'):
                                    nw_ = rs._prime.fast_stop(c_, px, rcfg, now)
                                    if nw_ is not c_:
                                        rs._learn_drops(c_, nw_, lambda l: rs._fuse._f(px.get(l.get('mint'))), now)
                                        cs_[tid_] = rs._prime.note_dropped(c_, nw_, now, rcfg['rotateHours'], {l.get('pairAddress'): px.get(l.get('mint')) for l in c_.get('legs') or []})
                                        stopped = True
                            if stopped:
                                d_['prime'] = {**(d_.get('prime') or {}), 'cards': cs_}; rs._json_save(rs.FUSE_HQ_PATH, d_)
                        if stopped:
                            try:
                                await rs._fw_tick(now)
                            except Exception as e:
                                print('fast stop keeper:', str(e)[:120])
                        await rs._prime_tick(rs.time.time())
        except Exception as e:
            print('real guard:', str(e)[:120])
        await rs.asyncio.sleep(rs.AGENT_GUARD_SEC if rs._guard_agents['held'] else rs._prime.GUARD_SEC)


def _fw_market_rows(cards, books):
    """Every pair whose live price can affect a card or its confirmed real-money book."""
    rows = {}
    for c in (cards or {}).values():
        for l in list(c.get('legs') or []) + list((c.get('parked') or {}).values()):
            if l.get('pairAddress'):
                rows[l['pairAddress']] = {'pairAddress': l['pairAddress'], 'mint': l.get('mint')}
    for b in (books or {}).values():
        for mint, l in (b.get('legs') or {}).items():
            if l.get('pair'):
                rows[l['pair']] = {'pairAddress': l['pair'], 'mint': mint}
    return list(rows.values())


async def _prime_unique_fix(now):
    """🃏 Once: undo "Add to all cards" — every paper card gets its OWN exits back (its explicit per-card edits are kept; any exit key it
    lost to the shared edit returns to that card's unique default; the shared TP / stop go back to 'tier'). The real card is never touched."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        if pr.get('uniqueFix') == rs.PRIME_UNIQUE:
            return False
        cfg = rs._prime.clean_cfg(pr.get('cfg') or {})
        cfg['tierCfg'] = rs._prime.unique_exits(cfg['tierCfg'])
        cfg['tp'] = cfg['sl'] = 0.0
        pr['cfg'] = rs._prime.clean_cfg(cfg); pr['uniqueFix'] = rs.PRIME_UNIQUE
        rs._json_save(rs.FUSE_HQ_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, 'engine-auto', 'arena-prime', 'every paper card back on its own unique exits (real card untouched)'); rs._admin_save(ad)
    return True


def _cook_warn(card, pair, ack, rcfg=None):
    """⏳ LET IT COOK: a real card's hand exit of a coin held under `pickLockMins` comes back as a 409 warning (the owner taps "do it anyway"
    and the same request goes again with `ack`). Never a block, never on paper cards, never on the engine's own exits."""
    rs = _rs()
    if ack or not (card or {}).get('real'):
        return
    cfg_ = rcfg if rcfg is not None else rs._prime.clean_cfg((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {})
    left = rs._prime.pick_lock(card, pair, cfg_, rs.time.time())
    if left:
        l = next((x for x in card.get('legs') or [] if x.get('pairAddress') == pair), {})
        raise rs.HTTPException(409, f"⚠ ⏳ ${l.get('symbol')} was bought {max(0, int(cfg_['pickLockMins']) - left)} min ago — your lock is {int(cfg_['pickLockMins'])} min "
                                 f"({left} min left). Coins sold inside 15 min lost $19.30 over 714 pieces (27% won); held 30–60 min won 59%. Let it cook?")


async def _real_hold_fix(now):
    """🍳 OWNER'S CALL (2026-10-08, "do all" after the pay-map): once, the real card lets a coin cook — min hold 30 min (round rotation, mover swaps,
    trench fills and re-shapes wait; stops, rug shield, floor, the owner's hand still act at once) and a trench / ticket coin's initial comes out at +100%.
    Evidence: held 30+ min 61% won +$5.32, sold inside 15 min 28% won −$17.55. The 5-min clock is untouched. Old values: data/realcfg_before_hold30.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        if pr.get('holdFix1') or not pr.get('realCfg'):
            return False
        rc = pr['realCfg']; new = {'minHoldMins': 30.0, 'trenchHouseAt': 100}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_hold30.json', {k: rc.get(k) for k in new})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **new})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(new))
        pr['holdFix1'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _real_ride_fix(now):
    """❄ OWNER'S DESIGN (2026-10-08: "if one coin runs it should be frozen on the card and skimming"): the real card's freeze (`rideAt`) was found at 0 = OFF,
    so no coin ever locked — the lock bank (50%), the full-stack skim, the off-its-peak sell and the stepped trail all start at the lock and never ran
    (the ledger shows plain skims only). Once, it goes back to the 5-min lock the trail (8%) was already set for: freeze at +15%. Old value: data/realcfg_before_ride.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('rideFix1') or not rc:
            return False
        if rs._fuse._f(rc.get('rideAt')) > 0:
            pr['rideFix1'] = now; rs._json_save(rs.FUSE_HQ_PATH, d); return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_ride.json', {'rideAt': rc.get('rideAt'), 'rideTrail': rc.get('rideTrail')})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'rideAt': 15.0, 'rideTrail': rs._fuse._f(rc.get('rideTrail')) or 8.0})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'rideAt', 'rideTrail'})
        pr['rideFix1'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _ladder_keep_fix(now):
    """🪜 Once (2026-10-08): the owner tapped "4 coins" while the ladder was on, before taps beat the ladder — keep that tap."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('ladderKeepFix1') or not rc.get('ladder'):
            return False
        if int(rs._fuse._f(rc.get('coins'))) == 4:
            pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {'coins'})
        pr['ladderKeepFix1'] = True
        rs._json_save(rs.FUSE_HQ_PATH, d)
        return True


def degen_patch_1009(rc):
    """Pure: the 2026-10-09 config (owner: "fix my settings to be degen … cut these trench coins and move on") → (new realCfg, keys changed)."""
    rs = _rs()
    cyc = dict(rc.get('cycles') or {}); cyc['degen'] = 'press'   # 🗑 off the trench cycle: runners strike, then a mixed round
    return rs._prime.clean_cfg({**rc, **rs.DEGEN_1009, 'cycles': cyc}), sorted(set(rs.DEGEN_1009) | {'cycles'})


async def _degen_fix_1009(now):
    """🎰→🏦 OWNER'S CALL (2026-10-09, after the pay-map + chain audit): once, the real card stops handing back its runs and leaves the trench.
    Found: the "always keep $1 riding" floor was above every coin on a $1.39 card, so no peak sell / lock bank could fire — six coins rode
    to 1.1–1.3× and gave it all back in 40 min. Changes: keep-riding floor off · full-stack skim to $0.50 · 🏠 initial out at +50% on EVERY
    coin · ⏳ 30-min ask before a hand exit · ride over → 🏦 bank its profit · min hold 30m · bank 50% at the lock · trench off (auto buys,
    tickets ride-or-rug, cycle → press). The tickets on the card lose ride-or-rug, so their stop applies again (the owner asked to cut them).
    Every key joins realOwnerSet + ladderKeep (the ladder's trench stage would put trench back). Old values: data/realcfg_before_degen1009.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('degenFix1009') or not rc:
            return False
        new, keys = rs.degen_patch_1009(rc)
        rs._json_save(rs.DATA_DIR / 'realcfg_before_degen1009.json', {k: rc.get(k) for k in keys})
        pr['realCfg'] = new
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(keys))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(keys))
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c['ticketRide'] = False
                for l in c.get('legs') or []:
                    if l.get('rideOrRug'):
                        l.pop('rideOrRug', None)
                        if l.get('slMode') == 'hold':
                            l.pop('slMode', None)
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🏦 your degen setup: keep-riding floor off · initial out at +50% on every coin · ride over → bank its profit · min hold 30m · bank 50% at the lock · trench off (tickets get their stop back)'})
        pr['degenFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


def overnight_patch_1009(rc):
    """Pure: the 2026-10-09 overnight selection (owner: "make tweaks to configs so I can wake up positive — I allow") → (new realCfg, keys).
    Copies WHAT the two paper cards that are up buy (Diamond +14.9%, Gold +10.2%: 12h+ coins, $50K+ pools, real volume, no "+20% on the
    hour" chase, no scout) — the real card bought any age, no pool floor, only coins already up 20%, and a 20% scout hopped onto movers
    (movers list −67% typical over 1h). Clock, stop, hold and exits are the owner's and are not touched. Not a promise of profit."""
    rs = _rs()
    return rs._prime.clean_cfg({**rc, **rs.OVERNIGHT_1009}), sorted(rs.OVERNIGHT_1009)


async def _overnight_fix_1009(now):
    """🌙 Once: apply `overnight_patch_1009` to the real card. Old values: data/realcfg_before_overnight1009.json. Keys → realOwnerSet + ladderKeep."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('overnightFix1009') or not rc:
            return False
        new, keys = rs.overnight_patch_1009(rc)
        rs._json_save(rs.DATA_DIR / 'realcfg_before_overnight1009.json', {k: rc.get(k) for k in keys})
        pr['realCfg'] = new
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(keys))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(keys))
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🌙 overnight setup: buys like the paper cards that are up — coins 12h+ old, $50K+ pools, $50K+/h volume, buyers 65%+, no chasing +20% hours, no scout · 3 coins · ≤ 2 swaps an hour. Your clock, stop, hold and exits unchanged.'})
        pr['overnightFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


def hunt_patch_1009(rc):
    """Pure: the owner's "send it" (2026-10-09, "we're supposed to be trenching"): 2 coins on the 🚀 Runner hunt line (12h+, $50K/h, +40%
    on the hour, $25K pool), the replay's own exits (stop −30, freeze +50, trail 30), 🏠 initial out at +50, ride over → bank. Runners only
    (newOnly) — an empty seat waits in cash for the next hunt coin. Clock / hold / swap cap stay the owner's. → (new realCfg, keys)."""
    rs = _rs()
    return rs._prime.clean_cfg({**rc, **rs.HUNT_1009}), sorted(rs.HUNT_1009)


async def _hunt_fix_1009(now):
    """🚀 Once: apply `hunt_patch_1009` to the real card. Old values: data/realcfg_before_hunt1009.json. Keys → realOwnerSet + ladderKeep."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('huntFix1009') or not rc:
            return False
        new, keys = rs.hunt_patch_1009(rc)
        rs._json_save(rs.DATA_DIR / 'realcfg_before_hunt1009.json', {k: rc.get(k) for k in keys})
        pr['realCfg'] = new
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(keys))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(keys))
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🚀 send it: 2 coins on the runner hunt line (12h+ · $50K/h · +40% on the hour) · stop −30 · freeze +50, trail 30 · 🏠 initial out at +50 · ride over → bank'})
        pr['huntFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _hunt_fix_1009b(now):
    """🚀 Once (same "send it"): the owner's vital filter (score 50+, 10% organic) removed all 6 coins clearing the hunt line → one step
    looser (35+, 5%). Old values: data/realcfg_before_hunt1009b.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('huntFix1009b') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_hunt1009b.json', {k: rc.get(k) for k in rs.HUNT_1009_B})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **rs.HUNT_1009_B})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(rs.HUNT_1009_B))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(rs.HUNT_1009_B))
        pr['huntFix1009b'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


def trench_patch_1009(rc):
    """Pure: the owner's 5-min / 2-round TRENCH setup (2026-10-09, "tweak my 5min 2 rnd configs so trenching is ez"), built on the card's
    own record: scalp the stake, ride the house (trims +$21.89 / 74% won vs whole exits −$32.83) → lock at +20 and bank 50%, initial out at
    +30, stepped trail; let it cook 15 min (exits < 15 min won 27%); trench = 🔥 SEND IT coins only (+0.5% vs the list's −79%), 2 of them.
    Stops, flow exit and rug radar act at once. → (new realCfg, keys)."""
    rs = _rs()
    cyc = dict(rc.get('cycles') or {}); cyc['degen'] = 'trench'
    return rs._prime.clean_cfg({**rc, **rs.TRENCH_1009, 'cycles': cyc}), sorted(set(rs.TRENCH_1009) | {'cycles'})


async def _trench_fix_1009(now):
    """🗑 Once: apply `trench_patch_1009` to the real card. Old values: data/realcfg_before_trench1009.json. Keys → realOwnerSet + ladderKeep."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('trenchFix1009') or not rc:
            return False
        new, keys = rs.trench_patch_1009(rc)
        rs._json_save(rs.DATA_DIR / 'realcfg_before_trench1009.json', {k: rc.get(k) for k in keys})
        pr['realCfg'] = new
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(keys))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(keys))
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🗑 trench setup: 5-min rounds · patience 2 · 2 trench coins, 🔥 SEND IT only · lock +20 & bank 50% · initial out at +30 · stepped trail · cook 15 min'})
        pr['trenchFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _procall_fix_1009(now):
    """🎯 Once (owner, 2026-10-09: "get in early on the best possible new trenches"): the real card's trench seats follow proven callers."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('procallFix1009') or not rc:
            return False
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'proCallEntry': True})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'proCallEntry'})
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {'proCallEntry'})
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🎯 trench seats now follow PROVEN Pump callers first — a fresh call (≤ 15 min), still within 15% of the cap they called it at, safety-scanned'})
        pr['procallFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _topseat_fix_1009(now):
    """🔥 Once (owner, 2026-10-09: "make it a config and turn it on"): the real card's TOP 1/3 coin takes a seat by itself; flow exit stays on."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('topSeatFix1009') or not rc:
            return False
        new = {'topSeat': True, 'flowExit': rc.get('flowExit') if rc.get('flowExit') in ('normal', 'tight') else 'normal'}
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **new})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(new))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(new))
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🔥 Top 3 auto-seat on: the TOP 1/3 coin takes your weakest non-winning seat (one per 10 min) · 🌊 buys-vs-sells exit sells it when sellers take over'})
        pr['topSeatFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _trench_safe_fix_1009(now):
    """🛡 Once (owner, 2026-10-09: "no extra seat, just make it run profits in trench safely"): trench ticket stop −30 → −20."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('trenchSafeFix1009') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_trenchsafe1009.json', {'trenchSlPct': rc.get('trenchSlPct')})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'trenchSlPct': 20})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'trenchSlPct'})
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {'trenchSlPct'})
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🛡 safe trench: busted reads (BOND RUN · EARLY RUSH · RUG BAIT · DUMPING · SLOW CURVE · BREAKOUT · FALLING KNIFE) and rug meter 50+ are never bought · trench ticket stop −20%'})
        pr['trenchSafeFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _clean_fix_1009(now):
    """🧹 Once (owner, 2026-10-09: "do these and make sure configs clean and ez"): ⚖ no coin over 35% of the card · 🚀 open seats take a
    banger first · and the settings taken OUT of Edit Fuse are switched off so nothing hidden keeps running (the scout was at 10%,
    stack-skim at $0.50). Old values: data/realcfg_before_clean1009.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('cleanFix1009') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_clean1009.json', {k: rc.get(k) for k in rs.CLEAN_1009})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **rs.CLEAN_1009})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(rs.CLEAN_1009))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(rs.CLEAN_1009))
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🧹 clean setup: ⚖ no coin over 35% of the card · 🚀 open seats take a banger first (proven caller → top 3 → cooling off) · 🏠 house riders ride outside your 4 seats · scout / stack-skim off'})
        pr['cleanFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _flow_tight_fix_1009(now):
    """🌊 Once (owner, 2026-10-09: "if I make buy-vs-sell tight it scalps and swaps faster? let's do it"): flow exit → tight (sellers 1.5×
    buyers, $25, 4 trades, price −1.5% in 90s). Its own record (flow_proof) shows whether faster exits pay. Old: realcfg_before_flowtight.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('flowTightFix1009') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_flowtight.json', {'flowExit': rc.get('flowExit')})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'flowExit': 'tight'})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'flowExit'})
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {'flowExit'})
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🌊 buys-vs-sells exit → TIGHT: sellers 1.5× buyers + price −1.5% in 90s sells the coin; the seat takes a banger'})
        pr['flowTightFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _entry_fix_1009(now):
    """🎯 Once (owner, 2026-10-09: "better entries … not getting in at highs, entries before the break, not −4¢"): clean entries on every
    door, buys-vs-sells waits 10 min after a buy, and the hunt line no longer REQUIRES +40% on the hour (that rule bought the highs).
    Old values: data/realcfg_before_entry1009.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('entryFix1009') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_entry1009.json', {k: rc.get(k) for k in rs.ENTRY_1009})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **rs.ENTRY_1009})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(rs.ENTRY_1009))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(rs.ENTRY_1009))
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🎯 clean entries: buyers 60%+, not chasing (+60% 1h / +3% 5m), 3%+ under its high, $50K+ pool, 6h+, $200K+/h on every door · buys-vs-sells waits 10 min after a buy · hunt line no longer needs +40%'})
        pr['entryFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _vital_off_fix_1009(now):
    """🫀 Once (2026-10-09): the vital-grade filter (35+ / 5% organic) is a hand-set score with no record, and it took the last coins
    clearing the clean-entry gate to 0 — two seats sat open with $1.11. It is off as an ENGINE gate (grades still show on every row).
    Old values: data/realcfg_before_vitaloff.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('vitalOffFix1009') or not rc:
            return False
        new = {'vitalMin': 0, 'organicMin': 0}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_vitaloff.json', {k: rc.get(k) for k in new})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **new})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(new))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(new))
        pr['vitalOffFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _moon_fix_1009(now):
    """🌙 Once (owner, 2026-10-09: "coins at 18K → 20M … got paid at 39K and skimmed to 40M"): the real card's trench / ticket coins play the
    MOON LADDER — lock at 2× (the initial comes out there: trench 🏠 line 100), 25% at 3× / 5× / 10× / 20× / 50×, a 40% trail.
    Old values: data/realcfg_before_moon1009.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('moonFix1009') or not rc:
            return False
        new = {'moonLadder': True, 'trenchHouseAt': 100}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_moon1009.json', {k: rc.get(k) for k in new})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **new})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(new))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(new))
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c.setdefault('events', []).append({'at': now, 'kind': 'fix', 'why': '🌙 moon ladder: trench coins lock at 2× (your initial comes out there), 25% sells at 3×/5×/10×/20×/50×, the bag rides a 40% trail · 🌊 the tape now times entries and sells half the profit into a buying climax'})
        pr['moonFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _floor_fix_1009(now):
    """🧱 Once (owner, 2026-10-09: "added $1 — let's keep $3.62"): the run started at $3.61. A floor AT the start would sell on the first
    1¢ wiggle; −10% (≈ $3.25) is the closest real protection — the whole card that far under its run start → every coin to cash, re-dealt."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('floorFix1009') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_floor1009.json', {'floorPct': rc.get('floorPct')})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'floorPct': 10})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'floorPct'})
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {'floorPct'})
        pr['floorFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _flow_fix_1009(now):
    """🌊 Once (owner, 2026-10-09: "fix card floor … we need to flow"): the −10% floor sold the whole card the moment it went on (the card
    was already at −12%) and the vital filter (grade 50 · 5% organic) then left NO coin to re-deal into — $3.15 sat in cash. Floor −20%
    (a 4-coin card with −30% coin stops reads −10% on two stops = a full round trip of the card for nothing), grade 35, organic off
    (Jupiter reads most Pump coins 2–3% organic). Old values: data/realcfg_before_flow1009.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('flowFix1009') or not rc:
            return False
        ch = {'floorPct': 20, 'vitalMin': 35, 'organicMin': 0}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_flow1009.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['flowFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _proof_gate_tick(now):
    """🧪 Hourly: run the edge audit on our own records (edge_audit.audit) and, for a real card whose owner switched the PROOF GATE on
    (cfg `proofGate`), hold it while no rule passes on unseen coins — ✋ hold all with `holdBy: 'proof'`: no engine BUY of any kind;
    stops, the rug shield and profit takes keep running; the owner's own picks still work — and release it the hour a rule passes.
    A hold the owner set by hand is never touched. Owner inbox once per change."""
    rs = _rs()
    import edge_audit as _ea
    calls_ = list(rs._agents_mem.get().get('done') or [])   # a copy taken on the loop: the live object keeps changing while the audit runs in its thread
    br_ = rs._json_load(rs.BRAIN_PATH, {})
    a = await rs.asyncio.to_thread(lambda: _ea.audit(br_.get('done') or [], calls_, _ea.COST, now, rs._fuse._f(br_.get('cleanFrom'))))
    rs._json_save(rs.EDGE_AUDIT_PATH, {**a, 'gate': _ea.gate(a), 'words': _ea.words(a)})
    g = _ea.gate(a)
    if g == 'wait':
        return a
    told = None
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.get('prime') or {}
        if not (pr.get('realCfg') or {}).get('proofGate') or (pr.get('realCfg') or {}).get('agentControl'):   # 🎮 the owner handed the card to the agents: their call
            return a
        ch = False
        for c in (pr.get('cards') or {}).values():
            if not c.get('real'):
                continue
            if g == 'hold' and not c.get('holdAll'):
                c['holdAll'] = True; c['holdBy'] = 'proof'; ch = True; told = _ea.words(a)
                c['events'] = (list(c.get('events') or []) + [{'kind': 'hold', 'at': now, 'why': told}])[-60:]
            elif g == 'trade' and c.get('holdAll') and c.get('holdBy') == 'proof':
                c['holdAll'] = False; c.pop('holdBy', None); ch = True; told = _ea.words(a) + ' — the engine trades again'
                c['events'] = (list(c.get('events') or []) + [{'kind': 'hold', 'at': now, 'why': told}])[-60:]
        if ch:
            rs._json_save(rs.FUSE_HQ_PATH, d)
    if told:
        for w in rs._owner_wallets():
            rs.notify(w, 'admin', told, url='/terminal/fuse?tab=cards', once=f"proof-gate-{g}-{int(now // 86400)}", push=False)
    return a


async def _proof_gate_fix_1010(now):
    """🧪 Once (owner, 2026-10-10, after the edge audit found 0 of 433 rules positive: "fix"): PROOF GATE on for the real card. Old value:
    data/realcfg_before_proofgate1010.json. Off again: Edit Fuse › Safety, or ▶ Release on the card."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('proofGateFix1010') or not rc:
            return False
        ch = {'proofGate': True}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_proofgate1010.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['proofGateFix1010'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    try:
        await rs._proof_gate_tick(now)   # judge at once — never wait an hour to stop a bleed
    except Exception as e:
        print('proof gate:', e)
    return True


async def _proof_clean_1013(now):
    """🩹 Once: every 1-hour paper record restarts (2026-10-13: 45–80% of their settled rows were −100% "vanished" coins that were alive —
    the graders' price fallback timed out at 3s on a 5–7s batch). Those rows decided Devil's busted reads, paused lists, the edge score
    and the proof gate. Settled rows only; open coins keep running; never a money record. Old rows: data/proof_before_clean1013.json."""
    rs = _rs()
    flag = rs.DATA_DIR / 'proof_clean.json'
    if rs._json_load(flag, {}).get('fix1013'):
        return False
    old, n = {}, 0
    for path in (rs.TRENCH_META_PATH, rs.ENTRY_PROOF_PATH, rs.CALL_PROOF_PATH, rs.PROCALL_PROOF_PATH, rs.BOTTOM_PROOF_PATH, rs.LENS_PROOF_PATH, rs.EDGE_PROOF_PATH, rs.FLOW_PROOF_PATH):
        st = rs._json_load(path, {})
        new, k = rs._trench.proof_restart(st)
        if k:
            old[path.name] = st; n += k; rs._json_save(path, new)
    doc = rs._json_load(rs.TRENCH_CALLOUT_PATH, {})
    new, k = rs._trench.proof_restart(doc.get('state') or {})
    if k:
        old[rs.TRENCH_CALLOUT_PATH.name] = doc.get('state'); n += k; rs._json_save(rs.TRENCH_CALLOUT_PATH, {**doc, 'state': new})
    if old:
        rs._json_save(rs.DATA_DIR / 'proof_before_clean1013.json', old)
    rs._json_save(flag, {'fix1013': now, 'rows': n})
    return True


async def _agent_open_fix_1012(now):
    """⚡ Once (owner, 2026-10-12: "no blocks, no reputation scoring — volume and newness only; no seat should be empty"): `agentOpen` on.
    The keeper's own buy checks (sell-back, price near market, pool floor) still run. Old value: data/realcfg_before_open1012.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('agentOpenFix1012') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_open1012.json', {'agentOpen': rc.get('agentOpen', False)})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'agentOpen': True})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'agentOpen'})
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {'agentOpen'})
        pr['agentOpenFix1012'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _agent_real_fix_1012(now):
    """💵 Once (owner, 2026-10-12, after the edge audit read NO PROVEN EDGE: "continue with real money unless more issues"): the agents trade
    real money again (`agentPaper` False). Best available stays off, the held-card leaks stay closed, the real-money memory and the agent cost
    caps stay on. Paper again: HQ › Agents › ⚙ Control (agentPaper) — old value in data/realcfg_before_agentreal1012.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('agentRealFix1012') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_agentreal1012.json', {'agentPaper': rc.get('agentPaper', True)})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'agentPaper': False})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'agentPaper'})
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {'agentPaper'})
        pr['agentRealFix1012'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


def _trail_fix_1014(now):
    """🏄 Once (owner, 2026-10-14: "they TP 10% max most of the time — they need to be smarter degens"): Reaper's trail was promoted to
    arm +4% / give back 35% by the OLD replay that ended where the agents sold. The full-move trail lab (168 real trades watched 30 min past
    the sale) has arm +10% / give back 30% ahead on BOTH the typical trade (+7.7% vs +4.4%) and the average (−5.5% vs −6.3%). Set as an
    owner correction (lineage); the shadow loop may move it again on new evidence. Stops and every hard safety exit are untouched."""
    rs = _rs()
    st = rs._office_state()
    if st.get('trailFix1014'):
        return False
    st.update(rs._of.owner_tune(st, 'reaper', {'protectAt': 10.0, 'giveBackPct': 30.0},
                             'owner: winners were banked at +5–10%; full-move trail lab: arm +10 / give 30 beats arm +4 / give 35 (typical +7.7% vs +4.4%)', now))
    st['trailFix1014'] = now
    return True


async def _curve_fix_1011(now):
    """🎢 Once (owner, 2026-10-11: "seats not filled means they too strict" — 11 of 41 hard NOs were fresh Pump coins on their launch curve,
    which no agent seat could buy): agent seats may buy a curve coin (`agentCurve`), judged on the curve's own depth; every keeper check
    still runs. Old value: data/realcfg_before_curve1011.json. Off again: HQ › Agents › ⚙ Control › 🎢."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('curveFix1011') or not rc:
            return False
        ch = {'agentCurve': True}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_curve1011.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['curveFix1011'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _g4seat_fix_1016(now):
    """🔁 Once (owner, 2026-10-16: "turn the G4 seat on in paper mode for the real card"): `agentAiSeat` = paper — G4 and the Mac model take
    turns on a PAPER seat (no money). Old value: data/realcfg_before_g4seat1016.json. Change it: HQ › Agents › 🎛 Limits › 🧠 G4 SEAT."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('g4seatFix1016') or not rc:
            return False
        ch = {'agentAiSeat': 'paper'}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_g4seat1016.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['g4seatFix1016'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _youticket_fix_1016(now):
    """✋ Once (owner, 2026-10-16: "shouldn't be messing with my trades period — I choose"): the 🎟 small-ticket sizing of the owner's young
    picks is OFF on the real card (`youngTicket` False) — a pick gets its full seat. Old value: data/realcfg_before_youticket1016.json.
    Switch it back on: Edit Fuse › Safety › 🎟 Small ticket."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('youTicketFix1016') or not rc:
            return False
        ch = {'youngTicket': False}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_youticket1016.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['youTicketFix1016'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _germline_fix_1016(now):
    """🦠 Once (owner, 2026-10-16: "raise my germ line to 15%"): the real card's germ line 10% → 15% (`agentGermMax`; the replay's best of
    8 / 15 / 25). Old value: data/realcfg_before_germline1016.json. Change it again: HQ › Agents › 🎛 Limits › 🦠 GERM PLAY."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('germLineFix1016') or not rc:
            return False
        ch = {'agentGermMax': 15}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_germline1016.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['germLineFix1016'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    rs._uni.set_band(pr['realCfg'])
    return True


async def _mcfloor_fix_1016(now):
    """🎯 Once (owner, 2026-10-16: "lower my MC band floor to $10K so newer launches reach the agents"): the real card's band floor
    $20K → $10K (`agentMcMin`). Old value: data/realcfg_before_mcfloor1016.json. Change it again: HQ › Agents › 🎛 Limits › 🎯 UNIVERSE."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('mcFloorFix1016') or not rc:
            return False
        ch = {'agentMcMin': 10_000.0}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_mcfloor1016.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['mcFloorFix1016'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    rs._uni.set_band(pr['realCfg'])
    return True


async def _minage_fix_1014(now):
    """🐣 Once (2026-10-14): the agents' youngest-coin control (`agentMinAgeH`) was shown but enforced nowhere after the 2026-10-12 refactor —
    the card held 0.5 h on screen while every trade it made was any age. Now that it IS enforced, a 0.5 h line would block 209 of the 273
    real trades on record, and those are the BEST bucket for a minutes-long scalp (0–5 min old: 72% won, median +5%; 1–6 h: 32% won,
    −5.4% avg; rugs ~8–11% in every bucket). So the card is set to what it really ran on — any age — and the owner chooses from here.
    Old value: data/realcfg_before_minage1014.json. Change: HQ › Agents › 🎛 controls › 🎯 UNIVERSE › Youngest coin."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('minAgeFix1014') or not rc:
            return False
        ch = {'agentMinAgeH': 0}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_minage1014.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['minAgeFix1014'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _armed_fix_1013(now):
    """🎯 Once (owner, 2026-10-13: "seat filling is the problem … keep seats full"): entry mode ARMED on the real card — a seat empty past the
    seat target takes the best ARMED coin at half a seat, and the empty-seat target drops to 15s. Old values: data/realcfg_before_armed1013.json.
    Back: HQ › Agents › 🎛 controls › Entry = agents."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('armedFix1013') or not rc:
            return False
        ch = {'agentEntry': 'armed', 'agentSeatTarget': 15}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_armed1013.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['armedFix1013'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _agent_control_set(on, now):
    """🎮 Switch agent control of the real card on / off: ON = the card is held by the agents (their moves only); OFF = that hold is
    released (the proof gate, when on, judges the card again at its next tick)."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        pr['realCfg'] = rs._prime.clean_cfg({**(pr.get('realCfg') or {}), 'agentControl': bool(on)})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'agentControl'})
        for c in (pr.get('cards') or {}).values():
            if not c.get('real'):
                continue
            if on and (not c.get('holdAll') or c.get('holdBy') == 'proof'):
                c['holdAll'] = True; c['holdBy'] = 'agents'
                c['events'] = (list(c.get('events') or []) + [{'kind': 'hold', 'at': now, 'why': "🎮 the agents control every seat — the engine's own swaps are off"}])[-60:]
            elif not on and c.get('holdBy') == 'agents':
                c['holdAll'] = False; c.pop('holdBy', None); c.pop('agentWant', None)
                c['events'] = (list(c.get('events') or []) + [{'kind': 'hold', 'at': now, 'why': '🎮 agent control off — the card is back on its own settings'}])[-60:]
        rs._json_save(rs.FUSE_HQ_PATH, d)


async def _desk_buys_fix_1105(now):
    """⚖ Once (owner, 2026-11-05: "Yes, stop their buys"): the desk's agents validate proofs instead of trading. Their new real buys stop; their exits and the owner's own picks run as before. It can be switched back in HQ › Agents. Old value: data/realcfg_before_deskbuys1105.json."""
    rs = _rs()
    d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.get('prime') or {}
    if pr.get('deskBuysFix1105') or not pr.get('realCfg'):
        return False
    rs._json_save(rs.DATA_DIR / 'realcfg_before_deskbuys1105.json', {'deskBuysOff': (pr.get('realCfg') or {}).get('deskBuysOff', False), 'at': now})
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        pr['realCfg'] = rs._prime.clean_cfg({**(pr.get('realCfg') or {}), 'deskBuysOff': True}); pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'deskBuysOff'}); pr['deskBuysFix1105'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _agent_control_fix_1010(now):
    """🎮 Once (owner, 2026-10-10 ~12:30 after a $1 top-up: "the agents should have control over my seats and switching coins … allow them
    real moves on my real money card — GO"): agent control ON. Said once before the switch: the edge audit reads 0 of 453 rules positive
    and their ENTER calls −4% typical; the owner's call. Old value: data/realcfg_before_agentcontrol1010.json."""
    rs = _rs()
    d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.get('prime') or {}
    if pr.get('agentControlFix1010') or not pr.get('realCfg'):
        return False
    rs._json_save(rs.DATA_DIR / 'realcfg_before_agentcontrol1010.json', {'agentControl': (pr.get('realCfg') or {}).get('agentControl')})
    await rs._agent_control_set(True, now)
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); d.setdefault('prime', {})['agentControlFix1010'] = now; rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _agent_duty_fix_1010(now):
    """🕙 Once (owner, 2026-10-10: "profit and move on … putting something on the card every 10 min"): their take line on the real seat goes
    from +50% to +10% (bank it, move on). Old value: data/realcfg_before_agentduty1010.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('agentDutyFix1010') or not rc:
            return False
        ch = {'agentTakePct': 10}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_agentduty1010.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['agentDutyFix1010'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _keephalf_fix_1010(now):
    """🔐 Once (owner, 2026-10-10 01:40, after a $1 top-up: "they must keep coins and profit going on card while I'm asleep — very smart money"):
    KEEP HALF on for the real card (`arena_prime.half_back`). Old value: data/realcfg_before_keephalf1010.json. Off again in Edit Fuse › Exits."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('keepHalfFix1010') or not rc:
            return False
        ch = {'keepHalf': True}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_keephalf1010.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['keepHalfFix1010'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _floor_off_fix_1009(now):
    """🧱 Once (owner, 2026-10-09: "MAKE A OFF OPTION FOR CARD/TRENCHCOIN FLOOR — I lost a dollar getting trenches swapped"): the −20% card
    floor sold the whole card at 15:44, frozen coins included, and −25% ticket stops kept shaking trench coins out. Card floor OFF and
    trench-coin stop OFF (tickets ride or rug — the rug shield still sells a pulled pool). Old values: data/realcfg_before_flooroff1009.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('floorOffFix1009') or not rc:
            return False
        ch = {'floorPct': 0, 'trenchSlPct': 100}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_flooroff1009.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['floorOffFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _night_off_fix_1017(now):
    """🌙 Once (owner, 2026-10-17 ~02:00: "disable night guard and let them trench again"): night guard (drawdown / streak pauses) and the
    night shift (00:00–09:00: 15% seats, 30-min min age, chart must say ENTER NOW, no valve) OFF on the real card. Rug-level exits, stops and
    every keeper check are unchanged. Old values: data/realcfg_before_nightoff1017.json. Back on = the 🌙 switches in 🎛 Limits."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('nightOffFix1017') or not rc:
            return False
        ch = {'nightGuard': False, 'nightShift': False}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_nightoff1017.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['nightOffFix1017'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _rush_fix_1009(now):
    """⚡ Once (owner, 2026-10-09: "upgrade engine to rush me — I'm trenching and giving the keys, open the door"): the real card RUSHES —
    the trench drop takes the Rush board's coin every 10 min (was 30, SEND IT only — usually nothing), and may take the seat of any of the
    owner's picks that is not frozen and not making money (❄ frozen coins are never touched). Tickets stay small (15%), stop off, 🏠 at 2×.
    Old values: data/realcfg_before_rush1009.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('rushFix1009') or not rc:
            return False
        ch = {'trenchRush': True, 'trenchEvery': 10, 'trenchSendOnly': False, 'trenchAuto': True}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_rush1009.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['rushFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _volcycle_fix_1009(now):
    """🌊 Once (owner, 2026-10-09: "need to be cycling new volume coins"): the real card's volume cycle ON, every 10 min. Old value:
    data/realcfg_before_volcycle1009.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('volCycleFix1009') or not rc:
            return False
        ch = {'volCycle': True, 'volEvery': 10}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_volcycle1009.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['volCycleFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _degen_crazy_fix_1009(now):
    """🧨 Once (owner, 2026-10-09: "go degen crazy and get us back to $4 — we are in this, not just me"): faster cycling with the guards that
    were added the same afternoon kept — rush + volume cycle every 5 min, trench tickets 25% of the card (ride or rug, 🏠 at 2×), 2 trench
    coins. Full seats still need 6h+ / $50K pools; rush still skips thin pools, busted reads and coins that already ran.
    Old values: data/realcfg_before_crazy1009.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('crazyFix1009') or not rc:
            return False
        ch = {'trenchEvery': 5, 'volEvery': 5, 'trenchStakePct': 25, 'trenchCoins': 2, 'trenchRush': True, 'volCycle': True}
        rs._json_save(rs.DATA_DIR / 'realcfg_before_crazy1009.json', {k: rc.get(k) for k in ch})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, **ch})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | set(ch))
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | set(ch))
        pr['crazyFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _agent_test_fix_1009(now):
    """🤖 Once (owner, 2026-10-09: "once 5 min is complete they must go through a real-money Fuse card test — my Fuse card"): the agents'
    feed into the real card is switched ON; it does nothing until the 5-minute paper desk has 10×'d in one run (`agents.stage`)."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('agentTestFix1009') or not rc:
            return False
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'agentFeed': True})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'agentFeed'})
        pr['agentTestFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _agent_learn_fix_1009(now):
    """🎓 Once (owner, 2026-10-09: "they do it on the creator wallet / Fuse wallet's real-money card to learn before I fund them"): the agents
    get ONE learning seat now — a 10% ticket, held until profit, pulled at once if its pool drains. Old value: data/realcfg_before_agentlearn.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('agentLearnFix1009') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_agentlearn.json', {k: rc.get(k) for k in ('agentLearn', 'agentLearnPct')})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'agentLearn': True, 'agentLearnPct': 10})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'agentLearn', 'agentLearnPct'})
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {'agentLearn', 'agentLearnPct'})
        pr['agentLearnFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _agent_seat_fix_1009(now):
    """🤖 Once (owner, 2026-10-09: "agents don't just get one small seat, they run 1 whole seat and suggest for the other 3"): the learning
    seat becomes a WHOLE seat (`agentLearnPct` 100). Old value: data/realcfg_before_agentseat.json."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('agentSeatFix1009') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_agentseat.json', {k: rc.get(k) for k in ('agentLearn', 'agentLearnPct')})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'agentLearn': True, 'agentLearnPct': 100})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'agentLearn', 'agentLearnPct'})
        pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {'agentLearn', 'agentLearnPct'})
        pr['agentSeatFix1009'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _ticket_ride_fix(now):
    """🎰 OWNER'S TRENCH STYLE (2026-10-08: "look how I'm trenching these new narratives — if it gets rugged oh well, gotta be a good one, and pull"):
    once, the real card's tickets go RIDE OR RUG (`ticketRide`: no stop, the 🏠 pull takes the initial out) — the tickets already on the card too.
    Old value: data/realcfg_before_ticketride.json. Off again = Edit Fuse › Safety › 🎰 Tickets: ride or rug → off."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        rc = pr.get('realCfg') or {}
        if pr.get('rugFix1') or not rc:
            return False
        rs._json_save(rs.DATA_DIR / 'realcfg_before_ticketride.json', {'ticketRide': rc.get('ticketRide', False)})
        pr['realCfg'] = rs._prime.clean_cfg({**rc, 'ticketRide': True})
        pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {'ticketRide'})
        for c in (pr.get('cards') or {}).values():
            if c.get('real'):
                c['ticketRide'] = True
                for l in c.get('legs') or []:
                    if l.get('ticket') and not l.get('placeholder'):
                        l.pop('sl', None); l.update(slMode='hold', rideOrRug=True)
        pr['rugFix1'] = now
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return True


async def _prime_reset_paper(now):
    """🔁 Start every paper tier card over at PAPER_START_USD ($100), once. Their old runs go to the permanent record + `prime.archive`; the tick deals
    fresh cards at the new size right after. Real-money cards keep running exactly as they are."""
    rs = _rs()
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        if pr.get('reset') == rs.PRIME_RESET:
            return 0
        cards = pr.get('cards') or {}
        gone = {k: c for k, c in cards.items() if not c.get('real')}
        for k, c in gone.items():
            try:
                rs._store.Ledger(rs.CARD_RECORDS_PATH, table='runs').append({'at': now, 'card': k, 'label': c.get('label'), 'startUsd': c.get('startUsd'), 'real': False, 'closed': True, 'why': f'restart on ${rs.PAPER_START_USD:g}'})
            except Exception as e:
                print('card records (reset):', e)
        pr['archive'] = ((pr.get('archive') or []) + [{'at': now, 'why': f'paper restart on ${rs.PAPER_START_USD:g}', 'cards': {k: {x: c.get(x) for x in ('label', 'startUsd', 'putInUsd', 'walletUsd', 'rounds')} for k, c in gone.items()}}])[-20:]
        pr['cards'] = {k: c for k, c in cards.items() if c.get('real')}
        pr['cfg'] = rs._prime.clean_cfg({**(pr.get('cfg') or {}), 'sizeUsd': rs.PAPER_START_USD})
        if rs.PRIME_RESET == 'paper20c':   # ⚡ Next Level: off the owner's picking habit (−27%), onto the agents' judged list
            tp_ = dict((pr.get('cfg') or {}).get('tierPick') or {})
            tp_['next'] = {'pickStyle': 'agents'}
            pr['cfg'] = rs._prime.clean_cfg({**pr['cfg'], 'tierPick': tp_})
            pr['humanTiers'] = [t_ for t_ in (pr.get('humanTiers') if pr.get('humanTiers') is not None else rs.HUMAN_TIERS_DEFAULT) if t_ != 'next']
        pr['reset'] = rs.PRIME_RESET
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return len(gone)


def _proven_candidates(hours):
    """The engine's strategies that ENDED UP on the replay for the round length nearest `hours` (pg_sim byClock) as reset candidates (exits + selection numbers)."""
    rs = _rs()
    import paper_reset as _pr
    bc = rs._json_load(rs.PG_SIM_PATH, {}).get('byClock') or {}
    rows = [(float(k), v) for k, v in bc.items() if v.get('strategies')]
    if not rows:
        return []
    clock, v = min(rows, key=lambda kv: abs(kv[0] - hours * 60))
    return [c for c in (_pr.from_sim(x.get('cfg') or {}) for x in v['strategies'] if x.get('profitable')) if c]


def _paper_broke(d, cards, px, now):
    """♻ A PAPER tier card worth ≤ 40% of what was put in (−60%, owner 2026-10-08: "paper cards must sl at −60%, we can't promote dead cards") restarts on the full paper size with a NEW config; the config it died on is SCRAPPED (never dealt again).
    Needs ≥ 5 rounds, ≥ 1h on the card, one reset per tier per 6h; a locked tier and the real card are never touched. The next tick deals the fresh card."""
    rs = _rs()
    import paper_reset as _pr
    pr_ = d.setdefault('prime', {}); locks = pr_.get('locks') or {}; cfg = rs._prime.clean_cfg(pr_.get('cfg') or {})
    last = pr_.setdefault('brokeAt', {}); out = dict(cards)
    for tid, c in cards.items():
        if c.get('real') or tid in locks:
            continue
        v = rs._prime.value(c, px, {})
        if not _pr.is_broke(c, v, now, last.get(tid, 0)):
            continue
        old = _pr.current(cfg, tid)
        others = [rs._prime.tier_cfg(cfg, t).get('pickStyle') for t, x in cards.items() if t != tid and not x.get('real')]
        new = _pr.fresh_config(old, pr_.get('scrapped') or [], others, rs._proven_candidates(rs._fuse._f((cfg.get('clocks') or {}).get(tid)) or 1.0))
        pr_['scrapped'] = ((pr_.get('scrapped') or []) + [_pr.scrap_row(tid, c, old, v, now)])[-_pr.SCRAP_KEEP:]
        _pr.apply(pr_, tid, new); cfg = rs._prime.clean_cfg(pr_.get('cfg') or {})
        try:
            rs._store.Ledger(rs.CARD_RECORDS_PATH, table='runs').append({'at': now, 'card': tid, 'label': c.get('label'), 'startUsd': c.get('startUsd'), 'real': False, 'closed': True, 'why': 'went broke — restarted on a new config'})
        except Exception as e:
            print('card records (broke):', e)
        pr_['archive'] = ((pr_.get('archive') or []) + [{'at': now, 'why': 'broke → new config', 'cards': {tid: {x: c.get(x) for x in ('label', 'startUsd', 'putInUsd', 'walletUsd', 'rounds')}}}])[-40:]
        ren = pr_.setdefault('renewed', {})
        ren[tid] = {'at': now, 'text': _pr.describe(new['cfg']), 'source': new['source'], 'n': int((ren.get(tid) or {}).get('n') or 0) + 1}
        last[tid] = now; out.pop(tid, None)
        try:
            rs._fuse_chat('fuse-lab', f"♻ {c.get('label') or tid} went broke (${v:.2f} of ${rs._fuse._f(c.get('putInUsd')) or rs._fuse._f(c.get('startUsd')):.0f}) — it restarts on a NEW config ({new['source']}): {_pr.describe(new['cfg'])}. The old one is scrapped.", f"broke-{tid}-{int(now // 3600)}")
        except Exception:
            pass
    return out


def _hq_ver():
    rs = _rs()
    try:
        st = rs.FUSE_HQ_PATH.stat(); return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def _record_runs(before, cards):
    """📜 Permanent record: each run that just ended on a tier card goes into the append-only ledger (never trimmed, never edited)."""
    rs = _rs()
    try:
        lg = rs._store.Ledger(rs.CARD_RECORDS_PATH, table='runs')
        for tid, c in cards.items():
            for r in c.get('runs') or []:   # runs keep only the last 10 on the card — the timestamp tells what's new
                if rs._fuse._f(r.get('at')) > before.get(tid, 0.0):
                    lg.append({**r, 'card': tid, 'label': c.get('label'), 'real': bool(c.get('real'))})
    except Exception as e:
        print('card records:', e)


async def _prime_reads(rows):
    """The three reads a Prime view needs, AT ONCE: DexScreener pairs (budgeted), Jupiter prices, SOL/USD. Stage times are kept."""
    rs = _rs()
    async def timed(name, coro, default, budget=None):
        t0 = rs.time.perf_counter()
        try:
            return await (rs.asyncio.wait_for(coro, timeout=budget) if budget else coro)
        except Exception:
            return default
        finally:
            rs._prime_stages[name] = round((rs.time.perf_counter() - t0) * 1000)
    px, jup, sol = await rs.asyncio.gather(timed('dexscreener', rs._hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in rows]), {}, rs.PRIME_DS_BUDGET),
                                        timed('jupiter', rs._jup_prices([l.get('mint') for l in rows]), {}), timed('sol', rs._sol_usd_live(), 0.0))
    return dict(px or {}), jup or {}, sol or 0.0


def _prime_resp_clear():
    rs = _rs()
    rs._prime_resp.update(at=0.0, data=None, task=None, cleared=rs.time.time())


async def _prime_resp_build():
    rs = _rs()
    t0 = rs.time.time()
    data = await rs._fuse_prime_build()
    if t0 >= rs._prime_resp['cleared']:   # a build that began before an owner write never refills the cache with the old state
        rs._prime_resp.update(at=rs.time.time(), data=data, snap=False)
        rs._prime_stages['buildMs'] = round((rs.time.time() - t0) * 1000)
        if rs.time.time() - rs._prime_resp.get('savedAt', 0) > rs.PRIME_SNAP_EVERY and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
            rs._prime_resp['savedAt'] = rs.time.time()
            try:
                await rs.asyncio.to_thread(rs._json_save, rs.PRIME_SNAPSHOT_PATH, {'at': rs.time.time(), 'data': data})
            except Exception:
                pass
    return data


def _prime_snapshot(now=None):
    """The last good /fuses/prime from disk (≤ PRIME_SNAP_MAX old) → (at, data) or None. Read once, on the first request after a start."""
    rs = _rs()
    now = rs.time.time() if now is None else now
    try:
        j = rs._json_load(rs.PRIME_SNAPSHOT_PATH, {}) or {}
    except Exception:
        return None
    return (j['at'], j['data']) if j.get('data') is not None and now - rs._fuse._f(j.get('at')) < rs.PRIME_SNAP_MAX else None


async def _prime_warm():
    """Warm /fuses/prime once, 20s after startup — after the keeper and the agents loop have started; it never blocks them."""
    rs = _rs()
    await rs.asyncio.sleep(20)
    try:
        if rs._prime_resp['data'] is None or rs._prime_resp.get('snap'):
            await rs._prime_resp_build()
    except Exception as e:
        print('prime warm:', type(e).__name__)


async def _fuse_prime_build():
    """⭐ Arena Prime cards (paper, fully auto) with every automation event + the config they run."""
    rs = _rs()
    _rc = rs._prime_real_cfg() if any((c or {}).get('real') for c in rs._prime_cards().values()) else {}
    _seed = sum(ord(ch) for ch in ''.join(sorted(rs._owner_wallets()))[:44]) if _rc else 0   # ⚡ each owner's card gets its own variant of the meta
    _ht, _hp, _hn = rs._human_style()
    _rcard = rs._real_card() if _rc else None
    _lst = (_rcard or {}).get('ladderStage') or rs._prime.ladder_stage(rs._ladder_value(_rcard)) if _rcard else None
    _lkeep = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('ladderKeep') or []
    _lad = {**rs._prime.ladder_view(_lst), 'on': bool(_rc.get('ladder')), 'value': round(rs._ladder_value(_rcard), 2), 'keys': rs._prime.ladder_keys(_lst), 'keep': _lkeep} if _rcard else None
    _fnow = rs.time.time()
    _flv = {p: {**{k: w.get(k) for k in ('buyUsd', 'sellUsd', 'n', 'pxChg', 'sellShare')}, 'age': round(_fnow - at)} for p, (at, w) in list(rs._flow_now.items()) if w and _fnow - at < 90}
    _fpr = rs._trench.meta_proof(rs._json_load(rs.FLOW_PROOF_PATH, {}), keys=('flow', 'rug'))
    return {'flow': _flv, 'flowProof': _fpr, 'ladder': _lad, 'meta': rs._prime.meta_for(rs._fuse._f(_rc.get('rotateHours')) or 1.0, _seed) if _rc else None, 'cards': await rs._prime_view(), 'humanStyle': {'tiers': _ht, 'picks': _hn, 'need': rs._ps.MIN_PICKS, 'ready': bool(_hp), 'words': rs._ps.words(_hp),
                           'moves': rs._om.summary(next((v for k, v in rs._json_load(rs.OWNER_MOVES_PATH, {}).items() if isinstance(v, dict)), {}))}, 'renewed': ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('renewed') or {}), 'scrapped': [{k: x.get(k) for k in ('tpl', 'at', 'label', 'text', 'valueUsd', 'putInUsd', 'rounds')} for x in ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('scrapped') or [])[-12:]], 'cfg': rs._prime_cfg(), 'templates': rs._prime.TEMPLATES, 'weather': rs._real_weather(), 'suggest': rs._json_load(rs.PG_SIM_PATH, {}).get('byClock') or {}, 'realGuard': rs._prime.real_guard({**rs._prime.clean_cfg((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}), 'instantSwapPct': rs._fuse._f(((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}).get('instantSwapPct'))}, (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realOwnerSet') or ())[1], 'paperMatch': rs._fw.paper_match(rs._fw_peek().get('quoteAudit')), 'locks': {k: v.get('lockedAt') for k, v in ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('locks') or {}).items()}, 'lockCfg': ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('locks') or {}), 'roundWinner': (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('roundWinner'), 'realOwnerSet': (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realOwnerSet') or []}

