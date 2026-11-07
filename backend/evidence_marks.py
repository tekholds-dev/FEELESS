"""🖍 EVIDENCE MARKS (owner 2026-11-05): every snapshot shows what was read from it. The words and numbers are found on the live page itself and boxed on the picture, and the picture is fingerprinted, so a proof can't claim to have read something the page never showed. A value not on the page is recorded as missing, never drawn."""
import hashlib
import io
import json
import re

MAX_BOXES = 30
_DEFAULT = r"\$\s?\d[\d,.]*\s?[KMBkmb]?|\b\d[\d,.]*\s?%|\b\d{1,3}(?:,\d{3})+\b"

FIND_JS = r"""(args) => {
  const words = (args.words || []).map(w => String(w).toLowerCase()).filter(w => w.length > 0);
  const re = args.pattern ? new RegExp(args.pattern, 'g') : null;
  const found = {}, rects = []; let off = null;
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n, seen = 0;
  while ((n = walk.nextNode()) && seen < 8000 && rects.length < args.max) {
    seen++;
    const t = n.nodeValue;
    if (!t || t.length > 1200) continue;
    const el = n.parentElement;
    if (!el || ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName)) continue;
    const low = t.toLowerCase();
    const hits = [];
    const edge = c => !c || !/[a-z0-9]/.test(c);
    for (const w of words) { const i = low.indexOf(w); if (i >= 0 && edge(low[i - 1]) && edge(low[i + w.length])) hits.push([i, i + w.length, w]); }
    if (re) { re.lastIndex = 0; let m; while ((m = re.exec(t)) && hits.length < 6) hits.push([m.index, m.index + m[0].length, m[0]]); }
    for (const [a, b, w] of hits) {
      const r = document.createRange(); r.setStart(n, a); r.setEnd(n, b);
      if (args.scroll && !off && el.getClientRects().length) { const c0 = r.getClientRects()[0]; if (c0 && (c0.bottom < 0 || c0.top > innerHeight)) off = el; }
      for (const c of r.getClientRects()) {
        if (c.width > 1 && c.height > 1 && c.bottom > 0 && c.right > 0 && c.top < innerHeight && c.left < innerWidth) { rects.push([c.left, c.top, c.right, c.bottom]); found[w] = (found[w] || 0) + 1; break; }
      }
    }
  }
  if (args.scroll && off && !rects.length) { off.scrollIntoView({ block: 'center' }); return { moved: true, rects, found, w: innerWidth, h: innerHeight }; }
  return { rects, found, w: innerWidth, h: innerHeight };
}"""


def value_words(values):
    """The ways a value the brain read can look on a page: '$12,345', '12345', '12,345', '45%', '45'. A bare one or two digit number alone is left out: it would box half a page. Pure."""
    out = []
    for v in values or []:
        t = str(v or '').strip()
        if not t:
            continue
        forms = [t, t.lstrip('$'), t.replace(',', ''), t.lstrip('$').replace(',', '')]
        m = re.fullmatch(r'\$?(\d+)(\.\d+)?', t.replace(',', ''))
        if m:
            forms.append(f"{int(m.group(1)):,}{m.group(2) or ''}")
        for f in forms:
            f = f.strip().lower()
            if f and f not in out and not re.fullmatch(r'\d{1,2}', f):
                out.append(f)
    return out


DEAD_SPREAD = 6.0


def is_dead(jpg):
    """A blank or nearly one-colour picture is no evidence of anything. Pure."""
    from PIL import Image, ImageStat
    try:
        im = Image.open(io.BytesIO(jpg)).convert('L').resize((64, 64))
        return ImageStat.Stat(im).stddev[0] < DEAD_SPREAD
    except Exception:   # noqa: BLE001 — bytes it cannot judge are kept, not thrown away
        return False


def words_of(texts, n=14):
    """Worth-finding words from trend titles: the longer, the more telling. Pure."""
    seen = []
    for t in texts or []:
        for w in re.findall(r"[A-Za-z0-9$][A-Za-z0-9'$.-]{3,}", str(t)):
            k = w.lower().strip(".'")
            if k not in seen and k not in ('with', 'from', 'that', 'this', 'what', 'have', 'will', 'more', 'over', 'after', 'about', 'their', 'there', 'your', 'news'):
                seen.append(k)
    return sorted(seen, key=len, reverse=True)[:n]


def draw(jpg, marks, stamp=''):
    """Box what was found on the picture and print what was read along the bottom. → jpg bytes."""
    from PIL import Image, ImageDraw
    im = Image.open(io.BytesIO(jpg)).convert('RGB'); W, H = im.size; sx = W / max(1, marks.get('w') or W); sy = H / max(1, marks.get('h') or H)
    over = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(over)
    for r in (marks.get('rects') or [])[:MAX_BOXES]:
        box = [r[0] * sx - 3, r[1] * sy - 2, r[2] * sx + 3, r[3] * sy + 2]
        d.rounded_rectangle(box, radius=3, fill=(62, 229, 138, 46), outline=(62, 229, 138, 255), width=2)
    if stamp:
        d.rectangle([0, H - 22, W, H], fill=(6, 12, 28, 225)); d.text((8, H - 17), str(stamp)[:int(W / 6)], fill=(191, 230, 255, 255))
    out = io.BytesIO(); Image.alpha_composite(im.convert('RGBA'), over).convert('RGB').save(out, 'JPEG', quality=62)
    return out.getvalue()


