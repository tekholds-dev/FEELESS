"""🧠 TRENCH MIND (pure, tested) — what the agent desk knows about HUMAN trenching. Owner, 2026-10-09: "research and understand human
trenching — the lingo, the narratives, buy-the-dip tuggers, botted launches; learn on its own from Pump and other platforms; give a real
analysis, not a repeat script of numbers; all agents must have trench humor".

Where it learns (all live, no keys needed):
  · Pump's own callouts — the THESIS text real trenchers write when they call a coin ("early tek 🫵", "dev is based, cto incoming").
    Every word is counted per day; a word that keeps showing up and isn't in the dictionary is LEARNED as new slang (with the coin it
    rode in on). Copy-paste swarms ("BOTS TAKEOVER $BOTS #8113" × 40) are caught as BOTTED CALLOUTS, not hype.
  · Coin names / tickers → the NARRATIVE a coin rides (AI, dog, cat, frog, politics, celeb, stock, holiday …) + which narratives are hot.
  · The coin's own vitals → BOTTED launch evidence (organic share, bundles, snipers, wash read) and the DIP-TUG pattern (a botted pump that
    dumped, with buyers trying to catch it).
Every one of these becomes a DRIVER on the agent desk, judged like the others (what really followed over 5 min) — the desk learns which
narratives and crowd patterns pay, it is never told.
Humor: each agent has its own voice; a quip is picked by the situation (never random noise) and is always labelled as the agent talking.
A read, never advice, never a promise.
"""
import re

# 📖 the trench dictionary (seed) — learned words are added beside it, never over it
SLANG = {
    'ape': 'buy in fast, no research', 'aped': 'bought in fast', 'jeet': 'sells the first green candle', 'jeets': 'people who dump early',
    'rug': 'dev / insiders pull the liquidity — the coin dies', 'rugged': 'liquidity pulled', 'cabal': 'an insider group that controls supply',
    'bundle': 'dev bought many wallets in the launch block', 'bundled': 'supply bought in the launch block', 'sniper': 'bot that buys in the first blocks',
    'snipers': 'first-block bots', 'cto': 'community takeover — the dev left, holders run it', 'kol': 'key opinion leader — a caller with reach',
    'send': 'it is going up', 'sendit': 'go all in', 'bonded': 'graduated off the Pump curve to a real pool', 'bonding': 'climbing the launch curve',
    'migration': 'graduation to the DEX pool', 'koth': 'king of the hill — top of Pump', 'paperhands': 'sold too early', 'diamondhands': 'holding through anything',
    'lfg': "let's f-ing go", 'ngmi': 'not gonna make it', 'wagmi': "we're all gonna make it", 'rekt': 'wrecked — lost it all', 'fud': 'fear, uncertainty, doubt',
    'alpha': 'early information', 'degen': 'high-risk trader', 'moon': 'huge pump', 'mooning': 'pumping hard', 'pnd': 'pump and dump',
    'exitliq': 'exit liquidity — the buyers insiders sell to', 'bagholder': 'stuck holding a dead coin', 'bags': 'what you hold', 'tek': 'technique / setup',
    'early': 'before the crowd', 'chad': 'the dev / buyer acting with conviction', 'based': 'respected, real', 'gem': 'a coin before it runs',
    'runner': 'a coin that keeps going', 'dip': 'the price came down', 'btd': 'buy the dip', 'top': 'the high everyone buys', 'topblast': 'bought the exact top',
    'dexpaid': 'dev paid for the DexScreener profile', 'boost': 'paid DexScreener boost', 'narrative': 'the story a coin rides', 'meta': 'what is working right now',
    'trenches': 'fresh launches on Pump', 'trenching': 'trading fresh launches', 'devsold': 'the creator sold', 'honeypot': 'you can buy but not sell',
    'botted': 'fake volume / fake buyers', 'washed': 'traded with itself to look busy', 'volumebot': 'a bot making fake volume', 'insiders': 'wallets tied to the dev',
    'dev': 'whoever launched the coin', 'cook': 'let it run', 'cooking': 'it is running', 'cooked': 'it is over', 'printing': 'making money',
    'goat': 'greatest of all time', 'giga': 'huge', 'mog': 'out-meme everything', 'lowcap': 'small market cap', 'mc': 'market cap', 'ath': 'all-time high',
}
NARRATIVES = {
    'ai': ('🤖 AI', r'\b(ai|gpt|agent|agents|bot|bots|neural|llm|sentient|agi|claude|grok)\b'),
    'dog': ('🐕 dog', r'\b(dog|doge|inu|shib|pup|puppy|woof|bonk|wif)\b'), 'cat': ('🐈 cat', r'\b(cat|kitty|meow|popcat|nyan|catflix)\b'),
    'frog': ('🐸 frog', r'\b(pepe|frog|frogodile|kek|toad)\b'), 'politics': ('🏛 politics', r'\b(trump|maga|biden|elon|musk|president|vote|usa)\b'),
    'celeb': ('⭐ celeb', r'\b(snoop|drake|kanye|ye|taylor|mrbeast|tate|ishowspeed|speed)\b'), 'stock': ('📈 stock / tech', r'\b(qbit|qubit|quantum|nvda|tesla|spacex|stonk|apple|ibm|tech)\b'),
    'holiday': ('🎃 season', r'\b(halloween|pumpoween|xmas|christmas|santa|spooky|ghost)\b'), 'food': ('🍔 food', r'\b(burger|pizza|taco|sushi|cheese|bread|rice)\b'),
    'game': ('🎮 game', r'\b(game|gamer|gaming|gta|gta6|pixel|arcade|pokemon|mario|minecraft|roblox|fortnite|nintendo|xbox|playstation)\b'), 'money': ('💸 money / casino', r'\b(jackpot|casino|lotto|cash|money|bank|rich|bet)\b'),
}
STOP = set(('the a an and or of to in on for is are be it its this that with at by from as was were will just you your we our us i me my they them he she his her '
             'not no yes so if but now all any one more most very too can get got go good like let other because about after again also back been before being '
             'both did does doing down each even every few first from had has have here how into its just know last least less made make many may might much '
             'must never new next off old only out over own same see should since some still such than then there these thing things think those though through '
             'today under until up use want way well what when where which while who why would yeah yet lol lmao gonna wanna just really people time day coins coin '
             'token tokens buy sell price chart guys bro fam im dont cant wont thats its ive youre theyre gm gn going come look need take give right big').split())
