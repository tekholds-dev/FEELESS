"""📚 THE EDGE LIBRARY (owner 2026-11-04): every case a trader meets, as a check an agent can run: what to read, what it means, what to do, what must stop it. Rules of thumb, never a promise: an agent's own record beside each file comes from its own folders.
The indicators are ours, plain Pine v5, written here and free to download. Pure."""

CATEGORIES = {'safety': 'Rugs + safety', 'flow': 'Who is buying', 'entry': 'Entries', 'exit': 'Exits', 'perps': 'Perps', 'market': 'Market mood'}
FILES = [
    ('mint-live', 'safety', 'Mint or freeze still on', 'RugCheck, token authority', 'The creator can print coins or lock wallets', 'Skip it', 'Never buy with either on'),
    ('lp-unlocked', 'safety', 'Pool not locked or burned', 'Pool LP lock share', 'Liquidity can leave in one move', 'Size down or skip', 'Under $10K pool: skip'),
    ('top10', 'safety', 'Top 10 hold too much', 'Top 10 share, excluding the pool', 'A few wallets can end it', 'Skip above 30% unless they are burned or locked', 'Check they are not one bundle'),
    ('bundle', 'safety', 'Launch was bundled', 'First-block buyers, same funder', 'One person is the crowd', 'Skip, or wait until they have sold', 'Do not trust the holder count'),
    ('dev-sold', 'safety', 'Dev sold early', 'Creator wallet history', 'Could be a rug or could clear overhang', 'Only with fresh buyers after it', 'A dev selling into a pump: leave'),
    ('honeypot', 'safety', 'Buys work, sells fail', 'Sell count against buy count, simulate a sell', 'You cannot get out', 'Never buy', 'One failed sell simulation is enough'),
    ('buyer-ratio', 'flow', 'Buyers against sellers', 'Buys and sells, 5 min and 1 h', 'Who is winning right now', 'Lean with it only if pool depth grows too', 'Thin pools fake this'),
    ('whale-tape', 'flow', 'A whale on the tape', 'Trades 5x the median and over $1K', 'One big hand moved it', 'Check what that wallet did on its last coins', 'Never chase the same candle'),
    ('sniper-exit', 'flow', 'Snipers still holding', 'Early wallets, share still held', 'They sell into your buy', 'Wait for most of them to clear', 'Over half still in: wait'),
    ('volume-fade', 'flow', 'Volume dying', '5 min volume against the hour', 'The move is out of buyers', 'No new entry', 'A falling price on falling volume is not a dip'),
    ('kol-call', 'flow', 'A big account called it', 'Time of the post against the chart', 'You may be their exit', 'Only if it was not already up 2x', 'Never in the first candle after'),
    ('breakout', 'entry', 'Breakout over a level', 'Close above with volume over its average', 'New buyers took the level', 'Enter the retest, not the wick', 'Stop under the level'),
    ('dip', 'entry', 'First dip after a run', 'Pullback 20-40% with buyers holding', 'Late sellers shaken out', 'Starter size, add only if it holds', 'Under the pre-run base: thesis dead'),
    ('fresh', 'entry', 'Under 10 minutes old', 'Age, pool, holders', 'No history at all', 'Do not buy on this alone', 'A hard guard, it can only stop a buy'),
    ('already-ran', 'entry', 'Already up 300% in an hour', '1 h change', 'You are the exit liquidity', 'Skip', 'A hard guard'),
    ('hold-time', 'exit', 'Selling too fast', 'Your own hold time on wins and losses', 'Short holds often pay fees for nothing', 'Give a real thesis time', 'A hard stop still always fires'),
    ('trim', 'exit', 'Taking part off', 'Up 2x, or the plan\'s level', 'Trims pay for the runners', 'Take some, trail the rest', 'Never add back on the same candle'),
    ('stop', 'exit', 'The stop was hit', 'Price against the plan', 'You were wrong, that is all', 'Sell. No debate', 'Never widen a stop'),
    ('funding-hot', 'perps', 'Funding very high', 'Hyperliquid funding each hour', 'Longs are paying to be there', 'Do not chase longs', 'A hot rate can stay hot'),
    ('oi-jump', 'perps', 'Open interest jumps', 'Open interest against price', 'New money, not just closes', 'Up with price: trend. Up against it: squeeze risk', 'Confirm on the book'),
    ('book-wall', 'perps', 'A wall on the book', 'Order book sizes near the price', 'Support or a spoof', 'Do not rely on one that keeps moving', 'Walls vanish when touched'),
    ('liq-cluster', 'perps', 'Liquidations near', 'Leverage and price distance', 'A wick can reach them', 'Keep your own liquidation further away', 'Lower the leverage first'),
    ('fear', 'market', 'Extreme fear or greed', 'Fear & Greed index', 'The crowd is one way', 'A reason to look, not to trade', 'Not a timing signal'),
    ('btc-first', 'market', 'BTC moving hard', 'BTC 1 h change', 'Everything else follows', 'Pause small coins during a sharp drop', 'Coins fall faster than they rise'),
]
FIELDS = ('id', 'cat', 't', 'read', 'means', 'do', 'stop')

