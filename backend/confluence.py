"""🧬 EDGE SCORE — Coming up = the best of the owner's swap-in lists, ranked by EVIDENCE (pure, tested).

Owner, 2026-10-08: "coming up should be the best of my swap in, not bs — plus complex meta add-ons humans could never figure out".
A human reads a list top-down and trusts the call on the row. This scores every coin across ALL the swap-in lists at once:

  · LISTS   every list the coin sits in, weighted by its rank there, each worth that list's OWN settled 1-hour median
  · CALL    the coin's read (BOND RUN, SEND IT, WASH TRADED …) worth that call's OWN settled 1-hour median
  · COMBO   the learned layer: coins are bucketed by (how many lists × the read's tone × flow pace), every bucket the board ranks
            is noted and settled an hour later (`track`), and a bucket with ≥ 5 settled adds its own median — interactions no
            single list or call shows (e.g. "in 3 lists but sellers in charge")
  · YOURS   how coins like this one ended on the owner's REAL card (real_learn.py: age · 1h move · buyers · pool · tag · who picked)
  · VITAL   small hand-set tilts (vital grade, organic flow, proven callers, pool drain) — labelled hand-set, never learned

edge = expected 1-hour move in %, from the records that exist (the hand-set tilts add at most ±6 pts). A ranking of evidence,
never a promise: on 2026-10-08 nearly every list and call had a NEGATIVE 1h median, so the score mostly separates bad from worse.
"""

LISTS = ('ptrend', 'calls', 'double', 'fed', 'movers', 'bottom', 'volume', 'pump', 'trench')
LIST_LABEL = {'ptrend': '🔥 Pump trending', 'calls': '📣 Pump callouts', 'double': '🔥🔥 Double signal', 'fed': '🧲 Fed runners', 'movers': '🚀 Movers',
              'bottom': '🟢 Dips & bottoms', 'volume': '🌊 Volume', 'pump': '🆕 New launches', 'trench': '🗑 Trench'}
MIN_N = 5          # a record counts once it has this many settled coins
TILT_MAX = 6.0     # hand-set tilts may move the edge at most this many points


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def _rec(r):
    return _f((r or {}).get('medPct')) if _f((r or {}).get('n')) >= MIN_N else None


def bucket(n_lists, tone, pace):
    """The learned-combo key: lists 1 / 2 / 3+ × read tone × flow pace (speeding / steady / fading)."""
    nl = '3+' if n_lists >= 3 else str(max(1, int(n_lists)))
    p = 'na' if pace is None else 'fast' if pace >= 1.3 else 'fade' if pace < 0.6 else 'flat'
    return f"{nl}|{tone or 'none'}|{p}"


def _pace(row):
    v1, v5 = _f(row.get('vol1h')), _f(row.get('vol5m'))
    return v5 * 12 / v1 if v1 > 0 and v5 > 0 else None


def edge(row, ranks, list_rec, call_rec, combo_rec=None, call_key=None, real_tbl=None):
    """`ranks` = {list: rank (1 = top)} for this coin. → {edge, parts [[label, pts]], lists, bucket, known}."""
    r = row or {}
    parts, known = [], 0
    # LISTS: rank-weighted average of each list's own record (top of a list counts most)
    num = den = 0.0
    for k, rk in (ranks or {}).items():
        m = _rec((list_rec or {}).get(k))
        if m is None:
            continue
        w = 1.0 / (1.0 + (max(1, int(rk)) - 1) / 10.0)
        num += w * m; den += w
    if den:
        v = num / den; parts.append([f"lists ({len(ranks)})", round(v, 1)]); known += 1
    # CALL: the read's own record
    tv = r.get('tv') or {}
    call = (tv.get('call') or [None, None, None])
    cm = _rec((call_rec or {}).get(call_key)) if call_key else None
    if cm is not None:
        parts.append([f"{call[0] or ''} {call[1] or 'read'}".strip(), round(cm, 1)]); known += 1
    # COMBO: the learned interaction bucket
    b = bucket(len(ranks or {}), call[2], _pace(r))
    bm = _rec((combo_rec or {}).get(b))
    if bm is not None:
        parts.append([f"combo {b}", round(bm, 1)]); known += 1
    # YOUR REAL TRADES: how coins like this one ended on the owner's real card (real_learn.py)
    if real_tbl:
        import real_learn as _rl
        rm, hits = _rl.match(r, real_tbl)
        if rm is not None:
            parts.append([f"your real trades ({sum(h[2] for h in hits)} pieces)", round(rm, 1)]); known += 1
    base = sum(p[1] for p in parts) / len(parts) if parts else 0.0
    # VITAL tilts (hand-set, capped)
    tilt = 0.0
    v = r.get('vital') or {}
    if v.get('score') is not None:
        tilt += (_f(v['score']) - 50) / 10
    org = v.get('organicPct')
    if org is not None:
        tilt += 1.5 if _f(org) >= 20 else -1.5 if _f(org) < 3 else 0.0
    pc = r.get('pc') or {}
    if _f(pc.get('pros')) > 0:
        tilt += 1.5
    if r.get('safe') is False:
        tilt -= 3
    tilt = max(-TILT_MAX, min(TILT_MAX, tilt))
    if tilt:
        parts.append(['vital · organic · callers (hand-set)', round(tilt, 1)])
    return {'edge': round(base + tilt, 1), 'parts': parts, 'lists': sorted(ranks or {}, key=lambda k: (ranks or {})[k]), 'bucket': b, 'known': known}


def gather(lists):
    """{list: [rows in that list's order]} → {mint: (merged row, {list: rank})}. One row per coin; fields from the first list that has them."""
    out = {}
    for k in LISTS:
        for i, row in enumerate((lists or {}).get(k) or []):
            m = (row or {}).get('mint') or (row or {}).get('baseAddress')
            if not m:
                continue
            got = out.get(m)
            if got:
                merged = {**{a: b for a, b in row.items() if b is not None}, **{a: b for a, b in got[0].items() if b is not None}}
                got[1].setdefault(k, i + 1)
                out[m] = (merged, got[1])
            else:
                out[m] = ({**row, 'mint': m}, {k: i + 1})
    return out


def rank(lists, list_rec, call_rec, combo_rec=None, call_key_of=None, real_tbl=None):
    """Every coin of every swap-in list, best evidence first → [{**row, 'edge': {...}}]."""
    ck = call_key_of or (lambda row: None)
    rows = []
    for m, (row, ranks) in gather(lists).items():
        e = edge(row, ranks, list_rec, call_rec, combo_rec, ck(row), real_tbl)
        rows.append({**row, 'mint': m, 'edge': e})
    rows.sort(key=lambda x: (-x['edge']['edge'], -x['edge']['known'], -len(x['edge']['lists'])))
    return rows


def words(e):
    """One line for the screen: '🧬 −1.2% · in 🔥 Pump trending + 🧲 Fed runners · read COOLING −3.6%'."""
    if not e:
        return ''
    ls = ' + '.join(LIST_LABEL.get(k, k) for k in (e.get('lists') or [])[:3])
    return f"🧬 {e['edge']:+.1f}% expected · in {ls}" if ls else f"🧬 {e['edge']:+.1f}% expected"
