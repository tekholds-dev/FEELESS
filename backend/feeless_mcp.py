"""⚡ FEELESS MCP — a READ-ONLY tool server for the owner's LM Studio model (owner, 2026-10-14: "a degen meta MCP server for my lm model …
smart, degen talking, pull from the internet easy and fast").

Speaks the Model Context Protocol (JSON-RPC 2.0) two ways, no SDK needed:
  stdio : backend/.venv/bin/python backend/feeless_mcp.py                (LM Studio on THIS Mac: "command" in mcp.json)
  http  : backend/.venv/bin/python backend/feeless_mcp.py --http         (LM Studio on another machine: "url" + a Bearer token)
          POST /mcp (Streamable HTTP, JSON answers). Every request needs `Authorization: Bearer <token>`; only loopback + private LAN
          clients are served. Token = FEELESS_MCP_TOKEN in backend/.env, else generated once into backend/data/mcp_token (0600).

THE WALL (hard-coded, tested in tests/test_feeless_mcp.py): every tool READS. Nothing here can sign, send, trade, top up, withdraw,
change a setting or reach an /admin route. The card / agents / evidence come from the local services' PUBLIC endpoints and the data files
the desk already writes. web_fetch refuses private / loopback / link-local / metadata addresses (checked on every redirect hop).
Tool answers are compact text (a small model's context is small)."""
import html
import ipaddress
import json
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env_loader  # noqa: F401  — backend/.env (Brave keys, LM base) when LM Studio launches this file directly; prints nothing (stdout is the MCP wire)
import re
import secrets
import socket
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import httpx

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
REP = os.environ.get('FEELESS_REP_URL', 'http://127.0.0.1:5077/api/reputation')
MKT = os.environ.get('FEELESS_MKT_URL', 'http://127.0.0.1:5001/api/market')
NAME, VERSION, PROTO = 'feeless', '1.0.0', '2025-06-18'
MAX_OUT = 6000          # chars per tool answer
FETCH_MAX = 2_000_000   # bytes read from one web page
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'
_cache = {}


def _http():
    if 'c' not in _cache:
        _cache['c'] = httpx.Client(timeout=12.0, headers={'User-Agent': UA}, follow_redirects=False)
    return _cache['c']


def _memo(key, ttl, fn):
    hit = _cache.get(('m', key))
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    v = fn()
    _cache[('m', key)] = (time.time(), v)
    return v


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def _usd(v):
    v = _f(v)
    a = abs(v)
    s = f"{a / 1e9:.2f}B" if a >= 1e9 else f"{a / 1e6:.2f}M" if a >= 1e6 else f"{a / 1e3:.1f}K" if a >= 1e3 else f"{a:.2f}"
    return ('-' if v < 0 else '') + '$' + s


def _cut(text, n=MAX_OUT):
    t = str(text or '')
    return t if len(t) <= n else t[:n - 40] + f"\n… (cut, {len(t) - n + 40} more chars)"


def _get(base, path, ttl=10):
    def go():
        r = _http().get(base + path, timeout=20)
        r.raise_for_status()
        return r.json()
    return _memo(base + path, ttl, go)


def _file(name):
    p = DATA / name
    try:
        st = p.stat()
    except OSError:
        return {}
    hit = _cache.get(('f', name))
    if hit and hit[0] == st.st_mtime:
        return hit[1]
    try:
        v = json.loads(p.read_text())
    except Exception:
        v = {}
    _cache[('f', name)] = (st.st_mtime, v)
    return v


# ── FEELESS tools (read only) ────────────────────────────────────────────────────────────────────────────────────────────────────
def t_card(_a):
    """The real Fuse card: put in → now, P&L, who holds the controls, every coin with its % and $."""
    d = _get(REP, '/fuses/prime', 8)
    cs = d.get('cards') or []
    cs = cs if isinstance(cs, list) else list(cs.values())
    real = [c for c in cs if c.get('real')]
    if not real:
        return 'No real card is running.'
    out = [truth_line((_file('agents_view.json') or {}).get('office') or {})]
    for c in real:
        m = c.get('math') or {}
        out.append(f"REAL CARD {c.get('tpl')} ({c.get('tier')}) — put in {_usd(m.get('putIn'))} · now {_usd(m.get('nowUsd') or c.get('valueUsd'))} · "
                   f"all-time P&L {_usd(m.get('pnlUsd'))} · fees apart {_usd(m.get('feesUsd'))} · this run {_f(c.get('pnlPct')):+.1f}% · "
                   f"held by {c.get('holdBy') or 'engine'}")
        for l in c.get('legs') or []:
            if l.get('placeholder'):
                out.append('  ○ seat open')
                continue
            flags = ' '.join(w for w, on in (('❄', l.get('frozen')), ('🏠', l.get('house')), ('⏳buying', l.get('buying')), ('🎟', l.get('ticket'))) if on)
            out.append(f"  ${l.get('symbol')} {_f(l.get('pnlPct')):+.1f}% · {_usd(l.get('usd'))} · pool {_usd(l.get('liq'))} · held "
                       f"{(time.time() - _f(l.get('at'), time.time())) / 60:.0f}m {flags}".rstrip())
    paper = [c for c in cs if not c.get('real') and _f(c.get('startUsd')) > 0]
    if paper:
        out.append('PAPER: ' + ' · '.join(f"{c.get('tier')} {_usd(c.get('startUsd'))}→{_usd(c.get('valueUsd'))}" for c in paper))
    return '\n'.join(out)


def t_agents(_a):
    """The agents' desk right now: mission, capital stance, seats, top candidates and what holds them back, the Judge."""
    v = _file('agents_view.json')
    o = v.get('office') or {}
    if not o:
        return 'The agents have not written a snapshot yet (backend/data/agents_view.json).'
    mi, cap = o.get('mission') or {}, o.get('capital') or {}
    lines = [f"MISSION {mi.get('phase')} · put in {_usd(mi.get('putIn'))} · value {_usd(mi.get('value'))} · needs {mi.get('needX')}× to breakeven · "
             f"stage {mi.get('lock')}",
             f"CAPITAL {cap.get('state')} ×{cap.get('mult')} — {cap.get('why')}"]
    if cap.get('leaks'):
        lines.append('LEAKS ' + ' · '.join(f"{x['rule']} n{x['n']} avg {x['avgPct']:+.1f}%" for x in cap['leaks'][:3]))
    if (cap.get('brake') or {}).get('on'):
        lines.append('BRAKE ON — ' + str(cap['brake'].get('why')))
    for s in o.get('seatBoard') or []:
        if s.get('empty'):
            lines.append(f"SEAT {s.get('seat')} open — {s.get('why') or s.get('blocker') or ''}"[:200])
        else:
            lines.append(f"SEAT {s.get('seat')} ${s.get('symbol')} {_f(s.get('pct')):+.1f}% · {s.get('vel')} · {s.get('structure')} · held "
                         f"{_f(s.get('heldMin')):.0f}m · {s.get('result')} ({s.get('rule')}): {s.get('why')}"[:260])
    cands = ((o.get('kernel') or {}).get('candidates') or [])[:10]
    if cands:
        lines.append('TOP CANDIDATES (status · rank · cap · age · 5m · buyers · why):')
        for c in cands:
            lines.append(f"  ${c.get('symbol')} {c.get('status')} · {_f(c.get('rank')):.0f} · {_usd(c.get('cap'))} · {_f(c.get('ageMin')):.0f}m · "
                         f"{_f(c.get('move5m')):+.1f}% · {_f(c.get('buyShare')):.0f}% buys · {c.get('why')} · devil: {c.get('devil')}"[:240])
    j = o.get('judge') or {}
    if j:
        lines.append('JUDGE ' + json.dumps({k: j.get(k) for k in ('trial', 'crown', 'last') if j.get(k)}, default=str)[:400])
    return '\n'.join(lines)


