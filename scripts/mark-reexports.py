#!/usr/bin/env python3
"""🏷 After scripts/move-section.py: an import in reputation_service.py that only moved code reads (as rs.NAME) looks unused to pyflakes. Each one that
another backend module really reads as rs.NAME / reputation_service.NAME gets `# noqa: F401  (read by <module> as rs.NAME)` on its line; one that
nothing reads is listed as DEAD (exit 1) for a human to delete. Never deletes anything itself.
  .venv/bin/python scripts/mark-reexports.py [feecat_service]"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'backend' / 'reputation_service.py'


def main():
    svc = sys.argv[1] if len(sys.argv) > 1 else 'reputation_service'   # or feecat_service
    SRC = ROOT / 'backend' / f'{svc}.py'
    out = subprocess.run([str(ROOT / '.venv/bin/python'), '-m', 'pyflakes', str(SRC)], capture_output=True, text=True).stdout
    others = {p: p.read_text(errors='ignore') for p in (ROOT / 'backend').rglob('*.py') if '.venv' not in p.parts and p != SRC}
    lines = SRC.read_text().splitlines(keepends=True); dead = []; marked = 0
    for row in out.splitlines():
        m = re.search(r':(\d+):\d+: \'(?:[\w.]+ as (\w+)|([\w.]+))\' imported but unused', row)
        if not m:
            continue
        ln = int(m.group(1)); name = m.group(2) or m.group(3).split('.')[-1]
        users = sorted({p.stem for p, t in others.items() if f'import {svc}' in t and re.search(r'\b(?:rs|' + svc + r'|_rs\(\)|_RSM)\.' + re.escape(name) + r'\b', t)})
        s = lines[ln - 1].rstrip('\n')
        if '# noqa' in s:
            continue
        if users:
            lines[ln - 1] = f"{s}   # noqa: F401  (read by {', '.join(users[:2])} as rs.{name})\n"; marked += 1
        else:
            dead.append(f'  line {ln}: {name}')
    SRC.write_text(''.join(lines))
    print(f'marked {marked} re-exports')
    if dead:
        print('DEAD (nothing reads them; check for side effects, then delete):\n' + '\n'.join(dead))
    return 1 if dead else 0


if __name__ == '__main__':
    sys.exit(main())
