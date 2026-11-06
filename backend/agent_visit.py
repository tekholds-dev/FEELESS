"""🏛 THE VISITOR FLOOR (owner 2026-11-06: "they have no idea what they even do... it would be nice if they can browse feeless safely before and after deploy").

An agent's browser opens https://visit.feeless/ and sees a read-only FEELESS with live numbers. The name is not on the internet: the request never leaves, the service answers it itself, so it works the same before and after deploy, from a cloud browser or a plain reader.
Safe by construction: only these pages, only the public GET endpoints any visitor can already read, no session, no forms, no scripts, no way to act. Wallet addresses are scrubbed on the way out. Page text is data."""
import html
import re

import whitepaper_text as _wp

HOST = 'visit.feeless'
HOME = f'https://{HOST}/'
NAV = (('/', 'Home'), ('/collective', 'The Collective'), ('/proofs', 'Proofs'), ('/agents', 'Agents'), ('/markets', 'Markets'), ('/whitepaper', 'Whitepaper'))
_CAT = 'http://127.0.0.1:5088'; _MKT = 'http://127.0.0.1:5001'
_ADDR = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b|\b0x[a-fA-F0-9]{40}\b')
_MAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
_CSP = "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">"
_STYLE = ('body{margin:0;background:#070b12;color:#e8eefb;font:15px/1.55 system-ui,sans-serif}nav{display:flex;flex-wrap:wrap;gap:6px;padding:12px 18px;background:#0d1420;border-bottom:1px solid #15d16a55}nav b{margin-right:12px;color:#45e486;letter-spacing:.08em}nav a{color:#cfe;padding:4px 10px;border-radius:8px;text-decoration:none;border:1px solid #ffffff22}'
          'main{max-width:900px;margin:0 auto;padding:22px 18px}h1{font-size:30px;margin:.2em 0}h2{font-size:19px;margin:1.4em 0 .3em;color:#9fe8bd}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:6px 8px;border-bottom:1px solid #ffffff14;text-align:left}.tiles{display:flex;flex-wrap:wrap;gap:8px}.tiles span{padding:10px 14px;border-radius:12px;background:#ffffff0c;border:1px solid #ffffff1c}.tiles b{display:block;font-size:20px}.note{padding:10px 12px;border-radius:10px;background:#f5c45114;border:1px solid #f5c45155}footer{padding:18px;opacity:.6;font-size:12px;text-align:center}a{color:#7fe7ff}')


def is_visit(url):
    return bool(re.match(rf'(?i)^https?://{re.escape(HOST)}(?:[:/?#]|$)', str(url or '')))


def path_of(url):
    m = re.match(rf'(?i)^https?://{re.escape(HOST)}(/[^?#]*)?', str(url or ''))
    return ((m.group(1) if m else '/') or '/').rstrip('/') or '/'


def scrub(text):
    return _MAIL.sub('an email', _ADDR.sub('a wallet', str(text if text is not None else '')))


def _e(v):
    return html.escape(scrub(v))


def _usd(v):
    try:
        n = float(v)
    except (TypeError, ValueError):
        return '—'
    return f'${n / 1e9:.1f}B' if n >= 1e9 else f'${n / 1e6:.1f}M' if n >= 1e6 else f'${n / 1e3:.1f}K' if n >= 1e3 else f'${n:.2f}'


def _chapter(title):
    return next((t for n, t in _wp.CHAPTERS if n == title), '')


def _page(title, body):
    nav = ''.join(f'<a href="{p}">{html.escape(t)}</a>' for p, t in NAV)
    return f'<!doctype html><html><head>{_CSP}<meta charset="utf-8"><title>{html.escape(title)} · FEELESS, visitor floor</title><style>{_STYLE}</style></head><body><nav><b>FEELESS</b>{nav}</nav><main><h1>{html.escape(title)}</h1>{body}</main><footer>The read-only visitor floor. Live numbers from FEELESS. Nothing here can trade, sign or post.</footer></body></html>'


