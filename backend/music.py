"""🎵 Mini player search (pure, tested): YouTube search results read from YouTube's own public results page (no key), Apple Music's
most-played chart (public RSS, no key), and the "keep going" pick for Next when the queue runs out (the artist's next song not already queued).
Spotify search runs only when the owner sets SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET; its tracks still PLAY through YouTube (the player)."""
import json
import re


def _text(x):
    if not isinstance(x, dict):
        return ''
    return x.get('simpleText') or ''.join(r.get('text', '') for r in x.get('runs') or [])


def yt_results(html, limit=20):
    """YouTube results page → [{id, title, channel, length, views, url, thumb}] (videos only, no shorts / live without a length)."""
    m = re.search(r'var ytInitialData = (\{.*?\});</script>', html or '', re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return []
    out, seen = [], set()

    def walk(o):
        if len(out) >= limit:
            return
        if isinstance(o, dict):
            v = o.get('videoRenderer')
            if isinstance(v, dict) and v.get('videoId') and v['videoId'] not in seen and v.get('lengthText'):
                seen.add(v['videoId'])
                out.append({'id': v['videoId'], 'title': _text(v.get('title')), 'channel': _text(v.get('ownerText')), 'length': _text(v.get('lengthText')),
                            'views': _text(v.get('viewCountText')), 'url': f"https://www.youtube.com/watch?v={v['videoId']}",
                            'thumb': f"https://i.ytimg.com/vi/{v['videoId']}/mqdefault.jpg"})
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(data)
    return out


def apple_top(doc, limit=25):
    """Apple Music most-played RSS → [{title, artist, art, query}] — `query` is what to search on YouTube to play it."""
    rows = ((doc or {}).get('feed') or {}).get('results') or []
    return [{'title': r.get('name'), 'artist': r.get('artistName'), 'art': r.get('artworkUrl100'), 'query': f"{r.get('artistName')} {r.get('name')}"}
            for r in rows[:limit] if r.get('name')]


def artist_of(title):
    """'Drake - God's Plan (Official Video)' → 'Drake'; 'God's Plan' → the whole title (search will still find more like it)."""
    t = re.sub(r'\s*[\(\[].*?[\)\]]', '', title or '').strip()
    for sep in (' - ', ' – ', ' — ', ' | '):
        if sep in t:
            return t.split(sep)[0].strip()
    return t


def secs(length):
    """'3:19' → 199 · '1:02:03' → 3723 · '' → None."""
    try:
        parts = [int(x) for x in str(length or '').split(':') if x != '']
    except ValueError:
        return None
    if not parts:
        return None
    total = 0
    for x in parts:
        total = total * 60 + x
    return total


def pick_next(results, skip_ids=(), skip_titles=(), max_secs=480):
    """The first SONG (≤ 8 min — never an hour-long mix) not already in the queue (by id or a near-identical title)."""
    norm = lambda s: re.sub(r'[^a-z0-9]', '', re.sub(r'\s*[\(\[].*?[\)\]]', '', s or '').lower())[:24]   # '(Lyrics)' / '[Official]' copies are the same song
    taken = {norm(t) for t in skip_titles}
    for r in results or []:
        n = secs(r.get('length'))
        if r['id'] not in set(skip_ids) and norm(r['title']) not in taken and (n is None or n <= max_secs) and 'mix' not in (r.get('title') or '').lower().split():
            return r
    return None


def spotify_tracks(doc, limit=10):
    items = (((doc or {}).get('tracks') or {}).get('items')) or []
    return [{'title': t.get('name'), 'artist': ', '.join(a.get('name', '') for a in t.get('artists') or []), 'art': (((t.get('album') or {}).get('images') or [{}])[0]).get('url'),
             'popularity': t.get('popularity'), 'query': f"{(t.get('artists') or [{}])[0].get('name', '')} {t.get('name')}"} for t in items[:limit]]
