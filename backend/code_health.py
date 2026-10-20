"""🧹 Code health — a static scan of the repo (pure: reads files, writes nothing).

Rows, each with file:line and the fix in plain words:
  dead_export   a frontend export never imported / used outside its own file and tests
  dead_def      a backend top-level function no other code (tests excluded) names
  dead_css      a class selector in styles/*.css whose name appears in no JS / JSX source
  big           the biggest Python functions and frontend components by lines
  dup           functions with an identical body (Python: AST, JS: normalized text) in two places

Heuristic by design (dynamic class names, getattr, string routes): every row says "check before deleting".
`scripts/code-health.py` runs it and writes data/code_health.json; HQ › Lag catcher reads that file.
"""
import ast
import hashlib
import os
import re
import time
from pathlib import Path

SKIP_DIRS = {'node_modules', 'build', '.venv', '__pycache__', '.git', 'data', 'lan_bundle', 'contracts'}
JS_EXT = ('.js', '.jsx')
BIG_TOP = 15
DUP_MIN_LINES = 4


def _walk(root, exts):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith('.')]
        for f in fns:
            if f.endswith(exts):
                yield Path(dp) / f


def _is_test(p):
    s = str(p)
    return '/tests/' in s or '.test.' in s or s.endswith('setupTests.js') or '/__tests__/' in s


def _rel(p, root):
    return str(Path(p).relative_to(root))


def _row(kind, file, line, name, fix, lines=None, **extra):
    return {'kind': kind, 'file': file, 'line': line, 'name': name, 'lines': lines, 'fix': fix, **extra}


# ── frontend ────────────────────────────────────────────────────────────────────────────────
_EXPORT = re.compile(r'^export\s+(?:default\s+)?(?:async\s+)?(?:function\*?|const|let|class)\s+([A-Za-z_$][\w$]*)', re.M)
_TOPDEF = re.compile(r'^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s+([A-Za-z_$][\w$]*)|(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=)', re.M)


def js_exports(text):
    return [(m.group(1), text.count('\n', 0, m.start()) + 1) for m in _EXPORT.finditer(text)
            if not text[m.start():m.start() + 15].startswith('export default')]


def js_blocks(text):
    """Top-level declarations → (name, line, n lines) up to the next top-level declaration."""
    ms = list(_TOPDEF.finditer(text))
    out = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        a = text.count('\n', 0, m.start()) + 1
        n = text[m.start():end].rstrip().count('\n') + 1
        out.append((m.group(1) or m.group(2), a, n, text[m.start():end]))
    return out


def _norm_js(body, name):
    b = re.sub(r'//[^\n]*|/\*.*?\*/', '', body, flags=re.S)
    b = b.replace(name, '§', 1)
    return re.sub(r'\s+', ' ', b).strip()


def scan_frontend(src):
    files = {p: p.read_text(errors='ignore') for p in _walk(src, JS_EXT)}
    prod = {p: t for p, t in files.items() if not _is_test(p)}
    words = {}
    for p, t in prod.items():
        for w in set(re.findall(r'[A-Za-z_$][\w$]*', t)):
            words.setdefault(w, set()).add(p)
    tests = '\n'.join(t for p, t in files.items() if _is_test(p))
    rows = []
    for p, t in prod.items():
        for name, line in js_exports(t):
            if words.get(name, set()) - {p}:
                continue
            in_tests = bool(re.search(r'\b%s\b' % re.escape(name), tests))
            own = len(re.findall(r'\b%s\b' % re.escape(name), t)) > 1
            if own:
                how, fix = 'own', (f'Used only inside its own file{" (+ a test)" if in_tests else ""} — '
                                   + ('keep the export for the test.' if in_tests else f'drop the `export` from {name}.'))
            elif in_tests:
                how, fix = 'tests', f'Only a test imports {name} — a test hook; delete it with its test if the test is not needed.'
            else:
                how, fix = 'none', f'Nothing uses {name} — delete it (and its CSS).'
            rows.append(_row('dead_export', p, line, name, fix, how=how))
    blocks = []
    for p, t in prod.items():
        for name, line, n, body in js_blocks(t):
            blocks.append((p, name, line, n, body))
    big = sorted(blocks, key=lambda b: -b[3])[:BIG_TOP]
    for p, name, line, n, _ in big:
        rows.append(_row('big', p, line, name, f'{n} lines — split into smaller components / helpers (one job each).', lines=n, lang='js'))
    seen = {}
    for p, name, line, n, body in blocks:
        if n < DUP_MIN_LINES or not re.match(r'(export\s+)?(async\s+)?function|(export\s+)?const\s+\w+\s*=\s*(\(|async|\w+\s*=>)', body):
            continue
        h = hashlib.sha1(_norm_js(body, name).encode()).hexdigest()
        seen.setdefault(h, []).append((p, name, line, n))
    for h, xs in seen.items():
        if len({x[0] for x in xs}) > 1:
            first = xs[0]
            for p, name, line, n in xs[1:]:
                rows.append(_row('dup', p, line, name, f'Same body as {first[1]} in {first[0].name}:{first[2]} — import that one instead.', lines=n, lang='js',
                                 twin=f'{first[0]}:{first[2]}'))
    return rows, files


_CSS_CLASS = re.compile(r'\.(-?[_a-zA-Z][\w-]*)')


