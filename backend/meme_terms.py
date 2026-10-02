"""📖 Meme terms: the reputation engine learns the trench's language every day — pure, tested.

Coins that launch today (names + tickers) and FEELESS chat are counted per term per day. A term is NEW TODAY when it shows up
at least `MIN_TODAY` times and ≥ `SPIKE`× its average over the last 7 days (or never before). Known slang comes with its
meaning from `GLOSSARY`; an unknown term is LEARNED from where it shows up: mostly coin names = a 🌊 ticker wave (copycats ride
it — a wave coin that wasn't first is flagged as a copycat), mostly chat = 💬 chat slang. Nothing here is a buy signal.
"""
import re

KEEP_DAYS = 8
MIN_TODAY = 3
SPIKE = 3.0
MAX_TERMS_PER_DAY = 3000

# Known trench slang → (meaning, kind). Kinds: slang | risk | hype | meta. The engine also learns words that aren't here.
GLOSSARY = {
    'jeet': ('sells the first green candle', 'slang'), 'jeets': ('people who sell the first green candle', 'slang'),
    'ape': ('buy in fast, no research', 'slang'), 'aped': ('bought in fast', 'slang'), 'aping': ('buying in fast', 'slang'),
    'cto': ('community takeover — the dev left, holders run it', 'meta'), 'rug': ('liquidity pulled / dev dumped', 'risk'),
    'rugged': ('liquidity pulled / dev dumped', 'risk'), 'bundle': ('dev bought supply across many wallets at launch', 'risk'),
    'bundled': ('supply bought across many wallets at launch', 'risk'), 'sniper': ('bot that buys in the first block', 'risk'),
    'snipers': ('bots that buy in the first blocks', 'risk'), 'cabal': ('insider group moving a coin together', 'risk'),
    'pvp': ('traders fighting over the same fresh launches', 'meta'), 'kol': ('influencer whose calls move coins', 'meta'),
    'lfg': ("let's go — hype", 'hype'), 'wagmi': ("we're all gonna make it", 'hype'), 'ngmi': ('not gonna make it', 'slang'),
    'gm': ('good morning — daily hello', 'slang'), 'moon': ('price going way up', 'hype'), 'mooning': ('price going way up', 'hype'),
    'send': ('push the price up hard', 'hype'), 'sendit': ('push it up hard', 'hype'), 'mog': ('outshine / dominate', 'slang'),
    'mogging': ('outshining', 'slang'), 'bags': ('coins you hold', 'slang'), 'bagholder': ('stuck holding a dead coin', 'slang'),
    'rekt': ('lost big', 'slang'), 'fud': ('fear, uncertainty, doubt — bad-news posting', 'slang'), 'shill': ('pushing a coin hard', 'slang'),
    'alpha': ('early, useful info', 'meta'), 'dyor': ('do your own research', 'slang'), 'paperhands': ('sells too early', 'slang'),
    'diamondhands': ('never sells', 'slang'), 'larp': ('pretending / faking it', 'slang'), 'chad': ('confident winner', 'slang'),
    'based': ('bold and right', 'slang'), 'cooked': ('done for', 'slang'), 'aura': ('vibe / status', 'slang'),
    'rizz': ('charm', 'slang'), 'sigma': ('lone-wolf winner meme', 'slang'), 'bonding': ('pump.fun curve before graduation', 'meta'),
    'migrated': ('graduated off the bonding curve to a DEX', 'meta'), 'graduated': ('left the bonding curve for a DEX', 'meta'),
    'devsold': ('the creator sold their coins', 'risk'), 'exitliq': ('late buyers that early sellers dump on', 'risk'),
    'honeypot': ('a coin you can buy but not sell', 'risk'), 'airdrop': ('free tokens — often bait in DMs', 'risk'),
    'pump': ('price going up / pump.fun', 'meta'), 'dump': ('price crashing', 'slang'), 'wen': ('when? (impatient)', 'slang'),
    'ser': ('sir — polite trench speak', 'slang'), 'fren': ('friend', 'slang'), 'degen': ('high-risk trader', 'slang'),
    'giga': ('huge', 'hype'), 'brainrot': ('absurd internet humour coins', 'meta'), 'goat': ('greatest of all time', 'hype'),
}
STOP = set('the and for you your with this that from are was have has not but all can get got its our out who how why what when new '
           'coin token sol solana pump fun official inu the of to in on is it a an by be me my we us so up no do go oh ok yes yea '
           'just like will now one two lol lmao gonna wanna dont cant im ive its thats there their them they then than here'.split())
_WORD = re.compile(r"[a-z][a-z0-9]{2,19}")


