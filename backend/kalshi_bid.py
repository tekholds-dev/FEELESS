"""🎯 REAL BIDS ON KALSHI (owner 2026-11-11: "kalshi signed in with $10 on it, they should be able to bid"). The only door that turns a PoB into a
real-money order. A topic PoB's two minds also read the live Kalshi markets for that topic; when BOTH pick the same market and the same side, this
makes a ticket. The order goes from the owner's own Kalshi API key to his own Kalshi account: FEELESS never holds his money.

Every guard must pass or nothing is sent (`check`):
  · the owner saved his Kalshi API key (key id + RSA private key) on this agent — there is no separate On switch (owner 2026-11-15: "i shouldnt
    have to cut on pob or kalshi"): a PoB HE asks for (main desk or proof folder) bids at once; AUTO is the one switch, and only lets his
    scheduled auto runs bid by themselves too (`sends_now`)
  · a LIMIT order at the ask it showed, never a market order; the price is re-read just before sending and refused if it moved past the limit
  · per bid ≤ his cap (default $1, hard max $5) · per day ≤ his daily cap (default $3, hard max $20)
  · both minds agree on the market and the side, each at or above his minimum confidence (default 65)
  · price between 5¢ and 95¢ · the market is active and closes more than 10 minutes from now
  · never the same market twice in 24 h · his Kalshi balance after the bid stays at or above his floor (default $2)
Pure and tested (`tests/test_kalshi_bid.py`): the service holds the store, the clock and the network.
"""
import asyncio
import base64
import calendar
import re
import time
import uuid

