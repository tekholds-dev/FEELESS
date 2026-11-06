#!/usr/bin/env python3
"""Makes the animated previews in Discover: a few frames of each kit's own public site, as a small animated WebP in frontend/public/kits. Run by hand when kits change: .venv/bin/python scripts/kit-previews.py"""
import asyncio
import io
import pathlib
import sys

from PIL import Image
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
import collective_kits as kits  # noqa: E402

OUT = ROOT / 'frontend' / 'public' / 'kits'
SIZE = (420, 262)


async def shoot(browser, kid, site):
    page = await browser.new_page(viewport={'width': 1200, 'height': 750}, color_scheme='dark')
    try:
        await page.goto(site, wait_until='domcontentloaded', timeout=30000); await page.wait_for_timeout(2500)
        frames = []
        top = await page.evaluate('document.documentElement.scrollHeight')
        for part in (0, 0.18, 0.36, 0.55):
            await page.evaluate(f'window.scrollTo(0, {int(top * part)})'); await page.wait_for_timeout(900)
            frames.append(Image.open(io.BytesIO(await page.screenshot(type='jpeg', quality=70))).convert('RGB').resize(SIZE))
        OUT.mkdir(parents=True, exist_ok=True)
        frames[0].save(OUT / f'{kid}.webp', save_all=True, append_images=frames[1:], duration=1300, loop=0, quality=52, method=4)
        print(kid, (OUT / f'{kid}.webp').stat().st_size // 1024, 'KB')
    except Exception as e:  # noqa: BLE001
        print(kid, 'FAILED', str(e)[:100])
    finally:
        await page.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome')   # the installed Chrome, in its own empty profile
        for kid, c in kits.CATALOG.items():
            await shoot(browser, kid, c['site'])
        await browser.close()


asyncio.run(main())
