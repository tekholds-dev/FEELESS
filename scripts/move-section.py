#!/usr/bin/env python3
"""🧹 CLEANUP (owner 2026-11-16 "clean the code as priority … production ready"): move one whole SECTION of reputation_service.py (its helpers AND
its routes, by line range) into its own module, the way scripts/move-routes.py moved routes:
  · every module name the moved code reads becomes `rs.NAME`, looked up on reputation_service when it runs, so a test or module that patches
    rs.X still reaches the moved code (behaviour identical by construction); every moved name stays on reputation_service as an alias
  · the comment block right above a function moves with it; constants, classes and state stay where they are (moved code reads them as rs.X)
A function is moved ONLY when the mover can be sure, else it stays and says why:
  · no decorator, or exactly one @app.<verb>('/constant/path') whose path no other path pattern could catch once it registers last
  · no global / nonlocal, no class / match / walrus-in-comprehension inside, never binds or reads `rs` / `_rs` / `_RSM`
  · defaults and annotations name only builtins / Optional / Query / Header / Request (or a body model, read as _RSM.Model)
  · its name is never read while reputation_service is still loading (module level, a decorator, a default, a class body)
  .venv/bin/python scripts/move-section.py --from 12905 --to 18627 --name ai           # dry run
  .venv/bin/python scripts/move-section.py --from 12905 --to 18627 --name ai --apply   # then: pyflakes gate, the backend tests"""
import argparse
import ast
import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'backend' / 'reputation_service.py'
PREFIX = {'reputation_service': 'rep_', 'feecat_service': 'fc_'}   # --svc: the service a section leaves, and its new modules' prefix
_spec = importlib.util.spec_from_file_location('move_routes', ROOT / 'scripts' / 'move-routes.py'); mr = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(mr)
VERBS = ('get', 'post', 'put', 'delete', 'patch', 'api_route')


def import_time_loads(tree):
    """Names read while the module loads: module-level statements, decorators, defaults, annotations and class bodies (not function bodies)."""
    out = set()

    def walk(n):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = n.args
            for d in a.defaults + [d for d in a.kw_defaults if d] + (n.decorator_list if not isinstance(n, ast.Lambda) else []):
                walk(d)
            for x in a.posonlyargs + a.args + a.kwonlyargs:
                if x.annotation:
                    walk(x.annotation)
            if not isinstance(n, ast.Lambda) and n.returns:
                walk(n.returns)
            return
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            out.add(n.id)
        for c in ast.iter_child_nodes(n):
            walk(c)
    for st in tree.body:
        walk(st)
    return out


def why_not(fn, glob, models, early, pats):
    if fn.name in early:
        return 'read while the service loads'
    route = None
    if fn.decorator_list:
        if len(fn.decorator_list) != 1:
            return 'more than one decorator'
        d = fn.decorator_list[0]
        if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and getattr(d.func.value, 'id', '') == 'app' and d.func.attr in VERBS):
            return 'decorator is not @app.<verb>'
        if not d.args or not isinstance(d.args[0], ast.Constant) or not str(d.args[0].value).startswith('/'):
            return 'computed path'
        if any(isinstance(n, ast.Name) for a in d.args[1:] + [k.value for k in d.keywords] for n in ast.walk(a)):
            return 'decorator names module values'
        route = d.args[0].value
        if any(o != route and rx.match(re.sub(r'\{[^}]+\}', 'x1y', route)) for o, rx in pats):
            return 'another path pattern could catch it once it moves last'
    for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
        for n in ast.walk(a.annotation) if a.annotation else []:
            if isinstance(n, ast.Name) and n.id not in mr.OK_ANN and n.id not in models:
                return f'parameter type {n.id}'
    for dflt in fn.args.defaults + [x for x in fn.args.kw_defaults if x is not None]:
        if any(isinstance(n, ast.Name) and n.id not in mr.OK_ANN for n in ast.walk(dflt)):
            return 'default names a module value'
    if fn.returns is not None:
        return 'return annotation'
    if any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(fn)):
        return 'global / nonlocal'
    if mr.bound_names(fn) & {'rs', '_rs', '_RSM'} or any(isinstance(n, ast.Name) and n.id in ('rs', '_rs', '_RSM') for n in ast.walk(fn)):
        return 'uses the name rs'
    if any(isinstance(n, (ast.ClassDef, ast.Match)) for n in ast.walk(fn)):
        return 'class or match inside'
    if any(isinstance(m, ast.NamedExpr) for c in ast.walk(fn) if isinstance(c, mr.COMP) for m in ast.walk(c)):
        return 'walrus inside a comprehension'
    return None


