"""🗺 THE LIVING ATLAS, first piece (Slice 11 · VISION › COMP "The Living Atlas"): facts kept as ATOMS with a freshness clock, and each
source's TRUST moving with settled outcomes.

  · ATOMS, NOT PAGES: one small fact = (subject, what) → a value, e.g. ('game:nba:401910022', 'line') → 'SA -16.5'. The same fact from three
    sites is ONE atom with three sources, each keeping the value it gave. The value a brain reads is the one the most trusted source gave.
  · FACTS AGE: every atom carries the clock of its kind (live odds go stale in minutes, a record in a day, a coin's launch never). A stale atom
    is handed over marked stale, never as fact, and COMP's reader re-reads it on its next pass.
  · SOURCES EARN TRUST: when a proof settles, every source that fed it gains (right) or loses (wrong) on that topic. Trust = (right+1)/(n+2),
    so a new source starts at 0.5 and only real outcomes move it. One proof moves one source once (`settled` is keyed by proof + host).
  · SEALED LIKE THE STASH: subjects, values and sources' values are sealed per category (`cat_keys.seal_bytes(raw, 'atlas:<cat>')`); the index
    holds only keyed hashes. A read needs a live brain (or COMP) run token from stash_brain. `stats` returns counts, kinds, freshness and the
    public trust table (site names + scores), never a fact."""
import hashlib
import hmac
import json
import re
import sqlite3
import time
from pathlib import Path

import cat_keys as _ck
import stash_brain as _sb

DIR = 'atlas'
NEVER = -1.0
# 🕐 how long each kind of fact stays true enough to use without a re-read (seconds; NEVER = it does not change)
FRESH = {'winchance': 15 * 60, 'moneyline': 15 * 60, 'line': 30 * 60, 'total': 30 * 60, 'price': 5 * 60, 'liquidity': 10 * 60, 'volume': 10 * 60,
         'change': 10 * 60, 'injury': 2 * 3600, 'schedule': 6 * 3600, 'record': 24 * 3600, 'form': 24 * 3600, 'leader': 24 * 3600, 'launch': NEVER}
FRESH_DEFAULT = 3600
FACTS_MAX = 40


def root_of(data_dir):
    return Path(data_dir) / DIR


def _db(root):
    root.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(root / 'atlas.db'), timeout=20)
    c.execute('PRAGMA busy_timeout=20000')
    c.executescript('''
      CREATE TABLE IF NOT EXISTS atoms (aid TEXT PRIMARY KEY, sh TEXT, cat TEXT, kind TEXT, first REAL, at REAL, fresh REAL, n INT, blob BLOB);
      CREATE INDEX IF NOT EXISTS atoms_sh ON atoms(sh);
      CREATE TABLE IF NOT EXISTS srcs (aid TEXT, host TEXT, at REAL, vh TEXT, blob BLOB, PRIMARY KEY (aid, host));
      CREATE TABLE IF NOT EXISTS trust (host TEXT, topic TEXT, right INT, wrong INT, at REAL, PRIMARY KEY (host, topic));
      CREATE TABLE IF NOT EXISTS settled (ref TEXT, host TEXT, topic TEXT, ok INT, at REAL, PRIMARY KEY (ref, host));''')
    return c


def _key(env=None):
    return hashlib.sha256(f'atlas-index:{_ck._master(env)}'.encode()).digest()


def _h(word, env=None):
    return hmac.new(_key(env), str(word).lower().encode(), hashlib.sha256).hexdigest()[:32]


def _seal(obj, cat, env=None):
    return _ck.seal_bytes(json.dumps(obj, separators=(',', ':')).encode(), f'atlas:{cat}', env)


def _open(raw, cat, env=None):
    return json.loads(_ck.unseal_bytes(raw, f'atlas:{cat}', env))


def host_of(h):
    return re.sub(r'^www\.', '', re.sub(r'^https?://', '', str(h or '').lower()).split('/')[0])


def fresh_for(kind):
    return float(FRESH.get(kind, FRESH_DEFAULT))


def is_fresh(row_at, fresh, now):
    return fresh == NEVER or (now - float(row_at)) <= float(fresh)