def t_trades(a):
    """What really happened: closed real trades, the ledger (buys, sells, refusals), the Judge's loss reviews, card events — for a window."""
    import chat_evidence as cev
    q = str(a.get('question') or a.get('window') or 'last 12 hours')[:200]
    now = time.time()
    w = cev.window(q, now)
    arch = _file('agent_archive.json') or {}
    office = _file('agent_office.json') or {}
    hq = _file('fuse_hq.json') or {}
    cards = ((hq.get('prime') or {}).get('cards') or {})
    tid = next((k for k, c in cards.items() if (c or {}).get('real')), 'degen')
    try:
        import store
        ledger, _last = store.Ledger(DATA / 'fuse_wallet.json').since(0)
    except Exception:
        ledger = []
    pk, _st = cev.packet(q, w, arch.get('positions'), ledger, ((office.get('judge') or {}).get('reviews')) or [],
                         (cards.get(tid) or {}).get('events') or [], [], now, tid)
    return _cut(json.dumps(cev.shrink(pk, MAX_OUT - 200), default=str, separators=(',', ':')))


def t_coin(a):
    """Everything FEELESS reads about one coin (by mint): vital, holders, dev, tape, trench read, Pump callers, socials."""
    mint = str(a.get('mint') or '').strip()
    if not re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', mint):
        return 'Give a Solana mint address (32–44 base58 characters). Use token_search to find one from a ticker.'
    d = _get(REP, f'/coin-read/{mint}', 10)
    return _cut(json.dumps(d, default=str, separators=(',', ':')))


def t_token_search(a):
    """Find coins by ticker / name / CA (FEELESS market search: DexScreener → Jupiter)."""
    q = str(a.get('query') or '').strip()[:60]
    if not q:
        return 'Give a ticker, name or mint.'
    d = _get(MKT, f'/search?q={quote_plus(q)}', 20)
    rows = d.get('pairs') if isinstance(d, dict) else d
    act = lambda p: (_f((p.get('volume') or {}).get('h24')), _f((p.get('liquidity') or {}).get('usd')))
    best = {}
    for p in rows or []:   # one row per coin: its most-traded pool (a dead pool can carry a nonsense cap / move)
        m_ = (p.get('baseToken') or {}).get('address')
        if m_ and (m_ not in best or act(p) > act(best[m_])):
            best[m_] = p
    out = []
    for p in sorted(best.values(), key=act, reverse=True)[:10]:
        b = p.get('baseToken') or {}
        out.append(f"${b.get('symbol')} {b.get('name')} · mint {b.get('address')} · {p.get('chainId')} · cap {_usd(p.get('marketCap') or p.get('fdv'))} · "
                   f"pool {_usd((p.get('liquidity') or {}).get('usd'))} · 1h {_f((p.get('priceChange') or {}).get('h1')):+.1f}% · "
                   f"vol 24h {_usd((p.get('volume') or {}).get('h24'))}")
    return '\n'.join(out) or 'Nothing found.'


def t_trench(a):
    """The trench right now: market weather + the open launch list (every coin the feed sees, busiest first, with its safety mark)."""
    n = max(5, min(40, int(_f(a.get('limit'), 20))))
    out = []
    try:
        fc = _get(REP, '/fuses/forecast', 30)
        out.append('WEATHER ' + json.dumps({k: fc.get(k) for k in ('weather', 'trend', 'green', 'buys') if fc.get(k) is not None}, default=str)[:400])
    except Exception:
        pass
    d = _get(REP, '/fuses/trench/open', 15)
    for r in (d.get('rows') or [])[:n]:
        out.append(f"${r.get('symbol')} {r.get('mint')} · {_f(r.get('ageH')) * 60:.0f}m old · cap {_usd(r.get('mcap'))} · vol1h {_usd(r.get('vol1h'))} · "
                   f"5m {_f(r.get('chg5m')):+.1f}% · 1h {_f(r.get('chg1h')):+.1f}% · buys {_f(r.get('buyShare')):.0f}% · "
                   f"{'✅ safe' if r.get('safe') is True else '⚠ failed: ' + ', '.join(map(str, r.get('fails') or []))[:60] if r.get('safe') is False else '❔ unscanned'}")
    return _cut('\n'.join(out))


LENSES = {'pump': ('ptrend', "🔥 Pump.fun's OWN trending tab, in Pump's order"), 'movers': ('live', '🚀 live movers (5-min $ × move)'),
          'volume': ('volume', '🌊 busiest by 1h volume'), 'dips': ('bottom', '🟢 dips & bottoms'), 'callers': ('procall', '🎯 proven Pump callers'),
          'narrative': ('wave', '🌊 narrative leaders (the original of a ticker wave)'), 'best': ('best', "🏆 the agents' best now")}


def t_pump_trending(a):
    """Pump.fun's own trending list (or another FEELESS pick list) with every vital FEELESS has on each coin — read, vital grade, holders,
    top-10, bundles, organic share, socials — so a model can shortlist, then `investigate` the best 2–3."""
    key = str(a.get('list') or 'pump').lower()
    lens, label = LENSES.get(key, LENSES['pump'])
    n = max(3, min(30, int(_f(a.get('limit'), 8))))   # 8 by default: a small local model (gemma e2b) lost the thread on a 15-coin answer
    d = _get(REP, f'/fuses/discover?lens={lens}', 20) or {}
    out = [f"{label} · {len(d.get('pools') or [])} coins · FACT = FEELESS's live read (Jupiter / DexScreener / our scan). Next: investigate(mint) the best 2–3."]
    for r in (d.get('pools') or d.get('rows') or [])[:n]:
        v, tv = r.get('vital') or {}, r.get('tv') or {}
        call = (tv.get('call') or [None, None])[1]
        soc = ' '.join(x for x, k in (('site', 'site'), ('X', 'x'), ('tg', 'tg')) if r.get(k)) or 'no socials'
        out.append(f"${r.get('symbol')} {r.get('baseAddress') or r.get('mint')} · {_f(r.get('ageH')) * 60:.0f}m · cap {_usd(r.get('mcap'))} · pool {_usd(r.get('liquidityUsd'))} · "
                   f"vol1h {_usd(r.get('vol1h'))} · 1h {_f(r.get('change1h')):+.0f}% · 5m {_f(r.get('change5m')):+.0f}% · buys {_f(r.get('buyShare')):.0f}% · "
                   f"vital {v.get('grade') or '?'} · read {call or '—'} · top10 {r.get('top10') if r.get('top10') is not None else '?'}% · "
                   f"organic {v.get('organicPct') if v.get('organicPct') is not None else '?'}% · bundled {r.get('bundledN') if r.get('bundledN') is not None else '?'} · {soc}")
    return _cut('\n'.join(out))


def t_memory(a):
    """🗄 The AI's filed memory (ai_memory.py): the notes that fit the question — how the owner trades, his lessons, live rules, desk coins,
    how the site works. Read-only."""
    import ai_memory as aim
    mem = _file('ai_memory.json') or {}
    q = str((a or {}).get('query') or '')
    lines = aim.recall(aim.seed_site(mem, time.time()), q, 12) if q else [f"[{d}] {x.get('t')}" for d in aim.DRAWERS for x in (mem.get(d) or [])[-4:]]
    return _cut('\n'.join(lines) or 'Memory is empty so far — it fills every 10 minutes from the desk.')


def t_owner(_a):
    """👤 The owner study: how the owner's own moves graded, his seats vs where the agents would have sold, his dragged lines vs theirs."""
    v = (_file('agents_view.json') or {}).get('office', {}).get('ownerStudy') or {}
    if not v:
        return 'No owner study yet — it is built every 10 minutes from graded moves.'
    out = [f"score {v.get('score')}% good over {v.get('graded')} graded moves"] + list(v.get('findings') or []) + [f"suggests: {x.get('value')}" for x in v.get('suggestions') or []]
    return _cut('\n'.join(out))


