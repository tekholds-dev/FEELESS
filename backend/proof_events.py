"""🧾 COL-3 PROOF EVENT HISTORY (owner + GPT 2026-11-09): every step of every proof, in order, in a record nobody can quietly edit.

One SQLite file (`proof_events.db`), append-only, each row HMAC-chained to the one before with ITS OWN key (never the Pool's money
chain, never its key). Writers take `BEGIN IMMEDIATE`, so two services appending at once still get one unbroken line.

Events: plan · build · review · file · grade · stamp · send · score · correction. A wrong row is never edited: a `correction` row
points at the row it fixes. Every row carries an id made from what happened, so the same fact filed twice (a replay, a restart,
two saves of the same state) is kept once.

Log only: nothing here changes a proof, a grade, a payout or a route. `watch()` reads folder state the service already saved and
files what changed since the record last saw it.

Deleting the newest rows leaves a shorter chain that still verifies: only a head kept somewhere else catches that
(`verify(expect=...)`). Where that head is anchored (the repo, a chain memo) is the owner's call."""
import hashlib
import hmac
import json
import sqlite3
import time

import mission as _mission
import proof_stamp as _stamp

VERSION = 1
EVENTS = ('plan', 'build', 'review', 'file', 'grade', 'stamp', 'send', 'score', 'correction', 'reuse')   # reuse: COL-26, a proven part used again
GENESIS = 'proof-events:genesis'
DB_NAME = 'proof_events.db'


class Tampered(Exception):
    """The event history is not what was written."""


def _key():
    import cat_keys
    return hashlib.sha256(f'proof-events:{cat_keys._master()}'.encode()).digest()   # its own key: knowing it says nothing about the Pool's


def _db(path, timeout=30.0):
    c = sqlite3.connect(str(path), timeout=timeout, isolation_level=None)
    c.execute(f'PRAGMA busy_timeout={int(timeout * 1000)}')
    if c.execute('PRAGMA journal_mode').fetchone()[0].lower() != 'wal':
        try:
            c.execute('PRAGMA journal_mode=WAL')
        except sqlite3.OperationalError:
            pass
    c.execute('CREATE TABLE IF NOT EXISTS events (n INTEGER PRIMARY KEY, eid TEXT NOT NULL UNIQUE, at REAL NOT NULL, kind TEXT NOT NULL,'
              ' ref TEXT NOT NULL, cat TEXT, event TEXT NOT NULL, data TEXT NOT NULL, prev TEXT NOT NULL, mac TEXT NOT NULL)')
    c.execute('CREATE INDEX IF NOT EXISTS events_proof ON events (kind, ref, n)')
    return c


def _canon(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), default=str)


def eid_of(kind, ref, event, *facts):
    """The id of a fact: the same proof, step and facts always make the same id."""
    return hashlib.sha256(_canon([kind, ref, event, *facts]).encode()).hexdigest()[:32]


def _mac(key, prev, row):
    body = _canon([row['n'], row['eid'], round(float(row['at']), 3), row['kind'], row['ref'], row['cat'], row['event'], row['data']])
    return hmac.new(key, f'{prev}|{body}'.encode(), hashlib.sha256).hexdigest()


def _clean(e):
    kind = _mission.kind_of(e.get('kind'))
    if kind not in _mission.KINDS:
        raise ValueError(f'unknown proof kind: {e.get("kind")!r}')
    if e.get('event') not in EVENTS:
        raise ValueError(f'unknown event: {e.get("event")!r}')
    ref = str(e.get('ref') or '').strip()
    if not ref:
        raise ValueError('an event needs the proof it belongs to')
    data = e.get('data') or {}
    if not isinstance(data, dict):
        raise ValueError('event data is a dict')
    return {'kind': kind, 'ref': ref[:96], 'cat': (str(e['cat'])[:64] if e.get('cat') else None), 'event': e['event'], 'data': _canon(data),
            'eid': str(e.get('eid') or eid_of(kind, ref, e['event'], data))[:64], 'at': float(e.get('at') or time.time())}


