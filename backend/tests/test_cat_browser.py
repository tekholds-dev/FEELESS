

def test_steel_live_view_is_page_only_and_hd():
    import cat_browser as cb
    assert cb.steel_view('https://api.steel.dev/v1/sessions/x/player') == 'https://api.steel.dev/v1/sessions/x/player?showControls=false&theme=dark&interactive=true'
    assert cb.steel_view('https://x/y?a=1').endswith('?a=1&showControls=false&theme=dark&interactive=true') and cb.steel_view(None) is None
    assert cb.VIEWPORT == {'width': 1440, 'height': 900}
