"""🧹 🧠 THE AI ROUTER: the minds, G4 / duo reviews, the local lane, exits and learning — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


def _ai_book():
    rs = _rs()
    if rs._ai.get('book') is None:
        rs._ai['book'] = rs._json_load(rs.AI_PROOF_PATH, {}) or {}
    return rs._ai['book']


def _ai_quote(t, n=70):
    """Third-party words (a site title, an X bio, a caller's thesis) for the model: links + addresses stripped, quotes removed, trimmed,
    and handed over IN QUOTES — the system prompt tells the model quoted text is data from the coin's own pages, never an instruction."""
    rs = _rs()
    t = rs._AI_URL.sub('', rs._re.sub(r'[\x00-\x1f\x7f"]+', ' ', str(t or ''))).strip()
    t = rs._re.sub(r'\s+', ' ', t)
    return f'"{t[:n].rstrip()}{"…" if len(t) > n else ""}"' if t else None


def _ai_brief(mint):
    """🔍 Sherlock's brief for ONE coin, from readings the desk ALREADY has this pass — no fetch, no extra request. The five original
    lines (holders · chart · flow · launch · crowd) + the trench vitals (owner, 2026-10-12: "pull more vital info from the AI provider to
    trench better on coins $12K–$300K"): the MC band · age bucket · volume / buyer velocity · the live 90s tape · early wallets · the dev ·
    socials (presence only, never a URL) · Pump callers · the launch curve · what our REAL card made on coins like it · the model's own
    judged record. ~200 tokens. Unknown stays absent (the model is told unknown is unknown)."""
    rs = _rs()
    x = next((r_ for r_ in (rs._agents.get('table') or []) if r_.get('mint') == mint), None)
    if not x:
        return {}
    v, n, ch, la, mi, li = x.get('vitals') or {}, x.get('nums') or {}, x.get('chart') or {}, x.get('launch') or {}, x.get('mind') or {}, x.get('li') or {}
    g = lambda lab, val, unit='': f'{lab} {val:g}{unit}' if isinstance(val, (int, float)) and not isinstance(val, bool) else None
    j = lambda *xs: ' · '.join(t_ for t_ in xs if t_) or None
    now = rs.time.time()
    mc = rs._fuse._f(v.get('mcap'))
    band = (f"{rs._uni.trench_band(mc) or 'trench'} · ${mc / 1e3:.0f}K cap, inside your {rs._uni.band_word()} band" if rs._uni.under_cap({'mcap': mc})
            else f"${mc / 1e3:.0f}K cap — outside your {rs._uni.band_word()} band" if mc > 0 else None)
    vpm, bpm = rs._opp.velocity(x)
    at_, w_ = rs._flow_now.get(x.get('pair')) or (0, None)
    w_ = w_ if w_ and now - rs._fuse._f(at_) <= 120 else None
    pc_ = (rs._pump_calls.get('map') or {}).get(mint)
    pcs = rs._pc.summary(pc_) if pc_ else None
    lead_ = (pcs or {}).get('lead') or {}
    try:
        mem_ = rs._real_mem(now) or {}
        est_, cell_ = rs._rm.estimate(mem_, rs._rm.feats(ch.get('state'), (ch.get('entry') or [None, None])[1] if len(ch.get('entry') or []) > 1 else None, '', li.get('phase'), li.get('cls'), v.get('ageH'))) if mem_.get('cells') else (None, None)
    except Exception:
        est_, cell_, mem_ = None, None, {}
    rec_ = rs._ail.record(rs._ai_book())
    try:
        dev_dump = rs._tcrew.dev_dumping(x)
    except Exception:
        dev_dump = False
    soc = [k_ for k_, on_ in (('site', x.get('site') or v.get('site')), ('X', x.get('x') or v.get('x')), ('Telegram', v.get('tg'))) if on_]
    # 🌐 SITE / X / STORY from the coin's own research packet (social_research: the site and X read by our headless browser)
    pk = x.get('social') or (rs._social.get('cache') or {}).get(mint) or {}
    ws, xs, cr, nar = pk.get('website') or {}, pk.get('x') or {}, pk.get('cross') or {}, pk.get('narrative') or {}
    mm_ = {'match': 'shows THIS mint', 'yes': 'shows THIS mint', 'mismatch': 'shows a DIFFERENT mint', 'no': 'shows a DIFFERENT mint'}
    lp_ = rs._fuse._f(xs.get('lastPostAt'))
    # 📈 CHART SHAPE from the agents' own read of the live 1-minute candles (chart_intel features)
    cf = ch.get('f') or (((rs._office.get('charts') or {}).get(mint) or {}).get('f')) or {}
    px_c, sup_, res_ = rs._fuse._f(cf.get('px')), rs._fuse._f(cf.get('support')), rs._fuse._f(cf.get('resistance'))
    ld_ = (pcs or {}).get('lead') or {}
    fa_ = rs._fuse._f(ld_.get('at') or (pcs or {}).get('lastAt'))
    # 👤 CREATOR / DEPLOYER from caches the desk already holds: Jupiter's dev launch record, our holder scan's creator + its rep, the launch read
    cw_ = rs._ja.crew((rs._jup_facts.get(mint) or (0, None))[1] or {})
    it_ = (rs._intel_cache.get(mint) or (0, {}))[1] if isinstance(rs._intel_cache.get(mint), (tuple, list)) else {}
    try:
        cfl_, crep_ = rs._creator_state(it_) if it_ else (False, None)
    except Exception:
        cfl_, crep_ = False, None
    lf_ = rs._launch_facts.get(mint) or {}
    return {k_: v_ for k_, v_ in {
        'holders': j(g('top10', v.get('top10'), '%'), g('dev', v.get('dev'), '%'), g('bundled', v.get('bundledN')), g('snipers', v.get('snipersN')), g('holders', v.get('holders')),
                     g('organic vol', v.get('organic'), '%'), 'scan passed' if v.get('safe') is True else 'scan FAILED' if v.get('safe') is False else None),
        'chart': j(ch.get('state'), ' / '.join(str(e_) for e_ in (ch.get('entry') or [])[:2]) or None, (ch.get('q') or {}).get('state')),
        'flow': j(g('1h', n.get('c1'), '%'), g('pace', n.get('pace'), 'x'), g('pool chg', n.get('liqD'), '%'), g('holders chg', n.get('holdD'), '%'), x.get('mp'), v.get('read')),
        'launch': j(la.get('pad'), la.get('type'), g('curve', la.get('curvePct'), '%'), li.get('cls') if li.get('cls') not in (None, 'UNKNOWN') else None, li.get('phase')),
        'crowd': j(mi.get('narr'), g('callers', mi.get('callers')) if mi.get('callers') else None, 'copy-paste swarm' if mi.get('swarm') else None, g('bots', mi.get('bots'), '%') if mi.get('bots') else None),
        'band': band,
        'fresh': li.get('fresh') or rs._opp.fresh_bucket(x)[0],
        'velocity': j(f"${vpm:,.0f}/min traded" if vpm is not None else None, f"{bpm:.1f} buys/min" if bpm is not None else None, g('5m $', n.get('v5'))),
        'tape': j(f"last 90s ${rs._fuse._f(w_.get('buyUsd')):,.0f} bought vs ${rs._fuse._f(w_.get('sellUsd')):,.0f} sold", g('trades', w_.get('n')), g('price', w_.get('pxChg'), '%'),
                  f"biggest sell ${rs._fuse._f((w_.get('bigSell') or {}).get('usd')):,.0f}" if (w_.get('bigSell') or {}).get('usd') else None) if w_ else None,
        'tapeRead': rs._flow.tape_read(w_) if w_ else None,
        'early': j(g('first-10 buyers hold', li.get('first10'), '%'), g('first-25 hold', li.get('first25'), '%'), f"cluster {li['cluster']}" if li.get('cluster') else None,
                   f"early wallets {str(li['ewp']).lower()}" if li.get('ewp') else None, f"selling pressure {str(li['press']).lower()}" if li.get('press') not in (None, 'NONE') else None,
                   g('wallets with a dump record', li.get('danger')) if rs._fuse._f(li.get('danger')) else None),
        'dev': j(g('dev holds', v.get('dev'), '%'), 'the dev is SELLING now' if dev_dump else None),
        'socials': ('set: ' + ', '.join(soc)) if soc else 'no site / X set',
        'creator': j(cw_.get('why') if cw_.get('kind') != 'unknown' else None, 'creator FLAGGED (rug report / bot)' if cfl_ else None,
                     f"creator rep {crep_}" if crep_ else None, g('dev holds', v.get('dev'), '%'), 'the dev is SELLING now' if dev_dump else None,
                     f"{len(lf_.get('bundled') or [])} bundled wallets at launch" if lf_.get('bundled') else None,
                     f"{len(lf_.get('snipers') or [])} snipers at launch" if lf_.get('snipers') else None),
        'calls': j(f"{pcs.get('callers') or 1} Pump caller{'' if (pcs.get('callers') or 1) == 1 else 's'}" + (f" ({pcs['pro']} proven)" if pcs.get('pro') else ''),
                   f"first called at ${rs._fuse._f(pcs.get('firstMc')) / 1e3:.0f}K" if pcs.get('firstMc') else None, g('best since the call', lead_.get('mult'), '×'),
                   f"lead caller {'verified · ' if ld_.get('verified') else ''}{int(rs._fuse._f(ld_.get('views'))):,} views" if ld_.get('views') or ld_.get('verified') else None,
                   f"called {int((now - fa_) / 60)} min ago" if fa_ > 0 else None, f"thesis {rs._ai_quote(ld_.get('thesis'))}" if ld_.get('thesis') else None,
                   'copy-paste caller swarm' if mi.get('swarm') else None, ('slang ' + ', '.join(map(str, (mi.get('slang') or [])[:3]))) if mi.get('slang') else None) if pcs else None,
        'site': j(('site loads' if ws.get('reachable') else 'site set but does NOT load') if ws.get('url') else None, rs._ai_quote(ws.get('title'), 60) if ws.get('reachable') else None,
                  mm_.get(str(ws.get('mintMatch') or '').lower()), 'links its X' if ws.get('x') else None, 'links a Telegram' if ws.get('tg') else None) if ws else None,
        'xinfo': j(('X account readable' if xs.get('available') else 'X set but not readable') if xs.get('url') else None, f"{int(rs._fuse._f(xs.get('followers'))):,} followers" if xs.get('followers') is not None else None,
                   f"last post {int((now - lp_) / 3600)}h ago" if lp_ > 0 else None, 'mentions this mint' if xs.get('mintMentioned') else None,
                   f"bio {rs._ai_quote(xs.get('bio'), 60)}" if xs.get('bio') else None) if xs else None,
        'story': j(nar.get('class'), f"{rs._fuse._f(nar.get('confidence')) * 100:.0f}% sure" if nar.get('class') else None, ('keywords ' + ', '.join(map(str, (nar.get('keywords') or [])[:4]))) if nar.get('keywords') else None,
                   'COPYCAT of another coin' if cr.get('copycat') else None, 'site / X CONFLICT' if cr.get('conflict') else None, ('flags ' + ', '.join(map(str, (cr.get('flags') or [])[:3]))) if cr.get('flags') else None) if (nar or cr) else None,
        'shape': j(f"last candles {cf['seq']} (G up · R down)" if cf.get('seq') else None,
                   ' · '.join(f'{lab} {cf[k_]:+.0f}%' for k_, lab in (('r5', '5m'), ('r15', '15m'), ('r30', '30m')) if isinstance(cf.get(k_), (int, float))) or None,
                   f"{cf.get('hh', 0)} higher highs / {cf.get('hl', 0)} higher lows / {cf.get('lh', 0)} lower highs / {cf.get('ll', 0)} lower lows" if cf.get('n') and 'hh' in cf else None,
                   f"at {rs._fuse._f(cf.get('pos')) * 100:.0f}% of its range, {rs._fuse._f(cf.get('distHigh')):.0f}% under the high" if cf.get('pos') is not None and cf.get('distHigh') is not None else None,
                   f"pulled back {rs._fuse._f(cf.get('pullback')):.0f}%" if rs._fuse._f(cf.get('pullback')) > 0 else None,
                   (('LOST its germ floor (the base its biggest run was born on) — the run is dead until back above' if (cf.get('germ') or {}).get('lost')
                     else f"germ floor (base of its +{rs._fuse._f(cf['germ'].get('runPct')):.0f}% run) {rs._fuse._f(cf['germ'].get('dist')):.0f}% below") if isinstance(cf.get('germ'), dict) else None),
                    (f"5-min germ {rs._fuse._f(cf['germ5'].get('dist')):.0f}% below" + (' — 1m AND 5m both sit on the germ: the cheap entry the run restarts from' if rs._fuse._f(cf['germ5'].get('dist')) <= 25 and isinstance(cf.get('germ'), dict) and rs._fuse._f(cf['germ'].get('dist')) <= 8 else ''))
                    if isinstance(cf.get('germ5'), dict) else None,
                   *[(f"{lab} FVG support: price INSIDE the gap" if g_.get('inside') else f"{lab} FVG support {rs._fuse._f(g_.get('dist')):.1f}% below ({g_.get('open')} open)")
                     for lab, g_ in (('1m', cf.get('fvg')), ('5m', cf.get('fvg5'))) if isinstance(g_, dict)],
                   ('breakout FAILED' if cf.get('breakFailed') else f"base, breakout held {cf.get('breakHeld')}×" if cf.get('base') and cf.get('breakHeld') else 'basing' if cf.get('base') else None),
                   f"support {(1 - sup_ / px_c) * 100:.0f}% below" if 0 < sup_ < px_c else None, f"resistance {(res_ / px_c - 1) * 100:.0f}% above" if res_ > 0 and px_c > 0 and res_ > px_c else None,
                   g('volume trend', cf.get('volTrend'), '×'), g('squeeze', cf.get('squeeze'), '×'), 'momentum decaying' if cf.get('decay') else None,
                   f"trend {cf.get('trend')} · chop {cf.get('chop')} · extension {cf.get('ext')} /100" if cf.get('trend') is not None else None) if cf.get('n') else None,
        'curve': (f"on the launch curve {rs._fuse._f(v.get('curvePct') or la.get('curvePct')):.0f}%" if (v.get('curve') or la.get('curvePct')) and not la.get('graduated') else 'graduated' if la.get('graduated') else None),
        'twins': rs._rm.twins(rs._real_trades(), rs._rm.feats(ch.get('state'), (ch.get('entry') or [None, None])[1] if len(ch.get('entry') or []) > 1 else None, '', li.get('phase'), li.get('cls'), v.get('ageH'))),
        'memory': (f"our real card: coins like this ({cell_}) returned {est_:+.0f}% typical (all real trades {rs._fuse._f(mem_.get('base')):+.0f}%, n {mem_.get('n') or 0})" if cell_
                   else f"our real card's typical trade {rs._fuse._f(mem_.get('base')):+.0f}% (n {mem_.get('n')})" if mem_.get('n') else None),
        'record': (j(*[f"{k_} {r_['med']:+.0f}% ({r_['n']})" for k_, r_ in sorted(rec_.items(), key=lambda kv: -kv[1]['n']) if k_ != 'ALL'][:3])
                   + f" · all {rec_['ALL']['med']:+.0f}% ({rec_['ALL']['n']}) — your own judged calls, 15 min later") if rec_.get('ALL') else None,
    }.items() if v_}


def _ai_learn_note(role, c, res, now):
    """A stance on a LIVE candidate is noted for judging (never a closed trade, never a held coin's review)."""
    rs = _rs()
    st = ((res or {}).get('advice') or {}).get('stance')
    if not st or role == 'judge' or c.get('result') is not None or not c.get('mint'):
        return
    px = rs._fuse._f(c.get('price')) or rs._fuse._f((rs._jup_px_cache.get(c['mint']) or (0, 0))[1])
    ad_ = (res or {}).get('advice') or {}
    rs._ai['book'] = rs._ail.note(rs._ai_book(), role, c['mint'], st, px, now, c.get('symbol'), len(ad_.get('risk_flags') or []), ad_.get('scout'), bool(c.get('atFill')),
                            bool(rs._tch.hits(rs._teach_state(), c.get('symbol'), c['mint'])), phase=ad_.get('chart_phase'), ephase=c.get('phase'), src=(res or {}).get('source'), predict=ad_.get('predict_pct'))   # 🎓 a read on a coin the owner taught is graded on its own (TAUGHT)


async def _ai_learn_settle(now):
    rs = _rs()
    await rs._ai_exit_settle(now)
    due = sorted({c_['mint'] for c_ in (rs._ai_book().get('open') or []) if now - rs._fuse._f(c_.get('at')) >= rs._ail.JUDGE_SEC})[:40]
    if not due:
        return
    try:
        px = await rs._jup_prices(due, judge=True)
    except Exception:
        return   # a pass where the price source answers nothing is not judged
    if not px:
        return
    n0 = len(rs._ai_book().get('done') or [])
    rs._ai['book'] = rs._ail.settle(rs._ai_book(), px, now)
    if len(rs._ai['book'].get('done') or []) != n0 and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        rs._json_save(rs.AI_PROOF_PATH, rs._ai['book'])


async def _ai_exit_settle(now):
    """🧠☠ exit reads ≥ 15 min old get what the coin really did (the judging price source, never a rate-limited zero)."""
    rs = _rs()
    b_ = rs._ai_exit_book()
    due = sorted({o_['mint'] for o_ in (b_.get('open') or []) if now - rs._fuse._f(o_.get('at')) >= rs._er.JUDGE_SEC})[:40]
    if not due:
        return
    try:
        px = await rs._jup_prices(due, judge=True)
    except Exception:
        return
    n0 = len(b_.get('done') or [])
    rs._ai['exitBook'] = rs._er.settle(b_, px or {}, now)
    if len(rs._ai['exitBook'].get('done') or []) != n0 and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        rs._json_save(rs.AI_EXIT_PATH, rs._ai['exitBook'])


def _ai_weights(now):
    """{mint: ×0.9 … ×1.1} — ONLY for stances proven on the model's own judged record (empty until then)."""
    rs = _rs()
    try:
        if not rs._ai_learn_on():
            return {}
        return rs._ail.weights(rs._ai['notes'], rs._ail.record(rs._ai_book()), now, rs._ail.vital_record(rs._ai_book()))
    except Exception:
        return {}


def _ai_learn_on():
    """The owner's switch (realCfg `agentAiLearn`, on by default): off = the model is still asked, shown and judged — it just weighs nothing."""
    rs = _rs()
    return bool(rs._prime.clean_cfg((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}).get('agentAiLearn'))


def _ai_exit_book():
    rs = _rs()
    if rs._ai['exitBook'] is None:
        rs._ai['exitBook'] = rs._json_load(rs.AI_EXIT_PATH, {}) or {}
    return rs._ai['exitBook']


def _ai_exit_effects(cfg_t, now):
    """{mint: 'ride' | 'tight' | 'widen'} for Reaper — fresh reads of a word its own graded record PROVED; {} while it is in shadow or switched off.
    + 🪜 the chart's own WIDEN (higher lows over the floor on a red seat), graded on ITS record (prov 'chart'), never pooled with the models'."""
    rs = _rs()
    try:
        on_ = (cfg_t or {}).get('agentAiExit', True) is not False
        out_ = rs._er.effects(rs._ai['exit'], rs._er.record(rs._ai_exit_book()), now, on=on_)
        for m_, w_ in rs._er.effects(rs._chart_widen, rs._er.record(rs._ai_exit_book(), 'chart'), now, on=on_).items():
            out_.setdefault(m_, w_)
        return out_
    except Exception:
        return {}


def _chart_widen_note(rep, now):
    """🪜 EVIDENCE TO WIDEN (owner, 2026-10-15: "adjusting SL when down and seeing higher lows"): a RED agent seat whose live chart shows 2+ higher
    lows, no lower low, and a tape that is not seller-led is a chart WIDEN read — noted at its price and graded 15 min later like the models'
    words (exit_read, prov 'chart'). It moves Reaper's stop only once ITS record proves it (≥ 20 graded, typical +2% after)."""
    rs = _rs()
    try:
        for r_ in rep or []:
            ch_, m_ = r_.get('chart') or {}, r_.get('mint')
            fl_ = (r_.get('flow') or {}).get('state')
            if not m_ or rs._fuse._f(r_.get('pct')) >= 0 or r_.get('action'):
                rs._chart_widen.pop(m_, None); continue
            if int(rs._fuse._f(ch_.get('hl'))) >= 2 and int(rs._fuse._f(ch_.get('ll'))) == 0 and fl_ != 'SELLERS':
                rs._chart_widen[m_] = {'word': 'WIDEN', 'at': now}
                rs._ai['exitBook'] = rs._er.note(rs._ai_exit_book(), m_, 'WIDEN', rs._fuse._f(r_.get('px')), r_.get('pct'), now, r_.get('symbol'), prov='chart')
            else:
                rs._chart_widen.pop(m_, None)
    except Exception as e:
        print('chart widen:', str(e)[:80])   # fillQ {mint: at} = coins that just took a real seat


def _ai_exit_words(cfg_t, now):
    """{mint: 'ride' | 'tight'} — the model's FRESH exit reads (proven or not): they only set how many 📸 snapshots a profit-side exit needs."""
    rs = _rs()
    try:
        return rs._er.fresh_words(rs._ai['exit'], now, on=(cfg_t or {}).get('agentAiExit', True) is not False)
    except Exception:
        return {}


def _ai_log(role, case, res, asked=False):
    """One model answer → the decision log the page shows (role · coin · stance · confidence · the model's sentence · what the kernel
    itself said at that moment). A cached answer is the SAME decision — not logged twice. Display only: nothing reads this back."""
    rs = _rs()
    ad = (res or {}).get('advice') or None
    if not asked and (not ad or res.get('cached')):
        return
    sn_ = case.get('_snap') or (rs._ai_snap(case.get('mint'), case.get('pair')) if case.get('mint') else None)   # 📸 the jobs hand in the raw case: rebuild its snapshot (memory only)
    case = {**case, '_snap': sn_}
    row = {'at': round(rs._fuse._f(res.get('at')) or rs.time.time(), 1), 'role': role, 'mint': case.get('mint'), 'symbol': case.get('symbol'), 'source': res.get('source'), 'label': res.get('label'),
           'ms': res.get('ms'), 'stance': (ad or {}).get('stance'), 'delta': (ad or {}).get('confidence_delta'), 'summary': (ad or {}).get('summary'),
           **{k_: (ad or {}).get(k_) for k_ in ('risk_flags', 'narrative', 'creator_context', 'conflict_resolution')}, 'kernel': case.get('status') or case.get('state') or (f"closed {case.get('result'):+.1f}%" if isinstance(case.get('result'), (int, float)) else None),
           'trigger': case.get('trigger') if isinstance(case.get('trigger'), str) else None, 'asked': bool(asked), 'why': None if ad else str(res.get('why') or 'no provider answered')[:120],
           'predict': (ad or {}).get('predict_pct'), 'snap': (case.get('_snap') or {}).get('pts'), 'snapSrc': (case.get('_snap') or {}).get('src'), 'word': case.get('_word')}   # 📸 the chart the model judged (the page draws it beside the answer)
    rs._ai['log'] = (rs._ai['log'] + [row])[-rs.AI_LOG_KEEP:]


def _ai_cfg():
    rs = _rs()
    return rs._json_load(rs.AI_CFG_PATH, {}) or {}


def _ai_http():
    rs = _rs()
    if rs._ai['http'] is None:
        rs._ai['http'] = rs.httpx.AsyncClient(timeout=20)   # ONE pooled client for every provider
    return rs._ai['http']


def _ai_view(now=None, light=False):
    """The page's AI block: the provider rows (state, model, latency, failures — never a key), totals, and the advice per coin.
    `light` = the office payload's copy (compact rows, the newest 12 notes); the full rows come from GET /admin/ai/providers."""
    rs = _rs()
    now = rs.time.time() if now is None else now
    v = rs._air.ROUTER.view(rs.os.environ, rs._ai_cfg(), now)
    notes = {m_: n_ for m_, n_ in rs._ai['notes'].items()}
    if light:
        keep = sorted(notes, key=lambda k_: -max(rs._fuse._f(x_.get('at')) for x_ in notes[k_].values()))[:12]
        return {'providers': [{k_: r_.get(k_) for k_ in ('key', 'label', 'priority', 'enabled', 'state', 'why', 'model', 'host', 'keySet', 'hint', 'lastMs', 'lastOkAt', 'lastErr', 'failures', 'requests', 'timeouts', 'coolSec')} for r_ in v['providers']], 'active': v['active'],
                'totals': v['totals'], 'notes': {m_: {ro_: {k_: n_.get(k_) for k_ in ('source', 'label', 'advice', 'at')} for ro_, n_ in notes[m_].items()} for m_ in keep},
                'lastAt': rs._ai['lastAt'], 'lastMs': rs._ai['lastMs'], 'every': rs.AI_EVERY, 'localLane': {**{k_: rs._local_lane.get(k_) for k_ in ('n', 'last', 'busy', 'every', 'whyEvery')}, 'watch': rs._aic.watch_view(rs._local_lane.get('watch') if rs._local_lane.get('watch') is not None else (rs._json_load(rs.LOCAL_WATCH_PATH, {}) or {}), rs._chat.get('settings') or {}, rs.time.time(), rs._local_lane.get('every'), rs._local_lane.get('whyEvery'))}, 'log': rs._ai['log'][-20:], 'metrics': v.get('metrics'),
                'model': next((r_.get('model') for r_ in v['providers'] if r_.get('key') == v['active']), None), 'learn': {**rs._ail.view(rs._ai_book()), 'on': rs._ai_learn_on()}, 'predict': {k_: rs._ail.predict_record(rs._ai_book(), None if k_ == 'all' else k_) for k_ in ('all', 'lan', 'local', 'openrouter', 'groq')},
                'duet': rs._duet.view(rs._duet.record(rs._ai_book().get('done'))),   # 🤝 Gemma + Qwen on one record: agree %, who wins splits
                'report': rs._ail.model_report(rs._ai_book(), {k_: dict(rs._air.ROUTER.stats.get(k_) or {}) for k_ in rs._air.PROVIDERS}, {r_.get('key'): r_.get('model') for r_ in v['providers']}),   # 🧠 every model on one yardstick
                'slip': {'firstPct': rs._fw.BUY_SLIP_FIRST / 100, 'retryPct': rs._fw.BUY_SLIP_MAX / 100, 'retries': rs._fw.BUY_SLIP_RETRIES},
                'exit': rs._er.view(rs._ai_exit_book(), rs._ai['exit'], now, on=((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}).get('agentAiExit', True) is not False)}
    return {**v, 'notes': notes, 'rounds': rs._ai['rounds'], 'lastAt': rs._ai['lastAt'], 'lastMs': rs._ai['lastMs'], 'every': rs.AI_EVERY}


def _ai_jobs(now):
    """What is worth a model's time this round (never every coin, never a price tick) → [(role, case, urgency, prio)] best first:
    the owner's review list (0) → a CONFLICT the Manager resolves (1) → READY coins in the band (2) → an AMBIGUOUS setup for Devil (3)
    → the top in-band contender (4) → the newest Judge review of a real exit (5). A case already answered in this material STATE is
    skipped (counted) — the router would only hand back its cached answer. Low priorities (≥ DEFER_PRIO) defer while the model is busy."""
    rs = _rs()
    p = rs._office.get('payload') or {}
    out, P = [], rs._air.PRIO
    for r_ in (p.get('ownerReview') or [])[:2]:
        if r_.get('mint'):
            out.append(('owner', {'mint': r_['mint'], 'symbol': r_.get('symbol'), 'state': r_.get('state'), 'why': r_.get('why'), 'cap': r_.get('mc'),
                                  'trigger': (r_.get('trigger') or {}).get('state'), 'devil': (r_.get('devil') or {}).get('severity'), 'pending': r_.get('pending')}, 'high', P['owner']))
    cands = (p.get('kernel') or {}).get('candidates') or []
    by_m = {c_.get('mint'): c_ for c_ in cands}
    for m_, at_ in sorted((rs._ai.get('fillQ') or {}).items(), key=lambda kv: kv[1])[:1]:   # 📍 ASK AT THE FILL: the coin that just took a real seat, on the live tape —
        rs._ai['fillQ'].pop(m_, None)                                                      # a record-only read graded on how that real trade ends (ai_learn AT:FILL)
        if now - rs._fuse._f(at_) <= 180 and by_m.get(m_):
            out.append(('devil', {**by_m[m_], 'atFill': True}, 'high', P['manager']))
    open_ = [c_ for c_ in cands if c_.get('status') in ('READY', 'CONTENDING')]
    inband = [c_ for c_ in open_ if rs._uni.under_cap({'mcap': c_.get('cap')})]
    asked_ = {c_.get('mint') for _r, c_, _u, _p in out}

    def add(role_, c_, urg_, pr_):
        if c_.get('mint') in asked_:
            return
        if rs._air.ROUTER.fresh(rs._ai_case(c_), role_, now):
            rs._air.ROUTER.totals['skipped'] += 1   # same coin, same state: the cached answer stands
            return
        out.append((role_, c_, urg_, pr_)); asked_.add(c_.get('mint'))
    for c_ in [c_ for c_ in inband if rs._ai_conflict(c_)][:1]:
        add('manager', c_, 'high', P['manager'])
    # 🧠☠ THE EXIT READ (owner, 2026-10-14: "AI should help Trigger and Reaper — smarter, cleaner exits"): each coin the agents HOLD gets one
    # read about once a minute (fresh ≤ 60s = skipped). Reaper never waits on it: it uses the cached word, and only once its record proves it.
    held_ = [r_ for r_ in (rs._office.get('reports') or []) if r_.get('mint') and not r_.get('action')]
    for r_ in sorted(held_, key=lambda r_: ('📸' not in str(r_.get('evidence') or ''), r_.get('owner') != 'you', -abs(rs._fuse._f(r_.get('pct')))))[:2]:   # 🤝 a coin Reaper WANTS to sell is read first: the model is its partner on that call   # 👤 your seats are read first — the AI's suggestion on YOUR coin
        if now - rs._fuse._f((rs._ai['exit'].get(r_['mint']) or {}).get('at')) < 60:
            continue
        add('exit', {'mint': r_['mint'], 'pair': r_.get('pair'), 'symbol': r_.get('sym') or r_.get('symbol'), 'pct': r_.get('pct'), 'peak': r_.get('peak'), 'heldMin': r_.get('heldMin'),
                     'structure': (r_.get('thesis') or {}).get('structure'), 'phase': (r_.get('phase') or {}).get('phase') if isinstance(r_.get('phase'), dict) else r_.get('phase'),
                     'state': r_.get('state'), 'rule': r_.get('rule'), 'why': r_.get('evidence')}, 'high', P['exit'])
    for c_ in [c_ for c_ in inband if c_.get('status') == 'READY'][:2]:
        add('sherlock', c_, 'high', P['ready'])
    for c_ in [c_ for c_ in inband if rs._ai_ambiguous(c_)][:1]:
        add('devil', c_, 'normal', P['devil'])
    # (2026-10-13) no model call for a contender or a closed trade any more: only what can still STOP a buy is worth a call — the
    # owner's own review, a split desk, a coin about to take a seat, an ambiguous setup. The Judge's review is the engine's own (no model).
    return sorted(out, key=lambda j_: j_[3])[:rs.AI_JOBS]


def _ai_signals(c):
    """⚖ What the agents themselves say about this coin, in one line (Trigger · Devil · kernel status / rank · Warden · Sherlock's unknowns)."""
    rs = _rs()
    dv = [f"{d_[0]} {str(d_[1]).replace('_', ' ')}" for d_ in (c.get('devil') or []) if isinstance(d_, (list, tuple)) and len(d_) >= 2]
    parts = [f"Trigger {c['trigger']}" + (f" ({c['narrative']})" if c.get('narrative') else '') if c.get('trigger') else None,
             ('Devil ' + '; '.join(dv[:3])) if dv else 'Devil no objection' if c.get('trigger') else None,
             f"kernel {c['status']}" + (f" rank {round(rs._fuse._f(c.get('rank')))} vs READY {round(rs._tkb.READY_MIN)}" if c.get('rank') is not None else '') if c.get('status') else None,
             f"Warden ×{c['size']}" if c.get('size') is not None else None, ('unknown: ' + ', '.join(c['unknown'][:3])) if c.get('unknown') else None]
    return ' · '.join(x for x in parts if x) or None


def _ai_conflict(c):
    """The agents disagree: Trigger wants in (ENTER) while Devil grades a STRONG warning (not the hard wall)."""
    dv = c.get('devil') or []
    return c.get('trigger') == 'ENTER' and any(isinstance(d_, (list, tuple)) and len(d_) > 1 and d_[1] == 'STRONG_WARNING' for d_ in dv) and not any(
        isinstance(d_, (list, tuple)) and len(d_) > 1 and d_[1] == 'HARD_VETO' for d_ in dv)


def _ai_ambiguous(c):
    """Close to a call either way: CONTENDING within 20% of the READY line with Trigger ENTER / ARM, or READY with holders still unknown."""
    rs = _rs()
    near = c.get('status') == 'CONTENDING' and c.get('trigger') in ('ENTER', 'ARM') and rs._fuse._f(c.get('rank')) >= 0.8 * rs._tkb.READY_MIN
    return near or (c.get('status') == 'READY' and 'holders' in (c.get('unknown') or []))


def _ai_learned(now):
    """🎓 EVERYTHING THE DESK LEARNED, live, for every model case (owner, 2026-10-13: "all teachings and learnings really need to be wired
    live"): the rule lab's live rules · the Judge's + coach's live ranking causes · what each desk's own vote is worth on real money — and
    📈 the model's own chart-reading record. Rebuilt at most every 30s from state the desk already holds (no fetch)."""
    rs = _rs()
    if now - rs._learned_mem['at'] < 30:
        return rs._learned_mem
    out = []
    try:
        for d_, names_ in (rs._rlab.lessons(rs._lab_state()) or {}).items():
            out += [f"lab · {d_}: {n_}" for n_ in names_[:2]]
        out += [f"rank down: {k_} ({p_:+.0f})" for k_, p_ in sorted((rs._coach_pens(now) or {}).items(), key=lambda kv: kv[1])[:3]]
        ds_ = (rs._office.get('payload') or {}).get('deskStats') or {}
        for d_ in rs._jr.VOTE_DESKS:
            o_ = (ds_.get(d_) or {}).get('own') or {}
            g_, b_ = o_.get('go') or {}, o_.get('doubt') or {}
            if g_.get('med') is not None and b_.get('med') is not None and min(g_.get('n', 0), b_.get('n', 0)) >= 5:
                out.append(f"{d_}'s own vote: GO typical {g_['med']:+.1f}% vs DOUBT {b_['med']:+.1f}% on real money")
    except Exception as e:
        print('ai learned:', str(e)[:80])
    rs._learned_mem.update(at=now, learned=out[:8] or None, chart=rs._ail.chart_line(rs._ail.vital_record(rs._ai_book())))
    return rs._learned_mem


def _ai_owner(now):
    """👤 HOW THE OWNER TRADES, for every model case (owner, 2026-10-15: "agents and AI study why and when I enter, how I adjust SL / TP — I
    show them how to trench"): his hand moves graded 30 min later (owner_moves), the coins he picks (pick_style bands), and whether his own
    dragged lines did better than the agents' on closed real trades (office.owner_hand). One line, rebuilt every minute, no fetch."""
    rs = _rs()
    if now - rs._owner_line['at'] < 60:
        return rs._owner_line['v']
    out = []
    try:
        log_ = next((v for k_, v in rs._json_load(rs.OWNER_MOVES_PATH, {}).items() if isinstance(v, dict)), {})
        sm_ = rs._om.summary(log_)
        out += [f"{x_['label']} n{x_['n']}: {x_['good']} good / {x_['bad']} bad, coin typ {x_['medPct']:+.0f}% after" for x_ in sm_.values()][:5]
        so_ = rs._om.shakeouts(log_)
        if so_.get('n'):   # 🛑 the owner's lesson: his tight stops that sold a coin right before it ran
            out.append(f"his stops: {so_['shaken']} of {so_['n']} sold a coin that then ran 20%+ within 2h" + (f" ({', '.join(so_['coins'][:3])})" if so_['coins'] else ''))
        last_ = [r_ for r_ in (log_.get('rows') or []) if r_.get('pct') is not None and not r_.get('engine')][-3:]
        if last_:
            out.append('his latest: ' + ' | '.join(rs._om.why_line(r_) for r_ in last_))
        pl_ = (rs._json_load(rs.PICK_STYLE_PATH, {}) or {}).get('log') or []
        pw_ = rs._ps.words(rs._ps.profile(pl_))
        if pw_:
            out.append('his picks: ' + '; '.join(pw_[:4]))
        oh_ = rs._of.owner_hand((rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions'))
        y_, a_ = oh_.get('yours') or {}, oh_.get('agents') or {}
        if y_.get('n'):
            out.append(f"his dragged SL/TP: n{y_['n']} typ {y_['med']:+.1f}% vs agents' own lines n{a_.get('n')} typ {a_.get('med') if a_.get('med') is not None else 0:+.1f}%")
    except Exception as e:
        print('ai owner:', str(e)[:80])
    rs._owner_line.update(at=now, v=' · '.join(out) or None)
    return rs._owner_line['v']


def _agent_pred(t_, ch_, now):
    """🔮 THE AGENTS' PREDICTION for a real buy: what our own real trades that looked like this one made (real_memory.estimate over the entry's
    structure · door · launch phase · class · age) — written into the thesis, graded against the real exit (office.pred_record)."""
    rs = _rs()
    try:
        mem_ = rs._real_mem(now) or {}
        if not mem_.get('cells'):
            return None
        li_ = t_.get('li') or {}
        est_, cell_ = rs._rm.estimate(mem_, rs._rm.feats((ch_ or {}).get('state'), ((ch_ or {}).get('entry') or [None, None])[1] if len((ch_ or {}).get('entry') or []) > 1 else None,
                                                  (t_.get('bought') or {}).get('tag') or t_.get('tag') or '', li_.get('phase'), li_.get('cls'), (t_.get('vitals') or {}).get('ageH')))
        return {'pct': round(rs._fuse._f(est_), 1), 'why': cell_}
    except Exception:
        return None


def _ai_snap(mint, pair=None):
    """📸 The chart snapshot the model reads: the agents' own 1-minute rows (ai_snapshot), % vs the entry when the agents hold the coin."""
    rs = _rs()
    if not mint:
        return None
    try:
        if not pair:
            pair = next((r_.get('pair') for r_ in (rs._agents.get('table') or []) if r_.get('mint') == mint), None)
        if not pair:
            return None
        ent_ = rs._fuse._f(((rs._office.get('pos') or {}).get(mint) or {}).get('entry'))
        return rs._snp.snapshot(rs._office_bars(pair, mint, rs._snp.PTS), entry=ent_ if ent_ > 0 else None)
    except Exception as e:
        print('ai snap:', str(e)[:80])
        return None


def _ai_case(c):
    """A kernel candidate → the compact case the router sends (it whitelists again) + 🎓 the owner's teachings that fit the coin."""
    rs = _rs()
    lm_ = rs._ai_learned(rs.time.time())
    sn_ = rs._ai_snap(c.get('mint'), c.get('pair'))
    th_ = [f"your rule {k_} HITS this coin: {w_}" for k_, w_ in ((rs._office.get('taught') or {}).get(c.get('mint')) or {}).items()]
    return {**rs._ai_brief(c.get('mint')), 'signals': rs._ai_signals(c), 'theory': __import__('trench_theory').verdict(c)['line'], 'lessons': (th_ + rs._tch.for_case(rs._teach_state(), c.get('symbol'), c.get('mint')))[:7] or None,
            'learned': lm_['learned'], 'chartRec': lm_['chart'], 'predictRec': rs._ail.predict_line(rs._ail.predict_record(rs._ai_book())), 'candles': '; '.join(x_ for x_ in ((sn_ or {}).get('line'), rs._ccl.line(rs.time.time())) if x_), 'owner': rs._ai_owner(rs.time.time()), '_snap': sn_,
            **{k_: c.get(k_) for k_ in ('mint', 'symbol', 'status', 'rank', 'ageMin', 'cap', 'liq', 'vol5m', 'move5m', 'buyShare', 'narrative', 'trigger', 'size', 'unknown',
                                       'state', 'why', 'pending', 'result', 'cause', 'pct', 'peak', 'heldMin', 'rule', 'structure', 'phase')},
            'devil': [f"{d_[0]} {d_[1]}" for d_ in (c.get('devil') or []) if isinstance(d_, (list, tuple)) and len(d_) >= 2] if isinstance(c.get('devil'), list) else c.get('devil')}


def _feecat_packet():
    """🐱 Her open trades + the coins at the top of her pool (the agents' READY / CONTENDING), each with the vitals the desk already holds."""
    rs = _rs()
    st_ = rs._json_load(rs.DATA_DIR / 'feecats.json', {}) or {}
    pos_ = [{'symbol': p_.get('symbol'), 'pairAddress': p_.get('pairAddress'), 'costSol': p_.get('costSol'), 'peakPct': p_.get('peakChange'),
             'heldMin': round((rs.time.time() - rs._fuse._f(p_.get('openedAt') or p_.get('at'))) / 60) if (p_.get('openedAt') or p_.get('at')) else None}
            for c_ in sorted((st_.get('cats') or {}).values(), key=lambda c_: not c_.get('modelBrain')) for p_ in c_.get('positions') or []][:6]   # 🪟 her own cats' trades first: she reads what she runs
    cand_ = []
    for r_ in rs._agent_inherit_rows(limit=6):
        x_ = rs._tk.KERNEL.candidate(r_['mint']) or {}
        n_, v_, d_ = x_.get('nums') or {}, x_.get('vitals') or {}, rs._tk.KERNEL.dec.get(r_['mint']) or {}
        r1_ = lambda v, k=1: None if v is None else round(rs._fuse._f(v), k)
        cand_.append({'symbol': r_['symbol'], 'pairAddress': r_['pairAddress'], 'status': d_.get('status'), 'cap': r1_(v_.get('mcap'), 0), 'ageMin': r1_(rs._fuse._f(v_['ageH']) * 60, 0) if v_.get('ageH') is not None else None,
                      'move5m': r1_(n_.get('d5')), 'buyers': r1_(n_.get('buy'), 0), 'pool': r1_(n_.get('liq') or v_.get('liq'), 0), 'top10': r1_(v_.get('top10'), 0),
                      'germ': ((x_.get('chart') or {}).get('germ')), 'read': str(d_.get('why') or '')[:80]})
    return {'openTrades': pos_ or 'none', 'nextCoins': cand_ or 'none'}


async def _feecat_duo(now, env, cfg):
    rs = _rs()
    if rs._air.asked_only(env):   # 🖥 owner 2026-11-05: this timer asked OSSY and G4 about FeeCat's trades all day. They answer only when he asks
        return
    """🐱🤝 ONE duo read per FEECAT_DUO_SEC: the lead model (Gemma) answers, the second (Qwen) reads the same packet + that answer and gives
    its own list. FeeCat acts ONLY on what BOTH named (`GET /cats-ai`): an `avoid` coin is not bought (she may only ever trade LESS by it),
    an `exit` trade in profit is banked. A split is shown, never acted on."""
    if now - rs._feecat_ai['at'] < rs.FEECAT_DUO_SEC:
        return
    rs._feecat_ai['at'] = now
    pk_ = rs._feecat_packet()
    if pk_['openTrades'] == 'none' and pk_['nextCoins'] == 'none':
        return
    pairs_ = {x_.get('pairAddress') for k_ in ('openTrades', 'nextCoins') if isinstance(pk_[k_], list) for x_ in pk_[k_]}
    def _lists(txt):
        j_ = rs._aic._first_json(txt or '') or {}
        return ({p_ for p_ in (j_.get('avoid') or []) if p_ in pairs_}, {p_ for p_ in (j_.get('exit') or []) if p_ in pairs_}, str(j_.get('why') or '')[:400]) if isinstance(j_, dict) else (set(), set(), '')
    try:
        r1 = await rs._air.ROUTER.ask(rs._ai_http(), env, cfg, 'Read the packet.', context=pk_, role='exit', urgency='force', only=(rs._duet.LEAD,), system=rs.FEECAT_DUO_ASK, only_system=True)
        a1, e1, w1 = _lists(r1.get('text'))
        r2 = await rs._air.ROUTER.ask(rs._ai_http(), env, cfg, f"The lead model answered: {str(r1.get('text') or 'nothing')[:600]}. Read the packet yourself and give YOUR list.",
                                   context=pk_, role='exit', urgency='force', only=(rs._duet.SECOND,), system=rs.FEECAT_DUO_ASK, only_system=True)
        a2, e2, w2 = _lists(r2.get('text'))
    except Exception as e_:
        print('feecat duo:', str(e_)[:100]); return
    if not r1.get('text') and not r2.get('text'):
        return
    rs._feecat_ai.update(avoid=sorted(a1 & a2), exit=sorted(e1 & e2), split=sorted((a1 ^ a2) | (e1 ^ e2)), why=(w1 or w2)[:400],
                      models=[x_ for x_ in (r1.get('label') if r1.get('text') else None, r2.get('label') if r2.get('text') else None) if x_], read=now)


def _dv_note(row, px, now):
    """Register a duo comment so it can be voted on and settled; the partner's advice auto-votes the holder's newest call."""
    rs = _rs()
    st_ = rs._dv.add(rs._dv_mem.get() or {}, rs._dv_key(row), row.get('by') or 'owner', row.get('action'), row.get('mint'), px, now, view=row.get('view'), text=row.get('why'))
    rs._dv_mem.put(st_, now)


async def _dv_settle(now):
    rs = _rs()
    st_ = rs._dv_mem.get() or {}
    open_ = sorted({it['mint'] for it in (st_.get('items') or {}).values() if len(it.get('res') or {}) < len(rs._dv.CHECKS) and it.get('mint')})[:60]
    if not open_:
        return
    pm_ = await rs._live_px(open_)
    rs._dv_mem.put(rs._dv.settle(st_, lambda m_: rs._fuse._f(pm_.get(m_)) or rs._fuse._f((rs._jup_px_cache.get(m_) or (0, 0))[1]), now), now)


def _g4_fate(w, why, now):
    """🧾 What happened to the newest model BUY (seated / refused / stale …) — shown on the duel board so a buy never vanishes silently."""
    rs = _rs()
    rs._g4['fate'] = {'symbol': (w or {}).get('symbol'), 'mint': (w or {}).get('mint'), 'why': str(why)[:120], 'at': now}
    if (w or {}).get('symbol') and not str(why).startswith(('sent to the seat check', 'Warden advised')):   # 🧾 the reason lands in the duo chat for good (it was overwritten by the next buy: $dev/null + $Eternia left no trace)
        try:
            ok_ = str(why).startswith(('seated', 'adopted'))
            m0_ = rs._g4_mem.get() or {}
            log_ = list(m0_.get('log') or [])
            if not any(r_.get('fateOf') == w.get('mint') and abs(rs._fuse._f(r_.get('at')) - now) < 90 and r_.get('why', '').endswith(str(why)[:60]) for r_ in log_[-6:]):
                rs._g4_mem.put({**m0_, 'log': rs._seat.note(log_, {'at': round(now), 'mode': 'real', 'model': 'SEAT', 'by': None, 'talk': True, 'action': 'TALK', 'fateOf': w.get('mint'),
                                                             'view': 'BOUGHT' if ok_ else 'NOT BOUGHT', 'mint': w.get('mint'), 'symbol': w.get('symbol'),
                                                             'why': f"🧾 ${w.get('symbol')} " + ('— ' if ok_ else 'not bought — ') + str(why)[:160]})}, now)
        except Exception as e:
            print('g4 fate note:', str(e)[:80])
    if why.startswith(('stale', 'seat off', 'paper', 'manual', 'coin left', 'coin blocked')):
        rs._g4['want'] = None


def _g4_state():
    rs = _rs()
    st_ = rs._g4_mem.get() or {}
    return {'log': list(st_.get('log') or []), 'book': st_.get('book') or {}, 'at': st_.get('at') or 0.0, 'opener': st_.get('opener'), 'talkAt': st_.get('talkAt') or 0.0, 'statsFrom': st_.get('statsFrom'), 'idleAt': st_.get('idleAt') or 0.0}


def _g4_qwen(mint):
    """Qwen's (the local model's) last word on a coin, from the notes the desk already holds — no call."""
    rs = _rs()
    for n_ in (rs._ai['notes'].get(mint) or {}).values():
        a_ = (n_ or {}).get('advice') or {}
        if (n_ or {}).get('source') == 'local' and a_.get('stance'):
            return f"{a_.get('stance')} · {str(a_.get('summary') or '')[:90]}"
    return None


def _g4_real_record(by=None):
    """The models' REAL closed trades (archive positions an AI seat held) → the same record shape as paper; `by` = only that model's own
    (2026-10-23: G4 read the DUO's 23% as "my win rate" and bragged past OSSY's 26%)."""
    rs = _rs()
    rows_ = [{'pct': p_.get('realPct')} for p_ in (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or [] if p_.get('g4') and p_.get('realPct') is not None and (by is None or p_.get('aiBy') == by)]
    return rs._seat.record(rows_)


def _g4_lessons():
    """🎓 Real trades the two models learn from (60s cache): each model's own (by who opened it), the owner's picks, the agents' seats."""
    rs = _rs()
    if rs._g4_les['v'] is not None and rs.time.time() - rs._g4_les['at'] < 60:
        return rs._g4_les['v']
    pos_ = [p_ for p_ in (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or [] if p_.get('realPct') is not None][-300:]
    row_ = lambda p_: {'aiBy': p_.get('aiBy'), 'sym': p_.get('sym') or p_.get('symbol'), 'realPct': p_.get('realPct'), 'rule': str((p_.get('exit') or {}).get('rule') or '').split(' ')[0] or None}
    line_ = lambda xs: (lambda r: f"{r['n']} real trades, {r['won']}% won, typical {r['med']}%, best {r['best']}%" if r.get('n') else None)(rs._seat.record([{'pct': x.get('realPct')} for x in xs]))
    last_ = lambda xs: ', '.join(f"${x.get('sym') or x.get('symbol') or '?'} {rs._fuse._f(x['realPct']):+.1f}%" for x in xs[-3:][::-1])
    own_ = [p_ for p_ in pos_ if p_.get('pick')]; ag_ = [p_ for p_ in pos_ if not p_.get('pick') and not p_.get('g4')]
    v_ = rs._seat.lessons([row_(p_) for p_ in pos_ if p_.get('g4')], (line_(own_) or '') + (f' · last: {last_(own_)}' if own_ else '') or None, (line_(ag_[-60:]) or '') + (f' · last: {last_(ag_)}' if ag_ else '') or None)
    rs._g4_les.update(at=rs.time.time(), v=v_)
    return v_


def _duo_push():
    """🔁 OSSY × G4 live: every model answer / chime-in / vote reaches the open Agents tab at once (it waited for the 20s page refresh)."""
    rs = _rs()
    try:
        rs._tke.HUB.publish('duo_update', 'duo', rs._duo_view(), rs.time.time())
    except Exception as e:
        print('duo push:', str(e)[:80])


async def _g4_review(now, env, cfg, st_, lv_, mode_):
    """🏁 FINAL REVIEW (owner, 2026-10-17): the model that ran the trade grades it (A–F · right · different · one lesson) once it closes; the
    lesson goes to the AI memory every model case recalls. One call; an unreadable answer is skipped. The turn passes after."""
    rs = _rs()
    try:
        rs._g4_mem.put({**(rs._g4_mem.get() or {}), 'live': None}, now)
        pos_ = next((p_ for p_ in reversed((rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or []) if isinstance(p_, dict) and p_.get('mint') == lv_.get('mint')
                     and rs._fuse._f(p_.get('closedAt')) >= rs._fuse._f(lv_.get('at'))), None)
        res_ = (pos_ or {}).get('realPct') if (pos_ or {}).get('realPct') is not None else lv_.get('pct')
        calls_ = [{k_: r_.get(k_) for k_ in ('action', 'view', 'why', 'pct')} for r_ in st_['log'] if r_.get('mint') == lv_.get('mint') and r_.get('by') == lv_.get('by')
                  and rs._fuse._f(r_.get('at')) >= rs._fuse._f(lv_.get('at')) - 120][-6:]
        trade_ = {'coin': lv_.get('sym'), 'result': res_, 'resultSource': 'confirmed sale' if pos_ and pos_.get('realPct') is not None else 'last price seen', 'peak': lv_.get('peak'),
                  'heldMin': lv_.get('heldMin'), 'exitRule': (pos_ or {}).get('rule'), 'calls': calls_}
        who_ = lv_.get('by') if lv_.get('by') in (rs._duet.LEAD, rs._duet.SECOND) else rs._duet.LEAD
        r_ = await rs._air.ROUTER.ask(rs._ai_http(), env, cfg, 'Review your closed trade.', context={'TRADE': trade_}, role='exit', urgency='force', only=(who_,), system=rs._seat.sys_for(rs._seat.REVIEW, who_), only_system=True)
        rv_ = rs._seat.review_parse(r_.get('text'))
        if not rv_:
            return
        nm_ = rs._air.model_name(env, who_)
        m1 = rs._g4_mem.get() or {}
        rs._g4_mem.put({**m1, 'log': rs._seat.note(rs._seat.merge_log(st_['log'], m1.get('log')), {'at': round(now), 'mode': mode_, 'model': nm_, 'by': who_, 'talk': True, 'action': 'REVIEW', 'view': rv_['grade'],
                                                                                         'why': f"🏁 FINAL on ${lv_.get('sym')} ({rs._fuse._f(res_):+.1f}%, peak {rs._fuse._f(lv_.get('peak')):+.1f}%): {rv_['why']} · lesson: {rv_['lesson']}"[:rs._seat.WHY_MAX + 300],
                                                                                         'mint': lv_.get('mint'), 'symbol': lv_.get('sym'), 'pct': res_})}, now)
        if rv_['lesson']:
            rs._aim_mem.put(rs._aim.file(rs._aim_mem.get() or {}, 'lessons', f"review{int(now)}", f"🏁 {nm_} on ${lv_.get('sym')} ({rs._fuse._f(res_):+.1f}%, grade {rv_['grade']}): {rv_['lesson']}", now), now)
    except Exception as e:
        print('g4 review:', str(e)[:100])
    finally:
        rs._duo_push()


async def _feecat_duo_safe(now, env, cfg):
    rs = _rs()
    try:
        await rs.asyncio.wait_for(rs._feecat_duo(now, env, cfg), timeout=200)
    except Exception as e:
        print('feecat duo:', str(e)[:80])


async def _g4_tick(now, env, cfg):
    """🧠 G4's minute: one snapshot packet → one action for ITS seat (paper book here; real = `_g4['want']`, applied by the tier tick)."""
    rs = _rs()
    if (rs._g4['busy'] and now - rs._fuse._f(rs._g4.get('at')) < rs.G4_STUCK_SEC) or not rs._seat.due(rs._g4['at'], now):   # a tick stuck > 4 min is let go
        return
    pr_ = (rs._json_load(rs.FUSE_HQ_PATH, {}) or {}).get('prime') or {}
    mode_ = rs._oe.clean_policy(rs._prime_real_cfg(pr_))['agentAiSeat']
    if mode_ == 'off':
        return
    if rs._prime.clean_cfg(pr_.get('realCfg') or {}).get('deskBuysOff') and not any(l.get('aiSeat') and not l.get('placeholder') for c_ in (pr_.get('cards') or {}).values() if (c_ or {}).get('real') for l in c_.get('legs') or []):
        return   # 🧠 desk buys are off and the seat holds nothing: no model call. A held seat is still watched until it sells
    rs._g4['busy'], rs._g4['at'] = True, now
    rs._duo_push()   # 🧠 "is thinking" shows live
    try:
        card_ = next((c_ for c_ in (pr_.get('cards') or {}).values() if (c_ or {}).get('real')), None) or {}
        st_ = rs._g4_state()
        book_ = st_['book']
        leg_ = rs._seat.review_leg(card_.get('legs'), now) if mode_ == 'real' else None
        held_m = (leg_ or {}).get('mint') or ((book_.get('open') or {}).get('mint') if mode_ == 'paper' else None)
        on_ = {l.get('mint') for l in card_.get('legs') or []}
        cands_ = [c_ for c_ in (rs._tk.KERNEL.candidate(m_, d_) for m_, d_ in rs._tk.KERNEL.ready(exclude=on_))][:rs._seat.CAND_N * 3]
        cands_ += [c_ for c_ in (rs._tk.KERNEL.candidate(x_['mint']) for x_ in rs._tk.KERNEL.cases(exclude=on_) if x_['status'] == 'CONTENDING') if c_][:rs._seat.CAND_N * 3 - len(cands_)]   # a wider pool: the gun-line / rotation filters below cut it, then the best CAND_N are shown
        op_ = {k_ for k_, v_ in ((rs._g4_mem.get() or {}).get('opened') or {}).items() if now - rs._fuse._f(v_) < 3600}
        op_ |= {r_.get('mint') for r_ in st_['log'][-120:] if r_.get('action') == 'BUY' and r_.get('mint') and now - rs._fuse._f(r_.get('at')) < 1800}   # 🚫 no coin either model already called a BUY on in the last 30 min   # 🚫 a coin either model bought in the last hour is off their list
        op_ |= rs._seat.recent_ai_buys(card_.get('events'), now)   # 🔁 coin rotation from the card's OWN record: any coin a model seated in the last 6h is off both lists
        cands_ = [c_ for c_ in cands_ if c_ and not rs._g4_bad_entry(c_)]   # 🔫 never offered a coin at its gun line / mid-spike / chart SKIP — the models only see clean entries
        cands_ = [c_ for c_ in cands_ if c_ and c_.get('mint') and not rs._fw.dollar_named(c_.get('symbol')) and c_['mint'] not in rs._g4_blocked(card_, now) and c_['mint'] not in op_]
        ai_syms_ = rs._seat.recent_ai_syms(card_.get('events'), now)
        cands_ = [c_ for c_ in cands_ if not any(rs._trl.family(c_.get('symbol') or '', y_) for y_ in ai_syms_)]   # 🧬 no look-alike of a coin either model traded in 6h
        if rs._g4_picks_only():   # 🧪 N04 (owner 2026-10-29 "picks only"): the models are offered ONLY the desk's proven-rule picks (136 real trades: no edge of their own)
            cands_ = [c_ for c_ in cands_ if c_.get('pick')]
        cands_ = sorted(cands_, key=lambda c_: rs._seat.germ_rank(rs._opp.germ_d(c_.get('chart') or {})[0], rs._uni.germ_max()))[:rs._seat.CAND_N]   # 🦠 germ-floor coins first (stable: kernel rank inside each tier)
        if not cands_ and not held_m:
            # Nothing actionable: do not wake a local model to say WAIT again.
            # Rotate the idle hunt clock too, so a later pick is offered to
            # both models in turn even if no model could answer while empty.
            if mode_ == 'real':
                hm_ = rs._g4_mem.get() or {}
                hunter_ = hm_.get('huntBy') if hm_.get('huntBy') in (rs._duet.LEAD, rs._duet.SECOND) else rs._seat.turn(st_['log'], rs._duet.LEAD, rs._duet.SECOND, opener=st_.get('opener'))[0]
                since_ = rs._fuse._f(hm_.get('huntSince')) or now
                if now - since_ >= rs._seat.HUNT_TURN_SEC:
                    partner_ = rs._duet.SECOND if hunter_ == rs._duet.LEAD else rs._duet.LEAD
                    rs._g4_mem.put({**hm_, 'opener': hunter_, 'huntBy': partner_, 'huntSince': now,
                                 'log': rs._seat.note(st_['log'], {'at': round(now), 'mode': mode_, 'model': 'SEAT', 'action': 'PASS',
                                                               'why': f'No eligible coin on the card — {rs._air.model_name(env, partner_)} gets the next pick'})}, now)
                elif not hm_.get('huntBy'):
                    rs._g4_mem.put({**hm_, 'huntBy': hunter_, 'huntSince': now}, now)
            # The next clock tick still checks the kernel for fresh picks.
            rs._g4['phase'] = 'NO ELIGIBLE COINS'
            return
        pxm_ = await rs._live_px([c_['mint'] for c_ in cands_] + ([held_m] if held_m else []))
        px_of = lambda m_: rs._fuse._f(pxm_.get(m_)) or rs._fuse._f((rs._jup_px_cache.get(m_) or (0, 0))[1])
        pos_ = ((rs._office_state().get('pos') or {}).get(held_m) or {}) if held_m else {}
        if mode_ == 'real' and leg_:
            held_ = rs._seat.held_row({**leg_, 'peakPct': pos_.get('peak')}, px_of(held_m), now, pos_.get('pressure'), rs._g4_qwen(held_m))
        elif mode_ == 'paper' and book_.get('open'):
            o_ = book_['open']
            held_ = rs._seat.held_row({'symbol': o_.get('symbol'), 'mint': o_['mint'], 'entry': o_['entry'], 'at': o_['at'], 'peakPct': o_.get('peak')}, px_of(o_['mint']), now, None, rs._g4_qwen(o_['mint']))
        else:
            held_ = None
        lv_ = (rs._g4_mem.get() or {}).get('live')
        if mode_ == 'real' and held_ and leg_:   # 📸 the live trade: remembered (for its final review) + a snapshot line every 5 min
            if not lv_ or lv_.get('mint') != held_m:
                lv_ = {'mint': held_m, 'sym': held_.get('symbol'), 'by': leg_.get('aiBy'), 'at': rs._fuse._f(leg_.get('at')) or now, 'snapAt': now}
            lv_ = {**lv_, 'pct': held_.get('pct'), 'peak': held_.get('peak'), 'heldMin': held_.get('heldMin')}
            if now - rs._fuse._f(lv_.get('snapAt')) >= rs._seat.SNAP_EVERY:
                rp0_ = next((r_ for r_ in rs._office.get('reports') or [] if r_.get('mint') == held_m), {})
                sn_ = rs._seat.snapshot_line(held_, (rs._tk.KERNEL.candidate(held_m) or {}).get('chart'), ' · '.join(x_ for x_ in (rp0_.get('state'), str(rp0_.get('rule') or '').split(' ')[0]) if x_) or None,
                                          ((rs._office.get('flow') or {}).get(held_m) or {}).get('state'))
                m0_ = rs._g4_mem.get() or {}
                rs._g4_mem.put({**m0_, 'log': rs._seat.note(rs._seat.merge_log(st_['log'], m0_.get('log')), {'at': round(now), 'mode': mode_, 'model': 'SNAPSHOT', 'by': None, 'talk': True, 'action': 'TALK',
                                                                                                  'view': 'SNAP', 'why': sn_, 'mint': held_m, 'symbol': held_.get('symbol'), 'pct': held_.get('pct')})}, now)
                st_ = rs._g4_state()
                lv_['snapAt'] = now
            rs._g4_mem.put({**(rs._g4_mem.get() or {}), 'live': lv_}, now)
        elif mode_ == 'real' and not held_ and lv_:   # 🏁 the trade closed: its holder reviews it BEFORE the turn moves on (this minute is the review)
            rs._g4['phase'] = 'SOLD'   # 🏁 never a stale HOLDING with no coin ("G4 is running $?" while the seat read EMPTY — owner: "my trade disappeared")
            await rs._g4_review(now, env, cfg, st_, lv_, mode_)
            return
        if mode_ == 'real' and not held_:   # 🪑 no open seat on the card → the models WAIT for one (no call, one line per 5 min)
            legs_r = [l for l in card_.get('legs') or [] if not l.get('placeholder') and rs._fuse._f(l.get('units')) > 0 and l.get('mint') != rs._fw.SOL_MINT]
            if len(legs_r) >= int(rs._fuse._f(rs._prime_real_cfg(pr_).get('coins')) or 4) and not any(l.get('placeholder') for l in card_.get('legs') or []):
                lw_ = next((r_ for r_ in reversed(st_['log']) if r_.get('seatWait')), None)
                if not lw_ or now - (lw_.get('at') or 0) > 300:
                    rs._g4_mem.put({**(rs._g4_mem.get() or {}), 'log': rs._seat.note(rs._seat.merge_log(st_['log'], (rs._g4_mem.get() or {}).get('log')), {'at': round(now), 'mode': mode_, 'model': 'SEAT', 'by': None, 'seatWait': True, 'action': 'WAIT',
                                                                                         'why': f'every seat is full ({len(legs_r)}) — waiting for one to open, then it is back to their turn'})}, now)
                rs._g4['phase'] = 'SEATS FULL'
                if now - rs._fuse._f(st_.get('idleAt')) >= rs._seat.IDLE_EVERY:   # 💬 seats full: one model (alternating) still reads the card's trades and says what it would do — graded by the market like every call
                    await rs._g4_idle(now, env, cfg, st_, legs_r, mode_)
                else:   # 🤝 … and between those, rides along with Reaper on one of his coins
                    await rs._reaper_partner(now, env, cfg, st_, card_, mode_, rs._seat.idle_turn(st_['log'], rs._duet.LEAD, rs._duet.SECOND))
                return
        rs._g4['phase'] = 'HOLDING' if held_ else 'HUNTING'
        rec_ = rs._g4_real_record() if mode_ == 'real' else rs._seat.record(book_.get('closed'))
        holder_ = (leg_ or {}).get('aiBy') if mode_ == 'real' else (book_.get('open') or {}).get('by')
        if mode_ == 'paper':
            st_['opener'] = holder_ or ((book_.get('closed') or [{}])[-1] or {}).get('by')
        first_, second_ = rs._seat.turn(st_['log'], rs._duet.LEAD, rs._duet.SECOND, bool(held_), opener=st_.get('opener'), holder=holder_)
        if not held_ and mode_ == 'real':   # ⏱ a hunting turn lasts HUNT_TURN_SEC: no clean entry found → the turn passes (G4 sat on WAIT 70× while OSSY never got a go)
            hm_ = rs._g4_mem.get() or {}
            if hm_.get('huntBy') != first_:
                rs._g4_mem.put({**hm_, 'huntBy': first_, 'huntSince': now}, now)
            elif now - rs._fuse._f(hm_.get('huntSince')) >= rs._seat.HUNT_TURN_SEC and rs._seat.hunt_answers(st_['log'], first_, rs._fuse._f(hm_.get('huntSince'))) >= rs._seat.HUNT_PASS_N:   # 🔁 a turn passes only when the hunter really LOOKED and found nothing — a model that could not answer keeps its turn (OSSY took every trade while G4's desktop was jammed)
                rs._g4_mem.put({**hm_, 'opener': first_, 'huntBy': second_, 'huntSince': now,
                             'log': rs._seat.note(rs._seat.merge_log(st_['log'], hm_.get('log')), {'at': round(now), 'mode': mode_, 'model': 'SEAT', 'by': None, 'action': 'PASS', 'why': f"⏱ {rs._air.model_name(env, first_)} found no clean entry in {rs._seat.HUNT_TURN_SEC / 60:.0f} min — {rs._air.model_name(env, second_)}'s turn"})}, now)
                st_['opener'] = first_
                first_, second_ = second_, first_   # 🔁 one REAL trade each: the opener runs it to the exit, then the other hunts
        guards_ = bool((rs._g4_mem.get() or {}).get('guards'))   # 🔁 owner, 2026-10-23 ("ossy and g4 not taking turns?"): STRICT TURNS by default — the streak brake + proof bench skip a turn only when the owner switches them on
        if not held_ and mode_ == 'real' and guards_:   # 🧯 STREAK BRAKE: a model on 3 straight real losses does not take a buy turn — its partner hunts
            br_ = rs._g4_brake(now)
            if br_.get(first_) and not br_.get(second_):
                bm_ = rs._g4_mem.get() or {}
                if bm_.get('brakeNote') != f'{first_}:{br_[first_]["since"]}':
                    rs._g4_mem.put({**bm_, 'brakeNote': f'{first_}:{br_[first_]["since"]}', 'log': rs._seat.note(rs._seat.merge_log(st_['log'], bm_.get('log')), {'at': round(now), 'mode': mode_, 'model': 'SEAT', 'by': None, 'action': 'PASS',
                                 'why': f"🧯 {rs._air.model_name(env, first_)} is on a losing streak ({br_[first_]['why']}) — {rs._air.model_name(env, second_)} picks until {rs._air.model_name(env, first_)}'s calls prove right again"})}, now)
                first_, second_ = second_, first_
        if not held_ and mode_ == 'real' and guards_:   # 🪑 PROOF BENCH: a model whose own last 150 FAVOR calls lose does not open the next real seat (ai_seat.bench)
            done_ = (rs._ai.get('book') or {}).get('done') or []
            b1_, b2_ = rs._seat.bench(done_, first_), rs._seat.bench(done_, second_)
            if b1_['benched'] and not b2_['benched']:
                bm_ = rs._g4_mem.get() or {}
                if bm_.get('benchNote') != f"{first_}:{b1_['n']}:{b1_['upPct']}":
                    rs._g4_mem.put({**bm_, 'benchNote': f"{first_}:{b1_['n']}:{b1_['upPct']}", 'log': rs._seat.note(rs._seat.merge_log(st_['log'], bm_.get('log')), {'at': round(now), 'mode': mode_, 'model': 'SEAT', 'by': None, 'action': 'PASS',
                                 'why': f"🪑 {rs._air.model_name(env, first_)} is benched: its last {b1_['n']} FAVOR calls settled {b1_['median']:+.1f}% median, {b1_['upPct']}% up — {rs._air.model_name(env, second_)} opens until that turns"})}, now)
                first_, second_ = second_, first_
        if mode_ == 'paper':
            rec_ = rs._seat.by_model(book_.get('closed')).get(first_) or {'n': 0}
        else:
            rec_ = rs._g4_real_record(first_)   # 💵 its OWN record, never the duo's
        rows_ = [rs._seat.cand_row(c_, rs._g4_qwen(c_['mint'])) for c_ in cands_]
        for r_c in rows_:   # 🐋 who has been trading each candidate (the chart's own wallet tags, cache only): read it, don't fear it
            cw_c = (rs._cw_cache.get(r_c.get('mint')) or (0, None))[1]
            if cw_c and cw_c.get('counts'):
                r_c['wallets'] = ' · '.join(f"{k_} {v_}" for k_, v_ in sorted(cw_c['counts'].items(), key=lambda kv: -kv[1])[:4])
        pick_ = rs._seat.agents_pick(rows_)
        says_ = rs._seat.talk_of(st_['log'], first_, since=rs._fuse._f((leg_ or {}).get('at')) or 0.0) if held_ else None
        learn_ = rs._seat.learn_block(rs._g4_lessons(), first_, second_, lambda k_: rs._air.model_name(env, k_))
        learn_['confidence'] = rs._dv.words(rs._dv_mem.get() or {}, first_)
        sv_ = rs._study.get('v') or {}   # 👤 the owner study: how HE trades (graded moves, where the agents sold him early) — the best tools from his day
        if sv_.get('findings'):
            learn_['ownerStudy'] = [str(x)[:160] for x in sv_['findings'][:4]]
        if rs._study.get('holdWins'):
            learn_['ownerHoldWins'] = rs._study['holdWins']   # ✋ the owner's holds that ran — hold like that
        if (rs._study.get('hints') or {}).get('line'):
            learn_['ownerHints'] = rs._study['hints']['line']   # ✋ how often the owner's one-click holds were right — weigh his calls by it
        hl_ = (rs._study.get('holds') or {}).get('lines') or []
        if hl_:
            learn_['holdLessons'] = [str(x)[:140] for x in hl_[:3]]   # 👍👎 what the market's verdicts on its calls + votes earned it
        on_ = next((r_ for r_ in reversed(st_['log']) if r_.get('by') == 'owner' and ((held_ and r_.get('mint') == held_.get('mint')) or (not held_ and not r_.get('mint') and now - rs._fuse._f(r_.get('at')) < 600))), None)   # 👤 with no trade open your chime-in reaches the model hunting next (10 min)
        if on_ and not rs._seat.owner_line_live(on_, held_, st_['log'], now):
            on_ = None   # 👤 an old line (another trade of this coin, 20+ min old, or already answered twice) is never fed back as "the Godfather said…"
        if on_:
            learn_['ownerSays'] = str(on_.get('why') or '')[:600]   # 👤 the owner chimed in on this trade
        await rs._dv_settle(now)
        try:   # 💵 each model's OWN money (owner, 2026-10-23: "they need to be aware of their individual live PnL"): its all-time real $, its partner's, this trade live in $
            tot_ = rs._duo_totals()
            nm1_, nm2_ = rs._air.model_name(env, first_), rs._air.model_name(env, second_)
            live_ = rs._duo_holding(leg_) if (held_ and leg_) else None
            pnl_ = rs._seat.pnl_words(nm1_, tot_.get(nm1_), nm2_, tot_.get(nm2_), live_)
            pnl2_ = rs._seat.pnl_words(nm2_, tot_.get(nm2_), nm1_, tot_.get(nm1_))
        except Exception as e:
            print('seat pnl:', str(e)[:80]); pnl_ = pnl2_ = None
        order_ = rs._seat.owner_order(learn_.get('ownerSays')) if held_ else None   # 🫡 the Godfather's SELL / TRIM on this trade is final
        pk_ = rs._seat.packet(rows_, held_, rs._seat.record_words(rec_), rs._seat.partner_of(st_['log'], first_), (pick_ or {}).get('symbol'), says_, learn_, pnl=pnl_, proven=rs._seat.research(rs._edge_rules()))
        if held_ and leg_:   # 🐋 what the snipers / bundles / dev / top holders / whales / top traders did since YOUR buy — see it, then move
            tr_h = rs._flow_trades.get(leg_.get('pairAddress'))
            if tr_h and now - tr_h[0] < 60:
                pk_['WALLETS'] = rs._cw.moves_since(rs._cw.tag_trades(tr_h[1], (rs._intel_cache.get(held_m) or (0, None))[1] or {}), rs._fuse._f(leg_.get('at')))['words'] + " — not a reason to panic: watch what they do next, then set your lines"
        rs._g4['reads'] = (rs._g4.get('reads') or 0) + 1
        held_ch = ((rs._tk.KERNEL.candidate(held_m) or {}).get('chart') or {}) if held_m else {}
        if held_:   # 📸 EVERY read: the held coin's 1-minute AND 5-minute chart + its germ / higher-low read (owner: "observe 1 and 5 min")
            try:
                pk_['chartView'] = rs._seat.chart_view(held_ch)
                pr_h = next((r_.get('pair') for r_ in (rs._agents.get('table') or []) if r_.get('mint') == held_m), None) or (leg_ or {}).get('pairAddress')
                b1_ = (rs._office_bars(pr_h, held_m, rs._snp.PTS * 5) if pr_h else None) or {}
                ent_h = rs._fuse._f((leg_ or {}).get('entryPx') or (leg_ or {}).get('entry')) or None
                rw_ = b1_.get('rows') or []
                s1_ = rs._snp.snapshot(b1_, entry=ent_h) if rw_ else None
                s5_ = rs._snp.snapshot({'src': b1_.get('src'), 'rows': rs._ci.bars5(rw_)}, entry=ent_h) if b1_.get('src') == 'candles' and len(rw_) >= 15 else None
                if s1_:
                    pk_['CHART1M'] = s1_.get('line') or s1_.get('text')
                if s5_:
                    pk_['CHART5M'] = str(s5_.get('line') or s5_.get('text') or '').replace('1m candles', '5m candles', 1)
            except Exception as e:
                print('g4 snap:', str(e)[:80])
        rs._g4['live'] = {'by': rs._air.model_name(env, first_), 'at': now, 'pick': (pick_ or {}).get('symbol'), 'held': held_,
                       'cands': [{k_: r_c.get(k_) for k_ in ('symbol', 'status', 'trigger', 'move5m', 'buyers', 'germ', 'pool', 'cap', 'ageMin', 'rank')} for r_c in rows_[:6]]}   # 👁 what the deciding model is reading, live
        t0_ = rs.time.perf_counter()
        r_ = await rs._air.ROUTER.ask(rs._ai_http(), env, cfg, 'Your minute snapshot. Decide.', context=pk_, role='exit', urgency='seat', only=(first_,), system=rs._seat.sys_for(rs._seat.SYSTEM, first_), only_system=True)   # 🔁 a held trade is ONLY its holder's call (the partner standing in made OSSY post HOLDs on G4's $MOMO); hunting, the partner may answer for a missed minute   # 🔁 the holder runs its trade; when it misses a minute (call cap / timeout) the partner stands in — the trade stays the holder's (leg aiBy)
        by_m = r_.get('source') if r_.get('source') in (first_, second_) else first_
        dec_ = rs._seat.parse(r_.get('text'), [c_['mint'] for c_ in cands_], bool(held_), {c_.get('symbol'): c_['mint'] for c_ in cands_ if c_.get('symbol')}, spoke=bool(learn_.get('ownerSays')))
        if dec_ and dec_.get('preds') and r_.get('source') in (first_, second_):   # 🔮 every prediction is graded 15 min later on the real price (ai_learn, per model)
            try:
                for m_p, v_p in dec_['preds'].items():
                    m_p = (held_m or (dec_.get('mint') or None)) if m_p == '_self' else m_p
                    sy_p = next((c_.get('symbol') for c_ in cands_ if c_['mint'] == m_p), None) or ((held_ or {}).get('symbol') if m_p == held_m else None)
                    px_p = rs._fuse._f((rs._jup_px_cache.get(m_p) or (0, 0))[1]) if m_p else 0.0
                    if m_p and px_p > 0:
                        rs._ai['book'] = rs._ail.note(rs._ai_book(), 'seat', m_p, 'FAVOR' if v_p > 0 else 'CAUTION', px_p, now, sy_p, src=r_.get('source'), predict=v_p)
                rs._json_save(rs.AI_PROOF_PATH, rs._ai['book'])
            except Exception as e_p:
                print('seat preds:', str(e_p)[:80])
        dec_ = rs._seat.cook(dec_, {**(held_ or {}), 'sl': (leg_ or {}).get('aiSl')}) if held_ else dec_
        if held_ and dec_:   # 🦠 a base (germ floor / higher lows) on slow volume is held — unless sellers lead the 90s tape
            dec_ = rs._seat.structure_hold(dec_, {**held_, 'sl': (leg_ or {}).get('aiSl')}, held_ch, sellers=str(((rs._office.get('flow') or {}).get(held_m) or {}).get('state') or '').upper() == 'SELLERS')
            dec_ = rs._seat.line_hold(dec_, {**held_, 'sl': (leg_ or {}).get('aiSl'), 'tp': (leg_ or {}).get('aiTp')}, held_ch, sellers=str(((rs._office.get('flow') or {}).get(held_m) or {}).get('state') or '').upper() == 'SELLERS')   # 🎯 between its SL and TP a SELL needs a chart reason
            dec_ = rs._seat.obey(dec_, order_, True)   # 🫡 after every hold-guard: the owner's order is never cooked / line-held back into a HOLD
        ms_ = round((rs.time.perf_counter() - t0_) * 1000)
        miss_ = None
        if not dec_:   # 🤝 no model answered (busy / timed out / unreadable): the agents decide the seat this minute instead of a dead minute
            miss_ = str(r_.get('why') or '; '.join(f'{a_} {b_}' for a_, b_ in (r_.get('tried') or [])) or ('unreadable: ' + str(r_.get('text') or '')[:60]) or 'no answer')[:120]
            dec_, by_m = rs._seat.backup(rows_, bool(held_)), 'agents'
        by_ = {c_['mint']: c_ for c_ in cands_}
        ev_, want_ = None, None
        if dec_ and mode_ == 'paper':
            book_, ev_ = rs._seat.paper_step(book_, dec_, by_, px_of, now, by_m)
        if dec_ and mode_ == 'real' and held_ and leg_ and (dec_.get('tp') or dec_.get('sl') or dec_.get('trail')) and by_m != 'agents':   # 🎯 the holder sets its own lines on its own trade
            rs._g4['set'] = {'pair': leg_.get('pairAddress'), 'tp': dec_.get('tp'), 'sl': dec_.get('sl'), 'trail': dec_.get('trail'), 'at': rs.time.time(), 'by': rs._air.model_name(env, by_m)}
        if dec_ and mode_ == 'real' and dec_['action'] in ('BUY', 'SELL', 'TRIM'):   # (a TRIM that also moved its lines used to set the lines and drop the trim)
            want_ = {**dec_, 'by': by_m, 'model': 'AGENTS' if by_m == 'agents' else rs._air.model_name(env, by_m), 'thinkAt': now, 'symbol': (by_.get(dec_['mint']) or {}).get('symbol') if dec_['action'] == 'BUY' else (leg_ or {}).get('symbol'), 'at': rs.time.time(), 'pair': (by_.get(dec_['mint']) or {}).get('pair') if dec_['action'] == 'BUY' else (leg_ or {}).get('pairAddress')}   # ⏱ fresh from the ANSWER (a 30–90s think read as stale)
        propose_ = f"{dec_['action']}{(' ' + str(dec_.get('pct') or '') + '%') if dec_['action'] == 'TRIM' else ''} ${(held_ or {}).get('symbol')} — {str(dec_.get('why') or '')[:120]}" if (mode_ == 'real' and held_ and want_ and want_['action'] in ('SELL', 'TRIM') and by_m != 'agents' and not dec_.get('obeyed')) else None   # 🤝 a real move waits for the partner's word (never the Godfather's order) (line moves never wait)
        focus_ = by_.get((dec_ or {}).get('mint')) if (dec_ or {}).get('action') == 'BUY' else None
        row_ = {'at': round(now), 'mode': mode_, 'model': 'AGENTS' if by_m == 'agents' else rs._air.model_name(env, by_m), 'by': by_m if dec_ else None, 'ms': ms_, 'miss': miss_,
                'action': (dec_ or {}).get('action') or 'NO ANSWER', 'why': (dec_ or {}).get('why') or str(r_.get('why') or 'the model did not answer')[:160],
                'conf': (dec_ or {}).get('conf'), 'watch': (dec_ or {}).get('watch'), 'symbol': (focus_ or {}).get('symbol') or (held_ or {}).get('symbol'),
                'mint': (focus_ or {}).get('mint') or (held_ or {}).get('mint'), 'pct': (held_ or {}).get('pct'), 'heldMin': (held_ or {}).get('heldMin'),
                'vitals': rs._seat.cand_row(focus_) if focus_ else ({k_: v_ for k_, v_ in rs._seat.cand_row(rs._tk.KERNEL.candidate(held_m) or {'mint': held_m}).items() if k_ not in ('mint',)} if held_m else None),
                'pressure': (held_ or {}).get('pressure'), 'qwen': rs._g4_qwen((focus_ or {}).get('mint') or held_m) if ((focus_ or {}).get('mint') or held_m) else None,
                'considered': len(cands_), 'event': ev_}
        log_ = rs._seat.note(st_['log'], row_)
        rp_ = next((r_ for r_ in (rs._office.get('reports') or []) if r_.get('mint') == held_m), None) if held_ else None
        rk_ = f"{(rp_ or {}).get('rule')}|{(rp_ or {}).get('state')}" if rp_ else None
        if rp_ and rk_ != (rs._g4_mem.get() or {}).get('reapKey'):   # ☠ Reaper's move on this trade (trailing / protect / skim / take) → its own line in the chat
            log_ = rs._seat.note(log_, {'at': round(now), 'mode': mode_, 'model': 'REAPER', 'by': 'reaper', 'talk': True, 'action': 'TALK', 'view': rp_.get('state'),
                                     'why': f"{rp_.get('rule')} · peak {rs._fuse._f(rp_.get('peak')):+.1f}% · {str(rp_.get('evidence') or '')[:110]}", 'mint': held_m,
                                     'symbol': (held_ or {}).get('symbol'), 'pct': (held_ or {}).get('pct')})
            rs._g4_mem.put({**(rs._g4_mem.get() or {}), 'reapKey': rk_}, now)
        lv_at = rs._fuse._f((rs._g4_mem.get() or {}).get('lvAt'))
        lv_ = [e_ for e_ in (card_.get('events') or []) if e_.get('kind') == 'level' and held_ and e_.get('symbol') == (held_ or {}).get('symbol') and rs._fuse._f(e_.get('at')) > max(lv_at, rs._fuse._f((leg_ or {}).get('at')))] if held_ else []
        for e_ in lv_[-2:]:   # ✋ your own TP / SL drag on this trade → a YOU line in the chat (the models read it next minute)
            log_ = rs._seat.note(log_, {'at': round(rs._fuse._f(e_.get('at'))), 'mode': mode_, 'model': 'YOU', 'by': 'owner', 'talk': True, 'action': 'TALK', 'view': 'LINES',
                                     'why': str(e_.get('why') or '')[:160], 'mint': held_m, 'symbol': (held_ or {}).get('symbol'), 'pct': (held_ or {}).get('pct')})
        if lv_:
            rs._g4_mem.put({**(rs._g4_mem.get() or {}), 'lvAt': max(rs._fuse._f(e_.get('at')) for e_ in lv_)}, now)
        ch_l = rs._seat.lines_word(leg_, dec_) if (mode_ == 'real' and held_ and leg_ and dec_ and by_m != 'agents') else {}
        if ch_l:   # 🎯 the holder moved its own TP / SL / trail → its own line in the trade room, graded by the market like a call
            lr_ = {'at': round(now) + 1, 'mode': mode_, 'model': row_['model'], 'by': by_m, 'action': 'LINES', 'view': rs._seat.lines_view(ch_l, leg_), 'lines': ch_l, 'why': rs._seat.lines_why(ch_l, leg_),
                   'symbol': (held_ or {}).get('symbol'), 'mint': (held_ or {}).get('mint'), 'pct': (held_ or {}).get('pct')}
            log_ = rs._seat.note(log_, lr_)
            if lr_['view'] and lr_['mint']:
                rs._dv_note(lr_, px_of(lr_['mint']), now)
        if row_.get('mint') and dec_ and by_m in (first_, second_):
            rs._dv_note(row_, px_of(row_['mint']), now)
        talk_at = st_.get('talkAt') or 0.0
        if propose_ or (held_ and dec_ and by_m != 'agents' and now - talk_at >= rs._seat.TALK_EVERY):   # line moves were applied above already — they never wait for the reply   # 🔁 back and forth: the partner answers EVERY holder call   # 🤝 a SELL / TRIM of the held trade waits for the partner's word (≤ ADVISE_SEC); otherwise   # 💬 the partner reads the SAME trade and advises; the holder sees it next minute (it never decides)
            talk_at = now
            try:
                t0b = rs.time.perf_counter()
                ra_ = await rs.asyncio.wait_for(rs._air.ROUTER.ask(rs._ai_http(), env, cfg, 'Advise on your partner\'s open trade.', context={**rs._seat.advise_packet(pk_, rs._air.model_name(env, first_), rs._air.model_name(env, second_), mine=pnl2_), **({'HOLDERPROPOSES': propose_} if propose_ else {})}, role='exit', urgency='seat', only=(second_,), system=rs._seat.sys_for(rs._seat.ADVISE, second_), only_system=True), timeout=rs.ADVISE_SEC)
                da_ = rs._seat.parse(ra_.get('text'), [], True, spoke=bool(learn_.get('ownerSays')))
                oth_ = rs._seat._sym_in((da_ or {}).get('why'), {l_.get('symbol'): l_.get('mint') for l_ in rs._duo_card_legs() if l_.get('symbol')}) if da_ else None
                if da_ and oth_ and oth_ != held_m:   # 💬 the advice is about ANOTHER coin on the card ($ELON on the $Kimchi trade) → it goes to that coin's own room, never the holder's chat
                    lo_ = next((l_ for l_ in rs._duo_card_legs() if l_.get('mint') == oth_), {})
                    crow_ = {'at': round(now), 'mode': mode_, 'model': rs._air.model_name(env, second_), 'by': second_, 'talk': True, 'coinTalk': True, 'action': 'TALK', 'view': da_['action'],
                             'why': str(da_.get('why') or '')[:rs._seat.WHY_MAX], 'conf': da_.get('conf'), 'symbol': lo_.get('symbol'), 'mint': oth_}
                    log_ = rs._seat.note(log_, crow_)
                    rs._dv_note(crow_, rs._fuse._f((await rs._live_px([oth_])).get(oth_)), now)
                    da_ = None
                if da_:
                    trow_ = {'at': round(now), 'mode': mode_, 'model': rs._air.model_name(env, second_), 'by': second_, 'talk': True, 'ms': round((rs.time.perf_counter() - t0b) * 1000),
                                             'action': 'TALK', 'view': da_['action'], 'why': f"to {rs._air.model_name(env, first_)}: {da_['action']} — {da_.get('why') or ''}"[:rs._seat.WHY_MAX + 40], 'conf': da_.get('conf'),
                                             'watch': da_.get('watch'), 'symbol': (held_ or {}).get('symbol'), 'mint': (held_ or {}).get('mint'), 'pct': (held_ or {}).get('pct'),
                                             'cap': (rs._seat.cand_row(rs._tk.KERNEL.candidate(held_m) or {'mint': held_m}) or {}).get('cap')}   # 📍 its pin on the chart sits at the cap it spoke at
                    log_ = rs._seat.note(log_, trow_)
                    rs._dv_note(trow_, px_of(held_m), now)
                    hc_ = next((r_ for r_ in reversed(log_) if r_.get('by') == first_ and r_.get('mint') == held_m and not r_.get('talk')), None)
                    if hc_:   # 🤝 the partner's advice IS its vote on the holder's newest call: agrees = 👍, disagrees = 👎
                        sv_, _ok = rs._dv.vote(rs._dv_mem.get() or {}, rs._dv_key(hc_), second_, 1 if rs._dv.side_of(da_['action']) == rs._dv.side_of(hc_.get('action')) else -1)
                        rs._dv_mem.put(sv_, now)
            except Exception as e_t:
                print('g4 talk:', str(e_t)[:100])
        if want_:   # the move goes out AFTER the partner spoke (its word is in the chat; the holder still decides)
            rs._g4['want'] = {**want_, 'at': rs.time.time()}
        if not held_ and mode_ == 'real' and now - rs._fuse._f(st_.get('idleAt')) >= rs._seat.IDLE_EVERY:   # 💬 between trades the two still talk: the waiting model reads the card's coins and says what it would do
            rs._g4_mem.put({**(rs._g4_mem.get() or {}), 'log': rs._seat.merge_log(log_, (rs._g4_mem.get() or {}).get('log'))}, now)
            await rs._g4_idle(now, env, cfg, {**st_, 'log': log_}, [l for l in card_.get('legs') or [] if not l.get('placeholder') and rs._fuse._f(l.get('units')) > 0 and l.get('mint') != rs._fw.SOL_MINT], mode_, who=second_)   # the one NOT hunting talks
            log_ = (rs._g4_mem.get() or {}).get('log') or log_
        if mode_ == 'real':   # 🤝 the model not deciding rides along on one of Reaper's coins (every 60s, rotating)
            try:
                await rs._reaper_partner(now, env, cfg, {**st_, 'log': log_}, card_, mode_, second_)
                log_ = rs._seat.merge_log(log_, (rs._g4_mem.get() or {}).get('log'))
            except Exception as e_p:
                print('reaper partner:', str(e_p)[:100])
        m1_ = rs._g4_mem.get() or {}   # the seat may have opened (and the stats restarted) while this model was thinking
        if (m1_.get('statsFrom') or 0) > (st_.get('statsFrom') or 0):
            log_ = [r_ for r_ in log_ if (r_.get('at') or 0) >= m1_['statsFrom']]
        log_ = rs._seat.merge_log(log_, m1_.get('log'))   # 💬 keep your chime-in (and any line) written while the model thought
        rs._g4_mem.put({'log': log_, 'book': book_, 'at': now, 'opener': m1_.get('opener') or st_.get('opener'), 'talkAt': talk_at, 'statsFrom': m1_.get('statsFrom'), 'idleAt': m1_.get('idleAt') or st_.get('idleAt'), 'opened': m1_.get('opened') or {}, 'huntBy': m1_.get('huntBy'), 'huntSince': m1_.get('huntSince'), 'reapKey': m1_.get('reapKey'), 'lvAt': m1_.get('lvAt'), 'live': m1_.get('live')}, now)   # 🚫 keep the bought-coins list (it was dropped every minute → $1 bought 3×)
    except Exception as e_:
        print('g4 seat:', str(e_)[:140])
    finally:
        rs._g4['busy'] = False
        rs._duo_push()


async def _g4_idle(now, env, cfg, st_, legs_, mode_, who=None):
    """💬 Every seat is full: the model whose idle turn it is reads the card's trades and comments on ONE (HOLD / SELL + why). It never trades —
    the row is a TALK the market grades (5 min / 1 h / 24 h) like every call, so idle minutes still build each model's record."""
    rs = _rs()
    m0 = rs._g4_mem.get() or {}
    rs._g4_mem.put({**m0, 'idleAt': now}, now)
    who_ = who or rs._seat.idle_turn(st_['log'], rs._duet.LEAD, rs._duet.SECOND)
    try:
        pxm_ = await rs._live_px([l.get('mint') for l in legs_])
        pos_all = rs._office_state().get('pos') or {}
        rows_, syms_ = [], {}
        for l in legs_[:6]:
            m_ = l.get('mint')
            px_ = rs._fuse._f(pxm_.get(m_)) or rs._fuse._f((rs._jup_px_cache.get(m_) or (0, 0))[1])
            en_ = rs._fuse._f(l.get('entryPx') or l.get('entry'))
            c_ = rs._seat.cand_row(rs._tk.KERNEL.candidate(m_) or {'mint': m_})
            rows_.append({'symbol': l.get('symbol'), 'holder': 'owner' if l.get('picked') else ('a model' if l.get('aiSeat') else 'agents'),
                          'pct': round((px_ / en_ - 1) * 100, 1) if px_ > 0 and en_ > 0 else None, 'peak': (pos_all.get(m_) or {}).get('peak'),
                          'heldMin': round((now - rs._fuse._f(l.get('at'))) / 60) if l.get('at') else None, 'move5m': c_.get('move5m'), 'buyers': c_.get('buyers'), 'cap': c_.get('cap'),
                          'chart': rs._seat.chart_view((rs._office.get('charts') or {}).get(m_)), 'base': rs._of.base_of((rs._office.get('charts') or {}).get(m_)),   # 📈 HH/HL + germ — read before setting any line
                          'lines': {k_: l.get(lk_) for k_, lk_ in (('tp', 'aiTp'), ('sl', 'aiSl'), ('trail', 'aiTrail')) if l.get(lk_)} or None, 'reaper': next(((r_.get('state'), r_.get('rule')) for r_ in rs._office.get('reports') or [] if r_.get('mint') == m_), None)})
            if l.get('symbol'):
                syms_[l['symbol']] = m_
        if not rows_:
            return
        t0_ = rs.time.perf_counter()
        r_ = await rs._air.ROUTER.ask(rs._ai_http(), env, cfg, 'Seats are full. Comment on one trade.', context={'CARD': rows_, 'learn': {'confidence': rs._dv.words(rs._dv_mem.get() or {}, who_)}, 'ownerSays': [f"${r_.get('symbol')}: {str(r_.get('why') or '')[:140]}" for r_ in (st_.get('log') or [])[-60:] if r_.get('by') == 'owner' and r_.get('coinTalk') and now - rs._fuse._f(r_.get('at')) < 1800][-3:]},   # 👤 your lines in a coin's room
                                   role='exit', urgency='force', only=(who_,), system=rs._seat.sys_for(rs._seat.IDLE, who_), only_system=True)
        d_ = rs._seat.idle_parse(r_.get('text'), syms_, spoke=any(r_o.get('by') == 'owner' and r_o.get('coinTalk') and now - rs._fuse._f(r_o.get('at')) < 1800 for r_o in (st_.get('log') or [])[-60:]))
        if not d_:
            return
        rw_ = next((x for x in rows_ if syms_.get(x['symbol']) == d_['mint']), {})
        row_ = {'at': round(now), 'mode': mode_, 'model': rs._air.model_name(env, who_), 'by': who_, 'talk': True, 'idle': True, 'action': 'TALK', 'view': d_['view'],
                'why': f"on ${rw_.get('symbol')} ({rw_.get('holder')}): {d_['view']} — {d_['why']}"[:rs._seat.WHY_MAX + 60], 'conf': d_['conf'], 'ms': round((rs.time.perf_counter() - t0_) * 1000),
                'symbol': rw_.get('symbol'), 'mint': d_['mint'], 'pct': rw_.get('pct'), 'cap': rw_.get('cap')}
        lg_ = next((l for l in legs_ or [] if l.get('mint') == d_['mint'] and not l.get('placeholder')), None)
        if lg_ and mode_ == 'real' and any(d_.get(k_) for k_ in ('tp', 'sl', 'trail')) and rs._uni.is_agent(lg_) and not lg_.get('picked') and not lg_.get('aiSeat') and not lg_.get('certified'):
            rs._g4['setAgent'] = {'pair': lg_.get('pairAddress'), 'own': False, 'tp': d_.get('tp'), 'sl': d_.get('sl'), 'trail': d_.get('trail'), 'at': rs.time.time(), 'by': rs._air.model_name(env, who_)}
            row_['why'] = (row_['why'] + ' · 🎯 ' + rs._seat.lines_why({k_: d_[k_] for k_ in ('tp', 'sl', 'trail') if d_.get(k_)}, lg_))[:220]
        m1 = rs._g4_mem.get() or {}
        rs._g4_mem.put({**m1, 'log': rs._seat.note(m1.get('log') or st_['log'], row_), 'idleAt': now}, now)
        rs._duo_push()
        rs._dv_note(row_, rs._fuse._f(pxm_.get(d_['mint'])), now)
        return d_
    except Exception as e:
        print('g4 idle:', str(e)[:100])
    return None


async def _reaper_partner(now, env, cfg, st_, card_, mode_, who):
    """🤝 REAPER NEVER TRADES ALONE (owner, 2026-10-18: "someone needs to be with Reaper in his trades"): every PARTNER_EVERY the model that is
    NOT deciding rides along on ONE of the agents' coins (the one read longest ago): HOLD / SELL + its lines. Its word goes into Reaper's own
    decision — SELL = TIGHTEN (a soft exit may act on one look), HOLD = RIDE (soft exits need more looks) — and its lines are set like any
    model line. Graded by the market like every call."""
    rs = _rs()
    legs_ = [l for l in card_.get('legs') or [] if rs._uni.is_agent(l) and not l.get('picked') and not l.get('aiSeat') and not l.get('placeholder') and l.get('real') and rs._fuse._f(l.get('units')) > 0]
    if not legs_ or now - rs._fuse._f(rs._g4.get('partnerAt')) < rs.PARTNER_EVERY:
        return None
    rs._g4['partnerAt'] = now
    seen_ = rs._g4.setdefault('partnerSeen', {})
    lg_ = min(legs_, key=lambda l: rs._fuse._f(seen_.get(l.get('mint'))))
    seen_[lg_.get('mint')] = now
    d_ = await rs._g4_idle(now, env, cfg, st_, [lg_], mode_, who=who)
    if d_ and d_.get('mint') == lg_.get('mint'):
        w_ = 'TIGHTEN' if d_['view'] == 'SELL' else 'RIDE'
        rs._ai['exit'][lg_['mint']] = {'word': w_, 'at': now, 'sym': lg_.get('symbol'), 'why': f"🤝 {rs._air.model_name(env, who)} riding with Reaper: {d_['view']} — {d_.get('why') or ''}"[:120], 'w1': w_, 'p1': who}
    return d_


def _pred_of(mint, now):
    """🔮 A PROVEN model's fresh (≤ 15 min) prediction on this coin, or None. Proven = ai_learn.predict_record for that model (≥ 20 graded calls
    each way, its 'up' calls beat its 'down' calls by ≥ 3 pts and went up). Until then predictions are graded and shown, never steering."""
    rs = _rs()
    if now - rs._pred_c['at'] > 120:
        bk_ = rs._ai_book()
        rs._pred_c.update(at=now, proven={p_ for p_ in (rs._duet.LEAD, rs._duet.SECOND) if rs._ail.predict_record(bk_, p_).get('proven')})
    if not rs._pred_c['proven']:
        return None
    bk_ = rs._ai_book()
    hit_ = [c_ for c_ in (bk_.get('open') or [])[::-1] if c_.get('mint') == mint and c_.get('pred') is not None and c_.get('prov') in rs._pred_c['proven'] and now - rs._fuse._f(c_.get('at')) <= 900]
    return rs._fuse._f(hit_[0]['pred']) if hit_ else None


def _duo_backed(mint, now):
    """🤝 (backed, why) — a model's BUY on this coin (≤ 15 min) or its 15-minute call of +3% or more (≤ 30 min), newest word wins."""
    rs = _rs()
    if now - rs._duo_pred_c['at'] > 20:
        bk_ = rs._ai_book()
        rs._duo_pred_c.update(at=now, rows=[c_ for c_ in (bk_.get('open') or []) + (bk_.get('done') or [])[-300:] if c_.get('pred') is not None and now - rs._fuse._f(c_.get('at')) <= rs._seat.DUO_PRED_SEC])
    return rs._seat.duo_backs((rs._g4_mem.get() or {}).get('log') or [], rs._duo_pred_c['rows'], mint, now)


def _agent_entry_ok(c):
    """🧠 May an agent door take this coin? Not at the gun line / mid-chase / after a spike / on a SKIP (the models' own filter —
    their record is why), not on an entry read the agents' own real trades keep losing on (`office_edge.losing_entries`, 60s cache), and —
    while agentDuoGate is on — only a coin OSSY or G4 backed (owner, 2026-10-18: "agents need to completely be like these guys")."""
    rs = _rs()
    if rs._g4_bad_entry(c):
        return False
    if rs._DUO_GATE['on']:
        ok_, why_ = rs._duo_backed(c.get('mint'), rs.time.time())
        c['duoWhy'] = why_
        if not ok_:
            return False
    pr_ = rs._pred_of(c.get('mint'), rs.time.time())
    if pr_ is not None and pr_ <= -5:   # 🔮 a PROVEN model calls it down ≥ 5% in 15 min: the agents skip it
        return False
    if rs.time.time() - rs._lose_c['at'] > 60:
        pos_l = (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or []
        rs._lose_c.update(at=rs.time.time(), v=rs._oe.losing_entries(pos_l), f=rs._oe.losing_feats(pos_l))
        rs._office['losingEntries'] = rs._lose_c['v']
        rs._office['losingFeats'] = rs._lose_c['f']   # ⚖ Devil's learned objections (shown in the payload)
    hit_ = rs._oe.feats_of_cand(c) & set(rs._lose_c.get('f') or {})
    if hit_:   # ⚖ an entry condition the agents' own record keeps losing on (CROWD FOMO, buying into a buying crowd …)
        return False
    v_ = c.get('vitals') or {}
    if v_.get('ageH') is not None and rs._fuse._f(v_['ageH']) < 6 and v_.get('bundledN') is None and v_.get('snipersN') is None:   # 🕵 a young coin whose launch (bundles / snipers) was never read is not a seat-filler buy
        return False
    if not rs._oe.setups_of(c, rs._uni.germ_max()):   # 🎯 the agents trade the three setups only: HH/HL · the germ · a held breakout
        return False
    c['setups'] = rs._oe.setups_of(c, rs._uni.germ_max())
    rule_ = ((c.get('chart') or {}).get('entry') or [None, None])[1]
    return str(rule_ or '') not in rs._lose_c['v']


def _g4_brake(now):
    """🧯 Which model is braked: its last BRAKE_N closed REAL trades were all losses, and the market has not yet graded its calls back to even
    (duo_votes confidence < 0) — or the brake is under an hour old. → {provider key: {since, why}}. 60s cache."""
    rs = _rs()
    if now - rs._g4_brake_c['at'] < 60:
        return rs._g4_brake_c['v']
    out = {}
    try:
        ps_ = sorted([p_ for p_ in (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or [] if p_.get('g4') and p_.get('realPct') is not None], key=lambda p_: rs._fuse._f(p_.get('closedAt') or p_.get('since')))
        for k_ in (rs._duet.LEAD, rs._duet.SECOND):
            mine_ = [p_ for p_ in ps_ if p_.get('aiBy') == k_]
            br_ = rs._seat.streak_brake([rs._fuse._f(p_['realPct']) for p_ in mine_])
            if not br_:
                continue
            since_ = rs._fuse._f(mine_[-1].get('closedAt') or mine_[-1].get('since'))
            conf_ = rs._dv.confidence(rs._dv_mem.get() or {}, k_)
            if now - since_ < 3600 or conf_ < 0:
                out[k_] = {'since': round(since_), 'why': br_}
    except Exception:
        out = {}
    rs._g4_brake_c.update(at=now, v=out)
    return out


def _g4_picks_only():
    """🧪 The owner's rule for the OSSY / G4 seat (`realCfg.aiSeatPicksOnly`, on by default since 2026-10-29): it may BUY only a coin the desk marks as a
    PICK (brain.edge_pick: a proven rule + its own survival + its germ). Coins it already holds keep running to their exits."""
    rs = _rs()
    return bool(((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}).get('aiSeatPicksOnly', True))


def _g4_bad_entry(c):
    """🔫 The entry the models may NOT take (owner, 2026-10-17: "not entering or even suggesting at the gun line"): pressed under its gun
    line, a breakout chase, after a spike, or the chart's own call is SKIP. → reason or None. Checked when the list is built AND again at the fill.
    2026-10-23 audit of 179 closed model trades: PARABOLIC / "E2 no chasing" entries 10 trades, 1 won, −9.9% avg; a spike bought 5–10% over
    its germ floor 12 trades, −10.7% avg (within 5%: 8 trades, +1.8%) — both refused here, like COMPRESSION."""
    rs = _rs()
    try:
        ch_ = c.get('chart') if isinstance(c.get('chart'), dict) else {}
        st_c = str(((rs._office.get('charts') or {}).get(c.get('mint')) or {}).get('state') or ch_.get('state') or c.get('structure') or '').upper()
        rule_ = str(((ch_.get('entry') or [None, None]) + [None])[1] or '')
        d5_, gd_ = (c.get('nums') or {}).get('d5'), rs._opp.germ_d(ch_)[0]
        return (rs._opp.gun_wall(c) or rs._opp.gun_chase(c) or rs._opp.spike_chase(c) or ('chart says SKIP' if str(c.get('chartCall') or '').upper().startswith('SKIP') else None)
                or ("COMPRESSION — the models' own record there: 46 real trades, 9 won" if st_c == 'COMPRESSION' else None)
                or ("PARABOLIC — no chasing vertical candles (the models' own record: 10 real trades, 1 won, −9.9% avg)" if st_c == 'PARABOLIC' or rule_.startswith('E2') else None)
                or (f"🚀 {rs._fuse._f(d5_):+.0f}% in 5 min and {gd_:.0f}% over its germ floor — a model waits until it's within {rs.G4_SPIKE_GERM:.0f}%"
                    if d5_ is not None and rs._fuse._f(d5_) >= rs._opp.SPIKE_5M and gd_ is not None and gd_ > rs.G4_SPIKE_GERM else None))
    except Exception:
        return None


def _g4_view():
    """🧠 G4's seat for the page: mode, record (paper + real), the open paper seat, the newest minute thoughts."""
    rs = _rs()
    st_ = rs._g4_state()
    mode_ = rs._oe.clean_policy(rs._prime_real_cfg())['agentAiSeat']
    return {'mode': mode_, 'paper': rs._seat.record((st_['book'] or {}).get('closed')), 'byModel': rs._seat.by_model((st_['book'] or {}).get('closed')), 'real': rs._g4_real_record(), 'open': (st_['book'] or {}).get('open'),
            'want': rs._g4.get('want'), 'busy': rs._g4['busy'], 'log': st_['log'][-60:][::-1]}


def _ai_stall_watch(now):
    """🩺 G4 / OSSY stall watchdog (owner night list: 'stalls — read Brain › Models live numbers first, then a stall watchdog'): a model
    that keeps failing while FEELESS keeps asking alerts the owner once per 30 min with the evidence. It never reloads by itself."""
    rs = _rs()
    out_ = []
    for k_ in ('lan', 'local'):
        st_ = rs._mdk.stall_of(rs._air.ROUTER.stats.get(k_), now)
        if not st_ or now - rs._stall_seen.get(k_, 0) < rs.STALL_ALERT_EVERY:
            continue
        rs._stall_seen[k_] = now
        nm_ = rs._air.model_name(rs.os.environ, k_)
        for w_ in rs._owner_wallets()[:2]:
            rs.notify(w_, 'shield', f"🩺 {nm_} stalled — {st_['why']}. Brain › Models › ⚡ Reload brings it back (your call).", url='/terminal/command?tab=agents',
                   once=f"stall-{k_}-{int(now // rs.STALL_ALERT_EVERY)}", meta={'claim': f'{nm_} keeps failing while the desk asks it', 'source': 'AI router stats'})
        out_.append(k_)
    return out_


async def _ai_round(now):
    """One advisory round. Every answer is DISPLAYED (notes by coin + role, with its source); nothing it says reaches a decision."""
    rs = _rs()
    env, cfg = rs.os.environ, rs._ai_cfg()
    if not any(not r_['why'] and r_['enabled'] for r_ in (rs._air.provider(env, k_, cfg) for k_ in rs._air.PROVIDERS)):
        return 0
    try:
        rs._ai_stall_watch(now)   # 🩺 a stalled model alerts the owner (never auto-reloads)
    except Exception:
        pass
    rs.asyncio.ensure_future(rs._local_lane_run(now))   # 💻 the local model's own lane (its own task: a 15–30s inference never holds this round)
    await rs._ai_learn_settle(now)   # 🧠 the model's earlier stances are judged against what the coin did (no model call)
    await rs._lab_tick(now, env, cfg)   # 🧪 the rule lab: the record re-judges every rule; at most once an hour the model proposes new ones
    rs.asyncio.ensure_future(rs._studio_auto_safe(now))   # 🤖 Prompt Studio auto-tune: a model whose switch is on and whose last trades turned red gets its AUTO-TUNED set
    rs.asyncio.ensure_future(rs._feecat_duo_safe(now, env, cfg))   # 🐱🤝 its own task: a stuck desktop model never holds the round (OSSY's minute waited behind it)   # FeeCat's one duo read per 10 min (both models must agree before she acts on it)
    await rs._coach_ai(now, env, cfg)   # 👑 at most every 15 min: the model reads the last real trades and may instruct the agents (bounded, coach.py)
    jobs = rs._ai_jobs(now)
    if not jobs:
        return 0
    t0 = rs.time.perf_counter()
    res = await rs.asyncio.gather(*[rs._air.ROUTER.reason(rs._ai_http(), env, cfg, {**rs._ai_case(c_), **({'atFill': True} if c_.get('atFill') else {})}, role_, urg_, prio=pr_, mode='case')
                                 for role_, c_, urg_, pr_ in jobs], return_exceptions=True)
    n = 0
    for (role_, c_, _u, _p), r_ in zip(jobs, res):
        if isinstance(r_, Exception) or not isinstance(r_, dict) or r_.get('deferred'):
            continue   # a deferred job keeps its last answer (it is asked again on a quieter round)
        m_ = c_.get('mint')
        if not m_:
            continue
        rs._ai['notes'].setdefault(m_, {})[role_] = {k_: r_.get(k_) for k_ in ('source', 'label', 'advice', 'ms', 'at', 'tried', 'why', 'cached')} | {'symbol': c_.get('symbol')}
        if role_ == 'exit':
            w_ = rs._er.word_of(r_.get('advice'), c_.get('pct'))
            rs._ai['exit'][m_] = {'word': w_, 'at': now, 'sym': c_.get('symbol'), 'why': ((r_.get('advice') or {}).get('summary') or '')[:120], 'w1': w_, 'p1': r_.get('source')}
            px_ = (rs._jup_px_cache.get(m_) or (0, 0))[1]
            rs._ai['exitBook'] = rs._er.note(rs._ai_exit_book(), m_, w_, px_, c_.get('pct'), now, c_.get('symbol'), prov=r_.get('source'))
            c_['_word'] = w_
            if r_.get('source') in (rs._duet.LEAD, rs._duet.SECOND):
                rs.asyncio.ensure_future(rs._exit_second(c_, r_.get('source'), px_))
        rs._ai_log(role_, c_, r_)
        rs._ai_learn_note(role_, c_, r_, now)
        n += 1
    if len(rs._ai['notes']) > rs.AI_NOTES_KEEP:
        for m_ in sorted(rs._ai['notes'], key=lambda k_: max(rs._fuse._f(v_.get('at')) for v_ in rs._ai['notes'][k_].values()))[:len(rs._ai['notes']) - rs.AI_NOTES_KEEP]:
            rs._ai['notes'].pop(m_, None)
    rs._ai.update(rounds=rs._ai['rounds'] + 1, lastAt=round(rs.time.time(), 1), lastMs=round((rs.time.perf_counter() - t0) * 1000))
    try:
        if rs._office.get('payload') is not None:
            rs._office['payload']['ai'] = rs._ai_view(light=True)
            rs._tke.HUB.publish('ai_update', 'ai', rs._office['payload']['ai'], rs.time.time())
    except Exception:
        pass
    return n


def _lw_note(now, ok, ms=None, why=None):
    rs = _rs()
    if rs._local_lane['watch'] is None:
        rs._local_lane['watch'] = rs._json_load(rs.LOCAL_WATCH_PATH, {}) or {}
    rs._local_lane['watch'] = rs._aic.watch_note(rs._local_lane['watch'], now, ok, ms, why)
    rs._json_save(rs.LOCAL_WATCH_PATH, rs._local_lane['watch'])


def _local_lane_pick(now):
    """The coin the local model reads next: the best in-band READY / CONTENDING candidate with NO fresh model read (it warms the seat gate)."""
    rs = _rs()
    cands = ((rs._office.get('payload') or {}).get('kernel') or {}).get('candidates') or []
    open_ = [c_ for c_ in cands if c_.get('status') in ('READY', 'CONTENDING') and c_.get('mint') and rs._uni.under_cap({'mcap': c_.get('cap')})]
    for c_ in sorted(open_, key=lambda c_: (c_.get('status') != 'READY', -rs._fuse._f(c_.get('rank')))):
        if rs._air.gate_verdict(rs._ai['notes'].get(c_['mint']), now)[0] is None:
            return c_
    return None


async def _duet_second(c_, r_, env, cfg, lagging=False):
    """💻 Qwen's second read of the case Gemma just read → its own note (slot 'sherlock2', graded on its own) + the merged 'duet' note
    the seat gate reads (an AGREED CAUTION may hold a coin back; a split is neutral until one model proves it wins splits)."""
    rs = _rs()
    now = rs.time.time()
    p_ = rs._air.provider(env, rs._duet.SECOND, cfg)
    if not rs._duet.second_due((r_ or {}).get('advice'), rs._duet_at['second'], now, lagging) or not p_['enabled'] or p_['why'] or rs._air.ROUTER.stats[rs._duet.SECOND]['coolUntil'] > now:
        return
    rs._duet_at['second'] = now
    try:
        r2 = await rs._air.ROUTER.reason(rs._ai_http(), env, cfg, rs._ai_case(c_), 'sherlock', 'force', prio=rs._air.PRIO['ready'], only=(rs._duet.SECOND,), mode='case')
    except Exception as e:
        print('duet second:', str(e)[:100]); return
    if not (r2 or {}).get('advice') or r2.get('source') != rs._duet.SECOND:
        return
    rs._ai_keep('sherlock', c_, r2, rs.time.time(), slot='sherlock2')
    m_ = rs._duet.merge(r_.get('advice'), r2.get('advice'), rs._duet.record(rs._ai_book().get('done')))
    rs._ai['notes'].setdefault(c_['mint'], {})['duet'] = {'source': 'duet', 'label': '🤝 DUET', 'at': rs.time.time(), 'symbol': c_.get('symbol'),
                                                        'advice': {**m_, 'risk_flags': m_['flags'], 'summary': m_['why']}}


async def _exit_second(c_, first_src, px_):
    """🤝 THE DUET ON EXITS (owner, 2026-10-15: "let both AI models decide on the vitals before, during and after a trade"): the other
    LM Studio model reads the SAME held seat. Agree → the word stands · split → no word (Reaper ignores a split). Each model's read is graded
    on its own (exit_read prov), so the page shows who reads exits better. Never while a browser reports lag on a shared GPU."""
    rs = _rs()
    now = rs.time.time()
    other = rs._duet.SECOND if first_src == rs._duet.LEAD else rs._duet.LEAD
    if rs._exit2['busy'] or now - rs._exit2['at'] < rs.EXIT2_EVERY:
        return
    env, cfg = rs.os.environ, rs._ai_cfg()
    pv = rs._air.provider(env, other, cfg)
    if not pv['enabled'] or pv['why'] or rs._air.ROUTER.stats[other]['coolUntil'] > now:
        return
    if other == 'local' and not rs._air.local_remote(env) and any(now - x_['at'] <= 120 and (rs._fuse._f(x_.get('fps')) and rs._fuse._f(x_.get('fps')) < 30) for x_ in list(rs._perf_samples)[-60:]):
        return   # the shared GPU is busy drawing a lagging page
    rs._exit2.update(at=now, busy=True)
    try:
        r2 = await rs._air.ROUTER.reason(rs._ai_http(), env, cfg, rs._ai_case(c_), 'exit', 'force', prio=rs._air.PRIO['exit'], only=(other,), mode='case')
        if not (r2 or {}).get('advice') or r2.get('source') != other:
            return
        m_ = c_['mint']
        w2 = rs._er.word_of(r2.get('advice'), c_.get('pct'))
        rs._ai['exitBook'] = rs._er.note(rs._ai_exit_book(), m_, w2, px_, c_.get('pct'), rs.time.time(), c_.get('symbol'), prov=other)
        e_ = rs._ai['exit'].get(m_) or {}
        if e_:
            e_.update(word=rs._er.pair_word(e_.get('w1'), w2), w2=w2, p2=other, at=rs.time.time())
        rs._ai_keep('exit', {**c_, '_word': w2}, r2, rs.time.time(), slot='exit2')
    except Exception as e:
        print('exit second:', str(e)[:100])
    finally:
        rs._exit2['busy'] = False


async def _local_lane_run(now):
    """💻 THE LOCAL MODEL WORKS FOR THE AGENTS (owner, 2026-10-13: "local LM needs to be stronger for them" · "it stopped running"): its own
    lane, beside the cloud — every LOCAL_LANE_EVERY it PRE-READS the best candidate nobody has read yet, so the seat gate finds a fresh
    read waiting (and the cloud is asked less). One inference at a time, in its own task: it never delays a pass, a tick or the cloud round."""
    rs = _rs()
    try:
        await rs._air.ROUTER.heartbeat(rs._ai_http(), rs.os.environ, rs._ai_cfg(), now)   # 💓 not ONLINE → one cheap model-list read brings it back (no Test click)
    except Exception:
        pass
    every = rs._fuse._f(rs.os.environ.get('LOCAL_LANE_SEC')) if rs.os.environ.get('LOCAL_LANE_SEC') not in (None, '') else rs.LOCAL_LANE_EVERY
    lane_ = 'lan' if rs._air.lan_ready(rs.os.environ, rs._ai_cfg()) else 'local'   # 🖥 the desktop Mac's gemma takes the lane when it is set up: this Mac's GPU stays the browser's
    remote_ = lane_ == 'lan' or rs._air.local_remote(rs.os.environ)
    if every > 0 and remote_:   # 🖥 LM Studio on another machine: no shared GPU here, so it pre-reads 3× as often
        every = min(every, rs.LOCAL_LANE_EVERY / 3)
    if every <= 0:
        return
    why_ = ''
    try:   # 💻 the owner's 24h boost: faster reads, paused by itself while a browser reports lag (the GPU is shared with Chrome)
        rs._brain_load()
        perf_ = [x_ for x_ in list(rs._perf_samples)[-200:] if now - x_['at'] <= 120]
        every, why_ = rs._aic.lane_every(rs._chat['settings'], now, perf_, rs._local_lane.get('lastMs'), base=every, shared_gpu=not remote_)
        if (why_.startswith('boost paused') or why_.startswith('paused')) and now - rs._local_lane['pausedAt'] >= 600:   # the watch notes a pause once per 10 min
            rs._local_lane['pausedAt'] = now; rs._lw_note(now, False, why='paused')
        rs._local_lane.update(every=round(every, 1), whyEvery=why_)
    except Exception as e:
        print('local boost:', str(e)[:80])
    if rs._local_lane['busy'] or now - rs._local_lane['at'] < every or rs._chat.get('busy'):   # 💬 the owner's chat goes first: the background read waits while you talk
        return
    env, cfg = rs.os.environ, rs._ai_cfg()
    p_ = rs._air.provider(env, lane_, cfg)
    if not p_['enabled'] or p_['why'] or rs._air.ROUTER.stats[lane_]['coolUntil'] > now:
        return
    c_ = rs._local_lane_pick(now)
    if not c_:
        return
    rs._local_lane.update(at=now, busy=True)
    try:
        r_ = await rs._air.ROUTER.reason(rs._ai_http(), env, cfg, rs._ai_case(c_), 'sherlock', 'high', prio=rs._air.PRIO['ready'], only=(lane_,), mode='case')
        ok_ = bool((r_ or {}).get('advice')) if isinstance(r_, dict) else False
        rs._local_lane['lastMs'] = (r_ or {}).get('ms') if isinstance(r_, dict) else None
        rs._lw_note(rs.time.time(), ok_, rs._local_lane['lastMs'])
        if rs._ai_keep('sherlock', c_, r_, rs.time.time()) and (r_ or {}).get('advice'):
            rs._local_lane.update(n=rs._local_lane['n'] + 1, last={'at': round(rs.time.time(), 1), 'symbol': c_.get('symbol'), 'ms': r_.get('ms'), 'stance': (r_.get('advice') or {}).get('stance'), 'via': r_.get('source')})
            if lane_ == rs._duet.LEAD:   # 🤝 THE DUET: Qwen re-reads what Gemma flagged — the pair is graded together and learns whose split call to follow
                await rs._duet_second(c_, r_, env, cfg, lagging=why_.startswith('boost paused') or why_.startswith('paused'))
    except Exception as e:
        print('local lane:', str(e)[:100])
    finally:
        rs._local_lane['busy'] = False


def _ai_keep(role_, c_, r_, now, slot=None):
    """One model answer → the notes by coin + role (or `slot`: the duet's second read keeps its own), the log and the judged record."""
    rs = _rs()
    if isinstance(r_, Exception) or not isinstance(r_, dict) or r_.get('deferred') or not c_.get('mint'):
        return False
    rs._ai['notes'].setdefault(c_['mint'], {})[slot or role_] = {k_: r_.get(k_) for k_ in ('source', 'label', 'advice', 'ms', 'at', 'tried', 'why', 'cached')} | {'symbol': c_.get('symbol')}
    rs._ai_log(role_, c_, r_)
    rs._ai_learn_note(role_, c_, r_, now)
    return True


async def _ai_gate(plan, need, cfg_t, now):
    """🛂 THE MODEL READS A COIN BEFORE IT TAKES A REAL SEAT (2026-10-13: of the last 24 real buys the model had read NONE before the buy —
    its reads came a round later, for display). For the coins about to be seated: a fresh read is used, a missing one is asked for now
    (cloud only, in parallel, ≤ AI_GATE_SEC). A strong, specific CAUTION holds that coin back this tick — graded by the regret ledger
    (`ai:CAUTION`), which switches the wait off if the coins it held back keep beating the ones taken. Silence, a slow answer, no cloud
    provider or the owner's switch off = the coin goes. It can only ever make the agents buy LESS. → (plan, waits)"""
    rs = _rs()
    if not plan or not cfg_t.get('agentAiGate', True) or not rs._rg.effective(cfg_t, rs._regret_book()).get('aiWait', True):
        return plan, []
    env, cfg = rs.os.environ, rs._ai_cfg()
    head = plan[:max(1, need) + 2]
    ask = [t_ for t_ in head if rs._air.gate_verdict(rs._ai['notes'].get(t_['mint']), now)[0] is None]
    if ask and rs._air.cloud_ready(rs._air.ROUTER, env, cfg, now):
        cs_ = [{**t_, 'cap': (t_.get('vitals') or {}).get('mcap'), 'liq': (t_.get('nums') or {}).get('liq'), 'vol5m': (t_.get('nums') or {}).get('v5'), 'move5m': (t_.get('nums') or {}).get('d5'),
                'buyShare': (t_.get('nums') or {}).get('buy'), 'ageMin': None if (t_.get('vitals') or {}).get('ageH') is None else round(rs._fuse._f(t_['vitals']['ageH']) * 60, 1), 'state': 'about to take a real seat'} for t_ in ask]
        tasks = [rs.asyncio.ensure_future(rs._air.ROUTER.reason(rs._ai_http(), env, cfg, rs._ai_case(c_), 'devil', 'high', prio=rs._air.PRIO['ready'], mode='case')) for c_ in cs_]
        for tk_, c_ in zip(tasks, cs_):   # an answer that lands after the wait is still kept (the next tick reads it)
            tk_.add_done_callback(lambda f_, c_=c_: (not f_.cancelled()) and f_.exception() is None and rs._ai_keep('devil', c_, f_.result(), rs.time.time()))
        await rs.asyncio.wait(tasks, timeout=rs.AI_GATE_SEC)
    out, waits = [], []
    for t_ in plan:
        v_, why_ = rs._air.gate_verdict(rs._ai['notes'].get(t_['mint']), rs.time.time()) if t_ in head else (None, None)
        if v_ == 'wait':
            rs._regret_note(t_['mint'], 'ai:CAUTION', rs._fuse._f(t_.get('px')), t_.get('symbol'))
            waits.append({'symbol': t_.get('symbol'), 'why': f"🧠 {why_}"})
            rs._tk.KERNEL.note('devil', 'AI WAIT', f"🧠 the model's read holds it back — {why_}", now, mint=t_['mint'], key=f"aigate:{int(now // 120)}")
            continue
        out.append(t_)
    return out, waits


def _ai_pause(round_sec):
    """Seconds to wait before the next advisory round: AI_EVERY, or longer when the last round kept the model busy (a 60s round on
    a loaded Mac → 60s off). A cloud provider answering in a second keeps the normal pace."""
    rs = _rs()
    return max(rs.AI_EVERY, rs._fuse._f(round_sec) * (1 - rs.AI_DUTY) / rs.AI_DUTY)


async def _g4_loop():
    """🔁 OSSY × G4 on THEIR OWN clock (2026-10-17: the minute only ran when the whole advisory round looped — rounds of 2+ min with
    the background reads, so OSSY went quiet for minutes). The trade chat comes first; the advisory round never holds it."""
    rs = _rs()
    await rs.asyncio.sleep(25)
    while True:
        try:
            now = rs.time.time()
            if (not rs._g4['busy'] or now - rs._fuse._f(rs._g4.get('at')) >= rs.G4_STUCK_SEC) and rs._seat.due(rs._g4['at'], now):
                env, cfg = rs.os.environ, rs._ai_cfg()
                if any(not r_['why'] and r_['enabled'] for r_ in (rs._air.provider(env, k_, cfg) for k_ in (rs._duet.LEAD, rs._duet.SECOND))):
                    rs.asyncio.ensure_future(rs._g4_tick(now, env, cfg))   # its own task: the 5s clock keeps running (a stuck tick is let go inside after 4 min)
        except Exception as e:
            print('g4 loop:', type(e).__name__, str(e)[:80])
        await rs.asyncio.sleep(rs.G4_LOOP_SEC)


async def _ai_loop():
    """🧠 The advisory loop — its own task, so a slow model can never delay a pass, a tick, a stop or an order."""
    rs = _rs()
    await rs.asyncio.sleep(20)
    while True:
        t0 = rs.time.time()
        try:
            await rs._ai_round(rs.time.time())
        except Exception as e:
            print('ai:', type(e).__name__)
        await rs.asyncio.sleep(rs._ai_pause(rs.time.time() - t0))


def _ai_general_context():
    """A few desk facts a GENERAL owner question may lean on (numbers the desk already holds — no fetch, no secrets, no addresses)."""
    rs = _rs()
    try:
        money, cap_, tr_ = rs._agents.get('money') or {}, rs._capital_view(), rs._office.get('trail') or {}
        prov = [f"{r_.get('label')}: {r_.get('state')}" + (f" ({r_.get('model')})" if r_.get('model') else '') for r_ in (rs._air.ROUTER.view(rs.os.environ, rs._ai_cfg()).get('providers') or []) if r_.get('state') not in ('KEY MISSING', 'NOT CONFIGURED')]
        return {'card': f"real card worth ${rs._fuse._f(money.get('value')):.2f}, ${rs._fuse._f(money.get('putIn')):.2f} put in" if money.get('value') is not None else None,
                'capital': rs._cap.lesson(cap_), 'trail': tr_.get('words'), 'reaperSettings': ' · '.join(f"{k_} {v_:g}" for k_, v_ in rs._of.tunes(rs._office_state(), 'reaper').items()),
                'providers': ' · '.join(prov)[:300] or None, 'localModelContext': (rs._air.ROUTER._ctx or (0, None))[1]}
    except Exception:
        return {}


def _brain_load():
    rs = _rs()
    if not rs._chat['loaded']:
        d_ = rs._json_load(rs.AI_CHAT_PATH, {}) or {}
        rs._chat.update(th=d_.get('th') or {}, saved=d_.get('saved') or [], settings=rs._aic.clean_settings(d_.get('settings')), loaded=True)
    return rs._chat


def _chat_persist():
    rs = _rs()
    rs._json_save(rs.AI_CHAT_PATH, {'th': rs._chat['th'], 'saved': rs._chat['saved'], 'settings': rs._chat['settings']})


def _chat_extra():
    rs = _rs()
    return {'threads': rs._aic.threads_view(rs._chat['th']), 'saved': rs._aic.saved_view(rs._chat['saved']), 'settings': rs._chat['settings'],
            'local': rs._aic.watch_view(rs._local_lane.get('watch') if rs._local_lane.get('watch') is not None else (rs._json_load(rs.LOCAL_WATCH_PATH, {}) or {}), rs._chat['settings'], rs.time.time(), rs._local_lane.get('every'), rs._local_lane.get('whyEvery'))}


def _chat_props():
    rs = _rs()
    if rs._chat['props'] is None:
        rs._chat['props'] = rs._json_load(rs.AI_PROPOSALS_PATH, {}) or {}
    return rs._chat['props']


def _chat_context(focus, now):
    """The desk's current truth for the chat, compact + cached: one build per AI_CHAT_CTX_SEC and per selected coin (no fetch, no scan)."""
    rs = _rs()
    k_, c_, at_ = rs._chat['ctx']
    if c_ is None or k_ != focus or now - at_ >= rs.AI_CHAT_CTX_SEC:
        c_ = rs._aic.context({**(rs._office.get('payload') or {}), 'capital': rs._capital_view(), 'trail': rs._office.get('trail')}, focus, tuple(rs._co.CAUSES))
        rs._chat['ctx'] = (focus, c_, now)
    if isinstance(c_, dict):
        try:   # 🦠 the germ entry's own real record (thesis germEntry on confirmed exits)
            c_ = {**c_, 'germRecord': rs._aic.germ_record(rs._real_trades())}
        except Exception as e_:
            print('chat germ record:', str(e_)[:80])
    return {**c_, 'today': rs.time.strftime('%A %Y-%m-%d %H:%M %Z', rs.time.localtime(now))} if isinstance(c_, dict) else c_   # 🕐 the models have no clock


def _chat_olds():
    """What each proposable thing is RIGHT NOW (shown as the proposal's old value)."""
    rs = _rs()
    rc = rs._prime.clean_cfg((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {})
    tn = rs._of.tunes(rs._office_state(), 'reaper')
    import ai_rig as _rg
    rg_ = _rg.clean({}, rs._json_load(rs.AI_RIG_PATH, {}))
    st_ = rs._chat.get('settings') or {}
    rig_ = {('rig', f'chat.{f_}'): st_.get(f_) for f_ in ('temp', 'len')}
    rig_.update({('rig', f'{k_}.{f_}'): v_ for k_ in _rg.KEYS for f_, v_ in rg_[k_].items() if f_ != 'load'})
    for k_ in _rg.LM_KEYS:   # a load's "now" = what LM Studio REPORTS it runs (last read), never the saved wish
        ld_ = (((rs._lms_seen.get(k_) or (0, None))[1] or {}).get('loaded') or [None])[0]
        rig_[('rig', f'{k_}.load')] = _rg.load_value({f_: ld_[f_] for f_ in _rg.LOAD_OPTIONS if ld_.get(f_) is not None}) if ld_ else 'not loaded'
    return {**{('cfg', k_): rc.get(k_) for k_ in rs._aic.SAFE_CFG}, **{('tune', k_): tn.get(k_) for k_ in rs._aic.TUNE_KEYS}, **rig_}


async def _ai_proposal_apply(p, now):
    """✅ THE ONLY PLACE AN APPROVED PROPOSAL TOUCHES THE DESK — one branch per safe kind, each through the desk's own existing path.
    Nothing here can reach an order, a size, a seat, a stop, a limit, a wallet or a key. → the audit line."""
    rs = _rs()
    kind, key, val = p.get('kind'), p.get('key'), p.get('new')
    if kind == 'cfg':
        if key not in rs._aic.SAFE_CFG or val not in rs._aic.SAFE_CFG[key]:
            raise ValueError('not an advisory switch')
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
            old = rs._prime.clean_cfg(pr.get('realCfg') or {}).get(key)
            pr['realCfg'] = rs._prime.clean_cfg({**(pr.get('realCfg') or {}), key: val})
            pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {key})
            pr['ladderKeep'] = sorted(set(pr.get('ladderKeep') or []) | {key})
            rs._json_save(rs.FUSE_HQ_PATH, d)
        return f"{key}: {old} → {val}"
    if kind == 'lesson':
        rs._teach['st'] = rs._tch.add(rs._teach_state(), {'kind': key, 'text': str(val)}, now)
        rs._json_save(rs.TEACH_PATH, rs._teach['st'])
        if rs._office.get('payload') is not None:
            rs._office['payload']['teach'] = {**rs._tch.view(rs._teach['st']), 'rules': rs._taught_view()}
        return f"lesson filed ({key}) — every fitting model case reads it"
    if kind == 'weight':
        st_, rule_ = rs._co.add(rs._coach_state(), key, 'owner', str(val), now)
        if rule_:
            rs._coach_put(st_)
        return f"rank weight on '{key}' {rule_['points']:+.0f} for 24h" if rule_ else f"a rule for '{key}' is already live"
    if kind == 'tune':
        rs._coach['tuneAsk'] = {'key': key, 'dir': val, 'why': str(p.get('reason') or '')[:90], 'at': now}   # the office pass puts it in SHADOW (office.model_candidate) — never live
        return f"Reaper {key} {val}: queued for a 20-exit shadow test"
    if kind == 'rig':   # 🎛 a MODEL setting the owner approved (ai_rig.check_change is the gate) — a load change reloads that model NOW, once
        import ai_rig as _rg
        v_ = _rg.check_change(key, val)
        if v_ is None:
            raise ValueError('not a model setting')
        mk_, _s, f_ = str(key).partition('.')
        if mk_ == 'chat':
            rs._brain_load()
            rs._chat['settings'] = rs._aic.clean_settings({f_: v_}, rs._chat['settings'])
            rs._chat_persist()
            return f"Brain chat {'temperature' if f_ == 'temp' else 'answer length'} → {v_} (live now)"
        prev_ = _rg.clean({}, rs._json_load(rs.AI_RIG_PATH, {}))
        if f_ == 'load':
            want_ = _rg.parse_load_value(v_)
            new_ = _rg.clean({mk_: {'load': want_}}, prev_)
            rs._json_save(rs.AI_RIG_PATH, new_); rs._rig_apply()
            res_ = await rs._lms_reload(mk_, new_[mk_]['load'])
            rs._lms_seen.pop(mk_, None)
            if not res_.get('ok'):
                return f"{_rg.NAMES[mk_]}: saved {_rg.load_words(want_)}, but the reload FAILED — {res_.get('err')} (tap ⚡ Reload in Brain › Models to retry)"
            got_ = res_.get('loaded') or {}
            return (f"{_rg.NAMES[mk_]} reloaded in {res_['ms'] / 1000:.1f}s — LM Studio reports {_rg.load_words({k_: got_[k_] for k_ in _rg.LOAD_OPTIONS if got_.get(k_) is not None}) or 'loaded'}"
                    + (f" · {res_['note']}" if res_.get('note') else ''))
        new_ = _rg.clean({mk_: {f_: v_}}, prev_)
        rs._json_save(rs.AI_RIG_PATH, new_); rs._rig_apply()
        return f"{_rg.NAMES[mk_]} {f_}: {prev_[mk_].get(f_)} → {v_} (live now — what FEELESS sends)"
    if kind == 'idea':   # 📋 approving an idea = permission to BUILD it: it joins the build queue the next engineering session works through
        try:
            rs._chat['build'], it_ = rs._aic.build_add(rs._build_state(), key, f"{val}" + (f" — why: {p.get('reason')}" if p.get('reason') else ''), f"approved · {p.get('agent') or 'desk'}", now)
            rs._json_save(rs.BUILD_QUEUE_PATH, rs._chat['build'])
            return f"queued for the build ({it_['id']}) — it changes no setting until it is built and shipped"
        except ValueError as e:
            return f"idea filed — {e}"
    raise ValueError('unknown kind')


def _rig_apply():
    rs = _rs()
    import ai_rig as _rg
    rs._air.RIG.clear()
    rs._air.RIG.update(_rg.clean({}, rs._json_load(rs.AI_RIG_PATH, {})))
    return rs._air.RIG


async def _lms_reload(key, want):
    """⚡ The ONE door to an LM Studio reload (the owner's ✅ or ⚡ tap): marks the reload for the keep-alive watchdog, reloads, clears the mark."""
    rs = _rs()
    try:
        rs.LMS_MARK_PATH.write_text(f'{key} {rs.time.time():.0f}')
    except OSError:
        pass
    try:
        return await rs._air.ROUTER.reload_model(rs._ai_http(), rs.os.environ, rs._ai_cfg(), key, want)
    finally:
        try:
            rs.LMS_MARK_PATH.unlink()
        except OSError:
            pass


async def _lms_states(fresh=False):
    """G4 + OSSY's LM Studio state, read in parallel (one cheap GET each, no inference) → {key: lms_row | None}."""
    rs = _rs()
    now_ = rs.time.time()
    keys_ = [k_ for k_ in ('lan', 'local') if fresh or now_ - (rs._lms_seen.get(k_) or (0, None))[0] > 15]
    if keys_:
        got_ = await rs.asyncio.gather(*[rs._air.ROUTER.lms_state(rs._ai_http(), rs.os.environ, rs._ai_cfg(), k_) for k_ in keys_], return_exceptions=True)
        for k_, v_ in zip(keys_, got_):
            rs._lms_seen[k_] = (now_, None if isinstance(v_, BaseException) else v_)
    return {k_: (rs._lms_seen.get(k_) or (0, None))[1] for k_ in ('lan', 'local')}


async def _mdk_cached(tag, ttl, fn):
    rs = _rs()
    hit = rs._mdk_seen.get(tag)
    if hit and rs.time.time() - hit[0] < ttl:
        return hit[1]
    try:
        v = await fn()
    except Exception as e:
        v = {'err': type(e).__name__}
    rs._mdk_seen[tag] = (rs.time.time(), v)
    return v


async def _mdk_lms(key):
    """LM Studio's own model list for one model's server → {data, ms, base} (raw, so INFO shows every field it reports)."""
    rs = _rs()
    async def go():
        p_ = rs._air.provider(rs.os.environ, key, rs._ai_cfg())
        if not p_.get('enabled') or not p_.get('base'):
            return {'err': p_.get('why') or 'off', 'base': p_.get('base')}
        root_ = rs._re.sub(r'/v1/?$', '', str(p_['base']).rstrip('/'))
        t0_ = rs.time.perf_counter()
        r_ = await rs.asyncio.wait_for(rs._ai_http().get(root_ + '/api/v1/models', **rs._air._lm_auth(rs.os.environ, key)), timeout=5)
        return {'data': r_.json() if r_.status_code == 200 else None, 'ms': round((rs.time.perf_counter() - t0_) * 1000), 'base': p_['base'],
                'err': None if r_.status_code == 200 else f'HTTP {r_.status_code}', 'model': p_.get('model')}
    return await rs._mdk_cached(f'lms:{key}', 15, go)


async def _mdk_mcp():
    """FEELESS's MCP server (feeless_mcp.py) as a model sees it: tools/list over its authenticated JSON-RPC."""
    rs = _rs()
    async def go():
        import feeless_mcp as _mcp_
        port_ = int(rs.os.environ.get('FEELESS_MCP_PORT', '8765'))
        t0_ = rs.time.perf_counter()
        try:
            r_ = await rs.asyncio.wait_for(rs._ai_http().post(f'http://127.0.0.1:{port_}/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'},
                                                        headers={'Authorization': f'Bearer {_mcp_.token()}', 'Accept': 'application/json, text/event-stream'}), timeout=5)
            tools_ = ((r_.json() or {}).get('result') or {}).get('tools') or [] if r_.status_code == 200 else []
            return rs._mdk.mcp_view(tools_, round((rs.time.perf_counter() - t0_) * 1000), None if r_.status_code == 200 else f'HTTP {r_.status_code}', f':{port_}/mcp')
        except Exception as e:
            return rs._mdk.mcp_view([], None, type(e).__name__, f':{port_}/mcp')
    return await rs._mdk_cached('mcp', 60, go)


async def _model_desk_view():
    rs = _rs()
    rig_ = rs._rig_apply()
    lan_, local_, mcp_ = await rs.asyncio.gather(rs._mdk_lms('lan'), rs._mdk_lms('local'), rs._mdk_mcp())
    v_ = rs._air.ROUTER.view(rs.os.environ, rs._ai_cfg())
    live_ = {r_['key']: r_ for r_ in v_.get('providers') or []}
    log_ = list(rs._air.CALL_LOG)
    act_ = rs._studio_apply()
    out_ = []
    for k_, raw_ in (('lan', lan_), ('local', local_)):
        lv_ = live_.get(k_) or {}
        p_ = rs._air.provider(rs.os.environ, k_, rs._ai_cfg())
        row_, listed_ = rs._mdk.lms_pick((raw_ or {}).get('data'), (raw_ or {}).get('model'))
        info_ = rs._mdk.lms_info(row_)
        ctx_ = (info_ or {}).get('loadedCtx')
        server_ = {'endpoint': rs._mdk.host_of((raw_ or {}).get('base')), 'api': 'LM Studio · OpenAI /v1 + REST /api/v1', 'ok': bool((raw_ or {}).get('data')),
                   'ms': (raw_ or {}).get('ms'), 'err': (raw_ or {}).get('err'), 'listed': listed_, 'instances': (info_ or {}).get('instances'),
                   'keySet': bool(rs._air._lm_auth(rs.os.environ, k_).get('headers'))}
        rg_ = rig_.get(k_) or {}
        server_.update(timeout=rg_.get('timeout'), parallel=rg_.get('parallel'), perMin=rg_.get('perMin'), state=lv_.get('state'), lastOkAt=lv_.get('lastOkAt'))
        a_ = act_.get(k_)
        out_.append({'key': k_, 'name': rs._air.model_name(rs.os.environ, k_), 'state': lv_.get('state'), 'model': (info_ or {}).get('name') or p_.get('model'),
                     'info': info_, 'server': server_, 'vitals': rs._mdk.vitals(log_, rs._air.INFLIGHT, k_, ctx_), 'stall': rs._mdk.stall_of(rs._air.ROUTER.stats.get(k_), rs.time.time()),
                     'inference': {'infer': rg_.get('infer') or {}, 'desk': {'temp': 0.1, 'maxTok': rs._air.MAX_TOKENS},
                                   'runtime': None,
                                   'reasoning': (info_ or {}).get('reasoning'),
                                   'mindset': {'set': a_['set'], 'seen': rs._air.MINDSET_SEEN.get(k_)} if a_ else None,
                                   'speculative': None}})
    return {'models': out_, 'mcp': mcp_, 'bounds': {k_: [lo_, hi_] for k_, (lo_, hi_, _t) in __import__('ai_rig').INFER_BOUNDS.items()}, 'at': rs.time.time()}


def _studio_apply():
    """The applied sets → the router (`_air.STUDIO`). Returns the clean active map."""
    rs = _rs()
    act_ = rs._pstu.clean_active(rs._json_load(rs.PROMPT_STUDIO_PATH, {}))
    rs._air.STUDIO.clear()
    rs._air.STUDIO.update({k_: v_['text'] for k_, v_ in act_.items()})
    rs._air.STUDIO_SET.clear()
    rs._air.STUDIO_SET.update({k_: v_['set'] for k_, v_ in act_.items()})
    rs._studio_lms(act_)
    return act_


def _studio_lms(act_):
    """📌 Keep LM Studio's "FEELESS LIVE · OSSY" preset = what FEELESS really sends OSSY: the seat prompt + the applied mindset + the sampling
    overrides (lms_preset.py). The owner's own LM Studio preset is never touched."""
    rs = _rs()
    try:
        import lms_preset as _lmp
        a_ = act_.get('local')
        sys_ = rs._seat.sys_for(rs._seat.SYSTEM, 'local') + (rs._pstu.overlay_block(a_['text']) if a_ else '')
        p_ = _lmp.write('local', sys_, (rs._air.RIG.get('local') or {}).get('infer'))
        if p_:
            rs._studio_lms_note['local'] = {'name': _lmp.NAME['local'], 'path': p_, 'at': rs.time.time(), 'set': (a_ or {}).get('set')}
    except Exception as e:
        print('lms preset:', str(e)[:80])


def _studio_trades(key):
    """A seat model's closed REAL trades from the ledger tape (trims included) → [{pct, peak, heldMin, at}], oldest first."""
    rs = _rs()
    if key not in ('lan', 'local'):
        return []
    pos_, tape_ = rs._duo_tape()
    out = []
    for row_ in tape_ or []:
        if row_.get('state') != 'sold' or not row_.get('result'):
            continue
        p_ = next((x_ for x_ in pos_ or [] if x_.get('mint') == row_.get('mint') and abs(rs._fuse._f(x_.get('since')) - rs._fuse._f(row_.get('at'))) <= 900), None)
        if (p_ or {}).get('aiBy') != key:
            continue
        r_ = row_['result']
        out.append({'pct': r_.get('pct'), 'peak': r_.get('peak'), 'heldMin': r_.get('heldMin'), 'usd': r_.get('usd'), 'at': row_.get('at')})
    return sorted(out, key=lambda t_: rs._fuse._f(t_.get('at')))


def _studio_core(k_, st_, done_):
    """One model's record → {trades, stats, fixes, sets} (the view and the auto-tune switch read the same numbers)."""
    rs = _rs()
    nm_ = rs._air.model_name(rs.os.environ, k_)
    trades_ = rs._studio_trades(k_)
    calls_ = [r_ for r_ in st_['log'] if r_.get('model') == nm_ and r_.get('action') != 'LINES' and not r_.get('talk')]
    s_ = rs._pstu.stats(trades_, calls_, rs._seat.bench(done_, k_))
    fx_ = rs._pstu.diagnose(s_)
    raw_ = rs._json_load(rs.PROMPT_STUDIO_PATH, {}) or {}
    best_ = rs._pstu.best_rung(rs._pstu.ladder(trades_, raw_.get('history'), k_, rs.time.time(), rs._pstu.clean_active(raw_).get(k_)))
    return {'trades': trades_, 'stats': s_, 'fixes': fx_, 'sets': rs._pstu.sets(k_, s_, fx_, best_)}


async def _studio_auto(now):
    """🤖 AUTO-TUNE (owner, 2026-10-22): every 5 min, for each model whose switch is ON — when its last trades turn RED, its AUTO-TUNED set is
    applied (after any applied set's 6 h cooldown), logged and put on the ladder's history. Never touches a model whose switch is off."""
    rs = _rs()
    if now - rs._studio_auto_at['t'] < 300:
        return 0
    rs._studio_auto_at['t'] = now
    raw_ = dict(rs._json_load(rs.PROMPT_STUDIO_PATH, {}) or {})
    on_ = {k_ for k_ in rs._pstu.KEYS if rs._pstu.auto_on(raw_, k_)}
    if not on_:
        return 0
    act_ = rs._pstu.clean_active(raw_)
    st_, done_ = rs._g4_state(), (rs._ai.get('book') or {}).get('done') or []
    n_ = 0
    for k_ in sorted(on_):
        core_ = rs._studio_core(k_, st_, done_)
        tuned_ = next((x_ for x_ in core_['sets'] if x_['set'] == 'tuned'), None)
        pick_ = rs._pstu.auto_pick(True, act_.get(k_), rs._pstu.recent(core_['trades']), tuned_, now)
        if not pick_:
            continue
        raw_[k_] = {'set': 'tuned', 'text': pick_['text'], 'at': now, 'by': 'auto', 'edited': False}
        raw_['history'] = rs._pstu.hist_add(raw_.get('history'), k_, 'tuned', now, 'auto')
        raw_['autoLog'] = (list(raw_.get('autoLog') or []) + [{'key': k_, 'at': round(now), 'why': pick_['why'], 'fixes': [f_['title'] for f_ in core_['fixes']]}])[-60:]
        n_ += 1
        print(f"prompt studio: auto-tuned {rs._air.model_name(rs.os.environ, k_)} — {pick_['why']}")
    if n_:
        rs._json_save(rs.PROMPT_STUDIO_PATH, raw_)
        rs._studio_apply()
    return n_


async def _studio_auto_safe(now):
    rs = _rs()
    try:
        await rs._studio_auto(now)
    except Exception as e:
        print('prompt studio auto:', str(e)[:100])


def _studio_layer(k, label, text, note=None):
    t_ = str(text or '')
    return {'k': k, 'label': label, 'chars': len(t_), 'tok': (len(t_) + 3) // 4, 'text': t_[:4000], **({'note': note} if note else {})}


async def _studio_view():
    rs = _rs()
    act_, rig_ = rs._studio_apply(), rs._rig_apply()
    lms_ = await rs._lms_states()
    v_ = rs._air.ROUTER.view(rs.os.environ, rs._ai_cfg())
    live_ = {r_['key']: r_.get('state') for r_ in v_.get('providers') or []}
    st_ = rs._g4_state()
    done_ = (rs._ai.get('book') or {}).get('done') or []
    brain_ = rs._air.brain_text(rs.os.environ) or ''
    raw_ = rs._json_load(rs.PROMPT_STUDIO_PATH, {}) or {}
    now_ = rs.time.time()
    models_ = []
    for k_ in rs._pstu.KEYS:
        nm_ = rs._air.model_name(rs.os.environ, k_)
        core_ = rs._studio_core(k_, st_, done_)
        trades_, s_, fx_ = core_['trades'], core_['stats'], core_['fixes']
        lm_ = (lms_ or {}).get(k_) or {}
        ctx_ = int(rs._fuse._f(((lm_.get('loaded') or [{}])[0] or {}).get('ctx')) or rs._fuse._f((rig_.get(k_) or {}).get('ctx')) or 0) or None
        a_ = act_.get(k_)
        job_ = rs._seat.sys_for(rs._seat.SYSTEM, k_)
        layers_ = [rs._studio_layer('job', 'Seat prompt', job_),
                   rs._studio_layer('identity', 'Identity', rs._air.identity_line(rs.os.environ, k_), 'chat only'),
                   *([rs._studio_layer('brain', 'Coin reads (brain)', brain_, 'background reads')] if brain_ else []),
                   rs._studio_layer('studio', 'Applied mindset', rs._pstu.overlay_block(a_['text']).strip() if a_ else '', None if a_ else 'none applied')]
        rec_ = rs._pstu.recent(trades_)
        last_ = next((x_ for x_ in reversed(raw_.get('autoLog') or []) if x_.get('key') == k_), None)
        models_.append({'key': k_, 'name': nm_, 'state': live_.get(k_), 'model': lm_.get('model') or (rs._air.provider(rs.os.environ, k_, rs._ai_cfg()) or {}).get('model'), 'ctx': ctx_,
                        'record': s_, 'fixes': fx_, 'sets': core_['sets'], 'layers': layers_,
                        'active': {**a_, 'since': rs._pstu.since(trades_, a_['at']),
                                   'seen': (lambda sn_: sn_ if sn_ and sn_.get('set') == a_['set'] and rs._fuse._f(sn_.get('at')) >= rs._fuse._f(a_['at']) - 1 else None)(rs._air.MINDSET_SEEN.get(k_))} if a_ else None,   # 🎭 proof: the last call that CARRIED it
                        'auto': {'on': rs._pstu.auto_on(raw_, k_), 'red': rs._pstu.is_red(rec_), 'recent': {x_: rec_.get(x_) for x_ in ('n', 'wonPct', 'avgPct')},
                                 'word': rs._pstu.red_word(rec_), 'last': last_, 'coolUntil': (rs._fuse._f(a_['at']) + rs._pstu.AUTO_COOLDOWN) if a_ and now_ - rs._fuse._f(a_['at']) < rs._pstu.AUTO_COOLDOWN else None,
                                 'n': rs._pstu.RECENT_N, 'won': rs._pstu.RED_WON},
                        'ladder': rs._pstu.ladder(trades_, raw_.get('history'), k_, now_, a_),
                        'lms': rs._studio_lms_note.get(k_)})   # 📌 the LM Studio preset that mirrors it (OSSY, this Mac)
    fee_ = await rs._studio_fee()
    return {'models': models_ + ([fee_] if fee_ else []), 'dials': list(rs._pstu.DIAL_KEYS), 'at': rs.time.time()}


async def _studio_fee(body=None):
    """🐱 FEE's own brains in Prompt Studio (feecat_service.studio_view): read, or apply / revert with body. None = the Fee service is down."""
    rs = _rs()
    try:
        u_, h_ = 'http://127.0.0.1:5088/api/cats/internal/studio', {'x-feeless-internal': rs._internal_key()}
        r_ = await (rs._ai_http().post(u_, headers=h_, json=body, timeout=8) if body is not None else rs._ai_http().get(u_, headers=h_, timeout=6))
        if body is not None and r_.status_code != 200:
            raise rs.HTTPException(r_.status_code, (r_.json() or {}).get('detail') or 'Fee service rejected the change.')
        return r_.json() if r_.status_code == 200 else None
    except rs.HTTPException:
        raise
    except Exception:   # down / a closed loop: the studio still shows G4 + OSSY
        if body is not None:
            raise rs.HTTPException(503, 'Fee service did not answer.')
        return None


async def _colony_value(addr):
    """🐝 The pot's live value: SOL + USDC + FEECAT on its wallet (balance × live price). None when the chain can't be read."""
    rs = _rs()
    try:
        sol_, usdc_, fc_, px_ = await rs.asyncio.gather(rs.token_balance(addr, rs.WSOL), rs.token_balance(addr, rs.USDC_MINT),
                                                     rs._holding_usd(addr, rs.ecosystem_mints()['feecat']), rs._sol_usd())
    except Exception:
        return None
    parts = {'sol': round(float(sol_.get('amount') or 0), 6), 'usdc': round(float(usdc_.get('amount') or 0), 2), 'feecatUsd': round(float(fc_ or 0), 2)}
    return {**parts, 'usd': round(parts['sol'] * float(px_ or 0) + parts['usdc'] + parts['feecatUsd'], 2)}


async def _colony_view():
    rs = _rs()
    import colony as _col
    d = rs._json_load(rs.COLONY_PATH, {})
    try:
        r_ = await rs._ai_http().get('http://127.0.0.1:5088/api/cats/internal/colony', headers={'x-feeless-internal': rs._internal_key()}, timeout=8)
        live = r_.json() if r_.status_code == 200 else {}
    except Exception:
        live = {}
    w = d.get('wallet') or {}
    val = await rs._colony_value(w['address']) if w.get('address') else None
    policy = _col.clean_policy(d.get('policy')); principal = float(d.get('principalUsd') or 0)
    pay = _col.payable((val or {}).get('usd'), principal, policy) if val else 0.0
    return {'wallet': {k: w.get(k) for k in ('address', 'at')} if w else None, 'value': val, 'principalUsd': round(principal, 2),
            'growthUsd': _col.growth((val or {}).get('usd'), principal) if val else 0.0, 'payableUsd': pay, 'policy': policy,
            'bounds': _col.POLICY_BOUNDS, 'guards': list(_col.FIXED_GUARDS),
            'sharers': len(live.get('sharers') or []),
            'sharedSol': round(sum(float(x.get('sol') or 0) for x in live.get('shares') or []), 6), 'pool': d.get('pool'), 'poolTokens': rs._pool_tokens(), 'poolDraft': d.get('poolDraft'), 'board': (live.get('board') or [])[:10],
            'colonized': live.get('colonized', 0), 'trades': live.get('trades', 0), 'epoch': live.get('epoch'), 'left': live.get('left'),
            'browsers': live.get('browsers') or [], 'log': (d.get('log') or [])[-8:]}


def _pool_tokens():
    """What the Pool can open a pool with. No token is required: the owner picks the pair (owner 2026-11-05: "we not paying in feecat")."""
    rs = _rs()
    m = rs.ecosystem_mints()
    return [{'k': 'SOL', 'mint': rs.POOL_QUOTES['SOL'][0]}, {'k': 'USDC', 'mint': rs.POOL_QUOTES['USDC'][0]}, {'k': 'FEE', 'mint': m.get('fee')}, {'k': 'FEECAT', 'mint': m.get('feecat')}]


async def _colony_pool_build(d, body):
    """🌊 Meteora DAMM v2 for any pair the owner picks, with the colony wallet as payer (circle/colony-pool.mjs, Meteora's own SDK): the transaction + a FREE
    on-chain simulation. Nothing is signed by the colony wallet here, nothing is sent."""
    rs = _rs()
    w = d.get('wallet') or {}
    if not w.get('address'):
        raise rs.HTTPException(400, 'Create the pot wallet first.')
    try:
        fc, sol = float(body.get('amountA', body.get('feecat'))), float(body.get('amountB', body.get('sol')))
    except (TypeError, ValueError):
        raise rs.HTTPException(400, 'Give both amounts.')
    quote = str(body.get('quote') or 'SOL').upper()   # noqa: F811 (the pool quote coin, not urllib quote)
    if quote not in rs.POOL_QUOTES:
        raise rs.HTTPException(400, 'The second token must be SOL or USDC.')
    mint_b, lo_, hi_ = rs.POOL_QUOTES[quote]
    mint_a = str(body.get('mintA') or rs.ecosystem_mints()['feecat']).strip()
    if not rs._re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', mint_a) or mint_a == mint_b:
        raise rs.HTTPException(400, 'Pick two different tokens.')
    if not (fc > 0 and lo_ <= sol <= hi_):
        raise rs.HTTPException(400, f'The first amount must be above 0, and {quote} between {lo_:g} and {hi_:,}.')
    args = {'payer': w['address'], 'mintA': mint_a, 'mintB': mint_b, 'amountA': fc, 'amountB': sol, 'feeBps': int(body.get('feeBps') or 100),
            'compoundingBps': int(body.get('compoundingBps') or 5000), 'lock': body.get('lock') is True}   # owner 2026-10-31: unlocked by default (the pool is partly disbursed)
    for _ in range(3):   # an RPC out of quota → the next one
        rpc = rs._next_rpc_endpoint()
        proc = await rs.asyncio.create_subprocess_exec(rs.shutil.which('node') or '/opt/homebrew/bin/node', str(rs.COLONY_POOL_JS), cwd=str(rs.COLONY_POOL_JS.parent), stdin=rs.asyncio.subprocess.PIPE, stdout=rs.asyncio.subprocess.PIPE, stderr=rs.asyncio.subprocess.DEVNULL)
        out, _ = await rs.asyncio.wait_for(proc.communicate(rs.json.dumps({**args, 'rpc': rpc}).encode()), 90)
        try:
            r = rs.json.loads(out.decode().strip().splitlines()[-1])
        except Exception:
            r = {'ok': False, 'error': 'the pool builder did not answer'}
        if r.get('ok') or '429' not in str(r.get('error')):
            break
        rs._rpc_cooldown_until[rpc] = rs.time.time() + 60
    return args, r


def _chat_syms():
    """Symbols on the real card + the recent decision tape (what a chat message may name without a $)."""
    rs = _rs()
    try:
        card_ = rs._real_card() or {}
        out = [l.get('symbol') for l in card_.get('legs') or [] if l.get('symbol')]
        out += [r.get('symbol') for r in list(rs._tk.KERNEL.tape.rows)[-200:] if isinstance(r, dict) and r.get('symbol')]
        return list(dict.fromkeys(out))
    except Exception:
        return []


def _chat_coin(text):
    """🪙 The named coin's own record for the chat: the live seat (entry, % now, peak, held, who picked it, your lines), Reaper's word and every
    moment the agents WOULD have sold it (with the % then), the owner's own graded moves on it, and its last closed trades."""
    rs = _rs()
    syms = rs._aic.named_syms(text, rs._chat_syms())[:2]
    if not syms:
        return None
    card_ = rs._real_card() or {}
    pos_ = rs._office_state().get('pos') or {}
    reps_ = {r_.get('mint'): r_ for r_ in (rs._office.get('reports') or []) if isinstance(r_, dict)}
    moves_ = (rs._json_load(rs.OWNER_MOVES_PATH, {}) or {}).get(rs._office.get('tid') or '', {}) or {}
    arch_ = (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions') or []
    out = []
    for sy in syms:
        leg = next((l for l in card_.get('legs') or [] if str(l.get('symbol') or '').upper() == sy and not l.get('placeholder')), None)
        mint = (leg or {}).get('mint') or next((p_.get('mint') for p_ in reversed(arch_) if str(p_.get('symbol') or '').upper() == sy), None)
        p_ = pos_.get(mint) or {}
        r_ = reps_.get(mint) or {}
        row = {'coin': sy, 'mint': mint}
        if leg:
            row['seat'] = {'who': 'yours (your pick)' if leg.get('picked') else 'agents', 'entry': leg.get('entry'), 'pctNow': r_.get('pct'), 'peak': p_.get('peak'),
                           'heldMin': round((rs.time.time() - rs._fuse._f(leg.get('at'))) / 60) if leg.get('at') else None, 'yourStop': leg.get('sl') if leg.get('ownerLvAt') else None,
                           'yourTake': leg.get('tp') if leg.get('ownerLvAt') else None, 'certified': bool(leg.get('certified')), 'reaper': f"{r_.get('state')} · {r_.get('rule')}" if r_ else None}
        wd_ = [f"{w_.get('rule')} at {rs._fuse._f(w_.get('pct')):+.1f}%" for w_ in (p_.get('study') or [])[-6:] if isinstance(w_, dict)]
        if p_.get('would'):
            wd_ = [f"first would-sell: {(p_['would'] or {}).get('rule')} at {rs._fuse._f((p_['would'] or {}).get('pct')):+.1f}%"] + wd_
        if wd_:
            row['agentsWouldHaveSold'] = wd_
        mv_ = [rs._om.why_line(x_) for x_ in (moves_.get('rows') or []) if x_.get('mint') == mint][-5:]
        if mv_:
            row['yourMovesOnIt'] = mv_
        past_ = [{'pct': x_.get('realPct'), 'rule': (x_.get('exit') or {}).get('rule'), 'heldMin': x_.get('heldMin'), 'pick': bool(x_.get('pick'))}
                 for x_ in arch_ if x_.get('mint') == mint and x_.get('realPct') is not None][-3:]
        if past_:
            row['closedBefore'] = past_
        out.append({k: v for k, v in row.items() if v not in (None, [], {})})
    return out or None


def _owner_brief():
    """👤 What the desk learned from the OWNER's own trades (never the agents'): the owner study's graded moves + findings, the owner's seats vs
    the agents' first exit call, the owner's dragged lines vs the agents', and the coins the owner has on the card right now."""
    rs = _rs()
    p_ = rs._office.get('payload') or {}
    st_ = p_.get('ownerStudy') or {}
    lg_ = (rs._json_load(rs.OWNER_MOVES_PATH, {}) or {}).get(rs._office.get('tid') or '', {}) or {}
    card_ = rs._real_card() or {}
    picks_ = [{'coin': l.get('symbol'), 'heldMin': round((rs.time.time() - rs._fuse._f(l.get('at'))) / 60) if l.get('at') else None,
               'yourStop': l.get('sl') if l.get('ownerLvAt') else None, 'yourTake': l.get('tp') if l.get('ownerLvAt') else None}
              for l in card_.get('legs') or [] if l.get('picked') and not l.get('placeholder')]
    out = {'yourMovesGraded': st_.get('kinds') or st_.get('graded'), 'learnedFromYou': (st_.get('findings') or [])[:8],
           'suggestionsForYou': [str(x.get('text') if isinstance(x, dict) else x)[:160] for x in (st_.get('suggestions') or [])[:4]],
           'yourSeatsVsAgents': p_.get('ownerSeats'), 'yourLinesVsAgents': p_.get('ownerHand'), 'yourOpenPicks': picks_ or 'none right now',
           'yourRecentMoves': [rs._om.why_line(r_) for r_ in (lg_.get('rows') or [])[-10:] if not r_.get('engine')],
           'yourStops': rs._om.shakeouts(lg_)}
    return {k: v for k, v in out.items() if v not in (None, [], {})}


def _chat_evidence(question, now):
    """📚 The evidence packet for one chat question (chat_evidence.packet over the archive, the full ledger, the Judge's reviews, the real
    card's events and the live decision tape) — cached 60s per window, run in a worker thread so the chat and the desk never wait on it."""
    rs = _rs()
    w = rs._cev.window(question, now)
    key = (w['label'], int(w['from'] // 60), int(w['to'] // 60))
    hit = rs._cev_cache.get(key)
    if hit and now - hit[0] < 60:
        pk, st = hit[1]
        return {**pk, 'question': str(question)[:300]}, st
    tid = rs._office.get('tid') or 'degen'
    card = (rs._prime_cards().get(tid) or {})
    rows = list(rs._tk.KERNEL.tape.rows)
    pk, st = rs._cev.packet(question, w, (rs._json_load(rs.ARCHIVE_PATH, {}) or {}).get('positions'), rs._fw_full_ledger(), ((rs._office_state().get('judge') or {}).get('reviews')) or [],
                         card.get('events') or [], rows, min((rs._fuse._f(r.get('at')) for r in rows), default=now), tid)
    pk = rs._cev.shrink(pk, rs._air.EVIDENCE_MAX - 200)
    if len(rs._cev_cache) > 20:
        rs._cev_cache.clear()
    rs._cev_cache[key] = (now, (pk, st))
    return pk, st


def _chat_learned():
    """How much the owner has taught the desk through the chat and the Teach box (the lessons every fitting model case reads)."""
    rs = _rs()
    return len((rs._teach_state() or {}).get('items') or [])


def _chat_image(url):
    """🖼 An image the owner attached to the Brain: ONLY a file from our own upload store (never a remote URL), ≤ 4 MB → (url, data URL) — the
    provider gets the bytes, so a localhost link never has to be reachable from the cloud."""
    rs = _rs()
    m_ = rs._CHAT_IMG.match(str(url or ''))
    if not m_:
        return None
    f_ = rs.UPLOAD_DIR / m_.group(1)
    if not f_.is_file() or f_.stat().st_size > 4_000_000:
        return None
    mime_ = {'png': 'image/png', 'jpg': 'image/jpeg', 'webp': 'image/webp', 'gif': 'image/gif'}[m_.group(2)]
    return url, f"data:{mime_};base64,{rs.base64.b64encode(f_.read_bytes()).decode()}"


def _build_state():
    """The build queue as it is ON DISK (parsed once per file version): the next engineering session marks items shipped in the file, and a
    copy kept in memory used to be saved back over that (b7–b10 came back 'queued')."""
    rs = _rs()
    rs._chat['build'] = rs._json_load(rs.BUILD_QUEUE_PATH, {}) or {}
    return rs._chat['build']


def _rpc_quota_notice():
    """🔑 Once a day: every keyed lane is out of quota → the owner's inbox gets one notice that opens the key box in HQ."""
    rs = _rs()
    lanes = rs._rpc_quota_state()
    day = rs.time.strftime('%Y-%m-%d')
    if lanes and not all(x['spent'] for x in lanes) or rs._rpc_warned['day'] == day:
        return False
    rs._rpc_warned['day'] = day
    for w in rs._owner_wallets():
        rs.notify(w, 'fuse-card', '🔑 Every RPC key is out of quota — real swaps are on slower public nodes. Tap to add a key (takes one paste).' if lanes
               else '🔑 No RPC key is set — real swaps are on slower public nodes. Tap to add one (takes one paste).',
               url='/terminal/hq?tab=fuse&rpc=1', push=False, once=f'rpc-key-{day}', meta={'claim': 'RPC key needed', 'source': 'Keeper RPC lanes'})
    return True


async def _agents_loop():
    """🤖 THE 60-SECOND OPERATING LOOP: the agents' pass runs on its OWN clock (AGENTS_EVERY), never behind the warm loop's dozen builders
    (it rode that loop and ran every ~3 minutes). The launch board it reads is refreshed first when it is over ~50s old (one build at a
    time: `_runner_live` shares an in-flight build). No new fetch kind — the same board, the same pass."""
    rs = _rs()
    await rs.asyncio.sleep(25)
    while True:
        try:
            if rs.time.time() - rs._fuse._f(rs._runner_live_cache.get('at')) > rs.AGENTS_EVERY:
                await rs._runner_live()
            await rs._agents_tick(rs.time.time())
            rs._shadow_real_buys(rs.time.time())
            await rs._shadow_settle(rs.time.time())
        except Exception as e:
            print('agents loop:', e)
        await rs.asyncio.sleep(2)


async def _fuse_warm_loop():
    """Fuse runs in the background: every 25s the live runner board, Runner discovery, the Arena stage and the season board
    are rebuilt, so every page load is served from a fresh cache and never waits on scans or prices."""
    rs = _rs()
    await rs.asyncio.sleep(20)
    while True:
        try:
            await rs._fuse_warm()
        except Exception as e:
            print('fuse warm:', e)
        await rs.asyncio.sleep(25)


async def _data_clean(now):
    """🧹 Hourly: slim stale chat token snapshots (the chat file is rewritten on every message, so its size is everyone's lag).
    Runs under the chat lock; writes only when something was freed; the result is kept for HQ and logged."""
    rs = _rs()
    async with rs._chat_lock:
        d = rs._chat_load()
        out, st = rs._dc.slim_chat(d, now)
        if st['messages']:
            rs.CHAT_PATH.write_text(rs.json.dumps(out))
    try:   # 🧹 re-fetchable caches + diagnostic logs only (storage_trim.py): the logo cache had grown to 1.0 GB
        lg_ = await rs.asyncio.to_thread(rs._strim.trim_logos, rs.LOGO_DIR, now)
        lo_ = [] if rs.os.environ.get('PYTEST_CURRENT_TEST') else await rs.asyncio.to_thread(rs._strim.trim_logs)
        bc_ = {} if rs.os.environ.get('PYTEST_CURRENT_TEST') else await rs.asyncio.to_thread(rs._strim.trim_build_cache, rs.Path(__file__).resolve().parent.parent / 'frontend' / 'node_modules' / '.cache' / 'babel-loader', now)
        st = {**st, 'logos': lg_, 'logs': lo_, 'buildCache': bc_}
        if lg_.get('files') or lo_:
            print(f"storage trim: logos −{lg_.get('freed', 0) / 1e6:.0f} MB ({lg_.get('files')} files) · logs {lo_}")
    except Exception as e:
        print('storage trim:', type(e).__name__)
    try:   # 🧹 the scanner's strike list: idle never-blocked wallets out, a blocked wallet keeps 40 strikes (it only ever grew: 16 MB)
        async with rs._block_lock:
            bd_, bst_ = rs._dc.slim_blocklist(rs._block_load(), now, rs.AUTO_BLOCK_STRIKES)
            if bst_['dropped'] or bst_['trimmed']:
                rs._block_flush(bd_)
                print(f"data cleaner: blocklist −{bst_['dropped']} idle wallets, {bst_['trimmed']} trimmed")
        st = {**st, 'blocklist': bst_}
    except Exception as e:
        print('blocklist trim:', type(e).__name__)
    rs._data_clean_last.update(at=now, chat=st)
    if st['messages']:
        print(f"data cleaner: chat −{st['bytes'] / 1e6:.2f} MB ({st['messages']} old messages slimmed)")
    return st


def _intel_save():
    """Write the COMPLETE holder scans (top-10 known) of the last 6h to disk (newest 400), the launch facts, and the scan scheduler's
    freshness book — so a restart knows what was scanned when, and what was failing."""
    rs = _rs()
    try:
        now = rs.time.time()
        rows = sorted(((m, at, out) for m, (at, out) in list(rs._intel_cache.items()) if isinstance(out, dict) and out.get('top10Pct') is not None and now - at < rs.INTEL_DISK_MAX_AGE),
                      key=lambda x: -x[1])[:rs.INTEL_DISK_KEEP]
        key = hash(tuple((m, round(at)) for m, at, _o in rows))
        if key != rs._intel_saved['key']:   # (only when a scan landed since the last write)
            rs._json_save(rs.INTEL_DISK, {'at': now, 'rows': [[m, at, out] for m, at, out in rows]})
            rs._intel_saved['key'] = key
        lf = sorted(rs._launch_facts.items(), key=lambda kv: -rs._fuse._f(kv[1].get('at')))[:rs.LAUNCH_KEEP]
        rs._json_save(rs.LAUNCH_DISK, {'at': now, 'rows': dict(lf)})
        rs._json_save(rs.ENRICH_DISK, rs._ENRICH.snapshot(now))
    except Exception as e:
        print('intel save:', e)


def _intel_restore():
    """At start: the scan results of the last 6h come back WITH THEIR AGE (a coin is never 'unscanned' just because the service
    restarted — an old result is STALE, not gone), and the scheduler gets its freshness book back: what is still fresh is not scanned
    again, what was failing keeps its back-off, and everything else waits its turn in the priority queue. → how many results came back"""
    rs = _rs()
    try:
        for m, v in ((rs._json_load(rs.LAUNCH_DISK, {}) or {}).get('rows') or {}).items():
            rs._launch_facts.setdefault(m, v)
        now, n = rs.time.time(), 0
        for m, at, out in (rs._json_load(rs.INTEL_DISK, {}) or {}).get('rows') or []:
            if isinstance(out, dict) and not out.get('topHolders') and not rs._fuse._f(out.get('top10Pct')):
                continue   # an old 'top-10 0%' with no holders behind it was a failed read, never a clean scan
            if now - rs._fuse._f(at) < rs.INTEL_DISK_MAX_AGE and m not in rs._intel_cache:
                rs._intel_cache[m] = (rs._fuse._f(at), out); n += 1
        got = rs._ENRICH.restore(rs._json_load(rs.ENRICH_DISK, {}) or {}, now, have=set(rs._intel_cache))
        for m, (at, out) in list(rs._intel_cache.items()):   # every complete result in memory is known to the scheduler at its real age
            if isinstance(out, dict) and out.get('top10Pct') is not None:
                rs._ENRICH.note_success(m, at)
        print('enrich freshness restored:', got, 'records ·', n, 'scan results')
        return n
    except Exception as e:
        print('intel restore:', e)
        return 0


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


def _deep_bucket(why):
    """Why a coin got a deep review, as one bucket: first look · not rejected last time · news (a material change) · cooldown over."""
    return 'first look' if why == 'never deep-reviewed' else 'not rejected' if why == 'was not rejected' else 'news' if str(why).startswith('changed') else 'cooldown over'


async def _office_candles(want, now, cats=None):
    """📈 The 1-minute candles behind the chart, ONCE per coin per pass: `want` = {mint: pool}. One request per pool that is not cached
    (the candles service on this machine), in parallel; nothing is fetched twice in a pass and no desk fetches for itself.
    → {mint: rows}. Tests never fetch."""
    rs = _rs()
    t0 = rs.time.perf_counter()
    pools = {}
    rs._office['cmeta'] = {}
    for m, pa in (want or {}).items():
        if m and pa:
            pools.setdefault(pa, m)   # a pool asked for twice (two mints / two desks) is still ONE request
    fresh = {pa for pa in pools if now - (rs._office['candles'].get(pa) or (0, None))[0] <= rs.OFFICE_CANDLE_TTL}
    todo = [pa for pa in pools if pa not in fresh]
    stat = {'req': 0, 'cached': len(fresh), 'merged': len([1 for m, pa in (want or {}).items() if m and pa]) - len(pools), 'coins': len(pools), 'dup': len(todo) - len(set(todo))}   # dup = a pool requested twice in one pass: 0 by construction
    if todo and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        # 👁 THE LIVE CHART, not a snapshot: ONE batched call to the candles service for every coin on the desk — the same chart the war
        # room draws (provider history + FEELESS's live 15s ticks); each pool is marked watched, so its newest candle keeps moving
        try:
            async with rs.httpx.AsyncClient(timeout=6) as http:
                r = await http.post('http://127.0.0.1:5099/api/candles/live', json={'chain': 'solana', 'interval': '1m', 'pairs': {pa: pools[pa] for pa in todo}})
                got = (r.json() or {}).get('charts') or {}
                stat['req'] = 1; stat['live'] = len(got); stat['started'] = (r.json() or {}).get('started')
                for pa, d_ in got.items():
                    rows = list(d_.get('candles') or [])[-rs._ci.LOOK - 5:]   # 🧪 kept EXACTLY as served (Tally validates them as fetched)
                    if rows:
                        rs._office['candles'][pa] = (now, rows, {'provider': d_.get('provider'), 'source': d_.get('source'), 'tickCount': d_.get('tickCount'), 'partial': bool(d_.get('partial')), 'fetchedAt': now, 'liveAt': d_.get('liveAt')})
        except Exception as e:
            print('live charts:', e)
        for pa in [pa for pa, v in rs._office['candles'].items() if now - v[0] > 600]:
            rs._office['candles'].pop(pa, None)
    stat['ms'] = round((rs.time.perf_counter() - t0) * 1000, 1)
    if cats is not None:   # 📈 which kind of coin the real candles went to this pass (fresh 0–12h · old · held) + the first 24 requested (the builds)
        first_ = list((want or {}).keys())[:24]
        stat['allocFirst'] = {k_: sum(1 for m_ in first_ if (cats.get(m_) or 'held') == k_) for k_ in ('fresh', 'old', 'held')}
        stat['loaded'] = {k_: sum(1 for m_, pa_ in (want or {}).items() if (cats.get(m_) or 'held') == k_ and (rs._office['candles'].get(pa_) or (0, None))[1]) for k_ in ('fresh', 'old', 'held')}
    rs._office['candleStat'] = stat
    out = {}
    for m, pa in (want or {}).items():
        hit = rs._office['candles'].get(pa)
        last_t = rs._fuse._f(hit[1][-1][0]) if hit and hit[1] and isinstance(hit[1][-1], (list, tuple)) and hit[1][-1] else 0.0
        if hit and hit[1] and now - last_t <= 300:   # a candle set whose last bar is over 5 min old is stale: the tape stands in
            out[m] = hit[1]
            rs._office['cmeta'][m] = (hit[2] if len(hit) > 2 else None) or {}
    return out


def _mkt_view(mint, pair, now=None):
    """⚡ THE shared market state of one coin, composed from the caches every desk already reads (nothing fetched here): Jupiter's live
    price (`_jup_px_cache`, 20s), the 90s trade tape (`_flow_now`), the newest real candles + the chart built from them (`_office`), and the
    board's pool depth (`_open_pairs`, stamped `_open_meta.at`). → {px, pxAt, pxSrc, liq, liqAt, tapeAt, flow, candleAt, chart}"""
    rs = _rs()
    now = now or rs.time.time()
    jt, jp = rs._jup_px_cache.get(mint, (0, 0))
    bp = (next((p_ for p_ in rs._open_pairs if p_.get('pairAddress') == pair), None) or ((rs._intake.get('pairs') or {}).get(mint) if ((rs._intake.get('pairs') or {}).get(mint) or {}).get('pairAddress') == pair else None)) if pair else None
    ft, fw = rs._flow_now.get(pair, (0, None)) if pair else (0, None)
    hit = rs._office['candles'].get(pair) if pair else None
    last_c = rs._fuse._f(hit[1][-1][0]) if hit and hit[1] and isinstance(hit[1][-1], (list, tuple)) else 0.0
    if jp and jp > 0:
        px, at, src = jp, jt, 'jupiter'
    else:
        px, at, src = rs._fuse._f((bp or {}).get('priceUsd')), (rs._open_meta['at'] if bp else 0), 'board'
    return {'px': px or None, 'pxAt': at or None, 'pxSrc': src if px else None, 'liq': rs._fuse._f(((bp or {}).get('liquidity') or {}).get('usd')) or None, 'liqAt': rs._open_meta['at'] if bp else None,
            'tapeAt': ft or None, 'flow': fw, 'candleAt': (last_c / 1000 if last_c > 1e12 else last_c) or None, 'chart': (rs._office.get('charts') or {}).get(mint)}


def _office_vels(cur, px, now):
    """📈 One REAL valuation read per held seat (the tier tick's price, or the fast guard's fresh Jupiter read) → velocity per mint. Memory
    only: after a restart every seat reads UNKNOWN until it has VEL_MIN_N reads — nothing is guessed."""
    rs = _rs()
    vh = rs._office.setdefault('vel', {})
    out, on = {}, set()
    for l in cur.get('legs') or []:
        m, e = l.get('mint'), rs._fuse._f(l.get('entry'))
        if not m or l.get('placeholder') or rs._fuse._f(l.get('units')) <= 0 or e <= 0:
            continue
        on.add(m)
        p_ = rs._fuse._f((px or {}).get(l.get('pairAddress')) or (px or {}).get(m))
        vh[m] = rs._so.vel_note(vh.get(m), now, (p_ / e - 1) * 100 if p_ > 0 else None)
        out[m] = rs._so.velocity(vh[m], now)
    for m in [m for m in vh if m not in on and not (vh[m] and now - rs._fuse._f(vh[m][-1][0]) < 600)]:
        vh.pop(m, None)
    return out


async def _live_px(mints):
    """⚡ The live price the FEELESS charts draw (the candles service's stream price, its shared 5s cache) for many coins in ONE local call."""
    rs = _rs()
    ms = [m for m in dict.fromkeys(mints or []) if m][:60]
    if not ms or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return {}
    try:
        async with rs.httpx.AsyncClient(timeout=rs.LIVE_PX_SEC if len(ms) <= 12 else rs.LIVE_PX_BULK_SEC) as http:
            r = await http.get('http://127.0.0.1:5099/api/candles/prices', params={'mints': ','.join(ms)})
            return {m: rs._fuse._f(v) for m, v in (r.json() or {}).items() if rs._fuse._f(v) > 0}
    except Exception:
        return {}


def _wake_note(kind, sym, why, now):
    rs = _rs()
    rs._wake['log'] = (list(rs._wake['log']) + [{'at': now, 'kind': kind, 'sym': sym, 'why': '; '.join(why[:2])}])[-20:]


async def _market_wake(agents_c, now):
    """⚡ MARKET-EVENT WAKEUPS between office passes: the live chart price for the agents' seats and their waiting candidates → a material
    change wakes Reaper (tier tick on freshly refreshed live candles) or Trigger (an early agents' pass). → True when the tier tick should run now."""
    rs = _rs()
    pos_ = rs._office.get('pos') or {}
    legs_ = [l for c in agents_c for l in c.get('legs') or [] if l.get('mint') in pos_ and not l.get('placeholder')]
    cand_ = rs._office.get('watchC') or {}
    lp = await rs._live_px([l['mint'] for l in legs_] + list(cand_))
    if not lp:
        return False
    try:   # ⚙ every live price is an EVENT for the kernel: the held coin / candidate is re-judged at once (measured: market move → Reaper decision)
        kctx_ = None
        for m_, px_ in lp.items():
            if m_ in rs._tk.KERNEL.store.mints:
                kctx_ = kctx_ or rs._kernel_ctx(rs.time.time())
                d_px_ = rs._tk.KERNEL.price_event(m_, px_, rs.time.time(), kctx_)
                rs._tke.HUB.publish('mint_update', m_, {'mint': m_, 'price': px_, 'priceAt': round(rs.time.time(), 2), 'status': (d_px_ or {}).get('status'), 'reaper': ((d_px_ or {}).get('opinions') or {}).get('reaper')}, rs.time.time())   # 📡 a live price → the page, now
    except Exception as e:
        print('kernel price event:', str(e)[:100])
    tick = False
    for l in legs_:
        m = l['mint']
        why = rs._mw.position_wake(pos_[m], lp.get(m))
        if why and rs._mw.due(rs._wake['pos'].get(m), now, rs._mw.GAP_POS):
            rs._wake['pos'][m] = now; rs._wake['n'] += 1; tick = True
            rs._jup_px_cache[m] = (now, lp[m])   # the tick decides on THIS price (the shared 20s cache could be a candle old)
            pa = l.get('pairAddress')
            if pa and rs._office['candles'].get(pa):   # … and on a re-read live chart (the refresh skips anything younger than its TTL)
                rs._office['candles'][pa] = (0.0,) + tuple(rs._office['candles'][pa][1:])
            rs._wake_note('reaper', l.get('symbol'), why, now)
    hit = [(m, rs._mw.candidate_wake(c, lp.get(m))) for m, c in cand_.items()]
    hit = [(m, w) for m, w in hit if w]
    if hit and rs._mw.due(rs._wake['candAt'], now, rs._mw.GAP_CAND) and now - rs._fuse._f(rs._agents.get('at')) >= rs._mw.GAP_CAND:
        rs._wake['candAt'] = now; rs._wake['candN'] += 1
        rs._agents['wake'] = now   # the agents' loop runs its next pass now (≤ 2s), not at the 55s mark
        for m, w in hit[:3]:
            rs._wake_note('trigger', (cand_.get(m) or {}).get('sym'), w, now)
    return tick


async def _office_candle_refresh(want, now):
    """⚡ Between agent passes: re-read the candles of the coins a decision is about to stand on (held coins + this tick's candidates)
    whose read is older than OFFICE_CANDLE_TTL — the SAME cache, one request per pool, ≤ OFFICE_REFRESH_MAX — and rebuild their shared
    chart; the case row in the agents' table gets the new chart too (a new 1-minute candle never waits for the coin's rediscovery)."""
    rs = _rs()
    stale = {m: pa for m, pa in (want or {}).items() if m and pa and now - (rs._office['candles'].get(pa) or (0, None))[0] > rs.OFFICE_CANDLE_TTL}
    todo = dict(list(stale.items())[:rs.OFFICE_REFRESH_MAX])
    if not todo or rs.os.environ.get('PYTEST_CURRENT_TEST'):
        return 0
    try:   # 👁 the LIVE chart for every coin a decision stands on: one batched local call (provider history + live 15s ticks)
        async with rs.httpx.AsyncClient(timeout=4) as http:
            live_ = ((await http.post('http://127.0.0.1:5099/api/candles/live', json={'chain': 'solana', 'interval': '1m', 'pairs': {pa: m for m, pa in todo.items()}})).json() or {}).get('charts') or {}
    except Exception:
        live_ = {}
    got = [(pa, list((live_.get(pa) or {}).get('candles') or [])[-rs._ci.LOOK - 5:], {k_: (live_.get(pa) or {}).get(k_) for k_ in ('provider', 'source', 'tickCount', 'liveAt')} | {'partial': bool((live_.get(pa) or {}).get('partial')), 'fetchedAt': now}) for pa in todo.values()]
    rs._office['load']['candleRefresh'] = int(rs._office['load'].get('candleRefresh') or 0) + len(todo)
    by = {x_.get('mint'): x_ for x_ in rs._agents.get('table') or []}
    n = 0
    for (pa, rows, meta_), m in zip(got, todo):
        if not rows:
            continue
        rs._office['candles'][pa] = (now, rows, meta_)
        x_ = by.get(m) or {}
        nm, vt = x_.get('nums') or {}, x_.get('vitals') or {}
        bp_ = next((p_ for p_ in rs._open_pairs if p_.get('pairAddress') == pa), None) or {}
        meta = {**(meta_ or {}), 'vol5m': ((bp_.get('volume') or {}).get('m5')), 'vol1h': vt.get('vol1h'), 'txns1h': vt.get('txns1h'), 'buy': nm.get('buy'), 'liqAge': 0.0, 'ageMin': None if vt.get('ageH') is None else rs._fuse._f(vt['ageH']) * 60}
        ch = rs._ci.read(rows, now, True, 'candles', meta, buy=nm.get('buy'), liq=nm.get('liq') or None, liq_d=nm.get('liqD'), flow=(rs._flow_now.get(pa) or (0, None))[1])
        rs._office['charts'][m] = ch
        if x_:
            x_['chart'] = rs._ci.compact(ch); x_['chartAt'] = now
        n += 1
    return n


def _intake_reg():
    rs = _rs()
    if rs._intake['reg'] is None:
        rs._intake['reg'] = dict((rs._json_load(rs.INTAKE_PATH, {}) or {}).get('reg') or {})
    return rs._intake['reg']


async def _intake_dex(mints, now):
    """📡 {mint: deepest DexScreener pair} for coins Jupiter's token read did not answer (30 a call, in parallel, cached 45s)."""
    rs = _rs()
    out, need = {}, []
    for m_ in dict.fromkeys(mints):
        hit = rs._intake_ds.get(m_)
        if hit and now - hit[0] < 45:
            if hit[1]:
                out[m_] = hit[1]
        else:
            need.append(m_)
    if need:
        async with rs.httpx.AsyncClient(timeout=8) as http:
            async def one(chunk):
                try:
                    r = await http.get('https://api.dexscreener.com/tokens/v1/solana/' + ','.join(chunk))
                    return r.json() if r.status_code == 200 else []
                except Exception:
                    return []
            rows = [p for got in await rs.asyncio.gather(*[one(need[i:i + 30]) for i in range(0, len(need), 30)]) if isinstance(got, list) for p in got]
        best = rs._in.deepest_pairs(rows, need)
        for m_ in need:
            rs._intake_ds[m_] = (now, best.get(m_))
        out.update(best)
        for m_ in [k for k, v in rs._intake_ds.items() if now - v[0] > 300]:
            rs._intake_ds.pop(m_, None)
    return out


async def _intake_pass(ob, now, owner=()):
    """🕸 Every existing outlet → the registry; rows for the coins the board does not carry → (extra rows, fresh {mint: [pulse|migr]},
    outlets {mint: [calls|feeders|radar|runner]}). One local read of the Pump pulse (PumpPortal live stream, already running) and ONE
    batched Jupiter token read for the missing rows — no new crawler, no RPC."""
    rs = _rs()
    born = lambda r: (now - rs._fuse._f(r['ageH']) * 3600) if r.get('ageH') is not None else None
    seen = {'open': [{'mint': r['mint'], 'symbol': r.get('symbol'), 'born': born(r), 'pad': 'pump' if str(r['mint']).endswith('pump') else 'bonk' if str(r['mint']).endswith('bonk') else None} for r in ob if r.get('mint')]}
    pl = {}
    if not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        try:
            async with rs.httpx.AsyncClient(timeout=3) as http:
                pl = (await http.get('http://127.0.0.1:5001/api/pump/pulse', params={'limit': 100})).json() or {}
        except Exception:
            pl = {}
    seen['pulse'] = [{'mint': l['mint'], 'symbol': l.get('symbol'), 'born': rs._fuse._f(l.get('at')) / 1000 or None, 'pad': 'pump'} for l in pl.get('launches') or [] if l.get('mint')]
    seen['migr'] = [{'mint': m_.get('mint'), 'symbol': m_.get('symbol'), 'pad': 'pump'} for m_ in pl.get('migrations') or [] if m_.get('mint')]
    seen['runner'] = [{'mint': r.get('mint'), 'symbol': r.get('symbol')} for r in rs._runner_cands if r.get('mint')]
    for k_, rows_ in (rs._lens_rows or {}).items():
        seen[f'list:{k_}'] = [{'mint': r.get('mint'), 'symbol': r.get('symbol')} for r in rows_ or [] if r.get('mint')]
    seen['calls'] = [{'mint': c.get('mint'), 'symbol': c.get('symbol')} for c in (rs._pump_calls.get('calls') or []) + ((rs._pump_calls.get('board') or {}).get('coins') or []) if c.get('mint')]
    fb = rs._feeders.get('board') or {}
    seen['feeders'] = [{'mint': m_} for m_ in list((fb.get('runners') or {}).keys()) + list((fb.get('kids') or {}).keys()) if m_]
    p2m = {p.get('pairAddress'): (p.get('baseToken') or {}).get('address') for p in rs._open_pairs}
    seen['radar'] = [{'mint': p2m[pa], 'symbol': sy} for pa, sy in (rs._radar.get('pairs') or {}).items() if p2m.get(pa)]
    seen['held'] = [{'mint': l.get('mint'), 'symbol': l.get('symbol')} for l in rs._prime_cards().get(rs._office.get('tid') or '', {}).get('legs') or [] if l.get('mint') and not l.get('placeholder')]
    reg, new_by, new_all = rs._in.note(rs._intake_reg(), seen, now)
    rs._intake['reg'] = reg
    have = {r['mint'] for r in ob if r.get('mint')}
    fresh, outlets = {}, {}
    for s_ in ('pulse', 'migr'):
        for x in seen[s_]:
            fresh.setdefault(x['mint'], []).append(s_)
    for s_ in ('calls', 'feeders', 'radar', 'runner'):
        for x in seen[s_]:
            outlets.setdefault(x['mint'], []).append(s_)
    want = [m_ for m_ in dict.fromkeys(owner or ()) if m_ not in have] + [m_ for m_ in list(dict.fromkeys(list(fresh) + list(outlets))) if m_ not in have and m_ not in (owner or ())][:rs.INTAKE_JUP]   # 👤 the owner's review coins first (never cut)
    extra = []
    if want and not rs.os.environ.get('PYTEST_CURRENT_TEST'):
        miss = [m_ for m_ in want if not (rs._jup_tok_cache.get(m_) and now - rs._fuse._f(rs._jup_tok_cache[m_][0]) < 60)]
        rs._office['load']['jupTokens'] = int(rs._office['load'].get('jupTokens') or 0) + (len(miss) + 99) // 100
        try:
            toks = await rs._jup_tokens(want)
        except Exception:
            toks = {}
        rcfg = rs._runner_cfg()
        for m_, t_ in (toks or {}).items():
            pr = rs._launchpad_board.jup_pair(t_)
            r = rs._trench.open_row(pr, now * 1000) if pr else None
            if not r:
                continue
            r['curve'] = not t_.get('graduatedPool') and (pr.get('dexId') == 'pumpfun' or t_.get('bondingCurve') is not None)   # still on its launch curve
            sc = rs._open_scan_judge(pr, m_, rcfg) or rs._jup_judge(pr, m_, rs._ja.facts(t_), rcfg)   # 🧪 Jupiter's audit stands in until our own scan lands
            r.update({'front': rs._trench.front_score(r), 'safe': None if not sc else bool(sc[0]), 'fails': ['not scanned yet — holders unknown'] if not sc else list(sc[1] or []),
                      'soft': True, 'open': True, 'outlet': True, **({k_: v_ for k_, v_ in (sc[2] or {}).items() if v_ is not None} if sc and len(sc) > 2 else {})})
            extra.append(r)
            if not any((p.get('baseToken') or {}).get('address') == m_ for p in rs._open_pairs[-400:]):
                rs._intake.setdefault('pairs', {})[m_] = pr   # the pair a fill / candle / live check needs (memory only)
        # 📡 Jupiter's read lane at its limit (429) must never starve the desk: the coins it did not answer → DexScreener (own quota)
        got_ = {r['mint'] for r in extra}
        try:
            dex_ = await rs._intake_dex([m_ for m_ in want if m_ not in got_], now)
        except Exception:
            dex_ = {}
        for m_, pr in dex_.items():
            r = rs._trench.open_row(pr, now * 1000)
            if not r:
                continue
            r['curve'] = pr.get('dexId') == 'pumpfun'
            sc = rs._open_scan_judge(pr, m_, rcfg)
            r.update({'front': rs._trench.front_score(r), 'safe': None if not sc else bool(sc[0]), 'fails': ['not scanned yet — holders unknown'] if not sc else list(sc[1] or []),
                      'soft': True, 'open': True, 'outlet': True, 'via': 'dex', **({k_: v_ for k_, v_ in (sc[2] or {}).items() if v_ is not None} if sc and len(sc) > 2 else {})})
            extra.append(r)
            if not any((p.get('baseToken') or {}).get('address') == m_ for p in rs._open_pairs[-400:]):
                rs._intake.setdefault('pairs', {})[m_] = pr
    rs._intake['last'] = {'at': now, 'newBy': {k_: len(v_) for k_, v_ in new_by.items()}, 'new': len(new_all), 'newMints': new_all[:40], 'want': len(want), 'rows': len(extra),
                       'rowsDex': sum(1 for r in extra if r.get('via') == 'dex'),
                       'pending': len(want) - len(extra), 'pulseStatus': pl.get('status'), 'pulsePerMin': (pl.get('launchesPerMinute') or [None])[-2] if pl.get('launchesPerMinute') else None,
                       'seen': rs._in.cycle(reg, seen, new_by, new_all, [], [], now)['uniqueSeen']}
    return extra, fresh, outlets


def _intake_after(table, cases, now):
    """The office stamps of this pass (agent intake · deep review · cleared) + the cycle's turnover, then the registry is saved."""
    rs = _rs()
    reg = rs._intake_reg()
    tm = [x_.get('mint') for x_ in table if x_.get('mint')]
    reg = rs._in.stamp(reg, 'intake', tm, now)
    reg = rs._in.stamp(reg, 'deep', rs._office.get('deepNow') or [], now)
    reg = rs._in.stamp(reg, 'clear', [c_['mint'] for c_ in cases if c_.get('cleared')], now)
    rs._intake['reg'] = reg
    last = rs._intake.get('last') or {}
    cy = rs._in.cycle(reg, {}, {k_: [None] * v_ for k_, v_ in (last.get('newBy') or {}).items()}, last.get('newMints') or [], tm, rs._intake.get('prev') or [], now)
    rs._intake['prev'] = tm
    rs._intake['cycle'] = {**cy, 'uniqueSeen': last.get('seen'), 'newUnique': last.get('new'), 'newBy': last.get('newBy') or {}}
    if now - rs._fuse._f(rs._intake.get('saveAt')) >= 50:
        rs._intake['saveAt'] = now
        rs._json_save(rs.INTAKE_PATH, {'reg': reg})
    return rs._intake['cycle']


def _intake_view(now):
    """🕸 The intake panel: this cycle's turnover, every outlet's funnel (seen → promoted → deep → cleared → bought → won / lost, 6h) and
    the latencies source → intake → deep → clear → seat. Context only — no source is ever a gate."""
    rs = _rs()
    reg = rs._intake_reg()
    return {'cycle': rs._intake.get('cycle'), 'last': {k_: v_ for k_, v_ in (rs._intake.get('last') or {}).items() if k_ != 'newMints'}, 'sources': rs._in.per_source(reg, now),
            'labels': {**rs._in.SOURCES, **{f'list:{k_}': rs._in.label(f'list:{k_}') for k_ in (rs._lens_rows or {})}}, 'latency': rs._in.latency(reg, now), 'registry': len(reg),
            'note': 'every outlet is an existing FEELESS stream; a source\'s record is context — every coin still earns its own decision'}


def _office_seat_payload():
    """🪑 The four-seat model for the page (memory only): every seat this cycle, the ranked bench, the summary line, each held / benched
    coin's score parts, every held seat's switch test, the newest cycle lines and the research packets' last job."""
    rs = _rs()
    return {'seatBoard': rs._agents.get('seatBoard'), 'bench': rs._agents.get('bench'), 'seatSummary': rs._agents.get('seatSummary'), 'seatScores': rs._agents.get('seatScores'),
            'switchTests': [{k_: v_ for k_, v_ in (t_ or {}).items() if k_ in ('mint', 'switch', 'why', 'edge', 'need', 'margin', 'scored', 'current', 'challenger', 'lines', 'mode')} for t_ in rs._agents.get('switchTests') or []],
            'cycleLog': [{k_: v_ for k_, v_ in x_.items() if k_ != 'mints'} for x_ in (rs._office.get('cycleLog') or [])[-12:]], 'research': rs._social.get('last'),
            'intakeView': rs._intake_view(rs.time.time()), 'util': rs._agents.get('util'), 'benchStats': rs._agents.get('benchStats'),
            'scoreNote': 'seat score = hand-set weights over measured parts (read · momentum · structure · liquidity · holders · live data · identity · penalties · velocity · thesis) — it RANKS coins that already passed every gate; it is not a learned or proven edge'}


def _office_cycle_log(table, now):
    """🔁 Append this pass's cycle line (counts from this pass's objects only) → `_office['cycleLog']` (≤ CYCLE_LOG_N, newest last)."""
    rs = _rs()
    cy, it = rs._office.get('cycle') or {}, rs._office.get('intake') or {}
    prev = (rs._office.get('cycleLog') or [None])[-1] or {}
    seen = rs._office.get('seen') or {}
    cases = rs._tk.KERNEL.cases(statuses=('READY', 'CONTENDING'))
    top5 = [c_.get('symbol') for c_ in cases[:5]]
    newin = [x_.get('symbol') for x_ in table if 'new' in (x_.get('intake') or []) and x_.get('ageH') is not None and rs._fuse._f(x_['ageH']) <= 1 and x_.get('mint') not in set(prev.get('mints') or [])]
    reviewed = set(rs._office.get('deepNow') or [])
    dw = rs._office.get('deepWhy') or {}
    repeats = [k_ for k_ in dw if k_ in ('news', 'cooldown over')]   # deep re-reviews of a REJECTED coin: only on news or after the cooldown (never every pass)
    rs._office['passN'] = int(rs._office.get('passN') or 0) + 1
    cooled = sum(1 for e_ in seen.values() if e_.get('reject') and not rs._oe.review_due(e_, now)[0])
    sb, bench_, summ = rs._agents.get('seatBoard') or [], rs._agents.get('bench') or [], rs._agents.get('seatSummary') or {}
    soc = rs._social.get('last') or {}
    line = {'n': rs._office['passN'], 'at': now, 'deepWhy': dw, 'board': it.get('board'), 'cheap': it.get('screened'), 'unique': len({x_.get('mint') for x_ in table}), 'newLaunches': it.get('newLaunches'),
            'newEntering': newin[:6], 'deep': len(reviewed), 'deepCoins': [((next((x_ for x_ in table if x_.get('mint') == m_), {}) or {}).get('symbol')) for m_ in list(reviewed)[:6]], 'scans': len((rs._office.get('scans') or {}).get('asked') or []) if rs._fuse._f((rs._office.get('scans') or {}).get('at')) >= now - 5 else 0,
            'social': None if not soc or rs._fuse._f(soc.get('at')) < rs._fuse._f(prev.get('at')) else len(soc.get('coins') or []), 'socialCoins': [c_.get('symbol') for c_ in soc.get('coins') or []][:4] if soc and rs._fuse._f(soc.get('at')) >= rs._fuse._f(prev.get('at')) else [],
            'cases': cy.get('cases'), 'cleared': cy.get('cleared'), 'occupancy': summ.get('occupancy'), 'target': summ.get('target'), 'bench': summ.get('bench'), 'benchReady': summ.get('benchReady'),
            'best': None if not bench_ else {'symbol': bench_[0].get('symbol'), 'score': bench_[0].get('score'), 'ready': bench_[0].get('ready'), 'block': bench_[0].get('block')},
            'seats': [{'symbol': x_.get('symbol'), 'result': x_.get('result'), 'vel': x_.get('vel'), 'pct': x_.get('pct')} if not x_.get('empty') else {'empty': True, 'code': x_.get('code'), 'next': (x_.get('next') or {}).get('symbol')} for x_ in sb],
            'top5': top5, 'top5Changed': None if not prev.get('top5') else len(set(top5) - set(prev.get('top5') or [])), 'repeats': sum(dw[k_] for k_ in repeats), 'cooled': cooled,
            'fresh': rs._office_fresh(now), 'buysLeft': summ.get('buysLeft'), 'mints': [x_.get('mint') for x_ in table],
            'intake': {k_: v_ for k_, v_ in (rs._intake.get('cycle') or {}).items()}, 'pulseNew': ((rs._intake.get('last') or {}).get('newBy') or {}).get('pulse'),
            'outletRows': (rs._office.get('intake') or {}).get('outletRows'), 'util': (rs._agents.get('util') or {}).get('all')}
    rs._office['cycleLog'] = (list(rs._office.get('cycleLog') or []) + [line])[-rs.CYCLE_LOG_N:]
    return line


def _office_fresh(now):
    """⏱ The six ages, separately, for the coins decisions stand on (held coins + this tick's live-checked candidates)."""
    rs = _rs()
    tid = rs._office.get('tid')
    legs = [l for l in rs._prime_cards().get(tid or '', {}).get('legs') or [] if l.get('mint') and not l.get('placeholder')]
    cands = [x_ for x_ in (rs._agents.get('table') or [])[:12]]
    hv = [rs._mkt_view(l.get('mint'), l.get('pairAddress'), now) for l in legs]
    views = hv + [rs._mkt_view(x_.get('mint'), x_.get('pair'), now) for x_ in cands]
    f = rs._oe.freshness(now, [v_['pxAt'] for v_ in views], [v_['tapeAt'] for v_ in (hv or views)], [v_['candleAt'] for v_ in views], rs._open_meta.get('at'), rs._agents.get('passAt'), rs._office.get('tickAt'))
    # the OLDEST held-seat input (the number a decision must not stand on if it is stale), alongside the newest of anything
    old_ = lambda ts: None if not [t for t in ts if t] else round(max(0.0, now - min(rs._fuse._f(t) for t in ts if t)), 1)
    f['held'] = {'price': old_([v_['pxAt'] for v_ in hv]), 'tape': old_([v_['tapeAt'] for v_ in hv]), 'candle': old_([v_['candleAt'] for v_ in hv]), 'n': len(hv)} if hv else None
    return f


def _office_load_pass():
    """Expensive calls since the last agent pass (deltas of process counters): candle reads, holder scans asked, Jupiter price requests,
    browser research fetches."""
    rs = _rs()
    cur = {'candles': int(rs._office['candleStat'].get('req') or 0) + int(rs._office['load'].get('candleRefresh') or 0), 'scans': int(rs._office['load'].get('scansAsked') or 0),
           'jupiter': rs._jup_calls['n'], 'browser': int(rs._office['load'].get('browser') or 0), 'scanWakes': int(rs._office['load'].get('scanWakes') or 0)}
    tot = rs._office.setdefault('loadTot', {'candles': 0})
    tot['candles'] = int(tot.get('candles') or 0) + int(rs._office['candleStat'].get('req') or 0)
    cur['candles'] = tot['candles'] + int(rs._office['load'].get('candleRefresh') or 0)
    prev = rs._office.get('loadPrev') or {k: 0 for k in cur}
    rs._office['loadPrev'] = cur
    return {k: cur[k] - int(prev.get(k) or 0) for k in cur}


def _social_cache():
    rs = _rs()
    if rs._social['cache'] is None:
        d_ = rs._json_load(rs.SOCIAL_PATH, {}) or {}
        rs._social['cache'] = dict(d_.get('packets') or {}) if d_.get('v') == rs.SOCIAL_V else {}   # an older parser's packets are re-read, never trusted
    return rs._social['cache']


def _social_flush(now=None):
    rs = _rs()
    if not rs._social.get('dirty') or rs._social.get('cache') is None:
        return
    rs._json_save(rs.SOCIAL_PATH, {'v': rs.SOCIAL_V, 'packets': rs._social['cache']}); rs._social['dirty'] = False; rs._social['savedAt'] = rs.time.time() if now is None else now


async def _research_tick(cases, rows_by, now):
    """🔎 ONE research job at a time, after the agent pass: the strongest due candidates (social_research.pick, ≤ PER_PASS) are read
    through local headless Chromium — their own website / X first, one search only when they carry no link. Never blocks the desks."""
    rs = _rs()
    if rs._social['busy'] or rs.os.environ.get('PYTEST_CURRENT_TEST') or not rs._sr.chrome_path():
        return 0
    rs._social['busy'] = True
    n = 0
    try:
        rs._office['load']['orphansKilled'] = int(rs._office['load'].get('orphansKilled') or 0) + await rs.asyncio.to_thread(rs._sr.reap_orphans)   # (off the event loop: its ps call stalled every request up to 5s — Lag catcher 2026-10-30) a browser left by a restart mid-fetch never keeps running
        cache = rs._social_cache()
        done_ = []
        picks_ = rs._sr.pick(cases, cache, now)
        try:   # 🔗 the creator's own links from Pump's coin record FIRST: the desk row often carries none, so coins WITH an X / site were filed "no socials" (2 of 4 checked, 2026-10-13)
            await rs._pump_links_warm([c_['mint'] for c_ in picks_ if str(c_.get('mint') or '').endswith('pump')])
        except Exception:
            pass
        for c_ in picks_:
            row = {**(rows_by.get(c_['mint']) or {}), 'mint': c_['mint'], 'symbol': c_.get('symbol'), 'launch': (c_.get('row') or {}).get('launch')}
            pl_ = (rs._PUMP_LINKS.get(c_['mint']) or (0, {}))[1]
            for k_ in ('site', 'x', 'tg'):
                if not (isinstance(row.get(k_), str) and row[k_].startswith('http')):
                    row[k_] = pl_.get(k_)   # a real link or nothing (the board's True = "set" is not a URL to read)
            try:
                pk, k = await rs._sr.research(row, now=rs.time.time(), cache_search=rs._social['searched'])
            except Exception as e:
                print('research:', e); continue
            n += k
            if pk.get('search') is not None:
                rs._social['searched'][c_['mint']] = now
            cache[c_['mint']] = pk
            done_.append({'symbol': c_.get('symbol'), 'narrative': (pk.get('narrative') or {}).get('class'), 'confidence': (pk.get('cross') or {}).get('confidence'),
                          'conflict': bool((pk.get('cross') or {}).get('conflict')), 'social': pk.get('social'), 'failed': bool(pk.get('failed'))})
        if len(cache) > rs.SOCIAL_KEEP:
            for k_ in sorted(cache, key=lambda k_: rs._fuse._f(cache[k_].get('at')))[:len(cache) - rs.SOCIAL_KEEP]:
                cache.pop(k_, None)
        rs._social['searched'] = {k_: t_ for k_, t_ in rs._social['searched'].items() if now - t_ < rs._sr.TTL['search']}
        rs._office['load']['browser'] = int(rs._office['load'].get('browser') or 0) + n
        rs._office['load']['researched'] = int(rs._office['load'].get('researched') or 0) + 1
        rs._social['last'] = {'at': rs.time.time(), 'requests': n, 'coins': done_}
        rs._social['dirty'] = True
        if now - rs._fuse._f(rs._social.get('savedAt')) >= rs.SOCIAL_SAVE_SEC:   # 💾 ≤ every 2 min (it was every research run)
            rs._social_flush(now)
    finally:
        rs._social['busy'] = False
    return n


def _seat_wake_maybe(now, why=''):
    """🪑 Wake the existing tier tick NOW when Agent Control is on, a seat is open, the office is LIVE, the keeper is healthy, the buy budget
    is not used, and at least one case in the table CLEARS — at most once per SEAT_TARGET_AUTO. No new loop, no new fetch."""
    rs = _rs()
    try:
        rcfg_ = ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {})
        seat_ = rs._agents.get('seat') or {}
        if not (rcfg_.get('agentControl') and seat_.get('empty') and seat_.get('movesLeft') and rs._is_keeper()) or rs.os.environ.get('PYTEST_CURRENT_TEST'):
            return False
        if now - rs._fuse._f(rs._office.get('seatWakeAt')) < rs._oe.SEAT_TARGET_AUTO or (rs._office.get('courier') or {}).get('health') == 'BAD' or rs._oe.policy(rcfg_)['manual'] or not rs._oe.ready(rs._office['boot'], now)['live']:
            return False
        on_ = {x_.get('mint') for x_ in ((rs._agents.get('card') or {}).get('seats') or []) if x_.get('mint')}
        if not rs._tk.KERNEL.ready(n=1, exclude=on_):   # nothing READY in the kernel: no reason to wake a fill
            return False
        rs._office['seatWakeAt'] = now; rs._office['seatWakes'] = int(rs._office.get('seatWakes') or 0) + 1; rs._office['seatWakeWhy'] = why
        rs.asyncio.ensure_future(rs._prime_tick(rs.time.time()))
        return True
    except Exception as e:
        print('seat wake:', e)
        return False


def _office_state():
    """The office's small state, read from disk ONCE per process and kept in memory (the page never causes a read)."""
    rs = _rs()
    if rs._office['state'] is None:
        d = rs._json_load(rs.OFFICE_PATH, {})
        rs._office.update(state=d, pos=dict(d.get('pos') or {}), exiting=list(d.get('exiting') or []), lat={k: list(v) for k, v in (d.get('lat') or {}).items()}, sized=dict(d.get('sized') or {}), theses=dict(d.get('theses') or {}))
    return rs._office['state']


def _office_lat(agent, ms):
    rs = _rs()
    rs._office['lat'][agent] = (list(rs._office['lat'].get(agent) or []) + [round(ms, 3)])[-rs.OFFICE_LAT_N:]


def _office_ledger(n=600):
    """The newest ledger rows (the append-only table, cached by row count — one COUNT per call, no re-read)."""
    rs = _rs()
    try:
        return (rs._fw_full_ledger() or [])[-n:]
    except Exception:
        return []


def _office_real():
    """→ (the real card's id, its wallet book) — read once per agent pass, never per page view."""
    rs = _rs()
    try:
        tid = next((k for k, c in rs._prime_cards().items() if c.get('real')), None)
        return tid, ((rs._fw_load().get('books') or {}).get(tid) or {}) if tid else {}
    except Exception:
        return None, {}


def _office_ctx(cur, t_, now):
    """What the Warden is shown: the card's own money, the candidate's measured numbers, the weather and the courier's health."""
    rs = _rs()
    v, n = t_.get('vitals') or {}, t_.get('nums') or {}
    st = rs._office_state()
    hrs = {int(k): rs._fuse._f(x) for k, x in (st.get('peaks') or {}).items() if now - int(k) * 3600 <= rs._cap.BRAKE_HOURS * 3600}
    money = rs._agents.get('money') or {}
    return {'value': money.get('value'), 'putIn': money.get('putIn'), 'peak': max(hrs.values()) if hrs else None, 'cash': max(0.0, rs._fuse._f(cur.get('cash')) - rs._fuse._f(cur.get('holdCashUsd'))),
            'seats': len(cur.get('legs') or []), 'liq': n.get('liq') or v.get('liq'), 'ageH': v.get('ageH'), 'd5': n.get('d5'), 'top10': v.get('top10'),
            'lastReal': (rs._agents_real().get('last') or [])[-3:], 'weather': rs._agents.get('weather'), 'courier': (rs._office.get('courier') or {}).get('health'),
            'chart': (rs._office.get('charts') or {}).get(t_.get('mint')), 'social': (rs._social_cache() or {}).get(t_.get('mint')), 'near': t_.get('nearReady'), 'tier': t_.get('tier'), 'policy': rs._oe.policy((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}), 'launch': rs._oe.launch_context(t_), 'li': t_.get('li'), 'holderSoft': (t_.get('vitals') or {}).get('holderSoft')}


def _office_warden(cur, t_, requested, cfg_t, now, move):
    """🛡 The Warden sizes ONE existing agent move (a seat fill, or a veto-only look at a switch). A failure here falls back to full
    size — exactly the card's rule as it was — and is printed; it can never return more than `requested`."""
    rs = _rs()
    try:
        t0 = rs.time.perf_counter()
        ctx_ = rs._office_ctx(cur, t_, now)
        ctx_['surv'] = rs._surv.coin(rs._SURV, t_.get('mint'), now)   # ⏱ its own 1 / 5 / 15-min survival → the risk scale
        ctx_['feats'] = rs._FEATS.get(t_.get('mint'))   # 🧪 P1 proven edge: its tags vs the rules that held on unseen coins
        ctx_['edgeRules'] = (rs._json_load(rs.EDGE_AUDIT_PATH, {}) or {}).get('rules') or []
        cap_ = rs._capital_view()
        if cap_.get('on'):   # 💰 size follows the agents' own real record (W23) — this fill's own DOOR once that door has a record, 🧯 the drawdown brake first
            ctx_['capital'] = rs._cap.for_door(cap_, 'armed' if t_.get('armed') else 'ready')
        ctx_['open'] = True   # 🪖 every agent move is a kernel candidate: execution rules as they are, uncertainty only SHRINKS (trench_crew.warden_rules)
        if t_.get('size') is not None:   # the brain's Warden opinion (uncertainty → size) enters the ONE sizing as rule W0
            ctx_.update(kernelSize=t_.get('size'), kernelWhy=t_.get('sizeWhy'))
        if move == 'fill':   # 🪑 multi-seat sizing: how many seats are still open and the free cash they share (W17)
            seats_ = int(rs._fuse._f(rs._oe.policy(cfg_t).get('seats') or cfg_t.get('coins') or 0))
            held_ = len([l for l in cur.get('legs') or [] if not (l.get('placeholder') and not l.get('manualCash'))])
            ctx_.update(openSeats=max(0, seats_ - held_), free=ctx_.get('cash'))
            rs._shadow_cost(now); ctx_.update(rtPct=rs._shadow.get('rt'), feeUsd=rs._shadow.get('feeUsd'))   # 💸 W22: the card's measured round trip
        wd = rs._of.warden(requested, ctx_, rs._office_state(), floor=max(0.05, rs._fuse._f(cfg_t.get('minOrderUsd'))))
        rs._office_lat('warden', (rs.time.perf_counter() - t0) * 1000)
    except Exception as e:
        print('warden:', e)
        return {'veto': False, 'allowed': requested, 'requested': requested, 'eff': 1.0, 'rules': [], 'decided': 'error — the card\'s own size stands'}
    rs._office['warden'] = {**wd, 'sym': t_.get('symbol'), 'mint': t_.get('mint'), 'at': now, 'move': move}
    st = rs._office_state()
    cnt = dict(st.get('count') or {})
    if wd['veto']:
        if now - rs._fuse._f(rs._office['vetoAt'].get(t_.get('mint'))) >= 600:   # one line per coin per 10 min — a veto is re-checked every tick
            rs._office['vetoAt'][t_.get('mint')] = now
            cnt['wardenVeto'] = int(cnt.get('wardenVeto') or 0) + 1
            st['wardenLog'] = (list(st.get('wardenLog') or []) + [{'at': now, 'sym': t_.get('symbol'), 'move': move, 'req': wd['requested'], 'allowed': 0, 'rule': wd['decided'], 'why': min(wd['rules'], key=lambda r: r['mult'])['why']}])[-30:]
            cur.setdefault('events', []).append({'at': now, 'kind': 'agent', 'move': 'veto', 'symbol': t_.get('symbol'), 'why': f"🛡 Warden vetoed ${t_.get('symbol')} ({move}): {min(wd['rules'], key=lambda r: r['mult'])['why']}"})
            rs._tk.KERNEL.note('warden', 'VETO', f"{move}: {min(wd['rules'], key=lambda r: r['mult'])['why']}", now, mint=t_.get('mint'), key=f'veto:{int(now // 600)}')
    else:
        rs._office['sized'][t_.get('mint')] = wd['eff']
        ch_ = (rs._office.get('charts') or {}).get(t_.get('mint'))
        if ch_:   # 🧾 the entry thesis is written the moment the move is allowed — what the structure was and what would prove it wrong
            v_, n_ = t_.get('vitals') or {}, t_.get('nums') or {}
            rs._office['theses'][t_.get('mint')] = rs._ci.thesis(ch_, now, {'liq': n_.get('liq') or v_.get('liq'), 'ageH': v_.get('ageH'), 'courier': (rs._office.get('courier') or {}).get('health')},
                                                           rs._of.tune(st, 'reaper', 'stopPct'), rs._of.take_line(cfg_t, rs._agents.get('scalp')),
                                                           germ_stop_on=rs._oe.clean_policy(cfg_t)['agentGermStop'] == 'on')   # 🦠 the germ stop (owner's switch, on by default)
            fv_ = (rs._office.get('flow') or {}).get(t_.get('mint')) or t_.get('fv')
            rs._office['theses'][t_.get('mint')].update(flow={'state': fv_.get('state'), 'buyPct': fv_.get('buyPct'), 'buyers': fv_.get('buyers')} if fv_ else None,
                                                     distHigh=t_.get('distHigh') if t_.get('distHigh') is not None else ((ch_.get('f') or {}).get('distHigh')),
                                                     germ=rs._ci.germ_word((ch_.get('f') or {}).get('germ')), germDist=((ch_.get('f') or {}).get('germ') or {}).get('dist'),
                                                     germEntry=rs._ci.germ_entry({'germ': rs._ci.germ_word((ch_.get('f') or {}).get('germ')), 'germ5': rs._ci.germ_word((ch_.get('f') or {}).get('germ5'))}),   # 🦠 1m + 5m at the buy   # 🦠 the floor at the buy (rule lab learns it)
                                                     pred=rs._agent_pred(t_, ch_, now),   # 🔮 the agents' own prediction for this trade (real-money memory), graded at the exit
                                                     votes=rs._jr.votes_of((rs._tk.KERNEL.dec.get(t_.get('mint')) or {}).get('opinions')))   # 🗳 each entry desk's OWN vote (judge_review.desk_votes scores it on the real result)
        if move == 'fill':
            rs._tk.KERNEL.note('warden', f"SIZE ${rs._fuse._f(wd['allowed']):.2f}", (min(wd['rules'], key=lambda r: r['mult'])['why'] if wd['rules'] else 'no rule bit — full size'), now, mint=t_.get('mint'),
                            result={'usd': round(rs._fuse._f(wd['allowed']), 4), 'requested': round(rs._fuse._f(wd['requested']), 4)}, key=f"sized:{int(now)}")
            cnt['wardenSized'] = int(cnt.get('wardenSized') or 0) + 1
            st['wardenLog'] = (list(st.get('wardenLog') or []) + [{'at': now, 'sym': t_.get('symbol'), 'move': move, 'req': wd['requested'], 'allowed': wd['allowed'], 'rule': wd['decided'], 'why': (min(wd['rules'], key=lambda r: r['mult'])['why'] if wd['rules'] else 'no rule bit — full size')}])[-30:]
    st['count'] = cnt
    return wd


def _office_reap(cur, px, cfg_t, ctl, now, dec, pol=None, live=True, vels=None, margins=None, buys_left=None, edge=None):
    """☠ Reaper looks at the open positions on the real card each tier tick and adds its exit requests to the agents' own decision
    list. Any failure leaves the list exactly as `agents.manage` returned it."""
    rs = _rs()
    try:
        t0 = rs.time.perf_counter()
        rs._office_state()
        tape, rug, press, fv_ = {}, {}, {}, {}
        for l in cur.get('legs') or []:
            at_, w_ = rs._flow_now.get(l.get('pairAddress')) or (0, None)
            if w_ and now - rs._fuse._f(at_) <= 90:
                tape[l.get('pairAddress')] = rs._flow.tape_read(w_)
                fv_[l.get('pairAddress')] = rs._flow.vital(w_)   # 🌊 the buy / sell vital Reaper reads (R4f / R4c, the tighter stop on a red seat)
                if l.get('mint') and fv_[l.get('pairAddress')]:
                    rs._flow_mark(l.get('mint'), fv_[l.get('pairAddress')], l.get('symbol'), now, held=True)
                if ctl and l.get('mint'):   # 🚨 the rug radar on the SAME tape for the agents' seats (creator / top-holder / bundle wallets dumping)
                    it_ = rs._flow_intel(l.get('mint'))
                    why_ = rs._flow.rug_why(w_, it_.get('creator'), it_.get('watch'), rs._fuse._f(l.get('liqNow')) or rs._fuse._f(l.get('liq')) or None)
                    if not why_:   # 🩸 the pool's SOL leaving fast (replay-proven: 3/14 rugs caught ~27s early, 0/10 winners sold)
                        tr_at_, tr_ = rs._flow_trades.get(l.get('pairAddress')) or (0, None)
                        if tr_ and now - rs._fuse._f(tr_at_) <= 60:
                            why_ = rs._flow.pool_drain(tr_, now, rs._fuse._f(l.get('liqNow')) or rs._fuse._f(l.get('liq')))
                    if why_:
                        rug[l.get('pairAddress')] = why_
                    try:   # 🕵 the launch's early buyers selling on the same tape → exit pressure (Reaper R4e / a tighter trail)
                        m_, _c, _e, pl_, cr_ = rs._li_parts(l.get('mint'))
                        press[l.get('pairAddress')] = rs._li.pressure(w_, m_, pl_, cr_)
                    except Exception:
                        pass
        pos, rep, gone = rs._of.reap(cur.get('legs'), rs._agents.get('table'), px, cfg_t, rs._office['pos'], now, rs._agents.get('scalp'), ctl, rs._agents.get('weather'), tape, rs._office_state(), rs._office['sized'], rs._office.get('charts'), rs._office.get('theses'), pol=pol, live=live, real=bool(cur.get('real')),
                                  vels=vels, margins=margins, rug=rug, press=press, flows=fv_, ai_exit=rs._ai_exit_effects(cfg_t, now), ai_words=rs._ai_exit_words(cfg_t, now), plan=rs._consig_plans(now))
        for g in gone:
            g['take'] = rs._of.take_line(cfg_t, rs._agents.get('scalp'))
            if not g.get('askRule'):   # 🧾 WHO removed it: the newest card event naming this coin (agent pull / swap · model sell · your ✂ · engine) — 63 of 67 sales read "left the card by another rule"
                ev_ = next((e_ for e_ in reversed(cur.get('events') or []) if now - rs._fuse._f(e_.get('at')) < 900 and g.get('sym') and (e_.get('symbol') == g.get('sym') or f"${g.get('sym')}" in str(e_.get('why') or ''))), None)
                if ev_:
                    g['askRule'] = f"left: {ev_.get('kind')} · {str(ev_.get('why') or '')[:90]}"
        by_ = {x_.get('mint'): x_ for x_ in rs._agents.get('table') or []}
        for r_ in rep:   # ⏱ DATA FRESHNESS per seat: nothing is called LIVE on stale inputs
            m_, pa_ = r_.get('mint'), r_.get('pair')
            r_['fresh'] = rs._mw.ages(now, (rs._jup_px_cache.get(m_) or (None,))[0], (rs._flow_now.get(pa_) or (None,))[0], (rs._office['candles'].get(pa_) or (None,))[0],
                                   (by_.get(m_) or {}).get('chartAt') or rs._agents.get('passAt'), now)
            r_['phase'] = rs._mw.market_phase((rs._office.get('charts') or {}).get(m_), (by_.get(m_) or {}).get('li'))
        rs._office.update(pos=pos, reports=rep, gone=list(rs._office.get('gone') or []) + gone)
        rs._chart_widen_note(rep, rs.time.time())   # 🪜 a red seat holding higher lows over its floor: noted as a chart WIDEN read and graded like the models' words
        rs._tape_reaper(rep, now)
        rs._office_lat('reaper', (rs.time.perf_counter() - t0) * 1000)
        return rs._of.merge_reaper(dec, rep, buys_left, edge)
    except Exception as e:
        print('reaper:', e)
        return dec


def _office_chart_view(ch, row=None):
    """The chart-intelligence box for one coin: the state, its evidence and contradictions, the four scores, Trigger's entry call,
    Devil's chart objections, the Warden's chart multiplier and the measured features behind them."""
    rs = _rs()
    if not ch:
        return None
    f = ch.get('f') or {}
    keep = ('px', 'r1', 'r5', 'r10', 'r15', 'r30', 'hh', 'hl', 'lh', 'll', 'lastHigh', 'lastLow', 'slope', 'fit', 'distHigh', 'distLow', 'germ', 'germ5', 'fvg', 'fvg5', 'rangePct', 'pos', 'vol', 'atr', 'body', 'wick', 'upWick', 'loWick', 'seq', 'up', 'down',
            'pullback', 'recovery', 'breakTries', 'breakHeld', 'breakFailed', 'supTests', 'resTests', 'squeeze', 'accel', 'decay', 'extPct', 'volTrend', 'buy', 'imbalance', 'trades', 'liq', 'liqD', 'impact', 'support', 'resistance')
    stop, parts = rs._ci.stop_for(f, ch.get('state'), {'liq': f.get('liq'), 'ageH': ((row or {}).get('vitals') or {}).get('ageH'), 'courier': (rs._office.get('courier') or {}).get('health')}, rs._of.tune(rs._office_state(), 'reaper', 'stopPct'))
    return {'state': ch.get('state'), 'src': ch.get('src'), 'n': ch.get('n'), 'conf': ch.get('conf'), 'ev': ch.get('ev'), 'con': ch.get('con'), 'trend': ch.get('trend'), 'chop': ch.get('chop'), 'mom': ch.get('mom'), 'ext': ch.get('ext'),
            'entry': ch.get('entry'), 'objs': ch.get('objs'), 'risk': ch.get('risk'), 'stop': stop, 'stopParts': parts, 'hardStop': rs._ci.CATASTROPHIC_STOP, 'f': {k: f.get(k) for k in keep},
            'q': rs._md.compact(ch.get('q')), 'qChecks': (ch.get('q') or {}).get('checks')}


def _office_bars(pair, mint=None, n=40):
    """The rows the page draws for one coin — the SAME rows the agents read this pass, with Tally's data-quality verdict on them.
    `src` candles = the candles service's 1-minute bars (v = that bar's own volume figure, None where the bar carries none — never a
    made-up bar); `src` tape = Tally's readings as close-only points: RECONSTRUCTED, drawn as a line, no volume at all. Memory only.
    → {src, rows: [[t, o, h, l, c, v|None]], q, volume} | None"""
    rs = _rs()
    q = rs._md.compact(((rs._office.get('charts') or {}).get(mint) or {}).get('q')) if mint else None
    hit = rs._office['candles'].get(pair)
    if hit and hit[1]:
        rows = []
        for r in hit[1][-n:]:
            try:
                rows.append([int(rs._fuse._f(r[0])), r[1], r[2], r[3], r[4], (r[5] if len(r) > 5 and r[5] is not None and rs._fuse._f(r[5]) > 0 else None)])
            except Exception:
                continue   # a row that cannot even be indexed is not drawn (Tally's verdict already says MALFORMED)
        return {'src': 'candles', 'rows': rows, 'q': q, 'volume': (q or {}).get('volume') or ('PARTIAL' if any(r[5] for r in rows) else 'UNAVAILABLE')}
    ser = ((rs._agents_mem.get().get('series') or {}).get(mint) or []) if mint else []
    rows = rs._ci.from_tape(ser)[-n:]
    return {'src': 'tape', 'rows': [[int(r[0]), r[1], r[2], r[3], r[4], None] for r in rows], 'q': q, 'volume': 'UNAVAILABLE'} if len(rows) >= 2 else None


def _office_positions():
    """Reaper's reports as the page gets them: + the position's own % path since entry and the candles behind its chart."""
    rs = _rs()
    out = []
    led_ = None
    for r in rs._office.get('reports') or []:
        p_ = (rs._office.get('pos') or {}).get(r.get('mint')) or {}
        mk_ = ((rs._tk.KERNEL.store.mints.get(r.get('mint')) or {}).get('market')) or {}
        sup_ = mk_.get('supply')
        if led_ is None:
            led_ = rs._office_ledger(400)
        fills_ = [{'at': rs._fuse._f(x_.get('at')), 'side': x_.get('side'), 'px': rs._fuse._f(x_.get('px')) or None, 'usd': round(rs._fuse._f(x_.get('usd')), 4), 'mc': rs._tks.mc(x_.get('px'), sup_)}
                  for x_ in led_ if x_.get('mint') == r.get('mint') and x_.get('side') in ('buy', 'sell') and rs._of.confirmed(x_) and (not rs._office.get('tid') or x_.get('card') == rs._office.get('tid'))][-6:]
        ent_ = rs._fuse._f(r.get('entry'))
        out.append({**r, 'path': list(p_.get('path') or [])[-40:], 'bars': rs._office_bars(r.get('pair'), r.get('mint')),
                    'supply': sup_, 'supplySrc': mk_.get('supplySrc'), 'mc': rs._tks.mc(r.get('px'), sup_), 'entryMc': rs._tks.mc(ent_, sup_),   # 📊 the chart language: price × supply (None = unavailable)
                    'peakMc': rs._tks.mc(ent_ * (1 + rs._fuse._f(r.get('peak')) / 100), sup_) if r.get('peak') is not None else None, 'fills': fills_,
                    'ghosts': [{'at': g_.get('at'), 'pct': g_.get('pct'), 'rule': str(g_.get('rule') or '').split(' ')[0]} for g_ in (p_.get('study') or []) if isinstance(g_, dict) and g_.get('sell')][-6:]})   # ✂ where the agents WOULD have sold (your picks)
    return out


def _hub_publish(now, light=False):
    """📡 Turn the page's payload into DELTAS on the kernel's hub: each kernel candidate, hunter lane set, position, agent card,
    generation book, execution state and metric block is sent only when its content changed. `light` (a tier tick between passes):
    positions, seats and execution only. Memory only — it reads nothing and never raises into its caller."""
    rs = _rs()
    try:
        p = rs._office.get('payload')
        if not p:
            return
        H = rs._tke.HUB
        rs._tape_flush(now)
        H.sync('position_update', {x_['mint']: {k_: v_ for k_, v_ in x_.items() if k_ not in rs._POS_DROP} for x_ in p.get('positions') or [] if x_.get('mint')}, now)
        H.publish('execution_update', 'office', {'courier': {k_: (rs._office.get('courier') or {}).get(k_) for k_ in ('health', 'why', 'pending', 'sends', 'fills', 'failed', 'landMed')},
                                                 'ready': p.get('ready'), 'seat': p.get('seat'), 'ops': p.get('ops'), 'lastAction': (p.get('mission') or {}).get('lastAction'),
                                                 'seatBoard': p.get('seatBoard'), 'seatSummary': p.get('seatSummary'), 'wake': p.get('wake'), 'armed': rs._office.get('armed'), 'regret': p.get('regret'), 'lab': p.get('lab')}, now)
        if light:
            return
        k = p.get('kernel') or {}
        H.sync('candidate_update', {c_['mint']: {k_: v_ for k_, v_ in c_.items() if k_ not in rs._DELTA_DROP} for c_ in k.get('candidates') or []}, now)
        H.publish('hunter_update', 'lanes', k.get('lanes') or [], now)
        H.sync('agent_update', {a_['key']: {k_: a_.get(k_) for k_ in ('key', 'task', 'decision', 'decisionAt', 'rule', 'card')} for a_ in p.get('agents') or []}, now)
        H.publish('lifecycle_update', 'generations', p.get('generations') or [], now)
        H.publish('metric_update', 'metrics', {'kernel': k.get('metrics'), 'enrich': p.get('enrich'), 'rpc': p.get('rpcStats'), 'stream': H.stats()}, now)
        if p.get('ai'):
            H.publish('ai_update', 'ai', p.get('ai'), now)
        H.publish('snapshot', 'office', {'at': p.get('at')}, now, force=True)
    except Exception as e:
        print('hub:', str(e)[:140])


def _net_stats(now=None):
    """📏 SSE streams (active · connects / disconnects / resyncs and their rate a minute) + RPC (logical · physical · 429 a minute, top
    methods, requests per mint) since the service started — for HQ diagnostics and agent_office_view.json. Memory only."""
    rs = _rs()
    now = rs.time.time() if now is None else now
    mins = max(1 / 60, (now - rs._SSE['since']) / 60)
    r = rs._chain.rpc_metrics(now)
    rm = max(1 / 60, rs._fuse._f(r.get('sinceSec')) / 60) if r else mins
    return {'sse': {**{k: v for k, v in rs._SSE.items() if k != 'since'}, 'subscribers': len(rs._tke.HUB.subs), 'connectsPerMin': round(rs._SSE['connects'] / mins, 3), 'minutes': round(mins, 1)},
            'rpc': {'logicalPerMin': round(rs._fuse._f(r.get('logical')) / rm, 1), 'physicalPerMin': round(rs._fuse._f(r.get('physical')) / rm, 1), 'r429PerMin': round(rs._fuse._f(r.get('r429')) / rm, 1),
                    'topMethods': sorted(((k_, v_.get('physical')) for k_, v_ in (r.get('requestsByMethod') or {}).items()), key=lambda kv: -(kv[1] or 0))[:6],
                    'perMint': r.get('requestsPerMint'), 'minutes': round(rm, 1)}, 'prime': dict(rs._prime_stages)}


def _office_light(tid, cur, now):
    """Between agent passes: the last real agent action (with what the LEDGER says about it), the duty clock and Reaper's positions
    are refreshed on the cached payload. Memory only — no read, no quote, no scan."""
    rs = _rs()
    ev = next((e for e in reversed(cur.get('events') or []) if e.get('kind') == 'agent' and e.get('move') in ('fill', 'swap', 'pull', 'veto')), None)
    last = None
    if ev:
        side = 'sell' if ev.get('move') == 'pull' else 'buy'
        res = {'state': 'vetoed'} if ev.get('move') == 'veto' else rs._of.fill_state(rs._office_ledger(), ev.get('mint'), side, rs._fuse._f(ev.get('at')) - 5, tid, symbol=ev.get('symbol'))
        last = {'at': ev.get('at'), 'move': ev.get('move'), 'sym': ev.get('symbol'), 'usd': ev.get('usd'), 'why': str(ev.get('why') or '')[:160], 'result': res}
    rs._office.update(last=last, dutyAt=rs._fuse._f(cur.get('agentDutyAt')), tid=tid)
    p = rs._office.get('payload')
    if p:
        p['positions'] = rs._office_positions()
        p['mission'] = {**p['mission'], 'lastAction': last}
        p['seat'], p['switchEval'], p['ready'] = rs._agents.get('seat'), rs._agents.get('switchEval'), rs._oe.ready(rs._office['boot'], now)
        p['ops'] = rs._oe.ops(p['ready'], p['seat'], rs._office.get('courier'), rs._is_keeper(), rs._uni.FILL_MOVES_HR)
        p['index'] = (rs._office.get('index') or [])[:80]
        p['rpc'] = {'lanes': rs._rpc_quota_state(), 'note': 'keyed lanes = keeper sends / balances first, then holder scans (budgeted); discovery comes from Pump\'s live stream + the launch boards — no RPC first-seen listener runs'}
        p['wake'] = {'reaper': rs._wake['n'], 'trigger': rs._wake['candN'], 'log': list(rs._wake['log'])[-8:], 'watching': len(rs._office.get('watchC') or {})}   # ⚡ market-event wakeups
        p['flowWait'] = rs._office.get('flowWait')   # 🌊 READY coins the live tape held back this tick (sellers lead / top of a spike)
        p['cycle'] = {**(rs._office.get('cycle') or {}), 'nextIn': max(0, round(rs._fuse._f((rs._office.get('cycle') or {}).get('at')) + rs.AGENTS_EVERY - now)) if rs._office.get('cycle') else None}
        p['seatActions'] = rs._oe.seat_actions(((rs._agents.get('card') or {}).get('seats')), rs._agents.get('decisions'), rs._agents.get('switchEval'), rs._agents.get('seat'))
        p.update(rs._office_seat_payload())
        try:
            p['fresh'] = rs._office_fresh(now); p['live'] = rs._office.get('live'); p['scans'] = rs._office.get('scans')
        except Exception as e:
            print('fresh:', e)
        rs._tape_ledger(now)
        p['tape'] = rs._tk.KERNEL.tape.view()
        rs._hub_publish(now, light=True)   # 📡 positions · seats · the last real action → the delta stream (only what changed)


def _office_pass(st, table, now, rcfg, jp, arch, cour, tid, desk_ms):
    """🏢 Once a pass, after the four desks: exits are confirmed against the ledger, the Archivist files the pass's cases + settles the
    open ones, the Judge runs its shadow tests and scores all ten, and ONE payload is built for the page. Pure compute + two saves."""
    rs = _rs()
    of = rs._office_state()
    perf = st.get('perf') or {}
    for a in ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'chart'):
        if perf.get(a) is not None:
            rs._office_lat(a, rs._fuse._f(perf[a]))
    view = rs._agents.get('view') or {}
    bust_seen = {(x_.get('vitals') or {}).get('read') for x_ in table if any(e_[0] == 'busted_read' for e_ in x_.get('ev') or [])} - {None}
    on = {x.get('mint') for x in ((rs._agents.get('card') or {}).get('seats') or []) if x.get('mint')}
    # 📮→☠ exits: a position that left the card is closed only when the ledger confirms the sale
    t0 = rs.time.perf_counter()
    still, closed = rs._of.confirm_exits(rs._office['exiting'], rs._office.get('gone') or [], rs._office_ledger(), now, tid,
                                      used={(p_.get('exit') or {}).get('sig') for p_ in ((arch or {}).get('positions') or [])[-120:] if p_.get('confirmed')} - {None})
    rs._office.update(exiting=still, gone=[])
    if closed:   # 🔁 every confirmed agent exit at a loss → no re-buy for 6h (any rule) · 🧠 every confirmed result → a real-money lesson
        try:
            of['lostAt'] = rs._oe.note_lost(of.get('lostAt'), closed, now)
            rl_ = rs._json_load(rs.REAL_LEARN_PATH, {})
            for p_ in closed:
                rl_ = rs._rl.note_closed(rl_, p_, now)
            rs._json_save(rs.REAL_LEARN_PATH, rl_); rs._rl_cache['at'] = 0.0
        except Exception as e:
            print('lost / learn:', e)
    if closed:   # 👁 every confirmed exit is watched 30 more minutes: what the coin did AFTER we left is what a wider trail would have kept
        rs._after_mem.put(rs._ap.watch(rs._after_mem.get(), [{**p_, 'closedAt': p_.get('closedAt') or now} for p_ in closed], now), now)
    if not of.get('judgeYoursFix'):   # ✋ once: the Judge's old reviews of YOUR trades stop blaming agent desks
        of['judge'] = rs._jr.mark_yours(of.get('judge'), {(p_.get('mint'), round(rs._fuse._f(p_.get('closedAt')))) for p_ in arch.get('positions') or [] if p_.get('pick')})
        of['judgeYoursFix'] = now
    if not of.get('germBackfill1016'):   # 🦠 once: YOUR past trades get their germ-at-entry from the recorded price ticks of the hour before
        of['germBackfill1016'] = now
        try:
            tk_ = rs._json_load(rs.DATA_DIR / 'candle_ticks.json', {}) or {}
            pair_ = {r_.get('mint'): r_.get('pair') for r_ in rs._fw_full_ledger() if r_.get('side') == 'buy' and r_.get('mint') and r_.get('pair')}
            for p_ in arch.get('positions') or []:
                if p_.get('pick') and ((p_.get('snaps') or {}).get('entry') or {}).get('germ') is None and pair_.get(p_.get('mint')) and p_.get('since'):
                    g_ = rs._co.germ_at(tk_.get(f"solana:{pair_[p_['mint']]}"), rs._fuse._f(p_['since']))
                    if g_ is not None:   # kept BESIDE the hash-chained records (editing a filed record would read as a rewrite)
                        arch.setdefault('germFill', {})[f"{p_['mint']}:{round(rs._fuse._f(p_['since']))}"] = g_
        except Exception as e_:
            print('germ backfill:', str(e_)[:100])
    for p_ in closed:
        arch = rs._of.file_position(arch, {**p_, 'closedAt': p_.get('closedAt') or now}, now)
        rs._tk.KERNEL.note('archivist', 'FILED', f"{'confirmed' if p_.get('confirmed') else 'UNCONFIRMED'} exit" + (f" {rs._fuse._f(p_.get('pct')):+.1f}%" if p_.get('pct') is not None else '') + (f" · {p_.get('askRule')}" if p_.get('askRule') else ''),
                        now, mint=p_.get('mint'), result={'pct': p_.get('pct')}, key=f"filed:{p_.get('leftAt') or int(now)}")
        if p_.get('confirmed'):   # 👨‍⚖️ every confirmed exit gets the Judge's review (root cause · desk · severity · change · confidence)
            try:
                of['judge'] = rs._jr.note(of.get('judge'), arch['positions'][-1], now)
                rv_ = (((of.get('judge') or {}).get('reviews')) or [{}])[-1]
                rs._tk.KERNEL.note('judge', 'REVIEW', f"{rv_.get('kind') or 'exit'}: {rv_.get('cause') or '—'}" + (f" → {rv_.get('resp')}" if rv_.get('resp') else ''), now, mint=p_.get('mint'),
                                result={'pct': p_.get('pct')}, key=f"review:{p_.get('leftAt') or int(now)}")
            except Exception as e:
                print('judge review:', e)
        if p_.get('confirmed') and p_.get('mint'):   # 🕸 how this coin's real seat ended → its outlets' win / loss record (context, never a gate)
            rs._intake['reg'] = rs._in.outcome(rs._intake_reg(), p_['mint'], rs._fuse._f(p_.get('realPct') if p_.get('realPct') is not None else p_.get('pct')), now,
                                         (rs._fuse._f(p_.get('closedAt') or now) - rs._fuse._f(p_.get('since'))) / 60 if p_.get('since') else None,
                                         (p_.get('launch') or {}).get('ageH'), (p_.get('li') or {}).get('mcap'))
    if not (of.get('judge') or {}).get('reviews'):   # first run: the Judge reviews the positions already on file (once)
        for p_ in [x for x in (arch.get('positions') or []) if x.get('confirmed')][-40:]:
            of['judge'] = rs._jr.note(of.get('judge'), p_, now)
    rs._office['court'] = rs._jr.court(of.get('judge'), now)
    if closed:   # 🪑 an exit was confirmed: the empty seat looks for its replacement now (the bench), not a pass later
        rs._seat_wake_maybe(now, 'exit confirmed')
    # 🗄 the pass's case files (strongest first) + every real agent action since the last pass
    wx = st.get('weather') or {}
    ctx0 = {'weather': wx, 'courier': cour}
    cases = rs._tk.KERNEL.cases(exclude=on, top=8, statuses=('READY', 'CONTENDING'))   # ⚙ the kernel's own candidates — the Archivist files what the KERNEL decided
    for c_ in cases:
        arch = rs._of.file_case(arch, rs._tkv.lineage(c_, {**ctx0, 'evidence': rs._of.evidence_refs(c_['row'].get('social'))}), now)
    seen = rs._fuse._f(of.get('actionSeen'))
    wd = rs._office.get('warden')
    by_m = {x['mint']: x for x in table}
    for e in [e for e in rs._prime_cards().get(tid or '', {}).get('events') or [] if e.get('kind') == 'agent' and e.get('move') in ('fill', 'swap', 'pull', 'veto') and rs._fuse._f(e.get('at')) > seen]:
        x_ = by_m.get(e.get('mint')) or next((x for x in table if x.get('symbol') == e.get('symbol')), None)
        full = rs._tk.KERNEL.case(x_['mint']) if x_ else None
        d_ = rs._tkv.lineage(full, {**ctx0, 'warden': wd if wd and wd.get('mint') == (x_ or {}).get('mint') else None, 'evidence': rs._of.evidence_refs(full['row'].get('social'))}, e.get('move')) if full else {'mint': e.get('mint'), 'sym': e.get('symbol'), 'action': e.get('move'), 'px': None}
        arch = rs._of.file_case(arch, {**d_, 'usd': e.get('usd'), 'eventAt': e.get('at'), 'why': str(e.get('why') or '')[:140]}, now)
        of['actionSeen'] = max(rs._fuse._f(of.get('actionSeen')), rs._fuse._f(e.get('at')))
    if jp:
        arch = rs._of.settle_cases(arch, lambda m: (jp or {}).get(m), now)
    rs._office_lat('archivist', (rs.time.perf_counter() - t0) * 1000)
    # 👨‍⚖️ shadow tests → promotion / rejection, then every agent's scorecard
    t0 = rs.time.perf_counter()
    ask_ = rs._coach.pop('tuneAsk', None)
    if ask_ and now - rs._fuse._f(ask_.get('at')) < 1800:   # 🧠 the model coach's notch → a shadow candidate (or refused, with the reason on the tape)
        n_full_ = sum(1 for p_ in arch.get('positions') or [] if p_.get('confirmed') and rs._ap.full(p_, (rs._after_mem.get() or {}).get('done')))
        of, no_ = rs._of.model_candidate(of, ask_.get('key'), ask_.get('dir'), n_full_, ask_.get('why'), now)
        rs._tk.KERNEL.note('judge', 'AI TUNE', f"🧠 asks Reaper {ask_.get('key')} {ask_.get('dir')}: {ask_.get('why') or ''} → " + (f'refused ({no_})' if no_ else 'in shadow — the next 20 exits decide'), now, key=f"aitune:{int(now // 600)}")
        rs._coach['tuneSaid'] = {'at': now, **{k_: ask_.get(k_) for k_ in ('key', 'dir', 'why')}, 'refused': no_}
    ha_ = rs._of.hold_ask((rs._study.get('holds') or {}).get('early'))
    if ha_ and now - rs._fuse._f(of.get('holdAskAt')) > 6 * 3600:   # 🎓 your holds: a trail rule that kept selling you early asks for one notch more room (shadow only)
        of['holdAskAt'] = now
        n_full_h = sum(1 for p_ in arch.get('positions') or [] if p_.get('confirmed') and rs._ap.full(p_, (rs._after_mem.get() or {}).get('done')))
        of, no_h = rs._of.model_candidate(of, 'giveBackPct', 'up', n_full_h, f"the owner held past {ha_[0]} {ha_[1]}× and ended ≥ 5 pts higher", now)
        rs._tk.KERNEL.note('judge', 'HOLD TUNE', f"🎓 {ha_[0]} sold the owner early {ha_[1]}× → " + (f'refused ({no_h})' if no_h else 'one notch more give-back in shadow — the next 20 exits decide'), now, key=f"holdtune:{int(now // 3600)}")
    mt_ = rs._seat.models_trail((rs._g4_mem.get() or {}).get('log'), now)
    if mt_ is not None and now - rs._fuse._f(of.get('modelTrailAt')) > 6 * 3600 and abs(mt_ - rs._of.tune(of, 'reaper', 'giveBackPct')) >= 5:   # 🧠 the agents learn their trail from OSSY / G4 (shadow only)
        of['modelTrailAt'] = now
        n_full_m = sum(1 for p_ in arch.get('positions') or [] if p_.get('confirmed') and rs._ap.full(p_, (rs._after_mem.get() or {}).get('done')))
        dir_m = 'up' if mt_ > rs._of.tune(of, 'reaper', 'giveBackPct') else 'down'
        of, no_m = rs._of.model_candidate(of, 'giveBackPct', dir_m, n_full_m, f"OSSY / G4 run their trades on a {mt_:g}% give-back", now)
        rs._tk.KERNEL.note('judge', 'LEARN', f"🧠 the models trail at {mt_:g}% → Reaper giveBackPct {dir_m}: " + (f'refused ({no_m})' if no_m else 'one notch in shadow — the next 20 exits decide'), now, key=f"mtrail:{int(now // 3600)}")
    ps_ = arch.get('positions') or []
    rfp_ = (len(ps_), (ps_[-1].get('h') if ps_ else None), len((rs._after_mem.get() or {}).get('done') or {}), rs.json.dumps(rs._of.tunes(of, 'reaper'), sort_keys=True),
            sum(1 for c_ in (of.get('candidates') or {}).values() if c_.get('status') == 'shadow'))
    if rs._office.get('trailFp') != rfp_ or now - rs._fuse._f(rs._office.get('trailAt')) > 600 or not rs._office.get('trail'):   # ⚡ the replays only when an exit / after-path / tune changed (they cost ~10s a window every pass)
        of = rs._of.judge_candidates(of, arch, rcfg, st.get('scalp'), now, after=(rs._after_mem.get() or {}).get('done') or {})   # 👁 on WHOLE moves: a path ending at our own sale can only favour a tighter trail
        rs._office['trail'] = rs._trail_view(of, arch, rcfg, st.get('scalp'))
        rs._office['trailFp'], rs._office['trailAt'] = rfp_, now
    ser = st.get('series') or {}
    stale = sum(1 for x in table if len(ser.get(x['mint']) or []) >= 2 and rs._fuse._f(ser[x['mint']][-1]['t']) - rs._fuse._f(ser[x['mint']][-2]['t']) > rs._of.STALE_SEC)
    viol = {k: dict(v) for k, v in (of.get('viol') or {}).items()}
    for a_ in ('tally', 'courier', 'archivist', 'reaper'):
        viol.setdefault(a_, {})
    viol['tally']['stale'] = int(viol['tally'].get('stale') or 0) + stale
    viol.setdefault('courier', {})['rule'] = int(cour.get('duplicates') or 0) + int(cour.get('unsigned') or 0)
    viol.setdefault('archivist', {})['rule'] = rs._arch_verify(arch)
    viol.setdefault('reaper', {})['rule'] = sum(1 for p_ in arch.get('positions') or [] if p_.get('confirmed') and not (p_.get('exit') or {}).get('sig'))
    money = rs._agents.get('money') or {}
    if money.get('value') is not None:
        pk = {k: v for k, v in (of.get('peaks') or {}).items() if now - int(k) * 3600 <= 90000}
        pk[str(int(now // 3600))] = max(rs._fuse._f(pk.get(str(int(now // 3600)))), rs._fuse._f(money['value']))
        of['peaks'] = pk
    if wx.get('regime') and (not of.get('weatherLog') or of['weatherLog'][-1]['regime'] != wx['regime']):
        of['weatherLog'] = (list(of.get('weatherLog') or []) + [{'at': now, 'regime': wx['regime'], 'why': (wx.get('why') or [''])[0]}])[-40:]
    rs._office['theses'] = {m: v for m, v in rs._office['theses'].items() if m in rs._office['pos'] or m in on or now - rs._fuse._f(v.get('at')) < 900}
    of.update(viol=viol, lat=rs._office['lat'], pos=rs._office['pos'], exiting=rs._office['exiting'], sized={m: v for m, v in rs._office['sized'].items() if m in rs._office['pos'] or m in on}, theses=rs._office['theses'])
    try:   # 🔎 the winners we missed: an autopsy for every coin the board watched for an hour that ran and that the card did not hold —
        # from files already on disk (the brain's settled watch list, the case files, Tally's tape). Paper only: nothing here can trade.
        arch, new_m = rs._oe.missed_winners(arch, [d_ for d_ in (rs._json_load(rs.BRAIN_PATH, {}).get('done') or [])[-600:] if rs._fuse._f(d_.get('at')) > rs._fuse._f(of.get('missedAt'))], ser, now, on, rs._fuse._f(of.get('missedAt')), st.get('first'))
        of['missedAt'] = now
    except Exception as e:
        print('missed winners:', e)
    try:   # 🧬 ONE lifecycle for all ten roles: real-money evidence only; a failed generation is replaced on this call
        of, lc_ev_ = rs._lc_evaluate(of, arch, cour, now)
        for e_ in lc_ev_:
            line_ = (f"🧬 generation {e_['gen']} replaced by generation {e_['to']} — {e_['why']}. New lesson: {e_['changed']}" if e_['kind'] == 'replaced'
                     else f"🧬 generation {e_['gen']} on PROBATION — {e_['why']}" if e_['kind'] == 'probation' else f"🧬 generation {e_['gen']} back to ACTIVE — {e_['why']}")
            st['feed'] = (list(st.get('feed') or []) + [{'at': now, 'who': e_['role'], 'sym': '', 'text': line_}])[-rs._pd.FEED_KEEP:]
            rs._tk.KERNEL.note('judge', {'replaced': 'GENERATION REPLACED', 'probation': 'PROBATION'}.get(e_['kind'], 'BACK TO ACTIVE'), f"{e_['role']} gen {e_['gen']} — {e_['why']}", now, key=f"lc:{e_['role']}:{e_['kind']}:{e_['gen']}")
            if e_['kind'] == 'replaced':
                ad_ = rs._admin_load(); rs._audit(ad_, 'agents', 'agent-generation', f"{e_['role']} gen {e_['gen']} → {e_['to']}: {e_['why']} · {e_['changed']}"[:300]); rs._admin_save(ad_)
    except Exception as e:
        print('lifecycle:', str(e)[:160])
    cards = rs._of.scorecards(st, arch, of, rs._agents_real(), cour, life={g_['role']: g_ for g_ in rs._tkl.generations(rs._lc_book(now), now)})
    rs._office_lat('judge', (rs.time.perf_counter() - t0) * 1000)
    of['lat'] = rs._office['lat']
    rs._office['state'] = of
    rs._json_save(rs.OFFICE_PATH, of); rs._json_save(rs.ARCHIVE_PATH, arch)
    # the CURRENT candidate, desk by desk
    case = cases[0] if cases else None
    cur_ctx, cur_case = {}, None
    if case:
        row = case['row']
        m = case['mint']
        scan = rs._of.scan_status((row.get('vitals') or {}).get('safe'), m in rs._intel_inflight, rs._fuse._f(rs._intel_failed.get(m)), rs._fuse._f((rs._intel_cache.get(m) or (0,))[0]) if isinstance(rs._intel_cache.get(m), (tuple, list)) else 0.0, now, rs.INTEL_TTL)
        cur_ctx = {'tally': rs._of.tally_read(row, ser.get(m), now), 'weather': wx, 'courier': cour, 'scan': scan,
                   'warden': wd if wd and wd.get('mint') == m and now - rs._fuse._f(wd.get('at')) <= 900 else None, 'filed': True}
        cur_case = {**rs._tkv.case_view(case, cur_ctx), 'chart': rs._office_chart_view(rs._office['charts'].get(m), row)}
    ms = {a: (rs._office['lat'].get(a) or [None])[-1] for a in rs._of.CHAIN}
    dv_rec = rs._of.devil_record(st, 72, now)   # 📝 the practice desk's objection record (display)
    gens_ = {g_['role']: g_ for g_ in rs._tkl.generations(rs._lc_book(now), now)}
    reviews_ = ((of.get('judge') or {}).get('reviews')) or []
    kmet_ = rs._tk.KERNEL.metrics(now)
    pl_all = [(c_, rs._tkv.pipeline(c_, {'courier': cour, 'ms': {}})) for c_ in cases[:4]]
    krec = lambda who: [{'at': now, 'text': f"${c_['symbol']} · " + next((s_['word'] for s_ in pl_ if s_['agent'] == who), '')[:150]} for c_, pl_ in pl_all]   # what THIS desk said about the top candidates of this pass
    top_ = cases[0] if cases else None
    op_ = (top_ or {}).get('op') or {}
    live = {
        'tally': {'task': f"measured {perf.get('coins')} coins this pass", 'at': perf.get('at'), 'rule': 'one MintState per mint · every section its own timestamp', 'decision': f"{perf.get('coins')} coins read · {stale} stale tapes · {kmet_['mints']} mints in state",
                  'inputs': cur_ctx.get('tally'), 'output': op_.get('tally'), 'recent': krec('tally')},
        'sherlock': {'task': f"evidence for {len(cases)} candidates · {(rs._office.get('enrich') or {}).get('queue', 0)} scan(s) queued", 'at': perf.get('at'), 'rule': 'UNKNOWN is research, never a rejection', 'decision': None if not top_ else f"${top_['symbol']} known: {', '.join(op_['sherlock']['known']) or 'nothing yet'}",
                     'inputs': None if not top_ else {'vitals': top_['row'].get('vitals'), 'scan': cur_ctx.get('scan')}, 'output': op_.get('sherlock'), 'recent': krec('sherlock')},
        'weather': {'task': f"read {(wx.get('inputs') or {}).get('coins')} coins + {(wx.get('inputs') or {}).get('rugN')} judged calls", 'at': wx.get('at'), 'rule': 'regime → rank ×' + f"{(op_.get('weather') or {}).get('factor', 1):g}" + f" · size ×{rs._of.weather_size(wx):g}",
                    'decision': f"{wx.get('regime')} ({round(rs._fuse._f(wx.get('confidence')) * 100)}% confidence)", 'inputs': wx.get('inputs'), 'output': {'regime': wx.get('regime'), 'why': wx.get('why'), 'mods': wx.get('mods'), 'missing': wx.get('missing')},
                    'recent': [{'at': w_['at'], 'text': f"{w_['regime']} — {w_['why']}"} for w_ in (of.get('weatherLog') or [])[-4:]][::-1]},
        'trigger': {'task': f"timing for {len(cases)} candidates from the live narrative", 'at': perf.get('at'), 'rule': f"ENTER on hot early move · breakout · running; READY from rank {rs._tk._b.READY_MIN:g}",
                    'decision': None if not top_ else f"${top_['symbol']} {op_['trigger']['state']}", 'inputs': {'readyMin': rs._tk._b.READY_MIN, 'lesson': (gens_.get('trigger') or {}).get('lessonVector')},
                    'output': op_.get('trigger'), 'recent': krec('trigger')},
        'devil': {'task': f"challenged {len(cases)} candidates", 'at': perf.get('at'), 'rule': 'evidence lowers the rank; only the hard wall blocks', 'decision': None if not top_ else f"${top_['symbol']} {rs._tkv.devil_view(op_)['word']}",
                  'inputs': {'bustedReads': sorted(bust_seen) if bust_seen else None, 'lesson': (gens_.get('devil') or {}).get('lessonVector')}, 'output': None if not top_ else rs._tkv.devil_view(op_), 'recent': krec('devil'), 'record': dv_rec[:10]},
        'warden': {'task': 'sizes each agent seat before it is filled', 'at': (wd or {}).get('at'), 'rule': (wd or {}).get('decided'), 'decision': None if not wd else f"${wd.get('sym')} ${wd['requested']:.2f} → ${wd['allowed']:.2f}" + (' VETO' if wd['veto'] else ''),
                   'inputs': None if not wd else {k: v for k, v in wd.items() if k in ('requested', 'limits')}, 'output': None if not wd else {k: wd[k] for k in ('allowed', 'mult', 'eff', 'veto', 'rules', 'decided')},
                   'recent': [{'at': w_['at'], 'text': f"${w_['sym']} {w_['move']} ${w_['req']:.2f} → ${w_['allowed']:.2f} · {w_['rule']}: {w_['why']}"} for w_ in (of.get('wardenLog') or [])[-4:]][::-1]},
        'courier': {'task': f"read {cour.get('sends')} sends + {cour.get('refused')} refusals of the last hour", 'at': cour.get('at'), 'rule': 'confirmed = filled row + signature', 'decision': cour.get('health'),
                    'inputs': {k: cour.get(k) for k in ('sends', 'fills', 'failed', 'expired', 'refused', 'retries', 'duplicates', 'unsigned', 'pending')}, 'output': {k: cour.get(k) for k in ('health', 'why', 'deltaMed', 'deltaWorst', 'landMed', 'feeMed')},
                    'recent': [{'at': r_['at'], 'text': f"${r_['sym']} {r_['side']} ${r_['usd']:.2f} — {r_['state']}" + (f" · {r_['delta']:+.2f}% vs mid" if r_.get('delta') is not None else '') + (f" · {r_['err']}" if r_.get('err') else '')} for r_ in (cour.get('last') or [])[:4]]},
        'reaper': {'task': f"watching {len(rs._office.get('reports') or [])} open position(s) · {len(rs._office['exiting'])} exit(s) waiting on the ledger", 'at': now, 'rule': 'R1–R9, first that fires',
                   'decision': ' · '.join(f"${r_['symbol']} {r_['state']}" for r_ in (rs._office.get('reports') or [])[:4]) or None, 'inputs': rs._of.tunes(of, 'reaper') | {'takeLine': rs._of.take_line(rcfg, st.get('scalp'))},
                   'output': [{k: r_.get(k) for k in ('symbol', 'state', 'rule', 'evidence')} for r_ in (rs._office.get('reports') or [])],
                   'recent': [{'at': p_.get('closedAt'), 'text': f"${p_.get('sym')} {p_.get('rule')} → " + (f"{p_['realPct']:+.1f}% real (confirmed)" if p_.get('confirmed') and p_.get('realPct') is not None else 'exit NOT confirmed')} for p_ in (arch.get('positions') or [])[-4:]][::-1]},
        'archivist': {'task': f"filed {len(cases)} case(s) this pass · {len(closed)} position(s) closed", 'at': now, 'rule': 'hash-chained · bounded · losses kept', 'decision': f"{len(arch.get('cases') or [])} cases · {len(arch.get('positions') or [])} positions on file",
                      'inputs': {'caseCap': rs._of.ARCH_CASES, 'positionCap': rs._of.ARCH_POS, 'filedEver': arch.get('filed')}, 'output': {'hashBreaks': viol['archivist']['rule'], 'folded': sum(v['n'] for k, v in (arch.get('agg') or {}).items() if k in ('cleared', 'blocked'))},
                      'recent': [{'at': c_['at'], 'text': f"${c_['d'].get('sym')} {'cleared' if c_['d'].get('cleared') else 'blocked'}" + (f" · {c_['d']['action']}" if c_['d'].get('action') else '') + (f" → {c_['out']['p5']:+.1f}% at 5 min" if (c_.get('out') or {}).get('p5') is not None else '')} for c_ in (arch.get('cases') or [])[-4:]][::-1]},
        'judge': {'task': f"{len(reviews_)} real exits reviewed · {sum(1 for c_ in (of.get('candidates') or {}).values() if c_['status'] == 'shadow')} tunable(s) in shadow", 'at': now,
                  'rule': f"one lifecycle for ten roles: PROBATION at net {rs._tkl.PROBATION_N} real losses pinned · replaced at {rs._tkl.REPLACE_N}",
                  'decision': 'on probation: ' + (', '.join(r_ for r_, g_ in gens_.items() if g_['status'] == 'PROBATION') or 'nobody'),
                  'inputs': {'reviews': len(reviews_)}, 'output': {'probation': [r_ for r_, g_ in gens_.items() if g_['status'] == 'PROBATION'], 'generations': {r_: g_['generation'] for r_, g_ in gens_.items()}},
                  'recent': [{'at': x_.get('retiredAt'), 'text': f"{x_.get('role')} gen {x_.get('gen')} replaced — {x_.get('why')}"} for x_ in (rs._lc_book(now).get('lineage') or [])[-4:]][::-1]},
    }
    cands = [{**{k: v for k, v in c_.items() if k != 'shadow'}, 'eval': c_.get('eval') or rs._of.evaluate(c_)} for c_ in sorted((of.get('candidates') or {}).values(), key=lambda c_: -c_['at'])[:6]]
    pipe = rs._tkv.pipeline(case, {**cur_ctx, 'ms': ms})
    if cur_case:
        cur_case['bars'] = rs._office_bars(case.get('pair'), case['mint'])
    queue = []   # every kernel candidate of this pass with the desk it stands at right now (the first desk that has not passed it)
    for c_ in cases[:6]:
        cx_ = cur_ctx if c_ is case else {'tally': rs._of.tally_read(c_['row'], ser.get(c_['mint']), now), 'weather': wx, 'courier': cour}
        pl_ = pipe if c_ is case else rs._tkv.pipeline(c_, {**cx_, 'ms': {}})
        at_ = next((s_ for s_ in pl_ if s_['agent'] not in ('archivist', 'judge', 'reaper') and s_['state'] not in ('PASS', 'DONE', 'WARN')), pl_[5])
        ch_ = c_['row'].get('chart') or {}
        queue.append({'mint': c_['mint'], 'symbol': c_.get('symbol'), 'lean': c_.get('rank'), 'rank': c_.get('rank'), 'status': c_['status'], 'cleared': c_.get('cleared'), 'go': c_.get('cleared'), 'at': at_['agent'], 'state': at_['state'], 'word': str(at_['word'])[:140],
                      'structure': ch_.get('state'), 'entry': (ch_.get('entry') or [None])[0], 'conf': ch_.get('conf'), 'data': ch_.get('q'), 'launch': c_['row'].get('launch'),
                      'pair': c_.get('pair'), 'bars': rs._office_bars(c_.get('pair'), c_['mint']), 'chart': rs._office_chart_view(rs._office['charts'].get(c_['mint']), c_['row']),
                      'devil': rs._tkv.devil_view(c_['op']), 'trace': rs._tkv.trace(c_, cx_)})
    if cur_case:
        cur_case['trace'] = queue[0]['trace'] if queue and queue[0]['mint'] == cur_case['mint'] else rs._tkv.trace(case, cur_ctx)
    dq_ = {}
    for c_ in rs._office['charts'].values():
        k_ = ((c_.get('q') or {}).get('state')) or 'NOT READ'
        dq_[k_] = dq_.get(k_, 0) + 1
    try:   # ✋ your answers to Reaper's questions, graded 15 min later (kept your line → right if the coin held · approved → right if it fell)
        st['askLog'], ask_rec_ = rs._of.ask_grade(st.get('askLog'), lambda m_: (rs._jup_px_cache.get(m_) or (0, 0))[1], now)
    except Exception:
        ask_rec_ = None
    rs._office['payload'] = {
        'at': now, 'mission': rs._of.mission(money, view.get('stage'), now, rs._office.get('last'), view.get('underwater')) | {'control': bool(rcfg.get('agentControl')), 'probation': [r_ for r_, g_ in gens_.items() if g_['status'] == 'PROBATION']},
        'office': {'chain': list(rs._of.CHAIN), 'priority': list(rs._of.PRIORITY), 'coins': perf.get('coins'), 'cases': len(cases), 'cleared': sum(1 for c_ in cases if c_['cleared'])},
        'agents': rs._of.agent_cards(cards, {'live': live, 'office': of}), 'currentCase': cur_case, 'pipeline': pipe,
        'queue': queue, 'positions': rs._office_positions(), 'exiting': [{'mint': p_['mint'], 'sym': p_.get('sym'), 'rule': p_.get('askRule'), 'state': (p_.get('exit') or {}).get('state'), 'since': p_.get('leftAt')} for p_ in rs._office['exiting']],
        'execution': {**cour, 'metrics': rs._fw.exec_metrics(rs._fw_peek().get('ledger'), now, dupes=rs._FW_DUPES['n'])}, 'ownerHand': rs._of.owner_hand(arch.get('positions')), 'survival': rs._surv.cohort(rs._SURV, now), 'edge': rs._edge_view(), 'ownerSeats': rs._of.owner_seats(arch.get('positions')), 'ownerStudy': rs._study['v'], 'aiMemory': rs._aim.size(rs._aim_mem.get() or {}), 'askRec': ask_rec_, 'agentPredict': rs._of.pred_record(arch.get('positions')), 'tid': tid, 'learning': {'patterns': rs._of.patterns(arch, st), 'candidates': cands, 'lineage': [{'agent': x_.get('role'), 'gen': x_.get('gen'), 'why': f"{x_.get('status') or 'replaced'} — {x_.get('why') or ''}" + (f" · next generation: {x_['changed']}" if x_.get('changed') else ''), 'at': x_.get('retiredAt')}
                                                         for x_ in reversed((rs._lc_book(now).get('lineage') or [])[-12:])], 'devil': dv_rec[:10], 'needShadow': rs._of.SHADOW_N, 'needPropose': rs._of.PROPOSE_N},
        'index': (rs._office.get('index') or [])[:80], 'rpc': {'lanes': rs._rpc_quota_state(), 'note': 'keyed lanes = keeper sends / balances first, then holder scans (budgeted); discovery comes from Pump\'s live stream + the launch boards — no RPC first-seen listener runs'},
        'court': rs._office.get('court'), 'opp': rs._office.get('opp'), 'coach': rs._coach_view(now), 'tradeTape': rs._trade_tape(now),   # 👑 the directives in force · 🎬 every real agent trade as one story
          # 👨‍⚖️ the Judge's loss / win reviews + rules · 🎯 this pass's A / B / C ranking counts
        'judge': {'probation': [r_ for r_, g_ in gens_.items() if g_['status'] == 'PROBATION'], 'rulings': len(reviews_), 'probationAt': rs._tkl.PROBATION_N, 'replaceAt': rs._tkl.REPLACE_N,
                  'contribution': rs._of.contribution(st, arch, of, cour, rs._agents_real(), money)},
        'data': {'states': dq_, 'trusted': dq_.get('TRUSTED', 0), 'enterGrade': dq_.get('TRUSTED', 0) + dq_.get('USABLE_WITH_CAUTION', 0), 'coins': len(rs._office['charts']),
                 'meaning': 'TRUSTED = real 1-minute OHLC from the candles service, every integrity check passed, newest bar ≤ 240s old, per-candle volume on ≥ 80% of moving bars, a live pool reading, confidence ≥ 80',
                 'sources': {'candles': 'candles service on this machine: the price-history provider named on each chart (today: Jupiter) sharpened with FEELESS-recorded prices', 'tape': "Tally's own tape: one launch-board price a pass (closes only) — RECONSTRUCTED",
                             'volume': 'per-candle: the provider bars that carry a figure · totals: the launch board\'s 5-min / 1-hour volume', 'trades': 'the 90-second trade tape (parsed swaps), only for coins whose tape the service already holds',
                             'liquidity': 'the launch board\'s pool depth, read each pass onto Tally\'s tape'}},
        'take': rs._of.take_info(rcfg, st.get('scalp')),
        'policy': {**rs._oe.policy(rcfg), 'controls': rs._oe.controls(rcfg, rs._oe.agents_now(rs._of.take_info(rcfg, st.get('scalp')), {**rs._of.tunes(of, 'reaper'), 'maxSeatPct': rs._of.tune(of, 'warden', 'maxSeatPct')},
                                                                                    next(({'stopPct': r_['thesis']['stopPct'], 'sym': r_.get('symbol')} for r_ in rs._office.get('reports') or [] if (r_.get('thesis') or {}).get('stopPct')), None)))},
        'ready': rs._oe.ready(rs._office['boot'], now), 'seat': rs._agents.get('seat'), 'switchEval': rs._agents.get('switchEval'),
        'review': rs._oe.review(st, arch, of, now, marks=of.get('reviewMarks')), 'launch': {'record': rs._oe.pad_record(rs._pd._judged(st, 5)), 'pads': dict(rs._oe.PADS), 'types': list(rs._oe.TYPES),
                                                           'source': 'mint suffix + the launch board row (curve flag, pool age) — anything else is UNKNOWN'},
        'performance': {'deskMs': round(desk_ms, 1), 'agents': {a: {**rs._of.lat(rs._office['lat'].get(a)), 'series': list(rs._office['lat'].get(a) or [])[-30:]} for a in rs._of.CHAIN}, 'chart': rs._of.lat(rs._office['lat'].get('chart')),
                        'speed': {**rs._oe.speed_view(of.get('speed')), 'seatWakes': int(rs._office.get('seatWakes') or 0), 'tickEvery': (rs._agents.get('seat') or {}).get('tickEvery')},
                        'candles': {**rs._office['candleStat'], 'tape': sum(1 for c_ in rs._office['charts'].values() if c_.get('src') == 'tape'), 'real': sum(1 for c_ in rs._office['charts'].values() if c_.get('src') == 'candles')}},
    }
    rs._office['payload']['ops'] = rs._oe.ops(rs._office['payload']['ready'], rs._office['payload']['seat'], rs._office.get('courier'), rs._is_keeper(), rs._uni.FILL_MOVES_HR)
    rs._office['payload']['cycle'] = {**(rs._office.get('cycle') or {}), 'nextIn': rs.AGENTS_EVERY}
    rs._office['payload']['seatActions'] = rs._oe.seat_actions(((rs._agents.get('card') or {}).get('seats')), rs._agents.get('decisions'), rs._agents.get('switchEval'), rs._agents.get('seat'))
    rs._office['payload'].update(rs._office_seat_payload())
    try:
        sc_ = rs._social_cache()
        want_ = {x_.get('mint') for x_ in (rs._agents.get('table') or [])[:30]} | set(rs._office.get('pos') or {})
        rs._office['payload']['social'] = {m_: {k_: v_ for k_, v_ in sc_[m_].items() if k_ not in ('search',)} for m_ in want_ if m_ in sc_}
        rs._office['payload'].update(fresh=rs._office_fresh(now), live=rs._office.get('live'), open=rs._office.get('open'), scans=rs._office.get('scans'), loadPass=rs._office_load_pass(),
                                  lifecycle=rs._lifecycle(now),
                                  kernel=rs._kernel_view(now), rpcStats=rs._chain.rpc_metrics(now), enrich={**(rs._office.get('enrich') or {}), **rs._ENRICH.metrics(now)},
                                  generations=rs._tkl.generations(rs._lc_book(now), now, rs._lc_shadows()),
                                  deskStats=rs._desk_stats_view(now), dialLab=rs._dial_lab(now),
                                  rounds={**rs._tr.summary(rs._rounds_state(), now), 'roundSec': rs._tr.ROUND_SEC, 'desk': {'n': int(now // rs._tr.ROUND_SEC) % int(86400 // rs._tr.ROUND_SEC) + 1, 'left': round(rs._tr.ROUND_SEC - now % rs._tr.ROUND_SEC, 1)},
                                          'live': sorted([{'mint': m_, 'sym': e_.get('sym'), 'round': e_.get('round'), 'left': rs._tr.time_left(e_['first'], now),
                                                           'tier': ((e_.get('reads') or [{}])[-1]).get('tier'), 'score': ((e_.get('reads') or [{}])[-1]).get('score'),
                                                           'phase': ((e_.get('reads') or [{}])[-1]).get('phase')}
                                                          for m_, e_ in (rs._rounds_state().get('c') or {}).items() if not e_.get('decision')], key=lambda r_: (-(r_['round'] or 0), -rs._fuse._f(r_['score'])))[:12],
                                          'recent': [{k_: h_.get(k_) for k_ in ('sym', 'decision', 'why', 'at', 'rounds')} | {'reads': [{k_: r_.get(k_) for k_ in ('round', 'tier', 'score', 'px', 'phase')} for r_ in h_.get('reads') or []]}
                                                     for h_ in (rs._rounds_state().get('hist') or [])[-12:]][::-1]},
                                  memory={k_: v_ for k_, v_ in (rs._real_mem(now) or {}).items() if k_ != 'cells'} | {'worst': sorted(((v_['est'], k_, v_['n']) for k_, v_ in ((rs._real_mem(now) or {}).get('cells') or {}).items()))[:6]})
    except Exception as e:
        print('fresh:', e)
    rs._office['payload']['performance']['passMs'] = round(sum(rs._fuse._f(ms.get(a)) for a in rs._of.CHAIN), 2)
    rs._tape_ledger(now)
    rs._office['payload'].update(nightGuard=rs._ng.view(rs._night['st'], rs._night['v'], now) if rs._night.get('v') else None, tape=rs._tk.KERNEL.tape.view(), ownerReview=rs._owner_view(now), ai=rs._ai_view(now, light=True), net=rs._net_stats(now), armed=rs._office.get('armed'), valve=rs._office.get('valve'), lab=rs._lab_view(now), regret=rs._rg.view(rs._regret_book(), now), capital=rs._capital_view(), trail=rs._office.get('trail'), teach={**rs._tch.view(rs._teach_state()), 'rules': rs._taught_view()},
                              universe={'capUsd': rs._uni.band()[1], 'minCapUsd': rs._uni.band()[0], 'word': rs._uni.band_word(), 'maxAgeH': rs._uni.limits()['maxAgeH'], 'minVol1h': rs._uni.limits()['minVol'], 'pumpTrend': rs._uni.limits()['trend'], 'trendingN': rs._uni.limits()['trendingN'], 'inLane': len(rs._agents.get('table') or []),
                                        'board': (rs._office.get('intake') or {}).get('board'), 'mints': len(rs._tk.KERNEL.store.mints)})
    rs._hub_publish(now)   # 📡 this pass as DELTAS: only what changed since the last one
    try:   # a read-only snapshot of what the page was handed (like agents_duty.json) — for checking the office without signing in to HQ (≤ once a minute)
        if now - rs._fuse._f(rs._office.get('viewSavedAt')) >= rs.VIEW_SAVE_SEC:
            rs._json_save(rs.DATA_DIR / 'agent_office_view.json', rs._office['payload']); rs._office['viewSavedAt'] = now
    except Exception:
        pass


def _agents_real():
    """💵 The REAL-money Fuse card test: every coin the agents put on the owner's real card (leg tag '🤖 agents GO') that has left it,
    judged on the card's own exit vs entry (real_learn). → {n, med, won}"""
    rs = _rs()
    ps = [rs._fuse._f(p.get('pct')) for p in (rs._json_load(rs.REAL_LEARN_PATH, {}).get('pieces') or []) if 'tag:🤖' in (p.get('k') or [])]
    last_ = list(ps)   # in the order they left the card (for the win / loss pips)
    last_sg = [rs._fuse._f(p.get('pct')) for p in (rs._json_load(rs.REAL_LEARN_PATH, {}).get('pieces') or []) if 'tag:🤝' in (p.get('k') or [])]
    n = len(ps); ps.sort()
    out = {'n': n, 'med': None if not n else round(ps[n // 2] if n % 2 else (ps[n // 2 - 1] + ps[n // 2]) / 2, 2), 'won': None if not n else round(sum(1 for x in ps if x > 0) / n * 100)}
    sg = sorted(rs._fuse._f(p.get('pct')) for p in (rs._json_load(rs.REAL_LEARN_PATH, {}).get('pieces') or []) if 'tag:🤝' in (p.get('k') or []))
    out['suggested'] = {'n': len(sg), 'med': None if not sg else round(sg[len(sg) // 2], 2), 'won': None if not sg else round(sum(1 for x in sg if x > 0) / len(sg) * 100)}   # 🤝 coins the owner took from their alert
    out['last'] = last_[-16:]; out['suggested']['last'] = last_sg[-16:]; out['w'] = sum(1 for x in last_ if x > 0)
    out['styles'] = rs._rl.style_record(rs._json_load(rs.REAL_LEARN_PATH, {}).get('pieces') or [])   # ⚡ AUTO / SCALP / RIDE, each its own real record
    return out


def _kernel_row(x):
    """A kernel candidate as a tier-card candidate row (the fields the engine's own rows carry)."""
    return {'mint': x['mint'], 'symbol': x['symbol'], 'pairAddress': x['pair'], 'price': x['px'], 'liq': (x.get('nums') or {}).get('liq'), 'safe': (x.get('vitals') or {}).get('safe') is True, 'ageH': (x.get('vitals') or {}).get('ageH')}


def _agent_inherit_rows(limit=8):
    """🤖 INHERIT, NEVER REDO (owner, 2026-10-13: "have the engine build new strats from the agents' work — never waste the agents' time,
    just inherit"): the runner candidates of a PAPER card on pick style `agents` are the kernel's own judged list — READY first, then
    CONTENDING, best rank first — exactly what the ten agents already read, ranked, weighed with real-money memory, the Judge's and
    the coach's penalties this pass. No second scan, no model call, no fetch. A coin the agents rejected is simply not on the list.
    Paper only: the real card's seats are filled by the agents themselves."""
    rs = _rs()
    rows = sorted([(m_, d_) for m_, d_ in rs._tk.KERNEL.dec.items() if d_.get('status') in ('READY', 'CONTENDING') and m_ in rs._tk.KERNEL.store.mints],
                  key=lambda kv: (kv[1]['status'] != 'READY', -rs._fuse._f(kv[1].get('rank'))))
    out = []
    for m_, d_ in rows:
        x = rs._tk.KERNEL.candidate(m_, d_)
        if x and x.get('px') and x.get('pair') and not rs._fw.dollar_named(x.get('symbol')):
            out.append({**rs._kernel_row(x), 'score': 60 + min(40.0, rs._fuse._f(x.get('rank')) / 10), 'tag': f"🤖 inherits the agents · {d_['status']} · rank {rs._fuse._f(x.get('rank')):.0f}"})
    return out[:limit]


def _agents_go_rows(legs=(), seats=2, learn=False, learn_pct=100, trust=False):
    """The team's GO coins for the real card's rush. PROVEN (5-min stage conquered + `agentFeed`): up to `agentSeats` coins, normal tickets.
    🎓 LEARNING (`agentLearn`, before they are proven): ONE coin at a time — a WHOLE seat at `learn_pct` 100 (default), else a % ticket.
    The other seats stay the owner's: the agents only SUGGEST for them (My cards alert → 🤝 tagged, scored apart)."""
    rs = _rs()
    v = rs._agents.get('view') or {}
    held = sum(1 for l in legs or [] if rs._prime.agent_leg(l))
    if v.get('feed'):
        if held >= int(seats or 2):
            return []
        learning = False
    elif learn:
        if held >= (2 if trust and rs._pos.trusted(rs._agents_real()) else 1):   # 🤝 earned trust: a 2nd seat
            return []
        learning = True
    else:
        return []
    on_ = {l.get('mint') for l in legs or []}
    out = []
    for m_, d_ in rs._tk.KERNEL.ready(exclude=on_):   # ⚙ the kernel's READY candidates (never a paper GO): the engine's trench drop still applies every one of its own checks
        x = rs._tk.KERNEL.candidate(m_, d_)
        if x and not rs._fw.dollar_named(x.get('symbol')):
            out.append({**rs._kernel_row(x),
                        'trenchOnly': True, 'trenchScore': 900 + x['rank'], 'tag': '🤖 agents READY' + (' · 🎓 learning seat' if learning else ''), **({'stakePct': int(learn_pct or 100)} if learning else {})})
    return out[:1 if learning else 4]


def _agents_snapshot():
    """Everything the last agent pass + tier tick left in memory (the office rides on the same answer). Runs nothing."""
    rs = _rs()
    if not rs._agents.get('view'):
        st = rs._agents_mem.get()
        rcfg_ = ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {})
        rs._agents['view'] = rs._paper_view(st, rs._agents.get('paper') or [], rcfg_, rs.time.time())
    v_ = {**rs._agents['view'], 'impostors': rs._agents.get('impostors') or []}   # 🎭 fakes of real coins dropped at intake (Tally's guard)
    if rs._agents.get('card') and (v_.get('card') or {}) != rs._agents['card']:   # the card moves every tier tick; the view is rebuilt once a minute
        v_ = {**v_, 'card': rs._agents['card']}
    return {**v_, 'office': rs._office.get('payload')}   # 🏢 the office rides on the SAME response: the Agents page makes one request


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

