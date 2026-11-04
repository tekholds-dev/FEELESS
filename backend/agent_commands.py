"""⚡ Free chat commands (owner 2026-11-04): instant trench + perp reads from FEELESS's own data, no model call, nothing bought.
Also the two words that shape an ask: Watch a Wallet becomes a real browser job, and a trader asked for non-trading work says it won't be as accurate."""
import re

COIN = r'\$?([A-Za-z0-9]{2,44})'
QUICK = [(re.compile(r'(?i)^\s*/?(?:price\s*gaps?|gaps?)\s*$'), 'gaps'),
         (re.compile(r'(?i)^\s*/?(?:trench(?:es)?|hot\s+coins)\s*$'), 'trench'),
         (re.compile(r'(?i)^\s*/?perps?\s*$'), 'perps'),
         (re.compile(r'(?i)^\s*/?(?:best\s+)?pools?\s*$'), 'pools')]
COIN_CMD = [(re.compile(rf'(?i)^\s*/?(?:check|rug\s*check|safe)\s+{COIN}\s*\??\s*$'), 'check'),
            (re.compile(rf'(?i)^\s*/?(?:history|prior)\s+{COIN}\s*$'), 'pow')]
COMMANDS = [('price gap', 'Free: price gaps between pools for the same coin, after swap costs'),
            ('trench', "Free: today's hottest Solana coins on FEELESS"),
            ('check $', 'Free: a coin\'s live read and whether it would pass the buy guards — type the coin'),
            ('history $', 'Free: every PoW ever filed on a coin and how it went — type the coin'),
            ('perps', 'Free: the perps desk markets and leverage'),
            ('watch a wallet', 'Its browser finds 3 top wallets on pump.fun and other sources, then reads their recent trades. Paid model calls')]

WATCH = re.compile(r'(?i)^\s*/?watch\s+(?:a\s+)?wallets?\s*(.*)$')
WATCH_GOAL = ('Find 3 top-performing Solana trader wallets. Open pump.fun and at least one other public source (gmgn.ai, birdeye.so, dexscreener.com top traders) in your browser, '
              'using real clicks. For each wallet: give its full address, the source page, and its last 5 trades you can see (coin, side, size, result). '
              'Say which wallet you trust most and why, from the numbers only. Do not buy anything.')

# Work a trader was not built for. Coin + market words win: "write up this coin" is still its job.
OFF_LANE = re.compile(r'(?i)\b(?:code|coding|program|script|website|web\s*app|landing\s*page|frontend|backend|debug|essay|blog|poem|story|resume|logo|image|picture|photo|video|tiktok|instagram|youtube|tweet\s+thread|email|homework|recipe|translate)\b')
MONEY = re.compile(r'(?i)\b(?:coin|token|memecoin|chart|trade|trading|perps?|wallet|pump|rug|liquidity|mcap|market\s*cap|sniper|holder|buy|sell|\$[a-z0-9]+)\b')
TRADER_NOTE = "🧭 Heads up: this is a trader agent, built for trading and perps. It will do this, but not as accurately as a General agent."


def quick(text):
    """→ {'tool', 'q'} for a free command, or None."""
    t = str(text or '')
    for rx, tool in QUICK:
        if rx.match(t):
            return {'tool': tool, 'q': ''}
    for rx, tool in COIN_CMD:
        m = rx.match(t)
        if m:
            return {'tool': tool, 'q': m.group(1)}
    return None


def watch_goal(text):
    """"watch a wallet" → the goal its browser works, keeping anything the owner added. None when it is not this command."""
    m = WATCH.match(str(text or ''))
    if not m:
        return None
    extra = m.group(1).strip()[:200]
    return WATCH_GOAL + (f' The owner adds: {extra}' if extra else '')


def off_lane(kind, text):
    """True when a trader was asked for work outside trading."""
    t = str(text or '')
    return kind != 'general' and bool(OFF_LANE.search(t)) and not MONEY.search(t)


def verdict(guards_ok, guards_why, safe_ok, safe_why):
    """A check's answer, in one line."""
    if not guards_ok:
        return f"🛑 It would NOT buy this: {guards_why}"
    if not safe_ok:
        return f"🛑 It would NOT buy this: {safe_why}"
    return f"✅ It passes the buy guards today ({safe_why}). That is not a call to buy."


# 🎨 What a General agent makes (owner 2026-11-04). Exact command words, so a sentence that merely mentions a page or a picture stays a normal ask.
IMAGE = re.compile(r'(?is)^\s*(?:/image\s+|(?:make|generate|create|draw)\s+(?:me\s+)?(?:an?\s+)?(?:image|picture|pic|drawing|logo)\s+(?:of\s+|for\s+|showing\s+)?)(.{3,})$')
PAGE = re.compile(r'(?is)^\s*(?:/page\s+|(?:build|make|code|create)\s+(?:me\s+)?(?:an?\s+)?(?:web\s*page|web\s*site|landing\s*page|page|site)\s+(?:for\s+|of\s+|about\s+|that\s+|with\s+|showing\s+)?)(.{3,})$')
PAGE_SYS = ('You build one web page. Reply with ONE complete HTML file in a single ```html block and nothing else: inline CSS and JS, no external files, fonts, images or network requests (it runs sandboxed with no network). '
            'It must look finished and work at phone width.')
_FENCE = re.compile(r'```(?:html)?\s*\n(.*?)```', re.S | re.I)
# `make an image of` works as a typed command but is not offered yet: OpenRouter refuses image output under $1.00 account balance (real call 2026-11-04, HANDOFF AG11).
MAKE_COMMANDS = [('build a page ', 'Writes a full web page, files it in Creations, and previews it on its monitor. Paid from its model budget'),
                 ('write a post about ', 'Writes a post with sources. It lands in Creations › Posts')]
FREE_READS = COMMANDS[:-1]


def make_job(text):
    """→ {'kind': 'image' | 'page', 'prompt'} for a make command, or None."""
    t = str(text or '')
    for rx, kind in ((IMAGE, 'image'), (PAGE, 'page')):
        m = rx.match(t)
        if m:
            return {'kind': kind, 'prompt': m.group(1).strip()[:1200]}
    return None


def page_in(reply):
    """The whole page in a model's reply, or None. A cut-off page, with no closing fence or tag, is never filed as finished."""
    t = str(reply or '')
    for m in _FENCE.finditer(t):
        if re.search(r'(?i)<(?:!doctype|html|body)\b', m.group(1)) and re.search(r'(?i)</(?:html|body)>', m.group(1)):
            return m.group(1).strip()
    bare = re.search(r'(?is)(?:<!doctype html|<html).*</html>', t)
    return bare.group(0).strip() if bare else None


def commands_for(kind, proofs):
    """A trader is offered money work. A General agent is offered making things, and the free reads. Either still does what it is told."""
    return MAKE_COMMANDS + FREE_READS if kind == 'general' else list(proofs) + COMMANDS
