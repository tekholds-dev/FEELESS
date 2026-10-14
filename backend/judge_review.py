"""👨‍⚖️ THE JUDGE: LOSS ACCOUNTABILITY, NOT A FEAR ENGINE (owner's spec, 2026-10-11).

After EVERY confirmed exit of an agent seat the Judge reviews it from the archive's record (entry structure + call, tier, data quality,
pool, holders, P/L path, peak, low, exit rule, velocity): ROOT CAUSE · RESPONSIBLE DESK · SEVERITY · RECOMMENDED CHANGE · CONFIDENCE, and a
0–100 responsibility per desk. It must say whether it was a BAD DECISION or a VALID DECISION THAT LOST. Wins are reviewed too (what to do
more of). A cause becomes a rule only by repetition: seen once = record only · twice = SHADOW (shown, not applied) · ≥ 3 in the recent
window = PROMOTED as a bounded RANKING penalty (≤ 8 points, expires after 24h) — never a new hard veto: a loss alone is not proof a rule
must get stricter. Pure, tested."""

DESKS = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'reaper')
KEEP = 80
WINDOW = 20             # the recent reviews patterns are counted over
SHADOW_N, PROMOTE_N = 2, 3
PROMOTE_PTS = 8.0
PROMOTE_SEC = 24 * 3600
GOOD_ENTRY = ('UPTREND', 'PULLBACK IN UPTREND', 'CONFIRMED BREAKOUT', 'BREAKOUT ATTEMPT', 'EARLY', 'ACCUMULATION', 'COMPRESSION')
# root cause → (desk, severity, recommended change, the ranking penalty a PROMOTED pattern applies: (feature, test-on-a-row words))
CAUSES = {
    'rugged': ('devil', 'high', 'Devil: weigh the rug signs that were on this coin harder (liquidity drain, holders)', 'thin pool'),
    'collapsing_entry': ('trigger', 'mid', 'Trigger: wait for a higher low after a fast drop before entering', 'falling now'),
    'entered_on_wait': ('trigger', 'low', 'Ranking: an entry the chart said to wait on needs a stronger score', 'chart says wait'),
    'thin_pool': ('warden', 'mid', 'Warden: a smaller seat in this liquidity band', 'thin pool'),
    'weak_holders': ('devil', 'mid', 'Devil: holder concentration counted against the rank', 'weak holders'),
    'bad_data': ('tally', 'mid', 'Tally: stale or sparse data should not carry an entry', 'thin data'),
    'after_distribution': ('devil', 'high', 'Devil: never enter while the early wallets are selling into the move (distribution)', 'early selling'),
    'crowd_fomo': ('trigger', 'mid', 'Trigger: this was the crowd\'s top — enter in early / accelerating FOMO, not after it', 'crowd fomo'),
    'bundled_exit': ('warden', 'mid', 'Warden: a bundled / clustered launch still holding its early supply gets a smaller seat', 'bundled'),
    'too_old': ('sherlock', 'mid', 'Ranking: a coin over 12h old needs a waking-up signal before it takes a seat from a fresh launch', None),
    'fallback_entry': ('trigger', 'mid', 'Seats: the best-available door must clear a B-tier entry score — cash beats the least-bad coin', None),
    'gave_back': ('reaper', 'mid', 'Reaper: trail a +8% winner tighter', None),
    'held_too_long': ('reaper', 'low', 'Reaper: replace a flat seat sooner', None),
    'variance': (None, 'none', 'none — a valid setup that lost; no rule changes', None),
}


