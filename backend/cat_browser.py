"""🌐 THE GENERAL CAT'S BROWSERS (owner 2026-10-29, P2: "2 browser windows … the AI models use their browser for users to see them work"; "free hosted
browser that doesn't cause lag or device burn, and fallbacks for the AIs if a service flops"). One window per model, run in the CLOUD — never on the
user's device. A provider CHAIN, first that answers wins:
  1. Steel        (STEEL_API_KEY)                            — the free credit tier, primary; a live view the owner can watch
  2. Browserless  (BROWSERLESS_API_KEY)                      — backup; CDP only (no shareable live view → the window shows snapshots)
  3. Browserbase  (BROWSERBASE_API_KEY + BROWSERBASE_PROJECT_ID) — backup; its live view lets the user click / type (human-needed sign-ins)
  4. reader       (always)                                   — no live browser: pages fetched as text by the server, so the models never stop
A session = {provider, id, live, connect, at}. `live` is the watch / take-over URL for the cat's OWNER only — and only when it carries none of our
keys (`safe_live`); otherwise the window shows snapshots. `connect` (the CDP address, may hold a key) never leaves the server.
FEELESS stores no passwords: a user signs in inside the live window themselves; the provider's saved context keeps the session, not us."""
import asyncio
import html
import json
import re
import uuid
from cat_policy import public_url, check_url

STEEL = 'https://api.steel.dev/v1'
BB = 'https://api.browserbase.com/v1'
TIMEOUT_MS = 15 * 60 * 1000      # Steel's free tier caps a session at 15 min — a window is reopened on the next task
TEXT_MAX = 6000                  # page text handed to a model per read


def keys(env):
    return {k: str((env or {}).get(k) or '').strip() for k in ('STEEL_API_KEY', 'BROWSERLESS_API_KEY', 'BROWSERBASE_API_KEY', 'BROWSERBASE_PROJECT_ID')}


def chain(env):
    """The providers this server can use, in order (reader always last)."""
    k = keys(env)
    return [p for p, ok in (('steel', k['STEEL_API_KEY']), ('browserless', k['BROWSERLESS_API_KEY']), ('browserbase', k['BROWSERBASE_API_KEY'] and k['BROWSERBASE_PROJECT_ID'])) if ok] + ['reader']


VIEWPORT = {'width': 1440, 'height': 900}   # 🖥 HD: the page fills the window on the desk (owner 2026-10-30: "cover the whole plot, HD")


def steel_view(url, hand=False):
    """Steel's live view, page only: no control bar, dark. LOCKED by default — only the models drive an agent window (owner 2026-10-31);
    `hand=True` is the clickable view a person gets for a sign-in / bot check. None stays None."""
    if not url:
        return url
    return url + ('&' if '?' in url else '?') + f"showControls=false&theme=dark&interactive={'true' if hand else 'false'}"


def safe_live(url, env):
    """A live URL may reach the owner's page only if it holds none of our secrets."""
    u = str(url or '')
    if not u.startswith('https://'):
        return None
    return None if any(v and v in u for v in keys(env).values()) or re.search(r'(?i)api[-_]?key=', u) else u


def _reader(note=None):
    return {'provider': 'reader', 'id': uuid.uuid4().hex[:12], 'live': None, 'connect': None, **({'note': note} if note else {})}


async def _steel(http, env, ctx=None):
    k = keys(env)['STEEL_API_KEY']
    body = {'timeout': TIMEOUT_MS, 'solveCaptcha': False, 'blockAds': True, 'dimensions': VIEWPORT, **({'sessionContext': ctx} if isinstance(ctx, dict) else {})}
    r = await http.post(f'{STEEL}/sessions', headers={'steel-api-key': k, 'Content-Type': 'application/json'}, json=body, timeout=20)
    if r.status_code not in (200, 201):
        raise ValueError(f'Steel {r.status_code}')
    j = r.json() or {}
    sid = j.get('id')
    if not sid:
        raise ValueError('Steel gave no session id')
    view = safe_live(j.get('debugUrl') or j.get('sessionViewerUrl'), env)
    return {'provider': 'steel', 'id': sid, 'live': steel_view(view), 'hand': steel_view(view, hand=True),
            'connect': j.get('websocketUrl') or f'wss://connect.steel.dev?apiKey={k}&sessionId={sid}'}


