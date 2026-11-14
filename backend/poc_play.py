"""🎨 POC-PLAY (owner 2026-11-13): the click-and-grab playground every PoC image / video opens in. The editing runs in the browser (Konva,
free, no key); this side only takes the finished picture back and files it in the PoC folder as a NEW version (the original stays).
Pure: a data URL in, checked bytes out."""
import base64
import re

MAX_BYTES = 12 * 1024 * 1024          # a 4K PNG of a busy scene stays under this
MAX_CLIP = 48 * 1024 * 1024           # a 60 s clip at 6 Mbps (the playground's recorder) is ~45 MB
TEMPLATES = ('free', 'post', 'story', 'thumb', 'phone', 'billboard', 'shelf', 'launch', 'ideas', 'adset')
_DATA = re.compile(r'^data:(?:image|video)/(png|jpeg|webp|mp4|webm)(?:;codecs=[\w.,"\'-]+)?;base64,([A-Za-z0-9+/=\s]+)$')
_MAGIC = {'png': b'\x89PNG\r\n\x1a\n', 'jpeg': b'\xff\xd8\xff', 'webp': b'RIFF', 'webm': b'\x1a\x45\xdf\xa3', 'mp4': b''}
VIDEO = ('mp4', 'webm')


def decode(data_url):
    """'data:image/png;base64,…' or a recorded clip 'data:video/mp4;base64,…' → (bytes, file extension). Raises ValueError with words the
    canvas shows. The bytes must really be the type they claim (a renamed file or script never lands in the media folder)."""
    m = _DATA.match(str(data_url or '').strip())
    if not m:
        raise ValueError('Export the canvas as a PNG, JPG or WebP picture (or an MP4 / WebM clip) first.')
    kind = m.group(1); clip = kind in VIDEO; cap = MAX_CLIP if clip else MAX_BYTES
    big = f'That clip is too big ({cap // 1048576} MB at most). Make it shorter.' if clip else 'That picture is too big (12 MB at most). Make the canvas smaller.'
    if len(m.group(2)) > cap * 4 // 3 + 8:
        raise ValueError(big)
    try:
        raw = base64.b64decode(re.sub(r'\s', '', m.group(2)), validate=True)
    except (ValueError, base64.binascii.Error):
        raise ValueError('The file did not come through whole. Try again.')
    real = raw.startswith(_MAGIC[kind]) and len(raw) >= 64 and (kind != 'webp' or raw[8:12] == b'WEBP') and (kind != 'mp4' or raw[4:8] == b'ftyp')
    if not real:
        raise ValueError('That is not a real clip.' if clip else 'That is not a real picture.')
    if len(raw) > cap:
        raise ValueError(big)
    return raw, {'jpeg': 'jpg'}.get(kind, kind)


def kind_of(ext):
    """'mp4' / 'webm' → 'video', a picture → 'image'."""
    return 'video' if ext in VIDEO else 'image'


def version_label(messages, template=None):
    """'Playground v3 · story': which edit of this folder it is, and the frame it was made in. Pure."""
    n = 1 + sum(1 for m in messages or [] if ((m or {}).get('media') or {}).get('provider') == 'playground')
    t = template if template in TEMPLATES and template != 'free' else None
    return f"Playground v{n}{f' · {t}' if t else ''}"
