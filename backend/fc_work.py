"""🧹 The general cat at work — moved whole out of feecat_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches feecat_service still
reaches it, and every function here is still reachable on feecat_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import feecat_service
    return feecat_service


def _rails():
    rs = _rs()
    return rs._gr.load(rs.DATA_DIR / 'guardrails.json')


def _task_cap_max():
    """🛡 The most one task may spend: today's TASK_CAP_MAX, or lower when the owner's guardrail says so (off = the half-cent floor)."""
    rs = _rs()
    return max(0.005, min(rs.TASK_CAP_MAX, rs._gr.value(rs._rails(), 'taskCap')))


def _first_list(cat):
    """Its first sources, each with its real state: real visits from the sources book, cookies read from its sealed sign-ins. Nothing is opened to work this out."""
    rs = _rs()
    now = rs.time.time(); jar = {}
    for site, r in (cat.get('siteSessions') or {}).items():
        try:
            ctx = rs.json.loads(rs._ck.unseal(r.get('ctx'), cat['id'], data_dir=rs.DATA_DIR))
            clean, st = rs._cb.clean_context(ctx, site, now)
            ends = [float(k.get('expires')) for k in (clean or {}).get('cookies') or [] if isinstance(k.get('expires'), (int, float)) and k.get('expires') > 0]
            jar[site] = {'kept': st.get('kept', 0), 'soonest': min(ends) if ends else None}
        except Exception:
            jar[site] = {'kept': 0, 'soonest': None}
    return rs._feat._sources.first_rows(cat, rs._src_book(), jar, now)


async def _site_reads(kind, by=None):
    """📖 A7: the best listed sites for this proof, really opened by us before the minds answer, and each visit goes in the sources book. Never stops a proof.
    🧠 COL-9: never the same research twice. A read another proof of this kind made a moment ago is reused while still fresh (markets: 5 minutes,
    games: 30, content: an hour, pages: 6 hours); the reuse is counted, nothing is opened again."""
    rs = _rs()
    hit = rs._READS.get(kind); me_ = tuple(by or ('', ''))
    if hit and rs.time.time() - hit[0] < rs.READ_FRESH_S.get(kind, 600) and hit[2]:
        rs._READS[kind] = (hit[0], hit[1], hit[2], hit[3] + 1, *hit[4:])
        src_ = hit[4] if len(hit) > 4 else ('', '')
        if src_[0] and src_[0] != me_[0]:   # 🧠 COL-9: another agent's fresh read: its folder says whose, and how old
            ago_ = round(rs.time.time() - hit[0])
            return hit[1], [{**r_, 'sharedBy': src_[1] or 'another agent', 'sharedAgo': ago_} for r_ in hit[2]]
        return hit[1], hit[2]
    try:
        async with rs.httpx.AsyncClient() as http:
            line_, sites_ = await rs._feat._sources.read_first(http, kind, await rs.asyncio.to_thread(rs._stash.trust_rows, rs.STASH_DIR, rs._feat._sources.STASH_CAT.get(kind)))
        for r_ in sites_:
            rs._src_note(r_['host'], r_['ok'])
        if any(r_.get('ok') for r_ in sites_):
            rs._READS[kind] = (rs.time.time(), line_, sites_, 0, me_)
        return line_, sites_
    except Exception as e:   # noqa: BLE001
        print(f'[refs] {kind}: {str(e)[:120]}')
        return '', []


def _src_book():
    rs = _rs()
    try:
        return rs.json.loads(rs.SOURCES_PATH.read_text()) or {}
    except (OSError, ValueError):
        return {}


def _src_note(host, ok):
    rs = _rs()
    try:
        b = rs._src.record(rs._src_book(), host, ok); rs.SOURCES_PATH.write_text(rs.json.dumps(b))
        h_ = rs._src.host_of(host)
        if not ok and h_:
            old_ = [x for x in (rs.BLOCKED_TXT.read_text().split('\n') if rs.BLOCKED_TXT.exists() else []) if x and not x.startswith(h_ + ' ')]
            rs.BLOCKED_TXT.write_text('\n'.join((old_ + [f"{h_} {rs.time.strftime('%Y-%m-%d %H:%M', rs.time.gmtime())}"])[-500:]) + '\n')
    except Exception as e:   # noqa: BLE001 — the book never blocks a task
        print(f'[sources] {e}')


async def _human_wait(ev, base_s, seen_at):
    """Wait for the owner's answer. The time runs out only once they have stopped moving on the watch screen. seen_at() → when they last moved."""
    rs = _rs()
    started = rs.time.time(); limit = base_s
    while True:
        try:
            await rs.asyncio.wait_for(ev.wait(), max(0.01, limit - (rs.time.time() - started)))
            return
        except rs.asyncio.TimeoutError:
            now = rs.time.time(); last = float(seen_at() or 0)
            if now - last >= rs.HUMAN_ACTIVE_S or now - started >= rs.HUMAN_MAX_S:
                raise
            limit = min(rs.HUMAN_MAX_S, last + rs.HUMAN_ACTIVE_S - started)


def _work_live(cat=None):
    """General cats' model calls: their OWN switch (GENERAL_CAT_LIVE) so the owner can test a general cat without turning on every trading
    cat's brain calls (LAUNCH_CAT_LIVE turns both on). Needs the OpenRouter key either way."""
    rs = _rs()
    key_ = bool(rs.os.environ.get('OPENROUTER_API_KEY')) or bool(cat and rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR))   # 🔑 owner 2026-11-11: an agent on its OWN key works with FEELESS's key removed
    return key_ and (rs.os.environ.get('GENERAL_CAT_LIVE', '').lower() in ('1', 'true', 'on') or rs._brains_live())


def _work_view(cat_id, owner=False):
    rs = _rs()
    view = rs._work_task_view(cat_id, owner)
    if owner:   # 💬 the proof its chat is talking about
        view['deskProof'] = ((rs._load().get('cats') or {}).get(cat_id) or {}).get('deskProof')
    return view


