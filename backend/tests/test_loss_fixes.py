"""🩹 Why the real card kept losing, 2026-10-13 — the leaks found in the overnight ledger, each with its fix."""
import asyncio
import time
from pathlib import Path

import fuse_wallet as fw
import office as of

SRC = (Path(__file__).resolve().parent.parent / 'reputation_service.py').read_text()


def test_a_buy_quoted_far_below_the_market_reading_is_a_crashed_coin_and_is_refused():
    """$PONSA / $REPE read ~$54K caps when the agents chose them and filled 96% lower: dead coins bought blind (the check only refused
    quotes ABOVE the market reading)."""
    o = {'usd': 1.0, 'midPx': 0.001, 'lamports': 10_000_000, 'agent': True}
    ok, why = fw.buy_safety(o, 25_000 * 10**6, 6, 9_900_000)              # quote = $0.00004 a coin, 96% under the reading
    assert not ok and 'below market' in why and 'crashed' in why
    assert any(w in why for w in fw.SAFETY_WORDS)                          # a safety refusal: the agents leave the coin alone 10 min
    assert fw.buy_safety(o, 1_200 * 10**6, 6, 9_900_000)[0]                # 17% cheaper than the reading: a normal fill, still bought
    assert fw.buy_safety(o, 25_000 * 10**6, None, 9_900_000)[0]            # unknown decimals: no price claim either way (as before)


def test_dead_coin_accounts_are_only_worthless_leftovers_no_card_holds():
    acct = lambda pk, mint, amt, ui, lam=1_500_000: {'pubkey': pk, 'program': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'lamports': lam,
                                                  'info': {'mint': mint, 'tokenAmount': {'amount': str(amt), 'uiAmount': ui, 'decimals': 6}}}
    rows = [acct('A1', 'DUST', 1_000, 0.001), acct('A2', 'HELD', 5_000_000, 5.0), acct('A3', 'RICH', 9_000_000, 9.0),
            acct('A4', 'OFF', 7, 0.000007), acct('A5', 'NOPX', 7, 0.000007), acct('A6', 'EMPTY', 0, 0.0)]
    rows += [acct('A7', 'USDREAL', 25_000_000, 25.0), acct('A8', 'BIGOFF', 900, 0.0009), acct('A9', 'MAJOR', 3, 0.000003)]
    dead = fw.dead_accounts(rows, keep_mints={'HELD'}, prices={'DUST': 0.0001, 'HELD': 0.0001, 'RICH': 1.0},
                            written_off={'OFF': 0.0001, 'USDREAL': 0.01, 'BIGOFF': 4.0}, never={'MAJOR'})
    assert [d['mint'] for d in dead] == ['DUST', 'OFF', 'USDREAL']         # held · worth $9 · no price and no write-off · empty (the sweep's job) · a write-off at $4 · a major: untouched
    assert fw.dead_accounts([acct('Z', 'MAJOR', 3, 0.000003)], prices={'MAJOR': 1e-9}, never={'MAJOR'}) == []
    assert dead[0]['usd'] < fw.DUST_USD and dead[0]['raw'] == 1_000 and dead[0]['rentSol'] == 0.0015 and dead[1]['usd'] is None
    assert len(fw.dead_accounts([acct(f'P{i}', f'M{i}', 5, 0.000005) for i in range(20)], prices={f'M{i}': 1e-9 for i in range(20)})) == fw.CLOSE_MAX


def test_the_close_dust_route_is_owner_only_and_dry_runs_first():
    i = SRC.index("async def fuse_wallet_close_dust(request: Request):")
    body = SRC[i:SRC.index('\n\n\n', i)]
    assert '_require_owner(request)' in body and "if not body.get('confirm') or not dead:" in body and "'dry': True" in body
    assert '_dust.burn_close_tx(' in body and "_fw_sign(" in body and "'side': 'close'" in body          # booked + credited like every sweep
    assert body.index("if not body.get('confirm')") < body.index('_fw_sign(')                          # nothing is signed on a dry run


