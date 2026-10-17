"""🧠 G4'S OWN SEAT (owner, 2026-10-16: "allow in limits to give the AI the seat — he takes all the agents' and Qwen's decisions and goes for what
he knows … in agent chat activity I can see live 1-min snapshot thoughts and vitals on decisions on live trades as the agents and Qwen may try to
get him out").

Pure. Every `EVERY_SEC` the lead model (G4 = Gemma on the desktop, provider `lan`) gets ONE packet: the coins the kernel has READY / CONTENDING
with every desk's word on them and Qwen's last read, plus its own seat (the coin it holds, its live %, and every time an agent rule wanted it out —
the PRESSURE). It answers one action: BUY a listed coin · HOLD · SELL · WAIT. The service applies it:
  paper  → this module's paper book at the live price (no money moves; its record is the proof)
  real   → the normal agent-seat path (Warden size, the keeper's own checks, one approval-free keeper swap like every agent seat)
It can only pick a coin the kernel already lists (never a mint the model made up), and it never touches another seat. A pulled pool, −45% and
the creator's own limits still sell its coin; every other agent rule only ARGUES (filed as pressure). Nothing here is a promise: its own
record — paper and real — is the only thing that says whether it wins.
"""
import json
import re
import statistics

MODES = ('off', 'paper', 'real')
EVERY_SEC = 60.0          # one snapshot thought a minute
FRESH_SEC = 120.0         # a decision older than this is never acted on
LOG_KEEP = 240            # ~4h of minute thoughts
PAPER_USD = 1.0           # the paper seat's size (record = %, the $ is for display)
PAPER_COST_PCT = 1.5      # the measured cost of one swap on the real card — paper pays it both ways
CAND_N = 8
ACTIONS = ('BUY', 'HOLD', 'SELL', 'WAIT')

SYSTEM = """You and one partner model take TURNS on ONE seat of a small real-money Solana trench card: one trade each — whoever buys runs that trade to its exit, then the other hunts the next one. It is your call now. PARTNER = your partner's last call and record: learn from it and beat it (each of you has your own record). Ten rule-based agents (Tally, Sherlock, Trigger,
Devil, Warden, Reaper …) and OSSY's earlier reads also cover these coins — their words are in the packet. You may follow them or overrule them.
Every minute you get a fresh snapshot. Decide ONE action for YOUR seat:
- BUY: only when your seat is empty, and only a coin from CANDIDATES (put its SYMBOL in "coin" — never the long address)
- HOLD: keep the coin you hold
- SELL: sell the coin you hold now
- WAIT: seat empty, nothing worth buying
AGENTS_PICK = the coin the agents would take right now (empty = they would wait). Rules you cannot break: never invent a coin; numbers come only from the packet; a coin you hold can still be sold under you if its pool is
pulled or it falls 45%. PRESSURE = times the agents wanted your coin out — weigh it, you decide.
Answer with ONLY this JSON, nothing else:
{"action":"BUY|HOLD|SELL|WAIT","coin":"<SYMBOL when BUY, else empty>","why":"<one line, under 160 chars, the numbers that decided it>","conf":<0-100>,"watch":"<what would make you sell, under 80 chars>"}"""


def _f(v, d=0.0):
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _r(v, k=1):
    return None if v is None else round(_f(v), k)


def cand_row(c, qwen=None):
    """One candidate as G4 reads it: the kernel's row + every desk's word + Qwen's last read. Unknown = absent."""
    n, v, ch = c.get('nums') or {}, c.get('vitals') or {}, c.get('chart') or {}
    out = {'symbol': c.get('symbol'), 'mint': c.get('mint'), 'status': c.get('status'), 'rank': _r(c.get('rank')),
           'agents': str(c.get('kwhy') or '')[:120], 'trigger': c.get('trigger'), 'chart': c.get('chartCall'), 'size': c.get('size'),
           'cap': _r(v.get('mcap'), 0), 'ageMin': None if v.get('ageH') is None else round(_f(v['ageH']) * 60), 'move5m': _r(n.get('d5')),
           'buyers': _r(n.get('buy'), 0), 'pool': _r(n.get('liq') or v.get('liq'), 0), 'top10': _r(v.get('top10'), 0),
           'germ': _r(ch.get('germDist')), 'germ5': _r(ch.get('germ5Dist')), 'offHigh': _r(ch.get('distHigh'))}
    if qwen:
        out['qwen'] = str(qwen)[:120]
    return {k: x for k, x in out.items() if x not in (None, '')}


