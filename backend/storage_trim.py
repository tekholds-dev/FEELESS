"""🧹 STORAGE TRIM — caches and logs that grew without a cap (2026-10-12 audit: backend/data/logos = 1.0 GB in 4,578 files, single
logos up to 2.5 MB; /tmp/feeless-api.log 19 MB and growing).

Only RE-FETCHABLE / DIAGNOSTIC data is trimmed here:
  · the coin-logo cache (any logo comes back from its source on the next request) — newest kept, total ≤ LOGO_MAX_BYTES, nothing
    younger than LOGO_KEEP_SEC is ever removed, and a single logo over LOGO_FILE_MAX is served but not cached
  · service logs in /tmp (feeless-*.log) — over LOG_MAX_BYTES the file keeps only its newest LOG_KEEP_BYTES (appending writers keep
    appending; nothing is lost from a ledger because no ledger is a log)
NEVER touched: ledgers, .db files, records, archives, agent lineage, anything outside these two places. `plan_*` are pure."""
import os
import time
from pathlib import Path

LOGO_MAX_BYTES = 300 * 1024 * 1024
LOGO_FILE_MAX = int(1.5 * 1024 * 1024)
LOGO_KEEP_SEC = 24 * 3600
LOG_MAX_BYTES = 20 * 1024 * 1024
LOG_KEEP_BYTES = 5 * 1024 * 1024
LOG_GLOB = 'feeless-*.log'


def plan_logos(files, now, max_bytes=LOGO_MAX_BYTES, keep_sec=LOGO_KEEP_SEC):
    """[(name, size, mtime)] → the names to delete: oldest first until the total is under `max_bytes`; never one newer than keep_sec."""
    total = sum(s for _n, s, _m in files)
    out = []
    for name, size, mt in sorted(files, key=lambda f: f[2]):
        if total <= max_bytes:
            break
        if now - mt < keep_sec:
            break                      # everything after this is newer still
        out.append(name)
        total -= size
    return out


def cache_logo_ok(body):
    """A logo body worth caching on disk (a 2.5 MB PNG is served once, not stored forever)."""
    return body is not None and 0 < len(body) <= LOGO_FILE_MAX


def plan_log(size, max_bytes=LOG_MAX_BYTES, keep=LOG_KEEP_BYTES):
    """→ bytes to keep from the end of a log (None = leave it alone)."""
    return keep if size > max_bytes else None


def trim_logos(d, now=None, max_bytes=None):
    d = Path(d)
    if not d.is_dir():
        return {'files': 0, 'freed': 0}
    now = time.time() if now is None else now
    files = []
    for f in d.iterdir():
        try:
            st = f.stat()
            if f.is_file():
                files.append((f.name, st.st_size, st.st_mtime))
        except OSError:
            continue
    gone, freed = plan_logos(files, now, LOGO_MAX_BYTES if max_bytes is None else max_bytes), 0
    sizes = {n: s for n, s, _m in files}
    for n in gone:
        try:
            (d / n).unlink()
            freed += sizes[n]
        except OSError:
            pass
    return {'files': len(gone), 'freed': freed, 'kept': len(files) - len(gone)}


def trim_logs(d='/tmp'):
    out = []
    for f in Path(d).glob(LOG_GLOB):
        try:
            keep = plan_log(f.stat().st_size)
            if keep is None:
                continue
            with open(f, 'rb+') as fh:
                fh.seek(-keep, os.SEEK_END)
                tail = fh.read()
                fh.seek(0)
                fh.write(b'[... older lines trimmed by storage_trim ...]\n' + tail)
                fh.truncate()
            out.append(f.name)
        except OSError:
            continue
    return out
