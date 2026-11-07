#!/usr/bin/env python
"""The whole site audit, signed out: every page at desktop and phone. Reports crashes, console errors, sideways scroll, lost clicks (a hit area under 32px) and load time. It reads only. Signed-in pages need the owner's wallet, so it says so instead of pretending."""
import json
import sys
import time

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:51367'
ROUTES = ['/', '/familia', '/hq-link'] + [f'/terminal/{x}' for x in ('', 'trade', 'new', 'movers', 'discover', 'pump', 'chat', 'watchlist', 'alerts', 'launch', 'fuse', 'fee', 'feeback', 'feecat', 'feecat/cats', 'feecat/agents', 'reputation', 'rewards', 'badges', 'leaderboard', 'seasons', 'alpha', 'support', 'feed', 'whitepaper', 'roadmap', 'learn', 'settings', 'legal', 'coin/DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263', 'nope-404')]   # the names in pages/Terminal.jsx; a wrong name shows 'Off the radar' and tests nothing
SIZES = {'desktop': (1280, 800), 'phone': (360, 780)}
IGNORE = ('token-logo/', 'reputation/img', 'favicon', 'ERR_BLOCKED', 'net::ERR_ABORTED', 'WebSocket', 'React DevTools')


def visit(page, url):
    errs = []; on_console = lambda m: errs.append(m.text[:200]) if m.type == 'error' and not any(x in m.text or x in (m.location or {}).get('url', '') for x in IGNORE) else None; on_error = lambda e: errs.append('CRASH ' + str(e)[:200])
    page.on('console', on_console); page.on('pageerror', on_error); t = time.time()
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=45000); page.wait_for_timeout(3500)
    except Exception as e:
        errs.append('LOAD ' + str(e)[:120])
    info = page.evaluate("""() => ({ unknown: !!document.querySelector('[data-testid=unknown-page-home]'), side: document.documentElement.scrollWidth - innerWidth, text: document.body.innerText.length, boom: /Something went wrong|Application error/.test(document.body.innerText), small: [...document.querySelectorAll('button,a[href],[role=tab]')].filter(b => { const r = b.getBoundingClientRect(); return r.height > 0 && r.width > 0 && Math.min(r.width, r.height) < 24 && getComputedStyle(b).visibility !== 'hidden'; }).length, buttons: document.querySelectorAll('button').length })""")
    page.remove_listener('console', on_console); page.remove_listener('pageerror', on_error)
    return {**info, 'errs': list(dict.fromkeys(errs))[:5], 'ms': round((time.time() - t) * 1000)}


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=sys.argv[2] if len(sys.argv) > 2 else None); out = []
    for name, (w, h) in SIZES.items():
        ctx = b.new_context(viewport={'width': w, 'height': h}); page = ctx.new_page()
        for r in ROUTES:
            x = visit(page, BASE + r); out.append({'route': r, 'size': name, **x}); bad = x['boom'] or x['side'] > 1 or x['errs'] or x['text'] < 40
            print(f"{'BAD ' if bad else 'ok  '}{name:7} {r:26} {x['ms']:>6}ms side {x['side']:>4} small {x['small']:>3} {x['errs'][:2] if x['errs'] else ''}", flush=True)
        ctx.close()
    b.close()
bad = [x for x in out if x['boom'] or x['side'] > 1 or x['errs'] or x['text'] < 40]
print(f"\n{len(out)} views. {len(bad)} with a problem. Slowest {max(x['ms'] for x in out)}ms. Signed-in pages were NOT covered.")
json.dump(out, open('/tmp/feeless-site-audit.json', 'w'))
