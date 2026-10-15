"""🤝 THE DUET — the two LM Studio models read the SAME thing and grow on ONE record (owner, 2026-10-14: "gemma primary, qwen secondary,
these 2 need to learn / grow together").

  🖥 LEAD   = 'lan'   (Gemma on the desktop Mac — its GPU is not the one this Mac's browser draws with)
  💻 SECOND = 'local' (Qwen on this Mac — fast, but it shares the GPU with Chrome, so it only re-reads what the lead flagged)

How they grow together, honestly:
  · every read of each model is graded on its own (ai_learn keeps `prov`);
  · a coin both read inside PAIR_SEC is a PAIR → `record` counts how often they agree, how the coins did when they agreed vs split,
    and WHO WAS RIGHT WHEN THEY SPLIT;
  · `merge` uses that: an agreed stance stands; a split is NEUTRAL until one of them has won ≥ TRUST_N splits at ≥ TRUST_PCT — then
    the split goes that model's way (the pair learns which of the two to listen to, on its own record, never on a hunch).
Advisory only, like every model read: an agreed CAUTION may hold a coin back (tightening), nothing here buys, sizes or sells.
"""
from __future__ import annotations

LEAD, SECOND = 'lan', 'local'
PAIR_SEC = 600.0          # two reads of the same coin this close together are one pair
SECOND_EVERY = 150.0      # 💻 the second model re-reads at most this often (it shares this Mac's GPU)
TRUST_N, TRUST_PCT = 10, 60
NAME = {LEAD: '🖥 GEMMA', SECOND: '💻 QWEN'}


def _f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def _right(stance, pct):
    """Did a stance call it? CAUTION → the coin fell, FAVOR → it rose; NEUTRAL claims nothing (None)."""
    if stance == 'CAUTION':
        return pct < 0
    if stance == 'FAVOR':
        return pct > 0
    return None


def second_due(lead_advice, last_at, now, lagging=False):
    """💻 Should Qwen re-read the case Gemma just read? Only a real call (not NEUTRAL), never while a browser lags, ≤ once per SECOND_EVERY."""
    st = (lead_advice or {}).get('stance')
    return bool(st in ('CAUTION', 'FAVOR') and not lagging and now - _f(last_at) >= SECOND_EVERY)


def merge(lead, second, rec=None):
    """Two advices on one coin → the duet's read {stance, agree, lead, second, flags, why, trusted}. Missing one = the other alone, marked."""
    a, b = (lead or {}).get('stance'), (second or {}).get('stance')
    flags = list(dict.fromkeys([str(x) for x in ((lead or {}).get('risk_flags') or []) + ((second or {}).get('risk_flags') or [])]))[:4]
    delta = min(_f((lead or {}).get('confidence_delta')), _f((second or {}).get('confidence_delta')))
    if not a or not b:
        one = a or b
        return {'stance': one or 'NEUTRAL', 'agree': None, 'lead': a, 'second': b, 'flags': flags, 'confidence_delta': delta,
                'why': 'one model only', 'trusted': None}
    if a == b:
        return {'stance': a, 'agree': True, 'lead': a, 'second': b, 'flags': flags, 'confidence_delta': delta,
                'why': f'both read {a}', 'trusted': None}
    t = trusted(rec)
    pick = a if t == LEAD else b if t == SECOND else 'NEUTRAL'
    return {'stance': pick, 'agree': False, 'lead': a, 'second': b, 'flags': flags,
            'confidence_delta': _f((lead if t == LEAD else second if t == SECOND else {}).get('confidence_delta')),
            'why': f"split: Gemma {a} vs Qwen {b}" + (f" → {NAME[t]} wins splits on its record" if t else ' → neutral until one proves it wins splits'),
            'trusted': t}


