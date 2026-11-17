"""🧹 Fuse seasons — moved whole out of reputation_service.py by scripts/move-section.py (owner 2026-11-16 cleanup).
Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches reputation_service still
reaches it, and every function here is still reachable on reputation_service under its own name. Constants, classes and state live in the service."""


def _rs():
    import reputation_service
    return reputation_service


async def _season_rows(since, until):
    rs = _rs()
    pos = [x for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or [] if since <= rs._fuse._f(x.get('at')) < until]
    if not pos:
        return [], set()
    px = await rs._hq_prices([leg for x in pos for leg in x['legs'] if leg.get('soldUsd') is None])
    rows = []
    for x in pos:
        rr = rs._hq.position_pnl(x, px)
        rows.append({**rr, 'wallet': x['wallet'], 'streak': rs._hq.swap_streak({**rr, 'events': x.get('events')})})
    wallets = list({x['wallet'] for x in pos})
    verdicts = await rs.asyncio.gather(*[rs._shield_of(w) for w in wallets], return_exceptions=True)
    bots = {w for w, v in zip(wallets, verdicts) if isinstance(v, dict) and v.get('verdict') == 'bot'}
    return rows, bots


def _season_wins():
    """{card id: {'week', 'rank'}} for every crowned card (drives the 🏆 badge + the season Fee-Back boost)."""
    rs = _rs()
    return {t_['id']: {'week': s['week'], 'rank': t_['rank']} for s in rs._json_load(rs.FUSE_HQ_PATH, {}).get('seasons') or [] for t_ in s.get('top') or []}


async def _fuse_season_tick(now):
    """Once per week: crown last week's top 3 cards (stored forever, winners notified, Fee-Back boost on those cards)."""
    rs = _rs()
    start = rs._hq.season_start(now); prev = start - rs._hq.WEEK
    if rs._fuse._f(rs._json_load(rs.FUSE_HQ_PATH, {}).get('seasonAwarded')) >= prev:
        return None
    rows, bots = await rs._season_rows(prev, start)
    top = rs._hq.season_board(rows, prev, start, bots)[:3]
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        if rs._fuse._f(d.get('seasonAwarded')) >= prev:
            return None
        d['seasonAwarded'] = prev
        if top:
            d.setdefault('seasons', []).append({'week': prev, 'n': len(rows), 'top': [{**t_, 'handle': rs.handle_of(t_['wallet'])} for t_ in top]})
        rs._json_save(rs.FUSE_HQ_PATH, d)
    # ⚔ backer season: last week's top 3 backers split the HQ prize pool (owed in the Fee-Back book → weekly payout)
    dd = rs._json_load(rs.FUSE_HQ_PATH, {})
    prizes = rs._hq.backer_prizes(rs._hq.backer_board(dd.get('backLog'), dd.get('backWins'), prev, start, set(rs._protected_wallets()) | bots), rs._card_rules().get('backerPoolUsd', 0))
    if prizes:
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {})
            d['backerPrizes'] = (d.get('backerPrizes') or []) + [{**pz, 'week': prev} for pz in prizes]
            rs._json_save(rs.FUSE_HQ_PATH, d)
        for pz in prizes:
            rs.notify(pz['wallet'], 'fuse-card', f"⚔ Top backer #{pz['rank']} last week — ${pz['usd']:.2f} prize, paid with the weekly Fee-Back.", url='/terminal/fuse?tab=arena',
                   once=f"backer-{prev}-{pz['wallet']}", meta={'claim': 'Most winning battle backs that week', 'source': 'Arena battles'})
    # 🐱 FeeCat challenge: every card opened last week that beat her average trade that week
    cat = await rs._feecat_raw()
    cat_pct = rs._hq.feecat_week_pct((cat or {}).get('exits'), (cat or {}).get('positions'), prev, start) if cat else None
    beat = rs._hq.beats_cat(rs._hq.season_board(rows, prev, start, bots), cat_pct)
    async with rs._admin_lock:
        d = rs._json_load(rs.FUSE_HQ_PATH, {})
        d.setdefault('catChallenge', []).append({'week': prev, 'catPct': cat_pct, 'ids': beat})
        d['catChallenge'] = d['catChallenge'][-52:]
        rs._json_save(rs.FUSE_HQ_PATH, d)
    owners = {x['id']: x for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or []}
    for cid in beat:
        if cid in owners:
            rs.notify(owners[cid]['wallet'], 'fuse-guard', f"🐱 Your card {owners[cid].get('name') or ''} beat FeeCat last week ({cat_pct:+.1f}% her average trade). +{rs._hq.CAT_WIN_PTS} Fuse score.",
                   url='/terminal/fuse?tab=arena', once=f"beatcat-{prev}-{cid}", meta={'claim': 'Card P&L above FeeCat\'s weekly average trade', 'source': 'Fuse season + FeeCat sim book'})
    # 🐱 FeeCat's weekly note: every wallet with a card opened last week, once per week
    dial = rs._json_load(rs.RUNNERS_PATH, {}).get('cfgDial')
    tuned = sum(1 for a in rs._admin_load().get('audit') or [] if a.get('action') == 'runners-config' and prev <= rs._fuse._f(a.get('at')) < start)
    beat_wallets = {owners[c]['wallet'] for c in beat if c in owners}
    for w in {r['wallet'] for r in rows if r.get('wallet')}:
        rs.notify(w, 'fuse-card', rs._hq.feecat_weekly(dial, tuned, w in beat_wallets, cat_pct), url='/terminal/fuse?tab=arena', once=f"feecat-week-{prev}",
               meta={'claim': "FeeCat's sim book + engine changes that week", 'source': 'Fuse season + HQ audit log'})
    plan = rs._hq.payout_plan((await rs._feeback_book())['rows'], await rs._sol_usd_live(), exclude=rs._protected_wallets())
    if plan['totalUsd'] >= 1:
        for adm in rs._admin_wallets():
            rs.notify(adm, 'shield', f"💸 Weekly Fuse payout ready: ${plan['totalUsd']:,.2f} to {len(plan['rows'])} wallets (Fee-Back + copy cuts). HQ › Fuse › Card rules › Pay.",
                   url='/terminal/command?tab=fuse', once=f"fuse-payout-{prev}", meta={'claim': 'Owed from the fee ledger', 'source': 'Fuse Fee-Back book'})
    medal = {1: '🥇', 2: '🥈', 3: '🥉'}
    if top:
        rs._fuse_chat('fuse-lab', '🏆 Fuse season crowned: ' + ' · '.join(f"{medal[t_['rank']]} {rs.handle_of(t_['wallet']) or t_['wallet'][:4] + '…'} {t_.get('name') or ''} {t_['pnlPct']:+.1f}%" for t_ in top), f"season-{prev}")
    for t_ in top:
        rs.notify(t_['wallet'], 'fuse-guard', f"🏆 {medal[t_['rank']]} Your card {t_.get('name') or ''} finished #{t_['rank']} in this week's Fuse season ({t_['pnlPct']:+.1f}%). "
               f"+{rs._card_rules()['seasonBoostPct']:g}% Fee-Back on it.", url='/terminal/fuse?tab=arena', once=f"season-{prev}-{t_['id']}",
               meta={'claim': f"#{t_['rank']} of {len(rows)} cards opened that week, by real P&L", 'source': 'Fuse season (verified FEELESS trades)'})
    rs._fuse_season_cache.update(at=0.0, data=None)
    return top


