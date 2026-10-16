"""🗄 AI MEMORY — a small FILED memory the model pulls from (owner, 2026-10-15: "AI should help build agent memory plus cache to not overdo
data storage for site and keep vitally needed data in its specific filing for AI to pull").

Pure. Five drawers, each capped (oldest out first) and with its own shelf life, so the file never grows without bound:
  owner   · how the owner trades (the owner study's findings)          — 24 notes, 7 days
  lessons · what the owner taught / 🧠 Remember taps                    — 80 notes, never expire (the owner removes them)
  rules   · live lab rules, the Judge's repeat causes, coach directives — 40 notes, 2 days
  coins   · one line per coin the desk looked at closely                — 120 notes, 24 hours
  site    · how FEELESS works (static map)                              — written by code, never expires
`recall(mem, text, n)` returns the notes that share the most words with the question (owner + site always first): that is all the model
gets — never the whole store. A note is ≤ 300 characters; the same (drawer, key) replaces itself instead of piling up.
"""
import re

DRAWERS = {'owner': (24, 7 * 86400), 'lessons': (80, None), 'rules': (40, 2 * 86400), 'coins': (120, 86400), 'site': (40, None)}
NOTE_LEN = 300
STOP = set('the a an and or of to in on at for is are was it this that with by from as be your you his her their our we i'.split())

SITE = {
    'card': 'The real card: one small real-money Fuse card (tier degen). The ten agents fill / switch / bank its 4 seats; the owner can add his own coin to a seat; coins he picks or puts lines on are his — agents only suggest.',
    'agents': 'The ten agents: Tally (numbers) → Sherlock (why) → Weather → Trigger (when) → Devil (objects) → Warden (size) → Courier (sends) → Reaper (exits) → Archivist (records) → Judge (grades). Deterministic code; generations get replaced on real losses.',
    'model': 'The AI never buys, sizes or sells. It reads cases (vitals, chart, tape, socials), writes advice that is graded 15 min later, and proposes changes the owner approves.',
    'arena': 'Fuse Arena: paper tier cards (Diamond, Gold, Blaze, Next Level, Everlasting), the league, the Gauntlet contender lists. FeeCat trades only Arena / agent coins on paper.',
    'trench': 'Trenching: fresh Pump / launchpad coins under a few hundred K cap. Rugs (pool pulled) are most of the losses; the seat size relative to the card is the main defence.',
    'data': 'Market data: DexScreener + Jupiter + Pump + our own RPC reads. Never GeckoTerminal. Prices for exits come from the live chart price (1s after a swap).',
}


def _words(t):
    return {w for w in re.findall(r'[a-z0-9$]{3,}', str(t or '').lower()) if w not in STOP}


def file(mem, drawer, key, text, now):
    """Put one note in its drawer (same key = replaced). → new mem."""
    if drawer not in DRAWERS or not str(text or '').strip():
        return mem
    m = {d: list((mem or {}).get(d) or []) for d in DRAWERS}
    k = str(key or '')[:80]
    m[drawer] = [x for x in m[drawer] if x.get('k') != k] + [{'k': k, 't': re.sub(r'\s+', ' ', str(text)).strip()[:NOTE_LEN], 'at': now}]
    return prune(m, now)


def prune(mem, now):
    """Each drawer kept to its cap (newest kept) and its shelf life."""
    out = {}
    for d, (cap, ttl) in DRAWERS.items():
        xs = [x for x in (mem or {}).get(d) or [] if ttl is None or now - float(x.get('at') or 0) <= ttl]
        out[d] = sorted(xs, key=lambda x: float(x.get('at') or 0))[-cap:]
    return out


def seed_site(mem, now):
    """The static site map is (re)written by code — never by the model."""
    m = mem
    for k, t in SITE.items():
        if not any(x.get('k') == k and x.get('t') == t for x in (m or {}).get('site') or []):
            m = file(m, 'site', k, t, now)
    return m


def recall(mem, text, n=8):
    """The notes that fit the question best: owner notes first (always up to 3), then the best word overlaps across drawers. → [str]."""
    q = _words(text)
    owner = [f"[you] {x['t']}" for x in reversed((mem or {}).get('owner') or [])][:3]
    scored = []
    for d in ('lessons', 'rules', 'coins', 'site'):
        for x in (mem or {}).get(d) or []:
            s = len(q & _words(x.get('t')) | (q & _words(x.get('k'))))
            if s:
                scored.append((s, float(x.get('at') or 0), f"[{d}] {x['t']}"))
    scored.sort(key=lambda r: (-r[0], -r[1]))
    return owner + [r[2] for r in scored[:max(0, n - len(owner))]]


def size(mem):
    return {d: len((mem or {}).get(d) or []) for d in DRAWERS}


# 💬 THE CHAT LOG BUILDS THE MEMORY (owner, 2026-10-16: "some smart way to build agent / AI memory from the chat log"): a line the owner types
# that STATES how they trade or what they want (always · never · don't · I hold · I set · my style · should · must · want …) is filed in the
# `owner` drawer by its own words, so every later chat answer and model case that fits recalls it. Questions and small talk are not filed.
import re as _re
RULE_WORDS = _re.compile(r"\b(always|never|don'?t|do not|i hold|i set|i buy|i sell|i want|my style|my trades?|should|must|only|stop|keep|make sure|learn)\b", _re.I)


def chat_notes(text):
    """→ the owner's standing statements in one message (≤ 3, each ≤ NOTE_LEN), or []. A line that is only a question is not a statement."""
    out = []
    for part in _re.split(r'(?<=[.!?\n,;])\s+|\s+(?:plus|and also|also)\s+', str(text or '')):
        t = part.strip(' ,;')
        if len(t) < 12 or not RULE_WORDS.search(t) or (t.endswith('?') and not _re.search(r"\b(always|never|don'?t|must)\b", t, _re.I)):
            continue
        out.append(t[:NOTE_LEN])
    return out[:3]