FILLER = {'narrative', 'meta', 'dev', 'mc', 'dip', 'bags', 'top', 'early'}   # dictionary words too generic to quote as "what they're saying"


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def words(text):
    """Lower-case trench words of a text: letters / digits only, slang joined ("paper hands" → also 'paperhands'), no tickers / numbers."""
    t = re.sub(r'https?://\S+', ' ', str(text or '').lower())
    t = re.sub(r'\$[a-z0-9]+|#\d+', ' ', t)
    ws = re.findall(r"[a-z][a-z']{1,18}", t)
    joined = [a + b for a, b in zip(ws, ws[1:]) if a + b in SLANG]
    return [w.strip("'") for w in ws if w not in STOP] + joined


def narrative(row):
    """→ (key, label) of the narrative a coin rides, from its name + ticker, or (None, None)."""
    t = f"{(row or {}).get('name') or ''} {(row or {}).get('symbol') or ''}".lower()
    for k, (label, rx) in NARRATIVES.items():
        if re.search(rx, t):
            return k, label
    return None, None


def swarm(theses):
    """🤖 BOTTED CALLOUTS: the same sentence (numbers stripped) posted again and again = a swarm, not a crowd. → (is_swarm, share of copies)."""
    norm = [re.sub(r'[#$]?\w*\d+\w*', '', str(t or '').lower()).strip() for t in theses or [] if str(t or '').strip()]
    if len(norm) < 4:
        return False, 0.0
    from collections import Counter
    top = Counter(norm).most_common(1)[0][1]
    tmpl = Counter(' '.join(n.split()[:2]) for n in norm).most_common(1)[0][1]   # "the bots are here …" / "the bots now …" = one template
    share = max(top, tmpl) / len(norm)
    return share >= 0.5, round(share, 2)


