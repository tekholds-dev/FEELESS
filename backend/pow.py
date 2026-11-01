"""⛏ PROOF OF WORK (owner 2026-10-31: "ai must find a coin from the intake list, do research on the web — 5 steps per site and only 3 major vital
data pulls they must save per site, no saving random data — make it strong enough to keep all agents in order and unbreakable per AI model").

A colonized agent's PoW run, the same for every model (the rules are code, not a prompt it may ignore):
  1 COIN    the server hands it ONE coin from the FEELESS intake (never its own pick, never one it researched in the last 6 h)
  2 START   its window opens a DuckDuckGo search of the coin (DexScreener's search when DuckDuckGo walls it) — never a blank page
  3 SITES   at most SITES_MAX sites; on each, at most SITE_STEPS moves (open · click · scroll · search) — the 6th is refused before it is paid
  4 PULLS   on each site at most SITE_PULLS saved facts, each a VITAL (a fixed list) WITH a number or a yes/no — anything else is refused
  5 CALL    BUY / WATCH / AVOID + why; the Hive grades it an hour on against what the coin really did (honey)
The PoW is filed as a cell (its pulls ride along) and in the owner's cabinet. Pure; the agent loop + the service enforce it. Nothing trades.
"""
import re
from urllib.parse import quote_plus

SITE_STEPS = 5
SITE_PULLS = 3
SITES_MAX = 4
STEPS_MAX = SITE_STEPS * SITES_MAX + 2     # every site's moves + the start + the call
EVERY_MIN_S = 1800                         # a colonized agent starts a PoW at most every 30 min (a browser costs money)
VALUE_MAX = 80

# the only facts worth saving about a Solana coin (canonical → the words a model may use for it)
VITALS = {
    'price': ('price', 'usd price'),
    'market cap': ('market cap', 'mcap', 'mc', 'fdv', 'cap'),
    'liquidity': ('liquidity', 'liq', 'pool', 'pool size', 'tvl'),
    'volume 24h': ('volume 24h', 'volume', '24h volume', 'vol', 'vol 24h'),
    'holders': ('holders', 'holder count', 'number of holders'),
    'top 10 holders': ('top 10 holders', 'top holders', 'top 10', 'top10', 'concentration'),
    'mint authority': ('mint authority', 'mintable', 'mint'),
    'freeze authority': ('freeze authority', 'freeze'),
    'lp locked': ('lp locked', 'lp burned', 'lp lock', 'liquidity locked', 'lp'),
    'dev holds': ('dev holds', 'dev wallet', 'creator holds', 'deployer', 'dev'),
    'age': ('age', 'created', 'launched', 'pair age'),
    'buys vs sells': ('buys vs sells', 'buys/sells', 'txns', 'buy sell ratio', 'buyers vs sellers'),
    'risk score': ('risk score', 'rugcheck score', 'risk', 'score', 'warnings'),
    'socials': ('socials', 'twitter', 'x account', 'website', 'telegram'),
    'news': ('news', 'narrative', 'catalyst', 'mentions', 'sentiment'),
}
_ALIAS = {a: k for k, v in VITALS.items() for a in v}
FACTISH = re.compile(r'(?i)\d|\b(yes|no|none|renounced|revoked|enabled|disabled|burned|burnt|locked|unlocked|verified|unverified|active|inactive|danger|good|warn\w*)\b')
CALLS = ('BUY', 'WATCH', 'AVOID')

RULES = ('PROOF OF WORK — the rules every FEELESS agent follows, whatever its prompt: research ONE coin (given to you), '
         f'on at most {SITES_MAX} sites, at most {SITE_STEPS} moves on each (open, click, scroll, search). On every site save at most {SITE_PULLS} VITAL facts '
         'with action "pull" (label = one of: ' + ', '.join(VITALS) + '; value = the number or yes/no you READ on the page, short). '
         'Never save anything else, never a fact you did not read, never the same vital twice on a site. A FEELESS tool read counts as one site. '
         'You start on a search page; open the coin\'s own pages (THE COIN\'S PAGES below) — one site at a time, pull, move on. When you have the vitals, "answer" with say = "BUY|WATCH|AVOID — why in one line". '
         'It is graded an hour later on what the coin really did.')


def host_of(url):
    if str(url or '').startswith('feeless:'):   # a FEELESS tool read (our live chart + numbers) is a source like any site
        return 'feeless.app'
    h = str(url or '').split('://')[-1].split('/')[0].split('?')[0].lower()
    return h[4:] if h.startswith('www.') else h


def links(p):
    """The coin's own research pages — opened straight from the PoW, never hunted for on a search page."""
    m, pa = p.get('mint') or '', p.get('pair') or ''
    return [f'https://dexscreener.com/solana/{pa or m}', f'https://rugcheck.xyz/tokens/{m}', f'https://solscan.io/token/{m}', f'https://birdeye.so/token/{m}?chain=solana']


def new(coin, now):
    """A fresh PoW record for one intake coin."""
    c = coin or {}
    return {'mint': c.get('mint'), 'pair': c.get('pair'), 'sym': str(c.get('sym') or '?')[:16], 'at': round(now), 'sites': {}, 'call': None, 'why': ''}


def start_url(p, blocked=False):
    """🔎 where its window opens: a DuckDuckGo search of the coin; DexScreener's search of the mint when DuckDuckGo walls it."""
    if blocked:
        return 'https://dexscreener.com/solana/' + str(p.get('pair') or p.get('mint') or '')
    q = f"${p.get('sym')} {p.get('mint') or ''} solana token".strip()
    return 'https://html.duckduckgo.com/html/?q=' + quote_plus(q)


