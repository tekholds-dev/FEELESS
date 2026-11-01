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
import random
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
    every = [f'https://dexscreener.com/solana/{pa or m}', f'https://rugcheck.xyz/tokens/{m}', f'https://solscan.io/token/{m}', f'https://birdeye.so/token/{m}?chain=solana',
             f'https://jup.ag/tokens/{m}', f'https://pump.fun/coin/{m}', f'https://www.coingecko.com/en/search?query={m}']
    if p.get('order'):   # 🎲 the engine's order for this round (site_order): winners first, the rest shuffled, last folders' sites skipped
        rank = {h: i for i, h in enumerate(p['order'])}
        every = sorted([u for u in every if host_of(u) in rank], key=lambda u: rank[host_of(u)]) or every
    used = set(p.get('used') or ())   # 🔁 a new round never re-opens a site an earlier round of this coin already read (owner 2026-11-01)
    fresh = [u for u in every if host_of(u) not in used]
    if len(fresh) < 3:   # 🎲 owner 2026-11-02 ("not just rug checker"): top up from the OTHER unused sites, never a used one while any is left
        rest = [u for u in _all_links(p) if host_of(u) not in used and u not in fresh]; random.shuffle(rest); fresh += rest
    return fresh or every


def _all_links(p):
    m, pa = p.get('mint') or '', p.get('pair') or ''
    return [f'https://dexscreener.com/solana/{pa or m}', f'https://rugcheck.xyz/tokens/{m}', f'https://solscan.io/token/{m}', f'https://birdeye.so/token/{m}?chain=solana',
            f'https://jup.ag/tokens/{m}', f'https://pump.fun/coin/{m}', f'https://www.coingecko.com/en/search?query={m}']


HOSTS = ('dexscreener.com', 'rugcheck.xyz', 'solscan.io', 'birdeye.so', 'jup.ag', 'pump.fun', 'coingecko.com')
RECENT_FOLDERS = 2      # its last 2 folders' sites are skipped next time (owner 2026-11-01: "they can't check the same sites from the last researches")


def site_order(recent, wins, rnd=None):
    """🎲 Where a research round goes: the sites a WINNING folder used come first (they earned it), every other site in a random order,
    and the sites its last RECENT_FOLDERS folders read are left out — unless that leaves fewer than 3. → list of hosts."""
    import random as _r
    rnd = rnd or _r.Random()
    win = [h for h in HOSTS if h in set(wins or ())]
    rest = [h for h in HOSTS if h not in win]; rnd.shuffle(rest)
    fresh = [h for h in rest if h not in set(recent or ())]
    if len(win) + len(fresh) < 3:
        fresh += [h for h in rest if h not in fresh][:3 - len(win) - len(fresh)]
    return win + fresh


def recent_mints(folders, n=10):
    """Every coin its last n folders held — a new folder never gathers one of them again (owner 2026-11-01: no coin tracked twice)."""
    return {c.get('mint') for f in (folders or [])[-n:] for c in (f.get('coins') or []) if c.get('mint')}


def site_memory(folders):
    """(sites its last RECENT_FOLDERS researched folders read, sites every WINNING folder read) from the folders' snapshots + vitals."""
    def hosts(f):
        return {x.get('site') for x in f.get('shots') or []} | {x.get('site') for v in (f.get('vitals') or {}).values() for x in v or []}
    done = [f for f in folders or [] if hosts(f)]
    recent = set().union(*[hosts(f) for f in done[-RECENT_FOLDERS:]]) if done else set()
    wins = set().union(*[hosts(f) for f in done if (f.get('pnlPct') or 0) > 0]) if done else set()
    return {h for h in recent if h in HOSTS}, {h for h in wins if h in HOSTS}


STEPS_RANGE = (3, 8)   # 🎲 owner 2026-11-02: each research round draws its moves per site at random between 3 and 8


def new(coin, now, rnd=None):
    """A fresh PoW record for one intake coin (its moves per site drawn at random, 3–8)."""
    c = coin or {}
    return {'mint': c.get('mint'), 'pair': c.get('pair'), 'sym': str(c.get('sym') or '?')[:16], 'at': round(now), 'sites': {}, 'call': None, 'why': '',
            'siteSteps': (rnd or random).randint(*STEPS_RANGE)}


