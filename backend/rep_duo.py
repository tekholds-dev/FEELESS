"""🧹 Duo tape, agents page, playground, verdicts — split out of rep_ai.py by scripts/split-module.py (owner 2026-11-17 cleanup); first moved whole out of reputation_service.py.
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


def _duo_tape():
    """(the models' archived positions, the trade tape built from the WHOLE ledger) — one build per 20s for the duo totals + rooms."""
    rs = _rs()
    if rs.time.time() - rs._duo_tape_c['at'] < 20:
        return rs._duo_tape_c['v']
    pos_ = [p_ for p_ in (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or [] if p_.get('g4')]
    led_ = list(rs._fw_full_ledger() or [])

    def _build():
        return (pos_, [r_ for r_ in rs._co.trade_tape(led_, pos_, n=400) if r_.get('who') == 'models'])
    if rs._duo_tape_c.get('v') is not None:   # ⚡ an old copy answers now; ONE rebuild runs in a worker thread (it held the loop ~3s)
        if not rs._duo_tape_c.get('busy'):
            rs._duo_tape_c['busy'] = True

            def _bg():
                try:
                    rs._duo_tape_c.update(at=rs.time.time(), v=_build())
                finally:
                    rs._duo_tape_c['busy'] = False
            rs.threading.Thread(target=_bg, daemon=True).start()
        return rs._duo_tape_c['v']
    v_ = _build()
    rs._duo_tape_c.update(at=rs.time.time(), v=v_)
    return v_


def _duo_totals():
    """💰 OSSY / G4 all-time REAL result: every closed AI-seat position from the LEDGER (every sale, trims included, against everything put in,
    top-ups included — the archive's % only knew the last sale), by the model that opened it."""
    rs = _rs()
    pos_, tape_ = rs._duo_tape()
    out = {}
    for row_ in tape_:
        if row_.get('who') != 'models' or row_.get('state') != 'sold' or not row_.get('result'):
            continue
        p_ = next((x_ for x_ in pos_ if x_.get('mint') == row_.get('mint') and abs(rs._fuse._f(x_.get('since')) - rs._fuse._f(row_.get('at'))) <= 900), None)
        k_ = rs._air.model_name(rs.os.environ, (p_ or {}).get('aiBy')) if (p_ or {}).get('aiBy') else '?'
        r_ = row_['result']
        t_ = out.setdefault(k_, {'n': 0, 'won': 0, 'usd': 0.0, 'pct': 0.0})
        t_['n'] += 1; t_['won'] += 1 if rs._fuse._f(r_.get('pct')) > 0 else 0; t_['usd'] = round(t_['usd'] + rs._fuse._f(r_.get('usd')), 3); t_['pct'] = round(t_['pct'] + rs._fuse._f(r_.get('pct')), 1)
    return out


def _duo_rooms(log, keep=8):
    """🗂 The rooms of the last model trades (newest first): coin, who bought, the real result when it closed, and that trade's own talk."""
    rs = _rs()
    res_ = {p_.get('mint'): p_ for p_ in (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or [] if p_.get('g4')}
    out, seen = [], set()
    for r_ in reversed(log or []):
        m_ = r_.get('mint')
        if r_.get('action') != 'BUY' or not m_ or m_ in seen or r_.get('by') not in (rs._duet.LEAD, rs._duet.SECOND):
            continue
        p_ = res_.get(m_)
        if not p_ and not any(x_.get('mint') == m_ and (x_.get('action') in ('HOLD', 'TRIM', 'SELL') or x_.get('talk')) for x_ in log):
            continue   # a BUY that never became a trade has no room
        seen.add(m_)
        rows_ = rs._seat.chat_window([r2_ for r2_ in log if r2_.get('mint') == m_ and (r2_.get('at') or 0) >= (r_.get('at') or 0) - 5])[::-1]
        tr_ = next((x_ for x_ in rs._duo_tape()[1] if x_.get('mint') == m_ and abs(rs._fuse._f(x_.get('at')) - rs._fuse._f(r_.get('at'))) <= 900), None)   # 🏁 the whole position from the ledger (trims included)
        sl_ = [s_ for s_ in (tr_ or {}).get('sells') or [] if s_.get('sig')]
        out.append({'mint': m_, 'symbol': r_.get('symbol'), 'model': r_.get('model'), 'at': r_.get('at'), 'pct': ((tr_ or {}).get('result') or {}).get('pct', (p_ or {}).get('realPct')),
                    'usd': ((tr_ or {}).get('result') or {}).get('usd'), 'banked': (tr_ or {}).get('banked'), 'closed': bool((p_ or {}).get('closedAt')) or (tr_ or {}).get('state') == 'sold',
                    'inUsd': ((tr_ or {}).get('buy') or {}).get('usd'), 'heldMin': ((tr_ or {}).get('result') or {}).get('heldMin'),
                    'back': round(sum(rs._fuse._f(s_.get('usd')) for s_ in sl_), 3) if sl_ else None,   # 💵 what the confirmed sells put back in the card's cash (each one has its chain signature)
                    'closedAt': (tr_ or {}).get('closedAt'),
                    'rows': [{**{k_: x_.get(k_) for k_ in ('at', 'model', 'action', 'view', 'why', 'conf', 'pct', 'talk')}, 'key': rs._dv_key(x_), 'mine': x_.get('by') == 'owner',
                              'votes': rs._dv.view(rs._dv_mem.get() or {}, rs._dv_key(x_))} for x_ in rows_]})
        if len(out) >= keep:
            break
    return out


def _duo_holding(l):
    """💹 the AI seat's live trade: coin, $ in, $ now, P&L % and $, peak, held minutes, its own TP / SL (live price from the shared cache)."""
    rs = _rs()
    px_ = rs._fuse._f((rs._jup_px_cache.get(l.get('mint')) or (0, 0))[1]) or rs._fuse._f(l.get('px'))
    en_, u_ = rs._fuse._f(l.get('entry')), rs._fuse._f(l.get('units'))
    cost_ = rs._fuse._f(l.get('costUsd')) or en_ * u_
    now_v = u_ * px_ if px_ > 0 else None
    pos_ = (rs._office_state().get('pos') or {}).get(l.get('mint')) or {}
    return {'symbol': l.get('symbol'), 'mint': l.get('mint'), 'since': l.get('at'), 'tp': l.get('aiTp'), 'sl': l.get('aiSl'),
            'inUsd': round(cost_, 3) if cost_ else None, 'nowUsd': round(now_v, 3) if now_v else None,
            'pct': round((px_ / en_ - 1) * 100, 2) if en_ > 0 and px_ > 0 else None, 'pnlUsd': round(now_v - cost_, 3) if now_v and cost_ else None,
            'peak': pos_.get('peak'), 'heldMin': round((rs.time.time() - rs._fuse._f(l.get('at'))) / 60, 1) if l.get('at') else None}


def _duo_card_legs():
    """The real card's coins right now (no reserved seats, no SOL)."""
    rs = _rs()
    return [l for c_ in (((rs._json_load(rs.FUSE_HQ_PATH, {}) or {}).get('prime') or {}).get('cards') or {}).values() if (c_ or {}).get('real')
            for l in c_.get('legs') or [] if not l.get('placeholder') and l.get('mint') and l.get('mint') != rs._fw.SOL_MINT]


def _duo_coin_rooms(log, ai_mint):
    """💬 One chat room per coin on the card that is NOT the models' trade — EVERY coin, not only the ones a model talked about (owner, 2026-10-17:
    "not seeing the agents' thoughts on coins they bought"): the card's own events on it (why the agents bought it, their banks / swaps / lines,
    your lines), Reaper's call on it right now, plus the models' idle reads and your chime-ins."""
    rs = _rs()
    legs_ = {l.get('mint'): l for l in rs._duo_card_legs()}
    card_ = next((c for c in ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}).values() if (c or {}).get('real')), {}) or {}
    reps_ = {r_.get('mint'): r_ for r_ in rs._office.get('reports') or [] if isinstance(r_, dict)}
    out = []
    for m_, l_ in legs_.items():
        if not m_ or m_ == ai_mint:
            continue
        sym_ = l_.get('symbol')
        talk_ = [{**{k_: x_.get(k_) for k_ in ('at', 'model', 'action', 'view', 'why', 'conf', 'pct', 'talk')}, 'key': rs._dv_key(x_), 'mine': x_.get('by') == 'owner',
                  'votes': rs._dv.view(rs._dv_mem.get() or {}, rs._dv_key(x_))} for x_ in log or [] if x_.get('mint') == m_ and (x_.get('idle') or x_.get('coinTalk'))]
        ev_ = [{'at': e_.get('at'), 'model': 'REAPER' if 'Reaper' in str(e_.get('why') or '') else 'YOU' if e_.get('kind') in ('level', 'manual-sell') else 'AGENTS', 'action': 'TALK', 'talk': True,
                'view': str(e_.get('move') or e_.get('kind') or '').upper(), 'why': str(e_.get('why') or '')[:220], 'mine': e_.get('kind') in ('level', 'manual-sell')}
               for e_ in card_.get('events') or [] if sym_ and (e_.get('mint') == m_ or e_.get('symbol') == sym_ or f"${sym_} " in str(e_.get('why') or '') + ' ')]
        rp_ = reps_.get(m_)
        now_ = [{'at': round(rs.time.time()), 'model': 'REAPER', 'action': 'TALK', 'talk': True, 'view': rp_.get('state'),
                 'why': f"{rp_.get('rule')} · {str(rp_.get('evidence') or '')[:180]}", 'pct': rp_.get('pct'), 'live': True}] if rp_ else []
        rows_ = rs._seat.chat_window(sorted(talk_ + ev_[-8:], key=lambda x: rs._fuse._f(x.get('at'))), 18) + now_   # 💬 your lines always stay
        out.append({'mint': m_, 'symbol': sym_, 'who': 'you' if l_.get('picked') else 'agents', 'rows': rows_[::-1],
                    'last': max([rs._fuse._f(x.get('at')) for x in talk_ + ev_] or [0])})
    return sorted(out, key=lambda r: -r['last'])


def _duo_pin_cap(r):
    rs = _rs()
    c = (r.get('vitals') or {}).get('cap') or r.get('cap')
    if c or not r.get('mint'):
        return c
    k = f"{r.get('at')}|{r.get('model')}|{r.get('mint')}"
    if k not in rs._duo_cap_seen:
        if len(rs._duo_cap_seen) > 4000:
            for k0 in list(rs._duo_cap_seen)[:1000]:
                rs._duo_cap_seen.pop(k0, None)
        rs._duo_cap_seen[k] = rs._duo_cap(r.get('mint'))
    return rs._duo_cap_seen[k]


def _duo_cap(mint):
    """A line with no cap of its own (your chime-in, Reaper) is pinned at the coin's live cap."""
    rs = _rs()
    try:
        return rs._seat.cand_row(rs._tk.KERNEL.candidate(mint) or {'mint': mint}).get('cap') if mint else None
    except Exception:
        return None


def _duo_phase(phase, held):
    """The seat's phase as the screen must read it: a HOLDING left over from the last tick with no coin in the seat is the trade that just
    closed (its review minute) → SOLD, never 'running $?' over an EMPTY seat."""
    ph = phase or ('HOLDING' if held else 'HUNTING')
    return 'SOLD' if ph == 'HOLDING' and not held else 'HOLDING' if held and ph in ('HUNTING', 'SOLD') else ph


def _duo_view(env=None):
    """🔁 The G4 × OSSY seat for the Agents tab (small: mode, whose turn, each model's record, the open paper seat, the last 8 calls)."""
    rs = _rs()
    try:
        st_ = rs._g4_state()
        env = env or rs.os.environ
        nm = lambda k: rs._air.model_name(env, k)
        legs_ = [l for c_ in (((rs._json_load(rs.FUSE_HQ_PATH, {}) or {}).get('prime') or {}).get('cards') or {}).values() if (c_ or {}).get('real') for l in c_.get('legs') or [] if l.get('aiSeat') and not l.get('placeholder')]
        first_, _s = rs._seat.turn(st_['log'], rs._duet.LEAD, rs._duet.SECOND, bool((st_['book'] or {}).get('open')) or bool(legs_), opener=st_.get('opener'), holder=(legs_[0].get('aiBy') if legs_ else ((st_['book'] or {}).get('open') or {}).get('by')))
        held_l = legs_[0] if legs_ else None
        hm_ = rs._g4_mem.get() or {}
        card_l = rs._duo_card_legs()
        return {'mode': rs._oe.clean_policy(rs._prime_real_cfg())['agentAiSeat'], 'next': nm(first_), 'at': st_['at'], 'busy': rs._g4['busy'],
                'phase': rs._duo_phase(rs._g4.get('phase'), held_l), 'holder': nm(held_l.get('aiBy')) if held_l and held_l.get('aiBy') else None,
                'seats': {'used': len(card_l), 'max': int(rs._fuse._f(rs._prime_real_cfg().get('coins')) or 4)},   # 🪑 the real card's seats (the models need one open)
                'guards': bool(hm_.get('guards')),   # 🔁 off = strict turns (one trade each); on = a losing model's turn can be skipped
                'bench': {nm(k_): rs._seat.bench((rs._ai.get('book') or {}).get('done') or [], k_) for k_ in (rs._duet.LEAD, rs._duet.SECOND)},   # 🪑 each model's FAVOR-call record (a warning while guards are off)
                'hunt': {'by': nm(hm_['huntBy']), 'since': hm_.get('huntSince'), 'turnSec': rs._seat.HUNT_TURN_SEC} if not held_l and hm_.get('huntBy') else None,   # ⏱ the hunter's clock
                'holding': rs._duo_holding(held_l) if held_l else None,
                'totals': rs._duo_totals(),   # 💰 each model's REAL closed-trade total: trades, won, $ and % (all time)
                'rooms': rs._duo_rooms(st_['log']),   # 🗂 every past model trade's own room: its convo + result, reopenable
                'conf': {nm(k_): {'boost': rs._dv.confidence(rs._dv_mem.get() or {}, k_), 'words': rs._dv.words(rs._dv_mem.get() or {}, k_)} for k_ in (rs._duet.LEAD, rs._duet.SECOND, 'owner')},
                'trade': [{**{k_: r_.get(k_) for k_ in ('at', 'model', 'action', 'view', 'why', 'conf', 'pct', 'talk')}, 'key': rs._dv_key(r_), 'mine': r_.get('by') == 'owner', 'votes': rs._dv.view(rs._dv_mem.get() or {}, rs._dv_key(r_))} for r_ in rs._seat.chat_window([r0_ for r0_ in st_['log']
                          if held_l and r0_.get('mint') == held_l.get('mint') and (r0_.get('at') or 0) >= rs._fuse._f(held_l.get('at')) - 180])][::-1],   # 💬 the conversation on THIS trade (your lines always stay)   # 💬 the conversation on THIS trade
                'coinRooms': rs._duo_coin_rooms(st_['log'], held_l.get('mint') if held_l else None),   # 💬 $ELON's own chat: what they say about YOUR coins / the agents' coins
                'between': [{**{k_: r_.get(k_) for k_ in ('at', 'model', 'action', 'view', 'why', 'conf', 'pct', 'talk', 'symbol')}, 'key': rs._dv_key(r_), 'mine': r_.get('by') == 'owner', 'votes': rs._dv.view(rs._dv_mem.get() or {}, rs._dv_key(r_))}
                            for r_ in rs._seat.chat_window([r0_ for r0_ in st_['log'] if (r0_.get('idle') or r0_.get('by') == 'owner') and not r0_.get('mint')], 14)][::-1],   # 💬 what they said BETWEEN trades (+ your lines then)
                'rec': {nm(k): v for k, v in rs._seat.by_model((st_['book'] or {}).get('closed')).items() if k in (rs._duet.LEAD, rs._duet.SECOND)},
                'open': (st_['book'] or {}).get('open'),
                'agents': rs._seat.by_model((st_['book'] or {}).get('closed')).get('agents'), 'fate': rs._g4.get('fate'), 'live': rs._g4.get('live'),
                'limits': {nm(k_): rs._air.rig(k_, 'timeout', (rs._air.PROVIDERS.get(k_) or (0,) * 7)[6] or 90) for k_ in (rs._duet.LEAD, rs._duet.SECOND)},   # ⏱ each model's real call deadline (the live line runs against it)
                'log': [{k: r.get(k) for k in ('at', 'model', 'action', 'symbol', 'why', 'conf', 'pct', 'ms', 'miss')} for r in st_['log'][-30:][::-1]],
                'chart': [{'at': r.get('at'), 'model': r.get('model'), 'mint': r.get('mint'), 'sym': r.get('symbol'), 'action': r.get('action'), 'view': r.get('view'), 'talk': bool(r.get('talk')), 'why': str(r.get('why') or '')[:rs._seat.WHY_MAX],
                           'pct': r.get('pct'), 'cap': rs._duo_pin_cap(r)} for r in rs._duo_chart_rows(st_['log'], card={l_.get('mint') for l_ in rs._duo_card_legs()})]}   # 📣 what the models said about each coin → bubbles on the Agents chart
    except Exception as e:
        return {'mode': 'off', 'err': str(e)[:80]}


def _agents_page_dict(snap):
    rs = _rs()
    off = snap.get('office')
    return {**snap, 'duo': rs._duo_view(), 'table': [{k: v for k, v in r.items() if k not in rs.AGENTS_ROW_DROP} if isinstance(r, dict) else r for r in snap.get('table') or []],
            'office': {k: v for k, v in off.items() if k not in rs.AGENTS_PAGE_DROP} if isinstance(off, dict) else off}


def _agents_page_body(now=None):
    rs = _rs()
    now = rs.time.time() if now is None else now
    key = (id(rs._agents.get('view')), id(rs._office.get('payload')), int(now / rs.AGENTS_PAGE_SEC))
    if rs._agents_page['key'] != key:
        page = rs._agents_page_dict(rs._agents_snapshot())
        try:
            body = rs.json.dumps(page, separators=(',', ':')).encode()
        except (TypeError, ValueError):
            from fastapi.encoders import jsonable_encoder
            body = rs.json.dumps(jsonable_encoder(page), separators=(',', ':')).encode()
        rs._agents_page.update(key=(id(rs._agents.get('view')), id(rs._office.get('payload')), int(now / rs.AGENTS_PAGE_SEC)), body=body)
    return rs._agents_page['body']


async def _fuse_warm():
    rs = _rs()
    if not rs._fuse_warm_n.get('restored'):
        rs._intel_boot()
    rs._FUSE_FORCE.set(True)          # task-local: viewers never see it, they keep reading the previous copy
    rs._fuse_warm_n['n'] += 1
    if rs._fuse_warm_n['n'] % 24 == 2:   # ~10 min: who the elite traders are + what they bought (FeeCat learns from it)
        await rs._crowd_build()
    if rs._fuse_warm_n['n'] % 3 == 1:   # 💾 finished holder scans survive a restart (a restart used to blank every list for minutes)
        rs._intel_save()
    try:   # 🗑 trench scan (~2 min, cached; heavy on-chain counts only for the 5 busiest finalists)
        await rs._trench_build(rs.time.time())
    except Exception as e:
        print('trench:', e)
    try:   # 📣 Pump's own callouts (once a minute) · 🧲 which runners new launches are paired with (every 2 min)
        await rs._pump_calls_build()
        await rs._feeders_build()
    except Exception as e:
        print('pump callouts:', e)
    try:   # 📣 callouts (~3.5 min): the open trench list's leaders, noted once, settled an hour later
        await rs._callout_tick(rs.time.time())
    except Exception as e:
        print('callouts:', e)
    try:   # ⚡ free hourly call: settle finished hours, open this hour's ballot
        await rs._predict_tick(rs.time.time())
        await rs._rm_tick(rs.time.time())
    except Exception as e:
        print('predict:', e)
    try:   # 🛡 crews: the week's top 3 pay their members season points, once
        await rs._crew_season_tick(rs.time.time())
        await rs._wars_tick(rs.time.time())
    except Exception as e:
        print('crews:', e)
    if rs._fuse_warm_n['n'] % 144 == 53:   # ~1h: 🧪 the edge audit + the proof gate on the real card
        try:
            await rs._proof_gate_tick(rs.time.time())
        except Exception as e:
            print('proof gate:', e)
    if rs._fuse_warm_n['n'] % 144 == 31:   # ~1h: 🧾 what's working / what's not, always running (owner inbox when something flips)
        try:
            await rs._verdict_tick(rs.time.time())
        except Exception as e:
            print('verdict:', e)
    if rs._fuse_warm_n['n'] % 144 == 7:   # ~1h: 🧹 data cleaner (stale derived data only — never money records or message text)
        try:
            await rs._data_clean(rs.time.time())
        except Exception as e:
            print('data cleaner:', e)
    try:   # 🧾 proof + real duels settle on time even with nobody watching
        await rs._proof_build()
    except Exception as e:
        print('proof:', e)
    try:   # 🏁 the contenders league is kept warm, so the Arena reads it in ms and the tier engine always knows who is next up
        await rs._contenders_build(fresh=True)
    except Exception as e:
        print('contenders:', e)
    if rs._fuse_warm_n['n'] % 36 == 5:   # ~15 min (one runner round): auto-strength picks the proven-best engine dial
        await rs._engine_auto(rs.time.time())
    if rs._fuse_warm_n['n'] % 144 == 3:  # ~1h: nudge HQ if a stronger engine config is waiting
        rs._engine_nudge(rs.time.time())
    if rs._fuse_warm_n['n'] % 12 == 1:   # ~5 min: refresh card holders' Fuse scores (feeds their trust score)
        holders = list({x['wallet'] for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or []})[:200]
        await rs.asyncio.gather(*[rs._fuse_score(w, fresh=True) for w in holders], return_exceptions=True)
    if rs._fuse_warm_n['n'] % 36 == 20:   # ~15 min: 🧠 300 background sim cards → the brain
        try:
            await rs._pg_sim_tick(rs.time.time())
        except Exception as e:
            print('pg sim:', e)
    if rs._fuse_warm_n['n'] % 12 == 9:   # ~5 min: 📏 paper ⇄ real quotes (paper's fill model is checked against Jupiter)
        try:
            await rs._paper_quote_audit(rs.time.time())
            _cal0 = rs._fw_calibration(rs._fw_load()); rs._prime.IMPACT_MULT = _cal0['impactMult']; rs._prime.SPREAD = _cal0.get('spread') or 0.0
        except Exception as e:
            print('quote audit:', e)
    if rs._fuse_warm_n['n'] % 12 == 7:   # ~5 min: 📖 the rep engine learns today's meme terms (new launches + chat)
        await rs._meme_tick(rs.time.time())
    if rs._fuse_warm_n['n'] % 2 == 1:    # ~50s: ⚔ engine playground battles (paper, HQ only)
        try:
            await rs._pg_battle_tick(rs.time.time())
        except Exception as e:
            print(f'[pg-battle] {e}')
    await rs._prime_tick(rs.time.time())    # ~25s: ⭐ tier cards (paper + real) — stops, rug shield and the keeper can't wait
    await rs._runner_live()
    await rs._arena_auto_refresh(rs.time.time())
    await rs.asyncio.gather(rs.runners_discover(), rs.fuse_arena_public(), rs.fuse_season(), rs._sol_usd_live(), return_exceptions=True)
    await rs._battle_tick(rs.time.time())
    rs._fuse_chat_tick(rs.time.time())


def _round_move(p, live):
    """A round pick's live move since entry, or None when the feed no longer sees the coin (never a fake 0%)."""
    rs = _rs()
    now_px = rs._fuse._f(({x['mint']: x for x in live['passing'] + live['dropped']}.get(p['mint']) or {}).get('price'))
    entry = rs._fuse._f(p.get('entry'))
    return round((now_px / entry - 1) * 100, 2) if now_px > 0 and entry > 0 else None


async def _scenario_stage(rd, now):
    """Once per runner round (or when HQ changes its picks): the scenario cards HQ PICKED in the engine playground
    (🎨 Creator's pick) are dealt onto the Arena at today's prices with this round's runners + SOL anchor. Runner-ups stay in
    the engine until picked; picked cards fill empty battle seats; ⭐ Publish puts one on the stage for good."""
    rs = _rs()
    rnd = (rd.get('rounds') or [None])[-1]
    picks = sorted(rd.get('creatorPicks') or [])
    if not rnd or not rnd.get('picks') or (rd.get('scenarioStageRound') == rnd.get('id') and rd.get('scenarioStagePicks') == picks):
        return None
    scen = [x for x in await rs.asyncio.to_thread(rs._rn.scenarios, rd.get('rounds') or [], rd.get('paths') or {}, now, rs._hq.RISK_DIALS) if x['id'] in set(picks)]   # ⚙ CPU off the loop (Lag catcher 2026-10-26: 2.8s stalls)
    anchor = await rs._top_anchor()
    cards = rs._rn.scenario_cards(scen, rnd['picks'], anchor, top=8, losers_ok=True)
    pgb_ = rd.get('pgBattle') or {}
    live_ = await rs._runner_live()
    cand_ = [{'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'mint': r.get('mint')} for r in live_.get('passing') or [] if r.get('pairAddress')]
    for i, c in enumerate(cards):   # 🎨 a picked card plays the playground's shape (≥ 4 coins, ≤ 2 pools) on the timeframe it proved best
        cards[i] = rs._pgb.fit_shape(c, cand_, rs._pgb.MIN_COINS)
        mins = rs._pgb.assign_clock((pgb_.get('cardClocks') or {}).get(c['id']), i)
        cards[i]['clock'] = mins; cards[i]['cfg'] = {**(c.get('cfg') or {}), 'rotateHours': round(mins / 60, 4)}
    if not cards:
        async with rs._admin_lock:
            d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['scenarioStage'] = []; d['scenarioStageRound'] = rnd.get('id'); d['scenarioStagePicks'] = picks; rs._json_save(rs.RUNNERS_PATH, d)
        rs._arena_mega_cache.update(at=0.0, data=None)
        return 0
    px = await rs._hq_prices([l for c in cards for l in c['legs']])
    stage = [{'id': f"scen-{c['id']}-{str(rnd['id'])[:6]}", 'src': c['id'], 'emoji': c['name'].split(' ', 1)[0], 'name': c['name'].split(' ', 1)[-1], 'at': now, 'tp': c['tp'], 'sl': c['sl'],
              'dial': c['dial'], 'cfg': c['cfg'], 'label': c['label'], 'clock': c.get('clock'),
              'legs': [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'baseAddress': l.get('mint'), 'weight': l['weight'], 'runner': l['role'] == 'runner', 'entry': rs._fuse._f(px.get(l['pairAddress']))}
                       for l in c['legs'] if rs._fuse._f(px.get(l['pairAddress'])) > 0]} for c in cards]
    async with rs._admin_lock:
        d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
        vers = d.setdefault('scenarioVersions', {})
        for st in stage:   # each new deal of the same scenario = its next version (v.01, v.02 …)
            vers[st['src']] = int(vers.get(st['src']) or 0) + 1; st['version'] = vers[st['src']]
        d['scenarioStage'] = stage; d['scenarioStageRound'] = rnd.get('id'); d['scenarioStagePicks'] = picks; rs._json_save(rs.RUNNERS_PATH, d)
    rs._arena_mega_cache.update(at=0.0, data=None)
    return len(stage)


def _pg_pick_ok(rd, sid):
    """🎨 A big card reaches the Arena only once it EARNED a playground seat: the background field (≤ 8) competes and only its top
    3 (`pg_battle.shown`) can be picked. With no field yet (battles off / still dealing) any scenario card can be picked."""
    rs = _rs()
    b = rd.get('pgBattle') or {}
    ids = list(b.get('cards') or {})
    return len(ids) < rs._pgb.SHOWN or sid in rs._pgb.shown(b.get('record'), b.get('pcts'), ids)


async def _engine_auto(now):
    """🔧 Auto-strength, once per runner round: if another engine dial is PROVEN better (runners.auto_pick on the dial proof),
    switch to it and log it (audit + admin inbox). Off when HQ turned auto-tune off (RUNNERS_PATH.autoTune = False)."""
    rs = _rs()
    rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    await rs._scenario_stage(rd, now)
    if rd.get('autoTune') is not False and rd.get('rounds'):   # 🩺 doctor: learn which picks win, apply that filter or sit out
        cfg_d = rs._rn.clean_cfg(rd.get('cfg') or {})
        f24 = rs._rn.filter_proof(rd['rounds'], rd.get('paths') or {}, now, cfg_d, 24 * 3600)
        f72 = rs._rn.filter_proof(rd['rounds'], rd.get('paths') or {}, now, cfg_d, 72 * 3600)
        doc = rs._rn.doctor(f24, f72)
        if doc['filter'] != rd.get('pickFilter') or doc['sitOut'] != bool(rd.get('sitOut')):
            async with rs._admin_lock:
                d_ = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); d_['pickFilter'] = doc['filter']; d_['sitOut'] = doc['sitOut']; d_['doctorWhy'] = doc['why']; d_['doctorAt'] = now
                rs._json_save(rs.RUNNERS_PATH, d_)
                ad = rs._admin_load(); rs._audit(ad, 'engine-auto', 'runners-config', f"🩺 doctor: filter {doc['filter'] or 'none'} · sit out {doc['sitOut']} — {doc['why']}"[:200]); rs._admin_save(ad)
            for w in rs._admin_wallets():
                rs.notify(w, 'admin', f"🩺 Fuse engine doctor: {('pick filter → ' + rs._rn.PICK_FILTERS[doc['filter']][0]) if doc['filter'] else ('sitting out runners' if doc['sitOut'] else 'filter cleared')} — {doc['why']}",
                       url='/terminal/command?tab=fuse', once=f"doctor-{doc['filter']}-{doc['sitOut']}-{int(now // 3600)}", meta={'claim': doc['why'], 'source': 'Runner rounds (paper, real prices)'})
            rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    if rd.get('autoTune') is False or not rd.get('rounds'):
        return None
    # 💡 scenario winner → runner exits (same TP×SL combo best in 24h AND 72h, ahead of the current exits) — audited
    cfg0 = rs._rn.clean_cfg(rd.get('cfg') or {})
    ex, ex_why = rs._rn.exits_pick({w: rs._rn.scenario_grid(rd['rounds'], rd['paths'], now, sec) for w, sec in (('24h', 86400), ('72h', 3 * 86400))},
                                (int(cfg0.get('runnerTp2') or 100), int(cfg0.get('runnerStop') or 30)))
    if ex:
        async with rs._admin_lock:
            d0 = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); d0['cfg'] = {**(d0.get('cfg') or {}), 'runnerTp2': ex[0], 'runnerStop': ex[1]}; d0['cfgDial'] = 'custom'; rs._json_save(rs.RUNNERS_PATH, d0)
        ad0 = rs._admin_load(); rs._audit(ad0, 'engine-auto', 'runners-config', f'scenario exits → TP +{ex[0]}% / stop −{ex[1]}%: {ex_why}'[:300]); rs._admin_save(ad0)
        rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    proofs = {w: rs._rn.dial_proof(rd['rounds'], rd['paths'], now, rs._hq.RISK_DIALS, window=sec) for w, sec in rs._rn.PROOF_WINDOWS.items()}
    dial, why = rs._rn.auto_pick_multi(proofs, rd.get('cfgDial'))
    if not dial or dial not in rs._rn.ENGINE_DIALS:
        return None
    async with rs._admin_lock:
        d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['cfg'] = rs._rn.engine_dial(dial, d.get('cfg') or {}); d['cfgDial'] = dial; rs._json_save(rs.RUNNERS_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, 'engine-auto', 'runners-config', f'auto-strength → {dial}: {why}'); rs._admin_save(ad)
    for adm in rs._admin_wallets():
        rs.notify(adm, 'shield', f"🔧 Engine auto-strength: switched to the {dial} dial — {why}. Turn off in HQ › Fuse › Engine.", url='/terminal/command?tab=fuse', once=f"engine-auto-{dial}-{int(now // 3600)}")
    return dial


