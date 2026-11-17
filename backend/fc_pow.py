"""🧹 Proof-of-work engine — moved whole out of feecat_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches feecat_service still
reaches it, and every function here is still reachable on feecat_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import feecat_service
    return feecat_service


def _pow_ver(cat):
    """Cheap owner desk version; a DNA or memory append updates PoI without full-folder polling."""
    rs = _rs()
    fs_ = cat.get('powFolders') or []; pf_ = cat.get('popFolders') or []
    base = f"{len(fs_)}:{(fs_[-1] if fs_ else {}).get('id', '')}:{sum(1 for x in fs_ if x.get('kept'))}:{sum(len(x.get('hidden') or []) for x in fs_)}"
    return f"{base}:{rs._poi.version(rs.DATA_DIR, cat['id'])}:{len(pf_)}:{(pf_[-1] if pf_ else {}).get('id', '')}:{sum(1 for x in pf_ if x.get('kept'))}"


def card_link(cat, provider, address, now):
    """💳 The digital card its owner signed up for, and the card's own top-up address, as the owner pasted it. Never a card number or an ID. No money moves. → the link, or ValueError."""
    rs = _rs()
    if provider not in rs.CARD_PROVIDERS:
        raise ValueError('Pick one of the card providers.')
    if not rs._topup.valid_address(str(address or '').strip()):
        raise ValueError('That is not a Solana address. Paste the top-up address the card gave you, never a card number.')
    cat['cardLink'] = {'provider': provider, 'address': str(address).strip(), 'at': round(now)}
    return cat['cardLink']


def _sicario_paused(cat):
    rs = _rs()
    return rs.SICARIO_PAUSED and cat.get('handle') == 'sicarios'


def _pow2_on(cat):
    rs = _rs()
    b = cat.get('brainsCfg') or {}
    asked_ = cat.get('id') in rs._POW_WANT or (cat.get('powRun') or {}).get('folder', {}).get('asked')
    if rs._sicario_paused(cat) and not asked_:
        return False
    if cat.get('id') in rs._POW_WANT or (cat.get('powRun') or {}).get('folder', {}).get('asked'):   # you asked: any agent kind, once
        return bool(b.get('brains')) and not cat.get('isLeader') and not cat.get('revoked')
    return (b.get('kind') or 'trading') == 'trading' and bool(b.get('brains')) and not cat.get('isLeader') and not cat.get('revoked') and not cat.get('needsTopup') \
        and cat.get('status') == 'running' and (cat.get('powLoop') or {}).get('on', True)


async def _pow2_ask(cat, i, sys_, user_, max_tokens=180, cost_to=None, kind=None):
    """One small call to mind i (inside its $ limits), from this proof kind's own minds when it has a pair (COL-2). → text ('' when nothing answered)."""
    rs = _rs()
    box_ = cost_to if cost_to is not None else (cat.get('powRun') or {}).get('folder') or {}
    kind = kind or (box_.get('proof') if cost_to is not None else 'pow')   # a PoP / PoB names itself in its box; no box = the open PoW folder
    b_ = cat['brainsCfg']; ms = rs._lc.minds_for(b_, kind)
    if not ms:   # ⛏ a folder's calls skip the daily $ limit until the trade closes (owner 2026-11-01)
        return ''
    own_ = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
    reply_ = ''
    for try_ in range(2):   # 🔁 a mind that comes back blank is asked once more, with room to answer (owner 2026-11-16: both minds work on every filing)
        tok_ = rs._CALL_CTX.set({'kind': kind, 'ref': box_.get('ref') or box_.get('id'), 'minds': ms[:2], 'mind': min(i, len(ms) - 1)}) if kind else None
        user_now_ = user_[:3500] + ('\nYour last reply was empty. Answer now, briefly, in the format asked.' if try_ else '')
        try:
            reply_, usd_, via_ = await rs._think(cat, ms[min(i, len(ms) - 1)], [{'role': 'system', 'content': sys_}, {'role': 'user', 'content': user_now_}], own_, None, max_tokens * (2 if try_ else 1))
        except Exception:   # noqa: BLE001 — no model now: one more try, then it tries again next tick
            reply_, usd_ = '', 0
        finally:
            if tok_:
                rs._CALL_CTX.reset(tok_)
        if not own_ and usd_:
            rs._lc.charge(b_, usd_)   # SingIt and OpenRouter both consume the agent's bought model budget
        elif usd_:
            day_ = rs.time.strftime('%Y-%m-%d', rs.time.gmtime()); b_['daySpend'] = {day_: round((b_.get('daySpend') or {}).get(day_, 0) + float(usd_), 6)}
        rs._pow2_cost(cost_to if cost_to is not None else (cat.get('powRun') or {}).get('folder'), i, usd_)   # a PoP's calls are the PoP's, never the open PoW folder's
        if str(reply_ or '').strip():
            break
    return str(reply_ or '')


def _pow2_cost(f, mind_i, usd):
    """💲 Every $ a folder costs (each mind's calls + its research rounds) — shown on the monitors and kept in the folder."""
    if not f or not usd:
        return
    f['cost'] = round(float(f.get('cost') or 0) + float(usd), 6)
    sp_ = f.setdefault('spend', {}); sp_[str(mind_i)] = round(float(sp_.get(str(mind_i)) or 0) + float(usd), 6)


async def _eco_pools(http, addrs=None):
    """Live pools for a PoEco market call: the named pairs when grading, else DexScreener's boosted Solana set. Never GeckoTerminal."""
    rs = _rs()
    try:
        if addrs:
            r = await http.get(f"https://api.dexscreener.com/latest/dex/pairs/solana/{','.join(addrs[:30])}", timeout=12)
            return rs._ecm.rows_of((r.json() or {}).get('pairs'))
        boosts = [x['tokenAddress'] for x in (await http.get('https://api.dexscreener.com/token-boosts/top/v1', timeout=12)).json() if x.get('chainId') == 'solana'][:12]
        pairs = (await http.get(f"https://api.dexscreener.com/tokens/v1/solana/{','.join(boosts)}", timeout=12)).json() if boosts else []
        return rs._ecm.rows_of(pairs)
    except (rs.httpx.HTTPError, ValueError, KeyError, TypeError):
        return []


async def _pow2_dex(http):
    """DexScreener's most-boosted Solana coins with their deepest pool (the folder's 'popular dex' coin)."""
    rs = _rs()
    try:
        boosts = [x['tokenAddress'] for x in (await http.get('https://api.dexscreener.com/token-boosts/top/v1', timeout=12)).json() if x.get('chainId') == 'solana'][:12]
        pairs = (await http.get(f"https://api.dexscreener.com/tokens/v1/solana/{','.join(boosts)}", timeout=12)).json() if boosts else []
    except (rs.httpx.HTTPError, ValueError, KeyError, TypeError):
        return []
    best = {}
    for p in pairs or []:
        m = (p.get('baseToken') or {}).get('address'); liq = rs._num((p.get('liquidity') or {}).get('usd'))
        if m and rs._ct.real_coin(p) and liq > rs._num(((best.get(m) or {}).get('liquidity') or {}).get('usd')):
            best[m] = p
    return [{'mint': m, 'pair': p.get('pairAddress'), 'sym': (p.get('baseToken') or {}).get('symbol'), 'liq': rs._num((p.get('liquidity') or {}).get('usd')),
             'mc': rs._num(p.get('marketCap') or p.get('fdv')), 'ch': (p.get('priceChange') or {}).get('h1')} for m, p in best.items()]


def _pow2_plan_round(cat, f, coin, mind_i, now, avoid=()):
    """One mind's plan for one coin: its known facts, its site order. `avoid` = sites its partner opens at the same moment."""
    rs = _rs()
    rp = {**rs._pow.new({'mint': coin['mint'], 'pair': coin['pair'], 'sym': coin['sym']}, now), 'cat': cat['id'], 'mind': mind_i, 'folder': f['id'], 'base': int(f.get('base') or 0), 'plan': (f.get('plans') or {}).get(coin['mint']),
          'used': list(((f.get('usedBy') or {}).get(coin['mint'])) or []),
          'known': [x['label'] for x in (f.get('vitals') or {}).get(coin['mint']) or [] if x.get('verified')]}   # only verified facts are inherited
    archive_ = rs._pow_archive_rows()
    prior_ = [r for r in rs._pow.archive_find(archive_, coin['mint'], 40) if r.get('kind') == 'research']
    blocked_sites_, blocked_steps_ = rs._pow.track_memory(archive_, cat['id'], coin['mint'])
    reused_ = rs._pow.reusable_facts(prior_, coin['mint'], now)
    if reused_:
        f.setdefault('vitals', {})[coin['mint']] = rs._pow.merge_vitals((f.get('vitals') or {}).get(coin['mint']), reused_)
    rp['known'] = sorted(set(rp['known']) | {x['label'] for x in reused_})
    own_site_ = rs._proof_site(cat, 'pow')
    if rs._pl.pow_note(cat.get('powFolders')):   # 🔁 the Proof Loop: it studies its last proofs before this one
        rp['plan'] = f"{rp.get('plan') or ''}{rs._pl.pow_note(cat.get('powFolders'))}".strip()
    rp['plan'] = f"{rp.get('plan') or ''}{rs._foot.note('pow', cat.get('powFolders'), mind_i)}{rs._convo(cat)}".strip()
    extra_ = rs._print.note(rs._print.build(cat, now)) + ' ' + rs._edge.checklist()   # 🧬 its own record + 📚 the case files. It studies them; every guard stays
    rp['plan'] = f"{rp.get('plan') or ''} {extra_}".strip()
    if own_site_:   # 🔎 "file a pump pow": the owner's scanned, signed-in site goes first
        rp.update(ownerSite=own_site_['url'], plan=f"{rp.get('plan') or ''}{rs._ss.note_for(own_site_, 'pow')}".strip())
    rp['reusedSites'] = sorted({x['site'] for x in reused_})
    rp['required'] = ['solscan.io'] + (['pump.fun'] if coin.get('src') == 'pump' else [])
    same_coin_sites_ = {h for row in prior_ for h in row.get('sites') or []}
    required_fresh_ = set(rp['required']) - same_coin_sites_ - set(rp['reusedSites'])
    rp['used'] = sorted((set(rp['used']) | blocked_sites_ | set(rp['reusedSites'])) - required_fresh_)
    rp['priorSteps'] = sorted(blocked_steps_)
    rp['prior'] = rs._pow.archive_brief(rs._pow.archive_find(archive_, coin['mint']))
    recent_, _ = rs._pow.site_memory(cat.get('powFolders'))
    try:
        own_dna_ = rs._poi.load(rs.DATA_DIR, cat['id'], mind_i)
        fp_ = rs._poi.fingerprint(own_dna_, mind_i)
        rp['dna'] = {'generations': fp_.get('generations'), 'states': rs._poi.evolution(own_dna_)['states']}
        other_dna_ = rs._poi.load(rs.DATA_DIR, cat['id'], 1 - mind_i)
        inherited_ = {h for h, state in rs._poi.evolution(other_dna_)['states'].items() if state == 'promoted'}
        retired_ = {h for h, state in rp['dna']['states'].items() if state == 'retired'}
    except (OSError, ValueError) as e:
        print(f'[poi] Research DNA unavailable: {e}'); fp_, inherited_, retired_ = {'coverage': {}}, set(), set()
    excluded_ = recent_ | blocked_sites_ | set(rp['reusedSites']) | set(avoid) | {h for v in (f.get('usedBy') or {}).values() for h in v or []}
    ranked_ = rs._pow.ranked_sources(excluded_, rs._src_book(), fp_.get('coverage'), now, inherited_, retired_)
    # A source visited for another coin is still a required verification target
    # for this mint. If rotation exhausts the catalog, reuse the least spent
    # available sites rather than filing a coin with no browser investigation.
    for host in rp['required']:
        if host in required_fresh_ and host in rs._pow.HOSTS and host not in ranked_:
            ranked_.insert(0, host)
    if len(ranked_) < 3:
        fallback_ = rs._pow.ranked_sources(blocked_sites_ | set(rp['reusedSites']), rs._src_book(), fp_.get('coverage'), now, inherited_, retired_)
        ranked_ += [host for host in fallback_ if host not in ranked_][:3 - len(ranked_)]
    rp['inherited'] = sorted(inherited_ & set(ranked_))
    rp['order'] = [h for h in rp['required'] if h in ranked_] + [h for h in ranked_ if h not in rp['required']]
    rp['order'] = rs._book.rank(cat.get('siteBook'), 'pow', rp['order'], keep=rp['required'])   # 📚 the owner's site book: their order first, off sites never
    return rp


def _pow2_research(cat, f, coin, mind_i, now):
    """🔎 One research round on ONE coin in mind_i's window (its own browser), with the watcher's chart read handed over. → True when it started."""
    rs = _rs()
    w_ = rs._WORK.get(cat['id'])
    if w_ and not w_.get('done'):
        return False
    rp = rs._pow2_plan_round(cat, f, coin, mind_i, now)
    try:
        rs._work_start(cat['id'], cat, rs._pow.goal(rp), str(int(f.get('base') or 0) + mind_i), None, rp)
    except rs.HTTPException:
        return False
    t_new = rs._WORK[cat['id']]['task']
    ch_ = (f.get('charts') or {}).get(coin['mint']) or []
    t_new['handoffs'] = [{'from': 'watcher', 'text': f"chart watcher on ${coin['sym']}: {rs._pow.chart_line(ch_)}"}] + ([{'from': 'archive', 'text': f"{rp['prior']} — do NOT repeat it: new sites, new facts"}] if rp.get('prior') else [])
    t_new['powPlan'] = list(f.get('plan') or [])
    f.update(rMint=coin['mint'], rMind=mind_i, researchAt=round(now))
    return True


def _pow_archive_add(row):
    rs = _rs()
    try:
        stored = {'v': 2, 'cat': row['cat'], 'sealed': rs._ck.seal(rs.json.dumps(row, separators=(',', ':')), row['cat'])} if row.get('cat') else row
        with rs.POW_ARCHIVE.open('a') as fh:
            fh.write(rs.json.dumps(stored, separators=(',', ':')) + '\n')
        rs._POW_ARCHIVE_CACHE['key'] = None
    except OSError as e:
        print(f'[pow archive] not kept: {e}')


def _pow_archive_rows():
    rs = _rs()
    try:
        stat = rs.POW_ARCHIVE.stat()
        key = (str(rs.POW_ARCHIVE), stat.st_mtime_ns, stat.st_size)
        if rs._POW_ARCHIVE_CACHE['key'] != key:
            rows = []
            for line in rs.POW_ARCHIVE.read_text().splitlines():
                if not line.strip():
                    continue
                raw = rs.json.loads(line)
                if raw.get('sealed'):
                    try:
                        raw = rs.json.loads(rs._ck.unseal(raw['sealed'], raw['cat'], data_dir=rs.DATA_DIR))
                    except Exception:
                        continue  # tampered/unreadable evidence is never trusted
                rows.append(raw)
            rs._POW_ARCHIVE_CACHE.update(key=key, rows=rows)
        return rs._POW_ARCHIVE_CACHE['rows']
    except (OSError, ValueError):
        return []


def _pow2_collect(f, t_, who, now, cat=None):
    """📁 A finished research round → that coin's folder: its vitals, its 2-per-site snapshots, the sites it used (the next round goes elsewhere)."""
    rs = _rs()
    pw_ = t_['pow']; m_ = pw_.get('mint'); pub_ = rs._pow.public(pw_)
    if not pw_.get('costed'):   # 💲 the research round's own browsing cost
        pw_['costed'] = True; rs._pow2_cost(f, int(f.get('base') or 0) + int(pw_.get('mind') or 0), float(t_.get('cost') or 0))
    vit_ = f.setdefault('vitals', {}); vit_[m_] = rs._pow.merge_vitals(vit_.get(m_), pub_['pulls'])   # 🧹 one row per fact, never the same fact twice
    f.setdefault('evidenceMetrics', {})[m_] = {**rs._pow.research_metrics(pw_, t_.get('cost'), now), 'openSec': t_.get('openSec'), 'modelSec': round(sum(float(x.get('modelSec') or 0) for x in t_.get('windows') or []), 1), 'modelCalls': sum(int(x.get('modelCalls') or 0) for x in t_.get('windows') or [])}   # ⏱ open · model · the rest is the browser
    if m_ == f.get('mint') and f.get('entry'):
        f['research'] = rs._pow.merge_vitals(f.get('research'), pub_['pulls'])
    f.setdefault('moves', {}).setdefault(m_, {}).update(pub_.get('moves') or {})   # 🎲 each site's random moves, kept
    ub_ = f.setdefault('usedBy', {}); ub_[m_] = sorted(set(ub_.get(m_) or []) | set((pw_.get('sites') or {}).keys()) | set(pw_.get('walled') or []))
    for sh_ in [x for x in (pw_.pop('_shots', None) or []) if x['site'] not in (pw_.get('walled') or [])]:   # 📸 its snapshots → the coin's folder, on disk
        name_ = f"{m_[:6].lower()}_r{f.get('rounds') or 0}_{rs.re.sub(r'[^a-z0-9.]', '', sh_['site'])}_{sh_['n']}.jpg"
        try:
            d_ = rs.POWSHOTS_DIR / rs.re.sub(r'[^a-z0-9]', '', f['id']); d_.mkdir(parents=True, exist_ok=True); (d_ / name_).write_bytes(rs._ck.seal_bytes(sh_['jpg'], cat['id']) if cat and any(s_ in name_ for s_ in (cat.get('siteSessions') or {})) else sh_['jpg'])
            f['shots'] = ((f.get('shots') or []) + [{'mint': m_, 'site': sh_['site'], 'n': sh_['n'], 'at': sh_['at'], 'file': name_, 'round': f.get('rounds') or 0, **({'found': sh_['found'], 'sha': sh_.get('sha')} if sh_.get('found') else {})}])[-60:]
        except OSError as e:
            print(f'[pow2] snapshot not kept: {e}')
    steps_ = list(dict.fromkeys(rs._pow.step_hash(sig) for w in t_.get('windows') or [] for sig in w.get('sigs') or []))
    rs._pow_archive_add(rs._pow.archive_row('research', (pw_.get('cat') or ''), f, {'mint': m_, 'sym': pw_.get('sym')}, now, by=who, mind=pw_.get('mind'), plan=pw_.get('plan'),
                                      vitals=pub_['pulls'], metrics=f['evidenceMetrics'][m_], sites=sorted((pw_.get('sites') or {}).keys()), steps=steps_, walled=list(pw_.get('walled') or []), call=pw_.get('call'), why=pw_.get('why'), strength=pub_.get('strength')))
    dna_row_ = None
    if pw_.get('cat'):
        try:
            dna_row_ = rs._poi.append(rs.DATA_DIR, pw_['cat'], int(pw_['mind']), f"{f['id']}:r{f.get('rounds') or 0}", m_, now,
                        pub_['pulls'], f['evidenceMetrics'][m_], steps_, (pw_.get('sites') or {}).keys())
        except (OSError, ValueError) as e:
            print(f'[poi] Research DNA not filed: {e}')
    f.setdefault('poiTrace', {})[m_] = {'mind': pw_.get('mind'), 'at': round(now), 'order': list(pw_.get('order') or [])[:12], 'required': list(pw_.get('required') or []), 'reused': list(pw_.get('reusedSites') or []),
                                        'inherited': list(pw_.get('inherited') or []), 'visited': sorted((pw_.get('sites') or {}).keys()), 'walled': list(pw_.get('walled') or []),
                                        'kernel': rs._kernel.fingerprint(), 'generation': (dna_row_ or {}).get('generation'), 'states': (pw_.get('dna') or {}).get('states') or {}}   # 🧬 how PoI shaped this round: the PoI child folder reads it (owner only, folder_public drops it)
    rs._pow2_say(f, who, f"${pw_.get('sym')} researched on {', '.join(sorted((pw_.get('sites') or {}).keys())) or 'no site'}: "
                      f"{' · '.join(x['label'] + ' ' + x['value'] for x in pub_['pulls'][:4]) or 'no vitals (' + (', '.join(pw_.get('walled') or []) + ' walled' if pw_.get('walled') else 'nothing it could read') + ')'}")
    f.pop('rMint', None)


