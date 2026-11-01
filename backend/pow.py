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
    every = [f'https://dexscreener.com/solana/{pa or m}', f'https://rugcheck.xyz/tokens/{m}', f'https://solscan.io/token/{m}', f'https://birdeye.so/token/{m}?chain=solana',
             f'https://jup.ag/tokens/{m}', f'https://pump.fun/coin/{m}', f'https://www.coingecko.com/en/search?query={m}']
    used = set(p.get('used') or ())   # 🔁 a new round never re-opens a site an earlier round of this folder already read (owner 2026-11-01)
    fresh = [u for u in every if host_of(u) not in used]
    return fresh if len(fresh) >= 2 else every


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
SIGN_WAIT_S = 600                 # a real buy waits this long for its wallet, then the folder closes and the order is withdrawn
MIN_LIQ = 5000
FOLDERS_KEEP = 30
SRC_LABEL = {'intake': 'FEELESS intake', 'pump': 'Pump', 'dex': 'DexScreener'}

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


def gather(intake, dex, done=()):
    """The folder's 4 coins: 2 FEELESS intake (best rank, real pools), 1 Pump, 1 DexScreener boost. → list (may be short when a source is dry)."""
    done = set(done or ()); got = []; seen = set(done)
    ok = lambda c: c.get('mint') and c.get('pair') and c['mint'] not in seen and _f(c.get('liq')) >= MIN_LIQ   # noqa: E731
    rows = sorted([c for c in intake or [] if ok(c)], key=lambda c: -_f(c.get('rank')))

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
    """🗺 The folder's ONE joint 3-step plan, set before anything is browsed (owner 2026-11-01: "both agents combined, 3-step total plan before browsing")."""
    if int(minds or 1) > 1:
        return ['both minds pick 1 of the 4 coins and agree', "A watches the coin's FEELESS chart · B researches its CA (DexScreener · RugCheck · Solscan)",
                "A decides HOLD / SELL with B's vitals — loop until it sells"]
    return ['it picks 1 of the 4 coins', "it watches the FEELESS chart, then researches the CA (DexScreener · RugCheck · Solscan)", 'it decides HOLD / SELL — loop until it sells']


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
    if rounds >= ROUNDS_MAX:
        return f'{ROUNDS_MAX} rounds — the folder closes'
    return None


def parse_decide(text):
    t = str(text or '').upper()
    act = 'SELL' if re.search(r'"ACTION"\s*:\s*"SELL"|\bSELL\b', t) else 'HOLD'
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
            'boughtAt', 'soldAt', 'real', 'shared', 'research', 'picks', 'whys', 'base', 'pair', 'mint', 'propose', 'sol', 'plan', 'entryUsd', 'tp', 'sl', 'shots')
    out = {k: f.get(k) for k in keep if k in f}
    if f.get('chart'):   # the live price the watcher reads (its P/L on the monitor)
        out['now'] = f['chart'][-1].get('px'); out['line'] = [x.get('px') for x in f['chart'][-24:]]
    return out


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
README = ('FEELESS PoW (PROOF OF WORK) README — not crypto mining. A PoW is a FOLDER your colony files: '
          '1) it starts empty; FEELESS gathers 4 coins: 2 from the FEELESS intake, 1 from Pump, 1 from DexScreener\'s most-boosted Solana coins. '
          '2) Each mind picks the ONE coin most likely to rise without rugging; both minds must AGREE (one round of discussion). '
          '3) That one coin is bought ON FEELESS through the guarded order path (paper, or the agent\'s own wallet when real). '
          '4) The loop: the chart watcher reads the FEELESS chart for at least 3 min; the researcher researches the coin\'s contract on 3 trusted sites '
          '(DexScreener, RugCheck, Solscan), at most 5 moves and 3 vital numbers per site, for at most 2.5 min; then the watcher decides HOLD or SELL. '
          'The minds set the size (within the wallet budget), take profit and stop loss themselves; those, 60 min and 6 rounds sell without asking. 5) The folder is filed (coins, picks, talk, research, P/L) in the owner\'s '
          'Desktop PoW folder + cabinet; a winning folder goes to the Colony with the owner\'s share of the profit. '
          'The owner starts one by typing "file a PoW" (or "A: file a PoW" / "B: file a PoW"); "stop PoW" ends it. Never invent another meaning. '
          'WHY: every PoW and every colonized run is you CAPITALIZING — profit pays for your own model calls (processing) and grows the capital you trade; '
          'a loss eats both. Small, careful, real numbers, short words.')
