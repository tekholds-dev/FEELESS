"""🧪 THE AI PLAYGROUND (owner, 2026-10-14: "a preview playground of things / imgs they can make"): a model writes ONE self-contained
HTML document (SVG, CSS, canvas, a little JS) — a card design, a chart theme idea, an animation, a mock-up — and the owner sees it live in
a locked frame. The frame is sandboxed (scripts only, no same-origin: no cookies, no HQ session, no site storage) and every document gets
a Content-Security-Policy that blocks ALL network (no fetch, no external image / font / script). Nothing here touches the agents or money;
a creation the owner likes goes to the build queue like any idea.
"""
from __future__ import annotations

import re
import time

MAX_HTML = 60_000
KEEP = 30
CSP = ("<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; "
       "script-src 'unsafe-inline'; font-src data:; media-src data: blob:\">")
ASK = ("PLAYGROUND mode. Make what the owner asks as ONE complete, self-contained HTML document and NOTHING else (no prose, no code fences): "
       "<!doctype html> … </html>. Inline <style> and <script> only; draw with SVG / CSS / canvas. No external URLs of any kind (no CDN, no "
       "fonts, no images by URL) — network is blocked. Dark background (#05100b), royal green #15d16a accent, JetBrains Mono / system mono, "
       "smooth 60fps animation with transform / opacity, sized to fill a 100% width × 100vh frame. Make it look like a senior motion designer "
       "built it for a degen trading terminal: bold, alive, clean.")


def extract(text):
    """The model's answer → one HTML document (fences dropped; a bare fragment is wrapped) or None."""
    t = re.sub(r'```(?:html)?', '', str(text or ''), flags=re.I).strip()
    m = re.search(r'<!doctype html.*?</html>|<html.*?</html>', t, re.I | re.S)
    if m:
        t = m.group(0)
    elif not re.search(r'<(svg|div|canvas|style|body)\b', t, re.I):
        return None
    else:
        t = f'<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#05100b">{t}</body></html>'
    return t[:MAX_HTML]


def lock(html):
    """The document with the network-blocking CSP as the first thing in <head> (whatever the model wrote)."""
    h = re.sub(r'<meta[^>]+http-equiv=["\']?content-security-policy[^>]*>', '', str(html or ''), flags=re.I)
    if re.search(r'<head[^>]*>', h, re.I):
        return re.sub(r'(<head[^>]*>)', lambda m: m.group(1) + CSP, h, count=1, flags=re.I)
    return CSP + h


def add(items, prompt, html, by, now=None):
    """File one creation (newest first, ≤ KEEP). → (items, item)"""
    it = {'id': f"p{int((now or time.time()) * 1000) % 10**10}", 'prompt': str(prompt or '')[:300], 'html': lock(html), 'by': str(by or '')[:40],
          'at': round(now or time.time(), 1)}
    return ([it] + [x for x in (items or []) if x.get('id') != it['id']])[:KEEP], it


def iterate_prompt(prompt, prev_html):
    """Change an earlier creation: the model gets its own last document + what to change."""
    return f"Change this document: {str(prompt)[:600]}\n\nThe current document:\n{str(prev_html or '')[:24_000]}"
