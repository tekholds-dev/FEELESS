"""Event-loop lag catcher (backend twin of HQ › Lag catcher).

A daemon thread pings the loop every TICK seconds. While a ping is unanswered for more than THRESH the loop thread is
blocked by synchronous code: its stack is sampled and the blocked time is charged to the project frames on it. Bounded:
at most KEEP culprits and LAST recent stalls are kept. Costs one call_soon_threadsafe per TICK when the loop is healthy.
"""
import os
import sys
import threading
import time

TICK = 0.05
THRESH = 0.25
KEEP = 60
LAST = 30
ROOT = os.path.dirname(os.path.abspath(__file__))


def culprit(frame, root=ROOT, depth=3):
    """'outer › … › inner:line' from the project frames of a stack (innermost last); '' when none are ours."""
    ours = []
    while frame is not None:
        fn = frame.f_code.co_filename
        if fn.startswith(root) and os.sep + '.venv' + os.sep not in fn and os.path.basename(fn) != 'loop_lag.py':
            ours.append((os.path.basename(fn)[:-3], frame.f_code.co_name, frame.f_lineno))
        frame = frame.f_back
    if not ours:
        return ''
    ours.reverse()
    outer, inner = ours[0], ours[-1]
    mid = ours[1:-1][-(depth - 2):] if depth > 2 else []
    parts = [f'{outer[0]}.{outer[1]}'] + [m[1] for m in mid]
    if len(ours) > 1:
        parts.append(f'{inner[1]}:{inner[2]}')
    return ' › '.join(parts)


class Watch:
    def __init__(self, thresh=THRESH, keep=KEEP, last=LAST):
        self.thresh, self.keep, self.last = thresh, keep, last
        self.where = {}          # culprit -> blocked seconds
        self.recent = []         # [{at, sec, where}]
        self.stalls = 0
        self.blocked = 0.0
        self.worst = 0.0
        self.since = time.time()
        self._sent = 0.0
        self._back = True
        self._thread = None
        self._stop = False

    def charge(self, key, sec):
        key = key or '(outside the project)'
        self.where[key] = self.where.get(key, 0.0) + sec
        if len(self.where) > self.keep:
            for k, _ in sorted(self.where.items(), key=lambda kv: kv[1])[:len(self.where) - self.keep]:
                self.where.pop(k, None)

    def stall(self, sec, hits, now=None, others=None):
        """One finished stall: `hits` = {culprit: samples} seen while it lasted; `others` = what worker threads were running (a
        thread that holds the GIL freezes the loop just the same)."""
        self.stalls += 1
        self.blocked += sec
        self.worst = max(self.worst, sec)
        top = max(hits.items(), key=lambda kv: kv[1])[0] if hits else ''
        row = {'at': round(now if now is not None else time.time(), 1), 'sec': round(sec, 2), 'where': top or '(outside the project)'}
        if others:
            row['threads'] = [k for k, _ in sorted(others.items(), key=lambda kv: -kv[1])[:4]]
        self.recent.append(row)
        del self.recent[:-self.last]

    def view(self, now=None):
        now = now if now is not None else time.time()
        span = max(1.0, now - self.since)
        return {'since': round(self.since, 1), 'spanSec': round(span), 'stalls': self.stalls, 'blockedSec': round(self.blocked, 1),
                'blockedPct': round(100 * self.blocked / span, 1), 'worstSec': round(self.worst, 2), 'threshSec': self.thresh,
                'top': [{'where': k, 'sec': round(v, 1)} for k, v in sorted(self.where.items(), key=lambda kv: -kv[1])[:20]],
                'recent': self.recent[-self.last:]}

    def reset(self):
        self.where, self.recent, self.stalls, self.blocked, self.worst, self.since = {}, [], 0, 0.0, 0.0, time.time()

    def _pong(self):
        self._back = True

    def _run(self, loop, ident):
        hits, others, sampled = {}, {}, 0.0
        me = threading.get_ident()
        while not self._stop:
            time.sleep(TICK)
            now = time.time()
            if self._back:
                if hits:
                    self.stall(now - self._sent, hits, now, others)
                    hits, others = {}, {}
                self._back, self._sent, sampled = False, now, now
                try:
                    loop.call_soon_threadsafe(self._pong)
                except RuntimeError:
                    return
                continue
            if now - self._sent < self.thresh:
                continue
            frames = sys._current_frames()
            frame = frames.get(ident)
            key = culprit(frame) if frame is not None else ''
            for tid, fr in frames.items():
                if tid not in (ident, me):
                    ok = culprit(fr)
                    if ok:
                        others[ok] = others.get(ok, 0) + 1
            hits[key] = hits.get(key, 0) + 1
            self.charge(key, now - sampled if len(hits) > 1 or hits[key] > 1 else now - self._sent)
            sampled = now

    def start(self, loop, ident=None):
        if self._thread:
            return
        self._thread = threading.Thread(target=self._run, args=(loop, ident or threading.get_ident()), name='loop-lag', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True


WATCH = Watch()
