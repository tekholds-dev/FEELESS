"""📜 THE DECISION TAPE — the kernel's own change events, in order (owner, 2026-10-12: "use real kernel / Archivist events, no fake AI
thoughts, no duplicate history engine"). A line exists only because something REAL changed: a role's opinion on a mint moved, the keeper's
ledger recorded an order, Reaper's ruling on a position changed, the Judge filed a review. Nothing is written on a timer and an
unchanged opinion writes nothing (so a quiet market is a quiet tape, and the page's pulse only fires on a real event id).

`diff` is pure: previous decision vs the new one (+ the MintState events that caused the re-judge) → the lines. `Tape` is a bounded ring
with monotonic ids; the service forwards new rows to the hub as `decision` deltas. It is a view of what the kernel just did — the
Archivist's hash-chained archive remains the record."""
KEEP = 400
SNAP = 30          # rows in the page's snapshot (the stream carries the rest as they happen)   # 2026-10-14: 40 → 30 for office-payload headroom (the live stream still sends every row)
INSIDE = ('READY', 'CONTENDING', 'ORDER_PENDING', 'HELD', 'EXIT_PENDING')
SEV_WORD = {'HARD_VETO': 'HARD VETO', 'STRONG_WARNING': 'STRONG WARNING', 'WARNING': 'WARNING', 'INFO': 'INFO'}
SEV_RANK = {'HARD_VETO': 3, 'STRONG_WARNING': 2, 'WARNING': 1, 'INFO': 0}
SURGE_PACE = 1.5        # 5-min volume running ≥ 1.5× the hour's pace, price up
SURGE_EVERY = 300.0     # at most one SURGE line per coin per 5 minutes
AGENTS = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge', 'kernel', 'owner')


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def _money(v):
    v = _f(v)
    return f"${v / 1e6:.2f}M" if v >= 1e6 else f"${v / 1e3:.1f}K" if v >= 1e3 else f"${v:.0f}"


