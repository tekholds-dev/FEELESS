"""📚 CHAT EVIDENCE (owner, 2026-10-14: "make LM chat see real FEELESS data — it answers generic / hypothetical"). Pure + tested
(`tests/test_chat_evidence.py`).

A question about what HAPPENED ("why did the agents fail last night?", "what trades hurt us?", "which agent was wrong?", "what did Reaper
miss?", "why was X bought / sold?") gets a compact EVIDENCE PACKET built only from FEELESS's own records inside the asked time window:
confirmed real exits (archive positions), the keeper's ledger (fills, refusals, failures, landing), the Judge's reviews (cause, desk, lesson),
the card's own agent events and the in-memory decision tape — plus `known_gaps` naming every source that has nothing for that window.
The model reads the packet as DATA and must answer from it; nothing here trades or changes a setting.
"""
import re
import time

ASK = re.compile(r"\b(why|what happened|last night|overnight|tonight|yesterday|today|this morning|earlier|hours?|trades?|lost|loss(es)?|losing|fail(ed|ing)?|"
                 r"hurt|wrong|miss(ed)?|bought|sold|buy|sell|reaper|trigger|devil|warden|courier|judge|sherlock|tally|archivist|weather|agents?|biggest|worst|best|rug(s|ged)?|"
                 r"exit(s|ed)?|entr(y|ies)|seat|card|pnl|p&l|profit|record|happen)\b", re.I)
KEEP_TRADES, KEEP_EVENTS, KEEP_REVIEWS = 10, 12, 8
RUG = -45.0


from fnum import nan_safe as _f


def wants(question):
    """Does this question ask about something that HAPPENED (→ real records), or is it general talk?"""
    return bool(ASK.search(str(question or '')))


def _lt(ts):
    return time.localtime(ts)


def window(question, now):
    """The time window the question asks about → {from, to, label}. last night / overnight = 20:00 the evening before → 09:00 (or now, if
    earlier); yesterday = the whole previous day; today / this morning = since midnight; "last N hours" / "N h" = now − N h; else 12h."""
    q = str(question or '').lower()
    lt = _lt(now)
    midnight = now - (lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec)
    m = re.search(r'(?:last|past)\s+(\d{1,2})\s*(?:h|hr|hrs|hours?)\b|\b(\d{1,2})\s*(?:h|hrs?|hours?)\b', q)
    if m:
        h = int(m.group(1) or m.group(2))
        h = max(1, min(72, h))
        return {'from': now - h * 3600, 'to': now, 'label': f'last {h}h'}
    if re.search(r'last night|overnight|tonight|while i (was )?(asleep|sleeping)|when i (went to )?sle', q):
        end = midnight + 9 * 3600 if now >= midnight + 9 * 3600 else now
        start = midnight - 4 * 3600
        return {'from': start, 'to': end, 'label': 'last night (20:00 → 09:00)'}
    if 'yesterday' in q:
        return {'from': midnight - 86400, 'to': midnight, 'label': 'yesterday'}
    if re.search(r'\btoday\b|this morning', q):
        return {'from': midnight, 'to': now, 'label': 'today'}
    return {'from': now - 12 * 3600, 'to': now, 'label': 'last 12h'}


def _hm(ts):
    return time.strftime('%m-%d %H:%M', _lt(ts)) if ts else None


def trades_in(positions, w):
    """Confirmed real exits closed inside the window (one per sale; duplicates dropped)."""
    out = []
    for p in positions or []:
        if not p.get('confirmed') or p.get('realPct') is None or (p.get('exit') or {}).get('state') == 'duplicate':
            continue
        at = _f(p.get('closedAt'))
        if w['from'] <= at <= w['to']:
            out.append(p)
    return out


def _trade_row(p):
    th, li = p.get('thesis') or {}, p.get('li') or {}
    age = (p.get('launch') or {}).get('ageH')
    return {k: v for k, v in {
        'coin': p.get('sym'), 'mint': str(p.get('mint') or '')[:8], 'in': _hm(_f(p.get('since'))), 'out': _hm(_f(p.get('closedAt'))),
        'heldMin': round((_f(p.get('closedAt')) - _f(p.get('since'))) / 60, 1) if p.get('since') else None,
        'pct': round(_f(p.get('realPct')), 1), 'usd': round(_f((p.get('exit') or {}).get('realUsd')), 3) if (p.get('exit') or {}).get('realUsd') is not None else None,
        'peak': round(_f(p.get('peak')), 1) if p.get('peak') is not None else None, 'exit': p.get('rule'),
        'door': str(p.get('tag') or '').replace('🤖 agents · ', '')[:26] or None, 'entry': th.get('call'), 'structure': th.get('structure'),
        'ageMin': round(_f(age) * 60) if age is not None and _f(age) >= 0 else None, 'phase': li.get('phase')}.items() if v is not None}


