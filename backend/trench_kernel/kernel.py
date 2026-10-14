"""⚙ THE KERNEL: event in → MintState updated → only the AFFECTED mints re-judged by the ten-agent brain → ONE decision per mint →
four hunter lanes. One instance per process (`KERNEL`). Measured, not claimed: every stage records its own latency (p50 / p95)."""
import time as _t

from . import brain as _b
from . import metrics as _m
from . import state as _s
from . import supply as _sup
from . import tape as _tape

LAT_KEEP = 400
STALE_SEC = 90.0   # 🧊 a candidate the desk has not re-read for this long is not READY / CONTENDING any more: its numbers are a memory.
# 2026-10-13: a launch that ran to $18K and died back to its $3K floor stayed "2 min old, +3% on 12× volume" in here for 25 minutes and
# was seated three times (Lynk; JEANPAD / TIMUR / SAVELLS the same) — a mint that leaves the desk used to keep its last decision for good.


def _p(xs, q):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * q))], 3) if xs else None


def _sig(v, n=6):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return float(f"{x:.{n}g}") if x == x and x not in (float('inf'), float('-inf')) else None


def _market(mk, age_min, owner):
    """The candidate's market numbers for the page, compact: a field nobody knows is ABSENT (the page prints UNKNOWN), never 0."""
    out = {'price': _sig(mk.get('price')), 'supply': _sig(mk.get('supply'), 10), 'supplySrc': mk.get('supplySrc'),
           'liq': _sig(mk.get('liquidity'), 4), 'vol5m': _sig(mk.get('volume5m'), 4), 'move5m': _sig(mk.get('move5m'), 3), 'buyShare': _sig(mk.get('buyShare'), 3),
           'ageMin': _sig(age_min, 4), 'owner': owner}
    return {k: v for k, v in out.items() if v is not None}


TRACK_VIEW = 8   # TRACKING coins the page sees beside the contenders (the review queue's NEW / TRACKING rows)


