"""🎓 TEACH THE DESK (owner, 2026-10-13: "where I can chat / coach / give images of charts / feed info on narratives to train the AI to teach
agents"). Pure + tested (`tests/test_teach.py`).

The owner writes NOTES (how they trench), NARRATIVES (what is hot and why) and CHART LESSONS (a caption + an optional chart image from the
FEELESS upload store). Every model read gets the teachings that fit the coin in its case (`for_case`: the owner's own words on THIS coin →
narratives whose words are in its name / ticker → the newest chart lessons → the newest notes), so the model's answers carry them; every
answer on a coin the owner taught is graded in its own learning bucket (ai_learn TAUGHT), so the record says whether the teaching helps.
A teaching is never an order, a size or a sell. Images are kept with their caption for the owner and the desk; the text model reads the
caption (a vision provider would be needed to read the picture itself).
"""
import re
import time

KINDS = ('note', 'narrative', 'chart')
MAX_TEXT, KEEP = 280, 200
STOP = {'the', 'and', 'for', 'are', 'with', 'this', 'that', 'coin', 'coins', 'meta', 'narrative', 'hot', 'new', 'all', 'any', 'you', 'our', 'its', 'not',
        'but', 'has', 'have', 'from', 'they', 'them', 'just', 'like', 'will', 'more', 'than', 'into', 'about', 'pump', 'sol', 'solana', 'buy', 'sell'}
_B58 = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')
_IMG = re.compile(r'^/api/reputation/uploads/[A-Za-z0-9._-]{4,80}$|^https://[A-Za-z0-9.-]+/api/reputation/uploads/[A-Za-z0-9._-]{4,80}$')


def _txt(s, n):
    return ' '.join(''.join(ch for ch in str(s or '') if ch.isprintable()).split())[:n]


def words(text):
    """A narrative's key words: lowercase letters / digits, ≥ 3 long, no filler — at most 6."""
    out = []
    for w in re.findall(r'[a-z0-9]{3,}', str(text or '').lower()):
        if w not in STOP and w not in out:
            out.append(w)
    return out[:6]


def clean(item):
    """The owner's input → a teaching, or None (unknown kind / empty text). Only an image from our own upload store is kept."""
    x = item if isinstance(item, dict) else {}
    kind, text = str(x.get('kind') or '').lower(), _txt(x.get('text'), MAX_TEXT)
    if kind not in KINDS or len(text) < 3:
        return None
    out = {'kind': kind, 'text': text}
    if isinstance(x.get('mint'), str) and _B58.match(x['mint']):
        out['mint'] = x['mint']
        out['sym'] = _txt(x.get('sym'), 16) or None
    if isinstance(x.get('img'), str) and _IMG.match(x['img']):
        out['img'] = x['img']
    if kind == 'narrative':
        out['words'] = words(text)
    return out


def add(state, item, now=None):
    t = clean(item)
    if not t:
        raise ValueError('write at least a few words, and pick NOTE · NARRATIVE · CHART')
    now = time.time() if now is None else now
    st = {'items': list((state or {}).get('items') or [])}
    st['items'] = ([{**t, 'id': f"t{int(now * 1000)}", 'at': round(now, 1)}] + st['items'])[:KEEP]
    return st


def remove(state, tid):
    return {'items': [t for t in (state or {}).get('items') or [] if t.get('id') != tid]}


def hits(state, symbol=None, mint=None, name=None):
    """The teachings about THIS coin: the owner's own words on its mint + narratives whose words are in its ticker / name."""
    hay = f"{symbol or ''} {name or ''}".lower()
    out = []
    for t in (state or {}).get('items') or []:
        if mint and t.get('mint') == mint:
            out.append(t)
        elif t.get('kind') == 'narrative' and hay.strip() and any(w in hay for w in t.get('words') or []):
            out.append(t)
    return out


def for_case(state, symbol=None, mint=None, name=None, n=6):
    """≤ n lines the model reads with this coin's case (the owner's words, labelled by kind)."""
    items = (state or {}).get('items') or []
    mine = hits(state, symbol, mint, name)
    charts = [t for t in items if t['kind'] == 'chart' and t not in mine][:2]
    notes = [t for t in items if t['kind'] == 'note' and not t.get('mint') and t not in mine][:2]
    lab = {'note': 'owner note', 'narrative': 'owner narrative', 'chart': 'owner chart lesson'}
    return [f"{lab[t['kind']]}{' on this coin' if t in mine else ''}: {t['text']}" for t in (mine + charts + notes)][:n]


def view(state, n=24):
    items = (state or {}).get('items') or []
    return {'items': items[:n], 'counts': {k: sum(1 for t in items if t['kind'] == k) for k in KINDS},
            'narratives': sorted({w for t in items if t['kind'] == 'narrative' for w in t.get('words') or []})[:24]}
