"""🏘 TOWN SIGNS — every building a family stands in its town (block_markets.TOWN) carries its tool's OWN live number on its sign (owner,
2026-10-23: "buildings represent realtime data"): Trench Towers = READY coins on the intake · Perps = the busiest market's mark, move and
funding · Pool Hall = the best sane APY · Trade Center = the real card's open seats and record · Night Vault = the best overnight strategy ·
Pump Radar = the hottest Pump coin · FeeCat = Fee's stack and lives · Rep market = live calls. Pure: the service feeds each tool's cached read
(GET /api/reputation/familia-town/live, one shared read every 45 s); a missing source leaves that sign on its plain subtitle."""

POOL_MIN_TVL = 1_000_000   # the Pool Hall's sign only quotes pools with real depth…
POOL_MAX_APY = 300         # …and an APY that is not a farm's launch-day number


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def usd(v):
    v = _f(v)
    if not v:
        return '$0'
    a = abs(v)
    return f"${v / 1e9:.1f}B" if a >= 1e9 else f"${v / 1e6:.1f}M" if a >= 1e6 else f"${v / 1e3:.1f}K" if a >= 1e3 else f"${v:,.0f}" if a >= 100 else f"${v:.2f}"


def pct(v, d=1):
    v = _f(v)
    return '—' if v is None else f"{v:+.{d}f}%"


def price(v):
    v = _f(v) or 0
    return f"${v:,.0f}" if v >= 1000 else f"${v:,.2f}" if v >= 1 else f"${v:.4g}"


def tt(intake):
    rows = (intake or {}).get('coins') or []
    if not rows:
        return None
    ready = sum(1 for r in rows if str(r.get('status') or '').upper() == 'READY')
    return {'line': f"{ready} READY · {len(rows)} on the intake", 'v': ready, 'tone': 'hot' if ready else 'calm'}


def perps(p):
    rows = [r for r in (p or {}).get('markets') or [] if _f(r.get('mark'))]
    if not rows:
        return None
    r = max(rows, key=lambda x: _f(x.get('oiUsd')) or 0)
    ch = _f(r.get('ch24'))
    return {'line': f"{r.get('coin')} {price(r.get('mark'))} · {pct(ch)} · f {pct(r.get('fundApr'), 0)}", 'v': ch, 'tone': 'up' if (ch or 0) >= 0 else 'down'}


def pools(hub):
    rows = [r for r in (hub or {}).get('pools') or [] if (_f(r.get('tvl')) or 0) >= POOL_MIN_TVL and 0 < (_f(r.get('apy')) or 0) <= POOL_MAX_APY]
    if not rows:
        return None
    r = max(rows, key=lambda x: _f(x.get('apy')))
    return {'line': f"TOP {_f(r['apy']):.0f}% APY · {r.get('sym') or r.get('proto')}", 'v': _f(r['apy']), 'tone': 'up'}


def trades(tc):
    if not tc:
        return None
    cl = tc.get('closed') or {}
    won = round(sum(b.get('wonPct', 0) * b.get('n', 0) for b in (cl.get('by') or {}).values()) / max(1, sum(b.get('n', 0) for b in (cl.get('by') or {}).values())))
    avg = _f(tc.get('avgPct'))
    head = f"{tc.get('open', 0)} open {pct(avg)}" if tc.get('open') else 'desk flat'
    return {'line': f"{head} · {cl.get('n', 0)} closed, {won}% won" if cl.get('n') else head, 'v': avg,
            'tone': 'calm' if not tc.get('open') else 'up' if (avg or 0) >= 0 else 'down'}


def vault(sleep):
    rows = [s for s in (sleep or {}).get('strategies') or [] if _f(s.get('apy'))]
    if not rows:
        return None
    s = max(rows, key=lambda x: _f(x.get('apy')))
    return {'line': f"BEST {_f(s['apy']):.1f}% · {s.get('name')}", 'v': _f(s['apy']), 'tone': 'up'}


def radar(board):
    rows = [r for r in board or [] if str(r.get('mint') or '').endswith('pump') and r.get('safe') is not False and _f(r.get('chg5m')) is not None]
    if not rows:
        return None
    r = max(rows, key=lambda x: _f(x.get('chg5m')))
    ch = _f(r['chg5m'])
    return {'line': f"🔥 ${r.get('symbol') or '?'} {pct(ch, 0)} 5m · {len(rows)} live", 'v': ch, 'tone': 'hot' if ch > 0 else 'down'}


def cats(prof):
    cat = (prof or {}).get('cat') or {}
    bal = _f(cat.get('balanceSol'))
    if bal is None:
        return None
    lives = ((prof or {}).get('discipline') or {}).get('lives')
    start = _f(cat.get('startingBalanceSol')) or bal
    roi = (bal / start - 1) * 100 if start else 0
    held = len(cat.get('positions') or [])
    return {'line': f"FEE {bal:.1f} SOL {pct(roi)}" + (f" · {lives}/9 lives" if lives is not None else '') + (f" · {held} held" if held else ''), 'v': roi,
            'tone': 'up' if roi >= 0 else 'down'}


def rep(rm):
    live = (rm or {}).get('live') or []
    if rm is None:
        return None
    if not live:
        return {'line': 'no live calls · next round soon', 'v': 0, 'tone': 'calm'}
    big = max(live, key=lambda m: abs(_f(m.get('move')) or 0))   # the live call moving most right now
    return {'line': f"{len(live)} live · {big.get('icon') or '🎲'} ${big.get('sym') or '?'} {pct(big.get('move'))}", 'v': len(live), 'tone': 'hot'}


READERS = {'tt': tt, 'perps': perps, 'pools': pools, 'trades': trades, 'vault': vault, 'radar': radar, 'cats': cats, 'rep': rep}


def signs(src):
    """{tool key: its source read (or None / an Exception)} → {tool key: {line, v, tone}} for the sources that read cleanly."""
    out = {}
    for k, fn in READERS.items():
        d = (src or {}).get(k)
        if d is None or isinstance(d, BaseException):
            continue
        try:
            s = fn(d)
        except Exception:
            s = None
        if s:
            out[k] = {**s, 'line': str(s['line'])[:48]}
    return out
