"""✂ Slice 29 (owner 2026-11-20: "able to edit captions and different transition and effects user or ai can use to make unique and ultimate
design"). A clip's LOOK: caption style (font, colour, size, position, word-by-word highlight, words per line, case, the words themselves and their
timing), a transition (cut, fade, zoom, whip, glitch) and effects (punch-in zoom, shake, colour grade, speed ramp, word pop). The owner or the
minds pick it; this file turns it into one ffmpeg run on this machine ($0, no watermark). No two clips of an agent share the same look.

Research 2026-11-20: the open clippers (captify, pycaps, caption-cast, the kinetic-subtitle write-ups) all draw word-highlight captions from
word times with Pillow or ASS and burn them with ffmpeg. This Mac's ffmpeg has no libass / drawtext, so captions stay Pillow bands (a concat
picture stream). Effects use `scale … eval=frame` + `crop` expressions (zoompan jitters on video), `rgbashift` / `noise` on the timeline
(glitch), `tmix` (whip blur), `eq` / `curves` (grade, dips), trim + setpts + atempo (speed, sound kept in sync). One real render checked
2026-11-20 on the ohara_iphone upload: a 9:16 5 s clip with punch-in, glitch, vintage grade, fade and 1.15× speed in 2.1 s."""
import json
import re
import subprocess
import time
from pathlib import Path

import clip_farm as _cf

SYS_FONTS = Path('/System/Library/Fonts')
FONTS = {   # key → (label, file, ttc index). A font missing on this machine falls back to the bundled Liberation Sans Bold.
    'bold': ('Bold sans', _cf.FONT, 0),
    'impact': ('Impact', SYS_FONTS / 'Supplemental' / 'Impact.ttf', 0),
    'condensed': ('Condensed heavy', SYS_FONTS / 'Avenir Next Condensed.ttc', 8),
    'rounded': ('Rounded', SYS_FONTS / 'Supplemental' / 'Arial Rounded Bold.ttf', 0),
    'serif': ('Serif', SYS_FONTS / 'Supplemental' / 'Georgia Bold.ttf', 0),
    'chalk': ('Chalk', SYS_FONTS / 'Supplemental' / 'Chalkduster.ttf', 0),
}
COLORS = {'white': (255, 255, 255, 255), 'cream': (255, 244, 214, 255), 'yellow': (255, 214, 10, 255), 'green': _cf.GREEN,
          'cyan': (40, 220, 255, 255), 'pink': (255, 70, 160, 255), 'orange': (255, 140, 30, 255)}
BASE_COLORS = ('white', 'cream', 'yellow')
HOT_COLORS = ('green', 'yellow', 'cyan', 'pink', 'orange', 'white')
SIZES = {'S': .8, 'M': 1.0, 'L': 1.2}
POS = {'top': .22, 'mid': .44, 'low': .64, 'bottom': .76}          # the band's top, as a share of the frame height
MODES = ('word', 'box', 'karaoke', 'plain')
TRANS = ('cut', 'fade', 'zoom', 'whip', 'glitch')
GRADES = {'none': '', 'warm': 'eq=saturation=1.15:gamma_r=1.06:gamma_b=0.94', 'teal': 'curves=r=0/0 0.5/0.46 1/1:b=0/0.06 0.5/0.56 1/0.94,eq=saturation=1.1',
          'mono': 'hue=s=0,eq=contrast=1.12', 'punchy': 'eq=contrast=1.12:saturation=1.3', 'vintage': 'curves=preset=vintage,eq=saturation=1.1',
          'cool': 'eq=saturation=1.05:gamma_b=1.07:gamma_r=0.95'}
SPEEDS = ('off', 'tight', 'ramp')
DEFAULT = {'cap': {'font': 'bold', 'color': 'white', 'hot': 'green', 'size': 'M', 'pos': 'low', 'mode': 'word', 'words': 3, 'case': 'upper'},
           'tr': 'cut', 'fx': {'punch': False, 'shake': False, 'grade': 'none', 'speed': 'off', 'pop': False}, 'edit': {'w': {}, 'off': 0.0}}
