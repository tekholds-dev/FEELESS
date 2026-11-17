"""🧩 SITE-5 / 🧹 cleanup 2026-11-16: the reputation service lives in reputation_service.py AND the rep_*.py modules the movers filled. A test that reads
the service's SOURCE reads all of it, with the movers' mechanical edits undone (`rs.NAME` → `NAME`, `@router.` → `@app.`, no `rs = _rs()` line):
  · a `# ↪ moved to rep_x.py: a, b` marker (scripts/move-section.py) is replaced IN PLACE by those functions, so a scan that slices the source
    between two functions sees the original order
  · the route modules (scripts/move-routes.py) are appended at the end, as before."""
import ast
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
MARK = re.compile(r'^# ↪ moved to (rep_\w+)\.py:(.*)$', re.M)


def _undo(text):
    text = re.sub(r'^[ \t]*rs = _rs\(\)\n', '', text, flags=re.M)
    return re.sub(r'(?<![\w.])(?:rs|_RSM)\.(?=[A-Za-z_])', '', text.replace('@router.', '@app.'))


def _segments(path):
    """Each function of a moved module with the comment lines right above it, undone. → {name: source}"""
    text = path.read_text(); lines = text.splitlines(keepends=True); out = {}
    for n in ast.parse(text).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            s = (n.decorator_list[0].lineno if n.decorator_list else n.lineno) - 1
            while s and lines[s - 1].lstrip().startswith('#'):
                s -= 1
            out[n.name] = _undo(''.join(lines[s:n.end_lineno]))
    return out


def service_src(routes=True):
    """routes=False: only the service with its moved sections in place (no appended route modules, which define their own helpers)."""
    main = (BACKEND / 'reputation_service.py').read_text()
    seg = {}

    def expand(m):
        mod = m.group(1)
        if mod not in seg:
            seg[mod] = _segments(BACKEND / f'{mod}.py')
        return '\n\n'.join(seg[mod][n.strip()] for n in m.group(2).split(',') if n.strip())
    parts = [MARK.sub(expand, main)]
    for f in sorted(BACKEND.glob('rep_*.py')) if routes else ():
        if f.stem not in seg:   # a route module: appended, as the route mover left them
            parts.append(_undo(f.read_text()))
    return '\n\n\n'.join(parts)


def fn_src(name):
    """One function's source, wherever it lives now."""
    src = service_src(); m = re.search(rf'^(?:async )?def {re.escape(name)}\(', src, re.M)
    if not m:
        raise KeyError(name)
    nxt = re.compile(r'\n(?=[^\s#)])').search(src, m.end())   # the next line that starts at column 0 (not a comment, not a closing paren)
    return src[m.start():nxt.start() + 1 if nxt else len(src)]