def t_notes(_a):
    """What the owner taught the desk (notes, narratives, chart lessons, the rules the agents run), the approved build queue and the
    Brain's saved settings — the shared memory every model should read before advising."""
    out = []
    t = _file('agent_teach.json') or {}
    for x in (t.get('items') or t.get('lessons') or [])[-25:]:
        out.append(f"🎓 {x.get('kind', 'note')}: {str(x.get('text') or '')[:200]}")
    for k, r in ((t.get('rules') or {}).items() if isinstance(t.get('rules'), dict) else []):
        out.append(f"🧷 rule {k}: mode {r.get('mode')} · strength {r.get('strength')}")
    b = _file('build_queue.json') or {}
    for x in (b.get('items') or [])[-12:]:
        out.append(f"📋 build [{x.get('status')}] {str(x.get('title') or x.get('key') or '')[:80]} — {str(x.get('text') or x.get('value') or '')[:140]}")
    return _cut('\n'.join(out) or 'No notes on file yet.')


DROP = {'logo', 'avatar', 'pairAddress', 'baseAddress', 'img', 'image', 'icon', 'url', 'x', 'tg', 'site', 'links', 'sig', 'tx', 'bars', 'path',
        'spark', 'hist', 'times', 'supplySrc', 'events'}


def compact(v, depth=0, lst=6):
    """Shrink any FEELESS answer for a small model: no logos / links / raw paths, floats rounded, lists cut to their first few."""
    if isinstance(v, dict):
        return {k: compact(x, depth + 1, lst) for k, x in v.items() if k not in DROP and x not in (None, '', [], {})}
    if isinstance(v, list):
        return [compact(x, depth + 1, max(3, lst - depth)) for x in v[:max(3, lst - depth)]]
    if isinstance(v, float):
        return round(v, 4) if abs(v) < 1 else round(v, 2)
    if isinstance(v, str) and len(v) > 220:
        return v[:220] + '…'
    return v


def _j(v, n=MAX_OUT):
    return _cut(json.dumps(compact(v), default=str, separators=(',', ':'), ensure_ascii=False), n)


def levers(o):
    """Facts → the REAL control each one points at (key, value now, options). Deterministic, so a small model only has to choose.
    Every line is a reading, never an order: the owner decides."""
    cap, pol, rg, tr, seat = o.get('capital') or {}, o.get('policy') or {}, (o.get('regret') or {}).get('record') or {}, o.get('trail') or {}, o.get('seat') or {}
    ctl = {c.get('key'): c for c in pol.get('controls') or []}
    now = lambda k: f"{k} now {(ctl.get(k) or {}).get('value')} ({(ctl.get(k) or {}).get('who')}) · options {(ctl.get(k) or {}).get('options')}"
    out = []
    r = cap.get('record') or {}
    if r.get('n'):
        w, l = _f(r.get('avgWin')), abs(_f(r.get('avgLoss')))
        be = round(l / (w + l) * 100) if w + l else None
        out.append(f"EXPECTANCY: {r.get('wonPct')}% won, wins +{w}% vs losses −{l}% → {r.get('expPct')}% a bet. Break-even needs {be}% won at this payoff — "
                   f"so the fix is SMALLER LOSSES (or bigger wins), not a higher win rate.")
    lk = (cap.get('leaks') or [{}])[0]
    if lk.get('rule'):
        rugish = any(x in lk['rule'] for x in ('R5x', 'R1', 'R4', 'catastrophic', 'drain', 'rug'))
        out.append(f"BIGGEST LEAK: {lk['rule']} — {lk.get('n')} exits at {lk.get('avgPct')}% each. " + (
            "These are rugs / pulled pools that gap straight through any stop (the −45% catastrophic line is fixed and can't save a pulled pool). "
            f"To keep rugs OFF the card RAISE one of these (higher = fewer, safer coins, fewer trades; lower = MORE rugs): {now('agentMinAgeH')} · "
            f"{now('agentPoolMin')} · {now('agentMcMin')}." if rugish else
            f"Stops fill past their line on fast coins. Levers: {now('agentSl')} · {now('agentMaxHold')}."))
    rg_ = (cap.get('rug') or {})
    if rg_.get('n'):
        out.append(f"RUGS: {rg_.get('rugs')} of the last {rg_.get('n')} real exits ({rg_.get('ratePct')}%) averaged {rg_.get('avgPct')}% — the rug budget caps a seat at {rg_.get('capPct')}% of the card.")
    d = {k: (v or {}).get('record') or {} for k, v in (cap.get('doors') or {}).items()}
    if d.get('ready') and d.get('armed'):
        out.append(f"DOORS: ⚡ ready {d['ready'].get('expPct')}%/bet (losses {d['ready'].get('avgLoss')}%) vs 🎯 armed {d['armed'].get('expPct')}%/bet (losses {d['armed'].get('avgLoss')}%) · {now('agentEntry')}.")
    if tr.get('live') and tr.get('best'):
        out.append(f"EXITS (trail lab, {tr.get('n')} whole moves): live trail arm +{tr['live'].get('arm')}% / give back {tr['live'].get('give')}% → typical {tr['live'].get('med')}%; "
                   f"best pair arm +{tr['best'].get('arm')}% / {tr['best'].get('give')}% → {tr['best'].get('med')}% · proven: {bool(tr.get('pays'))} · {now('agentTrail')}.")
    t_ = rg.get('taken') or {}
    for k, v in rg.items():
        if k == 'taken' or not v.get('n') or v['n'] < 8:
            continue
        better = _f(v.get('med')) - _f(t_.get('med'))
        if abs(better) >= 10:
            out.append(f"BLOCKED vs TAKEN: coins held back by {k} went {v.get('med')}% (n {v['n']}) vs the coins taken {t_.get('med')}% — "
                       + ("the check is blocking WINNERS (loosening it could help — only after more coins are judged)." if better > 0 else "the check is SAVING money — keep it."))
    if seat.get('want') and _f(seat.get('held')) < _f(seat.get('want')):
        out.append(f"SEATS: {seat.get('held')} of {seat.get('want')} held — {seat.get('reason')} · chart gate (🎯 Chart says go) on: {pol.get('chartGo')}.")
    return out


def truth_line(o):
    """🧾 ONE plain line of the numbers that matter, first in every money answer — a small model copies this instead of inventing
    (2026-10-15: Qwen 4B wrote "70% won, avg win $1.2K, size $80K" on a $2 card where the record said 33% won, +11.2% vs −9.6%)."""
    m = (o or {}).get('mission') or {}
    lv = levers(o)
    exp = next((x for x in (lv if isinstance(lv, list) else []) if str(x).startswith('EXPECTANCY')), '')
    v, put = m.get('value'), m.get('putIn')
    head = f"card ${_f(v):.2f} now, ${_f(put):.2f} put in" if v is not None and put is not None else 'card value unknown'
    return (f"TRUTH — copy these exactly, they are the ONLY real numbers; every $ amount is in DOLLARS AND CENTS (the card is ${_f(v):.2f}, never thousands): "
            f"{head} · {str(exp).replace('EXPECTANCY: ', '').split('. ')[0].rstrip('.…') or 'no exit record yet'}")