def _work_task_view(cat_id, owner=False):
    rs = _rs()
    w = rs._WORK.get(cat_id) or {}
    t = w.get('task')
    if not t:
        return {'task': None}
    wins = []
    for x in t['windows']:
        s_ = (w.get('sessions') or [None, None])[x['i']] or {}
        wins.append({**{k: x.get(k) for k in ('i', 'model', 'goal', 'status', 'bubble', 'url', 'title', 'human', 'answer', 'cost', 'coin', 'scratchN', 'cursor', 'marks')}, 'scratch': len(x.get('scratch') or []), 'steps': x['steps'][-10:],
                     'provider': s_.get('provider'), 'note': s_.get('note'), **({'live': s_.get('hand') if x.get('status') == 'human' and s_.get('hand') else s_.get('live'), 'hand': x.get('status') == 'human' and bool(s_.get('hand')), 'shot': bool((w.get('pages') or [None, None])[x['i']] and not s_.get('live'))} if owner else {})})
    return {'task': {k: t.get(k) for k in ('id', 'text', 'mode', 'status', 'cap', 'cost', 'answer', 'fast', 'why', 'stepsMax', 'keep', 'backup', 'walletPaid', 'proofKind')}, 'windows': wins}


def clean_limits(raw):
    """🎚 A general agent's spend limits, clamped; 0 = no extra limit. mindUsd: $ each mind may spend on one task · steps: actions each mind may take · dayUsd: $ a day."""
    rs = _rs()
    r = raw if isinstance(raw, dict) else {}
    num = lambda v, hi: max(0.0, min(float(hi), float(rs._num(v) or 0)))
    return {'mindUsd': [round(num(v, rs.TASK_CAP_MAX), 4) for v in list(r.get('mindUsd') or [])[:2]], 'steps': int(num(r.get('steps'), rs._ca.GO_STEPS)), 'dayUsd': round(num(r.get('dayUsd'), 100), 4)}


def ensure_real(cat):
    """👛 FUNDED = READY (owner 2026-11-02: "when I add money and split it I expect her to be ready"): any agent with its own wallet — general,
    trader, or Fee — trades from that wallet once funded, each buy sized by its MAX A TRADE (≤ 0.5 SOL) and every wallet guard (budget · day
    cap · gas · one order at a time). A general cat still buys only what you order; a trader / Fee mirror their own picks. Owner's ⏸ Paper stands."""
    rs = _rs()
    w = cat.get('agentWallet') or {}
    if not w.get('address') or not w.get('owner') or cat.get('paperByOwner') or rs._real.is_real(cat):
        return False
    rs._real.go_real(cat, w['owner'], max(rs._real.MIN_BUDGET, min(0.5, rs._num((cat.get('risk') or {}).get('maxPositionSol')) or 0.05)), rs.time.time())
    return True


def day_left(cat):
    """$ left today under its daily limit (None = no daily limit)."""
    rs = _rs()
    day = float((cat.get('limits') or {}).get('dayUsd') or 0)
    if not day:
        return None
    return max(0.0, day - float(((cat.get('brainsCfg') or {}).get('daySpend') or {}).get(rs.time.strftime('%Y-%m-%d', rs.time.gmtime()), 0)))


def _read_caps(lim, cap, n):
    """🌐 Each mind's ceiling on a proof read: his own per-mind caps when set (never past the task cap), else an even split. Pure."""
    own = [float(x) for x in (lim or {}).get('mindUsd') or [] if isinstance(x, (int, float)) and x > 0]
    return [min(float(cap), x) for x in own[:n]] if len(own) >= n else [float(cap) / n] * n


