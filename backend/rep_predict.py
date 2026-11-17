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


async def _prime_tick_inner(now):
    rs = _rs()
    await rs._prime_unique_fix(now)
    await rs._prime_reset_paper(now)
    await rs._real_hold_fix(now)
    await rs._real_ride_fix(now)
    await rs._ticket_ride_fix(now)
    await rs._degen_fix_1009(now)
    await rs._overnight_fix_1009(now)
    await rs._hunt_fix_1009(now)
    await rs._hunt_fix_1009b(now)
    await rs._trench_fix_1009(now)
    await rs._procall_fix_1009(now)
    await rs._topseat_fix_1009(now)
    await rs._trench_safe_fix_1009(now)
    await rs._clean_fix_1009(now)
    await rs._flow_tight_fix_1009(now)
    await rs._entry_fix_1009(now)
    await rs._vital_off_fix_1009(now)
    await rs._moon_fix_1009(now)
    await rs._floor_fix_1009(now)
    await rs._flow_fix_1009(now)
    await rs._floor_off_fix_1009(now)
    await rs._night_off_fix_1017(now)
    await rs._keephalf_fix_1010(now)
    await rs._proof_gate_fix_1010(now)
    await rs._curve_fix_1011(now)
    rs._trail_fix_1014(now)
    await rs._armed_fix_1013(now)
    await rs._desk_buys_fix_1105(now)
    await rs._proof_clean_1013(now)
    await rs._minage_fix_1014(now)
    await rs._mcfloor_fix_1016(now)
    await rs._germline_fix_1016(now)
    await rs._g4seat_fix_1016(now)
    await rs._youticket_fix_1016(now)
    await rs._agent_real_fix_1012(now)
    await rs._agent_open_fix_1012(now)
    await rs._agent_control_fix_1010(now)
    await rs._agent_duty_fix_1010(now)
    await rs._rush_fix_1009(now)
    await rs._volcycle_fix_1009(now)
    await rs._degen_crazy_fix_1009(now)
    await rs._agent_test_fix_1009(now)
    await rs._agent_learn_fix_1009(now)
    await rs._agent_seat_fix_1009(now)
    await rs._ladder_keep_fix(now)
    cfg = rs._prime_cfg()
    if not cfg['on']:
        return 0
    pools, runners, anchors = await rs._prime_candidates()
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    cards = dict((d.get('prime') or {}).get('cards') or {})
    snap_, ver_ = rs._prime.card_snap(cards), rs._hq_ver()   # what the tick STARTED from (an owner write during the tick must win)
    # one pair fetch → live price AND momentum for EVERY coin on the cards (majors + pools too, not only runner-board coins)
    books = (rs._fw_peek().get('books') or {})
    market_rows = rs._fw_market_rows(cards, books)
    pairs_ = await rs._fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in market_rows]) if market_rows else {}
    px = {k: rs._fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}
    jup = await rs._jup_prices([l.get('mint') for l in market_rows])
    for l in market_rows:   # 🎯 confirmed book holdings waiting on a sell need live prices too
        if jup.get(l.get('mint')):
            px[l['pairAddress']] = jup[l['mint']]
    def _mom(p):
        tx = (p.get('txns') or {}).get('h1') or {}; b, s_ = rs._fuse._f(tx.get('buys')), rs._fuse._f(tx.get('sells'))
        return {'chg1h': rs._fuse._f((p.get('priceChange') or {}).get('h1')), 'buyShare': round(b / (b + s_) * 100, 1) if b + s_ else None,
                'vol5m': rs._fuse._f((p.get('volume') or {}).get('m5')), 'vol1h': rs._fuse._f((p.get('volume') or {}).get('h1'))}
    pair_mom = {k: _mom(v) for k, v in pairs_.items()}
    # live momentum per pair (runner board: 1h move, buy share, 5m/1h volume) → exit_plan decides ride / gain / bank / cut early
    live = rs._runner_live_cache.get('data') or {}
    mom = {**pair_mom, **{r['pairAddress']: {k: r.get(k) for k in ('chg1h', 'buyShare', 'vol5m', 'vol1h')} for r in (live.get('passing') or []) + (live.get('dropped') or []) if r.get('pairAddress')}}
    locks = (d.get('prime') or {}).get('locks') or {}
    before_runs = {tid: max((rs._fuse._f(r.get('at')) for r in (c or {}).get('runs') or []), default=0.0) for tid, c in cards.items()}   # newest run already recorded
    taken = set()   # 🎲 coins already on a tier dealt earlier this tick — later tiers pick OTHER coins when they can (no 5 identical cards)
    order_t = sorted(rs._prime.TEMPLATES, key=lambda t: 0 if (cards.get(t) or {}).get('real') else 1)   # real cards pick first
    hs_tiers, hs_prof, _hs_n = rs._human_style()
    for tid in order_t:
        cur = cards.get(tid)
        liqs = {k: rs._fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_.items()}
        rs._prime.LIQ_SRC.update({k: v.get('source') or 'dex' for k, v in pairs_.items()})   # 🧪 the rug shield never compares Jupiter's one-sided depth with a DexScreener entry
        cfg_t = {**rs._prime.clean_cfg(locks[tid]), 'paperFeeUsd': cfg['paperFeeUsd']} if tid in locks else rs._prime.tier_cfg(cfg, tid)   # 🔒 a locked tier runs its own frozen config · every other tier its own ⏱ clock
        _raw_paper = (d.get('prime') or {}).get('cfg') or {}
        cfg_t = {**cfg_t, **{k: v for k, v in rs._prime.PAPER_TRY.items() if k not in _raw_paper}}   # 🧪 fed lock + second ticket are tried on paper first
        real_t = bool((cur or {}).get('real'))
        if real_t:
            cfg_t = rs._prime_real_cfg(d.get('prime') or {})   # 💵 the real card runs ITS OWN config — paper edits / locks / engine tunes never touch it
            if cur is not None and rs._prime_real_cfg(d.get('prime') or {}).get('ladder'):
                cur = rs._ladder_step(cur, {'ladder': True}, now)
                cfg_t = rs._prime_real_cfg({**(d.get('prime') or {}), 'cards': {**((d.get('prime') or {}).get('cards') or {}), tid: cur}})
        if real_t and cur is not None and cfg_t.get('calloutSell', True):   # 📣 CALLOUT SPIKE SELL: profit sold into a rush of Pump callers (degen.py)
            try:
                rushing_ = {h['mint']: h['callers'] for h in rs._pc.rush(rs._pump_calls.get('calls') or [], now * 1000, 1e15, n=3, window_min=10)}
                hits_ = rs._dg.spike_sells(cur, px, rushing_, now) if rushing_ else []
                if hits_:
                    cur = {**cur, 'legs': [dict(x) for x in cur['legs']], 'events': list(cur.get('events') or []), 'spikeAt': dict(cur.get('spikeAt') or {})}
                    for pa_, why_ in hits_:
                        l_ = next((x for x in cur['legs'] if x.get('pairAddress') == pa_), None)
                        if l_ and rs._prime._skim(cur, l_, rs._fuse._f(px.get(pa_)), liqs, now, to=cfg_t.get('skimTo') or 'card', frac=rs._dg.SPIKE_FRAC, why=why_) > 0:
                            cur['spikeAt'][l_['mint']] = now
            except Exception as e:
                print('callout spike:', e)
        if cur is not None:   # 🔁 the card carries its own "no same coin unless it dipped" rule (arena_prime.cooling / note_dropped read it)
            cur = {**cur, 'rebuyDip': int(cfg_t.get('rebuyDipPct') or 0), 'ticketOff': bool(real_t and not cfg_t.get('youngTicket', False)), 'ticketRide': bool(real_t and cfg_t.get('ticketRide'))}
        # 🎯 PAPER = REAL: every tier (paper too) only rotates into coins real money could buy (pool ≥ minLiqUsd), so paper results are an
        # honest preview. ✅ Runners also need confirmation: rising over the last hour with buyers in control (≥55% buys) — no buying the top.
        def _lq(x):
            v = x.get('liquidity'); return rs._fuse._f(v.get('usd') if isinstance(v, dict) else v) or rs._fuse._f(x.get('liq')) or liqs.get(x.get('pairAddress'), 0.0)
        fw_cfg = rs._fw_peek().get('cfg') or {}
        floor_of = (lambda x: rs._fw.liq_floor(fw_cfg, x.get('arena'))) if real_t else (lambda x: rs.PAPER_MIN_LIQ)   # paper ⇄ real floors are separate
        def _confirmed(x):
            if x.get('newMajor'):   # a new major: green over 24h with buyers at least even
                return rs._fuse._f(x.get('change24h')) > 0 and rs._fuse._f(x.get('buyShare')) >= 50
            m = mom.get(x.get('pairAddress')) or {}
            bs = rs._fuse._f(m.get('buyShare')); bs = bs * 100 if 0 < bs <= 1 else bs
            return rs._fuse._f(m.get('chg1h')) > 0 and bs >= 55
        # 💵 real money: a coin must clear its floor with REAL_LIQ_MARGIN room (cached depth drifts before the keeper's live re-check) and
        # there is NO fallback to thin pools — that fallback dealt coins the keeper then refused ("pool too thin") while the slot sat in cash
        mg = rs.REAL_LIQ_MARGIN if real_t else 1.0
        p_t = [x for x in pools if _lq(x) >= floor_of(x) * mg] or ([] if real_t else pools)
        # 🔎 PIPELINE (real cards): how many launch coins survive each step — shown on the card, so "why no new coin" is a number
        fun_ = []
        def _step(label, rows):
            if real_t:
                fun_.append([label, len([x for x in rows if not x.get('trenchOnly')])])
        _step('launch coins that pass every safety gate', runners)
        r_t = [x for x in runners if _lq(x) >= floor_of(x) * mg]
        _step(f'pool at least ${floor_of({}) * mg / 1000:,.0f}K (Fuse wallet min pool)', r_t)
        r_t = [x for x in r_t if _confirmed(x)]
        _step('up on the hour with buyers at 55%+', r_t)
        if real_t:   # 🌦 real money buys runners by the weather the engine's own sims measured (rain = strong + deep only · storm = none)
            r_t = rs._prime.weather_runners(r_t, rs._real_weather()['level'], rs._fw.clean_cfg(fw_cfg)['minLiqUsd'], _lq, cfg_t)
            _step(f"runner weather ({rs._real_weather()['level']}) + min age {rs._fuse._f(cfg_t.get('runnerMinAgeH')):g}h", r_t)
        else:   # 📄 paper = what real money could buy: no runner under 12h old (unknown age = out) — the paper Arena cards bled on launch pumps
            r_t = rs._prime.weather_runners(r_t, 'clear', 0, _lq, cfg_t)
        # 🗑 trench coins (strict gate, cached by the warm loop) — only a 🗑 trench slot ever takes one; own pool floor; real money
        # never buys one in a runner storm. The real-money runner age rule doesn't apply to them: the trench gate replaces it.
        tr_floor = rs._fw.clean_cfg(fw_cfg)['trenchMinLiqUsd']   # paper uses the same floor (paper = what real money could buy)
        # 🗑 `trenchAuto` off (the owner's switch): the engine is handed NO trench coin — they stay on the list for the owner's hand
        if cfg_t.get('trenchAuto', True) and not (real_t and (rs._real_weather()['level'] == 'storm')):
            # 🗑 THE TRENCH DROP reads the whole trench LIST, not the trench settings (owner: "no settings or configs — one of the
            # best possible coins from the trench list"): coins passing the owner's filter, then the engine scan's own passes, then
            # coins that clear every SAFETY check and miss only a crowd / age / size line. Safety is never skipped. Smart entry
            # (`trench_entry`: not falling, not mid-spike, buyers ≥ 55%) decides WHEN; best trench score first.
            tr_all, tr_seen = [], {y.get('mint') for y in r_t}
            # 🔥 SEND IT first — only once the call has PROVEN itself on its own record and the owner's switch is on (safe coins only)
            sendit_ = [{**x, 'trenchScore': 100 + rs._fuse._f((x.get('tv') or {}).get('heat')), 'sendIt': True} for x in (rs._call_cache.get('send') or [])] \
                if (cfg_t.get('sendItAuto', True) and rs._sendit_ready()) else []
            # 🔥 SEND IT ONLY (owner's switch): the trench list itself reads −79% an hour on its own record, the SEND IT call +0.5% (52% won)
            # 🧠 TRENCH BRAIN first — only once its walk-forward proof holds and the owner's switch is on (safe coins, learned play > 0)
            if cfg_t.get('trenchBrain', True) and rs._brain_ready():
                sendit_ = [x for x in rs._brain_rows()[:6] if x['brain']['est'] > 0 and x.get('safe') is True] + sendit_
            pro_ = rs._pc.pro_entries(rs._pump_calls.get('calls') or [], rs._pump_calls.get('callers') or {}, [rs._with_tv(x) for x in rs._open_board()], now * 1000) if cfg_t.get('proCallEntry') else []
            if (cfg_t.get('agentFeed') or cfg_t.get('agentLearn')) and not cfg_t.get('deskBuysOff'):   # 🤖 the agents' GO calls first — proven, or ONE small 🎓 learning seat
                sendit_ = rs._agents_go_rows((cur or {}).get('legs'), cfg_t.get('agentSeats'), cfg_t.get('agentLearn'), cfg_t.get('agentLearnPct'), cfg_t.get('agentTrust')) + sendit_
            if cfg_t.get('trenchRush'):   # ⚡ RUSH: the engine buys what the Rush board shows — trench + open-list coins that PASSED the scan, ranked by rush_score
                sendit_ = rs._rush_rows() + sendit_
            pool_t = rs._prime.trench_pool(sendit_, rs._trench_cache.get('rows'), rs._trench_cache.get('fallback'),
                                        [y for y in rs._trench_cache.get('checked') or [] if not y.get('ok') and rs._trench.soft_only(y.get('fails'))], cfg_t, pro=pro_)
            for x in pool_t:
                if x.get('mint') not in tr_seen and _lq(x) >= tr_floor * mg and rs._prime.trench_entry(x, mom) and rs._prime.trench_read_ok(rs._with_tv(x)) and (not real_t or rs._prime.trench_age_ok(x, cfg_t)):   # 🚨 real money: never a coin under the card's trench min age
                    tr_seen.add(x.get('mint')); tr_all.append({**x, 'trenchOnly': True})
            r_t = r_t + sorted(tr_all, key=lambda x: -rs._fuse._f(x.get('trenchScore') or x.get('score')))
        # 🪑 coins real money couldn't buy safely (2× in 10 min) are benched 1h for EVERY tier — paper never trades what real can't
        bench = set().union(*[rs._fw.benched(b, now) for b in (rs._fw_peek().get('books') or {}).values()] or [set()])
        if bench:
            p_t, r_t = [x for x in p_t if x.get('mint') not in bench], [x for x in r_t if x.get('mint') not in bench]
        if real_t:   # 🚪 real money never buys a coin that is falling right now (coins already on the card are not judged here)
            on_ = {l.get('mint') for l in (cur or {}).get('legs') or []}
            p_t = [x for x in p_t if x.get('mint') in on_ or rs._prime.entry_ok(x, mom)]
            r_t = [x for x in r_t if x.get('mint') in on_ or rs._prime.entry_ok(x, mom)]
        book_s = (rs._fw_peek().get('books') or {}).get(tid) or {} if cur and cur.get('real') else {}
        # 💵 the smallest order this card can send (sized to its seats) — the engine never opens a seat or cuts a coin by less
        mo_t = 0.0
        if cur and cur.get('real'):
            eq_t = rs._prime.value(cur, px, liqs)
            want_n = int(rs._fuse._f(cfg_t.get('coins'))) or len(cur.get('legs') or [])
            fit_n = rs._fw.fit_seats(eq_t, want_n)   # 🪑 a card too small for the owner's coin count holds the seats it can really fill
            if 0 < fit_n < want_n:
                cfg_t = {**cfg_t, 'coins': fit_n}
                if cur.get('seatFit') != fit_n:
                    cur = {**cur, 'seatFit': fit_n, 'events': list(cur.get('events') or []) + [{'at': now, 'kind': 'seat-wait', 'usd': round(eq_t, 4),
                           'why': f"🪑 the card is worth ${eq_t:.2f}: it holds {fit_n} of your {want_n} coins for now — a seat needs ${rs._fw.MIN_ORDER_FLOOR * rs._fw.SEAT_ROOM:.3f} or its buy cannot be sent. Seat {fit_n + 1} opens at ${(fit_n + 1) * rs._fw.MIN_ORDER_FLOOR * rs._fw.SEAT_ROOM:.2f}."}]}
            elif cur.get('seatFit'):
                cur = {k: v for k, v in cur.items() if k != 'seatFit'}
            mo_t = rs._fw.min_order(fw_cfg, eq_t, min(want_n, fit_n) or want_n)
        if mo_t:
            cfg_t = {**cfg_t, 'minOrderUsd': mo_t}
        stuck = set(rs._fw.stuck_buys(cur, now, bench, missed=book_s.get('misses'), pending_mint=(book_s.get('pending') or {}).get('toMint') or (book_s.get('pending') or {}).get('mint'),
                                     busy=bool(book_s.get('pending')) or rs._fw.slip_busy(book_s, now) or now - max([rs._fuse._f(t) for t in (book_s.get('soldAt') or {}).values()] or [0.0]) < 45,
                                     buy_pass_at=rs._FW_BUY_PASS.get(tid, 0.0))) if cur and cur.get('real') else set()
        if stuck:   # 🧾 a buy the LEDGER shows filled in the last 3 min is not stuck — the card's book just hasn't synced yet ($Americaexe filled 13:48:59, sent back to cash 13:49:01)
            landed_ = {r_.get('mint') for r_ in rs._fw_full_ledger()[-200:] if r_.get('card') == tid and r_.get('side') == 'buy' and r_.get('status') == 'filled' and now - rs._fuse._f(r_.get('at')) < 180}
            stuck = {pa_ for pa_ in stuck if next((l_.get('mint') for l_ in cur.get('legs') or [] if l_.get('pairAddress') == pa_), None) not in landed_}
        # (the stuck-buy swap runs BELOW, after every filter — see "⏳ STUCK BUYS")
        # ⏳ EVERY door obeys the card's min age on real money (pools, runners, seat refills, replacements, mover swaps): a row whose
        # age is known and under `runnerMinAgeH` is out whatever list it came from. $Grok came in 20 minutes old through a list
        # that was never age-checked and was pulled an hour later (−99.7%).
        if real_t:
            def _too_young(x, lim=rs._fuse._f(cfg_t.get('runnerMinAgeH'))):
                a_ = x.get('ageH')
                if a_ is None and rs._fuse._f(x.get('createdAt')) > 0:
                    a_ = (rs.time.time() * 1000 - rs._fuse._f(x.get('createdAt'))) / 3.6e6
                return lim > 0 and a_ is not None and rs._fuse._f(a_) < lim and not x.get('trenchOnly')
            p_t = [x for x in p_t if not _too_young(x)]; r_t = [x for x in r_t if not _too_young(x)]
            # 🩺 EVIDENCE FLOOR (owner, 2026-10-08: "why put me in this coin" — $Attention+ came in as a ride-end replacement with buyers at 50% and no
            # 1h volume reading): a coin the engine buys by itself needs buyers ≥ FALLBACK_MIN_BUY when that number is known, and 1h volume ≥ FALLBACK_MIN_VOL
            # when THAT is known. Majors, stocks, comebacks and trench rows keep their own rules; the owner's hand picks are never judged.
            p_t = [x for x in p_t if not rs._prime.thin_flow(x)]; r_t = [x for x in r_t if not rs._prime.thin_flow(x)]
        # 💵 dollar-named tickers are never the engine's choice (pools, runners, new majors) — see fuse_wallet.dollar_named
        p_t = [x for x in p_t if not rs._fw.dollar_named(x.get('symbol'))]; r_t = [x for x in r_t if not rs._fw.dollar_named(x.get('symbol'))]
        # ⏱ each clock gets ITS coins: fast rounds rank by what is moving now, slow rounds keep depth / score order
        p_t, r_t = rs._prime.clock_rank(p_t, cfg_t['rotateHours'], mom), rs._prime.clock_rank(r_t, cfg_t['rotateHours'], mom)
        # 🧠 EDGE: runners are ranked by what the board's own record says about coins like them (pick_edge.py) — the hand-written score and
        # the "what is hot now" order both pointed at the coins that lost most. Real money buys only runners the record does not
        # expect to lose (cfg `edgeGate`, on by default); no table yet / table failing its own test = the order above stands.
        human_t = bool(not real_t and hs_prof and tid in hs_tiers)
        agents_t = bool(not real_t and cfg_t.get('pickStyle') == 'agents')   # 🤖 this PAPER card inherits the agents' judged list (below)
        tb_ = rs._edge_load().get('table')
        pth_ = rs._json_load(rs.RUNNERS_PATH, {}).get('paths') or {}   # 📈 each candidate's own chart read (chart_read.py) joins its snapshot — table or not
        r_t = [{**x, **rs._pedge._chart.keys(pth_.get(x.get('mint')) or [], now)} for x in r_t]
        if real_t:   # 📈 a coin new to the board has no record of ours yet — read its chart from the market's own 15-min candles
            r_t = await rs._chart_fill(r_t, now)
        if tb_:
            r_t = rs._pedge.rank(r_t, tb_)
            if cfg_t.get('edgeGate', True) and not human_t and not agents_t:   # real AND paper (paper = real); a 👤 card is ordered by the owner's style instead
                r_t = rs._pedge.gate(r_t, tb_, float(cfg_t.get('edgeFloor') or 0))
        if agents_t:   # 🤖 its runner candidates ARE the agents' own READY / contending coins (no second scan; old list kept only when the desk is cold)
            inh_ = rs._agent_inherit_rows()
            r_t = inh_ or r_t
        if human_t:   # 👤 this PAPER card buys what the owner would pick: closest to their own picks first (pick_style.py)
            r_t = rs._ps.rank(r_t, hs_prof)
            # … and EXITS the way the owner does: the real card's own stop / lock / trail / hold / patience (its coins stay its own)
            rc_h = rs._prime_real_cfg(d.get('prime') or {})
            cfg_t = {**cfg_t, **{k: rc_h[k] for k in rs._prime.TIER_KEYS if k != 'trenchCoins' and rc_h.get(k) is not None}}
        if real_t and cur and cfg_t.get('pickVerify', True):   # ✅ a queued pick that turned bad before the bell is dropped, the old coin stays
            for l_ in cur.get('legs') or []:
                to_ = l_.get('swapTo') or {}
                c_ = next((r for r in rs._runner_cands if r.get('mint') == to_.get('mint')), None) if to_ else None
                bad_ = rs._rn.pick_check(c_, rs._runner_cfg())[1] if c_ and c_.get('scanned') and not to_.get('ack') else []   # an acknowledged pick is the owner's call
                if bad_:
                    l_.pop('swapTo', None)
                    cur['events'] = list(cur.get('events') or []) + [{'at': now, 'kind': 'rotate', 'symbol': to_.get('symbol'), 'usd': 0.0,
                                                                       'why': f"✅ your pick ${to_.get('symbol')} failed verification before the bell ({bad_[0]}) — not bought, ${l_.get('symbol')} stays"}]
        # 🆕 NEW COINS ONLY (cfg `newOnly`): the engine's choices are launch coins and nothing else — every door that reached for a
        # major or an old pool (shape seats, seat refills, "no runner → take a pool", extra seats) finds none, so a seat with no
        # qualifying new coin WAITS IN CASH. Coins the owner picked by hand stay (a re-shape never drops a pick).
        new_only_ = bool(real_t and cfg_t.get('newOnly'))
        if new_only_:
            p_t = []
        _step('not too young · not dollar-named · record gate', r_t)
        if real_t and cur and cur.get('rebuy'):   # 🔄 a rebuy waits for its sale to land, then the same coin takes the seat at a new entry
            bl_ = (((rs._fw_peek().get('books') or {}).get(tid) or {}).get('legs') or {}).get(cur['rebuy'].get('mint')) or {}
            cur = rs._prime.rebuy_in(cur, rs._fuse._f(bl_.get('atoms')) > 0, now)
        r_pre_ = list(r_t)   # 🔭 the scout's small ticket may take any SAFE mover (age + checks passed), not only coins on the card's full hunt line
        cb_ready_ = {}
        if real_t and cur and cfg_t.get('comeback', True) and cur.get('comeback'):   # 🔁 riders that left, watched for a recovered dip
            cb_store_, cb_ready_ = rs._prime.comeback_step(cur.get('comeback'), {x.get('mint'): rs._fuse._f(x.get('price')) for x in r_pre_}, now)
            cur = {**cur, 'comeback': cb_store_}
            if cb_ready_:
                r_pre_ = [({**x, 'comeback': cb_ready_[x['mint']]} if x.get('mint') in cb_ready_ else x) for x in r_pre_]
                r_t = [({**x, 'comeback': cb_ready_[x['mint']]} if x.get('mint') in cb_ready_ else x) for x in r_t]
        watch_ = []
        if real_t and cfg_t.get('upMeta', True):   # 🧭 UP NEXT IS META: the engine's own buys need a chart it can read, not falling
            watch_ = [x for x in r_t if not rs._prime.meta_ready(x)]   # 👀 shown under Coming up as "watching", with the reason
            r_pre_, r_t = rs._prime.meta_only(r_pre_, cfg_t, mom), rs._prime.meta_only(r_t, cfg_t, mom)
            _step('not mid-spike · not at its highs · chart readable · not trending down (up-next meta)', r_t)
        if real_t or cfg_t.get('pickStyle') in ('hunt', 'sniper'):   # 🏊 the owner's own runner line (real) · a paper card's own pick style
            r_t = rs._prime.deep_runners(r_t, cfg_t.get('runnerMinLiqK'), cfg_t.get('runnerMinBuy'), cfg_t.get('runnerMinVolK'), cfg_t.get('runnerMinChg1h'))
            _step('your hunt line (pool · volume · 1h move · buyers)', r_t)
        if real_t and cfg_t.get('entryGate'):   # 🎯 clean entries (trench tickets keep their own rules)
            r_t = [x for x in r_t if x.get('trenchOnly') or not rs._prime.entry_gate(x, mom)]
            _step('clean entry — buyers 50%+, not chasing, not at its highs, $50K+ pool, 6h+, $50K+/h', r_t)
        if real_t:   # 💀 never a dead coin (owner: "Coming up coins shouldn't be dead"): nothing in 5 min / < $3K or < 20 trades an hour
            r_t, r_pre_ = [x for x in r_t if not rs._ja.dead_why(x)], [x for x in r_pre_ if not rs._ja.dead_why(x)]
            _step('alive — traded in the last 5 min, $3K+ and 20+ trades an hour', r_t)
        if real_t and (cfg_t.get('vitalMin') or cfg_t.get('organicMin') or cfg_t.get('noSerial')):   # 🎛 the owner's vital filter (Coming up)
            vok_ = lambda x: rs._ja.filter_why((rs._jup_facts.get(x.get('mint')) or (0, None))[1], x, cfg_t) is None
            r_t, r_pre_ = [x for x in r_t if vok_(x)], [x for x in r_pre_ if vok_(x)]
            _step('your vital filter (grade · organic · crew)', r_t)
        # ⏳ STUCK BUYS are replaced HERE, from the fully filtered lists (min age, dollar names, record gate, chart / meta, the owner's
        # hunt line). This swap used to run before all of them, so a refused buy was replaced by ANY liquid coin: $BTT ("−100% inside
        # one candle this hour") took a seat, was refused too, and the seat looped through coins the card would never choose.
        if stuck:   # ⏳ the real card swaps a coin whose buy can't land (benched, or refused 15s ago) for a buyable one NOW
            before_ = cur
            cool_s = rs._prime.cooling(cur, now, cfg_t['rotateHours'], px)   # 🧊 … never for a coin that just left this card
            p_t, r_t = [x for x in p_t if x.get('mint') not in cool_s], [x for x in r_t if x.get('mint') not in cool_s]
            for pa in stuck:
                l = next((x for x in cur['legs'] if x.get('pairAddress') == pa), None)
                if not l:
                    continue
                why_s = "couldn't be bought safely — benched" if l.get('mint') in bench else "buy was refused — trying the next best coin" if l.get('mint') in (book_s.get('misses') or {}) else 'buy never landed in 2 min'
                why_x = ((book_s.get('benched') or {}).get(l.get('mint')) or (book_s.get('misses') or {}).get(l.get('mint')) or {}).get('why')
                why_s += f' ({why_x})' if why_x else ''   # the keeper's own reason, so a refused pick is never silent
                if l.get('picked'):   # 👤 YOUR pick is never swapped out or dropped by the engine — it waits (the keeper retries); ⏏ Pull is yours
                    if now - rs._fuse._f(l.get('waitNoteAt')) > 300:
                        l['waitNoteAt'] = now
                        cur = {**cur, 'events': list(cur.get('events') or []) + [{'at': now, 'kind': 'rotate', 'symbol': l.get('symbol'), 'usd': 0.0,
                                                                                    'why': f"⏳ your pick ${l.get('symbol')}: {why_s} — kept on your seat, the keeper keeps trying (⏏ Pull to drop it)"}]}
                    continue
                try:
                    if cur.get('holdBy') in ('proof', 'agents'):   # 🎮 held: the ENGINE swaps nothing in (2026-10-12: a refused agent buy became $Business, an engine pick)
                        why_s += ' — the card is held, no replacement'
                        raise ValueError('held')
                    want_usd = rs._fuse._f(l.get('wantUnits')) * (rs._fuse._f(px.get(pa)) or rs._fuse._f(l.get('entry')))
                    floor_s = rs._fw.NEW_SEAT_MIN if not rs._fw.held_units(book_s, l.get('mint')) else mo_t   # the keeper's own floor: a NEW coin opens its seat down to $0.05
                    if floor_s and want_usd < floor_s and want_usd < rs._fw.LEFTOVER_MIN_USD:
                        # the seat's money is under the smallest order the keeper sends: another coin would wait just the same
                        why_s = f"its ${want_usd:.2f} is under the smallest order the card can send (${floor_s:.2f})"
                        raise ValueError('unfundable seat')
                    tmp = {**cur, 'legs': [{**x, 'units': rs._fuse._f(x.get('wantUnits'))} if x is l else x for x in cur['legs']]}
                    # ⏭ NEXT UP FIRST (owner: "fall back to retry or swap to the next up buyable"): Coming up's ready coins from the last tick, in its order
                    up_ord = [u.get('mint') for u in ((cur.get('pipeline') or {}).get('up') or []) if not u.get('wait') and u.get('mint') != l.get('mint')]
                    r_pref = sorted(r_t, key=lambda x: up_ord.index(x.get('mint')) if x.get('mint') in up_ord else len(up_ord))
                    cur = rs._prime.replace_leg(tmp, pa, px, p_t, r_pref, anchors, cfg_t, now)
                    in_s = next((x.get('symbol') for x in cur['legs'] if x.get('mint') not in {y.get('mint') for y in tmp['legs']}), None)
                    cur['events'] = cur['events'][:-1] + [{**cur['events'][-1], 'why': f"⏳ ${l.get('symbol')} {why_s} — swapped for {'$' + in_s if in_s else 'a buyable coin'}{' (next up)' if in_s and any(x.get('symbol') == in_s and x.get('mint') in up_ord for x in r_pref) else ''}"}]
                except ValueError:   # nothing buyable of its role: the slot goes back to card cash (refilled next round), never waits forever
                    cur = {**cur, 'legs': [x for x in cur['legs'] if x is not l], 'events': list(cur.get('events') or []) + [
                        {'at': now, 'kind': 'rotate', 'symbol': l.get('symbol'), 'usd': 0.0, 'why': f"⏳ ${l.get('symbol')} {why_s} — slot back to card cash"}]}
            cur = rs._prime.note_dropped(before_, cur, now, cfg_t['rotateHours'], px)   # 🧊 the stuck coin cools like any coin that left
        mine = {l.get('mint') for l in (cur or {}).get('legs') or []}
        p_t = [x for x in p_t if x.get('mint') not in taken or x.get('mint') in mine]
        r_t = [x for x in r_t if x.get('mint') not in taken or x.get('mint') in mine]
        a_t = anchors
        run_ = ({x.get('mint') for x in rs._prime.movers(r_pre_, {}) + rs._prime.movers(r_pre_, cfg_t)} | set(cb_ready_)) if real_t else set()   # 🚀 running now → only the short cool-down
        cool = rs._prime.cooling(cur, now, cfg_t['rotateHours'], px, run_) - mine   # 🧊 coins this card just dropped sit out a few rounds → new coins flow in
        if cool:
            # 💵 A real stop must stay stopped. Falling back to the unfiltered
            # list when discovery was thin caused sell→immediate-rebuy churn.
            p_t = rs._prime_cool_candidates(p_t, cool, 2, strict=real_t)
            r_t = rs._prime_cool_candidates(r_t, cool, 3, strict=real_t)
        # 🪑 30-SECOND SEAT FALLBACK (real card; owner: "fill seats should be 30 secs, not the round"): when no coin clears the card's
        # full line, a seat empty for 30s takes the NEXT-BEST coin — one that passed safety, pool floor, weather, min age and the
        # record gate but is still being watched (at its highs / chart too short / under the hunt line). Never one falling now,
        # mid-spike, trending down, too wild, cooling or already on the card.
        if real_t and cur:
            fb_ids = {x.get('mint') for x in r_t} | set(cool) | mine
            fb_ = [x for x in rs._prime.flow_rank([y for y in list(r_pre_) + list(watch_) if not y.get('trenchOnly')])
                   if x.get('mint') not in fb_ids and rs._prime.seat_fallback_ok(x, mom)]
            # 🟢 … then BUY-BOTTOM coins (the owner's dips: far under their high, at the low of their range, no longer sliding) that
            # passed every safety check, clear the pool floor and the card's min age — a dip before a coin that already ran
            bt_m = {r.get('baseAddress'): r.get('divisionLabel') for r in rs._bottom_cache.get('rows') or []}
            min_age_ = rs._fuse._f(cfg_t.get('runnerMinAgeH'))
            bots_ = [{**r, 'tag': '🟢 buy bottom', 'bottomWhy': bt_m[r['mint']]} for r in rs._runner_cands
                     if r.get('mint') in bt_m and r.get('scanned') and not rs._rn.safety_fails(r, rs._runner_cfg()) and r['mint'] not in fb_ids
                     and _lq(r) >= floor_of(r) and rs._fuse._f(r.get('price')) > 0 and (r.get('ageH') is not None and rs._fuse._f(r.get('ageH')) >= min_age_)]
            fb_ = fb_ + [x for x in bots_ if x['mint'] not in {y.get('mint') for y in fb_}]
            if real_t:   # 🎛 the 30s seat fallback obeys the owner's vital filter too — and never takes a dead coin
                fb_ = [x for x in fb_ if rs._ja.filter_why((rs._jup_facts.get(x.get('mint')) or (0, None))[1], x, cfg_t) is None and not rs._ja.dead_why(x)]
            # ⏭ COMING UP BY CATEGORY (owner: "pick 1 of the best from the top for swap in categories"): each list (Pump trending,
            # Volume, Dips & bottoms, Movers, New launches, Trench) walked from ITS top; the first coin that passed the safety scan,
            # clears the pool floor + the card's min age, isn't dollar-named and is a sane entry (not falling / mid-spike / trending
            # down / too wild / at its highs) is that category's pick. They go FIRST in the 30s seat fallback: what Coming up shows
            # is what an empty seat takes.
            cand_by = {r.get('mint'): r for r in rs._runner_cands if r.get('mint')}
            seen_by = {x.get('mint'): x for x in list(r_pre_) + list(watch_) if x.get('mint')}
            def _cat_row(r):
                c_ = cand_by.get(r.get('mint'))
                return {**c_, **(seen_by.get(r.get('mint')) or {})} if c_ else None
            def _cat_ok(r):   # True, or the FIRST check it failed (shown per category under Coming up)
                x = _cat_row(r)
                if not x:
                    return 'not on the runner board yet'
                if not x.get('scanned'):
                    return 'holder scan not done'
                if rs._rn.safety_fails(x, rs._runner_cfg()):
                    return 'failed safety'
                if x['mint'] in fb_ids:
                    return 'on the card / cooling / already next'
                if _lq(x) < floor_of(x):
                    return 'pool under your floor'
                if rs._fuse._f(x.get('price')) <= 0:
                    return 'no live price'
                if x.get('ageH') is None or rs._fuse._f(x.get('ageH')) < min_age_:
                    return f'under your {min_age_:g}h min age'
                if rs._fw.dollar_named(x.get('symbol')):
                    return 'dollar-named'
                if rs._prime.at_high(x):
                    return 'at its highs'   # 🏔 never a coin sitting at its highs (owner)
                if not rs._prime.seat_fallback_ok(x, mom):
                    return 'falling / spiking'
                if real_t and rs._ja.dead_why(x):
                    return 'dead (nobody trading it)'
                vw_ = rs._ja.filter_why((rs._jup_facts.get(x['mint']) or (0, None))[1], x, cfg_t) if real_t else None
                if vw_:
                    return 'your vital filter'
                return True
            open_by = {r['mint']: r for r in (rs._open_board() if rs._open_pairs else (rs._open_cache.get('rows') or [])) if r.get('mint')}   # every feed coin, scanned or not
            cat_lists = {**rs._lens_rows, 'bottom': [{'mint': r.get('baseAddress')} for r in rs._bottom_cache.get('rows') or []],
                         'trench': [{'mint': r.get('mint')} for r in rs._trench_cache.get('rows') or []] or [{'mint': m} for m in list(open_by)[:60]]}   # 🗑 never an empty door: the open list stands in
            try:
                cat_picks, cat_miss = rs._prime.category_picks(cat_lists, _cat_ok, rs._list_records())
            except Exception:
                cat_picks, cat_miss = [], {}
            cat_rows = [{**_cat_row(p_), 'tag': f"{p_['catLabel']} #{p_['rank']}", 'cat': p_['cat'], 'catRank': p_['rank']} for p_ in cat_picks]
            # 🧬 EDGE FIRST (owner: "coming up should be the best of my swap-in, not bs"): every coin of the swap-in lists ranked by evidence
            # (confluence.py); the ones that clear every check of this card come first — Coming up shows them and an empty seat takes them.
            edge_ready, edge_watch = [], []
            if real_t:
                for e_ in rs._edge_rank()[:80]:
                    m_ = e_.get('mint')
                    if not m_ or m_ in mine:
                        continue
                    if e_['edge']['known'] and e_['edge']['edge'] <= rs.EDGE_BUY_MIN:
                        continue   # the evidence says it typically loses badly: never Coming up, never an engine buy
                    v_ = _cat_ok({'mint': m_})
                    if v_ is True:
                        edge_ready.append({**_cat_row({'mint': m_}), 'tag': rs._cf.words(e_['edge']), 'edge': e_['edge'], 'cat': 'edge'})
                    elif v_ not in ('not on the runner board yet', 'holder scan not done', 'failed safety', 'dead (nobody trading it)') and len(edge_watch) < 6:
                        edge_watch.append({**(_cat_row({'mint': m_}) or e_), 'tag': rs._cf.words(e_['edge']), 'edge': e_['edge'], 'watchWhy': v_})
                    if len(edge_ready) >= 6:
                        break
                if edge_ready and cfg_t.get('flowEntry', True):   # 🌊 FLOW ENTRY: never buy into a minute where sellers lead (the tape of the top 4)
                    fl_ = await rs._flow_fetch([x.get('pairAddress') for x in edge_ready[:8]])
                    ok_, held_ = [], []
                    for x in edge_ready:
                        w_ = fl_.get(x.get('pairAddress'))
                        why_ = rs._flow.entry_why(w_) if x.get('pairAddress') in fl_ else None
                        x = {**x, 'flow': {k: w_.get(k) for k in ('buyUsd', 'sellUsd', 'n', 'pxChg')} if w_ else None}
                        (held_ if why_ else ok_).append({**x, 'watchWhy': why_} if why_ else x)
                    burst_ = []
                    for x in ok_:   # ⚡ BUY BURST: a coin whose last 90s is a buying burst goes to the front (it is tagged; its own record is 'burst')
                        bw_ = rs._dg.burst_why(fl_.get(x.get('pairAddress')))
                        if bw_:
                            burst_.append({**x, 'tag': f"⚡ buy burst · {x.get('tag') or ''}".strip(' ·'), 'burst': bw_})
                    edge_ready = burst_ + [x for x in ok_ if x.get('mint') not in {y['mint'] for y in burst_}]
                    rs._burst_last = [(x['mint'], rs._fuse._f(x.get('price'))) for x in burst_]
                    for x in edge_ready:
                        if rs._smart_on(x.get('mint')):
                            x['tag'] = f"🐳 {len(rs._smart_on(x['mint']))} smart · {x.get('tag') or ''}".strip(' ·')
                    edge_watch = held_ + edge_watch
                cat_rows = edge_ready + [x for x in cat_rows if x.get('mint') not in {y['mint'] for y in edge_ready}]
            # 🚪 EVERY DOOR ALWAYS SHOWS ONE COIN (owner: "1 trench, 1 pump, 1 volume"): a door with nothing that clears every check shows its
            # best coin as WATCHING, with the first check it misses. Watch rows are only shown — never seated by the engine, owner-pickable.
            door_watch = rs._prime.door_watch(
                cat_picks, cat_lists, lambda r_: _cat_row(r_) or open_by.get(r_.get('mint')),
                lambda r_, x_: _cat_ok(r_) if _cat_row(r_) else ('failed safety' if x_.get('safe') is False else 'holder scan not done'),
                lambda m_, x_: m_ in fb_ids or m_ in mine or rs._fuse._f(x_.get('price')) <= 0 or rs._fw.dollar_named(x_.get('symbol')))
            fb_ = cat_rows + [x for x in fb_ if x.get('mint') not in {y['mint'] for y in cat_rows}]
            cfg_t = {**cfg_t, 'seatFallback': list({x.get('mint'): x for x in reversed(fb_)}.values())[::-1][:8], 'catPicks': cat_rows, 'catWatch': door_watch, 'catMiss': cat_miss,
                     'edgeReady': edge_ready, 'edgeWatch': edge_watch}
        if real_t and cfg_t.get('bangerRefill'):   # 🚀 every seat that opens (flow exit, stop, rotation, ride over) takes a banger first
            b_ = rs._bangers(mine, cool, mom, _lq, rs._fw.clean_cfg(fw_cfg)['minLiqUsd'], now, gate=bool(cfg_t.get('entryGate')))
            if b_:   # 🌊 the tape decides the order: ⚡ burst / 🧲 absorb first, a 🩸 dump or 🏔 climax (buying the top) waits
                fl_b = await rs._flow_fetch([x.get('pairAddress') for x in b_[:8]])
                tp_ = {x['mint']: rs._flow.tape_read(fl_b.get(x.get('pairAddress'))) for x in b_}
                b_ = [{**x, 'tape': tp_.get(x['mint']), **({'tag': f"{rs._flow.TAPES[tp_[x['mint']]]} · {x['tag']}"} if tp_.get(x['mint']) in ('burst', 'absorb') else {})}
                      for x in b_ if tp_.get(x['mint']) not in ('dump', 'climax')]
                b_ = sorted(b_, key=lambda x: 0 if x['tag'].startswith(('⚡', '🧲')) else 1)
            cfg_t = {**cfg_t, 'bangers': b_}
            rs._best_rows[:] = list(b_ or [])   # 🏆 the 🏆 Best now tab + the card's Best 3 read this list
        if real_t and cfg_t.get('entryGate'):   # 🎯 the 30s seat fallback and Coming up's category picks obey clean entries too
            cfg_t = {**cfg_t, 'seatFallback': [x for x in cfg_t.get('seatFallback') or [] if not rs._prime.entry_gate(x, mom, core=True)]}   # 🪑 the 30s fill: core rules only
        if real_t and cfg_t.get('volCycle'):   # 🪑 EMPTY SEATS FILL FROM THE VOLUME LIST TOO (owner: "seats are supposed to auto fill"): the engine's own funnel
            # often ends at 0 coins, and the volume cycle only ever REPLACED a flat coin — an empty seat sat in cash. Same rows the cycle buys
            # (6h+, $50K+ pool, $50K+/h, buyers ahead, rush-clean), busiest first, ahead of the 30s fallback list.
            vr_ = [{**x, 'liquidityUsd': x.get('liq'), 'tag': '🌊 volume'} for x in rs._prime.vol_cycle_rows([rs._with_tv(y) for y in rs._open_board() or [] if y.get('safe') is True])
                   if x.get('mint') not in mine and x.get('mint') not in cool and x.get('mint') not in bench and _lq(x) >= rs._fw.clean_cfg(fw_cfg)['minLiqUsd']
                   and not rs._fw.dollar_named(x.get('symbol')) and rs._fuse._f(x.get('price')) > 0][:4]
            cfg_t = {**cfg_t, 'seatFallback': vr_ + [x for x in cfg_t.get('seatFallback') or [] if x.get('mint') not in {y['mint'] for y in vr_}]}
        # 🧊 anchors cool too: a major this card just sold isn't bought back for 3 rounds while another major is available
        a_t = rs._prime_cool_candidates(anchors, cool, 2, strict=real_t and len([x for x in anchors if x.get('mint') not in cool]) >= 1) if cool else anchors
        if new_only_:
            a_t = []
        # 🚀 MOVER UPGRADE (real cards, cfg `moverSwap`): a coin that is not moving (±10% of its entry after 20 min, never a rider /
        # frozen / picked coin) gives its seat to a coin that IS — the card's own hunt selection, else ≥ $50K in the hour and up
        # ≥ 20%. One per card per 30 min. Rotation only ever swapped LOSERS, so a flat coin sat on the card for good while a
        # hunt-ready coin waited on the board (2026-10-06: $USDP +2% held, $GOMO +44% / $123K an hour not bought).
        # 🔭 SCOUT & PROMOTE (cfg `scoutPct` > 0) replaces the plain mover swap: one small ticket hops between movers every round;
        # a scout that proves itself is promoted to a full-size holder (arena_prime.scout_step).
        _lrec = rs._list_records() if real_t else {}
        _movers_off = rs._prime.list_paused(_lrec, 'movers')   # movers' own 1h record is a clear loser → the FULL-SIZE mover swap sits out (the scout's small ticket still hunts)
        if real_t and cur and rs._fuse._f(cfg_t.get('scoutPct')) > 0 and now - rs._fuse._f(cur.get('scoutAt')) >= max(120.0, rs._fuse._f(cfg_t.get('rotateHours')) * 3600 * 0.9):
            was_ = cur
            hot_s = [x for x in [y for y in r_pre_ if y.get('comeback')] + rs._prime.movers(r_t, cfg_t) + rs._prime.movers(r_pre_, {}) if x.get('mint') not in mine and x.get('mint') not in cool and x.get('mint') not in taken]
            nw_ = rs._prime.scout_step(cur, px, rs._prime.flow_rank(list({x['mint']: x for x in reversed(hot_s)}.values())[::-1]), cfg_t, now, p_t, anchors)   # the scout takes the best-LOOKING mover, not just the biggest hour
            if nw_ is not cur:
                cur = rs._prime.note_dropped(was_, {**nw_, 'scoutAt': now}, now, cfg_t['rotateHours'], px)
        elif real_t and cur and not _movers_off and cfg_t.get('moverSwap', True) and not cur.get('holdAll') and not cur.get('flooredAt') and now - rs._fuse._f(cur.get('moverAt')) >= rs._prime.MOVER_EVERY_SEC:
            hot_ = [x for x in rs._prime.movers(r_t, cfg_t) if x.get('mint') not in mine]
            fl_ = rs._prime.flat_leg(cur, px, now, max(rs._prime.FLAT_HOLD_SEC, rs._fuse._f(cfg_t.get('minHoldMins')) * 60)) if hot_ else None
            if fl_:
                try:
                    was_ = cur
                    nw_ = rs._prime.replace_leg(cur, fl_['pairAddress'], px, p_t, hot_, anchors, cfg_t, now)
                    in_ = next((l for l in nw_['legs'] if l.get('mint') not in mine), None)
                    row_ = next((x for x in hot_ if in_ and x.get('mint') == in_.get('mint')), {})
                    nw_['events'] = nw_['events'][:-1] + [{**nw_['events'][-1], 'why': f"🚀 mover in: ${(in_ or {}).get('symbol')} is up {rs._fuse._f(row_.get('chg1h')):+.0f}% on the hour on ${rs._fuse._f(row_.get('vol1h')) / 1000:,.0f}K volume — ${fl_.get('symbol')} was not moving"}]
                    nw_['moverAt'] = now
                    cur = rs._prime.note_dropped(was_, nw_, now, cfg_t['rotateHours'], px)
                except ValueError:
                    pass
        # 🌊 VOLUME CYCLE (owner: "need to be cycling new volume coins"): every `volEvery` min a coin that is NOT moving (±10% after its hold —
        # your picks too, the owner gave the keys; ❄ frozen / riding / house coins never) gives its seat to the busiest clean volume coin
        # on the open list. Every keeper check still decides the buy.
        if real_t and cur and cfg_t.get('volCycle') and not cur.get('holdAll') and not cur.get('flooredAt') and now - rs._fuse._f(cur.get('volAt')) >= rs._fuse._f(cfg_t.get('volEvery') or 10) * 60:
            fwc_v = rs._fw.clean_cfg(fw_cfg)
            hot_v = [x for x in rs._prime.vol_cycle_rows([rs._with_tv(y) for y in rs._open_board() or [] if y.get('safe') is True])
                     if x.get('mint') not in mine and x.get('mint') not in cool and x.get('mint') not in bench and _lq(x) >= fwc_v['minLiqUsd']
                     and not rs._fw.dollar_named(x.get('symbol')) and rs._fuse._f(x.get('price')) > 0][:6]
            fl_v = rs._prime.flat_leg(cur, px, now, max(600.0, rs._fuse._f(cfg_t.get('minHoldMins')) * 60), picks=True) if hot_v else None
            if fl_v:
                try:
                    was_ = cur
                    hot_v = [{**x, 'liquidityUsd': x.get('liq'), 'score': 100} for x in hot_v]
                    nw_ = rs._prime.replace_leg(cur, fl_v['pairAddress'], px, p_t, hot_v, anchors, cfg_t, now)
                    in_ = next((l for l in nw_['legs'] if l.get('mint') not in mine), None)
                    row_ = next((x for x in hot_v if in_ and x.get('mint') == in_.get('mint')), {})
                    g_ = (rs._fuse._f(px.get(fl_v['pairAddress'])) / rs._fuse._f(fl_v.get('entry')) - 1) * 100 if rs._fuse._f(fl_v.get('entry')) > 0 else 0.0
                    nw_['events'] = nw_['events'][:-1] + [{**nw_['events'][-1], 'why': f"🌊 volume cycle: ${(in_ or {}).get('symbol')} in — ${rs._fuse._f(row_.get('vol1h')) / 1000:,.0f}K traded this hour, {rs._fuse._f(row_.get('buyShare')):.0f}% buys, {rs._fuse._f(row_.get('chg1h')):+.0f}% 1h — ${fl_v.get('symbol')} was flat ({g_:+.1f}%)"}]
                    for l in nw_['legs']:
                        if in_ and l.get('mint') == in_.get('mint'):
                            l['bought'] = {**(l.get('bought') or {}), 'tag': '🌊 volume'}
                            l.pop('picked', None)   # the ENGINE's choice (replace_leg marks hand swaps as yours) — you-vs-engine stays true
                    nw_['volAt'] = now
                    cur = rs._prime.note_dropped(was_, nw_, now, cfg_t['rotateHours'], px)
                except ValueError:
                    pass
        # 🤖 AGENT SEATS: coins the agents put on the card hold until `agentTakePct` profit; in profit the desk reads them again and lets them
        # run, pulls them (profit to cash, seat left open) or swaps them for a fresh GO runner (agents.manage). Only while they are proven.
        if real_t and cur:   # 🎮 the card as seats for HQ › Agents (display only)
            rs._agents['card'] = rs._pos.card_seats(cur, None, px, cfg_t, take=rs._of.take_line(cfg_t, rs._agents.get('scalp')))
        # 🎮 AGENT CONTROL (cfg `agentControl`; owner, 2026-10-10: "the agents should have control over my seats and switching coins … real
        # moves on my real money card — GO"): the card is held BY THE AGENTS (`holdBy: 'agents'` — every engine door that checks holdAll is
        # off: rotation, re-shape, rush, cycles, the engine's seat refill) and only they buy: they fill empty seats with `eligible` GO coins,
        # switch a coin whose read broke (after 15 min), bank at their take line. ≤ CONTROL_MOVES_HR real buys an hour.
        ctl_ = bool(real_t and cur and cfg_t.get('agentControl') and not cur.get('flooredAt'))
        if ctl_ and not (cur.get('holdAll') and cur.get('holdBy') == 'agents') and (not cur.get('holdAll') or cur.get('holdBy') == 'proof'):
            cur = {**cur, 'holdAll': True, 'holdBy': 'agents', 'events': (list(cur.get('events') or []) + [{'at': now, 'kind': 'hold', 'why': '🎮 the agents control every seat — the engine\'s own swaps are off'}])[-60:]}
        ctl_ = bool(ctl_ and cur.get('holdBy') == 'agents')   # a hold the owner set by hand stays a hold: nobody trades
        pol_ = rs._oe.policy(cfg_t) if real_t and cur else None   # 🎛 the creator's limits: per control AGENTS CHOOSE or CREATOR OVERRIDE
        if real_t and cur:   # 🔌 positions are "reconciled" once every held coin was read back with a live price in this process
            if all(rs._fuse._f(px.get(l.get('pairAddress'))) > 0 for l in cur.get('legs') or [] if not l.get('placeholder') and rs._fuse._f(l.get('units')) > 0):
                rs._office['boot']['reconciled'] = True
            rs._office['ticks'] = (list(rs._office.get('ticks') or []) + [now])[-6:]
        rd_ = rs._oe.ready(rs._office['boot'], now)
        rs._office['ready'] = rd_   # the kernel's Courier reads the office's readiness
        if ctl_:
            cur['agentWant'] = pol_['seats']
        moves_ = max(0, rs._uni.CONTROL_MOVES_HR - rs._oe.real_buys(cur.get('events'), rs._fw_full_ledger(), tid, now, moves=('swap',))) if ctl_ else None   # 🧮 SWITCHES (real buys only)
        fills_left_ = max(0, rs._uni.FILL_MOVES_HR - rs._oe.real_buys(cur.get('events'), rs._fw_full_ledger(), tid, now, moves=('fill',))) if ctl_ else None   # 🪑 empty-seat fills
        if real_t and cur and (ctl_ or (((cfg_t.get('agentFeed') and (rs._agents.get('view') or {}).get('feed')) or cfg_t.get('agentLearn')) and not cur.get('holdAll'))) and not cur.get('flooredAt'):
            # ⚙ HELD SEATS — ONE brain: the kernel's position manager (trench_kernel.positions) + Reaper (office.reap). A challenger is a coin the
            # kernel has READY; a held coin and its challenger are compared on the kernel's own rank. No paper call, case file, lean or duty clock.
            due_ = bool(ctl_ and moves_ and rs._oe.cycle_due(pol_, cur.get('agentCycleAt'), now))
            if due_:
                cur['agentCycleAt'] = now; rs._office['cycleN'] = int(rs._office.get('cycleN') or 0) + 1
            cool = set(cool) | rs._agent_blocked(cur, now)
            on_k = {l.get('mint') for l in cur.get('legs') or []}
            ranks_ = rs._tk.KERNEL.ranks()
            ready_ = [c_ for c_ in (rs._tk.KERNEL.candidate(m_, d_) for m_, d_ in rs._tk.KERNEL.ready(exclude=set(cool) | on_k)) if c_ and not rs._fw.dollar_named(c_.get('symbol'))]
            cases_ = rs._tk.KERNEL.cases(exclude=on_k) if ctl_ else []
            full_ = bool(ctl_ and len([l for l in cur.get('legs') or [] if not l.get('placeholder')]) >= pol_['seats'])
            # 🔌 a coin is "off the board" only when the office is LIVE again after a restart AND it has been missing for the grace
            radar_ = {m_ for m_, p_ in (rs._office.get('pos') or {}).items() if rs._oe.radar_gone(p_.get('offSince'), now, rd_['live'])}
            vels_, margins_ = {}, {}
            scores_ = {m_: {'score': r_} for m_, r_ in ranks_.items()}   # 🏅 the kernel's rank IS the seat score (one ranking)
            if ctl_:
                try:
                    vels_ = rs._office_vels(cur, px, now)
                    best_r = ranks_.get(ready_[0]['mint']) if ready_ else None
                    for l in cur.get('legs') or []:
                        hr_ = ranks_.get(l.get('mint'))
                        if best_r is not None and hr_ is not None:   # (how far the best READY coin outranks this seat, what a switch needs)
                            margins_[l.get('mint')] = (round(best_r - hr_, 1), round(hr_ * (rs._pos.margin_need(pol_['switch'].get('mode')) - 1), 1))
                except Exception as e:
                    print('seat ranks:', e)
            dec_ = rs._pos.manage(cur.get('legs'), rs._agents.get('table'), px, cfg_t, rs._agents.get('scalp'), control=ctl_, now=now, moves_left=((1 if due_ and full_ else 0) if ctl_ else moves_),   # an EMPTY seat comes first: no switch while one is open
                               challengers=ready_, pol=pol_, radar=radar_, reviews={r_.get('mint'): r_.get('verdict') for r_ in rs._office.get('reports') or []}, live=rd_['live'], ranks=ranks_, vels=vels_ or None)
            # 🪑 A TIME EXIT IS A SWAP: it fires only while a buy is free AND a READY replacement exists NOW (after the empty seats take theirs)
            open_n = max(0, int(rs._fuse._f((pol_ or {}).get('seats'))) - len([l for l in cur.get('legs') or [] if not l.get('placeholder')]))
            spare_ = None if fills_left_ is None else min(fills_left_, len(ready_)) - open_n
            dec_ = rs._office_reap(cur, px, cfg_t, ctl_, now, dec_, pol_, rd_['live'], vels_, margins_, spare_, edge=margins_)   # ☠ Reaper's exit requests join the SAME decision list (it has no path of its own)
            cert_ = {l.get('pairAddress') for l in cur.get('legs') or [] if l.get('certified') and not l.get('placeholder')}
            if cert_:   # 🛡 a coin YOU certified is yours to hold — the desk's own swap / pull never touches it (only a pulled pool, −45%, your limits)
                dec_ = [x for x in dec_ if x.get('pair') not in cert_ or any(h_ in str(x.get('why')) for h_ in ('R1 ', 'R5x', 'R5c', 'R5g', 'R9c', 'drain'))]
            g4p_ = {l.get('pairAddress'): l for l in cur.get('legs') or [] if l.get('aiSeat') and not l.get('placeholder')}
            for gs_ in [x_ for x_ in (rs._g4.pop('set', None), rs._g4.pop('setAgent', None)) if x_ and rs._seat.fresh(x_, now)]:   # 🎯 a model moved take / stop / trail: its own seat, or an agents coin (never yours / certified)
                for l in cur['legs']:
                    if l.get('pairAddress') == gs_.get('pair') and not l.get('placeholder') and not l.get('certified') and (l.get('aiSeat') if gs_.get('own') is not False else (rs._uni.is_agent(l) and not l.get('picked') and not l.get('aiSeat'))):
                        e_, p_ = rs._fuse._f(l.get('entry')), rs._fuse._f(px.get(l.get('pairAddress')))
                        ch_ = rs._seat.line_change(l, {'aiTp': gs_.get('tp'), 'aiSl': gs_.get('sl'), 'aiTrail': gs_.get('trail')}, (p_ / e_ - 1) * 100 if e_ > 0 and p_ > 0 else None)   # 🛑 no −3% stops, no 35 ↔ 30 jitter
                        l.update(ch_)
                        if ch_ and not l.get('aiSeat'):
                            l['aiBy'] = gs_.get('by')
                        if ch_:
                            cur.setdefault('events', []).append({'at': now, 'kind': 'agent', 'move': 'lines', 'why': f"🎯 {gs_.get('by')} set ${l.get('symbol')}: " + ' · '.join(f"{ {'aiTp': 'TP +', 'aiSl': 'SL −', 'aiTrail': 'trail ↩'}[k_]}{v_:g}%" for k_, v_ in ch_.items())})
            if g4p_:   # 🧠 G4's seat: the agents only argue — a pulled pool, −45% and the creator's own limits still sell it
                dec_ = [x for x in dec_ if x.get('pair') not in g4p_ or any(h_ in str(x.get('why')) for h_ in ('R1 ', 'R5x', 'R5c', 'R9c', 'drain'))]
                w_ = rs._g4.get('want')
                if w_ and w_.get('action') == 'SELL' and rs._seat.fresh(w_, now) and pol_.get('aiSeat') == 'real' and w_.get('pair') in g4p_ and not any(x.get('pair') == w_['pair'] for x in dec_):
                    dec_.append({'action': 'pull', 'pair': w_['pair'], 'symbol': g4p_[w_['pair']].get('symbol'), 'why': f"🧠 {w_.get('model') or 'G4'} sold: {w_.get('why')}", 'bank': w_.get('bank'), 'bankBy': w_.get('model')})
                    rs._g4['want'] = None
                elif w_ and w_.get('action') == 'TRIM' and rs._seat.fresh(w_, now) and pol_.get('aiSeat') == 'real' and w_.get('pair') in g4p_ and not any(x.get('pair') == w_['pair'] for x in dec_):
                    dec_.append({'action': 'trim', 'pair': w_['pair'], 'symbol': g4p_[w_['pair']].get('symbol'), 'pct': w_.get('trim') or 50, 'why': f"🧠 {w_.get('model') or 'G4'} banked {w_.get('trim') or 50}%: {w_.get('why')}", 'bank': w_.get('bank'), 'bankBy': w_.get('model')})   # ✂ its trade, its call
                    rs._g4['want'] = None
            if ctl_:   # ⇄ the switching evaluation the page shows: each held coin against the best READY challenger (display only — `positions.manage` decided)
                try:
                    verd_ = {r_.get('mint'): r_.get('verdict') for r_ in rs._office.get('reports') or []}
                    held_l = [l for l in cur.get('legs') or [] if not l.get('placeholder') and rs._fuse._f(l.get('units')) > 0 and rs._fuse._f(l.get('entry')) > 0 and rs._fuse._f(px.get(l.get('pairAddress'))) > 0]
                    tests_ = [{'mint': l.get('mint'), **rs._pos.switch_view(l, (rs._fuse._f(px[l['pairAddress']]) / rs._fuse._f(l['entry']) - 1) * 100, (now - rs._fuse._f(l.get('at'))) / 60 if l.get('at') else 0.0,
                                                                        ready_[0] if ready_ else None, ranks_, pol_, verd_.get(l.get('mint')), vels_.get(l.get('mint')))} for l in held_l]
                    rs._agents['switchTests'] = tests_
                    rs._agents['switchEval'] = None if not tests_ else {**min(tests_, key=lambda t_: (not t_['switch'], t_['current']['pnl'])), 'at': now, 'dueIn': max(0, round(rs._fuse._f(cur.get('agentCycleAt')) + max(30.0, rs._fuse._f(pol_['seatTarget'])) - now)), 'full': full_}
                except Exception as e:
                    print('switch eval:', e)
            try:
                cur = rs._germ_rebuy_step(cur, px, now)   # 🦠 a coin your Gstop sold printed a NEW germ floor: it is queued back as your seat pick
            except Exception as e:
                print('germ rebuy:', e)
            rs._agents['decisions'] = [{k: v for k, v in x.items() if k != 'to'} | ({'toSym': x['to']['symbol']} if x.get('to') else {}) for x in dec_]
            rs._agents['card'] = rs._pos.card_seats(cur, rs._agents['decisions'], px, cfg_t, take=rs._of.take_line(cfg_t, rs._agents.get('scalp')))
            night_ = False
            if real_t and cfg_t.get('nightGuard', True) is not False:   # 🌙 the circuit breaker: a paused card buys NOTHING real (exits keep running)
                try:
                    if rs._night_check(now):
                        cfg_t, night_ = {**cfg_t, 'agentPaper': True}, True
                except Exception as e:
                    print('night guard:', str(e)[:120])
            paper_ = bool(cfg_t.get('agentPaper'))
            for x in dec_:
                try:
                    if x['action'] == 'swap' and (paper_ or cfg_t.get('deskBuysOff')):   # 📄 a switch-in is a real BUY: on paper, or with desk buys off, it is only recorded (the shadow book)
                        rs._shadow_note(x.get('to'), 'switch', now, cur); continue
                    if x['action'] == 'swap' and ctl_ and rs._office_warden(cur, x['to'], rs._fuse._f(next((rs._fuse._f(l.get('units')) * (rs._fuse._f(px.get(l.get('pairAddress'))) or rs._fuse._f(l.get('entry'))) for l in cur.get('legs') or [] if l.get('pairAddress') == x['pair']), 0.0)), cfg_t, now, 'swap')['veto']:
                        continue   # 🛡 a switch carries the old seat's money as it is: the Warden may only veto it
                    if x['action'] == 'pull' and 'R5g' in str(x.get('why')):   # 🦠 a Gstop sale: watch the coin for a NEW germ floor to buy it back
                        lg_g = next((l for l in cur.get('legs') or [] if l.get('pairAddress') == x['pair']), None)
                        if lg_g:
                            cur['germRebuy'] = {**{m_: v_ for m_, v_ in (cur.get('germRebuy') or {}).items() if now - rs._fuse._f(v_.get('at')) < rs.GERM_REBUY_SEC},
                                                lg_g.get('mint'): {'pair': x['pair'], 'symbol': lg_g.get('symbol'), 'lens': lg_g.get('gstop') or 'both', 'at': now, 'px': rs._fuse._f(px.get(x['pair']))}}
                    if real_t and x['action'] in ('pull', 'trim') and ctl_:   # 🕰 agent min hold: a soft exit of a red coin waits 15 min from the buy
                        lg_w = next((l for l in cur.get('legs') or [] if l.get('pairAddress') == x['pair']), None)
                        w_ = rs._prime.agent_hold_wait(lg_w, px.get(x['pair']), x.get('why'), now)
                        if w_ > 0:
                            x['held'] = f"🕰 min hold: {round(w_ / 60)} min left before an agent may sell it (stops / rug still act)"
                            continue
                    if x['action'] == 'pull' and ctl_:
                        was_ = cur
                        lg_ = next((l for l in cur.get('legs') or [] if l.get('pairAddress') == x['pair']), None)
                        if lg_ and rs._fuse._f(lg_.get('entry')) > 0 and 0 < rs._fuse._f(px.get(x['pair'])) < rs._fuse._f(lg_['entry']):   # left at a loss: this thesis is not bought back for 6h
                            st_o = rs._office_state(); st_o['lostAt'] = {**{m_: a_ for m_, a_ in (st_o.get('lostAt') or {}).items() if now - rs._fuse._f(a_) < rs._oe.FAILED_SEC}, lg_.get('mint'): now}
                        cur['agentExitAt'] = now
                        cur = rs._prime.agent_pull(cur, x['pair'], px, liqs, now, x['why'])   # in control: banked to FREE card cash, the seat opens for their next coin
                        if x.get('bank'):   # 🅿 the model chose to park this sale's proceeds out of the coins for 1–3 rounds
                            cur = rs._prime.park_bank(cur, rs._fuse._f((cur['events'][-1] or {}).get('usd')), x['bank'], now, x.get('symbol'), x.get('bankBy'))
                        cur = rs._prime.note_dropped(was_, cur, now, cfg_t['rotateHours'], px)
                    elif x['action'] == 'trim' and ctl_:   # 💰 scale-out: half banked, the rest rides the trail
                        cur = rs._prime.agent_trim(cur, x['pair'], px, liqs, now, x.get('pct') or rs._of.PICK_LOCK_SELL if (x.get('pct') or 'R5b' in str(x['why'])) else (rs._of.scale_of(pol_) or (0, rs._of.SCALE_PCT))[1], x['why'])   # 🔒 your pick: a portion, the rest rides your stop
                        if x.get('bank'):
                            cur = rs._prime.park_bank(cur, rs._fuse._f((cur['events'][-1] or {}).get('usd')), x['bank'], now, x.get('symbol'), x.get('bankBy'))
                    elif x['action'] == 'pull':
                        cur = rs._prime.sell_leg_to_cash(cur, x['pair'], px, now, 100.0)
                        cur['events'].append({'at': now, 'kind': 'agent', 'symbol': x['symbol'], 'why': f"🤖 agents pulled ${x['symbol']}: {x['why']}"})
                    elif x['action'] == 'swap':
                        t_ = x['to']
                        row_ = {'mint': t_['mint'], 'symbol': t_['symbol'], 'pairAddress': t_['pair'], 'price': t_['px'], 'liquidityUsd': (t_.get('nums') or {}).get('liq'), 'score': 100,
                                'ageH': (t_.get('vitals') or {}).get('ageH'), 'vol1h': (t_.get('vitals') or {}).get('vol1h'), 'buyShare': (t_.get('nums') or {}).get('buy')}
                        was_ = cur
                        cur = rs._prime.replace_leg(cur, x['pair'], px, p_t, [row_], anchors, cfg_t, now)
                        for l in cur['legs']:
                            if l.get('mint') == t_['mint']:
                                l.update(bought={**(l.get('bought') or {}), 'tag': '🤖 agents READY · switch'}, slMode='hold', rideOrRug=True, ticket=True); l.pop('picked', None)
                                if rs._uni.in_lane(t_.get('vitals') or {}):
                                    l['trench'] = True
                        cur['events'] = cur['events'][:-1] + [{**cur['events'][-1], 'kind': 'agent', 'move': 'swap', 'mint': t_['mint'], 'why': f"🤖 agents swapped ${x['symbol']} for ${t_['symbol']}: {x['why']}"}]
                        if ctl_:
                            cur['agentDutyAt'] = now
                        cur = rs._prime.note_dropped(was_, cur, now, cfg_t['rotateHours'], px)
                except ValueError:
                    continue
        if ctl_:   # ⚙ EMPTY SEATS — ONE candidate lifecycle: every fill comes from the kernel's READY list (ranked once, by the ten-agent brain)
            used_ = rs._oe.real_buys(cur.get('events'), rs._fw_full_ledger(), tid, now, moves=('fill',))   # 🪑 empty-seat fills (real buys only: a seat that never bought is not a buy)
            cfg_s = {**cfg_t, 'coins': pol_['seats']}
            held_n = len([l for l in cur.get('legs') or [] if not l.get('placeholder')])
            empty_n = max(0, pol_['seats'] - held_n)
            sic_want_ = (rs._g4.get('want') or {}).get('source') == 'sicario'   # 🎩 owner 2026-11-05: all 4 seats are open to a Sicario's PoW, desk buys stay off for everything else
            g4_seat_ = pol_.get('aiSeat') == 'real' and ((not cfg_t.get('deskBuysOff') and not any(l.get('aiSeat') and not l.get('placeholder') for l in cur.get('legs') or [])) or (sic_want_ and empty_n > 0))
            if g4_seat_ and empty_n:   # 🧠 one empty seat is G4's while its seat is on: the agents fill the rest
                empty_n -= 1
            if empty_n and not cur.get('agentEmptyAt'):
                cur['agentEmptyAt'] = now
            elif not empty_n:
                cur.pop('agentEmptyAt', None); rs._office.pop('validSince', None)
            rs._DUO_GATE['on'] = cfg_t.get('agentDuoGate', True) is not False
            blk_ = rs._agent_blocked(cur, now) | {l.get('mint') for l in cur.get('legs') or []}
            valid_ = [c_ for c_ in (rs._tk.KERNEL.candidate(m_, d_) for m_, d_ in rs._tk.KERNEL.ready(exclude=blk_)) if c_ and not rs._fw.dollar_named(c_.get('symbol'))]
            valid_ = sorted([c_ for c_ in valid_ if rs._agent_entry_ok(c_)],   # 🎯 EVERY agent door enters like OSSY / G4 (owner, 2026-10-18: "they are on point"): the three setups, no gun line / chase / spike /
                            key=lambda c_: (0 if (rs._pred_of(c_.get('mint'), now) or 0) >= 5 else 1,   # 🔮 a PROVEN model calls it up ≥ 5%: first
                                            0 if rs._fuse._f(c_.get('size')) >= 0.75 else 1,   # 🛡 the Warden's full-size picks first — the one desk whose call separates winners (−2.6 vs −4.9 typical, 187 real trades)
                                            rs._seat.germ_rank(rs._opp.germ_d(c_.get('chart') or {})[0], rs._uni.germ_max()),   # SKIP, no losing read, no young coin with an unread launch — germ floor first, like the models' list
                                            -sum(rs._oe.SETUP_SCORE.get(k_, 0) for k_ in c_.get('setups') or ()), -rs._fuse._f(c_.get('rank'))))
            for c_ in valid_:
                c_.update(tier='A', opp=c_['rank'], nearReady=f"⚡ {c_['kwhy']} · rank {c_['rank']:g} · size ×{c_['size']:g}")
            cases_ = rs._tk.KERNEL.cases(exclude={l.get('mint') for l in cur.get('legs') or []})
            cooled_ = [c_ for c_ in cases_ if c_['cleared'] and c_['mint'] in blk_]   # READY, but it left the card lately / the keeper refused it: the rebuy block holds it
            moved_, live_ = [], {}
            try:   # 👁 the LIVE chart for every held coin + the READY coins (one batched local call) and what a live breakout is measured from
                cand_ = valid_[:max(6, pol_['seats'] + 2)] + [c_ for c_ in (rs._tk.KERNEL.candidate(x_['mint']) for x_ in cases_ if x_['status'] == 'CONTENDING') if c_][:6]
                held_p = {l.get('mint'): l.get('pairAddress') for l in cur.get('legs') or [] if l.get('mint') and not l.get('placeholder')}
                if cand_ or held_p:
                    await rs._jup_prices([t_['mint'] for t_ in cand_] + list(held_p))
                    await rs._office_candle_refresh({**held_p, **{t_['mint']: t_['pair'] for t_ in cand_ if t_.get('pair')}}, now)
                    rs._office['watchC'] = {t_['mint']: {'sym': t_.get('symbol'), 'px': rs._fuse._f((rs._jup_px_cache.get(t_['mint']) or (0, 0))[1]) or rs._fuse._f(t_.get('px')),
                                                      'high': max([rs._fuse._f(r_[2]) for r_ in ((rs._office['candles'].get(t_['pair']) or (0, []))[1] or [])[-10:]] or [0])}
                                         for t_ in cand_ if t_.get('mint') and t_.get('pair')}   # ⚡ what a live breakout / material move is measured from
                rs._office['live'] = {'at': now, 'checked': []}
            except Exception as e:
                print('live refresh:', e)
            if empty_n and valid_ and not rs._office.get('validSince'):
                rs._office['validSince'] = now
            free_ = max(0.0, rs._fuse._f(cur.get('cash')) - rs._fuse._f(cur.get('holdCashUsd')))
            tk_ = rs._office.get('ticks') or []
            every_ = sorted(b_ - a_ for a_, b_ in zip(tk_, tk_[1:]))[len(tk_) // 2 - 1] if len(tk_) >= 3 else 50.0
            bk_ = ((rs._fw_peek().get('books') or {}).get(tid) or {}) if real_t else {}
            seat_ctx_ = {'want': pol_['seats'], 'held': held_n, 'cases': [c_ for c_ in cases_ if c_ not in cooled_ and c_['status'] != 'TRACKING'], 'valid': valid_, 'movesLeft': rs._uni.FILL_MOVES_HR - used_, 'movesHr': rs._uni.FILL_MOVES_HR, 'courier': (rs._office.get('courier') or {}).get('health'),
                         'manual': pol_['manual'], 'live': rd_['live'], 'readyWhy': rd_['why'], 'freeUsd': free_, 'minUsd': max(0.05, rs._fuse._f(cfg_t.get('minOrderUsd'))), 'emptySince': cur.get('agentEmptyAt'), 'target': pol_['seatTarget'], 'now': now, 'nextTickIn': min(every_, pol_['seatTarget']),
                         'control': True, 'halt': (bk_.get('haltWhy') or 'halted') if bk_.get('halt') else None, 'cooled': [c_.get('symbol') for c_ in cooled_], 'moved': moved_, 'timerIn': 0}
            vetoed_ = 0
            # the money boundary for a fill: the creator not on manual · the office LIVE · the keeper not halted · Courier not BAD · the runaway guard
            plan_ = valid_[:empty_n + 3] if (empty_n and not pol_['manual'] and rd_['live'] and not seat_ctx_['halt'] and seat_ctx_['courier'] != 'BAD' and used_ < rs._uni.FILL_MOVES_HR) else []
            rs._fw.set_agent_limits(rs._regret_limits(cfg_t))   # 😴 tuned by the regret ledger where the owner left AGENTS · 🎛 the owner's price-gap / sell-back / pool-floor / curve limits for agent buys: the pre-check and the keeper read the same ones
            if plan_ is not None and pol_.get('entry') == 'armed' and empty_n and not pol_['manual'] and rd_['live'] and not seat_ctx_['halt'] and seat_ctx_['courier'] != 'BAD' and used_ < rs._uni.FILL_MOVES_HR:
                # 🎯 KEEP SEATS FULL (the owner's entry mode): a seat empty past the owner's target with too few READY coins takes the best ARMED
                # coins (Trigger: "building, not yet") at HALF a seat — never a WAIT / NO coin, never a hard veto, never a blocked one
                try:
                    arm_ = rs._oe.armed_fill([c_ for c_ in (rs._tk.KERNEL.candidate(x_['mint']) for x_ in cases_ if x_['status'] == 'CONTENDING') if c_ and not rs._fw.dollar_named(c_.get('symbol')) and rs._agent_entry_ok(c_)],
                                          cur.get('agentEmptyAt'), pol_['seatTarget'], now, len(valid_), empty_n, blk_)
                    for c_ in arm_:
                        c_.update(tier='C', opp=c_['rank'], armed=True, nearReady=f"🎯 ARMED · {c_['kwhy']} · rank {c_['rank']:g} — your seat target passed, half a seat")
                    plan_ = plan_ + arm_
                    rs._office['armed'] = {'at': now, 'n': len(arm_), 'syms': [c_.get('symbol') for c_ in arm_]}
                except Exception as e:
                    print('armed fill:', str(e)[:120])
            if not plan_ and empty_n and not pol_['manual'] and rd_['live'] and not seat_ctx_['halt'] and seat_ctx_['courier'] != 'BAD' and used_ < rs._uni.FILL_MOVES_HR and cfg_t.get('agentValve', True):
                # 🪫 THE PATIENCE VALVE: an empty seat never sits all morning — after 10 min with nothing READY or armed, ONE chart-held coin
                # (wait for confirmation / breakout only) at the smallest seat, once per 15 min; it closes itself when its own record loses
                try:
                    vrec_ = rs._oe.valve_record(rs._real_trades())
                    v_ = rs._oe.valve_fill([c_ for c_ in (rs._tk.KERNEL.candidate(x_['mint']) for x_ in cases_ if x_['status'] == 'CONTENDING') if c_ and not rs._fw.dollar_named(c_.get('symbol')) and rs._agent_entry_ok(c_)],
                                        cur.get('agentEmptyAt'), now, cur.get('agentValveAt'), blk_, vrec_)
                    for c_ in v_:
                        c_.update(tier='C', opp=c_['rank'], armed=True, valve=True, size=min(rs._fuse._f(c_.get('size')) or 1, rs._oe.VALVE_SIZE),
                                  nearReady=f"🪫 VALVE · seat empty {int((now - rs._fuse._f(cur.get('agentEmptyAt'))) // 60)} min · the chart said {c_.get('chartCall', '').lower()} · smallest seat")
                    if v_:
                        cur['agentValveAt'] = now
                    plan_ = plan_ + v_
                    rs._office['valve'] = {'at': now, 'n': len(v_), 'syms': [c_.get('symbol') for c_ in v_], 'record': vrec_}
                except Exception as e:
                    print('valve fill:', str(e)[:120])
            cw_ = rs._ccl.wait_why(now, {'candleClock': cfg_t.get('candleClock', True) is not False and rs._rg.effective(cfg_t, rs._regret_book()).get('candleClock', True) is not False})
            if plan_ and cw_:   # ⏱ THE CANDLE CLOCK: no new buy in the first 100s of a 5-minute candle (record: worse in both halves, rugs left out)
                rs._office['flowWait'] = {'at': now, 'rows': [{'symbol': t_.get('symbol'), 'why': cw_} for t_ in plan_[:6]]}
                for t_ in plan_[:3]:
                    rs._regret_note(t_['mint'], 'clock:EARLY', rs._fuse._f(t_.get('px')), t_.get('symbol'))
                plan_ = []
            if plan_:   # 🌊 THE TAPE DECIDES THE MOMENT: each coin about to take a seat is read on its last 90s of real swaps — never into sellers, never at the top of a spike; a crowd buying goes first
                try:
                    fl_ = await rs._flow_fetch([t_.get('pair') for t_ in plan_ if t_.get('pair')])
                    keep_, waits_ = [], []
                    for t_ in plan_:
                        v_ = rs._flow.vital(fl_.get(t_.get('pair')))
                        if v_:
                            rs._flow_mark(t_['mint'], v_, t_.get('symbol'), now)
                        why_ = rs._flow.vital_block(v_)
                        wt_ = rs._rg.effective(cfg_t, rs._regret_book())
                        if why_ and not wt_.get({'PEAK': 'peakWait', 'SELLERS': 'sellersWait'}.get((v_ or {}).get('state'), ''), True):
                            why_ = None   # 😴 this tape wait was switched off by the regret ledger: the coins it held back kept beating the ones taken
                        if why_:
                            rs._regret_note(t_['mint'], f"flow:{v_.get('state')}", rs._fuse._f(t_.get('px')), t_.get('symbol'))
                            waits_.append({'symbol': t_.get('symbol'), 'why': why_})
                            rs._tk.KERNEL.note('trigger', 'WAIT', f"the tape says wait — {why_}", now, mint=t_['mint'], key=f"flow:{int(now // 120)}")
                            continue
                        wm_ = None
                        tr_w = rs._flow_trades.get(t_.get('pair'))
                        if tr_w and now - tr_w[0] < 30:   # 🐋 what the snipers / bundles / dev / top holders / whales / top traders did in the last 5 min
                            wm_ = rs._cw.moves_since(rs._cw.tag_trades(tr_w[1], (rs._intel_cache.get(t_['mint']) or (0, None))[1] or {}), now - 300)
                        if wm_ and not t_.get('g4') and rs._fuse._f(wm_['badSell']) >= rs._of.REAP_BAD_USD and rs._fuse._f(wm_['badSell']) > 2 * rs._fuse._f(wm_['badBuy']):
                            why_w = f"early hands are dumping it right now — {wm_['words']}: watch, then move"
                            rs._regret_note(t_['mint'], 'wallets:DUMP', rs._fuse._f(t_.get('px')), t_.get('symbol'))   # 😴 graded like every wait: the regret ledger says if it was right
                            waits_.append({'symbol': t_.get('symbol'), 'why': why_w})
                            rs._tk.KERNEL.note('trigger', 'WAIT', why_w, now, mint=t_['mint'], key=f"wal:{int(now // 120)}")
                            continue
                        smart_ = bool(wm_ and rs._fuse._f(wm_['smartBuy']) >= rs._of.REAP_SMART_USD and rs._fuse._f(wm_['smartBuy']) > rs._fuse._f(wm_['smartSell']))
                        sus_ = any(((n_ or {}).get('advice') or {}).get('stance') == 'CAUTION' for n_ in (rs._ai['notes'].get(t_['mint']) or {}).values())   # 🧠 SECOND LOOK: the rug-sniffer already flagged this coin → it goes behind the ones it did not (no call made here, never a block)
                        keep_.append(((0 if v_ and v_.get('state') == 'BUYERS' and v_.get('hot') else 1 if v_ and v_.get('state') == 'BUYERS' else 2) + (3 if sus_ else 0) - (1 if smart_ else 0), t_))   # 🐋 smart money buying it goes first
                    plan_ = [t_ for _g, t_ in sorted(keep_, key=lambda kv: kv[0])]
                    rs._office['flowWait'] = {'at': now, 'rows': waits_[:6]}
                except Exception as e:
                    print('flow gate:', str(e)[:120])
            rs._office['open'] = {'at': now, 'read': len(rs._tk.KERNEL.store.mints), 'ranked': len(valid_), 'top': [{'symbol': c_['symbol'], 'score': c_['rank'], 'narrative': c_['narrative']} for c_ in valid_[:8]],
                               'skipped': rs._tk.KERNEL.metrics(now)['byStatus']}
            rs._office['opp'] = {'at': now, 'cap': rs._agents.get('laneCap'), 'top': [{'symbol': c_['symbol'], 'tier': c_['status'], 'score': c_['rank']} for c_ in cases_[:6]]}
            if plan_ and real_t and empty_n > 0 and not cfg_t.get('agentPaper'):   # 🛂 the model's read BEFORE the seat (cloud only, ≤ 7s; it can only hold a coin back)
                try:
                    plan_, aiw_ = await rs._ai_gate(plan_, empty_n, cfg_t, now)
                    if aiw_:
                        rs._office['flowWait'] = {'at': now, 'rows': (list((rs._office.get('flowWait') or {}).get('rows') or []) + aiw_)[:6]}
                except Exception as e:
                    print('ai gate:', str(e)[:120])
            if cfg_t.get('agentPaper'):   # 📄 PAPER: every seat the kernel would fill is recorded in the shadow book at the live price — no real buy
                for t_ in plan_[:max(0, empty_n)]:
                    rs._shadow_note(t_, 'fill', now, cur)
                rs._shadow_controls(plan_[:max(0, empty_n)], [c_['row'] for c_ in cases_ if c_['status'] == 'CONTENDING'][:12], cases_, now)
                plan_ = []
            night_g4_ = night_ and ((rs._night.get('st') or {}).get('kind') == 'rug')   # 🔁 the AI seat is ONE trade at a time: only a rug-level trip pauses it (owner: "REAL seat"); drawdown / streak pauses stop the agents' fills only
            try:   # 🤝 the agents STRONGLY consider OSSY / G4 (owner, 2026-10-17): a coin a model called BUY in the last 10 min goes first into an open agent seat (every check still runs); a coin a model just said SELL / warned on is skipped
                dl_ = (rs._g4_mem.get() or {}).get('log') or []
                dpk_ = [r_.get('mint') for r_ in reversed(dl_) if r_.get('action') == 'BUY' and r_.get('mint') and now - rs._fuse._f(r_.get('at')) < 600]
                dwn_ = {r_.get('mint') for r_ in dl_ if r_.get('mint') and now - rs._fuse._f(r_.get('at')) < 900 and (r_.get('action') == 'SELL' or r_.get('view') == 'SELL')}
                if plan_:
                    plan_ = sorted([t_ for t_ in plan_ if t_['mint'] not in dwn_], key=lambda t_: dpk_.index(t_['mint']) if t_['mint'] in dpk_ else 99)
                    for t_ in plan_:
                        if t_['mint'] in dpk_ and '🤝' not in str(t_.get('nearReady') or ''):
                            t_['nearReady'] = '🤝 the models picked it · ' + str(t_.get('nearReady') or '')
                        elif t_.get('duoWhy') and '🤝' not in str(t_.get('nearReady') or ''):
                            t_['nearReady'] = f"🤝 {t_['duoWhy']} · " + str(t_.get('nearReady') or '')
            except Exception as e:
                print('duo consider:', str(e)[:80])
            w_, g4n_ = rs._g4.get('want'), 0   # 🔁 the AI seat is REAL even while the agents' own fills are on paper (owner, 2026-10-16); the night guard still stops it
            if w_ and w_.get('action') == 'BUY':   # 🧾 say WHY a model's BUY did not reach the card (it used to vanish silently)
                why_no = ('stale (older than 2 min)' if not rs._seat.fresh(w_, now) else 'seat off / not real' if not g4_seat_ else '🌙 night guard: a rug-level trip pauses the AI seat too' if night_g4_
                          else 'manual authority' if pol_['manual'] else 'office not LIVE yet' if not rd_['live'] else 'keeper halted' if seat_ctx_['halt']
                          else 'courier BAD' if seat_ctx_['courier'] == 'BAD' else 'hourly fill guard' if used_ >= rs._uni.FILL_MOVES_HR
                          else 'refused: ' + str((rs._agent_refused.get(w_.get('mint')) or (0, 'your own rule / a lesson / the keeper bench'))[1])[:100] if w_.get('mint') in rs._g4_blocked(cur, now) else None)
                if why_no:
                    rs._g4_fate(w_, why_no, now)
            if (g4_seat_ and w_ and w_.get('action') == 'BUY' and rs._seat.fresh(w_, now) and not night_g4_ and not pol_['manual'] and rd_['live'] and not seat_ctx_['halt']
                    and seat_ctx_['courier'] != 'BAD' and used_ < rs._uni.FILL_MOVES_HR and w_.get('mint') not in rs._g4_blocked(cur, now)):
                rs._g4['want'], rs._g4['pendSeat'] = None, {**w_}   # (kept until the save: an owner edit mid-tick drops this tick → the BUY is retried, never lost)
                lg_ = rs._seat.adoptable(cur.get('legs'), w_['mint'])
                if lg_ is not None:   # 🤝 the agents bought this very coin while the model thought ($onboard, 2026-10-17): the model ADOPTS that seat — no second buy, it is the model's trade now
                    lg_.update(aiSeat=True, aiBy=w_.get('by'), bought={**(lg_.get('bought') or {}), 'tag': '🤖 🧠 G4 seat'}, **{k_: v_ for k_, v_ in (('aiTp', w_.get('tp')), ('aiSl', w_.get('sl'))) if v_})
                    cur.setdefault('events', []).append({'at': now, 'kind': 'agent', 'symbol': lg_.get('symbol'), 'why': f"🤝 {w_.get('model') or 'the model'} took over the agents' seat on ${lg_.get('symbol')} — its trade now, no second buy"})
                    m0_ = rs._g4_mem.get() or {}
                    rs._g4_mem.put({**m0_, 'opener': w_.get('by'), 'opened': {**{k_: v_ for k_, v_ in (m0_.get('opened') or {}).items() if now - rs._fuse._f(v_) < 3600}, w_['mint']: now}}, now)
                    rs._g4['pendSeat'] = {**w_, 'seated': True}
                    rs._g4_fate(w_, 'adopted the agents\' seat on this coin — the model runs it now', now)
                    w_ = None
                gt_ = rs._tk.KERNEL.candidate(w_['mint']) if w_ else None
                bad_ = rs._g4_bad_entry(gt_) if gt_ else None
                if bad_:   # 🔫 the coin ran to its gun line while the model thought: no buy, it picks again next minute
                    rs._g4_fate(w_, 'not bought — ' + str(bad_)[:90], now)
                    gt_ = None
                elif gt_ and rs._g4_picks_only() and not gt_.get('pick'):   # 🧪 picks only — the HARD stop: a coin that is not a proven pick right now is never bought by the seat
                    rs._g4_fate(w_, '🧪 picks only: not a proven-rule pick right now — no buy', now)
                    gt_ = None
                if gt_ and gt_.get('pair'):
                    plan_, g4n_ = [{**gt_, 'g4': True, 'g4By': w_.get('by'), 'g4Tp': w_.get('tp'), 'g4Sl': w_.get('sl'), 'nearReady': f"🧠 {w_.get('model') or 'G4'}: {w_.get('why')}"}] + [t_ for t_ in plan_ if t_['mint'] != gt_['mint']], 1
                    rs._g4_fate(w_, 'sent to the seat check', now)
                elif not bad_ and w_:
                    rs._g4_fate(w_, 'coin left the desk before the buy', now)
            if cfg_t.get('deskBuysOff'):   # ⚖ the last door: nothing on the plan reaches the card but the coin a Sicario's PoW asked for
                plan_ = rs._seat.desk_off_plan(plan_, sic_want_); g4n_ = len(plan_)
            pre_ = await rs._seat_precheck(plan_[:empty_n + 3 + g4n_], cfg_t, now, seat_usd=rs._prime.agent_seat_usd(cur, px, cfg_s), need=empty_n + g4n_) if (plan_ and real_t) else None   # 🛂 the keeper's market gate BEFORE the seat
            rs._office['pre'] = {'at': now, 'asked': len(plan_), 'passed': len(pre_) if pre_ is not None else None,
                              'refused': [{'symbol': t_.get('symbol'), 'why': rs._agent_refused[t_['mint']][1]} for t_ in plan_ if pre_ is not None and t_['mint'] in rs._agent_refused][:6]}
            ag_fill_ = 0
            for t_ in plan_:   # 🔌 no fill until the office is LIVE after a restart · never while the keeper is halted or the Courier reads BAD
                t_ = {**t_, 'trench': rs._uni.in_lane(t_.get('vitals') or {})}   # 🗑 a lane launch → the keeper's trench pool floor
                if used_ >= rs._uni.FILL_MOVES_HR:
                    break
                if g4_seat_ and not t_.get('g4') and ag_fill_ >= empty_n:   # 🧠 one empty seat stays G4's while its seat is on
                    break
                if t_['mint'] in (rs._g4_blocked(cur, now) if t_.get('g4') else rs._agent_blocked(cur, now)):   # 🚫 banked / pulled / refused earlier in THIS tick (OSSY / G4: only the keeper's and your own blocks)
                    if t_.get('g4'):   # 🧾 never silent: the board said "sent to the seat check" for good while the refusal sat here
                        rs._g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'keeper refused: ' + str((rs._agent_refused.get(t_['mint']) or (0, 'blocked by your rule / keeper bench'))[1])[:90] + ' — the model picks again next minute', now)
                    continue
                if pre_ is not None:
                    if t_['mint'] not in pre_:   # 🛂 the keeper would refuse it: no seat, the next READY coin is tried
                        if t_.get('g4'):
                            rs._g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'keeper pre-check refused: ' + str((rs._agent_refused.get(t_['mint']) or (0, 'busy route'))[1])[:80], now)
                        continue
                    lv_ = pre_[t_['mint']]
                    if not t_.get('g4') and rs._fuse._f(lv_.get('px')) > 0 and rs._fuse._f(t_.get('px')) > 0 and rs._fuse._f(lv_['px']) >= rs._fuse._f(t_['px']) * (1 + rs.SPIKED_SINCE_READ / 100):
                        rs._agent_refused[t_['mint']] = (now + 120, f"jumped {(rs._fuse._f(lv_['px']) / rs._fuse._f(t_['px']) - 1) * 100:.0f}% since the agents read it — waits for the pullback", now)
                        continue   # 🚀 it spiked between the read and the buy: no chasing the candle that just printed
                    t_ = {**t_, 'px': lv_.get('px') or t_['px'], 'nums': {**(t_.get('nums') or {}), 'liq': lv_.get('liq') or (t_.get('nums') or {}).get('liq')}}
                try:
                    wd_ = rs._office_warden(cur, t_, rs._prime.agent_seat_usd(cur, px, cfg_s), cfg_t, now, 'fill')   # 🛡 sizes THIS seat: it can lower or veto, never raise
                    if t_.get('g4') and wd_['veto']:   # 🧼 owner 2026-10-28 ("G4 buys washed coins, not listening"): the models obey every Warden VETO
                        rs._g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'Warden VETO (models obey vetoes): ' + str(wd_.get('decided') or '')[:60], now)
                        vetoed_ += 1
                        continue
                    if t_.get('g4'):   # 🔁 OSSY / G4's turn is THEIR call (owner, 2026-10-16: "the agents can't stop them, they use the agents as helpers"): the Warden's word is advice, the seat is the card's full seat; the keeper's own money checks still run
                        if wd_['veto'] or wd_['allowed'] < rs._prime.agent_seat_usd(cur, px, cfg_s):
                            rs._g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'Warden advised: ' + str(wd_.get('why') or wd_.get('rules') or 'smaller')[:70] + ' — the model\'s call stands', now)
                        wd_ = {**wd_, 'veto': False, 'allowed': rs._prime.agent_seat_usd(cur, px, cfg_s)}
                    if wd_['veto']:
                        vetoed_ += 1
                        if t_.get('g4'):
                            rs._g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'Warden vetoed: ' + str(wd_.get('why') or wd_.get('rules') or '')[:80], now)
                        continue
                    cur = rs._prime.agent_seat(cur, {'mint': t_['mint'], 'symbol': t_['symbol'], 'pairAddress': t_['pair'], 'price': t_['px'], 'liquidityUsd': (t_.get('nums') or {}).get('liq'), 'trench': t_['trench'], 'curve': bool((t_.get('vitals') or {}).get('curve') and cfg_t.get('agentCurve')),
                                                  'ageH': (t_.get('vitals') or {}).get('ageH'), 'vol1h': (t_.get('vitals') or {}).get('vol1h'), 'buyShare': (t_.get('nums') or {}).get('buy'),
                                                  'riskScale': wd_.get('riskScale'),
                                                  'tag': '🤖 agents · ⚡ READY (kernel)' if not t_.get('armed') else '🤖 agents · 🪫 VALVE (empty seat)' if t_.get('valve') else '🤖 agents · 🎯 ARMED (seat target)', 'why': t_['nearReady']}, px, cfg_s, now,
                                          max_usd=wd_['allowed'] * (rs._oe.VALVE_SIZE if t_.get('valve') else rs._cap.armed_size(rs._capital_view()) if t_.get('armed') else 1.0))   # 🎯 an armed fill: half — the full size once the ARMED door's own real record proves it
                    used_ += 1; cur['agentDutyAt'] = now; cur['agentFillAt'] = now
                    if not t_.get('g4') and rs._DUO_GATE['on']:   # 🤝 the agents trade a model-backed coin on THAT model's own lines (R6m / R5m / R7a)
                        bl_ = rs._seat.backer_lines((rs._g4_mem.get() or {}).get('log') or [], t_['mint'], now)
                        for l_ in (cur.get('legs') or []) if bl_ else []:
                            if l_.get('mint') == t_['mint'] and not l_.get('aiSeat') and not l_.get('picked'):
                                l_.update({k2_: v2_ for k2_, v2_ in (('aiTp', bl_.get('tp')), ('aiSl', bl_.get('sl')), ('aiTrail', bl_.get('trail'))) if v2_}); l_['linesBy'] = bl_.get('by')
                    if t_.get('g4'):   # 🧠 the leg is G4's: the agents only argue on it from now on
                        rs._g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'seated — the keeper buys it next pass', now)
                        if (rs._g4.get('pendSeat') or {}).get('mint') == t_['mint']:
                            rs._g4['pendSeat']['seated'] = True
                        for l in cur['legs']:
                            if l.get('mint') == t_['mint']:
                                l['aiSeat'] = True
                                l['aiBy'] = t_.get('g4By')   # 🔁 whose trade this is: the turn moves only on a seat that really opened
                                for k_, v_ in (('aiTp', t_.get('g4Tp')), ('aiSl', t_.get('g4Sl'))):
                                    if v_:
                                        l[k_] = v_
                                l['bought'] = {**(l.get('bought') or {}), 'tag': '🤖 🧠 G4 seat'}
                        try:
                            m0_ = rs._g4_mem.get() or {}
                            m0_ = {**m0_, 'opened': {**{k_: v_ for k_, v_ in (m0_.get('opened') or {}).items() if now - rs._fuse._f(v_) < 3600}, t_['mint']: now}}   # 🚫 neither model buys this coin again for 1h
                            if not m0_.get('statsFrom'):   # 🔁 the first time a model's BUY really takes the seat, the duel board's stats restart from real play (owner, 2026-10-16)
                                m0_ = {**m0_, 'log': [], 'statsFrom': now}
                            rs._g4_mem.put({**m0_, 'opener': t_.get('g4By')}, now)
                        except Exception as e:
                            print('g4 opener:', str(e)[:80])
                        g4_seat_ = False
                    else:
                        ag_fill_ += 1
                    rs._ai.setdefault('fillQ', {})[t_['mint']] = now
                    rs._regret_note(t_['mint'], 'taken', rs._fuse._f(t_.get('px')), t_.get('symbol'))   # 😴 the baseline every blocked coin is graded against   # 📍 the model reads this coin once more AT the fill (record only — it never undoes a buy)
                    try:   # 📏 decision → order · discovery → entry · the coin's age at entry
                        K_ = rs._tk.KERNEL
                        K_.timings.note('readyToSeatSec', now - rs._fuse._f((K_.store.cand.get(t_['mint']) or {}).get('since') or now))
                        K_.timings.note('discoveryToEntrySec', now - rs._fuse._f(K_.store.stats['firstSeen'].get(t_['mint']) or now))
                        K_.timings.note('ageAtEntryMin', None if (t_.get('vitals') or {}).get('ageH') is None else rs._fuse._f(t_['vitals']['ageH']) * 60)
                        K_.store.set_status(t_['mint'], 'ORDER_PENDING', now, 'seat created — the keeper buys it')
                    except Exception as e:
                        print('timings:', e)
                    rs._intake['reg'] = rs._in.stamp(rs._intake_reg(), 'seat', [t_['mint']], now)   # 🕸 clear → seat latency
                    st_o = rs._office_state()   # ⏱ how long the seat sat empty, how long a valid candidate waited, how long after an exit the next fill came
                    sp_ = st_o.get('speed') or {}
                    if cur.get('agentEmptyAt'):
                        sp_ = rs._oe.speed_note(sp_, 'seatEmpty', now - rs._fuse._f(cur['agentEmptyAt']))
                    if rs._office.get('validSince'):
                        sp_ = rs._oe.speed_note(sp_, 'validToFill', now - rs._fuse._f(rs._office['validSince']))
                    if cur.get('agentExitAt'):
                        sp_ = rs._oe.speed_note(sp_, 'exitToFill', now - rs._fuse._f(cur['agentExitAt']))
                    st_o['speed'] = sp_
                    cur.pop('agentExitAt', None); cur.pop('agentEmptyAt', None); rs._office.pop('validSince', None)
                except ValueError as e_:
                    if t_.get('g4'):   # 🧾 the model's BUY used to vanish here (no free cash / no seat) — say why, and make room when cash is the reason
                        why_ = str(e_)
                        if 'free' in why_:
                            try:
                                cur, got_, ts_ = rs._prime.make_room(cur, rs._prime.agent_seat_usd(cur, px, cfg_s), px, None, now, pol_['seats'], t_.get('g4By') and str(t_.get('g4By')).upper() or 'the model')
                            except Exception as e2_:
                                got_, ts_ = 0.0, None
                                print('g4 make room:', str(e2_)[:80])
                            if got_ > 0:
                                why_ += f' — trimmed ${got_:.2f} of ${ts_} to pay it; the seat fills next tick'
                                if rs._g4.get('pendSeat'):
                                    rs._g4['want'] = {**rs._g4['pendSeat'], 'at': now}
                        rs._g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'not seated — ' + why_[:140], now)
                        continue
                    break
            held_n = len([l for l in cur.get('legs') or [] if not l.get('placeholder')])   # 🪑 the seat truth AFTER this tick's fills
            rs._agents['seat'] = {**rs._oe.seat_state({**seat_ctx_, 'held': held_n, 'vetoed': vetoed_, 'valid': [t_ for t_ in valid_ if t_['mint'] not in {l.get('mint') for l in cur.get('legs') or []}] if held_n < pol_['seats'] else valid_}),
                               'at': now, 'tickEvery': round(every_, 1), 'movesLeft': max(0, rs._uni.FILL_MOVES_HR - used_), 'freeUsd': round(max(0.0, rs._fuse._f(cur.get('cash')) - rs._fuse._f(cur.get('holdCashUsd'))), 2),
                               'refused': rs._seat_refusals(tid, now) if real_t else []}
            rs._agents['card'] = rs._pos.card_seats(cur, rs._agents.get('decisions'), px, cfg_t, take=rs._of.take_line(cfg_t, rs._agents.get('scalp')))
            try:   # 🪑 THE BENCH + EVERY SEAT THIS CYCLE (display — the decisions above were made by manage / Reaper / fill_plan)
                on2_ = {l.get('mint') for l in cur.get('legs') or [] if l.get('mint')}
                bench_ = rs._so.bench(cases_, scores_, on2_, {m_: (v_['ok'], v_['why']) for m_, v_ in live_.items()}, [c_['mint'] for c_ in cooled_])
                inp_ = {l.get('mint'): rs._mkt_view(l.get('mint'), l.get('pairAddress'), now).get('pxAt') for l in cur.get('legs') or [] if l.get('mint')}
                rs._agents['bench'] = bench_
                rs._agents['seatBoard'] = rs._so.seat_board((rs._agents['card'] or {}).get('seats'), rs._office.get('reports'), rs._agents.get('decisions'), vels_, scores_, bench_,
                                                      rs._agents.get('switchTests'), now, now, inp_, rs._agents.get('seat'), pol_['switch'].get('mode'))
                rs._agents['seatSummary'] = {**rs._so.summary(held_n, pol_['seats'], bench_, used_, rs._uni.FILL_MOVES_HR, max(0.0, rs._fuse._f(cur.get('cash')) - rs._fuse._f(cur.get('holdCashUsd')))),
                                          'hunt': list(rs._so.universe(rs._agents.get('money')))}   # 🧭 what the seats hunt in this phase
                rs._agents['seatScores'] = {m_: v_ for m_, v_ in scores_.items() if m_ in on2_ or m_ in {b_['mint'] for b_ in bench_}}
                bs_ = rs._so.bench_stats(bench_, (rs._agents.get('benchStats') or {}).get('mints'))
                rs._agents['benchStats'] = bs_
                st_u = rs._office_state(); st_u['util'] = rs._so.util_note(st_u.get('util'), rs._agents['seatBoard'], now)   # ⏱ seat time: occupied · empty (waiting · safety · budget · cash)
                rs._agents['util'] = rs._so.util_view(st_u['util'])
            except Exception as e:
                print('seat board:', e)
            rs._office['tickAt'] = now
        elif real_t and cur and pol_:   # 🪑 Agent Control OFF (or a hold the owner set): the seats still say why the agents fill nothing
            rs._agents['seat'] = {**rs._oe.seat_state({'want': pol_['seats'], 'held': len([l for l in cur.get('legs') or [] if not (l.get('placeholder') and not l.get('manualCash'))]), 'now': now, 'control': False,
                                                 'offWhy': None if not cfg_t.get('agentControl') else ('the card is floored — it re-deals before the agents act' if cur.get('flooredAt') else 'your own ✋ hold stands — nobody trades until you release it')}),
                               'at': now, 'movesLeft': 0, 'freeUsd': round(max(0.0, rs._fuse._f(cur.get('cash')) - rs._fuse._f(cur.get('holdCashUsd'))), 2)}
        if real_t and cur:
            rs._office_light(tid, cur, now)   # 🏢 the office's live bits (positions · last real action · duty clock) — memory only
        # 🔥 TOP-3 AUTO SEAT (owner, 2026-10-09: "those coins automatically get swapped into a seat and buy-vs-sell gets it gone"): the
        # card's TOP 1/3 coin takes the weakest seat that is not winning, one per 10 min — still the real-buy pool floor, no dollar names,
        # not falling right now; the flow exit sells it when sellers take over.
        if real_t and cur and cfg_t.get('topSeat') and not cur.get('holdAll') and not cur.get('flooredAt') and now - rs._fuse._f(cur.get('topSeatAt')) >= rs._prime.TOP_SEAT_SEC:
            tops_ = rs._prime.top_three((rs._contenders_cache.get('data') or {}).get('divisions'), mine, cool)
            fwc_ = rs._fw.clean_cfg(fw_cfg)
            cand_ = next((x for x in tops_ if _lq(x) >= fwc_['minLiqUsd'] and not rs._fw.dollar_named(x.get('symbol')) and rs._fuse._f(x.get('price')) > 0
                          and rs._prime.entry_ok(x, mom) and not (cfg_t.get('entryGate') and rs._prime.entry_gate(x, mom))), None)
            vic_ = rs._prime.top_victim(cur, px, now, max(120.0, rs._fuse._f(cfg_t.get('minHoldMins')) * 60)) if cand_ else None
            if cand_ and vic_:
                try:
                    was_ = cur
                    nw_ = rs._prime.replace_leg(cur, vic_['pairAddress'], px, p_t, [{**cand_, 'tag': '🔥 top 3'}], anchors, cfg_t, now)
                    nw_['events'] = nw_['events'][:-1] + [{**nw_['events'][-1], 'why': f"🔥 TOP 3 auto-seat: ${cand_.get('symbol')} (${rs._fuse._f(cand_.get('vol1h')) / 1000:,.0f}K/h, {rs._fuse._f(cand_.get('chg1h')):+.0f}% 1h) took ${vic_.get('symbol')}'s seat"}]
                    nw_['topSeatAt'] = now
                    cur = rs._prime.note_dropped(was_, nw_, now, cfg_t['rotateHours'], px)
                except ValueError:
                    pass
        true_usd = None
        if real_t:   # 💵 floor / rescue / fix / runs judge the TRUE book (confirmed coins + card SOL), never the engine's estimate
            bk = (rs._fw_peek().get('books') or {}).get(tid)
            try:
                sol_px_t = await rs._sol_usd_live() if bk else 0.0
            except Exception:
                sol_px_t = 0.0
            if bk and sol_px_t > 0 and not bk.get('pending'):
                true_usd = rs._fw.book_value(bk, px, sol_px_t) or None
        if not real_t:   # 🦠 paper cards buy at the germ: coins inside the germ line first, past 2× it only when nothing else is left
            gd_ = lambda m_: (lambda g_: rs._fuse._f(g_['dist']) if g_ and g_.get('dist') is not None else None)((((rs._office.get('charts') or {}).get(m_) or {}).get('f') or {}).get('germ'))
            r_t = rs._prime.germ_order(r_t, gd_, rs._uni.germ_max())
        if not real_t:   # 🧪 UNIQUE COINS: a paper card never holds a coin another card holds (anchors too, while another major is free)
            taken_ = {l.get('mint') for t2, c2 in cards.items() if t2 != tid for l in (c2 or {}).get('legs') or [] if l.get('symbol') != 'SOL'}
            p_t, r_t = rs._prime.unique_rows(p_t, taken_), rs._prime.unique_rows(r_t, taken_)
            a_t = rs._prime.unique_rows(a_t, taken_) or a_t
            dup_ = rs._prime.shared_leg(cur, taken_) if cur and not cur.get('flooredAt') else None
            if dup_:   # a coin it already shares is swapped for one of its own (one a tick, on paper)
                try:
                    was_u = cur
                    new_u = rs._prime.replace_leg(cur, dup_, px, p_t, r_t, a_t, cfg_t, now)
                    old_m = {l.get('mint') for l in was_u.get('legs') or []}
                    for l_ in new_u['legs']:
                        if l_.get('mint') not in old_m:
                            l_.pop('picked', None)   # the engine's swap, not a hand pick
                    new_u['events'][-1]['why'] = '🧪 unique coins — another card already holds it, this card takes one of its own'
                    new_u.pop('ownerOut', None) if not was_u.get('ownerOut') else None
                    cur = rs._prime.note_dropped(was_u, new_u, now, cfg_t['rotateHours'], px)
                except Exception:
                    cur = was_u
        for l_ in (cur or {}).get('legs') or []:   # 🧲 / 📣 what Pump's own feeds say about each coin the card holds (fed lock · second ticket)
            l_['fedN'] = int(((rs._feeders['board'].get('runners') or {}).get(l_.get('mint')) or {}).get('n') or 0)
            l_['calledN'] = int((rs._pump_calls['map'].get(l_.get('mint')) or {}).get('callers') or 0)
        if real_t and cfg_t.get('trenchSlAuto', True) and rs._fuse._f(cfg_t.get('trenchSlPct')) < 100:   # 🧠 tickets use the stop that paid best when the brain replayed every stop on the same paths
            bs_ = ((rs._brain_state()['sum'] or {}).get('stops') or {}).get('best')
            if bs_ is not None:
                cfg_t = {**cfg_t, 'ticketSl': bs_}
        cards[tid] = rs._prime.tick(cur, px, p_t, r_t, cfg_t, now, a_t, mom, liqs, true_usd=true_usd, blind=bool(real_t and true_usd is None)) if cur else rs._prime.deal(tid, p_t, r_t, cfg_t, now, [] if new_only_ else anchors)
        if cards[tid] is not None:
            cards[tid]['rebuyDip'] = int(cfg_t.get('rebuyDipPct') or 0)
        if not real_t and cards[tid] is not None:   # 🎯 no one strat fits every coin: each paper coin gets its OWN take / stop from its chart, once (no agent, no AI)
            t_l = rs._prime.card_template(cards[tid].get('tpl'), cfg_t)
            for l_ in cards[tid].get('legs') or []:
                if l_.get('autoLv') or l_.get('placeholder') or rs._fuse._f(l_.get('tp')) > 0 or rs._fuse._f(l_.get('sl')) > 0 or rs._prime.safe_anchor(l_):
                    continue
                ch_ = (rs._office.get('charts') or {}).get(l_.get('mint')) or {}
                ln_ = rs._prime.coin_lines(l_, t_l, ch_.get('f'), ch_.get('state'), {'liq': l_.get('liq'), 'ageH': l_.get('ageH')})
                if ln_:
                    l_.update(ln_, autoLv=round(now))
        cards[tid] = rs._prime.note_dropped(cur, cards[tid], now, cfg_t['rotateHours'], px)
        if real_t and cur and cards[tid]:   # 🧠 every coin that left the real card this tick is a lesson
            try:
                rs._learn_drops(cur, cards[tid], lambda l: rs._fuse._f(px.get(l.get('pairAddress'))), now)
            except Exception as e:
                print('real learn:', e)
        if real_t and cur and cards[tid] and cfg_t.get('comeback', True):   # 🔁 a rider that left this tick is watched for its comeback
            cards[tid]['comeback'] = rs._prime.comeback_note(cur.get('comeback'), cur, cards[tid], px, now)
        if real_t and cards[tid]:
            on_ = {l.get('mint') for l in cards[tid].get('legs') or []}
            free_ = [x for x in r_t if x.get('mint') not in on_ and not x.get('trenchOnly')]
            scout_ = [x for x in rs._prime.movers(r_pre_, {}) if x.get('mint') not in on_]
            row_ = lambda x: {'mint': x.get('mint'), 'pairAddress': x.get('pairAddress'), 'symbol': x.get('symbol'), 'chg1h': rs._fuse._f(x.get('chg1h')), 'vol1h': rs._fuse._f(x.get('vol1h')), 'tag': x.get('tag') or '',
                              'ageH': x.get('ageH'), 'liq': _lq(x), 'pad': x.get('pad'), 'mcap': x.get('mcap'), 'buyShare': x.get('buyShare'), 'top10': x.get('top10'), 'dev': x.get('dev'),
                              'insiders': x.get('insiders'), 'site': x.get('site'), 'x': x.get('x'), 'tg': x.get('tg'), 'chg5m': x.get('chg5m'),
                              'vol5m': x.get('vol5m'), 'txns1h': x.get('txns1h'), 'trench': x.get('trench'), 'trenchOnly': x.get('trenchOnly')}
            seen_u, up_ = set(), []
            for x in cfg_t.get('edgeReady') or []:   # 🧬 the best of the swap-in lists that this card would buy right now
                if x.get('mint') not in on_ and x['mint'] not in seen_u and len(up_) < 6:
                    seen_u.add(x['mint']); up_.append({**row_(x), 'cat': 'edge', 'tag': x.get('tag') or '', 'edge': x.get('edge')})
            rs._up_last = [(x['mint'], rs._fuse._f((x.get('price') or 0))) for x in (cfg_t.get('edgeReady') or [])[:4]]
            for x in cfg_t.get('edgeWatch') or []:   # 👀 then the best-evidence coins one check away, with that check
                if x.get('mint') and x['mint'] not in on_ and x['mint'] not in seen_u and len(up_) < 4:
                    seen_u.add(x['mint']); up_.append({**row_(x), 'tag': x.get('tag') or '', 'edge': x.get('edge'), 'wait': x.get('watchWhy')})
            doors_ = {x.get('cat'): x for x in (cfg_t.get('catPicks') or []) if x.get('cat') != 'edge'}
            for x in cfg_t.get('catWatch') or []:
                doors_.setdefault(x.get('cat'), x)
            for k_ in [c[0] for c in rs._prime.CATEGORIES]:   # ⏭ ONE coin per door in the owner's order (trench · pump · volume): ready, else watching with its reason
                x = doors_.get(k_)
                if x and x.get('mint') not in on_ and x['mint'] not in seen_u:
                    seen_u.add(x['mint']); up_.append({**row_(x), 'cat': x.get('cat'), 'catRank': x.get('catRank'), 'tag': x.get('tag') or '', **({'wait': x['watchWhy']} if x.get('watchWhy') else {})})
            for x in rs._prime.flow_rank(free_ + [y for y in scout_ if y.get('mint') not in {z.get('mint') for z in free_}]):   # ⏭ COMING UP: by what each coin looks like now (setup · chart), then hourly move
                if x.get('mint') and x['mint'] not in seen_u:
                    seen_u.add(x['mint']); up_.append(row_(x))
            # 👀 watching, DIPS FIRST: buy-bottom coins the 30s seat fallback may take, then coins waiting on their chart; a coin that
            # already ran (at its highs / too far / too hot / too wild) goes LAST — the owner: "next up giving stuff that peaked"
            for x in (cfg_t.get('seatFallback') or []):
                if x.get('bottomWhy') and x.get('mint') not in seen_u and x.get('mint') not in on_ and len(up_) < 6:
                    seen_u.add(x['mint']); up_.append({**row_(x), 'tag': '🟢 buy bottom', 'wait': f"dip — {x['bottomWhy']} · takes a seat that stays empty 30s"})
            peaked_ = lambda w: any(k in w for k in ('at its highs', 'too far', 'too hot', 'too wild'))
            wrows_ = [(x, rs._prime.meta_why(x) or 'not ready') for x in rs._prime.flow_rank([y for y in watch_ if y.get('mint') not in on_ and not y.get('trenchOnly')])]
            for x, w_ in sorted(wrows_, key=lambda t: peaked_(t[1])):
                if x.get('mint') and x['mint'] not in seen_u and len(up_) < 6:
                    seen_u.add(x['mint']); up_.append({**row_(x), 'wait': w_ + (' — already ran' if peaked_(w_) else '')})
            up_ = [y for y in up_ if not str(y.get('wait') or '').startswith(('failed safety', 'holder scan', 'not on the runner board'))]   # 🧹 a coin that failed safety is never "coming up"
            # 💀 never a dead coin under Coming up (a 0 on the row = not read, the runner board's numbers win)
            cards[tid]['pipeline'] = {'at': now, 'steps': fun_ + [['not on the card and not cooling', len(free_)]], 'up': [rs._up_vital(u_) for u_ in [y for y in up_ if not rs._ja.dead_why({**{k: v for k, v in y.items() if v not in (None, 0, 0.0)}, **(rs._cand_map().get(y.get('mint')) or {})})][:6]], 'catMiss': cfg_t.get('catMiss') or {},
                                      'next': [f"${x.get('symbol')} {rs._fuse._f(x.get('chg1h')):+.0f}%" for x in sorted(free_, key=lambda x: -rs._fuse._f(x.get('chg1h')))[:4]],
                                      'scout': [f"${x.get('symbol')} {rs._fuse._f(x.get('chg1h')):+.0f}%" for x in scout_[:4]],
                                      'best': [rs._up_vital({k: x.get(k) for k in ('mint', 'pairAddress', 'symbol', 'price', 'chg1h', 'chg5m', 'vol1h', 'liq', 'tag', 'tape', 'buyShare')})
                                               for x in (cfg_t.get('bangers') or [])[:3]]}
        taken |= {l.get('mint') for l in (cards[tid] or {}).get('legs') or [] if l.get('role') != 'anchor'}
    cards = {k: v for k, v in cards.items() if v}
    try:   # 📏 vs holding SOL: remember SOL's price when each run starts (a new run = a new startUsd)
        sol_now = await rs._sol_usd_live()
        for v in cards.values():
            if sol_now and v.get('solStartFor') != v.get('startUsd'):
                # a run already underway when first seen has no true SOL baseline → no comparison until its next run starts
                v['solLate'] = 'solStart' not in v
                v['solStart'], v['solStartFor'] = sol_now, v.get('startUsd')
    except Exception:
        pass
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        if rs._hq_ver() != ver_:   # the file was saved while this tick worked: the owner's pick / skim / lock on a card beats the tick
            cards = rs._prime.merge_tick(snap_, cards, (d.get('prime') or {}).get('cards') or {})
        ps_ = rs._g4.pop('pendSeat', None)
        if ps_ and ps_.get('seated') and not ps_.get('retried') and not any(l_.get('mint') == ps_.get('mint') and not l_.get('placeholder') for c_ in cards.values() if (c_ or {}).get('real') for l_ in c_.get('legs') or []):
            rs._g4['want'] = {**ps_, 'at': rs.time.time(), 'thinkAt': now, 'retried': True, 'seated': False}   # 🔁 your edit saved the card while this tick ran (it wins) → the model's seat is retried next tick, never silently lost
            rs._g4_fate(ps_, 'your edit saved the card at the same moment — retrying the seat next tick', now)
        rs._record_runs(before_runs, cards)
        try:
            cards = rs._paper_broke(d, cards, px, now)   # ♻ broke paper cards restart on a NEW config, the old one is scrapped
        except Exception as e:
            print('paper broke:', e)
        win = rs._prime.crown_round(cards)
        d.setdefault('prime', {})['cards'] = cards
        if any(c.get('real') for c in cards.values()) and not d['prime'].get('realCfg'):
            # 💵 the first time a card runs real money its config is FROZEN as its own — HQ / engine tunes on paper can't reach it after this
            d['prime']['realCfg'] = rs._prime.clean_cfg(d['prime'].get('cfg') or {})
            d['prime']['realCfg']['instantSwapPct'] = d['prime']['realCfg'].get('rotateMinDrop', 0)
        if win:
            d['prime']['roundWinner'] = {'id': win, 'at': now}
        rs._json_save(rs.FUSE_HQ_PATH, d)
    return len(cards)

