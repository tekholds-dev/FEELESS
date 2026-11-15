"""🗂 AGENT ASSETS — the studios' shared shelf (owner 2026-11-15: "POC, POSTATIC, AND GAME FOLDERS'S STUDIOS NEED A DISCOVERY OR SOMETHING THEY
CAN DOWNLOAD OR EVEN UPLOAD ASSETS TO THEIR FILE").

Pure. Two halves:
  · MY FILES   what its owner uploaded or kept, per agent (images, video, audio, 3D models, fonts, game files), downloadable any time
  · DISCOVER   real free media from the source's own API: images and video from Wikimedia Commons, audio from Openverse (Freesound and
               others), 3D models from the CC0 library the 3D studio already uses. Every row carries its licence and its creator.
Keeping a found file downloads it once, server side, only from those hosts; nothing is hot-linked into a proof.
"""
import html
import re
import time
import uuid

MAX_FILE = 25_000_000
MAX_TOTAL = 250_000_000
MAX_ROWS = 300
KINDS = {
    'image': ('png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'),
    'video': ('mp4', 'webm', 'mov', 'ogv'),
    'audio': ('mp3', 'ogg', 'oga', 'wav', 'm4a', 'flac'),
    'model': ('glb', 'gltf', 'obj', 'fbx', 'ydd', 'ydr', 'yft', 'ytd', 'dff', 'txd'),
    'file': ('ttf', 'otf', 'woff2', 'zip', 'hdr', 'exr', 'lua', 'json', 'txt', 'md', 'pdf'),
}
MIME = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'webp': 'image/webp', 'gif': 'image/gif', 'svg': 'image/svg+xml',
        'mp4': 'video/mp4', 'webm': 'video/webm', 'mov': 'video/quicktime', 'ogv': 'video/ogg', 'mp3': 'audio/mpeg', 'ogg': 'audio/ogg', 'oga': 'audio/ogg',
        'wav': 'audio/wav', 'm4a': 'audio/mp4', 'flac': 'audio/flac', 'glb': 'model/gltf-binary', 'gltf': 'model/gltf+json', 'pdf': 'application/pdf',
        'json': 'application/json', 'txt': 'text/plain', 'md': 'text/markdown', 'zip': 'application/zip'}
KEEP_FROM = re.compile(r'^https://(upload\.wikimedia\.org|cdn\.freesound\.org|dl\.polyhaven\.org|raw\.githubusercontent\.com/(ToxSam|nasa)|'
                       r'huggingface\.co/datasets/allenai/objaverse/resolve/main|audio\.jamendo\.com|[\w-]+\.ccmixter\.org)/[\w./%()~,+-]+$')
COMMONS = 'https://commons.wikimedia.org/w/api.php'
OPENVERSE_AUDIO = 'https://api.openverse.org/v1/audio/'


def ext_of(name):
    n = str(name or '').rsplit('/', 1)[-1].split('?', 1)[0]
    return n.rsplit('.', 1)[-1].lower() if '.' in n else ''


def kind_of(name):
    e = ext_of(name)
    return next((k for k, v in KINDS.items() if e in v), None)


def clean_name(name):
    n = re.sub(r'[^\w.\- ()]', '', str(name or '').rsplit('/', 1)[-1]).strip()[:80]
    return n if n and kind_of(n) else ''


def add(rows, name, size, src='upload', lic='', by='', url='', now=None):
    """→ (rows, the new row). Raises ValueError on a bad or oversized file. Newest first."""
    n = clean_name(name)
    if not n:
        raise ValueError('That kind of file is not allowed here.')
    if size > MAX_FILE:
        raise ValueError(f'{n} is over 25 MB.')
    if sum(int(r.get('size') or 0) for r in rows or []) + size > MAX_TOTAL:
        raise ValueError('Your files are full (250 MB). Delete some first.')
    row = {'id': uuid.uuid4().hex[:12], 'name': n, 'kind': kind_of(n), 'ext': ext_of(n), 'size': int(size), 'src': src, 'lic': str(lic or '')[:40],
           'by': strip_html(by)[:80], 'from': str(url or '')[:300], 'at': round(now or time.time())}
    return [row] + list(rows or [])[:MAX_ROWS - 1], row


def drop(rows, aid):
    return [r for r in rows or [] if r.get('id') != aid]


def strip_html(s):
    return html.unescape(re.sub(r'<[^>]+>', '', str(s or ''))).strip()


def commons_url(q, video=False, n=24):
    ft = 'video' if video else 'bitmap'
    return (f"{COMMONS}?action=query&generator=search&gsrnamespace=6&gsrsearch={q} filetype:{ft}&gsrlimit={n}&prop=imageinfo"
            f"&iiprop=url|extmetadata|size|mime&iiurlwidth=360&format=json")


def commons_rows(j, video=False):
    """Commons' own answer → rows: a picture to show, the real file to keep, its licence and creator."""
    out = []
    for p in sorted(((j or {}).get('query') or {}).get('pages', {}).values(), key=lambda x: x.get('index', 0)):
        ii = (p.get('imageinfo') or [{}])[0]; m = ii.get('extmetadata') or {}
        url = str(ii.get('url') or '').split('?', 1)[0]   # Commons adds ?utm_… tracking to file addresses: the file is the same without it
        if not KEEP_FROM.match(url) or not kind_of(url):
            continue
        out.append({'id': f"cm-{p.get('pageid')}", 'name': strip_html(p.get('title', '')).replace('File:', '')[:80], 'kind': 'video' if video else 'image',
                    'thumb': ii.get('thumburl') or '', 'url': url, 'size': int(ii.get('size') or 0), 'w': ii.get('width'), 'h': ii.get('height'),
                    'lic': strip_html((m.get('LicenseShortName') or {}).get('value'))[:40], 'by': strip_html((m.get('Artist') or {}).get('value'))[:80],
                    'page': ii.get('descriptionurl') or '', 'src': 'Wikimedia Commons'})
    return out


def openverse_rows(j):
    out = []
    for r in (j or {}).get('results') or []:
        url = str(r.get('url') or '')
        if not KEEP_FROM.match(url):
            continue
        lic = f"{str(r.get('license') or '').upper()} {r.get('license_version') or ''}".strip()
        out.append({'id': f"ov-{r.get('id')}", 'name': str(r.get('title') or 'Sound')[:80], 'kind': 'audio', 'thumb': '', 'url': url,
                    'size': int(r.get('filesize') or 0), 'secs': round((r.get('duration') or 0) / 1000), 'lic': lic[:40], 'by': str(r.get('creator') or '')[:80],
                    'page': r.get('foreign_landing_url') or '', 'src': str(r.get('source') or 'Openverse').title()})
    return out


def model_rows(found, credit=''):
    return [{'id': r['id'], 'name': r['name'], 'kind': 'model', 'thumb': r.get('thumb') or '', 'url': '', 'lib': True, 'lic': 'CC0', 'by': credit, 'src': '3D library'} for r in found or []]


def view(rows):
    rows = rows or []
    return {'rows': rows, 'used': sum(int(r.get('size') or 0) for r in rows), 'max': MAX_TOTAL,
            'counts': {k: sum(1 for r in rows if r.get('kind') == k) for k in KINDS}}
