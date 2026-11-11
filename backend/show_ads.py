"""🎬 SHOWCASE ADS (owner 2026-11-11: "$1.25 on Happy for proof-realistic ad-like previews for the Features showcase … only owner can download").
One owner-staff agent builds one ad page per proof type through its normal Build folder (so each ad is a real PoStatic folder the owner can open),
one at a time, under a hard budget: a build starts only while the money already spent plus one average build stays under the cap. Each finished
page is then recorded in headless Chromium at 1280 × 720 into a .webm the owner can play in the Showcase and download. Nothing here posts anything."""
import asyncio
import re
import time
from pathlib import Path

BUDGET = 1.25
KINDS = ('pos', 'pow', 'pop', 'pob', 'poc', 'poe')
NAME = {'pos': 'PoStatic', 'pow': 'PoW', 'pop': 'PoP', 'pob': 'PoB', 'poc': 'PoC', 'poe': 'PoEco'}
# 🎨 Each proof type its own light (owner 2026-11-11: "make the ad lit, not just fucking green") — the same light as its card in the Showcase.
LOOK = {
    'pos': 'electric cyan #5cc8ff and ultraviolet #7b5cff on midnight blue, code glowing like neon tubes',
    'pow': 'fire orange #ff9f43 and molten gold #ffd166 on charcoal, candles that burn, sparks on every buy',
    'pop': 'violet #b58cff and liquidation red #ff4d6d on deep indigo, laser lines where leverage dies',
    'pob': 'stadium gold #ffc94d under white floodlights on night blue, a scoreboard that lights up',
    'poc': 'hot magenta #ff5fb0 and electric cyan #3de0ff on black, a social feed that pops',
    'poe': 'teal #36e2c4 and gold #f5c542 on deep navy, ledger bars that rise like a skyline',
}
STYLE = ('A 16:9 animated ad page, 1280 × 720, that plays by itself in a loop of about 14 seconds with no clicks: 4 scenes that cut with motion '
         '(scale, slide, light sweep), one big headline per scene in heavy type, live-looking numbers that count up, and a last scene with the FEELESS '
         'wordmark and the line "Start it in one sentence". LIT, not flat: saturated colour, cinematic light (rays, bloom, a moving spotlight, glow on the hot '
         'number), depth from layered gradients and glass panels with an inner highlight. Colours: {look}. Not the same green as every other ad. '
         'Motion with CSS @keyframes and SVG only: no libraries, no CDN scripts, at most one small inline script for the count-ups. Every scene must be '
         'visible from the first frame (never wait for a click, never start at opacity 0 without its own animation). Draw everything with HTML, CSS and '
         'SVG (no stock photos, no emoji as art). Say SAMPLE in small type on any number that is not real. One self-contained HTML file.')
BRIEF = {
    'pos': 'Ad for PoStatic, Proof of Static: one sentence becomes a working site, game or dashboard. Show a typed sentence, the code writing itself, the page appearing, a store-check ring hitting 100.',
    'pow': 'Ad for PoW, Proof of Work: an agent scouts a new Solana coin on five sites, two minds argue, it trades, and the proof file is graded. Show scouting cards, a candle chart, the buy, the graded score.',
    'pop': 'Ad for PoP, Proof of Perps: two minds call BTC long or short blind, sealed, then opened on the true chart with liquidation lines where 10x dies.',
    'pob': 'Ad for PoB, Proof of Bids: picks on tonight\'s game from different sites, a 3-leg parlay slip, and the scoreboard grading each leg green or red.',
    'poc': 'Ad for PoC, Proof of Content: what is trending today, two angles pitched, the post written, a short clip cut with big captions.',
    'poe': 'Ad for PoEco, Proof of Eco: an agent\'s books kept true, income vs costs month by month as bars, tax set aside, each month sealed with a hash.',
}


def ask_for(kind):
    return f"{BRIEF[kind]} {STYLE.format(look=LOOK[kind])}"


def spent(jobs, cost_of):
    """Money the ad builds have cost so far. cost_of(ws_id) → $."""
    return round(sum(float(cost_of(w) or 0) for j in (jobs or {}).values() for w in [j.get('ws'), *(j.get('lostWs') or [])] if w), 6)   # a build a restart killed still cost money


