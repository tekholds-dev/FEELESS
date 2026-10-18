import social_feed as sf

TG = '''<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="pumpfun/9" data-view="x">
<div class="tgme_widget_message_user"><a href="https://t.me/pumpfun"><i class="tgme_widget_message_user_photo bgcolor1" data-content="P"><img src="https://cdn.example/a.jpg"></i></a></div>
<a class="tgme_widget_message_owner_name" href="https://t.me/pumpfun"><span dir="auto">Pump.fun</span></a>
<a class="tgme_widget_message_photo_wrap" style="width:1px;background-image:url('https://cdn.example/p.jpg')"></a>
<div class="tgme_widget_message_text js-message_text" dir="auto">gm <b>trenches</b><br/>new &amp; hot</div>
<time datetime="2026-10-18T10:00:00+00:00" class="time">10:00</time></div></div>'''


def test_telegram_preview_page_becomes_posts_with_text_time_author_and_photo():
    p = sf.parse_telegram(TG, 'pumpfun')
    assert len(p) == 1 and p[0]['text'] == 'gm trenches\nnew & hot' and p[0]['author'] == 'Pump.fun'
    assert p[0]['url'] == 'https://t.me/pumpfun/9' and p[0]['img'] == 'https://cdn.example/p.jpg' and p[0]['avatar'] == 'https://cdn.example/a.jpg' and p[0]['at'] > 0


def test_bluesky_and_pump_and_feeless_share_one_shape_and_mix_newest_first():
    b = sf.parse_bluesky({'posts': [{'uri': 'at://did/app.bsky.feed.post/abc', 'author': {'handle': 'x.bsky.social', 'displayName': 'X'}, 'record': {'text': 'sol szn', 'createdAt': '2026-10-18T11:00:00Z'}}]})
    p = sf.from_pump([{'id': '1', 'mint': 'MINT', 'user': 'caller', 'thesis': 'send it', 'at': 1792350000000, 'symbol': 'ABC', 'avatar': 'javascript:alert(1)'}])
    f = sf.from_feeless([{'id': 7, 'text': 'hi', 'ts': 1792360000, 'address': 'AAAAbbbbCCCC'}], 'feed-general')
    keys = {'id', 'src', 'author', 'handle', 'avatar', 'text', 'url', 'at', 'img', 'coin'}
    assert all(keys <= set(x) for x in b + p + f)
    assert p[0]['avatar'] is None and p[0]['url'] == 'https://pump.fun/coin/MINT' and p[0]['coin']['symbol'] == 'ABC'   # only http(s) links survive
    m = sf.mix([b, p, f])
    assert [x['src'] for x in m] == ['feeless', 'pump', 'bluesky'] or m[0]['at'] >= m[-1]['at']
    assert [x['src'] for x in sf.mix([b, p, f], srcs={'pump'})] == ['pump']

