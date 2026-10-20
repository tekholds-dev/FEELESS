"""🩺 LAG ADVISOR (owner, 2026-10-20: "give the lag catcher a cool vital upgrade … advising and suggesting"). Pure.
Reads what the lag catcher already measures — browser reports (perf.summarize), the event-loop watch (loop_lag view: blocked %, worst
stall, top culprits, JSON load / save costs) and the machine (load, swap) — and turns it into a ranked list of advice: what is slow,
the number that says so, and the fix that applies to THAT cause. Nothing here changes anything; it is a read."""

LEVEL = {'bad': 0, 'warn': 1, 'ok': 2}


def _r(level, area, what, why, fix, where=None):
    return {'level': level, 'area': area, 'what': what, 'why': why, 'fix': fix, 'where': where}


def advise(summary=None, loop=None, machine=None):
    s, lp, m = summary or {}, loop or {}, machine or {}
    out = []
    # 🖥 the machine first: a full swap makes every other number lie
    sw, load, cores = m.get('swapPct'), m.get('load1'), m.get('cores') or 8
    if sw is not None and sw >= 85:
        out.append(_r('bad', 'machine', f'Swap {sw:.0f}% full', 'Every parse and paint waits on disk when memory is full — no code fix beats this.',
                      'Close a Chrome window or unload the local model in LM Studio; the desktop model can carry the chat.', 'this Mac'))
    if load is not None and load >= cores * 1.5:
        out.append(_r('warn', 'machine', f'Load {load:.1f} on {cores} cores', 'More work queued than the CPU can run.',
                      'Pause a background lane (Brain ⚙ local boost off) or close the dev server and use fast mode (scripts/serve-fast.sh).', 'this Mac'))
    # ⏳ the server loop
    bp, worst = lp.get('blockedPct'), lp.get('worstSec')
    if bp is not None and bp >= 10:
        out.append(_r('bad' if bp >= 25 else 'warn', 'server', f'Event loop blocked {bp:.0f}% of the time', 'Every request waits while the loop is stuck.',
                      'Fix the top culprit below first — it is where the blocked time was measured.', 'reputation_service'))
    if worst is not None and worst >= 3:
        out.append(_r('warn', 'server', f'Worst stall {worst:.1f}s', 'One step held the loop that long; anyone loading a page then waited too.',
                      'Move that step to a worker thread or cache it.', 'loop_lag top'))
    for t in (lp.get('top') or [])[:3]:
        sec = t.get('sec') or 0
        if sec >= 0.3:
            out.append(_r('warn', 'server', f'{t.get("where", "?")}', f'{sec:.1f}s of blocked loop time charged here.',
                          'Read-only callers should reuse a parsed copy; heavy builds belong in a thread.', t.get('where')))
    for row in (lp.get('json') or [])[:4]:
        try:
            name, n, sec = row[0], int(row[1]), float(row[2])
        except (TypeError, ValueError, IndexError):
            continue
        if sec >= 15 and n >= 200:
            kind, file = (name.split(':', 1) + [''])[:2]
            fix = (f'{file} is rewritten {n}× ({sec / n * 1000:.0f} ms each) — debounce its saves (write ≤ every few seconds, flush on stop) or keep it in a MemStore.'
                   if kind == 'save' else f'{file} is parsed {n}× — read it through the parse cache (_json_load) or keep it in memory.')
            out.append(_r('warn' if sec < 60 else 'bad', 'storage', f'{name} · {sec:.0f}s total', f'{n} times in the watch window.', fix, file))
    # 🌐 what browsers feel
    for r in (s.get('routes') or [])[:12]:
        p95, calls = r.get('p95') or 0, r.get('calls') or 0
        if p95 >= 2500 and calls >= 3:
            p50 = r.get('p50') or 0
            why = 'Fast most of the time, slow on a cold cache' if p50 < 800 else 'Slow every time'
            fix = ('Serve the last copy and rebuild in the background (stale-while-revalidate).' if p50 < 800
                   else 'Run its independent lookups in parallel (asyncio.gather) and cache the answer.')
            out.append(_r('bad' if p95 >= 6000 else 'warn', 'api', f'{r.get("route")} · p95 {p95 / 1000:.1f}s', f'{why} ({calls} calls, p50 {p50} ms).', fix, r.get('route')))
    for p in (s.get('pages') or [])[:8]:
        fps, jank = p.get('fps'), p.get('jankMsPerReport') or 0
        if (fps is not None and fps < 30) or jank >= 400:
            out.append(_r('warn', 'page', f'{p.get("page")} · {fps if fps is not None else "—"} fps, {jank} ms jank',
                          'Main thread busy while this page was open.', 'Count non-transform animations and page-tall layers there; pause off-screen FX.', p.get('page')))
    out.sort(key=lambda a: LEVEL.get(a['level'], 3))
    return out[:14]


def vitals(summary=None, loop=None, machine=None, fx=None):
    """The strip on top: one number each, toned."""
    s, lp, m, f = summary or {}, loop or {}, machine or {}, fx or {}
    tone = lambda v, warn, bad, lower=False: None if v is None else ('bad' if (v <= bad if lower else v >= bad) else 'warn' if (v <= warn if lower else v >= warn) else 'ok')
    rows = [('SPEED', s.get('score'), '', tone(s.get('score'), 85, 60, True)),
            ('LOOP BLOCKED', lp.get('blockedPct'), '%', tone(lp.get('blockedPct'), 5, 20)),
            ('WORST STALL', lp.get('worstSec'), 's', tone(lp.get('worstSec'), 1, 4)),
            ('SWAP', m.get('swapPct'), '%', tone(m.get('swapPct'), 60, 85)),
            ('LOAD', m.get('load1'), '', tone(m.get('load1'), (m.get('cores') or 8), (m.get('cores') or 8) * 1.5)),
            ('FX PAUSED', f.get('paused'), '', None)]
    return [{'k': k, 'v': v, 'unit': u, 'tone': t} for k, v, u, t in rows]
