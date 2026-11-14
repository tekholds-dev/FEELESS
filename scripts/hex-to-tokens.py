#!/usr/bin/env python3
"""🎨 STYLE-1 / LOOK-1: rewrite hand-written hex colours in CSS sheets onto the meta.css tokens (CLAUDE.md §6: tokens only).

Each hex is read as a role, not a hue: near-black → --m-bg / --m-surface / --m-surface-2, dark greys → --m-line / --m-line-hi,
mid greys → --m-mute / --m-dim, light → --m-text; saturated reds/pinks → --m-danger, ambers → --m-warn, every other saturated
colour (green, cyan, blue, violet) → --m-accent. Alpha survives as color-mix(... N%, transparent). Inside a `body.theme-day` rule
lightness is read inverted (a white card in day = the surface, dark ink in day = the text), because the tokens flip there.
The look (lib/looks.js) remaps the tokens, so a converted sheet follows the site palette (FEELESS green on Obsidian).

  --check  a.css b.css   count hex per file (exit 0)
  --write  a.css b.css   rewrite in place, print before → after
  --only REGEX           only rules whose selector matches (e.g. '\\.clx-' to convert one surface inside a shared sheet)
  --palette [--prefix X] a.css …   STYLE-1 mode (the look must NOT change): every colour in a sheet becomes ONE named page token, declared once in a
                         `:root{}` palette block at the top of that sheet (`--<pfx>-<role><n>: #hex`), and every use reads var(). Pixel-identical
                         by construction; each page keeps its own accents (RULINGS 2026-11-13); a colour is changed in one place.
meta.css is never touched (it defines the tokens). Comments are left alone.
"""
import colorsys
import re
import sys
from pathlib import Path

HEX = re.compile(r'#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b')
RULE = re.compile(r'([^{}]*)\{([^{}]*)\}')
COMMENT = re.compile(r'/\*.*?\*/', re.S)


def parse(h):
    if len(h) in (3, 4):
        h = ''.join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return r, g, b, a


def role(r, g, b, day=False):
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    if day:   # day ink: dark = the text, near-white = the card
        if light < 0.32:
            return '--m-text' if light < 0.22 or sat < 0.5 else '--m-dim'
        if light > 0.96:
            return '--m-surface'
        light = 1 - light
    if sat < 0.22 or light < 0.12 or (light > 0.93):
        if light < 0.06:
            return '--m-bg'
        if light < 0.11:
            return '--m-surface'
        if light < 0.17:
            return '--m-surface-2'
        if light < 0.3:
            return '--m-line'
        if light < 0.45:
            return '--m-line-hi'
        if light < 0.62:
            return '--m-mute'
        if light < 0.8:
            return '--m-dim'
        return '--m-text'
    if light < 0.2:
        return '--m-surface-2' if light > 0.14 else '--m-surface'
    deg = hue * 360
    if deg >= 330 or deg < 18:
        return '--m-danger'
    if deg < 58:
        return '--m-warn'
    return '--m-accent'


def token(h, day=False):
    r, g, b, a = parse(h)
    t = f'var({role(r, g, b, day)})'
    if a >= 0.995:
        return t
    return f'color-mix(in srgb, {t} {max(1, round(a * 100))}%, transparent)'


def convert(css, only=None):
    keep = {}

    def stash(m):
        k = f'\0{len(keep)}\0'
        keep[k] = m.group(0)
        return k
    body = COMMENT.sub(stash, css)

    def rule(m):
        sel, decl = m.group(1), m.group(2)
        day = 'theme-day' in sel
        if only and not re.search(only, sel):
            return m.group(0)
        return sel + '{' + HEX.sub(lambda x: token(x.group(1), day), decl) + '}'
    body = RULE.sub(rule, body)
    for k, v in keep.items():
        body = body.replace(k, v)
    return body


def count(css):
    return len(HEX.findall(COMMENT.sub('', css)))


PALETTE = re.compile(r':root\s*\{\s*/\* page tokens \(STYLE-1\) \*/[^{}]*\}\s*', re.S)
ABBR = {'--m-bg': 'bg', '--m-surface': 'sf', '--m-surface-2': 's2', '--m-line': 'ln', '--m-line-hi': 'lh', '--m-mute': 'mu', '--m-dim': 'dm',
        '--m-text': 'tx', '--m-accent': 'ac', '--m-danger': 'dg', '--m-warn': 'wn'}
URL = re.compile(r'url\([^)]*\)', re.I)


