"""📺 Watch folder highlights (owner 2026-11-12: "recent highlights per gamer or team").

Free and legal, no API key: every official channel publishes its newest videos as a public feed
(youtube.com/feeds/videos.xml?channel_id=…). We read those feeds, newest first, and filter by the team / player / gamer the user typed.
Any channel can be followed by its @handle: the channel page's CANONICAL id is used (the first "channelId" on a page is often a featured
channel, not the page's own). Nothing is downloaded or rehosted: the site plays each video in YouTube's own player.
"""
import asyncio
import re
import time
import xml.etree.ElementTree as ET

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

UA = {'User-Agent': 'Mozilla/5.0 (FEELESS watch room)', 'Accept-Language': 'en'}
NS = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015', 'm': 'http://search.yahoo.com/mrss/'}
FEED_TTL = 600          # a channel's feed is read at most every 10 minutes, shared by every viewer
HANDLE_TTL = 86400
MAX_CH = 30
_re_ch = re.compile(r'^UC[\w-]{22}$')
_re_handle = re.compile(r'^@?[\w.\-]{3,40}$')
_feeds: dict = {}       # channel id → (at, [videos])
_handles: dict = {}     # handle → (at, {id, name})
_client = None


def _http():
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=8, headers=UA, follow_redirects=True)
    return _client


def parse_feed(xml_text):
    """A channel feed → [{id, title, channel, channelId, at, thumb, views}] (newest first, as the feed lists them). Pure."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    ch = (root.findtext('a:title', '', NS) or '').strip()
    out = []
    for e in root.findall('a:entry', NS):
        vid = e.findtext('yt:videoId', '', NS)
        if not vid:
            continue
        stats = e.find('m:group/m:community/m:statistics', NS)
        thumb = e.find('m:group/m:thumbnail', NS)
        out.append({'id': vid, 'title': (e.findtext('a:title', '', NS) or '').strip(), 'channel': ch, 'channelId': e.findtext('yt:channelId', '', NS),
                    'at': e.findtext('a:published', '', NS), 'thumb': thumb.get('url') if thumb is not None else f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg',
                    'views': int(stats.get('views') or 0) if stats is not None else 0, 'short': '/shorts/' in (e.find('a:link', NS).get('href') if e.find('a:link', NS) is not None else '')})
    return out


def match(videos, q):
    """Keep the videos whose title names every word the user typed (any order, any case). Empty q keeps all. Pure."""
    words = [w for w in re.split(r'\s+', (q or '').lower().strip()) if w]
    if not words:
        return list(videos)
    return [v for v in videos if all(re.search(r'(?<![a-z0-9])' + re.escape(w), v['title'].lower()) for w in words)]


def canonical_id(html):
    """A channel page → its OWN channel id (canonical link / externalId), never a featured channel's. Pure."""
    m = re.search(r'rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', html) or re.search(r'"externalId":"(UC[\w-]{22})"', html)
    return m.group(1) if m else None


async def _feed(cid):
    hit = _feeds.get(cid)
    if hit and time.time() - hit[0] < FEED_TTL:
        return hit[1]
    try:
        r = await _http().get('https://www.youtube.com/feeds/videos.xml', params={'channel_id': cid})
        vids = parse_feed(r.text) if r.status_code == 200 else []
    except httpx.HTTPError:
        vids = hit[1] if hit else []   # a blip keeps the last good read
    _feeds[cid] = (time.time(), vids)
    return vids


@router.get('/api/reputation/watch/highlights')
async def highlights(ch: str = '', q: str = '', shorts: int = 1, limit: int = 40):
    """🎬 Newest videos across these official channels, filtered by a team / player / gamer name → {videos, channels, read}."""
    ids = [c for c in dict.fromkeys(ch.split(',')) if _re_ch.match(c)][:MAX_CH]
    if not ids:
        raise HTTPException(400, 'Pick at least one channel.')
    feeds = await asyncio.gather(*(_feed(c) for c in ids))
    allv = [v for f in feeds for v in f if shorts or not v['short']]
    got = sorted(match(allv, q[:60]), key=lambda v: v['at'], reverse=True)[:max(1, min(limit, 80))]
    return {'videos': got, 'channels': len(ids), 'read': sum(1 for f in feeds if f), 'q': q[:60]}


@router.get('/api/reputation/watch/channel')
async def channel(handle: str):
    """➕ Follow any channel by its @handle (a team, a league, a gamer) → {id, name}."""
    h = handle.strip().lstrip('@')
    if not _re_handle.match(h):
        raise HTTPException(400, 'Type a YouTube handle, like @NBA.')
    hit = _handles.get(h.lower())
    if hit and time.time() - hit[0] < HANDLE_TTL:
        return hit[1]
    try:
        r = await _http().get(f'https://www.youtube.com/@{h}')
    except httpx.HTTPError:
        raise HTTPException(502, 'YouTube did not answer. Try again in a moment.')
    cid = canonical_id(r.text) if r.status_code == 200 else None
    if not cid:
        raise HTTPException(404, f'No YouTube channel is called @{h}.')
    m = re.search(r'<meta property="og:title" content="([^"]*)"', r.text)
    out = {'id': cid, 'name': (m.group(1) if m else h)[:60], 'handle': f'@{h}'}
    _handles[h.lower()] = (time.time(), out)
    return out