def goal(p):
    return (f"PROOF OF WORK on ${p['sym']} (Solana mint {p.get('mint')}, pair {p.get('pair')}). Research it on up to {SITES_MAX} sites, "
            f"pull up to {SITE_PULLS} vitals per site, then answer BUY / WATCH / AVOID with why.")


def site_done(p, url):
    """This site's work is used up: its vitals are saved or its moves are spent."""
    s = (p.get('sites') or {}).get(host_of(url))
    return bool(s) and (len(s['pulls']) >= SITE_PULLS or s['steps'] >= SITE_STEPS)


def next_link(p):
    """The engine drives the route (a small model once re-read the same FEELESS page until it was stopped): the coin's next page not yet
    researched, while sites are left. → url or None (then it must answer)."""
    if len(p.get('sites') or {}) >= SITES_MAX:
        return None
    return next((u for u in links(p) if host_of(u) not in (p.get('sites') or {}) and host_of(u) not in (p.get('walled') or [])), None)


def wall(p, url):
    """A bot-check / wall: never counted as one of its sites, never opened again in this PoW."""
    h = host_of(url); (p.get('sites') or {}).pop(h, None)
    p.setdefault('walled', []).append(h)


def _site(p, url):
    h = host_of(url)
    if not h or '.' not in h:
        return None
    return p['sites'].setdefault(h, {'steps': 0, 'pulls': []}) if h in p['sites'] or len(p['sites']) < SITES_MAX else None


def step(p, url):
    """One move on a site. → None when it may go, else why it is refused (before it is paid for). The search page is free."""
    h = host_of(url)
    if not h or '.' not in h or h.endswith('duckduckgo.com'):
        return None
    if h in (p.get('walled') or []):
        return f'{h} is behind a bot check — another site'
    s = p['sites'].get(h)
    if s is None and len(p['sites']) >= SITES_MAX:
        return f'{SITES_MAX} sites already researched — answer with the vitals you pulled'
    s = _site(p, url)
    if s['steps'] >= SITE_STEPS:
        return f'{SITE_STEPS} moves on {h} are used — open another site, or answer'
    s['steps'] += 1
    return None


def vital(label):
    k = re.sub(r'\s+', ' ', str(label or '').strip().lower().replace('_', ' '))
    return k if k in VITALS else _ALIAS.get(k)


def pull(p, url, label, value):
    """Save one vital read on the page at `url`. → (ok, why)."""
    v = vital(label)
    if not v:
        return False, f'"{label}" is not a vital — save only: ' + ', '.join(VITALS)
    val = re.sub(r'\s+', ' ', str(value or '')).strip()[:VALUE_MAX]
    if not val or not FACTISH.search(val):
        return False, f'a {v} needs the number or yes/no you read'
    h = host_of(url)
    if not h or '.' not in h or h.endswith('duckduckgo.com'):
        return False, 'open the coin\'s page first — a pull is a fact read ON a site (or in a FEELESS tool read)'
    s = _site(p, url)
    if s is None:
        return False, f'{SITES_MAX} sites already researched'
    if len(s['pulls']) >= SITE_PULLS:
        return False, f'{SITE_PULLS} vitals from {h} already saved — open another site, or answer'
    if any(x['label'] == v for x in s['pulls']):
        return False, f'{v} from {h} is already saved'
    s['pulls'].append({'label': v, 'value': val})
    return True, f'saved {v} = {val} from {h}'


def call_of(text):
    m = re.search(r'\b(BUY|WATCH|AVOID)\b', str(text or '').upper())
    return m.group(1) if m else 'WATCH'


def finish(p, answer):
    p['call'] = call_of(answer)
    p['why'] = re.sub(r'(?i)^\W*(buy|watch|avoid)\W*', '', str(answer or '').strip().splitlines()[0] if str(answer or '').strip() else '')[:200]
    return p


def pulls(p):
    return [{'site': h, **x} for h, s in (p.get('sites') or {}).items() for x in s.get('pulls') or []]


SAFETY = ('mint authority', 'freeze authority', 'lp locked', 'top 10 holders', 'dev holds', 'risk score')


def strength(p):
    """0–100: how much real work backs the call — sites with pulls, distinct vitals, safety vitals read, the same vital confirmed twice."""
    ps = pulls(p)
    if not ps:
        return 0
    sites = len({x['site'] for x in ps}); kinds = {x['label'] for x in ps}
    safe = len(kinds & set(SAFETY)); twice = sum(1 for k in kinds if sum(1 for x in ps if x['label'] == k) > 1)
    return min(100, sites * 15 + len(kinds) * 6 + safe * 6 + twice * 5)


def public(p):
    return {'sym': p.get('sym'), 'mint': p.get('mint'), 'pair': p.get('pair'), 'at': p.get('at'), 'call': p.get('call'), 'why': p.get('why'),
            'pulls': pulls(p), 'sites': len(p.get('sites') or {}), 'steps': sum(int(s.get('steps') or 0) for s in (p.get('sites') or {}).values()),
            'strength': strength(p), 'walled': list(p.get('walled') or []), 'by': p.get('by'), 'mind': p.get('mind'), 'honey': p.get('honey')}


def pick(coins, done_mints, min_liq=5000):
    """The next intake coin: a real pool, not researched lately; the intake's own rank first."""
    for c in sorted(coins or [], key=lambda r: -float(r.get('rank') or 0)):
        try:
            liq = float(c.get('liq') or 0)
        except (TypeError, ValueError):
            liq = 0
        if c.get('mint') and c.get('pair') and liq >= min_liq and c['mint'] not in (done_mints or set()):
            return {'mint': c['mint'], 'pair': c['pair'], 'sym': str(c.get('sym') or '?')[:16]}
    return None
