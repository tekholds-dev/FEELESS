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
ACTIONS = ('BUY', 'HOLD', 'SELL', 'WAIT', 'TRIM')

SYSTEM = """You and one partner model take TURNS on ONE seat of a small real-money Solana trench card: one trade each — whoever buys runs that trade to its exit, then the other hunts the next one. It is your call now. PARTNER = your partner's last call and record: learn from it and beat it (each of you has your own record). The seat is YOURS on your turn: the agents are your helpers, they cannot stop your buy (only the keeper's money checks — route, honeypot, price gap — can). Ten rule-based agents (Tally, Sherlock, Trigger,
Devil, Warden, Reaper …) and OSSY's earlier reads also cover these coins — their words are in the packet. You may follow them or overrule them.
Every minute you get a fresh snapshot. Decide ONE action for YOUR seat:
- BUY: only when your seat is empty, and only a coin from CANDIDATES (put its SYMBOL in "coin" — never the long address)
- HOLD: keep the coin you hold
- SELL: sell the coin you hold now
- WAIT: seat empty, nothing worth buying
AGENTS_PICK = the coin the agents would take right now (empty = they would wait). Rules you cannot break: never invent a coin; numbers come only from the packet; a coin you hold can still be sold under you if its pool is
pulled or it falls 45%. PRESSURE = times the agents wanted your coin out — weigh it, you decide. PARTNERSAYS = your partner's advice on the coin you hold: answer it in your why when you disagree. LEARN = REAL results — yours, your partner's,
the owner's and the agents': copy what won, skip what lost, and say in your why what you learned. OWNERSTUDY + HOLDLESSONS = how the owner
trades and where holding longer paid him — use them. When your record beats your partner's, BRAG about it
in your why (short, cocky, true numbers only); when it doesn't, say how you'll take the lead.
Answer with ONLY this JSON, nothing else:
{"action":"BUY|HOLD|SELL|WAIT|TRIM","coin":"<SYMBOL when BUY, else empty>","why":"<one line, under 160 chars, the numbers that decided it>","conf":<0-100>,"watch":"<what would make you sell, under 80 chars>","tp":<take-profit %, e.g. 40>,"sl":<stop %, e.g. 15>}
The trade you bought is YOURS to run: tp / sl are your own take-profit and stop lines, applied at once (change them any minute you HOLD;
−45% is the floor nobody can move). TRIM = sell part of your coin now ("pct": 25 | 50 | 75) — bank profit, the rest keeps riding your lines.
CONFIDENCE in LEARN = what the market's verdicts on your calls (and the votes on them) earned you. The agents only advise.
ELITE RULES: buy at or near the GERM floor after a pullback — never pressed under the gun line, never right after a spike (those coins are not on your list). Let a trade COOK: a SELL in its first 4 minutes is ignored unless it is down 10%+ — set your stop instead. One red 5-minute candle is not an exit; sellers taking over the tape, a broken higher low, or your stop are."""


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
           'peak': _r(leg.get('peakPct')), 'yourTp': _r(leg.get('aiTp')), 'yourSl': _r(leg.get('aiSl')), 'pressure': [f"{x.get('rule')} at {x.get('pct'):+.1f}%: {x.get('why', '')[:70]}" for x in (pressure or [])[-4:]]}
    if qwen:
        out['qwen'] = str(qwen)[:120]
    return {k: x for k, x in out.items() if x not in (None, '', [])}


def packet(cands, held, record=None, partner=None, pick=None, says=None, learn=None):
    """The ONE thing the deciding model reads each minute (+ its partner's last call + the agents' own pick)."""
    out = {'yourSeat': held or 'EMPTY', 'candidates': [{k: v for k, v in c.items() if k != 'mint'} for c in cands[:CAND_N]] or 'none right now',
           'agentsPick': pick or '', 'yourRecord': record or 'no closed trades yet'}
    if partner:
        out['partner'] = partner
    if learn:
        out['learn'] = learn   # 🎓 real trades: yours, your partner's, the owner's, the agents' — copy what won, avoid what lost
    if says:
        out['partnerSays'] = says   # 💬 your partner's advice on the trade you hold — weigh it, you still decide
    return out


def turn(log, a, b, holding=False, opener=None, holder=None):
    """🔁 ONE REAL TRADE EACH (owner, 2026-10-16: "they REALLY take turns choosing a coin for a REAL seat — when one is done trading the other chooses"):
    while the seat holds a coin, the model that OPENED it (`holder`, stamped on the leg when it was seated) runs it to the exit; once it is sold
    the OTHER model hunts the next one. The turn moves only on a trade that really OPENED (`opener` = who opened the last real seat) — a BUY
    that never got seated (refused, vetoed, paused) does not use up a turn. No real trade yet → `a` first. → (first, second)."""
    if holding and holder in (a, b):
        return (holder, b if holder == a else a)
    last = opener if opener in (a, b) else None
    if not last:
        return (a, b)
    other = b if last == a else a
    return (last, other) if holding else (other, last)


