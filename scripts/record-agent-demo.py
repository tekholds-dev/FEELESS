"""🎥 Record the General agent's two DEMO browser runs (owner, 2026-10-30: "do 2 different test recordings using the browser windows and put
them in the demo window browsers"). A real headless Chromium drives big crypto sites the way each mind would (owner: degen web3 /
billion-dollar crypto sites, not wiki): Mind A researches coins on CoinMarketCap, Mind B works the Jupiter desk. Sites behind a bot check
are skipped, never bypassed. Each step saves a frame + the URL, a caption and where the
cursor clicked (as % of the frame) into frontend/public/agent-demo/frames.json — AgentDemo.jsx plays them in its two browser windows.

Run:  .venv/bin/python scripts/record-agent-demo.py          (all runs)
      .venv/bin/python scripts/record-agent-demo.py trade    (only the trading demo: FEELESS chart + perps · the BTC narrative; needs the dev server)
"""
import glob
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / 'frontend' / 'public' / 'agent-demo'
W, H = 1440, 900   # HD (owner 2026-10-30: "the video covers the whole window, HD")


def center(page, sel):
    try:
        b = page.locator(sel).first.bounding_box(timeout=3000)
    except Exception:   # the box moved / re-rendered — the cursor just aims mid-frame
        b = None
    return [round((b['x'] + b['width'] / 2) / W * 100, 1), round((b['y'] + b['height'] / 2) / H * 100, 1)] if b else [50, 50]


def shot(page, run, frames, caption, cursor=None):
    name = f'{run}{len(frames) + 1}.jpg'
    page.screenshot(path=str(OUT / name), type='jpeg', quality=72, timeout=60000, animations='disabled')
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


class Blocked(Exception):
    pass


def go(page, url, wait=5000):
    """Open a page; a bot check (Cloudflare etc.) is skipped, never bypassed."""
    page.goto(url, timeout=45000, wait_until='domcontentloaded'); page.wait_for_timeout(wait)
    body = (page.content() or '')[:200000].lower()
    if '/sorry/' in page.url or 'unusual traffic' in body or 'verify you are human' in body or 'performing security verification' in body or 'just a moment' in page.title().lower():
        raise Blocked(url)
    for txt in ('Reject Additional Cookies', 'Reject all', 'Necessary only'):   # a cookie banner: the privacy-first choice, never "accept"
        try:
            page.get_by_role('button', name=txt).first.click(timeout=1200); page.wait_for_timeout(600); break
        except Exception:
            pass


def run_c(page):   # 🎯 TWO JOBS · job 1: find new + trending coins on CoinMarketCap
    f = []
    go(page, 'https://coinmarketcap.com/new/')
    shot(page, 'c', f, 'job 1 · opens the newest coins', [30, 30])
    page.mouse.wheel(0, 500); page.wait_for_timeout(1500)
    shot(page, 'c', f, 'reads their first-day volume', [45, 45])
    go(page, 'https://coinmarketcap.com/trending-cryptocurrencies/')
    shot(page, 'c', f, 'cross-checks what is trending', [35, 30])
    page.mouse.wheel(0, 500); page.wait_for_timeout(1500)
    shot(page, 'c', f, 'hands 3 coins to B', [40, 55])
    return f


def run_d(page):   # 🎯 TWO JOBS · job 2: the on-chain check on those coins (the official Solana Explorer)
    f = []
    go(page, 'https://explorer.solana.com/address/JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN', 8000)
    shot(page, 'd', f, 'job 2 · opens $JUP on-chain', [30, 25])
    page.mouse.wheel(0, 500); page.wait_for_timeout(1500)
    shot(page, 'd', f, 'reads supply + authorities', [45, 45])
    go(page, 'https://explorer.solana.com/address/DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263', 8000)
    shot(page, 'd', f, 'checks $BONK next', [30, 25])
    page.mouse.wheel(0, 500); page.wait_for_timeout(1500)
    shot(page, 'd', f, 'writes the on-chain report', [45, 50])
    return f


FEELESS = os.environ.get('FEELESS_URL', 'http://localhost:51367')   # the dev server: FEELESS charts only (owner 2026-10-31)


def click(page, sel, wait=2500):
    page.locator(sel).first.click(timeout=8000); page.wait_for_timeout(wait)
    return center(page, sel)


