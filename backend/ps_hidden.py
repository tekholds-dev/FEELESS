"""🕵 POSTATIC HIDDEN CHECKS (owner 2026-11-13, P1 of the proof-integrity plan GPT · Grok · Claude agreed on).
Code, not a model, tests every filed page against checks the builders are never shown (not in their brief, not in the rubric, never fed back
as a lesson), so a page cannot be written to please them. A builder can't talk code into a pass, and a judge that sat out (it built the page)
still leaves this independent signal. Pure: page HTML in, result out.

Why these: the real PoStatic reviews of 2026-11-13 all failed on the same things a machine can see for itself — sample numbers left in
("Sample numbers until the coin is live"), empty sources, unfinished scenes ("This scene needs WebGL")."""
import re

VERSION = 3   # v2 (COL-20 P2, 2026-11-13): every reused kit the page loads must be on today's tested pin (kit_fresh), and the review lists the kits checked
#                v3 (Slice 3, 2026-11-18): links inside the page go somewhere real, more placeholder text, and a real phone in a headless browser:
#                it loads with no script error, fits a 390 px screen, no two blocks of words sit on top of each other, outside links answer
FAKE = re.compile(r'lorem ipsum|placeholder|\bTODO\b|\bTBD\b|sample (numbers|data)|dummy (data|text)|example\.(com|org)|your (text|title|name|company|email) here|coming soon'
                  r'|\[(?:your|insert|add|company|name|link|image)[^\]]{0,30}\]|\{\{\s*\w+\s*\}\}|\bjohn doe\b|\bjane doe\b|acme (inc|corp)|123 main st|\bxxx+\b|\(555\)|\.invalid\b', re.I)
UNFINISHED = re.compile(r'needs webgl|not implemented|under construction|work in progress|\bWIP\b', re.I)


def _text(h):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.I | re.S))).strip()


def _ver(v):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r'[.\-]', str(v))[:3])


def kits_used(html, pins):
    """🧰 P2: the reused kits this page loads from a CDN, each against today's tested pin. pins = {npm package: (version, 'major' | 'exact')}
    from kit_fresh. A 'major' pin floats inside its major, so the page passes on the same major or newer; an 'exact' pin needs that version
    or newer. → [{'pkg', 'used', 'pin', 'ok'}]. Pure."""
    out, seen = [], set()
    for pkg, (pin, mode) in (pins or {}).items():
        if not pin:
            continue
        for used in re.findall(r'/' + re.escape(pkg) + r'@([0-9][0-9A-Za-z.\-]*)(?=[/"\'?#])', str(html or '')):
            if (pkg, used) in seen:
                continue
            seen.add((pkg, used))
            ok = _ver(used)[0] >= _ver(pin)[0] if mode == 'major' else _ver(used) >= _ver(pin)
            out.append({'pkg': pkg, 'used': used, 'pin': pin, 'ok': bool(ok)})
    return out


def _ids(h):
    return set(re.findall(r'\bid\s*=\s*["\']([^"\']+)', h))


def dead_anchors(h):
    """In-page links that point at nothing: #name with no element of that id, or javascript: links. → [href]. Pure."""
    ids = _ids(h); out = []
    for x in re.findall(r'<a\b[^>]*\bhref\s*=\s*["\']([^"\']*)', h, re.I):
        x = x.strip()
        if (x.startswith('#') and len(x) > 1 and x[1:] not in ids) or x.lower().startswith('javascript:'):
            out.append(x[:60])
    return out


def outside_links(h, n=10):
    """The page's outside links worth checking (http/https, one per address). → [url]. Pure."""
    return list(dict.fromkeys(x.strip() for x in re.findall(r'<a\b[^>]*\bhref\s*=\s*["\'](https?://[^"\']+)', str(h or ''), re.I)))[:n]