def prefix(name):
    """catWorkbench.css → 'cw'; a plain lowercase name → its first 3 letters. Short so the sheet does not grow much."""
    stem = name.rsplit('.', 1)[0]
    caps = re.findall(r'[A-Z]', stem)
    return (stem[0] + ''.join(caps)).lower()[:4] if caps else stem[:3].lower()


def outside(css):
    """Hex values outside a STYLE-1 palette block and outside comments (what the sweep is measured on)."""
    return count(URL.sub('', PALETTE.sub('', css)))


def unpalette(css):
    """The inverse (for the proof): var(--x) → its hex from the palette block, block removed. palette() then unpalette() == the original."""
    m0 = PALETTE.search(css)
    if not m0:
        return css
    pal = dict(re.findall(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})', m0.group(0)))
    body = css[:m0.start()] + css[m0.end():]
    return re.sub(r'var\((--[\w-]+)\)', lambda m: pal.get(m.group(1), m.group(0)), body)


LEAD = re.compile(r'''(\s*(?:/\*.*?\*/\s*)*(?:@(?:charset|import)(?:'[^']*'|"[^"]*"|\([^)]*\)|[^;'"(])*;\s*)*)''', re.S)   # a ';' inside url('…wght@400;700') is not the end of the @import

def palette(css, pfx):
    """→ (new css, {var: hex}). Idempotent: an existing palette block is read and extended, never duplicated."""
    keep = {}

    def stash(m):
        k = f'\0{len(keep)}\0'
        keep[k] = m.group(0)
        return k
    old = {}
    m0 = PALETTE.search(css)
    if m0:
        for name, val in re.findall(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})', m0.group(0)):
            old[val.lower()] = name
        css = css[:m0.start()] + css[m0.end():]
    body = COMMENT.sub(stash, css)
    body = URL.sub(stash, body)
    names = dict(old); used = {}

    def name_of(h):
        h = '#' + h.lower()
        if h in names:
            return names[h]
        r, g, b, _ = parse(h[1:])
        ab = ABBR[role(r, g, b)]
        used[ab] = used.get(ab, sum(1 for v in names.values() if re.match(rf'--{pfx}-{ab}\d+$', v))) + 1
        n = f'--{pfx}-{ab}{used[ab]}'
        while n in names.values():
            used[ab] += 1; n = f'--{pfx}-{ab}{used[ab]}'
        names[h] = n
        return n

    def rule(m):
        sel, decl = m.group(1), m.group(2)
        return sel + '{' + HEX.sub(lambda x: f'var({name_of(x.group(1))})', decl) + '}'
    body = RULE.sub(rule, body)
    for k in sorted(keep, key=lambda k: -int(k.strip('\0'))):
        body = body.replace(k, keep[k])
    if not names:
        return body, {}
    block = ':root { /* page tokens (STYLE-1) */ ' + ' '.join(f'{v}: {h};' for h, v in sorted(names.items(), key=lambda kv: kv[1])) + ' }\n'
    lead = LEAD.match(body).group(1)
    return lead + block + body[len(lead):], {v: h for h, v in names.items()}


def main(argv):
    if argv and argv[0] == '--palette':
        pfx = None
        if '--prefix' in argv:   # a shorter prefix for a sheet whose KB budget has no room for the default one
            i = argv.index('--prefix'); pfx = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
        for f in argv[1:]:
            p = Path(f)
            if p.name == 'meta.css':
                print(f'{f}: skipped (defines the tokens)'); continue
            use = pfx or prefix(p.name)
            clash = [o.name for o in p.parent.glob('*.css') if o != p and re.search(rf'--{re.escape(use)}-[a-z0-9]{{2}}\d+\s*:', o.read_text())]
            if clash:   # page tokens live on :root, so two sheets sharing a prefix would overwrite each other's colours
                print(f'{f}: prefix {use!r} already used by {", ".join(clash)} — pick another'); return 1
            css = p.read_text(); out, pal = palette(css, use)
            p.write_text(out)
            print(f'{f}: {outside(css)} → {outside(out)} hex outside the palette · {len(pal)} page tokens')
        return 0
    if len(argv) < 2 or argv[0] not in ('--check', '--write'):
        print(__doc__)
        return 2
    only = None
    if '--only' in argv:
        i = argv.index('--only'); only = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    for f in argv[1:]:
        p = Path(f)
        if p.name == 'meta.css':
            print(f'{f}: skipped (defines the tokens)')
            continue
        css = p.read_text()
        if argv[0] == '--check':
            print(f'{f}: {count(css)} hex')
            continue
        out = convert(css, only)
        p.write_text(out)
        print(f'{f}: {count(css)} → {count(out)} hex')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
