"""📺 Watch highlights: feed parsing, name matching and the handle → OWN channel id rule (no network)."""
import rep_watch as w

FEED = '''<?xml version="1.0"?><feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
<title>NBA</title>
<entry><yt:videoId>aaaaaaaaaaa</yt:videoId><yt:channelId>UCWJ2lWNubArHWmf3FIHbfcQ</yt:channelId><title>Lakers vs Celtics | Full Game Highlights</title>
<link rel="alternate" href="https://www.youtube.com/watch?v=aaaaaaaaaaa"/><published>2026-11-11T05:00:00+00:00</published>
<media:group><media:thumbnail url="https://i.ytimg.com/vi/aaaaaaaaaaa/hqdefault.jpg"/><media:community><media:statistics views="1200"/></media:community></media:group></entry>
<entry><yt:videoId>bbbbbbbbbbb</yt:videoId><yt:channelId>UCWJ2lWNubArHWmf3FIHbfcQ</yt:channelId><title>Flakers? no. Best dunks</title>
<link rel="alternate" href="https://www.youtube.com/shorts/bbbbbbbbbbb"/><published>2026-11-10T05:00:00+00:00</published></entry>
</feed>'''


def test_a_feed_becomes_playable_videos_with_their_own_channel_and_shorts_marked():
    v = w.parse_feed(FEED)
    assert [x['id'] for x in v] == ['aaaaaaaaaaa', 'bbbbbbbbbbb']
    assert v[0]['channel'] == 'NBA' and v[0]['views'] == 1200 and not v[0]['short'] and v[1]['short']
    assert v[1]['thumb'].endswith('bbbbbbbbbbb/hqdefault.jpg')   # no thumbnail in the feed: YouTube's own
    assert w.parse_feed('not xml') == []


def test_a_name_matches_whole_words_at_their_start_in_any_order():
    v = w.parse_feed(FEED)
    assert [x['id'] for x in w.match(v, 'lakers')] == ['aaaaaaaaaaa']          # "Flakers" is not the Lakers
    assert [x['id'] for x in w.match(v, 'CELTICS lakers')] == ['aaaaaaaaaaa']
    assert len(w.match(v, '')) == 2 and w.match(v, 'warriors') == []


def test_a_handle_resolves_to_the_pages_own_channel_never_a_featured_one():
    html = '"channelId":"UCmyweyoqldy5yPGeHigEyzA" … <link rel="canonical" href="https://www.youtube.com/channel/UCAW-NpUFkMyCNrvRSSGIvDQ">'
    assert w.canonical_id(html) == 'UCAW-NpUFkMyCNrvRSSGIvDQ'
    assert w.canonical_id('"externalId":"UCAW-NpUFkMyCNrvRSSGIvDQ"') == 'UCAW-NpUFkMyCNrvRSSGIvDQ'
    assert w.canonical_id('<html>nothing</html>') is None
