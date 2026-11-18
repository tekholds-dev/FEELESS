"""🔎 WHAT MATTERS ON A PAGE (owner 2026-11-17: "brains shouldnt be cycling through the same sites and dead searching, each site browsed by brain
should get a snapshot and a webscrape to help them identify whats on the page and whats vital").

A mind's read of a page used to be its raw screen: 30 menu links ("[link] NFL [link] NBA …") before one useful line. Here the page's scraped text
is cut to the lines that matter for its task: lines that name the task's own words (the teams, the coin) or carry the numbers a pick is made from
(odds, lines, records, percentages, injuries). Menus, buttons and one-word links are dropped. A page that is a bot wall is called dead, so neither
mind spends another step on it, and the host is remembered for a few hours so the next read skips it. Pure, except the small in-memory dead list.
"""
import re
import time

VITAL_MAX = 14          # lines handed to a mind per page
LINE_MAX = 220
DEAD_TTL_S = 6 * 3600   # a walled site is skipped by every read for 6 hours (in memory: a restart forgets it)
_DEAD = {}              # host → when it walled a read

WALL = re.compile(r"verifying your browser|vercel security checkpoint|security checkpoint|checking your browser|just a moment\.\.\.|"
                  r"verify you are human|are you a robot|captcha|access denied|request blocked|403 forbidden|enable javascript and cookies|"
                  r"unusual traffic|attention required|pardon our interruption|press (and|&) hold", re.I)
NUM = re.compile(r"(?<![\w.])[+\-−]\d+(\.\d)?\b|\b\d{1,3}\.\d\b|\b\d{1,3}(\.\d+)?%|\b\d{1,2}-\d{1,2}\b|\$\d|\b0?\.\d{2}\b|\b\d+(\.\d)?\s?(pts|reb|ast|ppg|rpg|apg|yds|td)\b", re.I)
FACT = re.compile(r"\b(injur|out\b|questionable|doubtful|probable|day-to-day|odds|spread|line\b|total|over|under|moneyline|favorite|underdog|"
                  r"predict|chance|record|streak|home|away|last \d|vs\.?|against|preview|matchup|lineup|starting|price|volume|liquidity|holders|"
                  r"market cap|mcap|fdv|yes\b|no\b)", re.I)
NAV = re.compile(r"^\[(link|button)\]\s*\S{1,18}$|^(sign in|log in|sign up|menu|more|search|home|watch|fantasy|tickets|skip to main content)$", re.I)
PROMO = re.compile(r"promo\s*code|\bbonus\b|sign[- ]?up offer|deposit \$|\b(get|trade|play|bet|spend) \$\d+.{0,40}\b(get|bonus|in)\b|odds boost|free bet|terms apply|21\+|gambling problem|1-800-gambler", re.I)
STOP = {'vs', 'v', 'at', 'the', 'a', 'an', 'and', 'of', 'on', 'for', 'to', 'win', 'wins', 'parlay', 'slip', 'legs', 'leg', 'team', 'best', 'pick',
        'picks', 'tonight', 'today', 'game', 'bid', 'bids', 'pob', 'make', 'start', 'this', 'with', 'from', 'read', 'your', 'site', 'sites'}


def words_of(goal, n=8):
    """The task's own words worth finding on a page (team names, the coin): 3+ letters, not filler. Pure."""
    out = []
    for w in re.findall(r"[a-z][a-z0-9.'-]{2,}", str(goal or '').lower()):
        w = w.strip(".'-")
        if w not in STOP and w not in out and not w.startswith('http') and '.' not in w:
            out.append(w)
    return out[:n]


def dead(text):
    """→ why this page is a wall (a bot check / CAPTCHA / blocked), or None. Pure."""
    m = WALL.search(str(text or '')[:3000])
    return f'a bot wall ("{m.group(0)}")' if m else None


def _lines(text):
    seen, out = set(), []
    for raw in re.split(r'[\n|]+', str(text or '')):
        t = re.sub(r'\s+', ' ', raw).strip(' ·-—')
        if len(t) < 4 or t.lower() in seen or NAV.search(t) or t.startswith(('ON SCREEN', 'PAGE SNAPSHOT')):
            continue
        seen.add(t.lower()); out.append(t[:LINE_MAX])
    return out


def vital(text, goal, n=VITAL_MAX):
    """The lines of a scraped page that matter for this task, best first: its own words AND a number score highest, then either one. Pure."""
    ws = words_of(goal)
    rows = []
    for i, t in enumerate(_lines(text)):
        low = t.lower()
        if PROMO.search(t) or (len(t.split()) <= 2 and not NUM.search(t) and not FACT.search(t)):   # an ad, or a bare name with nothing about it ("Markkanen Out" stays)
            continue
        hit = sum(1 for w in ws if w in low)
        score = hit * 2 + (2 if NUM.search(t) else 0) + (1 if FACT.search(t) else 0)
        if score >= 2 and (hit or NUM.search(t)):
            rows.append((score, i, t))
    top = sorted(rows, key=lambda r: (-r[0], r[1]))[:n]
    return [t for _, _, t in sorted(top, key=lambda r: r[1])]   # page order, so a table still reads top to bottom


def brief(text, goal, host=''):
    """The block a mind reads after the raw page: what matters here, or why the page is dead. Pure."""
    why = dead(text)
    if why:
        return f"\n\nDEAD PAGE: {host or 'this site'} is {why}. Do not come back: open a different site."
    rows = vital(text, goal)
    if not rows:
        return f"\n\nWHAT MATTERS ON {host or 'THIS PAGE'}: nothing about your task was found here. Open the page about it (search the site) or move on."
    return f"\n\nWHAT MATTERS ON {host or 'THIS PAGE'} (scraped from the whole page, for your task):\n" + '\n'.join(f'• {t}' for t in rows)


def note(text, goal):
    """A site's line for the proof's folder: its vital lines, not its menu. Pure."""
    rows = vital(text, goal, 8)
    return ' · '.join(rows)[:700] if rows else str(text or '')[:300]


def mark_dead(host, now=None):
    if host:
        _DEAD[host] = now or time.time()


def is_dead(host, now=None):
    at = _DEAD.get(host)
    return bool(at and (now or time.time()) - at < DEAD_TTL_S)


def dead_hosts(now=None):
    now = now or time.time()
    return {h for h, at in _DEAD.items() if now - at < DEAD_TTL_S}
