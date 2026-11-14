"""📮 POC-PLAY item 8 (owner 2026-11-13): a picked week board goes out FOR REAL through Postiz's official public API (it holds the OAuth
connections to X / Instagram / TikTok / YouTube / LinkedIn / Threads — we never touch a platform password). Nothing posts without the
owner's own Postiz key saved on the agent AND his click. Each post is scheduled (or left as a draft) on the channel Postiz has for its
platform; a platform with no connected channel is skipped and said, never guessed.

Key format: the Postiz API key alone (cloud, https://api.postiz.com/public/v1), or `<https base url> <key>` for a self-hosted Postiz.
Pure helpers + three calls that take an httpx.AsyncClient (faked in tests)."""
import datetime as dt
import re

CLOUD = 'https://api.postiz.com/public/v1'
DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
# our board platform → the Postiz integration identifiers that can carry it (first connected one wins)
IDENT = {'x': ('x',), 'instagram': ('instagram', 'instagram-standalone'), 'tiktok': ('tiktok',), 'youtube': ('youtube',),
         'linkedin': ('linkedin', 'linkedin-page'), 'threads': ('threads',)}
NEEDS_MEDIA = {'instagram', 'tiktok', 'youtube'}   # these platforms refuse a words-only post
KEY = re.compile(r'^(?:(https://[^\s]{6,200})\s+)?((?:pos_)?[A-Za-z0-9_\-.]{16,200})$')


def split_key(saved):
    """'<key>' or '<https base> <key>' → (base, key). Raises ValueError."""
    m = KEY.match(str(saved or '').strip())
    if not m:
        raise ValueError('That is not a Postiz API key (Settings › Public API in Postiz).')
    return (m.group(1) or CLOUD).rstrip('/'), m.group(2)


def channel_for(integrations, platform):
    """The first connected, enabled Postiz channel for a board platform, or None."""
    for ident in IDENT.get(platform, ()):
        for it in integrations or []:
            if isinstance(it, dict) and it.get('identifier') == ident and not it.get('disabled') and it.get('id'):
                return it
    return None


def settings_for(platform, ident, caption, kind=None):
    """The per-platform `settings` block Postiz requires."""
    if platform == 'x':
        return {'__type': 'x', 'who_can_reply_post': 'everyone'}
    if platform == 'instagram':
        return {'__type': ident, 'post_type': 'post'}
    if platform == 'youtube':
        title = re.sub(r'\s+', ' ', caption).strip()[:100]
        return {'__type': 'youtube', 'title': title if len(title) >= 2 else 'New video', 'type': 'public', 'selfDeclaredMadeForKids': 'no'}
    if platform == 'tiktok':
        return {'__type': 'tiktok', 'privacy_level': 'PUBLIC_TO_EVERYONE', 'duet': False, 'stitch': False, 'comment': True, 'autoAddMusic': 'no',
                'brand_content_toggle': False, 'brand_organic_toggle': False, 'content_posting_method': 'DIRECT_POST'}
    return {'__type': ident}


def next_monday(today):
    """The Monday after `today` (a date). A week board always goes into a whole coming week."""
    return today + dt.timedelta(days=7 - today.weekday())


def when(post, start, tz_min=0):
    """Board post {day, time 'HH:MM'} + the week's Monday (date) + the browser's getTimezoneOffset() minutes → UTC datetime."""
    h, m = (int(x) for x in str(post.get('time') or '09:00').split(':')[:2])
    local = dt.datetime.combine(start + dt.timedelta(days=DAYS.index(post['day'])), dt.time(h, m))
    return (local + dt.timedelta(minutes=int(tz_min or 0))).replace(tzinfo=dt.timezone.utc)


def plan(posts, integrations, start, tz_min, now, has_media):
    """→ (sendable [(i, post, channel, utc)], skipped [(i, platform, why)]). `has_media(post)` says if its media file exists. Pure."""
    go, skip = [], []
    for i, p in enumerate(posts or []):
        ch = channel_for(integrations, p.get('platform'))
        t = when(p, start, tz_min)
        if not ch:
            skip.append((i, p.get('platform'), 'no connected channel in Postiz'))
        elif t <= now + dt.timedelta(minutes=5):
            skip.append((i, p.get('platform'), 'that time has passed'))
        elif p.get('platform') in NEEDS_MEDIA and not has_media(p):
            skip.append((i, p.get('platform'), 'needs a picture or clip'))
        else:
            go.append((i, p, ch, t))
    return go, skip


def body(post, channel, utc, mode, media=None):
    """The POST /posts body for one board post. mode: 'schedule' or 'draft'."""
    ident = channel.get('identifier') or post['platform']
    return {'type': 'draft' if mode == 'draft' else 'schedule', 'date': utc.strftime('%Y-%m-%dT%H:%M:%S.000Z'), 'shortLink': False, 'tags': [],
            'posts': [{'integration': {'id': channel['id']}, 'value': [{'content': post['caption'], 'image': [media] if media else []}],
                       'settings': settings_for(post['platform'], ident, post['caption'])}]}


def _err(r):
    try:
        j = r.json(); msg = j.get('msg') or j.get('message') or ''
    except ValueError:
        msg = ''
    return f'Postiz said {r.status_code}' + (f': {str(msg)[:120]}' if msg else '')


async def channels(http, base, key):
    """GET /integrations → the connected channels. Raises ValueError with words."""
    r = await http.get(f'{base}/integrations', headers={'Authorization': key})
    if r.status_code != 200:
        raise ValueError('Postiz refused the key.' if r.status_code in (401, 403) else _err(r))
    j = r.json()
    return j if isinstance(j, list) else []


async def upload(http, base, key, name, raw, ctype):
    """POST /upload → {id, path} for a media file."""
    r = await http.post(f'{base}/upload', headers={'Authorization': key}, files={'file': (name, raw, ctype)})
    if r.status_code not in (200, 201):
        raise ValueError(_err(r))
    j = r.json()
    if not j.get('id') or not j.get('path'):
        raise ValueError('Postiz did not keep the file.')
    return {'id': j['id'], 'path': j['path']}


async def create(http, base, key, payload):
    """POST /posts → the Postiz post id."""
    r = await http.post(f'{base}/posts', headers={'Authorization': key}, json=payload)
    if r.status_code not in (200, 201):
        raise ValueError(_err(r))
    j = r.json(); first = (j[0] if isinstance(j, list) and j else j) or {}
    return str(first.get('postId') or first.get('id') or '')