def pairs(done):
    """Graded reads (ai_learn `done`) → pairs of a lead read and a second read of the same coin within PAIR_SEC."""
    by = {}
    for c in done or []:
        p = c.get('prov') or c.get('src')
        if p in (LEAD, SECOND) and c.get('mint') and c.get('pct') is not None:
            by.setdefault(c['mint'], []).append(c)
    out = []
    for rows in by.values():
        ls = [c for c in rows if (c.get('prov') or c.get('src')) == LEAD]
        ss = [c for c in rows if (c.get('prov') or c.get('src')) == SECOND]
        used = set()
        for l in ls:
            m = min((s for i, s in enumerate(ss) if i not in used and abs(_f(s.get('at')) - _f(l.get('at'))) <= PAIR_SEC),
                    key=lambda s: abs(_f(s.get('at')) - _f(l.get('at'))), default=None)
            if m is not None:
                used.add(ss.index(m))
                out.append((l, m))
    return out


def _med(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs)
    return round(xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2, 1)


def record(done):
    """The duet's own record: pairs, agree %, typical move when they agreed CAUTION / FAVOR, and who was right when they split."""
    ps = pairs(done)
    agree = [(l, s) for l, s in ps if l.get('stance') == s.get('stance')]
    split = [(l, s) for l, s in ps if l.get('stance') != s.get('stance')]
    win = {LEAD: 0, SECOND: 0}
    called = 0
    for l, s in split:
        pct = _f(l.get('pct'))
        rl, rs = _right(l.get('stance'), pct), _right(s.get('stance'), pct)
        if rl is None and rs is None:
            continue
        called += 1
        if rl:
            win[LEAD] += 1
        if rs:
            win[SECOND] += 1
    both = lambda st: [_f(l.get('pct')) for l, s in agree if l.get('stance') == st]
    bc, bf = both('CAUTION'), both('FAVOR')
    return {'pairs': len(ps), 'agreePct': round(100 * len(agree) / len(ps)) if ps else None,
            'bothCaution': {'n': len(bc), 'med': _med(bc), 'right': round(100 * sum(1 for x in bc if x < 0) / len(bc)) if bc else None},
            'bothFavor': {'n': len(bf), 'med': _med(bf), 'right': round(100 * sum(1 for x in bf if x > 0) / len(bf)) if bf else None},
            'splits': called, 'leadWins': win[LEAD], 'secondWins': win[SECOND],
            'leadPct': round(100 * win[LEAD] / called) if called else None, 'secondPct': round(100 * win[SECOND] / called) if called else None}


def trusted(rec):
    """Which model the pair listens to on a split — only once its split record proves it (≥ TRUST_N called splits, ≥ TRUST_PCT right)."""
    r = rec or {}
    if _f(r.get('splits')) < TRUST_N:
        return None
    best = max((LEAD, SECOND), key=lambda k: _f(r.get('leadPct' if k == LEAD else 'secondPct')))
    pct = _f(r.get('leadPct' if best == LEAD else 'secondPct'))
    other = _f(r.get('secondPct' if best == LEAD else 'leadPct'))
    return best if pct >= TRUST_PCT and pct > other else None


# ── the owner's chat: both models on one question ─────────────────────────────────────────────────────────────────────────────
def second_prompt(question, lead_text):
    """💻 What Qwen is asked after Gemma answered: agree or push back, add what is missing — never repeat."""
    return (f"The owner asked: {str(question)[:1500]}\n\n🖥 Gemma (the lead model) answered:\n{str(lead_text)[:2500]}\n\n"
            "You are the SECOND model. In ≤ 5 lines: say AGREE or PUSH BACK first, then only what Gemma got wrong or left out, "
            "with the numbers from the context. Do not repeat what is already right.")


def combine(lead_text, second_text):
    """The chat reply when both answered (or which one did)."""
    a, b = str(lead_text or '').strip(), str(second_text or '').strip()
    if a and b:
        return f"🖥 GEMMA\n{a}\n\n💻 QWEN — second read\n{b}"
    return a or b or None


def view(rec):
    """What the page shows: the record + who the pair listens to on a split."""
    r = rec or {}
    if not r.get('pairs'):   # nothing paired yet: one tiny line (the office payload is capped at 100 KB)
        return {'pairs': 0, 'need': TRUST_N}
    return {**{k: v for k, v in r.items() if v not in (None, 0) or k == 'pairs'}, 'trusted': trusted(r), 'need': TRUST_N}