def t_diagnose(_a):
    """THE MONEY PICTURE for advice: real win/loss record + where the money leaks, exits vs what the trail lab says, missed coins the
    checks blocked, the Judge's loss / win patterns, each desk's own vote record, live lab rules, execution health, and the CURRENT controls
    (the levers the owner can pull in HQ › Agents › controls)."""
    o = (_file('agents_view.json') or {}).get('office') or {}
    if not o:
        return 'No agents snapshot yet.'
    cap, tr, rg, ct = o.get('capital') or {}, o.get('trail') or {}, o.get('regret') or {}, o.get('court') or {}
    pol, ex, tape = o.get('policy') or {}, o.get('execution') or {}, o.get('tradeTape') or {}
    parts = [
        ('TRUTH', truth_line(o)),
        ('LEVERS — facts + the real control behind each (pick moves ONLY from here or CONTROLS)', levers(o)),
        ('MISSION', {k: (o.get('mission') or {}).get(k) for k in ('putIn', 'value', 'needX', 'phase', 'lock')}),
        ('CAPITAL (last 30 real exits · long = 150)', {k: cap.get(k) for k in ('state', 'mult', 'why', 'record', 'long', 'leaks', 'rug', 'brake')}),
        ('BY DOOR', {k: (v or {}).get('record') for k, v in (cap.get('doors') or {}).items()}),
        ('EXITS: trail lab (live trail vs best on whole moves, $ left on the table)', {k: tr.get(k) for k in ('n', 'live', 'best', 'pays', 'left', 'ruleWords', 'words')}),
        ('MISSED: what the checks blocked vs what was taken (30 min later)', {k: rg.get(k) for k in ('record', 'tune')}),
        ('JUDGE: loss + win patterns on real money', {k: ct.get(k) for k in ('lossPatterns', 'winPatterns', 'scores', 'promoted', 'launchShape')}),
        ('DESKS: each desk graded on its OWN vote', {d: (v or {}).get('own') or (v or {}).get('word') for d, v in (o.get('deskStats') or {}).items()}),
        ('YOUR HAND (coins whose TP/SL you dragged vs left to the agents)', o.get('ownerHand')),
        ('REAL-MONEY MEMORY', o.get('memory')),
        ('LIVE LAB RULES', [r for r in ((o.get('lab') or {}).get('rules') or []) if (r or {}).get('state') in ('live', 'LIVE')][:6]),
        ('TRADE TAPE stats (call → fill speed, slippage)', {k: tape.get(k) for k in ('stats', 'line')}),
        ('EXECUTION', {k: ex.get(k) for k in ('health', 'why', 'fills', 'failed', 'refused', 'refusedWhy', 'deltaMed', 'deltaWorst')}),
        ('SEATS', {k: (o.get('seat') or {}).get(k) for k in ('want', 'held', 'blockers', 'reason')}),
        ('UNIVERSE (who they may buy)', o.get('universe')),
        ('CONTROLS IN FORCE (HQ › Agents › controls; "agents" = they choose)', {k: (v.get('eff') if isinstance(v, dict) and 'eff' in v else v) for k, v in pol.items()}),
    ]
    out = []
    for title, v in parts:
        if v in (None, {}, []):
            continue
        body = '\n'.join(f'- {x}' for x in v) if title.startswith('LEVERS') else _j(v, 1500 if title.startswith('CONTROLS') else 700)
        piece = f"## {title}\n{body}"
        out.append(piece)
    return '\n'.join(out)


SITE = {
    'runners': ('/runners', lambda d: {k: d.get(k) for k in ('round', 'proof', 'widen', 'live', 'lanes', 'exits')}),
    'arena': ('/fuses/arena', lambda d: {k: d.get(k) for k in ('outlook', 'bestStyle', 'board', 'bredScrapped', 'dials', 'engineDial')}),
    'gauntlet': ('/fuses/contenders', lambda d: {'weather': d.get('weather'), 'nextUp': d.get('nextUp'),
                                                  'divisions': [{'label': x.get('label'), 'rule': x.get('rule'), 'top': (x.get('rows') or [])[:3]} for x in d.get('divisions') or []]}),
    'callouts': ('/fuses/pump-callouts', lambda d: {'top': d.get('top'), 'callers': d.get('callers'), 'source': d.get('source')}),
    'edge': ('/fuses/edge', lambda d: {'up': d.get('up'), 'rows': [{k: r.get(k) for k in ('symbol', 'mint', 'edge', 'tv', 'vital')} for r in (d.get('rows') or [])[:12]]}),
    'lists': ('/fuses/list-proof', None), 'calls': ('/fuses/call-proof', None),
    'strategies': ('/fuses/strategies?hours=0.25', None), 'brain': ('/fuses/trench-brain', None), 'learn': ('/fuses/learn', None),
    'forecast': ('/fuses/forecast', None), 'proof': ('/fuses/proof', lambda d: {k: d.get(k) for k in ('records', 'setups', 'duels', 'feed')}),
    'slang': ('/meme-terms', lambda d: d.get('terms')), 'season': ('/fuses/season', None),
}
SITE_WORDS = {'runners': 'runner board + round proof', 'arena': 'paper strategies board', 'gauntlet': 'every pick list (divisions) + next up',
              'callouts': "Pump's callouts + caller board", 'edge': 'the 🧬 edge ranking (Coming up)', 'lists': "each pick list's own 1h record",
              'calls': "each trench read's record (SEND IT, BOND RUN…)", 'strategies': 'proven setups per clock', 'brain': 'the trench brain (learned plays + stops)',
              'learn': 'what the real card taught the engine', 'forecast': 'market weather + entry setups now', 'proof': 'Fuse proof: records, live swaps, duels',
              'slang': 'trench words learned today', 'season': 'Fuse season'}


def t_site(a):
    """Any section of the FEELESS site, compacted."""
    sec = str(a.get('section') or '').strip().lower()
    if sec not in SITE:
        return 'Sections: ' + ' · '.join(f'{k} ({w})' for k, w in SITE_WORDS.items())
    path, pick = SITE[sec]
    d = _get(REP, path, 20)
    return _j(pick(d) if pick else d)


# ── the internet (fast, keyless) ─────────────────────────────────────────────────────────────────────────────────────────────────
def public_ip(ip):
    a = ipaddress.ip_address(ip)
    return not (a.is_private or a.is_loopback or a.is_link_local or a.is_multicast or a.is_reserved or a.is_unspecified
                or (a.version == 4 and a in ipaddress.ip_network('100.64.0.0/10')))


def safe_url(url):
    """A public http(s) URL whose host resolves ONLY to public addresses → None, else the reason."""
    u = urlparse(str(url or ''))
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
        return 'only plain public http(s) URLs'
    try:
        ips = {x[4][0] for x in socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == 'https' else 80), proto=socket.IPPROTO_TCP)}
    except OSError:
        return 'that host does not resolve'
    if not ips or not all(public_ip(i) for i in ips):
        return 'that host is on a private / local network — refused'
    return None


