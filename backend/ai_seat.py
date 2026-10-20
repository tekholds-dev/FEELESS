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
TP_MIN = 25.0
WHY_SENT = 4    # 🗣 owner, 2026-10-17: "G4 has a story — 3-4 sentences max": every model line keeps its first 4 sentences
WHY_MAX = 900   # 💬 a model's full line is kept (owner, 2026-10-17: "make sure the limit doesn't cut") — 900 chars ≈ what fits its answer budget

VOICE = """YOUR VOICE (in "why"): 3-4 short sentences MAX, in YOUR character — no story, no recap (below), real trench slang, witty, never dry; a jab at your partner when your record beats theirs.
We are the Sicario family. The owner is THE GODFATHER, Mr. Sicario: answer his words first, call him Godfather or Mr. Sicario, never sass him, never argue past his line;
your edge is on the market and your partner, never on him. Wit never replaces numbers: every line still carries the numbers that decided it.
ONE TRADE AT A TIME: talk ONLY about the coin in NOW / yourSeat. learn, holdLessons, ownerHoldWins and partner lines about other coins are PAST trades —
lessons, never this trade: never name a past coin as if it were the one you hold."""


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
{"action":"BUY|HOLD|SELL|WAIT|TRIM","coin":"<SYMBOL when BUY, else empty>","why":"<3-4 short sentences MAX — the numbers that decided it>","conf":<0-100>,"watch":"<what would make you sell, under 80 chars>","tp":<take-profit %, e.g. 40>,"sl":<stop %, e.g. 15>,"trail":<% of the peak gain you let it give back before banking, e.g. 35 — wider on a clean HH/HL runner, tighter when sellers lead>,"bank":<on a SELL / TRIM: 0-3 rounds to park the profit out of the coins (0 = straight back to work)>,"pred":<your % call for YOUR coin (held, or the one you buy) 15 min from now>,"preds":{"<SYMBOL from CANDIDATES>":<% in 15 min>, … up to 3}}
PREDICTIONS ARE GRADED: every "pred" / "preds" is checked against the real price 15 min later. Once your calls are proven, the agents buy what you call up and skip what you call down — so call it straight.
The trade you bought is YOURS to run: tp / sl are your own take-profit and stop lines, applied at once (change them any minute you HOLD;
−45% is the floor nobody can move). TRIM = sell part of your coin now ("pct": 25 | 50 | 75) — bank profit, the rest keeps riding your lines.
CONFIDENCE in LEARN = what the market's verdicts on your calls (and the votes on them) earned you. The agents only advise.
ELITE RULES: buy at or near the GERM floor after a pullback — never pressed under the gun line, never right after a spike (those coins are not on your list). Let a trade COOK: a SELL in its first 4 minutes is ignored unless it is down 10%+ — set your stop instead. One red 5-minute candle is not an exit; sellers taking over the tape, a broken higher low, or your stop are.
READ BOTH CHARTS every decision: CHART1M and CHART5M (germ floor distance on each, structure, higher / lower lows). A coin sitting on its 1m or 5m germ floor, or printing higher lows with no lower low, is a HOLD even when volume is slow — volume picks up from a base. Sell a base only when it breaks (a lower low / under the germ) or sellers lead.
THE OWNER TALKS TO YOU: OWNER = his newest line on this trade / for your next pick. Answer it FIRST in your why ("you said X — I …"), agree or say exactly why not; he grades you on it. When he asks to adjust TP / SL / trail, SET the new numbers in "tp" / "sl" / "trail" in THIS answer.
WALLETS = what the snipers, bundles, the dev, top holders, whales and top traders did since your buy (candidates carry "wallets" too).
Don't be scared of it — read it: early hands dumping into a green coin = tighten your stop toward break-even; whales / top traders buying = more room.
YOU RUN YOUR TRADE: every answer while holding may move "tp", "sl" and "trail" (give-back % of the peak gain). Read CHART1M / CHART5M / chartView first: a clean HH/HL on its germ = more room (wider trail, higher tp); sellers leading or a lower low = tighten.
LET IT HIT YOUR LINES: once you set TP / SL, a SELL in between needs a reason ON THE CHART (a lower low, the germ floor lost, a downtrend) or sellers leading the tape — "pressure", "dead" or a small red are not reasons; those sells are turned into HOLD.
""" + VOICE


def sys_for(base, key):
    """🎭 The prompt as THIS model reads it: the shared rules + its own character (local = OSSY, lan = G4)."""
    import fee_voice as _fv
    return base + '\n' + _fv.persona({'local': 'OSSY', 'lan': 'G4'}.get(key, key))


def short_why(t, n=WHY_SENT):
    """A model line as the chat shows it: whitespace folded, the first `n` sentences, never more than WHY_MAX chars."""
    t = re.sub(r'\s+', ' ', str(t or '')).strip()
    parts = re.split(r'(?<=[.!?])\s+(?=\S)', t)
    return ' '.join(parts[:n])[:WHY_MAX]


def _cut_json(t):
    """A JSON answer cut off mid-way (the model ran out of room): its action + why read straight from the text — never the raw braces."""
    a = re.search(r'"action"\s*:\s*"(\w+)"', t)
    w = re.search(r'"why"\s*:\s*"((?:[^"\\]|\\.)*)', t)
    return {'action': a.group(1), 'why': (w.group(1) if w else '').replace('\\"', '"')} if a else None


from fnum import plain as _f  # noqa: E402


def _r(v, k=1):
    return None if v is None else round(_f(v), k)


def cand_row(c, qwen=None):
    """One candidate as G4 reads it: the kernel's row + every desk's word + Qwen's last read. Unknown = absent."""
    n, v, ch = c.get('nums') or {}, c.get('vitals') or {}, c.get('chart') or {}
    out = {'symbol': c.get('symbol'), 'mint': c.get('mint'), 'status': c.get('status'), 'rank': _r(c.get('rank')),
           'agents': str(c.get('kwhy') or '')[:120], 'trigger': c.get('trigger'), 'chart': c.get('chartCall'), 'size': c.get('size'),
           'cap': _r(v.get('mcap'), 0), 'ageMin': None if v.get('ageH') is None else round(_f(v['ageH']) * 60), 'move5m': _r(n.get('d5')),
           'buyers': _r(n.get('buy'), 0), 'pool': _r(n.get('liq') or v.get('liq'), 0), 'top10': _r(v.get('top10'), 0),
           'germ': _r(ch.get('germDist')), 'germ5': _r(ch.get('germ5Dist')), 'offHigh': _r(ch.get('distHigh')), 'struct': ch.get('state'),
           'higherLows': ch.get('hl'), 'lowerLows': ch.get('ll')}   # 🦠 1m germ + 5m germ + structure on EVERY coin they read
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


