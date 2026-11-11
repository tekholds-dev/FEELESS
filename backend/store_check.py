"""📱 STORE CHECK (owner 2026-11-10: "users take the site or game to a potential mobile app store atmosphere to confirm all requirements and
checks before shipping"). One built page (a PoStatic folder's latest version) is checked the way Apple's App Review and Google Play would look
at it once it is wrapped as an app (a PWA / TWA / web-view shell): every row names the store rule it comes from, says pass / warn / fail, and
how to fix it. Two layers:
  · static  — pure reads of the HTML (always runs, no network): viewport, icon + manifest, HTTPS only, privacy policy when it collects data,
              account deletion when it has sign-up, real-money / gambling / crypto flags, placeholder text, accessibility, safe links, size.
  · device  — the page opened in headless Chromium at two phone sizes (360 × 780, 390 × 844): sideways scroll, console errors, tap targets
              under 44 px, load time. Skipped (and said so) when no Chromium is on the machine.
A FAIL is a likely rejection; a WARN needs a decision or a disclosure. Nothing here submits anything to a store."""
import asyncio
import re
import time

SEV = {'fail': 0, 'warn': 1, 'pass': 2, 'skip': 3}
PHONES = ((360, 780), (390, 844))
MAX_BYTES = 4_000_000


def _has(rx, html):
    return re.search(rx, html, re.I | re.S) is not None


def _row(rid, label, rule, ok, fix, warn=False, detail=''):
    return {'id': rid, 'label': label, 'rule': rule, 'state': 'pass' if ok else ('warn' if warn else 'fail'), 'fix': '' if ok else fix, 'detail': detail}


