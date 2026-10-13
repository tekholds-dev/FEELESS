"""💾 ONE JSON STORE IN MEMORY (owner, 2026-10-12: "storage efficient"). The agents' pass re-parsed and re-wrote ~9 MB of JSON every
~30s — agents.json (3 MB) was LOADED and SAVED on every pass, trench_lingo.json (1.3 MB) too; the loop-lag catcher charged them ~13s of
blocked event loop in 25 minutes. A MemStore is loaded once, kept as the live object, and written at most every `every` seconds (and on
`flush`, which the service calls at shutdown). A crash loses at most `every` seconds of THAT store — never use it for money records.

The path is looked up at CALL time (`path_of()`), so the test sandbox (conftest re-points module Paths per test) is always honoured: a new
path = a fresh load, never another test's object. Pure apart from the injected load / save functions."""
import time


class MemStore:
    def __init__(self, path_of, every, load, save, default=dict):
        self.path_of, self.every, self._load, self._save, self.default = path_of, float(every), load, save, default
        self.obj, self.key, self.savedAt, self.dirty = None, None, 0.0, False
        self.stats = {'loads': 0, 'saves': 0, 'skipped': 0}

    def get(self):
        """The live object (loaded from disk once per path)."""
        k = str(self.path_of())
        if self.obj is None or self.key != k:
            self.obj = self._load(self.path_of(), self.default())
            if not isinstance(self.obj, dict) and self.default is dict:
                self.obj = {}
            self.key, self.savedAt, self.dirty = k, time.time(), False
            self.stats['loads'] += 1
        return self.obj

    def put(self, obj, now=None, force=False):
        """Replace the live object; write it if `every` seconds passed since the last write (or `force`). → True when written."""
        now = time.time() if now is None else now
        self.get()   # binds the current path (a put before any get must not write to a stale one)
        self.obj, self.dirty = obj, True
        if force or now - self.savedAt >= self.every:
            return self.flush(now)
        self.stats['skipped'] += 1
        return False

    def flush(self, now=None):
        """Write the live object now if it changed since the last write. → True when written."""
        if self.obj is None or not self.dirty:
            return False
        self._save(self.path_of(), self.obj)
        self.savedAt, self.dirty = (time.time() if now is None else now), False
        self.stats['saves'] += 1
        return True