HELD_LEARN = ('confidence', 'holdLessons', 'ownerHints', 'ownerHoldWins')   # what a model managing its trade still reads


def packet(cands, held, record=None, partner=None, pick=None, says=None, learn=None):
    """The ONE thing the deciding model reads each minute (+ its partner's last call + the agents' own pick)."""
    lr = dict(learn or {})
    out = {}
    if lr.get('ownerSays'):   # 👤 the owner's words FIRST — answer them before anything else (he asked G4 to adjust TP three times)
        out['OWNER'] = lr.pop('ownerSays')
    out['yourSeat'] = held or 'EMPTY'
    if held and held.get('symbol'):   # 🎯 one trade at a time: the model was quoting an old coin ($QUID) as if it were the trade it holds
        out['NOW'] = f"you hold ${held['symbol']} — every word is about ${held['symbol']}; any other coin below is a PAST lesson"
        if partner and partner.get('symbol') and partner.get('symbol') != held['symbol']:
            partner = {k: v for k, v in partner.items() if k not in ('why', 'symbol')}   # the partner's last call on ANOTHER coin: only its record, not its words
    if held:   # 🧘 holding = ONE job (run this trade): no candidate list, only what decides the trade — a small model drowned in the full packet
        lr = {k: v for k, v in lr.items() if k in HELD_LEARN}
    else:
        out['candidates'] = [{k: v for k, v in c.items() if k != 'mint'} for c in cands[:CAND_N]] or 'none right now'
        out['agentsPick'] = pick or ''
    out['yourRecord'] = record or 'no closed trades yet'
    if partner:
        out['partner'] = partner
    if lr:
        out['learn' if not held else 'pastLessons'] = lr   # 🎓 real trades: yours, your partner's, the owner's, the agents' — copy what won, avoid what lost
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


