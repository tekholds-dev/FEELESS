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


def main(argv):
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
