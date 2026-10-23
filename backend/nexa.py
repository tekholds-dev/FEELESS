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
# ⚡ FAST READ (owner, 2026-10-22: NEXA "slow ass" on the i5): most reads are numbers only — the coins as short lines tagged O1 / N1 (a 44-char
# pairAddress costs ~30 tokens in AND out), no JSON keys in, a tiny JSON out → a fraction of the prompt + ≤ FAST_TOK tokens of answer. The FULL read
# (tune · lesson · discovery · remember) runs once per FULL_EVERY.
FULL_EVERY = 3600
FAST_TOK = 48
FAST_OPEN, FAST_NEXT = 3, 5
ASK_FAST = (
    "You are NEXA SICARIO, FeeCat's analyst. FeeCat trades PAPER. Each line is a coin: O# = her open trades, N# = coins she may buy "
    "(cap $, age min, 5m %, buyers, pool $, top10 %, germ). Answer ONE JSON line and nothing else: "
    '{"exit":["O#"],"avoid":["N#"],"favor":["N#"],"why":"<the numbers that decided it, max 12 words>"}. '
    "exit = bank an open trade now. avoid = she should not buy it. favor = the best next coin. Use only the lines given. Empty lists are fine."
)

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

# 🪶 LEAN FULL READ (2026-10-22: her full read took ~177 s on the i5 and came back CUT OFF — 44-char pairAddresses + six fields could never fit
# 100 tokens, so the JSON failed to parse and she "couldn't read"). Same O# / N# lines as the fast read, rules + record + notes as short text,
# NO chat persona (it is for her voice, not a JSON read), ≤ 2 remembered facts, FULL_TOK to finish.
FULL_TOK, FULL_NOTES = 180, 6
ASK_FULL = (
    "You are NEXA SICARIO, FeeCat's analyst. FeeCat trades PAPER. COINS: O# = her open trades, N# = coins she may buy (cap $, age min, 5m %, buyers, "
    "pool $, top10 %, germ). THEORY = the desk's proven laws (fresh < 15 min loses; still on the curve loses; cap < $30K + graduated is the only proven "
    "setup; exits first; holds 30 min+ win). RULES = name value [low high]. RECORD = how your calls did. NOTES = what you filed. Answer ONE JSON line "
    "and nothing else: "
    '{"exit":["O#"],"avoid":["N#"],"favor":["N#"],"tune":{"rule":number},"lesson":"one line, numbers","why":"under 15 words",'
    '"remember":[["coin|creator|narrative|lesson|fact","key","short fact"]]}. '
    "tune ≤ 2 RULES inside their bounds, only when RECORD shows the rule costs her. remember ≤ 2. Use only the lines given. Empty lists are fine."
)


def full_text(lines, rules, bounds, record_, notes):
    """The lean full-read packet as plain text (the coin lines come from fast_lines)."""
    rl = ' · '.join(f"{k} {v} [{(bounds.get(k) or ('?', '?'))[0]} {(bounds.get(k) or ('?', '?'))[1]}]" for k, v in list((rules or {}).items())[:10])
    rc = ' · '.join(f"{k} n{v.get('n', 0)}" + (f" {v['rightPct']}% right typical {v['typical']:+.1f}%" if v.get('n') else '') for k, v in (record_ or {}).items())
    return f"COINS\n{lines}\nRULES {rl or 'none'}\nRECORD {rc or 'none yet'}\nNOTES " + (' | '.join(str(n)[:120] for n in (notes or [])[-FULL_NOTES:]) or 'none')


def parse_full(text, ids, rules, bounds):
    """The lean full answer → parse()'s shape: tags mapped back to pairAddresses, tune clamped, lesson kept."""
    d = first_json(text)
    if d is None:
        return None
    out = parse_fast(text, ids)
    out['tune'] = clamp_tune(d.get('tune') if isinstance(d.get('tune'), dict) else {}, rules, bounds)
    out['lesson'] = ' '.join(str(d.get('lesson') or '').split())[:NOTE_LEN]
    return out


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


def full_due(st, now):
    """The FULL read (tune + lesson + discovery) once per FULL_EVERY; every other read is the fast one."""
    at = (st or {}).get('fullAt')
    return not at or now - _f(at) >= FULL_EVERY


def _k(v):
    v = _f(v, None) if v is not None else None
    if v is None:
        return None
    a = abs(v)
    return f"{v / 1e6:.1f}M" if a >= 1e6 else f"{v / 1e3:.0f}K" if a >= 1e3 else (f"{v:.1f}" if a < 10 and v != int(v) else str(int(round(v))))


def fast_lines(open_, next_):
    """The packet as short number lines → (text, {'O1': pairAddress, 'N1': …}). Only coins with a pairAddress; ≤ FAST_OPEN open + FAST_NEXT next."""
    rows, ids = [], {}
    for pre, xs, n in (('O', open_, FAST_OPEN), ('N', next_, FAST_NEXT)):
        i = 0
        for x in (xs if isinstance(xs, list) else []):
            if not isinstance(x, dict) or not x.get('pairAddress') or i >= n:
                continue
            i += 1
            tag = f"{pre}{i}"
            ids[tag] = x['pairAddress']
            mv = _f(x.get('move5m'), None) if x.get('move5m') is not None else None
            bits = [tag, f"${str(x.get('symbol') or '?')[:10]}", *(f"{w} {v}" for w, v in (
                ('cap', _k(x.get('cap'))), ('age', _k(x.get('ageMin'))), ('5m', None if mv is None else f"{mv:+.1f}"), ('buyers', _k(x.get('buyers'))),
                ('pool', _k(x.get('pool'))), ('top10', _k(x.get('top10'))), ('germ', _k(x.get('germ')))) if v is not None)]
            if pre == 'O' and x.get('status'):
                bits.append(str(x['status'])[:12])
            rows.append(' '.join(bits))
    return '\n'.join(rows) or 'no coins', ids


_ECHO = re.compile(r'under \d{1,2} words|max \d{1,2} words|the numbers that decided|^numbers?$|^<.*>$|^why$', re.I)   # "under 15 words" (her read's why) echoed too, 2026-10-23


def real_why(w):
    """🧽 Her small model echoes the prompt's placeholder ("under 12 words, numbers" landed on every FeeCat receipt, 2026-10-23) → ''.
    A real reason passes untouched. Pure (tests)."""
    w = ' '.join(str(w or '').split())[:NOTE_LEN]
    return '' if _ECHO.search(w) else w


def parse_fast(text, ids):
    """The fast answer → the same shape as parse() (tune / lesson / discovery empty), tags mapped back to pairAddresses; None = no JSON."""
    d = first_json(text)
    if d is None:
        return None

    def pick(k, pre):
        out = set()
        for v in (d.get(k) or []) if isinstance(d.get(k), list) else []:
            t = str(v).strip().upper()
            t = t if t[:1] in ('O', 'N') else f"{pre}{t}"   # a bare 2 means N2 / O2
            if t.startswith(pre) and t in ids:
                out.add(ids[t])
        return sorted(out)[:6]
    return {'avoid': pick('avoid', 'N'), 'exit': pick('exit', 'O'), 'favor': pick('favor', 'N'), 'tune': {}, 'lesson': '', 'discovery': '',
            'why': real_why(d.get('why'))}


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
            'lesson': clean('lesson'), 'discovery': disc, 'why': real_why(d.get('why'))}


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