# every loss in ONE of five words (owner, 2026-10-11): what kind of mistake it was — never a reason to tighten everything
LOSS_CLASS = {'variance': 'NORMAL LOSS', 'gave_back': 'BAD EXIT', 'held_too_long': 'BAD HOLD', 'collapsing_entry': 'BAD TIMING', 'entered_on_wait': 'BAD TIMING',
              'crowd_fomo': 'BAD TIMING', 'after_distribution': 'BAD ENTRY', 'bundled_exit': 'BAD ENTRY', 'thin_pool': 'BAD ENTRY', 'weak_holders': 'BAD ENTRY',
              'too_old': 'BAD ENTRY', 'fallback_entry': 'BAD ENTRY', 'bad_data': 'BAD ENTRY', 'rugged': 'BAD ENTRY'}


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def review(p):
    """One closed position (the archive's record) → the Judge's review. Losses get a root cause + desk blame; wins get why it worked."""
    p = p or {}
    pct = _f(p.get('realPct') if p.get('realPct') is not None else p.get('lastPct'))
    th = p.get('thesis') or {}
    entry, call = th.get('structure'), th.get('call')
    path = [_f(x) for x in (p.get('path') or [])]
    peak = _f(p.get('peak'))
    held = max(0.0, (_f(p.get('closedAt')) - _f(p.get('since'))) / 60) if p.get('since') else None
    rule = str(p.get('rule') or '')
    tier = (str(p.get('tag') or '').split('· ')[-1].split('-tier')[0] if '-tier' in str(p.get('tag') or '') else None)
    lis = p.get('li') or {}
    base = {'sym': p.get('sym'), 'mint': p.get('mint'), 'at': _f(p.get('closedAt')), 'pct': round(pct, 2), 'held': None if held is None else round(held, 1),
            'peak': round(peak, 1), 'entry': entry, 'call': call, 'tier': tier, 'exit': rule, 'band': p.get('band'),
            'phase': lis.get('phase'), 'cls': lis.get('cls'), 'rank': (lis.get('rank') or [None])[0], 'early': lis.get('early'), 'ageH': lis.get('ageH'), 'mcap': lis.get('mcap')}
    if pct > 0:
        why = [x for x in (f"entered on {entry}" if entry else None, f"{call}" if call else None, f"peak +{peak:.0f}%" if peak else None,
                           f"held {held:.0f} min" if held is not None else None, f"exit: {rule}" if rule else None, f"tier {tier}" if tier else None,
                           f"phase {base['phase']}" if base['phase'] else None, f"{base['cls']}" if base['cls'] else None, f"buyer rank {base['rank']}" if base['rank'] else None,
                           f"early wallets held {base['early']:.0f}%" if base['early'] is not None else None) if x]
        return {**base, 'kind': 'win', 'why': ' · '.join(why), 'pattern': f"{entry or 'unknown'}|{tier or '-'}"}
    resp = {d: 0 for d in DESKS}
    li = p.get('li') or {}
    if any(k in rule for k in ('R1', 'R2', 'R4', 'rug', 'drain', 'pool')) or _f(p.get('liqPct')) and _f(p.get('liqPct')) < 50:
        cause = 'after_distribution' if li.get('phase') == 'DISTRIBUTION' or li.get('press') in ('WATCH', 'HIGH') else 'rugged'
    elif li.get('phase') == 'DISTRIBUTION' or li.get('press') in ('WATCH', 'HIGH'):
        cause = 'after_distribution'
    elif li.get('phase') == 'CROWD FOMO' and pct <= -5:
        cause = 'crowd_fomo'
    elif li.get('cls') in ('BUNDLED', 'INSIDER-LIKE CLUSTER') and _f(li.get('early')) >= 20 and pct <= -10:
        cause = 'bundled_exit'
    elif 'best available' in str(p.get('tag') or '') and pct <= -3:
        cause = 'fallback_entry'
    elif _f((p.get('launch') or {}).get('ageH') if (p.get('launch') or {}).get('ageH') is not None else li.get('ageH')) >= 12 and pct <= -3:
        cause = 'too_old'
    elif peak >= 8 and pct <= 0:
        cause = 'gave_back'
    elif len(path) >= 2 and min(path[:2]) <= -5:
        cause = 'collapsing_entry'
    elif p.get('dd') or p.get('quality') in ('SPARSE', 'NO_REAL_CANDLES', 'STALE', 'INVALID'):
        cause = 'bad_data'
    elif p.get('liq') is not None and 0 < _f(p.get('liq')) < 20_000 and pct <= -10:
        cause = 'thin_pool'
    elif p.get('top10') is not None and _f(p.get('top10')) >= 30 and pct <= -10:
        cause = 'weak_holders'
    elif call and call != 'ENTER NOW' and tier in ('C', None) and pct <= -5:
        cause = 'entered_on_wait'
    elif rule.startswith('R9') and abs(pct) < 5:
        cause = 'held_too_long'
    elif entry in GOOD_ENTRY and pct > -12:
        cause = 'variance'
    else:
        cause = 'collapsing_entry' if pct <= -12 else 'variance'
    desk, sev, change, _pen = CAUSES[cause]
    if desk:
        resp[desk] = 80 if sev == 'high' else 60 if sev == 'mid' else 40
        if cause in ('collapsing_entry', 'entered_on_wait'):
            resp['sherlock'] = 20   # the reasons pointed in
        if cause == 'rugged':
            resp['warden'] = 30     # it was sized into it
    if pct <= -10 and tier in ('B', 'C') and p.get('warden') is not None and _f(p.get('warden')) >= 0.75:   # 🛡 a low-confidence entry at ≥ 75% of a seat: the Warden sized too large
        resp['warden'] = max(resp['warden'], 50)
    sized_ = resp['warden'] >= 50 and cause != 'rugged'
    return {**base, 'kind': 'loss', 'cause': cause, 'lossClass': LOSS_CLASS.get(cause, 'BAD ENTRY'), 'desk': desk, 'oversized': sized_, 'severity': sev, 'change': change, 'resp': resp,
            'decision': 'valid decision that lost' if cause == 'variance' else 'bad decision',
            'lesson': change if cause != 'variance' else 'the setup was valid — keep taking it; size handles the variance'}


