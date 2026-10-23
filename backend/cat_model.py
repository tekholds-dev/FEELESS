"""🪟 A CAT WITH A MODEL BRAIN (owner, 2026-10-22: "NEXA trading a cat"). A cat assigned to NEXA trades PAPER on her own published desk read
(`/api/reputation/cats-ai` → `nexa`: favor / exit / avoid by pairAddress, one read per ~15 min on her CPU model) — no extra inference per cat:

- BUY: only a coin she FAVORED in a fresh read, and only after every FeeCat guard passed it (lanes, safety, Fuse veto, setup memory,
  discipline) — her word picks among guarded coins, it never opens a new buy door. NEXA SILENT (no fresh read) → FeeCat's own engine covers
  at COVER_MULT size, tagged, so the desk never stalls on her CPU.
- SELL: a coin she named EXIT in a fresh read is sold at the live price. Stops, trails and the rug rules keep running underneath her.
- AVOID: never bought.
A read older than FRESH_SEC is not acted on (the cat simply holds and its rules run). Pure + tested; feecat_service does the I/O.
"""
import time

FRESH_SEC = 1800.0   # her read runs every 15 min (~3 min on the i5): a read older than 30 min is stale → the cat's own rules only
COVER_MULT = 0.5     # NEXA silent (no fresh read) → FeeCat's own engine covers at half size (owner: "feecat's engine covers if she doesn't answer")
COVER_WHY = "🐱 FeeCat covers for NEXA (no fresh answer) — her own rules, half size"
MODELS = {'nexa': {'id': 'nexa', 'name': 'NEXA', 'key': 'win', 'provider': 'FEELESS · local model', 'label': 'NEXA · FEELESS local model'}}


def model_of(cat):
    """→ the cat's model-brain row, or None (rule engine)."""
    return MODELS.get(str((cat or {}).get('modelBrain') or '').lower())


def read_of(nexa, now=None):
    """`/cats-ai`'s `nexa` block → {favor, exit, avoid (sets of pairAddress), why, at, age} or None when missing / stale."""
    n = nexa if isinstance(nexa, dict) else {}
    at = float(n.get('at') or 0)
    now = time.time() if now is None else now
    if at <= 0 or now - at > FRESH_SEC:
        return None
    pick = lambda k: {str(p) for p in (n.get(k) or []) if p}
    return {'favor': pick('favor'), 'exit': pick('exit'), 'avoid': pick('avoid'), 'why': ' '.join(str(n.get('why') or '').split())[:160],
            'at': at, 'age': round(now - at), 'skim': {str(p): float(t or 0) for p, t in (n.get('skim') or {}).items() if p},
            'lines': {str(p): v for p, v in (n.get('lines') or {}).items() if p and isinstance(v, dict)}}


def buy_ok(read, pair):
    """→ (ok, why). Only a coin she favored in a fresh read; an avoided one never."""
    if not read:
        return False, '🪟 NEXA has no fresh read — her cat waits for her'
    if pair in read['avoid']:
        return False, '🪟 NEXA said avoid it'
    if pair not in read['favor']:
        return False, '🪟 not one of NEXA\'s picks'
    return True, f"🪟 NEXA favored it ({round(read['age'] / 60)} min ago)" + (f": {read['why']}" if read['why'] else '')


def sell_now(read, pair):
    """→ the sale's reason when her fresh read named this held coin EXIT, else None."""
    if read and pair in read['exit']:
        return '🪟 NEXA said exit' + (f": {read['why']}" if read['why'] else '')
    return None


def skim_now(read, pos):
    """→ the reason to bank HALF of this held coin when her fresh read said SKIM on it and that call wasn't skimmed yet (pos['nxSkimAt'])."""
    at = (read or {}).get('skim', {}).get((pos or {}).get('pairAddress'))
    if not at or float((pos or {}).get('nxSkimAt') or 0) >= at:
        return None
    return '🪟 NEXA said skim: banked half'


def line_exit(read, pos, change):
    """🎯 Her own stop / take on a held coin ({'sl': 15, 'tp': 60} in % from the average entry) → the sale's reason, else None. FeeCat's rug
    stops keep running underneath; her lines only ever sell (never widen a stop)."""
    ln = (read or {}).get('lines', {}).get((pos or {}).get('pairAddress')) or {}
    if ln.get('sl') and change <= -float(ln['sl']):
        return f"🪟 NEXA's stop −{float(ln['sl']):g}% hit ({change:+.1f}%)"
    if ln.get('tp') and change >= float(ln['tp']):
        return f"🪟 NEXA's take +{float(ln['tp']):g}% hit ({change:+.1f}%)"
    return None


def status(nexa, now=None):
    """The model's live state for the UI: live (fresh read) · waiting (stale / none) + her read's counts."""
    r = read_of(nexa, now)
    n = nexa if isinstance(nexa, dict) else {}
    return {'state': 'live' if r else 'waiting', 'readAt': n.get('at'), 'ageMin': round(r['age'] / 60) if r else None,
            'favor': len(n.get('favor') or []), 'exit': len(n.get('exit') or []), 'avoid': len(n.get('avoid') or []),
            'why': ' '.join(str(n.get('why') or '').split())[:160], 'record': n.get('record')}
