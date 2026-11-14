"""🧩 SITE-5: the route mover reads module globals by Python's own scope rules, so a moved route that reuses a module name as a local
still reads its own local (and every real global becomes rs.NAME)."""
import ast
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('move_routes', ROOT / 'scripts' / 'move-routes.py')
mr = importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)


def globs(src, glob):
    fn = ast.parse(src).body[0]
    return sorted(n.id for n in mr.global_loads(fn, set(glob)))


def test_locals_params_comprehensions_and_lambdas_shadow_module_names():
    G = {'x', 'p', 'P', 'A', 'items', 'helper', 'k', 'v', 'D'}
    assert globs('def f():\n    x = 1\n    return x', G) == []                                      # a local, even though x is global
    assert globs('def f():\n    y = x\n    x = 2\n    return y', G) == []                          # bound later = local everywhere (Python)
    assert globs('def f():\n    return [p for p in P]', G) == ['P']                                  # comprehension var vs its global iterable
    assert globs('def f(items):\n    return [x for x in items if x]', G) == []                       # first iterable runs in f's scope
    assert globs('def f():\n    return list(map(lambda A: A + 1, P))', G) == ['P']                 # lambda param
    assert globs('def f():\n    x = 3\n    def g():\n        return x + A\n    return g()', G) == ['A']   # closure reads f's x
    assert globs('def f():\n    return {k: v for k, v in D.items()}', G) == ['D']
    assert globs('def f():\n    return helper(x)', G) == ['helper', 'x']                            # plain globals still found
    assert globs('def f():\n    try:\n        pass\n    except Exception as v:\n        return v', G) == []


def test_shapes_it_does_not_model_are_refused():
    fn = ast.parse('@app.get("/x")\ndef f():\n    return [y := 1 for _ in range(2)]').body[0]
    assert mr.check(fn, '', set()) == 'walrus inside a comprehension'


def test_no_moved_route_hides_the_service_lookup():
    """2026-11-14: a moved admin route did `import range_sim as _rs`, which made `_rs` local to it, so `rs = _rs()` raised → 500.
    Every moved route must leave the names rs / _rs / _RSM to the mover, and the mover refuses one that binds them."""
    import ast
    import pathlib
    for f in sorted((pathlib.Path(__file__).resolve().parents[1]).glob('rep_*.py')):
        for fn in ast.parse(f.read_text()).body:
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name != '_rs':
                bound = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)} - {'rs'}
                bound |= {(a.asname or a.name).split('.')[0] for n in ast.walk(fn) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
                assert not bound & {'_rs', '_RSM'}, (f.name, fn.name)