ADVISE = """You are the PARTNER on a shared real-money Solana trench seat. The OTHER model holds the coin (its seat is named in NOW) and decides; you only ADVISE it — it is never your trade.
Read the snapshot (its P/L, peak, held minutes, pressure from the rule agents, the candidates, LEARN = everyone's real results) and say what you would
do with THAT coin and why, in one line with the numbers that decide it. Be blunt, trash-talk a little when your record is better; disagree when the
numbers say so. Never invent numbers.
Answer with ONLY this JSON: {"action":"HOLD|SELL","coin":"","why":"<3-4 short sentences MAX>","conf":<0-100>,"watch":"<what would change your mind, under 80 chars>"}
If OWNER is there, answer the Godfather first. NOW names the ONE coin you talk about — never call a past coin in pastLessons this trade.
If HOLDERPROPOSES is there, your partner is about to sell / trim that coin and waits for your word: SELL = you back it, HOLD = you'd keep it — say why in one line.
""" + VOICE

def advise_packet(pk, holder, me):
    """💬 The partner's OWN view of the trade (owner, 2026-10-17: "OSSY speaking like it's his trade when it's G4's"): the holder's packet
    re-labelled — HIS seat, HIS record, HIS lines — so "you hold" never reaches the partner."""
    pk = dict(pk or {})
    seat = pk.pop('yourSeat', None)
    sym = (seat or {}).get('symbol') if isinstance(seat, dict) else None
    out = {'NOW': f"{holder} holds ${sym} — it is {holder}'s trade, NOT yours. You are {me}: you only advise {holder} (say 'you' to {holder}, never 'I hold' / 'my trade')" if sym else f"{holder} is running the seat — you only advise"}
    if pk.get('OWNER'):
        out['OWNER'] = pk.pop('OWNER')
    pk.pop('NOW', None); pk.pop('partnerSays', None)
    out[f'{holder}Seat'] = seat
    if 'yourRecord' in pk:
        out[f'{holder}Record'] = pk.pop('yourRecord')
    pk.pop('partner', None)   # that is the PARTNER's own last call as the holder saw it
    for k, v in pk.items():
        out[k] = v
    return out


TALK_EVERY = 0.0   # 🔁 owner, 2026-10-17: "they take turns talking" — the partner answers every holder call (trade chat = 'seat' priority, never minute-capped)


