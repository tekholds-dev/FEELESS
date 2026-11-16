#!/usr/bin/env python3
"""📡 No-money live check before a push (owner 2026-11-16 proposals: "stuff actually working").

Reads the real outside services FEELESS trades and files on, plus our own four services, and says which answer.
READ ONLY: a Jupiter quote it never turns into a swap, Kalshi's public market list, ESPN's scoreboard, DexScreener's
boosted list. No key is read, nothing is signed, sent or bought. NO GeckoTerminal (CLAUDE.md §1).

Exit 0 = every check answered; 1 = one or more did not (the gate shows it as a warning and still pushes: an outside
service being down is not our code being broken). Usage: .venv/bin/python scripts/live-check.py
"""
import json
import sys
import time
import urllib.request

SOL = 'So11111111111111111111111111111111111111112'
USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
CHECKS = [
    # (name, url, test of the parsed JSON → True when it answered with real data)
    ('Jupiter quote (never swapped)', f'https://lite-api.jup.ag/swap/v1/quote?inputMint={SOL}&outputMint={USDC}&amount=10000000&slippageBps=50',
     lambda j: int(j.get('outAmount') or 0) > 0),
    ('Kalshi markets (public read)', 'https://api.elections.kalshi.com/trade-api/v2/markets?limit=1&status=open', lambda j: isinstance(j.get('markets'), list)),
    ('ESPN scoreboard', 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard', lambda j: isinstance(j.get('events'), list)),
    ('DexScreener boosts', 'https://api.dexscreener.com/token-boosts/top/v1', lambda j: isinstance(j, list) and len(j) > 0),
    ('server 5001', 'http://127.0.0.1:5001/docs', None),
    ('reputation 5077', 'http://127.0.0.1:5077/api/reputation/rep-markets', lambda j: isinstance(j, dict)),
    ('feecat 5088', 'http://127.0.0.1:5088/api/cats/health', None),
    ('candles 5099', 'http://127.0.0.1:5099/api/candles/health', None),
]


def check(name, url, ok, opener=urllib.request.urlopen):
    """→ (passed, line). One GET, 10 s at most. Pure apart from the GET."""
    t0 = time.time()
    try:
        with opener(urllib.request.Request(url, headers={'User-Agent': 'feeless-live-check/1', 'Accept': 'application/json'}), timeout=10) as r:
            body = r.read()
            code = r.status
        good = code == 200 and (ok is None or ok(json.loads(body or b'null')))
        why = '' if good else f'answered {code} without real data'
    except Exception as e:   # noqa: BLE001 — any failure is a line, never a crash
        good, why = False, str(e)[:120]
    ms = round((time.time() - t0) * 1000)
    return good, f"{'✅' if good else '⚠'} {name:<32} {ms:>5} ms {why}".rstrip()


def main(checks=CHECKS, opener=urllib.request.urlopen):
    rows = [check(n, u, ok, opener) for n, u, ok in checks]
    for _, line in rows:
        print(line)
    bad = sum(1 for g, _ in rows if not g)
    print(f"live check: {len(rows) - bad}/{len(rows)} answered{'' if not bad else ' — read the ⚠ lines before a real-money test'}")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
