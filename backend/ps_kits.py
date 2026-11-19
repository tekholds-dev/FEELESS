"""🧰 SLICE 3 · THE POSTATIC TOOLKIT (owner 2026-11-18: "so many integrative tools missing from static"; VISION › PoStatic › Full toolkit).
Every build mind gets EVERY approved kit, not only the owner's 3 picks: 3D (three.js), Motion, charts (Recharts, Lightweight Charts),
shadcn/ui, live market data (DexScreener + our own candle index), wallet connect, forms and maps. The picks stay "must use"; the menu is
"may use, pick what fits". After a build, code (never the model) reads which kits the page really uses and what each did, so the folder and
the proof record list them. Pure, except nothing: the live reader is in fc_desk (_page_live), its parsing is here.

A built page is locked (no network, collective_kits.open_for_kits): live numbers and the wallet come in through the frame bridge
(postMessage from the FEELESS window), never a fetch. The wallet bridge is read-only: it hands the page a public address and its SOL, and
there is no message that signs or sends anything (§1)."""
import json
import re

import collective_kits as _kits

# 🧾 kid → how a mind uses it, how code sees it was used, and what it did (read from the page's own code)
MENU = {
    'three': {'name': 'three.js (3D)', 'cdn': True,
              'how': 'A real 3D scene: <script type="module">import * as THREE from "three"</script> (the import map is added for you). Cap pixel ratio at 2, pause when hidden, draw a still if WebGL is missing. Words go beside or below the canvas, never laid on it.'},
    'motion': {'name': 'Motion', 'cdn': True,
               'how': 'Every entrance, hover and scroll effect: Motion.animate(el, {opacity: [0, 1], y: [24, 0]}, {duration: .6}), Motion.inView, Motion.scroll, Motion.stagger.'},
    'recharts': {'name': 'Recharts', 'cdn': True,
                 'how': 'React charts without a build step: const h = React.createElement, R = Recharts; ReactDOM.createRoot(el).render(h(R.ResponsiveContainer, {width: "100%", height: 260}, h(R.AreaChart, {data}, h(R.XAxis, {dataKey: "t"}), h(R.YAxis), h(R.Tooltip), h(R.Area, {dataKey: "v"})))).'},
    'lwcharts': {'name': 'Lightweight Charts', 'cdn': True,
                 'how': 'Price charts: const c = LightweightCharts.createChart(el, {autoSize: true}); c.addCandlestickSeries().setData(rows) with {time, open, high, low, close}. The chart div gets its own height (height:320px); its title goes above it, never on it.'},
    'shadcn': {'name': 'shadcn/ui', 'cdn': True,
               'how': 'Its look with Tailwind classes: cards (rounded-xl border bg-card p-6 shadow-sm), badges, buttons, tabs, inputs; muted text, tight spacing.'},
    'live': {'name': 'DexScreener + FEELESS indexes', 'cdn': False,
             'how': ("Live market numbers, given to the page by FEELESS (never fetch): window.FEELESS_LIVE and a message every 20 s, "
                     "addEventListener('message', e => { if (e.data && e.data.t === 'feeless-live') render(e.data.live) }). live = {solUsd, solChange24h, slot, tps, at, "
                     "pools: [{pair, dex, priceUsd, liqUsd, vol24, change24, turnover, url}] (DexScreener), candles: {pair: 'SOL/USDC', interval: '5m', rows: [[time, open, high, low, close, volume]]} (FEELESS candle index)}. "
                     'Show the read time; keep the last numbers if a message is late.')},
    'wallet': {'name': 'Wallet connect', 'cdn': False,
               'how': ("A Connect wallet button through FEELESS, read-only: parent.postMessage({t: 'feeless-wallet-connect'}, '*'), then "
                       "addEventListener('message', e => { if (e.data && e.data.t === 'feeless-wallet') show(e.data.address, e.data.sol) }). The page never asks to sign or send anything; there is no way to.")},
    'forms': {'name': 'Forms', 'cdn': False,
              'how': 'Real forms: <form> with labels, required fields, inline errors, a result that changes, saved on the device with localStorage. A form never sends anything anywhere.'},
    'leaflet': {'name': 'Leaflet (maps)', 'cdn': True,
                'how': "Maps: const m = L.map(el).setView([lat, lng], z); L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {attribution: '© OpenStreetMap © CARTO'}).addTo(m); L.marker([lat, lng]).addTo(m). The map div gets its own height (style=\"height:360px\") and its title goes ABOVE it, never laid on the map."},
}
IDS = tuple(MENU)
SIGN = {   # code use, read from the page (a kit named in a comment alone does not count)
    'three': r'\bTHREE\.\w+',
    'motion': r'\bMotion\.(?:animate|inView|scroll|stagger|hover|press)\b',
    'recharts': r'\bRecharts\.\w+|=\s*Recharts\b|\bR\.(?:LineChart|AreaChart|BarChart|PieChart|ComposedChart|RadarChart|ResponsiveContainer)\b',
    'lwcharts': r'\bLightweightCharts\.createChart\b',
    'shadcn': r'class="[^"]*\brounded-(?:md|lg|xl|2xl)\b[^"]*\bborder\b',
    'live': r"feeless-live|FEELESS_LIVE",
    'wallet': r"feeless-wallet-connect",
    'forms': r'<form\b',
    'leaflet': r'\bL\.map\(',
}
KITS_JSON = re.compile(r'<script[^>]+id=["\']?feeless-kits["\']?[^>]*>(.*?)</script>', re.I | re.S)
MARKET = re.compile(r'(?i)\b(dexscreener|pools?|liquidity|volume|turnover|candles?|price chart|market|tokens?|coins?|memecoin|chart)\b')
WALLET = re.compile(r'(?i)\bwallet|connect\b')


