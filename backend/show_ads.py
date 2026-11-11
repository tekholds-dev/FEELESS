"""🎬 SHOWCASE ADS (owner 2026-11-11: "$1.25 on Happy for proof-realistic ad-like previews for the Features showcase … only owner can download").
One owner-staff agent builds one ad page per proof type through its normal Build folder (so each ad is a real PoStatic folder the owner can open),
one at a time, under a hard budget: a build starts only while the money already spent plus one average build stays under the cap. Each finished
page is then recorded in headless Chromium at 1280 × 720 into a .webm the owner can play in the Showcase and download. Nothing here posts anything."""
import asyncio
import re
import time
from pathlib import Path

BUDGET = 2.25   # owner 2026-11-11: +$1 for real commercial ads
# 🎬 the ads are built by a design-grade model, not the agent's own cheap pair (owner 2026-11-11: "real commercial type ads … find the best ad models
# that's efficient"). Claude Sonnet 5.5 on OpenRouter: $2 in / $10 out per M tokens, about $0.10 an ad page.
MODEL = 'anthropic/claude-sonnet-5.5'
KITS = ['gsap']   # pro timelines for commercial motion; never a game or canvas library (their text cannot be checked, their playtest is for games)
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
STYLE = ('A real TV-commercial-grade 16:9 ad page, 1280 × 720, that plays by itself in a loop of about 14 seconds with no clicks, like a launch '
         'spot from the biggest tech brands: 4 scenes on one GSAP master timeline, each a camera move (slow push-in, parallax layers, a whip-pan cut), '
         'kinetic typography (one big headline per scene in heavy type, words landing on the beat), a drawn FEELESS product shot (the real UI the brief '
         'names, as a glass device frame with live-looking numbers that count up), and a last scene: the FEELESS wordmark lockup and the line "Start it in '
         'one sentence". LIT, not flat: saturated colour, cinematic light (rays, bloom, a moving spotlight, lens flare, glow on the hot number), film grain, '
         'depth from layered gradients and glass panels with an inner highlight. Colours: {look}. Not the same green as every other ad. Motion with GSAP '
         '(load it from the kit given) plus CSS and SVG; no game library, no canvas text, no other CDN scripts. Every scene must be '
         'visible from the first frame (never wait for a click, never start at opacity 0 without its own animation). Draw everything with HTML, CSS and '
         'SVG, or use images the stash offers (no other stock photos, no emoji as art). Say SAMPLE in small type on any number that is not real. Everything fits inside the 1280 × 720 frame '
         'at every moment: one scene on screen at a time, nothing past the edges, no text on top of other text, at most one headline and one support '
         'line per scene, and no debug readouts (no state, score or timer counters). One self-contained HTML file.')
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


HIDDEN_FIX = '<style>[hidden]{display:none!important}html,body{overflow:hidden!important}</style>'   # an ad is one frame: no scrollbar, and Space can't scroll it


def playable(html):
    """🎬 A page's own `.x{display:grid}` beat its `hidden` attribute and kept an "Animation unavailable" cover on the whole PoP ad (2026-11-11):
    hidden means hidden. Goes inside <head> (before the doctype would drop the page into quirks mode). Pure."""
    h = str(html or '')
    m = re.search(r'<head[^>]*>', h, re.I) or re.search(r'<html[^>]*>', h, re.I) or re.search(r'<!doctype[^>]*>', h, re.I)
    return h[:m.end()] + HIDDEN_FIX + h[m.end():] if m else HIDDEN_FIX + h


def fix_ask(errs, lay=()):
    """The one fix pass a broken ad gets: its own crashes and layout faults, word for word, and nothing else to change. Pure."""
    parts = []
    if errs:
        parts.append('It crashes while it plays, so its scenes never show. Fix exactly these errors: ' + ' | '.join(str(e)[:220] for e in errs[:3]) + '.')
    if lay:   # a layout fault is a structure problem: patches never landed on it (2026-11-11), so the page is rebuilt whole, same scenes and words
        parts.append('Its layout breaks the 1280 × 720 frame: ' + ' ; '.join(str(f)[:160] for f in lay[:6]) + '. Rebuild the page from scratch with the '
                     'same four scenes and words, in HTML, CSS and SVG only (no canvas, no game library), every scene inside the frame, nothing past the '
                     'edges, no text on top of other text, no debug readouts.')
    return 'This ad page breaks while it plays. ' + ' '.join(parts) + (' Fix those and change nothing else.' if not lay else '')