class _Text(HTMLParser):
    SKIP = {'script', 'style', 'noscript', 'svg', 'head', 'nav', 'footer', 'form', 'iframe'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.title, self._t, self.links = [], 0, '', False, []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag == 'title':
            self._t = True
        if tag == 'a' and len(self.links) < 40:
            h = dict(attrs).get('href')
            if h and h.startswith('http'):
                self.links.append(h)
        if tag in ('p', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'tr', 'div'):
            self.out.append('\n')

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag == 'title':
            self._t = False

    def handle_data(self, d):
        if self._t:
            self.title += d
        elif not self.skip:
            self.out.append(d)


def page_text(raw):
    p = _Text()
    try:
        p.feed(raw)
    except Exception:
        pass
    t = re.sub(r'[ \t\r\f\v]+', ' ', ''.join(p.out))
    t = re.sub(r'\n\s*\n+', '\n', t).strip()
    return p.title.strip(), t, p.links


def _fetch(url, hops=4):
    for _ in range(hops):
        why = safe_url(url)
        if why:
            raise ValueError(why)
        with _http().stream('GET', url, timeout=10) as r:
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get('location'):
                url = urljoin(url, r.headers['location'])
                continue
            buf = b''
            for ch in r.iter_bytes():
                buf += ch
                if len(buf) >= FETCH_MAX:
                    break
            return url, r.status_code, r.headers.get('content-type', ''), buf.decode(r.encoding or 'utf-8', 'replace')
    raise ValueError('too many redirects')


def t_web_fetch(a):
    """Read a public web page as plain text (title, text, links). JSON is returned as is."""
    url = str(a.get('url') or '').strip()
    n = max(500, min(MAX_OUT, int(_f(a.get('max_chars'), 4000))))
    try:
        final, code, ctype, body = _memo('fetch:' + url, 120, lambda: _fetch(url))
    except Exception as e:
        return f'Could not read it: {e}'
    if 'json' in ctype:
        return _cut(f'{code} {final}\n{body}', n)
    title, text, links = page_text(body)
    return _cut(f"{code} {final}\nTITLE {title}\n{text}\nLINKS {' '.join(links[:12])}", n)


def ddg_results(raw, n=8):
    """DuckDuckGo's HTML results → [{title, url, snippet}] (ads dropped)."""
    strip = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s or ''))).strip()
    out = []
    for blk in re.split(r'(?=<a[^>]+class="result__a")', raw)[1:]:
        m = re.match(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        if not m:
            continue
        href = html.unescape(m.group(1))
        if 'uddg=' in href:
            href = parse_qs(urlparse(href).query).get('uddg', [href])[0]
        if 'duckduckgo.com/y.js' in href or not href.startswith('http'):   # an ad
            continue
        sn = re.search(r'class="result__snippet"[^>]*>(.*?)</(?:a|div|td)>', blk, re.S)
        out.append({'title': strip(m.group(2)), 'url': href, 'snippet': strip(sn.group(1) if sn else '')[:300]})
        if len(out) >= n:
            break
    return out


def t_web_search(a):
    """Search the web (DuckDuckGo, no key; Brave Search when BRAVE_API_KEY is set). Add 'site:x.com' etc. to narrow it."""
    q = str(a.get('query') or '').strip()[:200]
    n = max(1, min(10, int(_f(a.get('limit'), 6))))
    if not q:
        return 'Give a query.'
    try:
        res = _search_rows(q, n)
    except Exception as e:
        return f'Search failed: {type(e).__name__}'
    return '\n'.join(f"{i + 1}. {x['title']}\n   {x['url']}\n   {x['snippet']}" for i, x in enumerate(res)) or 'No results (try other words).'


def t_x_search(a):
    """Find recent posts about a coin / ticker / CA on X (through the web search — X itself needs a login)."""
    return t_web_search({'query': f"site:x.com {a.get('query') or ''}", 'limit': a.get('limit') or 8})


def brave_keys(env=None):
    """Every Brave Search key in the env, in order (BRAVE_API_KEY, BRAVE_API_KEY_2 … _4)."""
    e = env if env is not None else os.environ
    return [k for k in (str(e.get(n_) or '').strip() for n_ in ('BRAVE_API_KEY', 'BRAVE_API_KEY_2', 'BRAVE_API_KEY_3', 'BRAVE_API_KEY_4')) if k]


_BRAVE_REST = {}   # key index → resting until (a 429 / quota answer rests that key; the next one takes over)
BRAVE_MONTH_CAP = 1900   # Brave's free plan ≈ 2,000 searches / month / key: stop at 1,900 so a key never hits the wall mid-month (then the next key, then DuckDuckGo)
BRAVE_GAP = 1.05         # … and ≤ 1 request a second per key (the free plan's rate)
_BRAVE_LAST = {}


def brave_budget(path=None, now=None):
    """{'month': 'YYYY-MM', 'n': {key index: searches this month}} — one small file shared by every process that searches (Brain + MCP)."""
    p = path or (DATA / 'brave_usage.json')
    m = time.strftime('%Y-%m', time.gmtime(now or time.time()))
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        d = {}
    return d if d.get('month') == m else {'month': m, 'n': {}}


def brave_note(i, path=None, now=None):
    p = path or (DATA / 'brave_usage.json')
    d = brave_budget(p, now)
    d['n'][str(i)] = int(d['n'].get(str(i), 0)) + 1
    try:
        p.write_text(json.dumps(d))
    except OSError:
        pass
    return d


def _search_rows(q, n):
    """The search behind web_search and the Brain's chat, as rows: Brave key 1 → key 2 (a refused / rate-limited key rests 60s) → DuckDuckGo.
    Cached 5 min. Rows carry `via` (brave1 / brave2 / ddg)."""
    def go():
        now = time.time()
        used = brave_budget(now=now)['n']
        for i, key in enumerate(brave_keys()):
            if _BRAVE_REST.get(i, 0) > now or int(used.get(str(i), 0)) >= BRAVE_MONTH_CAP:
                continue
            wait = BRAVE_GAP - (time.time() - _BRAVE_LAST.get(i, 0))
            if wait > 0:
                time.sleep(min(wait, BRAVE_GAP))
            _BRAVE_LAST[i] = time.time(); brave_note(i, now=now)
            try:
                r = _http().get('https://api.search.brave.com/res/v1/web/search', params={'q': q, 'count': n},
                                headers={'X-Subscription-Token': key, 'Accept': 'application/json'}, timeout=10)
            except Exception:
                _BRAVE_REST[i] = now + 30
                continue
            if r.status_code == 200:
                return [{'title': x.get('title'), 'url': x.get('url'), 'snippet': re.sub(r'<[^>]+>', '', x.get('description') or ''), 'via': f'brave{i + 1}'}
                        for x in ((r.json().get('web') or {}).get('results') or [])[:n]]
            _BRAVE_REST[i] = now + (60 if r.status_code == 429 else 600)
        r = _http().post('https://html.duckduckgo.com/html/', data={'q': q}, timeout=10)
        return [{**x, 'via': 'ddg'} for x in ddg_results(r.text, n)]
    return _memo('search:' + q.lower().strip() + str(n), 21600, go)   # 6h: the same question never spends a second search


def _read_many(urls, each=1400):
    """Fetch up to 6 public pages in parallel (the same safe_url check on every hop) → [(url, title, text excerpt | error)]."""
    from concurrent.futures import ThreadPoolExecutor

    def one(u):
        try:
            final, code, ctype, body = _memo('fetch:' + u, 120, lambda: _fetch(u))
            if 'json' in ctype:
                return u, f'{code} json', body[:each]
            title, text, _links = page_text(body)
            return final, title or str(code), text[:each]
        except Exception as e:
            return u, 'unreadable', str(e)[:120]
    with ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(one, [u for u in urls if u][:6]))


def t_deep_research(a):
    """🕸 DEEP RESEARCH: several searches (the query + angles), the best distinct pages READ in parallel, every excerpt with its source.
    Read only, public hosts only (private / loopback / metadata addresses are refused on every redirect hop)."""
    q = str(a.get('query') or '').strip()[:300]
    if len(q) < 2:
        return 'Give a query.'
    depth = max(1, min(3, int(_f(a.get('depth'), 2))))
    angles = [q] + [f'{q} {w}' for w in ('scam OR rug OR exploit', 'team OR founder OR dev', 'news')][:depth]
    seen, rows = set(), []
    for ang in angles:
        try:
            for x in _search_rows(ang, 6):
                host = (urlparse(x.get('url') or '').hostname or '').lower()
                if x.get('url') and host not in seen:
                    seen.add(host); rows.append(x)
        except Exception:
            continue
    if not rows:
        return 'No results (try other words).'
    reads = _read_many([x['url'] for x in rows[:2 + 2 * depth]])
    out = [f'DEEP RESEARCH · "{q}" · {len(angles)} searches · {len(reads)} pages read (FACT = quoted page text; anything else is your inference)']
    for u, t, txt in reads:
        out.append(f"\n■ {t}\n  {u}\n  " + re.sub(r'\s+', ' ', txt))
    out.append('\nOTHER RESULTS: ' + ' | '.join(f"{x['title']} {x['url']}" for x in rows[len(reads):len(reads) + 6]))
    return _cut('\n'.join(out), MAX_OUT)


