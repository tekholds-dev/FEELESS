import json
import music


def page(videos):
    data = {'contents': {'list': [{'videoRenderer': v} for v in videos]}}
    return f'<script>var ytInitialData = {json.dumps(data)};</script>'


def v(i, title, length='3:20'):
    return {'videoId': i, 'title': {'runs': [{'text': title}]}, 'ownerText': {'runs': [{'text': 'Chan'}]}, 'lengthText': {'simpleText': length} if length else None,
            'viewCountText': {'simpleText': '1,000 views'}}


def test_youtube_results_are_read_from_the_page_videos_only():
    rows = music.yt_results(page([v('aaaaaaaaaaa', "Drake - God's Plan"), v('bbbbbbbbbbb', 'Live now', None), v('aaaaaaaaaaa', 'dupe')]))
    assert [r['id'] for r in rows] == ['aaaaaaaaaaa'] and rows[0]['title'] == "Drake - God's Plan" and rows[0]['url'].endswith('aaaaaaaaaaa')
    assert music.yt_results('<html>nothing</html>') == []


def test_next_keeps_going_with_the_artist_never_a_song_already_queued():
    assert music.artist_of("Drake - God's Plan (Official Video)") == 'Drake'
    rows = [{'id': 'a', 'title': "Drake - God's Plan"}, {'id': 'b', 'title': "Drake - God's Plan (Lyrics)"}, {'id': 'c', 'title': 'Drake - Hotline Bling'}]
    assert music.pick_next(rows, skip_ids=['a'], skip_titles=["Drake - God's Plan"])['id'] == 'c'


def test_apple_chart_and_spotify_rows_carry_a_youtube_query():
    top = music.apple_top({'feed': {'results': [{'name': 'Song', 'artistName': 'Artist', 'artworkUrl100': 'x'}]}})
    assert top == [{'title': 'Song', 'artist': 'Artist', 'art': 'x', 'query': 'Artist Song'}]
    sp = music.spotify_tracks({'tracks': {'items': [{'name': 'T', 'artists': [{'name': 'A'}], 'album': {'images': [{'url': 'i'}]}, 'popularity': 90}]}})
    assert sp[0]['query'] == 'A T' and sp[0]['popularity'] == 90


def test_next_never_picks_an_hour_long_mix():
    rows = [{'id': 'm', 'title': 'Drake 2025 MIX Best Collection', 'length': '1:02:03'}, {'id': 's', 'title': 'Drake - Hotline Bling', 'length': '4:55'}]
    assert music.pick_next(rows)['id'] == 's' and music.secs('3:19') == 199 and music.secs('') is None