def note(state, p, now):
    """File one review (skip a position already reviewed) → new state {reviews: [...]}."""
    st = dict(state or {})
    rs = list(st.get('reviews') or [])
    key = (p or {}).get('mint'), round(_f((p or {}).get('closedAt')))
    if any((r.get('mint'), round(_f(r.get('at')))) == key for r in rs[-40:]):
        return st
    rs.append(review(p))
    st['reviews'] = rs[-KEEP:]
    return st


def court(state, now):
    """The Judge's dashboard + the rules it runs: last loss / last win, desk responsibility (average over recent losses), loss and win
    patterns, SHADOW rules (seen twice) and PROMOTED rules (≥ 3 of the same cause in the recent window, bounded, 24h)."""
    rs = list((state or {}).get('reviews') or [])
    recent = rs[-WINDOW:]
    losses = [r for r in recent if r.get('kind') == 'loss']
    wins = [r for r in recent if r.get('kind') == 'win']
    by = {}
    for r in losses:
        if r.get('cause') != 'variance':
            by.setdefault(r['cause'], []).append(r)
    shadow, promoted = [], []
    for cause, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        desk, sev, change, pen = CAUSES[cause]
        row = {'cause': cause, 'n': len(xs), 'desk': desk, 'change': change, 'last': max(_f(x.get('at')) for x in xs)}
        if len(xs) >= PROMOTE_N and pen and now - row['last'] < PROMOTE_SEC:
            promoted.append({**row, 'penalty': pen, 'points': -PROMOTE_PTS, 'confidence': 'HIGH', 'until': row['last'] + PROMOTE_SEC})
        elif len(xs) >= SHADOW_N:
            shadow.append({**row, 'confidence': 'MEDIUM', 'note': 'shown, not applied — one more of the same cause promotes it' if pen else 'recorded for the desk (no ranking rule)'})
    scores = {d: round(sum(_f((r.get('resp') or {}).get(d)) for r in losses) / len(losses)) if losses else 0 for d in DESKS}
    wp = {}
    for r in wins:
        wp.setdefault(r.get('pattern'), []).append(_f(r.get('pct')))
    return {'lastLoss': next((r for r in reversed(rs) if r.get('kind') == 'loss'), None), 'lastWin': next((r for r in reversed(rs) if r.get('kind') == 'win'), None),
            'scores': scores, 'losses': len(losses), 'wins': len(wins),
            'lossPatterns': [{'cause': c, 'n': len(v), 'desk': CAUSES[c][0]} for c, v in sorted(by.items(), key=lambda kv: -len(kv[1]))][:5],
            'variance': sum(1 for r in losses if r.get('cause') == 'variance'),
            'winPatterns': sorted(({'pattern': k, 'n': len(v), 'avg': round(sum(v) / len(v), 1)} for k, v in wp.items()), key=lambda x: -x['n'])[:5],
            'shadow': shadow, 'promoted': promoted, 'launchShape': launch_shape(rs)}


