"""🧬 TRUE SUBSTITUTION (owner, 2026-10-12: "demotion is not enough — bad generation out, new generation in; lessons stay, bad habits go;
the role survives, the failed mind does not"). Pure + tested (`tests/test_generations.py`).

Every role always has exactly ONE generation in control:
  ACTIVE   controls live decisions                 SHADOW   the generation it replaced, judged on the same live cases (24h)
  BENCHED  pulled from live control (the owner)    RETIRED  archived for good (older lives, or a shadow whose 24h ended)
There is no "probation but still trading": when the Judge's REAL evidence (repeated losses pinned on that desk, net of its credited wins —
never one valid trade that lost) says a generation failed, it is replaced at once and the new one is ACTIVE on the same tick.

The next generation inherits ONLY the specific fix for HOW the last one failed (`improve`), applied to the hard-coded DEFAULTS — never the old
generation's tunables, accumulated vetoes or a pickier bar (a reborn Trigger used to start +0.5 pickier per death: that is inherited fear).
Every patch stays inside the tunable's bounds and makes the desk FASTER / more precise (earlier protection, quicker cut of a dead or
collapsing coin) — never slower or more restrictive about what may be bought.
"""
STATUSES = ('ACTIVE', 'SHADOW', 'BENCHED', 'RETIRED')
SHADOW_SEC = 24 * 3600.0
SHADOW_MIN_N = 5              # real closed positions after the switch before the shadow record says anything

# failure cause (judge_review `cause` / `lossClass`) → what the next generation changes, per office desk: (tunable, new value, words)
CAUSE_PATCH = {
    'reaper': {
        'gave_back':    [('protectAt', 4.0, 'arms its trail at +4% instead of +6% (gave back gains)'), ('giveBackPct', 35.0, 'banks after giving back 35% of a peak (was 50%)')],
        'BAD EXIT':     [('protectAt', 4.0, 'arms its trail at +4% (exits came too late)'), ('giveBackPct', 35.0, 'tighter give-back: 35%')],
        'held_too_long': [('timeMaxMin', 60.0, 'a coin with no read left goes after 60 min, not 120 (held losers too long)'), ('stopPct', 20.0, 'stop ceiling 20% (was 30%)')],
        'BAD HOLD':     [('timeMaxMin', 60.0, 'quicker on dead positions: 60 min'), ('stopPct', 20.0, 'stop ceiling 20%')],
        'rugged':       [('stopPct', 20.0, 'cuts a collapsing coin sooner: stop ceiling 20%')],
        'thin_pool':    [('stopPct', 20.0, 'cuts a thinning pool sooner: stop ceiling 20%')],
        'bundled_exit': [('stopPct', 20.0, 'cuts when the bundle exits: stop ceiling 20%')],
    },
    'warden': {
        'thin_pool':    [('poolSharePct', 0.75, 'takes at most 0.75% of a pool (was 1%)')],
        'BAD SIZE':     [('maxSeatPct', 30.0, 'one new seat ≤ 30% of the card (was 40%)')],
    },
}


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def improve(agent, causes, tunable):
    """→ (tune patch {key: value}, [what changed]) for the NEXT generation of an office desk, from the causes of the losses pinned on the one
    that failed (most common first). Starts from DEFAULTS (the caller drops the old tunes); each value clamped to its bounds."""
    patch, words = {}, []
    for c in causes or []:
        for key, val, w in (CAUSE_PATCH.get(agent) or {}).get(str(c), []):
            if key in patch or key not in (tunable.get(agent) or {}):
                continue
            _d, lo, hi, _ = tunable[agent][key]
            patch[key] = max(lo, min(hi, val)); words.append(w)
    return patch, (words or ['clean defaults — no specific failure pattern to fix'])


def failure_causes(reviews, agent, born):
    """The causes of the real losses pinned on `agent` since `born`, most common first."""
    import collections
    c = collections.Counter()
    for r in reviews or []:
        if r.get('kind') == 'loss' and _f(r.get('at')) >= _f(born) and _f((r.get('resp') or {}).get(agent)) > 0:
            for k in (r.get('cause'), r.get('lossClass')):
                if k:
                    c[str(k)] += 1
    return [k for k, _ in c.most_common()]


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


def lifecycle(four, office, now, shadows=None):
    """→ {role: {active: {gen, since, status, watch}, past: [{gen, status, why, changed, edge, shadow}]}} for the ten roles. ACTIVE is always
    the current generation; the one it replaced is SHADOW for SHADOW_SEC, then RETIRED; the owner's bench (office['benched']) shows BENCHED."""
    out = {}
    four, office, shadows = four or {}, office or {}, shadows or {}
    roles = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge')
    benched = set(office.get('benched') or [])
    for a in roles:
        src = four if a in ('tally', 'sherlock', 'trigger', 'devil') else office
        gen = int((src.get('gen') or {}).get(a) or 1)
        since = _f((src.get('born') or {}).get(a))
        lin = [x for x in src.get('lineage') or [] if x.get('agent') == a]
        past = []
        for x in reversed(lin):
            died = _f(x.get('died') or x.get('at'))
            st = 'SHADOW' if x is lin[-1] and now - died < SHADOW_SEC else 'RETIRED'
            past.append({'gen': x.get('gen'), 'status': st, 'at': died, 'why': x.get('why'), 'changed': x.get('changed') or x.get('lesson'),
                         'shadow': shadows.get(a) if st == 'SHADOW' else None})
        out[a] = {'active': {'gen': gen, 'since': since or None, 'status': 'BENCHED' if a in benched else 'ACTIVE'}, 'past': past[:6]}
    return out
