"""☁ EACH AGENT'S OWN STORAGE (FC08, owner 2026-10-31: "any imgs I upload should go to the cloud the agents can put stuff in or use as storage
that they clean"). Files the owner drops in the workbench chat (+), kept per agent on the FEELESS server: images / GIFs only, 1 GB per agent,
auto-cleaned 7 days after the last use. An agent reads them by name (its task text lists them) and its live browser can upload one to another site
(`upload` action — e.g. a coin image on pump.fun). Links are unguessable ids; only the agent's owner can list, add or delete.
☁ These are only the chat's ATTACHMENTS (owner 2026-10-30: "FEELESS will not fund any storage"): 100 MB per agent, gone 24 h after the last
use — long enough for its browser to upload one. What it keeps lives in its OWNER's cloud (agent_cloud.py: their Google Drive / Dropbox)."""
import base64
import re
import time
import uuid
from pathlib import Path

QUOTA = 100 * 1024 ** 2          # 100 MB of attachments per agent
TTL = 86400                      # gone 24 h after it was last used
MAX_STILL = 15 * 1024 ** 2       # same caps as site uploads (2026-10-26): stills 15 MB, GIFs 40 MB
MAX_GIF = 40 * 1024 ** 2
KEEP = 40                        # files listed per agent at most
TYPES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif', 'video/mp4': 'mp4', 'video/webm': 'webm'}
MAGIC = {'png': (b'\x89PNG',), 'jpg': (b'\xff\xd8\xff',), 'gif': (b'GIF87a', b'GIF89a'), 'webp': (b'RIFF',), 'webm': (b'\x1aE\xdf\xa3',), 'mp4': (b'',)}
ID_RE = re.compile(r'^[0-9a-f]{32}$')


def _root(data_dir, cat_id):
    if not re.match(r'^[A-Za-z0-9_-]{1,64}$', str(cat_id or '')):
        raise ValueError('Not an agent id.')
    return Path(data_dir) / 'agent_files' / cat_id


def decode(data_url):
    """'data:image/png;base64,…' → (mime, bytes, ext). Refuses anything that is not a real PNG / JPEG / WebP / GIF under its cap."""
    m = re.match(r'^data:((?:image|video)/[a-z0-9+]+);base64,(.+)$', str(data_url or ''), re.S)
    if not m or m.group(1) not in TYPES:
        raise ValueError('Images and clips only: PNG, JPEG, WebP, GIF, MP4 or WebM.')
    mime, ext = m.group(1), TYPES[m.group(1)]
    try:
        raw = base64.b64decode(m.group(2), validate=False)
    except Exception:
        raise ValueError('That file could not be read.')
    if not raw.startswith(MAGIC[ext]) or (ext == 'webp' and raw[8:12] != b'WEBP') or (ext == 'mp4' and raw[4:8] != b'ftyp'):
        raise ValueError('That file is not the image it claims to be.')
    big = ext in ('gif', 'mp4', 'webm')
    if len(raw) > (MAX_GIF if big else MAX_STILL):
        raise ValueError(f"Too big: {'GIFs and clips' if big else 'images'} up to {(MAX_GIF if big else MAX_STILL) // 1024 ** 2} MB.")
    return mime, raw, ext


def read(data_dir, cat, fid, env=None):
    """One attachment's bytes, or None."""
    p = path_of(data_dir, cat, fid)
    return p.read_bytes() if p and p.exists() else None


def local_copy(data_dir, cat, fid, env=None):
    """The path its browser uploads from."""
    return path_of(data_dir, cat, fid)


def used(cat):
    return sum(int(f.get('size') or 0) for f in cat.get('files') or [])


def save(data_dir, cat, data_url, name='', now=None, env=None):
    """Store one file for this agent → its public row. Raises ValueError (bad file, quota)."""
    mime, raw, ext = decode(data_url)
    if used(cat) + len(raw) > QUOTA:
        raise ValueError('100 MB of attachments at most — remove one first (keep files in your own cloud).')
    if len(cat.get('files') or []) >= KEEP:
        raise ValueError(f'It keeps {KEEP} files at most — delete one first.')
    fid, now = uuid.uuid4().hex, now or time.time()
    clean_name = re.sub(r'[^\w .()-]', '', str(name or ''))[:80].strip() or f'file.{ext}'
    row = {'id': fid, 'name': clean_name, 'mime': mime, 'ext': ext, 'size': len(raw), 'at': round(now), 'used': round(now)}
    root = _root(data_dir, cat['id'])
    root.mkdir(parents=True, exist_ok=True)
    (root / f'{fid}.{ext}').write_bytes(raw)
    cat['files'] = list(cat.get('files') or []) + [row]
    return row


def find(cat, fid):
    return next((f for f in cat.get('files') or [] if f.get('id') == fid), None) if ID_RE.match(str(fid or '')) else None


def path_of(data_dir, cat, fid):
    f = find(cat, fid)
    return (_root(data_dir, cat['id']) / f"{f['id']}.{f['ext']}") if f else None


def delete(data_dir, cat, fid, env=None):
    f = find(cat, fid)
    if not f:
        return False
    path_of(data_dir, cat, fid).unlink(missing_ok=True)
    cat['files'] = [f for f in cat.get('files') or [] if f.get('id') != fid]
    return True


def touch(cat, ids, now=None):
    """The files a task uses stay 7 more days. → those rows (unknown ids dropped)."""
    rows = [f for f in (find(cat, i) for i in (ids or [])[:8]) if f]
    for f in rows:
        f['used'] = round(now or time.time())
    return rows


def clean(data_dir, store, now=None):
    """Every agent's files unused for 7 days are deleted (bytes + row). → how many."""
    now, n = now or time.time(), 0
    for cat in (store.get('cats') or {}).values():
        for f in list(cat.get('files') or []):
            if now - float(f.get('used') or f.get('at') or 0) > TTL:
                delete(data_dir, cat, f['id']); n += 1
    return n


def public(cat, base=''):
    """The owner's view: rows + links + usage."""
    files = [{**f, 'url': f"{base}/api/cats/{cat['id']}/files/{f['id']}.{f['ext']}", 'expires': f.get('used', f.get('at', 0)) + TTL} for f in cat.get('files') or []]
    return {'files': files, 'used': used(cat), 'quota': QUOTA, 'ttlHours': TTL // 3600, 'cloud': {k: v for k, v in (cat.get('cloudLink') or {}).items() if k in ('provider', 'label', 'at')} or None}


def task_note(rows):
    """What the agent's task text says about the attached files."""
    if not rows:
        return ''
    return ('\n\nFILES THE USER ATTACHED (in your storage — to put one on a website, use action "upload" with label = the file field and '
            'value = the file name): ' + '; '.join(f"{f['name']} ({f['mime']}, {f['size'] // 1024} KB)" for f in rows))
