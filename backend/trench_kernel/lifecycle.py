"""🧬 ONE LIFECYCLE FOR ALL TEN ROLES (kernel finalize, 2026-10-12). Pure + tested (tests/test_kernel_lifecycle.py).

There used to be three engines: the four desks' paper survival (`survival / evolve` + the team's nine lives), the office desks'
`office.demote`, and a reader that stitched the two books together. Now there is ONE book and ONE rule:

  book = {'roles': {role: {gen, bornAt, status, lesson, decisions, wins, losses, net, netImpact, lastEval, lastWhy}}, 'lineage': [...]}

  ACTIVE     the generation that controls its role's live parameters
  PROBATION  the same generation, still the only one in control, with the Judge's real evidence against it building (shown, not hidden)
  SHADOW     the generation that was replaced — 24h on the record beside its successor, NO live authority
  RETIRED    archived for good

Evidence = REAL money only: the Judge's reviews of confirmed exits since the generation was born. `losses` = losses the Judge pinned on
the role (responsibility ≥ PIN), `wins` = wins credited to it, `net = losses − wins`. net ≥ PROBATION_N → PROBATION; net ≥ REPLACE_N → the
generation is replaced on that evaluation: the next one starts from the hard-coded DEFAULTS plus only the fix for HOW the last one failed
(`CAUSE_PATCH`, every value inside its bounds), the old one becomes SHADOW. Paper calls, lives and streaks decide nothing here.

`lessons(book)` is the ONLY door a generation's parameters reach live code through, and it returns the ACTIVE / PROBATION generation of
each role — a SHADOW or RETIRED generation cannot be read by the brain or the office at all (tested).
"""
import collections

ROLES = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge')
STATUSES = ('ACTIVE', 'PROBATION', 'SHADOW', 'RETIRED')
LIVE = ('ACTIVE', 'PROBATION')
PIN = 50.0            # responsibility the Judge must put on a role for a loss to count against it
PROBATION_N = 2
REPLACE_N = 3
MIN_LIFE_SEC = 3600.0  # a generation born under an hour ago is not replaced yet (it has not had its chance)
SHADOW_SEC = 24 * 3600.0
LINEAGE_KEEP = 80
ENTRY_ROLES = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden')   # every real entry passed through each of these
INTEGRITY_ROLES = ('courier', 'archivist', 'judge')                             # judged on integrity failures, never on a trade's result
OFFICE_ROLES = ('weather', 'warden', 'courier', 'reaper')                       # their lesson vector = their office tunables
REAPER_TAKES = ('R6', 'R7')                                                     # Reaper's own profit exits

# The brain-side parameters a generation may carry: (default, low, high, what it is). The office desks' parameters live in office.TUNABLE
# (handed in as `tunable`); together they are every role's LESSON VECTOR. A role with no parameters still has a generation and a record.
KERNEL_TUNABLE = {
    'sherlock': {'walletTrust': (1.0, 1.0, 2.0, 'how hard early-wallet evidence moves a rank (1 = the base +8% … −15%)')},
    'trigger': {'lateMove': (0.0, 0.0, 60.0, 'a coin already up this much in 5 min is ARMED, not entered (0 = off)')},
    'devil': {'strong': (0.85, 0.75, 0.9, 'rank × for each strong warning')},
}
# failure cause (the Judge's `cause` / `lossClass`) → what the NEXT generation changes: (key, value, words). Faster / more precise, bounded.
CAUSE_PATCH = {
    'trigger': {'collapsing_entry': [('lateMove', 25.0, 'arms a coin already +25% in 5 min instead of entering its top')],
                'crowd_fomo': [('lateMove', 25.0, 'arms a coin already +25% in 5 min (it bought the crowd\'s top)')],
                'BAD TIMING': [('lateMove', 25.0, 'arms a coin already +25% in 5 min')]},
    'devil': {'rugged': [('strong', 0.8, 'a strong warning now costs 20% of a rank (was 15%)')],
              'after_distribution': [('strong', 0.8, 'a strong warning now costs 20% of a rank')],
              'weak_holders': [('strong', 0.8, 'a strong warning now costs 20% of a rank')]},
    'sherlock': {'too_old': [('walletTrust', 1.5, 'weighs early-wallet evidence 1.5× (it leaned on stale coins)')],
                 'collapsing_entry': [('walletTrust', 1.5, 'weighs early-wallet evidence 1.5×')]},
    'reaper': {'gave_back': [('protectAt', 4.0, 'arms its trail at +4% instead of +6% (gave back gains)'), ('giveBackPct', 35.0, 'banks after giving back 35% of a peak (was 50%)')],
               'BAD EXIT': [('protectAt', 4.0, 'arms its trail at +4% (exits came too late)'), ('giveBackPct', 35.0, 'tighter give-back: 35%')],
               'held_too_long': [('timeMaxMin', 60.0, 'a coin with no read left goes after 60 min, not 120'), ('stopPct', 20.0, 'stop ceiling 20% (was 30%)')],
               'BAD HOLD': [('timeMaxMin', 60.0, 'quicker on dead positions: 60 min'), ('stopPct', 20.0, 'stop ceiling 20%')],
               'rugged': [('stopPct', 20.0, 'cuts a collapsing coin sooner: stop ceiling 20%')],
               'thin_pool': [('stopPct', 20.0, 'cuts a thinning pool sooner: stop ceiling 20%')],
               'bundled_exit': [('stopPct', 20.0, 'cuts when the bundle exits: stop ceiling 20%')]},
    'warden': {'thin_pool': [('poolSharePct', 0.75, 'takes at most 0.75% of a pool (was 1%)')],
               'bundled_exit': [('maxSeatPct', 30.0, 'one new seat ≤ 30% of the card (was 40%)')],
               'BAD SIZE': [('maxSeatPct', 30.0, 'one new seat ≤ 30% of the card (was 40%)')]},
}


