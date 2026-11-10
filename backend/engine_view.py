"""📡 AGT-12 THE ENGINE FOLDER (owner: "live data showing what each engine does for agents and the Collective"). Every engine that runs on its
own reports here, as counts only: the OSSY + G4 reviewer, the kit freshness pass, the shared reads (COL-9), the method kits (COL-10) and the
model routes of the last hour. No wallet, owner, prompt or page. Pure: the service passes in its state."""
import json

HOUR = 3600


def routes(lines, now, span=HOUR):
    """The call log's last `span` seconds, per route: calls, ok %, $ and average ms. → rows, busiest first."""
    by = {}
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if now - float(r.get('at') or 0) > span:
            continue
        k = str(r.get('route') or '?'); b = by.setdefault(k, {'route': k, 'calls': 0, 'ok': 0, 'usd': 0.0, 'ms': 0})
        b['calls'] += 1; b['ok'] += bool(r.get('ok')); b['usd'] += float(r.get('usd') or 0); b['ms'] += int(r.get('ms') or 0)
    return sorted(({**b, 'okPct': round(100 * b['ok'] / b['calls']), 'usd': round(b['usd'], 4), 'avgMs': round(b['ms'] / b['calls'])} for b in by.values()), key=lambda b: -b['calls'])


def reviewer(cats, version, lines, every_s, scope):
    """How far the reviewer got: proofs it graded at the current version, how many wait, pass rate, who really answered lately."""
    import mission
    done = due = passed = 0; last = 0.0
    for c in cats:
        if scope and c.get('handle') not in scope:
            continue
        for _k, (_c, key) in mission.KINDS.items():
            for f in c.get(key) or []:
                if f.get('status') != 'closed' or f.get('noTrade'):
                    continue
                rv = f.get('review') or {}
                if (rv.get('v') or 0) >= version:
                    done += 1; passed += rv.get('verdict') == 'pass'; last = max(last, float(rv.get('at') or 0))
                else:
                    due += 1
    who = {}
    for line in lines[-400:]:
        if '"ref":"review:' in line:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            k = f"{r.get('asked', '?').split('/')[-1].upper()} · {r.get('route')} · {r.get('model')}"; who[k] = who.get(k, 0) + 1
    return {'graded': done, 'waiting': due, 'passPct': round(100 * passed / done) if done else None, 'lastAt': last or None, 'everyS': every_s,
            'scope': list(scope) or ['every agent'], 'answered': [{'who': k, 'calls': n} for k, n in sorted(who.items(), key=lambda x: -x[1])][:4]}


def reads(shared, topics, fresh_s, now):
    """The shared reads alive now: per kind, how old, how often reused; plus topic reads (PoB)."""
    rows = [{'kind': k, 'ageMin': round((now - at) / 60), 'freshMin': round(fresh_s.get(k, 600) / 60), 'reused': n, 'sites': len(sites or [])}
            for k, (at, _line, sites, n) in shared.items() if now - at <= fresh_s.get(k, 600)]
    t_live = [t for t in topics.values() if now - t['at'] <= fresh_s.get('pob', 1800)]
    return {'kinds': sorted(rows, key=lambda r: r['kind']), 'topics': len(t_live), 'topicReuses': sum(t.get('reused', 0) for t in t_live)}


def methods(state):
    out = {'active': 0, 'unmeasured': 0, 'quarantined': 0}
    for r in (state or {}).values():
        out[r.get('state', 'unmeasured')] = out.get(r.get('state', 'unmeasured'), 0) + 1
    return {**out, 'kits': [{'kit': r['kit'], 'state': r.get('state'), 'followedWin': r.get('followedWin'), 'followedReview': r.get('followedReview')} for r in (state or {}).values()]}