class Kernel:
    def __init__(self):
        self.store = _s.MintStore()
        self.dec = {}          # mint → the last decision (status, rank, why, opinions)
        self.decAt = {}        # mint → when it was decided
        self.lat = {'ingest': [], 'rank': [], 'agents': [], 'priceToReaper': []}
        self.counts = {'events': 0, 'rejudged': 0, 'passes': 0, 'priceEvents': 0}
        self.t0 = _t.time()
        self.lanes = []
        self.tape = _tape.Tape()      # 📜 the kernel's own change events (a real change writes a line; an unchanged opinion writes nothing)
        self.owner = {}               # mint → 'review' | 'track' | 'arm' (the owner's review list — priority only, never a bypass)
        self.timings = _m.Timings()   # 📏 decision → order, discovery → entry, age at entry, wake → decision (noted by the service)

    def _lat(self, k, ms):
        self.lat[k] = (self.lat[k] + [ms])[-LAT_KEEP:]

    def mc(self, m):
        ms = self.store.mints.get(m)
        return _sup.mc(ms['market'].get('price'), ms['market'].get('supply')) if ms else None

    def note(self, agent, action, why, now, mint=None, result=None, key=None, px=None):
        """One REAL event from outside the brain (the keeper's ledger, Reaper's ruling, the Judge's review …) → the tape."""
        ms = self.store.mints.get(mint) if mint else None
        price = px if px else (ms['market'].get('price') if ms else None)
        return self.tape.add(agent, action, why, now, mint=mint, symbol=(ms['identity']['symbol'] if ms else None),
                             mc=_sup.mc(price, ms['market'].get('supply')) if ms else None, px=price, result=result, key=key)

    def stale(self, m, now):
        """True = the desk has not re-read this mint for STALE_SEC (a live price event alone does not refresh volume, buyers, age or the chart)."""
        ms = self.store.mints.get(m)
        return bool(ms) and now - float(ms['market'].get('marketAt') or 0) > STALE_SEC

    def judge(self, mints, ctx, now, events=None):
        for m in mints:
            ms = self.store.mints.get(m)
            if not ms:
                continue
            a = _t.perf_counter()
            d = _b.think(ms, ctx)
            self._lat('agents', (_t.perf_counter() - a) * 1000)
            if d['status'] in ('READY', 'CONTENDING') and self.stale(m, now):
                d = {**d, 'status': 'TRACKING', 'stale': True, 'why': f"off the desk for {int(now - (ms['market'].get('marketAt') or 0))}s — its reading is old, waiting for a fresh one"}
            for agent, action, why, key in _tape.diff(self.dec.get(m), d, ms, (events or {}).get(m) or (), now, owner=m in self.owner):
                self.note(agent, action, why, now, mint=m, key=key)
            self.dec[m], self.decAt[m] = d, now
            self.store.set_status(m, d['status'], now, d['why'])
            self.counts['rejudged'] += 1

    def run(self, rows, now, ctx=None, source=None):
        """One batch of rows from the shared desk (any source). → {mint: events}. Only mints with events (and every held mint) are re-judged."""
        ctx = ctx or {}
        a = _t.perf_counter()
        ev = self.store.ingest(rows, now, source)
        self._lat('ingest', (_t.perf_counter() - a) * 1000 / max(1, len(rows or [])))
        held = set((ctx.get('held') or {}).keys())
        pend = set(ctx.get('pending') or ())
        affected = (set(ev) | {m for m in held | pend if m in self.store.mints} | {m for m in self.store.mints if m not in self.dec}
                    | {m for m, d in self.dec.items() if d['status'] == 'ORDER_PENDING' and m in self.store.mints}   # an order that landed / was called off is re-judged
                    | {m for m, d in self.dec.items() if d['status'] in ('READY', 'CONTENDING') and self.stale(m, now)}   # 🧊 a candidate that left the desk steps down…
                    | {m for m, d in self.dec.items() if d.get('stale') and not self.stale(m, now)})   # …and is judged again the pass the desk reads it
        a = _t.perf_counter()
        self.judge(affected, ctx, now, ev)
        self._lat('rank', (_t.perf_counter() - a) * 1000 / max(1, len(affected)))
        for m, d in self.dec.items():   # a mint that left the desk keeps its last decision; one we no longer hold is not HELD any more
            if d['status'] in ('HELD', 'EXIT_PENDING') and m not in held:
                self.store.set_status(m, 'CLOSED', now, 'left the card')
                d['status'] = 'CLOSED'
                self.note('kernel', 'CLOSED', 'left the card', now, mint=m, key='st:CLOSED')
        self.lanes = _b.lanes({m: d for m, d in self.dec.items() if m in self.store.mints}, [m for m in held if m in self.store.mints])
        self.counts['events'] += sum(len(v) for v in ev.values()); self.counts['passes'] += 1
        return ev

    def price_event(self, mint, px, now, ctx=None):
        """A live price for ONE mint (the 6-second guard / market wake) → its MintState + decision update now. → the decision."""
        ms = self.store.mints.get(mint)
        if not ms or not (px and px > 0):
            return None
        a = _t.perf_counter()
        old = ms['market'].get('price')
        ms['market'] = {**ms['market'], 'price': px, 'priceAt': now}
        ms['row'] = {**ms['row'], 'px': px}
        if old and abs(px / old - 1) * 100 >= _s.MATERIAL['price']:
            self.judge([mint], ctx or {}, now)
            self._lat('priceToReaper', (_t.perf_counter() - a) * 1000)
        self.counts['priceEvents'] += 1
        return self.dec.get(mint)

    def ready(self, n=None, exclude=()):
        """READY candidates — the ONE list a seat fill reads: a coin the OWNER armed first (among coins that are READY on their own —
        arming never makes a coin READY), then best rank."""
        r = sorted([(m, d) for m, d in self.dec.items() if d['status'] == 'READY' and m not in exclude and m in self.store.mints],
                   key=lambda kv: (self.owner.get(kv[0]) != 'arm', -kv[1]['rank']))
        return r[:n] if n else r

    def ranks(self):
        """{mint: the kernel's rank} for every judged mint (held coins too — a challenger is compared with the coin it would replace)."""
        return {m: d['rank'] for m, d in self.dec.items() if m in self.store.mints}

    def candidate(self, m, d=None):
        """ONE candidate as a row a fill / a switch / the seat board reads: the sensed row + the kernel's decision."""
        d = d or self.dec.get(m)
        ms = self.store.mints.get(m)
        if not d or not ms:
            return None
        x, op = ms['row'], d['opinions']
        return {**x, 'pair': x.get('pair') or x.get('pairAddress'), 'px': ms['market'].get('price') or x.get('px'), 'status': d['status'], 'rank': d['rank'], 'kwhy': d['why'],
                'size': op['warden']['size'], 'sizeWhy': op['warden']['why'], 'narrative': op['trigger']['narrative'], 'trigger': op['trigger']['state'], 'chartCall': op['trigger'].get('chart'),
                'chartWait': op['trigger'].get('chartWait'), 'open': True}

    def case(self, m):
        """ONE kernel case file (any status) — the sensed row + the ten opinions + the reducer's steps as checks. None = not judged."""
        d, ms = self.dec.get(m), self.store.mints.get(m)
        if not d or not ms:
            return None
        op = d['opinions']
        wall = next((w for _o, s, w in op['devil']['objections'] if s == 'HARD_VETO'), None)
        checks = [['wall', not wall, str(wall or 'inside the hard wall')[:120]],
                  ['timing', op['trigger']['state'] == 'ENTER', f"{op['trigger']['narrative']} → {op['trigger']['state']}: {str(op['trigger']['why'])[:90]}"],
                  ['execution', bool(op['courier']['ok']), str(op['courier']['why'])[:90]],
                  ['rank', d['rank'] >= _b.READY_MIN, f"rank {d['rank']:g} (READY from {_b.READY_MIN:g})"]]
        return {'mint': m, 'symbol': ms['identity']['symbol'], 'pair': ms['identity']['pair'], 'px': ms['market'].get('price'), 'rank': d['rank'], 'lean': d['rank'],
                'cleared': d['status'] == 'READY', 'status': d['status'], 'go': d['status'] == 'READY', 'checks': checks, 'unknown': op['sherlock']['unknown'], 'row': ms['row'],
                'op': op, 'kwhy': d['why'], 'parts': d.get('parts')}

    def cases(self, exclude=(), top=0, statuses=('READY', 'CONTENDING', 'TRACKING')):
        """The kernel's CASE FILES (the seat board, the bench, the candle / research order, the Archivist read these): one per judged
        candidate not excluded, READY first then by rank. `cleared` = READY. `checks` = the reducer's own steps (the wall · timing ·
        execution · rank) — not a second set of rules."""
        ex = set(exclude or ())
        out = [c for c in (self.case(m) for m, d in list(self.dec.items()) if m not in ex and d['status'] in statuses and not d.get('stale')) if c]   # 🧊 a coin off the desk is no case
        out.sort(key=lambda c: (not c['cleared'], c['status'] == 'TRACKING', -c['rank']))
        return out[:top] if top else out

    def metrics(self, now):
        up = max(1.0, now - self.t0)
        st = self.store.stats
        return {'eventsPerSec': round(self.counts['events'] / up, 3), 'uniqueMintsPerMin': round(len(st['firstSeen']) / up * 60, 2),
                'dupesDropped': st['dupes'], 'mints': len(self.store.mints), 'rejudged': self.counts['rejudged'], 'passes': self.counts['passes'],
                'latencyMs': {k: {'p50': _p(v, 0.5), 'p95': _p(v, 0.95), 'n': len(v)} for k, v in self.lat.items()}, 'timings': self.timings.view(),
                'byStatus': {s: sum(1 for c in self.store.cand.values() if c['status'] == s) for s in _s.STATES}}

    def view(self, now, top=24):
        """The bounded payload: lanes, the top candidates with every agent's line, per-section ages, metrics."""
        rows = sorted([(m, d) for m, d in self.dec.items() if m in self.store.mints and d['status'] in ('READY', 'CONTENDING', 'ORDER_PENDING', 'HELD', 'EXIT_PENDING')],
                      key=lambda kv: (kv[1]['status'] not in ('HELD', 'EXIT_PENDING', 'ORDER_PENDING'), -kv[1]['rank']))[:top]
        rows += sorted([(m, d) for m, d in self.dec.items() if m in self.store.mints and d['status'] == 'TRACKING' and not d.get('stale')],   # 👀 the review queue's TRACKING rows (bounded)
                       key=lambda kv: -kv[1]['rank'])[:TRACK_VIEW]
        out = []
        for i, (m, d) in enumerate(rows):
            ms, op = self.store.mints[m], d['opinions']
            mk = ms['market']
            out.append({'mint': m, 'symbol': ms['identity']['symbol'], 'pair': ms['identity']['pair'], 'status': d['status'], 'rank': d['rank'], 'why': d['why'],
                        **_market(mk, op['tally'].get('ageMin'), self.owner.get(m)),   # 📊 price × supply = the chart language (the page multiplies; unknown = absent, never 0)
                        'fresh': op['tally']['fresh'], 'cap': op['tally']['cap'], 'narrative': op['trigger']['narrative'], 'trigger': op['trigger']['state'],
                        'devil': [[o, s, str(w)[:80]] for o, s, w in op['devil']['objections']][:4], 'devilConf': op['devil']['confidence'],
                        'size': op['warden']['size'], 'sizeWhy': op['warden']['why'], 'courier': op['courier']['ok'], 'reaper': op['reaper'],
                        'unknown': op['sherlock']['unknown'],   # relative ages are not sent: the page computes every age from `times` / `decidedAt` (the stream never sent them either)
                        'times': _s.times(ms), 'decidedAt': round(self.decAt.get(m, now), 2),   # absolute, per section: what the delta stream sends (the page computes each age itself)
                        'sources': ms['identity']['sources'][:6], **({'vit': vit(ms.get('row') or {})} if d['status'] != 'TRACKING' and i < VIT_TOP else {})})   # the vital board: seats + the top of the queue (TRACKING rows draw none)
        held = [m for m, d in self.dec.items() if d['status'] in ('HELD', 'EXIT_PENDING') and m in self.store.mints]   # the lanes from the CURRENT decisions (a price event may be newer than the pass)
        self.lanes = _b.lanes({m: d for m, d in self.dec.items() if m in self.store.mints}, held)
        return {'lanes': [{**l, 'symbol': (self.store.mints.get(l.get('mint')) or {}).get('identity', {}).get('symbol') if l.get('mint') else None} for l in self.lanes],
                'candidates': out, 'metrics': self.metrics(now)}