def css_classes(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    out = {}
    for m in re.finditer(r'([^{}]+)\{', text):
        sel = m.group(1)
        if sel.strip().startswith('@'):
            continue
        sel = re.sub(r'url\([^)]*\)|"[^"]*"|\'[^\']*\'|\d+\.\d+', '', sel)
        line = text.count('\n', 0, m.start(1) + len(m.group(1)) - len(m.group(1).lstrip())) + 1
        for c in _CSS_CLASS.findall(sel):
            out.setdefault(c, line)
    return out


def scan_css(styles, files, public=None):
    """Mirrors styles/cssHygiene.test.js: a class is used when any source token equals it or a dynamic prefix
    (`x-${…}` / 'x-' +) starts it."""
    blob = '\n'.join(t for p, t in files.items() if not _is_test(p))
    if public and Path(public).exists():
        blob += '\n'.join(p.read_text(errors='ignore') for p in Path(public).rglob('*.html'))
    tokens = set(re.findall(r'[A-Za-z_][\w-]*', blob))
    prefixes = tuple(set(re.findall(r'([A-Za-z_][\w-]*-)\$\{', blob)) | set(re.findall(r'[\'"]([A-Za-z_][\w-]*-)[\'"]\s*\+', blob)))
    rows = []
    for p in sorted(Path(styles).glob('*.css')):
        for c, line in css_classes(p.read_text(errors='ignore')).items():
            if c in tokens or c.startswith(prefixes):
                continue
            rows.append(_row('dead_css', p, line, c, f'No component renders .{c} — delete its rule (brace-aware; cssCoverage still passes).'))
    return rows


# ── backend ─────────────────────────────────────────────────────────────────────────────────
def _norm_py(fn):
    f = ast.parse(ast.unparse(fn)).body[0]
    f.name = '§'
    if f.body and isinstance(f.body[0], ast.Expr) and isinstance(getattr(f.body[0], 'value', None), ast.Constant):
        f.body = f.body[1:] or [ast.Pass()]
    return ast.dump(f, annotate_fields=False)


def scan_backend(back, extra_dirs=()):
    files = {p: p.read_text(errors='ignore') for p in _walk(back, ('.py',))}
    for d in extra_dirs:
        files.update({p: p.read_text(errors='ignore') for p in _walk(d, ('.py',))})
    prod = {p: t for p, t in files.items() if not _is_test(p)}
    counts = {}
    for t in prod.values():
        for w in re.findall(r'[A-Za-z_]\w*', t):
            counts[w] = counts.get(w, 0) + 1
    rows, fns, seen = [], [], {}
    for p, t in prod.items():
        if not str(p).startswith(str(back)):
            continue
        try:
            tree = ast.parse(t)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            n = (node.end_lineno or node.lineno) - node.lineno + 1
            fns.append((p, node.name, node.lineno, n))
            if not node.decorator_list and counts.get(node.name, 0) <= 1 and not node.name.startswith('test'):
                rows.append(_row('dead_def', p, node.lineno, node.name, f'Nothing calls {node.name}() outside tests — delete it (and its test).', lines=n))
            if n >= DUP_MIN_LINES:
                try:
                    seen.setdefault(hashlib.sha1(_norm_py(node).encode()).hexdigest(), []).append((p, node.name, node.lineno, n))
                except Exception:
                    pass
    for p, name, line, n in sorted(fns, key=lambda f: -f[3])[:BIG_TOP]:
        rows.append(_row('big', p, line, name, f'{n} lines — split it: one job per helper, keep the route thin.', lines=n, lang='py'))
    for xs in seen.values():
        if len(xs) > 1:
            first = xs[0]
            for p, name, line, n in xs[1:]:
                rows.append(_row('dup', p, line, name, f'Same body as {first[1]}() in {first[0].name}:{first[2]} — import that one.', lines=n, lang='py',
                                 twin=f'{first[0]}:{first[2]}'))
    return rows


def file_sizes(root, paths):
    out = []
    for p in paths:
        try:
            out.append({'file': _rel(p, root), 'lines': p.read_text(errors='ignore').count('\n') + 1})
        except Exception:
            pass
    return sorted(out, key=lambda r: -r['lines'])[:12]


def scan(root):
    root = Path(root).resolve()
    src, back = root / 'frontend' / 'src', root / 'backend'
    t0 = time.time()
    fe_rows, fe_files = scan_frontend(src)
    rows = fe_rows + scan_css(src / 'styles', fe_files, root / 'frontend' / 'public') + scan_backend(back, (root / 'scripts',))
    for r in rows:
        r['file'] = _rel(r['file'], root)
        if r.get('twin'):
            f, _, l = r['twin'].rpartition(':')
            r['twin'] = f'{_rel(f, root)}:{l}'
    kinds = {}
    for r in rows:
        kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
    py = [p for p in _walk(back, ('.py',)) if not _is_test(p)]
    js = [p for p in fe_files if not _is_test(p)]
    return {'at': time.time(), 'root': str(root), 'scanSec': round(time.time() - t0, 1), 'counts': kinds,
            'totals': {'pyLines': sum(p.read_text(errors='ignore').count('\n') for p in py),
                       'jsLines': sum(fe_files[p].count('\n') for p in js),
                       'cssLines': sum(p.read_text(errors='ignore').count('\n') for p in (src / 'styles').glob('*.css'))},
            'biggestFiles': file_sizes(root, py + js), 'rows': rows}
