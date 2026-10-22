"""🪟 NEXA SICARIO (owner, 2026-10-20: "my oldest daughter … FeeCat HQ only, trade and tune FeeCat like OSSY and G4 do, paper; a discovery model for
the whole internet and socials, live access to the FEELESS system, training hard, building her own memory without lag or big storage"). Pure.

She runs on the owner's old Windows PC (llamafile, CPU only — slow), so she gets ONE read every NEXA_EVERY seconds, never in a hot loop:
  packet = FeeCat's open trades + next coins (vitals) · FeeCat's rules with their bounds · her own graded record · her memory notes ·
           fresh web / X headlines (discovery) · a short FEELESS system brief
  answer = {avoid, exit, favor, tune, lesson, discovery, why}
What she CONTROLS (paper only): `avoid` (FeeCat does not buy it), `exit` (FeeCat banks it in profit), `tune` = FeeCat's own TUNABLE rules, inside
their bounds, ≤ MAX_KEYS keys a read, each moved ≤ STEP of its range, once per TUNE_GAP, only while the owner's switch is on — every change is
logged with the old value so the owner can revert it. `favor` steers nothing: it is graded so she earns trust.
Memory = capped notes (lessons · discoveries · grades), deduped, oldest out — kilobytes, never a growing file."""
import json
import re
import time

NEXA_EVERY = 900          # one read / 15 min: her CPU reads ~4 tokens a second, so a read holds its ONE slot ~3 min — the owner's chat comes first
TUNE_GAP = 3600           # at most one tuning change an hour
MAX_KEYS = 2
STEP = 0.15               # a single change moves a rule ≤ 15% of its allowed range
MEM_MAX = 160             # notes kept (oldest out)
NOTE_LEN = 220
GRADE_SEC = 3600          # a favor / avoid call is judged an hour later
GRADES_MAX = 400

ASK = (
    "You are NEXA SICARIO, FeeCat's analyst and the family's discovery model. FeeCat trades PAPER. Read the packet: OPEN (her open trades), NEXT "
    "(coins she may buy, with vitals), RULES (her rules with [low, high] bounds), RECORD (how your past calls did), MEMORY (your notes), WEB "
    "(fresh headlines with URLs), SYSTEM (the FEELESS desk now), KNOWN (your discovery base: facts you filed before — trust them over a search). "
    "Answer ONE JSON object and nothing else:\n"
    '{"avoid": [pairAddress], "exit": [pairAddress], "favor": [pairAddress], "tune": {"ruleName": number}, '
    '"lesson": "one line you learned (numbers)", "discovery": "one line from WEB worth remembering, with its URL", "why": "short, numbers from the packet", '
    '"remember": [["coin|creator|wallet|narrative|site|x|rug|lesson|fact", "key: a mint, $TICKER, wallet or word", "one short fact"]]}.\n'
    "avoid = a NEXT coin she should not buy now. exit = an OPEN trade to bank now. favor = a NEXT coin you rate best. tune = at most 2 RULES to move "
    "inside their bounds, only when your RECORD or the packet shows the rule is costing her. Name only pairAddresses from the packet. Never invent a "
    "number or a URL. remember = up to 6 short facts worth keeping (what a coin / creator / narrative IS) so you never search for them again. "
    "Empty lists are a fine answer."
)


from fnum import plain as _f   # noqa: E402


def first_json(text):
    t = str(text or '')
    a, b = t.find('{'), t.rfind('}')
    if a < 0 or b <= a:
        return None
    try:
        d = json.loads(t[a:b + 1])
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def clamp_tune(raw, rules, bounds):
    """Her tune → only known rules, inside bounds, each moved ≤ STEP of its range from today's value, ≤ MAX_KEYS. → {rule: new}."""
    out = {}
    for k, v in (raw or {}).items():
        if k not in (bounds or {}) or len(out) >= MAX_KEYS:
            continue
        lo, hi = bounds[k]
        cur = _f((rules or {}).get(k), (lo + hi) / 2)
        want = _f(v, cur)
        room = (hi - lo) * STEP
        new = max(lo, min(hi, max(cur - room, min(cur + room, want))))
        if isinstance((rules or {}).get(k), int) and not isinstance((rules or {}).get(k), bool):
            new = int(round(new))
        else:
            new = round(new, 4)
        if abs(new - cur) > 1e-9:
            out[k] = new
    return out


