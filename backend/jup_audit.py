"""🧪 Jupiter audit → coin facts, dev CREW read and the coin's VITAL verdict. Pure (no network) + tested.

Why (owner, 2026-10-08: "no new coins, I'm running in circles … the gates need to be broken … add popular crews and bad crews who run
coins … the long horizontal vitals aren't vital enough"): our own holder scan needs ~40 RPC calls for a brand-new coin and only one RPC
lane answered, so ~19 of 271 listed coins were ever scanned and an unscanned coin is never bought. Jupiter's token rows (100 a call,
already fetched for prices) carry an audit for EVERY coin: top-holder %, dev balance %, mint / freeze authority, holder count, the dev
wallet and how many coins that dev launched (devMints) and graduated (devMigrations), plus organic vs bot volume. That is a holder
reading for every coin at once (`lite_intel`) and the crew signal (`crew`).
"""


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def facts(tok):
    """A Jupiter /tokens/v2 row → plain facts (None = Jupiter did not say)."""
    t = tok or {}
    a = t.get('audit') or {}
    s1 = t.get('stats1h') or {}
    vol = _f(s1.get('buyVolume')) + _f(s1.get('sellVolume'))
    org = _f(s1.get('buyOrganicVolume')) + _f(s1.get('sellOrganicVolume'))
    num = lambda v: None if v is None else _f(v)
    return {'holders': num(t.get('holderCount')), 'top10': num(a.get('topHoldersPercentage')), 'devPct': num(a.get('devBalancePercentage')),
            'devMints': None if a.get('devMints') is None else int(_f(a.get('devMints'))),
            'devGrads': None if a.get('devMigrations') is None else int(_f(a.get('devMigrations'))),
            'dev': t.get('dev'), 'mintOff': a.get('mintAuthorityDisabled'), 'freezeOff': a.get('freezeAuthorityDisabled'),
            'organic': num(t.get('organicScore')), 'organicLabel': t.get('organicScoreLabel'),
            'organicPct': round(org / vol * 100, 1) if vol > 0 else None,
            'traders1h': num(s1.get('numTraders')), 'realBuyers1h': num(s1.get('numOrganicBuyers')),
            'holderChg1h': num(s1.get('holderChange')), 'netBuyers1h': num(s1.get('numNetBuyers')), 'liqChg1h': num(s1.get('liquidityChange')),
            'verified': bool(t.get('isVerified')), 'launchpad': t.get('launchpad')}


# 👥 CREW = the people who run the coin, read from the dev's own launch record (Jupiter counts every coin the dev wallet minted and how
# many graduated). A dev whose coins keep graduating is a crew the market follows; a wallet that has launched hundreds and graduated a
# handful is a serial launcher (most of its coins die fast). It is a READ, never a hard block — $TikTok's dev (1,076 launches, 22
# graduated) still ran +10,000% in an hour.
POPULAR_GRADS, POPULAR_RATE = 3, 0.2
SERIAL_MINTS, SERIAL_RATE = 50, 0.05


def crew(f):
    """→ {'kind': popular | serial | fresh | mixed | unknown, 'icon', 'label', 'why'} from the dev's launch record."""
    m, g = (f or {}).get('devMints'), (f or {}).get('devGrads')
    if m is None:
        return {'kind': 'unknown', 'icon': '❔', 'label': 'crew unknown', 'why': 'Jupiter has no launch record for this dev'}
    g = int(g or 0); rate = g / m if m else 0.0
    rec = f"dev launched {m} coin{'s' if m != 1 else ''}, {g} graduated"
    if g >= POPULAR_GRADS and rate >= POPULAR_RATE:
        return {'kind': 'popular', 'icon': '🔥', 'label': 'popular crew', 'why': f"{rec} ({rate * 100:.0f}%) — their coins tend to make it"}
    if m >= SERIAL_MINTS and rate < SERIAL_RATE:
        return {'kind': 'serial', 'icon': '☠', 'label': 'serial launcher', 'why': f"{rec} ({rate * 100:.1f}%) — most of their coins die; take profit fast"}
    if m <= 3:
        return {'kind': 'fresh', 'icon': '🆕', 'label': 'fresh dev', 'why': f"{rec} — no track record yet"}
    return {'kind': 'mixed', 'icon': '⚪', 'label': 'mixed crew', 'why': f"{rec} ({rate * 100:.0f}%)"}


def lite_intel(f):
    """A holder reading in `token_intel`'s shape from Jupiter's audit — used ONLY when our own RPC scan has not landed (the full scan still
    runs and replaces it). Insiders / bundles are unknown here (None); mint / freeze authority and the dev record ride along."""
    if not f or f.get('top10') is None:
        return None
    return {'top10Pct': round(_f(f['top10']), 2), 'devHoldingPct': None if f.get('devPct') is None else round(_f(f['devPct']), 4),
            'insidersHoldingPct': None, 'bundledWallets': None, 'sniperWallets': None, 'creator': f.get('dev'),
            'holders': f.get('holders'), 'source': 'jupiter', 'jup': f}


def authority_bad(f):
    """Mint or freeze authority still live = the dev can print or freeze — a hard no, whatever else reads well."""
    return bool(f) and (f.get('mintOff') is False or f.get('freezeOff') is False)