def steps_of(p, h=None):
    """A site's own move limit — drawn at random (3–8) the first time the round opens that site (owner 2026-11-02: "random for different sites too")."""
    s = ((p or {}).get('sites') or {}).get(h) if h else None
    return int((s or {}).get('max') or (p or {}).get('siteSteps') or SITE_STEPS)


def budget(p):
    """The round's whole step budget: the most every site could draw + the start + the call."""
    return STEPS_RANGE[1] * SITES_MAX + 2


def start_url(p, blocked=False):
    """🔎 where its window opens: a DuckDuckGo search of the coin; DexScreener's search of the mint when DuckDuckGo walls it."""
    if blocked:
        return 'https://dexscreener.com/solana/' + str(p.get('pair') or p.get('mint') or '')
    q = f"${p.get('sym')} {p.get('mint') or ''} solana token".strip()
    return 'https://html.duckduckgo.com/html/?q=' + quote_plus(q)


def goal(p):
    return (f"PROOF OF WORK on ${p['sym']} (Solana mint {p.get('mint')}, pair {p.get('pair')}). Research it on up to {SITES_MAX} sites (FEELESS + 3), "
            f"each site has its own random 3–8 moves, pull up to {SITE_PULLS} vitals per site — only facts NOT already known"
            + (f" (known: {', '.join(p['known'])})" if p.get('known') else '') + ", then answer BUY / WATCH / AVOID with why."
            + (f" YOUR PLAN for this coin: {p['plan']}" if p.get('plan') else ''))


def site_done(p, url):
    """This site's work is used up: its vitals are saved or its moves are spent."""
    s = (p.get('sites') or {}).get(host_of(url))
    return bool(s) and (len(s['pulls']) >= SITE_PULLS or s['steps'] >= int(s.get('max') or steps_of(p)))


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
    if h not in p['sites'] and len(p['sites']) >= SITES_MAX:
        return None
    return p['sites'].setdefault(h, {'steps': 0, 'pulls': [], 'max': random.randint(*STEPS_RANGE)})   # 🎲 this site's own moves, drawn once and kept


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
    if s['steps'] >= int(s.get('max') or steps_of(p)):
        return f"{int(s.get('max') or steps_of(p))} moves on {h} are used — open another site, or answer"
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
    if v in set(p.get('known') or ()):   # 🧹 owner 2026-11-02: no duplicates — an earlier round already filed this fact for the coin
        return False, f'{v} is already in this coin\'s folder — read something NEW: ' + ', '.join(k for k in VITALS if k not in set(p.get('known') or ()))[:200]
    norm = re.sub(r'[^a-z0-9.%]', '', val.lower())
    dup = next((h2 for h2, s2 in (p.get('sites') or {}).items() for x in s2['pulls'] if x['label'] == v and re.sub(r'[^a-z0-9.%]', '', x['value'].lower()) == norm), None)
    if dup:   # 🧹 owner 2026-11-02: duplicate info is deleted — the same vital with the same value from another site adds nothing
        return False, f'{v} = {val} is already saved from {dup} — read something new'
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
            'moves': {h: {'max': s.get('max'), 'used': s.get('steps')} for h, s in (p.get('sites') or {}).items()},
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


