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


