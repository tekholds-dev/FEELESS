"""🖍 EVIDENCE MARKS (owner 2026-11-05): every snapshot shows what was read from it. The words and numbers are found on the live page itself and boxed on the picture, and the picture is fingerprinted, so a proof can't claim to have read something the page never showed. A value not on the page is recorded as missing, never drawn."""
import hashlib
import io
import json
import re

MAX_BOXES = 30
_DEFAULT = r"\$\s?\d[\d,.]*\s?[KMBkmb]?|\b\d[\d,.]*\s?%|\b\d{1,3}(?:,\d{3})+\b"

FIND_JS = r"""(args) => {
  const words = (args.words || []).map(w => String(w).toLowerCase()).filter(w => w.length > 2);
  const re = args.pattern ? new RegExp(args.pattern, 'g') : null;
  const found = {}, rects = [];
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
      for (const c of r.getClientRects()) {
        if (c.width > 1 && c.height > 1 && c.bottom > 0 && c.right > 0 && c.top < innerHeight && c.left < innerWidth) { rects.push([c.left, c.top, c.right, c.bottom]); found[w] = (found[w] || 0) + 1; break; }
      }
    }
  }
  return { rects, found, w: innerWidth, h: innerHeight };
}"""


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


async def marked_shot(page, words=None, now=0, pattern=_DEFAULT):
    """A snapshot with what it read boxed on it. → {jpg, found, missing, sha} or None. A failed mark still keeps a plain picture, and says it has none."""
    jpg = await page.shot()
    if not jpg:
        return None
    words = list(words or [])
    try:
        marks = await page.find_private(f'() => ({FIND_JS})({json.dumps({"words": words, "pattern": pattern, "max": MAX_BOXES})})') or {}
        found = marks.get('found') or {}
        jpg = draw(jpg, marks, f"FEELESS read: {', '.join(list(found)[:8])}" if found else '')
    except Exception:   # noqa: BLE001 — a picture without boxes is still evidence, and it says so
        found = {}
    return {'jpg': jpg, 'found': found, 'missing': [w for w in words if w not in found], 'sha': fingerprint(jpg, getattr(page, 'url', ''), now, found)}
