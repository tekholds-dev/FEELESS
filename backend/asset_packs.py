"""🎁 REAL ASSETS (owner 2026-11-06: "they should start blank and grab real assets"). What agents build with: 521 models, 997 HDRI lights and 869 PBR textures from Poly Haven, all CC0. Its API is free for commercial use and asks two things, both done here: a User-Agent of our own and a visible credit.

Only addresses that Poly Haven's own API returned are ever kept, so a page can load only from that one host."""
import json
import re
import time
from pathlib import Path

API = 'https://api.polyhaven.com'
UA = 'FEELESS-agent-studio/1.0'
CREDIT = 'Assets from Poly Haven (CC0)'
HOST = 'https://dl.polyhaven.org/'
TYPES = {'model': 'models', 'hdri': 'hdris', 'texture': 'textures'}
INDEX = 'assets_index.dat'   # not *.json: the kit folder reads every .json as a kit
FILES = 'assets_files.dat'
MAX_AGE = 7 * 86400
SAFE_URL = re.compile(r'https://dl\.polyhaven\.org/[\w./%-]+')
MANY = re.compile(r'(?i)\b(two|three|four|five|six|seven|eight|nine|ten|dual|triple|double|multiple|several|many|rows? of|\d+)\b')
WANTS_3D = re.compile(r'(?i)\b(3d|three\.?js|webgl|r3f|react three|glb|gltf|hdri|photoreal|product shot|render(?:ed)? scene|3d landing|room with|whole room)\b')
STOP = {'a', 'an', 'the', 'of', 'and', 'with', 'for', 'on', 'in', 'to'}
MATERIAL_WORDS = {'marble', 'wood', 'wooden', 'velvet', 'metal', 'steel', 'concrete', 'stone', 'granite', 'brick', 'leather', 'fabric', 'glass', 'gold', 'chrome', 'plaster', 'tile', 'carpet'}
LOOK_SKIP = {'dark', 'light', 'polished', 'old', 'new', 'rough', 'smooth', 'soft', 'shiny', 'matte', 'black', 'white', 'grey', 'gray', 'red', 'blue', 'green'}


def wants_3d(text):
    return bool(WANTS_3D.search(str(text or '')))


def _load(root, name):
    try:
        d = json.loads((Path(root) / name).read_text())
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def _save(root, name, d):
    p = Path(root); p.mkdir(parents=True, exist_ok=True); tmp = p / f'{name}.tmp'; tmp.write_text(json.dumps(d)); tmp.replace(p / name)


async def refresh(http, root, now=None):
    """Keeps the names, tags and popularity of everything Poly Haven has. A failed read keeps the last one. → how many"""
    now = now or time.time(); old = _load(root, INDEX); rows = dict(old.get('rows') or {})
    for kind, t in TYPES.items():
        r = await http.get(f'{API}/assets', params={'t': t}, headers={'User-Agent': UA}, timeout=30)
        if r.status_code != 200:
            continue
        rows[kind] = [{'id': k, 'name': str(v.get('name') or k)[:60], 'tags': [str(x).lower() for x in (v.get('tags') or []) + (v.get('categories') or [])][:24], 'pop': int(v.get('download_count') or 0)} for k, v in r.json().items() if isinstance(v, dict)]
    if rows:
        _save(root, INDEX, {'at': round(now), 'rows': rows})
    return sum(len(v) for v in rows.values())


def _ready(root, now=None):
    d = _load(root, INDEX)
    return bool(d.get('rows')) and (now or time.time()) - float(d.get('at') or 0) < MAX_AGE


async def ensure(http, root):
    if not _ready(root):
        await refresh(http, root)


def _words(text):
    return [w for w in re.findall(r'[a-z0-9]+', str(text or '').lower()) if w not in STOP]


def _score(row, words):
    """Whole tag and name matches count most. An empty search shows what people use most."""
    tags = set(row['tags']); name = set(_words(row['name'])); hits = sum(3 if w in tags else 2 if w in name else 1 if any(w in t for t in tags) else 0 for w in words)
    return hits, row['pop']


def _stem(w):
    return w[:-1] if len(w) > 3 and w.endswith('s') and not w.endswith('ss') else w


