"""🎨 POC-PLAY (owner 2026-11-13): the click-and-grab playground every PoC image / video opens in. The editing runs in the browser (Konva,
free, no key); this side only takes the finished picture back and files it in the PoC folder as a NEW version (the original stays).
Pure: a data URL in, checked bytes out."""
import base64
import re

MAX_BYTES = 12 * 1024 * 1024          # a 4K PNG of a busy scene stays under this
TEMPLATES = ('free', 'post', 'story', 'thumb', 'phone', 'billboard', 'shelf', 'launch', 'ideas', 'adset')
_DATA = re.compile(r'^data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=\s]+)$')
_MAGIC = {'png': b'\x89PNG\r\n\x1a\n', 'jpeg': b'\xff\xd8\xff', 'webp': b'RIFF'}


def decode(data_url):
    """'data:image/png;base64,…' → (bytes, file extension). Raises ValueError with words the canvas shows. The bytes must really be the
    picture type they claim (a renamed file or script never lands in the media folder)."""
    m = _DATA.match(str(data_url or '').strip())
    if not m:
        raise ValueError('Export the canvas as a PNG, JPG or WebP picture first.')
    if len(m.group(2)) > MAX_BYTES * 4 // 3 + 8:
        raise ValueError('That picture is too big (12 MB at most). Make the canvas smaller.')
    try:
        raw = base64.b64decode(re.sub(r'\s', '', m.group(2)), validate=True)
    except (ValueError, base64.binascii.Error):
        raise ValueError('The picture did not come through whole. Try again.')
    kind = m.group(1)
    if not raw.startswith(_MAGIC[kind]) or (kind == 'webp' and raw[8:12] != b'WEBP') or len(raw) < 64:
        raise ValueError('That is not a real picture.')
    if len(raw) > MAX_BYTES:
        raise ValueError('That picture is too big (12 MB at most). Make the canvas smaller.')
    return raw, {'jpeg': 'jpg'}.get(kind, kind)


def version_label(messages, template=None):
    """'Playground v3 · story': which edit of this folder it is, and the frame it was made in. Pure."""
    n = 1 + sum(1 for m in messages or [] if ((m or {}).get('media') or {}).get('provider') == 'playground')
    t = template if template in TEMPLATES and template != 'free' else None
    return f"Playground v{n}{f' · {t}' if t else ''}"
