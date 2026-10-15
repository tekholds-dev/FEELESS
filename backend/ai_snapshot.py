"""📸 THE CHART SNAPSHOT THE MODELS READ (owner, 2026-10-15: "show snapshot of chart and analysis to help Reaper and other agents' confidence").
Pure + tested (`tests/test_ai_snapshot.py`).

The SAME 1-minute rows the agents read (`_office_bars`: candles service bars, or Tally's close-only tape) turned into ONE short line a text
model can read, plus the points the page draws beside the model's answer — so the owner sees exactly the picture the model judged.

  line  "1m candles, % vs entry: closes +0.0 +1.2 … · range high +8.1 / low −2.3 · last 5 min vol $1,840 vs $620 before · 3 green of last 5"
  pts   the closes as % (≤ PTS numbers, one decimal) — the page's sparkline

Never invents a bar: a close-only tape says so ("tape, closes only — no highs / lows / volume"); no rows = None."""
from __future__ import annotations

PTS = 24


def _f(v, d=None):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def snapshot(bars, entry=None, n=PTS):
    """`bars` = {src, rows: [[t, o, h, l, c, v|None]]} → {line, pts, src, base} | None. `entry` (a held coin's entry price) is the 0% line,
    else the first close shown."""
    rows = [r for r in ((bars or {}).get('rows') or []) if isinstance(r, (list, tuple)) and len(r) >= 5 and (_f(r[4]) or 0) > 0][-n:]
    if len(rows) < 3:
        return None
    tape = (bars or {}).get('src') != 'candles'
    base = _f(entry) if (_f(entry) or 0) > 0 else _f(rows[0][4])
    pc = lambda x: round((x / base - 1) * 100, 1)
    pts = [pc(_f(r[4])) for r in rows]
    parts = [f"1m {'tape (closes only)' if tape else 'candles'}, % vs {'entry' if (_f(entry) or 0) > 0 else 'the first close shown'}: closes " + ' '.join(f"{p:+.1f}" for p in pts)]
    if not tape:
        hi = max(_f(r[2], _f(r[4])) for r in rows)
        lo = min(_f(r[3], _f(r[4])) for r in rows)
        parts.append(f"range high {pc(hi):+.1f} / low {pc(lo):+.1f}")
        vols = [_f(r[5]) if len(r) > 5 else None for r in rows]
        last, before = [v for v in vols[-5:] if v], [v for v in vols[:-5] if v]
        if last and before:
            parts.append(f"last 5 min vol ${sum(last):,.0f} vs ${sum(before) / max(1, len(before)) * 5:,.0f} per 5 min before")
        greens = sum(1 for r in rows[-5:] if _f(r[4]) >= _f(r[1], _f(r[4])))
        parts.append(f"{greens} green of the last 5")
        lows = [_f(r[3], _f(r[4])) for r in rows]
        hl = sum(1 for a, b in zip(lows[-6:-1], lows[-5:]) if b > a)
        parts.append(f"{hl} of the last 5 lows were higher lows")
    else:
        parts.append('no highs / lows / volume on a tape')
    return {'line': ' · '.join(parts), 'pts': pts, 'src': 'tape' if tape else 'candles', 'base': base}
