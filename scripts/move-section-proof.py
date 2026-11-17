#!/usr/bin/env python3
"""🧾 Proof that scripts/move-section.py changed NO behaviour: every function in backend/rep_<name>.py, with its `rs = _rs()` line, its `rs.` / `_RSM.`
prefixes and its @router (back to @app) undone, is byte-for-byte the function of the same name in the given git revision of reputation_service.py.
  .venv/bin/python scripts/move-section-proof.py --rev HEAD backend/rep_ai.py [backend/rep_x.py …]   → exit 0 only when every function matches"""
import argparse
import ast
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def funcs(text):
    lines = text.splitlines(keepends=True); out = {}
    for n in ast.parse(text).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            s = (n.decorator_list[0].lineno if n.decorator_list else n.lineno) - 1
            out[n.name] = ''.join(lines[s:n.end_lineno])
    return out


def undo(code):
    code = re.sub(r'^[ \t]*rs = _rs\(\)\n', '', code, count=1, flags=re.M)
    code = re.sub(r'(?<![\w.])(?:rs|_RSM)\.(?=[A-Za-z_])', '', code)
    return re.sub(r'@router\.(get|post|put|delete|patch|api_route)\(', r'@app.\1(', code, count=1)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rev', action='append'); ap.add_argument('--svc', default='reputation_service'); ap.add_argument('mods', nargs='+'); a = ap.parse_args()
    revs = a.rev or ['HEAD']   # --rev may repeat (a module filled across several commits): a function must equal its original at one of them
    olds = [funcs(subprocess.run(['git', 'show', f'{r}:backend/{a.svc}.py'], cwd=ROOT, capture_output=True, text=True, check=True).stdout) for r in revs]
    old = {}
    for o in olds:
        for k, v in o.items():
            old.setdefault(k, v)
    bad = 0; n = 0; globs = 0
    for m in a.mods:
        for name, code in funcs(pathlib.Path(m).read_text()).items():
            if name == '_rs':
                continue
            n += 1
            if name not in old:
                print(f'✗ {m}: {name} is not in {a.svc}@{revs}'); bad += 1
            elif any(undo(code) == o.get(name) for o in olds):
                pass
            elif undo(code) != old[name]:
                no_glob = [re.sub(r'^[ \t]*global [\w, ]+[ \t]*(#.*)?\n', '', o[name], flags=re.M) for o in olds if name in o]   # `global X` moved as rs.X (move-section.global_ok)
                if undo(code) in no_glob:
                    globs += 1
                else:
                    print(f'✗ {m}: {name} differs from the original'); bad += 1
    print(f'{n - bad}/{n} moved functions are the original, byte for byte' + (f' ({globs} once their `global` line, now rs.<name>, is set aside)' if globs else '') if n else 'no functions found')
    return 1 if bad or not n else 0


if __name__ == '__main__':
    sys.exit(main())
