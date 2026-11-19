"""📮 Slice 5 (owner 2026-11-18: "grab 3 third party sites that can post to x, tiktok, youtube, etc after signed in to them all").
A PoC posts ONLY after its owner approves, through ONE of three posting services he signed his own accounts into. Each holds the platform
logins by the platforms' official OAuth; FEELESS keeps only his service key, sealed in the agent's API drawer (cat_keys), never in git or logs.
Each also reads each post's views and engagement back, which is how a PoC is graded on real reach (poc_studio.grade).

  · Upload-Post  https://upload-post.com   video, photos and text/threads; per-post analytics by request id   (checked live 2026-11-18)
  · Zernio       https://zernio.com        one post to many networks; per-post analytics by post id           (checked live 2026-11-18)
  · Ayrshare     https://ayrshare.com      one post to many networks; per-post analytics by post id           (checked live 2026-11-18)

Calls take an httpx.AsyncClient (faked in tests). Nothing here decides to post: the approve route does, on the owner's click only."""
import base64
import re
import secrets

SERVICES = {
    'uploadpost': {'name': 'Upload-Post', 'site': 'https://upload-post.com', 'keys': 'https://app.upload-post.com/api-keys', 'base': 'https://api.upload-post.com',
                   'platforms': ('x', 'tiktok', 'youtube', 'instagram', 'bluesky', 'threads', 'linkedin'), 'thread': True,
                   'how': 'Upload-Post › API keys. If you made more than one profile there, save "<profile name> <key>".'},
    'zernio': {'name': 'Zernio', 'site': 'https://zernio.com', 'keys': 'https://zernio.com/dashboard/api-keys', 'base': 'https://zernio.com/api/v1',
               'platforms': ('x', 'tiktok', 'youtube', 'instagram', 'bluesky', 'threads', 'linkedin', 'facebook'), 'thread': False,
               'how': 'Zernio › Settings › API keys.'},
    'ayrshare': {'name': 'Ayrshare', 'site': 'https://ayrshare.com', 'keys': 'https://app.ayrshare.com/api', 'base': 'https://api.ayrshare.com/api',
                 'platforms': ('x', 'tiktok', 'youtube', 'instagram', 'bluesky', 'threads', 'linkedin', 'facebook'), 'thread': True,
                 'how': 'Ayrshare › API Key.'},
}
PLAT = {'x': 'X', 'tiktok': 'TikTok', 'youtube': 'YouTube', 'instagram': 'Instagram', 'bluesky': 'Bluesky', 'threads': 'Threads', 'linkedin': 'LinkedIn', 'facebook': 'Facebook'}
WIRE = {'zernio': {'x': 'twitter'}, 'ayrshare': {'x': 'twitter'}}   # our platform id → the service's own
# what each platform gets by default: the piece, its format, and which post text rides with it
DEFAULT = {'tiktok': ('video', 'story'), 'youtube': ('video', 'story'), 'instagram': ('video', 'story'), 'x': ('image', 'feed'), 'bluesky': ('image', 'feed'),
           'threads': ('image', 'feed'), 'facebook': ('image', 'feed'), 'linkedin': ('image', 'wide')}
NEEDS_MEDIA = {'tiktok', 'youtube', 'instagram'}
VIDEO_ONLY = {'tiktok', 'youtube'}
KEY = re.compile(r'^(?:([A-Za-z0-9_.@-]{1,64})\s+)?([A-Za-z0-9_.\-]{16,4000})$')


def split_key(svc, saved):
    """The saved drawer value → (profile or None, key). Raises ValueError with what to do."""
    m = KEY.match(str(saved or '').strip())
    if svc not in SERVICES or not m:
        raise ValueError(f"That is not a {SERVICES.get(svc, {}).get('name', 'posting')} key. {SERVICES.get(svc, {}).get('how', '')}".strip())
    if m.group(1) and svc != 'uploadpost':
        raise ValueError(f"Save the {SERVICES[svc]['name']} key alone.")
    return m.group(1), m.group(2)


