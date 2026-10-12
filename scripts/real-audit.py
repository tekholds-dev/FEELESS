#!/usr/bin/env python3
"""🧾 EMERGENCY EDGE AUDIT — every real round trip rebuilt from the keeper's LEDGER (never a UI summary), attributed, costed, and
stress-tested. Read-only: prints a report and writes backend/data/real_audit.json. Prints no keys, RPC URLs or wallet ids.

  backend/.venv/bin/python scripts/real-audit.py [card]

A round trip = the first filled buy of a coin on a card → filled sells / write-off until the units are gone. Money:
  cost      = $ the buys sent to the pool        proceeds = $ the sells returned (a write-off returns $0)
  fees      = network + priority fees on every leg (ledger feeUsd)
  slippage  = buys: (fill − mid) × units · sells: (mid − fill) × units   (mid = the market price the keeper saw at send)
  NET $     = proceeds − cost − fees            GROSS = proceeds − cost
MAE / MFE / entry facts come from the agents' archive when the trip was theirs (Reaper's own path record).
"""
import json
import random
import statistics as st
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
import store  # noqa: E402

DATA = ROOT / 'backend' / 'data'
SOL = 'So11111111111111111111111111111111111111112'
WINDOWS = (('24h', 24), ('48h', 48), ('7d', 168))
AGE_B = (('0-5m', 5 / 60), ('5-15m', .25), ('15-60m', 1), ('1-3h', 3), ('3-6h', 6), ('6-12h', 12), ('12h+', 1e9))
SRC_MAP = (('pulse', 'Pump pulse'), ('migr', 'migration'), ('list:pump', 'Pump live'), ('list:ptrend', 'trending'), ('list:volume', 'volume'),
           ('list:movers', 'movers'), ('list:live', 'movers'), ('list:calls', 'callout'), ('calls', 'callout'), ('list:procall', 'callout'),
           ('open', 'Pump radar'), ('runner', 'runner board'), ('feeders', 'fed runners'))


def f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def sol_price():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:5099/api/candles/prices?mints={SOL}', timeout=6) as r:
            return f(json.loads(r.read()).get(SOL)) or None
    except Exception:
        return None


def trips(rows, card):
    """FIFO-free round trips per coin: a trip opens on a buy with no units held and closes when ≤ 2% of the bought units remain."""
    open_, out = {}, []
    for r in sorted((r for r in rows if r.get('card') == card), key=lambda r: f(r.get('at'))):
        side, st_, m = r.get('side'), r.get('status'), r.get('mint')
        if not m:
            continue
        if side == 'buy' and st_ == 'filled':
            t = open_.setdefault(m, {'mint': m, 'sym': r.get('symbol'), 'open': f(r['at']), 'cost': 0.0, 'proc': 0.0, 'fees': 0.0, 'slip': 0.0,
                                     'bought': 0.0, 'sold': 0.0, 'buys': 0, 'sells': 0, 'whyIn': r.get('why'), 'writeoff': False, 'sellBack': r.get('sellBackPct')})
            u = f(r.get('units')); t['cost'] += f(r.get('usd')); t['fees'] += f(r.get('feeUsd')); t['bought'] += u; t['buys'] += 1
            if f(r.get('midPx')) > 0 and f(r.get('px')) > 0:
                t['slip'] += (f(r['px']) - f(r['midPx'])) * u
        elif side in ('sell', 'writeoff') and m in open_ and st_ in ('filled', 'done'):
            t = open_[m]
            u = f(r.get('units')) or (f(r.get('atoms')) / 10 ** int(r.get('decimals') or 0) if r.get('atoms') else 0.0)
            if side == 'writeoff':
                t['writeoff'] = True; u = max(u, t['bought'] - t['sold'])
            else:
                t['proc'] += f(r.get('usd')); t['fees'] += f(r.get('feeUsd')); t['sells'] += 1
                if f(r.get('midPx')) > 0 and f(r.get('px')) > 0:
                    t['slip'] += (f(r['midPx']) - f(r['px'])) * u
            t['sold'] += u; t['close'] = f(r['at']); t['whyOut'] = r.get('why')
            if t['bought'] > 0 and t['sold'] >= t['bought'] * 0.98:
                out.append(open_.pop(m))
    for t in out:
        t['gross'] = t['proc'] - t['cost']; t['net'] = t['gross'] - t['fees']
        t['netPct'] = t['net'] / t['cost'] * 100 if t['cost'] > 0 else 0.0
        t['grossPct'] = t['gross'] / t['cost'] * 100 if t['cost'] > 0 else 0.0
        t['holdS'] = t['close'] - t['open']
    return out, list(open_.values())