BROWSERLESS = 'wss://production-sfo.browserless.io'


async def _browserless(http, env, ctx=None):
    """Browserless needs no session call: the CDP address IS the session (it holds the token → server-only, never shown)."""
    return {'provider': 'browserless', 'id': uuid.uuid4().hex[:12], 'live': None, 'connect': f"{BROWSERLESS}?token={keys(env)['BROWSERLESS_API_KEY']}&timeout={TIMEOUT_MS}"}


async def _bb(http, env, ctx=None):
    k = keys(env)
    h = {'X-BB-API-Key': k['BROWSERBASE_API_KEY'], 'Content-Type': 'application/json'}
    body = {'projectId': k['BROWSERBASE_PROJECT_ID'], 'keepAlive': False, **({'browserSettings': {'context': {'id': ctx, 'persist': True}}} if isinstance(ctx, str) else {})}
    r = await http.post(f'{BB}/sessions', headers=h, json=body, timeout=20)
    if r.status_code not in (200, 201):
        raise ValueError(f'Browserbase {r.status_code}')
    j = r.json() or {}
    sid = j.get('id')
    if not sid:
        raise ValueError('Browserbase gave no session id')
    live = None
    try:
        d = await http.get(f'{BB}/sessions/{sid}/debug', headers=h, timeout=15)
        live = safe_live((d.json() or {}).get('debuggerFullscreenUrl'), env) if d.status_code == 200 else None
    except Exception:
        live = None
    return {'provider': 'browserbase', 'id': sid, 'live': live, 'hand': live, 'connect': j.get('connectUrl')}


async def open_session(http, env, ctx=None):
    """→ (session, tried) — the first provider that answers; `tried` = [(provider, why it failed)] so the window can say which flopped."""
    tried = []
    for p in chain(env):
        if p == 'reader':
            return _reader('; '.join(f'{a} {b}' for a, b in tried) or None), tried
        try:
            return await {'steel': _steel, 'browserless': _browserless, 'browserbase': _bb}[p](http, env, ctx), tried
        except Exception as e:
            tried.append((p, str(e)[:80] or 'no answer'))
    return _reader(), tried


# 🔓 SIGNED-IN SITES (owner 2026-10-31: "click a bot-blocked site in the drawer, sign in, and agents open the browser signed in already"): the OWNER
# signs in (and clears any check) by hand in a live Steel window; we keep that window's cookies + local storage, sealed per agent, and every
# later window starts with them. Nothing is bypassed — a person did the sign-in; a site that re-checks still asks a person.
CTX_MAX = 400_000


async def read_context(http, env, sid):
    """A live Steel session's cookies + local storage (indexedDB / session storage are left out — too big, rarely the sign-in)."""
    r = await http.get(f'{STEEL}/sessions/{sid}/context', headers={'steel-api-key': keys(env)['STEEL_API_KEY']}, timeout=20)
    if r.status_code != 200:
        raise ValueError(f'Steel context {r.status_code}')
    j = r.json() or {}
    return {'cookies': list(j.get('cookies') or []), 'localStorage': dict(j.get('localStorage') or {})}


# 🧼 SIGN-IN HYGIENE (owner 2026-10-31: "cookies cleaned + encrypted so only agents use them, no hacker can inject anything — why does Proton
# have 80 cookies? keep only the latest"): what a sign-in leaves is cut to the SITE'S OWN first-party cookies, the newest copy of each, nothing
# expired, no analytics / ad trackers, no stale older login (a site's AUTH-<id> pairs: only the newest id stays), every field checked (no
# newline / semicolon smuggling, sane sizes, only the keys a browser takes). Run on every save AND every load; sealed per agent (Fernet = tamper-proof).
SITE_FAMILY = {'x.com': ('x.com', 'twitter.com'), 'twitter.com': ('x.com', 'twitter.com'), 'google.com': ('google.com', 'accounts.google.com'),
               'proton.me': ('proton.me', 'protonmail.com'), 'telegram.org': ('telegram.org', 't.me')}
