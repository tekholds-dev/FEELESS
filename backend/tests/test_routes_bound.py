"""Every route answers with the function written for it, and every call inside the service passes arguments that function accepts.
Two real breaks found from the logs on 2026-10-13: a helper inserted between a route decorator and its handler bound the public coin
intel route to the helper (422 on every read for two days), and an owner button called `_audit` with the wrong arguments (500 on
every click)."""
import ast
from pathlib import Path

import reputation_service as rs

SRC = (Path(__file__).resolve().parent.parent / 'reputation_service.py').read_text()


def test_no_route_is_bound_to_a_private_helper():
    bad = [(r.path, r.endpoint.__name__) for r in rs.app.routes if getattr(r, 'endpoint', None) is not None and r.endpoint.__name__.startswith('_')]
    assert not bad, bad
    intel = [r for r in rs.app.routes if getattr(r, 'path', '') == '/api/reputation/intel/{chain}/{mint}']
    assert intel and intel[0].endpoint.__name__ == 'token_intel'


def test_every_call_to_a_module_function_passes_arguments_it_accepts():
    tree = ast.parse(SRC)
    defs, seen = {}, set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = n.args
            if n.name in seen or a.vararg or a.kwarg:      # defined twice / takes anything: not judged
                defs.pop(n.name, None); seen.add(n.name); continue
            seen.add(n.name)
            defs[n.name] = (len(a.args) - len(a.defaults), len(a.args), {x.arg for x in a.args + a.kwonlyargs},
                            {x.arg for x, d in zip(a.kwonlyargs, a.kw_defaults) if d is None})
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in defs:
            if any(isinstance(x, ast.Starred) for x in n.args) or any(k.arg is None for k in n.keywords):
                continue
            req, mx, names, need_kw = defs[n.func.id]
            kw = {k.arg for k in n.keywords}
            if len(n.args) > mx or len(n.args) + len(kw & names - need_kw) < req or not kw <= names or not need_kw <= kw:
                bad.append((n.lineno, n.func.id))
    assert not bad, bad
