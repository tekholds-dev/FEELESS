"""🎞 Where a clip for a swap comes from (owner 2026-11-17: "goto my bishop file, add a viral video clip in there and ask them to replace the main
character with bishop"). Pure: no network, no files. The server fetches; this decides WHAT may be fetched and HOW ffmpeg cuts it.
  · a Bluesky post link (bsky.app/profile/<handle>/post/<rkey>) → its video, read from Bluesky's public API; the stream must sit on Bluesky's
    own video hosts (checked live 2026-11-17: getPostThread gives embed.playlist on video.bsky.app, an HLS playlist ffmpeg reads in ~6 s)
  · a direct https link to an .mp4 / .webm / .mov file
  · YouTube, TikTok, Instagram, X, Facebook links are refused with what to do instead: their terms forbid downloading, so the owner saves the
    clip from the app (he has the rights) and adds the file."""
import re
from urllib.parse import quote, urlparse

BSKY_POST = re.compile(r'^https://(?:www\.)?bsky\.app/profile/([A-Za-z0-9._:-]{3,253})/post/([A-Za-z0-9]{6,20})/?(?:[?#].*)?$')
BSKY_VIDEO_HOSTS = ('video.bsky.app', 'video.cdn.bsky.app')
BSKY_API = 'https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread'
DIRECT = re.compile(r'\.(mp4|webm|mov)$', re.I)
NO_DOWNLOAD = {'youtube.com': 'YouTube', 'youtu.be': 'YouTube', 'tiktok.com': 'TikTok', 'instagram.com': 'Instagram',
               'x.com': 'X', 'twitter.com': 'X', 'facebook.com': 'Facebook', 'fb.watch': 'Facebook'}


def classify(url):
    """→ ('bluesky', handle, rkey) | ('direct', url). ValueError with what to do for anything else."""
    u = str(url or '').strip()
    m = BSKY_POST.match(u)
    if m:
        return 'bluesky', m.group(1), m.group(2)
    if not u.startswith('https://'):
        raise ValueError('Paste a link that starts with https://')
    host = (urlparse(u).hostname or '').lower()
    for dom, name in NO_DOWNLOAD.items():
        if host == dom or host.endswith('.' + dom):
            raise ValueError(f"{name} doesn't allow downloading its videos. Save the clip from the {name} app (it has to be yours, or you need the rights), then press Add your clip.")
    if not DIRECT.search(urlparse(u).path or ''):
        raise ValueError('That link is not a video file. Paste a Bluesky post, or a link that ends in .mp4, .webm or .mov.')
    return 'direct', u


def bsky_thread_url(handle, rkey):
    return f"{BSKY_API}?uri={quote(f'at://{handle}/app.bsky.feed.post/{rkey}', safe='')}&depth=0&parentHeight=0"


def bsky_video(thread):
    """getPostThread's answer → (playlist url, words of the post). The video may sit in the post or in a quote-with-media. ValueError if none."""
    post = ((thread or {}).get('thread') or {}).get('post') or {}
    emb = post.get('embed') or {}
    for e in (emb, emb.get('media') or {}):
        pl = str(e.get('playlist') or '')
        if pl:
            if urlparse(pl).scheme != 'https' or (urlparse(pl).hostname or '') not in BSKY_VIDEO_HOSTS:
                raise ValueError("That post's video is not on Bluesky's own video servers.")
            return pl, ' '.join(str((post.get('record') or {}).get('text') or '').split())[:80]
    raise ValueError('That Bluesky post has no video.')


def cut_args(src, out, start=0.0, max_s=15, stream=False):
    """ffmpeg arguments: from `start` seconds, at most `max_s` seconds, re-encoded to plain H.264 + AAC MP4 (exact cut, plays everywhere).
    A stream (Bluesky HLS) may only use the network protocols HLS needs, never local files."""
    pre = ['-protocol_whitelist', 'https,tls,tcp,crypto,hls', '-rw_timeout', '20000000'] if stream else []
    seek = ['-ss', f'{max(0.0, float(start or 0)):.2f}'] if float(start or 0) > 0 else []
    pick = [] if stream else ['-map', '0:v:0', '-map', '0:a:0?']   # a stream: ffmpeg's own pick = its sharpest variant (Bluesky lists 360p first)
    return (['ffmpeg', '-v', 'error', '-nostdin', '-y'] + pre + seek + ['-i', str(src), '-t', f'{float(max_s):.2f}'] + pick + [
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(out)])


