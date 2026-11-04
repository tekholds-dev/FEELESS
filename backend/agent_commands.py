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
PROJECT = re.compile(r'(?is)^\s*(?:/project\s+|(?:build|make|code|create|start)\s+(?:me\s+)?(?:an?\s+)?(?:project|web\s*app|app)\s+(?:for\s+|of\s+|about\s+|that\s+|with\s+|showing\s+)?)(.{3,})$')
PROJECT_SYS = ('You build a small static web project of several files. index.html is required, and it loads its own css and js by relative path. No external files, fonts, images, packages or network requests: '
               'it runs sandboxed with no network, with no build step and no server. It must look finished and work at phone width. Reply with each file exactly like this and nothing else:\n'
               '=== FILE: index.html ===\n<contents>\n=== FILE: css/style.css ===\n<contents>\n=== END ===')
PROJECT_FILES_MAX = 12
PROJECT_BYTES_MAX = 400_000
_PROJECT_PATH = re.compile(r'^[A-Za-z0-9_-][\w.-]*(?:/[A-Za-z0-9_-][\w.-]*){0,3}$')
_PROJECT_EXT = re.compile(r'(?i)\.(html|css|js|mjs|json|md|txt|svg)$')
PAGE_SYS = ('You build one web page. Reply with ONE complete HTML file in a single ```html block and nothing else: inline CSS and JS, no external files, fonts, images or network requests (it runs sandboxed with no network). '
            'It must look finished and work at phone width.')
_FENCE = re.compile(r'```(?:html)?\s*\n(.*?)```', re.S | re.I)
# `make an image of` works as a typed command but is not offered yet: OpenRouter refuses image output under $1.00 account balance (real call 2026-11-04, HANDOFF AG11).
MAKE_COMMANDS = [('build a project ', 'Writes a small project of several files, files it in Creations with a .zip, and runs it on its monitor. Paid from its model budget'),
                 ('build a page ', 'Writes a full web page, files it in Creations, and previews it on its monitor. Paid from its model budget'),
                 ('write a post about ', 'Writes a post with sources. It lands in Creations › Posts')]
FREE_READS = COMMANDS[:-1]


def make_job(text):
    """→ {'kind': 'image' | 'page', 'prompt'} for a make command, or None."""
    t = str(text or '')
    for rx, kind in ((IMAGE, 'image'), (PROJECT, 'project'), (PAGE, 'page')):
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


# 👁 A Watch a Wallet run files as a folder (owner 2026-11-04): each address the browser really reported, with the lines about it. The chain check is what proves the address is real.
_ADDRESS = re.compile(r'(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])')
WATCH_KEEP = 20
WALLETS_MAX = 6


def wallets_in(answer):
    """→ [{'address', 'lines'}], in the order it named them. A line about a wallet is every line from its address to the next address."""
    out, now = [], None
    for raw in str(answer or '').splitlines():
        line = raw.strip(' *-•\t')
        if not line:
            continue
        hits = [a for a in _ADDRESS.findall(line) if re.search(r'\d', a) and re.search(r'[a-z]', a) and re.search(r'[A-Z]', a)]
        fresh = [a for a in hits if not any(a == w['address'] for w in out)]
        if fresh:
            now = {'address': fresh[0], 'lines': []}
            out.append(now)
            line = line.replace(fresh[0], '').strip(' :*-`')
        if now is not None and line and len(now['lines']) < 8:
            now['lines'].append(line[:200])
    return out[:WALLETS_MAX]


def watch_folder(task, now, n):
    """A finished run → its folder. No address in the answer files as that, never as a result."""
    wins = task.get('windows') or []
    sites = sorted({re.sub(r'^https?://(www\.)?', '', str(s.get('detail') or '')).split('/')[0] for w in wins for s in w.get('steps') or [] if s.get('action') == 'open' and str(s.get('detail') or '').startswith('http')})
    answer = str(task.get('answer') or '')
    wallets = wallets_in(answer)
    return {'id': f"watch{int(now)}", 'n': n, 'at': round(now), 'status': task.get('status'), 'why': str(task.get('why') or '')[:160], 'sites': sites[:8], 'cost': round(float(task.get('cost') or 0), 5),
            'wallets': wallets, 'answer': answer[:3000], 'checked': not wallets}


async def chain_check(http, url, address):
    """A real wallet has history on the chain. → {'txs', 'lastAt'}, or {'txs': None} when the RPC did not answer."""
    try:
        r = await http.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'getSignaturesForAddress', 'params': [address, {'limit': 20}]}, timeout=10)
        rows = (r.json() or {}).get('result')
    except Exception:   # noqa: BLE001 — an unanswered check is filed as unchecked
        return {'txs': None}
    if not isinstance(rows, list):
        return {'txs': None}
    return {'txs': len(rows), 'lastAt': rows[0].get('blockTime') if rows else None}


# 🧱 A coding agent's real project files (owner 2026-11-04, AG10). Static only: a project that needs a server waits for a sandbox host, and this says so instead of pretending.
def project_in(reply):
    """→ {path: text}, or None. A reply with no closing line was cut off, so it is never filed as finished. A path that climbs out of the project, or a file type that could run elsewhere, sinks the whole reply."""
    t = str(reply or '')
    if not re.search(r'(?m)^=== END ===\s*$', t):
        return None
    t = t[:re.search(r'(?m)^=== END ===\s*$', t).start()]
    parts = re.split(r'(?m)^=== FILE: (.+?) ===[ \t]*\n', t)
    files = {}
    for path, body in zip(parts[1::2], parts[2::2]):
        path = path.strip()
        if not _PROJECT_PATH.match(path) or '..' in path or not _PROJECT_EXT.search(path):
            return None
        files[path] = re.sub(r'^```\w*\n|\n```\s*$', '', body.rstrip('\n') + '\n').rstrip('\n') + '\n'
    if not files or 'index.html' not in files or len(files) > PROJECT_FILES_MAX or sum(len(v.encode()) for v in files.values()) > PROJECT_BYTES_MAX:
        return None
    return files if re.search(r'(?i)</(?:html|body)>', files['index.html']) else None


def project_preview(files):
    """index.html with its own css and js pulled in, so the sandboxed monitor runs the whole project with no server."""
    def rel(attr):
        return re.sub(r'^\./', '', attr)
    html = files['index.html']

    def css(m):
        body = files.get(rel(m.group(1)))
        return f'<style>{body}</style>' if body is not None else m.group(0)

    def js(m):
        body = files.get(rel(m.group(2)))
        return f"<script{m.group(1)}{m.group(3)}>{body.replace('</script', '<' + chr(92) + '/script')}</script>" if body is not None else m.group(0)
    html = re.sub(r'(?i)<link\b[^>]*?href=["\']([^"\']+\.css)["\'][^>]*>', css, html)
    return re.sub(r'(?is)<script\b([^>]*?)\s*src=["\']([^"\']+\.m?js)["\']([^>]*)>\s*</script>', js, html)
