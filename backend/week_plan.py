"""🗓 POC-PLAY items 4 + 5 (owner 2026-11-13): a 7-day posting board (Mon–Sun × platform) and brain-made week SCENARIOS — each mind writes one
whole week in a different style ("launch week", "steady drip", "hype into event"), each scenario is filed as its own PoC proof and graded
like any other. Nothing is posted by this (posting is the OAuth step). Pure: prompts in, checked plans out."""
import json
import re

DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
PLATFORMS = ('x', 'instagram', 'tiktok', 'youtube', 'linkedin', 'threads')
STYLES = (('launch', 'Launch week', 'build to one big reveal mid-week, then proof and follow-up'),
          ('drip', 'Steady drip', 'one calm post a day, same time, the habit is the point'),
          ('hype', 'Hype into event', 'quiet start, rising pace, peak on the event day (Fri/Sat), a thank-you after'))
MAX_POSTS = 21
CAPTION = 280

SYS = """You plan ONE week of social posts for the owner's product. Style: {style} — {how}.
Return ONLY JSON: {{"idea": "one line: the week's story", "posts": [{{"day": "Mon", "platform": "x", "time": "09:30", "caption": "the post", "media": "a media id from the list or empty"}}]}}
Rules: days are Mon Tue Wed Thu Fri Sat Sun. Platforms: {platforms}. 5 to {most} posts in the week, at most 3 a day. Captions under {cap} characters,
written to post as-is (no placeholders, no made-up numbers, prices or quotes). Use a media id only from the list."""


def prompt(style_key, topic, media):
    """→ (system, user) for one mind writing one scenario. `media` = [{'id', 'kind', 'prompt'}] made in this folder."""
    key, name, how = next(s for s in STYLES if s[0] == style_key)
    lines = '\n'.join(f"- {m['id']} ({m.get('kind') or 'image'}): {str(m.get('prompt') or '')[:80]}" for m in media or []) or '- none yet (leave media empty)'
    return (SYS.format(style=name, how=how, platforms=', '.join(PLATFORMS), most=MAX_POSTS, cap=CAPTION),
            f"Product / topic: {topic or 'the owner’s product'}\nMedia made in this folder:\n{lines}")


def _hhmm(t):
    m = re.match(r'^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*$', str(t or ''), re.I)
    if not m:
        return '09:00'
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if m.group(3):
        h = h % 12 + (12 if m.group(3).lower() == 'pm' else 0)
    return f'{min(h, 23):02d}:{min(mi, 59):02d}'


def clean(d, media_ids=()):
    """A plan (parsed or edited by the owner) → the checked plan: known days/platforms, ≤3 a day, ≤21 posts, captions cut, unknown media
    dropped, sorted by day then time. Raises ValueError when nothing usable is left. Pure."""
    ids = {str(m) for m in media_ids or []}; per = {}; out = []
    for p in (d or {}).get('posts') or []:
        if not isinstance(p, dict):
            continue
        day = str(p.get('day') or '')[:3].title(); plat = str(p.get('platform') or '').lower().strip()
        plat = {'twitter': 'x', 'ig': 'instagram', 'yt': 'youtube'}.get(plat, plat)
        cap = re.sub(r'\s+', ' ', str(p.get('caption') or '')).strip()[:CAPTION]
        if day not in DAYS or plat not in PLATFORMS or not cap or per.get(day, 0) >= 3 or len(out) >= MAX_POSTS:
            continue
        per[day] = per.get(day, 0) + 1
        med = str(p.get('media') or '')
        out.append({'day': day, 'platform': plat, 'time': _hhmm(p.get('time')), 'caption': cap, **({'media': med} if med in ids else {})})
    if not out:
        raise ValueError('No usable posts in that week plan.')
    out.sort(key=lambda p: (DAYS.index(p['day']), p['time']))
    return {'idea': re.sub(r'\s+', ' ', str((d or {}).get('idea') or '')).strip()[:200], 'posts': out}


def parse(raw, media_ids=()):
    """A mind's answer → a checked plan (the first JSON object in it). Raises ValueError. Pure."""
    m = re.search(r'\{.*\}', str(raw or ''), re.S)
    if not m:
        raise ValueError('The mind did not answer with a plan.')
    try:
        d = json.loads(m.group(0))
    except ValueError:
        raise ValueError('The plan was not valid JSON.')
    return clean(d, media_ids)


def board(plan):
    """→ {platform: {day: [posts]}} for the grid (only platforms the plan uses, in PLATFORMS order). Pure."""
    used = [p for p in PLATFORMS if any(x['platform'] == p for x in plan.get('posts') or [])]
    return {p: {d: [x for x in plan['posts'] if x['platform'] == p and x['day'] == d] for d in DAYS} for p in used}