# Named starting points (the owner or the minds start from one, then change anything). New clips get one each, nudged unique.
PRESETS = {
    'classic': {'cap': {}, 'tr': 'cut', 'fx': {}},
    'hype': {'cap': {'font': 'impact', 'hot': 'yellow', 'size': 'L', 'mode': 'box', 'words': 2}, 'tr': 'zoom', 'fx': {'punch': True, 'shake': True, 'grade': 'punchy', 'speed': 'tight', 'pop': True}},
    'clean': {'cap': {'font': 'rounded', 'hot': 'cyan', 'size': 'S', 'pos': 'bottom', 'mode': 'karaoke', 'case': 'said'}, 'tr': 'fade', 'fx': {'grade': 'cool'}},
    'cinema': {'cap': {'font': 'serif', 'color': 'cream', 'hot': 'orange', 'mode': 'plain', 'case': 'said', 'pos': 'bottom'}, 'tr': 'fade', 'fx': {'grade': 'teal', 'speed': 'ramp'}},
    'glitch': {'cap': {'font': 'condensed', 'hot': 'pink', 'mode': 'word', 'words': 1, 'size': 'L', 'pos': 'mid'}, 'tr': 'glitch', 'fx': {'punch': True, 'grade': 'mono', 'pop': True}},
    'story': {'cap': {'font': 'chalk', 'color': 'yellow', 'hot': 'white', 'mode': 'karaoke', 'words': 2}, 'tr': 'whip', 'fx': {'grade': 'vintage', 'punch': True}},
}
PRESET_ORDER = ('classic', 'hype', 'clean', 'cinema', 'glitch', 'story')
STOP = set('the a an and or but so to of in on at for with from this that these those it its is are was were be been being i you he she we they me my your our their '
           'just like really very what when where which who how then than there here have has had do does did not no yes can could would should will about into out up down'.split())


def _pick(v, allowed, dflt):
    return v if v in allowed else dflt


def clean_look(d=None):
    """Any look (from the page, a mind or an old version) → a whole, valid look. Unknown values fall back to the default. Pure."""
    d = d if isinstance(d, dict) else {}; c = d.get('cap') if isinstance(d.get('cap'), dict) else {}; fx = d.get('fx') if isinstance(d.get('fx'), dict) else {}
    ed = d.get('edit') if isinstance(d.get('edit'), dict) else {}; dc, dfx = DEFAULT['cap'], DEFAULT['fx']
    try:
        nw = int(c.get('words', dc['words']))
    except (TypeError, ValueError):
        nw = dc['words']
    try:
        off = float(ed.get('off') or 0)
    except (TypeError, ValueError):
        off = 0.0
    words = {}
    for k, v in (ed.get('w') or {}).items() if isinstance(ed.get('w'), dict) else []:
        if str(k).isdigit():
            words[str(int(k))] = ' '.join(str(v or '').split())[:40]   # '' drops the word from the captions
    return {'cap': {'font': _pick(c.get('font'), FONTS, dc['font']), 'color': _pick(c.get('color'), BASE_COLORS, dc['color']), 'hot': _pick(c.get('hot'), HOT_COLORS, dc['hot']),
                    'size': _pick(c.get('size'), SIZES, dc['size']), 'pos': _pick(c.get('pos'), POS, dc['pos']), 'mode': _pick(c.get('mode'), MODES, dc['mode']),
                    'words': max(1, min(3, nw)), 'case': _pick(c.get('case'), ('upper', 'said'), dc['case'])},
            'tr': _pick(d.get('tr'), TRANS, DEFAULT['tr']),
            'fx': {'punch': bool(fx.get('punch')), 'shake': bool(fx.get('shake')), 'grade': _pick(fx.get('grade'), GRADES, dfx['grade']),
                   'speed': _pick(fx.get('speed'), SPEEDS, dfx['speed']), 'pop': bool(fx.get('pop'))},
            'edit': {'w': dict(sorted(words.items(), key=lambda kv: int(kv[0]))[:400]), 'off': round(max(-1.0, min(1.0, off)), 2)},
            **({'preset': d['preset']} if d.get('preset') in PRESETS else {})}