def _med(xs):
    s = sorted(xs)
    return (s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2) if s else None


def summary(ts):
    """The window in numbers: exits, won %, typical / average %, rugs, the exits that lost the most, by exit rule and by door."""
    if not ts:
        return None
    pcts = [_f(p['realPct']) for p in ts]
    by_rule, by_door = {}, {}
    for p in ts:
        by_rule.setdefault(str(p.get('rule') or '?')[:28], []).append(_f(p['realPct']))
        by_door.setdefault(str(p.get('tag') or '?').replace('🤖 agents · ', '')[:22], []).append(_f(p['realPct']))
    agg = lambda g: [{'group': k, 'exits': len(v), 'avgPctEach': round(sum(v) / len(v), 1), 'totalPctPts': round(sum(v), 0)}   # named fields: a bare column was misread as one coin's loss
                     for k, v in sorted(g.items(), key=lambda kv: sum(kv[1]))[:6]]
    usd = [_f((p.get('exit') or {}).get('realUsd')) for p in ts if (p.get('exit') or {}).get('realUsd') is not None]
    return {'exits': len(ts), 'wonPct': round(100 * sum(1 for x in pcts if x > 0) / len(pcts)), 'medPct': round(_med(pcts), 1), 'avgPct': round(sum(pcts) / len(pcts), 1),
            'rugs': sum(1 for x in pcts if x <= RUG), 'rugLossPctPts': round(sum(x for x in pcts if x <= RUG), 0), 'realizedUsd': round(sum(usd), 2) if usd else None,
            'byExitRule': agg(by_rule), 'byDoor': agg(by_door)}


def execution(ledger, w, card=None):
    """The keeper's ledger inside the window: fills, refused / failed buys + sells with their reasons, landing time, write-offs, top-ups."""
    rows = [r for r in ledger or [] if w['from'] <= _f(r.get('at')) <= w['to'] and (card is None or r.get('card') in (None, card))]
    if not rows:
        return None
    fills = [r for r in rows if r.get('status') == 'filled' and r.get('side') in ('buy', 'sell')]
    bad = [r for r in rows if r.get('status') in ('failed', 'skipped', 'refused') and r.get('side') in ('buy', 'sell')]
    why = {}
    for r in bad:
        k = re.sub(r'[\d.$%]+', '#', str(r.get('err') or r.get('why') or '?'))[:60]
        why[k] = why.get(k, 0) + 1
    land = [_f(r.get('landSec')) for r in fills if r.get('landSec') is not None]
    return {k: v for k, v in {
        'buys': sum(1 for r in fills if r['side'] == 'buy'), 'sells': sum(1 for r in fills if r['side'] == 'sell'),
        'realizedUsd': round(sum(_f(r.get('realizedPnlUsd')) for r in fills if r['side'] == 'sell'), 2),
        'refusedOrFailed': len(bad), 'topReasons': sorted(([k, n] for k, n in why.items()), key=lambda x: -x[1])[:5],
        'landSecMed': round(_med(land), 1) if land else None,
        'writeOffs': [[r.get('symbol'), _hm(_f(r.get('at')))] for r in rows if r.get('side') == 'writeoff'][:5] or None,
        'topUps': [[round(_f(r.get('usd')), 2), _hm(_f(r.get('at')))] for r in rows if r.get('side') == 'topup'][:5] or None,
        'halts': [[_hm(_f(r.get('at'))), str(r.get('why') or '')[:60]] for r in rows if r.get('side') == 'fix' and 'halt' in str(r.get('why') or '').lower()][:3] or None,
    }.items() if v not in (None, [], {})}


def judge(reviews, w):
    """The Judge's rulings on real exits inside the window: cause and desk counts + the worst few with the lesson."""
    rv = [r for r in reviews or [] if w['from'] <= _f(r.get('at')) <= w['to']]
    if not rv:
        return None
    cause, desk = {}, {}
    for r in rv:
        if r.get('kind') == 'loss':
            cause[r.get('cause') or '?'] = cause.get(r.get('cause') or '?', 0) + 1
            desk[r.get('desk') or '?'] = desk.get(r.get('desk') or '?', 0) + 1
    worst = sorted((r for r in rv if r.get('kind') == 'loss'), key=lambda r: _f(r.get('pct')))[:KEEP_REVIEWS]
    return {'reviews': len(rv), 'losses': sum(1 for r in rv if r.get('kind') == 'loss'), 'wins': sum(1 for r in rv if r.get('kind') == 'win'),
            'lossCauses': sorted(([k, n] for k, n in cause.items()), key=lambda x: -x[1])[:6], 'deskBlamed': sorted(([k, n] for k, n in desk.items()), key=lambda x: -x[1])[:6],
            'worst': [{k: v for k, v in {'coin': r.get('sym'), 'at': _hm(_f(r.get('at'))), 'pct': round(_f(r.get('pct')), 1), 'exit': r.get('exit'), 'cause': r.get('cause'),
                                         'class': r.get('lossClass'), 'desk': r.get('desk'), 'lesson': str(r.get('lesson') or '')[:110]}.items() if v is not None} for r in worst]}