def _work_start(cat_id, cat, text, to=None, files=None, pow_=None, pows=None, read_=False, kind=None):
    """Start one task in the cat's windows. 🏇 Let it go (cat.workGo): a long step budget (cat_agent.GO_STEPS) — it stops only when done, at
    its $ cap, or when a person is needed (a sign-in / CAPTCHA / payment: it never types a password or a card)."""
    rs = _rs()
    b = cat.get('brainsCfg') or {}
    if not pow_ and not read_:
        cat['workNow'] = {'text': str(text)[:2600], 'to': to, 'at': rs.time.time()}   # 🛟 a restart mid-task files this to resume — an ask is never lost
    cap = min(float(cat.get('taskCap') or rs.TASK_CAP_DEFAULT), rs._task_cap_max(), max(0.005, float(b.get('credit') or 0) - rs._lc.CREDIT_RESERVE))   # its own credit only, always leaving the reserve
    left_ = rs.day_left(cat)
    if pow_:   # ⛏ a PoW folder runs to its close: no task cap / day limit / step config in its way (owner 2026-11-01) — only its credit, never past the reserve
        cap = min(rs._pow.ROUND_USD * (len(pows) if pows else 1), max(0.005, float(b.get('credit') or 0) - rs._lc.CREDIT_RESERVE))   # 💲 each coin's research round has its own small ceiling
    elif read_:   # 🌐 owner 2026-11-17 ("said a .03 limit … limits should be set already by me"): a PoB / PoP read runs on HIS limits (task cap, each mind's cap,
        cap = min(float(cat.get('taskCap') or rs.TASK_CAP_DEFAULT), rs._task_cap_max(), max(0.005, float(b.get('credit') or 0) - rs._lc.CREDIT_RESERVE))   # moves), not PoW's $0.03 a coin
    elif left_ is not None:
        if left_ <= 0:
            raise rs.HTTPException(409, "It reached today's $ limit. Raise it in its limits, or it carries on tomorrow.")
        cap = min(cap, left_)
    lim_ = cat.get('limits') or {}
    models = list(b['brains'])[:8]
    k_minds_ = 'pow' if pow_ else kind if read_ else None
    if k_minds_ and rs._lc.minds_for(b, k_minds_):   # 🧠 owner 2026-11-15 'not even the right minds set': a proof's monitors browse with THAT proof's own pair (PoB = its PoB minds), the same models that make its call
        models = rs._lc.minds_for(b, k_minds_)
    if to not in (None, 'both') and str(to).isdigit() and int(to) < len(models):   # talk to ONE of its minds: that model takes the whole task
        models = [models[int(to)]]
    if pows:   # ⛏ a pair round: each mind's own model, in mind order (window i = mind i)
        base_ = int(pow_.get('base') or 0)
        models = [models[(base_ + i) % len(models)] for i in sorted(pows)]
    names = [str(m).split('/')[-1][:24] for m in models]
    steps = int(lim_.get('steps') or 0) or (rs._ca.GO_STEPS if cat.get('workGo') else rs._ca.STEP_MAX)
    if pow_:   # ⛏ one mind, its own job, the PoW's step budget (its random 3–8 moves a site, pow.py) — the rest is the same guarded work path
        steps = rs._pow.budget(pow_)
    elif read_:
        steps = int(lim_.get('steps') or 0) or rs.READ_STEPS   # 🌐 his moves a window, else the read's own
    rs._WORK[cat_id] = {'task': rs._ca.new_task(rs.uuid.uuid4().hex[:10], text, models, cap, steps, 'jobs' if pow_ or read_ else cat.get('workMode') or 'plan', rs._read_caps(lim_, cap, len(models)) if read_ and len(models) > 1 else lim_.get('mindUsd') if len(models) > 1 else None), 'events': {}, 'go': {}, 'sessions': [None] * len(models), 'pages': [None] * len(models), 'at': rs.time.time()}
    rs._WORK[cat_id]['task']['alts'] = ['https://' + h for h in rs._src.best(rs._src_book(), n=6)]   # 🔀 where a repeating mind is moved
    rs._WORK[cat_id]['task']['knowhow'] = rs._pow.README + '\n' + rs._colony.KNOWHOW + (' ' + rs._colony.COLONIZED if rs._hive_on(cat) else '') + '\n' + rs._src.brief(rs._src_book())   # 🐝🧭 every mind knows the Colony + where to browse
    if pow_:
        rs._WORK[cat_id]['task']['pow'] = pow_
    if pows:   # each mind researches its own coin at once, on its own ceiling
        rs._WORK[cat_id]['task'].update(pows=dict(pows), jobs=[rs._pow.goal(pows[i]) for i in sorted(pows)], mindCaps=[rs._pow.ROUND_USD] * len(pows))
    if read_:   # 🌐 each mind reads for itself, blind to its partner
        rs._WORK[cat_id]['task'].update(proofRead=True, jobs=[str(text)] * len(models))
    if pow_ or read_ or (b.get('kind') or 'trading') == 'trading':   # 📰 a trader's windows (and every PoW): read + click on the research list only (cat_policy.RESEARCH_*)
        rs._WORK[cat_id]['task'].update(research=True, tools={'browse': True, 'forms': True}, alsoHosts=rs._proof_hosts(cat, 'pow' if pow_ else (cat.get('proofSite') or {}).get('kind')) + (list(cat.get('proofHosts') or []) if read_ else []))
    else:
        rs._WORK[cat_id]['task']['tools'] = rs._cp.toolkit(cat.get('job', 'agent'), cat.get('tools'))
    rs._WORK[cat_id]['task']['files'] = [{'name': f['name'], 'mime': f['mime'], 'path': str(rs._af.local_copy(rs.DATA_DIR, cat, f['id']))} for f in rs._af.touch(cat, files)]   # ☁ its `upload` action reads these
    rs._WORK[cat_id]['task']['personal'] = rs._feat.personal_line(cat) + ('' if pow_ else rs._job_brain(cat, text))   # 🧠 what its owner told it, and what it knows by itself. A PoW's job stays as it was
    rs._WORK[cat_id]['task']['clouds'] = {i: [x.get('text', '') for x in (b.get('minds') or {}).get(m, [])][-8:] for i, m in enumerate(models)}   # ☁ each mind reads its own cloud
    rs._OR_KNOBS.set(b.get('knobs') or None)   # 🎛 rides into the task (create_task copies this context)
    ctx_tok_ = rs._CALL_CTX.set({'kind': k_minds_, 'ref': f"read:{rs._WORK[cat_id]['task']['id']}", 'minds': models}) if k_minds_ else None   # 🧾 Slice 0: a proof's windows log their calls (read:<task>), so its record names who really read
    try:
        rs._WORK[cat_id]['runner'] = rs.asyncio.create_task(rs._work_run(cat_id, models, names, text, cap, str(b.get('prompt') or '')[:1200], b.get('efforts') or {},
                                                                rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)))
    finally:
        if ctx_tok_ is not None:
            rs._CALL_CTX.reset(ctx_tok_)


