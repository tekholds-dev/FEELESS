#!/usr/bin/env python3
"""🧩 SITE-5 · move plain READ routes out of reputation_service.py into backend/rep_more_reads.py, the same way slices 2-7 did:
helpers stay in reputation_service and are looked up as `rs.NAME` when the route runs (tests that patch them still work), the route keeps
its exact path, method and parameters, and every moved name stays reachable on reputation_service as an alias.
A route is moved ONLY when the mover can be sure (anything else is skipped and said why):
  · GET only, path without 'admin', no money words in its source (sign / send / swap / withdraw / quote / transfer …)
  · decorated by plain @app.get(...) whose arguments name nothing from the module
  · parameters annotated / defaulted only with builtins, Optional, Query, Header, Request
  · no `global` / `nonlocal`, never binds or reads a name called `rs`, and no name is both a local and a module global
  .venv/bin/python scripts/move-routes.py            # dry run: what would move, what is skipped and why
  .venv/bin/python scripts/move-routes.py --apply    # move them (then: route-table.py --check, pyflakes, the backend tests)"""
import argparse
import ast
import builtins
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'backend' / 'reputation_service.py'
DST = ROOT / 'backend' / 'rep_more_reads.py'
MONEY = re.compile(r'sendTransaction|_circle\(|_circle_post|signedTransaction|/swap|withdraw|_rpc_broadcast|broadcast\(|payout|refund|deposit|transfer|quote|_require_owner|_require_admin|_is_staff', re.I)
OK_ANN = {'str', 'int', 'float', 'bool', 'dict', 'list', 'Optional', 'Query', 'Header', 'Request', 'None'}
BUILTINS = set(dir(builtins))


def bound_names(fn):
    out = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
    for a in (fn.args.vararg, fn.args.kwarg):
        if a:
            out.add(a.arg)
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n is not fn:
            out.add(n.name)
            if not isinstance(n, ast.ClassDef):
                out |= {a.arg for a in n.args.args + n.args.kwonlyargs + n.args.posonlyargs}
        elif isinstance(n, ast.Lambda):
            out |= {a.arg for a in n.args.args + n.args.kwonlyargs}
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            out |= {(a.asname or a.name).split('.')[0] for a in n.names}
        elif isinstance(n, ast.arg):
            out.add(n.arg)
    return out


def module_globals(tree):
    g = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            g.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            g |= {(a.asname or a.name).split('.')[0] for a in n.names}
        else:
            for t in ast.walk(n):
                if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store):
                    g.add(t.id)
    return g


def check(fn, src, glob):
    if len(fn.decorator_list) != 1:
        return 'not exactly one decorator'
    d = fn.decorator_list[0]
    if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and isinstance(d.func.value, ast.Name) and d.func.value.id == 'app' and d.func.attr == 'get'):
        return 'not @app.get'
    if not d.args or not isinstance(d.args[0], ast.Constant) or 'admin' in str(d.args[0].value):
        return 'admin path or computed path'
    if any(isinstance(n, ast.Name) for a in d.args[1:] + [k.value for k in d.keywords] for n in ast.walk(a)):
        return 'decorator names module values'
    for a in fn.args.args + fn.args.kwonlyargs:
        for n in ast.walk(a.annotation) if a.annotation else []:
            if isinstance(n, ast.Name) and n.id not in OK_ANN:
                return f'parameter type {n.id}'
    for dflt in fn.args.defaults + [x for x in fn.args.kw_defaults if x is not None]:
        for n in ast.walk(dflt):
            if isinstance(n, ast.Name) and n.id not in OK_ANN:
                return f'parameter default uses {n.id}'
    if fn.returns is not None:
        return 'return annotation'
    if any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(fn)):
        return 'global / nonlocal'
    if MONEY.search(src):
        return 'money / staff words'
    b = bound_names(fn)
    if 'rs' in b or any(isinstance(n, ast.Name) and n.id == 'rs' for n in ast.walk(fn)):
        return 'uses the name rs'
    clash = sorted((b & glob) - {a.arg for a in fn.args.args + fn.args.kwonlyargs})
    params = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
    if clash or (params & glob):
        return f'local shadows a module name ({", ".join(sorted(clash or params & glob))[:60]})'
    return None