def preset(name):
    p = PRESETS.get(name) or PRESETS['classic']
    return clean_look({'cap': {**DEFAULT['cap'], **p['cap']}, 'tr': p['tr'], 'fx': {**DEFAULT['fx'], **p['fx']}, 'preset': name if name in PRESETS else 'classic'})


def merge(look, patch):
    """A partial change (the chat's, a mind's) onto a look → a whole look. Pure."""
    a = clean_look(look); p = patch if isinstance(patch, dict) else {}
    if p.get('preset') in PRESETS:
        b = preset(p['preset']); b['edit'] = a['edit']; a = b
    return clean_look({'cap': {**a['cap'], **(p.get('cap') or {})}, 'tr': p.get('tr') or a['tr'], 'fx': {**a['fx'], **(p.get('fx') or {})},
                       'edit': {'w': {**a['edit']['w'], **((p.get('edit') or {}).get('w') or {})}, 'off': (p.get('edit') or {}).get('off', a['edit']['off'])},
                       **({'preset': a['preset']} if a.get('preset') and not (set(p) - {'preset'}) else {})})


def sig(look):
    """The look's design (everything but its word edits) as one string: two clips with the same sig look the same. Pure."""
    a = clean_look(look)
    return json.dumps({'cap': a['cap'], 'tr': a['tr'], 'fx': a['fx']}, sort_keys=True)


NUDGES = (('cap', 'hot', HOT_COLORS), ('fx', 'grade', tuple(GRADES)), ('cap', 'font', tuple(FONTS)), ('tr', None, TRANS), ('cap', 'pos', tuple(POS)), ('cap', 'mode', MODES))


def unique(look, used):
    """The look, or the nearest one no other clip uses (changes the hot colour first, then the grade, font, transition …). Pure."""
    a = clean_look(look); used = set(used or ())
    if sig(a) not in used:
        return a, ''
    for grp, key, vals in NUDGES:
        for v in vals:
            b = json.loads(json.dumps(a)); b.pop('preset', None)
            if key:
                b[grp][key] = v
            else:
                b['tr'] = v
            if sig(b) not in used:
                return clean_look(b), f"{key or 'transition'} → {v} (another clip already had that exact look)"
    return a, ''


def describe(look):
    """A short plain line about a look (shown on its tile and given to the minds). Pure."""
    a = clean_look(look); c, fx = a['cap'], a['fx']
    on = [k for k in ('punch', 'shake', 'pop') if fx[k]] + ([f"{fx['grade']} grade"] if fx['grade'] != 'none' else []) + ([f"speed {fx['speed']}"] if fx['speed'] != 'off' else [])
    return f"{FONTS[c['font']][0]} {c['size']} {c['color']}/{c['hot']} {c['mode']} {c['words']}w {c['pos']} · {a['tr']}" + (f" · {', '.join(on)}" if on else '')


# ── time: speed, beats, where the effects land ──────────────────────────────────────────────────────────────────────────────────────
def segments(look, dur):
    """[(from s, to s, speed)] over the clip (source seconds from its start). Pure."""
    sp = clean_look(look)['fx']['speed']
    if sp == 'tight':
        return [(0.0, dur, 1.1)]
    if sp == 'ramp' and dur > 8:
        return [(0.0, dur - 2.5, 1.25), (dur - 2.5, dur, 1.0)]   # quick through the build-up, real time for the payoff
    return [(0.0, dur, 1.0)]


def tmap(t, segs):
    """Source seconds (from the clip start) → output seconds. Pure."""
    out = 0.0
    for a, b, sp in segs:
        if t <= b:
            return out + (max(t, a) - a) / sp
        out += (b - a) / sp
    return out