async def _work_run(cat_id, models, names, text, cap, brief='', efforts=None, own_key=None):
    rs = _rs()
    rs._OR_CAT.set(cat_id)
    w = rs._WORK[cat_id]
    await rs._or_models()   # the price list: after a restart every model read as 'unknown cost' and the budget check stopped the task
    cat_now = rs._load()['cats'].get(cat_id) or {}; paid_ = {'usdc': 0.0, 'on': False}
    if (cat_now.get('agentWallet') or {}).get('circleAcct') == 'agent' and not own_key:   # 💳 it pays for its own thinking from its own wallet
        try:
            paid_.update(usdc=await rs._thinking_money(cat_now), on=True)
        except (rs.httpx.HTTPError, ValueError) as e:
            print(f'[agent think] {cat_id}: {str(e)[:120]}')
    env = rs.os.environ
    async with rs.httpx.AsyncClient(timeout=30) as http:
        sessions, pages, stok_ = [], [], None
        try:
            t_open_ = rs.time.time()
            asked_ = [bool(j) for j in rs._ca.split_jobs(text, len(models))] if len(models) > 1 else [True]
            for i, _m in enumerate(models):
                if len(models) > 1 and sum(asked_) == 1 and not asked_[i]:   # "A: …" only: the mind not asked opens no cloud browser (it sat on a blank tab, billing minutes)
                    sessions.append({'provider': 'reader', 'live': None, 'note': 'not asked this time'}); pages.append(rs._cb.ReaderPage(http)); continue
                warm_ = rs._warm_for(cat_id)
                if warm_ and not warm_.get('busy') and (warm_['site'].split('.')[0] in str(text).lower() or ((rs._load()['cats'].get(cat_id) or {}).get('proofSite') or {}).get('site') == warm_['site']):
                    warm_['busy'] = True   # 🔥 the window the owner just cleared: this mind works there, signed in, with no new check. It stays open after
                    s_, _tried = {'provider': 'steel', 'id': warm_['sid'], 'live': warm_['live'], 'hand': warm_['hand'], 'connect': warm_['connect'], 'warm': True}, []
                else:
                    s_, _tried = await rs._cb.open_session(http, env, rs._site_ctx(rs._load()['cats'].get(cat_id) or {}))   # 🔓 starts signed in where the owner signed in
                sessions.append(s_)
                try:
                    pages.append(await rs._cb.LivePage(s_['connect'], s_.pop('cookies', None), **({'plain': True} if s_.get('warm') else {})).start() if s_.get('connect') else rs._cb.ReaderPage(http))
                except Exception as e:   # the live browser did not connect → the reader keeps the model working
                    sessions[-1] = {**s_, 'provider': 'reader', 'live': None, 'note': f"{s_['provider']} did not connect ({str(e)[:60]})"}
                    pages.append(rs._cb.ReaderPage(http))
            ctx_s_ = rs._CALL_CTX.get() or {}   # 🧠 Slice 10: the stash in front of every window (ask first, keep every public page 3 ways, sealed)
            stok_, pages = rs._sbrain.start_run(w['task'], pages, sessions, rs.DATA_DIR, ctx_s_.get('ref') or f"task:{w['task'].get('id')}", cat_id, ctx_s_.get('kind') or '',
                                               [str(h) for h in (cat_now.get('siteSessions') or {})] + [str((rs._warm_for(cat_id) or {}).get('site') or '')][:1 if rs._warm_for(cat_id) else 0])
            w.update(sessions=sessions, pages=pages); w['task']['openSec'] = round(rs.time.time() - t_open_, 1)

            orders = [{'role': 'system', 'content': f"Your owner's standing orders, sealed at launch — follow them on every step: {brief}"}] if brief else []

            def spend_left(model):
                """What this call may still spend: the task's cap, or in a pair round the mind's own ceiling (the two minds share nothing)."""
                t_ = w['task']; left_ = t_['cap'] - t_['cost']
                if t_.get('pows'):
                    left_ = min(left_, rs._pow.ROUND_USD - max([float(x.get('cost') or 0) for x in t_['windows'] if x.get('model') == model] or [0.0]))
                return left_

            def reply_room(model, messages):
                """🎚 The longest reply that still fits what is left of its $ cap (owner's low cap: a short question must still run), up to 4096 tokens."""
                row = next((m for m in ((rs._MODELS.get('rows') or {}).get('models') or []) if m['id'] == model), None)
                if row is None or not row.get('outUsd'):
                    return 4096
                sent = len(rs.json.dumps(orders + messages, ensure_ascii=False).encode('utf-8')) / 3 + 256
                return max(0, min(4096, int((spend_left(model) - sent * row['inUsd'] / 1e6) / row['outUsd'] * 1e6)))

            async def ask(model, messages):   # 🧾 Slice 0: inside a proof's read, every window call goes in the call log (who REALLY answered, $, time)
                ctx_ = rs._CALL_CTX.get()
                if not ctx_:
                    return await ask_raw(model, messages)
                ans_ = {}; tok_ = rs._ANSWER.set(ans_); t0_ = rs.time.perf_counter(); out_ = ('', 0.0)
                try:
                    out_ = await ask_raw(model, messages)
                    return out_
                finally:
                    rs._ANSWER.reset(tok_)
                    rs._mind_call(cat_now, model, ctx_, ans_, out_[0], out_[1], 'window', rs.time.perf_counter() - t0_)

            async def ask_raw(model, messages):   # 📜 the sealed brief rides every call (plan · each browsing step · merge)
                rs._OR_LAST.pop('err', None); rs._OR_LAST.pop('backup', None)
                if own_key:   # an explicitly supplied owner key takes priority
                    try:
                        text_, usd_ = await rs._or_call(model, orders + messages, max_tokens=reply_room(model, messages), backup=False, **({'effort': efforts[model]} if (efforts or {}).get(model) else {}))
                        if str(text_ or '').strip():
                            return text_, usd_
                    except rs._ca.Stopped:
                        raise
                    except Exception:
                        pass   # → its wallet's pay-per-call provider, then the free backup (the creator's order)
                room_ = paid_['usdc'] - rs._ap.RESERVE_USD
                if paid_['on'] and room_ > 0:
                    t_ = w['task']; ceil_ = min(room_, spend_left(model)); paid_['usdc'] -= ceil_   # held while it is in flight: two minds can never both spend the same USDC
                    usd_ = 0.0
                    try:
                        text_, usd_ = await rs._wallet_call(cat_now, model, orders + messages, reply_room(model, messages), ceil_)
                    finally:
                        paid_['usdc'] += ceil_ - usd_
                    if str(text_ or '').strip():
                        t_['walletPaid'] = round((t_.get('walletPaid') or 0) + usd_, 6)
                        return text_, usd_
                text_, usd_ = await rs._or_call(model, orders + messages, max_tokens=reply_room(model, messages), backup=True, **({'key': own_key} if own_key else {}), **({'effort': efforts[model]} if (efforts or {}).get(model) else {}))
                if not str(text_ or '').strip():
                    raise rs._ca.Stopped(rs._OR_LAST.get('err') or 'The model returned nothing. Try again.')
                if rs._OR_LAST.get('backup'):
                    w['task']['backup'] = True
                return text_, usd_

            def cost_bound(model, messages):
                if str(model).startswith('local/'):   # 🖥 the owner's own LM Studio is free
                    return 0.0
                row = next((m for m in ((rs._MODELS.get('rows') or {}).get('models') or []) if m['id'] == model), None)
                if row is None:
                    return float('inf')
                tokens = len(rs.json.dumps(orders + messages, ensure_ascii=False).encode('utf-8')) / 3 + 256
                room = reply_room(model, messages)
                return float('inf') if room < 256 else (tokens * row['inUsd'] + room * row['outUsd']) / 1e6
            ask.cost_bound = cost_bound

            async def wait_human(i):
                win_ = (w['task'].get('windows') or [{}] * (i + 1))[i]; h_ = win_.get('human') or {}
                if h_.get('kind') == 'login':   # 🔐 a site already in its vault: filled on the server, no pause — the model only ever types the placeholders
                    try:
                        got_ = rs._cv.saved_for(rs._load()['cats'].get(cat_id) or {}, h_.get('site'), data_dir=rs.DATA_DIR)
                    except Exception:
                        got_ = None
                    if got_:
                        win_['pw'] = {'site': h_.get('site'), 'user': got_[0][:120], 'pw': got_[1]}
                        w['task'].setdefault('vaultUsed', []).append(h_.get('site'))
                        return True
                check_ = h_.get('kind') != 'login' and bool(rs.re.search(r'captcha|bot check|cloudflare|checkpoint|blocked', str(h_.get('why') or ''), rs.re.I))   # a WALL, not a sign-in (yours to do)
                if check_:   # 🧭 a bot check / wall: the book learns it, and the window offers the best other sources
                    host_ = rs._src.host_of(h_.get('url') or win_.get('url'))
                    known_ = rs._src.walled_lately(rs._src_book(), host_)
                    rs._src_note(host_, False)
                    h_['alts'] = [h for h in w['task'].get('alsoHosts') or [] if h != host_][:6] if w['task'].get('notCoins') else rs._src.best(rs._src_book(), exclude=[host_]); win_['human'] = h_
                    if h_.get('kind') == 'challenge' and (known_ or host_ in (w['task'].get('wallWaits') or [])):   # 🚧 one 45 s window per wall: the other mind and later coins move on at once, and the gap is recorded
                        return False
                    w['task'].setdefault('wallWaits', []).append(host_)
                ev = w['events'][i] = rs.asyncio.Event()
                pg_ = pages[i] if i < len(pages) and getattr(pages[i], 'live', False) else None
                try:
                    if pg_:
                        await pg_.release()   # 🙋 hands off: you are alone in the window (a routed browser loops Cloudflare's box)
                    w.setdefault('connects', {})[i] = (sessions[i] or {}).get('connect') if i < len(sessions) else None   # runtime only: never in the task, its file or a view
                    await rs._human_wait(ev, rs.BLOCK_PIVOT_S if check_ else rs.HUMAN_WAIT_S, lambda: (w.get('seen') or {}).get(i))
                except rs.asyncio.TimeoutError:   # ⏸ nobody answered: a bot check → the best other source; anything else is filed to come back to
                    if check_:
                        rs._challenge_note(cat_id, rs._src.host_of(h_.get('url') or win_.get('url')), 'timedOut')
                        w['events'].pop(i, None)
                        if h_.get('alts'):
                            win_['redirect'] = 'https://' + h_['alts'][0]
                        return True
                    w['events'].pop(i, None)
                    why_ = h_.get('why') or 'it needs you'
                    win_['parked'] = f"{rs._ca.PARKED}: no answer in {rs.HUMAN_WAIT_S // 60} min — filed to come back to ({why_})"
                    w['task'].setdefault('parked', []).append({'why': why_, 'url': h_.get('url') or win_.get('url'), 'mind': i})
                    return False
                finally:
                    (w.get('connects') or {}).pop(i, None); (w.get('seen') or {}).pop(i, None)
                    if pg_:
                        try:
                            await rs._seal_downloads(cat_id, (sessions[i] or {}).get('id') if i < len(sessions) else None, pg_, h_.get('site') or '')   # 🔏 what you downloaded there
                        except Exception as e:
                            print(f'[vault] {cat_id}: {str(e)[:80]}')
                        try:
                            await pg_.start()   # the agent takes the window back where you left it
                        except Exception as e:
                            print(f'[agent window] {cat_id}: could not take the window back ({str(e)[:80]})')
                went_ = bool(w['go'].pop(i, False))
                if went_ and check_ and pg_ and not win_.get('redirect'):   # 🍪 you passed the check: keep its pass (sealed) so its next windows skip it
                    await rs._keep_pass(cat_id, pg_, h_.get('url') or win_.get('url'))
                    rs._challenge_note(cat_id, rs._src.host_of(h_.get('url') or win_.get('url')), 'manualPass')
                return went_
            async def feeless(tool, q=''):   # 🧰 FEELESS first: our own read-only tools, server-side (the browser is walled off from us)
                if tool in ('inbox', 'mailbox'):
                    return await rs._mail_tool(http, rs._load()['cats'].get(cat_id) or {}, tool)
                return await rs._ct.run_tool(http, tool, q)
            await rs._ca.run(w['task'], ask, pages, wait_human, names, feeless)
        finally:
            for k_, pg in enumerate(pages):   # 🖼 the last page stays on its window after the task (owner 2026-10-31: "always show the last page they were on")
                try:
                    jpg_ = await rs.asyncio.wait_for(rs._vv.visitor_frame(pg, getattr(pg, 'url', '') or ''), 12) if getattr(pg, 'live', False) else None
                    if jpg_ and jpg_ != rs._vv.blank_jpg():   # 🔒 a private page never becomes a public resting monitor
                        rs._SHOTS[(cat_id, k_)] = (rs.time.time(), jpg_)
                        rs._last_put(cat_id, rs._slot_of(cat_now, models[k_] if k_ < len(models) else ''), jpg_)   # 🖼 its model's monitor idles on this page (kept on disk)
                except Exception:   # noqa: BLE001 — a missing last frame never blocks closing the browser
                    pass
                await pg.close()
            for s_ in sessions:
                if s_.get('warm'):
                    (rs._WARM.get(cat_id) or {}).pop('busy', None)
                    continue
                await rs._cb.close_session(http, env, s_)
            for x_ in (w.get('task') or {}).get('windows') or []:   # 🧭 the book learns which sites a window really read (blocked ones were filed as they happened)
                if str(x_.get('url') or '').startswith('http') and x_.get('status') == 'done':
                    rs._src_note(x_['url'], True)
            rs._sbrain.end_run(w.get('task') or {}, stok_, pages)
            w['pages'] = [None] * len(models)
            if (w.get('task') or {}).get('pow'):
                try:
                    await rs._pow_price(http, w['task'])
                except Exception as e:   # noqa: BLE001 — no price = filed ungraded, never a broken desk
                    print(f'[pow] {cat_id}: {str(e)[:120]}')
            for x_ in (w.get('task') or {}).get('windows') or []:   # a stopped round's browser is closed: its window must not claim it still works ("Session not found")
                if x_.get('status') == 'working':
                    x_['status'] = 'done'
            w['done'] = True


