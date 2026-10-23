import site_probe as sp

NOW = 1_800_000_000.0
REAL = """<html><head><title>Orbit Protocol — onchain yield</title><script id="__NEXT_DATA__">{}</script><script src="/_next/static/x.js"></script></head>
<body><h1>Stake once, earn on every chain</h1><h2>How it works</h2><a href="/docs">Docs</a><a href="https://github.com/orbit/app">GitHub</a>
<button>Connect Wallet</button><script>import('@solana/web3.js')</script><a href="https://x.com/orbit">X</a>""" + ' word' * 400 + "</body></html>"
MEME = """<html><head><title>$MOONCAT</title><meta name="generator" content="Carrd"></head><body><h1>MOONCAT TO THE MOON</h1><p>CA: 9xyz pump</p>
<a href="https://pump.fun/coin/x">Buy on pump.fun</a><a href="https://dexscreener.com/solana/x">Chart</a><a href="https://t.me/mooncat">TG</a>
<p>built with carrd</p></body></html>"""


def test_hosts_are_plain_https_names_never_ips_or_socials():
    assert sp.host_of('https://www.Orbit.xyz/app?x=1') == 'orbit.xyz' and sp.host_of('http://sub.coin.co.uk/') == 'sub.coin.co.uk'
    assert sp.host_of('https://127.0.0.1/x') is None and sp.host_of('ftp://coin.xyz') is None and sp.host_of('https://user:pw@coin.xyz') is None
    assert sp.host_of('javascript:alert(1)') is None and sp.host_of('') is None and sp.host_of('https://localhost') is None
    assert sp.registrable('app.orbit.xyz') == 'orbit.xyz' and sp.registrable('sub.coin.co.uk') == 'coin.co.uk'
    assert sp.skip('pump.fun') and sp.skip('www.dexscreener.com'.removeprefix('www.')) and sp.skip('m.x.com') and not sp.skip('orbit.xyz')


def test_the_ssrf_guard_only_lets_public_addresses_through():
    assert sp.public_ip('104.16.1.1') and sp.public_ip('2606:4700::1111')
    for bad in ('127.0.0.1', '10.0.0.249', '192.168.1.5', '172.16.0.1', '169.254.169.254', '::1', '0.0.0.0', 'fc00::1', 'nonsense'):
        assert not sp.public_ip(bad), bad


def test_rdap_age_and_the_two_verdicts():
    rdap = {'events': [{'eventAction': 'last changed', 'eventDate': '2026-01-01T00:00:00Z'}, {'eventAction': 'registration', 'eventDate': '2025-01-01T00:00:00Z'}]}
    age = sp.age_days(rdap, NOW)
    assert age is not None and age > 365 and sp.age_days({}, NOW) is None and sp.age_days({'events': [{'eventAction': 'registration', 'eventDate': 'bad'}]}, NOW) is None
    real = sp.snapshot(REAL)
    assert real['title'].startswith('Orbit Protocol') and real['heads'][0] == 'Stake once, earn on every chain' and 'Next.js' in real['stack']
    assert real['dapp'] and real['docs'] and real['socials'] == ['X'] and real['words'] > 300
    v = sp.verdict(age, real)
    assert v['kind'] == 'REAL TECH' and v['line'].startswith('🧪 REAL TECH ·') and 'wallet connect' in v['line']
    meme = sp.snapshot(MEME)
    assert meme['builder'] == ['Carrd'] and meme['meme'] >= 2 and not meme['dapp']
    m = sp.verdict(3, meme)
    assert m['kind'] == 'TEMPLATE' and 'Carrd one-pager' in m['line'] and '3d old' in m['line']
    assert sp.verdict(None, None)['kind'] == 'UNREAD'
    f = sp.fact('mooncat.xyz', m, meme)
    assert f.startswith('mooncat.xyz · 🎭 TEMPLATE') and '“$MOONCAT”' in f and len(f) <= 220


def test_her_site_read_files_a_verdict_under_the_coin_and_never_fetches_a_private_host(monkeypatch):
    import asyncio
    import reputation_service as rs
    real_fetch = rs._nexa_site_fetch
    monkeypatch.setattr(rs, '_open_pairs', [{'baseToken': {'address': 'MINT1'}, 'info': {'websites': [{'url': 'http://mooncat.xyz'}]}},
                                            {'baseToken': {'address': 'MINT2'}, 'info': {'websites': [{'url': 'https://pump.fun/coin/x'}]}},
                                            {'baseToken': {'address': 'MINT3'}, 'info': {'websites': [{'url': 'https://evil.example'}]}}])

    async def fetch(url, hops=3):
        return MEME if 'mooncat' in url else None

    async def rdap(domain):
        return {'events': [{'eventAction': 'registration', 'eventDate': '2026-10-20T00:00:00Z'}]}
    monkeypatch.setattr(rs, '_nexa_site_fetch', fetch); monkeypatch.setattr(rs, '_nexa_rdap', rdap)
    kb = {}
    n = asyncio.run(rs._nexa_sites(kb, [{'mint': 'MINT1'}, {'mint': 'MINT2'}, {'mint': 'MINT3'}], NOW))
    assert n == 2                                                                   # pump.fun is not the coin's own site
    assert kb['site']['mint1']['f'].startswith('mooncat.xyz · 🎭 TEMPLATE') and kb['site']['mint3']['f'].startswith('evil.example · ❔')
    assert asyncio.run(rs._nexa_sites(kb, [{'mint': 'MINT1'}], NOW + 3600)) == 0    # read this week → never fetched again

    class _Loop:
        async def getaddrinfo(self, host, port, type=0):
            return [(2, 1, 6, '', ('10.0.0.249', 443))]
    monkeypatch.setattr(rs.asyncio, 'get_running_loop', lambda: _Loop())
    fetched = []
    monkeypatch.setattr(rs, '_ai_http', lambda: fetched.append(1))
    assert asyncio.run(real_fetch('https://lan-host.xyz/')) is None and fetched == []   # resolves to the LAN → never requested
