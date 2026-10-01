"""COIN EDGE: one record per coin that every surface reads (pure, no I/O — the service passes what its caches hold).

pulse (5m flow) · snipersOut (radar) · verify (check level) · intel (forensics + wallet lists for tape tags) · runner (gates,
score, lane, bond boxes) · sources (why Fuse likes it) · elite (FEELESS's proven traders buying). `signals` = the short,
cited reasons a coin stands out, strongest first — the same evidence the case file / radar / alerts show.
"""

INTEL_KEYS = ('creator', 'top10Pct', 'insidersHoldingPct', 'devHoldingPct', 'sniperWallets', 'bundledWallets', 'topHolders')


def compose(mint, pulse=None, sniper=None, verify=None, intel=None, runner=None, sources=None, elite=None):
    intel_out = {k: intel.get(k) for k in INTEL_KEYS} if intel else None
    if intel_out and intel_out.get('topHolders'):
        intel_out['topHolders'] = intel_out['topHolders'][:10]
    run = None
    if runner:
        run = {k: runner.get(k) for k in ('score', 'lane', 'gates', 'bondTier', 'stage', 'curve')}
        run['passing'] = not runner.get('gates')
        run['bond'] = [{'label': b.get('label'), 'ok': bool(b.get('ok'))} for b in runner.get('bond') or []] or None
    sig = []
    if sniper:
        sig.append({'kind': 'snipers-out', 'text': sniper.get('text') or 'Every flagged sniper sold out', 'source': 'Launch forensics radar'})
    if run and run.get('bondTier'):
        sig.append({'kind': 'bond', 'text': f"{run['bondTier']} — {run.get('curve') or 0:.0f}% up the curve, every bond box ticked", 'source': 'Fuse Runners bond check'})
    if elite and elite.get('n'):
        sig.append({'kind': 'elite', 'text': f"{elite['n']} proven FEELESS trader{'s' if elite['n'] != 1 else ''} bought in 6h (${elite.get('usd', 0):,.0f})", 'source': 'Verified FEELESS trades'})
    if sources:
        sig.append({'kind': 'fuse', 'text': 'Fuse likes it: ' + ', '.join(s.get('label') or s.get('kind') for s in sources[:3]), 'source': 'Fuse Runners sources'})
    if verify and verify.get('level') in ('gold', 'verified'):
        sig.append({'kind': 'verified', 'text': 'FEELESS verified' if verify['level'] == 'verified' else 'Gold check (official / reviewed)', 'source': 'Coin verification'})
    if run and not run['passing'] and run.get('gates'):
        sig.append({'kind': 'gate', 'text': f"Fails: {run['gates'][0]}" + (f" (+{len(run['gates']) - 1})" if len(run['gates']) > 1 else ''), 'source': 'Fuse Runners gates', 'warn': True})
    if verify and verify.get('level') == 'revoked':
        sig.append({'kind': 'revoked', 'text': 'Verification revoked', 'source': 'Coin verification', 'warn': True})
    return {'mint': mint, 'pulse': pulse, 'snipersOut': sniper, 'verify': verify, 'intel': intel_out, 'runner': run,
            'sources': sources or [], 'elite': elite, 'signals': sig}
