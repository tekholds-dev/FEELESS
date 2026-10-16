"""🧬 The SHADOW record of a replaced generation (Reaper's price rules replayed with the old and the new lesson on the same real exits).

The lifecycle itself — ONE book, ONE rule for all ten roles — lives in trench_kernel/lifecycle.py; `improve` is used from it here. Pure + tested (`tests/test_generations.py`).
"""
from trench_kernel.lifecycle import improve as _improve

SHADOW_MIN_N = 5              # real closed positions after the switch before the shadow record says anything


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def improve(agent, causes, tunable, prev=None, wins=0):
    """→ (lesson patch, [what changed]) for the NEXT generation (trench_kernel.lifecycle.improve): the fix for how it failed + what a
    WINNING generation earned (`prev` lesson, `wins` credited real wins)."""
    return _improve(agent, causes, tunable, prev=prev, wins=wins)


def shadow_record(positions, old_p, new_p, since, take, replay):
    """OLD generation vs NEW generation on the SAME real positions closed after the switch: Reaper's price rules replayed on each recorded
    path with each generation's settings. → {n, old, new, edge, verdict} (None under SHADOW_MIN_N)."""
    ps = [p for p in positions or [] if _f(p.get('closedAt')) >= _f(since) and p.get('path')]
    if len(ps) < SHADOW_MIN_N:
        return {'n': len(ps), 'verdict': f'{len(ps)} of {SHADOW_MIN_N} real exits since the switch — too early to compare'}
    o = [replay(p['path'], old_p, take) for p in ps]
    n_ = [replay(p['path'], new_p, take) for p in ps]
    oa, na = sum(o) / len(o), sum(n_) / len(n_)
    edge = round(na - oa, 2)
    return {'n': len(ps), 'old': round(oa, 2), 'new': round(na, 2), 'edge': edge,
            'verdict': 'new generation better' if edge > 0.5 else 'old generation was better — the Judge may evolve again' if edge < -0.5 else 'no clear difference yet'}