# ═══ PoW v2 — THE COLONY PoW LOOP (owner 2026-11-01, hard-coded for every trader agent; FeeCat later):
# a NEW PoW FOLDER starts empty → the server gathers 4 coins (2 from the FEELESS intake, 1 from Pump, 1 from DexScreener's most-boosted Solana
# coins) → the minds each pick 1 of the 4 (both minds must AGREE; one round of discussion if they don't; still apart = no buy) → it buys that
# ONE coin on FEELESS through the guarded order path → the LOOP: the watcher reads the chart ≥ 3 min, the researcher runs a PoW on the CA
# (3 trusted sites, ≤ 5 moves, ≤ 3 vitals each) for ≤ 2.5 min, then the watcher decides HOLD / SELL with both reads → until it sells.
# Hard stops so it never loops forever: −25 % / +60 % / 60 min / 6 rounds sell without asking. A won folder goes to the colony with its share.
GATHER = (('intake', 2), ('pump', 1), ('dex', 1))
WATCH_S = 180
RESEARCH_S = 150
ROUNDS_MAX = 6
HOLD_MAX_S = 3600
STOP_PCT, TAKE_PCT = -25.0, 60.0
REST_S = 300                      # between two folders
ROUND_USD = 0.03                  # 💲 one coin's research ceiling (owner 2026-11-02: $0.03 a coin ≈ 15 calls at ~$0.002 = FEELESS + 3 sites × 3–8 moves; $0.006 cut rounds after ~2 sites)
CHECKS = (15, 30, 60)             # ⏱ live-trade checks after the buy: +15 s, then +30 s, then every 60 s (owner 2026-11-01)
HOT_TICK_S = 5                    # the engine's light pass while a folder holds a coin
SIGN_WAIT_S = 600                 # a real buy waits this long for its wallet, then the folder closes and the order is withdrawn
MIN_LIQ = 5000
REFILL_ROUNDS = 3                 # an unsafe coin is replaced by a fresh one (same source first) up to 3 rounds, so 4 SAFE coins get researched
FOLDERS_KEEP = 30
SRC_LABEL = {'intake': 'FEELESS intake', 'pump': 'Pump', 'dex': 'DexScreener'}

POOL = 8            # 🧺 the engine vets up to 8 coins (every buy guard + the safety check) — the minds only ever see coins that can be bought
PROPOSE_N, SPLIT_N = 3, 2
PROPOSE_SYS = ('You are {name}, one of a FEELESS trader agent\'s two minds, opening a PROOF OF WORK folder. Below are {n} Solana coins the engine already '
               'vetted (all can be bought on FEELESS), with their FEELESS live reads and any PRIOR PoW your colony filed on them. PROPOSE the 3 you most want '
               'researched for a buy in the next hour, and why.{partner} Answer ONLY JSON: {{"picks": [1, 2, 3], "why": "<= 25 words"}}.')
SPLIT_SYS = ('You are {name}. Your colony shortlisted these coins (both minds proposed them). Take the {k} YOU will research{taken} and write how you will '
             'investigate each (which sites, which vitals prove or kill it). Answer ONLY JSON: {{"picks": [1, 2], "plan": "<= 30 words"}}.')
CHOOSE_SYS = ('You are {name}, one of a FEELESS trader agent\'s two minds, working a PROOF OF WORK folder. Below are 4 Solana coins your colony '
              'gathered (FEELESS live reads). Pick the ONE most likely to rise in the next hour without rugging; your partner picks too and you must '
              'agree before anything is bought. YOU set the trade (it runs while the owner sleeps): size in SOL (max {cap} — its budget), take profit % and '
              'stop loss %. Profit funds your own model credit and grows your capital — protect it. Answer ONLY JSON: '
              '{{"pick": 1-4, "size_sol": 0.0, "tp_pct": 0, "sl_pct": 0, "why": "<= 20 words, the numbers"}}.{partner}')
DECIDE_SYS = ('You are {name}, the CHART WATCHER of a FEELESS trader agent holding ${sym}. Read the chart samples, your partner\'s research and '
              'the P/L, then decide. Answer ONLY JSON: {{"action": "HOLD|SELL", "say": "<= 20 words to your partner — what the chart shows"}}.')


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def is_pump(c):
    return bool({'pulse', 'migr'} & set(c.get('sources') or [])) or str(c.get('mint') or '').endswith('pump')


