"""🎭 AN AGENT'S CHARACTER (owner 2026-11-04): one of Wireface 2D's 24 free characters, or the owner's own picture rigged in their browser. A look only: no engine reads it."""
import io
import json

from PIL import Image

PEOPLE = ('sarah', 'marcus', 'amara', 'walter', 'lucia', 'arjun', 'omar', 'ruth', 'robot', 'monster', 'dracula')
FACES = PEOPLE + ('ava', 'pip', 'sora', 'mabel', 'rex', 'eleanor', 'hazel', 'theo', 'kit', 'gus', 'vee', 'fern', 'bolt')
CUSTOM = 'custom'
MAX_CHAR = 6_000_000   # one rigged picture is about 0.7 MB
MAX_THUMB = 400_000


def clean_id(v):
    v = str(v or '').strip().lower()
    return v if v in FACES else None


def clean_thumb(raw):
    """A small JPEG, re-encoded so nothing but pixels survives (no EXIF, no location). None when it is not a picture."""
    if not raw or len(raw) > MAX_THUMB:
        return None
    try:
        im = Image.open(io.BytesIO(raw)); im.load()
        im = im.convert('RGB'); im.thumbnail((256, 256))
        out = io.BytesIO(); im.save(out, 'JPEG', quality=82)
        return out.getvalue()
    except Exception:   # noqa: BLE001 — anything Pillow cannot read is not a picture
        return None


def clean_character(raw):
    """A rigged character's JSON, or None. It is served to visitors, so it must parse as one object and fit the cap."""
    if not raw or len(raw) > MAX_CHAR:
        return None
    try:
        d = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    return raw if isinstance(d, dict) and d else None