def static_checks(html):
    """→ [row] for one page's HTML. Pure."""
    h = str(html or '')
    low = h.lower()
    rows = []
    rows.append(_row('viewport', 'Fits a phone screen', 'Apple 4.0 Design · Play: Core app quality', _has(r'<meta[^>]+name=["\']viewport["\'][^>]+width=device-width', h),
                     'Add <meta name="viewport" content="width=device-width,initial-scale=1">.'))
    rows.append(_row('title', 'Has a name and a language', 'Apple 2.3.7 Accurate metadata', _has(r'<title>\s*[^<\s][^<]*</title>', h) and _has(r'<html[^>]+lang=', h),
                     'Give the page a <title> and <html lang="en">.', warn=True))
    icon = _has(r'<link[^>]+rel=["\'][^"\']*(apple-touch-icon|icon)[^"\']*["\']', h)
    rows.append(_row('icon', 'Has an app icon', 'Apple 2.3.8 Icons · Play: Store listing', icon, 'Add an app icon (<link rel="apple-touch-icon" href="icon-512.png">, 512 × 512 PNG).', warn=True))
    rows.append(_row('manifest', 'Has a web app manifest', 'Play: Trusted Web Activity / PWA install', _has(r'<link[^>]+rel=["\']manifest["\']', h),
                     'Add a manifest (name, icons 192 + 512, start_url, display: standalone) so it can be wrapped for Google Play.', warn=True))
    insecure = sorted(set(m for m in re.findall(r'(?:src|href|action)=["\'](http://[^"\']+)', h, re.I) if not m.startswith(('http://localhost', 'http://127.0.0.1'))))
    rows.append(_row('https', 'Loads nothing over plain http', 'Apple App Transport Security · Play: Cleartext traffic', not insecure,
                     'Load every file over https.', detail=', '.join(insecure[:3])))
    collects = _has(r'<input[^>]+type=["\'](email|tel|password)["\']', h) or _has(r'<input[^>]+name=["\'][^"\']*(email|phone|address|name)', h)
    privacy = _has(r'privacy', low)
    rows.append(_row('privacy', 'Privacy policy where it collects data', 'Apple 5.1.1(i) · Play: User Data policy', privacy or not collects,
                     'It asks for personal data: link a privacy policy on the page and in the store listing.', detail='collects personal data' if collects else ''))
    signup = _has(r'(sign ?up|create (an )?account|register)', low) and _has(r'type=["\']password["\']', h)
    rows.append(_row('delete', 'Account deletion when it has sign-up', 'Apple 5.1.1(v) · Play: Account deletion', not signup or _has(r'delete (my |your )?account', low),
                     'It lets people make an account: give them a way to delete it in the app.'))
    money = _has(r'\b(bet|wager|casino|slots?|jackpot|real money|cash out|parlay|odds)\b', low)
    rows.append(_row('gambling', 'Real-money games flagged', 'Apple 5.3 Gaming, gambling · Play: Real-money gambling', not money,
                     'It talks about betting or real money: real-money play needs a licence in each country and a 17+ / 18+ rating; keep it free-to-play or region-lock it.', warn=True))
    crypto = _has(r'\b(wallet|connect wallet|phantom|metamask|swap|token|solana|nft)\b', low)
    rows.append(_row('crypto', 'Crypto features flagged', 'Apple 3.1.5 Cryptocurrencies · Play: Financial services', not crypto,
                     'Crypto: no on-device mining; exchange or trading needs the right licence; NFTs bought in-app go through in-app purchase on iOS. Say which applies in the listing.', warn=True))
    miner = _has(r'(coinhive|cryptonight|webminer|coin-hive|minero\.cc)', low)
    rows.append(_row('miner', 'No crypto mining in the page', 'Apple 2.4.2 · Play: Malware', not miner, 'Remove the mining script.'))
    evals = len(re.findall(r'\beval\s*\(|new Function\s*\(', h))
    rows.append(_row('code', 'No downloaded or hidden code', 'Apple 2.5.2 Software requirements', evals == 0, 'Remove eval() / new Function(): an app may not run code it was not reviewed with.', warn=True,
                     detail=f'{evals} found' if evals else ''))
    filler = re.findall(r'(lorem ipsum|\bTODO\b|coming soon|placeholder text|example\.com)', h, re.I)
    rows.append(_row('complete', 'No placeholder content', 'Apple 2.1 App completeness · Play: Minimum functionality', not filler,
                     'Replace placeholder text before shipping.', detail=', '.join(sorted(set(x.lower() for x in filler))[:3])))
    imgs = re.findall(r'<img\b[^>]*>', h, re.I)
    no_alt = sum(1 for t in imgs if not re.search(r'\balt=', t, re.I))
    rows.append(_row('a11y', 'Pictures have words for screen readers', 'Apple: Accessibility · Play: Accessibility', no_alt == 0, 'Add alt text to every image.', warn=True,
                     detail=f'{no_alt} of {len(imgs)} images' if no_alt else ''))
    blank = [t for t in re.findall(r'<a\b[^>]*target=["\']_blank["\'][^>]*>', h, re.I) if 'noopener' not in t.lower()]
    rows.append(_row('links', 'Outside links open safely', 'Security best practice', not blank, 'Add rel="noopener" to links that open a new tab.', warn=True, detail=f'{len(blank)} links' if blank else ''))
    size = len(h.encode())
    rows.append(_row('size', 'Small enough to load fast on a phone', 'Play: Core app quality (startup)', size <= MAX_BYTES, 'Shrink the page: compress images, drop unused libraries.', warn=True,
                     detail=f'{size / 1e6:.1f} MB'))
    trackers = sorted(set(re.findall(r'(google-analytics|googletagmanager|facebook\.net|hotjar|mixpanel|segment\.com)', low)))
    rows.append(_row('tracking', 'Tracking is disclosed', 'Apple 5.1.2 App Tracking Transparency · Play: Data safety', not trackers,
                     'It loads trackers: ask permission on iOS (ATT) and list them in Play\'s Data safety form.', warn=True, detail=', '.join(trackers)))
    return rows