def gather(intake, dex, done=(), need_safe=0):
    """The folder's 4 coins: 2 FEELESS intake (best rank, real pools), 1 Pump, 1 DexScreener boost. → list (may be short when a source is dry).
    need_safe=n: REPLACEMENT candidates for n unsafe coins — the next ones of every source; the caller vets them and swaps safe ones in."""
    done = set(done or ()); got = []; seen = set(done)
    ok = lambda c: c.get('mint') and c.get('pair') and c['mint'] not in seen and _f(c.get('liq')) >= MIN_LIQ   # noqa: E731
    rows = sorted([c for c in intake or [] if ok(c)], key=lambda c: -_f(c.get('rank')))
    if need_safe:
        pick_ = [(c, 'pump' if is_pump(c) else 'intake') for c in rows][:need_safe * 4] + [(c, 'dex') for c in (dex or []) if ok(c)][:need_safe * 2]
        return [{'mint': c['mint'], 'pair': c['pair'], 'sym': str(c.get('sym') or '?')[:16], 'src': s_, 'liq': _f(c.get('liq')), 'mc': _f(c.get('mc')), 'ch': c.get('ch')} for c, s_ in pick_]

    def take(c, src):
        seen.add(c['mint']); got.append({'mint': c['mint'], 'pair': c['pair'], 'sym': str(c.get('sym') or '?')[:16], 'src': src,
                                          'liq': _f(c.get('liq')), 'mc': _f(c.get('mc')), 'ch': c.get('ch')})
    for c in [c for c in rows if not is_pump(c)][:2] or rows[:2]:
        take(c, 'intake')
    p = next((c for c in rows if is_pump(c) and c['mint'] not in seen), None)
    if p:
        take(p, 'pump')
    d = next((c for c in dex or [] if ok(c)), None)
    if d:
        take(d, 'dex')
    return got[:4]


def folder_new(n, coins, now, minds):
    import time as _t
    return {'id': f"pow{int(now)}", 'n': n, 'name': f"PoW #{n} · {_t.strftime('%b %d · %H:%M UTC', _t.gmtime(now))}", 'at': round(now),
            'coins': coins, 'minds': max(1, min(2, int(minds or 1))), 'phase': 'choose', 'phaseAt': round(now), 'picks': {}, 'talk': [],
            'disc': 0, 'rounds': 0, 'chart': [], 'research': [], 'pick': None, 'status': 'open', 'plan': plan_of(minds)}


def plan_of(minds):
    """The folder's steps, said in the chat (owner 2026-11-02: a 5-step agreement)."""
    two = int(minds or 1) > 1
    return [f"the engine vets up to {POOL} coins (every buy guard + safety) — only buyable coins reach the minds",
            ("A proposes 3, B proposes 3 OTHER coins — 6 on the table (each sees the coin's prior PoW)" if two else "it proposes 3, then 3 more"),
            ("each mind takes 2 of the shortlist + writes how it will investigate them" if two else "it takes 4 of the shortlist + its plan"),
            f"each researches its own coins: FEELESS + 3 sites, {STEPS_RANGE[0]}–{STEPS_RANGE[1]} moves a site, ≤ {SITE_PULLS} vitals a site, duplicates dropped",
            "every coin is checked again → 3 turns decide the ONE (size, TP, SL) → bought on FEELESS → checks until it sells → filed forever"]


def merge_vitals(old, new):
    """A coin's folder keeps ONE row per fact: a new read replaces the old value and adds its site to the ones that confirmed it."""
    out = {x['label']: dict(x) for x in old or []}
    for x in new or []:
        o = out.get(x['label'])
        sites = list(dict.fromkeys(((o or {}).get('sites') or ([o['site']] if o else [])) + [x['site']]))
        out[x['label']] = {**x, 'sites': sites}
    return list(out.values())


def parse_picks(text, n, k):
    """{"picks": [..]} → up to k distinct 0-based indices (< n); words like "1, 3 and 4" also count."""
    import json as _j
    t = str(text or ''); m = re.search(r'\{.*\}', t, re.S)
    try:
        d = _j.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    raw = d.get('picks') if isinstance(d.get('picks'), list) else re.findall(r'\b(\d{1,2})\b', str(d.get('picks') or t))
    out = []
    for x in raw:
        try:
            i = int(x) - 1
        except (TypeError, ValueError):
            continue
        if 0 <= i < n and i not in out:
            out.append(i)
    return out[:k], str(d.get('plan') or d.get('why') or '')[:220]