def rewrite(fn, lines, glob, models):
    """The moved source: every module global read as rs.NAME (column exact, right to left), `rs = _rs()` as its first statement, @router for a route.
    Comment lines directly above it move with it. → (code, (start, end))"""
    start = (fn.decorator_list[0].lineno if fn.decorator_list else fn.lineno) - 1; end = fn.end_lineno
    while start and lines[start - 1].lstrip().startswith('#') and not lines[start - 1].startswith('# ----'):
        start -= 1
    seg = lines[start:end]
    col = lambda n: len(lines[n.lineno - 1].encode()[:n.col_offset].decode())
    hits = [(n.lineno - 1 - start, col(n), n.id, 'rs.') for n in mr.global_loads(fn, glob)]
    hits += [(n.lineno - 1 - start, col(n), n.id, '_RSM.') for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs if a.annotation
             for n in ast.walk(a.annotation) if isinstance(n, ast.Name) and n.id in models]
    by_line = {}
    for li, c, name, pre in hits:
        by_line.setdefault(li, []).append((c, name, pre))
    for li, cols in by_line.items():
        s = seg[li]
        for c, name, pre in sorted(cols, reverse=True):
            assert s[c:c + len(name)] == name, (fn.name, s, c, name)
            s = s[:c] + pre + s[c:]
        seg[li] = s
    if fn.decorator_list:
        di = fn.decorator_list[0].lineno - 1 - start
        seg[di] = re.sub(r'@app\.(get|post|put|delete|patch|api_route)\(', r'@router.\1(', seg[di], count=1)
    body0 = fn.body[0]
    doc = isinstance(body0, ast.Expr) and isinstance(body0.value, ast.Constant) and isinstance(body0.value.value, str)
    indent = re.match(r'\s*', lines[body0.lineno - 1]).group(0)
    if body0.lineno == fn.lineno:   # a one-line def: `def f(): return x` → split it so rs can come first
        return None, None
    if hits:
        at = (body0.end_lineno if doc else body0.lineno - 1) - start
        seg.insert(at, f'{indent}rs = _rs()\n')
    return ''.join(seg), (start, end)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='a', type=int, required=True); ap.add_argument('--to', dest='b', type=int, required=True)
    ap.add_argument('--name', required=True, help='the new module is backend/rep_<name>.py'); ap.add_argument('--apply', action='store_true')
    ap.add_argument('--title', default='', help='one line for the new module docstring')
    ap.add_argument('--svc', default='reputation_service', choices=sorted(PREFIX))
    o = ap.parse_args()
    global SRC
    SRC = ROOT / 'backend' / f'{o.svc}.py'; pre = PREFIX[o.svc]
    mod = f'{pre}{re.sub(r"[^a-z0-9_]", "", o.name.lower())}'; dst = ROOT / 'backend' / f'{mod}.py'
    text = SRC.read_text(); lines = text.splitlines(keepends=True); tree = ast.parse(text); glob = mr.module_globals(tree)
    models = set()
    for _ in range(4):
        models |= {n.name for n in tree.body if isinstance(n, ast.ClassDef) and any(getattr(b, 'id', '') in models | {'BaseModel'} for b in n.bases)}
    early = import_time_loads(tree)
    pats = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in VERBS and n.args and isinstance(n.args[0], ast.Constant) and str(n.args[0].value).startswith('/') and '{' in n.args[0].value:
            p = n.args[0].value; pats.append((p, re.compile('^' + re.sub(r'\\\{[^}]+\\\}', '[^/]+', re.escape(p)) + '$')))
    for f in sorted((ROOT / 'backend').glob(f'{pre}*.py')):
        for p in re.findall(r"@router\.(?:get|post|put|delete|patch|api_route)\('([^']+)'", f.read_text()):
            if '{' in p:
                pats.append((p, re.compile('^' + re.sub(r'\\\{[^}]+\\\}', '[^/]+', re.escape(p)) + '$')))
    moves, skips = [], {}
    for fn in tree.body:
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or not (o.a <= fn.lineno < o.b):
            continue
        why = why_not(fn, glob, models, early, pats)
        if not why and fn.body[0].lineno == fn.lineno:
            why = 'one-line def'
        (skips.setdefault(why, []).append(fn.name) if why else moves.append(fn))
    n_lines = sum(fn.end_lineno - (fn.decorator_list[0].lineno if fn.decorator_list else fn.lineno) + 1 for fn in moves)
    print(f'{mod}: move {len(moves)} functions ({sum(1 for f in moves if f.decorator_list)} routes, ~{n_lines} lines) from lines {o.a}-{o.b}')
    for k, v in sorted(skips.items(), key=lambda kv: -len(kv[1])):
        print(f'  stay {len(v):>3}  {k}: {", ".join(v[:6])}{" …" if len(v) > 6 else ""}')
    if not o.apply or not moves:
        return 0
    out, cut = [], []
    for fn in moves:
        code, rng = rewrite(fn, lines, glob, models)
        out.append(code); cut.append((*rng, fn.name))
    runs = []   # functions cut next to each other (only blank lines between) leave ONE marker: where the code went, in its old order
    for s, e, name in sorted(cut):
        if runs and all(not lines[k].strip() for k in range(runs[-1][1], s)):
            runs[-1][1] = e; runs[-1][2].append(name)
        else:
            runs.append([s, e, [name]])
    for s, e, names_ in reversed(runs):
        mark, row = [], f'# ↪ moved to {mod}.py:'
        for n in names_:
            if len(row) + len(n) > 150:
                mark.append(row.rstrip(',') + '\n'); row = f'# ↪ moved to {mod}.py:'
            row += f' {n},'
        mark.append(row.rstrip(',') + '\n')
        lines[s:e] = mark
    body = re.sub(r'\n{4,}', '\n\n\n', ''.join(lines))
    names = [fn.name for fn in moves]
    routes = any(fn.decorator_list for fn in moves)
    head = (f'"""🧹 {o.title or mod} — moved whole out of {o.svc}.py by scripts/move-section.py (owner 2026-11-16 cleanup).\n'
            f'Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches {o.svc} still\n'
            f'reaches it, and every function here is still reachable on {o.svc} under its own name. Constants, classes and state live in the service."""\n'
            + (f'import {o.svc} as _RSM  # noqa: E402,F401  (body models; this module is imported at the END of the service)\n' if routes else '')
            + ('from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401\nfrom typing import Optional  # noqa: F401\n\nrouter = APIRouter()\n\n\n' if routes else '\n\n')
            + f'def _rs():\n    import {o.svc}\n    return {o.svc}\n\n\n')
    if dst.exists():
        dst.write_text(dst.read_text().rstrip('\n') + '\n\n\n' + '\n\n'.join(out) + '\n')
    else:
        dst.write_text(head + '\n\n'.join(out) + '\n')
    wired = f'import {mod} as _{mod}' in body
    tail = ('' if wired else f'\nimport {mod} as _{mod}   # noqa: E402  🧹 moved by scripts/move-section.py\n' + (f'app.include_router(_{mod}.router)\n' if routes else '')) \
        + ''.join(f'{n} = _{mod}.{n}\n' for n in names)
    SRC.write_text(body.rstrip('\n') + '\n' + tail)
    print(f'moved {len(names)} → {dst.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
