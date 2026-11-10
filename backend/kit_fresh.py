"""🧰♻️ KIT FRESHNESS (owner 2026-11-10: "the stash's tooling always the best, fresh and never stale"). Every page a proof builds loads its kits
from a CDN at a pinned version. Pins went stale (echarts 5 while 6 was out, motion 12 under 14, three 0.170 under 0.187). Once a day this asks
npm for each tracked kit's newest version; a version out at least MIN_AGE_S whose real CDN file passes a headless smoke test (the library's
global really appears, no page error) replaces the pin. The old one is kept: if the current version ever fails the smoke test, it rolls back.
Pure except `latest` (npm) and `smoke` (a headless browser), which the service passes in."""
import json
import re
import time

MIN_AGE_S = 7 * 86400        # a release this young is not taken yet (fresh, never bleeding-edge)
CHECK_EVERY_S = 86400
STATE = 'fresh.json'
NPM = 'https://registry.npmjs.org/'

# kid → (npm package, how the pin is written: 'major' floats inside a major on the CDN, 'exact' is one version, how the smoke test knows it loaded)
TRACK = {
    'motion': ('motion', 'major', 'typeof Motion !== "undefined" && !!Motion.animate'),
    'echarts': ('echarts', 'major', '!!(window.echarts && echarts.init)'),
    'd3': ('d3', 'major', '!!(window.d3 && d3.select)'),
    'lwcharts': ('lightweight-charts', 'major', '!!(window.LightweightCharts && LightweightCharts.createChart)'),
    'gsap': ('gsap', 'major', '!!(window.gsap && gsap.to)'),
    'pixi': ('pixi.js', 'major', '!!(window.PIXI && PIXI.Application)'),
    'konva': ('konva', 'major', '!!(window.Konva && Konva.Stage)'),
    'fabric': ('fabric', 'major', '!!(window.fabric && fabric.Canvas)'),
    'chartjs': ('chart.js', 'major', 'typeof Chart === "function"'),
    'mermaid': ('mermaid', 'major', '!!(window.mermaid && mermaid.initialize)'),
    'daisyui': ('daisyui', 'major', 'css'),
    'heroui': ('@heroui/styles', 'exact', 'css'),
    'lucide': ('lucide', 'exact', '!!(window.lucide && lucide.createIcons)'),
    'three': ('three', 'exact', 'module:three:Scene'),
    'phaser': ('phaser', 'major', '!!(window.Phaser && Phaser.Game)'),
    'matter': ('matter-js', 'major', '!!(window.Matter && Matter.Engine)'),
    'howler': ('howler', 'major', 'typeof Howl === "function"'),
    'tone': ('tone', 'major', '!!(window.Tone && Tone.Synth)'),
    'anime': ('animejs', 'major', '!!(window.anime && anime.animate)'),
    'particles': ('@tsparticles/slim', 'major', '!!(window.tsParticles && window.loadSlim)'),
    'marked': ('marked', 'major', '!!(window.marked && marked.parse)'),
    'tabulator': ('tabulator-tables', 'major', 'typeof Tabulator === "function"'),
    'leaflet': ('leaflet', 'exact', '!!(window.L && L.map)'),
}


def _pin_re(pkg):
    return re.compile(r'(?<=/)' + re.escape(pkg) + r'@([0-9][0-9A-Za-z.\-]*)(?=/)')


def current(kit_use, kid):
    """The version a kit is pinned at in its tags, or None. Pure."""
    pkg = TRACK[kid][0]
    for tag in (kit_use.get(kid) or {}).get('tags') or []:
        m = _pin_re(pkg).search(tag)
        if m:
            return m.group(1)
    return None


def _num(v):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r'[.\-]', str(v))[:3])


def want(pin, have, latest, published_at, now):
    """The pin to move to, or None. A major pin moves only to a newer major; an exact pin to a newer version; never a release younger than
    MIN_AGE_S, never a pre-release. Pure."""
    if not latest or not have or re.search(r'[a-zA-Z]', latest) or now - float(published_at or now) < MIN_AGE_S:
        return None
    nxt = latest.split('.')[0] if pin == 'major' else latest
    if pin == 'major':
        return nxt if int(nxt) > _num(have)[0] else None
    return nxt if _num(nxt) > _num(have) else None


def swap(kit_use, pkg, old, new):
    """Every tag of every kit that loads pkg@old now loads pkg@new (three is shared by three and r3f, its addons path too). → count. Mutates."""
    n = 0; rx = re.compile(r'(?<=/)' + re.escape(f'{pkg}@{old}') + r'(?=/)')
    for k in kit_use.values():
        tags = k.get('tags') or []
        for i, t in enumerate(tags):
            t2, c = rx.subn(f'{pkg}@{new}', t)
            if c:
                tags[i] = t2; n += c
    return n