INDICATORS = {
    'rsi': ('RSI + zones', '//@version=5\nindicator("FEELESS RSI", overlay=false)\nlen = input.int(14)\nr = ta.rsi(close, len)\nplot(r, color=color.new(#45e486, 0))\nhline(70)\nhline(30)\nbgcolor(r > 70 ? color.new(color.red, 90) : r < 30 ? color.new(color.green, 90) : na)\n'),
    'ema-cross': ('EMA 9/21 cross', '//@version=5\nindicator("FEELESS EMA cross", overlay=true)\na = ta.ema(close, input.int(9))\nb = ta.ema(close, input.int(21))\nplot(a, color=#45e486)\nplot(b, color=#b388ff)\nplotshape(ta.crossover(a, b), style=shape.triangleup, location=location.belowbar, color=#45e486)\nplotshape(ta.crossunder(a, b), style=shape.triangledown, location=location.abovebar, color=#ff8fa3)\n'),
    'vwap': ('VWAP + bands', '//@version=5\nindicator("FEELESS VWAP", overlay=true)\nv = ta.vwap(hlc3)\nd = ta.stdev(close, 20)\nplot(v, color=#45e486)\nplot(v + d, color=color.new(#b388ff, 40))\nplot(v - d, color=color.new(#b388ff, 40))\n'),
    'bollinger': ('Bollinger squeeze', '//@version=5\nindicator("FEELESS squeeze", overlay=true)\nb = ta.sma(close, 20)\nd = ta.stdev(close, 20) * 2\nplot(b, color=#45e486)\nu = plot(b + d, color=#b388ff)\nl = plot(b - d, color=#b388ff)\nfill(u, l, color=color.new(#b388ff, 92))\nbgcolor((2 * d) / b < 0.04 ? color.new(color.yellow, 92) : na)\n'),
    'volume-spike': ('Volume spike', '//@version=5\nindicator("FEELESS volume spike", overlay=false)\nm = ta.sma(volume, 20)\nplot(volume, style=plot.style_columns, color=volume > m * input.float(3.0) ? #45e486 : color.new(#8d86a8, 40))\nplot(m, color=#b388ff)\n'),
    'obv': ('On-balance volume', '//@version=5\nindicator("FEELESS OBV", overlay=false)\nplot(ta.cum(math.sign(ta.change(close)) * volume), color=#45e486)\n'),
    'macd': ('MACD', '//@version=5\nindicator("FEELESS MACD", overlay=false)\n[m, s, h] = ta.macd(close, 12, 26, 9)\nplot(m, color=#45e486)\nplot(s, color=#b388ff)\nplot(h, style=plot.style_columns, color=h >= 0 ? color.new(#45e486, 50) : color.new(#ff8fa3, 50))\n'),
    'atr-stop': ('ATR trailing stop', '//@version=5\nindicator("FEELESS ATR stop", overlay=true)\na = ta.atr(14) * input.float(3.0)\nvar float s = na\ns := close > nz(s[1]) ? math.max(nz(s[1]), close - a) : close + a\nplot(s, color=close > s ? #45e486 : #ff8fa3)\n'),
}


def rows():
    return [dict(zip(FIELDS, f)) for f in FILES]


def checklist(limit=6):
    """A one-line reminder for a research round. It only ever adds checks."""
    return 'Before you decide, check: ' + '; '.join(f[1 + 1].lower() for f in FILES[:limit]) + '.'


def indicator_list():
    return [{'id': k, 't': v[0]} for k, v in INDICATORS.items()]