def trust_score(right, wrong):
    return round((int(right or 0) + 1) / (int(right or 0) + int(wrong or 0) + 2), 3)


# ── put (COMP's reader, or a brain inside a run) ─────────────────────────────────────────────────────────────────────────────────────────
def put(root, token, rows, now=None, env=None):
    """rows = [{subject, what, value, host, kind, cat, label?}] → how many atoms were new. The same (subject, what) from another site adds a
    source to the atom it already is; the same site again just refreshes its clock and value."""
    _sb._brain(token, now); now = float(now or time.time()); new = 0
    with _db(root) as c:
        for r in rows or []:
            subj, what, val = str(r.get('subject') or '').strip().lower(), str(r.get('what') or '').strip().lower(), r.get('value')
            host = host_of(r.get('host')); kind = str(r.get('kind') or 'fact'); cat = re.sub(r'[^a-z0-9_-]', '', str(r.get('cat') or 'web').lower()) or 'web'
            if not subj or not what or val in (None, '') or not host:
                continue
            aid = _h(f'{subj}|{what}', env); fresh = fresh_for(kind)
            old = c.execute('SELECT n FROM atoms WHERE aid = ?', (aid,)).fetchone()
            c.execute('INSERT OR REPLACE INTO srcs VALUES (?,?,?,?,?)', (aid, host, now, _h(str(val), env), _seal({'value': val}, cat, env)))
            n = c.execute('SELECT COUNT(*) FROM srcs WHERE aid = ?', (aid,)).fetchone()[0]
            blob = _seal({'subject': subj, 'what': what, 'label': str(r.get('label') or '')[:80]}, cat, env)
            if old:
                c.execute('UPDATE atoms SET at = ?, n = ?, fresh = ?, kind = ?, blob = ? WHERE aid = ?', (now, n, fresh, kind, blob, aid))
            else:
                new += 1
                c.execute('INSERT INTO atoms VALUES (?,?,?,?,?,?,?,?,?)', (aid, _h(subj, env), cat, kind, now, now, fresh, n, blob))
    return new


def due(root, subject, whats, now=None, env=None):
    """True when any of these facts about `subject` is missing or stale: COMP's reader re-reads it (no unsealing, hashes only)."""
    now = float(now or time.time())
    if not (root / 'atlas.db').exists():
        return True
    with _db(root) as c:
        for w in whats:
            r = c.execute('SELECT at, fresh FROM atoms WHERE aid = ?', (_h(f'{str(subject).lower()}|{str(w).lower()}', env),)).fetchone()
            if not r or not is_fresh(r[0], r[1], now):
                return True
    return False


# ── read (brains only) ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def facts(root, token, subjects, now=None, topic=None, n=FACTS_MAX, env=None):
    """🔎 Every atom about these subjects, freshest first: its value (from the most trusted source on `topic`), every source with the value it
    gave and its trust, its age, and whether it is still fresh. Stale ones come back marked stale. → [atom]"""
    _sb._brain(token, now); now = float(now or time.time())
    subs = [str(s).lower() for s in subjects or [] if s]
    if not subs or not (root / 'atlas.db').exists():
        return []
    out = []
    with _db(root) as c:
        q = ','.join('?' * len(subs))
        rows = c.execute(f'SELECT aid, cat, kind, at, fresh, n, blob FROM atoms WHERE sh IN ({q}) ORDER BY at DESC LIMIT ?', [_h(s, env) for s in subs] + [int(n) * 3]).fetchall()
        tr = {(h, t): trust_score(r, w) for h, t, r, w in c.execute('SELECT host, topic, right, wrong FROM trust').fetchall()}
        for aid, cat, kind, at, fresh, cnt, blob in rows:
            try:
                head = _open(blob, cat, env)
                src = [{'host': h, 'at': round(a), 'value': _open(b, cat, env)['value'], 'trust': tr.get((h, topic or cat), 0.5)}
                       for h, a, b in c.execute('SELECT host, at, blob FROM srcs WHERE aid = ? ORDER BY at DESC', (aid,)).fetchall()]
            except (ValueError, KeyError):
                continue
            if not src:
                continue
            best = max(src, key=lambda s: (s['trust'], s['at']))
            out.append({**head, 'kind': kind, 'value': best['value'], 'by': best['host'], 'sources': src, 'agree': len({json.dumps(s['value']) for s in src}) == 1,
                        'age': round(now - at), 'fresh': is_fresh(at, fresh, now)})
            if len(out) >= n:
                break
    return out


