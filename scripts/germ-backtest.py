"""🦠 Germ vs gun-line entries, replayed on the recorded 1-minute candles (read-only). See CLAUDE.md › BUY AT THE GERM."""
import json, sys, statistics as st
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # run: backend/.venv/bin/python scripts/germ-backtest.py
sys.path.insert(0, os.path.join(ROOT, 'backend'))
import chart_intel as ci
d = json.load(open(os.path.join(ROOT, 'backend', 'data', 'candle_ticks.json')))
COST = 3.0
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
def swing_highs(rs, k=3):
    return [rs[i][2] for i in range(k, len(rs) - k) if rs[i][2] == max(r[2] for r in rs[i - k:i + k + 1])]
res = {'germ': [], 'gun': [], 'all': []}
X = {'germ': [], 'gun': []}
pools = 0
for key, ticks in d.items():
    bs = bars(ticks)
    if len(bs) < 200: continue
    pools += 1
    last = {}
    for i in range(90, len(bs) - 30):
        w = bs[i - 60:i + 1]; px = w[-1][4]
        f15, f30 = (bs[i + 15][4] / px - 1) * 100, (bs[i + 30][4] / px - 1) * 100
        mfe = (max(r[2] for r in bs[i + 1:i + 31]) / px - 1) * 100; mae = (min(r[3] for r in bs[i + 1:i + 31]) / px - 1) * 100
        if i % 15 == 0: res['all'].append(f30 - COST)
        g = ci.germ(w)
        sh = swing_highs(w[:-1])
        over = [h for h in sh if h > w[-2][4]]
        gun = min(over) if over else None
        # GERM entry: within 8% above the germ low, not lost, 5 one-minute closes above it (1m) and the 5-minute bar not falling > 3% (5m confirm)
        five = w[-6:]
        m5 = (five[-1][4] / five[0][4] - 1) * 100
        if g and not g['lost'] and 0 <= g['dist'] <= 8 and all(r[4] >= g['px'] for r in five) and m5 >= -3 and i - last.get('g', -99) >= 15:
            res['germ'].append(f30 - COST); X['germ'].append((mfe, mae)); last['g'] = i
        # GUN entry: this bar closed above the nearest swing high overhead (the breakout the bots buy today)
        if gun and w[-2][4] <= gun < px and i - last.get('u', -99) >= 15:
            res['gun'].append(f30 - COST); X['gun'].append((mfe, mae)); last['u'] = i
print('pools', pools)
for k, v in res.items():
    if v:
        v2 = sorted(v); n = len(v)
        h = n // 2
        a, b = v2, None
        print(f"{k:5} n{n:5} avg{st.mean(v):+6.2f}% med{st.median(v):+6.2f}% won{sum(1 for x in v if x > 0) * 100 // n}%  (30 min, after a 3% round trip)  first half avg {st.mean(v[:n//2]):+.2f} · second half {st.mean(v[n//2:]):+.2f}")

for k, v in X.items():
    n = len(v)
    print(f"{k:5} reached +10%: {sum(1 for a, b in v if a >= 10) * 100 // n}% · +20%: {sum(1 for a, b in v if a >= 20) * 100 // n}% · fell -15% first-ish (MAE ≤ -15): {sum(1 for a, b in v if b <= -15) * 100 // n}% · typical peak {st.median(a for a, b in v):+.1f}% · typical worst {st.median(b for a, b in v):+.1f}%")