def plan(choice, files, studio, svc):
    """The owner's picks {platform: piece} (or the defaults) → what goes where. Pure. → (go [{platform, piece, format, file, text, title}], skipped [{platform, why}])"""
    s = SERVICES[svc]; by = {(f.get('piece'), f.get('format')): f for f in files or [] if isinstance(f, dict) and f.get('url') and not f.get('error')}
    post = (studio or {}).get('post') or {}; go, skip = [], []
    for pl, piece in (choice or {}).items():
        if pl not in PLAT:
            continue
        piece = piece if piece in ('video', 'image', 'thread') else DEFAULT[pl][0]
        if pl not in s['platforms']:
            skip.append({'platform': pl, 'why': f"{s['name']} does not post to {PLAT[pl]}"}); continue
        if piece == 'thread' and (not s['thread'] or pl not in ('x', 'threads', 'bluesky')):
            skip.append({'platform': pl, 'why': 'a thread goes to X, Threads or Bluesky through Upload-Post or Ayrshare'}); continue
        if pl in VIDEO_ONLY and piece != 'video':
            skip.append({'platform': pl, 'why': f'{PLAT[pl]} takes the video only'}); continue
        if pl in NEEDS_MEDIA and piece == 'thread':
            skip.append({'platform': pl, 'why': f'{PLAT[pl]} needs a picture or clip'}); continue
        fmt = 'story' if piece == 'video' and pl in NEEDS_MEDIA else DEFAULT[pl][1] if piece != 'video' else 'feed' if pl in ('x', 'bluesky', 'threads', 'facebook') else 'wide'
        f = by.get(('thread' if piece == 'thread' else piece, fmt))
        if not f:
            skip.append({'platform': pl, 'why': f'the {piece} file ({fmt}) is missing'}); continue
        text = f.get('text') if piece == 'thread' else post.get('story' if pl in NEEDS_MEDIA else 'wide' if pl in ('linkedin', 'facebook') else 'feed') or ''
        go.append({'platform': pl, 'piece': piece, 'format': fmt, 'file': f, 'text': str(text)[:2200], 'title': str((studio or {}).get('hook') or text)[:100]})
    return go, skip


def _err(r, name):
    try:
        j = r.json(); msg = j.get('message') or j.get('error') or j.get('msg') or ''
    except ValueError:
        msg = ''
    return f"{name} said {r.status_code}" + (f": {str(msg)[:140]}" if msg else '')


def _ctype(name):
    ext = str(name).rsplit('.', 1)[-1].lower()
    return 'video/mp4' if ext == 'mp4' else 'image/png' if ext == 'png' else 'image/jpeg'


# ── who is connected ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async def accounts(http, svc, saved):
    """The accounts the owner signed into the service. → [{platform, name}] (our platform ids). Raises ValueError with words."""
    prof, key = split_key(svc, saved); s = SERVICES[svc]; back = {v: k for k, v in WIRE.get(svc, {}).items()}
    if svc == 'uploadpost':
        r = await http.get(f"{s['base']}/api/uploadposts/users", headers={'Authorization': f'Apikey {key}'})
        if r.status_code != 200:
            raise ValueError(_err(r, s['name']))
        out = []
        for p in r.json().get('profiles') or []:
            if prof and p.get('username') != prof:
                continue
            for pl, v in (p.get('social_accounts') or {}).items():
                if v and pl in PLAT:
                    out.append({'platform': pl, 'name': str((v or {}).get('display_name') or p.get('username') or '')[:60] if isinstance(v, dict) else str(p.get('username'))[:60], 'profile': p.get('username')})
        return out
    if svc == 'zernio':
        r = await http.get(f"{s['base']}/accounts", headers={'Authorization': f'Bearer {key}'})
        if r.status_code != 200:
            raise ValueError(_err(r, s['name']))
        j = r.json(); rows = j.get('accounts') if isinstance(j, dict) else j
        return [{'platform': back.get(a.get('platform'), a.get('platform')), 'name': str(a.get('username') or a.get('displayName') or '')[:60], 'id': a.get('_id') or a.get('id')}
                for a in rows or [] if isinstance(a, dict) and back.get(a.get('platform'), a.get('platform')) in PLAT and a.get('isActive', True) is not False]
    r = await http.get(f"{s['base']}/user", headers={'Authorization': f'Bearer {key}'})
    if r.status_code != 200:
        raise ValueError(_err(r, s['name']))
    j = r.json(); names = {d.get('platform'): d.get('username') or d.get('displayName') for d in j.get('displayNames') or [] if isinstance(d, dict)}
    return [{'platform': back.get(pl, pl), 'name': str(names.get(pl) or '')[:60]} for pl in j.get('activeSocialAccounts') or [] if back.get(pl, pl) in PLAT]


