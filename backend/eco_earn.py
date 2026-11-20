"""💼 Slice 16 (owner 2026-11-19: "poeco can do upwork and other stuff etc no face … to make money working for places … whatever pays real money!!").
PoEco earns: the finder reads open paid work from PUBLIC feeds only (no login, no scraping behind one), keeps what is faceless and allowed by the
platform's own terms, scores each on fit, pay, deadline and what the minds would cost, and the folder shows the best with the expected profit.
Both minds draft the bid blind and the stronger is kept. Nothing goes out by itself: the owner approves, then HE sends it from his own account
(FEELESS never signs up, never logs in with a password, never holds the money: the platform pays him directly). On a win the minds do the work,
the Collective checks it, the owner approves delivery. Graded on real money paid (his receipt or his mark) against the minds' cost; fees live on
the receipt, never in the profit (§1 style). Pure: every read, call and save is done by fc_earn.py. Slices 17–23 reuse this door (bounties,
clips as a service, storefronts …): a new source is one PLATFORMS row + one parse_* function; the scoring, bid pick, stages and grade stay."""
import hashlib
import json
import math
import re
import time

DAY = 86400

# Terms first (web search 2026-11-20, one real public read of each kept feed the same day). IN = our flow is allowed: AI-made work, a bid the
# owner approves and sends himself. OUT = named with why.
PLATFORMS = [
    {'id': 'superteam', 'name': 'Superteam Earn', 'in': True, 'site': 'https://superteam.fun/earn',
     'feeds': ['https://superteam.fun/api/listings/?type=bounty&take=40', 'https://superteam.fun/api/listings/?type=project&take=40'],
     'terms': 'Every listing says who may do it (agentAccess). AGENT_ALLOWED / AGENT_ONLY listings are open to AI agents with a human claiming the payout; HUMAN_ONLY ones are skipped.',
     'how': 'The owner submits from his own Superteam account; the reward goes to his own wallet.', 'src': 'https://superteam.fun/earn/agents'},
    {'id': 'freelancer', 'name': 'Freelancer.com', 'in': True, 'site': 'https://www.freelancer.com',
     'feeds': ['https://www.freelancer.com/api/projects/0.1/projects/active/?limit=40&job_details=true&full_description=true&sort_field=time_updated'],
     'terms': 'No ban on AI-made work found in its terms; bots that cheat or bypass its systems are banned. So FEELESS never bids: the owner pastes the approved bid and sends it himself.',
     'how': 'The owner bids from his own Freelancer account; the client pays him there.', 'src': 'https://www.freelancer.com/about/terms'},
    {'id': 'algora', 'name': 'Algora (GitHub bounties)', 'in': True, 'site': 'https://algora.io',
     'feeds': ['https://api.github.com/search/issues?q=label:%22%F0%9F%92%8E+Bounty%22+state:open+is:issue+commenter:app/algora-pbc&per_page=30&sort=created'],
     'terms': "Algora sets no AI rule; each repo does. The finder reads the repo's CONTRIBUTING and drops any repo that bans AI-made pull requests.",
     'how': 'The owner opens the pull request from his own GitHub; Algora pays him.', 'src': 'https://algora.io'},
    {'id': 'upwork', 'name': 'Upwork', 'in': False, 'why': 'No public listing feed (its RSS ended 2024-08-20; its API needs an approved app and a login), and bots that send proposals are banned. AI-assisted bids are fine, so the owner can paste a FEELESS draft by hand.',
     'src': 'https://support.upwork.com/hc/en-us/articles/52052528243731-RSS-deprecation'},
    {'id': 'fiverr', 'name': 'Fiverr', 'in': False, 'why': 'No job feed: buyers come to a seller\'s gigs. AI work is allowed if refined and original, but bots that mass-message are banned.',
     'src': 'https://help.fiverr.com/hc/en-us/articles/37333301560593-Using-AI-on-Fiverr-Guidelines-for-freelancers-and-clients'},
    {'id': 'contra', 'name': 'Contra', 'in': False, 'why': 'No public listing feed and no AI-work terms found to build on.', 'src': 'https://contra.com'},
    {'id': 'gitcoin', 'name': 'Gitcoin', 'in': False, 'why': 'Its bounties moved to Buidlbox in 2023 and its grants software wound down in 2025: nothing open to read.',
     'src': 'https://support.gitcoin.co/gitcoin-knowledge-base/misc/cgrants-bounties-and-hackathons-sunsetting-faq'},
]
PLAT = {p['id']: p for p in PLATFORMS}
KEPT = [p['id'] for p in PLATFORMS if p['in']]

