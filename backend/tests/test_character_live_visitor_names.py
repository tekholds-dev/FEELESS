"""🎭 characters · 🔴 the live relay · 👀 what a visitor sees · 🪪 name locks. Fakes only: no network, no real channel."""
import asyncio
import io

import pytest
from PIL import Image

import agent_face as af
import agent_live as al
import name_lock as nl
import visitor_view as vv


def _jpg(size=(200, 100), color=(255, 255, 255)):
    b = io.BytesIO(); Image.new('RGB', size, color).save(b, 'JPEG'); return b.getvalue()


def test_only_the_24_characters_pass():
    assert af.clean_id('Sora') == 'sora' and len(af.FACES) == 24
    assert af.clean_id('../../etc/passwd') is None and af.clean_id('') is None


def test_a_thumb_is_reencoded_and_strips_what_is_not_pixels():
    raw = io.BytesIO(); exif = Image.Exif(); exif[0x010e] = 'home address'
    Image.new('RGB', (900, 900), (9, 9, 9)).save(raw, 'JPEG', exif=exif)
    out = af.clean_thumb(raw.getvalue())
    im = Image.open(io.BytesIO(out))
    assert im.width == 256 and not dict(im.getexif())
    assert af.clean_thumb(b'<svg onload=alert(1)>') is None
    assert af.clean_thumb(b'x' * (af.MAX_THUMB + 1)) is None


def test_a_character_must_be_one_json_object_under_the_cap():
    assert af.clean_character(b'{"a":1}') == b'{"a":1}'
    assert af.clean_character(b'[1]') is None and af.clean_character(b'<html>') is None
    assert af.clean_character(b'{"a":"' + b'x' * af.MAX_CHAR + b'"}') is None


@pytest.mark.parametrize('platform,url', [('twitch', ''), ('twitch', 'rtmps://live.twitch.tv/app'), ('kick', 'rtmps://abc123.global-contribute.live-video.net/app'), ('tiktok', 'rtmp://push-rtmp-l1.tiktokcdn.com/game')])
def test_a_published_stream_address_passes(platform, url):
    assert al.check_server(platform, url)


@pytest.mark.parametrize('platform,url', [('twitch', 'rtmp://live.twitch.tv/app'), ('twitch', 'rtmps://evil.example/app'), ('twitch', 'rtmps://live.twitch.tv.evil.example/app'), ('kick', 'rtmps://u:p@x.contribute.live-video.net/app'),
                                          ('kick', ''), ('tiktok', 'rtmp://127.0.0.1/app'), ('tiktok', 'file:///etc/passwd'), ('nope', 'rtmps://live.twitch.tv/app')])
def test_any_other_address_is_refused(platform, url):
    with pytest.raises(ValueError):
        al.check_server(platform, url)


def test_a_key_cannot_smuggle_ffmpeg_options():
    assert al.check_key('live_123456_abcDEF?x=1')
    for bad in ('short', 'a b c d e f g h', 'abcdefgh|rtmp://evil', 'abcdefgh]x', "abcdefgh'x"):
        with pytest.raises(ValueError):
            al.check_key(bad)


def test_one_channel_or_many():
    assert al.ffmpeg_args(['rtmps://a/k'])[-3:] == ['-f', 'flv', 'rtmps://a/k']
    many = al.ffmpeg_args(['rtmps://a/k', 'rtmps://b/k'])
    assert many[-1] == '[f=flv:onfail=ignore]rtmps://a/k|[f=flv:onfail=ignore]rtmps://b/k'


def test_a_key_never_reaches_a_message():
    assert 'SECRET' not in al.hide_keys('failed rtmps://x/SECRETKEY', ['SECRETKEY'])
    pub = al.public_row({'since': 5, 'platforms': ['twitch'], 'key': 'SECRET'})
    assert pub == {'on': True, 'since': 5, 'where': ['Twitch']} and al.public_row(None) == {'on': False}
    view = al.owner_view({'twitch': {'server': 'rtmps://s', 'key': 'v2:sealed'}})
    assert view['twitch']['set'] is True and 'v2:sealed' not in str(view) and view['kick']['set'] is False


class _Stdin:
    def __init__(self): self.got, self.closed = [], False
    def write(self, b): self.got.append(b)
    async def drain(self): pass
    def is_closing(self): return self.closed
    def close(self): self.closed = True


class _Err:
    async def readline(self): return b''


class _Proc:
    def __init__(self): self.stdin, self.stderr, self.returncode = _Stdin(), _Err(), None
    async def wait(self): self.returncode = 0; return 0
    def kill(self): self.returncode = -9


