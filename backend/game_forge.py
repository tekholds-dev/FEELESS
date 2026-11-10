"""🎮 AGT-35 THE GAME FORGE (owner 2026-11-10: "these games aren't what I wanted"). Every game used to become one of two fixed three.js
templates (runner, arena). Now a mind DESIGNS the game first (genre, core loop, controls for keys and touch, win and lose, progression, juice),
writes it on a real free engine (Phaser 3 for 2D, Babylon.js or three.js + Rapier for 3D; no Unity / Unreal key, those need a desktop editor),
and a headless browser PLAYS it before it can be filed: it must draw, take input, change state and stay free of errors. A game that fails is
handed back with the exact failures; one that keeps failing is never filed.

Every game exposes `window.__game = {state, score, start()}` so the playtest (and later the Collective's own record) can read it."""
import json
import re

ENGINES = {   # pinned, checked live 2026-11-10 (all 200 on jsDelivr); licenses carried into the parts record
    'phaser': {'name': 'Phaser 3', 'dims': '2D', 'license': 'MIT', 'tag': '<script src="https://cdn.jsdelivr.net/npm/phaser@3.80.1/dist/phaser.min.js"></script>',
               'how': 'new Phaser.Game({type: Phaser.AUTO, scale: {mode: Phaser.Scale.RESIZE}, physics: {default: "arcade"}, scene: [...]})'},
    'babylon': {'name': 'Babylon.js 7', 'dims': '3D', 'license': 'Apache-2.0', 'tag': '<script src="https://cdn.jsdelivr.net/npm/babylonjs@7.31.0/babylon.js"></script>',
                'how': 'const engine = new BABYLON.Engine(canvas, true); const scene = new BABYLON.Scene(engine); scene.collisionsEnabled = true; engine.runRenderLoop(() => scene.render())'},
    'three': {'name': 'three.js + Rapier', 'dims': '3D', 'license': 'MIT + Apache-2.0',
              'tag': '<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/","rapier":"https://cdn.jsdelivr.net/npm/@dimforge/rapier3d-compat@0.14.0/rapier.es.js"}}</script>',
              'how': "<script type=\"module\">import * as THREE from 'three'; import RAPIER from 'rapier'; await RAPIER.init(); ...</script>"},
}
ART = 'Free art you may load by https: Kenney (kenney.nl, CC0), Quaternius (quaternius.com, CC0), Poly Haven (polyhaven.com, CC0). Or draw everything in code.'
GENRES = ('platformer', 'shooter', 'racer', 'puzzle', 'survival', 'tower defense', 'runner', 'rhythm', 'fighting', 'sports', 'idle', 'roguelite', 'other')
MAX_FIX = 2

DESIGN_SYS = ('You are a senior game designer. Design ONE small but complete browser game for the owner\'s ask: something a player would '
              'actually replay, not a demo. Answer ONLY JSON: {"title": "<2-4 words>", "genre": "<' + '|'.join(GENRES) + '>", "engine": "<phaser for 2D | babylon or three for 3D>", '
              '"pitch": "<one line>", "coreLoop": "<what the player does every 10 seconds>", "controls": {"keys": "<keys>", "touch": "<touch>"}, '
              '"win": "<how you win or how a run scores>", "lose": "<how you lose>", "progression": ["<what gets harder or unlocks>", "..."], '
              '"juice": ["<feel: screen shake, particles, sound, hit stop>", "..."], "entities": ["<player, enemies, pickups, level pieces>", "..."], '
              '"screens": ["title", "play", "game over with score and restart"]}. Pick the engine that fits the ask. Never pick an engine you cannot finish the game in.')


def design_of(raw):
    """The design JSON a mind wrote → a clean design, or ValueError. Pure."""
    m = re.search(r'\{.*\}', str(raw or ''), re.S)
    if not m:
        raise ValueError('The design was not JSON.')
    try:
        d = json.loads(m.group(0))
    except ValueError:
        raise ValueError('The design was not JSON.')
    eng = str(d.get('engine') or '').lower().strip()
    eng = eng if eng in ENGINES else ('phaser' if '2d' in json.dumps(d).lower() else 'three')
    s = lambda v, n=200: ' '.join(str(v or '').split())[:n]
    lst = lambda v, n=6: [s(x, 120) for x in (v if isinstance(v, list) else [v] if v else [])][:n]
    out = {'title': s(d.get('title'), 40) or 'Untitled', 'genre': s(d.get('genre'), 30).lower() or 'other', 'engine': eng, 'pitch': s(d.get('pitch')),
           'coreLoop': s(d.get('coreLoop')), 'controls': {'keys': s((d.get('controls') or {}).get('keys'), 120), 'touch': s((d.get('controls') or {}).get('touch'), 120)},
           'win': s(d.get('win')), 'lose': s(d.get('lose')), 'progression': lst(d.get('progression')), 'juice': lst(d.get('juice')), 'entities': lst(d.get('entities'), 10),
           'screens': lst(d.get('screens'), 4) or ['title', 'play', 'game over']}
    if not out['coreLoop'] or not (out['controls']['keys'] or out['controls']['touch']):
        raise ValueError('The design has no core loop or no controls.')
    return out


