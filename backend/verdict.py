"""🧾 What's working, what's not — one verdict over every engine's OWN record (pure, tested).

Every row = one thing the system runs (a tier card, a strategy, a runner lane, an engine dial, a round length, a sim trait, a
real run) judged the same way from numbers it already recorded:
  • ✅ keep  — enough samples, average AND median above 0 (one freak run can't carry it)
  • ❌ scrap — enough samples, average AND median at or below 0
  • 👀 watch — too few samples yet, or average and median disagree
Nothing here trades or changes a setting; it only reads records and says which ones are paying for themselves.
"""
import math
import statistics


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def judge(n, avg, med, min_n):
    """→ (verdict, why) from a sample count, an average % and a median %."""
    n, avg, med = int(n or 0), _f(avg), _f(med)
    if n < min_n:
        return 'watch', f"needs {min_n - n} more to call"
    if avg > 0 and med > 0:
        return 'keep', f"average {avg:+.1f}% · typical {med:+.1f}% over {n}"
    if avg <= 0 and med <= 0:
        return 'scrap', f"average {avg:+.1f}% · typical {med:+.1f}% over {n}"
    return 'watch', f"mixed: average {avg:+.1f}% but typical {med:+.1f}% over {n}"


def _row(area, name, n, avg, med, min_n, extra=''):
    v, why = judge(n, avg, med, min_n)
    return {'area': area, 'name': name, 'n': int(n or 0), 'avgPct': round(_f(avg), 2), 'medPct': round(_f(med), 2), 'verdict': v,
            'why': why + (f" · {extra}" if extra else '')}


def _avg_med(pcts):
    p = [_f(x) for x in pcts or []]
    return (statistics.mean(p), statistics.median(p)) if p else (0.0, 0.0)


TRAIT_WORDS = {'clock': 'round length (min)', 'minDrop': 'rotate only coins down', 'confirm': 'losing rounds before a swap', 'hold': 'min hold (min)',
               'instant': 'instant swap at', 'shape': 'card shape', 'tp': 'take-profit', 'sl': 'stop', 'cycle': 'cycle', 'rideAt': 'freeze a runner at'}


def build(tiers=None, strategies=None, lanes=None, dials=None, sim_score=None, clocks=None, real=None):
    """tiers = {card: {label, pcts: [run %]}} · strategies = arena_board rows · lanes = lane_proofs · dials = {window: dial_proof} ·
    sim_score = pg_sim.learn (trait → value → {n, medPct, avgPct}) · clocks = pg_battle clockStats · real = run_report rows."""
    rows = []
    for card, t in (tiers or {}).items():
        a, m = _avg_med(t.get('pcts'))
        rows.append(_row('⭐ Tier card', t.get('label') or card, len(t.get('pcts') or []), a, m, 5, 'paper runs, start → end'))
    for s in strategies or []:
        rows.append(_row('🏟 Strategy', s.get('style'), s.get('runs'), s.get('avgPct'), s.get('medPct', s.get('avgPct')), 3, f"{s.get('winRate', 0)}% won"))
    for lane, p in (lanes or {}).items():
        rows.append(_row('🏃 Runner lane', lane, p.get('n'), p.get('avgPct'), p.get('avgPct'), 8, f"{p.get('winRate', 0)}% won"))
    for win, proof in (dials or {}).items():
        for dial, p in (proof or {}).items():
            rows.append(_row('🎚 Engine dial', f"{dial} · {win}", p.get('rounds'), p.get('avgPct'), p.get('avgPct'), 8, f"{p.get('winRate', 0)}% won"))
    for mins, c in (clocks or {}).items():
        rows.append(_row('⏱ Playground clock', f"{mins} min rounds", c.get('bells'), c.get('avgPct'), c.get('avgPct'), 3, 'battle bells, average card'))
    for trait, vals in (sim_score or {}).items():
        for val, s in (vals or {}).items():
            rows.append(_row('🧠 Sim config', f"{TRAIT_WORDS.get(trait, trait)} = {val}", s.get('n'), s.get('avgPct'), s.get('medPct'), 30,
                             f"{s.get('upPct', 0)}% of sim cards ended up"))
    for r in real or []:
        if r.get('pnlPct') is None:
            continue
        v, why = judge(1, r['pnlPct'], r['pnlPct'], 1)
        extra = f"fees {_f(r.get('feesPct')):.1f}% of money in · {_f(r.get('perHour')):.1f} swaps/h"
        if r.get('holdSolPct') is not None:
            extra += f" · SOL did {_f(r['holdSolPct']):+.1f}%"
        rows.append({'area': '💵 Real run', 'name': r.get('label') or r.get('card'), 'n': int(r.get('swaps') or 0), 'avgPct': round(_f(r['pnlPct']), 2),
                     'medPct': round(_f(r['pnlPct']), 2), 'verdict': v, 'why': f"{_f(r['pnlPct']):+.1f}% so far · {extra}"})
    order = {'scrap': 0, 'keep': 1, 'watch': 2}
    rows.sort(key=lambda r: (order[r['verdict']], -abs(r['avgPct'])))
    k = sum(1 for r in rows if r['verdict'] == 'keep'); s = sum(1 for r in rows if r['verdict'] == 'scrap'); w = len(rows) - k - s
    if not rows:
        head = 'No records yet — the engines need a few hours of rounds first.'
    elif not k:
        head = f"Nothing is proven to make money yet: {s} losing, {w} still unproven. Don't fund more until something turns ✅."
    else:
        best = max((r for r in rows if r['verdict'] == 'keep'), key=lambda r: r['medPct'])
        head = f"{k} working · {s} losing · {w} unproven. Strongest: {best['area']} {best['name']} ({best['why'].split(' over')[0]})."
    return {'rows': rows, 'keep': k, 'scrap': s, 'watch': w, 'headline': head}
