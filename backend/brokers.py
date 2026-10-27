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


def personal(client_id):
    """A SnapTrade PERSONAL key (`PERS-…`): it reaches the key owner's OWN linked broker accounts — calls carry no userId / userSecret, and
    FEELESS opens it to the owner's (staff) wallets only. A commercial key registers one SnapTrade user per wallet instead."""
    return str(client_id or '').startswith('PERS-')


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


# 🔑 BRING YOUR OWN KEY — Alpaca (owner, 2026-10-24: "users add their own keys … fastest, easiest, won't charge nothing to start"): a free
# Alpaca account, no minimum, commission-free US stocks · ETFs · crypto; API keys are self-serve in its dashboard (paper keys at once, live after
# its ID check). The user pastes Key ID + Secret once; FEELESS seals them to their wallet (`seal`) and trades their own account with them.
ALPACA = {'live': 'https://api.alpaca.markets', 'paper': 'https://paper-api.alpaca.markets'}
ALPACA_SIGNUP = 'https://app.alpaca.markets/signup'


def alpaca_base(paper):
    return ALPACA['paper' if paper else 'live']


def alpaca_headers(key, secret):
    return {'APCA-API-KEY-ID': str(key or '').strip(), 'APCA-API-SECRET-KEY': str(secret or '').strip(), 'Accept': 'application/json'}


def alpaca_keys_ok(key, secret):
    """Shape check before any call (Alpaca key ids are 16–32 upper-case letters / digits; secrets 32–64 chars)."""
    k, s = str(key or '').strip(), str(secret or '').strip()
    return bool(re.match(r'^[A-Z0-9]{16,32}$', k)) and bool(re.match(r'^[A-Za-z0-9/+=_\-]{30,72}$', s))


def is_crypto(sym):
    return '/' in str(sym or '')