def attach(ts, archive, reg):
    """Agent facts from the archive (the closest position of that coin opened inside the trip) + first-seen source from the intake registry."""
    by = defaultdict(list)
    for p in archive.get('positions') or []:
        by[p.get('mint')].append(p)
    for t in ts:
        ps = [p for p in by.get(t['mint']) or [] if t['open'] - 120 <= f(p.get('since')) <= t['close'] + 60]
        p = min(ps, key=lambda p: abs(f(p.get('since')) - t['open'])) if ps else None
        t['agent'] = bool(p) or '🤖' in str(t.get('whyIn') or '')
        if p:
            th, li, la = p.get('thesis') or {}, p.get('li') or {}, p.get('launch') or {}
            t.update(tag=p.get('tag'), exitRule=p.get('rule'), struct=th.get('structure'), rule=(th.get('triggerRule') or '').split(' ')[0] or None,
                     mfe=f(p.get('peak')), mae=f(p.get('low')), ageH=la.get('ageH') if la.get('ageH') is not None else li.get('ageH'),
                     mcap=li.get('mcap'), phase=li.get('phase'))
        e = (reg.get('reg') or {}).get(t['mint']) or {}
        src = e.get('src') or {}
        first = min(src.items(), key=lambda kv: f(kv[1]))[0] if src else None
        t['source'] = next((w for k, w in SRC_MAP if first and (first == k or first.startswith(k))), first or 'other') if first else 'other'
        t['door'] = door(t.get('tag'))
        t['exit'] = exit_kind(t)
    return ts


def door(tag):
    s = str(tag or '')
    for w, k in (('A-tier', 'A'), ('B-tier', 'B'), ('C-tier', 'C'), ('best available', 'best available'), ('floor', 'seat floor'),
                 ('last resort', 'seat floor'), ('duty', 'duty'), ('GO', 'GO')):
        if w in s:
            return k
    return 'engine / owner' if not s else 'other'


def exit_kind(t):
    r = str(t.get('exitRule') or '') + ' ' + str(t.get('whyOut') or '')
    if t.get('writeoff') or any(k in r for k in ('R1 ', 'R2 ', 'R4r', 'R4e', 'rug', 'drain')):
        return 'rug / liquidity'
    for k, w in (('R5x', 'stop'), ('R5t', 'Reaper breakdown'), ('R5', 'stop'), ('R7b', 'Reaper breakdown'), ('R7s', 'Reaper breakdown'),
                 ('R7', 'trail'), ('R6', 'take'), ('R9', 'time'), ('R11', 'time'), ('R8', 'switch / momentum'), ('R4', 'Reaper breakdown')):
        if k in r:
            return w
    return 'other' if not t.get('exitRule') else t['exitRule'].split(' ')[0]


def age_band(h):
    if h is None:
        return 'age ?'
    return next(n for n, cap in AGE_B if f(h) < cap)