def diff(prev, cur, ms, events=(), now=0.0, owner=False):
    """→ [(agent, action, why, key)] — the REAL changes between two decisions on one mint. `key` de-dupes a repeated line.
    A coin that is not (and was not) a candidate writes nothing — unless the owner asked for its review."""
    if not cur:
        return []
    ps, cs = (prev or {}).get('status'), cur.get('status')
    inside, was = cs in INSIDE, ps in INSIDE
    if not (inside or was or owner):
        return []
    out = []
    op, pop = cur.get('opinions') or {}, (prev or {}).get('opinions') or {}
    m = (ms or {}).get('market') or {}
    ev = set(events or ())
    t = op.get('tally') or {}
    if inside and not was:
        out.append(('tally', 'CANDIDATE', f"{t.get('fresh') or 'age ?'} · {_money(t.get('vpm'))}/min · {t.get('sources') or 0} source(s)", 'cand'))
    elif 'volume' in ev and _f(m.get('pace')) >= SURGE_PACE and _f(m.get('move5m')) > 0 and inside:
        out.append(('tally', 'SURGE', f"5-min volume {_money(m.get('volume5m'))} at {_f(m.get('pace')):.1f}× the hour's pace, {_f(m.get('move5m')):+.1f}%", f"surge:{int(_f(now) // SURGE_EVERY)}"))
    c = (ms or {}).get('chain') or {}
    if 'holders' in ev and c.get('holderStatus') == 'READY':
        safe = c.get('holderSafe')
        out.append(('sherlock', 'HOLDERS READ', ('scan passed' if safe else 'scan flagged' if safe is False else 'read') + (f" · top-10 {_f(c.get('top10')):.0f}%" if c.get('top10') is not None else ''), f"holders:{safe}"))
    if 'wallets' in ev and c.get('earlyWallets') not in (None, 'PENDING', 'UNKNOWN'):
        out.append(('sherlock', 'EARLY WALLETS', f"{c.get('earlyWallets')}" + (f" — {c.get('pressWhy')}" if c.get('pressWhy') else ''), f"wallets:{c.get('earlyWallets')}"))
    if 'research' in ev and ((ms or {}).get('research') or {}).get('status') == 'READY':
        out.append(('sherlock', 'RESEARCH', 'site / X found', 'research'))
    tr, ptr = op.get('trigger') or {}, pop.get('trigger') or {}
    if tr.get('state') and tr.get('state') != ptr.get('state') and (inside or was or owner):
        out.append(('trigger', tr['state'], f"{tr.get('narrative') or ''} — {tr.get('why') or ''}".strip(' —'), f"trig:{tr['state']}"))
    dv, pdv = op.get('devil') or {}, pop.get('devil') or {}
    had = {o for o, _s, _w in (pdv.get('objections') or [])}
    new = sorted([(o, s, w) for o, s, w in (dv.get('objections') or []) if o not in had], key=lambda x: -SEV_RANK.get(x[1], 0))
    if new:
        o, s, w = new[0]
        out.append(('devil', SEV_WORD.get(s, s), str(w), f"dev:{o}:{s}"))
    elif had and not (dv.get('objections') or []):
        out.append(('devil', 'CLEARED', 'nothing against it now', 'dev:clear'))
    wa, pwa = op.get('warden') or {}, pop.get('warden') or {}
    if cs == 'READY' and (ps != 'READY' or wa.get('size') != pwa.get('size')):
        out.append(('warden', f"SIZE ×{_f(wa.get('size')):g}", str(wa.get('why') or 'full size'), f"size:{wa.get('size')}"))
    if cs != ps:
        why = cur.get('why') or ''
        if cs == 'READY':
            out.append(('kernel', 'READY', f"rank {_f(cur.get('rank')):g} — {why}", 'st:READY'))
        elif cs == 'ORDER_PENDING':
            out.append(('courier', 'ORDER PENDING', 'seat created — the keeper is buying; the ledger says when it is held', 'st:ORDER_PENDING'))
        elif cs == 'HELD' and ps != 'EXIT_PENDING':
            out.append(('kernel', 'HELD', 'on the card — Reaper has it', 'st:HELD'))
        elif cs == 'CONTENDING' and ps == 'READY':
            out.append(('kernel', 'BACK TO CONTENDING', why, 'st:CONTENDING'))
        elif cs == 'TRACKING' and was:
            out.append(('kernel', 'DROPPED TO TRACKING', why, 'st:TRACKING'))
        elif cs == 'CLOSED' and was:
            out.append(('kernel', 'CLOSED', why or 'left the card', 'st:CLOSED'))
    return out


class Tape:
    def __init__(self, keep=KEEP):
        self.keep = int(keep)
        self.rows = []
        self.seq = 0
        self.last = {}     # (mint, agent) → the last key written (an unchanged line is not written twice)

    def add(self, agent, action, why, now, mint=None, symbol=None, mc=None, px=None, result=None, key=None):
        """One real event → its row (or None: the same line as the last one from this agent on this mint)."""
        assert agent in AGENTS, agent
        k, sig = (mint, agent), key or action
        if self.last.get(k) == sig:
            return None
        self.last[k] = sig
        if len(self.last) > 4 * self.keep:
            live = {(r['mint'], r['agent']) for r in self.rows}
            self.last = {kk: v for kk, v in self.last.items() if kk in live}
        self.seq += 1
        row = {'id': self.seq, 'at': round(_f(now), 2), 'agent': agent, 'action': str(action)[:40], 'why': str(why or '')[:160], 'mint': mint, 'symbol': symbol,
               'mc': round(_f(mc)) if _f(mc) > 0 else None, 'px': float(f"{_f(px):.6g}") if _f(px) > 0 else None, 'result': result}
        self.rows.append(row)
        if len(self.rows) > self.keep:
            del self.rows[:len(self.rows) - self.keep]
        return row

    def since(self, seq):
        return [r for r in self.rows if r['id'] > int(seq or 0)]

    def view(self, n=SNAP):
        """The newest `n` rows for a snapshot, compact (an unknown field is absent, never 0). The live stream sends every row as it happens."""
        return [{k: v for k, v in r.items() if v is not None} for r in self.rows[-n:]]