def _season_race(week, board, now):
    """Rank changes since the last background build → the Arena race ticker; a card entering or leaving the top 3 alerts
    its owner once (per card, week and direction)."""
    rs = _rs()
    if rs._season_moves['week'] != week:
        rs._season_moves.update(week=week, prev={}, list=[])
    prev = rs._season_moves['prev']
    moves = rs._hq.rank_moves(prev, board) if prev else []
    rs._season_moves['list'] = (rs._season_moves['list'] + [{**m, 'at': now} for m in moves])[-30:]
    now_rank = {b['id']: b['rank'] for b in board}
    for b in board:
        was = prev.get(b['id']) if prev else None
        if prev and b['rank'] <= 3 and (was is None or was > 3):
            rs.notify(b['wallet'], 'fuse-guard', f"🏆 Your card {b.get('name') or ''} just entered the Fuse season top 3 (#{b['rank']}, {b['pnlPct']:+.1f}%). Hold it to Monday 00:00 UTC.",
                   url='/terminal/fuse?tab=arena', once=f"top3-in-{week}-{b['id']}", meta={'claim': f"#{b['rank']} by real P&L this week", 'source': 'Fuse season'})
    if prev:
        for cid, was in prev.items():
            if was <= 3 and now_rank.get(cid, 99) > 3:
                own = next((b for b in board if b['id'] == cid), None)
                pos = own or next((x for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or [] if x['id'] == cid), None)
                if pos:
                    rs.notify(pos['wallet'], 'fuse-guard', f"⚠ Your card dropped out of the Fuse season top 3 (now #{now_rank.get(cid, '10+')}). There's still time before Monday 00:00 UTC.",
                           url='/terminal/fuse?tab=arena', once=f"top3-out-{week}-{cid}-{int(now // 3600)}", meta={'claim': 'Rank fell below #3', 'source': 'Fuse season'})
    rs._season_moves['prev'] = now_rank


async def _series_24h(pair):
    """Last 24h of 15m closes for one pool (candles service), [[t, close], …]. 60s cache."""
    rs = _rs()
    hit = rs._replay_cache.get(pair)
    if hit and rs.time.time() - hit[0] < 60:
        return hit[1]
    try:
        async with rs.httpx.AsyncClient(timeout=6) as http:
            cs = (await http.get(f'http://127.0.0.1:5099/api/candles/solana/{pair}', params={'interval': '15m'})).json().get('candles') or []
    except Exception:
        cs = []
    since = rs.time.time() - 86400
    out = [[int(c[0]), c[4]] for c in cs if c and c[0] >= since and c[4]]
    rs._replay_cache[pair] = (rs.time.time(), out)
    return out


async def _fuse_score(address, fresh=False):
    """⚛️ Fuse score for a wallet (2 min cache): real card P&L, medals, copies, streaks, holding + reputation."""
    rs = _rs()
    a = rs.primary_of(address)
    hit = rs._fuse_score_cache.get(a)
    if hit and not fresh and rs.time.time() - hit[0] < 120:
        return hit[1]
    mine = set(rs.linked_of(a)) | {a}
    allp = rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or []
    pos = [x for x in allp if x['wallet'] in mine]
    px = await rs._hq_prices([leg for x in pos for leg in x['legs'] if leg.get('soldUsd') is None]) if pos else {}
    now = rs.time.time()
    rows = []
    for x in pos:
        rr = rs._hq.position_pnl(x, px)
        rows.append({**rr, 'streak': rs._hq.swap_streak({**rr, 'events': x.get('events')}), 'compound': rs._hq.compound_streak({**rr, 'events': x.get('events')}),
                     'heldS': (x.get('closedAt') or now) - rs._fuse._f(x.get('at'))})
    ids = {x['id'] for x in pos}
    wins = [w for cid, w in rs._season_wins().items() if cid in ids]
    copies = sum(1 for c in allp if c.get('copyOwner') in mine)
    tr = (rs._trust_cache.get(a) or (0, {}))[1].get('score')
    sh = await rs._shield_of(a)
    cat_wins = sum(1 for w in rs._json_load(rs.FUSE_HQ_PATH, {}).get('catChallenge') or [] for cid in w.get('ids') or [] if cid in ids)
    rec = rs._json_load(rs.FUSE_HQ_PATH, {}).get('battleRecord') or {}
    bat = {k: sum(int((rec.get(f'user:{cid}') or {}).get(k) or 0) for cid in ids) for k in ('w', 'l', 'd')}
    medals = {str(r): sum(1 for w in wins if w.get('rank') == r) for r in (1, 2, 3)}
    held = [r for r in rows if not r.get('closed')]
    out = {'address': a, **rs._hq.fuse_score(rows, wins, copies, tr, bot=sh.get('verdict') == 'bot', cat_wins=cat_wins),
           # Trader page (profile top): the record behind the score, every number from FEELESS's own Fuse records
           'trader': {'medals': medals, 'battles': bat, 'catWins': cat_wins, 'copies': copies, 'held': len(held),
                      'heldPnlUsd': round(sum(r['pnlUsd'] for r in held), 2), 'bestPct': round(max((r['pnlPct'] for r in rows), default=0.0), 2),
                      'closed': sum(1 for r in rows if r.get('closed'))}}
    rs._fuse_score_cache[a] = (rs.time.time(), out)
    return out


def _bred_load():
    """🧬 Engine-made strategies → `fuse.BRED` (so `fuse.fitness` can score them). Cheap: the hot JSON cache."""
    rs = _rs()
    bred = rs._json_load(rs.FUSE_HQ_PATH, {}).get('bredStyles') or {}
    rs._fuse.BRED.clear(); rs._fuse.BRED.update({k: v.get('weights') or {} for k, v in bred.items()})
    return bred