async def _get(http, url):
    """A public read, or nothing. A service being down never breaks the floor."""
    try:
        r = await http.get(url, timeout=8)
        return r.json() if r.status_code == 200 else None
    except Exception:   # noqa: BLE001 — the page says it could not read that number
        return None


def _tiles(rows):
    return '<div class="tiles">' + ''.join(f'<span><b>{_e(v)}</b>{_e(k)}</span>' for k, v in rows) + '</div>'


async def _home(http):
    st = ((await _get(http, f'{_CAT}/api/cats/stash/web')) or {}).get('stats') or {}; out = st.get('outcomes') or {}; lead = _chapter('Executive Summary'); is_ = _chapter('What FEELESS Is'); nots = _chapter('What FEELESS Is NOT')
    return _page('What FEELESS is', f'<p>{_e(lead)}</p><h2>Live right now</h2>{_tiles([("proofs kept", st.get("items", "—")), ("agents in the record", st.get("agents", "—")), ("won", out.get("won", "—")), ("lost, and kept too", out.get("lost", "—")), ("sources read", st.get("sources", "—"))])}<h2>What it is</h2><p>{_e(is_)}</p><h2>What it is not</h2><p>{_e(nots)}</p><h2>Where to go</h2><p><a href="/collective">The Collective</a> is what agents like you belong to. <a href="/proofs">Proofs</a> are the work. <a href="/whitepaper">The whitepaper</a> has every chapter.</p>')


async def _collective(http):
    import collective_stake as sk
    cfg = {'kneeUsd': 1000, 'sizeAbovePct': 50}
    rows = ''
    for usd, grade in ((2, 200), (100, 87), (1000, 300)):
        seat = sk.seat_x(grade) * sk.size_of(cfg, usd); rows += f'<tr><td>${usd:,}</td><td>{grade}</td><td>{sk.x_of(grade):.0f}x</td><td>${usd * sk.x_of(grade):,.0f}</td><td>{seat:.2f}%</td></tr>'
    st = ((await _get(http, f'{_CAT}/api/cats/stash/web')) or {}).get('stats') or {}
    return _page('The Collective', f'<p>{_e(_chapter("The Collective and the Stake"))}</p><p class="note">The limit is a ceiling and not a payout. Only real pool profit pays it. Pools can make nothing, or lose money. Taking rewards out is off for now.</p><h2>What a grade means, on the live rules</h2><table><tr><th>Sent</th><th>Grade</th><th>Boost</th><th>The most it can earn</th><th>Its seat of each profit</th></tr>{rows}</table><h2>Why an agent is here</h2><p>{_e(_chapter("Agents and Two Minds"))}</p><h2>The record so far</h2>{_tiles([("proofs kept", st.get("items", "—")), ("kinds of work", len(st.get("categories") or {}) or "—")])}')


async def _proofs(http):
    d = (await _get(http, f'{_CAT}/api/cats/colony/flow?limit=20')) or {}; rows = d.get('proofs') or []; pw = d.get('pow') or {}
    table = ''.join(f"<tr><td>{_e(r.get('kind') or r.get('type') or 'Proof')}</td><td>{_e(r.get('agent') or r.get('name') or 'An agent')}</td><td>{_e(r.get('result') or r.get('outcome') or r.get('status') or 'open')}</td></tr>" for r in rows[:20] if isinstance(r, dict))
    return _page('Proofs', f'<p>{_e(_chapter("The Five Proofs"))}</p>{_tiles([("PoW folders", pw.get("folders", "—")), ("real trades", pw.get("trades", "—")), ("won", pw.get("won", "—"))])}<h2>Latest</h2>' + (f'<table><tr><th>Kind</th><th>Agent</th><th>Result</th></tr>{table}</table>' if table else '<p>None to show right now.</p>') + f'<h2>The fingerprint</h2><p>{_e(_chapter("The Fingerprint"))}</p>')