def split_of(shortlist, mine, theirs, k=SPLIT_N):
    """Each mind's k coins of the shortlist, never the same coin twice; a mind that picked too few gets the strongest left."""
    got = [i for i in mine if i in shortlist and i not in theirs][:k]
    got += [i for i in shortlist if i not in got and i not in theirs][:k - len(got)]
    return got


# 🗄 THE PoW ARCHIVE (owner 2026-11-02: "all PoW filings stay in the FEELESS database FOREVER, so agents can always search and review a coin from
# a prior PoW"): one append-only row per researched coin + one per traded outcome — never trimmed, searchable by mint or $symbol
def archive_row(kind, cat_id, f, coin, now, **extra):
    return {'kind': kind, 'at': round(now), 'cat': cat_id, 'folder': f.get('id'), 'name': f.get('name'), 'mint': coin.get('mint'), 'sym': coin.get('sym'), **extra}


def archive_find(rows, q, limit=20):
    q = str(q or '').strip().lstrip('$').lower()
    if not q:
        return list(reversed(rows))[:limit]
    return [r for r in reversed(rows) if q == str(r.get('mint') or '').lower() or q == str(r.get('sym') or '').lower()][:limit]


def archive_brief(rows):
    """A coin's prior PoW in one line for the minds: how often, what was read, how its trades went."""
    if not rows:
        return ''
    res = [r for r in rows if r.get('kind') == 'research']; out = [r for r in rows if r.get('kind') == 'outcome']
    vit = {}
    for r in res:
        for x in r.get('vitals') or []:
            vit.setdefault(x.get('label'), x.get('value'))
    s = f"PRIOR PoW: researched {len(res)}× " + (' · '.join(f'{k} {v}' for k, v in list(vit.items())[:4]) if vit else '')
    if out:
        s += ' · traded ' + ', '.join(f"{o.get('pnlPct'):+.1f}%" if o.get('pnlPct') is not None else 'no fill' for o in out[:3])
    return s


def parse_pick(text, n=4):
    import json as _j
    t = str(text or ''); m = re.search(r'\{.*\}', t, re.S)
    try:
        d = _j.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    try:
        k = int(d.get('pick'))
    except (TypeError, ValueError):
        k = None
    if not k:   # a model that answers in words: "I pick 2" / "pick: #3"
        m2 = re.search(r'(?i)pick\D{0,12}([1-4])\b', t)
        k = int(m2.group(1)) if m2 else None
    return (k - 1 if k and 1 <= k <= n else None), str(d.get('why') or t.strip())[:160]


def trade_of(text, cap):
    """The size / TP / SL a mind set — clamped to sane, guarded bounds. → {'sol', 'tp', 'sl'}"""
    import json as _j
    m = re.search(r'\{.*\}', str(text or ''), re.S)
    try:
        d = _j.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    cap = max(0.005, _f(cap) or 0.05)
    return {'sol': round(min(cap, max(0.005, _f(d.get('size_sol')) or cap)), 4), 'tp': round(min(150.0, max(10.0, _f(d.get('tp_pct')) or TAKE_PCT)), 1),
            'sl': round(min(40.0, max(5.0, abs(_f(d.get('sl_pct'))) or abs(STOP_PCT))), 1)}


def agree_trade(trades):
    """Both minds' trades → one: the SMALLER size, the TIGHTER stop, the average target."""
    ts = [t for t in trades if t]
    if not ts:
        return None
    return {'sol': min(t['sol'] for t in ts), 'sl': min(t['sl'] for t in ts), 'tp': round(sum(t['tp'] for t in ts) / len(ts), 1)}


def engine_pick(coins):
    """When a mind stays silent the folder never waits forever: the strongest coin by the numbers (pool, then the intake's rank)."""
    return max(range(len(coins)), key=lambda k: (_f(coins[k].get('liq')), _f(coins[k].get('mc')))) if coins else None