from fnum import nan_safe as _f


def _bounds(tunable):
    return {**{r: dict(v) for r, v in (tunable or {}).items()}, **KERNEL_TUNABLE}


def new_book(now, four=None, office=None):
    """A fresh book — or, once, the migration of the two old books (the four desks' gen / born / lineage in the paper desk's state, the
    office desks' in the office state + its promoted tunables) into the one. Every role starts ACTIVE."""
    four, office = four or {}, office or {}
    roles, lineage = {}, []
    for r in ROLES:
        src = four if r in ('tally', 'sherlock', 'trigger', 'devil') else office
        roles[r] = {'gen': int((src.get('gen') or {}).get(r) or 1), 'bornAt': _f((src.get('born') or {}).get(r)) or None, 'status': 'ACTIVE',
                    'lesson': dict(((office.get('tune') or {}).get(r) or {})) if src is office else {}}
        for x in src.get('lineage') or []:
            if x.get('agent') == r:
                died = _f(x.get('died') or x.get('at'))
                lineage.append({'role': r, 'gen': x.get('gen'), 'bornAt': x.get('born'), 'retiredAt': died, 'status': 'RETIRED', 'why': x.get('why'),
                                'changed': x.get('changed') or (', '.join(x['lesson']) if isinstance(x.get('lesson'), list) else x.get('lesson')), 'lesson': x.get('oldTune') or {}})
    lineage.sort(key=lambda x: _f(x.get('retiredAt')))
    return {'v': 1, 'at': now, 'roles': roles, 'lineage': lineage[-LINEAGE_KEEP:]}


def ensure(book, now=0.0):
    """Every role present, exactly one live generation each (repairs a partial book)."""
    b = dict(book or {})
    roles = {r: dict(v) for r, v in (b.get('roles') or {}).items() if r in ROLES}
    for r in ROLES:
        v = roles.setdefault(r, {'gen': 1, 'bornAt': None, 'lesson': {}})
        v['gen'] = max(1, int(_f(v.get('gen')) or 1))
        v['lesson'] = dict(v.get('lesson') or {})
        if v.get('status') not in LIVE:
            v['status'] = 'ACTIVE'
    return {**b, 'v': 1, 'roles': roles, 'lineage': [dict(x) for x in (b.get('lineage') or [])][-LINEAGE_KEEP:]}


def attribute(reviews, role, born, integrity=None):
    """This generation's REAL record → {decisions, wins, losses, net, causes (most common first)}. Reviews = the Judge's reviews of confirmed
    exits since it was born. Courier / Archivist / Judge are never blamed for a trade's result: their losses are INTEGRITY failures
    handed in by the caller (`integrity[role]` = unsigned or duplicate fills · a rewritten archive record · a review that failed to file)."""
    rv = [r for r in reviews or [] if r.get('kind') in ('win', 'loss') and _f(r.get('at')) >= _f(born)]
    if role in INTEGRITY_ROLES:
        bad = int(_f((integrity or {}).get(role)))
        return {'decisions': len(rv), 'wins': 0, 'losses': bad, 'net': bad, 'causes': ['integrity'] if bad else []}
    lost = [r for r in rv if r['kind'] == 'loss' and _f((r.get('resp') or {}).get(role)) >= PIN]
    won = [r for r in rv if r['kind'] == 'win' and (role in ENTRY_ROLES or str(r.get('exit') or '').startswith(REAPER_TAKES))]
    c = collections.Counter()
    for r in lost:
        for k in (r.get('cause'), r.get('lossClass')):
            if k:
                c[str(k)] += 1
    return {'decisions': len(rv), 'wins': len(won), 'losses': len(lost), 'net': len(lost) - len(won), 'causes': [k for k, _ in c.most_common()]}