def _pow2_research_pair(cat, f, coins, now):
    """🏇 Both minds research their OWN coin at once, each in its own browser (PoW #13: one at a time = 675 of its 888 s). → True when started."""
    rs = _rs()
    w_ = rs._WORK.get(cat['id'])
    if w_ and not w_.get('done'):
        return False
    a_ = rs._pow2_plan_round(cat, f, coins[0], 0, now)
    b_ = rs._pow2_plan_round(cat, f, coins[1], 1, now, avoid=(a_.get('order') or [])[:rs._pow.SITES_MAX])
    try:
        rs._work_start(cat['id'], cat, f"A: ${a_['sym']}\nB: ${b_['sym']}", None, None, a_, pows={0: a_, 1: b_})
    except rs.HTTPException:
        return False
    t_new = rs._WORK[cat['id']]['task']; t_new['powPlan'] = list(f.get('plan') or []); t_new['handoffs'] = []
    for i, (c, rp) in enumerate(zip(coins, (a_, b_))):
        ch_ = (f.get('charts') or {}).get(c['mint']) or []
        t_new['handoffs'] += [{'from': 'watcher', 'only': i, 'text': f"chart watcher on ${c['sym']}: {rs._pow.chart_line(ch_)}"}] + ([{'from': 'archive', 'only': i, 'text': f"{rp['prior']} — do NOT repeat it: new sites, new facts"}] if rp.get('prior') else [])
    f.update(rPair={'0': coins[0]['mint'], '1': coins[1]['mint']}, rMint=coins[0]['mint'], rMind=0, researchAt=round(now))
    return True


def _pow2_running(cat, f):
    """(task, its research is running now, it is this folder's) for the agent's current window."""
    rs = _rs()
    w_ = rs._WORK.get(cat['id']); t_ = (w_ or {}).get('task') or {}
    mine = (t_.get('pow') or {}).get('folder') == f['id'] and ((t_.get('pow') or {}).get('mint') == f.get('rMint') or bool(t_.get('pows') and f.get('rPair')))
    return w_, t_, mine and not (w_ or {}).get('done'), mine


def _any_hot():
    rs = _rs()
    try:
        return any(c.get('popRun') or c.get('popCard') or c.get('popRead') or c.get('pobRead') or ((c.get('powRun') or {}).get('folder') or {}).get('phase') in ('buy', 'watch', 'research', 'decide', 'sell', 'sell_wait') for c in rs._load()['cats'].values())
    except Exception:   # noqa: BLE001
        return False


def _pow2_approve(cat, pid):
    """⛏ A PoW folder's own order is pre-approved: the agent's wallet sends it in the engine's agent pass (agent_trade.wants: approved), through every server guard."""
    p_ = next((x for x in cat.get('proposals') or [] if x.get('id') == pid), None)
    if p_:
        p_.update(approved=True, by='pow')


def _pow2_say(f, who, text):
    rs = _rs()
    f['talk'] = (f.get('talk') or []) + [{'by': who, 'text': str(text)[:200], 'at': round(rs.time.time())}]
    f['talk'] = f['talk'][-24:]


async def _pow2_reconcile(http, cat, f, buy=None, sell=None):
    """Use the two confirmed wallet fills, including fees, before reporting net profit or a Colony obligation. `buy` / `sell` = rows with a
    `sig` (COL-25 relink); by default its own proposals."""
    rs = _rs()
    proposals = {p.get('id'): p for p in cat.get('proposals') or []}
    if buy is None:
        buy, sell = proposals.get(f.get('pid')) or {}, proposals.get(f.get('sellPid')) or {}
        if any(p.get('status') != 'done' for p in (buy, sell)):
            return False
    wallet = (cat.get('agentWallet') or {}).get('address')
    if not wallet or any(not (p or {}).get('sig') for p in (buy, sell)):
        return False
    try:
        txs = await rs.asyncio.gather(*(rs._crpc._rpc(http, 'getTransaction', [p['sig'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}], scan=False)
                                   for p in (buy, sell)))
        fills = [rs._fills.raw_fill(tx, wallet, f['mint']) for tx in txs]
    except (RuntimeError, ValueError, rs.httpx.HTTPError) as e:
        print(f'[pow2] fill reconciliation deferred: {str(e)[:100]}')
        return False
    if not fills[0] or not fills[1] or fills[0]['side'] != 'buy' or fills[1]['side'] != 'sell' or not fills[0]['cashSol'] or not fills[1]['cashSol']:
        return False
    f.update(buySig=buy['sig'], sellSig=sell['sig'], netPnlSol=round(fills[1]['cashSol'] - fills[0]['cashSol'], 9),
             settlementVerified=True, cashSpentSol=fills[0]['cashSol'], cashReturnedSol=fills[1]['cashSol'])
    return True


async def _pow2_relink(store):
    """🧾 COL-25 (found 2026-11-10): filed real PoWs lost their order ids and chain proof (pow.folder_public dropped them), so none was ever
    checked against the chain. Each one with its own buy and sell in the agent's transactions is read back from the chain once: P&L becomes
    the net of the two real fills, fees included, and the proof history files the change as a correction. Reads only; moves nothing."""
    rs = _rs()
    fixed = 0
    async with rs.httpx.AsyncClient(timeout=20) as http:
        for cid, c in (store.get('cats') or {}).items():
            for f in c.get('powFolders') or []:
                if not f.get('real') or f.get('settlementVerified') or (cid, f.get('id')) in rs._RELINKED:
                    continue
                rs._RELINKED.add((cid, f.get('id')))
                pair = rs._pow.match_sigs(f, c.get('agentTx'))
                if not pair:
                    continue
                if await rs._pow2_reconcile(http, c, f, pair[0], pair[1]):
                    f.update(pid=pair[0].get('pid'), sellPid=pair[1].get('pid'), sigsFrom='agent transactions, matched by coin and time')
                    f['pnlSol'] = f['netPnlSol']; f['pnlPct'] = round(100 * f['netPnlSol'] / f['cashSpentSol'], 2) if f.get('cashSpentSol') else None
                    fixed += 1
    return fixed


def _pow2_shadow_entry(f, prices, now):
    """Start same-time paper comparisons when the chosen buy actually fills."""
    rs = _rs()
    f['shadowEntry'] = {c['mint']: {'px': rs._num((prices.get(c['pair']) or {}).get('priceNative')), 'at': round(now)}
                        for c in f.get('coins') or [] if c.get('safe', True) and c.get('pair')}


async def _pow2_shadow_exit(http, f, now):
    rs = _rs()
    if not f.get('shadowEntry') or f.get('shadow') is not None:
        return
    alternatives = [c for c in f.get('coins') or [] if c.get('mint') != f.get('mint') and c.get('safe', True) and c.get('pair')]
    try:
        prices = await rs._pair_prices(http, [c['pair'] for c in alternatives]) if alternatives else {}
    except (rs.httpx.HTTPError, ValueError):
        prices = {}
    f['shadow'] = rs._pow.shadow_compare(f, {c['mint']: rs._num((prices.get(c['pair']) or {}).get('priceNative')) for c in alternatives}, now)


def _pow2_close(cat, f, why, now, exit_px=0.0):
    """⛏ The folder ends: its P/L (pool price, fees apart), the owner's files, a graded cell, the cabinet — and on a WIN with colonize on, the
    colony gets the folder + its share (paper never pays; a real win accrues pct % of the profit, sent by the owner's approval flow)."""
    rs = _rs()
    f.update(status='closed', why=why, soldAt=round(now), phase='done')
    if f.get('entry') and exit_px:
        f['exit'] = exit_px; f['pnlEstimatePct'] = round(rs._pow.pnl_pct(f['entry'], exit_px), 2)
        f['pnlEstimateSol'] = round(float(f.get('sol') or 0) * f['pnlEstimatePct'] / 100, 6)
    if f.get('real'):
        f['pnlSol'] = f.get('netPnlSol') if f.get('settlementVerified') else None
        f['pnlPct'] = round(100 * f['pnlSol'] / f['cashSpentSol'], 2) if f.get('settlementVerified') and f.get('cashSpentSol') else None
    elif f.get('pnlEstimateSol') is not None:
        f['pnlSol'], f['pnlPct'] = f['pnlEstimateSol'], f['pnlEstimatePct']
    if f.get('real') and f.get('settlementVerified') and (f.get('netPnlSol') or 0) > 0 and (cat.get('colonyShare') or {}).get('on'):
        rs._colony_share(cat, {'symbol': f.get('sym')}, f['netPnlSol'], f.get('sellSig'), {'kind': 'PoW', 'id': f.get('id'), 'name': f.get('name'), 'sym': f.get('sym'), 'pnlPct': f.get('pnlPct')})
        f['shared'] = (cat.get('colonyShare') or {}).get('pct')
    b_ = cat.setdefault('brainsCfg', {})
    f['grade'] = None if f.get('pnlPct') is None else ('good' if f['pnlPct'] > 0 else 'bad')
    for sh_ in f.get('shots') or []:   # 📸 the pick's snapshots become the trade's evidence: 👍 good / 👎 bad
        if f['grade'] and sh_.get('mint') == f.get('mint'):
            sh_['trade'] = f['grade']
    if f.get('pick'):   # 🗄 the outcome, filed forever beside the coin's research
        rs._pow_archive_add(rs._pow.archive_row('outcome', cat['id'], f, f['pick'], now, real=bool(f.get('real')), sol=f.get('sol'), tp=f.get('tp'), sl=f.get('sl'),
                                          pnlPct=f.get('pnlPct'), pnlSol=f.get('pnlSol'), why=why, bought=bool(f.get('entry'))))
    f['report'], md_ = rs._pow.report(f)   # 📋 every folder ends with its final report (in the folder + report.md on disk)
    try:
        d_ = rs.POWSHOTS_DIR / rs.re.sub(r'[^a-z0-9]', '', f['id']); d_.mkdir(parents=True, exist_ok=True); (d_ / 'report.md').write_text(md_)
    except OSError as e:
        print(f'[pow2] report not kept: {e}')
    cat['powFolders'] = rs._pow.trim_folders((cat.get('powFolders') or []) + [rs._pow.folder_public(f)])   # 📌 kept folders are never trimmed
    won = (f.get('pnlPct') or 0) > 0
    b_['cloud'] = ((b_.get('cloud') or []) + [{'at': now, 'word': 'WIN' if won else 'PoW', 'sym': f.get('sym') or '', 'by': ['pow'],
                    'text': f"⛏ {f['name']}: {('$' + f['sym']) if f.get('sym') else 'no buy'} — {why}" + (f" · {f['pnlPct']:+.1f}%" if f.get('pnlPct') is not None else '')}])[-rs._lc.CLOUD_MAX:]
    if f.get('pair') and f.get('entry'):   # graded like every call; the folder rides along (the colony's PoW feed shows it)
        cells = rs._hive_cells(); cells.append({'id': rs.uuid.uuid4().hex[:12], 'cat': cat['id'], 'name': str(cat.get('name') or 'agent')[:40], 'pair': f['pair'], 'mint': f.get('mint'),
                                             'sym': f.get('sym'), 'price': rs._num(f.get('entryUsd')), 'call': 'BUY', 'why': (f.get('why0') or why)[:200], 'at': f.get('boughtAt') or now,
                                             'usd': 0, 'epoch': rs._hv.epoch_of(now), 'folder': rs._pow.folder_public(f), 'won': won, 'colony': bool(won and rs._hive_on(cat))})
        if rs._num(f.get('entryUsd')) > 0:
            rs._hive_save(cells)
    run_ = cat.setdefault('powRun', {}); run_.pop('folder', None); run_['rested'] = now


def _order_wait(cat):
    """Who a real order waits on: its own wallet on auto, you on ASK ME, your wallet's signature when it has none of its own."""
    w_ = cat.get('agentWallet')
    return "waiting for your wallet's signature" if not w_ else 'its wallet is sending it' if w_.get('mode') == 'auto' else 'waiting for your OK'


async def _quick_answer(q):
    """⚡ A free command's reply. Read-only; a failed read says so."""
    rs = _rs()
    async with rs.httpx.AsyncClient(timeout=30) as http:
        if q['tool'] != 'check':
            return str((await rs._ct.run_tool(http, q['tool'], q['q']))[0])[:2400]
        read, coin = await rs._ct.run_tool(http, 'coin', q['q'])
        if not coin:
            return str(read)[:1200]
        pair = await rs._order_pair(http, coin.get('mint') or q['q'])
        if not pair:
            return f"🛑 It would NOT buy this: no pool it can trade.\n\n{str(read)[:700]}"
        ok_, why_ = rs._co.buy_guards(pair, rs.time.time() * 1000)
        safe_, swhy_, _cv = await rs._safety(http, pair) if ok_ else (False, '', 0)
        return f"{rs._ac.verdict(ok_, why_, safe_, swhy_)}\n\n{str(read)[:700]}"


async def _pow2_vet(http, c, now, read=True):
    """📥 A coin's FEELESS live read + the SAME guards + safety check a buy runs (free, server-side) — the minds only choose what can be bought."""
    rs = _rs()
    if read:
        try:
            c['read'] = str((await rs._ct.run_tool(http, 'coin', c['mint']))[0])[:600]
        except Exception:   # noqa: BLE001
            c['read'] = ''
    try:
        pp_ = await rs._order_pair(http, c['mint']); ok_, why_ = rs._co.buy_guards(pp_, now * 1000) if pp_ else (False, 'no pool')
        if ok_:
            ok_, why_, _cv_ = await rs._safety(http, pp_)
        c.update(safe=bool(ok_), risk=None if ok_ else str(why_)[:80])
    except Exception as e:   # noqa: BLE001 — unknown = not safe
        c.update(safe=False, risk=f'no safety read ({str(e)[:40]})')