async def _hard_stop(w, grace=2.0):
    """■ Stop means stop (owner 2026-10-31: "the stop btn not stopping them"): the flag is only read between steps, so a model call or page load
    still in flight is cancelled after `grace` s — pages + cloud sessions still close in _work_run's finally, the $ spent so far is still charged."""
    rs = _rs()
    await rs.asyncio.sleep(grace)
    r = w.get('runner'); t = w.get('task') or {}
    if w.get('done') or not r or r.done():
        return
    t.update(status='stopped', why=t.get('why') or 'stopped by you')
    for win in t.get('windows') or []:
        if win.get('status') != 'done':
            win['status'] = 'stopped'
    r.cancel()


def _job_tree(t):
    """🗂 One request as a tree: the request → each mind (its job, 3-step plan, its steps, its answer) → the final answer."""
    rs = _rs()
    return {'id': t.get('id'), 'at': round(rs.time.time()), 'proof': t.get('proofKind') or ('pow' if t.get('pow') or t.get('pows') else None), 'request': str(t.get('text') or '')[:400], 'status': t.get('status'), 'cost': round(float(t.get('cost') or 0), 4),
            'answer': str(t.get('answer') or '')[:1200], 'minds': [{'model': str(w.get('model') or '').split('/')[-1][:30], 'job': rs._ca.job_label(w.get('goal')), 'plan': list(w.get('plan') or [])[:3],
            'steps': [{'a': x.get('action'), 't': str(x.get('thought') or '')[:90], 'd': str(x.get('detail') or '')[:90]} for x in (w.get('steps') or [])[-24:]],
            'answer': str(w.get('answer') or '')[:400], 'cost': round(float(w.get('cost') or 0), 5)} for w in t.get('windows') or [] if w.get('goal')]}


