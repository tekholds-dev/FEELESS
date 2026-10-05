#!/usr/bin/env python3
"""🧾 Where did the real card's money go? READ-ONLY report from the local Fuse wallet ledger (backend/data/fuse_wallet.db).
Usage (from the repo root):  backend/.venv/bin/python scripts/fuse-report.py [hours=12]
Prints no keys, no RPC URL, no wallet id. Prices: Jupiter's public price API (read-only); offline → held coins at cost."""
import json, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
import store, fuse_wallet as fw  # noqa: E402

SOL = 'So11111111111111111111111111111111111111112'


def jup(mints):
    # httpx (backend venv, ships its own CA bundle): the Mac's python.org urllib often has no CA certs → "offline" + a fake $150 SOL
    try:
        import httpx
        d = httpx.get('https://lite-api.jup.ag/price/v3', params={'ids': ','.join(mints)}, timeout=8).json()
    except Exception:
        try:
            with urllib.request.urlopen(f"https://lite-api.jup.ag/price/v3?ids={','.join(mints)}", timeout=8) as r:
                d = json.loads(r.read())
        except Exception as e:
            print(f"(price fetch failed: {str(e)[:80]})")
            return {}
    return {m: float((v or {}).get('usdPrice') or 0) for m, v in (d or {}).items() if isinstance(v, dict)}


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
    path = ROOT / 'backend' / 'data' / 'fuse_wallet.json'
    d = store.KV(path).get({}) or {}
    rows = store.Ledger(path).rows(limit=100000) or d.get('ledger') or []
    books = d.get('books') or {}
    now = time.time(); since = now - hours * 3600
    mints = sorted({m for b in books.values() for m in (b.get('legs') or {})} | {SOL})
    px = jup(mints); sol_px = px.get(SOL) or 150.0
    u = lambda v: f"${v:,.2f}" if v is not None else '—'
    print(f"FUSE WALLET — last {hours:g}h · SOL {u(sol_px)}{'' if px else ' (offline: held coins at cost)'}")
    wallet = [r for r in rows if r.get('card') == 'wallet' and r.get('at', 0) >= since]
    if wallet:
        print(f"  wallet: {sum(1 for r in wallet if r.get('status') == 'sent')} rent sweeps, {sum(r.get('sol') or 0 for r in wallet if r.get('status') == 'sent'):.4f} SOL rent back to reserve")
    for card, book in books.items():
        t = fw.money_trail([r for r in rows if r.get('card') == card], book, since, now, sol_px, px)
        print(f"\n== {card} ==")
        print(f"  put in {u(t['fundedUsd'])} → now {u(t['nowUsd'])} (coins {u(t['heldNowUsd'])} + cash {u(t['cashUsd'])}) · price result {u(t['resultUsd'])}")
        print(f"  where it went: realized {u(t['realizedAllUsd'])} (this window {u(t['realizedWindowUsd'])}) · still-held move {u(t['unrealizedUsd'])} · "
              f"written off {u(t['writeoffUsd'])} · fees the card paid {u(t['cardFeesUsd'])} · unexplained {u(t['unexplainedUsd'])}")
        print("  (unexplained ≠ 0 is usually SOL's own move: card cash is SOL, realized $ was booked at each fill's SOL price)")
        print(f"  {t['swaps']} swaps in window · network fees {u(t['netFeesWindowUsd'])} · rent on reserve {t['rentOnReserveSol']:.4f} SOL")
        for c in t['coins']:
            print(f"    {c['symbol']:<10} {c['buys']}b/{c['sells']}s  bought {u(c['boughtUsd'])}  sold {u(c['soldUsd'])}  realized {u(c['realizedUsd'])}")
        for h in t['held']:
            print(f"    HELD {h['symbol']:<10} cost {u(h['costUsd'])} → now {u(h['nowUsd'])}")
        for p in t['problems'][:8]:
            print(f"    ⚠ {p['n']}× {p['why']}")
        for m, why in t['benched'].items():
            print(f"    🪑 benched {m[:6]}… — {why}")
        rep = fw.run_report([r for r in rows if r.get('card') == card], card, now, t['fundedUsd'], t['nowUsd'])
        for f in rep.get('flaws') or []:
            print(f"    FLAW [{f['level']}] {f['what']} → {f['fix']}")


if __name__ == '__main__':
    main()
