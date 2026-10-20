"""💬 FEEd REACTIONS (owner, 2026-10-19: "FEEd meta styled like X but better — vital features like comment, clean, not usage overloading"). Pure:
likes + comments on ANY timeline post (FEELESS, Pump, Telegram, Bluesky — keyed by the post's own id), one wallet one like, comments trimmed and
capped. The page reads counts for the posts on screen in ONE batched call; a thread's comments only when it is opened. Memory caps keep the
store small: 3,000 posts, 60 comments each, oldest-touched dropped first."""
import re

POSTS_MAX, COMMENTS_MAX, TEXT_MAX, IDS_MAX = 3000, 60, 280, 60
_ID = re.compile(r'^[A-Za-z0-9:_\-./]{1,96}$')


def ok_id(pid):
    return bool(_ID.match(str(pid or '')))


def _clean(t):
    t = ' '.join(re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', str(t or '')).split())
    if not t:
        raise ValueError('Write something first.')
    return t[:TEXT_MAX]


def _post(store, pid, now):
    if not ok_id(pid):
        raise ValueError('Unknown post.')
    p = store.setdefault('posts', {}).setdefault(pid, {'likes': [], 'comments': [], 'at': now})
    p['at'] = now
    if len(store['posts']) > POSTS_MAX:   # drop the least recently touched
        for k in sorted(store['posts'], key=lambda k: store['posts'][k].get('at', 0))[:len(store['posts']) - POSTS_MAX]:
            store['posts'].pop(k, None)
    return p


def like(store, wallet, pid, now):
    """Toggle this wallet's like. → (liked, count)."""
    p = _post(store, pid, now)
    if wallet in p['likes']:
        p['likes'].remove(wallet)
        return False, len(p['likes'])
    p['likes'].append(wallet)
    return True, len(p['likes'])


def comment(store, wallet, name, pid, text, now):
    p = _post(store, pid, now)
    c = {'by': wallet, 'name': str(name or '')[:32], 'text': _clean(text), 'at': now}
    p['comments'] = (p['comments'] + [c])[-COMMENTS_MAX:]
    return c


def counts(store, ids, me=None):
    """{id: {likes, comments, mine}} for up to 60 ids (unknown ids = zeros, nothing created)."""
    out = {}
    for pid in [i for i in (ids or []) if ok_id(i)][:IDS_MAX]:
        p = (store.get('posts') or {}).get(pid) or {}
        out[pid] = {'likes': len(p.get('likes') or []), 'comments': len(p.get('comments') or []), 'mine': bool(me and me in (p.get('likes') or []))}
    return out


def thread(store, pid):
    return list(((store.get('posts') or {}).get(pid) or {}).get('comments') or [])