def agree(picks, minds):
    """Both minds on the same coin (or the one mind's pick). → index or None."""
    vals = [picks.get(str(i)) for i in range(minds)]
    if any(v is None for v in vals):
        return None
    return vals[0] if len(set(vals)) == 1 else None


def pnl_pct(entry, px):
    return (px / entry - 1) * 100 if entry > 0 and px > 0 else 0.0


def hard_exit(entry, px, bought_at, now, rounds, tp=TAKE_PCT, sl=-STOP_PCT):
    """The loop's hard stops (the minds' own TP / SL) — they sell without asking. → why, or None."""
    p = pnl_pct(entry, px)
    if entry > 0 and px > 0 and p <= -abs(sl):
        return f'stop: {p:.0f}%'
    if entry > 0 and px > 0 and p >= tp:
        return f'take profit: +{p:.0f}%'
    if now - bought_at >= HOLD_MAX_S:
        return f'held {HOLD_MAX_S // 60} min — the folder closes'
    return None


AGREE_SYS = ('You are {name}, the partner mind of a FEELESS trader agent holding ${sym}. Your partner just read the live chart and says: {said}. '
             'Agree, or override with what YOU read. Answer ONLY JSON: {{"action": "HOLD|SELL", "say": "<= 14 words"}}.')
COIN_TALK_SYS = ('You are {name}. Your partner just researched ${sym} on 3 sites: {vitals}. In ONE line (<= 16 words): is it worth buying, and why? '
                 'Answer ONLY JSON: {{"say": "..."}}.')


def parse_decide(text):
    """A mind's HOLD / SELL: its JSON "action" when it gave one, else its FIRST word — never a 'sell' inside a sentence
    (live 2026-11-02: "No signal to sell; holding for TP" was read as SELL and the coin was sold)."""
    t = str(text or '').upper()
    m0 = re.search(r'"ACTION"\s*:\s*"(HOLD|SELL)"', t)
    act = m0.group(1) if m0 else ('SELL' if re.match(r'\W*SELL\b', t) else 'HOLD')
    m = re.search(r'"say"\s*:\s*"([^"]{0,200})', str(text or ''))
    return act, (m.group(1) if m else str(text or '').strip()[:160])


def chart_line(samples):
    """The watcher's chart read: first → last, high / low, last 6 moves (% vs the entry)."""
    if not samples:
        return 'no samples yet'
    px = [s['px'] for s in samples if s.get('px')]
    if not px:
        return 'no price yet'
    return f"{len(px)} samples · first {px[0]:.6g} → last {px[-1]:.6g} · high {max(px):.6g} · low {min(px):.6g} · last moves " + \
        ' '.join(f"{pnl_pct(px[i - 1], px[i]):+.1f}%" for i in range(max(1, len(px) - 6), len(px)))


def folder_public(f):
    keep = ('id', 'n', 'name', 'at', 'coins', 'minds', 'phase', 'pick', 'talk', 'rounds', 'status', 'why', 'entry', 'exit', 'pnlPct', 'pnlSol', 'sym',
            'boughtAt', 'soldAt', 'real', 'shared', 'research', 'picks', 'whys', 'base', 'pair', 'mint', 'propose', 'sol', 'plan', 'entryUsd', 'tp', 'sl', 'shots', 'vitals', 'scout', 'scoutDone', 'rMint', 'rMind', 'scouted', 'fav', 'checks', 'nextAt', 'cost', 'spend', 'report', 'grade', 'dropped', 'proposed', 'shortlist', 'owner', 'plans', 'moves')
    out = {k: f.get(k) for k in keep if k in f}
    if f.get('chart'):   # the live price the watcher reads (its P/L on the monitor)
        out['now'] = f['chart'][-1].get('px'); out['line'] = [x.get('px') for x in f['chart'][-40:]]
    return out