def t_investigate(a):
    """🔎 COIN INVESTIGATION: FEELESS's own read of the coin (holders, dev, tape, callers, socials) + its website and X read from the
    links the coin itself set + web results for the ticker and the CA. Everything labelled with its source."""
    mint = str(a.get('mint') or '').strip()
    if not re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', mint):
        return 'Give a Solana mint address. Use token_search first to turn a ticker into one.'
    d = _get(REP, f'/coin-read/{mint}', 10) or {}
    flat = json.dumps(d, default=str)
    links = list(dict.fromkeys(re.findall(r'https?://[^\s"\\]+', flat)))
    site = [u for u in links if not re.search(r'(x\.com|twitter\.com|t\.me|pump\.fun|dexscreener|jup\.ag|ipfs|arweave|solscan)', u)][:2]
    xs = [u for u in links if re.search(r'(x\.com|twitter\.com)/', u)][:2]
    sym = str(d.get('symbol') or (d.get('row') or {}).get('symbol') or '').strip()
    out = ['INVESTIGATION · ' + (f'${sym} · ' if sym else '') + mint, '\n== FEELESS READ ==', _cut(flat, 2500)]
    if site:
        out.append('\n== ITS WEBSITE (the link the coin set) ==')
        for u, t, txt in _read_many(site, 900):
            out.append(f'■ {t} · {u}\n  ' + re.sub(r'\s+', ' ', txt) + ('\n  ✓ the page names this mint' if mint in txt else '\n  ✗ the page does not name this mint'))
    if xs:
        out.append('\n== ITS X (the link the coin set; X shows little without a login) ==\n' + ' '.join(xs))
    for q in [f'"{mint}"'] + ([f'${sym} solana'] if sym else []):
        try:
            rs = _search_rows(q, 5)
            out.append(f'\n== WEB: {q} ==\n' + ('\n'.join(f"- {x['title']} · {x['url']} · {x['snippet'][:160]}" for x in rs) or 'nothing found'))
        except Exception as e:
            out.append(f'\n== WEB: {q} == search failed: {type(e).__name__}')
    return _cut('\n'.join(out), MAX_OUT)


def t_now(_a):
    """Today's date and time — the model has no clock of its own (2026-10-15: Qwen "ran Python" and answered 2023)."""
    import datetime as _dt
    u = _dt.datetime.now(_dt.timezone.utc)
    loc = _dt.datetime.now().astimezone()
    return f"NOW · UTC {u.strftime('%A %Y-%m-%d %H:%M')} · owner local {loc.strftime('%A %Y-%m-%d %H:%M %Z')} · unix {int(u.timestamp())}"


TOOLS = {
    'now': (t_now, "Today's date and time (UTC + the owner's local). Call it whenever the date matters — you have no clock.", {}),
    'feeless_card': (t_card, 'The REAL Fuse card right now: put in, value, all-time P&L, who controls it, every coin with % and $, paper cards.', {}),
    'feeless_agents': (t_agents, "The agents' desk: mission, capital stance + leaks, the 4 seats (P/L, velocity, Reaper's ruling), top candidates and why, the Judge.", {}),
    'feeless_diagnose': (t_diagnose, 'THE MONEY PICTURE — use before ANY advice on fixing / scaling the agents: real win-loss record, avg win vs avg loss, where money leaks '
                         '(which exit rules), trail lab ($ left on the table), coins the checks wrongly blocked, Judge loss/win patterns, each desk graded on its own vote, '
                         'execution speed, and the CONTROLS in force (the levers the owner can change).', {}),
    'feeless_site': (t_site, 'Read any part of the FEELESS site: ' + ' · '.join(f'{k} = {w}' for k, w in SITE_WORDS.items()) + '.',
                     {'section': {'type': 'string', 'enum': list(SITE), 'description': 'which section'}}),
    'feeless_trades': (t_trades, 'Evidence of what REALLY happened in a window (closed real trades, buys/sells/refusals from the ledger, Judge loss reviews, card events). '
                       'Ask with words like "last night", "last 6 hours", "today", "why did we lose".',
                       {'question': {'type': 'string', 'description': 'the window / question, e.g. "last night" or "last 3 hours"'}}),
    'feeless_coin': (t_coin, "FEELESS's full read of one Solana coin: vital grade, holders, dev, tape (buys vs sells), trench read, Pump callers, socials.",
                     {'mint': {'type': 'string', 'description': 'the coin mint address'}}),
    'token_search': (t_token_search, 'Find a coin by ticker, name or CA → mint, cap, pool, 1h move, 1h volume.', {'query': {'type': 'string'}}),
    'trench_now': (t_trench, 'The trench right now: weather + the live launch list (busiest first, age, cap, volume, moves, buyers, ✅ / ⚠ safety).',
                   {'limit': {'type': 'integer', 'description': '5–40 coins (default 20)'}}),
    'web_search': (t_web_search, 'Search the internet. Fast, cached 5 min. Add site:x.com / site:dexscreener.com / site:pump.fun to narrow.',
                   {'query': {'type': 'string'}, 'limit': {'type': 'integer', 'description': '1–10 (default 6)'}}),
    'web_fetch': (t_web_fetch, 'Read any public web page or JSON API as plain text (title, text, links). Cached 2 min.',
                  {'url': {'type': 'string'}, 'max_chars': {'type': 'integer', 'description': '500–6000 (default 4000)'}}),
    'x_search': (t_x_search, 'Recent X posts about a ticker / coin / CA (via web search).', {'query': {'type': 'string'}, 'limit': {'type': 'integer'}}),
    'pump_trending': (t_pump_trending, "Pump.fun's OWN trending list (or list=movers / volume / dips / callers / narrative / best) with FEELESS's vitals on every coin. "
                      'Use to shortlist, then investigate the best 2–3 and deep_research the narrative.',
                      {'list': {'type': 'string', 'enum': list(LENSES)}, 'limit': {'type': 'integer', 'description': '3–30 (default 8)'}}),
    'feeless_memory': (t_memory, "The AI's filed memory: notes that fit a question (owner habits, lessons, live rules, desk coins, how FEELESS works).", {'query': {'type': 'string', 'description': 'what you are about to answer'}}),
    'owner_report': (t_owner, "The owner study: his graded moves, his seats vs the agents' exit calls, his SL / TP lines vs theirs, and what it suggests.", {}),
    'feeless_notes': (t_notes, "The owner's teachings, the rules the agents run, and the approved build queue — read before advising.", {}),
    'deep_research': (t_deep_research, 'DEEP research on anything: several searches (the query + scam / team / news angles), the best pages READ in parallel, '
                      'every excerpt with its URL. Use for projects, people, narratives, "is this legit".',
                      {'query': {'type': 'string'}, 'depth': {'type': 'integer', 'description': '1–3 (default 2): more angles + more pages'}}),
    'investigate': (t_investigate, 'Full investigation of ONE coin: FEELESS read + its own website (does it name the mint?) + its X link + web results for the CA and ticker.',
                    {'mint': {'type': 'string'}}),
}
REQUIRED = {'deep_research': ['query'], 'investigate': ['mint'], 'feeless_site': ['section'], 'feeless_coin': ['mint'], 'token_search': ['query'], 'web_search': ['query'], 'web_fetch': ['url'], 'x_search': ['query']}
LIMIT = {'feeless_diagnose': 9000}   # the money picture is the one answer worth ~2.5K tokens
FORBIDDEN_WORDS = ('sign', 'send', 'trade', 'swap', 'buy', 'sell', 'withdraw', 'topup', 'top_up', 'admin', 'wallet_key', 'transfer')


def tool_list():
    return [{'name': k, 'description': d, 'inputSchema': {'type': 'object', 'properties': p, 'required': REQUIRED.get(k, [])},
             'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': k.startswith(('web', 'x_', 'deep', 'invest'))}}
            for k, (_fn, d, p) in TOOLS.items()]