GREAT_WINS = 3   # 🧬 "inherit the great": a generation with at least this many REAL wins credited passes on the settings it won with


def improve(role, causes, tunable=None, prev=None, wins=0):
    """→ (lesson {key: value}, [what changed]) for the NEXT generation: the DEFAULTS plus the fix for how the last one failed, each
    value clamped to its bounds. 🧬 INHERIT THE GREAT (owner, 2026-10-12): a generation that EARNED real wins (≥ GREAT_WINS credited) hands
    down the settings it won with — except the ones its own failure is being fixed on. A generation that never won hands down nothing
    (no inherited fear: a loser's settings die with it)."""
    b = _bounds(tunable).get(role) or {}
    patch, words = {}, []
    fixed = {key for c in causes or [] for key, _v, _w in (CAUSE_PATCH.get(role) or {}).get(str(c), [])}
    if int(wins or 0) >= GREAT_WINS:
        for key, val in (prev or {}).items():
            if key in b and key not in fixed and val is not None:
                _d, lo, hi, _w = b[key]
                patch[key] = max(lo, min(hi, _f(val))); words.append(f"kept {key} {patch[key]:g} — it won {int(wins)} real trades with it")
    for c in causes or []:
        for key, val, w in (CAUSE_PATCH.get(role) or {}).get(str(c), []):
            if key in patch or key not in b:
                continue
            _d, lo, hi, _w = b[key]
            patch[key] = max(lo, min(hi, val)); words.append(w)
    return patch, (words or ['clean defaults — no specific failure pattern to fix'])


def evaluate(book, reviews, now, tunable=None, integrity=None, desk_stats=None):
    """ONE evaluation of all ten roles on the Judge's real evidence. → (book, [events]). An event = {role, kind: 'replaced' | 'probation' |
    'cleared', gen, to, why, changed}. A role whose net real record reaches REPLACE_N is replaced NOW (the new generation is ACTIVE on
    this call, the old one SHADOW)."""
    b = ensure(book, now)
    roles, lineage, events = b['roles'], b['lineage'], []
    for x in lineage:   # a shadow whose 24h ended is retired for good
        if x.get('status') == 'SHADOW' and now - _f(x.get('retiredAt')) >= SHADOW_SEC:
            x['status'] = 'RETIRED'
    for r in ROLES:
        v = roles[r]
        if v.get('bornAt') is None:
            v['bornAt'] = now
        a = attribute(reviews, r, v['bornAt'], integrity)
        ds = (desk_stats or {}).get(r) or {}
        v.update(decisions=a['decisions'], wins=a['wins'], losses=a['losses'], net=a['net'], netImpact=ds.get('medNet'), lastEval=now)
        was = v['status']
        if a['net'] >= REPLACE_N and a['losses'] > 0 and now - _f(v['bornAt']) >= MIN_LIFE_SEC:
            lesson, changed = improve(r, a['causes'], tunable, prev=v.get('lesson'), wins=a['wins'])
            why = (f"{a['losses']} integrity failures this life" if r in INTEGRITY_ROLES
                   else f"real money: {a['losses']} losses pinned this life vs {a['wins']} wins credited" + (f" (most often {a['causes'][0]})" if a['causes'] else ''))
            for x in lineage:   # only ONE shadow per role: the generation before this one is retired now
                if x.get('role') == r and x.get('status') == 'SHADOW':
                    x['status'] = 'RETIRED'
            lineage.append({'role': r, 'gen': v['gen'], 'bornAt': v['bornAt'], 'retiredAt': now, 'status': 'SHADOW', 'why': why, 'changed': '; '.join(changed),
                            'lesson': dict(v.get('lesson') or {}), 'newLesson': dict(lesson), 'decisions': a['decisions'], 'wins': a['wins'], 'losses': a['losses'], 'cause': (a['causes'] or [None])[0]})
            roles[r] = {'gen': v['gen'] + 1, 'bornAt': now, 'status': 'ACTIVE', 'lesson': lesson, 'decisions': 0, 'wins': 0, 'losses': 0, 'net': 0, 'netImpact': None, 'lastEval': now,
                        'lastWhy': f"replaced generation {v['gen']}: {why}"}
            events.append({'role': r, 'kind': 'replaced', 'gen': v['gen'], 'to': v['gen'] + 1, 'why': why, 'changed': '; '.join(changed), 'lesson': lesson})
            continue
        v['status'] = 'PROBATION' if a['net'] >= PROBATION_N and a['losses'] > 0 else 'ACTIVE'
        v['lastWhy'] = (f"{a['losses']} real losses pinned vs {a['wins']} wins credited — replaced at net {REPLACE_N}" if v['status'] == 'PROBATION' and r not in INTEGRITY_ROLES
                        else f"{a['losses']} integrity failures — replaced at {REPLACE_N}" if v['status'] == 'PROBATION'
                        else f"{a['wins']} wins credited · {a['losses']} losses pinned over {a['decisions']} real exits" if a['decisions'] else 'no real exits judged this life yet')
        if v['status'] != was:
            events.append({'role': r, 'kind': 'probation' if v['status'] == 'PROBATION' else 'cleared', 'gen': v['gen'], 'why': v['lastWhy']})
    return {**b, 'at': now, 'roles': roles, 'lineage': lineage[-LINEAGE_KEEP:]}, events