def wants_market(text):
    return bool(MARKET.search(str(text or '')))


def menu_line(picks=()):
    """The whole approved toolkit, for every PoStatic build (the picks still come first and must be used). → prompt text"""
    rows = '\n'.join(f"- {m['name']}: {m['how']}" for kid, m in MENU.items())
    picked = [MENU[p]['name'] for p in picks or () if p in MENU]
    return ('\nTHE FULL POSTATIC TOOLKIT: you may use ANY of these approved kits; pick the ones that fit this page, use each one for real (no empty '
            'chart box, no button that does nothing), and their files are added for you.' + (f" Already picked: {', '.join(picked)}." if picked else '') + '\n'
            + rows + '\nAt the end of <body> say which kits you used and what each did, in plain words: '
            '<script type="application/json" id="feeless-kits">{"Motion": "hero entrance and card stagger", "Lightweight Charts": "the SOL candles"}</script>')


def in_page(html):
    """The toolkit kits this page's code really uses. → [kid]"""
    h = str(html or '')
    return [k for k in IDS if re.search(SIGN[k], h)]


def _said(html):
    """What the minds said each kit did (their own feeless-kits note), by kit id. Words only, never trusted for 'used'. Pure."""
    m = KITS_JSON.search(str(html or ''))
    try:
        d = json.loads(m.group(1)) if m else {}
    except ValueError:
        return {}
    out = {}
    for k, v in (d.items() if isinstance(d, dict) else []):
        key = re.sub(r'[^a-z0-9]', '', str(k).lower())
        for kid, meta in MENU.items():
            names = {re.sub(r'[^a-z0-9]', '', x.lower()) for x in (kid, meta['name'], meta['name'].split(' (')[0])}
            if key in names or any(n and n in key for n in names if len(n) > 3):
                out[kid] = ' '.join(str(v).split())[:140]
    return out


def _n(rx, h):
    return len(re.findall(rx, h))


