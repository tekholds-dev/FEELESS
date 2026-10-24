"""🏦 THE BROKERAGE — a user's OWN broker account (Webull · Coinbase · Kraken · Alpaca · E*TRADE … through SnapTrade), linked to their
Familia wallet, read live and traded from FEELESS. Pure + tested (`tests/test_brokers.py`); the network lives in reputation_service.

How it works (owner, 2026-10-24: "find easy setup brokers … smooth for users to hook up a broker via their crypto wallet in fam, log in and get
to it, see all data in the buildings"; DECISIONS #9):
  1. 🔗 LINK — the user is signed in to Familia with their wallet (the signed session). FEELESS registers ONE SnapTrade user per primary
     wallet (`user_id`) and opens SnapTrade's Connection Portal: the user logs in to THEIR broker there (FEELESS never sees a broker password).
  2. 🔐 FEELESS keeps only SnapTrade's per-user secret, ENCRYPTED at rest (`seal` / `unseal`, Fernet with BROKER_SECRET_KEY) — unlink deletes
     the SnapTrade user and every connection.
  3. 📊 READ — accounts, cash, buying power, positions (live value + P&L) → the 🏦 building + YOUR MONEY.
  4. 🎟 TRADE — stocks / ETFs / crypto BUY / SELL (Market by $ or by units, or Limit), each order confirmed on screen and checked here
     (`order_body`: the account is the user's, size within MAX_ORDER_USD, a known action / type) before SnapTrade sends it to the broker.
Signing (docs.snaptrade.com/docs/request-signatures): HMAC-SHA256 with the consumer key over the canonical JSON {content, path, query}
(sorted keys, no whitespace), Base64, in the `Signature` header; `clientId` + `timestamp` ride the query.
"""
import base64
import hashlib
import hmac
import json
import re
import time
from urllib.parse import urlencode

from fnum import nan_safe as _f

API = 'https://api.snaptrade.com/api/v1'
MAX_ORDER_USD = 2500          # one ticket while it is new (owner can raise it)
ACTIONS = ('BUY', 'SELL')
TYPES = ('Market', 'Limit')
SYMBOL = re.compile(r'^[A-Z0-9][A-Z0-9.\-/]{0,14}$')


def keys(env):
    """(client id, consumer key) or (None, None) — trading opens when both are set."""
    c, k = str((env or {}).get('SNAPTRADE_CLIENT_ID') or '').strip(), str((env or {}).get('SNAPTRADE_CONSUMER_KEY') or '').strip()
    return (c, k) if c and k else (None, None)


def user_id(primary):
    """The one SnapTrade user per FEELESS primary wallet (stable, no PII)."""
    return 'fl-' + hashlib.sha256(f'feeless-broker:{primary}'.encode()).hexdigest()[:32]


def signed(method, path, query, body, client_id, consumer_key, now=None):
    """→ (url, headers) for one SnapTrade call. `query` = dict of the call's own params (clientId + timestamp are added here)."""
    q = {**(query or {}), 'clientId': client_id, 'timestamp': str(int(now or time.time()))}
    qs = urlencode(q)
    content = body if body not in (None, {}) else None
    sig_obj = {'content': content, 'path': f'/api/v1{path}', 'query': qs}
    raw = json.dumps(sig_obj, separators=(',', ':'), sort_keys=True)
    sig = base64.b64encode(hmac.new(consumer_key.encode(), raw.encode(), hashlib.sha256).digest()).decode()
    return f'{API}{path}?{qs}', {'Signature': sig, 'Content-Type': 'application/json', 'Accept': 'application/json'}


def _fernet(env):
    from cryptography.fernet import Fernet
    k = str((env or {}).get('BROKER_SECRET_KEY') or '').strip()
    if not k:
        raise RuntimeError('BROKER_SECRET_KEY is not set — FEELESS will not store a broker secret in the clear.')
    key = base64.urlsafe_b64encode(hashlib.sha256(k.encode()).digest())
    return Fernet(key)


def seal(secret, env):
    return _fernet(env).encrypt(str(secret).encode()).decode()


