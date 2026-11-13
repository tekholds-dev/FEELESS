#!/usr/bin/env python3
"""🧹 STYLE-1: cut CSS that can never paint, so a legacy sheet has room for its colour palette (budgets are never raised).

Only three cuts, each pixel-identical by construction:
  1. commented-out rules   a /* … */ comment that holds CSS ({ … }) is dead text
  2. duplicate rules       the same selector with the same declarations in the same @media/@supports context, twice → the
                           earlier copy goes (the later copy sits later in the cascade, so it already wins everywhere)
  3. overridden lines      a declaration that a LATER rule with the exact same selector, in the same context, declares again →
                           the earlier line goes (same specificity, later wins). Skipped when the earlier line is !important,
                           when the later value uses a function that an old browser might drop (the earlier line could be its
                           fallback), and inside @keyframes / @font-face.
A rule left with no declarations goes too. --check prints what it would cut; --write cuts it. The proof (--prove): for every
(context, selector, property) the winning value is the same before and after.

  .venv/bin/python scripts/css-dead-cut.py --check frontend/src/styles/command.css
  .venv/bin/python scripts/css-dead-cut.py --write frontend/src/styles/command.css
"""
import re
import sys
from pathlib import Path

COMMENT = re.compile(r'/\*[\s\S]*?\*/')
SAFE_FN = {'var', 'rgb', 'rgba', 'hsl', 'hsla', 'calc', 'url', 'linear-gradient', 'radial-gradient', 'conic-gradient', 'repeating-linear-gradient',
           'cubic-bezier', 'translate', 'translatex', 'translatey', 'translate3d', 'scale', 'scalex', 'scaley', 'rotate', 'blur', 'min', 'max',
           'clamp', 'repeat', 'minmax', 'steps', 'drop-shadow', 'brightness', 'saturate', 'inset', 'format', 'local', 'attr'}
SKIP_CTX = re.compile(r'@(?:-webkit-)?keyframes|@font-face', re.I)


def blank(css):
    """Comments and strings → spaces of the same length, so brace scanning never trips on them; offsets stay true."""
    out = COMMENT.sub(lambda m: ' ' * len(m.group(0)), css)
    return re.sub(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'', lambda m: m.group(0)[0] + ' ' * (len(m.group(0)) - 2) + m.group(0)[-1], out)


def rules(css):
    """→ [(ctx, selector, body_start, body_end, rule_start, rule_end)] for style rules, in source order."""
    b = blank(css); out = []; ctx = []; i = 0; head = 0
    while i < len(b):
        c = b[i]
        if c == '{':
            sel = b[head:i].strip()
            if sel.startswith('@'):
                ctx.append(' '.join(sel.split())); i += 1; head = i; continue
            j = b.index('}', i)
            out.append((tuple(ctx), ' '.join(COMMENT.sub(' ', css[head:i]).split()), i + 1, j, head, j + 1))   # the selector as the browser reads it
            i = j + 1; head = i; continue
        if c == '}':
            if ctx:
                ctx.pop()
            i += 1; head = i; continue
        if c == ';' and b[head:i].strip().startswith('@'):
            i += 1; head = i; continue
        i += 1
    return out


def decls(body):
    """→ [(prop, value, start, end)] with offsets inside body (end includes the ';')."""
    out = []; depth = 0; start = 0
    for k, ch in enumerate(body + ';'):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == ';' and depth == 0:
            seg = body[start:k]
            if ':' in seg and seg.strip():
                p, v = seg.split(':', 1)
                out.append((p.strip().lower(), v.strip(), start, min(k + 1, len(body))))
            start = k + 1
    return out


def safe(value):
    return all(f.lower() in SAFE_FN for f in re.findall(r'([\w-]+)\(', value))


def cut(css):
    """→ (new css, stats). Applies the three cuts; offsets are cut from the end backwards so they stay valid."""
    stats = {'commented': 0, 'duplicate': 0, 'overridden': 0, 'bytes': 0}
    spans = []   # (start, end) to delete
    for m in COMMENT.finditer(css):
        if '{' in m.group(0) and '}' in m.group(0) and ':' in m.group(0):
            spans.append((m.start(), m.end())); stats['commented'] += 1
    rs = rules(css); bl = blank(css)
    later = {}
    for idx, (ctx, sel, bs, be, _, _) in enumerate(rs):
        for p, v, _, _ in decls(bl[bs:be]):
            later.setdefault((ctx, sel, p), []).append((idx, v))
    seen = {}
    for idx, (ctx, sel, bs, be, rs0, re0) in enumerate(rs):
        if any(SKIP_CTX.search(c) for c in ctx):
            continue
        body = bl[bs:be]; ds = decls(body)
        key = (ctx, sel, ' '.join(body.split()))
        seen.setdefault(key, []).append(idx)
        drop = []
        for p, v, s, e in ds:
            if '!important' in v.lower():
                continue
            after = [(j, w) for j, w in later[(ctx, sel, p)] if j > idx]
            if after and all(safe(w) for _, w in after):
                drop.append((bs + s, bs + e))
        if drop and len(drop) == len(ds):
            spans.append((rs0, re0)); stats['overridden'] += len(drop)
        else:
            spans.extend(drop); stats['overridden'] += len(drop)
    for key, idxs in seen.items():
        for idx in idxs[:-1]:
            _, _, _, _, rs0, re0 = rs[idx]
            if not any(a <= rs0 and re0 <= b for a, b in spans):
                spans.append((rs0, re0)); stats['duplicate'] += 1
    # merge + apply
    spans.sort(); merged = []
    for a, b in spans:
        if merged and a < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    out = css
    for a, b in reversed(merged):
        out = out[:a] + out[b:]
    out = re.sub(r'\{\s*;', '{', out)
    stats['bytes'] = len(css.encode()) - len(out.encode())
    return out, stats


def paint(css):
    """(ctx, selector, prop) → winning value, from the comment-free text (the proof compares these)."""
    bl = blank(css); out = {}
    for ctx, sel, bs, be, _, _ in rules(css):
        for p, v, s, e in decls(bl[bs:be]):
            raw = css[bs + s:bs + e].split(':', 1)[1].rstrip(';').strip()
            k = (ctx, sel, p)
            if k in out and '!important' in out[k].lower() and '!important' not in raw.lower():
                continue
            out[k] = ' '.join(raw.split())
    return out


def main(argv):
    if len(argv) < 2 or argv[0] not in ('--check', '--write', '--prove'):
        print(__doc__); return 2
    bad = 0
    for f in argv[1:]:
        p = Path(f); css = p.read_text(); out, st = cut(css)
        same = paint(css) == paint(out)
        print(f'{f}: {st["bytes"] / 1024:.1f} KB cut · {st["commented"]} commented-out · {st["duplicate"]} duplicate rules · '
              f'{st["overridden"]} overridden lines · paint identical: {same}')
        if not same:
            bad = 1
            a, b = paint(css), paint(out)
            for k in list(set(a) | set(b))[:5]:
                if a.get(k) != b.get(k):
                    print('   differs:', k, a.get(k), '→', b.get(k))
        elif argv[0] == '--write':
            p.write_text(out)
    return bad


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
