"""🧠☠ THE MODEL'S EXIT READ (owner, 2026-10-14: "agents usually take ~+8% — AI should help Trigger and Reaper make smarter, cleaner exits").
Pure + tested (`tests/test_exit_read.py`).

The model reads each coin the agents HOLD (its P/L, peak, hold time, tape, chart) about once a minute and answers in one word:
  RIDE     the run is still being bought — let it work
  TIGHTEN  it is fading / distributing — protect what is up
  —        nothing to say
Reaper NEVER waits on it: it reads the last cached answer (≤ FRESH_SEC old). Every read is noted at the coin's price and graded 15 min
later on what the coin really did (RIDE right = it rose · TIGHTEN right = it fell). A word moves Reaper ONLY once its own graded record
proves it (≥ MIN_N reads, the typical move ≥ EDGE_PCT the right way), and then only inside fixed bounds:
  proven RIDE    on a green seat whose tape is not seller-led → the wide ride trail (office.RIDE_GIVE, same as a hot crowd buying)
  proven TIGHTEN on a green seat → the trail banks sooner (×0.6, like a reversing P/L)
It never opens a position, never sizes, never sells by itself, never moves a stop or the catastrophic line.
Real record behind it (2026-10-14, 143 real exits since the 3-second guard): 69% won, average win +8.3%; 34 of 109 losers had been up ≥ +5%
(median peak +14%) — a read that tells a fading run from a live one is worth exactly that gap, IF its record says so."""
import statistics

JUDGE_SEC = 900.0      # a read is graded 15 min after it was made
FRESH_SEC = 180.0      # Reaper uses a read for 3 min
RENOTE_SEC = 300.0     # the same word on the same coin is one graded read per 5 min
MIN_N = 20             # a word does nothing until this many of its reads are graded
EDGE_PCT = 2.0         # … and their typical 15-min move is at least this far the right way
GONE_SEC = 3600.0      # no price for an hour after the read = the coin is gone: −100% (a TIGHTEN was right)
KEEP = 400
CALLS = ('RIDE', 'TIGHTEN')
TIGHT = 0.6            # a proven TIGHTEN: the trail gives back 60% of what it would (the same factor as a reversing P/L)
ASK = ("This coin is HELD by the desk (`pct` now, `peak` = best % since entry, `heldMin`). Read the tape, flow and chart: is this run still "
       "being bought, or is it fading / distributing? Put HOLD in `call` when buyers still carry it, PROTECT or EXIT when it is fading "
       "(confidence_delta −0.25 = clearly fading). Never advise buying more. summary = the one sign you read.")


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def word_of(advice):
    """The model's answer → RIDE · TIGHTEN · None. PROTECT / EXIT or a strong negative delta = TIGHTEN; HOLD with no named risk = RIDE."""
    a = advice if isinstance(advice, dict) else {}
    call = str(a.get('call') or '').upper()
    d = _f(a.get('confidence_delta'), 0.0)
    if call in ('PROTECT', 'EXIT') or d <= -0.12:
        return 'TIGHTEN'
    if call in ('HOLD', 'SUPPORT_ENTRY') and d >= 0 and not (a.get('risk_flags') or []):
        return 'RIDE'
    return None


def note(book, mint, word, px, pct, now, symbol=None):
    """One graded read (skipped: no word / no price / the same word on this coin < RENOTE_SEC ago)."""
    b = dict(book or {})
    if word not in CALLS or not mint or _f(px) <= 0:
        return b
    op = list(b.get('open') or [])
    if any(o.get('mint') == mint and o.get('word') == word and now - _f(o.get('at')) < RENOTE_SEC for o in op):
        return b
    op.append({'mint': mint, 'sym': symbol, 'word': word, 'px': _f(px), 'pct': round(_f(pct), 2), 'at': now})
    b['open'] = op[-KEEP:]
    return b


def settle(book, prices, now):
    """Reads ≥ JUDGE_SEC old get their 15-min move; no price for GONE_SEC = −100%; otherwise they wait."""
    b = dict(book or {})
    keep, done = [], list(b.get('done') or [])
    for o in b.get('open') or []:
        if now - _f(o.get('at')) < JUDGE_SEC:
            keep.append(o)
            continue
        p = _f((prices or {}).get(o.get('mint')))
        if p > 0:
            done.append({**o, 'move': round((p / _f(o['px']) - 1) * 100, 2), 'doneAt': now})
        elif now - _f(o.get('at')) >= GONE_SEC:
            done.append({**o, 'move': -100.0, 'doneAt': now, 'gone': True})
        else:
            keep.append(o)
    b['open'], b['done'] = keep[-KEEP:], done[-KEEP:]
    return b


def record(book):
    """{word: {n, med, right (% graded the right way), proven}}."""
    out = {}
    for w in CALLS:
        mv = [_f(d.get('move')) for d in (book or {}).get('done') or [] if d.get('word') == w]
        if not mv:
            out[w] = {'n': 0, 'med': None, 'right': None, 'proven': False}
            continue
        med = statistics.median(mv)
        right = sum(1 for m in mv if (m > 0 if w == 'RIDE' else m < 0)) / len(mv) * 100
        ok = len(mv) >= MIN_N and (med >= EDGE_PCT if w == 'RIDE' else med <= -EDGE_PCT)
        out[w] = {'n': len(mv), 'med': round(med, 1), 'right': round(right), 'proven': ok}
    return out


def effects(reads, rec, now, on=True):
    """{mint: 'ride' | 'tight'} for Reaper — fresh reads of a PROVEN word only. `reads` {mint: {word, at}}."""
    if not on:
        return {}
    out = {}
    for m, r in (reads or {}).items():
        w = (r or {}).get('word')
        if w in CALLS and now - _f(r.get('at')) <= FRESH_SEC and ((rec or {}).get(w) or {}).get('proven'):
            out[m] = 'ride' if w == 'RIDE' else 'tight'
    return out


def view(book, reads, now, on=True):
    """The page's compact block: per word n · median · proven (the sentence is built on the page), and the 4 newest reads."""
    rec = record(book)
    return {'rec': {w: [rec[w]['n'], rec[w]['med'], int(rec[w]['proven'])] for w in CALLS}, 'min': MIN_N, 'on': int(bool(on)),
            'reads': [[r.get('sym'), r.get('word'), round(now - _f(r.get('at')))]
                      for _m, r in sorted((reads or {}).items(), key=lambda kv: -_f(kv[1].get('at')))[:3]]}   # the payload is capped at 100 KB