async def device_checks(html, chromium=None, timeout_s=40):
    """→ [row] from opening the page at two phone sizes. [] with one skip row when no browser is available."""
    path = chromium
    if path is None:
        try:
            import free_browser as _fb
            path = _fb.chromium_path()
        except Exception:   # noqa: BLE001
            path = None
    if not path:
        return [{'id': 'device', 'label': 'Phone test in a real browser', 'rule': 'Play: Core app quality', 'state': 'skip', 'fix': 'No Chromium on this machine, so the phone test did not run.', 'detail': ''}]

    async def run():
        from playwright.async_api import async_playwright
        out = {'overflow': [], 'errors': 0, 'small': 0, 'ms': 0}
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=path)
            try:
                for w, hgt in PHONES:
                    pg = await b.new_page(viewport={'width': w, 'height': hgt}, is_mobile=True, has_touch=True)
                    errs = []
                    pg.on('pageerror', lambda e: errs.append(str(e)))
                    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
                    t = time.time()
                    await pg.set_content(html, wait_until='load', timeout=20000)
                    out['ms'] = max(out['ms'], int((time.time() - t) * 1000))
                    await pg.wait_for_timeout(800)
                    sw = await pg.evaluate('document.documentElement.scrollWidth')
                    if sw > w + 2:
                        out['overflow'].append(f'{w}px wide → {sw}px')
                    out['small'] = max(out['small'], await pg.evaluate("""() => [...document.querySelectorAll('button,a,[role=button],input,select')].filter(e => {
                        const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.width < 44 || r.height < 44); }).length"""))
                    out['errors'] = max(out['errors'], len(errs))
                    await pg.close()
            finally:
                await b.close()
        return out
    try:
        r = await asyncio.wait_for(run(), timeout_s)
    except Exception as e:   # noqa: BLE001 — a page that will not open is itself the finding
        return [{'id': 'device', 'label': 'Opens on a phone', 'rule': 'Apple 2.1 App completeness', 'state': 'fail', 'fix': 'The page did not open in a phone browser.', 'detail': str(e)[:120]}]
    return [_row('overflow', 'No sideways scrolling on a phone', 'Apple 4.0 Design · Play: Core app quality', not r['overflow'], 'Something is wider than the screen: let it wrap or shrink at 360 px.', detail='; '.join(r['overflow'])),
            _row('errors', 'No errors while it runs', 'Apple 2.1 App completeness (crashes)', r['errors'] == 0, 'Fix the page errors shown in the browser console.', detail=f"{r['errors']} errors" if r['errors'] else ''),
            _row('taps', 'Buttons big enough to tap', 'Apple HIG 44 pt · Play: 48 dp touch targets', r['small'] == 0, 'Make every button and link at least 44 × 44 px.', warn=True, detail=f"{r['small']} too small" if r['small'] else ''),
            _row('speed', 'Opens fast', 'Play: Core app quality (startup)', r['ms'] <= 3000, 'It took over 3 s to open: lighten it.', warn=True, detail=f"{r['ms']} ms")]


def verdict(rows):
    """→ {'score', 'state', 'fails', 'warns', 'line'} over the rows that ran."""
    ran = [r for r in rows if r['state'] != 'skip']
    fails = sum(r['state'] == 'fail' for r in ran); warns = sum(r['state'] == 'warn' for r in ran)
    score = round(100 * sum({'pass': 1, 'warn': 0.5, 'fail': 0}[r['state']] for r in ran) / max(1, len(ran)))
    state = 'blocked' if fails else 'review' if warns else 'ready'
    line = {'blocked': f'{fails} thing{"s" if fails != 1 else ""} a store would likely reject', 'review': f'Ready once you decide {warns} flag{"s" if warns != 1 else ""}', 'ready': 'Ready to wrap and submit'}[state]
    return {'score': score, 'state': state, 'fails': fails, 'warns': warns, 'line': line}


async def check(html, device=True, chromium=None):
    rows = static_checks(html) + (await device_checks(html, chromium) if device else [])
    rows.sort(key=lambda r: SEV[r['state']])
    return {**verdict(rows), 'rows': rows, 'at': round(time.time())}
