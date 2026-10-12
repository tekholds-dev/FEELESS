"""⏱ THE 5-MINUTE ROUNDS + THREE-ROUND PATIENCE (owner's trench-desk spec, 2026-10-12). Pure + tested (`tests/test_trench_rounds.py`).

Every candidate in the new-entry universe gets rounds on its OWN clock, from the first pass it was seen:
  ROUND 1  discovery / initial read      ROUND 2  confirm or reject      ROUND 3  final entry decision
Each round stores ONE read from the CURRENT live row (price · tier · score · buyers · pool · 5-min move · chart phase · early-wallet pressure).
By the end of round 3 it becomes ENTER, REJECT or COOLDOWN — never an endless WAIT:
  REJECT   at once on a hard safety failure (`opportunity.hard_fail`), or at round 3 with no tier / a failed thesis
  ENTER    early on a full 🟢 GO; at round 3 when it is A / B tier and CONFIRMED across its reads (momentum held, buyers kept coming,
           pool held, no avoid phase); a C tier enters only when every read improved (small size — the Warden sizes C at half a seat)
  COOLDOWN not bad, nothing developed — out for COOL_SEC unless something MATERIAL changes (then a new round 1 starts at once)
An ENTER decision is valid for one round; not seated by then = COOLDOWN. Held positions get their own round number (`position_round`).
Every finished candidate goes to the round history (round 1 read · round 2 read · round 3 decision) — so patience can be judged.
"""
ROUND_SEC = 300.0
MAX_ROUNDS = 3
COOL_SEC = 900.0          # a COOLDOWN sits out 15 min …
REJECT_SEC = 1800.0       # … a REJECT 30 min, unless something material changes
ENTER_TTL = ROUND_SEC     # an ENTER not seated within one round lapses to COOLDOWN
WAKE_PX = 5.0             # a ≥ 5% price move since the last read, a tier upgrade or a scan landing wakes a cooled coin into a new round 1
AVOID = ('LATE FOMO', 'DISTRIBUTION', 'COLLAPSE')
PREFER = ('EARLY ACCELERATION', 'FIRST PULLBACK', 'RECLAIM', 'BREAKOUT')
HIST_KEEP = 400
PENDING = ('holders not read yet', 'no live price')   # not a NO yet: a newborn's holder scan / price is still coming — it keeps its rounds
TIER_RANK = {'A': 3, 'B': 2, 'C': 1}


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def round_of(first, now):
    return min(MAX_ROUNDS, int(max(0.0, _f(now) - _f(first)) // ROUND_SEC) + 1)


def time_left(first, now):
    """Seconds left in the current round."""
    return round(ROUND_SEC - (max(0.0, _f(now) - _f(first)) % ROUND_SEC), 1)


def read_of(row, tier, score, phase, now):
    n, v, li = row.get('nums') or {}, row.get('vitals') or {}, row.get('li') or {}
    return {'at': round(now, 1), 'px': _f(row.get('px')), 'tier': tier, 'pending': row.get('_pending'), 'score': None if score is None else round(_f(score), 1),
            'buy': n.get('buy'), 'liq': n.get('liq') or v.get('liq'), 'd5': n.get('d5'), 'phase': phase, 'ewp': li.get('ewp'),
            'go': bool(row.get('go'))}


def confirmed(reads):
    """Did the setup HOLD across its rounds? → (ok, why). Missing numbers are not judged."""
    a, z = reads[0], reads[-1]
    if _f(a['px']) > 0 and _f(z['px']) > 0 and z['px'] < a['px'] * 0.97:
        return False, f"price {(z['px'] / a['px'] - 1) * 100:+.1f}% since round 1 — momentum did not hold"
    if z.get('buy') is not None and _f(z['buy']) < 50:
        return False, f"buyers {_f(z['buy']):.0f}% — sellers lead now"
    if a.get('liq') and z.get('liq') and _f(z['liq']) < _f(a['liq']) * 0.8:
        return False, f"pool {(_f(z['liq']) / _f(a['liq']) - 1) * 100:+.0f}% since round 1"
    if z.get('phase') in AVOID:
        return False, f"chart phase {z['phase']}"
    if z.get('ewp') == 'DUMPING':
        return False, 'early wallets dumping'
    return True, 'held across rounds'


def improving(reads):
    """Every read better than the one before (score and price) — the bar for a C-tier entry."""
    return len(reads) >= 2 and all(_f(b.get('score')) > _f(a.get('score')) and _f(b['px']) >= _f(a['px']) for a, b in zip(reads, reads[1:]))


def decide(reads):
    """Round 3 → (ENTER | REJECT | COOLDOWN, why)."""
    z = reads[-1]
    if z.get('pending'):
        return 'COOLDOWN', f"still pending after three rounds: {z['pending']}"
    ok, why = confirmed([r for r in reads if not r.get('pending')] or reads)
    if not z.get('tier'):
        return 'REJECT', 'no tier after three rounds (score under C)'
    if not ok:
        return ('REJECT' if 'sellers' in why or 'pool' in why or 'phase' in why or 'dumping' in why else 'COOLDOWN'), why
    if z['tier'] in ('A', 'B'):
        return 'ENTER', f"{z['tier']}-tier, {why} over {len(reads)} rounds"
    if improving(reads):
        return 'ENTER', f"C-tier improving every round ({' → '.join(str(r.get('score')) for r in reads)}) — small size"
    return 'COOLDOWN', 'C-tier and not improving — nothing developed'


def woken(e, row, tier, now):
    """A cooled / rejected coin comes back as a new round 1 when something MATERIAL changed."""
    last = (e.get('reads') or [{}])[-1]
    if last.get('pending') and tier:
        return f"{last['pending']} -> now read"
    px, lp = _f(row.get('px')), _f(last.get('px'))
    if px > 0 and lp > 0 and abs(px / lp - 1) * 100 >= WAKE_PX:
        return f"price {(px / lp - 1) * 100:+.1f}% since its last read"
    if TIER_RANK.get(tier, 0) > TIER_RANK.get(last.get('tier'), 0):
        return f"tier {last.get('tier') or '—'} → {tier}"
    if row.get('go'):
        return 'a full GO'
    return None


def step(state, rows, now, hard=None, tiers=None, phases=None, held=()):
    """One agent pass. rows = the desk's live table (new-entry universe); hard {mint: reason} · tiers {mint: (tier, score)} ·
    phases {mint: phase}; held = mints on the card (their rounds are positions, not candidates). → new state."""
    s = {'c': dict((state or {}).get('c') or {}), 'hist': list((state or {}).get('hist') or [])}
    hard, tiers, phases, seen = hard or {}, tiers or {}, phases or {}, set()
    def close(m, e, dec, why):
        e = {**e, 'decision': dec, 'why': why, 'decidedAt': now,
             'until': now + (ENTER_TTL if dec == 'ENTER' else REJECT_SEC if dec == 'REJECT' else COOL_SEC)}
        s['hist'].append({'mint': m, 'sym': e.get('sym'), 'first': e['first'], 'decision': dec, 'why': why, 'at': now,
                          'rounds': len(e.get('reads') or []), 'reads': e.get('reads') or []})
        return e
    for r in rows or []:
        m = r.get('mint')
        if not m or m in held:
            continue
        seen.add(m)
        tier, score = (tiers.get(m) or (None, None))
        e = s['c'].get(m)
        if e and e.get('decision'):
            if e['decision'] == 'ENTER' and now >= _f(e.get('until')):
                e = close(m, {**e, 'decision': None}, 'COOLDOWN', 'ENTER not seated within its round')
            elif e['decision'] in ('COOLDOWN', 'REJECT'):
                w = woken(e, r, tier, now) if not hard.get(m) else None
                if w or now >= _f(e.get('until')) or e.get('why') in PENDING:   # an old 'pending' rejection is not a rejection
                    e = {'first': now, 'sym': r.get('symbol'), 'reads': [], 'woke': w or 'cooldown over'}
            s['c'][m] = e
            if e.get('decision'):
                continue
        e = e or {'first': now, 'sym': r.get('symbol'), 'reads': []}
        if hard.get(m) and hard[m] not in PENDING:
            s['c'][m] = close(m, e, 'REJECT', hard[m]); continue
        r = {**r, '_pending': hard.get(m)} if hard.get(m) else r
        rd = round_of(e['first'], now)
        reads = list(e.get('reads') or [])
        if len(reads) < rd:   # one read per round, taken from the CURRENT live row
            reads.append({**read_of(r, tier, score, phases.get(m), now), 'round': rd})
        e = {**e, 'sym': r.get('symbol'), 'reads': reads, 'round': rd, 'seen': now}
        if r.get('go'):
            e = close(m, e, 'ENTER', f"full 🟢 GO in round {rd}")
        elif rd >= MAX_ROUNDS and len(reads) >= MAX_ROUNDS:
            dec, why = decide(reads)
            e = close(m, e, dec, why)
        s['c'][m] = e
    # a candidate that left the universe mid-rounds (aged out, cap crossed, off the board) is closed, not left waiting
    for m, e in list(s['c'].items()):
        if m not in seen and not e.get('decision') and m not in held and now - _f(e.get('seen') or e.get('first')) > ROUND_SEC:   # one pass off the list is a flicker, not an exit
            s['c'][m] = close(m, e, 'COOLDOWN', 'left the new-entry universe for a whole round')
        if e.get('decision') and now - _f(e.get('decidedAt')) > REJECT_SEC + 3600:
            s['c'].pop(m, None)
    s['hist'] = s['hist'][-HIST_KEEP:]
    return s


def entered(state, now):
    """Mints with a live ENTER decision → {mint: why}."""
    return {m: e.get('why') for m, e in ((state or {}).get('c') or {}).items() if e.get('decision') == 'ENTER' and now < _f(e.get('until'))}


def summary(state, now):
    """For the Agents tab: round counts, how candidates ended, average rounds before a decision."""
    c = (state or {}).get('c') or {}
    live = [e for e in c.values() if not e.get('decision')]
    hist = (state or {}).get('hist') or []
    recent = [h for h in hist if now - _f(h.get('at')) < 3600]
    dec = {k: sum(1 for h in recent if h['decision'] == k) for k in ('ENTER', 'REJECT', 'COOLDOWN')}
    return {'round': {str(k): sum(1 for e in live if e.get('round') == k) for k in (1, 2, 3)}, 'decided1h': dec,
            'avgRounds': round(sum(h['rounds'] for h in recent) / len(recent), 2) if recent else None,
            'waitingLongest': max([round(now - _f(e['first'])) for e in live], default=0)}


def position_round(since, now):
    """A held position's round number on its own 5-minute clock + seconds left."""
    return {'round': int(max(0.0, _f(now) - _f(since)) // ROUND_SEC) + 1, 'left': time_left(since, now)}


def action_word(state):
    """Reaper's report state → the round result word: HOLD · PROTECT · TAKE · EXIT · SWAP."""
    s = str(state or '').upper()
    return 'TAKE' if 'TAKE' in s else 'EXIT' if 'EXIT' in s else 'SWAP' if 'SWAP' in s or 'SWITCH' in s else 'PROTECT' if 'PROTECT' in s else 'HOLD'