def _head(query):
    """The thing itself, not what it is like: a "vintage film camera, brass and leather" is a camera, and "stack of old books" is books."""
    first = re.split(r',|\bwith\b|\bon\b|\bin\b|\bbeside\b', str(query or '').lower())[0]; words = [w for w in re.findall(r'[a-z0-9]+', first) if w not in STOP]
    return _stem(words[-1]) if words else ''


def best(root, query, kind):
    """The one asset for a description, only if it really is that thing. A chair must be a chair, and a near miss counts as not found, so nothing is ever swapped for something else."""
    head = _head(query); rows = (_load(root, INDEX).get('rows') or {}).get(kind) or []; words = _words(query); fits = []
    for r in rows:
        have = {_stem(t) for t in r['tags']} | {_stem(w) for w in _words(r['name'])} | {_stem(w) for t in r['tags'] for w in _words(t)} | {_stem(w) for w in re.findall(r'[a-z]+', re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', r['id']).lower().replace('_', ' '))}
        if head and head in have:
            fits.append(r)
    if not fits:
        return None
    return sorted(fits, key=lambda r: _score(r, words), reverse=True)[0]


SET_PIECES = (('cylinder', [3.2, 0.12, 3.2], [0, 0.06, 0], re.compile(r'(?i)\b(stage|slab|platform|pedestal|plinth|podium|base)\b')), ('box', [14, 7, 0.2], [0, 3.5, -4], re.compile(r'(?i)\b(backdrop|wall|curtain|background)\b')), ('box', [14, 0.1, 14], [0, 0.05, 0], re.compile(r'(?i)\b(floor|carpet|rug)\b')))


def search(root, query, kind='model', n=24):
    words = _words(query); rows = (_load(root, INDEX).get('rows') or {}).get(kind) or []; ranked = sorted(rows, key=lambda r: _score(r, words), reverse=True)
    if words:
        ranked = [r for r in ranked if _score(r, words)[0] > 0]
    return [{'id': r['id'], 'name': r['name'], 'kind': kind, 'tags': r['tags'][:5], 'thumb': f"https://cdn.polyhaven.com/asset_img/thumbs/{r['id']}.png?width=256&height=256"} for r in ranked[:n]]


def _url(v):
    v = str(v or '')
    return v if SAFE_URL.fullmatch(v) else ''


async def resolve(http, root, asset_id, kind, res='1k'):
    """The real files of one asset, from Poly Haven's own answer. Remembered, so it asks once. → {id, name, kind, url, files} or None"""
    aid = re.sub(r'[^\w-]', '', str(asset_id or ''))[:60]; key = f'{kind}:{aid}:{res}'; cache = _load(root, FILES)
    if key in cache:
        return cache[key]
    if kind not in TYPES or not aid:
        return None
    r = await http.get(f'{API}/files/{aid}', headers={'User-Agent': UA}, timeout=20)
    if r.status_code != 200:
        return None
    d = r.json(); name = aid.replace('_', ' '); out = None
    try:
        if kind == 'model':
            g = d['gltf'][res]['gltf']; files = {k.split('/')[-1]: _url(v.get('url')) for k, v in (g.get('include') or {}).items() if _url(v.get('url'))}
            out = {'id': aid, 'name': name, 'kind': kind, 'url': _url(g['url']), 'files': files}
        elif kind == 'hdri':
            out = {'id': aid, 'name': name, 'kind': kind, 'url': _url(d['hdri'][res]['hdr']['url']), 'files': {}}
        else:
            out = {'id': aid, 'name': name, 'kind': kind, 'url': _url(d['Diffuse'][res]['jpg']['url']), 'files': {'nor': _url(d['nor_gl'][res]['jpg']['url']), 'rough': _url(d['Rough'][res]['jpg']['url'])}}
    except (KeyError, TypeError, AttributeError):
        return None
    if not out or not out['url']:
        return None
    cache[key] = out; _save(root, FILES, cache)
    return out


def clean_asset(a):
    """An asset in a scene: only addresses on Poly Haven's host, anything else is dropped."""
    if not isinstance(a, dict) or not _url(a.get('url')):
        return None
    return {'id': re.sub(r'[^\w-]', '', str(a.get('id') or ''))[:60], 'name': ' '.join(str(a.get('name') or '').split())[:60], 'url': a['url'], 'files': {re.sub(r'[^\w.-]', '', str(k))[:80]: v for k, v in (a.get('files') if isinstance(a.get('files'), dict) else {}).items() if _url(v)}}


def compose(scene):
    """Gravity and staging by code, because a real model put a chair in mid air: real things rest on the stage or the ground, and a stage is sized to what stands on it."""
    rows = scene.get('objects') or []; things = [o for o in rows if o.get('asset')]; stage = next((o for o in rows if o.get('shape') == 'cylinder' and not o.get('asset') and o['scale'][0] >= 1 and o['scale'][1] <= 0.5), None)
    if stage and things:
        cx, cz = stage['pos'][0], stage['pos'][2]; reach = max((((o['pos'][0] - cx) ** 2 + (o['pos'][2] - cz) ** 2) ** 0.5 + (o.get('height') or 0.5) / 2 for o in things), default=1); size = round(max(1.4, reach * 2.3), 2); stage['scale'][0] = size; stage['scale'][2] = size
    top = stage['pos'][1] + stage['scale'][1] / 2 if stage else 0
    for o in things:
        if o.get('rest') is False:   # it stands on a desk or a shelf, where the builder put it
            continue
        on = stage and ((o['pos'][0] - stage['pos'][0]) ** 2 + (o['pos'][2] - stage['pos'][2]) ** 2) ** 0.5 <= stage['scale'][0] / 2
        o['pos'][1] = round(top if on else 0, 3)
    return scene


async def fill(http, root, scene, many=False):
    """Turns what a model asked for by name into real files: a chair it described becomes a real chair. What cannot be found is left out and named. → (scene, what was used, what was not found)"""
    used = []; missing = []
    for o in scene.get('objects') or []:
        if o.get('find') and not o.get('asset'):
            hit = None if _head(o['find']) in MATERIAL_WORDS else best(root, o['find'], 'model'); got = await resolve(http, root, hit['id'], 'model') if hit else None
            if not got and _head(o['find']) in MATERIAL_WORDS:   # "polished marble" is a surface, not a thing to fetch
                o['find'] = f"{o['find']} stage"
            if got:
                o.update(asset=got, shape='model', name=o.get('name') or got['name']); used.append(got['name'])
            else:
                piece = None if got else next((p for p in SET_PIECES if p[3].search(o['find'])), None)
                if piece:   # a stage or a wall is a shape with a real surface, not a thing to find
                    o.update(shape=piece[0], scale=piece[1], pos=[o['pos'][0], piece[2][1], piece[2][2] if piece[0] == 'box' and piece[2][2] else o['pos'][2]], look=o.get('look') or o['find'], height=0); o.pop('find', None)
                else:
                    missing.append(o['find'])
        if o.get('look') and not o.get('pbr'):
            hit = next((h for h in (best(root, w, 'texture') for w in reversed(_words(o['look'])) if not any(p[3].search(w) for p in SET_PIECES) and w not in LOOK_SKIP) if h), None); got = await resolve(http, root, hit['id'], 'texture') if hit else None
            if got:
                o['pbr'] = got; used.append(got['name'])
            else:
                missing.append(o['look'])
    scene['objects'] = [o for o in scene.get('objects') or [] if o.get('shape') != 'model' or o.get('asset')]
    if any(o.get('asset') for o in scene['objects']):   # with real models on the set, a plain shape is only a stage, a wall or something built on purpose: a model's stand-in cubes would hide the real thing
        scene['objects'] = [o for o in scene['objects'] if o.get('asset') or any(p[3].search(o.get('name') or '') or p[3].search(o.get('look') or '') for p in SET_PIECES) or o.get('glass') or o.get('metal', 0) > 0.5 or o.get('glow') or o.get('built') or o.get('user')]
    seen = set(); keep = []
    for o in scene['objects']:   # a model repeated the hero around the set: one of each, unless it was told how many by the owner adding more by hand
        key = (o.get('asset') or {}).get('url')
        if key and key in seen and not many:
            continue
        seen.add(key); keep.append(o)
    scene['objects'] = keep
    compose(scene)
    if scene.get('light_find') and not scene.get('hdri'):
        hit = next(iter(search(root, scene['light_find'], 'hdri', 1)), None); got = await resolve(http, root, hit['id'], 'hdri') if hit else None
        if got:
            scene['hdri'] = got; used.append(got['name'])
        else:
            missing.append(scene['light_find'])
    return scene, used, missing
