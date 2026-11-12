"""🎯 REAL BIDS ON KALSHI (owner 2026-11-11: "kalshi signed in with $10 on it, they should be able to bid"). The only door that turns a PoB into a
real-money order. A topic PoB's two minds also read the live Kalshi markets for that topic; when BOTH pick the same market and the same side, this
makes a ticket. The order goes from the owner's own Kalshi API key to his own Kalshi account: FEELESS never holds his money.

Every guard must pass or nothing is sent (`check`):
  · the owner switched the door on for this agent (off by default), and saved his Kalshi API key (key id + RSA private key)
  · mode 'approve' (default) waits for his tap on the ticket; 'auto' sends it inside the caps by itself
  · a LIMIT order at the ask it showed, never a market order; the price is re-read just before sending and refused if it moved past the limit
  · per bid ≤ his cap (default $1, hard max $5) · per day ≤ his daily cap (default $3, hard max $20)
  · both minds agree on the market and the side, each at or above his minimum confidence (default 65)
  · price between 5¢ and 95¢ · the market is active and closes more than 10 minutes from now
  · never the same market twice in 24 h · his Kalshi balance after the bid stays at or above his floor (default $2)
Pure and tested (`tests/test_kalshi_bid.py`): the service holds the store, the clock and the network.
"""
import base64
import re
import time
import uuid

BASE = 'https://api.elections.kalshi.com/trade-api/v2'
PATH = '/trade-api/v2'
HARD_BID, HARD_DAY = 5.0, 20.0
DEFAULT = {'on': False, 'mode': 'approve', 'bidUsd': 1.0, 'dayUsd': 3.0, 'floorUsd': 2.0, 'minConf': 65}
MIN_PRICE, MAX_PRICE = 0.05, 0.95
CLOSE_GAP_S = 600
SAME_MARKET_S = 86400
LIST_MAX = 12
# league words → Kalshi's game series (read live 2026-11-11: /markets?series_ticker=KXNBAGAME answered with real games)
SERIES = ((r'\b(nba|basketball|lakers|celtics|knicks|warriors|pacers|wizards|bulls|heat|nets|bucks|suns|nuggets|mavericks|thunder|spurs|magic|hawks|76ers|sixers|raptors|cavaliers|cavs|pistons|hornets|grizzlies|pelicans|jazz|kings|clippers|rockets|timberwolves|blazers)\b', 'KXNBAGAME'),
          (r'\b(nfl|football|chiefs|bills|eagles|cowboys|49ers|niners|ravens|packers|lions|bengals|steelers|jets|giants|patriots|dolphins|broncos|chargers|raiders|seahawks|rams|vikings|bears|saints|falcons|buccaneers|panthers|commanders|cardinals|texans|colts|jaguars|titans|browns)\b', 'KXNFLGAME'),
          (r'\b(nhl|hockey|bruins|rangers|maple leafs|canadiens|penguins|capitals|oilers|avalanche|lightning|panthers|stars|golden knights|kraken|flames|canucks|jets|wild|blues|predators|devils|islanders|flyers|hurricanes|senators|sabres|red wings|blackhawks|ducks|sharks|kings|blue jackets|utah)\b', 'KXNHLGAME'),
          (r'\b(mlb|baseball|yankees|dodgers|red sox|mets|cubs|braves|astros|phillies|padres|giants|mariners|orioles|guardians|twins|rays|blue jays|brewers|cardinals|reds|pirates|royals|tigers|white sox|angels|athletics|rockies|marlins|nationals|diamondbacks|rangers)\b', 'KXMLBGAME'),
          (r'\b(ncaaf|college football|cfb)\b', 'KXNCAAFGAME'),
          (r'\b(ncaab|college basketball|march madness)\b', 'KXNCAAMBGAME'))
KEY_RE = re.compile(r'^\s*([0-9A-Za-z-]{20,64}?)\s*(-----BEGIN (?:RSA )?PRIVATE KEY-----)\s*([A-Za-z0-9+/=\s]{40,8000}?)\s*(-----END (?:RSA )?PRIVATE KEY-----)\s*$', re.S)


def cfg(raw):
    """The owner's door settings, clamped to the hard limits. Unknown or missing values fall back to the safe default."""
    r = raw if isinstance(raw, dict) else {}
    def num(k, lo, hi):
        try:
            return round(max(lo, min(hi, float(r.get(k, DEFAULT[k])))), 2)
        except (TypeError, ValueError):
            return DEFAULT[k]
    return {'on': r.get('on') is True, 'mode': 'auto' if r.get('mode') == 'auto' else 'approve', 'bidUsd': num('bidUsd', 0.05, HARD_BID),
            'dayUsd': num('dayUsd', 0.05, HARD_DAY), 'floorUsd': num('floorUsd', 0, 10000), 'minConf': int(num('minConf', 50, 100))}