def out_dur(segs):
    return sum((b - a) / sp for a, b, sp in segs)


def clip_words(words, s, e, look):
    """The clip's words with the owner's edits (text changed, '' = dropped) and timing offset, times from the clip start. Pure."""
    a = clean_look(look); ed = a['edit']['w']; off = a['edit']['off']; out = []
    for i, w in enumerate(x for x in words if x['e'] > s and x['s'] < e):
        txt = ed.get(str(i), w['w'])
        if not str(txt).strip():
            continue
        out.append({'i': i, 'w': str(txt), 's': max(0.0, w['s'] - s + off), 'e': max(0.05, min(e - s, w['e'] - s + off))})
    return out


def beats(ws, dur):
    """Where a new sentence starts after a pause (and the start): the transition and punch-in points, ≥ 2.5 s apart, at most 7. Pure."""
    pts = [0.0]
    for i in range(1, len(ws)):
        if (ws[i]['s'] - ws[i - 1]['e'] > .3 or re.search(r'[.!?]$', ws[i - 1]['w'])) and ws[i]['s'] - pts[-1] >= 2.5 and ws[i]['s'] < dur - 1.5:
            pts.append(round(ws[i]['s'], 2))
    return pts[:7]


def pops(ws, dur, most=3):
    """The words that pop as stickers: numbers and long uncommon words, ≥ 3 s apart. → [(t, WORD)] Pure."""
    out = []
    for w in ws:
        t = re.sub(r"[^\w$%'-]", '', w['w'])
        if (re.search(r'\d', t) or (len(t) >= 7 and t.lower() not in STOP)) and (not out or w['s'] - out[-1][0] >= 3) and w['s'] < dur - .8:
            out.append((round(w['s'], 2), t.upper()))
    return out[:most]


# ── pictures: caption bands, the hook title, word pops ──────────────────────────────────────────────────────────────────────────────
def font(key, px):
    from PIL import ImageFont
    _l, path, idx = FONTS.get(key) or FONTS['bold']
    try:
        return ImageFont.truetype(str(path), max(8, int(px)), index=idx)
    except OSError:
        return _cf._font(px)