def smoke_page(tags, check):
    """A tiny page that loads only this kit's real CDN files and reports whether it worked. Pure."""
    body = ''.join(tags)
    if check == 'css':
        body = body.replace('<link ', '<link onload="window.__css=(window.__css||0)+1" ')
        return f'<!doctype html><html><head>{body}</head><body></body></html>', 'window.__css > 0'
    if check.startswith('module:'):
        _m, spec, name = check.split(':')
        return (f'<!doctype html><html><head>{body}</head><body><script type="module">import * as M from "{spec}"; window.__mod = !!M.{name};</script></body></html>',
                'window.__mod === true')
    return f'<!doctype html><html><head>{body}</head><body></body></html>', check


def load(root):
    try:
        return json.loads((root / STATE).read_text())
    except (OSError, ValueError):
        return {'pins': {}, 'log': [], 'checkedAt': 0}


def save(root, st):
    st['log'] = (st.get('log') or [])[-60:]
    root.mkdir(parents=True, exist_ok=True); (root / STATE).write_text(json.dumps(st, indent=1))


def apply(kit_use, st):
    """Put every saved pin back into the tags (at start-up, after a pass). → kits moved. Mutates."""
    moved = 0
    for kid, p in (st.get('pins') or {}).items():
        if kid in TRACK and kid in kit_use:
            have = current(kit_use, kid)
            if have and have != p['v']:
                moved += bool(swap(kit_use, TRACK[kid][0], have, p['v']))
    return moved


async def latest(http, pkg):
    """(newest version, its publish time) from npm, or (None, None)."""
    try:
        r = await http.get(NPM + pkg.replace('/', '%2f'), timeout=20, headers={'Accept': 'application/json'})
        if r.status_code != 200:
            return None, None
        d = r.json(); v = (d.get('dist-tags') or {}).get('latest')
        t = (d.get('time') or {}).get(v)
        from datetime import datetime
        return v, (datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp() if t else None)
    except Exception:   # noqa: BLE001: npm down = nothing moves
        return None, None


async def run(http, kit_use, root, smoke, now=None):
    """One freshness pass. `smoke(html, expr)` → (ok, why). Moves pins that pass, rolls back a current pin that fails. → the pass's log rows."""
    now = now or time.time(); st = load(root); rows = []
    for kid, (pkg, pin, check) in TRACK.items():
        if kid not in kit_use:
            continue
        have = current(kit_use, kid)
        if not have:
            continue
        v, at = await latest(http, pkg)
        nxt = want(pin, have, v, at, now)
        if nxt:
            trial = {kid: {'tags': [re.sub(r'(?<=/)' + re.escape(f'{pkg}@{have}') + r'(?=/)', f'{pkg}@{nxt}', t) for t in kit_use[kid]['tags']]}}
            ok, why = await smoke(*smoke_page(trial[kid]['tags'], check))
            if ok:
                swap(kit_use, pkg, have, nxt)
                st.setdefault('pins', {})[kid] = {'v': nxt, 'prev': have, 'npm': v, 'at': round(now)}
                rows.append({'kit': kid, 'from': have, 'to': nxt, 'ok': True, 'at': round(now)})
            else:
                rows.append({'kit': kid, 'from': have, 'to': nxt, 'ok': False, 'why': str(why)[:160], 'at': round(now)})
            continue
        p = (st.get('pins') or {}).get(kid)
        if p and p.get('prev') and p['v'] == have:   # the pin we moved to: still loads? if not, back to the one before
            ok, why = await smoke(*smoke_page(kit_use[kid]['tags'], check))
            if not ok:
                swap(kit_use, pkg, have, p['prev']); st['pins'].pop(kid, None)
                rows.append({'kit': kid, 'from': have, 'to': p['prev'], 'ok': True, 'rollback': True, 'why': str(why)[:160], 'at': round(now)})
    st['checkedAt'] = round(now); st['log'] = (st.get('log') or []) + rows
    save(root, st)
    return rows


def view(kit_use, root):
    """Per tracked kit: its version now, the one before, when it moved. For the Stash."""
    st = load(root)
    return {'checkedAt': st.get('checkedAt'), 'kits': [{'kit': kid, 'pkg': pkg, 'v': current(kit_use, kid), 'pin': pin, **({'prev': p['prev'], 'movedAt': p['at']} if (p := (st.get('pins') or {}).get(kid)) else {})}
                                                        for kid, (pkg, pin, _c) in TRACK.items() if kid in kit_use], 'log': (st.get('log') or [])[-12:][::-1]}


async def browser_smoke(chromium, html, expr, wait_ms=6000):
    """Load the smoke page in headless Chromium (its real CDN files), → (ok, why). A page error or the global missing = not ok."""
    from playwright.async_api import async_playwright
    errs = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=chromium) if chromium else await pw.chromium.launch()
        try:
            pg = await b.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
            await pg.set_content(html, wait_until='load', timeout=30000)
            try:
                await pg.wait_for_function(expr, timeout=wait_ms)
                ok = True
            except Exception:   # noqa: BLE001: never appeared
                ok = False
            return (ok and not errs), ('; '.join(errs) or ('loaded' if ok else 'the library never appeared'))
        finally:
            await b.close()
