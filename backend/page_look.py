"""👁 What a page really looks like, measured in a real browser at desktop and phone width. The score used to read only code, so a page with cards sitting on its own words could rank S (owner 2026-11-07).
Runs the locked page (`agent_features.preview`) with nothing but https allowed and no file or local address. Numbers only are kept: never a page."""
import json
from pathlib import Path
from fnum import plain as _n

STORE = 'page_looks.json'
SIZES = (('desktop', 1280, 800), ('phone', 390, 800))
SCREENS = 4
BROKEN = 0.5        # below this a page is held down, however deep its code is
MEASURE = r"""(screens) => new Promise(done => {
  const seen = new Map(); const texts = [];
  const leafs = () => { const out = []; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
    while ((n = w.nextNode())) { if (!n.textContent.trim() || !n.parentElement || ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(n.parentElement.tagName)) continue; out.push(n); } return out; };
  const shown = el => { for (let e = el; e && e !== document.documentElement; e = e.parentElement) { const s = getComputedStyle(e); if (s.visibility === 'hidden' || s.display === 'none' || Number(s.opacity) < 0.15) return false; } return true; };
  const related = (a, b) => a === b || a.contains(b) || b.contains(a);
  const look = () => { const y = scrollY;
    for (const n of leafs()) { const el = n.parentElement; if (!shown(el)) continue; const r = document.createRange(); r.selectNodeContents(n); const b = r.getBoundingClientRect(); if (b.width < 4 || b.height < 4 || b.bottom < 0 || b.top > innerHeight) continue;
      const key = n; const row = seen.get(key) || { el, top: b.top + y, left: b.left, w: b.width, h: b.height, words: n.textContent.trim().slice(0, 30), covered: false, fixed: false }; seen.set(key, row);
      const midY = Math.min(innerHeight - 1, Math.max(0, b.top + b.height / 2)); const pts = [b.left + 3, b.left + b.width / 2, b.right - 3].filter(x => x >= 0 && x < innerWidth); let hid = 0;
      for (const x of pts) { const top = document.elementFromPoint(x, midY); if (top && !related(top, el) && !top.closest('a,button,label')?.contains(el)) hid += 1; }
      if (pts.length && hid >= 2) row.covered = true; } };
  let i = 0; const step = () => { look(); i += 1; if (i >= screens || scrollY + innerHeight >= document.documentElement.scrollHeight - 2) return finish(); scrollBy(0, innerHeight * 0.9); setTimeout(step, 450); };
  const finish = () => { scrollTo(0, 0); const rows = [...seen.values()]; let overlaps = 0; const said = [];
    for (let a = 0; a < rows.length; a += 1) for (let b = a + 1; b < rows.length; b += 1) { const p = rows[a]; const q = rows[b]; if (related(p.el, q.el)) continue; const ox = Math.min(p.left + p.w, q.left + q.w) - Math.max(p.left, q.left); const oy = Math.min(p.top + p.h, q.top + q.h) - Math.max(p.top, q.top); if (ox > 4 && oy > 4 && ox * oy > 0.2 * Math.min(p.w * p.h, q.w * q.h)) { overlaps += 1; if (said.length < 3) said.push(p.words); } }
    done({ overlaps, covered: rows.filter(r => r.covered).length, texts: rows.length, side: Math.max(0, document.documentElement.scrollWidth - innerWidth), said, coveredWords: rows.filter(r => r.covered).slice(0, 3).map(r => r.words) }); };
  step(); })"""


def path_of(root):
    return Path(root) / STORE


def load(root):
    try:
        d = json.loads(path_of(root).read_text())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save(root, rows):
    p = path_of(root); p.parent.mkdir(parents=True, exist_ok=True); tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(rows)); tmp.replace(p)


def key_of(cat_id, ws, version):
    return f'{cat_id}:{ws}:{int(version or 0)}'


def score(sizes):
    """{size: measures} → (0 to 1, note). Words on words and words under something cost most; a page that cannot be read at all gets nothing. Pure, so it can be tested without a browser."""
    if not sizes:
        return None, 'Not looked at yet'
    worst = 1.0; bits = []
    for name, m in sizes.items():
        if not m.get('texts'):
            worst = 0.0; bits.append(f'{name}: nothing to read'); continue
        crowd = _n(m.get('overlaps')); hid = _n(m.get('covered')); side = _n(m.get('side')) > 4; err = _n(m.get('errors'))
        v = 1.0 - min(0.7, 0.14 * crowd) - min(0.5, 0.08 * hid) - (0.25 if side else 0.0) - min(0.3, 0.15 * err); worst = min(worst, max(0.0, v))
        said = [f'{int(crowd)} overlaps' if crowd else '', f'{int(hid)} covered' if hid else '', 'scrolls sideways' if side else '', f'{int(err)} script errors' if err else '']
        if any(said):
            bits.append(f"{name}: {', '.join(x for x in said if x)}")
    return round(worst, 3), ('; '.join(bits) or 'Nothing overlaps at either size')[:150]



async def shot(html, chromium, w=1280, h=800, wait=7000):
    """A picture of one page, so a mind can look at its own work. → jpeg bytes or None."""
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=chromium, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        try:
            ctx = await b.new_context(viewport={'width': w, 'height': h})
            async def only_https(route):
                await (route.continue_() if route.request.url.startswith(('https://', 'data:', 'blob:', 'about:')) and route.request.method == 'GET' else route.abort())
            await ctx.route('**/*', only_https); pg = await ctx.new_page()
            await pg.set_content(html, wait_until='domcontentloaded', timeout=15000); await pg.wait_for_timeout(wait)
            return await pg.screenshot(type='jpeg', quality=60, timeout=60000)
        finally:
            await b.close()


MEASURE_S = 90   # 2026-11-14: a headless Chromium that never answered hung the push gate for 33 min — a look check now fails, never hangs


async def measure(html, chromium, limit=MEASURE_S):
    """Opens one page at both sizes. → {size: measures}. Each size has its own context, so nothing carries over. Raises TimeoutError
    after `limit` seconds (a stuck browser never holds its caller)."""
    import asyncio
    return await asyncio.wait_for(_measure(html, chromium), limit)


async def _measure(html, chromium):
    from playwright.async_api import async_playwright
    out = {}
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=chromium, timeout=30000)
        try:
            for name, w, h in SIZES:
                ctx = await b.new_context(viewport={'width': w, 'height': h}); errs = []
                async def only_https(route):
                    await (route.continue_() if route.request.url.startswith(('https://', 'data:', 'blob:', 'about:')) and route.request.method == 'GET' else route.abort())
                await ctx.route('**/*', only_https); pg = await ctx.new_page(); pg.on('pageerror', lambda e, box=errs: box.append(str(e)[:80]))
                await pg.set_content(html, wait_until='domcontentloaded', timeout=15000); await pg.wait_for_timeout(1800)
                out[name] = {**await pg.evaluate(MEASURE, SCREENS), 'errors': len(errs)}
                await ctx.close()
        finally:
            await b.close()
    return out