def verdict(f, scan=None):
    """🫀 THE VITAL (replaces the long chip row): one verdict + the 3 facts that decide it.
    → {'grade': A–F, 'score': 0–100, 'tone': good|warn|bad, 'word', 'flags': [(icon, text, tone)…≤3], 'bars': {holders, dev, crew, flow}}
    Every part is a reading, never a promise. Unknown = the bar sits at half and says so."""
    f = f or {}; s = scan or {}
    flags, pts = [], 50.0
    if authority_bad(f):
        return {'grade': 'F', 'score': 0, 'tone': 'bad', 'word': 'DEV CAN MINT / FREEZE', 'flags': [('⛔', 'mint or freeze authority still live', 'bad')],
                'organicPct': f.get('organicPct'), 'bars': {'flow': 0, 'growth': 0, 'holders': 0, 'dev': 0, 'crew': 0}}
    top10 = s.get('top10') if s.get('top10') is not None else f.get('top10')
    if top10 is None:
        hb = 0.5
    else:
        hb = max(0.0, min(1.0, (45 - _f(top10)) / 35))
        if _f(top10) >= 35:
            flags.append(('🐋', f"top-10 hold {_f(top10):.0f}%", 'bad'))
        elif _f(top10) <= 18:
            flags.append(('🧩', f"spread — top-10 {_f(top10):.0f}%", 'good'))
    bund = s.get('bundledN')
    ins = s.get('insiders')
    if bund is not None and int(bund) >= 3:
        flags.append(('📦', f"{int(bund)} bundled wallets", 'bad')); hb *= 0.6
    if ins is not None and _f(ins) >= 15:
        flags.append(('🕵', f"insiders {_f(ins):.0f}%", 'bad')); hb *= 0.6
    dev = s.get('dev') if s.get('dev') is not None else f.get('devPct')
    db = 0.5 if dev is None else max(0.0, min(1.0, (10 - _f(dev)) / 10))
    if dev is not None and _f(dev) >= 8:
        flags.append(('👤', f"dev holds {_f(dev):.0f}%", 'bad'))
    c = crew(f)
    cb = {'popular': 1.0, 'mixed': 0.55, 'fresh': 0.5, 'unknown': 0.5, 'serial': 0.15}[c['kind']]
    if c['kind'] in ('popular', 'serial'):
        flags.append((c['icon'], c['label'] + f" ({f.get('devGrads') or 0}/{f.get('devMints')})", 'good' if c['kind'] == 'popular' else 'bad'))
    # 📈 GROWTH (profit signals): holders arriving this hour, real buyers ahead of sellers, and the pool not being drained
    hc, nb, tr, lc = f.get('holderChg1h'), f.get('netBuyers1h'), f.get('traders1h'), f.get('liqChg1h')
    gb = 0.5 if hc is None else max(0.0, min(1.0, 0.3 + _f(hc) / 70))
    if lc is not None and _f(lc) <= -25:
        flags.append(('🩸', f"pool drained {_f(lc):.0f}% this hour", 'bad')); gb *= 0.4
    elif hc is not None and _f(hc) >= 15:
        flags.append(('📈', f"holders +{min(999, _f(hc)):.0f}% this hour", 'good'))
    if nb is not None and _f(tr) >= 100 and _f(nb) / _f(tr) >= 0.4:
        flags.append(('🧲', f"{int(_f(nb)):,} net buyers of {int(_f(tr)):,}", 'good')); gb = min(1.0, gb + 0.15)
    org = f.get('organicPct')
    fb = 0.5 if org is None else max(0.0, min(1.0, _f(org) / 40))
    if org is not None and _f(org) < 8 and _f(f.get('traders1h')) >= 200:
        flags.append(('🤖', f"bots — {_f(org):.0f}% of volume is organic", 'bad'))
    elif org is not None and _f(org) >= 30:
        flags.append(('🌱', f"{_f(org):.0f}% organic volume", 'good'))
    pts = round((hb * 0.3 + db * 0.15 + cb * 0.2 + fb * 0.2 + gb * 0.15) * 100)
    grade = 'A' if pts >= 80 else 'B' if pts >= 65 else 'C' if pts >= 50 else 'D' if pts >= 35 else 'F'
    tone = 'good' if pts >= 65 else 'warn' if pts >= 45 else 'bad'
    word = {'A': 'CLEAN', 'B': 'GOOD', 'C': 'MIXED', 'D': 'RISKY', 'F': 'DANGER'}[grade]
    order = {'bad': 0, 'good': 1, 'warn': 2}
    flags = sorted(flags, key=lambda x: order.get(x[2], 3))[:3]
    return {'grade': grade, 'score': int(pts), 'tone': tone, 'word': word, 'flags': flags, 'crew': c,
            'organicPct': org, 'bars': {'flow': round(fb, 2), 'growth': round(gb, 2), 'holders': round(hb, 2), 'dev': round(db, 2), 'crew': round(cb, 2)}}


# 🎛 THE OWNER'S VITAL FILTER (real card cfg `vitalMin` · `organicMin` · `noSerial`; Coming up + every engine door obeys it). Unknown = not judged.
VITAL_MINS = (0, 35, 50, 65)      # any · D+ · C+ · B+
ORGANIC_MINS = (0, 5, 10, 20, 30)


def filter_why(f, scan=None, cfg=None):
    """None = passes the owner's vital filter, else the reason (shown under Coming up)."""
    c = cfg or {}
    vm, om, ns = int(_f(c.get('vitalMin'))), int(_f(c.get('organicMin'))), bool(c.get('noSerial'))
    if not (vm or om or ns) or not f:
        return None
    v = verdict(f, scan)
    if vm and v['score'] < vm:
        return f"vital {v['grade']} {v['score']} — your filter wants {vm}+"
    if ns and v['crew']['kind'] == 'serial':
        return f"serial launcher ({f.get('devGrads') or 0}/{f.get('devMints')}) — your filter skips them"
    if om and f.get('organicPct') is not None and _f(f['organicPct']) < om:
        return f"{_f(f['organicPct']):.0f}% organic — your filter wants {om}%+"
    return None