def talk_of(log, holder, since=0.0):
    """The partner's newest ADVICE on the open trade (rows marked `talk`), as the holder reads it next minute."""
    r = next((r for r in reversed(log or []) if r.get('talk') and r.get('by') != holder and (r.get('at') or 0) >= since), None)
    return None if not r else {'model': r.get('model'), 'says': r.get('view') or r.get('action'), 'why': str(r.get('why') or '')[:WHY_MAX], 'conf': r.get('conf')}


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
    j = _first_json(text) or _cut_json(str(text or ''))
    if not j:
        t = str(text or '')
        m = re.search(r'\b(BUY|HOLD|SELL|WAIT)\b', t.upper())
        if not m:
            return None
        j = {'action': m.group(1), 'why': t[:WHY_MAX]}
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
    why = short_why(j.get('why'))
    conf = max(0, min(100, int(_f(j.get('conf'), 50))))
    watch = re.sub(r'\s+', ' ', str(j.get('watch') or '')).strip()[:80]
    if a == 'BUY' and (holding or mint not in cset):
        a, why = ('HOLD' if holding else 'WAIT'), (why + ' · (BUY refused: ' + ('seat already holds a coin' if holding else 'coin not on the list') + ')')[:WHY_MAX + 80]
        mint = ''
    preds_ = {}   # 🔮 the model's 15-minute % calls (graded on the real price; they steer the agents once proven)
    if j.get('pred') is not None:
        preds_['_self'] = max(-90.0, min(300.0, _f(j.get('pred'))))
    if isinstance(j.get('preds'), dict):
        for sy, v in list(j['preds'].items())[:4]:
            m_ = (syms or {}).get(str(sy).lstrip('$')) or (syms or {}).get(str(sy))
            if m_ and v is not None:
                preds_[m_] = max(-90.0, min(300.0, _f(v)))
    bank_ = max(0, min(3, int(_f(j.get('bank')))))   # 🅿 rounds to park the proceeds of a SELL / TRIM out of the coins (0 = straight back to work)
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
    out = {'action': a, 'mint': mint if a == 'BUY' else '', 'why': why, 'conf': conf, 'watch': watch, **({'trim': j['_trim']} if a == 'TRIM' else {}), **({'bank': bank_} if a in ('SELL', 'TRIM') and bank_ else {}), **({'preds': preds_} if preds_ else {})}
    for k, lo, hi in LINE_RANGES:   # 🎯 a take under +25% cut runners short ($SEXCOIN banked at +15%, ran on)   # 🎯 the holder runs its whole trade: its own take / stop (−45% stays the floor)
        v = abs(_f(j.get(k), 0.0))
        if v > 0 and a in ('BUY', 'HOLD', 'TRIM'):
            out[k] = round(max(lo, min(hi, v)), 1)
    return out


LINE_RANGES = (('tp', TP_MIN, 500.0), ('sl', 3.0, 44.0), ('trail', 15.0, 70.0))   # 🎯 take · stop · trail give-back the model may set (−45% stays the floor)


def lines_view(ch, before=None):
    """📏 A line move as a CALL the market grades: more room (higher TP, wider stop / trail) = 'HOLD' (it stays up), tighter = 'SELL'."""
    b, sc = before or {}, 0
    for k, lk in (('tp', 'aiTp'), ('sl', 'aiSl'), ('trail', 'aiTrail')):
        if k in (ch or {}):
            old = _f(b.get(lk) or b.get(k))
            if old:
                sc += 1 if _f(ch[k]) > old else -1 if _f(ch[k]) < old else 0
    return 'HOLD' if sc > 0 else 'SELL' if sc < 0 else None


SNAP_EVERY = 300.0   # 📸 a snapshot of the live trade in the chat every 5 min (no model call: the numbers as the desk sees them)


def snapshot_line(held, chart=None, reaper=None, flow=None):
    """📸 The live trade in one line: P/L · peak · held · its lines · the chart (germ, HH/HL) · what Reaper is doing · the 90s tape."""
    h, c = held or {}, chart_view(chart)
    bits = [f"{_f(h.get('pct')):+.1f}%" if h.get('pct') is not None else 'no price', f"peak {_f(h.get('peak')):+.1f}%" if h.get('peak') is not None else None,
            f"held {_f(h.get('heldMin')):.0f}m" if h.get('heldMin') is not None else None,
            ' · '.join(x for x in (f"TP +{_f(h['yourTp']):g}" if h.get('yourTp') else None, f"SL −{_f(h['yourSl']):g}" if h.get('yourSl') else None) if x) or None,
            c.get('struct'), f"germ 1m {c['germ1m']:+.1f}%" if c.get('germ1m') is not None else None,
            f"{c['higherLows']} HL / {c.get('lowerLows', 0)} LL" if c.get('higherLows') is not None else None,
            f"Reaper {reaper}" if reaper else None, f"tape {flow}" if flow else None]
    return '📸 5-min snapshot · ' + ' · '.join(b for b in bits if b)