def ref_args(src, out, max_s=None):
    """A light copy of a clip for a reference upload: the short side at most 720 px, no sound, ~1–3 MB for 15 s; at most `max_s` seconds."""
    return ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(src), *(['-t', f'{float(max_s):.2f}'] if max_s else []), '-map', '0:v:0', '-an',
            '-vf', "scale='if(gt(iw,ih),-2,min(720,iw))':'if(gt(iw,ih),min(720,ih),-2)'",
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '27', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)]


def img_args(src, out):
    """A light JPEG of the character picture (long side at most 1280 px) for a reference upload."""
    return ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(src), '-vf', "scale='min(1280,iw)':-2", '-frames:v', '1', '-q:v', '3', str(out)]


def sound_args(made, clip, out):
    """The made video with the ORIGINAL clip's sound (same timing), cut to the shorter of the two. No sound in the clip → the video as made."""
    return ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(made), '-i', str(clip), '-map', '0:v:0', '-map', '1:a:0',
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(out)]


def nearest_aspect(w, h, allowed=('9:16', '3:4', '1:1', '4:3', '16:9', '21:9', '9:21')):
    """The allowed aspect ratio closest to w×h (a TikTok 1080×1920 → 9:16). No size → 9:16, the viral default."""
    try:
        r = float(w) / float(h)
    except (TypeError, ValueError, ZeroDivisionError):
        return '9:16'
    return min(allowed, key=lambda a: abs(int(a.split(':')[0]) / int(a.split(':')[1]) - r))


# 💬 Auto captions (owner 2026-11-17, studio proposal 3): the clip's sound → the owner's own OpenRouter (an audio-reading model) → timed lines.
CAPTION_MODEL = 'google/gemini-2.5-flash'   # reads audio through OpenRouter's input_audio; about $0.001 for a minute of speech
CAPTION_MAX_S = 60
CAPTION_ASK = ('Transcribe the speech in this audio as short on-screen captions. Answer ONLY with JSON: '
               '{"lines":[{"s":start seconds,"e":end seconds,"t":"the words"}]}. At most 6 words a line, in the order spoken, '
               'times from the start of the audio. No speech → {"lines":[]}.')


def audio_args(src, out, max_s=CAPTION_MAX_S):
    """The clip's sound only, mono 16 kHz MP3, at most `max_s` seconds (small: ~360 KB a minute)."""
    return ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(src), '-t', f'{float(max_s):.2f}', '-vn', '-ac', '1', '-ar', '16000',
            '-c:a', 'libmp3lame', '-b:a', '48k', str(out)]


def parse_captions(text, max_s=CAPTION_MAX_S):
    """The model's answer → [{'at', 'dur', 'text'}], in time order, inside 0..max_s, each 0.3–8 s, words ≤ 60 chars, at most 120 lines.
    Anything that is not the JSON asked for → []. Pure."""
    import json as _j
    raw = str(text or '')
    a, b = raw.find('{'), raw.rfind('}')
    try:
        rows = _j.loads(raw[a:b + 1]).get('lines') if a >= 0 and b > a else []
    except (ValueError, AttributeError):
        return []
    out = []
    for r in rows if isinstance(rows, list) else []:
        try:
            s, e = float(r.get('s')), float(r.get('e'))
        except (TypeError, ValueError, AttributeError):
            continue
        words = ' '.join(str(r.get('t') or '').split())[:60]
        if not words or s != s or e != e or s < 0 or s >= max_s:
            continue
        e = min(max_s, max(e, s + 0.3), s + 8)
        out.append({'at': round(s, 2), 'dur': round(e - s, 2), 'text': words})
    return sorted(out, key=lambda x: x['at'])[:120]