def alpaca_order(raw):
    """The ticket → Alpaca's POST /v2/orders body, or ValueError. Stocks / ETFs: Market by $ (notional, `day`) or shares, Limit by shares + price;
    crypto (`BTC/USD`): `gtc`. Same caps as every broker ticket (MAX_ORDER_USD)."""
    r = raw if isinstance(raw, dict) else {}
    sym = str(r.get('symbol') or '').strip().upper()
    if '/' not in sym and sym in ('BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'LTC', 'AVAX', 'LINK', 'SHIB', 'UNI'):
        sym = f'{sym}/USD'   # a bare crypto ticker → Alpaca's pair
    side, kind = str(r.get('action') or '').lower(), str(r.get('type') or 'Market').lower()
    if not SYMBOL.match(sym):
        raise ValueError('Type the ticker (AAPL, SPY, BTC …).')
    if side not in ('buy', 'sell') or kind not in ('market', 'limit'):
        raise ValueError('BUY or SELL · Market or Limit.')
    usd, units, price = _f(r.get('usd')), _f(r.get('units')), _f(r.get('price'))
    body = {'symbol': sym, 'side': side, 'type': kind, 'time_in_force': 'gtc' if is_crypto(sym) else 'day'}
    if kind == 'limit':
        if not (price > 0 and units > 0):
            raise ValueError('A limit order needs a price and a share count.')
        if price * units > MAX_ORDER_USD:
            raise ValueError(f'Max ${MAX_ORDER_USD:,} a ticket for now.')
        body.update(limit_price=str(round(price, 4)), qty=str(units))
    elif usd > 0:
        if not (1 <= usd <= MAX_ORDER_USD):
            raise ValueError(f'From $1 to ${MAX_ORDER_USD:,} a ticket.')
        body['notional'] = f'{usd:.2f}'
    elif units > 0:
        body['qty'] = str(units)
    else:
        raise ValueError('Set a $ amount or a share count.')
    return body


def alpaca_view(account, positions, paper):
    """Alpaca /v2/account + /v2/positions → one account in the building's shape (id 'alpaca')."""
    a = account or {}
    rows = []
    for p in positions or []:
        units, price, val, pnl = _num(p.get('qty')), _num(p.get('current_price')), _num(p.get('market_value')), _num(p.get('unrealized_pl'))
        rows.append({'ticker': p.get('symbol') or '?', 'name': None, 'units': units, 'price': price, 'value': round(val, 2), 'pnl': round(pnl, 2),
                     'pnlPct': round(_num(p.get('unrealized_plpc')) * 100, 2) if p.get('unrealized_plpc') is not None else None, 'kind': p.get('asset_class')})
    rows.sort(key=lambda x: -x['value'])
    return {'id': 'alpaca', 'broker': 'Alpaca' + (' · PAPER' if paper else ''), 'name': 'Your keys', 'number': str(a.get('account_number') or '')[-4:],
            'cash': round(_num(a.get('cash')), 2), 'buyingPower': round(_num(a.get('buying_power')), 2), 'value': round(_num(a.get('equity') or a.get('portfolio_value')), 2),
            'positions': rows, 'paper': bool(paper), 'status': a.get('status')}


# 🔑 BRING YOUR OWN KEY — Crypto.com Exchange (owner, 2026-10-26: "select usa providers like crypto.com … enter my api" ): the user makes an API key
# in their own Crypto.com Exchange account (Settings › API Keys, trading on, withdrawals OFF), pastes key + secret once; FEELESS checks it
# against private/user-balance, seals it to the wallet, and sends spot BUY / SELL to private/create-order. Signing (exchange-docs.crypto.com):
# HMAC-SHA256(secret, method + id + api_key + params-string + nonce), hex; the params string = sorted keys, each key then its value.
CDC_API = 'https://api.crypto.com/exchange/v1'
CDC_SIGNUP = 'https://crypto.com/exchange'


def cdc_keys_ok(key, secret):
    k, s = str(key or '').strip(), str(secret or '').strip()
    return bool(re.match(r'^[A-Za-z0-9_\-]{16,64}$', k)) and bool(re.match(r'^[A-Za-z0-9_\-]{16,96}$', s))


def cdc_params(obj, level=0):
    """Crypto.com's canonical params string (its reference algorithm): sorted keys, key + value, lists flattened, None → 'null'."""
    if level >= 3 or not isinstance(obj, dict):
        return str(obj)
    out = ''
    for k in sorted(obj):
        out += k
        v = obj[k]
        if v is None:
            out += 'null'
        elif isinstance(v, list):
            out += ''.join(cdc_params(x, level + 1) for x in v)
        else:
            out += str(v)
    return out


def cdc_signed(method, params, key, secret, nonce=None, req_id=1):
    """The signed JSON body for POST {CDC_API}/{method}."""
    nonce = int(nonce if nonce is not None else time.time() * 1000)
    params = params or {}
    payload = f'{method}{req_id}{key}{cdc_params(params)}{nonce}'
    sig = hmac.new(str(secret).encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {'id': req_id, 'method': method, 'api_key': key, 'params': params, 'nonce': nonce, 'sig': sig}


def cdc_order(raw):
    """The ticket → private/create-order params, or ValueError. Spot vs USD: Market BUY by $ (notional), Market SELL by units, Limit by units + price."""
    r = raw if isinstance(raw, dict) else {}
    sym = re.sub(r'[/_-]?USDT?$', '', str(r.get('symbol') or '').strip().upper())
    side, kind = str(r.get('action') or '').upper(), str(r.get('type') or 'Market').upper()
    if not re.match(r'^[A-Z0-9]{2,12}$', sym):
        raise ValueError('Type the coin (BTC, ETH, SOL, CRO …).')
    if side not in ('BUY', 'SELL') or kind not in ('MARKET', 'LIMIT'):
        raise ValueError('BUY or SELL · Market or Limit.')
    usd, units, price = _f(r.get('usd')), _f(r.get('units')), _f(r.get('price'))
    body = {'instrument_name': f'{sym}_USD', 'side': side, 'type': kind}
    if kind == 'LIMIT':
        if not (price > 0 and units > 0):
            raise ValueError('A limit order needs a price and an amount.')
        if price * units > MAX_ORDER_USD:
            raise ValueError(f'Max ${MAX_ORDER_USD:,} a ticket for now.')
        body.update(price=f'{price:g}', quantity=f'{units:g}')
    elif side == 'BUY' and usd > 0:
        if not (1 <= usd <= MAX_ORDER_USD):
            raise ValueError(f'From $1 to ${MAX_ORDER_USD:,} a ticket.')
        body['notional'] = f'{usd:.2f}'
    elif units > 0:
        body['quantity'] = f'{units:g}'
    else:
        raise ValueError('Market BUY by $ · SELL by the amount of coin.')
    return body


def cdc_caps(instruments):
    """public/get-instruments → what the exchange lists: spot vs USD, perpetuals (count, max leverage, the biggest names), dated futures."""
    rows = [r for r in (instruments or []) if isinstance(r, dict) and r.get('tradable', True)]
    spot = [r for r in rows if r.get('inst_type') == 'CCY_PAIR' and r.get('quote_ccy') in ('USD', 'USDC', 'USDT')]
    perps = [r for r in rows if r.get('inst_type') == 'PERPETUAL_SWAP']
    top = ('BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'CRO', 'SUI', 'LINK', 'ADA', 'AVAX')
    lev = lambda r: int(_num(r.get('max_leverage'))) or 0
    rank = lambda rs, key: sorted(rs, key=lambda r: (top.index(r.get('base_ccy')) if r.get('base_ccy') in top else 99, r.get(key) or ''))
    pick = lambda rs, key: rank(rs, key)[:8]
    # `all` = the FULL tradeable list (owner 2026-10-27: "full list of tradeables per provider") — base coin + its max leverage, big names first
    return {'spot': {'n': len(spot), 'top': [r.get('symbol') for r in pick(spot, 'symbol')], 'all': sorted({str(r.get('base_ccy') or '') for r in spot} - {''}, key=lambda b: (top.index(b) if b in top else 99, b))},
            'perps': {'n': len(perps), 'maxLev': max([lev(r) for r in perps] or [0]), 'top': [{'symbol': r.get('symbol'), 'lev': lev(r)} for r in pick(perps, 'symbol')],
                      'all': [{'base': r.get('base_ccy'), 'lev': lev(r)} for r in rank(perps, 'symbol') if r.get('base_ccy')]},
            'futures': {'n': sum(1 for r in rows if r.get('inst_type') == 'FUTURE')}}


def cdc_perp_order(raw, inst, mark):
    """A perps ticket on the user's OWN Crypto.com account → private/create-order params, or ValueError. Size = $ × leverage ÷ the mark,
    rounded DOWN to the instrument's quantity step; MARKET only. Crypto.com decides whether the account may trade perps (it refuses otherwise)."""
    r = raw if isinstance(raw, dict) else {}
    side = str(r.get('action') or '').upper(); usd, lev = _f(r.get('usd')), _f(r.get('lev')) or 1
    if side not in ('BUY', 'SELL'):
        raise ValueError('LONG (BUY) or SHORT (SELL).')
    mx = int(_num((inst or {}).get('max_leverage'))) or 1
    if not 1 <= lev <= mx:
        raise ValueError(f'Leverage runs 1× to {mx}× on {(inst or {}).get("symbol")}.')
    if not (1 <= usd <= MAX_ORDER_USD) or not (mark and mark > 0):
        raise ValueError(f'From $1 to ${MAX_ORDER_USD:,} of margin, with a live price.')
    step = _num((inst or {}).get('qty_tick_size')) or 0.0001
    qty = int((usd * lev / mark) / step) * step
    if qty <= 0:
        raise ValueError(f'Too small: the minimum step is {step:g} {(inst or {}).get("base_ccy") or ""}.')
    dec = max(0, len(f'{step:.10f}'.rstrip('0').split('.')[1]) if '.' in f'{step:.10f}'.rstrip('0') else 0)
    return {'instrument_name': (inst or {}).get('symbol'), 'side': side, 'type': 'MARKET', 'quantity': f'{qty:.{dec}f}'}


def cdc_view(res):
    """private/user-balance's result → one account in the building's shape (id 'cdc')."""
    d = ((res or {}).get('data') or [{}])[0] if isinstance((res or {}).get('data'), list) else {}
    rows = []
    for p in d.get('position_balances') or []:
        units, val = _num(p.get('quantity')), _num(p.get('market_value'))
        if units <= 0:
            continue
        rows.append({'ticker': p.get('instrument_name') or '?', 'name': None, 'units': units, 'price': round(val / units, 6) if units else None,
                     'value': round(val, 2), 'pnl': 0.0, 'pnlPct': None, 'kind': 'crypto'})
    rows.sort(key=lambda x: -x['value'])
    cash = next((x['value'] for x in rows if x['ticker'] in ('USD', 'USDC', 'USDT')), 0.0)
    return {'id': 'cdc', 'broker': 'Crypto.com', 'name': 'Your keys', 'number': '', 'cash': round(cash, 2),
            'buyingPower': round(_num(d.get('total_available_balance')), 2), 'value': round(_num(d.get('total_cash_balance')) or sum(x['value'] for x in rows), 2),
            'positions': rows, 'paper': False, 'status': 'ACTIVE'}


def seal_key_file(path):
    """The seal key FEELESS makes for itself when BROKER_SECRET_KEY is not set: 48 random bytes in a 0600 file beside the data (never printed,
    never in git). Returns the key string."""
    import os
    import secrets
    from pathlib import Path
    p = Path(path)
    if p.exists():
        return p.read_text().strip()
    k = secrets.token_urlsafe(48)
    p.write_text(k)
    os.chmod(p, 0o600)
    return k
