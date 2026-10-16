"""🦠 Germ EXITS replayed on the recorded 1-minute candles (read-only): flat stop vs a stop just under the germ, and a moon bag that rides
on the germ instead of the peak. Entries = the agents' germ entry (≤ MAX% above the 1m germ, 5 closes holding it, 5m not falling > 3%).
Run: backend/.venv/bin/python scripts/germ-exits.py [max_pct]"""
import json, sys, os, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'backend'))
import chart_intel as ci
MAX = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
COST, H = 3.0, 120
d = json.load(open(os.path.join(ROOT, 'backend', 'data', 'candle_ticks.json')))
def bars(ticks):
    ticks = sorted((t['t'], t['p']) for t in ticks if t.get('p'))
    if len(ticks) < 120: return []
    out, cur, b = [], None, None
    for t, p in ticks:
        m = int(t // 60) * 60
        if cur is None: cur, b = m, [m, p, p, p, p, 0]
        while m > cur:
            out.append(b); cur += 60; pc = b[4]; b = [cur, pc, pc, pc, pc, 0]
        b[2] = max(b[2], p); b[3] = min(b[3], p); b[4] = p
    out.append(b); return out

def run(path, px, stop_px, moon, hist):
    """path = bars after entry. Scale 75% at +10 (stop first if both in a bar), rest: trail arm +10 give back 30% of the peak gain,
    or (moon) exit when a 1m close falls under the rolling germ. Stop fills at the stop or the bar's open when it gapped through."""
    sold, got, peak, scaled = 0.0, 0.0, 0.0, False
    for k, b in enumerate(path):
        lo, hi, cl, op = (b[3] / px - 1) * 100, (b[2] / px - 1) * 100, (b[4] / px - 1) * 100, (b[1] / px - 1) * 100
        sp = (stop_px / px - 1) * 100
        if lo <= sp and not scaled:
            return min(sp, op)
        if not scaled and hi >= 10:
            scaled, got, sold = True, 0.75 * 10, 0.75
        peak = max(peak, hi)
        if scaled:
            if moon:
                g = ci.germ((hist + path[:k + 1])[-60:])
                floor = (g['px'] / px - 1) * 100 if g and not g['lost'] else 0.0
                if cl < max(floor, 0.0):
                    return got + (1 - sold) * max(cl, floor)
            elif peak >= 10 and cl <= peak * 0.7:
                return got + (1 - sold) * cl
    return got + (1 - sold) * cl if path else 0

R = {k: [] for k in ('flat20', 'germstop', 'moon', 'germstop+moon')}
for key, ticks in d.items():
    bs = bars(ticks)
    if len(bs) < 200: continue
    last = -99
    for i in range(90, len(bs) - H):
        if i - last < 15: continue
        w = bs[i - 60:i + 1]; px = w[-1][4]
        g = ci.germ(w)
        if not g or g['lost'] or not (0 <= g['dist'] <= MAX): continue
        five = w[-6:]
        if not all(r[4] >= g['px'] for r in five) or (five[-1][4] / five[0][4] - 1) * 100 < -3: continue
        last = i
        path = bs[i + 1:i + 1 + H]
        gs = min(max(g['px'] * 0.97, px * (1 - 0.35)), px * (1 - 0.08))   # germ − 3%, never wider than 35% or tighter than 8%
        t = bs[i][0]
        R['flat20'].append((t, run(path, px, px * 0.8, False, w) - COST))
        R['germstop'].append((t, run(path, px, gs, False, w) - COST))
        R['moon'].append((t, run(path, px, px * 0.8, True, w) - COST))
        R['germstop+moon'].append((t, run(path, px, gs, True, w) - COST))
for k, v in R.items():
    v = [x for _, x in sorted(v)]
    n = len(v); a, b = v[:n // 2], v[n // 2:]
    print(f"{k:14} n{n:4} avg {st.mean(v):+6.2f}% med {st.median(v):+6.2f}% won {sum(x > 0 for x in v) * 100 // n}% · older half avg {st.mean(a):+.2f} · newer half {st.mean(b):+.2f}")
