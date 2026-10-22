"""🛡 REP MARKETS — YES / NO markets on what FEELESS itself measures (owner, 2026-10-20: "add polymarket bidding to rep — its own robust live
twist, degen and META"). Pure + tested; the service holds the store and the clock.

NOT MONEY, EVER: every wallet gets CHIPS_WEEK free chips each UTC week; chips can't be bought, sent or cashed out, and every wallet starts the
week at the same number. A winning side's chips are paid back out of the losing side (parimutuel), and the week's net chip gain turns into season
points (CHIPS_PER_PT chips = 1 point). Nothing is deposited, nothing is withdrawn.

THE TWIST — REP-WEIGHTED ODDS: every market shows TWO prices. The crowd price is the plain share of chips on YES. The 🛡 rep price weighs every stake
by its bettor's verified FEELESS trust score (0–100: verified trades, calls, bot shield) — so you can see when the wallets with a record disagree
with the crowd. When the two split by SPLIT_PTS or more the market is flagged ⚡ SMART SPLIT.

Markets are made every hour from the live lists and settled on recorded prices only (Jupiter), so every result can be checked:
  · 📈 UP      — "$SYM higher in 1h?"           YES = price at close > price at open
  · 🚀 DOUBLE  — "$SYM 2× in 4h?"               YES = price ever seen ≥ 2× open before close (peak tracked each tick)
  · ☠ RUG     — "$SYM −80% within 1h?"         YES = price ever seen ≤ 0.2× open, or no price for the last 15 min of the window
"""
import uuid

CHIPS_WEEK = 1000
STAKE_MIN, STAKE_MAX = 10, 500
CHIPS_PER_PT = 10
SPLIT_PTS = 15
LOCK_SEC = 120
KINDS = {'up': ('📈', 3600), 'double': ('🚀', 4 * 3600), 'rug': ('☠', 3600)}
MARKETS_KEPT = 160
GONE_SEC = 900
HOUSE = 'house'
HOUSE_SEED = 100   # 🏠 the house backs BOTH sides of every market (free chips, never banked): a lone right call still gets paid (2026-10-22 —
                    # the owner bid alone, every market was one-sided, so a win only refunded the stake)
WEEK = 7 * 86400

from fnum import plain as _f   # noqa: E402