async def _pow2_tick(http, store, cat, now):
    """One step of this agent's PoW folder."""
    rs = _rs()
    run_ = cat.setdefault('powRun', {}); f = run_.get('folder'); b_ = cat['brainsCfg']; ms = rs._lc.minds_for(b_, 'pow')
    minds = max(1, min(2, int(((cat.get('hive') or {}).get('minds')) or len(ms[:2]))))
    want = rs._POW_WANT.pop(cat['id'], None)
    if want and want.get('do') == 'stop' and f:   # ⏹ you ended it: sells if it bought, else just closes
        if f.get('phase') == 'sell_wait':
            f['sellWhy'] = 'you stopped it'  # an existing pending wallet sell must never be duplicated
        elif f.get('phase') in ('watch', 'research', 'decide', 'sell'):
            f.update(phase='sell', sellWhy='you stopped it')
        else:
            rs._pow2_close(cat, f, 'you stopped it', now); return
    base = 0
    if want and want.get('do') == 'start' and not f:
        base = want.get('mind') or 0
        minds = 1 if want.get('mind') is not None or len(ms) < 2 else 2
    if not f:
        if not want and (now - float(run_.get('rested') or 0) < rs._pow.REST_S or (cat.get('brainsCfg') or {}).get('kind') == 'general'):   # an ask skips the rest
            return
        try:
            intake = ((await http.get(f'{rs._ct.REP}/api/reputation/familia/intake', timeout=15)).json() or {}).get('coins') or []
        except (rs.httpx.HTTPError, ValueError):
            intake = []
        dex_ = await rs._pow2_dex(http)
        recent_ = rs._pow.recent_mints(cat.get('powFolders'))
        coins = rs._pow.gather(intake, dex_, recent_)
        seen_ = recent_ | {c['mint'] for c in coins}
        # Vet in small parallel batches. Browsing/holder checks used to block the
        # engine for minutes, then retry the entire search when only 2-3 passed.
        candidates = list(coins)
        candidates += rs._pow.gather(intake, dex_, seen_, need_safe=16)
        pool_, dropped = [], []
        lost_ = rs._pl.losers(cat.get('powFolders'))   # 🔁 the Proof Loop: a coin shaped like one it lost on is dropped, so a new fingerprint never repeats a loss
        shapes_ = rs._pl.colony_shapes(store.get('cats'), cat.get('id'))   # 🐝 a sharing agent also skips what the colony keeps losing on
        for offset in range(0, len(candidates), 4):
            batch = candidates[offset:offset + 4]
            await rs.asyncio.gather(*(rs._pow2_vet(http, c, now, read=False) for c in batch))
            for c in batch:
                like_ = rs._pl.repeat_of(c, lost_) if c.get('safe') else None
                herd_ = rs._pl.colony_like(c, shapes_) if c.get('safe') and not like_ else None
                if like_:
                    dropped.append({'mint': c.get('mint'), 'sym': c.get('sym'), 'src': c.get('src'), 'risk': f"same fingerprint as PoW #{like_.get('n')} ${like_.get('sym')}, which lost", 'like': f"#{like_.get('n')} ${like_.get('sym')}"})
                elif herd_:
                    dropped.append({'mint': c.get('mint'), 'sym': c.get('sym'), 'src': c.get('src'), 'risk': f"the colony lost {herd_['losses']} times on this shape", 'like': f"colony shape, {herd_['losses']} losses"})
                elif c.get('safe'):
                    pool_.append(c)
                else:
                    dropped.append({k_: c.get(k_) for k_ in ('mint', 'sym', 'src', 'risk')})
            if len(pool_) >= 4:
                break
        fallback_ = False
        if len(pool_) < 4 and want:
            pair_ = rs._pow.fallback_pair(pool_)
            if pair_:
                pool_, fallback_ = pair_, True
        coins = pool_[:4]
        if len(coins) < 4 and not fallback_:
            run_['why'] = f'only {len(coins)} buyable coins found — tries again'; run_['rested'] = now
            if want and int(want.get('tries') or 0) < 1:
                rs._POW_WANT[cat['id']] = {**want, 'tries': int(want.get('tries') or 0) + 1}
            elif want:
                cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"⛏ No PoW yet: only {len(coins)} of {len(candidates)} coins passed every buy guard. Most common reason: {rs._pow.top_reason(dropped)}. Nothing was bought.", 'at': rs.time.time(), 'open': 'pow'}])[-40:]
            return
        for c in coins:
            try:
                c['read'] = str((await rs._ct.run_tool(http, 'coin', c['mint']))[0])[:600]
            except Exception:
                c['read'] = ''
        run_['n'] = int(run_.get('n') or 0) + 1
        run_['folder'] = f = rs._pow.folder_new(run_['n'], coins, now, minds)
        f['loop'] = rs._pl.pow_loop(cat.get('powFolders'), dropped)
        f['models'] = [rs._pl._short(m) for m in ms[:2]]
        f['lead'] = rs._pl.lead_of(rs._pl.mind_board(cat), rs._pl.pow_topics(coins), f['models']) if minds > 1 else None   # 🧠 the mind with the better record here opens and has the last word
        f.update(base=min(base, max(0, len(ms) - 1)), asked=bool(want), propose=bool((want or {}).get('propose')), dropped=dropped, phase='choose' if fallback_ else 'propose', fallback=fallback_, turn=0, proposed={})
        if fallback_:
            f['plan'] = ['one safe FEELESS intake coin and one safe Pump coin are the shared options', 'both minds compare them and agree on a research favorite', 'each coin is researched, then both minds decide the one to file or buy']
            rs._pow2_say(f, 'engine', 'two-source fallback: both minds compare the same safe FEELESS and Pump coins, research each, then agree')
        if dropped:
            rs._pow2_say(f, 'engine', f"replaced {len(dropped)} unsafe: " + ', '.join('$' + str(x['sym']) + ' (' + str(x['risk'])[:40] + ')' for x in dropped))
        rs._pow2_say(f, 'engine', f"new folder: {', '.join('$' + c['sym'] + ' (' + rs._pow.SRC_LABEL[c['src']] + ')' for c in coins)}")
        rs._pow2_say(f, 'plan', ' → '.join(f'{k + 1}) {x}' for k, x in enumerate(f['plan'])))
        return
    b0 = int(f.get('base') or 0)
    names = [str(m).split('/')[-1][:24] for m in ms[b0:2]]
    ask_ = lambda i, *a: rs._pow2_ask(cat, b0 + i, *a)   # noqa: E731 — mind B alone = index 1
    if f['phase'] in ('propose', 'split'):   # 🗣 owner 2026-11-02: A proposes 3 → B proposes 3 → A takes 2 + its plan → B takes 2 + its plan
        turn = int(f.get('turn') or 0); i = turn % f['minds']; nm_ = names[i] if i < len(names) else 'mind'; n_ = len(f['coins'])
        rows_ = rs._pow_archive_rows()
        if f['phase'] == 'propose':
            prev_ = (f.get('proposed') or {}).get('0') or {}
            gone_ = set(prev_.get('picks') or []) if turn else set()   # 🚫 owner 2026-11-02: B proposes 3 OTHER coins — 6 proposals, never the same twice
            listing = '\n'.join(f"{k + 1}) ${c['sym']} [{rs._pow.SRC_LABEL[c['src']]}] pool ${c['liq']:,.0f} cap ${c['mc']:,.0f} — {c.get('read', '')[:200]}"
                                 + (f" · {rs._pow.archive_brief(rs._pow.archive_find(rows_, c['mint']))}" if rs._pow.archive_find(rows_, c['mint']) else '') for k, c in enumerate(f['coins']) if k not in gone_)
            partner = '' if turn == 0 else f" YOUR PARTNER ALREADY PROPOSED {', '.join('$' + f['coins'][k]['sym'] for k in prev_.get('picks') or [])} (\"{prev_.get('why', '')}\") — those are taken: propose 3 OTHER coins from the list."
            fpl_ = rs._pow.trade_record_line(rs._pow.trade_record(rows_, cat['id']))   # 🧬 what its own wins were built on
            read_, f['sitesRead'] = await rs._site_reads('pow', (cat['id'], cat.get('name')))
            raw_ = await ask_(i, rs._pow.PROPOSE_SYS.format(name=nm_, n=n_, partner=partner) + rs._feat._sources.proof_line('pow') + read_ + rs._recall(cat, 'Trades', ' '.join(str(c_.get('sym')) for c_ in f.get('coins') or [])), (fpl_ + '\n' if fpl_ else '') + listing, 400)
            picks, why = rs._pow.parse_picks(raw_, n_, rs._pow.PROPOSE_N + len(gone_))
            picks = [k for k in picks if k not in gone_][:rs._pow.PROPOSE_N]
            need_ = min(rs._pow.PROPOSE_N, n_ - len(gone_))
            if len(picks) < need_:
                f['silent'] = int(f.get('silent') or 0) + 1
                if f['silent'] < 3:
                    return
                picks = (picks + [k for k in sorted(range(n_), key=lambda x: -f['coins'][x]['liq']) if k not in picks and k not in gone_])[:need_]; why = why or 'the engine filled the deepest pools'
            f['silent'] = 0; f.setdefault('proposed', {})[str(turn)] = {'picks': picks, 'why': why, 'by': nm_}
            said_ = f"proposes {', '.join('$' + f['coins'][k]['sym'] for k in picks)} — {why}"
            rs._pow2_say(f, nm_, said_)
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"🗣 MIND {'AB'[b0 + i]} {said_}"[:400], 'at': rs.time.time(), 'open': 'pow'}])[-40:]
            if turn == 0:
                f['turn'] = 1; return
            short_ = list(dict.fromkeys(k for t_ in ('0', '1') for k in (f['proposed'].get(t_) or {}).get('picks') or []))
            short_ += [k for k in sorted(range(n_), key=lambda x: -f['coins'][x]['liq']) if k not in short_][:max(0, 2 * rs._pow.SPLIT_N - len(short_))]
            f.update(shortlist=short_, phase='split', turn=0, owner={}, plans={})
            rs._pow2_say(f, 'engine', f"shortlist: {', '.join('$' + f['coins'][k]['sym'] for k in short_)} — each mind takes {rs._pow.SPLIT_N} and plans its research")
            return
        short_ = list(f.get('shortlist') or []); taken_ = [k for k in short_ if f['coins'][k]['mint'] in (f.get('owner') or {})]
        listing = '\n'.join(f"{k + 1}) ${f['coins'][k]['sym']} [{rs._pow.SRC_LABEL[f['coins'][k]['src']]}] pool ${f['coins'][k]['liq']:,.0f} — {f['coins'][k].get('read', '')[:160]}" for k in short_ if k not in taken_)
        taken_txt = '' if not taken_ else f" — NOT your partner's {', '.join('$' + f['coins'][k]['sym'] for k in taken_)}"
        raw_ = await ask_(i, rs._pow.SPLIT_SYS.format(name=nm_, k=rs._pow.SPLIT_N, taken=taken_txt), listing, 400)
        picks, plan_ = rs._pow.parse_picks(raw_, n_, rs._pow.SPLIT_N)
        mine_ = rs._pow.split_of([k for k in short_ if k not in taken_], picks, taken_)
        for k in mine_:
            f['owner'][f['coins'][k]['mint']] = i; f['plans'][f['coins'][k]['mint']] = plan_ or 'confirm the safety vitals, then the buyers vs sellers'
        said_ = f"takes {', '.join('$' + f['coins'][k]['sym'] for k in mine_)} — plan: {plan_ or 'safety vitals first, then flow'}"
        rs._pow2_say(f, nm_, said_)
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"🗣 MIND {'AB'[b0 + i]} {said_}"[:400], 'at': rs.time.time(), 'open': 'pow'}])[-40:]
        if turn == 0 and len(short_) > len(mine_):
            f['turn'] = 1; return
        by_ = [[m for m, o in f['owner'].items() if o == x] for x in (0, 1)]
        order_ = [m for pair_ in zip(by_[0] + [None] * 4, by_[1] + [None] * 4) for m in pair_ if m][:2 * rs._pow.SPLIT_N]
        f.update(scout=order_, scoutDone=[], phase='scout', phaseAt=round(now), turn=0, picks={}, said={}, fav=order_[0] if order_ else None)
        rs._pow2_say(f, 'engine', f"they research {', '.join('$' + next(c['sym'] for c in f['coins'] if c['mint'] == m) for m in order_)} — each its own, with its plan")
        return
    if f['phase'] == 'choose':   # 🗣 3 turns, in your chat (owner 2026-11-01): A proposes → B agrees or suggests → A's FINAL plan
        if f.get('scouted') and not f.get('revetted'):   # 🔁 live 2026-11-02: $pairless ran +443 % DURING its research — every coin is checked again before they decide
            f['revetted'] = True
            for c in [c for c in f['coins'] if c.get('safe', True)]:
                await rs._pow2_vet(http, c, now, read=False)
                if not c.get('safe'):
                    rs._pow2_say(f, 'engine', f"${c['sym']} is out now — {c.get('risk')}")
        safe_ = [k for k, c in enumerate(f['coins']) if c.get('safe', True) and (not f.get('scouted') or not f.get('scout') or c['mint'] in f['scout'])]   # 🔎 they decide among the coins they researched
        if not safe_:
            rs._pow2_close(cat, f, 'none of the folder coins passed the safety check — no buy', now); return
        listing = '\n'.join(f"{k + 1}) ${c['sym']} [{rs._pow.SRC_LABEL[c['src']]}] pool ${c['liq']:,.0f} cap ${c['mc']:,.0f}"
                             + ('' if c.get('safe', True) else f" — UNSAFE ({c.get('risk')}), never pick it") + f" — {c.get('read', '')[:220]}"
                             + (f" · RESEARCHED: {' · '.join(x['label'] + ' ' + x['value'] + ' (' + x['site'] + ')' for x in (f.get('vitals') or {}).get(c['mint'], [])[:6])}" if (f.get('vitals') or {}).get(c['mint']) else '')
                             + (f" · CHART {rs._pow.chart_line((f.get('charts') or {}).get(c['mint']))}" if (f.get('charts') or {}).get(c['mint']) else '') for k, c in enumerate(f['coins']) if k in safe_ or not f.get('scouted'))
        listing = ('STEP: ' + ('PLAN which coins to research — your pick = your early favorite' if not f.get('scouted') else 'DECIDE the ONE to buy with the research below') + '\n' + listing)
        turn = int(f.get('turn') or 0); last_ = turn >= (2 if f['minds'] > 1 else 0); i = 1 if (turn == 1 and f['minds'] > 1) else 0
        if f['minds'] > 1 and (f.get('lead') or {}).get('i') == 1:   # 🧠 mind B has the better record here: B opens and B gives the final plan. Every guard and the safer-trade rule stay
            i = 1 - i
        cap_ = round(min(rs._at.MAX_BUY_SOL, rs._num(cat.get('budgetSol')) or rs._num((cat.get('risk') or {}).get('maxPositionSol')) or 0.05), 4)
        prev = f.get('said') or {}
        partner = ('' if turn == 0 else f" YOUR PARTNER {'PROPOSES' if turn == 1 else 'ANSWERED'} {prev.get('k', 0) + 1} (${f['coins'][prev.get('k', 0)]['sym']}, "
                   f"{prev.get('t', {}).get('sol')} SOL, TP +{prev.get('t', {}).get('tp')}%, SL −{prev.get('t', {}).get('sl')}%): \"{prev.get('why', '')}\". "
                   + ('Agree, or suggest a better coin / trade and why.' if turn == 1 else 'Give the FINAL plan.'))
        raw_ = await ask_(i, rs._pow.CHOOSE_SYS.format(name=names[i] if i < len(names) else 'mind', partner=partner, cap=cap_, n=len(f['coins'])), listing, 600)
        k, why = rs._pow.parse_pick(raw_)
        if k is None or k not in safe_:
            f['silent'] = int(f.get('silent') or 0) + (1 if k is None else 0)
            if k is None and f['silent'] < 3:
                return   # asked again next tick
            k, why = max(safe_, key=lambda x: f['coins'][x]['liq']), (why or 'the engine took the safest by pool')   # never an unsafe coin, never stuck
        f['silent'] = 0
        tr_ = rs._pow.trade_of(raw_, cap_)
        f['said'] = {'k': k, 't': tr_, 'why': why}; f.setdefault('trades', {})[str(i)] = tr_; f['picks'][str(i)] = k; f.setdefault('whys', {})[str(i)] = why
        verb = 'final plan' if last_ else ('proposes' if turn == 0 else 'answers')
        said_ = f"{verb}: ${f['coins'][k]['sym']} · {tr_['sol']:g} SOL · TP +{tr_['tp']:g}% · SL −{tr_['sl']:g}% — {why}"
        rs._pow2_say(f, names[i] if i < len(names) else 'mind', said_)
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"🗣 MIND {'AB'[b0 + i]} {said_}"[:400], 'at': rs.time.time(), 'open': 'pow'}])[-40:]   # the discussion, in your chat
        if not last_:
            f['turn'] = turn + 1; return
        if not f.get('scouted'):   # 🗺 that was the PLAN: research the safe coins first (their favorite first), then decide with the research in hand
            order_ = [k] + sorted([x for x in safe_ if x != k], key=lambda x: -f['coins'][x]['liq'])
            f.update(scout=[f['coins'][x]['mint'] for x in order_], scoutDone=[], phase='scout', phaseAt=round(now), turn=0, picks={}, said={}, fav=f['coins'][k]['mint'])
            rs._pow2_say(f, 'engine', f"plan agreed — they research {', '.join('$' + f['coins'][x]['sym'] for x in order_)} in turns, then decide")
            return
        c = f['coins'][k]; f.update(pick=c, mint=c['mint'], pair=c['pair'], sym=c['sym'], why0=why, phase='buy', phaseAt=round(now))
        tr_ = rs._pow.agree_trade(list((f.get('trades') or {}).values())) or tr_   # the final coin; the safer of their trades
        f.update(sol=tr_['sol'], tp=tr_['tp'], sl=tr_['sl'])
        rs._pow2_say(f, 'engine', f"they set the trade: {tr_['sol']:g} SOL · take profit +{tr_['tp']:g}% · stop −{tr_['sl']:g}%")
        if cat.get('handle') == 'sicarios' and (cat.get('brainsCfg') or {}).get('cardSeat') and not f.get('propose'):   # 🎩 no wallet here: the agreed coin goes to a free seat on the card, and every guard of that seat decides
            sent_ = await rs._card_seat_send(http, f, c, tr_, now); f['cardSeat'] = sent_
            rs._pow2_say(f, 'engine', f"sent ${c['sym']} to the Fuse card seat" if sent_.get('ok') else f"the card refused ${c['sym']}: {sent_.get('why')}")
            rs._pow2_close(cat, f, f"🎩 ${c['sym']}: {'sent to the Fuse card seat' if sent_.get('ok') else 'the card refused it: ' + str(sent_.get('why'))}", now)
            return
        if f.get('propose'):   # 💡 a proposal: the agreed coin is filed as the card — nothing bought
            rs._pow2_say(f, 'engine', f"proposal: ${c['sym']} ({rs._pow.SRC_LABEL[c['src']]}) — nothing bought")
            try:   # 🌘 what it would have done: every coin read now and an hour on (price only, never P/L)
                rs._pow2_shadow_entry(f, await rs._pair_prices(http, [x['pair'] for x in f.get('coins') or [] if x.get('pair')]), now); f['shadowDueAt'] = round(now + rs._pow.SHADOW_S)
            except (rs.httpx.HTTPError, ValueError) as e:
                print(f'[pow2] shadow not started: {str(e)[:100]}')
            rs._pow2_close(cat, f, f"💡 proposes ${c['sym']} — {f.get('why0') or 'both minds agreed'}", now)
        return
    if f['phase'] == 'buy':
        if f.get('pid'):   # 💵 a REAL buy: the folder waits for its wallet to fill it — it never tracks a buy that did not happen (live 2026-11-01)
            p_ = next((x for x in cat.get('proposals') or [] if x.get('id') == f['pid']), None) or {}
            if p_.get('status') == 'done' or f['mint'] in (cat.get('realHeld') or {}):
                prices = await rs._pair_prices(http, [c['pair'] for c in f['coins'] if c.get('safe', True)])
                live = prices.get(f['pair']) or {}; rs._pow2_shadow_entry(f, prices, now)
                f.update(entry=rs._num(live.get('priceNative')), entryUsd=rs._num(live.get('priceUsd')), boughtAt=round(now), phase='watch', phaseAt=round(now))
                rs._pow2_say(f, 'engine', f"its wallet bought {f['sol']:g} SOL of ${f['sym']} on FEELESS")
            elif 'wallet holds' in str(p_.get('agentWhy') or '') or 'no SOL left' in str(p_.get('agentWhy') or ''):   # 💸 it can't afford it: say so NOW, never wait 10 min
                p_.update(status='expired', why2=p_['agentWhy'])
                cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"💸 {f['name']}: its wallet can't buy ${f['sym']} — {p_['agentWhy']}. Add SOL to its wallet, then file a PoW again.", 'at': rs.time.time(), 'open': 'pow'}])[-40:]
                rs._pow2_close(cat, f, f"its wallet is short — {p_['agentWhy']}", now)
            elif p_.get('status') in ('failed', 'expired', 'skip') or now - f['phaseAt'] > rs._pow.SIGN_WAIT_S:
                sent_ = p_.get('agentTx') and any(t.get('key') == p_['agentTx'] and t.get('status') in rs._at.LIVE for t in cat.get('agentTx') or [])
                if p_.get('status') == 'pending' and sent_ and now - f['phaseAt'] <= 2 * rs._pow.SIGN_WAIT_S:   # already sent: the chain decides. Closing now could leave a coin with no folder watching it
                    return
                if p_.get('status') == 'pending':
                    p_.update(status='expired', why2='sent, but the chain never confirmed it' if sent_ else 'its PoW folder closed before it was signed')   # nothing left hanging
                rs._pow2_close(cat, f, f"the buy did not fill ({p_.get('why2') or p_.get('status') or 'not signed'})", now)
            return
        sol = round(float(f.get('sol') or min(rs._num((cat.get('risk') or {}).get('maxPositionSol')) or 0.05, rs._num(cat.get('budgetSol')) or 1.0)), 4)   # the size the minds agreed
        row = await rs._run_order(store, cat, f"buy {sol} SOL of {f['mint']}", http)
        if row.get('state') not in ('filled', 'proposed'):
            f['tried'] = (f.get('tried') or []) + [f['mint']]
            nxt_ = [c for c in f['coins'] if c.get('safe', True) and c['mint'] not in f['tried']]
            if not nxt_:
                rs._pow2_close(cat, f, f"buy refused — {row.get('why')} (no other safe coin)", now); return
            c = max(nxt_, key=lambda x: x['liq'])   # 🔁 the next safe coin of the folder, never a dead end
            rs._pow2_say(f, 'engine', f"${f['sym']} refused ({row.get('why')}) — next safe coin: ${c['sym']}")
            f.update(pick=c, mint=c['mint'], pair=c['pair'], sym=c['sym']); return
        if row.get('state') == 'proposed':   # 💵 its OWN wallet buys — no signature from you (owner 2026-11-01); the server guards still run (budget · day cap · gas · one at a time)
            rs._pow2_approve(cat, row.get('pid'))
            sol = rs._pow2_real_sol(cat, row.get('pid'), sol)
            f.update(sol=sol, real=True, pid=row.get('pid'), phaseAt=round(now))
            rs._pow2_say(f, 'engine', f"its wallet is buying {sol:g} SOL of ${f['sym']} on FEELESS")
            return
        prices = await rs._pair_prices(http, [c['pair'] for c in f['coins'] if c.get('safe', True)])
        live = prices.get(f['pair']) or {}; rs._pow2_shadow_entry(f, prices, now)
        f.update(sol=sol, real=False, entry=rs._num(live.get('priceNative')), entryUsd=rs._num(live.get('priceUsd')), boughtAt=round(now), phase='watch', phaseAt=round(now))
        rs._pow2_say(f, 'engine', f"bought {sol:g} SOL of ${f['sym']} on FEELESS (paper)")
        return
    if f['phase'] == 'scout':   # 🔎 SCOUT: each safe coin gets a research round (its own coin folder), the minds taking turns; the other watches its chart
        prs_ = await rs._pair_prices(http, [c['pair'] for c in f['coins'] if c['mint'] in f['scout']])
        for c in f['coins']:
            px_ = rs._num((prs_.get(c['pair']) or {}).get('priceNative'))
            if px_:
                f.setdefault('charts', {})[c['mint']] = (((f.get('charts') or {}).get(c['mint'])) or [])[-30:] + [{'at': round(now), 'px': px_}]
        w_, t_, running, mine_ = rs._pow2_running(cat, f)
        if f.get('rPair'):
            if running and now - float(f.get('researchAt') or now) < rs._pow.RESEARCH_S:
                return
            if running:
                rs.asyncio.create_task(rs._hard_stop(w_, 0)); return
            if mine_:
                async def partner_(i, m):   # 🗣 ONE line from the partner on the coin this mind just read
                    c_ = next((c for c in f['coins'] if c['mint'] == m), {}); o_ = 1 - i
                    vt_ = ' · '.join(f"{x['label']} {x['value']}" for x in (f.get('vitals') or {}).get(m, [])[:6]) or 'no vitals'
                    raw_ = await ask_(o_, rs._pow.COIN_TALK_SYS.format(name=names[o_] if o_ < len(names) else 'mind', sym=c_.get('sym'), vitals=vt_), vt_, 160)
                    line_ = (rs.re.search(r'"say"\s*:\s*"([^"]{0,200})', str(raw_)) or [None, str(raw_).strip()[:160]])[1]
                    if line_:
                        rs._pow2_say(f, names[o_] if o_ < len(names) else 'mind', f"on ${c_.get('sym')}: {line_}")
                for i_, pw_ in t_['pows'].items():
                    win_ = t_['windows'][i_]
                    rs._pow2_collect(f, {**t_, 'pow': pw_, 'cost': win_.get('cost') or 0, 'windows': [win_]}, names[i_] if i_ < len(names) else 'mind', now, cat=cat)
                await rs.asyncio.gather(*(partner_(int(i), m) for i, m in f['rPair'].items()))
            f['scoutDone'] = (f.get('scoutDone') or []) + list(f.pop('rPair').values()); f.pop('rMint', None)
        elif f.get('rMint'):
            if running and now - float(f.get('researchAt') or now) < rs._pow.RESEARCH_S:
                return
            if running:
                rs.asyncio.create_task(rs._hard_stop(w_, 0)); return
            if mine_:
                m_ = f.get('rMint'); rs._pow2_collect(f, t_, names[f.get('rMind') or 0] if (f.get('rMind') or 0) < len(names) else 'mind', now, cat=cat); f['rMint'] = m_
                if f['minds'] > 1:   # 🗣 ONE line from the partner after that coin's 3-site research
                    o_ = 1 - int(f.get('rMind') or 0); c_ = next((c for c in f['coins'] if c['mint'] == m_), {})
                    vt_ = ' · '.join(f"{x['label']} {x['value']}" for x in (f.get('vitals') or {}).get(m_, [])[:6]) or 'no vitals'
                    raw_ = await ask_(o_, rs._pow.COIN_TALK_SYS.format(name=names[o_] if o_ < len(names) else 'mind', sym=c_.get('sym'), vitals=vt_), vt_, 160)
                    line_ = (rs.re.search(r'"say"\s*:\s*"([^"]{0,200})', str(raw_)) or [None, str(raw_).strip()[:160]])[1]
                    if line_:
                        rs._pow2_say(f, names[o_] if o_ < len(names) else 'mind', f"on ${c_.get('sym')}: {line_}")
            f['scoutDone'] = (f.get('scoutDone') or []) + [f.pop('rMint', None) or '']
        left_ = [m for m in f['scout'] if m not in (f.get('scoutDone') or [])]
        if not left_:   # every coin has its folder: the final 3-turn decision, with the research in hand
            f.update(phase='choose', scouted=True, turn=0, picks={}, said={}, phaseAt=round(now)); rs._pow2_say(f, 'engine', 'every coin researched — they decide which ONE to buy')
            return
        c_ = next(c for c in f['coins'] if c['mint'] == left_[0]); mi_ = int((f.get('owner') or {}).get(c_['mint'], len(f.get('scoutDone') or []) % f['minds']))   # each mind researches the coins IT took
        turn_ = {}   # 🏇 the next unread coin of each mind: two owners = both research at once
        for k_, m_ in enumerate(left_):
            turn_.setdefault(int((f.get('owner') or {}).get(m_, (len(f.get('scoutDone') or []) + k_) % f['minds'])), m_)
        pair_ = [next(c for c in f['coins'] if c['mint'] == turn_[i]) for i in (0, 1)] if f['minds'] > 1 and {0, 1} <= set(turn_) else None
        if not (rs._pow2_research_pair(cat, f, pair_, now) if pair_ else rs._pow2_research(cat, f, c_, mi_, now)):   # its window is busy (your ask): wait for it — a coin is never skipped unread (live 2026-11-01: $JOB was)
            f.setdefault('busyAt', round(now))
            if now - f['busyAt'] >= 300:
                f['scoutDone'] = (f.get('scoutDone') or []) + [c_['mint']]; f.pop('busyAt', None)
                rs._pow2_say(f, 'engine', f"${c_['sym']} not researched — its window stayed busy 5 min; it keeps its FEELESS read")
        else:
            f.pop('busyAt', None)
        return
    live = (await rs._pair_prices(http, [f['pair']])).get(f['pair']) or {}
    px = rs._num(live.get('priceNative'))
    held = f['mint'] in (cat.get('realHeld') or {}) if f.get('real') else any(p.get('pairAddress') == f['pair'] for p in cat.get('positions') or [])
    if f.get('sellPid'):
        sale = next((p for p in cat.get('proposals') or [] if p.get('id') == f['sellPid']), None) or {}
        if sale.get('status') == 'done' and not held:
            if not f.get('settlementVerified') and now >= float(f.get('reconcileAfter') or 0):
                if not await rs._pow2_reconcile(http, cat, f):
                    f['settlementPending'] = True
                    f['reconcileAfter'] = round(now + 15)
            if not f.get('settlementVerified'):
                return  # the folder stays recoverable until both on-chain fills can be verified
            f.pop('settlementPending', None)
            await rs._pow2_shadow_exit(http, f, now)
            rs._pow2_close(cat, f, f.get('sellWhy') or 'its wallet sold', now, px)
        elif sale.get('status') in ('failed', 'expired'):
            f.pop('sellPid', None)
            f['sellAttempts'] = int(f.get('sellAttempts') or 0) + 1
            rs._pow2_say(f, 'engine', f"sell was not confirmed: {sale.get('why2') or sale.get('status')}")
        return
    if not held:   # its stops (or you) already sold it
        if f.get('real'):
            f['settlementPending'] = True
        await rs._pow2_shadow_exit(http, f, now)
        rs._pow2_close(cat, f, 'sold by its stops', now, px); return
    if px:
        f['chart'] = (f.get('chart') or [])[-40:] + [{'at': round(now), 'px': px}]
    why_x = rs._pow.hard_exit(f.get('entry') or 0, px, f.get('boughtAt') or now, now, f.get('rounds') or 0, float(f.get('tp') or rs._pow.TAKE_PCT), float(f.get('sl') or abs(rs._pow.STOP_PCT)))
    if why_x or f['phase'] == 'sell':
        row = await rs._run_order(store, cat, f"sell all {f['mint']}", http)
        if row.get('state') == 'proposed':
            rs._pow2_approve(cat, row.get('pid'))   # its wallet sells on its own too
            f.update(sellPid=row.get('pid'), sellWhy=why_x or f.get('sellWhy') or 'the watcher said sell', phase='sell_wait')
            rs._pow2_say(f, 'engine', f"sell sent; waiting for its wallet's confirmed fill (because {f['sellWhy']})")
            return
        if f.get('real'):
            rs._pow2_say(f, 'engine', f"sell not confirmed — {row.get('why')}; the folder keeps watching")
            f['phase'] = 'sell'
            return
        rs._pow2_say(f, 'engine', f"sell: {why_x or f.get('sellWhy') or 'the watcher said sell'} — {row.get('why')}")
        await rs._pow2_shadow_exit(http, f, now)
        rs._pow2_close(cat, f, why_x or f.get('sellWhy') or 'the watcher sold', now, px); return
    rr_ = int(f.get('rr') or 0)
    researcher = rr_ % f['minds']   # 🔁 research rounds ALTERNATE minds in the background while the chart is checked live
    w_, t_, running, mine_ = rs._pow2_running(cat, f)
    if f.get('rMint'):
        if running and now - float(f.get('researchAt') or now) >= rs._pow.RESEARCH_S:
            rs.asyncio.create_task(rs._hard_stop(w_, 0)); running = False   # ⏱ a research round is 2.5 min
        if mine_ and not running:
            rs._pow2_collect(f, t_, names[f.get('rMind') or 0] if (f.get('rMind') or 0) < len(names) else 'mind', now, cat=cat); f['rr'] = rr_ + 1
        elif not mine_:
            f.pop('rMint', None); f['rr'] = rr_ + 1   # its window was taken (your ask): that round is skipped, never stuck
    elif now - float(f.get('researchAt') or 0) >= 20:   # the next round starts (a short breath between rounds)
        rs._pow2_research(cat, f, {'mint': f['mint'], 'pair': f['pair'], 'sym': f['sym']}, researcher, now)
    f['phase'] = 'research' if f.get('rMint') else 'watch'
    n_ = int(f.get('checks') or 0)
    if n_ >= 2 and rs._pow.next_check_s(f.get('entry') or 0, px, f.get('tp') or rs._pow.TAKE_PCT, f.get('sl') or abs(rs._pow.STOP_PCT), n_) == rs._pow.CHECKS[-1]:
        f['nextAt'] = min(float(f.get('nextAt') or now), round(now + rs._pow.CHECKS[-1]))  # a move toward either exit wakes minds sooner
    if now < float(f.get('nextAt') or (float(f.get('boughtAt') or now) + rs._pow.CHECKS[0])):   # +15 s → +30 s → every 60 s, each from the last check (no catch-up storms)
        return
    # ⏱ LIVE-TRADE CHECK n (2 steps): the watcher reads the chart → the partner agrees or overrides
    watcher_ = (researcher + 1) % f['minds']; other_ = researcher if f['minds'] > 1 else watcher_
    res_ = ' · '.join(f"{x['label']} {x['value']} ({x['site']})" for x in (f.get('research') or [])[-6:]) or 'none yet'
    a1, s1 = rs._pow.parse_decide(await ask_(watcher_, rs._pow.DECIDE_SYS.format(name=names[watcher_] if watcher_ < len(names) else 'mind', sym=f['sym']),
                                         f"P/L {rs._pow.pnl_pct(f.get('entry') or 0, px):+.1f}% · TP +{f.get('tp')}% · SL −{f.get('sl')}% · CHART {rs._pow.chart_line(f.get('chart'))}\nRESEARCH {res_}", 220))
    act, say = a1, s1
    if f['minds'] > 1:
        a2, s2 = rs._pow.parse_decide(await ask_(other_, rs._pow.AGREE_SYS.format(name=names[other_] if other_ < len(names) else 'mind', sym=f['sym'], said=f'{a1}: {s1}'),
                                             f"P/L {rs._pow.pnl_pct(f.get('entry') or 0, px):+.1f}% · CHART {rs._pow.chart_line(f.get('chart'))}", 200))
        act, say = a2, f"{s1} → {s2}"
        rs._pow2_say(f, names[watcher_] if watcher_ < len(names) else 'mind', f"check {n_ + 1}: {a1} — {s1}")
        rs._pow2_say(f, names[other_] if other_ < len(names) else 'mind', f"{'agrees' if a2 == a1 else 'overrides'}: {a2} — {s2}")
    else:
        rs._pow2_say(f, names[0] if names else 'mind', f"check {n_ + 1}: {a1} — {s1}")
    f['checks'] = n_ + 1; f['rounds'] = n_ + 1
    f['nextAt'] = round(now + rs._pow.next_check_s(f.get('entry') or 0, px, f.get('tp') or rs._pow.TAKE_PCT, f.get('sl') or abs(rs._pow.STOP_PCT), n_ + 1))
    if act == 'SELL':
        f.update(phase='sell', sellWhy=f'they agreed: {say[:90]}')