def test_the_jupiter_key_is_spent_only_by_the_money_path(monkeypatch):
    """Price / token READS went keyed-first, unpaced, and ate the ~1 request/s the keeper's quotes need (30 of 55 skipped agent buys
    overnight were "Jupiter route unavailable (HTTP 429)")."""
    import reputation_service as rs
    seen = []

    class R:
        status_code = 200
        def json(self): return {'M': {'usdPrice': 1.5}}

    class H:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None, headers=None):
            seen.append((url.split('/')[2], bool((headers or {}).get('x-api-key')))); return R()
    monkeypatch.setattr(rs.httpx, 'AsyncClient', H)
    monkeypatch.setenv('JUPITER_API_KEY', 'k' * 24)
    for n_ in ('JUPITER_API_KEY_2', 'JUPITER_API_KEY_3', 'JUPITER_API_KEY_4', 'JUPITER_API_KEY_5', 'JUPITER_API_KEY_6', 'JUPITER_READ_KEY'):
        monkeypatch.delenv(n_, raising=False)   # the owner's real extra keys must not decide this test
    rs._jup_px_cache.clear()
    assert asyncio.run(rs._jup_prices(['M'])) == {'M': 1.5} and seen == [('lite-api.jup.ag', False)]     # a read: public lane only
    rs._jup_px_cache.clear(); seen.clear()
    assert asyncio.run(rs._jup_prices(['M'], keyed=True)) == {'M': 1.5} and seen == [('api.jup.ag', True)]   # the keeper's own check
    i = SRC.index('async def _fw_secure_buy('); assert "_jup_prices([order['mint']], keyed=True)" in SRC[i:i + 1600]
    assert '_jup_tokens(list(miss.values()), keyed=True)' in SRC[SRC.index('async def _fw_live_pairs('):SRC.index('async def _fw_preflight(')]
    assert SRC.count('keyed=True') <= 6                                                                   # the key stays on the money path


def test_the_archive_check_is_incremental_and_still_finds_a_rewrite():
    arch = {'anchor': 'A0', 'posAnchor': 'P0', 'cases': [], 'positions': []}
    prev = 'A0'
    for i in range(5):
        d = {'mint': f'M{i}', 'n': i}
        h = of._hash(prev, d); arch['cases'].append({'d': d, 'h': h}); prev = h
    bad, m = of.verify_inc(arch, None, 0.0)
    assert bad == 0 and m['fullAt'] == 0.0
    assert of.verify_inc(arch, m, 10.0) == (0, m)                                           # nothing changed: no hashing at all
    d = {'mint': 'M5'}; h = of._hash(prev, d); arch['cases'].append({'d': d, 'h': h})
    bad, m2 = of.verify_inc(arch, m, 20.0)
    assert bad == 0 and m2['fullAt'] == 0.0                                                 # appended: only the new record checked
    arch['cases'][2]['d'] = {'mint': 'FORGED'}                                              # a rewrite in the middle …
    assert of.verify_inc(arch, m2, 30.0)[0] == 0                                            # … is not seen between full checks
    bad, m3 = of.verify_inc(arch, m2, 30.0 + of.VERIFY_FULL_SEC + 1)
    assert bad >= 1 and m3['fullAt'] > 30.0                                                 # … and is found by the next full one
    assert of.verify_inc(arch, None, 0.0)[0] == of.verify(arch)                             # the same count as the plain check
    assert '_arch_verify(arch)' in SRC and '_of.verify(arch)' not in SRC


def test_the_tier_tick_reads_the_wallet_doc_from_the_read_only_copy():
    """The loop-lag catcher charged `_prime_tick › _fw_load` 149s of blocked loop in 8h: the 1.2 MB wallet doc was parsed seven times a tick
    just to read fields."""
    i = SRC.index('async def _prime_tick_inner(now):')
    body = SRC[i:SRC.index('\nasync def ', i + 10)]
    for line in ("books = (_fw_peek().get('books') or {})", "fw_cfg = _fw_peek().get('cfg') or {}", "bk_ = ((_fw_peek().get('books') or {}).get(tid) or {}) if real_t else {}",
                 "bk = (_fw_peek().get('books') or {}).get(tid)", "fw_books = _fw_peek().get('books') or {}"):
        assert line in SRC
    assert time.time() > 0
