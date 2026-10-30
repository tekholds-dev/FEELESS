"""🎥 Record the General agent's two DEMO browser runs (owner, 2026-10-30: "do 2 different test recordings using the browser windows and put
them in the demo window browsers"). A real headless Chromium drives big crypto sites the way each mind would (owner: degen web3 /
billion-dollar crypto sites, not wiki): Mind A researches coins on CoinMarketCap, Mind B works the Jupiter desk. Sites behind a bot check
are skipped, never bypassed. Each step saves a frame + the URL, a caption and where the
cursor clicked (as % of the frame) into frontend/public/agent-demo/frames.json — AgentDemo.jsx plays them in its two browser windows.

Run:  .venv/bin/python scripts/record-agent-demo.py
"""
import glob
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / 'frontend' / 'public' / 'agent-demo'
W, H = 960, 600


def center(page, sel):
    try:
        b = page.locator(sel).first.bounding_box(timeout=3000)
    except Exception:   # the box moved / re-rendered — the cursor just aims mid-frame
        b = None
    return [round((b['x'] + b['width'] / 2) / W * 100, 1), round((b['y'] + b['height'] / 2) / H * 100, 1)] if b else [50, 50]


def shot(page, run, frames, caption, cursor=None):
    name = f'{run}{len(frames) + 1}.jpg'
    page.screenshot(path=str(OUT / name), type='jpeg', quality=62, timeout=60000, animations='disabled')
    frames.append({'src': f'/agent-demo/{name}', 'url': page.url.replace('https://', ''), 'caption': caption, 'cursor': cursor or [50, 50]})


def run_a(page):   # 🧠 A · coin research on CoinMarketCap
    f = []
    page.goto('https://coinmarketcap.com/', timeout=45000, wait_until='domcontentloaded'); page.wait_for_timeout(4000)
    shot(page, 'a', f, 'opens CoinMarketCap', [50, 30])
    page.goto('https://coinmarketcap.com/currencies/solana/', timeout=45000, wait_until='domcontentloaded'); page.wait_for_timeout(4000)
    shot(page, 'a', f, 'opens $SOL', [22, 22])
    page.mouse.wheel(0, 500); page.wait_for_timeout(1200)
    shot(page, 'a', f, 'reads cap + volume', [24, 45])
    page.goto('https://coinmarketcap.com/currencies/jupiter-ag/', timeout=45000, wait_until='domcontentloaded'); page.wait_for_timeout(4000)
    shot(page, 'a', f, 'compares $JUP', [22, 22])
    return f


def run_b(page):   # 🧠 B · the Jupiter desk: spot, a token search, perps
    f = []
    page.goto('https://jup.ag/', timeout=45000, wait_until='domcontentloaded'); page.wait_for_timeout(4000)
    shot(page, 'b', f, 'opens Jupiter', [62, 64])
    search = 'input[placeholder*="Search" i], button:has-text("Search")'
    at = center(page, search)
    try:
        page.locator(search).first.click(timeout=4000); page.keyboard.type('JUP', delay=60); page.wait_for_timeout(2500)
    except Exception:
        pass
    shot(page, 'b', f, 'searches $JUP', at)
    page.goto('https://jup.ag/perps', timeout=45000, wait_until='domcontentloaded'); page.wait_for_timeout(5000)
    shot(page, 'b', f, 'reads SOL perps', [45, 45])
    page.mouse.wheel(0, 500); page.wait_for_timeout(1200)
    shot(page, 'b', f, 'checks funding + size', [55, 55])
    return f


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        # any cached headless shell works (the pip package may expect a newer build than the one installed)
        exe = os.environ.get('PW_CHROME') or next(iter(sorted(glob.glob(os.path.expanduser('~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell')), reverse=True)), None)
        b = p.chromium.launch(**({'executable_path': exe} if exe else {}))
        ctx = b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=1, color_scheme='dark')
        data = {'credit': 'Recorded live · CoinMarketCap · Jupiter', 'a': run_a(ctx.new_page()), 'b': run_b(ctx.new_page())}
        b.close()
    (OUT / 'frames.json').write_text(json.dumps(data, indent=1))
    print(len(data['a']), len(data['b']), 'frames')


if __name__ == '__main__':
    main()
