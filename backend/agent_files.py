"""☁ EACH AGENT'S OWN STORAGE (FC08, owner 2026-10-31: "any imgs I upload should go to the cloud the agents can put stuff in or use as storage
that they clean"). Files the owner drops in the workbench chat (+), kept per agent on the FEELESS server: images / GIFs only, 1 GB per agent,
auto-cleaned 7 days after the last use. An agent reads them by name (its task text lists them) and its live browser can upload one to another site
(`upload` action — e.g. a coin image on pump.fun). Links are unguessable ids; only the agent's owner can list, add or delete.
☁ ITS CLOUD STARTS WITH ITS FIRST REAL DEPOSIT (owner 2026-10-30): FEELESS gives it 1 GB from the first free pool FEELESS holds keys for —
Cloudflare R2 (10 GB free) → Backblaze B2 (10 GB free) → Filebase (5 GB free), all one S3 API, a folder per agent — else the FEELESS server.
Keys per pool in backend/.env: <R2|B2|FILEBASE>_S3_ENDPOINT, _KEY_ID, _SECRET, _BUCKET. No keys ⇒ the server pool, and the drawer says so."""
import base64
import re
import time
import os
import uuid
from pathlib import Path

QUOTA = 1024 ** 3                # 1 GB per agent
TTL = 7 * 86400                  # cleaned 7 days after it was last used
MAX_STILL = 15 * 1024 ** 2       # same caps as site uploads (2026-10-26): stills 15 MB, GIFs 40 MB
MAX_GIF = 40 * 1024 ** 2
KEEP = 40                        # files listed per agent at most
TYPES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif', 'video/mp4': 'mp4', 'video/webm': 'webm'}
MAGIC = {'png': (b'\x89PNG',), 'jpg': (b'\xff\xd8\xff',), 'gif': (b'GIF87a', b'GIF89a'), 'webp': (b'RIFF',), 'webm': (b'\x1aE\xdf\xa3',), 'mp4': (b'',)}
# ☁ the free pools FEELESS can hand an agent a folder in (prefix, label, free GB). Order = first choice.
POOLS = (('R2', 'Cloudflare R2', 10), ('B2', 'Backblaze B2', 10), ('FILEBASE', 'Filebase', 5))
SERVER = ('feeless', 'FEELESS server', None)
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


def pools(env=None):
    """The free pools FEELESS has keys for → [(prefix, label, free GB)]."""
    env = os.environ if env is None else env
    return [p for p in POOLS if all(str(env.get(f'{p[0]}_S3_{k}') or '').strip() for k in ('ENDPOINT', 'KEY_ID', 'SECRET', 'BUCKET'))]


def start_cloud(cat, all_cats, env=None, now=None):
    """☁ Its first real deposit starts its cloud: 1 GB in the first free pool with room (each pool's free GB ÷ 1 GB a folder), else the
    FEELESS server. Once per agent. → its cloud row (None if it already had one)."""
    if cat.get('cloud'):
        return None
    taken = {}
    for c in all_cats or []:
        k = (c.get('cloud') or {}).get('pool')
        if k:
            taken[k] = taken.get(k, 0) + 1
    pick = next((p for p in pools(env) if taken.get(p[0], 0) < p[2] * (1024 ** 3) // QUOTA), SERVER)
    cat['cloud'] = {'pool': pick[0], 'label': pick[1], 'quota': QUOTA, 'startedAt': round(now or time.time()), 'seen': False}
    return cat['cloud']


def _s3(pool, env=None):
    import boto3
    env = os.environ if env is None else env
    return boto3.client('s3', endpoint_url=env[f'{pool}_S3_ENDPOINT'], aws_access_key_id=env[f'{pool}_S3_KEY_ID'],
                        aws_secret_access_key=env[f'{pool}_S3_SECRET'], region_name=env.get(f'{pool}_S3_REGION') or 'auto'), env[f'{pool}_S3_BUCKET']


def _key(cat, f):
    return f"agents/{cat['id']}/{f['id']}.{f['ext']}"


def _remote(cat):
    pool = (cat.get('cloud') or {}).get('pool')
    return pool if pool and pool != SERVER[0] else None


def read(data_dir, cat, fid, env=None):
    """One file's bytes from wherever its cloud keeps them, or None."""
    f = find(cat, fid)
    if not f:
        return None
    if _remote(cat):
        cli, bucket = _s3(_remote(cat), env)
        return cli.get_object(Bucket=bucket, Key=_key(cat, f))['Body'].read()
    p = path_of(data_dir, cat, fid)
    return p.read_bytes() if p and p.exists() else None


def local_copy(data_dir, cat, fid, env=None):
    """A path its browser can upload from: the file itself on the server pool, a fresh temp copy from a remote pool."""
    if not _remote(cat):
        return path_of(data_dir, cat, fid)
    f, raw = find(cat, fid), read(data_dir, cat, fid, env)
    tmp = Path(data_dir) / 'agent_files' / '_tmp'
    tmp.mkdir(parents=True, exist_ok=True)
    out = tmp / f"{f['id']}.{f['ext']}"
    out.write_bytes(raw or b'')
    return out


def used(cat):
    return sum(int(f.get('size') or 0) for f in cat.get('files') or [])


def save(data_dir, cat, data_url, name='', now=None, env=None):
    """Store one file for this agent → its public row. Raises ValueError (bad file, quota)."""
    mime, raw, ext = decode(data_url)
    if not cat.get('cloud'):
        raise ValueError('Its cloud starts with its first real deposit — fund it first.')
    if used(cat) + len(raw) > QUOTA:
        raise ValueError('Its 1 GB cloud is full — delete a file first.')
    if len(cat.get('files') or []) >= KEEP:
        raise ValueError(f'It keeps {KEEP} files at most — delete one first.')
    fid, now = uuid.uuid4().hex, now or time.time()
    clean_name = re.sub(r'[^\w .()-]', '', str(name or ''))[:80].strip() or f'file.{ext}'
    row = {'id': fid, 'name': clean_name, 'mime': mime, 'ext': ext, 'size': len(raw), 'at': round(now), 'used': round(now)}
    if _remote(cat):
        cli, bucket = _s3(_remote(cat), env)
        cli.put_object(Bucket=bucket, Key=_key(cat, row), Body=raw, ContentType=mime)
    else:
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
    if _remote(cat):
        cli, bucket = _s3(_remote(cat), env)
        cli.delete_object(Bucket=bucket, Key=_key(cat, f))
    else:
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
    return {'files': files, 'used': used(cat), 'quota': QUOTA, 'ttlDays': TTL // 86400, 'cloud': cat.get('cloud')}


def task_note(rows):
    """What the agent's task text says about the attached files."""
    if not rows:
        return ''
    return ('\n\nFILES THE USER ATTACHED (in your storage — to put one on a website, use action "upload" with label = the file field and '
            'value = the file name): ' + '; '.join(f"{f['name']} ({f['mime']}, {f['size'] // 1024} KB)" for f in rows))
