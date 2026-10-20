import social_feed as sf

OEMBED = {'author_name': 'Toly', 'html': '<blockquote class="twitter-tweet"><p lang="en" dir="ltr">gm solana<br>ship it <a href="https://t.co/x">pic</a></p>&mdash; Toly (@aeyakovenko) <a href="https://twitter.com/aeyakovenko/status/1?ref_src=x">October 19, 2026</a></blockquote>'}


def test_only_real_x_post_links_pass():
    assert sf.x_status('https://x.com/aeyakovenko/status/1849011223344') == ('aeyakovenko', '1849011223344')
    assert sf.x_status('https://twitter.com/a_b/statuses/12345678') == ('a_b', '12345678')
    assert sf.x_status('https://x.com/aeyakovenko') is None
    assert sf.x_status('https://evil.com/x.com/a/status/123456') is None
    assert sf.x_status('javascript:alert(1)') is None


def test_oembed_becomes_a_post_with_who_shared_it():
    p = sf.from_x_oembed(OEMBED, 'https://x.com/aeyakovenko/status/1849011223344', 'FAM', 100.0)
    assert p['id'] == 'x:1849011223344' and p['src'] == 'x' and p['author'] == 'Toly'
    assert p['text'].startswith('gm solana\nship it') and '<' not in p['text']
    assert p['url'] == 'https://x.com/aeyakovenko/status/1849011223344' and p['sharedBy'] == 'FAM' and p['postedAt']
    assert sf.from_x_oembed({'html': ''}, 'https://x.com/a/status/123456', None) is None
    assert ('x', 'X') in sf.SOURCES
