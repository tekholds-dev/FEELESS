"""🧪 THE TRENCH THEORY (owner, 2026-10-22: "create a scientific trench meta theory for agents and NEXA and G4"). Pure + tested.

Every law below is a MEASURED claim from FEELESS's own records, not a vibe — `scripts/edge-audit.py` (4,000 launch coins watched an hour,
learn on the oldest 60 %, test on the newest 40 %, 3 % round-trip cost) and the real card's ledger (943 pieces). `verdict(case)` reads a coin
case against the laws BEFORE any model sees it, so G4 / OSSY / NEXA confirm or deny ONE line instead of reasoning from zero (shorter prompts,
faster reads), and every model argues from the same evidence. Re-run the audit and update EVIDENCE when the numbers move; a law that stops
holding on unseen coins is deleted, never argued with.
"""

AS_OF = '2026-10-22'
COST_PCT = 3.0
# law key → (the claim, the evidence behind it)
EVIDENCE = {
    'fresh':   ('a coin under 15 min old loses', '2,421 coins: typical −68.7 % over the hour, 14 % up'),
    'curve':   ('still on the bonding curve = the worst bucket', '2,181 coins: typical −65.4 %, 9 % up'),
    'proven':  ('cap under $30K AND graduated = the ONLY rule positive on unseen coins', '110 coins: typical +1.0 %, capped avg +10.2 %, 52 % up'),
    'exits':   ('set the exit before entry: out at +50 / −30 beats holding', 'typical −9.9 % vs −42.8 % held an hour'),
    'hold':    ('on the real card, holds of 30 min+ win and holds under 15 min lose; trims make the money', '943-piece ledger'),
    'cost':    (f'a setup must expect more than the {COST_PCT:g} % round trip', 'every rule is scored after cost'),
    'thin':    ('a pool under $5K cannot take a real exit', 'slippage eats the move'),
}


def _n(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def verdict(case):
    """A coin case → {score -3…+2, fits [law], breaks [law], line} — the desk's pre-read every model gets as `theory`."""
    c = case if isinstance(case, dict) else {}
    age, cap, liq, held = _n(c.get('ageMin')), _n(c.get('cap')), _n(c.get('liq')), _n(c.get('heldMin'))
    stage = str(c.get('curve') or c.get('stage') or c.get('status') or '').lower()
    graduated = any(w in stage for w in ('graduat', 'migrat', 'amm', 'raydium', 'pumpswap')) or c.get('graduated') is True
    on_curve = not graduated and ('curve' in stage or 'bond' in stage)
    fits, breaks = [], []
    if age is not None and age < 15:
        breaks.append('fresh')
    if on_curve:
        breaks.append('curve')
    if graduated and cap is not None and cap < 30_000:
        fits.append('proven')
    if liq is not None and liq < 5_000:
        breaks.append('thin')
    if held is not None and held >= 30:
        fits.append('hold')
    elif held is not None and held < 15:
        breaks.append('hold')
    score = max(-3, min(2, len(fits) - len(breaks)))
    words = [f"✅ {EVIDENCE[k][0]} ({EVIDENCE[k][1]})" for k in fits] + [f"⛔ {EVIDENCE[k][0]} ({EVIDENCE[k][1]})" for k in breaks]
    lead = 'FITS the proven setup' if 'proven' in fits and not breaks else 'BREAKS the theory' if breaks else 'no proven edge either way'
    return {'score': score, 'fits': fits, 'breaks': breaks, 'line': f"theory {AS_OF}: {lead}" + (f" — {'; '.join(words)}" if words else '') + f"; exits set first (+50 / −30); cost {COST_PCT:g} %."}


def laws_text():
    """The theory as plain lines (Brain › Models, the docs, a GENERAL question about strategy)."""
    return [f"{k.upper()}: {claim} — {ev}" for k, (claim, ev) in EVIDENCE.items()]