# 📐 THE FRAME CHECK (owner 2026-11-11: "shit clipped", text stacked on text): at the middle of each of the 4 scenes every visible run of text is
# measured by its own glyphs. Faults: text or a card cut by the 1280 × 720 frame, text on text, a solid panel over words, an empty frame, words
# painted on a canvas (nothing can check them), debug counters ("STATE play · 02s / 14s").
FIT_AT = (1.8, 5.3, 8.8, 12.3)
FIT_JS = r"""(at) => {
  const W = innerWidth, H = innerHeight, out = [], runs = [];
  const shown = el => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const s = getComputedStyle(e); if (s.display === 'none' || s.visibility === 'hidden') return 0; o *= +s.opacity; } return o; };
  const inside = r => r.right > 0 && r.left < W && r.bottom > 0 && r.top < H;
  const cut = r => inside(r) && (r.right > W + 4 || r.bottom > H + 4 || r.left < -4 || r.top < -4);
  const solid = s => { const m = (s.backgroundColor || '').match(/[\d.]+/g); return (m && (m.length < 4 || +m[3] > 0.3)) || (s.backgroundImage && s.backgroundImage !== 'none'); };
  for (const el of document.body.querySelectorAll('*')) {
    if (/^(script|style|title|noscript)$/i.test(el.tagName)) continue;
    const nodes = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim().length > 1); if (!nodes.length) continue;
    let r = null; for (const n of nodes) { const g = document.createRange(); g.selectNodeContents(n); const b = g.getBoundingClientRect(); if (b.width < 2) continue;
      r = r ? { left: Math.min(r.left, b.left), top: Math.min(r.top, b.top), right: Math.max(r.right, b.right), bottom: Math.max(r.bottom, b.bottom) } : { left: b.left, top: b.top, right: b.right, bottom: b.bottom }; }
    const o = r ? shown(el) : 0; if (!r || o < 0.15) continue;
    runs.push({ el, r, o, t: nodes.map(n => n.textContent).join(' ').replace(/\s+/g, ' ').trim().slice(0, 48) });
  }
  const seen = runs.filter(a => a.o >= 0.35 && inside(a.r));
  const big = [...document.querySelectorAll('canvas')].some(c => { const r = c.getBoundingClientRect(); return r.width * r.height > W * H * 0.5 && shown(c) > 0.35; });
  if (big && seen.length < 4) out.push('its words are painted on a canvas: draw every headline and number as HTML text');
  if (!big && !seen.length) out.push('the frame is empty at ' + at + 's: every scene needs its headline on screen');
  for (const a of seen) {
    if (cut(a.r)) out.push('cut by the frame: "' + a.t + '"');
    if (/\bSTATE\s+\w+|\d+\s*s\s*\/\s*\d+\s*s\b|\bFPS\b|\bDEBUG\b/.test(a.t)) out.push('a debug readout: "' + a.t + '"');
    const cx = (a.r.left + a.r.right) / 2, cy = (a.r.top + a.r.bottom) / 2;   // something solid drawn over the middle of the words
    for (const t of document.elementsFromPoint(Math.min(W - 1, Math.max(0, cx)), Math.min(H - 1, Math.max(0, cy)))) {
      if (t === a.el || t.contains(a.el) || a.el.contains(t)) break;
      if ((/^(img|video|canvas)$/i.test(t.tagName) || solid(getComputedStyle(t))) && shown(t) > 0.5) { out.push('covered: "' + a.t + '" sits under another panel'); break; }
    }
  }
  for (const el of document.body.querySelectorAll('div,section,article,aside,figure,li')) {   // a card half off the frame
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    if (r.width < 120 || r.height < 48 || r.width > W * 0.95 || r.height > H * 0.95 || !cut(r) || !(solid(s) || parseFloat(s.borderTopWidth) > 0) || shown(el) < 0.35) continue;
    const t = (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 40); out.push('a panel cut by the frame' + (t ? ': "' + t + '"' : '')); if (out.length > 10) break;
  }
  for (let i = 0; i < runs.length; i++) for (let j = i + 1; j < runs.length; j++) {
    const a = runs[i], b = runs[j]; if (a.el.contains(b.el) || b.el.contains(a.el) || (a.o < 0.35 && b.o < 0.35)) continue;
    const core = r => { const k = (r.bottom - r.top) * 0.22; return { left: r.left, right: r.right, top: r.top + k, bottom: r.bottom - k }; };   // the glyphs, not the font's leading
    const A = core(a.r), B = core(b.r);
    const w = Math.min(A.right, B.right) - Math.max(A.left, B.left), h = Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top);
    const small = Math.min((A.right - A.left) * (A.bottom - A.top), (B.right - B.left) * (B.bottom - B.top));
    if (w > 0 && h > 0 && w * h > small * 0.3) out.push('text on text: "' + a.t + '" over "' + b.t + '"');
  }
  return [...new Set(out)].slice(0, 8);
}"""


async def record(html, out: Path, chromium, seconds=14, timeout_s=60, errs=None, lay=None):
    """Plays one page at 1280 × 720 for `seconds` and saves it as out (.webm). → True when a video was written.
    `errs` (a list) collects the page's own crashes and blocked loads while it plays: 4 of the first 6 ads recorded 14 s of an empty stage (2026-11-11).
    `lay` (a list) collects the frame check's faults (FIT_JS at FIT_AT)."""
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
                await pg.evaluate('scrollTo(0, 0)')   # Space scrolled an overflowing ad mid-recording (2026-11-11)
                t0 = 0.0
                for at in (a for a in FIT_AT if lay is not None and a < seconds):
                    await pg.wait_for_timeout(int((at - t0) * 1000)); t0 = at
                    for f in await pg.evaluate(FIT_JS, at):
                        if f not in lay:
                            lay.append(f)
                await pg.wait_for_timeout(int((seconds - t0) * 1000))
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
