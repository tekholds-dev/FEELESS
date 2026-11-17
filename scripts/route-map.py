#!/usr/bin/env python3
"""🗺 Which function answers each route of a service, the way the app really matches them (first match wins, included routers and all).
  PYTHONPATH=backend .venv/bin/python scripts/route-map.py feecat_service            → print the map
  … route-map.py --write reputation_service feecat_service                          → save it as the baseline (scripts/route-maps/<svc>.txt)
  … route-map.py --check reputation_service feecat_service                          → exit 1 when a baseline route now reaches a DIFFERENT function
                                                                                      or no longer answers; a new route is only listed
The gate runs --check: moving code between modules must never change which function answers a route. A route renamed on purpose → --write."""
import importlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAPS = ROOT / 'scripts' / 'route-maps'
DECOR = re.compile(r"@(?:app|router)\.(get|post|put|delete|patch|websocket)\('([^']+)'")
PREFIX = {'reputation_service': 'rep_', 'feecat_service': 'fc_'}


def route_map(svc):
    from starlette.routing import Match
    app = importlib.import_module(svc).app
    asks = set()
    for f in [ROOT / 'backend' / f'{svc}.py', *sorted((ROOT / 'backend').glob(f'{PREFIX[svc]}*.py'))]:
        asks |= {(v.upper(), re.sub(r'\{[^}:]+(:path)?\}', 'x1y', p)) for v, p in DECOR.findall(f.read_text())}
    out = {}
    for method, path in sorted(asks):
        kind = 'websocket' if method == 'WEBSOCKET' else 'http'
        scope = {'type': kind, 'path': path, 'root_path': '', 'method': 'GET' if kind == 'websocket' else method, 'headers': [], 'query_string': b''}
        out[f'{method:<9} {path}'] = _first(app.router.routes, scope, Match) or '—'
    return out


def _first(routes, scope, Match):
    """The function of the first route that fully matches, in order. FastAPI ≥ 0.13x keeps an included router as ONE _IncludedRouter entry
    (it walks original_router.routes in order); older FastAPI copies its routes in. Both are walked the same way here."""
    for r in routes:
        inner = getattr(r, 'original_router', None)
        if inner is not None:
            hit = _first(inner.routes, scope, Match)
            if hit:
                return hit
            continue
        m, child = r.matches(scope)
        if m == Match.FULL:
            ep = child.get('endpoint') or getattr(r, 'endpoint', None)
            return getattr(ep, '__name__', repr(ep))
    return None


def render(m):
    return ''.join(f'{k:<70} → {v}\n' for k, v in sorted(m.items()))


def parse(text):
    return {k.rstrip(): v.strip() for k, v in (ln.split(' → ', 1) for ln in text.splitlines() if ' → ' in ln)}


def compare(base, now):
    """→ (problems, new routes). A problem: a baseline route that now reaches another function, or none."""
    bad = [f'{k}: was {v}, now {now.get(k, "gone")}' for k, v in sorted(base.items()) if now.get(k) != v]
    return bad, sorted(set(now) - set(base))


def main():
    args = sys.argv[1:]; mode = args.pop(0) if args and args[0] in ('--write', '--check') else None
    rc = 0
    for svc in args or ['reputation_service']:
        m = route_map(svc)
        if mode == '--write':
            MAPS.mkdir(exist_ok=True); (MAPS / f'{svc}.txt').write_text(render(m)); print(f'{svc}: {len(m)} routes saved')
        elif mode == '--check':
            bad, new = compare(parse((MAPS / f'{svc}.txt').read_text()), m)
            for b in bad:
                print(f'  ✗ {svc} {b}')
            print(f'{svc}: {len(m)} routes · {len(bad)} changed · {len(new)} new' + (f' ({", ".join(new[:4])}{" …" if len(new) > 4 else ""})' if new else ''))
            rc |= 1 if bad else 0
        else:
            sys.stdout.write(render(m))
    return rc


if __name__ == '__main__':
    sys.exit(main())
