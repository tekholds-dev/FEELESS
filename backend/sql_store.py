"""🗄 SITE-8 · SQL DOCS: a JSON-document store in SQLite that any number of worker PROCESSES can share without losing a write.
Tested: tests/test_sql_store.py (4 processes × 150 updates of one doc → exactly 600, where the old whole-file JSON pattern loses most).

Why: every store under backend/data was one JSON file, read whole, changed in memory, written whole, guarded by an asyncio lock that only
exists inside ONE process. With two uvicorn workers, a check-in saved by worker A is wiped by worker B's older copy. Here each key is its own
row, and `update(key, fn)` reads, changes and writes that row inside one `BEGIN IMMEDIATE` transaction (SQLite's write lock is shared by
every process), so two workers touching the same wallet are serialized and two touching different wallets never clash.

  docs = Docs(path[, inner='profiles'])  # <name>.db beside the old file; the old .json is moved in once, byte for byte, and kept read-only
  docs.get(key, default) · docs.all() · docs.put(key, value) · docs.update(key, fn) → fn's return · docs.replace_all(mapping)
`all()` is cached per database version (`PRAGMA data_version`), so hot readers pay one tiny query until somebody writes.

  lock = ProcLock(path)  # for a WHOLE-document store (crews.json): `async with lock:` = one holder across every worker process
"""
import asyncio
import fcntl
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

BUSY_MS = 10_000


class Docs:
    def __init__(self, path, migrate_from=None, inner=None):
        self.inner = inner   # the old file wraps its rows one level down, e.g. {'profiles': {wallet: {...}}} → inner='profiles'
        self.path = Path(path).with_suffix('.db')
        self.src = Path(migrate_from) if migrate_from else Path(path).with_suffix('.json')
        self._local = threading.local()
        self._cache = (None, None)
        self._ready = False

    def _db(self):
        c = getattr(self._local, 'c', None)
        if c is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            c = sqlite3.connect(str(self.path), timeout=BUSY_MS / 1000, isolation_level=None, check_same_thread=False)
            c.execute(f'PRAGMA busy_timeout={BUSY_MS}')
            # Switching a NEW file to WAL takes an exclusive lock that SQLite's busy handler does not wait for: workers opening the store
            # together get 'database is locked' at once (caught by the 4-process test). Retry until the busy budget runs out.
            for i_ in range(400):
                try:
                    c.execute('PRAGMA journal_mode=WAL')
                    c.execute('CREATE TABLE IF NOT EXISTS docs (k TEXT PRIMARY KEY, v TEXT NOT NULL)')
                    c.execute('CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)')
                    break
                except sqlite3.OperationalError as e:
                    if 'locked' not in str(e) or i_ == 399:
                        raise
                    time.sleep(0.025)
            c.execute('PRAGMA synchronous=NORMAL')
            self._local.c = c
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        if not self._ready:
            self._migrate(c)
        return c

    def _migrate(self, c):
        """The old JSON file moves in ONCE (under the write lock, so two workers starting together move it once); it stays as a read-only backup."""
        c.execute('BEGIN IMMEDIATE')
        try:
            done = c.execute("SELECT v FROM meta WHERE k = 'migrated'").fetchone()
            if not done:
                old = {}
                if self.src.exists():
                    old = json.loads(self.src.read_text() or '{}')
                    if self.inner and isinstance(old, dict):
                        old = old.get(self.inner) or {}
                    if not isinstance(old, dict):
                        raise ValueError(f'{self.src.name} is not a keyed store')
                c.executemany('INSERT OR REPLACE INTO docs (k, v) VALUES (?, ?)', [(str(k), json.dumps(v)) for k, v in old.items()])
                c.execute("INSERT INTO meta (k, v) VALUES ('migrated', ?)", (json.dumps({'from': self.src.name, 'keys': len(old)}),))
            c.execute('COMMIT')
        except BaseException:
            c.execute('ROLLBACK')
            raise
        if not done and self.src.exists():
            try:
                os.chmod(self.src, 0o400)
            except OSError:
                pass
        self._ready = True

    def get(self, key, default=None):
        row = self._db().execute('SELECT v FROM docs WHERE k = ?', (str(key),)).fetchone()
        return json.loads(row[0]) if row else default

    def all(self):
        c = self._db(); ver = (id(c), c.execute('PRAGMA data_version').fetchone()[0])
        if self._cache[0] == ver:
            return self._cache[1]
        out = {k: json.loads(v) for k, v in c.execute('SELECT k, v FROM docs')}
        self._cache = (ver, out)
        return out

    def put(self, key, value):
        self.update(key, lambda _old: value)

    def update(self, key, fn, default=None):
        """fn(current or default) → the new value, or (new value, result) when it returns a 2-tuple tagged by `Docs.Result`. One transaction."""
        c = self._db(); key = str(key)
        c.execute('BEGIN IMMEDIATE')
        try:
            row = c.execute('SELECT v FROM docs WHERE k = ?', (key,)).fetchone()
            cur = json.loads(row[0]) if row else (json.loads(json.dumps(default)) if default is not None else None)
            out = fn(cur)
            new, res = (out.value, out.result) if isinstance(out, Result) else (out, out)
            if new is None:
                c.execute('DELETE FROM docs WHERE k = ?', (key,))
            else:
                c.execute('INSERT OR REPLACE INTO docs (k, v) VALUES (?, ?)', (key, json.dumps(new)))
            c.execute('COMMIT')
        except BaseException:
            c.execute('ROLLBACK')
            raise
        self._cache = (None, None)
        return res

    def replace_all(self, mapping):
        c = self._db()
        c.execute('BEGIN IMMEDIATE')
        try:
            c.execute('DELETE FROM docs')
            c.executemany('INSERT INTO docs (k, v) VALUES (?, ?)', [(str(k), json.dumps(v)) for k, v in (mapping or {}).items()])
            c.execute('COMMIT')
        except BaseException:
            c.execute('ROLLBACK')
            raise
        self._cache = (None, None)