def _engine_nudge(now):
    """Once per new set of suggestions: tell HQ a stronger engine config is waiting (they click to apply)."""
    rs = _rs()
    s = rs._rn.suggest_cfg(rs._runner_cfg())
    if s:
        key = ','.join(f"{x['key']}:{x['to']}" for x in s)
        for adm in rs._admin_wallets():
            rs.notify(adm, 'shield', f"⚡ Stronger Fuse engine config found ({len(s)} settings) — review and apply in HQ › Fuse › Engine.",
                   url='/terminal/command?tab=fuse', once=f"engine-{rs.hashlib.sha1(key.encode()).hexdigest()[:12]}", meta={'claim': s[0]['why'], 'source': 'runners.RECOMMENDED'})
    return s


async def _top_anchor():
    """⚓ The engine cards' anchor: the most ACTIVE major right now (`fuse.rank_anchors`), never SOL by name."""
    rs = _rs()
    top = next(iter(rs._fuse.rank_anchors(await rs._majors_rows())), None)
    return {'chainId': 'solana', 'pairAddress': top['pairAddress'], 'symbol': top.get('symbol'), 'mint': top.get('baseAddress')} if top else None


async def _pg_scenario_cards(rd, scen=None, now=None, losers_ok=False, top=6, coins=None):
    """The playground's best scenario cards (this round's gated runners + SOL anchor), versioned and tagged with where they're listed.
    `coins` = the regular card shape (6 coins, ≤ 2 pools, topped up with the best gated runners)."""
    rs = _rs()
    scen = scen if scen is not None else rs._rn.scenarios(rd.get('rounds') or [], rd.get('paths') or {}, now or rs.time.time(), rs._hq.RISK_DIALS)
    anchor = await rs._top_anchor()
    listed = {**{x: 'pick' for x in rd.get('creatorPicks') or []}, **{x.get('src'): 'bench' for x in rd.get('scenarioStage') or []},
              **{f.get('fromScenario'): 'stage' for f in (rs._json_load(rs.FUSES_PATH, {'fuses': {}}).get('fuses') or {}).values() if f.get('arena') and f.get('fromScenario')}}
    out = rs._rn.tag_versions(rs._rn.scenario_cards(scen, ((rd.get('rounds') or [{}])[-1] or {}).get('picks'), anchor, top=top, losers_ok=losers_ok), rd.get('scenarioVersions') or {}, listed)
    if coins:
        cand = [{'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'mint': r.get('mint')} for r in (await rs._runner_live()).get('passing') or [] if r.get('pairAddress')]
        out = [rs._pgb.fit_shape(c, cand, coins) for c in out]
        for c in out:   # weights back to 100% after the top-up
            tot = sum(rs._fuse._f(l.get('weight')) for l in c['legs']) or 1.0
            c['legs'] = [{**l, 'weight': round(rs._fuse._f(l.get('weight')) / tot * 100, 1)} for l in c['legs']]
    return out


def _pg_battle_view(rd):
    rs = _rs()
    b = rd.get('pgBattle') or {}
    cards = b.get('cards') or {}
    view = lambda k: {**{x: (cards.get(k) or {}).get(x) for x in ('id', 'name', 'dial', 'tp', 'sl', 'swaps', 'phase', 'rounds', 'bredFrom')}, 'pct': (b.get('pcts') or {}).get(k),
                      'dna': (b.get('dna') or {}).get(k), 'dnaLabel': rs._dna.label((b.get('dna') or {}).get(k)) if (b.get('dna') or {}).get(k) else None,
                      'legs': [{x: l.get(x) for x in ('symbol', 'role', 'pairAddress')} for l in (cards.get(k) or {}).get('legs') or []], 'record': (b.get('record') or {}).get(k),
                      'clock': rs._pgb.assign_clock((b.get('cardClocks') or {}).get(k), list(cards).index(k) if k in cards else 0), 'clocks': (b.get('cardClocks') or {}).get(k) or {}}
    return {'cfg': rs._pgb.clean_cfg(b.get('cfg')), 'clockStats': b.get('clockStats') or {}, 'bestClock': b.get('bestClock'), 'roundNow': b.get('roundMins'), 'locked': b.get('locked') or [], 'scrapped': len(b.get('scrapped') or []), 'picks': rd.get('creatorPicks') or [], 'endsAt': b.get('endsAt'), 'pairs': [{'a': view(p['a']), 'b': view(p['b'])} for p in b.get('pairs') or []],
            'field': [view(k) for k in cards], 'shown': [view(k) for k in rs._pgb.shown(b.get('record'), b.get('pcts'), list(cards))],
            'log': (b.get('log') or [])[-12:][::-1], 'record': b.get('record') or {}, 'names': {k: c.get('name') for k, c in cards.items()},
            'brain': {**rs._dna.best(b.get('brain') or {}), 'label': rs._dna.label(rs._dna.best(b.get('brain') or {})['dna']), 'scores': b.get('brain') or {}}}


async def _pg_battle_tick(now):
    """⚔ Engine playground battles (paper, HQ only): deal the best scenario cards, swap TP / stop / dead coins mid-round,
    settle at the bell (bigger % wins), winners keep their coins, losers re-bred from this round's picks."""
    rs = _rs()
    rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}})
    b = rd.get('pgBattle') or {}
    cfg = rs._pgb.clean_cfg(b.get('cfg'))
    if not cfg['on']:
        return None
    scs = {c['id']: c for c in await rs._pg_scenario_cards(rd, None, now, losers_ok=True, top=max(8, cfg['cards']))}   # battles field the top-ranked scenarios even when negative
    if len(scs) < 2:
        return None
    cards = dict(b.get('cards') or {})
    scrapped = set(b.get('scrapped') or [])   # 🗑 dead strategies stay off the field (record kept)
    want = [k for k in scs if k not in scrapped][:cfg['cards']]
    legs = [{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for k in want for l in (cards.get(k) or scs[k])['legs']]
    live = await rs._runner_live()
    cand = [r for r in live.get('passing') or [] if r.get('pairAddress')]
    pairs_ = await rs._fuse_pairs(legs + [{'chainId': 'solana', 'pairAddress': r['pairAddress']} for r in cand[:12]])
    prices = {k: rs._fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}
    liqs = {k: rs._fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_.items()}
    quiet = {k: not (rs._fuse._f(((v.get('txns') or {}).get('m5') or {}).get('buys')) + rs._fuse._f(((v.get('txns') or {}).get('m5') or {}).get('sells'))) and not rs._fuse._f((v.get('volume') or {}).get('m5'))
             for k, v in pairs_.items()}
    cand = [{'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'mint': r.get('mint'), 'price': prices.get(r['pairAddress']) or r.get('price'), 'liq': liqs.get(r['pairAddress'])} for r in cand]
    rcfg_ = rs._runner_cfg()
    targets = rs._pgb.coin_targets(int(rcfg_.get('autoCoins') or 4) + int(rcfg_.get('autoPools') or 3))   # HQ's amount: half · same · double, ≥ 4
    for i, k in enumerate(want):   # deal any missing card — ≥ 4 coins, ≤ 2 pools; the engine experiments with the coin count
        if k not in cards or not cards[k].get('legs'):
            cards[k] = {**rs._pgb.deal(rs._pgb.fit_shape(scs[k], cand, targets[i % len(targets)]), prices, liqs, now, cfg['sizeUsd']), 'target': targets[i % len(targets)]}
    dna = {k: v for k, v in (b.get('dna') or {}).items() if k in want}
    dna = rs._dna.assign([{'id': k, 'dial': scs[k].get('dial')} for k in want], known=dna)   # 🧬 every battle card plays its own DNA
    results = []
    if now >= rs._fuse._f(b.get('endsAt')):
        pcts = {k: rs._pgb.round_pct(cards[k], prices, liqs) for k in cards if k in want}
        results, record, losers = rs._pgb.settle(b.get('pairs'), pcts, b.get('record'), now)
        # 🧠 the engine learns which DNA wins (trait win rates), then breeds the first loser with the winning DNA (exploit) — the rest
        # get fresh unique DNA (explore)
        sc_ = rs._dna.learn([{'winner': r_['winner'], 'loser': r_['b'] if r_['winner'] == r_['a'] else r_['a']} for r_ in results if r_.get('winner')], dna)
        brain = b.get('brain') or {}
        for t_, vals in sc_.items():
            for v_, st_ in vals.items():
                cur_ = brain.setdefault(t_, {}).setdefault(v_, {'w': 0, 'n': 0}); cur_['w'] += st_['w']; cur_['n'] += st_['n']
        b['brain'] = brain
        best_ = rs._dna.best(brain)['dna']; exploited = False
        locked = set(b.get('locked') or [])   # 🔒 HQ-locked cards keep their coins + DNA even after a loss
        beat_by = {(r_['b'] if r_['winner'] == r_['a'] else r_['a']): r_['winner'] for r_ in results if r_.get('winner')}
        lineage = dict(b.get('lineage') or {})
        for k in want:
            if k in losers and k not in locked:   # 🧬 re-bred: same scenario, this round's picks, fresh $ (same coin-count experiment)
                cards[k] = {**rs._pgb.deal(rs._pgb.fit_shape(scs[k], cand, cards.get(k, {}).get('target') or targets[0]), prices, liqs, now, cfg['sizeUsd']), 'target': cards.get(k, {}).get('target') or targets[0]}
                par = beat_by.get(k)
                if par and cards.get(par):   # it now plays the strategy that beat it → named as that strategy's next version (v.0x)
                    gen = int((lineage.get(par) or {}).get('gen') or 0) + 1
                    lineage[k] = {'parent': par, 'gen': gen}
                    cards[k]['name'] = rs._pgb.child_name(cards[par].get('name'), gen + 1); cards[k]['bredFrom'] = cards[par].get('name')
                if not exploited and rs._dna.sig(best_) not in {rs._dna.sig(v) for kk, v in dna.items() if kk != k}:
                    dna[k] = best_; exploited = True
                else:
                    dna.pop(k, None)
            else:             # winner keeps its coins, re-shaped by its DNA cycle (true fills); the next round counts from here
                cards[k] = rs._pgb.cycle_rebalance(cards[k], dna.get(k), pcts.get(k), prices, liqs)
                cards[k] = {**cards[k], 'roundUsd': rs._pgb.value(cards[k], prices, liqs)}
        dead_now = rs._pgb.dead(record, locked)
        for k in dead_now:   # 🗑 scrap strategies that only lose — they stop using data, the record stays
            scrapped.add(k); cards.pop(k, None); dna.pop(k, None)
        if dead_now and set(dead_now) & set(rd.get('creatorPicks') or []):   # a dead big card leaves the Arena too; the engine deals new ones
            async with rs._admin_lock:
                rd2 = rs._json_load(rs.RUNNERS_PATH, {}); rd2['creatorPicks'] = [x for x in rd2.get('creatorPicks') or [] if x not in set(dead_now)]; rs._json_save(rs.RUNNERS_PATH, rd2)
            rd['creatorPicks'] = [x for x in rd.get('creatorPicks') or [] if x not in set(dead_now)]
        want = [k for k in want if k not in scrapped]
        dna = rs._dna.assign([{'id': k, 'dial': scs[k].get('dial')} for k in want], known=dna)
        played = int(b.get('roundMins') or cfg['roundMins'])
        b['clockStats'] = rs._pgb.clock_learn(b.get('clockStats'), played, list(pcts.values()))   # ⏱ what each round length did
        b['cardClocks'] = rs._pgb.card_clock_learn(b.get('cardClocks'), played, pcts)            # ⏱ … and per card: its own best timeframe
        nxt_clock = rs._pgb.next_clock(cfg, int(b.get('bells') or 0))   # first round 5 min, then 15 · 30 · 60 · 5 …
        b = {**b, 'lineage': {k: v for k, v in lineage.items() if k in want}, 'bells': int(b.get('bells') or 0) + 1, 'roundMins': nxt_clock, 'bestClock': rs._pgb.best_clock(b['clockStats']),
             'record': record, 'scrapped': sorted(scrapped)[-300:], 'pairs': rs._pgb.pair_up(want), 'endsAt': now + nxt_clock * 60,
             'log': ((b.get('log') or []) + [{**r_, 'aName': cards.get(r_['a'], {}).get('name'), 'bName': cards.get(r_['b'], {}).get('name')} for r_ in results])[-40:]}
    else:
        for k in want:
            cards[k] = rs._pgb.tick(cards[k], prices, liqs, quiet, cand, cfg, now, dna.get(k))
    b['cards'] = {k: cards[k] for k in want}
    b['dna'] = dna
    b['pcts'] = {k: rs._pgb.round_pct(cards[k], prices, liqs) for k in want}
    b['cfg'] = cfg
    async with rs._admin_lock:
        d = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['pgBattle'] = b; rs._json_save(rs.RUNNERS_PATH, d)
    return len(results)


def _edge_load():
    """The last edge table from disk (once, after a restart) so cards are ranked before the first sim tick."""
    rs = _rs()
    if not rs._edge_state and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        rs._edge_state.update(rs._json_load(rs.EDGE_PATH, {}) or {'at': 0})
    return rs._edge_state


async def _pg_sim_tick(now):
    """🧠 Background playground: 300 sim cards (random clock / TP / SL / hold / rotate-only-losers) replayed over the REAL recorded
    price paths of the last 24h and 6h, fees on every swap. The brain keeps the trait scores; HQ can apply its pick to the tier engine."""
    rs = _rs()
    rd_ = rs._json_load(rs.RUNNERS_PATH, {})
    paths, rounds_ = rd_.get('paths') or {}, rd_.get('rounds') or []
    res24 = await rs.asyncio.to_thread(rs._pgs.run, paths, now, 300, 24, None, rs._pgs.SWAP_COST, rounds_)
    res6 = await rs.asyncio.to_thread(rs._pgs.run, paths, now, 200, 6, None, rs._pgs.SWAP_COST, rounds_)
    try:   # 🧠 what the board's own record says about its picks (learned only from outcomes already known) → ranking + real-money gate
        eb_ = await rs.asyncio.to_thread(rs._pedge.build, rounds_, paths, now)
        rs._edge_state.update(eb_)
        rs._json_save(rs.EDGE_PATH, eb_)
    except Exception as e:
        print('edge build:', e)
    res = res24 + res6
    if not res:
        return 0
    d = rs._json_load(rs.PG_SIM_PATH, {})
    score = rs._pgs.learn(res)
    was = rs._prime.weather(d)['level']
    d['prevBest'] = d.get('best') or {}   # 🧷 the self-fix only moves a setting when the same value wins twice in a row
    # ☠ settings whose typical sim card lost in BOTH windows sit out for a day (never the last value of a trait), then are judged again
    retired = rs._pgs.retire(rs._pgs.learn(res24), rs._pgs.learn(res6), d.get('retired'), now)
    d.update(at=now, summary=rs._pgs.summary(res), s24=rs._pgs.summary(res24), s6=rs._pgs.summary(res6), score=score, retired=retired, best=rs._pgs.best(score, retired=retired), byClock=rs._pgs.by_clock(res, retired=retired),
             history=((d.get('history') or []) + [{'at': now, **rs._pgs.summary(res)}])[-96:])
    try:   # 🎯 the Sniper setup per round length, walk-forward over the whole record (see pg_sim.proven)
        pv_, all_ = {}, {}
        for ck_ in rs._pgs.CLOCKS:
            got_ = await rs.asyncio.to_thread(rs._pgs.setups, paths, rounds_, now, ck_)
            if got_:
                all_[str(ck_)] = got_
                pv_.update({str(ck_): x for x in got_ if x['key'] == 'sniper'})
        d['setups'] = all_
        d['proven'] = pv_
        d['provenLog'] = ((d.get('provenLog') or []) + [{'at': now, **{k: [v['medPct'], v['windowsUp'], v['windows']] for k, v in pv_.items()},
                                                        **{f'h{k}': [x['medPct'], x['windowsUp'], x['windows']] for k, v in all_.items() for x in v if x['key'] == 'rhunt'}}])[-400:]   # how the proof itself moves, run after run
    except Exception as e:
        print('sim proven:', e)
    rs._json_save(rs.PG_SIM_PATH, d)
    wx = rs._prime.weather(d)
    if wx['level'] != was:   # 🌦 the real card's runner rule just changed → tell the owner once, in plain words
        say = {'clear': '☀ Runner weather cleared — the real card may buy every gated runner again.',
               'rain': f"🌧 Runner weather turned (sims {wx['avgPct']:+.1f}%) — the real card now buys only strong runners in deep pools.",
               'storm': f"⛈ Runner storm (sims {wx['avgPct']:+.1f}%) — the real card buys no runners, new majors only, until it clears."}[wx['level']]
        for w in rs._owner_wallets():
            rs.notify(w, 'fuse-card', say, url='/terminal/hq?tab=fuse', push=True, once=f"wx-{wx['level']}-{int(now // 3600)}",
                   meta={'claim': 'Runner weather', 'source': f"{wx['n']} sim cards on real recorded prices"})
    await rs._engine_self_fix(now, d)
    return len(res)


def _brain_patch(cfg, s24, best, prev=None, owner_set=()):
    """What the sim brain would change on ONE config (paper or the real card's own); {} when its 🧠 switch is off. Keys the OWNER set
    by hand (`owner_set`, e.g. 5-min rounds with patience 2) are never touched — the owner picks, the brain only fills the rest."""
    rs = _rs()
    if not cfg.get('autoBrain', True):
        return {}
    patch = {}
    bad = s24.get('n', 0) >= 100 and rs._fuse._f(s24.get('avgPct')) <= -5
    if bad != bool(cfg.get('strictRunners')):
        patch['strictRunners'] = bad
    floor_confirm = 3 if cfg['rotateHours'] * 60 <= 5 else 2   # 🔒 the SELF-FIX never takes patience under 3 on fast clocks. The owner may still pick 2 by hand (real guard floor = 2) — with 🧠 Auto-tune on, the brain can raise it back.
    for trait, key, cast in (('minDrop', 'rotateMinDrop', float), ('confirm', 'rotateConfirm', int)):
        b = best.get(trait)
        if b and b.get('n', 0) >= 30:
            v = max(floor_confirm, cast(b['value'])) if key == 'rotateConfirm' else cast(b['value'])
            # 🧷 no flapping: a value is applied only when the SAME value won the previous sim run too (rotateConfirm went
            # 3 → 4 → 3 → 4 every 30 min, rewriting the config and spamming every card's log)
            steady = not prev or (prev.get(trait) or {}).get('value') == b['value']
            if v != cfg.get(key) and steady:
                patch[key] = v
    return {k: v for k, v in patch.items() if k not in set(owner_set or ())}


async def _engine_self_fix(now, sim):
    """🔧 The engine fixes itself from the sim brain (cfg `autoBrain`, default on; the clock is never touched):
      • 🌧 runner weather — the last 24h of sims averaging ≤ −5% → strict runners (only coins with real flow + buyers get in);
      • the brain's rotate-only-losers threshold + patience (rounds in a row) are applied once 30+ sims back each value.
    Paper and the 💵 real card are tuned SEPARATELY, each only if its own 🧠 switch is on. Audited + a `brain` event only on cards it changed."""
    rs = _rs()
    s24, best = sim.get('s24') or {}, sim.get('best') or {}
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        paper = rs._prime.clean_cfg(pr.get('cfg') or {})
        real = rs._prime.clean_cfg(pr['realCfg']) if isinstance(pr.get('realCfg'), dict) and pr.get('realCfg') else None
        prev = sim.get('prevBest') or {}
        pp = rs._brain_patch(paper, s24, best, prev)
        rp = rs._brain_patch(real, s24, best, prev, owner_set=pr.get('realOwnerSet')) if real else {}
        if not pp and not rp:
            return None
        if pp:
            pr['cfg'] = rs._prime.clean_cfg({**paper, **pp})
        if rp:
            pr['realCfg'] = rs._prime.clean_cfg({**real, **rp})
        for c in (pr.get('cards') or {}).values():
            patch = (rp if real else pp) if c.get('real') else pp
            if patch:
                why = ' · '.join(f'{k} → {v}' for k, v in patch.items())
                c.setdefault('events', []).append({'at': now, 'kind': 'brain', 'why': f'🧠 engine self-fix from {s24.get("n", 0)} sims: {why}'})
        rs._json_save(rs.FUSE_HQ_PATH, d)
    ad = rs._admin_load(); rs._audit(ad, 'engine', 'self-fix', rs.json.dumps({'paper': pp, 'real': rp})); rs._admin_save(ad)
    return {**pp, **({'real': rp} if rp else {})}


def _verdict_acts(r):
    rs = _rs()
    a = r.get('area') or ''
    if a == '🧠 Sim config' and r['name'].split(' = ')[0] in {rs._verdict.TRAIT_WORDS.get(k, k) for k in rs.SIM_KEYS}:
        return [['apply-one', '🃏 One card'], ['apply-real', '💵 Real card']] if r['verdict'] != 'scrap' else []   # every card keeps its OWN config — never all at once
    if a == '🏟 Strategy':
        return [['scrap', '🗑 Scrap']] if r['verdict'] != 'keep' else [['keep', '📌 Keep on rails']]
    if a == '🎚 Engine dial' and r['verdict'] == 'keep':
        return [['apply', '🎚 Use this dial']]
    if a == '⭐ Tier card' and r['verdict'] == 'scrap':
        return [['redeal', '🃏 Re-deal fresh']]
    return []


def _retired(board):
    """☠ Retired strategies = proven losers + the ones HQ scrapped from the verdict, minus the ones HQ chose to keep."""
    rs = _rs()
    d = rs._json_load(rs.FUSE_HQ_PATH, {})
    return (rs._hq.retired_styles(board) | set(d.get('scrappedStyles') or [])) - set(d.get('keptStyles') or [])


async def _verdict_build(real=True):
    rs = _rs()
    now = rs.time.time()
    d = rs._json_load(rs.FUSE_HQ_PATH, {}); rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': [], 'paths': {}}); sim = rs._json_load(rs.PG_SIM_PATH, {})
    lg = rs._store.Ledger(rs.CARD_RECORDS_PATH, table='runs')
    tiers = {}
    for tpl, t in rs._prime.TEMPLATES.items():
        rows = [r for r in lg.rows(limit=500, card=tpl) if not r.get('real')]
        tiers[tpl] = {'label': t.get('label') or tpl, 'pcts': [rs._fuse._f(r.get('pct')) for r in rows]}
    board = rs._hq.arena_board([rs._hq.arena_value(e, {}, now) for e in d.get('arena') or []])
    cfg_ = rs._runner_cfg()
    lanes, dials = await rs.asyncio.to_thread(lambda: (rs._rn.lane_proofs(rd.get('rounds') or [], rd.get('paths') or {}, now, cfg_), {w: rs._rn.dial_proof(rd.get('rounds') or [], rd.get('paths') or {}, now, rs._hq.RISK_DIALS, window=sec) for w, sec in rs._rn.PROOF_WINDOWS.items()}))   # ⚙ off the loop
    try:
        reals = await rs._fw_reports('') if real else []
    except Exception:
        reals = []
    out = rs._verdict.build(tiers, board, lanes, dials, sim.get('score'), (rd.get('pgBattle') or {}).get('clockStats'), reals)
    for r in out['rows']:
        r['acts'] = rs._verdict_acts(r)
    scr = set(d.get('scrappedStyles') or []); kept = set(d.get('keptStyles') or [])
    for r in out['rows']:
        if r['area'] == '🏟 Strategy':
            r['state'] = 'scrapped' if r['name'] in scr else 'kept' if r['name'] in kept else None
    return {**out, 'at': now}


async def _verdict_tick(now):
    """🧾 Hourly: Fuse always runs what's-working-what's-not. A row that turns ✅ or ❌ (with enough samples) → owner inbox once."""
    rs = _rs()
    prev = rs._json_load(rs.VERDICT_PATH, {})
    out = await rs._verdict_build(real=True)
    before = {f"{r['area']}|{r['name']}": r['verdict'] for r in prev.get('rows') or []}
    flips = [r for r in out['rows'] if r['verdict'] in ('keep', 'scrap') and before.get(f"{r['area']}|{r['name']}") not in (None, r['verdict'])]
    hist = ((prev.get('history') or []) + [{'at': now, 'keep': out['keep'], 'scrap': out['scrap'], 'watch': out['watch']}])[-96:]
    rs._json_save(rs.VERDICT_PATH, {**out, 'history': hist})
    # 🗑 QUICK SCRAP (owner, 2026-10-06: "auto strengthened and quick scrap"): a STRATEGY the verdict marks ❌ on its own record leaves
    # the trader rails at once — no click. 📌 a strategy the owner chose to KEEP is never touched, and one that turns ✅ again comes
    # back by itself. Every move is audited + told to the owner once. (Cards, dials and real money are still the owner's click.)
    try:
        async with rs._admin_lock:
            dq = rs._json_load(rs.FUSE_HQ_PATH, {})
            if dq.get('autoScrap', True):
                scr = set(dq.get('scrappedStyles') or []); kept = set(dq.get('keptStyles') or []); auto_ = set(dq.get('autoScrapped') or [])
                bad = {r['name'] for r in out['rows'] if r['area'] == '🏟 Strategy' and r['verdict'] == 'scrap'} - kept
                good = {r['name'] for r in out['rows'] if r['area'] == '🏟 Strategy' and r['verdict'] == 'keep'}
                new_out, back_in = bad - scr, (auto_ & scr) & good
                if new_out or back_in:
                    scr = (scr | new_out) - back_in; auto_ = (auto_ | new_out) - back_in
                    dq['scrappedStyles'], dq['autoScrapped'] = sorted(scr), sorted(auto_)
                    rs._json_save(rs.FUSE_HQ_PATH, dq)
                    ad_ = rs._admin_load(); rs._audit(ad_, 'engine-auto', 'fuse-auto-scrap', f"scrapped {sorted(new_out)} · restored {sorted(back_in)}"[:200]); rs._admin_save(ad_)
                    for w in rs._owner_wallets():
                        rs.notify(w, 'admin', '🗑 Fuse auto-scrap: ' + ' · '.join(([f"off the rails: {', '.join(sorted(new_out))}"] if new_out else []) + ([f"back on: {', '.join(sorted(back_in))}"] if back_in else []))
                               + ' — 📌 Keep in HQ › Fuse overrides it.', url='/terminal/hq?tab=fuse', push=False, once=f"autoscrap-{int(now // 3600)}", meta={'claim': 'Fuse verdict (own records)', 'source': 'auto-scrap'})
    except Exception as e:
        print('auto scrap:', e)
    for r in flips[:6]:
        for w in rs._owner_wallets():
            rs.notify(w, 'admin', f"🧾 Fuse verdict: {r['area']} {r['name']} is now {'✅ working' if r['verdict'] == 'keep' else '❌ not working'} — one click in HQ › Fuse to act on it.",
                   url='/terminal/hq?tab=fuse', push=False, once=f"verdict-{r['area']}-{r['name']}-{r['verdict']}-{int(now // 86400)}", meta={'claim': r['why'], 'source': 'Fuse verdict (own records)'})
    return len(flips)

