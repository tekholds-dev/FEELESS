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