def lessons(book):
    """{role: lesson} of the generation IN CONTROL of each role — the only thing live code may read from a generation."""
    return {r: dict(v.get('lesson') or {}) for r, v in ((book or {}).get('roles') or {}).items() if r in ROLES and v.get('status') in LIVE}


def lesson_value(book_or_lessons, role, key, tunable=None):
    """One parameter of the live generation: its lesson's value inside the bounds, else the default. Accepts a book or `lessons(book)`."""
    d, lo, hi, _w = (_bounds(tunable).get(role) or {})[key]
    ls = lessons(book_or_lessons) if 'roles' in (book_or_lessons or {}) else (book_or_lessons or {})
    v = (ls.get(role) or {}).get(key)
    return max(lo, min(hi, _f(v))) if v is not None else d


def has_authority(book, role, gen):
    """Does generation `gen` of `role` control anything live? Only the current one does."""
    v = ((book or {}).get('roles') or {}).get(role) or {}
    return v.get('status') in LIVE and int(_f(v.get('gen'))) == int(_f(gen))


def sync_office(book, office_tune, replaced=()):
    """The office desks' lesson IS their tunables (office.tune reads `office['tune']`). A role replaced this evaluation writes its new lesson
    there; otherwise a value the office's own shadow test promoted flows into the live generation's lesson. → (book, office tune)"""
    b, t = ensure(book), {k: dict(v) for k, v in (office_tune or {}).items()}
    for r in OFFICE_ROLES:
        if r in replaced:
            if b['roles'][r]['lesson']:
                t[r] = dict(b['roles'][r]['lesson'])
            else:
                t.pop(r, None)
        else:
            b['roles'][r]['lesson'] = dict(t.get(r) or {})
    return b, t


def generations(book, now, shadows=None):
    """→ [AgentGeneration] for the page: role · generation · bornAt · status · decisions · winsAttributed · lossesAttributed · netImpact ·
    lessonVector · lineage (SHADOW / RETIRED, newest first) · lastEvaluation — exactly one live generation per role."""
    b = ensure(book, now)
    out = []
    for r in ROLES:
        v = b['roles'][r]
        past = [{**{k: x.get(k) for k in ('gen', 'status', 'why', 'changed', 'cause', 'decisions', 'wins', 'losses')}, 'at': x.get('retiredAt'), 'lesson': x.get('lesson'),
                 'shadow': (shadows or {}).get(r) if x.get('status') == 'SHADOW' else None} for x in reversed(b['lineage']) if x.get('role') == r][:6]
        out.append({'role': r, 'generation': v['gen'], 'bornAt': v.get('bornAt'), 'status': v['status'], 'decisions': v.get('decisions'), 'winsAttributed': v.get('wins'),
                    'lossesAttributed': v.get('losses'), 'net': v.get('net'), 'netImpact': v.get('netImpact'), 'lessonVector': dict(v.get('lesson') or {}),
                    'lessons': [p['changed'] for p in past[:1] if p.get('changed')], 'lineage': past, 'lastEvaluation': v.get('lastEval'), 'why': v.get('lastWhy'),
                    'replaceAt': REPLACE_N, 'probationAt': PROBATION_N})
    return out