class Result:
    """Return Result(new_value, answer) from an update fn to store one thing and hand the caller another."""
    __slots__ = ('value', 'result')

    def __init__(self, value, result):
        self.value, self.result = value, result


class ProcLock:
    """🔒 An asyncio lock that also holds across PROCESSES (an OS file lock on <name>.lock beside the store), for whole-document JSON stores
    whose every load → change → save already sits inside `async with <lock>:`. Swapping the per-process asyncio.Lock for this one makes two
    uvicorn workers take turns, so neither saves over the other's write (and a payment checked inside the lock is seen by the other worker).
    The file lock is taken in a thread, so the event loop keeps answering while another worker holds it."""

    def __init__(self, path):
        self._where = path   # a path, or a function returning one (read at each use, so a test sandbox that moves the store moves the lock)
        self._a = None; self._fd = None

    @property
    def path(self):
        return Path(self._where() if callable(self._where) else self._where).with_suffix('.lock')

    def _alock(self):
        if self._a is None:
            self._a = asyncio.Lock()
        return self._a

    async def __aenter__(self):
        await self._alock().acquire()
        try:
            where = self.path; where.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(where, os.O_RDWR | os.O_CREAT, 0o600)
            try:
                await asyncio.to_thread(fcntl.flock, fd, fcntl.LOCK_EX)
            except BaseException:
                os.close(fd); raise
            self._fd = fd
        except BaseException:
            self._a.release(); raise
        return self

    async def __aexit__(self, *exc):
        fd, self._fd = self._fd, None
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd); self._a.release()
        return False

    def locked(self):
        return self._a is not None and self._a.locked()


class SharedSet:
    """💳 A set every worker process shares (payment signatures taken by a request right now). `claim(x)` is ONE transaction: True for the
    first caller in any process, False for every other until it is discarded or `ttl` passes (a request that died mid-check never locks a
    payment forever; a payment that went through is kept for good in its own store). Same calls as a set: in · add · discard · clear."""

    def __init__(self, path, ttl=900):
        self._where = path; self.ttl = ttl; self._docs = {}   # a path or a function returning one (read at each use: test sandboxes)

    @property
    def docs(self):
        p = str(self._where() if callable(self._where) else self._where)
        return self._docs.get(p) or self._docs.setdefault(p, Docs(p))

    def _fresh(self, v):
        return bool(v) and time.time() - float(v.get('at') or 0) < self.ttl

    def claim(self, x):
        x = str(x)
        return self.docs.update(x, lambda cur: Result(cur, False) if self._fresh(cur) else Result({'at': time.time()}, True))

    def add(self, x):
        self.docs.put(str(x), {'at': time.time()})

    def discard(self, x):
        if x:
            self.docs.update(str(x), lambda _cur: None)

    def clear(self):
        self.docs.replace_all({})

    def __contains__(self, x):
        return self._fresh(self.docs.get(str(x)))
