"""🏦 PoEco LIVE BOOKS — the owner's real business, filled in by itself (owner 2026-11-12: "give this dude what he really asked for").

No typing, no bank paste, no sample rows: every number comes from a store FEELESS already writes —
  IN    fees users paid FEELESS        (fee_ledger.json: feeUsd per trade, minus FeeBack paid out)
  OUT   rented model spend             (mind_calls.jsonl: usd per call, which model, which job)
  CARD  the real Fuse card             (real_audit.json from scripts/real-audit.py: put in, open positions, last-7-day net)
→ KPIs, 30 daily buckets (in / out / net), spend by model and by job, and a plain verdict. Pure: the route reads, this sums.
"""
import json
import time

DAY = 86400


def _f(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _day(t):
    return time.strftime('%m-%d', time.localtime(t))


def build(ledger, calls, audit, feeback_paid, now=None, days=30):
    now = now or time.time()
    start = now - days * DAY
    buckets = {}
    for i in range(days):
        t = start + (i + 1) * DAY
        buckets[_day(t)] = {'d': _day(t), 'in': 0.0, 'out': 0.0}
    fee_all = fee_7 = 0.0; trades = 0; payers = 0
    for rows in (ledger or {}).values():
        if rows:
            payers += 1
        for r in rows or []:
            usd = _f(r.get('feeUsd')); t = _f(r.get('t') or r.get('at'))
            fee_all += usd; trades += 1
            if t >= now - 7 * DAY:
                fee_7 += usd
            if t >= start and _day(t) in buckets:
                buckets[_day(t)]['in'] += usd
    spend_all = spend_7 = 0.0; by_model = {}; by_job = {}; n_calls = 0
    for c in calls or []:
        usd = _f(c.get('usd')); t = _f(c.get('at'))
        n_calls += 1; spend_all += usd
        if t >= now - 7 * DAY:
            spend_7 += usd
        if t >= start and _day(t) in buckets:
            buckets[_day(t)]['out'] += usd
        if usd:
            m = str(c.get('model') or c.get('asked') or '?').split('/')[-1][:32]
            by_model[m] = by_model.get(m, 0.0) + usd
            j = str(c.get('kind') or '?')[:16]
            by_job[j] = by_job.get(j, 0.0) + usd
    back = sum(_f(v) for v in (feeback_paid or {}).values())
    a = audit or {}
    w7 = ((a.get('windows') or {}).get('7d') or {}).get('all') or {}
    card = {'putInUsd': round(_f(a.get('putInUsd')), 2), 'openCostUsd': round(sum(_f(o.get('costUsd')) for o in a.get('open') or []), 2),
            'open': len(a.get('open') or []), 'net7dUsd': round(_f(w7.get('netUsd')), 3), 'trips7d': int(w7.get('n') or 0),
            'verdict': a.get('verdict') if isinstance(a.get('verdict'), str) else (a.get('verdict') or {}).get('say') if isinstance(a.get('verdict'), dict) else None,
            'asOf': round(_f(a.get('at'))) or None} if a else None
    net_all = fee_all - back - spend_all
    net_7 = fee_7 - spend_7 + (card['net7dUsd'] if card else 0)
    daily = [{**b, 'in': round(b['in'], 4), 'out': round(b['out'], 4), 'net': round(b['in'] - b['out'], 4)} for b in buckets.values()]
    run = 0.0
    for b in daily:
        run += b['net']; b['cum'] = round(run, 4)
    burn = spend_7 / 7
    top = lambda d: [{'k': k, 'usd': round(v, 4)} for k, v in sorted(d.items(), key=lambda x: -x[1])[:6]]   # noqa: E731
    if fee_all - back >= spend_all and fee_all > 0:
        say = 'Fees pay for the models: the business covers its own brains.'
    elif fee_all > 0:
        say = f'Models cost {spend_all / max(fee_all - back, 1e-9):.1f}× what fees bring in. More volume or cheaper minds closes it.'
    else:
        say = 'No fee income yet: every model call is paid from your pocket.'
    return {'at': round(now), 'kpi': {'feesUsd': round(fee_all, 4), 'fees7dUsd': round(fee_7, 4), 'feeBackPaidUsd': round(back, 4), 'trades': trades,
                                     'payers': payers, 'spendUsd': round(spend_all, 4), 'spend7dUsd': round(spend_7, 4), 'calls': n_calls,
                                     'netUsd': round(net_all, 4), 'net7dUsd': round(net_7, 4), 'burnPerDayUsd': round(burn, 4),
                                     'perCallUsd': round(spend_all / n_calls, 4) if n_calls else 0},
            'daily': daily, 'byModel': top(by_model), 'byJob': top(by_job), 'card': card, 'say': say}


def read(paths):
    """paths: {'ledger', 'calls', 'audit', 'feeback'} → the inputs for build(), each tolerant of a missing or broken file."""
    def j(p, d):
        try:
            return json.loads(p.read_text())
        except (OSError, ValueError):
            return d
    calls = []
    try:
        for ln in paths['calls'].read_text(errors='ignore').splitlines()[-20000:]:
            try:
                calls.append(json.loads(ln))
            except ValueError:
                pass
    except OSError:
        pass
    return j(paths['ledger'], {}), calls, j(paths['audit'], None), j(paths['feeback'], {})
