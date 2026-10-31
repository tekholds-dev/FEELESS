"""⚡ EARN MODE (owner 2026-10-30: every agent gets a button to focus on profit on FEELESS when nobody is asking it anything — first safe price
gaps, then pool compounding, then maybe safe coins). This is the PLANNER: from the live price-gap, vault and pool feeds it ranks what its
money could do right now for the owner's risk choice. Pure, tested. It never signs: every play opens its own Launch › Pools tab, where the
owner's wallet signs (an agent wallet that deposits on its own is a later, guarded build — the owner tests real money first).

A gap counts only while OPEN and its net (after a swap's cost each side) is above zero; on most reads costs eat it, and the plan says so."""

RISKS = ('safe', 'mid', 'risky')
ALLOW = {'safe': {'safe'}, 'mid': {'safe', 'mid'}, 'risky': {'safe', 'mid', 'risky'}}
VAULT_TIER = {'lst': 'safe', 'stable': 'safe', 'vault': 'mid', 'loop': 'risky'}
SHOW = 6


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def plays(gaps=None, vault=None, pools=None, risk='safe', budget_usd=25.0):
    """→ the ranked plays [{kind, title, sub, dayUsd, apy, tier, tab, why}] for `risk` (safe ⊂ mid ⊂ risky), best $/day first."""
    allow = ALLOW.get(risk, ALLOW['safe'])
    budget = max(0.0, _f(budget_usd, 25.0))
    out = []
    for g in (gaps or {}).get('gaps') or []:   # 1 · price gaps: only open ones that beat their costs
        net = _f(g.get('netPct'))
        if g.get('open') and net > 0:
            out.append({'kind': 'gap', 'title': f"{g.get('sym')} gap {net:.2f}% net", 'tier': 'safe' if (g.get('lo') or {}).get('liq', 0) >= 1e6 else 'mid',
                        'sub': f"cheap on {(g.get('lo') or {}).get('dex')}, rich on {(g.get('hi') or {}).get('dex')}", 'apy': None,
                        'dayUsd': round(budget * net / 100, 4), 'tab': 'gaps', 'why': 'enter through the cheap pool; one-off, not a daily yield'})
    for s in (vault or {}).get('strategies') or []:   # 2 · compounding: the Night Vault's strategies
        apy = _f(s.get('apy'))
        if apy > 0:
            out.append({'kind': 'vault', 'title': f"{s.get('name')} · {s.get('top')}", 'tier': VAULT_TIER.get(s.get('key'), 'mid'), 'apy': round(apy, 2),
                        'sub': (s.get('risk') or {}).get('note') or s.get('sub') or '', 'dayUsd': round(budget * apy / 100 / 365, 4), 'tab': 'vault',
                        'why': 'compounds while it sleeps — your wallet signs the deposit'})
    for r in sorted([p for p in (pools or {}).get('pools') or [] if p.get('kind') in ('v3', 'dlmm', 'v2') and _f(p.get('apy')) > 0],
                    key=lambda p: -_f(p.get('apy')))[:12]:   # 3 · the busiest bands (AutoRange / pools)
        out.append({'kind': 'range' if r.get('kind') in ('v3', 'dlmm') else 'pool', 'title': f"{r.get('sym')} · {r.get('proto')}", 'tier': r.get('tier') or 'mid',
                    'apy': round(_f(r.get('apy')), 2), 'sub': f"${_f(r.get('tvl')) / 1e6:.1f}M pool{' · impermanent loss' if r.get('il') else ''}",
                    'dayUsd': round(budget * _f(r.get('apy')) / 100 / 365, 4), 'tab': 'range' if r.get('kind') in ('v3', 'dlmm') else 'pools',
                    'why': 'LP fees while price stays in the band' if r.get('kind') in ('v3', 'dlmm') else 'LP fees on a full-range pool'})
    out = [p for p in out if p['tier'] in allow]
    order = {'gap': 0, 'vault': 1, 'range': 2, 'pool': 3}
    return sorted(out, key=lambda p: (-p['dayUsd'], order[p['kind']]))[:SHOW]


def clean(raw):
    """The owner's Earn Mode switch → {'on', 'risk', 'budgetUsd'}."""
    raw = raw or {}
    return {'on': bool(raw.get('on')), 'risk': raw.get('risk') if raw.get('risk') in RISKS else 'safe',
            'budgetUsd': round(min(100_000.0, max(1.0, _f(raw.get('budgetUsd'), 25.0))), 2)}
