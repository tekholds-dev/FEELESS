"""📜 THE UPDATES LOG (owner 2026-10-27: "site settings should show a log of updates for site, backend or mobile — users see active fixes
and what came from requests"). Pure: `git log` text in → public update rows out. Each commit = one row: when, NEW (a requested feature) or FIX,
which parts it touched (SITE = the web app, BACKEND = the services, MOBILE = phone / Duo / Safari work) and its items (the subject split on " · ").
Anything that reads like an internal detail (keys, secrets, the HQ, wallets, admin) is dropped before it leaves the server.
"""
import re

SEP_C, SEP_F = '\x1e', '\x1f'
FORMAT = f'{SEP_C}%h{SEP_F}%ad{SEP_F}%s'          # git log --format=… --name-only --date=short
_KIND = re.compile(r'^(feat|fix|perf|refactor|style|docs|test|chore|build|ci)(?:\(([^)]*)\))?!?:\s*', re.I)
_MOBILE_PATH = re.compile(r'(duo|phone|mobile|ios|safari|touch|clipboard|pwa|manifest)', re.I)
_MOBILE_WORD = re.compile(r'(📱|iphone|duo|mobile|phone|safari|ios\b|360\s?px|portrait|landscape)', re.I)
_PRIVATE = re.compile(r'(api[_ ]?key|secret|token|\.env|password|passphrase|\bhq\b|admin|staff|owner-only|cmd ctr|command center|private key|seed phrase|'
                      r'[1-9A-HJ-NP-Za-km-z]{32,44})', re.I)
SHOWN = ('feat', 'fix', 'perf', 'style')


def _items(body):
    """Split a subject on " · " only outside brackets — "(NEW · GERM · DESK)" stays one item."""
    out, cur, depth, i = [], '', 0, 0
    while i < len(body):
        c = body[i]
        depth += c in '([{'
        depth -= c in ')]}' and depth > 0
        if depth == 0 and body.startswith(' · ', i):
            out.append(cur); cur = ''; i += 3; continue
        cur += c; i += 1
    return [x.strip() for x in out + [cur] if x.strip()]


def parse(text, limit=60):
    """`git log --format=FORMAT --name-only --date=short` → [{sha, at, type: new|fix, parts: [site|backend|mobile], area, items: [...]}]."""
    rows = []
    for chunk in (text or '').split(SEP_C):
        head, _, files = chunk.partition('\n')
        bits = head.split(SEP_F)
        if len(bits) != 3:
            continue
        sha, at, subject = bits
        m = _KIND.match(subject)
        kind = (m.group(1).lower() if m else 'feat')
        if kind not in SHOWN:
            continue
        area = (m.group(2) or '').strip() if m else ''
        paths = [f.strip() for f in files.splitlines() if f.strip()]
        parts = []
        if any(p.startswith('frontend/') for p in paths):
            parts.append('site')
        if any(p.startswith('backend/') for p in paths):
            parts.append('backend')
        body = subject[m.end():] if m else subject
        if any(_MOBILE_PATH.search(p) for p in paths) or _MOBILE_WORD.search(body):
            parts.append('mobile')
        items = [i for i in _items(body) if not _PRIVATE.search(i)]
        if not items or not parts:
            continue
        rows.append({'sha': sha[:8], 'at': at, 'type': 'fix' if kind == 'fix' else 'new', 'parts': parts,
                     'area': '' if _PRIVATE.search(area) else area[:24], 'items': [i[:220] for i in items[:8]]})
        if len(rows) >= limit:
            break
    return rows


def counts(rows):
    """How many rows touch each part + how many are fixes vs new — the log's meters."""
    out = {'site': 0, 'backend': 0, 'mobile': 0, 'new': 0, 'fix': 0}
    for r in rows:
        for p in r['parts']:
            out[p] += 1
        out[r['type']] += 1
    return out