def _code_did(kid, h):
    """What a kit did, read from the code alone. → words"""
    if kid == 'three':
        n = _n(r'new\s+THREE\.WebGLRenderer', h); models = _n(r'data-feeless-model="', h)
        return (f"{n or 1} live 3D scene{'s' if n > 1 else ''}" + (f", the studio piece in {models} place{'s' if models > 1 else ''}" if models else ''))
    if kid == 'motion':
        n = _n(r'\bMotion\.(?:animate|inView|scroll|hover|press)\b', h)
        return f"{n} animation call{'s' if n != 1 else ''} (entrances, scroll, hovers)"
    if kid == 'recharts':
        kinds = sorted({m.lower().replace('chart', ' chart') for m in re.findall(r'\b(LineChart|AreaChart|BarChart|PieChart|ComposedChart|RadarChart)\b', h)})
        return ', '.join(kinds) if kinds else 'a React chart'
    if kid == 'lwcharts':
        n = _n(r'LightweightCharts\.createChart', h); kinds = sorted({k.lower() for k in re.findall(r'add(Candlestick|Line|Area|Histogram|Bar|Baseline)Series', h)})
        return f"{n} price chart{'s' if n > 1 else ''}" + (f" ({', '.join(kinds)})" if kinds else '')
    if kid == 'shadcn':
        n = _n(r'class="[^"]*rounded-(?:md|lg|xl|2xl)', h)
        return f"{n} part{'s' if n != 1 else ''} in the shadcn look (cards, badges, buttons)"
    if kid == 'live':
        bits = [w for w, rx in (('live SOL price', r'solUsd'), ('DexScreener pools', r'\bpools\b'), ('FEELESS 5m candles', r'\bcandles\b'), ('slot and TPS', r'\btps\b|\bslot\b')) if re.search(rx, h)]
        return ', '.join(bits) or 'live numbers from FEELESS'
    if kid == 'wallet':
        return 'Connect wallet through FEELESS (read-only: address and SOL)'
    if kid == 'forms':
        f, i = _n(r'<form\b', h), _n(r'<(?:input|select|textarea)\b', h)
        return f"{f} form{'s' if f != 1 else ''}, {i} field{'s' if i != 1 else ''}" + (', saved on the device' if 'localStorage' in h else '')
    if kid == 'leaflet':
        mk = _n(r'L\.(?:marker|circleMarker|circle)\(', h); maps = max(1, _n(r'L\.map\(', h))
        return f"{maps} map" + (f" with {mk} marker call{'s' if mk != 1 else ''}" if mk else '')
    return 'used'


def did(html, picks=()):
    """🧾 Every kit this page carries (the picks, used or not, then each toolkit kit its code uses) with what it did.
    The minds' own words win when the code really uses that kit; else code says it. → [{id, name, used, did, by, picked}]"""
    h = str(html or ''); said = _said(h); out = []
    for row in _kits.kit_report(h, picks):   # the owner's picks first, used or not (the folder says so either way)
        kid = row['id']; use = row['used'] or (kid in MENU and bool(re.search(SIGN[kid], h)))
        words = said.get(kid) if use and said.get(kid) else (_code_did(kid, h) if use and kid in MENU else ('used' if use else ''))
        out.append({**row, 'used': bool(use), 'did': words, 'by': 'minds' if use and said.get(kid) else 'code', 'picked': True})
    have = {r['id'] for r in out}
    for kid in in_page(h):
        if kid in have:
            continue
        out.append({'id': kid, 'name': MENU[kid]['name'], 'used': True, 'did': said.get(kid) or _code_did(kid, h), 'by': 'minds' if said.get(kid) else 'code', 'picked': False})
    return out


def carry(picks, html, models=False):
    """The kits whose files this page may load: the picks, every toolkit kit its code uses, three for the owner's models. → [kid]"""
    out = list(dict.fromkeys([*(picks or []), *[k for k in in_page(html) if MENU[k]['cdn']], *(['three'] if models else [])]))
    return [k for k in out if k in _kits.KIT_USE or k not in MENU]


# ── 📡 the live kit's numbers: DexScreener pools + our own candle index, parsed here, read by fc_desk._page_live ──
DEX_SOL = 'https://api.dexscreener.com/token-pairs/v1/solana/So11111111111111111111111111111111111111112'
DEX_BOOSTS = 'https://api.dexscreener.com/token-boosts/top/v1'
DEX_TOKENS = 'https://api.dexscreener.com/tokens/v1/solana/{}'
CANDLE_PAIR = '58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2'   # SOL/USDC Raydium, the pool our own candle index (candles_service) keeps
POOLS = 12


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def pool_row(p):
    """One DexScreener pair → the row a page gets. Turnover = 24 h volume ÷ liquidity. Pure."""
    liq = _f((p.get('liquidity') or {}).get('usd')); vol = _f((p.get('volume') or {}).get('h24'))
    return {'pair': f"{(p.get('baseToken') or {}).get('symbol')}/{(p.get('quoteToken') or {}).get('symbol')}"[:24], 'dex': str(p.get('dexId') or '')[:16],
            'priceUsd': _f(p.get('priceUsd')), 'liqUsd': round(liq), 'vol24': round(vol), 'change24': _f((p.get('priceChange') or {}).get('h24')),
            'turnover': round(vol / liq, 2) if liq else 0, 'url': str(p.get('url') or '')[:120]}