TRACKER = re.compile(r'^(_ga|_gid|_gat|_gcl|__utm|_fbp|_fbc|fr$|_hj|ajs_|_uet|_clck|_clsk|_clid|mp_|amplitude|_tt_|_ttp|_pin_|_rdt|_scid|_sctr|__hs|hubspot|_mkto|intercom-|optimizely|_dc_gtm|IDE$|test_cookie$|personalization_id$|guest_id_ads$|guest_id_marketing$)', re.I)
COOKIE_KEYS = ('name', 'value', 'domain', 'path', 'expires', 'httpOnly', 'secure', 'sameSite', 'priority', 'sourceScheme', 'sourcePort')
BAD = re.compile(r'[\r\n;\x00]')
COOKIES_MAX, LS_KEYS_MAX, LS_VALUE_MAX, LS_ORIGIN_MAX = 60, 200, 32_000, 256_000


def site_base(site):
    h = re.sub(r'^https?://', '', str(site or '').lower()).split('/')[0].split(':')[0].strip('.')
    parts = h.split('.')
    return '.'.join(parts[-3:]) if len(parts) >= 3 and parts[-2] in ('co', 'com', 'org', 'net') and len(parts[-1]) == 2 else '.'.join(parts[-2:])


def _ours(host, bases):
    h = str(host or '').lower().lstrip('.')
    h = re.sub(r'^https?://', '', h).split('/')[0].split(':')[0]
    return any(h == b or h.endswith('.' + b) for b in bases)


def clean_context(ctx, site, now=None):
    """One saved sign-in → (clean context, {'kept', 'dropped'}). Only the site (and its own sibling domains) survives."""
    now = now or __import__('time').time()
    base = site_base(site)
    bases = SITE_FAMILY.get(base, (base,))
    jar = {}
    raw = list((ctx or {}).get('cookies') or [])
    for k in raw:
        if not isinstance(k, dict):
            continue
        name, value, dom, path = str(k.get('name') or ''), str(k.get('value') or ''), str(k.get('domain') or ''), str(k.get('path') or '/')
        exp = k.get('expires')
        exp = float(exp) if isinstance(exp, (int, float)) else -1.0
        if (not name or len(name) > 256 or len(value) > 4096 or BAD.search(name) or BAD.search(value) or BAD.search(path) or not path.startswith('/')
                or not re.fullmatch(r'\.?[a-z0-9.-]{1,253}', dom.lower()) or not _ours(dom, bases) or TRACKER.match(name) or (0 < exp < now)):
            continue
        c = {key: k[key] for key in COOKIE_KEYS if key in k}
        c['expires'] = exp
        if c.get('sameSite') not in ('Strict', 'Lax', 'None'):
            c.pop('sameSite', None)
        key = (name, dom.lower().lstrip('.'), path)
        if key not in jar or exp > jar[key]['expires'] or exp < 0 <= jar[key]['expires']:
            jar[key] = c
    ids = {}   # a site's per-login pairs (AUTH-<id>, REFRESH-<id>): per SUB-DOMAIN only the newest login stays (account.proton.me and
    for c in jar.values():   # mail.proton.me each hold their own, both current — found on the owner's real Proton save 2026-10-31)
        m = re.fullmatch(r'([A-Za-z]+)-([a-z0-9]{20,})', c['name'])
        if m:
            d_ = str(c.get('domain') or '').lower().lstrip('.'); w_ = c['expires'] if c['expires'] > 0 else now + 1e9
            if w_ > ids.get(d_, ('', -1.0))[1]:
                ids[d_] = (m.group(2), w_)
    stale = lambda c: (re.fullmatch(r'[A-Za-z]+-[a-z0-9]{20,}', c['name']) and str(c.get('domain') or '').lower().lstrip('.') in ids
                       and not c['name'].endswith('-' + ids[str(c.get('domain') or '').lower().lstrip('.')][0]))
    cookies = [c for c in jar.values() if not stale(c)]
    cookies.sort(key=lambda c: (not c.get('httpOnly'), -(c['expires'] if c['expires'] > 0 else now + 1e9)))
    cookies = cookies[:COOKIES_MAX]
    store = {}
    for origin, kv in ((ctx or {}).get('localStorage') or {}).items():
        if not _ours(origin, bases) or not isinstance(kv, dict):
            continue
        out, size = {}, 0
        for key_, val in list(kv.items())[:LS_KEYS_MAX]:
            v = str(val)
            if len(v) > LS_VALUE_MAX or size + len(v) > LS_ORIGIN_MAX or TRACKER.match(str(key_)):
                continue
            out[str(key_)[:256]] = v; size += len(v)
        if out:
            store[origin] = out
    return {'cookies': cookies, 'localStorage': store}, {'kept': len(cookies), 'dropped': len(raw) - len(cookies)}


