"""🧩 COL-26 THE PARTS RECORD, the capability foundry (owner + GPT 2026-11-09). Agents get stronger by working, like muscles: code an agent
wrote inside a proof that got PROVED becomes a reusable PART, and the next build of any kind is offered it. Parts nobody reuses go stale and
stop being offered.

A part is kept only if: its proof is PROVED, every license it inherits is carried (any GPL source blocks it), and a code check passes (it
parses, no outside script beyond the kit libraries, no eval). Reuse is a COL-3 event and is logged, never paid (a royalty would change THE
DEAL: the owner's call once real numbers exist). One SQLite file, its own; content is the part's own HTML, capped."""
import hashlib
import html as _html
import json
import re
import sqlite3
import time
from html.parser import HTMLParser

DB_NAME = 'parts.db'
MAX_PART = 12000          # characters of one part's code
MAX_PARTS_PER_PAGE = 6
STALE_S = 30 * 86400      # a part nobody reused in 30 days stops being offered (its record stays)
BLOCKING = ('GPL', 'AGPL', 'LGPL', 'SSPL')
ALLOWED_SCRIPT_HOSTS = ('cdn.jsdelivr.net', 'unpkg.com', 'cdnjs.cloudflare.com', 'esm.sh')   # where kit libraries load from
BLOCK_TAGS = ('header', 'nav', 'section', 'main', 'article', 'aside', 'footer', 'form')
WORD = re.compile(r'[a-z0-9]{3,}')


def _db(path):
    c = sqlite3.connect(str(path), timeout=30)
    c.execute('PRAGMA busy_timeout=30000')
    c.execute('CREATE TABLE IF NOT EXISTS parts (id TEXT PRIMARY KEY, cat TEXT, kind TEXT, proof TEXT, ws TEXT, title TEXT, tag TEXT, html TEXT, '
              'bytes INTEGER, licenses TEXT, kits TEXT, quality REAL, words TEXT, at REAL, used_at REAL, uses INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS uses (part TEXT, kind TEXT, ref TEXT, cat TEXT, at REAL, PRIMARY KEY (part, kind, ref))')
    return c


