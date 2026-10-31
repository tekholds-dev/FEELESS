"""🧰 FEELESS FIRST — the tools a GENERAL agent reads before any outside site (owner, 2026-10-30: "agents use the FEELESS site first to make
moves — our tools like trench, perps, pools, price gap, all that — except creating a coin, a pool or another agent").

The agent's cloud browser is walled off from FEELESS (cat_policy.check_url: it can never sign in or make cats), so these run SERVER-SIDE as
read-only lookups on our own services and hand the mind a short text it can reason on. `coin` also returns the pair, so the user's window
switches to OUR live chart of it. Nothing here trades, signs, creates or posts: moves still go through the agent's guarded order path.
"""
import re

TOOLS = {
    'coin': 'one coin on FEELESS: price, cap, pool, 24h volume + move (opens our live chart)',
    'trench': "the trenches right now: today's hottest Solana coins on our board",
    'perps': 'the FEELESS perps desk: markets, max leverage, how an order is placed',
    'pools': 'the Pool Hub: the best Solana pools by yield + depth',
    'gaps': 'price gaps between pools for the same token, net of swap costs',
}
# 🚫 never: another agent / FeeCat anywhere, or a coin / pool ON FEELESS (owner 2026-10-30: "on pump or any other platform they can do as they please —
# rep still scores that agent's wallet; just don't allow it on FEELESS"). Scams / rugs / phishing stay refused everywhere (cat_policy.BAD_JOB).
# 2026-10-31 (owner): "agents can't create a coin or another agent on FEELESS — on any other site they can do as requested". A FeeCat is always
# ours (refused everywhere); an agent with no site named is refused (it could mean FEELESS); "… on virtuals.io" is fine. Hard locks: cat_policy.check_url
# (FEELESS launch / agent pages never open in its browser) + feecat `create_cat` / reputation `feeless-launch` refuse every agent's own wallet.
NEVER = re.compile(r'(?i)\b(?:create|launch|deploy|mint|make|start|spawn)\s+(?:a\s+|an\s+|my\s+|our\s+|new\s+|another\s+)*fee\s*cats?\b'
                   r'|\b(?:create|launch|deploy|mint|make|start|spawn)\s+(?:a\s+|an\s+|my\s+|our\s+|new\s+|another\s+)*(?:agent|ai\s+agent|cat\s+agent)s?\b'
                   r'(?![^.\n]{0,30}\b(?:on|at|via|with|in|using)\s+(?!feeless|feecat)[a-z0-9])'
                   r'|\b(?:create|launch|deploy|mint|make|start)\b[^.\n]{0,40}\b(?:coin|token|memecoin|pool|liquidity\s+pool|lp)\b[^.\n]{0,30}\b(?:on|in|via|with)\s+(?:feeless|feecat)\b')
PERPS = [('SOL', 250), ('ETH', 250), ('BTC', 250)]
MAIN = 'http://127.0.0.1:5001'
REP = 'http://127.0.0.1:5077'


def _n(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def money(v):
    v = _n(v)
    return f'${v / 1e9:.1f}B' if v >= 1e9 else f'${v / 1e6:.1f}M' if v >= 1e6 else f'${v / 1e3:.1f}K' if v >= 1e3 else f'${v:.0f}'


def pair_line(p):
    b = p.get('baseToken') or {}
    ch = (p.get('priceChange') or {}).get('h24')
    return (f"${b.get('symbol') or '?'} · price ${p.get('priceUsd') or '?'} · cap {money(p.get('marketCap') or p.get('fdv'))} · pool {money((p.get('liquidity') or {}).get('usd'))}"
            f" · 24h vol {money((p.get('volume') or {}).get('h24'))} · 24h {('+' if _n(ch) >= 0 else '') + f'{_n(ch):.1f}%' if ch is not None else '—'}"
            f" · {p.get('dexId') or '?'} · pair {p.get('pairAddress') or '?'}")


def coin_text(pairs, q):
    rows = [p for p in pairs or [] if p.get('pairAddress')][:5]
    if not rows:
        return f'FEELESS found no coin for "{q}".', None
    top = rows[0]
    return 'FEELESS · coin search "' + q + '" (deepest pool first):\n' + '\n'.join(pair_line(p) for p in rows), {
        'pair': top['pairAddress'], 'mint': (top.get('baseToken') or {}).get('address'), 'symbol': (top.get('baseToken') or {}).get('symbol')}


def trench_text(pairs):
    rows = [p for p in pairs or [] if p.get('pairAddress')][:8]
    return 'FEELESS · the trenches now:\n' + '\n'.join(pair_line(p) for p in rows) if rows else 'The trench board is empty right now.'


def pools_text(hub):
    rows = sorted([r for r in (hub or {}).get('pools') or [] if r.get('apy') is not None], key=lambda r: -_n(r.get('apy')))[:8]
    if not rows:
        return 'The Pool Hub has no pools right now.'
    return 'FEELESS · Pool Hub (yield first):\n' + '\n'.join(
        f"{r.get('sym')} · {r.get('proto') or r.get('kind') or '?'} · APY {_n(r.get('apy')):.1f}% · TVL {money(r.get('tvl'))}" for r in rows)


def gaps_text(gaps):
    rows = sorted(gaps or [], key=lambda g: -_n(g.get('netPct')))[:6]
    if not rows:
        return 'No price gaps right now.'
    return 'FEELESS · price gaps (net of a 0.3% swap each side; OPEN only after two reads):\n' + '\n'.join(
        f"{g.get('sym')} · gap {_n(g.get('gapPct')):.2f}% · net {_n(g.get('netPct')):+.2f}% · {g.get('n')} pools" + (' · OPEN' if g.get('open') else '') for g in rows)


def perps_text():
    return ('FEELESS perps desk (Jupiter perps, paid in USDC or SOL): ' + ', '.join(f'{m}-PERP up to {x}x' for m, x in PERPS)
            + '. A position is opened from the perps desk and the user signs it; the agent proposes the trade (market, side, size, leverage, stop).')


async def run_tool(http, tool, q=''):
    """→ (text the mind reads, the coin {pair, mint, symbol} for the live chart or None). Read-only; a failed read says so."""
    tool = str(tool or '').lower()
    if tool not in TOOLS:
        return f"Unknown FEELESS tool '{tool}'. Tools: " + ', '.join(TOOLS), None
    q = str(q or '').strip()[:60]
    try:
        if tool == 'coin':
            r = await http.get(f'{MAIN}/api/market/search', params={'q': q or 'SOL'}, timeout=20)
            return coin_text((r.json() or {}).get('pairs'), q)
        if tool == 'trench':
            r = await http.get(f'{MAIN}/api/market/feed', params={'chain': 'solana'}, timeout=20)
            return trench_text((r.json() or {}).get('pairs')), None
        if tool == 'pools':
            r = await http.get(f'{REP}/api/reputation/familia-pools', timeout=20)
            return pools_text(r.json()), None
        if tool == 'gaps':
            r = await http.get(f'{REP}/api/reputation/familia-pools/gaps', timeout=20)
            j = r.json()
            return gaps_text(j.get('gaps') if isinstance(j, dict) else j), None
        return perps_text(), None
    except Exception as e:
        return f'FEELESS {tool} could not be read just now ({str(e)[:80]}) — say so, do not guess.', None