def crowd(calls):
    """👥 What the humans calling this coin are saying: callers, real-vs-swarm, the slang they use, the words they lean on."""
    calls = list(calls or [])
    theses = [c.get('thesis') for c in calls if c.get('thesis')]
    is_swarm, share = swarm(theses)
    ws = [w for t in theses for w in words(t)]
    from collections import Counter
    cnt = Counter(ws)
    slang = [w for w, _ in cnt.most_common(30) if w in SLANG and w not in FILLER][:4]
    hype = sum(cnt[w] for w in ('send', 'sendit', 'moon', 'gem', 'early', 'lfg', 'cooking', 'printing', 'runner', 'giga', 'tek'))
    fear = sum(cnt[w] for w in ('rug', 'rugged', 'jeet', 'jeets', 'devsold', 'cooked', 'dump', 'exitliq', 'honeypot', 'bundle', 'bundled'))
    users = {c.get('user') for c in calls if c.get('user')}
    return {'callers': len(users), 'swarm': is_swarm, 'swarmShare': share, 'slang': slang, 'hype': hype, 'fear': fear,
            'words': [w for w, _ in cnt.most_common(6) if w not in SLANG][:3]}


def bots(row):
    """🤖 BOTTED LAUNCH evidence from the coin's own vitals → (score 0–100, [reasons]). Unknown readings are not counted."""
    r = row or {}
    out, s = [], 0
    org = r.get('organicPct') if r.get('organicPct') is not None else (r.get('vital') or {}).get('organicPct')
    if org is not None and _f(org) < 5:
        s += 35; out.append(f'only {_f(org):.0f}% of the volume is organic')
    if r.get('bundledN') is not None and _f(r['bundledN']) >= 3:
        s += 25; out.append(f"{int(_f(r['bundledN']))} bundled launch wallets")
    if r.get('snipersN') is not None and _f(r['snipersN']) >= 8:
        s += 15; out.append(f"{int(_f(r['snipersN']))} snipers in the first blocks")
    if ((r.get('tv') or {}).get('call') or [None, None])[1] == 'WASH TRADED':
        s += 25; out.append('wash-traded volume')
    if _f(r.get('txns1h')) > 0 and _f(r.get('vol1h')) / max(1.0, _f(r.get('txns1h'))) < 8:
        s += 10; out.append(f"${_f(r.get('vol1h')) / max(1.0, _f(r.get('txns1h'))):.0f} average trade — micro-buys")
    return min(100, s), out


def dip_tug(row, nums=None):
    """🪝 DIP TUGGERS: a coin that pumped and dumped (1h deep red or well off its 6h run) while buyers are STILL ≥ 50% — the crowd is trying
    to catch the dip. On a botted launch that is usually exit liquidity; on a clean one it is the bounce trade. → (is_tug, words)."""
    r, n = row or {}, nums or {}
    c1, c6 = r.get('chg1h') if r.get('chg1h') is not None else n.get('c1'), r.get('chg6h')
    b = r.get('buyShare') if r.get('buyShare') is not None else n.get('buy')
    dumped = (c1 is not None and _f(c1) <= -25) or (c6 is not None and _f(c6) >= 100 and c1 is not None and _f(c1) <= -15)
    if dumped and b is not None and _f(b) >= 50:
        return True, f"dumped ({_f(c1):+.0f}% 1h) and {_f(b):.0f}% of trades are still buys — tuggers catching the dip"
    return False, ''


