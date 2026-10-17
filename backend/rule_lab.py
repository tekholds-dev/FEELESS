"""🧪 THE RULE LAB — the model PROPOSES, the real-money record DECIDES (owner, 2026-10-13: "do all — the model proposes rules, the record tests
them … let it name new causes … trigger needs more lessons from AI on trench entry buying, all agents need lessons"). Pure + tested
(`tests/test_rule_lab.py`).

A rule = {act: avoid | favor, when: [1–2 entry tokens], name, why, desk}. Tokens are the SAME entry features the real-money memory files
every closed agent trade by (`real_memory.pos_feats`: chart structure · the chart's entry rule · door / tier · launch phase · launch class ·
age band) + the buy / sell vital at the entry (`flow:BUYERS|SELLERS|PEAK|BALANCED|THIN`) + how far under its recent high it was bought
(`high:top|near|off`). The model may only use tokens that exist in our own record (`vocab`), so a rule can always be tested.

How a rule goes LIVE (one of two doors, both on REAL fills only):
  1 · WALK-FORWARD: the oldest 60% of trades and the newest 40% are judged apart; in BOTH the coins the rule matches must do ≥ EDGE points
      worse (avoid) / better (favor) than the coins it does not, with ≥ MIN_LEARN / MIN_TEST matched trades. The newest 40% are trades the
      proposal was never fitted to (the model sees bucket counts, not which half they sit in).
  2 · NEW CAUSE (avoid only): the rule matched ≥ CAUSE_LOSSES of the last LOSS_WINDOW real LOSSES and the replay does not contradict it
      (matched coins did not do better). It joins the desk's vocabulary under the model's own name.
A live rule is a LESSON for the desk it names: avoid = ×AVOID_F on the rank (Judge's evidence weight) and, when its tokens are about the
entry MOMENT (flow / high / entry rule / chart structure), Trigger arms instead of entering; favor = ×FAVOR_F on the rank. Never an order,
a size, a sell or a blocked seat. A live rule is re-judged on every new trade: it drops back the moment the record stops backing it, and
a proposal that waits RETIRE_SEC without passing is retired. Nothing here is a promise — 755 hand-made rules found no edge on 2026-10-13.
"""
import real_memory as _rm

ACTS = ('avoid', 'favor')
DESKS = ('trigger', 'sherlock', 'devil', 'warden', 'reaper')
SPLIT = 0.6
MIN_LEARN, MIN_TEST = 6, 5
EDGE = 3.0
CAUSE_LOSSES, LOSS_WINDOW = 3, 20
AVOID_F, FAVOR_F = 0.88, 1.06
CLAMP = (0.8, 1.1)
RETIRE_SEC = 24 * 3600
KEEP = 40
MAX_WHEN = 2
MOMENT = ('flow:', 'high:', 'rule:', 'struct:', 'fresh:')   # (fresh: buying a coin minutes old IS a timing call)   # entry-MOMENT tokens: a live avoid rule on these is Trigger's lesson (arm, don't enter)


from fnum import nan_safe as _f


def high_band(dist):
    """% under its recent high at the buy → top (< 2%) · near (2–8%) · off (≥ 8%). None = not read."""
    if dist is None:
        return None
    d = _f(dist)
    return 'top' if d < 2 else 'near' if d < 8 else 'off'


def fresh_band(age_h):
    """Age at the buy, finer than the memory's bands (the record's sharpest split: < 15 min −14.8% vs 15–60 min −1.4%, 2026-10-13)."""
    if age_h is None:
        return None
    a = _f(age_h)
    return '<15m' if a < 0.25 else '15-60m' if a < 1 else '1-3h' if a < 3 else '3h+'


def trade_feats(p):
    """A closed real trade's entry tokens (what the memory files it by + the tape + the high at entry, when the thesis kept them)."""
    th = (p or {}).get('thesis') or {}
    out = list(_rm.pos_feats(p or {}))
    fl = (th.get('flow') or {}).get('state') if isinstance(th.get('flow'), dict) else th.get('flow')
    if fl:
        out.append(f'flow:{fl}')
    hb = high_band(th.get('distHigh'))
    if hb:
        out.append(f'high:{hb}')
    if th.get('germ'):
        out.append(f"germ:{th['germ']}")   # 🦠 where the price sat vs its germ floor at the buy
    la, li = (p or {}).get('launch') or {}, (p or {}).get('li') or {}
    fb = fresh_band(la.get('ageH') if la.get('ageH') is not None else li.get('ageH'))
    if fb:
        out.append(f'fresh:{fb}')
    return out