def test_the_relay_passes_bytes_and_stops():
    async def go():
        made = {}
        async def spawn(*args, **kw): made['args'] = args; made['p'] = _Proc(); return made['p']
        r = al.Relay(['rtmps://x/KEY'], ['KEY']); await r.start(spawn); await r.write(b'abc'); assert made['p'].stdin.got == [b'abc']
        await r.stop(); assert made['p'].stdin.closed and made['p'].returncode == 0 and not r.alive
        with pytest.raises(ConnectionError):
            await r.write(b'x')
    asyncio.run(go())


@pytest.mark.parametrize('url', ['https://mail.google.com/mail/u/0', 'https://mail.tm/inbox', 'https://accounts.google.com/x', 'https://x.com/settings/account', 'https://polymarket.com/profile', 'https://pump.fun/login', 'https://a.com/account/security',
                                 'https://stake.us/settings/verification', 'https://a.com/sign-in', 'javascript:alert(1)', 'not a url'])
def test_private_pages(url):
    assert vv.private_page(url)


@pytest.mark.parametrize('url', ['https://polymarket.com/event/lakers', 'https://pump.fun/coin/abc', 'https://dexscreener.com/solana', 'https://stake.us/sports/nfl', 'https://news.site/settlement-news', 'https://a.com/portfolio', ''])
def test_public_pages(url):
    assert not vv.private_page(url)


def test_scrub_takes_out_emails_and_phones_only():
    got = vv.scrub({'a': 'write me at joe.bloggs+1@gmail.com now', 'b': ['call (415) 555-0134'], 'c': 'balance $1,234.56 at 12:30 on 2026-11-04', 'n': 5, 'd': {'e': '+1 415-555-0134'}})
    assert got['a'] == 'write me at 🔒 now' and got['b'] == ['call 🔒'] and got['d']['e'] == '🔒'
    assert got['c'] == 'balance $1,234.56 at 12:30 on 2026-11-04' and got['n'] == 5


def test_the_blank_screen_is_a_real_picture():
    im = Image.open(io.BytesIO(vv.blank_jpg()))
    assert im.size == (960, 600) and vv.blank_jpg() is vv.blank_jpg()


class _Page:
    url = 'https://polymarket.com/portfolio'
    def __init__(self, rects=(), boom=False): self.rects, self.boom, self.calls = rects, boom, 0
    async def find_private(self, js):
        self.calls += 1
        if self.boom:
            raise RuntimeError('page gone')
        return {'rects': list(self.rects), 'w': 200, 'h': 100}
    async def shot(self): return _jpg()


def test_a_visitor_frame_covers_the_spot_and_keeps_the_rest():
    out = asyncio.run(vv.visitor_frame(_Page([[10, 10, 60, 30]])))
    im = Image.open(io.BytesIO(out)).convert('RGB')
    assert sum(im.getpixel((30, 20))) < 90 and sum(im.getpixel((150, 80))) > 700


def test_a_private_page_or_any_failure_shows_blank_never_a_raw_frame():
    assert asyncio.run(vv.visitor_frame(_Page(), 'https://mail.google.com/x')) == vv.blank_jpg()
    assert asyncio.run(vv.visitor_frame(_Page(boom=True))) == vv.blank_jpg()
    class NoFind:
        url = 'https://a.com/'
        async def shot(self): return _jpg()
    assert asyncio.run(vv.visitor_frame(NoFind())) == vv.blank_jpg()


def test_first_name_is_free_then_7_days():
    ok, rec, _ = nl.check(None, 'w', 'Ann', now=1000)
    assert ok and rec['name'] == 'Ann' and nl.genuine(rec, 'w', 'Ann')
    ok, same, _ = nl.check(rec, 'w', 'Ann', now=1100)
    assert ok and same is rec
    ok, still, why = nl.check(rec, 'w', 'Bea', now=1000 + 6 * 86400)
    assert not ok and still is rec and '7 days' in why and 'Try again in 1d 0h' in why
    ok, rec2, _ = nl.check(rec, 'w', 'Bea', now=1000 + nl.LOCK_S)
    assert ok and rec2['name'] == 'Bea'


def test_staff_change_any_time_and_past_names_are_sealed():
    rec = nl.stamp(None, 'w', 'Ann', now=1000)
    ok, rec2, _ = nl.check(rec, 'w', 'Bea', is_staff=True, now=1001)
    assert ok and rec2['name'] == 'Bea' and 'Ann' not in rec2['past'] and nl.past_names(rec2)[0]['name'] == 'Ann'


def test_a_forged_name_fails_the_signature():
    rec = nl.stamp(None, 'w', 'Ann', now=1000)
    assert not nl.genuine({**rec, 'name': 'Scammer'}, 'w', 'Scammer')
    assert not nl.genuine(rec, 'other-wallet', 'Ann')
