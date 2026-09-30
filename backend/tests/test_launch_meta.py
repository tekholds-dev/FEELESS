from launch_meta import social_url, token_metadata, pump_form, upload_path


def test_handles_become_links():
    assert social_url('twitter', '@feeless') == 'https://x.com/feeless'
    assert social_url('telegram', 'feelessgroup') == 'https://t.me/feelessgroup'
    assert social_url('website', 'feeless.xyz') == ''
    assert social_url('twitter', 'http://x.com/a') == ''
    assert social_url('website', 'https://feeless.xyz') == 'https://feeless.xyz'


def test_metadata_carries_banner_and_links():
    m = token_metadata('https://feeless.xyz', 'Fee', 'FEE', 'hi', '/api/reputation/uploads/' + 'a' * 32 + '.png',
                       '/api/reputation/uploads/' + 'b' * 32 + '.png', 'https://feeless.xyz', '@feeless', '@feelessgroup')
    assert m['image'].startswith('https://feeless.xyz/api/reputation/uploads/')
    assert m['banner'] == m['header'] == m['extensions']['banner']
    assert m['extensions']['twitter'] == m['twitter'] == 'https://x.com/feeless'
    assert m['extensions']['telegram'] == 'https://t.me/feelessgroup'
    assert m['external_url'] == 'https://feeless.xyz'


def test_metadata_drops_unsafe_images():
    m = token_metadata('https://s', 'A', 'A', image='javascript:alert(1)', banner='http://x/y.png')
    assert m['image'] == '' and 'banner' not in m and m['properties']['files'] == []


def test_pump_form_keeps_handles():
    f = pump_form(' Fee ', 'fee', 'd', twitter='@feeless', website='nope')
    assert f['twitter'] == 'https://x.com/feeless' and 'website' not in f and f['symbol'] == 'FEE'


def test_uploads_are_rerooted_on_the_public_site():
    u = 'http://localhost:51367/api/reputation/uploads/' + 'c' * 32 + '.webp'
    assert upload_path(u) == '/api/reputation/uploads/' + 'c' * 32 + '.webp'
    assert token_metadata('https://feeless.xyz', 'A', 'A', image=u)['image'] == 'https://feeless.xyz' + upload_path(u)
    assert upload_path('https://evil.xyz/api/reputation/uploads/../x.png') == ''


def test_launch_tab_rules():
    from launch_meta import clean_tab, dev_buy_ok
    t = clean_tab({'rails': ['pump', 'raydium'], 'devBuy': True, 'maxDevBuySol': 99})
    assert t['rails'] == ['pump'] and t['maxDevBuySol'] == 50
    assert clean_tab({'rails': []})['rails'] == ['feeless']
    assert dev_buy_ok({'devBuy': False}, 0) and not dev_buy_ok({'devBuy': False}, 0.1)
    assert dev_buy_ok({'maxDevBuySol': 2}, 2) and not dev_buy_ok({'maxDevBuySol': 2}, 2.5)


def test_launch_costs_are_clamped_and_default_cheap():
    from launch_meta import clean_costs, COSTS_DEFAULT
    assert clean_costs(None) == COSTS_DEFAULT and COSTS_DEFAULT['pumpSlippagePct'] == 1.0
    c = clean_costs({'pumpSlippagePct': 99, 'pumpPriorityFeeSol': 5, 'feelessPriorityFeeSol': -1})
    assert c == {'pumpSlippagePct': 25.0, 'pumpPriorityFeeSol': 0.01, 'feelessPriorityFeeSol': 0.0}
    assert clean_costs({'pumpSlippagePct': 'abc'})['pumpSlippagePct'] == 1.0


def test_saving_costs_keeps_the_launch_rules_and_house_configs(tmp_path, monkeypatch):
    import asyncio
    import reputation_service as rs
    monkeypatch.setattr(rs, 'LAUNCH_RAIL_PATH', tmp_path / 'rail.json')
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'Adm1n'); monkeypatch.setattr(rs, '_admin_load', lambda: {}); monkeypatch.setattr(rs, '_admin_save', lambda d: None)
    monkeypatch.setattr(rs, '_audit', lambda *a: None)
    rs._json_save(rs.LAUNCH_RAIL_PATH, {'config': 'Cfg1', 'feeClaimer': 'F', 'house': [{'config': 'H1', 'label': 'Reserve'}], 'tab': {'rails': ['pump']}})
    asyncio.run(rs.launch_costs_set(None, rs.LaunchCostsIn(pumpSlippagePct=2, pumpPriorityFeeSol=0.0002, feelessPriorityFeeSol=0)))
    d = rs._json_load(rs.LAUNCH_RAIL_PATH, {})
    assert d['config'] == 'Cfg1' and d['house'][0]['label'] == 'Reserve' and d['tab'] == {'rails': ['pump']}
    assert d['costs'] == {'pumpSlippagePct': 2.0, 'pumpPriorityFeeSol': 0.0002, 'feelessPriorityFeeSol': 0.0}