def append_many(path, events, key=None, timeout=30.0):
    """Files events in order under one lock. An event whose id is already on record is skipped. → the rows written."""
    key = key or _key()
    rows = [_clean(e) for e in events]
    if not rows:
        return []
    c = _db(path, timeout)
    try:
        c.execute('BEGIN IMMEDIATE')
        last = c.execute('SELECT n, mac FROM events ORDER BY n DESC LIMIT 1').fetchone()
        n, prev = (last[0], last[1]) if last else (0, GENESIS)
        out, seen = [], set()
        for r in rows:
            if r['eid'] in seen or c.execute('SELECT 1 FROM events WHERE eid = ?', (r['eid'],)).fetchone():
                continue
            if r['event'] == 'correction':
                fx = json.loads(r['data']).get('fixes')
                hit = c.execute('SELECT kind, ref FROM events WHERE n = ?', (fx,)).fetchone() if isinstance(fx, int) else None
                if not hit or tuple(hit) != (r['kind'], r['ref']):
                    raise ValueError('a correction must point at an earlier row of the same proof')
            n += 1; r['n'] = n; r['prev'] = prev; r['mac'] = prev = _mac(key, prev, r); seen.add(r['eid'])
            c.execute('INSERT INTO events (n, eid, at, kind, ref, cat, event, data, prev, mac) VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (r['n'], r['eid'], r['at'], r['kind'], r['ref'], r['cat'], r['event'], r['data'], r['prev'], r['mac']))
            out.append({**r, 'data': json.loads(r['data'])})
        c.execute('COMMIT')
        return out
    except BaseException:
        if c.in_transaction:
            c.execute('ROLLBACK')
        raise
    finally:
        c.close()


def append(path, kind, ref, event, data=None, cat=None, eid=None, at=None, key=None):
    """One event. → its row, or None when the same fact is already on record."""
    got = append_many(path, [{'kind': kind, 'ref': ref, 'event': event, 'data': data, 'cat': cat, 'eid': eid, 'at': at}], key)
    return got[0] if got else None


def correct(path, fixes, why, data=None, key=None, at=None):
    """A wrong row stays; this row says which one is wrong and why. → its row."""
    c = _db(path)
    try:
        hit = c.execute('SELECT kind, ref, cat FROM events WHERE n = ?', (int(fixes),)).fetchone()
    finally:
        c.close()
    if not hit:
        raise ValueError(f'no row {fixes} to correct')
    body = {**(data or {}), 'fixes': int(fixes), 'why': str(why or '')[:300]}
    return append(path, hit[0], hit[1], 'correction', body, cat=hit[2], key=key, at=at)


def _row(r):
    return {'n': r[0], 'eid': r[1], 'at': r[2], 'kind': r[3], 'ref': r[4], 'cat': r[5], 'event': r[6], 'data': json.loads(r[7]), 'prev': r[8], 'mac': r[9]}


_COLS = 'n, eid, at, kind, ref, cat, event, data, prev, mac'


def verify(path, key=None, expect=None):
    """Walks the whole chain. `expect` = a head (n, mac) kept elsewhere: a chain cut back below it fails.
    → {'ok', 'count', 'head', 'brokenAt', 'why'}"""
    key = key or _key()
    c = _db(path)
    try:
        prev, want, last = GENESIS, 1, None
        for r in c.execute(f'SELECT {_COLS} FROM events ORDER BY n'):
            row = _row(r); row['data'] = r[7]
            if row['n'] != want:
                return {'ok': False, 'count': want - 1, 'head': last, 'brokenAt': want, 'why': f'row {want} is missing'}
            if row['prev'] != prev:
                return {'ok': False, 'count': want - 1, 'head': last, 'brokenAt': want, 'why': f'row {want} does not follow row {want - 1}'}
            if not hmac.compare_digest(_mac(key, prev, row), row['mac']):
                return {'ok': False, 'count': want - 1, 'head': last, 'brokenAt': want, 'why': f'row {want} was changed after it was written'}
            prev, want, last = row['mac'], want + 1, [row['n'], row['mac']]
        count = want - 1
        if expect:
            en, emac = int(expect[0]), str(expect[1])
            mac_at = c.execute('SELECT mac FROM events WHERE n = ?', (en,)).fetchone()
            if not mac_at:
                return {'ok': False, 'count': count, 'head': last, 'brokenAt': en, 'why': f'the chain was cut back: row {en} is gone'}
            if not hmac.compare_digest(mac_at[0], emac):
                return {'ok': False, 'count': count, 'head': last, 'brokenAt': en, 'why': f'row {en} is not the row the kept head names'}
        return {'ok': True, 'count': count, 'head': last, 'brokenAt': None, 'why': None}
    finally:
        c.close()


def head(path):
    """[n, mac] of the newest row (what an outside anchor would keep), or None."""
    c = _db(path)
    try:
        r = c.execute('SELECT n, mac FROM events ORDER BY n DESC LIMIT 1').fetchone()
        return [r[0], r[1]] if r else None
    finally:
        c.close()


def counts(path):
    """Every proof's record in one read: {(kind, ref): {'events', 'last', 'at', 'steps'}}. A missing file is an empty record."""
    from pathlib import Path
    if not Path(path).exists():
        return {}
    c = _db(path)
    try:
        out = {}
        for kind, ref, event, at in c.execute('SELECT kind, ref, event, at FROM events ORDER BY n'):
            r = out.setdefault((kind, ref), {'events': 0, 'last': None, 'at': None, 'steps': []})
            r['events'] += 1; r['last'] = event; r['at'] = at
            if event not in r['steps']:
                r['steps'].append(event)
        return out
    finally:
        c.close()


def rows(path, events=('review', 'stamp', 'correction')):
    """(kind, ref, event, data) in record order, for the judges' scorecard. A missing file is no rows."""
    from pathlib import Path
    if not Path(path).exists():
        return []
    c = _db(path)
    try:
        q = f"SELECT kind, ref, event, data FROM events WHERE event IN ({','.join('?' * len(events))}) ORDER BY n"
        return [(k, r, e, json.loads(d or '{}')) for k, r, e, d in c.execute(q, tuple(events))]
    finally:
        c.close()


def history(path, kind, ref):
    """One proof's rows in order. A row a later correction fixes carries `correctedBy` (that row's n)."""
    c = _db(path)
    try:
        rows = [_row(r) for r in c.execute(f'SELECT {_COLS} FROM events WHERE kind = ? AND ref = ? ORDER BY n', (_mission.kind_of(kind), str(ref)))]
    finally:
        c.close()
    by_n = {r['n']: r for r in rows}
    for r in rows:
        if r['event'] == 'correction' and r['data'].get('fixes') in by_n:
            by_n[r['data']['fixes']].setdefault('correctedBy', []).append(r['n'])
    return rows


def recent(path, cat, since=0.0, limit=30):
    """🔔 The desk's bell: one agent's newest steps (any proof), newest first. Read only; no data body beyond a short label."""
    c = _db(path)
    try:
        rows = [_row(r) for r in c.execute(f'SELECT {_COLS} FROM events WHERE cat = ? AND at > ? ORDER BY at DESC LIMIT ?', (str(cat), float(since or 0), int(limit)))]
    finally:
        c.close()
    def detail(d):
        d = d or {}
        if d.get('verdict'):
            return f"{d['verdict']}{' ' + str(d['score']) + '/100' if d.get('score') is not None else ''}"
        if d.get('graded'):
            return str(d['graded'])
        if d.get('score') is not None:
            return f"{d['score']}/100"
        return str(d.get('label') or d.get('name') or d.get('sym') or '')[:40]
    return [{'at': r['at'], 'kind': r['kind'], 'ref': r['ref'], 'event': r['event'], 'detail': detail(r['data']), 'bad': (r['data'] or {}).get('verdict') == 'fail' or (r['data'] or {}).get('graded') == 'wrong'} for r in rows]


BRIEF_KINDS = ('pow', 'pop', 'pob', 'poc', 'pos', 'poe')


def brief(path, now=None):
    """📰 The daily proofs brief, from the record itself (no model, no guess): per proof type, what was filed in 24 h and 7 d, how the other
    minds reviewed it (pass rate, average score) and how it graded. The ranking rewards proofs that pass review and actually get graded right;
    a type with nothing reviewed this week cannot top it. Pure on the file's rows."""
    from pathlib import Path
    now = now or time.time(); out = {k: {'kind': k, 'filed24': 0, 'filed7': 0, 'reviews': 0, 'passed': 0, 'scoreSum': 0, 'right': 0, 'wrong': 0} for k in BRIEF_KINDS}
    if Path(path).exists():
        c = _db(path)
        try:
            for kind, event, at, data in c.execute('SELECT kind, event, at, data FROM events WHERE at > ?', (now - 7 * 86400,)):
                r = out.get(kind)
                if not r:
                    continue
                d = json.loads(data or '{}')
                if event == 'file':   # when it was really filed (the record was backfilled on 2026-11-09/10, so `at` alone says "today" for old proofs)
                    when = float(d.get('filedAt') or at)
                    if when > now - 7 * 86400:
                        r['filed7'] += 1; r['filed24'] += int(when > now - 86400)
                elif event == 'review' and d.get('score') is not None:
                    r['reviews'] += 1; r['scoreSum'] += float(d['score']); r['passed'] += int(d.get('verdict') == 'pass')
                elif event == 'grade':
                    r['right'] += int(d.get('graded') == 'right'); r['wrong'] += int(d.get('graded') == 'wrong')
        finally:
            c.close()
    rows = []
    for r in out.values():
        avg = round(r['scoreSum'] / r['reviews']) if r['reviews'] else None
        pass_pct = round(100 * r['passed'] / r['reviews']) if r['reviews'] else None
        graded = r['right'] + r['wrong']; right_pct = round(100 * r['right'] / graded) if graded else None
        heat = (0 if avg is None else avg) * 0.5 + (0 if right_pct is None else right_pct) * 0.3 + min(r['filed7'], 20) + 5 * min(r['filed24'], 4)
        rows.append({'kind': r['kind'], 'filed24': r['filed24'], 'filed7': r['filed7'], 'reviews': r['reviews'], 'avgScore': avg, 'passPct': pass_pct,
                     'right': r['right'], 'wrong': r['wrong'], 'rightPct': right_pct, 'heat': round(heat, 1) if r['reviews'] else 0})
    rows.sort(key=lambda x: -x['heat'])
    return {'rows': rows, 'best': rows[0]['kind'] if rows and rows[0]['heat'] > 0 else None, 'at': now}


# ---- the watcher: folder state the service saved → the events it implies --------------------------------------------------

def _sent_of(v):
    if not v:
        return None
    if isinstance(v, dict):
        return {k: v[k] for k in ('sig', 'sol', 'at') if v.get(k) is not None} or {'sent': True}
    return {'at': v} if isinstance(v, (int, float)) and not isinstance(v, bool) else {'sent': True}


def facts(kind, f, now):
    """What a saved folder says has happened. Pure."""
    code = _mission.KINDS[kind][0]
    won = _stamp._result(code, f)
    st = _stamp.of(code, f, now)['state']
    score = None
    if won is not None and kind != 'poe':
        score = {'won': won}
        for k in ('pnlPct', 'pnlSol', 'roePct', 'net'):
            if f.get(k) is not None:
                score[k] = f[k]
    return {'filed': f.get('status') or 'filed', 'filedAt': f.get('closedAt') or f.get('at'), 'graded': f.get('graded') if f.get('graded') in ('right', 'wrong') else None,
            'gradedBy': f.get('gradedBy'), 'score': score, 'stamp': st if st in ('proved', 'not') else None, 'sent': _sent_of(f.get('sent'))}


def states(store, now):
    """Every proof folder in a feecats store, plus each open PoW run. → [(kind, ref, cat, facts)]"""
    out = []
    for cid, c in ((store or {}).get('cats') or {}).items():
        for kind, (_code, key_) in _mission.KINDS.items():
            for f in c.get(key_) or []:
                if f.get('id'):   # one row per filing: a PoStatic workspace files many pages, each its own folder
                    out.append((kind, str(f['id']), cid, {**facts(kind, f, now), **({'inWs': f['ws']} if f.get('ws') else {})}))
        run = (c.get('powRun') or {}).get('folder') or {}
        if run.get('id') and run.get('status') != 'closed':
            out.append(('pow', str(run['id']), cid, {'open': True, 'phase': run.get('phase')}))
    return out


def ws_state(cat_id, doc):
    """A PoStatic build or PoC post workspace (its plan, reviews and pages, under the workspace id; each page it files is a folder row whose
    `file` event names this workspace). → (kind, ref, cat, facts) or None"""
    kind = {'build': 'pos', 'content': 'poc'}.get((doc or {}).get('kind'))
    if not kind or not doc.get('id'):
        return None
    plan = doc.get('plan') or {}
    return (kind, str(doc['id']), cat_id, {'ws': True, 'planAt': plan.get('at'), 'planBy': plan.get('by'), 'approved': bool(plan.get('approved')),
                                            'stage': doc.get('stage'), 'versions': [[v.get('at'), v.get('by')] for v in doc.get('versions') or []]})


def _last(rows, event):
    for r in reversed(rows):
        if r['event'] == event or (r['event'] == 'correction' and r['data'].get('event') == event):
            return r
    return None


def _changes(kind, ref, cat, fx, rows, now):
    """The events between what the record holds for this proof (`rows`) and what its folder says now (`fx`)."""
    out, ev = [], lambda event, data, *k: out.append({'kind': kind, 'ref': ref, 'cat': cat, 'event': event, 'data': data, 'at': now,
                                                       'eid': eid_of(kind, ref, event, *k)})
    if fx.get('ws'):
        if fx.get('planAt'):
            ev('plan', {'by': fx.get('planBy'), 'approved': fx['approved'], 'planAt': fx['planAt']}, fx['planAt'], fx['approved'])
        if fx.get('stage') == 'review':
            after = fx['versions'][-1][0] if fx['versions'] else None
            ev('review', {'after': after}, after)
        for at, by in fx['versions']:
            ev('build', {'by': by, 'versionAt': at}, at, by)
        return out
    if fx.get('open'):
        ev('plan', {'phase': fx.get('phase')})
        if fx.get('phase'):
            ev('build', {'phase': fx['phase']}, fx['phase'])
        return out
    ev('file', {'status': fx['filed'], 'filedAt': fx.get('filedAt'), **({'ws': fx['inWs']} if fx.get('inWs') else {})})   # `at` is when the record saw it; `filedAt` is the folder's own time
    for field, event, val in (('graded', 'grade', fx['graded']), ('score', 'score', fx['score']), ('stamp', 'stamp', fx['stamp'])):
        prev = _last(rows, event)
        had = (prev['data'].get('to') if prev['event'] == 'correction' else prev['data'].get(field)) if prev else None
        if prev is None:
            if val is not None:
                ev(event, {field: val, **({'by': fx.get('gradedBy')} if event == 'grade' and fx.get('gradedBy') else {})}, val)
        elif _canon(had) != _canon(val):
            ev('correction', {'event': event, 'fixes': prev['n'], 'from': had, 'to': val, 'why': 'the folder changed after it was filed'}, prev['n'], val)
    if fx['sent'] and not _last(rows, 'send'):
        ev('send', fx['sent'])
    return out


class Watcher:
    """Remembers what it last filed for each proof, so an unchanged folder costs one comparison and no database read."""

    def __init__(self, path, key=None, timeout=2.0):
        self.path, self.key, self.timeout, self.seen = path, key, timeout, {}

    def watch(self, items, now=None):
        """Files what changed. A busy database just means the next save files it. → the rows written"""
        now = now or time.time()
        last = {(k, r): (k, r, c, fx) for k, r, c, fx in items}   # the same proof twice in one save: its newest state wins
        todo = [(k, r, c, fx, _canon(fx)) for k, r, c, fx in last.values() if self.seen.get((k, r)) != _canon(fx)]
        if not todo:
            return []
        key = self.key or _key()
        c = _db(self.path, self.timeout)
        try:
            evs = []
            for kind, ref, cat, fx, _fp in todo:
                rows = [_row(x) for x in c.execute(f'SELECT {_COLS} FROM events WHERE kind = ? AND ref = ? ORDER BY n', (kind, ref))]
                evs += _changes(kind, ref, cat, fx, rows, now)
        finally:
            c.close()
        out = append_many(self.path, evs, key, self.timeout)
        for kind, ref, _c, _fx, fp in todo:
            self.seen[(kind, ref)] = fp
        return out