def run_t(page):   # 📈 BRAIN A · researches BTC on the FEELESS chart, then sets up a FEELESS perps ticket (no wallet: nothing is ever signed)
    f = []
    go(page, f'{FEELESS}/dev/perps', 9000)
    shot(page, 't', f, 'opens BTC on the FEELESS chart', click(page, '[data-testid="pd-m-BTC"]', 5000))
    shot(page, 't', f, '1H · the trend BTC is in', click(page, '[data-testid="pd-iv-1h"]', 5000))
    shot(page, 't', f, 'RSI · is BTC stretched?', click(page, '[data-testid="pd-ind-rsi"]', 4000))
    click(page, '[data-testid="pd-iv-15m"]', 3000)
    shot(page, 't', f, '15M vs VWAP · the entry zone', click(page, '[data-testid="pd-ind-vwap"]', 4000))
    shot(page, 't', f, "takes B's read: policy tailwind", None)
    shot(page, 't', f, 'FEELESS perps · BTC long', click(page, '[data-testid="pt-long"]', 2500))
    shot(page, 't', f, '10× · $25 inside your caps', (click(page, '[data-testid="pt-u-25"]', 1500), click(page, '[data-testid="pt-l-10"]', 2500))[1])
    shot(page, 't', f, 'TP +5% · SL −2% · ready for you', (click(page, '[data-testid="pt-tp-5"]', 1500), click(page, '[data-testid="pt-sl-2"]', 2500))[1])
    return f


NARRATIVE = [('https://www.coindesk.com/policy', 'BTC policy · Washington + the SEC'),
             ('https://www.theblock.co/category/policy', 'the bills + the votes'),
             ('https://decrypt.co/news', 'the BTC narrative today'),
             ('https://www.coindesk.com/markets', 'ETF flows + the Fed · what moves BTC')]


def run_u(page):   # 📰 BRAIN B · the narrative around BTC (politics, policy, ETF flows, the Fed) — fed to A; a bot-checked site is skipped
    f = []
    for url, cap in NARRATIVE:
        try:
            go(page, url, 6000)
        except Blocked as e:
            print('skipped (bot check):', e); continue
        except Exception as e:   # a slow site: skip it, keep the run
            print('skipped (slow):', url, str(e)[:80]); continue
        shot(page, 'u', f, cap, [40 + len(f) * 5, 38 + len(f) * 4])
        page.mouse.wheel(0, 700); page.wait_for_timeout(1500)
        shot(page, 'u', f, 'reads past the headline', [55, 55])
    if f:
        f[-1]['caption'] = 'hands A the read: policy + flows'
    return f


def trade_runs(ctx):
    for old in glob.glob(str(OUT / '[tu][0-9]*.jpg')):
        os.remove(old)
    out = {'t': run_t(ctx.new_page()), 'u': run_u(ctx.new_page())}
    out['chartCredit'] = 'Recorded live · FEELESS chart + perps · the BTC narrative'
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        # any cached headless shell works (the pip package may expect a newer build than the one installed)
        exe = os.environ.get('PW_CHROME') or next(iter(sorted(glob.glob(os.path.expanduser('~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell')), reverse=True)), None)
        b = p.chromium.launch(**({'executable_path': exe} if exe else {}))
        ctx = b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=1, color_scheme='dark')
        if TRADE_ONLY:   # `trade`: re-record only the trading demo, keep the general runs
            data = {k: v for k, v in json.loads((OUT / 'frames.json').read_text()).items() if k not in ('t', 'u', 'tSym', 'uSym', 'chartCredit')}
            data.update(trade_runs(ctx)); b.close(); (OUT / 'frames.json').write_text(json.dumps(data, indent=1))
            print({k: len(v) for k, v in data.items() if isinstance(v, list)}, 'frames'); return
        data = {'credit': 'Recorded live · CoinMarketCap · Jupiter', 'a': run_a(ctx.new_page()), 'b': run_b(ctx.new_page())}
        for key, fn, credit in (('c', run_c, None), ('d', run_d, None)):
            try:
                data[key] = fn(ctx.new_page())
            except Blocked as e:
                print('skipped (bot check):', e)
        if data.get('c') and data.get('d'):
            data['jobsCredit'] = 'Recorded live · CoinMarketCap · Solana Explorer'
        data.update(trade_runs(ctx))
        b.close()
    (OUT / 'frames.json').write_text(json.dumps(data, indent=1))
    print({k: len(v) for k, v in data.items() if isinstance(v, list)}, 'frames')


TRADE_ONLY = 'trade' in __import__('sys').argv[1:]

if __name__ == '__main__':
    main()