def _job_memory(cat):
    """🧠 A 👍 / 👎 on a request becomes memory for BOTH minds (they read it on their next task) — written by the engine, the store's one writer."""
    rs = _rs()
    rates = cat.get('jobRates') or {}; b = cat['brainsCfg']
    for j in cat.get('jobs') or []:
        r = rates.get(j.get('id'))
        if r not in ('up', 'down') or j.get('rate') == r:
            continue
        j['rate'] = r
        line = (f"👍 the owner APPROVED: \"{j['request'][:90]}\" → {j['answer'][:110]} — do it like this again" if r == 'up' else
                f"👎 the owner REJECTED: \"{j['request'][:90]}\" → {j['answer'][:90]} — do it differently next time")
        for m in b.get('brains') or []:
            mc_ = b.setdefault('minds', {}); mc_[m] = ((mc_.get(m) or []) + [{'at': rs.time.time(), 'text': line[:240]}])[-rs._ca.MIND_CLOUD_MAX:]
        b['cloud'] = ((b.get('cloud') or []) + [{'at': rs.time.time(), 'word': 'APPROVED' if r == 'up' else 'REJECTED', 'sym': '', 'text': line[:240], 'by': ['you']}])[-rs._lc.CLOUD_MAX:]


def _work_settle(store):
    """The engine's pass: a finished task's $ is charged to the cat's credit and its question + answer join the cat's chat (one writer)."""
    rs = _rs()
    for cid, w in list(rs._WORK.items()):
        if not w.get('done') or w.get('settled'):
            continue
        cat = store['cats'].get(cid)
        t = w.get('task') or {}
        if cat:
            cat.pop('workNow', None)
        if cat and cat.get('brainsCfg'):
            cat['artifacts'] = (list(cat.get('artifacts') or []) + t.get('artifacts', []))[-30:]
            cat['refusals'] = (list(cat.get('refusals') or []) + [{'at': rs.time.time(), 'why': x} for x in t.get('refusals', [])])[-100:]
            if not rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR):   # its owner's own key pays OpenRouter directly — no FEELESS credit
                rs._lc.charge(cat['brainsCfg'], max(0.0, t.get('cost') or 0))   # every paid call consumes its bought model budget, including SingIt paid from its wallet
            if t.get('watch'):   # 👁 Watch a Wallet: its answer files as a folder too
                cat['watchFolders'] = (list(cat.get('watchFolders') or []) + [rs._ac.watch_folder(t, rs.time.time(), int(((cat.get('watchFolders') or [{}])[-1]).get('n') or 0) + 1)])[-rs._ac.WATCH_KEEP:]
            if t.get('pow'):   # ⛏ a Colony PoW: filed (cell + cabinet), no flat fee, never a chat line you did not type
                rs._pow_settle(cat, t, rs.time.time())
            elif t.get('status') == 'done' and not t.get('proofRead'):   # 🤖 the flat fee for anything that is not a trade
                cat['feesDue'] = (list(cat.get('feesDue') or []) + [{'key': f"task-{t.get('id')}"}])[-20:]
            for lg_ in t.get('logins') or []:   # 🔐 every sign-up's password → sealed in its vault, then gone from memory
                try:
                    rs._cv.put_login(cat, lg_.get('site'), lg_.get('user'), lg_.get('pw'), data_dir=rs.DATA_DIR)
                    rs.keep_owned(cat)   # 🔐 a login it made survives the next save like one you typed
                except (ValueError, RuntimeError):
                    pass
            t['logins'] = []
            for site_u in t.get('vaultUsed') or []:   # 🔐 the audit line: its windows signed in with a saved login
                rs.vault_log(cat, 'used', site_u)
            if t.get('vaultUsed'):
                rs.keep_owned(cat)
            for md_ in t.get('media') or []:
                try:
                    rs._cv.add_media(cat, md_.get('url'), md_.get('title'))
                except ValueError:
                    pass
            for w_ in t.get('windows') or []:   # ☁ each mind's best notes → its OWN cloud
                if w_.get('best'):
                    mc_ = cat['brainsCfg'].setdefault('minds', {})
                    mc_[w_['model']] = ((mc_.get(w_['model']) or []) + [{'at': rs.time.time(), 'text': str(x)[:240]} for x in w_['best'] if not rs._cp.thinking_leak(x)])[-rs._ca.MIND_CLOUD_MAX:]
                    w_['best'] = []
            for x_ in (t.get('filed') or [])[-12:]:   # 📥 what its windows read + noted while browsing → the cabinet, with where it came from
                cat['brainsCfg']['cloud'] = ((cat['brainsCfg'].get('cloud') or []) + [{'at': rs.time.time(), 'word': 'FILED', 'sym': '', 'text': f"📥 {x_.get('site')}: {x_.get('text')}"[:240], 'by': ['browser']}])[-rs._lc.CLOUD_MAX:]
            for k_ in [k_ for k_ in t.get('keep') or [] if not rs._cp.thinking_leak(k_)]:   # ☁ the best of both scratch pads → its main cloud (the rest was thrown away; never a mind's private thinking)
                cat['brainsCfg']['cloud'] = ((cat['brainsCfg'].get('cloud') or []) + [{'at': rs.time.time(), 'word': 'KEEP', 'sym': '', 'text': str(k_)[:240], 'by': ['both']}])[-rs._lc.CLOUD_MAX:]
            if t.get('siteTrade'):
                rs._site_trade_filed(cat, t)
            cat['chat'] = list(cat.get('chat') or []) if t.get('pow') or t.get('proofRead') else (list(cat.get('chat') or []) + ([] if t.get('youSaid') else [{'by': 'you', 'text': t.get('text'), 'at': w.get('at')}]) + [
                           {'by': 'cats', 'text': (f"💳 Paid ${t.get('walletPaid'):.4f} from its wallet: " if t.get('walletPaid') else '') + ("🛟 Backup model, free (OpenRouter has no credit): " if t.get('backup') else '') + (t.get('answer') or f"({t.get('status')}: {t.get('why') or 'no answer'})"), 'at': rs.time.time(), 'cost': t.get('cost'), 'fast': t.get('fast'), 'tid': t.get('id')}])[-rs.CHAT_KEEP:]
            cat['jobs'] = (list(cat.get('jobs') or []) + [rs._job_tree(t)])[-rs.JOBS_KEEP:]   # 🗂 the exact log tree of every request (owner 2026-11-01), AGT-9: a proof's own research jobs too, tagged with its kind
        if cat and cat.get('brainsCfg'):
            rs._job_memory(cat)
        if cat and t.get('parked'):   # ⏸ filed to come back to when you are back (desk: Resume / Drop)
            cat['workParked'] = (list(cat.get('workParked') or []) + [{'at': rs.time.time(), 'text': t.get('text'), 'why': p_.get('why'), 'url': p_.get('url')} for p_ in t['parked']])[-rs.HANDOFF_MAX:]
        w['settled'] = True
        # 🏇 let it go: the next queued ask starts on its own (a stopped task pauses the queue — you stopped it for a reason; a parked one does not)
        if cat and cat.get('workGo') and cat.get('workQueue') and t.get('status') != 'stopped' and rs._work_live(cat) and rs._lc.can_ask(cat.get('brainsCfg') or {}):
            if rs.day_left(cat) is None or rs.day_left(cat) > 0:   # at its daily $ limit the queue waits
                nxt = cat['workQueue'].pop(0)
                rs._work_start(cid, cat, nxt.get('text'), nxt.get('to'), nxt.get('files'))