async def _bred_tick(board, now):
    """🧬 Strategy generation + scrapping (hourly, with the autopilot): losers with a full record are scrapped to the log, a proven
    one is reported to the owner once, and a free seat gets ONE new strategy bred from the record. Returns the alive ones."""
    rs = _rs()
    d0 = rs._json_load(rs.FUSE_HQ_PATH, {})
    alive, scrapped, proven, want = rs._hq.bred_cycle(d0.get('bredStyles') or {}, board, now, d0.get('bredAt') or 0)
    new = None
    if want:
        table = {**rs._fuse.STYLES, **{k: v.get('weights') or {} for k, v in alive.items()}, **{r['style']: r.get('weights') or {} for r in d0.get('bredScrapped') or []}}
        kid = rs._fuse.breed_style(board, table, seed=int(d0.get('bredN') or 0) + 1)
        if kid:
            new = (f"gen-{int(d0.get('bredN') or 0) + 1}", {**kid, 'at': now})
    if scrapped or new or set(alive) != set(d0.get('bredStyles') or {}):
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {})
            cur = {k: v for k, v in (d.get('bredStyles') or {}).items() if k in alive}
            if new:
                cur[new[0]] = new[1]; d['bredN'] = int(d.get('bredN') or 0) + 1; d['bredAt'] = now
            d['bredStyles'] = cur
            d['bredScrapped'] = (list(d.get('bredScrapped') or []) + scrapped)[-20:]
            rs._json_save(rs.FUSE_HQ_PATH, d)
    for name in proven:
        for adm in rs._admin_wallets():
            rs.notify(adm, 'shield', f"🧬 Engine-made strategy {name} is winning in the arena (average and typical run both up). Open the verdict to decide.",
                   url='/terminal/command', once=f'bred-proven-{name}', push=False)
    return rs._bred_load()