def band(W, words, hot, cap, px, done=()):
    """One caption band for one group of words, styled by the look's caption block. The whole group always fits inside the frame width
    (it shrinks, never runs off the edge). → RGBA picture W wide."""
    from PIL import Image, ImageDraw
    mode = cap['mode']; up = cap['case'] == 'upper'
    txt = [(re.sub(r"[^\w'’$%#@&!?.,-]", '', w['w']) or w['w']).upper() if up else w['w'] for w in words]
    while True:
        f, fb = font(cap['font'], px), font(cap['font'], px * (1.12 if mode == 'word' else 1.0)); stroke = max(2, int(px // 10))
        d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8))); gap = int(px * .3)
        boxes = [d0.textbbox((0, 0), t, font=fb if i == hot else f, stroke_width=stroke) for i, t in enumerate(txt)]
        widths = [b[2] - b[0] for b in boxes]; pad = int(px * .22) if mode == 'box' else 0
        total = sum(widths) + gap * (len(txt) - 1) + 2 * pad
        if total <= W * .88 or px <= 14:
            break
        px = max(14, int(px * min(.92, W * .88 / total)))
    H = int(px * 1.8); im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = (W - total) // 2 + pad; base, hc = COLORS[cap['color']], COLORS[cap['hot']]
    for i, t in enumerate(txt):
        b = boxes[i]; y = (H - (b[3] - b[1])) // 2 - b[1]; fnt = fb if i == hot else f
        fill = base
        if mode == 'word' and i == hot:
            fill = hc
        elif mode == 'karaoke' and (i in done or i == hot):
            fill = hc
        elif mode == 'box' and i == hot:
            d.rounded_rectangle((x - pad, (H - (b[3] - b[1])) // 2 - pad // 2, x + widths[i] + pad - stroke, (H + (b[3] - b[1])) // 2 + pad), radius=int(px * .22), fill=hc)
            fill = _cf.INK
        d.text((x - b[0], y), t, font=fnt, fill=fill, stroke_width=0 if (mode == 'box' and i == hot) else stroke, stroke_fill=_cf.INK)
        x += widths[i] + gap
    return im


def hook_lines(W, hook, px, key='bold'):
    """The hook title's lines: EVERY word kept (the 9:16 cut-off bug, PoC #21: "…since I was a" lost "kid."), each line inside 84 % of the
    frame, at most 3 lines (the font shrinks until it fits). → (px, lines) Pure but for the font measure."""
    from PIL import Image, ImageDraw
    words = str(hook or '').split(); d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    while True:
        f = font(key, px); lines, cur = [], ''
        for w in words:
            t = (cur + ' ' + w).strip()
            if d0.textlength(t, font=f) > W * .8 and cur:
                lines.append(cur); cur = w
            else:
                cur = t
        if cur:
            lines.append(cur)
        if (len(lines) <= 3 and all(d0.textlength(x, font=f) <= W * .84 for x in lines)) or px <= 18:
            return px, lines
        px = int(px * .9)


def hook_band(W, hook, px, cap=None):
    """The hook title for the first 2 s: ink words on a bar of the look's hot colour (FEELESS green by default). Never cut off."""
    from PIL import Image, ImageDraw
    cap = cap or DEFAULT['cap']; key = cap.get('font', 'bold'); px, lines = hook_lines(W, hook, px, key); f = font(key, px)
    d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8))); lh = int(px * 1.22); H = lh * len(lines) + int(px * .9)
    im = Image.new('RGBA', (W, max(1, H)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if not lines:
        return im
    bw = int(min(W * .94, max(d0.textlength(x, font=f) for x in lines) + px * 1.2)); col = COLORS.get(cap.get('hot'), _cf.GREEN)
    if col == COLORS['white']:
        col = _cf.GREEN
    d.rounded_rectangle(((W - bw) // 2, 0, (W + bw) // 2, H), radius=int(px * .35), fill=col)
    for i, x in enumerate(lines):
        d.text(((W - d0.textlength(x, font=f)) // 2, int(px * .45) + i * lh), x, font=f, fill=_cf.INK)
    return im


def pop_pic(W, word, cap, px, k, scale=1.0):
    """A word sticker: the word on a tilted pill of the hot colour."""
    from PIL import Image, ImageDraw
    px = max(10, int(px * scale)); f = font(cap['font'], px); d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    tw = d0.textlength(word, font=f)
    if tw > W * .7:
        px = max(10, int(px * W * .7 / tw)); f = font(cap['font'], px); tw = d0.textlength(word, font=f)
    pw, ph = int(tw + px * .9), int(px * 1.5); pill = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(pill)
    col = COLORS[cap['hot']] if cap['hot'] != 'white' else COLORS['yellow']
    d.rounded_rectangle((0, 0, pw - 1, ph - 1), radius=ph // 2, fill=col, outline=_cf.INK, width=max(2, px // 14))
    d.text(((pw - tw) // 2, int(px * .2)), word, font=f, fill=_cf.INK)
    pill = pill.rotate((-7, 6, -4)[k % 3], expand=True, resample=Image.BICUBIC)
    out = Image.new('RGBA', (W, int(px * 2.6 / max(scale, .5)) + 8), (0, 0, 0, 0))
    out.alpha_composite(pill, ((W - pill.width) // 2 + (-1, 1, 0)[k % 3] * int(W * .12), max(0, (out.height - pill.height) // 2)))
    return out


def _concat(rows, tmp, name):
    lst = Path(tmp) / f'{name}.txt'
    lst.write_text('ffconcat version 1.0\n' + ''.join(f"file '{p.name}'\nduration {d:.3f}\n" for p, d in rows) + f"file '{rows[-1][0].name}'\n")
    return lst


def caption_track(ws, dur, W, H, tmp, fmt, look):
    """The styled captions as one picture stream (output times) → (list path, band y, band count)."""
    from PIL import Image
    a = clean_look(look); cap = a['cap']
    px = {'story': 88, 'feed': 66, 'wide': 60}[fmt] * SIZES[cap['size']]; bh = int(px * 1.8)
    y = int(min(H * POS[cap['pos']], H - bh - H * .04))
    blank = Path(tmp) / f'{fmt}_cblank.png'; Image.new('RGBA', (W, bh), (0, 0, 0, 0)).save(blank)
    rows, t, k = [], 0.0, 0
    for g in _cf.groups([{'s': w['s'], 'e': w['e'], 'w': w['w']} for w in ws], 0.0, dur, most=cap['words']):
        for i, w in enumerate(g):
            s_ = w['s']; e_ = g[i + 1]['s'] if i + 1 < len(g) else max(w['e'], s_ + .25)
            if s_ > t + .01:
                rows.append((blank, s_ - t))
            p = Path(tmp) / f'{fmt}_c{k}.png'; im = band(W, g, i, cap, px, done=range(i))
            if im.height != bh:
                im = im.crop((0, (im.height - bh) // 2, W, (im.height - bh) // 2 + bh)) if im.height > bh else _pad(im, W, bh)
            im.save(p, compress_level=1); k += 1
            rows.append((p, max(.04, e_ - max(s_, t)))); t = max(t, e_)
    if t < dur:
        rows.append((blank, dur - t))
    return _concat(rows, tmp, f'{fmt}_caps'), y, k


def _pad(im, W, h):
    from PIL import Image
    out = Image.new('RGBA', (W, h), (0, 0, 0, 0)); out.alpha_composite(im, (0, (h - im.height) // 2)); return out


def pop_track(ws, dur, W, H, tmp, fmt, look):
    """The word pops as one picture stream: scale-in frames, then held for 0.8 s. → (list path, y) or None"""
    from PIL import Image
    a = clean_look(look); hits = pops(ws, dur)
    if not a['fx']['pop'] or not hits:
        return None
    px = {'story': 70, 'feed': 56, 'wide': 52}[fmt]; ph = int(px * 2.6) + 8
    blank = Path(tmp) / f'{fmt}_pblank.png'; Image.new('RGBA', (W, ph), (0, 0, 0, 0)).save(blank); rows, t = [], 0.0
    for k, (at, word) in enumerate(hits):
        if at > t + .01:
            rows.append((blank, at - t))
        for j, (sc, d) in enumerate(((.55, .05), (.85, .05), (1.1, .06), (1.0, .64))):
            p = Path(tmp) / f'{fmt}_p{k}_{j}.png'; _pad(pop_pic(W, word, a['cap'], px, k, sc).crop((0, 0, W, ph)), W, ph).save(p, compress_level=1)
            rows.append((p, d))
        t = at + .8
    if t < dur:
        rows.append((blank, dur - t))
    return _concat(rows, tmp, f'{fmt}_pops'), int(H * (.30 if a['cap']['pos'] != 'top' else .52))


# ── the ffmpeg graph ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _win(ts, a, b):
    return '+'.join(f'between(t,{t + a:.2f},{t + b:.2f})' for t in ts) or '0'


def fx_chain(look, W, H, dur, bts, pop_ts):
    """The effect filters (output time t) after the reframe and the speed. → filter string ('null' when nothing). Pure."""
    a = clean_look(look); fx = a['fx']; tr = a['tr']; parts = []
    if GRADES[fx['grade']]:
        parts.append(GRADES[fx['grade']])
    z = []
    if fx['punch']:   # every other sentence is punched in (the talking-head jump-cut look)
        z += [f"0.12*between(t,{bts[i]:.2f},{(bts[i + 1] if i + 1 < len(bts) else dur + 1):.2f})" for i in range(1, len(bts), 2)]
    if tr == 'zoom':
        z += [f"0.22*max(0,1-(t-{b:.2f})/0.35)*between(t,{b:.2f},{b + .35:.2f})" for b in bts]
    shake = _win(pop_ts or bts[1:3], 0, .4) if fx['shake'] else ''
    whip = _win(bts[1:], -.1, .12) if tr == 'whip' else ''
    slack = .08 if whip else .05 if shake else 0
    if z or slack:
        zz = '+'.join(z) or '0'
        parts.append(f"scale=w='2*trunc({W}*(1+{slack}+{zz})/2)':h='2*trunc({H}*(1+{slack}+{zz})/2)':eval=frame")
        dx = '0'; dy = '0'
        if shake:
            dx += f"+{int(W * .018)}*sin(t*41)*({shake})"; dy += f"+{int(H * .012)}*cos(t*37)*({shake})"
        if whip:
            dx += f"+{int(W * .035)}*sin(t*60)*({whip})"
        parts.append(f"crop={W}:{H}:'(iw-{W})/2+{dx}':'(ih-{H})/2+{dy}'")
    if whip:
        parts.append(f"tmix=frames=5:weights='1 1 1 1 1':enable='{whip}'")
    if tr == 'glitch':
        g = _win(bts, 0, .22)
        parts += [f"rgbashift=rh={int(W * .014)}:bh=-{int(W * .014)}:enable='{g}'", f"noise=alls=45:allf=t:enable='{g}'"]
    if tr == 'fade':
        dip = '+'.join(f"0.55*max(0,1-abs(t-{b:.2f})/0.14)" for b in bts[1:]) or '0'
        parts.append(f"eq=brightness='-({dip})':eval=frame")
        parts += ['fade=t=in:st=0:d=0.3', f'fade=t=out:st={max(0.0, dur - .35):.2f}:d=0.35']
    return ','.join(parts) or 'null'


def graph(look, base, W, H, dur_src, ws, cy, hy, pop=None):
    """The whole filter_complex for one format: reframe → speed (sound kept in sync) → effects → captions → hook → pops. Pure."""
    segs = segments(look, dur_src); dur = out_dur(segs); bts = beats(ws, dur); pts_ = [t for t, _w in pops(ws, dur)] if clean_look(look)['fx']['pop'] else []
    if len(segs) == 1 and segs[0][2] == 1.0:
        sp = '[b]null[s];[0:a]anull[a]'
    else:
        k = len(segs); vs = ''.join(f'[b{i}]' for i in range(k)); as_ = ''.join(f'[a{i}]' for i in range(k))
        sp = (f'[b]split={k}{vs};[0:a]asplit={k}{as_};' if k > 1 else '[b]null[b0];[0:a]anull[a0];')
        sp += ';'.join(f'[b{i}]trim={a_:.3f}:{b_:.3f},setpts=(PTS-STARTPTS)/{s_}[v{i}];[a{i}]atrim={a_:.3f}:{b_:.3f},asetpts=PTS-STARTPTS,atempo={s_}[u{i}]'
                       for i, (a_, b_, s_) in enumerate(segs))
        sp += ';' + ''.join(f'[v{i}][u{i}]' for i in range(k)) + f'concat=n={k}:v=1:a=1[s][a]'
    out = base + ';' + sp + f";[s]{fx_chain(look, W, H, dur, bts, pts_)},setsar=1[f];[f][1:v]overlay=0:{cy}:format=auto[c];[c][2:v]overlay=0:{hy}:enable='lt(t,{_cf.HOOK_S + .5})'"
    if pop:
        out += f"[d];[d][3:v]overlay=0:{pop}:format=auto"
    return out + '[v]', dur


def render(src, s, e, words, info, fmt, pts, look, hook, out, tmp, ffmpeg='ffmpeg', encoder='h264_videotoolbox'):
    """One clip in one format with its look. → seconds it took. Raises with ffmpeg's last line on a failure."""
    t0 = time.time(); a = clean_look(look); W, H, _ = _cf.FORMATS[fmt]; box = _cf.crop_box(info, fmt); segs = segments(a, e - s)
    ws = [{**w, 's': tmap(w['s'], segs), 'e': tmap(w['e'], segs)} for w in clip_words(words, s, e, a)]; dur = out_dur(segs)
    lst, cy, _k = caption_track(ws, dur, W, H, tmp, fmt, a)
    hk = Path(tmp) / f'{fmt}_hook.png'; hook_band(W, hook, {'story': 64, 'feed': 52, 'wide': 50}[fmt], a['cap']).save(hk)
    hy = int(H * {'story': .12, 'feed': .07, 'wide': .06}[fmt])
    pop = pop_track(ws, dur, W, H, tmp, fmt, a)
    if box:
        cmds = Path(tmp) / f'{fmt}_crop.txt'; cmds.write_text(_cf.crop_cmds(pts, info, box) or '0.00 crop x 0;')
        x0 = int(max(0, min(info['w'] - box[0], (pts[0][1] if pts else .5) * info['w'] - box[0] / 2)))
        base = f"[0:v]sendcmd=f='{cmds.name}',crop={box[0]}:{box[1]}:{x0}:0,scale={W}:{H}:flags=lanczos,setsar=1[b]"
    else:
        base = (f'[0:v]split[a][f];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:2,eq=brightness=-0.12[bg];'
                f'[f]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[b]')
    filt, dur = graph(a, base, W, H, e - s, ws, cy, hy, pop[1] if pop else None)
    fps = min(30.0, info.get('fps') or 30)
    enc = (['-c:v', 'h264_videotoolbox', '-b:v', '9M' if fmt == 'story' else '7M', '-allow_sw', '1'] if encoder == 'h264_videotoolbox'
           else ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20'])
    cmd = [ffmpeg, '-v', 'error', '-nostdin', '-y', '-ss', f'{s:.2f}', '-t', f'{e - s:.2f}', '-i', str(src), '-f', 'concat', '-safe', '0', '-i', lst.name,
           '-loop', '1', '-t', f'{dur:.2f}', '-i', hk.name, *(['-f', 'concat', '-safe', '0', '-i', pop[0].name] if pop else []),
           '-filter_complex', filt, '-map', '[v]', '-map', '[a]', '-r', f'{fps:g}', *enc, '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
           '-t', f'{dur:.2f}', '-movflags', '+faststart', str(out)]
    r = subprocess.run(cmd, cwd=str(tmp), capture_output=True, timeout=600)
    if (r.returncode != 0 or not Path(out).is_file() or not Path(out).stat().st_size) and encoder != 'libx264':
        return render(src, s, e, words, info, fmt, pts, a, hook, out, tmp, ffmpeg, 'libx264')
    if r.returncode != 0:
        raise RuntimeError(((r.stderr or b'').decode(errors='replace').strip().splitlines() or [f'ffmpeg exit {r.returncode}'])[-1][:200])
    return round(time.time() - t0, 1)


def window_words(src, s, e, ffmpeg='ffmpeg'):
    """A clip made before Slice 29 kept no word times: transcribe just its window (a 30 s clip in a few seconds, local). → words, source times"""
    import numpy as np
    raw = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-ss', f'{s:.2f}', '-t', f'{e - s:.2f}', '-i', str(src), '-vn', '-f', 's16le', '-ac', '1', '-ar', '16000', '-'],
                         capture_output=True, timeout=120).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    return [{**w, 's': round(w['s'] + s, 2), 'e': round(w['e'] + s, 2)} for w in _cf.transcribe(audio)]


def lucky(n, used):
    """The starting look for the n-th new clip: the presets in turn, nudged unique. Pure."""
    return unique(preset(PRESET_ORDER[n % len(PRESET_ORDER)]), used)[0]

