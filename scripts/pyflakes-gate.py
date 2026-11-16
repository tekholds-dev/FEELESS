#!/usr/bin/env python3
"""🧹 Backend lint gate (owner 2026-11-16 "clean code sitewide, no bugs, no dups or dead code").

Runs pyflakes on every backend module (not tests) and fails on any finding, except one whose source line says `noqa`:
those are deliberate (a side-effect import like env_loader, or a name re-exported for tests / other modules as `rs.X`).
An unused import with no reason, an f-string with nothing in it, an undefined name or a shadowed import fails the push.
Exit 0 = clean. Usage: .venv/bin/python scripts/pyflakes-gate.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted(str(p) for p in (ROOT / 'backend').glob('*.py'))
LINE = re.compile(r'^(?P<f>[^:]+):(?P<n>\d+):(?:\d+:)? (?P<msg>.*)$')


def findings(out):
    """pyflakes output → the findings a `noqa` line does not excuse. Pure apart from reading the named files."""
    cache, bad = {}, []
    for raw in out.splitlines():
        m = LINE.match(raw.strip())
        if not m:
            continue
        src = cache.setdefault(m['f'], Path(m['f']).read_text(errors='replace').splitlines())
        n = int(m['n'])
        text = src[n - 1] if 0 < n <= len(src) else ''
        if 'noqa' in text:
            continue
        bad.append(raw.strip())
    return bad


def main():
    r = subprocess.run([sys.executable, '-m', 'pyflakes', *FILES], capture_output=True, text=True)
    bad = findings(r.stdout + r.stderr)
    for b in bad:
        print(b.replace(str(ROOT) + '/', ''))
    if bad:
        print(f'✋ {len(bad)} lint finding(s): fix them, or mark a deliberate one with `# noqa: <code> (why)` on its line')
        return 1
    print(f'pyflakes clean: {len(FILES)} backend modules')
    return 0


if __name__ == '__main__':
    sys.exit(main())
