"""💸 COL-16 · A proof sent WITH funds to be graded (owner 2026-11-12). Pure + tested (`tests/test_proof_funds.py`).

  QUOTE    the owner picks SOL; on AUTO its agent adds PCT % of that from ITS OWN wallet. Both amounts + the % are shown before send.
  SIGN     the owner's wallet signs ONE transfer (owner → the Collective pot). The server sends it only if the signed message is
           byte-for-byte the quoted one and the owner's signature verifies. A quote is used once (no resubmits) and lives 120 s.
  RECEIPT  filed on the proof: both amounts, the %, both signatures, the quote hash.
"""
import base64
import hashlib
import json

QUOTE_TTL = 120
MIN_SOL = 0.001
PCT_MAX = 100.0


def quote(user_sol, pct, auto, agent_free_sol):
    """→ {userSol, pct, agentSol, totalSol, auto}. On AUTO its agent's share must fit in its free SOL (gas already kept out)."""
    u = round(float(user_sol or 0), 6)
    if u < MIN_SOL:
        raise ValueError(f'Send at least {MIN_SOL} SOL with the proof.')
    p = round(float(pct or 0), 2) if auto else 0.0
    if auto and not 0 < p <= PCT_MAX:
        raise ValueError('Set its share between 1% and 100%.')
    a = round(u * p / 100, 6) if auto else 0.0
    if auto and a < MIN_SOL:
        raise ValueError(f'{p:g}% of {u:g} SOL is under {MIN_SOL} SOL. Raise the amount or the %.')
    if a > float(agent_free_sol or 0) + 1e-9:
        raise ValueError(f'Its wallet can add {max(0.0, float(agent_free_sol or 0)):.6f} SOL (gas kept). {p:g}% needs {a:g}.')
    return {'userSol': u, 'pct': p, 'agentSol': a, 'totalSol': round(u + a, 6), 'auto': bool(auto)}


def qhash(cat_id, proof_id, q, tx_b64):
    return hashlib.sha256(json.dumps([cat_id, proof_id, q, tx_b64], sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:24]


def signed_matches(signed_b64, quoted_b64, signer):
    """True only when the signed transaction's message IS the quoted message and `signer` really signed it."""
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
    try:
        st = Transaction.from_bytes(base64.b64decode(signed_b64)); qt = Transaction.from_bytes(base64.b64decode(quoted_b64))
    except (ValueError, TypeError):
        return False
    if bytes(st.message) != bytes(qt.message):
        return False
    keys = list(st.message.account_keys); pk = Pubkey.from_string(signer)
    if not keys or keys[0] != pk:
        return False
    sig = st.signatures[0]
    return sig.verify(pk, bytes(st.message))


def receipt(q, proof_id, user_sig, agent_sig, qh, at):
    return {'proof': proof_id, 'userSol': q['userSol'], 'pct': q['pct'], 'agentSol': q['agentSol'] if agent_sig else 0.0, 'totalSol': round(q['userSol'] + (q['agentSol'] if agent_sig else 0.0), 6),
            'auto': q['auto'], 'userSig': user_sig, 'agentSig': agent_sig, 'agentMissed': bool(q['auto'] and q['agentSol'] and not agent_sig), 'quote': qh, 'at': round(at)}
