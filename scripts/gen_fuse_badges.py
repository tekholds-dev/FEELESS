"""Draw the Fuse badge set (430x300 jpg poster + pulsing gif), same format as the other quest badges.
Run: .venv/bin/python scripts/gen_fuse_badges.py   →  frontend/public/assets/badges/feeless/<id>.{jpg,gif}"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[1] / 'frontend' / 'public' / 'assets' / 'badges' / 'feeless'
W, H = 430, 300
VIOLET, GREEN, PINK, GOLD, CYAN = (155, 92, 255), (25, 245, 143), (255, 106, 213), (255, 211, 107), (111, 231, 255)


def base(glow):
    im = Image.new('RGB', (W, H), (10, 6, 20))
    d = ImageDraw.Draw(im)
    for r in range(150, 0, -6):   # purple radial sky
        a = (150 - r) / 150
        d.ellipse([W / 2 - r * 1.6, H / 2 - r, W / 2 + r * 1.6, H / 2 + r], fill=(int(10 + 40 * a * glow), int(6 + 10 * a), int(20 + 70 * a * glow)))
    for x in range(0, W, 32):     # grid floor
        d.line([(x, H), (W / 2 + (x - W / 2) * .25, H * .62)], fill=(60, 30, 110), width=1)
    for y in (H * .66, H * .74, H * .85):
        d.line([(0, y), (W, y)], fill=(55, 28, 100), width=1)
    return im


def hexagon(d, cx, cy, r, color, width=4):
    pts = [(cx + r * math.cos(math.pi / 3 * i - math.pi / 2), cy + r * math.sin(math.pi / 3 * i - math.pi / 2)) for i in range(7)]
    d.line(pts, fill=color, width=width, joint='curve')


def glyph(d, kind, cx, cy, s, col):
    if kind == 'fuser':        # atom
        for a in (0, 60, 120):
            box = [cx - s, cy - s * .38, cx + s, cy + s * .38]
            orb = Image.new('L', (W, H)); od = ImageDraw.Draw(orb); od.ellipse(box, outline=255, width=4)
            d._image.paste(col, mask=orb.rotate(a, center=(cx, cy)))
        d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=col)
    elif kind == 'battle_champ':   # crossed swords
        for sgn in (-1, 1):
            d.line([(cx - s * sgn, cy - s), (cx + s * .8 * sgn, cy + s * .8)], fill=col, width=7)
            d.line([(cx + s * .55 * sgn - 14, cy + s * .55 - 14 * sgn * sgn), (cx + s * .55 * sgn + 14, cy + s * .55 + 14)], fill=col, width=6)
    elif kind == 'survivor':   # shield
        d.polygon([(cx, cy - s), (cx + s * .85, cy - s * .55), (cx + s * .7, cy + s * .45), (cx, cy + s), (cx - s * .7, cy + s * .45), (cx - s * .85, cy - s * .55)], outline=col, width=6)
        d.line([(cx - s * .35, cy), (cx - s * .05, cy + s * .3), (cx + s * .4, cy - s * .3)], fill=col, width=7)
    elif kind == 'cat_slayer':   # cat head + strike
        d.ellipse([cx - s * .8, cy - s * .55, cx + s * .8, cy + s * .75], outline=col, width=6)
        d.polygon([(cx - s * .75, cy - s * .2), (cx - s * .55, cy - s * 1), (cx - s * .2, cy - s * .5)], outline=col, width=5)
        d.polygon([(cx + s * .75, cy - s * .2), (cx + s * .55, cy - s * 1), (cx + s * .2, cy - s * .5)], outline=col, width=5)
        d.line([(cx - s, cy + s * .9), (cx + s, cy - s * .9)], fill=GOLD, width=6)
    elif kind == 'medalist':   # medal + ribbon
        d.polygon([(cx - s * .55, cy - s), (cx - s * .15, cy - s), (cx + s * .1, cy - s * .2), (cx - s * .3, cy - s * .2)], fill=VIOLET)
        d.polygon([(cx + s * .55, cy - s), (cx + s * .15, cy - s), (cx - s * .1, cy - s * .2), (cx + s * .3, cy - s * .2)], fill=PINK)
        d.ellipse([cx - s * .6, cy - s * .35, cx + s * .6, cy + s * .85], outline=col, width=7)
        d.ellipse([cx - s * .25, cy + s * .05, cx + s * .25, cy + s * .45], fill=col)


BADGES = {'fuser': GREEN, 'battle_champ': VIOLET, 'survivor': CYAN, 'cat_slayer': PINK, 'medalist': GOLD}


def frame(kind, col, t):
    glow = .75 + .25 * math.sin(t * 2 * math.pi)
    im = base(glow)
    halo = Image.new('RGB', (W, H)); hd = ImageDraw.Draw(halo)
    hexagon(hd, W / 2, H / 2 - 6, 96 + 4 * glow, col, width=10)
    im = Image.blend(im, Image.composite(halo, im, halo.convert('L').point(lambda v: 255 if v else 0)).filter(ImageFilter.GaussianBlur(8)), .55)
    d = ImageDraw.Draw(im)
    hexagon(d, W / 2, H / 2 - 6, 96, col, width=4)
    glyph(d, kind, W / 2, H / 2 - 6, 52, col)
    return im


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    for kind, col in BADGES.items():
        frames = [frame(kind, col, i / 12) for i in range(12)]
        frames[0].save(OUT / f'{kind}.jpg', quality=82)
        frames[0].save(OUT / f'{kind}.gif', save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)
        print(kind, (OUT / f'{kind}.jpg').stat().st_size, (OUT / f'{kind}.gif').stat().st_size)