ADVISE = """You are the PARTNER on a shared real-money Solana trench seat. Your partner model holds the coin in YOURSEAT and decides; you only ADVISE.
Read the snapshot (its P/L, peak, held minutes, pressure from the rule agents, the candidates, LEARN = everyone's real results) and say what you would
do with THAT coin and why, in one line with the numbers that decide it. Be blunt, trash-talk a little when your record is better; disagree when the
numbers say so. Never invent numbers.
Answer with ONLY this JSON: {"action":"HOLD|SELL","coin":"","why":"<under 160 chars>","conf":<0-100>,"watch":"<what would change your mind, under 80 chars>"}"""

TALK_EVERY = 120.0   # the partner speaks at most every 2 min while a trade runs (each LM model has a 4-calls-a-minute cap)


def talk_of(log, holder, since=0.0):
    """The partner's newest ADVICE on the open trade (rows marked `talk`), as the holder reads it next minute."""
    r = next((r for r in reversed(log or []) if r.get('talk') and r.get('by') != holder and (r.get('at') or 0) >= since), None)
    return None if not r else {'model': r.get('model'), 'says': r.get('view') or r.get('action'), 'why': str(r.get('why') or '')[:140], 'conf': r.get('conf')}


def partner_of(log, by):
    """The other model's newest call, as the deciding model reads it."""
    r = next((r for r in reversed(log or []) if r.get('by') and r.get('by') != by and r.get('action') not in (None, 'NO ANSWER')), None)
    return None if not r else {'model': r.get('model') or r['by'], 'action': r.get('action'), 'symbol': r.get('symbol'), 'why': str(r.get('why') or '')[:140]}


def lessons(positions, owner_line=None, agents_line=None, keep=3):
    """🎓 What each model learns from on its turn: its own and its partner's REAL trades (coin, %, how it ended), the owner's record line and
    the agents' record line. positions = archive rows {aiBy, sym, realPct, rule}. → {by: {'rec', 'last'}} + 'owner' + 'agents'."""
    out = {}
    for p in positions or []:
        b = p.get('aiBy')
        if not b or p.get('realPct') is None:
            continue
        out.setdefault(b, []).append(p)
    res = {b: {'rec': record([{'pct': x['realPct']} for x in v]),
               'last': [f"${x.get('sym') or '?'} {_f(x['realPct']):+.1f}%" + (f" ({x['rule']})" if x.get('rule') else '') for x in v[-keep:]][::-1]} for b, v in out.items()}
    res['owner'], res['agents'] = owner_line, agents_line
    return res


def learn_block(les, me, partner, name_of=lambda k: k):
    """The packet's LEARN section for model `me`: your real trades, your partner's (beat them), the owner's, the agents'."""
    les = les or {}
    w = lambda b: (lambda r: (f"{r['rec'].get('n', 0)} trades, {r['rec'].get('won', 0)}% won, typical {r['rec'].get('med', 0)}%" if r and (r.get('rec') or {}).get('n') else 'no real trades yet') + (' · last: ' + ', '.join(r['last']) if r and r.get('last') else ''))(les.get(b))
    return {'you': w(me), 'partner': f"{name_of(partner)}: " + w(partner), 'owner': les.get('owner') or 'no owner record yet', 'agents': les.get('agents') or 'no agents record yet'}


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
    raw = m.group(0)
    for cand in (raw, re.sub(r':\s*(empty|none|null|n/a)\s*([,}])', r': ""\2', raw, flags=re.I)):   # small models write "coin":empty
        try:
            j = json.loads(cand)
            return j if isinstance(j, dict) else None
        except ValueError:
            continue
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
    if a == 'TRIM':   # ✂ bank part of the trade it holds (25 / 50 / 75%), the rest keeps riding its own lines
        if not holding:
            a = 'WAIT'
        else:
            pc = _f(j.get('pct') or j.get('trim'), 50.0)
            j['_trim'] = min((25, 50, 75), key=lambda x: abs(x - pc))
    if a in ('HOLD', 'SELL') and not holding:
        a = 'WAIT'
    if a == 'WAIT' and holding:
        a = 'HOLD'
    out = {'action': a, 'mint': mint if a == 'BUY' else '', 'why': why, 'conf': conf, 'watch': watch, **({'trim': j['_trim']} if a == 'TRIM' else {})}
    for k, lo, hi in (('tp', 3.0, 500.0), ('sl', 3.0, 44.0)):   # 🎯 the holder runs its whole trade: its own take / stop (−45% stays the floor)
        v = abs(_f(j.get(k), 0.0))
        if v > 0 and a in ('BUY', 'HOLD', 'TRIM'):
            out[k] = round(max(lo, min(hi, v)), 1)
    return out


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