def tokenize(text):
    """Lower-cased words 3–20 chars (a $TICKER counts as its word), stopwords and pure numbers dropped. One count per text."""
    t = re.sub(r'\$', ' ', str(text or '').lower())
    t = t.replace('paper hands', 'paperhands').replace('diamond hands', 'diamondhands').replace('dev sold', 'devsold').replace('exit liq', 'exitliq').replace('send it', 'sendit')
    return sorted({w for w in _WORD.findall(t) if w not in STOP})


def day_of(ts):
    return int(ts // 86400)


def learn(state, samples, now):
    """samples = [(text, source 'coin'|'chat', ref)]. Counts per day per term + where each term was seen; keeps 8 days."""
    s = state if isinstance(state, dict) else {}
    days = s.setdefault('days', {}); first = s.setdefault('firstSeen', {}); refs = s.setdefault('refs', {}); src = s.setdefault('src', {})
    seen_refs = s.setdefault('seenRefs', {})
    today = str(day_of(now))
    bucket = days.setdefault(today, {})
    done = set(seen_refs.get(today) or [])
    for text, source, ref in samples or []:
        key = f'{source}:{ref}'
        if ref and key in done:
            continue                       # the same coin / message counts once a day
        done.add(key)
        for w in tokenize(text):
            if w not in bucket and len(bucket) >= MAX_TERMS_PER_DAY:
                continue
            bucket[w] = bucket.get(w, 0) + 1
            first.setdefault(w, now)
            sc = src.setdefault(w, {'coin': 0, 'chat': 0}); sc['coin' if source == 'coin' else 'chat'] += 1
            if source == 'coin' and ref and ref not in (refs.get(w) or []):
                refs[w] = ((refs.get(w) or []) + [ref])[-6:]
    seen_refs[today] = sorted(done)[-5000:]
    for k in [k for k in days if int(k) < day_of(now) - KEEP_DAYS]:
        days.pop(k, None)
    for k in [k for k in seen_refs if k != today]:
        seen_refs.pop(k, None)
    return s


def trending(state, now, limit=24):
    """Terms new or spiking today, each with what it means (known) or what the engine learned (wave / chat slang)."""
    days = (state or {}).get('days') or {}
    today = days.get(str(day_of(now))) or {}
    prev = [days.get(str(day_of(now) - i)) or {} for i in range(1, 8)]
    n_prev = max(1, sum(1 for d in prev if d))
    out = []
    for w, c in today.items():
        if c < MIN_TODAY:
            continue
        base = sum(d.get(w, 0) for d in prev) / n_prev
        if base and c < base * SPIKE:
            continue
        sc = ((state.get('src') or {}).get(w)) or {'coin': 0, 'chat': 0}
        known = GLOSSARY.get(w)
        kind = known[1] if known else 'wave' if sc['coin'] >= sc['chat'] else 'chat'
        meaning = known[0] if known else (f"🌊 ticker wave — {sc['coin']} coins named after it today; the first one usually runs, copycats usually don't"
                                          if kind == 'wave' else f"💬 new chat slang — {sc['chat']} mentions today (still learning what it means)")
        out.append({'term': w, 'today': c, 'base': round(base, 1), 'spike': round(c / base, 1) if base else None, 'new': not base,
                    'known': bool(known), 'kind': kind, 'meaning': meaning, 'coins': ((state.get('refs') or {}).get(w) or [])[-4:],
                    'firstSeen': (state.get('firstSeen') or {}).get(w)})
    return sorted(out, key=lambda x: (-(x['new']), -x['today']))[:limit]


def wave_of(name, symbol, trend):
    """The trending ticker wave a coin rides (copycat check), or None."""
    words = set(tokenize(f'{name} {symbol}'))
    hit = [t for t in trend or [] if t['kind'] == 'wave' and t['term'] in words]
    return max(hit, key=lambda t: t['today']) if hit else None


def explain(state, term):
    w = str(term or '').lower().strip('$ ')
    if w in GLOSSARY:
        return {'term': w, 'known': True, 'meaning': GLOSSARY[w][0], 'kind': GLOSSARY[w][1]}
    sc = ((state or {}).get('src') or {}).get(w)
    if not sc:
        return {'term': w, 'known': False, 'meaning': 'not seen in the trenches yet', 'kind': None}
    return {'term': w, 'known': False, 'kind': 'wave' if sc['coin'] >= sc['chat'] else 'chat',
            'meaning': f"seen in {sc['coin']} coin names and {sc['chat']} chat messages", 'coins': ((state.get('refs') or {}).get(w) or [])[-4:]}
