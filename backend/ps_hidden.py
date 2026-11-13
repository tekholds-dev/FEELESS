"""🕵 POSTATIC HIDDEN CHECKS (owner 2026-11-13, P1 of the proof-integrity plan GPT · Grok · Claude agreed on).
Code, not a model, tests every filed page against checks the builders are never shown (not in their brief, not in the rubric, never fed back
as a lesson), so a page cannot be written to please them. A builder can't talk code into a pass, and a judge that sat out (it built the page)
still leaves this independent signal. Pure: page HTML in, result out.

Why these: the real PoStatic reviews of 2026-11-13 all failed on the same things a machine can see for itself — sample numbers left in
("Sample numbers until the coin is live"), empty sources, unfinished scenes ("This scene needs WebGL")."""
import re

VERSION = 2   # v2 (COL-20 P2, 2026-11-13): every reused kit the page loads must be on today's tested pin (kit_fresh), and the review lists the kits checked
FAKE = re.compile(r'lorem ipsum|placeholder|\bTODO\b|\bTBD\b|sample (numbers|data)|dummy (data|text)|example\.com|your (text|title|name) here|coming soon', re.I)
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


def run(html, pins=None):
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
        ('no-fake-data', not FAKE.search(h)),                                    # nothing sample, placeholder or lorem left in
        ('finished', not UNFINISHED.search(text)),                               # no "needs WebGL" / "under construction"
        ('has-title', bool(re.search(r'<title>\s*\S', h, re.I))),
        ('has-heading', bool(re.search(r'<h1\b', h, re.I))),
        ('phone-ready', bool(re.search(r'<meta[^>]+name=["\']viewport', h, re.I))),
        ('images-load', all(s and s.group(1).strip() and not s.group(1).startswith('http://') for s in srcs)),   # every picture has a real, secure source
        ('links-go-somewhere', not hrefs or sum(1 for x in hrefs if x.strip() in ('', '#')) <= len(hrefs) // 2),
        ('no-insecure-content', not re.search(r'(src|href)\s*=\s*["\']http://', h, re.I)),
        ('has-words', len(text) >= 120),                                         # a page says something, not a shell
    ]
    kits = kits_used(h, pins)
    if kits:
        checks.append(('kits-current', all(k['ok'] for k in kits)))             # P2: no stale copy of a kit the stash already moved past
    passed = sum(1 for _i, ok in checks if ok)
    return {'v': VERSION, 'passed': passed, 'total': len(checks), 'pct': round(100 * passed / len(checks)),
            'checks': [{'id': i, 'pass': bool(ok)} for i, ok in checks], 'failed': [i for i, ok in checks if not ok], 'kits': kits}