async def _pow2_shadow_due(store, now):
    """🌘 Grade proposals whose shadow hour is up. One network read, only when one is due."""
    rs = _rs()
    due = [f for c in store['cats'].values() for f in (c.get('powFolders') or [])[-3:] if f.get('shadowDueAt') and f.get('shadow') is None and now >= f['shadowDueAt']]
    if due:
        async with rs.httpx.AsyncClient(timeout=20) as http:
            for f in due:
                await rs._pow2_shadow_exit(http, f, now)


def _proof_site(cat, kind):
    """The manual of the site the owner named for this proof, or None. A saved sign-in was dropped: it no longer goes there."""
    rs = _rs()
    ps = cat.get('proofSite') or {}
    if not kind or ps.get('kind') != kind or rs.time.time() - float(ps.get('at') or 0) > rs.PROOF_SITE_S or ps.get('site') not in (cat.get('siteSessions') or {}):
        return None
    return (cat.get('siteManuals') or {}).get(ps.get('site'))


def _site_note(cat, kind):
    rs = _rs()
    m = rs._proof_site(cat, kind)
    return rs._ss.note_for(m, kind) if m else ''


def _proof_hosts(cat, kind):
    rs = _rs()
    m = rs._proof_site(cat, kind)
    return [m['site']] if m else []


def _site_proof_start(cat, cat_id, site, kind):
    """🔎 One door for the chat's "file a pump pow" and the manual's button: the same proof, with its windows going to that site first. → (ok, what to say)"""
    rs = _rs()
    room_ = rs._proof_room(cat, cat_id, {'pow': 'PoW', 'pop': 'PoP'}.get(kind, 'PoB'))
    if room_:
        return False, room_
    if kind == 'pow':
        f_ = (cat.get('powRun') or {}).get('folder')
        if f_:
            return False, f"⛏ {f_.get('name')} is still open ({f_.get('phase')}). Say \"stop PoW\" to end it first."
        if not (cat.get('brainsCfg') or {}).get('brains'):
            return False, '⛏ It needs a model first.'
        cat['proofSite'] = {'site': site, 'kind': kind, 'at': rs.time.time()}
        rs._POW_WANT[cat_id] = {'do': 'start', 'mind': None}; rs._POW_WAKE.set()
        return True, f'⛏ Filing a PoW with {site} first, signed in. It reads there and buys only through FEELESS, by the usual guards.'
    if kind == 'pop':
        ok_, say_ = rs._pop.reply('start', cat.get('popRun'), cat.get('popCard'))
        if ok_:
            cat['proofSite'] = {'site': site, 'kind': kind, 'at': rs.time.time()}
            rs._POP_WANT[cat_id] = 'start'; rs._POW_WAKE.set()
            say_ = f'📉 Filing a PoP with {site} read first, signed in. The trade stays on paper.'
        return ok_, say_
    ok_, say_ = rs._pob.reply(cat.get('pobRun'), bool(cat.get('pobRead')))
    if ok_:
        cat['proofSite'] = {'site': site, 'kind': kind, 'at': rs.time.time()}
        rs._POB_WANT[cat_id] = 'start'; rs._POW_WAKE.set()
        say_ = f'🎲 Filing a PoB with {site} read first, signed in. Free chips on the FEELESS board only, nothing on {site}.'
    return ok_, say_


async def _mail_tool(http, cat, tool):
    """📧 The agent's read of ITS OWN box. Its owner makes the box from the desktop."""
    rs = _rs()
    box_ = cat.get('mailbox') or {}
    if not box_.get('address'):
        return 'It has no mailbox yet. Ask its owner to press Make its email in the Mail folder.'
    if tool == 'mailbox':
        return f"Its email: {box_['address']}"
    try:
        return rs._am.for_model(await rs._am.inbox(http, box_['address'], rs._cv.reveal(cat, rs._am.SITE, box_['address'], data_dir=rs.DATA_DIR)))
    except ValueError as e:
        return str(e)


# 💸 TOP-UPS (agent_topup.py): one card a time. Only the owner's own words reach these: the chat door and the card's buttons.
async def _sol_usd(http):
    rs = _rs()
    r = await http.get('https://api.dexscreener.com/latest/dex/pairs/solana/58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2', timeout=8)
    return rs._num(((r.json().get('pairs') or [{}])[0]).get('priceUsd'))