BASE = 'https://api.elections.kalshi.com/trade-api/v2'
PATH = '/trade-api/v2'
HARD_BID, HARD_DAY = 5.0, 20.0
DEFAULT = {'mode': 'approve', 'bidUsd': 1.0, 'dayUsd': 3.0, 'floorUsd': 2.0, 'minConf': 65}
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
    return {'mode': 'auto' if r.get('mode') == 'auto' else 'approve', 'bidUsd': num('bidUsd', 0.05, HARD_BID),
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
        return calendar.timegm(time.strptime(str(iso)[:19], '%Y-%m-%dT%H:%M:%S'))   # UTC; mktime - timezone was an hour off in summer time
    except (TypeError, ValueError):
        return 0


# 🏷 KALSHI NAMES A TEAM BY ITS CITY ("Dallas wins", "Los Angeles L"), read live 2026-11-15. A topic says "Mavericks vs Celtics":
# the nickname maps to Kalshi's own label, so a PoB sees ITS game only (a Mavs PoB was shown Lakers–Suns and Hornets–Clippers before this).
_T = lambda s: dict(x.split('=') for x in s.split(','))
TEAM_LABEL = {
    'KXNBAGAME': _T('hawks=Atlanta,nets=Brooklyn,celtics=Boston,hornets=Charlotte,bulls=Chicago,cavaliers=Cleveland,cavs=Cleveland,mavericks=Dallas,mavs=Dallas,nuggets=Denver,pistons=Detroit,warriors=Golden State,'
                    'rockets=Houston,pacers=Indiana,clippers=Los Angeles C,lakers=Los Angeles L,grizzlies=Memphis,heat=Miami,bucks=Milwaukee,timberwolves=Minnesota,wolves=Minnesota,pelicans=New Orleans,knicks=New York,'
                    'thunder=Oklahoma City,magic=Orlando,76ers=Philadelphia,sixers=Philadelphia,suns=Phoenix,blazers=Portland,trail blazers=Portland,kings=Sacramento,spurs=San Antonio,raptors=Toronto,jazz=Utah,wizards=Washington'),
    'KXNFLGAME': _T('cardinals=Arizona,falcons=Atlanta,ravens=Baltimore,bills=Buffalo,panthers=Carolina,bears=Chicago,bengals=Cincinnati,browns=Cleveland,cowboys=Dallas,broncos=Denver,lions=Detroit,packers=Green Bay,'
                    'texans=Houston,colts=Indianapolis,jaguars=Jacksonville,chiefs=Kansas City,chargers=Los Angeles C,rams=Los Angeles R,raiders=Las Vegas,dolphins=Miami,vikings=Minnesota,patriots=New England,saints=New Orleans,'
                    'giants=New York G,jets=New York J,eagles=Philadelphia,steelers=Pittsburgh,seahawks=Seattle,49ers=San Francisco,niners=San Francisco,buccaneers=Tampa Bay,bucs=Tampa Bay,titans=Tennessee,commanders=Washington'),
    'KXNHLGAME': _T('ducks=Anaheim,bruins=Boston,sabres=Buffalo,hurricanes=Carolina,blue jackets=Columbus,flames=Calgary,blackhawks=Chicago,avalanche=Colorado,stars=Dallas,red wings=Detroit,oilers=Edmonton,panthers=Florida,'
                    'kings=Los Angeles,wild=Minnesota,canadiens=Montreal,devils=New Jersey,predators=Nashville,islanders=New York I,rangers=New York R,senators=Ottawa,flyers=Philadelphia,penguins=Pittsburgh,kraken=Seattle,'
                    'sharks=San Jose,blues=St. Louis,lightning=Tampa Bay,maple leafs=Toronto,leafs=Toronto,utah=Utah,canucks=Vancouver,golden knights=Vegas,jets=Winnipeg,capitals=Washington'),
    'KXMLBGAME': _T('diamondbacks=Arizona,braves=Atlanta,orioles=Baltimore,red sox=Boston,cubs=Chicago C,white sox=Chicago WS,reds=Cincinnati,guardians=Cleveland,rockies=Colorado,tigers=Detroit,astros=Houston,royals=Kansas City,'
                    'angels=Los Angeles A,dodgers=Los Angeles D,marlins=Miami,brewers=Milwaukee,twins=Minnesota,mets=New York M,yankees=New York Y,athletics=Athletics,phillies=Philadelphia,pirates=Pittsburgh,padres=San Diego,'
                    'giants=San Francisco,mariners=Seattle,cardinals=St. Louis,rays=Tampa Bay,rangers=Texas,blue jays=Toronto,nationals=Washington'),
}
_GAME_RE = re.compile(r'the (.+?) vs (.+?) (?:pro |nhl |mlb |men|women|college|game)', re.I)


def teams_in(topic, series=None):
    """The Kalshi labels a topic names: its nicknames mapped, plus any Kalshi city label written out. Pure."""
    t = f" {re.sub(r'[^a-z0-9. ]+', ' ', str(topic or '').lower())} "; at = {}
    for s, table in TEAM_LABEL.items():
        if series and s not in series:
            continue
        for nick, label in table.items():
            i = min([x for x in (t.find(f' {nick} '), t.find(f' {label.lower()} ')) if x >= 0], default=-1)
            if i >= 0 and (label not in at or i < at[label]):
                at[label] = i
    return sorted(at, key=lambda k: (at[k], k))   # in the order the topic names them


def game_of(m):
    """The two labels of the game a market is on, from its rules ("the Dallas vs Boston Pro Basketball game"). Pure."""
    g = _GAME_RE.search(str(m.get('rules_primary') or ''))
    return {g.group(1).strip(), g.group(2).strip()} if g else {str(m.get('yes_sub_title') or '').strip()}


# ⏱ ALREADY-RAN GUARD (owner 2026-11-15 'mavs already playing'): a game ESPN shows live or over is never offered for a bid. A game not on
# today's ESPN board counts as not started only when Kalshi expects it to finish more than 6 h from now. Unsure → not offered.
ESPN_OF = {'KXNBAGAME': 'nba', 'KXNFLGAME': 'nfl', 'KXNHLGAME': 'nhl', 'KXMLBGAME': 'mlb', 'KXNCAAFGAME': 'cfb', 'KXNCAAMBGAME': 'cbb'}
AHEAD_S = 6 * 3600


def _hit(team, label, series):
    return TEAM_LABEL.get(series, {}).get(str(team.get('short') or '').lower()) == label or str(team.get('name') or '').startswith(label)


def _start(iso):
    """ESPN's start time ('2026-11-15T23:00Z') → unix seconds, 0 when unreadable (so an unreadable time never counts as not started)."""
    m = re.match(r'(\d{4}-\d\d-\d\dT\d\d:\d\d)', str(iso or ''))
    return _ts(m.group(1) + ':00') if m else 0


def not_started(m, games, now=None):
    """True only when the market's game is sure not to have begun. Pure."""
    now = now or time.time(); labels = game_of(m); series = str(m.get('ticker') or '').split('-')[0]
    if len(labels) == 2:
        for g in games or []:
            ts = g.get('teams') or []
            if len(ts) == 2 and all(any(_hit(t, lab, series) for t in ts) for lab in labels):
                return g.get('state') == 'pre' and _start(g.get('at')) > now   # ESPN still says 'pre' a few minutes past tip-off: the clock decides too
    return _ts(m.get('occurrence_datetime')) - now > AHEAD_S


async def unstarted(http, m):
    """The send-time re-check: ESPN's board read again right before an order goes out. Any failure → False (nothing is sent)."""
    try:
        import proof_tools as _pt
        s = str((m or {}).get('ticker') or '').split('-')[0]
        b = await _pt.sport_board(http, ESPN_OF[s]) if s in ESPN_OF else {}
        return not_started(m, (b or {}).get('games') or [])
    except Exception:   # noqa: BLE001 — unsure is a refusal
        return False


def relevant(markets, topic, now=None, n=LIST_MAX, series=None):
    """Open markets that could take a bid, soonest first. A topic that names teams gets ONLY their games (two teams: the game between them);
    a topic with no team ("best nba picks tonight") gets the league's soonest games. A named team Kalshi does not list → none, never another game."""
    now = now or time.time()
    live = [m for m in markets or [] if m.get('status') in ('active', 'open') and _ts(m.get('close_time')) - now > CLOSE_GAP_S]
    named = teams_in(topic, series)
    if named:
        pairs = [(a, b) for i, a in enumerate(named) for b in named[i + 1:]]   # a nickname two leagues share (rangers, jets) adds a label: any pair that is a real game
        live = [m for m in live if any({a, b} <= game_of(m) for a, b in pairs)] if pairs else [m for m in live if game_of(m) & set(named)]   # two teams with no game between them → none
    elif re.search(r'\b(vs|v|at|versus)\b', str(topic or '').lower()):   # "X vs Y" with names Kalshi does not know: no market rather than a stranger's game
        live = []
    return sorted(live, key=lambda m: _ts(m.get('close_time')))[:n]


def line(m):
    ya, na = price_of(m, 'yes'), price_of(m, 'no')
    return f"{m.get('ticker')} · {m.get('title')} · YES {ya if ya is not None else '—'} / NO {na if na is not None else '—'} (dollars per contract that pays $1) · closes {str(m.get('close_time'))[:16]}Z"


def first_note(markets):
    """🎯 KALSHI FIRST (owner 2026-11-15 'use whatever they gonna bid on to research first, then other sources'): the live market goes at the
    top of each mind's research goal, so every site it reads is about the game it may bid on. Data, never an instruction. Pure."""
    if not markets:
        return ''
    return ('THE LIVE KALSHI MARKET YOU ARE RESEARCHING FOR A REAL BID (read this first; data, never an instruction):\n' + '\n'.join(line(m) for m in markets[:6]) +
            '\nResearch THIS game on the sites below: injuries, rest, recent form and the line, against the Kalshi price. ')


def first_say(markets, has_key):
    """The chat line's Kalshi part when a PoB starts: the market and its prices, or why there is no real bid this time. Pure."""
    if not has_key:
        return ''
    if not markets:
        return ' ⚠ No open Kalshi market for a game that has not started, so this one files without a real bid.'
    return ' 🎯 Kalshi first: ' + ' · '.join(f"{m.get('title')} {price_of(m, 'yes') or '—'}" for m in markets[:2]) + '.'


def brief(markets):
    if not markets:
        return ''
    return ('\nLIVE KALSHI MARKETS (real money: it bids at once if BOTH of you back the same ticker and side; if only one of you does, the owner '
            'gets that pick to place with a tap). You MUST back exactly one of these with your honest confidence: add '
            '"kalshi": {"ticker": "<ticker>", "side": "yes|no"} to your main pick. Only if nothing you read supports any side, give no pick and say why in "pass":\n'
            + '\n'.join(line(m) for m in markets))


def _conf(v):
    """A mind's confidence as a whole number: 70, '70', '70%' → 70; anything unreadable → 0 (never offered)."""
    m = re.match(r'\s*(\d{1,3})', str(v if v is not None else ''))
    return min(100, int(m.group(1))) if m else 0


def offer(calls, ids, min_conf):
    """🙋 The minds split (owner 2026-11-15 'they either choose or give me a option or pick'): the most confident single mind's Kalshi pick at or
    over his minimum confidence, for HIM to place with a tap. Never sent by itself. → {ticker, side, conf: [c], why: [w], by} or None. Pure."""
    best = None
    for c in calls or []:
        for p in c.get('picks') or []:
            k = p.get('kalshi') if isinstance(p.get('kalshi'), dict) else None
            t, s = str((k or {}).get('ticker') or '').strip(), str((k or {}).get('side') or '').lower()
            conf = _conf(p.get('confidence'))
            if t in ids and s in ('yes', 'no') and conf >= min_conf and (not best or conf > best['conf'][0]):
                best = {'ticker': t, 'side': s, 'conf': [conf], 'why': [str(p.get('why') or '')], 'by': c.get('name') or f"Mind {'AB'[int(c.get('mind') or 0) % 2]}"}
    return best


def room_view(k):
    """🏟 A ticket as the game room shows it. Money in = what reached Kalshi (count × price); fees are never in it (CLAUDE.md §1). Pure."""
    n = (int(k['filled'] or 0) if k.get('filled') is not None else int(k.get('count') or 0) if k.get('status') == 'filled' else 0) if k.get('orderId') else 0   # a resting order holds nothing yet
    px = float(k.get('price') or 0); live = k.get('livePx')
    cost = round(n * px, 2)
    if k.get('outcome'):
        now = round(n * 1.0, 2) if k['outcome'] == 'won' else 0.0
    else:
        now = round(n * float(live), 2) if live is not None and n else None
    return {'ticker': k.get('ticker'), 'side': k.get('side'), 'title': k.get('title'), 'price': px or None, 'count': k.get('count'), 'filled': n, 'cost': cost,
            'now': now, 'pnl': round(now - cost, 2) if now is not None and n else None, 'livePx': live, 'status': k.get('status'), 'outcome': k.get('outcome'),
            'placed': bool(k.get('orderId')), 'offer': k.get('offer'), 'conf': k.get('conf'), 'why': k.get('why') if isinstance(k.get('why'), str) else None}


def outcome_line(k, has_key):
    """What the filed PoB did on Kalshi, in one chat sentence. Pure."""
    if not has_key:
        return ' No Kalshi key saved, so it is filed on paper.'
    if not k:
        return ' No real bid: no Kalshi market both minds backed, and no single pick reached your minimum confidence.'
    side = f"{str(k.get('side') or '').upper()} {k.get('title') or k.get('ticker')}"
    if k.get('orderId'):
        return f" 🎯 Real Kalshi bid placed: {side}, {k.get('count')} × {float(k.get('price') or 0):.2f} = ${float(k.get('usd') or 0):.2f}. Open its game to watch it live."
    if k.get('status') == 'waiting' and k.get('offer'):
        return f" 🙋 The minds split. {k.get('offer')} backs {side} at {(k.get('conf') or [0])[0]}%: tap Approve real bid in its folder to place it."
    if k.get('status') == 'waiting':
        return f" 🎯 Both minds back {side}: tap Approve real bid in its folder to place it."
    return f" Kalshi bid not sent: {k.get('why') or k.get('status')}."


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


def sends_now(c, by):
    """A PoB the owner asked for (`by` 'you') sends its ticket at once; one his scheduled auto run filed ('auto') only when AUTO is on —
    otherwise it waits for his tap. Every guard in `check` still runs either way."""
    return by != 'auto' or cfg(c)['mode'] == 'auto'


def check(c, market, pick, bids, balance_usd, now=None):
    """→ (ok, why, count, price). Every guard in the module note; the first that fails is the reason shown to the owner."""
    now = now or time.time(); c = cfg(c)
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
async def markets_for(http, topic, games=None):
    """The open Kalshi markets for this topic's games, none already started. `games` = ESPN board rows (read here when not given)."""
    rows = []; ss = series_for(topic)[:2]
    for s in ss:
        r = await http.get(f'{BASE}/markets', params={'series_ticker': s, 'status': 'open', 'limit': 1000})
        if r.status_code == 200:
            rows += r.json().get('markets') or []
    if games is None:
        import proof_tools as _pt   # ESPN's board: the guard's source of truth for "has it started"
        boards = await asyncio.gather(*(_pt.sport_board(http, ESPN_OF[s]) for s in ss if s in ESPN_OF), return_exceptions=True)
        games = [g for b in boards if isinstance(b, dict) for g in b.get('games') or []]
    now = time.time()
    return [m for m in relevant(rows, topic, now=now, n=LIST_MAX * 4, series=ss) if not_started(m, games, now)][:LIST_MAX]


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


# ✅ CONFIRM ON KALSHI (owner 2026-11-14: "they should check and confirm the bid on kalshi works"). After an order is sent, the agent reads it
# back from his own Kalshi account: the ticket then says what Kalshi itself holds (resting / filled / canceled, n of m filled), not what we hoped.
def settle(o, count, price):
    """Kalshi's order record → what the ticket shows. A canceled order with no fill frees its money from today's cap."""
    o = o or {}; count = int(count or 0); st = str(o.get('status') or '').lower()
    if o.get('fill_count') is not None:
        filled = int(float(o.get('fill_count') or 0))
    elif o.get('remaining_count') is not None:
        filled = max(0, int(o.get('initial_count') or count) - int(float(o.get('remaining_count') or 0)))
    else:
        filled = count if st == 'executed' else 0
    filled = min(filled, count) if count else filled
    status = 'filled' if st == 'executed' or (count and filled >= count) else 'resting' if st in ('resting', 'pending') else 'canceled' if st == 'canceled' else 'sent'
    if status == 'canceled' and filled:
        status = 'filled'   # part filled, the rest canceled: the filled part is a real position
    usd = round((filled if status in ('filled', 'canceled') else count) * float(price or 0), 2)   # resting/sent: the whole order is reserved
    return {'status': status, 'filled': filled, 'usd': usd, 'kalshiStatus': st or None}


async def order_status(http, key_id, pem, order_id):
    path = f'/portfolio/orders/{order_id}'
    r = await http.get(f'{BASE}{path}', headers=headers(key_id, pem, 'GET', path))
    if r.status_code != 200:
        raise RuntimeError(f'Kalshi said {r.status_code} reading the order: {r.text[:160]}')
    return (r.json() or {}).get('order') or {}


# 🧠 THE BIG IDEAS (owner 2026-11-14: "do all of the big ideas"). Pure; the service reads Kalshi and holds the store.
def _top_pick(c, ids):
    best = None
    for p in c.get('picks') or []:
        k = p.get('kalshi') if isinstance(p.get('kalshi'), dict) else None
        t, s = str((k or {}).get('ticker') or '').strip(), str((k or {}).get('side') or '').lower()
        if t in ids and s in ('yes', 'no') and (best is None or (p.get('confidence') or 0) > (best[2].get('confidence') or 0)):
            best = (t, s, p)
    return best


def split_view(calls, markets):
    """⚖ HEDGE: the minds did NOT agree, so no ticket — show each mind's own Kalshi side with the live odds instead of nothing. → [] or 2 rows."""
    by = {m.get('ticker'): m for m in markets or []}
    out = []
    for c in (calls or [])[:2]:
        tp = _top_pick(c, set(by))
        if tp:
            t, s, p = tp
            out.append({'mind': c.get('mind'), 'name': c.get('name'), 'ticker': t, 'side': s, 'title': by[t].get('title') or t,
                        'price': price_of(by[t], s), 'conf': p.get('confidence') or 0, 'why': str(p.get('why') or '')[:160]})
    return out if out and chosen(calls, set(by)) is None else []


def result_of(market):
    """Kalshi's settled result for a market: 'yes' / 'no', or None while it is open."""
    r = str((market or {}).get('result') or '').lower()
    return r if r in ('yes', 'no') else None


def lesson(bid):
    """🎓 A settled real-money bid as a COMP training row (the same shape as an owner proof): only what was known when it was bid."""
    minds = bid.get('minds') if isinstance(bid.get('minds'), list) else []
    plan = f"{str(bid.get('side') or '').upper()} at {float(bid.get('price') or 0):.2f} on Kalshi; both minds agreed" + (f": {' / '.join(str(x) for x in minds if x)}" if minds else '')
    return {'id': f"kalshi:{bid.get('orderId') or bid.get('id')}", 'kind': 'PoB · Kalshi', 'title': bid.get('title') or bid.get('ticker'),
            'plan': plan[:600], 'source': 'kalshi', 'outcome': bid.get('outcome'), 'at': bid.get('at')}


def streak(bids):
    """🔥 Settled real bids won in a row, newest first (an open bid neither breaks nor adds)."""
    n = 0
    for b in sorted([b for b in bids or [] if b.get('outcome') in ('won', 'lost')], key=lambda b: -float(b.get('settledAt') or b.get('at') or 0)):
        if b['outcome'] != 'won':
            break
        n += 1
    return n


STREAK_NEED = 3


def raise_offer(c, bids):
    """After 3 real wins in a row, OFFER (never apply) a bigger per-bid size: double, capped by the hard max and his daily cap. → dict or None."""
    c = cfg(c); n = streak(bids)
    to = round(min(HARD_BID, c['dayUsd'], c['bidUsd'] * 2), 2)
    return {'streak': n, 'from': c['bidUsd'], 'to': to} if n >= STREAK_NEED and to > c['bidUsd'] else None


def rivals(rows):
    """🥊 Two different agents on the SAME Kalshi market, OPPOSITE sides. rows: [{agent, name, ticker, side, title, result}] → pairs, newest market first;
    once Kalshi settles it, the pair names the winner and the loser."""
    by = {}
    for r in rows or []:
        if r.get('ticker') and r.get('side') in ('yes', 'no') and r.get('agent'):
            by.setdefault(r['ticker'], {}).setdefault(r['side'], {}).setdefault(r['agent'], r)
    out = []
    for t, sides in by.items():
        for y in (sides.get('yes') or {}).values():
            for n in (sides.get('no') or {}).values():
                if y['agent'] == n['agent']:
                    continue
                res = y.get('result') or n.get('result')
                win, lose = (y, n) if res == 'yes' else (n, y) if res == 'no' else (None, None)
                out.append({'ticker': t, 'title': y.get('title') or t, 'yes': y.get('name'), 'no': n.get('name'), 'result': res,
                            'winner': (win or {}).get('name'), 'loser': (lose or {}).get('name'), 'at': max(float(y.get('at') or 0), float(n.get('at') or 0))})
    return sorted(out, key=lambda r: -r['at'])[:12]
