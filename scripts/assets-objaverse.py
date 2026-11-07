#!/usr/bin/env python3
"""Builds the big model index from Objaverse's public metadata: every CC0 object, plus CC-BY objects people liked, under a size a browser can load.
Names, tags and addresses only: a model is fetched by the page that uses it, and a CC-BY model's creator is credited on that page.
No NC or SA licence is ever taken, and nothing age restricted. Run: .venv/bin/python scripts/assets-objaverse.py [likes] [out]"""
import concurrent.futures as cf
import gzip
import json
import re
import sys
import time
from pathlib import Path

import httpx

BASE = 'https://huggingface.co/datasets/allenai/objaverse/resolve/main'
HEAD = {'User-Agent': 'FEELESS-assets/1.0'}
MAX_FACES = 80000
MIN_LIKES = int(sys.argv[1]) if len(sys.argv) > 1 else 15
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / 'backend/data/kits/assets_more.dat'
SKIP = re.compile(r'(?i)\b(nsfw|nude|naked|sex|porn|hentai|gore|nazi|swastika|star ?wars|pokemon|pikachu|mario|marvel|disney|batman|spider-?man|harry potter|naruto|gundam|minecraft|fortnite|lego|ferrari|lamborghini|porsche|bmw|mercedes|tesla|nike|adidas|coca)\b')


def keep(uid, v, paths):
    lic = str(v.get('license')); faces = v.get('faceCount') or 0; likes = v.get('likeCount') or 0; name = re.sub(r'[_-]+', ' ', str(v.get('name') or '')).strip(); tags = [str(t.get('name')).lower() for t in v.get('tags') or [] if isinstance(t, dict)][:16]
    cats = [str(c.get('name')).lower() for c in v.get('categories') or [] if isinstance(c, dict)]
    if lic not in ('cc0', 'by') or v.get('isAgeRestricted') or not v.get('isDownloadable') or uid not in paths or not name or not 100 < faces <= MAX_FACES or SKIP.search(f"{name} {' '.join(tags)}"):
        return None
    if lic == 'by' and likes < MIN_LIKES:
        return None
    words = {w for w in re.findall(r'[a-z0-9]+', name.lower()) if len(w) > 2}
    return {'id': 'ox-' + uid[:32], 'name': name[:60], 'tags': list({*tags, *cats, *words})[:24], 'pop': int(likes), 'url': f'{BASE}/{paths[uid]}', 'lic': lic, 'by': str((v.get('user') or {}).get('displayName') or '')[:40], 'faces': faces}


def shard(c, name, paths):
    for tries in range(3):
        try:
            r = c.get(f'{BASE}/metadata/{name}'); r.raise_for_status()
            return [x for x in (keep(u, v, paths) for u, v in json.loads(gzip.decompress(r.content)).items()) if x]
        except Exception as e:  # noqa: BLE001 — one shard never stops the rest, and a bad read tries again
            print('retry', name, str(e)[:60], flush=True); time.sleep(5 * (tries + 1))
    return []


def main():
    c = httpx.Client(follow_redirects=True, timeout=180, headers=HEAD)
    paths = json.loads(gzip.decompress(c.get(f'{BASE}/object-paths.json.gz').content))
    names = [x['path'].split('/')[-1] for x in c.get('https://huggingface.co/api/datasets/allenai/objaverse/tree/main/metadata').json()]; rows = []
    with cf.ThreadPoolExecutor(4) as pool:
        for i, got in enumerate(pool.map(lambda n: shard(c, n, paths), names)):
            rows += got
            if i % 20 == 0:
                print(i, len(names), len(rows), flush=True)
    rows.sort(key=lambda r: (-(r['lic'] == 'cc0'), -r['pop']))
    OUT.parent.mkdir(parents=True, exist_ok=True); tmp = OUT.with_suffix('.tmp'); tmp.write_text(json.dumps({'at': round(time.time()), 'rows': rows})); tmp.replace(OUT)
    print('done', len(rows), 'cc0', sum(r['lic'] == 'cc0' for r in rows), OUT.stat().st_size // 1024, 'KB', flush=True)


if __name__ == '__main__':
    main()