FIT = {   # faceless work the minds can do from a keyboard, by the words a listing uses
    'writing': ('article', 'blog', 'thread', 'write', 'writer', 'writing', 'copy', 'copywrit', 'content', 'newsletter', 'docs', 'documentation', 'ebook', 'seo', 'proofread', 'edit '),
    'code': ('bug', 'fix', 'implement', ' api', 'script', 'python', 'rust', 'typescript', 'javascript', 'react', 'node', 'smart contract', 'program', 'integration',
             'backend', 'frontend', 'website', 'web app', 'wordpress', 'compiler', 'test', 'cli', 'sdk', 'golang', ' go ', 'php', 'django', 'bot'),
    'data': ('data', 'scrap', 'spreadsheet', 'excel', 'csv', 'dashboard', 'entry', 'sql', 'database', 'analytics'),
    'research': ('research', 'report', 'analysis', 'feedback', 'review', 'market study', 'survey', 'audit'),
    'design': ('logo', 'graphic design', 'figma', 'banner', ' ui ', 'ui design', 'ux', 'illustration', 'meme', 'infographic', 'slides', 'presentation', 'social media post', 'thumbnail', 'icon'),
    'translation': ('translat', 'locali', 'subtitle'),
}
FACE = ('video', 'voice', 'voiceover', 'call', 'on-site', 'onsite', 'photograph', 'in person', 'in-person', 'camera', 'podcast', 'phone', 'interview', 'tiktok',
        'youtube', 'influencer', 'kyc', 'actor', 'presenter', 'ugc', 'animation', 'event', 'meetup', 'irl', 'filming', 'model ', 'live stream', 'livestream')
CREDENTIAL = (' pe ', 'licensed', 'license holder', 'stamp', 'professional engineer', 'engineer of record', 'architect', 'structural', 'renovation', 'autocad', 'cad drawing',
              'cpa', 'attorney', 'lawyer', 'legal advice', 'notary', 'certified', 'tutor', 'tutoring', 'teacher', 'coach', 'manager', 'full-time', 'full time', 'part-time',
              'employee', 'hire for', 'long term', 'long-term', 'minecraft', 'in game', 'pci compliance', 'penetration test')   # a licence, a seat in a team or a live session: not a faceless one-off
HOURS = {'writing': 3, 'code': 6, 'data': 4, 'research': 4, 'design': 3, 'translation': 2}   # what a person would spend: the hours the minds save
CALLS = {'writing': 4, 'code': 10, 'data': 6, 'research': 6, 'design': 4, 'translation': 3}   # mind calls to bid + do the work
STABLE = {'USDC', 'USDG', 'USDT', 'PYUSD', 'USD', 'USDS', 'DAI'}
AI_BAN = re.compile(r'(no|ban|banned|not accept|prohibit|forbid|reject|disallow)[^.\n]{0,60}\b(ai|llm|chatgpt|copilot|generated|vibe)|\b(ai|llm)[- ]generated[^.\n]{0,40}(not|ban|reject|close)', re.I)
FACE_SAY = re.compile(r"\b(i am|i'm) (a )?(human|real person)\b|\bon camera\b|\bvideo call\b", re.I)
DISCLOSE = 'Drafted with AI help; I review and stand behind everything I deliver.'
STAGES = ('bid', 'bid_approved', 'sent', 'won', 'work', 'checked', 'delivery_approved', 'paid', 'lost', 'unpaid')


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else d
    except (TypeError, ValueError):
        return d