def fingerprint(jpg, url, at, found):
    return hashlib.sha256(jpg + json.dumps([str(url), int(at), sorted((found or {}).keys())]).encode()).hexdigest()[:32]


LIVE_MAX = 14
LIVE_JS = r"""(args) => {
  const old = document.getElementById('feeless-marks'); if (old) old.remove();
  const rows = args.rects || []; if (!rows.length) return 0;
  const box = document.createElement('div'); box.id = 'feeless-marks'; box.setAttribute('aria-hidden', 'true'); box.style.cssText = 'position:fixed;inset:0;z-index:2147483646;pointer-events:none;';
  rows.forEach(r => { const m = document.createElement('i'); m.style.cssText = `position:fixed;left:${r[0] - 4}px;top:${r[1] - 3}px;width:${r[2] - r[0] + 8}px;height:${r[3] - r[1] + 6}px;box-sizing:border-box;border:2px solid ${args.color};border-radius:4px;background:${args.color}1f;box-shadow:0 0 10px ${args.color}80;`; box.appendChild(m); });
  document.documentElement.appendChild(box);
  const top = Math.max(0, outerHeight - innerHeight), W = outerWidth || innerWidth, H = outerHeight || innerHeight;
  return { n: rows.length, pts: rows.slice(0, 8).map(r => [Math.min(1, Math.max(0, (r[0] + r[2]) / 2 / W)), Math.min(1, Math.max(0, (top + (r[1] + r[3]) / 2) / H))]) };
}"""
SEEN = '#3ee58a'   # what the mind says it is reading
HUNT = '#ffc24d'   # the words of the job, found on a page it just opened


def mark_words(a):
    """The words a mind says it read on this screen: its "mark" list, and the value of every fact it pulled. Pure. → [text]"""
    a = a if isinstance(a, dict) else {}; rows = a.get('mark') if isinstance(a.get('mark'), list) else [a.get('mark')] if isinstance(a.get('mark'), str) else []
    rows = [str(x).strip() for x in rows if str(x or '').strip()] + [str(f.get('value')).strip() for f in (a.get('facts') if isinstance(a.get('facts'), list) else []) if isinstance(f, dict) and f.get('value')]
    return [w[:120].lower() for w in dict.fromkeys(rows) if len(w) > 1][:10]


async def live_marks(page, words, color=SEEN):
    """🖍 Lined boxes round what it is reading, in the window itself, so the owner watches them land. They sit on top and take no clicks, and the next set replaces them. Only text really on the screen gets one. Never stops the work. → {n, pts: where each box is as a share of the window, found: the words it found}"""
    try:
        draw_ = getattr(page, 'draw_marks', None)
        if not draw_ or not words:
            return {'n': 0, 'pts': [], 'found': []}
        got = await draw_(f"() => ({FIND_JS})({json.dumps({'words': list(words or []), 'pattern': None, 'max': LIVE_MAX, 'scroll': False})})") or {}
        drawn = await draw_(f"() => ({LIVE_JS})({json.dumps({'rects': got.get('rects') or [], 'color': color})})") or {}
        drawn = drawn if isinstance(drawn, dict) else {'n': int(drawn or 0), 'pts': []}
        return {'n': drawn.get('n') or 0, 'pts': drawn.get('pts') or [], 'found': [w for w in words if w in (got.get('found') or {})]}
    except Exception:   # noqa: BLE001 — a box is a nicety
        return {'n': 0, 'pts': [], 'found': []}


async def marked_shot(page, words=None, now=0, pattern=None, read=False):
    """A snapshot with what it read boxed on it. → {jpg, found, missing, read, sha} or None. Boxes come only from `words`, the things the brain really read: nothing is boxed for a page it merely opened, unless a caller asks for a pattern. It scrolls to a value that sits off screen, and it takes the picture right after finding the boxes, so they line up. A blank page returns None. A failed mark keeps a plain picture, and says it has none."""
    words = list(words or []); found = {}; marks = {}
    try:
        if words or pattern:
            args = {'words': words, 'pattern': pattern, 'max': MAX_BOXES, 'scroll': True}; marks = await page.find_private(f'() => ({FIND_JS})({json.dumps(args)})') or {}
            if marks.get('moved'):
                marks = await page.find_private(f'() => ({FIND_JS})({json.dumps({**args, "scroll": False})})') or {}
            found = marks.get('found') or {}
    except Exception:   # noqa: BLE001 — a picture without boxes is still evidence, and it says so
        marks = {}; found = {}
    jpg = await page.shot()
    if not jpg or is_dead(jpg):
        return None
    if marks.get('rects'):
        jpg = draw(jpg, marks, f"FEELESS read: {', '.join(list(found)[:8])}")
    return {'jpg': jpg, 'found': found, 'missing': [w for w in words if w not in found], 'read': bool(read and found), 'sha': fingerprint(jpg, getattr(page, 'url', ''), now, found)}
