"""FEELESS investigation engine: turns on-chain forensics into case files.

Every point of a score comes from a cited piece of evidence (what, how much, where it came from), the way
professional on-chain investigators write cases: funding trails (first-transaction funder, the Arkham/Nansen
clustering signal), launch outcomes, sniping/bundling records, caller dump patterns and linked wallets.
Pure functions only: the service gathers the data, this module scores and explains it.
"""

LEVELS = ((70, 'high', 'High risk'), (40, 'suspect', 'Suspect'), (15, 'watch', 'Watch'), (0, 'clean', 'No red flags'))


def _level(score):
    for floor, key, label in LEVELS:
        if score >= floor:
            return key, label
    return 'clean', 'No red flags'


def _ev(kind, weight, claim, source):
    return {'kind': kind, 'weight': weight, 'claim': claim, 'source': source}


def wallet_evidence(ctx: dict) -> list:
    """ctx: blocked (blocklist record or None), funderOfSquads (funder record or None), fundedBy (wallet or None),
    fundedByFlagged (bool), creator (score_creator dict or None), caller (_kol_stats dict or None),
    linkedCreators (list of {address, badge, ruggedCount})."""
    ev = []
    b = ctx.get('blocked') or {}
    if b.get('reported'):
        ev.append(_ev('blocklist', 45, 'Reported as a rug and confirmed onto the FEELESS blocklist.', 'FEELESS blocklist'))
    roles = list((b.get('mints') or {}).values())
    for role, label in (('sniper', 'sniped'), ('bundler', 'bundled'), ('funder', 'bankrolled snipers on')):
        n = roles.count(role)
        if n:
            ev.append(_ev(role, min(45, 15 * n), f'{label.capitalize()} {n} launch{"es" if n > 1 else ""} (seen in the mint block / first ~1s).', 'Launch forensics'))
    f = ctx.get('funderOfSquads') or {}
    if f.get('funded'):
        n, m = len(f['funded']), len(f.get('mints') or {})
        ev.append(_ev('funder', 40 if (n >= 3 or m >= 2) else 15, f'Funded {n} sniper/bundler wallet{"s" if n > 1 else ""} across {m} launch{"es" if m != 1 else ""}.', 'Funding graph'))
    if ctx.get('fundedByFlagged'):
        ev.append(_ev('funded-by', 30, f"First funded by {ctx['fundedBy'][:4]}…{ctx['fundedBy'][-4:]}, a wallet already behind snipe/bundle squads.", 'Funding graph'))
    c = ctx.get('creator') or {}
    if c:
        if c.get('ruggedCount'):
            ev.append(_ev('rugs', min(50, 25 * c['ruggedCount']), f"{c['ruggedCount']} launch{'es' if c['ruggedCount'] > 1 else ''} rugged (liquidity pulled).", 'Creator record'))
        if c.get('dumpedCount'):
            ev.append(_ev('dumps', min(30, 10 * c['dumpedCount']), f"{c['dumpedCount']} launch{'es' if c['dumpedCount'] > 1 else ''} dumped by the creator.", 'Creator record'))
        if (c.get('launchBurst24h') or 0) >= 3:
            ev.append(_ev('farm', 15, f"Launched {c['launchBurst24h']} coins inside 24h (a launch-farm pattern).", 'Creator record'))
        if c.get('cloneCount'):
            ev.append(_ev('clones', 10, f"{c['cloneCount']} copy-paste launch{'es' if c['cloneCount'] > 1 else ''} (same ticker reused).", 'Creator record'))
        if c.get('bigWinners'):
            ev.append(_ev('winners', -min(30, 10 * c['bigWinners']), f"{c['bigWinners']} launch{'es' if c['bigWinners'] > 1 else ''} still alive above $100K MC.", 'Creator record'))
    k = ctx.get('caller') or {}
    if k.get('danger'):
        ev.append(_ev('caller', 25, 'Calls then dumps: sells into followers shortly after calling.', 'Caller trade history'))
    elif (k.get('quickFlipPct') or 0) >= 50:
        ev.append(_ev('flipper', 15, f"Flips {k['quickFlipPct']}% of positions within an hour.", 'Caller trade history'))
    bad_links = [l for l in ctx.get('linkedCreators') or [] if l.get('badge') in ('flagged', 'risky') or (l.get('ruggedCount') or 0)]
    if bad_links:
        ev.append(_ev('linked', min(30, 10 * len(bad_links)), f'Shares a funding source with {len(bad_links)} flagged creator wallet{"s" if len(bad_links) > 1 else ""}.', 'Funding graph'))
    return sorted(ev, key=lambda e: -abs(e['weight']))