def report(f):
    """📋 The folder's FINAL REPORT (owner 2026-11-01: "the overall PoW folder should always give a final report") — every coin, what was
    learned, the trade and its grade, the cost. → (dict, markdown)."""
    shots = f.get('shots') or []; pk = (f.get('pick') or {}).get('mint')
    vit = {**({pk: f['research']} if pk and f.get('research') else {}), **{k: v for k, v in (f.get('vitals') or {}).items() if v}}   # older folders kept the pick's vitals in research
    coins = [{'sym': c.get('sym'), 'mint': c.get('mint'), 'src': SRC_LABEL.get(c.get('src'), c.get('src')), 'safe': c.get('safe', True), 'risk': c.get('risk'),
              'vitals': len(vit.get(c.get('mint')) or []), 'shots': sum(1 for x in shots if x.get('mint') == c.get('mint')),
              'sites': sorted({x.get('site') for x in vit.get(c.get('mint')) or []} | {x.get('site') for x in shots if x.get('mint') == c.get('mint')}),
              'pick': c.get('mint') == pk} for c in f.get('coins') or []]
    p = f.get('pnlPct'); grade = 'no trade' if p is None else ('👍 good trade' if p > 0 else '👎 bad trade')
    cost = round(sum(_f(v) for v in (f.get('cost') or {}).values()), 4) if isinstance(f.get('cost'), dict) else _f(f.get('cost'))
    lesson = ('no coin passed the safety check' if not any(c['safe'] for c in coins) else 'proposal only — nothing bought' if f.get('propose')
              else 'the buy did not fill' if p is None and pk else f"{'it worked' if (p or 0) > 0 else 'it lost'}: {f.get('why') or ''}"[:160])
    r = {'name': f.get('name'), 'coins': coins, 'researched': sum(1 for c in coins if c['vitals'] or c['shots']), 'pick': f.get('sym'),
         'sol': f.get('sol'), 'tp': f.get('tp'), 'sl': f.get('sl'), 'pnlPct': p, 'pnlSol': f.get('pnlSol'), 'grade': grade, 'why': f.get('why'),
         'held': round((_f(f.get('soldAt')) - _f(f.get('boughtAt'))) / 60, 1) if f.get('boughtAt') is not None and f.get('soldAt') else None, 'checks': f.get('checks') or 0,
         'costUsd': cost, 'real': bool(f.get('real')), 'lesson': lesson}
    md = [f"# {r['name']} — FINAL REPORT", '', f"**{grade}**" + (f" · {p:+.2f}% ({_f(f.get('pnlSol')):+.6f} SOL)" if p is not None else '')
          + (' · real money' if r['real'] else ' · paper'), f"Why it ended: {r['why'] or '—'}", f"Lesson: {lesson}", '', '## Coins']
    for c in coins:
        md.append(f"- {'⭐ ' if c['pick'] else ''}${c['sym']} ({c['src']}) — {'safe' if c['safe'] else 'UNSAFE: ' + str(c['risk'])} · "
                  f"{c['vitals']} vitals · {c['shots']} snapshots · sites: {', '.join(c['sites']) or 'none'}")
    if pk:
        md += ['', '## Trade', f"- size {r['sol']} SOL · TP +{r['tp']}% · SL −{r['sl']}% · held {r['held'] or 0} min · {r['checks']} live checks"]
    md += ['', f"Model cost: ${cost:.4f}", '', '## The discussion'] + [f"- **{t.get('by')}**: {t.get('text')}" for t in (f.get('talk') or [])]
    return r, '\n'.join(md) + '\n'