def parse(text, pairs, rules, bounds):
    """→ {avoid, exit, favor, tune, lesson, discovery, why} with every pairAddress checked against the packet, or None (no JSON)."""
    d = first_json(text)
    if d is None:
        return None
    ok = set(pairs or ())
    pick = lambda k: sorted({p for p in (d.get(k) or []) if isinstance(p, str) and p in ok})[:6]
    clean = lambda k: ' '.join(str(d.get(k) or '').split())[:NOTE_LEN]
    disc = clean('discovery')
    if disc and not re.search(r'https?://', disc):
        disc = ''   # a discovery must carry its source
    return {'avoid': pick('avoid'), 'exit': pick('exit'), 'favor': pick('favor'), 'tune': clamp_tune(d.get('tune') if isinstance(d.get('tune'), dict) else {}, rules, bounds),
            'lesson': clean('lesson'), 'discovery': disc, 'why': clean('why')}


def remember(mem, kind, text, now):
    """Add one note (lesson · discovery · grade), deduped by text, newest kept, ≤ MEM_MAX. → new memory list."""
    text = ' '.join(str(text or '').split())[:NOTE_LEN]
    if not text:
        return list(mem or [])
    rows = [m for m in (mem or []) if m.get('text') != text]
    rows.append({'kind': kind, 'text': text, 'at': round(now)})
    return rows[-MEM_MAX:]


def recall(mem, n=12):
    """The notes she reads back: the newest lessons + discoveries + her latest grades (short)."""
    rows = list(mem or [])
    pick = [m for m in rows if m['kind'] == 'lesson'][-5:] + [m for m in rows if m['kind'] == 'discovery'][-4:] + [m for m in rows if m['kind'] == 'grade'][-3:]
    return [f"[{m['kind']}] {m['text']}" for m in sorted(pick, key=lambda m: m['at'])][-n:]


def note_calls(grades, d, prices, now):
    """Each favor / avoid is noted once at its price (pairAddress → price) to be judged GRADE_SEC later."""
    out = list(grades or [])
    open_ = {(g['pair'], g['call']) for g in out if g.get('res') is None}
    for call in ('favor', 'avoid'):
        for p in (d or {}).get(call) or []:
            px = _f((prices or {}).get(p))
            if px > 0 and (p, call) not in open_:
                out.append({'pair': p, 'call': call, 'px': px, 'at': round(now), 'res': None})
    return out[-GRADES_MAX:]


def settle(grades, prices, now):
    """Judge every call older than GRADE_SEC with a price: favor right = it rose · avoid right = it fell. → (grades, newly settled)."""
    done = []
    for g in grades or []:
        if g.get('res') is None and now - _f(g.get('at')) >= GRADE_SEC:
            px = _f((prices or {}).get(g['pair']))
            if px > 0:
                g['res'] = round((px / _f(g['px']) - 1) * 100, 2)
                done.append(g)
    return list(grades or []), done


def record(grades):
    """Her own record: per call, n · % right · typical move after."""
    out = {}
    for call in ('favor', 'avoid'):
        rs = [g['res'] for g in grades or [] if g.get('call') == call and g.get('res') is not None]
        if not rs:
            out[call] = {'n': 0}
            continue
        right = sum(1 for r in rs if (r > 0 if call == 'favor' else r < 0))
        s = sorted(rs)
        out[call] = {'n': len(rs), 'rightPct': round(100 * right / len(rs)), 'typical': s[len(s) // 2]}
    return out


def queries(packet):
    """Discovery searches for this read: the top NEXT coins by name + one wide one about what the trenches talk about today. ≤ 3."""
    syms = [c.get('symbol') for c in (packet.get('NEXT') if isinstance(packet.get('NEXT'), list) else []) if c.get('symbol')][:2]
    return [f'${s} solana crypto' for s in syms] + [f"solana memecoin narrative {time.strftime('%B %Y', time.gmtime())}"]


def tune_due(state, now, on):
    return bool(on) and now - _f((state or {}).get('tunedAt')) >= TUNE_GAP