def verdict(evidence: list, protected: bool = False) -> dict:
    if protected:
        return {'score': 0, 'level': 'feeless', 'label': 'FEELESS wallet', 'summary': 'Official FEELESS wallet: never blocklisted.'}
    score = max(0, min(100, sum(e['weight'] for e in evidence)))
    level, label = _level(score)
    bad = [e for e in evidence if e['weight'] > 0]
    summary = (bad[0]['claim'] + (f' (+{len(bad) - 1} more finding{"s" if len(bad) > 2 else ""})' if len(bad) > 1 else '')) if bad else 'Nothing on record against this wallet yet.'
    return {'score': score, 'level': level, 'label': label, 'summary': summary}


def clusters(holders: list, funder_of: dict, min_size: int = 2) -> dict:
    """Group holder wallets by who funded them (Bubblemaps-style bubbles, but evidence-backed).
    holders: [{owner, pct}], funder_of: {wallet: funder}. A cluster = 2+ holders sharing one funder,
    or a holder that funded other holders."""
    pct = {h['owner']: h.get('pct') or 0 for h in holders if h.get('owner')}
    groups = {}
    for w in pct:
        root = funder_of.get(w)
        if root:
            groups.setdefault(root, set()).add(w)
    for w in pct:  # a holder that itself funded other holders heads their cluster
        if w in groups:
            groups[w].add(w)
    out = [{'funder': f, 'wallets': sorted(ws), 'pct': round(sum(pct.get(w, 0) for w in ws), 2)}
           for f, ws in groups.items() if len(ws) >= min_size]
    out.sort(key=lambda c: -c['pct'])
    return {'clusters': out, 'linkedPct': round(sum(c['pct'] for c in out), 2), 'wallets': len(pct)}


def coin_risk(intel: dict, auth: dict, creator_blocked: bool = False, linked_pct: float = 0) -> dict:
    """0-100 coin risk (RugCheck-style) with the reason for every point."""
    ev = []
    if auth.get('freezeAuthority'):
        ev.append(_ev('freeze', 40, 'Freeze authority is live: the creator can freeze your tokens so you cannot sell.', 'Mint account'))
    if auth.get('mintAuthority'):
        ev.append(_ev('mint', 30, 'Mint authority is live: the creator can print more supply.', 'Mint account'))
    if creator_blocked:
        ev.append(_ev('creator', 40, 'Creator wallet is on the FEELESS blocklist.', 'FEELESS blocklist'))
    dev, ins, top = intel.get('devHoldingPct') or 0, intel.get('insidersHoldingPct') or 0, intel.get('top10Pct') or 0
    if dev >= 5:
        ev.append(_ev('dev', 25 if dev >= 20 else 10, f'Creator holds {dev}% of supply.', 'Holder scan'))
    if ins >= 10:
        ev.append(_ev('insiders', 25 if ins >= 25 else 10, f'Snipers/bundlers still hold {ins}% of supply.', 'Launch forensics'))
    if top >= 35:
        ev.append(_ev('top10', 20 if top >= 50 else 10, f'Top 10 wallets hold {top}% (pools excluded).', 'Holder scan'))
    if len(intel.get('bundledWallets') or []) >= 3:
        ev.append(_ev('bundle', 10, f"{len(intel['bundledWallets'])} wallets bought in the mint block (bundled launch).", 'Launch forensics'))
    if len(intel.get('sniperWallets') or []) >= 5:
        ev.append(_ev('snipe', 10, f"{len(intel['sniperWallets'])} wallets sniped within ~1s of launch.", 'Launch forensics'))
    if intel.get('flaggedFunders'):
        ev.append(_ev('funders', 20, 'Sniper wallets were funded by known rug/snipe funders.', 'Funding graph'))
    if linked_pct >= 20:
        ev.append(_ev('clusters', 15, f'Linked wallet clusters hold {linked_pct}% of supply.', 'Funding clusters'))
    score = min(100, sum(e['weight'] for e in ev))
    level = 'danger' if score >= 50 else 'caution' if score >= 20 else 'ok'
    return {'score': score, 'level': level, 'evidence': sorted(ev, key=lambda e: -e['weight'])}
