"""Lag catcher: aggregate what real browsers report (API latency, long tasks, FPS) and name the fix.
Pure functions; the service stores the samples and serves the summary to HQ."""
import re

_ID = re.compile(r'/(?:[1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40}|\d+)(?=/|$)')


def route_key(path: str) -> str:
    """/api/market/pair/solana/Abc…xyz?x=1 → /api/market/pair/solana/:id (so routes group)."""
    return _ID.sub('/:id', (path or '').split('?')[0])[:120]


def _pct(xs, q):
    if not xs:
        return 0
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(q * len(xs)))])


def summarize(samples: list) -> dict:
    """samples: [{page, api: {route: [ms…]}, longTasks, longMs, fps, lite, errors}] from the last window."""
    api, pages = {}, {}
    for s in samples:
        for route, ms in (s.get('api') or {}).items():
            api.setdefault(route_key(route), []).extend(float(x) for x in ms[:50] if isinstance(x, (int, float)))
        pg = pages.setdefault(str(s.get('page') or '/')[:60], {'reports': 0, 'longTasks': 0, 'longMs': 0, 'fps': [], 'lite': 0, 'errors': 0})
        pg['reports'] += 1; pg['longTasks'] += int(s.get('longTasks') or 0); pg['longMs'] += int(s.get('longMs') or 0)
        pg['lite'] += 1 if s.get('lite') else 0; pg['errors'] += int(s.get('errors') or 0)
        for k, n in (s.get('errRoutes') or {}).items():
            pg.setdefault('errRoutes', {})[str(k)[:110]] = pg.get('errRoutes', {}).get(str(k)[:110], 0) + int(n or 0)
        if s.get('fps'):
            pg['fps'].append(float(s['fps']))
        lay = s.get('layout') or {}
        if lay:   # 🧱 the page watcher: sideways scroll + which classes spill / sit covered
            pg['sideways'] = max(pg.get('sideways', 0), int(lay.get('sideways') or 0))
            for kind in ('spills', 'covered'):
                for c in lay.get(kind) or []:
                    pg.setdefault(kind, {})[c] = pg.get(kind, {}).get(c, 0) + 1
    routes = sorted(({'route': r, 'calls': len(ms), 'p50': _pct(ms, .5), 'p95': _pct(ms, .95)} for r, ms in api.items() if ms), key=lambda r: -r['p95'])
    page_rows = sorted(({'page': p, 'reports': v['reports'], 'longTasks': v['longTasks'], 'jankMsPerReport': round(v['longMs'] / v['reports']),
                         'fps': round(sum(v['fps']) / len(v['fps'])) if v['fps'] else None, 'autoLite': v['lite'], 'errors': v['errors'],
                         'errRoutes': dict(sorted((v.get('errRoutes') or {}).items(), key=lambda kv: -kv[1])[:8]),
                         'sideways': v.get('sideways', 0), 'spills': sorted(v.get('spills') or {}, key=lambda k: -v['spills'][k])[:5],
                         'covered': sorted(v.get('covered') or {}, key=lambda k: -v['covered'][k])[:5]}
                        for p, v in pages.items()), key=lambda r: -r['jankMsPerReport'])
    fixes = []
    for r in routes[:8]:
        if r['p95'] >= 2500:
            fixes.append({'level': 'bad', 'what': f"{r['route']} p95 {r['p95']}ms", 'fix': 'Cache it server-side (_cached_json / TTL) and prefetch it before the click.'})
        elif r['p95'] >= 1200:
            fixes.append({'level': 'warn', 'what': f"{r['route']} p95 {r['p95']}ms", 'fix': 'Run its upstream lookups in parallel (asyncio.gather) or share one poller.'})
    for p in page_rows[:6]:
        if p['fps'] is not None and p['fps'] < 40:
            fixes.append({'level': 'bad', 'what': f"{p['page']} runs at {p['fps']} fps", 'fix': 'Heavy animation on this page: turn on site-wide lite effects or trim its backdrop.'})
        elif p['jankMsPerReport'] >= 400:
            fixes.append({'level': 'warn', 'what': f"{p['page']} blocks the main thread {p['jankMsPerReport']}ms/min", 'fix': 'Split the render (memo lists, virtualize long feeds, debounce inputs).'})
    for p in page_rows:   # 🧱 layout: every page that spills / overlaps / scrolls sideways for a real user, named
        if p.get('sideways'):
            fixes.append({'level': 'bad', 'what': f"{p['page']} scrolls sideways by {p['sideways']}px", 'fix': 'A child is wider than the screen: give the grid / flex child min-width: 0 or clip the decorative bleed.'})
        if p.get('spills'):
            fixes.append({'level': 'warn', 'what': f"{p['page']} text runs out of its box: .{', .'.join(p['spills'][:3])}", 'fix': 'min-width: 0 on the flex / grid child, or overflow-wrap: anywhere / an ellipsis on that class.'})
        if p.get('covered'):
            fixes.append({'level': 'warn', 'what': f"{p['page']} buttons covered by another layer: .{', .'.join(p['covered'][:3])}", 'fix': 'Raise the button (z-index) or move the floating layer off it.'})
    return {'routes': routes[:25], 'pages': page_rows[:25], 'fixes': fixes, 'reports': len(samples),
            'score': max(0, 100 - 12 * sum(f['level'] == 'bad' for f in fixes) - 5 * sum(f['level'] == 'warn' for f in fixes))}
