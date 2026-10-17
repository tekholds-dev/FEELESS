"""🗄 SQLite store for data that must never be half-written (real money first). Stdlib only, crash-safe:

  • `KV(path)`: named JSON documents in one SQLite file (WAL journal, one transaction per write — a crash can't leave half a file);
  • `Ledger(path)`: an append-only audit table (rows are never edited or trimmed — the full history stays forever).

A JSON file that already exists next to it (same name, .json) is imported once on first open, so moving a store over is lossless.
Migration path for the rest of FEELESS: move a store here when it holds money / audit data or is written very often.
"""
import json
import sqlite3
import threading
import time
from pathlib import Path

_locks: dict = {}
_made: set = set()   # (db, table) already created in this process


def _conn(db):
    c = sqlite3.connect(str(db), timeout=10, isolation_level=None)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=NORMAL')
    return c


class KV:
    def __init__(self, json_path):
        self.json_path = Path(json_path)
        self.db = self.json_path.with_suffix('.db')
        self.lock = _locks.setdefault(str(self.db), threading.Lock())
        with self.lock:
            fresh = not self.db.exists()
            c = _conn(self.db)
            c.execute('CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL, at REAL NOT NULL)')
            if fresh and self.json_path.exists():   # one-time lossless import of the old JSON file
                try:
                    c.execute('INSERT OR REPLACE INTO kv VALUES (?, ?, ?)', ('doc', self.json_path.read_text(), time.time()))
                except (OSError, ValueError):
                    pass
            c.close()

    def get(self, default=None, key='doc'):
        with self.lock:
            c = _conn(self.db)
            row = c.execute('SELECT v FROM kv WHERE k = ?', (key,)).fetchone()
            c.close()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except ValueError:
            return default

    def stamp(self, key='doc'):
        """When this key was last written (None = never): lets a read-only caller reuse its parsed copy until the next put."""
        with self.lock:
            c = _conn(self.db)
            row = c.execute('SELECT at FROM kv WHERE k = ?', (key,)).fetchone()
            c.close()
        return row[0] if row else None

    def put(self, value, key='doc'):
        blob = json.dumps(value)
        with self.lock:
            c = _conn(self.db)
            c.execute('BEGIN IMMEDIATE')
            c.execute('INSERT OR REPLACE INTO kv VALUES (?, ?, ?)', (key, blob, time.time()))
            c.execute('COMMIT')
            c.close()


class Ledger:
    def __init__(self, json_path, table='ledger'):
        self.db = Path(json_path).with_suffix('.db')
        self.table = table
        self.lock = _locks.setdefault(str(self.db), threading.Lock())
        key = (str(self.db), table)
        if key in _made and self.db.exists():   # ⚡ the table exists already: no connection + CREATE on every construction
            return
        with self.lock:
            c = _conn(self.db)
            c.execute(f'CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, card TEXT, row TEXT NOT NULL)')
            c.close()
        _made.add(key)

    def append(self, row):
        with self.lock:
            c = _conn(self.db)
            c.execute(f'INSERT INTO {self.table} (at, card, row) VALUES (?, ?, ?)', (float(row.get('at') or time.time()), str(row.get('card') or ''), json.dumps(row)))
            c.close()

    def rows(self, limit=200, card=None):
        with self.lock:
            c = _conn(self.db)
            q = f'SELECT row FROM {self.table}' + (' WHERE card = ?' if card else '') + ' ORDER BY id DESC LIMIT ?'
            out = [json.loads(r[0]) for r in c.execute(q, ((card, limit) if card else (limit,))).fetchall()]
            c.close()
        return out

    def since(self, after_id=0):
        """Rows appended after `after_id`, oldest first → (rows, last id). Lets a reader keep the whole table in memory and fetch only
        what is new (re-reading thousands of rows for every appended one blocked the service)."""
        with self.lock:
            c = _conn(self.db)
            got = c.execute(f'SELECT id, row FROM {self.table} WHERE id > ? ORDER BY id ASC', (int(after_id or 0),)).fetchall()
            c.close()
        return [json.loads(r[1]) for r in got], (got[-1][0] if got else int(after_id or 0))

    def last_id(self):
        """The newest row's id (0 = empty) — O(1) on the primary key, unlike COUNT(*) which walks the whole table."""
        with self.lock:
            c = _conn(self.db)
            n = c.execute(f'SELECT MAX(id) FROM {self.table}').fetchone()[0]
            c.close()
        return int(n or 0)

    def count(self):
        with self.lock:
            c = _conn(self.db)
            n = c.execute(f'SELECT COUNT(*) FROM {self.table}').fetchone()[0]
            c.close()
        return n