def merge_contexts(ctxs):
    """Several saved sign-ins → one session context (later ones win on the same cookie / origin); None when empty or too big."""
    jar, store = {}, {}
    for c in ctxs or []:
        for k in (c or {}).get('cookies') or []:
            jar[(k.get('name'), k.get('domain'), k.get('path'))] = k
        for origin, kv in ((c or {}).get('localStorage') or {}).items():
            store.setdefault(origin, {}).update(kv or {})
    out = {'cookies': list(jar.values()), 'localStorage': store}
    return out if (jar or store) and len(json.dumps(out)) <= CTX_MAX else None


async def close_session(http, env, s):
    """Release a hosted session (best effort — a provider's own timeout ends it anyway)."""
    k = keys(env)
    try:
        if s.get('provider') == 'steel':
            await http.post(f"{STEEL}/sessions/{s['id']}/release", headers={'steel-api-key': k['STEEL_API_KEY']}, timeout=10)
        elif s.get('provider') == 'browserbase':
            await http.post(f"{BB}/sessions/{s['id']}", headers={'X-BB-API-Key': k['BROWSERBASE_API_KEY'], 'Content-Type': 'application/json'},
                            json={'projectId': k['BROWSERBASE_PROJECT_ID'], 'status': 'REQUEST_RELEASE'}, timeout=10)
    except Exception:
        pass


# ── the reader (no live browser): plain fetches, readable text, a web search ────────────────────────────────────────────────────────────
_TAGS = re.compile(r'<(script|style|noscript|svg|title|head)[^>]*>.*?</\1>', re.S | re.I)   # the title is returned on its own, never twice


def page_text(markup, limit=TEXT_MAX):
    """HTML → (title, readable text) — scripts / styles dropped, whitespace folded."""
    m = str(markup or '')
    title = html.unescape((re.search(r'<title[^>]*>(.*?)</title>', m, re.S | re.I) or [None, ''])[1]).strip()[:140]
    body = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', _TAGS.sub(' ', m)))).strip()
    return title, body[:limit]


def search_hits(markup, n=8):
    """DuckDuckGo's HTML results → [{title, url}] (the reader's search)."""
    out = []
    for href, title in re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', str(markup or ''), re.S):
        u = html.unescape(href)
        m = re.search(r'uddg=([^&]+)', u)
        if m:
            from urllib.parse import unquote
            u = unquote(m.group(1))
        if u.startswith('http'):
            out.append({'title': re.sub(r'<[^>]+>', '', html.unescape(title)).strip()[:120], 'url': u})
        if len(out) >= n:
            break
    return out


def needs_human(url, text):
    """A sign-in / sign-up / CAPTCHA wall → the reason a person must act (the models stop and ask), else None."""
    u, t = str(url or '').lower(), str(text or '').lower()[:4000]
    if re.search(r'captcha|verify you are human|are you a robot', t):
        return 'a CAPTCHA — only you can pass it'
    if re.search(r'just a moment\.\.\.|checking your browser|security checkpoint|performing security verification|unusual traffic|attention required', t) or '/sorry/' in u or 'cdn-cgi/challenge' in u:
        return 'a bot check (Cloudflare / a checkpoint) — pass it in the window, or save a sign-in for this site in Credentials'
    if re.search(r'/(login|signin|sign-in|signup|sign-up|register|auth)\b|/i/flow/login|/onboarding\b|[?&]mode=login\b', u) or re.search(r'\b(sign in|log in|create (an )?account)\b.{0,80}\bpassword\b', t):
        return 'a sign-in / sign-up — you type your own details in the window (FEELESS never sees them)'
    return None


# ── page drivers: one interface (goto · search · click · type · read · shot) over a live hosted browser or the reader ────────────────────
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'}
SEARCH = 'https://html.duckduckgo.com/html/?q='


