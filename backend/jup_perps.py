"""📉 REAL PERPS — Jupiter Perps, in FEELESS (owner, 2026-10-23: "do jupiter as a provider … we tryna long or short — that's what matters";
DECISIONS #8: the owner lifted the 🇺🇸 rule for perps, their call and their risk).

Jupiter's Perps API builds the transaction (POST perps-api.jup.ag/v1/positions/increase · /positions/decrease → serializedTxBase64 + quote);
the user's wallet signs it, FEELESS passes it to Jupiter's /transaction/execute, where Jupiter's keeper co-signs and lands it ("instant"
positions). `verify` opens every transaction before the wallet sees it and refuses it unless the user pays, the user is a signer, at most
Jupiter's keeper signers sign beside them, and only the Perps program + Solana's own programs run. Longs on SOL / ETH / BTC hold the asset
as collateral, shorts hold USDC (Jupiter's rule); the user funds with USDC or SOL. Jupiter's minimum is $10 of collateral per new position.
Guards: those three markets only, leverage 1.1–100×, $10–$1,000 collateral per open, 1 % max price slippage. Pure: no network here.
"""
import base64

API = 'https://perps-api.jup.ag/v1'
PERPS = 'PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu'
ALLOW = {PERPS: 'Jupiter Perps', '11111111111111111111111111111111': 'System', 'ComputeBudget111111111111111111111111111111': 'Compute budget',
         'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'Token', 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 'Associated token account',
         'DoVEsk76QybCEHQGzkvYPWLQu9gzNoZZZt3TPiL597e': 'Jupiter Doves price oracle', 'Ed25519SigVerify111111111111111111111111111': 'Signed-price check'}
USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
SOL = 'So11111111111111111111111111111111111111112'
MARKETS = {'SOL': SOL, 'ETH': '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs', 'BTC': '3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh'}
INPUTS = {'USDC': (USDC, 6), 'SOL': (SOL, 9)}
MIN_USD, MAX_USD, MIN_LEV, MAX_LEV, SLIP_BPS = 10, 1000, 1.1, 100, 100
MAX_TX_BYTES = 1232


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def clean_open(raw, sol_price):
    """{address, asset, side, usd (collateral $), lev, input: USDC|SOL} → the /positions/increase body + what it is, or ValueError."""
    raw = raw if isinstance(raw, dict) else {}
    me, asset, side, inp = str(raw.get('address') or '').strip(), str(raw.get('asset') or '').upper(), str(raw.get('side') or '').lower(), str(raw.get('input') or 'USDC').upper()
    if not 32 <= len(me) <= 44:
        raise ValueError('Connect your wallet first.')
    if asset not in MARKETS or side not in ('long', 'short') or inp not in INPUTS:
        raise ValueError('Pick SOL, ETH or BTC, long or short, paid in USDC or SOL.')
    usd, lev = _f(raw.get('usd')), _f(raw.get('lev'))
    if usd is None or not MIN_USD <= usd <= MAX_USD:
        raise ValueError(f'Collateral runs ${MIN_USD} (Jupiter\'s minimum) to ${MAX_USD:,} per open.')
    if lev is None or not MIN_LEV <= lev <= MAX_LEV:
        raise ValueError(f'Leverage runs {MIN_LEV}× to {MAX_LEV}×.')
    mint, dec = INPUTS[inp]
    if inp == 'SOL' and not (sol_price and sol_price > 0):
        raise ValueError('No live SOL price — pay in USDC or try again.')
    amount = usd if inp == 'USDC' else usd / sol_price
    units = str(int(amount * 10 ** dec))
    body = {'walletAddress': me, 'marketMint': MARKETS[asset], 'collateralMint': MARKETS[asset] if side == 'long' else USDC, 'inputMint': mint,
            'collateralTokenDelta': units, 'side': side, 'maxSlippageBps': str(SLIP_BPS), 'leverage': f'{round(lev, 1)}', 'includeSerializedTx': True}
    return body, {'asset': asset, 'side': side, 'usd': round(usd, 2), 'lev': round(lev, 1), 'input': inp}


def close_body(raw):
    raw = raw if isinstance(raw, dict) else {}
    me, pos = str(raw.get('address') or '').strip(), str(raw.get('positionPubkey') or '').strip()
    if not 32 <= len(me) <= 44 or not 32 <= len(pos) <= 44:
        raise ValueError('Pick the position to close.')
    return {'walletAddress': me, 'positionPubkey': pos, 'entirePosition': True, 'receiveToken': 'USDC', 'maxSlippageBps': str(SLIP_BPS), 'includeSerializedTx': True}


def verify(b64, signer, signed=False):
    """A Jupiter Perps transaction → (ok, why). The user pays and signs; at most two keeper signers beside them; only ALLOW programs; the
    Perps program runs. `signed`: the wallet's signature must be present (the execute step)."""
    from solders.transaction import VersionedTransaction
    try:
        raw = base64.b64decode(str(b64 or ''), validate=True)
        tx = VersionedTransaction.from_bytes(raw)
    except Exception:
        return False, 'Not a transaction.'
    if len(raw) > MAX_TX_BYTES:
        return False, 'Not a transaction.'
    msg = tx.message; keys = [str(k) for k in msg.account_keys]; n = msg.header.num_required_signatures
    if not keys or keys[0] != signer:
        return False, 'The fee payer is not your wallet.'
    if not 1 <= n <= 3:
        return False, 'Unexpected signers — refused.'
    progs = set()
    for ix in msg.instructions:
        if ix.program_id_index >= len(keys):
            return False, 'It calls a program it does not list.'
        progs.add(keys[ix.program_id_index])
    bad = sorted(p for p in progs if p not in ALLOW)
    if bad:
        return False, f'It calls a program FEELESS does not know ({bad[0][:6]}…) — refused.'
    if PERPS not in progs:
        return False, 'It never calls Jupiter Perps — refused.'
    if signed and bytes(tx.signatures[0]) == bytes(64):
        return False, 'Your wallet did not sign it.'
    return True, None


def _usd(v):   # Jupiter's raw USD integers carry 6 decimals
    x = _f(v)
    return None if x is None else x / 1e6


def positions(raw):
    """GET /positions?walletAddress= → the open positions, newest first, in plain dollars."""
    rows = (raw or {}).get('dataList') if isinstance(raw, dict) else None
    out = []
    for p in rows if isinstance(rows, list) else []:
        try:
            out.append({'pubkey': p['positionPubkey'], 'asset': p['asset'], 'side': p['side'], 'lev': round(_f(p.get('leverage')) or 0, 2),
                        'size': _usd(p.get('sizeUsd')), 'collateral': _usd(p.get('collateralUsd')), 'value': _usd(p.get('valueUsd')),
                        'entry': _usd(p.get('entryPriceUsd')), 'mark': _usd(p.get('markPriceUsd')), 'liq': _usd(p.get('liquidationPriceUsd')),
                        'pnl': _usd(p.get('pnlBeforeFeesUsd')), 'pnlPct': _f(p.get('pnlBeforeFeesPct')), 'fees': _usd(p.get('totalFeesUsd')),
                        'at': _f(p.get('createdTime'))})
        except (KeyError, TypeError):
            continue
    return sorted(out, key=lambda x: -(x['at'] or 0))
