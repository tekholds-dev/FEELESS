"""📡 THE KERNEL'S DELTA STREAM — what changed, pushed; never the whole office rebuilt for a tiny change. Pure + tested.

`Hub` keeps a bounded, numbered log of DELTAS. `publish(kind, key, data)` appends one only when that (kind, key) really changed since it
was last sent (a content hash) — so a pass in which nothing moved sends nothing. `sync(kind, {key: data})` does that for a whole keyed
set and sends `data: None` for a key that is gone. A subscriber asks `since(seq)`: it gets the deltas after `seq`, or `gap = True` when
it fell too far behind (then it reloads the snapshot once — the only time it does).

Kinds (one vocabulary for the page's store, frontend/src/lib/agentHub.js):
  mint_update · candidate_update · agent_update · hunter_update · position_update · lifecycle_update · execution_update · metric_update
  · snapshot (a full pass ended: everything that is not delta-streamed is as fresh as this `at`)
Freshness stays explicit: a delta carries the absolute time of what it describes (`times` per section, `decidedAt`) — a price update
never makes a holder scan or an agent decision look newer than it is.
"""
import asyncio
import json

KINDS = ('mint_update', 'candidate_update', 'agent_update', 'hunter_update', 'position_update', 'lifecycle_update', 'execution_update', 'metric_update', 'snapshot',
         'decision', 'owner_update')   # 📜 one REAL kernel decision event (the tape) · the owner's review list
KEEP = 2000
MAX_SUBS = 12


def _h(data):
    try:
        return hash(json.dumps(data, sort_keys=True, default=str))
    except Exception:
        return None


class Hub:
    def __init__(self, keep=KEEP):
        self.seq = 0
        self.keep = int(keep)
        self.log = []        # [{seq, kind, key, at, data}]
        self.last = {}       # (kind, key) → content hash of what was last sent
        self.subs = set()    # asyncio.Event per live subscriber
        self.sent = {k: 0 for k in KINDS}
        self.skipped = 0

    def publish(self, kind, key, data, now, force=False, track=True):
        """One delta, only if it changed. → the event, or None (unchanged). `track=False` = an EVENT (a decision line): always sent, and
        nothing is remembered about it (it is never compared with a later one)."""
        assert kind in KINDS, kind
        h = _h(data) if track else None
        if track and not force and h is not None and self.last.get((kind, key)) == h:
            self.skipped += 1
            return None
        if track:
            self.last[(kind, key)] = h
        self.seq += 1
        e = {'seq': self.seq, 'kind': kind, 'key': key, 'at': round(float(now), 2), 'data': data}
        self.log.append(e)
        if len(self.log) > self.keep:
            del self.log[:len(self.log) - self.keep]
        self.sent[kind] += 1
        for ev in list(self.subs):
            ev.set()
        return e

    def sync(self, kind, items, now):
        """A keyed SET: publish what changed, and `data: None` for every key that was there and is gone. → the events sent"""
        out = []
        for key, data in (items or {}).items():
            e = self.publish(kind, key, data, now)
            if e:
                out.append(e)
        for (k, key) in [kk for kk in self.last if kk[0] == kind and kk[1] not in (items or {})]:
            self.last.pop((k, key), None)
            self.seq += 1
            e = {'seq': self.seq, 'kind': kind, 'key': key, 'at': round(float(now), 2), 'data': None}
            self.log.append(e); self.sent[kind] += 1; out.append(e)
        if out:
            if len(self.log) > self.keep:
                del self.log[:len(self.log) - self.keep]
            for ev in list(self.subs):
                ev.set()
        return out

    def since(self, seq):
        """→ (deltas after `seq`, gap). gap = the subscriber is older than the log (or from another process): it must reload the snapshot."""
        seq = int(seq or 0)
        if seq > self.seq:
            return [], True          # a sequence from before a restart
        if not self.log:
            return [], False
        if seq < self.log[0]['seq'] - 1:
            return [], True
        return [e for e in self.log if e['seq'] > seq], False

    async def wait(self, seq, timeout):
        """Sleep until something newer than `seq` exists (or the timeout). → True when there is news."""
        if self.seq > int(seq or 0):
            return True
        ev = asyncio.Event()
        self.subs.add(ev)
        try:
            await asyncio.wait_for(ev.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            self.subs.discard(ev)

    def stats(self):
        return {'seq': self.seq, 'log': len(self.log), 'subscribers': len(self.subs), 'sent': dict(self.sent), 'skippedUnchanged': self.skipped}


def sse(e):
    """One delta as a Server-Sent Event frame."""
    return f"id: {e['seq']}\nevent: {e['kind']}\ndata: {json.dumps({'key': e['key'], 'at': e['at'], 'data': e['data']}, default=str, separators=(',', ':'))}\n\n"


HUB = Hub()