async def _fuse_autopilot_tick(now=None):
    """Hourly: settle due arena runs, then enter each strategy's current champion ($5 paper, 3 pools) once per hour —
    the arena proves strategies on its own. Then alert HQ about wallets newly flagged as bots."""
    rs = _rs()
    now = now or rs.time.time()
    await rs._fuse_season_tick(now)
    await rs._arena_settle(now=now)
    arena = rs._json_load(rs.FUSE_HQ_PATH, {}).get('arena') or []
    board_now = rs._hq.arena_board([rs._hq.arena_value(e, {}, now) for e in arena])
    bred = await rs._bred_tick(board_now, now)                                             # 🧬 generate a new strategy / scrap a proven loser
    dead = rs._retired(board_now) - set(bred)   # ☠ losers: one probe a day, not hourly (a bred one keeps its hourly run until it is judged)
    styles = [st for st in [*rs._fuse.STYLES, *bred] if rs._hq.autopilot_due(arena, st, now, retired=dead)]
    if styles:
        metas, sol_usd = await rs.asyncio.gather(rs._fuse_candidates(), rs._sol_usd_live())
        if len(metas) >= 3:
            runs = await rs.asyncio.gather(*[rs.asyncio.to_thread(rs._fuse.evolve, metas, 3, 14, 28, st, 5 / sol_usd, sol_usd, int(now // 3600)) for st in styles])
            champs = [(st, rs._champ_view(ev['champions'][0], metas)) for st, ev in zip(styles, runs) if ev['champions']]
            prices = await rs._hq_prices([leg for _, c in champs for leg in c['legs']])
            async with rs._admin_lock:
                d = rs._json_load(rs.FUSE_HQ_PATH, {})
                for st, c in champs:
                    if rs._hq.autopilot_due(d.get('arena') or [], st, now, retired=dead):
                        d['arena'] = ((d.get('arena') or []) + [{**rs._hq.arena_entry(c, st, prices, now, rs.uuid.uuid4().hex[:10]), 'auto': True}])[-rs.ARENA_KEEP:]   # ⚡ ~100h of runs: the doc is rewritten every card tick
                rs._json_save(rs.FUSE_HQ_PATH, d)
    await rs._shield_alerts()


async def _shield_alerts():
    """Bot shield → HQ inbox: each wallet newly judged 'bot' is reported once to every admin wallet (cited)."""
    rs = _rs()
    rows = rs._shield_scan_all()
    d = rs._json_load(rs.SHIELD_PATH, {})
    told = set(d.get('alerted') or [])
    new = [r for r in rows if r['verdict'] == 'bot' and not r.get('manual') and r['address'] not in told]
    for r in new[:20]:
        claim = r['hits'][0]['evidence'][0] if r['hits'] else {'claim': r['why'], 'source': 'Bot shield'}
        for adm in rs._admin_wallets():
            rs.notify(adm, 'shield', f"🛡 Bot shield flagged {r['address'][:4]}…{r['address'][-4:]} ({r['score']}): {claim['claim']}",
                   url='/terminal/command', once=f"shield-{r['address']}", meta={'claim': claim['claim'], 'source': claim['source']}, push=False)
        told.add(r['address'])
    if new:
        d['alerted'] = sorted(told)[-5000:]
        rs._json_save(rs.SHIELD_PATH, d)
    return len(new)


async def _fuse_autopilot_loop():
    rs = _rs()
    await rs.asyncio.sleep(90)
    while True:
        try:
            await rs._fuse_autopilot_tick()
        except Exception as e:
            print('fuse autopilot:', e)
        await rs.asyncio.sleep(rs._hq.AUTOPILOT_EVERY)


def _card_look(body, prev):
    """A published card's look + configs (engine scenario cards): dial safe|balanced|degen, TP/SL/rotate/stop-mode chips."""
    rs = _rs()
    dial = body.get('dial', prev.get('dial', ''))
    cfg = body.get('cfg') if isinstance(body.get('cfg'), dict) else prev.get('cfg')
    out = {'dial': dial if dial in rs._rn.CARD_NAMES else ''}
    if cfg:
        out['cfg'] = {'tp': max(0, min(5000, int(rs._fuse._f(cfg.get('tp'))))), 'sl': max(0, min(95, int(rs._fuse._f(cfg.get('sl'))))), 'window': str(cfg.get('window') or '')[:6],
                      'rotateHours': max(0.08, min(48, rs._fuse._f(cfg.get('rotateHours')) or 24)), 'slMode': cfg.get('slMode') if cfg.get('slMode') in ('sell', 'park', 'hold') else 'sell'}
    if body.get('fromScenario') or prev.get('fromScenario'):
        out['fromScenario'] = str(body.get('fromScenario') or prev.get('fromScenario'))[:40]
    return out


def _fuse_chat(room, text, key, tokens=None):
    """Fuse moments into chat — battle results, bond runs, FeeCat's book, season crowns. Once per key (kept 2 days)."""
    rs = _rs()
    # 🧈 own small file (2026-10-15): 1,385 keys (97 KB) lived in fuse_hq.json — every post re-wrote the whole Fuse file, unlocked, beside the card tick
    posted = rs._json_load(rs.FUSE_CHAT_POSTED_PATH, None)
    if posted is None:
        posted = dict((rs._json_load(rs.FUSE_HQ_PATH, {}) or {}).get('chatPosted') or {})
    if key in posted:
        return None
    msg = rs.chat_system_post(room, rs.FUSE_ARENA_NAME, rs.FEE_ADDRESS, text[:600], tokens=tokens)
    now = rs.time.time()
    rs._json_save(rs.FUSE_CHAT_POSTED_PATH, {k: v for k, v in {**posted, key: now}.items() if now - v < 2 * 86400})
    return msg


def _fuse_chat_tick(now):
    """Background: 🔔 new bond runs → the coin's own room + fuse-lab; 🐱 FeeCat book changes → fuse-lab."""
    rs = _rs()
    live = rs._runner_live_cache.get('data') or {}
    for r in live.get('passing') or []:
        if r.get('bondTier') == 'run' and r.get('pairAddress'):
            txt = f"🔔 BOND RUN: ${r.get('symbol')} ticked every box at {rs._fuse._f(r.get('curve')):.0f}% up the curve — {r.get('buyShare')}% buys, curve +{rs._fuse._f(r.get('curveSpeed')):.0f} pts in 10m. Gated, not a promise."
            tok = [{'chainId': 'solana', 'pairAddress': r['pairAddress'], 'baseToken': {'address': r['mint'], 'symbol': r.get('symbol'), 'name': r.get('name') or r.get('symbol')},
                    'priceUsd': r.get('price'), 'marketCap': r.get('mcap'), 'volume': {'h1': r.get('vol1h')}, 'info': {'imageUrl': r.get('logo')},
                    'signals': {'score_label': f"🔔 Bond run · score {round(rs._fuse._f(r.get('score')))}", 'score_reasons': [f"{rs._fuse._f(r.get('curve')):.0f}% up the curve", f"{r.get('buyShare')}% buys", 'gated by Fuse runners']}}]
            rs._fuse_chat(f"coin-solana-{r['pairAddress']}-trenches", txt, f"bond-{r['mint']}-{int(now // 21600)}", tok)
            rs._fuse_chat('fuse-lab', txt, f"bond-lab-{r['mint']}-{int(now // 21600)}", tok)
    fc = next((c for c in rs._arena_mega_cache.get('data') or [] if c.get('kind') == 'feecat'), None)
    if fc:
        syms = sorted(l.get('symbol') or '?' for l in fc['legs'])
        rs._fuse_chat('fuse-lab', f"🐱 FeeCat's book now: {' · '.join('$' + s for s in syms)} ({(fc['index'] or 100) - 100:+.1f}% sim, {fc['record'].get('winRate')}% wins). Beat her this week for +8 Fuse score.",
                   f"feecat-book-{'-'.join(syms)}")


def _battle_view(mega, now):
    """⚔ Live battlefield: each pair with both cards' move since the bell (live from the stage), time left, recent results."""
    rs = _rs()
    b = rs._json_load(rs.FUSE_HQ_PATH, {}).get('battles') or {}
    pct = {f"{c['kind']}:{c['id']}": (c['index'] or 100) - 100 for c in mega}
    backs = list((b.get('backs') or {}).values()); paid = list((b.get('paid') or {}).values())
    paper = b.get('paper') or {}
    pnow = lambda k, start, bs=0.0: round(paper[k]['pct'] - bs, 2) if (paper.get(k) or {}).get('pct') is not None else round(pct.get(k, start) - start, 2)   # THIS bell's move on the season book
    pairs = [{side: {**x[side], 'now': pnow(x[side]['key'], x[side]['start'], rs._fuse._f(x[side].get('bookStart'))), 'paper': {kk: (paper.get(x[side]['key']) or {}).get(kk) for kk in ('startUsd', 'valueUsd', 'feesUsd', 'hiPct', 'loPct')} if paper.get(x[side]['key']) else None,
                     'frames': {str(m): rs._pgb.frame_pct(paper.get(x[side]['key']), now, m) for m in rs._pgb.FRAMES} if paper.get(x[side]['key']) else None,
                     'spark': [round(v - rs._fuse._f(x[side].get('bookStart')), 2) for v in rs._pgb.spark(paper.get(x[side]['key']), b.get('at'))],   # 📈 the race line: % since the bell, 1 point a minute
                     'backers': backs.count(x[side]['key']),
                     'paidN': sum(1 for q in paid if q['key'] == x[side]['key']), 'paidUsd': round(sum(q['usd'] for q in paid if q['key'] == x[side]['key']), 2)} for side in ('a', 'b')}
             for x in b.get('pairs') or []]
    for i, x in enumerate(b.get('pairs') or []):   # ⚡ the game's live scoreboard: six coin-vs-coin duels since the bell
        bell_a, bell_b = x['a'].get('bellPx'), x['b'].get('bellPx')
        pairs[i]['duels'] = rs._pgb.duels(paper.get(x['a']['key']), paper.get(x['b']['key']), bell_a, bell_b) if bell_a and bell_b else None
        for side in ('a', 'b'):
            pairs[i][side].pop('bellPx', None)
    br = rs._json_load(rs.FUSE_HQ_PATH, {}).get('bracket') or {}
    bc = br.get('cards') or {}
    cbs = rs._json_load(rs.FUSE_HQ_PATH, {}).get('comebacks') or {}
    board = []
    for c in rs._rn.unique_cards(mega):
        k = f"{c['kind']}:{c['id']}"; r = bc.get(k) or {'w': 0, 'l': 0}
        board.append({'key': k, 'comebacks': int(cbs.get(k) or 0), 'name': c.get('name') or 'Card', 'emoji': c.get('emoji'), 'dial': c.get('dial'), 'w': r.get('w', 0), 'l': r.get('l', 0),
                      'pct': round((c.get('index') or 100) - 100, 2), 'status': 'winners' if r.get('l', 0) == 0 else 'losers' if r.get('l', 0) == 1 else 'out'})
    board.sort(key=lambda x: ({'winners': 0, 'losers': 1, 'out': 2}[x['status']], -x['w'], -x['pct']))
    lg_ = rs._json_load(rs.FUSE_HQ_PATH, {}).get('league') or None
    league_view = None
    if lg_:   # 🏆 the league table IS the board: points, W-D-L, the season book's $ (started at $20)
        t_ = rs._lg.table(lg_); half = max(1, len(t_) // 2)
        board = [{'key': r['key'], 'name': r['name'], 'emoji': r.get('emoji'), 'w': r['w'], 'd': r['d'], 'l': r['l'], 'pts': r['pts'], 'rank': i + 1,
                  'usd': rs._fuse._f((paper.get(r['key']) or {}).get('valueUsd')) or rs._fuse._f((r.get('hist') or [rs._lg.START_USD])[-1]),
                  'pct': rs._fuse._f((paper.get(r['key']) or {}).get('pct')), 'comebacks': int(cbs.get(r['key']) or 0), 'src': r.get('src'),
                  'status': 'winners' if i < half else 'losers'} for i, r in enumerate(t_)]
        league_view = {'n': lg_['n'], 'round': lg_.get('round', 0), 'rounds': lg_.get('rounds', rs._lg.ROUNDS), 'startUsd': rs._lg.START_USD, 'fieldMax': rs._lg.FIELD_MAX,
                       'cycled': (lg_.get('cycled') or [])[-6:][::-1], 'cut': {'usd': rs._lg.CUT_USD, 'dropPct': rs._lg.CUT_DROP, 'bells': rs._lg.CUT_BELLS}}
    fighting = {p_[s_]['key'] for p_ in pairs for s_ in ('a', 'b')}
    calls = list((br.get('picks') or {}).values())
    for x in board:
        x['calls'] = calls.count(x['key'])
    up_next = [] if league_view else [x for x in board if x['status'] != 'out' and x['key'] not in fighting][:3]
    return {'pairs': pairs, 'league': league_view, 'endsAt': b.get('endsAt'), 'log': (rs._json_load(rs.FUSE_HQ_PATH, {}).get('battleLog') or [])[-8:][::-1],
            'bracket': {'board': board, 'season': br.get('season') or 1, 'champions': list(reversed(br.get('champions') or []))[:5], 'upNext': up_next, 'calls': len(calls)}, 'max': rs._rn.BATTLE_MAX}


def _league_card(d, key, mega):
    """The coins a fighter plays: its league seat (playground cards live only there), else its live Arena card."""
    r = next((x for x in ((d.get('league') or {}).get('field') or []) if x['key'] == key), None)
    return r or next((c for c in mega if f"{c['kind']}:{c['id']}" == key), None)


def _league_extra(mega):
    """League seats that aren't live Arena cards (cycled-in playground cards) as cards the Pit can draw in its corners."""
    rs = _rs()
    have = {f"{c['kind']}:{c['id']}" for c in mega}
    out = []
    for r in ((rs._json_load(rs.FUSE_HQ_PATH, {}).get('league') or {}).get('field') or []):
        if r['key'] not in have and ':' in r['key']:
            kind, cid = r['key'].split(':', 1)
            out.append({'kind': kind, 'id': cid, 'name': r['name'], 'emoji': r.get('emoji'), 'legs': r.get('legs') or [], 'fighterOnly': True, 'league': True,
                        'activity': {'tier': 'warm', 'score': 30}})
    return out


def _league_playground():
    """Fresh engine-playground cards for the league (cycled-in seats + filling a thin field): the HQ battle field, best record first."""
    rs = _rs()
    pg = (rs._json_load(rs.RUNNERS_PATH, {}).get('pgBattle') or {})
    rec = pg.get('record') or {}
    cards = sorted((pg.get('cards') or {}).items(), key=lambda kv: -((rec.get(kv[0]) or {}).get('w', 0) - (rec.get(kv[0]) or {}).get('l', 0)))
    out = []
    for k, c in cards:
        legs = [{'pairAddress': l.get('pairAddress'), 'symbol': l.get('symbol'), 'baseAddress': l.get('mint'), 'weight': rs._fuse._f(l.get('usd')) or 1.0,
                 'runner': (l.get('role') or 'runner') == 'runner'} for l in c.get('legs') or [] if l.get('pairAddress')]
        if len(legs) >= 2:
            name = str(c.get('name') or k)
            out.append({'key': f"pg:{k}", 'name': name.split(' ', 1)[-1] if ' ' in name else name, 'emoji': name.split(' ', 1)[0] if ' ' in name else '🧪', 'legs': legs, 'src': 'playground'})
    return out


async def _arena_auto_refresh(now):
    """Background: deal a fresh Arena build once per runner round (best gated coins + best live pools)."""
    rs = _rs()
    rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': []})
    last = (rd.get('rounds') or [None])[-1]
    if not last or ((rd.get('autoCard') or {}).get('at') or 0) >= last['at']:
        return None
    live, pools = await rs.asyncio.gather(rs._runner_live(), rs._fuse_candidates())
    rd_ = rs._json_load(rs.RUNNERS_PATH, {})
    cfg_ = rs._runner_cfg()
    if rd_.get('sitOut'):   # 🩺 nothing wins → the Arena Pick sits out runners (pools only) until a filter proves itself
        cfg_ = {**cfg_, 'autoCoins': 0}
    card = rs._rn.auto_card(rs._rn.apply_filter(live['passing'], rd_.get('pickFilter'), cfg_.get('autoCoins') or 0), list(pools.values()), now, cfg_)
    if card:
        async with rs._admin_lock:
            rd = rs._json_load(rs.RUNNERS_PATH, {'rounds': []}); rd['autoCard'] = card; rs._json_save(rs.RUNNERS_PATH, rd)
    return card


async def _feecat_raw():
    rs = _rs()
    try:
        async with rs.httpx.AsyncClient(timeout=2.5) as http:
            c = (await http.get('http://127.0.0.1:5088/api/cats/leader')).json()
        return c.get('cat') or c
    except Exception:
        return None


async def _feecat_card():
    """🐱 FeeCat on the Arena: her open simulated book as one card (legs = her positions, entry = her fill), with her
    record, so traders can see whether her edge beats theirs. Never real money — labelled sim everywhere."""
    rs = _rs()
    c = await rs._feecat_raw()
    if not c:
        return None
    ps = [p for p in c.get('positions') or [] if p.get('pairAddress')]
    if not ps:
        return None
    cost = sum(rs._fuse._f(p.get('costSol')) for p in ps) or 1.0
    pct = round(sum(rs._fuse._f(p.get('costSol')) * rs._fuse._f(p.get('currentChange')) for p in ps) / cost, 2)
    wr = rs._fuse._f(c.get('winRate'))
    act = rs._hq.activity(len(ps), 0, sum(rs._fuse._f(p.get('entryVolH1')) for p in ps) * 24, pct)
    return {'kind': 'feecat', 'id': 'feecat', 'name': f"{c.get('name') or 'FeeCat'}'s book", 'emoji': '🐱', 'aura': '', 'chat': 'fuse-card-feecat',
            'legs': [{'pairAddress': p['pairAddress'], 'symbol': p.get('symbol'), 'baseAddress': p.get('mint'), 'entry': rs._fuse._f(p.get('entryPriceUsd')),
                      'weight': round(rs._fuse._f(p.get('costSol')) / cost * 100, 2), 'at': p.get('openedAt')} for p in ps],
            'index': round(100 + pct, 2), 'grade': 'A' if wr >= 55 else 'B' if wr >= 45 else 'C', 'buyers': 0, 'activity': act,
            'record': {'winRate': round(wr), 'wins': c.get('wins'), 'losses': c.get('losses'), 'realizedSol': round(rs._fuse._f(c.get('realizedPnlSol')), 4),
                       'lives': (c.get('discipline') or {}).get('lives')}}


async def _arena_mega(rd, cfg, now):
    """Cards on the Arena stage: HQ mega cards (published Fuses flagged `arena`) + runner cards that lit after their
    rounds. Each carries its live activity (fuse_hq.activity → hard-coded effect tier). 30s cache, parallel lookups."""
    rs = _rs()
    if rs._arena_mega_cache.pop('boot', False) and rs._arena_mega_cache['data'] is None and not rs._FUSE_FORCE.get():
        # ⚡ first call after a restart: the stage written to disk (≤ 15 min old) is served at once and rebuilt in the background (it took ≈ 13s cold)
        snap_ = rs._launchpad_board.launchpad_board_snapshot(rs.ARENA_SNAPSHOT_PATH, 'mega', now)
        if snap_:
            rs._arena_mega_cache.update(at=now - max(40.0, snap_[0]), data=snap_[1])
    if rs._arena_mega_cache['data'] is not None and not rs._FUSE_FORCE.get():
        age_ = now - rs._arena_mega_cache['at']
        if age_ < 40:
            return rs._arena_mega_cache['data']
        if age_ < 600:   # ⚡ stale: answer with the last stage at once, ONE background rebuild (a viewer used to wait for every card's live view)
            if not rs._arena_mega_cache.get('busy'):
                rs._arena_mega_cache['busy'] = True

                async def _bg():
                    tok = rs._FUSE_FORCE.set(True)
                    try:
                        await rs._arena_mega(rd, cfg, rs.time.time())
                    except Exception:
                        pass
                    finally:
                        rs._FUSE_FORCE.reset(tok); rs._arena_mega_cache['busy'] = False
                rs.asyncio.create_task(_bg())
            return rs._arena_mega_cache['data']
    store = rs._json_load(rs.FUSES_PATH, {'fuses': {}})
    staged = sorted(((fid, f) for fid, f in (store.get('fuses') or {}).items() if f.get('arena') and f.get('enabled', True)), key=lambda x: -rs._fuse._f(x[1].get('createdAt')))[:8]   # newest first
    views = await rs.asyncio.gather(*[rs._fuse_view(fid, f, store) for fid, f in staged], return_exceptions=True)
    out = []
    for v in views:
        if isinstance(v, BaseException):
            continue
        day = [b for b in store.get('buys', []) if b['fuse'] == v['id'] and now - rs._fuse._f(b.get('at')) < 86400]
        act = rs._hq.activity(len(day), len({b['wallet'] for b in day}), v['volume24h'], (v['index'] or 100) - 100)
        base = (store['fuses'].get(v['id']) or {}).get('basePrices') or {}
        out.append({'kind': 'mega', 'id': v['id'], 'name': v['name'], 'emoji': v['emoji'], 'aura': v.get('aura') or '', 'chat': f"fuse-card-{str(v['id']).lower()}",
                    'dial': v.get('dial') or '', 'cfg': v.get('cfg') or None, 'tagline': v.get('tagline') or '',
                    'legs': [{**l, 'base': base.get(l['pairAddress'])} for l in v['legs']],
                    'index': v['index'], 'grade': (v['score'] or {}).get('grade'), 'buyers': v['trust']['buyers'], 'activity': act})
    live = {r['mint']: r for r in (await rs._runner_live())['passing']}
    for c in [c for c in reversed(rd.get('litCards') or []) if not c.get('downAt')][:6]:
        pct = rs._rn.card_result(c, rd['paths'], now, cfg)
        flow = sum(rs._fuse._f(live.get(p['mint'], {}).get('vol1h')) * 24 for p in c['picks'])
        out.append({'kind': 'lit', 'id': c['id'], 'name': ' · '.join(f"${p.get('symbol')}" for p in c['picks'][:4]), 'emoji': '🔥', 'aura': '',
                    'legs': [{'pairAddress': p.get('pairAddress') or p['mint'], 'symbol': p.get('symbol'), 'baseAddress': p['mint'], 'logo': p.get('logo'),
                              'weight': round(100 / max(1, len(c['picks'])), 2), 'entry': p.get('entry')} for p in c['picks']], 'chat': f"fuse-card-{c['id']}",
                    'index': round(100 + pct, 2), 'grade': 'A' if pct > 0 else 'C', 'buyers': 0, 'at': c['at'], 'proof': c.get('proof'),
                    'streak': rs._hq.swap_streak({'events': [{'kind': 'buy'}] * len(c.get('swaps') or []), 'pnlPct': pct}), 'swaps': (c.get('swaps') or [])[-3:],
                    'activity': rs._hq.activity(0, 0, flow, pct)})
    # Traders' cards: every open card shows until it's withdrawn; one that's up ≥ topTierPct takes the top tier.
    hq_all = rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or []
    hq = [x for x in hq_all if not x.get('closedAt')]
    hq = sorted(hq, key=lambda x: -rs._fuse._f(x.get('at')))[:24]
    if hq:
        upx = await rs._hq_prices([leg for x in hq for leg in x['legs']])
        top = rs._card_rules()['topTierPct']
        for x in hq:
            rr = rs._hq.position_pnl(x, upx)
            if rr['closed']:
                continue
            stk = rs._hq.swap_streak({**rr, 'events': x.get('events')})
            cmp_ = rs._hq.compound_streak({**rr, 'events': x.get('events')})
            ncopy = sum(1 for c in hq_all if c.get('copyOf') == x['id'])
            act = rs._hq.activity(len(rr['legs']) + ncopy, 1 + ncopy, rr['valueUsd'] * 24, rr['pnlPct'])
            act = {**act, 'score': min(100, act['score'] + stk['bonus'] + cmp_['bonus'])}
            act['tier'] = next(tn for cut, tn in rs._hq.ACTIVITY_TIERS if act['score'] >= cut)
            if rr['pnlPct'] >= top:
                act = {'score': max(act['score'], 90), 'tier': 'blazing'}
            out.append({'kind': 'user', 'id': x['id'], 'name': x.get('name') or 'Fuse card', 'emoji': '🃏', 'aura': '', 'owner': rs.handle_of(x['wallet']) or f"{x['wallet'][:4]}…{x['wallet'][-4:]}",
                        'legs': [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'baseAddress': l.get('mint'), 'weight': round(rs._fuse._f(l.get('usd')) / max(1e-9, rr['costUsd']) * 100, 2),
                                  'usd': l.get('usd'), 'tokens': l.get('tokens'), 'realizedUsd': l.get('realizedUsd'), 'soldUsd': l.get('soldUsd'), 'heldUsd': l.get('heldUsd'),
                                  'entry': (rs._fuse._f(l.get('usd')) / rs._fuse._f(l.get('tokens'))) if rs._fuse._f(l.get('tokens')) > 0 else None} for l in rr['legs']],   # true entry from the confirmed buy
                        'costUsd': rr['costUsd'], 'compound': cmp_, 'chat': f"fuse-card-{x['id']}",
                        'index': round(100 + rr['pnlPct'], 2), 'grade': 'A' if rr['pnlPct'] >= top else 'B' if rr['pnlPct'] >= 0 else 'C', 'buyers': 1, 'mode': x.get('mode') or 'hold',
                        'pnlPct': rr['pnlPct'], 'at': x.get('at'), 'activity': act, 'streak': stk, 'copies': ncopy, 'copyPct': rs._card_rules()['copyPct']})
    fc = await rs._feecat_card()
    if fc:
        out.append(fc)
    ac = rd.get('autoCard')
    if ac and ac.get('legs'):
        apx = await rs._hq_prices([l for l in ac['legs']])
        moves = [apx[l['pairAddress']] / l['entry'] for l in ac['legs'] if rs._fuse._f(apx.get(l['pairAddress'])) > 0 and rs._fuse._f(l.get('entry')) > 0]
        pct = round((sum(moves) / len(moves) - 1) * 100, 2) if moves else 0.0
        coins = sum(1 for l in ac['legs'] if l.get('runner'))
        out.append({'kind': 'auto', 'id': 'arena-pick', 'name': 'Arena Pick',   # stable id: its bracket record + chat survive each round's re-deal 'emoji': '⚔', 'aura': '', 'dial': 'degen' if coins >= 3 else 'balanced',
                    'tagline': f"{coins} coins + {len(ac['legs']) - coins} pools",
                    'legs': ac['legs'], 'index': round(100 + pct, 2), 'grade': 'A' if pct > 0 else 'B', 'buyers': 0, 'at': ac['at'], 'chat': f"fuse-card-{ac['id']}",
                    'activity': rs._hq.activity(len(ac['legs']), 0, sum(rs._fuse._f(l.get('vol1h')) for l in ac['legs']) * 24, pct)})
    published = {f.get('fromScenario') for f in (store.get('fuses') or {}).values() if f.get('arena') and f.get('fromScenario')}
    bench_names = set()
    for sc in rd.get('scenarioStage') or []:   # 🥈 runners-up: engine scenario cards waiting for HQ's audit (published ones show as mega)
        if sc.get('src') in published:
            continue
        spx = await rs._hq_prices([l for l in sc['legs']])
        mv_ = [spx[l['pairAddress']] / l['entry'] for l in sc['legs'] if rs._fuse._f(spx.get(l['pairAddress'])) > 0 and rs._fuse._f(l.get('entry')) > 0]
        pct_ = round((sum(m * rs._fuse._f(l['weight']) for m, l in zip(mv_, sc['legs'])) / max(1e-9, sum(rs._fuse._f(l['weight']) for l in sc['legs'][:len(mv_)])) - 1) * 100, 2) if mv_ else 0.0
        dial = sc.get('dial') or rs._rn.dial_of(sc['tp'], sc['sl'])
        own = f"{sc['emoji']} {sc['name']}" if sc.get('dial') and sc.get('emoji') else None
        nm_ = own if own and own not in bench_names else rs._rn.card_name(dial, sc['id'], bench_names)   # never two runners-up with one name
        bench_names.add(nm_)
        out.append({'kind': 'scenario', 'bench': True, 'id': sc['id'], 'src': sc.get('src'), 'version': sc.get('version'), 'name': nm_.split(' ', 1)[-1], 'emoji': nm_.split(' ', 1)[0], 'aura': '', 'legs': sc['legs'], 'index': round(100 + pct_, 2), 'dial': dial,
                    'cfg': sc.get('cfg') or rs._rn.card_cfg(dial, sc), 'grade': 'A' if pct_ > 0 else 'B', 'buyers': 0, 'at': sc['at'], 'chat': f"fuse-card-{sc['id']}", 'pnlPct': pct_,
                    'tagline': f"engine card · TP +{sc['tp']}% / stop −{sc['sl']}%",
                    'activity': rs._hq.activity(len(sc['legs']), 0, 0, pct_)})
    # 🏆 the engine's top battle winner is the ONE engine card that reaches the Arena by itself (HQ 🎨 picks the rest)
    pgb = rd.get('pgBattle') or {}
    champ_id = rs._pgb.champion(pgb.get('record'), pgb.get('cards'))
    if champ_id and champ_id not in set(rd.get('creatorPicks') or []):
        champ_id = None   # 🔒 HQ verifies every big engine card before it reaches the Arena (🎨 pick it in the playground)
    if champ_id and not any(x.get('src') == champ_id for x in out):
        cc = pgb['cards'][champ_id]; r_ = pgb['record'][champ_id]
        cpx = await rs._hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in cc['legs']])
        mv_ = [(rs._fuse._f(cpx.get(l['pairAddress'])) / l['entry'] - 1) * 100 for l in cc['legs'] if rs._fuse._f(cpx.get(l['pairAddress'])) > 0 and rs._fuse._f(l.get('entry')) > 0]
        pct_ = round(sum(mv_) / len(mv_), 2) if mv_ else 0.0
        nm_ = cc.get('name') or 'Engine champ'
        out.append({'kind': 'engine', 'bench': True, 'engineChamp': True, 'id': champ_id, 'src': champ_id, 'name': nm_.split(' ', 1)[-1], 'emoji': nm_.split(' ', 1)[0] if ' ' in nm_ else '🏆',
                    'legs': [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'baseAddress': l.get('mint'), 'weight': round(100 / max(1, len(cc['legs'])), 2), 'runner': l.get('role') == 'runner', 'entry': l.get('entry')} for l in cc['legs']],
                    'index': round(100 + pct_, 2), 'grade': 'A' if pct_ > 0 else 'B', 'buyers': 0, 'at': cc.get('at'), 'chat': f"fuse-card-{champ_id}", 'pnlPct': pct_, 'dial': cc.get('dial'),
                    'cfg': {'tp': int(rs._fuse._f(cc.get('tp'))), 'sl': int(rs._fuse._f(cc.get('sl'))), 'rotateHours': 1, 'slMode': 'sell'},
                    'tagline': f"engine champion · {r_.get('w', 0)}–{r_.get('l', 0)} in playground battles", 'activity': rs._hq.activity(len(cc['legs']), 0, 0, pct_)})
    # 🎛 at most 4 engine cards on the Arena, each with ≥ 6 coins: the engine champion first, then the best runners-up
    eng = [x for x in out if x.get('kind') in ('scenario', 'engine') and x.get('bench')]
    arena_runner_cards = sum(1 for x in out if x.get('kind') in ('lit', 'round', 'auto'))   # cards the Arena's own runner rounds made
    keep = sorted([x for x in eng if len(x.get('legs') or []) >= rs._pgb.MIN_COINS], key=lambda x: (not x.get('engineChamp'), -rs._fuse._f(x.get('pnlPct'))))[:min(4, arena_runner_cards)]   # ⚖ never more playground than Arena picks
    out = [x for x in out if x not in eng or x in keep]
    # ⭐ top-tier cards fight in the bracket too (fighters only — they already have their own section at the top of the Arena)
    tier_dial = {'diamond': 'safe', 'ever': 'safe', 'gold': 'balanced', 'blaze': 'degen', 'next': 'degen'}
    pcfg = rs._prime_cfg()
    for pc_ in await rs._prime_view():
        out.append({'kind': 'prime', 'fighterOnly': True, 'id': pc_['tpl'], 'name': pc_['label'].split(' ', 1)[-1], 'emoji': pc_['label'].split(' ', 1)[0],
                    'legs': [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'baseAddress': l.get('mint'), 'weight': round(rs._fuse._f(l.get('usd')) / max(1e-9, pc_['valueUsd']) * 100, 2), 'runner': l.get('role') == 'runner', 'entry': l.get('entry')} for l in pc_['legs']],
                    'index': round(100 + rs._fuse._f(pc_.get('pnlPct')), 2), 'grade': 'A' if rs._fuse._f(pc_.get('pnlPct')) > 0 else 'B', 'buyers': 0, 'at': pc_.get('at'), 'chat': f"fuse-card-prime-{pc_['tpl']}",
                    'dial': tier_dial.get(pc_.get('tier')), 'cfg': {'tp': pc_.get('tp'), 'sl': pc_.get('sl'), 'rotateHours': pcfg.get('rotateHours'), 'slMode': {'replace': 'sell'}.get(pcfg.get('slMode'), pcfg.get('slMode')), 'cycle': pc_.get('cycleMode')},
                    'tagline': f"top-tier card · {pc_.get('rounds', 0)} rounds", 'activity': rs._hq.activity(len(pc_['legs']), 0, 0, rs._fuse._f(pc_.get('pnlPct'))),
                    'real': pc_.get('cfgScope') == 'real'})
    rnd = (rd.get('rounds') or [None])[-1]
    if not [x for x in out if not x.get('fighterOnly')] and rnd and rnd.get('picks'):   # never an empty stage: the live round stands in as a proving card
        ps = rnd['picks']
        moves = [((rs._fuse._f(live.get(p['mint'], {}).get('price')) or p['entry']) / p['entry'] - 1) * 100 for p in ps if rs._fuse._f(p.get('entry')) > 0]
        mv = round(sum(moves) / len(moves), 2) if moves else 0.0
        out.append({'kind': 'round', 'id': str(rnd.get('id')), 'name': ' · '.join(f"${p.get('symbol')}" for p in ps[:4]), 'emoji': '⏳', 'aura': '',
                    'legs': [{'pairAddress': p.get('pairAddress') or p['mint'], 'symbol': p.get('symbol'), 'baseAddress': p['mint'], 'logo': p.get('logo'),
                              'weight': round(100 / len(ps), 2), 'entry': p.get('entry')} for p in ps], 'chat': f"fuse-card-{rnd.get('id')}",
                    'index': round(100 + mv, 2), 'grade': 'B', 'buyers': 0, 'at': rnd.get('at'),
                    'activity': rs._hq.activity(0, 0, sum(rs._fuse._f(live.get(p['mint'], {}).get('vol1h')) * 24 for p in ps), mv)})
    rec = rs._json_load(rs.FUSE_HQ_PATH, {}).get('battleRecord') or {}
    out = [{**c, 'record_wl': rec.get(f"{c['kind']}:{c['id']}")} for c in out]
    out = await rs._card_dna_tag(out, rd)
    out.sort(key=lambda x: -x['activity']['score'])
    rs._arena_mega_cache.update(at=now, data=out)
    if out and now - rs._arena_mega_cache.get('savedAt', 0) >= 60:
        rs._arena_mega_cache['savedAt'] = now
        try:
            await rs.asyncio.to_thread(rs._launchpad_board.save_board_snapshot, rs.ARENA_SNAPSHOT_PATH, 'mega', out, {}, now)
        except Exception:
            pass
    return out


