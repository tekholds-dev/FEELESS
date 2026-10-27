"""🏁 THE RACEWAY (owner 2026-10-27: "family be a telegram game where people can drive vehicles / race this city"). Pure + tested; the service holds
the clock, the tokens and the store.

· The race city is the Familia grid drawn as streets: RACE_GRID × RACE_GRID blocks, a road every RACE_CELL metres (the browser builds the very same
  grid from the world's blocks — the families' buildings line the streets). Checkpoints sit on road crossings, so every one is reachable.
· The SERVER deals the track (today's daily race, or a delivery errand from the family's home) and checks every finish: no time faster than the
  straight line between the checkpoints at the fastest vehicle's top speed, checkpoint splits in order, and the real clock between start and
  finish must agree with the time the browser reports. Nothing here moves money — MP only, into the family bank like every errand.
"""
import hashlib
import math
import random

RACE_GRID = 8
RACE_CELL = 38.0
RACE_TOP = 52.0          # m/s — the fastest vehicle (the bike); the straight line at this speed is the floor of any honest time
RACE_CPS = 6
PAR_SPEED = 21.0         # m/s along the checkpoint path — beat par for the bonus
RACE_MP, RACE_PAR_MP = 120, 280          # the day's first finish · under par (once a day each)
ERRAND_BONUS = 1.25                      # a driven delivery under par pays the errand ×1.25
VEHICLES = ('car', 'bike', 'truck')
CLOCK_SLACK = 0.85       # the real clock may run a little short of the reported time (network) — never by more than 15 % + 2 s


def _h(s):
    return int(hashlib.sha256(str(s).encode()).hexdigest()[:12], 16)


def crossing(i, j):
    return [round(i * RACE_CELL, 1), round(j * RACE_CELL, 1)]


def _path_len(start, cps):
    pts = [start[:2]] + cps
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def _track(rng, start_ij, n):
    """n distinct crossings, each a few blocks from the last (never the same street twice in a row)."""
    cps, (ci, cj), seen = [], start_ij, {start_ij}
    while len(cps) < n:
        i, j = rng.randrange(RACE_GRID + 1), rng.randrange(RACE_GRID + 1)
        d = abs(i - ci) + abs(j - cj)
        if (i, j) in seen or d < 3 or d > 7:
            continue
        seen.add((i, j)); cps.append(crossing(i, j)); ci, cj = i, j
    return cps


def _pack(start, cps, kind, store=''):
    length = _path_len(start, cps)
    return {'kind': kind, 'store': store, 'start': start, 'cps': cps, 'len': round(length, 1),
            'par': int(length / PAR_SPEED * 1000), 'min': int(length / RACE_TOP * 1000), 'grid': RACE_GRID, 'cell': RACE_CELL}


def daily_track(day):
    """Today's race (the same for everyone on a UTC day): from the south-west corner through RACE_CPS crossings."""
    rng = random.Random(_h(f'race:{day}'))
    return _pack([0.0, 0.0, 0.0], _track(rng, (0, 0), RACE_CPS), 'race')


def errand_track(store, home_id, now):
    """A delivery: from the family's home crossing → the pickup → the drop (a new route every 10 minutes)."""
    h = _h(f'home:{home_id}')
    hi, hj = h % (RACE_GRID + 1), (h // 7) % (RACE_GRID + 1)
    rng = random.Random(_h(f'errand:{store}:{home_id}:{int(now // 600)}'))
    return _pack([*crossing(hi, hj), 0.0], _track(rng, (hi, hj), 2), 'errand', store)


def check(track, ms, splits, elapsed):
    """→ None when the finish is honest, else why not. `splits` = ms at each checkpoint, `elapsed` = the server's own seconds since start."""
    try:
        ms = int(ms); splits = [int(x) for x in (splits or [])]
    except (TypeError, ValueError):
        return 'Bad time.'
    if len(splits) != len(track['cps']):
        return 'Every checkpoint, in order.'
    if any(b <= a for a, b in zip([0] + splits, splits)) or splits[-1] > ms + 50:
        return 'Checkpoint times out of order.'
    if ms < track['min']:
        return 'Faster than the straight line at top speed — not a real run.'
    if elapsed < ms / 1000 * CLOCK_SLACK - 2:
        return 'The clock says that run was shorter than its time.'
    if ms > 15 * 60 * 1000:
        return 'Too slow — the run timed out.'
    return None


def race_mp(ms, track, paid):
    """MP for a daily-race finish: the first finish of the day + an under-par bonus, each once a day. `paid` = what today already paid."""
    mp, got = 0, set(paid or [])
    if 'finish' not in got:
        mp += RACE_MP; got.add('finish')
    if ms <= track['par'] and 'par' not in got:
        mp += RACE_PAR_MP; got.add('par')
    return mp, sorted(got)


def board(day_rows, n=10):
    """The day's board: each driver's best, fastest first."""
    rows = sorted(day_rows.values(), key=lambda r: r['ms'])[:n]
    return [{**r, 'place': i + 1} for i, r in enumerate(rows)]


def record(day_rows, who, ms, vehicle, name, tag):
    """Keep a driver's best of the day → True when it's a new best."""
    cur = day_rows.get(who)
    if cur and cur['ms'] <= ms:
        return False
    day_rows[who] = {'who': who[:4] + '…' + who[-4:] if len(who) > 12 else who, 'ms': int(ms), 'vehicle': vehicle if vehicle in VEHICLES else 'car',
                     'name': str(name or '')[:24], 'tag': str(tag or '')[:6]}
    return True


# 📲 the Telegram group's automated posts (the service sends them when TELEGRAM_BOT_TOKEN + TELEGRAM_GROUP_ID are set)
def _fmt(ms):
    ms = max(0, int(ms)); return f"{ms // 60000}:{(ms % 60000) / 1000:05.2f}"


def _name(r):
    return f"[{r['tag']}] {r['name']}" if r.get('tag') else (r.get('name') or r.get('who') or 'a racer')


VEH_WORD = {'car': 'MUSCLE CAR', 'bike': 'STREET BIKE', 'truck': 'BOX TRUCK'}


def record_post(row, prev=None):
    """A new #1 of the day → the group's post."""
    beat = f" — beat {_name(prev)} by {(prev['ms'] - row['ms']) / 1000:.2f}s" if prev and prev.get('ms', 0) > row['ms'] else ''
    return f"🏁 NEW #1 IN FEE CITY\n{_name(row)} · {_fmt(row['ms'])} on a {VEH_WORD.get(row.get('vehicle'), 'MUSCLE CAR')}{beat}\nThink you're faster? Today's track is open."


def recap_post(day, rows):
    """Yesterday's podium → the group's morning post (None when nobody raced)."""
    top = board(rows or {}, 3)
    if not top:
        return None
    medal = ['🥇', '🥈', '🥉']
    lines = [f"{medal[i]} {_name(r)} · {_fmt(r['ms'])} · {VEH_WORD.get(r.get('vehicle'), 'MUSCLE CAR')}" for i, r in enumerate(top)]
    return f"🏆 FEE CITY RACE · {day}\n" + '\n'.join(lines) + f"\n{len(rows)} driver{'s' if len(rows) != 1 else ''} raced. A new track is live — first finish pays {RACE_MP} MP, under par {RACE_PAR_MP} more."