# ── post (only ever called by the owner's approve) ─────────────────────────────────────────────────────────────────────────────────────
async def publish(http, svc, saved, go, read_file, accts=None):
    """Posts every planned piece. `read_file(file row) → bytes`. → {platform: {ok, ref, id, url, error}}. One platform failing never stops another."""
    prof, key = split_key(svc, saved); s = SERVICES[svc]; out = {}
    groups = {}
    for g in go:
        groups.setdefault((g['piece'], g['format'], g['text'], g['file'].get('url')), []).append(g)
    for (piece, _fmt, text, _u), rows in groups.items():
        pls = [g['platform'] for g in rows]; f = rows[0]['file']; title = rows[0]['title']
        try:
            if svc == 'uploadpost':
                res = await _up_post(http, s, key, prof, piece, pls, f, text, title, read_file)
            elif svc == 'zernio':
                res = await _zer_post(http, s, key, piece, pls, f, text, title, read_file, accts or [])
            else:
                res = await _ayr_post(http, s, key, piece, pls, f, text, title, read_file)
        except ValueError as e:
            res = {pl: {'ok': False, 'error': str(e)[:200]} for pl in pls}
        except Exception as e:   # noqa: BLE001: a network error is said per platform, never a crash
            res = {pl: {'ok': False, 'error': f'{s["name"]} did not answer ({type(e).__name__})'} for pl in pls}
        for pl in pls:
            out[pl] = {'piece': piece, **(res.get(pl) or {'ok': False, 'error': f'{s["name"]} gave no answer for {PLAT[pl]}'})}
    return out


async def _up_post(http, s, key, prof, piece, pls, f, text, title, read_file):
    user = prof
    if not user:
        r = await http.get(f"{s['base']}/api/uploadposts/users", headers={'Authorization': f'Apikey {key}'})
        if r.status_code != 200:
            raise ValueError(_err(r, s['name']))
        ps = [p for p in r.json().get('profiles') or [] if any((p.get('social_accounts') or {}).get(x) for x in pls)]
        if not ps:
            raise ValueError(f"No {s['name']} profile has {', '.join(PLAT[x] for x in pls)} connected.")
        user = ps[0].get('username')
    rid = 'fl' + secrets.token_hex(10); data = [('user', user), ('request_id', rid), ('async_upload', 'true')] + [('platform[]', x) for x in pls]
    h = {'Authorization': f'Apikey {key}', 'Idempotency-Key': rid}
    if piece == 'thread':
        r = await http.post(f"{s['base']}/api/upload_text", headers=h, data=dict(data[:3]) | {'title': text}, files=[('platform[]', (None, x)) for x in pls])
    elif piece == 'image':
        name = str(f['url']).rsplit('/', 1)[-1]
        r = await http.post(f"{s['base']}/api/upload_photos", headers=h, data=dict(data[:3]) | {'title': text}, files=[('platform[]', (None, x)) for x in pls] + [('photos[]', (name, read_file(f), _ctype(name)))])
    else:
        name = str(f['url']).rsplit('/', 1)[-1]
        r = await http.post(f"{s['base']}/api/upload", headers=h, data=dict(data[:3]) | {'title': title, 'description': text, 'tiktok_title': text[:2200], 'instagram_title': text[:2200]},
                            files=[('platform[]', (None, x)) for x in pls] + [('video', (name, read_file(f), 'video/mp4'))])
    if r.status_code not in (200, 202):
        raise ValueError(_err(r, s['name']))
    j = r.json(); res = j.get('results') if isinstance(j.get('results'), dict) else {}
    return {pl: ({'ok': bool((res.get(pl) or {}).get('success')), 'ref': rid, 'url': (res.get(pl) or {}).get('url'), 'error': (res.get(pl) or {}).get('error')} if pl in res
                 else {'ok': True, 'ref': rid, 'pending': True}) for pl in pls}


