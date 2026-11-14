#!/usr/bin/env python3
"""🧹 STYLE-1 slice 3: cut CSS selectors for surfaces that no longer exist (a class no code can ever put on an element).

A selector is dead when it REQUIRES a class (outside :not / :is / :where / :matches) that appears nowhere in the code:
  - not as a literal word in any module the app can load (imports walked from src/index.js), public/*.html|js or backend/*.py, and
  - not buildable: no `prefix-${…}` / `'prefix-' + …` in the code covers it, and no `${…}-suffix` covers it.
A dead selector can never match, so cutting it can never change paint. A rule loses only its dead selectors; a rule left
with none goes whole (an @media left empty goes too). --prove: every live (context, selector, property) keeps its winning value.

  .venv/bin/python scripts/css-dead-surfaces.py --check frontend/src/styles/terminal.css
  .venv/bin/python scripts/css-dead-surfaces.py --write frontend/src/styles/terminal.css
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('css_dead_cut', ROOT / 'scripts' / 'css-dead-cut.py')
dc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(dc)

WORD = re.compile(r'[A-Za-z_][\w-]*')
CLASS = re.compile(r'\.(-?[A-Za-z_][\w-]*)')
SKIP_CTX = re.compile(r'@(?:-webkit-)?keyframes|@font-face', re.I)


IMPORT = re.compile(r"""(?:from\s+|import\s*\(\s*|require\s*\(\s*|import\s+)['"]((?:\.{1,2}|@)/[^'"]+)['"]""")
EXTS = ('', '.js', '.jsx', '.ts', '.tsx', '.mjs', '/index.js', '/index.jsx')


def reachable(root=ROOT):
    """Every frontend module the app can load, walking imports (static, lazy, require) from src/index.js. Tests are not the app."""
    src = root / 'frontend' / 'src'; seen = set(); todo = [src / 'index.js']
    while todo:
        f = todo.pop()
        if f in seen or not f.is_file():
            continue
        seen.add(f)
        for rel in IMPORT.findall(f.read_text(errors='ignore')):
            base = src / rel[2:] if rel.startswith('@/') else f.parent / rel   # '@/' = src (jsconfig + craco alias)
            for e in EXTS:
                c = Path(str(base) + e).resolve()
                if c.is_file():
                    if c.suffix != '.css':
                        todo.append(c)
                    break
    return seen


def corpus(root=ROOT):
    """→ (words, dynamic prefixes, dynamic suffixes) from every place a LIVE class name can come from."""
    words, pre, suf = set(), set(), set()
    files = sorted(reachable(root)) + [p for p in (root / 'frontend/public').rglob('*') if p.suffix in {'.html', '.js'}]
    files += list((root / 'backend').glob('*.py'))
    for p in files:
        try:
            t = p.read_text(errors='ignore')
        except OSError:
            continue
        words.update(WORD.findall(t))
        pre.update(re.findall(r'([A-Za-z_][\w-]*-)\$\{', t))
        pre.update(re.findall(r'([A-Za-z_][\w-]*-)[\'"`]\s*\+', t))
        suf.update(re.findall(r'\}(-[\w-]+)', t))
        suf.update(re.findall(r'\+\s*[\'"`](-[\w-]+)', t))
    return words, pre, suf


def alive(cls, words, pre, suf):
    if cls in words:
        return True
    parts = cls.split('-')
    if any('-'.join(parts[:k]) + '-' in pre for k in range(1, len(parts))):
        return True
    return any(cls.endswith(s) for s in suf)


def _strip_groups(sel):
    """Selector text with :not(…) / :is(…) / :where(…) / :matches(…) / :has(…) argument lists removed (conservative)."""
    out = []; i = 0
    while i < len(sel):
        m = re.match(r':(?:not|is|where|matches|has|-webkit-any|-moz-any)\(', sel[i:])
        if m:
            depth = 0; j = i + m.end() - 1
            while j < len(sel):
                depth += sel[j] == '('; depth -= sel[j] == ')'
                if depth == 0:
                    break
                j += 1
            i = j + 1; continue
        out.append(sel[i]); i += 1
    return ''.join(out)


def split_top(sel):
    parts, depth, cur = [], 0, ''
    for ch in sel:
        depth += ch == '('; depth -= ch == ')'
        if ch == ',' and depth == 0:
            parts.append(cur); cur = ''
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def dead_sel(sel, words, pre, suf):
    bare = re.sub(r'\[[^\]]*\]', '', _strip_groups(sel))   # attribute values are not classes
    return any(not alive(c, words, pre, suf) for c in CLASS.findall(bare))


def cut(css, words, pre, suf):
    """→ (new css, stats)."""
    edits = []; stats = {'rules': 0, 'selectors': 0}
    for ctx, sel, bs, be, rs0, re0 in dc.rules(css):
        if any(SKIP_CTX.search(c) for c in ctx):
            continue
        sels = split_top(sel)
        keep = [s for s in sels if not dead_sel(s, words, pre, suf)]
        if len(keep) == len(sels):
            continue
        if not keep:
            edits.append((rs0, re0, '')); stats['rules'] += 1
        else:
            lead = css[rs0:bs - 1]; ws = lead[:len(lead) - len(lead.lstrip())]
            edits.append((rs0, bs - 1, ws + ', '.join(keep) + ' '))
        stats['selectors'] += len(sels) - len(keep)
    out = css
    for a, b, rep in sorted(edits, reverse=True):
        out = out[:a] + rep + out[b:]
    for _ in range(4):   # at-rule blocks left empty
        out = re.sub(r'@(?:media|supports|container)[^{};]*\{\s*\}', '', out)
    stats['bytes'] = len(css.encode()) - len(out.encode())
    return out, stats


def prove(before, after, words, pre, suf):
    """Every live selector keeps every winning value; nothing new appears."""
    def live(css):
        p = dc.paint(css); o = {}
        for (ctx, sel, prop), v in p.items():
            for s in split_top(sel):
                if not dead_sel(s, words, pre, suf):
                    o[(ctx, s, prop)] = v
        return o
    a, b = live(before), live(after)
    return [k for k in set(a) | set(b) if a.get(k) != b.get(k)]


def main(argv):
    if len(argv) < 2 or argv[0] not in ('--check', '--write'):
        print(__doc__); return 2
    words, pre, suf = corpus()
    rc = 0
    for f in argv[1:]:
        p = Path(f); css = p.read_text()
        out, st = cut(css, words, pre, suf)
        bad = prove(css, out, words, pre, suf)
        print(f'{p.name}: {st["rules"]} rules + {st["selectors"] - st["rules"]} extra selectors dead · {st["bytes"] / 1024:.1f} KB · paint {"IDENTICAL" if not bad else f"DIFFERS ({len(bad)})"}')
        if bad:
            rc = 1; [print('  ', k) for k in bad[:10]]
        elif argv[0] == '--write':
            p.write_text(out)
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
