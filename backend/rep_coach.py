"""🧹 Lifecycle, shadows, owner book, coach, regret, lab, seats — split out of rep_ai.py by scripts/split-module.py (owner 2026-11-17 cleanup); first moved whole out of reputation_service.py.
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


def _lc_book(now=None):
    """The ONE lifecycle book. First run: the two old books (the four desks' gen / born / lineage, the office desks' + their tunables) are
    migrated into it once; after that nothing else holds a generation."""
    rs = _rs()
    if rs._lc_mem['book'] is None:
        b = rs._json_load(rs.LIFECYCLE_PATH, {}) or {}
        if not b.get('roles'):
            b = rs._tkl.new_book(now or rs.time.time(), rs._agents_mem.get() or {}, rs._json_load(rs.OFFICE_PATH, {}) or {})
        rs._lc_mem['book'] = rs._tkl.ensure(b, now or rs.time.time())
    return rs._lc_mem['book']


def _lc_shadows():
    """Cached 5 min (two callers a pass replayed every real exit twice — the loop-lag catcher's 'reaper_replay' culprit)."""
    rs = _rs()
    if rs._lc_sh_memo and rs.time.time() - rs._lc_sh_memo.get('at', 0) < 300:
        return rs._lc_sh_memo['v']
    v = rs._lc_shadows_raw()
    rs._lc_sh_memo.update(at=rs.time.time(), v=v)
    return v


def _lc_shadows_raw():
    """The replaced Reaper generation vs its successor on the SAME real exits since the switch (its price rules replayed with each lesson)."""
    rs = _rs()
    out = {}
    try:
        x_ = next((x for x in reversed(rs._lc_book().get('lineage') or []) if x.get('role') == 'reaper' and x.get('status') == 'SHADOW'), None)
        if x_:
            of_ = rs._office_state()
            pos_ = (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or []
            take_ = rs._of.take_line(((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}), rs._agents.get('scalp'))
            old_ = {k_: rs._of.tune({'tune': {'reaper': x_.get('lesson') or {}}}, 'reaper', k_) for k_ in rs._of.TUNABLE['reaper']}
            out['reaper'] = rs._gen.shadow_record(pos_, old_, rs._of.tunes(of_, 'reaper'), rs._fuse._f(x_.get('retiredAt')), take_, rs._of.reaper_replay)
    except Exception as e:
        print('lifecycle shadow:', str(e)[:100])
    return out


def _evo_view(role='reaper', now=None):
    """🧪 One Evolution Lab pass on Reaper's REAL closed exits: frozen baseline vs a challenger fit on the oldest 60%, judged on the newest
    40%, gated, with its shadow trades and generation history. A new pass is appended only when new exits arrived; cached 10 min."""
    rs = _rs()
    now = now or rs.time.time()
    if rs._evo_memo.get('at', 0) > now - 600 and rs._evo_memo.get('v'):
        return rs._evo_memo['v']
    led = rs._json_load(rs.EVO_PATH, {}).get(role) or []
    pos_ = [p for p in (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or [] if p.get('path')]
    take_ = rs._of.take_line(((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}), None)
    base_ = rs._evo.baseline(led)
    current_ = {k: v[0] for k, v in rs._of.TUNABLE[role].items()} if not base_ else base_['params']
    last_ = next((e for e in reversed(led) if e.get('action') == 'challenge'), None)
    if not last_ or (last_.get('held') or {}).get('n', 0) + (last_.get('learn') or {}).get('n', 0) != len(pos_):
        j = rs._evo.run(led, role, current_, rs._of.TUNABLE[role], pos_, rs._of.reaper_replay, take_, now)
        book_ = rs._json_load(rs.EVO_PATH, {}); book_[role] = led; rs._json_save(rs.EVO_PATH, book_)
    else:
        j = rs._evo.judge(current_, last_['params'], pos_, rs._of.reaper_replay, take_)
    base_ = rs._evo.baseline(led)
    v = {'role': role, 'baseline': base_, 'judge': j, 'history': rs._evo.history(led), 'exits': len(pos_), 'take': take_,
         'gate': {'heldFrac': rs._evo.HELD_FRAC, 'minHeld': rs._evo.MIN_HELD, 'minChanged': rs._evo.MIN_CHANGED, 'edgePts': rs._evo.EDGE_PTS},
         'live': {k: v_[0] for k, v_ in rs._of.TUNABLE[role].items()}, 'note': 'The lab keeps its own ledger. Applying a promoted generation to live trading is the owner\'s call.'}
    rs._evo_memo.update(at=now, v=v)
    return v


def _lifecycle(now):
    """🧬 The page's per-role view of the ONE book: the generation in control + the ones it replaced (SHADOW 24h, then RETIRED)."""
    rs = _rs()
    gens = rs._tkl.generations(rs._lc_book(now), now, rs._lc_shadows())
    return {g['role']: {'active': {'gen': g['generation'], 'since': g['bornAt'], 'status': g['status'], 'why': g.get('why'), 'net': g.get('net'), 'lesson': g.get('lessonVector')}, 'past': g['lineage']} for g in gens}


def _lc_evaluate(of, arch, cour, now):
    """🧬 ONE evaluation of all ten roles on the Judge's reviews of REAL exits (the only evidence). A replaced office desk's new lesson is
    written to its tunables on this same call; a brain-side role's lesson is read by the kernel on its next judgement. → (office state, events)"""
    rs = _rs()
    reviews = ((of.get('judge') or {}).get('reviews')) or []
    integrity = {'courier': int((cour or {}).get('duplicates') or 0) + int((cour or {}).get('unsigned') or 0), 'archivist': int(rs._arch_verify(arch) or 0), 'judge': 0}
    book, ev = rs._tkl.evaluate(rs._lc_book(now), reviews, now, tunable=rs._of.TUNABLE, integrity=integrity, desk_stats=rs._jr.desk_stats(reviews))
    book, tune_ = rs._tkl.sync_office(book, of.get('tune'), {e_['role'] for e_ in ev if e_['kind'] == 'replaced'})
    rs._lc_mem['book'] = book
    rs._json_save(rs.LIFECYCLE_PATH, book)
    return {**of, 'tune': tune_}, ev


def _rounds_state():
    rs = _rs()
    if rs._rounds['state'] is None:
        rs._rounds['state'] = rs._json_load(rs.ROUNDS_PATH, {}) or {}
    return rs._rounds['state']


def _judge_weights(now):
    """🧠 The Judge's evidence weights per mint (real-money memory → ×0.7 … ×1.3; only while the memory proves itself) × 🧪 the rule lab's live
    rules (each passed its own walk-forward on real fills, or named a repeat real loss) — a weight, never a veto."""
    rs = _rs()
    mem = rs._real_mem(now) or {}
    lab_ = rs._lab_state()
    if not mem.get('proof', {}).get('ok'):
        w = {}
        for x_ in rs._agents.get('table') or []:
            f_ = rs._rlab.weight(lab_, rs._rlab.row_feats(x_))
            if f_ != 1.0:
                w[x_.get('mint')] = f_
        return w
    w = {}
    srec_ = rs._co.source_record((rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions'))
    for x_ in rs._agents.get('table') or []:
        ch_ = x_.get('chart') or {}
        est_, _c = rs._rm.estimate(mem, rs._rm.feats(ch_.get('state'), (ch_.get('entry') or [None, None])[1] if len(ch_.get('entry') or []) > 1 else None, '', (x_.get('li') or {}).get('phase'), (x_.get('li') or {}).get('cls'), (x_.get('vitals') or {}).get('ageH')))
        w[x_.get('mint')] = 1 + (rs._fuse._f(est_) - rs._rm.veto_of(mem)) / 40   # against the LINE (the median of our own real trades): the worse half ranks down to ×0.7, the better half up to ×1.3 — a seat is never left empty for it
        w[x_.get('mint')] = max(0.7, min(1.3, w[x_.get('mint')])) * rs._co.source_factor(srec_, x_.get('src'))   # 📏 … and every source that listed it is a proven loser on REAL fills → ×0.9
        w[x_.get('mint')] *= rs._rlab.weight(lab_, rs._rlab.row_feats(x_))   # 🧪 … and the lab's live rules it matches
    return w


def _paper_view(st, paper, rcfg, now):
    """📝 The page's practice-desk payload (board rows, feed, records). Every row carries the KERNEL's decision as `k` — the one meaning of a
    coin's state the page shows (READY · CONTENDING · TRACKING · HELD, Devil's graded evidence, the Warden's size)."""
    rs = _rs()
    v = rs._pd.view(st, paper or [], bool(rcfg.get('agentFeed')), rs._agents_real(), rs._agents.get('mind'), rcfg, rs._agents.get('decisions'), now, rs._agents.get('card'), rs._agents.get('money'))
    try:
        for x_ in v.get('table') or []:
            d_ = rs._tk.KERNEL.dec.get(x_.get('mint'))
            if d_:
                op_ = d_['opinions']
                x_['k'] = {'status': d_['status'], 'rank': d_['rank'], 'why': str(d_['why'])[:140], 'trigger': op_['trigger']['state'], 'narrative': op_['trigger']['narrative'],
                           'devil': [[o, sv, str(w)[:90]] for o, sv, w in op_['devil']['objections']][:4], 'hard': bool(op_['devil']['hard']), 'size': op_['warden']['size'],
                           'unknown': op_['sherlock']['unknown'], 'courier': bool(op_['courier']['ok'])}
    except Exception as e:
        print('paper view:', str(e)[:120])
    return v


def _kernel_view(now):
    """The kernel's bounded view for the page + each candidate's EVIDENCE state from the scan scheduler (FRESH · STALE · PENDING ·
    RATE_LIMITED · UNAVAILABLE — a state of the evidence, never a verdict on the coin)."""
    rs = _rs()
    v = rs._tk.KERNEL.view(now)
    for c_ in v.get('candidates') or []:
        c_['scan'] = rs._ENRICH.status(c_['mint'], now)
    try:   # 📏 order → fill, timed from the keeper's own ledger rows (the truth of a fill)
        tid_ = rs._office.get('tid')
        ev_ = (rs._prime_cards().get(tid_ or '') or {}).get('events') or []
        v['metrics']['execution'] = rs._tkm.execution(rs._office_ledger(), ev_, tid_, now)
    except Exception as e:
        print('exec timings:', str(e)[:100])
    return v


def _edge_rules():
    """The rules a 🧪 PICK may match: only while the proof gate reads TRADE (enough coins judged AND a rule held on unseen coins)."""
    rs = _rs()
    a_ = rs._json_load(rs.EDGE_AUDIT_PATH, {}) or {}
    return list(a_.get('rules') or []) if a_.get('gate') == 'trade' else []


def _edge_view():
    """🧪 A06 for the Agents tab: is the PICK on, the proof gate's verdict and the proven rules a pick can match (best first)."""
    rs = _rs()
    a_ = rs._json_load(rs.EDGE_AUDIT_PATH, {}) or {}
    on_ = ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}).get('edgePick', True)
    rc_ = (rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}
    return {'on': bool(on_), 'young': bool(rc_.get('pickYoung', False)), 'seatPicksOnly': bool(rc_.get('aiSeatPicksOnly', True)), 'minAgeMin': round(rs._uni.min_age() * 60), 'gate': a_.get('gate') or 'wait', 'held': int(a_.get('held') or 0), 'tested': int(a_.get('tested') or 0),
            'rules': [{'rule': ' + '.join(r_.get('rule') or []), 'med': r_.get('med'), 'n': r_.get('n'), 'up': r_.get('up')} for r_ in (a_.get('rules') or [])[:6]]}


def _kernel_ctx(now):
    """The small context the ten agents read: held positions (entry · peak · Reaper's stop) · the weather · execution health · the Judge's weights."""
    rs = _rs()
    pos = rs._office.get('pos') or {}
    held = {l.get('mint'): {'entry': rs._fuse._f(l.get('entry')), 'peak': rs._fuse._f((pos.get(l.get('mint')) or {}).get('peak')), 'stopNow': (pos.get(l.get('mint')) or {}).get('stopNow')}
            for l in ((rs._prime_cards().get(rs._office.get('tid') or '') or {}).get('legs') or [])
            if l.get('mint') and not l.get('placeholder') and rs._fuse._f(l.get('units')) > 0}
    rd = rs._office.get('ready') or {}
    legs_ = ((rs._prime_cards().get(rs._office.get('tid') or '') or {}).get('legs') or [])
    pending = {l.get('mint') for l in legs_ if l.get('mint') and not l.get('placeholder') and rs._fuse._f(l.get('units')) <= 0}   # a seat the keeper is still buying
    return {'held': held, 'pending': pending, 'regime': (rs._agents.get('weather') or {}).get('regime'), 'courier': (rs._office.get('courier') or {}).get('health'),
            'live': rd.get('live') if rd else None, 'weights': rs._judge_weights(now), 'aiw': rs._ai_weights(now), 'pens': rs._coach_pens(now), 'lessons': rs._tkl.lessons(rs._lc_book(now)), 'lab': rs._rlab.trigger_lessons(rs._lab_state()), 'waits': rs._rg.effective(rs._prime.clean_cfg((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}), rs._regret_book()),
            'watchOnly': {m_ for m_ in rs._owner.get('only') or () if rs._tk.KERNEL.owner.get(m_) != 'arm'},   # 👤 review / track only: judged, never READY   # 🧬 only the generations IN CONTROL
            'edgeRules': rs._edge_rules(), 'feats': rs._FEATS, 'surv': rs._SURV, 'now': now,   # 🧪 A06 the PICK (brain.edge_pick)
            'edgePick': ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}).get('edgePick', True),
            'pickYoung': bool(((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}).get('pickYoung', False))}


def _owner_book(now):
    """The owner's list, pruned (a review lasts 30 min, an ARM 6h → then tracked). Loaded once; written only when it changes."""
    rs = _rs()
    if rs._owner['book'] is None:
        rs._owner['book'] = dict((rs._json_load(rs.OWNER_REVIEW_PATH, {}) or {}).get('book') or {})
    b = rs._owr.prune(rs._owner['book'], now)
    if b != rs._owner['book']:
        rs._owner['book'] = b
        rs._json_save(rs.OWNER_REVIEW_PATH, {'book': b, 'at': now})
    return b


def _owner_view(now):
    """The owner's review rows from the kernel's own state (newest first). A coin the kernel has not read yet = RESOLVING."""
    rs = _rs()
    K = rs._tk.KERNEL
    b = rs._owner_book(now)
    return [rs._owr.result(m_, e_, K.store.mints.get(m_), K.dec.get(m_), rs._ENRICH.status(m_, now), now, only=m_ in (rs._owner.get('only') or ()))
            for m_, e_ in sorted(b.items(), key=lambda kv: -rs._fuse._f(kv[1].get('at')))]


async def _owner_resolve(addr):
    """An address from the owner's box → (mint, symbol) or (None, None). A mint FEELESS already knows; a POOL it knows; else ONE Jupiter
    token lookup (it finds a coin by mint or by any of its pools). Never an RPC call, never an arbitrary URL."""
    rs = _rs()
    K = rs._tk.KERNEL
    if addr in K.store.mints:
        return addr, K.store.mints[addr]['identity'].get('symbol')
    for m_, ms_ in K.store.mints.items():
        if ms_['identity'].get('pair') == addr:
            return m_, ms_['identity'].get('symbol')
    for p_ in rs._open_pairs:
        bt_ = p_.get('baseToken') or {}
        if bt_.get('address') == addr or p_.get('pairAddress') == addr:
            return bt_.get('address'), bt_.get('symbol')
    if rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return None, None
    try:
        async with rs.httpx.AsyncClient(timeout=6) as http:
            pr = await rs._launchpad_board.jup_lookup(http, addr)
        bt_ = (pr or {}).get('baseToken') or {}
        return (bt_.get('address'), bt_.get('symbol')) if bt_.get('address') else (None, None)
    except Exception as e:
        print('owner resolve:', str(e)[:100])
        return None, None


async def _owner_act(text, action, now):
    """ONE owner action (REVIEW · TRACK · ARM · IGNORE) on a pasted CA / link → the list. It only edits the owner's list and wakes the
    agents' next pass: no order, no quote, no wallet call — the kernel decides the coin exactly as it decides every other."""
    rs = _rs()
    ref = rs._owr.parse(text)
    if not ref:
        raise ValueError('paste a Solana mint (CA), or a pump.fun / dexscreener.com/solana / birdeye.so token link')
    if action == 'ignore' and ref['address'] in rs._owner_book(now):
        mint, sym = ref['address'], None
    else:
        mint, sym = await rs._owner_resolve(ref['address'])
        if not mint and ref['kind'] == 'mint':
            mint = ref['address']   # a mint from a Pump / Birdeye link: the next agent pass reads it (RESOLVING until then)
    if not mint:
        raise ValueError('no Solana coin found for that address yet — a brand-new mint can take a minute to be indexed')
    b = rs._owr.apply(rs._owner_book(now), mint, action, now, sym, ref['source'])
    rs._owner['book'] = b
    rs._json_save(rs.OWNER_REVIEW_PATH, {'book': b, 'at': now})
    rs._tk.KERNEL.owner = rs._owr.modes(b, now)
    rs._tk.KERNEL.note('owner', action.upper(), {'review': 'sent through the normal agent review', 'track': 'kept on the owner\'s list', 'arm': 'owner priority — it still has to be READY on its own and pass every execution check',
                                              'ignore': 'off the owner\'s list'}[action], now, mint=mint, key=f'{action}:{int(now)}')
    try:   # audited like every owner action (this call had the wrong arguments: every REVIEW / TRACK / ARM / IGNORE answered 500 after it had already saved)
        ad_ = rs._admin_load(); rs._audit(ad_, 'owner', 'owner-review', f"{action} {mint} via {ref['source']}"); rs._admin_save(ad_)
    except Exception as e:
        print('owner-review audit:', str(e)[:120])
    if action != 'ignore':
        rs._agents['wake'] = now   # the agents read it on their next pass (≤ a few seconds), not at the clock
    rs._tape_flush(now)
    return mint


def _tape_flush(now):
    """📡 New decision-tape rows + the owner's list → the hub (one event per REAL decision; nothing is sent when nothing happened)."""
    rs = _rs()
    try:
        H, T = rs._tke.HUB, rs._tk.KERNEL.tape
        for r_ in T.since(rs._tape_seen['hub']):
            H.publish('decision', str(r_['id']), r_, now, track=False)
            rs._tape_seen['hub'] = r_['id']
        H.publish('owner_update', 'owner', rs._owner_view(now), now)
    except Exception as e:
        print('tape flush:', str(e)[:120])


def _tape_ledger(now):
    """📮 Courier's lines on the tape = the keeper's OWN ledger rows for the real card (sent → confirmed fill / failed / refused). The
    ledger is the truth of a fill; this only reads it."""
    rs = _rs()
    try:
        tid_ = rs._office.get('tid')
        since_ = rs._tape_seen['ledger'] or (now - 900)
        new_ = [r_ for r_ in rs._office_ledger(200) if r_.get('side') in ('buy', 'sell') and (not tid_ or r_.get('card') == tid_) and rs._fuse._f(r_.get('at')) > since_]
        for r_ in new_:
            st_ = 'FILLED' if rs._of.confirmed(r_) else 'FAILED' if r_.get('status') == 'failed' else 'REFUSED' if r_.get('status') == 'skipped' else str(r_.get('status') or '').upper()
            if st_ not in ('FILLED', 'FAILED', 'REFUSED'):
                continue
            usd_ = rs._fuse._f(r_.get('usd'))
            why_ = (f"${usd_:.2f}" + (f" · landed in {rs._fuse._f(r_.get('landSec')):.0f}s" if r_.get('landSec') is not None else '')) if st_ == 'FILLED' else str(r_.get('err') or r_.get('why') or '')[:120]
            rs._tk.KERNEL.note('courier', f"{st_} {str(r_.get('side')).upper()}", why_, rs._fuse._f(r_.get('at')) or now, mint=r_.get('mint'), px=rs._fuse._f(r_.get('px')) or None,
                            result={'state': st_.lower(), 'usd': round(usd_, 4), 'sig': r_.get('sig') if st_ == 'FILLED' else None, 'side': r_.get('side')}, key=f"{r_.get('sig') or r_.get('id') or r_.get('at')}:{st_}")
            rs._tape_seen['ledger'] = max(rs._tape_seen['ledger'], rs._fuse._f(r_.get('at')))
        if not rs._tape_seen['ledger']:
            rs._tape_seen['ledger'] = now - 900
    except Exception as e:
        print('tape ledger:', str(e)[:120])


def _tape_reaper(reports, now):
    """☠ Reaper's lines = its ruling on each open position, written when the ruling CHANGES (HOLD → PROTECT → TAKE / EXIT)."""
    rs = _rs()
    try:
        for r_ in reports or []:
            m_ = r_.get('mint')
            dec_ = r_.get('decision') or r_.get('state')
            if not m_ or not dec_:
                continue
            rs._tk.KERNEL.note('reaper', dec_, f"{r_.get('rule') or ''} — {str(r_.get('evidence') or '')[:110]}".strip(' —'), now, mint=m_, px=rs._fuse._f(r_.get('px')) or None,
                            result={'pct': r_.get('pct')}, key=f"{dec_}:{r_.get('rule')}")
    except Exception as e:
        print('tape reaper:', str(e)[:120])


def _kernel_pass(table, now):
    """⚙ The sensed rows → the kernel (only changed mints re-judged) → the ONE enrichment scheduler. Sherlock's evidence requests are
    queued by what the kernel is doing with each coin: HELD first, then READY, then the coin each hunter lane is watching, then the top
    contenders, then fast new movers — nothing else is asked for here, and no agent fetches for itself. A coin whose scan is pending,
    rate-limited or unavailable stays exactly where its rank puts it."""
    rs = _rs()
    rs._tk.KERNEL.owner = rs._owr.modes(rs._owner_book(now), now)
    try:
        rs._surv.observe(rs._SURV, table, now)   # ⏱ NSFA: every sensed coin's 1 / 5 / 15-min survival
        for r_ in table or []:   # 🧪 each coin's audit tags (trench_brain.feats) — the Warden checks them against the proven-edge rules
            if r_.get('mint'):
                rs._FEATS[r_['mint']] = rs._tb.feats(rs._sn.audit_row(r_))   # the flat shape the audit learned on (the nested row tagged almost nothing)
        if len(rs._FEATS) > 4000:
            for k_ in list(rs._FEATS)[:len(rs._FEATS) - 3000]:
                rs._FEATS.pop(k_, None)
    except Exception as e_:
        print(f'[survival] {e_}')
    rs._taught_stamp(table, now)
    for r_ in table or []:   # 📊 a reliable token supply (our own holder scan read it from the chain) rides on the row → the MintState's supply
        if r_.get('mint') and not r_.get('supply'):
            s_ = rs._fuse._f((rs._intel_cache.get(r_['mint']) or (0, {}))[1].get('supply')) if isinstance(rs._intel_cache.get(r_['mint']), (tuple, list)) else 0
            if s_ > 0:
                r_['supply'] = s_
    ctx = rs._kernel_ctx(now)
    ev = rs._tk.KERNEL.run(table, now, ctx, source='desk')
    K, P = rs._tk.KERNEL, rs._enr.PRIO
    want = {}   # mint → (priority, why): the most important reason wins
    def ask(m_, p_, why_):
        if m_ and (m_ not in want or p_ < want[m_][0]):
            want[m_] = (p_, why_)
    for m_ in (ctx.get('held') or {}):
        ask(m_, P['HELD'], 'held')
    for m_, _d in K.ready(n=rs.ENRICH_TOP):
        ask(m_, P['READY'], 'ready')
    for l_ in K.lanes:
        if l_.get('mint') and l_.get('state') != 'HELD':
            ask(l_['mint'], P['ARMED'], 'hunter lane')
    for m_, mode_ in K.owner.items():   # 👤 the owner asked: its research is queued ahead of the pack (an armed coin with the READY ones)
        if m_ in K.store.mints:
            ask(m_, P['READY'] if mode_ == 'arm' else P['LOOK'], f'owner {mode_}')
    cont_ = sorted(((m_, d_) for m_, d_ in K.dec.items() if d_['status'] == 'CONTENDING' and m_ in K.store.mints), key=lambda kv: -kv[1]['rank'])
    for m_, _d in cont_[:rs.ENRICH_TOP]:
        ask(m_, P['CONTENDING'], 'top contender')
    for m_ in [m_ for m_, e_ in ev.items() if 'new' in e_ and (K.dec.get(m_) or {}).get('status') in ('READY', 'CONTENDING')][:rs.ENRICH_MOVERS]:
        ask(m_, P['MOVER'], 'new mover')
    asked = 0
    for m_, (p_, why_) in want.items():
        d_ = K.dec.get(m_) or {}
        op_ = d_.get('opinions') or {}
        if p_ > P['HELD'] and 'holders' not in ((op_.get('sherlock') or {}).get('requests') or []) and rs._intel_fresh(m_, p_) is not None:
            continue   # Sherlock has what he asked for and it is still fresh
        rs.asyncio.ensure_future(rs._runner_intel(m_, p_, why_, wait=False)); asked += 1
    em_ = rs._ENRICH.metrics(now)
    rs._office['enrich'] = {'at': now, 'asked': asked, 'holderInflight': em_['inflight'], 'tier0': len(K.store.mints), 'queue': em_['queueDepth'], **em_}


def _rounds_pass(table, now):
    """⏱ One round step over the desk's live table (CURRENT rows only): hard safety → REJECT now; tier + score + trench phase per read;
    round 3 decides. Each decision is also noted in the shadow book (its own group), so whether patience helped is measured, not assumed."""
    rs = _rs()
    held = {x_.get('mint') for x_ in ((rs._agents.get('card') or {}).get('seats') or []) if x_.get('mint')}
    rows = [x_ for x_ in table or [] if x_.get('mint') and not rs._fw.dollar_named(x_.get('symbol'))]
    hard, tiers, phases = {}, {}, {}
    for x_ in rows:
        h_ = rs._opp.hard_fail(x_)
        if h_:
            hard[x_['mint']] = h_; continue
        s_, _p = rs._opp.score(x_)
        tiers[x_['mint']] = (rs._opp.tier_of(s_), s_)
        phases[x_['mint']] = x_.get('mp')
    st = rs._tr.step(rs._rounds_state(), rows, now, hard, tiers, phases, held)
    # 📄 (2026-10-13) the round decisions are no longer paper rows: the paper book holds ONE entry per CONFIRMED real buy + its controls
    # (`_shadow_real_buys`) — paper and real money now grade the same trades, 1 : 1
    rs._rounds['state'] = st
    rs._json_save(rs.ROUNDS_PATH, st)


def _shadow_cost(now):
    """The round trip a $0.10 agent seat REALLY pays, from the card's own recent filled buys: the sell-back loss quoted at the buy + the
    network fee both ways as a share of the order. Re-measured every 10 min; never a constant guess."""
    rs = _rs()
    if rs._shadow['cost'] is None or now - rs._shadow['costAt'] > 600:
        try:
            rows = [r for r in rs._fw_full_ledger()[-600:] if r.get('side') == 'buy' and r.get('status') == 'filled' and rs._fuse._f(r.get('usd')) > 0]
            rt = [abs(rs._fuse._f(r.get('sellBackPct'))) for r in rows if r.get('sellBackPct') is not None]
            fee = [2 * rs._fuse._f(r.get('feeUsd')) / rs._fuse._f(r['usd']) * 100 for r in rows if r.get('feeUsd') is not None]
            rs._shadow['cost'] = round((rs._st_med(rt) if rt else 2.3) + (rs._st_med(fee) if fee else 1.0), 3)
            rs._shadow['rt'] = round(rs._st_med(rt), 3) if rt else 2.3
            rs._shadow['feeUsd'] = round(rs._st_med([rs._fuse._f(r.get('feeUsd')) for r in rows if r.get('feeUsd') is not None]), 6) if rows else 0.0
        except Exception as e:
            print('shadow cost:', str(e)[:100]); rs._shadow['cost'] = rs._shadow['cost'] or 3.3
        rs._shadow['costAt'] = now
    return rs._shadow['cost']


def _st_med(v):
    v = sorted(v); n = len(v)
    return (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2) if n else 0.0


def _shadow_book():
    rs = _rs()
    if rs._shadow['book'] is None:
        rs._shadow['book'] = rs._json_load(rs.SHADOW_PATH, {}) or {}
    return rs._shadow['book']


def _shadow_px(row):
    rs = _rs()
    return rs._fuse._f(row.get('px')) or rs._fuse._f((rs._jup_px_cache.get(row.get('mint')) or (0, 0))[1])


def _shadow_note(row, kind, now, card=None):
    """📄 One paper decision at the live price of the decision moment."""
    rs = _rs()
    try:
        if row:
            rs._shadow['book'] = rs._sb.note(rs._shadow_book(), row, kind, now, rs._shadow_px(row), rs._shadow_cost(now)); rs._shadow['dirty'] = True
    except Exception as e:
        print('shadow note:', str(e)[:100])


def _shadow_controls(chosen, pool, cases, now):
    """🎲 The control group of the same moment: best not chosen · random eligible · a WAIT coin."""
    rs = _rs()
    try:
        if not chosen:
            return
        waits = [c_.get('row') or c_ for c_ in cases or [] if not c_.get('cleared')]
        for g_, r_ in rs._sb.controls(chosen, pool, waits, now).items():
            rs._shadow['book'] = rs._sb.note(rs._shadow_book(), r_, g_, now, rs._shadow_px(r_), rs._shadow_cost(now))
        rs._shadow['dirty'] = True
    except Exception as e:
        print('shadow controls:', str(e)[:100])


def _shadow_real_buys(now):
    """📄 PAPER = EVERY CONFIRMED REAL BUY, 1 : 1 (owner, 2026-10-13: "paper should only be with each confirmed buy to tighten paper to real
    money ratio"). Each FILLED agent buy on the ledger becomes ONE paper entry at the market price of its decision (`midPx`), carrying
    the price it really filled at (`real`) — so the book says what the fill cost on top of the paper model — plus the control picks of
    that same moment (best not chosen · random eligible · a WAIT coin): did the agents beat a random coin? No model, no fetch, no quote:
    the ledger rows already in memory + this pass's desk rows."""
    rs = _rs()
    try:
        b = rs._shadow_book()
        since = rs._fuse._f(b.get('buyAt')) or now          # first run: start from now (never a backfill)
        rows = [r for r in rs._fw_full_ledger()[-300:] if r.get('side') == 'buy' and r.get('status') == 'filled' and r.get('agent') and r.get('sig')
                and rs._fuse._f(r.get('confirmedAt') or r.get('at')) > since]
        b['buyAt'] = max([since] + [rs._fuse._f(r.get('confirmedAt') or r.get('at')) for r in rows])
        if not rows:
            rs._shadow['book'] = b
            return 0
        by_ = {x_.get('mint'): x_ for x_ in rs._agents.get('table') or []}
        cases_ = rs._tk.KERNEL.cases()
        chosen = []
        for r in rows:
            row_ = {**(by_.get(r['mint']) or {'mint': r['mint'], 'symbol': r.get('symbol')}), 'go': True}
            px_ = rs._fuse._f(r.get('midPx')) or rs._fuse._f(r.get('px'))
            n0 = len(b.get('rows') or [])
            b = rs._sb.note(b, row_, 'fill', now, px_, rs._shadow_cost(now))
            if len(b.get('rows') or []) > n0:
                b['rows'][-1].update(real=rs._fuse._f(r.get('px')) or None, usd=rs._fuse._f(r.get('usd')) or None, sig=str(r.get('sig'))[:12])
                chosen.append(row_)
        if chosen:
            waits = [c_.get('row') or c_ for c_ in cases_ if not c_.get('cleared')]
            for g_, r_ in rs._sb.controls(chosen, [c_['row'] for c_ in cases_ if c_.get('row') and c_['status'] in ('READY', 'CONTENDING')][:12], waits, now).items():
                b = rs._sb.note(b, r_, g_, now, rs._shadow_px(r_), rs._shadow_cost(now))
        rs._shadow['book'] = b; rs._shadow['dirty'] = True
        return len(chosen)
    except Exception as e:
        print('shadow real buys:', str(e)[:120])
        return 0


async def _shadow_settle(now):
    """Grade open shadow rows with the live chart price (one local batched call) and save when anything changed."""
    rs = _rs()
    b = rs._shadow_book()
    ms = rs._sb.due(b, now)
    if ms:
        px = {}
        for i in range(0, len(ms), 60):
            px.update(await rs._live_px(ms[i:i + 60]))
        rs._shadow['book'] = rs._sb.settle(b, px, now); rs._shadow['dirty'] = True
    if rs._shadow['dirty'] and now - rs._fuse._f(rs._shadow.get('savedAt')) >= rs.SHADOW_SAVE_SEC:   # 💾 ≤ once a minute (it was every pass)
        rs._shadow_flush(now)


def _shadow_flush(now=None):
    rs = _rs()
    if not rs._shadow.get('dirty') or rs._shadow.get('book') is None:
        return
    rs._shadow['book']['report'] = rs._sb.report(rs._shadow['book']); rs._shadow['book']['verdict'] = rs._sb.verdict(rs._shadow['book']['report'])
    rs._json_save(rs.SHADOW_PATH, rs._shadow['book']); rs._shadow['dirty'] = False; rs._shadow['savedAt'] = rs.time.time() if now is None else now


def _dial_lab(now):
    """🎚 what each dial would have bought, replayed on the agents' own judged calls (paper_desk.dial_replay) — rebuilt once a minute."""
    rs = _rs()
    if now - rs._dial_mem['at'] >= 60:
        try:
            rs._dial_mem.update(at=now, v=rs._pd.dial_replay(rs._agents_mem.get().get('done') or []))
        except Exception as e:
            print('dial lab:', str(e)[:80]); rs._dial_mem['at'] = now
    return rs._dial_mem['v']


def _desk_stats_view(now):
    """👨‍⚖️ the desks' records for the page + the model: the Judge's team record (`desk_stats`) + each entry desk's OWN vote on real money
    (`own`, judge_review.desk_votes) + the three desks that never vote on an entry, on their own job: 📮 Courier = sends that landed in the
    last hour · 🗄 Archivist = records filed with no rewrite in the chain. (Owner-approved build b5 / b10: no desk reads UNKNOWN for want of
    a measure, and seven desks no longer share one number.)"""
    rs = _rs()
    out = rs._jr.desk_stats(((rs._office_state().get('judge') or {}).get('reviews')) or [])
    try:
        own = rs._jr.desk_votes(rs._real_trades())
        for d_, r_ in own.items():
            out.setdefault(d_, {})['own'] = r_
        m_ = rs._fw.exec_metrics(rs._fw_peek().get('ledger'), now)
        out['courier'] = {'decisions': m_['sends'], 'accuracy': round(m_['fills'] / m_['sends'] * 100) if m_['sends'] else None, 'kind': 'landed', 'window': 'last hour'}
        arch_ = rs._json_load(rs.ARCHIVE_PATH, {}) or {}
        n_ = len(arch_.get('positions') or []) + len(arch_.get('cases') or [])
        out['archivist'] = {'decisions': n_, 'accuracy': 100 if n_ and not rs._arch_verify(arch_) else (0 if n_ else None), 'kind': 'intact'}
    except Exception as e:
        print('desk stats:', e)
    return out


def _night_check(now):
    """🌙 One look of the night guard (night_guard.py) on the real card's value + its confirmed real exits → True while new buys are paused.
    The owner's inbox hears about each trip once."""
    rs = _rs()
    if rs._night['st'] is None:
        rs._night['st'] = rs._json_load(rs.NIGHT_PATH, {}) or {}
    ex = [{'at': rs._fuse._f(t.get('leftAt') or (t.get('exit') or {}).get('at')), 'pct': t.get('realPct')} for t in (rs._real_trades() or [])[-40:]]
    st, v = rs._ng.step(rs._night['st'], (rs._agents.get('money') or {}).get('value'), ex, now, night=rs._ng.is_night(rs.time.localtime(now).tm_hour))
    rs._night.update(st=st, v=v)
    if v.get('new'):
        rs._json_save(rs.NIGHT_PATH, st)
        for w in rs._owner_wallets():
            rs.notify(w, 'fuse-card', f"🌙 Night guard: new real buys paused {round((v['until'] - now) / 60)} min — {v['why']}. Exits keep running.", url='/terminal/hq?tab=agents',
                   push=True, once=f"night-{int(now)}", meta={'claim': 'Night guard', 'source': 'real card value + confirmed exits'})
    elif int(now) % 300 < 8:
        rs._json_save(rs.NIGHT_PATH, st)
    lt_ = rs.time.localtime(now)
    day_ = rs.time.strftime('%Y-%m-%d', lt_)
    if 8 <= lt_.tm_hour < 12 and st.get('morning') != day_:   # ☀ the overnight report, once a morning (owner's idea #2)
        since_ = rs.time.mktime((lt_.tm_year, lt_.tm_mon, lt_.tm_mday, 20, 0, 0, 0, 0, -1)) - 86400
        ex2 = [{'at': rs._fuse._f(t.get('leftAt') or (t.get('exit') or {}).get('at')), 'pct': t.get('realPct'), 'sym': t.get('sym') or t.get('symbol'),
                'rule': str((t.get('exit') or {}).get('rule') or t.get('rule') or '').split(' ')[0] or None} for t in (rs._real_trades() or [])[-200:]]
        txt_ = rs._ng.morning(ex2, st, since_, now)
        st['morning'] = day_; rs._night['st'] = st; rs._json_save(rs.NIGHT_PATH, st)
        if txt_:
            for w in rs._owner_wallets():
                rs.notify(w, 'fuse-card', txt_, url='/terminal/hq?tab=agents', push=True, once=f"morning-{day_}", meta={'claim': 'Overnight report', 'source': 'confirmed real exits'})
    return bool(v.get('paused'))


def _real_trades():
    """Our confirmed real exits (one per sale), re-read from the archive at most once a minute — for the model's "twins" line."""
    rs = _rs()
    if rs.time.time() - rs._real_tr['at'] > 60:
        rs._real_tr.update(at=rs.time.time(), rows=rs._rm.trades((rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions')))
    return rs._real_tr['rows']


async def _after_step(now):
    """One live-price reading for every exit still being watched (one local batched call; nothing is bought, sold or decided here)."""
    rs = _rs()
    st = rs._after_mem.get()
    ms = rs._ap.mints(st)
    if not ms:
        return
    px = {}
    for i in range(0, min(len(ms), 120), 60):
        px.update(await rs._live_px(ms[i:i + 60]))
    rs._after_mem.put(rs._ap.step(st, px, now), now)


def _trail_view(of, arch, rcfg, scalp):
    """👁 The trail grid on WHOLE moves (path + the 30 min after the sale) + what is in shadow → the page and the model coach."""
    rs = _rs()
    try:
        g = rs._ap.grid((arch or {}).get('positions'), (rs._after_mem.get() or {}).get('done'), rs._of.reaper_replay, rs._of.tunes(of, 'reaper'), rs._of.take_line(rcfg, scalp))
    except Exception as e:
        print('trail grid:', e)
        g = {'n': 0, 'need': rs._ap.MIN_N, 'pays': False}
    try:   # 🟢 b8: green exits by the rule that sold them vs what the live trail would have made on the same whole move
        g['bench'] = rs._ap.rule_bench((arch or {}).get('positions'), (rs._after_mem.get() or {}).get('done'), set(rs._of.SOFT_EXITS) - {'R7'})   # 🪑 R7 (the trail) is what protects the rest — never benched
        rs._of.BENCHED = {r_ for r_, v_ in g['bench'].items() if v_.get('benched')}
        g['byRule'] = rs._ap.by_rule((arch or {}).get('positions'), (rs._after_mem.get() or {}).get('done'), rs._of.reaper_replay, rs._of.tunes(of, 'reaper'), rs._of.take_line(rcfg, scalp))
        g['ruleWords'] = rs._ap.rule_words(g['byRule'])
        g['twin'] = rs._ap.scale_twin((arch or {}).get('positions'), (rs._after_mem.get() or {}).get('done'), rs._of.SCALE_AT, rs._of.tunes(of, 'reaper').get('giveBackPct', 30), frac=rs._of.SCALE_PCT / 100)   # 💰 the scale-out's paper twin
    except Exception as e:
        print('trail by rule:', e)
    sh = next((c for c in ((of or {}).get('candidates') or {}).values() if c.get('status') == 'shadow' and c.get('agent') == 'reaper'), None)
    return {**g, 'words': rs._ap.words(g), 'watching': len((rs._after_mem.get() or {}).get('open') or {}), 'asked': rs._coach.get('tuneSaid'), 'tunes': rs._of.tunes(of, 'reaper'),
            'shadow': None if not sh else {'key': sh['key'], 'value': sh['value'], 'live': sh.get('live'), 'from': (sh.get('evidence') or {}).get('from'), 'why': (sh.get('evidence') or {}).get('why'), **rs._of.evaluate(sh)}}


def _capital_view():
    """💰 The capital desk's read of the agents' own confirmed real exits (capital.py) — what the Warden sizes by, the page shows and the
    model coach is taught. `on` = the owner's switch (realCfg `agentCapital`); off = shown and taught, sizes nothing."""
    rs = _rs()
    rc = rs._prime.clean_cfg((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {})
    try:
        money = rs._agents.get('money') or {}
        hrs = {int(k): rs._fuse._f(x) for k, x in (rs._office_state().get('peaks') or {}).items() if rs.time.time() - int(k) * 3600 <= rs._cap.BRAKE_HOURS * 3600}
        return rs._cap.view(rs._real_trades(), int(rs._fuse._f(rc.get('agentSeats') or rc.get('coins') or 4)) or 4, rc.get('agentCapital'), money.get('value'), max(hrs.values()) if hrs else None)
    except Exception as e:
        print('capital:', e)
        return {'on': False, 'record': {'n': 0}, 'state': 'PROVING', 'mult': None, 'floor': None, 'why': 'no record read', 'leaks': []}


def _real_mem(now):
    """🧠 The real-money memory (`real_memory.build` over the archive's confirmed real exits), rebuilt at most once a minute."""
    rs = _rs()
    if rs._rm_cache['mem'] is None or now - rs._rm_cache['at'] >= 60:
        try:
            rs._rm_cache['mem'] = rs._rm.build((rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions'))
        except Exception as e:
            print('real memory:', str(e)[:120]); rs._rm_cache['mem'] = rs._rm_cache['mem'] or {}
        rs._rm_cache['at'] = now
    return rs._rm_cache['mem']


def _coach_state():
    rs = _rs()
    if rs._coach['s'] is None:
        rs._coach['s'] = rs._json_load(rs.COACH_PATH, None) or rs._co.new_state()
    return rs._coach['s']


def _coach_put(state):
    rs = _rs()
    rs._coach['s'] = state
    rs._json_save(rs.COACH_PATH, state)
    if rs._office.get('payload') is not None:
        rs._office['payload']['coach'] = rs._coach_view(rs.time.time())


def _coach_pens(now):
    """👨‍⚖️ + 👑 every ranking weight the kernel reads this pass: the Judge's repeat-loss causes merged with the coach's live directives."""
    rs = _rs()
    out = rs._co.pens(rs._coach_state(), now, rs._jr.penalties((rs._office.get('court') or {}).get('promoted')))
    for k_, p_ in rs._trl.pens(rs._taught_rules()).items():   # 🎓 your lessons in ⬇ rank / ✋ skip mode rank a matching coin down (the stronger of the two per cause)
        out[k_] = min(out.get(k_, 0.0), p_)
    return out


def _coach_view(now):
    rs = _rs()
    return {**rs._co.view(rs._coach_state(), now, rs._jr.penalties((rs._office.get('court') or {}).get('promoted'))), 'ai': rs._coach.get('aiSaid')}


def _trade_tape(now):
    """🎬 The real trade tape for the page (rebuilt at most every 20s): ledger fills + the archive + the Judge's reviews + the model's log."""
    rs = _rs()
    if rs._coach['tape'] is None or now - rs._coach['tapeAt'] >= 20:
        try:
            ar_ = rs._json_load(rs.ARCHIVE_PATH, {}) or {}
            pos_ = rs._co.germ_fill(ar_.get('positions'), ar_.get('germFill'))   # 🦠 your past entries' germ, backfilled beside the hash chain
            rows = rs._co.trade_tape(rs._fw_full_ledger()[-900:], pos_, ((rs._office_state().get('judge') or {}).get('reviews')) or [], rs._ai.get('log') or [], n=24)
            rs._coach.update(tape={'rows': rows, 'stats': rs._co.tape_stats(rows), 'sources': rs._co.source_record(pos_), 'rules': rs._co.rule_record(pos_), 'line': rs._co.line_replay(pos_), 'germ': rs._co.germ_record(pos_),
                                 'holds': {k_: v_ for k_, v_ in (rs._study.get('holds') or {}).items() if k_ in ('early', 'n')}, 'proof': rs._co.agent_proof(pos_)}, tapeAt=now)   # 🦠 your entries vs the germ · 🎓 rules that sold you early
            rs._coach_grade(now)
        except Exception as e:
            print('trade tape:', str(e)[:120])
    return rs._coach['tape']


def _coach_grade(now):
    """📏 Every live directive (owner · model · Judge) is graded on the coins it ranked down: noted once at the desk's own price, judged
    30 min later from the desk's price again (no fetch). A MODEL directive its own record proves wrong ends itself; an owner's is shown."""
    rs = _rs()
    try:
        st_ = rs._coach_state()
        keys = set(rs._coach_pens(now)) | set(rs._trl.flagged(rs._taught_rules()))   # 🎓 a 👀 flag-only lesson is graded too
        table = rs._agents.get('table') or []
        hits = {}
        for x_ in table if keys else []:
            for words_, _p in rs._opp.judge_hits(x_, {k_: -1.0 for k_ in keys}):
                hits.setdefault(words_.split(': ', 1)[-1], []).append((x_.get('mint'), x_.get('symbol'), rs._fuse._f(x_.get('px'))))
        had = bool(((st_.get('grade') or {}).get('open')))
        if not hits and not had:
            return
        st_ = rs._co.grade_note(st_, hits, now)
        st_, n_ = rs._co.grade_settle(st_, {x_.get('mint'): rs._fuse._f(x_.get('px')) for x_ in table}, now)
        st_, ended = rs._co.drop_wrong(st_, now)
        for k_ in ended:
            rs._tk.KERNEL.note('judge', 'RULE ENDED', f"📏 {k_}: ended by its own record", now, key=f"coachend:{k_}:{int(now // 3600)}")
        rs._coach['s'] = st_
        if n_ or ended or now - rs._coach.get('gradeSaved', 0.0) >= 300:
            rs._coach['gradeSaved'] = now
            rs._json_save(rs.COACH_PATH, st_)
    except Exception as e:
        print('coach grade:', str(e)[:120])


def _teach_state():
    rs = _rs()
    if rs._teach['st'] is None:
        rs._teach['st'] = rs._json_load(rs.TEACH_PATH, {}) or {}
    return rs._teach['st']


def _taught_rules():
    """🎓 Your lessons as rules (taught_rules.py): mode · strength · knob per rule, kept beside the teachings."""
    rs = _rs()
    return rs._trl.clean(rs._teach_state().get('rules'))


def _taught_stamp(table, now):
    """Each sensed row gets `taught` = {rule: reason} for every lesson it hits (the kernel ranks by it, ✋ skip blocks it, the model
    reads it); `_office['taught']` = the same by mint, `_office['taughtSeen']` = counts + 3 examples per rule for the page."""
    rs = _rs()
    try:
        rules = rs._taught_rules()
        hrs = (rules.get('same narrative') or {}).get('hours', 6)
        legs_ = ((rs._prime_cards().get(rs._office.get('tid') or '') or {}).get('legs') or [])
        by_m = {r_.get('mint'): r_ for r_ in table or []}
        held_ = [{'symbol': l.get('symbol') or (by_m.get(l.get('mint')) or {}).get('symbol'), 'name': (by_m.get(l.get('mint')) or {}).get('name'), 'mint': l.get('mint')}
                 for l in legs_ if l.get('mint') and not l.get('placeholder')]
        held_m = {h['mint'] for h in held_}
        seen_ = rs._trl.recent(held_, (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or [], now, hrs)
        chrs_ = (rules.get('clone') or {}).get('hours', 720)
        traded_ = [(h['symbol'], h['mint']) for h in held_ if h.get('symbol')] + [(r_.get('symbol'), r_.get('mint')) for r_ in rs._fw_full_ledger()   # 🧬 by TIME, not row count: 1,500 busy rows once covered only ~2h and a second $FOMO got through
                   if r_.get('card') == rs._office.get('tid') and r_.get('side') == 'buy' and r_.get('status') == 'filled' and r_.get('symbol') and now - rs._fuse._f(r_.get('at')) <= chrs_ * 3600]
        traded_ = list(dict.fromkeys(traded_))   # 🧈 one row per (ticker, coin): 30 days of buys repeated the same tickers thousands of times
        out, cnt, ex = {}, {}, {}
        miss_ = []
        for r_ in table or []:   # 🔗 the creator's own links from Pump's record ride on the row (the panel's socials icons read them)
            pl_ = (rs._PUMP_LINKS.get(r_.get('mint')) or (0, None))[1]
            if pl_ is None and str(r_.get('mint') or '').endswith('pump'):
                miss_.append(r_['mint'])
            for k_, u_ in (pl_ or {}).items():
                if not (isinstance(r_.get(k_), str) and r_[k_].startswith('http')):
                    r_[k_] = u_
        if miss_:
            try:
                rs.asyncio.get_running_loop().create_task(rs._pump_links_warm(miss_[:rs.PUMP_LINKS_PER_PASS]))
            except RuntimeError:
                pass
        for r_ in table or []:
            if not r_.get('mint') or r_['mint'] in held_m:
                r_.pop('taught', None)
                continue
            full_ = (rs._office.get('charts') or {}).get(r_['mint'])   # the row carries a compact chart; the candle features live in the shared snapshot
            h_ = rs._trl.hits({**r_, 'chart': full_} if full_ else r_, rules, seen_, traded_, table)
            if h_:
                r_['taught'] = h_
                out[r_['mint']] = h_
                for k_, w_ in h_.items():
                    cnt[k_] = cnt.get(k_, 0) + 1
                    if len(ex.setdefault(k_, [])) < 3:
                        ex[k_].append({'mint': r_['mint'], 'sym': r_.get('symbol'), 'why': w_})
            else:
                r_.pop('taught', None)
        rs._office['taught'], rs._office['taughtSeen'] = out, {'counts': cnt, 'examples': ex}
    except Exception as e:
        print('taught rules:', str(e)[:120])


def _taught_view():
    rs = _rs()
    ts_ = rs._office.get('taughtSeen') or {}
    return rs._trl.view(rs._taught_rules(), rs._co.grades(rs._coach_state()), ts_.get('counts'), ts_.get('examples'))


def _regret_book():
    rs = _rs()
    if rs._regret['b'] is None:
        rs._regret['b'] = rs._json_load(rs.REGRET_PATH, {}) or {}
    return rs._regret['b']


def _regret_note(mint, why, px, sym=None):
    """😴 A coin a check blocked (or the desk took: why='taken') — graded 30 min later beside the taken ones (regret.py)."""
    rs = _rs()
    if mint and why:
        rs._regret['b'] = rs._rg.note(rs._regret_book(), mint, why, px, rs.time.time(), sym)


def _regret_limits(cfg):
    """The limits + tape waits the agents buy by: the owner's own value when set, else what the regret ledger tuned, else the default."""
    rs = _rs()
    try:
        return {**(cfg or {}), **rs._rg.effective(cfg or {}, rs._regret_book())}
    except Exception:
        return cfg or {}


async def _regret_tick(now):
    """Once a minute: every open note's peak + its grade when due (one batched public price read), then one tuning look (regret.tune)."""
    rs = _rs()
    if now - rs._regret['at'] < 60:
        return
    rs._regret['at'] = now
    try:
        b = rs._regret_book()
        mints = list(dict.fromkeys(c_['mint'] for c_ in (b.get('open') or [])))[:80]
        px = await rs._jup_prices(mints, judge=True) if mints else {}
        if mints and not px:
            return   # a pass where the price source answers nothing grades nothing
        b = rs._rg.watch(b, px, now)
        for m_, d_ in sorted(list(rs._tk.KERNEL.dec.items()), key=lambda kv: -rs._fuse._f(kv[1].get('rank')))[:40]:   # 🎯 coins the chart held back are graded beside the coins taken
            if (d_.get('opinions') or {}).get('trigger', {}).get('chartWait'):
                ms_ = rs._tk.KERNEL.store.mints.get(m_) or {}
                rs._regret_note(m_, 'chart:WAIT', rs._fuse._f((ms_.get('market') or {}).get('price')), (ms_.get('identity') or {}).get('symbol'))
        rc = rs._prime.clean_cfg((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {})
        b, ch = rs._rg.tune(b, rc, now)
        rs._regret['b'] = b
        for c_ in ch:
            rs._tk.KERNEL.note('judge', 'TWEAK', f"😴 {c_['key']} → {c_['to']}: {c_['why']}", now, key=f"regret:{c_['key']}:{int(now // 600)}")
        if ch or now - rs._regret['savedAt'] >= 120:
            rs._json_save(rs.REGRET_PATH, b); rs._regret['savedAt'] = now
    except Exception as e:
        print('regret:', str(e)[:140])


def _lab_state():
    rs = _rs()
    if rs._lab['st'] is None:
        rs._lab['st'] = rs._json_load(rs.LAB_PATH, {}) or {}
    return rs._lab['st']


async def _lab_tick(now, env, cfg):
    """🧪 THE RULE LAB (owner, 2026-10-13: "the model proposes rules, the record tests them … let it name new causes … all agents need lessons"):
    every LAB_JUDGE_EVERY every rule on file is re-judged on our REAL trades (no model call — `rule_lab.step`); at most every LAB_EVERY one
    CLOUD call (never the local model) reads the record by entry feature and may propose up to 3 rules in our own words. Only a rule that
    passes the walk-forward on real fills — or names a repeat real loss — goes live, as a lesson for its desk (rank ×0.88 / ×1.06; Trigger
    arms instead of entering on a live entry-moment avoid rule). Never an order, a size or a sell."""
    rs = _rs()
    if now - rs._lab['judgedAt'] < rs.LAB_JUDGE_EVERY:
        return 0
    rs._lab['judgedAt'] = now
    try:
        trades = rs._real_trades()
        props = []
        if now - rs._lab['at'] >= rs.LAB_EVERY and len(trades) >= 20:
            rs._lab['at'] = now
            reviews = ((rs._office_state().get('judge') or {}).get('reviews')) or []
            case = rs._rlab.case(trades, rs._lab_state(), reviews)
            case['lessons'] = [f"owner {t['kind']}: {t['text']}" for t in (rs._teach_state().get('items') or [])[:6]] or None   # 🎓 the lab reads the owner's teachings too
            res = await rs._air.ROUTER.reason(rs._ai_http(), env, cfg, case, 'lab', 'normal', prio=rs._air.PRIO['lab'], mode='case')
            ad = (res or {}).get('advice') or {}
            props = rs._rlab.clean(ad.get('rules'), rs._rlab.vocab(trades))
            rs._lab['said'] = {'at': now, 'summary': ad.get('summary'), 'proposed': len(props), 'source': (res or {}).get('label') or (res or {}).get('source')}
        props = props + rs._rlab.auto_propose(trades, {'rules': list((rs._lab_state().get('rules') or [])) + props})   # 🧪 the record proposes too — the lab never waits on the model
        st_, went = rs._rlab.step(rs._lab_state(), props, trades, now)
        rs._lab['st'] = st_
        for r_ in went:
            rp_ = r_.get('replay') or {}
            rs._tk.KERNEL.note('judge', 'LESSON', f"🧪 {r_['desk']} learned '{r_['name']}' ({r_['act']} {' & '.join(r_['when'])}) — {r_.get('door')}: unseen "
                            f"{rs._fuse._f((rp_.get('test') or {}).get('avg')):+.1f}% vs {rs._fuse._f((rp_.get('test') or {}).get('rest')):+.1f}%", now, key=f"lab:{r_['id']}")
        rs._json_save(rs.LAB_PATH, st_)
        return len(went)
    except Exception as e:
        print('rule lab:', str(e)[:140])
        return 0


def _lab_view(now):
    """The page's 🧪 RULE LAB: every rule with its status + replay, what each desk learned, the model's last proposal line."""
    rs = _rs()
    st_ = rs._lab_state()
    rows = [{'id': r_['id'], 'act': r_['act'], 'when': r_['when'], 'name': r_['name'], 'why': r_.get('why'), 'desk': r_.get('desk'), 'status': r_.get('status'),
             'door': r_.get('door'), 'lossHits': r_.get('lossHits'), 'test': (r_.get('replay') or {}).get('test'), 'learn': (r_.get('replay') or {}).get('learn'),
             'at': r_.get('at'), 'liveAt': r_.get('liveAt')} for r_ in (st_.get('rules') or [])[:16]]
    return {'rules': rows, 'lessons': rs._rlab.lessons(st_), 'log': (st_.get('log') or [])[-6:], 'said': rs._lab.get('said'), 'trades': len(rs._real_trades()),
            'next': max(0, round(rs.LAB_EVERY - (now - rs._lab['at']))) if rs._lab['at'] else 0}


async def _coach_ai(now, env, cfg):
    """👑 THE MODEL INSTRUCTS THE AGENTS (owner, 2026-10-13: "AI should be able to understand and instruct / strengthen agents"): one cloud
    call at most every COACH_AI_EVERY — never the local model (role `coach` is a background job) — over the last real trades' causes.
    Its `directives` are kept only when the cause is in the fixed vocabulary, land at −4 for 6h (`coach.add(by='ai')`), never over an
    owner rule, and wait for the creator's ✅ strengthen / ✕ kill on the page. A ranking weight: never an order, a size or a sell."""
    rs = _rs()
    if now - rs._coach['aiAt'] < rs.COACH_AI_EVERY:
        return 0
    rs._coach['aiAt'] = now
    try:
        reviews = ((rs._office_state().get('judge') or {}).get('reviews')) or []
        capv_, tr_ = rs._capital_view(), rs._office.get('trail') or {}
        money_ = capv_.get('state') == 'PROTECT' or (capv_.get('brake') or {}).get('on') or (rs._fuse._f(tr_.get('left')) >= rs._ap.EDGE and int(tr_.get('n') or 0) >= rs._ap.MIN_N)
        if len([r_ for r_ in reviews if rs._fuse._f(r_.get('pct')) < 0 and now - rs._fuse._f(r_.get('at')) < 6 * 3600]) < 2 and not money_:
            return 0   # nothing to coach on: fewer than two real losses in the last 6h AND the money record asks for nothing (not losing, no brake, no trail left on the table)
        st_ = rs._coach_state()
        mem_ = rs._real_mem(now) or {}
        case = rs._co.coach_case(reviews, {'worst': sorted(((v_['est'], k_, v_['n']) for k_, v_ in (mem_.get('cells') or {}).items()))[:4]}, rs._co.active(st_, now),
                              rs._co.grades(st_), (rs._coach.get('tape') or {}).get('rules'), (rs._coach.get('tape') or {}).get('stats'))
        case['capital'] = rs._cap.lesson(capv_)   # 💰 the desk's money record: win rate, payoff, Kelly, by door, the brake, where the losses come from
        case['trail'] = (str(tr_.get('words') or '') + (' · top: ' + ' | '.join(f"arm +{r_['arm']:g}% give {r_['give']:g}% → {r_['avg']:+.1f}% ({r_['won']}% won)" for r_ in (tr_.get('rows') or [])[:3]) if tr_.get('rows') else ''))[:360] or None
        case['tunes'] = ' · '.join(f"{k_} {v_:g}" for k_, v_ in rs._of.tunes(rs._office_state(), 'reaper').items())[:160]
        res = await rs._air.ROUTER.reason(rs._ai_http(), env, cfg, case, 'coach', 'normal', prio=rs._air.PRIO['coach'], mode='case')
        ad = (res or {}).get('advice') or {}
        n = 0
        for key_, why_ in rs._co.from_ai(ad):
            st_, rule_ = rs._co.add(st_, key_, 'ai', why_ or ad.get('summary'), now)
            if rule_:
                n += 1
                rs._tk.KERNEL.note('judge', 'AI COACH', f"🧠 {key_} {rule_['points']:+.0f} for 6h — {rule_.get('why') or ''}", now, key=f"aicoach:{key_}:{int(now // 3600)}")
        if n:
            rs._coach_put(st_)
        if ad.get('tune'):   # 🎚 the model asks for ONE exit notch: queued for the office pass, which puts it in SHADOW (office.model_candidate) — never live
            rs._coach['tuneAsk'] = {**ad['tune'], 'at': now}
        rs._coach['aiSaid'] = {'at': now, 'summary': ad.get('summary'), 'n': n, 'tune': ad.get('tune'), 'source': (res or {}).get('label') or (res or {}).get('source')}
        return n
    except Exception as e:
        print('coach ai:', str(e)[:120])
        return 0


def _germ_rebuy_step(cur, px, now):
    """🦠 GERM RE-BUY (owner, 2026-10-16: "when a new germ floor is confirmed on 1–5 min it auto sells and rebuys"): a coin your Gstop sold is
    queued back as YOUR seat pick (acknowledged, every keeper check still runs) once its chart prints a NEW germ floor — born after the sale,
    not lost, the price inside your germ line — on the lens you picked (both = 1m AND 5m). Watched GERM_REBUY_SEC, then dropped."""
    rs = _rs()
    rb = {m_: v_ for m_, v_ in (cur.get('germRebuy') or {}).items() if now - rs._fuse._f(v_.get('at')) < rs.GERM_REBUY_SEC}
    if not rb:
        cur.pop('germRebuy', None)
        return cur
    mx_ = rs._uni.germ_max() or 15
    for m_, v_ in list(rb.items()):
        if m_ in rs._prime.held_mints(cur):
            rb.pop(m_); continue
        f_ = (((rs._office.get('charts') or {}).get(m_) or {}).get('f') or {})
        new_ = lambda g_: bool(g_) and not g_.get('lost') and rs._fuse._f(g_.get('at')) >= rs._fuse._f(v_['at']) - 60 and 0 <= rs._fuse._f(g_.get('dist')) <= mx_
        lens_ = v_.get('lens') or 'both'
        ok_ = (new_(f_.get('germ')) and new_(f_.get('germ5'))) if lens_ == 'both' else new_(f_.get('germ' if lens_ == '1m' else 'germ5'))
        p_ = rs._fuse._f(px.get(v_['pair'])) or rs._fuse._f((rs._jup_px_cache.get(m_) or (0, 0))[1])
        if not ok_ or p_ <= 0:
            continue
        try:
            cur = rs._prime.queue_seat(cur, {'mint': m_, 'pairAddress': v_['pair'], 'symbol': v_.get('symbol'), 'price': p_, 'ack': True}, more=True)
            cur.setdefault('events', []).append({'at': now, 'kind': 'agent', 'symbol': v_.get('symbol'), 'why': f"🦠 germ re-buy: ${v_.get('symbol')} printed a new {lens_} germ floor — queued back on your seat"})
            rb.pop(m_)
        except ValueError:
            rb.pop(m_)
    cur['germRebuy'] = rb
    return cur


def _germ_of(mint):
    """🦠 (germ floor px, % the price sits above it) from the agents' shared chart snapshot — None when not read."""
    rs = _rs()
    g_ = (((rs._office.get('charts') or {}).get(mint) or {}).get('f') or {}).get('germ')
    return (rs._fuse._f(g_.get('px')), rs._fuse._f(g_.get('dist'))) if g_ and not g_.get('lost') else None


def _agent_blocked(card, now):
    """🚫 ONE list of coins the agents may not buy right now: what they just left (`arena_prime.agent_out`: 10 min, a rug / danger exit 6h)
    + what the keeper benched or refused on a safety check (no route back, sell-back tax, price gap) for ANY book. 2026-10-12: $TikTok and
    $REGGIE were refused "no route back to SOL" and the seat sat empty while the agents' own lists still offered them."""
    rs = _rs()
    books = (rs._fw_peek().get('books') or {}).values()
    for m_ in [m_ for m_, v_ in rs._agent_refused.items() if v_[0] <= now]:
        rs._agent_refused.pop(m_, None)
    return rs._prime.agent_out(card, now, lambda m_: rs._fuse._f((rs._jup_px_cache.get(m_) or (0, 0))[1]), rs._germ_of) | set(rs._agent_refused) | rs._co.blocked(rs._coach_state(), now) | set().union(set(), *[rs._fw.agent_no_buy(b, now) for b in books]) | rs._trl.skips(rs._taught_rules(), rs._office.get('taught') or {}) | {d_.get('mint') for d_ in rs._agents.get('impostors') or []}   # 🎭 impostors of a real coin + coins the creator pulled with a reason (6h) + 🎓 your lessons in ✋ skip mode


def _g4_blocked(card, now):
    """🔁 What OSSY / G4 may not buy on their turn: the keeper's money refusals, impostors and YOUR own pulls / ✋ lessons — never the
    agents' own just-left cool-down (owner: "the agents can't stop them")."""
    rs = _rs()
    books = (rs._fw_peek().get('books') or {}).values()
    return set(rs._agent_refused) | rs._co.blocked(rs._coach_state(), now) | set().union(set(), *[rs._fw.agent_no_buy(b, now) for b in books]) | rs._trl.skips(rs._taught_rules(), rs._office.get('taught') or {}) | {d_.get('mint') for d_ in rs._agents.get('impostors') or []}


def _seat_refusals(tid, now, window=900.0, keep=5):
    """Why a READY coin did NOT become a position: the keeper's own refusals for this card (ledger, last 15 min) + the seat pre-check's,
    newest first, one line per coin — shown on the empty seat (it used to read only "rebuy cooldown")."""
    rs = _rs()
    out, seen = [], set()
    for r_ in reversed(rs._fw_full_ledger()[-400:]):
        at_ = rs._fuse._f(r_.get('at'))
        if now - at_ > window:
            break
        if r_.get('card') != tid or r_.get('side') != 'buy' or r_.get('status') not in ('skipped', 'failed') or r_.get('mint') in seen:
            continue
        seen.add(r_.get('mint'))
        out.append({'symbol': r_.get('symbol'), 'why': str(r_.get('err') or r_.get('why') or '')[:110], 'at': round(at_, 1), 'by': 'keeper'})
    for m_, (_until, why_, at_) in rs._agent_refused.items():
        if m_ not in seen and now - at_ <= window:
            out.append({'symbol': (rs._tk.KERNEL.candidate(m_) or {}).get('symbol') or m_[:4], 'why': why_, 'at': round(at_, 1), 'by': 'pre-check'})
    return sorted(out, key=lambda x_: -x_['at'])[:keep]


async def _seat_precheck(plan, cfg_t, now, seat_usd=0.0, need=1):
    """🛂 CHECK THE BUY BEFORE THE SEAT (read-only; ONE batched live read for the coins about to be seated): the keeper's own final market
    gate (`fuse_wallet.live_buy_market`: the exact pool answers, it holds this mint, a live price, pool ≥ its floor) run BEFORE a seat is
    created. 2026-10-12: of 20 agent seats in 25 min, 9 were refused by that gate seconds later ("live market unavailable", "live pool too
    thin: $5,959") — each one emptied the seat again and used a fill. A coin that fails sits out AGENT_PRE_SEC and the next READY coin is
    tried in the same tick. → {mint: {'liq', 'px'}} for the coins that pass (fresh entry depth + price: the board's row was minutes old,
    so the rug shield read "$18K → $8K, pulled" and the stop read −24% three seconds after a buy)."""
    rs = _rs()
    out = {m_: v_[1] for m_, v_ in rs._seat_pre_ok.items() if now - v_[0] < rs.SEAT_PRE_OK_SEC}   # a pass is good for 20s: no second live read for the same coin
    for m_ in [m_ for m_ in rs._seat_pre_ok if m_ not in out]:
        rs._seat_pre_ok.pop(m_, None)
    plan = [t_ for t_ in plan or [] if t_.get('mint') not in out]
    if not plan:
        return out
    try:
        live = await rs._fw_live_pairs([{'pair': t_.get('pair'), 'mint': t_.get('mint')} for t_ in plan if t_.get('pair')])
    except Exception as e:
        print('seat precheck:', type(e).__name__)
        return {**out, **{t_['mint']: {} for t_ in plan}}   # the read itself failed: the keeper's own gate still decides
    cfg = rs._fw_cfg()
    try:
        sol_px = await rs._sol_usd_live() if seat_usd > 0 else 0.0
    except Exception:
        sol_px = 0.0
    for t_ in plan:
        if len(out) >= need:   # enough coins for the open seats: the rest are not quoted this tick (Jupiter's free tier is shared with the keeper)
            break
        o_ = {'side': 'buy', 'mint': t_.get('mint'), 'pair': t_.get('pair'), 'symbol': t_.get('symbol'), 'agent': not t_.get('g4'), **({'picked': True} if t_.get('g4') else {}), 'trench': rs._uni.in_lane(t_.get('vitals') or {}),
              'curve': bool((t_.get('vitals') or {}).get('curve') and cfg_t.get('agentCurve'))}
        ok_, why_, lv_ = rs._fw.live_buy_market(o_, live.get(t_.get('pair')), cfg)
        hold_ = rs.AGENT_PRE_SEC
        cap_ = rs._fuse._f((live.get(t_.get('pair')) or {}).get('marketCap') or (live.get(t_.get('pair')) or {}).get('fdv'))
        if ok_ and cap_ > 0 and not (rs._uni.band()[0] <= cap_ < rs._uni.band()[1]):
            # 🎯 the owner's band is judged on the LIVE cap too: the desk's row can be minutes old, and a launch that ran to $18K and died back
            # to its $3K floor was seated again and again on its old reading (Lynk / JEANPAD / TIMUR / SAVELLS, 2026-10-13)
            ok_, why_ = False, f"live cap ${cap_:,.0f} is outside your {rs._uni.band_word()} band (the desk's reading was old)"
        if ok_ and rs._uni.min_age() > 0:   # 🐣 the owner's youngest-coin line, judged on the live pool's own birth (the desk row can be wrong)
            born_ = rs._fuse._f((live.get(t_.get('pair')) or {}).get('pairCreatedAt')) / 1000.0
            ages_ = [a_ for a_ in ((rs.time.time() - born_) / 3600.0 if born_ > 0 else None, (t_.get('vitals') or {}).get('ageH'), (t_.get('li') or {}).get('ageH'), t_.get('ageH'))
                     if a_ is not None and rs._fuse._f(a_) >= 0]
            age_ = min(rs._fuse._f(a_) for a_ in ages_) if ages_ else None   # 🐣 the YOUNGEST age any source reports (Gemini went in at 17 min: the pool read older than the coin)
            yw_ = rs._uni.too_young({'ageH': age_}) if age_ is not None else 'launch age unknown (your youngest-coin line is on)'
            if yw_:
                ok_, why_ = False, yw_
        if ok_ and sol_px > 0 and seat_usd > 0 and rs.time.time() - rs._FW_JUP_BUSY['at'] <= rs.JUP_BUSY_SEC:
            continue   # Jupiter is rate-limiting us: the keeper's own buy would fail the same way → no seat this tick, the coin is NOT marked refused
        if ok_ and sol_px > 0 and seat_usd > 0:
            # 🛡 the SAME two read-only quotes the keeper takes before it signs (buy near market · sells straight back · impact): a coin the
            # keeper would refuse never gets a seat, so the card shows no "buy refused" and the seat goes to the next coin in this tick
            o_.update(usd=round(seat_usd, 4), lamports=int(seat_usd / sol_px * 1e9), midPx=lv_.get('midPx'), liq=lv_.get('liq'))
            try:
                q_ = await rs._fw_quote(o_, cfg)
                ok_, why_, _b = await rs._fw_secure_buy(o_, cfg, q_)
                if ok_ and rs._fuse._f(q_.get('priceImpactPct')) * 100 > cfg['maxImpactPct']:
                    ok_, why_ = False, f"price impact {rs._fuse._f(q_.get('priceImpactPct')) * 100:.2f}% > {cfg['maxImpactPct']:g}%"
                if not ok_:
                    hold_ = rs.AGENT_NOROUTE_SEC if 'no route' in why_ else rs._fw.AGENT_REFUSED_SEC
            except rs.HTTPException as e:
                if any(u_ in str(e.detail).lower() for u_ in rs._fw.UNROUTABLE):
                    ok_, why_, hold_ = False, 'Jupiter has no route for it yet', rs.AGENT_NOROUTE_SEC
                else:
                    continue   # a busy Jupiter (429 / 5xx) is not the coin's fault: no seat this tick, nothing held against the coin
        if ok_:
            out[t_['mint']] = {'liq': rs._fuse._f(lv_.get('liq')) or None, 'px': rs._fuse._f(lv_.get('midPx')) or None}
            rs._seat_pre_ok[t_['mint']] = (now, out[t_['mint']])
        else:
            rs._agent_refused[t_['mint']] = (now + hold_, why_, now)
            rs._regret_note(t_['mint'], rs._rg.why_class(why_), rs._fuse._f((lv_ or {}).get('midPx')) or rs._fuse._f(t_.get('px')), t_.get('symbol'))   # 😴 graded later beside the coins taken
    return out


async def _agents_tick(now):
    """🤖 One pass of the four agents (Tally → Sherlock → Trigger → Devil) over the busiest open-list coins, then every open call is judged
    at 5 / 15 / 60 min at Jupiter's price. Runs in the warm loop — any hour, whenever there is internet. A pass where Jupiter answers
    nothing is not judged (an outage must not read as every coin vanishing)."""
    rs = _rs()
    woke = rs._fuse._f(rs._agents.get('wake')) > rs._fuse._f(rs._agents['at'])   # ⚡ a live breakout / material move on a waiting candidate: Trigger re-reads now
    if (now - rs._agents['at'] < rs.AGENTS_EVERY and not (woke and now - rs._agents['at'] >= rs._mw.GAP_CAND)) or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return
    rs._agents['at'] = now
    wake_at_ = rs._fuse._f(rs._agents.get('wake')) if woke else 0.0
    await rs._regret_tick(now)   # 😴 grade the coins the checks blocked + tune the checks the owner left on AGENTS (once a minute)
    try:   # 🎯 the owner's MC band (realCfg agentMcMin / agentMcMax, default $12K–$300K) — every reader of the universe reads it from here
        _rc_ = rs._prime.clean_cfg((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {})
        rs._uni.set_band(rs._ng.night_cfg(_rc_, rs.time.localtime().tm_hour, on=_rc_.get('nightShift', True) is not False))   # 🌙 the night profile's min age reaches the universe too
        rs._uni.set_trending([r_.get('mint') for r_ in (rs._lens_rows or {}).get('ptrend') or []])   # 🔥 the coins on Pump's own Trending board right now
    except Exception as e:
        print('band:', e)
    try:
        # 🕸 THE CRAWL: the busiest open-list coins + the NEWEST launches (≤ 1h) — and every coin is tagged with every corner of the trench it
        # showed up in (Pump trending / callouts / live, movers, volume, fed, waves, cooling, proven callers …): each source is a learned driver
        ob_ = rs._open_board(len(rs._open_pairs) or None) or []   # 🕸 the WHOLE launch feed the board holds (not just the top 200 front-runners)
        # 🕸 ONE DEDUPED LIVE INTAKE: every outlet FEELESS already runs (Pump pulse + migrations · the board · the runner board · tracked
        # lists · callouts · fed runners · the radar · the card) is noted in ONE registry; coins the board does not carry get their row
        # from Jupiter's token data (one batched read, the existing cache) so a launch seconds old reaches Tally on this pass
        try:
            own_ = rs._owr.modes(rs._owner_book(now), now)   # 👤 the owner's review / track / arm list: each gets a seat at the desk's table (the SAME agents read it)
            board_m = {x.get('mint') for x in ob_}
            extra_, fresh_, outl_ = await rs._intake_pass(ob_, now, list(own_))
        except Exception as e:
            print('intake:', e); extra_, fresh_, outl_, own_, board_m = [], {}, {}, {}, set()
        ob_ = rs._in.shared_rows(ob_ + extra_, fresh_, outl_, rs._intake_reg())
        rs._shared_intake.update(at=now, rows=ob_)   # discovery first; agent screening below never trims the shared intake
        rs._intake_cache['at'] = 0.0
        held_l = {l.get('mint') for l in rs._prime_cards().get(rs._office.get('tid') or '', {}).get('legs') or [] if l.get('mint')}
        cap_ = max(rs._uni.lane_cap(ob_), rs._agents.get('laneStep') or rs._uni.LANE_CAPS[0]); rs._agents['laneCap'] = cap_   # 🪜 the smallest cap that can fill the seats ($200K first) — or wider, when last pass's ranking came up short
        rs._owner['only'] = {m_ for m_ in own_ if m_ not in held_l and not (m_ in board_m or m_ in fresh_ or m_ in outl_)} | {x.get('mint') for x in ob_ if x.get('mint') in own_ and x.get('mint') not in held_l and not rs._uni.in_lane(x, cap_)}
        try:   # 🎭 OFFICIAL COIN GUARD: a launch wearing the ticker of a real, bigger coin (the $20M STREAM vs a $40K "STREAM") never reaches the desk
            legs_h = rs._prime_cards().get(rs._office.get('tid') or '', {}).get('legs') or []
            seen_ = list(ob_) + [{'symbol': (p_.get('baseToken') or {}).get('symbol'), 'mint': (p_.get('baseToken') or {}).get('address'),
                                  'mcap': p_.get('marketCap') or p_.get('fdv')} for p_ in (rs._open_pairs or [])]
            est_ = rs._imp.established(seen_, rs._fuse.ALL_MAJORS, [l for l in legs_h if not l.get('placeholder')])
            keep_, drop_ = rs._imp.filter_rows([x for x in ob_ if x.get('mint') not in held_l and x.get('mint') not in own_], est_)
            if drop_:
                gone_ = {d_['mint'] for d_ in drop_}
                ob_ = [x for x in ob_ if x.get('mint') not in gone_]
            rs._agents['impostors'] = drop_[:20]
        except Exception as e_:
            print('impostor guard:', str(e_)[:100])
        ob_ = [x for x in ob_ if x.get('mint') in held_l or x.get('mint') in own_ or rs._uni.in_lane(x, cap_)]   # 🎯 the universe FIRST: intake slots go to coins under the cap (they were spent on $200K+ coins, then dropped — 26 safe sub-$200K pools never reached the desk)
        src_ = {}
        for k_, lst_ in (rs._lens_rows or {}).items():
            for r_ in lst_ or []:
                if r_.get('mint') and k_ in rs._sn.SOURCES:
                    src_.setdefault(r_['mint'], []).append(k_)
        for c_ in rs._pump_calls.get('calls') or []:
            if c_.get('mint') and 'calls' not in src_.get(c_['mint'], []):
                src_.setdefault(c_['mint'], []).append('calls')
        held_m = [l.get('mint') for l in rs._prime_cards().get(rs._office.get('tid') or '', {}).get('legs') or [] if l.get('mint')]
        seen_mem = rs._office.get('seen') or {}
        cool_ = {k_ for k_, e_ in seen_mem.items() if not rs._oe.review_due(e_, now)[0]}
        # held coins always + last pass's strongest cases / bench — but a rejected case with nothing new since does not hold a seat at the table
        stale_ = lambda r_: rs._oe.fresh_key((r_ or {}).get('vitals') or r_ or {}) >= 5 and not rs._opp.reawake(r_ or {})   # 🧊 12h+ and not waking up: no automatic recheck
        recheck_ = held_m + list(own_) + [c_['mint'] for c_ in rs._tk.KERNEL.cases(top=20, statuses=('READY', 'CONTENDING')) if c_['mint'] not in cool_ and not stale_(c_.get('row'))] + [b_['mint'] for b_ in rs._agents.get('bench') or [] if b_.get('mint') not in cool_ and not stale_(b_)]
        taken_ = rs._oe.intake(ob_, recheck_, src_, cool=cool_, fresh=fresh_, outlets=outl_)
        rs._office['intake'] = {'board': len(ob_), 'boardFeed': len(ob_) - len(extra_), 'outletRows': len(extra_), 'screened': len(taken_), 'by': {k_: sum(1 for x in taken_ if k_ in x['intake']) for k_, _n in rs._oe.INTAKE_SLOTS},
                             'newLaunches': sum(1 for x in ob_ if x.get('ageH') is not None and rs._fuse._f(x['ageH']) <= 1), 'cooled': len(cool_)}
        seen_ = {x.get('mint') for x in taken_ if 'new' in x['intake'] and x.get('ageH') is not None and rs._fuse._f(x['ageH']) <= 1}
        raw = [rs._with_tv(x) for x in taken_]
        for x in raw:
            x['src'] = ['open'] + (['new'] if x.get('mint') in seen_ else []) + src_.get(x.get('mint'), []) + list(fresh_.get(x.get('mint')) or []) + (['outlet'] if x.get('mint') in outl_ else [])
        tv_ = {x.get('mint'): x.get('tv') for x in raw}
        rows = [rs._uni.established({**r, 'tv': tv_.get(r.get('mint')) or r.get('tv')}) for r in rs._clean_rows([dict(x) for x in raw])]   # 🏛 an established coin's top-10 = exchange / pool wallets, not a failed scan
        if ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}).get('agentCurve'):   # 🎢 owner's switch: a fresh Pump coin still on its curve
            sp_ = await rs._sol_usd_live()   # has no pool figure — its curve depth stands in (0 = unknown → the conservative $100)
            for r in rows:
                if r.get('curve') and rs._fuse._f(r.get('liq')) <= 0 and rs._fuse._f(r.get('mcap')) > 0:
                    r['liq'] = rs._fuse.curve_liq(r['mcap'], sp_ or 100.0); r['liqCurve'] = True
        for r in rows:   # 🧪 the agents' own holder line: failed ONLY on concentration, inside the agents' limits → passes as a half-seat coin
            soft_ = rs._uni.agent_holder_pass(r)
            if soft_:
                r['safe'], r['holderSoft'] = True, soft_
        rows = [({**r, 'owner': own_[r['mint']]} if r.get('mint') in own_ else r) for r in rows if r.get('mint') in held_m or r.get('mint') in own_ or rs._uni.in_lane(r, rs._agents.get('laneCap') or rs._uni.AGENT_MAX_MCAP)]   # 🎯 the lane (the ladder's cap) — coins on the card stay: their exits still run
        # 🧠 the human read: who is calling each coin on Pump and what they write, the narratives hot on the board, the lingo they use
        calls_ = rs._pump_calls.get('calls') or []
        by_m = {}
        for c_ in calls_:
            by_m.setdefault(c_.get('mint'), []).append(c_)
        hot_ = rs._tm.hot_narratives(rows)
        soc_ = rs._social_cache()
        try:   # 🧨 who leads each ticker wave and who copies it · how many PROVEN Pump callers are on the coin (strategy inputs, paper first)
            wr_ = rs._mt.wave_roles(rs._mt.trending(rs._json_load(rs.MEME_PATH, {}), now), rows)
        except Exception:
            wr_ = {}
        rows = [{**r, 'mind': rs._tm.read(r, by_m.get(r.get('mint')), hot_), 'waveRole': wr_.get(r.get('mint')), 'pros': int((rs._pump_calls['map'].get(r.get('mint')) or {}).get('pro') or 0),
                 **({'social': soc_[r['mint']]} if r.get('mint') in soc_ else {})} for r in rows if not rs._fw.dollar_named(r.get('symbol'))]
        lingo = rs._lingo_mem.get() or {}
        if now - rs._fuse._f(rs._agents.get('lingoAt')) >= 600:   # 🗣 slang is learned from Pump callers' text every 10 min, not every 18s pass (2.7s of blocked loop)
            rs._agents['lingoAt'] = now
            lingo = rs._tm.learn_lingo(lingo, [c_.get('thesis') for c_ in calls_ if c_.get('thesis')], now)
            rs._lingo_mem.put(lingo, now)
        rs._agents['mind'] = {'hot': [{'key': k, **v} for k, v in list(hot_.items())[:6]], 'dictionary': len(rs._tm.SLANG),
                           'learned': rs._agents.get('mindLearned') if rs._agents.get('mindLearnedAt') == rs._agents.get('lingoAt') else rs._agents.__setitem__('mindLearnedAt', rs._agents.get('lingoAt')) or rs._agents.__setitem__('mindLearned', __import__('heapq').nlargest(16, ({'word': w, **v} for w, v in (lingo.get('learned') or {}).items()), key=lambda x: rs._fuse._f(x.get('first')))) or rs._agents['mindLearned'],   # ⚡ rebuilt only when the slang is re-learned (3.6s of blocked loop)
                           'callsRead': len(calls_), 'swarms': sum(1 for r in rows if ((r.get('mind') or {}).get('crowd') or {}).get('swarm'))}
        st = rs._agents_mem.get()
        try:   # 👨‍⚖️ the Judge rules on REAL money too: the agents' own seats that left the card (the card's ledger result)
            st['realPieces'] = [{k_: p_.get(k_) for k_ in ('symbol', 'mint', 'pct', 'holdMin', 'why', 'at')} for p_ in (rs._json_load(rs.REAL_LEARN_PATH, {}).get('pieces') or []) if 'tag:🤖' in (p_.get('k') or [])][-30:]
            st['realReviews'] = [{k_: r_.get(k_) for k_ in ('kind', 'at', 'resp', 'cause', 'sym')} for r_ in ((rs._office_state().get('judge') or {}).get('reviews') or [])][-60:]   # 💵 the Judge's real-loss reviews decide who survives
        except Exception:
            pass
        try:   # ⚖ Devil's busted reads = the reads' own live 1-hour records, never a fixed list
            bust_ = rs._sn.busted(rs._trench.meta_proof(rs._json_load(rs.CALL_PROOF_PATH, {}), keys=tuple(dict.fromkeys(rs.CALL_KEYS.values()))), rs.CALL_KEYS)
        except Exception:
            bust_ = None
        t_tick = rs.time.perf_counter()
        of_ = rs._office_state()
        tid_r, book_r = rs._office_real()
        t0_ = rs.time.perf_counter(); cour_ = rs._of.courier(rs._office_ledger(), book_r, now, tid_r, of_); rs._office_lat('courier', (rs.time.perf_counter() - t0_) * 1000)   # 📮 execution truth from the keeper's own rows
        rs._office['courier'] = cour_
        wfn_ = lambda nums_, rows_, s_, n_: (lambda w_: {**w_, 'adj': rs._of.weather_adj(w_)})(rs._of.weather(nums_, rows_, s_, n_, cour_['health'], of_))   # 🌦 ONE regime a pass
        # 📈 ONE shared chart snapshot per coin: real 1-min candles for the coins on the real card + last pass's strongest cases (≤ a dozen
        # requests, cached), Tally's own tape for everything else. Every desk reads that one object.
        held_ = {l.get('mint'): l.get('pairAddress') for l in rs._prime_cards().get(tid_r or '', {}).get('legs') or [] if l.get('mint') and not l.get('placeholder')}
        seen_mem = rs._office.get('seen') or {}
        # 🔬 DEEP REVIEW (real 1-min candles) = the top of the ranked bench first, then the strongest reads — but a rejected coin with nothing new
        # is not re-reviewed (its slot goes to a coin with news); each pick records WHY it was due (never reviewed · material change · cooldown over)
        cand_c = rs._tk.KERNEL.cases(exclude=set(held_), top=60, statuses=('READY', 'CONTENDING'))   # ⚙ the kernel's own ranked candidates (last pass) pick the deep reviews
        rank_ = {b_.get('mint'): i_ for i_, b_ in enumerate(rs._agents.get('bench') or [])}
        _fk = lambda r_: rs._oe.fresh_key(r_ or {})
        _old_c = lambda c_: _fk((c_.get('row') or {}).get('vitals')) >= 5 and not rs._opp.reawake(c_.get('row'))   # 🆕 12h+ and not waking up: deep review only when nothing fresher is due
        cand_c.sort(key=lambda c_: (_old_c(c_), _fk((c_.get('row') or {}).get('vitals')), rank_.get(c_['mint'], 999), not c_.get('cleared'), -rs._fuse._f(c_.get('lean'))))
        why_ = {}
        top_ = {}
        n_cases_, n_new_, young_min_ = rs.OFFICE_CANDLE_CASES - 6, rs.OFFICE_CANDLE_NEW + 6, rs._opp.OLD_H * 60   # 🆕 0–12h coins dominate the deep review, whatever the phase
        for c_ in cand_c:
            due_, w_ = rs._oe.review_due(seen_mem.get(c_['mint']), now)
            if due_ and len(top_) < n_cases_:
                top_[c_['mint']] = c_['pair']; b_ = rs._deep_bucket(w_); why_[b_] = why_.get(b_, 0) + 1
        for x_ in sorted((x_ for x_ in rows if x_.get('ageH') is not None and rs._fuse._f(x_['ageH']) * 60 <= young_min_ and rs._fuse._f(x_.get('vol5m')) >= 1000 and x_.get('pairAddress')),
                         key=lambda x_: (_fk(x_), -rs._fuse._f(x_.get('vol5m')))):   # 🆕 freshness ladder first (0–15m …), then the busiest   # 🐣 deep review for the busiest NEWBORNS too: their few real candles are their evidence (cooldown applies)
            if len([m_ for m_ in top_ if m_ not in {c_['mint'] for c_ in cand_c}]) >= n_new_:
                break
            due_, w_ = rs._oe.review_due(seen_mem.get(x_['mint']), now)
            if due_ and x_['mint'] not in top_:
                top_[x_['mint']] = x_['pairAddress']; b_ = rs._deep_bucket(w_); why_[b_] = why_.get(b_, 0) + 1
        rs._office['deepWhy'] = why_
        rs._office['deepNow'] = [m_ for m_ in top_ if m_ not in held_]   # this pass's DEEP reviews (real candles) — held coins are re-read every pass anyway
        # 📈 CANDLE BUDGET FOLLOWS NEW / BUSY COINS: the candles service builds a limited number of new histories per call IN REQUEST ORDER —
        # it used to get the intake order (held + last pass's cases first). Now: fresh 0–12h coins by the ladder + 5-min $, then the deep
        # reviews, then everything else, held coins LAST (the tier tick re-reads them every tick anyway).
        cat_ = {}
        for r_ in rows:
            if r_.get('mint'):
                cat_[r_['mint']] = 'held' if r_['mint'] in held_ else ('fresh' if _fk(r_) <= 4 else 'old')
        want_c = rs._oe.candle_order(rows, top_, held_)
        old_ord = list(dict.fromkeys([r_['mint'] for r_ in rows if r_.get('mint') and r_.get('pairAddress')] + list(top_) + list(held_)))[:24]
        cmap_ = await rs._office_candles(want_c, now, cat_)   # 👁 every coin on the desk reads the LIVE chart
        rs._office['candleStat']['allocBefore'] = {k_: sum(1 for m_ in old_ord if cat_.get(m_, 'held' if m_ in held_ else 'old') == k_) for k_ in ('fresh', 'old', 'held')}   # what the old order would have built first
        flows_ = {p_: w_ for p_, (at_, w_) in list(rs._flow_now.items()) if w_ and now - rs._fuse._f(at_) <= 90}
        charts_ = {}
        rcfg_ = ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {})
        # 📡 THE SENSES: ONE row per mint — Tally's tape, the shared chart read, the human read, the launch context, Devil's EVIDENCE. No verdict.
        st, table, sctx_ = rs._sn.sense(st, rows, now, candles=cmap_, flows=flows_, charts_out=charts_, cmeta=rs._office.get('cmeta'), busted=bust_, weather_fn=wfn_)
        for m_, pa_ in held_.items():   # a held coin that is off the board still gets its chart (Reaper needs it), from the same candle read
            if m_ not in charts_ and cmap_.get(m_):
                charts_[m_] = rs._ci.read(cmap_[m_], now, True, 'candles', None if not (rs._office.get('cmeta') or {}).get(m_) else {**{k_: v_ for k_, v_ in rs._office['cmeta'][m_].items() if k_ in ('provider', 'source', 'tickCount', 'partial')}, 'noCtx': True}, flow=flows_.get(pa_))   # off the board: no pool / volume reading is handed in, so neither is judged (the row checks still run)
        rs._office['charts'] = charts_
        rs._li_attach(table, now)   # 🕵 launch intelligence on every sensed row (early-buyer map, launch class, FOMO phase, exit pressure) — cache reads only
        rs._agents['passAt'] = now
        rs._agents['weather'] = st.get('weather')
        rg_ = (st.get('weather') or {}).get('regime')
        if rg_ and rg_ != rs._tape_seen.get('regime'):   # 🌦 one line when the regime CHANGES
            rs._tk.KERNEL.note('weather', rg_, '; '.join(str(x_) for x_ in ((st.get('weather') or {}).get('why') or [])[:2]) or 'regime read from this pass', now, key=f'regime:{rg_}:{int(now // 60)}')
            rs._tape_seen['regime'] = rg_
        rs._agents['table'] = table   # the SENSED rows: what every live decision reads (no paper verdict exists on them)
        try:   # ⚙ THE KERNEL DECIDES HERE — sensed rows → one MintState per mint → the ten-agent brain → ONE reducer. Nothing below can change it.
            rs._kernel_pass(table, now)
        except Exception as e:
            print('kernel:', str(e)[:160])
        if wake_at_:   # 📏 a live market event woke the office → the kernel has re-judged
            rs._tk.KERNEL.timings.note('wakeToDecisionSec', rs.time.time() - wake_at_)
        kcases_ = rs._tk.KERNEL.cases()   # the kernel's case files of THIS pass (the seat board, the scan / research order and the registry read these)
        try:   # ♻ per-coin memory: first / last seen · last deep review · last reject · last material change
            rs._office['seen'] = rs._oe.note_seen(rs._office.get('seen'), table, kcases_, {m_ for m_, c_ in charts_.items() if (c_ or {}).get('src') == 'candles'}, now)
        except Exception as e:
            print('seen:', e)
        if len(table) >= rs._oe.READY_MIN_COINS:   # 🔌 a full pass on a real board since this process started (the refill the restart race waits for)
            rs._office['boot']['passes'] = int(rs._office['boot'].get('passes') or 0) + 1
        rs._office['boot']['coins'] = len(table)
        # 📝 THE PAPER DESK (offline practice): graded calls on the same sensed rows, recorded and judged at 5 / 15 / 60 min. Evidence for the
        # Judge and the page — no fill, switch, exit, size or generation reads anything it writes (tests/test_kernel_authority.py).
        arch_ = rs._json_load(rs.ARCHIVE_PATH, {})
        jp = {}
        paper_ = table
        try:
            st, paper_ = rs._pd.calls(st, table, sctx_, now, rcfg_.get('agentDial'), bust_)
            st = rs._pd.record(st, paper_, now)
            want = list(dict.fromkeys(list((st.get('open') or {}).keys()) + [c_['d']['mint'] for c_ in arch_.get('cases') or [] if c_['d'].get('mint') and 'p60' not in (c_.get('out') or {})]))   # ONE batched price read for the calls AND the archive's open cases
            jp = await rs._jup_prices(want, judge=True) if want else {}
            if not want or jp:
                before = st
                st = rs._pd.settle(st, lambda m: (jp or {}).get(m), now)
                st['feed'] = (list(st.get('feed') or []) + rs._pd.results(before, st, now))[-rs._pd.FEED_KEEP:]
            st['money'] = rs._agents.get('money') or st.get('money') or {}
            st = rs._pd.scalp_adopt(st, now)          # ⚡ the take line learned from their own graded 5-minute paths (used only while proven, owner switch `agentScalp`)
            rs._agents['scalp'] = st.get('scalp')
            st = rs._pd.burn(st, now)
            st = rs._pd.autopsy(st, now)
            st = rs._pd.history(st, now)
            n_ideas = len(st.get('ideas') or {})
            st = rs._pd.ideas(st)   # 💡 tactics found in the practice record go up to the creator
            for iid, v in (st.get('ideas') or {}).items():
                if v.get('status') == 'new' and v.get('at', 0) and len(st['ideas']) > n_ideas and iid not in (rs._agents.get('told') or set()):
                    rs._agents.setdefault('told', set()).add(iid)
                    st['feed'] = (list(st.get('feed') or []) + [{'at': now, 'who': 'desk', 'sym': '', 'text': f"💡 new idea for the creator: {v['text']}"}])[-rs._pd.FEED_KEEP:]
        except Exception as e:
            print('paper desk:', str(e)[:160])
        rs._agents_mem.put(st, now)   # 💾 the live object; written ≤ every 90s (it was 3 MB parsed + written every pass)
        try:   # 🎯 the mission reads the real card's own money (server value vs put-in) — the same numbers My cards shows
            rc_ = next((c for c in (await rs._prime_view()) if c.get('real')), None)
            rs._agents['money'] = {'value': rc_.get('valueUsd'), 'putIn': (rc_.get('math') or {}).get('putIn')} if rc_ else {}
        except Exception:
            pass
        rs._agents.update(paper=paper_, view=rs._paper_view(st, paper_, rcfg_, now))
        try:   # 🔁 this cycle's funnel, for the page (counts from this pass's objects only)
            prev_ = (rs._office.get('cycle') or {}).get('at')
            rs._office['cycle'] = rs._oe.cycle_view(rs._office.get('intake'), table, kcases_,
                                              rs._office.get('charts'), st.get('first'), now, now, max(rs.AGENTS_EVERY, rs._fuse._f(rs._oe.policy(rcfg_)['seatTarget'])), int(rs._office.get('cycleN') or 0), rs._office.get('lastMints'))
            rs._office['cycle']['prevAt'] = prev_
            try:   # 🆕 the fresh-trench pipeline of this cycle (buckets · deep · cleared · repeats · top 5 · age at entry) — display only
                arch_p_ = rs._json_load(rs.ARCHIVE_PATH, {}).get('positions') or []
                rs._office['cycle']['fresh'] = rs._oe.fresh_view(table, rs._office.get('deepNow') or [], [c_['mint'] for c_ in kcases_ if c_.get('cleared')],
                                                           rs._office.get('lastMints'), [{**c_['row'], 'opp': c_['rank'], 'tier': c_['status']} for c_ in kcases_ if c_['status'] in ('READY', 'CONTENDING')], arch_p_ + list(rs._office.get('pos', {}).values()), now,
                                                           (rs._office.get('intake') or {}).get('cooled'))
                rs._office['cycle']['fresh']['candles'] = {k_: (rs._office.get('candleStat') or {}).get(k_) for k_ in ('allocFirst', 'allocBefore', 'loaded')}
                hv_ = sorted(rs._fuse._f((x_.get('vitals') or {}).get('ageH')) * 60 for x_ in table if x_.get('mint') in set(held_m) and (x_.get('vitals') or {}).get('ageH') is not None)
                rs._office['cycle']['fresh']['ageHeldMin'] = round(hv_[len(hv_) // 2], 1) if hv_ else None
                rs._office['index'] = rs._oe.active_index(table, rs._office.get('seen'), now, rs._agents.get('laneCap'))   # 🗂 the ONE active candidate index (recomputed from this pass)
            except Exception as e:
                print('fresh view:', e)
            rs._office['lastMints'] = [x_.get('mint') for x_ in table]
        except Exception as e:
            print('cycle view:', e)
        try:   # 👁 every exit still being watched gets its reading (the trail replay's missing half)
            await rs._after_step(now)
        except Exception as e:
            print('after path:', e)
        try:   # 🏢 the rest of the office on the SAME snapshot: Archivist files + settles, exits are confirmed, the Judge scores all ten
            rs._office_pass(st, table, now, rcfg_, jp, arch_, cour_, tid_r, (rs.time.perf_counter() - t_tick) * 1000)
        except Exception as e:
            print('office:', e)
        try:   # 🕸 the intake registry's stamps for this pass (agent intake · deep review · cleared) + the turnover of the desk
            rs._intake_after(table, kcases_, now)
        except Exception as e:
            print('intake after:', e)
        try:   # 🔁 EVERY SEAT, EVERY CYCLE: with Agent Control on, a pass that is not followed by a tier tick within 30s wakes one — each held seat
            # gets a fresh HOLD / PROTECT / TAKE / EXIT / SWAP stamped on THIS pass's read (the same tick that would have run anyway, earlier)
            if (rcfg_.get('agentControl') and rs._is_keeper() and not rs.os.environ.get('PYTEST_CURRENT_TEST') and now - rs._fuse._f(rs._office.get('tickAt')) > 30
                    and now - rs._fuse._f(rs._office.get('cycleWakeAt')) > 30):
                rs._office['cycleWakeAt'] = now
                rs.asyncio.ensure_future(rs._prime_tick(rs.time.time()))
        except Exception as e:
            print('cycle wake:', e)
        try:   # 🪑 an empty agent seat + a candidate that just CLEARED → the existing tier tick runs now instead of up to a tick later (≤ once per 30s;
            # no new loop, no new fetch: the tick it wakes is the one that would have run anyway)
            seat_ = rs._agents.get('seat') or {}
            if (rcfg_.get('agentControl') and seat_.get('empty') and rs._is_keeper() and now - rs._fuse._f(rs._office.get('seatWakeAt')) >= rs._oe.SEAT_TARGET_AUTO and not rs.os.environ.get('PYTEST_CURRENT_TEST')
                    and (rs._office.get('courier') or {}).get('health') != 'BAD' and seat_.get('movesLeft') and not rs._oe.policy(rcfg_)['manual'] and rs._oe.ready(rs._office['boot'], now)['live']
                    and any(c_['cleared'] and c_['mint'] not in {x_.get('mint') for x_ in ((rs._agents.get('card') or {}).get('seats') or []) if x_.get('mint')} for c_ in kcases_)):
                rs._office['seatWakeAt'] = now; rs._office['seatWakes'] = int(rs._office.get('seatWakes') or 0) + 1
                rs.asyncio.create_task(rs._prime_tick(rs.time.time()))
        except Exception as e:
            print('seat wake:', e)
        try:   # ⏱ THE 5-MINUTE ROUNDS: every candidate of the new-entry universe moves round 1 → 2 → 3 → ENTER / REJECT / COOLDOWN
            rs._rounds_pass(table, now)
        except Exception as e:
            print('rounds:', str(e)[:120])
        try:   # a read-only copy of exactly what GET /admin/agents answers (for checking the real page without an HQ sign-in) — ≤ once a minute
            if now - rs._fuse._f(rs._agents.get('viewSavedAt')) >= rs.VIEW_SAVE_SEC:
                vp_ = rs.DATA_DIR / 'agents_view.json'; vt_ = vp_.with_suffix('.tmp')
                vt_.write_bytes(rs._agents_page_body()); vt_.replace(vp_)   # the SAME bytes the page gets (already serialized: no second 600 KB dump per pass)
                rs._agents['viewSavedAt'] = now
        except Exception:
            pass
        try:   # 🔎 the narrative packet for the strongest candidates only (background; one job at a time; cached by TTL)
            rows_by_ = {r_.get('mint'): r_ for r_ in rows}
            rs.asyncio.ensure_future(rs._research_tick([c_ for c_ in kcases_ if c_['status'] != 'TRACKING'][:12], rows_by_, now))
        except Exception as e:
            print('research start:', e)
        try:   # 🔁 ONE LINE PER ~60s CYCLE: what the office looked at, what it found, what each seat did, how fresh every input was
            rs._office_cycle_log(table, now)
        except Exception as e:
            print('cycle log:', e)
        try:   # ⚙ the kernel's case files on disk each pass (read-only snapshot: what is READY, what holds each coin back) — read THIS first when no fill happens
            rs._json_save(rs.DATA_DIR / 'agents_duty.json', {'at': now, 'ready': sum(1 for c_ in kcases_ if c_['cleared']), 'byStatus': rs._tk.KERNEL.metrics(now)['byStatus'],
                                                       'cases': [{'symbol': c_['symbol'], 'status': c_['status'], 'rank': c_['rank'], 'cleared': c_['cleared'], 'why': str(c_.get('kwhy') or '')[:120],
                                                                  'blocked': [k_[2] for k_ in c_['checks'] if not k_[1]]} for c_ in kcases_[:25]]})
        except Exception:
            pass
    except Exception as e:
        print('agents:', e)


def _arch_verify(arch):
    """🗄 The archive's hash-chain check, incremental (office.verify_inc): the full chain at most every 5 min, new records in between."""
    rs = _rs()
    bad, m = rs._of.verify_inc(arch, rs._verify_memo.get('m'), rs.time.time())
    rs._verify_memo['m'] = m
    return bad

