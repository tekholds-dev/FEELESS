"""⚙ THE KERNEL: event in → MintState updated → only the AFFECTED mints re-judged by the ten-agent brain → ONE decision per mint →
four hunter lanes. One instance per process (`KERNEL`). Measured, not claimed: every stage records its own latency (p50 / p95)."""
import time as _t

from . import brain as _b
from . import state as _s

LAT_KEEP = 400


def _p(xs, q):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * q))], 3) if xs else None


class Kernel:
    def __init__(self):
        self.store = _s.MintStore()
        self.dec = {}          # mint → the last decision (status, rank, why, opinions)
        self.decAt = {}        # mint → when it was decided
        self.lat = {'ingest': [], 'rank': [], 'agents': [], 'priceToReaper': []}
        self.counts = {'events': 0, 'rejudged': 0, 'passes': 0, 'priceEvents': 0}
        self.t0 = _t.time()
        self.lanes = []

    def _lat(self, k, ms):
        self.lat[k] = (self.lat[k] + [ms])[-LAT_KEEP:]

    def judge(self, mints, ctx, now):
        for m in mints:
            ms = self.store.mints.get(m)
            if not ms:
                continue
            a = _t.perf_counter()
            d = _b.think(ms, ctx)
            self._lat('agents', (_t.perf_counter() - a) * 1000)
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
        affected = set(ev) | {m for m in held if m in self.store.mints} | {m for m in self.store.mints if m not in self.dec}
        a = _t.perf_counter()
        self.judge(affected, ctx, now)
        self._lat('rank', (_t.perf_counter() - a) * 1000 / max(1, len(affected)))
        for m, d in self.dec.items():   # a mint that left the desk keeps its last decision; one we no longer hold is not HELD any more
            if d['status'] in ('HELD', 'EXIT_PENDING') and m not in held:
                self.store.set_status(m, 'CLOSED', now, 'left the card')
                d['status'] = 'CLOSED'
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
        """READY candidates, best rank first — the ONE list a seat fill reads."""
        r = sorted([(m, d) for m, d in self.dec.items() if d['status'] == 'READY' and m not in exclude and m in self.store.mints], key=lambda kv: -kv[1]['rank'])
        return r[:n] if n else r

    def metrics(self, now):
        up = max(1.0, now - self.t0)
        st = self.store.stats
        return {'eventsPerSec': round(self.counts['events'] / up, 3), 'uniqueMintsPerMin': round(len(st['firstSeen']) / up * 60, 2),
                'dupesDropped': st['dupes'], 'mints': len(self.store.mints), 'rejudged': self.counts['rejudged'], 'passes': self.counts['passes'],
                'latencyMs': {k: {'p50': _p(v, 0.5), 'p95': _p(v, 0.95), 'n': len(v)} for k, v in self.lat.items()},
                'byStatus': {s: sum(1 for c in self.store.cand.values() if c['status'] == s) for s in _s.STATES}}

    def view(self, now, top=24):
        """The bounded payload: lanes, the top candidates with every agent's line, per-section ages, metrics."""
        rows = sorted([(m, d) for m, d in self.dec.items() if m in self.store.mints and d['status'] in ('READY', 'CONTENDING', 'HELD', 'EXIT_PENDING')],
                      key=lambda kv: (kv[1]['status'] not in ('HELD', 'EXIT_PENDING'), -kv[1]['rank']))[:top]
        out = []
        for m, d in rows:
            ms, op = self.store.mints[m], d['opinions']
            out.append({'mint': m, 'symbol': ms['identity']['symbol'], 'pair': ms['identity']['pair'], 'status': d['status'], 'rank': d['rank'], 'why': d['why'],
                        'fresh': op['tally']['fresh'], 'cap': op['tally']['cap'], 'narrative': op['trigger']['narrative'], 'trigger': op['trigger']['state'],
                        'devil': [[o, s, str(w)[:80]] for o, s, w in op['devil']['objections']][:4], 'devilConf': op['devil']['confidence'],
                        'size': op['warden']['size'], 'sizeWhy': op['warden']['why'], 'courier': op['courier']['ok'], 'reaper': op['reaper'],
                        'unknown': op['sherlock']['unknown'], 'ages': _s.ages(ms, now), 'decidedAgo': round(max(0.0, now - self.decAt.get(m, now)), 1),
                        'sources': ms['identity']['sources'][:6]})
        held = [m for m, d in self.dec.items() if d['status'] in ('HELD', 'EXIT_PENDING') and m in self.store.mints]   # the lanes from the CURRENT decisions (a price event may be newer than the pass)
        self.lanes = _b.lanes({m: d for m, d in self.dec.items() if m in self.store.mints}, held)
        return {'lanes': [{**l, 'symbol': (self.store.mints.get(l.get('mint')) or {}).get('identity', {}).get('symbol') if l.get('mint') else None} for l in self.lanes],
                'candidates': out, 'metrics': self.metrics(now)}


KERNEL = Kernel()