def agent_events(events, tape, w):
    """The card's own agent moves (fills, swaps, pulls) + the decision tape rows inside the window, newest first, compact."""
    out = []
    for e in events or []:
        if w['from'] <= _f(e.get('at')) <= w['to'] and (e.get('kind') in ('agent', 'flow', 'rug', 'sl', 'seat') or 'agent' in str(e.get('why') or '')):
            out.append({'at': _hm(_f(e.get('at'))), 'kind': e.get('kind'), 'move': e.get('move'), 'coin': e.get('symbol'), 'why': str(e.get('why') or '')[:100]})
    for t in tape or []:
        if w['from'] <= _f(t.get('at')) <= w['to'] and t.get('agent') in ('reaper', 'devil', 'warden', 'courier', 'trigger', 'judge'):
            out.append({'at': _hm(_f(t.get('at'))), 'agent': t.get('agent'), 'action': t.get('action'), 'why': str(t.get('why') or '')[:100]})
    out.sort(key=lambda r: r.get('at') or '', reverse=True)
    return out[:KEEP_EVENTS]


def packet(question, w, positions=None, ledger=None, reviews=None, events=None, tape=None, tape_since=None, card=None):
    """→ (packet, data state). LIVE FEELESS = trades AND ledger in the window · PARTIAL = some sources answered · NO HISTORY = none."""
    ts = trades_in(positions, w)
    worst = sorted(ts, key=lambda p: _f(p.get('realPct')))[:KEEP_TRADES // 2]
    best = sorted(ts, key=lambda p: -_f(p.get('realPct')))[:KEEP_TRADES // 2]
    seen, pick = set(), []
    for p in worst + best:
        k = (p.get('mint'), p.get('closedAt'))
        if k not in seen:
            seen.add(k); pick.append(p)
    ex, jd, ev = execution(ledger, w, card), judge(reviews, w), agent_events(events, tape, w)
    gaps = []
    if not ts:
        gaps.append('no confirmed real exits in this window (archive positions)')
    if not ex:
        gaps.append('no keeper ledger rows in this window')
    if not jd:
        gaps.append("no Judge reviews in this window")
    if tape_since and _f(tape_since) > w['from']:
        gaps.append(f"the live decision tape only reaches back to {_hm(_f(tape_since))} (it is kept in memory and reset by the last restart)")
    pk = {'mode': 'general_analysis', 'question': str(question or '')[:300],
          'time_window': {'label': w['label'], 'from': _hm(w['from']), 'to': _hm(w['to'])},
          'summary': summary(ts), 'trades': [_trade_row(p) for p in pick], 'judge': jd, 'execution_events': ex, 'agent_events': ev, 'known_gaps': gaps}
    pk = {k: v for k, v in pk.items() if v not in (None, [], {})}
    state = 'LIVE FEELESS' if ts and ex else 'PARTIAL' if (ts or ex or jd or ev) else 'NO HISTORY'
    return pk, state


RULES = ("ANSWER FROM THE EVIDENCE PACKET ONLY (it is FEELESS's own records for the asked window). Name actual coins, times, exit rules, "
         "agents and numbers from it. Never invent a market selloff, hack, liquidation, news, dollar amount or agent behaviour that is not in it. "
         "If the packet does not hold what the question needs, say exactly what is missing (see known_gaps). Lead with the one biggest cause, "
         "then up to 3 supporting facts, then one concrete fix. Short.")


def shrink(pk, limit=3200):
    """Keep the packet under `limit` characters of JSON: drop agent events, then trades, then the judge's worst list, one row at a time."""
    import json
    p = dict(pk)
    for key in ('agent_events', 'trades', 'judge'):
        while len(json.dumps(p, separators=(',', ':'), default=str)) > limit:
            v = p.get(key)
            if isinstance(v, list) and v:
                p[key] = v[:-1] if len(v) > 1 else None
                if p[key] is None:
                    p.pop(key)
            elif isinstance(v, dict) and v.get('worst'):
                p[key] = {**v, 'worst': v['worst'][:-1]}
            else:
                break
    return p