def rewrite(fn, lines, glob):
    """Source of the moved route: @router.get, `rs = _rs()` first, every module global read as rs.NAME (column-exact, right to left)."""
    start = fn.decorator_list[0].lineno - 1; end = fn.end_lineno
    seg = lines[start:end]
    hits = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in glob and n.id not in OK_ANN and n is not None:
            if any(n is x for x in ast.walk(fn.decorator_list[0])):
                continue
            hits.append((n.lineno - 1 - start, n.col_offset, n.id))
    for li, col, name in sorted(hits, key=lambda h: (h[0], -h[1])):
        pass
    by_line = {}
    for li, col, name in hits:
        by_line.setdefault(li, []).append((col, name))
    for li, cols in by_line.items():
        s = seg[li]
        for col, name in sorted(cols, reverse=True):
            assert s[col:col + len(name)] == name, (fn.name, s, col, name)
            s = s[:col] + 'rs.' + s[col:]
        seg[li] = s
    seg[0] = seg[0].replace('@app.get(', '@router.get(', 1)
    body0 = fn.body[0]
    doc = isinstance(body0, ast.Expr) and isinstance(body0.value, ast.Constant) and isinstance(body0.value.value, str)
    at = (body0.end_lineno if doc else body0.lineno) - start   # insert after the docstring, or before the first statement
    indent = re.match(r'\s*', lines[fn.body[0].lineno - 1]).group(0)
    seg.insert(at if doc else at - 1, f'{indent}rs = _rs()\n')
    return ''.join(seg), (start, end)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true'); ap.add_argument('--max', type=int, default=400); a = ap.parse_args()
    text = SRC.read_text(); lines = text.splitlines(keepends=True); tree = ast.parse(text); glob = module_globals(tree)
    called = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    moves, skips = [], {}
    pats = []   # every GET path in the app, as a regex: a moved route lands LAST, so it must not be catchable by any other path pattern
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ('get', 'api_route') and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str) and n.args[0].value.startswith('/'):
            pth = n.args[0].value
            if '{' in pth:
                pats.append((pth, re.compile('^' + re.sub(r'\\\{[^}]+\\\}', '[^/]+', re.escape(pth)) + '$')))
    for f in sorted(ROOT.joinpath('backend').glob('rep_*.py')):
        for pth in re.findall(r"@router\.(?:get|api_route)\('([^']+)'", f.read_text()):
            if '{' in pth:
                pats.append((pth, re.compile('^' + re.sub(r'\\\{[^}]+\\\}', '[^/]+', re.escape(pth)) + '$')))
    for fn in tree.body:
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or not fn.decorator_list:
            continue
        d = fn.decorator_list[0]
        if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and getattr(d.func.value, 'id', '') == 'app'):
            continue
        src = ''.join(lines[d.lineno - 1:fn.end_lineno])
        why = check(fn, src, glob - {fn.name})
        me = d.args[0].value if d.args and isinstance(d.args[0], ast.Constant) else ''
        if not why and any(o != me and rx.match(re.sub(r'\{[^}]+\}', 'x1y', me)) for o, rx in pats):
            why = 'another path pattern could catch it once it moves last'
        if why:
            skips.setdefault(why.split(' (')[0], []).append(fn.name)
            continue
        moves.append(fn)
    moves = moves[:a.max]
    print(f'move {len(moves)} read routes')
    for k, v in sorted(skips.items(), key=lambda kv: -len(kv[1])):
        print(f'  skip {len(v):>3}  {k}')
    if not a.apply:
        return 0
    out, cut = [], []
    for fn in moves:
        code, rng = rewrite(fn, lines, glob - {fn.name})
        out.append(code); cut.append(rng)
    for s, e in sorted(cut, reverse=True):
        del lines[s:e]
    names = [fn.name for fn in moves]
    alias = [f'{n} = _rep_more_reads.{n}\n' for n in names if n in called or True]
    tail = ('\nimport rep_more_reads as _rep_more_reads   # noqa: E402  🧩 SITE-5 slice 8: plain read routes, moved by scripts/move-routes.py\n'
            'app.include_router(_rep_more_reads.router)\n' + ''.join(alias))
    SRC.write_text(''.join(lines).rstrip('\n') + '\n' + tail)
    head = ('"""🧩 SITE-5 slice 8 (2026-11-13): plain read routes (GET, no admin, no money, no staff checks), moved out of reputation_service by\n'
            'scripts/move-routes.py. Helpers stay there and are looked up on reputation_service when a route runs, so a test that patches them still works."""\n'
            'from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401\n'
            'from typing import Optional  # noqa: F401\n\nrouter = APIRouter()\n\n\ndef _rs():\n    import reputation_service\n    return reputation_service\n\n\n')
    DST.write_text(head + '\n\n'.join(out) + '\n')
    print(f'moved {len(names)} → {DST.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
