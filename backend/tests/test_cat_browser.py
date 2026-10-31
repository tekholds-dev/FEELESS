

def test_steel_live_view_is_page_only_and_hd():
    import cat_browser as cb
    assert cb.steel_view('https://api.steel.dev/v1/sessions/x/player') == 'https://api.steel.dev/v1/sessions/x/player?showControls=false&theme=dark&interactive=true'
    assert cb.steel_view('https://x/y?a=1').endswith('?a=1&showControls=false&theme=dark&interactive=true') and cb.steel_view(None) is None
    assert cb.VIEWPORT == {'width': 1440, 'height': 900}


def test_a_bot_check_stops_the_window_for_a_person_never_a_bypass():
    from cat_browser import needs_human
    for page in ('Just a moment... Checking your browser', 'Vercel Security Checkpoint', 'Our systems have detected unusual traffic', 'Attention Required! | Cloudflare'):
        assert 'bot check' in needs_human('https://site.com/', page)
    assert 'bot check' in needs_human('https://www.google.com/sorry/index', '')
    assert needs_human('https://coindesk.com/policy', 'Policy news about bitcoin') is None
