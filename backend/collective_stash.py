"""🧊 THE COLLECTIVE STASH (owner 2026-11-05): nothing gets lost. Every agent's proofs, won or lost, and every snapshot, compressed and sealed on our own disk, with a searchable index. It holds only the visitor-safe copy: no emails, phones, wallet trails or pages from signed-in accounts. The web of sources and kinds is counted from what is really in it."""
import hashlib
import io
import json
import shutil
import sqlite3
import time
import zlib
from urllib.parse import urlsplit

SEAL_ID = 'collective-stash'
CATEGORY = {'powFolders': 'Trades', 'popFolders': 'Perps', 'pobFolders': 'Picks', 'pocFolders': 'Content', 'psFolders': 'Code', 'shot': 'Snapshots'}
MAX_SOURCES = 60


def _db(root):
    root.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(root / 'index.db', timeout=30)
    c.execute('PRAGMA busy_timeout=30000')
    if c.execute('PRAGMA journal_mode').fetchone()[0].lower() != 'wal':   # only the first open switches it: two at once used to lock each other out
        try:
            c.execute('PRAGMA journal_mode=WAL')
        except sqlite3.OperationalError:
            pass
    c.execute('CREATE TABLE IF NOT EXISTS items (key TEXT PRIMARY KEY, at REAL, category TEXT, source TEXT, agent TEXT, outcome TEXT, title TEXT, sha TEXT, raw INTEGER, stored INTEGER)')
    c.execute('CREATE INDEX IF NOT EXISTS i_cat ON items(category)')
    c.execute('CREATE INDEX IF NOT EXISTS i_src ON items(source)')
    return c


def _seal(raw):
    import cat_keys
    return cat_keys.seal_bytes(raw, SEAL_ID)


def _unseal(raw):
    import cat_keys
    return cat_keys.unseal_bytes(raw, SEAL_ID)


def host_of(v):
    h = (urlsplit(str(v)).netloc or str(v)).lower()
    return h[4:] if h.startswith('www.') else h


def compress_image(raw):
    """A snapshot as a small WebP. Anything PIL cannot read stays as it is. Readable text survives at this size."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw)).convert('RGB')
        if im.width > 1280:
            im = im.resize((1280, int(im.height * 1280 / im.width)))
        out = io.BytesIO(); im.save(out, 'WEBP', quality=55, method=4)
        return out.getvalue() if out.tell() < len(raw) else raw
    except Exception:   # noqa: BLE001
        return raw


def _blob(root, packed):
    """One sealed file per distinct content: the same picture twice is stored once. → (sha, bytes on disk)"""
    sha = hashlib.sha256(packed).hexdigest()[:40]
    f = root / 'blobs' / sha[:2] / sha
    if f.exists():
        return sha, 0
    f.parent.mkdir(parents=True, exist_ok=True)
    sealed = _seal(packed); f.write_bytes(sealed)
    return sha, len(sealed)


def agent_tag(cat_id):
    return hashlib.sha256(f'stash:{cat_id}'.encode()).hexdigest()[:12]


def put(root, key, category, source, agent, outcome, title, raw, kind='json', at=None):
    """Keep one thing, once. → True when it was new. It only ever adds: nothing here deletes."""
    c = _db(root)
    try:
        if c.execute('SELECT 1 FROM items WHERE key=?', (key,)).fetchone():
            return False
        packed = compress_image(raw) if kind == 'image' else zlib.compress(raw, 9)
        sha, stored = _blob(root, packed)
        c.execute('INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?)', (key, at or time.time(), category, host_of(source)[:80], agent_tag(agent), outcome, str(title)[:160], sha, len(raw), stored))
        c.commit()
        return True
    finally:
        c.close()


def outcome_of(key, f):
    if key == 'powFolders':
        v = f.get('pnlPct')
    elif key == 'popFolders':
        v = f.get('roePct')
    else:
        v = {'right': 1, 'wrong': -1}.get(f.get('graded'))
    return 'none' if v is None else 'won' if float(v) > 0 else 'lost' if float(v) < 0 else 'flat'


def sources_of(f):
    """Which sites a proof read, from what it recorded."""
    out = set(f.get('sites') or [])
    for row in (f.get('usedBy') or {}).values():
        out |= set(row or [])
    for s in f.get('shots') or []:
        out.add(s.get('site'))
    for r in f.get('refs') or []:
        out.add(host_of(r.get('url')))
    return sorted(host_of(x) for x in out if x)[:20] or ['own read']


def ingest_cat(root, cat, public_folder, read_shot, keys=CATEGORY):
    """Every closed proof of one agent, won or lost, plus its snapshots. public_folder strips anything private first; read_shot returns a snapshot's plain bytes, or None for a sealed one from a signed-in site. → how many were new."""
    new = 0
    for key in ('powFolders', 'popFolders', 'pobFolders', 'pocFolders', 'psFolders'):
        for f in (cat or {}).get(key) or []:
            if f.get('status') not in ('closed', None) or not f.get('id'):
                continue
            safe = public_folder(f); srcs = sources_of(f); out = outcome_of(key, f)
            title = f.get('sym') or f.get('topic') or f.get('market') or f.get('name') or key
            at = float(f.get('soldAt') or f.get('closedAt') or f.get('at') or 0) or None
            if put(root, f"{key}:{f['id']}", keys[key], srcs[0], cat.get('id'), out, title, json.dumps(safe, default=str).encode(), 'json', at):
                new += 1
            for s in srcs[1:]:
                if put(root, f"{key}:{f['id']}:src:{s}", keys[key], s, cat.get('id'), out, title, s.encode(), 'json', at):
                    new += 1
            for sh in f.get('shots') or []:
                k = f"shot:{f['id']}:{sh.get('file')}"
                raw = read_shot(f, sh)
                if raw and put(root, k, keys['shot'], sh.get('site') or 'own read', cat.get('id'), out, f"{title} · {sh.get('site')}", raw, 'image', at):
                    new += 1
    return new