def _cut(s, n):
    s = ' '.join(str(s or '').split())
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _iso(s):
    try:
        return time.mktime(time.strptime(str(s)[:19], '%Y-%m-%dT%H:%M:%S')) - time.timezone
    except (TypeError, ValueError):
        return None


def fit_of(text):
    """→ (category or '', why). Faceless work only: a listing that needs a face, a voice, a camera or a place is out with its word."""
    t = f' {str(text or "").lower()} '
    face = next((w for w in FACE if w in t), None)
    if face:
        return '', f'needs a face or a place ("{face.strip()}")'
    cred = next((w for w in CREDENTIAL if w in t), None)
    if cred:
        return '', f'needs a licence, a role or a live session ("{cred.strip()}")'
    hits = {c: sum(1 for w in ws if w in t) for c, ws in FIT.items()}
    hits['translation'] *= 2   # "translate the docs" is translation, not writing
    c = max(hits, key=hits.get)
    return (c, f'{c}: ' + ', '.join(w.strip() for w in FIT[c] if w in t)[:80]) if hits[c] else ('', 'no faceless task the minds can do (writing, code, data, research, design, translation)')


def _row(src, lid, title, url, desc, pay_usd, pay_note, deadline, rivals, extra=None):
    return {'src': src, 'id': f'{src}:{lid}', 'title': _cut(title, 140), 'url': url, 'desc': _cut(desc, 1200), 'payUsd': pay_usd, 'pay': pay_note,
            'deadline': deadline, 'rivals': rivals, **(extra or {})}


def parse_superteam(rows, prices=None):
    """Superteam Earn's public listings → (kept, out). Only listings its own flag opens to agents; an open HUMAN_ONLY listing is out, named."""
    kept, out = [], []
    for r in rows or []:
        if not isinstance(r, dict) or r.get('status') not in (None, 'OPEN'):
            continue
        tok = str(r.get('token') or '').upper(); amt = _f(r.get('rewardAmount')) or _f(r.get('maxRewardAsk'))
        usd = amt if tok in STABLE else (amt * _f((prices or {}).get(tok)) if (prices or {}).get(tok) else None)
        row = _row('superteam', r.get('id') or r.get('slug'), r.get('title'), f"https://superteam.fun/earn/listing/{r.get('slug')}", f"{r.get('title')} · {(r.get('sponsor') or {}).get('name') or ''} · {r.get('type')}",
                   round(usd, 2) if usd is not None else None, f"{amt:,.0f} {tok}" + ('' if usd is not None else ' (no USD price)'), _iso(r.get('deadline')),
                   int(((r.get('_count') or {}).get('Submission')) or 0), {'access': r.get('agentAccess'), 'sponsor': (r.get('sponsor') or {}).get('name'), 'type': r.get('type')})
        if r.get('agentAccess') not in ('AGENT_ALLOWED', 'AGENT_ONLY'):
            out.append({**row, 'outWhy': f"its sponsor set it {r.get('agentAccess') or 'human only'}: no AI agents"})
        else:
            kept.append(row)
    return kept, out


def parse_freelancer(j):
    """Freelancer.com's public active-projects API → (kept, out). Budget × the listing's own exchange rate = USD; hourly jobs count 10 hours."""
    kept = []
    for r in ((j or {}).get('result') or {}).get('projects') or []:
        if not isinstance(r, dict) or r.get('status') != 'active':
            continue
        b = r.get('budget') or {}; cur = r.get('currency') or {}; rate = _f(cur.get('exchange_rate'), 0)
        lo, hi = _f(b.get('minimum')), _f(b.get('maximum')) or _f(b.get('minimum'))
        hourly = r.get('type') == 'hourly'; mid = (lo + hi) / 2 * (10 if hourly else 1)
        usd = round(mid * rate, 2) if rate and mid else None
        jobs = ', '.join(x.get('name', '') for x in r.get('jobs') or [] if isinstance(x, dict))
        sub = _f(r.get('time_submitted')); dl = sub + _f(r.get('bidperiod'), 7) * DAY if sub else None
        kept.append(_row('freelancer', r.get('id'), r.get('title'), f"https://www.freelancer.com/projects/{r.get('seo_url')}", f"{r.get('preview_description') or r.get('description') or ''} · skills: {jobs}",
                         usd, f"{cur.get('sign') or ''}{lo:,.0f}–{hi:,.0f} {cur.get('code') or ''}" + (' /hr (×10 h)' if hourly else ''), dl, int(((r.get('bid_stats') or {}).get('bid_count')) or 0),
                         {'hourly': hourly, 'skills': jobs[:120]}))
    return kept, []