def held_row(leg, px, now, pressure=None, qwen=None):
    """G4's own seat right now (None = empty)."""
    if not leg:
        return None
    en, p = _f(leg.get('entry')), _f(px)
    pct = round((p / en - 1) * 100, 2) if en > 0 and p > 0 else None
    out = {'symbol': leg.get('symbol'), 'mint': leg.get('mint'), 'pct': pct, 'heldMin': round((now - _f(leg.get('at'))) / 60, 1) if leg.get('at') is not None else None,
           'peak': _r(leg.get('peakPct')), 'pressure': [f"{x.get('rule')} at {x.get('pct'):+.1f}%: {x.get('why', '')[:70]}" for x in (pressure or [])[-4:]]}
    if qwen:
        out['qwen'] = str(qwen)[:120]
    return {k: x for k, x in out.items() if x not in (None, '', [])}


def packet(cands, held, record=None, partner=None, pick=None):
    """The ONE thing the deciding model reads each minute (+ its partner's last call + the agents' own pick)."""
    out = {'yourSeat': held or 'EMPTY', 'candidates': [{k: v for k, v in c.items() if k != 'mint'} for c in cands[:CAND_N]] or 'none right now',
           'agentsPick': pick or '', 'yourRecord': record or 'no closed trades yet'}
    if partner:
        out['partner'] = partner
    return out


def turn(log, a, b, holding=False):
    """🔁 ONE TRADE AT A TIME (owner, 2026-10-16: "if it's OSSY's turn he calls his buy, and when he's done with the trade it's G4's turn"):
    while the seat holds a coin, the model that BOUGHT it runs it to the exit; once it is sold (seat empty) the OTHER model hunts the next one.
    No buy yet → `a` first. The second key is only the fallback when the first can't answer. → (first, second)."""
    last = next((r.get('by') for r in reversed(log or []) if r.get('by') in (a, b) and r.get('action') == 'BUY'), None)
    if not last:
        return (a, b)
    other = b if last == a else a
    return (last, other) if holding else (other, last)


def partner_of(log, by):
    """The other model's newest call, as the deciding model reads it."""
    r = next((r for r in reversed(log or []) if r.get('by') and r.get('by') != by and r.get('action') not in (None, 'NO ANSWER')), None)
    return None if not r else {'model': r.get('model') or r['by'], 'action': r.get('action'), 'symbol': r.get('symbol'), 'why': str(r.get('why') or '')[:140]}


def by_model(closed):
    """Each model's own record: a trade belongs to the model that OPENED it."""
    out = {}
    for x in closed or []:
        out.setdefault(x.get('by') or '?', []).append(x)
    return {k: record(v) for k, v in out.items()}


def _first_json(text):
    t = str(text or '')
    m = re.search(r'\{.*\}', t, re.S)
    if not m:
        return None
    try:
        j = json.loads(m.group(0))
        return j if isinstance(j, dict) else None
    except ValueError:
        return None


def _sym_in(text, syms):
    """The ONE candidate symbol a free-text line names (None when it names none or several)."""
    t = str(text or '').upper()
    hit = {m for sy, m in (syms or {}).items() if sy and re.search(r'(?<![A-Z0-9])\$?' + re.escape(str(sy).lstrip('$').upper()) + r'(?![A-Z0-9])', t)}
    return next(iter(hit)) if len(hit) == 1 else None


def parse(text, cand_mints, holding, syms=None):
    """→ {action, mint, why, conf, watch} or None. A BUY of a coin not in the list, a BUY while holding, a SELL / HOLD with an empty seat
    are corrected to what the seat can actually do (never acted on as written).
    The coin is read from "coin" / "symbol" / "mint" — and when that field is unusable (small models mangle a 44-char mint; the router masks
    any long address as •••), from the ONE candidate symbol its own "why" names. A reply with no JSON is read for its first action word."""
    j = _first_json(text)
    if not j:
        t = str(text or '')
        m = re.search(r'\b(BUY|HOLD|SELL|WAIT)\b', t.upper())
        if not m:
            return None
        j = {'action': m.group(1), 'why': t[:160]}
    a = str(j.get('action') or '').upper().strip()
    if a not in ACTIONS:
        return None
    cset = set(cand_mints or ())
    raw = str(j.get('coin') or j.get('symbol') or j.get('mint') or '').strip()
    mint = raw if raw in cset else None
    if not mint:
        key = raw.lstrip('$').upper()
        hit = [m for sy, m in (syms or {}).items() if key and str(sy).lstrip('$').upper() == key] or [m for m in cset if len(raw) >= 6 and m.startswith(raw)]
        mint = hit[0] if len(hit) == 1 else None
    if not mint and a == 'BUY':
        mint = _sym_in(j.get('why'), syms)
    mint = mint or ''
    why = re.sub(r'\s+', ' ', str(j.get('why') or '')).strip()[:160]
    conf = max(0, min(100, int(_f(j.get('conf'), 50))))
    watch = re.sub(r'\s+', ' ', str(j.get('watch') or '')).strip()[:80]
    if a == 'BUY' and (holding or mint not in cset):
        a, why = ('HOLD' if holding else 'WAIT'), (why + ' · (BUY refused: ' + ('seat already holds a coin' if holding else 'coin not on the list') + ')')[:200]
        mint = ''
    if a in ('HOLD', 'SELL') and not holding:
        a = 'WAIT'
    if a == 'WAIT' and holding:
        a = 'HOLD'
    return {'action': a, 'mint': mint if a == 'BUY' else '', 'why': why, 'conf': conf, 'watch': watch}