async def _live_feed(cat):
    """📡 Real numbers any proof may use, read only: SOL price and 24h change (DexScreener), slot and TPS over its own Helius key from the
    cabinet when saved, else FEELESS's RPC, and its own wallet's SOL. Cached 20 s per agent. The key stays here. → dict"""
    rs = _rs()
    now = rs.time.time(); hit = rs._LIVE.get(cat.get('id'))
    if hit and now - hit['at'] < rs.LIVE_S:
        return hit
    key = rs._ck.key_for(cat, 'helius', data_dir=rs.DATA_DIR); addr = (cat.get('agentWallet') or {}).get('address')
    async with rs.httpx.AsyncClient(timeout=10) as http:
        async def rpc(method, params):
            if key:
                r = await http.post(f'https://mainnet.helius-rpc.com/?api-key={key}', json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
                return (r.json() or {}).get('result') if r.status_code == 200 else None
            return await rs._crpc._rpc(http, method, params, scan=False)
        async def pair():
            r = await http.get('https://api.dexscreener.com/latest/dex/pairs/solana/58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2', timeout=8)
            p_ = (r.json().get('pairs') or [{}])[0] if r.status_code == 200 else {}
            return rs._num(p_.get('priceUsd')) or None, (p_.get('priceChange') or {}).get('h24')
        async def safe(c):
            try:
                return await c
            except Exception:   # noqa: BLE001 — one dead source leaves its number empty, never the others
                return None
        got = await rs.asyncio.gather(safe(pair()), safe(rpc('getSlot', [{'commitment': 'confirmed'}])), safe(rpc('getRecentPerformanceSamples', [1])), safe(rs._lamports_sol(http, addr)) if addr else rs.asyncio.sleep(0))
    (sol, ch), slot, perf, bal = got[0] or (None, None), got[1], got[2], got[3]
    perf_ = (perf or [{}])[0] if isinstance(perf, list) else {}
    tps = round(perf_.get('numTransactions', 0) / perf_['samplePeriodSecs']) if perf_.get('samplePeriodSecs') else None
    feed = {'solUsd': sol, 'solChange24h': rs._num(ch) if ch is not None else None, 'slot': slot if isinstance(slot, int) else None, 'tps': tps, 'walletSol': bal,
            'source': 'its own Helius key' if key else 'FEELESS RPC', 'at': round(now)}
    rs._LIVE[cat.get('id')] = feed
    return feed


async def _lamports_sol(http, addr):
    """The SOL on an address, read on-chain, or None. It is what the chain says, not the site's own balance figure."""
    rs = _rs()
    try:
        got = await rs._crpc._rpc(http, 'getBalance', [addr, {'commitment': 'confirmed'}])
        return round(rs._num((got or {}).get('value')) / 1e9, 6)
    except Exception:   # noqa: BLE001 — unread stays unread
        return None


async def _topup_send(cat, cat_id, usd, typed):
    """→ (ok, what to say). One transfer from its own wallet to the card's address. The card goes first, so no second yes can send it again."""
    rs = _rs()
    c_ = cat.get('topup'); now = rs.time.time(); addr_ = (cat.get('agentWallet') or {}).get('address')
    if rs._tu.expired(c_, now) or not c_.get('address'):
        return False, '💸 Nothing is waiting to be topped up. Say "top up pump".'
    why_ = rs._tu.amount_why(usd)
    if why_:
        return False, f'💸 {why_}'
    if not addr_ or not rs._pays_itself(cat):
        return False, '💸 Only its own Circle wallet can send a top-up.'
    if not rs._tu.valid_address(c_['address']) and not str(c_['address']) == addr_:
        return False, '💸 That is not a Solana address, so nothing moved.'
    if c_['address'] == addr_:
        return False, '💸 That is its own wallet, so nothing moved.'
    if not rs._tu.check_ok(c_, typed):
        return False, "💸 It read that address from the page, so type its last 4 characters first. Nothing moved."
    if cat_id in rs._SWAP_BUSY:
        return False, '💸 A send is already on its way.'
    rs._SWAP_BUSY.add(cat_id)
    try:
        async with rs.httpx.AsyncClient(timeout=30) as http:
            px_ = await rs._sol_usd(http)
            if not px_:
                return False, '💸 No SOL price right now, so nothing moved.'
            lam_ = rs._tu.to_lamports(usd, px_); sol_ = round(lam_ / 1e9, 6)
            _usdc, bal_ = await rs._agent_usdc(http, addr_)
            if sol_ > bal_ - rs._at.GAS_SOL + 1e-9:
                return False, f'💸 It holds {bal_:.4f} SOL and keeps {rs._at.GAS_SOL} for gas, so ${usd:.2f} ({sol_} SOL) will not fit. Nothing moved.'
            before_ = await rs._lamports_sol(http, c_['address'])
            cat.pop('topup', None)   # one yes, one send
            bh_ = ((await rs._crpc._rpc(http, 'getLatestBlockhash', [{'commitment': 'confirmed'}])) or {}).get('value', {}).get('blockhash')
            rec_ = {'key': f"feeless-{cat_id}-topup-{c_['id']}", 'tx': rs.pot_transfer_tx(addr_, c_['address'], lam_, bh_)}
            try:
                await rs._at._circle_post(http, cat, rec_)
            except ValueError as e:
                return False, f'💸 {str(e)[:120]}. Nothing moved.'
    finally:
        rs._SWAP_BUSY.discard(cat_id)
    if not rec_.get('sig'):
        return False, '💸 Sent to the signer, but no signature came back yet. Check its wallet before asking again.'
    cat['topups'] = (list(cat.get('topups') or []) + [{'site': c_['site'], 'address': c_['address'], 'usd': usd, 'sol': sol_, 'sig': rec_['sig'], 'at': round(now), 'before': before_, 'after': None}])[-rs._tu.LEDGER_MAX:]
    return True, f"💸 Sent ${usd:.2f} ({sol_} SOL) to your {c_['site']} account. tx {rec_['sig']}"


def _topup_answer(cat, ans):
    """What a chat answer does to the card, with no money moved here. → {'say'} or, for a yes that can send, {'send': usd}. {'ask': True} means it still needs an amount."""
    rs = _rs()
    c_ = cat.get('topup')
    if ans.get('address'):
        if not rs._tu.valid_address(ans['address']):
            return {'say': '💸 That is not a Solana address.'}
        c_.update(address=ans['address'], source='owner', state='ask')
        return {'say': rs._tu.question(c_)}
    if not ans.get('yes'):
        cat.pop('topup', None)
        return {'say': '💸 Okay, no top-up. Nothing moved.'}
    if not c_.get('address'):
        return {'say': f"💸 I need your {c_['site']} deposit address first. Paste it here."}
    usd_ = ans.get('usd') or c_.get('usd')
    if not usd_:
        return {'say': '💸 How much? Say "yes, top up $1.50".', 'ask': True}
    c_['usd'] = usd_
    return {'send': usd_}


def _topup_start(cat, got):
    """The chat's "top up pump". → what to say. Finding the address is a browser read on its budget; a pasted address skips it."""
    rs = _rs()
    now = rs.time.time(); manuals_ = cat.get('siteManuals') or {}; site_ = rs._tu.site_for(got['word'], manuals_)
    if not site_:
        return f"💸 I have no manual for {got['word']} yet. Open a proof folder, type the site and hit Scan. Then ask again."
    if site_ not in (cat.get('siteSessions') or {}):
        return f'💸 {site_} is not signed in. Open it from its manual, sign in and save first.'
    if not rs._pays_itself(cat):
        return '💸 Only its own Circle wallet can send a top-up. This agent has none.'
    if got.get('address') and not rs._tu.valid_address(got['address']):
        return '💸 That is not a Solana address.'
    m_ = manuals_[site_]; c_ = rs._tu.card(site_, m_.get('url'), got.get('usd'), got.get('address'), 'owner', now)
    known_ = next((r['address'] for r in reversed(cat.get('topups') or []) if r.get('site') == site_), None)
    if not c_['address'] and known_:   # you already checked this one on a past send
        c_.update(address=known_, source='owner', state='ask')
    cat['topup'] = c_
    if c_['address']:
        return rs._tu.question(c_)
    cat['proofSite'] = {'site': site_, 'kind': 'topup', 'at': now}
    why_ = rs._read_start(cat, rs._tu.GOAL.format(site=site_, url=m_.get('url')), None, '')
    if why_:
        cat.pop('proofSite', None)
        return f"💸 I could not look for it ({why_}). Paste your {site_} deposit address here."
    cat['topupRead'] = {'at': round(now), 'tid': rs._WORK[cat['id']]['task']['id']}
    c_['state'] = 'reading'
    return f"💸 Looking for your {site_} deposit address in its window, signed in. Nothing will be sent until you say yes."


def _site_wallet(cat, site):
    """Its account's wallet on that site: a top-up address, or one its window read."""
    return next((r['address'] for r in reversed(cat.get('topups') or []) if r.get('site') == site and r.get('address')), None) or (cat.get('siteWallets') or {}).get(site) or ''


async def _token_balance(http, owner, mint):
    """The coin balance of a wallet on the chain, or None when the read failed. Zero means no coins, not a failed read."""
    rs = _rs()
    url_ = rs._crpc._next_rpc_endpoint() or 'https://api.mainnet-beta.solana.com'   # the live lane, never a spent key
    try:
        r = await http.post(url_, json={'jsonrpc': '2.0', 'id': 1, 'method': 'getTokenAccountsByOwner', 'params': [owner, {'mint': mint}, {'encoding': 'jsonParsed'}]}, timeout=10)
        rows = (r.json().get('result') or {})['value']
        return sum(float(x['account']['data']['parsed']['info']['tokenAmount']['uiAmount'] or 0) for x in rows)
    except Exception:   # noqa: BLE001 — no read is not a zero balance
        return None


async def _site_trade_chat(cat_id, order, ans):
    """🛒 One order or one answer → what it says. It writes onto the newest store, since a pair read takes a moment."""
    rs = _rs()
    now = rs.time.time(); pair_ = None; c_ = None
    if order:
        async with rs.httpx.AsyncClient(timeout=12) as http:
            pair_ = await rs._order_pair(http, order['coin'])
    store = rs._load(); cat = store['cats'][cat_id]
    if order:
        fact_ = rs._st.facts(pair_, now)
        why_ = rs._st.why_not(order, fact_, cat.get('siteTrades'), now)
        if why_:
            return f'🛒 Not placing that. {why_}'
        c_ = rs._st.card(order, fact_, now)
        if not cat.get('siteTradeAuto'):
            cat['siteTrade'] = c_; rs.keep_owned(cat); rs._save(store)
            return rs._st.question(c_)
    else:
        c_ = cat.get('siteTrade')
        if not c_ or rs._st.expired(c_, now):
            cat.pop('siteTrade', None); rs.keep_owned(cat); rs._save(store)
            return '🛒 That order timed out. Nothing was placed.'
        if not ans.get('yes'):
            cat.pop('siteTrade', None); rs.keep_owned(cat); rs._save(store)
            return '🛒 Okay, not placing it.'
        if ans.get('usd') and c_['side'] == 'buy':
            c_['usd'] = float(ans['usd'])
            why_ = rs._st.why_not(c_, {'mint': c_['mint'], 'sym': c_['sym'], 'pool': c_['pool'], 'ageS': c_['ageS'], 'run1h': c_['run1h']}, cat.get('siteTrades'), now)
            if why_:
                return f'🛒 Not placing that. {why_}'
    b_ = cat.get('brainsCfg') or {}; w_ = rs._WORK.get(cat_id)
    if w_ and not w_.get('done'):
        return '🛒 It is still working. Stop that first, then ask again. Nothing was placed.'
    if not rs._work_live(cat) or not rs._lc.can_ask(b_) or not b_.get('brains'):
        return '🛒 It has no model credit to work its window. Nothing was placed.'
    wallet_ = rs._site_wallet(cat, c_['site'])
    before_ = None
    if wallet_:
        async with rs.httpx.AsyncClient(timeout=12) as http:
            before_ = await rs._token_balance(http, wallet_, c_['mint'])
    store = rs._load(); cat = store['cats'][cat_id]
    cat.pop('siteTrade', None)
    cat['proofSite'] = {'site': c_['site'], 'kind': 'trade', 'at': now}
    rs._work_start(cat_id, cat, rs._st.goal(c_, wallet_), '1', [])
    cat.pop('workNow', None)   # an order is never resumed after a restart: it would run without its yes
    rs._WORK[cat_id]['task'].update(siteTrade={**c_, 'wallet': wallet_, 'before': before_}, youSaid=True)
    rs.keep_owned(cat); rs._save(store)
    warm_ = rs._warm_for(cat_id, c_['site'])
    return f"🛒 Placing it: {rs._st.words(c_)} on {c_['site']}. " + ('It works in the window you just cleared.' if warm_ else 'A new window may hit a bot check. If it does, it hands the window to you. Clear it and it carries on.')


def _site_trade_filed(cat, t):
    """Its window finished: keep the receipt. The chain settles it on the next pass."""
    rs = _rs()
    c_ = t['siteTrade']; now = rs.time.time(); wallet_ = c_.get('wallet') or ''; answer_ = t.get('answer') or t.get('why') or ''
    if not wallet_:
        found_ = rs._st.address_in(str(answer_).replace(c_['mint'], ''))
        if found_ and rs._tu.valid_address(found_):
            cat.setdefault('siteWallets', {})[c_['site']] = found_
    cat.pop('proofSite', None)
    cat['siteTrades'] = (list(cat.get('siteTrades') or []) + [rs._st.row(c_, wallet_, c_.get('before'), answer_, now)])[-rs._st.LEDGER_MAX:]


async def _site_trade_pass(store):
    rs = _rs()
    now = rs.time.time()
    for cat in store['cats'].values():
        if cat.get('siteTrade') and rs._st.expired(cat['siteTrade'], now):
            cat.pop('siteTrade', None)
        rows_ = [r for r in cat.get('siteTrades') or [] if r.get('state') == 'checking' and now - float(r.get('at') or 0) >= rs._st.CHECK_AFTER_S]
        if rows_:
            async with rs.httpx.AsyncClient(timeout=12) as http:
                for r in rows_:
                    rs._st.settle(r, await rs._token_balance(http, r['wallet'], r['mint']), now)
                    if r['state'] != 'checking':
                        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': rs._st.saying(r), 'at': now}])[-200:]


async def _topup_pass(store):
    rs = _rs()
    now = rs.time.time()
    for cat in store['cats'].values():
        rd_ = cat.get('topupRead')
        if rd_:
            done_, notes_, why_ = rs._read_check(cat, rd_, now)
            if done_:
                cat.pop('topupRead', None); cat.pop('proofSite', None); c_ = cat.get('topup')
                if c_ and not c_.get('address'):
                    a_ = rs._tu.address_in(notes_)
                    if a_:
                        c_.update(address=a_, source='read', state='ask')
                        line_ = rs._tu.question(c_) + ' It read this from the page, so type its last 4 characters in the card.'
                    else:
                        c_['state'] = 'needs_address'
                        line_ = f"💸 I could not find one address on {c_['site']}{' (' + why_ + ')' if why_ else ''}. Paste it here, and check it on the site."
                    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': line_, 'at': now}])[-200:]
        if cat.get('topup') and rs._tu.expired(cat['topup'], now):
            cat.pop('topup', None)
        rows_ = [r for r in cat.get('topups') or [] if r.get('after') is None and now - float(r.get('at') or 0) >= 20]
        if rows_:   # "loaded": the same address, read again after the send
            async with rs.httpx.AsyncClient(timeout=10) as http:
                for r in rows_:
                    r['after'] = await rs._lamports_sol(http, r['address'])
                    if r['after'] is None and now - float(r.get('at') or 0) > 600:
                        r['after'] = -1   # stop asking; the row keeps its tx


async def _site_scan_run(cat_id, url, site, kind, ctx):
    """🔎 A plain fetch first (free). A wall or no terms goes to its browser, with the owner's saved sign-in only if the site needs it. No check is ever passed for them."""
    rs = _rs()
    out = {'cat': cat_id, 'site': site, 'url': url, 'kind': kind, 'pages': [], 'jpg': None, 'wall': ''}
    try:
        async with rs.httpx.AsyncClient(timeout=20) as http:
            out['pages'] = await rs._ss.read_fetch(http, url, site)
            want_all = rs._ss.needs_browser(out['pages'])
            s_ = None; page_ = None; warm_ = rs._warm_for(cat_id, site)
            if warm_:
                warm_['busy'] = True
            try:
                s_, _ = ({'connect': warm_['connect'], 'warm': True}, []) if warm_ else await rs._cb.open_session(http, rs.os.environ, ctx if want_all else None)
                if s_.get('connect'):
                    page_ = await rs._cb.LivePage(s_['connect'], cookies=s_.get('cookies'), **({'plain': True} if warm_ else {})).start()
                    rows, out['jpg'] = await rs.asyncio.wait_for(rs._ss.read_browser(page_, url, site, snapshot_only=not want_all), rs.SCAN_BROWSER_S)
                    if want_all:   # the browser read wins where the fetch was walled
                        got_ = {r['kind'] for r in rows if r.get('ok')}
                        out['pages'] = rows + [r for r in out['pages'] if r.get('ok') and r['kind'] not in got_]
            except Exception as e:   # noqa: BLE001 — the fetch read still files; the manual says no snapshot
                out['browserWhy'] = str(e)[:80] or 'its browser did not open'
            finally:
                if page_:
                    try:
                        await page_.close()
                    except Exception:
                        pass
                if warm_:
                    warm_.pop('busy', None)
                elif s_ and s_.get('connect'):
                    try:
                        await rs._cb.close_session(http, rs.os.environ, s_)
                    except Exception:
                        pass
    except Exception as e:   # noqa: BLE001 — a scan that fails says why in its manual
        out['wall'] = str(e)[:120] or 'the scan failed'
    out['wall'] = out['wall'] or rs._ss.wall_of(out['pages'])
    rs._SCAN_DONE.append(out); rs._POW_WAKE.set()


async def _watch_pass(store):
    """👁 Each wallet in a new Watch a Wallet folder gets one chain check: does this address have real history. A model can name an address that was never a trader."""
    rs = _rs()
    url_ = rs._crpc._next_rpc_endpoint() or 'https://api.mainnet-beta.solana.com'   # the live lane, never a spent key
    rows_ = [(c, f) for c in store['cats'].values() for f in c.get('watchFolders') or [] if not f.get('checked')]
    if not rows_:
        return
    async with rs.httpx.AsyncClient(timeout=12) as http:
        for _, f_ in rows_:
            for w_, got_ in zip(f_['wallets'], await rs.asyncio.gather(*(rs._ac.chain_check(http, url_, w_['address']) for w_ in f_['wallets']))):
                w_.update(got_)
            f_['checked'] = True


async def _site_pass(store):
    """🔎 File what finished: its snapshot on disk, its manual, one small model call to reword it when it has budget. The site's own sentences stay underneath."""
    rs = _rs()
    await rs._watch_pass(store)
    await rs._topup_pass(store)
    await rs._site_trade_pass(store)
    await rs._warm_expire(rs.time.time())
    for cid_ in list(rs._SCAN_FILED):
        rs._SCAN_BUSY.pop(cid_, None); rs._SCAN_FILED.discard(cid_)
    while rs._SCAN_DONE:
        o = rs._SCAN_DONE.pop(0); cat = store['cats'].get(o['cat']); rs._SCAN_FILED.add(o['cat']); rs._POW_WAKE.set()
        if not cat:
            continue
        now = rs.time.time(); name_ = None
        if o.get('jpg'):
            try:
                d_ = rs.POWSHOTS_DIR / ('site' + rs.re.sub(r'[^a-z0-9]', '', o['cat'].lower())[:40]); d_.mkdir(parents=True, exist_ok=True)
                name_ = rs.re.sub(r'[^a-z0-9.]', '', o['site']) + '.jpg'; (d_ / name_).write_bytes(rs._ck.seal_bytes(o['jpg'], o['cat']))
            except OSError:
                name_ = None
        m = rs._ss.build(o['site'], o['kind'], o['url'], o['pages'], now, name_, o['wall'])
        if o.get('browserWhy'):
            m['browserWhy'] = o['browserWhy']
        b_ = cat.get('brainsCfg') or {}
        if m['state'] != 'unread' and b_.get('brains') and (float(b_.get('credit') or 0) - rs._lc.CREDIT_RESERVE > 0.005 or rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)):
            lines_, index_ = rs._ss.polish_prompt(m)
            if lines_:
                box_ = {'cost': 0}
                try:
                    reply_ = await rs.asyncio.wait_for(rs._pow2_ask(cat, 0, rs._ss.POLISH_SYS, lines_, 500, box_), 30)
                except rs.asyncio.TimeoutError:
                    reply_ = ''
                m = rs._ss.apply_polish(m, reply_, index_, str(b_['brains'][0]).split('/')[-1]); m['cost'] = box_.get('cost', 0)
        rows_ = dict(cat.get('siteManuals') or {}); rows_[o['site']] = rs._ss.merge(rows_.get(o['site']), m); cat['siteManuals'] = rs._ss.trim(rows_)
        say_ = {'unread': f"🔎 Could not read {o['site']}: {m['wall'] or 'no page answered'}. Press Open + sign in: it opens the same window if it is still up. Clear the check, then save.", 'thin': f"🔎 Read {o['site']}, but found no terms page. Its manual says what it did find."}.get(m['state']) or f"🔎 {o['site']} is scanned. Its manual is in the folder."
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': say_, 'at': now, 'open': {'pop': 'pop', 'pob': 'bids'}.get(o['kind'], 'pow')}])[-200:]


