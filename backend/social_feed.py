"""📰 FEEd's outside sources (owner, 2026-10-18: "FEEd should show X, Reddit and other crypto social updates … mixed or by site").
Pure parsers: every source becomes the SAME post shape so the page can mix them on one timeline —
{id, src, author, handle, avatar, text, url, at (sec), img, coin: {symbol, mint} | None}.

What can be read WITHOUT anyone's login (measured 2026-10-18): Pump's own callouts (already read for the desk), public Telegram channels
(t.me/s/<channel> preview pages) and Bluesky's public search. X and Reddit refuse server reads without their own registered API apps
(X 401 / Reddit 403), so FEEd posts TO them through their own compose pages (the user's own login, the user presses Post) — never a stored
password or token here. Text from other people is data: trimmed, control characters dropped, rendered as text, links http(s) only."""
import html as _html
import re

SOURCES = (('feeless', 'FEELESS'), ('pump', 'Pump'), ('telegram', 'Telegram'), ('bluesky', 'Bluesky'))
TG_CHANNELS = ('pumpfun', 'whale_alert_io')
BSKY_QUERY = 'solana memecoin'
TEXT_MAX = 600
_CTRL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')
_TAG = re.compile(r'<[^>]+>')


def clean(t, n=TEXT_MAX):
    t = _CTRL.sub('', _html.unescape(str(t or ''))).strip()
    return t[:n]


def safe_url(u):
    u = str(u or '').strip()
    return u if u.startswith(('https://', 'http://')) else None


def _num(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def from_pump(latest):
    """Pump callouts → posts (caller, thesis, the coin it was called on)."""
    out = []
    for c in latest or []:
        at = _num(c.get('at'))
        at = at / 1000 if at > 1e12 else at
        if not at or not (c.get('thesis') or c.get('symbol')):
            continue
        mint = c.get('mint')
        out.append({'id': f"pump:{c.get('id') or mint}:{int(at)}", 'src': 'pump', 'author': clean(c.get('user'), 40) or 'pump caller', 'handle': clean(c.get('user'), 40),
                    'avatar': safe_url(c.get('avatar')), 'text': clean(c.get('thesis')) or f"called ${clean(c.get('symbol'), 20)}", 'at': at,
                    'url': f'https://pump.fun/coin/{mint}' if mint else None, 'img': safe_url(c.get('logo')),
                    'coin': {'symbol': clean(c.get('symbol'), 20), 'mint': mint, 'mcap': _num(c.get('mcap')) or None, 'atMc': _num(c.get('atMc')) or None} if mint else None})
    return out


def from_feeless(msgs, room):
    """FEELESS room messages → posts."""
    out = []
    for m in msgs or []:
        at = _num(m.get('ts') or m.get('at'))
        at = at / 1000 if at > 1e12 else at
        txt = clean(m.get('text'))
        if not at or not txt:
            continue
        who = clean(m.get('handle') or m.get('name') or (str(m.get('address') or '')[:4] + '…' + str(m.get('address') or '')[-4:]), 40)
        out.append({'id': f"feeless:{room}:{m.get('id') or int(at)}", 'src': 'feeless', 'author': who, 'handle': who, 'avatar': safe_url(m.get('avatar')),
                    'text': txt, 'at': at, 'url': None, 'img': None, 'coin': None, 'room': room, 'address': m.get('address')})
    return out


_TG_MSG = re.compile(r'<div class="tgme_widget_message [^"]*"[^>]*data-post="([^"]+)"(.*?)(?=<div class="tgme_widget_message_wrap|\Z)', re.S)
_TG_TEXT = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
_TG_TIME = re.compile(r'<time[^>]*datetime="([^"]+)"')
_TG_NAME = re.compile(r'tgme_widget_message_owner_name"[^>]*><span[^>]*>(.*?)</span>', re.S)
_TG_PHOTO = re.compile(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)")
_TG_AVA = re.compile(r'tgme_widget_message_user_photo[^>]*>\s*<img src="([^"]+)"')


def _iso(s):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(s).replace('Z', '+00:00')).timestamp()
    except ValueError:
        return 0.0


def parse_telegram(page, channel):
    """A public channel preview page (t.me/s/<channel>) → posts, oldest → newest as the page lists them."""
    out = []
    for post, body in _TG_MSG.findall(page or ''):
        tm = _TG_TEXT.search(body)
        txt = clean(_TAG.sub('', (tm.group(1) if tm else '').replace('<br/>', '\n').replace('<br>', '\n')))
        at = _iso((_TG_TIME.search(body) or [None, ''])[1]) if _TG_TIME.search(body) else 0.0
        if not txt or not at:
            continue
        nm = _TG_NAME.search(body); ph = _TG_PHOTO.search(body); av = _TG_AVA.search(body)
        out.append({'id': f'telegram:{post}', 'src': 'telegram', 'author': clean(_TAG.sub('', nm.group(1)), 40) if nm else channel, 'handle': channel,
                    'avatar': safe_url(av.group(1)) if av else None, 'text': txt, 'at': at, 'url': f'https://t.me/{post}', 'img': safe_url(ph.group(1)) if ph else None, 'coin': None})
    return out


def parse_bluesky(js):
    """Bluesky public search (app.bsky.feed.searchPosts) → posts."""
    out = []
    for p in (js or {}).get('posts') or []:
        a = p.get('author') or {}; r = p.get('record') or {}
        txt = clean(r.get('text')); at = _iso(r.get('createdAt'))
        uri = str(p.get('uri') or '')
        if not txt or not at or not uri:
            continue
        rk = uri.rsplit('/', 1)[-1]
        img = None
        emb = p.get('embed') or {}
        if (emb.get('images') or []):
            img = safe_url(emb['images'][0].get('thumb'))
        h = clean(a.get('handle'), 60)
        out.append({'id': f'bluesky:{rk}', 'src': 'bluesky', 'author': clean(a.get('displayName') or h, 40), 'handle': h, 'avatar': safe_url(a.get('avatar')),
                    'text': txt, 'at': at, 'url': f'https://bsky.app/profile/{h}/post/{rk}' if h else None, 'img': img, 'coin': None})
    return out


def mix(lists, srcs=None, limit=80):
    """Every source's posts on one timeline, newest first, one copy of each id; `srcs` = the bubbles the viewer picked (None = all)."""
    seen, out = set(), []
    for p in sorted([p for l in lists for p in (l or [])], key=lambda p: -_num(p.get('at'))):
        if p['id'] in seen or (srcs and p.get('src') not in srcs):
            continue
        seen.add(p['id']); out.append(p)
    return out[:limit]

