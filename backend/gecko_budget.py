"""One GeckoTerminal budget shared by every FEELESS process (their public cap is 30 req/min per IP).
Charts get priority: background jobs may only use part of the minute, so candles always have room."""
import fcntl
import json
import time
from pathlib import Path

PATH = Path(__file__).parent / 'data' / 'gecko_budget.json'
CAP = 27                 # stay under GeckoTerminal's 30/min
BACKGROUND_CAP = 12      # globe/feeds may not use more than this in any minute
BACKOFF_SECONDS = 65


def take(kind: str = 'chart') -> bool:
    PATH.parent.mkdir(exist_ok=True)
    with open(PATH, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        try:
            d = json.loads(f.read() or '{}')
        except ValueError:
            d = {}
        now = time.time()
        calls = [c for c in d.get('calls', []) if now - c[0] < 60]
        ok = now >= d.get('blockedUntil', 0) and len(calls) < CAP and (kind == 'chart' or sum(1 for c in calls if c[1] != 'chart') < BACKGROUND_CAP)
        if ok:
            calls.append([now, kind])
        d['calls'] = calls
        f.seek(0); f.truncate(); f.write(json.dumps(d))
        fcntl.flock(f, fcntl.LOCK_UN)
    return ok


def throttled():
    """Call on a 429: every process pauses GeckoTerminal until the window resets."""
    PATH.parent.mkdir(exist_ok=True)
    with open(PATH, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        try:
            d = json.loads(f.read() or '{}')
        except ValueError:
            d = {}
        d['blockedUntil'] = time.time() + BACKOFF_SECONDS
        f.seek(0); f.truncate(); f.write(json.dumps(d))
        fcntl.flock(f, fcntl.LOCK_UN)