def _read_start(cat, goal, who, kind=''):
    """🌐 (owner 2026-11-04: "trader agent browses sites as it files pow, pop, pob"). Its minds open real windows, on the research list only. → '' when started, else why it could not."""
    rs = _rs()
    w_ = rs._WORK.get(cat['id']); b_ = cat.get('brainsCfg') or {}
    if w_ and not w_.get('done'):
        return 'its windows were busy'
    if not rs._work_live(cat):
        return 'browsing is off on this server'
    if not b_.get('brains') or (float(b_.get('credit') or 0) - rs._lc.CREDIT_RESERVE <= 0.005 and not rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)):
        return 'no model credit left for browsing'
    try:
        rs._work_start(cat['id'], cat, goal + rs._site_note(cat, kind) + (rs._book.goal_line(cat.get('siteBook'), kind) if kind in rs._book.KINDS else ''), who if who in ('0', '1') else None, None, read_=True, kind=kind or None)
    except rs.HTTPException as e:
        return str(e.detail)[:80]
    if kind in ('pob', 'poc', 'pos'):   # the sources book + the PoW guide list coin sites (Birdeye, Jupiter, RugCheck): GLM followed them on a Knicks pick (2026-11-07)
        rs._WORK[cat['id']]['task'].update(knowhow=rs._colony.KNOWHOW, alts=[])
    if kind in rs._book.KINDS and (cat.get('siteBook') or {}).get(kind):   # 📚 a repeating window moves to the owner's next site, never an off one
        t_b_ = rs._WORK[cat['id']]['task']; t_b_['alsoHosts'] = rs._foot.order_sites(kind, rs._book.apply(cat['siteBook'], kind, list(t_b_.get('alsoHosts') or []) + rs._book.DEFAULTS[kind]), cat.get(rs._PROOF_KEYS.get(kind)))   # 🧭 the sites the last proofs leaned on go last
    rs._WORK[cat['id']]['task']['stepsMax'] = rs._foot.read_steps(kind, rs.READ_STEPS, (cat.get('limits') or {}).get('steps'))   # 🔁 his own steps limit (owner 2026-11-15 'set to 30'), PoP's lower budget kept
    rs._WORK[cat['id']]['task']['proofKind'] = kind or 'proof'   # 🗂 AGT-9: this job is filed in Jobs under its proof
    rs._WORK[cat['id']]['task']['notCoins'] = kind in ('pob', 'poc', 'pos')   # the coin research order (RugCheck, Solscan) is only for coins: it was sent to every window, so a game pick opened a rug checker
    return ''


def read_note(w):
    """A window's summary; when it ran out of budget before writing one, the text of the pages it really read. Nothing else is ever handed to the minds. Pure."""
    said = str(w.get('answer') or '').strip()
    if len(said) > 80 and not said.startswith(('⏹', '(error)')):
        return said[:600]
    pages = ' | '.join(f"{site}: {text}" for site, text in list((w.get('_read') or {}).items())[:4])
    return f'{said} {pages}'.strip()[:2000]


def _read_notes(t):
    """What each window actually opened and answered. A site it never reached is not listed. → {mind: {'sites', 'note'}}."""
    rs = _rs()
    out = {}
    for w in t.get('windows') or []:
        sites = sorted({rs._pow.host_of(s.get('detail')) for s in w.get('steps') or [] if s.get('action') == 'open' and str(s.get('detail') or '').startswith('http')} - {'', None})
        if w.get('goal'):
            out[str(w.get('i'))] = {'sites': sites, 'note': rs.read_note(w), 'cost': round(float(w.get('cost') or 0), 5)}
            for site_ in {rs._pow.host_of(k) for k in (w.get('_read') or {})} - {'', None}:   # 📖 a page it really read counts as a visit, so its first-sources list is true
                rs._src_note(site_, True)
            print(f"[read] mind {w.get('i')}: {len(w.get('steps') or [])} steps, {len(sites)} sites, status {w.get('status')}, ${float(w.get('cost') or 0):.4f}, answer: {str(w.get('answer') or '')[:90]!r}")
    return out


def _read_check(cat, rd, now):
    """→ (done, notes, why). A read that outlives READ_S is stopped and files what it reached; one a restart lost files as not browsed, and says so."""
    rs = _rs()
    w_ = rs._WORK.get(cat['id']); t_ = (w_ or {}).get('task') or {}
    if t_.get('id') != rd.get('tid'):
        return True, {}, 'its browser session ended before the read finished'
    if w_.get('done'):
        return True, rs._read_notes(t_), ''
    if now - float(rd.get('at') or now) < rs.READ_S:
        return False, None, ''
    t_['stop'] = True
    return True, rs._read_notes(t_), 'time ran out on the read'


def _made_refusal(cat, job):
    """Why it can't make this now, or '' when it can. A picture goes on FEELESS's image key and is charged to its own model budget, so an own key does not cover it."""
    rs = _rs()
    b_ = cat.get('brainsCfg') or {}; left_ = float(b_.get('credit') or 0) - rs._lc.CREDIT_RESERVE; own_ = job['kind'] == 'page' and rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
    why_ = rs._ca.refusal(job['prompt'])
    if why_:
        return f'🛑 {why_}'
    if not rs._work_live(cat):
        return '⏸ Model calls are off on this server.'
    if cat['id'] in rs._MADE_BUSY:
        return '🎨 It is still making the last one.'
    if not b_.get('brains'):
        return '🎨 It needs a model first.'
    est_ = {'image': rs.IMAGE_EST_USD, 'project': rs.PROJECT_EST_USD}.get(job['kind'], rs.PAGE_EST_USD)
    if not own_ and left_ < est_:
        return f"🎨 Its model budget is too low: this needs about ${est_:.2f}."
    left_day = rs.day_left(cat)
    if left_day is not None and left_day <= 0:
        return "🎨 It reached today's $ limit."
    return ''


async def _made_job(cat_id, job, cat):
    """One picture or page. Its result waits for the engine pass; nothing here writes the store."""
    rs = _rs()
    out = {'cat': cat_id, 'job': job, 'usd': 0.0, 'why': '', 'own': False}
    try:
        if job['kind'] == 'image':
            async with rs.httpx.AsyncClient(timeout=110) as http:
                r = await http.post(f'{rs._ct.REP}/api/reputation/internal/agent-image', headers=rs._at._internal_headers(), json={'prompt': job['prompt']})
            j = r.json() or {}
            out.update(usd=float(j.get('usd') or 0) or rs.IMAGE_EST_USD if j.get('url') else 0.0, url=j.get('url'), why='' if j.get('url') else str(j.get('detail') or j.get('why') or 'no picture came back')[:160])
        elif job['kind'] == 'project':
            own_ = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
            reply_, usd_, _via = await rs._think(cat, cat['brainsCfg']['brains'][0], [{'role': 'system', 'content': rs._ac.PROJECT_SYS}, {'role': 'user', 'content': job['prompt']}], own_, None, rs.PROJECT_TOKENS)
            files_ = rs._ac.project_in(reply_)
            out.update(usd=float(usd_ or 0), own=bool(own_), files=files_, why='' if files_ else 'the model did not finish a whole project')
        else:
            own_ = rs._ck.key_for(cat, 'openrouter', data_dir=rs.DATA_DIR)
            reply_, usd_, _via = await rs._think(cat, cat['brainsCfg']['brains'][0], [{'role': 'system', 'content': rs._ac.PAGE_SYS}, {'role': 'user', 'content': job['prompt']}], own_, None, rs.PAGE_TOKENS)
            html_ = rs._ac.page_in(reply_)
            out.update(usd=float(usd_ or 0), own=bool(own_), html=html_, why='' if html_ else 'the model did not finish a whole page')
    except Exception as e:   # noqa: BLE001 — it says so in the chat
        out['why'] = f'{type(e).__name__}'
    rs._MADE_DONE.append(out); rs._MADE_BUSY.discard(cat_id); rs._POW_WAKE.set()


def _internal_key_read():
    rs = _rs()
    return (rs.DATA_DIR / 'internal.key').read_text().strip()


async def _card_seat_send(http, f, c, tr_, now):
    """🎩 Asks the card to consider this coin for a free seat. The card's own guards decide; nothing is bought here. → {ok, why, at}"""
    rs = _rs()
    try:
        r = await http.post('http://127.0.0.1:5077/api/reputation/internal/sicario-want', headers={'x-feeless-internal': rs._internal_key_read()}, timeout=8, json={'mint': c.get('mint'), 'pair': c.get('pair'), 'symbol': c.get('sym'), 'tp': tr_.get('tp'), 'sl': tr_.get('sl'), 'why': str(f.get('why0') or 'both minds agreed')[:110], 'folder': f.get('id')})
        j = r.json() if r.status_code == 200 else {'ok': False, 'why': f'the card service answered {r.status_code}'}
    except (rs.httpx.HTTPError, ValueError) as e:
        j = {'ok': False, 'why': f'the card service did not answer ({type(e).__name__})'}
    return {'ok': bool(j.get('ok')), 'why': j.get('why'), 'at': round(now)}


async def _card_seat_fates(http, store, now):
    """🎩 What the card did with each coin Sicario's sent, on the folder. A sent coin is not a bought coin."""
    rs = _rs()
    for c in store['cats'].values():
        if c.get('handle') != 'sicarios':
            continue
        for f in (c.get('powFolders') or [])[-5:]:
            s_ = f.get('cardSeat') or {}
            if s_.get('ok') and not s_.get('fate') and now - float(s_.get('at') or 0) >= 20:
                try:
                    r = await http.get(f"http://127.0.0.1:5077/api/reputation/internal/sicario-want?mint={f.get('mint')}", headers={'x-feeless-internal': rs._internal_key_read()}, timeout=5)
                    if r.status_code == 200 and r.json().get('fate'):
                        s_['fate'] = str(r.json()['fate'])[:120]; rs._pow2_say(f, 'engine', f"the card: {s_['fate']}")
                except (rs.httpx.HTTPError, ValueError):
                    pass


async def _sicario_free(http, store):
    """🎩 Free seats on the card, asked only while Sicario's is in Auto-collect. None = no answer, so nothing is filed."""
    rs = _rs()
    if not rs._self_start_ok() or not any(c.get('handle') == 'sicarios' and (c.get('hive') or {}).get('on') and not c.get('revoked') for c in store['cats'].values()):
        return None
    try:
        r = await http.get('http://127.0.0.1:5077/api/reputation/internal/sicario-want', headers={'x-feeless-internal': rs._internal_key_read()}, timeout=5)
        return ((r.json().get('seats') or {}).get('free')) if r.status_code == 200 else None
    except (rs.httpx.HTTPError, ValueError):
        return None


def _sicario_loop(store, now, free=None):
    """🎩 Two ways it keeps working. Auto-collect (its hive on): PoWs until the card's seats are full, each one sent to a free seat. Endless: the next proof of any kind as soon as it is idle and rested. It has no wallet."""
    rs = _rs()
    if not rs._self_start_ok():   # 🛑 discontinued (SELF_START) · 🛡 AGX-7: no Auto-collect seats and no Endless proofs while the owner has agents paused
        return
    for c in store['cats'].values():
        b_ = c.get('brainsCfg') or {}; cid = c.get('id')
        if rs._sicario_paused(c):
            continue
        fill = bool((c.get('hive') or {}).get('on')) and int(free or 0) > 0
        if c.get('handle') != 'sicarios' or not (b_.get('endless') or fill) or c.get('agentWallet') or c.get('revoked'):
            continue
        if (c.get('powRun') or {}).get('folder') or c.get('popRun') or c.get('popCard') or c.get('popRead') or c.get('pobRead') or c.get('pobRun') or cid in rs._POC_BUSY or cid in rs._POW_WANT or cid in rs._POP_WANT or cid in rs._POB_WANT:
            continue
        if now - float(b_.get('loopAt') or 0) < (rs.SICARIO_FILL_GAP_S if fill else rs.SICARIO_GAP_S):
            continue
        if fill:
            b_['cardSeat'] = True; b_['loopAt'] = now; rs._POW_WANT[cid] = {'do': 'start', 'mind': None}; rs._POW_WAKE.set()
            continue
        i = int(b_.get('loopI') or 0); kind = rs.SICARIO_QUESTS[i % len(rs.SICARIO_QUESTS)]; b_['loopI'] = i + 1; b_['loopAt'] = now
        if kind == 'pow':
            rs._POW_WANT[cid] = {'do': 'start', 'mind': None}
        elif kind == 'pop':
            rs._POP_WANT[cid] = 'start'
        elif kind == 'pob':
            rs._POB_WANT[cid] = 'start'; c['pobBy'] = 'auto'
        else:
            rs._POC_BUSY.add(cid); rs.asyncio.create_task(rs._poc_file(cid, ''))
        rs._POW_WAKE.set()


def _proof_won(kind, f):
    """True, False, or None while it has no result. The same lines the rubric reads."""
    if kind == 'pow':
        return None if f.get('status') != 'closed' or f.get('pnlPct') is None else float(f.get('pnlPct')) > 0
    if kind == 'pop':
        return None if f.get('noTrade') or f.get('status') != 'closed' or f.get('roePct') is None else float(f.get('roePct')) > 0
    return {'right': True, 'wrong': False}.get(f.get('graded'))


def _kit_record(store=None):
    """🧰 What each kit has really done: proofs that read it and how they came out. Read from the proofs themselves, at most every 5 minutes."""
    rs = _rs()
    if rs.time.time() - rs._KIT_RECORD['at'] < 300:
        return rs._KIT_RECORD['rows']
    out = {}; store = store if store is not None else rs._load()
    for cat in (store.get('cats') or {}).values():
        for kind, key in rs._PROOF_KEYS.items():
            seen = {}
            for f in cat.get(key) or []:
                if not isinstance(f, dict):
                    continue
                used = f.get('kits') or []
                if kind == 'pos' and not used and f.get('ws'):
                    used = [k.get('id') for k in (rs._ws_load(cat.get('id'), f['ws']) or {}).get('kitsUsed') or [] if isinstance(k, dict) and k.get('used')]
                seen[f.get('ws') or f.get('id')] = (used, rs._proof_won(kind, f))   # the newest version of a page speaks for it
            for used, won in seen.values():
                for kid in used:
                    r = out.setdefault(kid, {'used': 0, 'won': 0, 'lost': 0}); r['used'] += 1
                    if won is not None:
                        r['won' if won else 'lost'] += 1
    rs._KIT_RECORD.update(at=rs.time.time(), rows=out)
    return out


def _wallet_think(cat_id, now=None, days=7):
    """What its models really cost over the last week, read from the paid receipts. → {usd, perDay, calls, days}"""
    rs = _rs()
    now = now or rs.time.time(); usd = 0.0; calls = 0; first = now
    try:
        with (rs.DATA_DIR / 'model_receipts.jsonl').open() as f_:
            for line_ in f_:
                if cat_id not in line_:
                    continue
                r_ = rs.json.loads(line_)
                if r_.get('cat') == cat_id and now - float(r_.get('at') or 0) <= days * 86400:
                    usd += float(r_.get('usd') or 0); calls += 1; first = min(first, float(r_['at']))
    except (OSError, ValueError):
        pass
    span = max(1.0, (now - first) / 86400) if calls else 1.0
    return {'usd': round(usd, 4), 'perDay': round(usd / span, 4), 'calls': calls, 'days': round(span, 1)}


def _idea_facts(store):
    """Real counts for the minds to pitch from. No names, wallets or keys."""
    rs = _rs()
    cats = [c for c in store['cats'].values() if not c.get('revoked')]; kinds = {k: [f for c in cats for f in c.get(key) or [] if isinstance(f, dict)] for k, key in rs._PROOF_KEYS.items()}
    st_ = rs._debate.load(rs.DATA_DIR)
    return rs.json.dumps({'agents': len(cats), 'proofs': {k: {'filed': len(v), 'right': sum(1 for f in v if rs._proof_won(k, f) is True), 'wrong': sum(1 for f in v if rs._proof_won(k, f) is False)} for k, v in kinds.items()}, 'debate': {'onTable': len(st_['table']), 'settled': sum(1 for r in st_['table'] if r.get('settled'))}, 'kitsUsedMost': sorted(((k, v['used']) for k, v in rs._kit_record(store).items()), key=lambda x: -x[1])[:5], 'assets': sum(len(v) for v in (rs._assets._load(rs.KITS_DIR, rs._assets.INDEX).get('rows') or {}).values())})


async def _live_read(cat, site, force=False, now=None):
    """📡 One watched page: did it really change, and is it worth saying something? Reads the page only, no sign-in. → what happened, in words"""
    rs = _rs()
    now = now or rs.time.time(); brains = (cat.get('brainsCfg') or {}).get('brains') or []
    if not brains:
        return 'Pick a model for this agent first.'
    if not rs._kits._public_host(site.get('host') or ''):
        return 'That page is not public.'
    async with rs.httpx.AsyncClient(timeout=20, follow_redirects=False) as h_:
        r_ = await h_.get(site['url'], headers={'User-Agent': 'Mozilla/5.0 (FEELESS live desk)'})
    site['readAt'] = round(now)
    if r_.status_code != 200:
        site['note'] = f'It would not open ({r_.status_code}).'
        return site['note']
    text_ = rs._pw.page_text(r_.text); had_ = rs._play_load(cat['id'], f"live{site['id']}") or {}; fresh_ = rs._pw.changes(had_.get('text'), text_) if had_.get('text') else text_[:rs._pw.MAX_TEXT]
    rs._play_save(cat['id'], f"live{site['id']}", {'text': text_[:rs._pw.MAX_TEXT * 2]})
    if had_.get('text') and not fresh_:
        site['note'] = 'Nothing new.'
        return site['note']
    if not rs._pw.can_draft(site, now):
        site['note'] = 'Changed, but it reached its 4 drafts for today.'
        return site['note']
    raw_, _u, _o = await rs._ws_ask(cat, brains[0], rs._pw.SYS + rs._play.notes_line(cat, 'live'), rs._pw.ask_text(site, fresh_ or text_[:rs._pw.MAX_TEXT]), 600); rs._pw.note_draft(site, now); row_, why_ = rs._pw.parse(raw_)
    site['checks'] = int(site.get('checks') or 0) + 1; site['lastUsd'] = round(float(_u or 0), 5); site['spentUsd'] = round(float(site.get('spentUsd') or 0) + float(_u or 0), 5); site['lastAt'] = round(now)   # 💵 what each read really cost
    if row_:
        row_.update(site=site['host'], url=site['url'], at=round(now)); cat['pocDrafts'] = (list(cat.get('pocDrafts') or []) + [row_])[-40:]; site['note'] = 'New draft.'
        return f"New draft: {row_['happened']}"
    site['note'] = f"Not worth a word: {why_}" if why_ else 'The agent sent nothing usable.'
    return site['note']


def _live_view(cat, sites, drafts):
    """📡 The live desk's state: its pages (with what each read really cost), drafts, the model that reads, and the agent's PoC files
    (a PoC's name + its first ask become a page's agenda in one tap)."""
    rs = _rs()
    brains = (cat.get('brainsCfg') or {}).get('brains') or []
    paid = [r['lastUsd'] for r in sites if r.get('checks') and r.get('lastUsd') is not None]
    pocs = []
    for w in (cat.get('workspaces') or [])[-24:][::-1]:
        if w.get('kind') != 'content':
            continue
        doc = rs._ws_load(cat['id'], w.get('id')) or {}
        first = next((m.get('text') for m in doc.get('messages') or [] if m.get('by') == 'you' and m.get('text')), '')
        pocs.append({'id': w.get('id'), 'name': w.get('name'), 'agenda': str(first or w.get('name') or '')[:240]})
    return {'sites': sites, 'drafts': drafts, 'canAsk': bool(brains), 'model': brains[0] if brains else None,
            'perReadUsd': round(sum(paid) / len(paid), 5) if paid else None, 'spentUsd': round(sum(float(r.get('spentUsd') or 0) for r in sites), 4),
            'pocs': pocs[:12], 'limits': {'pages': rs._pw.MAX_SITES, 'draftsPerPageDay': rs._pw.DAY_DRAFTS}}