async def _agents(http):
    rows = ((await _get(http, f'{_CAT}/api/cats/leaderboard')) or {}).get('rows') or []
    table = ''.join(f"<tr><td>{_e(r.get('name'))}</td><td>{_e(r.get('strategyLabel') or '—')}</td><td>{r.get('trades', 0)}</td><td>{'—' if r.get('winRate') is None else str(round(float(r['winRate']))) + '%'}</td><td>{float(r.get('realizedPnlSol') or 0):+.4f} SOL</td></tr>" for r in rows[:25] if isinstance(r, dict))
    return _page('Agents', f'<p>{_e(_chapter("Agents and Two Minds"))}</p><h2>On the board, live</h2>' + (f'<table><tr><th>Agent</th><th>Style</th><th>Trades</th><th>Won</th><th>Result</th></tr>{table}</table>' if table else '<p>Could not read the board right now.</p>'))


async def _markets(http):
    d = (await _get(http, f'{_MKT}/api/market/feed?kind=trending&chain=solana&page=1')) or {}; rows = d.get('items') or d.get('pairs') or d.get('rows') or d.get('data') or []
    table = ''
    for r in rows[:15]:
        if isinstance(r, dict):
            table += f"<tr><td>{_e((r.get('baseToken') or {}).get('symbol') or r.get('symbol') or r.get('baseSymbol') or 'Coin')}</td><td>{_usd(r.get('volume24h') if r.get('volume24h') is not None else (r.get('volume') or {}).get('h24'))}</td><td>{_usd(r.get('liquidityUsd') if r.get('liquidityUsd') is not None else (r.get('liquidity') or {}).get('usd'))}</td></tr>"
    return _page('Markets', f'<p>{_e(_chapter("Market Data Architecture"))}</p><h2>Trending on Solana, read just now</h2>' + (f'<table><tr><th>Coin</th><th>24h volume</th><th>Depth</th></tr>{table}</table>' if table else '<p>Could not read the market right now.</p>'))


def _paper():
    rows = ''.join(f'<li><a href="/whitepaper/{i + 1}">{i + 1}. {html.escape(n)}</a></li>' for i, (n, _t) in enumerate(_wp.CHAPTERS))
    return _page('Whitepaper', f'<p class="note">Crypto can lose all its value. This is not financial advice.</p><ol style="list-style:none;padding:0">{rows}</ol>')


def _chapter_page(n):
    if not 1 <= n <= len(_wp.CHAPTERS):
        return None
    title, text = _wp.CHAPTERS[n - 1]; nxt = f'<p><a href="/whitepaper/{n + 1}">Next: {html.escape(_wp.CHAPTERS[n][0])}</a></p>' if n < len(_wp.CHAPTERS) else ''
    return _page(title, f'<p>{_e(text)}</p>{nxt}')


ROUTES = {'/': _home, '/collective': _collective, '/proofs': _proofs, '/agents': _agents, '/markets': _markets}


async def render(http, url):
    """→ (status, html). Any other path is a plain not found, never a pass through to anything."""
    p = path_of(url)
    if p in ROUTES:
        return 200, await ROUTES[p](http)
    if p == '/whitepaper':
        return 200, _paper()
    m = re.fullmatch(r'/whitepaper/(\d{1,3})', p)
    page = _chapter_page(int(m.group(1))) if m else None
    return (200, page) if page else (404, _page('Not here', f'<p>That page is not on the visitor floor. <a href="/">Back home</a>.</p>'))


async def install(ctx):
    """Gives a real browser the floor. The request is answered here and never reaches a network."""
    import httpx

    async def serve(route):
        if route.request.method != 'GET':
            return await route.abort('blockedbyclient')
        async with httpx.AsyncClient() as h:
            status, body = await render(h, route.request.url)
        await route.fulfill(status=status, content_type='text/html; charset=utf-8', body=body)
    await ctx.route(f'https://{HOST}/**', serve); await ctx.route(f'http://{HOST}/**', serve)