def launch_shape(rs):
    """🕵 WHAT EARLY WINNERS LOOK LIKE vs losers: every reviewed exit (all kept, not only the recent window) grouped by its launch shape at
    entry — FOMO phase, buyer rank, launch class → {key: {value: {n, won %, avg}}}. Only reviews that carried a launch-intel snapshot."""
    out = {}
    for k in ('phase', 'rank', 'cls'):
        g = {}
        for r in rs or []:
            if r.get(k):
                g.setdefault(r[k], []).append(_f(r.get('pct')))
        out[k] = {v: {'n': len(xs), 'won': round(100 * sum(x > 0 for x in xs) / len(xs)), 'avg': round(sum(xs) / len(xs), 1)} for v, xs in g.items()}
    return out


LIVE_RULES = True    # 👨‍⚖️ LIVE AS RANKING WEIGHTS (owner, 2026-10-13: "do #3"): a cause the Judge saw ≥ 3× in its last 20 real-loss reviews ranks
                     # matching coins DOWN (≤ 8 points each, expires 24h after its last case). Never a veto, never a threshold, never a
                     # sell — a seat is not left empty for it. It was frozen on 2026-10-12 and had never been wired into the live ranking.


def penalties(promoted, live=None):
    """The promoted rules as ranking penalties: {feature words: points} (opportunity.score subtracts them from matching coins).
    {} when LIVE_RULES is off (or live=False) — then the proposals only stay on record (`court`)."""
    if not (LIVE_RULES if live is None else live):
        return {}
    out = {}
    for r in promoted or []:
        if r.get('penalty'):
            out[r['penalty']] = min(out.get(r['penalty'], 0.0), _f(r.get('points')))
    return out


# ── 📋 PER-DESK REAL-MONEY RECORD (owner's spec: "no BS scorecards — real decisions, win / loss responsibility, accuracy, median net impact")
ENTRY_DESKS = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden')   # every real entry passed through each of these
TAKE_EXITS = ('R6', 'R7')                                                         # Reaper's own profit exits (take / trail / structure / reversal)


def desk_stats(reviews):
    """From the Judge's reviews of REAL exits only. decisions = real trades the desk took part in (every entry desk on every entry;
    Reaper on every exit) · winResp = wins it is credited with (entry desks on every win; Reaper only when its own profit exit took it) ·
    lossResp = losses the Judge PINNED on it (resp > 0 — "variance" losses blame nobody) · accuracy = share of the trades it took part in
    that made money (no desk can read 100% because the Judge never blamed it) · medNet = median real % of those trades. Nothing summed."""
    import statistics as _st
    out = {}
    rv = [r for r in reviews or [] if r.get('kind') in ('win', 'loss')]
    for d in ENTRY_DESKS + ('reaper',):
        win = sum(1 for r in rv if r['kind'] == 'win' and (d in ENTRY_DESKS or str(r.get('exit') or '').startswith(TAKE_EXITS)))
        loss = sum(1 for r in rv if r['kind'] == 'loss' and _f((r.get('resp') or {}).get(d)) > 0)
        vals = [_f(r.get('pct')) for r in rv]
        out[d] = {'decisions': len(rv), 'winResp': win, 'lossResp': loss,
                  'accuracy': round(sum(1 for v in vals if v > 0) / len(vals) * 100) if vals else None,
                  'medNet': round(_st.median(vals), 2) if vals else None}
    return out


# 🗳 EACH DESK ON ITS OWN VOTE (owner-approved build b5 + b10, 2026-10-13: "show agent decision overlap" — `desk_stats` credits every
# entry desk with the SAME team record, so seven desks read "80 real decisions, 62% right" and nobody can tell them apart). At the moment
# a real seat is allowed, each entry desk's own stance is stamped on the entry thesis as a VOTE: GO (it was for it) or DOUBT (it pushed
# against it). A desk is RIGHT when its vote matches the real result (GO and the trade made money · DOUBT and it lost). A LONE dissent =
# the only desk voting against the other five; it is the measure of what that desk alone would have changed. Pure.
VOTE_DESKS = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden')