def week_id(now):
    return int((now + 3 * 86400) // WEEK)   # Monday-anchored UTC weeks


def bank(st, wallet, now):
    """The wallet's chip bank this week (made fresh on its first read of a new week)."""
    b = st.setdefault('banks', {}).get(wallet)
    if not b or b.get('week') != week_id(now):
        b = {'week': week_id(now), 'chips': CHIPS_WEEK, 'won': 0, 'lost': 0, 'pts': 0}
        st['banks'][wallet] = b
    return b


def question(kind, sym):
    return {'up': f'${sym} higher in 1 hour?', 'double': f'${sym} doubles within 4 hours?', 'rug': f'${sym} falls 80% within 1 hour?'}[kind]


def make(kind, mint, sym, px, now, src=None, seed=0):
    icon, dur = KINDS[kind]
    return {'id': uuid.uuid4().hex[:10], 'kind': kind, 'icon': icon, 'mint': mint, 'sym': sym, 'q': question(kind, sym), 'src': src,
            'px0': _f(px), 'peak': _f(px), 'low': _f(px), 'lastPxAt': now, 'opensAt': now, 'closesAt': now + dur, 'state': 'open',
            'stakes': [{'w': HOUSE, 'side': sd, 'chips': seed, 'at': now, 'rep': 0} for sd in ('yes', 'no') if seed > 0], 'path': [[round(now), 1.0]]}


def new_markets(st, rows, prices, now, per_hour=4):
    """Open this hour's markets from the live lists (rows: [{mint, symbol, src, rug?, ageH?}]) — one coin once per open market, ≤ per_hour new.
    Kinds: the top two trending → UP · a coin under 6h old → DOUBLE · a coin with a rug meter ≥ 50 → RUG."""
    open_ = {(m['mint'], m['kind']) for m in st.get('markets') or [] if m['state'] == 'open'}
    made, out = 0, []
    def add(kind, r):
        nonlocal made
        px = _f((prices or {}).get(r.get('mint')))
        if made >= per_hour or px <= 0 or (r['mint'], kind) in open_:
            return
        m = make(kind, r['mint'], r.get('symbol') or r['mint'][:4], px, now, r.get('src'), seed=HOUSE_SEED)
        out.append(m); open_.add((r['mint'], kind)); made += 1
    rows = [r for r in rows or [] if r.get('mint')]
    for r in rows[:2]:
        add('up', r)
    def pick(ok):   # a coin not already in a market this pass first — variety over three markets on one coin
        used = {m['mint'] for m in out}
        hits = [r for r in rows if ok(r)]
        return next((r for r in hits if r['mint'] not in used), hits[0] if hits else None)
    r = pick(lambda r: r.get('ageH') is not None and _f(r['ageH']) < 6)
    if r:
        add('double', r)
    r = pick(lambda r: _f(r.get('rug')) >= 50)
    if r:
        add('rug', r)
    st.setdefault('markets', []).extend(out)
    st['markets'] = st['markets'][-MARKETS_KEPT:]
    return out


def odds(m, rep_of=None):
    """→ {yes, no (chips), crowd (YES %), rep (rep-weighted YES %), split, n}. A market with no chips reads 50 / 50."""
    yes = sum(s['chips'] for s in m['stakes'] if s['side'] == 'yes')
    no = sum(s['chips'] for s in m['stakes'] if s['side'] == 'no')
    w = lambda s: s['chips'] * max(5.0, _f((rep_of or {}).get(s['w'], s.get('rep', 50))))   # rep 0 still counts a little
    wy = sum(w(s) for s in m['stakes'] if s['side'] == 'yes' and s['w'] != HOUSE); wn = sum(w(s) for s in m['stakes'] if s['side'] == 'no' and s['w'] != HOUSE)
    crowd = round(100 * yes / (yes + no)) if yes + no else 50
    rep = round(100 * wy / (wy + wn)) if wy + wn else 50
    return {'yes': yes, 'no': no, 'crowd': crowd, 'rep': rep, 'split': abs(crowd - rep) >= SPLIT_PTS and wy + wn > 0, 'n': sum(1 for s in m['stakes'] if s['w'] != HOUSE)}


def stake(st, wallet, mid, side, chips, now, rep=50):
    if side not in ('yes', 'no'):
        raise ValueError('Pick YES or NO.')
    m = next((x for x in st.get('markets') or [] if x['id'] == mid), None)
    if not m or m['state'] != 'open' or now >= m['closesAt'] - LOCK_SEC:
        raise ValueError('That market is closed for new chips.')
    chips = int(chips)
    if not STAKE_MIN <= chips <= STAKE_MAX:
        raise ValueError(f'Stake {STAKE_MIN}–{STAKE_MAX} chips.')
    if any(s['w'] == wallet and s['side'] != side for s in m['stakes']):
        raise ValueError('You already backed the other side of this market.')
    b = bank(st, wallet, now)
    if b['chips'] < chips:
        raise ValueError(f"You have {b['chips']} chips left this week.")
    b['chips'] -= chips
    m['stakes'].append({'w': wallet, 'side': side, 'chips': chips, 'at': now, 'rep': round(_f(rep))})
    return m


def mark(m, px, now):
    """Each tick: the live price moves the market's path / peak / low (what DOUBLE and RUG settle on)."""
    px = _f(px)
    if px > 0 and m['px0'] > 0:
        m['peak'] = max(m['peak'], px); m['low'] = min(m['low'], px); m['lastPxAt'] = now; m['pxNow'] = px
        if not m['path'] or now - m['path'][-1][0] >= 60:
            m['path'] = (m['path'] + [[round(now), round(px / m['px0'], 4)]])[-90:]


def outcome(m, now):
    """YES / NO once the market can be decided (early for DOUBLE / RUG the moment it happens), else None."""
    p0 = m['px0']
    if m['kind'] == 'double' and m['peak'] >= 2 * p0:
        return 'yes'
    if m['kind'] == 'rug' and (m['low'] <= 0.2 * p0 or now - _f(m.get('lastPxAt')) >= GONE_SEC):
        return 'yes'
    if now < m['closesAt']:
        return None
    if m['kind'] == 'up':
        return 'yes' if _f(m.get('pxNow')) > p0 else 'no'
    return 'no'


def settle(st, now):
    """Decide every market that can be decided; pay winners from the losing side (each winner gets back its chips + a share of the losers' by its
    stake), and record each wallet's net in its week. A one-sided market refunds everyone. → [settled markets]"""
    done = []
    for m in st.get('markets') or []:
        if m['state'] != 'open':
            continue
        res = outcome(m, now)
        if res is None:
            continue
        m['state'], m['result'], m['settledAt'] = 'settled', res, now
        win = [s for s in m['stakes'] if s['side'] == res]; lose = [s for s in m['stakes'] if s['side'] != res]
        tw, tl = sum(s['chips'] for s in win if s['w'] != HOUSE), sum(s['chips'] for s in lose)   # the house's winning seed takes no share (burned)
        for s in m['stakes']:
            if s['w'] == HOUSE:   # the house's seed is never banked: what it loses pays the winners, what it wins is burned
                s['paid'] = 0; continue
            b = bank(st, s['w'], now)
            if not win or not lose:      # nobody on one side (a market without a house seed): everyone home
                b['chips'] += s['chips']; s['paid'] = s['chips']
            elif s['side'] == res:
                gain = round(tl * s['chips'] / tw)
                b['chips'] += s['chips'] + gain; b['won'] += gain; s['paid'] = s['chips'] + gain
            else:
                b['lost'] += s['chips']; s['paid'] = 0
        done.append(m)
    return done


def season_pts(b):
    """Points the week's NET chip gain is worth (never negative)."""
    return max(0, int((b.get('won', 0) - b.get('lost', 0)) // CHIPS_PER_PT))


def view(m, now, wallet=None, rep_of=None):
    o = odds(m, rep_of)
    mine = [s for s in m['stakes'] if s['w'] == wallet] if wallet else []
    return {'id': m['id'], 'kind': m['kind'], 'icon': m['icon'], 'q': m['q'], 'mint': m['mint'], 'sym': m['sym'], 'src': m.get('src'), 'state': m['state'],
            'result': m.get('result'), 'opensAt': m['opensAt'], 'closesAt': m['closesAt'], 'locksAt': m['closesAt'] - LOCK_SEC,
            'move': round((_f(m.get('pxNow')) / m['px0'] - 1) * 100, 2) if m.get('pxNow') and m['px0'] else None,
            'peak': round((m['peak'] / m['px0'] - 1) * 100, 2) if m['px0'] else None, 'path': [p[1] for p in m['path'][-40:]], **o,
            'mine': {'side': mine[0]['side'], 'chips': sum(s['chips'] for s in mine), 'paid': sum(s.get('paid', 0) for s in mine) if m['state'] == 'settled' else None} if mine else None}


def board(st, now, wallet=None, rep_of=None):
    ms = st.get('markets') or []
    live = sorted([m for m in ms if m['state'] == 'open'], key=lambda m: m['closesAt'])
    done = sorted([m for m in ms if m['state'] != 'open'], key=lambda m: -_f(m.get('settledAt')))[:12]
    b = bank(st, wallet, now) if wallet else None
    lb = sorted(((w, x) for w, x in (st.get('banks') or {}).items() if x.get('week') == week_id(now)), key=lambda t: -(t[1].get('won', 0) - t[1].get('lost', 0)))[:10]
    return {'live': [view(m, now, wallet, rep_of) for m in live], 'settled': [view(m, now, wallet, rep_of) for m in done],
            'bank': ({**b, 'pts': season_pts(b)} if b else None),
            'top': [{'w': w[:4] + '…' + w[-4:], 'net': x.get('won', 0) - x.get('lost', 0)} for w, x in lb if x.get('won', 0) - x.get('lost', 0) > 0],
            'rules': {'week': CHIPS_WEEK, 'min': STAKE_MIN, 'max': STAKE_MAX, 'perPt': CHIPS_PER_PT, 'split': SPLIT_PTS}}