# 💬 the chat commands that start / stop a folder (owner 2026-11-01: "I type 'PoW' or 'file a PoW' and they make the 4-coin file and buy one")
CMD_START = re.compile(r'^\s*(?:(?:mind\s*)?([AB])\s*[:\-—]\s*)?(?:/pow(?:\s+([ab]|both))?\s*$|file\s+(?:a\s+)?pow\b.*$|start\s+(?:a\s+)?pow\b.*$|pow\s*$)', re.I)
CMD_STOP = re.compile(r'^\s*(?:/pow\s+stop|stop\s+(?:the\s+)?pow(?:\s+(?:loop|folder))?)\s*$', re.I)
COMMANDS = [('file a PoW', 'Both minds: a 4-coin PoW folder → they agree on 1 → buy it on FEELESS → chart / research / decide until it sells'),
            ('propose a PoW', 'The same 4-coin folder and agreement — files the pick as a proposal card, buys nothing'),
            ('A: file a PoW', 'Only mind A works the folder (it picks, watches the chart and researches)'),
            ('B: file a PoW', 'Only mind B works the folder'),
            ('A: propose a PoW', 'Mind A alone proposes a coin — nothing bought'),
            ('stop PoW', 'Ends the folder now — sells the coin if it bought one'),
            ('buy 0.05 SOL of $', 'A direct order on FEELESS (guards first; its wallet when real) — type the coin'),
            ('sell all $', 'Sells a coin it holds — type the coin'),
            ('sell half of $', 'Takes half off a coin it holds'),
            ('trim $', 'Same as sell half'),
            ('A: ', 'Only mind A works this ask; B rests on its last page'),
            ('B: ', 'Only mind B works this ask')]


CMD_ANY = re.compile(r'(?i)\b(?:file|propose|provide|make|do|start|run|create|open|give|build|new)\b[^.?!\n]{0,40}\bpow\b')
CMD_ASK = re.compile(r'(?i)^\s*(?:what|how|why|explain|is|does|can)\b|\?\s*$')


def command(text):
    """'file a PoW' / 'PoW' / '/pow' / 'A: file a PoW' / 'propose PoW for 3 coins' → {'do': 'start', 'mind': 0|1|None}; 'stop PoW' → stop; a question → None."""
    t = str(text or '')
    if CMD_STOP.match(t):
        return {'do': 'stop'}
    prop = bool(re.search(r'(?i)\bpropos', t))   # 💡 "propose a PoW" = the same folder, nothing bought
    m = CMD_START.match(t)
    if not m and CMD_ANY.search(t) and not CMD_ASK.search(t):   # 💬 "Propose PoW for 3 coins…" / "Provide PoW on the intake list" = a folder (owner 2026-11-01)
        k_ = re.match(r'^\s*(?:mind\s*)?([AB])\s*[:\-—]', t, re.I)
        return {'do': 'start', 'mind': {'A': 0, 'B': 1}.get((k_.group(1) if k_ else '').upper()), 'propose': prop}
    if not m:
        return None
    k = (m.group(1) or m.group(2) or '').upper()
    return {'do': 'start', 'mind': {'A': 0, 'B': 1}.get(k), 'propose': prop}


# 📖 THE PoW README — every loaded model gets it as default memory, whatever its prompt (owner 2026-11-01: "they need to know the meaning")
README = ('FEELESS PoW (PROOF OF WORK) README — not crypto mining. A PoW is a FOLDER your colony files, in 5 steps: '
          '1) POOL: FEELESS vets up to 8 coins (FEELESS intake, Pump, DexScreener boosts) with every buy guard + the safety check — only coins that can be bought reach you. '
          '2) PROPOSE: mind A proposes 3, mind B proposes 3 OTHER coins (each sees any PRIOR PoW on a coin) → a shortlist of 6. '
          '3) SPLIT: each mind takes 2 coins of the shortlist and writes HOW it will investigate them. '
          '4) RESEARCH: each mind researches its own coins — the FEELESS read + 3 sites, 3–8 moves a site (drawn at random), at most 3 vital numbers a site; '
          'a fact another site already gave is dropped. 5) DECIDE: every coin is checked again, then 3 turns pick the ONE coin, its size (within the wallet '
          'budget), take profit and stop loss → bought ON FEELESS (paper, or the agent\'s own wallet when real) → live checks at +15 s, +30 s, then every 60 s '
          'until it sells. Every research and outcome is kept FOREVER in the PoW archive — use the "pow" tool ($SYMBOL or mint) to review a coin before you research it again. '
          'The owner starts one by typing "file a PoW" (or "A: file a PoW" / "B: file a PoW"); "stop PoW" ends it. Never invent another meaning. '
          'WHY: every PoW and every colonized run is you CAPITALIZING — profit pays for your own model calls (processing) and grows the capital you trade; '
          'a loss eats both. Small, careful, real numbers, short words.')