def bounty_usd(text):
    m = re.search(r'\$\s?(\d[\d,]*(?:\.\d+)?)\s*(k)?\b', str(text or ''), re.I)
    return round(_f(m.group(1).replace(',', '')) * (1000 if m.group(2) else 1), 2) if m else None


def repo_of(url):
    m = re.match(r'https://github\.com/([^/]+/[^/]+)/issues/\d+', str(url or ''))
    return m.group(1) if m else ''


def ai_rule(contributing):
    """A repo's own rule on AI-made pull requests, from its CONTRIBUTING: 'banned' | 'ok' | 'unknown' (none found)."""
    if contributing is None:
        return 'unknown'
    return 'banned' if AI_BAN.search(str(contributing)) else 'ok'


def parse_algora(j, rules=None):
    """GitHub's public issue search for Algora's 💎 Bounty label → (kept, out). A repo whose CONTRIBUTING bans AI work is out; a bounty with no $ is out."""
    kept, out = [], []
    for r in (j or {}).get('items') or []:
        if not isinstance(r, dict) or r.get('state') != 'open':
            continue
        repo = repo_of(r.get('html_url')); text = f"{r.get('title')} {r.get('body') or ''}"
        usd = bounty_usd(' '.join(lb.get('name', '') for lb in r.get('labels') or [] if isinstance(lb, dict)) + ' ' + text)
        row = _row('algora', r.get('id'), r.get('title'), r.get('html_url'), f"{repo} · {r.get('body') or ''}", usd, f'${usd:,.0f}' if usd else 'no $ amount on the issue', None,
                   int(r.get('comments') or 0), {'repo': repo, 'aiRule': (rules or {}).get(repo, 'unknown')})
        labels = ' '.join(lb.get('name', '') for lb in r.get('labels') or [] if isinstance(lb, dict)).lower()
        opened = 'ai agent friendly' in labels or 'ai only' in labels   # the repo's own label opens it to AI agents
        if opened:
            row['aiRule'] = 'ok (its label: AI agent friendly)'
        if (rules or {}).get(repo) == 'banned' and not opened:
            out.append({**row, 'outWhy': f'{repo} bans AI-made pull requests in its CONTRIBUTING'})
        elif usd is None:
            out.append({**row, 'outWhy': 'no $ amount on the issue'})
        else:
            kept.append(row)
    return kept, out


def mind_cost(category, per_call):
    """What the minds would cost to bid and do it: the calls this kind of work takes × this agent's real median $ per call."""
    return round(CALLS.get(category, 6) * max(0.0, _f(per_call)), 4)