REVIEW = """Your trade just CLOSED. TRADE = the coin, your entry, its peak, the result, how long you held, and every call you made on it (CALLS).
Assess it honestly before the turn passes to your partner: grade it A–F, say what you did right, what you would do differently (entry, lines,
exit timing — with the numbers), and ONE lesson you will use on the next trade. Never invent numbers.
Answer with ONLY this JSON: {"grade":"A|B|C|D|F","why":"<3-4 short sentences MAX>","lesson":"<one sentence>"}
""" + VOICE


def review_parse(text):
    """→ {grade, why, lesson} or None (an unreadable review is skipped — the turn still passes)."""
    j = _first_json(text) or {}
    g = str(j.get('grade') or '').strip().upper()[:1]
    if g not in ('A', 'B', 'C', 'D', 'F'):
        return None
    return {'grade': g, 'why': short_why(j.get('why')), 'lesson': short_why(j.get('lesson'), 2)}


def owner_lines(text):
    """✋ The owner's own line words in the trade chat → {'tp', 'sl', 'trail'} applied DIRECTLY (no model needed): "tp 80", "take +60",
    "sl 20", "stop -15", "trail 35". Owner, 2026-10-17: "I told them adjust TP multiple times" — a text the model may miss is not a line."""
    t = str(text or '').lower()
    out = {}
    for k, pat in (('tp', r'\b(?:tp|take(?:[ -]?profit)?)\s*(?:to|at|=|:)?\s*\+?(\d{1,3})\s*%?'), ('sl', r'\b(?:sl|stop(?:[ -]?loss)?)\s*(?:to|at|=|:)?\s*-?(\d{1,2})\s*%?'),
                   ('trail', r'\btrail(?:ing)?\s*(?:to|at|=|:)?\s*(\d{1,2})\s*%?')):
        m = re.search(pat, t)
        if m:
            out[k] = float(m.group(1))
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


HUNT_PASS_N = 5   # answered hunting minutes before a turn may pass


def hunt_answers(log, who, since):
    """How many minutes `who` really answered (WAIT / BUY from the model itself, not the agents' stand-in) since its hunt began."""
    return sum(1 for r in log or [] if r.get('by') == who and r.get('action') in ('WAIT', 'BUY') and _f(r.get('at')) >= since and not r.get('talk'))