def handle(msg):
    """One JSON-RPC message → its answer (None for a notification)."""
    if not isinstance(msg, dict):
        return {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32600, 'message': 'invalid request'}}
    mid, method, params = msg.get('id'), msg.get('method'), msg.get('params') or {}
    if mid is None:
        return None
    ok = lambda r: {'jsonrpc': '2.0', 'id': mid, 'result': r}
    if method == 'initialize':
        return ok({'protocolVersion': params.get('protocolVersion') or PROTO, 'capabilities': {'tools': {'listChanged': False}},
                   'serverInfo': {'name': NAME, 'version': VERSION},
                   'instructions': 'FEELESS read-only desk + web. Call feeless_card / feeless_agents for the live state, feeless_trades for what happened, '
                                   'feeless_coin / token_search for a coin, web_search + web_fetch for anything outside.'})
    if method == 'ping':
        return ok({})
    if method == 'tools/list':
        return ok({'tools': tool_list()})
    if method == 'tools/call':
        name, args = params.get('name'), params.get('arguments') or {}
        if name not in TOOLS:
            return {'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32602, 'message': f'unknown tool {name}'}}
        t0 = time.perf_counter()
        try:
            text, err = _cut(TOOLS[name][0](args if isinstance(args, dict) else {}), LIMIT.get(name, MAX_OUT)), False
        except httpx.HTTPError as e:
            text, err = f'FEELESS service did not answer ({type(e).__name__}) — is the backend running?', True
        except Exception as e:
            text, err = f'{name} failed: {type(e).__name__}: {str(e)[:160]}', True
        _log(f"{name} {round((time.perf_counter() - t0) * 1000)}ms{' ERR' if err else ''}")
        return ok({'content': [{'type': 'text', 'text': text}], 'isError': err})
    if method in ('resources/list', 'prompts/list'):
        return ok({method.split('/')[0]: []})
    return {'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32601, 'message': f'method not found: {method}'}}


def _log(s):
    print(time.strftime('%H:%M:%S'), s, file=sys.stderr, flush=True)


def token():
    t = os.environ.get('FEELESS_MCP_TOKEN')
    if not t:
        try:
            for ln in (ROOT / '.env').read_text().splitlines():
                if ln.startswith('FEELESS_MCP_TOKEN='):
                    t = ln.split('=', 1)[1].strip().strip('"\'')
                    break
        except OSError:
            pass
    if t:
        return t
    p = DATA / 'mcp_token'
    if not p.exists():
        DATA.mkdir(parents=True, exist_ok=True)
        p.write_text(secrets.token_urlsafe(32))
        os.chmod(p, 0o600)
    return p.read_text().strip()


def client_ok(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return a.is_loopback or (a.version == 4 and any(a in ipaddress.ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')))


PRESET = Path.home() / '.lmstudio' / 'config-presets' / 'FEELESS FEE Master.preset.json'


def fee_prompt(name='OSSY'):
    """🎙 The FEE prompt as served: docs/lm_fee_prompt.txt + "WHAT FEELESS KNOWS RIGHT NOW" rebuilt from the AI memory + the owner study
    (fee_voice.living) — every install / hourly re-pull / local rewrite carries what FEELESS learned since the last one."""
    try:
        base = (ROOT.parent / 'docs' / 'lm_fee_prompt.txt').read_text().replace('{NAME}', name)
    except OSError:
        return None
    try:
        import fee_voice as _fv
        mem = _file('ai_memory.json') or {}
        study = ((_file('agents_view.json') or {}).get('office') or {}).get('ownerStudy') or {}
        live = _fv.living(mem, study)
    except Exception:
        live = ''
    return base.rstrip() + ('\n\n' + live if live else '')


def write_local_preset():
    """This Mac's LM Studio preset ← fee_prompt() (only when it changed). → True when it was written."""
    p = fee_prompt()
    if not p or not PRESET.exists():
        return False
    try:
        pj = json.loads(PRESET.read_text())
    except (OSError, ValueError):
        return False
    hit = []

    def _set(o):
        if isinstance(o, dict):
            if o.get('key') == 'llm.prediction.systemPrompt':
                hit.append(o.get('value') != p); o['value'] = p
            for v in o.values():
                _set(v)
        elif isinstance(o, list):
            for v in o:
                _set(v)
    _set(pj)
    if not any(hit):
        return False
    PRESET.write_text(json.dumps(pj, indent=2))
    return True


DESKTOP_MODEL = os.environ.get('LAN_LLM_MODEL') or 'qwen/qwen3-4b-2507'   # 🖥 desktop = M1 · 8 GB: Qwen3-4B Instruct 2507 (MLX 4-bit ≈ 2.3 GB) — best JSON / instruction model that leaves room for an 8K context
DESKTOP_FALLBACK = 'google/gemma-4-e2b'   # what it ran before — loaded when the new one can't be


def install_script(url, tok, preset_json=None, prompt=None, install_url=None, model=None):
    """🖥 The ONE script the desktop Mac runs (`curl … /lan-install | bash`): writes the FEE preset into its LM Studio and merges a
    `feeless` entry (this Mac's MCP url + token) into ~/.lmstudio/mcp.json without touching any other server there. Pure text."""
    if preset_json is None:
        try:
            preset_json = PRESET.read_text()
        except OSError:
            preset_json = json.dumps({'name': 'FEELESS FEE Master', 'operation': {'fields': [{'key': 'llm.prediction.systemPrompt', 'value': prompt or ''}]}}, indent=2)
    if prompt is None:
        prompt = fee_prompt('G4')
    if prompt:   # the FEE prompt from the repo ALWAYS wins: LM Studio once saved the agents' JSON brain prompt over the local preset (2026-10-15)
        try:
            pj = json.loads(preset_json)

            def _set(o):
                if isinstance(o, dict):
                    if o.get('key') == 'llm.prediction.systemPrompt':
                        o['value'] = prompt
                    for v in o.values():
                        _set(v)
                elif isinstance(o, list):
                    for v in o:
                        _set(v)
            _set(pj)
            preset_json = json.dumps(pj, indent=2)
        except ValueError:
            pass
    entry = json.dumps({'url': url, 'headers': {'Authorization': f'Bearer {tok}'}})
    install_url = install_url or re.sub(r'/mcp/?$', '', url) + '/lan-install'   # the keep-alive re-pulls THIS script hourly
    return f"""#!/bin/bash
# FEELESS → this Mac's LM Studio: the FEE preset + the FEELESS MCP (read-only tools). Re-run any time; it only replaces its own entries.
set -e
d="$HOME/.lmstudio"; mkdir -p "$d/config-presets"
cat > "$d/config-presets/FEELESS FEE Master.preset.json" <<'FEELESS_PRESET_EOF'
{preset_json}
FEELESS_PRESET_EOF
/usr/bin/osascript -l JavaScript <<'FEELESS_JS_EOF'
ObjC.import('Foundation');
var p = $.NSProcessInfo.processInfo.environment.objectForKey('HOME').js + '/.lmstudio/mcp.json';
var cur = {{}};
if ($.NSFileManager.defaultManager.fileExistsAtPath(p)) {{ try {{ cur = JSON.parse($.NSString.stringWithContentsOfFileEncodingError(p, $.NSUTF8StringEncoding, null).js) || {{}}; }} catch (e) {{ cur = {{}}; }} }}
cur.mcpServers = cur.mcpServers || {{}};
cur.mcpServers.feeless = {entry};
$(JSON.stringify(cur, null, 2)).writeToFileAtomicallyEncodingError(p, true, $.NSUTF8StringEncoding, null);
FEELESS_JS_EOF
# 🖥 KEEP IT RUNNING (owner, 2026-10-15: "ensure it stays running when sleep etc and updates are in it"): two LaunchAgents on THIS Mac —
#  · com.feeless.awake  = caffeinate (no idle / system sleep while logged in; a closed laptop lid or a power-off still stops it)
#  · com.feeless.lankeep = every 60s: LM Studio's server up on port $PORT + the model loaded; every hour: re-run this installer from
#    FEELESS so the preset / prompt / these helpers update by themselves. Re-running this script replaces only its own files.
PORT="${{FEELESS_LM_PORT:-1236}}"; MODEL="${{FEELESS_LM_MODEL:-{model or DESKTOP_MODEL}}}"; FALLBACK="{DESKTOP_FALLBACK}"; CTX="${{FEELESS_LM_CTX:-8192}}"
mkdir -p "$HOME/.feeless" "$HOME/Library/LaunchAgents"
cat > "$HOME/.feeless/lan-keep.sh" <<FEELESS_KEEP_EOF
#!/bin/bash
LMS="\\$HOME/.lmstudio/bin/lms"; [ -x "\\$LMS" ] || LMS="\\$(command -v lms)"; [ -n "\\$LMS" ] || exit 0
"\\$LMS" server status 2>&1 | grep -qi "running" || "\\$LMS" server start --port $PORT >/dev/null 2>&1
FAILED="\\$HOME/.feeless/model-failed"
if ! "\\$LMS" ps 2>/dev/null | grep -q "$MODEL"; then
  "\\$LMS" ls 2>/dev/null | grep -q "$MODEL" || "\\$LMS" get "$MODEL" -y >/dev/null 2>&1   # ⬇ FEELESS picks the desktop model: downloaded once, by itself
  if "\\$LMS" ls 2>/dev/null | grep -q "$MODEL" && [ "\\$(cat "\\$FAILED" 2>/dev/null)" != "$MODEL" ]; then
    "\\$LMS" unload --all >/dev/null 2>&1   # 8 GB Mac: ONE model in memory
    "\\$LMS" load "$MODEL" --context-length $CTX --gpu max -y >/dev/null 2>&1 || echo "$MODEL" > "\\$FAILED"   # a model that won't load is not retried every minute
  fi
  "\\$LMS" ps 2>/dev/null | grep -q . || "\\$LMS" load "$FALLBACK" --context-length $CTX --gpu max -y >/dev/null 2>&1   # nothing loaded → the old model
fi
st="\\$HOME/.feeless/last-update"; now=\\$(date +%s); last=\\$(cat "\\$st" 2>/dev/null || echo 0)
if [ \\$((now - last)) -ge 3600 ]; then echo \\$now > "\\$st"; curl -fsS -m 20 -H "Authorization: Bearer {tok}" "{install_url}" | FEELESS_LM_PORT=$PORT FEELESS_LM_CTX=$CTX FEELESS_NO_RELOAD=1 bash >/dev/null 2>&1; fi
FEELESS_KEEP_EOF
chmod +x "$HOME/.feeless/lan-keep.sh"
plist() {{ cat > "$HOME/Library/LaunchAgents/$1.plist" <<FEELESS_PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>Label</key><string>$1</string><key>ProgramArguments</key><array>$2</array>$3<key>RunAtLoad</key><true/></dict></plist>
FEELESS_PLIST_EOF
}}
plist com.feeless.awake "<string>/usr/bin/caffeinate</string><string>-dimsu</string>" "<key>KeepAlive</key><true/>"
plist com.feeless.lankeep "<string>/bin/bash</string><string>$HOME/.feeless/lan-keep.sh</string>" "<key>StartInterval</key><integer>60</integer>"
if [ -z "$FEELESS_NO_RELOAD" ]; then   # the hourly self-update re-writes the files only: the agents pick up the new script on their next run
  for a in com.feeless.awake com.feeless.lankeep; do launchctl bootout "gui/$(id -u)/$a" 2>/dev/null || true; launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/$a.plist" 2>/dev/null || true; done
fi
echo "✅ FEELESS loaded into LM Studio: preset 'FEELESS FEE Master' + MCP 'feeless' ({url})"
echo "🖥 Keep-alive on: this Mac stays awake while logged in, LM Studio's server (port $PORT) + $MODEL are checked every minute, updates pull hourly."
echo "   Also set: System Settings › Energy › 'Prevent automatic sleeping' + 'Wake for network access' ON; LM Studio › Developer › 'Serve on local network' ON."
echo "   In LM Studio: right panel › Preset › FEELESS FEE Master · Program › turn the 'feeless' MCP on · load the model with context 8192+."
"""


def serve_http(host, port):
    import hmac
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    tok = token()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj=None, extra=None):
            body = b'' if obj is None else json.dumps(obj).encode()
            self.send_response(code)
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            if obj is not None:
                self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _gate(self):
            if not client_ok(self.client_address[0]):
                self._send(403, {'error': 'LAN only'})
                return False
            got = self.headers.get('Authorization', '')
            if not hmac.compare_digest(got.encode(), f'Bearer {tok}'.encode()):
                self._send(401, {'error': 'missing or wrong Bearer token'})
                return False
            return True

        def do_GET(self):
            if self.path.rstrip('/') == '/health':
                return self._send(200, {'ok': True, 'name': NAME, 'tools': len(TOOLS)})
            if not self._gate():
                return
            if self.path.split('?')[0].rstrip('/') == '/lan-install':   # 🖥 the desktop Mac's one-paste installer (same LAN + token gate as the tools)
                host_ = re.sub(r'[^A-Za-z0-9.:\-\[\]]', '', self.headers.get('Host') or f'127.0.0.1:{port}')
                body = install_script(f'http://{host_}/mcp', tok).encode()
                _log(f"lan-install pulled by {self.client_address[0]}")   # 🖥 proof the desktop's hourly update ran
                self.send_response(200); self.send_header('Content-Type', 'text/x-shellscript; charset=utf-8'); self.send_header('Content-Length', str(len(body))); self.end_headers()
                return self.wfile.write(body)
            self._send(405, {'error': 'POST JSON-RPC to /mcp'}, {'Allow': 'POST'})

        def do_DELETE(self):
            if self._gate():
                self._send(204)

        def do_POST(self):
            if not self._gate():
                return
            if self.path.split('?')[0].rstrip('/') not in ('/mcp', ''):
                return self._send(404, {'error': 'POST to /mcp'})
            n = int(self.headers.get('Content-Length') or 0)
            if n > 1_000_000:
                return self._send(413, {'error': 'too big'})
            try:
                msg = json.loads(self.rfile.read(n) or b'null')
            except ValueError:
                return self._send(400, {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'parse error'}})
            sid = self.headers.get('Mcp-Session-Id') or secrets.token_hex(8)
            if isinstance(msg, list):
                res = [r for r in (handle(m) for m in msg) if r is not None]
                return self._send(200, res, {'Mcp-Session-Id': sid}) if res else self._send(202)
            res = handle(msg)
            if res is None:
                return self._send(202)
            self._send(200, res, {'Mcp-Session-Id': sid})

    srv = ThreadingHTTPServer((host, port), H)
    _log(f'FEELESS MCP on http://{host}:{port}/mcp · {len(TOOLS)} read-only tools · Bearer token required · LAN clients only')
    srv.serve_forever()


def serve_stdio():
    _log(f'FEELESS MCP (stdio) · {len(TOOLS)} read-only tools')
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            res = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'parse error'}}
        else:
            res = [r for r in (handle(m) for m in msg) if r] if isinstance(msg, list) else handle(msg)
        if res:
            sys.stdout.write(json.dumps(res) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    if '--http' in sys.argv:
        host = os.environ.get('FEELESS_MCP_HOST', '0.0.0.0')
        port = int(os.environ.get('FEELESS_MCP_PORT', '8765'))
        serve_http(host, port)
    else:
        serve_stdio()