def votes_of(op):
    """The kernel's ten opinions for a coin (trench_kernel.brain.think → 'opinions') → {desk: 'go' | 'doubt'} for the six entry desks.
    A desk with no opinion has no vote (never a guess)."""
    o, out = op or {}, {}
    t = o.get('tally')
    if t:
        out['tally'] = 'go' if _f(t.get('move5m')) > 0 and _f(t.get('vpm')) > 0 else 'doubt'
    s = o.get('sherlock')
    if s:
        out['sherlock'] = 'go' if _f(s.get('factor')) >= 1.0 and 'holders' not in (s.get('unknown') or ()) else 'doubt'
    w = o.get('weather')
    if w:
        out['weather'] = 'go' if _f(w.get('factor')) >= 1.0 else 'doubt'
    g = o.get('trigger')
    if g:
        out['trigger'] = 'go' if g.get('state') == 'ENTER' else 'doubt'
    d = o.get('devil')
    if d:
        out['devil'] = 'doubt' if any(sv in ('STRONG_WARNING', 'HARD_VETO') for _o, sv, _w in (d.get('objections') or [])) else 'go'
    a = o.get('warden')
    if a:
        out['warden'] = 'go' if _f(a.get('size')) >= 0.75 else 'doubt'
    return out


def votes_from_pos(p):
    """A position's votes: the stamped ones, else what the archive already kept for older trades (Weather's regime, the Warden's size,
    the door Trigger let it in by). Desks that left nothing have no vote."""
    p = p or {}
    v = dict(((p.get('thesis') or {}).get('votes')) or {})
    if 'weather' not in v and p.get('wx'):
        v['weather'] = 'go' if p['wx'] in ('HOT', 'NORMAL') else 'doubt'
    if 'warden' not in v and p.get('warden') is not None:
        v['warden'] = 'go' if _f(p['warden']) >= 0.75 else 'doubt'
    if 'trigger' not in v and p.get('tag'):
        tag = str(p['tag'])
        if 'ARMED' in tag or 'best available' in tag or 'seat floor' in tag:
            v['trigger'] = 'doubt'
        elif 'READY' in tag:
            v['trigger'] = 'go'
    return v


def desk_votes(trades, min_n=5):
    """Confirmed real exits (real_memory.trades) → {desk: {n, right, rightPct, go: {n, med}, doubt: {n, med}, lone, loneRight}}. `rightPct`
    is None under `min_n` votes. A trade at exactly 0% counts as a loss (fees made it one)."""
    import statistics as _st
    out = {d: {'n': 0, 'right': 0, 'go': [], 'doubt': [], 'lone': 0, 'loneRight': 0} for d in VOTE_DESKS}
    for p in trades or []:
        pct = p.get('realPct')
        if pct is None:
            continue
        won, v = _f(pct) > 0, votes_from_pos(p)
        known = [d for d in VOTE_DESKS if v.get(d) in ('go', 'doubt')]
        for d in known:
            o = out[d]
            o['n'] += 1
            right = (v[d] == 'go') == won
            o['right'] += int(right)
            o[v[d]].append(_f(pct))
            others = [v[x] for x in known if x != d]
            if len(others) >= 3 and all(x != v[d] for x in others):   # the ONLY desk on its side
                o['lone'] += 1; o['loneRight'] += int(right)
    res = {}
    for d, o in out.items():
        res[d] = {'n': o['n'], 'right': o['right'], 'rightPct': round(o['right'] / o['n'] * 100) if o['n'] >= min_n else None,
                  'go': {'n': len(o['go']), 'med': round(_st.median(o['go']), 1) if o['go'] else None},
                  'doubt': {'n': len(o['doubt']), 'med': round(_st.median(o['doubt']), 1) if o['doubt'] else None},
                  'lone': o['lone'], 'loneRight': o['loneRight']}
    return res


def vote_line(d, r):
    """One line for the model / the page: what this desk's OWN vote has been worth on real money."""
    if not r or not r.get('n'):
        return f"{d}: no own vote on file yet"
    g, b = r['go'], r['doubt']
    return (f"{d}: own vote right {r['rightPct'] if r['rightPct'] is not None else 'UNKNOWN'}% of {r['n']} · said GO {g['n']}× (typical {g['med'] if g['med'] is not None else '—'}%) · "
            f"DOUBTED {b['n']}× (typical {b['med'] if b['med'] is not None else '—'}%) · lone dissent {r['lone']}× ({r['loneRight']} right)")
