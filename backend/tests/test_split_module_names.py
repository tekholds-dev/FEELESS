"""The routes split out of reputation_service (rep_*.py) read its names as `rs.X`. pyflakes cannot see that, so an "unused" import
removed from reputation_service once took /api/reputation/health down (rs._chain_rpc_mod, 2026-11-12). Every rs.X must exist."""
import ast
import pathlib
import re

B = pathlib.Path(__file__).resolve().parents[1]


def test_every_rs_name_a_split_module_reads_exists():
    tree = ast.parse((B / 'reputation_service.py').read_text())
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {(a.asname or a.name).split('.')[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    names |= {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    missing, checked = {}, 0
    for f in sorted(B.glob('rep_*.py')):
        src = f.read_text()
        if not re.search(r'^\s*(import reputation_service as rs|rs = )', src, re.M):   # they bind it as `rs = _rs()`
            continue
        checked += 1
        for x in set(re.findall(r'(?<![\w.])rs\.([A-Za-z_]\w*)', src)) - names:
            missing.setdefault(f.name, []).append(x)
    assert checked, 'no split module found: the pattern is stale'
    assert missing == {}
