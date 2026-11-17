#!/usr/bin/env python3
"""🗺 Which function answers each route of a service, the way the app really matches them (first match wins, included routers and all).
Run it before and after moving routes between modules: the two maps must be identical (a moved route keeps its function name).
  PYTHONPATH=backend .venv/bin/python scripts/route-map.py feecat_service > before.txt   (… after.txt; diff before.txt after.txt)"""
import importlib
import pathlib
import re
import sys

from starlette.routing import Match

ROOT = pathlib.Path(__file__).resolve().parent.parent
DECOR = re.compile(r"@(?:app|router)\.(get|post|put|delete|patch|websocket)\('([^']+)'")


def main():
    svc = sys.argv[1] if len(sys.argv) > 1 else 'reputation_service'
    pre = {'reputation_service': 'rep_', 'feecat_service': 'fc_'}[svc]
    app = importlib.import_module(svc).app
    asks = set()
    for f in [ROOT / 'backend' / f'{svc}.py', *sorted((ROOT / 'backend').glob(f'{pre}*.py'))]:
        asks |= {(v.upper(), re.sub(r'\{[^}:]+(:path)?\}', 'x1y', p)) for v, p in DECOR.findall(f.read_text())}
    for method, path in sorted(asks):
        kind = 'websocket' if method == 'WEBSOCKET' else 'http'
        scope = {'type': kind, 'path': path, 'root_path': '', 'method': 'GET' if kind == 'websocket' else method, 'headers': [], 'query_string': b''}
        hit = '—'
        for r in app.router.routes:
            m, child = r.matches(scope)
            if m == Match.FULL:
                ep = child.get('endpoint') or getattr(r, 'endpoint', None)
                hit = getattr(ep, '__name__', repr(ep)); break
        print(f'{method:<9} {path:<60} → {hit}')


if __name__ == '__main__':
    main()