def row_feats(x):
    """A LIVE desk row → the same tokens (chart state, the chart's entry rule, launch phase / class, age, the live tape, the high)."""
    x = x or {}
    ch, li, v = x.get('chart') or {}, x.get('li') or {}, x.get('vitals') or {}
    ent = ch.get('entry') or []
    out = list(_rm.feats(ch.get('state'), ent[1] if len(ent) > 1 else None, x.get('tag') or '', li.get('phase'), li.get('cls'), v.get('ageH')))
    out = [t for t in out if t != 'door:other']   # a live coin has no door yet
    fl = (x.get('fv') or {}).get('state')
    if fl:
        out.append(f'flow:{fl}')
    hb = high_band(x.get('distHigh') if x.get('distHigh') is not None else (ch.get('f') or {}).get('distHigh'))
    if hb:
        out.append(f'high:{hb}')
    if ch.get('germ'):
        out.append(f"germ:{ch['germ']}")
    fb = fresh_band(v.get('ageH'))
    if fb:
        out.append(f'fresh:{fb}')
    return out


AUTO_N, AUTO_GAP, AUTO_MAX = 10, 5.0, 2


def auto_propose(trades, state):
    """🧪 The lab does not wait for the model: every token our record holds on ≥ AUTO_N real trades whose typical result sits ≥ AUTO_GAP points
    from the whole record's is proposed as ONE rule (avoid under it, favor over it) — at most AUTO_MAX new a pass, never one on file. The
    walk-forward still decides; most of these fail, and that is the point (no lesson goes live on in-sample numbers)."""
    rows = _rm.trades(trades)
    if len(rows) < 2 * AUTO_N:
        return []
    allv = sorted(_rm._cap(p.get('realPct')) for p in rows)
    base = allv[len(allv) // 2]
    have = {r['id'] for r in (state or {}).get('rules') or []}
    out = []
    for t, x in sorted(vocab(trades).items(), key=lambda kv: -abs(kv[1]['med'] - base)):
        if x['n'] < AUTO_N or abs(x['med'] - base) < AUTO_GAP:
            continue
        act = 'avoid' if x['med'] < base else 'favor'
        rid = f'{act}:{t}'
        if rid in have:
            continue
        out.append({'id': rid, 'act': act, 'when': [t], 'name': f"{'🚫' if act == 'avoid' else '✅'} {t}"[:40], 'by': 'record',
                    'why': f"{t}: typical {x['med']:+.0f}% on {x['n']} real trades vs {base:+.0f}% overall", 'desk': desk_of([t])})
        if len(out) >= AUTO_MAX:
            break
    return out


def vocab(trades):
    """Every token our own record holds (≥ 3 trades) → {token: {n, med}} — the only words a proposal may use."""
    by = {}
    for p in trades or []:
        for t in set(trade_feats(p)):
            by.setdefault(t, []).append(_rm._cap(p.get('realPct')))
    return {t: {'n': len(v), 'med': round(sorted(v)[len(v) // 2], 1)} for t, v in by.items() if len(v) >= 3}


def desk_of(when):
    """Whose lesson a rule is: the entry moment → Trigger · the launch's crowd / class → Devil · the coin's age / door → Sherlock."""
    w = ' '.join(when or [])
    if any(k in w for k in MOMENT):
        return 'trigger'
    if 'cls:' in w or 'phase:' in w:
        return 'devil'
    return 'sherlock'


def clean(raw, vocab_):
    """The model's proposals → valid rules only: a known act, 1–2 tokens that exist in our record, a short name. Anything else is dropped."""
    out = []
    for r in raw or []:
        if not isinstance(r, dict):
            continue
        act = str(r.get('act') or '').strip().lower()
        raw_t = {str(t).strip() for t in (r.get('when') or []) if isinstance(t, str) and str(t).strip()}
        if act not in ACTS or not raw_t or len(raw_t) > MAX_WHEN or not raw_t <= set(vocab_ or {}):   # every word must exist in our record
            continue
        when = sorted(raw_t)
        name = ' '.join(str(r.get('name') or '').split())[:40] or ' & '.join(when)
        out.append({'id': f"{act}:{'&'.join(when)}", 'act': act, 'when': when, 'name': name, 'why': ' '.join(str(r.get('why') or '').split())[:120],
                    'desk': desk_of(when)})
    return out[:3]


def _half(rows, when):
    m = [_rm._cap(p.get('realPct')) for p in rows if set(when) <= set(trade_feats(p))]
    u = [_rm._cap(p.get('realPct')) for p in rows if not set(when) <= set(trade_feats(p))]
    avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
    return {'n': len(m), 'avg': avg(m), 'rest': avg(u), 'restN': len(u)}


def replay(rule, trades):
    """Walk-forward on REAL trades (oldest first): {learn, test, pass} — pass = the rule's side holds in BOTH halves by ≥ EDGE."""
    rows = _rm.trades(trades)
    k = int(len(rows) * SPLIT)
    lr, ts = _half(rows[:k], rule['when']), _half(rows[k:], rule['when'])
    sign = -1 if rule['act'] == 'avoid' else 1

    def ok(h, n_min):
        return h['n'] >= n_min and h['avg'] is not None and h['rest'] is not None and sign * (h['avg'] - h['rest']) >= EDGE
    return {'learn': lr, 'test': ts, 'pass': ok(lr, MIN_LEARN) and ok(ts, MIN_TEST),
            'against': ts['n'] >= MIN_TEST and ts['avg'] is not None and ts['rest'] is not None and sign * (ts['avg'] - ts['rest']) < 0}


def loss_hits(rule, trades):
    """How many of our last LOSS_WINDOW real LOSSES this rule describes (door 2: a new cause)."""
    losses = [p for p in _rm.trades(trades) if _f(p.get('realPct')) < 0][-LOSS_WINDOW:]
    return sum(1 for p in losses if set(rule['when']) <= set(trade_feats(p)))


def judge(rule, trades, now):
    """One rule against today's record → the rule with its status: live (walk-forward) · live as a cause · proposed · failed."""
    r = dict(rule)
    rp = replay(r, trades)
    hits = loss_hits(r, trades) if r['act'] == 'avoid' else 0
    r.update(replay=rp, lossHits=hits, judgedAt=round(now, 1))
    if rp['pass']:
        r.update(status='live', door='walk-forward')
    elif r['act'] == 'avoid' and hits >= CAUSE_LOSSES and not rp['against']:
        r.update(status='live', door='new cause')
    elif rp['against'] or now - _f(r.get('at') or now) >= RETIRE_SEC:
        r.update(status='failed')
    else:
        r.update(status='proposed')
    if r['status'] == 'live' and not r.get('liveAt'):
        r['liveAt'] = round(now, 1)
    return r


def step(state, proposals, trades, now):
    """New proposals join (one per id, never a repeat of a failed one), every rule is re-judged on today's record. → (state, newly live)"""
    st = {'rules': list((state or {}).get('rules') or []), 'log': list((state or {}).get('log') or [])}
    have = {r['id'] for r in st['rules']}
    for r in proposals or []:
        if r['id'] not in have:
            st['rules'].append({**r, 'at': round(now, 1)}); have.add(r['id'])
    was = {r['id'] for r in st['rules'] if r.get('status') == 'live'}
    st['rules'] = [judge(r, trades, now) for r in st['rules']]
    went = [r for r in st['rules'] if r['status'] == 'live' and r['id'] not in was]
    for r in went:
        st['log'] = (st['log'] + [{'at': round(now, 1), 'id': r['id'], 'name': r['name'], 'door': r.get('door'), 'desk': r['desk']}])[-30:]
    st['rules'] = sorted(st['rules'], key=lambda r: ({'live': 0, 'proposed': 1, 'failed': 2}[r['status']], -_f(r.get('at'))))[:KEEP]
    return st, went


def live(state):
    return [r for r in (state or {}).get('rules') or [] if r.get('status') == 'live']


def weight(state, feats):
    """A live coin's rank factor from the live rules it matches (the most cautious avoid wins; favors only when no avoid matches)."""
    fs = set(feats or ())
    hit = [r for r in live(state) if set(r['when']) <= fs]
    if not hit:
        return 1.0
    av = [r for r in hit if r['act'] == 'avoid']
    f = AVOID_F ** len(av) if av else FAVOR_F
    return max(CLAMP[0], min(CLAMP[1], round(f, 3)))


def trigger_lessons(state):
    """Live AVOID rules on the entry MOMENT — Trigger arms instead of entering a coin that matches one."""
    return [{'id': r['id'], 'when': r['when'], 'name': r['name']} for r in live(state) if r['act'] == 'avoid' and any(t.startswith(MOMENT) for t in r['when'])]


def lessons(state):
    """{desk: [rule names]} — what each desk learned from the record (shown on the page)."""
    out = {}
    for r in live(state):
        out.setdefault(r['desk'], []).append(f"{'🚫' if r['act'] == 'avoid' else '✅'} {r['name']}")
    return out


def case(trades, state, reviews=None):
    """What the model is shown to propose from: the vocabulary (token → n, typical %), the rules already on file, the last losses' causes."""
    v = vocab(trades)
    top = sorted(v.items(), key=lambda kv: kv[1]['med'])[:14] + sorted(v.items(), key=lambda kv: -kv[1]['med'])[:6]
    return {'vocabTable': [f"{t}: n {x['n']} · typical {x['med']:+.0f}%" for t, x in top], 'vocab': sorted(v)[:60],
            'rules': [f"{r['act']} {' & '.join(r['when'])} ({r['status']})" for r in (state or {}).get('rules') or []][:12],
            'losses': [f"{r.get('sym')}: {_f(r.get('pct')):+.0f}% · {r.get('cause') or '?'}" for r in (reviews or []) if _f(r.get('pct')) < 0][-6:],
            'trades': len(_rm.trades(trades))}