def facts_line(rows, n=24):
    """What a brain reads: one fact per line with its sources and age; stale ones say so. '' when none."""
    if not rows:
        return ''
    def one(a):
        srcs = ', '.join(f"{s['host']} {s['value']}" if not a['agree'] else s['host'] for s in a['sources'][:4])
        age = f"{max(1, round(a['age'] / 60))} min ago" if a['age'] < 7200 else f"{round(a['age'] / 3600)} h ago"
        return f"- {a.get('label') or a['subject']} · {a['what']}: {a['value']} ({srcs}; read {age}{'' if a['fresh'] else '; STALE, check it again'})"
    return '\n'.join(one(a) for a in rows[:n])


# ── trust (settled outcomes) ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def settle(root, ref, hosts, topic, ok, now=None):
    """🏁 A proof settled: each source that fed it moves once on `topic` (right when the proof was right). → hosts that moved now."""
    now = float(now or time.time()); topic = str(topic or 'web').lower(); moved = []
    with _db(root) as c:
        for h in dict.fromkeys(host_of(x) for x in hosts or [] if x):
            if not h or c.execute('SELECT 1 FROM settled WHERE ref = ? AND host = ?', (str(ref), h)).fetchone():
                continue
            c.execute('INSERT INTO settled VALUES (?,?,?,?,?)', (str(ref), h, topic, 1 if ok else 0, now))
            c.execute('INSERT INTO trust VALUES (?,?,?,?,?) ON CONFLICT(host, topic) DO UPDATE SET right = right + ?, wrong = wrong + ?, at = ?',
                      (h, topic, 1 if ok else 0, 0 if ok else 1, now, 1 if ok else 0, 0 if ok else 1, now))
            moved.append(h)
    return moved


def trust_rows(root, topic=None):
    if not (root / 'atlas.db').exists():
        return []
    with _db(root) as c:
        rows = c.execute('SELECT host, topic, right, wrong, at FROM trust' + (' WHERE topic = ?' if topic else ''), (topic,) if topic else ()).fetchall()
    return sorted(({'host': h, 'topic': t, 'right': r, 'wrong': w, 'trust': trust_score(r, w), 'at': round(a)} for h, t, r, w, a in rows), key=lambda x: (-x['trust'], -(x['right'] + x['wrong'])))


# ── counts (never a fact) ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def stats(root, now=None):
    """The atlas panel: atoms by kind (fresh / stale / from 2+ sources), sources, settled proofs, and the trust table. Never a subject or value."""
    now = float(now or time.time())
    if not (root / 'atlas.db').exists():
        return {'atoms': 0, 'fresh': 0, 'stale': 0, 'multi': 0, 'sources': 0, 'kinds': [], 'trust': [], 'settled': 0}
    with _db(root) as c:
        k = c.execute('SELECT kind, cat, COUNT(*), SUM(CASE WHEN fresh = -1 OR ? - at <= fresh THEN 1 ELSE 0 END), SUM(CASE WHEN n > 1 THEN 1 ELSE 0 END), MAX(at) '
                      'FROM atoms GROUP BY kind, cat', (now,)).fetchall()
        srcs = c.execute('SELECT COUNT(*) FROM srcs').fetchone()[0]
        settled = c.execute('SELECT COUNT(DISTINCT ref) FROM settled').fetchone()[0]
    kinds = sorted(({'kind': kd, 'cat': ct, 'atoms': n, 'fresh': int(f or 0), 'stale': n - int(f or 0), 'multi': int(m or 0), 'lastAt': round(a or 0)} for kd, ct, n, f, m, a in k),
                   key=lambda r: -r['atoms'])
    return {'atoms': sum(r['atoms'] for r in kinds), 'fresh': sum(r['fresh'] for r in kinds), 'stale': sum(r['stale'] for r in kinds), 'multi': sum(r['multi'] for r in kinds),
            'sources': srcs, 'kinds': kinds, 'trust': trust_rows(root)[:40], 'settled': settled}