def agents_pick(cands):
    """The coin the ten agents would take right now: the kernel's first READY coin Trigger says ENTER on (None = they would wait)."""
    return next((c for c in cands or [] if c.get('status') == 'READY' and str(c.get('trigger') or '').upper() in ('ENTER', 'GO')), None)


def backup(cands, holding):
    """🤝 AGENTS AS BACKUP: when no model answered, the seat still decides — the agents' own call. Holding → HOLD (Reaper's exits keep
    running on it); empty → BUY the agents' pick, else WAIT. Never a coin the kernel does not list."""
    if holding:
        return {'action': 'HOLD', 'mint': '', 'why': 'no model answered — the agents hold it (Reaper keeps watching)', 'conf': 50, 'watch': ''}
    p = agents_pick(cands)
    if not p:
        return {'action': 'WAIT', 'mint': '', 'why': 'no model answered — nothing READY with an ENTER from Trigger', 'conf': 50, 'watch': ''}
    return {'action': 'BUY', 'mint': p['mint'], 'why': f"no model answered — the agents' pick {p.get('symbol') or ''}: READY, Trigger ENTER"[:160], 'conf': 50, 'watch': ''}


def paper_step(book, dec, cand_by_mint, px_of, now, by=None):
    """The paper seat: BUY opens at the live price, SELL closes it (the measured swap cost both ways). → (book, event | None)."""
    b = {'open': (book or {}).get('open'), 'closed': list((book or {}).get('closed') or [])}
    if not dec:
        return b, None
    o = b['open']
    if dec['action'] == 'BUY' and not o:
        c = (cand_by_mint or {}).get(dec['mint']) or {}
        p = _f(px_of(dec['mint']) if px_of else c.get('px'))
        if p > 0:
            b['open'] = {'mint': dec['mint'], 'symbol': c.get('symbol'), 'entry': p, 'at': now, 'why': dec['why'], 'peak': 0.0, 'by': by}
            return b, {'kind': 'buy', 'symbol': c.get('symbol'), 'px': p}
    if o:
        p = _f(px_of(o['mint']) if px_of else 0)
        if p > 0:
            o['peak'] = max(_f(o.get('peak')), (p / _f(o['entry']) - 1) * 100)
        if dec['action'] == 'SELL' and p > 0:
            gross = (p / _f(o['entry']) - 1) * 100
            net = round(gross - 2 * PAPER_COST_PCT, 2)
            b['closed'] = (b['closed'] + [{**o, 'exit': p, 'closedAt': now, 'pct': net, 'gross': round(gross, 2), 'heldMin': round((now - _f(o['at'])) / 60, 1), 'exitWhy': dec['why'], 'exitBy': by}])[-200:]
            b['open'] = None
            return b, {'kind': 'sell', 'symbol': o.get('symbol'), 'pct': net}
    return b, None


def record(closed):
    """Closed trades (paper or real, % after costs) → {n, won, avg, med, best, worst} — the ONLY proof of G4."""
    xs = [_f(x.get('pct')) for x in closed or [] if x.get('pct') is not None]
    if not xs:
        return {'n': 0}
    return {'n': len(xs), 'won': round(100 * sum(1 for x in xs if x > 0) / len(xs)), 'avg': round(sum(xs) / len(xs), 2),
            'med': round(statistics.median(xs), 2), 'best': round(max(xs), 1), 'worst': round(min(xs), 1)}


def record_words(rec):
    r = rec or {}
    return 'no closed trades yet' if not r.get('n') else f"{r['n']} closed · {r['won']}% won · avg {r['avg']:+.1f}% · typical {r['med']:+.1f}% (after costs)"


def note(log, row, keep=LOG_KEEP):
    """One minute thought on the live log (newest last)."""
    return (list(log or []) + [row])[-keep:]


def due(last_at, now, every=EVERY_SEC):
    return now - _f(last_at) >= every


def fresh(dec, now):
    return bool(dec) and now - _f(dec.get('at')) <= FRESH_SEC