async def _agent_pass(store):
    """🏇 Agent trades (agent_trade.py): every REAL cat with its own wallet settles what is in flight and sends its next proposal — inside this
    loop's own load → save, so no other writer races it. A failure is logged and never stops the engine."""
    rs = _rs()
    key = rs.os.environ.get('CROSSMINT_API_KEY', '').strip()
    cats = [c for c in store['cats'].values() if (c.get('agentWallet') or {}).get('address') and rs._real.is_real(c) and not c.get('revoked')]
    cats = [c for c in cats if key or (c.get('agentWallet') or {}).get('provider') == 'circle']   # a Circle wallet needs no Crossmint key
    if not cats:
        return
    now = rs.time.time()
    async with rs.httpx.AsyncClient(timeout=25) as http_a:
        for c in cats:
            try:
                for w_ in await rs._at.run(http_a, key, c, now):
                    rs._log_event(store, c, 'TRADE', f"{c.get('name')}: {w_}")
                await rs._agent_fees(http_a, c, now)
            except Exception as exc:
                print('agent pass', c.get('id'), exc)


def _trade_usd(cat, row, px):
    """A trade's size in dollars. A sell is sized by what the coins cost, since the fill comes back later."""
    rs = _rs()
    if row.get('side') == 'buy':
        return rs._num(row.get('sol')) * px
    cost = next((rs._num(t.get('sol')) for t in cat.get('agentTx') or [] if t.get('side') == 'buy' and t.get('mint') == row.get('mint') and t.get('status') == 'success'), 0)
    return cost * min(1.0, rs._num(row.get('fraction')) or 1.0) * px