def pools_of(sol_pairs, token_pairs):
    """The top SOL pools plus the best pool of each boosted coin, biggest liquidity first, one row per pair. Pure."""
    best = {}
    for p in (token_pairs if isinstance(token_pairs, list) else []):
        t = (p.get('baseToken') or {}).get('address')
        if t and (t not in best or _f((p.get('liquidity') or {}).get('usd')) > _f((best[t].get('liquidity') or {}).get('usd'))):
            best[t] = p
    sol = sorted((p for p in (sol_pairs if isinstance(sol_pairs, list) else []) if isinstance(p, dict)), key=lambda p: -_f((p.get('liquidity') or {}).get('usd')))[:4]
    rows, seen = [], set()
    for p in [*sol, *sorted(best.values(), key=lambda p: -_f((p.get('liquidity') or {}).get('usd')))]:
        a = p.get('pairAddress')
        if a and a not in seen and _f((p.get('liquidity') or {}).get('usd')) > 0:
            seen.add(a); rows.append(pool_row(p))
    return rows[:POOLS]


def candles_of(j, keep=96):
    """Our candle index's reply → {pair, interval, rows: [[t, o, h, l, c, v]]}, or None. Pure."""
    rows = [[int(r[0]), *[round(_f(x), 6) for x in r[1:6]]] for r in ((j or {}).get('candles') or []) if isinstance(r, list) and len(r) >= 6][-keep:]
    return {'pair': 'SOL/USDC', 'interval': '5m', 'source': 'FEELESS candle index', 'rows': rows} if rows else None


CENTRE_KITS = {'3d': ('three',), 'candles': ('lwcharts', 'live'), 'datachart': ('recharts', 'live'), 'map': ('leaflet',), 'tool': ('forms',),
               'table': ('live',), 'numbers': ('live', 'motion'), 'story': ('motion',)}


PART_WORDS = (('leaflet', r'\bmaps?\b|locations?|cities|meet ?ups?|where'), ('wallet', r'wallet|connect\b|phantom|solflare'),
              ('lwcharts', r'candles?|candlestick|price chart|ohlc'), ('recharts', r'\bcharts?\b|graph|trend|history'),
              ('live', r'live|real.?time|price|pools?|volume|liquidity|\bsol\b|market'), ('forms', r'form|sign.?up|register|whitelist|subscribe|calculator|input'),
              ('three', r'\b3d\b|three|scene|globe'))


def part_kits(section):
    """🧩 The kits one section's own brief calls for ("Interactive map of meetups" → Leaflet). → [kit id]. Pure."""
    t = str(section or '').lower()
    return [k for k, rx in PART_WORDS if re.search(rx, t)][:3]


def part_line(brief, is_centre, live='', section=''):
    """🧩 What one section's writer reads (a page built in sections): the centrepiece section gets its kit's exact how-to and the live
    numbers; every other section gets the how-to of the kits its own brief calls for (a map section → Leaflet), then the short menu.
    Kept short: a local mind's section prompt is cut at 1,500 characters. → text"""
    names = ', '.join(m['name'] for m in MENU.values())
    if not is_centre:
        ks = part_kits(section)
        how = ('\nTHIS SECTION NEEDS ' + ' and '.join(MENU[k]['name'] for k in ks) + ', for real, in its own <script>:\n'
               + '\n'.join(f"- {MENU[k]['name']}: {MENU[k]['how']}" for k in ks) + (live[:500] if live and 'live' in ks else '') + '\n') if ks else ''
        return (how + f'KITS YOU MAY USE in this section (their files are added for you): {names}. Motion for entrances: Motion.animate(el, {{opacity: [0, 1]}}). '
                'Never draw a chart by hand, fake a wallet or make numbers up: a number is live (from the feeless-live message) or labelled sample. '
                'Never lay words on top of a map, chart, scene or another block (no position:absolute text over them): a title sits above.')
    ks = CENTRE_KITS.get((brief or {}).get('centre'), ())
    return ('\nTHIS SECTION IS THE CENTREPIECE: ' + str((brief or {}).get('centre')) + '. Build it with ' + ' and '.join(MENU[k]['name'] for k in ks) + ', for real, in this section\'s own <script>.\n'
            + '\n'.join(f"- {MENU[k]['name']}: {MENU[k]['how']}" for k in ks) + (live[:900] if live and 'live' in ks else '')
            + '\nNever lay words on top of the centrepiece (no position:absolute text over it): its title sits above.\n')
