"""BOT SHIELD: FEELESS's defender. Pure engines over a wallet's own FEELESS records (no I/O). Each engine returns a
0–100 score and cited evidence (claim + source), exactly like case files, so every flag can be checked by a human.

Engines (each catches one farming pattern):
  reward_farmer   signs in for daily rewards but never trades or chats
  clockwork       acts on a machine schedule (near-identical gaps / same second of the day)
  batch_cluster   checks in within the same seconds as a group of other wallets, day after day
  wash_trader     buys and sells the same coin back-to-back for ~zero net (farms volume / points)
  dust_farmer     many sub-$1 trades (farms trade-count quests)
  chat_spam       repeats the same message / bursts of messages
  referral_farm   invites wallets that never do anything
  fuse_self_deal  buys its own Fuse (farms the creator cut)
verdict(): bot ≥ 75, watch ≥ 45, else clean. Admin "clear" always wins; FEELESS wallets are never flagged.
"""
import statistics
from collections import Counter

BOT, WATCH = 75, 45


def _e(engine, score, claims):
    return {'engine': engine, 'score': int(max(0, min(100, score))), 'evidence': [{'claim': c, 'source': s} for c, s in claims]}


def reward_farmer(f):
    days, trades, chat = len(f.get('signin_days') or []), len(f.get('trades') or []), len(f.get('chat') or [])
    if days >= 5 and trades == 0 and chat == 0:
        return _e('reward_farmer', 80 if days >= 14 else 60, [(f'{days} daily check-ins, 0 trades, 0 chat messages', 'Quest check-ins + trade ledger')])
    return None


def clockwork(f):
    ts = sorted(t for t in (f.get('checkin_at') or []) if t)
    claims, score = [], 0
    if len(ts) >= 5:
        sod = [t % 86400 for t in ts]
        sd = statistics.pstdev(sod)
        if sd < 90:
            score = 75; claims.append((f'{len(ts)} check-ins all within ±{int(sd)}s of the same time of day', 'Check-in timestamps'))
    ev = sorted(x for x in [*(t.get('ts') or 0 for t in f.get('trades') or []), *(m.get('ts') or 0 for m in f.get('chat') or [])] if x)
    if len(ev) >= 8:
        gaps = [b - a for a, b in zip(ev, ev[1:]) if b > a]
        if len(gaps) >= 7 and statistics.mean(gaps) > 0 and statistics.pstdev(gaps) / statistics.mean(gaps) < 0.05:
            score = max(score, 70); claims.append((f'{len(gaps)} actions spaced {int(statistics.mean(gaps))}s apart (±{statistics.pstdev(gaps) / statistics.mean(gaps) * 100:.1f}%)', 'Trades + chat timestamps'))
    return _e('clockwork', score, claims) if score else None


def batch_cluster(f):
    days = f.get('batch_days') or 0           # days this wallet checked in within 3s of ≥3 other wallets
    if days >= 3:
        return _e('batch_cluster', 85 if days >= 6 else 70, [(f'On {days} days it checked in within 3s of 3+ other wallets', 'Check-in timestamps (all wallets)')])
    return None


def wash_trader(f, window=600, tol=0.03):
    rows = sorted((t for t in f.get('trades') or [] if t.get('ts')), key=lambda t: t['ts'])
    trips = 0
    for i, a in enumerate(rows):
        if a.get('side') != 'buy':
            continue
        b = next((x for x in rows[i + 1:] if x.get('token') == a.get('token') and x.get('side') == 'sell' and x['ts'] - a['ts'] <= window), None)
        if b and a.get('usd') and abs((b.get('usd') or 0) - a['usd']) / a['usd'] <= tol:
            trips += 1
    if trips >= 3:
        return _e('wash_trader', 80 if trips >= 6 else 65, [(f'{trips} buy→sell round trips on the same coin inside 10 min for ~0 net', 'FEELESS trade ledger')])
    return None


def dust_farmer(f):
    usd = [float(t.get('usd') or 0) for t in f.get('trades') or []]
    if len(usd) >= 10 and statistics.median(usd) < 1:
        return _e('dust_farmer', 70 if len(usd) >= 30 else 55, [(f'{len(usd)} trades, median ${statistics.median(usd):.2f}', 'FEELESS trade ledger')])
    return None


def chat_spam(f):
    msgs = f.get('chat') or []
    dup = max(Counter(str(m.get('text') or '').strip().lower() for m in msgs if m.get('text')).values(), default=0)
    ts = sorted(m.get('ts') or 0 for m in msgs)
    burst = max((sum(1 for y in ts if 0 <= y - x <= 60) for x in ts), default=0)
    claims, score = [], 0
    if dup >= 5:
        score = 65 if dup < 12 else 80; claims.append((f'Same message posted {dup}×', 'Chat log'))
    if burst >= 20:
        score = max(score, 70); claims.append((f'{burst} messages inside one minute', 'Chat log'))
    return _e('chat_spam', score, claims) if score else None


def referral_farm(f):
    inv = f.get('invitees') or []           # [{active: bool}]
    dead = sum(1 for x in inv if not x.get('active'))
    if len(inv) >= 5 and dead / len(inv) >= 0.8:
        return _e('referral_farm', 80 if len(inv) >= 15 else 65, [(f'{dead} of {len(inv)} invited wallets never traded or chatted', 'Referral ledger + activity')])
    return None


def fuse_self_deal(f):
    n = f.get('own_fuse_buys') or 0
    if n:
        return _e('fuse_self_deal', 80 if n >= 3 else 50, [(f'Bought its own Fuse {n}× (creator cut withheld on these)', 'Fuse buys ledger')])
    return None


ENGINES = (reward_farmer, clockwork, batch_cluster, wash_trader, dust_farmer, chat_spam, referral_farm, fuse_self_deal)


def scan(f, protected=False, manual=None):
    """All engines → {verdict, score, hits}. manual = 'cleared' | 'bot' (Cmd Ctr decision) always wins."""
    if protected:
        return {'verdict': 'clean', 'score': 0, 'hits': [], 'why': 'FEELESS wallet'}
    hits = [h for h in (eng(f) for eng in ENGINES) if h]
    top = max((h['score'] for h in hits), default=0)
    score = min(100, top + 10 * sum(1 for h in hits if h['score'] >= WATCH and h['score'] != top))
    verdict = 'bot' if score >= BOT else 'watch' if score >= WATCH else 'clean'
    if manual == 'cleared':
        verdict, why = 'clean', 'Cleared in Cmd Ctr'
    elif manual == 'bot':
        verdict, why = 'bot', 'Confirmed bot in Cmd Ctr'
    else:
        why = hits[0]['evidence'][0]['claim'] if hits else 'No bot pattern'
    return {'verdict': verdict, 'score': score, 'hits': sorted(hits, key=lambda h: -h['score']), 'why': why}


def batch_days(checkins, wallet, window=3, peers=3):
    """checkins = {wallet: [ts,...]} → days on which `wallet` checked in within `window`s of ≥`peers` other wallets."""
    mine = checkins.get(wallet) or []
    others = [(w, t) for w, ts in checkins.items() if w != wallet for t in ts]
    days = set()
    for t in mine:
        near = {w for w, u in others if abs(u - t) <= window}
        if len(near) >= peers:
            days.add(int(t // 86400))
    return len(days)


def rep_penalty(result):
    """How Bot shield feeds reputation: bot −40, watch −15 (cited)."""
    return {'bot': -40, 'watch': -15}.get(result['verdict'], 0)