VIT_TOP = 12


def _f0(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def vit(r):
    """🫀 The vitals the decision panel draws as clickables (one compact dict from the sensed row — no fetch): holders, flow, launch,
    chart, narrative, the owner's lesson-rules this coin hits and the socials report. Unknown = absent, never 0."""
    import social_research as _sr
    v, n, li, ch, mi = r.get('vitals') or {}, r.get('nums') or {}, r.get('li') or {}, r.get('chart') or {}, r.get('mind') or {}
    en = ch.get('entry') or [None, None, None]
    out = {'top10': v.get('top10'), 'bundled': v.get('bundledN'), 'snipers': v.get('snipersN'), 'dev': v.get('dev'), 'holders': v.get('holders'),
           'organic': v.get('organic'), 'rug': v.get('rug'), 'read': v.get('read'), 'vol1h': v.get('vol1h'), 'tx1h': v.get('txns1h'),
           'buy': n.get('buy') if n.get('buy') is not None else v.get('buyShare'), 'd5': n.get('d5'), 'pace': n.get('pace'), 'liqD': n.get('liqD'),
           'phase': li.get('phase'), 'cls': li.get('cls'), 'press': li.get('press'), 'first10': li.get('first10'),
           'chart': ch.get('state'), 'entry': en[0], 'entryWhy': en[2] if len(en) > 2 else None, 'dq': (ch.get('q') or {}).get('state'),
           'mp': r.get('mp'), 'narr': mi.get('narr'), 'wave': r.get('waveRole'), 'callers': mi.get('callers'), 'swarm': mi.get('swarm'),
           'taught': r.get('taught') or None, 'soc': _sr.report(r['social']) if r.get('social') else None,
           'links': {k: r[k] for k in ('site', 'x', 'tg') if isinstance(r.get(k), str) and r[k].startswith(('http://', 'https://'))} or None}
    import drain as _drn
    import trench_brain as _tb
    dr_ = _drn.read(v, n, r.get('fv'))   # 🩸 the drain read (exit liquidity · holders leaving · pool draining · the tape) — no fetch
    if dr_['score'] or dr_['xl'] is not None:   # compact: the office payload is capped at 100 KB
        out['drain'] = {k: x for k, x in (('s', dr_['score']), ('st', dr_['state']), ('xl', dr_['xl']), ('hd', dr_['hd']), ('lq', dr_['lq']),
                                          ('w', [q[0] for q in dr_['parts']][:2] or None)) if x is not None}
    flat = {**v, 'chg5m': n.get('d5'), 'vol5m': n.get('v5'), 'holdD': n.get('holdD'), 'tv': r.get('tv'),
            'chg1h': (r.get('li') or {}).get('chg1h')}
    od_ = _drn.odds(_tb.feats(flat), _drn.TABLE)   # 🔮 the measured rug share of coins like this one (the trench brain's judged coins)
    if od_:
        out['odds'] = [od_['rug'], od_['n'], od_['base'], od_['feature']]   # [rug %, coins, base %, feature] — the page writes the sentence
    fv_ = r.get('fv') or {}
    if fv_.get('state'):
        out['tape'] = [fv_.get('state'), round(_f0(fv_.get('buyUsd'))), round(_f0(fv_.get('sellUsd')))]   # [state, $ bought, $ sold] (90s)
    return {k: x for k, x in out.items() if x is not None and x is not False}


KERNEL = Kernel()