def run(html, pins=None, seen=None):
    """→ {'v', 'passed', 'total', 'pct', 'checks': [{id, pass}], 'failed': [ids], 'kits': [...]} or None when there is no page. Pure.
    pins (optional) adds 'kits-current' when the page loads any tracked kit: an old copy of a library we already moved off fails it."""
    h = re.sub(r'<div id="none">.*?</div>', ' ', str(html or ''), flags=re.S)   # the hidden no-WebGL fallback (display:none) is not page text
    if len(h) < 40:
        return None
    text = _text(h)
    imgs = re.findall(r'<img\b[^>]*>', h, re.I)
    srcs = [re.search(r'\bsrc\s*=\s*["\']([^"\']*)', i, re.I) for i in imgs]
    hrefs = re.findall(r'<a\b[^>]*\bhref\s*=\s*["\']([^"\']*)', h, re.I)
    checks = [
        ('no-fake-data', not FAKE.search(re.sub(r'(?i)\bplaceholder\s*=\s*("[^"]*"|\'[^\']*\')', '', h))),   # nothing sample or lorem left in (a form field's hint is not fake data)
        ('finished', not UNFINISHED.search(text)),                               # no "needs WebGL" / "under construction"
        ('has-title', bool(re.search(r'<title>\s*\S', h, re.I))),
        ('has-heading', bool(re.search(r'<h1\b', h, re.I))),
        ('phone-ready', bool(re.search(r'<meta[^>]+name=["\']viewport', h, re.I))),
        ('images-load', all(s and s.group(1).strip() and not s.group(1).startswith('http://') for s in srcs)),   # every picture has a real, secure source
        ('links-go-somewhere', not hrefs or sum(1 for x in hrefs if x.strip() in ('', '#')) <= len(hrefs) // 2),
        ('no-dead-anchors', not dead_anchors(h)),                                # v3: every #link lands on something in the page
        ('no-insecure-content', not re.search(r'(src|href)\s*=\s*["\']http://', h, re.I)),
        ('has-words', len(text) >= 120),                                         # a page says something, not a shell
    ]
    kits = kits_used(h, pins)
    if kits:
        checks.append(('kits-current', all(k['ok'] for k in kits)))             # P2: no stale copy of a kit the stash already moved past
    sn = seen if isinstance(seen, dict) and seen.get('ran') else None
    if sn:   # v3: what a real phone saw (browser()); only when it really ran, so a page is never failed by a browser that was not there
        checks += [('phone-load', bool(sn.get('loads'))), ('fits-phone', bool(sn.get('fits'))), ('no-overlap', not sn.get('overlaps')),
                   ('links-alive', not sn.get('deadLinks'))]
    passed = sum(1 for _i, ok in checks if ok)
    return {'v': VERSION, 'passed': passed, 'total': len(checks), 'pct': round(100 * passed / len(checks)),
            'checks': [{'id': i, 'pass': bool(ok)} for i, ok in checks], 'failed': [i for i, ok in checks if not ok], 'kits': kits,
            **({'seen': sn} if sn else {}), 'deadAnchors': dead_anchors(h)[:6]}


# ── 📱 v3: the page on a real phone, in headless Chromium (the builders never see this, and nothing here is ever fed back to them) ──
PHONE = {'width': 390, 'height': 844}
_LOOK = r"""() => {
  const sel = 'h1,h2,h3,h4,h5,p,li,button,a,label,input,select,textarea,td,th,figcaption,blockquote,dt,dd,small,strong';
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 4 && r.height > 4 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05 && ((e.innerText || e.value || '').trim().length > 0); };
  let els = [...document.querySelectorAll(sel)].filter(vis).slice(0, 500);
  els = els.filter(e => !els.some(o => o !== e && e.contains(o)));
  const box = e => { const r = e.getBoundingClientRect(); return [r.left, r.top + scrollY, r.right, r.bottom + scrollY]; };
  const bs = els.map(box), out = [];
  for (let i = 0; i < els.length && out.length < 8; i++) for (let j = i + 1; j < els.length && out.length < 8; j++) {
    const a = bs[i], b = bs[j], w = Math.min(a[2], b[2]) - Math.max(a[0], b[0]), h = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
    if (w <= 2 || h <= 2) continue;
    const small = Math.min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]));
    if (w * h / small > 0.35) out.push([els[i].tagName.toLowerCase() + ': ' + (els[i].innerText || '').trim().slice(0, 30), els[j].tagName.toLowerCase() + ': ' + (els[j].innerText || '').trim().slice(0, 30)]);
  }
  const words = (document.body && document.body.innerText || '').trim().length;
  return {overlaps: out, scrollW: document.documentElement.scrollWidth, innerW: innerWidth, words};
}"""


async def browser(html, chromium=None, http=None, settle_ms=2500, timeout_ms=10000):
    """📱 Opens the page as a phone (390 x 844) and as a desktop, the way a visitor would: does it load with no script error, fit the phone
    with no sideways scroll, keep every block of words clear of the others; then asks each outside link once. → {ran, loads, fits, overlaps,
    errors, deadLinks, ms}. A browser that cannot start → {ran: False, why}."""
    import time
    t0 = time.time()
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {'ran': False, 'why': 'no headless browser here'}
    errs, out = [], {'ran': True}
    try:
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=chromium) if chromium else await pw.chromium.launch()
            try:
                seen = []
                for name, vp, mobile in (('phone', PHONE, True), ('desktop', {'width': 1280, 'height': 800}, False)):
                    ctx = await b.new_context(viewport=vp, is_mobile=mobile, has_touch=mobile, device_scale_factor=2 if mobile else 1)
                    pg = await ctx.new_page(); mine = []
                    pg.on('pageerror', lambda e, m=mine: m.append(str(e)[:140]))
                    try:
                        await pg.set_content(str(html or ''), wait_until='load', timeout=timeout_ms); ok = True
                    except Exception as e:   # noqa: BLE001: it did not load in time
                        ok = False; mine.append(f'did not load in {timeout_ms // 1000} s ({type(e).__name__})')
                    await pg.wait_for_timeout(settle_ms)
                    try:
                        got = await pg.evaluate(_LOOK)
                    except Exception as e:   # noqa: BLE001
                        got = {'overlaps': [], 'scrollW': 0, 'innerW': 1, 'words': 0}; mine.append(f'could not be read ({type(e).__name__})')
                    seen.append((name, ok, got, mine)); errs += [f'{name}: {m}' for m in mine]
                    await ctx.close()
            finally:
                await b.close()
    except Exception as e:   # noqa: BLE001: no browser on this machine / it crashed: say so, never fail the page for it
        return {'ran': False, 'why': f'{type(e).__name__}: {str(e)[:120]}'}
    phone = seen[0]; desk = seen[1]
    out['loads'] = bool(phone[1] and not phone[3] and phone[2].get('words', 0) >= 20)
    out['fits'] = phone[2].get('scrollW', 0) <= PHONE['width'] + 2   # never innerWidth: a phone widens it to fit a page that is too wide
    out['overlaps'] = [{'on': n, 'a': a, 'b': b_} for n, _ok, g, _m in (phone, desk) for a, b_ in (g.get('overlaps') or [])][:8]
    out['errors'] = errs[:6]; out['phoneWidth'] = phone[2].get('scrollW')
    out['deadLinks'] = await dead_links(outside_links(html), http) if http is not None else []
    out['ms'] = round((time.time() - t0) * 1000)
    return out


async def dead_links(urls, http):
    """Each outside link asked once. Dead = it does not resolve, or answers 404 / 410 / 5xx. A site that blocks robots (401, 403, 405, 429)
    is not called dead. → [{url, why}]"""
    out = []
    for u in urls or []:
        try:
            r = await http.head(u, follow_redirects=True, timeout=6)
            if r.status_code in (405, 403, 501):
                r = await http.get(u, follow_redirects=True, timeout=6)
            if r.status_code in (404, 410) or r.status_code >= 500:
                out.append({'url': u[:120], 'why': str(r.status_code)})
        except Exception as e:   # noqa: BLE001: no answer at all
            out.append({'url': u[:120], 'why': type(e).__name__})
    return out