async def _pocwatch_check(cat, w, now=None):
    """👁 One PoC watch check: read the public page, keep its fingerprint, ask the model only when it really changed. → the check row"""
    rs = _rs()
    now = round(now or rs.time.time()); brains = rs._lc.minds_for(cat.get('brainsCfg'), 'poc') or (cat.get('brainsCfg') or {}).get('brains') or []
    row = {'at': now, 'ok': False}
    if not rs._kits._public_host(w.get('host') or ''):
        row['why'] = 'That page is not public.'; rs._pw.add_check(w, row); return row
    try:
        async with rs.httpx.AsyncClient(timeout=20, follow_redirects=False) as h_:
            r_ = await h_.get(w['url'], headers={'User-Agent': 'Mozilla/5.0 (FEELESS PoC watch)'})
    except rs.httpx.HTTPError as e:
        row['why'] = f'It would not open ({type(e).__name__}).'; rs._pw.add_check(w, row); return row
    if r_.status_code != 200:
        row['why'] = f'It would not open ({r_.status_code}).'; rs._pw.add_check(w, row); return row
    text_ = rs._pw.page_text(r_.text); key_ = f"watch{w['id']}"; had_ = rs._play_load(cat['id'], key_) or {}
    fresh_ = rs._pw.changes(had_.get('text'), text_) if had_.get('text') else ''
    rs._play_save(cat['id'], key_, {'text': text_[:rs._pw.MAX_TEXT * 2]})
    row.update(ok=True, sha=rs.hashlib.sha256(text_.encode()).hexdigest()[:16], chars=len(text_), changed=bool(fresh_) or not had_.get('text'), newLines=len(fresh_.splitlines()) if fresh_ else 0, usd=0.0)
    prev_ = next((c for c in reversed(w.get('checks') or []) if c.get('ok') and c.get('steps')), None)
    if had_.get('text') and not fresh_ and prev_:
        row.update(steps=prev_['steps'], headline=prev_.get('headline', ''), carried=True)   # 💤 nothing new on the page: the last answers stand, no model spent
    elif not brains:
        row.update(ok=False, why='Pick a model for this agent first.')
    else:
        rs._CALL_CTX.set({'kind': 'poc', 'ref': w['id'], 'minds': brains[:1]})
        raw_, usd_, own_ = await rs._ws_ask(cat, brains[0], rs._pw.WATCH_SYS, rs._pw.ask_watch(w, text_, fresh_), 500)
        head_, steps_ = rs._pw.parse_watch(raw_, len(w['steps']))
        row['usd'] = round(float(usd_ or 0), 5)
        if usd_ and not own_ and cat.get('brainsCfg'):
            rs._lc.charge(cat['brainsCfg'], float(usd_))
        if steps_ is None:
            row.update(ok=False, why='The model sent nothing usable.')
        else:
            row.update(headline=head_, steps=steps_)
    rs._pw.add_check(w, row)
    return row


def _pocwatch_file(cat, w, now=None):
    """📋 The watch is over: the SHORT report becomes a PoC folder (proof: every check's time, page fingerprint and answers stay on it)."""
    rs = _rs()
    now = round(now or rs.time.time()); rep_ = rs._pw.report(w); w.update(status='done', doneAt=now, report=rep_)
    rows_ = list(cat.get('pocFolders') or [])
    rows_.append({'id': f'poc{rs.secrets.token_hex(5)}', 'n': rs._next_n(rows_), 'kind': 'PoC', 'by': 'Watch', 'at': now, 'status': 'closed', 'paper': True,
                  'topic': f"Watch · {w['host']}"[:60], 'calls': [], 'cost': rep_['spentUsd'],
                  'watch': {'id': w['id'], 'url': w['url'], 'steps': w['steps'], 'hours': w['hours'], 'perHour': w['perHour'], 'startedAt': w['startedAt'], 'report': rep_,
                            'checks': [{k: c.get(k) for k in ('at', 'ok', 'sha', 'changed', 'newLines', 'usd', 'headline', 'steps', 'why', 'carried')} for c in w.get('checks') or []]}})
    cat['pocFolders'] = rows_[-60:]
    seen_ = sum(1 for x in rep_['steps'] if x['verdict'] == 'seen')
    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"👁 PoC watch on {w['host']} is done: {rep_['read']} checks in {w['hours']} h, {seen_} of {len(rep_['steps'])} steps seen, ${rep_['spentUsd']:.4f}. The report is in the PoC folder.", 'at': rs.time.time(), 'open': 'poc'}])[-200:]
    return rows_[-1]


async def _pocwatch_pass(store):
    """Every 5 minutes: each running watch that is due gets one check, one at a time; a finished one files its report."""
    rs = _rs()
    if rs._POCWATCH_BUSY[0]:
        return
    rs._POCWATCH_BUSY[0] = True
    try:
        for cat in list((store.get('cats') or {}).values()):
            if cat.get('revoked'):
                continue
            for wid in [x.get('id') for x in cat.get('pocWatches') or []]:
                now = rs.time.time(); w = next((x for x in cat.get('pocWatches') or [] if x.get('id') == wid), None)   # looked up again: each save swaps in fresh copies
                if not w or not rs._pw.due(w, now):
                    continue
                try:
                    if now < float(w['endsAt']):
                        await rs._pocwatch_check(cat, w, now)
                    else:
                        rs._pocwatch_file(cat, w, now)
                    rs.keep_owned(cat); rs._save(store)
                except Exception as e:   # noqa: BLE001 — one dead page never stops the rest
                    print(f'[watch] {str(e)[:120]}')
    finally:
        rs._POCWATCH_BUSY[0] = False


def _pocwatch_view(cat):
    rs = _rs()
    brains = rs._lc.minds_for(cat.get('brainsCfg'), 'poc') or (cat.get('brainsCfg') or {}).get('brains') or []
    paid = [c['usd'] for w in cat.get('pocWatches') or [] for c in w.get('checks') or [] if c.get('ok') and not c.get('carried') and c.get('usd') is not None]
    return {'watches': list(cat.get('pocWatches') or [])[::-1], 'model': brains[0] if brains else None, 'perAskUsd': round(sum(paid) / len(paid), 5) if paid else None,
            'limits': {'watches': rs._pw.MAX_WATCHES, 'steps': rs._pw.MAX_STEPS, 'hours': 24, 'perHour': 4}}


async def _live_pass(store):
    """Every 30 minutes, each page that is on and an hour old. One at a time, so it never loads the machine."""
    rs = _rs()
    if rs._LIVE_BUSY[0]:
        return
    rs._LIVE_BUSY[0] = True
    try:
        for cat in list((store.get('cats') or {}).values()):
            for site in cat.get('pocWatch') or []:
                if site.get('on') and rs.time.time() - float(site.get('readAt') or 0) > 3600 and not cat.get('revoked'):
                    try:
                        await rs._live_read(cat, site); rs.keep_owned(cat)
                    except Exception as e:   # noqa: BLE001 — one dead site never stops the rest
                        site['note'] = f'It would not open ({type(e).__name__}).'; print(f'[live] {str(e)[:100]}')
    finally:
        rs._LIVE_BUSY[0] = False


async def _eco_check_pass(store):
    """🤖 One check a day for each agent whose owner turned its PoEco agent on, on its own model. A failed day is tried again in an hour. It only writes a note."""
    rs = _rs()
    today = rs.time.strftime('%Y-%m-%d', rs.time.gmtime()); done = 0
    for cat in list((store.get('cats') or {}).values()):
        brains = rs._lc.minds_for(cat.get('brainsCfg'), 'poe')
        if not cat.get('poeAi') or not brains or cat.get('revoked'):
            continue
        try:
            desk = rs._eco_desk_load(cat['id'])
            if not rs._eco.check_due(desk, today):
                continue
            raw, _u, _o = await rs._ws_ask(cat, brains[0], rs._eco.ECO_SYS, f'THE BOOKS: {rs._eco.ai_facts(desk, today)}\nOWNER: {rs._eco.CHECK_ASK}', 500); said, _r = rs._eco.parse_ai(raw)
            if said:
                desk = rs._eco_desk_load(cat['id']); rs._eco.add_check(desk, said, today); rs._eco_desk_save(cat['id'], desk); done += 1
        except Exception as e:   # noqa: BLE001 — one agent's books never stop the others
            print(f'[eco] check: {str(e)[:100]}')
    return done


def _debate_bank(st):
    """🥊 A finished room's points raise real boost ceilings, once, and only when both seats have a stake, so an empty account cannot farm them. No money moves: a ceiling is still paid only from real pool profit. → True when a room was settled here"""
    rs = _rs()
    rows = rs._debate.to_bank(st)
    if not rows:
        return False
    now = rs.time.time()
    def run(state):
        out = {}
        for r in rows:
            both = rs._stake.staked(state, r['a']['cat']) and rs._stake.staked(state, r['b']['cat'])
            out[r['id']] = {side: rs._stake.add_debate(state, f"debate:{r['id']}", r[side]['cat'], (r.get('totals') or {}).get(side, 0), now) for side in 'ab'} if both else {}
        return out
    try:
        got = rs._cpool.update(rs.POOL_PATH, run)
    except Exception as e:   # the ledger was busy or unreadable: the room keeps its record and is offered again on the next read
        print(f'[debate] bank: {str(e)[:100]}')
        return False
    for r in rows:
        r['banked'] = got.get(r['id']) or {}
    return True


async def _debate_pass(store):
    """⚔ Each agent whose owner allows it grades its next proof on the table, on its own AI, a few a day, and moves on until none are left. A bad reply is not saved and costs that proof nothing."""
    rs = _rs()
    if not rs.SELF_START:   # 🛑 grading on its own AI by itself is self-started usage: discontinued (owner 2026-11-14)
        return 0
    if rs._DEBATE_BUSY[0]:
        return 0
    rs._DEBATE_BUSY[0] = True; done = 0
    try:
        for cat in list((store.get('cats') or {}).values()):
            cfg = cat.get('brainsCfg') or {}; model = (cfg.get('brains') or [None])[0]
            if not cfg.get('debateOn') or not model or cat.get('revoked'):
                continue
            st = rs._debate.load(rs.DATA_DIR); kinds = [k for k, key in rs._PROOF_KEYS.items() if cat.get(key)]; row = rs._debate.next_for(st, cat['id'], kinds)
            if not row or rs._debate.used_today(st, cat['id']) >= rs._debate.PER_DAY:
                continue
            try:
                raw, _usd, _own = await rs._ws_ask(cat, model, rs._debate.SYSTEM, rs._debate.ask_text(row), 400)
            except Exception as e:   # noqa: BLE001 — one agent's failure never stops the floor
                print(f'[debate] {str(e)[:100]}')
                continue
            got = rs._debate.parse_take(raw)
            if got:
                st = rs._debate.load(rs.DATA_DIR)   # read again: the model call gave others time to write
                try:
                    rs._debate.take(st, row['id'], cat['id'], cat.get('name'), got); rs._debate.save(rs.DATA_DIR, st); done += 1
                except ValueError:
                    pass
    finally:
        rs._DEBATE_BUSY[0] = False
    return done


async def _kit_minds_pass():
    """🧠 OSSY and G4 ask for better tools in their own words, the search runs on those words, and each says what it would really use. Free. Nothing they say reaches a proof: the owner approves. → what they said"""
    rs = _rs()
    said = []
    for mind, name in (('local/ossy', 'OSSY'), ('local/g4', 'G4')):
        try:
            have_ = ', '.join(sorted(k['name'] for k in rs._kits.all_rows(rs.KITS_DIR)))[:900]
            ask_, _u = await rs._lm_call(mind, [{'role': 'system', 'content': rs._kits.MIND_ASK.format(have=have_)}, {'role': 'user', 'content': 'What should we search for?'}], 300)
            if not str(ask_ or '').strip():
                said.append(f'{name} is off right now.'); continue
            if rs._kits.note_queries(rs.KITS_DIR, ask_):
                async with rs.httpx.AsyncClient() as h_:
                    await rs._kits.scout(h_, rs.KITS_DIR)
            new_ = [r for r in rs._kits.proposed_rows(rs.KITS_DIR) if r.get('status') == 'new'][:14]
            if new_:
                rated_, _u = await rs._lm_call(mind, [{'role': 'system', 'content': rs._kits.MIND_RATE}, {'role': 'user', 'content': '\n'.join(f"{r['name']} ({r['kinds'][0]}): {r['what']}" for r in new_)}], 300)
                why_ = rs._kits.note_rating(rs.KITS_DIR, name, rated_)
                said.append(f'{name}: {why_}' if why_ else f'{name} would use none of these.')
        except Exception as e:   # noqa: BLE001 — a mind that fails never stops the rest
            print(f'[kits] {name}: {str(e)[:100]}')
            said.append(f'{name} could not finish.')
    return ' · '.join(said)


def _convo(cat):
    rs = _rs()
    return rs._foot.convo_line(rs._play_load((cat or {}).get('id'), 'convo'))


def _proof_brain(cat, kind):
    """🧠 Owner 2026-11-07: a selected agent takes this in by itself. How this kind of proof scores and where its last one lost. Never on a PoW, whose picks can buy real coins: no trading rule or incentive moves."""
    rs = _rs()
    if not kind or kind == 'pow':
        return ''
    rows = [f for f in cat.get(rs._PROOF_KEYS.get(kind)) or [] if isinstance(f, dict)]
    return rs._know.score_line(kind) + (rs._know.weak_line(rs._proof_view(cat, kind, rows[-1])) if rows else '') + rs._debate.lessons(rs._debate.load(rs.DATA_DIR), cat.get('id'), kind) + (rs._play.notes_line(cat, 'edit') if kind == 'poc' else rs._play.notes_line(cat, '3d') if kind == 'pos' else '')


def _job_brain(cat, text):
    """🧠 What a chat job starts with, whatever was asked: where it is, and what the Collective already proved on this. Titles and results only, read from this server. Never stops a job."""
    rs = _rs()
    try:
        words_ = rs.re.findall(r"[A-Za-z0-9$][A-Za-z0-9$-]{2,}", str(text or ''))[:10]; return '\n' + rs._know.WHERE + rs._feat._sources.recall_line(rs._stash.related(rs.STASH_DIR, words_, None, 4), rs._stash.agent_tag(cat.get('id'))) + rs._feat._sources.best_line(rs._stash.best_for(rs.STASH_DIR, words_, None, 2), rs._stash.agent_tag(cat.get('id')))
    except Exception as e:   # noqa: BLE001
        print(f'[brain] {str(e)[:100]}')
        return ''


def _stash_best(cat, category, text):
    """🔎 The best proofs the Collective holds on this, for its minds. The owner never gets this. Never stops a proof."""
    rs = _rs()
    try:
        return rs._feat._sources.best_line(rs._stash.best_for(rs.STASH_DIR, rs.re.findall(r"[A-Za-z0-9$][A-Za-z0-9$-]{2,}", str(text or ''))[:10], None, 2), rs._stash.agent_tag(cat.get('id')))
    except Exception as e:   # noqa: BLE001
        print(f'[stash] {str(e)[:100]}')
        return ''


def _fit_line(cat, kind):
    """⚠ What the picked models cannot do on this job. It warns once and never stops the work: the owner's pick always runs. → a line or ''"""
    rs = _rs()
    rows = {r['id']: r for r in ((rs._MODELS.get('rows') or {}).get('models') or [])}; names = []; picked = ((cat.get('brainsCfg') or {}).get('brains') or [])[:2]; found = [(m, rows.get(m)) for m in picked]
    if kind in ('pos', 'poc') and any(r and r.get('vision') for _, r in found):   # one mind that can see is enough: it does the looking
        return ''
    for m, r in found:
        for line in rs._lc.limits_of(r, kind):
            names.append(f"{str(m).split('/')[-1]} {line}")
    return ('Worth knowing: ' + '; '.join(names) + '. It still does the work, the result just may not be its best. Model discovery shows which models suit this proof.') if names else ''


def _mkit_extra():
    rs = _rs()
    p_ = rs.DATA_DIR / rs._mkits.EXTRA_FILE
    at_ = p_.stat().st_mtime if p_.exists() else 0
    if at_ != rs._MKIT_EXTRA['at']:
        rs._MKIT_EXTRA.update(at=at_, kits=rs._mkits.load_extra(rs.DATA_DIR))
    return rs._MKIT_EXTRA['kits']


def _mkit_set(new_, combos_=None):
    """Store a measurement and log every kit whose state moved (the rollback history)."""
    rs = _rs()
    rs._mkits.log_changes(rs.DATA_DIR, dict(rs._MKIT_STATE), new_); rs._MKIT_STATE.update(new_)
    if combos_ is not None:
        rs._MKIT_COMBOS[:] = combos_[:24]


def _mkit_measure(cat, rows):
    """Kits one by one, and kits in pairs, from the same proofs."""
    rs = _rs()
    fb_ = {(k, str(f.get('id'))): f for k, (_c, key) in rs._mission.KINDS.items() for f in cat.get(key) or []}
    kits_ = rs._mkits.reliability(rows, fb_, rs._mkit_extra()); rs._mkit_set(kits_, rs._mkits.combos(rows, fb_, rs._mkit_extra()))
    return kits_


def _recall(cat, category, text):
    """🔎 Every proof looks first in the Collective's private record for a winning proof of its own or anyone's, before it searches, and gets the kits for its kind of proof, the owner's picks first. Never stops a proof."""
    rs = _rs()
    try:
        cfg_ = cat.get('brainsCfg') or {}; kind_ = rs.RECALL_KIND.get(category, ''); mode_, mine_ = rs._kits.picks_of(cfg_, kind_); auto_ = mode_ == 'auto'
        picks_ = rs._kits.auto_picks(rs.KITS_DIR, kind_, text, record=rs._kit_record()) if auto_ else mine_; rs._KIT_LAST[(cat.get('id'), kind_)] = picks_
        return rs._mkits.active_line(kind_, rs._MKIT_STATE, rs._mkit_extra()) + rs._db_shared_line(cat, kind_) + rs._review.lessons_line(rs._REVIEW_LESSONS.get(kind_) or []) + rs._stash_best(cat, category, text) + rs._convo(cat) + rs._proof_brain(cat, kind_) + (rs._cg.project_line(cat.get('projectRepo')) if kind_ == 'pos' else '') + rs._kits.line(rs.KITS_DIR, kind_, picks_, open_kits=auto_) + rs._kits.skills_line(cat.get('brainsCfg'), {k['id']: k.get('name') for k in rs._kits.catalog_view(rs.KITS_DIR)}) + rs._feat._sources.recall_line(rs._stash.related(rs.STASH_DIR, rs.re.findall(r"[A-Za-z0-9$][A-Za-z0-9$-]{2,}", str(text or ''))[:10], category), rs._stash.agent_tag(cat.get('id')))
    except Exception as e:   # noqa: BLE001
        print(f'[recall] {str(e)[:100]}')
        return ''