def stats(root):
    c = _db(root)
    try:
        n, raw, stored = c.execute('SELECT COUNT(*), COALESCE(SUM(raw),0), COALESCE(SUM(stored),0) FROM items').fetchone()
        by = dict(c.execute('SELECT category, COUNT(*) FROM items GROUP BY category').fetchall())
        out = dict(c.execute('SELECT outcome, COUNT(*) FROM items GROUP BY outcome').fetchall())
        agents = c.execute('SELECT COUNT(DISTINCT agent) FROM items').fetchone()[0]
        srcs = c.execute("SELECT COUNT(DISTINCT source) FROM items WHERE source != 'own read'").fetchone()[0]
        day = c.execute('SELECT COUNT(*) FROM items WHERE at > ?', (time.time() - 86400,)).fetchone()[0]
    finally:
        c.close()
    free = shutil.disk_usage(root).free
    return {'items': n, 'rawBytes': raw, 'storedBytes': stored, 'categories': by, 'outcomes': out, 'agents': agents, 'sources': srcs, 'lastDay': day, 'freeBytes': free, 'where': 'this machine'}


def web(root):
    """The web of what it really holds: the Stash → each category → each source, by count. Counts and site names only, safe to show anyone."""
    c = _db(root)
    try:
        rows = c.execute('SELECT category, source, COUNT(*), MAX(at) FROM items GROUP BY category, source ORDER BY COUNT(*) DESC LIMIT ?', (MAX_SOURCES * 4,)).fetchall()
    finally:
        c.close()
    cats = {}; srcs = {}; links = []
    for cat, src, n, at in rows:
        cats[cat] = cats.get(cat, 0) + n
        srcs[src] = {'n': srcs.get(src, {}).get('n', 0) + n, 'at': max(srcs.get(src, {}).get('at', 0), at or 0)}
        links.append({'from': cat, 'to': src, 'n': n})
    keep = sorted(srcs, key=lambda s: -srcs[s]['n'])[:MAX_SOURCES]
    return {'categories': [{'id': k, 'n': v} for k, v in sorted(cats.items(), key=lambda x: -x[1])], 'sources': [{'id': k, **srcs[k]} for k in keep], 'links': [x for x in links if x['to'] in keep]}


def read(root, key):
    """Open one kept item, for its owner's tools. Sealed content fails closed."""
    c = _db(root)
    try:
        row = c.execute('SELECT sha, category FROM items WHERE key=?', (key,)).fetchone()
    finally:
        c.close()
    if not row:
        return None
    packed = _unseal((root / 'blobs' / row[0][:2] / row[0]).read_bytes())
    return packed if row[1] == CATEGORY['shot'] else zlib.decompress(packed)
