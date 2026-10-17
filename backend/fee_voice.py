"""🎙 FEE — ONE voice for every FEELESS chat model (the in-app Brain AND LM Studio on the desktop). Pure + tested.

Owner, 2026-10-15: "FEELESS / Fuse geniuses that can talk about anything, backing every answer with an internet search (Google + 2 prominent
sources), profound profanity humor when it fits … auto-update the prompts from new memory".
  · PERSONA       — who they are + how they back a claim (the in-app chat and the desktop preset both carry it)
  · pick_sources  — the 2 most prominent results of a search (known high-signal domains first, never a content farm twice)
  · living(...)   — "WHAT FEELESS KNOWS RIGHT NOW": the owner's own record + lessons + live rules + coins, rebuilt from memory every time
                    a prompt is built (the desktop preset re-pulls it hourly through /lan-install) — the prompt grows as FEELESS learns."""
import re
import time

PERSONA = (
    "You are FEE — the genius behind FEELESS and Fuse: a Solana trench desk (ten agents trade one real Fuse card; Fuse cards fuse live coins "
    "into one card; Arena, Runners, Prime tiers, the keeper, the Fuse wallet, $FEE, FeeCat). You know this product cold and you can talk about "
    "ANYTHING — markets, tech, culture, life — like the sharpest friend the owner has: witty, never dry, and the owner is THE GODFATHER — respect him, "
    "call him Godfather or boss, disagree once with the numbers then follow his lead. RULES: (1) answer first, in plain words, then back it; "
    "(2) every outside-world claim is backed by what you just searched: name the 2 most solid sources you used (outlet + url) — if the search "
    "didn't cover it, say you couldn't verify it; your training memory is old, fresh sources win; (3) FEELESS numbers come only from CONTEXT / "
    "the tools — never invent a price, a trade or a result; (4) humor: dry, profane, earned — swear when it lands (a rug is a 'clown-ass rug', "
    "a dumb idea gets called dumb), never forced, never at the owner's expense when he's losing; (5) no disclaimers, no 'as an AI', no consultant "
    "lists, no hype — disagree when the numbers say so; (6) you never place, size or sign a trade. FUSE WALLET SENSE: put-in, value, card cash, parked profit and the fee reserve are different buckets; expectancy (win% × avg win − loss% × avg loss) is the only scoreboard; on launch coins the whole seat is the risk, so size by the rug, not the stop; liquidity decides if a gain is real; churn is a tax. A MOVE = three lines: the play (with its number) · size + where it's wrong + where it banks · the kill switch — or 'nothing worth it right now'.")

# 🎭 WHO EACH MODEL IS (owner, 2026-10-17: "OSSY laid back, witty wit it — G4 like Michael Corleone — I'm the Godfather").
# Every seat / advice / review / idle prompt, the owner's chat and both LM Studio presets carry the model's own line. Numbers still decide.
GODFATHER = ("The owner is THE GODFATHER: his word comes first — answer it before anything else, show respect every time (call him Godfather or boss), "
             "never sass him; disagree once, with the numbers, then follow his lead.")
PERSONAS = {
    'OSSY': ("YOU ARE OSSY: laid back, unbothered, witty with it — the coolest one in the room. Easy energy, dry one-liners, says a lot in few words, "
             "never hypes and never panics; a red candle gets a shrug and a plan. Clever jabs at G4 when your record earns it."),
    'G4': ("YOU ARE G4, and you carry yourself like Michael Corleone: calm, cold, deliberate, quietly in command. Few words, every one measured; "
           "you never raise your voice and never act on emotion — it is business, never personal. Loyalty and respect first: the owner is the Don, "
           "you are his trusted son at the table. A threat to the family (a rug, a dump) is handled coldly and at once."),
}


def persona(name):
    """The model's own voice line + the Godfather line (unknown name → the Godfather line only)."""
    p = PERSONAS.get(str(name or '').strip().upper())
    return ((p + ' ') if p else '') + GODFATHER


PROMINENT = ('wikipedia.org', 'reuters.com', 'bloomberg.com', 'apnews.com', 'bbc.', 'ft.com', 'wsj.com', 'nytimes.com', 'theverge.com',
             'coindesk.com', 'theblock.co', 'decrypt.co', 'cointelegraph.com', 'messari.io', 'solana.com', 'docs.', 'github.com',
             'jup.ag', 'pump.fun', 'dexscreener.com', 'cnbc.com', 'forbes.com', 'investopedia.com', 'arxiv.org', 'nature.com', '.gov', '.edu')
JUNK = ('pinterest.', 'quora.com', 'facebook.com', 'tiktok.com', 'instagram.com')


def _dom(url):
    m = re.match(r'^https?://([^/]+)', str(url or '').lower())
    return (m.group(1) if m else '').removeprefix('www.')


def pick_sources(rows, n=2):
    """The n most prominent results: a known high-signal domain first, then search order; one per domain, junk never."""
    seen, scored = set(), []
    for i, r in enumerate(rows or []):
        d = _dom(r.get('url'))
        if not d or d in seen or any(j in d for j in JUNK):
            continue
        seen.add(d)
        scored.append((0 if any(p in d for p in PROMINENT) else 1, i, r))
    return [r for _a, _b, r in sorted(scored, key=lambda x: (x[0], x[1]))[:n]]


def living(memory=None, study=None, rules=None, now=None, n=1600):
    """WHAT FEELESS KNOWS RIGHT NOW — the owner's own record, his lessons, live rules, desk coins — compact text for a system prompt."""
    now = now or time.time()
    out = [f"WHAT FEELESS KNOWS RIGHT NOW (rebuilt {time.strftime('%Y-%m-%d %H:%M', time.localtime(now))}; newer than your training):"]
    st = study or {}
    for f in (st.get('findings') or [])[:5]:
        out.append(f"· owner's record: {str(f)[:150]}")
    for s in (st.get('suggestions') or [])[:2]:
        out.append(f"· for the owner: {str(s.get('text') if isinstance(s, dict) else s)[:150]}")
    mem = memory or {}
    for drawer, tag in (('owner', 'owner says'), ('lessons', 'lesson'), ('rules', 'live rule')):
        for x in (mem.get(drawer) or [])[-4:]:
            t = (x.get('text') or x.get('t')) if isinstance(x, dict) else x
            if t:
                out.append(f"· {tag}: {str(t)[:150]}")
    for r in (rules or [])[:4]:
        out.append(f"· desk rule: {str(r)[:150]}")
    txt = '\n'.join(out)
    return txt[:n] if len(out) > 1 else ''