async def _zer_post(http, s, key, piece, pls, f, text, title, read_file, accts):
    h = {'Authorization': f'Bearer {key}'}; ids = {a.get('platform'): a.get('id') for a in accts if a.get('id')}
    missing = [x for x in pls if not ids.get(x)]
    if missing:
        raise ValueError(f"No {', '.join(PLAT[x] for x in missing)} account connected in Zernio.")
    media = []
    if piece in ('image', 'video'):
        name = str(f['url']).rsplit('/', 1)[-1]; ct = _ctype(name)
        r = await http.post(f"{s['base']}/media/presign", headers=h, json={'filename': name, 'contentType': ct})
        if r.status_code != 200:
            raise ValueError(_err(r, s['name']))
        pre = r.json(); up = await http.put(pre['uploadUrl'], content=read_file(f), headers={'Content-Type': ct})
        if up.status_code not in (200, 201, 204):
            raise ValueError(f"{s['name']} storage said {up.status_code}")
        media = [{'type': piece, 'url': pre['publicUrl']}]
    body = {'content': text, 'mediaItems': media, 'publishNow': True,
            'platforms': [{'platform': WIRE['zernio'].get(x, x), 'accountId': ids[x], **({'platformSpecificData': {'title': title}} if x == 'youtube' else {})} for x in pls]}
    r = await http.post(f"{s['base']}/posts", headers={**h, 'x-request-id': 'fl' + secrets.token_hex(10)}, json=body)
    if r.status_code not in (200, 201):
        raise ValueError(_err(r, s['name']))
    p = (r.json() or {}).get('post') or {}; back = {v: k for k, v in WIRE['zernio'].items()}
    got = {back.get(x.get('platform'), x.get('platform')): x for x in p.get('platforms') or [] if isinstance(x, dict)}
    return {pl: {'ok': (got.get(pl) or {}).get('status') not in ('failed', 'error'), 'ref': p.get('_id'), 'url': (got.get(pl) or {}).get('platformPostUrl'),
                 'id': (got.get(pl) or {}).get('platformPostId'), 'error': (got.get(pl) or {}).get('errorMessage')} for pl in pls}


async def _ayr_post(http, s, key, piece, pls, f, text, title, read_file):
    h = {'Authorization': f'Bearer {key}'}; body = {'post': text, 'platforms': [WIRE['ayrshare'].get(x, x) for x in pls]}
    if piece in ('image', 'video'):
        name = str(f['url']).rsplit('/', 1)[-1]; ct = _ctype(name)
        r = await http.post(f"{s['base']}/media/upload", headers=h, json={'file': f"data:{ct};base64,{base64.b64encode(read_file(f)).decode()}", 'fileName': name})
        if r.status_code != 200 or not (r.json() or {}).get('url'):
            raise ValueError(_err(r, s['name']))
        body['mediaUrls'] = [r.json()['url']]
        if piece == 'video':
            body['isVideo'] = True
            if 'youtube' in pls:
                body['youTubeOptions'] = {'title': title, 'shorts': True, 'visibility': 'public'}
    if piece == 'thread':
        body['twitterOptions'] = {'thread': True, 'threadNumber': False}
    r = await http.post(f"{s['base']}/post", headers=h, json=body)
    if r.status_code not in (200, 201):
        raise ValueError(_err(r, s['name']))
    j = r.json() or {}; back = {v: k for k, v in WIRE['ayrshare'].items()}
    got = {back.get(x.get('platform'), x.get('platform')): x for x in j.get('postIds') or [] if isinstance(x, dict)}
    errs = {back.get(e.get('platform'), e.get('platform')): e.get('message') for e in j.get('errors') or [] if isinstance(e, dict)}
    return {pl: {'ok': (got.get(pl) or {}).get('status') == 'success', 'ref': j.get('id'), 'url': (got.get(pl) or {}).get('postUrl'), 'id': (got.get(pl) or {}).get('id'),
                 'error': errs.get(pl)} for pl in pls}