def summary(ts):
    if not ts:
        return None
    net = [t['net'] for t in ts]; pct = [t['netPct'] for t in ts]
    win, loss = sum(x for x in net if x > 0), -sum(x for x in net if x < 0)
    return {'n': len(ts), 'netUsd': round(sum(net), 4), 'grossUsd': round(sum(t['gross'] for t in ts), 4), 'feesUsd': round(sum(t['fees'] for t in ts), 4),
            'slipUsd': round(sum(t['slip'] for t in ts), 4), 'medNetPct': round(st.median(pct), 2), 'avgNetPct': round(sum(pct) / len(pct), 2),
            'won': round(sum(1 for x in net if x > 0) / len(net) * 100), 'pf': round(win / loss, 2) if loss else None,
            'medGrossPct': round(st.median([t['grossPct'] for t in ts]), 2), 'maxDD': round(max_dd(net), 4)}


def max_dd(seq):
    eq = peak = dd = 0.0
    for x in seq:
        eq += x; peak = max(peak, eq); dd = min(dd, eq - peak)
    return dd


def monte_carlo(ts, n=2000, seed=7):
    """Shuffled order → drawdown distribution; bootstrap of the mean net % → share of resamples above 0."""
    if len(ts) < 10:
        return None
    rnd = random.Random(seed); net = [t['net'] for t in ts]; pct = [t['netPct'] for t in ts]
    dds = sorted(max_dd(rnd.sample(net, len(net))) for _ in range(n))
    means = [sum(rnd.choice(pct) for _ in pct) / len(pct) for _ in range(n)]
    top = sorted(net, reverse=True)
    return {'ddMedianUsd': round(dds[n // 2], 4), 'ddWorst5pctUsd': round(dds[int(n * 0.05)], 4),
            'meanPositiveShare': round(sum(1 for m in means if m > 0) / n * 100, 1),
            'top3ShareOfProfit': round(sum(top[:3]) / sum(x for x in net if x > 0) * 100, 1) if any(x > 0 for x in net) else None}


def cause(t):
    """One primary reason per LOSING trip (net < 0), from what is on record."""
    r = str(t.get('exitRule') or '')
    if t['exit'] == 'rug / liquidity':
        return 'rug / liquidity'
    if t.get('churn'):
        return 'rebuy / churn'
    if t['gross'] >= 0:
        return 'execution cost'
    if t.get('rule') in ('E2', 'E3') or t.get('struct') == 'PARABOLIC':
        return 'late entry'
    if t.get('mfe') is not None and f(t.get('mfe')) >= 5:
        return 'bad exit (was up ≥ 5%)'
    if t.get('mfe') is not None and f(t.get('mfe')) < 2:
        return 'bad selection (never went up)'
    return 'other' if not r else 'other'


def group(ts, key):
    g = defaultdict(list)
    for t in ts:
        g[key(t)].append(t)
    return {k: summary(v) for k, v in sorted(g.items(), key=lambda kv: sum(t['net'] for t in kv[1]))}


def feats(t):
    """Only what was observable at the buy."""
    return [f"age:{age_band(t.get('ageH'))}", f"door:{t['door']}", f"rule:{t.get('rule') or '-'}", f"struct:{t.get('struct') or '-'}",
            f"src:{t['source']}", f"phase:{t.get('phase') or '-'}", f"cap:{'<50K' if f(t.get('mcap')) < 5e4 else '<200K' if f(t.get('mcap')) < 2e5 else '200K+'}" if t.get('mcap') else 'cap:?']


def walk_forward(ts, folds=5, min_n=8):
    """Rolling: each fold learns 'take only buckets whose median NET was > 0 on ≥ min_n past trades' from everything BEFORE it and is
    judged on the fold itself. → per-fold + pooled unseen result of the trades the rule would have taken vs all trades."""
    ts = sorted(ts, key=lambda t: t['open'])
    if len(ts) < 40:
        return None
    size = len(ts) // (folds + 1)
    took, every, rows = [], [], []
    for k in range(1, folds + 1):
        train, test = ts[:k * size], ts[k * size:(k + 1) * size]
        cells = defaultdict(list)
        for t in train:
            for x in feats(t):
                cells[x].append(t['netPct'])
        good = {x for x, v in cells.items() if len(v) >= min_n and st.median(v) > 0}
        tk = [t for t in test if any(x in good for x in feats(t))]
        took += tk; every += test
        rows.append({'fold': k, 'rules': sorted(good), 'taken': len(tk), 'of': len(test),
                     'takenAvg': round(sum(t['netPct'] for t in tk) / len(tk), 2) if tk else None, 'allAvg': round(sum(t['netPct'] for t in test) / len(test), 2)})
    return {'folds': rows, 'taken': summary(took), 'all': summary(every)}


def main():
    card = sys.argv[1] if len(sys.argv) > 1 else 'degen'
    path = DATA / 'fuse_wallet.json'
    d = store.KV(path).get({}) or {}
    rows = store.Ledger(path).rows(limit=200000) or d.get('ledger') or []
    archive = json.loads((DATA / 'agent_archive.json').read_text()) if (DATA / 'agent_archive.json').exists() else {}
    reg = json.loads((DATA / 'intake_registry.json').read_text()) if (DATA / 'intake_registry.json').exists() else {}
    sol = sol_price()
    now = time.time()
    all_t, still = trips(rows, card)
    all_t = attach(all_t, archive, reg)
    last_sell = {}
    for t in sorted(all_t, key=lambda t: t['open']):   # 🔁 a coin bought again ≤ 2 min after the last trip on it closed
        t['churn'] = t['open'] - last_sell.get(t['mint'], -1e18) <= 120
        last_sell[t['mint']] = t['close']
    book = (d.get('books') or {}).get(card) or {}
    out = {'at': now, 'card': card, 'solUsd': sol, 'putInUsd': book.get('fundedUsd'), 'open': [{'sym': t['sym'], 'costUsd': round(t['cost'], 4)} for t in still], 'windows': {}}
    print(f"EDGE AUDIT · card {card} · SOL {'$%.2f' % sol if sol else 'unknown'} · ledger rows {len(rows)} · round trips {len(all_t)}")
    print(f"put in ${f(book.get('fundedUsd')):.2f} (book)")
    for name, hrs in WINDOWS:
        ts = [t for t in all_t if t['close'] >= now - hrs * 3600]
        if not ts:
            continue
        ag = [t for t in ts if t['agent']]
        hrs_live = max(1e-9, min(hrs, (now - min(t['open'] for t in ts)) / 3600))
        s = summary(ts)
        avg_pos = sum(t['cost'] for t in ts) / len(ts)
        cost_pct = (s['feesUsd'] + max(0.0, s['slipUsd'])) / max(1e-9, sum(t['cost'] for t in ts)) * 100
        churn = {'tradesPerHour': round(len(ts) / hrs_live, 2), 'swapsPerHour': round(sum(t['buys'] + t['sells'] for t in ts) / hrs_live, 2),
                 'medianHoldMin': round(st.median([t['holdS'] for t in ts]) / 60, 1), 'avgPositionUsd': round(avg_pos, 4),
                 'turnoverUsd': round(sum(t['cost'] for t in ts), 2), 'costPctPerTrip': round(cost_pct, 2),
                 'minGrossEdgePct': round(cost_pct, 2)}
        losers = [t for t in ts if t['net'] < 0]
        causes = defaultdict(float)
        for t in losers:
            causes[cause(t)] += -t['net']
        tot = sum(causes.values()) or 1
        w = {'all': s, 'agents': summary(ag), 'churn': churn, 'mc': monte_carlo(ts),
             'bySource': group(ag or ts, lambda t: t['source']), 'byAge': group(ag or ts, lambda t: age_band(t.get('ageH'))),
             'byEntry': group(ag or ts, lambda t: t['door']), 'byRule': group(ag or ts, lambda t: t.get('rule') or '—'),
             'byExit': group(ag or ts, lambda t: t['exit']), 'byStruct': group(ag or ts, lambda t: t.get('struct') or '—'),
             'bestAvailable': summary([t for t in ag if t['door'] in ('best available', 'seat floor')]),
             'lossCauses': {k: round(v / tot * 100, 1) for k, v in sorted(causes.items(), key=lambda kv: -kv[1])},
             'churnBugTrips': sum(1 for t in ts if t.get('churn'))}
        out['windows'][name] = w
        print(f"\n== {name} ==  trips {s['n']} (agents {len(ag)}) · NET ${s['netUsd']:+.2f} · gross ${s['grossUsd']:+.2f} · fees ${s['feesUsd']:.2f} · slippage ${s['slipUsd']:.2f}")
        print(f"   median net {s['medNetPct']:+.1f}% · avg {s['avgNetPct']:+.1f}% · won {s['won']}% · profit factor {s['pf']} · max DD ${s['maxDD']:.2f}")
        print(f"   churn: {churn['tradesPerHour']} trips/h · {churn['swapsPerHour']} swaps/h · median hold {churn['medianHoldMin']} min · avg position ${avg_pos:.3f} · turnover ${churn['turnoverUsd']}")
        print(f"   EXECUTION COST ≈ {cost_pct:.1f}% of every trip (fees + slippage) → a trade must make ≥ {cost_pct:.1f}% GROSS just to break even")
        if w['mc']:
            print(f"   Monte Carlo: DD median ${w['mc']['ddMedianUsd']:.2f} · worst 5% ${w['mc']['ddWorst5pctUsd']:.2f} · resampled mean > 0 in {w['mc']['meanPositiveShare']}% · top-3 trips = {w['mc']['top3ShareOfProfit']}% of all profit")
        ba = w['bestAvailable']
        if ba:
            print(f"   BEST AVAILABLE / seat floor: n {ba['n']} · won {ba['won']}% · median gross {ba['medGrossPct']:+.1f}% · median net {ba['medNetPct']:+.1f}% · total ${ba['netUsd']:+.2f} · DD ${ba['maxDD']:.2f}")
        print('   loss causes (% of $ lost): ' + ' · '.join(f'{k} {v}%' for k, v in w['lossCauses'].items()))
        for title, key in (('source', 'bySource'), ('age', 'byAge'), ('entry door', 'byEntry'), ('entry rule', 'byRule'), ('exit', 'byExit')):
            print(f'   by {title}: ' + ' · '.join(f"{k} n{v['n']} ${v['netUsd']:+.2f} ({v['medNetPct']:+.0f}%)" for k, v in w[key].items() if v))
    ag7 = [t for t in all_t if t['agent']]
    wf = walk_forward(ag7)
    out['walkForward'] = wf
    print('\n== OUT-OF-SAMPLE (rolling walk-forward on the agents\' real trips, NET after costs) ==')
    if not wf:
        print('   fewer than 40 agent trips — nothing to judge')
    else:
        for r in wf['folds']:
            print(f"   fold {r['fold']}: rules learned before it: {', '.join(r['rules']) or 'none'} → took {r['taken']}/{r['of']} at {r['takenAvg']}% avg (all {r['allAvg']}%)")
        tk = wf['taken']
        print(f"   POOLED UNSEEN: taken {tk['n'] if tk else 0} trips · avg {tk['avgNetPct'] if tk else '—'}% · median {tk['medNetPct'] if tk else '—'}% · PF {tk['pf'] if tk else '—'}  vs all {wf['all']['avgNetPct']}%")
        verdict = 'NO PROVEN EDGE' if not tk or tk['n'] < 30 or tk['avgNetPct'] <= 0 or (tk['pf'] or 0) <= 1 else 'a candidate rule (needs forward paper proof)'
        out['verdict'] = verdict
        print(f"   VERDICT: {verdict}")
    (DATA / 'real_audit.json').write_text(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
