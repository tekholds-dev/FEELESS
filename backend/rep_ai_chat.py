"""🧹 Direct LM chat, model desk, prompt studio, colony view — split out of rep_ai.py by scripts/split-module.py (owner 2026-11-17 cleanup); first moved whole out of reputation_service.py.
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


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