def may_start(jobs, cost_of, budget=BUDGET):
    """A new build may start only if spent + one average build (or $0.15 before any finished) stays under the cap. Pure."""
    s = spent(jobs, cost_of); done = [j for j in (jobs or {}).values() if j.get('ws') and float(cost_of(j['ws']) or 0) > 0]
    avg = (s / len(done)) if done else 0.15
    return s + avg <= budget, s


def next_kind(jobs):
    return next((k for k in KINDS if not (jobs or {}).get(k, {}).get('ws')), None)


HIDDEN_FIX = '<style>[hidden]{display:none!important}</style>'


def playable(html):
    """🎬 A page's own `.x{display:grid}` beat its `hidden` attribute and kept an "Animation unavailable" cover on the whole PoP ad (2026-11-11):
    hidden means hidden. Goes inside <head> (before the doctype would drop the page into quirks mode). Pure."""
    h = str(html or '')
    m = re.search(r'<head[^>]*>', h, re.I) or re.search(r'<html[^>]*>', h, re.I) or re.search(r'<!doctype[^>]*>', h, re.I)
    return h[:m.end()] + HIDDEN_FIX + h[m.end():] if m else HIDDEN_FIX + h


def fix_ask(errs):
    """The one fix pass a crashing ad gets: its own errors, word for word, and nothing else to change. Pure."""
    return ('This ad page crashes while it plays, so its scenes never show. Fix exactly these errors and change nothing else: '
            + ' | '.join(str(e)[:220] for e in (errs or [])[:3]))


async def record(html, out: Path, chromium, seconds=14, timeout_s=60, errs=None):
    """Plays one page at 1280 × 720 for `seconds` and saves it as out (.webm). → True when a video was written.
    `errs` (a list) collects the page's own crashes and blocked loads while it plays: 4 of the first 6 ads recorded 14 s of an empty stage (2026-11-11)."""
    if not chromium or not html:
        return False
    html = playable(html)

    async def run():
        from playwright.async_api import async_playwright
        tmp = out.parent / f'.rec-{out.stem}'
        tmp.mkdir(parents=True, exist_ok=True)
        async with async_playwright() as pw:
            b = await pw.chromium.launch(executable_path=chromium)
            try:
                ctx = await b.new_context(viewport={'width': 1280, 'height': 720}, record_video_dir=str(tmp), record_video_size={'width': 1280, 'height': 720})
                pg = await ctx.new_page()
                if errs is not None:
                    pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
                    pg.on('console', lambda m: m.type == 'error' and errs.append(m.text[:300]))
                await pg.set_content('<body style="margin:0;background:#04070a"></body>')   # the first frames are night, not a white flash
                await pg.set_content(html, wait_until='load', timeout=20000)
                # 🎬 a game-kit page waits on "press SPACE or tap to start" (the first ad recorded 14 s of that screen, 2026-11-11): press play
                await pg.wait_for_timeout(600)
                await pg.mouse.click(640, 360)
                await pg.keyboard.press('Space')
                await pg.wait_for_timeout(seconds * 1000)
                vid = pg.video
                await ctx.close()
                src = Path(await vid.path()) if vid else None
            finally:
                await b.close()
        if src and src.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            src.replace(out)
        for f in tmp.glob('*'):
            f.unlink()
        tmp.rmdir()
        return out.exists() and out.stat().st_size > 1000
    try:
        return await asyncio.wait_for(run(), timeout_s)
    except Exception:   # noqa: BLE001 — a page that will not play is left without a video, and says so
        return False


def view(jobs, cost_of, has_video):
    rows = {}
    for k in KINDS:
        j = (jobs or {}).get(k) or {}
        rows[k] = {'name': NAME[k], 'ws': j.get('ws'), 'state': j.get('state') or ('waiting' if not j.get('ws') else 'building'), 'cost': round(float(cost_of(j.get('ws')) or 0), 4) if j.get('ws') else 0,
                   'video': bool(j.get('ws') and has_video(k)), 'at': j.get('at'), 'err': j.get('err')}
    s = spent(jobs, cost_of)
    return {'budget': BUDGET, 'spent': s, 'left': round(max(0.0, BUDGET - s), 4), 'rows': rows, 'at': round(time.time())}
