"""🌐 NEXA'S SITE READ (owner, 2026-10-22 P0 #2: "a site's AGE (RDAP / WHOIS) + a page SNAPSHOT (title, headings, tech fingerprint, template match)
→ real tech vs another same-utility site, into her discovery base; one-line packet like her desk calls").

A coin's website → how old its domain is (RDAP registration date) + what the page is made of (title, first headings, the framework or page
builder behind it, a wallet connect, docs / GitHub, its socials, meme tells) → one verdict: 🧪 REAL TECH · 🎭 TEMPLATE · 🪶 THIN, filed in her
discovery base under the coin's mint as a 'site' fact so she reads it with the coin and never fetches it twice in a week. Pure + tested; the
service fetches (https only, public IPs only, ≤ 3 hops, 6 s, 300 KB) — a coin's URL is untrusted input."""
import ipaddress
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

FRAMEWORK = [('Next.js', r'__NEXT_DATA__|/_next/static'), ('Nuxt', r'__NUXT__|/_nuxt/'), ('Svelte', r'class="[^"]*svelte-[a-z0-9]{5,}'),
             ('Vue', r'data-v-[0-9a-f]{6,}'), ('React', r'data-reactroot|id="root"|react-dom'), ('Vite', r'/assets/index-[A-Za-z0-9_-]{6,}\.js')]
BUILDER = [('Carrd', r'carrd\.co|built with carrd'), ('Linktree', r'linktr\.ee|linktree'), ('Wix', r'wixstatic\.com|_wixCIDX|wix\.com'),
           ('Squarespace', r'squarespace'), ('Webflow', r'webflow'), ('Framer', r'framerusercontent\.com|framer\.(com|website)'),
           ('WordPress', r'wp-content|wp-includes'), ('GitBook', r'gitbook'), ('Shopify', r'cdn\.shopify\.com')]
DAPP = r'wallet-adapter|web3modal|walletconnect|@solana/web3|rainbowkit|wagmi|connect\s*wallet|phantom\.app'
DOCS = r'whitepaper|litepaper|/docs\b|docs\.|gitbook\.io|github\.com/'
SOCIAL = {'X': r'(twitter|x)\.com/[A-Za-z0-9_]+', 'TG': r't\.me/[A-Za-z0-9_+]+', 'Discord': r'discord\.(gg|com)/'}
MEME = r'pump\.fun|dexscreener\.com|to the moon|1000x|100x|\bca\s*[:=]|contract address|buy now|ape in'
SKIP = ('pump.fun', 'dexscreener.com', 'x.com', 'twitter.com', 't.me', 'discord.gg', 'discord.com', 'youtube.com', 'tiktok.com', 'instagram.com',
        'raydium.io', 'jup.ag', 'birdeye.so', 'solscan.io', 'github.com', 'medium.com')   # not the coin's own site — nothing to judge


def host_of(url):
    """The host of a coin's website (lowercase, no www.) — None unless it is a plain http(s) URL with a real hostname (never an IP literal)."""
    try:
        u = urlparse(str(url or '').strip())
    except ValueError:
        return None
    h = (u.hostname or '').lower().rstrip('.')
    if u.scheme not in ('http', 'https') or not h or '.' not in h or u.username or u.password:
        return None
    try:
        ipaddress.ip_address(h)
        return None
    except ValueError:
        pass
    return h[4:] if h.startswith('www.') else h


def registrable(host):
    """The registered domain RDAP knows (example.com · example.co.uk) — the last two labels, three for a short second level under a 2-letter TLD."""
    parts = str(host or '').split('.')
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in ('co', 'com', 'net', 'org', 'gov', 'ac', 'edu'):
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])


def skip(host):
    return not host or any(host == d or host.endswith('.' + d) for d in SKIP)


def public_ip(ip):
    """True only for a globally routable address (no loopback / private / link-local / reserved / multicast) — the SSRF guard."""
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return a.is_global and not (a.is_loopback or a.is_private or a.is_link_local or a.is_reserved or a.is_multicast or a.is_unspecified)


def age_days(rdap, now):
    """RDAP JSON → days since the domain was registered (None when it doesn't say)."""
    for e in (rdap or {}).get('events') or []:
        if str(e.get('eventAction') or '').lower() == 'registration' and e.get('eventDate'):
            try:
                t = datetime.fromisoformat(str(e['eventDate']).replace('Z', '+00:00'))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                return max(0, int((now - t.timestamp()) // 86400))
            except ValueError:
                return None
    return None


def _txt(s):
    return ' '.join(re.sub(r'<[^>]+>', ' ', re.sub(r'&[a-z#0-9]+;', ' ', str(s or ''))).split())


def snapshot(html):
    """The page's HTML → {title, heads, stack, builder, dapp, docs, socials, meme, words}."""
    h = str(html or '')[:300_000]
    low = h.lower()
    title = _txt((re.search(r'<title[^>]*>(.*?)</title>', h, re.I | re.S) or [None, ''])[1])[:80]
    heads = [x for x in (_txt(m)[:60] for m in re.findall(r'<h[12][^>]*>(.*?)</h[12]>', h, re.I | re.S)) if x][:4]
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.I | re.S)
    return {'title': title, 'heads': heads, 'stack': [n for n, rx in FRAMEWORK if re.search(rx, h)], 'builder': [n for n, rx in BUILDER if re.search(rx, low)],
            'dapp': bool(re.search(DAPP, low)), 'docs': bool(re.search(DOCS, low)), 'socials': [k for k, rx in SOCIAL.items() if re.search(rx, low)],
            'meme': len(re.findall(MEME, low)), 'words': len(_txt(body).split())}


def verdict(age, snap):
    """Age + snapshot → {kind, score, line}: 🧪 REAL TECH (score ≥ 3) · 🎭 TEMPLATE (≤ −1) · 🪶 THIN (between) · ❔ UNREAD (no page)."""
    if snap is None:
        return {'kind': 'UNREAD', 'score': 0, 'line': f"❔ page unreadable · {age}d old" if age is not None else '❔ page unreadable'}
    s = 0
    s += 2 if (age or 0) >= 365 else 1 if (age or 0) >= 90 else -2 if age is not None and age < 14 else 0
    s += 2 if snap['dapp'] else 0
    s += 1 if snap['docs'] else 0
    s += 1 if snap['stack'] and not snap['builder'] else 0
    s -= 1 if snap['builder'] and not snap['dapp'] else 0
    s -= 1 if snap['meme'] >= 2 else 0
    s -= 1 if snap['words'] < 120 else 0
    kind = 'REAL TECH' if s >= 3 else 'TEMPLATE' if s <= -1 else 'THIN'
    icon = {'REAL TECH': '🧪', 'TEMPLATE': '🎭', 'THIN': '🪶'}[kind]
    built = (snap['builder'] or snap['stack'] or ['plain HTML'])[0]
    bits = [f"{icon} {kind}", f"{age}d old" if age is not None else 'age ?', f"{built}{' one-pager' if snap['builder'] and not snap['dapp'] else ''}",
            'wallet connect' if snap['dapp'] else None, 'docs' if snap['docs'] else None, '+'.join(snap['socials']) or 'no socials',
            f"{snap['meme']} meme tells" if snap['meme'] >= 2 else None]
    return {'kind': kind, 'score': s, 'line': ' · '.join(b for b in bits if b)[:150]}


def fact(host, v, snap=None):
    """Her discovery-base fact for the coin (≤ 160 chars): domain · verdict · the page's own title."""
    t = (snap or {}).get('title') or ''
    return f"{host} · {v['line']}" + (f" · “{t[:40]}”" if t else '')