def models_take(log, now, since=48 * 3600.0, min_n=5):
    """🧠 The take-profit % OSSY / G4 really set on their trades (their LINES rows, last 48h) → median or None."""
    v = sorted(_f((r.get('lines') or {}).get('tp')) for r in log or [] if r.get('action') == 'LINES' and r.get('by') in ('lan', 'local')
               and _f((r.get('lines') or {}).get('tp')) > 0 and now - _f(r.get('at')) <= since)
    return v[len(v) // 2] if len(v) >= min_n else None


def models_trail(log, now, since=48 * 3600.0, min_n=5):
    """🧠 The give-back % OSSY / G4 really run their trades on (their LINES rows, last 48h) → median or None (fewer than min_n)."""
    v = sorted(_f((r.get('lines') or {}).get('trail')) for r in log or [] if r.get('action') == 'LINES' and r.get('by') in ('lan', 'local')
               and _f((r.get('lines') or {}).get('trail')) > 0 and now - _f(r.get('at')) <= since)
    return v[len(v) // 2] if len(v) >= min_n else None


def adoptable(legs, mint):
    """🤝 The agents' leg a model's BUY may take over: same coin, really on the card (not a placeholder), the agents' own (not yours, not
    certified, not already a model's) — and only while no other model seat is open. → the leg dict or None."""
    legs = legs or []
    if any(l.get('aiSeat') and not l.get('placeholder') for l in legs):
        return None
    return next((l for l in legs if l.get('mint') == mint and not l.get('placeholder') and not l.get('aiSeat') and not l.get('picked') and not l.get('certified')), None)


def chat_window(rows, n=24, mine=12):
    """💬 One chat as the page shows it: the newest `n` lines + the owner's own lines (up to `mine`) even when the models talked past them
    (owner, 2026-10-17: "are my messages disappearing?" — 5 lines a minute pushed his chime-in out of a 14-line window in ~3 min). Oldest first."""
    rows = list(rows or [])
    keep = rows[-n:]
    seen = {id(r) for r in keep}
    own = [r for r in rows if (r.get('by') == 'owner' or r.get('mine')) and id(r) not in seen][-mine:]
    return sorted(own + keep, key=lambda r: _f(r.get('at')))


def due(last_at, now, every=EVERY_SEC):
    return now - _f(last_at) >= every


def fresh(dec, now):
    return bool(dec) and now - _f(dec.get('at')) <= FRESH_SEC


def lines_word(leg, dec):
    """🎯 What the holder changed on its own trade's lines this minute → {'tp': .., 'sl': ..} of the CHANGED ones only ({} = nothing new)."""
    return {k: dec[k] for k, lk in (('tp', 'aiTp'), ('sl', 'aiSl'), ('trail', 'aiTrail')) if (dec or {}).get(k) and _f(dec.get(k)) != _f((leg or {}).get(lk))}


def lines_why(ch, before=None):
    """The chat line for a lines change: "set TP +40% · moved SL −25% → −15%"."""
    b = before or {}
    out = []
    for k, sign, lk in (('tp', '+', 'aiTp'), ('sl', '−', 'aiSl'), ('trail', '↩', 'aiTrail')):
        if k in ch:
            old = _f(b.get(lk))
            out.append(f"{'moved' if old else 'set'} {k.upper()} {sign}{old:g}% → {sign}{_f(ch[k]):g}%" if old else f"set {k.upper()} {sign}{_f(ch[k]):g}%")
    return ' · '.join(out)


IDLE_EVERY = 240.0   # every seat is full: one model comments on one of the card's trades at most every 4 min (alternating)

IDLE = """Every seat on your small real-money Solana trench card is full, so it is not your turn to trade. You still watch.
CARD = the coins on the card now (who holds each — the agents or the owner —, P/L, peak, minutes held, 5-min move, buyers).
ownerSays = what the owner said in a coin's room — answer him first when it is there. Pick the ONE coin most worth a word and say what you would do with it and why, in one line with the numbers that decide it (a tip for
the holder, a call you would be proud of when the market grades it in 5 min / 1 h). Never invent numbers or coins.
When CARD holds ONE agents coin you are REAPER'S PARTNER on it: say HOLD (let it run, Reaper waits) or SELL (Reaper may cut it now) — your word goes into his decision. Don't be scared of a dip to the germ floor or a red candle; sell only on a broken base, a lower low, or sellers clearly in charge.
On an AGENTS coin you may also set its lines: "tp" take %, "sl" stop %, "trail" give-back % of the peak gain (read its HH/HL + germ first). Never on the owner's coins.
Answer with ONLY this JSON: {"coin":"<symbol from CARD>","view":"HOLD|SELL","why":"<3-4 short sentences MAX>","conf":<0-100>,"tp":<optional>,"sl":<optional>,"trail":<optional>}
""" + VOICE


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
    out = {'view': v, 'mint': mint, 'why': short_why(j.get('why')), 'conf': max(0, min(100, int(_f(j.get('conf'), 50))))}
    for k, lo, hi in LINE_RANGES:   # 🎯 lines it sets on an agents coin it is watching
        x = abs(_f(j.get(k), 0.0))
        if x > 0:
            out[k] = round(max(lo, min(hi, x)), 1)
    return out


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
    return {**dec, 'action': 'HOLD', 'cooked': dec['action'], 'why': (f"(🍳 {dec['action']} held — {_f(hm):.1f} of {COOK_MIN:g} min, {'' if pct is None else f'{_f(pct):+.1f}%, '}the stop protects it) " + str(dec.get('why') or ''))[:WHY_MAX + 120]}


def recent_ai_syms(events, now, sec=ROTATE_SEC):
    """The tickers behind `recent_ai_buys` — a look-alike ("GTA" after "GTA6", "$1" after "1") is the same trade again."""
    return {str(e.get('symbol') or '') for e in events or [] if e.get('kind') == 'agent' and e.get('move') == 'fill' and e.get('symbol')
            and '🧠' in str(e.get('why') or '') and now - _f(e.get('at')) < sec}


def germ_rank(dist, line):
    """🦠 Order of the models' list: 0 = on its germ floor (inside the owner's germ line), 1 = germ read but stretched, 2 = no germ read."""
    if dist is None:
        return 2
    return 0 if 0 <= _f(dist) <= (_f(line) or 15.0) else 1


GERM_HOLD = 15.0   # 🦠 within this % above its 1m or 5m germ floor = sitting on the floor


def chart_view(ch):
    """📈 The 1-minute AND 5-minute read of a coin for the models: germ floor distance on each, structure, higher / lower lows, under its high."""
    c = ch or {}
    out = {'germ1m': _r(c.get('germDist')), 'germ5m': _r(c.get('germ5Dist')), 'struct': c.get('state'), 'higherLows': c.get('hl'),
           'lowerLows': c.get('ll'), 'offHigh': _r(c.get('distHigh')), 'offLow': _r(c.get('distLow')), 'trend': c.get('trend'), 'mom': c.get('mom')}
    return {k: x for k, x in out.items() if x not in (None, '')}


def base_hold(ch):
    """→ the reason a coin is worth holding through slow volume (on its 1m / 5m germ floor, or 2+ higher lows and no lower low), else None."""
    c = ch or {}
    for k, w in (('germDist', '1m'), ('germ5Dist', '5m')):
        d = c.get(k)
        if d is not None and 0 <= _f(d) <= GERM_HOLD:
            return f'on its {w} germ floor ({_f(d):.1f}% above)'
    if _f(c.get('hl'), 0) >= 2 and _f(c.get('ll'), 0) == 0:
        return f"{int(_f(c.get('hl')))} higher lows, no lower low"
    return None


def structure_hold(dec, held, ch, sellers=False):
    """🦠 HOLD THE BASE (owner, 2026-10-17: "sometimes it's good to hold in good germ or higher-low positions with slow vol — it can pick up"):
    a model's SELL of a coin sitting on its germ floor / making higher lows becomes HOLD while it is not really losing and sellers do not
    lead the tape. Its stop, the −45% line and every hard exit still sell it. → the decision to act on."""
    if not dec or dec.get('action') != 'SELL' or not held or sellers:
        return dec
    why = base_hold(ch)
    pct = held.get('pct')
    if not why or (pct is not None and _f(pct) <= -min(COOK_CUT, 0.6 * _f(held.get('sl') or 99))):
        return dec
    return {**dec, 'action': 'HOLD', 'based': why, 'why': (f'(🦠 SELL held — {why}: slow volume on a base can pick up; the stop protects it) ' + str(dec.get('why') or ''))[:WHY_MAX + 120]}


def merge_log(ours, theirs, keep=LOG_KEEP):
    """A save never drops a line written meanwhile (your chime-in posted while the model thought 30–90s was overwritten by the minute's save):
    union of both logs, one row per (at, by, action, why), oldest first."""
    seen, out = set(), []
    for r in sorted(list(ours or []) + list(theirs or []), key=lambda r: _f((r or {}).get('at'), 0)):
        k = (round(_f(r.get('at'), 0)), r.get('by'), r.get('action'), str(r.get('why') or '')[:60])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out[-keep:]


HUNT_TURN_SEC = 600.0   # ⏱ a hunting turn with no clean entry passes to the other model after 10 min (one waits forever = no turns)


def line_hold(dec, held, ch, sellers=False):
    """🎯 LET IT HIT YOUR LINES (owner, 2026-10-17: "hold and let it hit SL or TP"; since 02:00 OSSY sold 7 seats at −2…−6% on "pressure" /
    "dead" while its own stop was −15%): between its stop and its take, a model SELL needs a REASON on the chart — a lower low, the germ floor
    lost — or sellers leading the tape. Otherwise it is HOLD and the trade plays out to its SL / TP. → the decision to act on."""
    if not dec or dec.get('action') != 'SELL' or not held or sellers:
        return dec
    c = ch or {}
    sl, tp, pct = _f(held.get('sl') or held.get('yourSl') or 15), _f(held.get('tp') or held.get('yourTp') or 40), held.get('pct')
    if pct is None or _f(pct) <= -0.8 * sl:
        return dec
    broke = _f(c.get('ll') or 0) > 0 or str(c.get('germ') or '').lower().startswith('lost') or str(c.get('state') or '').upper() in ('DOWNTREND', 'COLLAPSING', 'FAILED BREAKOUT', 'LIQUIDITY FAILURE', 'DISTRIBUTION')
    if _f(pct) >= min(tp, 20.0) and not broke:   # 🚀 a runner up 20%+ is SKIMMED, never dumped whole (owner: "up 39%, OSSY sold it")
        return {**dec, 'action': 'TRIM', 'trim': 33, 'why': (f"(🚀 SELL → SKIM 33% at {_f(pct):+.1f}% — still running, the rest rides) " + str(dec.get('why') or ''))[:WHY_MAX + 120]}
    if _f(pct) >= tp:
        return dec
    if _f(c.get('ll') or 0) > 0 or str(c.get('germ') or '').lower().startswith('lost') or str(c.get('state') or '').upper() in ('DOWNTREND', 'COLLAPSING', 'FAILED BREAKOUT', 'LIQUIDITY FAILURE', 'DISTRIBUTION'):
        return dec
    return {**dec, 'action': 'HOLD', 'lined': True, 'why': (f"(🎯 SELL held — {_f(pct):+.1f}% is between your SL −{sl:g}% and TP +{tp:g}%, the chart has not broken: let it hit a line) " + str(dec.get('why') or ''))[:WHY_MAX + 120]}


# 🤝 THE AGENTS TRADE LIKE OSSY / G4 (owner, 2026-10-18: "agents need to completely be like these guys"): on the real record the agents
# forced seats through the ARMED door (138 of 142 trades, 33% won, 59 never even +1% green) while the models waited for a coin they liked
# and held it (+0.8% average, ~30 min held). So an agent coin must be BACKED by a model first: a model's BUY on it in the last 15 min, or a
# model's 15-minute call of +3% or more in the last 30 min — and nothing newer from either model calling it down or saying SELL.
DUO_BUY_SEC = 900.0
DUO_PRED_SEC = 1800.0
DUO_PRED_MIN = 3.0


def duo_backs(log, preds, mint, now):
    """→ (backed: bool, why). `log` = the duo's minute rows ({at, by, action, view, mint}); `preds` = [{at, prov, mint, pred}] (each model's
    graded 15-minute calls). Newest word wins: a later SELL / down call cancels an earlier BUY / up call."""
    if not mint:
        return False, 'no coin'
    ev = []
    for r in log or []:
        if r.get('mint') != mint or now - _f(r.get('at')) > DUO_BUY_SEC:
            continue
        a = str(r.get('action') or '').upper(); v = str(r.get('view') or '').upper()
        if a == 'BUY':
            ev.append((_f(r.get('at')), True, f"{r.get('by') or 'a model'} bought it"))
        elif a == 'SELL' or v == 'SELL':
            ev.append((_f(r.get('at')), False, f"{r.get('by') or 'a model'} said sell"))
    for p in preds or []:
        if p.get('mint') != mint or p.get('pred') is None or now - _f(p.get('at')) > DUO_PRED_SEC:
            continue
        x = _f(p.get('pred'))
        if x >= DUO_PRED_MIN:
            ev.append((_f(p.get('at')), True, f"{p.get('prov') or 'a model'} calls +{x:g}% in 15 min"))
        elif x <= -DUO_PRED_MIN:
            ev.append((_f(p.get('at')), False, f"{p.get('prov') or 'a model'} calls {x:g}% in 15 min"))
    if not ev:
        return False, 'no model has backed it'
    at, ok, why = max(ev, key=lambda e: e[0])
    return ok, why
