"""💳 AN AGENT PAYS FOR ITS OWN THINKING (owner 2026-10-30, W06): one model call = one USDC payment from that agent's own wallet (x402 `exact` on Solana), so its
model money is locked to it on-chain and no shared account can run dry for it. The provider answers 402 with a quote; we check it, build the payment, Circle signs for
this agent's wallet only, and the provider pays the network fee. Ceilings: never more than MAX_CALL_USD a call, never past the task cap, and RESERVE_USD always stays
in the wallet. Pure, tested (tests/test_agent_pay.py); the network sits in feecat_service._wallet_call + reputation's /internal/agent-x402-pay."""
import base64
import json
import secrets

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction

import cat_fund as _cf

PROVIDER = 'https://ask.singitai.app/v1/chat/completions'
SOLANA = 'solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp'
MEMO_PROGRAM = 'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr'
MAX_CALL_USD = 0.25
RESERVE_USD = 0.10    # the same 10 cents every agent stops short of
USDC_SCALE = 1_000_000
# the picks this provider lists under another name (its /v1/models, checked live 2026-10-31: no claude-haiku-5.5 → the nearest Haiku)
MODEL_MAP = {'gpt-6.1-terra': 'gpt-6-luna', 'gpt-6.1-sol': 'gpt-6-luna', 'claude-haiku-5.5': 'claude-haiku-4.5',
             'nemotron-3-ultra-550b-a55b': 'nvidia-nemotron-3-ultra-550b-a55b'}
FALLBACK_MODEL = 'deepseek-v4.1-flash'   # the provider's own default — first paid call answered with it 2026-10-31 ($0.002)
FREE_URL_MODEL = 'free/deepseek-v4.1-flash'   # its free tier: no wallet, 20 calls a day, ≤ 400 tokens, ≤ 4,000 chars
FREE_MAX_TOKENS, FREE_MAX_CHARS = 400, 4000


def provider_model(model):
    """'anthropic/claude-haiku-5.5' → this provider's id (an OpenRouter ':free' tag dropped)."""
    m = str(model or '').split('/')[-1].split(':')[0]
    return MODEL_MAP.get(m, m)


def free_messages(messages):
    """Fit a call into the free tier's 4,000 chars: the system prompt keeps its head, the last message its tail."""
    ms = [dict(m) for m in messages or []]
    while sum(len(str(m.get('content') or '')) for m in ms) > FREE_MAX_CHARS and ms:
        big = max(ms, key=lambda m: len(str(m.get('content') or '')))
        c = str(big.get('content') or '')
        over = sum(len(str(m.get('content') or '')) for m in ms) - FREE_MAX_CHARS
        big['content'] = c[:max(0, len(c) - over - 1)] if big.get('role') == 'system' else c[over + 1:]
        if not big['content']:
            ms.remove(big)
    return ms


def pick_quote(header, ceiling_usd):
    """The base64 PAYMENT-REQUIRED header → (document, the Solana USDC `exact` entry). Raises ValueError on anything we must not pay."""
    try:
        doc = json.loads(base64.b64decode(str(header) + '=='))
    except Exception:
        raise ValueError('no readable quote')
    e = next((x for x in doc.get('accepts') or [] if x.get('scheme') == 'exact' and x.get('network') == SOLANA and x.get('asset') == _cf.USDC_MINT), None)
    if not e:
        raise ValueError('no Solana USDC quote')
    amount = int(e.get('amount') or 0)
    if amount <= 0 or amount > int(min(MAX_CALL_USD, float(ceiling_usd or 0)) * USDC_SCALE):
        raise ValueError(f'quote ${amount / USDC_SCALE:g} is over the limit for this call')
    if not (e.get('extra') or {}).get('feePayer') or not e.get('payTo'):
        raise ValueError('quote has no fee payer or recipient')
    return doc, e


def build_payment(wallet, entry, blockhash):
    """The unsigned payment: compute limit, compute price, one USDC transfer to `payTo`, one memo, the provider's fee payer. → base64."""
    me, to, fee = Pubkey.from_string(wallet), Pubkey.from_string(entry['payTo']), Pubkey.from_string(entry['extra']['feePayer'])
    amount = int(entry['amount'])
    if entry.get('asset') != _cf.USDC_MINT or amount <= 0 or amount > int(MAX_CALL_USD * USDC_SCALE):
        raise ValueError('That payment is not allowed.')
    if fee == me:
        raise ValueError('The agent wallet must not pay the network fee.')
    memo = str((entry.get('extra') or {}).get('memo') or secrets.token_hex(16)).encode()[:256]
    ixs = [set_compute_unit_limit(30_000), set_compute_unit_price(1), _cf._send_usdc(me, to, amount), Instruction(Pubkey.from_string(MEMO_PROGRAM), memo, [AccountMeta(me, True, False)])]
    msg = MessageV0.try_compile(fee, ixs, [], Hash.from_string(blockhash))
    return base64.b64encode(bytes(VersionedTransaction.populate(msg, [Signature.default()] * msg.header.num_required_signatures))).decode()


def payment_header(doc, entry, signed_b64):
    """The signed payment as the x402 v2 PaymentPayload, base64."""
    return base64.b64encode(json.dumps({'x402Version': int(doc.get('x402Version') or 2), 'resource': doc.get('resource'), 'accepted': entry, 'payload': {'transaction': signed_b64}}).encode()).decode()