def per_call(rows, since=0):
    """This agent's median $ per answered call (its real call log), or a floor when it has none."""
    us = sorted(_f(r.get('usd')) for r in rows or [] if isinstance(r, dict) and r.get('ok') and _f(r.get('usd')) > 0 and _f(r.get('at')) >= since)
    return round(us[len(us) // 2], 6) if us else 0.002


def chance(rivals, src):
    """A plain win chance from how many already entered (no history yet: it is a guess, and the grade later shows how good)."""
    n = max(0, int(rivals or 0))
    return round(min(0.35, 1 / (1 + n / (3 if src == 'superteam' else 6 if src == 'freelancer' else 4))), 3)


def score(row, per_call_usd, now=None):
    """Fit, pay, deadline and the minds' cost → {cat, fitWhy, cost, chance, expProfit, hours, parts, score}. 0 when not faceless or past due."""
    now = now or time.time(); cat, why = fit_of(f"{row.get('title')} {row.get('desc')}")
    cost = mind_cost(cat, per_call_usd); pay = row.get('payUsd'); ch = chance(row.get('rivals'), row.get('src'))
    exp = round((pay or 0) * ch - cost, 2) if pay is not None else None
    left = (row['deadline'] - now) / DAY if row.get('deadline') else None
    parts = {'fit': 30 if cat else 0,
             'pay': round(min(30, 6 * math.log10(1 + pay)), 1) if pay else 0,
             'deadline': 0 if left is not None and left < 0.5 else 20 if left is None or left >= 3 else round(20 * left / 3, 1),
             'profit': 0 if not exp or exp <= 0 else round(min(20, 5 * math.log10(1 + exp)), 1)}
    total = 0 if not cat or (left is not None and left < 0.5) else round(sum(parts.values()))
    return {**row, 'cat': cat, 'fitWhy': why, 'cost': cost, 'chance': ch, 'expProfit': exp, 'hours': HOURS.get(cat, 0), 'daysLeft': round(left, 1) if left is not None else None,
            'parts': parts, 'score': total}


def board(kept, out, per_call_usd, filed_ids=(), now=None, n=12):
    """The folder's board: the best faceless listings by score (one already bid on is skipped: a new footprint), plus what was left out and why."""
    rows = [score(r, per_call_usd, now) for r in kept]
    skipped = [r for r in rows if not r['score']]
    best = sorted((r for r in rows if r['score'] and r['id'] not in set(filed_ids)), key=lambda r: (-r['score'], -(r['expProfit'] or 0)))
    why = {}
    for r in out + skipped:
        k = r.get('outWhy') or ('due in under 12 hours' if r.get('cat') else re.sub(r' \(".*', '', str(r.get('fitWhy') or '')))
        why[k] = why.get(k, 0) + 1
    return {'at': round(now or time.time()), 'best': best[:n], 'seen': len(kept) + len(out), 'kept': len(best),
            'out': sorted(({'why': k, 'n': v} for k, v in why.items() if k), key=lambda x: -x['n'])[:8]}


SYS = ('You bid on one paid job for the owner, who will do it with AI help and no face (writing, code, data, research, design or translation). '
       'Read the listing and the kits. Write the bid he will send from HIS OWN account: specific to this listing, plain, no fluff, never claim to be a human '
       'or offer a call or video. Reply ONLY with JSON: {"bid": "the message, 80-220 words", "plan": ["3-6 concrete steps to deliver"], '
       '"price": number in USD (at most the listed pay), "days": number, "risks": ["what could lose it"], "fit": 0-10}')
RETRY = 'Your last reply could not be read. Reply with the JSON object ONLY, no other text.'


def ask_text(row):
    return (f"LISTING ({PLAT.get(row['src'], {}).get('name', row['src'])}): {row['title']}\nURL: {row['url']}\nPAY: {row['pay']} (≈ ${row.get('payUsd') or '?'})\n"
            f"DEADLINE: {row.get('daysLeft') if row.get('daysLeft') is not None else 'open'} days · ALREADY ENTERED: {row.get('rivals')}\nKIND OF WORK: {row.get('cat')}\nDETAILS: {row.get('desc')}")


def parse_bid(raw):
    """A mind's bid JSON, or None. Tolerates a fenced block or prose around it."""
    m = re.search(r'\{.*\}', str(raw or ''), re.S)
    if not m:
        return None
    try:
        j = json.loads(m.group(0))
    except (TypeError, ValueError):
        return None
    if not isinstance(j, dict) or not str(j.get('bid') or '').strip():
        return None
    return {'bid': str(j['bid']).strip()[:2400], 'plan': [str(x)[:200] for x in j.get('plan') or [] if x][:8], 'price': _f(j.get('price')) or None,
            'days': _f(j.get('days')) or None, 'risks': [str(x)[:160] for x in j.get('risks') or [] if x][:5], 'fit': max(0, min(10, _f(j.get('fit'))))}


def bid_score(b, row):
    """How strong a drafted bid is, by rules anyone can check → (0..100, [why])."""
    if not b:
        return 0, ['no bid came back']
    words = len(b['bid'].split()); why = []
    keys = {w for w in re.findall(r'[a-z]{5,}', str(row.get('title') or '').lower())}
    hits = sum(1 for w in keys if w in b['bid'].lower())
    s = 0
    s += 25 if 80 <= words <= 260 else 10 if words >= 40 else 0; why.append(f'{words} words')
    s += min(25, 8 * hits); why.append(f'{hits} of the listing\'s words')
    s += min(20, 5 * len(b['plan'])); why.append(f"{len(b['plan'])} plan steps")
    pay = row.get('payUsd')
    if b['price'] and pay and b['price'] <= pay * 1.05:
        s += 10; why.append(f"${b['price']:.0f} within the pay")
    elif b['price'] and pay:
        why.append(f"${b['price']:.0f} over the ${pay:.0f} pay")
    if b['days'] and (row.get('daysLeft') is None or b['days'] <= row['daysLeft']):
        s += 10; why.append(f"{b['days']:.0f} days fits the deadline")
    s += round(b['fit'])
    if FACE_SAY.search(b['bid']):
        s -= 40; why.append('claims a face, a call or to be human (not allowed)')
    return max(0, min(100, s)), why


def pick(bids, row):
    """Both minds' blind bids → (index of the stronger, scored list). The kept bid always carries the AI disclosure (Fiverr / Upwork style honesty)."""
    scored = [(*bid_score(b, row), b) for b in bids]
    k = max(range(len(scored)), key=lambda i: scored[i][0]) if scored else None
    if k is None or not scored[k][0]:
        return None, scored
    b = scored[k][2]
    if 'ai help' not in b['bid'].lower() and 'ai-assisted' not in b['bid'].lower():
        b['bid'] = b['bid'].rstrip() + '\n\n' + DISCLOSE
    return k, scored


def new_folder(n, row, kept, scored, calls, cost, now=None):
    """The earn filing: the listing as scored, both bids (the kept one marked), the cost so far. Status 'closed' (it files now; the stages carry on)."""
    now = round(now or time.time())
    return {'id': f'earn{now}', 'n': n, 'kind': 'earn', 'at': now, 'status': 'closed', 'paper': True, 'topic': _cut(f"{PLAT.get(row['src'], {}).get('name')}: {row['title']}", 120),
            'listing': {k: row.get(k) for k in ('src', 'id', 'title', 'url', 'pay', 'payUsd', 'deadline', 'daysLeft', 'rivals', 'cat', 'fitWhy', 'cost', 'chance', 'expProfit', 'hours', 'parts', 'score', 'access', 'repo', 'aiRule', 'sponsor')},
            'platform': {k: PLAT.get(row['src'], {}).get(k) for k in ('id', 'name', 'terms', 'how', 'src')},
            'bids': [{'mind': i, 'score': s, 'why': w, **(b or {})} for i, (s, w, b) in enumerate(scored)], 'kept': kept,
            'bid': (scored[kept][2] if kept is not None else None), 'calls': calls, 'cost': round(cost, 5),
            'stage': 'bid', 'stages': [{'stage': 'bid', 'at': now, 'by': 'minds'}], 'sources': {'listing': [{'url': row['url']}]}}


def can_go(f, stage, by, test_ok=False):
    """The approve door (Slice 5's rule): only the owner moves a filing on, never the internal key or an auto run; a TEST needs his on-purpose tick.
    → '' when allowed, else why not."""
    if by != 'owner':
        return 'Only its owner approves. Nothing is sent or delivered by itself.'
    if (f.get('test') or f.get('testRun')) and not test_ok and stage in ('bid_approved', 'delivery_approved'):
        return 'This is a TEST filing. Approve it on purpose (tick "this test is real") if you mean to send it.'
    order = {'bid_approved': ('bid',), 'sent': ('bid_approved',), 'won': ('sent',), 'lost': ('bid', 'bid_approved', 'sent', 'won', 'work', 'checked', 'delivery_approved'),
             'work': ('won',), 'checked': ('work',), 'delivery_approved': ('checked',), 'paid': ('delivery_approved',), 'unpaid': ('delivery_approved',)}
    if stage not in order:
        return 'No such step.'
    if f.get('stage') not in order[stage]:
        return f"It is at '{f.get('stage')}': {stage.replace('_', ' ')} comes after {' or '.join(order[stage])}."
    return ''


def move(f, stage, by, now=None, **kw):
    now = round(now or time.time())
    f['stage'] = stage
    f['stages'] = list(f.get('stages') or []) + [{'stage': stage, 'at': now, 'by': by, **{k: v for k, v in kw.items() if v not in (None, '')}}]
    return f


def receipt(amount, fee=0.0, currency='USD', rate=1.0, ref=''):
    """The money as the platform paid it. Fees stay HERE, never in the profit (§1 style)."""
    amt = _f(amount); fee_ = _f(fee); r = _f(rate, 1.0) or 1.0
    if amt < 0 or fee_ < 0:
        raise ValueError('Amounts are never negative.')
    return {'amount': round(amt, 2), 'fee': round(fee_, 2), 'currency': str(currency or 'USD')[:8].upper(), 'rate': r, 'usd': round(amt * r, 2), 'feeUsd': round(fee_ * r, 2),
            'netUsd': round((amt - fee_) * r, 2), 'ref': str(ref or '')[:300]}


def grade(f):
    """Graded on real money: paid (receipt usd, fees excluded) − the minds' cost = profit; hours saved. A lost or unpaid job is graded too, with why."""
    cost = round(_f(f.get('cost')) + _f((f.get('work') or {}).get('cost')), 5); hrs = _f((f.get('listing') or {}).get('hours'))
    st = f.get('stage'); last = (f.get('stages') or [{}])[-1]
    if st == 'paid':
        r = f.get('receipt') or {}; profit = round(_f(r.get('usd')) - cost, 2)
        return {'result': 'paid', 'paidUsd': r.get('usd'), 'cost': cost, 'profit': profit, 'hoursSaved': hrs, 'perHour': round(profit / hrs, 2) if hrs else None,
                'feeOnReceipt': r.get('feeUsd'), 'why': f"paid ${_f(r.get('usd')):.2f}, the minds cost ${cost:.4f}; fees ${_f(r.get('feeUsd')):.2f} stay on the receipt"}
    if st in ('lost', 'unpaid'):
        return {'result': st, 'paidUsd': 0.0, 'cost': cost, 'profit': round(-cost, 4), 'hoursSaved': 0, 'why': last.get('why') or ('the bid did not win' if st == 'lost' else 'delivered but never paid')}
    return None


def footprint_text(f):
    lst = f.get('listing') or {}
    return f"{lst.get('src')} {lst.get('title')}"


def record_rows(f):
    """Slice 16's own checks on an earn filing (beside every proof's minds / sources / footprint / kits)."""
    lst = f.get('listing') or {}; pl = f.get('platform') or {}; bids = f.get('bids') or []; st = f.get('stage'); g = f.get('graded')
    kept_ok = f.get('kept') is not None and len([b for b in bids if b.get('bid')]) >= 1
    appr = next((s for s in f.get('stages') or [] if s.get('stage') == 'bid_approved'), None)
    return [
        {'key': 'terms', 'label': "The platform's terms allow AI-made work and our flow", 'ok': pl.get('id') in KEPT, 'why': f"{pl.get('name')}: {pl.get('terms')}"[:300]},
        {'key': 'finder', 'label': 'A real open listing, scored on fit, pay, deadline and the minds\' cost', 'ok': bool(lst.get('url')) and bool(lst.get('cat')) and lst.get('score') is not None,
         'why': f"{lst.get('cat')} · {lst.get('pay')} · score {lst.get('score')} · minds ${_f(lst.get('cost')):.4f} · expected profit ${_f(lst.get('expProfit')):.2f} ({round(_f(lst.get('chance')) * 100)}% chance)"},
        {'key': 'bid', 'label': 'Both minds drafted the bid blind; the stronger is kept', 'ok': kept_ok and len(bids) >= 2,
         'why': ' · '.join(f"Mind {'AB'[b['mind'] % 2]} {b.get('score')}" + (' (kept)' if b['mind'] == f.get('kept') else '') for b in bids) or 'no bid'},
        {'key': 'approve', 'label': 'Nothing sent until the owner approves, from his own account', 'ok': not any(s.get('by') not in ('owner', 'minds', 'collective') for s in f.get('stages') or []),
         'why': (f"approved by the owner {time.strftime('%m-%d %H:%M', time.gmtime(appr['at']))} UTC; he sends it himself" if appr else f"waiting at '{st}': nothing was sent")},
        {'key': 'graded', 'label': 'Graded on real money (paid − the minds\' cost; fees on the receipt)', 'ok': True,
         'why': g['why'] if g else f"open: grades when he marks it paid, lost or unpaid (so far the minds cost ${_f(f.get('cost')):.4f})"},
    ]


def seal(f):
    """A hash of what the owner approved (the listing + the kept bid): the same approve always gives this seal."""
    b = f.get('bid') or {}
    return hashlib.sha256(json.dumps({'l': (f.get('listing') or {}).get('id'), 'b': b.get('bid'), 'p': b.get('price')}, sort_keys=True).encode()).hexdigest()[:16]


WORK_SYS = ('You do ONE paid job the owner won, with no face: deliver the finished work itself, not a plan. Read the listing, the kept bid and the kits. '
            'Reply ONLY with JSON: {"accept": ["each requirement from the listing, one line"], "work": "the finished deliverable (Markdown; code in fenced blocks)", '
            '"met": ["for each accept line, where the work meets it, or NOT MET and why"]}')


def work_text(f):
    lst = f.get('listing') or {}; b = f.get('bid') or {}
    return (f"LISTING: {lst.get('title')}\nURL: {lst.get('url')}\nPAY: {lst.get('pay')}\nKIND OF WORK: {lst.get('cat')}\n"
            f"THE KEPT BID: {b.get('bid')}\nPLAN: {json.dumps(b.get('plan') or [])}\nDAYS: {b.get('days')}")


def parse_work(raw):
    m = re.search(r'\{.*\}', str(raw or ''), re.S)
    try:
        j = json.loads(m.group(0)) if m else None
    except (TypeError, ValueError):
        j = None
    if not isinstance(j, dict) or len(str(j.get('work') or '').split()) < 30:
        return None
    return {'accept': [str(x)[:200] for x in j.get('accept') or [] if x][:15], 'text': str(j['work'])[:20000], 'met': [str(x)[:200] for x in j.get('met') or [] if x][:15]}


def work_score(w, f):
    """How complete a deliverable is, by rules anyone can check → (0..100, [why])."""
    if not w:
        return 0, ['no deliverable came back']
    words = len(w['text'].split()); acc = len(w['accept']); unmet = sum(1 for x in w['met'] if 'not met' in x.lower())
    keys = {x for x in re.findall(r'[a-z]{5,}', str((f.get('listing') or {}).get('title') or '').lower())}; hits = sum(1 for x in keys if x in w['text'].lower())
    s = min(40, words // 20) + min(25, 5 * acc) + min(20, 5 * hits) + (15 if acc and not unmet else 0) - (40 if FACE_SAY.search(w['text']) else 0)
    return max(0, min(100, s)), [f'{words} words', f'{acc} requirements listed', f'{unmet} not met', f"{hits} of the listing's words"]