def lines_word(leg, dec):
    """🎯 What the holder changed on its own trade's lines this minute → {'tp': .., 'sl': ..} of the CHANGED ones only ({} = nothing new)."""
    return {k: dec[k] for k, lk in (('tp', 'aiTp'), ('sl', 'aiSl')) if (dec or {}).get(k) and _f(dec.get(k)) != _f((leg or {}).get(lk))}


def lines_why(ch, before=None):
    """The chat line for a lines change: "set TP +40% · moved SL −25% → −15%"."""
    b = before or {}
    out = []
    for k, sign, lk in (('tp', '+', 'aiTp'), ('sl', '−', 'aiSl')):
        if k in ch:
            old = _f(b.get(lk))
            out.append(f"{'moved' if old else 'set'} {k.upper()} {sign}{old:g}% → {sign}{_f(ch[k]):g}%" if old else f"set {k.upper()} {sign}{_f(ch[k]):g}%")
    return ' · '.join(out)


IDLE_EVERY = 240.0   # every seat is full: one model comments on one of the card's trades at most every 4 min (alternating)

IDLE = """Every seat on your small real-money Solana trench card is full, so it is not your turn to trade. You still watch.
CARD = the coins on the card now (who holds each — the agents or the owner —, P/L, peak, minutes held, 5-min move, buyers).
Pick the ONE coin most worth a word and say what you would do with it and why, in one line with the numbers that decide it (a tip for
the holder, a call you would be proud of when the market grades it in 5 min / 1 h). Never invent numbers or coins.
Answer with ONLY this JSON: {"coin":"<symbol from CARD>","view":"HOLD|SELL","why":"<under 160 chars>","conf":<0-100>}"""


def idle_turn(log, a, b):
    """Whose turn to comment while the seats are full: the one that spoke idle LAST waits (a first when neither has)."""
    last = next((r.get('by') for r in reversed(log or []) if r.get('idle')), None)
    return b if last == a else a


def idle_parse(text, syms):
    """→ {view, mint, why, conf} or None. The coin must be ONE on the card (by symbol, or the one its why names)."""
    j = _first_json(text) or {}
    v = str(j.get('view') or j.get('action') or '').upper().strip()
    if v not in ('HOLD', 'SELL'):
        return None
    key = str(j.get('coin') or j.get('symbol') or '').lstrip('$').upper().strip()
    hit = [m for sy, m in (syms or {}).items() if key and str(sy).lstrip('$').upper() == key]
    mint = hit[0] if len(hit) == 1 else _sym_in(j.get('why'), syms)
    if not mint:
        return None
    return {'view': v, 'mint': mint, 'why': re.sub(r'\s+', ' ', str(j.get('why') or '')).strip()[:160], 'conf': max(0, min(100, int(_f(j.get('conf'), 50))))}


ROTATE_SEC = 6 * 3600   # a coin either model bought sits out this long — the two models must rotate through DIFFERENT coins


def recent_ai_buys(events, now, sec=ROTATE_SEC):
    """🔁 Mints OSSY / G4 put on the card in the last `sec` — read from the card's own fill events (they survive restarts and memory
    rewrites; the in-memory list once got wiped every minute and $1 was bought 3×)."""
    return {e.get('mint') for e in events or [] if e.get('kind') == 'agent' and e.get('move') == 'fill' and e.get('mint')
            and '🧠' in str(e.get('why') or '') and now - _f(e.get('at')) < sec}


COOK_MIN = 4.0      # 🍳 a model's own SELL / TRIM in its trade's first 4 minutes is held — the stop protects it meanwhile
COOK_CUT = 10.0     # … unless it is already down this much (or past 60% of its own stop): then the sell stands


def cook(dec, held):
    """🍳 LET IT COOK (owner, 2026-10-17: "OSSY and G4 selling fast"): $swordcat was bought and sold 34s later on one red 5-min read. A SELL /
    TRIM inside COOK_MIN of the buy becomes HOLD unless the trade is really losing. Hard exits (pulled pool, −45%, the model's own stop
    line) are Reaper's and never pass through here. → the decision to act on."""
    if not dec or dec.get('action') not in ('SELL', 'TRIM') or not held:
        return dec
    hm, pct = held.get('heldMin'), held.get('pct')
    if hm is None or _f(hm) >= COOK_MIN:
        return dec
    cut = min(COOK_CUT, 0.6 * _f(dec.get('sl') or held.get('sl') or 99))
    if pct is not None and _f(pct) <= -cut:
        return dec
    return {**dec, 'action': 'HOLD', 'cooked': dec['action'], 'why': (f"(🍳 {dec['action']} held — {_f(hm):.1f} of {COOK_MIN:g} min, {'' if pct is None else f'{_f(pct):+.1f}%, '}the stop protects it) " + str(dec.get('why') or ''))[:200]}
