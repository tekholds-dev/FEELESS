"""💵 REAL-MONEY CATS — option A of docs/REAL_CATS.md, decided in docs/DECISIONS.md #2: the user's own wallet signs every trade; FEELESS never
holds a cat's money or keys. Pure + tested; feecat_service wires it.

A cat switched to REAL by a signed-in wallet keeps running its engine on its paper ledger (its shadow record, shown with every proposal) —
and every BUY it makes and every exit of a coin the user really bought becomes a PROPOSAL for that wallet: coin, side, size (a buy never
above the user's per-trade budget), the cat's reason and its record. A proposal lives PROPOSAL_SEC (prices move); the user approves it (the
swap opens with the coins + amount set → Get quote → the wallet signs) or skips it. Sells are only proposed for coins the user bought
through an approved proposal. Nothing here moves money."""
import hashlib
import json
import time
import uuid

PROPOSAL_SEC = 900       # a proposal is fresh for 15 minutes
KEEP = 30                # proposals remembered per cat (newest first)
MIN_BUDGET, MAX_BUDGET = 0.01, 5.0   # SOL per real buy the user allows


def session_wallet(sessions, token, now=None):
    """The wallet a FEELESS chat session token belongs to (the same store reputation_service signs into), or None when unknown / expired."""
    if not token:
        return None
    rec = ((sessions or {}).get('s') or {}).get(hashlib.sha256(str(token).encode()).hexdigest())
    if not rec or (now or time.time()) > float(rec.get('exp') or 0):
        return None
    return rec.get('address')


def load_sessions(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def go_real(cat, wallet, budget_sol, now=None):
    """Switch a cat to REAL for `wallet` (the signed-in owner) with a per-buy budget. → the cat."""
    b = float(budget_sol or 0)
    if not MIN_BUDGET <= b <= MAX_BUDGET:
        raise ValueError(f'A real cat buys between {MIN_BUDGET} and {MAX_BUDGET} SOL a trade.')
    cat.update(mode='real', realWallet=wallet, budgetSol=round(b, 4), realSince=now or time.time())
    cat.setdefault('proposals', []); cat.setdefault('realHeld', {})
    return cat


def go_paper(cat):
    cat['mode'] = 'paper'
    for p in cat.get('proposals') or []:
        if p['status'] == 'pending':
            p['status'] = 'cancelled'
    return cat


def is_real(cat):
    return (cat or {}).get('mode') == 'real' and bool(cat.get('realWallet'))


def record_of(cat):
    """The cat's own paper record, shown with every proposal (no cat has a proven edge on unseen coins — say so with numbers)."""
    n = int(cat.get('wins') or 0) + int(cat.get('losses') or 0)
    return {'trades': n, 'wonPct': round(100 * int(cat.get('wins') or 0) / n) if n else None, 'pnlSol': round(float(cat.get('realizedPnlSol') or 0), 4)}


def propose(cat, side, mint, pair, symbol, why, now, sol=None, fraction=None, px=None):
    """A buy (`sol`, capped at the user's budget) or a sell (`fraction` of what the user bought) → the proposal (None when a sell has
    nothing real behind it). A newer proposal on the same coin + side replaces a pending one."""
    if not is_real(cat) or not mint:
        return None
    if side == 'sell' and not (cat.get('realHeld') or {}).get(mint):
        return None
    for p in cat['proposals']:
        if p['status'] == 'pending' and p['mint'] == mint and p['side'] == side:
            p['status'] = 'replaced'
    p = {'id': uuid.uuid4().hex[:10], 'side': side, 'mint': mint, 'pair': pair, 'symbol': symbol, 'why': str(why or '')[:160], 'at': now,
         'until': now + PROPOSAL_SEC, 'status': 'pending', 'px': px, 'record': record_of(cat)}
    if side == 'buy':
        p['sol'] = round(min(float(sol or 0) or cat['budgetSol'], cat['budgetSol']), 4)
    else:
        p['fraction'] = max(0.01, min(1.0, float(fraction or 1.0)))
    cat['proposals'] = ([p] + cat['proposals'])[:KEEP]
    return p


def expire(cat, now):
    """Pending proposals older than PROPOSAL_SEC → expired. → how many."""
    n = 0
    for p in cat.get('proposals') or []:
        if p['status'] == 'pending' and now > p['until']:
            p['status'] = 'expired'; n += 1
    return n


def resolve(cat, pid, result, now, sig=None):
    """The user's answer: 'done' (signed — `sig` is the transaction) or 'skip'. A done buy marks the coin as really held; a done full sell
    clears it. → the proposal."""
    p = next((x for x in cat.get('proposals') or [] if x['id'] == pid), None)
    if not p:
        raise ValueError('That proposal is gone.')
    if p['status'] != 'pending':
        raise ValueError(f"That proposal is {p['status']} already.")
    if result not in ('done', 'skip'):
        raise ValueError('done or skip.')
    if result == 'done' and now > p['until']:
        p['status'] = 'expired'
        raise ValueError('That proposal expired — prices moved; wait for the next one.')
    p.update(status=result, answeredAt=now, sig=(str(sig)[:100] if sig else None))
    held = cat.setdefault('realHeld', {})
    if result == 'done' and p['side'] == 'buy':
        held[p['mint']] = {'at': now, 'symbol': p['symbol'], 'pair': p['pair']}
    elif result == 'done' and p['side'] == 'sell' and p.get('fraction', 1) >= 0.99:
        held.pop(p['mint'], None)
    return p


def view(cat, now):
    """What the owner's page shows: mode, budget, live proposals (pending first), what is really held."""
    expire(cat, now)
    ps = sorted(cat.get('proposals') or [], key=lambda p: (p['status'] != 'pending', -p['at']))
    return {'mode': cat.get('mode') or 'paper', 'wallet': cat.get('realWallet'), 'budgetSol': cat.get('budgetSol'), 'proposals': ps[:12],
            'pending': sum(1 for p in ps if p['status'] == 'pending'), 'held': cat.get('realHeld') or {}}