class _Blocks(HTMLParser):
    """The page's top-level building blocks: each header / nav / section / main / article / aside / footer / form, with its exact source span."""

    def __init__(self, src):
        super().__init__(convert_charrefs=True); self.src = src; self.depth = 0; self.open = None; self.out = []; self.lines = [0]
        for ln in src.splitlines(keepends=True):
            self.lines.append(self.lines[-1] + len(ln))

    def _pos(self):
        ln, col = self.getpos(); return self.lines[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            if self.open is None:
                self.open = (tag, self._pos(), dict(attrs)); self.depth = 1
            elif tag == self.open[0]:
                self.depth += 1

    def handle_endtag(self, tag):
        if self.open and tag == self.open[0]:
            self.depth -= 1
            if self.depth == 0:
                end = self.src.find('>', self._pos()) + 1
                self.out.append((self.open[0], self.open[2], self.src[self.open[1]:end])); self.open = None


def _top(src):
    p = _Blocks(src)
    try:
        p.feed(src); p.close()
    except Exception:   # noqa: BLE001: a page that will not parse gives no parts
        return []
    return p.out


def blocks(page, depth=0):
    """→ [(tag, attrs, html)] of the page's building blocks, in order. A main or article holding 2+ blocks is split into them (a whole page is
    not a part). Pure."""
    out = []
    for tag, attrs, code in _top(str(page or '')):
        if tag in ('main', 'article') and depth < 2:
            inner = code[code.find('>') + 1:code.rfind('</')]
            kids = blocks(inner, depth + 1)
            if len(kids) >= 2:
                out += kids; continue
        if 80 <= len(code) <= MAX_PART:
            out.append((tag, attrs, code))
    return out


def check(code):
    """The code check a part must pass. → '' when clean, else why. Pure."""
    s = str(code or '')
    if re.search(r'\beval\s*\(|new\s+Function\s*\(', s):
        return 'uses eval'
    for src in re.findall(r'<script[^>]+src=["\']([^"\']+)', s, re.I):
        host = re.sub(r'^https?://', '', src).split('/')[0].lower()
        if src.startswith('http') and not any(host == h or host.endswith('.' + h) for h in ALLOWED_SCRIPT_HOSTS):
            return f'loads a script from {host}'
    if re.search(r'on\w+\s*=\s*["\'][^"\']*(document\.cookie|localStorage|fetch\()', s, re.I):
        return 'an inline handler reaches cookies, storage or the network'
    return ''


def licenses_of(kits, catalog):
    """→ (licenses, blocked_by). Every kit's license is carried; a GPL-family one blocks the part. Pure."""
    lic = sorted({str((catalog.get(k) or {}).get('license') or 'unknown') for k in kits or []}) or ['FEELESS']
    bad = [x for x in lic if any(b in x.upper() for b in BLOCKING)]
    return lic, bad


def title_of(tag, attrs, code):
    m = re.search(r'<h[1-3][^>]*>(.*?)</h[1-3]>', code, re.I | re.S)
    t = re.sub(r'<[^>]+>', '', m.group(1)) if m else (attrs.get('aria-label') or attrs.get('id') or attrs.get('class') or tag)
    return _html.unescape(re.sub(r'\s+', ' ', str(t))).strip()[:60] or tag


def words_of(text):
    return sorted(set(WORD.findall(re.sub(r'<[^>]+>', ' ', str(text or '')).lower())))[:200]


def harvest(path, cat_id, proof, page, kits, catalog, quality=None, now=None):
    """A PROVED page → its parts, once. `proof` = {'kind', 'id', 'ws', 'state'}; anything not proved gives nothing.
    → {'kept': [ids], 'skipped': [(title, why)]}"""
    now = now or time.time(); kept, skipped = [], []
    if proof.get('state') != 'proved':
        return {'kept': [], 'skipped': [('page', 'its proof is not PROVED')]}
    lic, bad = licenses_of(kits, catalog)
    if bad:
        return {'kept': [], 'skipped': [('page', f'a source license blocks reuse: {", ".join(bad)}')]}
    c = _db(path)
    try:
        for tag, attrs, code in blocks(page)[:MAX_PARTS_PER_PAGE]:
            why = check(code); t = title_of(tag, attrs, code)
            if why:
                skipped.append((t, why)); continue
            pid = 'pt_' + hashlib.sha256(code.encode()).hexdigest()[:12]
            if c.execute('SELECT 1 FROM parts WHERE id=?', (pid,)).fetchone():
                continue
            c.execute('INSERT INTO parts (id, cat, kind, proof, ws, title, tag, html, bytes, licenses, kits, quality, words, at, used_at, uses) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)',
                      (pid, cat_id, proof.get('kind'), proof.get('id'), proof.get('ws'), t, tag, code, len(code), json.dumps(lic), json.dumps(sorted(kits or [])), quality, ' '.join(words_of(code + ' ' + t)), now, now))
            kept.append(pid)
        c.commit()
    finally:
        c.close()
    return {'kept': kept, 'skipped': skipped}


def _row(r):
    return {'id': r[0], 'cat': r[1], 'kind': r[2], 'proof': r[3], 'ws': r[4], 'title': r[5], 'tag': r[6], 'bytes': r[8], 'licenses': json.loads(r[9]),
            'kits': json.loads(r[10]), 'quality': r[11], 'at': r[13], 'usedAt': r[14], 'uses': r[15]}


def offer(path, ask, now=None, limit=3, kind=None):
    """The parts worth offering the next build: matched to the ask by words, fresh ones only (used or made in the last 30 days). Pure read.
    → [part rows with 'html' and 'score']"""
    now = now or time.time(); want = set(words_of(ask))
    if not want:
        return []
    c = _db(path)
    try:
        rows = c.execute('SELECT * FROM parts WHERE used_at >= ?', (now - STALE_S,)).fetchall()
    finally:
        c.close()
    scored = []
    for r in rows:
        hit = len(want & set((r[12] or '').split()))
        if hit:
            scored.append((hit + min(r[15], 5) * 0.5, r))
    out = []
    for sc, r in sorted(scored, key=lambda x: -x[0])[:limit]:
        out.append({**_row(r), 'html': r[7], 'score': round(sc, 1)})
    return out


def offer_line(parts):
    """The lines a build reads: each offered part, marked so a reuse can be seen in the page it makes. Pure."""
    if not parts:
        return ''
    body = '\n\n'.join(f'PART {p["id"]} ("{p["title"]}", from a PROVED {p["kind"]}, licenses: {", ".join(p["licenses"])}). If you reuse or adapt it, keep data-part="{p["id"]}" on its outer tag:\n{p["html"][:4000]}' for p in parts)
    return ('\n\nPROVEN PARTS from the Collective: blocks of pages that already worked. Reuse or adapt one ONLY if it fits this ask better than '
            'writing it fresh; keep its license notes.\n' + body + '\n')


def reused_in(page):
    """The part ids a finished page carries. Pure."""
    return sorted(set(re.findall(r'data-part=["\'](pt_[0-9a-f]{12})["\']', str(page or ''))))


def use(path, part_ids, kind, ref, cat_id, now=None):
    """Logs each reuse once per proof; a used part is fresh again. → the ids newly logged."""
    now = now or time.time(); new = []
    c = _db(path)
    try:
        for pid in part_ids or []:
            if not c.execute('SELECT 1 FROM parts WHERE id=?', (pid,)).fetchone():
                continue
            if c.execute('INSERT OR IGNORE INTO uses VALUES (?,?,?,?,?)', (pid, kind, str(ref), cat_id, now)).rowcount:
                c.execute('UPDATE parts SET uses = uses + 1, used_at = ? WHERE id = ?', (now, pid)); new.append(pid)
        c.commit()
    finally:
        c.close()
    return new


def family(path, now=None):
    """Every part with its family tree (which proofs reused it) and whether it is stale. → rows, most reused first."""
    now = now or time.time()
    c = _db(path)
    try:
        rows = [_row(r) for r in c.execute('SELECT * FROM parts ORDER BY uses DESC, at DESC')]
        kids = {}
        for part, kind, ref, cat, at in c.execute('SELECT part, kind, ref, cat, at FROM uses ORDER BY at'):
            kids.setdefault(part, []).append({'kind': kind, 'ref': ref, 'at': at})
    finally:
        c.close()
    for r in rows:
        r['reusedBy'] = kids.get(r['id'], []); r['stale'] = (now - (r['usedAt'] or 0)) > STALE_S
    return rows