def split_key(secret):
    """'<key id> <PEM>' (pasted on one line or many) → (key id, a clean PEM), or (None, None). The PEM is rebuilt with real line breaks."""
    m = KEY_RE.match(str(secret or ''))
    if not m:
        return None, None
    body = re.sub(r'\s+', '', m.group(3))
    return m.group(1), '\n'.join([m.group(2)] + [body[i:i + 64] for i in range(0, len(body), 64)] + [m.group(4)]) + '\n'


def sign(pem, method, path, ts_ms):
    """Kalshi's request signature over timestamp + METHOD + path (no query), base64: RSA-PSS (SHA-256, salt = digest length) for an RSA key,
    plain Ed25519 for an Ed25519 key (Kalshi's default key type now; the owner's key is one, 2026-11-11)."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519, padding
    key = serialization.load_pem_private_key(pem.encode(), password=None)
    msg = f'{ts_ms}{method.upper()}{path.split("?")[0]}'.encode()
    sig = key.sign(msg) if isinstance(key, ed25519.Ed25519PrivateKey) else key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())
    return base64.b64encode(sig).decode()


def headers(key_id, pem, method, path, now=None):
    ts = str(int((now or time.time()) * 1000))
    return {'KALSHI-ACCESS-KEY': key_id, 'KALSHI-ACCESS-TIMESTAMP': ts, 'KALSHI-ACCESS-SIGNATURE': sign(pem, method, PATH + path, ts), 'Content-Type': 'application/json'}


def series_for(topic):
    t = str(topic or '').lower()
    return [s for rx, s in SERIES if re.search(rx, t)]


def price_of(m, side):
    """The ask to buy that side, in dollars (Kalshi sends '0.4000' strings; older rows send cents)."""
    for k in (f'{side}_ask_dollars',):
        try:
            v = float(m.get(k))
            if v > 0:
                return round(v, 4)
        except (TypeError, ValueError):
            pass
    try:
        c = float(m.get(f'{side}_ask'))
        return round(c / 100, 4) if c > 0 else None
    except (TypeError, ValueError):
        return None


def _ts(iso):
    try:
        return time.mktime(time.strptime(str(iso)[:19], '%Y-%m-%dT%H:%M:%S')) - time.timezone
    except (TypeError, ValueError):
        return 0


def relevant(markets, topic, now=None, n=LIST_MAX):
    """Open markets whose title shares a word with the topic (team names), soonest first. Only ones that could take a bid."""
    words = {w for w in re.findall(r'[a-z]{4,}', str(topic or '').lower()) if w not in ('game', 'games', 'tonight', 'today', 'pick', 'picks', 'best', 'parlay', 'parlays', 'bets', 'bidding', 'choices', 'with')}
    now = now or time.time()
    live = [m for m in markets or [] if m.get('status') in ('active', 'open') and _ts(m.get('close_time')) - now > CLOSE_GAP_S]
    hit = [m for m in live if any(w in f"{m.get('title') or ''} {m.get('yes_sub_title') or ''} {m.get('subtitle') or ''}".lower() for w in words)]
    return sorted(hit or live, key=lambda m: _ts(m.get('close_time')))[:n]   # Kalshi titles name cities ("Kansas City wins"); a nickname that matches nothing gets the league's soonest games


def line(m):
    ya, na = price_of(m, 'yes'), price_of(m, 'no')
    return f"{m.get('ticker')} · {m.get('title')} · YES {ya if ya is not None else '—'} / NO {na if na is not None else '—'} (dollars per contract that pays $1) · closes {str(m.get('close_time'))[:16]}Z"


def brief(markets):
    if not markets:
        return ''
    return ('\nLIVE KALSHI MARKETS (real money: the owner bids only if BOTH of you pick the same ticker and side). To back one, add '
            '"kalshi": {"ticker": "<ticker>", "side": "yes|no"} to that pick:\n' + '\n'.join(line(m) for m in markets))


def chosen(calls, ids):
    """The market both minds backed: same ticker, same side, both confident enough later in `check`. → {ticker, side, conf: [a, b], why} or None."""
    if len(calls) < 2:
        return None
    def picks(c):
        out = {}
        for p in c.get('picks') or []:
            k = p.get('kalshi') if isinstance(p.get('kalshi'), dict) else None
            t, s = str((k or {}).get('ticker') or '').strip(), str((k or {}).get('side') or '').lower()
            if t in ids and s in ('yes', 'no') and (t, s) not in out:
                out[(t, s)] = p
        return out
    a, b = picks(calls[0]), picks(calls[1])
    both = [k for k in a if k in b]
    if not both:
        return None
    t, s = max(both, key=lambda k: min(a[k].get('confidence') or 0, b[k].get('confidence') or 0))
    return {'ticker': t, 'side': s, 'conf': [a[(t, s)].get('confidence') or 0, b[(t, s)].get('confidence') or 0], 'why': [a[(t, s)].get('why') or '', b[(t, s)].get('why') or '']}


def spent_today(bids, now=None):
    now = now or time.time()
    return round(sum(float(b.get('usd') or 0) for b in bids or [] if b.get('status') in ('sent', 'filled', 'resting') and now - float(b.get('at') or 0) < 86400), 2)


def check(c, market, pick, bids, balance_usd, now=None):
    """→ (ok, why, count, price). Every guard in the module note; the first that fails is the reason shown to the owner."""
    now = now or time.time(); c = cfg(c)
    if not c['on']:
        return False, 'Real Kalshi bids are off for this agent.', 0, None
    if not market or market.get('ticker') != (pick or {}).get('ticker'):
        return False, 'That market is not open on Kalshi any more.', 0, None
    if market.get('status') not in ('active', 'open') or _ts(market.get('close_time')) - now <= CLOSE_GAP_S:
        return False, 'That market closes in under 10 minutes, or is closed.', 0, None
    if min(pick.get('conf') or [0]) < c['minConf']:
        return False, f"Both minds need {c['minConf']}% confidence; they had {' and '.join(str(x) for x in pick.get('conf') or [])}%.", 0, None
    price = price_of(market, pick.get('side'))
    if price is None or not MIN_PRICE <= price <= MAX_PRICE:
        return False, 'Its price is outside 5¢ to 95¢, so it is not bid.', 0, price
    if any(b.get('ticker') == pick['ticker'] and now - float(b.get('at') or 0) < SAME_MARKET_S and b.get('status') != 'refused' for b in bids or []):
        return False, 'It already bid on this market in the last 24 hours.', 0, price
    left = round(c['dayUsd'] - spent_today(bids, now), 2)
    budget = min(c['bidUsd'], left)
    count = int(budget // price)
    if count < 1:
        return False, f"Today's cap of ${c['dayUsd']:.2f} is used up." if left < price else f"${c['bidUsd']:.2f} buys no contract at {price:.2f}.", 0, price
    usd = round(count * price, 2)
    if balance_usd is None:
        return False, 'Could not read the Kalshi balance, so nothing was sent.', 0, price
    if balance_usd - usd < c['floorUsd']:
        return False, f"Your Kalshi balance (${balance_usd:.2f}) would fall under your ${c['floorUsd']:.2f} floor.", 0, price
    return True, f"{count} × {pick['side'].upper()} at {price:.2f} = ${usd:.2f}", count, price


def order(pick, count, price, client_id=None):
    """A LIMIT buy at the shown ask (cents), never a market order."""
    cents = max(1, min(99, int(round(price * 100))))
    return {'ticker': pick['ticker'], 'action': 'buy', 'side': pick['side'], 'count': int(count), 'type': 'limit',
            ('yes_price' if pick['side'] == 'yes' else 'no_price'): cents, 'client_order_id': client_id or str(uuid.uuid4())}


def ticket(pick, market, folder_id, now=None):
    return {'id': 'kb' + uuid.uuid4().hex[:10], 'ticker': pick['ticker'], 'side': pick['side'], 'title': market.get('title') or pick['ticker'],
            'conf': pick.get('conf'), 'why': pick.get('why'), 'price': price_of(market, pick['side']), 'folder': folder_id, 'at': round(now or time.time()), 'status': 'waiting'}


# 🌐 the network (the service passes one pooled httpx client)
async def markets_for(http, topic):
    rows = []
    for s in series_for(topic)[:2]:
        r = await http.get(f'{BASE}/markets', params={'series_ticker': s, 'status': 'open', 'limit': 200})
        if r.status_code == 200:
            rows += r.json().get('markets') or []
    return relevant(rows, topic)


async def market(http, ticker):
    r = await http.get(f'{BASE}/markets/{ticker}')
    return (r.json() or {}).get('market') if r.status_code == 200 else None


async def balance(http, key_id, pem):
    r = await http.get(f'{BASE}/portfolio/balance', headers=headers(key_id, pem, 'GET', '/portfolio/balance'))
    if r.status_code != 200:
        raise RuntimeError(f'Kalshi said {r.status_code}: {r.text[:160]}')
    return round(float(r.json().get('balance') or 0) / 100, 2)


async def place(http, key_id, pem, body):
    r = await http.post(f'{BASE}/portfolio/orders', json=body, headers=headers(key_id, pem, 'POST', '/portfolio/orders'))
    if r.status_code not in (200, 201):
        raise RuntimeError(f'Kalshi refused the order ({r.status_code}): {r.text[:200]}')
    return (r.json() or {}).get('order') or {}
