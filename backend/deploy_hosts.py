"""🚀 Go live: where a built page can be hosted, cheapest first (owner 2026-11-12: "user access to choose different deployment providers, best costs and cheap too").

Every row's numbers come from that host's own pricing or limits page, read 2026-11-12. Once a day we read each page again and keep a row
"checked" only while the sentence its numbers come from is still there; a page that changed or did not answer says so instead of a stale promise.
Nothing is deployed from here and no account is made: the user takes the page's zip to the host they pick.
"""
import asyncio
import html
import re
import time

import httpx
from fastapi import APIRouter

router = APIRouter()

TTL = 86400
UA = {'User-Agent': 'Mozilla/5.0 (FEELESS go-live check)', 'Accept-Language': 'en'}

# freeGB: data a month the free plan serves (None = static traffic is not metered). paid: the first paid step, $ a month.
HOSTS = [
    {'id': 'cloudflare', 'name': 'Cloudflare Pages', 'freeGB': None, 'paid': 5, 'maxMB': 25, 'maxNote': '25 MiB a file, 20,000 files',
     'free': 'Static traffic free and unlimited · 500 builds a month', 'best': 'Most traffic for $0',
     'steps': ['dash.cloudflare.com › Workers & Pages › Create › Pages', 'Upload assets › drop the unzipped folder', 'Live on *.pages.dev in about a minute'],
     'open': 'https://dash.cloudflare.com/?to=/:account/pages/new/upload',
     'src': 'https://developers.cloudflare.com/pages/functions/pricing/', 'proof': r'requests to static assets are free and unlimited'},
    {'id': 'surge', 'name': 'Surge', 'freeGB': None, 'paid': 30, 'maxMB': None, 'maxNote': None,
     'free': 'No bandwidth billing · custom domain + HTTPS free', 'best': 'One command, no dashboard',
     'steps': ['Unzip the page', 'In that folder run: npx surge', 'Pick a name.surge.sh, done'],
     'open': 'https://surge.sh/help/getting-started-with-surge',
     'src': 'https://surge.sh/pricing', 'proof': r'no bandwidth billing'},
    {'id': 'github', 'name': 'GitHub Pages', 'freeGB': 100, 'paid': None, 'maxMB': 1024, 'maxNote': '1 GB a site, 10 builds an hour',
     'free': '100 GB a month (soft) · public repo', 'best': 'Already on GitHub',
     'steps': ['New public repo › Add file › Upload files (the unzipped folder)', 'Settings › Pages › Deploy from branch: main', 'Live on you.github.io/repo'],
     'open': 'https://github.com/new',
     'src': 'https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits', 'proof': r'soft bandwidth limit of 100 GB per month'},
    {'id': 'vercel', 'name': 'Vercel', 'freeGB': 100, 'paid': 20, 'maxMB': None, 'maxNote': None,
     'free': '100 GB a month · 1M requests', 'best': 'Next step: server code',
     'steps': ['Unzip the page', 'In that folder run: npx vercel', 'Answer its questions, live on *.vercel.app'],
     'open': 'https://vercel.com/new',
     'src': 'https://vercel.com/pricing', 'proof': r'Fast Data Transfer 100 GB / month included'},
    {'id': 'netlify', 'name': 'Netlify', 'freeGB': 15, 'paid': 9, 'maxMB': None, 'maxNote': None,
     'free': '300 credits a month (a GB costs 20 → up to 15 GB)', 'best': 'Drag and drop',
     'steps': ['app.netlify.com/drop', 'Drop the unzipped folder', 'Live on *.netlify.app'],
     'open': 'https://app.netlify.com/drop',
     'src': 'https://www.netlify.com/pricing/', 'proof': r'300 credit limit'},
    {'id': 'render', 'name': 'Render', 'freeGB': 5, 'paid': 25, 'maxMB': None, 'maxNote': None,
     'free': 'Static sites free · 5 GB a month', 'best': 'Same place as a backend',
     'steps': ['Put the folder in a GitHub repo', 'render.com › New › Static Site › pick the repo', 'Live on *.onrender.com'],
     'open': 'https://dashboard.render.com/select-repo?type=static',
     'src': 'https://render.com/pricing', 'proof': r'5 GB of bandwidth included'},
]
_seen: dict = {}   # id → (at, state, httpStatus)
_client = None


def _http():
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=12, headers=UA, follow_redirects=True)
    return _client


def page_text(raw):
    """A page's words, tags and scripts out. Pure."""
    s = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', raw or '', flags=re.S | re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s)))


def rank(rows, page_mb=0.0):
    """Cheapest first: $0 plans before paid-only, then most free traffic (unmetered first), then the cheapest paid step.
    Each row gains visits = free page loads a month for a page this size, and fits = False when the page is over a host's cap. Pure."""
    out = []
    for h in rows:
        r = dict(h)
        mb = max(float(page_mb or 0), 0.0)
        r['fits'] = not (r.get('maxMB') and mb > r['maxMB'])
        r['visits'] = None if r['freeGB'] is None or mb <= 0 else int(r['freeGB'] * 1024 / mb)
        out.append(r)
    big = float('inf')
    return sorted(out, key=lambda r: (not r['fits'], r['state'] != 'checked', -(big if r['freeGB'] is None else r['freeGB']), r['paid'] if r['paid'] is not None else 0))


async def _check(h):
    hit = _seen.get(h['id'])
    if hit and time.time() - hit[0] < TTL:
        return hit
    try:
        r = await _http().get(h['src'])
        state = 'checked' if r.status_code == 200 and re.search(h['proof'], page_text(r.text), re.I) else 'changed'
        code = r.status_code
    except httpx.HTTPError:
        state, code = (hit[1], hit[2]) if hit else ('unread', 0)
    _seen[h['id']] = (time.time(), state, code)
    return _seen[h['id']]


@router.get('/api/reputation/deploy/hosts')
async def hosts(mb: float = 0):
    """🚀 Hosts for a built page, cheapest first, each re-checked against its own pricing page once a day → {hosts, checkedAt}."""
    seen = await asyncio.gather(*(_check(h) for h in HOSTS))
    rows = [{**{k: v for k, v in h.items() if k != 'proof'}, 'state': s[1], 'checkedAt': int(s[0])} for h, s in zip(HOSTS, seen)]
    return {'hosts': rank(rows, mb), 'checkedAt': int(min(s[0] for s in seen)), 'mb': round(mb, 3)}