async def _card_dna_tag(cards, rd):
    """🧬 Every Arena card carries its own DNA: user cards = their plan · tier cards = their tier config · engine cards = the battle DNA ·
    everything else gets a unique DNA (stable per card, stored) — so no two cards play alike."""
    rs = _rs()
    pcfg = rs._prime_cfg(); pos = {x['id']: x for x in rs._json_load(rs.FUSE_HQ_PATH, {}).get('positions') or []}
    pgd = ((rd.get('pgBattle') or {}).get('dna') or {})
    fixed = {}
    for c in cards:
        k = f"{c['kind']}:{c['id']}"
        if c['kind'] == 'user' and c['id'] in pos:
            x = pos[c['id']]
            fixed[k] = rs._dna.clean({'cycle': x.get('cycle') if x.get('cycle') in ('classic', 'adaptive', 'safe', 'press', 'rescue', 'auto') else 'off', 'compound': x.get('compoundStyle') or 'smart', 'payoutPct': x.get('payoutPct', 100),
                                   'clock': x.get('rotateHours') or 24, 'stop': x.get('slMode') or 'sell'})
        elif c['kind'] == 'prime':
            fixed[k] = rs._dna.clean({'cycle': (pcfg.get('cycles') or {}).get(c['id'], 'off'), 'compound': pcfg.get('compoundStyle', 'smart') if pcfg.get('compound') else 'off',
                                   'payoutPct': (pcfg.get('payouts') or {}).get(c['id'], 0), 'clock': pcfg.get('rotateHours'), 'stop': {'replace': 'sell'}.get(pcfg.get('slMode'), pcfg.get('slMode')), 'trail': pcfg.get('trail', True)})
        elif c['kind'] == 'engine' and pgd.get(c['id']):
            fixed[k] = pgd[c['id']]
    store = rs._json_load(rs.FUSE_HQ_PATH, {}).get('cardDna') or {}
    known = {**store, **fixed}
    assigned = rs._dna.assign([{'id': f"{c['kind']}:{c['id']}", 'dial': c.get('dial')} for c in cards], known=known)
    new = {k: v for k, v in assigned.items() if k not in fixed and k not in store}
    if new:
        async with rs._admin_lock:
            d = rs._json_load(rs.FUSE_HQ_PATH, {}); d['cardDna'] = {**dict(list((d.get('cardDna') or {}).items())[-300:]), **new}; rs._json_save(rs.FUSE_HQ_PATH, d)
    return [{**c, 'dna': assigned[f"{c['kind']}:{c['id']}"], 'dnaLabel': rs._dna.label(assigned[f"{c['kind']}:{c['id']}"])} for c in cards]


async def _fuse_candidates(chain='solana'):
    """The gene pool: best ~40 live pools across popular / yield / deep / new (one row per pool)."""
    rs = _rs()
    raw = await rs._fuse_discover_pairs(chain)
    cands = {}
    for lens in rs._fuse.LENSES:
        for r in rs._fuse.discover(raw, lens, chain, now_ms=rs.time.time() * 1000, limit=12):
            cands.setdefault(r['pairAddress'], r)
    return cands


def _champ_view(c, metas, chain='solana'):
    return {**c, 'legs': [{**{k: metas[pa].get(k) for k in ('symbol', 'quote', 'dex', 'logo', 'liquidityUsd', 'aprEst', 'change24h', 'baseAddress', 'quoteAddress')},
                           'chainId': chain, 'pairAddress': pa, 'weight': c['weights'][pa]} for pa in c['pools']]}