def unseal(token, env):
    return _fernet(env).decrypt(str(token).encode()).decode()


def order_body(raw, accounts):
    """The ticket → SnapTrade's /trade/place body, or ValueError. `accounts` = the user's own account ids (from /accounts)."""
    r = raw if isinstance(raw, dict) else {}
    acct, sym = str(r.get('accountId') or ''), str(r.get('symbol') or '').strip().upper()
    action, kind = str(r.get('action') or '').upper(), str(r.get('type') or 'Market')
    if acct not in (accounts or ()):
        raise ValueError('Pick one of YOUR linked accounts.')
    if not SYMBOL.match(sym):
        raise ValueError('Type the ticker (AAPL, SPY, BTC …).')
    if action not in ACTIONS or kind not in TYPES:
        raise ValueError('BUY or SELL · Market or Limit.')
    usd, units, price = _f(r.get('usd')), _f(r.get('units')), _f(r.get('price'))
    body = {'account_id': acct, 'action': action, 'symbol': sym, 'universal_symbol_id': None, 'order_type': kind, 'time_in_force': 'Day',
            'price': None, 'stop': None, 'units': None, 'notional_value': None}
    if kind == 'Limit':
        if not (price > 0 and units > 0):
            raise ValueError('A limit order needs a price and a share count.')
        if price * units > MAX_ORDER_USD:
            raise ValueError(f'Max ${MAX_ORDER_USD:,} a ticket for now.')
        body.update(price=round(price, 4), units=units)
    elif usd > 0:
        if not (1 <= usd <= MAX_ORDER_USD):
            raise ValueError(f'From $1 to ${MAX_ORDER_USD:,} a ticket.')
        body['notional_value'] = round(usd, 2)
    elif units > 0:
        body['units'] = units
    else:
        raise ValueError('Set a $ amount or a share count.')
    return body


def _num(v):
    x = _f(v)
    return x if x == x else 0.0


def view(accounts, positions, balances):
    """SnapTrade rows → the building's view: each account (broker, name, cash, buying power, value) + its positions (ticker, units, price,
    value, P&L, P&L %), and the totals. positions / balances = {account_id: rows}."""
    out, tv, tp = [], 0.0, 0.0
    for a in accounts or []:
        aid = a.get('id')
        bal = balances.get(aid) or []
        cash = sum(_num(b.get('cash')) for b in bal if isinstance(b, dict))
        bp = sum(_num(b.get('buying_power')) for b in bal if isinstance(b, dict))
        rows = []
        for p in positions.get(aid) or []:
            sym = ((p.get('symbol') or {}).get('symbol') or {})
            tick = sym.get('symbol') if isinstance(sym, dict) else str(sym or '')
            units, price, cost = _num(p.get('units')), _num(p.get('price')), _num(p.get('average_purchase_price'))
            val = units * price; pnl = _num(p.get('open_pnl')) if p.get('open_pnl') is not None else (val - units * cost if cost > 0 else 0.0)
            rows.append({'ticker': tick or '?', 'name': (sym.get('description') if isinstance(sym, dict) else None), 'units': units, 'price': price,
                         'value': round(val, 2), 'pnl': round(pnl, 2), 'pnlPct': round(pnl / (units * cost) * 100, 2) if cost > 0 and units else None,
                         'kind': ((sym.get('type') or {}).get('code') if isinstance(sym, dict) else None)})
        rows.sort(key=lambda x: -x['value'])
        value = _num(((a.get('balance') or {}).get('total') or {}).get('amount')) or round(cash + sum(x['value'] for x in rows), 2)
        tv += value; tp += sum(x['pnl'] for x in rows)
        out.append({'id': aid, 'broker': a.get('institution_name') or (a.get('meta') or {}).get('institution_name') or 'Broker', 'name': a.get('name') or 'Account',
                    'number': str(a.get('number') or '')[-4:], 'cash': round(cash, 2), 'buyingPower': round(bp, 2), 'value': round(value, 2), 'positions': rows})
    return {'accounts': out, 'value': round(tv, 2), 'pnl': round(tp, 2)}
