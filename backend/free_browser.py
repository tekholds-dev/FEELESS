"""🆓 A snapshot with no paid browser (owner 2026-11-05: free first). Local headless Chromium on the machine the service runs on. One at a time, public pages only, no sign-ins, and it never gets past a bot check: a wall comes back as a wall."""
import asyncio
import glob
import os

import evidence_marks as _marks

_ONE = asyncio.Semaphore(1)
WALL_WORDS = ('just a moment', 'security verification', 'verify you are human', 'attention required')


def chromium_path():
    """The newest Chromium Playwright has on this machine, or None."""
    roots = [os.environ.get('PLAYWRIGHT_BROWSERS_PATH') or '', os.path.expanduser('~/Library/Caches/ms-playwright'), os.path.expanduser('~/.cache/ms-playwright')]
    for root in roots:
        if not root:
            continue
        hits = sorted(glob.glob(f'{root}/chromium-*/chrome-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing') + glob.glob(f'{root}/chromium-*/chrome-*/chrome'), reverse=True)
        if hits:
            return hits[0]
    return None


class _Page:
    def __init__(self, page):
        self._p = page
        self.url = page.url

    async def shot(self):
        return await self._p.screenshot(type='jpeg', quality=62)

    async def find_private(self, js):
        return await self._p.evaluate(js)


async def shots(urls, words, now, pattern=_marks._DEFAULT, wait_ms=2500, timeout_s=70):
    """→ [{url, site, title, jpg, found, missing, sha}] for the pages that opened and were not walled. Nothing on any failure: a proof never stops for a picture."""
    path = chromium_path()
    if not path:
        return []
    async def run():
        from playwright.async_api import async_playwright
        out = []
        async with _ONE, async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=path)
            try:
                for url in urls:
                    try:
                        pg = await b.new_page(viewport={'width': 1200, 'height': 820})
                        await pg.goto(url, timeout=20000, wait_until='domcontentloaded')
                        await pg.wait_for_timeout(wait_ms)
                        title = await pg.title()
                        if any(w in title.lower() for w in WALL_WORDS):
                            await pg.close()
                            continue
                        r = await _marks.marked_shot(_Page(pg), words, now, pattern)
                        if r:
                            out.append({'url': pg.url[:200], 'site': _host(pg.url), 'title': title[:90], **r})
                        await pg.close()
                    except Exception as e:   # noqa: BLE001 — the next page still gets its turn
                        print(f'[free browser] {url}: {str(e)[:90]}')
            finally:
                await b.close()
        return out
    try:
        return await asyncio.wait_for(run(), timeout_s)
    except Exception as e:   # noqa: BLE001
        print(f'[free browser] {str(e)[:120]}')
        return []


def _host(u):
    from urllib.parse import urlsplit
    h = urlsplit(str(u)).netloc.lower()
    return h[4:] if h.startswith('www.') else h
