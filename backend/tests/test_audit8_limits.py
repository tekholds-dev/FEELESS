"""Audit 2026-11-12 #8: anonymous callers can't burn memory, disk or the global lock (uploads, ads, clicks, page views, edge, HQ pair, perps)."""
import asyncio
import base64

import pytest

rs = pytest.importorskip('reputation_service')


class Req:
    def __init__(self, ip='9.9.9.9'):
        self.headers = {}
        self.client = type('C', (), {'host': ip})()


def test_an_oversized_upload_is_refused_before_the_base64_decode(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'UPLOAD_DIR', tmp_path)
    monkeypatch.setattr(rs, '_require_admin', lambda r: (_ for _ in ()).throw(rs.HTTPException(403, 'no')))
    rs._upload_ip.clear()
    decoded = []
    real = base64.b64decode
    monkeypatch.setattr(base64, 'b64decode', lambda s, *a, **k: decoded.append(1) or real(s, *a, **k))
    big = 'data:image/png;base64,' + 'A' * (rs.upload_cap('image/png', 'user') * 4 // 3 + 100)
    with pytest.raises(rs.HTTPException) as e:
        asyncio.run(rs.upload_image(rs.UploadPayload(dataUrl=big), Req()))
    assert e.value.status_code == 413 and decoded == []


def test_an_ad_event_for_a_made_up_id_never_rewrites_the_file_and_devices_are_limited(monkeypatch):
    saves = []
    monkeypatch.setattr(rs, '_json_load', lambda p, d=None: {'ads': [{'id': 'real1', 'views': 0}]} if p == rs.ADS_PATH else (d or {}))
    monkeypatch.setattr(rs, '_json_save', lambda p, d: saves.append(p))
    rs._ad_ev_ip.clear()
    assert asyncio.run(rs.ad_event('nope', Req(), 'view')) == {'ok': False}
    assert asyncio.run(rs.ad_event('../x', Req(), 'view')) == {'ok': False}
    assert saves == []
    assert asyncio.run(rs.ad_event('real1', Req(), 'view')) == {'ok': True} and saves == [rs.ADS_PATH]
    for _ in range(59):
        asyncio.run(rs.ad_event('real1', Req(), 'view'))
    with pytest.raises(rs.HTTPException) as e:
        asyncio.run(rs.ad_event('real1', Req(), 'view'))
    assert e.value.status_code == 429
    assert asyncio.run(rs.ad_event('real1', Req('8.8.8.8'), 'click')) == {'ok': True}   # another device is not locked out


def test_the_click_map_stops_growing_at_its_cap(monkeypatch):
    d = {f'ca:k{i}': [1, 0, 0] for i in range(rs.CLICKS_MAX)}
    monkeypatch.setattr(rs, '_json_load', lambda p, dflt=None: d)
    monkeypatch.setattr(rs, '_json_save', lambda p, x: None)
    rs._click_ip.clear()
    assert asyncio.run(rs.track_click(Req(), rs.ClickIn(kind='ca', value='brand-new'))) == {'ok': False, 'count': 0}
    assert asyncio.run(rs.track_click(Req(), rs.ClickIn(kind='ca', value='k5')))['count'] == 2   # a known key still counts
    assert len(d) == rs.CLICKS_MAX


def test_page_view_maps_from_the_request_are_capped(monkeypatch):
    monkeypatch.setattr(rs, '_tr_buf', {'views': {}, 'uniq': {}, 'coins': {}, 'refs': {}, 'hours': {}})
    rs._tr_ip.clear()
    for i in range(rs.TR_MAP_MAX + 50):
        rs._tr_ip.clear()
        asyncio.run(rs.page_view(Req(), rs.PageView(path=f'/p{i}?pair=C{i}', ref=f'https://h{i}.io/')))
    b = rs._tr_buf
    assert max(len(v) for v in b['views'].values()) == rs.TR_MAP_MAX
    assert len(b['coins']) == rs.TR_MAP_MAX and len(b['refs']) == rs.TR_MAP_MAX


def test_one_device_cannot_flood_hq_pair_codes(monkeypatch):
    monkeypatch.setattr(rs, '_lan_ip', lambda: None)
    rs._hqp_ip.clear()
    for _ in range(6):
        asyncio.run(rs.hq_pair_new(Req('7.7.7.7'), 51367))
    with pytest.raises(rs.HTTPException) as e:
        asyncio.run(rs.hq_pair_new(Req('7.7.7.7'), 51367))
    assert e.value.status_code == 429


def test_edge_observe_and_perps_send_are_limited_per_device():
    rs._edge_ip.clear(); rs._fjx_hits.clear()
    assert all(rs._ip_hit(rs._edge_ip, Req(), 120, 3600) for _ in range(120)) and not rs._ip_hit(rs._edge_ip, Req(), 120, 3600)
    assert all(rs._ip_hit(rs._fjx_hits, Req(), 30, 3600) for _ in range(30)) and not rs._ip_hit(rs._fjx_hits, Req(), 30, 3600)
    import pathlib
    import re
    src = re.sub(r'\b(?:rs|_RSM)\.', '', ''.join(f.read_text() for f in [pathlib.Path(rs.__file__), *sorted(pathlib.Path(rs.__file__).parent.glob('rep_*.py'))]))   # SITE-5 moves routes out; read them wherever they are
    assert 'if not _ip_hit(_edge_ip, request, 120, 3600)' in src and 'if not _ip_hit(_fjx_hits, request, 30, 3600)' in src


def test_trading_internal_key_is_constant_time_and_a_missing_key_refuses(monkeypatch):
    import trading
    monkeypatch.setattr(trading, '_internal_key', lambda: 'K1')
    ok = lambda h: trading._internal_ok(type('R', (), {'headers': h})())
    assert ok({'x-feeless-internal': 'K1'}) and not ok({'x-feeless-internal': 'K2'}) and not ok({})
    monkeypatch.setattr(trading, '_internal_key', lambda: '')
    assert not ok({'x-feeless-internal': ''})
    assert "!= key" not in open(trading.__file__).read()
