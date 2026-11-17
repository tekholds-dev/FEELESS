#!/usr/bin/env python3
"""✂ Split a module that scripts/move-section.py filled (rep_ai.py, fc_desk.py …) along the service's `# ↪ moved to <mod>.py:` markers: every
function named by the markers between two service lines leaves <mod>.py for <into>.py, text unchanged (moved code already reads the service as
rs.<name>, so where it sits does not matter). The service's markers and aliases follow; <into> is imported (and its router included) right after
<mod>, so its routes keep their place among the others (check with scripts/route-map.py before/after). Refuses anything it cannot place exactly.
  .venv/bin/python scripts/split-module.py --svc reputation_service --mod rep_ai --into rep_office --from 3037 --to 3260 --title "…" [--apply]"""
import argparse
import ast
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def segments(text):
    """{name: (start, end)} line ranges (0-based, end exclusive): the function, its decorators and the comment lines right above it."""
    lines = text.splitlines(keepends=True); out = {}
    for n in ast.parse(text).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            s = (n.decorator_list[0].lineno if n.decorator_list else n.lineno) - 1
            while s and lines[s - 1].lstrip().startswith('#'):
                s -= 1
            out[n.name] = (s, n.end_lineno)
    return out


def main():
    ap = argparse.ArgumentParser()
    for a in ('--svc', '--mod', '--into', '--title'):
        ap.add_argument(a, required=True)
    ap.add_argument('--from', dest='a', type=int, required=True); ap.add_argument('--to', dest='b', type=int, required=True)
    ap.add_argument('--apply', action='store_true'); o = ap.parse_args()
    B = ROOT / 'backend'; svc_p = B / f'{o.svc}.py'; mod_p = B / f'{o.mod}.py'; dst = B / f'{o.into}.py'
    if dst.exists():
        sys.exit(f'{dst.name} exists')
    svc = svc_p.read_text().splitlines(keepends=True); mod_t = mod_p.read_text(); mod_l = mod_t.splitlines(keepends=True)
    tag = f'# ↪ moved to {o.mod}.py:'
    rows = [i for i in range(o.a - 1, min(o.b, len(svc))) if svc[i].startswith(tag)]
    names = [n.strip() for i in rows for n in svc[i][len(tag):].split(',') if n.strip()]
    seg = segments(mod_t); missing = [n for n in names if n not in seg]
    if missing or not names:
        sys.exit(f'not in {o.mod}.py: {missing}' if missing else 'no markers in that range')
    code = '\n\n'.join(''.join(mod_l[seg[n][0]:seg[n][1]]) for n in names)
    routes = '@router.' in code
    print(f'{o.into}: {len(names)} functions ({code.count("@router.")} routes, {code.count(chr(10)) + 1} lines) from {o.mod}.py')
    if not o.apply:
        return 0
    keep = sorted(((s, e) for n, (s, e) in seg.items() if n in set(names)), reverse=True)
    for s, e in keep:
        del mod_l[s:e]
    mod_p.write_text(re.sub(r'\n{4,}', '\n\n\n', ''.join(mod_l)))
    need = []
    if '_RSM.' in code:
        need.append(f'import {o.svc} as _RSM  # noqa: E402,F401  (body models / annotations; this module is imported at the END of the service)')
    if routes or re.search(r'\b(Request|Query|Header|Optional)\b', code):
        need.append('from fastapi import APIRouter, Header, HTTPException, Query, Request  # noqa: F401\nfrom typing import Optional  # noqa: F401')
    tc = re.search(r'^from typing import TYPE_CHECKING\nif TYPE_CHECKING:.*\n(?:    .*\n)+', mod_t, re.M)
    if tc:
        need.append(tc.group(0).rstrip('\n'))
    if routes:
        need.append('\nrouter = APIRouter()')
    dst.write_text(f'"""🧹 {o.title} — split out of {o.mod}.py by scripts/split-module.py (owner 2026-11-17 cleanup); first moved whole out of {o.svc}.py.\n'
                   f'Same code: every name it reads from the service is looked up there when it runs (as rs.<name>), so a test that patches {o.svc} still\n'
                   f'reaches it, and every function here is still reachable on {o.svc} under its own name. Constants, classes and state live in the service."""\n'
                   + ('\n'.join(need) + '\n' if need else '') + '\n\n' + f'def _rs():\n    import {o.svc}\n    return {o.svc}\n\n\n' + code + '\n')
    for i in rows:
        svc[i] = svc[i].replace(tag, f'# ↪ moved to {o.into}.py:')
    moved = set(names)
    for i, ln in enumerate(svc):
        m = re.match(rf'^(\w+) = _{o.mod}\.(\w+)\n$', ln)
        if m and m.group(1) == m.group(2) and m.group(1) in moved:
            svc[i] = f'{m.group(1)} = _{o.into}.{m.group(1)}\n'
    at = next(i for i, ln in enumerate(svc) if ln.startswith(f'import {o.mod} as _{o.mod}'))
    if at + 1 < len(svc) and svc[at + 1].startswith(f'app.include_router(_{o.mod}.router)'):
        at += 1
    svc[at + 1:at + 1] = [f'import {o.into} as _{o.into}   # noqa: E402  🧹 split out of {o.mod}.py by scripts/split-module.py\n']\
        + ([f'app.include_router(_{o.into}.router)\n'] if routes else [])
    svc_p.write_text(''.join(svc))
    before = segments(subprocess.run(['git', 'show', f'HEAD:backend/{o.mod}.py'], cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    old_l = subprocess.run(['git', 'show', f'HEAD:backend/{o.mod}.py'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines(keepends=True)
    bad = 0
    for p in (mod_p, dst):
        t = p.read_text(); ln = t.splitlines(keepends=True)
        for n, (s, e) in segments(t).items():
            if n != '_rs' and n in before and ''.join(ln[s:e]) != ''.join(old_l[before[n][0]:before[n][1]]):
                print(f'✗ {p.name}: {n} changed'); bad += 1
    print(f'split {len(names)} → backend/{dst.name}' + (f' · {bad} CHANGED' if bad else ' · every function byte-for-byte as it was'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
