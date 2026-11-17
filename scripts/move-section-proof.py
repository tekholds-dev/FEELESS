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
    ap = argparse.ArgumentParser(); ap.add_argument('--rev', default='HEAD'); ap.add_argument('--svc', default='reputation_service'); ap.add_argument('mods', nargs='+'); a = ap.parse_args()
    old = funcs(subprocess.run(['git', 'show', f'{a.rev}:backend/{a.svc}.py'], cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    bad = 0; n = 0
    for m in a.mods:
        for name, code in funcs(pathlib.Path(m).read_text()).items():
            if name == '_rs':
                continue
            n += 1
            if name not in old:
                print(f'✗ {m}: {name} is not in {a.svc}@{a.rev}'); bad += 1
            elif undo(code) != old[name]:
                print(f'✗ {m}: {name} differs from the original'); bad += 1
    print(f'{n - bad}/{n} moved functions are the original, byte for byte' if n else 'no functions found')
    return 1 if bad or not n else 0


if __name__ == '__main__':
    sys.exit(main())