async def _agent_fees(http, cat, now):
    """🤖 Agent fees to the Collective: a % per trade that landed, one flat per finished task. A wallet that can't pay yet is asked again later; the key means never twice."""
    rs = _rs()
    w_ = cat.get('agentWallet') or {}
    if w_.get('circleAcct') != 'agent' or now - float(cat.get('feeTry') or 0) < 120:
        return
    due = [('trade', t.get('key') or t.get('id'), t) for t in cat.get('agentTx') or [] if t.get('status') == 'success' and not t.get('feeDone')]
    px = await rs._pool_px(http)
    if not px:
        return
    due += [('other', x['key'], x) for x in cat.get('feesDue') or []]
    for kind, key, row in due[:3]:
        r = await http.post('http://127.0.0.1:5077/api/reputation/internal/agent-fee', headers=rs._internal_headers(), timeout=30,
                            json={'catId': cat['id'], 'walletId': w_.get('circleId'), 'address': w_.get('address'), 'owner': w_.get('owner'), 'kind': kind, 'key': f'fee-{key}', 'usd': rs._trade_usd(cat, row, px) if kind == 'trade' else 0})
        if r.status_code != 200:
            cat['feeTry'] = now
            return
        if kind == 'trade':
            row['feeDone'] = True
        else:
            cat['feesDue'] = [x for x in cat['feesDue'] if x['key'] != key]


async def _engine_loop():
    rs = _rs()
    full_at = 0.0
    while True:
        try:
            store = rs._load()
            hot_ = any(((c.get('powRun') or {}).get('folder') or {}).get('phase') in ('buy', 'watch', 'research', 'decide', 'sell', 'sell_wait') for c in store['cats'].values())
            if rs.time.time() - full_at < rs.TICK_SECONDS and hot_:   # ⛏ a folder holds a coin: a LIGHT pass every 5 s (its live checks + its wallet's sends), the market scan stays at 20 s
                await rs._agent_pass(store); await rs._pow2_pass(store); rs._work_settle(store); rs._save(store)
                await rs.asyncio.sleep(rs._pow.HOT_TICK_S); continue
            full_at = rs.time.time()
            rs._migrate(store)
            rs._apply_overrides(store)
            running = rs._engine_cats(store)   # 🛑 Fee has no engine (owner 2026-11-14)
            if running:
                await rs.run_engine(store, running)
            await rs._agent_pass(store)
            await rs._pow2_pass(store)   # ⛏ the Colony PoW loop of every trader agent (the engine is the store's one writer)
            try:
                async with rs.httpx.AsyncClient(timeout=15) as http_c:
                    await rs._pool_pass(http_c, store, rs.time.time()); await rs._collect_pass(http_c, store, rs.time.time()); await rs._convo_pass(http_c, store, rs.time.time()); await rs._pob_grade_pass(http_c, store, rs.time.time())
            except Exception as e:   # noqa: BLE001 — the Collective never stops the engine
                print(f'[collective] {str(e)[:160]}')
            rs._work_settle(store)
            rs._review_apply(store)   # 🧑‍⚖️ OSSY and G4's verdicts land on their folders
            rs._db_grow(store)   # 🗄 every closed proof becomes a sealed row in its agent's own database
            rs._pot_alert_pass(store)   # ✅ AGX-10: a proof under 1x → one 'Fix first' line in its chat + a redo waiting for Approve (no model call)
            if rs.time.time() - store.get('lastWallPost', 0) >= rs.WALL_EVERY:
                store['lastWallPost'] = rs.time.time()   # claim the slot first; a failed post retries next window
                await rs._meta_post(store)
            rs._save(store)
        except Exception as exc:  # keep the loop alive; surface in logs
            print('engine error', exc)
        try:
            await rs.asyncio.wait_for(rs._POW_WAKE.wait(), timeout=rs._pow.HOT_TICK_S if rs._any_hot() else rs.TICK_SECONDS)
        except rs.asyncio.TimeoutError:
            pass
        finally:
            rs._POW_WAKE.clear()


def _score(cat):
    return {
        'id': cat['id'], 'name': cat['name'], 'avatar': cat['avatar'], 'level': cat['level'],
        'strategyLabel': cat['strategyLabel'], 'realizedPnlSol': cat['realizedPnlSol'],
        'volumeSol': cat.get('volumeSol', 0), 'winRate': cat.get('winRate'), 'isLeader': bool(cat.get('isLeader')),
        'openPositions': len(cat.get('positions', [])), 'trades': cat.get('wins', 0) + cat.get('losses', 0),
        # 🏆 the board + live activity draw each agent as it looks (owner 2026-10-30): its look, its desk colour, live or not, what kind — nothing private
        'look': cat.get('look'), 'skin': cat.get('skin'), 'status': cat.get('status'), 'kind': (cat.get('brainsCfg') or {}).get('kind') or 'rules',
        'brains': [str(m).split('/')[-1] for m in ((cat.get('brainsCfg') or {}).get('brains') or [])][:2],
        # 📸 its recent snapshot for the board cards: the last 24 points of its P/L curve + the coin it is on / just left
        'curve': [round(float(x.get('value') or 0), 6) for x in (cat.get('pnlHistory') or [])[-24:]],
        'coin': ((cat.get('positions') or [{}])[0].get('symbol') if cat.get('positions') else ((cat.get('exits') or [{}])[-1].get('symbol') if cat.get('exits') else None)),
    }