class ReaderPage:
    """No live browser: the server fetches pages as text. It cannot type (a form needs a live window → the model is told so)."""
    live = False

    def __init__(self, http):
        self.http, self.url, self.title, self._html = http, None, None, ''

    async def goto(self, url):
        if not str(url).startswith(('http://', 'https://')):
            return '(not a web address)'
        from urllib.parse import urljoin
        for _ in range(6):
            await public_url(url)
            r = await self.http.get(url, headers=UA, timeout=20, follow_redirects=False)
            if r.status_code not in (301, 302, 303, 307, 308):
                break
            url = urljoin(url, r.headers.get('location', ''))
        else:
            raise ValueError('Too many redirects.')
        self.url, self._html = str(r.url), r.text
        self.title, body = page_text(r.text)
        return body

    async def search(self, q):
        r = await self.http.get(SEARCH + __import__('urllib.parse').parse.quote(str(q)[:200]), headers=UA, timeout=20)
        self.url, self.title, self._html = f'search: {q}', f'search: {q}', r.text
        hits = search_hits(r.text)
        return '\n'.join(f"{i + 1}. {h['title']} — {h['url']}" for i, h in enumerate(hits)) or '(no results)'

    async def click(self, text):
        t = str(text).strip().lower()
        for href, label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', self._html, re.S):
            if t and t in re.sub(r'<[^>]+>', '', html.unescape(label)).strip().lower():
                if href.startswith('/') and self.url and self.url.startswith('http'):
                    from urllib.parse import urljoin
                    href = urljoin(self.url, href)
                return await self.goto(html.unescape(href))
        return f'(no link with the text "{text}")'

    async def type(self, label, value):
        return '(the reader cannot type into forms — this needs a live browser window)'

    async def upload(self, label, f):
        return '(the reader cannot upload files — this needs a live browser window)'

    async def read(self):
        return page_text(self._html)[1] if self._html else ''

    async def shot(self):
        return None

    async def close(self):
        return None


class DownloadKeeper:
    """⬇ While a PERSON has a live window: ONE bare browser-level socket — nothing attached to the page, so a bot check still sees a person —
    that sends every download (a site's recovery PDF, an in-page blob) to Steel's session files, where FEELESS seals it. Names come from the
    browser's own download events (Steel stores each file under a guid). Proven 2026-10-31: a blob download landed only while this socket was open."""
    def __init__(self, connect):
        self.connect, self.names, self._ws, self._task = connect, {}, None, None

    async def start(self):
        import websockets
        self._ws = await websockets.connect(self.connect, max_size=None)
        await self._ws.send(json.dumps({'id': 1, 'method': 'Browser.setDownloadBehavior', 'params': {'behavior': 'allowAndName', 'downloadPath': '/files', 'eventsEnabled': True}}))
        self._task = asyncio.create_task(self._read())
        return self

    async def _read(self):
        try:
            async for m in self._ws:
                d = json.loads(m)
                if d.get('method') == 'Browser.downloadWillBegin':
                    self.names[d['params'].get('guid')] = str(d['params'].get('suggestedFilename') or 'download')[:100]
        except Exception:
            pass

    async def stop(self):
        if self._task:
            self._task.cancel()
        try:
            await self._ws.close()
        except Exception:
            pass


async def collect_downloads(http, env, session_id, names=None):
    """⬇ Every file downloaded in a Steel window → [(name, bytes)], each DELETED from Steel once read (it lives on only sealed in the drawer)."""
    k, out = (env or {}).get('STEEL_API_KEY'), []
    if not k or not session_id:
        return out
    h = {'steel-api-key': k}
    r = await http.get(f'{STEEL}/sessions/{session_id}/files', headers=h, timeout=20)
    for f in ((r.json() or {}).get('data') or []) if r.status_code == 200 else []:
        guid = str(f.get('path') or '').rsplit('/', 1)[-1]
        if not guid or int(f.get('size') or 0) > 5 * 1024 * 1024:
            continue
        g = await http.get(f'{STEEL}/sessions/{session_id}/files/{guid}', headers=h, timeout=30)
        if g.status_code == 200:
            out.append(((names or {}).get(guid) or 'download', g.content))
            await http.delete(f'{STEEL}/sessions/{session_id}/files/{guid}', headers=h, timeout=15)
    return out