# ── reach, read back ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _num_dict(d):
    """The numbers of a service's analytics block, flattened one level (some nest them under 'analytics' / 'post_metrics' / 'metrics')."""
    d = d if isinstance(d, dict) else {}
    for k in ('post_metrics', 'analytics', 'metrics', 'stats'):
        if isinstance(d.get(k), dict):
            return {**{a: b for a, b in d.items() if isinstance(b, (int, float))}, **d[k]}
    return d


async def reach(http, svc, saved, posted):
    """Each posted platform's numbers now. → {platform: raw metrics dict} plus {'_errors': {platform: why}}. Never raises for one platform."""
    _prof, key = split_key(svc, saved); s = SERVICES[svc]; out, errs = {}, {}
    refs = {}
    for pl, row in (posted or {}).items():
        if isinstance(row, dict) and row.get('ok') and row.get('ref'):
            refs.setdefault(row['ref'], []).append(pl)
    back = {v: k for k, v in WIRE.get(svc, {}).items()}
    for ref, pls in refs.items():
        try:
            if svc == 'uploadpost':
                r = await http.get(f"{s['base']}/api/uploadposts/post-analytics/{ref}", headers={'Authorization': f'Apikey {key}'})
                if r.status_code != 200:
                    raise ValueError(_err(r, s['name']))
                for pl, v in (r.json().get('platforms') or {}).items():
                    if pl in pls:
                        if (v or {}).get('post_metrics_error') and not (v or {}).get('post_metrics'):
                            errs[pl] = str(v['post_metrics_error'])[:160]
                        out[pl] = _num_dict(v)
            elif svc == 'zernio':
                r = await http.get(f"{s['base']}/analytics", headers={'Authorization': f'Bearer {key}'}, params={'postId': ref})
                if r.status_code != 200:
                    raise ValueError(_err(r, s['name']))
                j = r.json() or {}; rows = j.get('platformAnalytics') or []
                for x in rows:
                    pl = back.get((x or {}).get('platform'), (x or {}).get('platform'))
                    if pl in pls:
                        out[pl] = _num_dict(x)
                if not rows and len(pls) == 1 and isinstance(j.get('analytics'), dict):
                    out[pls[0]] = j['analytics']
            else:
                r = await http.post(f"{s['base']}/analytics/post", headers={'Authorization': f'Bearer {key}'}, json={'id': ref, 'platforms': [WIRE['ayrshare'].get(x, x) for x in pls]})
                if r.status_code != 200:
                    raise ValueError(_err(r, s['name']))
                j = r.json() or {}
                for x in pls:
                    v = j.get(WIRE['ayrshare'].get(x, x))
                    if isinstance(v, dict):
                        out[x] = _num_dict(v)
                for e in j.get('errors') or []:
                    if isinstance(e, dict):
                        errs[back.get(e.get('platform'), e.get('platform'))] = str(e.get('message') or '')[:160]
        except Exception as e:   # noqa: BLE001
            for pl in pls:
                errs[pl] = str(e)[:160] if isinstance(e, ValueError) else f"{s['name']} did not answer"
    return {**out, '_errors': errs}