def build_sys(design):
    """The build brief for the mind that writes the game. Pure."""
    e = ENGINES[design['engine']]
    return ('You are a senior game developer. Write the WHOLE game below as ONE self-contained HTML file and nothing else (no markdown). '
            f'Engine: {e["name"]} ({e["dims"]}). Load it with exactly this tag in <head>: {e["tag"]} Start it like: {e["how"]}. '
            'Rules: it must be fully playable, with a title screen, play, and a game over screen with the score and a restart; controls on BOTH keyboard and touch '
            '(on-screen buttons or swipe on phones); it fills the window and survives a resize; it keeps 60 fps on a laptop (pool objects, no leaks). '
            'Make it FEEL good: the juice listed, sound with the Web Audio API (no audio files), clear readable HUD. ' + ART + ' '
            'REQUIRED hook, exactly: window.__game = {state: "title", score: 0, start() {/* leaves the title and begins play */}}; keep state ("title" | "play" | "over") '
            'and score current as the game runs. No other network, no eval, no alert().\n\nTHE DESIGN:\n' + json.dumps(design, indent=1))


def fix_sys(design, report):
    return (build_sys(design) + '\n\nYOUR LAST BUILD FAILED THE PLAYTEST. Fix every one of these and return the whole file again:\n- ' + '\n- '.join(report['why']))


def html_of(raw):
    """A mind's reply → the HTML file it wrote (fences stripped). Pure."""
    t = re.sub(r'^```(?:html)?\s*|```\s*$', '', str(raw or '').strip(), flags=re.M).strip()
    i = t.lower().find('<!doctype'); i = i if i >= 0 else t.lower().find('<html')
    return t[i:] if i >= 0 else t


PLAY = r"""async () => {
  const g = () => window.__game; const out = {hook: !!g(), states: [], errorsBefore: 0};
  const canvas = document.querySelector('canvas'); out.canvas = !!canvas && canvas.width > 50 && canvas.height > 50;
  const frames = await new Promise(r => { let n = 0; const t0 = performance.now(); const f = () => { n++; if (performance.now() - t0 < 1000) requestAnimationFrame(f); else r(n); }; requestAnimationFrame(f); });
  out.fps = frames; out.states.push(g() && g().state);
  try { g() && g().start && g().start(); } catch (e) { out.startError = String(e).slice(0, 120); }
  await new Promise(r => setTimeout(r, 400)); out.states.push(g() && g().state); out.score0 = g() && g().score;
  return out;
}"""


def _spread(a, b=None):
    """How much a screenshot varies (one image: is anything drawn), or how much two differ (did the screen change). Reads the PNG/JPEG the
    browser composited, so WebGL counts too (a WebGL canvas reads back blank). → a number, 0 = flat / identical."""
    import io
    from PIL import Image, ImageChops, ImageStat
    x = Image.open(io.BytesIO(a)).convert('L').resize((96, 56))
    if b is None:
        return round(ImageStat.Stat(x).stddev[0], 1)
    x, y = Image.open(io.BytesIO(a)).convert('L'), Image.open(io.BytesIO(b)).convert('L')   # full size: a small sprite moving is still a change
    return sum(ImageChops.difference(x, y).point(lambda v: 255 if v > 40 else 0).histogram()[255:])   # pixels that clearly changed


async def playtest(html, chromium, keys=('ArrowRight', 'ArrowLeft', 'ArrowUp', 'Space', 'KeyW', 'KeyD')):
    """Plays the game in a real browser (https only, a software GPU). → {'ok', 'why': [...], 'facts': {...}}"""
    from playwright.async_api import async_playwright
    why, facts, errs = [], {}, []
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=chromium, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
        try:
            ctx = await b.new_context(viewport={'width': 1280, 'height': 760})
            async def only_https(route):
                await (route.continue_() if route.request.url.startswith(('https://', 'data:', 'blob:', 'about:')) and route.request.method == 'GET' else route.abort())
            await ctx.route('**/*', only_https); pg = await ctx.new_page()
            pg.on('pageerror', lambda e: errs.append(str(e)[:140]))
            await pg.set_content(html, wait_until='load', timeout=30000); await pg.wait_for_timeout(2500)
            facts = await pg.evaluate(PLAY)
            shot0 = await pg.screenshot(type='jpeg', quality=40); facts['look0'] = _spread(shot0)
            await pg.mouse.click(640, 380)
            for k in keys:
                await pg.keyboard.down(k); await pg.wait_for_timeout(260); await pg.keyboard.up(k)
            await pg.wait_for_timeout(600)
            facts['after'] = await pg.evaluate('() => window.__game ? {state: window.__game.state, score: window.__game.score} : null')
            shot1 = await pg.screenshot(type='jpeg', quality=40); facts['look1'] = _spread(shot1); facts['changed'] = _spread(shot0, shot1); facts['moved'] = facts['changed'] > 150
            facts['errors'] = errs[:5]
        except Exception as e:   # noqa: BLE001: a page that will not load fails the test, plainly
            why.append(f'it did not load: {type(e).__name__}: {str(e)[:120]}')
        finally:
            await b.close()
    if facts:
        if not facts.get('hook'):
            why.append('window.__game is missing (it must expose state, score and start())')
        if not facts.get('canvas'):
            why.append('no canvas was drawn')
        if max(facts.get('look0') or 0, facts.get('look1') or 0) < 2:
            why.append('the screen is one flat colour: nothing is drawn')
        if facts.get('startError'):
            why.append(f'start() threw: {facts["startError"]}')
        if facts.get('hook') and 'play' not in [facts['states'][-1] if facts.get('states') else None, (facts.get('after') or {}).get('state')]:
            why.append('after start() and input the state never became "play"')
        if not facts.get('moved'):
            why.append('nothing on screen changed while keys were pressed')
        if (facts.get('fps') or 0) < 20:
            why.append(f'it runs at {facts.get("fps")} frames a second in the test browser (needs 20+)')
        for e in facts.get('errors') or []:
            why.append(f'page error: {e}')
    return {'ok': not why, 'why': why[:8], 'facts': {k: facts.get(k) for k in ('fps', 'states', 'after', 'moved', 'changed', 'look0', 'look1', 'errors')}}