class LivePage:
    """A hosted browser (Steel / Browserbase) driven over CDP with Playwright — the window the user watches."""
    live = True

    def __init__(self, connect):
        self.connect, self.url, self.title, self._pw, self._b, self._p = connect, None, None, None, None, None

    async def start(self):
        from playwright.async_api import async_playwright
        if getattr(self, 'downloads', None):
            await self.downloads.stop()
        self._pw = await async_playwright().start()
        self._b = await self._pw.chromium.connect_over_cdp(self.connect, timeout=30000)
        ctx = self._b.contexts[0] if self._b.contexts else await self._b.new_context(service_workers='block')
        async def guard(route):
            try:
                await public_url(route.request.url)
            except (ValueError, OSError):
                await route.abort('blockedbyclient')
            else:
                await route.continue_()
        await ctx.route('**/*', guard)
        # Wallet extensions and persistent worker contexts are not shared with cats.
        await ctx.clear_permissions()
        if hasattr(ctx, 'route_web_socket'):
            await ctx.route_web_socket('**/*', lambda ws: ws.close())
        self._p = ctx.pages[0] if ctx.pages else await ctx.new_page()
        return self

    async def _sync(self):
        check_url(self._p.url) if self._p.url != 'about:blank' else None
        self.url = self._p.url
        try:
            self.title = (await self._p.title())[:140]
        except Exception:
            self.title = None
        return await self.read()

    async def goto(self, url):
        await public_url(url)
        await self._p.goto(str(url), wait_until='domcontentloaded', timeout=30000)
        return await self._sync()

    async def search(self, q):
        return await self.goto(SEARCH + __import__('urllib.parse').parse.quote(str(q)[:200]))

    async def click(self, text):
        await self._p.get_by_text(str(text), exact=False).first.click(timeout=8000)
        await self._p.wait_for_load_state('domcontentloaded', timeout=15000)
        return await self._sync()

    async def type(self, label, value):
        f = self._p.get_by_label(str(label)).or_(self._p.get_by_placeholder(str(label))).first
        await f.fill(str(value), timeout=8000)
        return await self._sync()

    async def upload(self, label, f):
        """☁ One of the owner's attached files (agent_files) onto the file field by its label / button text — bytes sent over CDP, never a path."""
        from pathlib import Path
        data = Path(f['path']).read_bytes()
        payload = {'name': f['name'], 'mimeType': f['mime'], 'buffer': data}
        field = self._p.locator('input[type=file]')
        if label:
            near = self._p.get_by_label(str(label)).or_(self._p.locator(f'input[type=file][name*="{re.sub(r"[^A-Za-z0-9_-]", "", str(label))[:30]}" i]'))
            if await near.count():
                field = near
        if not await field.count():
            async with self._p.expect_file_chooser(timeout=8000) as fc:
                await self._p.get_by_text(str(label or 'upload'), exact=False).first.click(timeout=8000)
            await (await fc.value).set_files(payload)
        else:
            await field.first.set_input_files(payload, timeout=8000)
        return f"(uploaded {f['name']}) " + await self._sync()

    async def read(self):
        try:
            return re.sub(r'\s+', ' ', await self._p.inner_text('body', timeout=8000))[:TEXT_MAX]
        except Exception:
            return ''

    async def shot(self):
        """A small JPEG of the window (the snapshot view when no live URL can be shown)."""
        try:
            return await self._p.screenshot(type='jpeg', quality=45, timeout=8000)
        except Exception:
            return None

    async def close(self):
        for x in (self._b, self._pw):
            try:
                await (x.close() if x is self._b else x.stop())
            except Exception:
                pass

    async def release(self):
        """🙋 Let go while a PERSON uses the window (a sign-in, a "verify you are human" box): no request routing, no automation attached.
        With every request routed through us, Cloudflare's check reloads forever (owner 2026-10-31). The person still clicks it themselves;
        start() takes the window back after, on the page they left it."""
        await self.close()
        self._b = self._pw = self._p = None
        try:   # ⬇ a recovery file you download while you have the window lands where FEELESS seals it (collect_downloads), never on a disk we can't reach
            self.downloads = await DownloadKeeper(self.connect).start()
        except Exception:
            self.downloads = None
