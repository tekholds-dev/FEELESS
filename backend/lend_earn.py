"""🏦 DEPOSIT WITHOUT LEAVING FEELESS — Jupiter Lend Earn (owner, 2026-10-22: "in-city deposit … the wallet signs, never custody").

Jupiter's Earn API builds the UNSIGNED transaction (POST /lend/v1/earn/deposit · /withdraw {asset, signer, amount in base units} →
{transaction: base64}); FEELESS only passes it to the user's own wallet. Before it does, `verify` opens the transaction and refuses it unless:
  · the fee payer is the user and the user is the ONLY signer (nobody else can co-sign anything into it),
  · every instruction calls a program on ALLOW (Jupiter Lend's own programs from developers.jup.ag/docs/lend/program-addresses + Solana's
    system / token / associated-token / compute-budget / memo programs).
The client then simulates it (nothing is signed if the chain would reject it), the wallet signs, the user sees it land. Pure: no network here.
"""
import base64
from decimal import Decimal, InvalidOperation, ROUND_DOWN

EARN = 'https://api.jup.ag/lend/v1/earn'
EARN_PUBLIC = 'https://lite-api.jup.ag/lend/v1/earn'
SIDES = ('deposit', 'withdraw')
ALLOW = {
    'jup3YeL8QhtSx1e253b2FDvsMNC87fDrgQZivbrndc9': 'Jupiter Lend · Earn',
    'jupeiUmn818Jg1ekPURTpr4mFo29p46vygyykFJ3wZC': 'Jupiter Lend · Liquidity',
    'jup7TthsMgcR9Y3L277b8Eo9uboVSmu1utkuXHNUKar': 'Jupiter Lend · Rewards rate model',
    'jupnw4B6Eqs7ft6rxpzYLJZYSnrpRgPcr589n5Kv4oc': 'Jupiter Oracle',
    '11111111111111111111111111111111': 'System',
    'ComputeBudget111111111111111111111111111111': 'Compute budget',
    'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'Token',
    'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb': 'Token-2022',
    'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 'Associated token account',
    'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr': 'Memo',
}
MAX_TX_BYTES = 1232


def base_units(amount, decimals):
    """'1.5' USDC (6 decimals) → '1500000'. Rounds DOWN (never asks for more than typed); None for anything not a positive number."""
    try:
        d = Decimal(str(amount).strip())
        dec = int(decimals)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not d.is_finite() or d <= 0 or not 0 <= dec <= 18:
        return None
    n = int((d * (Decimal(10) ** dec)).to_integral_value(rounding=ROUND_DOWN))
    return str(n) if n > 0 else None


def clean_request(raw):
    """→ (side, asset, signer, amount) or raises ValueError with words the panel shows."""
    raw = raw if isinstance(raw, dict) else {}
    side = str(raw.get('side') or 'deposit')
    if side not in SIDES:
        raise ValueError('Pick deposit or withdraw.')
    asset, signer = str(raw.get('asset') or '').strip(), str(raw.get('address') or '').strip()
    if not (32 <= len(asset) <= 44) or not (32 <= len(signer) <= 44):
        raise ValueError('Connect your wallet and pick a lending market.')
    return side, asset, signer, raw.get('amount')


def verify(b64, signer, allow=None, must=('jup3YeL8QhtSx1e253b2FDvsMNC87fDrgQZivbrndc9', 'jupeiUmn818Jg1ekPURTpr4mFo29p46vygyykFJ3wZC')):
    """The transaction Jupiter built → (ok, why, programs). Refused unless the user pays + is the only signer, every program is on `allow`
    (default ALLOW) and one of `must` runs (`lend_borrow` passes Jupiter Lend's vaults program)."""
    allow = ALLOW if allow is None else allow
    from solders.transaction import VersionedTransaction
    try:
        raw = base64.b64decode(str(b64 or ''), validate=True)
    except Exception:
        return False, 'Not a transaction.', []
    if not raw or len(raw) > MAX_TX_BYTES:
        return False, 'Not a transaction.', []
    try:
        msg = VersionedTransaction.from_bytes(raw).message
    except Exception:
        return False, 'Not a transaction.', []
    keys = [str(k) for k in msg.account_keys]
    if not keys or keys[0] != signer:
        return False, 'The fee payer is not your wallet.', []
    if msg.header.num_required_signatures != 1:
        return False, 'Someone other than you would sign it.', []
    progs = []
    for ix in msg.instructions:
        i = ix.program_id_index
        if i >= len(keys):
            return False, 'It calls a program it does not list.', progs
        progs.append(keys[i])
    bad = sorted({p for p in progs if p not in allow})
    if bad:
        return False, f"It calls a program FEELESS does not know ({bad[0][:6]}…) — refused.", progs
    if not any(p in must for p in progs):
        return False, 'It never calls Jupiter Lend — refused.', progs
    return True, None, progs


# 💵 THE $5 RUN (owner, 2026-10-23: "a minimum of $5 to see REAL compound"): a Jupiter Lend Earn deposit compounds on-chain every block — the
# run shows the wallet's own position (Jupiter's /earn/positions: `underlyingAssets` = what the deposit is worth now) and Jupiter's own
# earnings count, ticking between reads at the live rate. Rates come as hundredths of a percent (728 = 7.28 %).
RUN = {'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 'USDC', 'So11111111111111111111111111111111111111112': 'SOL'}
RUN_MIN_USD = 5


def _n(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def run_assets(tokens):
    """Jupiter's /earn/tokens → the run's two doors, USDC then SOL: {sym, mint, jl, dec, apy, price}."""
    out = {}
    for t in tokens if isinstance(tokens, list) else []:
        try:
            a = t['asset']; sym = RUN.get(a['address'])
            if sym and sym not in out:
                out[sym] = {'sym': sym, 'mint': a['address'], 'jl': t['address'], 'dec': int(t.get('decimals') or a.get('decimals') or 6),
                            'apy': round(_n(t.get('totalRate')) / 100, 2), 'price': _n(a.get('price'))}
        except (KeyError, TypeError, ValueError):
            continue
    return [out[k] for k in ('USDC', 'SOL') if k in out]


def run_positions(positions, assets, earned=None):
    """The wallet's live deposits in the run's assets (shares > 0) → {sym, mint, jl, balance, usd, apy, earned (Jupiter's count, $)}."""
    by = {a['jl']: a for a in assets}; earned = earned or {}; out = []
    for p in positions if isinstance(positions, list) else []:
        try:
            a = by.get(p['token']['address'])
            if not a or _n(p.get('shares')) <= 0:
                continue
            bal = _n(p.get('underlyingAssets')) / 10 ** a['dec']
        except (KeyError, TypeError):
            continue
        out.append({**a, 'balance': bal, 'usd': round(bal * a['price'], 6), 'earned': round(_n(earned.get(a['jl'])) / 10 ** a['dec'] * a['price'], 6)})
    return out