def learn_lingo(state, theses, now, min_days=2, min_count=6):
    """📖 Learn new slang from human callouts: count each non-dictionary word per day (swarm copies counted once); a word seen ≥ `min_count`
    times on ≥ `min_days` days is LEARNED (kept with when it first showed up). → new state {days: {day: {word: n}}, learned: {word: {...}}}."""
    st = {'days': dict((state or {}).get('days') or {}), 'learned': dict((state or {}).get('learned') or {})}
    day = str(int(now // 86400))
    seen = set()
    uniq = []
    for t in theses or []:
        k = re.sub(r'[#$]?\w*\d+\w*', '', str(t or '').lower()).strip()
        if k and k not in seen:
            seen.add(k); uniq.append(t)
    d = dict(st['days'].get(day) or {})
    for t in uniq:
        for w in set(words(t)):
            if w not in SLANG and len(w) >= 3:
                d[w] = d.get(w, 0) + 1
    st['days'][day] = d
    st['days'] = dict(sorted(st['days'].items())[-7:])
    tot, days_ = {}, {}
    for dd in st['days'].values():
        for w, n in dd.items():
            tot[w] = tot.get(w, 0) + n; days_[w] = days_.get(w, 0) + 1
    for w, n in tot.items():
        if n >= min_count and days_[w] >= min_days and w not in st['learned'] and w not in STOP and w not in SLANG:   # old counts may hold stop words
            st['learned'][w] = {'first': now, 'n': n}
    for w in st['learned']:
        st['learned'][w]['n'] = tot.get(w, st['learned'][w].get('n', 0))
    return st


def hot_narratives(rows):
    """🌊 Which narratives the live list is riding right now: {key: {label, n, vol1h}} by 1h volume."""
    out = {}
    for r in rows or []:
        k, label = narrative(r)
        if k:
            o = out.setdefault(k, {'label': label, 'n': 0, 'vol1h': 0.0})
            o['n'] += 1; o['vol1h'] += _f(r.get('vol1h'))
    return dict(sorted(out.items(), key=lambda kv: -kv[1]['vol1h']))


# 😏 the voices — a line is chosen by the SITUATION (stable per coin, so it does not flicker), always the agent talking, never advice
QUIPS = {
    'tally': {'surge': ['Volume just put its seatbelt on.', 'The tape is louder than a group chat at ATH.'],
              'quiet': ['Volume left the chat.', 'Quieter than a dev after a rug.'],
              'falling': ['Numbers are doing a trust fall. Nobody caught it.'], 'default': ['I just count. The counting is not looking boring.']},
    'sherlock': {'bots': ['These buyers have the personality of a cron job.', 'Organic? This is a greenhouse with the lights off.'],
                 'swarm': ['Twenty callers, one keyboard.', 'That is not a crowd, that is a copy-paste with a ticker.'],
                 'narrative': ['Riding the {narr} meta like it owes them money.'], 'tug': ['Dip tuggers out here catching knives with oven mitts.'],
                 'default': ['Following the money, not the vibes.']},
    'trigger': {'enter': ['Clean entry. Not chasing, not catching — just walking in.', 'Door is open. Small ticket, no hero.'],
                'wait': ['Patience. The top is where jeets go to retire.', 'Not yet. Even the moon has a schedule.'],
                'skip': ['Hard pass. My exit liquidity era is over.', 'Nope. That chart has a lawyer.']},
    'devil': {'object': ['Respectfully: this is how bags are born.', 'Love the energy. Hate the bundles.', 'I have seen this movie. The dev leaves in act two.'],
              'agree': ['Fine. I looked for the rug and found carpet.', 'No smoking gun. Annoying, but fine.'], 'default': ['Somebody has to be the adult in the trenches.']},
}


def quip(agent, situation, seed='', **fmt):
    """One line in the agent's own voice for this situation; stable for a coin (the seed picks it) so the desk does not flicker."""
    bank = (QUIPS.get(agent) or {})
    lines = bank.get(situation) or bank.get('default') or ['']
    i = sum(ord(ch) for ch in str(seed)) % len(lines)
    try:
        return lines[i].format(**fmt)
    except (KeyError, IndexError):
        return lines[i]


def read(row, calls=None, hot=None):
    """🧠 The human read of one coin → {narr: (key, label, hot?), crowd: {...}, bots: (score, reasons), tug: (bool, words), drivers: [keys]}.
    The driver keys feed Sherlock (judged on the 5-min record like every driver): narr:<key>, narr_hot, crowd_real, swarm, botted, tug."""
    nk, nl = narrative(row)
    cr = crowd(calls)
    bs, bw = bots(row)
    tg, tw = dip_tug(row)
    is_hot = bool(nk and hot and nk in list(hot)[:3])
    ds = ([f'narr:{nk}'] if nk else []) + (['narr_hot'] if is_hot else [])
    if cr['callers'] >= 2:
        ds.append('swarm' if cr['swarm'] else 'crowd_real')
    if bs >= 40:
        ds.append('botted')
    if tg:
        ds.append('tug')
    return {'narr': (nk, nl, is_hot), 'crowd': cr, 'bots': (bs, bw), 'tug': (tg, tw), 'drivers': ds}


def analysis(sym, rd, nums, call, verdict, arg):
    """✍ A real paragraph from what the desk KNOWS about this coin — narrative, crowd, bots, the tape, the call, the argument — plus one line of
    each agent's humor. Not a template of numbers: every clause appears only when its evidence does."""
    n = nums or {}
    nk, nl, hot = rd['narr']
    cr, (bs, bw), (tg, tw) = rd['crowd'], rd['bots'], rd['tug']
    parts = []
    parts.append(f"${sym} rides the {nl} narrative" + (" — one of the hottest on the board right now" if hot else '') + '.' if nl else f"${sym} has no clear narrative — it trades on flow alone.")
    if cr['callers']:
        if cr['swarm']:
            parts.append(f"{cr['callers']} Pump callers, but {round(cr['swarmShare'] * 100)}% of the calls are the same line — a botted callout swarm, not a crowd.")
        else:
            talk = (f" talking {', '.join(cr['slang'])}" if cr['slang'] else '') + (' with real fear in the replies' if cr['fear'] > cr['hype'] else ' and the tone is hype' if cr['hype'] else '')
            parts.append(f"{cr['callers']} real caller{'s' if cr['callers'] != 1 else ''} on it{talk}.")
    if bs >= 40:
        parts.append(f"Botted launch signs: {'; '.join(bw[:2])}.")
    elif bw:
        parts.append(f"One bot flag ({bw[0]}), not enough to call it botted.")
    if tg:
        parts.append(tw[0].upper() + tw[1:] + ('. On a botted launch that is usually exit liquidity.' if bs >= 40 else '. On a clean launch that can be the bounce.'))
    if n.get('d5') is not None:
        parts.append(f"Tape: {_f(n['d5']):+.1f}% in 5 min" + (f", volume {n['pace']}× its hourly pace" if n.get('pace') is not None else '') + (f", {round(_f(n['buy']))}% buys" if n.get('buy') is not None else '') + '.')
    c = {'enter': 'Trigger says ENTER', 'wait': 'Trigger says WAIT', 'skip': 'Trigger says SKIP'}.get(call, '')
    v = {'agree': 'and Devil cannot knock it down', 'object': f'but Devil objects: {arg}'}.get(verdict, '')
    if c:
        parts.append(f"{c} {v}".strip() + '.')
    seed = sym or ''
    sit_s = 'swarm' if cr['swarm'] else 'bots' if bs >= 40 else 'tug' if tg else 'narrative' if nl else 'default'
    jokes = {'sherlock': quip('sherlock', sit_s, seed, narr=(nl or '').split(' ', 1)[-1]),
             'trigger': quip('trigger', call if call in ('enter', 'wait', 'skip') else 'wait', seed),
             'devil': quip('devil', verdict if verdict in ('agree', 'object') else 'default', seed),
             'tally': quip('tally', 'surge' if _f(n.get('pace')) >= 2 else 'quiet' if n.get('pace') is not None and _f(n['pace']) < 0.5 else 'falling' if _f(n.get('d5')) < -6 else 'default', seed)}
    return {'text': ' '.join(parts), 'jokes': jokes}