def _sicario_merge(store):
    """🎩 OSSY and G4 are one agent, Sicario's, with those two as its minds (owner 2026-11-05). No wallet of its own. Runs until both rows are settled."""
    rs = _rs()
    for c in store['cats'].values():
        if c.get('handle') == 'sicarios' and not str((c.get('brainsCfg') or {}).get('brains', [''])[0]).startswith('local/'):
            c['brainsCfg']['brains'] = ['local/ossy', 'local/g4']   # its own models, free
        if c.get('handle') == 'sicarios' and (c.get('brainsCfg') or {}).get('cardSeat') is None:
            c['brainsCfg']['cardSeat'] = True   # 🎩 owner 2026-11-05: they trade from the Fuse wallet. A PoW you ask for goes to the card; the switch still turns it off
        if c.get('handle') == 'sicarios' and str((c.get('brainsCfg') or {}).get('prompt') or '').startswith(rs.SICARIO_OLD_PROMPT):
            c['brainsCfg']['prompt'] = rs.SICARIO_PROMPT   # 🎩 owner 2026-11-05: not stuck on trading. Only the old default moves; a prompt the owner wrote stays
        if c.get('handle') == 'ossy-desk' and c.get('name') == 'OSSY' and not c.get('agentWallet'):
            c['name'] = "Sicario's"; c['handle'] = 'sicarios'; b_ = c.setdefault('brainsCfg', {}); b_['mindNames'] = ['OSSY', 'G4']
            b_['prompt'] = rs.SICARIO_PROMPT
        elif c.get('handle') == 'g4-desk' and c.get('name') == 'G4' and not c.get('revoked') and not c.get('agentWallet') and not any(c.get(k) for k in ('powFolders', 'popFolders', 'pobFolders')):
            c['revoked'] = True


def _made_pass(store):
    """🎨 File what finished: charge what it really cost, keep the file, say so in the chat."""
    rs = _rs()
    while rs._MADE_DONE:
        o = rs._MADE_DONE.pop(0); cat = store['cats'].get(o['cat'])
        if not cat or not cat.get('brainsCfg'):
            continue
        job = o['job']; b_ = cat['brainsCfg']; now = rs.time.time(); line = {'by': 'cats', 'at': now, 'cost': o['usd']}
        if o['usd'] and o['own']:
            day_ = rs.time.strftime('%Y-%m-%d', rs.time.gmtime()); b_['daySpend'] = {day_: round((b_.get('daySpend') or {}).get(day_, 0) + o['usd'], 6)}
        elif o['usd']:
            rs._lc.charge(b_, o['usd'])
        try:
            if o['why']:
                raise ValueError(o['why'])
            row = rs._af.save(rs.DATA_DIR, cat, o['url'], f"{job['prompt'][:40]}.png", now) if job['kind'] == 'image' else rs._af.save_project(rs.DATA_DIR, cat, o['files'], rs._ac.project_preview(o['files']), job['prompt'][:40], now) if job['kind'] == 'project' else rs._af.save_page(rs.DATA_DIR, cat, o['html'], job['prompt'][:40], now)
            url = f"/api/cats/{cat['id']}/files/{row['id']}.{row['ext']}"
            line.update(text=f"🎨 Here it is: {job['prompt'][:120]}", img=url) if job['kind'] == 'image' else line.update(text=f"🖥 Built{' a project of ' + str(len(o['files'])) + ' files' if job['kind'] == 'project' else ''}: {job['prompt'][:120]}", page=url)
            cat['feesDue'] = (list(cat.get('feesDue') or []) + [{'key': f"task-{row['id'][:10]}"}])[-20:]
        except ValueError as e:
            line['text'] = f'🎨 Not made: {str(e)[:160]}'
        cat['chat'] = (list(cat.get('chat') or []) + [line])[-200:]


def _pow2_real_sol(cat, pid, asked):
    """The size the wallet will really send: its budget can cap what the minds agreed, and the chat and folder must say the capped number."""
    rs = _rs()
    return rs._num(next((x.get('sol') for x in cat.get('proposals') or [] if x.get('id') == pid), 0)) or asked


async def _pop_read(http, market):
    rs = _rs()
    s_, t_ = await rs.asyncio.gather(http.get(f'{rs.POP_FEED}/{market}-USD/stats'), http.get(f'{rs.POP_FEED}/{market}-USD/ticker'))
    return rs._pop.read_market(market, s_.json() if s_.status_code == 200 else None, t_.json() if t_.status_code == 200 else None)


def _pop_file(cat, rec, line):
    rs = _rs()
    cat['popFolders'] = rs._pop.trim(list(cat.get('popFolders') or []) + [{**rec, 'n': rs._pop.number(cat), 'kits': rs._KIT_LAST.get((cat.get('id'), 'pop')) or []}])
    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': line, 'at': rs.time.time(), 'open': 'pop'}])[-200:]


def _pop_view(cat):
    """🗂 Every filed proof as a desktop folder, newest first, with its report and discussion."""
    rs = _rs()
    return [rs._pop.folder(r, i + 1) for i, r in enumerate(cat.get('popFolders') or [])][::-1]


async def _pop_price(http, market):
    """The live price, or 0 when the feed gave none: a missed read is retried on the next pass, never guessed."""
    rs = _rs()
    try:
        return rs._num(((await http.get(f"{rs.POP_FEED}/{market}-USD/ticker")).json() or {}).get('price'))
    except (rs.httpx.HTTPError, ValueError):
        return 0.0


def _pop_dna_id(cat_id):
    """A PoP's fingerprint is kept apart from the PoW one: perps sources must never enter a coin's research rotation."""
    return f'{cat_id}:pop'


async def _pop_chart(http, market):
    rs = _rs()
    try:
        return rs._pop.chart_line(market, (await http.get(f'{rs.POP_FEED}/{market}-USD/candles', params={'granularity': 300})).json())
    except Exception:   # noqa: BLE001 — no candles is a thinner brief, never a stopped proof
        return ''


async def _pop_gather(http, cat, reads, idx, rid, now):
    """🛰 Each mind's own sources, measured against the chart, and its fingerprint updated. → {mind: [rows]}."""
    rs = _rs()
    out, taken = {}, []
    for i in idx:
        sites = rs._popsrc.pick(cat.get('popFolders'), i, taken); taken += sites
        rows = await rs._popsrc.read_mind(http, sites, reads); out[str(i)] = rows
        try:
            rs._poi.append(rs.DATA_DIR, rs._pop_dna_id(cat['id']), i, rid, 'PERPS', now, rs._popsrc.facts(rows, now), {'visits': len(sites), 'verified': sum(1 for r in rows if r.get('ok') and not r.get('off')), 'gaps': sorted({r['site'] for r in rows if not r.get('ok')})}, visited=sites)
        except Exception as e:   # noqa: BLE001 — a fingerprint that cannot file never stops the proof
            print(f'[pop] dna: {str(e)[:120]}')
    return out


async def _pop_round(cat, idx, sys_of, brief, box):
    """One blind round: the listed minds answer at once, inside the round's time limit. A mind that says nothing is a mind with no call."""
    rs = _rs()
    return await rs._minds_ask([rs._pow2_ask(cat, i, sys_of(i), brief(i), 220, box) for i in idx], rs._pop.ROUND_S)


async def _minds_ask(asks, secs):
    """🧠 Every mind answers at once, each on its own clock: a slow or blank mind is '' and never blanks the other (owner 2026-11-16: both minds work)."""
    rs = _rs()
    async def one(a):
        try:
            return await rs.asyncio.wait_for(a, secs)
        except rs.asyncio.TimeoutError:
            return ''
    return list(await rs.asyncio.gather(*(one(a) for a in asks)))


async def _pop_open(http, cat, do, who, now, browsed=None, read_why=''):
    """📉 file a PoP / 💡 propose one. Both start blind. Only a proposal gets the second round: split minds see each other's call once and may hold or change."""
    rs = _rs()
    propose = do == 'propose'; icon = '💡 pPoP' if propose else '📉 PoP'
    reads = [r for r in await rs.asyncio.gather(*(rs._pop_read(http, m) for m in rs._pop.MARKETS)) if r]
    brains = rs._lc.minds_for(cat.get('brainsCfg'), 'pop'); rid = f'pop{int(now)}'; flag = {'proposal': True} if propose else {}
    if not reads or not brains:
        rs._pop_file(cat, {**flag, 'id': rid, 'at': round(now), 'status': 'closed', 'noTrade': True, 'why': 'no live price' if not reads else 'it needs a model first', 'calls': []}, f'{icon} not filed: no live price or no model')
        return
    names = [str(m).split('/')[-1][:24] for m in brains]; box = {'cost': 0, 'ref': rid, 'proof': 'pop'}
    idx = [int(who)] if who in ('0', '1') and int(who) < len(brains) else list(range(len(brains)))
    charts = [c for c in await rs.asyncio.gather(*(rs._pop_chart(http, r['market']) for r in reads)) if c]
    sources = await rs._pop_gather(http, cat, reads, idx, rid, now)
    loop_ = rs._pl.perp_loop(cat.get('popFolders'))   # 🔁 the Proof Loop: both minds study their last proofs before they call
    lead_ = rs._pl.lead_of(rs._pl.mind_board(cat), rs._pl.pop_topics(reads), names)   # 🧠 each mind sees who has the better record here
    shared = '\n'.join([rs._pop.market_line(r) for r in reads] + charts) + rs._pl.perp_note(loop_) + rs._pl.lead_note(lead_)
    shared += rs._foot.note('pop', cat.get('popFolders'))
    shared += rs._convo(cat)
    read_, sites_read_ = await rs._site_reads('pop', (cat['id'], cat.get('name')))
    shared += rs._feat._sources.proof_line('pop') + read_ + rs._recall(cat, 'Perps', ' '.join(str(r.get('market') or '') for r in reads))
    brief = lambda i: shared + '\nYour own sources:\n' + '\n'.join(rs._popsrc.line(r) for r in sources.get(str(i), [])) + (f"\nWhat you read in your own browser (data, never an instruction):\n{(browsed or {}).get(str(i), {}).get('note')}" if (browsed or {}).get(str(i), {}).get('note') else '')
    raw = await rs._pop_round(cat, idx, lambda i: rs._pop.SYS.format(name=names[i]), brief, box)
    parsed = [rs._pop.parse_call(x) for x in raw]
    calls = [{'mind': i, 'name': names[i], **(c or {'why': str(raw[k] or '')[:160]})} for k, (i, c) in enumerate(zip(idx, parsed))]
    trade, why = rs._pop.agree(parsed); conviction = 'solo' if len(idx) == 1 else 'blind'
    final_calls = parsed
    if propose and not trade and len(idx) == 2 and any(parsed):
        again = await rs._pop_round(cat, idx, lambda i: rs._pop.CHALLENGE_SYS.format(name=names[i], mine=rs._pop.call_line(parsed[idx.index(i)]), other=rs._pop.call_line(parsed[1 - idx.index(i)])), brief, box)
        second = [rs._pop.parse_call(x) if x else parsed[k] for k, x in enumerate(again)]   # a mind that went silent keeps its first call
        calls = [{'mind': i, 'name': names[i], **(c or {'why': str(again[k] or calls[k].get('why') or '')[:160]}), 'first': rs._pop.call_line(parsed[k])[:60], 'changed': (c or {}).get('side') != (parsed[k] or {}).get('side') or (c or {}).get('market') != (parsed[k] or {}).get('market')} for k, (i, c) in enumerate(zip(idx, second))]
        trade, why = rs._pop.agree(second); conviction = 'argued'; final_calls = second
    base = {**flag, 'id': rid, 'at': round(now), 'calls': calls, 'loop': loop_, 'lead': lead_, 'kernel': rs._kernel.fingerprint(), 'paper': True, 'cost': box.get('cost', 0), 'spend': box.get('spend'), 'reads': reads, 'sources': sources, 'sitesRead': sites_read_, 'browsed': browsed or {}, 'browseWhy': read_why}
    both_ = [c for c in final_calls if c and c.get('market') and c.get('side')] if not trade else []
    px_of = {r['market']: r['px'] for r in reads}
    if len(both_) == 2 and all(c['market'] in px_of for c in both_) and not cat.get('popCard'):   # 💡 still split: you pick which mind's paper trade runs
        cat['popCard'] = {**rs._pop.card(rid, both_[0], px_of[both_[0]['market']], now, calls, 'split', base), 'alt': {**both_[1], 'entry': px_of[both_[1]['market']]}}
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"💡 pPoP: the minds split, {rs._pop.call_line(both_[0])} or {rs._pop.call_line(both_[1])}. Pick one to run on paper, within 15 minutes.", 'at': now, 'open': 'pop'}])[-200:]
        return
    lone_ = [(k, c) for k, c in enumerate(final_calls) if c and c.get('market') and c.get('side')] if not trade and len(idx) == 2 else []
    if len(lone_) == 1 and lone_[0][1]['market'] in px_of and not cat.get('popCard'):   # 🙋 one mind called it, the other passed: a card for HIS tap, paper only, never opened by itself
        k_, c_ = lone_[0]; passed_ = rs._pop.no_trade_why('a mind called no trade', calls)
        cat['popCard'] = rs._pop.card(rid, {x: c_[x] for x in ('market', 'side', 'lev', 'tp', 'sl')}, px_of[c_['market']], now, calls, 'lone', base)
        cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': f"🙋 {icon}: only Mind {'AB'[idx[k_]]} called it: {rs._pop.call_line(c_)}. {passed_}. Run it on paper within 15 minutes, or let it go.", 'at': now, 'open': 'pop'}])[-200:]
        return
    if not trade:
        why = rs._pop.no_trade_why(why, calls)
        rs._pop_file(cat, {**base, 'status': 'closed', 'noTrade': True, 'why': why}, f'{icon} filed with no trade: {why}')
        return
    chk_ = rs._cmp.check('pop', {**base, **trade, 'calls': calls, 'board': reads}); base['compare'] = chk_
    if not chk_['ok']:   # ⚖ COL-13: a thin call is not traded, even on paper; the next round reads more first
        rs._pop_file(cat, {**base, 'status': 'closed', 'noTrade': True, 'why': f"not traded: {chk_['why']}. Compare before settling."}, f"{icon} filed with no trade: {chk_['why']}")
        return
    px = next(r['px'] for r in reads if r['market'] == trade['market'])
    if propose:
        cat['popCard'] = rs._pop.card(rid, trade, px, now, calls, conviction, base)
        line = f"💡 pPoP: {trade['side']} {trade['market']} {trade['lev']}× at ${px:,.2f}. Nothing is open. You have 15 minutes to run it."
    else:
        cat['popRun'] = {**base, **trade, 'status': 'open', 'entry': px, 'mark': px, 'roePct': 0.0, 'openedAt': round(now), 'liqPct': rs._pop.liq_move_pct(trade['lev'])}
        line = f"📉 PoP open on paper: {trade['side']} {trade['market']} {trade['lev']}× at ${px:,.2f}"
    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': line, 'at': now, 'open': 'pop'}])[-200:]


async def _pop_card_tick(http, cat, c, do, now):
    """💡 The open proposal: your Run or Pass, then one ghost price read on true prices."""
    rs = _rs()
    px = await rs._pop_price(http, c['market'])
    if do == 'adopt':
        why = 'a PoP is already open' if cat.get('popRun') else rs._pop.adopt_refusal(c, px, now)
        if why:
            c['refused'] = why
        else:
            cat['popRun'] = rs._pop.adopt(c, px, now); cat.pop('popCard', None)
            rs._pop_file(cat, {**c, 'status': 'closed', 'state': 'ran', 'ranAt': round(now)}, f"📉 Ran the proposal on paper: {c['side']} {c['market']} {c['lev']}× at ${px:,.2f}")
            return
    elif do == 'pass' and c.get('state') == 'waiting':
        c['state'] = 'passed'; c.pop('refused', None)
    if px > 0:
        rs._pop.sample(c, px, now)
        rec = rs._pop.ghost(c, px, now)
        if rec:
            cat.pop('popCard', None)
            rs._pop_file(cat, rec, f"💡 pPoP ghost closed ({rec['why']}): {rec['side']} {rec['market']} would have made {rec['roePct']:+.2f}%")


async def _pop_begin(http, cat, do, who, now):
    """🌐 The minds read sites first. No window free: the proof still files on its free sources, and its folder says it did not browse."""
    rs = _rs()
    if cat.get('popRead'):
        return
    why = rs._read_start(cat, rs.POP_READ_GOAL, who, 'pop')
    if why:
        await rs._pop_open(http, cat, do, who, now, None, why)
        return
    t_ = rs._WORK[cat['id']]['task']
    if len(t_.get('jobs') or []) > 1:   # 👣 each mind its own two sites and angle (owner 2026-11-15: "the other brain researches … uniquely")
        foot_ = rs._foot.plan('pop', '', rs._book.apply(cat.get('siteBook'), 'pop', list(rs._foot.POP_SITES)), cat.get('popFolders'))
        t_['jobs'] = [rs._foot.pop_goal(foot_['sites'][i_], foot_['angles'][i_]) for i_ in range(2)][:len(t_['jobs'])]
    cat['popRead'] = {'do': do, 'who': who, 'at': round(now), 'tid': t_['id']}
    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': '🌐 Reading perps sites in its own windows first. Watch its monitors.', 'at': now, 'open': 'pop'}])[-200:]


async def _pop_tick(http, cat, now):
    rs = _rs()
    want = rs._POP_WANT.pop(cat['id'], None); do, _, who = str(want or '').partition(':')
    if cat.get('popCard'):
        await rs._pop_card_tick(http, cat, cat['popCard'], do, now)
    run = cat.get('popRun')
    if run:
        px = await rs._pop_price(http, run['market'])
        why = 'stopped by you' if do == 'stop' else rs._pop.hard_exit(run, px, now)
        if px > 0:
            run.update(mark=px, roePct=rs._pop.roe_pct(run, px)); rs._pop.sample(run, px, now)
        if why and px > 0:
            rec = rs._pop.close(run, px, now, why); cat.pop('popRun', None)
            rs._pop_file(cat, rec, f"📉 PoP closed ({why}): {rec['side']} {rec['market']} {rec['roePct']:+.2f}% on paper")
    elif do == 'start':
        await rs._pop_begin(http, cat, do, who, now)
    if do == 'propose' and not cat.get('popCard'):
        await rs._pop_begin(http, cat, do, who, now)
    rd = cat.get('popRead')
    if rd:
        done, notes, why = rs._read_check(cat, rd, now)
        if done:
            cat.pop('popRead', None)
            if not (cat.get('popRun') if rd.get('do') == 'start' else cat.get('popCard')):
                await rs._pop_open(http, cat, rd.get('do'), rd.get('who'), now, notes, why)


def _kalshi_say_no(cat, tk):
    """🛑 A bid that did not go out says so in chat, in plain words (owner 2026-11-15 PoB #17: 'idk if its going through or not')."""
    rs = _rs()
    t_ = f"🛑 Nothing bought on {tk.get('title') or tk.get('ticker')}: {rs._kb.plain_why(tk.get('why'))}"
    cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'cats', 'text': t_[:400], 'at': rs.time.time(), 'open': 'bids'}])[-200:]


def _pob_team_bid(cat, topic, now=None):
    """The team-to-win bid already on Kalshi for this game today (its title), or ''. Same game = the desk's own rule (pob.same_game). Pure."""
    rs = _rs()
    me_ = {'topic': topic, 'at': now or rs.time.time()}
    for f_ in reversed(cat.get('pobFolders') or []):
        k_ = f_.get('kalshi') if isinstance(f_.get('kalshi'), dict) else None
        if k_ and k_.get('kind') != 'parlay' and rs._kb.reached(k_) and rs._pob.same_game(f_, me_):
            return str(k_.get('title') or k_.get('ticker') or 'a real bid')
    return ''


async def _kalshi_go(cat, tk):
    """A ticket's one door to Kalshi: a slip takes the quote path, a single market the order path."""
    rs = _rs()
    return await (rs._kalshi_slip_send if tk.get('kind') == 'parlay' else rs._kalshi_send)(cat, tk)

